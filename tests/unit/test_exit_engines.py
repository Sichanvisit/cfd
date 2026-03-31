from types import SimpleNamespace

from backend.services.exit_engines import ExitActionExecutor, ExitMetricsCollector, ExitRiskGuard, ExitStageRouter


class _DummyRuntime:
    def __init__(self):
        self.calls = []

    def close_position(self, ticket: int, reason: str = "Exit") -> bool:
        self.calls.append((int(ticket), str(reason)))
        return True


class _DummyTradeLogger:
    def __init__(self):
        self.reqs = []

    def register_exit_request(self, ticket, reason, score, detail=""):
        self.reqs.append((int(ticket), str(reason), int(score), str(detail)))


def test_exit_stage_router_maps_stage_to_policy():
    plan = ExitStageRouter.build_stage_execution_plan("protect", confirm_needed=3, adverse_risk=True)
    assert plan["policy_stage"] == "short"
    assert plan["allow_short"] is True
    assert plan["allow_mid"] is False
    assert int(plan["confirm_short"]) == 2


def test_exit_action_executor_executes_and_resets():
    runtime = _DummyRuntime()
    logger = _DummyTradeLogger()
    metrics = {}
    resets = []

    def _bump(key: str, amount: int = 1):
        metrics[key] = int(metrics.get(key, 0)) + int(amount)

    def _reset(ticket_i: int):
        resets.append(int(ticket_i))

    exe = ExitActionExecutor(runtime=runtime, trade_logger=logger, bump_metric=_bump, reset_state=_reset)
    pos = SimpleNamespace(ticket=1001)
    ok = exe.execute_exit(
        pos=pos,
        ticket_i=1001,
        reason="Lock Exit",
        exit_signal_score=120,
        detail="unit-test",
        metric_keys=["exit_lock"],
    )
    assert ok is True
    assert runtime.calls == [(1001, "Lock Exit")]
    assert resets == [1001]
    assert int(metrics.get("exit_lock", 0)) == 1
    assert logger.reqs and logger.reqs[0][1] == "Lock Exit"


def test_exit_metrics_collector_snapshot_has_total():
    metrics = {"exit_lock": 2, "exit_target": 1}
    snap = ExitMetricsCollector.snapshot(metrics, {"blend_mode": "dynamic"}, {}, {})
    assert int(snap["exit_total"]) == 3


def test_exit_risk_guard_returns_reverse_surface_on_adverse_reverse():
    runtime = _DummyRuntime()
    logger = _DummyTradeLogger()
    metrics = {}
    resets = []

    def _bump(key: str, amount: int = 1):
        metrics[key] = int(metrics.get(key, 0)) + int(amount)

    def _reset(ticket_i: int):
        resets.append(int(ticket_i))

    guard = ExitRiskGuard(
        action_executor=ExitActionExecutor(runtime=runtime, trade_logger=logger, bump_metric=_bump, reset_state=_reset),
        bump_metric=_bump,
        check_profit_giveback=lambda *args: False,
        check_plus_to_minus=lambda *args: False,
        should_delay_adverse=lambda *args: (False, ""),
    )
    pos = SimpleNamespace(ticket=2002, type=0)

    hit, reverse_action, reverse_score, reverse_reasons = guard.try_execute_hard_risk_guards(
        pos=pos,
        symbol="BTCUSD",
        ticket_i=2002,
        profit=-0.44,
        adverse_risk=True,
        duration_sec=90.0,
        favorable_move_pct=0.0012,
        dynamic_loss_usd=0.20,
        tf_confirm=False,
        hold_strong=False,
        protect_score=10,
        protect_threshold=60,
        lock_score=10,
        lock_threshold=90,
        min_target_profit=0.04,
        min_net_guard=0.10,
        exit_signal_score=160,
        exit_detail="unit",
        reverse_signal_threshold=140,
        score_gap=30,
        opposite_score=93.0,
        result={"sell": {"reasons": ["sell_reverse_ready"]}, "buy": {"reasons": []}},
    )

    assert hit is True
    assert reverse_action == "SELL"
    assert reverse_score == 93.0
    assert reverse_reasons == ["sell_reverse_ready"]
    assert runtime.calls == [(2002, "Adverse Reversal")]
    assert int(metrics.get("exit_adverse_reversal", 0)) == 1
