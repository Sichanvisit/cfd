from backend.services.exit_profile_identity_policy import resolve_exit_profile_identity_v1


def test_identity_prefers_management_profile():
    identity = resolve_exit_profile_identity_v1(
        management_profile_id="breakout_hold_profile",
        invalidation_id="breakout_failure",
        entry_setup_id="range_upper_reversal_sell",
    )
    assert identity["profile_id"] == "hold_then_trail"
    assert identity["source"] == "management_profile"


def test_identity_uses_invalidation_when_management_profile_missing():
    identity = resolve_exit_profile_identity_v1(
        invalidation_id="lower_support_fail",
        entry_setup_id="trend_pullback_buy",
        fallback_profile="neutral",
    )
    assert identity["profile_id"] == "tight_protect"
    assert identity["source"] == "invalidation"


def test_identity_uses_entry_setup_when_higher_priority_ids_missing():
    identity = resolve_exit_profile_identity_v1(
        entry_setup_id="trend_pullback_sell",
        fallback_profile="neutral",
    )
    assert identity["profile_id"] == "protect_then_hold"
    assert identity["source"] == "entry_setup"


def test_identity_keeps_normalized_fallback_when_no_mapping_exists():
    identity = resolve_exit_profile_identity_v1(
        management_profile_id="",
        invalidation_id="",
        entry_setup_id="",
        fallback_profile=" Hold_Then_Trail ",
    )
    assert identity["profile_id"] == "hold_then_trail"
    assert identity["source"] == "fallback"


def test_identity_defaults_to_neutral_when_fallback_blank():
    identity = resolve_exit_profile_identity_v1()
    assert identity["profile_id"] == "neutral"
    assert identity["fallback_profile"] == "neutral"
