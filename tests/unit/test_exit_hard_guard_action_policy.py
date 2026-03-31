from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_hard_guard_action_policy import (
    resolve_exit_hard_guard_action_candidate_v1,
)


def test_exit_hard_guard_action_policy_maps_profit_giveback_to_lock():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        profit=0.44,
        adverse_risk=False,
        tf_confirm=False,
        hold_strong=False,
        protect_now=False,
        lock_now=False,
        min_target_profit=0.1,
        min_net_guard=0.2,
        exit_detail="unit",
        exit_signal_score=100,
        reverse_signal_threshold=120,
        score_gap=12,
        opposite_score=88.0,
        result={},
        profit_giveback_hit=True,
    )

    assert candidate["hit"] is True
    assert candidate["reason"] == "Lock Exit"
    assert candidate["candidate_kind"] == "profit_giveback_lock"


def test_exit_hard_guard_action_policy_defer_on_adverse_wait():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        profit=-0.28,
        adverse_risk=True,
        tf_confirm=False,
        hold_strong=False,
        protect_now=False,
        lock_now=False,
        min_target_profit=0.05,
        min_net_guard=0.1,
        exit_detail="unit",
        exit_signal_score=120,
        reverse_signal_threshold=130,
        score_gap=24,
        opposite_score=91.0,
        result={},
        hold_for_adverse=True,
        wait_adverse=True,
    )

    assert candidate["hit"] is False
    assert candidate["defer"] is True
    assert candidate["candidate_kind"] == "adverse_wait"


def test_exit_hard_guard_action_policy_builds_adverse_reverse_candidate():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        profit=-0.55,
        adverse_risk=True,
        tf_confirm=False,
        hold_strong=False,
        protect_now=False,
        lock_now=False,
        min_target_profit=0.05,
        min_net_guard=0.1,
        exit_detail="unit",
        exit_signal_score=160,
        reverse_signal_threshold=140,
        score_gap=30,
        opposite_score=97.0,
        result={"buy": {"reasons": ["reverse_buy_ready"]}},
        hold_for_adverse=True,
        extreme_adverse=True,
    )

    assert candidate["hit"] is True
    assert candidate["candidate_kind"] == "adverse_reverse"
    assert candidate["reason"] == "Adverse Reversal"
    assert candidate["reverse_action"] == "BUY"
    assert candidate["reverse_reasons"] == ["reverse_buy_ready"]
