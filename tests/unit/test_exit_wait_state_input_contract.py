from backend.services.exit_wait_state_input_contract import (
    build_exit_wait_state_input_v1,
    compact_exit_wait_state_input_v1,
)
from backend.services.wait_engine import WaitEngine


def test_exit_wait_state_input_contract_builds_policy_and_bias_surface():
    contract = build_exit_wait_state_input_v1(
        symbol="BTCUSD",
        trade_ctx={
            "profit": -0.22,
            "entry_setup_id": "range_lower_reversal_buy",
        },
        stage_inputs={
            "profit": -0.22,
            "peak_profit": 0.0,
            "duration_sec": 90.0,
            "entry_direction": "BUY",
            "state_vector_v2": {
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
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=6,
        detail={"route_txt": "unit"},
    )

    assert contract["contract_version"] == "exit_wait_state_input_v1"
    assert contract["identity"]["symbol"] == "BTCUSD"
    assert contract["identity"]["state_payload_source"] == "stage_inputs"
    assert contract["policy"]["recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert contract["policy"]["allow_wait_tp1"] is True
    assert contract["bias"]["state_edge_reverse_v1"]["active"] is True
    assert contract["detail"]["route_txt"] == "unit"
    assert (
        contract["context"]["exit_manage_context_v1"]["posture"]["policy_stage"] == "short"
    )


def test_exit_wait_state_input_contract_compacts_key_runtime_surface():
    contract = build_exit_wait_state_input_v1(
        symbol="XAUUSD",
        trade_ctx={
            "profit": 0.24,
            "entry_setup_id": "range_lower_reversal_buy",
        },
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
            "entry_direction": "BUY",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
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

    compact = compact_exit_wait_state_input_v1(contract)

    assert compact["contract_version"] == "exit_wait_state_input_v1"
    assert compact["identity"]["symbol"] == "XAUUSD"
    assert compact["policy"]["recovery_policy_id"] == "range_lower_reversal_buy_xau_balanced"
    assert compact["bias"]["prefer_hold_through_green"] is True
    assert compact["context"]["exit_manage_context_v1"]["posture"]["policy_stage"] == "mid"


def test_wait_engine_metadata_includes_compact_exit_wait_state_input():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.22, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={"profit": -0.22, "peak_profit": 0.0, "duration_sec": 90.0},
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=6,
        detail={"route_txt": "unit"},
    )

    compact_contract = wait_state.metadata["exit_wait_state_input_v1"]

    assert compact_contract["contract_version"] == "exit_wait_state_input_v1"
    assert compact_contract["identity"]["symbol"] == "BTCUSD"
    assert compact_contract["policy"]["recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert compact_contract["context"]["exit_manage_context_v1"]["posture"]["policy_stage"] == "short"
