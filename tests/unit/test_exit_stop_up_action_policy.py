from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_stop_up_action_policy import (
    resolve_exit_stop_up_action_candidate_v1,
)


def test_exit_stop_up_action_candidate_locks_profit_for_tight_buy():
    out = resolve_exit_stop_up_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        current_price=101.0,
        profit=0.62,
        peak_profit=0.92,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["contract_version"] == "exit_stop_up_action_candidate_v1"
    assert out["should_move"] is True
    assert out["candidate_kind"] == "profit_lock_stop_up"
    assert 100.0 < float(out["target_sl"]) < 101.0


def test_exit_stop_up_action_candidate_uses_break_even_for_small_green_sell():
    out = resolve_exit_stop_up_action_candidate_v1(
        pos_type=ORDER_TYPE_SELL,
        entry_price=100.0,
        current_price=99.6,
        profit=0.14,
        peak_profit=0.20,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["should_move"] is True
    assert out["candidate_kind"] == "break_even_stop_up"
    assert 99.6 < float(out["target_sl"]) < 100.0


def test_exit_stop_up_action_candidate_skips_when_not_green():
    out = resolve_exit_stop_up_action_candidate_v1(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        current_price=99.7,
        profit=-0.2,
        peak_profit=0.0,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["should_move"] is False
    assert out["candidate_kind"] == "none"
