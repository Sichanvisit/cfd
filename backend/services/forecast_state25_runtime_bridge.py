"""Runtime-safe forecast-state25 bridge helpers."""

from __future__ import annotations

import json
from typing import Any, Mapping

from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    LEARNING_REGISTRY_BINDING_MODE_FALLBACK,
    build_learning_registry_binding_fields,
    build_learning_registry_relation,
)
from backend.services.teacher_pattern_labeler import build_teacher_pattern_payload_v2
from backend.services.teacher_pattern_active_candidate_runtime import (
    build_state25_candidate_weight_surface_v1,
)


FORECAST_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION = "forecast_state25_runtime_bridge_v1"
STATE25_RUNTIME_HINT_CONTRACT_VERSION = "state25_runtime_hint_v1"
FORECAST_RUNTIME_SUMMARY_CONTRACT_VERSION = "forecast_runtime_summary_v1"
ENTRY_WAIT_EXIT_BRIDGE_CONTRACT_VERSION = "entry_wait_exit_bridge_v1"
FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_VERSION = "forecast_state25_scope_freeze_v1"
FORECAST_STATE25_LOG_ONLY_OVERLAY_CANDIDATES_CONTRACT_VERSION = (
    "forecast_state25_log_only_overlay_candidates_v1"
)
FORECAST_STATE25_LOG_ONLY_OVERLAY_TRACE_CONTRACT_VERSION = (
    "forecast_state25_log_only_overlay_trace_v1"
)
FORECAST_DIRECT_BINDING_REPORT_CONTRACT_VERSION = "forecast_direct_binding_report_v1"

FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_V1 = {
    "contract_version": FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_VERSION,
    "state25_role": "scene_owner",
    "forecast_role": "branch_owner",
    "outcome_role": "wait_quality_and_economic_target_owner",
    "runtime_direct_use_fields": [
        "state25_runtime_hint_v1",
        "forecast_runtime_summary_v1",
        "entry_wait_exit_bridge_v1",
        "log_only_overlay_candidates_v1",
    ],
    "learning_only_fields": [
        "closed_history_teacher_labels",
        "wait_quality_labels",
        "economic_target_labels",
        "future_outcome_bridge_labels",
    ],
    "no_leakage_rule": (
        "Closed-history final labels and future outcome labels are replay-only and "
        "must not be used as direct runtime features."
    ),
}

_FORECAST_RUNTIME_SUMMARY_FIELD_ORDER = [
    "confirm_side",
    "confirm_score",
    "false_break_score",
    "continuation_score",
    "continue_favor_score",
    "fail_now_score",
    "wait_confirm_gap",
    "hold_exit_gap",
    "same_side_flip_gap",
    "belief_barrier_tension_gap",
    "decision_hint",
]

_ENTRY_WAIT_EXIT_FIELD_ORDER = [
    "prefer_entry_now",
    "prefer_wait_now",
    "prefer_hold_if_entered",
    "prefer_fast_cut_if_entered",
]


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


def _pick_float(*values: Any, default: float = 0.0) -> float:
    for value in values:
        if value in ("", None):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return float(default)


