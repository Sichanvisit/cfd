from types import SimpleNamespace

from backend.app.trading_application import TradingApplication
from backend.core.trade_constants import TRADE_RETCODE_DONE


class _DummyObservability:
    def incr(self, *_args, **_kwargs):
        return None

    def event(self, *_args, **_kwargs):
        return None


class _BrokerBlocked:
    def __init__(self):
        self.order_send_called = 0

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(ask=101.0, bid=100.0)

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=False)

    def symbol_info(self, _symbol):
        return SimpleNamespace(point=0.01, digits=2, trade_stops_level=0)

    def order_send(self, _request):
        self.order_send_called += 1
        return None

    def last_error(self):
        return (0, "ok")


class _BrokerAllowed:
    def __init__(self):
        self.order_send_called = 0

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(ask=101.0, bid=100.0)

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def symbol_info(self, _symbol):
        return SimpleNamespace(point=0.01, digits=2, trade_stops_level=0)

    def order_send(self, _request):
        self.order_send_called += 1
        return SimpleNamespace(retcode=TRADE_RETCODE_DONE, order=777, comment="ok")

    def last_error(self):
        return (0, "ok")


class _BrokerAllowedWithPosition:
    def __init__(self):
        self.order_send_called = 0

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(ask=101.0, bid=100.0)

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def symbol_info(self, _symbol):
        return SimpleNamespace(point=0.01, digits=2, trade_stops_level=0)

    def order_send(self, _request):
        self.order_send_called += 1
        return SimpleNamespace(retcode=TRADE_RETCODE_DONE, order=777, position=0, comment="ok")

    def positions_get(self, **kwargs):
        if kwargs.get("ticket") == 777:
            return []
        if kwargs.get("symbol") == "NAS100":
            return [SimpleNamespace(ticket=999, type=0, magic=0, time=123456)]
        return []

    def last_error(self):
        return (0, "ok")


class _BrokerForStopMove:
    def __init__(self, *, pos_type=0, current_sl=0.0):
        self.pos_type = pos_type
        self.current_sl = current_sl
        self.last_request = None

    def positions_get(self, **kwargs):
        if kwargs.get("ticket") == 999:
            return [SimpleNamespace(ticket=999, symbol="BTCUSD", type=self.pos_type, sl=self.current_sl, tp=0.0)]
        return []

    def symbol_info(self, _symbol):
        return SimpleNamespace(point=0.01, digits=2, trade_stops_level=10)

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(bid=100.0, ask=100.1)

    def order_send(self, request):
        self.last_request = dict(request)
        return SimpleNamespace(retcode=TRADE_RETCODE_DONE, comment="ok")


def _new_app_for_execute_order(broker):
    app = TradingApplication.__new__(TradingApplication)
    app.broker = broker
    app.observability = _DummyObservability()
    app.last_order_error = ""
    app.last_order_ts = 0.0
    return app


def test_execute_order_respects_broker_terminal_info_block():
    broker = _BrokerBlocked()
    app = _new_app_for_execute_order(broker)
    out = app.execute_order("NAS100", "BUY", 0.1)
    assert out is None
    assert broker.order_send_called == 0


def test_execute_order_uses_broker_and_succeeds_with_mock():
    broker = _BrokerAllowed()
    app = _new_app_for_execute_order(broker)
    out = app.execute_order("NAS100", "BUY", 0.1)
    assert out == 777
    assert broker.order_send_called == 1


def test_execute_order_prefers_live_position_ticket_when_available():
    broker = _BrokerAllowedWithPosition()
    app = _new_app_for_execute_order(broker)
    out = app.execute_order("NAS100", "BUY", 0.1)
    assert out == 999
    assert broker.order_send_called == 1


def test_move_stop_to_break_even_clamps_buy_stop_below_bid():
    broker = _BrokerForStopMove(pos_type=0, current_sl=0.0)
    app = _new_app_for_execute_order(broker)
    moved = app.move_stop_to_break_even(999, 120.0)

    assert moved is True
    assert broker.last_request is not None
    assert broker.last_request["sl"] < 100.0


def test_move_stop_to_break_even_clamps_sell_stop_above_ask():
    broker = _BrokerForStopMove(pos_type=1, current_sl=0.0)
    app = _new_app_for_execute_order(broker)
    moved = app.move_stop_to_break_even(999, 80.0)

    assert moved is True
    assert broker.last_request is not None
    assert broker.last_request["sl"] > 100.1
