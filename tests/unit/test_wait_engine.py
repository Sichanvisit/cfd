from backend.services.wait_engine import WaitEngine


def test_entry_wait_engine_marks_center_for_middle_box():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="BTCUSD",
        row={
            "symbol": "BTCUSD",
            "action": "BUY",
            "box_state": "MIDDLE",
            "bb_state": "UNKNOWN",
            "blocked_by": "setup_rejected",
            "wait_score": 38.0,
            "wait_conflict": 0.0,
            "wait_noise": 14.0,
            "wait_penalty": 0.0,
        },
    )

    assert wait_state.state == "CENTER"
    assert wait_state.hard_wait is False


def test_entry_wait_engine_marks_against_mode_for_sell_only_buy():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="NAS100",
        row={
            "symbol": "NAS100",
            "action": "BUY",
            "core_allowed_action": "SELL_ONLY",
            "preflight_allowed_action": "SELL_ONLY",
            "wait_score": 12.0,
        },
    )

    assert wait_state.state == "AGAINST_MODE"
    assert wait_state.hard_wait is True


def test_entry_wait_engine_marks_edge_approach_for_btc_lower_mid_observe():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="BTCUSD",
        row={
            "symbol": "BTCUSD",
            "action": "",
            "box_state": "LOWER",
            "bb_state": "MID",
            "blocked_by": "setup_rejected",
            "action_none_reason": "",
            "setup_reason": "lower_approach_observe_wait",
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BOTH",
            "wait_score": 38.0,
            "wait_conflict": 0.0,
            "wait_noise": 14.0,
            "wait_penalty": 0.0,
        },
    )

    assert wait_state.state == "EDGE_APPROACH"
    assert wait_state.hard_wait is False


def test_entry_wait_decision_prefers_wait_for_edge_approach():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row={
            "symbol": "BTCUSD",
            "action": "",
            "box_state": "LOWER",
            "bb_state": "MID",
            "blocked_by": "edge_approach_observe",
            "action_none_reason": "edge_approach_observe",
            "setup_reason": "lower_approach_observe_wait",
            "core_allowed_action": "BUY_ONLY",
            "preflight_allowed_action": "BOTH",
            "wait_score": 38.0,
            "wait_conflict": 0.0,
            "wait_noise": 14.0,
            "wait_penalty": 0.0,
        },
        blocked_reason="edge_approach_observe",
        raw_entry_score=193.0,
        effective_threshold=45.0,
        core_score=0.25,
    )

    assert decision["selected"] is True
    assert decision["decision"] == "wait_soft_edge_approach"


def test_entry_wait_engine_keeps_xau_second_support_probe_active_not_center_noise():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "BUY",
            "box_state": "LOWER",
            "bb_state": "MID",
            "blocked_by": "outer_band_buy_reversal_support_required",
            "wait_score": 34.0,
            "wait_conflict": 0.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "metadata": {
                    "xau_second_support_probe_relief": True,
                },
            },
        },
    )

    assert wait_state.state == "ACTIVE"
    assert wait_state.hard_wait is False
    assert wait_state.reason == "lower_rebound_probe_observe"
    assert wait_state.metadata["blocked_by"] == "outer_band_buy_reversal_support_required"
    assert wait_state.metadata["observe_reason"] == "lower_rebound_probe_observe"
    assert wait_state.metadata["reason_split_v1"]["observe_reason"] == "lower_rebound_probe_observe"
    assert wait_state.metadata["reason_split_v1"]["blocked_by"] == "outer_band_buy_reversal_support_required"
    assert wait_state.metadata["reason_split_v1"]["action_none_reason"] == ""
    assert wait_state.metadata["xau_second_support_probe"] is True


def test_entry_wait_decision_does_not_prefer_wait_for_xau_second_support_probe():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "BUY",
            "box_state": "LOWER",
            "bb_state": "MID",
            "blocked_by": "outer_band_buy_reversal_support_required",
            "wait_score": 34.0,
            "wait_conflict": 0.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "metadata": {
                    "xau_second_support_probe_relief": True,
                },
            },
        },
        blocked_reason="setup_rejected",
        raw_entry_score=132.0,
        effective_threshold=45.0,
        core_score=0.58,
    )

    assert decision["wait_state"].metadata["xau_second_support_probe"] is True
    assert decision["wait_state"].reason == "lower_rebound_probe_observe"
    assert decision["selected"] is False


