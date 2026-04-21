from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.improvement_detector_policy import (
    DETECTOR_CANDLE_WEIGHT,
    DETECTOR_DAILY_SURFACE_LIMITS,
    DETECTOR_MIN_REPEAT_SAMPLES,
    DETECTOR_SCENE_AWARE,
    DETECTOR_REVERSE_PATTERN,
    DETECTOR_TOTAL_DAILY_SURFACE_LIMIT,
    build_improvement_detector_policy_baseline,
    write_improvement_detector_policy_baseline_snapshot,
)
from backend.services.improvement_proposal_policy import build_improvement_proposal_envelope
from backend.services.improvement_readiness_surface import (
    default_improvement_readiness_surface_json_path,
)
from backend.services.improvement_status_policy import (
    PROPOSAL_STAGE_OBSERVE,
    READINESS_STATUS_PENDING_EVIDENCE,
    READINESS_STATUS_READY_FOR_REVIEW,
    proposal_stage_label_ko,
    readiness_status_label_ko,
)
from backend.services.improvement_detector_feedback_runtime import (
    DETECTOR_NARROWING_CAUTION,
    DETECTOR_NARROWING_KEEP,
    DETECTOR_NARROWING_PROMOTE,
    DETECTOR_NARROWING_SUPPRESS,
    build_detector_feedback_narrowing_index,
    build_detector_feedback_scope_key,
    detector_narrowing_label_ko,
    evaluate_detector_feedback_narrowing,
)
from backend.services.learning_registry_resolver import (
    LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    LEARNING_REGISTRY_BINDING_MODE_EXACT,
    LEARNING_REGISTRY_BINDING_MODE_FALLBACK,
    build_learning_registry_binding_fields,
    build_learning_registry_relation,
)
from backend.services.reason_label_map import (
    normalize_runtime_reason,
    normalize_runtime_reason_body,
    normalize_runtime_transition_hint,
)
from backend.services.path_checkpoint_scene_bias_preview import (
    default_checkpoint_trend_exhaustion_scene_bias_preview_path,
)
from backend.services.path_checkpoint_scene_disagreement_audit import (
    default_checkpoint_scene_disagreement_audit_path,
)
from backend.services.state25_weight_patch_review import (
    build_state25_weight_patch_review_candidate_v1,
    build_state25_weight_patch_review_candidate_from_context_bridge_v1,
)
from backend.services.state25_threshold_patch_review import (
    build_state25_threshold_patch_review_candidate_from_context_bridge_v1,
)
from backend.services.directional_continuation_learning_candidate import (
    build_directional_continuation_learning_candidates,
)
from backend.services.semantic_baseline_no_action_cluster_candidate import (
    SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
    build_semantic_baseline_no_action_cluster_candidates,
)
from backend.services.trade_feedback_runtime import (
    DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT,
    build_manual_trade_proposal_snapshot,
)


IMPROVEMENT_LOG_ONLY_DETECTOR_CONTRACT_VERSION = "improvement_log_only_detector_v1"
MANUAL_DETECT_COMMAND = "/detect"
DEFAULT_DETECT_RECENT_LIMIT = DEFAULT_MANUAL_PROPOSE_RECENT_LIMIT

RESULT_TYPE_CORRECT = "result_correct"
RESULT_TYPE_MISREAD = "result_misread"
RESULT_TYPE_TIMING = "result_timing"
RESULT_TYPE_UNRESOLVED = "result_unresolved"

EXPLANATION_TYPE_CLEAR = "explanation_clear"
EXPLANATION_TYPE_GAP = "explanation_gap"
EXPLANATION_TYPE_UNKNOWN = "explanation_unknown"

HINDSIGHT_STATUS_CONFIRMED_MISREAD = "confirmed_misread"
HINDSIGHT_STATUS_FALSE_ALARM = "false_alarm"
HINDSIGHT_STATUS_PARTIAL_MISREAD = "partial_misread"
HINDSIGHT_STATUS_UNRESOLVED = "unresolved"

GENERIC_REASON_TOKENS = {
    "manual",
    "h1",
    "rsi",
    "general",
    "default",
    "unknown",
    "mixed",
    "observe",
}

SPECIFIC_DIRECTION_REASON_TOKENS = {
    "upper",
    "lower",
    "reject",
    "rebound",
    "reclaim",
    "box",
    "range",
    "compression",
    "wick",
    "band",
    "breakout",
    "pullback",
    "continuation",
    "follow",
    "sweep",
    "probe",
    "edge",
    "anchor",
    "touch",
    "spread",
    "trend",
}

CONTEXT_CONFIDENCE_HIGH = 0.70
CONTEXT_CONFIDENCE_CAUTION = 0.40

DETECTOR_COOLDOWN_MINUTES = {
    DETECTOR_SCENE_AWARE: 45,
    DETECTOR_CANDLE_WEIGHT: 90,
    DETECTOR_REVERSE_PATTERN: 30,
}

_CONTEXT_TOKEN_GROUPS = {
    "breakout_context": {"breakout", "retest", "sweep", "probe"},
    "reclaim_context": {"reclaim", "rebound", "anchor"},
    "compression_context": {"compression", "squeeze"},
    "range_context": {"range", "box", "mixed", "edge"},
    "reversion_context": {"pullback", "continuation", "follow", "runner", "trend"},
}

