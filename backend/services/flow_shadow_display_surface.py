from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


FLOW_SHADOW_DISPLAY_SURFACE_CONTRACT_VERSION = "flow_shadow_display_surface_contract_v1"
FLOW_SHADOW_DISPLAY_SURFACE_SUMMARY_VERSION = "flow_shadow_display_surface_summary_v1"

FLOW_SHADOW_MARKER_STATE_ENUM_V1 = (
    "NONE",
    "EXISTING_WATCH",
    "FALLBACK_START_WATCH",
)
FLOW_SHADOW_ENTRY_ZONE_STATE_ENUM_V1 = (
    "NEUTRAL",
    "FAVORABLE_EDGE",
    "MID_PULLBACK",
    "OPPOSITE_EDGE_CHASE",
    "BREAKOUT_CONTINUATION",
    "BREAKOUT_LATE_RISK",
)
FLOW_SHADOW_CHART_EVENT_OVERRIDE_STATE_ENUM_V1 = (
    "NONE",
    "UNCHANGED",
    "OVERRIDDEN_TO_WAIT",
    "OVERRIDDEN_TO_PROBE",
)
FLOW_SHADOW_CHART_EVENT_EMIT_STATE_ENUM_V1 = (
    "NONE",
    "START_WATCH",
    "EDGE_WATCH",
    "TURN_WAIT",
    "BREAKOUT_PROBE",
    "SUPPRESSED",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value or {})
    if isinstance(value, str):
        text = str(value or "").strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = {}
            return dict(parsed or {}) if isinstance(parsed, Mapping) else {}
    return {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = 0.0
    return max(0.0, min(1.0, parsed))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _effective_flow_state(row: Mapping[str, Any] | None) -> str:
    payload = _mapping(row)
    xau_effective = _text(payload.get("xau_gate_effective_flow_support_state_v1")).upper()
    if xau_effective:
        return xau_effective
    return _text(payload.get("flow_support_state_v1")).upper()


def _effective_conviction(row: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    values = [
        _float(payload.get("aggregate_conviction_v1"), 0.0),
        _float(payload.get("xau_gate_effective_aggregate_conviction_v1"), 0.0),
    ]
    return round(max(values), 4)


def _effective_persistence(row: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    values = [
        _float(payload.get("flow_persistence_v1"), 0.0),
        _float(payload.get("xau_gate_effective_flow_persistence_v1"), 0.0),
    ]
    return round(max(values), 4)


def _resolve_direction(row: Mapping[str, Any] | None) -> tuple[str, str]:
    payload = _mapping(row)
    consumer_state = _json_mapping(payload.get("consumer_check_state_v1"))
    consumer_side = _text(
        consumer_state.get("check_side") or payload.get("consumer_check_side")
    ).upper()
    consumer_stage = _text(
        consumer_state.get("check_stage") or payload.get("consumer_check_stage")
    ).upper()
    consumer_entry_ready = bool(
        consumer_state.get("entry_ready", payload.get("consumer_check_entry_ready", False))
    )
    consumer_chart_hint = _text(consumer_state.get("chart_event_kind_hint")).upper()
    consumer_chart_reason = _text(consumer_state.get("chart_display_reason")).lower()
    overlay_enabled = bool(payload.get("directional_continuation_overlay_enabled", False))
    overlay_side = _text(payload.get("directional_continuation_overlay_side")).upper()
    if (
        consumer_side in {"BUY", "SELL"}
        and consumer_stage in {"OBSERVE", "BLOCKED", "PROBE", "READY"}
        and overlay_enabled
        and overlay_side in {"BUY", "SELL"}
        and overlay_side != consumer_side
    ):
        explicit_consumer_wait = bool(
            consumer_chart_hint == "WAIT"
            and not consumer_entry_ready
            and (
                "wait_as_wait" in consumer_chart_reason
                or "promotion_wait" in consumer_chart_reason
                or "wait_checks" in consumer_chart_reason
            )
        )
        if explicit_consumer_wait:
            return consumer_side, "CONSUMER_WAIT_OVERRIDE"
    if overlay_enabled and overlay_side in {"BUY", "SELL"}:
        return overlay_side, "OVERLAY"

    if consumer_side in {"BUY", "SELL"} and consumer_stage in {"OBSERVE", "BLOCKED", "PROBE", "READY"}:
        return consumer_side, "CONSUMER"

    action = _text(payload.get("action")).upper()
    if action in {"BUY", "SELL"}:
        return action, "ACTION"
    return "NONE", "NONE"


def _score_label(value: float) -> str:
    score = _clamp01(value)
    if score >= 0.67:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    return "LOW"


def _append_unique(items: list[str], value: str) -> None:
    value_n = _text(value).upper()
    if value_n and value_n not in items:
        items.append(value_n)


def _position_zones(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    position_snapshot = _json_mapping(payload.get("position_snapshot_v2"))
    return _json_mapping(position_snapshot.get("zones"))


def _zone_value(row: Mapping[str, Any] | None, key: str) -> str:
    zones = _position_zones(row)
    return _text(zones.get(str(key or ""))).upper()


def _entry_zone_state(
    row: Mapping[str, Any] | None,
    *,
    direction: str,
    continuation_prob: float,
) -> tuple[str, list[str], str]:
    payload = _mapping(row)
    reason = _text(payload.get("consumer_check_reason")).lower()
    box_zone = _zone_value(payload, "box_zone") or _text(payload.get("box_state")).upper()
    bb20_zone = _zone_value(payload, "bb20_zone")
    previous_break_state = _text(payload.get("previous_box_break_state")).upper()
    previous_relation = _text(payload.get("previous_box_relation")).upper()
    breakout_direction = _text(payload.get("breakout_candidate_direction")).upper()
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    overlay_direction = _text(payload.get("directional_continuation_overlay_direction")).upper()
    late_chase_state = _text(payload.get("late_chase_risk_state")).upper()

    favorable_edge = False
    opposite_edge = False
    mid_pullback = bool(
        box_zone in {"MIDDLE", "MID"}
        or bb20_zone in {"MIDDLE", "MID"}
        or any(token in reason for token in ("mid_reclaim", "pullback", "anchor_required"))
    )
    breakout_context = False

    if direction == "BUY":
        favorable_edge = bool(
            box_zone in {"BELOW", "LOWER", "LOWER_EDGE"}
            or bb20_zone in {"LOWER_EDGE", "BREAKDOWN"}
            or any(token in reason for token in ("lower_", "rebound", "reclaim"))
        )
        opposite_edge = bool(
            box_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
            or bb20_zone in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
            or any(token in reason for token in ("upper_", "outer_band", "boundary"))
        )
        breakout_context = bool(
            previous_break_state in {"BREAKOUT_HELD", "RECLAIMED"}
            and previous_relation in {"ABOVE", "AT_HIGH"}
            and (
                breakout_direction == "UP"
                or overlay_direction == "UP"
                or breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
            )
        )
    elif direction == "SELL":
        favorable_edge = bool(
            box_zone in {"ABOVE", "UPPER", "UPPER_EDGE"}
            or bb20_zone in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
            or any(token in reason for token in ("upper_", "reject", "resistance"))
        )
        opposite_edge = bool(
            box_zone in {"BELOW", "LOWER", "LOWER_EDGE"}
            or bb20_zone in {"LOWER_EDGE", "BREAKDOWN"}
            or any(token in reason for token in ("lower_", "breakdown", "boundary"))
        )
        breakout_context = bool(
            previous_break_state in {"BREAKOUT_HELD", "RECLAIMED"}
            and previous_relation in {"BELOW", "AT_LOW"}
            and (
                breakout_direction == "DOWN"
                or overlay_direction == "DOWN"
                or breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
            )
        )

    breakout_late_risk = bool(
        breakout_context
        and (
            late_chase_state in {"HIGH", "MEDIUM", "EARLY_WARNING"}
            or opposite_edge
            or any(token in reason for token in ("outer_band", "boundary", "reversal_support_required"))
        )
    )
    breakout_continuation = bool(
        breakout_context
        and not breakout_late_risk
        and continuation_prob >= 0.58
    )

    zone_state = "NEUTRAL"
    if breakout_late_risk:
        zone_state = "BREAKOUT_LATE_RISK"
    elif breakout_continuation:
        zone_state = "BREAKOUT_CONTINUATION"
    elif favorable_edge:
        zone_state = "FAVORABLE_EDGE"
    elif mid_pullback:
        zone_state = "MID_PULLBACK"
    elif opposite_edge:
        zone_state = "OPPOSITE_EDGE_CHASE"

    caution_flags: list[str] = []
    if favorable_edge:
        _append_unique(caution_flags, "FAVORABLE_EDGE")
    if mid_pullback:
        _append_unique(caution_flags, "MID_PULLBACK")
    if opposite_edge:
        _append_unique(caution_flags, "OPPOSITE_EDGE_CHASE")
    if breakout_context:
        _append_unique(caution_flags, "BREAKOUT_CONTINUATION_MODE")
    if breakout_late_risk:
        _append_unique(caution_flags, "BREAKOUT_LATE_RISK")
    if late_chase_state in {"HIGH", "MEDIUM", "EARLY_WARNING"} or any(
        token in reason for token in ("reversal", "outer_band")
    ):
        _append_unique(caution_flags, "TURN_RISK_RISING")
    if any(token in reason for token in ("boundary", "outer_band", "anchor_required", "reversal_support_required")):
        _append_unique(caution_flags, "BOUNDARY_FRICTION")

    reason_summary = (
        f"zone={zone_state}; direction={direction or 'NONE'}; "
        f"box={box_zone or 'NONE'}; bb20={bb20_zone or 'NONE'}; "
        f"prev={previous_break_state or 'NONE'}:{previous_relation or 'NONE'}; "
        f"late={late_chase_state or 'NONE'}; reason={reason or 'none'}"
    )
    return zone_state, caution_flags, reason_summary


def _continuation_persistence_prob(row: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    persistence = _effective_persistence(payload)
    overlay_score = _clamp01(payload.get("directional_continuation_overlay_score"))
    truth_state = _text(payload.get("flow_candidate_truth_state_v1")).upper()
    verdict = _text(payload.get("flow_candidate_improvement_verdict_v1")).upper()
    feedback = _text(payload.get("bounded_candidate_feedback_loop_action_v1")).upper()
    structure_gate = _text(payload.get("flow_structure_gate_v1")).upper()
    flow_state = _effective_flow_state(payload)
    audit_state = _text(payload.get("nas_btc_hard_opposed_truth_audit_state_v1")).upper()
    reason = _text(payload.get("consumer_check_reason")).lower()
    stage = _text(payload.get("consumer_check_stage")).upper()
    chart_hint = _text(payload.get("chart_event_kind_hint")).upper()

    score = (persistence * 0.45) + (overlay_score * 0.30)
    score += {
        "FLOW_CONFIRMED": 0.22,
        "FLOW_BUILDING": 0.15,
        "FLOW_UNCONFIRMED": 0.06,
        "FLOW_OPPOSED": -0.10,
    }.get(flow_state, 0.0)
    score += {"ELIGIBLE": 0.06, "WEAK": 0.02, "INELIGIBLE": -0.04}.get(structure_gate, 0.0)
    if truth_state == "WIDEN_EXPECTED":
        score += 0.12
    if verdict in {"OVER_TIGHTENED", "MISSED_IMPROVEMENT"}:
        score += 0.10
    if feedback == "KEEP_SHADOW":
        score += 0.08
    elif feedback == "KEEP_REVIEW":
        score += 0.04
    if any(token in reason for token in ("rebound", "reclaim", "probe_observe", "buy_watch", "sell_watch")):
        score += 0.06
    if stage in {"OBSERVE", "PROBE"}:
        score += 0.05
    elif stage == "BLOCKED":
        score += 0.03
    if chart_hint in {"BUY_WATCH", "SELL_WATCH"}:
        score += 0.08
    if audit_state == "FIXED_HARD_OPPOSED":
        score -= 0.20
    elif audit_state == "MIXED_REVIEW":
        score -= 0.05
    return round(_clamp01(score), 4)


def _entry_quality_prob(
    row: Mapping[str, Any] | None,
    continuation_prob: float,
    *,
    zone_state: str,
    caution_flags: tuple[str, ...],
) -> float:
    payload = _mapping(row)
    conviction = _effective_conviction(payload)
    overlay_score = _clamp01(payload.get("directional_continuation_overlay_score"))
    flow_state = _effective_flow_state(payload)
    stage = _text(payload.get("consumer_check_stage")).upper()
    feedback = _text(payload.get("bounded_candidate_feedback_loop_action_v1")).upper()
    chart_hint = _text(payload.get("chart_event_kind_hint")).upper()
    reason = _text(payload.get("consumer_check_reason")).lower()
    late_chase_state = _text(payload.get("late_chase_risk_state")).upper()

    score = (continuation_prob * 0.45) + (conviction * 0.20) + (overlay_score * 0.20)
    score += {"READY": 0.12, "PROBE": 0.08, "OBSERVE": 0.02, "BLOCKED": -0.03}.get(stage, 0.0)
    score += {"KEEP_SHADOW": 0.05, "KEEP_REVIEW": 0.0}.get(feedback, 0.0)
    score += {"FLOW_CONFIRMED": 0.08, "FLOW_BUILDING": 0.04, "FLOW_OPPOSED": -0.02}.get(flow_state, 0.0)
    score += {
        "FAVORABLE_EDGE": 0.10,
        "MID_PULLBACK": 0.04,
        "BREAKOUT_CONTINUATION": 0.06,
        "OPPOSITE_EDGE_CHASE": -0.18,
        "BREAKOUT_LATE_RISK": -0.22,
    }.get(_text(zone_state).upper(), 0.0)
    if any(token in reason for token in ("outer_band", "reversal_support_required", "boundary")):
        score -= 0.04
    if late_chase_state == "HIGH":
        score -= 0.18
    elif late_chase_state in {"MEDIUM", "EARLY_WARNING"}:
        score -= 0.08
    if "TURN_RISK_RISING" in caution_flags:
        score -= 0.05
    if "BOUNDARY_FRICTION" in caution_flags:
        score -= 0.03
    score = _clamp01(score)
    exceptional_upper_chase = bool(
        continuation_prob >= 0.74
        and conviction >= 0.32
        and overlay_score >= 0.78
    )
    if chart_hint in {"BUY_WATCH", "SELL_WATCH"}:
        zone_state_u = _text(zone_state).upper()
        if zone_state_u == "BREAKOUT_CONTINUATION":
            score = min(score, 0.62)
        elif zone_state_u == "FAVORABLE_EDGE":
            score = min(score, 0.58)
        elif zone_state_u == "MID_PULLBACK":
            score = min(score, 0.52)
        elif zone_state_u == "OPPOSITE_EDGE_CHASE":
            score = min(score, 0.34 if exceptional_upper_chase else 0.18)
        elif zone_state_u == "BREAKOUT_LATE_RISK":
            score = min(score, 0.22)
        else:
            score = min(score, 0.45)
    return round(score, 4)


def _reversal_risk_prob(
    row: Mapping[str, Any] | None,
    *,
    continuation_prob: float,
    conviction: float,
) -> float:
    payload = _mapping(row)
    overlay_score = _clamp01(payload.get("directional_continuation_overlay_score"))
    flow_state = _effective_flow_state(payload)
    structure_gate = _text(payload.get("flow_structure_gate_v1")).upper()
    audit_state = _text(payload.get("nas_btc_hard_opposed_truth_audit_state_v1")).upper()
    truth_state = _text(payload.get("flow_candidate_truth_state_v1")).upper()
    verdict = _text(payload.get("flow_candidate_improvement_verdict_v1")).upper()
    stage = _text(payload.get("consumer_check_stage")).upper()
    reason = _text(payload.get("consumer_check_reason")).lower()
    late_chase_state = _text(payload.get("late_chase_risk_state")).upper()

    score = 0.35
    score += {"FLOW_OPPOSED": 0.18, "FLOW_UNCONFIRMED": 0.08}.get(flow_state, 0.0)
    if structure_gate == "INELIGIBLE":
        score += 0.12
    if audit_state == "FIXED_HARD_OPPOSED":
        score += 0.14
    elif audit_state == "MIXED_REVIEW":
        score += 0.05
    if stage == "BLOCKED":
        score += 0.05
    if any(token in reason for token in ("outer_band", "reversal", "boundary")):
        score += 0.08
    if late_chase_state == "HIGH":
        score += 0.10
    elif late_chase_state in {"MEDIUM", "EARLY_WARNING"}:
        score += 0.05
    score -= overlay_score * 0.20
    score -= continuation_prob * 0.18
    score -= conviction * 0.10
    if truth_state == "WIDEN_EXPECTED" and verdict == "OVER_TIGHTENED":
        score -= 0.10
    return round(_clamp01(score), 4)


def _marker_state(
    row: Mapping[str, Any] | None,
    *,
    direction: str,
    continuation_prob: float,
    reversal_risk_prob: float,
) -> tuple[str, str, str]:
    payload = _mapping(row)
    existing_hint = _text(payload.get("chart_event_kind_hint")).upper()
    if existing_hint in {"BUY_WATCH", "SELL_WATCH"}:
        return "EXISTING_WATCH", existing_hint, "existing_chart_watch_hint"

    truth_state = _text(payload.get("flow_candidate_truth_state_v1")).upper()
    verdict = _text(payload.get("flow_candidate_improvement_verdict_v1")).upper()
    feedback = _text(payload.get("bounded_candidate_feedback_loop_action_v1")).upper()

    if direction not in {"BUY", "SELL"}:
        return "NONE", "", "direction_unavailable"
    if continuation_prob < 0.28:
        return "NONE", "", "continuation_shadow_too_low"
    if reversal_risk_prob >= 0.68:
        return "NONE", "", "reversal_risk_shadow_too_high"
    if truth_state != "WIDEN_EXPECTED" and verdict not in {"OVER_TIGHTENED", "MISSED_IMPROVEMENT"}:
        return "NONE", "", "no_widening_pressure"
    if feedback not in {"KEEP_REVIEW", "KEEP_SHADOW"}:
        return "NONE", "", "candidate_feedback_not_ready"
    return "FALLBACK_START_WATCH", f"{direction}_WATCH", "shadow_widening_watch_start"


def _consumer_wait_chart_kind(row: Mapping[str, Any] | None) -> tuple[str, str]:
    payload = _mapping(row)
    state = _json_mapping(payload.get("consumer_check_state_v1"))
    hint = _text(state.get("chart_event_kind_hint")).upper()
    side = _text(state.get("check_side") or payload.get("consumer_check_side")).upper()
    stage = _text(state.get("check_stage") or payload.get("consumer_check_stage")).upper()
    entry_ready = bool(state.get("entry_ready", payload.get("consumer_check_entry_ready", False)))
    reason = _text(state.get("chart_display_reason")).strip().lower()
    if hint != "WAIT" or side not in {"BUY", "SELL"}:
        return "", ""
    if entry_ready:
        return "", ""
    if stage not in {"OBSERVE", "PROBE", "BLOCKED", "READY"}:
        return "", ""
    return f"{side}_WAIT", (reason or "consumer_wait_chart_hint")


def _resolve_chart_event_override(
    row: Mapping[str, Any] | None,
    *,
    direction: str,
    base_event_kind: str,
    zone_state: str,
    continuation_prob: float,
    entry_prob: float,
    reversal_risk_prob: float,
) -> tuple[str, str, str]:
    payload = _mapping(row)
    direction_u = _text(direction).upper()
    base_kind = _text(base_event_kind).upper()
    if direction_u not in {"BUY", "SELL"}:
        return base_kind, "NONE", "direction_unavailable"

    watch_kind = f"{direction_u}_WATCH"
    wait_kind = f"{direction_u}_WAIT"
    probe_kind = f"{direction_u}_PROBE"
    zone_state_u = _text(zone_state).upper()
    chart_hint = _text(payload.get("chart_event_kind_hint")).upper()

    if zone_state_u in {"OPPOSITE_EDGE_CHASE", "BREAKOUT_LATE_RISK"} and base_kind in {"", watch_kind, probe_kind}:
        return wait_kind, "OVERRIDDEN_TO_WAIT", f"{zone_state_u.lower()}_downgrade"
    if (
        zone_state_u == "BREAKOUT_CONTINUATION"
        and continuation_prob >= 0.58
        and entry_prob >= 0.24
        and reversal_risk_prob <= 0.42
        and base_kind in {"", watch_kind, wait_kind}
    ):
        return probe_kind, "OVERRIDDEN_TO_PROBE", "breakout_continuation_probe"
    if base_kind:
        return base_kind, "UNCHANGED", "base_chart_event_preserved"
    if chart_hint:
        return chart_hint, "UNCHANGED", "existing_chart_event_preserved"
    return "", "NONE", "no_chart_event_base"


def _resolve_chart_event_emission(
    *,
    direction: str,
    final_chart_kind: str,
    override_state: str,
    zone_state: str,
    marker_state: str,
    continuation_prob: float,
    entry_prob: float,
    reversal_risk_prob: float,
    caution_flags: tuple[str, ...],
) -> tuple[bool, str, str, str]:
    direction_u = _text(direction).upper()
    final_kind = _text(final_chart_kind).upper()
    override_state_u = _text(override_state).upper()
    zone_state_u = _text(zone_state).upper()
    marker_state_u = _text(marker_state).upper()
    if direction_u not in {"BUY", "SELL"} or not final_kind:
        return False, "NONE", "direction_or_chart_kind_unavailable", ""
    if override_state_u == "OVERRIDDEN_TO_WAIT":
        if zone_state_u == "OPPOSITE_EDGE_CHASE":
            if continuation_prob < 0.24 or reversal_risk_prob < 0.38:
                return False, "SUPPRESSED", "turn_wait_not_specific_enough", ""
        elif zone_state_u == "BREAKOUT_LATE_RISK":
            if continuation_prob < 0.30 or reversal_risk_prob < 0.26:
                return False, "SUPPRESSED", "late_breakout_wait_not_specific_enough", ""
        else:
            return False, "SUPPRESSED", "wait_without_specific_zone_transition", ""
        emit_key = f"{direction_u}|{final_kind}|{zone_state_u}|TURN_WAIT"
        return True, "TURN_WAIT", "late_risk_caution_transition", emit_key
    if override_state_u == "OVERRIDDEN_TO_PROBE":
        emit_key = f"{direction_u}|{final_kind}|{zone_state_u}|BREAKOUT_PROBE"
        return True, "BREAKOUT_PROBE", "clean_breakout_probe_transition", emit_key
    if marker_state_u == "FALLBACK_START_WATCH":
        if zone_state_u not in {"FAVORABLE_EDGE", "MID_PULLBACK", "BREAKOUT_CONTINUATION"}:
            return False, "SUPPRESSED", "fallback_watch_without_entry_edge", ""
        if continuation_prob < 0.24 or entry_prob < 0.10:
            return False, "SUPPRESSED", "fallback_watch_signal_too_weak", ""
        emit_key = f"{direction_u}|{final_kind}|START_WATCH"
        return True, "START_WATCH", "fallback_watch_start", emit_key
    if (
        final_kind in {f"{direction_u}_PROBE", f"{direction_u}_READY"}
        and zone_state_u in {"FAVORABLE_EDGE", "MID_PULLBACK", "BREAKOUT_CONTINUATION"}
        and continuation_prob >= 0.24
        and entry_prob >= 0.16
        and reversal_risk_prob <= 0.62
    ):
        emit_key = f"{direction_u}|{final_kind}|{zone_state_u}|POINT_CHECK"
        return True, "POINT_CHECK", "directional_entry_point_check", emit_key
    if (
        marker_state_u == "EXISTING_WATCH"
        and zone_state_u == "FAVORABLE_EDGE"
        and entry_prob >= 0.30
        and reversal_risk_prob <= 0.52
        and continuation_prob >= 0.32
    ):
        emit_key = f"{direction_u}|{final_kind}|EDGE_WATCH"
        return True, "EDGE_WATCH", "favorable_edge_watch_point", emit_key
    if "BOUNDARY_FRICTION" in caution_flags and zone_state_u in {"MID_PULLBACK", "OPPOSITE_EDGE_CHASE"}:
        return False, "SUPPRESSED", "boundary_friction_without_edge_trigger", ""
    return False, "SUPPRESSED", "not_specific_enough_for_chart_emit", ""


def _axis_summary(continuation_prob: float, entry_prob: float, reversal_prob: float) -> str:
    return (
        f"지속 {int(round(_clamp01(continuation_prob) * 100.0))}% / "
        f"진입 {int(round(_clamp01(entry_prob) * 100.0))}% / "
        f"반전 {int(round(_clamp01(reversal_prob) * 100.0))}%"
    )


def build_flow_shadow_display_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_SHADOW_DISPLAY_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only shadow display surface for Telegram and chart display. Splits directional flow into "
            "continuation persistence, fresh entry quality, and reversal risk, and emits a bounded watch-start marker."
        ),
        "row_level_fields_v1": [
            "flow_shadow_direction_v1",
            "flow_shadow_direction_source_v1",
            "flow_shadow_continuation_persistence_prob_v1",
            "flow_shadow_continuation_persistence_label_v1",
            "flow_shadow_entry_quality_prob_v1",
            "flow_shadow_entry_quality_label_v1",
            "flow_shadow_reversal_risk_prob_v1",
            "flow_shadow_reversal_risk_label_v1",
            "flow_shadow_entry_zone_state_v1",
            "flow_shadow_caution_flags_v1",
            "flow_shadow_zone_reason_summary_v1",
            "flow_shadow_axes_summary_v1",
            "flow_shadow_start_marker_state_v1",
            "flow_shadow_start_marker_event_kind_v1",
            "flow_shadow_start_marker_reason_v1",
            "flow_shadow_chart_event_base_kind_v1",
            "flow_shadow_chart_event_final_kind_v1",
            "flow_shadow_chart_event_override_state_v1",
            "flow_shadow_chart_event_override_reason_v1",
            "flow_shadow_chart_event_emit_v1",
            "flow_shadow_chart_event_emit_state_v1",
            "flow_shadow_chart_event_emit_reason_v1",
            "flow_shadow_chart_event_emit_key_v1",
            "flow_shadow_chart_event_ownership_v1",
            "flow_shadow_display_reason_summary_v1",
        ],
        "marker_state_enum_v1": list(FLOW_SHADOW_MARKER_STATE_ENUM_V1),
        "entry_zone_state_enum_v1": list(FLOW_SHADOW_ENTRY_ZONE_STATE_ENUM_V1),
        "chart_event_override_state_enum_v1": list(FLOW_SHADOW_CHART_EVENT_OVERRIDE_STATE_ENUM_V1),
        "chart_event_emit_state_enum_v1": list(FLOW_SHADOW_CHART_EVENT_EMIT_STATE_ENUM_V1),
        "control_rules_v1": [
            "The surface is read-only and must not mutate live execution or thresholds",
            "Shadow continuation can stay elevated even when flow_support_state_v1 is conservative",
            "Entry quality must remain distinct from continuation persistence",
            "Fallback chart watch markers may only be added when no explicit chart_event_kind_hint exists",
            "Upper-edge chase contexts must be downgraded to WAIT unless breakout continuation is exceptionally strong",
            "Breakout continuation may use PROBE instead of WATCH when the continuation context is clean enough",
            "Chart markers should only emit at start, edge, caution-turn, or breakout-transition points",
            "The surface is a display layer, not a new interpretation authority",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def attach_flow_shadow_display_surface_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(latest_signal_by_symbol or {}).items()}
    for symbol, row in rows.items():
        symbol_name = _text(row.get("symbol") or symbol).upper()
        direction, direction_source = _resolve_direction(row)
        conviction = _effective_conviction(row)
        continuation_prob = _continuation_persistence_prob(row)
        zone_state, caution_flags, zone_reason_summary = _entry_zone_state(
            row,
            direction=direction,
            continuation_prob=continuation_prob,
        )
        entry_prob = _entry_quality_prob(
            row,
            continuation_prob,
            zone_state=zone_state,
            caution_flags=tuple(caution_flags),
        )
        reversal_prob = _reversal_risk_prob(row, continuation_prob=continuation_prob, conviction=conviction)
        marker_state, marker_event_kind, marker_reason = _marker_state(
            row,
            direction=direction,
            continuation_prob=continuation_prob,
            reversal_risk_prob=reversal_prob,
        )
        existing_chart_kind = _text(row.get("chart_event_kind_hint")).upper()
        consumer_wait_chart_kind, consumer_wait_chart_reason = _consumer_wait_chart_kind(row)
        base_chart_kind = existing_chart_kind or (
            marker_event_kind if marker_state == "FALLBACK_START_WATCH" else ""
        )
        if consumer_wait_chart_kind and (
            not base_chart_kind
            or base_chart_kind in {
                "BUY_WATCH",
                "SELL_WATCH",
                "BUY_PROBE",
                "SELL_PROBE",
                "BUY_WAIT",
                "SELL_WAIT",
                "WAIT",
            }
        ):
            base_chart_kind = consumer_wait_chart_kind
        final_chart_kind, override_state, override_reason = _resolve_chart_event_override(
            row,
            direction=direction,
            base_event_kind=base_chart_kind,
            zone_state=zone_state,
            continuation_prob=continuation_prob,
            entry_prob=entry_prob,
            reversal_risk_prob=reversal_prob,
        )
        emit_chart_event, emit_state, emit_reason, emit_key = _resolve_chart_event_emission(
            direction=direction,
            final_chart_kind=final_chart_kind,
            override_state=override_state,
            zone_state=zone_state,
            marker_state=marker_state,
            continuation_prob=continuation_prob,
            entry_prob=entry_prob,
            reversal_risk_prob=reversal_prob,
            caution_flags=tuple(caution_flags),
        )

        if final_chart_kind:
            row["chart_event_kind_hint"] = final_chart_kind
            if override_state in {"OVERRIDDEN_TO_WAIT", "OVERRIDDEN_TO_PROBE"}:
                row["chart_event_reason_hint"] = override_reason
            elif (
                marker_state == "FALLBACK_START_WATCH"
                and not _text(row.get("chart_event_reason_hint"))
            ):
                row["chart_event_reason_hint"] = marker_reason

        row["flow_shadow_direction_v1"] = direction
        row["flow_shadow_direction_source_v1"] = direction_source
        row["flow_shadow_continuation_persistence_prob_v1"] = continuation_prob
        row["flow_shadow_continuation_persistence_label_v1"] = _score_label(continuation_prob)
        row["flow_shadow_entry_quality_prob_v1"] = entry_prob
        row["flow_shadow_entry_quality_label_v1"] = _score_label(entry_prob)
        row["flow_shadow_reversal_risk_prob_v1"] = reversal_prob
        row["flow_shadow_reversal_risk_label_v1"] = _score_label(reversal_prob)
        row["flow_shadow_entry_zone_state_v1"] = zone_state
        row["flow_shadow_caution_flags_v1"] = list(caution_flags)
        row["flow_shadow_zone_reason_summary_v1"] = zone_reason_summary
        row["flow_shadow_axes_summary_v1"] = _axis_summary(continuation_prob, entry_prob, reversal_prob)
        row["flow_shadow_start_marker_state_v1"] = marker_state
        row["flow_shadow_start_marker_event_kind_v1"] = marker_event_kind
        row["flow_shadow_start_marker_reason_v1"] = marker_reason
        row["flow_shadow_chart_event_base_kind_v1"] = base_chart_kind
        row["flow_shadow_chart_event_final_kind_v1"] = final_chart_kind
        row["flow_shadow_chart_event_override_state_v1"] = override_state
        row["flow_shadow_chart_event_override_reason_v1"] = override_reason
        row["flow_shadow_chart_event_emit_v1"] = bool(emit_chart_event)
        row["flow_shadow_chart_event_emit_state_v1"] = emit_state
        row["flow_shadow_chart_event_emit_reason_v1"] = emit_reason
        row["flow_shadow_chart_event_emit_key_v1"] = emit_key
        row["flow_shadow_chart_event_ownership_v1"] = "SHADOW_DISPLAY" if final_chart_kind else ""
        row["flow_shadow_display_reason_summary_v1"] = (
            f"symbol={symbol_name or symbol}; "
            f"direction={direction or 'NONE'}({direction_source or 'NONE'}); "
            f"flow={_effective_flow_state(row) or 'NONE'}; "
            f"conviction={conviction:.4f}; "
            f"zone={zone_state}; "
            f"persistence={_effective_persistence(row):.4f}; "
            f"shadow={row['flow_shadow_axes_summary_v1']}; "
            f"marker={marker_state}:{marker_event_kind or 'NONE'}; "
            f"chart={base_chart_kind or 'NONE'}->{final_chart_kind or 'NONE'}({override_state}); "
            f"consumer_wait={consumer_wait_chart_kind or 'NONE'}:{consumer_wait_chart_reason or 'none'}; "
            f"emit={emit_state}:{emit_reason or 'NONE'}"
        )
        rows[str(symbol)] = row
    return rows


def build_flow_shadow_display_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_shadow_display_surface_fields_v1(latest_signal_by_symbol)
    symbol_count = len(rows_by_symbol)
    marker_counts: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    zone_counts: dict[str, int] = {}
    override_counts: dict[str, int] = {}
    emit_counts: dict[str, int] = {}
    avg_continuation = 0.0
    avg_entry = 0.0
    avg_reversal = 0.0

    for row in rows_by_symbol.values():
        marker_state = _text(row.get("flow_shadow_start_marker_state_v1")) or "NONE"
        marker_counts[marker_state] = int(marker_counts.get(marker_state, 0) or 0) + 1
        direction = _text(row.get("flow_shadow_direction_v1")) or "NONE"
        direction_counts[direction] = int(direction_counts.get(direction, 0) or 0) + 1
        zone_state = _text(row.get("flow_shadow_entry_zone_state_v1")) or "NEUTRAL"
        zone_counts[zone_state] = int(zone_counts.get(zone_state, 0) or 0) + 1
        override_state = _text(row.get("flow_shadow_chart_event_override_state_v1")) or "NONE"
        override_counts[override_state] = int(override_counts.get(override_state, 0) or 0) + 1
        emit_state = _text(row.get("flow_shadow_chart_event_emit_state_v1")) or "NONE"
        emit_counts[emit_state] = int(emit_counts.get(emit_state, 0) or 0) + 1
        avg_continuation += _float(row.get("flow_shadow_continuation_persistence_prob_v1"), 0.0)
        avg_entry += _float(row.get("flow_shadow_entry_quality_prob_v1"), 0.0)
        avg_reversal += _float(row.get("flow_shadow_reversal_risk_prob_v1"), 0.0)

    if symbol_count:
        avg_continuation = round(avg_continuation / symbol_count, 4)
        avg_entry = round(avg_entry / symbol_count, 4)
        avg_reversal = round(avg_reversal / symbol_count, 4)

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["flow_shadow_display_surface_available"] if rows_by_symbol else ["no_rows_for_flow_shadow_display_surface"],
        "symbol_count": int(symbol_count),
        "flow_shadow_marker_state_count_summary": dict(marker_counts),
        "flow_shadow_direction_count_summary": dict(direction_counts),
        "flow_shadow_entry_zone_state_count_summary": dict(zone_counts),
        "flow_shadow_chart_event_override_state_count_summary": dict(override_counts),
        "flow_shadow_chart_event_emit_state_count_summary": dict(emit_counts),
        "avg_flow_shadow_continuation_persistence_prob_v1": avg_continuation,
        "avg_flow_shadow_entry_quality_prob_v1": avg_entry,
        "avg_flow_shadow_reversal_risk_prob_v1": avg_reversal,
    }
    return {
        "contract_version": FLOW_SHADOW_DISPLAY_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_shadow_display_surface_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Flow Shadow Display Surface v1",
        "",
        f"- status: `{_text(summary.get('status'))}`",
        f"- symbol_count: `{int(summary.get('symbol_count') or 0)}`",
        (
            "- avg shadow axes: "
            f"continuation=`{summary.get('avg_flow_shadow_continuation_persistence_prob_v1', 0.0)}` / "
            f"entry=`{summary.get('avg_flow_shadow_entry_quality_prob_v1', 0.0)}` / "
            f"reversal=`{summary.get('avg_flow_shadow_reversal_risk_prob_v1', 0.0)}`"
        ),
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            (
                f"- `{symbol}`: direction={row.get('flow_shadow_direction_v1', '')} | "
                f"zone={row.get('flow_shadow_entry_zone_state_v1', '')} | "
                f"axes={row.get('flow_shadow_axes_summary_v1', '')} | "
                f"marker={row.get('flow_shadow_start_marker_state_v1', '')}:{row.get('flow_shadow_start_marker_event_kind_v1', '')} | "
                f"chart={row.get('flow_shadow_chart_event_final_kind_v1', '')} | "
                f"emit={row.get('flow_shadow_chart_event_emit_state_v1', '')}"
            )
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_shadow_display_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_flow_shadow_display_surface_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "flow_shadow_display_surface_latest.json"
    markdown_path = output_dir / "flow_shadow_display_surface_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_flow_shadow_display_surface_markdown_v1(report))
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
    _write_json(json_path, report)
    return report
