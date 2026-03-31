from backend.services.exit_recovery_base_policy import resolve_exit_recovery_base_policy_v1


def test_base_policy_uses_default_when_no_mapping_exists():
    policy = resolve_exit_recovery_base_policy_v1(
        symbol="XAUUSD",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "default"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is False
    assert policy["prefer_reverse"] is False


def test_base_policy_prefers_management_profile_before_other_inputs():
    policy = resolve_exit_recovery_base_policy_v1(
        symbol="NAS100",
        management_profile_id="breakout_hold_profile",
        invalidation_id="breakout_failure",
        entry_setup_id="range_upper_reversal_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_hold_profile"
    assert policy["allow_wait_be"] is False
    assert policy["prefer_reverse"] is True


def test_base_policy_uses_btc_range_lower_balanced_profile_even_with_support_hold_management():
    policy = resolve_exit_recovery_base_policy_v1(
        symbol="BTCUSD",
        management_profile_id="support_hold_profile",
        invalidation_id="lower_support_fail",
        entry_setup_id="range_lower_reversal_buy",
        default_be_max_loss_usd=0.20,
        default_tp1_max_loss_usd=0.20,
        default_max_wait_seconds=120,
        default_reverse_score_gap=24,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["allow_wait_tp1"] is True
    assert policy["max_wait_seconds"] >= 300


def test_base_policy_uses_symbol_specific_breakout_retest_variant():
    policy = resolve_exit_recovery_base_policy_v1(
        symbol="XAUUSD",
        entry_setup_id="breakout_retest_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_retest_xau_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["prefer_reverse"] is False


def test_base_policy_uses_invalidation_failure_when_no_higher_priority_mapping_exists():
    policy = resolve_exit_recovery_base_policy_v1(
        invalidation_id="breakdown_failure",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_failure"
    assert policy["allow_wait_be"] is False
    assert policy["prefer_reverse"] is True