_RUNTIME_CONTEXT_STATE_FIELDS = (
    "context_state_version",
    "context_state_built_at",
    "htf_context_version",
    "previous_box_context_version",
    "conflict_context_version",
    "share_context_version",
    "trend_15m_direction",
    "trend_15m_strength",
    "trend_15m_strength_score",
    "trend_1h_direction",
    "trend_1h_strength",
    "trend_1h_strength_score",
    "trend_4h_direction",
    "trend_4h_strength",
    "trend_4h_strength_score",
    "trend_1d_direction",
    "trend_1d_strength",
    "trend_1d_strength_score",
    "htf_alignment_state",
    "htf_alignment_detail",
    "htf_against_severity",
    "previous_box_high",
    "previous_box_low",
    "previous_box_mid",
    "previous_box_mode",
    "previous_box_confidence",
    "previous_box_is_consolidation",
    "previous_box_relation",
    "previous_box_break_state",
    "previous_box_lifecycle",
    "distance_from_previous_box_high_pct",
    "distance_from_previous_box_low_pct",
    "context_conflict_state",
    "context_conflict_flags",
    "context_conflict_intensity",
    "context_conflict_score",
    "context_conflict_label_ko",
    "late_chase_risk_state",
    "late_chase_reason",
    "late_chase_confidence",
    "late_chase_trigger_count",
    "cluster_share_global",
    "cluster_share_symbol",
    "cluster_share_symbol_band",
    "share_context_label_ko",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _summary_mapping(value: object) -> dict[str, Any]:
    payload = _mapping(value)
    nested_summary = _mapping(payload.get("summary"))
    return nested_summary if nested_summary else payload


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _load_json(path: str | Path | None) -> dict[str, Any]:
    file_path = Path(path or "")
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def default_runtime_status_json_path() -> Path:
    return _repo_root() / "data" / "runtime_status.json"


def default_runtime_status_detail_json_path() -> Path:
    return _repo_root() / "data" / "runtime_status.detail.json"


def default_scene_disagreement_json_path() -> Path:
    return default_checkpoint_scene_disagreement_audit_path()


def default_scene_bias_preview_json_path() -> Path:
    return default_checkpoint_trend_exhaustion_scene_bias_preview_path()


def default_improvement_log_only_detector_paths() -> tuple[Path, Path]:
    directory = _repo_root() / "data" / "analysis" / "shadow_auto"
    return (
        directory / "improvement_log_only_detector_latest.json",
        directory / "improvement_log_only_detector_latest.md",
    )


def _latest_signal_rows(
    runtime_status_payload: Mapping[str, Any],
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    latest_signal_payload = _mapping(runtime_status_detail_payload).get("latest_signal_by_symbol")
    if not isinstance(latest_signal_payload, Mapping) or not latest_signal_payload:
        latest_signal_payload = _mapping(runtime_status_payload).get("latest_signal_by_symbol")
    rows: list[dict[str, Any]] = []
    for raw_symbol, raw_row in dict(latest_signal_payload or {}).items():
        row = _mapping(raw_row)
        if not row:
            continue
        row["symbol"] = _text(row.get("symbol")).upper() or _text(raw_symbol).upper()
        rows.append(row)
    return rows


def _position_energy_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = _mapping(row)
    energy_surface = _mapping(row_map.get("position_energy_surface_v1"))
    energy = _mapping(energy_surface.get("energy"))
    if energy:
        return energy
    return {
        "lower_position_force": row_map.get("lower_position_force"),
        "upper_position_force": row_map.get("upper_position_force"),
        "middle_neutrality": row_map.get("middle_neutrality"),
    }


def _position_metadata_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = _mapping(row)
    snapshot = _mapping(row_map.get("position_snapshot_v2"))
    snapshot_energy = _mapping(snapshot.get("energy"))
    return _mapping(snapshot_energy.get("metadata"))


def _position_force_values(row: Mapping[str, Any]) -> tuple[float, float, float]:
    energy = _position_energy_payload(row)
    return (
        _to_float(energy.get("lower_position_force")),
        _to_float(energy.get("upper_position_force")),
        _to_float(energy.get("middle_neutrality")),
    )


def _position_dominance(row: Mapping[str, Any]) -> str:
    metadata = _position_metadata_payload(row)
    dominance = _text(metadata.get("position_dominance")).upper()
    if dominance:
        return dominance
    lower_force, upper_force, middle_force = _position_force_values(row)
    if upper_force > max(lower_force, middle_force):
        return "UPPER"
    if lower_force > max(upper_force, middle_force):
        return "LOWER"
    if middle_force > max(upper_force, lower_force):
        return "MIDDLE"
    return "MIXED"


def _position_dominance_label_ko(row: Mapping[str, Any]) -> str:
    return {
        "UPPER": "상단 우세",
        "LOWER": "하단 우세",
        "MIDDLE": "중립 우세",
        "MIXED": "혼합",
        "UNRESOLVED": "미확정",
    }.get(_position_dominance(row), "미확정")


def _format_force_surface_ko(row: Mapping[str, Any]) -> str:
    lower_force, upper_force, middle_force = _position_force_values(row)
    return (
        f"{_position_dominance_label_ko(row)} "
        f"(하단 {lower_force:.2f} / 상단 {upper_force:.2f} / 중립 {middle_force:.2f})"
    )


_BOX_STATE_RELATIVE_MAP = {
    "BELOW": 0.05,
    "LOWER": 0.18,
    "LOWER_EDGE": 0.25,
    "MIDDLE": 0.50,
    "MID": 0.50,
    "UPPER_EDGE": 0.75,
    "UPPER": 0.82,
    "ABOVE": 0.95,
}


def _meaningful_force_context(row: Mapping[str, Any]) -> bool:
    lower_force, upper_force, middle_force = _position_force_values(row)
    return max(lower_force, upper_force, middle_force) >= 0.15


def _runtime_signal_index(
    runtime_status_payload: Mapping[str, Any],
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in _latest_signal_rows(runtime_status_payload, runtime_status_detail_payload):
        symbol = _text(row.get("symbol")).upper()
        if symbol:
            index[symbol] = row
    return index


def _issue_sort_key(row: Mapping[str, Any]) -> tuple[int, int, int, float, float, str]:
    severity = _to_int(_mapping(row).get("severity"), 9)
    score = _to_int(_mapping(row).get("repeat_count"), 0)
    semantic_rank = 0 if _text(_mapping(row).get("semantic_cluster_key")) else 1
    priority_score = _to_float(_mapping(row).get("priority_score"), 0.0)
    misread_confidence = _to_float(_mapping(row).get("misread_confidence"), 0.0)
    detector_key = _text(_mapping(row).get("detector_key"))
    return (semantic_rank, severity, -score, -priority_score, -misread_confidence, detector_key)


def _feedback_key_for_row(row: Mapping[str, Any]) -> str:
    row_map = _mapping(row)
    digest = hashlib.sha1(
        "|".join(
            [
                _text(row_map.get("detector_key")),
                _text(row_map.get("symbol")),
                _text(row_map.get("summary_ko")),
                _text(row_map.get("why_now_ko")),
            ]
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"detfb_{digest}"


def _attach_feedback_scope_key(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(row)
    row_map["feedback_scope_key"] = _text(row_map.get("feedback_scope_key")) or build_detector_feedback_scope_key(
        detector_key=row_map.get("detector_key"),
        symbol=row_map.get("symbol"),
        summary_ko=row_map.get("summary_ko"),
    )
    return row_map


def _apply_feedback_narrowing(
    rows: list[dict[str, Any]],
    feedback_history: list[Mapping[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    index = build_detector_feedback_narrowing_index(feedback_history)
    surfaced: list[dict[str, Any]] = []
    narrowed_out: list[dict[str, Any]] = []
    summary = {
        "promoted": 0,
        "kept": 0,
        "caution": 0,
        "suppressed": 0,
        "neutral": 0,
    }
    for raw_row in rows:
        row = _attach_feedback_scope_key(raw_row)
        scope_key = _text(row.get("feedback_scope_key"))
        feedback_profile = _mapping(index.get(scope_key))
        decision = evaluate_detector_feedback_narrowing(feedback_profile)
        row["feedback_profile"] = feedback_profile
        row["narrowing_decision"] = decision
        row["narrowing_label_ko"] = detector_narrowing_label_ko(decision)
        base_severity = _to_int(row.get("severity"), 9)
        row["base_severity"] = base_severity
        if decision == DETECTOR_NARROWING_PROMOTE:
            row["severity"] = max(1, base_severity - 1)
            summary["promoted"] += 1
            surfaced.append(row)
            continue
        if decision == DETECTOR_NARROWING_KEEP:
            summary["kept"] += 1
            surfaced.append(row)
            continue
        if decision == DETECTOR_NARROWING_CAUTION:
            row["severity"] = base_severity + 1
            summary["caution"] += 1
            surfaced.append(row)
            continue
        if decision == DETECTOR_NARROWING_SUPPRESS:
            summary["suppressed"] += 1
            narrowed_out.append(row)
            continue
        summary["neutral"] += 1
        surfaced.append(row)
    return surfaced, narrowed_out, summary


def _scene_disagreement_symbol_counts(
    scene_disagreement_payload: Mapping[str, Any] | None,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    summary = _summary_mapping(scene_disagreement_payload)
    counts: dict[str, int] = defaultdict(int)
    labels_by_symbol: dict[str, list[str]] = defaultdict(list)
    for raw_profile in list(summary.get("label_pull_profiles") or []):
        profile = _mapping(raw_profile)
        label = _text(profile.get("candidate_selected_label"))
        for raw_slice in list(profile.get("top_slices") or []):
            slice_map = _mapping(raw_slice)
            symbol = _text(slice_map.get("symbol")).upper()
            if not symbol:
                continue
            counts[symbol] += _to_int(slice_map.get("count"), 1)
            if label and label not in labels_by_symbol[symbol]:
                labels_by_symbol[symbol].append(label)
    return counts, labels_by_symbol


def _runtime_source_inputs(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = _mapping(row)
    barrier_state = _mapping(row_map.get("barrier_state_v1"))
    metadata = _mapping(barrier_state.get("metadata"))
    semantic_inputs = _mapping(metadata.get("semantic_barrier_inputs_v2"))
    return _mapping(semantic_inputs.get("runtime_source_inputs"))


def _runtime_secondary_source_inputs(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = _mapping(row)
    barrier_state = _mapping(row_map.get("barrier_state_v1"))
    metadata = _mapping(barrier_state.get("metadata"))
    semantic_inputs = _mapping(metadata.get("semantic_barrier_inputs_v2"))
    return _mapping(semantic_inputs.get("secondary_source_inputs"))


def _runtime_forecast_summary_inputs(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = _mapping(row)
    forecast_bridge = _mapping(row_map.get("forecast_state25_runtime_bridge_v1"))
    return _summary_mapping(forecast_bridge.get("forecast_runtime_summary_v1"))


def _resolve_box_relative_context(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_map = _mapping(row)
    source_inputs = _runtime_source_inputs(row_map)
    secondary_inputs = _runtime_secondary_source_inputs(row_map)

    relative_position = None
    source_mode = "unknown"
    for key in ("box_relative_position", "current_box_relative_position"):
        if row_map.get(key) not in (None, ""):
            relative_position = _to_float(row_map.get(key), 0.0)
            source_mode = "direct"
            break

    box_state = _text(row_map.get("box_state")).upper() or _text(source_inputs.get("source_position_in_session_box")).upper()
    if relative_position is None and box_state in _BOX_STATE_RELATIVE_MAP:
        relative_position = _BOX_STATE_RELATIVE_MAP[box_state]
        source_mode = "proxy"

    if relative_position is None:
        return {
            "available": False,
            "box_state": box_state or "UNKNOWN",
            "box_zone": "UNKNOWN",
            "box_relative_position": None,
            "range_too_narrow": False,
            "source_mode": source_mode,
            "recent_range_mean": _to_float(secondary_inputs.get("source_recent_range_mean"), 0.0),
        }

    relative_position = max(0.0, min(1.0, float(relative_position)))
    if relative_position <= 0.25:
        zone = "LOWER"
    elif relative_position >= 0.75:
        zone = "UPPER"
    else:
        zone = "MIDDLE"

    range_too_narrow = False
    box_range = _to_float(row_map.get("box_range"), 0.0)
    atr_value = _to_float(row_map.get("atr"), 0.0)
    if box_range > 0.0 and atr_value > 0.0 and box_range < (atr_value * 0.3):
        range_too_narrow = True

    return {
        "available": True,
        "box_state": box_state or zone,
        "box_zone": zone,
        "box_relative_position": relative_position,
        "range_too_narrow": range_too_narrow,
        "source_mode": source_mode,
        "recent_range_mean": _to_float(secondary_inputs.get("source_recent_range_mean"), 0.0),
    }


def _format_box_relative_line(row: Mapping[str, Any] | None) -> str:
    context = _resolve_box_relative_context(row)
    if not bool(context.get("available")):
        return ""
    zone_label = {
        "LOWER": "하단 영역",
        "MIDDLE": "중단 영역",
        "UPPER": "상단 영역",
    }.get(_text(context.get("box_zone")).upper(), "미확정")
    relative_value = context.get("box_relative_position")
    source_mode = _text(context.get("source_mode")) or "unknown"
    state_text = _text(context.get("box_state")).upper() or "-"
    suffix_parts = [f"state {state_text}", source_mode]
    if bool(context.get("range_too_narrow")):
        suffix_parts.append("좁은 박스 예외")
    recent_range_mean = _to_float(context.get("recent_range_mean"), 0.0)
    if recent_range_mean > 0.0:
        suffix_parts.append(f"최근 range {recent_range_mean:.2f}")
    suffix = " / ".join(suffix_parts)
    return f"{zone_label} ({float(relative_value):.2f} / {suffix})"


def _resolve_wick_body_context(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_map = _mapping(row)
    secondary_inputs = _runtime_secondary_source_inputs(row_map)
    forecast_summary = _runtime_forecast_summary_inputs(row_map)

    def _pick(*values: object) -> float:
        for value in values:
            if value in (None, ""):
                continue
            try:
                return float(value)
            except Exception:
                continue
        return 0.0

    upper = _pick(
        row_map.get("micro_upper_wick_ratio_20"),
        forecast_summary.get("micro_upper_wick_ratio_20"),
        secondary_inputs.get("source_micro_upper_wick_ratio_20"),
    )
    lower = _pick(
        row_map.get("micro_lower_wick_ratio_20"),
        forecast_summary.get("micro_lower_wick_ratio_20"),
        secondary_inputs.get("source_micro_lower_wick_ratio_20"),
    )
    doji = _pick(
        row_map.get("micro_doji_ratio_20"),
        forecast_summary.get("micro_doji_ratio_20"),
        secondary_inputs.get("source_micro_doji_ratio_20"),
    )
    body = _pick(
        row_map.get("micro_body_size_pct_20"),
        forecast_summary.get("micro_body_size_pct_20"),
        secondary_inputs.get("source_micro_body_size_pct_20"),
    )

    if max(upper, lower, doji, body) <= 0.0:
        return {
            "available": False,
            "upper_wick_ratio": 0.0,
            "lower_wick_ratio": 0.0,
            "doji_ratio": 0.0,
            "body_size_pct": 0.0,
            "candle_type": "UNKNOWN",
            "structure_hint": "",
        }

    is_doji = doji >= 0.30 or (body > 0.0 and body <= 0.05)
    candle_type = "DOJI" if is_doji else "NORMAL"
    structure_hint = ""
    if is_doji:
        if upper >= max(0.45, lower + 0.10):
            structure_hint = "상단 거부형 doji"
        elif lower >= max(0.45, upper + 0.10):
            structure_hint = "하단 방어형 doji"
        else:
            structure_hint = "우유부단 doji"
    else:
        if upper >= 0.25 and upper > lower:
            structure_hint = "윗꼬리 거부 우세"
        elif lower >= 0.25 and lower > upper:
            structure_hint = "아랫꼬리 방어 우세"
        elif max(upper, lower) >= 0.20:
            structure_hint = "꼬리 확장 관찰"

    return {
        "available": True,
        "upper_wick_ratio": upper,
        "lower_wick_ratio": lower,
        "doji_ratio": doji,
        "body_size_pct": body,
        "candle_type": candle_type,
        "structure_hint": structure_hint,
    }


def _format_wick_body_line(row: Mapping[str, Any] | None) -> str:
    context = _resolve_wick_body_context(row)
    if not bool(context.get("available")):
        return ""
    upper = float(context.get("upper_wick_ratio") or 0.0)
    lower = float(context.get("lower_wick_ratio") or 0.0)
    doji = float(context.get("doji_ratio") or 0.0)
    body = float(context.get("body_size_pct") or 0.0)
    hint = _text(context.get("structure_hint"))
    candle_type = _text(context.get("candle_type")).upper()
    if candle_type == "DOJI":
        base = f"doji {doji:.2f} / 윗꼬리 {upper:.2f} / 아랫꼬리 {lower:.2f}"
    else:
        base = f"윗꼬리 {upper:.2f} / 아랫꼬리 {lower:.2f} / 몸통 {body:.2f}"
    return f"{base}{f' / {hint}' if hint else ''}"


def _resolve_recent_3bar_direction_context(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_map = _mapping(row)
    secondary_inputs = _runtime_secondary_source_inputs(row_map)
    forecast_summary = _runtime_forecast_summary_inputs(row_map)
    direct_stats = _mapping(row_map.get("micro_direction_run_stats_v1"))
    forecast_stats = _mapping(forecast_summary.get("micro_direction_run_stats_v1"))

    def _pick_float(*values: object) -> float:
        for value in values:
            if value in (None, ""):
                continue
            try:
                return float(value)
            except Exception:
                continue
        return 0.0

    bull_ratio = _pick_float(
        row_map.get("micro_bull_ratio_20"),
        direct_stats.get("bull_ratio_20"),
        forecast_summary.get("micro_bull_ratio_20"),
        forecast_stats.get("bull_ratio_20"),
        secondary_inputs.get("source_micro_bull_ratio_20"),
    )
    bear_ratio = _pick_float(
        row_map.get("micro_bear_ratio_20"),
        direct_stats.get("bear_ratio_20"),
        forecast_summary.get("micro_bear_ratio_20"),
        forecast_stats.get("bear_ratio_20"),
        secondary_inputs.get("source_micro_bear_ratio_20"),
    )
    same_color_run_current = int(
        round(
            _pick_float(
                row_map.get("micro_same_color_run_current"),
                direct_stats.get("same_color_run_current"),
                forecast_summary.get("micro_same_color_run_current"),
                forecast_stats.get("same_color_run_current"),
                secondary_inputs.get("source_micro_same_color_run_current"),
            )
        )
    )
    same_color_run_max_20 = int(
        round(
            _pick_float(
                row_map.get("micro_same_color_run_max_20"),
                direct_stats.get("same_color_run_max_20"),
                forecast_summary.get("micro_same_color_run_max_20"),
                forecast_stats.get("same_color_run_max_20"),
                secondary_inputs.get("source_micro_same_color_run_max_20"),
            )
        )
    )

    if max(bull_ratio, bear_ratio, float(same_color_run_current), float(same_color_run_max_20)) <= 0.0:
        return {
            "available": False,
            "recent_3bar_direction": "UNKNOWN",
            "recent_3bar_direction_ko": "",
            "bull_ratio": 0.0,
            "bear_ratio": 0.0,
            "same_color_run_current": 0,
            "same_color_run_max_20": 0,
            "structure_hint": "",
        }

    direction = "MIXED"
    direction_ko = "혼조"
    if bull_ratio >= 0.70 and bull_ratio > (bear_ratio + 0.05):
        direction = "STRONG_UP"
        direction_ko = "강상승"
    elif bull_ratio >= 0.55 and bull_ratio > (bear_ratio + 0.03):
        direction = "WEAK_UP"
        direction_ko = "약상승"
    elif bear_ratio >= 0.70 and bear_ratio > (bull_ratio + 0.05):
        direction = "STRONG_DOWN"
        direction_ko = "강하락"
    elif bear_ratio >= 0.55 and bear_ratio > (bull_ratio + 0.03):
        direction = "WEAK_DOWN"
        direction_ko = "약하락"

    structure_hint = ""
    if direction in ("STRONG_UP", "WEAK_UP") and same_color_run_current >= 3:
        structure_hint = f"상승 연속 {same_color_run_current}"
    elif direction in ("STRONG_DOWN", "WEAK_DOWN") and same_color_run_current >= 3:
        structure_hint = f"하락 연속 {same_color_run_current}"
    elif direction == "MIXED" and same_color_run_current >= 3:
        structure_hint = f"연속봉 {same_color_run_current} 관찰"

    return {
        "available": True,
        "recent_3bar_direction": direction,
        "recent_3bar_direction_ko": direction_ko,
        "bull_ratio": bull_ratio,
        "bear_ratio": bear_ratio,
        "same_color_run_current": same_color_run_current,
        "same_color_run_max_20": same_color_run_max_20,
        "structure_hint": structure_hint,
    }


def _format_recent_3bar_direction_line(row: Mapping[str, Any] | None) -> str:
    context = _resolve_recent_3bar_direction_context(row)
    if not bool(context.get("available")):
        return ""
    direction_ko = _text(context.get("recent_3bar_direction_ko")) or "혼조"
    bull_ratio = float(context.get("bull_ratio") or 0.0)
    bear_ratio = float(context.get("bear_ratio") or 0.0)
    same_color_run_current = _to_int(context.get("same_color_run_current"), 0)
    same_color_run_max_20 = _to_int(context.get("same_color_run_max_20"), 0)
    structure_hint = _text(context.get("structure_hint"))
    base = (
        f"{direction_ko} (상승 {bull_ratio:.2f} / 하락 {bear_ratio:.2f} / "
        f"연속 {same_color_run_current}"
    )
    if same_color_run_max_20 > 0:
        base = f"{base} / 최대연속 {same_color_run_max_20}"
    base = f"{base})"
    return f"{base}{f' / {structure_hint}' if structure_hint else ''}"


def _trend_direction_arrow(direction: object) -> str:
    return {
        "UPTREND": "↑",
        "DOWNTREND": "↓",
        "MIXED": "→",
        "UNKNOWN": "?",
    }.get(_text(direction).upper(), "?")


def _htf_alignment_detail_label_ko(value: object) -> str:
    return {
        "ALL_ALIGNED_UP": "전체 상승 정렬",
        "MOSTLY_ALIGNED_UP": "대체로 상승 정렬",
        "AGAINST_HTF_UP": "현재만 하락, 상위는 상승",
        "ALL_ALIGNED_DOWN": "전체 하락 정렬",
        "MOSTLY_ALIGNED_DOWN": "대체로 하락 정렬",
        "AGAINST_HTF_DOWN": "현재만 상승, 상위는 하락",
        "MIXED": "혼조",
    }.get(_text(value).upper(), "")


def _format_htf_context_line(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    alignment_state = _text(row_map.get("htf_alignment_state")).upper()
    alignment_detail = _text(row_map.get("htf_alignment_detail")).upper()
    if not alignment_state and not alignment_detail:
        return ""
    detail_label = _htf_alignment_detail_label_ko(alignment_detail)
    if not detail_label:
        detail_label = {
            "WITH_HTF": "상위 추세와 정합",
            "AGAINST_HTF": "상위 추세 역행",
            "MIXED_HTF": "상위 추세 혼조",
        }.get(alignment_state, "")
    trend_parts = []
    for prefix in ("15m", "1h", "4h", "1d"):
        direction = _text(row_map.get(f"trend_{prefix}_direction")).upper()
        if not direction:
            continue
        trend_parts.append(f"{prefix.upper()}{_trend_direction_arrow(direction)}")
    suffix_parts = []
    if trend_parts:
        suffix_parts.append(" ".join(trend_parts))
    severity = _text(row_map.get("htf_against_severity")).upper()
    if severity:
        suffix_parts.append(severity)
    if suffix_parts:
        return f"{detail_label} ({' / '.join(suffix_parts)})"
    return detail_label


def _previous_box_break_state_label_ko(value: object) -> str:
    return {
        "BREAKOUT_HELD": "상단 돌파 유지",
        "BREAKOUT_FAILED": "상단 돌파 실패",
        "BREAKDOWN_HELD": "하단 이탈 유지",
        "RECLAIMED": "하단 이탈 후 되찾기",
        "REJECTED": "상단 거부",
        "INSIDE": "이전 박스 내부",
    }.get(_text(value).upper(), "")


def _previous_box_relation_label_ko(value: object) -> str:
    return {
        "ABOVE": "상단 위",
        "AT_HIGH": "상단 접촉",
        "INSIDE": "박스 내부",
        "AT_LOW": "하단 접촉",
        "BELOW": "하단 아래",
    }.get(_text(value).upper(), "")


def _previous_box_lifecycle_label_ko(value: object) -> str:
    return {
        "FORMING": "형성 중",
        "CONFIRMED": "확정",
        "BROKEN": "돌파/이탈",
        "RETESTED": "재테스트",
        "INVALIDATED": "무효화",
    }.get(_text(value).upper(), "")


def _format_previous_box_context_line(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    break_label = _previous_box_break_state_label_ko(row_map.get("previous_box_break_state"))
    relation_label = _previous_box_relation_label_ko(row_map.get("previous_box_relation"))
    lifecycle_label = _previous_box_lifecycle_label_ko(row_map.get("previous_box_lifecycle"))
    confidence = _text(row_map.get("previous_box_confidence")).upper()
    if not any((break_label, relation_label, lifecycle_label, confidence)):
        return ""
    suffix_parts = [part for part in (relation_label, lifecycle_label, confidence) if part]
    if break_label and suffix_parts:
        return f"{break_label} ({' / '.join(suffix_parts)})"
    return break_label or " / ".join(suffix_parts)


def _format_context_conflict_line(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    state = _text(row_map.get("context_conflict_state")).upper()
    if state in {"", "NONE"}:
        return ""
    label = _text(row_map.get("context_conflict_label_ko")) or state
    intensity = _text(row_map.get("context_conflict_intensity")).upper()
    score = _to_float(row_map.get("context_conflict_score"), 0.0)
    suffix_parts = []
    if intensity:
        suffix_parts.append(intensity)
    if score > 0.0:
        suffix_parts.append(f"score {score:.2f}")
    if suffix_parts:
        return f"{label} ({' / '.join(suffix_parts)})"
    return label


def _late_chase_reason_label_ko(value: object) -> str:
    return {
        "EXTENDED_ABOVE_PREV_BOX": "직전 박스 위 과확장",
        "AGAINST_PULLBACK_DEPTH": "눌림 깊이 부족",
        "HTF_ALREADY_EXTENDED": "상위 추세 과확장",
        "MULTI_BAR_RUN_AFTER_BREAK": "돌파 후 연속 추세 과열",
    }.get(_text(value).upper(), "")


def _format_late_chase_line(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    state = _text(row_map.get("late_chase_risk_state")).upper()
    if state in {"", "NONE"}:
        return ""
    reason_label = _late_chase_reason_label_ko(row_map.get("late_chase_reason"))
    confidence = _to_float(row_map.get("late_chase_confidence"), 0.0)
    trigger_count = _to_int(row_map.get("late_chase_trigger_count"), 0)
    suffix_parts = []
    if reason_label:
        suffix_parts.append(reason_label)
    if confidence > 0.0:
        suffix_parts.append(f"conf {confidence:.2f}")
    if trigger_count > 0:
        suffix_parts.append(f"trigger {trigger_count}")
    if suffix_parts:
        return f"{state} ({' / '.join(suffix_parts)})"
    return state


def _format_share_context_line(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    band = _text(row_map.get("cluster_share_symbol_band")).upper()
    if band not in {"DOMINANT", "COMMON"}:
        return ""
    label = _text(row_map.get("share_context_label_ko"))
    share_symbol = row_map.get("cluster_share_symbol")
    share_value = None if share_symbol in (None, "") else _to_float(share_symbol, 0.0)
    if label and share_value is not None:
        return f"{label} ({share_value * 100.0:.1f}%)"
    return label


def _build_runtime_context_bundle(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_map = _mapping(row)
    ordered_lines: list[str] = []
    ordered_segments: list[str] = []
    for prefix, formatter in (
        ("맥락 충돌", _format_context_conflict_line),
        ("HTF", _format_htf_context_line),
        ("직전 박스", _format_previous_box_context_line),
        ("늦은 추격", _format_late_chase_line),
        ("반복성", _format_share_context_line),
    ):
        text = formatter(row_map)
        if not text:
            continue
        ordered_lines.append(f"- {prefix}: {text}")
        ordered_segments.append(f"{prefix} {text}")
    return {
        "context_bundle_lines_ko": ordered_lines,
        "context_bundle_summary_ko": " | ".join(ordered_segments[:4]),
    }


def _structure_alignment_mode(row: Mapping[str, Any] | None) -> str:
    row_map = _mapping(row)
    profile = _reason_token_profile(
        row_map.get("consumer_check_reason"),
        row_map.get("entry_reason"),
        row_map.get("entry_reason_ko"),
        row_map.get("summary_ko"),
    )
    tokens = set(profile.get("tokens") or [])
    breakout_tokens = {"breakout", "retest", "sweep", "liquidity", "rangebreak"}
    reversion_tokens = {
        "range",
        "box",
        "reject",
        "rebound",
        "pullback",
        "continuation",
        "runner",
        "compression",
        "wick",
        "mixed",
        "follow",
        "trend",
    }
    if tokens & breakout_tokens:
        return "BREAKOUT"
    if "reclaim" in tokens and not (tokens & {"reject", "range", "box", "rebound"}):
        return "BREAKOUT"
    if tokens & reversion_tokens or "reclaim" in tokens:
        return "REVERSION"
    return "UNKNOWN"


def _box_position_mismatch_component_ko(row: Mapping[str, Any] | None, *, side: str, alignment_mode: str) -> str:
    context = _resolve_box_relative_context(row)
    if not bool(context.get("available")) or bool(context.get("range_too_narrow")):
        return ""
    zone = _text(context.get("box_zone")).upper()
    relative_value = _to_float(context.get("box_relative_position"), 0.0)
    if zone == "MIDDLE":
        return ""
    if alignment_mode == "BREAKOUT":
        if side == "BUY" and zone == "LOWER":
            return f"박스 하단 {relative_value:.2f} 위치에서 돌파 롱"
        if side == "SELL" and zone == "UPPER":
            return f"박스 상단 {relative_value:.2f} 위치에서 돌파 숏"
        return ""
    if alignment_mode == "REVERSION":
        if side == "BUY" and zone == "UPPER":
            return f"박스 상단 {relative_value:.2f} 위치에서 롱"
        if side == "SELL" and zone == "LOWER":
            return f"박스 하단 {relative_value:.2f} 위치에서 숏"
    return ""


def _wick_structure_mismatch_component_ko(row: Mapping[str, Any] | None, *, side: str) -> str:
    context = _resolve_wick_body_context(row)
    if not bool(context.get("available")):
        return ""
    upper = _to_float(context.get("upper_wick_ratio"), 0.0)
    lower = _to_float(context.get("lower_wick_ratio"), 0.0)
    candle_type = _text(context.get("candle_type")).upper()
    if side == "BUY":
        if candle_type == "DOJI" and upper >= max(0.45, lower + 0.10):
            return f"윗꼬리 {upper:.2f} / 상단 거부형 doji"
        if upper >= 0.25 and upper > lower:
            return f"윗꼬리 {upper:.2f} / 상단 거부 우세"
    if side == "SELL":
        if candle_type == "DOJI" and lower >= max(0.45, upper + 0.10):
            return f"아랫꼬리 {lower:.2f} / 하단 방어형 doji"
        if lower >= 0.25 and lower > upper:
            return f"아랫꼬리 {lower:.2f} / 하단 방어 우세"
    return ""


def _recent_3bar_mismatch_component_ko(row: Mapping[str, Any] | None, *, side: str) -> str:
    context = _resolve_recent_3bar_direction_context(row)
    if not bool(context.get("available")):
        return ""
    direction = _text(context.get("recent_3bar_direction")).upper()
    direction_ko = _text(context.get("recent_3bar_direction_ko")) or "혼조"
    if side == "BUY" and direction in {"STRONG_DOWN", "WEAK_DOWN"}:
        return f"최근 3봉 {direction_ko}"
    if side == "SELL" and direction in {"STRONG_UP", "WEAK_UP"}:
        return f"최근 3봉 {direction_ko}"
    return ""


def _resolve_composite_structure_mismatch(row: Mapping[str, Any] | None) -> dict[str, Any]:
    row_map = _mapping(row)
    side = _text(row_map.get("consumer_check_side")).upper()
    alignment_mode = _structure_alignment_mode(row_map)
    components = [
        component
        for component in (
            _box_position_mismatch_component_ko(row_map, side=side, alignment_mode=alignment_mode),
            _wick_structure_mismatch_component_ko(row_map, side=side),
            _recent_3bar_mismatch_component_ko(row_map, side=side),
        )
        if component
    ]
    component_count = len(components)
    return {
        "available": bool(side),
        "alignment_mode": alignment_mode,
        "components_ko": components,
        "component_count": component_count,
        "is_composite": component_count >= 2,
        "summary_ko": " + ".join(components[:3]),
    }


def _reason_tokens(*values: object) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _text(value).lower()
        if not text:
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", text)
        for token in normalized.split():
            if token:
                tokens.add(token)
    return tokens


def _reason_token_profile(*values: object) -> dict[str, Any]:
    tokens = _reason_tokens(*values)
    generic_tokens = sorted(token for token in tokens if token in GENERIC_REASON_TOKENS)
    specific_tokens = sorted(token for token in tokens if token in SPECIFIC_DIRECTION_REASON_TOKENS)
    return {
        "tokens": sorted(tokens),
        "generic_tokens": generic_tokens,
        "specific_tokens": specific_tokens,
        "generic_only": bool(generic_tokens) and not bool(specific_tokens),
    }


def _surfaceable_reason_body(raw_reason: object) -> str:
    if _reason_token_profile(raw_reason).get("generic_only"):
        return ""
    return normalize_runtime_reason_body(raw_reason)


def _context_confidence_label_ko(value: object) -> str:
    confidence = _to_float(value, 0.0)
    if confidence >= CONTEXT_CONFIDENCE_HIGH:
        return "높음"
    if confidence >= CONTEXT_CONFIDENCE_CAUTION:
        return "주의"
    return "낮음"


def _first_line_with(lines: list[str], marker: str) -> str:
    for line in lines:
        text = _text(line)
        if marker in text:
            return text
    return ""


def _build_explainability_snapshot(
    row: Mapping[str, Any],
    *,
    context_flag: str,
    context_confidence: float,
) -> dict[str, Any]:
    row_map = _mapping(row)
    evidence_lines = [str(line) for line in list(row_map.get("evidence_lines_ko") or [])]
    transition_lines = [str(line) for line in list(row_map.get("transition_lines_ko") or [])]
    return {
        "why_now": _text(row_map.get("why_now_ko")),
        "force": _first_line_with(evidence_lines, "위/아래 힘"),
        "alignment": _first_line_with(evidence_lines, "구조 "),
        "context": context_flag,
        "context_confidence": round(max(0.0, min(1.0, context_confidence)), 2),
        "box": _first_line_with(evidence_lines, "박스 위치:"),
        "candle": _first_line_with(evidence_lines, "캔들 구조:"),
        "recent_3bar": _first_line_with(evidence_lines, "최근 3봉 흐름:"),
        "reason": _first_line_with(evidence_lines, "현재 체크 이유:"),
        "transition_hint": _first_line_with(transition_lines, "next_action_hint:"),
    }


def _context_token_scores(row: Mapping[str, Any]) -> tuple[dict[str, int], dict[str, Any]]:
    row_map = _mapping(row)
    profile = _reason_token_profile(
        row_map.get("summary_ko"),
        row_map.get("why_now_ko"),
        row_map.get("entry_reason"),
        row_map.get("entry_reason_ko"),
        *list(row_map.get("evidence_lines_ko") or []),
        *list(row_map.get("transition_lines_ko") or []),
    )
    tokens = set(profile.get("tokens") or [])
    scores = {
        context_flag: sum(1 for token in tokens if token in group_tokens)
        for context_flag, group_tokens in _CONTEXT_TOKEN_GROUPS.items()
    }
    return scores, profile


def _infer_context_flag_with_confidence(row: Mapping[str, Any]) -> tuple[str, float]:
    scores, profile = _context_token_scores(row)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_context, top_score = ranked[0] if ranked else ("unknown_context", 0)
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    evidence_lines = [str(line) for line in list(_mapping(row).get("evidence_lines_ko") or [])]
    structural_count = sum(
        1
        for marker in ("위/아래 힘", "박스 위치:", "캔들 구조:", "최근 3봉 흐름:")
        if any(marker in _text(line) for line in evidence_lines)
    )

    if top_score <= 0:
        confidence = min(0.39, 0.10 + (0.05 * structural_count))
        return "unknown_context", round(confidence, 2)

    confidence = 0.30 + (0.12 * min(top_score, 3)) + (0.05 * min(structural_count, 4))
    if second_score > 0:
        confidence -= 0.15 if second_score >= top_score else 0.05
    if bool(profile.get("generic_only")):
        confidence = min(confidence, 0.35)
    confidence = max(0.0, min(1.0, confidence))
    if confidence < CONTEXT_CONFIDENCE_CAUTION:
        return "unknown_context", round(confidence, 2)
    return top_context, round(confidence, 2)


def _calculate_misread_confidence(
    row: Mapping[str, Any],
    *,
    context_flag: str,
    context_confidence: float,
    explainability_snapshot: Mapping[str, Any],
) -> float:
    structural_count = sum(
        1
        for key in ("force", "box", "candle", "recent_3bar")
        if _text(_mapping(explainability_snapshot).get(key))
    )
    result_bonus = {
        RESULT_TYPE_MISREAD: 0.28,
        RESULT_TYPE_TIMING: 0.20,
        RESULT_TYPE_UNRESOLVED: 0.10,
        RESULT_TYPE_CORRECT: 0.08,
    }.get(_text(_mapping(row).get("result_type")), 0.08)
    explanation_bonus = {
        EXPLANATION_TYPE_CLEAR: 0.16,
        EXPLANATION_TYPE_GAP: 0.08,
        EXPLANATION_TYPE_UNKNOWN: 0.04,
    }.get(_text(_mapping(row).get("explanation_type")), 0.04)
    severity_bonus = 0.06 if _to_int(_mapping(row).get("severity"), 9) <= 1 else 0.03
    confidence = (
        0.05
        + (0.04 * min(structural_count, 4))
        + min(max(context_confidence, 0.0), 1.0) * 0.20
        + result_bonus
        + explanation_bonus
        + severity_bonus
    )
    if context_flag == "unknown_context":
        confidence -= 0.08
    return round(max(0.0, min(1.0, confidence)), 2)


def _attach_detector_operational_hints(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    for raw_row in rows:
        row = _attach_feedback_scope_key(raw_row)
        context_flag, context_confidence = _infer_context_flag_with_confidence(row)
        explainability_snapshot = _build_explainability_snapshot(
            row,
            context_flag=context_flag,
            context_confidence=context_confidence,
        )
        misread_confidence = _calculate_misread_confidence(
            row,
            context_flag=context_flag,
            context_confidence=context_confidence,
            explainability_snapshot=explainability_snapshot,
        )
        row["context_flag"] = context_flag
        row["context_confidence"] = context_confidence
        row["context_confidence_label_ko"] = _context_confidence_label_ko(context_confidence)
        row["misread_confidence"] = misread_confidence
        row["explainability_snapshot"] = explainability_snapshot
        attached.append(row)
    return attached


def _parse_iso_datetime(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _cooldown_minutes_for_row(row: Mapping[str, Any]) -> int:
    detector_key = _text(_mapping(row).get("detector_key"))
    return int(DETECTOR_COOLDOWN_MINUTES.get(detector_key, 45))


def _derive_structure_alignment_state(
    row: Mapping[str, Any] | None,
) -> tuple[str, str]:
    row_map = _mapping(row)
    side = _text(row_map.get("consumer_check_side")).upper()
    dominance = _text(row_map.get("position_dominance")).upper()
    alignment_mode = _text(row_map.get("structure_alignment_mode")).upper()
    if not alignment_mode:
        alignment_mode = _structure_alignment_mode(row_map)
    if side not in {"BUY", "SELL"} or dominance not in {"UPPER", "LOWER"}:
        return "NEUTRAL", "중립 ➖"

    if alignment_mode == "BREAKOUT":
        is_match = (side == "BUY" and dominance == "UPPER") or (
            side == "SELL" and dominance == "LOWER"
        )
    elif alignment_mode == "REVERSION":
        is_match = (side == "BUY" and dominance == "LOWER") or (
            side == "SELL" and dominance == "UPPER"
        )
    else:
        return "NEUTRAL", "중립 ➖"

    if is_match:
        return "MATCH", "정합 ✅"
    return "MISMATCH", "엇갈림 ⚠️"


def _attach_runtime_structure_context(
    row: Mapping[str, Any],
    runtime_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    row_map = dict(row)
    runtime_map = _mapping(runtime_row)
    if not runtime_map:
        return row_map

    consumer_check_side = _text(runtime_map.get("consumer_check_side")).upper()
    if consumer_check_side:
        row_map["consumer_check_side"] = consumer_check_side
    consumer_check_reason = _text(runtime_map.get("consumer_check_reason"))
    if consumer_check_reason:
        row_map["consumer_check_reason"] = consumer_check_reason

    position_dominance = _position_dominance(runtime_map)
    if position_dominance:
        row_map["position_dominance"] = position_dominance

    combined_for_alignment = {**row_map, **runtime_map}
    structure_alignment_mode = _text(row_map.get("structure_alignment_mode")).upper()
    if not structure_alignment_mode:
        structure_alignment_mode = _structure_alignment_mode(combined_for_alignment)
    if structure_alignment_mode:
        row_map["structure_alignment_mode"] = structure_alignment_mode

    structure_alignment, structure_alignment_label_ko = _derive_structure_alignment_state(
        {**combined_for_alignment, **row_map}
    )
    row_map["structure_alignment"] = structure_alignment
    row_map["structure_alignment_label_ko"] = structure_alignment_label_ko

    box_context = _resolve_box_relative_context(runtime_map)
    if bool(box_context.get("available")):
        row_map["box_relative_position"] = _to_float(
            box_context.get("box_relative_position"),
            0.0,
        )
        row_map["box_zone"] = _text(box_context.get("box_zone")).upper()
        row_map["range_too_narrow"] = bool(box_context.get("range_too_narrow"))
        row_map["box_relative_position_source_mode"] = _text(
            box_context.get("source_mode")
        )

    wick_context = _resolve_wick_body_context(runtime_map)
    if bool(wick_context.get("available")):
        row_map["upper_wick_ratio"] = _to_float(
            wick_context.get("upper_wick_ratio"),
            0.0,
        )
        row_map["lower_wick_ratio"] = _to_float(
            wick_context.get("lower_wick_ratio"),
            0.0,
        )
        row_map["doji_ratio"] = _to_float(wick_context.get("doji_ratio"), 0.0)
        row_map["candle_type"] = _text(wick_context.get("candle_type")).upper()

    recent_context = _resolve_recent_3bar_direction_context(runtime_map)
    if bool(recent_context.get("available")):
        row_map["recent_3bar_direction"] = _text(
            recent_context.get("recent_3bar_direction")
        ).upper()
        row_map["recent_3bar_direction_ko"] = _text(
            recent_context.get("recent_3bar_direction_ko")
        )

    for field_name in _RUNTIME_CONTEXT_STATE_FIELDS:
        if field_name not in runtime_map:
            continue
        value = runtime_map.get(field_name)
        if value is None:
            continue
        row_map[field_name] = value

    return row_map


def _attach_runtime_context_bundle(
    row: Mapping[str, Any],
    runtime_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    row_map = _attach_runtime_structure_context(row, runtime_row)
    bundle = _build_runtime_context_bundle(row_map)
    bundle_lines = [str(line) for line in list(bundle.get("context_bundle_lines_ko") or []) if _text(line)]
    if bundle_lines:
        row_map["context_bundle_lines_ko"] = bundle_lines
        row_map["context_bundle_summary_ko"] = _text(bundle.get("context_bundle_summary_ko"))
        evidence_lines = [str(line) for line in list(row_map.get("evidence_lines_ko") or [])]
        row_map["evidence_lines_ko"] = bundle_lines + evidence_lines
        conflict_state = _text(row_map.get("context_conflict_state")).upper()
        if conflict_state not in {"", "NONE"}:
            conflict_label = _text(row_map.get("context_conflict_label_ko")) or row_map["context_bundle_summary_ko"]
            why_now_ko = _text(row_map.get("why_now_ko"))
            if conflict_label and conflict_label not in why_now_ko:
                row_map["why_now_ko"] = f"맥락상 {conflict_label}. {why_now_ko}".strip()
    else:
        row_map["context_bundle_lines_ko"] = []
        row_map["context_bundle_summary_ko"] = ""
    return row_map


def _normalized_registry_key_list(values: list[object] | tuple[object, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        key = _text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _detector_binding_evidence_registry_keys(
    row: Mapping[str, Any],
) -> list[str]:
    row_map = _mapping(row)
    evidence_keys: list[str] = []
    if _text(row_map.get("htf_alignment_state")).upper():
        evidence_keys.append("misread:htf_alignment_state")
    if _text(row_map.get("htf_alignment_detail")).upper():
        evidence_keys.append("misread:htf_alignment_detail")
    if _text(row_map.get("htf_against_severity")).upper():
        evidence_keys.append("misread:htf_against_severity")
    if _text(row_map.get("previous_box_break_state")).upper():
        evidence_keys.append("misread:previous_box_break_state")
    if _text(row_map.get("previous_box_relation")).upper():
        evidence_keys.append("misread:previous_box_relation")
    if _text(row_map.get("previous_box_lifecycle")).upper():
        evidence_keys.append("misread:previous_box_lifecycle")
    if _text(row_map.get("previous_box_confidence")).upper():
        evidence_keys.append("misread:previous_box_confidence")
    if _text(row_map.get("position_dominance")).upper():
        evidence_keys.append("misread:position_dominance")
    if _text(row_map.get("structure_alignment")).upper():
        evidence_keys.append("misread:structure_alignment")
    if _text(row_map.get("context_conflict_state")).upper() and _text(row_map.get("context_conflict_state")).upper() != "NONE":
        evidence_keys.append("misread:context_conflict_state")
    if _text(row_map.get("context_conflict_intensity")).upper():
        evidence_keys.append("misread:context_conflict_intensity")
    if _text(row_map.get("context_flag")):
        evidence_keys.append("misread:context_flag")
    if row_map.get("context_confidence") not in (None, ""):
        evidence_keys.append("misread:context_confidence")
    if _text(row_map.get("late_chase_risk_state")).upper() and _text(row_map.get("late_chase_risk_state")).upper() != "NONE":
        evidence_keys.append("misread:late_chase_risk_state")
    if _text(row_map.get("late_chase_reason")).upper():
        evidence_keys.append("misread:late_chase_reason")
    if row_map.get("box_relative_position") not in (None, ""):
        evidence_keys.append("misread:box_relative_position")
    if _text(row_map.get("box_zone")).upper():
        evidence_keys.append("misread:box_zone")
    if "range_too_narrow" in row_map:
        evidence_keys.append("misread:range_too_narrow")
    if row_map.get("upper_wick_ratio") not in (None, ""):
        evidence_keys.append("misread:upper_wick_ratio")
    if row_map.get("lower_wick_ratio") not in (None, ""):
        evidence_keys.append("misread:lower_wick_ratio")
    if row_map.get("doji_ratio") not in (None, ""):
        evidence_keys.append("misread:doji_ratio")
    if _text(row_map.get("recent_3bar_direction")).upper():
        evidence_keys.append("misread:recent_3bar_direction")
    if _text(row_map.get("result_type")):
        evidence_keys.append("misread:result_type")
    if _text(row_map.get("explanation_type")):
        evidence_keys.append("misread:explanation_type")
    if row_map.get("misread_confidence") not in (None, ""):
        evidence_keys.append("misread:misread_confidence")
    if _mapping(row_map.get("explainability_snapshot")):
        evidence_keys.append("misread:explainability_snapshot")
    if row_map.get("cooldown_window_min") not in (None, ""):
        evidence_keys.append("misread:cooldown_window_min")
    if bool(row_map.get("composite_structure_mismatch")):
        evidence_keys.append("misread:composite_structure_mismatch")
    evidence_keys.extend(
        [
            _text(key)
            for key in list(row_map.get("extra_evidence_registry_keys") or [])
            if _text(key)
        ]
    )
    return _normalized_registry_key_list(evidence_keys)


def _detector_binding_target_registry_keys(
    row: Mapping[str, Any],
) -> list[str]:
    preview = _mapping(_mapping(row).get("weight_patch_preview"))
    overrides = _mapping(preview.get("state25_teacher_weight_overrides"))
    keys = [f"state25_weight:{_text(key)}" for key in overrides.keys() if _text(key)]
    return _normalized_registry_key_list(keys)


def _detector_binding_mode(
    row: Mapping[str, Any],
    *,
    evidence_registry_keys: list[str],
) -> str:
    row_map = _mapping(row)
    detector_key = _text(row_map.get("detector_key"))
    structural_keys = {
        "misread:htf_alignment_state",
        "misread:htf_alignment_detail",
        "misread:htf_against_severity",
        "misread:previous_box_break_state",
        "misread:previous_box_relation",
        "misread:previous_box_lifecycle",
        "misread:previous_box_confidence",
        "misread:context_conflict_state",
        "misread:context_conflict_intensity",
        "misread:late_chase_risk_state",
        "misread:late_chase_reason",
        "misread:position_dominance",
        "misread:structure_alignment",
        "misread:box_relative_position",
        "misread:box_zone",
        "misread:range_too_narrow",
        "misread:upper_wick_ratio",
        "misread:lower_wick_ratio",
        "misread:doji_ratio",
        "misread:recent_3bar_direction",
        "misread:composite_structure_mismatch",
    }
    structural_evidence = [
        key for key in evidence_registry_keys if key in structural_keys
    ]
    if "misread:composite_structure_mismatch" in structural_evidence:
        return LEARNING_REGISTRY_BINDING_MODE_DERIVED
    if detector_key == DETECTOR_REVERSE_PATTERN and not structural_evidence:
        return LEARNING_REGISTRY_BINDING_MODE_FALLBACK
    if len(structural_evidence) >= 2:
        return LEARNING_REGISTRY_BINDING_MODE_DERIVED
    if structural_evidence:
        return LEARNING_REGISTRY_BINDING_MODE_EXACT
    return LEARNING_REGISTRY_BINDING_MODE_FALLBACK


def _detector_primary_registry_key(
    row: Mapping[str, Any],
    *,
    evidence_registry_keys: list[str],
) -> str:
    row_map = _mapping(row)
    override_key = _text(row_map.get("primary_registry_key_override"))
    if override_key:
        return override_key
    priority = [
        "misread:composite_structure_mismatch",
        "misread:context_conflict_state",
        "misread:late_chase_risk_state",
        "misread:htf_alignment_state",
        "misread:previous_box_break_state",
        "misread:structure_alignment",
        "misread:box_relative_position",
        "misread:upper_wick_ratio",
        "misread:recent_3bar_direction",
        "misread:position_dominance",
        "misread:result_type",
        "misread:misread_confidence",
        "misread:explainability_snapshot",
        "misread:context_flag",
        "misread:cooldown_window_min",
    ]
    for key in priority:
        if key in evidence_registry_keys:
            return key
    if evidence_registry_keys:
        return evidence_registry_keys[0]
    if _mapping(row_map.get("weight_patch_preview")):
        target_registry_keys = _detector_binding_target_registry_keys(row_map)
        if target_registry_keys:
            return target_registry_keys[0]
    return ""


def _build_semantic_baseline_no_action_cluster_detector_rows() -> list[dict[str, Any]]:
    candidate_rows = build_semantic_baseline_no_action_cluster_candidates()
    rows: list[dict[str, Any]] = []
    for raw_candidate in candidate_rows:
        candidate = _mapping(raw_candidate)
        if _text(candidate.get("cluster_pattern_code")) == "continuation_gap":
            continue
        cluster_count = _to_int(candidate.get("cluster_count"), 0)
        if cluster_count <= 0:
            continue
        severity = 1 if cluster_count >= 15 else 2
        rows.append(
            {
                "detector_key": DETECTOR_SCENE_AWARE,
                "detector_label_ko": "scene-aware detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": _text(candidate.get("symbol")).upper(),
                "repeat_count": cluster_count,
                "summary_ko": _text(candidate.get("summary_ko")),
                "why_now_ko": _text(candidate.get("why_now_ko")),
                "recommended_action_ko": _text(candidate.get("recommended_action_ko")),
                "evidence_lines_ko": list(candidate.get("evidence_lines_ko") or []),
                "transition_lines_ko": [
                    f"- cluster_key: {_text(candidate.get('candidate_key'))}",
                    f"- semantic_shadow_unavailable_share: {_to_float(candidate.get('semantic_shadow_unavailable_share')):.2f}",
                ],
                "result_type": _text(candidate.get("result_type"), RESULT_TYPE_UNRESOLVED),
                "explanation_type": _text(candidate.get("explanation_type"), EXPLANATION_TYPE_GAP),
                "misread_confidence": _to_float(candidate.get("misread_confidence"), 0.0),
                "priority_score": _to_float(candidate.get("priority_score"), 0.0),
                "context_flag": "semantic_observe_context",
                "context_confidence": 0.55,
                "semantic_cluster_key": _text(candidate.get("candidate_key")),
                "observe_reason": _text(candidate.get("observe_reason")),
                "blocked_by": _text(candidate.get("blocked_by")),
                "action_none_reason": _text(candidate.get("action_none_reason")),
                "primary_registry_key_override": _text(
                    candidate.get("primary_registry_key_override"),
                    SEMANTIC_BASELINE_NO_ACTION_PRIMARY_REGISTRY_KEY,
                ),
                "extra_evidence_registry_keys": list(candidate.get("extra_evidence_registry_keys") or []),
            }
        )
    return rows


def _build_directional_continuation_detector_rows() -> list[dict[str, Any]]:
    candidate_rows = build_directional_continuation_learning_candidates()
    rows: list[dict[str, Any]] = []
    for raw_candidate in candidate_rows:
        candidate = _mapping(raw_candidate)
        repeat_count = _to_int(candidate.get("repeat_count"), 0)
        if repeat_count <= 0:
            continue
        severity = 0 if repeat_count >= 5 else 1
        rows.append(
            {
                "detector_key": DETECTOR_SCENE_AWARE,
                "detector_label_ko": "scene-aware detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": _text(candidate.get("symbol")).upper(),
                "repeat_count": repeat_count,
                "summary_ko": _text(candidate.get("summary_ko")),
                "why_now_ko": _text(candidate.get("why_now_ko")),
                "recommended_action_ko": _text(candidate.get("recommended_action_ko")),
                "evidence_lines_ko": list(candidate.get("evidence_lines_ko") or []),
                "transition_lines_ko": [
                    f"- continuation_direction: {_text(candidate.get('continuation_direction'))}",
                    f"- candidate_key: {_text(candidate.get('candidate_key'))}",
                    f"- source_kind: {_text(candidate.get('source_kind'))}",
                ],
                "result_type": RESULT_TYPE_UNRESOLVED,
                "explanation_type": EXPLANATION_TYPE_GAP,
                "misread_confidence": _to_float(candidate.get("misread_confidence"), 0.0),
                "context_flag": "directional_continuation_gap",
                "context_confidence": 0.60,
                "registry_key": _text(candidate.get("registry_key")),
                "primary_registry_key_override": _text(candidate.get("registry_key")),
                "extra_evidence_registry_keys": list(
                    candidate.get("extra_evidence_registry_keys") or []
                ),
                "continuation_direction": _text(candidate.get("continuation_direction")),
                "continuation_pattern_code": _text(candidate.get("pattern_code")),
                "continuation_pattern_label_ko": _text(candidate.get("pattern_label_ko")),
                "primary_failure_label": _text(candidate.get("primary_failure_label")),
                "continuation_failure_label": _text(candidate.get("continuation_failure_label")),
                "context_failure_label": _text(candidate.get("context_failure_label")),
                "source_kind": _text(candidate.get("source_kind")),
                "source_kind_list": list(candidate.get("source_kind_list") or []),
                "source_labels_ko": list(candidate.get("source_labels_ko") or []),
                "dominant_observe_reason": _text(candidate.get("dominant_observe_reason")),
            }
        )
    return rows


def _attach_detector_registry_binding(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    row_map = dict(row)
    evidence_registry_keys = _detector_binding_evidence_registry_keys(row_map)
    target_registry_keys = _detector_binding_target_registry_keys(row_map)
    binding_mode = _detector_binding_mode(
        row_map,
        evidence_registry_keys=evidence_registry_keys,
    )
    primary_registry_key = _detector_primary_registry_key(
        row_map,
        evidence_registry_keys=evidence_registry_keys,
    )
    row_map.update(
        build_learning_registry_binding_fields(
            primary_registry_key,
            binding_mode=binding_mode,
        )
    )
    relation = build_learning_registry_relation(
        evidence_registry_keys=evidence_registry_keys,
        target_registry_keys=target_registry_keys,
        binding_mode=binding_mode,
    )
    row_map["evidence_registry_keys"] = list(relation.get("evidence_registry_keys") or [])
    row_map["target_registry_keys"] = list(relation.get("target_registry_keys") or [])
    row_map["evidence_bindings"] = list(relation.get("evidence_bindings") or [])
    row_map["target_bindings"] = list(relation.get("target_bindings") or [])
    row_map["registry_binding_ready"] = bool(relation.get("binding_ready"))
    return row_map


def _attach_detector_registry_bindings(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_attach_detector_registry_binding(row) for row in rows]


def _cooldown_should_bypass(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    previous_severity = _to_int(_mapping(previous).get("severity"), 9)
    current_severity = _to_int(_mapping(current).get("severity"), 9)
    previous_confidence = _to_float(_mapping(previous).get("misread_confidence"), 0.0)
    current_confidence = _to_float(_mapping(current).get("misread_confidence"), 0.0)
    previous_repeat = _to_int(_mapping(previous).get("repeat_count"), 0)
    current_repeat = _to_int(_mapping(current).get("repeat_count"), 0)
    previous_result = _text(_mapping(previous).get("result_type"))
    current_result = _text(_mapping(current).get("result_type"))
    return bool(
        current_severity < previous_severity
        or current_confidence >= (previous_confidence + 0.15)
        or current_repeat >= (previous_repeat + 2)
        or (
            current_result == RESULT_TYPE_MISREAD
            and previous_result not in {RESULT_TYPE_MISREAD, RESULT_TYPE_TIMING}
        )
    )


def _cooldown_state_entry(row: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    row_map = _mapping(row)
    return {
        "feedback_scope_key": _text(row_map.get("feedback_scope_key")),
        "detector_key": _text(row_map.get("detector_key")),
        "symbol": _text(row_map.get("symbol")).upper(),
        "summary_ko": _text(row_map.get("summary_ko")),
        "last_surfaced_at": generated_at,
        "misread_confidence": _to_float(row_map.get("misread_confidence"), 0.0),
        "severity": _to_int(row_map.get("severity"), 9),
        "repeat_count": _to_int(row_map.get("repeat_count"), 0),
        "result_type": _text(row_map.get("result_type")),
        "cooldown_window_min": _cooldown_minutes_for_row(row_map),
    }


def _prune_cooldown_state(
    rows_by_scope: Mapping[str, Any],
    *,
    now_dt: datetime,
) -> dict[str, Any]:
    pruned: dict[str, Any] = {}
    for scope_key, raw_entry in dict(rows_by_scope or {}).items():
        entry = _mapping(raw_entry)
        last_dt = _parse_iso_datetime(entry.get("last_surfaced_at"))
        if last_dt is None:
            continue
        age_minutes = max(0.0, (now_dt - last_dt).total_seconds() / 60.0)
        window = max(1, _to_int(entry.get("cooldown_window_min"), 45))
        if age_minutes > (window * 8):
            continue
        pruned[_text(scope_key)] = dict(entry)
    return pruned


def _apply_detector_cooldown(
    rows: list[dict[str, Any]],
    *,
    previous_snapshot_payload: Mapping[str, Any] | None,
    now_ts: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    now_dt = _parse_iso_datetime(now_ts) or datetime.now().astimezone()
    previous_state = _mapping(_mapping(previous_snapshot_payload).get("cooldown_state"))
    rows_by_scope = _prune_cooldown_state(
        _mapping(previous_state.get("rows_by_scope")),
        now_dt=now_dt,
    )
    surfaced: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    summary = {
        "kept": 0,
        "suppressed": 0,
        "bypassed": 0,
        "active_scope_count": 0,
    }

    for raw_row in rows:
        row = _attach_feedback_scope_key(raw_row)
        scope_key = _text(row.get("feedback_scope_key"))
        previous_entry = _mapping(rows_by_scope.get(scope_key))
        cooldown_window_min = _cooldown_minutes_for_row(row)
        row["cooldown_window_min"] = cooldown_window_min
        if previous_entry:
            previous_dt = _parse_iso_datetime(previous_entry.get("last_surfaced_at"))
            if previous_dt is not None:
                elapsed_min = max(0.0, (now_dt - previous_dt).total_seconds() / 60.0)
                if elapsed_min < cooldown_window_min:
                    if _cooldown_should_bypass(previous_entry, row):
                        row["cooldown_state"] = "BYPASS"
                        row["cooldown_reason_ko"] = "강한 증거 갱신으로 cooldown 우회"
                        summary["bypassed"] += 1
                        surfaced.append(row)
                        rows_by_scope[scope_key] = _cooldown_state_entry(row, now_ts)
                        continue
                    remaining = max(0, cooldown_window_min - int(elapsed_min))
                    row["cooldown_state"] = "SUPPRESSED"
                    row["cooldown_reason_ko"] = f"동일 scope {remaining}분 cooldown"
                    summary["suppressed"] += 1
                    suppressed.append(row)
                    continue
        row["cooldown_state"] = "SURFACED"
        row["cooldown_reason_ko"] = ""
        summary["kept"] += 1
        surfaced.append(row)
        rows_by_scope[scope_key] = _cooldown_state_entry(row, now_ts)

    summary["active_scope_count"] = len(rows_by_scope)
    return surfaced, suppressed, summary, {
        "generated_at": now_ts,
        "rows_by_scope": rows_by_scope,
    }


def _result_type_label_ko(value: object) -> str:
    return {
        RESULT_TYPE_CORRECT: "결과 정합",
        RESULT_TYPE_MISREAD: "결과 오판",
        RESULT_TYPE_TIMING: "타이밍 불일치",
        RESULT_TYPE_UNRESOLVED: "결과 미확정",
    }.get(_text(value), "결과 미확정")


def _explanation_type_label_ko(value: object) -> str:
    return {
        EXPLANATION_TYPE_CLEAR: "설명 명확",
        EXPLANATION_TYPE_GAP: "설명 부족",
        EXPLANATION_TYPE_UNKNOWN: "설명 미확인",
    }.get(_text(value), "설명 미확인")


def _hindsight_status_label_ko(value: object) -> str:
    return {
        HINDSIGHT_STATUS_CONFIRMED_MISREAD: "사후 확정 오판",
        HINDSIGHT_STATUS_FALSE_ALARM: "사후 과민 경보",
        HINDSIGHT_STATUS_PARTIAL_MISREAD: "사후 부분 오판",
        HINDSIGHT_STATUS_UNRESOLVED: "사후 미해결",
    }.get(_text(value), "사후 미해결")


def _classify_explanation_type(row: Mapping[str, Any]) -> str:
    row_map = _mapping(row)
    summary_ko = _text(row_map.get("summary_ko"))
    why_now_ko = _text(row_map.get("why_now_ko"))
    if not summary_ko and not why_now_ko:
        return EXPLANATION_TYPE_UNKNOWN

    evidence_lines = [str(line) for line in list(row_map.get("evidence_lines_ko") or [])]
    structural_markers = (
        "위/아래 힘:",
        "박스 위치:",
        "캔들 구조:",
        "최근 3봉 흐름:",
        "현재 체크 이유:",
        "avg_shock_score:",
        "action:",
    )
    structural_count = sum(
        1
        for line in evidence_lines
        if any(marker in line for marker in structural_markers)
    )
    detector_key = _text(row_map.get("detector_key"))
    if detector_key == DETECTOR_REVERSE_PATTERN:
        return EXPLANATION_TYPE_CLEAR if why_now_ko and structural_count >= 1 else EXPLANATION_TYPE_GAP
    return EXPLANATION_TYPE_CLEAR if why_now_ko and structural_count >= 2 else EXPLANATION_TYPE_GAP


def _extract_realized_pnl_sum(row: Mapping[str, Any]) -> float | None:
    for line in list(_mapping(row).get("transition_lines_ko") or []):
        text = _text(line)
        if "realized_pnl_sum:" not in text:
            continue
        try:
            raw_value = text.split("realized_pnl_sum:", 1)[1].split("USD", 1)[0].strip()
            return float(raw_value)
        except Exception:
            return None
    return None


def _classify_result_type(row: Mapping[str, Any]) -> str:
    row_map = _mapping(row)
    detector_key = _text(row_map.get("detector_key"))
    if detector_key == DETECTOR_SCENE_AWARE:
        return RESULT_TYPE_UNRESOLVED

    if detector_key == DETECTOR_CANDLE_WEIGHT:
        net_pnl = _to_float(row_map.get("net_pnl"), 0.0)
        win_rate = _to_float(row_map.get("win_rate"), 0.0)
        if net_pnl < 0.0 and win_rate < 0.45:
            return RESULT_TYPE_MISREAD
        if net_pnl < 0.0 and win_rate >= 0.45:
            return RESULT_TYPE_TIMING
        if net_pnl > 0.0 and win_rate >= 0.55:
            return RESULT_TYPE_CORRECT
        return RESULT_TYPE_UNRESOLVED

    if detector_key == DETECTOR_REVERSE_PATTERN:
        realized_pnl_sum = _extract_realized_pnl_sum(row_map)
        if realized_pnl_sum is None:
            return RESULT_TYPE_UNRESOLVED
        if realized_pnl_sum < 0.0:
            return RESULT_TYPE_MISREAD
        if realized_pnl_sum > 0.0:
            return RESULT_TYPE_TIMING
        return RESULT_TYPE_UNRESOLVED

    return RESULT_TYPE_UNRESOLVED


def _classify_hindsight_status(row: Mapping[str, Any]) -> str:
    result_type = _text(_mapping(row).get("result_type"))
    if result_type == RESULT_TYPE_MISREAD:
        return HINDSIGHT_STATUS_CONFIRMED_MISREAD
    if result_type == RESULT_TYPE_TIMING:
        return HINDSIGHT_STATUS_PARTIAL_MISREAD
    if result_type == RESULT_TYPE_CORRECT:
        return HINDSIGHT_STATUS_FALSE_ALARM
    return HINDSIGHT_STATUS_UNRESOLVED


def _attach_misread_axes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        result_type = _classify_result_type(row)
        explanation_type = _classify_explanation_type(row)
        row["result_type"] = result_type
        row["result_type_ko"] = _result_type_label_ko(result_type)
        row["explanation_type"] = explanation_type
        row["explanation_type_ko"] = _explanation_type_label_ko(explanation_type)
        row["misread_axes_ko"] = f"{row['result_type_ko']} / {row['explanation_type_ko']}"
        transition_lines = list(row.get("transition_lines_ko") or [])
        transition_lines.append(f"- 분류: {row['misread_axes_ko']}")
        row["transition_lines_ko"] = transition_lines
        attached.append(row)
    return attached


def _attach_hindsight_validator(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    summary = {
        HINDSIGHT_STATUS_CONFIRMED_MISREAD: 0,
        HINDSIGHT_STATUS_FALSE_ALARM: 0,
        HINDSIGHT_STATUS_PARTIAL_MISREAD: 0,
        HINDSIGHT_STATUS_UNRESOLVED: 0,
    }
    for raw_row in rows:
        row = dict(raw_row)
        hindsight_status = _classify_hindsight_status(row)
        summary[hindsight_status] = _to_int(summary.get(hindsight_status)) + 1
        row["hindsight_status"] = hindsight_status
        row["hindsight_status_ko"] = _hindsight_status_label_ko(hindsight_status)
        row["hindsight_validated"] = hindsight_status != HINDSIGHT_STATUS_UNRESOLVED
        transition_lines = list(row.get("transition_lines_ko") or [])
        transition_lines.append(f"- 사후 판정: {row['hindsight_status_ko']}")
        row["transition_lines_ko"] = transition_lines
        attached.append(row)
    return attached


def _build_direction_misread_context(
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    disagreement_count: int,
    candidate_label: str,
) -> tuple[str, list[str], list[str]]:
    runtime_map = _mapping(runtime_row)
    force_line = _format_force_surface_ko(runtime_map)
    why_now = (
        f"{symbol}에서 {candidate_label or 'scene'} 불일치가 {disagreement_count}건 누적됐고, "
        f"현재 위/아래 힘은 {force_line}로 읽힙니다."
    )
    current_reason = _surfaceable_reason_body(runtime_map.get("consumer_check_reason"))
    evidence_lines = [
        f"- 위/아래 힘: {force_line}",
        f"- 현재 체크 방향: {_text(runtime_map.get('consumer_check_side')).upper() or '-'}",
    ]
    if current_reason:
        evidence_lines.append(f"- 현재 체크 이유: {current_reason}")
    box_line = _format_box_relative_line(runtime_map)
    if box_line:
        evidence_lines.append(f"- 박스 위치: {box_line}")
    wick_line = _format_wick_body_line(runtime_map)
    if wick_line:
        evidence_lines.append(f"- 캔들 구조: {wick_line}")
    recent_3bar_line = _format_recent_3bar_direction_line(runtime_map)
    if recent_3bar_line:
        evidence_lines.append(f"- 최근 3봉 흐름: {recent_3bar_line}")
    transition_lines = []
    blocked_by = normalize_runtime_reason_body(runtime_map.get("blocked_by"))
    if blocked_by:
        transition_lines.append(f"- blocked_by: {blocked_by}")
    next_action_hint = _text(runtime_map.get("next_action_hint")).upper()
    if next_action_hint:
        transition_lines.append(f"- next_action_hint: {next_action_hint}")
    return why_now, evidence_lines, transition_lines


def _issue_has_candle_box_direction_signal(issue: Mapping[str, Any]) -> bool:
    issue_map = _mapping(issue)
    profile = _reason_token_profile(
        issue_map.get("entry_reason"),
        issue_map.get("entry_reason_ko"),
    )
    if bool(profile.get("generic_only")):
        return False
    return bool(profile.get("specific_tokens"))


def _build_scene_aware_detector_rows(
    runtime_status_payload: Mapping[str, Any],
    *,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    scene_disagreement_payload: Mapping[str, Any] | None = None,
    scene_bias_preview_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    runtime_signal_index = _runtime_signal_index(
        runtime_status_payload,
        runtime_status_detail_payload,
    )
    disagreement_counts, _ = _scene_disagreement_symbol_counts(scene_disagreement_payload)
    semantic_rollout = _mapping(_mapping(runtime_status_payload).get("semantic_rollout_state"))
    recent_rows = list(semantic_rollout.get("recent") or [])
    grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "reasons": []}
    )
    for raw_row in recent_rows:
        row = _mapping(raw_row)
        symbol = _text(row.get("symbol")).upper()
        domain = _text(row.get("domain")).lower()
        mode = _text(row.get("mode")).lower()
        trace_quality_state = _text(row.get("trace_quality_state")).lower()
        fallback_reason = _text(row.get("fallback_reason"))
        if domain != "entry" or mode != "log_only":
            continue
        if trace_quality_state not in {"unavailable", "missing", "degraded"}:
            continue
        group_key = (symbol, trace_quality_state, fallback_reason or "none")
        grouped[group_key]["count"] += 1
        reason_text = _text(row.get("reason"))
        if reason_text and reason_text not in grouped[group_key]["reasons"]:
            grouped[group_key]["reasons"].append(reason_text)

    rows: list[dict[str, Any]] = []
    min_repeat = int(DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_SCENE_AWARE])
    for (symbol, trace_state, fallback_reason), group in grouped.items():
        repeat_count = int(group["count"])
        if repeat_count < min_repeat:
            continue
        severity = 1 if repeat_count >= (min_repeat + 2) else 2
        why_now = (
            f"{symbol} entry semantic trace가 `{trace_state}` 상태로 {repeat_count}회 반복되었습니다."
        )
        if fallback_reason and fallback_reason != "none":
            why_now += f" fallback=`{fallback_reason}`가 같이 남았습니다."
        rows.append(
            {
                "detector_key": DETECTOR_SCENE_AWARE,
                "detector_label_ko": "scene-aware detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": symbol,
                "repeat_count": repeat_count,
                "summary_ko": f"{symbol} scene trace 누락 반복 감지",
                "why_now_ko": why_now,
                "recommended_action_ko": "scene trace 수집 누락 경로를 먼저 복기하고, 반복되면 scene proposal로 승격합니다.",
                "evidence_lines_ko": [
                    f"- trace_quality_state: {trace_state}",
                    f"- repeat_count: {repeat_count}",
                    f"- fallback_reason: {fallback_reason or 'none'}",
                ],
                "debug_reason_lines": list(group["reasons"])[:2],
            }
        )

    disagreement_summary = _summary_mapping(scene_disagreement_payload)
    label_pull_profiles = list(disagreement_summary.get("label_pull_profiles") or [])
    for raw_profile in label_pull_profiles:
        profile = _mapping(raw_profile)
        row_count = _to_int(profile.get("row_count"))
        if row_count < min_repeat:
            continue
        label = _text(profile.get("candidate_selected_label"))
        watch_state = _text(profile.get("watch_state"), "review")
        top_slice = _mapping((profile.get("top_slices") or [None])[0])
        top_symbol = _text(top_slice.get("symbol")).upper() or "MULTI"
        top_checkpoint_type = _text(top_slice.get("checkpoint_type"))
        top_surface_name = _text(top_slice.get("surface_name"))
        severity = 1 if watch_state == "overpull_watch" else 2
        rows.append(
            {
                "detector_key": DETECTOR_SCENE_AWARE,
                "detector_label_ko": "scene-aware detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": top_symbol,
                "repeat_count": row_count,
                "summary_ko": f"{label} 장면 불일치 반복 관찰",
                "why_now_ko": (
                    f"{label} 장면이 {row_count}건 반복 관찰됐고 watch_state={watch_state}입니다."
                ),
                "recommended_action_ko": "scene detector는 아직 log-only로 두고, 같은 장면이 반복되면 scene proposal 후보로만 올립니다.",
                "evidence_lines_ko": [
                    f"- runtime_unresolved_share: {_to_float(profile.get('runtime_unresolved_share')):.2f}",
                    f"- hindsight_resolved_share: {_to_float(profile.get('hindsight_resolved_share')):.2f}",
                    f"- expected_action_alignment_rate: {_to_float(profile.get('expected_action_alignment_rate')):.2f}",
                ],
                "transition_lines_ko": [
                    f"- top_slice: {top_symbol} / {top_surface_name or '-'} / {top_checkpoint_type or '-'}",
                    f"- recommended_next_action: {_text(disagreement_summary.get('recommended_next_action'), '-')}",
                ],
            }
        )

    scene_bias_summary = _summary_mapping(scene_bias_preview_payload)
    preview_changed_row_count = _to_int(scene_bias_summary.get("preview_changed_row_count"))
    if preview_changed_row_count > 0:
        top_changed_slice = _mapping((scene_bias_summary.get("top_changed_slices") or [None])[0])
        preview_symbol = _text(top_changed_slice.get("symbol")).upper() or "MULTI"
        preview_action = _text(top_changed_slice.get("preview_action_label"))
        preview_checkpoint_type = _text(top_changed_slice.get("checkpoint_type"))
        worsened_count = _to_int(scene_bias_summary.get("worsened_row_count"))
        severity = 1 if worsened_count > 0 else 2
        rows.append(
            {
                "detector_key": DETECTOR_SCENE_AWARE,
                "detector_label_ko": "scene-aware detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": preview_symbol,
                "repeat_count": preview_changed_row_count,
                "summary_ko": "trend exhaustion preview changed 관찰",
                "why_now_ko": (
                    f"preview action 변경이 {preview_changed_row_count}건 관찰됐고, improved={_to_int(scene_bias_summary.get('improved_row_count'))}, worsened={worsened_count}입니다."
                ),
                "recommended_action_ko": "scene bias preview는 아직 반영하지 않고, changed slice가 누적되는지 관찰합니다.",
                "evidence_lines_ko": [
                    f"- improved_row_count: {_to_int(scene_bias_summary.get('improved_row_count'))}",
                    f"- worsened_row_count: {worsened_count}",
                    f"- recommended_next_action: {_text(scene_bias_summary.get('recommended_next_action'), '-')}",
                ],
                "transition_lines_ko": [
                    f"- top_changed_slice: {preview_symbol} / {preview_checkpoint_type or '-'} / {preview_action or '-'}",
                ],
            }
        )
    rows.extend(_build_directional_continuation_detector_rows())
    rows.extend(_build_semantic_baseline_no_action_cluster_detector_rows())
    return sorted(rows, key=_issue_sort_key)


def _build_scene_aware_detector_rows_v2(
    runtime_status_payload: Mapping[str, Any],
    *,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    scene_disagreement_payload: Mapping[str, Any] | None = None,
    scene_bias_preview_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = _build_scene_aware_detector_rows(
        runtime_status_payload,
        scene_disagreement_payload=scene_disagreement_payload,
        scene_bias_preview_payload=scene_bias_preview_payload,
    )
    runtime_signal_index = _runtime_signal_index(
        runtime_status_payload,
        runtime_status_detail_payload,
    )
    disagreement_counts, _ = _scene_disagreement_symbol_counts(scene_disagreement_payload)
    updated_rows: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        symbol = _text(row.get("symbol")).upper()
        detector_key = _text(row.get("detector_key"))
        runtime_row = _mapping(runtime_signal_index.get(symbol))
        if detector_key != DETECTOR_SCENE_AWARE or not runtime_row or not _meaningful_force_context(runtime_row):
            updated_rows.append(row)
            continue
        if _text(row.get("semantic_cluster_key")):
            evidence_lines = list(row.get("evidence_lines_ko") or [])
            evidence_lines.insert(0, f"- 위치 힘: {_format_force_surface_ko(runtime_row)}")
            current_reason = _surfaceable_reason_body(runtime_row.get("consumer_check_reason"))
            if current_reason:
                evidence_lines.append(f"- 현재 체크 이유: {current_reason}")
            row["evidence_lines_ko"] = evidence_lines
            row = _attach_runtime_context_bundle(row, runtime_row)
            updated_rows.append(row)
            continue
        row = _attach_runtime_structure_context(row, runtime_row)
        summary_text = _text(row.get("summary_ko"))
        if "preview changed" in summary_text.lower():
            evidence_lines = list(row.get("evidence_lines_ko") or [])
            evidence_lines.insert(0, f"- 위/아래 힘: {_format_force_surface_ko(runtime_row)}")
            row["evidence_lines_ko"] = evidence_lines
            row = _attach_runtime_context_bundle(row, runtime_row)
            updated_rows.append(row)
            continue
        if "scene trace" in summary_text.lower():
            evidence_lines = list(row.get("evidence_lines_ko") or [])
            evidence_lines.append(f"- 위/아래 힘: {_format_force_surface_ko(runtime_row)}")
            row["evidence_lines_ko"] = evidence_lines
            row = _attach_runtime_context_bundle(row, runtime_row)
            updated_rows.append(row)
            continue

        disagreement_count = disagreement_counts.get(symbol, _to_int(row.get("repeat_count")))
        candidate_label = _text(summary_text).split(" ", 1)[0]
        why_now_ko, force_evidence_lines, force_transition_lines = _build_direction_misread_context(
            symbol,
            runtime_row,
            disagreement_count,
            candidate_label,
        )
        row["summary_ko"] = f"{symbol} 상하단 방향 오판 가능성 관찰"
        row["why_now_ko"] = why_now_ko
        row["evidence_lines_ko"] = force_evidence_lines + list(row.get("evidence_lines_ko") or [])
        row["transition_lines_ko"] = list(row.get("transition_lines_ko") or []) + force_transition_lines
        row = _attach_runtime_context_bundle(row, runtime_row)
        updated_rows.append(row)
    return sorted(updated_rows, key=_issue_sort_key)


def _build_weight_override_preview(issue: Mapping[str, Any]) -> dict[str, Any]:
    reason_text = _text(_mapping(issue).get("entry_reason")).lower()
    entry_reason_ko = _text(_mapping(issue).get("entry_reason_ko"))
    overrides: dict[str, float] = {}
    concern_parts: list[str] = []
    if any(token in reason_text for token in ("upper", "reject", "wick")):
        overrides["upper_wick_weight"] = 0.75
        overrides["reversal_risk_weight"] = 1.10
        concern_parts.append("윗꼬리/상단 거부 해석 비중")
    if any(token in reason_text for token in ("lower", "rebound", "reclaim")):
        overrides["lower_wick_weight"] = 0.75
        overrides["participation_weight"] = 1.05
        concern_parts.append("아랫꼬리/하단 반등 해석 비중")
    if "doji" in reason_text:
        overrides["doji_weight"] = 0.80
        concern_parts.append("도지 민감도")
    if any(token in reason_text for token in ("range", "mixed", "compression", "box")):
        overrides["compression_weight"] = 1.10
        concern_parts.append("박스/압축 해석 비중")
    if not overrides:
        overrides["candle_body_weight"] = 0.90
        concern_parts.append("캔들 몸통 비중")

    concern_summary = f"{entry_reason_ko} 패턴에서 {' / '.join(concern_parts)} 점검이 필요합니다."
    current_behavior = (
        f"{entry_reason_ko} 패턴에서 반복 손실 또는 낮은 MFE 포착이 관찰되어 현재 해석 비중이 과하거나 어긋난 것으로 보입니다."
    )
    proposed_behavior = (
        "해당 가중치를 bounded log-only patch로 먼저 낮추거나 조정하고, 실제 해석 변화는 관찰만 합니다."
    )
    evidence_summary = (
        f"{_text(issue.get('level_reason_ko'))} | 표본 {_to_int(issue.get('trade_count'))}건 | "
        f"순손익 {_to_float(issue.get('net_pnl')):+.2f} USD"
    )
    preview = build_state25_weight_patch_review_candidate_v1(
        concern_summary_ko=concern_summary,
        current_behavior_ko=current_behavior,
        proposed_behavior_ko=proposed_behavior,
        evidence_summary_ko=evidence_summary,
        state25_teacher_weight_overrides=overrides,
        state25_execution_bind_mode="log_only",
        trace_id=f"detect_weight::{_text(issue.get('entry_reason'))}",
    )
    return preview


def _build_state25_context_bridge_weight_review_detector_rows(
    runtime_status_payload: Mapping[str, Any],
    *,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    runtime_signal_index = _runtime_signal_index(
        runtime_status_payload,
        runtime_status_detail_payload,
    )
    rows: list[dict[str, Any]] = []
    for symbol, runtime_row in runtime_signal_index.items():
        runtime_map = _mapping(runtime_row)
        preview = build_state25_weight_patch_review_candidate_from_context_bridge_v1(
            runtime_map
        )
        if not preview:
            continue
        requested_count = _to_int(preview.get("bridge_weight_requested_count"), 0)
        effective_count = _to_int(preview.get("bridge_weight_effective_count"), 0)
        suppressed_count = _to_int(preview.get("bridge_weight_suppressed_count"), 0)
        if requested_count <= 0:
            continue
        severity = 1 if (
            effective_count > 0
            and _text(runtime_map.get("context_conflict_intensity")).upper() == "HIGH"
        ) else 2
        evidence_lines = [
            f"- context_bridge requested/effective/suppressed: {requested_count}/{effective_count}/{suppressed_count}",
        ]
        context_summary = _text(preview.get("bridge_context_summary_ko"))
        if context_summary:
            evidence_lines.append(f"- bridge_context: {context_summary}")
        bias_side = _text(preview.get("bridge_context_bias_side")).upper()
        bias_confidence = _to_float(preview.get("bridge_context_bias_confidence"), 0.0)
        if bias_side:
            evidence_lines.append(
                f"- bridge_bias: {bias_side} ({bias_confidence:.2f})"
            )
        transition_lines = [
            f"- bridge_stage: {_text(preview.get('bridge_stage')) or '-'} / {_text(preview.get('bridge_translator_state')) or '-'}",
        ]
        failure_modes = _normalized_registry_key_list(preview.get("bridge_failure_modes"))
        guard_modes = _normalized_registry_key_list(preview.get("bridge_guard_modes"))
        if failure_modes:
            transition_lines.append(f"- bridge_failure_modes: {', '.join(failure_modes)}")
        if guard_modes:
            transition_lines.append(f"- bridge_guard_modes: {', '.join(guard_modes)}")
        row = {
            "detector_key": DETECTOR_CANDLE_WEIGHT,
            "detector_label_ko": "candle/weight detector",
            "severity": severity,
            "proposal_stage": PROPOSAL_STAGE_OBSERVE,
            "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
            "symbol": _text(symbol).upper(),
            "dominant_symbol": _text(symbol).upper(),
            "entry_reason": "state25_context_bridge_weight_only_review",
            "entry_reason_ko": "state25 context bridge weight-only review",
            "trade_count": requested_count,
            "repeat_count": requested_count,
            "summary_ko": f"{_text(symbol).upper()} state25 context bridge weight review 후보",
            "why_now_ko": _text(preview.get("evidence_summary_ko")) or _text(preview.get("why_now_ko")),
            "recommended_action_ko": "state25 context bridge weight-only preview를 log-only review backlog로 먼저 검토합니다.",
            "evidence_lines_ko": evidence_lines,
            "transition_lines_ko": transition_lines,
            "weight_patch_preview": preview,
            "context_flag": "state25_context_bridge_weight_only_review",
            "context_confidence": max(0.5, bias_confidence),
            "primary_registry_key_override": _text(preview.get("registry_key")),
            "extra_evidence_registry_keys": list(preview.get("evidence_registry_keys") or []),
            "state25_candidate_context_bridge_v1": _mapping(
                preview.get("state25_candidate_context_bridge_v1")
            ),
        }
        row = _attach_runtime_context_bundle(row, runtime_map)
        rows.append(row)
    return rows


def _build_state25_context_bridge_threshold_review_detector_rows(
    runtime_status_payload: Mapping[str, Any],
    *,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    runtime_signal_index = _runtime_signal_index(
        runtime_status_payload,
        runtime_status_detail_payload,
    )
    rows: list[dict[str, Any]] = []
    for symbol, runtime_row in runtime_signal_index.items():
        runtime_map = _mapping(runtime_row)
        preview = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
            runtime_map
        )
        if not preview:
            continue
        requested_points = _to_float(preview.get("bridge_threshold_requested_points"), 0.0)
        effective_points = _to_float(preview.get("bridge_threshold_effective_points"), 0.0)
        if requested_points <= 0.0:
            continue
        changed_decision = bool(preview.get("bridge_threshold_changed_decision"))
        severity = 1 if (changed_decision and effective_points > 0.0) else 2
        suppressed_count = _to_int(preview.get("bridge_threshold_suppressed_count"), 0)
        evidence_lines = [
            (
                f"- context_bridge threshold requested/effective: "
                f"+{requested_points:.2f}pt / +{effective_points:.2f}pt"
            ),
        ]
        context_summary = _text(preview.get("bridge_context_summary_ko"))
        if context_summary:
            evidence_lines.append(f"- bridge_context: {context_summary}")
        if changed_decision:
            evidence_lines.append(
                "- decision_counterfactual: "
                f"{_text(preview.get('bridge_without_bridge_decision'), '-')} -> "
                f"{_text(preview.get('bridge_with_bridge_decision'), '-')}"
            )
        transition_lines = [
            f"- bridge_stage: {_text(preview.get('bridge_stage')) or '-'} / {_text(preview.get('bridge_translator_state')) or '-'}",
            f"- threshold_direction: {_text(preview.get('bridge_threshold_direction')) or '-'}",
        ]
        reason_keys = _normalized_registry_key_list(
            preview.get("bridge_threshold_reason_keys")
        )
        if reason_keys:
            transition_lines.append(f"- threshold_reason_keys: {', '.join(reason_keys)}")
        failure_modes = _normalized_registry_key_list(preview.get("bridge_failure_modes"))
        guard_modes = _normalized_registry_key_list(preview.get("bridge_guard_modes"))
        if failure_modes:
            transition_lines.append(f"- bridge_failure_modes: {', '.join(failure_modes)}")
        if guard_modes:
            transition_lines.append(f"- bridge_guard_modes: {', '.join(guard_modes)}")
        if suppressed_count > 0:
            transition_lines.append(f"- threshold_suppressed_count: {suppressed_count}")
        row = {
            "detector_key": DETECTOR_CANDLE_WEIGHT,
            "detector_label_ko": "candle/weight detector",
            "severity": severity,
            "proposal_stage": PROPOSAL_STAGE_OBSERVE,
            "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
            "symbol": _text(symbol).upper(),
            "dominant_symbol": _text(symbol).upper(),
            "entry_reason": "state25_context_bridge_threshold_log_only_review",
            "entry_reason_ko": "state25 context bridge threshold log-only review",
            "trade_count": 1,
            "repeat_count": 1,
            "summary_ko": f"{_text(symbol).upper()} state25 context bridge threshold review 후보",
            "why_now_ko": _text(preview.get("evidence_summary_ko")) or _text(preview.get("why_now_ko")),
            "recommended_action_ko": "state25 context bridge threshold harden preview를 log-only review backlog로 먼저 검토합니다.",
            "evidence_lines_ko": evidence_lines,
            "transition_lines_ko": transition_lines,
            "threshold_patch_preview": preview,
            "context_flag": "state25_context_bridge_threshold_log_only_review",
            "context_confidence": 0.85 if changed_decision else 0.65,
            "primary_registry_key_override": _text(preview.get("registry_key")),
            "extra_evidence_registry_keys": list(preview.get("evidence_registry_keys") or []),
            "state25_candidate_context_bridge_v1": _mapping(
                preview.get("state25_candidate_context_bridge_v1")
            ),
        }
        row = _attach_runtime_context_bundle(row, runtime_map)
        rows.append(row)
    return rows


def _build_candle_weight_detector_rows(
    closed_frame: pd.DataFrame | None,
    *,
    recent_trade_limit: int,
    timezone: Any,
    now_ts: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    proposal_payload = build_manual_trade_proposal_snapshot(
        closed_frame,
        recent_trade_limit=recent_trade_limit,
        timezone=timezone,
        now_ts=now_ts,
    )
    min_repeat = int(DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_CANDLE_WEIGHT])
    rows: list[dict[str, Any]] = []
    surfaced_problem_patterns = list(proposal_payload.get("surfaced_problem_patterns") or [])
    fallback_problem_patterns = [
        _mapping(raw_issue)
        for raw_issue in list(proposal_payload.get("problem_patterns") or [])
        if _to_int(_mapping(raw_issue).get("trade_count")) >= min_repeat
        and _to_float(_mapping(raw_issue).get("net_pnl")) < 0.0
    ]
    source_issues: list[dict[str, Any]] = []
    seen_reasons: set[str] = set()
    for raw_issue in [*surfaced_problem_patterns, *fallback_problem_patterns]:
        issue_map = _mapping(raw_issue)
        reason_key = _text(issue_map.get("entry_reason"))
        if not reason_key or reason_key in seen_reasons:
            continue
        if _reason_token_profile(
            issue_map.get("entry_reason"),
            issue_map.get("entry_reason_ko"),
        ).get("generic_only"):
            continue
        source_issues.append(issue_map)
        seen_reasons.add(reason_key)

    for issue_map in source_issues:
        trade_count = _to_int(issue_map.get("trade_count"))
        if trade_count < min_repeat:
            continue
        preview = _build_weight_override_preview(issue_map)
        severity = 1 if _to_int(issue_map.get("level"), 9) <= 1 else 2
        rows.append(
            {
                "detector_key": DETECTOR_CANDLE_WEIGHT,
                "detector_label_ko": "candle/weight detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": _text(issue_map.get("symbol")).upper(),
                "dominant_symbol": _text(issue_map.get("dominant_symbol")).upper(),
                "entry_reason": _text(issue_map.get("entry_reason")),
                "entry_reason_ko": _text(issue_map.get("entry_reason_ko")),
                "trade_count": trade_count,
                "win_rate": _to_float(issue_map.get("win_rate")),
                "net_pnl": _to_float(issue_map.get("net_pnl")),
                "repeat_count": trade_count,
                "summary_ko": f"{_text(issue_map.get('entry_reason_ko'))} 패턴 가중치 점검 제안",
                "why_now_ko": _text(issue_map.get("level_reason_ko")),
                "recommended_action_ko": "state25 weight patch preview를 log-only proposal로 검토합니다.",
                "evidence_lines_ko": [
                    f"- 표본: {trade_count}건",
                    f"- 승률: {_to_float(issue_map.get('win_rate')) * 100.0:.1f}%",
                    f"- 순손익: {_to_float(issue_map.get('net_pnl')):+.2f} USD",
                ],
                "weight_patch_preview": preview,
            }
        )
    return sorted(rows, key=_issue_sort_key), proposal_payload


def _build_candle_weight_detector_rows_v2(
    closed_frame: pd.DataFrame | None,
    *,
    runtime_status_payload: Mapping[str, Any],
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    recent_trade_limit: int,
    timezone: Any,
    now_ts: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, proposal_payload = _build_candle_weight_detector_rows(
        closed_frame,
        recent_trade_limit=recent_trade_limit,
        timezone=timezone,
        now_ts=now_ts,
    )
    runtime_signal_index = _runtime_signal_index(
        runtime_status_payload,
        runtime_status_detail_payload,
    )
    bridge_review_rows = _build_state25_context_bridge_weight_review_detector_rows(
        runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
    )
    bridge_review_rows.extend(
        _build_state25_context_bridge_threshold_review_detector_rows(
        runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        )
    )
    updated_rows: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        issue_symbol = _text(row.get("dominant_symbol")).upper() or _text(row.get("symbol")).upper()
        entry_reason = _text(row.get("entry_reason"))
        if not issue_symbol or not _issue_has_candle_box_direction_signal(row):
            updated_rows.append(row)
            continue
        row["symbol"] = issue_symbol
        row = _attach_runtime_structure_context(row, runtime_signal_index.get(issue_symbol))
        row["summary_ko"] = f"{issue_symbol} 캔들/박스 위치 대비 방향 해석 불일치 관찰"
        level_reason = _text(row.get("why_now_ko"))
        runtime_row = _mapping(runtime_signal_index.get(issue_symbol))
        why_now_parts = [level_reason] if level_reason else []
        evidence_lines = list(row.get("evidence_lines_ko") or [])
        if runtime_row and _meaningful_force_context(runtime_row):
            why_now_parts.append(f"현재 위/아래 힘은 {_format_force_surface_ko(runtime_row)}입니다.")
            evidence_lines.insert(
                0,
                f"- 위/아래 힘: {_format_force_surface_ko(runtime_row)}",
            )
            box_line = _format_box_relative_line(runtime_row)
            if box_line:
                why_now_parts.append(f"현재 박스 위치는 {box_line}입니다.")
                evidence_lines.insert(
                    1,
                    f"- 박스 위치: {box_line}",
                )
            wick_line = _format_wick_body_line(runtime_row)
            if wick_line:
                why_now_parts.append(f"현재 캔들 구조는 {wick_line}입니다.")
                evidence_lines.insert(
                    2,
                    f"- 캔들 구조: {wick_line}",
                )
            recent_3bar_line = _format_recent_3bar_direction_line(runtime_row)
            if recent_3bar_line:
                why_now_parts.append(f"현재 최근 3봉 흐름은 {recent_3bar_line}입니다.")
                evidence_lines.insert(
                    3,
                    f"- 최근 3봉 흐름: {recent_3bar_line}",
                )
            current_reason = _surfaceable_reason_body(runtime_row.get("consumer_check_reason"))
            if current_reason:
                evidence_lines.append(
                    f"- 현재 체크 이유: {current_reason}"
                )
        if runtime_row:
            composite_context = _resolve_composite_structure_mismatch(
                {
                    **runtime_row,
                    "entry_reason": entry_reason,
                    "entry_reason_ko": row.get("entry_reason_ko"),
                    "summary_ko": row.get("summary_ko"),
                }
            )
            row["structure_alignment_mode"] = _text(composite_context.get("alignment_mode"))
            row["structure_mismatch_components_ko"] = list(composite_context.get("components_ko") or [])
            row["structure_mismatch_component_count"] = _to_int(composite_context.get("component_count"), 0)
            row["composite_structure_mismatch"] = bool(composite_context.get("is_composite"))
            if bool(composite_context.get("is_composite")):
                composite_summary = _text(composite_context.get("summary_ko"))
                row["summary_ko"] = f"{issue_symbol} 구조 복합 불일치 관찰"
                why_now_parts.insert(0, f"구조 복합 불일치가 관찰됩니다. {composite_summary}.")
                evidence_lines.insert(0, f"- 구조 복합 불일치: {composite_summary}")
                row["severity"] = 1
        row["why_now_ko"] = " ".join(part for part in why_now_parts if part).strip()
        row["recommended_action_ko"] = (
            "state25 weight patch preview를 log-only로만 올리고, detector feedback으로 방향 오판 여부를 먼저 확인합니다."
        )
        row["evidence_lines_ko"] = evidence_lines
        row["transition_lines_ko"] = [
            f"- entry_reason: {entry_reason or '-'}",
        ]
        row = _attach_runtime_context_bundle(row, runtime_row)
        updated_rows.append(row)
    updated_rows.extend(bridge_review_rows)
    return sorted(updated_rows, key=_issue_sort_key), proposal_payload


def _build_reverse_pattern_detector_rows(
    runtime_status_payload: Mapping[str, Any],
    readiness_surface_payload: Mapping[str, Any],
    closed_frame: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    pending_reverse = _mapping(runtime_status_payload).get("pending_reverse_by_symbol") or {}
    rows: list[dict[str, Any]] = []
    min_repeat = int(DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_REVERSE_PATTERN])

    for raw_symbol, raw_payload in dict(pending_reverse or {}).items():
        payload = _mapping(raw_payload)
        symbol = _text(raw_symbol).upper()
        action = _text(payload.get("action")).upper()
        reason_count = _to_int(payload.get("reason_count"))
        if reason_count < min_repeat:
            continue
        reasons = [normalize_runtime_transition_hint(item) for item in list(payload.get("reasons") or []) if _text(item)]
        severity = 1 if _to_int(payload.get("age_sec")) >= 10 else 2
        rows.append(
            {
                "detector_key": DETECTOR_REVERSE_PATTERN,
                "detector_label_ko": "reverse pattern detector",
                "severity": severity,
                "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                "symbol": symbol,
                "repeat_count": reason_count,
                "summary_ko": f"{symbol} 반전 대기 패턴 관찰",
                "why_now_ko": (
                    f"{symbol} 반전 후보가 {action} 방향으로 대기 중이며, 이유 {reason_count}개가 누적되었습니다."
                ),
                "recommended_action_ko": "즉시 강제 반전이 아니라 blocked/pending 원인을 먼저 복기하고, 반복되면 reverse proposal로 승격합니다.",
                "evidence_lines_ko": [
                    f"- action: {action or '-'}",
                    f"- age_sec: {_to_int(payload.get('age_sec'))}",
                    f"- expires_in_sec: {_to_int(payload.get('expires_in_sec'))}",
                ],
                "transition_lines_ko": [f"- {reason}" for reason in reasons[:3]],
            }
        )

    if closed_frame is not None and not closed_frame.empty:
        reverse_candidates = closed_frame.copy()
        for column_name in ("symbol", "shock_reason", "shock_action"):
            if column_name not in reverse_candidates.columns:
                reverse_candidates[column_name] = ""
        for column_name in ("shock_score", "profit"):
            if column_name not in reverse_candidates.columns:
                reverse_candidates[column_name] = 0.0

        reverse_candidates["symbol"] = reverse_candidates["symbol"].fillna("").astype(str).str.upper()
        reverse_candidates["shock_reason"] = reverse_candidates["shock_reason"].fillna("").astype(str)
        reverse_candidates["shock_action"] = reverse_candidates["shock_action"].fillna("").astype(str)
        reverse_candidates["shock_score"] = pd.to_numeric(reverse_candidates["shock_score"], errors="coerce").fillna(0.0)
        reverse_candidates["profit"] = pd.to_numeric(reverse_candidates["profit"], errors="coerce").fillna(0.0)

        filtered = reverse_candidates.loc[
            (reverse_candidates["shock_score"] >= 15.0)
            & (
                reverse_candidates["shock_reason"].str.contains("opposite_score_spike|adverse_risk", case=False, na=False)
                | reverse_candidates["shock_action"].str.contains("downgrade_to_mid|force_exit_candidate|hold", case=False, na=False)
            )
        ].copy()

        if not filtered.empty:
            for symbol, symbol_frame in filtered.groupby("symbol", dropna=False):
                repeat_count = int(len(symbol_frame))
                if repeat_count < min_repeat:
                    continue
                dominant_reason = _text(symbol_frame["shock_reason"].mode().iloc[0] if not symbol_frame["shock_reason"].mode().empty else "")
                dominant_action = _text(symbol_frame["shock_action"].mode().iloc[0] if not symbol_frame["shock_action"].mode().empty else "")
                avg_shock_score = float(symbol_frame["shock_score"].mean())
                severity = 1 if avg_shock_score >= 30.0 or "force_exit_candidate" in dominant_action.lower() else 2
                rows.append(
                    {
                        "detector_key": DETECTOR_REVERSE_PATTERN,
                        "detector_label_ko": "reverse pattern detector",
                        "severity": severity,
                        "proposal_stage": PROPOSAL_STAGE_OBSERVE,
                        "readiness_status": READINESS_STATUS_READY_FOR_REVIEW,
                        "symbol": _text(symbol).upper(),
                        "repeat_count": repeat_count,
                        "summary_ko": f"{_text(symbol).upper()} missed reverse / shock 패턴 관찰",
                        "why_now_ko": (
                            f"{_text(symbol).upper()}에서 reverse missed로 읽을 수 있는 shock 패턴이 {repeat_count}건 반복됐습니다."
                        ),
                        "recommended_action_ko": "즉시 반영은 하지 않고, reverse-ready / reverse-blocked와 함께 missed reverse 패턴으로만 누적 관찰합니다.",
                        "evidence_lines_ko": [
                            f"- avg_shock_score: {avg_shock_score:.1f}",
                            f"- dominant_shock_reason: {dominant_reason or '-'}",
                            f"- dominant_shock_action: {dominant_action or '-'}",
                        ],
                        "transition_lines_ko": [
                            f"- realized_pnl_sum: {float(symbol_frame['profit'].sum()):+.2f} USD",
                        ],
                    }
                )
    return sorted(rows, key=_issue_sort_key)


def _cap_detector_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    sorted_rows = sorted(rows, key=_issue_sort_key)
    used_per_detector: dict[str, int] = defaultdict(int)
    accepted: list[dict[str, Any]] = []
    dropped = 0
    for row in sorted_rows:
        detector_key = _text(row.get("detector_key"))
        detector_limit = int(DETECTOR_DAILY_SURFACE_LIMITS.get(detector_key, 0))
        if len(accepted) >= DETECTOR_TOTAL_DAILY_SURFACE_LIMIT:
            dropped += 1
            continue
        if detector_limit > 0 and used_per_detector[detector_key] >= detector_limit:
            dropped += 1
            continue
        accepted.append(row)
        used_per_detector[detector_key] += 1
    return accepted, dropped


def _attach_feedback_refs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attached: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        row_map = _attach_feedback_scope_key(row)
        row_map["feedback_ref"] = f"D{index}"
        row_map["feedback_key"] = _feedback_key_for_row(row_map)
        attached.append(row_map)
    return attached


def _render_report_lines(payload: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    envelope = _mapping(payload.get("proposal_envelope"))
    lines.append(
        f"단계: {proposal_stage_label_ko(envelope.get('proposal_stage'))} / 준비: {readiness_status_label_ko(envelope.get('readiness_status'))}"
    )
    lines.append(f"요약: {_text(envelope.get('summary_ko'))}")
    lines.append("")
    for section_key, title in (
        ("scene_aware_detector", "scene-aware detector"),
        ("candle_weight_detector", "candle/weight detector"),
        ("reverse_pattern_detector", "reverse pattern detector"),
    ):
        section = _mapping(payload.get(section_key))
        section_rows = list(section.get("surfaced_rows") or [])
        lines.append(title)
        if not section_rows:
            lines.append("- surface된 관찰 없음")
            lines.append("")
            continue
        for index, row in enumerate(section_rows, start=1):
            row_map = _mapping(row)
            lines.append(
                f"{index}. {_text(row_map.get('summary_ko'))} | 단계 {proposal_stage_label_ko(row_map.get('proposal_stage'))} | 준비 {readiness_status_label_ko(row_map.get('readiness_status'))}"
            )
            lines.append(f"   - 이유: {_text(row_map.get('why_now_ko'))}")
            misread_axes = _text(row_map.get("misread_axes_ko"))
            if misread_axes:
                lines.append(f"   - 분류: {misread_axes}")
            for evidence in list(row_map.get("evidence_lines_ko") or [])[:3]:
                lines.append(f"   {evidence}")
            for transition in list(row_map.get("transition_lines_ko") or [])[:3]:
                lines.append(f"   {transition}")
            preview = _mapping(row_map.get("weight_patch_preview"))
            if preview:
                lines.append(f"   - preview: {_text(preview.get('proposal_summary_ko'))}")
        lines.append("")
    return [line for line in lines if line is not None]


def _render_report_lines_v2(payload: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    envelope = _mapping(payload.get("proposal_envelope"))
    lines.append(
        f"단계: {proposal_stage_label_ko(envelope.get('proposal_stage'))} / 준비: {readiness_status_label_ko(envelope.get('readiness_status'))}"
    )
    lines.append(f"요약: {_text(envelope.get('summary_ko'))}")
    lines.append("")
    for section_key, title in (
        ("scene_aware_detector", "scene-aware detector"),
        ("candle_weight_detector", "candle/weight detector"),
        ("reverse_pattern_detector", "reverse pattern detector"),
    ):
        section = _mapping(payload.get(section_key))
        section_rows = list(section.get("surfaced_rows") or [])
        lines.append(title)
        if not section_rows:
            lines.append("- surface된 관찰 없음")
            lines.append("")
            continue
        for index, row in enumerate(section_rows, start=1):
            row_map = _mapping(row)
            feedback_ref = _text(row_map.get("feedback_ref"), f"D{index}")
            narrowing_label = _text(row_map.get("narrowing_label_ko"))
            lines.append(
                f"{feedback_ref}. {_text(row_map.get('summary_ko'))} | 단계 {proposal_stage_label_ko(row_map.get('proposal_stage'))} | 준비:{readiness_status_label_ko(row_map.get('readiness_status'))}"
            )
            lines.append(f"   - 이유: {_text(row_map.get('why_now_ko'))}")
            misread_axes = _text(row_map.get("misread_axes_ko"))
            if misread_axes:
                lines.append(f"   - 분류: {misread_axes}")
            if narrowing_label:
                lines.append(f"   - feedback-aware: {narrowing_label}")
            for evidence in list(row_map.get("evidence_lines_ko") or [])[:3]:
                lines.append(f"   {evidence}")
            for transition in list(row_map.get("transition_lines_ko") or [])[:3]:
                lines.append(f"   {transition}")
            preview = _mapping(row_map.get("weight_patch_preview"))
            if preview:
                lines.append(f"   - preview: {_text(preview.get('proposal_summary_ko'))}")
        lines.append("")
    return [line for line in lines if line is not None]


def build_improvement_log_only_detector_snapshot(
    *,
    runtime_status_payload: Mapping[str, Any],
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    readiness_surface_payload: Mapping[str, Any],
    scene_disagreement_payload: Mapping[str, Any] | None = None,
    scene_bias_preview_payload: Mapping[str, Any] | None = None,
    closed_frame: pd.DataFrame | None,
    feedback_history: list[Mapping[str, Any]] | None = None,
    previous_snapshot_payload: Mapping[str, Any] | None = None,
    recent_trade_limit: int = DEFAULT_DETECT_RECENT_LIMIT,
    timezone: Any,
    now_ts: str = "",
) -> dict[str, Any]:
    generated_at = _text(now_ts, _now_iso())
    scene_rows_all = _build_scene_aware_detector_rows_v2(
        runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        scene_disagreement_payload=scene_disagreement_payload,
        scene_bias_preview_payload=scene_bias_preview_payload,
    )
    candle_rows_all, proposal_payload = _build_candle_weight_detector_rows_v2(
        closed_frame,
        runtime_status_payload=runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        recent_trade_limit=recent_trade_limit,
        timezone=timezone,
        now_ts=generated_at,
    )
    reverse_rows_all = _build_reverse_pattern_detector_rows(
        runtime_status_payload,
        readiness_surface_payload,
        closed_frame,
    )

    all_rows = _attach_misread_axes([*scene_rows_all, *candle_rows_all, *reverse_rows_all])
    all_rows = _attach_detector_operational_hints(all_rows)
    all_rows = _attach_hindsight_validator(all_rows)
    candidate_rows, narrowed_out_rows, narrowing_summary = _apply_feedback_narrowing(
        all_rows,
        feedback_history,
    )
    cooldown_candidate_rows, cooldown_suppressed_rows, cooldown_summary, cooldown_state = _apply_detector_cooldown(
        candidate_rows,
        previous_snapshot_payload=previous_snapshot_payload,
        now_ts=generated_at,
    )
    cooldown_candidate_rows = _attach_detector_registry_bindings(cooldown_candidate_rows)
    narrowed_out_rows = _attach_detector_registry_bindings(narrowed_out_rows)
    cooldown_suppressed_rows = _attach_detector_registry_bindings(cooldown_suppressed_rows)
    surfaced_rows, dropped_count = _cap_detector_rows(cooldown_candidate_rows)
    surfaced_rows = _attach_feedback_refs(surfaced_rows)
    narrowed_out_rows = _attach_feedback_refs(narrowed_out_rows)
    cooldown_suppressed_rows = _attach_feedback_refs(cooldown_suppressed_rows)
    scene_rows = [
        row for row in surfaced_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_SCENE_AWARE
    ]
    candle_rows = [
        row for row in surfaced_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_CANDLE_WEIGHT
    ]
    reverse_rows = [
        row for row in surfaced_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_REVERSE_PATTERN
    ]
    narrowed_scene_rows = [
        row for row in narrowed_out_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_SCENE_AWARE
    ]
    narrowed_candle_rows = [
        row for row in narrowed_out_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_CANDLE_WEIGHT
    ]
    narrowed_reverse_rows = [
        row for row in narrowed_out_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_REVERSE_PATTERN
    ]
    cooldown_scene_rows = [
        row for row in cooldown_suppressed_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_SCENE_AWARE
    ]
    cooldown_candle_rows = [
        row for row in cooldown_suppressed_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_CANDLE_WEIGHT
    ]
    cooldown_reverse_rows = [
        row for row in cooldown_suppressed_rows if _text(_mapping(row).get("detector_key")) == DETECTOR_REVERSE_PATTERN
    ]
    hindsight_summary = {
        HINDSIGHT_STATUS_CONFIRMED_MISREAD: 0,
        HINDSIGHT_STATUS_FALSE_ALARM: 0,
        HINDSIGHT_STATUS_PARTIAL_MISREAD: 0,
        HINDSIGHT_STATUS_UNRESOLVED: 0,
    }
    for row in all_rows:
        hindsight_status = _text(_mapping(row).get("hindsight_status"))
        if hindsight_status in hindsight_summary:
            hindsight_summary[hindsight_status] += 1

    total_surfaced = len(surfaced_rows)
    summary_ko = (
        f"log-only detector 관찰 {total_surfaced}건이 surface되었습니다."
        if total_surfaced
        else "지금은 surface할 detector 관찰이 없습니다."
    )
    why_now_ko = (
        surfaced_rows[0]["why_now_ko"]
        if surfaced_rows
        else "scene/candle/reverse detector 모두 관찰 단계이며 즉시 surface할 패턴은 아직 없습니다."
    )
    recommended_action_ko = (
        "보고서 topic에서 detector 관찰을 확인하고, 반복되는 패턴만 /propose 또는 review proposal로 승격합니다."
        if surfaced_rows
        else "지금은 detector 로그를 계속 쌓고 readiness/설명력 축을 우선 확인합니다."
    )
    readiness_status = READINESS_STATUS_READY_FOR_REVIEW if surfaced_rows else READINESS_STATUS_PENDING_EVIDENCE
    proposal_envelope = build_improvement_proposal_envelope(
        proposal_type="IMPROVEMENT_LOG_ONLY_DETECTOR_REPORT",
        scope_key=f"LOG_ONLY_DETECT::{max(10, int(recent_trade_limit))}",
        trace_id=generated_at,
        proposal_stage=PROPOSAL_STAGE_OBSERVE,
        readiness_status=readiness_status,
        summary_ko=summary_ko,
        why_now_ko=why_now_ko,
        recommended_action_ko=recommended_action_ko,
        confidence_level="MEDIUM" if surfaced_rows else "LOW",
        expected_effect_ko="문제 패턴을 자동 적용 없이 먼저 surface해서 detector 품질을 좁혀갑니다.",
        scope_note_ko=f"manual_detect_recent_limit={max(10, int(recent_trade_limit))}",
        evidence_snapshot={
            "scene_surface_count": len(scene_rows),
            "candle_surface_count": len(candle_rows),
            "reverse_surface_count": len(reverse_rows),
            "narrowed_out_count": len(narrowed_out_rows),
            "cooldown_suppressed_count": len(cooldown_suppressed_rows),
            "dropped_count": dropped_count,
        },
    )
    report_lines = _render_report_lines_v2(
        {
            "proposal_envelope": proposal_envelope,
            "scene_aware_detector": {"surfaced_rows": scene_rows},
            "candle_weight_detector": {"surfaced_rows": candle_rows},
            "reverse_pattern_detector": {"surfaced_rows": reverse_rows},
        }
    )
    inbox_summary = (
        f"[detector 관찰] scene {len(scene_rows)} / candle {len(candle_rows)} / reverse {len(reverse_rows)} / 총 {total_surfaced}건"
    )
    return {
        "contract_version": IMPROVEMENT_LOG_ONLY_DETECTOR_CONTRACT_VERSION,
        "generated_at": generated_at,
        "recent_trade_limit": max(10, int(recent_trade_limit)),
        "proposal_envelope": proposal_envelope,
        "detector_policy": build_improvement_detector_policy_baseline(),
        "surfaced_detector_count": total_surfaced,
        "narrowed_out_detector_count": len(narrowed_out_rows),
        "cooldown_suppressed_detector_count": len(cooldown_suppressed_rows),
        "dropped_detector_count": dropped_count,
        "feedback_narrowing_summary": narrowing_summary,
        "hindsight_summary": hindsight_summary,
        "cooldown_summary": cooldown_summary,
        "cooldown_state": cooldown_state,
        "feedback_issue_refs": [
            {
                "feedback_ref": _text(_mapping(row).get("feedback_ref")),
                "feedback_key": _text(_mapping(row).get("feedback_key")),
                "feedback_scope_key": _text(_mapping(row).get("feedback_scope_key")),
                "detector_key": _text(_mapping(row).get("detector_key")),
                "symbol": _text(_mapping(row).get("symbol")).upper(),
                "summary_ko": _text(_mapping(row).get("summary_ko")),
                "hindsight_status": _text(_mapping(row).get("hindsight_status")),
                "hindsight_status_ko": _text(_mapping(row).get("hindsight_status_ko")),
                "result_type": _text(_mapping(row).get("result_type")),
                "explanation_type": _text(_mapping(row).get("explanation_type")),
                "misread_confidence": _to_float(_mapping(row).get("misread_confidence"), 0.0),
                "context_flag": _text(_mapping(row).get("context_flag")),
                "registry_key": _text(_mapping(row).get("registry_key")),
                "registry_label_ko": _text(_mapping(row).get("registry_label_ko")),
                "registry_binding_mode": _text(_mapping(row).get("registry_binding_mode")),
                "evidence_registry_keys": list(_mapping(row).get("evidence_registry_keys") or []),
                "target_registry_keys": list(_mapping(row).get("target_registry_keys") or []),
                "context_bundle_summary_ko": _text(_mapping(row).get("context_bundle_summary_ko")),
                "weight_patch_preview": dict(_mapping(_mapping(row).get("weight_patch_preview"))),
                "threshold_patch_preview": dict(_mapping(_mapping(row).get("threshold_patch_preview"))),
                "repeat_count": _to_int(_mapping(row).get("repeat_count"), 0),
                "generated_at": generated_at,
            }
            for row in surfaced_rows
        ],
        "scene_aware_detector": {
            "detector_key": DETECTOR_SCENE_AWARE,
            "surface_limit": DETECTOR_DAILY_SURFACE_LIMITS[DETECTOR_SCENE_AWARE],
            "min_repeat_sample": DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_SCENE_AWARE],
            "candidate_count": len(scene_rows_all),
            "surfaced_rows": scene_rows,
            "narrowed_out_rows": narrowed_scene_rows,
            "cooldown_suppressed_rows": cooldown_scene_rows,
        },
        "candle_weight_detector": {
            "detector_key": DETECTOR_CANDLE_WEIGHT,
            "surface_limit": DETECTOR_DAILY_SURFACE_LIMITS[DETECTOR_CANDLE_WEIGHT],
            "min_repeat_sample": DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_CANDLE_WEIGHT],
            "candidate_count": len(candle_rows_all),
            "surfaced_rows": candle_rows,
            "narrowed_out_rows": narrowed_candle_rows,
            "cooldown_suppressed_rows": cooldown_candle_rows,
            "manual_trade_proposal_reference": {
                "analyzed_trade_count": _to_int(proposal_payload.get("analyzed_trade_count")),
                "surfaced_problem_pattern_count": len(list(proposal_payload.get("surfaced_problem_patterns") or [])),
            },
        },
        "reverse_pattern_detector": {
            "detector_key": DETECTOR_REVERSE_PATTERN,
            "surface_limit": DETECTOR_DAILY_SURFACE_LIMITS[DETECTOR_REVERSE_PATTERN],
            "min_repeat_sample": DETECTOR_MIN_REPEAT_SAMPLES[DETECTOR_REVERSE_PATTERN],
            "candidate_count": len(reverse_rows_all),
            "surfaced_rows": reverse_rows,
            "narrowed_out_rows": narrowed_reverse_rows,
            "cooldown_suppressed_rows": cooldown_reverse_rows,
        },
        "report_title_ko": "log-only detector 관찰 보고",
        "report_lines_ko": report_lines,
        "inbox_summary_ko": inbox_summary,
    }


def render_improvement_log_only_detector_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Improvement Log-Only Detector Snapshot",
        "",
        f"- contract_version: `{_text(_mapping(payload).get('contract_version'))}`",
        f"- generated_at: `{_text(_mapping(payload).get('generated_at'))}`",
        f"- surfaced_detector_count: `{_to_int(_mapping(payload).get('surfaced_detector_count'))}`",
        f"- dropped_detector_count: `{_to_int(_mapping(payload).get('dropped_detector_count'))}`",
        "",
        "## Report",
    ]
    for row in list(_mapping(payload).get("report_lines_ko") or []):
        lines.append(f"- {row}")
    return "\n".join(lines)


def write_improvement_log_only_detector_snapshot(
    payload: Mapping[str, Any],
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    default_json_path, default_markdown_path = default_improvement_log_only_detector_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_improvement_log_only_detector_markdown(payload),
        encoding="utf-8",
    )
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }


def build_default_improvement_log_only_detector_snapshot(
    *,
    closed_frame: pd.DataFrame | None,
    feedback_history: list[Mapping[str, Any]] | None = None,
    recent_trade_limit: int = DEFAULT_DETECT_RECENT_LIMIT,
    timezone: Any,
    now_ts: str = "",
    runtime_status_path: str | Path | None = None,
    runtime_status_detail_path: str | Path | None = None,
    readiness_surface_path: str | Path | None = None,
    scene_disagreement_path: str | Path | None = None,
    scene_bias_preview_path: str | Path | None = None,
    previous_snapshot_path: str | Path | None = None,
) -> dict[str, Any]:
    runtime_status_payload = _load_json(runtime_status_path or default_runtime_status_json_path())
    runtime_status_detail_payload = _load_json(
        runtime_status_detail_path or default_runtime_status_detail_json_path()
    )
    readiness_surface_payload = _load_json(
        readiness_surface_path or default_improvement_readiness_surface_json_path()
    )
    scene_disagreement_payload = _load_json(
        scene_disagreement_path or default_scene_disagreement_json_path()
    )
    scene_bias_preview_payload = _load_json(
        scene_bias_preview_path or default_scene_bias_preview_json_path()
    )
    default_snapshot_json_path, _ = default_improvement_log_only_detector_paths()
    previous_snapshot_payload = _load_json(
        previous_snapshot_path or default_snapshot_json_path
    )
    return build_improvement_log_only_detector_snapshot(
        runtime_status_payload=runtime_status_payload,
        runtime_status_detail_payload=runtime_status_detail_payload,
        readiness_surface_payload=readiness_surface_payload,
        scene_disagreement_payload=scene_disagreement_payload,
        scene_bias_preview_payload=scene_bias_preview_payload,
        closed_frame=closed_frame,
        feedback_history=feedback_history,
        previous_snapshot_payload=previous_snapshot_payload,
        recent_trade_limit=recent_trade_limit,
        timezone=timezone,
        now_ts=now_ts,
    )


def materialize_improvement_log_only_detector_baselines() -> dict[str, Any]:
    policy_paths = write_improvement_detector_policy_baseline_snapshot()
    payload = build_improvement_log_only_detector_snapshot(
        runtime_status_payload={},
        readiness_surface_payload={},
        closed_frame=pd.DataFrame(),
        recent_trade_limit=DEFAULT_DETECT_RECENT_LIMIT,
        timezone="Asia/Seoul",
    )
    snapshot_paths = write_improvement_log_only_detector_snapshot(payload)
    return {
        "policy_paths": policy_paths,
        "snapshot_paths": snapshot_paths,
    }
