"""Runtime-safe breakout event contract builders.

Phase 0 freezes the breakout event interface without changing live behavior.
This module only consumes runtime-safe fields and must not read manual labels
or future outcome data.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION = "breakout_event_runtime_v1"
BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_VERSION = "breakout_event_scope_freeze_v1"

BREAKOUT_EVENT_ALLOWED_DIRECTIONS = frozenset({"UP", "DOWN", "NONE"})
BREAKOUT_EVENT_ALLOWED_STATES = frozenset(
    {
        "pre_breakout",
        "initial_breakout",
        "breakout_pullback",
        "breakout_continuation",
        "failed_breakout",
    }
)
BREAKOUT_EVENT_ALLOWED_REFERENCE_TYPES = frozenset({"box", "range", "squeeze", "hybrid", "unknown"})
BREAKOUT_EVENT_ALLOWED_RETEST_STATUSES = frozenset({"none", "pending", "passed", "failed"})

BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_VERSION,
    "breakout_event_role": "action_transition_event_owner",
    "phase": "P0",
    "runtime_direct_use_fields": [
        "breakout_detected",
        "breakout_direction",
        "breakout_state",
        "effective_breakout_readiness_state",
        "breakout_readiness_origin",
        "breakout_confidence",
        "breakout_strength",
        "breakout_failure_risk",
        "breakout_followthrough_score",
        "breakout_retest_status",
        "breakout_reference_type",
        "breakout_context_scene_family",
        "breakout_context_state25_label",
        "breakout_age_bars",
        "breakout_type_candidate",
        "selected_axis_family",
        "breakout_direction_gap",
        "breakout_direction_gap_normalized",
        "why_none_reason",
        "breakout_axis_mode",
        "breakout_axis_bridge_applied",
        "breakout_up_source",
        "breakout_down_source",
        "reason_summary",
    ],
    "runtime_feature_sources": [
        "micro_breakout_readiness_state",
        "micro_swing_high_retest_count_20",
        "micro_swing_low_retest_count_20",
        "response_vector_v2.breakout_up",
        "response_vector_v2.breakout_down",
        "response_vector_v2.upper_break_up",
        "response_vector_v2.lower_break_down",
        "response_vector_v2.mid_reclaim_up",
        "response_vector_v2.mid_lose_down",
        "position_energy_surface_v1.response.breakout_up",
        "position_energy_surface_v1.response.breakout_down",
        "position_energy_surface_v1.response.upper_break_up",
        "position_energy_surface_v1.response.lower_break_down",
        "position_energy_surface_v1.response.mid_reclaim_up",
        "position_energy_surface_v1.response.mid_lose_down",
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.confirm_side",
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.confirm_score",
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.false_break_score",
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.continuation_score",
        "forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.wait_confirm_gap",
        "forecast_state25_runtime_bridge_v1.state25_runtime_hint_v1.scene_family",
        "forecast_state25_runtime_bridge_v1.state25_runtime_hint_v1.scene_pattern_name",
    ],
    "replay_only_fields": [
        "breakout_reference_high",
        "breakout_reference_low",
        "breakout_reference_width",
        "breakout_close_outside_ratio",
        "breakout_body_expansion",
        "breakout_volatility_expansion",
        "breakout_followthrough_window_bars",
        "breakout_failure_return_depth",
        "breakout_reference_density_score",
    ],
    "learning_only_fields": [
        "manual_wait_teacher_label",
        "manual_wait_teacher_anchor_time",
        "manual_wait_teacher_entry_time",
        "manual_wait_teacher_exit_time",
        "future_favorable_move_ratio",
        "future_adverse_move_ratio",
        "breakout_manual_alignment_v1",
        "breakout_action_target_v1",
    ],
    "forbidden_runtime_inputs": [
        "manual_wait_teacher_label",
        "manual_wait_teacher_anchor_time",
        "manual_wait_teacher_entry_time",
        "manual_wait_teacher_exit_time",
        "future_favorable_move_ratio",
        "future_adverse_move_ratio",
        "breakout_manual_alignment_v1",
        "breakout_action_target_v1",
    ],
    "no_leakage_rule": (
        "Runtime breakout event features may consume only runtime-observable inputs. "
        "Manual truth rows, future bar outcomes, replay-derived reference levels, and "
        "shadow action targets are replay-only and must never be read inside "
        "breakout_event_runtime_v1."
    ),
}

BREAKOUT_READY_PRIMARY_MIN = 0.28
BREAKOUT_READY_PRESSURE_MIN = 0.30
BREAKOUT_BUILDING_PRIMARY_MIN = 0.13
BREAKOUT_BUILDING_PRESSURE_MIN = 0.10
BREAKOUT_BUILDING_EDGE_MIN = 0.04
BREAKOUT_COILED_PRIMARY_MIN = 0.09
BREAKOUT_COILED_PRESSURE_MIN = 0.07

INITIAL_BREAKOUT_PRIMARY_MIN = 0.10
INITIAL_BREAKOUT_MARGIN_MIN = 0.02
RECLAIM_BREAKOUT_PRIMARY_MIN = 0.08
RECLAIM_BREAKOUT_MARGIN_MIN = 0.01
CONTINUATION_BREAKOUT_PRIMARY_MIN = 0.09
CONTINUATION_BREAKOUT_SCORE_MIN = 0.18


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


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


def _clamp01(value: object) -> float:
    return max(0.0, min(1.0, _to_float(value)))


def _pick_text(*values: object) -> str:
    for value in values:
        text = _to_str(value)
        if text:
            return text
    return ""


def _forecast_bridge(
    row: Mapping[str, Any] | None,
    override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if override:
        return _as_mapping(override)
    return _as_mapping(_as_mapping(row).get("forecast_state25_runtime_bridge_v1"))


def _forecast_summary(bridge: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_as_mapping(bridge).get("forecast_runtime_summary_v1"))


def _scene_hint(bridge: Mapping[str, Any] | None) -> dict[str, Any]:
    return _as_mapping(_as_mapping(bridge).get("state25_runtime_hint_v1"))


def _runtime_signal_surface(
    row: Mapping[str, Any] | None,
    override: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _as_mapping(row)
    if override:
        mapped = _as_mapping(override)
        if _as_mapping(mapped.get("position_energy_surface_v1")):
            return mapped
        return {"position_energy_surface_v1": mapped}
    existing = _as_mapping(payload.get("runtime_signal_surface_v1"))
    if existing:
        return existing
    position_surface = _as_mapping(payload.get("position_energy_surface_v1"))
    if position_surface:
        return {"position_energy_surface_v1": position_surface}
    return {}


def _axis_value(response: Mapping[str, Any], raw_response: Mapping[str, Any], key: str) -> float:
    return max(_clamp01(response.get(key)), _clamp01(raw_response.get(key)))


def _select_axis_score(candidates: list[tuple[str, float]]) -> tuple[float, str]:
    best_score = 0.0
    best_source = ""
    for source, raw_score in candidates:
        score = _clamp01(raw_score)
        if score > best_score:
            best_score = score
            best_source = source
    return best_score, best_source


def _response_breakout_axis_trace(
    row: Mapping[str, Any] | None,
    runtime_signal_surface_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    surface = _runtime_signal_surface(row, runtime_signal_surface_v1)
    position_surface = _as_mapping(surface.get("position_energy_surface_v1"))
    response = _as_mapping(position_surface.get("response"))
    payload = _as_mapping(row)
    raw_response = _as_mapping(payload.get("response_vector_v2"))

    breakout_up_direct = _axis_value(response, raw_response, "breakout_up")
    breakout_down_direct = _axis_value(response, raw_response, "breakout_down")
    upper_break_up = _axis_value(response, raw_response, "upper_break_up")
    lower_break_down = _axis_value(response, raw_response, "lower_break_down")
    mid_reclaim_up = _axis_value(response, raw_response, "mid_reclaim_up")
    mid_lose_down = _axis_value(response, raw_response, "mid_lose_down")
    mid_reclaim_up_proxy = mid_reclaim_up * 0.70
    mid_lose_down_proxy = mid_lose_down * 0.70
    initial_breakout_up = max(breakout_up_direct, upper_break_up)
    initial_breakout_down = max(breakout_down_direct, lower_break_down)
    reclaim_breakout_up = mid_reclaim_up_proxy
    reclaim_breakout_down = mid_lose_down_proxy

    breakout_up, breakout_up_source = _select_axis_score(
        [
            ("breakout_up", breakout_up_direct),
            ("upper_break_up", upper_break_up),
            ("mid_reclaim_up_proxy", mid_reclaim_up_proxy),
        ]
    )
    breakout_down, breakout_down_source = _select_axis_score(
        [
            ("breakout_down", breakout_down_direct),
            ("lower_break_down", lower_break_down),
            ("mid_lose_down_proxy", mid_lose_down_proxy),
        ]
    )

    direct_sources = {"breakout_up", "breakout_down"}
    any_direct = breakout_up_source in direct_sources or breakout_down_source in direct_sources
    any_proxy = bool(
        breakout_up_source in {"upper_break_up", "mid_reclaim_up_proxy"}
        or breakout_down_source in {"lower_break_down", "mid_lose_down_proxy"}
    )
    if any_direct and any_proxy:
        axis_mode = "mixed"
    elif any_proxy:
        axis_mode = "proxy"
    elif any_direct:
        axis_mode = "direct"
    else:
        axis_mode = "missing"

    return {
        "breakout_up": round(float(breakout_up), 6),
        "breakout_down": round(float(breakout_down), 6),
        "breakout_up_source": breakout_up_source,
        "breakout_down_source": breakout_down_source,
        "breakout_axis_mode": axis_mode,
        "breakout_axis_bridge_applied": bool(any_proxy),
        "initial_breakout_up_score": round(float(initial_breakout_up), 6),
        "initial_breakout_down_score": round(float(initial_breakout_down), 6),
        "reclaim_breakout_up_score": round(float(reclaim_breakout_up), 6),
        "reclaim_breakout_down_score": round(float(reclaim_breakout_down), 6),
        "mid_reclaim_up_raw": round(float(mid_reclaim_up), 6),
        "mid_lose_down_raw": round(float(mid_lose_down), 6),
    }


def _response_breakout_scores(
    row: Mapping[str, Any] | None,
    runtime_signal_surface_v1: Mapping[str, Any] | None,
) -> tuple[float, float]:
    axis_trace = _response_breakout_axis_trace(row, runtime_signal_surface_v1)
    return _clamp01(axis_trace.get("breakout_up")), _clamp01(axis_trace.get("breakout_down"))


def _retest_count(row: Mapping[str, Any] | None, direction: str) -> int:
    payload = _as_mapping(row)
    if direction == "UP":
        return int(_to_float(payload.get("micro_swing_high_retest_count_20"), 0.0))
    if direction == "DOWN":
        return int(_to_float(payload.get("micro_swing_low_retest_count_20"), 0.0))
    return 0


def _direction_gap_metrics(up_score: float, down_score: float) -> tuple[float, float]:
    primary = max(up_score, down_score)
    gap = abs(up_score - down_score)
    if primary <= 0.0:
        return gap, 0.0
    return gap, gap / primary


def _resolve_breakout_type_candidate(
    *,
    initial_breakout_up_score: float,
    initial_breakout_down_score: float,
    reclaim_breakout_up_score: float,
    reclaim_breakout_down_score: float,
    continuation_score: float,
    effective_readiness_state: str,
    reclaim_retest_hint_count: int,
) -> str:
    initial_primary = max(initial_breakout_up_score, initial_breakout_down_score)
    reclaim_primary = max(reclaim_breakout_up_score, reclaim_breakout_down_score)
    ready = effective_readiness_state in {"READY_BREAKOUT", "BUILDING_BREAKOUT", "COILED_BREAKOUT"}

    if initial_primary <= 0.0 and reclaim_primary <= 0.0:
        return "none"
    if initial_primary >= max(reclaim_primary + INITIAL_BREAKOUT_MARGIN_MIN, INITIAL_BREAKOUT_PRIMARY_MIN):
        return "initial_breakout_candidate"
    if reclaim_retest_hint_count > 0 and reclaim_primary >= RECLAIM_BREAKOUT_PRIMARY_MIN and ready:
        return "reclaim_breakout_candidate"
    if continuation_score >= CONTINUATION_BREAKOUT_SCORE_MIN and reclaim_primary >= CONTINUATION_BREAKOUT_PRIMARY_MIN and ready:
        return "continuation_breakout_candidate"
    if reclaim_primary >= max(initial_primary + RECLAIM_BREAKOUT_MARGIN_MIN, RECLAIM_BREAKOUT_PRIMARY_MIN) and ready:
        return "reclaim_breakout_candidate"
    if initial_primary >= INITIAL_BREAKOUT_PRIMARY_MIN and reclaim_primary >= RECLAIM_BREAKOUT_PRIMARY_MIN:
        if continuation_score >= CONTINUATION_BREAKOUT_SCORE_MIN and ready:
            return "continuation_breakout_candidate"
        return "initial_breakout_candidate" if initial_primary >= reclaim_primary else "reclaim_breakout_candidate"
    if initial_primary >= INITIAL_BREAKOUT_PRIMARY_MIN:
        return "initial_breakout_candidate"
    if reclaim_primary >= RECLAIM_BREAKOUT_PRIMARY_MIN and ready:
        return "reclaim_breakout_candidate"
    return "none"


def _confirm_direction(confirm_side: str) -> str:
    side = _to_str(confirm_side).upper()
    if side == "BUY":
        return "UP"
    if side == "SELL":
        return "DOWN"
    return "NONE"


def _resolve_direction_trace(
    *,
    breakout_type_candidate: str,
    initial_breakout_up_score: float,
    initial_breakout_down_score: float,
    reclaim_breakout_up_score: float,
    reclaim_breakout_down_score: float,
    effective_readiness_state: str,
    continuation_score: float,
    confirm_side: str,
    confirm_score: float,
    false_break_score: float,
) -> dict[str, Any]:
    if breakout_type_candidate == "initial_breakout_candidate":
        selected_axis_family = "initial"
        up_score_raw = initial_breakout_up_score
        down_score_raw = initial_breakout_down_score
    elif breakout_type_candidate == "continuation_breakout_candidate":
        selected_axis_family = "continuation"
        up_score_raw = reclaim_breakout_up_score
        down_score_raw = reclaim_breakout_down_score
    elif breakout_type_candidate == "reclaim_breakout_candidate":
        selected_axis_family = "reclaim"
        up_score_raw = reclaim_breakout_up_score
        down_score_raw = reclaim_breakout_down_score
    else:
        selected_axis_family = "missing"
        up_score_raw = 0.0
        down_score_raw = 0.0

    gap, normalized_gap = _direction_gap_metrics(up_score_raw, down_score_raw)
    ready = effective_readiness_state in {"READY_BREAKOUT", "BUILDING_BREAKOUT", "COILED_BREAKOUT"}
    confirm_direction = _confirm_direction(confirm_side)

    direction = "NONE"
    why_none_reason = ""
    direction_reason = ""

    if breakout_type_candidate == "none":
        why_none_reason = "type_threshold_not_met"
    elif up_score_raw <= 0.0 and down_score_raw <= 0.0:
        why_none_reason = "missing_breakout_response_axis"
    elif selected_axis_family == "initial":
        primary = max(up_score_raw, down_score_raw)
        if primary < INITIAL_BREAKOUT_PRIMARY_MIN:
            why_none_reason = "initial_axis_below_min"
        elif not ready and primary < 0.18:
            why_none_reason = "readiness_not_ready"
        elif gap < 0.02 or normalized_gap < 0.10:
            if confirm_direction != "NONE" and confirm_score >= 0.18 and primary >= INITIAL_BREAKOUT_PRIMARY_MIN:
                direction = confirm_direction
                direction_reason = f"confirm_tiebreak_{direction.lower()}"
            elif min(up_score_raw, down_score_raw) >= 0.08:
                why_none_reason = "mixed_axis_conflict"
            else:
                why_none_reason = "gap_too_small"
        else:
            direction = "UP" if up_score_raw > down_score_raw else "DOWN"
            direction_reason = "initial_breakout_resolved"
    elif selected_axis_family == "reclaim":
        primary = max(up_score_raw, down_score_raw)
        initial_primary = max(initial_breakout_up_score, initial_breakout_down_score)
        if not ready:
            why_none_reason = "readiness_not_ready"
        elif primary < RECLAIM_BREAKOUT_PRIMARY_MIN:
            why_none_reason = "reclaim_axis_below_min"
        elif initial_primary < 0.06 and continuation_score < 0.12:
            why_none_reason = "reclaim_without_break"
        elif gap < 0.012 or normalized_gap < 0.08:
            if confirm_direction != "NONE" and confirm_score >= 0.15 and continuation_score >= 0.12:
                direction = confirm_direction
                direction_reason = f"confirm_tiebreak_{direction.lower()}"
            elif min(up_score_raw, down_score_raw) >= 0.08:
                why_none_reason = "mixed_axis_conflict"
            else:
                why_none_reason = "gap_too_small"
        else:
            direction = "UP" if up_score_raw > down_score_raw else "DOWN"
            direction_reason = "reclaim_breakout_resolved"
    else:
        primary = max(up_score_raw, down_score_raw)
        if not ready:
            why_none_reason = "readiness_not_ready"
        elif continuation_score < CONTINUATION_BREAKOUT_SCORE_MIN:
            why_none_reason = "continuation_not_ready"
        elif primary < CONTINUATION_BREAKOUT_PRIMARY_MIN:
            why_none_reason = "continuation_without_break"
        elif gap < 0.012 or normalized_gap < 0.06:
            if confirm_direction != "NONE" and confirm_score >= 0.14 and continuation_score >= 0.18:
                direction = confirm_direction
                direction_reason = f"confirm_tiebreak_{direction.lower()}"
            elif min(up_score_raw, down_score_raw) >= 0.08:
                why_none_reason = "mixed_axis_conflict"
            else:
                why_none_reason = "gap_too_small"
        else:
            direction = "UP" if up_score_raw > down_score_raw else "DOWN"
            direction_reason = "continuation_breakout_resolved"

    return {
        "breakout_direction": direction,
        "selected_axis_family": selected_axis_family,
        "up_score_raw": round(float(up_score_raw), 6),
        "down_score_raw": round(float(down_score_raw), 6),
        "breakout_direction_gap": round(float(gap), 6),
        "breakout_direction_gap_normalized": round(float(normalized_gap), 6),
        "breakout_direction_reason": direction_reason,
        "why_none_reason": why_none_reason,
    }


def _resolve_reference_type(micro_state: str, scene_family: str, scene_label: str) -> str:
    joined = " ".join(item for item in (micro_state, scene_family, scene_label) if item).upper()
    if "COILED" in joined or "SQUEEZE" in joined or "TRIANGLE" in joined:
        return "squeeze"
    if "RANGE" in joined or "BOX" in joined or "CONSOLIDATION" in joined:
        return "box"
    if "BREAKOUT" in joined:
        return "hybrid"
    return "unknown"


def _resolve_effective_breakout_readiness_state(
    *,
    micro_state: str,
    breakout_up: float,
    breakout_down: float,
    confirm_score: float,
    continuation_score: float,
    wait_confirm_gap: float,
) -> tuple[str, str]:
    existing = _to_str(micro_state).upper()
    if existing:
        return existing, "runtime"

    primary_axis = max(breakout_up, breakout_down)
    confirmation_pressure = max(confirm_score, continuation_score)
    directional_edge = abs(breakout_up - breakout_down)

    if (
        primary_axis >= BREAKOUT_READY_PRIMARY_MIN
        and confirmation_pressure >= BREAKOUT_READY_PRESSURE_MIN
        and wait_confirm_gap >= 0.0
    ):
        return "READY_BREAKOUT", "surrogate"
    if primary_axis >= BREAKOUT_BUILDING_PRIMARY_MIN and (
        confirmation_pressure >= BREAKOUT_BUILDING_PRESSURE_MIN or directional_edge >= BREAKOUT_BUILDING_EDGE_MIN
    ):
        return "BUILDING_BREAKOUT", "surrogate"
    if primary_axis >= BREAKOUT_COILED_PRIMARY_MIN and confirmation_pressure >= BREAKOUT_COILED_PRESSURE_MIN:
        return "COILED_BREAKOUT", "surrogate"
    if primary_axis >= BREAKOUT_COILED_PRIMARY_MIN and directional_edge >= 0.03 and wait_confirm_gap >= -0.08:
        return "COILED_BREAKOUT", "surrogate"
    return "", ""


def _resolve_breakout_state(
    *,
    micro_state: str,
    breakout_type_candidate: str,
    breakout_direction: str,
    confirm_score: float,
    false_break_score: float,
    continuation_score: float,
    wait_confirm_gap: float,
    retest_count: int,
) -> tuple[bool, str]:
    ready_state = micro_state in {"READY_BREAKOUT", "COILED_BREAKOUT", "BUILDING_BREAKOUT"}
    if breakout_direction == "NONE":
        return False, "pre_breakout"
    if false_break_score >= max(confirm_score, continuation_score, 0.60):
        return True, "failed_breakout"
    if breakout_type_candidate == "continuation_breakout_candidate":
        if continuation_score >= max(false_break_score, 0.42) and wait_confirm_gap >= -0.05:
            return True, "breakout_continuation"
        if retest_count > 0 or ready_state:
            return True, "breakout_pullback"
    if breakout_type_candidate == "reclaim_breakout_candidate":
        if retest_count > 0 or ready_state:
            return True, "breakout_pullback"
        if continuation_score >= max(false_break_score, 0.42) and wait_confirm_gap >= -0.02:
            return True, "breakout_continuation"
    if retest_count > 0 and continuation_score >= max(false_break_score, 0.45):
        return True, "breakout_pullback"
    if continuation_score >= max(false_break_score, 0.50) and wait_confirm_gap >= 0.0:
        return True, "breakout_continuation"
    if ready_state or confirm_score >= max(false_break_score, 0.45):
        return True, "initial_breakout"
    return False, "pre_breakout"


def build_breakout_event_runtime_v1(
    row: Mapping[str, Any] | None,
    *,
    forecast_state25_runtime_bridge_v1: Mapping[str, Any] | None = None,
    runtime_signal_surface_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _as_mapping(row)
    forecast_bridge = _forecast_bridge(payload, forecast_state25_runtime_bridge_v1)
    forecast = _forecast_summary(forecast_bridge)
    scene = _scene_hint(forecast_bridge)
    micro_state = _to_str(payload.get("micro_breakout_readiness_state")).upper()
    if not micro_state:
        micro_state = _to_str(payload.get("state25_breakout_readiness_state")).upper()

    axis_trace = _response_breakout_axis_trace(payload, runtime_signal_surface_v1)
    breakout_up = _clamp01(axis_trace.get("breakout_up"))
    breakout_down = _clamp01(axis_trace.get("breakout_down"))
    confirm_side = _to_str(forecast.get("confirm_side")).upper()
    confirm_score = _clamp01(forecast.get("confirm_score"))
    false_break_score = _clamp01(forecast.get("false_break_score"))
    continuation_score = _clamp01(forecast.get("continuation_score"))
    wait_confirm_gap = _to_float(forecast.get("wait_confirm_gap"), 0.0)
    scene_family = _to_str(scene.get("scene_family")).lower()
    scene_label = _pick_text(scene.get("scene_pattern_name"), scene.get("scene_group_hint"))
    reclaim_retest_hint_count = max(
        int(_to_float(payload.get("micro_swing_high_retest_count_20"), 0.0)),
        int(_to_float(payload.get("micro_swing_low_retest_count_20"), 0.0)),
    )
    effective_readiness_state, breakout_readiness_origin = _resolve_effective_breakout_readiness_state(
        micro_state=micro_state,
        breakout_up=breakout_up,
        breakout_down=breakout_down,
        confirm_score=confirm_score,
        continuation_score=continuation_score,
        wait_confirm_gap=wait_confirm_gap,
    )

    breakout_type_candidate = _resolve_breakout_type_candidate(
        initial_breakout_up_score=_clamp01(axis_trace.get("initial_breakout_up_score")),
        initial_breakout_down_score=_clamp01(axis_trace.get("initial_breakout_down_score")),
        reclaim_breakout_up_score=_clamp01(axis_trace.get("reclaim_breakout_up_score")),
        reclaim_breakout_down_score=_clamp01(axis_trace.get("reclaim_breakout_down_score")),
        continuation_score=continuation_score,
        effective_readiness_state=effective_readiness_state,
        reclaim_retest_hint_count=reclaim_retest_hint_count,
    )
    direction_trace = _resolve_direction_trace(
        breakout_type_candidate=breakout_type_candidate,
        initial_breakout_up_score=_clamp01(axis_trace.get("initial_breakout_up_score")),
        initial_breakout_down_score=_clamp01(axis_trace.get("initial_breakout_down_score")),
        reclaim_breakout_up_score=_clamp01(axis_trace.get("reclaim_breakout_up_score")),
        reclaim_breakout_down_score=_clamp01(axis_trace.get("reclaim_breakout_down_score")),
        effective_readiness_state=effective_readiness_state,
        continuation_score=continuation_score,
        confirm_side=confirm_side,
        confirm_score=confirm_score,
        false_break_score=false_break_score,
    )
    breakout_direction = _to_str(direction_trace.get("breakout_direction")).upper()
    retest_count = _retest_count(payload, breakout_direction)
    breakout_detected, breakout_state = _resolve_breakout_state(
        micro_state=effective_readiness_state,
        breakout_type_candidate=breakout_type_candidate,
        breakout_direction=breakout_direction,
        confirm_score=confirm_score,
        false_break_score=false_break_score,
        continuation_score=continuation_score,
        wait_confirm_gap=wait_confirm_gap,
        retest_count=retest_count,
    )

    breakout_strength = max(
        breakout_up if breakout_direction == "UP" else 0.0,
        breakout_down if breakout_direction == "DOWN" else 0.0,
        confirm_score,
        continuation_score,
    )
    breakout_confidence = _clamp01(
        (breakout_strength * 0.55) + (continuation_score * 0.25) + (max(wait_confirm_gap, 0.0) * 0.20)
    )
    if breakout_state == "failed_breakout":
        breakout_confidence = _clamp01((breakout_strength * 0.40) + (false_break_score * 0.40) + 0.20)

    if breakout_state == "failed_breakout":
        breakout_retest_status = "failed"
    elif breakout_state == "breakout_pullback":
        breakout_retest_status = "passed"
    elif breakout_detected and retest_count > 0:
        breakout_retest_status = "pending"
    else:
        breakout_retest_status = "none"

    available = bool(
        effective_readiness_state
        or breakout_up > 0.0
        or breakout_down > 0.0
        or forecast
    )
    reason_tokens = [
        breakout_state,
        breakout_direction.lower() if breakout_direction != "NONE" else "none",
        breakout_type_candidate,
        _to_str(direction_trace.get("selected_axis_family")).lower(),
        _to_str(direction_trace.get("why_none_reason")).lower(),
        effective_readiness_state.lower() if effective_readiness_state else "",
        _to_str(forecast.get("decision_hint")).lower(),
    ]

    return {
        "contract_version": BREAKOUT_EVENT_RUNTIME_CONTRACT_VERSION,
        "scope_freeze_contract_version": BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_VERSION,
        "available": bool(available),
        "breakout_detected": bool(breakout_detected),
        "breakout_direction": breakout_direction if breakout_direction in BREAKOUT_EVENT_ALLOWED_DIRECTIONS else "NONE",
        "breakout_state": breakout_state if breakout_state in BREAKOUT_EVENT_ALLOWED_STATES else "pre_breakout",
        "breakout_confidence": round(float(breakout_confidence), 6),
        "breakout_strength": round(float(_clamp01(breakout_strength)), 6),
        "breakout_failure_risk": round(float(false_break_score), 6),
        "breakout_followthrough_score": round(float(continuation_score), 6),
        "breakout_retest_status": (
            breakout_retest_status
            if breakout_retest_status in BREAKOUT_EVENT_ALLOWED_RETEST_STATUSES
            else "none"
        ),
        "breakout_reference_type": _resolve_reference_type(effective_readiness_state, scene_family, scene_label),
        "breakout_context_scene_family": scene_family,
        "breakout_context_state25_label": scene_label,
        "breakout_age_bars": 0 if breakout_state in {"pre_breakout", "initial_breakout"} else 1,
        "breakout_type_candidate": breakout_type_candidate,
        "selected_axis_family": _to_str(direction_trace.get("selected_axis_family"), "missing"),
        "breakout_direction_gap": round(_to_float(direction_trace.get("breakout_direction_gap"), 0.0), 6),
        "breakout_direction_gap_normalized": round(
            _to_float(direction_trace.get("breakout_direction_gap_normalized"), 0.0), 6
        ),
        "why_none_reason": _to_str(direction_trace.get("why_none_reason")).lower(),
        "effective_breakout_readiness_state": effective_readiness_state,
        "breakout_readiness_origin": breakout_readiness_origin,
        "breakout_axis_mode": _to_str(axis_trace.get("breakout_axis_mode"), "missing"),
        "breakout_axis_bridge_applied": bool(axis_trace.get("breakout_axis_bridge_applied")),
        "breakout_up_source": _to_str(axis_trace.get("breakout_up_source")),
        "breakout_down_source": _to_str(axis_trace.get("breakout_down_source")),
        "reason_summary": "|".join(token for token in reason_tokens if token),
    }
