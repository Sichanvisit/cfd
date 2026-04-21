from datetime import datetime

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df
from backend.trading.trade_logger_open_snapshots import upsert_open_snapshots


class _FakeTradeLogger:
    def __init__(self):
        self.df = normalize_trade_df(pd.DataFrame(columns=TRADE_COLUMNS))
        self.active_tickets = set()
        self.synced = None
        self.read_calls = 0
        self.write_calls = 0
        self._open_snapshot_signature_cache = {}

    def _read_open_df_safe(self):
        self.read_calls += 1
        return self.df.copy()

    def _normalize_dataframe(self, df):
        return normalize_trade_df(df)

    def _normalize_entry_stage(self, value):
        return str(value or "balanced").strip().lower()

    def _write_open_df(self, df):
        self.write_calls += 1
        self.df = normalize_trade_df(df)

    def _sync_open_rows_to_store(self, df):
        self.synced = normalize_trade_df(df)

    def _indicator_columns(self):
        return []

    def _ts_to_kst_text(self, _ts):
        return "2026-03-06 12:00:00"

    def _now_kst_dt(self):
        return datetime(2026, 3, 6, 12, 0, 0)


def test_open_snapshot_new_row_keeps_entry_metadata():
    logger = _FakeTradeLogger()

    updated = upsert_open_snapshots(
        logger,
        [
            {
                "ticket": 101,
                "symbol": "BTCUSD",
                "direction": "BUY",
                "lot": 0.01,
                "open_price": 72000.0,
                "entry_reason": "[AUTO] test",
                "entry_stage": "balanced",
                "entry_setup_id": "range_lower_reversal_buy",
                "management_profile_id": "support_hold_profile",
                "invalidation_id": "lower_support_fail",
                "exit_profile": "tight_protect",
                "prediction_bundle": "{\"p\":0.5}",
                "entry_wait_state": "CENTER",
                "decision_row_key": "decision_row_v1|symbol=BTCUSD|anchor=1",
                "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1772766000|hint=BUY",
                "trade_link_key": "trade_link_v1|ticket=101|symbol=BTCUSD|direction=BUY|open_ts=1772766000",
                "replay_row_key": "decision_row_v1|symbol=BTCUSD|anchor=1",
                "signal_age_sec": 12.5,
                "bar_age_sec": 12.5,
                "decision_latency_ms": 180,
                "order_submit_latency_ms": 47,
                "missing_feature_count": 2,
                "data_completeness_ratio": 0.8,
                "used_fallback_count": 1,
                "compatibility_mode": "hybrid",
                "detail_blob_bytes": 4096,
                "snapshot_payload_bytes": 1024,
                "row_payload_bytes": 768,
                "micro_breakout_readiness_state": "READY_BREAKOUT",
                "micro_reversal_risk_state": "LOW_RISK",
                "micro_participation_state": "ACTIVE_PARTICIPATION",
                "micro_gap_context_state": "NO_GAP_CONTEXT",
                "micro_body_size_pct_20": 0.27,
                "micro_doji_ratio_20": 0.15,
                "micro_same_color_run_current": 3,
                "micro_same_color_run_max_20": 5,
                "micro_range_compression_ratio_20": 0.42,
                "micro_volume_burst_ratio_20": 1.9,
                "micro_volume_burst_decay_20": 0.64,
                "micro_gap_fill_progress": 0.0,
                "teacher_pattern_id": 12,
                "teacher_pattern_name": "브레이크아웃 직전",
                "teacher_pattern_group": "C",
                "teacher_pattern_secondary_id": 23,
                "teacher_pattern_secondary_name": "삼각수렴 압축",
                "teacher_direction_bias": "breakout_up",
                "teacher_entry_bias": "wait_then_breakout",
                "teacher_wait_bias": "short_wait",
                "teacher_exit_bias": "hold_runner",
                "teacher_transition_risk": "false_break_risk",
                "teacher_label_confidence": 0.71,
                "teacher_lookback_bars": 20,
                "teacher_label_version": "v2",
                "teacher_label_source": "rule_v2",
                "teacher_label_review_status": "pending",
                "manual_entry_tag": "manual-breakout-retry",
            }
        ],
    )

    assert updated == 1
    row = logger.df.iloc[-1]
    assert row["entry_setup_id"] == "range_lower_reversal_buy"
    assert row["management_profile_id"] == "support_hold_profile"
    assert row["invalidation_id"] == "lower_support_fail"
    assert row["exit_profile"] == "tight_protect"
    assert row["entry_wait_state"] == "CENTER"
    assert row["decision_row_key"] == "decision_row_v1|symbol=BTCUSD|anchor=1"
    assert row["runtime_snapshot_key"].startswith("runtime_signal_row_v1|symbol=BTCUSD")
    assert row["trade_link_key"].startswith("trade_link_v1|ticket=101")
    assert row["replay_row_key"] == "decision_row_v1|symbol=BTCUSD|anchor=1"
    assert row["signal_age_sec"] == 12.5
    assert row["bar_age_sec"] == 12.5
    assert row["decision_latency_ms"] == 180
    assert row["order_submit_latency_ms"] == 47
    assert row["missing_feature_count"] == 2
    assert row["data_completeness_ratio"] == 0.8
    assert row["used_fallback_count"] == 1
    assert row["compatibility_mode"] == "hybrid"
    assert row["detail_blob_bytes"] == 4096
    assert row["snapshot_payload_bytes"] == 1024
    assert row["row_payload_bytes"] == 768
    assert row["micro_breakout_readiness_state"] == "READY_BREAKOUT"
    assert row["micro_reversal_risk_state"] == "LOW_RISK"
    assert row["micro_participation_state"] == "ACTIVE_PARTICIPATION"
    assert row["micro_gap_context_state"] == "NO_GAP_CONTEXT"
    assert row["micro_body_size_pct_20"] == 0.27
    assert row["micro_doji_ratio_20"] == 0.15
    assert row["micro_same_color_run_current"] == 3
    assert row["micro_same_color_run_max_20"] == 5
    assert row["micro_range_compression_ratio_20"] == 0.42
    assert row["micro_volume_burst_ratio_20"] == 1.9
    assert row["micro_volume_burst_decay_20"] == 0.64
    assert row["micro_gap_fill_progress"] == 0.0
    assert row["teacher_pattern_id"] == 12
    assert row["teacher_pattern_name"] == "브레이크아웃 직전"
    assert row["teacher_pattern_group"] == "C"
    assert row["teacher_pattern_secondary_id"] == 23
    assert row["teacher_pattern_secondary_name"] == "삼각수렴 압축"
    assert row["teacher_direction_bias"] == "breakout_up"
    assert row["teacher_entry_bias"] == "wait_then_breakout"
    assert row["teacher_wait_bias"] == "short_wait"
    assert row["teacher_exit_bias"] == "hold_runner"
    assert row["teacher_transition_risk"] == "false_break_risk"
    assert row["teacher_label_confidence"] == 0.71
    assert row["teacher_lookback_bars"] == 20
    assert row["teacher_label_version"] == "v2"
    assert row["teacher_label_source"] == "rule_v2"
    assert row["teacher_label_review_status"] == "pending"
    assert row["manual_entry_tag"] == "manual-breakout-retry"


