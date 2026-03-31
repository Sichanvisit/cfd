from backend.services.exit_wait_state_rewrite_policy import apply_exit_wait_state_rewrite_v1
from backend.services.wait_engine import WaitEngine


def _contract(
    *,
    identity: dict | None = None,
    market: dict | None = None,
    risk: dict | None = None,
    policy: dict | None = None,
    bias: dict | None = None,
) -> dict:
    return {
        "identity": {
            "symbol": "BTCUSD",
            "entry_direction": "BUY",
            **(identity or {}),
        },
        "market": {
            "current_box_state": "LOWER",
            "current_bb_state": "MID",
            "reached_opposite_edge": False,
            **(market or {}),
        },
        "risk": {
            "profit": 0.24,
            "adverse_risk": False,
            "tf_confirm": False,
            "score_gap": 0,
            **(risk or {}),
        },
        "policy": {
            "recovery_be_max_loss": 0.90,
            "recovery_tp1_max_loss": 0.35,
            "reverse_score_gap": 18,
            **(policy or {}),
        },
        "bias": {
            "state_exit_bias_v1": {},
            "belief_execution_overrides_v1": {},
            "symbol_edge_execution_overrides_v1": {},
            **(bias or {}),
        },
    }


def _base_policy(*, state: str, reason: str, hard_wait: bool = False, matched_rule: str = "") -> dict:
    return {
        "state": state,
        "reason": reason,
        "hard_wait": hard_wait,
        "matched_rule": matched_rule,
    }


def test_exit_wait_state_rewrite_policy_promotes_green_close_from_state_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            bias={
                "state_exit_bias_v1": {"prefer_hold_through_green": True},
            }
        ),
        base_state_policy_v1=_base_policy(
            state="GREEN_CLOSE",
            reason="green_close_hold",
            matched_rule="green_close",
        ),
    )

    assert resolution["state"] == "ACTIVE"
    assert resolution["reason"] == "green_close_hold_bias"
    assert resolution["base_state"] == "GREEN_CLOSE"
    assert resolution["rewrite_applied"] is True
    assert resolution["rewrite_rule"] == "state_hold_through_green"


def test_exit_wait_state_rewrite_policy_promotes_green_close_from_belief_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            bias={
                "belief_execution_overrides_v1": {"prefer_hold_extension": True},
            }
        ),
        base_state_policy_v1=_base_policy(
            state="GREEN_CLOSE",
            reason="green_close_hold",
            matched_rule="green_close",
        ),
    )

    assert resolution["state"] == "ACTIVE"
    assert resolution["reason"] == "belief_hold_bias"
    assert resolution["rewrite_rule"] == "belief_hold_extension"


def test_exit_wait_state_rewrite_policy_promotes_green_close_from_symbol_edge_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            bias={
                "symbol_edge_execution_overrides_v1": {"prefer_hold_to_opposite_edge": True},
            }
        ),
        base_state_policy_v1=_base_policy(
            state="GREEN_CLOSE",
            reason="green_close_hold",
            matched_rule="green_close",
        ),
    )

    assert resolution["state"] == "ACTIVE"
    assert resolution["reason"] == "symbol_edge_hold_bias"
    assert resolution["rewrite_rule"] == "symbol_edge_hold_to_opposite_edge"


def test_exit_wait_state_rewrite_policy_cuts_recovery_from_state_fast_cut_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            risk={
                "profit": -0.72,
                "adverse_risk": False,
                "tf_confirm": True,
                "score_gap": 24,
            },
            bias={
                "state_exit_bias_v1": {"prefer_fast_cut": True},
            },
        ),
        base_state_policy_v1=_base_policy(
            state="RECOVERY_BE",
            reason="recovery_to_breakeven",
            matched_rule="recovery_be",
        ),
    )

    assert resolution["state"] == "CUT_IMMEDIATE"
    assert resolution["reason"] == "state_fast_exit_cut"
    assert resolution["hard_wait"] is False
    assert resolution["rewrite_rule"] == "state_fast_cut_recovery"


def test_exit_wait_state_rewrite_policy_cuts_recovery_from_belief_fast_cut_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            risk={
                "profit": -0.20,
                "adverse_risk": False,
                "tf_confirm": True,
                "score_gap": 22,
            },
            bias={
                "belief_execution_overrides_v1": {"prefer_fast_cut": True},
            },
        ),
        base_state_policy_v1=_base_policy(
            state="RECOVERY_BE",
            reason="recovery_to_breakeven",
            matched_rule="recovery_be",
        ),
    )

    assert resolution["state"] == "CUT_IMMEDIATE"
    assert resolution["reason"] == "belief_fast_exit_cut"
    assert resolution["rewrite_rule"] == "belief_fast_cut_recovery"


def test_exit_wait_state_rewrite_policy_cuts_none_from_state_fast_cut_bias():
    resolution = apply_exit_wait_state_rewrite_v1(
        exit_wait_state_input_v1=_contract(
            risk={
                "profit": -0.20,
                "adverse_risk": False,
                "tf_confirm": True,
                "score_gap": 24,
            },
            bias={
                "state_exit_bias_v1": {"prefer_fast_cut": True},
            },
        ),
        base_state_policy_v1=_base_policy(
            state="NONE",
            reason="",
            matched_rule="none",
        ),
    )

    assert resolution["state"] == "CUT_IMMEDIATE"
    assert resolution["reason"] == "state_fast_exit_cut"
    assert resolution["rewrite_rule"] == "state_fast_cut_none"


def test_wait_engine_metadata_includes_exit_wait_state_rewrite_summary():
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

    rewrite_summary = wait_state.metadata["exit_wait_state_rewrite_v1"]

    assert rewrite_summary["contract_version"] == "exit_wait_state_rewrite_v1"
    assert rewrite_summary["base_state"] == "GREEN_CLOSE"
    assert rewrite_summary["state"] == "ACTIVE"
    assert rewrite_summary["reason"] == "green_close_hold_bias"
    assert rewrite_summary["rewrite_applied"] is True
