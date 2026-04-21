"""Runtime-safe barrier-state25 bridge helpers."""

from __future__ import annotations

import json
from typing import Any, Mapping

from backend.services.belief_state25_runtime_bridge import build_belief_runtime_summary_v1
from backend.services.entry_wait_belief_bias_policy import resolve_entry_wait_acting_side_v1
from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_runtime_summary_v1,
    build_state25_runtime_hint_v1,
)


BARRIER_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION = "barrier_state25_runtime_bridge_v1"
BARRIER_RUNTIME_SUMMARY_CONTRACT_VERSION = "barrier_runtime_summary_v1"
BARRIER_INPUT_TRACE_CONTRACT_VERSION = "barrier_input_trace_v1"
BARRIER_ACTION_HINT_CONTRACT_VERSION = "barrier_action_hint_v1"
BARRIER_SCOPE_FREEZE_CONTRACT_VERSION = "barrier_state25_scope_freeze_v1"

BARRIER_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": BARRIER_SCOPE_FREEZE_CONTRACT_VERSION,
    "scene_role": "scene_owner",
    "barrier_role": "blocking_owner",
    "forecast_role": "branch_owner",
    "belief_role": "thesis_persistence_owner",
    "runtime_direct_use_fields": [
        "barrier_runtime_summary_v1",
    ],
    "learning_only_fields": [
        "barrier_input_trace_v1",
        "barrier_action_hint_v1",
        "barrier_outcome_label",
        "barrier_label_confidence",
        "barrier_outcome_reason",
        "barrier_cost_loss_avoided_r",
        "barrier_cost_profit_missed_r",
        "barrier_cost_wait_value_r",
    ],
    "no_leakage_rule": (
        "Closed-trade labels, wait-quality/economic labels, and future barrier outcome labels are replay-only "
        "and must not be used as direct runtime barrier features."
    ),
}


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value or {})
    if isinstance(value, str):
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return dict(parsed or {}) if isinstance(parsed, Mapping) else {}
    return {}


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _pick_text(*values: Any) -> str:
    for value in values:
        text = _to_text(value)
        if text:
            return text
    return ""


def _scene_hint(row: Mapping[str, Any]) -> dict[str, Any]:
    existing = _coerce_mapping(_coerce_mapping(row.get("forecast_state25_runtime_bridge_v1")).get("state25_runtime_hint_v1"))
    if existing:
        return existing
    return build_state25_runtime_hint_v1(row)


def _forecast_hint(row: Mapping[str, Any]) -> dict[str, Any]:
    existing = _coerce_mapping(
        _coerce_mapping(row.get("forecast_state25_runtime_bridge_v1")).get("forecast_runtime_summary_v1")
    )
    if existing:
        return existing
    return build_forecast_runtime_summary_v1(row)


def _acting_side(payload: Mapping[str, Any], belief_summary: Mapping[str, Any]) -> str:
    acting_side = resolve_entry_wait_acting_side_v1(
        action=_to_text(payload.get("action")),
        core_allowed_action=_to_text(payload.get("core_allowed_action")),
        preflight_allowed_action=_to_text(payload.get("preflight_allowed_action")),
        dominant_side=_to_text(belief_summary.get("dominant_side")),
    )
    return acting_side.upper()


def _anchor_context(payload: Mapping[str, Any], acting_side: str) -> str:
    outcome = _to_text(payload.get("outcome")).lower()
    blocked_by = _to_text(payload.get("blocked_by")).lower()
    observe_reason = _to_text(payload.get("observe_reason")).lower()
    wait_selected = bool(payload.get("entry_wait_selected", False))
    wait_decision = _to_text(payload.get("entry_wait_decision")).lower()
    if outcome == "entered":
        return "relief_release"
    if wait_selected or wait_decision.startswith("wait") or outcome == "wait" or observe_reason:
        return "wait_block"
    if acting_side in {"BUY", "SELL"} or blocked_by:
        return "entry_block"
    return "entry_block"