def test_open_snapshot_update_does_not_blank_existing_metadata():
    logger = _FakeTradeLogger()
    logger.df = normalize_trade_df(
        pd.DataFrame(
            [
                {
                    "ticket": 202,
                    "symbol": "NAS100",
                    "direction": "SELL",
                    "lot": 0.1,
                    "open_time": "2026-03-06 12:00:00",
                    "open_ts": 1772766000,
                    "open_price": 25000.0,
                    "status": "OPEN",
                    "entry_setup_id": "breakout_retest_sell",
                    "management_profile_id": "breakout_hold_profile",
                    "invalidation_id": "breakout_failure",
                    "exit_profile": "hold_then_trail",
                    "prediction_bundle": "{\"x\":1}",
                    "entry_wait_state": "NOISE",
                    "decision_row_key": "decision_row_v1|symbol=NAS100|anchor=202",
                    "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=1772766000|hint=SELL",
                    "trade_link_key": "trade_link_v1|ticket=202|symbol=NAS100|direction=SELL|open_ts=1772766000",
                    "replay_row_key": "decision_row_v1|symbol=NAS100|anchor=202",
                    "signal_age_sec": 9.5,
                    "bar_age_sec": 9.5,
                    "decision_latency_ms": 220,
                    "order_submit_latency_ms": 58,
                    "missing_feature_count": 1,
                    "data_completeness_ratio": 0.9,
                    "used_fallback_count": 1,
                    "compatibility_mode": "hybrid",
                    "detail_blob_bytes": 2048,
                    "snapshot_payload_bytes": 640,
                    "row_payload_bytes": 512,
                    "micro_breakout_readiness_state": "COILED_BREAKOUT",
                    "micro_reversal_risk_state": "MEDIUM_RISK",
                    "micro_participation_state": "THIN_PARTICIPATION",
                    "micro_gap_context_state": "GAP_PARTIAL_FILL",
                    "micro_body_size_pct_20": 0.19,
                    "micro_doji_ratio_20": 0.21,
                    "micro_same_color_run_current": 2,
                    "micro_same_color_run_max_20": 4,
                    "micro_range_compression_ratio_20": 0.31,
                    "micro_volume_burst_ratio_20": 1.4,
                    "micro_volume_burst_decay_20": 0.58,
                    "micro_gap_fill_progress": 0.45,
                    "teacher_pattern_id": 5,
                    "teacher_pattern_name": "Range 반전장",
                    "teacher_pattern_group": "D",
                    "teacher_pattern_secondary_id": 22,
                    "teacher_pattern_secondary_name": "더블탑/바텀",
                    "teacher_direction_bias": "fade_reversal",
                    "teacher_entry_bias": "fade_entry",
                    "teacher_wait_bias": "wait_edge",
                    "teacher_exit_bias": "quick_take",
                    "teacher_transition_risk": "range_false_break",
                    "teacher_label_confidence": 0.66,
                    "teacher_lookback_bars": 20,
                    "teacher_label_version": "v2",
                    "teacher_label_source": "rule_v2",
                    "teacher_label_review_status": "reviewed",
                    "manual_entry_tag": "manual-range-fade",
                }
            ]
        )
    )

    updated = upsert_open_snapshots(
        logger,
        [
            {
                "ticket": 202,
                "symbol": "NAS100",
                "direction": "SELL",
                "lot": 0.1,
                "open_price": 25001.0,
                "entry_reason": "[AUTO] refresh",
                "entry_setup_id": "",
                "management_profile_id": "",
                "invalidation_id": "",
                "exit_profile": "",
                "prediction_bundle": "",
                "entry_wait_state": "",
                "micro_breakout_readiness_state": "",
                "micro_reversal_risk_state": "",
                "micro_participation_state": "",
                "micro_gap_context_state": "",
                "micro_body_size_pct_20": "",
                "micro_doji_ratio_20": "",
                "micro_same_color_run_current": "",
                "micro_same_color_run_max_20": "",
                "micro_range_compression_ratio_20": "",
                "micro_volume_burst_ratio_20": "",
                "micro_volume_burst_decay_20": "",
                "micro_gap_fill_progress": "",
                "teacher_pattern_id": "",
                "teacher_pattern_name": "",
                "teacher_pattern_group": "",
                "teacher_pattern_secondary_id": "",
                "teacher_pattern_secondary_name": "",
                "manual_entry_tag": "",
                "teacher_direction_bias": "",
                "teacher_entry_bias": "",
                "teacher_wait_bias": "",
                "teacher_exit_bias": "",
                "teacher_transition_risk": "",
                "teacher_label_confidence": "",
                "teacher_lookback_bars": "",
                "teacher_label_version": "",
                "teacher_label_source": "",
                "teacher_label_review_status": "",
            }
        ],
    )

    assert updated == 1
    row = logger.df.iloc[-1]
    assert row["entry_setup_id"] == "breakout_retest_sell"
    assert row["management_profile_id"] == "breakout_hold_profile"
    assert row["invalidation_id"] == "breakout_failure"
    assert row["exit_profile"] == "hold_then_trail"
    assert row["prediction_bundle"] == "{\"x\":1}"
    assert row["entry_wait_state"] == "NOISE"
    assert row["decision_row_key"] == "decision_row_v1|symbol=NAS100|anchor=202"
    assert row["runtime_snapshot_key"].startswith("runtime_signal_row_v1|symbol=NAS100")
    assert row["trade_link_key"].startswith("trade_link_v1|ticket=202")
    assert row["replay_row_key"] == "decision_row_v1|symbol=NAS100|anchor=202"
    assert row["signal_age_sec"] == 9.5
    assert row["bar_age_sec"] == 9.5
    assert row["decision_latency_ms"] == 220
    assert row["order_submit_latency_ms"] == 58
    assert row["missing_feature_count"] == 1
    assert row["data_completeness_ratio"] == 0.9
    assert row["used_fallback_count"] == 1
    assert row["compatibility_mode"] == "hybrid"
    assert row["detail_blob_bytes"] == 2048
    assert row["snapshot_payload_bytes"] == 640
    assert row["row_payload_bytes"] == 512
    assert row["micro_breakout_readiness_state"] == "COILED_BREAKOUT"
    assert row["micro_reversal_risk_state"] == "MEDIUM_RISK"
    assert row["micro_participation_state"] == "THIN_PARTICIPATION"
    assert row["micro_gap_context_state"] == "GAP_PARTIAL_FILL"
    assert row["micro_body_size_pct_20"] == 0.19
    assert row["micro_doji_ratio_20"] == 0.21
    assert row["micro_same_color_run_current"] == 2
    assert row["micro_same_color_run_max_20"] == 4
    assert row["micro_range_compression_ratio_20"] == 0.31
    assert row["micro_volume_burst_ratio_20"] == 1.4
    assert row["micro_volume_burst_decay_20"] == 0.58
    assert row["micro_gap_fill_progress"] == 0.45
    assert row["teacher_pattern_id"] == 5
    assert row["teacher_pattern_name"] == "Range 반전장"
    assert row["teacher_pattern_group"] == "D"
    assert row["teacher_pattern_secondary_id"] == 22
    assert row["teacher_pattern_secondary_name"] == "더블탑/바텀"
    assert row["teacher_direction_bias"] == "fade_reversal"
    assert row["teacher_entry_bias"] == "fade_entry"
    assert row["teacher_wait_bias"] == "wait_edge"
    assert row["teacher_exit_bias"] == "quick_take"
    assert row["teacher_transition_risk"] == "range_false_break"
    assert row["teacher_label_confidence"] == 0.66
    assert row["teacher_lookback_bars"] == 20
    assert row["teacher_label_version"] == "v2"
    assert row["teacher_label_source"] == "rule_v2"
    assert row["teacher_label_review_status"] == "reviewed"
    assert row["manual_entry_tag"] == "manual-range-fade"


