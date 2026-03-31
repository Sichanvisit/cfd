from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_manage_positions import _resolve_profit_stop_up, _resolve_setup_specific_exit_guard_policy


def test_profit_stop_up_locks_profit_for_tight_buy():
    out = _resolve_profit_stop_up(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        current_price=101.0,
        profit=0.62,
        peak_profit=0.92,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["should_move"] is True
    assert out["reason"] == "profit_lock_stop_up"
    assert 100.0 < out["target_sl"] < 101.0


def test_profit_stop_up_uses_break_even_for_small_green_sell():
    out = _resolve_profit_stop_up(
        pos_type=ORDER_TYPE_SELL,
        entry_price=100.0,
        current_price=99.6,
        profit=0.14,
        peak_profit=0.20,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["should_move"] is True
    assert out["reason"] == "break_even_stop_up"
    assert 99.6 < out["target_sl"] < 100.0


def test_profit_stop_up_skips_when_not_green():
    out = _resolve_profit_stop_up(
        pos_type=ORDER_TYPE_BUY,
        entry_price=100.0,
        current_price=99.7,
        profit=-0.2,
        peak_profit=0.0,
        exit_profile_id="tight_protect",
        chosen_stage="protect",
    )

    assert out["should_move"] is False


def test_nas_upper_reversal_sell_exit_guard_policy_raises_profit_floor():
    out = _resolve_setup_specific_exit_guard_policy(
        symbol="NAS100",
        entry_setup_id="range_upper_reversal_sell",
        side="SELL",
    )

    assert out["min_net_guard_bonus"] >= 0.8
    assert out["min_target_profit_bonus"] >= 0.9


def test_non_nas_exit_guard_policy_keeps_default_profit_floor():
    out = _resolve_setup_specific_exit_guard_policy(
        symbol="BTCUSD",
        entry_setup_id="range_upper_reversal_sell",
        side="SELL",
    )

    assert out["min_net_guard_bonus"] == 0.0
    assert out["min_target_profit_bonus"] == 0.0
