from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_hard_guard_action_policy import (
    resolve_exit_hard_guard_action_candidate_v1,
)


def test_exit_hard_guard_action_policy_maps_profit_giveback_to_lock():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        profit=0.44,
        peak_profit=1.42,
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
        peak_profit=0.0,
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
        peak_profit=0.0,
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


def test_exit_hard_guard_action_policy_defers_adverse_protect_when_wait_contract_is_active():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        profit=-0.45,
        peak_profit=0.0,
        adverse_risk=True,
        tf_confirm=True,
        hold_strong=False,
        protect_now=True,
        lock_now=False,
        min_target_profit=0.05,
        min_net_guard=0.1,
        exit_detail="unit",
        exit_signal_score=150,
        reverse_signal_threshold=140,
        score_gap=32,
        opposite_score=95.0,
        result={"buy": {"reasons": ["reverse_buy_ready"]}},
        hold_for_adverse=True,
        wait_adverse=True,
        wait_detail="adverse_wait=holding(0.00/0.35)",
    )

    assert candidate["hit"] is False
    assert candidate["defer"] is True
    assert candidate["candidate_kind"] == "adverse_wait"


def test_exit_hard_guard_action_policy_keeps_adverse_protect_when_wait_contract_is_inactive():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        profit=-0.45,
        peak_profit=0.0,
        adverse_risk=True,
        tf_confirm=True,
        hold_strong=False,
        protect_now=True,
        lock_now=False,
        min_target_profit=0.05,
        min_net_guard=0.1,
        exit_detail="unit",
        exit_signal_score=150,
        reverse_signal_threshold=140,
        score_gap=32,
        opposite_score=95.0,
        result={"buy": {"reasons": ["reverse_buy_ready"]}},
        hold_for_adverse=True,
        wait_adverse=False,
    )

    assert candidate["hit"] is True
    assert candidate["defer"] is False
    assert candidate["candidate_kind"] in {"adverse_protect", "adverse_weak_peak_protect"}
    assert candidate["reason"] == "Protect Exit"


def test_exit_hard_guard_action_policy_prefers_protect_for_weak_peak_adverse_case():
    candidate = resolve_exit_hard_guard_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        profit=-0.18,
        peak_profit=0.12,
        adverse_risk=True,
        tf_confirm=False,
        hold_strong=False,
        protect_now=True,
        lock_now=False,
        min_target_profit=0.05,
        min_net_guard=0.1,
        exit_detail="unit",
        exit_signal_score=110,
        reverse_signal_threshold=140,
        score_gap=18,
        opposite_score=72.0,
        result={"buy": {"reasons": []}},
        hold_for_adverse=True,
        wait_adverse=False,
    )

    assert candidate["hit"] is True
    assert candidate["candidate_kind"] == "adverse_weak_peak_protect"
    assert candidate["reason"] == "Protect Exit"