def test_open_snapshot_identical_payload_skips_csv_roundtrip_on_second_call():
    logger = _FakeTradeLogger()
    snapshot = {
        "ticket": 303,
        "symbol": "XAUUSD",
        "direction": "BUY",
        "lot": 0.01,
        "open_price": 3000.5,
        "entry_reason": "[AUTO] unchanged",
        "entry_stage": "balanced",
        "entry_setup_id": "range_lower_reversal_buy",
        "management_profile_id": "support_hold_profile",
        "invalidation_id": "lower_support_fail",
        "exit_profile": "tight_protect",
        "entry_wait_state": "EDGE_APPROACH",
        "decision_row_key": "decision_row_v1|symbol=XAUUSD|anchor=303",
    }

    assert upsert_open_snapshots(logger, [snapshot]) == 1
    first_read_calls = logger.read_calls
    first_write_calls = logger.write_calls

    assert upsert_open_snapshots(logger, [snapshot]) == 0
    assert logger.read_calls == first_read_calls
    assert logger.write_calls == first_write_calls


def test_open_snapshot_volatile_regime_and_indicator_refresh_hits_cache_fast_path():
    logger = _FakeTradeLogger()
    logger._indicator_columns = lambda: ["rsi14"]
    snapshot = {
        "ticket": 305,
        "symbol": "XAUUSD",
        "direction": "BUY",
        "lot": 0.01,
        "open_price": 3000.5,
        "entry_reason": "[AUTO] unchanged",
        "entry_stage": "balanced",
        "entry_setup_id": "range_lower_reversal_buy",
        "management_profile_id": "support_hold_profile",
        "invalidation_id": "lower_support_fail",
        "exit_profile": "tight_protect",
        "entry_wait_state": "EDGE_APPROACH",
        "decision_row_key": "decision_row_v1|symbol=XAUUSD|anchor=305",
        "runtime_snapshot_key": "runtime_signal_row_v1|symbol=XAUUSD|anchor=305",
        "trade_link_key": "trade_link_v1|ticket=305|symbol=XAUUSD|direction=BUY|open_ts=1772766000",
        "replay_row_key": "decision_row_v1|symbol=XAUUSD|anchor=305",
        "regime": {"name": "uptrend", "volatility_ratio": 1.15},
        "indicators": {"rsi14": 52.0},
    }

    assert upsert_open_snapshots(logger, [snapshot]) == 1
    first_read_calls = logger.read_calls
    first_write_calls = logger.write_calls

    refreshed = dict(snapshot)
    refreshed["regime"] = {"name": "downtrend", "volatility_ratio": 1.42}
    refreshed["indicators"] = {"rsi14": 68.0}
    refreshed["entry_reason"] = "[AUTO] drifting reason"

    assert upsert_open_snapshots(logger, [refreshed]) == 0
    assert logger.read_calls == first_read_calls
    assert logger.write_calls == first_write_calls
    row = logger.df.iloc[-1]
    assert row["regime_name"] == "uptrend"
    assert row["rsi14"] == 52.0


