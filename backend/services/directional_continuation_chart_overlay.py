from __future__ import annotations

from typing import Any, Mapping

from backend.services.directional_continuation_learning_candidate import (
    build_directional_continuation_learning_candidates,
)


DIRECTIONAL_CONTINUATION_CHART_OVERLAY_VERSION = "directional_continuation_chart_overlay_v1"

_UP_REASON_TOKENS = (
    "upper_break_fail",
    "upper_reclaim",
    "lower_rebound",
    "buy_watch",
    "buy_probe",
    "buy_wait",
)
_DOWN_REASON_TOKENS = (
    "upper_reject",
    "middle_sr_anchor",
    "upper_dominant",
    "lower_dominant",
    "sell_watch",
    "sell_probe",
    "sell_wait",
    "breakdown",
    "lower_break",
)
_UP_BREAK_STATES = {"BREAKOUT_HELD", "RECLAIMED"}
_DOWN_BREAK_STATES = {"BREAKDOWN_HELD", "BREAKOUT_FAILED", "REJECTED"}
_UP_RELATIONS = {"ABOVE", "AT_HIGH"}
_DOWN_RELATIONS = {"BELOW", "AT_LOW"}
_UP_BOX_STATES = {"ABOVE", "UPPER", "UPPER_EDGE"}
_DOWN_BOX_STATES = {"BELOW", "LOWER", "LOWER_EDGE"}
_UP_BB_STATES = {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
_DOWN_BB_STATES = {"LOWER", "LOWER_EDGE", "BELOW", "BREAKDOWN"}
_SOURCE_CANDIDATE_WEIGHT = {
    "semantic_baseline_no_action_cluster": 1.0,
    "market_family_entry_audit": 0.93,
    "wrong_side_conflict_harvest": 0.78,
}
_SOURCE_SHARE_CAP = {
    "semantic_baseline_no_action_cluster": 1.0,
    "market_family_entry_audit": 0.85,
    "wrong_side_conflict_harvest": 0.45,
}


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _empty_overlay_state(symbol: str, *, selection_state: str, suppression_reason: str = "") -> dict[str, Any]:
    return {
        "contract_version": DIRECTIONAL_CONTINUATION_CHART_OVERLAY_VERSION,
        "symbol": str(symbol or "").upper().strip(),
        "overlay_enabled": False,
        "overlay_state": "DISABLED",
        "overlay_direction": "",
        "overlay_side": "",
        "overlay_event_kind_hint": "",
        "overlay_reason": "",
        "overlay_reason_ko": "",
        "overlay_summary_ko": "",
        "overlay_score": 0.0,
        "overlay_bias_score": 0.0,
        "overlay_candidate_score": 0.0,
        "overlay_source_kind": "",
        "overlay_source_labels_ko": [],
        "overlay_candidate_key": "",
        "overlay_registry_key": "",
        "overlay_repeat_count": 0,
        "overlay_selection_state": str(selection_state or "NO_CANDIDATE"),
        "overlay_suppression_reason": str(suppression_reason or ""),
        "overlay_dominant_observe_reason": "",
        "overlay_current_reason": "",
        "overlay_current_side": "",
        "overlay_reason_match": False,
        "overlay_up_score": 0.0,
        "overlay_down_score": 0.0,
    }


def _direction_score_map(scored_rows: list[dict[str, Any]]) -> dict[str, float]:
    scores = {"UP": 0.0, "DOWN": 0.0}
    for item in list(scored_rows or []):
        direction = _text(item.get("direction")).upper()
        if direction in scores:
            scores[direction] = _to_float(item.get("selection_score"), 0.0)
    return scores


def _best_candidate_for_direction(
    scored_rows: list[dict[str, Any]],
    direction: str,
) -> dict[str, Any]:
    direction_u = _text(direction).upper()
    for item in list(scored_rows or []):
        if _text(item.get("direction")).upper() == direction_u:
            return dict(item)
    return {}


def _build_carry_forward_overlay_state(
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    *,
    scored_rows: list[dict[str, Any]],
    previous_overlay_state: Mapping[str, Any] | None,
    selection_state: str,
) -> dict[str, Any] | None:
    previous_overlay = _mapping(previous_overlay_state)
    if not bool(previous_overlay.get("overlay_enabled", False)):
        return None

    previous_direction = _text(previous_overlay.get("overlay_direction")).upper()
    if previous_direction not in {"UP", "DOWN"}:
        return None

    direction_scores = _direction_score_map(scored_rows)
    previous_direction_score = _to_float(direction_scores.get(previous_direction), 0.0)
    opposite_direction = "DOWN" if previous_direction == "UP" else "UP"
    opposite_score = _to_float(direction_scores.get(opposite_direction), 0.0)
    payload = _mapping(runtime_row)
    breakout_direction = _text(
        payload.get("breakout_candidate_direction") or payload.get("breakout_direction")
    ).upper()
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    if (
        breakout_direction in {"UP", "DOWN"}
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
        and breakout_direction != previous_direction
    ):
        return None

    if selection_state == "LOW_ALIGNMENT":
        if previous_direction_score < 0.40:
            return None
    elif selection_state == "DIRECTION_TIE":
        if previous_direction_score < 0.42:
            return None
        if (opposite_score - previous_direction_score) > 0.03:
            return None
    else:
        return None

    candidate_row = _best_candidate_for_direction(scored_rows, previous_direction)
    candidate = _mapping(candidate_row.get("candidate"))
    if not candidate:
        candidate = previous_overlay
    overlay_score = max(
        previous_direction_score,
        _to_float(previous_overlay.get("overlay_score"), 0.0) * 0.92,
    )
    current_reason = _current_reason(runtime_row)
    dominant_reason = _text(candidate.get("dominant_observe_reason")).lower()
    repeat_count = max(1, _to_int(previous_overlay.get("overlay_repeat_count"), 1))
    return {
        "contract_version": DIRECTIONAL_CONTINUATION_CHART_OVERLAY_VERSION,
        "symbol": str(symbol or "").upper().strip(),
        "overlay_enabled": True,
        "overlay_state": "CARRY_FORWARD",
        "overlay_direction": previous_direction,
        "overlay_side": _direction_side(previous_direction),
        "overlay_event_kind_hint": _direction_event_kind(previous_direction),
        "overlay_reason": _direction_reason(previous_direction),
        "overlay_reason_ko": _text(candidate.get("summary_ko") or previous_overlay.get("overlay_reason_ko")),
        "overlay_summary_ko": _text(candidate.get("summary_ko") or previous_overlay.get("overlay_summary_ko")),
        "overlay_score": round(_clamp01(overlay_score), 4),
        "overlay_bias_score": _to_float(candidate_row.get("bias_score"), 0.0),
        "overlay_candidate_score": _to_float(candidate_row.get("candidate_score"), 0.0),
        "overlay_source_kind": _text(candidate.get("source_kind") or previous_overlay.get("overlay_source_kind")),
        "overlay_source_labels_ko": list(candidate.get("source_labels_ko") or previous_overlay.get("overlay_source_labels_ko") or []),
        "overlay_candidate_key": _text(candidate.get("candidate_key") or previous_overlay.get("overlay_candidate_key")),
        "overlay_registry_key": _text(candidate.get("registry_key") or previous_overlay.get("overlay_registry_key")),
        "overlay_repeat_count": int(repeat_count),
        "overlay_selection_state": f"{previous_direction}_CARRY_FORWARD",
        "overlay_suppression_reason": f"CARRY_FORWARD_{selection_state}",
        "overlay_dominant_observe_reason": _text(candidate.get("dominant_observe_reason") or previous_overlay.get("overlay_dominant_observe_reason")),
        "overlay_current_reason": current_reason,
        "overlay_current_side": _current_side(runtime_row),
        "overlay_reason_match": bool(dominant_reason and current_reason == dominant_reason),
        "overlay_up_score": _to_float(direction_scores.get("UP"), 0.0),
        "overlay_down_score": _to_float(direction_scores.get("DOWN"), 0.0),
    }


def _current_reason(row: Mapping[str, Any] | None) -> str:
    payload = _mapping(row)
    observe = _mapping(payload.get("observe_confirm_v2"))
    return _text(
        payload.get("consumer_check_reason")
        or observe.get("reason")
        or payload.get("observe_reason")
        or payload.get("action_none_reason")
        or payload.get("blocked_by")
    ).lower()


def _current_side(row: Mapping[str, Any] | None) -> str:
    payload = _mapping(row)
    observe = _mapping(payload.get("observe_confirm_v2"))
    side = _text(payload.get("consumer_check_side") or observe.get("side") or payload.get("observe_side")).upper()
    return side if side in {"BUY", "SELL"} else ""


def _direction_reason_tokens(direction: str) -> tuple[str, ...]:
    return _UP_REASON_TOKENS if str(direction).upper() == "UP" else _DOWN_REASON_TOKENS


def _opposite_reason_tokens(direction: str) -> tuple[str, ...]:
    return _DOWN_REASON_TOKENS if str(direction).upper() == "UP" else _UP_REASON_TOKENS


def _reason_matches_direction(direction: str, reason: str) -> bool:
    reason_n = _text(reason).lower()
    if not reason_n:
        return False
    return any(token in reason_n for token in _direction_reason_tokens(direction))


def _reason_matches_opposite_direction(direction: str, reason: str) -> bool:
    reason_n = _text(reason).lower()
    if not reason_n:
        return False
    return any(token in reason_n for token in _opposite_reason_tokens(direction))


def _direction_box_states(direction: str) -> set[str]:
    return set(_UP_BOX_STATES if str(direction).upper() == "UP" else _DOWN_BOX_STATES)


def _direction_bb_states(direction: str) -> set[str]:
    return set(_UP_BB_STATES if str(direction).upper() == "UP" else _DOWN_BB_STATES)


def _direction_break_states(direction: str) -> set[str]:
    return set(_UP_BREAK_STATES if str(direction).upper() == "UP" else _DOWN_BREAK_STATES)


def _direction_relations(direction: str) -> set[str]:
    return set(_UP_RELATIONS if str(direction).upper() == "UP" else _DOWN_RELATIONS)


def _direction_side(direction: str) -> str:
    return "BUY" if str(direction).upper() == "UP" else "SELL"


def _direction_event_kind(direction: str) -> str:
    return "BUY_WATCH" if str(direction).upper() == "UP" else "SELL_WATCH"


def _direction_reason(direction: str) -> str:
    return "directional_up_continuation_watch" if str(direction).upper() == "UP" else "directional_down_continuation_watch"


def _trend_alignment_count(direction: str, row: Mapping[str, Any] | None) -> int:
    payload = _mapping(row)
    direction_u = _text(direction).upper()
    count = 0
    for field in ("trend_15m_direction", "trend_1h_direction", "trend_4h_direction", "trend_1d_direction"):
        trend_direction = _text(payload.get(field)).upper()
        if direction_u == "UP" and trend_direction == "UPTREND":
            count += 1
        elif direction_u == "DOWN" and trend_direction == "DOWNTREND":
            count += 1
    return int(count)


def _structural_continuation_alignment(direction: str, row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    direction_u = _text(direction).upper()
    if direction_u not in {"UP", "DOWN"}:
        return {"score": 0.0, "confirmed": False, "trend_alignment_count": 0}

    htf_alignment_state = _text(payload.get("htf_alignment_state")).upper()
    break_state = _text(payload.get("previous_box_break_state")).upper()
    relation = _text(payload.get("previous_box_relation")).upper()
    box_state = _text(payload.get("box_state")).upper()
    bb_state = _text(payload.get("bb_state")).upper()
    breakout_direction = _text(
        payload.get("breakout_candidate_direction") or payload.get("breakout_direction")
    ).upper()
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    current_side = _current_side(payload)
    reason = _current_reason(payload)
    trend_alignment_count = _trend_alignment_count(direction_u, payload)
    supportive_break_state = break_state in _direction_break_states(direction_u)
    supportive_relation = relation in _direction_relations(direction_u) or (
        relation == "INSIDE" and supportive_break_state
    )
    supportive_box = box_state in _direction_box_states(direction_u)
    supportive_bb = bb_state in _direction_bb_states(direction_u)
    breakout_supportive = bool(
        breakout_direction == direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    breakout_opposing = bool(
        breakout_direction in {"UP", "DOWN"}
        and breakout_direction != direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    reason_supportive = _reason_matches_direction(direction_u, reason)
    reason_opposing = _reason_matches_opposite_direction(direction_u, reason)
    side_expected = _direction_side(direction_u)
    continuation_resume = _continuation_resume_signal(direction_u, payload)
    continuation_resume_score = _to_float(continuation_resume.get("score"), 0.0)
    continuation_resume_confirmed = bool(continuation_resume.get("confirmed", False))

    score = 0.0
    if htf_alignment_state == "WITH_HTF":
        score += 0.20
    if trend_alignment_count >= 3:
        score += 0.18
    elif trend_alignment_count == 2:
        score += 0.12
    elif trend_alignment_count == 1:
        score += 0.05
    if supportive_break_state:
        score += 0.18
    if supportive_relation:
        score += 0.10
    if supportive_box:
        score += 0.07
    if supportive_bb:
        score += 0.06
    if breakout_supportive:
        score += 0.12
    if reason_supportive:
        score += 0.09
    if continuation_resume_confirmed:
        score += 0.10
    score += continuation_resume_score * 0.08
    if current_side == side_expected:
        score += 0.05
    elif current_side:
        score -= 0.04
    if breakout_opposing:
        score -= 0.15
    if reason_opposing:
        score -= 0.10

    normalized_score = _clamp01(score)
    confirmed = bool(
        normalized_score >= 0.42
        and htf_alignment_state == "WITH_HTF"
        and trend_alignment_count >= 2
        and (
            supportive_break_state
            or breakout_supportive
            or reason_supportive
            or continuation_resume_confirmed
        )
    )
    return {
        "score": round(normalized_score, 4),
        "confirmed": bool(confirmed),
        "trend_alignment_count": int(trend_alignment_count),
        "reason_supportive": bool(reason_supportive),
        "reason_opposing": bool(reason_opposing),
        "breakout_supportive": bool(breakout_supportive),
        "supportive_break_state": bool(supportive_break_state),
        "continuation_resume_score": round(continuation_resume_score, 4),
        "continuation_resume_confirmed": bool(continuation_resume_confirmed),
    }


def _continuation_resume_signal(direction: str, row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    direction_u = _text(direction).upper()
    if direction_u not in {"UP", "DOWN"}:
        return {"score": 0.0, "confirmed": False}

    breakout_runtime = _mapping(payload.get("breakout_event_runtime_v1"))
    breakout_overlay = _mapping(payload.get("breakout_event_overlay_candidates_v1"))
    breakout_direction = _text(
        breakout_runtime.get("breakout_direction")
        or payload.get("breakout_candidate_direction")
        or payload.get("breakout_direction")
    ).upper()
    breakout_target = _text(
        breakout_overlay.get("candidate_action_target")
        or payload.get("breakout_candidate_action_target")
    ).upper()
    breakout_state = _text(
        breakout_runtime.get("breakout_state") or payload.get("breakout_candidate_surface_state")
    ).lower()
    breakout_retest_status = _text(breakout_runtime.get("breakout_retest_status")).lower()
    breakout_reference_type = _text(breakout_runtime.get("breakout_reference_type")).lower()
    breakout_confidence = _clamp01(
        _to_float(
            breakout_runtime.get("breakout_confidence", payload.get("breakout_candidate_confidence", 0.0)),
            0.0,
        )
    )
    breakout_followthrough = _clamp01(
        _to_float(
            breakout_runtime.get(
                "breakout_followthrough_score",
                payload.get("breakout_followthrough_score", 0.0),
            ),
            0.0,
        )
    )
    break_state = _text(payload.get("previous_box_break_state")).upper()
    relation = _text(payload.get("previous_box_relation")).upper()
    low_retests = _to_float(
        payload.get("previous_box_low_retest_count", payload.get("swing_low_retest_count_20", 0.0)),
        0.0,
    )
    high_retests = _to_float(
        payload.get("previous_box_high_retest_count", payload.get("swing_high_retest_count_20", 0.0)),
        0.0,
    )

    score = 0.0
    if breakout_direction == direction_u:
        score += 0.18
    if breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        score += 0.12
    if breakout_state in {"breakout_pullback", "continuation_follow", "reclaim_breakout_candidate"}:
        score += 0.14
    if breakout_retest_status in {"passed", "holding", "ready"}:
        score += 0.12
    if breakout_reference_type in {"squeeze", "reclaim", "retest"}:
        score += 0.06
    score += breakout_confidence * 0.10
    score += breakout_followthrough * 0.12

    if direction_u == "UP":
        if break_state in {"BREAKOUT_HELD", "RECLAIMED"}:
            score += 0.08
        if relation in {"ABOVE", "AT_HIGH", "INSIDE"}:
            score += 0.08
        if low_retests >= 2:
            score += 0.10
    else:
        if break_state in {"BREAKDOWN_HELD", "BREAKOUT_FAILED", "REJECTED"}:
            score += 0.08
        if relation in {"BELOW", "AT_LOW", "INSIDE"}:
            score += 0.08
        if high_retests >= 2:
            score += 0.10

    normalized_score = _clamp01(score)
    confirmed = bool(
        breakout_direction == direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
        and normalized_score >= 0.44
    )
    return {
        "score": round(normalized_score, 4),
        "confirmed": bool(confirmed),
    }


def _candidate_base_score(candidate: Mapping[str, Any] | None) -> float:
    payload = _mapping(candidate)
    source_kind = _text(payload.get("source_kind"))
    share_cap = _to_float(_SOURCE_SHARE_CAP.get(source_kind), 1.0)
    source_weight = _to_float(_SOURCE_CANDIDATE_WEIGHT.get(source_kind), 0.9)
    score = _clamp01(
        (_clamp01(_to_float(payload.get("misread_confidence"), 0.0)) * 0.42)
        + (min(1.0, _to_float(payload.get("priority_score"), 0.0) / 100.0) * 0.25)
        + (min(share_cap, _clamp01(_to_float(payload.get("symbol_share"), 0.0))) * 0.18)
        + (min(share_cap, _clamp01(_to_float(payload.get("global_share"), 0.0))) * 0.07)
        + (min(1.0, _to_int(payload.get("repeat_count"), 0) / 20.0) * 0.08)
    )
    return _clamp01(score * source_weight)


def _accuracy_alignment_score(row: Mapping[str, Any] | None, candidate: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    candidate_map = _mapping(candidate)
    measured_count = _to_int(payload.get("directional_continuation_accuracy_measured_count"), 0)
    sample_count = _to_int(payload.get("directional_continuation_accuracy_sample_count"), 0)
    if measured_count <= 0 and sample_count <= 0:
        return 0.5

    correct_rate = _clamp01(_to_float(payload.get("directional_continuation_accuracy_correct_rate"), 0.0))
    false_alarm_rate = _clamp01(_to_float(payload.get("directional_continuation_accuracy_false_alarm_rate"), 0.0))
    last_state = _text(payload.get("directional_continuation_accuracy_last_state")).upper()
    last_candidate_key = _text(payload.get("directional_continuation_accuracy_last_candidate_key"))
    candidate_key = _text(candidate_map.get("candidate_key"))

    score = 0.5
    if measured_count >= 3:
        score += (correct_rate - 0.5) * 0.8
        score -= max(0.0, false_alarm_rate - 0.4) * 0.9
    if measured_count and sample_count and measured_count < max(3, int(sample_count * 0.4)):
        score -= 0.05
    if candidate_key and last_candidate_key and candidate_key == last_candidate_key:
        if last_state == "INCORRECT":
            score -= 0.18
        elif last_state == "CORRECT":
            score += 0.08
    return _clamp01(score)


def _current_cycle_structure_score(direction: str, row: Mapping[str, Any] | None, candidate: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    candidate_map = _mapping(candidate)
    direction_u = _text(direction).upper()
    source_kind = _text(candidate_map.get("source_kind"))
    breakout_direction = _text(
        payload.get("breakout_candidate_direction") or payload.get("breakout_direction")
    ).upper()
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    quick_state = _text(payload.get("quick_trace_state")).upper()
    break_state = _text(payload.get("previous_box_break_state")).upper()
    relation = _text(payload.get("previous_box_relation")).upper()
    failure_risk = _clamp01(_to_float(payload.get("active_action_conflict_breakout_failure_risk"), 0.0))
    current_side = _current_side(payload)
    reason = _current_reason(payload)
    reason_matches_direction = _reason_matches_direction(direction_u, reason)
    reason_matches_opposite = _reason_matches_opposite_direction(direction_u, reason)
    structural_alignment = _structural_continuation_alignment(direction_u, payload)
    structural_alignment_score = _to_float(structural_alignment.get("score"), 0.0)
    structural_alignment_confirmed = bool(structural_alignment.get("confirmed", False))
    continuation_resume = _continuation_resume_signal(direction_u, payload)
    continuation_resume_score = _to_float(continuation_resume.get("score"), 0.0)
    continuation_resume_confirmed = bool(continuation_resume.get("confirmed", False))

    score = 0.5
    if breakout_direction in {"UP", "DOWN"}:
        if breakout_direction == direction_u:
            score += 0.24
        else:
            score -= 0.22
    elif breakout_target == "WAIT_MORE":
        score -= 0.04

    if breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"} and breakout_direction == direction_u:
        score += 0.08

    if break_state == "BREAKOUT_FAILED":
        if direction_u == "UP":
            score -= 0.18
        else:
            score += 0.12
    elif break_state in {"BREAKOUT_HELD", "RECLAIMED"}:
        if direction_u == "UP":
            score += 0.14
        else:
            score -= 0.10
    elif break_state in {"BREAKDOWN_HELD", "REJECTED"}:
        if direction_u == "DOWN":
            score += 0.14
        else:
            score -= 0.12

    if relation == "INSIDE":
        if direction_u == "UP" and break_state == "BREAKOUT_FAILED":
            score -= 0.06
        elif direction_u == "DOWN" and break_state == "BREAKOUT_FAILED":
            score += 0.06

    if quick_state == "BLOCKED" and breakout_target in {"", "WAIT_MORE"}:
        if source_kind in {"wrong_side_conflict_harvest", "market_family_entry_audit"}:
            score -= 0.08
        if failure_risk >= 0.9 and direction_u == "UP" and current_side == "SELL":
            score -= 0.08

    if breakout_target in {"", "WAIT_MORE"} and quick_state in {"OBSERVE", "BLOCKED", "PROBE_WAIT"}:
        if reason_matches_direction:
            score += 0.08
        if reason_matches_opposite:
            score -= 0.07

    if source_kind == "wrong_side_conflict_harvest":
        score -= 0.08
        if break_state == "BREAKOUT_FAILED" and direction_u == "UP":
            score -= 0.10

    if direction_u == "UP" and "middle_sr_anchor" in reason and break_state == "BREAKOUT_FAILED":
        score -= 0.08
    if direction_u == "DOWN" and any(
        token in reason for token in ("upper_reject", "middle_sr_anchor", "outer_band", "upper_dominant", "lower_dominant", "upper_edge")
    ):
        score += 0.05
    if (
        break_state == "BREAKOUT_FAILED"
        and relation == "AT_HIGH"
        and current_side == "SELL"
        and any(token in reason for token in ("middle_sr_anchor", "upper_dominant", "upper_reject", "upper_edge"))
        ):
        if direction_u == "DOWN":
            score += 0.16
        else:
            score -= 0.18
    if structural_alignment_confirmed:
        score += 0.12
    elif structural_alignment_score >= 0.34 and reason_matches_direction:
        score += 0.05
    elif structural_alignment_score <= 0.18 and reason_matches_opposite:
        score -= 0.06
    score += continuation_resume_score * 0.18
    if continuation_resume_confirmed:
        score += 0.08
    return _clamp01(score)


def _direction_bias_score(direction: str, row: Mapping[str, Any] | None, candidate: Mapping[str, Any] | None) -> float:
    payload = _mapping(row)
    candidate_map = _mapping(candidate)
    direction_u = _text(direction).upper()
    side_expected = _direction_side(direction_u)
    reason = _current_reason(payload)
    current_side = _current_side(payload)
    score = 0.24

    for field in ("trend_15m_direction", "trend_1h_direction", "trend_4h_direction", "trend_1d_direction"):
        trend_direction = _text(payload.get(field)).upper()
        if direction_u == "UP" and trend_direction == "UPTREND":
            score += 0.08
        elif direction_u == "DOWN" and trend_direction == "DOWNTREND":
            score += 0.08
        elif trend_direction in {"UPTREND", "DOWNTREND"}:
            score -= 0.05

    if current_side == side_expected:
        score += 0.10
    elif current_side:
        score -= 0.06

    dominant_reason = _text(candidate_map.get("dominant_observe_reason")).lower()
    if dominant_reason and reason == dominant_reason:
        score += 0.18

    if reason:
        if any(token in reason for token in _direction_reason_tokens(direction_u)):
            score += 0.14
        if any(token in reason for token in _opposite_reason_tokens(direction_u)):
            score -= 0.08

    break_state = _text(payload.get("previous_box_break_state")).upper()
    relation = _text(payload.get("previous_box_relation")).upper()
    box_state = _text(payload.get("box_state")).upper()
    bb_state = _text(payload.get("bb_state")).upper()
    if break_state in _direction_break_states(direction_u):
        score += 0.14
    elif break_state and break_state != "INSIDE":
        score -= 0.05
    if relation in _direction_relations(direction_u):
        score += 0.08
    if box_state in _direction_box_states(direction_u):
        score += 0.05
    if bb_state in _direction_bb_states(direction_u):
        score += 0.05

    conflict_state = _text(payload.get("context_conflict_state")).upper()
    if conflict_state in {"AGAINST_HTF", "AGAINST_PREV_BOX", "AGAINST_PREV_BOX_AND_HTF"}:
        if direction_u == "UP" and current_side == "SELL":
            score += 0.18
        elif direction_u == "DOWN" and current_side == "BUY":
            score += 0.18

    return _clamp01(score)


def _selection_score(
    direction: str,
    row: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> tuple[float, float, float, float, float, float]:
    candidate_score = _candidate_base_score(candidate)
    bias_score = _direction_bias_score(direction, row, candidate)
    structure_score = _current_cycle_structure_score(direction, row, candidate)
    accuracy_score = _accuracy_alignment_score(row, candidate)
    structural_alignment_score = _to_float(
        _structural_continuation_alignment(direction, row).get("score"),
        0.0,
    )
    payload = _mapping(row)
    candidate_map = _mapping(candidate)
    current_reason = _current_reason(payload)
    dominant_reason = _text(candidate_map.get("dominant_observe_reason")).lower()
    breakout_direction = _text(
        payload.get("breakout_candidate_direction") or payload.get("breakout_direction")
    ).upper()
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    quick_state = _text(payload.get("quick_trace_state")).upper()
    false_alarm_rate = _clamp01(_to_float(payload.get("directional_continuation_accuracy_false_alarm_rate"), 0.0))
    measured_count = _to_int(payload.get("directional_continuation_accuracy_measured_count"), 0)
    last_state = _text(payload.get("directional_continuation_accuracy_last_state")).upper()
    last_candidate_key = _text(payload.get("directional_continuation_accuracy_last_candidate_key"))
    candidate_key = _text(candidate_map.get("candidate_key"))
    source_kind = _text(candidate_map.get("source_kind"))
    reason_matches_direction = _reason_matches_direction(direction, current_reason)
    reason_matches_opposite = _reason_matches_opposite_direction(direction, current_reason)

    selection_score = _clamp01(
        (candidate_score * 0.27)
        + (bias_score * 0.24)
        + (structure_score * 0.24)
        + (accuracy_score * 0.13)
        + (structural_alignment_score * 0.12)
    )
    if (
        measured_count >= 5
        and false_alarm_rate >= 0.55
        and candidate_key
        and candidate_key == last_candidate_key
        and last_state == "INCORRECT"
        and breakout_direction != _text(direction).upper()
        and breakout_target in {"", "WAIT_MORE"}
    ):
        selection_score -= 0.12
    if accuracy_score < 0.25 and structure_score < 0.45:
        selection_score -= 0.12
    if source_kind == "wrong_side_conflict_harvest" and structure_score < 0.45:
        selection_score -= 0.10
    if dominant_reason and current_reason and dominant_reason != current_reason and quick_state == "BLOCKED":
        selection_score -= 0.08
    if (
        source_kind == "semantic_baseline_no_action_cluster"
        and measured_count >= 5
        and accuracy_score < 0.25
        and breakout_direction not in {_text(direction).upper()}
        and breakout_target in {"", "WAIT_MORE"}
        and quick_state == "BLOCKED"
    ):
        selection_score -= 0.16
    if (
        source_kind == "wrong_side_conflict_harvest"
        and dominant_reason
        and current_reason
        and dominant_reason != current_reason
        and breakout_target in {"", "WAIT_MORE"}
    ):
        selection_score -= 0.12
    if (
        source_kind == "wrong_side_conflict_harvest"
        and breakout_target in {"", "WAIT_MORE"}
        and quick_state in {"OBSERVE", "BLOCKED", "PROBE_WAIT"}
    ):
        if reason_matches_opposite:
            selection_score -= 0.12
        elif not reason_matches_direction and current_reason:
            selection_score -= 0.05

    return (
        round(_clamp01(selection_score), 4),
        round(candidate_score, 4),
        round(bias_score, 4),
        round(structure_score, 4),
        round(accuracy_score, 4),
        round(structural_alignment_score, 4),
    )


def build_directional_continuation_chart_overlay_state(
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    *,
    continuation_candidates: list[Mapping[str, Any]] | None = None,
    previous_overlay_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    symbol_key = _text(symbol or _mapping(runtime_row).get("symbol")).upper().strip()
    if not symbol_key:
        return _empty_overlay_state("", selection_state="MISSING_SYMBOL")

    if continuation_candidates is None:
        continuation_candidates = build_directional_continuation_learning_candidates()

    symbol_candidates = [
        _mapping(candidate)
        for candidate in list(continuation_candidates or [])
        if _text(_mapping(candidate).get("symbol")).upper() == symbol_key
    ]
    if not symbol_candidates:
        return _empty_overlay_state(symbol_key, selection_state="NO_CANDIDATE")

    scored_rows: list[dict[str, Any]] = []
    for candidate in symbol_candidates:
        direction = _text(candidate.get("continuation_direction")).upper()
        if direction not in {"UP", "DOWN"}:
            continue
        selection_score, candidate_score, bias_score, structure_score, accuracy_score, structural_alignment_score = _selection_score(
            direction,
            runtime_row,
            candidate,
        )
        scored_rows.append(
            {
                "direction": direction,
                "selection_score": selection_score,
                "candidate_score": candidate_score,
                "bias_score": bias_score,
                "structure_score": structure_score,
                "accuracy_score": accuracy_score,
                "structural_alignment_score": structural_alignment_score,
                "candidate": candidate,
            }
        )
    if not scored_rows:
        return _empty_overlay_state(symbol_key, selection_state="NO_DIRECTIONAL_CANDIDATE")

    ordered = sorted(
        scored_rows,
        key=lambda item: (-_to_float(item.get("selection_score"), 0.0), item.get("direction")),
    )
    best = ordered[0]
    direction_scores = _direction_score_map(ordered)
    second_score = _to_float(ordered[1].get("selection_score"), 0.0) if len(ordered) > 1 else 0.0
    best_score = _to_float(best.get("selection_score"), 0.0)
    best_structure_score = _to_float(best.get("structure_score"), 0.0)
    best_accuracy_score = _to_float(best.get("accuracy_score"), 0.0)
    best_bias_score = _to_float(best.get("bias_score"), 0.0)
    best_structural_alignment_score = _to_float(best.get("structural_alignment_score"), 0.0)
    payload = _mapping(runtime_row)
    current_reason = _current_reason(runtime_row)
    breakout_target = _text(payload.get("breakout_candidate_action_target")).upper()
    quick_state = _text(payload.get("quick_trace_state")).upper()
    previous_overlay_enabled = bool(_mapping(previous_overlay_state).get("overlay_enabled", False))
    structural_direction_confirmed = bool(
        _structural_continuation_alignment(_text(best.get("direction")).upper(), payload).get("confirmed", False)
    )
    allow_low_score_direction = (
        best_score >= 0.42
        and abs(best_score - second_score) >= 0.08
        and best_structure_score >= 0.58
        and best_accuracy_score >= 0.30
    ) or (
        structural_direction_confirmed
        and best_score >= 0.39
        and abs(best_score - second_score) >= 0.06
        and best_structure_score >= 0.54
        and best_structural_alignment_score >= 0.42
        and best_bias_score >= 0.24
    ) or (
        best_score >= 0.40
        and abs(best_score - second_score) >= 0.01
        and best_bias_score >= 0.28
        and _reason_matches_direction(_text(best.get("direction")).upper(), current_reason)
        and breakout_target in {"", "WAIT_MORE"}
        and quick_state in {"OBSERVE", "BLOCKED", "PROBE_WAIT"}
    )
    if best_score < 0.46 and not allow_low_score_direction:
        carry_forward = _build_carry_forward_overlay_state(
            symbol_key,
            runtime_row,
            scored_rows=ordered,
            previous_overlay_state=previous_overlay_state,
            selection_state="LOW_ALIGNMENT",
        )
        if carry_forward is not None:
            return carry_forward
        return _empty_overlay_state(symbol_key, selection_state="LOW_ALIGNMENT", suppression_reason="LOW_SELECTION_SCORE") | {
            "overlay_up_score": _to_float(direction_scores.get("UP"), 0.0),
            "overlay_down_score": _to_float(direction_scores.get("DOWN"), 0.0),
            "overlay_current_reason": _current_reason(runtime_row),
            "overlay_current_side": _current_side(runtime_row),
        }
    if len(ordered) > 1 and abs(best_score - second_score) < 0.05:
        tight_tie_direction_override = (
            not previous_overlay_enabled
            and best_score >= 0.46
            and abs(best_score - second_score) >= 0.01
            and best_structure_score >= 0.56
            and best_bias_score >= 0.27
            and _reason_matches_direction(_text(best.get("direction")).upper(), current_reason)
            and breakout_target in {"", "WAIT_MORE"}
            and quick_state in {"OBSERVE", "BLOCKED", "PROBE_WAIT"}
        ) or (
            structural_direction_confirmed
            and best_score >= 0.43
            and abs(best_score - second_score) >= 0.01
            and best_structure_score >= 0.52
            and best_structural_alignment_score >= 0.44
            and breakout_target in {"", "WAIT_MORE"}
        )
        if tight_tie_direction_override:
            pass
        else:
            carry_forward = _build_carry_forward_overlay_state(
                symbol_key,
                runtime_row,
                scored_rows=ordered,
                previous_overlay_state=previous_overlay_state,
                selection_state="DIRECTION_TIE",
            )
            if carry_forward is not None:
                return carry_forward
            return _empty_overlay_state(symbol_key, selection_state="DIRECTION_TIE", suppression_reason="TIGHT_DIRECTION_TIE") | {
                "overlay_up_score": _to_float(direction_scores.get("UP"), 0.0),
                "overlay_down_score": _to_float(direction_scores.get("DOWN"), 0.0),
                "overlay_current_reason": _current_reason(runtime_row),
                "overlay_current_side": _current_side(runtime_row),
            }

    best_candidate = _mapping(best.get("candidate"))
    direction = _text(best.get("direction")).upper()
    dominant_reason = _text(best_candidate.get("dominant_observe_reason")).lower()
    repeat_count = 3 if best_score >= 0.82 else (2 if best_score >= 0.66 else 1)
    return {
        "contract_version": DIRECTIONAL_CONTINUATION_CHART_OVERLAY_VERSION,
        "symbol": symbol_key,
        "overlay_enabled": True,
        "overlay_state": "ENABLED",
        "overlay_direction": direction,
        "overlay_side": _direction_side(direction),
        "overlay_event_kind_hint": _direction_event_kind(direction),
        "overlay_reason": _direction_reason(direction),
        "overlay_reason_ko": _text(best_candidate.get("summary_ko")),
        "overlay_summary_ko": _text(best_candidate.get("summary_ko")),
        "overlay_score": round(best_score, 4),
        "overlay_bias_score": _to_float(best.get("bias_score"), 0.0),
        "overlay_candidate_score": _to_float(best.get("candidate_score"), 0.0),
        "overlay_source_kind": _text(best_candidate.get("source_kind")),
        "overlay_source_labels_ko": list(best_candidate.get("source_labels_ko") or []),
        "overlay_candidate_key": _text(best_candidate.get("candidate_key")),
        "overlay_registry_key": _text(best_candidate.get("registry_key")),
        "overlay_repeat_count": int(repeat_count),
        "overlay_selection_state": f"{direction}_SELECTED",
        "overlay_suppression_reason": "",
        "overlay_dominant_observe_reason": _text(best_candidate.get("dominant_observe_reason")),
        "overlay_current_reason": current_reason,
        "overlay_current_side": _current_side(runtime_row),
        "overlay_reason_match": bool(dominant_reason and current_reason == dominant_reason),
        "overlay_up_score": _to_float(direction_scores.get("UP"), 0.0),
        "overlay_down_score": _to_float(direction_scores.get("DOWN"), 0.0),
    }


def build_directional_continuation_chart_overlay_flat_fields_v1(
    overlay_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _mapping(overlay_state)
    return {
        "directional_continuation_overlay_enabled": bool(payload.get("overlay_enabled", False)),
        "directional_continuation_overlay_direction": _text(payload.get("overlay_direction")).upper(),
        "directional_continuation_overlay_side": _text(payload.get("overlay_side")).upper(),
        "directional_continuation_overlay_event_kind_hint": _text(payload.get("overlay_event_kind_hint")).upper(),
        "directional_continuation_overlay_score": _to_float(payload.get("overlay_score"), 0.0),
        "directional_continuation_overlay_selection_state": _text(payload.get("overlay_selection_state")),
        "directional_continuation_overlay_candidate_key": _text(payload.get("overlay_candidate_key")),
        "directional_continuation_overlay_source_kind": _text(payload.get("overlay_source_kind")),
        "directional_continuation_overlay_reason_match": bool(payload.get("overlay_reason_match", False)),
    }
