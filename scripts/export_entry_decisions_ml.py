from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.semantic_v1.contracts import (  # noqa: E402
    SEMANTIC_FEATURE_CONTRACT_VERSION,
    SEMANTIC_TARGET_CONTRACT_VERSION,
)
from ml.semantic_v1.feature_packs import (  # noqa: E402
    ALL_CONTRACT_COLUMNS,
    SEMANTIC_INPUT_PACKS,
    SUPPORT_PACKS,
)
from backend.services.storage_compaction import (  # noqa: E402
    resolve_entry_decision_row_key,
    resolve_runtime_signal_row_key,
)

DEFAULT_SOURCE = PROJECT_ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "datasets" / "ml_exports"
DEFAULT_MANIFEST_ROOT = PROJECT_ROOT / "data" / "manifests"
DEFAULT_EXPORT_KIND = "forecast"
EXPORT_SCHEMA_VERSION = "entry_decisions_ml_semantic_v2"
EXPORT_MANIFEST_VERSION = "entry_decisions_ml_export_manifest_v1"
MISSINGNESS_REPORT_VERSION = "entry_decisions_ml_missingness_v1"
KEY_INTEGRITY_REPORT_VERSION = "entry_decisions_ml_key_integrity_v1"

BASE_COLUMNS = [
    "time",
    "signal_timeframe",
    "signal_bar_ts",
    "symbol",
    "action",
    "considered",
    "outcome",
    "blocked_by",
    "observe_reason",
    "action_none_reason",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "probe_candidate_active",
    "probe_direction",
    "probe_scene_id",
    "probe_candidate_support",
    "probe_pair_gap",
    "probe_plan_active",
    "probe_plan_ready",
    "probe_plan_reason",
    "probe_plan_scene",
    "probe_promotion_bias",
    "probe_temperament_source",
    "probe_entry_style",
    "probe_temperament_note",
    "edge_execution_scene_id",
    "quick_trace_state",
    "quick_trace_reason",
    "semantic_shadow_available",
    "semantic_shadow_reason",
    "semantic_shadow_activation_state",
    "semantic_shadow_activation_reason",
    "semantic_live_threshold_applied",
    "semantic_live_threshold_state",
    "semantic_live_threshold_reason",
    "signal_age_sec",
    "bar_age_sec",
    "decision_latency_ms",
    "order_submit_latency_ms",
    "missing_feature_count",
    "data_completeness_ratio",
    "used_fallback_count",
    "compatibility_mode",
    "detail_blob_bytes",
    "snapshot_payload_bytes",
    "row_payload_bytes",
    "entry_score_raw",
    "contra_score_raw",
    "effective_entry_threshold",
    "base_entry_threshold",
    "entry_stage",
    "ai_probability",
    "size_multiplier",
    "utility_u",
    "utility_p",
    "utility_p_raw",
    "utility_p_calibrated",
    "utility_stats_ready",
    "utility_wins_n",
    "utility_losses_n",
    "utility_w",
    "utility_l",
    "utility_cost",
    "utility_context_adj",
    "u_min",
    "u_pass",
    "decision_rule_version",
    "entry_decision_mode",
    "core_reason",
    "action_none_reason",
    "core_pass",
    "core_allowed_action",
    "box_state",
    "bb_state",
    "core_buy_raw",
    "core_sell_raw",
    "core_best_raw",
    "core_min_raw",
    "core_margin_raw",
    "core_tie_band_raw",
    "setup_id",
    "setup_side",
    "setup_status",
    "setup_trigger_state",
    "setup_score",
    "setup_entry_quality",
    "setup_reason",
    "wait_score",
    "wait_conflict",
    "wait_noise",
    "wait_penalty",
    "entry_wait_state",
    "entry_wait_hard",
    "entry_wait_reason",
    "entry_wait_selected",
    "entry_wait_decision",
    "entry_enter_value",
    "entry_wait_value",
    "transition_side_separation",
    "transition_confirm_fake_gap",
    "transition_reversal_continuation_gap",
    "management_continue_fail_gap",
    "management_recover_reentry_gap",
    "preflight_regime",
    "preflight_liquidity",
    "preflight_allowed_action",
    "preflight_approach_mode",
    "preflight_reason",
    "last_order_retcode",
    "order_block_remaining_sec",
    "consumer_archetype_id",
    "consumer_invalidation_id",
    "consumer_management_profile_id",
    "consumer_guard_result",
    "consumer_effective_action",
    "consumer_block_reason",
    "consumer_block_kind",
    "consumer_block_source_layer",
    "consumer_block_is_execution",
    "consumer_block_is_semantic_non_action",
]