def test_open_snapshot_auto_labels_teacher_pattern_when_missing():
    logger = _FakeTradeLogger()

    updated = upsert_open_snapshots(
        logger,
        [
            {
                "ticket": 304,
                "symbol": "XAUUSD",
                "direction": "BUY",
                "lot": 0.01,
                "open_price": 3001.5,
                "entry_reason": "[AUTO] unlabeled snapshot",
                "entry_stage": "balanced",
                "entry_setup_id": "breakout_prepare_buy",
                "micro_breakout_readiness_state": "COILED_BREAKOUT",
                "micro_reversal_risk_state": "LOW_RISK",
                "micro_participation_state": "ACTIVE_PARTICIPATION",
                "micro_gap_context_state": "NO_GAP_CONTEXT",
                "micro_body_size_pct_20": 0.14,
                "micro_doji_ratio_20": 0.22,
                "micro_same_color_run_current": 2,
                "micro_same_color_run_max_20": 3,
                "micro_range_compression_ratio_20": 0.82,
                "micro_volume_burst_ratio_20": 2.1,
                "micro_volume_burst_decay_20": 0.18,
                "micro_gap_fill_progress": 0.0,
                "micro_swing_high_retest_count_20": 2,
                "micro_swing_low_retest_count_20": 2,
            }
        ],
    )

    assert updated == 1
    row = logger.df.iloc[-1]
    assert row["teacher_pattern_id"] == 12
    assert row["teacher_pattern_name"] == "브레이크아웃 직전"
    assert row["teacher_pattern_secondary_id"] == 23
    assert row["teacher_pattern_secondary_name"] == "삼각수렴 압축"
    assert row["teacher_entry_bias"] == "breakout"
    assert str(row["teacher_label_version"]).startswith("state25_v")


