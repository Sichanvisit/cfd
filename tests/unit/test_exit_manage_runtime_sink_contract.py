from backend.domain.decision_models import WaitState
from backend.services.exit_manage_context_contract import build_exit_manage_context_v1
from backend.services.exit_manage_execution_input_contract import (
    build_exit_manage_execution_input_v1,
)
from backend.services.exit_manage_runtime_sink_contract import (
    build_exit_manage_runtime_sink_v1,
    compact_exit_manage_runtime_sink_v1,
)
from backend.services.exit_wait_taxonomy_contract import build_exit_wait_taxonomy_v1


def _build_execution_input():
    latest_signal_row = {
        "exit_utility_v1": {
            "winner": "wait_exit",
            "decision_reason": "wait_exit_reversal_confirm",
            "utility_exit_now": 0.24,
            "utility_hold": 0.18,
            "utility_reverse": 0.09,
            "utility_wait_exit": 0.31,
            "u_cut_now": 0.11,
            "u_wait_be": 0.07,
            "u_wait_tp1": 0.06,
            "u_reverse": 0.04,
            "p_recover_be": 0.21,
            "p_recover_tp1": 0.14,
            "p_deeper_loss": 0.17,
            "p_reverse_valid": 0.33,
            "wait_selected": True,
            "wait_decision": "wait_exit_reversal_confirm",
        },
        "exit_manage_context_v1": build_exit_manage_context_v1(
            symbol="XAUUSD",
            trade_ctx={
                "entry_setup_id": "range_upper_reversal_sell",
                "management_profile_id": "reversal_profile",
                "invalidation_id": "upper_break_reclaim",
                "exit_profile": "hold_then_trail",
                "direction": "SELL",
            },
            stage_inputs={
                "regime_now": "RANGE",
                "regime_at_entry": "RANGE",
                "current_box_state": "UPPER",
                "current_bb_state": "UPPER_EDGE",
                "entry_direction": "SELL",
                "profit": 0.41,
                "peak_profit": 0.66,
                "duration_sec": 240.0,
            },
            chosen_stage="protect",
            policy_stage="short",
            exec_profile="adaptive",
            confirm_needed=4,
            exit_signal_score=152,
            score_gap=21,
            adverse_risk=True,
            tf_confirm=True,
            detail={"route_txt": "unit-route"},
        ),
        "exit_wait_taxonomy_v1": build_exit_wait_taxonomy_v1(
            wait_state=WaitState(
                phase="exit",
                state="REVERSAL_CONFIRM",
                hard_wait=True,
                reason="opposite_signal_unconfirmed",
            ),
            utility_result={
                "winner": "wait_exit",
                "decision_reason": "wait_exit_reversal_confirm",
                "wait_selected": True,
                "wait_decision": "wait_exit_reversal_confirm",
            },
        ),
        "exit_prediction_v1": {"p_more_profit": 0.28, "p_giveback": 0.54, "p_reverse_valid": 0.33},
    }
    return build_exit_manage_execution_input_v1(
        symbol="XAUUSD",
        ticket=9876,
        direction="SELL",
        trade_ctx={
            "entry_setup_id": "range_upper_reversal_sell",
            "management_profile_id": "reversal_profile",
            "invalidation_id": "upper_break_reclaim",
            "exit_profile": "hold_then_trail",
        },
        latest_signal_row=latest_signal_row,
        exit_wait_state=WaitState(
            phase="exit",
            state="REVERSAL_CONFIRM",
            hard_wait=True,
            reason="opposite_signal_unconfirmed",
        ),
        chosen_stage="protect",
        policy_stage="short",
        exec_profile="adaptive",
        protect_threshold=72,
        lock_threshold=104,
        hold_threshold=52,
        confirm_needed=4,
        delay_ticks=3,
        stage_route={"chosen": "protect", "ev": {"protect": 0.58}, "confidence": 0.74},
        regime_name="RANGE",
        regime_observed="RANGE",
        regime_switch_detail="upper_range_hold",
        peak_profit=0.66,
        giveback_usd=0.25,
        shock_ctx={
            "shock_score": 41.0,
            "shock_level": "MEDIUM",
            "shock_reason": "opposite_score_spike",
            "shock_action": "hold_then_recheck",
            "pre_shock_stage": "mid",
            "post_shock_stage": "short",
            "shock_at_profit": 0.41,
        },
        shock_progress={"shock_hold_delta_30": -0.12, "ticks_elapsed": 16},
    )


def test_exit_manage_runtime_sink_contract_builds_logger_and_live_metrics_payloads():
    sink = build_exit_manage_runtime_sink_v1(
        exit_manage_execution_input_v1=_build_execution_input()
    )

    logger_payload = sink["trade_logger_payload"]
    live_metrics = sink["live_metrics_payload"]

    assert sink["contract_version"] == "exit_manage_runtime_sink_v1"
    assert logger_payload["entry_setup_id"] == "range_upper_reversal_sell"
    assert logger_payload["management_profile_id"] == "reversal_profile"
    assert logger_payload["decision_winner"] == "wait_exit"
    assert logger_payload["exit_wait_selected"] == 1
    assert logger_payload["exit_wait_state_family"] == "confirm_hold"
    assert logger_payload["exit_policy_stage"] == "short"
    assert logger_payload["exit_threshold_triplet"] == "72/104/52"
    assert logger_payload["shock_score"] == 41.0
    assert logger_payload["ticks_elapsed"] == 16
    assert (
        logger_payload["prediction_bundle"]
        == '{"p_more_profit":0.28,"p_giveback":0.54,"p_reverse_valid":0.33}'
    )

    assert live_metrics["decision_winner"] == "wait_exit"
    assert live_metrics["exit_profile"] == "tight_protect"
    assert live_metrics["exit_wait_state"] == "REVERSAL_CONFIRM"
    assert live_metrics["exit_wait_decision"] == "wait_exit_reversal_confirm"
    assert live_metrics["exit_wait_bridge_status"] == "aligned_confirm_wait"
    assert live_metrics["shock_hold_delta_30"] == -0.12


def test_exit_manage_runtime_sink_contract_compacts_summary():
    compact = compact_exit_manage_runtime_sink_v1(
        build_exit_manage_runtime_sink_v1(
            exit_manage_execution_input_v1=_build_execution_input()
        )
    )

    assert compact["contract_version"] == "exit_manage_runtime_sink_v1"
    assert compact["summary"]["decision_winner"] == "wait_exit"
    assert compact["summary"]["exit_wait_state"] == "REVERSAL_CONFIRM"
    assert compact["summary"]["exit_policy_regime"] == "RANGE"
