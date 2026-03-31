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
