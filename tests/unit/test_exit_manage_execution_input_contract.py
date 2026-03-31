from backend.domain.decision_models import WaitState
from backend.services.exit_manage_context_contract import build_exit_manage_context_v1
from backend.services.exit_manage_execution_input_contract import (
    build_exit_manage_execution_input_v1,
    compact_exit_manage_execution_input_v1,
)
from backend.services.exit_wait_taxonomy_contract import build_exit_wait_taxonomy_v1


def _build_latest_signal_row():
    exit_manage_context_v1 = build_exit_manage_context_v1(
        symbol="BTCUSD",
        trade_ctx={
            "entry_setup_id": "range_lower_reversal_buy",
            "management_profile_id": "support_hold_profile",
            "invalidation_id": "lower_support_fail",
            "exit_profile": "tight_protect",
            "direction": "BUY",
        },
        stage_inputs={
            "regime_now": "RANGE",
            "regime_at_entry": "TREND",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
            "profit": 0.34,
            "peak_profit": 0.58,
            "duration_sec": 180.0,
        },
        chosen_stage="hold",
        policy_stage="mid",
        exec_profile="balanced",
        confirm_needed=3,
        exit_signal_score=118,
        score_gap=14,
        adverse_risk=False,
        tf_confirm=False,
        detail={"route_txt": "unit-exit"},
    )
    exit_wait_taxonomy_v1 = build_exit_wait_taxonomy_v1(
        wait_state=WaitState(
            phase="exit",
            state="ACTIVE",
            hard_wait=False,
            reason="green_hold_bias",
        ),
        utility_result={
            "winner": "hold",
            "decision_reason": "hold_has_best_utility",
            "wait_selected": False,
            "wait_decision": "",
        },
    )
    return {
        "exit_utility_v1": {
            "winner": "hold",
            "decision_reason": "hold_has_best_utility",
            "utility_exit_now": 0.18,
            "utility_hold": 0.42,
            "utility_reverse": -0.15,
            "utility_wait_exit": 0.21,
            "u_cut_now": 0.08,
            "u_wait_be": 0.03,
            "u_wait_tp1": 0.05,
            "u_reverse": -0.10,
            "p_recover_be": 0.12,
            "p_recover_tp1": 0.06,
            "p_deeper_loss": 0.22,
            "p_reverse_valid": 0.18,
            "wait_selected": False,
            "wait_decision": "",
        },
        "exit_manage_context_v1": exit_manage_context_v1,
        "exit_wait_taxonomy_v1": exit_wait_taxonomy_v1,
        "exit_prediction_v1": {"p_more_profit": 0.44, "p_giveback": 0.31, "p_reverse_valid": 0.18},
    }


def test_exit_manage_execution_input_contract_builds_manage_surface():
    contract = build_exit_manage_execution_input_v1(
        symbol="BTCUSD",
        ticket=1234,
        direction="BUY",
        trade_ctx={
            "entry_setup_id": "range_lower_reversal_buy",
            "management_profile_id": "support_hold_profile",
            "invalidation_id": "lower_support_fail",
            "exit_profile": "tight_protect",
        },
        latest_signal_row=_build_latest_signal_row(),
        exit_wait_state=WaitState(
            phase="exit",
            state="ACTIVE",
            hard_wait=False,
            reason="green_hold_bias",
        ),
        chosen_stage="hold",
        policy_stage="mid",
        exec_profile="balanced",
        protect_threshold=68,
        lock_threshold=96,
        hold_threshold=48,
        confirm_needed=3,
        delay_ticks=2,
        stage_route={"chosen": "hold", "ev": {"hold": 0.42}, "confidence": 0.66, "hist_n": 14},
        regime_name="RANGE",
        regime_observed="RANGE",
        regime_switch_detail="stable",
        peak_profit=0.58,
        giveback_usd=0.24,
        shock_ctx={"shock_score": 28.5, "shock_level": "LOW", "shock_reason": "spread_jump"},
        shock_progress={"shock_hold_delta_30": -0.04, "ticks_elapsed": 11},
    )

    assert contract["contract_version"] == "exit_manage_execution_input_v1"
    assert contract["identity"]["symbol"] == "BTCUSD"
    assert contract["identity"]["ticket"] == 1234
    assert contract["handoff"]["management_profile_id"] == "support_hold_profile"
    assert contract["posture"]["effective_exit_profile"] == "tight_protect"
    assert contract["decision"]["winner"] == "hold"
    assert contract["wait_state"]["state"] == "ACTIVE"
    assert contract["wait_taxonomy"]["state_family"] == "active_hold"
    assert contract["thresholds"]["exit_threshold_triplet"] == "68/96/48"
    assert contract["regime"]["switch_detail"] == "stable"
    assert contract["shock"]["progress"]["ticks_elapsed"] == 11
    assert contract["runtime"]["exit_prediction_v1"]["p_more_profit"] == 0.44


def test_exit_manage_execution_input_contract_compacts_operating_summary():
    compact = compact_exit_manage_execution_input_v1(
        build_exit_manage_execution_input_v1(
            symbol="BTCUSD",
            ticket=4321,
            direction="SELL",
            trade_ctx={"entry_setup_id": "breakout_retest_sell", "exit_profile": "hold_then_trail"},
            latest_signal_row=_build_latest_signal_row(),
            exit_wait_state={"state": "ACTIVE", "reason": "unit", "hard_wait": False},
            chosen_stage="lock",
            policy_stage="short",
            exec_profile="neutral",
            protect_threshold=60,
            lock_threshold=84,
            hold_threshold=44,
            confirm_needed=2,
            delay_ticks=1,
            stage_route={"chosen": "lock"},
            regime_name="TREND",
            regime_observed="EXPANSION",
            peak_profit=0.70,
            giveback_usd=0.10,
            shock_ctx={"shock_score": 12.0, "shock_level": "LOW"},
        )
    )

    assert compact["contract_version"] == "exit_manage_execution_input_v1"
    assert compact["identity"]["ticket"] == 4321
    assert compact["posture"]["policy_stage"] == "short"
    assert compact["decision"]["winner"] == "hold"
    assert compact["wait"]["state_family"] == "active_hold"
    assert compact["thresholds"]["delay_ticks"] == 1
    assert compact["regime"]["observed"] == "EXPANSION"
    assert compact["shock"]["shock_level"] == "LOW"
