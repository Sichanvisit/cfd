"""Runtime-safe belief-state25 bridge helpers."""

from __future__ import annotations

from typing import Any, Mapping

from backend.services.entry_wait_belief_bias_policy import resolve_entry_wait_acting_side_v1
from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_runtime_summary_v1,
    build_state25_runtime_hint_v1,
)


BELIEF_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION = "belief_state25_runtime_bridge_v1"
BELIEF_RUNTIME_SUMMARY_CONTRACT_VERSION = "belief_runtime_summary_v1"
BELIEF_INPUT_TRACE_CONTRACT_VERSION = "belief_input_trace_v1"
BELIEF_ACTION_HINT_CONTRACT_VERSION = "belief_action_hint_v1"
BELIEF_SCOPE_FREEZE_CONTRACT_VERSION = "belief_state25_scope_freeze_v1"

BELIEF_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": BELIEF_SCOPE_FREEZE_CONTRACT_VERSION,
    "scene_role": "scene_owner",
    "belief_role": "thesis_persistence_owner",
    "forecast_role": "branch_owner",
    "barrier_role": "blocking_owner",
    "runtime_direct_use_fields": [
        "belief_runtime_summary_v1",
    ],
    "learning_only_fields": [
        "belief_input_trace_v1",
        "belief_action_hint_v1",
        "belief_outcome_label",
        "belief_label_confidence",
        "belief_break_signature",
        "belief_outcome_reason",
    ],
    "no_leakage_rule": (
        "Future outcome labels and closed-trade labels are replay-only and must not be used as "
        "direct runtime belief features."
    ),
}


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


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


def _active_side_from_row(row: Mapping[str, Any], belief_state: Mapping[str, Any]) -> str:
    acting_side = resolve_entry_wait_acting_side_v1(
        action=_to_text(row.get("action")),
        core_allowed_action=_to_text(row.get("core_allowed_action")),
        preflight_allowed_action=_to_text(row.get("preflight_allowed_action")),
        dominant_side=_to_text(belief_state.get("dominant_side")),
    )
    return acting_side.upper()


def _active_pair(side: str, belief_state: Mapping[str, Any]) -> tuple[float, float, float, float]:
    if str(side).upper() == "BUY":
        return (
            _to_float(belief_state.get("buy_belief")),
            _to_float(belief_state.get("buy_persistence")),
            _to_float(belief_state.get("sell_belief")),
            _to_float(belief_state.get("sell_persistence")),
        )
    if str(side).upper() == "SELL":
        return (
            _to_float(belief_state.get("sell_belief")),
            _to_float(belief_state.get("sell_persistence")),
            _to_float(belief_state.get("buy_belief")),
            _to_float(belief_state.get("buy_persistence")),
        )
    buy_belief = _to_float(belief_state.get("buy_belief"))
    sell_belief = _to_float(belief_state.get("sell_belief"))
    buy_persistence = _to_float(belief_state.get("buy_persistence"))
    sell_persistence = _to_float(belief_state.get("sell_persistence"))
    if buy_belief >= sell_belief:
        return buy_belief, buy_persistence, sell_belief, sell_persistence
    return sell_belief, sell_persistence, buy_belief, buy_persistence


def _anchor_context(row: Mapping[str, Any], belief_state: Mapping[str, Any], acting_side: str) -> str:
    position_count = int(_to_float(row.get("my_position_count"), 0.0))
    dominant_side = _to_text(belief_state.get("dominant_side")).upper()
    flip_readiness = _to_float(belief_state.get("flip_readiness"))
    instability = _to_float(belief_state.get("belief_instability"))
    if position_count > 0:
        if acting_side in {"BUY", "SELL"} and dominant_side in {"BUY", "SELL"}:
            if acting_side != dominant_side and flip_readiness >= 0.55:
                return "flip_thesis"
        if flip_readiness >= 0.62 and instability >= 0.45 and dominant_side in {"BUY", "SELL"}:
            return "flip_thesis"
        return "hold_thesis"
    return "entry_thesis"


def _persistence_hint(
    *,
    active_persistence: float,
    opposite_persistence: float,
    flip_readiness: float,
    instability: float,
) -> str:
    if flip_readiness >= 0.62 and instability >= 0.45:
        return "FLIP_READY"
    if active_persistence >= 0.38 and instability <= 0.45:
        return "STABLE"
    if active_persistence < 0.24 or instability >= 0.60:
        return "UNSTABLE"
    if opposite_persistence > active_persistence:
        return "DECAYING"
    return "BALANCED"


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