def test_entry_wait_engine_keeps_xau_upper_sell_probe_active_not_center_noise():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "SELL",
            "box_state": "UPPER",
            "bb_state": "MID",
            "blocked_by": "outer_band_reversal_guard",
            "wait_score": 34.0,
            "wait_conflict": 0.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                },
            },
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "metadata": {},
            },
        },
    )

    assert wait_state.state == "ACTIVE"
    assert wait_state.hard_wait is False
    assert wait_state.reason == "upper_reject_probe_observe"
    assert wait_state.metadata["blocked_by"] == "outer_band_reversal_guard"
    assert wait_state.metadata["observe_reason"] == "upper_reject_probe_observe"
    assert wait_state.metadata["xau_upper_sell_probe"] is True


def test_entry_wait_decision_does_not_prefer_wait_for_xau_upper_sell_probe():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "SELL",
            "box_state": "UPPER",
            "bb_state": "MID",
            "blocked_by": "outer_band_reversal_guard",
            "wait_score": 34.0,
            "wait_conflict": 0.0,
            "wait_noise": 12.0,
            "wait_penalty": 0.0,
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                },
            },
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "metadata": {},
            },
        },
        blocked_reason="setup_rejected",
        raw_entry_score=132.0,
        effective_threshold=45.0,
        core_score=0.58,
    )

    assert decision["wait_state"].metadata["xau_upper_sell_probe"] is True
    assert decision["wait_state"].reason == "upper_reject_probe_observe"
    assert decision["selected"] is False


def test_exit_wait_engine_marks_reversal_confirm_without_tf_confirm():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="XAUUSD",
        trade_ctx={"profit": 0.2},
        stage_inputs={"profit": 0.2, "peak_profit": 0.5},
        adverse_risk=True,
        tf_confirm=False,
        chosen_stage="lock",
        policy_stage="mid",
        confirm_needed=3,
        exit_signal_score=180,
        score_gap=24,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "REVERSAL_CONFIRM"
    assert wait_state.hard_wait is True


def test_exit_wait_engine_marks_recovery_tp1_for_small_loss():
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

    assert wait_state.state == "RECOVERY_TP1"
    assert wait_state.hard_wait is False
    assert wait_state.metadata["exit_manage_context_v1"]["identity"]["entry_setup_id"] == "range_lower_reversal_buy"
    assert wait_state.metadata["exit_manage_context_v1"]["posture"]["policy_stage"] == "short"


def test_exit_wait_engine_trend_pullback_uses_recovery_be_not_tp1():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="NAS100",
        trade_ctx={"profit": -0.22, "entry_setup_id": "trend_pullback_buy"},
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

    assert wait_state.state == "RECOVERY_BE"
    assert wait_state.metadata["recovery_policy_id"] == "trend_pullback"


def test_exit_wait_engine_holds_green_close_when_state_favors_patience():
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

    assert wait_state.state == "ACTIVE"
    assert wait_state.reason == "green_close_hold_bias"
    assert wait_state.metadata["state_exit_bias_v1"]["prefer_hold_through_green"] is True


