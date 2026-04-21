"""
Trading application orchestration (phase 1 extraction from main.py).
"""

import logging
import os
import time
import json
import re
import csv
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from ml.runtime import AIModelRuntime
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard, SEMANTIC_LIVE_ROLLOUT_VERSION
from ml.semantic_v1.runtime_adapter import SemanticShadowRuntime

from adapters.mt5_connection_adapter import connect_to_mt5, disconnect_mt5
from adapters.mt5_broker_adapter import MT5BrokerAdapter
from adapters.telegram_notifier_adapter import TelegramNotifierAdapter
from adapters.file_observability_adapter import FileObservabilityAdapter
from backend.core.config import Config
from backend.core.trade_constants import (
    ORDER_FILLING_IOC,
    ORDER_TIME_GTC,
    ORDER_TYPE_BUY,
    ORDER_TYPE_SELL,
    TIMEFRAME_D1,
    TIMEFRAME_H1,
    TIMEFRAME_H4,
    TIMEFRAME_M1,
    TIMEFRAME_M5,
    TIMEFRAME_M15,
    TIMEFRAME_M30,
    TIMEFRAME_W1,
    TRADE_ACTION_DEAL,
    TRADE_ACTION_SLTP,
    TRADE_RETCODE_DONE,
)
from backend.services.exit_wait_taxonomy_contract import build_exit_wait_taxonomy_v1
from backend.services.context_state_builder import build_context_state_v12
from backend.services.directional_continuation_chart_overlay import (
    build_directional_continuation_chart_overlay_flat_fields_v1,
    build_directional_continuation_chart_overlay_state,
)
from backend.services.directional_continuation_learning_candidate import (
    build_directional_continuation_learning_candidates,
)
from backend.services.directional_continuation_accuracy_tracker import (
    build_directional_continuation_accuracy_flat_fields_v1,
    update_directional_continuation_accuracy_tracker,
)
from backend.services.htf_trend_cache import HtfTrendCache
from backend.services.previous_box_calculator import PreviousBoxCalculator
from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_flat_fields_v1,
    build_state25_candidate_context_bridge_v1,
)
from backend.trading.chart_painter import Painter
from backend.trading.scorer import Scorer
from backend.trading.symbol_resolver import SymbolResolver
from backend.trading.trade_logger import TradeLogger
from backend.services.entry_service import EntryService
from backend.services.exit_service import ExitService
from backend.services.policy_service import PolicyService
from backend.services.storage_compaction import (
    RUNTIME_STATUS_DETAIL_SCHEMA_VERSION,
    compact_runtime_signal_row,
    resolve_runtime_status_detail_path,
)
from backend.services.runtime_recycle import (
    build_runtime_recycle_state,
    build_runtime_recycle_drift_v1,
    build_runtime_recycle_health_v1,
    export_runtime_recycle_state,
)
from backend.services.teacher_pattern_active_candidate_runtime import (
    build_state25_candidate_size_surface_v1,
    build_state25_candidate_threshold_surface_v1,
    build_state25_candidate_weight_surface_v1,
    load_state25_candidate_runtime_state,
)
from backend.services.runtime_signal_surface import (
    build_legacy_raw_score_surface_v1,
    build_position_energy_surface_v1,
    enrich_runtime_signal_surface_v1,
)
from backend.services.runtime_signal_wiring_audit import generate_and_write_runtime_signal_wiring_audit
from backend.services.ca2_r0_stability_audit import generate_and_write_ca2_r0_stability_audit
from backend.services.ca2_session_split_audit import generate_and_write_ca2_session_split_audit
from backend.services.session_bucket_helper import (
    build_runtime_row_session_bucket_surface_v1,
    build_session_bucket_contract_v1,
)
from backend.services.session_direction_annotation_contract import (
    build_session_direction_annotation_contract_v1,
)
from backend.services.should_have_done_contract import build_should_have_done_contract_v1
from backend.services.should_have_done_candidate_summary import (
    generate_and_write_should_have_done_candidate_summary,
)
from backend.services.canonical_surface_builder import (
    attach_canonical_surface_fields_v1,
    build_canonical_surface_contract_v1,
    generate_and_write_canonical_surface_summary_v1,
)
from backend.services.session_aware_annotation_accuracy import (
    build_session_aware_annotation_accuracy_contract_v1,
    generate_and_write_session_aware_annotation_accuracy_v1,
)
from backend.services.session_bias_shadow_report import (
    attach_session_bias_shadow_fields_v1,
    build_session_bias_shadow_contract_v1,
    generate_and_write_session_bias_shadow_report_v1,
)
from backend.services.state_strength_s0_stability_guard import (
    generate_and_write_state_strength_s0_stability_report_v1,
)
from backend.services.state_polarity_d0_stability_guard import (
    generate_and_write_state_polarity_d0_stability_report_v1,
)
from backend.services.state_polarity_slot_vocabulary_contract import (
    build_state_polarity_slot_vocabulary_contract_v1,
    generate_and_write_state_polarity_slot_vocabulary_summary_v1,
)
from backend.services.rejection_split_rule_contract import (
    build_rejection_split_rule_contract_v1,
    generate_and_write_rejection_split_rule_summary_v1,
)
from backend.services.continuation_stage_contract import (
    build_continuation_stage_contract_v1,
    generate_and_write_continuation_stage_summary_v1,
)
from backend.services.location_context_contract import (
    build_location_context_contract_v1,
    generate_and_write_location_context_summary_v1,
)
from backend.services.tempo_profile_contract import (
    build_tempo_profile_contract_v1,
    generate_and_write_tempo_profile_summary_v1,
)
from backend.services.ambiguity_modifier_contract import (
    build_ambiguity_modifier_contract_v1,
    generate_and_write_ambiguity_modifier_summary_v1,
)
from backend.services.xau_pilot_mapping_contract import (
    build_xau_pilot_mapping_contract_v1,
    generate_and_write_xau_pilot_mapping_summary_v1,
)
from backend.services.nas_pilot_mapping_contract import (
    build_nas_pilot_mapping_contract_v1,
    generate_and_write_nas_pilot_mapping_summary_v1,
)
from backend.services.btc_pilot_mapping_contract import (
    build_btc_pilot_mapping_contract_v1,
    generate_and_write_btc_pilot_mapping_summary_v1,
)
from backend.services.xau_readonly_surface_contract import (
    attach_xau_readonly_surface_fields_v1,
    build_xau_readonly_surface_contract_v1,
    generate_and_write_xau_readonly_surface_summary_v1,
)
from backend.services.nas_readonly_surface_contract import (
    attach_nas_readonly_surface_fields_v1,
    build_nas_readonly_surface_contract_v1,
    generate_and_write_nas_readonly_surface_summary_v1,
)
from backend.services.btc_readonly_surface_contract import (
    attach_btc_readonly_surface_fields_v1,
    build_btc_readonly_surface_contract_v1,
    generate_and_write_btc_readonly_surface_summary_v1,
)
from backend.services.xau_decomposition_validation import (
    attach_xau_decomposition_validation_fields_v1,
    build_xau_decomposition_validation_contract_v1,
    generate_and_write_xau_decomposition_validation_summary_v1,
)
from backend.services.xau_refined_gate_timebox_audit import (
    attach_xau_refined_gate_timebox_audit_fields_v1,
    build_xau_refined_gate_timebox_audit_contract_v1,
    generate_and_write_xau_refined_gate_timebox_audit_summary_v1,
)
from backend.services.state_flow_f0_chain_alignment_audit import (
    attach_state_flow_f0_chain_alignment_fields_v1,
    build_state_flow_f0_chain_alignment_contract_v1,
    generate_and_write_state_flow_f0_chain_alignment_summary_v1,
)
from backend.services.flow_structure_gate_contract import (
    attach_flow_structure_gate_fields_v1,
    build_flow_structure_gate_contract_v1,
    generate_and_write_flow_structure_gate_summary_v1,
)
from backend.services.aggregate_directional_flow_metrics_contract import (
    attach_aggregate_directional_flow_metrics_fields_v1,
    build_aggregate_directional_flow_metrics_contract_v1,
    generate_and_write_aggregate_directional_flow_metrics_summary_v1,
)
from backend.services.retained_window_flow_calibration_contract import (
    attach_retained_window_flow_calibration_fields_v1,
    build_retained_window_flow_calibration_contract_v1,
    generate_and_write_retained_window_flow_calibration_summary_v1,
)
from backend.services.flow_threshold_provisional_band_contract import (
    attach_flow_threshold_provisional_band_fields_v1,
    build_flow_threshold_provisional_band_contract_v1,
    generate_and_write_flow_threshold_provisional_band_summary_v1,
)
from backend.services.exact_pilot_match_bonus_contract import (
    attach_exact_pilot_match_bonus_fields_v1,
    build_exact_pilot_match_bonus_contract_v1,
    generate_and_write_exact_pilot_match_bonus_summary_v1,
)
from backend.services.flow_support_state_contract import (
    attach_flow_support_state_fields_v1,
    build_flow_support_state_contract_v1,
    generate_and_write_flow_support_state_summary_v1,
)
from backend.services.flow_chain_shadow_comparison_contract import (
    attach_flow_chain_shadow_comparison_fields_v1,
    build_flow_chain_shadow_comparison_contract_v1,
    generate_and_write_flow_chain_shadow_comparison_summary_v1,
)
from backend.services.flow_candidate_improvement_review_contract import (
    attach_flow_candidate_improvement_review_fields_v1,
    build_flow_candidate_improvement_review_contract_v1,
    generate_and_write_flow_candidate_improvement_review_summary_v1,
)
from backend.services.nas_btc_hard_opposed_truth_audit import (
    attach_nas_btc_hard_opposed_truth_audit_fields_v1,
    build_nas_btc_hard_opposed_truth_audit_contract_v1,
    generate_and_write_nas_btc_hard_opposed_truth_audit_summary_v1,
)
from backend.services.bounded_calibration_candidate_contract import (
    attach_bounded_calibration_candidate_fields_v1,
    build_bounded_calibration_candidate_contract_v1,
    generate_and_write_bounded_calibration_candidate_summary_v1,
)
from backend.services.bounded_candidate_shadow_apply_contract import (
    attach_bounded_candidate_shadow_apply_fields_v1,
    build_bounded_candidate_shadow_apply_contract_v1,
    generate_and_write_bounded_candidate_shadow_apply_summary_v1,
)
from backend.services.bounded_candidate_evaluation_dashboard_contract import (
    attach_bounded_candidate_evaluation_dashboard_fields_v1,
    build_bounded_candidate_evaluation_dashboard_contract_v1,
    generate_and_write_bounded_candidate_evaluation_dashboard_summary_v1,
)
from backend.services.bounded_candidate_lifecycle_feedback_loop_contract import (
    attach_bounded_candidate_lifecycle_feedback_loop_fields_v1,
    build_bounded_candidate_lifecycle_feedback_loop_contract_v1,
    generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary_v1,
)
from backend.services.bounded_candidate_patch_memory_loop_contract import (
    attach_recent_rollback_memory_fields_v1,
    attach_bounded_candidate_patch_memory_loop_fields_v1,
    build_bounded_candidate_patch_memory_loop_contract_v1,
    generate_and_write_bounded_candidate_patch_memory_loop_summary_v1,
)
from backend.services.flow_shadow_display_surface import (
    attach_flow_shadow_display_surface_fields_v1,
    build_flow_shadow_display_surface_contract_v1,
    generate_and_write_flow_shadow_display_surface_summary_v1,
)
from backend.services.nas_decomposition_validation import (
    attach_nas_decomposition_validation_fields_v1,
    build_nas_decomposition_validation_contract_v1,
    generate_and_write_nas_decomposition_validation_summary_v1,
)
from backend.services.btc_decomposition_validation import (
    attach_btc_decomposition_validation_fields_v1,
    build_btc_decomposition_validation_contract_v1,
    generate_and_write_btc_decomposition_validation_summary_v1,
)
from backend.services.state_slot_commonization_judge import (
    build_state_slot_commonization_judge_contract_v1,
    generate_and_write_state_slot_commonization_judge_summary_v1,
)
from backend.services.state_slot_execution_interface_bridge import (
    attach_state_slot_execution_interface_bridge_fields_v1,
    build_state_slot_execution_interface_bridge_contract_v1,
    generate_and_write_state_slot_execution_interface_bridge_summary_v1,
)
from backend.services.state_slot_symbol_extension_surface import (
    attach_state_slot_symbol_extension_surface_fields_v1,
    build_state_slot_symbol_extension_surface_contract_v1,
    generate_and_write_state_slot_symbol_extension_surface_summary_v1,
)
from backend.services.state_slot_position_lifecycle_policy import (
    attach_state_slot_position_lifecycle_policy_fields_v1,
    build_state_slot_position_lifecycle_policy_contract_v1,
    generate_and_write_state_slot_position_lifecycle_policy_summary_v1,
)
from backend.services.execution_policy_shadow_audit import (
    attach_execution_policy_shadow_audit_fields_v1,
    build_execution_policy_shadow_audit_contract_v1,
    generate_and_write_execution_policy_shadow_audit_summary_v1,
)
from backend.services.bounded_lifecycle_canary import (
    attach_bounded_lifecycle_canary_fields_v1,
    build_bounded_lifecycle_canary_contract_v1,
    generate_and_write_bounded_lifecycle_canary_summary_v1,
)
from backend.services.state_strength_profile_contract import (
    attach_state_strength_profile_fields_v1,
    build_state_strength_profile_contract_v1,
    generate_and_write_state_strength_summary_v1,
)
from backend.services.local_structure_profile_contract import (
    attach_local_structure_profile_fields_v1,
    build_local_structure_profile_contract_v1,
    generate_and_write_local_structure_summary_v1,
)
from backend.services.runtime_readonly_surface import (
    attach_runtime_readonly_surface_fields_v1,
    build_runtime_readonly_surface_contract_v1,
    generate_and_write_runtime_readonly_surface_summary_v1,
)
from backend.services.state_structure_dominance_profile import (
    attach_state_structure_dominance_fields_v1,
    build_state_structure_dominance_contract_v1,
    generate_and_write_state_structure_dominance_summary_v1,
)
from backend.services.dominance_validation_profile import (
    attach_dominance_validation_fields_v1,
    build_dominance_validation_contract_v1,
    generate_and_write_dominance_validation_summary_v1,
)
from backend.services.dominance_accuracy_shadow import (
    attach_dominance_accuracy_shadow_fields_v1,
    build_dominance_accuracy_shadow_contract_v1,
    generate_and_write_dominance_accuracy_shadow_reports_v1,
)
from backend.services.symbol_specific_state_strength_calibration import (
    attach_symbol_specific_state_strength_calibration_fields_v1,
    build_symbol_specific_state_strength_calibration_contract_v1,
    generate_and_write_symbol_specific_state_strength_calibration_summary_v1,
)
from backend.services.strategy_service import StrategyService
from backend.app.trading_application_runner import run_trading_application
from backend.app.trading_application_reverse import try_reverse_entry as helper_try_reverse_entry
from backend.app.trading_application_reasoning import (
    build_scored_reasons as helper_build_scored_reasons,
    build_scored_reasons_raw as helper_build_scored_reasons_raw,
    entry_features as helper_entry_features,
    estimate_reason_points as helper_estimate_reason_points,
    exit_features as helper_exit_features,
    score_adjustment as helper_score_adjustment,
)

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

_MICRO_STRUCTURE_VERSION = "micro_structure_v1"
_MICRO_REQUIRED_BAR_COLUMNS = ("open", "high", "low", "close")
_MICRO_VOLUME_COLUMNS = ("real_volume", "tick_volume", "volume")
_MICRO_GAP_OPEN_KEYS = (
    "gap_anchor_open",
    "session_open",
    "session_open_price",
    "current_session_open",
    "day_open",
)
_MICRO_GAP_PREV_CLOSE_KEYS = (
    "gap_anchor_previous_close",
    "previous_session_close",
    "session_previous_close",
    "prev_session_close",
)


