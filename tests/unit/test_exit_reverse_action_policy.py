from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_reverse_action_policy import (
    resolve_exit_adverse_reverse_candidate_v1,
    resolve_exit_reversal_action_candidate_v1,
)


def test_exit_adverse_reverse_candidate_compresses_threshold_with_plus_to_minus():
    candidate = resolve_exit_adverse_reverse_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        exit_signal_score=122,
        reverse_signal_threshold=140,
        score_gap=14,
        plus_to_minus_hint=True,
        opposite_score=87.0,
        result={"sell": {"reasons": ["sell_reverse_ready"]}},
    )

    assert candidate["contract_version"] == "exit_adverse_reverse_candidate_v1"
    assert candidate["should_reverse"] is True
    assert candidate["reverse_action"] == "SELL"
    assert candidate["score_gap_eff"] <= 14


def test_exit_reversal_action_candidate_requires_confirm_streak():
    candidate = resolve_exit_reversal_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        reversal_hit=True,
        streak=2,
        reversal_confirm_needed=3,
        opposite_score=101.0,
        result={"buy": {"reasons": ["buy_reversal_ready"]}},
    )

    assert candidate["should_execute"] is False
    assert candidate["candidate_kind"] == "reversal_hold"


def test_exit_reversal_action_candidate_builds_reverse_surface():
    candidate = resolve_exit_reversal_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        reversal_hit=True,
        streak=3,
        reversal_confirm_needed=3,
        opposite_score=101.0,
        result={"buy": {"reasons": ["buy_reversal_ready"]}},
    )

    assert candidate["should_execute"] is True
    assert candidate["candidate_kind"] == "reversal_execute"
    assert candidate["reverse_action"] == "BUY"
    assert candidate["reverse_reasons"] == ["buy_reversal_ready"]