def test_exit_wait_engine_fast_exit_state_overrides_recovery_wait():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.20, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={
            "profit": -0.20,
            "peak_profit": 0.0,
            "duration_sec": 60.0,
            "entry_direction": "BUY",
            "state_vector_v2": {
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
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=36,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "CUT_IMMEDIATE"
    assert wait_state.reason == "state_fast_exit_cut"
    assert wait_state.metadata["state_exit_bias_v1"]["prefer_fast_cut"] is True


def test_exit_wait_engine_holds_green_close_when_belief_confirms_entry_side():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.24, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.30,
            "duration_sec": 120.0,
            "entry_direction": "BUY",
            "belief_state_v1": {
                "buy_persistence": 0.62,
                "sell_persistence": 0.0,
                "belief_spread": 0.20,
                "dominant_side": "BUY",
                "dominant_mode": "continuation",
                "buy_streak": 3,
                "sell_streak": 0,
                "metadata": {"dominance_deadband": 0.05},
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

    assert wait_state.state == "ACTIVE"
    assert wait_state.reason == "belief_hold_bias"
    assert wait_state.metadata["belief_execution_overrides_v1"]["prefer_hold_extension"] is True


def test_exit_wait_engine_cuts_recovery_when_opposite_belief_strengthens():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.20, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={
            "profit": -0.20,
            "peak_profit": 0.0,
            "duration_sec": 60.0,
            "entry_direction": "BUY",
            "belief_state_v1": {
                "buy_persistence": 0.0,
                "sell_persistence": 0.64,
                "belief_spread": -0.22,
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_streak": 0,
                "sell_streak": 3,
                "metadata": {"dominance_deadband": 0.05},
            },
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=22,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "CUT_IMMEDIATE"
    assert wait_state.reason == "belief_fast_exit_cut"
    assert wait_state.metadata["belief_execution_overrides_v1"]["prefer_fast_cut"] is True


def test_entry_wait_decision_prefers_wait_for_center_rejection():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "BUY",
            "box_state": "MIDDLE",
            "bb_state": "LOWER_EDGE",
            "blocked_by": "setup_rejected",
            "wait_score": 30.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
        },
        blocked_reason="setup_rejected",
        raw_entry_score=42.0,
        effective_threshold=45.0,
        core_score=0.4,
    )

    assert decision["selected"] is True
    assert decision["decision"] == "wait_soft_center"


def test_entry_wait_decision_keeps_skip_without_wait_state():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="NAS100",
        row={
            "symbol": "NAS100",
            "action": "SELL",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "blocked_by": "dynamic_threshold_not_met",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
        },
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=61.0,
        effective_threshold=68.0,
        core_score=0.6,
    )

    assert decision["selected"] is False
    assert decision["decision"] == "skip"


def test_entry_wait_engine_marks_policy_suppressed_from_live_hints():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="BTCUSD",
        row={
            "symbol": "BTCUSD",
            "action": "",
            "blocked_by": "layer_mode_confirm_suppressed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "consumer_layer_mode_suppressed": True,
            "consumer_policy_block_layer": "Barrier",
            "consumer_policy_block_effect": "confirm_to_observe_suppression",
            "wait_score": 8.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
        },
    )

    assert wait_state.state == "POLICY_SUPPRESSED"
    assert wait_state.hard_wait is True
    assert wait_state.reason == "layer_mode_confirm_suppressed"
    assert wait_state.metadata["policy_suppressed"] is True
    assert wait_state.metadata["policy_block_layer"] == "Barrier"


def test_entry_wait_decision_prefers_wait_for_policy_hard_block_even_when_blocked_reason_is_generic():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row={
            "symbol": "BTCUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 6.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_layer_mode_hard_block_active": True,
            "consumer_policy_block_layer": "Barrier",
            "consumer_policy_block_effect": "hard_block",
            "consumer_energy_action_readiness": 0.31,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "barrier_soft_block",
            "consumer_energy_soft_block_strength": 0.81,
        },
        blocked_reason="core_not_passed",
        raw_entry_score=88.0,
        effective_threshold=84.0,
        core_score=0.34,
    )

    assert decision["selected"] is True
    assert decision["decision"] == "wait_policy_hard_block"
    assert decision["policy_hint_applied"] is True
    assert decision["energy_hint_applied"] is True
    assert decision["wait_value"] > decision["enter_value"]


def test_entry_wait_decision_prefers_wait_for_energy_helper_bias_without_policy_block():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_energy_action_readiness": 0.24,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "forecast_wait_bias",
            "consumer_energy_soft_block_strength": 0.72,
        },
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
    )

    assert decision["selected"] is True
    assert decision["decision"] == "wait_soft_helper_block"
    assert decision["policy_hint_applied"] is False
    assert decision["energy_hint_applied"] is True
    assert decision["wait_value"] > decision["enter_value"]


def test_entry_wait_engine_records_energy_usage_trace_for_helper_soft_block_state():
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_energy_action_readiness": 0.24,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "forecast_wait_bias",
            "consumer_energy_soft_block_strength": 0.81,
        },
    )

    trace = wait_state.metadata["entry_wait_energy_usage_trace_v1"]

    assert wait_state.state == "HELPER_SOFT_BLOCK"
    assert wait_state.hard_wait is True
    assert trace["usage_source"] == "recorded"
    assert trace["usage_mode"] == "wait_state_branch_applied"
    assert [record["branch"] for record in trace["branch_records"]] == [
        "helper_soft_block_state",
        "helper_soft_block_hard_wait",
    ]


