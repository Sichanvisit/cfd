"""Log-only breakout overlay contracts.

Phase 0 freezes how breakout events will translate into later policy overlays,
without applying any live behavior changes.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.services.breakout_event_runtime import (
    BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION,
    build_breakout_event_runtime_v1,
)


BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION = "breakout_event_overlay_candidates_v1"
BREAKOUT_EVENT_OVERLAY_TRACE_CONTRACT_VERSION = "breakout_event_overlay_trace_v1"
BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_VERSION = "breakout_event_overlay_scope_freeze_v1"

BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_VERSION,
    "overlay_role": "log_only_breakout_translation_layer",
    "phase": "P0",
    "runtime_direct_use_fields": [
        "breakout_event_runtime_v1",
        "breakout_event_overlay_candidates_v1",
        "breakout_event_overlay_trace_v1",
    ],
    "runtime_dependencies": [
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1",
        "belief_state25_runtime_bridge_v1.belief_runtime_summary_v1",
        "barrier_state25_runtime_bridge_v1.barrier_runtime_summary_v1",
    ],
    "replay_only_fields": [
        "breakout_manual_alignment_v1",
        "breakout_action_target_v1",
    ],
    "no_leakage_rule": (
        "Breakout overlay candidates may translate runtime breakout signals into "
        "log-only hints, but they must not consume manual truth labels, future bar "
        "outcomes, or replay-derived action targets."
    ),
}

BREAKOUT_ACTION_TARGET_ENTER_NOW = "ENTER_NOW"
BREAKOUT_ACTION_TARGET_WAIT_MORE = "WAIT_MORE"
BREAKOUT_ACTION_TARGET_AVOID_ENTRY = "AVOID_ENTRY"
BREAKOUT_ACTION_TARGET_EXIT_PROTECT = "EXIT_PROTECT"
BREAKOUT_ACTION_TARGET_WATCH_BREAKOUT = "WATCH_BREAKOUT"
BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT = "PROBE_BREAKOUT"

BREAKOUT_SOFT_BARRIER_PROBE_MIN = 0.50
BREAKOUT_SOFT_BARRIER_PROBE_MAX = 0.66
BREAKOUT_SOFT_BARRIER_PROBE_CONFIDENCE_MIN = 0.09
BREAKOUT_SOFT_BARRIER_PROBE_CONFIRM_MIN = 0.11
BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN = 0.10


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _runtime_breakout(
    row: Mapping[str, Any] | None,
    breakout_event_runtime_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mapped = _as_mapping(breakout_event_runtime_v1)
    if mapped:
        return mapped
    payload = _as_mapping(row)
    existing = _as_mapping(payload.get(BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION))
    if existing:
        return existing
    return build_breakout_event_runtime_v1(payload)


def _forecast_summary(bridge: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_as_mapping(bridge).get("forecast_runtime_summary_v1"))


def _belief_summary(bridge: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_as_mapping(bridge).get("belief_runtime_summary_v1"))


def _barrier_summary(bridge: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_as_mapping(bridge).get("barrier_runtime_summary_v1"))


def _confirm_aligned(direction: str, confirm_side: str) -> bool:
    direction_u = _to_str(direction).upper()
    confirm_u = _to_str(confirm_side).upper()
    if direction_u == "UP":
        return confirm_u == "BUY"
    if direction_u == "DOWN":
        return confirm_u == "SELL"
    return False


def _resolve_breakout_conflict_v1(
    *,
    breakout_state: str,
    breakout_direction: str,
    effective_readiness: str,
    breakout_confidence: float,
    confirm_side: str,
    confirm_score: float,
    continuation_score: float,
    confirm_aligned: bool,
    barrier_total: float,
) -> dict[str, Any]:
    breakout_live = breakout_state in {"initial_breakout", "breakout_pullback", "breakout_continuation"}
    ready = effective_readiness in {"READY_BREAKOUT", "BUILDING_BREAKOUT", "COILED_BREAKOUT"}
    has_confirm_owner = _to_str(confirm_side).upper() in {"BUY", "SELL"}
    confirm_conflict = breakout_live and has_confirm_owner and not confirm_aligned and confirm_score >= 0.10
    barrier_drag = breakout_live and barrier_total > 0.35
    breakout_viable = breakout_confidence >= 0.08 and ready and breakout_direction in {"UP", "DOWN"}

    conflict_level = "none"
    confirm_alignment_score = 1.0 if confirm_aligned else (0.0 if confirm_conflict else 0.5)
    action_demotion_rule = ""
    demoted_candidate_action_target = ""

    if not breakout_viable:
        if confirm_conflict:
            conflict_level = "confirm_conflict"
        elif barrier_drag:
            conflict_level = "barrier_drag"
        return {
            "conflict_level": conflict_level,
            "confirm_alignment_score": round(float(confirm_alignment_score), 6),
            "action_demotion_rule": action_demotion_rule,
            "demoted_candidate_action_target": demoted_candidate_action_target,
        }

    if confirm_conflict and barrier_drag:
        conflict_level = "stacked_conflict"
        action_demotion_rule = "watch_breakout_conflict_stack"
        demoted_candidate_action_target = BREAKOUT_ACTION_TARGET_WATCH_BREAKOUT
    elif (
        barrier_drag
        and confirm_aligned
        and BREAKOUT_SOFT_BARRIER_PROBE_MIN <= barrier_total <= BREAKOUT_SOFT_BARRIER_PROBE_MAX
        and breakout_confidence >= BREAKOUT_SOFT_BARRIER_PROBE_CONFIDENCE_MIN
        and (
            confirm_score >= BREAKOUT_SOFT_BARRIER_PROBE_CONFIRM_MIN
            or continuation_score >= BREAKOUT_SOFT_BARRIER_PROBE_CONTINUATION_MIN
        )
    ):
        conflict_level = "barrier_drag"
        action_demotion_rule = "probe_breakout_soft_barrier_drag"
        demoted_candidate_action_target = BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT
    elif barrier_drag:
        conflict_level = "barrier_drag"
        action_demotion_rule = "watch_breakout_barrier_drag"
        demoted_candidate_action_target = BREAKOUT_ACTION_TARGET_WATCH_BREAKOUT
    elif confirm_conflict:
        conflict_level = "confirm_conflict"
        action_demotion_rule = "probe_breakout_confirm_conflict"
        demoted_candidate_action_target = BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT

    return {
        "conflict_level": conflict_level,
        "confirm_alignment_score": round(float(confirm_alignment_score), 6),
        "action_demotion_rule": action_demotion_rule,
        "demoted_candidate_action_target": demoted_candidate_action_target,
    }


def build_breakout_event_overlay_candidates_v1(
    row: Mapping[str, Any] | None = None,
    *,
    breakout_event_runtime_v1: Mapping[str, Any] | None = None,
    forecast_state25_runtime_bridge_v1: Mapping[str, Any] | None = None,
    belief_state25_runtime_bridge_v1: Mapping[str, Any] | None = None,
    barrier_state25_runtime_bridge_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    breakout = _runtime_breakout(row, breakout_event_runtime_v1)
    forecast = _forecast_summary(forecast_state25_runtime_bridge_v1)
    belief = _belief_summary(belief_state25_runtime_bridge_v1)
    barrier = _barrier_summary(barrier_state25_runtime_bridge_v1)

    if not breakout.get("available", False):
        return {
            "contract_version": BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION,
            "available": False,
            "enabled": False,
            "overlay_mode": "observe_only",
            "wait_bias_action": "observe_only",
            "barrier_relief_action": "observe_only",
            "belief_action": "observe_only",
            "forecast_path_hint": "",
            "candidate_action_target": "",
            "reason_summary": "breakout_runtime_unavailable",
        }

    breakout_state = _to_str(breakout.get("breakout_state")).lower()
    breakout_direction = _to_str(breakout.get("breakout_direction")).upper()
    effective_readiness = _to_str(breakout.get("effective_breakout_readiness_state")).upper()
    breakout_confidence = _to_float(breakout.get("breakout_confidence"))
    failure_risk = _to_float(breakout.get("breakout_failure_risk"))
    followthrough = _to_float(breakout.get("breakout_followthrough_score"))
    hold_exit_gap = _to_float(forecast.get("hold_exit_gap"))
    confirm_side = _to_str(forecast.get("confirm_side")).upper()
    confirm_score = _to_float(forecast.get("confirm_score"))
    barrier_total = _to_float(barrier.get("barrier_total"))
    flip_readiness = _to_float(belief.get("flip_readiness"))
    confirm_aligned = _confirm_aligned(breakout_direction, confirm_side)
    conflict_trace = _resolve_breakout_conflict_v1(
        breakout_state=breakout_state,
        breakout_direction=breakout_direction,
        effective_readiness=effective_readiness,
        breakout_confidence=breakout_confidence,
        confirm_side=confirm_side,
        confirm_score=confirm_score,
        continuation_score=followthrough,
        confirm_aligned=confirm_aligned,
        barrier_total=barrier_total,
    )

    wait_bias_action = "hold_wait_bias"
    barrier_relief_action = "keep_barrier"
    belief_action = "monitor_thesis"
    forecast_path_hint = "await_breakout"
    candidate_action_target = BREAKOUT_ACTION_TARGET_WAIT_MORE
    reason_tokens: list[str] = []

    if breakout_state == "failed_breakout" or failure_risk >= 0.70:
        wait_bias_action = "reinforce_wait_bias"
        barrier_relief_action = "preserve_protection"
        belief_action = "degrade_thesis"
        forecast_path_hint = "failed_breakout_reversal"
        candidate_action_target = BREAKOUT_ACTION_TARGET_AVOID_ENTRY
        reason_tokens.extend(("failed_breakout", "avoid_entry"))
    elif (
        breakout_state in {"initial_breakout", "breakout_pullback"}
        and effective_readiness in {"READY_BREAKOUT", "BUILDING_BREAKOUT"}
        and breakout_confidence >= 0.28
        and failure_risk <= 0.40
        and barrier_total <= 0.35
        and followthrough >= 0.20
        and confirm_aligned
        and confirm_score >= 0.18
    ):
        wait_bias_action = "release_wait_bias"
        barrier_relief_action = "relax_breakout_drag"
        belief_action = "reinforce_thesis"
        forecast_path_hint = "breakout_then_continue" if followthrough >= 0.30 else "breakout_then_retest"
        candidate_action_target = BREAKOUT_ACTION_TARGET_ENTER_NOW
        reason_tokens.extend(("surrogate_ready_breakout_entry", forecast_path_hint))
    elif breakout_state in {"initial_breakout", "breakout_pullback"} and breakout_confidence >= 0.55 and failure_risk <= 0.55:
        wait_bias_action = "release_wait_bias"
        barrier_relief_action = "relax_breakout_drag"
        belief_action = "reinforce_thesis"
        forecast_path_hint = "breakout_then_continue" if followthrough >= 0.45 else "breakout_then_retest"
        candidate_action_target = BREAKOUT_ACTION_TARGET_ENTER_NOW
        reason_tokens.extend(("breakout_entry", forecast_path_hint))
    elif (
        breakout_state in {"initial_breakout", "breakout_pullback"}
        and breakout_direction in {"UP", "DOWN"}
        and effective_readiness in {"READY_BREAKOUT", "BUILDING_BREAKOUT", "COILED_BREAKOUT"}
        and breakout_confidence >= 0.12
        and failure_risk <= 0.45
        and barrier_total <= 0.35
        and followthrough >= 0.10
        and confirm_aligned
    ):
        wait_bias_action = "soft_release_wait_bias"
        barrier_relief_action = "bounded_probe_only"
        belief_action = "bounded_probe_thesis"
        forecast_path_hint = "breakout_then_retest"
        candidate_action_target = BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT
        reason_tokens.extend(("supportive_breakout_probe", "probe_breakout"))
    elif breakout_state == "breakout_continuation" and hold_exit_gap <= -0.12 and flip_readiness >= 0.40:
        wait_bias_action = "neutral_wait_bias"
        barrier_relief_action = "keep_relief"
        belief_action = "protect_open_thesis"
        forecast_path_hint = "breakout_then_continue"
        candidate_action_target = BREAKOUT_ACTION_TARGET_EXIT_PROTECT
        reason_tokens.extend(("continuation_protect", "exit_protect"))
    elif breakout_state == "breakout_continuation" and breakout_confidence >= 0.50 and barrier_total <= 0.45:
        wait_bias_action = "release_wait_bias"
        barrier_relief_action = "relax_breakout_drag"
        belief_action = "reinforce_thesis"
        forecast_path_hint = "breakout_then_continue"
        candidate_action_target = BREAKOUT_ACTION_TARGET_ENTER_NOW
        reason_tokens.extend(("continuation_entry", "confirm_followthrough"))
    elif conflict_trace.get("demoted_candidate_action_target") == BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT:
        wait_bias_action = "soft_release_wait_bias"
        barrier_relief_action = "bounded_probe_only"
        belief_action = "bounded_probe_thesis"
        forecast_path_hint = "breakout_probe_window"
        candidate_action_target = BREAKOUT_ACTION_TARGET_PROBE_BREAKOUT
        reason_tokens.extend(
            (
                _to_str(conflict_trace.get("action_demotion_rule"), "probe_breakout_confirm_conflict"),
                "probe_breakout",
            )
        )
    elif conflict_trace.get("demoted_candidate_action_target") == BREAKOUT_ACTION_TARGET_WATCH_BREAKOUT:
        wait_bias_action = "soft_hold_watch_bias"
        barrier_relief_action = "keep_barrier_watch"
        belief_action = "monitor_breakout_conflict"
        forecast_path_hint = "breakout_watch_window"
        candidate_action_target = BREAKOUT_ACTION_TARGET_WATCH_BREAKOUT
        reason_tokens.extend(
            (
                _to_str(conflict_trace.get("action_demotion_rule"), "watch_breakout_barrier_drag"),
                "watch_breakout",
            )
        )
    else:
        if breakout_state in {"initial_breakout", "breakout_pullback"}:
            if not confirm_aligned and confirm_score >= 0.10:
                reason_tokens.extend(("confirm_conflict_hold", "wait_more"))
            elif barrier_total > 0.35:
                reason_tokens.extend(("barrier_drag_hold", "wait_more"))
            elif breakout_confidence < 0.28:
                reason_tokens.extend(("overlay_confidence_low", "wait_more"))
            elif effective_readiness not in {"READY_BREAKOUT", "BUILDING_BREAKOUT"}:
                reason_tokens.extend(("readiness_not_ready", "wait_more"))
            else:
                reason_tokens.extend(("initial_breakout_hold", "wait_more"))
        elif breakout_state == "breakout_continuation":
            reason_tokens.extend(("continuation_hold", "wait_more"))
        else:
            reason_tokens.extend(("pre_breakout", "wait_more"))

    return {
        "contract_version": BREAKOUT_EVENT_OVERLAY_CANDIDATES_CONTRACT_VERSION,
        "available": True,
        "enabled": True,
        "overlay_mode": "log_only",
        "wait_bias_action": wait_bias_action,
        "barrier_relief_action": barrier_relief_action,
        "belief_action": belief_action,
        "forecast_path_hint": forecast_path_hint,
        "candidate_action_target": candidate_action_target,
        "conflict_level": _to_str(conflict_trace.get("conflict_level")),
        "confirm_alignment_score": round(_to_float(conflict_trace.get("confirm_alignment_score"), 0.0), 6),
        "action_demotion_rule": _to_str(conflict_trace.get("action_demotion_rule")),
        "reason_summary": "|".join(reason_tokens),
    }


def build_breakout_event_overlay_trace_v1(
    breakout_event_overlay_candidates_v1: Mapping[str, Any] | None,
    *,
    symbol: str = "",
    entry_stage: str = "",
) -> dict[str, Any]:
    overlay = _as_mapping(breakout_event_overlay_candidates_v1)
    return {
        "contract_version": BREAKOUT_EVENT_OVERLAY_TRACE_CONTRACT_VERSION,
        "symbol": _to_str(symbol).upper(),
        "entry_stage": _to_str(entry_stage).upper(),
        "binding_mode": "log_only",
        "overlay_available": bool(overlay.get("available", False)),
        "overlay_enabled": bool(overlay.get("enabled", False)),
        "actual_policy_unchanged": True,
        "candidate_action_target": _to_str(overlay.get("candidate_action_target")),
        "candidate_wait_bias_action": _to_str(overlay.get("wait_bias_action")),
        "candidate_barrier_relief_action": _to_str(overlay.get("barrier_relief_action")),
        "candidate_belief_action": _to_str(overlay.get("belief_action")),
        "candidate_forecast_path_hint": _to_str(overlay.get("forecast_path_hint")),
        "candidate_conflict_level": _to_str(overlay.get("conflict_level")),
        "candidate_action_demotion_rule": _to_str(overlay.get("action_demotion_rule")),
        "reason_summary": _to_str(overlay.get("reason_summary")),
    }
