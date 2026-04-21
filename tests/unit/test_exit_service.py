import backend.services.exit_service as exit_service_module
from backend.core.config import Config
from backend.services.exit_service import ExitService


class _DummyRuntime:
    def __init__(self):
        self.latest_signal_by_symbol = {}
        self.broker = None


class _DummyTradeLogger:
    pass


def _build_service() -> ExitService:
    return ExitService(_DummyRuntime(), _DummyTradeLogger())


def _patch_adverse_wait_config(monkeypatch) -> None:
    monkeypatch.setattr(Config, "ADVERSE_WAIT_FOR_BETTER_EXIT_ENABLED", True, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_DISABLE_ON_GIVEBACK", False, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_MIN_LOSS_USD", 0.8, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_NO_TURN_SCORE_GAP", 35, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_MIN_SECONDS", 10.0, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_MAX_SECONDS", 120.0, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_RECOVERY_USD", 0.35, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_TF_CONFIRM_MAX_SECONDS", 90.0, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_TF_CONFIRM_WEAK_PEAK_USD", 0.50, raising=False)
    monkeypatch.setattr(Config, "ADVERSE_WAIT_TF_CONFIRM_WEAK_PEAK_MAX_SECONDS", 45.0, raising=False)


def test_should_delay_adverse_exit_uses_shorter_timeout_for_tf_confirm_weak_peak(monkeypatch):
    _patch_adverse_wait_config(monkeypatch)
    svc = _build_service()
    svc.peak_profit[1] = 0.10

    times = iter([100.0, 160.0])
    monkeypatch.setattr(exit_service_module.time, "time", lambda: next(times))

    wait_now, detail_now = svc._should_delay_adverse_exit(
        ticket_i=1,
        profit=-1.2,
        hold_strong=False,
        tf_confirm=True,
        score_gap=40,
        extreme_adverse=False,
    )
    wait_later, detail_later = svc._should_delay_adverse_exit(
        ticket_i=1,
        profit=-1.2,
        hold_strong=False,
        tf_confirm=True,
        score_gap=40,
        extreme_adverse=False,
    )

    assert wait_now is True
    assert detail_now == "adverse_wait=warmup(0s/10s)"
    assert wait_later is False
    assert detail_later == "adverse_wait=timeout(60s)"


def test_should_delay_adverse_exit_keeps_tf_confirm_wait_when_peak_was_meaningful(monkeypatch):
    _patch_adverse_wait_config(monkeypatch)
    svc = _build_service()
    svc.peak_profit[7] = 0.85

    times = iter([200.0, 260.0])
    monkeypatch.setattr(exit_service_module.time, "time", lambda: next(times))

    wait_now, detail_now = svc._should_delay_adverse_exit(
        ticket_i=7,
        profit=-1.2,
        hold_strong=False,
        tf_confirm=True,
        score_gap=40,
        extreme_adverse=False,
    )
    wait_later, detail_later = svc._should_delay_adverse_exit(
        ticket_i=7,
        profit=-1.2,
        hold_strong=False,
        tf_confirm=True,
        score_gap=40,
        extreme_adverse=False,
    )

    assert wait_now is True
    assert detail_now == "adverse_wait=warmup(0s/10s)"
    assert wait_later is True
    assert detail_later == "adverse_wait=holding(0.00/0.35)"