def test_entry_wait_decision_records_energy_usage_trace_for_helper_block_decision():
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_energy_action_readiness": 0.24,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "forecast_wait_bias",
            "consumer_energy_soft_block_strength": 0.72,
        },
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
    )

    state_trace = decision["entry_wait_energy_usage_trace_v1"]
    decision_trace = decision["entry_wait_decision_energy_usage_trace_v1"]

    assert decision["decision"] == "wait_soft_helper_block"
    assert state_trace["usage_source"] == "recorded"
    assert decision_trace["usage_source"] == "recorded"
    assert decision_trace["usage_mode"] == "wait_decision_branch_applied"
    assert [record["branch"] for record in decision_trace["branch_records"]] == [
        "action_readiness_utility",
        "wait_vs_enter_hint_prefer_wait",
        "soft_block_utility",
        "wait_soft_helper_block_decision",
    ]
    assert (
        decision["wait_state"].metadata["entry_wait_decision_energy_usage_trace_v1"]["branch_records"]
        == decision_trace["branch_records"]
    )


def test_entry_wait_decision_changes_when_wait_vs_enter_hint_flips():
    prefer_wait = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_energy_action_readiness": 0.24,
            "consumer_energy_wait_vs_enter_hint": "prefer_wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "forecast_wait_bias",
            "consumer_energy_soft_block_strength": 0.72,
        },
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
    )
    prefer_enter = WaitEngine.evaluate_entry_wait_decision(
        symbol="XAUUSD",
        row={
            "symbol": "XAUUSD",
            "action": "",
            "blocked_by": "core_not_passed",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "consumer_energy_action_readiness": 0.24,
            "consumer_energy_wait_vs_enter_hint": "prefer_enter",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "forecast_wait_bias",
            "consumer_energy_soft_block_strength": 0.72,
        },
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
    )

    assert prefer_wait["selected"] is True
    assert prefer_wait["decision"] == "wait_soft_helper_block"
    assert prefer_enter["selected"] is True
    assert prefer_enter["decision"] == "wait_soft_helper_soft_block"
    assert prefer_wait["wait_value"] > prefer_enter["wait_value"]
    assert prefer_wait["enter_value"] < prefer_enter["enter_value"]


def test_entry_wait_engine_belief_low_persistence_keeps_wait_lock():
    row = {
        "symbol": "BTCUSD",
        "action": "BUY",
        "blocked_by": "core_not_passed",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "wait_score": 38.0,
        "wait_conflict": 0.0,
        "wait_noise": 0.0,
        "wait_penalty": 0.0,
        "belief_state_v1": {
            "buy_belief": 0.18,
            "sell_belief": 0.15,
            "buy_persistence": 0.20,
            "sell_persistence": 0.0,
            "belief_spread": 0.03,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "buy_streak": 1,
            "sell_streak": 0,
            "transition_age": 0,
            "metadata": {"dominance_deadband": 0.05},
        },
    }
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="BTCUSD",
        row=row,
    )
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=row,
        blocked_reason="core_not_passed",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )

    belief_bias = wait_state.metadata["belief_wait_bias_v1"]

    assert belief_bias["prefer_wait_lock"] is True
    assert belief_bias["persistence_low"] is True
    assert belief_bias["spread_deadband"] is True
    assert decision["selected"] is True
    assert decision["decision"].startswith("wait_")


def test_entry_wait_engine_belief_deadband_keeps_wait_even_with_streak():
    row = {
        "symbol": "BTCUSD",
        "action": "BUY",
        "blocked_by": "dynamic_threshold_not_met",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "wait_score": 40.0,
        "wait_conflict": 0.0,
        "wait_noise": 0.0,
        "wait_penalty": 0.0,
        "belief_state_v1": {
            "buy_belief": 0.34,
            "sell_belief": 0.31,
            "buy_persistence": 0.60,
            "sell_persistence": 0.0,
            "belief_spread": 0.02,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "buy_streak": 3,
            "sell_streak": 0,
            "transition_age": 0,
            "metadata": {"dominance_deadband": 0.05},
        },
    }
    wait_state = WaitEngine.build_entry_wait_state_from_row(
        symbol="BTCUSD",
        row=row,
    )
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=row,
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )

    belief_bias = wait_state.metadata["belief_wait_bias_v1"]

    assert belief_bias["spread_deadband"] is True
    assert belief_bias["prefer_wait_lock"] is True
    assert decision["selected"] is True
    assert decision["decision"].startswith("wait_")


