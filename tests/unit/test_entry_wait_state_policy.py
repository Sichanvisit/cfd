from backend.services.entry_wait_state_policy import resolve_entry_wait_state_policy_v1


def test_entry_wait_state_policy_marks_policy_suppressed_as_hard_wait():
    policy = resolve_entry_wait_state_policy_v1(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        blocked_by="layer_mode_confirm_suppressed",
        policy_suppressed=True,
        wait_score=8.0,
        wait_soft=45.0,
        wait_hard=70.0,
    )

    assert policy["state"] == "POLICY_SUPPRESSED"
    assert policy["hard_wait"] is True
    assert policy["reason"] == "layer_mode_confirm_suppressed"


def test_entry_wait_state_policy_keeps_xau_second_support_probe_active():
    policy = resolve_entry_wait_state_policy_v1(
        symbol="XAUUSD",
        action="BUY",
        box_state="LOWER",
        bb_state="MID",
        blocked_by="outer_band_buy_reversal_support_required",
        observe_reason="lower_rebound_probe_observe",
        wait_score=34.0,
        wait_conflict=0.0,
        wait_noise=12.0,
        wait_soft=45.0,
        wait_hard=70.0,
        observe_metadata={"xau_second_support_probe_relief": True},
    )

    assert policy["state"] == "ACTIVE"
    assert policy["hard_wait"] is False
    assert policy["xau_second_support_probe"] is True


def test_entry_wait_state_policy_belief_confirm_release_unlocks_hard_wait():
    policy = resolve_entry_wait_state_policy_v1(
        symbol="BTCUSD",
        action="BUY",
        blocked_by="core_not_passed",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        wait_score=38.0,
        wait_conflict=0.0,
        wait_noise=0.0,
        wait_soft=45.0,
        wait_hard=70.0,
        belief_wait_bias_v1={"prefer_confirm_release": True},
    )

    assert policy["state"] == "ACTIVE"
    assert policy["hard_wait"] is False