def _component_candidates(barrier_state: Mapping[str, Any], acting_side: str) -> dict[str, float]:
    active_side = str(acting_side).upper()
    candidates = {
        "conflict_barrier": _to_float(barrier_state.get("conflict_barrier")),
        "middle_chop_barrier": _to_float(barrier_state.get("middle_chop_barrier")),
        "direction_policy_barrier": _to_float(barrier_state.get("direction_policy_barrier")),
        "liquidity_barrier": _to_float(barrier_state.get("liquidity_barrier")),
    }
    if active_side == "BUY":
        candidates["buy_barrier"] = _to_float(barrier_state.get("buy_barrier"))
    elif active_side == "SELL":
        candidates["sell_barrier"] = _to_float(barrier_state.get("sell_barrier"))
    else:
        candidates["buy_barrier"] = _to_float(barrier_state.get("buy_barrier"))
        candidates["sell_barrier"] = _to_float(barrier_state.get("sell_barrier"))
    return candidates


def _top_component(barrier_state: Mapping[str, Any], acting_side: str) -> tuple[str, float]:
    candidates = _component_candidates(barrier_state, acting_side)
    if not candidates:
        return "", 0.0
    name, value = max(candidates.items(), key=lambda item: float(item[1]))
    return str(name), float(value)


def _top_component_reason(barrier_state: Mapping[str, Any], component_name: str) -> str:
    metadata = _coerce_mapping(barrier_state.get("metadata"))
    reasons = _coerce_mapping(metadata.get("barrier_reasons"))
    return _to_text(reasons.get(component_name))


def _relief_score(barrier_state: Mapping[str, Any], acting_side: str) -> float:
    metadata = _coerce_mapping(barrier_state.get("metadata"))
    edge_turn_relief_score = _to_float(metadata.get("edge_turn_relief_score"))
    edge_turn_relief_v1 = _coerce_mapping(metadata.get("edge_turn_relief_v1"))
    side_relief = 0.0
    if str(acting_side).upper() == "BUY":
        side_relief = _to_float(edge_turn_relief_v1.get("buy_relief"))
    elif str(acting_side).upper() == "SELL":
        side_relief = _to_float(edge_turn_relief_v1.get("sell_relief"))
    return max(edge_turn_relief_score, side_relief)


def _barrier_total(barrier_state: Mapping[str, Any], acting_side: str) -> float:
    _, component_value = _top_component(barrier_state, acting_side)
    return float(component_value)


def _unavailable_barrier_context(payload: Mapping[str, Any]) -> tuple[str, str, str]:
    blocked_by = _to_text(payload.get("blocked_by")).lower()
    if blocked_by in {"max_positions_reached", "entry_cooldown"}:
        return "pre_context_skip", blocked_by, f"pre_context|{blocked_by}"
    return "runtime_unavailable", "barrier_missing", "barrier_missing"