def test_entry_wait_engine_edge_pair_clear_winner_releases_wait():
    base_row = {
        "symbol": "BTCUSD",
        "action": "BUY",
        "blocked_by": "dynamic_threshold_not_met",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "wait_score": 30.0,
        "wait_conflict": 0.0,
        "wait_noise": 0.0,
        "wait_penalty": 0.0,
    }
    row = {
        **base_row,
        "observe_confirm_v2": {
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BUY",
                    "winner_clear": True,
                    "pair_gap": 0.18,
                }
            }
        },
    }
    baseline = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=dict(base_row),
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )
    wait_state = WaitEngine.build_entry_wait_state_from_row(symbol="BTCUSD", row=row)
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=row,
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )

    edge_pair_bias = wait_state.metadata["edge_pair_wait_bias_v1"]

    assert edge_pair_bias["prefer_confirm_release"] is True
    assert edge_pair_bias["prefer_wait_lock"] is False
    assert wait_state.hard_wait is False
    assert decision["enter_value"] > baseline["enter_value"]
    assert decision["wait_value"] < baseline["wait_value"]


def test_entry_wait_engine_edge_pair_unresolved_keeps_wait_lock():
    row = {
        "symbol": "BTCUSD",
        "action": "BUY",
        "blocked_by": "core_not_passed",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "wait_score": 42.0,
        "wait_conflict": 0.0,
        "wait_noise": 0.0,
        "wait_penalty": 0.0,
        "observe_confirm_v2": {
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BALANCED",
                    "winner_clear": False,
                    "pair_gap": 0.02,
                }
            }
        },
    }
    wait_state = WaitEngine.build_entry_wait_state_from_row(symbol="BTCUSD", row=row)
    decision = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=row,
        blocked_reason="core_not_passed",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )

    edge_pair_bias = wait_state.metadata["edge_pair_wait_bias_v1"]

    assert edge_pair_bias["prefer_wait_lock"] is True
    assert edge_pair_bias["prefer_confirm_release"] is False
    assert wait_state.hard_wait is True
    assert decision["selected"] is True
    assert decision["decision"].startswith("wait_")


def test_entry_wait_decision_belief_release_reduces_wait_for_confirmed_buy():
    base_row = {
        "symbol": "BTCUSD",
        "action": "BUY",
        "blocked_by": "dynamic_threshold_not_met",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "wait_score": 32.0,
        "wait_conflict": 0.0,
        "wait_noise": 0.0,
        "wait_penalty": 0.0,
    }
    without_belief = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row=dict(base_row),
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )
    with_belief = WaitEngine.evaluate_entry_wait_decision(
        symbol="BTCUSD",
        row={
            **base_row,
            "belief_state_v1": {
                "buy_belief": 0.48,
                "sell_belief": 0.12,
                "buy_persistence": 0.62,
                "sell_persistence": 0.0,
                "belief_spread": 0.20,
                "dominant_side": "BUY",
                "dominant_mode": "continuation",
                "buy_streak": 3,
                "sell_streak": 0,
                "transition_age": 3,
                "metadata": {"dominance_deadband": 0.05},
            },
        },
        blocked_reason="dynamic_threshold_not_met",
        raw_entry_score=84.0,
        effective_threshold=80.0,
        core_score=0.72,
    )

    assert without_belief["selected"] is True
    assert with_belief["wait_state"].metadata["belief_wait_bias_v1"]["prefer_confirm_release"] is True
    assert with_belief["enter_value"] > without_belief["enter_value"]
    assert with_belief["wait_value"] < without_belief["wait_value"]
    assert with_belief["selected"] is False


def test_exit_utility_decision_prefers_wait_for_recovery():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.4},
        stage_inputs={"profit": -0.4, "peak_profit": 0.0, "duration_sec": 120.0},
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=6,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={"profit": -0.4, "peak_profit": 0.0, "duration_sec": 120.0, "score_gap": 6},
        exit_predictions={"p_more_profit": 0.44, "p_giveback": 0.22, "p_reverse_valid": 0.12},
        wait_predictions={"p_better_exit_if_wait": 0.74, "expected_exit_improvement": 0.42, "expected_miss_cost": 0.08},
        recovery_predictions={"p_recover_be": 0.76, "p_recover_tp1": 0.58, "p_deeper_loss": 0.18, "p_reverse_valid": 0.12},
        exit_profile_id="neutral",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "wait_be"
    assert decision["wait_selected"] is True
    assert decision["decision_reason"] == "wait_be_recovery"
    assert decision["exit_wait_taxonomy_v1"]["state"]["state_family"] == "recovery_hold"
    assert decision["exit_wait_taxonomy_v1"]["decision"]["decision_family"] == "recovery_wait"
    assert decision["exit_wait_taxonomy_v1"]["bridge"]["bridge_status"] == "aligned_recovery_wait"


