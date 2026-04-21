from types import SimpleNamespace

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df
from backend.trading.trade_logger_close_ops import update_closed_trade


class _FakeBroker:
    @staticmethod
    def symbol_info(_symbol):
        return SimpleNamespace(point=1.0)


class _FakeTradeLogger:
    def __init__(self):
        self.df = normalize_trade_df(
            pd.DataFrame(
                [
                    {
                        "ticket": 777,
                        "symbol": "BTCUSD",
                        "direction": "BUY",
                        "lot": 0.01,
                        "open_time": "2026-04-02 12:00:00",
                        "open_ts": 1775102400,
                        "open_price": 70000.0,
                        "status": "OPEN",
                        "entry_reason": "[MANUAL] Position Snapshot",
                        "manual_entry_tag": "manual-breakout-entry",
                    }
                ],
                columns=TRADE_COLUMNS,
            )
        )
        self.broker = _FakeBroker()
        self.pending_exit = {}
        self.live_exit_context = {}
        self.closed_rows = None
        self.written_df = None
        self.synced_df = None

    def _read_open_df_safe(self):
        return self.df.copy()

    def _normalize_dataframe(self, df):
        return normalize_trade_df(df)

    def _sum_exit_profit_for_position(self, _ticket):
        return None

    def resolve_shock_event_on_close(self, *_args, **_kwargs):
        return None

    def _ts_to_kst_text(self, _ts):
        return "2026-04-02 12:05:00"

    def _ts_to_kst_dt(self, _ts):
        return pd.Timestamp("2026-04-02 12:05:00")

    def _estimate_reason_points(self, _reason):
        return 17

    @staticmethod
    def _normalize_exit_reason(reason):
        return str(reason or "").strip()

    def _append_to_closed_file(self, df):
        self.closed_rows = normalize_trade_df(df)

    def _write_open_df(self, df):
        self.written_df = normalize_trade_df(df)

    def _sync_open_rows_to_store(self, df):
        self.synced_df = normalize_trade_df(df)


def test_update_closed_trade_preserves_manual_entry_tag_and_sets_manual_exit_tag():
    logger = _FakeTradeLogger()
    deal = SimpleNamespace(
        symbol="BTCUSD",
        time=1775102700,
        price=70025.0,
        profit=25.0,
        swap=0.0,
        commission=0.0,
        comment="manual-take-profit",
    )

    message = update_closed_trade(logger, 777, deal, fallback_reason="Manual/Unknown")

    assert logger.closed_rows is not None
    closed = logger.closed_rows.iloc[0]
    assert closed["manual_entry_tag"] == "manual-breakout-entry"
    assert closed["manual_exit_tag"] == "manual-take-profit"
    assert closed["exit_reason"] == "manual-take-profit"
    assert isinstance(message, str)
    assert "*청산*" in message
    assert "manual-take-profit" in message


def test_update_closed_trade_populates_gross_net_and_cost_breakdown_fields():
    logger = _FakeTradeLogger()
    deal = SimpleNamespace(
        symbol="BTCUSD",
        time=1775102700,
        price=70025.0,
        profit=25.0,
        swap=-1.0,
        commission=-2.0,
        comment="manual-take-profit",
    )

    update_closed_trade(logger, 777, deal, fallback_reason="Manual/Unknown")

    assert logger.closed_rows is not None
    closed = logger.closed_rows.iloc[0]
    assert closed["profit"] == 22.0
    assert closed["gross_pnl"] == 25.0
    assert closed["cost_total"] == 3.0
    assert closed["net_pnl_after_cost"] == 22.0
