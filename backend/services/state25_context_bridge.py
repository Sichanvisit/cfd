"""Helpers for the state25 context bridge."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from backend.services.teacher_pattern_active_candidate_runtime import (
    STATE25_TEACHER_WEIGHT_CATALOG,
    normalize_state25_teacher_weight_overrides,
)


STATE25_CONTEXT_BRIDGE_CONTRACT_VERSION = "state25_candidate_context_bridge_v1"
STATE25_CONTEXT_BRIDGE_STAGE_BC6 = "BC6_THRESHOLD_LOG_ONLY"
STATE25_CONTEXT_BRIDGE_TRANSLATOR_STATE_WEIGHT_THRESHOLD = (
    "WEIGHT_THRESHOLD_LOG_ONLY_ACTIVE"
)

STATE25_CONTEXT_BRIDGE_FAILURE_STALE_CONTEXT_SUPPRESSED = "STALE_CONTEXT_SUPPRESSED"
STATE25_CONTEXT_BRIDGE_FAILURE_LOW_CONFIDENCE_CONTEXT = "LOW_CONFIDENCE_CONTEXT"
STATE25_CONTEXT_BRIDGE_FAILURE_SIGNED_THRESHOLD_UNAVAILABLE = (
    "SIGNED_THRESHOLD_UNAVAILABLE"
)

STATE25_CONTEXT_BRIDGE_GUARD_DOUBLE_COUNTING_SUPPRESSED = (
    "DOUBLE_COUNTING_SUPPRESSED"
)
STATE25_CONTEXT_BRIDGE_GUARD_CAP_HIT = "CAP_HIT"
STATE25_CONTEXT_BRIDGE_GUARD_SIZE_FLOOR_PROTECTED = "SIZE_FLOOR_PROTECTED"

_FRESHNESS_UNKNOWN = "UNKNOWN"
_FRESHNESS_FRESH = "FRESH"
_FRESHNESS_AGING = "AGING"
_FRESHNESS_STALE = "STALE"
_WEIGHT_DELTA_CAP = 0.20
_LOW_CONFIDENCE_PREVIOUS_BOX_REVIEW_RELIEF_ACTIVATION = 0.35
_THRESHOLD_STAGE_MULTIPLIERS = {
    "AGGRESSIVE": 0.7,
    "BALANCED": 1.0,
    "CONSERVATIVE": 1.2,
}
_THRESHOLD_STAGE_CAP_POINTS = {
    "AGGRESSIVE": 3.0,
    "BALANCED": 4.0,
    "CONSERVATIVE": 5.0,
}
_RUNTIME_HINT_DUPLICATE_SOURCE_KEYS = (
    "forecast_state25_runtime_bridge_v1",
    "belief_state25_runtime_bridge_v1",
    "barrier_state25_runtime_bridge_v1",
)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        text = _to_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:16]


def _resolve_freshness_state(
    age_seconds: float | int | None,
    *,
    fresh_limit_seconds: int,
    stale_limit_seconds: int,
) -> str:
    if age_seconds in (None, ""):
        return _FRESHNESS_UNKNOWN
    age_value = _to_float(age_seconds, -1.0)
    if age_value < 0:
        return _FRESHNESS_UNKNOWN
    if age_value <= float(fresh_limit_seconds):
        return _FRESHNESS_FRESH
    if age_value <= float(stale_limit_seconds):
        return _FRESHNESS_AGING
    return _FRESHNESS_STALE


def _resolve_activation_for_freshness(state: str) -> float:
    if state == _FRESHNESS_FRESH:
        return 1.0
    if state == _FRESHNESS_AGING:
        return 0.5
    return 0.0


def _resolve_entry_stage_threshold_multiplier(entry_stage: Any) -> float:
    stage = _to_text(entry_stage).upper()
    if "AGGRESSIVE" in stage:
        return float(_THRESHOLD_STAGE_MULTIPLIERS["AGGRESSIVE"])
    if "CONSERVATIVE" in stage:
        return float(_THRESHOLD_STAGE_MULTIPLIERS["CONSERVATIVE"])
    return float(_THRESHOLD_STAGE_MULTIPLIERS["BALANCED"])


def _resolve_entry_stage_threshold_cap_points(entry_stage: Any) -> float:
    stage = _to_text(entry_stage).upper()
    if "AGGRESSIVE" in stage:
        return float(_THRESHOLD_STAGE_CAP_POINTS["AGGRESSIVE"])
    if "CONSERVATIVE" in stage:
        return float(_THRESHOLD_STAGE_CAP_POINTS["CONSERVATIVE"])
    return float(_THRESHOLD_STAGE_CAP_POINTS["BALANCED"])


def _resolve_overlap_sources(row: Mapping[str, Any]) -> list[str]:
    sources: list[str] = []
    if _coerce_mapping(row.get("forecast_state25_runtime_bridge_v1")):
        sources.append("forecast_state25_runtime_bridge_v1")
    if _coerce_mapping(row.get("belief_state25_runtime_bridge_v1")):
        sources.append("belief_state25_runtime_bridge_v1")
    if _coerce_mapping(row.get("barrier_state25_runtime_bridge_v1")):
        sources.append("barrier_state25_runtime_bridge_v1")
    if _coerce_mapping(row.get("countertrend_continuation_signal_v1")):
        sources.append("countertrend_continuation_signal_v1")
    return sources


def _resolve_overlap_class(overlap_sources: list[str]) -> str:
    if not overlap_sources:
        return ""
    if "countertrend_continuation_signal_v1" in overlap_sources:
        return "CONTINUATION_DUPLICATE"
    if any(
        item in overlap_sources
        for item in (
            "forecast_state25_runtime_bridge_v1",
            "belief_state25_runtime_bridge_v1",
            "barrier_state25_runtime_bridge_v1",
        )
    ):
        return "RISK_DUPLICATE"
    return "SAME_DIRECTION_DUPLICATE"


def _runtime_hint_signature(payload: Mapping[str, Any] | None) -> dict[str, str]:
    hint = _coerce_mapping(_coerce_mapping(payload).get("state25_runtime_hint_v1"))
    return {
        "scene_pattern_id": _to_text(hint.get("scene_pattern_id")),
        "entry_bias_hint": _to_text(hint.get("entry_bias_hint")),
        "wait_bias_hint": _to_text(hint.get("wait_bias_hint")),
        "exit_bias_hint": _to_text(hint.get("exit_bias_hint")),
        "transition_risk_hint": _to_text(hint.get("transition_risk_hint")),
        "reason_summary": _to_text(hint.get("reason_summary")),
    }


def _is_same_runtime_hint_duplicate(
    row: Mapping[str, Any],
    overlap_sources: list[str],
) -> bool:
    if "countertrend_continuation_signal_v1" in overlap_sources:
        return False

    runtime_hint_sources = [
        source
        for source in overlap_sources
        if source in _RUNTIME_HINT_DUPLICATE_SOURCE_KEYS
    ]
    if len(runtime_hint_sources) < 2:
        return False

    encoded_signatures: list[str] = []
    for source in runtime_hint_sources:
        signature = _runtime_hint_signature(_coerce_mapping(row.get(source)))
        if not any(_to_text(value) for value in signature.values()):
            continue
        encoded_signatures.append(
            json.dumps(
                signature,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    if len(encoded_signatures) < 2:
        return False
    return len(set(encoded_signatures)) == 1


def _resolve_htf_severity_multiplier(value: Any) -> float:
    severity = _to_text(value).upper()
    if severity == "HIGH":
        return 1.0
    if severity == "MEDIUM":
        return 0.75
    if severity == "LOW":
        return 0.5
    return 0.6


def _should_enable_low_confidence_previous_box_review_relief(
    row: Mapping[str, Any],
    *,
    context_inputs: Mapping[str, Any],
) -> bool:
    previous_box_break_state = _to_text(
        context_inputs.get("previous_box_break_state")
    ).upper()
    previous_box_relation = _to_text(context_inputs.get("previous_box_relation")).upper()
    previous_box_confidence = _to_text(
        context_inputs.get("previous_box_confidence")
    ).upper()
    previous_box_is_consolidation = _to_bool(
        context_inputs.get("previous_box_is_consolidation"),
        True,
    )
    context_conflict_state = _to_text(
        context_inputs.get("context_conflict_state")
    ).upper()
    context_conflict_intensity = _to_text(
        context_inputs.get("context_conflict_intensity")
    ).upper()
    context_conflict_flags = {
        flag.upper()
        for flag in _normalize_text_list(context_inputs.get("context_conflict_flags"))
    }

    if previous_box_confidence != "LOW":
        return False
    if previous_box_is_consolidation:
        return False
    if previous_box_break_state not in {"BREAKOUT_HELD", "RECLAIMED"}:
        return False
    if previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation not in {
        "ABOVE",
        "AT_HIGH",
    }:
        return False
    if not (
        "AGAINST_PREV_BOX" in context_conflict_flags
        or context_conflict_state in {"AGAINST_PREV_BOX", "AGAINST_PREV_BOX_AND_HTF"}
    ):
        return False
    if context_conflict_state == "AGAINST_PREV_BOX_AND_HTF":
        return True
    if context_conflict_intensity in {"MEDIUM", "HIGH"}:
        return True
    return "AGAINST_HTF" in context_conflict_flags


def _resolve_state25_weight_baseline_overrides(row: Mapping[str, Any]) -> dict[str, float]:
    direct = normalize_state25_teacher_weight_overrides(
        row.get("state25_teacher_weight_overrides")
    )
    if direct:
        return direct
    for field_name in ("state25_candidate_runtime_v1", "state25_candidate_runtime_state"):
        payload = _coerce_mapping(row.get(field_name))
        overrides = normalize_state25_teacher_weight_overrides(
            payload.get("teacher_weight_overrides")
            or payload.get("state25_teacher_weight_overrides")
        )
        if overrides:
            return overrides
    return {}


def _build_weight_row(
    *,
    weight_key: str,
    baseline_value: float,
    target_value: float,
    delta: float,
    reason_keys: list[str],
    activation_ratio: float,
) -> dict[str, Any]:
    meta = dict(STATE25_TEACHER_WEIGHT_CATALOG.get(weight_key, {}))
    return {
        "weight_key": weight_key,
        "label_ko": _to_text(meta.get("label_ko")) or weight_key,
        "description_ko": _to_text(meta.get("description_ko")),
        "baseline_value": round(float(baseline_value), 6),
        "target_value": round(float(target_value), 6),
        "delta": round(float(delta), 6),
        "reason_keys": _normalize_text_list(reason_keys),
        "activation_ratio": round(float(activation_ratio), 6),
    }


def _build_requested_weight_candidates(
    *,
    context_inputs: Mapping[str, Any],
    component_activation: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, list[str]], list[str]]:
    candidates: list[dict[str, Any]] = []
    bias_scores = {"BUY": 0.0, "SELL": 0.0}
    bias_sources: dict[str, list[str]] = {"BUY": [], "SELL": []}
    trace_codes: list[str] = []

    consumer_side = _to_text(context_inputs.get("consumer_check_side")).upper()
    htf_state = _to_text(context_inputs.get("htf_alignment_state")).upper()
    prev_break_state = _to_text(context_inputs.get("previous_box_break_state")).upper()
    htf_activation = _to_float(component_activation.get("htf"), 0.0)
    prev_activation = _to_float(component_activation.get("previous_box"), 0.0)

    if htf_state == "AGAINST_HTF" and htf_activation > 0.0 and consumer_side in {"BUY", "SELL"}:
        severity_multiplier = _resolve_htf_severity_multiplier(
            context_inputs.get("htf_against_severity")
        )
        ratio = round(htf_activation * severity_multiplier, 6)
        candidates.extend(
            [
                {
                    "weight_key": "reversal_risk_weight",
                    "delta": -0.12 * ratio,
                    "reason_key": "AGAINST_HTF",
                    "activation_ratio": ratio,
                },
                {
                    "weight_key": "directional_bias_weight",
                    "delta": 0.10 * ratio,
                    "reason_key": "AGAINST_HTF",
                    "activation_ratio": ratio,
                },
            ]
        )
        bias_side = "SELL" if consumer_side == "BUY" else "BUY"
        bias_scores[bias_side] += ratio
        bias_sources[bias_side].append("AGAINST_HTF")
        trace_codes.append("WEIGHT_PAIR_AGAINST_HTF")

    if prev_break_state == "BREAKOUT_HELD" and prev_activation > 0.0:
        ratio = round(prev_activation, 6)
        candidates.extend(
            [
                {
                    "weight_key": "range_reversal_weight",
                    "delta": -0.10 * ratio,
                    "reason_key": "BREAKOUT_HELD",
                    "activation_ratio": ratio,
                },
                {
                    "weight_key": "directional_bias_weight",
                    "delta": 0.08 * ratio,
                    "reason_key": "BREAKOUT_HELD",
                    "activation_ratio": ratio,
                },
            ]
        )
        bias_scores["BUY"] += ratio
        bias_sources["BUY"].append("BREAKOUT_HELD")
        trace_codes.append("WEIGHT_PAIR_BREAKOUT_HELD")

    if prev_break_state == "RECLAIMED" and prev_activation > 0.0:
        ratio = round(prev_activation, 6)
        candidates.extend(
            [
                {
                    "weight_key": "reversal_risk_weight",
                    "delta": -0.08 * ratio,
                    "reason_key": "RECLAIMED",
                    "activation_ratio": ratio,
                },
                {
                    "weight_key": "participation_weight",
                    "delta": 0.08 * ratio,
                    "reason_key": "RECLAIMED",
                    "activation_ratio": ratio,
                },
            ]
        )
        bias_scores["BUY"] += ratio
        bias_sources["BUY"].append("RECLAIMED")
        trace_codes.append("WEIGHT_PAIR_RECLAIMED")

    if _to_text(context_inputs.get("late_chase_risk_state")).upper() not in {"", "NONE"}:
        trace_codes.append("LATE_CHASE_WEIGHT_SKIPPED_V1")

    return candidates, bias_scores, bias_sources, trace_codes


def _resolve_context_bias(
    bias_scores: Mapping[str, float],
    bias_sources: Mapping[str, list[str]],
) -> tuple[str, float, list[str]]:
    buy_score = float(bias_scores.get("BUY", 0.0) or 0.0)
    sell_score = float(bias_scores.get("SELL", 0.0) or 0.0)
    total = buy_score + sell_score
    if total <= 0:
        return "", 0.0, []
    if abs(buy_score - sell_score) < 0.15:
        return "", 0.0, []
    if buy_score > sell_score:
        return "BUY", round(buy_score / total, 6), _normalize_text_list(bias_sources.get("BUY"))
    return "SELL", round(sell_score / total, 6), _normalize_text_list(bias_sources.get("SELL"))


def _aggregate_weight_candidates(
    candidates: list[dict[str, Any]],
    baseline_overrides: Mapping[str, float],
) -> dict[str, dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        weight_key = _to_text(candidate.get("weight_key"))
        if weight_key not in STATE25_TEACHER_WEIGHT_CATALOG:
            continue
        row = aggregated.setdefault(
            weight_key,
            {
                "baseline_value": float(baseline_overrides.get(weight_key, 1.0)),
                "delta": 0.0,
                "reason_keys": [],
                "activation_ratio": 0.0,
            },
        )
        row["delta"] = float(row["delta"]) + _to_float(candidate.get("delta"), 0.0)
        row["reason_keys"] = _normalize_text_list(
            list(row.get("reason_keys", [])) + [_to_text(candidate.get("reason_key"))]
        )
        row["activation_ratio"] = max(
            _to_float(row.get("activation_ratio"), 0.0),
            _to_float(candidate.get("activation_ratio"), 0.0),
        )
    return aggregated


def _build_effective_weight_adjustments(
    requested: Mapping[str, dict[str, Any]],
    *,
    double_counting_guard_active: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], bool]:
    effective: dict[str, dict[str, Any]] = {}
    suppressed: dict[str, dict[str, Any]] = {}
    cap_hit = False

    for weight_key, row in dict(requested).items():
        baseline_value = _to_float(row.get("baseline_value"), 1.0)
        requested_delta = _to_float(row.get("delta"), 0.0)
        reason_keys = _normalize_text_list(row.get("reason_keys"))
        activation_ratio = _to_float(row.get("activation_ratio"), 0.0)

        if double_counting_guard_active:
            suppressed[weight_key] = {
                "reason": "DOUBLE_COUNTING_GUARD",
                "source": "overlap_guard",
                "reason_keys": reason_keys,
            }
            continue

        effective_delta = requested_delta
        if abs(effective_delta) > _WEIGHT_DELTA_CAP:
            effective_delta = _WEIGHT_DELTA_CAP if effective_delta > 0 else -_WEIGHT_DELTA_CAP
            cap_hit = True
        target_value = baseline_value + effective_delta
        clamped = normalize_state25_teacher_weight_overrides({weight_key: target_value})
        effective_value = float(clamped.get(weight_key, baseline_value))
        effective_delta = effective_value - baseline_value

        effective[weight_key] = _build_weight_row(
            weight_key=weight_key,
            baseline_value=baseline_value,
            target_value=effective_value,
            delta=effective_delta,
            reason_keys=reason_keys,
            activation_ratio=activation_ratio,
        )

    return effective, suppressed, cap_hit


def _resolve_threshold_base_points(row: Mapping[str, Any]) -> tuple[float | None, str]:
    for field_name in (
        "effective_entry_threshold",
        "entry_threshold",
        "base_entry_threshold",
        "state25_candidate_effective_entry_threshold",
    ):
        value = _to_float(row.get(field_name), 0.0)
        if value > 0.0:
            return float(value), field_name
    return None, ""


def _resolve_threshold_score_reference(
    row: Mapping[str, Any],
    *,
    consumer_check_side: str,
) -> tuple[float | None, str]:
    for field_name in ("final_score", "entry_score", "raw_score", "entry_score_raw"):
        value = row.get(field_name)
        if value not in (None, ""):
            return _to_float(value, 0.0), field_name

    side = _to_text(consumer_check_side).upper()
    if side == "BUY" and row.get("buy_score") not in (None, ""):
        return _to_float(row.get("buy_score"), 0.0), "buy_score"
    if side == "SELL" and row.get("sell_score") not in (None, ""):
        return _to_float(row.get("sell_score"), 0.0), "sell_score"

    buy_score = row.get("buy_score")
    sell_score = row.get("sell_score")
    if buy_score not in (None, "") or sell_score not in (None, ""):
        return max(_to_float(buy_score, 0.0), _to_float(sell_score, 0.0)), "max_side_score"
    return None, ""


def _resolve_late_chase_activation_confidence(context_inputs: Mapping[str, Any]) -> float:
    confidence = _to_float(context_inputs.get("late_chase_confidence"), 0.0)
    if confidence <= 0.0:
        return 1.0
    return _clamp(confidence, 0.25, 1.0)


def _base_threshold_adjustment_pct(
    *,
    context_conflict_state: str,
    context_conflict_intensity: str,
    htf_alignment_state: str,
    htf_against_severity: str,
    late_chase_state: str,
) -> tuple[list[tuple[str, float]], list[str]]:
    contributions: list[tuple[str, float]] = []
    trace_codes: list[str] = []

    intensity = _to_text(context_conflict_intensity).upper()
    severity = _to_text(htf_against_severity).upper()
    conflict_state = _to_text(context_conflict_state).upper()
    htf_state = _to_text(htf_alignment_state).upper()
    late_state = _to_text(late_chase_state).upper()

    if conflict_state == "AGAINST_PREV_BOX_AND_HTF":
        pct = {"LOW": 0.08, "MEDIUM": 0.10, "HIGH": 0.12}.get(intensity, 0.10)
        contributions.append(("AGAINST_PREV_BOX_AND_HTF", pct))
        trace_codes.append("THRESHOLD_HARDEN_AGAINST_PREV_BOX_AND_HTF")
    elif conflict_state == "AGAINST_HTF" or htf_state == "AGAINST_HTF":
        pct = {"LOW": 0.06, "MEDIUM": 0.08, "HIGH": 0.10}.get(severity, 0.08)
        contributions.append(("AGAINST_HTF", pct))
        trace_codes.append("THRESHOLD_HARDEN_AGAINST_HTF")

    if late_state == "EARLY_WARNING":
        contributions.append(("LATE_CHASE_RISK", 0.04))
        trace_codes.append("THRESHOLD_HARDEN_LATE_CHASE")
    elif late_state == "HIGH":
        contributions.append(("LATE_CHASE_RISK", 0.08))
        trace_codes.append("THRESHOLD_HARDEN_LATE_CHASE")

    return contributions, trace_codes


def _build_requested_threshold_adjustment(
    *,
    row: Mapping[str, Any],
    context_inputs: Mapping[str, Any],
    component_activation: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str], bool]:
    requested = {
        "threshold_base_points": 0.0,
        "threshold_candidate_points": 0.0,
        "threshold_delta_points": 0.0,
        "threshold_delta_pct": 0.0,
        "threshold_delta_direction": "",
        "threshold_delta_reason_keys": [],
        "threshold_stage_multiplier": 1.0,
        "threshold_stage_cap_points": 0.0,
        "threshold_source_field": "",
    }
    suppressed: dict[str, Any] = {}
    consumer_side = _to_text(context_inputs.get("consumer_check_side")).upper()
    if consumer_side not in {"BUY", "SELL"}:
        suppressed.update({"reason": "NO_ENTRY_SIDE", "source": "consumer_check_side"})
        return requested, suppressed, ["THRESHOLD_TRANSLATOR_NO_ENTRY_SIDE"], False

    base_threshold, source_field = _resolve_threshold_base_points(row)
    if base_threshold is None:
        suppressed.update({"reason": "NO_BASE_THRESHOLD", "source": "runtime_row"})
        return requested, suppressed, ["THRESHOLD_BASE_UNAVAILABLE"], True

    contributions, trace_codes = _base_threshold_adjustment_pct(
        context_conflict_state=context_inputs.get("context_conflict_state"),
        context_conflict_intensity=context_inputs.get("context_conflict_intensity"),
        htf_alignment_state=context_inputs.get("htf_alignment_state"),
        htf_against_severity=context_inputs.get("htf_against_severity"),
        late_chase_state=context_inputs.get("late_chase_risk_state"),
    )
    if not contributions:
        return requested, suppressed, ["THRESHOLD_TRANSLATOR_NO_SIGNAL"], False

    requested_pct = 0.0
    reason_keys: list[str] = []
    for reason_key, base_pct in contributions:
        if reason_key == "AGAINST_PREV_BOX_AND_HTF":
            activation_ratio = (
                _to_float(component_activation.get("htf"), 0.0)
                + _to_float(component_activation.get("previous_box"), 0.0)
            ) / 2.0
        elif reason_key == "AGAINST_HTF":
            activation_ratio = _to_float(component_activation.get("htf"), 0.0)
        else:
            activation_ratio = _to_float(component_activation.get("late_chase"), 0.0)
            activation_ratio *= _resolve_late_chase_activation_confidence(context_inputs)
        if activation_ratio <= 0.0:
            continue
        requested_pct += float(base_pct) * float(activation_ratio)
        reason_keys.append(reason_key)

    if requested_pct <= 0.0 or not reason_keys:
        return requested, suppressed, ["THRESHOLD_TRANSLATOR_INACTIVE_AFTER_GATING"], False

    stage_multiplier = _resolve_entry_stage_threshold_multiplier(
        context_inputs.get("entry_stage")
    )
    stage_cap_points = _resolve_entry_stage_threshold_cap_points(
        context_inputs.get("entry_stage")
    )
    requested_pct *= stage_multiplier
    requested_points = float(base_threshold) * float(requested_pct)
    requested.update(
        {
            "threshold_base_points": round(float(base_threshold), 6),
            "threshold_candidate_points": round(
                float(base_threshold) + float(requested_points),
                6,
            ),
            "threshold_delta_points": round(float(requested_points), 6),
            "threshold_delta_pct": round(float(requested_pct), 6),
            "threshold_delta_direction": "HARDEN",
            "threshold_delta_reason_keys": _normalize_text_list(reason_keys),
            "threshold_stage_multiplier": round(float(stage_multiplier), 6),
            "threshold_stage_cap_points": round(float(stage_cap_points), 6),
            "threshold_source_field": source_field,
        }
    )
    return requested, suppressed, trace_codes, False


def _build_effective_threshold_adjustment(
    requested: Mapping[str, Any],
    *,
    double_counting_guard_active: bool,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    requested_map = dict(requested or {})
    effective = dict(requested_map)
    suppressed: dict[str, Any] = {}
    cap_hit = False

    requested_points = _to_float(requested_map.get("threshold_delta_points"), 0.0)
    base_points = _to_float(requested_map.get("threshold_base_points"), 0.0)
    stage_cap_points = max(
        0.0,
        _to_float(requested_map.get("threshold_stage_cap_points"), 0.0),
    )
    if requested_points <= 0.0 or base_points <= 0.0:
        effective.update(
            {
                "threshold_candidate_points": round(float(base_points), 6),
                "threshold_delta_points": 0.0,
                "threshold_delta_pct": 0.0,
                "threshold_delta_direction": "",
                "threshold_delta_reason_keys": [],
            }
        )
        return effective, suppressed, False

    if double_counting_guard_active:
        suppressed = {
            "reason": "DOUBLE_COUNTING_GUARD",
            "source": "overlap_guard",
            "reason_keys": _normalize_text_list(
                requested_map.get("threshold_delta_reason_keys")
            ),
        }
        effective.update(
            {
                "threshold_candidate_points": round(float(base_points), 6),
                "threshold_delta_points": 0.0,
                "threshold_delta_pct": 0.0,
            }
        )
        return effective, suppressed, False

    effective_points = float(requested_points)
    if stage_cap_points > 0.0 and effective_points > stage_cap_points:
        effective_points = float(stage_cap_points)
        cap_hit = True
    effective_pct = (effective_points / base_points) if base_points > 0.0 else 0.0
    effective.update(
        {
            "threshold_candidate_points": round(float(base_points) + float(effective_points), 6),
            "threshold_delta_points": round(float(effective_points), 6),
            "threshold_delta_pct": round(float(effective_pct), 6),
        }
    )
    return effective, suppressed, cap_hit


def build_default_state25_candidate_context_bridge_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE25_CONTEXT_BRIDGE_CONTRACT_VERSION,
        "bridge_stage": STATE25_CONTEXT_BRIDGE_STAGE_BC6,
        "translator_state": STATE25_CONTEXT_BRIDGE_TRANSLATOR_STATE_WEIGHT_THRESHOLD,
        "context_inputs": {},
        "freshness": {},
        "component_activation": {
            "htf": 0.0,
            "previous_box": 0.0,
            "late_chase": 0.0,
            "share": 0.0,
        },
        "component_activation_reasons": {
            "htf": [],
            "previous_box": [],
            "late_chase": [],
            "share": [],
        },
        "context_bias_side": "",
        "context_bias_side_confidence": 0.0,
        "context_bias_side_source_keys": [],
        "weight_adjustments_requested": {},
        "weight_adjustments_effective": {},
        "weight_adjustments_suppressed": {},
        "threshold_adjustment_requested": {
            "threshold_base_points": 0.0,
            "threshold_candidate_points": 0.0,
            "threshold_delta_points": 0.0,
            "threshold_delta_pct": 0.0,
            "threshold_delta_direction": "",
            "threshold_delta_reason_keys": [],
            "threshold_stage_multiplier": 1.0,
            "threshold_stage_cap_points": 0.0,
            "threshold_source_field": "",
        },
        "threshold_adjustment_effective": {
            "threshold_base_points": 0.0,
            "threshold_candidate_points": 0.0,
            "threshold_delta_points": 0.0,
            "threshold_delta_pct": 0.0,
            "threshold_delta_direction": "",
            "threshold_delta_reason_keys": [],
            "threshold_stage_multiplier": 1.0,
            "threshold_stage_cap_points": 0.0,
            "threshold_source_field": "",
        },
        "threshold_adjustment_suppressed": {},
        "size_adjustment_requested": {
            "size_multiplier_delta": 0.0,
        },
        "size_adjustment_effective": {
            "size_multiplier_delta": 0.0,
        },
        "size_adjustment_suppressed": {},
        "size_adjustment_state": "UNCHANGED",
        "double_counting_guard_active": False,
        "overlap_sources": [],
        "overlap_class": "",
        "overlap_guard_decision": "NO_OVERLAP",
        "overlap_same_runtime_hint_duplicate": False,
        "stacking_limited": False,
        "caps_applied": {
            "weight": False,
            "threshold": False,
            "size": False,
        },
        "trace_reason_codes": [],
        "trace_lines_ko": [],
        "decision_counterfactual": {
            "without_bridge_decision": "",
            "with_bridge_decision": "",
            "bridge_changed_decision": False,
            "score_reference_value": 0.0,
            "score_source_field": "",
            "threshold_base_points": 0.0,
            "threshold_candidate_points": 0.0,
        },
        "outcome_counterfactual": {
            "bridge_changed_outcome": False,
            "bridge_contribution": "",
        },
        "bridge_decision_id": "",
        "hindsight_link_key": "",
        "proposal_link_key": "",
        "override_scope": "NONE",
        "override_scope_detail": {},
        "failure_modes": [],
        "guard_modes": [],
    }


def build_state25_candidate_context_bridge_v1(
    row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    row_map = _coerce_mapping(row)
    contract = build_default_state25_candidate_context_bridge_v1()

    symbol = _to_text(row_map.get("symbol"))
    entry_stage = _to_text(row_map.get("entry_stage"))
    consumer_check_side = _to_text(row_map.get("consumer_check_side")).upper()
    signal_timeframe = _to_text(row_map.get("signal_timeframe"))

    context_inputs = {
        "symbol": symbol,
        "entry_stage": entry_stage,
        "consumer_check_side": consumer_check_side,
        "signal_timeframe": signal_timeframe,
        "htf_alignment_state": _to_text(row_map.get("htf_alignment_state")),
        "htf_against_severity": _to_text(row_map.get("htf_against_severity")),
        "previous_box_break_state": _to_text(row_map.get("previous_box_break_state")),
        "previous_box_relation": _to_text(row_map.get("previous_box_relation")),
        "previous_box_confidence": _to_text(
            row_map.get("previous_box_confidence")
        ).upper(),
        "previous_box_is_consolidation": _to_bool(
            row_map.get("previous_box_is_consolidation"),
            True,
        ),
        "context_conflict_state": _to_text(row_map.get("context_conflict_state")),
        "context_conflict_intensity": _to_text(
            row_map.get("context_conflict_intensity")
        ).upper(),
        "context_conflict_flags": _normalize_text_list(
            row_map.get("context_conflict_flags")
        ),
        "late_chase_risk_state": _to_text(row_map.get("late_chase_risk_state")),
        "late_chase_confidence": _to_float(
            row_map.get("late_chase_confidence"),
            0.0,
        ),
        "late_chase_trigger_count": int(
            _to_float(row_map.get("late_chase_trigger_count"), 0.0)
        ),
        "cluster_share_symbol_band": _to_text(
            row_map.get("cluster_share_symbol_band")
        ).upper(),
    }
    contract["context_inputs"] = context_inputs

    htf_age_candidates = [
        _to_float(row_map.get("trend_1h_age_seconds"), -1.0),
        _to_float(row_map.get("trend_4h_age_seconds"), -1.0),
        _to_float(row_map.get("trend_1d_age_seconds"), -1.0),
    ]
    valid_htf_ages = [value for value in htf_age_candidates if value >= 0.0]
    htf_age_seconds = max(valid_htf_ages) if valid_htf_ages else None
    htf_freshness = _resolve_freshness_state(
        htf_age_seconds,
        fresh_limit_seconds=600,
        stale_limit_seconds=1800,
    )
    previous_box_age_seconds = _to_float(
        row_map.get("previous_box_age_seconds"),
        -1.0,
    )
    previous_box_freshness = _resolve_freshness_state(
        previous_box_age_seconds if previous_box_age_seconds >= 0 else None,
        fresh_limit_seconds=300,
        stale_limit_seconds=900,
    )
    contract["freshness"] = {
        "htf": {
            "state": htf_freshness,
            "age_seconds": None if htf_age_seconds is None else float(htf_age_seconds),
        },
        "previous_box": {
            "state": previous_box_freshness,
            "age_seconds": None
            if previous_box_age_seconds < 0
            else float(previous_box_age_seconds),
        },
    }

    component_activation = dict(contract["component_activation"])
    activation_reasons = {
        key: list(value)
        for key, value in dict(contract["component_activation_reasons"]).items()
    }
    previous_box_review_relief_active = False

    component_activation["htf"] = _resolve_activation_for_freshness(htf_freshness)
    if htf_freshness == _FRESHNESS_AGING:
        activation_reasons["htf"].append("AGING")
    elif htf_freshness == _FRESHNESS_STALE:
        activation_reasons["htf"].append("STALE")
    elif htf_freshness == _FRESHNESS_UNKNOWN:
        activation_reasons["htf"].append("UNKNOWN_AGE")

    previous_box_activation = _resolve_activation_for_freshness(previous_box_freshness)
    previous_box_confidence = context_inputs["previous_box_confidence"]
    if previous_box_confidence == "LOW":
        previous_box_activation = min(previous_box_activation, 0.5)
        activation_reasons["previous_box"].append("LOW_CONFIDENCE")
    if not bool(context_inputs["previous_box_is_consolidation"]):
        if (
            previous_box_activation > 0.0
            and _should_enable_low_confidence_previous_box_review_relief(
                row_map,
                context_inputs=context_inputs,
            )
        ):
            previous_box_review_relief_active = True
            previous_box_activation = min(
                previous_box_activation,
                _LOW_CONFIDENCE_PREVIOUS_BOX_REVIEW_RELIEF_ACTIVATION,
            )
            activation_reasons["previous_box"].append("LOW_CONFIDENCE_REVIEW_RELIEF")
            activation_reasons["previous_box"].append("NON_CONSOLIDATION_REVIEW_ONLY")
        else:
            previous_box_activation = 0.0
            activation_reasons["previous_box"].append("NON_CONSOLIDATION")
    if previous_box_freshness == _FRESHNESS_AGING:
        activation_reasons["previous_box"].append("AGING")
    elif previous_box_freshness == _FRESHNESS_STALE:
        activation_reasons["previous_box"].append("STALE")
    elif previous_box_freshness == _FRESHNESS_UNKNOWN:
        activation_reasons["previous_box"].append("UNKNOWN_AGE")
    component_activation["previous_box"] = float(previous_box_activation)

    late_chase_state = context_inputs["late_chase_risk_state"].upper()
    if late_chase_state and late_chase_state != "NONE":
        component_activation["late_chase"] = 1.0
        activation_reasons["late_chase"].append("DIRECT_RISK_SIGNAL")
    else:
        component_activation["late_chase"] = 0.0
        activation_reasons["late_chase"].append("NO_SIGNAL")

    share_band = context_inputs["cluster_share_symbol_band"]
    if share_band:
        component_activation["share"] = 0.2
        activation_reasons["share"].append("BOOSTER_ONLY")
    else:
        component_activation["share"] = 0.0
        activation_reasons["share"].append("NO_SHARE_CONTEXT")

    contract["component_activation"] = component_activation
    contract["component_activation_reasons"] = activation_reasons

    overlap_sources = _resolve_overlap_sources(row_map)
    overlap_class = _resolve_overlap_class(overlap_sources)
    same_runtime_hint_duplicate = _is_same_runtime_hint_duplicate(
        row_map,
        overlap_sources,
    )
    contract["overlap_sources"] = overlap_sources
    contract["overlap_class"] = overlap_class
    contract["overlap_same_runtime_hint_duplicate"] = same_runtime_hint_duplicate
    if overlap_sources:
        if overlap_class == "RISK_DUPLICATE" and same_runtime_hint_duplicate:
            contract["double_counting_guard_active"] = False
            contract["overlap_guard_decision"] = "RELAXED_SAME_RUNTIME_HINT_DUPLICATE"
        else:
            contract["double_counting_guard_active"] = True
            contract["overlap_guard_decision"] = "BLOCKED_OVERLAP_DUPLICATE"
            contract["guard_modes"] = [
                STATE25_CONTEXT_BRIDGE_GUARD_DOUBLE_COUNTING_SUPPRESSED
            ]

    failure_modes: list[str] = []
    if htf_freshness == _FRESHNESS_STALE or previous_box_freshness == _FRESHNESS_STALE:
        failure_modes.append(STATE25_CONTEXT_BRIDGE_FAILURE_STALE_CONTEXT_SUPPRESSED)
    if previous_box_confidence == "LOW":
        failure_modes.append(STATE25_CONTEXT_BRIDGE_FAILURE_LOW_CONFIDENCE_CONTEXT)
    contract["failure_modes"] = _normalize_text_list(failure_modes)
    contract["guard_modes"] = _normalize_text_list(contract.get("guard_modes"))

    trace_reason_codes: list[str] = [
        "WEIGHT_TRANSLATOR_READY",
        "THRESHOLD_TRANSLATOR_READY",
    ]
    if contract["double_counting_guard_active"]:
        trace_reason_codes.append("DOUBLE_COUNTING_GUARD_READY")
    elif same_runtime_hint_duplicate and overlap_sources:
        trace_reason_codes.append("OVERLAP_GUARD_RELAXED_SAME_RUNTIME_HINT")
    if component_activation["htf"] == 0.0 and htf_freshness == _FRESHNESS_STALE:
        trace_reason_codes.append("HTF_STALE")
    if component_activation["previous_box"] == 0.0 and "NON_CONSOLIDATION" in activation_reasons["previous_box"]:
        trace_reason_codes.append("PREVIOUS_BOX_NON_CONSOLIDATION")
    if previous_box_review_relief_active:
        trace_reason_codes.append("LOW_CONFIDENCE_PREVIOUS_BOX_REVIEW_RELIEF")
    if component_activation["share"] > 0.0:
        trace_reason_codes.append("SHARE_BOOSTER_ONLY")

    requested_candidates, bias_scores, bias_sources, translation_trace_codes = (
        _build_requested_weight_candidates(
            context_inputs=context_inputs,
            component_activation=component_activation,
        )
    )
    trace_reason_codes.extend(translation_trace_codes)

    if (
        context_inputs["htf_alignment_state"].upper() == "AGAINST_HTF"
        and component_activation["htf"] <= 0.0
    ):
        contract["weight_adjustments_suppressed"]["AGAINST_HTF"] = {
            "reason": "STALE_OR_INACTIVE_HTF",
            "source": "htf",
        }
    if (
        context_inputs["previous_box_break_state"].upper() in {"BREAKOUT_HELD", "RECLAIMED"}
        and component_activation["previous_box"] <= 0.0
    ):
        contract["weight_adjustments_suppressed"]["PREVIOUS_BOX_CONTEXT"] = {
            "reason": "LOW_CONFIDENCE_OR_NON_CONSOLIDATION",
            "source": "previous_box",
        }
    if late_chase_state and late_chase_state != "NONE":
        contract["weight_adjustments_suppressed"]["LATE_CHASE_RISK"] = {
            "reason": "DEFER_TO_THRESHOLD_SIZE_V1",
            "source": "translator_policy",
        }

    baseline_overrides = _resolve_state25_weight_baseline_overrides(row_map)
    aggregated_requested = _aggregate_weight_candidates(
        requested_candidates,
        baseline_overrides,
    )
    requested_rows: dict[str, dict[str, Any]] = {}
    for weight_key, weight_row in aggregated_requested.items():
        baseline_value = _to_float(weight_row.get("baseline_value"), 1.0)
        requested_delta = _to_float(weight_row.get("delta"), 0.0)
        requested_rows[weight_key] = _build_weight_row(
            weight_key=weight_key,
            baseline_value=baseline_value,
            target_value=baseline_value + requested_delta,
            delta=requested_delta,
            reason_keys=_normalize_text_list(weight_row.get("reason_keys")),
            activation_ratio=_to_float(weight_row.get("activation_ratio"), 0.0),
        )
    contract["weight_adjustments_requested"] = requested_rows

    effective_rows, suppressed_rows, weight_cap_hit = _build_effective_weight_adjustments(
        requested_rows,
        double_counting_guard_active=contract["double_counting_guard_active"],
    )
    contract["weight_adjustments_effective"] = effective_rows
    merged_weight_suppressed = dict(contract["weight_adjustments_suppressed"])
    merged_weight_suppressed.update(suppressed_rows)
    contract["weight_adjustments_suppressed"] = merged_weight_suppressed
    if weight_cap_hit:
        contract["caps_applied"]["weight"] = True
        contract["guard_modes"] = _normalize_text_list(
            list(contract["guard_modes"]) + [STATE25_CONTEXT_BRIDGE_GUARD_CAP_HIT]
        )
        trace_reason_codes.append("WEIGHT_CAP_APPLIED")

    context_bias_side, context_bias_confidence, context_bias_sources = _resolve_context_bias(
        bias_scores,
        bias_sources,
    )
    contract["context_bias_side"] = context_bias_side
    contract["context_bias_side_confidence"] = context_bias_confidence
    contract["context_bias_side_source_keys"] = context_bias_sources
    if requested_rows:
        trace_reason_codes.append("WEIGHT_TRANSLATOR_ACTIVE")
    else:
        trace_reason_codes.append("WEIGHT_TRANSLATOR_NO_SIGNAL")
    threshold_requested, threshold_suppressed, threshold_trace_codes, threshold_unavailable = (
        _build_requested_threshold_adjustment(
            row=row_map,
            context_inputs=context_inputs,
            component_activation=component_activation,
        )
    )
    contract["threshold_adjustment_requested"] = threshold_requested
    if threshold_suppressed:
        contract["threshold_adjustment_suppressed"] = dict(threshold_suppressed)
    if threshold_unavailable:
        contract["failure_modes"] = _normalize_text_list(
            list(contract["failure_modes"])
            + [STATE25_CONTEXT_BRIDGE_FAILURE_SIGNED_THRESHOLD_UNAVAILABLE]
        )
    trace_reason_codes.extend(threshold_trace_codes)

    threshold_effective, threshold_guard_suppressed, threshold_cap_hit = (
        _build_effective_threshold_adjustment(
            threshold_requested,
            double_counting_guard_active=contract["double_counting_guard_active"],
        )
    )
    contract["threshold_adjustment_effective"] = threshold_effective
    if threshold_guard_suppressed:
        merged_threshold_suppressed = dict(contract["threshold_adjustment_suppressed"])
        merged_threshold_suppressed.update(threshold_guard_suppressed)
        contract["threshold_adjustment_suppressed"] = merged_threshold_suppressed
        trace_reason_codes.append("THRESHOLD_GUARD_SUPPRESSED")
    if threshold_cap_hit:
        contract["caps_applied"]["threshold"] = True
        contract["guard_modes"] = _normalize_text_list(
            list(contract["guard_modes"]) + [STATE25_CONTEXT_BRIDGE_GUARD_CAP_HIT]
        )
        trace_reason_codes.append("THRESHOLD_CAP_APPLIED")
    if _to_float(threshold_requested.get("threshold_delta_points"), 0.0) > 0.0:
        trace_reason_codes.append("THRESHOLD_TRANSLATOR_ACTIVE")
    else:
        trace_reason_codes.append("THRESHOLD_TRANSLATOR_NO_SIGNAL")

    contract["trace_reason_codes"] = _normalize_text_list(trace_reason_codes)

    trace_lines_ko = [
        "state25 context bridge가 BC6에서 weight + threshold log-only translator를 계산했습니다.",
        (
            "activation: "
            f"HTF {component_activation['htf']:.1f} / "
            f"previous_box {component_activation['previous_box']:.1f} / "
            f"late_chase {component_activation['late_chase']:.1f} / "
            f"share {component_activation['share']:.1f}"
        ),
    ]
    if requested_rows:
        trace_lines_ko.append(
            f"weight 요청 {len(requested_rows)}건 / effective {len(effective_rows)}건"
        )
    if contract["context_bias_side"]:
        trace_lines_ko.append(
            "weight bias: "
            f"{contract['context_bias_side']} "
            f"(confidence {float(contract['context_bias_side_confidence']):.2f})"
        )
    threshold_requested_points = _to_float(
        threshold_requested.get("threshold_delta_points"),
        0.0,
    )
    threshold_effective_points = _to_float(
        threshold_effective.get("threshold_delta_points"),
        0.0,
    )
    if threshold_requested_points > 0.0:
        trace_lines_ko.append(
            "threshold harden: "
            f"requested +{threshold_requested_points:.2f}pt "
            f"({float(threshold_requested.get('threshold_delta_pct', 0.0)):.1%}) / "
            f"effective +{threshold_effective_points:.2f}pt"
        )
    if contract["overlap_guard_decision"] == "RELAXED_SAME_RUNTIME_HINT_DUPLICATE":
        trace_lines_ko.append(
            "overlap guard: forecast/belief/barrier가 같은 runtime hint를 반복한 경우로 보여 "
            "BC5에서 weight/threshold review 후보까지 suppression을 완화했습니다."
        )
    if "LATE_CHASE_WEIGHT_SKIPPED_V1" in contract["trace_reason_codes"]:
        trace_lines_ko.append(
            "late chase는 BC6에서도 weight보다 threshold/size 우선으로 보류했습니다."
        )
    if contract["failure_modes"]:
        trace_lines_ko.append(
            "failure: " + ", ".join(_normalize_text_list(contract["failure_modes"]))
        )
    if contract["guard_modes"]:
        trace_lines_ko.append(
            "guard: " + ", ".join(_normalize_text_list(contract["guard_modes"]))
        )
    contract["trace_lines_ko"] = trace_lines_ko

    score_reference, score_source_field = _resolve_threshold_score_reference(
        row_map,
        consumer_check_side=consumer_check_side,
    )
    base_threshold_points = _to_float(
        threshold_requested.get("threshold_base_points"),
        0.0,
    )
    candidate_threshold_points = _to_float(
        threshold_effective.get("threshold_candidate_points"),
        0.0,
    )
    if score_reference is not None and base_threshold_points > 0.0:
        without_bridge_decision = (
            "ENTER" if float(score_reference) >= float(base_threshold_points) else "SKIP"
        )
        with_bridge_decision = (
            "ENTER"
            if float(score_reference)
            >= float(candidate_threshold_points or base_threshold_points)
            else "SKIP"
        )
    else:
        without_bridge_decision = ""
        with_bridge_decision = ""
    contract["decision_counterfactual"] = {
        "without_bridge_decision": without_bridge_decision,
        "with_bridge_decision": with_bridge_decision,
        "bridge_changed_decision": bool(
            without_bridge_decision
            and with_bridge_decision
            and without_bridge_decision != with_bridge_decision
        ),
        "score_reference_value": round(float(score_reference or 0.0), 6),
        "score_source_field": score_source_field,
        "threshold_base_points": round(float(base_threshold_points), 6),
        "threshold_candidate_points": round(float(candidate_threshold_points), 6),
    }
    if contract["decision_counterfactual"]["bridge_changed_decision"]:
        contract["trace_reason_codes"] = _normalize_text_list(
            list(contract["trace_reason_codes"]) + ["THRESHOLD_DECISION_CHANGED"]
        )
        contract["trace_lines_ko"].append(
            "decision counterfactual: bridge threshold harden으로 ENTER 후보가 SKIP으로 바뀌었습니다."
        )

    contract["override_scope"] = "SYMBOL_CONTEXT_ONLY" if symbol else "NONE"
    contract["override_scope_detail"] = {
        "symbol": symbol,
        "entry_stage": entry_stage,
        "context_conflict_state": context_inputs["context_conflict_state"],
    }

    decision_seed = {
        "symbol": symbol,
        "entry_stage": entry_stage,
        "consumer_check_side": consumer_check_side,
        "signal_timeframe": signal_timeframe,
        "context_conflict_state": context_inputs["context_conflict_state"],
        "late_chase_risk_state": late_chase_state,
        "bridge_stage": contract["bridge_stage"],
    }
    bridge_decision_id = f"state25-ctx-{_fingerprint(decision_seed)}"
    contract["bridge_decision_id"] = bridge_decision_id
    contract["hindsight_link_key"] = bridge_decision_id
    contract["proposal_link_key"] = bridge_decision_id

    return contract

def build_state25_candidate_context_bridge_flat_fields_v1(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bridge = _coerce_mapping(payload)
    weight_requested = _coerce_mapping(bridge.get("weight_adjustments_requested"))
    weight_effective = _coerce_mapping(bridge.get("weight_adjustments_effective"))
    threshold_requested = _coerce_mapping(bridge.get("threshold_adjustment_requested"))
    threshold_effective = _coerce_mapping(bridge.get("threshold_adjustment_effective"))
    failure_modes = _normalize_text_list(bridge.get("failure_modes"))
    guard_modes = _normalize_text_list(bridge.get("guard_modes"))
    decision_counterfactual = _coerce_mapping(bridge.get("decision_counterfactual"))
    threshold_direction = _to_text(
        threshold_effective.get("threshold_delta_direction")
        or threshold_requested.get("threshold_delta_direction")
    )
    return {
        "state25_context_bridge_stage": _to_text(bridge.get("bridge_stage")),
        "state25_context_bridge_translator_state": _to_text(
            bridge.get("translator_state")
        ),
        "state25_context_bridge_bias_side": _to_text(bridge.get("context_bias_side")),
        "state25_context_bridge_bias_confidence": _to_float(
            bridge.get("context_bias_side_confidence"),
            0.0,
        ),
        "state25_context_bridge_overlap_guard_decision": _to_text(
            bridge.get("overlap_guard_decision")
        ),
        "state25_context_bridge_same_runtime_hint_duplicate": _to_bool(
            bridge.get("overlap_same_runtime_hint_duplicate"),
            False,
        ),
        "state25_context_bridge_guard_active": _to_bool(
            bridge.get("double_counting_guard_active"),
            False,
        ),
        "state25_context_bridge_weight_requested_count": int(len(weight_requested)),
        "state25_context_bridge_weight_effective_count": int(len(weight_effective)),
        "state25_context_bridge_threshold_requested_points": _to_float(
            threshold_requested.get("threshold_delta_points"),
            0.0,
        ),
        "state25_context_bridge_threshold_effective_points": _to_float(
            threshold_effective.get("threshold_delta_points"),
            0.0,
        ),
        "state25_context_bridge_threshold_direction": threshold_direction,
        "state25_context_bridge_threshold_changed_decision": _to_bool(
            decision_counterfactual.get("bridge_changed_decision"),
            False,
        ),
        "state25_context_bridge_failure_count": int(len(failure_modes)),
        "state25_context_bridge_guard_count": int(len(guard_modes)),
    }
