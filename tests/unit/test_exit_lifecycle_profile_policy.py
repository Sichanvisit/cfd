from backend.services.exit_lifecycle_profile_policy import apply_exit_lifecycle_profile_v1


def test_lifecycle_keeps_profile_outside_range():
    result = apply_exit_lifecycle_profile_v1(
        base_profile="hold_then_trail",
        regime_name="trend",
        current_box_state="middle",
    )
    assert result["profile_id"] == "hold_then_trail"
    assert result["applied"] is False
    assert result["reason"] == "no_change"


def test_lifecycle_tightens_hold_then_trail_inside_range():
    result = apply_exit_lifecycle_profile_v1(
        base_profile="hold_then_trail",
        regime_name="RANGE",
        current_box_state="LOWER",
    )
    assert result["profile_id"] == "tight_protect"
    assert result["applied"] is True
    assert result["reason"] == "range_hold_then_trail_tighten"


def test_lifecycle_tightens_protect_then_hold_in_range_middle():
    result = apply_exit_lifecycle_profile_v1(
        base_profile="protect_then_hold",
        regime_name="RANGE",
        current_box_state="middle",
    )
    assert result["profile_id"] == "tight_protect"
    assert result["applied"] is True
    assert result["reason"] == "range_middle_protect_then_hold_tighten"


def test_lifecycle_keeps_profile_when_range_but_no_adjustment_needed():
    result = apply_exit_lifecycle_profile_v1(
        base_profile="protect_then_hold",
        regime_name="RANGE",
        current_box_state="UPPER",
    )
    assert result["profile_id"] == "protect_then_hold"
    assert result["applied"] is False
    assert result["reason"] == "no_change"
