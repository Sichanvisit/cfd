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
    monkeypatch.setattr(Config, "IMMEDIATE_REVERSE_FLAT_WAIT_SEC", 0.0)

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


def test_try_reverse_entry_retries_pending_candidate_once_symbol_turns_flat(monkeypatch):
    app = _DummyApp()
    trade_logger = _DummyTradeLogger()
    positions_state = {"open": True}

    def _positions_get(symbol=None):
        if positions_state["open"]:
            return [SimpleNamespace(magic=Config.MAGIC_NUMBER, type=1)]
        return []

    app.broker = SimpleNamespace(positions_get=_positions_get)

    monkeypatch.setattr(Config, "ALLOW_IMMEDIATE_REVERSE", True)
    monkeypatch.setattr(Config, "IMMEDIATE_REVERSE_FLAT_WAIT_SEC", 0.0)
    monkeypatch.setattr(Config, "IMMEDIATE_REVERSE_PENDING_TTL_SEC", 30.0)

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
    assert "BTCUSD" in app.pending_reverse_by_symbol

    positions_state["open"] = False
    try_reverse_entry(
        app,
        reverse_action=None,
        reverse_score=0,
        reverse_reasons=[],
        symbol="BTCUSD",
        buy_s=220,
        sell_s=80,
        tick=SimpleNamespace(ask=100.2, bid=100.1),
        scorer=None,
        df_all={},
        trade_logger=trade_logger,
    )

    assert app.execute_order_called is True
    assert "BTCUSD" not in app.pending_reverse_by_symbol


def test_try_reverse_entry_waits_briefly_for_recent_close_before_order(monkeypatch):
    app = _DummyApp()
    trade_logger = _DummyTradeLogger()
    call_counter = {"count": 0}

    def _positions_get(symbol=None):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            return [SimpleNamespace(magic=Config.MAGIC_NUMBER, type=1)]
        return []

    app.broker = SimpleNamespace(positions_get=_positions_get)

    monkeypatch.setattr(Config, "ALLOW_IMMEDIATE_REVERSE", True)
    monkeypatch.setattr(Config, "IMMEDIATE_REVERSE_FLAT_WAIT_SEC", 0.3)
    monkeypatch.setattr(Config, "IMMEDIATE_REVERSE_PENDING_TTL_SEC", 30.0)

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

    assert app.execute_order_called is True