TEXT_COLUMNS = {
    "time",
    "signal_timeframe",
    "symbol",
    "action",
    "outcome",
    "blocked_by",
    "observe_reason",
    "action_none_reason",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "compatibility_mode",
    "probe_direction",
    "probe_scene_id",
    "probe_plan_reason",
    "probe_plan_scene",
    "probe_promotion_bias",
    "probe_temperament_source",
    "probe_entry_style",
    "probe_temperament_note",
    "edge_execution_scene_id",
    "quick_trace_state",
    "quick_trace_reason",
    "semantic_shadow_reason",
    "semantic_shadow_activation_state",
    "semantic_shadow_activation_reason",
    "semantic_live_threshold_state",
    "semantic_live_threshold_reason",
    "entry_stage",
    "decision_rule_version",
    "entry_decision_mode",
    "core_reason",
    "action_none_reason",
    "core_allowed_action",
    "box_state",
    "bb_state",
    "setup_id",
    "setup_side",
    "setup_status",
    "setup_trigger_state",
    "setup_reason",
    "entry_wait_state",
    "entry_wait_reason",
    "entry_wait_decision",
    "preflight_regime",
    "preflight_liquidity",
    "preflight_allowed_action",
    "preflight_approach_mode",
    "preflight_reason",
    "consumer_archetype_id",
    "consumer_invalidation_id",
    "consumer_management_profile_id",
    "consumer_guard_result",
    "consumer_effective_action",
    "consumer_block_reason",
    "consumer_block_kind",
    "consumer_block_source_layer",
}

FLOAT_COLUMNS = {
    "entry_score_raw",
    "contra_score_raw",
    "signal_age_sec",
    "bar_age_sec",
    "probe_candidate_support",
    "probe_pair_gap",
    "effective_entry_threshold",
    "base_entry_threshold",
    "ai_probability",
    "size_multiplier",
    "utility_u",
    "utility_p",
    "utility_p_raw",
    "utility_p_calibrated",
    "utility_w",
    "utility_l",
    "utility_cost",
    "utility_context_adj",
    "u_min",
    "core_buy_raw",
    "core_sell_raw",
    "core_best_raw",
    "core_min_raw",
    "core_margin_raw",
    "core_tie_band_raw",
    "setup_score",
    "setup_entry_quality",
    "wait_score",
    "wait_conflict",
    "wait_noise",
    "wait_penalty",
    "entry_enter_value",
    "entry_wait_value",
    "transition_side_separation",
    "transition_confirm_fake_gap",
    "transition_reversal_continuation_gap",
    "management_continue_fail_gap",
    "management_recover_reentry_gap",
    "data_completeness_ratio",
}

INT_COLUMNS = {
    "signal_bar_ts",
    "considered",
    "decision_latency_ms",
    "order_submit_latency_ms",
    "missing_feature_count",
    "used_fallback_count",
    "detail_blob_bytes",
    "snapshot_payload_bytes",
    "row_payload_bytes",
    "utility_wins_n",
    "utility_losses_n",
    "last_order_retcode",
    "order_block_remaining_sec",
}

BOOL_INT_COLUMNS = {
    "utility_stats_ready",
    "u_pass",
    "core_pass",
    "entry_wait_hard",
    "probe_candidate_active",
    "probe_plan_active",
    "probe_plan_ready",
    "semantic_shadow_available",
    "semantic_live_threshold_applied",
    "consumer_block_is_execution",
    "consumer_block_is_semantic_non_action",
}


@dataclass(frozen=True)
class JsonFieldSpec:
    target: str
    path: tuple[str, ...]
    kind: str = "text"
    source: str = ""
    fallback: str | None = None


