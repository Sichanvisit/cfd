from backend.services.entry_wait_belief_bias_policy import (
    resolve_entry_wait_acting_side_v1,
    resolve_entry_wait_belief_bias_v1,
)


def test_entry_wait_belief_bias_policy_returns_neutral_defaults_without_belief_state():
    payload = resolve_entry_wait_belief_bias_v1()

    assert payload["present"] is False
    assert payload["acting_side"] == ""
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is False


def test_entry_wait_belief_bias_policy_keeps_wait_lock_for_low_persistence_deadband():
    payload = resolve_entry_wait_belief_bias_v1(
        belief_state_v1={
            "buy_persistence": 0.20,
            "sell_persistence": 0.0,
            "belief_spread": 0.03,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "buy_streak": 1,
            "sell_streak": 0,
        },
        belief_metadata={"dominance_deadband": 0.05},
        action="BUY",
    )

    assert payload["acting_side"] == "BUY"
    assert payload["persistence_low"] is True
    assert payload["spread_deadband"] is True
    assert payload["prefer_wait_lock"] is True


def test_entry_wait_belief_bias_policy_prefers_confirm_release_for_clear_supported_side():
    payload = resolve_entry_wait_belief_bias_v1(
        belief_state_v1={
            "buy_persistence": 0.62,
            "sell_persistence": 0.0,
            "belief_spread": 0.20,
            "dominant_side": "BUY",
            "dominant_mode": "continuation",
            "buy_streak": 3,
            "sell_streak": 0,
        },
        belief_metadata={"dominance_deadband": 0.05},
        action="BUY",
    )

    assert payload["acting_side"] == "BUY"
    assert payload["persistence_high"] is True
    assert payload["spread_clear"] is True
    assert payload["prefer_confirm_release"] is True
    assert payload["enter_value_delta"] > 0.0
    assert payload["wait_value_delta"] < 0.0


def test_entry_wait_belief_bias_policy_keeps_wait_lock_for_dominant_side_mismatch():
    payload = resolve_entry_wait_belief_bias_v1(
        belief_state_v1={
            "buy_persistence": 0.10,
            "sell_persistence": 0.64,
            "belief_spread": -0.22,
            "dominant_side": "SELL",
            "dominant_mode": "reversal",
            "buy_streak": 0,
            "sell_streak": 3,
        },
        belief_metadata={"dominance_deadband": 0.05},
        action="BUY",
    )

    assert payload["acting_side"] == "BUY"
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is True


def test_entry_wait_acting_side_policy_falls_back_to_preflight_then_dominant_side():
    assert (
        resolve_entry_wait_acting_side_v1(
            action="",
            core_allowed_action="NONE",
            preflight_allowed_action="SELL_ONLY",
            dominant_side="BUY",
        )
        == "SELL"
    )
    assert (
        resolve_entry_wait_acting_side_v1(
            action="",
            core_allowed_action="NONE",
            preflight_allowed_action="BOTH",
            dominant_side="BUY",
        )
        == "BUY"
    )
