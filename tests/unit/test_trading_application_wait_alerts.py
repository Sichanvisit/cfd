from backend.app.trading_application import TradingApplication


class _DummyBroker:
    def positions_get(self, symbol: str = "", ticket: int | None = None):
        return []


class _DummyNotifier:
    def send(self, message):
        return None

    def shutdown(self, timeout: float = 2.0):
        return None

    def format_entry_message(self, *args, **kwargs):
        return "entry"

    def format_exit_message(self, *args, **kwargs):
        return "exit"

    def format_wait_message(self, *args, **kwargs):
        return "wait"

    def build_wait_message_signature(self, symbol, action, reason=None, row=None):
        return f"{symbol}|{action}|{reason}"

    def format_reverse_message(self, *args, **kwargs):
        return "reverse"

    def build_reverse_message_signature(self, symbol, action, score, reasons, pending=False):
        return f"{symbol}|{action}|{int(bool(pending))}|{int(score)}"


class _DummyObservability:
    def incr(self, name, amount=1):
        return None

    def event(self, name, level="info", payload=None):
        return None


def test_wait_alert_dedupe_suppresses_same_signature_within_cooldown(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr("backend.app.trading_application.time.time", lambda: 1000.0)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    assert app.should_notify_wait_message("BTCUSD", "BTCUSD|SELL|forecast_guard") is True
    assert app.should_notify_wait_message("BTCUSD", "BTCUSD|SELL|forecast_guard") is False


def test_wait_alert_dedupe_allows_same_signature_after_cooldown(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    now = {"value": 1000.0}

    def _fake_time():
        return now["value"]

    monkeypatch.setattr("backend.app.trading_application.time.time", _fake_time)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    assert app.should_notify_wait_message("BTCUSD", "BTCUSD|SELL|forecast_guard") is True
    now["value"] = 1300.0
    assert app.should_notify_wait_message("BTCUSD", "BTCUSD|SELL|forecast_guard") is True


def test_reverse_alert_dedupe_suppresses_same_signature_within_cooldown(monkeypatch):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    monkeypatch.setattr("backend.app.trading_application.time.time", lambda: 1000.0)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )

    assert app.should_notify_reverse_message("BTCUSD", "BTCUSD|BUY|1|262") is True
    assert app.should_notify_reverse_message("BTCUSD", "BTCUSD|BUY|1|262") is False