JSON_FIELD_SPECS = [
    JsonFieldSpec(
        target="observe_action",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("action",),
    ),
    JsonFieldSpec(
        target="observe_side",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("side",),
    ),
    JsonFieldSpec(
        target="observe_state",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("state",),
    ),
    JsonFieldSpec(
        target="observe_archetype_id",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("archetype_id",),
    ),
    JsonFieldSpec(
        target="observe_invalidation_id",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("invalidation_id",),
    ),
    JsonFieldSpec(
        target="observe_management_profile_id",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("management_profile_id",),
    ),
    JsonFieldSpec(
        target="observe_confidence",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("confidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="observe_reason",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("reason",),
    ),
    JsonFieldSpec(
        target="observe_blocked_reason",
        source="observe_confirm_v2",
        fallback="observe_confirm_v1",
        path=("metadata", "blocked_reason"),
    ),
    JsonFieldSpec(
        target="energy_selected_side",
        source="energy_helper_v2",
        path=("selected_side",),
    ),
    JsonFieldSpec(
        target="energy_action_readiness",
        source="energy_helper_v2",
        path=("action_readiness",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_continuation_support",
        source="energy_helper_v2",
        path=("continuation_support",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_reversal_support",
        source="energy_helper_v2",
        path=("reversal_support",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_suppression_pressure",
        source="energy_helper_v2",
        path=("suppression_pressure",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_forecast_support",
        source="energy_helper_v2",
        path=("forecast_support",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_net_utility",
        source="energy_helper_v2",
        path=("net_utility",),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_confidence_direction",
        source="energy_helper_v2",
        path=("confidence_adjustment_hint", "direction"),
    ),
    JsonFieldSpec(
        target="energy_confidence_delta_band",
        source="energy_helper_v2",
        path=("confidence_adjustment_hint", "delta_band"),
    ),
    JsonFieldSpec(
        target="energy_soft_block_active",
        source="energy_helper_v2",
        path=("soft_block_hint", "active"),
        kind="bool_int",
    ),
    JsonFieldSpec(
        target="energy_soft_block_reason",
        source="energy_helper_v2",
        path=("soft_block_hint", "reason"),
    ),
    JsonFieldSpec(
        target="energy_soft_block_strength",
        source="energy_helper_v2",
        path=("soft_block_hint", "strength"),
        kind="float",
    ),
    JsonFieldSpec(
        target="energy_priority_hint",
        source="energy_helper_v2",
        path=("metadata", "utility_hints", "priority_hint"),
    ),
    JsonFieldSpec(
        target="energy_wait_vs_enter_hint",
        source="energy_helper_v2",
        path=("metadata", "utility_hints", "wait_vs_enter_hint"),
    ),
    JsonFieldSpec(
        target="belief_dominant_side",
        source="belief_state_v1",
        path=("dominant_side",),
    ),
    JsonFieldSpec(
        target="belief_dominant_mode",
        source="belief_state_v1",
        path=("dominant_mode",),
    ),
    JsonFieldSpec(
        target="belief_buy_persistence",
        source="belief_state_v1",
        path=("buy_persistence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="belief_sell_persistence",
        source="belief_state_v1",
        path=("sell_persistence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="belief_buy_streak",
        source="belief_state_v1",
        path=("buy_streak",),
        kind="int",
    ),
    JsonFieldSpec(
        target="belief_sell_streak",
        source="belief_state_v1",
        path=("sell_streak",),
        kind="int",
    ),
    JsonFieldSpec(
        target="barrier_buy_barrier",
        source="barrier_state_v1",
        path=("buy_barrier",),
        kind="float",
    ),
    JsonFieldSpec(
        target="barrier_sell_barrier",
        source="barrier_state_v1",
        path=("sell_barrier",),
        kind="float",
    ),
    JsonFieldSpec(
        target="transition_p_buy_confirm",
        source="transition_forecast_v1",
        path=("p_buy_confirm",),
        kind="float",
    ),
    JsonFieldSpec(
        target="transition_p_sell_confirm",
        source="transition_forecast_v1",
        path=("p_sell_confirm",),
        kind="float",
    ),
    JsonFieldSpec(
        target="transition_p_false_break",
        source="transition_forecast_v1",
        path=("p_false_break",),
        kind="float",
    ),
    JsonFieldSpec(
        target="transition_p_continuation_success",
        source="transition_forecast_v1",
        path=("p_continuation_success",),
        kind="float",
    ),
    JsonFieldSpec(
        target="transition_p_reversal_success",
        source="transition_forecast_v1",
        path=("p_reversal_success",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_continue_favor",
        source="trade_management_forecast_v1",
        path=("p_continue_favor",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_fail_now",
        source="trade_management_forecast_v1",
        path=("p_fail_now",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_reach_tp1",
        source="trade_management_forecast_v1",
        path=("p_reach_tp1",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_opposite_edge_reach",
        source="trade_management_forecast_v1",
        path=("p_opposite_edge_reach",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_recover_after_pullback",
        source="trade_management_forecast_v1",
        path=("p_recover_after_pullback",),
        kind="float",
    ),
    JsonFieldSpec(
        target="management_p_better_reentry_if_cut",
        source="trade_management_forecast_v1",
        path=("p_better_reentry_if_cut",),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_box",
        source="position_snapshot_v2",
        path=("vector", "x_box"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_bb20",
        source="position_snapshot_v2",
        path=("vector", "x_bb20"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_bb44",
        source="position_snapshot_v2",
        path=("vector", "x_bb44"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_ma20",
        source="position_snapshot_v2",
        path=("vector", "x_ma20"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_ma60",
        source="position_snapshot_v2",
        path=("vector", "x_ma60"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_sr",
        source="position_snapshot_v2",
        path=("vector", "x_sr"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_x_trendline",
        source="position_snapshot_v2",
        path=("vector", "x_trendline"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_pos_composite",
        source="position_snapshot_v2",
        path=("interpretation", "pos_composite"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_alignment_label",
        source="position_snapshot_v2",
        path=("interpretation", "alignment_label"),
    ),
    JsonFieldSpec(
        target="position_bias_label",
        source="position_snapshot_v2",
        path=("interpretation", "bias_label"),
    ),
    JsonFieldSpec(
        target="position_conflict_kind",
        source="position_snapshot_v2",
        path=("interpretation", "conflict_kind"),
    ),
    JsonFieldSpec(
        target="position_lower_force",
        source="position_snapshot_v2",
        path=("energy", "lower_position_force"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_upper_force",
        source="position_snapshot_v2",
        path=("energy", "upper_position_force"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_middle_neutrality",
        source="position_snapshot_v2",
        path=("energy", "middle_neutrality"),
        kind="float",
    ),
    JsonFieldSpec(
        target="position_conflict_score",
        source="position_snapshot_v2",
        path=("energy", "position_conflict_score"),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_lower_break_down",
        source="response_vector_v2",
        path=("lower_break_down",),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_lower_hold_up",
        source="response_vector_v2",
        path=("lower_hold_up",),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_mid_lose_down",
        source="response_vector_v2",
        path=("mid_lose_down",),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_mid_reclaim_up",
        source="response_vector_v2",
        path=("mid_reclaim_up",),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_upper_break_up",
        source="response_vector_v2",
        path=("upper_break_up",),
        kind="float",
    ),
    JsonFieldSpec(
        target="response_upper_reject_down",
        source="response_vector_v2",
        path=("upper_reject_down",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_alignment_gain",
        source="state_vector_v2",
        path=("alignment_gain",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_breakout_continuation_gain",
        source="state_vector_v2",
        path=("breakout_continuation_gain",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_trend_pullback_gain",
        source="state_vector_v2",
        path=("trend_pullback_gain",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_range_reversal_gain",
        source="state_vector_v2",
        path=("range_reversal_gain",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_conflict_damp",
        source="state_vector_v2",
        path=("conflict_damp",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_noise_damp",
        source="state_vector_v2",
        path=("noise_damp",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_liquidity_penalty",
        source="state_vector_v2",
        path=("liquidity_penalty",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_volatility_penalty",
        source="state_vector_v2",
        path=("volatility_penalty",),
        kind="float",
    ),
    JsonFieldSpec(
        target="state_countertrend_penalty",
        source="state_vector_v2",
        path=("countertrend_penalty",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_buy_total",
        source="evidence_vector_v1",
        path=("buy_total_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_buy_continuation",
        source="evidence_vector_v1",
        path=("buy_continuation_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_buy_reversal",
        source="evidence_vector_v1",
        path=("buy_reversal_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_sell_total",
        source="evidence_vector_v1",
        path=("sell_total_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_sell_continuation",
        source="evidence_vector_v1",
        path=("sell_continuation_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="evidence_sell_reversal",
        source="evidence_vector_v1",
        path=("sell_reversal_evidence",),
        kind="float",
    ),
    JsonFieldSpec(
        target="forecast_position_primary_label",
        source="forecast_features_v1",
        path=("position_primary_label",),
    ),
    JsonFieldSpec(
        target="forecast_position_secondary_context_label",
        source="forecast_features_v1",
        path=("position_secondary_context_label",),
    ),
    JsonFieldSpec(
        target="forecast_position_conflict_score",
        source="forecast_features_v1",
        path=("position_conflict_score",),
        kind="float",
    ),
    JsonFieldSpec(
        target="forecast_middle_neutrality",
        source="forecast_features_v1",
        path=("middle_neutrality",),
        kind="float",
    ),
    JsonFieldSpec(
        target="forecast_management_horizon_bars",
        source="forecast_features_v1",
        path=("metadata", "management_horizon_bars"),
        kind="int",
    ),
    JsonFieldSpec(
        target="forecast_signal_timeframe",
        source="forecast_features_v1",
        path=("metadata", "signal_timeframe"),
    ),
]

JSON_SOURCE_COLUMNS = sorted(
    {
        spec.source
        for spec in JSON_FIELD_SPECS
        if spec.source
    }
    | {
        spec.fallback
        for spec in JSON_FIELD_SPECS
        if spec.fallback
    }
)
SOURCE_COLUMNS = sorted(set(BASE_COLUMNS) | set(JSON_SOURCE_COLUMNS))
OUTPUT_COLUMNS = list(dict.fromkeys([*BASE_COLUMNS, *(spec.target for spec in JSON_FIELD_SPECS)]))

_MISSING_CONTRACT_COLUMNS = sorted(set(ALL_CONTRACT_COLUMNS) - set(OUTPUT_COLUMNS))
if _MISSING_CONTRACT_COLUMNS:
    raise RuntimeError(
        "export_entry_decisions_ml is missing semantic contract columns: "
        + ", ".join(_MISSING_CONTRACT_COLUMNS)
    )


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def _resolve_manifest_root(value: str | None) -> Path:
    return _resolve_path(value, DEFAULT_MANIFEST_ROOT)


def _ensure_manifest_dirs(manifest_root: Path) -> dict[str, Path]:
    mapping = {
        "export": manifest_root / "export",
    }
    for path in mapping.values():
        path.mkdir(parents=True, exist_ok=True)
    return mapping


def _write_manifest(dir_path: Path, prefix: str, payload: Mapping[str, Any], timestamp: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    out_path = dir_path / f"{prefix}_{timestamp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _missing_mask(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series.dtype):
        return series.isna()
    text = series.fillna("").astype(str).str.strip()
    return text.eq("") | text.str.lower().isin({"nan", "none", "null"})


def _normalized_key_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index, dtype="string")
    text = frame[column].fillna("").astype("string").str.strip()
    return text.mask(text.str.lower().isin({"nan", "none", "null"}), "")


def _duplicate_key_summary(series: pd.Series) -> dict[str, Any]:
    non_empty = series[series.ne("")]
    if non_empty.empty:
        return {
            "duplicate_key_count": 0,
            "duplicate_row_excess_count": 0,
            "sample_values": {},
        }
    counts = non_empty.value_counts()
    duplicates = counts[counts > 1]
    return {
        "duplicate_key_count": int(len(duplicates)),
        "duplicate_row_excess_count": int((duplicates - 1).sum()) if not duplicates.empty else 0,
        "sample_values": {str(key): int(value) for key, value in duplicates.head(5).items()},
    }


def _build_key_integrity_report(
    frame: pd.DataFrame,
    *,
    created_at: str,
    source_path: Path,
    output_path: Path,
    export_kind: str,
) -> dict[str, Any]:
    decision_keys = _normalized_key_series(frame, "decision_row_key")
    runtime_keys = _normalized_key_series(frame, "runtime_snapshot_key")
    trade_keys = _normalized_key_series(frame, "trade_link_key")
    replay_keys = _normalized_key_series(frame, "replay_row_key")
    decision_replay_mismatch = decision_keys.ne("") & replay_keys.ne("") & decision_keys.ne(replay_keys)

    return {
        "created_at": created_at,
        "report_version": KEY_INTEGRITY_REPORT_VERSION,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "source_path": str(source_path),
        "output_path": str(output_path),
        "export_kind": export_kind,
        "rows": int(len(frame)),
        "missing_key_rows": {
            "decision_row_key": int(decision_keys.eq("").sum()),
            "runtime_snapshot_key": int(runtime_keys.eq("").sum()),
            "trade_link_key": int(trade_keys.eq("").sum()),
            "replay_row_key": int(replay_keys.eq("").sum()),
        },
        "duplicate_keys": {
            "decision_row_key": _duplicate_key_summary(decision_keys),
            "runtime_snapshot_key": _duplicate_key_summary(runtime_keys),
            "trade_link_key": _duplicate_key_summary(trade_keys),
            "replay_row_key": _duplicate_key_summary(replay_keys),
        },
        "decision_replay_mismatch_rows": int(decision_replay_mismatch.sum()),
        "decision_replay_mismatch_samples": [
            {
                "decision_row_key": str(decision_keys.loc[index]),
                "replay_row_key": str(replay_keys.loc[index]),
            }
            for index in frame.index[decision_replay_mismatch].tolist()[:5]
        ],
    }


def _normalize_group_series(df: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="string")
    series = df[column].fillna("").astype(str).str.strip()
    invalid = series.eq("") | series.str.lower().isin({"nan", "none", "null"})
    return series.mask(invalid, default).astype("string")


def _update_missingness_counts(
    store: dict[str, dict[str, Any]],
    key: str,
    frame: pd.DataFrame,
    missing_masks: dict[str, pd.Series],
) -> None:
    entry = store.setdefault(
        str(key),
        {
            "rows": 0,
            "missing_rows": {column: 0 for column in frame.columns},
        },
    )
    entry["rows"] += int(len(frame))
    for column, mask in missing_masks.items():
        if column not in entry["missing_rows"]:
            entry["missing_rows"][column] = 0
        entry["missing_rows"][column] += int(mask.loc[frame.index].sum())


def _finalize_missingness_bucket(
    rows: int,
    missing_rows: Mapping[str, int],
) -> dict[str, Any]:
    output = {
        "rows": int(rows),
        "missing_rows": {},
        "missing_rate": {},
    }
    for column, count in missing_rows.items():
        output["missing_rows"][str(column)] = int(count)
        output["missing_rate"][str(column)] = (
            None if rows <= 0 else round(float(count) / float(rows), 6)
        )
    return output


def _bool_to_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"1", "true", "yes", "y", "on"}:
        return 1
    if text in {"0", "false", "no", "n", "off"}:
        return 0
    try:
        return 1 if float(text) != 0.0 else 0
    except ValueError:
        return None


def _parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return {}


def _get_nested(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _coerce_value(value: Any, kind: str) -> Any:
    if kind == "float":
        if value in ("", None):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if kind == "int":
        if value in ("", None):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
    if kind == "bool_int":
        return _bool_to_int(value)
    if value in ("", None):
        return ""
    return str(value)


def _build_output_path(
    source: Path,
    output_dir: Path,
    explicit_output: str | None,
    *,
    export_kind: str,
) -> Path:
    if explicit_output:
        return _resolve_path(explicit_output, output_dir / export_kind / "entry_decisions_ml.parquet")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / export_kind / f"{source.stem}.ml_semantic_{export_kind}_{ts}.parquet"


def _apply_filters(chunk: pd.DataFrame, *, symbols: set[str], entered_only: bool, remaining: int | None) -> pd.DataFrame:
    out = chunk
    if symbols:
        symbol_series = out["symbol"] if "symbol" in out.columns else pd.Series([""] * len(out), index=out.index)
        out = out[symbol_series.astype(str).str.upper().isin(symbols)]
    if entered_only:
        outcome_series = out["outcome"] if "outcome" in out.columns else pd.Series([""] * len(out), index=out.index)
        out = out[outcome_series.astype(str).str.lower() == "entered"]
    if remaining is not None:
        out = out.head(max(0, remaining))
    return out


def _normalize_key_seed_value(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    return value


def _derive_identity_keys(chunk: pd.DataFrame, out: pd.DataFrame) -> None:
    row_count = len(out)
    if row_count <= 0:
        return

    def _source_values(frame: pd.DataFrame, column: str) -> list[Any]:
        if column not in frame.columns:
            return [""] * row_count
        values = frame[column].tolist()
        if len(values) != row_count:
            values = list(values[:row_count]) + ([""] * max(0, row_count - len(values)))
        return values

    source_times = _source_values(chunk, "time")
    source_signal_bar_ts = _source_values(chunk, "signal_bar_ts")
    source_symbols = _source_values(chunk, "symbol")
    source_actions = _source_values(chunk, "action")
    source_setup_ids = _source_values(chunk, "setup_id")
    source_outcomes = _source_values(out, "outcome")
    source_observe_reasons = _source_values(out, "observe_reason")
    source_blocked_by = _source_values(out, "blocked_by")
    source_action_none_reasons = _source_values(out, "action_none_reason")
    source_quick_trace_states = _source_values(out, "quick_trace_state")

    existing_decision_keys = out["decision_row_key"].fillna("").astype(str).tolist()
    existing_runtime_keys = out["runtime_snapshot_key"].fillna("").astype(str).tolist()
    existing_replay_keys = out["replay_row_key"].fillna("").astype(str).tolist()

    derived_decision_keys: list[str] = []
    derived_runtime_keys: list[str] = []
    derived_replay_keys: list[str] = []

    for idx in range(row_count):
        seed_row = {
            "time": _normalize_key_seed_value(source_times[idx]),
            "signal_bar_ts": _normalize_key_seed_value(source_signal_bar_ts[idx]),
            "symbol": _normalize_key_seed_value(source_symbols[idx]),
            "action": _normalize_key_seed_value(source_actions[idx]),
            "setup_id": _normalize_key_seed_value(source_setup_ids[idx]),
            "outcome": _normalize_key_seed_value(source_outcomes[idx]),
            "observe_reason": _normalize_key_seed_value(source_observe_reasons[idx]),
            "blocked_by": _normalize_key_seed_value(source_blocked_by[idx]),
            "action_none_reason": _normalize_key_seed_value(source_action_none_reasons[idx]),
            "quick_trace_state": _normalize_key_seed_value(source_quick_trace_states[idx]),
        }
        decision_key = str(existing_decision_keys[idx] or "").strip() or resolve_entry_decision_row_key(seed_row)
        runtime_key = str(existing_runtime_keys[idx] or "").strip()
        if not runtime_key:
            runtime_key = resolve_runtime_signal_row_key(seed_row)
        replay_key = str(existing_replay_keys[idx] or "").strip() or decision_key
        derived_decision_keys.append(decision_key)
        derived_runtime_keys.append(runtime_key)
        derived_replay_keys.append(replay_key)

    out["decision_row_key"] = pd.Series(derived_decision_keys, index=out.index, dtype="string")
    out["runtime_snapshot_key"] = pd.Series(derived_runtime_keys, index=out.index, dtype="string")
    out["replay_row_key"] = pd.Series(derived_replay_keys, index=out.index, dtype="string")


def _transform_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    out_data: dict[str, Any] = {}
    for column in BASE_COLUMNS:
        if column in chunk.columns:
            out_data[column] = chunk[column]
        else:
            out_data[column] = [""] * len(chunk)

    parsed_json_columns: dict[str, list[dict[str, Any]]] = {}
    for column in JSON_SOURCE_COLUMNS:
        if column not in chunk.columns:
            parsed_json_columns[column] = [{} for _ in range(len(chunk))]
            continue
        parsed_json_columns[column] = [_parse_json(value) for value in chunk[column].tolist()]

    for spec in JSON_FIELD_SPECS:
        primary_payloads = parsed_json_columns.get(spec.source, [])
        fallback_payloads = parsed_json_columns.get(spec.fallback, []) if spec.fallback else []
        base_values = out_data.get(spec.target)
        values: list[Any] = []
        for idx in range(len(chunk)):
            primary_payload = primary_payloads[idx] if idx < len(primary_payloads) else {}
            fallback_payload = fallback_payloads[idx] if idx < len(fallback_payloads) else {}
            payload = primary_payload or fallback_payload
            value = _coerce_value(_get_nested(payload, spec.path), spec.kind)
            if value in ("", None) and base_values is not None:
                if hasattr(base_values, "iloc"):
                    base_value = base_values.iloc[idx] if idx < len(base_values) else ""
                elif isinstance(base_values, (list, tuple)):
                    base_value = base_values[idx] if idx < len(base_values) else ""
                else:
                    base_value = ""
                if base_value not in ("", None):
                    value = _coerce_value(base_value, spec.kind)
            values.append(value)
        out_data[spec.target] = values

    out = pd.DataFrame(out_data)
    _derive_identity_keys(chunk, out)

    for column in sorted(TEXT_COLUMNS | {spec.target for spec in JSON_FIELD_SPECS if spec.kind == "text"}):
        if column in out.columns:
            out[column] = out[column].fillna("").astype("string")

    for column in sorted(FLOAT_COLUMNS | {spec.target for spec in JSON_FIELD_SPECS if spec.kind == "float"}):
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").astype("float32")

    for column in sorted(INT_COLUMNS | {spec.target for spec in JSON_FIELD_SPECS if spec.kind == "int"}):
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").round().astype("Int64")

    for column in sorted(BOOL_INT_COLUMNS | {spec.target for spec in JSON_FIELD_SPECS if spec.kind == "bool_int"}):
        if column in out.columns:
            out[column] = out[column].map(_bool_to_int).astype("Int8")

    return out.reset_index(drop=True)


def _empty_output_frame() -> pd.DataFrame:
    empty = pd.DataFrame(columns=SOURCE_COLUMNS)
    transformed = _transform_chunk(empty)
    return transformed.reindex(columns=OUTPUT_COLUMNS)


def _update_time_bounds(
    current_min: str | None,
    current_max: str | None,
    series: pd.Series,
) -> tuple[str | None, str | None]:
    if series.empty:
        return current_min, current_max
    values = series.fillna("").astype(str).str.strip()
    values = values[values.ne("")]
    if values.empty:
        return current_min, current_max
    candidate_min = str(values.min())
    candidate_max = str(values.max())
    if current_min is None or candidate_min < current_min:
        current_min = candidate_min
    if current_max is None or candidate_max > current_max:
        current_max = candidate_max
    return current_min, current_max


def export_entry_decisions_ml(
    source_path: Path,
    output_path: Path,
    *,
    batch_rows: int,
    symbols: list[str],
    entered_only: bool,
    limit: int | None,
    compression: str,
    manifest_root: Path,
    export_kind: str,
) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(f"source file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_dirs = _ensure_manifest_dirs(manifest_root)
    if output_path.exists():
        output_path.unlink()

    reader = pd.read_csv(
        source_path,
        encoding="utf-8-sig",
        chunksize=max(100, int(batch_rows)),
        low_memory=True,
        usecols=lambda name: name in SOURCE_COLUMNS,
    )

    writer: pq.ParquetWriter | None = None
    scanned_rows = 0
    written_rows = 0
    symbol_filter = {str(symbol or "").upper().strip() for symbol in symbols if str(symbol or "").strip()}
    remaining = int(limit) if limit is not None else None
    selected_columns = list(OUTPUT_COLUMNS)
    observed_symbols: set[str] = set()
    observed_setup_ids: set[str] = set()
    min_time: str | None = None
    max_time: str | None = None
    overall_missing_rows = {column: 0 for column in selected_columns}
    missingness_by_symbol: dict[str, dict[str, Any]] = {}
    missingness_by_setup: dict[str, dict[str, Any]] = {}

    try:
        for chunk in reader:
            scanned_rows += int(len(chunk))
            filtered = _apply_filters(
                chunk,
                symbols=symbol_filter,
                entered_only=entered_only,
                remaining=remaining,
            )
            if filtered.empty:
                continue

            transformed = _transform_chunk(filtered).reindex(columns=selected_columns)
            min_time, max_time = _update_time_bounds(min_time, max_time, transformed["time"])
            symbol_groups = _normalize_group_series(transformed, "symbol", "__missing_symbol__")
            setup_groups = _normalize_group_series(transformed, "setup_id", "__missing_setup_id__")
            observed_symbols.update({value for value in symbol_groups.unique().tolist() if value})
            observed_setup_ids.update({value for value in setup_groups.unique().tolist() if value})

            missing_masks = {column: _missing_mask(transformed[column]) for column in transformed.columns}
            for column, mask in missing_masks.items():
                overall_missing_rows[column] += int(mask.sum())
            for group_key, group_frame in transformed.groupby(symbol_groups, dropna=False):
                _update_missingness_counts(missingness_by_symbol, str(group_key), group_frame, missing_masks)
            for group_key, group_frame in transformed.groupby(setup_groups, dropna=False):
                _update_missingness_counts(missingness_by_setup, str(group_key), group_frame, missing_masks)

            table = pa.Table.from_pandas(transformed, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(
                    output_path,
                    table.schema,
                    compression=(None if compression == "none" else compression),
                    use_dictionary=True,
                )
            writer.write_table(table)
            written_rows += int(len(transformed))

            if remaining is not None:
                remaining -= int(len(transformed))
                if remaining <= 0:
                    break
    finally:
        if writer is not None:
            writer.close()

    if writer is None:
        empty_frame = _empty_output_frame()
        table = pa.Table.from_pandas(empty_frame, preserve_index=False)
        writer = pq.ParquetWriter(
            output_path,
            table.schema,
            compression=(None if compression == "none" else compression),
            use_dictionary=True,
        )
        writer.write_table(table)
        writer.close()

    now = datetime.now().astimezone()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    output_bytes = int(output_path.stat().st_size) if output_path.exists() else 0
    source_bytes = int(source_path.stat().st_size)
    missingness_report = {
        "created_at": now.isoformat(),
        "report_version": MISSINGNESS_REPORT_VERSION,
        "schema_version": EXPORT_SCHEMA_VERSION,
        "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
        "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
        "semantic_input_pack_keys": [pack.key for pack in SEMANTIC_INPUT_PACKS],
        "support_pack_keys": [pack.key for pack in SUPPORT_PACKS],
        "source_path": str(source_path),
        "output_path": str(output_path),
        "export_kind": export_kind,
        "rows_written": int(written_rows),
        "selected_columns": list(selected_columns),
        "selected_column_count": len(selected_columns),
        "overall": _finalize_missingness_bucket(written_rows, overall_missing_rows),
        "missing_columns": [
            str(column)
            for column in selected_columns
            if int(overall_missing_rows.get(column, 0)) >= int(written_rows)
        ],
        "by_symbol": {
            key: _finalize_missingness_bucket(value["rows"], value["missing_rows"])
            for key, value in sorted(missingness_by_symbol.items())
        },
        "by_setup_id": {
            key: _finalize_missingness_bucket(value["rows"], value["missing_rows"])
            for key, value in sorted(missingness_by_setup.items())
        },
    }
    missingness_path = output_path.with_suffix(output_path.suffix + ".missingness.json")
    missingness_path.write_text(json.dumps(missingness_report, ensure_ascii=False, indent=2), encoding="utf-8")
    exported_frame = pd.read_parquet(output_path)
    key_integrity_report = _build_key_integrity_report(
        exported_frame,
        created_at=now.isoformat(),
        source_path=source_path,
        output_path=output_path,
        export_kind=export_kind,
    )
    key_integrity_path = output_path.with_suffix(output_path.suffix + ".key_integrity.json")
    key_integrity_path.write_text(json.dumps(key_integrity_report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "created_at": now.isoformat(),
        "schema_version": EXPORT_SCHEMA_VERSION,
        "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
        "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
        "semantic_input_pack_keys": [pack.key for pack in SEMANTIC_INPUT_PACKS],
        "support_pack_keys": [pack.key for pack in SUPPORT_PACKS],
        "source_path": str(source_path),
        "output_path": str(output_path),
        "source_bytes": source_bytes,
        "output_bytes": output_bytes,
        "rows_scanned": scanned_rows,
        "rows_written": written_rows,
        "columns_written": len(selected_columns),
        "selected_columns": list(selected_columns),
        "missing_columns": list(missingness_report.get("missing_columns", [])),
        "compression": compression,
        "export_kind": export_kind,
        "entered_only": bool(entered_only),
        "symbols": sorted(symbol_filter),
        "limit": (None if limit is None else int(limit)),
        "symbols_written": sorted(observed_symbols),
        "setup_ids_written": sorted(observed_setup_ids),
        "time_range_start": min_time,
        "time_range_end": max_time,
        "raw_nested_payload_included": False,
        "compression_ratio": (None if output_bytes <= 0 else round(source_bytes / output_bytes, 3)),
        "missingness_report_path": str(missingness_path),
        "key_integrity_report_path": str(key_integrity_path),
    }
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    summary["summary_path"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "created_at": now.isoformat(),
        "job_name": f"entry_decisions_ml_export_{export_kind}",
        "source_path": str(source_path),
        "output_path": str(output_path),
        "schema_version": EXPORT_SCHEMA_VERSION,
        "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
        "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
        "semantic_input_pack_keys": [pack.key for pack in SEMANTIC_INPUT_PACKS],
        "support_pack_keys": [pack.key for pack in SUPPORT_PACKS],
        "manifest_version": EXPORT_MANIFEST_VERSION,
        "row_count": int(written_rows),
        "file_size_bytes": int(output_bytes),
        "compression": compression,
        "retention_policy": "managed_by_ml_export_tier",
        "export_kind": export_kind,
        "rows_scanned": int(scanned_rows),
        "source_size_bytes": int(source_bytes),
        "selected_columns": list(selected_columns),
        "selected_column_count": len(selected_columns),
        "missing_columns": list(missingness_report.get("missing_columns", [])),
        "filters": {
            "symbols": sorted(symbol_filter),
            "entered_only": bool(entered_only),
            "limit": (None if limit is None else int(limit)),
        },
        "time_range_start": min_time,
        "time_range_end": max_time,
        "raw_nested_payload_included": False,
        "summary_path": str(summary_path),
        "missingness_report_path": str(missingness_path),
        "key_integrity_report_path": str(key_integrity_path),
    }
    manifest_path = _write_manifest(
        manifest_dirs["export"],
        f"entry_decisions_ml_export_{export_kind}",
        manifest,
        timestamp,
    )
    summary["manifest_path"] = str(manifest_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a slim, ML-friendly Parquet dataset from entry_decisions.csv.",
    )
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Path to entry_decisions.csv",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output parquet path. Defaults to data/datasets/ml_exports/<timestamp>.parquet",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated parquet files when --output is omitted.",
    )
    parser.add_argument(
        "--export-kind",
        default=DEFAULT_EXPORT_KIND,
        choices=["forecast", "replay"],
        help="Export tier subdirectory under ml_exports.",
    )
    parser.add_argument(
        "--manifest-root",
        default=str(DEFAULT_MANIFEST_ROOT),
        help="Manifest root directory. Defaults to data/manifests.",
    )
    parser.add_argument(
        "--batch-rows",
        type=int,
        default=5000,
        help="Rows to process per chunk.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of filtered rows to export.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Optional symbol filter. Repeat for multiple symbols.",
    )
    parser.add_argument(
        "--entered-only",
        action="store_true",
        help="Only export rows where outcome == entered.",
    )
    parser.add_argument(
        "--compression",
        default="zstd",
        choices=["zstd", "snappy", "gzip", "brotli", "none"],
        help="Parquet compression codec.",
    )
    args = parser.parse_args()

    source_path = _resolve_path(args.source, DEFAULT_SOURCE)
    output_dir = _resolve_path(args.output_dir, DEFAULT_OUTPUT_DIR)
    output_path = _build_output_path(
        source=source_path,
        output_dir=output_dir,
        explicit_output=args.output,
        export_kind=str(args.export_kind),
    )
    manifest_root = _resolve_manifest_root(args.manifest_root)
    summary = export_entry_decisions_ml(
        source_path=source_path,
        output_path=output_path,
        batch_rows=int(args.batch_rows),
        symbols=list(args.symbol),
        entered_only=bool(args.entered_only),
        limit=args.limit,
        compression=str(args.compression),
        manifest_root=manifest_root,
        export_kind=str(args.export_kind),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