def test_exit_utility_decision_does_not_pick_reverse_without_ready_state():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.35, "entry_setup_id": "range_lower_reversal_buy"},
        stage_inputs={"profit": -0.35, "peak_profit": 0.0, "duration_sec": 120.0},
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=120,
        score_gap=36,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={"profit": -0.35, "peak_profit": 0.0, "duration_sec": 120.0, "score_gap": 36, "adverse_risk": False},
        exit_predictions={"p_more_profit": 0.22, "p_giveback": 0.55, "p_reverse_valid": 0.90},
        wait_predictions={"p_better_exit_if_wait": 0.40, "expected_exit_improvement": 0.12, "expected_miss_cost": 0.06},
        recovery_predictions={"p_recover_be": 0.62, "p_recover_tp1": 0.46, "p_deeper_loss": 0.22, "p_reverse_valid": 0.92},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] != "reverse_now"


def test_exit_utility_decision_prefers_exit_now_for_tight_protect_positive_profit():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="XAUUSD",
        trade_ctx={"profit": 0.42, "entry_setup_id": "range_upper_reversal_sell"},
        stage_inputs={"profit": 0.42, "peak_profit": 0.86, "duration_sec": 75.0},
        adverse_risk=False,
        tf_confirm=False,
        chosen_stage="lock",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=24,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="XAUUSD",
        wait_state=wait_state,
        stage_inputs={"profit": 0.42, "peak_profit": 0.86, "duration_sec": 75.0, "score_gap": 0, "adverse_risk": False},
        exit_predictions={"p_more_profit": 0.48, "p_giveback": 0.44, "p_reverse_valid": 0.08},
        wait_predictions={"p_better_exit_if_wait": 0.28, "expected_exit_improvement": 0.12, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.20, "p_recover_tp1": 0.12, "p_deeper_loss": 0.34, "p_reverse_valid": 0.08},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "exit_now"


def test_exit_wait_engine_marks_range_middle_observe_for_green_trade():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.22, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.22,
            "peak_profit": 0.31,
            "duration_sec": 60.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=24,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "ACTIVE"
    assert wait_state.reason == "range_middle_observe"


def test_exit_utility_decision_prefers_exit_now_when_range_sell_reaches_lower_edge():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.42, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.42,
            "peak_profit": 0.68,
            "duration_sec": 110.0,
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "LOWER_EDGE",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=26,
        score_gap=4,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.42,
            "peak_profit": 0.68,
            "duration_sec": 110.0,
            "score_gap": 4,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "LOWER_EDGE",
            "entry_direction": "SELL",
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.08},
        wait_predictions={"p_better_exit_if_wait": 0.30, "expected_exit_improvement": 0.10, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.18, "p_recover_tp1": 0.08, "p_deeper_loss": 0.30, "p_reverse_valid": 0.08},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "exit_now"
    assert decision["reached_opposite_edge"] is True


def test_exit_utility_decision_prefers_exit_now_for_btc_upper_sell_on_support_bounce_proxy():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.24, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="lock",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.05},
        wait_predictions={"p_better_exit_if_wait": 0.28, "expected_exit_improvement": 0.09, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.12, "p_recover_tp1": 0.08, "p_deeper_loss": 0.28, "p_reverse_valid": 0.05},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "exit_now"
    assert decision["decision_reason"] == "exit_now_best"
    assert decision["btc_upper_support_bounce_exit"] is False


def test_exit_utility_decision_prefers_exit_now_for_btc_upper_sell_on_support_bounce_without_range_regime():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.22, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.22,
            "peak_profit": 0.56,
            "duration_sec": 80.0,
            "regime_now": "EXPANSION",
            "current_box_state": "MIDDLE",
            "current_bb_state": "UNKNOWN",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="lock",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.22,
            "peak_profit": 0.56,
            "duration_sec": 80.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "EXPANSION",
            "current_box_state": "MIDDLE",
            "current_bb_state": "UNKNOWN",
            "entry_direction": "SELL",
        },
        exit_predictions={"p_more_profit": 0.40, "p_giveback": 0.50, "p_reverse_valid": 0.05},
        wait_predictions={"p_better_exit_if_wait": 0.26, "expected_exit_improvement": 0.08, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.12, "p_recover_tp1": 0.08, "p_deeper_loss": 0.28, "p_reverse_valid": 0.05},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "exit_now"
    assert decision["decision_reason"] == "exit_now_best"
    assert decision["btc_upper_support_bounce_exit"] is False


