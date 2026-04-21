from datetime import datetime

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df
from backend.trading import trade_logger_log_entry


class _FakeTradeLogger:
    def __init__(self):
        self.df = normalize_trade_df(pd.DataFrame(columns=TRADE_COLUMNS))
        self.active_tickets = set()
        self.synced = None

    def _now_kst_dt(self):
        return datetime(2026, 4, 2, 20, 0, 0)

    def _normalize_entry_stage(self, value):
        return str(value or "balanced").strip().lower()

    def _read_open_df_safe(self):
        return self.df.copy()

    def _normalize_dataframe(self, df):
        return normalize_trade_df(df)

    def _write_open_df(self, df):
        self.df = normalize_trade_df(df)

    def _upsert_open_rows_to_store(self, df):
        self.synced = normalize_trade_df(df)

    def _indicator_columns(self):
        return []


def test_trade_logger_log_entry_uses_regime_volatility_ratio_as_entry_atr_proxy():
    logger = _FakeTradeLogger()

    trade_logger_log_entry.log_entry(
        logger,
        ticket=101,
        symbol="BTCUSD",
        direction="BUY",
        price=70000.0,
        reason="[AUTO] proxy test",
        regime={"name": "NORMAL", "volatility_ratio": 1.38},
        entry_atr_ratio=1.0,
    )

    row = logger.df.iloc[-1]
    assert float(row["entry_atr_ratio"]) == 1.38
    assert float(logger.synced.iloc[-1]["entry_atr_ratio"]) == 1.38


def test_trade_logger_log_entry_preserves_explicit_entry_atr_ratio():
    logger = _FakeTradeLogger()

    trade_logger_log_entry.log_entry(
        logger,
        ticket=102,
        symbol="XAUUSD",
        direction="SELL",
        price=3200.0,
        reason="[AUTO] explicit atr",
        regime={"name": "EXPANSION", "volatility_ratio": 1.48},
        entry_atr_ratio=1.12,
    )

    row = logger.df.iloc[-1]
    assert float(row["entry_atr_ratio"]) == 1.12
