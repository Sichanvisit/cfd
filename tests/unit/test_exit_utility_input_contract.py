from backend.services.exit_utility_input_contract import (
    build_exit_utility_input_v1,
    compact_exit_utility_input_v1,
)
from backend.services.wait_engine import WaitEngine


def _build_wait_state():
    return WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.24, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
            "entry_direction": "BUY",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "regime_now": "RANGE",
            "state_vector_v2": {
                "wait_patience_gain": 1.12,
                "hold_patience_gain": 1.24,
                "fast_exit_risk_penalty": 0.18,
                "metadata": {
                    "patience_state_label": "HOLD_FAVOR",
                    "topdown_state_label": "BULL_CONFLUENCE",
                    "execution_friction_state": "LOW_FRICTION",
                    "session_exhaustion_state": "LOW_EXHAUSTION_RISK",
                    "event_risk_state": "LOW_EVENT_RISK",
                },
            },
        },
        adverse_risk=False,
        tf_confirm=False,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=1,
        exit_signal_score=0,
        score_gap=0,
        detail={"route_txt": "unit"},
    )


def test_exit_utility_input_contract_builds_surface_from_wait_state():
    wait_state = _build_wait_state()

    contract = build_exit_utility_input_v1(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
            "state_vector_v2": {
                "wait_patience_gain": 1.12,
                "hold_patience_gain": 1.24,
                "fast_exit_risk_penalty": 0.18,
                "metadata": {
                    "patience_state_label": "HOLD_FAVOR",
                    "topdown_state_label": "BULL_CONFLUENCE",
                    "execution_friction_state": "LOW_FRICTION",
                    "session_exhaustion_state": "LOW_EXHAUSTION_RISK",
                    "event_risk_state": "LOW_EVENT_RISK",
                },
            },
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.08},
        wait_predictions={"p_better_exit_if_wait": 0.30, "expected_exit_improvement": 0.10, "expected_miss_cost": 0.10},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert contract["contract_version"] == "exit_utility_input_v1"
    assert contract["identity"]["symbol"] == "BTCUSD"
    assert contract["identity"]["state"] == "ACTIVE"
    assert contract["identity"]["exit_profile_id"] == "tight_protect"
    assert contract["policy"]["recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert contract["prediction"]["expected_exit_improvement"] == 0.1
    assert contract["bias"]["state_execution_bias_v1"]["prefer_hold_through_green"] is True
    assert contract["context"]["exit_wait_state_surface_v1"]["state"]["base_state"] == "GREEN_CLOSE"


def test_exit_utility_input_contract_compacts_runtime_summary():
    compact = compact_exit_utility_input_v1(
        build_exit_utility_input_v1(
            symbol="BTCUSD",
            wait_state=_build_wait_state(),
            stage_inputs={
                "profit": 0.24,
                "peak_profit": 0.30,
                "duration_sec": 120.0,
                "score_gap": 0,
                "adverse_risk": False,
                "regime_now": "RANGE",
                "current_box_state": "LOWER",
                "current_bb_state": "MID",
                "entry_direction": "BUY",
            },
            exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.08},
            wait_predictions={"p_better_exit_if_wait": 0.30, "expected_exit_improvement": 0.10, "expected_miss_cost": 0.10},
            exit_profile_id="tight_protect",
            roundtrip_cost=0.06,
        )
    )

    assert compact["contract_version"] == "exit_utility_input_v1"
    assert compact["identity"]["symbol"] == "BTCUSD"
    assert compact["risk"]["profit"] == 0.24
    assert compact["prediction"]["p_more_profit"] == 0.42
    assert compact["context"]["exit_wait_state_surface_v1"]["state"]["state"] == "ACTIVE"


def test_wait_engine_exit_utility_decision_exposes_input_and_base_surfaces():
    wait_state = _build_wait_state()

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.08},
        wait_predictions={"p_better_exit_if_wait": 0.30, "expected_exit_improvement": 0.10, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.18, "p_recover_tp1": 0.08, "p_deeper_loss": 0.30, "p_reverse_valid": 0.08},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["exit_utility_input_v1"]["contract_version"] == "exit_utility_input_v1"
    assert decision["exit_utility_input_v1"]["identity"]["symbol"] == "BTCUSD"
    assert decision["exit_utility_base_bundle_v1"]["contract_version"] == "exit_utility_base_bundle_v1"
    assert decision["exit_utility_base_bundle_v1"]["identity"]["state"] == "ACTIVE"
    assert decision["exit_utility_base_bundle_v1"]["inputs"]["locked_profit"] == 0.24
    assert (
        decision["exit_recovery_utility_bundle_v1"]["contract_version"]
        == "exit_recovery_utility_bundle_v1"
    )
    assert (
        decision["exit_reverse_eligibility_v1"]["contract_version"]
        == "exit_reverse_eligibility_v1"
    )
    assert (
        decision["exit_utility_scene_bias_bundle_v1"]["contract_version"]
        == "exit_utility_scene_bias_bundle_v1"
    )
    assert (
        decision["exit_utility_decision_policy_v1"]["contract_version"]
        == "exit_utility_decision_policy_v1"
    )
