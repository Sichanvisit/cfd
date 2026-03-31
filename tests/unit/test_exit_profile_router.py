from backend.services.exit_profile_router import (
    apply_range_lifecycle_profile,
    resolve_exit_profile,
    resolve_recovery_policy,
)


def test_resolve_exit_profile_maps_range_reversal_to_tight_protect():
    assert resolve_exit_profile(entry_setup_id="range_upper_reversal_sell") == "tight_protect"


def test_resolve_exit_profile_maps_trend_pullback_to_hold_profile():
    assert resolve_exit_profile(entry_setup_id="trend_pullback_buy") == "protect_then_hold"


def test_resolve_exit_profile_maps_breakout_to_trail_profile():
    assert resolve_exit_profile(entry_setup_id="breakout_retest_sell") == "hold_then_trail"


def test_resolve_exit_profile_prefers_management_profile_handoff():
    assert resolve_exit_profile(
        management_profile_id="breakout_hold_profile",
        invalidation_id="breakout_failure",
        entry_setup_id="range_upper_reversal_sell",
    ) == "hold_then_trail"


def test_range_lower_reversal_policy_allows_wait_tp1():
    policy = resolve_recovery_policy(
        entry_setup_id="range_lower_reversal_buy",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_reversal"
    assert policy["allow_wait_tp1"] is True


def test_nas_range_lower_reversal_buy_policy_uses_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="NAS100",
        entry_setup_id="range_lower_reversal_buy",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_nas_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is True
    assert policy["prefer_reverse"] is False
    assert policy["reverse_score_gap"] >= 26


def test_btc_range_lower_reversal_buy_policy_uses_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is True
    assert policy["prefer_reverse"] is False
    assert policy["max_wait_seconds"] >= 300
    assert policy["be_max_loss_usd"] >= 0.24
    assert policy["tp1_max_loss_usd"] >= 0.51
    assert policy["reverse_score_gap"] >= 32


def test_btc_range_lower_reversal_buy_policy_overrides_support_hold_profile_with_balanced_recovery():
    policy = resolve_recovery_policy(
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
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is True
    assert policy["max_wait_seconds"] >= 300
    assert policy["symbol"] == "BTCUSD"
    assert policy["management_profile_id"] == "support_hold_profile"
    assert policy["invalidation_id"] == "lower_support_fail"


def test_btc_range_lower_reversal_buy_policy_prefers_reverse_in_edge_rotation_state():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        state_vector_v2={
            "wait_patience_gain": 1.02,
            "hold_patience_gain": 1.08,
            "fast_exit_risk_penalty": 0.10,
            "metadata": {
                "regime_state_label": "CHOP_NOISE",
                "session_regime_state": "SESSION_EDGE_ROTATION",
                "topdown_confluence_state": "WEAK_CONFLUENCE",
                "execution_friction_state": "MEDIUM_FRICTION",
                "patience_state_label": "WAIT_FAVOR",
            },
        },
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["prefer_reverse"] is True
    assert policy["reverse_score_gap"] < 26
    assert policy["state_edge_reverse_v1"]["active"] is True
    assert policy["state_edge_reverse_v1"]["reason"] == "edge_rotation_reverse_ready"


def test_range_upper_reversal_sell_policy_disables_wait_tp1_and_tightens_limits():
    policy = resolve_recovery_policy(
        symbol="XAUUSD",
        entry_setup_id="range_upper_reversal_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_upper_reversal_sell_tight"
    assert policy["allow_wait_tp1"] is False
    assert policy["be_max_loss_usd"] <= 0.45
    assert policy["max_wait_seconds"] <= 90


def test_btc_range_upper_reversal_sell_policy_allows_wait_be_with_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_upper_reversal_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_upper_reversal_sell_btc_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is False
    assert policy["be_max_loss_usd"] <= 0.45
    assert policy["max_wait_seconds"] <= 90


def test_btc_range_upper_reversal_sell_policy_prefers_reverse_in_edge_rotation_state():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_upper_reversal_sell",
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
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_upper_reversal_sell_btc_balanced"
    assert policy["prefer_reverse"] is True
    assert policy["reverse_score_gap"] < 24
    assert policy["state_edge_reverse_v1"]["active"] is True


def test_nas_range_upper_reversal_sell_policy_allows_wait_tp1_with_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="NAS100",
        entry_setup_id="range_upper_reversal_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_upper_reversal_sell_nas_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is True
    assert policy["prefer_reverse"] is False
    assert policy["be_max_loss_usd"] <= 0.60
    assert policy["max_wait_seconds"] <= 120
    assert policy["reverse_score_gap"] >= 26


def test_breakout_retest_policy_prefers_reverse_and_disables_recovery():
    policy = resolve_recovery_policy(
        entry_setup_id="breakout_retest_buy",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_retest"
    assert policy["allow_wait_be"] is False
    assert policy["allow_wait_tp1"] is False
    assert policy["prefer_reverse"] is True


def test_nas_breakout_retest_sell_policy_uses_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="NAS100",
        entry_setup_id="breakout_retest_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_retest_nas_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is False
    assert policy["prefer_reverse"] is False
    assert policy["be_max_loss_usd"] <= 0.55
    assert policy["max_wait_seconds"] <= 120
    assert policy["reverse_score_gap"] >= 26


def test_xau_breakout_retest_sell_policy_uses_balanced_recovery():
    policy = resolve_recovery_policy(
        symbol="XAUUSD",
        entry_setup_id="breakout_retest_sell",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_retest_xau_balanced"
    assert policy["allow_wait_be"] is True
    assert policy["allow_wait_tp1"] is False
    assert policy["prefer_reverse"] is False
    assert policy["be_max_loss_usd"] <= 0.45
    assert policy["max_wait_seconds"] <= 90
    assert policy["reverse_score_gap"] >= 24


def test_breakout_hold_management_profile_prefers_reverse_without_setup_fallback():
    policy = resolve_recovery_policy(
        management_profile_id="breakout_hold_profile",
        invalidation_id="breakout_failure",
        entry_setup_id="",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "breakout_hold_profile"
    assert policy["allow_wait_be"] is False
    assert policy["allow_wait_tp1"] is False
    assert policy["prefer_reverse"] is True


def test_apply_range_lifecycle_profile_downgrades_breakout_hold_to_tight_protect_in_range():
    assert apply_range_lifecycle_profile(
        base_profile="hold_then_trail",
        regime_name="RANGE",
        current_box_state="MIDDLE",
    ) == "tight_protect"


def test_recovery_policy_extends_wait_under_hold_favor_state():
    policy = resolve_recovery_policy(
        symbol="XAUUSD",
        entry_setup_id="range_lower_reversal_buy",
        state_vector_v2={
            "wait_patience_gain": 1.14,
            "hold_patience_gain": 1.22,
            "fast_exit_risk_penalty": 0.18,
            "metadata": {
                "patience_state_label": "HOLD_FAVOR",
                "topdown_state_label": "BULL_CONFLUENCE",
                "execution_friction_state": "LOW_FRICTION",
                "session_exhaustion_state": "LOW_EXHAUSTION_RISK",
                "event_risk_state": "LOW_EVENT_RISK",
            },
        },
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_xau_balanced"
    assert policy["max_wait_seconds"] > 210
    assert policy["allow_wait_tp1"] is True
    assert policy["state_execution_overrides_v1"]["active"] is True


def test_recovery_policy_tightens_under_high_stress_fast_exit_state():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
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
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["max_wait_seconds"] < 210
    assert policy["allow_wait_tp1"] is False
    assert policy["state_execution_overrides_v1"]["force_disable_wait_tp1"] is True


def test_recovery_policy_extends_wait_when_entry_side_belief_is_confirmed():
    policy = resolve_recovery_policy(
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
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["max_wait_seconds"] > 210
    assert policy["belief_execution_overrides_v1"]["prefer_hold_extension"] is True
    assert policy["belief_execution_overrides_v1"]["same_side_confirmed"] is True


def test_recovery_policy_tightens_when_opposite_belief_rises():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
        belief_state_v1={
            "buy_persistence": 0.0,
            "sell_persistence": 0.64,
            "belief_spread": -0.22,
            "dominant_side": "SELL",
            "dominant_mode": "reversal",
            "buy_streak": 0,
            "sell_streak": 3,
            "metadata": {"dominance_deadband": 0.05},
        },
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["max_wait_seconds"] < 210
    assert policy["allow_wait_tp1"] is False
    assert policy["belief_execution_overrides_v1"]["prefer_fast_cut"] is True
    assert policy["belief_execution_overrides_v1"]["opposite_side_rising"] is True


def test_xau_range_lower_reversal_buy_policy_promotes_edge_to_edge_hold():
    policy = resolve_recovery_policy(
        symbol="XAUUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_xau_balanced"
    assert policy["max_wait_seconds"] >= 255
    assert policy["reverse_score_gap"] >= 26
    assert policy["symbol_edge_execution_overrides_v1"]["active"] is True
    assert policy["symbol_edge_execution_overrides_v1"]["scene_id"] == "xau_lower_edge_to_edge_buy"


def test_btc_range_lower_reversal_buy_policy_emits_symbol_edge_hold_overrides():
    policy = resolve_recovery_policy(
        symbol="BTCUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
        default_be_max_loss_usd=0.9,
        default_tp1_max_loss_usd=0.35,
        default_max_wait_seconds=240,
        default_reverse_score_gap=18,
    )
    assert policy["policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert policy["symbol_edge_execution_overrides_v1"]["active"] is True
    assert policy["symbol_edge_execution_overrides_v1"]["scene_id"] == "btc_lower_edge_noise_hold_buy"
