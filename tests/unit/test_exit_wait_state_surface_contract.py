from backend.services.exit_wait_state_surface_contract import (
    build_exit_wait_state_surface_v1,
    compact_exit_wait_state_surface_v1,
)
from backend.services.storage_compaction import compact_runtime_signal_row
from backend.services.wait_engine import WaitEngine


def _input_contract() -> dict:
    return {
        "contract_version": "exit_wait_state_input_v1",
        "identity": {
            "symbol": "BTCUSD",
            "entry_setup_id": "range_lower_reversal_buy",
            "entry_direction": "BUY",
        },
        "market": {
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "reached_opposite_edge": False,
        },
        "risk": {
            "profit": 0.24,
            "peak_profit": 0.30,
            "giveback": 0.06,
            "duration_sec": 120.0,
            "tf_confirm": False,
            "adverse_risk": False,
            "confirm_needed": 1,
            "exit_signal_score": 0,
            "score_gap": 0,
        },
        "policy": {
            "recovery_policy_id": "range_lower_reversal_buy_btc_balanced",
            "management_profile_id": "reversal_profile",
            "invalidation_id": "lower_support_fail",
            "entry_setup_id": "range_lower_reversal_buy",
            "allow_wait_be": True,
            "allow_wait_tp1": True,
            "prefer_reverse": True,
            "recovery_be_max_loss": 0.90,
            "recovery_tp1_max_loss": 0.35,
            "recovery_wait_max_seconds": 240.0,
            "reverse_score_gap": 18,
        },
        "bias": {
            "state_exit_bias_v1": {
                "prefer_hold_through_green": True,
                "prefer_fast_cut": False,
            },
            "belief_execution_overrides_v1": {
                "prefer_hold_extension": False,
                "prefer_fast_cut": False,
            },
            "symbol_edge_execution_overrides_v1": {
                "prefer_hold_to_opposite_edge": True,
            },
        },
        "detail": {
            "route_txt": "unit",
        },
        "context": {
            "exit_manage_context_v1": {
                "posture": {
                    "chosen_stage": "hold",
                    "policy_stage": "mid",
                }
            }
        },
    }


def test_exit_wait_state_surface_contract_builds_compact_summary():
    surface = build_exit_wait_state_surface_v1(
        exit_wait_state_input_v1=_input_contract(),
        exit_wait_state_policy_v1={
            "contract_version": "exit_wait_state_policy_v1",
            "state": "GREEN_CLOSE",
            "reason": "green_close_hold",
            "hard_wait": False,
            "matched_rule": "green_close",
        },
        exit_wait_state_rewrite_v1={
            "contract_version": "exit_wait_state_rewrite_v1",
            "state": "ACTIVE",
            "reason": "green_close_hold_bias",
            "hard_wait": False,
            "base_state": "GREEN_CLOSE",
            "base_reason": "green_close_hold",
            "base_hard_wait": False,
            "base_matched_rule": "green_close",
            "rewrite_applied": True,
            "rewrite_rule": "state_hold_through_green",
        },
        score=0.06,
        penalty=0.0,
    )
    compact = compact_exit_wait_state_surface_v1(surface)

    assert compact["contract_version"] == "exit_wait_state_surface_v1"
    assert compact["identity"]["symbol"] == "BTCUSD"
    assert compact["state"]["state"] == "ACTIVE"
    assert compact["state"]["base_state"] == "GREEN_CLOSE"
    assert compact["state"]["rewrite_rule"] == "state_hold_through_green"
    assert compact["policy"]["recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert compact["bias"]["state_prefer_hold_through_green"] is True


def test_wait_engine_metadata_includes_exit_wait_state_surface():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.24, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
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
        adverse_risk=False,
        tf_confirm=False,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=1,
        exit_signal_score=0,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    surface = wait_state.metadata["exit_wait_state_surface_v1"]

    assert surface["contract_version"] == "exit_wait_state_surface_v1"
    assert surface["identity"]["symbol"] == "BTCUSD"
    assert surface["state"]["base_state"] == "GREEN_CLOSE"
    assert surface["state"]["state"] == "ACTIVE"
    assert surface["state"]["rewrite_applied"] is True
    assert surface["state"]["rewrite_rule"] == "state_hold_through_green"


def test_compact_runtime_signal_row_exposes_exit_wait_surface_summary():
    row = {
        "symbol": "BTCUSD",
        "time": "2026-03-29T18:40:00+09:00",
        "exit_wait_state_v1": {
            "phase": "exit",
            "state": "ACTIVE",
            "hard_wait": False,
            "score": 0.06,
            "penalty": 0.0,
            "reason": "green_close_hold_bias",
            "metadata": {
                "exit_wait_state_surface_v1": compact_exit_wait_state_surface_v1(
                    build_exit_wait_state_surface_v1(
                        exit_wait_state_input_v1=_input_contract(),
                        exit_wait_state_policy_v1={
                            "contract_version": "exit_wait_state_policy_v1",
                            "state": "GREEN_CLOSE",
                            "reason": "green_close_hold",
                            "hard_wait": False,
                            "matched_rule": "green_close",
                        },
                        exit_wait_state_rewrite_v1={
                            "contract_version": "exit_wait_state_rewrite_v1",
                            "state": "ACTIVE",
                            "reason": "green_close_hold_bias",
                            "hard_wait": False,
                            "base_state": "GREEN_CLOSE",
                            "base_reason": "green_close_hold",
                            "base_hard_wait": False,
                            "base_matched_rule": "green_close",
                            "rewrite_applied": True,
                            "rewrite_rule": "state_hold_through_green",
                        },
                        score=0.06,
                        penalty=0.0,
                    )
                )
            },
        },
    }

    compact = compact_runtime_signal_row(row)

    assert compact["exit_wait_state_surface_v1"]["state"]["base_state"] == "GREEN_CLOSE"
    assert compact["exit_wait_base_state"] == "GREEN_CLOSE"
    assert compact["exit_wait_rewrite_applied"] is True
    assert compact["exit_wait_rewrite_rule"] == "state_hold_through_green"
    assert compact["exit_wait_score"] == 0.06
    assert compact["exit_wait_recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