def _forecast_expected_path(summary: Mapping[str, Any]) -> str:
    decision_hint = _to_text(summary.get("decision_hint")).upper()
    confirm_side = _to_text(summary.get("confirm_side")).upper()
    confirm_score = _to_float(summary.get("confirm_score"))
    false_break_score = _to_float(summary.get("false_break_score"))
    continuation_score = _to_float(summary.get("continuation_score"))
    continue_favor_score = _to_float(summary.get("continue_favor_score"))
    fail_now_score = _to_float(summary.get("fail_now_score"))
    wait_confirm_gap = _to_float(summary.get("wait_confirm_gap"))
    hold_exit_gap = _to_float(summary.get("hold_exit_gap"))

    if false_break_score >= max(confirm_score, continuation_score, 0.55):
        return "failed_break"
    if confirm_side in {"BUY", "SELL"} and continuation_score >= max(false_break_score, 0.45):
        if continue_favor_score >= fail_now_score:
            return "continuation"
    if decision_hint == "WAIT_BIASED" or wait_confirm_gap <= -0.15:
        return "wait_then_confirm"
    if decision_hint == "FAST_EXIT_BIASED" or hold_exit_gap <= -0.12:
        return "fragile_hold"
    return "balanced"


def _forecast_reason_codes(summary: Mapping[str, Any]) -> str:
    tokens: list[str] = []
    decision_hint = _to_text(summary.get("decision_hint")).upper()
    confirm_side = _to_text(summary.get("confirm_side")).upper()
    if decision_hint:
        tokens.append(decision_hint.lower())
    if confirm_side in {"BUY", "SELL"}:
        tokens.append(f"{confirm_side.lower()}_confirm")
    if _to_float(summary.get("false_break_score")) >= 0.55:
        tokens.append("false_break_risk")
    if _to_float(summary.get("continue_favor_score")) >= 0.60:
        tokens.append("continue_favor")
    if _to_float(summary.get("fail_now_score")) >= 0.55:
        tokens.append("fail_now_risk")
    return "|".join(tokens[:4])


def _dominant_evidence_family(side: str, evidence: Mapping[str, Any]) -> str:
    side_upper = str(side).upper()
    if side_upper == "BUY":
        continuation = _to_float(evidence.get("buy_continuation_evidence"))
        reversal = _to_float(evidence.get("buy_reversal_evidence"))
    elif side_upper == "SELL":
        continuation = _to_float(evidence.get("sell_continuation_evidence"))
        reversal = _to_float(evidence.get("sell_reversal_evidence"))
    else:
        continuation = max(
            _to_float(evidence.get("buy_continuation_evidence")),
            _to_float(evidence.get("sell_continuation_evidence")),
        )
        reversal = max(
            _to_float(evidence.get("buy_reversal_evidence")),
            _to_float(evidence.get("sell_reversal_evidence")),
        )
    if continuation >= max(reversal + 0.08, 0.20):
        return "CONTINUATION"
    if reversal >= max(continuation + 0.08, 0.20):
        return "REVERSAL"
    if max(continuation, reversal) <= 0.12:
        return "WEAK"
    return "MIXED"


def _evidence_total(side: str, evidence: Mapping[str, Any]) -> float:
    side_upper = str(side).upper()
    if side_upper == "BUY":
        return _to_float(evidence.get("buy_total_evidence"))
    if side_upper == "SELL":
        return _to_float(evidence.get("sell_total_evidence"))
    return max(_to_float(evidence.get("buy_total_evidence")), _to_float(evidence.get("sell_total_evidence")))


def _evidence_conflict(evidence: Mapping[str, Any]) -> float:
    buy_total = _to_float(evidence.get("buy_total_evidence"))
    sell_total = _to_float(evidence.get("sell_total_evidence"))
    denominator = max(buy_total, sell_total, 0.10)
    return max(0.0, min(1.0, 1.0 - (abs(buy_total - sell_total) / denominator)))


def _evidence_fragility(side: str, evidence: Mapping[str, Any]) -> float:
    side_upper = str(side).upper()
    if side_upper == "BUY":
        continuation = _to_float(evidence.get("buy_continuation_evidence"))
        reversal = _to_float(evidence.get("buy_reversal_evidence"))
        total = _to_float(evidence.get("buy_total_evidence"))
    elif side_upper == "SELL":
        continuation = _to_float(evidence.get("sell_continuation_evidence"))
        reversal = _to_float(evidence.get("sell_reversal_evidence"))
        total = _to_float(evidence.get("sell_total_evidence"))
    else:
        continuation = max(
            _to_float(evidence.get("buy_continuation_evidence")),
            _to_float(evidence.get("sell_continuation_evidence")),
        )
        reversal = max(
            _to_float(evidence.get("buy_reversal_evidence")),
            _to_float(evidence.get("sell_reversal_evidence")),
        )
        total = max(_to_float(evidence.get("buy_total_evidence")), _to_float(evidence.get("sell_total_evidence")))
    denominator = max(total, 0.10)
    return max(0.0, min(1.0, 1.0 - (abs(continuation - reversal) / denominator)))