def _micro_to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _micro_clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _micro_safe_div(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    denom = abs(float(denominator))
    if denom <= 1e-9:
        return float(default)
    return float(numerator) / denom


def _micro_default_snapshot(
    *,
    lookback: int,
    baseline_lookback: int,
    data_state: str,
    anchor_state: str,
) -> dict:
    return {
        "version": _MICRO_STRUCTURE_VERSION,
        "lookback_bars": int(lookback),
        "baseline_lookback_bars": int(baseline_lookback),
        "window_size": 0,
        "data_state": str(data_state),
        "anchor_state": str(anchor_state),
        "body_size_pct_20": 0.0,
        "upper_wick_ratio_20": 0.0,
        "lower_wick_ratio_20": 0.0,
        "doji_ratio_20": 0.0,
        "same_color_run_current": 0,
        "same_color_run_max_20": 0,
        "bull_ratio_20": 0.0,
        "bear_ratio_20": 0.0,
        "direction_run_stats": {
            "current": 0,
            "max_20": 0,
            "bull_ratio_20": 0.0,
            "bear_ratio_20": 0.0,
        },
        "range_compression_ratio_20": 0.0,
        "volume_source": "none",
        "volume_burst_ratio_20": 0.0,
        "volume_burst_decay_20": 0.0,
        "swing_high_retest_count_20": 0,
        "swing_low_retest_count_20": 0,
        "gap_fill_progress": None,
    }


def _micro_series_sign(value: float) -> int:
    if value > 1e-9:
        return 1
    if value < -1e-9:
        return -1
    return 0


def _micro_run_stats(opens: pd.Series, closes: pd.Series) -> tuple[int, int, float, float]:
    signs = [_micro_series_sign(float(close) - float(open_)) for open_, close in zip(opens.tolist(), closes.tolist())]
    window_size = max(len(signs), 1)
    bull_ratio = sum(1 for sign in signs if sign > 0) / window_size
    bear_ratio = sum(1 for sign in signs if sign < 0) / window_size

    current_run = 0
    current_sign = signs[-1] if signs else 0
    if current_sign != 0:
        for sign in reversed(signs):
            if sign == current_sign:
                current_run += 1
            else:
                break

    max_run = 0
    active_sign = 0
    active_len = 0
    for sign in signs:
        if sign == 0:
            active_sign = 0
            active_len = 0
            continue
        if sign == active_sign:
            active_len += 1
        else:
            active_sign = sign
            active_len = 1
        max_run = max(max_run, active_len)

    return int(current_run), int(max_run), float(bull_ratio), float(bear_ratio)


def _micro_select_volume_series(df: pd.DataFrame) -> tuple[pd.Series, str]:
    for column in _MICRO_VOLUME_COLUMNS:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
        if float(series.abs().sum()) > 0.0:
            return series.astype(float), str(column)
    return pd.Series([0.0] * len(df), index=df.index, dtype=float), "none"


def _micro_retest_count(series: pd.Series, *, tolerance: float, high_side: bool) -> int:
    if series.empty:
        return 0
    pivot = float(series.max() if high_side else series.min())
    hits = int(sum(1 for value in series.tolist() if abs(float(value) - pivot) <= tolerance))
    return max(0, hits - 1)


def _micro_gap_fill_progress(*, current_price: float, gap_open: float, previous_close: float) -> tuple[float | None, str]:
    gap_size = float(gap_open) - float(previous_close)
    if abs(gap_size) <= 1e-9:
        return 1.0, "NO_GAP"
    if gap_size > 0.0:
        progress = _micro_safe_div(float(gap_open) - float(current_price), float(gap_open) - float(previous_close), default=0.0)
    else:
        progress = _micro_safe_div(float(current_price) - float(gap_open), float(previous_close) - float(gap_open), default=0.0)
    return _micro_clamp01(progress), "READY"


def _collect_owned_position_counts(positions, *, magic_number: int) -> tuple[dict[str, int], int, int]:
    counts_by_symbol: dict[str, int] = {}
    total_open_positions = 0
    owned_open_positions = 0
    for raw_position in list(positions or []):
        total_open_positions += 1
        try:
            magic = int(getattr(raw_position, "magic", 0) or 0)
        except Exception:
            magic = 0
        if magic != int(magic_number):
            continue
        owned_open_positions += 1
        symbol = str(getattr(raw_position, "symbol", "") or "").upper().strip()
        if symbol:
            counts_by_symbol[symbol] = int(counts_by_symbol.get(symbol, 0) or 0) + 1
    return counts_by_symbol, int(total_open_positions), int(owned_open_positions)


def _normalize_runtime_signal_position_counts(
    latest_signal_by_symbol: dict[str, dict] | None,
    *,
    positions,
    magic_number: int,
) -> tuple[dict[str, dict], dict[str, int], int, int]:
    counts_by_symbol, total_open_positions, owned_open_positions = _collect_owned_position_counts(
        positions,
        magic_number=int(magic_number),
    )
    normalized_rows: dict[str, dict] = {}
    for symbol, raw_row in dict(latest_signal_by_symbol or {}).items():
        if not isinstance(raw_row, dict):
            continue
        symbol_key = str(symbol or "").upper().strip()
        normalized_row = dict(raw_row)
        normalized_row["my_position_count"] = int(counts_by_symbol.get(symbol_key, 0) or 0)
        normalized_rows[str(symbol)] = normalized_row
    return normalized_rows, counts_by_symbol, total_open_positions, owned_open_positions


_RUNTIME_SIGNAL_DOWNSTREAM_DERIVED_PREFIXES = (
    "directional_continuation_accuracy_",
    "canonical_",
    "session_bias_",
    "state_strength_",
    "local_structure_",
    "few_candle_",
    "consumer_veto_",
    "runtime_readonly_surface_",
    "state_structure_dominance_",
    "dominance_",
    "symbol_specific_state_strength_",
    "symbol_state_strength_",
    "xau_",
    "nas_",
    "btc_",
    "state_slot_execution_interface_bridge_",
    "state_slot_symbol_extension_",
    "common_state_",
    "state_slot_position_lifecycle_policy_",
    "execution_policy_shadow_audit_",
    "bounded_lifecycle_canary_",
    "xau_refined_gate_timebox_audit_",
    "state_flow_f0_chain_alignment_",
    "flow_structure_gate_",
    "aggregate_",
    "retained_window_",
    "flow_threshold_",
    "provisional_flow_",
    "boosted_provisional_",
    "exact_pilot_match_",
    "pilot_match_bonus_",
    "flow_support_",
    "flow_chain_shadow_",
    "flow_candidate_",
    "nas_btc_hard_opposed_truth_audit_",
    "recent_rollback_memory_",
    "bounded_calibration_candidate_",
    "bounded_candidate_",
    "flow_shadow_",
    "flow_persistence_",
    "flow_min_",
)

_RUNTIME_SIGNAL_DOWNSTREAM_DERIVED_EXACT_KEYS = {
    "breakout_hold_quality_v1",
    "body_drive_state_v1",
    "local_continuation_discount_v1",
    "would_override_caution_v1",
    "common_vocabulary_compatibility_v1",
    "state_slot_bridge_state_v1",
    "bridge_source_slot_v1",
    "entry_bias_v1",
    "hold_bias_v1",
    "add_bias_v1",
    "reduce_bias_v1",
    "exit_bias_v1",
    "state_slot_execution_bridge_reason_summary_v1",
    "state_slot_lifecycle_policy_state_v1",
    "state_slot_execution_policy_source_v1",
    "entry_policy_v1",
    "hold_policy_v1",
    "add_policy_v1",
    "reduce_policy_v1",
    "exit_policy_v1",
    "state_slot_lifecycle_policy_reason_summary_v1",
    "lifecycle_policy_alignment_state_v1",
    "entry_delay_conflict_flag_v1",
    "hold_support_alignment_v1",
    "reduce_exit_pressure_alignment_v1",
    "execution_policy_shadow_error_type_v1",
    "execution_policy_shadow_reason_summary_v1",
}


def _reset_runtime_signal_downstream_derived_fields(
    rows_by_symbol: dict[str, dict] | None,
) -> dict[str, dict]:
    normalized_rows: dict[str, dict] = {}
    for symbol, raw_row in dict(rows_by_symbol or {}).items():
        if not isinstance(raw_row, dict):
            continue
        row = dict(raw_row)
        stale_keys = [
            str(key)
            for key in row.keys()
            if str(key) in _RUNTIME_SIGNAL_DOWNSTREAM_DERIVED_EXACT_KEYS
            or str(key).startswith(_RUNTIME_SIGNAL_DOWNSTREAM_DERIVED_PREFIXES)
        ]
        for key in stale_keys:
            row.pop(key, None)
        normalized_rows[str(symbol)] = row
    return normalized_rows


def _runtime_signal_wiring_audit_artifact_write_allowed(
    rows_by_symbol: dict[str, dict] | None,
    symbols,
) -> bool:
    expected_symbols: set[str] = set()
    if isinstance(symbols, dict):
        raw_symbols = symbols.values()
    else:
        raw_symbols = symbols or []
    for raw_symbol in list(raw_symbols or []):
        symbol = str(raw_symbol or "").upper().strip()
        if symbol:
            expected_symbols.add(symbol)
    present_symbols = {
        str(symbol or "").upper().strip()
        for symbol, row in dict(rows_by_symbol or {}).items()
        if str(symbol or "").strip() and isinstance(row, dict) and row
    }
    if not expected_symbols:
        return bool(present_symbols)
    return expected_symbols.issubset(present_symbols)


class TradingApplication:
    TIMEFRAMES = {
        "1M": TIMEFRAME_M1,
        "5M": TIMEFRAME_M5,
        "15M": TIMEFRAME_M15,
        "30M": TIMEFRAME_M30,
        "1H": TIMEFRAME_H1,
        "4H": TIMEFRAME_H4,
        "1D": TIMEFRAME_D1,
        "1W": TIMEFRAME_W1,
    }
    AI_MODEL_CHECK_INTERVAL_SEC = 30
    RUNTIME_RECENT_WINDOWS = (50, 200, 300)
    RUNTIME_RECENT_DEFAULT_WINDOW = 200
    RUNTIME_RECENT_BLOCKED_REASON_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_BLOCKED_REASON_LIMIT = 3
    RUNTIME_RECENT_WAIT_ENERGY_BRANCH_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_WAIT_ENERGY_BRANCH_LIMIT = 3
    RUNTIME_RECENT_WAIT_BIAS_SOURCE_LIMIT = 4
    RUNTIME_RECENT_SYMBOL_WAIT_BIAS_SOURCE_LIMIT = 3
    RUNTIME_RECENT_WAIT_POLICY_REASON_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_WAIT_POLICY_REASON_LIMIT = 3
    RUNTIME_RECENT_WAIT_SCENE_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_WAIT_SCENE_LIMIT = 3
    RUNTIME_RECENT_WAIT_REASON_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_WAIT_REASON_LIMIT = 3
    RUNTIME_RECENT_WAIT_STATE_DECISION_BRIDGE_LIMIT = 8
    RUNTIME_RECENT_SYMBOL_WAIT_STATE_DECISION_BRIDGE_LIMIT = 4
    RUNTIME_RECENT_EXIT_REASON_LIMIT = 5
    RUNTIME_RECENT_SYMBOL_EXIT_REASON_LIMIT = 3
    RUNTIME_RECENT_EXIT_BRIDGE_LIMIT = 8
    RUNTIME_RECENT_SYMBOL_EXIT_BRIDGE_LIMIT = 4
    RUNTIME_RECENT_STAGE_ORDER = ("READY", "PROBE", "OBSERVE", "BLOCKED", "NONE")
    RUNTIME_RECENT_WAIT_BIAS_SOURCE_ORDER = ("belief", "edge_pair", "state", "probe")
    RUNTIME_RECENT_REQUIRED_SIDE_ORDER = ("BUY", "SELL")

    def __init__(self, broker=None, notifier_client=None, observability=None):
        self.broker = broker or MT5BrokerAdapter()
        self.notifier = notifier_client or TelegramNotifierAdapter()
        self.observability = observability or FileObservabilityAdapter()
        self.last_entry_time = {}
        self.pending_reverse_by_symbol = {}
        self.runtime_reverse_alert_state_by_symbol = {}
        self.runtime_wait_alert_state_by_symbol = {}
        self.latest_regime_by_symbol = {}
        self.latest_signal_by_symbol = {}
        self._htf_trend_cache = HtfTrendCache(broker=self.broker)
        self._previous_box_calculator = PreviousBoxCalculator()
        self.project_root = Path(__file__).resolve().parents[2]
        self.ai_model_path = self.project_root / "models" / "ai_models.joblib"
        self.ai_model_mtime = None
        self.ai_last_check_at = 0.0
        self.ai_runtime = self._load_ai_runtime(self.ai_model_path) if bool(getattr(Config, "AI_RUNTIME_ENABLED", True)) else None
        self.semantic_model_dir = self.project_root / "models" / "semantic_v1"
        self.semantic_model_signature = tuple()
        self.semantic_last_check_at = 0.0
        self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
            state="not_checked",
            reason="not_checked",
            available_targets=(),
        )
        self.semantic_shadow_runtime = self._load_semantic_shadow_runtime(self.semantic_model_dir)
        if (
            self.semantic_shadow_runtime is None
            and str((self.semantic_shadow_runtime_diagnostics or {}).get("reason", "") or "") == "not_checked"
        ):
            self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                state="inactive",
                reason="runtime_unavailable",
                available_targets=(),
            )
        self.semantic_promotion_guard = SemanticPromotionGuard()
        self.semantic_rollout_manifest_path = (
            self.project_root
            / "data"
            / "manifests"
            / "rollout"
            / "semantic_live_rollout_latest.json"
        )
        self.semantic_rollout_state = {
            "contract_version": SEMANTIC_LIVE_ROLLOUT_VERSION,
            "entry": {
                "events_total": 0,
                "alerts_total": 0,
                "threshold_applied_total": 0,
                "fallback_total": 0,
                "partial_live_total": 0,
            },
            "exit": {
                "events_total": 0,
                "alerts_total": 0,
                "threshold_applied_total": 0,
                "fallback_total": 0,
                "partial_live_total": 0,
            },
            "recent": [],
        }
        self.runtime_status_path = self.project_root / "data" / "runtime_status.json"
        self.runtime_status_detail_path = resolve_runtime_status_detail_path(self.runtime_status_path)
        self.runtime_loop_debug_path = self.project_root / "data" / "runtime_loop_debug.json"
        self.entry_decision_log_path = self._resolve_project_path(
            getattr(Config, "ENTRY_DECISION_LOG_PATH", r"data\trades\entry_decisions.csv")
        )
        self.trade_history_csv_path = self._resolve_project_path(
            getattr(Config, "TRADE_HISTORY_CSV_PATH", r"data\trades\trade_history.csv")
        )
        self.last_order_ts = 0.0
        self.last_order_error = ""
        self.last_order_retcode = None
        self.last_order_comment = ""
        self.last_order_retcode_by_symbol = {}
        self.last_order_comment_by_symbol = {}
        self.order_block_until_by_symbol = {}
        self.order_block_reason_by_symbol = {}
        self.runtime_recycle_state = build_runtime_recycle_state(
            mode=getattr(Config, "RUNTIME_RECYCLE_MODE", "log_only"),
            interval_sec=int(getattr(Config, "RUNTIME_RECYCLE_INTERVAL_SEC", 3600) or 0),
            flat_grace_sec=int(getattr(Config, "RUNTIME_RECYCLE_FLAT_GRACE_SEC", 30) or 0),
            post_order_grace_sec=int(getattr(Config, "RUNTIME_RECYCLE_POST_ORDER_GRACE_SEC", 90) or 0),
        )
        self.runtime_recent_summary_cache = {}
        self.runtime_recent_default_window_cache = {}
        self.runtime_recycle_health_state = build_runtime_recycle_health_v1(
            recent_runtime_summary={},
            default_recent_window={},
            latest_signal_by_symbol={},
            signal_stale_sec=int(getattr(Config, "RUNTIME_RECYCLE_SIGNAL_STALE_SEC", 900) or 900),
        )
        self.runtime_recycle_drift_state = build_runtime_recycle_drift_v1(
            recent_runtime_summary={},
            default_recent_window={},
            latest_signal_by_symbol={},
            min_rows=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_MIN_ROWS", 40) or 40),
            stage_dominance_threshold=float(getattr(Config, "RUNTIME_RECYCLE_DRIFT_STAGE_DOMINANCE", 0.85) or 0.85),
            block_dominance_threshold=float(getattr(Config, "RUNTIME_RECYCLE_DRIFT_BLOCK_DOMINANCE", 0.85) or 0.85),
            decision_dominance_threshold=float(getattr(Config, "RUNTIME_RECYCLE_DRIFT_DECISION_DOMINANCE", 0.90) or 0.90),
            min_signal_count=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_SIGNAL_MIN_COUNT", 2) or 2),
        )
        self.state25_active_candidate_state_path = (
            self.project_root
            / "models"
            / "teacher_pattern_state25_candidates"
            / "active_candidate_state.json"
        )
        self.state25_candidate_runtime_state = load_state25_candidate_runtime_state(
            self.state25_active_candidate_state_path
        )
        self.ai_entry_traces = []
        self.directional_continuation_accuracy_report_v1 = {}
        self.runtime_signal_wiring_audit_report_v1 = {}
        self.ca2_session_split_report_v1 = {}
        self.should_have_done_candidate_report_v1 = {}
        self.canonical_surface_report_v1 = {}
        self.session_aware_annotation_accuracy_report_v1 = {}
        self.session_bias_shadow_report_v1 = {}
        self.symbol_specific_state_strength_calibration_report_v1 = {}
        self.state_flow_f0_chain_alignment_report_v1 = {}
        self.flow_structure_gate_report_v1 = {}
        self.aggregate_directional_flow_metrics_report_v1 = {}
        self.retained_window_flow_calibration_report_v1 = {}
        self.flow_threshold_provisional_band_report_v1 = {}
        self.exact_pilot_match_bonus_report_v1 = {}
        self.flow_support_state_report_v1 = {}
        self.flow_chain_shadow_comparison_report_v1 = {}
        self.flow_candidate_improvement_review_report_v1 = {}
        self.nas_btc_hard_opposed_truth_audit_report_v1 = {}
        self.bounded_calibration_candidate_report_v1 = {}
        self.bounded_candidate_shadow_apply_report_v1 = {}
        self.bounded_candidate_evaluation_dashboard_report_v1 = {}
        self.bounded_candidate_lifecycle_feedback_loop_report_v1 = {}
        self.bounded_candidate_patch_memory_loop_report_v1 = {}
        self.flow_shadow_display_surface_report_v1 = {}
        self.directional_continuation_candidates_cache_v1 = []
        self.loop_debug_state = {}
        if self.ai_runtime and self.ai_model_path.exists():
            self.ai_model_mtime = self.ai_model_path.stat().st_mtime
        self.semantic_model_signature = self._semantic_model_signature(self.semantic_model_dir)

    def notify(self, message: str):
        self.notifier.send(message)

    def notify_shutdown(self):
        self.notifier.shutdown()

    def _obs_inc(self, name: str, amount: int = 1):
        try:
            self.observability.incr(name, amount)
        except Exception:
            return

    def _obs_event(self, name: str, level: str = "info", payload: dict | None = None):
        try:
            self.observability.event(name, level=level, payload=payload)
        except Exception:
            return

    def format_entry_message(self, symbol, action, score, price, lot, reasons, pos_count, max_pos, row: dict | None = None):
        return self.notifier.format_entry_message(
            symbol,
            action,
            score,
            price,
            lot,
            reasons,
            pos_count,
            max_pos,
            row=row,
        )

    def format_exit_message(
        self,
        symbol,
        profit,
        points,
        entry_price,
        exit_price,
        exit_reason: str | None = None,
        review_context: dict | None = None,
    ):
        return self.notifier.format_exit_message(
            symbol,
            profit,
            points,
            entry_price,
            exit_price,
            exit_reason=exit_reason,
            review_context=review_context,
        )

    def format_wait_message(
        self,
        symbol,
        action,
        price,
        pos_count,
        max_pos,
        reason: str | None = None,
        row: dict | None = None,
    ):
        return self.notifier.format_wait_message(
            symbol,
            action,
            price,
            pos_count,
            max_pos,
            reason=reason,
            row=row,
        )

    def build_wait_message_signature(
        self,
        symbol,
        action,
        reason: str | None = None,
        row: dict | None = None,
    ) -> str:
        return self.notifier.build_wait_message_signature(
            symbol,
            action,
            reason=reason,
            row=row,
        )

    def format_reverse_message(
        self,
        symbol,
        action,
        score,
        price,
        reasons,
        pos_count,
        max_pos,
        pending: bool = False,
        row: dict | None = None,
    ):
        return self.notifier.format_reverse_message(
            symbol,
            action,
            score,
            price,
            reasons,
            pos_count,
            max_pos,
            pending=pending,
            row=row,
        )

    def build_reverse_message_signature(
        self,
        symbol,
        action,
        score,
        reasons,
        pending: bool = False,
    ) -> str:
        return self.notifier.build_reverse_message_signature(
            symbol,
            action,
            score,
            reasons,
            pending=pending,
        )

    def should_notify_wait_message(self, symbol: str, signature: str) -> bool:
        signature_text = str(signature or "").strip()
        if not signature_text:
            return False
        now_ts = float(time.time())
        cooldown_sec = float(getattr(Config, "RUNTIME_WAIT_ALERT_COOLDOWN_SEC", 180.0) or 180.0)
        symbol_key = str(symbol or "").upper().strip()
        state = {}
        if isinstance(self.runtime_wait_alert_state_by_symbol, dict):
            state = dict(self.runtime_wait_alert_state_by_symbol.get(symbol_key, {}) or {})
        last_signature = str(state.get("signature", "") or "")
        last_sent_ts = float(state.get("last_sent_ts", 0.0) or 0.0)
        if last_signature == signature_text and (now_ts - last_sent_ts) < cooldown_sec:
            return False
        if not isinstance(self.runtime_wait_alert_state_by_symbol, dict):
            self.runtime_wait_alert_state_by_symbol = {}
        self.runtime_wait_alert_state_by_symbol[symbol_key] = {
            "signature": signature_text,
            "last_sent_ts": float(now_ts),
        }
        return True

    def should_notify_reverse_message(self, symbol: str, signature: str) -> bool:
        signature_text = str(signature or "").strip()
        if not signature_text:
            return False
        now_ts = float(time.time())
        cooldown_sec = float(getattr(Config, "RUNTIME_REVERSE_ALERT_COOLDOWN_SEC", 120.0) or 120.0)
        symbol_key = str(symbol or "").upper().strip()
        state = {}
        if isinstance(self.runtime_reverse_alert_state_by_symbol, dict):
            state = dict(self.runtime_reverse_alert_state_by_symbol.get(symbol_key, {}) or {})
        last_signature = str(state.get("signature", "") or "")
        last_sent_ts = float(state.get("last_sent_ts", 0.0) or 0.0)
        if last_signature == signature_text and (now_ts - last_sent_ts) < cooldown_sec:
            return False
        if not isinstance(self.runtime_reverse_alert_state_by_symbol, dict):
            self.runtime_reverse_alert_state_by_symbol = {}
        self.runtime_reverse_alert_state_by_symbol[symbol_key] = {
            "signature": signature_text,
            "last_sent_ts": float(now_ts),
        }
        return True

    def _append_ai_entry_trace(self, trace: dict):
        try:
            if not isinstance(trace, dict):
                return
            trace = self._normalize_execution_diff_surface_fields(trace)
            nested_execution_diff = trace.get("execution_action_diff_v1")
            if not isinstance(nested_execution_diff, dict):
                original_side = str(trace.get("execution_diff_original_action_side", "") or "").strip().upper()
                guarded_side = str(trace.get("execution_diff_guarded_action_side", "") or "").strip().upper()
                promoted_side = str(trace.get("execution_diff_promoted_action_side", "") or "").strip().upper()
                final_side = str(trace.get("execution_diff_final_action_side", "") or "").strip().upper()
                changed = bool(trace.get("execution_diff_changed", False))
                if any((original_side, guarded_side, promoted_side, final_side, changed)):
                    if not original_side:
                        original_side = "NONE"
                    if not guarded_side:
                        guarded_side = "SKIP" if bool(trace.get("execution_diff_guard_applied", False)) else original_side
                    if not promoted_side:
                        promoted_side = "NONE"
                    if not final_side:
                        final_side = "SKIP" if changed else "NONE"
                    nested_execution_diff = {
                        "contract_version": "execution_action_diff_v1",
                        "original_action_side": original_side,
                        "guarded_action_side": guarded_side,
                        "promoted_action_side": promoted_side,
                        "final_action_side": final_side,
                        "action_changed": changed,
                        "guard_applied": bool(trace.get("execution_diff_guard_applied", False)),
                        "promotion_active": bool(trace.get("execution_diff_promotion_active", False)),
                        "action_change_reason_keys": list(trace.get("execution_diff_reason_keys", []) or []),
                    }
                    trace["execution_action_diff_v1"] = dict(nested_execution_diff)
                    trace = self._normalize_execution_diff_surface_fields(trace)
            row = {
                "time": datetime.now(KST).isoformat(timespec="seconds"),
                "symbol": str(trace.get("symbol", "")),
                "action": str(trace.get("action", "")),
                "raw_score": float(trace.get("raw_score", 0.0) or 0.0),
                "contra_score": float(trace.get("contra_score", 0.0) or 0.0),
                "probability": (
                    None if trace.get("probability") is None else float(trace.get("probability"))
                ),
                "score_adj": int(trace.get("score_adj", 0) or 0),
                "final_score": float(trace.get("final_score", 0.0) or 0.0),
                "threshold": float(trace.get("threshold", 0.0) or 0.0),
                "blocked": bool(trace.get("blocked", False)),
                "regime": str(trace.get("regime", "")),
                "volume_ratio": (
                    None if trace.get("volume_ratio") is None else float(trace.get("volume_ratio"))
                ),
                "volatility_ratio": (
                    None
                    if trace.get("volatility_ratio") is None
                    else float(trace.get("volatility_ratio"))
                ),
                "spread_ratio": (
                    None if trace.get("spread_ratio") is None else float(trace.get("spread_ratio"))
                ),
                "buy_multiplier": (
                    None if trace.get("buy_multiplier") is None else float(trace.get("buy_multiplier"))
                ),
                "sell_multiplier": (
                    None if trace.get("sell_multiplier") is None else float(trace.get("sell_multiplier"))
                ),
                "effective_entry_threshold": (
                    None if trace.get("effective_entry_threshold") is None else float(trace.get("effective_entry_threshold"))
                ),
                "base_entry_threshold": (
                    None if trace.get("base_entry_threshold") is None else float(trace.get("base_entry_threshold"))
                ),
                "blocked_by": str(trace.get("blocked_by", "")),
                "entry_stage": str(trace.get("entry_stage", "")),
                "entry_quality": (
                    None if trace.get("entry_quality") is None else float(trace.get("entry_quality"))
                ),
                "execution_diff_original_action_side": str(
                    trace.get("execution_diff_original_action_side", "")
                ),
                "execution_diff_guarded_action_side": str(
                    trace.get("execution_diff_guarded_action_side", "")
                ),
                "execution_diff_promoted_action_side": str(
                    trace.get("execution_diff_promoted_action_side", "")
                ),
                "execution_diff_final_action_side": str(
                    trace.get("execution_diff_final_action_side", "")
                ),
                "execution_diff_changed": bool(trace.get("execution_diff_changed", False)),
                "execution_diff_guard_applied": bool(
                    trace.get("execution_diff_guard_applied", False)
                ),
                "execution_diff_promotion_active": bool(
                    trace.get("execution_diff_promotion_active", False)
                ),
                "execution_diff_reason_keys": list(
                    trace.get("execution_diff_reason_keys", []) or []
                ),
                "execution_diff_guard_reason_summary": str(
                    trace.get("execution_diff_guard_reason_summary", "")
                ),
                "execution_diff_promotion_reason": str(
                    trace.get("execution_diff_promotion_reason", "")
                ),
                "execution_diff_promotion_suppressed_reason": str(
                    trace.get("execution_diff_promotion_suppressed_reason", "")
                ),
            }
            if isinstance(trace.get("execution_action_diff_v1"), dict) and trace.get("execution_action_diff_v1"):
                row["execution_action_diff_v1"] = dict(trace.get("execution_action_diff_v1", {}) or {})
            self.ai_entry_traces.append(row)
            if len(self.ai_entry_traces) > 80:
                self.ai_entry_traces = self.ai_entry_traces[-80:]
        except Exception:
            pass

    def _export_pending_reverse_by_symbol(self) -> dict[str, dict]:
        exported: dict[str, dict] = {}
        store = getattr(self, "pending_reverse_by_symbol", {})
        if not isinstance(store, dict):
            return exported
        now_ts = float(time.time())
        for raw_symbol, raw_payload in store.items():
            payload = dict(raw_payload or {}) if isinstance(raw_payload, dict) else {}
            symbol = str(raw_symbol or "").upper().strip()
            action = str(payload.get("action", "") or "").upper().strip()
            if not symbol or action not in {"BUY", "SELL"}:
                continue
            created_at = float(payload.get("created_at", 0.0) or 0.0)
            expires_at = float(payload.get("expires_at", 0.0) or 0.0)
            reasons = [
                str(reason).strip()
                for reason in list(payload.get("reasons", []) or [])
                if str(reason).strip()
            ]
            exported[symbol] = {
                "action": action,
                "score": float(payload.get("score", 0.0) or 0.0),
                "reasons": reasons[:3],
                "reason_count": len(reasons),
                "age_sec": max(0, int(now_ts - created_at)) if created_at > 0.0 else 0,
                "expires_in_sec": max(0, int(expires_at - now_ts)) if expires_at > 0.0 else 0,
            }
        return exported

    # Public bridge for services to avoid depending on private methods.
    def append_ai_entry_trace(self, trace: dict):
        self._append_ai_entry_trace(trace)

    @staticmethod
    def _load_ai_runtime(model_path: Path):
        if not bool(getattr(Config, "AI_RUNTIME_ENABLED", True)):
            logger.info("AI runtime disabled by config; skipping model load: %s", model_path)
            return None
        if not model_path.exists():
            logger.info("AI model not found: %s", model_path)
            return None
        try:
            runtime = AIModelRuntime(model_path)
            logger.info("AI model loaded: %s", model_path)
            return runtime
        except Exception as exc:
            logger.exception("Failed to load AI model: %s", exc)
            return None

    @staticmethod
    def _semantic_model_signature(model_dir: Path) -> tuple[tuple[str, int], ...]:
        if not model_dir.exists():
            return tuple()
        items: list[tuple[str, int]] = []
        for path in sorted(model_dir.glob("*_model.joblib")):
            try:
                items.append((path.name, int(path.stat().st_mtime_ns)))
            except OSError:
                continue
        return tuple(items)

    @classmethod
    def _resolve_project_path(cls, path_value: str | Path) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path

    @staticmethod
    def _runtime_now_iso() -> str:
        return datetime.now(KST).isoformat(timespec="seconds")

    def _build_semantic_shadow_runtime_diagnostics(
        self,
        *,
        state: str,
        reason: str,
        available_targets: tuple[str, ...] | list[str] | None = None,
        error: str = "",
    ) -> dict[str, object]:
        return {
            "contract_version": "semantic_shadow_runtime_diagnostics_v1",
            "checked_at": self._runtime_now_iso(),
            "state": str(state or "unknown"),
            "reason": str(reason or "unknown"),
            "model_dir": str(self.semantic_model_dir),
            "model_dir_exists": bool(self.semantic_model_dir.exists()),
            "available_targets": list(available_targets or ()),
            "error": str(error or ""),
        }

    @staticmethod
    def _csv_bool(value: object) -> bool:
        text = str(value or "").strip().lower()
        return text in {"1", "true", "yes", "y", "on"}

    @classmethod
    def _csv_json_dict(cls, value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return dict(value)
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            loaded = json.loads(text)
        except Exception:
            return {}
        return dict(loaded) if isinstance(loaded, dict) else {}

    @staticmethod
    def _trace_branch_names(trace_payload: dict[str, object]) -> list[str]:
        branch_records = trace_payload.get("branch_records", [])
        if not isinstance(branch_records, list):
            return []
        names: list[str] = []
        for record in branch_records:
            if not isinstance(record, dict):
                continue
            branch = str(record.get("branch", "") or "").strip()
            if branch:
                names.append(branch)
        return names

    @classmethod
    def _empty_wait_energy_trace_bucket(cls) -> dict[str, object]:
        return {
            "trace_present_rows": 0,
            "trace_branch_rows": 0,
            "usage_source_counter": Counter(),
            "usage_mode_counter": Counter(),
            "branch_counter": Counter(),
        }

    @classmethod
    def _accumulate_wait_energy_trace_bucket(
        cls,
        bucket: dict[str, object],
        trace_payload: dict[str, object],
    ) -> None:
        trace_payload = dict(trace_payload or {})
        if not trace_payload:
            return
        bucket["trace_present_rows"] = int(bucket.get("trace_present_rows", 0) or 0) + 1
        usage_source = str(trace_payload.get("usage_source", "") or "").strip().lower()
        usage_mode = str(trace_payload.get("usage_mode", "") or "").strip().lower()
        if usage_source:
            bucket["usage_source_counter"][usage_source] += 1
        if usage_mode:
            bucket["usage_mode_counter"][usage_mode] += 1
        branch_names = cls._trace_branch_names(trace_payload)
        if branch_names:
            bucket["trace_branch_rows"] = int(bucket.get("trace_branch_rows", 0) or 0) + 1
            for branch_name in branch_names:
                bucket["branch_counter"][branch_name] += 1

    @classmethod
    def _build_wait_energy_trace_bucket_summary(
        cls,
        bucket: dict[str, object],
        *,
        branch_limit: int,
    ) -> dict[str, object]:
        return {
            "trace_present_rows": int(bucket.get("trace_present_rows", 0) or 0),
            "trace_branch_rows": int(bucket.get("trace_branch_rows", 0) or 0),
            "usage_source_counts": cls._ordered_count_map(bucket.get("usage_source_counter", Counter())),
            "usage_mode_counts": cls._ordered_count_map(bucket.get("usage_mode_counter", Counter())),
            "branch_counts": cls._ordered_count_map(
                bucket.get("branch_counter", Counter()),
                limit=branch_limit,
            ),
        }

    @classmethod
    def _build_wait_energy_trace_summary(
        cls,
        state_bucket: dict[str, object],
        decision_bucket: dict[str, object],
        *,
        branch_limit: int,
    ) -> dict[str, object]:
        return {
            "entry_wait_state_trace": cls._build_wait_energy_trace_bucket_summary(
                state_bucket,
                branch_limit=branch_limit,
            ),
            "entry_wait_decision_trace": cls._build_wait_energy_trace_bucket_summary(
                decision_bucket,
                branch_limit=branch_limit,
            ),
        }

    @staticmethod
    def _summary_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _summary_str_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                items.append(text)
        return items

    @classmethod
    def _resolve_wait_context_surface(cls, row: dict[str, object]) -> dict[str, object]:
        return dict(row.get("entry_wait_context_v1", {}) or {})

    @classmethod
    def _resolve_wait_bias_bundle_surface(
        cls,
        row: dict[str, object],
        wait_context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        bundle = dict(row.get("entry_wait_bias_bundle_v1", {}) or {})
        if bundle:
            return bundle
        wait_context = dict(wait_context or {})
        return dict(dict(wait_context.get("bias", {}) or {}).get("bundle", {}) or {})

    @classmethod
    def _resolve_wait_state_policy_input_surface(
        cls,
        row: dict[str, object],
        wait_context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        policy_input = dict(row.get("entry_wait_state_policy_input_v1", {}) or {})
        if policy_input:
            return policy_input
        wait_context = dict(wait_context or {})
        return dict(dict(wait_context.get("policy", {}) or {}).get("entry_wait_state_policy_input_v1", {}) or {})

    @classmethod
    def _empty_wait_bias_bundle_bucket(cls) -> dict[str, object]:
        return {
            "active_release_source_counter": Counter(),
            "active_wait_lock_source_counter": Counter(),
            "release_bias_count_counter": Counter(),
            "wait_lock_bias_count_counter": Counter(),
        }

    @classmethod
    def _accumulate_wait_bias_bundle_bucket(
        cls,
        bucket: dict[str, object],
        bundle_summary: dict[str, object],
    ) -> None:
        bundle_summary = dict(bundle_summary or {})
        if not bundle_summary:
            return
        release_sources = cls._summary_str_list(bundle_summary.get("active_release_sources", []))
        wait_lock_sources = cls._summary_str_list(bundle_summary.get("active_wait_lock_sources", []))
        for source in release_sources:
            bucket["active_release_source_counter"][source] += 1
        for source in wait_lock_sources:
            bucket["active_wait_lock_source_counter"][source] += 1
        bucket["release_bias_count_counter"][len(release_sources)] += 1
        bucket["wait_lock_bias_count_counter"][len(wait_lock_sources)] += 1

    @classmethod
    def _build_wait_bias_bundle_summary(
        cls,
        bucket: dict[str, object],
        *,
        source_limit: int,
    ) -> dict[str, object]:
        return {
            "active_release_source_counts": cls._ordered_count_map(
                bucket.get("active_release_source_counter", Counter()),
                limit=source_limit,
                preferred_order=cls.RUNTIME_RECENT_WAIT_BIAS_SOURCE_ORDER,
            ),
            "active_wait_lock_source_counts": cls._ordered_count_map(
                bucket.get("active_wait_lock_source_counter", Counter()),
                limit=source_limit,
                preferred_order=cls.RUNTIME_RECENT_WAIT_BIAS_SOURCE_ORDER,
            ),
            "release_bias_count_distribution": cls._ordered_count_map(
                bucket.get("release_bias_count_counter", Counter()),
            ),
            "wait_lock_bias_count_distribution": cls._ordered_count_map(
                bucket.get("wait_lock_bias_count_counter", Counter()),
            ),
        }

    @classmethod
    def _empty_wait_state_policy_surface_bucket(cls) -> dict[str, object]:
        return {
            "policy_state_counter": Counter(),
            "policy_reason_counter": Counter(),
            "required_side_counter": Counter(),
            "policy_hard_block_active_rows": 0,
            "policy_suppressed_rows": 0,
            "helper_soft_block_rows": 0,
            "helper_wait_hint_rows": 0,
        }

    @classmethod
    def _accumulate_wait_state_policy_surface_bucket(
        cls,
        bucket: dict[str, object],
        wait_context: dict[str, object],
        policy_input: dict[str, object],
    ) -> None:
        wait_context = dict(wait_context or {})
        policy_input = dict(policy_input or {})
        policy_surface = dict(wait_context.get("policy", {}) or {})
        state = str(policy_surface.get("state", "") or "").strip().upper()
        reason = str(policy_surface.get("reason", "") or "").strip()
        if state:
            bucket["policy_state_counter"][state] += 1
        if reason:
            bucket["policy_reason_counter"][reason] += 1

        identity = dict(policy_input.get("identity", {}) or {})
        helper_hints = dict(policy_input.get("helper_hints", {}) or {})
        required_side = str(identity.get("required_side", "") or "").strip().upper()
        if required_side:
            bucket["required_side_counter"][required_side] += 1
        if bool(helper_hints.get("policy_hard_block_active", False)):
            bucket["policy_hard_block_active_rows"] = int(
                bucket.get("policy_hard_block_active_rows", 0) or 0
            ) + 1
        if bool(helper_hints.get("policy_suppressed", False)):
            bucket["policy_suppressed_rows"] = int(bucket.get("policy_suppressed_rows", 0) or 0) + 1
        if bool(helper_hints.get("soft_block_active", False)):
            bucket["helper_soft_block_rows"] = int(bucket.get("helper_soft_block_rows", 0) or 0) + 1
        if str(helper_hints.get("wait_vs_enter_hint", "") or "").strip():
            bucket["helper_wait_hint_rows"] = int(bucket.get("helper_wait_hint_rows", 0) or 0) + 1

    @classmethod
    def _build_wait_state_policy_surface_summary(
        cls,
        bucket: dict[str, object],
        *,
        reason_limit: int,
    ) -> dict[str, object]:
        return {
            "policy_state_counts": cls._ordered_count_map(bucket.get("policy_state_counter", Counter())),
            "policy_reason_counts": cls._ordered_count_map(
                bucket.get("policy_reason_counter", Counter()),
                limit=reason_limit,
            ),
            "required_side_counts": cls._ordered_count_map(
                bucket.get("required_side_counter", Counter()),
                preferred_order=cls.RUNTIME_RECENT_REQUIRED_SIDE_ORDER,
            ),
            "policy_hard_block_active_rows": int(bucket.get("policy_hard_block_active_rows", 0) or 0),
            "policy_suppressed_rows": int(bucket.get("policy_suppressed_rows", 0) or 0),
            "helper_soft_block_rows": int(bucket.get("helper_soft_block_rows", 0) or 0),
            "helper_wait_hint_rows": int(bucket.get("helper_wait_hint_rows", 0) or 0),
        }

    @classmethod
    def _empty_wait_special_scene_bucket(cls) -> dict[str, object]:
        return {
            "probe_scene_counter": Counter(),
            "xau_second_support_probe_relief_rows": 0,
            "btc_lower_strong_score_soft_wait_candidate_rows": 0,
            "probe_ready_for_entry_rows": 0,
        }

    @classmethod
    def _accumulate_wait_special_scene_bucket(
        cls,
        bucket: dict[str, object],
        policy_input: dict[str, object],
    ) -> None:
        policy_input = dict(policy_input or {})
        special_scenes = dict(policy_input.get("special_scenes", {}) or {})
        probe_scene_id = str(special_scenes.get("probe_scene_id", "") or "").strip()
        if probe_scene_id:
            bucket["probe_scene_counter"][probe_scene_id] += 1
        if bool(special_scenes.get("xau_second_support_probe_relief", False)):
            bucket["xau_second_support_probe_relief_rows"] = int(
                bucket.get("xau_second_support_probe_relief_rows", 0) or 0
            ) + 1
        if bool(special_scenes.get("btc_lower_strong_score_soft_wait_candidate", False)):
            bucket["btc_lower_strong_score_soft_wait_candidate_rows"] = int(
                bucket.get("btc_lower_strong_score_soft_wait_candidate_rows", 0) or 0
            ) + 1
        if bool(special_scenes.get("probe_ready_for_entry", False)):
            bucket["probe_ready_for_entry_rows"] = int(bucket.get("probe_ready_for_entry_rows", 0) or 0) + 1

    @classmethod
    def _build_wait_special_scene_summary(
        cls,
        bucket: dict[str, object],
        *,
        scene_limit: int,
    ) -> dict[str, object]:
        return {
            "probe_scene_counts": cls._ordered_count_map(
                bucket.get("probe_scene_counter", Counter()),
                limit=scene_limit,
            ),
            "xau_second_support_probe_relief_rows": int(
                bucket.get("xau_second_support_probe_relief_rows", 0) or 0
            ),
            "btc_lower_strong_score_soft_wait_candidate_rows": int(
                bucket.get("btc_lower_strong_score_soft_wait_candidate_rows", 0) or 0
            ),
            "probe_ready_for_entry_rows": int(bucket.get("probe_ready_for_entry_rows", 0) or 0),
        }

    @classmethod
    def _empty_wait_threshold_shift_bucket(cls) -> dict[str, object]:
        return {
            "soft_shift_total": 0.0,
            "hard_shift_total": 0.0,
            "threshold_rows": 0,
            "soft_threshold_shift_up_rows": 0,
            "soft_threshold_shift_down_rows": 0,
            "hard_threshold_shift_up_rows": 0,
            "hard_threshold_shift_down_rows": 0,
        }

    @classmethod
    def _accumulate_wait_threshold_shift_bucket(
        cls,
        bucket: dict[str, object],
        bundle_summary: dict[str, object],
        policy_input: dict[str, object],
    ) -> None:
        bundle_summary = dict(bundle_summary or {})
        policy_input = dict(policy_input or {})
        threshold_adjustment = dict(bundle_summary.get("threshold_adjustment", {}) or {})
        thresholds = dict(policy_input.get("thresholds", {}) or {})
        if not threshold_adjustment and not thresholds:
            return
        base_soft = cls._summary_float(
            threshold_adjustment.get("base_soft_threshold", thresholds.get("base_soft_threshold", 0.0)),
            0.0,
        )
        base_hard = cls._summary_float(
            threshold_adjustment.get("base_hard_threshold", thresholds.get("base_hard_threshold", 0.0)),
            0.0,
        )
        effective_soft = cls._summary_float(
            threshold_adjustment.get("effective_soft_threshold", thresholds.get("effective_soft_threshold", 0.0)),
            0.0,
        )
        effective_hard = cls._summary_float(
            threshold_adjustment.get("effective_hard_threshold", thresholds.get("effective_hard_threshold", 0.0)),
            0.0,
        )
        soft_shift = float(effective_soft - base_soft)
        hard_shift = float(effective_hard - base_hard)
        bucket["threshold_rows"] = int(bucket.get("threshold_rows", 0) or 0) + 1
        bucket["soft_shift_total"] = float(bucket.get("soft_shift_total", 0.0) or 0.0) + soft_shift
        bucket["hard_shift_total"] = float(bucket.get("hard_shift_total", 0.0) or 0.0) + hard_shift
        if soft_shift > 0:
            bucket["soft_threshold_shift_up_rows"] = int(bucket.get("soft_threshold_shift_up_rows", 0) or 0) + 1
        elif soft_shift < 0:
            bucket["soft_threshold_shift_down_rows"] = int(
                bucket.get("soft_threshold_shift_down_rows", 0) or 0
            ) + 1
        if hard_shift > 0:
            bucket["hard_threshold_shift_up_rows"] = int(bucket.get("hard_threshold_shift_up_rows", 0) or 0) + 1
        elif hard_shift < 0:
            bucket["hard_threshold_shift_down_rows"] = int(
                bucket.get("hard_threshold_shift_down_rows", 0) or 0
            ) + 1

    @classmethod
    def _build_wait_threshold_shift_summary(cls, bucket: dict[str, object]) -> dict[str, object]:
        threshold_rows = int(bucket.get("threshold_rows", 0) or 0)
        soft_shift_total = float(bucket.get("soft_shift_total", 0.0) or 0.0)
        hard_shift_total = float(bucket.get("hard_shift_total", 0.0) or 0.0)
        return {
            "soft_threshold_shift_avg": round(soft_shift_total / threshold_rows, 6) if threshold_rows > 0 else 0.0,
            "hard_threshold_shift_avg": round(hard_shift_total / threshold_rows, 6) if threshold_rows > 0 else 0.0,
            "soft_threshold_shift_up_rows": int(bucket.get("soft_threshold_shift_up_rows", 0) or 0),
            "soft_threshold_shift_down_rows": int(bucket.get("soft_threshold_shift_down_rows", 0) or 0),
            "hard_threshold_shift_up_rows": int(bucket.get("hard_threshold_shift_up_rows", 0) or 0),
            "hard_threshold_shift_down_rows": int(bucket.get("hard_threshold_shift_down_rows", 0) or 0),
        }

    @classmethod
    def _row_has_wait_semantic(cls, row: dict[str, object]) -> bool:
        return bool(
            str(row.get("entry_wait_state", "") or "").strip()
            or str(row.get("entry_wait_reason", "") or "").strip()
            or str(row.get("entry_wait_decision", "") or "").strip()
            or bool(row.get("entry_wait_selected", False))
            or bool(row.get("entry_wait_hard", False))
        )

    @classmethod
    def _empty_wait_state_semantic_bucket(cls) -> dict[str, object]:
        return {
            "row_count": 0,
            "wait_state_counter": Counter(),
            "hard_wait_state_counter": Counter(),
            "wait_reason_counter": Counter(),
            "hard_wait_true_rows": 0,
        }

    @classmethod
    def _accumulate_wait_state_semantic_bucket(
        cls,
        bucket: dict[str, object],
        *,
        wait_state: str,
        wait_hard: bool,
        wait_reason: str,
    ) -> None:
        state = str(wait_state or "NONE").strip().upper() or "NONE"
        reason = str(wait_reason or "").strip()
        bucket["row_count"] = int(bucket.get("row_count", 0) or 0) + 1
        bucket["wait_state_counter"][state] += 1
        if reason:
            bucket["wait_reason_counter"][reason] += 1
        if bool(wait_hard):
            bucket["hard_wait_state_counter"][state] += 1
            bucket["hard_wait_true_rows"] = int(bucket.get("hard_wait_true_rows", 0) or 0) + 1

    @classmethod
    def _build_wait_state_semantic_summary(
        cls,
        bucket: dict[str, object],
        *,
        reason_limit: int,
    ) -> dict[str, object]:
        return {
            "row_count": int(bucket.get("row_count", 0) or 0),
            "wait_state_counts": cls._ordered_count_map(bucket.get("wait_state_counter", Counter())),
            "hard_wait_state_counts": cls._ordered_count_map(bucket.get("hard_wait_state_counter", Counter())),
            "wait_reason_counts": cls._ordered_count_map(
                bucket.get("wait_reason_counter", Counter()),
                limit=reason_limit,
            ),
            "hard_wait_true_rows": int(bucket.get("hard_wait_true_rows", 0) or 0),
        }

    @classmethod
    def _empty_wait_decision_bucket(cls) -> dict[str, object]:
        return {
            "decision_row_count": 0,
            "wait_decision_counter": Counter(),
            "wait_selected_rows": 0,
            "wait_skipped_rows": 0,
        }

    @classmethod
    def _accumulate_wait_decision_bucket(
        cls,
        bucket: dict[str, object],
        *,
        wait_selected: bool,
        wait_decision: str,
    ) -> None:
        decision = str(wait_decision or "").strip() or ("wait_selected" if wait_selected else "skip")
        bucket["decision_row_count"] = int(bucket.get("decision_row_count", 0) or 0) + 1
        bucket["wait_decision_counter"][decision] += 1
        if bool(wait_selected):
            bucket["wait_selected_rows"] = int(bucket.get("wait_selected_rows", 0) or 0) + 1
        else:
            bucket["wait_skipped_rows"] = int(bucket.get("wait_skipped_rows", 0) or 0) + 1

    @classmethod
    def _build_wait_decision_summary(cls, bucket: dict[str, object]) -> dict[str, object]:
        decision_row_count = int(bucket.get("decision_row_count", 0) or 0)
        wait_selected_rows = int(bucket.get("wait_selected_rows", 0) or 0)
        return {
            "decision_row_count": decision_row_count,
            "wait_decision_counts": cls._ordered_count_map(bucket.get("wait_decision_counter", Counter())),
            "wait_selected_rows": wait_selected_rows,
            "wait_skipped_rows": int(bucket.get("wait_skipped_rows", 0) or 0),
            "wait_selected_rate": round(wait_selected_rows / decision_row_count, 6)
            if decision_row_count > 0
            else 0.0,
        }

    @classmethod
    def _empty_wait_state_decision_bridge_bucket(cls) -> dict[str, object]:
        return {
            "bridge_row_count": 0,
            "state_to_decision_counter": Counter(),
            "selected_by_state_counter": Counter(),
            "hard_wait_selected_rows": 0,
            "soft_wait_selected_rows": 0,
        }

    @classmethod
    def _accumulate_wait_state_decision_bridge_bucket(
        cls,
        bucket: dict[str, object],
        *,
        wait_state: str,
        wait_hard: bool,
        wait_selected: bool,
        wait_decision: str,
    ) -> None:
        state = str(wait_state or "NONE").strip().upper() or "NONE"
        decision = str(wait_decision or "").strip() or ("wait_selected" if wait_selected else "skip")
        bucket["bridge_row_count"] = int(bucket.get("bridge_row_count", 0) or 0) + 1
        bucket["state_to_decision_counter"][f"{state}->{decision}"] += 1
        if bool(wait_selected):
            bucket["selected_by_state_counter"][state] += 1
            if bool(wait_hard):
                bucket["hard_wait_selected_rows"] = int(bucket.get("hard_wait_selected_rows", 0) or 0) + 1
            else:
                bucket["soft_wait_selected_rows"] = int(bucket.get("soft_wait_selected_rows", 0) or 0) + 1

    @classmethod
    def _build_wait_state_decision_bridge_summary(
        cls,
        bucket: dict[str, object],
        *,
        bridge_limit: int,
    ) -> dict[str, object]:
        return {
            "bridge_row_count": int(bucket.get("bridge_row_count", 0) or 0),
            "state_to_decision_counts": cls._ordered_count_map(
                bucket.get("state_to_decision_counter", Counter()),
                limit=bridge_limit,
            ),
            "selected_by_state_counts": cls._ordered_count_map(
                bucket.get("selected_by_state_counter", Counter())
            ),
            "hard_wait_selected_rows": int(bucket.get("hard_wait_selected_rows", 0) or 0),
            "soft_wait_selected_rows": int(bucket.get("soft_wait_selected_rows", 0) or 0),
        }

    @classmethod
    def _derive_exit_taxonomy_from_trade_row(cls, row: dict[str, object]) -> dict[str, object]:
        state = str(row.get("exit_wait_state", "") or "").strip().upper() or "NONE"
        winner = str(
            row.get("decision_winner", "")
            or row.get("final_outcome", "")
            or ""
        ).strip().lower()
        wait_selected = bool(row.get("exit_wait_selected", False))
        wait_decision = str(row.get("exit_wait_decision", "") or "").strip()
        decision_reason = str(row.get("decision_reason", "") or "").strip()

        taxonomy = build_exit_wait_taxonomy_v1(
            wait_state={
                "state": state,
                "hard_wait": bool(state == "REVERSAL_CONFIRM"),
                "reason": "",
            },
            utility_result={
                "winner": winner,
                "decision_reason": decision_reason,
                "wait_selected": bool(wait_selected),
                "wait_decision": wait_decision,
            },
        )
        state_taxonomy = dict(taxonomy.get("state", {}) or {})
        decision_taxonomy = dict(taxonomy.get("decision", {}) or {})
        bridge_taxonomy = dict(taxonomy.get("bridge", {}) or {})

        existing_state_family = str(row.get("exit_wait_state_family", "") or "").strip().lower()
        existing_hold_class = str(row.get("exit_wait_hold_class", "") or "").strip().lower()
        existing_decision_family = str(row.get("exit_wait_decision_family", "") or "").strip().lower()
        existing_bridge_status = str(row.get("exit_wait_bridge_status", "") or "").strip().lower()

        if existing_state_family:
            state_taxonomy["state_family"] = existing_state_family
        if existing_hold_class:
            state_taxonomy["hold_class"] = existing_hold_class
        if existing_decision_family:
            decision_taxonomy["decision_family"] = existing_decision_family
        if existing_bridge_status:
            bridge_taxonomy["bridge_status"] = existing_bridge_status

        return {
            "state": state_taxonomy,
            "decision": decision_taxonomy,
            "bridge": bridge_taxonomy,
        }

    @classmethod
    def _row_has_exit_semantic(cls, row: dict[str, object]) -> bool:
        return bool(
            str(row.get("exit_wait_state", "") or "").strip()
            or str(row.get("decision_winner", "") or "").strip()
            or str(row.get("exit_wait_decision", "") or "").strip()
            or str(row.get("decision_reason", "") or "").strip()
        )

    @classmethod
    def _empty_exit_state_semantic_bucket(cls) -> dict[str, object]:
        return {
            "row_count": 0,
            "wait_state_counter": Counter(),
            "state_family_counter": Counter(),
            "hold_class_counter": Counter(),
        }

    @classmethod
    def _accumulate_exit_state_semantic_bucket(
        cls,
        bucket: dict[str, object],
        *,
        state: str,
        state_family: str,
        hold_class: str,
    ) -> None:
        wait_state = str(state or "NONE").strip().upper() or "NONE"
        family = str(state_family or "neutral").strip().lower() or "neutral"
        hold = str(hold_class or "none").strip().lower() or "none"
        bucket["row_count"] = int(bucket.get("row_count", 0) or 0) + 1
        bucket["wait_state_counter"][wait_state] += 1
        bucket["state_family_counter"][family] += 1
        bucket["hold_class_counter"][hold] += 1

    @classmethod
    def _build_exit_state_semantic_summary(cls, bucket: dict[str, object]) -> dict[str, object]:
        return {
            "row_count": int(bucket.get("row_count", 0) or 0),
            "wait_state_counts": cls._ordered_count_map(bucket.get("wait_state_counter", Counter())),
            "state_family_counts": cls._ordered_count_map(bucket.get("state_family_counter", Counter())),
            "hold_class_counts": cls._ordered_count_map(bucket.get("hold_class_counter", Counter())),
        }

    @classmethod
    def _empty_exit_decision_bucket(cls) -> dict[str, object]:
        return {
            "decision_row_count": 0,
            "winner_counter": Counter(),
            "decision_family_counter": Counter(),
            "decision_reason_counter": Counter(),
            "wait_selected_rows": 0,
        }

    @classmethod
    def _accumulate_exit_decision_bucket(
        cls,
        bucket: dict[str, object],
        *,
        winner: str,
        decision_family: str,
        decision_reason: str,
        wait_selected: bool,
    ) -> None:
        winner_value = str(winner or "").strip().lower() or "none"
        family = str(decision_family or "neutral").strip().lower() or "neutral"
        reason = str(decision_reason or "").strip()
        bucket["decision_row_count"] = int(bucket.get("decision_row_count", 0) or 0) + 1
        bucket["winner_counter"][winner_value] += 1
        bucket["decision_family_counter"][family] += 1
        if reason:
            bucket["decision_reason_counter"][reason] += 1
        if bool(wait_selected):
            bucket["wait_selected_rows"] = int(bucket.get("wait_selected_rows", 0) or 0) + 1

    @classmethod
    def _build_exit_decision_summary(
        cls,
        bucket: dict[str, object],
        *,
        reason_limit: int,
    ) -> dict[str, object]:
        decision_row_count = int(bucket.get("decision_row_count", 0) or 0)
        return {
            "decision_row_count": decision_row_count,
            "winner_counts": cls._ordered_count_map(bucket.get("winner_counter", Counter())),
            "decision_family_counts": cls._ordered_count_map(
                bucket.get("decision_family_counter", Counter())
            ),
            "decision_reason_counts": cls._ordered_count_map(
                bucket.get("decision_reason_counter", Counter()),
                limit=reason_limit,
            ),
            "wait_selected_rows": int(bucket.get("wait_selected_rows", 0) or 0),
            "wait_selected_rate": round(
                int(bucket.get("wait_selected_rows", 0) or 0) / decision_row_count,
                6,
            )
            if decision_row_count > 0
            else 0.0,
        }

    @classmethod
    def _empty_exit_state_decision_bridge_bucket(cls) -> dict[str, object]:
        return {
            "bridge_row_count": 0,
            "bridge_status_counter": Counter(),
            "state_to_decision_counter": Counter(),
        }

    @classmethod
    def _accumulate_exit_state_decision_bridge_bucket(
        cls,
        bucket: dict[str, object],
        *,
        state_family: str,
        decision_family: str,
        bridge_status: str,
    ) -> None:
        state_key = str(state_family or "neutral").strip().lower() or "neutral"
        decision_key = str(decision_family or "neutral").strip().lower() or "neutral"
        bridge_key = str(bridge_status or "neutral").strip().lower() or "neutral"
        bucket["bridge_row_count"] = int(bucket.get("bridge_row_count", 0) or 0) + 1
        bucket["bridge_status_counter"][bridge_key] += 1
        bucket["state_to_decision_counter"][f"{state_key}->{decision_key}"] += 1

    @classmethod
    def _build_exit_state_decision_bridge_summary(
        cls,
        bucket: dict[str, object],
        *,
        bridge_limit: int,
    ) -> dict[str, object]:
        return {
            "bridge_row_count": int(bucket.get("bridge_row_count", 0) or 0),
            "bridge_status_counts": cls._ordered_count_map(
                bucket.get("bridge_status_counter", Counter()),
                limit=bridge_limit,
            ),
            "state_to_decision_counts": cls._ordered_count_map(
                bucket.get("state_to_decision_counter", Counter()),
                limit=bridge_limit,
            ),
        }

    @classmethod
    def _ordered_count_map(
        cls,
        counter: Counter,
        *,
        limit: int | None = None,
        preferred_order: tuple[str, ...] = (),
    ) -> dict[str, int]:
        items: list[tuple[str, int]] = []
        seen: set[str] = set()
        for key in preferred_order:
            count = int(counter.get(key, 0) or 0)
            if count > 0:
                items.append((str(key), count))
                seen.add(str(key))
        for key, count in sorted(((str(k), int(v)) for k, v in counter.items() if int(v) > 0), key=lambda item: (-item[1], item[0])):
            if key in seen:
                continue
            items.append((key, count))
        if limit is not None:
            items = items[: max(0, int(limit))]
        return {key: count for key, count in items}

    @classmethod
    def _summarize_recent_runtime_window(cls, rows: list[dict[str, object]]) -> dict[str, object]:
        stage_counter: Counter[str] = Counter()
        blocked_reason_counter: Counter[str] = Counter()
        symbol_stats: dict[str, dict[str, object]] = {}
        wrong_ready_count = 0
        display_ready_true = 0
        display_ready_false = 0
        entry_ready_true = 0
        entry_ready_false = 0
        blocked_row_count = 0
        wait_energy_state_bucket = cls._empty_wait_energy_trace_bucket()
        wait_energy_decision_bucket = cls._empty_wait_energy_trace_bucket()
        wait_bias_bundle_bucket = cls._empty_wait_bias_bundle_bucket()
        wait_state_policy_surface_bucket = cls._empty_wait_state_policy_surface_bucket()
        wait_special_scene_bucket = cls._empty_wait_special_scene_bucket()
        wait_threshold_shift_bucket = cls._empty_wait_threshold_shift_bucket()
        wait_state_semantic_bucket = cls._empty_wait_state_semantic_bucket()
        wait_decision_bucket = cls._empty_wait_decision_bucket()
        wait_state_decision_bridge_bucket = cls._empty_wait_state_decision_bridge_bucket()

        for row in rows:
            symbol = str(row.get("symbol", "") or "UNKNOWN").upper()
            stage = str(row.get("stage", "") or "NONE").upper() or "NONE"
            blocked_reason = str(row.get("blocked_reason", "") or "")
            display_ready = bool(row.get("display_ready", False))
            entry_ready = bool(row.get("entry_ready", False))
            wrong_ready = bool(row.get("wrong_ready", False))
            wait_state = str(row.get("entry_wait_state", "") or "").strip().upper()
            wait_hard = bool(row.get("entry_wait_hard", False))
            wait_reason = str(row.get("entry_wait_reason", "") or "").strip()
            wait_selected = bool(row.get("entry_wait_selected", False))
            wait_decision = str(row.get("entry_wait_decision", "") or "").strip()
            has_wait_semantic = cls._row_has_wait_semantic(row)
            state_trace = dict(row.get("entry_wait_energy_usage_trace_v1", {}) or {})
            decision_trace = dict(row.get("entry_wait_decision_energy_usage_trace_v1", {}) or {})
            wait_context = cls._resolve_wait_context_surface(row)
            wait_bias_bundle = cls._resolve_wait_bias_bundle_surface(row, wait_context=wait_context)
            wait_state_policy_input = cls._resolve_wait_state_policy_input_surface(
                row,
                wait_context=wait_context,
            )

            stage_counter[stage] += 1
            if blocked_reason:
                blocked_reason_counter[blocked_reason] += 1
                blocked_row_count += 1
            wrong_ready_count += int(wrong_ready)
            display_ready_true += int(display_ready)
            display_ready_false += int(not display_ready)
            entry_ready_true += int(entry_ready)
            entry_ready_false += int(not entry_ready)
            cls._accumulate_wait_energy_trace_bucket(wait_energy_state_bucket, state_trace)
            cls._accumulate_wait_energy_trace_bucket(wait_energy_decision_bucket, decision_trace)
            cls._accumulate_wait_bias_bundle_bucket(wait_bias_bundle_bucket, wait_bias_bundle)
            cls._accumulate_wait_state_policy_surface_bucket(
                wait_state_policy_surface_bucket,
                wait_context,
                wait_state_policy_input,
            )
            cls._accumulate_wait_special_scene_bucket(wait_special_scene_bucket, wait_state_policy_input)
            cls._accumulate_wait_threshold_shift_bucket(
                wait_threshold_shift_bucket,
                wait_bias_bundle,
                wait_state_policy_input,
            )
            if has_wait_semantic:
                cls._accumulate_wait_state_semantic_bucket(
                    wait_state_semantic_bucket,
                    wait_state=wait_state,
                    wait_hard=wait_hard,
                    wait_reason=wait_reason,
                )
                cls._accumulate_wait_decision_bucket(
                    wait_decision_bucket,
                    wait_selected=wait_selected,
                    wait_decision=wait_decision,
                )
                cls._accumulate_wait_state_decision_bridge_bucket(
                    wait_state_decision_bridge_bucket,
                    wait_state=wait_state,
                    wait_hard=wait_hard,
                    wait_selected=wait_selected,
                    wait_decision=wait_decision,
                )

            bucket = symbol_stats.setdefault(
                symbol,
                {
                    "rows": 0,
                    "stage_counter": Counter(),
                    "blocked_reason_counter": Counter(),
                    "wrong_ready_count": 0,
                    "display_ready_true": 0,
                    "display_ready_false": 0,
                    "entry_ready_true": 0,
                    "entry_ready_false": 0,
                    "wait_energy_state_bucket": cls._empty_wait_energy_trace_bucket(),
                    "wait_energy_decision_bucket": cls._empty_wait_energy_trace_bucket(),
                    "wait_bias_bundle_bucket": cls._empty_wait_bias_bundle_bucket(),
                    "wait_state_policy_surface_bucket": cls._empty_wait_state_policy_surface_bucket(),
                    "wait_special_scene_bucket": cls._empty_wait_special_scene_bucket(),
                    "wait_threshold_shift_bucket": cls._empty_wait_threshold_shift_bucket(),
                    "wait_state_semantic_bucket": cls._empty_wait_state_semantic_bucket(),
                    "wait_decision_bucket": cls._empty_wait_decision_bucket(),
                    "wait_state_decision_bridge_bucket": cls._empty_wait_state_decision_bridge_bucket(),
                },
            )
            bucket["rows"] = int(bucket.get("rows", 0) or 0) + 1
            bucket["stage_counter"][stage] += 1
            if blocked_reason:
                bucket["blocked_reason_counter"][blocked_reason] += 1
            bucket["wrong_ready_count"] = int(bucket.get("wrong_ready_count", 0) or 0) + int(wrong_ready)
            bucket["display_ready_true"] = int(bucket.get("display_ready_true", 0) or 0) + int(display_ready)
            bucket["display_ready_false"] = int(bucket.get("display_ready_false", 0) or 0) + int(not display_ready)
            bucket["entry_ready_true"] = int(bucket.get("entry_ready_true", 0) or 0) + int(entry_ready)
            bucket["entry_ready_false"] = int(bucket.get("entry_ready_false", 0) or 0) + int(not entry_ready)
            cls._accumulate_wait_energy_trace_bucket(bucket["wait_energy_state_bucket"], state_trace)
            cls._accumulate_wait_energy_trace_bucket(bucket["wait_energy_decision_bucket"], decision_trace)
            cls._accumulate_wait_bias_bundle_bucket(bucket["wait_bias_bundle_bucket"], wait_bias_bundle)
            cls._accumulate_wait_state_policy_surface_bucket(
                bucket["wait_state_policy_surface_bucket"],
                wait_context,
                wait_state_policy_input,
            )
            cls._accumulate_wait_special_scene_bucket(bucket["wait_special_scene_bucket"], wait_state_policy_input)
            cls._accumulate_wait_threshold_shift_bucket(
                bucket["wait_threshold_shift_bucket"],
                wait_bias_bundle,
                wait_state_policy_input,
            )
            if has_wait_semantic:
                cls._accumulate_wait_state_semantic_bucket(
                    bucket["wait_state_semantic_bucket"],
                    wait_state=wait_state,
                    wait_hard=wait_hard,
                    wait_reason=wait_reason,
                )
                cls._accumulate_wait_decision_bucket(
                    bucket["wait_decision_bucket"],
                    wait_selected=wait_selected,
                    wait_decision=wait_decision,
                )
                cls._accumulate_wait_state_decision_bridge_bucket(
                    bucket["wait_state_decision_bridge_bucket"],
                    wait_state=wait_state,
                    wait_hard=wait_hard,
                    wait_selected=wait_selected,
                    wait_decision=wait_decision,
                )

        symbol_summary: dict[str, object] = {}
        for symbol in sorted(symbol_stats):
            bucket = symbol_stats[symbol]
            symbol_summary[symbol] = {
                "rows": int(bucket.get("rows", 0) or 0),
                "stage_counts": cls._ordered_count_map(
                    bucket.get("stage_counter", Counter()),
                    preferred_order=cls.RUNTIME_RECENT_STAGE_ORDER,
                ),
                "blocked_reason_counts": cls._ordered_count_map(
                    bucket.get("blocked_reason_counter", Counter()),
                    limit=cls.RUNTIME_RECENT_SYMBOL_BLOCKED_REASON_LIMIT,
                ),
                "wrong_ready_count": int(bucket.get("wrong_ready_count", 0) or 0),
                "display_ready_true": int(bucket.get("display_ready_true", 0) or 0),
                "display_ready_false": int(bucket.get("display_ready_false", 0) or 0),
                "entry_ready_true": int(bucket.get("entry_ready_true", 0) or 0),
                "entry_ready_false": int(bucket.get("entry_ready_false", 0) or 0),
                "wait_energy_trace_summary": cls._build_wait_energy_trace_summary(
                    bucket.get("wait_energy_state_bucket", cls._empty_wait_energy_trace_bucket()),
                    bucket.get("wait_energy_decision_bucket", cls._empty_wait_energy_trace_bucket()),
                    branch_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_ENERGY_BRANCH_LIMIT,
                ),
                "wait_bias_bundle_summary": cls._build_wait_bias_bundle_summary(
                    bucket.get("wait_bias_bundle_bucket", cls._empty_wait_bias_bundle_bucket()),
                    source_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_BIAS_SOURCE_LIMIT,
                ),
                "wait_state_policy_surface_summary": cls._build_wait_state_policy_surface_summary(
                    bucket.get(
                        "wait_state_policy_surface_bucket",
                        cls._empty_wait_state_policy_surface_bucket(),
                    ),
                    reason_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_POLICY_REASON_LIMIT,
                ),
                "wait_special_scene_summary": cls._build_wait_special_scene_summary(
                    bucket.get("wait_special_scene_bucket", cls._empty_wait_special_scene_bucket()),
                    scene_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_SCENE_LIMIT,
                ),
                "wait_threshold_shift_summary": cls._build_wait_threshold_shift_summary(
                    bucket.get("wait_threshold_shift_bucket", cls._empty_wait_threshold_shift_bucket())
                ),
                "wait_state_semantic_summary": cls._build_wait_state_semantic_summary(
                    bucket.get("wait_state_semantic_bucket", cls._empty_wait_state_semantic_bucket()),
                    reason_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_REASON_LIMIT,
                ),
                "wait_decision_summary": cls._build_wait_decision_summary(
                    bucket.get("wait_decision_bucket", cls._empty_wait_decision_bucket())
                ),
                "wait_state_decision_bridge_summary": cls._build_wait_state_decision_bridge_summary(
                    bucket.get(
                        "wait_state_decision_bridge_bucket",
                        cls._empty_wait_state_decision_bridge_bucket(),
                    ),
                    bridge_limit=cls.RUNTIME_RECENT_SYMBOL_WAIT_STATE_DECISION_BRIDGE_LIMIT,
                ),
            }

        return {
            "row_count": int(len(rows)),
            "oldest_time": str(rows[0].get("time", "") or "") if rows else "",
            "latest_time": str(rows[-1].get("time", "") or "") if rows else "",
            "stage_counts": cls._ordered_count_map(stage_counter, preferred_order=cls.RUNTIME_RECENT_STAGE_ORDER),
            "blocked_reason_counts": cls._ordered_count_map(
                blocked_reason_counter,
                limit=cls.RUNTIME_RECENT_BLOCKED_REASON_LIMIT,
            ),
            "wrong_ready_count": int(wrong_ready_count),
            "display_ready_summary": {
                "display_ready_true": int(display_ready_true),
                "display_ready_false": int(display_ready_false),
                "entry_ready_true": int(entry_ready_true),
                "entry_ready_false": int(entry_ready_false),
                "blocked_row_count": int(blocked_row_count),
            },
            "wait_energy_trace_summary": cls._build_wait_energy_trace_summary(
                wait_energy_state_bucket,
                wait_energy_decision_bucket,
                branch_limit=cls.RUNTIME_RECENT_WAIT_ENERGY_BRANCH_LIMIT,
            ),
            "wait_bias_bundle_summary": cls._build_wait_bias_bundle_summary(
                wait_bias_bundle_bucket,
                source_limit=cls.RUNTIME_RECENT_WAIT_BIAS_SOURCE_LIMIT,
            ),
            "wait_state_policy_surface_summary": cls._build_wait_state_policy_surface_summary(
                wait_state_policy_surface_bucket,
                reason_limit=cls.RUNTIME_RECENT_WAIT_POLICY_REASON_LIMIT,
            ),
            "wait_special_scene_summary": cls._build_wait_special_scene_summary(
                wait_special_scene_bucket,
                scene_limit=cls.RUNTIME_RECENT_WAIT_SCENE_LIMIT,
            ),
            "wait_threshold_shift_summary": cls._build_wait_threshold_shift_summary(
                wait_threshold_shift_bucket,
            ),
            "wait_state_semantic_summary": cls._build_wait_state_semantic_summary(
                wait_state_semantic_bucket,
                reason_limit=cls.RUNTIME_RECENT_WAIT_REASON_LIMIT,
            ),
            "wait_decision_summary": cls._build_wait_decision_summary(wait_decision_bucket),
            "wait_state_decision_bridge_summary": cls._build_wait_state_decision_bridge_summary(
                wait_state_decision_bridge_bucket,
                bridge_limit=cls.RUNTIME_RECENT_WAIT_STATE_DECISION_BRIDGE_LIMIT,
            ),
            "symbol_summary": symbol_summary,
        }

    @classmethod
    def _summarize_recent_exit_runtime_window(cls, rows: list[dict[str, object]]) -> dict[str, object]:
        status_counter: Counter[str] = Counter()
        symbol_stats: dict[str, dict[str, object]] = {}
        exit_state_semantic_bucket = cls._empty_exit_state_semantic_bucket()
        exit_decision_bucket = cls._empty_exit_decision_bucket()
        exit_bridge_bucket = cls._empty_exit_state_decision_bridge_bucket()

        for row in rows:
            symbol = str(row.get("symbol", "") or "UNKNOWN").strip().upper() or "UNKNOWN"
            status = str(row.get("status", "") or "UNKNOWN").strip().upper() or "UNKNOWN"
            taxonomy = cls._derive_exit_taxonomy_from_trade_row(row)
            state_taxonomy = dict(taxonomy.get("state", {}) or {})
            decision_taxonomy = dict(taxonomy.get("decision", {}) or {})
            bridge_taxonomy = dict(taxonomy.get("bridge", {}) or {})
            status_counter[status] += 1
            cls._accumulate_exit_state_semantic_bucket(
                exit_state_semantic_bucket,
                state=str(state_taxonomy.get("state", "") or ""),
                state_family=str(state_taxonomy.get("state_family", "") or ""),
                hold_class=str(state_taxonomy.get("hold_class", "") or ""),
            )
            cls._accumulate_exit_decision_bucket(
                exit_decision_bucket,
                winner=str(decision_taxonomy.get("winner", "") or ""),
                decision_family=str(decision_taxonomy.get("decision_family", "") or ""),
                decision_reason=str(decision_taxonomy.get("decision_reason", "") or ""),
                wait_selected=bool(decision_taxonomy.get("wait_selected", False)),
            )
            cls._accumulate_exit_state_decision_bridge_bucket(
                exit_bridge_bucket,
                state_family=str(state_taxonomy.get("state_family", "") or ""),
                decision_family=str(decision_taxonomy.get("decision_family", "") or ""),
                bridge_status=str(bridge_taxonomy.get("bridge_status", "") or ""),
            )

            bucket = symbol_stats.setdefault(
                symbol,
                {
                    "rows": 0,
                    "status_counter": Counter(),
                    "exit_state_semantic_bucket": cls._empty_exit_state_semantic_bucket(),
                    "exit_decision_bucket": cls._empty_exit_decision_bucket(),
                    "exit_bridge_bucket": cls._empty_exit_state_decision_bridge_bucket(),
                },
            )
            bucket["rows"] = int(bucket.get("rows", 0) or 0) + 1
            bucket["status_counter"][status] += 1
            cls._accumulate_exit_state_semantic_bucket(
                bucket["exit_state_semantic_bucket"],
                state=str(state_taxonomy.get("state", "") or ""),
                state_family=str(state_taxonomy.get("state_family", "") or ""),
                hold_class=str(state_taxonomy.get("hold_class", "") or ""),
            )
            cls._accumulate_exit_decision_bucket(
                bucket["exit_decision_bucket"],
                winner=str(decision_taxonomy.get("winner", "") or ""),
                decision_family=str(decision_taxonomy.get("decision_family", "") or ""),
                decision_reason=str(decision_taxonomy.get("decision_reason", "") or ""),
                wait_selected=bool(decision_taxonomy.get("wait_selected", False)),
            )
            cls._accumulate_exit_state_decision_bridge_bucket(
                bucket["exit_bridge_bucket"],
                state_family=str(state_taxonomy.get("state_family", "") or ""),
                decision_family=str(decision_taxonomy.get("decision_family", "") or ""),
                bridge_status=str(bridge_taxonomy.get("bridge_status", "") or ""),
            )

        symbol_summary: dict[str, object] = {}
        for symbol in sorted(symbol_stats):
            bucket = symbol_stats[symbol]
            symbol_summary[symbol] = {
                "rows": int(bucket.get("rows", 0) or 0),
                "status_counts": cls._ordered_count_map(bucket.get("status_counter", Counter())),
                "exit_state_semantic_summary": cls._build_exit_state_semantic_summary(
                    bucket.get("exit_state_semantic_bucket", cls._empty_exit_state_semantic_bucket())
                ),
                "exit_decision_summary": cls._build_exit_decision_summary(
                    bucket.get("exit_decision_bucket", cls._empty_exit_decision_bucket()),
                    reason_limit=cls.RUNTIME_RECENT_SYMBOL_EXIT_REASON_LIMIT,
                ),
                "exit_state_decision_bridge_summary": cls._build_exit_state_decision_bridge_summary(
                    bucket.get("exit_bridge_bucket", cls._empty_exit_state_decision_bridge_bucket()),
                    bridge_limit=cls.RUNTIME_RECENT_SYMBOL_EXIT_BRIDGE_LIMIT,
                ),
            }

        return {
            "row_count": int(len(rows)),
            "oldest_time": str(rows[0].get("time", "") or "") if rows else "",
            "latest_time": str(rows[-1].get("time", "") or "") if rows else "",
            "status_counts": cls._ordered_count_map(status_counter),
            "exit_state_semantic_summary": cls._build_exit_state_semantic_summary(
                exit_state_semantic_bucket
            ),
            "exit_decision_summary": cls._build_exit_decision_summary(
                exit_decision_bucket,
                reason_limit=cls.RUNTIME_RECENT_EXIT_REASON_LIMIT,
            ),
            "exit_state_decision_bridge_summary": cls._build_exit_state_decision_bridge_summary(
                exit_bridge_bucket,
                bridge_limit=cls.RUNTIME_RECENT_EXIT_BRIDGE_LIMIT,
            ),
            "symbol_summary": symbol_summary,
        }

    def _build_recent_exit_runtime_diagnostics(self) -> dict[str, object]:
        windows = tuple(sorted({int(size) for size in self.RUNTIME_RECENT_WINDOWS if int(size) > 0}))
        source_path = Path(
            getattr(self, "trade_history_csv_path", self._resolve_project_path(r"data\trades\trade_history.csv"))
        )
        diagnostics = {
            "contract_version": "runtime_recent_exit_diagnostics_v1",
            "source": "trade_history.csv",
            "source_path": str(source_path),
            "available": False,
            "reason": "source_missing",
            "error": "",
            "windows": {
                f"last_{size}": self._summarize_recent_exit_runtime_window([])
                for size in windows
            },
        }
        if not source_path.exists():
            return diagnostics

        buffer: deque[dict[str, object]] = deque(maxlen=max(windows) if windows else 0)
        try:
            with source_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for raw_row in reader:
                    if not isinstance(raw_row, dict):
                        continue
                    row = {
                        "time": str(raw_row.get("close_time", "") or raw_row.get("open_time", "") or ""),
                        "symbol": str(raw_row.get("symbol", "") or "UNKNOWN").strip().upper() or "UNKNOWN",
                        "status": str(raw_row.get("status", "") or "UNKNOWN").strip().upper() or "UNKNOWN",
                        "exit_wait_state": str(raw_row.get("exit_wait_state", "") or "").strip().upper(),
                        "exit_wait_selected": self._csv_bool(raw_row.get("exit_wait_selected", "")),
                        "exit_wait_decision": str(raw_row.get("exit_wait_decision", "") or "").strip(),
                        "decision_winner": str(raw_row.get("decision_winner", "") or "").strip().lower(),
                        "final_outcome": str(raw_row.get("final_outcome", "") or "").strip().lower(),
                        "decision_reason": str(raw_row.get("decision_reason", "") or "").strip(),
                        "exit_wait_state_family": str(raw_row.get("exit_wait_state_family", "") or "").strip().lower(),
                        "exit_wait_hold_class": str(raw_row.get("exit_wait_hold_class", "") or "").strip().lower(),
                        "exit_wait_decision_family": str(
                            raw_row.get("exit_wait_decision_family", "") or ""
                        ).strip().lower(),
                        "exit_wait_bridge_status": str(
                            raw_row.get("exit_wait_bridge_status", "") or ""
                        ).strip().lower(),
                    }
                    if not self._row_has_exit_semantic(row):
                        continue
                    buffer.append(row)
        except Exception as exc:
            diagnostics["reason"] = "read_failed"
            diagnostics["error"] = str(exc)
            return diagnostics

        rows = list(buffer)
        diagnostics["available"] = True
        diagnostics["reason"] = "ok" if rows else "empty_source"
        diagnostics["rows_loaded"] = int(len(rows))
        diagnostics["windows"] = {}
        for size in windows:
            diagnostics["windows"][f"last_{size}"] = self._summarize_recent_exit_runtime_window(rows[-size:])
        return diagnostics

    @classmethod
    def _build_recent_exit_runtime_summary(
        cls,
        recent_exit_diagnostics: dict[str, object],
    ) -> tuple[dict[str, object], dict[str, object]]:
        window_key = f"last_{int(cls.RUNTIME_RECENT_DEFAULT_WINDOW)}"
        windows = dict(recent_exit_diagnostics.get("windows", {}) or {})
        default_window = dict(windows.get(window_key, {}) or {})
        summary_windows: dict[str, object] = {}
        for key in sorted(windows):
            window = dict(windows.get(key, {}) or {})
            summary_windows[str(key)] = {
                "row_count": int(window.get("row_count", 0) or 0),
                "status_counts": dict(window.get("status_counts", {}) or {}),
                "exit_state_semantic_summary": dict(window.get("exit_state_semantic_summary", {}) or {}),
                "exit_decision_summary": dict(window.get("exit_decision_summary", {}) or {}),
                "exit_state_decision_bridge_summary": dict(
                    window.get("exit_state_decision_bridge_summary", {}) or {}
                ),
            }
        return (
            {
                "contract_version": "runtime_recent_exit_summary_v1",
                "source": str(recent_exit_diagnostics.get("source", "") or ""),
                "source_path": str(recent_exit_diagnostics.get("source_path", "") or ""),
                "available": bool(recent_exit_diagnostics.get("available", False)),
                "reason": str(recent_exit_diagnostics.get("reason", "") or ""),
                "default_window": window_key,
                "windows": summary_windows,
            },
            default_window,
        )

    def _build_recent_runtime_diagnostics(self) -> dict[str, object]:
        windows = tuple(sorted({int(size) for size in self.RUNTIME_RECENT_WINDOWS if int(size) > 0}))
        source_path = Path(getattr(self, "entry_decision_log_path", self._resolve_project_path(r"data\trades\entry_decisions.csv")))
        diagnostics = {
            "contract_version": "runtime_recent_diagnostics_v1",
            "source": "entry_decisions.csv",
            "source_path": str(source_path),
            "available": False,
            "reason": "source_missing",
            "error": "",
            "windows": {
                f"last_{size}": self._summarize_recent_runtime_window([])
                for size in windows
            },
        }
        if not source_path.exists():
            return diagnostics

        buffer: deque[dict[str, object]] = deque(maxlen=max(windows) if windows else 0)
        try:
            with source_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for raw_row in reader:
                    if not isinstance(raw_row, dict):
                        continue
                    blocked_reason = str(
                        raw_row.get("blocked_by", "")
                        or raw_row.get("action_none_reason", "")
                        or ""
                    ).strip()
                    stage = str(raw_row.get("consumer_check_stage", "") or "").strip().upper() or "NONE"
                    entry_ready = self._csv_bool(raw_row.get("consumer_check_entry_ready", ""))
                    display_ready = self._csv_bool(raw_row.get("consumer_check_display_ready", ""))
                    buffer.append(
                        {
                            "time": str(raw_row.get("time", "") or ""),
                            "symbol": str(raw_row.get("symbol", "") or "UNKNOWN").strip().upper() or "UNKNOWN",
                            "stage": stage,
                            "blocked_reason": blocked_reason,
                            "display_ready": display_ready,
                            "entry_ready": entry_ready,
                            "wrong_ready": bool(blocked_reason and (stage == "READY" or entry_ready)),
                            "entry_wait_state": str(raw_row.get("entry_wait_state", "") or "").strip().upper(),
                            "entry_wait_hard": self._csv_bool(raw_row.get("entry_wait_hard", "")),
                            "entry_wait_reason": str(raw_row.get("entry_wait_reason", "") or "").strip(),
                            "entry_wait_selected": self._csv_bool(raw_row.get("entry_wait_selected", "")),
                            "entry_wait_decision": str(raw_row.get("entry_wait_decision", "") or "").strip(),
                            "entry_wait_context_v1": self._csv_json_dict(
                                raw_row.get("entry_wait_context_v1", "")
                            ),
                            "entry_wait_bias_bundle_v1": self._csv_json_dict(
                                raw_row.get("entry_wait_bias_bundle_v1", "")
                            ),
                            "entry_wait_state_policy_input_v1": self._csv_json_dict(
                                raw_row.get("entry_wait_state_policy_input_v1", "")
                            ),
                            "entry_wait_energy_usage_trace_v1": self._csv_json_dict(
                                raw_row.get("entry_wait_energy_usage_trace_v1", "")
                            ),
                            "entry_wait_decision_energy_usage_trace_v1": self._csv_json_dict(
                                raw_row.get("entry_wait_decision_energy_usage_trace_v1", "")
                            ),
                        }
                    )
        except Exception as exc:
            diagnostics["reason"] = "read_failed"
            diagnostics["error"] = str(exc)
            return diagnostics

        rows = list(buffer)
        diagnostics["available"] = True
        diagnostics["reason"] = "ok" if rows else "empty_source"
        diagnostics["rows_loaded"] = int(len(rows))
        diagnostics["windows"] = {}
        for size in windows:
            diagnostics["windows"][f"last_{size}"] = self._summarize_recent_runtime_window(rows[-size:])
        return diagnostics

    @classmethod
    def _build_recent_runtime_summary(cls, recent_diagnostics: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        window_key = f"last_{int(cls.RUNTIME_RECENT_DEFAULT_WINDOW)}"
        windows = dict(recent_diagnostics.get("windows", {}) or {})
        default_window = dict(windows.get(window_key, {}) or {})
        summary_windows: dict[str, object] = {}
        for key in sorted(windows):
            window = dict(windows.get(key, {}) or {})
            summary_windows[str(key)] = {
                "row_count": int(window.get("row_count", 0) or 0),
                "stage_counts": dict(window.get("stage_counts", {}) or {}),
                "blocked_reason_counts": dict(window.get("blocked_reason_counts", {}) or {}),
                "wrong_ready_count": int(window.get("wrong_ready_count", 0) or 0),
                "display_ready_summary": dict(window.get("display_ready_summary", {}) or {}),
                "wait_energy_trace_summary": dict(window.get("wait_energy_trace_summary", {}) or {}),
                "wait_bias_bundle_summary": dict(window.get("wait_bias_bundle_summary", {}) or {}),
                "wait_state_policy_surface_summary": dict(
                    window.get("wait_state_policy_surface_summary", {}) or {}
                ),
                "wait_special_scene_summary": dict(window.get("wait_special_scene_summary", {}) or {}),
                "wait_threshold_shift_summary": dict(window.get("wait_threshold_shift_summary", {}) or {}),
                "wait_state_semantic_summary": dict(window.get("wait_state_semantic_summary", {}) or {}),
                "wait_decision_summary": dict(window.get("wait_decision_summary", {}) or {}),
                "wait_state_decision_bridge_summary": dict(
                    window.get("wait_state_decision_bridge_summary", {}) or {}
                ),
            }
        return (
            {
                "contract_version": "runtime_recent_summary_v1",
                "source": str(recent_diagnostics.get("source", "entry_decisions.csv") or "entry_decisions.csv"),
                "available": bool(recent_diagnostics.get("available", False)),
                "reason": str(recent_diagnostics.get("reason", "unknown") or "unknown"),
                "default_window": window_key,
                "windows": summary_windows,
            },
            default_window,
        )

    def _semantic_shadow_runtime_export(self) -> dict[str, object]:
        raw = dict(self.semantic_shadow_runtime_diagnostics or {})
        checked_at = str(raw.get("checked_at", "") or "")
        return {
            "contract_version": "semantic_shadow_runtime_export_v1",
            "checked_at": checked_at,
            "state": str(raw.get("state", "") or ""),
            "reason": str(raw.get("reason", "") or ""),
            "model_dir": str(raw.get("model_dir", self.semantic_model_dir) or self.semantic_model_dir),
            "model_dir_exists": bool(raw.get("model_dir_exists", self.semantic_model_dir.exists())),
            "available_targets": list(raw.get("available_targets", []) or []),
            "load_error": str(raw.get("error", "") or ""),
            "raw": raw,
        }

    def _load_semantic_shadow_runtime(self, model_dir: Path):
        if not model_dir.exists():
            logger.info("Semantic shadow model dir not found: %s", model_dir)
            self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                state="inactive",
                reason="model_dir_missing",
                available_targets=(),
            )
            return None
        try:
            runtime = SemanticShadowRuntime(model_dir)
            if not runtime.available_targets:
                logger.info("Semantic shadow models not found in: %s", model_dir)
                self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                    state="inactive",
                    reason="model_files_missing",
                    available_targets=(),
                )
                return None
            logger.info(
                "Semantic shadow runtime loaded: %s targets=%s",
                model_dir,
                ",".join(runtime.available_targets),
            )
            self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                state="active",
                reason="loaded",
                available_targets=runtime.available_targets,
            )
            return runtime
        except Exception as exc:
            logger.exception("Failed to load semantic shadow runtime: %s", exc)
            self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                state="inactive",
                reason="model_load_failed",
                available_targets=(),
                error=str(exc),
            )
            return None

    def _refresh_ai_runtime_if_needed(self, force=False):
        now = time.time()
        if not force and (now - self.ai_last_check_at) < self.AI_MODEL_CHECK_INTERVAL_SEC:
            return
        self.ai_last_check_at = now

        if not bool(getattr(Config, "AI_RUNTIME_ENABLED", True)):
            self.ai_runtime = None
            self.ai_model_mtime = None
            return

        if not self.ai_model_path.exists():
            self.ai_runtime = None
            self.ai_model_mtime = None
            return

        try:
            mtime = self.ai_model_path.stat().st_mtime
            if force or self.ai_model_mtime is None or mtime > self.ai_model_mtime:
                runtime = self._load_ai_runtime(self.ai_model_path)
                if runtime is not None:
                    self.ai_runtime = runtime
                    self.ai_model_mtime = mtime
                    logger.info("AI model hot-reloaded: %s", self.ai_model_path)
        except Exception as exc:
            logger.exception("Failed to refresh AI runtime: %s", exc)

    def _refresh_semantic_shadow_runtime_if_needed(self, force=False):
        now = time.time()
        if not force and (now - self.semantic_last_check_at) < self.AI_MODEL_CHECK_INTERVAL_SEC:
            return
        self.semantic_last_check_at = now

        signature = self._semantic_model_signature(self.semantic_model_dir)
        if not signature:
            self.semantic_shadow_runtime = None
            self.semantic_model_signature = tuple()
            self.semantic_shadow_runtime_diagnostics = self._build_semantic_shadow_runtime_diagnostics(
                state="inactive",
                reason=("model_dir_missing" if not self.semantic_model_dir.exists() else "model_files_missing"),
                available_targets=(),
            )
            return

        if force or signature != self.semantic_model_signature:
            runtime = self._load_semantic_shadow_runtime(self.semantic_model_dir)
            self.semantic_shadow_runtime = runtime
            self.semantic_model_signature = signature
            if runtime is not None:
                logger.info("Semantic shadow runtime hot-reloaded: %s", self.semantic_model_dir)

    def record_semantic_rollout_event(self, *, domain: str, event: dict | None) -> None:
        payload = dict(event or {})
        bucket_key = "entry" if str(domain or "").strip().lower() != "exit" else "exit"
        state = getattr(self, "semantic_rollout_state", None)
        if not isinstance(state, dict):
            return
        bucket = state.get(bucket_key)
        if not isinstance(bucket, dict):
            bucket = {
                "events_total": 0,
                "alerts_total": 0,
                "threshold_applied_total": 0,
                "fallback_total": 0,
                "partial_live_total": 0,
            }
            state[bucket_key] = bucket
        bucket["events_total"] = int(bucket.get("events_total", 0) or 0) + 1
        bucket["alerts_total"] = int(bucket.get("alerts_total", 0) or 0) + int(
            1 if bool(payload.get("alert_active")) else 0
        )
        bucket["threshold_applied_total"] = int(bucket.get("threshold_applied_total", 0) or 0) + int(
            1 if bool(payload.get("threshold_applied")) else 0
        )
        bucket["fallback_total"] = int(bucket.get("fallback_total", 0) or 0) + int(
            1 if bool(payload.get("fallback_applied")) else 0
        )
        bucket["partial_live_total"] = int(bucket.get("partial_live_total", 0) or 0) + int(
            1 if bool(payload.get("partial_live_applied")) else 0
        )
        recent = state.get("recent")
        if not isinstance(recent, list):
            recent = []
            state["recent"] = recent
        recent.append(
            {
                "time": datetime.now(KST).isoformat(timespec="seconds"),
                "domain": bucket_key,
                "symbol": str(payload.get("symbol", "")),
                "mode": str(payload.get("mode", "")),
                "baseline_action": str(payload.get("baseline_action", "")),
                "trace_quality_state": str(payload.get("trace_quality_state", "")),
                "threshold_before": payload.get("threshold_before"),
                "threshold_after": payload.get("threshold_after"),
                "threshold_adjustment_points": payload.get("threshold_adjustment_points"),
                "fallback_reason": str(payload.get("fallback_reason", "")),
                "alert_active": bool(payload.get("alert_active")),
                "reason": str(payload.get("reason", "")),
            }
        )
        if len(recent) > 40:
            state["recent"] = recent[-40:]

    def _semantic_live_config_payload(self) -> dict[str, object]:
        return {
            "contract_version": SEMANTIC_LIVE_ROLLOUT_VERSION,
            "mode": str(getattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "disabled") or "disabled"),
            "kill_switch": bool(getattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False)),
            "require_clean_trace": bool(getattr(Config, "SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE", True)),
            "max_missing_features": int(getattr(Config, "SEMANTIC_LIVE_MAX_MISSING_FEATURES", 2)),
            "allowed_compatibility_modes": list(
                getattr(Config, "SEMANTIC_LIVE_ALLOWED_COMPATIBILITY_MODES", ()) or ()
            ),
            "symbol_allowlist": list(getattr(Config, "SEMANTIC_LIVE_SYMBOL_ALLOWLIST", ()) or ()),
            "entry_stage_allowlist": list(
                getattr(Config, "SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST", ()) or ()
            ),
            "min_timing_probability": float(getattr(Config, "SEMANTIC_LIVE_MIN_TIMING_PROB", 0.58)),
            "min_entry_quality_probability": float(
                getattr(Config, "SEMANTIC_LIVE_MIN_ENTRY_QUALITY_PROB", 0.58)
            ),
            "shadow_runtime_state": str(
                (self.semantic_shadow_runtime_diagnostics or {}).get("state", "") or ""
            ),
            "shadow_runtime_reason": str(
                (self.semantic_shadow_runtime_diagnostics or {}).get("reason", "") or ""
            ),
            "shadow_runtime_available_targets": list(
                (self.semantic_shadow_runtime_diagnostics or {}).get("available_targets", []) or []
            ),
            "timing_threshold": float(getattr(Config, "SEMANTIC_TIMING_THRESHOLD", 0.55)),
            "entry_quality_threshold": float(
                getattr(Config, "SEMANTIC_ENTRY_QUALITY_THRESHOLD", 0.55)
            ),
            "exit_management_threshold": float(
                getattr(Config, "SEMANTIC_EXIT_MANAGEMENT_THRESHOLD", 0.55)
            ),
        }

    @staticmethod
    def get_lot_size(symbol):
        for key, lot in Config.LOT_SIZES.items():
            if key in symbol.upper():
                return lot
        return Config.LOT_SIZES.get("DEFAULT", 0.01)

    @staticmethod
    def _get_symbol_pct(symbol, mapping, default_key="DEFAULT"):
        upper = symbol.upper()
        for key, val in mapping.items():
            if key == default_key:
                continue
            if key in upper:
                return float(val)
        return float(mapping.get(default_key, 0.0))

    def _calc_sl_tp(self, symbol, action, price):
        info = self.broker.symbol_info(symbol)
        if not info:
            return None, None

        point = float(info.point or 0.0)
        digits = int(info.digits or 5)
        stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
        min_stop_dist = point * stops_level if point > 0 else 0.0

        sl_pct = TradingApplication._get_symbol_pct(symbol, Config.STOP_LOSS_PCT_BY_SYMBOL)
        tp_pct = TradingApplication._get_symbol_pct(symbol, Config.TAKE_PROFIT_PCT_BY_SYMBOL)

        # Use max of broker minimum stop distance and percentage-based distance.
        sl_dist = max(price * sl_pct, min_stop_dist * 1.2, point * 10 if point > 0 else 0.0)
        tp_dist = max(price * tp_pct, min_stop_dist * 1.2, point * 10 if point > 0 else 0.0)

        sl = None
        tp = None
        if action == "BUY":
            sl = round(price - sl_dist, digits) if Config.USE_SERVER_SIDE_SL else None
            tp = round(price + tp_dist, digits) if Config.USE_SERVER_SIDE_TP else None
        else:
            sl = round(price + sl_dist, digits) if Config.USE_SERVER_SIDE_SL else None
            tp = round(price - tp_dist, digits) if Config.USE_SERVER_SIDE_TP else None
        return sl, tp

    @staticmethod
    def _mt5_common_files_dir():
        appdata = os.getenv("APPDATA", "")
        if not appdata:
            return None
        p = Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"
        return p if p.exists() else None

    @classmethod
    def _read_exported_indicator_row(cls, symbol):
        """
        Read latest indicator row exported by DrawHelper from MT5 common files.
        Expected file: <SYMBOL>_indicator_data.csv
        """
        common_dir = cls._mt5_common_files_dir()
        if common_dir is None:
            return {}
        f = common_dir / f"{symbol}_indicator_data.csv"
        if not f.exists():
            return {}
        try:
            df = pd.read_csv(f)
            if df.empty:
                return {}
            if "time" in df.columns:
                df["_dt"] = pd.to_datetime(df["time"], errors="coerce")
                if df["_dt"].notna().any():
                    row = df.sort_values("_dt", ascending=False).iloc[0]
                else:
                    row = df.iloc[-1]
            else:
                row = df.iloc[-1]
            return {
                "ind_rsi": float(pd.to_numeric(row.get("rsi"), errors="coerce")),
                "ind_adx": float(pd.to_numeric(row.get("adx"), errors="coerce")),
                "ind_plus_di": float(pd.to_numeric(row.get("plus_di"), errors="coerce")),
                "ind_minus_di": float(pd.to_numeric(row.get("minus_di"), errors="coerce")),
                "ind_ma_20": float(pd.to_numeric(row.get("ma20"), errors="coerce")),
                "ind_ma_60": float(pd.to_numeric(row.get("ma60"), errors="coerce")),
                "ind_ma_120": float(pd.to_numeric(row.get("ma120"), errors="coerce")),
                "ind_ma_240": float(pd.to_numeric(row.get("ma240"), errors="coerce")),
                "ind_ma_480": float(pd.to_numeric(row.get("ma480"), errors="coerce")),
                "ind_bb_20_up": float(pd.to_numeric(row.get("bb20_up"), errors="coerce")),
                "ind_bb_20_mid": float(pd.to_numeric(row.get("bb20_mid"), errors="coerce")),
                "ind_bb_20_dn": float(pd.to_numeric(row.get("bb20_dn"), errors="coerce")),
            }
        except Exception as exc:
            logger.exception("Failed to read exported indicator csv for %s: %s", symbol, exc)
            return {}

    @staticmethod
    def _entry_indicator_snapshot(symbol, scorer, df_all):
        """
        Snapshot technical indicators at entry time from 15M frame.
        """
        m15 = df_all.get("15M")
        if m15 is None or m15.empty:
            return {}
        try:
            m15_ind = scorer.trend_mgr.add_indicators(m15)
            if m15_ind is None or m15_ind.empty:
                return {}
            cur = m15_ind.iloc[-1]
            snap = {
                "ind_rsi": float(cur.get("rsi", float("nan"))),
                "ind_adx": float(cur.get("adx", float("nan"))),
                "ind_plus_di": float(cur.get("plus_di", float("nan"))),
                "ind_minus_di": float(cur.get("minus_di", float("nan"))),
                "ind_disparity": float(cur.get("disparity", float("nan"))),
                "ind_ma_20": float(cur.get("ma_20", float("nan"))),
                "ind_ma_60": float(cur.get("ma_60", float("nan"))),
                "ind_ma_120": float(cur.get("ma_120", float("nan"))),
                "ind_ma_240": float(cur.get("ma_240", float("nan"))),
                "ind_ma_480": float(cur.get("ma_480", float("nan"))),
                "ind_bb_20_up": float(cur.get("bb_20_up", float("nan"))),
                "ind_bb_20_mid": float(cur.get("bb_20_mid", float("nan"))),
                "ind_bb_20_dn": float(cur.get("bb_20_dn", float("nan"))),
                "ind_bb_4_up": float(cur.get("bb_4_up", float("nan"))),
                "ind_bb_4_dn": float(cur.get("bb_4_dn", float("nan"))),
            }
            # Fallback/merge from MT5 exported indicator csv if some key values are missing.
            exported = TradingApplication._read_exported_indicator_row(symbol)
            if exported:
                for k, v in exported.items():
                    if k in snap and (pd.isna(snap[k]) or snap[k] == 0.0):
                        if not pd.isna(v):
                            snap[k] = float(v)
            return snap
        except Exception as exc:
            logger.exception("Failed to build entry indicator snapshot: %s", exc)
            return {}

    @staticmethod
    def entry_indicator_snapshot(symbol, scorer, df_all):
        return TradingApplication._entry_indicator_snapshot(symbol, scorer, df_all)

    @staticmethod
    def build_micro_structure_v1_from_ohlcv(
        df,
        *,
        metadata=None,
        lookback: int = 20,
        baseline_lookback: int = 50,
        doji_body_ratio_threshold: float = 0.10,
        retest_tolerance_ratio: float = 0.15,
    ):
        snapshot = _micro_default_snapshot(
            lookback=lookback,
            baseline_lookback=baseline_lookback,
            data_state="NO_DATA",
            anchor_state="UNAVAILABLE",
        )
        if df is None or len(df) == 0:
            return snapshot

        missing_columns = [column for column in _MICRO_REQUIRED_BAR_COLUMNS if column not in df.columns]
        if missing_columns:
            snapshot["data_state"] = "MISSING_COLUMNS"
            return snapshot

        md = dict(metadata or {})
        window_size = min(len(df), max(int(lookback), 1))
        snapshot["window_size"] = int(window_size)
        snapshot["data_state"] = "READY" if len(df) >= int(lookback) else "INSUFFICIENT_BARS"
        recent = df.tail(window_size).copy()

        opens = pd.to_numeric(recent["open"], errors="coerce").fillna(0.0).astype(float)
        highs = pd.to_numeric(recent["high"], errors="coerce").fillna(0.0).astype(float)
        lows = pd.to_numeric(recent["low"], errors="coerce").fillna(0.0).astype(float)
        closes = pd.to_numeric(recent["close"], errors="coerce").fillna(0.0).astype(float)

        total_ranges = (highs - lows).clip(lower=0.0)
        safe_ranges = total_ranges.mask(total_ranges <= 1e-9, 1e-9)
        bodies = (closes - opens).abs()
        upper_wicks = (highs - pd.concat([opens, closes], axis=1).max(axis=1)).clip(lower=0.0)
        lower_wicks = (pd.concat([opens, closes], axis=1).min(axis=1) - lows).clip(lower=0.0)
        close_scale = closes.abs().mask(closes.abs() <= 1e-9, 1e-9)

        body_size_pct_20 = float((bodies / close_scale).mean())
        upper_wick_ratio_20 = float((upper_wicks / safe_ranges).mean())
        lower_wick_ratio_20 = float((lower_wicks / safe_ranges).mean())
        doji_ratio_20 = float(((bodies / safe_ranges) <= float(doji_body_ratio_threshold)).mean())

        current_run, max_run, bull_ratio, bear_ratio = _micro_run_stats(opens, closes)

        if len(df) >= int(window_size) * 2:
            baseline = df.iloc[-(int(window_size) * 2): -int(window_size)].copy()
        else:
            baseline = df.tail(min(len(df), max(int(baseline_lookback), int(window_size)))).copy()
        base_highs = pd.to_numeric(baseline["high"], errors="coerce").fillna(0.0).astype(float)
        base_lows = pd.to_numeric(baseline["low"], errors="coerce").fillna(0.0).astype(float)
        recent_span = float(highs.max() - lows.min()) if not highs.empty else 0.0
        baseline_span = float(base_highs.max() - base_lows.min()) if not base_highs.empty else 0.0
        if baseline_span <= 1e-9:
            baseline_span = _micro_to_float(md.get("recent_range_mean"), recent_span)
        range_compression_ratio_20 = _micro_clamp01(1.0 - _micro_safe_div(recent_span, baseline_span, default=1.0))

        volume_series, volume_source = _micro_select_volume_series(recent)
        volume_baseline = float(volume_series.mean()) if not volume_series.empty else 0.0
        peak_volume = float(volume_series.max()) if not volume_series.empty else 0.0
        current_volume = float(volume_series.iloc[-1]) if not volume_series.empty else 0.0
        volume_burst_ratio_20 = _micro_safe_div(peak_volume, volume_baseline, default=0.0)
        volume_burst_decay_20 = 0.0
        if peak_volume > max(volume_baseline, 1e-9):
            volume_burst_decay_20 = _micro_clamp01(1.0 - _micro_safe_div(current_volume, peak_volume, default=1.0))

        mean_range = float(total_ranges.mean()) if not total_ranges.empty else 0.0
        median_close = float(closes.abs().median()) if not closes.empty else 0.0
        tolerance = max(mean_range * float(retest_tolerance_ratio), median_close * 0.0005, 1e-9)
        swing_high_retest_count_20 = _micro_retest_count(highs, tolerance=tolerance, high_side=True)
        swing_low_retest_count_20 = _micro_retest_count(lows, tolerance=tolerance, high_side=False)

        gap_open = None
        previous_session_close = None
        for key in _MICRO_GAP_OPEN_KEYS:
            if md.get(key) is not None:
                gap_open = _micro_to_float(md.get(key))
                break
        for key in _MICRO_GAP_PREV_CLOSE_KEYS:
            if md.get(key) is not None:
                previous_session_close = _micro_to_float(md.get(key))
                break

        gap_fill_progress = None
        anchor_state = "MISSING_GAP_ANCHOR"
        current_price = float(closes.iloc[-1]) if not closes.empty else 0.0
        if gap_open is not None and previous_session_close is not None:
            gap_fill_progress, anchor_state = _micro_gap_fill_progress(
                current_price=current_price,
                gap_open=gap_open,
                previous_close=previous_session_close,
            )

        snapshot.update(
            {
                "anchor_state": str(anchor_state),
                "body_size_pct_20": float(body_size_pct_20),
                "upper_wick_ratio_20": float(upper_wick_ratio_20),
                "lower_wick_ratio_20": float(lower_wick_ratio_20),
                "doji_ratio_20": float(doji_ratio_20),
                "same_color_run_current": int(current_run),
                "same_color_run_max_20": int(max_run),
                "bull_ratio_20": float(bull_ratio),
                "bear_ratio_20": float(bear_ratio),
                "direction_run_stats": {
                    "current": int(current_run),
                    "max_20": int(max_run),
                    "bull_ratio_20": float(bull_ratio),
                    "bear_ratio_20": float(bear_ratio),
                },
                "range_compression_ratio_20": float(range_compression_ratio_20),
                "volume_source": str(volume_source),
                "volume_burst_ratio_20": float(volume_burst_ratio_20),
                "volume_burst_decay_20": float(volume_burst_decay_20),
                "swing_high_retest_count_20": int(swing_high_retest_count_20),
                "swing_low_retest_count_20": int(swing_low_retest_count_20),
                "gap_fill_progress": None if gap_fill_progress is None else float(gap_fill_progress),
            }
        )
        return snapshot

    @staticmethod
    def build_micro_structure_v1(df, *, metadata=None, lookback: int = 20, baseline_lookback: int = 50):
        return TradingApplication.build_micro_structure_v1_from_ohlcv(
            df,
            metadata=metadata,
            lookback=lookback,
            baseline_lookback=baseline_lookback,
        )

    def fetch_micro_structure_v1(self, symbol, *, metadata=None, count: int = 50):
        df = self.fetch_data(symbol, TIMEFRAME_M1, count=max(int(count), 20))
        return self.build_micro_structure_v1_from_ohlcv(
            df,
            metadata=metadata,
            lookback=20,
            baseline_lookback=max(int(count), 50),
        )

    def fetch_data(self, symbol, tf_const, count=300):
        for _ in range(3):
            rates = self.broker.copy_rates_from_pos(symbol, tf_const, 0, count)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s")
                return df
            time.sleep(0.1)
        return None

    @staticmethod
    def _resolve_runtime_context_current_price(runtime_row: dict | None) -> float | None:
        row = dict(runtime_row or {})
        for key in (
            "current_price",
            "live_price",
            "price",
            "close",
            "current_close",
            "last_price",
            "entry_price",
        ):
            try:
                value = row.get(key)
                if value in (None, ""):
                    continue
                return float(value)
            except Exception:
                continue
        return None

    @staticmethod
    def _extract_runtime_share_state(runtime_row: dict | None) -> dict:
        row = dict(runtime_row or {})
        share_state: dict[str, object] = {}
        for key in (
            "cluster_share_global",
            "cluster_share_symbol",
            "cluster_share_symbol_band",
            "share_context_label_ko",
        ):
            value = row.get(key)
            if value not in (None, ""):
                share_state[str(key)] = value
        return share_state

    def _build_runtime_market_price_snapshot(self, symbol: str) -> dict[str, float]:
        snapshot: dict[str, float] = {}
        symbol_key = str(symbol or "").upper().strip()
        if not symbol_key:
            return snapshot
        if hasattr(self.broker, "copy_rates_from_pos"):
            try:
                frame_m1 = self.fetch_data(symbol_key, TIMEFRAME_M1, count=3)
            except Exception:
                frame_m1 = None
            if frame_m1 is not None and not frame_m1.empty and "close" in frame_m1.columns:
                try:
                    snapshot["current_close"] = float(frame_m1["close"].iloc[-1])
                except Exception:
                    pass
        if hasattr(self.broker, "symbol_info_tick"):
            try:
                tick = self.broker.symbol_info_tick(symbol_key)
            except Exception:
                tick = None
            if tick:
                try:
                    bid = float(getattr(tick, "bid", 0.0) or 0.0)
                except Exception:
                    bid = 0.0
                try:
                    ask = float(getattr(tick, "ask", 0.0) or 0.0)
                except Exception:
                    ask = 0.0
                if bid > 0.0:
                    snapshot["bid"] = float(bid)
                if ask > 0.0:
                    snapshot["ask"] = float(ask)
                if ask > 0.0 and bid > 0.0:
                    snapshot["live_price"] = float((ask + bid) / 2.0)
                elif ask > 0.0:
                    snapshot["live_price"] = float(ask)
                elif bid > 0.0:
                    snapshot["live_price"] = float(bid)
        return snapshot

    def _attach_directional_continuation_accuracy_surface_fields(
        self,
        rows: dict[str, dict] | None,
        report: dict | None,
    ) -> dict[str, dict]:
        enriched_rows: dict[str, dict] = {}
        report_map = dict(report or {})
        for raw_symbol, raw_row in dict(rows or {}).items():
            row = dict(raw_row or {}) if isinstance(raw_row, dict) else {}
            symbol = str(raw_symbol or row.get("symbol", "") or "").upper().strip()
            direction = str(row.get("directional_continuation_overlay_direction", "") or "").upper().strip()
            if symbol and direction in {"UP", "DOWN"}:
                row.update(
                    build_directional_continuation_accuracy_flat_fields_v1(
                        report_map,
                        symbol=symbol,
                        direction=direction,
                    )
                )
            row = self._normalize_execution_diff_surface_fields(row)
            enriched_rows[symbol or str(raw_symbol)] = row
        return enriched_rows

    def _attach_single_directional_continuation_accuracy_surface_fields(
        self,
        row: dict | None,
        report: dict | None = None,
    ) -> dict:
        payload = dict(row or {})
        symbol = str(payload.get("symbol", "") or "").upper().strip()
        direction = str(payload.get("directional_continuation_overlay_direction", "") or "").upper().strip()
        report_map = dict(report or getattr(self, "directional_continuation_accuracy_report_v1", {}) or {})
        if symbol and direction in {"UP", "DOWN"} and report_map:
            payload.update(
                build_directional_continuation_accuracy_flat_fields_v1(
                    report_map,
                    symbol=symbol,
                    direction=direction,
                )
            )
        return payload

    @staticmethod
    def _normalize_execution_diff_surface_fields(row: dict | None) -> dict:
        payload = dict(row or {})
        nested = payload.get("execution_action_diff_v1")
        if not isinstance(nested, dict):
            return payload
        def _missing(value):
            return value is None or value == "" or value == [] or value == {}
        field_map = {
            "execution_diff_original_action_side": "original_action_side",
            "execution_diff_guarded_action_side": "guarded_action_side",
            "execution_diff_promoted_action_side": "promoted_action_side",
            "execution_diff_final_action_side": "final_action_side",
            "execution_diff_changed": "action_changed",
            "execution_diff_guard_applied": "guard_applied",
            "execution_diff_promotion_active": "promotion_active",
            "execution_diff_reason_keys": "action_change_reason_keys",
            "execution_diff_guard_reason_summary": "guard_reason_summary",
            "execution_diff_promotion_reason": "promotion_reason",
            "execution_diff_promotion_suppressed_reason": "promotion_suppressed_reason",
        }
        always_surface_text_fields = {
            "execution_diff_guard_reason_summary",
            "execution_diff_promotion_reason",
            "execution_diff_promotion_suppressed_reason",
        }
        for flat_key, nested_key in field_map.items():
            if _missing(payload.get(flat_key)):
                value = nested.get(nested_key)
                if flat_key in always_surface_text_fields:
                    if value in (None, [], {}):
                        value = ""
                    payload[flat_key] = value
                elif not _missing(value):
                    payload[flat_key] = value
        return payload

    def _hydrate_execution_diff_surface_fields(self, symbol: str, row: dict | None) -> dict:
        payload = dict(row or {})
        source_candidates: list[dict] = []
        previous_rows = getattr(self, "latest_signal_by_symbol", None)
        if isinstance(previous_rows, dict):
            previous_row = previous_rows.get(str(symbol), {})
            if isinstance(previous_row, dict):
                source_candidates.append(dict(previous_row))
        trace_rows = getattr(self, "ai_entry_traces", None)
        if isinstance(trace_rows, list):
            for trace in reversed(trace_rows):
                if not isinstance(trace, dict):
                    continue
                if str(trace.get("symbol", "") or "").upper().strip() != str(symbol).upper().strip():
                    continue
                source_candidates.append(dict(trace))
                break

        def _has_execution_diff_surface(candidate: dict) -> bool:
            if not isinstance(candidate, dict):
                return False
            if isinstance(candidate.get("execution_action_diff_v1"), dict) and candidate.get("execution_action_diff_v1"):
                return True
            return any(
                candidate.get(key) not in (None, "", [], {})
                for key in (
                    "execution_diff_original_action_side",
                    "execution_diff_guarded_action_side",
                    "execution_diff_promoted_action_side",
                    "execution_diff_final_action_side",
                    "execution_diff_changed",
                )
            )

        if not _has_execution_diff_surface(payload):
            for candidate in source_candidates:
                if not _has_execution_diff_surface(candidate):
                    continue
                if isinstance(candidate.get("execution_action_diff_v1"), dict) and candidate.get("execution_action_diff_v1"):
                    payload["execution_action_diff_v1"] = dict(candidate.get("execution_action_diff_v1", {}) or {})
                for key in (
                    "execution_diff_original_action_side",
                    "execution_diff_guarded_action_side",
                    "execution_diff_promoted_action_side",
                    "execution_diff_final_action_side",
                    "execution_diff_changed",
                    "execution_diff_guard_applied",
                    "execution_diff_promotion_active",
                    "execution_diff_reason_keys",
                    "execution_diff_guard_reason_summary",
                    "execution_diff_promotion_reason",
                    "execution_diff_promotion_suppressed_reason",
                ):
                    if payload.get(key) in (None, "", [], {}):
                        value = candidate.get(key)
                        if value not in (None, "", [], {}):
                            payload[key] = value
                break
        return self._normalize_execution_diff_surface_fields(payload)

    def _enrich_runtime_signal_row_with_state_context(
        self,
        symbol: str,
        runtime_row: dict | None,
        *,
        continuation_candidates: list[dict] | None = None,
    ) -> dict:
        row = dict(runtime_row or {})
        symbol_key = str(symbol or row.get("symbol", "") or "").upper().strip()
        if not symbol_key:
            return row

        row.update(self._build_runtime_market_price_snapshot(symbol_key))
        session_bucket_surface = build_runtime_row_session_bucket_surface_v1(row)
        htf_state: dict = {}
        previous_box_state: dict = {}
        share_state = self._extract_runtime_share_state(row)

        if hasattr(self.broker, "copy_rates_from_pos"):
            try:
                htf_state = self._htf_trend_cache.build_htf_state_v1(symbol_key)
            except Exception:
                logger.exception("Failed to build HTF state v1 for %s", symbol_key)
            try:
                frame_15m = self.fetch_data(symbol_key, TIMEFRAME_M15, count=80)
                previous_box_state = self._previous_box_calculator.calculate(
                    frame_15m,
                    symbol=symbol_key,
                    current_price=self._resolve_runtime_context_current_price(row),
                    proxy_state=row,
                )
            except Exception:
                logger.exception("Failed to build previous box state v1 for %s", symbol_key)

        try:
            context_state = build_context_state_v12(
                symbol=symbol_key,
                consumer_check_side=row.get("consumer_check_side"),
                htf_state=htf_state,
                previous_box_state=previous_box_state,
                share_state=share_state,
                proxy_state=row,
            )
        except Exception:
            logger.exception("Failed to build context state v1.2 for %s", symbol_key)
            return row

        enriched = dict(row)
        enriched["session_bucket_surface_v1"] = dict(session_bucket_surface)
        enriched["session_bucket_v1"] = str(session_bucket_surface.get("session_bucket", "") or "")
        enriched["session_bucket_timestamp_source_v1"] = str(
            session_bucket_surface.get("timestamp_source", "") or ""
        )
        enriched.update(context_state)
        bridge_input_row = dict(enriched)
        bridge_input_row["state25_candidate_runtime_v1"] = dict(
            getattr(self, "state25_candidate_runtime_state", {}) or {}
        )
        bridge_payload = build_state25_candidate_context_bridge_v1(bridge_input_row)
        enriched["state25_candidate_context_bridge_v1"] = bridge_payload
        enriched.update(build_state25_candidate_context_bridge_flat_fields_v1(bridge_payload))
        previous_overlay_state = dict(
            (
                (
                    getattr(self, "latest_signal_by_symbol", {}) or {}
                ).get(symbol_key, {}) or {}
            ).get("directional_continuation_overlay_v1", {}) or {}
        )
        try:
            continuation_overlay = build_directional_continuation_chart_overlay_state(
                symbol_key,
                enriched,
                continuation_candidates=continuation_candidates,
                previous_overlay_state=previous_overlay_state,
            )
        except TypeError:
            continuation_overlay = build_directional_continuation_chart_overlay_state(
                symbol_key,
                enriched,
                continuation_candidates=continuation_candidates,
            )
        enriched["directional_continuation_overlay_v1"] = continuation_overlay
        enriched.update(build_directional_continuation_chart_overlay_flat_fields_v1(continuation_overlay))
        if bool(continuation_overlay.get("overlay_enabled", False)):
            enriched["chart_event_kind_hint"] = str(
                continuation_overlay.get("overlay_event_kind_hint", "") or ""
            ).upper()
            enriched["chart_event_reason_hint"] = str(
                continuation_overlay.get("overlay_reason", "")
                or continuation_overlay.get("overlay_summary_ko", "")
                or ""
            )
        else:
            enriched["chart_event_kind_hint"] = ""
            enriched["chart_event_reason_hint"] = ""
        enriched = self._hydrate_execution_diff_surface_fields(symbol_key, enriched)
        enriched = self._attach_single_directional_continuation_accuracy_surface_fields(enriched)
        return enriched

    def _enrich_runtime_signal_rows_with_state_context(self, rows: dict[str, dict] | None) -> dict[str, dict]:
        enriched_rows: dict[str, dict] = {}
        try:
            continuation_candidates = build_directional_continuation_learning_candidates()
        except Exception:
            logger.exception("Failed to build directional continuation learning candidates for runtime rows")
            continuation_candidates = []
        self.directional_continuation_candidates_cache_v1 = list(continuation_candidates or [])
        for symbol, runtime_row in dict(rows or {}).items():
            if not isinstance(runtime_row, dict):
                continue
            enriched_rows[str(symbol)] = self._enrich_runtime_signal_row_with_state_context(
                str(symbol),
                runtime_row,
                continuation_candidates=continuation_candidates,
            )
        return enriched_rows

    def build_chart_painter_runtime_row(
        self,
        symbol: str,
        runtime_row: dict | None,
        *,
        continuation_candidates: list[dict] | None = None,
    ) -> dict:
        return self.build_entry_runtime_signal_row(
            symbol,
            runtime_row,
            continuation_candidates=continuation_candidates,
        )

    def build_entry_runtime_signal_row(
        self,
        symbol: str,
        runtime_row: dict | None,
        *,
        continuation_candidates: list[dict] | None = None,
    ) -> dict:
        row = dict(runtime_row or {})
        try:
            if continuation_candidates is None:
                cached_candidates = getattr(self, "directional_continuation_candidates_cache_v1", None)
                if isinstance(cached_candidates, list) and cached_candidates:
                    continuation_candidates = list(cached_candidates)
                else:
                    try:
                        continuation_candidates = build_directional_continuation_learning_candidates()
                    except Exception:
                        logger.exception(
                            "Failed to build directional continuation learning candidates for entry row %s",
                            symbol,
                        )
                        continuation_candidates = []
                    self.directional_continuation_candidates_cache_v1 = list(continuation_candidates or [])
            return self._enrich_runtime_signal_row_with_state_context(
                str(symbol),
                row,
                continuation_candidates=continuation_candidates,
            )
        except Exception:
            logger.exception("Failed to build entry runtime row for %s", symbol)
            return row

    def execute_order(self, symbol, action, lot):
        if not hasattr(self, "last_order_retcode_by_symbol") or not isinstance(self.last_order_retcode_by_symbol, dict):
            self.last_order_retcode_by_symbol = {}
        if not hasattr(self, "last_order_comment_by_symbol") or not isinstance(self.last_order_comment_by_symbol, dict):
            self.last_order_comment_by_symbol = {}
        if not hasattr(self, "order_block_until_by_symbol") or not isinstance(self.order_block_until_by_symbol, dict):
            self.order_block_until_by_symbol = {}
        if not hasattr(self, "order_block_reason_by_symbol") or not isinstance(self.order_block_reason_by_symbol, dict):
            self.order_block_reason_by_symbol = {}
        tick = self.broker.symbol_info_tick(symbol)
        if not tick:
            return None
        terminal_info = self.broker.terminal_info()
        if terminal_info is not None and not bool(getattr(terminal_info, "trade_allowed", True)):
            self.last_order_error = "AutoTrading disabled by client"
            self.last_order_retcode = None
            self.last_order_comment = "AutoTrading disabled by client"
            logger.warning("Order blocked %s %s lot=%s: %s", symbol, action, lot, self.last_order_error)
            self._obs_inc("orders_failed_total", 1)
            self._obs_event(
                "order_blocked",
                level="warning",
                payload={
                    "symbol": symbol,
                    "action": action,
                    "lot": float(lot),
                    "error": self.last_order_error,
                },
            )
            print("[주문 실패] AutoTrading disabled by client")
            return None

        order_type = ORDER_TYPE_BUY if action == "BUY" else ORDER_TYPE_SELL
        price = tick.ask if action == "BUY" else tick.bid
        sl, tp = self._calc_sl_tp(symbol, action, price)

        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": Config.MAGIC_NUMBER,
            "comment": "AutoTrade",
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp

        result = self.broker.order_send(request)
        if result and result.retcode == TRADE_RETCODE_DONE:
            resolved_ticket = self._resolve_position_ticket_after_entry(
                symbol=symbol,
                action=action,
                result=result,
            )
            self.last_order_ts = time.time()
            self.last_order_error = ""
            self.last_order_retcode = TRADE_RETCODE_DONE
            self.last_order_comment = ""
            self.last_order_retcode_by_symbol[str(symbol)] = TRADE_RETCODE_DONE
            self.last_order_comment_by_symbol[str(symbol)] = ""
            self.order_block_until_by_symbol.pop(str(symbol), None)
            self.order_block_reason_by_symbol.pop(str(symbol), None)
            self._obs_inc("orders_success_total", 1)
            self._obs_event(
                "order_success",
                payload={"symbol": symbol, "action": action, "lot": float(lot), "ticket": int(resolved_ticket or 0)},
            )
            return resolved_ticket

        retcode = getattr(result, "retcode", None) if result else None
        error = result.comment if result else "Unknown"
        symbol_key = str(symbol)
        self.last_order_retcode = retcode
        self.last_order_comment = str(error)
        self.last_order_retcode_by_symbol[symbol_key] = retcode
        self.last_order_comment_by_symbol[symbol_key] = str(error)
        self.last_order_error = f"retcode={retcode}, comment={error}, last_error={self.broker.last_error()}"
        if int(retcode or 0) == 10018 or "market closed" in str(error).lower():
            cooldown_sec = max(0, int(getattr(Config, "ENTRY_MARKET_CLOSED_COOLDOWN_SEC", 300)))
            if cooldown_sec > 0:
                self.order_block_until_by_symbol[symbol_key] = time.time() + float(cooldown_sec)
                self.order_block_reason_by_symbol[symbol_key] = "market_closed"
        logger.warning("Order failed %s %s lot=%s: %s", symbol, action, lot, self.last_order_error)
        self._obs_inc("orders_failed_total", 1)
        self._obs_event(
            "order_failed",
            level="warning",
            payload={
                "symbol": symbol,
                "action": action,
                "lot": float(lot),
                "retcode": retcode,
                "error": str(error),
            },
        )
        print(f"[주문 실패] {error}")
        return None

    def get_order_block_status(self, symbol):
        symbol_key = str(symbol or "")
        expiry = float(self.order_block_until_by_symbol.get(symbol_key, 0.0) or 0.0)
        now = time.time()
        if expiry <= now:
            self.order_block_until_by_symbol.pop(symbol_key, None)
            self.order_block_reason_by_symbol.pop(symbol_key, None)
            return {
                "active": False,
                "reason": "",
                "remaining_sec": 0,
                "retcode": self.last_order_retcode_by_symbol.get(symbol_key),
                "comment": self.last_order_comment_by_symbol.get(symbol_key, ""),
            }
        return {
            "active": True,
            "reason": str(self.order_block_reason_by_symbol.get(symbol_key, "") or ""),
            "remaining_sec": max(0, int(expiry - now)),
            "retcode": self.last_order_retcode_by_symbol.get(symbol_key),
            "comment": self.last_order_comment_by_symbol.get(symbol_key, ""),
        }

    def _resolve_position_ticket_after_entry(self, symbol, action, result):
        raw_ticket = int(getattr(result, "order", 0) or 0)
        raw_position = int(getattr(result, "position", 0) or 0)
        if raw_position > 0:
            return raw_position

        positions_get = getattr(self.broker, "positions_get", None)
        if not callable(positions_get):
            return raw_ticket

        if raw_ticket > 0:
            try:
                positions = positions_get(ticket=raw_ticket) or []
                if positions:
                    return int(getattr(positions[0], "ticket", raw_ticket) or raw_ticket)
            except Exception:
                pass

        direction_type = ORDER_TYPE_BUY if str(action).upper() == "BUY" else ORDER_TYPE_SELL
        deadline = time.time() + 1.5
        best_ticket = raw_ticket
        while time.time() < deadline:
            try:
                positions = positions_get(symbol=symbol) or []
            except Exception:
                break
            candidates = []
            for pos in positions:
                try:
                    pos_type = getattr(pos, "type", -1)
                    if pos_type is None:
                        pos_type = -1
                    if int(pos_type) != int(direction_type):
                        continue
                    magic = int(getattr(pos, "magic", 0) or 0)
                    if magic not in (0, int(Config.MAGIC_NUMBER)):
                        continue
                    ts = int(getattr(pos, "time_msc", 0) or 0) or int(getattr(pos, "time", 0) or 0)
                    candidates.append((ts, int(getattr(pos, "ticket", 0) or 0)))
                except Exception:
                    continue
            if candidates:
                candidates.sort()
                best_ticket = int(candidates[-1][1] or raw_ticket)
                if best_ticket > 0:
                    return best_ticket
            time.sleep(0.15)

        return raw_ticket

    def close_position(self, ticket, reason="Exit"):
        positions = self.broker.positions_get(ticket=ticket)
        if not positions:
            return True

        pos = positions[0]
        tick = self.broker.symbol_info_tick(pos.symbol)
        if not tick:
            return False

        close_type = ORDER_TYPE_SELL if pos.type == ORDER_TYPE_BUY else ORDER_TYPE_BUY
        price = tick.bid if pos.type == ORDER_TYPE_BUY else tick.ask

        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": Config.MAGIC_NUMBER,
            "comment": reason,
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }

        result = self.broker.order_send(request)
        return bool(result and result.retcode == TRADE_RETCODE_DONE)

    def close_position_partial(self, ticket, volume, reason="Partial Exit"):
        positions = self.broker.positions_get(ticket=ticket)
        if not positions:
            return False

        pos = positions[0]
        vol = float(volume or 0.0)
        if vol <= 0.0:
            return False
        if vol > float(pos.volume):
            vol = float(pos.volume)

        tick = self.broker.symbol_info_tick(pos.symbol)
        if not tick:
            return False

        close_type = ORDER_TYPE_SELL if pos.type == ORDER_TYPE_BUY else ORDER_TYPE_BUY
        price = tick.bid if pos.type == ORDER_TYPE_BUY else tick.ask
        request = {
            "action": TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": vol,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": Config.MAGIC_NUMBER,
            "comment": reason,
            "type_time": ORDER_TIME_GTC,
            "type_filling": ORDER_FILLING_IOC,
        }
        result = self.broker.order_send(request)
        return bool(result and result.retcode == TRADE_RETCODE_DONE)

    def move_stop_to_break_even(self, ticket, be_price):
        positions = self.broker.positions_get(ticket=ticket)
        if not positions:
            return False
        pos = positions[0]
        info = self.broker.symbol_info(pos.symbol)
        if not info:
            return False
        tick = self.broker.symbol_info_tick(pos.symbol)
        if not tick:
            return False
        digits = int(getattr(info, "digits", 5) or 5)
        point = float(getattr(info, "point", 0.0) or 0.0)
        stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
        min_stop_dist = max(point * max(1, stops_level), point * 10 if point > 0 else 0.0)
        safety_dist = min_stop_dist * 1.1 if min_stop_dist > 0 else 0.0
        current_sl = float(getattr(pos, "sl", 0.0) or 0.0)
        target_sl = float(be_price)
        if int(pos.type) == int(ORDER_TYPE_BUY):
            max_valid_sl = float(tick.bid) - float(safety_dist)
            if max_valid_sl <= 0.0:
                return False
            target_sl = min(float(target_sl), float(max_valid_sl))
            target_sl = round(float(target_sl), digits)
            if current_sl > 0 and target_sl <= current_sl:
                return False
            if target_sl >= float(tick.bid):
                return False
        else:
            min_valid_sl = float(tick.ask) + float(safety_dist)
            target_sl = max(float(target_sl), float(min_valid_sl))
            target_sl = round(float(target_sl), digits)
            if current_sl > 0 and target_sl >= current_sl:
                return False
            if target_sl <= float(tick.ask):
                return False
        request = {
            "action": TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": int(pos.ticket),
            "sl": target_sl,
            "tp": float(getattr(pos, "tp", 0.0) or 0.0),
            "magic": Config.MAGIC_NUMBER,
            "comment": "Move SL to BE",
        }
        result = self.broker.order_send(request)
        return bool(result and result.retcode == TRADE_RETCODE_DONE)

    @staticmethod
    def calculate_sniper_indicators(df):
        if df is None or len(df) < 20:
            return {"rsi": 50, "bb_up": 0, "bb_dn": 0}

        try:
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            loss = loss.replace(0, 0.00001)
            rsi = 100 - (100 / (1 + gain / loss))

            ma = df["close"].rolling(20).mean()
            std = df["close"].rolling(20).std()

            return {
                "rsi": rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
                "bb_up": (ma + 2 * std).iloc[-1],
                "bb_dn": (ma - 2 * std).iloc[-1],
            }
        except Exception as exc:
            logger.exception("Failed to calculate sniper indicators: %s", exc)
            return {"rsi": 50, "bb_up": 0, "bb_dn": 0}

    def print_dashboard(self, symbol, buy_s, sell_s, rsi, pos_count, active, reason, entry_threshold):
        os.system("cls" if os.name == "nt" else "clear")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rsi_status = "OVERBOUGHT" if rsi > 70 else ("OVERSOLD" if rsi < 30 else "NEUTRAL")
        market_status = "ACTIVE" if active else "INACTIVE"
        runtime_row = {}
        if isinstance(self.latest_signal_by_symbol, dict):
            runtime_row = dict(self.latest_signal_by_symbol.get(symbol, {}) or {})
        if not runtime_row:
            runtime_row = {
                "symbol": str(symbol),
                "is_active": bool(active),
                "inactive_reason": str(reason or ""),
                "buy_score": int(buy_s),
                "sell_score": int(sell_s),
                "entry_threshold": int(entry_threshold),
                "my_position_count": int(pos_count),
            }
        position_surface = build_position_energy_surface_v1(runtime_row)
        legacy_surface = build_legacy_raw_score_surface_v1(runtime_row)
        summary = dict(position_surface.get("summary", {}) or {})
        location = dict(position_surface.get("location", {}) or {})
        position = dict(position_surface.get("position", {}) or {})
        energy = dict(position_surface.get("energy", {}) or {})
        observe = dict(position_surface.get("observe", {}) or {})
        readiness = dict(position_surface.get("readiness", {}) or {})
        legacy_summary = dict(legacy_surface.get("summary", {}) or {})

        print("=" * 92)
        print("AUTO TRADING SYSTEM".center(92))
        print("=" * 92)
        print(f"Time: {now}")
        print(
            f"Symbol: {symbol} | Market: {market_status} | Mode: {position_surface.get('market_mode', '-') or '-'}"
            f" | Policy: {position_surface.get('direction_policy', '-') or '-'}"
        )
        print(
            f"Location: BOX={location.get('box_zone', '-') or '-'} / BB20={location.get('bb20_zone', '-') or '-'}"
            f" / BB44={location.get('bb44_zone', '-') or '-'}"
            f" | Position: {position.get('primary_label', '-') or '-'}"
        )
        print(
            f"Energy : lower {float(energy.get('lower_position_force', 0.0) or 0.0):.2f}"
            f" / upper {float(energy.get('upper_position_force', 0.0) or 0.0):.2f}"
            f" / middle {float(energy.get('middle_neutrality', 0.0) or 0.0):.2f}"
            f" | Bias: {summary.get('energy_bias', '-') or '-'}"
        )
        print(
            f"Observe: {observe.get('action', '-') or '-'} {observe.get('side', '')}".rstrip()
            + f" | Reason: {observe.get('reason', reason) or reason or '-'}"
        )
        print(
            f"Ready  : state={summary.get('decision_state', '-') or '-'}"
            f" / display={bool(readiness.get('display_ready', False))}"
            f" / entry={bool(readiness.get('entry_ready', False))}"
            f" / stage={readiness.get('consumer_stage', '-') or '-'}"
        )
        state_reason = summary.get("state_reason", "") or "-"
        print(f"Reason : {state_reason}")
        if readiness.get("wait_policy_state") or readiness.get("wait_policy_reason"):
            print(
                f"Wait   : {readiness.get('wait_policy_state', '-') or '-'}"
                f" | {readiness.get('wait_policy_reason', '-') or '-'}"
            )
        print(
            f"Legacy : BUY {legacy_surface.get('buy_score', 0):>4}"
            f" / SELL {legacy_surface.get('sell_score', 0):>4}"
            f" / WAIT {legacy_surface.get('wait_score', 0):>4}"
            f" / TH {legacy_surface.get('entry_threshold', 0):>4}"
            f" | raw={legacy_summary.get('dominant_side', '-') or '-'}"
            f" ({legacy_summary.get('threshold_state', '-') or '-'})"
        )
        print("-" * 92)
        print(f"RSI  : {rsi:.1f} ({rsi_status})")
        print(f"Positions: {pos_count}/{Config.MAX_POSITIONS}")
        print("=" * 92)
        print("Press Ctrl+C to stop")

    @staticmethod
    def _score_adjustment(probability, weight):
        return helper_score_adjustment(probability, weight)

    @staticmethod
    def score_adjustment(probability, weight):
        return TradingApplication._score_adjustment(probability, weight)

    @staticmethod
    def _estimate_reason_points(reason: str) -> int:
        return helper_estimate_reason_points(reason)

    @classmethod
    def _build_scored_reasons(cls, reasons, target_total, ai_adj=0):
        return helper_build_scored_reasons(reasons=reasons, target_total=target_total, ai_adj=ai_adj)

    @classmethod
    def build_scored_reasons(cls, reasons, target_total, ai_adj=0):
        return cls._build_scored_reasons(reasons, target_total, ai_adj=ai_adj)

    @classmethod
    def _build_scored_reasons_raw(cls, reasons, ai_adj=0):
        return helper_build_scored_reasons_raw(reasons=reasons, ai_adj=ai_adj)

    @staticmethod
    def _entry_features(symbol, action, score, contra_score, reasons, regime=None, indicators=None, metadata=None):
        return helper_entry_features(
            symbol=symbol,
            action=action,
            score=score,
            contra_score=contra_score,
            reasons=reasons,
            regime=regime,
            indicators=indicators,
            metadata=metadata,
        )

    @staticmethod
    def entry_features(symbol, action, score, contra_score, reasons, regime=None, indicators=None, metadata=None):
        return TradingApplication._entry_features(
            symbol=symbol,
            action=action,
            score=score,
            contra_score=contra_score,
            reasons=reasons,
            regime=regime,
            indicators=indicators,
            metadata=metadata,
        )

    @staticmethod
    def _exit_features(
        symbol,
        direction,
        open_time,
        duration_sec,
        entry_score,
        contra_score,
        exit_score,
        entry_reason,
        exit_reason,
        regime=None,
        trade_ctx=None,
        stage_inputs=None,
        live_metrics=None,
    ):
        return helper_exit_features(
            symbol=symbol,
            direction=direction,
            open_time=open_time,
            duration_sec=duration_sec,
            entry_score=entry_score,
            contra_score=contra_score,
            exit_score=exit_score,
            entry_reason=entry_reason,
            exit_reason=exit_reason,
            regime=regime,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            live_metrics=live_metrics,
        )

    def _allow_ai_exit(
        self,
        symbol,
        direction,
        open_time,
        duration_sec,
        entry_score,
        contra_score,
        exit_score,
        entry_reason,
        exit_reason,
        regime=None,
        trade_ctx=None,
        stage_inputs=None,
        live_metrics=None,
    ):
        if not self.ai_runtime:
            return True
        feat = self._exit_features(
            symbol=symbol,
            direction=direction,
            open_time=open_time,
            duration_sec=duration_sec,
            entry_score=entry_score,
            contra_score=contra_score,
            exit_score=exit_score,
            entry_reason=entry_reason,
            exit_reason=exit_reason,
            regime=regime,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            live_metrics=live_metrics,
        )
        dec = self.ai_runtime.predict_exit(feat, threshold=Config.AI_EXIT_THRESHOLD)
        if not dec.decision:
            print(f"[AI] exit hold {symbol} {exit_reason} p={dec.probability:.3f}")
            return False
        return True

    def allow_ai_exit(
        self,
        symbol,
        direction,
        open_time,
        duration_sec,
        entry_score,
        contra_score,
        exit_score,
        entry_reason,
        exit_reason,
        regime=None,
        trade_ctx=None,
        stage_inputs=None,
        live_metrics=None,
    ):
        return self._allow_ai_exit(
            symbol=symbol,
            direction=direction,
            open_time=open_time,
            duration_sec=duration_sec,
            entry_score=entry_score,
            contra_score=contra_score,
            exit_score=exit_score,
            entry_reason=entry_reason,
            exit_reason=exit_reason,
            regime=regime,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            live_metrics=live_metrics,
        )

    def _exit_reversal_ai_adjustment(
        self,
        symbol,
        direction,
        open_time,
        duration_sec,
        entry_score,
        contra_score,
        exit_score,
        entry_reason,
        regime=None,
        trade_ctx=None,
        stage_inputs=None,
        live_metrics=None,
    ):
        if not self.ai_runtime:
            return 0
        feat = self._exit_features(
            symbol=symbol,
            direction=direction,
            open_time=open_time,
            duration_sec=duration_sec,
            entry_score=entry_score,
            contra_score=contra_score,
            exit_score=exit_score,
            entry_reason=entry_reason,
            exit_reason="Reversal",
            regime=regime,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            live_metrics=live_metrics,
        )
        dec = self.ai_runtime.predict_exit(feat, threshold=Config.AI_EXIT_THRESHOLD)
        ai_adj = self._score_adjustment(dec.probability, Config.AI_EXIT_WEIGHT)
        if not dec.decision:
            ai_adj = min(ai_adj, 0)
        return ai_adj

    def exit_reversal_ai_adjustment(
        self,
        symbol,
        direction,
        open_time,
        duration_sec,
        entry_score,
        contra_score,
        exit_score,
        entry_reason,
        regime=None,
        trade_ctx=None,
        stage_inputs=None,
        live_metrics=None,
    ):
        return self._exit_reversal_ai_adjustment(
            symbol=symbol,
            direction=direction,
            open_time=open_time,
            duration_sec=duration_sec,
            entry_score=entry_score,
            contra_score=contra_score,
            exit_score=exit_score,
            entry_reason=entry_reason,
            regime=regime,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            live_metrics=live_metrics,
        )

    def _write_runtime_status(
        self,
        loop_count,
        symbols,
        entry_threshold,
        exit_threshold,
        adverse_loss_usd=None,
        reverse_signal_threshold=None,
        policy_snapshot=None,
    ):
        try:
            def _json_fallback(obj):
                # Handle numpy/pandas scalars without importing heavy deps here.
                try:
                    if hasattr(obj, "item"):
                        return obj.item()
                except Exception:
                    pass
                return str(obj)

            self.runtime_status_path.parent.mkdir(parents=True, exist_ok=True)
            live_positions = []
            try:
                live_positions = self.broker.positions_get() or []
            except Exception:
                logger.exception("Failed to collect live positions before runtime status export")
            normalized_signal_rows, _, total_open_positions, owned_open_positions = (
                _normalize_runtime_signal_position_counts(
                    self.latest_signal_by_symbol,
                    positions=live_positions,
                    magic_number=int(getattr(Config, "MAGIC_NUMBER", 0)),
                )
            )
            context_enriched_signal_rows = self._enrich_runtime_signal_rows_with_state_context(
                normalized_signal_rows
            )
            context_enriched_signal_rows = _reset_runtime_signal_downstream_derived_fields(
                context_enriched_signal_rows
            )
            continuation_accuracy_report = update_directional_continuation_accuracy_tracker(
                context_enriched_signal_rows
            )
            self.directional_continuation_accuracy_report_v1 = dict(
                continuation_accuracy_report or {}
            )
            context_enriched_signal_rows = self._attach_directional_continuation_accuracy_surface_fields(
                context_enriched_signal_rows,
                continuation_accuracy_report,
            )
            context_enriched_signal_rows = attach_canonical_surface_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            runtime_signal_wiring_audit = generate_and_write_runtime_signal_wiring_audit(
                self.latest_signal_by_symbol,
                ai_entry_traces=self.ai_entry_traces,
                accuracy_report=continuation_accuracy_report,
                write_artifacts=False,
            )
            self.runtime_signal_wiring_audit_report_v1 = dict(runtime_signal_wiring_audit or {})
            ca2_r0_stability_report = generate_and_write_ca2_r0_stability_audit(
                runtime_signal_wiring_audit,
                accuracy_report=continuation_accuracy_report,
            )
            self.ca2_r0_stability_report_v1 = dict(ca2_r0_stability_report or {})
            ca2_session_split_report = generate_and_write_ca2_session_split_audit(
                ai_entry_traces=self.ai_entry_traces,
            )
            self.ca2_session_split_report_v1 = dict(ca2_session_split_report or {})
            should_have_done_candidate_report = generate_and_write_should_have_done_candidate_summary(
                latest_signal_by_symbol=self.latest_signal_by_symbol,
                ai_entry_traces=self.ai_entry_traces,
            )
            self.should_have_done_candidate_report_v1 = dict(should_have_done_candidate_report or {})
            canonical_surface_report = generate_and_write_canonical_surface_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.canonical_surface_report_v1 = dict(canonical_surface_report or {})
            session_aware_annotation_accuracy_report = generate_and_write_session_aware_annotation_accuracy_v1(
                session_split_report=ca2_session_split_report,
                should_have_done_report=should_have_done_candidate_report,
                canonical_surface_report=canonical_surface_report,
            )
            self.session_aware_annotation_accuracy_report_v1 = dict(
                session_aware_annotation_accuracy_report or {}
            )
            context_enriched_signal_rows = attach_session_bias_shadow_fields_v1(
                context_enriched_signal_rows,
                session_aware_annotation_accuracy_report=session_aware_annotation_accuracy_report,
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            session_bias_shadow_report = generate_and_write_session_bias_shadow_report_v1(
                self.latest_signal_by_symbol,
                session_aware_annotation_accuracy_report=session_aware_annotation_accuracy_report,
            )
            self.session_bias_shadow_report_v1 = dict(session_bias_shadow_report or {})
            context_enriched_signal_rows = attach_state_strength_profile_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_strength_summary_report = generate_and_write_state_strength_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.state_strength_summary_report_v1 = dict(state_strength_summary_report or {})
            context_enriched_signal_rows = attach_local_structure_profile_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            local_structure_summary_report = generate_and_write_local_structure_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.local_structure_summary_report_v1 = dict(local_structure_summary_report or {})
            context_enriched_signal_rows = attach_runtime_readonly_surface_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            runtime_readonly_surface_report = generate_and_write_runtime_readonly_surface_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.runtime_readonly_surface_report_v1 = dict(runtime_readonly_surface_report or {})
            context_enriched_signal_rows = attach_state_structure_dominance_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_structure_dominance_report = generate_and_write_state_structure_dominance_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.state_structure_dominance_report_v1 = dict(state_structure_dominance_report or {})
            context_enriched_signal_rows = attach_dominance_validation_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            dominance_validation_report = generate_and_write_dominance_validation_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.dominance_validation_report_v1 = dict(dominance_validation_report or {})
            context_enriched_signal_rows = attach_dominance_accuracy_shadow_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            dominance_accuracy_shadow_report = generate_and_write_dominance_accuracy_shadow_reports_v1(
                self.latest_signal_by_symbol,
            )
            self.dominance_accuracy_shadow_report_v1 = dict(dominance_accuracy_shadow_report or {})
            context_enriched_signal_rows = attach_symbol_specific_state_strength_calibration_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            symbol_specific_state_strength_calibration_report = (
                generate_and_write_symbol_specific_state_strength_calibration_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.symbol_specific_state_strength_calibration_report_v1 = dict(
                symbol_specific_state_strength_calibration_report or {}
            )
            context_enriched_signal_rows = attach_xau_readonly_surface_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            xau_readonly_surface_report = generate_and_write_xau_readonly_surface_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.xau_readonly_surface_report_v1 = dict(xau_readonly_surface_report or {})
            context_enriched_signal_rows = attach_xau_decomposition_validation_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            xau_decomposition_validation_report = generate_and_write_xau_decomposition_validation_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.xau_decomposition_validation_report_v1 = dict(xau_decomposition_validation_report or {})
            state_slot_commonization_judge_report = generate_and_write_state_slot_commonization_judge_summary_v1(
                xau_pilot_mapping_report={
                    "contract": build_xau_pilot_mapping_contract_v1(),
                    "summary": {},
                },
                xau_readonly_surface_report=xau_readonly_surface_report,
                xau_decomposition_validation_report=xau_decomposition_validation_report,
            )
            self.state_slot_commonization_judge_report_v1 = dict(state_slot_commonization_judge_report or {})
            context_enriched_signal_rows = attach_state_slot_execution_interface_bridge_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_slot_execution_interface_bridge_report = (
                generate_and_write_state_slot_execution_interface_bridge_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.state_slot_execution_interface_bridge_report_v1 = dict(
                state_slot_execution_interface_bridge_report or {}
            )
            context_enriched_signal_rows = attach_state_slot_symbol_extension_surface_fields_v1(
                context_enriched_signal_rows,
                state_slot_commonization_judge_report=state_slot_commonization_judge_report,
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_slot_symbol_extension_surface_report = (
                generate_and_write_state_slot_symbol_extension_surface_summary_v1(
                    self.latest_signal_by_symbol,
                    state_slot_commonization_judge_report=state_slot_commonization_judge_report,
                )
            )
            self.state_slot_symbol_extension_surface_report_v1 = dict(
                state_slot_symbol_extension_surface_report or {}
            )
            context_enriched_signal_rows = attach_nas_readonly_surface_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            nas_readonly_surface_report = generate_and_write_nas_readonly_surface_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.nas_readonly_surface_report_v1 = dict(nas_readonly_surface_report or {})
            context_enriched_signal_rows = attach_nas_decomposition_validation_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            nas_decomposition_validation_report = generate_and_write_nas_decomposition_validation_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.nas_decomposition_validation_report_v1 = dict(nas_decomposition_validation_report or {})
            context_enriched_signal_rows = attach_btc_readonly_surface_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            btc_readonly_surface_report = generate_and_write_btc_readonly_surface_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.btc_readonly_surface_report_v1 = dict(btc_readonly_surface_report or {})
            context_enriched_signal_rows = attach_btc_decomposition_validation_fields_v1(context_enriched_signal_rows)
            self.latest_signal_by_symbol = context_enriched_signal_rows
            btc_decomposition_validation_report = generate_and_write_btc_decomposition_validation_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.btc_decomposition_validation_report_v1 = dict(btc_decomposition_validation_report or {})
            context_enriched_signal_rows = attach_state_slot_position_lifecycle_policy_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_slot_position_lifecycle_policy_report = (
                generate_and_write_state_slot_position_lifecycle_policy_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.state_slot_position_lifecycle_policy_report_v1 = dict(
                state_slot_position_lifecycle_policy_report or {}
            )
            context_enriched_signal_rows = attach_execution_policy_shadow_audit_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            execution_policy_shadow_audit_report = generate_and_write_execution_policy_shadow_audit_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.execution_policy_shadow_audit_report_v1 = dict(
                execution_policy_shadow_audit_report or {}
            )
            context_enriched_signal_rows = attach_bounded_lifecycle_canary_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            bounded_lifecycle_canary_report = generate_and_write_bounded_lifecycle_canary_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.bounded_lifecycle_canary_report_v1 = dict(
                bounded_lifecycle_canary_report or {}
            )
            context_enriched_signal_rows = attach_xau_refined_gate_timebox_audit_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            xau_refined_gate_timebox_audit_report = (
                generate_and_write_xau_refined_gate_timebox_audit_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.xau_refined_gate_timebox_audit_report_v1 = dict(
                xau_refined_gate_timebox_audit_report or {}
            )
            context_enriched_signal_rows = attach_state_flow_f0_chain_alignment_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            state_flow_f0_chain_alignment_report = (
                generate_and_write_state_flow_f0_chain_alignment_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.state_flow_f0_chain_alignment_report_v1 = dict(
                state_flow_f0_chain_alignment_report or {}
            )
            context_enriched_signal_rows = attach_flow_structure_gate_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            flow_structure_gate_report = generate_and_write_flow_structure_gate_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.flow_structure_gate_report_v1 = dict(flow_structure_gate_report or {})
            context_enriched_signal_rows = attach_aggregate_directional_flow_metrics_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            aggregate_directional_flow_metrics_report = (
                generate_and_write_aggregate_directional_flow_metrics_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.aggregate_directional_flow_metrics_report_v1 = dict(
                aggregate_directional_flow_metrics_report or {}
            )
            context_enriched_signal_rows = attach_retained_window_flow_calibration_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            retained_window_flow_calibration_report = (
                generate_and_write_retained_window_flow_calibration_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.retained_window_flow_calibration_report_v1 = dict(
                retained_window_flow_calibration_report or {}
            )
            context_enriched_signal_rows = attach_flow_threshold_provisional_band_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            flow_threshold_provisional_band_report = (
                generate_and_write_flow_threshold_provisional_band_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.flow_threshold_provisional_band_report_v1 = dict(
                flow_threshold_provisional_band_report or {}
            )
            context_enriched_signal_rows = attach_exact_pilot_match_bonus_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            exact_pilot_match_bonus_report = (
                generate_and_write_exact_pilot_match_bonus_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.exact_pilot_match_bonus_report_v1 = dict(
                exact_pilot_match_bonus_report or {}
            )
            context_enriched_signal_rows = attach_flow_support_state_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            flow_support_state_report = generate_and_write_flow_support_state_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.flow_support_state_report_v1 = dict(
                flow_support_state_report or {}
            )
            context_enriched_signal_rows = attach_flow_chain_shadow_comparison_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            flow_chain_shadow_comparison_report = generate_and_write_flow_chain_shadow_comparison_summary_v1(
                self.latest_signal_by_symbol,
            )
            self.flow_chain_shadow_comparison_report_v1 = dict(
                flow_chain_shadow_comparison_report or {}
            )
            context_enriched_signal_rows = attach_flow_candidate_improvement_review_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            flow_candidate_improvement_review_report = (
                generate_and_write_flow_candidate_improvement_review_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.flow_candidate_improvement_review_report_v1 = dict(
                flow_candidate_improvement_review_report or {}
            )
            context_enriched_signal_rows = attach_nas_btc_hard_opposed_truth_audit_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            nas_btc_hard_opposed_truth_audit_report = (
                generate_and_write_nas_btc_hard_opposed_truth_audit_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.nas_btc_hard_opposed_truth_audit_report_v1 = dict(
                nas_btc_hard_opposed_truth_audit_report or {}
            )
            context_enriched_signal_rows = attach_recent_rollback_memory_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_bounded_calibration_candidate_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_bounded_candidate_shadow_apply_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_bounded_candidate_evaluation_dashboard_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_bounded_candidate_lifecycle_feedback_loop_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_bounded_candidate_patch_memory_loop_fields_v1(
                context_enriched_signal_rows
            )
            context_enriched_signal_rows = attach_flow_shadow_display_surface_fields_v1(
                context_enriched_signal_rows
            )
            self.latest_signal_by_symbol = context_enriched_signal_rows
            bounded_calibration_candidate_report = (
                generate_and_write_bounded_calibration_candidate_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.bounded_calibration_candidate_report_v1 = dict(
                bounded_calibration_candidate_report or {}
            )
            bounded_candidate_shadow_apply_report = (
                generate_and_write_bounded_candidate_shadow_apply_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.bounded_candidate_shadow_apply_report_v1 = dict(
                bounded_candidate_shadow_apply_report or {}
            )
            bounded_candidate_evaluation_dashboard_report = (
                generate_and_write_bounded_candidate_evaluation_dashboard_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.bounded_candidate_evaluation_dashboard_report_v1 = dict(
                bounded_candidate_evaluation_dashboard_report or {}
            )
            bounded_candidate_lifecycle_feedback_loop_report = (
                generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.bounded_candidate_lifecycle_feedback_loop_report_v1 = dict(
                bounded_candidate_lifecycle_feedback_loop_report or {}
            )
            bounded_candidate_patch_memory_loop_report = (
                generate_and_write_bounded_candidate_patch_memory_loop_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.bounded_candidate_patch_memory_loop_report_v1 = dict(
                bounded_candidate_patch_memory_loop_report or {}
            )
            flow_shadow_display_surface_report = (
                generate_and_write_flow_shadow_display_surface_summary_v1(
                    self.latest_signal_by_symbol,
                )
            )
            self.flow_shadow_display_surface_report_v1 = dict(
                flow_shadow_display_surface_report or {}
            )
            # Flow history sync consumes the final rows, including late chart-event ownership fields.
            flow_history_sync_hook = getattr(self, "runtime_flow_history_sync_hook", None)
            if callable(flow_history_sync_hook):
                try:
                    flow_history_sync_hook(self.latest_signal_by_symbol)
                except Exception:
                    logger.exception("Failed to sync flow history before runtime wiring audit")
            runtime_signal_wiring_audit = generate_and_write_runtime_signal_wiring_audit(
                self.latest_signal_by_symbol,
                ai_entry_traces=self.ai_entry_traces,
                accuracy_report=continuation_accuracy_report,
                write_artifacts=_runtime_signal_wiring_audit_artifact_write_allowed(
                    self.latest_signal_by_symbol,
                    symbols,
                ),
            )
            self.runtime_signal_wiring_audit_report_v1 = dict(runtime_signal_wiring_audit or {})
            ca2_r0_stability_report = generate_and_write_ca2_r0_stability_audit(
                runtime_signal_wiring_audit,
                accuracy_report=continuation_accuracy_report,
            )
            self.ca2_r0_stability_report_v1 = dict(ca2_r0_stability_report or {})
            state_strength_s0_stability_report = generate_and_write_state_strength_s0_stability_report_v1(
                runtime_signal_wiring_audit_report=runtime_signal_wiring_audit,
                ca2_r0_stability_report=ca2_r0_stability_report,
                ca2_session_split_report=ca2_session_split_report,
                should_have_done_report=should_have_done_candidate_report,
                canonical_surface_report=canonical_surface_report,
                session_bias_shadow_report=session_bias_shadow_report,
            )
            self.state_strength_s0_stability_report_v1 = dict(state_strength_s0_stability_report or {})
            state_polarity_d0_stability_report = generate_and_write_state_polarity_d0_stability_report_v1(
                runtime_signal_wiring_audit_report=runtime_signal_wiring_audit,
                ca2_r0_stability_report=ca2_r0_stability_report,
                should_have_done_report=should_have_done_candidate_report,
                canonical_surface_report=canonical_surface_report,
                state_structure_dominance_report=state_structure_dominance_report,
                dominance_accuracy_report={
                    "summary": dict(
                        (dominance_accuracy_shadow_report or {}).get("accuracy_summary", {})
                        if isinstance((dominance_accuracy_shadow_report or {}).get("accuracy_summary", {}), dict)
                        else {}
                    ),
                    "artifact_paths": dict(
                        (dominance_accuracy_shadow_report or {}).get("artifact_paths", {})
                        if isinstance((dominance_accuracy_shadow_report or {}).get("artifact_paths", {}), dict)
                        else {}
                    ),
                },
                symbol_specific_state_strength_calibration_report=symbol_specific_state_strength_calibration_report,
            )
            self.state_polarity_d0_stability_report_v1 = dict(state_polarity_d0_stability_report or {})
            state_polarity_slot_vocabulary_report = generate_and_write_state_polarity_slot_vocabulary_summary_v1()
            self.state_polarity_slot_vocabulary_report_v1 = dict(state_polarity_slot_vocabulary_report or {})
            rejection_split_rule_report = generate_and_write_rejection_split_rule_summary_v1()
            self.rejection_split_rule_report_v1 = dict(rejection_split_rule_report or {})
            continuation_stage_report = generate_and_write_continuation_stage_summary_v1()
            self.continuation_stage_report_v1 = dict(continuation_stage_report or {})
            location_context_report = generate_and_write_location_context_summary_v1()
            self.location_context_report_v1 = dict(location_context_report or {})
            tempo_profile_report = generate_and_write_tempo_profile_summary_v1()
            self.tempo_profile_report_v1 = dict(tempo_profile_report or {})
            ambiguity_modifier_report = generate_and_write_ambiguity_modifier_summary_v1()
            self.ambiguity_modifier_report_v1 = dict(ambiguity_modifier_report or {})
            xau_pilot_mapping_report = generate_and_write_xau_pilot_mapping_summary_v1()
            self.xau_pilot_mapping_report_v1 = dict(xau_pilot_mapping_report or {})
            nas_pilot_mapping_report = generate_and_write_nas_pilot_mapping_summary_v1()
            self.nas_pilot_mapping_report_v1 = dict(nas_pilot_mapping_report or {})
            btc_pilot_mapping_report = generate_and_write_btc_pilot_mapping_summary_v1()
            self.btc_pilot_mapping_report_v1 = dict(btc_pilot_mapping_report or {})
            normalized_runtime_recycle_state = dict(getattr(self, "runtime_recycle_state", {}) or {})
            normalized_runtime_recycle_state["last_open_positions_count"] = int(total_open_positions)
            normalized_runtime_recycle_state["last_owned_open_positions_count"] = int(owned_open_positions)
            self.runtime_recycle_state = normalized_runtime_recycle_state
            recent_runtime_diagnostics = self._build_recent_runtime_diagnostics()
            recent_runtime_summary, default_recent_window = self._build_recent_runtime_summary(recent_runtime_diagnostics)
            recent_exit_runtime_diagnostics = self._build_recent_exit_runtime_diagnostics()
            recent_exit_runtime_summary, default_recent_exit_window = self._build_recent_exit_runtime_summary(
                recent_exit_runtime_diagnostics
            )
            runtime_recycle_health = build_runtime_recycle_health_v1(
                recent_runtime_summary=recent_runtime_summary,
                default_recent_window=default_recent_window,
                latest_signal_by_symbol=self.latest_signal_by_symbol,
                now_ts=time.time(),
                signal_stale_sec=int(getattr(Config, "RUNTIME_RECYCLE_SIGNAL_STALE_SEC", 900) or 900),
            )
            runtime_recycle_drift = build_runtime_recycle_drift_v1(
                recent_runtime_summary=recent_runtime_summary,
                default_recent_window=default_recent_window,
                latest_signal_by_symbol=self.latest_signal_by_symbol,
                now_ts=time.time(),
                min_rows=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_MIN_ROWS", 40) or 40),
                stage_dominance_threshold=float(
                    getattr(Config, "RUNTIME_RECYCLE_DRIFT_STAGE_DOMINANCE", 0.85) or 0.85
                ),
                block_dominance_threshold=float(
                    getattr(Config, "RUNTIME_RECYCLE_DRIFT_BLOCK_DOMINANCE", 0.85) or 0.85
                ),
                decision_dominance_threshold=float(
                    getattr(Config, "RUNTIME_RECYCLE_DRIFT_DECISION_DOMINANCE", 0.90) or 0.90
                ),
                min_signal_count=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_SIGNAL_MIN_COUNT", 2) or 2),
            )
            self.runtime_recent_summary_cache = dict(recent_runtime_summary or {})
            self.runtime_recent_default_window_cache = dict(default_recent_window or {})
            self.runtime_recycle_health_state = dict(runtime_recycle_health or {})
            self.runtime_recycle_drift_state = dict(runtime_recycle_drift or {})
            state25_candidate_runtime_state = dict(
                getattr(self, "state25_candidate_runtime_state", {}) or {}
            )
            state25_candidate_threshold_surface = build_state25_candidate_threshold_surface_v1(
                state25_candidate_runtime_state,
                baseline_entry_threshold=entry_threshold,
            )
            state25_candidate_size_surface = build_state25_candidate_size_surface_v1(
                state25_candidate_runtime_state
            )
            state25_candidate_weight_surface = build_state25_candidate_weight_surface_v1(
                state25_candidate_runtime_state
            )
            semantic_shadow_runtime_export = self._semantic_shadow_runtime_export()
            payload_updated_at = datetime.now(KST).isoformat(timespec="seconds")
            payload = {
                "updated_at": payload_updated_at,
                "generated_at": payload_updated_at,
                "loop_count": int(loop_count),
                "symbols": list(symbols.values()) if isinstance(symbols, dict) else [],
                "entry_threshold": int(entry_threshold),
                "exit_threshold": int(exit_threshold),
                "adverse_loss_usd": float(adverse_loss_usd) if adverse_loss_usd is not None else None,
                "reverse_signal_threshold": (
                    int(reverse_signal_threshold) if reverse_signal_threshold is not None else None
                ),
                "ai_loaded": bool(self.ai_runtime),
                "semantic_shadow_loaded": bool(self.semantic_shadow_runtime),
                "ai_config": {
                    "runtime_enabled": bool(getattr(Config, "AI_RUNTIME_ENABLED", True)),
                    "entry_threshold_prob": float(Config.AI_ENTRY_THRESHOLD),
                    "entry_weight": int(Config.AI_ENTRY_WEIGHT),
                    "entry_filter_enabled": bool(Config.AI_USE_ENTRY_FILTER),
                    "entry_block_prob": float(Config.AI_ENTRY_BLOCK_PROB),
                },
                "semantic_shadow_config": {
                    "model_dir": str(self.semantic_model_dir),
                    "available_targets": list(
                        getattr(self.semantic_shadow_runtime, "available_targets", ()) or ()
                    ),
                    "timing_threshold": float(getattr(Config, "SEMANTIC_TIMING_THRESHOLD", 0.55)),
                    "entry_quality_threshold": float(
                        getattr(Config, "SEMANTIC_ENTRY_QUALITY_THRESHOLD", 0.55)
                    ),
                    "exit_management_threshold": float(
                        getattr(Config, "SEMANTIC_EXIT_MANAGEMENT_THRESHOLD", 0.55)
                    ),
                },
                "semantic_live_config": self._semantic_live_config_payload(),
                "semantic_rollout_state": dict(self.semantic_rollout_state or {}),
                "semantic_shadow_runtime_checked_at": str(
                    semantic_shadow_runtime_export.get("checked_at", "") or ""
                ),
                "semantic_shadow_runtime_model_dir": str(
                    semantic_shadow_runtime_export.get("model_dir", "") or ""
                ),
                "semantic_shadow_runtime_load_error": str(
                    semantic_shadow_runtime_export.get("load_error", "") or ""
                ),
                "recent_summary_window": str(recent_runtime_summary.get("default_window", "") or ""),
                "recent_stage_counts": dict(default_recent_window.get("stage_counts", {}) or {}),
                "recent_blocked_reason_counts": dict(
                    default_recent_window.get("blocked_reason_counts", {}) or {}
                ),
                "recent_symbol_summary": dict(default_recent_window.get("symbol_summary", {}) or {}),
                "recent_wrong_ready_count": int(default_recent_window.get("wrong_ready_count", 0) or 0),
                "recent_display_ready_summary": dict(
                    default_recent_window.get("display_ready_summary", {}) or {}
                ),
                "recent_wait_bias_bundle_summary": dict(
                    default_recent_window.get("wait_bias_bundle_summary", {}) or {}
                ),
                "recent_wait_state_policy_surface_summary": dict(
                    default_recent_window.get("wait_state_policy_surface_summary", {}) or {}
                ),
                "recent_wait_special_scene_summary": dict(
                    default_recent_window.get("wait_special_scene_summary", {}) or {}
                ),
                "recent_wait_threshold_shift_summary": dict(
                    default_recent_window.get("wait_threshold_shift_summary", {}) or {}
                ),
                "recent_wait_state_semantic_summary": dict(
                    default_recent_window.get("wait_state_semantic_summary", {}) or {}
                ),
                "recent_wait_decision_summary": dict(
                    default_recent_window.get("wait_decision_summary", {}) or {}
                ),
                "recent_wait_state_decision_bridge_summary": dict(
                    default_recent_window.get("wait_state_decision_bridge_summary", {}) or {}
                ),
                "recent_exit_summary_window": str(
                    recent_exit_runtime_summary.get("default_window", "") or ""
                ),
                "recent_exit_status_counts": dict(
                    default_recent_exit_window.get("status_counts", {}) or {}
                ),
                "recent_exit_symbol_summary": dict(
                    default_recent_exit_window.get("symbol_summary", {}) or {}
                ),
                "recent_exit_state_semantic_summary": dict(
                    default_recent_exit_window.get("exit_state_semantic_summary", {}) or {}
                ),
                "recent_exit_decision_summary": dict(
                    default_recent_exit_window.get("exit_decision_summary", {}) or {}
                ),
                "recent_exit_state_decision_bridge_summary": dict(
                    default_recent_exit_window.get("exit_state_decision_bridge_summary", {}) or {}
                ),
                "recent_exit_runtime_summary": recent_exit_runtime_summary,
                "recent_exit_runtime_diagnostics": recent_exit_runtime_diagnostics,
                "recent_runtime_summary": recent_runtime_summary,
                "recent_runtime_diagnostics": recent_runtime_diagnostics,
                "runtime_recycle_health_v1": runtime_recycle_health,
                "runtime_recycle_drift_v1": runtime_recycle_drift,
                "directional_continuation_accuracy_summary_v1": dict(
                    (continuation_accuracy_report or {}).get("summary", {})
                    if isinstance((continuation_accuracy_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "directional_continuation_accuracy_artifact_paths": dict(
                    (continuation_accuracy_report or {}).get("artifact_paths", {})
                    if isinstance((continuation_accuracy_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "runtime_signal_wiring_audit_summary_v1": dict(
                    (runtime_signal_wiring_audit or {}).get("summary", {})
                    if isinstance((runtime_signal_wiring_audit or {}).get("summary", {}), dict)
                    else {}
                ),
                "runtime_signal_wiring_audit_artifact_paths": dict(
                    (runtime_signal_wiring_audit or {}).get("artifact_paths", {})
                    if isinstance((runtime_signal_wiring_audit or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "session_bucket_contract_v1": build_session_bucket_contract_v1(),
                "session_direction_annotation_contract_v1": build_session_direction_annotation_contract_v1(),
                "should_have_done_contract_v1": build_should_have_done_contract_v1(),
                "canonical_surface_contract_v1": build_canonical_surface_contract_v1(),
                "session_aware_annotation_accuracy_contract_v1": build_session_aware_annotation_accuracy_contract_v1(),
                "session_bias_shadow_contract_v1": build_session_bias_shadow_contract_v1(),
                "state_strength_profile_contract_v1": build_state_strength_profile_contract_v1(),
                "state_polarity_slot_vocabulary_contract_v1": build_state_polarity_slot_vocabulary_contract_v1(),
                "rejection_split_rule_contract_v1": build_rejection_split_rule_contract_v1(),
                "continuation_stage_contract_v1": build_continuation_stage_contract_v1(),
                "location_context_contract_v1": build_location_context_contract_v1(),
                "tempo_profile_contract_v1": build_tempo_profile_contract_v1(),
                "ambiguity_modifier_contract_v1": build_ambiguity_modifier_contract_v1(),
                "xau_pilot_mapping_contract_v1": build_xau_pilot_mapping_contract_v1(),
                "nas_pilot_mapping_contract_v1": build_nas_pilot_mapping_contract_v1(),
                "btc_pilot_mapping_contract_v1": build_btc_pilot_mapping_contract_v1(),
                "xau_readonly_surface_contract_v1": build_xau_readonly_surface_contract_v1(),
                "nas_readonly_surface_contract_v1": build_nas_readonly_surface_contract_v1(),
                "btc_readonly_surface_contract_v1": build_btc_readonly_surface_contract_v1(),
                "xau_decomposition_validation_contract_v1": build_xau_decomposition_validation_contract_v1(),
                "xau_refined_gate_timebox_audit_contract_v1": (
                    build_xau_refined_gate_timebox_audit_contract_v1()
                ),
                "state_flow_f0_chain_alignment_contract_v1": (
                    build_state_flow_f0_chain_alignment_contract_v1()
                ),
                "flow_structure_gate_contract_v1": build_flow_structure_gate_contract_v1(),
                "aggregate_directional_flow_metrics_contract_v1": (
                    build_aggregate_directional_flow_metrics_contract_v1()
                ),
                "retained_window_flow_calibration_contract_v1": (
                    build_retained_window_flow_calibration_contract_v1()
                ),
                "flow_threshold_provisional_band_contract_v1": (
                    build_flow_threshold_provisional_band_contract_v1()
                ),
                "exact_pilot_match_bonus_contract_v1": (
                    build_exact_pilot_match_bonus_contract_v1()
                ),
                "flow_support_state_contract_v1": (
                    build_flow_support_state_contract_v1()
                ),
                "flow_chain_shadow_comparison_contract_v1": (
                    build_flow_chain_shadow_comparison_contract_v1()
                ),
                "flow_candidate_improvement_review_contract_v1": (
                    build_flow_candidate_improvement_review_contract_v1()
                ),
                "nas_btc_hard_opposed_truth_audit_contract_v1": (
                    build_nas_btc_hard_opposed_truth_audit_contract_v1()
                ),
                "bounded_calibration_candidate_contract_v1": (
                    build_bounded_calibration_candidate_contract_v1()
                ),
                "bounded_candidate_shadow_apply_contract_v1": (
                    build_bounded_candidate_shadow_apply_contract_v1()
                ),
                "bounded_candidate_evaluation_dashboard_contract_v1": (
                    build_bounded_candidate_evaluation_dashboard_contract_v1()
                ),
                "bounded_candidate_lifecycle_feedback_loop_contract_v1": (
                    build_bounded_candidate_lifecycle_feedback_loop_contract_v1()
                ),
                "bounded_candidate_patch_memory_loop_contract_v1": (
                    build_bounded_candidate_patch_memory_loop_contract_v1()
                ),
                "flow_shadow_display_surface_contract_v1": (
                    build_flow_shadow_display_surface_contract_v1()
                ),
                "nas_decomposition_validation_contract_v1": build_nas_decomposition_validation_contract_v1(),
                "btc_decomposition_validation_contract_v1": build_btc_decomposition_validation_contract_v1(),
                "state_slot_commonization_judge_contract_v1": build_state_slot_commonization_judge_contract_v1(),
                "state_slot_execution_interface_bridge_contract_v1": build_state_slot_execution_interface_bridge_contract_v1(),
                "state_slot_symbol_extension_surface_contract_v1": (
                    build_state_slot_symbol_extension_surface_contract_v1()
                ),
                "state_slot_position_lifecycle_policy_contract_v1": (
                    build_state_slot_position_lifecycle_policy_contract_v1()
                ),
                "execution_policy_shadow_audit_contract_v1": build_execution_policy_shadow_audit_contract_v1(),
                "bounded_lifecycle_canary_contract_v1": build_bounded_lifecycle_canary_contract_v1(),
                "local_structure_profile_contract_v1": build_local_structure_profile_contract_v1(),
                "runtime_readonly_surface_contract_v1": build_runtime_readonly_surface_contract_v1(),
                "state_structure_dominance_contract_v1": build_state_structure_dominance_contract_v1(),
                "dominance_validation_contract_v1": build_dominance_validation_contract_v1(),
                "dominance_accuracy_shadow_contract_v1": build_dominance_accuracy_shadow_contract_v1(),
                "symbol_specific_state_strength_calibration_contract_v1": (
                    build_symbol_specific_state_strength_calibration_contract_v1()
                ),
                "ca2_r0_stability_summary_v1": dict(
                    (ca2_r0_stability_report or {}).get("summary", {})
                    if isinstance((ca2_r0_stability_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "ca2_r0_stability_artifact_paths": dict(
                    (ca2_r0_stability_report or {}).get("artifact_paths", {})
                    if isinstance((ca2_r0_stability_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "ca2_session_split_summary_v1": dict(
                    (ca2_session_split_report or {}).get("summary", {})
                    if isinstance((ca2_session_split_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "ca2_session_split_artifact_paths": dict(
                    (ca2_session_split_report or {}).get("artifact_paths", {})
                    if isinstance((ca2_session_split_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "should_have_done_summary_v1": dict(
                    (should_have_done_candidate_report or {}).get("summary", {})
                    if isinstance((should_have_done_candidate_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "should_have_done_artifact_paths": dict(
                    (should_have_done_candidate_report or {}).get("artifact_paths", {})
                    if isinstance((should_have_done_candidate_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "canonical_surface_summary_v1": dict(
                    (canonical_surface_report or {}).get("summary", {})
                    if isinstance((canonical_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "canonical_surface_artifact_paths": dict(
                    (canonical_surface_report or {}).get("artifact_paths", {})
                    if isinstance((canonical_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "session_aware_annotation_accuracy_summary_v1": dict(
                    (session_aware_annotation_accuracy_report or {}).get("summary", {})
                    if isinstance((session_aware_annotation_accuracy_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "session_aware_annotation_accuracy_artifact_paths": dict(
                    (session_aware_annotation_accuracy_report or {}).get("artifact_paths", {})
                    if isinstance((session_aware_annotation_accuracy_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "session_bias_shadow_summary_v1": dict(
                    (session_bias_shadow_report or {}).get("summary", {})
                    if isinstance((session_bias_shadow_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "session_bias_shadow_artifact_paths": dict(
                    (session_bias_shadow_report or {}).get("artifact_paths", {})
                    if isinstance((session_bias_shadow_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_strength_summary_v1": dict(
                    (state_strength_summary_report or {}).get("summary", {})
                    if isinstance((state_strength_summary_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_strength_artifact_paths": dict(
                    (state_strength_summary_report or {}).get("artifact_paths", {})
                    if isinstance((state_strength_summary_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "local_structure_summary_v1": dict(
                    (local_structure_summary_report or {}).get("summary", {})
                    if isinstance((local_structure_summary_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "local_structure_artifact_paths": dict(
                    (local_structure_summary_report or {}).get("artifact_paths", {})
                    if isinstance((local_structure_summary_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "runtime_readonly_surface_summary_v1": dict(
                    (runtime_readonly_surface_report or {}).get("summary", {})
                    if isinstance((runtime_readonly_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "runtime_readonly_surface_artifact_paths": dict(
                    (runtime_readonly_surface_report or {}).get("artifact_paths", {})
                    if isinstance((runtime_readonly_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_structure_dominance_summary_v1": dict(
                    (state_structure_dominance_report or {}).get("summary", {})
                    if isinstance((state_structure_dominance_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_structure_dominance_artifact_paths": dict(
                    (state_structure_dominance_report or {}).get("artifact_paths", {})
                    if isinstance((state_structure_dominance_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "dominance_validation_summary_v1": dict(
                    (dominance_validation_report or {}).get("summary", {})
                    if isinstance((dominance_validation_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "dominance_validation_artifact_paths": dict(
                    (dominance_validation_report or {}).get("artifact_paths", {})
                    if isinstance((dominance_validation_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "dominance_accuracy_summary_v1": dict(
                    (dominance_accuracy_shadow_report or {}).get("accuracy_summary", {})
                    if isinstance((dominance_accuracy_shadow_report or {}).get("accuracy_summary", {}), dict)
                    else {}
                ),
                "dominance_candidate_shadow_report_v1": dict(
                    (dominance_accuracy_shadow_report or {}).get("shadow_summary", {})
                    if isinstance((dominance_accuracy_shadow_report or {}).get("shadow_summary", {}), dict)
                    else {}
                ),
                "dominance_accuracy_shadow_artifact_paths": dict(
                    (dominance_accuracy_shadow_report or {}).get("artifact_paths", {})
                    if isinstance((dominance_accuracy_shadow_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "symbol_specific_state_strength_calibration_summary_v1": dict(
                    (symbol_specific_state_strength_calibration_report or {}).get("summary", {})
                    if isinstance((symbol_specific_state_strength_calibration_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "symbol_specific_state_strength_calibration_artifact_paths": dict(
                    (symbol_specific_state_strength_calibration_report or {}).get("artifact_paths", {})
                    if isinstance(
                        (symbol_specific_state_strength_calibration_report or {}).get("artifact_paths", {}),
                        dict,
                    )
                    else {}
                ),
                "state_strength_s0_stability_summary_v1": dict(
                    (state_strength_s0_stability_report or {}).get("summary", {})
                    if isinstance((state_strength_s0_stability_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_strength_s0_stability_artifact_paths": dict(
                    (state_strength_s0_stability_report or {}).get("artifact_paths", {})
                    if isinstance((state_strength_s0_stability_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_polarity_d0_stability_summary_v1": dict(
                    (state_polarity_d0_stability_report or {}).get("summary", {})
                    if isinstance((state_polarity_d0_stability_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_polarity_d0_stability_artifact_paths": dict(
                    (state_polarity_d0_stability_report or {}).get("artifact_paths", {})
                    if isinstance((state_polarity_d0_stability_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_polarity_slot_vocabulary_summary_v1": dict(
                    (state_polarity_slot_vocabulary_report or {}).get("summary", {})
                    if isinstance((state_polarity_slot_vocabulary_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_polarity_slot_vocabulary_artifact_paths": dict(
                    (state_polarity_slot_vocabulary_report or {}).get("artifact_paths", {})
                    if isinstance((state_polarity_slot_vocabulary_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "rejection_split_rule_summary_v1": dict(
                    (rejection_split_rule_report or {}).get("summary", {})
                    if isinstance((rejection_split_rule_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "rejection_split_rule_artifact_paths": dict(
                    (rejection_split_rule_report or {}).get("artifact_paths", {})
                    if isinstance((rejection_split_rule_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "continuation_stage_summary_v1": dict(
                    (continuation_stage_report or {}).get("summary", {})
                    if isinstance((continuation_stage_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "continuation_stage_artifact_paths": dict(
                    (continuation_stage_report or {}).get("artifact_paths", {})
                    if isinstance((continuation_stage_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "location_context_summary_v1": dict(
                    (location_context_report or {}).get("summary", {})
                    if isinstance((location_context_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "location_context_artifact_paths": dict(
                    (location_context_report or {}).get("artifact_paths", {})
                    if isinstance((location_context_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "tempo_profile_summary_v1": dict(
                    (tempo_profile_report or {}).get("summary", {})
                    if isinstance((tempo_profile_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "tempo_profile_artifact_paths": dict(
                    (tempo_profile_report or {}).get("artifact_paths", {})
                    if isinstance((tempo_profile_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "ambiguity_modifier_summary_v1": dict(
                    (ambiguity_modifier_report or {}).get("summary", {})
                    if isinstance((ambiguity_modifier_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "ambiguity_modifier_artifact_paths": dict(
                    (ambiguity_modifier_report or {}).get("artifact_paths", {})
                    if isinstance((ambiguity_modifier_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "xau_pilot_mapping_summary_v1": dict(
                    (xau_pilot_mapping_report or {}).get("summary", {})
                    if isinstance((xau_pilot_mapping_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "xau_pilot_mapping_artifact_paths": dict(
                    (xau_pilot_mapping_report or {}).get("artifact_paths", {})
                    if isinstance((xau_pilot_mapping_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "nas_pilot_mapping_summary_v1": dict(
                    (nas_pilot_mapping_report or {}).get("summary", {})
                    if isinstance((nas_pilot_mapping_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "nas_pilot_mapping_artifact_paths": dict(
                    (nas_pilot_mapping_report or {}).get("artifact_paths", {})
                    if isinstance((nas_pilot_mapping_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "btc_pilot_mapping_summary_v1": dict(
                    (btc_pilot_mapping_report or {}).get("summary", {})
                    if isinstance((btc_pilot_mapping_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "btc_pilot_mapping_artifact_paths": dict(
                    (btc_pilot_mapping_report or {}).get("artifact_paths", {})
                    if isinstance((btc_pilot_mapping_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "xau_readonly_surface_summary_v1": dict(
                    (xau_readonly_surface_report or {}).get("summary", {})
                    if isinstance((xau_readonly_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "xau_readonly_surface_artifact_paths": dict(
                    (xau_readonly_surface_report or {}).get("artifact_paths", {})
                    if isinstance((xau_readonly_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "nas_readonly_surface_summary_v1": dict(
                    (nas_readonly_surface_report or {}).get("summary", {})
                    if isinstance((nas_readonly_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "nas_readonly_surface_artifact_paths": dict(
                    (nas_readonly_surface_report or {}).get("artifact_paths", {})
                    if isinstance((nas_readonly_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "btc_readonly_surface_summary_v1": dict(
                    (btc_readonly_surface_report or {}).get("summary", {})
                    if isinstance((btc_readonly_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "btc_readonly_surface_artifact_paths": dict(
                    (btc_readonly_surface_report or {}).get("artifact_paths", {})
                    if isinstance((btc_readonly_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "xau_decomposition_validation_summary_v1": dict(
                    (xau_decomposition_validation_report or {}).get("summary", {})
                    if isinstance((xau_decomposition_validation_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "xau_decomposition_validation_artifact_paths": dict(
                    (xau_decomposition_validation_report or {}).get("artifact_paths", {})
                    if isinstance((xau_decomposition_validation_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "xau_refined_gate_timebox_audit_summary_v1": dict(
                    (xau_refined_gate_timebox_audit_report or {}).get("summary", {})
                    if isinstance((xau_refined_gate_timebox_audit_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "xau_refined_gate_timebox_audit_artifact_paths": dict(
                    (xau_refined_gate_timebox_audit_report or {}).get("artifact_paths", {})
                    if isinstance((xau_refined_gate_timebox_audit_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_flow_f0_chain_alignment_summary_v1": dict(
                    (state_flow_f0_chain_alignment_report or {}).get("summary", {})
                    if isinstance((state_flow_f0_chain_alignment_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_flow_f0_chain_alignment_artifact_paths": dict(
                    (state_flow_f0_chain_alignment_report or {}).get("artifact_paths", {})
                    if isinstance((state_flow_f0_chain_alignment_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_structure_gate_summary_v1": dict(
                    (flow_structure_gate_report or {}).get("summary", {})
                    if isinstance((flow_structure_gate_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_structure_gate_artifact_paths": dict(
                    (flow_structure_gate_report or {}).get("artifact_paths", {})
                    if isinstance((flow_structure_gate_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "aggregate_directional_flow_metrics_summary_v1": dict(
                    (aggregate_directional_flow_metrics_report or {}).get("summary", {})
                    if isinstance((aggregate_directional_flow_metrics_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "aggregate_directional_flow_metrics_artifact_paths": dict(
                    (aggregate_directional_flow_metrics_report or {}).get("artifact_paths", {})
                    if isinstance((aggregate_directional_flow_metrics_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "retained_window_flow_calibration_summary_v1": dict(
                    (retained_window_flow_calibration_report or {}).get("summary", {})
                    if isinstance((retained_window_flow_calibration_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "retained_window_flow_calibration_artifact_paths": dict(
                    (retained_window_flow_calibration_report or {}).get("artifact_paths", {})
                    if isinstance((retained_window_flow_calibration_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_threshold_provisional_band_summary_v1": dict(
                    (flow_threshold_provisional_band_report or {}).get("summary", {})
                    if isinstance((flow_threshold_provisional_band_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_threshold_provisional_band_artifact_paths": dict(
                    (flow_threshold_provisional_band_report or {}).get("artifact_paths", {})
                    if isinstance((flow_threshold_provisional_band_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "exact_pilot_match_bonus_summary_v1": dict(
                    (exact_pilot_match_bonus_report or {}).get("summary", {})
                    if isinstance((exact_pilot_match_bonus_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "exact_pilot_match_bonus_artifact_paths": dict(
                    (exact_pilot_match_bonus_report or {}).get("artifact_paths", {})
                    if isinstance((exact_pilot_match_bonus_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_support_state_summary_v1": dict(
                    (flow_support_state_report or {}).get("summary", {})
                    if isinstance((flow_support_state_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_support_state_artifact_paths": dict(
                    (flow_support_state_report or {}).get("artifact_paths", {})
                    if isinstance((flow_support_state_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_chain_shadow_comparison_summary_v1": dict(
                    (flow_chain_shadow_comparison_report or {}).get("summary", {})
                    if isinstance((flow_chain_shadow_comparison_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_chain_shadow_comparison_artifact_paths": dict(
                    (flow_chain_shadow_comparison_report or {}).get("artifact_paths", {})
                    if isinstance((flow_chain_shadow_comparison_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_candidate_improvement_review_summary_v1": dict(
                    (flow_candidate_improvement_review_report or {}).get("summary", {})
                    if isinstance((flow_candidate_improvement_review_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_candidate_improvement_review_artifact_paths": dict(
                    (flow_candidate_improvement_review_report or {}).get("artifact_paths", {})
                    if isinstance((flow_candidate_improvement_review_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "nas_btc_hard_opposed_truth_audit_summary_v1": dict(
                    (nas_btc_hard_opposed_truth_audit_report or {}).get("summary", {})
                    if isinstance((nas_btc_hard_opposed_truth_audit_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "nas_btc_hard_opposed_truth_audit_artifact_paths": dict(
                    (nas_btc_hard_opposed_truth_audit_report or {}).get("artifact_paths", {})
                    if isinstance((nas_btc_hard_opposed_truth_audit_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_calibration_candidate_summary_v1": dict(
                    (bounded_calibration_candidate_report or {}).get("summary", {})
                    if isinstance((bounded_calibration_candidate_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_calibration_candidate_artifact_paths": dict(
                    (bounded_calibration_candidate_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_calibration_candidate_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_candidate_shadow_apply_summary_v1": dict(
                    (bounded_candidate_shadow_apply_report or {}).get("summary", {})
                    if isinstance((bounded_candidate_shadow_apply_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_candidate_shadow_apply_artifact_paths": dict(
                    (bounded_candidate_shadow_apply_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_candidate_shadow_apply_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_candidate_evaluation_dashboard_summary_v1": dict(
                    (bounded_candidate_evaluation_dashboard_report or {}).get("summary", {})
                    if isinstance((bounded_candidate_evaluation_dashboard_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_candidate_evaluation_dashboard_artifact_paths": dict(
                    (bounded_candidate_evaluation_dashboard_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_candidate_evaluation_dashboard_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_candidate_lifecycle_feedback_loop_summary_v1": dict(
                    (bounded_candidate_lifecycle_feedback_loop_report or {}).get("summary", {})
                    if isinstance((bounded_candidate_lifecycle_feedback_loop_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_candidate_lifecycle_feedback_loop_artifact_paths": dict(
                    (bounded_candidate_lifecycle_feedback_loop_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_candidate_lifecycle_feedback_loop_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_candidate_patch_memory_loop_summary_v1": dict(
                    (bounded_candidate_patch_memory_loop_report or {}).get("summary", {})
                    if isinstance((bounded_candidate_patch_memory_loop_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_candidate_patch_memory_loop_artifact_paths": dict(
                    (bounded_candidate_patch_memory_loop_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_candidate_patch_memory_loop_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "flow_shadow_display_surface_summary_v1": dict(
                    (flow_shadow_display_surface_report or {}).get("summary", {})
                    if isinstance((flow_shadow_display_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "flow_shadow_display_surface_artifact_paths": dict(
                    (flow_shadow_display_surface_report or {}).get("artifact_paths", {})
                    if isinstance((flow_shadow_display_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "nas_decomposition_validation_summary_v1": dict(
                    (nas_decomposition_validation_report or {}).get("summary", {})
                    if isinstance((nas_decomposition_validation_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "nas_decomposition_validation_artifact_paths": dict(
                    (nas_decomposition_validation_report or {}).get("artifact_paths", {})
                    if isinstance((nas_decomposition_validation_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "btc_decomposition_validation_summary_v1": dict(
                    (btc_decomposition_validation_report or {}).get("summary", {})
                    if isinstance((btc_decomposition_validation_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "btc_decomposition_validation_artifact_paths": dict(
                    (btc_decomposition_validation_report or {}).get("artifact_paths", {})
                    if isinstance((btc_decomposition_validation_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_slot_commonization_judge_summary_v1": dict(
                    (state_slot_commonization_judge_report or {}).get("summary", {})
                    if isinstance((state_slot_commonization_judge_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_slot_commonization_judge_artifact_paths": dict(
                    (state_slot_commonization_judge_report or {}).get("artifact_paths", {})
                    if isinstance((state_slot_commonization_judge_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_slot_execution_interface_bridge_summary_v1": dict(
                    (state_slot_execution_interface_bridge_report or {}).get("summary", {})
                    if isinstance((state_slot_execution_interface_bridge_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_slot_execution_interface_bridge_artifact_paths": dict(
                    (state_slot_execution_interface_bridge_report or {}).get("artifact_paths", {})
                    if isinstance((state_slot_execution_interface_bridge_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_slot_symbol_extension_surface_summary_v1": dict(
                    (state_slot_symbol_extension_surface_report or {}).get("summary", {})
                    if isinstance((state_slot_symbol_extension_surface_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_slot_symbol_extension_surface_artifact_paths": dict(
                    (state_slot_symbol_extension_surface_report or {}).get("artifact_paths", {})
                    if isinstance((state_slot_symbol_extension_surface_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "state_slot_position_lifecycle_policy_summary_v1": dict(
                    (state_slot_position_lifecycle_policy_report or {}).get("summary", {})
                    if isinstance((state_slot_position_lifecycle_policy_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "state_slot_position_lifecycle_policy_artifact_paths": dict(
                    (state_slot_position_lifecycle_policy_report or {}).get("artifact_paths", {})
                    if isinstance((state_slot_position_lifecycle_policy_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "execution_policy_shadow_audit_summary_v1": dict(
                    (execution_policy_shadow_audit_report or {}).get("summary", {})
                    if isinstance((execution_policy_shadow_audit_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "execution_policy_shadow_audit_artifact_paths": dict(
                    (execution_policy_shadow_audit_report or {}).get("artifact_paths", {})
                    if isinstance((execution_policy_shadow_audit_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "bounded_lifecycle_canary_summary_v1": dict(
                    (bounded_lifecycle_canary_report or {}).get("summary", {})
                    if isinstance((bounded_lifecycle_canary_report or {}).get("summary", {}), dict)
                    else {}
                ),
                "bounded_lifecycle_canary_artifact_paths": dict(
                    (bounded_lifecycle_canary_report or {}).get("artifact_paths", {})
                    if isinstance((bounded_lifecycle_canary_report or {}).get("artifact_paths", {}), dict)
                    else {}
                ),
                "semantic_shadow_runtime_diagnostics": semantic_shadow_runtime_export,
                "ai_entry_traces": self.ai_entry_traces[-30:],
                "last_order_ts": self.last_order_ts,
                "last_order_error": self.last_order_error,
                "last_order_retcode": self.last_order_retcode,
                "last_order_comment": self.last_order_comment,
                "order_block_by_symbol": {
                    str(symbol): {
                        "reason": str(self.order_block_reason_by_symbol.get(str(symbol), "") or ""),
                        "remaining_sec": max(0, int(float(expiry) - time.time())),
                    }
                    for symbol, expiry in self.order_block_until_by_symbol.items()
                    if float(expiry or 0.0) > time.time()
                },
                "pending_reverse_by_symbol": self._export_pending_reverse_by_symbol(),
                "market_regime_by_symbol": self.latest_regime_by_symbol,
                "latest_signal_by_symbol": {
                    str(symbol): enrich_runtime_signal_surface_v1(row)
                    for symbol, row in context_enriched_signal_rows.items()
                    if isinstance(row, dict)
                },
                "loop_debug_state": self.loop_debug_state,
                "state25_candidate_runtime_v1": state25_candidate_runtime_state,
                "state25_candidate_threshold_surface_v1": state25_candidate_threshold_surface,
                "state25_candidate_size_surface_v1": state25_candidate_size_surface,
                "state25_candidate_weight_surface_v1": state25_candidate_weight_surface,
                "runtime_recycle": export_runtime_recycle_state(normalized_runtime_recycle_state),
            }
            if isinstance(policy_snapshot, dict):
                payload["policy_snapshot"] = policy_snapshot
            slim_payload = dict(payload)
            slim_payload["detail_schema_version"] = RUNTIME_STATUS_DETAIL_SCHEMA_VERSION
            slim_payload["detail_payload_path"] = self.runtime_status_detail_path.name
            slim_payload["pending_reverse_by_symbol"] = dict(payload.get("pending_reverse_by_symbol", {}) or {})
            slim_payload["latest_signal_by_symbol"] = {
                str(symbol): compact_runtime_signal_row(row)
                for symbol, row in context_enriched_signal_rows.items()
                if isinstance(row, dict)
            }
            slim_payload.pop("recent_runtime_diagnostics", None)
            slim_payload.pop("recent_exit_runtime_diagnostics", None)
            slim_payload.pop("semantic_shadow_runtime_diagnostics", None)
            self.runtime_status_detail_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=_json_fallback),
                encoding="utf-8",
            )
            self.runtime_status_path.write_text(
                json.dumps(slim_payload, ensure_ascii=False, indent=2, default=_json_fallback),
                encoding="utf-8",
            )
            self.semantic_rollout_manifest_path.parent.mkdir(parents=True, exist_ok=True)
            self.semantic_rollout_manifest_path.write_text(
                json.dumps(
                    {
                        "updated_at": payload["updated_at"],
                        "contract_version": SEMANTIC_LIVE_ROLLOUT_VERSION,
                        "semantic_live_config": payload["semantic_live_config"],
                        "semantic_rollout_state": payload["semantic_rollout_state"],
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=_json_fallback,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.exception("Failed to write runtime status: %s", exc)

    def refresh_state25_candidate_runtime_state(self) -> dict:
        self.state25_candidate_runtime_state = load_state25_candidate_runtime_state(
            getattr(self, "state25_active_candidate_state_path", ""),
            current_state=getattr(self, "state25_candidate_runtime_state", {}),
        )
        return dict(self.state25_candidate_runtime_state or {})

    def _write_loop_debug(self, *, loop_count: int, stage: str, symbol: str = "", detail: str = "") -> None:
        try:
            payload = {
                "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
                "loop_count": int(loop_count),
                "stage": str(stage or ""),
                "symbol": str(symbol or ""),
                "detail": str(detail or ""),
            }
            self.loop_debug_state = dict(payload)
            self.runtime_loop_debug_path.parent.mkdir(parents=True, exist_ok=True)
            self.runtime_loop_debug_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.exception("Failed to write loop debug state: %s", exc)

    @staticmethod
    def _print_startup_symbols(symbols: dict):
        print(f"\n[시작] 감시 심볼: {list(symbols.values())}\n")

    def _build_exit_detail(self, opposite_reasons, exit_signal_score, trade_logger, ticket):
        """Build and persist live exit-side reason context for manual/auto exits."""
        live_scored = self._build_scored_reasons_raw(
            opposite_reasons,
            ai_adj=0,
        )
        detail_score = 0
        for s in live_scored:
            detail_score += int(self._estimate_reason_points(s))
        detail_score = int(max(0, detail_score))
        if detail_score <= 0:
            detail_score = int(max(0, self._estimate_reason_points("Trigger: 반대 시그널 임계치")))
        trade_logger.update_live_exit_context(
            ticket,
            reason="Exit Context",
            exit_score=detail_score,
            detail=" | ".join(live_scored[:3]),
        )
        exit_detail = ", ".join(live_scored[:3])
        if not exit_detail:
            fallback_scored = self._build_scored_reasons_raw(["Trigger: 반대 시그널 임계치"], ai_adj=0)
            exit_detail = ", ".join(fallback_scored[:1])
        return exit_detail, detail_score

    def build_exit_detail(self, opposite_reasons, exit_signal_score, trade_logger, ticket):
        return self._build_exit_detail(opposite_reasons, exit_signal_score, trade_logger, ticket)

    def _try_reverse_entry(
        self,
        reverse_action,
        reverse_score,
        reverse_reasons,
        symbol,
        buy_s,
        sell_s,
        tick,
        scorer,
        df_all,
        trade_logger,
    ):
        helper_try_reverse_entry(
            self,
            reverse_action=reverse_action,
            reverse_score=reverse_score,
            reverse_reasons=reverse_reasons,
            symbol=symbol,
            buy_s=buy_s,
            sell_s=sell_s,
            tick=tick,
            scorer=scorer,
            df_all=df_all,
            trade_logger=trade_logger,
        )

    def run(self):
        run_trading_application(self)




