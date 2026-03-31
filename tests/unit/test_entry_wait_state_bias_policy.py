from backend.services.entry_wait_state_bias_policy import resolve_entry_wait_state_bias_v1


def test_entry_wait_state_bias_policy_returns_neutral_defaults_without_state_vector():
    payload = resolve_entry_wait_state_bias_v1()

    assert payload["wait_soft_mult"] == 1.0
    assert payload["wait_hard_mult"] == 1.0
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is False


def test_entry_wait_state_bias_policy_prefers_confirm_release_for_high_quality_confirm_state():
    payload = resolve_entry_wait_state_bias_v1(
        state_vector_v2={
            "confirm_aggression_gain": 1.10,
            "wait_patience_gain": 0.96,
            "fast_exit_risk_penalty": 0.10,
        },
        state_metadata={
            "topdown_state_label": "bull_confluence",
            "quality_state_label": "high_quality",
            "patience_state_label": "confirm_favor",
            "execution_friction_state": "low_friction",
            "event_risk_state": "low_event_risk",
        },
    )

    assert payload["prefer_confirm_release"] is True
    assert payload["prefer_wait_lock"] is False
    assert payload["wait_soft_mult"] > 1.0
    assert payload["wait_hard_mult"] > 1.0
    assert payload["quality_state_label"] == "HIGH_QUALITY"


def test_entry_wait_state_bias_policy_prefers_wait_lock_for_high_friction_event_risk():
    payload = resolve_entry_wait_state_bias_v1(
        state_vector_v2={
            "confirm_aggression_gain": 0.98,
            "wait_patience_gain": 1.14,
            "fast_exit_risk_penalty": 0.20,
        },
        state_metadata={
            "quality_state_label": "low_quality",
            "patience_state_label": "wait_favor",
            "execution_friction_state": "high_friction",
            "event_risk_state": "high_event_risk",
        },
    )

    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is True
    assert payload["wait_soft_mult"] < 1.0
    assert payload["wait_hard_mult"] < 1.0


def test_entry_wait_state_bias_policy_clamps_floor_for_extreme_negative_inputs():
    payload = resolve_entry_wait_state_bias_v1(
        state_vector_v2={
            "confirm_aggression_gain": 0.0,
            "wait_patience_gain": 3.0,
            "fast_exit_risk_penalty": 10.0,
        },
        state_metadata={},
    )

    assert payload["wait_soft_mult"] == 0.78
    assert payload["wait_hard_mult"] == 0.74
