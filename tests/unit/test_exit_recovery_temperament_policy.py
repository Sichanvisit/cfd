from backend.services.exit_recovery_temperament_policy import (
    apply_exit_recovery_temperament_v1,
    resolve_exit_recovery_temperament_bundle_v1,
)


def _base_policy() -> dict:
    return {
        "policy_id": "range_lower_reversal_buy_btc_balanced",
        "symbol": "BTCUSD",
        "management_profile_id": "",
        "invalidation_id": "",
        "entry_setup_id": "range_lower_reversal_buy",
        "allow_wait_be": True,
        "allow_wait_tp1": True,
        "prefer_reverse": False,
        "be_max_loss_usd": 0.24,
        "tp1_max_loss_usd": 0.51,
        "max_wait_seconds": 300,
        "reverse_score_gap": 32,
    }


def test_temperament_bundle_is_neutral_without_state_or_belief():
    bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
    )
    assert bundle["state_execution_overrides_v1"]["active"] is False
    assert bundle["belief_execution_overrides_v1"]["active"] is False
    assert bundle["state_edge_reverse_v1"]["active"] is False
    assert bundle["symbol_edge_execution_overrides_v1"]["active"] is True


def test_temperament_apply_tightens_wait_under_fast_exit_state():
    bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
        state_vector_v2={
            "wait_patience_gain": 0.94,
            "hold_patience_gain": 0.88,
            "fast_exit_risk_penalty": 0.92,
            "metadata": {
                "patience_state_label": "FAST_EXIT_FAVOR",
                "topdown_state_label": "TOPDOWN_CONFLICT",
                "execution_friction_state": "HIGH_FRICTION",
                "session_exhaustion_state": "HIGH_EXHAUSTION_RISK",
                "event_risk_state": "HIGH_EVENT_RISK",
            },
        },
    )
    policy = apply_exit_recovery_temperament_v1(
        base_policy=_base_policy(),
        temperament_bundle=bundle,
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["max_wait_seconds"] < 300
    assert policy["allow_wait_tp1"] is False
    assert policy["state_execution_overrides_v1"]["force_disable_wait_tp1"] is True


def test_temperament_apply_extends_wait_for_same_side_belief():
    bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
        belief_state_v1={
            "buy_persistence": 0.62,
            "sell_persistence": 0.0,
            "belief_spread": 0.20,
            "dominant_side": "BUY",
            "dominant_mode": "continuation",
            "buy_streak": 3,
            "sell_streak": 0,
            "metadata": {"dominance_deadband": 0.05},
        },
    )
    policy = apply_exit_recovery_temperament_v1(
        base_policy=_base_policy(),
        temperament_bundle=bundle,
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["max_wait_seconds"] > 300
    assert policy["belief_execution_overrides_v1"]["prefer_hold_extension"] is True
    assert policy["belief_execution_overrides_v1"]["same_side_confirmed"] is True


def test_temperament_apply_prefers_reverse_in_edge_rotation_scene():
    bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol="BTCUSD",
        entry_setup_id="range_upper_reversal_sell",
        entry_direction="SELL",
        state_vector_v2={
            "wait_patience_gain": 1.00,
            "hold_patience_gain": 1.10,
            "fast_exit_risk_penalty": 0.08,
            "metadata": {
                "regime_state_label": "RANGE_SWING",
                "session_regime_state": "SESSION_EDGE_ROTATION",
                "topdown_confluence_state": "WEAK_CONFLUENCE",
                "execution_friction_state": "MEDIUM_FRICTION",
                "patience_state_label": "WAIT_FAVOR",
            },
        },
    )
    policy = apply_exit_recovery_temperament_v1(
        base_policy={
            **_base_policy(),
            "policy_id": "range_upper_reversal_sell_btc_balanced",
            "entry_setup_id": "range_upper_reversal_sell",
            "reverse_score_gap": 24,
        },
        temperament_bundle=bundle,
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["prefer_reverse"] is True
    assert policy["reverse_score_gap"] < 24
    assert policy["state_edge_reverse_v1"]["active"] is True


def test_temperament_bundle_preserves_symbol_edge_payload():
    bundle = resolve_exit_recovery_temperament_bundle_v1(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
    )
    assert bundle["symbol_edge_execution_overrides_v1"]["active"] is True
    assert bundle["symbol_edge_execution_overrides_v1"]["scene_id"] == "btc_lower_edge_noise_hold_buy"