def build_barrier_runtime_summary_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    barrier_state = _coerce_mapping(payload.get("barrier_state_v1"))
    if not barrier_state:
        availability_stage, availability_reason, reason_summary = _unavailable_barrier_context(payload)
        return {
            "contract_version": BARRIER_RUNTIME_SUMMARY_CONTRACT_VERSION,
            "available": False,
            "acting_side": "",
            "anchor_context": "",
            "barrier_total": 0.0,
            "active_side_barrier": 0.0,
            "opposite_side_barrier": 0.0,
            "top_component": "",
            "top_component_reason": "",
            "relief_score": 0.0,
            "blocking_bias": "UNAVAILABLE",
            "barrier_blocked_flag": False,
            "availability_stage": availability_stage,
            "availability_reason": availability_reason,
            "reason_summary": reason_summary,
        }

    belief_summary = build_belief_runtime_summary_v1(payload)
    acting_side = _acting_side(payload, belief_summary)
    anchor_context = _anchor_context(payload, acting_side)
    top_component, top_value = _top_component(barrier_state, acting_side)
    top_reason = _top_component_reason(barrier_state, top_component)
    relief_score = _relief_score(barrier_state, acting_side)

    if acting_side == "BUY":
        active_side_barrier = _to_float(barrier_state.get("buy_barrier"))
        opposite_side_barrier = _to_float(barrier_state.get("sell_barrier"))
    elif acting_side == "SELL":
        active_side_barrier = _to_float(barrier_state.get("sell_barrier"))
        opposite_side_barrier = _to_float(barrier_state.get("buy_barrier"))
    else:
        active_side_barrier = max(_to_float(barrier_state.get("buy_barrier")), _to_float(barrier_state.get("sell_barrier")))
        opposite_side_barrier = active_side_barrier

    barrier_total = _barrier_total(barrier_state, acting_side)
    blocked_by = _to_text(payload.get("blocked_by")).lower()
    observe_reason = _to_text(payload.get("observe_reason")).lower()
    barrier_blocked_flag = bool("barrier" in blocked_by or "barrier" in observe_reason or barrier_total >= 0.45)

    if barrier_total >= 0.60:
        blocking_bias = "HARD_BLOCK"
    elif barrier_total >= 0.35:
        blocking_bias = "WAIT_BLOCK"
    elif relief_score >= 0.20:
        blocking_bias = "RELIEF_READY"
    else:
        blocking_bias = "LIGHT_BLOCK"

    reason_summary = "|".join(
        token
        for token in (
            acting_side.lower() if acting_side else "",
            anchor_context,
            top_component.lower() if top_component else "",
            blocking_bias.lower(),
        )
        if token
    )
    return {
        "contract_version": BARRIER_RUNTIME_SUMMARY_CONTRACT_VERSION,
        "available": True,
        "acting_side": acting_side,
        "anchor_context": anchor_context,
        "barrier_total": round(float(barrier_total), 6),
        "active_side_barrier": round(float(active_side_barrier), 6),
        "opposite_side_barrier": round(float(opposite_side_barrier), 6),
        "conflict_barrier": round(_to_float(barrier_state.get("conflict_barrier")), 6),
        "middle_chop_barrier": round(_to_float(barrier_state.get("middle_chop_barrier")), 6),
        "direction_policy_barrier": round(_to_float(barrier_state.get("direction_policy_barrier")), 6),
        "liquidity_barrier": round(_to_float(barrier_state.get("liquidity_barrier")), 6),
        "top_component": top_component,
        "top_component_reason": top_reason,
        "relief_score": round(float(relief_score), 6),
        "blocking_bias": blocking_bias,
        "barrier_blocked_flag": barrier_blocked_flag,
        "reason_summary": reason_summary,
    }