def test_exit_wait_engine_uses_recovery_be_for_btc_upper_sell_balanced_profile():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": -0.12, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": -0.12,
            "peak_profit": 0.0,
            "duration_sec": 25.0,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=18,
        score_gap=6,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "RECOVERY_BE"
    assert wait_state.metadata["recovery_policy_id"] == "range_upper_reversal_sell_btc_balanced"
    assert wait_state.metadata["allow_wait_be"] is True


def test_exit_wait_engine_uses_balanced_recovery_for_nas_upper_sell():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="NAS100",
        trade_ctx={"profit": -0.12, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": -0.12,
            "peak_profit": 0.0,
            "duration_sec": 25.0,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=18,
        score_gap=6,
        detail={"route_txt": "unit"},
    )

    assert wait_state.state == "RECOVERY_TP1"
    assert wait_state.metadata["recovery_policy_id"] == "range_upper_reversal_sell_nas_balanced"
    assert wait_state.metadata["allow_wait_be"] is True
    assert wait_state.metadata["allow_wait_tp1"] is True


def test_exit_utility_decision_prefers_not_to_exit_now_for_nas_upper_sell_before_opposite_edge():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="NAS100",
        trade_ctx={"profit": 0.24, "entry_setup_id": "breakout_retest_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="NAS100",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.05},
        wait_predictions={"p_better_exit_if_wait": 0.28, "expected_exit_improvement": 0.09, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.12, "p_recover_tp1": 0.08, "p_deeper_loss": 0.28, "p_reverse_valid": 0.05},
        exit_profile_id="hold_then_trail",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] != "exit_now"
    assert decision["nas_upper_hold_bias"] is True


def test_exit_wait_engine_marks_balanced_policy_for_nas_lower_buy():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="NAS100",
        trade_ctx={"profit": -0.14, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": -0.14,
            "peak_profit": 0.0,
            "duration_sec": 45.0,
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "LOWER_EDGE",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="protect",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=4,
        detail={"route_txt": "unit"},
    )

    assert wait_state.metadata["recovery_policy_id"] == "range_lower_reversal_buy_nas_balanced"
    assert wait_state.metadata["allow_wait_be"] is True
    assert wait_state.metadata["allow_wait_tp1"] is True


def test_exit_utility_decision_prefers_not_to_exit_now_for_nas_lower_buy_before_upper_edge():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="NAS100",
        trade_ctx={"profit": 0.24, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="NAS100",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.24,
            "peak_profit": 0.54,
            "duration_sec": 55.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.42, "p_giveback": 0.48, "p_reverse_valid": 0.05},
        wait_predictions={"p_better_exit_if_wait": 0.28, "expected_exit_improvement": 0.09, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.12, "p_recover_tp1": 0.08, "p_deeper_loss": 0.28, "p_reverse_valid": 0.05},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] != "exit_now"
    assert decision["lower_reversal_hold_bias"] is True


def test_exit_utility_decision_prefers_exit_now_for_btc_upper_sell_after_small_green_peak():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.09, "entry_setup_id": "range_upper_reversal_sell", "direction": "SELL"},
        stage_inputs={
            "profit": 0.09,
            "peak_profit": 0.18,
            "duration_sec": 40.0,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "SELL",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="lock",
        policy_stage="short",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.09,
            "peak_profit": 0.18,
            "duration_sec": 40.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "SELL",
        },
        exit_predictions={"p_more_profit": 0.44, "p_giveback": 0.46, "p_reverse_valid": 0.05},
        wait_predictions={"p_better_exit_if_wait": 0.22, "expected_exit_improvement": 0.08, "expected_miss_cost": 0.10},
        recovery_predictions={"p_recover_be": 0.22, "p_recover_tp1": 0.12, "p_deeper_loss": 0.28, "p_reverse_valid": 0.05},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["winner"] == "exit_now"
    assert decision["decision_reason"] == "exit_now_best"
    assert decision["u_wait_be"] > -999.0