def _normalize_registry_key_list(values: list[object] | tuple[object, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        key = _to_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _parse_direction(*values: Any) -> str:
    for value in values:
        text = _to_text(value).upper()
        if text in {"BUY", "SELL"}:
            return text
        if text == "BUY_ONLY":
            return "BUY"
        if text == "SELL_ONLY":
            return "SELL"
    return ""


def _prediction_bundle_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return json.dumps(dict(value), ensure_ascii=False, separators=(",", ":"))
    return ""


def _forecast_registry_key(field_name: object) -> str:
    field = _to_text(field_name)
    return f"forecast:{field}" if field else ""


def _forecast_binding_keys_for_payload(
    payload: Mapping[str, Any] | None,
    field_order: list[str],
) -> list[str]:
    payload_map = _coerce_mapping(payload)
    return _normalize_registry_key_list(
        [_forecast_registry_key(field_name) for field_name in field_order if field_name in payload_map]
    )


def _format_forecast_registry_value_ko(field_name: str, value: Any) -> str:
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if field_name.endswith("_score") or field_name.endswith("_gap"):
        return f"{_to_float(value, 0.0):.2f}"
    if isinstance(value, float):
        return f"{float(value):.2f}"
    text = _to_text(value)
    return text or "-"


def _build_forecast_registry_report_lines(
    payload: Mapping[str, Any] | None,
    field_order: list[str],
) -> list[str]:
    payload_map = _coerce_mapping(payload)
    lines: list[str] = []
    for field_name in field_order:
        if field_name not in payload_map:
            continue
        binding = build_learning_registry_binding_fields(
            _forecast_registry_key(field_name),
            binding_mode=LEARNING_REGISTRY_BINDING_MODE_EXACT,
        )
        label_ko = _to_text(binding.get("registry_label_ko")) or field_name
        lines.append(
            f"- {label_ko}: {_format_forecast_registry_value_ko(field_name, payload_map.get(field_name))}"
        )
    return lines


def _attach_forecast_registry_binding(
    payload: Mapping[str, Any] | None,
    *,
    field_order: list[str],
    primary_field: str,
) -> dict[str, Any]:
    payload_map = dict(_coerce_mapping(payload))
    target_registry_keys = _forecast_binding_keys_for_payload(payload_map, field_order)
    binding_mode = (
        LEARNING_REGISTRY_BINDING_MODE_EXACT
        if len(target_registry_keys) == 1
        else LEARNING_REGISTRY_BINDING_MODE_DERIVED
        if target_registry_keys
        else LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    )
    primary_registry_key = _forecast_registry_key(primary_field) if target_registry_keys else ""
    binding_fields = build_learning_registry_binding_fields(
        primary_registry_key,
        binding_mode=binding_mode,
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=target_registry_keys,
        target_registry_keys=target_registry_keys,
        binding_mode=binding_mode,
    )
    payload_map.update(binding_fields)
    payload_map.update(
        {
            "registry_binding_ready": bool(binding_fields.get("registry_found")) and bool(relation.get("binding_ready")),
            "evidence_registry_keys": relation.get("evidence_registry_keys", []),
            "target_registry_keys": relation.get("target_registry_keys", []),
            "evidence_bindings": relation.get("evidence_bindings", []),
            "target_bindings": relation.get("target_bindings", []),
            "registry_report_lines_ko": _build_forecast_registry_report_lines(payload_map, field_order),
        }
    )
    return payload_map


def _scene_snapshot_from_runtime_row(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    current_context = _coerce_mapping(payload.get("current_entry_context_v1"))
    context_meta = _coerce_mapping(current_context.get("metadata"))
    entry_result = _coerce_mapping(payload.get("entry_decision_result_v1"))
    selected_setup = _coerce_mapping(entry_result.get("selected_setup"))
    observe_confirm = _coerce_mapping(payload.get("observe_confirm_v2"))
    forecast_features = _coerce_mapping(payload.get("forecast_features_v1"))
    forecast_meta = _coerce_mapping(forecast_features.get("metadata"))
    semantic_inputs = _coerce_mapping(forecast_meta.get("semantic_forecast_inputs_v2"))
    state_harvest = _coerce_mapping(semantic_inputs.get("state_harvest"))
    secondary_harvest = _coerce_mapping(semantic_inputs.get("secondary_harvest"))
    state25_candidate_runtime = _coerce_mapping(
        payload.get("state25_candidate_runtime_v1")
        or payload.get("state25_candidate_runtime_state")
    )
    weight_surface = build_state25_candidate_weight_surface_v1(
        state25_candidate_runtime,
        symbol=_pick_text(payload.get("symbol")),
        entry_stage=_pick_text(
            payload.get("entry_stage"),
            payload.get("entry_wait_decision"),
        ),
    )

    return {
        "direction": _parse_direction(
            payload.get("direction"),
            payload.get("action"),
            payload.get("setup_side"),
            selected_setup.get("side"),
            observe_confirm.get("side"),
            payload.get("observe_side"),
            payload.get("direction_policy"),
            current_context.get("direction_policy"),
        ),
        "entry_setup_id": _pick_text(
            payload.get("entry_setup_id"),
            payload.get("setup_id"),
            selected_setup.get("setup_id"),
            context_meta.get("entry_setup_id"),
        ).lower(),
        "entry_session_name": _pick_text(
            payload.get("entry_session_name"),
            context_meta.get("entry_session_name"),
        ).upper(),
        "entry_wait_state": _pick_text(
            payload.get("entry_wait_state"),
            payload.get("wait_policy_state"),
        ).upper(),
        "entry_score": _pick_float(
            payload.get("entry_score"),
            payload.get("raw_score"),
            payload.get("entry_score_raw"),
            payload.get("core_best_raw"),
            payload.get("core_score"),
        ),
        "contra_score_at_entry": _pick_float(
            payload.get("contra_score_at_entry"),
            payload.get("contra_score"),
            payload.get("entry_contra_score_raw"),
            payload.get("core_min_raw"),
        ),
        "prediction_bundle": _prediction_bundle_text(payload.get("prediction_bundle")),
        "micro_breakout_readiness_state": _pick_text(
            payload.get("micro_breakout_readiness_state"),
            state_harvest.get("micro_breakout_readiness_state"),
        ).upper(),
        "micro_reversal_risk_state": _pick_text(
            payload.get("micro_reversal_risk_state"),
            state_harvest.get("micro_reversal_risk_state"),
        ).upper(),
        "micro_participation_state": _pick_text(
            payload.get("micro_participation_state"),
            state_harvest.get("micro_participation_state"),
        ).upper(),
        "micro_gap_context_state": _pick_text(
            payload.get("micro_gap_context_state"),
            state_harvest.get("micro_gap_context_state"),
        ).upper(),
        "micro_body_size_pct_20": _pick_float(
            payload.get("micro_body_size_pct_20"),
            secondary_harvest.get("source_micro_body_size_pct_20"),
        ),
        "micro_doji_ratio_20": _pick_float(
            payload.get("micro_doji_ratio_20"),
            secondary_harvest.get("source_micro_doji_ratio_20"),
        ),
        "micro_range_compression_ratio_20": _pick_float(
            payload.get("micro_range_compression_ratio_20"),
            secondary_harvest.get("source_micro_range_compression_ratio_20"),
        ),
        "micro_volume_burst_ratio_20": _pick_float(
            payload.get("micro_volume_burst_ratio_20"),
            secondary_harvest.get("source_micro_volume_burst_ratio_20"),
        ),
        "micro_volume_burst_decay_20": _pick_float(
            payload.get("micro_volume_burst_decay_20"),
            secondary_harvest.get("source_micro_volume_burst_decay_20"),
        ),
        "micro_gap_fill_progress": _pick_float(
            payload.get("micro_gap_fill_progress"),
            secondary_harvest.get("source_micro_gap_fill_progress"),
        ),
        "micro_upper_wick_ratio_20": _pick_float(
            payload.get("micro_upper_wick_ratio_20"),
            secondary_harvest.get("source_micro_upper_wick_ratio_20"),
        ),
        "micro_lower_wick_ratio_20": _pick_float(
            payload.get("micro_lower_wick_ratio_20"),
            secondary_harvest.get("source_micro_lower_wick_ratio_20"),
        ),
        "micro_same_color_run_current": int(
            _pick_float(
                payload.get("micro_same_color_run_current"),
                secondary_harvest.get("source_micro_same_color_run_current"),
                default=0.0,
            )
        ),
        "micro_same_color_run_max_20": int(
            _pick_float(
                payload.get("micro_same_color_run_max_20"),
                secondary_harvest.get("source_micro_same_color_run_max_20"),
                default=0.0,
            )
        ),
        "micro_swing_high_retest_count_20": int(
            _pick_float(
                payload.get("micro_swing_high_retest_count_20"),
                secondary_harvest.get("source_micro_swing_high_retest_count_20"),
                default=0.0,
            )
        ),
        "micro_swing_low_retest_count_20": int(
            _pick_float(
                payload.get("micro_swing_low_retest_count_20"),
                secondary_harvest.get("source_micro_swing_low_retest_count_20"),
                default=0.0,
            )
        ),
        "micro_bull_ratio_20": _pick_float(
            payload.get("micro_bull_ratio_20"),
            secondary_harvest.get("source_micro_bull_ratio_20"),
        ),
        "micro_bear_ratio_20": _pick_float(
            payload.get("micro_bear_ratio_20"),
            secondary_harvest.get("source_micro_bear_ratio_20"),
        ),
        "state25_weight_log_only_enabled": bool(
            weight_surface.get("log_only_enabled", False)
        ),
        "state25_weight_bounded_live_enabled": bool(
            weight_surface.get("bounded_live_enabled", False)
        ),
        "state25_teacher_weight_overrides": dict(
            weight_surface.get("live_teacher_weight_overrides", {}) or {}
        ),
        "state25_teacher_weight_override_display_ko": list(
            weight_surface.get("teacher_weight_override_display_ko", []) or []
        ),
    }


def build_state25_runtime_hint_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    scene_snapshot = _scene_snapshot_from_runtime_row(row)
    teacher_payload = build_teacher_pattern_payload_v2(scene_snapshot)
    if not teacher_payload:
        return {
            "contract_version": STATE25_RUNTIME_HINT_CONTRACT_VERSION,
            "available": False,
            "scene_source": "teacher_pattern_rule_runtime_hint_v1",
            "scene_pattern_id": 0,
            "scene_pattern_name": "",
            "scene_family": "unknown",
            "scene_group_hint": "",
            "candidate_pattern_ids": [],
            "entry_bias_hint": "",
            "wait_bias_hint": "",
            "exit_bias_hint": "",
            "transition_risk_hint": "",
            "confidence": 0.0,
            "primary_score": 0.0,
            "secondary_score": 0.0,
            "reason_summary": "insufficient_scene_signal",
        }

    primary_id = int(teacher_payload.get("teacher_pattern_id", 0) or 0)
    secondary_id = int(teacher_payload.get("teacher_pattern_secondary_id", 0) or 0)
    candidate_ids = [pattern_id for pattern_id in (primary_id, secondary_id) if pattern_id > 0]
    pattern_name = str(teacher_payload.get("teacher_pattern_name", "") or "")
    group_hint = str(teacher_payload.get("teacher_pattern_group", "") or "")
    entry_bias = str(teacher_payload.get("teacher_entry_bias", "") or "")
    wait_bias = str(teacher_payload.get("teacher_wait_bias", "") or "")
    exit_bias = str(teacher_payload.get("teacher_exit_bias", "") or "")
    transition_risk = str(teacher_payload.get("teacher_transition_risk", "") or "")
    confidence = _to_float(teacher_payload.get("teacher_label_confidence"), 0.0)
    primary_score = _to_float(teacher_payload.get("teacher_primary_score"), 0.0)
    secondary_score = _to_float(teacher_payload.get("teacher_secondary_score"), 0.0)
    reason_summary = "|".join(
        item
        for item in (pattern_name, group_hint, entry_bias, wait_bias, transition_risk)
        if item
    )
    return {
        "contract_version": STATE25_RUNTIME_HINT_CONTRACT_VERSION,
        "available": True,
        "scene_source": "teacher_pattern_rule_runtime_hint_v1",
        "scene_pattern_id": primary_id,
        "scene_pattern_name": pattern_name,
        "scene_family": f"pattern_{primary_id}" if primary_id > 0 else "unknown",
        "scene_group_hint": group_hint,
        "candidate_pattern_ids": candidate_ids,
        "entry_bias_hint": entry_bias,
        "wait_bias_hint": wait_bias,
        "exit_bias_hint": exit_bias,
        "transition_risk_hint": transition_risk,
        "confidence": confidence,
        "primary_score": primary_score,
        "secondary_score": secondary_score,
        "reason_summary": reason_summary,
    }


def build_forecast_runtime_summary_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    transition = _coerce_mapping(payload.get("transition_forecast_v1"))
    management = _coerce_mapping(payload.get("trade_management_forecast_v1"))
    gap_metrics = _coerce_mapping(payload.get("forecast_gap_metrics_v1"))
    transition_meta = _coerce_mapping(transition.get("metadata"))
    management_meta = _coerce_mapping(management.get("metadata"))

    buy_confirm = _to_float(transition.get("p_buy_confirm"), 0.0)
    sell_confirm = _to_float(transition.get("p_sell_confirm"), 0.0)
    confirm_side = _pick_text(
        transition_meta.get("dominant_side"),
        "BUY" if buy_confirm >= sell_confirm and buy_confirm > 0.0 else "",
        "SELL" if sell_confirm > buy_confirm else "",
    ).upper()
    confirm_score = max(buy_confirm, sell_confirm)
    false_break_score = _to_float(transition.get("p_false_break"), 0.0)
    continuation_score = _to_float(transition.get("p_continuation_success"), 0.0)
    fail_now_score = _to_float(management.get("p_fail_now"), 0.0)
    continue_favor_score = _to_float(management.get("p_continue_favor"), 0.0)
    wait_confirm_gap = _pick_float(gap_metrics.get("wait_confirm_gap"), payload.get("wait_confirm_gap"))
    hold_exit_gap = _pick_float(gap_metrics.get("hold_exit_gap"), payload.get("hold_exit_gap"))
    same_side_flip_gap = _pick_float(
        gap_metrics.get("same_side_flip_gap"),
        payload.get("same_side_flip_gap"),
    )
    belief_barrier_tension_gap = _pick_float(
        gap_metrics.get("belief_barrier_tension_gap"),
        payload.get("belief_barrier_tension_gap"),
    )

    if wait_confirm_gap >= 0.15 and confirm_score >= max(false_break_score, 0.35):
        decision_hint = "CONFIRM_BIASED"
    elif wait_confirm_gap <= -0.15:
        decision_hint = "WAIT_BIASED"
    elif hold_exit_gap <= -0.12:
        decision_hint = "FAST_EXIT_BIASED"
    elif hold_exit_gap >= 0.12:
        decision_hint = "HOLD_BIASED"
    else:
        decision_hint = "BALANCED"

    payload_out = {
        "contract_version": FORECAST_RUNTIME_SUMMARY_CONTRACT_VERSION,
        "available": bool(transition or management or gap_metrics),
        "confirm_side": confirm_side,
        "confirm_score": float(confirm_score),
        "false_break_score": float(false_break_score),
        "continuation_score": float(continuation_score),
        "continue_favor_score": float(continue_favor_score),
        "fail_now_score": float(fail_now_score),
        "wait_confirm_gap": float(wait_confirm_gap),
        "hold_exit_gap": float(hold_exit_gap),
        "same_side_flip_gap": float(same_side_flip_gap),
        "belief_barrier_tension_gap": float(belief_barrier_tension_gap),
        "transition_mapper_version": str(transition_meta.get("mapper_version", "") or ""),
        "management_mapper_version": str(management_meta.get("mapper_version", "") or ""),
        "decision_hint": decision_hint,
    }
    return _attach_forecast_registry_binding(
        payload_out,
        field_order=_FORECAST_RUNTIME_SUMMARY_FIELD_ORDER,
        primary_field="decision_hint",
    )


def build_entry_wait_exit_bridge_v1(
    state25_runtime_hint_v1: Mapping[str, Any] | None,
    forecast_runtime_summary_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    scene = _coerce_mapping(state25_runtime_hint_v1)
    forecast = _coerce_mapping(forecast_runtime_summary_v1)
    wait_confirm_gap = _to_float(forecast.get("wait_confirm_gap"), 0.0)
    hold_exit_gap = _to_float(forecast.get("hold_exit_gap"), 0.0)
    same_side_flip_gap = _to_float(forecast.get("same_side_flip_gap"), 0.0)
    confirm_score = _to_float(forecast.get("confirm_score"), 0.0)
    false_break_score = _to_float(forecast.get("false_break_score"), 0.0)
    wait_bias_hint = _to_text(scene.get("wait_bias_hint"))
    transition_risk_hint = _to_text(scene.get("transition_risk_hint"))

    prefer_entry_now = bool(wait_confirm_gap >= 0.12 and confirm_score >= max(false_break_score, 0.35))
    prefer_wait_now = bool(wait_confirm_gap <= -0.12 or "WAIT" in wait_bias_hint.upper())
    prefer_hold_if_entered = bool(hold_exit_gap >= 0.10 and same_side_flip_gap >= 0.0)
    prefer_fast_cut_if_entered = bool(
        hold_exit_gap <= -0.12 or "HIGH" in transition_risk_hint.upper()
    )

    if prefer_entry_now:
        entry_quality_hint = "ENTRY_NOW"
    elif prefer_wait_now:
        entry_quality_hint = "WAIT_FIRST"
    else:
        entry_quality_hint = "ENTRY_BALANCED"

    if prefer_wait_now and not prefer_entry_now:
        wait_quality_hint = "WAIT_SUPPORTED"
    elif prefer_entry_now and "WAIT" in wait_bias_hint.upper():
        wait_quality_hint = "WAIT_LAGGING"
    else:
        wait_quality_hint = "WAIT_BALANCED"

    if prefer_hold_if_entered and not prefer_fast_cut_if_entered:
        management_quality_hint = "HOLD_SUPPORTED"
    elif prefer_fast_cut_if_entered:
        management_quality_hint = "FAST_CUT_SUPPORTED"
    else:
        management_quality_hint = "MANAGEMENT_BALANCED"

    payload_out = {
        "contract_version": ENTRY_WAIT_EXIT_BRIDGE_CONTRACT_VERSION,
        "entry_quality_hint": entry_quality_hint,
        "wait_quality_hint": wait_quality_hint,
        "management_quality_hint": management_quality_hint,
        "prefer_entry_now": prefer_entry_now,
        "prefer_wait_now": prefer_wait_now,
        "prefer_hold_if_entered": prefer_hold_if_entered,
        "prefer_fast_cut_if_entered": prefer_fast_cut_if_entered,
        "reason_summary": "|".join(
            item
            for item in (entry_quality_hint, wait_quality_hint, management_quality_hint)
            if item
        ),
    }
    return _attach_forecast_registry_binding(
        payload_out,
        field_order=_ENTRY_WAIT_EXIT_FIELD_ORDER,
        primary_field="prefer_entry_now",
    )


def build_forecast_state25_log_only_overlay_candidates_v1(
    state25_runtime_hint_v1: Mapping[str, Any] | None,
    forecast_runtime_summary_v1: Mapping[str, Any] | None,
    entry_wait_exit_bridge_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    scene = _coerce_mapping(state25_runtime_hint_v1)
    forecast = _coerce_mapping(forecast_runtime_summary_v1)
    bridge = _coerce_mapping(entry_wait_exit_bridge_v1)

    scene_available = bool(scene.get("available", False))
    forecast_available = bool(forecast.get("available", False))
    bridge_available = bool(bridge)
    available = bool(scene_available and forecast_available and bridge_available)

    confirm_score = _to_float(forecast.get("confirm_score"), 0.0)
    false_break_score = _to_float(forecast.get("false_break_score"), 0.0)
    wait_confirm_gap = _to_float(forecast.get("wait_confirm_gap"), 0.0)
    hold_exit_gap = _to_float(forecast.get("hold_exit_gap"), 0.0)
    confidence = _to_float(scene.get("confidence"), 0.0)
    decision_hint = _to_text(forecast.get("decision_hint")).upper()
    entry_quality_hint = _to_text(bridge.get("entry_quality_hint")).upper()
    wait_quality_hint = _to_text(bridge.get("wait_quality_hint")).upper()
    management_quality_hint = _to_text(bridge.get("management_quality_hint")).upper()
    prefer_entry_now = bool(bridge.get("prefer_entry_now", False))
    prefer_wait_now = bool(bridge.get("prefer_wait_now", False))
    prefer_hold_if_entered = bool(bridge.get("prefer_hold_if_entered", False))
    prefer_fast_cut_if_entered = bool(bridge.get("prefer_fast_cut_if_entered", False))

    threshold_delta_points = 0
    size_multiplier_factor = 1.0
    wait_bias_action = "observe_only"
    management_bias = "neutral"
    reason_tokens: list[str] = []

    if available:
        if prefer_entry_now and decision_hint == "CONFIRM_BIASED":
            threshold_delta_points = -3 if confirm_score >= 0.70 and confidence >= 0.55 else -2
            reason_tokens.append("entry_confirm_relief")
        elif prefer_wait_now or decision_hint == "WAIT_BIASED":
            threshold_delta_points = 2
            reason_tokens.append("wait_bias_hold")
        elif entry_quality_hint == "ENTRY_BALANCED" and confirm_score >= max(false_break_score, 0.45):
            threshold_delta_points = -1
            reason_tokens.append("balanced_entry_relief")

        if prefer_entry_now and prefer_hold_if_entered and hold_exit_gap >= 0.10:
            size_multiplier_factor = 1.10
            reason_tokens.append("hold_supported_size_up")
        elif prefer_fast_cut_if_entered or false_break_score >= 0.60:
            size_multiplier_factor = 0.85
            reason_tokens.append("fast_cut_size_down")

        if entry_quality_hint == "ENTRY_NOW" and wait_quality_hint != "WAIT_SUPPORTED":
            wait_bias_action = "release_wait_bias"
            reason_tokens.append("wait_release")
        elif wait_quality_hint == "WAIT_SUPPORTED" or prefer_wait_now:
            wait_bias_action = "reinforce_wait_bias"
            reason_tokens.append("wait_reinforce")

        if management_quality_hint == "HOLD_SUPPORTED" and not prefer_fast_cut_if_entered:
            management_bias = "hold_bias"
            reason_tokens.append("hold_bias")
        elif management_quality_hint == "FAST_CUT_SUPPORTED" or prefer_fast_cut_if_entered:
            management_bias = "fast_cut_bias"
            reason_tokens.append("fast_cut_bias")

    enabled = bool(
        available
        and (
            threshold_delta_points != 0
            or abs(size_multiplier_factor - 1.0) >= 1e-9
            or wait_bias_action != "observe_only"
            or management_bias != "neutral"
        )
    )

    return {
        "contract_version": FORECAST_STATE25_LOG_ONLY_OVERLAY_CANDIDATES_CONTRACT_VERSION,
        "available": available,
        "enabled": enabled,
        "overlay_mode": "log_only",
        "scene_pattern_id": int(scene.get("scene_pattern_id", 0) or 0),
        "scene_group_hint": str(scene.get("scene_group_hint", "") or ""),
        "decision_hint": decision_hint,
        "threshold_delta_points": int(threshold_delta_points),
        "size_multiplier_factor": round(float(size_multiplier_factor), 6),
        "wait_bias_action": wait_bias_action,
        "management_bias": management_bias,
        "reason_summary": "|".join(reason_tokens),
    }


def build_forecast_state25_log_only_overlay_trace_v1(
    runtime_bridge: Mapping[str, Any] | None,
    *,
    symbol: str,
    entry_stage: str,
    actual_effective_entry_threshold: float | int,
    actual_size_multiplier: float | int,
) -> dict[str, Any]:
    bridge = _coerce_mapping(runtime_bridge)
    scene = _coerce_mapping(bridge.get("state25_runtime_hint_v1"))
    forecast = _coerce_mapping(bridge.get("forecast_runtime_summary_v1"))
    overlay = _coerce_mapping(bridge.get("log_only_overlay_candidates_v1"))

    actual_threshold = float(actual_effective_entry_threshold or 0.0)
    actual_multiplier = max(0.0, _to_float(actual_size_multiplier, 1.0))
    threshold_delta = int(overlay.get("threshold_delta_points", 0) or 0)
    size_factor = max(0.0, _to_float(overlay.get("size_multiplier_factor"), 1.0))
    candidate_threshold = max(1.0, actual_threshold + float(threshold_delta))
    candidate_multiplier = max(0.01, actual_multiplier * size_factor)

    return {
        "contract_version": FORECAST_STATE25_LOG_ONLY_OVERLAY_TRACE_CONTRACT_VERSION,
        "symbol": str(symbol or "").upper().strip(),
        "entry_stage": str(entry_stage or "").upper().strip(),
        "scene_pattern_id": int(scene.get("scene_pattern_id", 0) or 0),
        "scene_group_hint": str(scene.get("scene_group_hint", "") or ""),
        "decision_hint": str(forecast.get("decision_hint", "") or ""),
        "binding_mode": "log_only",
        "overlay_available": bool(overlay.get("available", False)),
        "overlay_enabled": bool(overlay.get("enabled", False)),
        "actual_effective_entry_threshold": float(actual_threshold),
        "candidate_effective_entry_threshold": float(candidate_threshold),
        "candidate_entry_threshold_delta": round(float(candidate_threshold - actual_threshold), 6),
        "actual_size_multiplier": float(actual_multiplier),
        "candidate_size_multiplier": round(float(candidate_multiplier), 6),
        "candidate_size_multiplier_delta": round(float(candidate_multiplier - actual_multiplier), 6),
        "candidate_wait_bias_action": str(overlay.get("wait_bias_action", "observe_only") or "observe_only"),
        "candidate_management_bias": str(overlay.get("management_bias", "neutral") or "neutral"),
        "reason_summary": str(overlay.get("reason_summary", "") or ""),
    }


def build_forecast_state25_runtime_bridge_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    state25_runtime_hint_v1 = build_state25_runtime_hint_v1(row)
    forecast_runtime_summary_v1 = build_forecast_runtime_summary_v1(row)
    entry_wait_exit_bridge_v1 = build_entry_wait_exit_bridge_v1(
        state25_runtime_hint_v1,
        forecast_runtime_summary_v1,
    )
    log_only_overlay_candidates_v1 = build_forecast_state25_log_only_overlay_candidates_v1(
        state25_runtime_hint_v1,
        forecast_runtime_summary_v1,
        entry_wait_exit_bridge_v1,
    )
    all_forecast_target_registry_keys = _normalize_registry_key_list(
        [
            *list(forecast_runtime_summary_v1.get("target_registry_keys") or []),
            *list(entry_wait_exit_bridge_v1.get("target_registry_keys") or []),
        ]
    )
    bridge_binding_mode = (
        LEARNING_REGISTRY_BINDING_MODE_DERIVED
        if all_forecast_target_registry_keys
        else LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    )
    bridge_binding_fields = build_learning_registry_binding_fields(
        _forecast_registry_key("decision_hint"),
        binding_mode=bridge_binding_mode,
    )
    bridge_relation = build_learning_registry_relation(
        evidence_registry_keys=all_forecast_target_registry_keys,
        target_registry_keys=all_forecast_target_registry_keys,
        binding_mode=bridge_binding_mode,
    )
    forecast_registry_report_lines_ko = [
        "forecast 보조 판단:",
        *list(forecast_runtime_summary_v1.get("registry_report_lines_ko") or []),
        *list(entry_wait_exit_bridge_v1.get("registry_report_lines_ko") or []),
    ]
    return {
        "contract_version": FORECAST_STATE25_RUNTIME_BRIDGE_CONTRACT_VERSION,
        "scope_freeze_contract_version": FORECAST_STATE25_SCOPE_FREEZE_CONTRACT_VERSION,
        "direct_binding_report_contract_version": FORECAST_DIRECT_BINDING_REPORT_CONTRACT_VERSION,
        "scene_source": str(state25_runtime_hint_v1.get("scene_source", "") or ""),
        **bridge_binding_fields,
        "registry_binding_ready": bool(bridge_binding_fields.get("registry_found")) and bool(bridge_relation.get("binding_ready")),
        "evidence_registry_keys": bridge_relation.get("evidence_registry_keys", []),
        "target_registry_keys": bridge_relation.get("target_registry_keys", []),
        "evidence_bindings": bridge_relation.get("evidence_bindings", []),
        "target_bindings": bridge_relation.get("target_bindings", []),
        "forecast_registry_report_lines_ko": forecast_registry_report_lines_ko,
        "state25_runtime_hint_v1": state25_runtime_hint_v1,
        "forecast_runtime_summary_v1": forecast_runtime_summary_v1,
        "entry_wait_exit_bridge_v1": entry_wait_exit_bridge_v1,
        "log_only_overlay_candidates_v1": log_only_overlay_candidates_v1,
    }