def _barrier_primary_component(side: str, barrier: Mapping[str, Any]) -> tuple[str, float]:
    side_upper = str(side).upper()
    candidates = {
        "conflict_barrier": _to_float(barrier.get("conflict_barrier")),
        "middle_chop_barrier": _to_float(barrier.get("middle_chop_barrier")),
        "direction_policy_barrier": _to_float(barrier.get("direction_policy_barrier")),
        "liquidity_barrier": _to_float(barrier.get("liquidity_barrier")),
    }
    if side_upper == "BUY":
        candidates["side_barrier"] = _to_float(barrier.get("buy_barrier"))
    elif side_upper == "SELL":
        candidates["side_barrier"] = _to_float(barrier.get("sell_barrier"))
    else:
        candidates["side_barrier"] = max(
            _to_float(barrier.get("buy_barrier")),
            _to_float(barrier.get("sell_barrier")),
        )
    component = max(candidates.items(), key=lambda item: item[1])
    return str(component[0]), float(component[1])


def build_belief_runtime_summary_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    belief_state = _coerce_mapping(payload.get("belief_state_v1"))
    if not belief_state:
        return {
            "contract_version": BELIEF_RUNTIME_SUMMARY_CONTRACT_VERSION,
            "available": False,
            "acting_side": "",
            "anchor_context": "",
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "active_belief": 0.0,
            "active_persistence": 0.0,
            "opposite_belief": 0.0,
            "opposite_persistence": 0.0,
            "belief_spread": 0.0,
            "flip_readiness": 0.0,
            "belief_instability": 0.0,
            "transition_age": 0,
            "persistence_hint": "UNAVAILABLE",
            "reason_summary": "belief_missing",
        }

    acting_side = _active_side_from_row(payload, belief_state)
    active_belief, active_persistence, opposite_belief, opposite_persistence = _active_pair(acting_side, belief_state)
    dominant_side = _pick_text(belief_state.get("dominant_side"), "BALANCED").upper()
    dominant_mode = _pick_text(belief_state.get("dominant_mode"), "balanced").lower()
    flip_readiness = _to_float(belief_state.get("flip_readiness"))
    instability = _to_float(belief_state.get("belief_instability"))
    anchor_context = _anchor_context(payload, belief_state, acting_side)
    persistence_hint = _persistence_hint(
        active_persistence=active_persistence,
        opposite_persistence=opposite_persistence,
        flip_readiness=flip_readiness,
        instability=instability,
    )
    reason_summary = "|".join(
        token
        for token in (
            acting_side.lower() if acting_side else "",
            dominant_side.lower() if dominant_side else "",
            dominant_mode,
            anchor_context,
            persistence_hint.lower(),
        )
        if token
    )
    return {
        "contract_version": BELIEF_RUNTIME_SUMMARY_CONTRACT_VERSION,
        "available": True,
        "acting_side": acting_side,
        "anchor_context": anchor_context,
        "dominant_side": dominant_side,
        "dominant_mode": dominant_mode,
        "active_belief": round(float(active_belief), 6),
        "active_persistence": round(float(active_persistence), 6),
        "opposite_belief": round(float(opposite_belief), 6),
        "opposite_persistence": round(float(opposite_persistence), 6),
        "belief_spread": round(_to_float(belief_state.get("belief_spread")), 6),
        "flip_readiness": round(float(flip_readiness), 6),
        "belief_instability": round(float(instability), 6),
        "transition_age": int(_to_float(belief_state.get("transition_age"), 0.0)),
        "persistence_hint": persistence_hint,
        "reason_summary": reason_summary,
    }


