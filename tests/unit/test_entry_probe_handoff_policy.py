from backend.services.entry_probe_handoff_policy import resolve_entry_probe_ready_handoff_v1


def test_probe_handoff_keeps_values_when_probe_not_ready():
    out = resolve_entry_probe_ready_handoff_v1(
        probe_plan_v1={"active": True, "ready_for_entry": False},
        consumer_archetype_id="upper_reject_sell",
        consumer_invalidation_id="custom_invalidation",
        consumer_management_profile_id="custom_profile",
        default_side_gate_v1={"acting_archetype": "lower_hold_buy"},
    )

    assert out["probe_ready_handoff"] is False
    assert out["consumer_archetype_id"] == "upper_reject_sell"
    assert out["consumer_invalidation_id"] == "custom_invalidation"
    assert out["consumer_management_profile_id"] == "custom_profile"


def test_probe_handoff_fills_missing_fields_from_default_side_gate_archetype():
    out = resolve_entry_probe_ready_handoff_v1(
        probe_plan_v1={"active": True, "ready_for_entry": True},
        consumer_archetype_id="",
        consumer_invalidation_id="",
        consumer_management_profile_id="",
        default_side_gate_v1={
            "acting_archetype": "lower_hold_buy",
            "winner_archetype": "lower_break_sell",
        },
    )

    assert out["probe_ready_handoff"] is True
    assert out["fallback_archetype"] == "lower_hold_buy"
    assert out["consumer_archetype_id"] == "lower_hold_buy"
    assert out["consumer_invalidation_id"] == "lower_support_fail"
    assert out["consumer_management_profile_id"] == "support_hold_profile"


def test_probe_handoff_preserves_explicit_profile_values():
    out = resolve_entry_probe_ready_handoff_v1(
        probe_plan_v1={"active": True, "ready_for_entry": True},
        consumer_archetype_id="upper_reject_sell",
        consumer_invalidation_id="keep_this_invalidation",
        consumer_management_profile_id="keep_this_profile",
        default_side_gate_v1={"acting_archetype": "lower_hold_buy"},
    )

    assert out["probe_ready_handoff"] is True
    assert out["consumer_archetype_id"] == "upper_reject_sell"
    assert out["consumer_invalidation_id"] == "keep_this_invalidation"
    assert out["consumer_management_profile_id"] == "keep_this_profile"