def build_barrier_input_trace_v1(
    row: Mapping[str, Any] | None,
    *,
    barrier_runtime_summary_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(row or {})
    barrier_summary = _coerce_mapping(barrier_runtime_summary_v1)
    if not barrier_summary:
        barrier_summary = build_barrier_runtime_summary_v1(payload)
    if not barrier_summary.get("available", False):
        return {
            "contract_version": BARRIER_INPUT_TRACE_CONTRACT_VERSION,
            "available": False,
            "reason_summary": "barrier_missing",
        }

    scene_hint = _scene_hint(payload)
    forecast_summary = _forecast_hint(payload)
    belief_summary = build_belief_runtime_summary_v1(payload)
    barrier_state = _coerce_mapping(payload.get("barrier_state_v1"))
    metadata = _coerce_mapping(barrier_state.get("metadata"))
    reason_summary = "|".join(
        token
        for token in (
            _to_text(scene_hint.get("scene_pattern_name")),
            _to_text(forecast_summary.get("decision_hint")).lower(),
            _to_text(barrier_summary.get("top_component")).lower(),
            _to_text(barrier_summary.get("blocking_bias")).lower(),
        )
        if token
    )
    return {
        "contract_version": BARRIER_INPUT_TRACE_CONTRACT_VERSION,
        "available": True,
        "scene_id": int(_to_float(scene_hint.get("scene_pattern_id"), 0.0)),
        "state25_label": _to_text(scene_hint.get("scene_pattern_name")),
        "state25_confidence": round(_to_float(scene_hint.get("confidence")), 6),
        "forecast_decision_hint": _to_text(forecast_summary.get("decision_hint")).upper(),
        "forecast_confirm_side": _to_text(forecast_summary.get("confirm_side")).upper(),
        "forecast_wait_confirm_gap": round(_to_float(forecast_summary.get("wait_confirm_gap")), 6),
        "belief_dominant_side": _to_text(belief_summary.get("dominant_side")).upper(),
        "belief_persistence_hint": _to_text(belief_summary.get("persistence_hint")).upper(),
        "belief_flip_readiness": round(_to_float(belief_summary.get("flip_readiness")), 6),
        "direction_policy": _to_text(metadata.get("policy_side_barriers", {})).upper(),
        "top_component": _to_text(barrier_summary.get("top_component")),
        "top_component_reason": _to_text(barrier_summary.get("top_component_reason")),
        "relief_score": round(_to_float(barrier_summary.get("relief_score")), 6),
        "event_risk_barrier_score": round(_to_float(metadata.get("event_risk_barrier_score")), 6),
        "execution_friction_barrier_score": round(_to_float(metadata.get("execution_friction_barrier_score")), 6),
        "edge_turn_relief_score": round(_to_float(metadata.get("edge_turn_relief_score")), 6),
        "reason_summary": reason_summary,
    }


def build_barrier_action_hint_v1(
    row: Mapping[str, Any] | None,
    *,
    barrier_runtime_summary_v1: Mapping[str, Any] | None = None,
    barrier_input_trace_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(row or {})
    barrier_summary = _coerce_mapping(barrier_runtime_summary_v1)
    if not barrier_summary:
        barrier_summary = build_barrier_runtime_summary_v1(payload)
    barrier_trace = _coerce_mapping(barrier_input_trace_v1)
    if not barrier_trace:
        barrier_trace = build_barrier_input_trace_v1(
            payload,
            barrier_runtime_summary_v1=barrier_summary,
        )

    available = bool(
        barrier_summary.get("available", False)
        and barrier_trace.get("available", False)
    )
    if not available:
        return {
            "contract_version": BARRIER_ACTION_HINT_CONTRACT_VERSION,
            "available": False,
            "enabled": False,
            "hint_mode": "observe_only",
            "recommended_family": "observe_only",
            "supporting_label_candidate": "",
            "overlay_confidence": "low",
            "overlay_cost_hint": "neutral",
            "reason_summary": "barrier_hint_unavailable",
        }

    anchor_context = _to_text(barrier_summary.get("anchor_context")).lower()
    barrier_total = _to_float(barrier_summary.get("barrier_total"))
    relief_score = _to_float(barrier_summary.get("relief_score"))
    blocking_bias = _to_text(barrier_summary.get("blocking_bias")).upper()
    top_component = _to_text(barrier_summary.get("top_component"))
    forecast_decision_hint = _to_text(barrier_trace.get("forecast_decision_hint")).upper()
    belief_persistence_hint = _to_text(barrier_trace.get("belief_persistence_hint")).upper()
    belief_flip_readiness = _to_float(barrier_trace.get("belief_flip_readiness"))

    recommended_family = "observe_only"
    supporting_label_candidate = ""
    overlay_cost_hint = "neutral"
    reason_tokens: list[str] = []

    if (
        anchor_context == "relief_release"
        and relief_score >= 0.20
        and barrier_total <= 0.35
    ):
        recommended_family = "relief_release_bias"
        supporting_label_candidate = "relief_success"
        overlay_cost_hint = "profit_missed_risk"
        reason_tokens.extend(("release_relief", top_component.lower()))
    elif barrier_total >= 0.60 or blocking_bias == "HARD_BLOCK":
        recommended_family = "block_bias"
        supporting_label_candidate = "avoided_loss"
        overlay_cost_hint = "loss_avoided_bias"
        reason_tokens.extend(("hard_block", top_component.lower()))
    elif barrier_total >= 0.35 or blocking_bias == "WAIT_BLOCK":
        recommended_family = "wait_bias"
        supporting_label_candidate = "correct_wait"
        overlay_cost_hint = "wait_value_balance"
        reason_tokens.extend(("wait_block", belief_persistence_hint.lower()))
    elif relief_score >= 0.18 and barrier_total <= 0.34:
        recommended_family = "relief_watch"
        supporting_label_candidate = (
            "missed_profit" if forecast_decision_hint.endswith("CONFIRM") else "correct_wait"
        )
        overlay_cost_hint = "profit_missed_risk"
        reason_tokens.extend(("relief_watch", forecast_decision_hint.lower()))
    elif (
        anchor_context == "wait_block"
        and relief_score >= 0.12
        and barrier_total <= 0.24
        and belief_flip_readiness >= 0.40
    ):
        recommended_family = "relief_watch"
        supporting_label_candidate = "overblock"
        overlay_cost_hint = "profit_missed_risk"
        reason_tokens.extend(("overblock_watch", "flip_pressure"))

    enabled = recommended_family != "observe_only"
    if not enabled:
        overlay_confidence = "low"
        if not reason_tokens:
            reason_tokens.append("observe_only")
    elif recommended_family == "block_bias":
        overlay_confidence = "high" if barrier_total >= 0.72 else "medium"
    elif recommended_family == "wait_bias":
        overlay_confidence = (
            "high"
            if barrier_total >= 0.50 and relief_score <= 0.12
            else "medium"
        )
    elif recommended_family == "relief_release_bias":
        overlay_confidence = (
            "high"
            if relief_score >= 0.24 and barrier_total <= 0.28
            else "medium"
        )
    else:
        overlay_confidence = (
            "high"
            if relief_score >= 0.24 and barrier_total <= 0.26
            else "medium"
        )

    return {
        "contract_version": BARRIER_ACTION_HINT_CONTRACT_VERSION,
        "available": True,
        "enabled": enabled,
        "hint_mode": "log_only" if enabled else "observe_only",
        "recommended_family": recommended_family,
        "supporting_label_candidate": supporting_label_candidate,
        "overlay_confidence": overlay_confidence,
        "overlay_cost_hint": overlay_cost_hint,
        "anchor_context": anchor_context,
        "barrier_total": round(float(barrier_total), 6),
        "relief_score": round(float(relief_score), 6),
        "blocking_bias": blocking_bias,
        "top_component": top_component,
        "forecast_decision_hint": forecast_decision_hint,
        "belief_persistence_hint": belief_persistence_hint,
        "belief_flip_readiness": round(float(belief_flip_readiness), 6),
        "reason_summary": "|".join(token for token in reason_tokens[:4] if token),
    }


def build_barrier_state25_runtime_bridge_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    scene_hint = _scene_hint(payload)
    barrier_summary = build_barrier_runtime_summary_v1(payload)
    input_trace = build_barrier_input_trace_v1(payload, barrier_runtime_summary_v1=barrier_summary)
    barrier_action_hint = build_barrier_action_hint_v1(
        payload,
        barrier_runtime_summary_v1=barrier_summary,
        barrier_input_trace_v1=input_trace,
    )
    return {
        "contract_version": BARRIER_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION,
        "scope_freeze_contract_version": BARRIER_SCOPE_FREEZE_CONTRACT_VERSION,
        "scene_source": _pick_text(scene_hint.get("scene_source"), "state25_runtime_hint_v1"),
        "state25_runtime_hint_v1": scene_hint,
        "barrier_runtime_summary_v1": barrier_summary,
        "barrier_input_trace_v1": input_trace,
        "barrier_action_hint_v1": barrier_action_hint,
    }
