"""AI2 baseline-no-action candidate bridge helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION = "entry_candidate_bridge_v1"
ENTRY_CANDIDATE_BRIDGE_SCALAR_FIELDS = [
    "entry_candidate_bridge_contract_version",
    "entry_candidate_bridge_baseline_no_action",
    "entry_candidate_bridge_mode",
    "entry_candidate_bridge_active_conflict",
    "entry_candidate_bridge_conflict_selected",
    "entry_candidate_bridge_effective_baseline_action",
    "entry_candidate_bridge_conflict_kind",
    "entry_candidate_bridge_available",
    "entry_candidate_bridge_selected",
    "entry_candidate_bridge_source",
    "entry_candidate_bridge_action",
    "entry_candidate_bridge_reason",
    "entry_candidate_bridge_confidence",
    "entry_candidate_bridge_candidate_count",
    "entry_candidate_surface_family",
    "entry_candidate_surface_state",
    "semantic_candidate_action",
    "semantic_candidate_confidence",
    "semantic_candidate_reason",
    "shadow_candidate_action",
    "shadow_candidate_confidence",
    "shadow_candidate_reason",
    "state25_candidate_action",
    "state25_candidate_confidence",
    "state25_candidate_reason",
    "breakout_candidate_action",
    "breakout_candidate_confidence",
    "breakout_candidate_reason",
    "breakout_candidate_source",
    "breakout_candidate_action_target",
    "breakout_candidate_direction",
    "breakout_candidate_conflict_action",
    "breakout_candidate_conflict_confidence",
    "breakout_candidate_conflict_mode",
    "breakout_candidate_surface_family",
    "breakout_candidate_surface_state",
    "countertrend_continuation_enabled",
    "countertrend_continuation_state",
    "countertrend_continuation_action",
    "countertrend_continuation_confidence",
    "countertrend_continuation_reason_summary",
    "countertrend_continuation_warning_count",
    "countertrend_continuation_surface_family",
    "countertrend_continuation_surface_state",
    "countertrend_anti_long_score",
    "countertrend_anti_short_score",
    "countertrend_pro_up_score",
    "countertrend_pro_down_score",
    "countertrend_directional_bias",
    "countertrend_action_state",
    "countertrend_directional_candidate_action",
    "countertrend_directional_execution_action",
    "countertrend_directional_state_reason",
    "countertrend_directional_state_rank",
    "countertrend_directional_owner_family",
    "countertrend_directional_down_bias_score",
    "countertrend_directional_up_bias_score",
    "countertrend_candidate_action",
    "countertrend_candidate_confidence",
    "countertrend_candidate_reason",
]

BASELINE_NO_ACTION_BRIDGE_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "rollout_mode",
    "recent_row_count",
    "baseline_no_action_row_count",
    "bridge_available_count",
    "bridge_selected_count",
    "breakout_candidate_count",
    "bridge_source_counts",
    "breakout_reason_counts",
    "recent_symbols",
    "recommended_next_action",
]


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _stable_join(values: pd.Series) -> str:
    seen: list[str] = []
    for raw in values.fillna("").astype(str):
        text = raw.strip()
        if not text or text in seen:
            continue
        seen.append(text)
    return ",".join(seen)


def _series_json_counts(values: pd.Series) -> str:
    counts = (
        values.fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _candidate_payload(
    *,
    source: str,
    action: str = "",
    confidence: float = 0.0,
    reason: str = "",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    action_u = _to_text(action).upper()
    payload = {
        "source": source,
        "available": action_u in {"BUY", "SELL"},
        "action": action_u if action_u in {"BUY", "SELL"} else "",
        "confidence": round(max(0.0, min(1.0, float(confidence))), 6),
        "reason": _to_text(reason),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _build_semantic_candidate(
    *,
    semantic_probe_bridge_action: str,
    semantic_probe_bridge_reason: str,
    semantic_shadow_prediction_v1: Mapping[str, Any] | None,
    probe_candidate_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    action_u = _to_text(semantic_probe_bridge_action).upper()
    if action_u not in {"BUY", "SELL"}:
        return _candidate_payload(source="semantic_candidate")
    prediction = _as_mapping(semantic_shadow_prediction_v1)
    probe_candidate = _as_mapping(probe_candidate_v1)
    timing_prob = _to_float(_as_mapping(prediction.get("timing")).get("probability"), 0.0)
    entry_prob = _to_float(_as_mapping(prediction.get("entry_quality")).get("probability"), 0.0)
    probe_support = _to_float(probe_candidate.get("candidate_support"), 0.0)
    confidence = max(timing_prob, entry_prob, probe_support, 0.55)
    return _candidate_payload(
        source="semantic_candidate",
        action=action_u,
        confidence=confidence,
        reason=_to_text(semantic_probe_bridge_reason, "semantic_probe_bridge"),
    )


def _build_shadow_candidate(
    *,
    semantic_shadow_prediction_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    prediction = _as_mapping(semantic_shadow_prediction_v1)
    action_u = _to_text(prediction.get("action_hint")).upper()
    timing = _as_mapping(prediction.get("timing"))
    entry = _as_mapping(prediction.get("entry_quality"))
    if action_u not in {"BUY", "SELL"}:
        return _candidate_payload(source="shadow_candidate")
    if not bool(prediction.get("available")) or not bool(prediction.get("should_enter")):
        return _candidate_payload(source="shadow_candidate")
    if not bool(timing.get("decision")) or not bool(entry.get("decision")):
        return _candidate_payload(source="shadow_candidate")
    confidence = max(
        min(_to_float(timing.get("probability"), 0.0), _to_float(entry.get("probability"), 0.0)),
        0.55,
    )
    return _candidate_payload(
        source="shadow_candidate",
        action=action_u,
        confidence=confidence,
        reason=_to_text(prediction.get("reason"), "shadow_should_enter"),
    )


def _build_state25_candidate(
    *,
    state25_candidate_log_only_trace_v1: Mapping[str, Any] | None,
    forecast_state25_runtime_bridge_v1: Mapping[str, Any] | None,
    forecast_state25_log_only_overlay_trace_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate_trace = _as_mapping(state25_candidate_log_only_trace_v1)
    forecast_bridge = _as_mapping(forecast_state25_runtime_bridge_v1)
    forecast = _as_mapping(forecast_bridge.get("forecast_runtime_summary_v1"))
    overlay_trace = _as_mapping(forecast_state25_log_only_overlay_trace_v1)
    binding_mode = _to_text(candidate_trace.get("binding_mode")).lower()
    confirm_side = _to_text(forecast.get("confirm_side")).upper()
    confirm_score = _to_float(forecast.get("confirm_score"), 0.0)
    decision_hint = _to_text(forecast.get("decision_hint")).upper()
    wait_bias_action = _to_text(overlay_trace.get("candidate_wait_bias_action")).lower()
    symbol_scope_hit = _to_bool(candidate_trace.get("threshold_symbol_scope_hit"), True) or _to_bool(
        candidate_trace.get("size_symbol_scope_hit"), True
    )
    stage_scope_hit = _to_bool(candidate_trace.get("threshold_stage_scope_hit"), True)
    if binding_mode == "disabled" or confirm_side not in {"BUY", "SELL"}:
        return _candidate_payload(source="state25_candidate")
    if not symbol_scope_hit or not stage_scope_hit:
        return _candidate_payload(source="state25_candidate")
    if confirm_score < 0.55 or decision_hint == "WAIT_BIASED":
        return _candidate_payload(source="state25_candidate")
    if wait_bias_action not in {"release_wait_bias", "neutral_wait_bias"}:
        return _candidate_payload(source="state25_candidate")
    return _candidate_payload(
        source="state25_candidate",
        action=confirm_side,
        confidence=confirm_score,
        reason=f"state25_forecast::{decision_hint.lower()}::{wait_bias_action}",
    )


def _normalize_breakout_conflict_metrics(
    *,
    breakout_detected: bool,
    target: str,
    confidence: float,
    failure_risk: float,
) -> tuple[float, float]:
    target_u = _to_text(target).upper()
    confidence_value = _to_float(confidence, 0.0)
    failure_risk_value = _to_float(failure_risk, 0.0)
    if not breakout_detected or target_u not in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        return confidence_value, failure_risk_value
    if confidence_value <= 0.0:
        confidence_value = (
            0.30
            if target_u == "WATCH_BREAKOUT"
            else 0.34
            if target_u == "PROBE_BREAKOUT"
            else 0.56
        )
    if failure_risk_value <= 0.0:
        failure_risk_value = (
            0.36
            if target_u == "WATCH_BREAKOUT"
            else 0.30
            if target_u == "PROBE_BREAKOUT"
            else 0.22
        )
    return confidence_value, failure_risk_value


def _build_breakout_candidate(
    *,
    breakout_event_runtime_v1: Mapping[str, Any] | None,
    breakout_event_overlay_candidates_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    runtime = _as_mapping(breakout_event_runtime_v1)
    overlay = _as_mapping(breakout_event_overlay_candidates_v1)
    target = _to_text(overlay.get("candidate_action_target")).upper()
    direction = _to_text(runtime.get("breakout_direction")).upper()
    if not bool(runtime.get("available")) or not bool(overlay.get("enabled")):
        return _candidate_payload(source="breakout_candidate")
    confidence = _to_float(runtime.get("breakout_confidence"), 0.0)
    failure_risk = _to_float(runtime.get("breakout_failure_risk"), 0.0)
    confidence, failure_risk = _normalize_breakout_conflict_metrics(
        breakout_detected=bool(runtime.get("breakout_detected")),
        target=target,
        confidence=confidence,
        failure_risk=failure_risk,
    )
    conflict_action = ""
    conflict_confidence = 0.0
    conflict_mode = ""
    if bool(runtime.get("breakout_detected")) and direction in {"UP", "DOWN"}:
        if target in {"PROBE_BREAKOUT", "ENTER_NOW"} and confidence >= 0.18 and failure_risk <= 0.50:
            conflict_action = "BUY" if direction == "UP" else "SELL"
            conflict_confidence = confidence
            conflict_mode = "active_action_conflict_resolution"
        elif target == "WATCH_BREAKOUT" and confidence >= 0.28 and failure_risk <= 0.40:
            conflict_action = "BUY" if direction == "UP" else "SELL"
            conflict_confidence = confidence
            conflict_mode = "watch_only_conflict_guard"
    if target != "ENTER_NOW" or direction not in {"UP", "DOWN"}:
        return _candidate_payload(
            source="breakout_candidate",
            extra={
                "candidate_action_target": target,
                "breakout_direction": direction,
                "candidate_source": "breakout_runtime_overlay",
                "conflict_candidate_action": conflict_action,
                "conflict_candidate_confidence": round(conflict_confidence, 6),
                "conflict_candidate_mode": conflict_mode,
            },
        )
    if not bool(runtime.get("breakout_detected")):
        return _candidate_payload(source="breakout_candidate")
    if confidence < 0.55 or failure_risk > 0.55:
        return _candidate_payload(source="breakout_candidate")
    action = "BUY" if direction == "UP" else "SELL"
    return _candidate_payload(
        source="breakout_candidate",
        action=action,
        confidence=confidence,
        reason="|".join(
            token
            for token in (
                _to_text(runtime.get("breakout_state")),
                _to_text(overlay.get("reason_summary")),
            )
            if token
        ),
        extra={
            "candidate_action_target": target,
            "breakout_direction": direction,
            "candidate_source": "breakout_runtime_overlay",
            "conflict_candidate_action": conflict_action,
            "conflict_candidate_confidence": round(conflict_confidence, 6),
            "conflict_candidate_mode": conflict_mode,
        },
    )


def _build_breakout_conflict_candidate(
    *,
    baseline_action: str,
    breakout_event_runtime_v1: Mapping[str, Any] | None,
    breakout_event_overlay_candidates_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = _build_breakout_candidate(
        breakout_event_runtime_v1=breakout_event_runtime_v1,
        breakout_event_overlay_candidates_v1=breakout_event_overlay_candidates_v1,
    )
    baseline_action_u = _to_text(baseline_action).upper()
    conflict_action = _to_text(candidate.get("conflict_candidate_action")).upper()
    if conflict_action not in {"BUY", "SELL"}:
        return _candidate_payload(source="breakout_candidate")
    if baseline_action_u in {"BUY", "SELL"} and conflict_action == baseline_action_u:
        return _candidate_payload(source="breakout_candidate")
    confidence = max(_to_float(candidate.get("conflict_candidate_confidence"), 0.0), 0.42)
    return _candidate_payload(
        source="breakout_candidate",
        action=conflict_action,
        confidence=confidence,
        reason=_to_text(candidate.get("reason"), "breakout_conflict_candidate"),
        extra={
            "candidate_action_target": _to_text(candidate.get("candidate_action_target")).upper(),
            "breakout_direction": _to_text(candidate.get("breakout_direction")).upper(),
            "candidate_source": _to_text(
                candidate.get("candidate_source"),
                "breakout_runtime_overlay",
            ),
            "candidate_mode": _to_text(
                candidate.get("conflict_candidate_mode"),
                "active_action_conflict_resolution",
            ),
        },
    )


def _build_countertrend_candidate(
    *,
    countertrend_continuation_signal_v1: Mapping[str, Any] | None,
) -> dict[str, Any]:
    signal = _as_mapping(countertrend_continuation_signal_v1)
    directional_candidate_action = _to_text(
        signal.get("directional_candidate_action")
    ).upper()
    directional_state = _to_text(signal.get("directional_action_state")).upper()
    if directional_candidate_action in {"BUY", "SELL"} and directional_state in {
        "UP_PROBE",
        "DOWN_PROBE",
        "UP_ENTER",
        "DOWN_ENTER",
    }:
        return _candidate_payload(
            source="countertrend_candidate",
            action=directional_candidate_action,
            confidence=max(_to_float(signal.get("signal_confidence"), 0.0), 0.55),
            reason=_to_text(signal.get("reason_summary"), "countertrend_continuation"),
            extra={
                "candidate_source": "countertrend_continuation_signal_v1",
                "surface_family": _to_text(signal.get("surface_family")),
                "surface_state": _to_text(signal.get("surface_state")),
                "directional_bias": _to_text(signal.get("directional_bias")),
                "directional_action_state": directional_state,
                "directional_execution_action": _to_text(
                    signal.get("directional_execution_action")
                ).upper(),
            },
        )
    action_u = _to_text(signal.get("signal_action")).upper()
    if not bool(signal.get("enabled")) or action_u not in {"BUY", "SELL"}:
        return _candidate_payload(source="countertrend_candidate")
    return _candidate_payload(
        source="countertrend_candidate",
        action=action_u,
        confidence=max(_to_float(signal.get("signal_confidence"), 0.0), 0.55),
        reason=_to_text(signal.get("reason_summary"), "countertrend_continuation"),
        extra={
            "candidate_source": "countertrend_continuation_signal_v1",
            "surface_family": _to_text(signal.get("surface_family")),
            "surface_state": _to_text(signal.get("surface_state")),
        },
    )


def _candidate_priority(source: str) -> int:
    return {
        "countertrend_candidate": 5,
        "breakout_candidate": 4,
        "semantic_candidate": 3,
        "shadow_candidate": 2,
        "state25_candidate": 1,
    }.get(_to_text(source), 0)


def _derive_breakout_surface_hint(
    runtime: Mapping[str, Any] | None,
    overlay: Mapping[str, Any] | None,
) -> tuple[str, str]:
    breakout = _as_mapping(runtime)
    overlay_payload = _as_mapping(overlay)
    breakout_state = _to_text(breakout.get("breakout_state")).lower()
    breakout_type = _to_text(breakout.get("breakout_type_candidate")).lower()
    target = _to_text(overlay_payload.get("candidate_action_target")).upper()

    if target == "EXIT_PROTECT":
        return "protective_exit_surface", "protect_exit"
    if breakout_state == "breakout_continuation" or breakout_type == "continuation_breakout_candidate":
        return "follow_through_surface", "continuation_follow"
    if breakout_state == "breakout_pullback" or breakout_type == "reclaim_breakout_candidate":
        return "follow_through_surface", "pullback_resume"
    if breakout_state == "initial_breakout" or breakout_type == "initial_breakout_candidate":
        return "initial_entry_surface", "initial_break"
    if target in {"PROBE_BREAKOUT", "WATCH_BREAKOUT"}:
        return "follow_through_surface", "pullback_resume"
    return "", ""


def _derive_selected_surface_hint(
    *,
    selected_source: str,
    observe_reason: str,
    blocked_by: str,
    breakout_event_runtime_v1: Mapping[str, Any] | None,
    breakout_event_overlay_candidates_v1: Mapping[str, Any] | None,
) -> tuple[str, str]:
    source_u = _to_text(selected_source)
    observe_reason_u = _to_text(observe_reason).lower()
    blocked_by_u = _to_text(blocked_by).lower()

    if source_u == "breakout_candidate":
        return _derive_breakout_surface_hint(
            breakout_event_runtime_v1,
            breakout_event_overlay_candidates_v1,
        )
    if source_u == "countertrend_candidate":
        return "follow_through_surface", "continuation_follow"
    if observe_reason_u == "outer_band_reversal_support_required_observe" or blocked_by_u == "outer_band_guard":
        return "follow_through_surface", "pullback_resume"
    if observe_reason_u in {"lower_rebound_probe_observe", "middle_sr_anchor_required_observe"}:
        return "initial_entry_surface", "timing_better_entry"
    if source_u in {"semantic_candidate", "shadow_candidate", "state25_candidate"}:
        return "initial_entry_surface", "initial_break"
    return "", ""


def build_entry_candidate_bridge_v1(
    *,
    symbol: str,
    action: str,
    entry_stage: str,
    core_reason: str = "",
    observe_reason: str = "",
    action_none_reason: str = "",
    blocked_by: str = "",
    compatibility_mode: str = "",
    semantic_probe_bridge_action: str = "",
    semantic_probe_bridge_reason: str = "",
    entry_probe_plan_v1: Mapping[str, Any] | None = None,
    entry_default_side_gate_v1: Mapping[str, Any] | None = None,
    probe_candidate_v1: Mapping[str, Any] | None = None,
    semantic_shadow_prediction_v1: Mapping[str, Any] | None = None,
    state25_candidate_log_only_trace_v1: Mapping[str, Any] | None = None,
    forecast_state25_runtime_bridge_v1: Mapping[str, Any] | None = None,
    forecast_state25_log_only_overlay_trace_v1: Mapping[str, Any] | None = None,
    breakout_event_runtime_v1: Mapping[str, Any] | None = None,
    breakout_event_overlay_candidates_v1: Mapping[str, Any] | None = None,
    countertrend_continuation_signal_v1: Mapping[str, Any] | None = None,
    active_action_conflict_guard_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_action = _to_text(action).upper()
    conflict_guard = _as_mapping(active_action_conflict_guard_v1)
    effective_baseline_action = baseline_action or _to_text(
        conflict_guard.get("baseline_action")
    ).upper()
    baseline_no_action = effective_baseline_action not in {"BUY", "SELL"}
    active_conflict_detected = _to_bool(conflict_guard.get("conflict_detected", False))
    conflict_resolution_active = bool(
        active_conflict_detected
        and (
            _to_bool(conflict_guard.get("guard_applied", False))
            or _to_bool(conflict_guard.get("guard_eligible", False))
        )
    )
    conflict_kind = _to_text(conflict_guard.get("conflict_kind"))
    bridge_mode = (
        "no_action_rescue"
        if baseline_no_action
        else (
            "active_action_conflict_resolution"
            if conflict_resolution_active
            else "baseline_action_keep"
        )
    )
    sources = {
        "semantic_candidate": _build_semantic_candidate(
            semantic_probe_bridge_action=semantic_probe_bridge_action,
            semantic_probe_bridge_reason=semantic_probe_bridge_reason,
            semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
            probe_candidate_v1=probe_candidate_v1,
        ),
        "shadow_candidate": _build_shadow_candidate(
            semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
        ),
        "state25_candidate": _build_state25_candidate(
            state25_candidate_log_only_trace_v1=state25_candidate_log_only_trace_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
            forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
        ),
        "breakout_candidate": _build_breakout_candidate(
            breakout_event_runtime_v1=breakout_event_runtime_v1,
            breakout_event_overlay_candidates_v1=breakout_event_overlay_candidates_v1,
        ),
        "countertrend_candidate": _build_countertrend_candidate(
            countertrend_continuation_signal_v1=countertrend_continuation_signal_v1,
        ),
    }
    valid_candidates = [
        candidate
        for candidate in sources.values()
        if _to_text(candidate.get("action")).upper() in {"BUY", "SELL"}
    ]
    valid_candidates.sort(
        key=lambda candidate: (
            _to_float(candidate.get("confidence"), 0.0),
            _candidate_priority(_to_text(candidate.get("source"))),
        ),
        reverse=True,
    )
    conflict_candidates = [
        candidate
        for candidate in valid_candidates
        if effective_baseline_action in {"BUY", "SELL"}
        and _to_text(candidate.get("action")).upper() in {"BUY", "SELL"}
        and _to_text(candidate.get("action")).upper() != effective_baseline_action
    ]
    breakout_conflict_candidate = _build_breakout_conflict_candidate(
        baseline_action=effective_baseline_action,
        breakout_event_runtime_v1=breakout_event_runtime_v1,
        breakout_event_overlay_candidates_v1=breakout_event_overlay_candidates_v1,
    )
    if (
        conflict_resolution_active
        and _to_text(breakout_conflict_candidate.get("action")).upper() in {"BUY", "SELL"}
    ):
        conflict_candidates.append(breakout_conflict_candidate)
        conflict_candidates.sort(
            key=lambda candidate: (
                _to_float(candidate.get("confidence"), 0.0),
                _candidate_priority(_to_text(candidate.get("source"))),
            ),
            reverse=True,
        )
    selected = {}
    if baseline_no_action and valid_candidates:
        selected = valid_candidates[0]
    elif conflict_resolution_active and conflict_candidates:
        selected = conflict_candidates[0]
    selected_surface_family, selected_surface_state = _derive_selected_surface_hint(
        selected_source=_to_text(selected.get("source")),
        observe_reason=observe_reason,
        blocked_by=blocked_by,
        breakout_event_runtime_v1=breakout_event_runtime_v1,
        breakout_event_overlay_candidates_v1=breakout_event_overlay_candidates_v1,
    )
    breakout_surface_family, breakout_surface_state = _derive_breakout_surface_hint(
        breakout_event_runtime_v1,
        breakout_event_overlay_candidates_v1,
    )
    return {
        "contract_version": ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION,
        "symbol": _to_text(symbol).upper(),
        "entry_stage": _to_text(entry_stage).upper(),
        "baseline_action": baseline_action,
        "effective_baseline_action": effective_baseline_action,
        "baseline_no_action": baseline_no_action,
        "bridge_mode": bridge_mode,
        "active_conflict_detected": bool(active_conflict_detected),
        "conflict_resolution_active": bool(conflict_resolution_active),
        "conflict_kind": conflict_kind,
        "core_reason": _to_text(core_reason),
        "observe_reason": _to_text(observe_reason),
        "action_none_reason": _to_text(action_none_reason),
        "blocked_by": _to_text(blocked_by),
        "compatibility_mode": _to_text(compatibility_mode),
        "candidate_available": bool(selected),
        "candidate_count": (
            len(valid_candidates)
            if baseline_no_action
            else len(conflict_candidates) if conflict_resolution_active else 0
        ),
        "conflict_selected": bool(conflict_resolution_active and selected),
        "selected_source": _to_text(selected.get("source")),
        "selected_action": _to_text(selected.get("action")).upper(),
        "selected_confidence": round(_to_float(selected.get("confidence"), 0.0), 6),
        "selected_reason": _to_text(selected.get("reason")),
        "selected_surface_family": selected_surface_family,
        "selected_surface_state": selected_surface_state,
        "breakout_surface_family": breakout_surface_family,
        "breakout_surface_state": breakout_surface_state,
        "countertrend_continuation_signal_v1": dict(countertrend_continuation_signal_v1 or {}),
        "active_action_conflict_guard_v1": dict(active_action_conflict_guard_v1 or {}),
        "sources": sources,
        "entry_probe_plan_v1": dict(entry_probe_plan_v1 or {}),
        "entry_default_side_gate_v1": dict(entry_default_side_gate_v1 or {}),
    }


def build_entry_candidate_bridge_flat_fields(
    surface: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _as_mapping(surface)
    sources = _as_mapping(payload.get("sources"))
    semantic_candidate = _as_mapping(sources.get("semantic_candidate"))
    shadow_candidate = _as_mapping(sources.get("shadow_candidate"))
    state25_candidate = _as_mapping(sources.get("state25_candidate"))
    breakout_candidate = _as_mapping(sources.get("breakout_candidate"))
    countertrend_candidate = _as_mapping(sources.get("countertrend_candidate"))
    countertrend_signal = _as_mapping(payload.get("countertrend_continuation_signal_v1"))
    return {
        "entry_candidate_bridge_contract_version": _to_text(
            payload.get("contract_version"),
            ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION,
        ),
        "entry_candidate_bridge_baseline_no_action": bool(
            payload.get("baseline_no_action", False)
        ),
        "entry_candidate_bridge_mode": _to_text(payload.get("bridge_mode")),
        "entry_candidate_bridge_active_conflict": bool(
            payload.get("active_conflict_detected", False)
        ),
        "entry_candidate_bridge_conflict_selected": bool(
            payload.get("conflict_selected", False)
        ),
        "entry_candidate_bridge_effective_baseline_action": _to_text(
            payload.get("effective_baseline_action")
        ).upper(),
        "entry_candidate_bridge_conflict_kind": _to_text(payload.get("conflict_kind")),
        "entry_candidate_bridge_available": bool(payload.get("candidate_available", False)),
        "entry_candidate_bridge_selected": bool(
            _to_text(payload.get("selected_action")).upper() in {"BUY", "SELL"}
        ),
        "entry_candidate_bridge_source": _to_text(payload.get("selected_source")),
        "entry_candidate_bridge_action": _to_text(payload.get("selected_action")).upper(),
        "entry_candidate_bridge_reason": _to_text(payload.get("selected_reason")),
        "entry_candidate_bridge_confidence": round(
            _to_float(payload.get("selected_confidence"), 0.0),
            6,
        ),
        "entry_candidate_bridge_candidate_count": int(
            _to_float(payload.get("candidate_count"), 0.0)
        ),
        "entry_candidate_surface_family": _to_text(payload.get("selected_surface_family")),
        "entry_candidate_surface_state": _to_text(payload.get("selected_surface_state")),
        "entry_candidate_surface_v1": dict(payload),
        "semantic_candidate_action": _to_text(semantic_candidate.get("action")).upper(),
        "semantic_candidate_confidence": round(
            _to_float(semantic_candidate.get("confidence"), 0.0), 6
        ),
        "semantic_candidate_reason": _to_text(semantic_candidate.get("reason")),
        "shadow_candidate_action": _to_text(shadow_candidate.get("action")).upper(),
        "shadow_candidate_confidence": round(
            _to_float(shadow_candidate.get("confidence"), 0.0), 6
        ),
        "shadow_candidate_reason": _to_text(shadow_candidate.get("reason")),
        "state25_candidate_action": _to_text(state25_candidate.get("action")).upper(),
        "state25_candidate_confidence": round(
            _to_float(state25_candidate.get("confidence"), 0.0), 6
        ),
        "state25_candidate_reason": _to_text(state25_candidate.get("reason")),
        "breakout_candidate_action": _to_text(breakout_candidate.get("action")).upper(),
        "breakout_candidate_confidence": round(
            _to_float(breakout_candidate.get("confidence"), 0.0), 6
        ),
        "breakout_candidate_reason": _to_text(breakout_candidate.get("reason")),
        "breakout_candidate_source": _to_text(
            breakout_candidate.get("candidate_source"),
            _to_text(breakout_candidate.get("source")),
        ),
        "breakout_candidate_action_target": _to_text(
            breakout_candidate.get("candidate_action_target")
        ).upper(),
        "breakout_candidate_direction": _to_text(
            breakout_candidate.get("breakout_direction")
        ).upper(),
        "breakout_candidate_conflict_action": _to_text(
            breakout_candidate.get("conflict_candidate_action")
        ).upper(),
        "breakout_candidate_conflict_confidence": round(
            _to_float(breakout_candidate.get("conflict_candidate_confidence"), 0.0),
            6,
        ),
        "breakout_candidate_conflict_mode": _to_text(
            breakout_candidate.get("conflict_candidate_mode")
        ),
        "breakout_candidate_surface_family": _to_text(payload.get("breakout_surface_family")),
        "breakout_candidate_surface_state": _to_text(payload.get("breakout_surface_state")),
        "countertrend_continuation_enabled": bool(
            countertrend_signal.get("enabled", False)
        ),
        "countertrend_continuation_state": _to_text(
            countertrend_signal.get("signal_state"),
            _to_text(
                countertrend_candidate.get("surface_state"),
                "continuation_follow"
                if _to_text(countertrend_candidate.get("action")).upper() in {"BUY", "SELL"}
                else "",
            ),
        ),
        "countertrend_continuation_action": _to_text(
            countertrend_signal.get("signal_action"),
            _to_text(countertrend_candidate.get("action")).upper(),
        ).upper(),
        "countertrend_continuation_confidence": round(
            _to_float(
                countertrend_signal.get("signal_confidence"),
                _to_float(countertrend_candidate.get("confidence"), 0.0),
            ),
            6,
        ),
        "countertrend_continuation_reason_summary": _to_text(
            countertrend_signal.get("reason_summary"),
            _to_text(countertrend_candidate.get("reason")),
        ),
        "countertrend_continuation_warning_count": int(
            _to_float(countertrend_signal.get("warning_count"), 0.0)
        ),
        "countertrend_continuation_surface_family": _to_text(
            countertrend_signal.get("surface_family"),
            _to_text(
                countertrend_candidate.get("surface_family"),
                "follow_through_surface"
                if _to_text(countertrend_candidate.get("action")).upper() in {"BUY", "SELL"}
                else "",
            ),
        ),
        "countertrend_continuation_surface_state": _to_text(
            countertrend_signal.get("surface_state"),
            _to_text(countertrend_candidate.get("surface_state")),
        ),
        "countertrend_anti_long_score": round(
            _to_float(countertrend_signal.get("anti_long_score"), 0.0),
            6,
        ),
        "countertrend_anti_short_score": round(
            _to_float(countertrend_signal.get("anti_short_score"), 0.0),
            6,
        ),
        "countertrend_pro_up_score": round(
            _to_float(countertrend_signal.get("pro_up_score"), 0.0),
            6,
        ),
        "countertrend_pro_down_score": round(
            _to_float(countertrend_signal.get("pro_down_score"), 0.0),
            6,
        ),
        "countertrend_directional_bias": _to_text(countertrend_signal.get("directional_bias")),
        "countertrend_action_state": _to_text(
            countertrend_signal.get("directional_action_state")
        ).upper(),
        "countertrend_directional_candidate_action": _to_text(
            countertrend_signal.get("directional_candidate_action")
        ).upper(),
        "countertrend_directional_execution_action": _to_text(
            countertrend_signal.get("directional_execution_action")
        ).upper(),
        "countertrend_directional_state_reason": _to_text(
            countertrend_signal.get("directional_state_reason")
        ),
        "countertrend_directional_state_rank": int(
            _to_float(countertrend_signal.get("directional_state_rank"), 0.0)
        ),
        "countertrend_directional_owner_family": _to_text(
            countertrend_signal.get("directional_owner_family")
        ),
        "countertrend_directional_down_bias_score": round(
            _to_float(countertrend_signal.get("directional_down_bias_score"), 0.0),
            6,
        ),
        "countertrend_directional_up_bias_score": round(
            _to_float(countertrend_signal.get("directional_up_bias_score"), 0.0),
            6,
        ),
        "countertrend_candidate_action": _to_text(countertrend_candidate.get("action")).upper(),
        "countertrend_candidate_confidence": round(
            _to_float(countertrend_candidate.get("confidence"), 0.0), 6
        ),
        "countertrend_candidate_reason": _to_text(countertrend_candidate.get("reason")),
    }


def build_baseline_no_action_bridge(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    recent_limit: int = 200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    runtime = dict(runtime_status or {})
    decisions = entry_decisions.copy() if entry_decisions is not None else pd.DataFrame()
    if decisions.empty:
        empty = pd.DataFrame(columns=BASELINE_NO_ACTION_BRIDGE_COLUMNS)
        summary = {
            "contract_version": ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "recent_row_count": 0,
            "baseline_no_action_row_count": 0,
            "bridge_available_count": 0,
            "bridge_selected_count": 0,
            "breakout_candidate_count": 0,
            "recommended_next_action": "collect_recent_entry_rows",
        }
        return empty, summary

    decisions = decisions.copy()
    for column in (
        "time",
        "symbol",
        "action",
        "entry_authority_rejected_by",
        "entry_candidate_bridge_baseline_no_action",
        "entry_candidate_bridge_available",
        "entry_candidate_bridge_selected",
        "entry_candidate_bridge_source",
        "breakout_candidate_action",
        "breakout_candidate_reason",
    ):
        if column not in decisions.columns:
            decisions[column] = ""
    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    baseline_mask = (
        recent["entry_authority_rejected_by"].fillna("").astype(str).str.strip() == "baseline_no_action"
    )
    if not baseline_mask.any():
        baseline_mask = recent["entry_candidate_bridge_baseline_no_action"].fillna(False).astype(bool)
    if not baseline_mask.any():
        baseline_mask = recent["action"].fillna("").astype(str).str.strip().eq("")
    baseline = recent.loc[baseline_mask].copy()

    if baseline.empty:
        empty = pd.DataFrame(columns=BASELINE_NO_ACTION_BRIDGE_COLUMNS)
        summary = {
            "contract_version": ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "recent_row_count": int(len(recent)),
            "baseline_no_action_row_count": 0,
            "bridge_available_count": 0,
            "bridge_selected_count": 0,
            "breakout_candidate_count": 0,
            "recommended_next_action": "retain_ai2_observation",
        }
        return empty, summary

    selected_mask = baseline["entry_candidate_bridge_selected"].fillna(False).astype(bool)
    breakout_mask = baseline["breakout_candidate_action"].fillna("").astype(str).str.strip().isin({"BUY", "SELL"})
    summary = {
        "contract_version": ENTRY_CANDIDATE_BRIDGE_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(_as_mapping(runtime.get("semantic_live_config")).get("mode")),
        "recent_row_count": int(len(recent)),
        "baseline_no_action_row_count": int(len(baseline)),
        "bridge_available_count": int(
            baseline["entry_candidate_bridge_available"].fillna(False).astype(bool).sum()
        ),
        "bridge_selected_count": int(selected_mask.sum()),
        "breakout_candidate_count": int(breakout_mask.sum()),
        "bridge_source_counts": _series_json_counts(baseline["entry_candidate_bridge_source"]),
        "breakout_reason_counts": _series_json_counts(baseline["breakout_candidate_reason"]),
        "recent_symbols": _stable_join(baseline["symbol"]),
        "recommended_next_action": (
            "implement_ai3_utility_gate_recast"
            if int(selected_mask.sum()) > 0
            else "increase_candidate_surface_coverage"
        ),
    }
    frame = pd.DataFrame(
        [
            {
                "observation_event_id": "baseline_no_action_bridge::latest",
                "generated_at": summary["generated_at"],
                "runtime_updated_at": summary.get("runtime_updated_at", ""),
                "rollout_mode": summary.get("rollout_mode", ""),
                "recent_row_count": summary["recent_row_count"],
                "baseline_no_action_row_count": summary["baseline_no_action_row_count"],
                "bridge_available_count": summary["bridge_available_count"],
                "bridge_selected_count": summary["bridge_selected_count"],
                "breakout_candidate_count": summary["breakout_candidate_count"],
                "bridge_source_counts": summary["bridge_source_counts"],
                "breakout_reason_counts": summary["breakout_reason_counts"],
                "recent_symbols": summary["recent_symbols"],
                "recommended_next_action": summary["recommended_next_action"],
            }
        ],
        columns=BASELINE_NO_ACTION_BRIDGE_COLUMNS,
    )
    return frame, summary


def load_baseline_no_action_bridge_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def render_baseline_no_action_bridge_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    rows = frame.copy() if frame is not None else pd.DataFrame()
    lines = [
        "# Baseline No-Action Candidate Bridge",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- rollout_mode: `{_to_text(summary.get('rollout_mode'), 'unknown')}`",
        f"- recent_row_count: `{int(_to_float(summary.get('recent_row_count'), 0.0))}`",
        f"- baseline_no_action_row_count: `{int(_to_float(summary.get('baseline_no_action_row_count'), 0.0))}`",
        f"- bridge_selected_count: `{int(_to_float(summary.get('bridge_selected_count'), 0.0))}`",
        f"- breakout_candidate_count: `{int(_to_float(summary.get('breakout_candidate_count'), 0.0))}`",
        f"- bridge_source_counts: `{_to_text(summary.get('bridge_source_counts'), '{}')}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
    ]
    if rows.empty:
        lines.extend(["", "_No baseline-no-action bridge rows found._"])
    return "\n".join(lines) + "\n"
