from backend.services.entry_probe_plan_policy import resolve_entry_probe_plan_v1


def test_entry_probe_plan_returns_inactive_reason_when_not_observe_stage():
    out = resolve_entry_probe_plan_v1(
        symbol="XAUUSD",
        shadow_action="BUY",
        shadow_side="BUY",
        shadow_stage="CONFIRM",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
            }
        },
        default_side_gate_v1={"winner_side": "BUY"},
    )

    assert out["active"] is False
    assert out["ready_for_entry"] is False
    assert out["reason"] == "probe_not_observe_stage"


def test_entry_probe_plan_blocks_btc_lower_probe_on_pair_gap():
    out = resolve_entry_probe_plan_v1(
        symbol="BTCUSD",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.20,
                "near_confirm": False,
            }
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": 0.05,
            "wait_confirm_gap": 0.02,
            "continue_fail_gap": 0.01,
            "action_confirm_score": 0.26,
            "same_side_persistence": 0.30,
            "same_side_belief": 0.58,
            "same_side_streak": 1,
            "dominant_side": "BUY",
            "dominant_mode": "continuation",
            "pair_gap": 0.07,
            "same_side_barrier": 0.18,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is False
    assert out["reason"] == "probe_pair_gap_not_ready"
    assert out["symbol_scene_relief"] == "btc_lower_buy_conservative_probe"


def test_entry_probe_plan_applies_xau_second_support_structural_relief():
    out = resolve_entry_probe_plan_v1(
        symbol="XAUUSD",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        observe_metadata={
            "xau_second_support_probe_relief": True,
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.852236834869189,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_second_support_buy_probe",
                },
            },
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": -0.1467739361116228,
            "wait_confirm_gap": -0.090749,
            "continue_fail_gap": -0.17040298852170147,
            "action_confirm_score": 0.173233,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.04900711877082087,
            "same_side_streak": 0,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "pair_gap": 0.18737033146923063,
            "same_side_barrier": 0.4634672677886277,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["structural_relief_applied"] is True
    assert out["symbol_scene_relief"] == "xau_second_support_buy_probe"


def test_entry_probe_plan_applies_xau_upper_sell_structural_relief():
    out = resolve_entry_probe_plan_v1(
        symbol="XAUUSD",
        shadow_action="WAIT",
        shadow_side="SELL",
        shadow_stage="OBSERVE",
        box_state="UPPER",
        bb_state="UNKNOWN",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "SELL",
                "trigger_branch": "upper_reject",
                "candidate_support": 0.20,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "SELL",
            "default_side": "SELL",
            "acting_against_default": False,
            "confirm_fake_gap": -0.18,
            "wait_confirm_gap": -0.11,
            "continue_fail_gap": -0.20,
            "action_confirm_score": 0.15,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.02,
            "same_side_streak": 0,
            "dominant_side": "SELL",
            "dominant_mode": "reversal",
            "pair_gap": 0.09,
            "same_side_barrier": 0.46,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["structural_relief_applied"] is True
    assert out["symbol_scene_relief"] == "xau_upper_sell_probe"


def test_entry_probe_plan_applies_nas_clean_confirm_structural_relief_for_near_confirm_probe():
    out = resolve_entry_probe_plan_v1(
        symbol="NAS100",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        box_state="LOWER",
        bb_state="MID",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.12,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "nas_clean_confirm_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": -0.25,
            "wait_confirm_gap": -0.20,
            "continue_fail_gap": -0.27,
            "action_confirm_score": 0.09,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.012,
            "same_side_streak": 0,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "pair_gap": 0.19,
            "same_side_barrier": 0.55,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["structural_relief_applied"] is True
    assert out["symbol_scene_relief"] == "nas_clean_confirm_probe"


def test_entry_probe_plan_applies_nas_clean_confirm_forecast_relief():
    out = resolve_entry_probe_plan_v1(
        symbol="NAS100",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        box_state="LOWER",
        bb_state="MID",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.59,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "nas_clean_confirm_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": -0.28,
            "wait_confirm_gap": -0.19,
            "continue_fail_gap": -0.27,
            "action_confirm_score": 0.10,
            "same_side_persistence": 0.14,
            "same_side_belief": 0.32,
            "same_side_streak": 1,
            "dominant_side": "BUY",
            "dominant_mode": "continuation",
            "pair_gap": 0.05,
            "same_side_barrier": 0.52,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["forecast_support"] is True
    assert out["nas_clean_confirm_forecast_relief"] is True


def test_entry_probe_plan_applies_nas_clean_confirm_against_default_relief_for_upper_reject_sell():
    out = resolve_entry_probe_plan_v1(
        symbol="NAS100",
        shadow_action="WAIT",
        shadow_side="SELL",
        shadow_stage="OBSERVE",
        box_state="LOWER",
        bb_state="UPPER_EDGE",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "SELL",
                "trigger_branch": "upper_reject",
                "candidate_support": 0.34,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "nas_clean_confirm_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "SELL",
            "winner_archetype": "upper_reject_sell",
            "winner_clear": True,
            "default_side": "BUY",
            "acting_side": "SELL",
            "acting_against_default": True,
            "conflict_local_upper_override": True,
            "confirm_fake_gap": -0.27,
            "wait_confirm_gap": -0.25,
            "continue_fail_gap": -0.31,
            "action_confirm_score": 0.05,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.01,
            "same_side_streak": 0,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "pair_gap": 0.31,
            "same_side_barrier": 0.79,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["default_side_aligned"] is True
    assert out["nas_clean_confirm_against_default_relief"] is True


def test_entry_probe_plan_applies_nas_clean_confirm_lower_rebound_buy_relief():
    out = resolve_entry_probe_plan_v1(
        symbol="NAS100",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.67,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "nas_clean_confirm_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": -0.11,
            "wait_confirm_gap": -0.05,
            "continue_fail_gap": -0.19,
            "action_confirm_score": 0.18,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.04,
            "same_side_streak": 0,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "pair_gap": 0.167,
            "same_side_barrier": 0.48,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["forecast_support"] is True
    assert out["belief_support"] is True
    assert out["nas_clean_confirm_lower_rebound_buy_relief"] is True


def test_entry_probe_plan_applies_nas_clean_confirm_lower_rebound_buy_relief_with_live_like_metrics():
    out = resolve_entry_probe_plan_v1(
        symbol="NAS100",
        shadow_action="WAIT",
        shadow_side="BUY",
        shadow_stage="OBSERVE",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        observe_metadata={
            "probe_candidate_v1": {
                "active": True,
                "probe_kind": "edge_probe",
                "probe_direction": "BUY",
                "trigger_branch": "lower_rebound",
                "candidate_support": 0.6523,
                "near_confirm": True,
                "symbol_probe_temperament_v1": {
                    "scene_id": "nas_clean_confirm_probe",
                },
            }
        },
        default_side_gate_v1={
            "winner_side": "BUY",
            "default_side": "BUY",
            "acting_against_default": False,
            "confirm_fake_gap": -0.1667,
            "wait_confirm_gap": -0.1156,
            "continue_fail_gap": -0.2568,
            "action_confirm_score": 0.1374,
            "same_side_persistence": 0.0,
            "same_side_belief": 0.0212,
            "same_side_streak": 0,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "pair_gap": 0.1530,
            "same_side_barrier": 0.5877,
        },
    )

    assert out["active"] is True
    assert out["ready_for_entry"] is True
    assert out["forecast_support"] is True
    assert out["belief_support"] is True
    assert out["barrier_support"] is True
    assert out["nas_clean_confirm_lower_rebound_buy_relief"] is True