def test_normalize_trade_df_preserves_micro_structure_fields_for_closed_rows():
    df = pd.DataFrame(
        [
            {
                "ticket": 404,
                "symbol": "XAUUSD",
                "direction": "BUY",
                "status": "CLOSED",
                "open_time": "2026-03-06 12:00:00",
                "close_time": "2026-03-06 12:05:00",
                "open_price": 3000.0,
                "close_price": 3004.0,
                "profit": 4.0,
                "micro_breakout_readiness_state": "READY_BREAKOUT",
                "micro_reversal_risk_state": "LOW_RISK",
                "micro_participation_state": "ACTIVE_PARTICIPATION",
                "micro_gap_context_state": "GAP_FULLY_FILLED",
                "micro_body_size_pct_20": "0.33",
                "micro_doji_ratio_20": "0.11",
                "micro_same_color_run_current": "4",
                "micro_same_color_run_max_20": "6",
                "micro_range_compression_ratio_20": "0.28",
                "micro_volume_burst_ratio_20": "2.25",
                "micro_volume_burst_decay_20": "0.52",
                "micro_gap_fill_progress": "1.0",
                "teacher_pattern_id": "20",
                "teacher_pattern_name": "엔진 꺼짐장",
                "teacher_pattern_group": "E",
                "teacher_pattern_secondary_id": "2",
                "teacher_pattern_secondary_name": "변동성 큰 장",
                "teacher_direction_bias": "neutral_to_fast_cut",
                "teacher_entry_bias": "avoid",
                "teacher_wait_bias": "low_patience",
                "teacher_exit_bias": "scale_out_or_exit",
                "teacher_transition_risk": "engine_off",
                "teacher_label_confidence": "0.83",
                "teacher_lookback_bars": "30",
                "teacher_label_version": "v2",
                "teacher_label_source": "rule_v2",
                "teacher_label_review_status": "approved",
            }
        ]
    )

    out = normalize_trade_df(df)
    row = out.iloc[0]

    assert row["status"] == "CLOSED"
    assert row["micro_breakout_readiness_state"] == "READY_BREAKOUT"
    assert row["micro_reversal_risk_state"] == "LOW_RISK"
    assert row["micro_participation_state"] == "ACTIVE_PARTICIPATION"
    assert row["micro_gap_context_state"] == "GAP_FULLY_FILLED"
    assert row["micro_body_size_pct_20"] == 0.33
    assert row["micro_doji_ratio_20"] == 0.11
    assert row["micro_same_color_run_current"] == 4
    assert row["micro_same_color_run_max_20"] == 6
    assert row["teacher_pattern_id"] == 20
    assert row["teacher_pattern_name"] == "엔진 꺼짐장"
    assert row["teacher_pattern_group"] == "E"
    assert row["teacher_pattern_secondary_id"] == 2
    assert row["teacher_pattern_secondary_name"] == "변동성 큰 장"
    assert row["teacher_direction_bias"] == "neutral_to_fast_cut"
    assert row["teacher_entry_bias"] == "avoid"
    assert row["teacher_wait_bias"] == "low_patience"
    assert row["teacher_exit_bias"] == "scale_out_or_exit"
    assert row["teacher_transition_risk"] == "engine_off"
    assert row["teacher_label_confidence"] == 0.83
    assert row["teacher_lookback_bars"] == 30
    assert row["teacher_label_version"] == "v2"
    assert row["teacher_label_source"] == "rule_v2"
    assert row["teacher_label_review_status"] == "approved"
    assert row["micro_range_compression_ratio_20"] == 0.28
    assert row["micro_volume_burst_ratio_20"] == 2.25
    assert row["micro_volume_burst_decay_20"] == 0.52
    assert row["micro_gap_fill_progress"] == 1.0
