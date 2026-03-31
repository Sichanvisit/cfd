from backend.services.entry_try_open_entry import _resolve_setup_specific_pyramid_policy


def test_xau_breakout_sell_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="XAUUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="LOWER",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_xau_range_upper_sell_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="XAUUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        preflight_allowed_action="BOTH",
        box_state="UPPER",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_nas_range_lower_buy_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001


def test_nas_breakout_sell_relaxes_first_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] < 0.001


def test_nas_breakout_sell_relaxes_second_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="NAS100",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=2,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.0004


def test_btc_breakout_sell_relaxes_more_aggressively_for_first_addon():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00035


def test_btc_breakout_sell_relaxes_second_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
        box_state="BELOW",
        same_dir_count=2,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00022


def test_btc_breakout_sell_relaxes_more_aggressively_for_first_addon_when_preflight_is_both():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="breakout_retest_sell",
        preflight_allowed_action="BOTH",
        box_state="BELOW",
        same_dir_count=1,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "progressive"
    assert out["require_drawdown"] is False
    assert out["edge_guard"] is False
    assert out["min_prog"] <= 0.00035


def test_btc_upper_shadow_reject_sell_keeps_default_addon_policy():
    out = _resolve_setup_specific_pyramid_policy(
        symbol="BTCUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        preflight_allowed_action="BOTH",
        box_state="ABOVE",
        same_dir_count=3,
        pyramid_mode="adverse",
        require_drawdown=True,
        edge_guard=True,
        min_prog=0.001,
    )

    assert out["pyramid_mode"] == "adverse"
    assert out["require_drawdown"] is True
    assert out["edge_guard"] is True
    assert out["min_prog"] == 0.001