def test_exit_utility_decision_keeps_btc_lower_reversal_buy_holding_through_mid_noise():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.14, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.14,
            "peak_profit": 0.26,
            "duration_sec": 90.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=14,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.14,
            "peak_profit": 0.26,
            "duration_sec": 90.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.40, "p_giveback": 0.46, "p_reverse_valid": 0.04},
        wait_predictions={"p_better_exit_if_wait": 0.30, "expected_exit_improvement": 0.10, "expected_miss_cost": 0.09},
        recovery_predictions={"p_recover_be": 0.16, "p_recover_tp1": 0.10, "p_deeper_loss": 0.26, "p_reverse_valid": 0.04},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["btc_lower_hold_bias"] is True
    assert decision["btc_lower_mid_noise_hold_bias"] is True
    assert decision["winner"] != "exit_now"


def test_exit_utility_decision_keeps_btc_lower_reversal_buy_active_after_partial_giveback():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="BTCUSD",
        trade_ctx={"profit": 0.00, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.00,
            "peak_profit": 0.18,
            "duration_sec": 105.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=True,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="BTCUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.00,
            "peak_profit": 0.18,
            "duration_sec": 105.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.38, "p_giveback": 0.44, "p_reverse_valid": 0.04},
        wait_predictions={"p_better_exit_if_wait": 0.28, "expected_exit_improvement": 0.09, "expected_miss_cost": 0.08},
        recovery_predictions={"p_recover_be": 0.17, "p_recover_tp1": 0.11, "p_deeper_loss": 0.24, "p_reverse_valid": 0.04},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["btc_lower_hold_bias"] is True
    assert decision["btc_lower_mid_noise_hold_bias"] is True
    assert decision["winner"] != "exit_now"


def test_exit_utility_decision_keeps_xau_lower_reversal_buy_holding_through_middle_noise():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="XAUUSD",
        trade_ctx={"profit": 0.18, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.18,
            "peak_profit": 0.42,
            "duration_sec": 120.0,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=False,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=12,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="XAUUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.18,
            "peak_profit": 0.42,
            "duration_sec": 120.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.44, "p_giveback": 0.46, "p_reverse_valid": 0.04},
        wait_predictions={"p_better_exit_if_wait": 0.32, "expected_exit_improvement": 0.12, "expected_miss_cost": 0.09},
        recovery_predictions={"p_recover_be": 0.24, "p_recover_tp1": 0.16, "p_deeper_loss": 0.22, "p_reverse_valid": 0.04},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert wait_state.reason in {"range_middle_observe", "symbol_edge_hold_bias", "belief_hold_bias", "green_close_hold_bias"}
    assert decision["xau_lower_edge_to_edge_hold_bias"] is True
    assert decision["winner"] != "exit_now"


def test_exit_utility_decision_prefers_exit_now_for_xau_lower_buy_at_upper_edge_completion():
    wait_state = WaitEngine.build_exit_wait_state(
        symbol="XAUUSD",
        trade_ctx={"profit": 0.36, "entry_setup_id": "range_lower_reversal_buy", "direction": "BUY"},
        stage_inputs={
            "profit": 0.36,
            "peak_profit": 0.58,
            "duration_sec": 180.0,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "BUY",
        },
        adverse_risk=False,
        tf_confirm=False,
        chosen_stage="hold",
        policy_stage="mid",
        confirm_needed=2,
        exit_signal_score=10,
        score_gap=0,
        detail={"route_txt": "unit"},
    )

    decision = WaitEngine.evaluate_exit_utility_decision(
        symbol="XAUUSD",
        wait_state=wait_state,
        stage_inputs={
            "profit": 0.36,
            "peak_profit": 0.58,
            "duration_sec": 180.0,
            "score_gap": 0,
            "adverse_risk": False,
            "regime_now": "RANGE",
            "current_box_state": "UPPER",
            "current_bb_state": "UPPER_EDGE",
            "entry_direction": "BUY",
        },
        exit_predictions={"p_more_profit": 0.36, "p_giveback": 0.52, "p_reverse_valid": 0.04},
        wait_predictions={"p_better_exit_if_wait": 0.18, "expected_exit_improvement": 0.08, "expected_miss_cost": 0.12},
        recovery_predictions={"p_recover_be": 0.18, "p_recover_tp1": 0.10, "p_deeper_loss": 0.28, "p_reverse_valid": 0.04},
        exit_profile_id="tight_protect",
        roundtrip_cost=0.06,
    )

    assert decision["reached_opposite_edge"] is True
    assert decision["symbol_edge_completion_bias_v1"]["active"] is True
    assert decision["winner"] == "exit_now"
