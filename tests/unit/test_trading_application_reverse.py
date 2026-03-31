from types import SimpleNamespace

from backend.app.trading_application_reverse import try_reverse_entry
from backend.core.config import Config


class _DummyApp:
    def __init__(self):
        self.last_entry_time = {"BTCUSD": 0.0}
        self.latest_signal_by_symbol = {"BTCUSD": {"entry_threshold": 300}}
        self.latest_regime_by_symbol = {"BTCUSD": {"name": "RANGE"}}
        self.ai_runtime = None
        self.execute_order_called = False
        self.broker = SimpleNamespace(
            positions_get=lambda symbol=None: [SimpleNamespace(magic=Config.MAGIC_NUMBER, type=1)],
        )

    def get_lot_size(self, _symbol):
        return 0.01

    def execute_order(self, *_args, **_kwargs):
        self.execute_order_called = True
        return 1001

    def _entry_features(self, *_args, **_kwargs):
        return {}

    def _score_adjustment(self, *_args, **_kwargs):
        return 0

    def _append_ai_entry_trace(self, *_args, **_kwargs):
        return None

    def _entry_indicator_snapshot(self, *_args, **_kwargs):
        return {}

    def _build_scored_reasons(self, reasons, **_kwargs):
        return list(reasons)

    def format_entry_message(self, *_args, **_kwargs):
        return "reverse"

    def notify(self, *_args, **_kwargs):
        return None


class _DummyTradeLogger:
    def log_entry(self, *_args, **_kwargs):
        return None


def test_try_reverse_entry_requires_flat_symbol(monkeypatch):
    app = _DummyApp()
    trade_logger = _DummyTradeLogger()

    monkeypatch.setattr(Config, "ALLOW_IMMEDIATE_REVERSE", True)

    try_reverse_entry(
        app,
        reverse_action="BUY",
        reverse_score=250,
        reverse_reasons=["reverse"],
        symbol="BTCUSD",
        buy_s=220,
        sell_s=80,
        tick=SimpleNamespace(ask=100.2, bid=100.1),
        scorer=None,
        df_all={},
        trade_logger=trade_logger,
    )

    assert app.execute_order_called is False
