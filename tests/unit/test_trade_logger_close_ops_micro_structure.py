from datetime import datetime

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df
from backend.trading.trade_logger_close_ops import force_close_unknown


class _FakeCloseTradeLogger:
    def __init__(self):
        self.df = normalize_trade_df(
            pd.DataFrame(
                [
                    {
                        "ticket": 901,
                        "symbol": "NAS100",
                        "direction": "SELL",
                        "lot": 0.1,
                        "open_time": "2026-03-06 12:00:00",
                        "open_ts": 1772766000,
                        "open_price": 25000.0,
                        "status": "OPEN",
                        "management_profile_id": "breakout_hold_profile",
                        "invalidation_id": "breakout_failure",
                        "entry_setup_id": "upper_break_fail_confirm",
                        "exit_profile": "hold_then_trail",
                        "micro_breakout_readiness_state": "COILED_BREAKOUT",
                        "micro_reversal_risk_state": "MEDIUM_RISK",
                        "micro_participation_state": "ACTIVE_PARTICIPATION",
                        "micro_gap_context_state": "NO_GAP_CONTEXT",
                        "micro_body_size_pct_20": 0.22,
                        "micro_doji_ratio_20": 0.18,
                        "micro_same_color_run_current": 3,
                        "micro_same_color_run_max_20": 5,
                        "micro_range_compression_ratio_20": 0.36,
                        "micro_volume_burst_ratio_20": 1.7,
                        "micro_volume_burst_decay_20": 0.61,
                        "micro_gap_fill_progress": 0.0,
                        "teacher_pattern_id": 8,
                        "teacher_pattern_name": "죽음의 가위장",
                        "teacher_pattern_group": "E",
                        "teacher_pattern_secondary_id": 2,
                        "teacher_pattern_secondary_name": "변동성 큰 장",
                        "teacher_direction_bias": "sell_confirm",
                        "teacher_entry_bias": "confirm_entry",
                        "teacher_wait_bias": "low_patience",
                        "teacher_exit_bias": "protective_exit",
                        "teacher_transition_risk": "trend_acceleration",
                        "teacher_label_confidence": 0.74,
                        "teacher_lookback_bars": 20,
                        "teacher_label_version": "v2",
                        "teacher_label_source": "rule_v2",
                        "teacher_label_review_status": "pending",
                    }
                ],
                columns=TRADE_COLUMNS,
            )
        )
        self.closed_rows = None
        self.written_df = None
        self.synced_df = None

    def _read_open_df_safe(self):
        return self.df.copy()

    def _normalize_dataframe(self, df):
        return normalize_trade_df(df)

    def _now_kst_text(self):
        return "2026-03-06 12:05:00"

    def _text_to_kst_epoch(self, _text):
        return 1772766300

    def resolve_shock_event_on_close(self, *_args, **_kwargs):
        return None

    def _estimate_reason_points(self, _reason):
        return 15

    def _append_to_closed_file(self, df):
        self.closed_rows = normalize_trade_df(df)

    def _write_open_df(self, df):
        self.written_df = normalize_trade_df(df)

    def _sync_open_rows_to_store(self, df):
        self.synced_df = normalize_trade_df(df)


def test_force_close_unknown_preserves_micro_structure_fields_in_closed_rows():
    logger = _FakeCloseTradeLogger()

    ok = force_close_unknown(logger, 901, reason="Manual/Unknown")

    assert ok is True
    assert logger.closed_rows is not None
    closed = logger.closed_rows.iloc[0]
    assert closed["status"] == "CLOSED"
    assert closed["micro_breakout_readiness_state"] == "COILED_BREAKOUT"
    assert closed["micro_reversal_risk_state"] == "MEDIUM_RISK"
    assert closed["micro_participation_state"] == "ACTIVE_PARTICIPATION"
    assert closed["micro_gap_context_state"] == "NO_GAP_CONTEXT"
    assert closed["micro_body_size_pct_20"] == 0.22
    assert closed["micro_doji_ratio_20"] == 0.18
    assert closed["micro_same_color_run_current"] == 3
    assert closed["micro_same_color_run_max_20"] == 5
    assert closed["micro_range_compression_ratio_20"] == 0.36
    assert closed["micro_volume_burst_ratio_20"] == 1.7
    assert closed["micro_volume_burst_decay_20"] == 0.61
    assert closed["micro_gap_fill_progress"] == 0.0
    assert closed["teacher_pattern_id"] == 8
    assert closed["teacher_pattern_name"] == "죽음의 가위장"
    assert closed["teacher_pattern_group"] == "E"
    assert closed["teacher_pattern_secondary_id"] == 2
    assert closed["teacher_pattern_secondary_name"] == "변동성 큰 장"
    assert closed["teacher_direction_bias"] == "sell_confirm"
    assert closed["teacher_entry_bias"] == "confirm_entry"
    assert closed["teacher_wait_bias"] == "low_patience"
    assert closed["teacher_exit_bias"] == "protective_exit"
    assert closed["teacher_transition_risk"] == "trend_acceleration"
    assert closed["teacher_label_confidence"] == 0.74
    assert closed["teacher_lookback_bars"] == 20
    assert closed["teacher_label_version"] == "v2"
    assert closed["teacher_label_source"] == "rule_v2"
    assert closed["teacher_label_review_status"] == "pending"
    assert logger.written_df is not None
    assert logger.written_df.empty
    assert logger.synced_df is not None
    assert logger.synced_df.empty