def build_belief_input_trace_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    belief_summary = build_belief_runtime_summary_v1(payload)
    if not belief_summary.get("available", False):
        return {
            "contract_version": BELIEF_INPUT_TRACE_CONTRACT_VERSION,
            "available": False,
            "reason_summary": "belief_missing",
        }

    scene_hint = _scene_hint(payload)
    forecast_summary = _forecast_hint(payload)
    evidence = _coerce_mapping(payload.get("evidence_vector_v1"))
    barrier = _coerce_mapping(payload.get("barrier_state_v1"))
    acting_side = _to_text(belief_summary.get("acting_side")).upper()
    primary_component, barrier_total_hint = _barrier_primary_component(acting_side, barrier)
    forecast_confidence = max(
        _to_float(forecast_summary.get("confirm_score")),
        _to_float(forecast_summary.get("continuation_score")),
        _to_float(forecast_summary.get("false_break_score")),
        _to_float(forecast_summary.get("continue_favor_score")),
        _to_float(forecast_summary.get("fail_now_score")),
    )
    dominant_evidence_family = _dominant_evidence_family(acting_side, evidence)
    evidence_total = _evidence_total(acting_side, evidence)
    evidence_conflict = _evidence_conflict(evidence)
    evidence_fragility = _evidence_fragility(acting_side, evidence)
    reason_summary = "|".join(
        token
        for token in (
            _to_text(scene_hint.get("scene_pattern_name")),
            _forecast_expected_path(forecast_summary),
            dominant_evidence_family.lower(),
            str(primary_component or "").lower(),
        )
        if token
    )
    return {
        "contract_version": BELIEF_INPUT_TRACE_CONTRACT_VERSION,
        "available": True,
        "scene_id": int(_to_float(scene_hint.get("scene_pattern_id"), 0.0)),
        "state25_label": _to_text(scene_hint.get("scene_pattern_name")),
        "state25_confidence": round(_to_float(scene_hint.get("confidence")), 6),
        "forecast_expected_path": _forecast_expected_path(forecast_summary),
        "forecast_confidence": round(float(forecast_confidence), 6),
        "forecast_reason_codes": _forecast_reason_codes(forecast_summary),
        "dominant_evidence_family": dominant_evidence_family,
        "evidence_total": round(float(evidence_total), 6),
        "evidence_conflict": round(float(evidence_conflict), 6),
        "evidence_fragility": round(float(evidence_fragility), 6),
        "barrier_total_hint": round(float(barrier_total_hint), 6),
        "barrier_primary_component": primary_component,
        "reason_summary": reason_summary,
    }


