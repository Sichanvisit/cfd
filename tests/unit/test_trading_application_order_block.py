from types import SimpleNamespace

from backend.app.trading_application import TradingApplication


class _DummyBroker:
    def symbol_info_tick(self, symbol):
        return SimpleNamespace(ask=100.0, bid=99.5)

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.1, digits=1, trade_stops_level=10)

    def order_send(self, request):
        return SimpleNamespace(retcode=10018, comment="Market closed")

    def last_error(self):
        return (1, "Success")


class _DummyNotifier:
    def send(self, message):
        return None

    def shutdown(self):
        return None


class _DummyObservability:
    def incr(self, name, amount=1):
        return None

    def event(self, name, level="info", payload=None):
        return None


def test_market_closed_sets_symbol_order_block():
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    ticket = app.execute_order("BTCUSD", "BUY", 0.01)

    assert ticket is None
    status = app.get_order_block_status("BTCUSD")
    assert status["active"] is True
    assert status["reason"] == "market_closed"
    assert status["retcode"] == 10018
    assert "Market closed" in app.last_order_error