def build_belief_action_hint_v1(
    row: Mapping[str, Any] | None,
    *,
    belief_runtime_summary_v1: Mapping[str, Any] | None = None,
    belief_input_trace_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(row or {})
    belief_summary = _coerce_mapping(belief_runtime_summary_v1)
    if not belief_summary:
        belief_summary = build_belief_runtime_summary_v1(payload)
    belief_trace = _coerce_mapping(belief_input_trace_v1)
    if not belief_trace:
        belief_trace = build_belief_input_trace_v1(payload)

    available = bool(
        belief_summary.get("available", False)
        and belief_trace.get("available", False)
    )
    if not available:
        return {
            "contract_version": BELIEF_ACTION_HINT_CONTRACT_VERSION,
            "available": False,
            "enabled": False,
            "hint_mode": "observe_only",
            "recommended_family": "observe_only",
            "supporting_label_candidate": "",
            "overlay_confidence": "low",
            "reason_summary": "belief_hint_unavailable",
        }

    anchor_context = _to_text(belief_summary.get("anchor_context")).lower()
    active_persistence = _to_float(belief_summary.get("active_persistence"))
    flip_readiness = _to_float(belief_summary.get("flip_readiness"))
    instability = _to_float(belief_summary.get("belief_instability"))
    persistence_hint = _to_text(belief_summary.get("persistence_hint")).upper()

    forecast_expected_path = _to_text(belief_trace.get("forecast_expected_path")).lower()
    dominant_evidence_family = _to_text(belief_trace.get("dominant_evidence_family")).upper()
    evidence_conflict = _to_float(belief_trace.get("evidence_conflict"))
    evidence_fragility = _to_float(belief_trace.get("evidence_fragility"))
    barrier_total_hint = _to_float(belief_trace.get("barrier_total_hint"))
    barrier_primary_component = _to_text(belief_trace.get("barrier_primary_component"))

    recommended_family = "observe_only"
    supporting_label_candidate = ""
    reason_tokens: list[str] = []

    if (
        anchor_context == "flip_thesis"
        and flip_readiness >= 0.62
        and barrier_total_hint <= 0.55
    ):
        recommended_family = "flip_alert"
        supporting_label_candidate = "correct_flip"
        reason_tokens.extend(("flip_ready", "flip_thesis"))
    elif (
        flip_readiness >= 0.58
        and dominant_evidence_family in {"REVERSAL", "MIXED"}
        and barrier_total_hint <= 0.45
    ):
        recommended_family = "flip_alert"
        supporting_label_candidate = (
            "correct_flip" if anchor_context == "flip_thesis" else "missed_flip"
        )
        reason_tokens.extend(("flip_pressure", "reversal_evidence"))
    elif (
        anchor_context == "flip_thesis"
        and flip_readiness <= 0.38
        and active_persistence >= 0.34
        and dominant_evidence_family == "CONTINUATION"
    ):
        recommended_family = "wait_bias"
        supporting_label_candidate = "premature_flip"
        reason_tokens.extend(("flip_not_confirmed", "continuation_reclaim"))
    elif (
        active_persistence < 0.24
        or instability >= 0.60
        or (forecast_expected_path == "fragile_hold" and evidence_fragility >= 0.55)
    ):
        recommended_family = "reduce_alert"
        supporting_label_candidate = "wrong_hold"
        reason_tokens.extend(("fragile_thesis", "reduce_risk"))
    elif (
        forecast_expected_path == "wait_then_confirm"
        and barrier_total_hint >= 0.40
        and active_persistence >= 0.26
    ):
        recommended_family = "wait_bias"
        supporting_label_candidate = "correct_hold"
        reason_tokens.extend(("wait_then_confirm", "barrier_wait_value"))
    elif (
        active_persistence >= 0.38
        and instability <= 0.45
        and evidence_conflict <= 0.52
    ):
        recommended_family = "hold_bias"
        supporting_label_candidate = "correct_hold"
        reason_tokens.extend(("stable_hold", persistence_hint.lower()))

    enabled = recommended_family != "observe_only"
    if not enabled:
        overlay_confidence = "low"
        if not reason_tokens:
            reason_tokens.append("observe_only")
    elif recommended_family == "hold_bias":
        overlay_confidence = (
            "high"
            if active_persistence >= 0.46 and instability <= 0.30 and evidence_conflict <= 0.35
            else "medium"
        )
    elif recommended_family == "flip_alert":
        overlay_confidence = (
            "high"
            if flip_readiness >= 0.68 and barrier_total_hint <= 0.35
            else "medium"
        )
    elif recommended_family == "reduce_alert":
        overlay_confidence = (
            "high"
            if instability >= 0.68 or active_persistence <= 0.16
            else "medium"
        )
    else:
        overlay_confidence = (
            "high"
            if barrier_total_hint >= 0.50 and forecast_expected_path == "wait_then_confirm"
            else "medium"
        )

    return {
        "contract_version": BELIEF_ACTION_HINT_CONTRACT_VERSION,
        "available": True,
        "enabled": enabled,
        "hint_mode": "log_only" if enabled else "observe_only",
        "recommended_family": recommended_family,
        "supporting_label_candidate": supporting_label_candidate,
        "overlay_confidence": overlay_confidence,
        "active_persistence": round(float(active_persistence), 6),
        "flip_readiness": round(float(flip_readiness), 6),
        "belief_instability": round(float(instability), 6),
        "forecast_expected_path": forecast_expected_path,
        "dominant_evidence_family": dominant_evidence_family,
        "barrier_primary_component": barrier_primary_component,
        "barrier_total_hint": round(float(barrier_total_hint), 6),
        "reason_summary": "|".join(reason_tokens[:4]),
    }


def build_belief_state25_runtime_bridge_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    scene_hint = _scene_hint(payload)
    belief_summary = build_belief_runtime_summary_v1(payload)
    belief_input_trace = build_belief_input_trace_v1(
        {
            **payload,
            "forecast_state25_runtime_bridge_v1": {
                **_coerce_mapping(payload.get("forecast_state25_runtime_bridge_v1")),
                "state25_runtime_hint_v1": scene_hint,
            },
        }
    )
    belief_action_hint = build_belief_action_hint_v1(
        payload,
        belief_runtime_summary_v1=belief_summary,
        belief_input_trace_v1=belief_input_trace,
    )
    return {
        "contract_version": BELIEF_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION,
        "scope_freeze_contract_version": BELIEF_SCOPE_FREEZE_CONTRACT_VERSION,
        "scene_source": _to_text(scene_hint.get("scene_source")) or "teacher_pattern_rule_runtime_hint_v1",
        "state25_runtime_hint_v1": scene_hint,
        "belief_runtime_summary_v1": belief_summary,
        "belief_input_trace_v1": belief_input_trace,
        "belief_action_hint_v1": belief_action_hint,
    }
