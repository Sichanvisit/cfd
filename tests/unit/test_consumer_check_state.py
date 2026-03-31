from backend.services.consumer_check_state import (
    build_consumer_check_state_v1,
    evaluate_consumer_open_guard_v1,
    resolve_effective_consumer_check_state_v1,
)


def test_build_consumer_check_state_marks_energy_soft_block_as_blocked():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "core_pass": 1,
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "BLOCKED"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["display_strength_level"] == 5


def test_evaluate_consumer_open_guard_blocks_same_side_blocked_state():
    guard = evaluate_consumer_open_guard_v1(
        consumer_check_state_v1={
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "BLOCKED",
            "check_reason": "lower_rebound_confirm",
            "entry_block_reason": "energy_soft_block",
        },
        action="BUY",
    )

    assert guard["guard_active"] is True
    assert guard["allows_open"] is False
    assert guard["failure_code"] == "consumer_stage_blocked"
    assert guard["entry_block_reason"] == "energy_soft_block"


def test_evaluate_consumer_open_guard_allows_ready_same_side_open():
    guard = evaluate_consumer_open_guard_v1(
        consumer_check_state_v1={
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": True,
            "check_side": "SELL",
            "check_stage": "READY",
            "check_reason": "upper_reject_confirm",
            "entry_block_reason": "",
        },
        action="SELL",
    )

    assert guard["guard_active"] is True
    assert guard["allows_open"] is True
    assert guard["failure_code"] == ""


def test_resolve_effective_consumer_check_state_suppresses_display_for_late_hidden_guard():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": True,
            "check_side": "BUY",
            "check_stage": "READY",
            "check_reason": "lower_rebound_confirm",
            "display_strength_level": 8,
        },
        blocked_by_value="range_lower_buy_requires_lower_edge",
        action_none_reason_value="policy_hard_blocked",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "BLOCKED"
    assert reason == "lower_rebound_confirm"
    assert level == 0
    assert state["blocked_display_reason"] == "range_lower_buy_requires_lower_edge"


def test_resolve_effective_consumer_check_state_downgrades_ready_to_observe_on_late_soft_block():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": True,
            "check_side": "BUY",
            "check_stage": "READY",
            "check_reason": "lower_rebound_confirm",
            "display_strength_level": 8,
        },
        blocked_by_value="energy_soft_block",
        action_none_reason_value="execution_soft_blocked",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_confirm"
    assert level == 5
    assert state["entry_block_reason"] == "execution_soft_blocked"


def test_build_consumer_check_state_downgrades_nas_lower_rebound_probe_to_observe():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "OBSERVE"
    assert state["display_strength_level"] == 5
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_downgrades_nas_lower_rebound_probe_to_observe_under_forecast_guard():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_downgrades_nas_lower_rebound_probe_to_observe_under_barrier_guard():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_marks_nas_lower_recovery_start_as_triple_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "nas_lower_recovery_start"
    assert state["display_importance_tier"] == "high"
    assert state["display_score"] >= 0.90
    assert state["display_repeat_count"] == 3


def test_build_consumer_check_state_marks_nas_structural_observe_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "nas_structural_rebound"
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_marks_nas_upper_support_awareness_as_single_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "nas_upper_support_awareness"
    assert state["display_importance_tier"] == ""
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_marks_nas_breakout_reclaim_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "nas_breakout_reclaim_confirm"
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_restores_nas_breakout_awareness_from_bf1_bridge():
    base_payload = {
        "observe_reason": "lower_rebound_confirm",
        "consumer_effective_action": "BUY",
        "blocked_by": "forecast_guard",
        "action_none_reason": "observe_state_wait",
        "probe_scene_id": "nas_clean_confirm_probe",
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
        "core_pass": 0,
        "entry_probe_plan_v1": {
            "ready_for_entry": True,
            "active": True,
            "candidate_support": 0.55,
            "pair_gap": 0.22,
        },
    }
    bridged_payload = {
        **base_payload,
        "forecast_features_v1": {
            "metadata": {
                "bridge_first_v1": {
                    "act_vs_wait_bias_v1": {
                        "contract_version": "act_vs_wait_bias_v1",
                        "act_vs_wait_bias": 0.64,
                        "false_break_risk": 0.28,
                        "awareness_keep_allowed": True,
                        "reason_summary": "test",
                    }
                }
            }
        },
    }

    base_state = build_consumer_check_state_v1(
        payload=base_payload,
        canonical_symbol="NAS100",
    )
    bridged_state = build_consumer_check_state_v1(
        payload=bridged_payload,
        canonical_symbol="NAS100",
    )

    assert base_state["check_stage"] == "BLOCKED"
    assert base_state["check_display_ready"] is False
    assert base_state["display_importance_source_reason"] == "nas_breakout_reclaim_confirm"
    assert base_state["display_score"] == 0.0
    assert base_state["display_repeat_count"] == 0

    assert bridged_state["check_stage"] == "OBSERVE"
    assert bridged_state["check_display_ready"] is True
    assert bridged_state["entry_ready"] is False
    assert bridged_state["display_importance_source_reason"] == "nas_breakout_reclaim_confirm"
    assert bridged_state["display_importance_tier"] == "medium"
    assert bridged_state["bridge_first_adjustment_reason"] == "bf1_awareness_keep"
    assert bridged_state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert bridged_state["modifier_applied"] is True
    assert bridged_state["modifier_primary_reason"] == "bf1_awareness_keep"
    assert bridged_state["modifier_reason_codes"] == ["bf1_awareness_keep"]
    assert bridged_state["modifier_stage_adjustment"] == "blocked_to_observe"
    assert bridged_state["modifier_score_delta"] > 0.0
    assert bridged_state["bridge_act_vs_wait_bias"] == 0.64
    assert bridged_state["bridge_false_break_risk"] == 0.28
    assert bridged_state["bridge_awareness_keep_allowed"] is True
    assert 0.80 <= bridged_state["display_score"] < 0.90
    assert bridged_state["display_repeat_count"] == 2


def test_build_consumer_check_state_exposes_modifier_contract_without_uplift_when_not_applied():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is False
    assert state["modifier_primary_reason"] == ""
    assert state["modifier_reason_codes"] == []
    assert state["modifier_stage_adjustment"] == "none"
    assert state["modifier_score_delta"] == 0.0


def test_build_consumer_check_state_does_not_uplift_nas_upper_continuation_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_marks_xau_lower_recovery_start_as_triple_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "high"
    assert state["display_score"] >= 0.90
    assert state["display_repeat_count"] == 3


def test_build_consumer_check_state_marks_xau_second_support_observe_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_reversal_guard",
            "action_none_reason": "observe_state_wait",
            "probe_scene_id": "xau_second_support_buy_probe",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_marks_xau_upper_reject_confirm_as_triple_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "high"
    assert state["display_score"] >= 0.90
    assert state["display_repeat_count"] == 3


def test_build_consumer_check_state_damps_xau_second_support_under_choppy_state():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_reversal_guard",
            "action_none_reason": "observe_state_wait",
            "probe_scene_id": "xau_second_support_buy_probe",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "position_snapshot_v2": {
                "interpretation": {
                    "bias_label": "",
                    "primary_label": "MIXED_CONTEXT",
                    "secondary_context_label": "MIDDLE_CONTEXT",
                },
                "energy": {
                    "middle_neutrality": 0.62,
                    "position_conflict_score": 0.41,
                    "lower_position_force": 0.18,
                    "upper_position_force": 0.20,
                },
            },
            "state_vector_v2": {
                "fast_exit_risk_penalty": 0.34,
                "conflict_damp": 0.89,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == ""
    assert state["display_importance_adjustment_reason"] == "xau_state_chop_soft_cap"
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_soft_caps_xau_upper_reject_under_choppy_state():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "position_snapshot_v2": {
                "interpretation": {
                    "bias_label": "",
                    "primary_label": "MIXED_CONTEXT",
                    "secondary_context_label": "UPPER_CONTEXT",
                },
                "energy": {
                    "middle_neutrality": 0.56,
                    "position_conflict_score": 0.33,
                    "lower_position_force": 0.16,
                    "upper_position_force": 0.24,
                },
            },
            "state_vector_v2": {
                "fast_exit_risk_penalty": 0.31,
                "conflict_damp": 0.90,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert state["display_importance_adjustment_reason"] == "xau_state_chop_soft_cap"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_hides_xau_upper_reject_confirm_under_forecast_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is False
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] in {"OBSERVE", "PROBE"}
    assert state["blocked_display_reason"] == "xau_upper_reject_guard_wait_hidden"
    assert state["display_strength_level"] >= 0
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0


def test_build_consumer_check_state_hides_xau_upper_reject_mixed_confirm_under_forecast_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_mixed_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is False
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] in {"OBSERVE", "PROBE"}
    assert state["blocked_display_reason"] == "xau_upper_reject_guard_wait_hidden"
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0


def test_build_consumer_check_state_hides_xau_upper_reject_confirm_under_barrier_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "barrier_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is False
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["blocked_display_reason"] == "xau_upper_reject_guard_wait_hidden"
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0


def test_build_consumer_check_state_hides_xau_upper_reject_mixed_confirm_under_barrier_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_mixed_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "barrier_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] == "OBSERVE"
    assert state["blocked_display_reason"] in {"", "xau_upper_reject_development"}
    assert state["display_importance_tier"] in {"", "medium"}
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_upper_reject_mixed_guard_wait_as_wait_checks"


def test_build_consumer_check_state_downgrades_btc_lower_rebound_probe_to_observe():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "OBSERVE"
    assert state["display_strength_level"] == 5
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_keeps_btc_lower_probe_energy_soft_block_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "lower_rebound",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "BUY",
                "symbol_scene_relief": "btc_lower_buy_conservative_probe",
                "candidate_support": 0.86,
                "pair_gap": 0.22,
            },
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["blocked_display_reason"] == "energy_soft_block"
    assert state["display_importance_tier"] == "high"
    assert state["display_importance_source_reason"] == "btc_lower_recovery_start"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "btc_lower_rebound_probe_energy_soft_block_as_wait_checks"
    assert state["display_strength_level"] >= 6
    assert state["display_repeat_count"] >= 3


def test_build_consumer_check_state_keeps_btc_lower_probe_promotion_wait_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "probe_not_promoted"
    assert state["blocked_display_reason"] == "probe_promotion_gate"
    assert state["display_importance_tier"] == "high"
    assert state["display_importance_source_reason"] == "btc_lower_recovery_start"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "btc_lower_probe_promotion_wait_as_wait_checks"
    assert state["display_strength_level"] >= 6
    assert state["display_repeat_count"] >= 3


def test_build_consumer_check_state_keeps_nas_upper_reject_probe_forecast_wait_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "probe_not_promoted"
    assert state["blocked_display_reason"] == "forecast_guard"
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "nas_upper_reject_probe_forecast_wait_as_wait_checks"
    assert state["display_strength_level"] >= 6
    assert state["display_repeat_count"] >= 2


def test_build_consumer_check_state_keeps_nas_upper_reject_probe_promotion_wait_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "probe_not_promoted"
    assert state["blocked_display_reason"] == "probe_promotion_gate"
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "nas_upper_reject_probe_promotion_wait_as_wait_checks"
    assert state["display_strength_level"] >= 6
    assert state["display_repeat_count"] >= 2


def test_build_consumer_check_state_keeps_btc_structural_probe_energy_soft_block_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "BLOCKED"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["blocked_display_reason"] == "energy_soft_block"
    assert state["display_importance_tier"] == "medium"
    assert state["display_importance_source_reason"] == "btc_structural_rebound"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "btc_structural_probe_energy_soft_block_as_wait_checks"
    assert state["display_strength_level"] >= 5
    assert state["display_repeat_count"] >= 2


def test_build_consumer_check_state_marks_btc_lower_recovery_start_as_triple_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "high"
    assert state["display_score"] >= 0.90
    assert state["display_repeat_count"] == 3


def test_build_consumer_check_state_marks_btc_structural_rebound_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "probe_guard_wait_as_wait_checks"


def test_build_consumer_check_state_does_not_uplift_btc_upper_continuation_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "UPPER",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == ""
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_keeps_btc_structural_probe_wait_visible_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "btc_structural_rebound"
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "probe_guard_wait_as_wait_checks"


def test_build_consumer_check_state_keeps_nas_outer_band_probe_against_default_side_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "entry_probe_plan_v1": {
                "reason": "probe_against_default_side",
                "active": True,
                "ready_for_entry": False,
                "symbol_scene_relief": "nas_clean_confirm_probe",
                "intended_action": "SELL",
            },
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["display_importance_source_reason"] == "nas_upper_support_awareness"
    assert state["display_importance_tier"] == ""
    assert state["blocked_display_reason"] == "outer_band_guard"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "probe_guard_wait_as_wait_checks"
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_keeps_xau_middle_anchor_guard_wait_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert state["check_side"] == "SELL"
    assert state["blocked_display_reason"] == "middle_sr_anchor_guard"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_middle_anchor_guard_wait_as_wait_checks"
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_build_consumer_check_state_hides_btc_structural_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "structural_wait_hide_without_probe"
    assert "structural_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_sell_outer_band_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "UPPER",
            "bb_state": "UNKNOWN",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "sell_outer_band_wait_hide_without_probe"
    assert "sell_outer_band_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_nas_sell_middle_anchor_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "UPPER",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "nas_sell_middle_anchor_wait_hide_without_probe"
    assert "nas_sell_middle_anchor_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_nas_upper_reclaim_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reclaim_strength_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "UPPER",
            "bb_state": "UNKNOWN",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "nas_upper_reclaim_wait_hide_without_probe"
    assert "nas_upper_reclaim_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_nas_upper_reject_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "nas_upper_reject_wait_hide_without_probe"
    assert "nas_upper_reject_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_nas_upper_break_fail_wait_without_probe_scene():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_break_fail_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "ABOVE",
            "bb_state": "BREAKOUT",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == ""
    assert state["display_importance_tier"] == ""
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "nas_upper_break_fail_wait_hide_without_probe"
    assert "nas_upper_break_fail_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_hides_btc_lower_rebound_forecast_wait_without_probe():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "LOWER",
            "bb_state": "BREAKDOWN",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == "btc_lower_recovery_start"
    assert state["display_importance_tier"] == "high"
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "btc_lower_rebound_forecast_wait_hide_without_probe"
    assert "btc_lower_rebound_forecast_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_build_consumer_check_state_tags_hidden_btc_lower_rebound_breakdown_family_with_modifier_reason():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "BELOW",
            "bb_state": "BREAKDOWN",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_display_ready"] is False
    assert state["display_importance_source_reason"] == "btc_lower_recovery_start"
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "btc_lower_rebound_forecast_wait_hide_without_probe"
    assert "btc_lower_rebound_forecast_wait_hide_without_probe" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"


def test_build_consumer_check_state_marks_btc_breakout_reclaim_confirm_as_double_display():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_build_consumer_check_state_hides_btc_conflict_wait_signal_via_conflict_soft_cap():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "conflict_box_upper_bb20_lower_lower_support_confirm",
            "observe_side": "BUY",
            "blocked_by": "forecast_guard",
            "action_none_reason": "observe_state_wait",
            "box_state": "MIDDLE",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is False
    assert state["display_score"] == 0.0
    assert state["display_repeat_count"] == 0
    assert state["modifier_contract_version"] == "common_state_aware_display_modifier_v1"
    assert state["modifier_applied"] is True
    assert state["modifier_primary_reason"] == "conflict_wait_hide"
    assert "conflict_wait_hide" in state["modifier_reason_codes"]
    assert state["modifier_stage_adjustment"] == "visibility_suppressed"
    assert state["modifier_score_delta"] < 0.0


def test_resolve_effective_consumer_check_state_keeps_repeated_btc_structural_observe_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="outer_band_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "outer_band_reversal_support_required_observe"
    assert level == 5
    assert state["blocked_display_reason"] == "outer_band_guard"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "probe_guard_wait_as_wait_checks"
    assert state["display_repeat_count"] >= 1


def test_resolve_effective_consumer_check_state_suppresses_repeated_btc_lower_probe_observe():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="forecast_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 0
    assert state["blocked_display_reason"] == "btc_lower_probe_cadence_suppressed"


def test_resolve_effective_consumer_check_state_keeps_btc_lower_probe_visible_under_barrier_guard():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="barrier_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 5
    assert state["blocked_display_reason"] in {"", "probe_not_promoted", "barrier_guard"}


def test_resolve_effective_consumer_check_state_keeps_btc_lower_probe_energy_soft_block_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "lower_rebound",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "BUY",
                "symbol_scene_relief": "btc_lower_buy_conservative_probe",
                "candidate_support": 0.86,
                "pair_gap": 0.22,
            },
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="energy_soft_block",
        action_none_reason_value="execution_soft_blocked",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "PROBE"
    assert reason == "lower_rebound_probe_observe"
    assert level >= 6
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "btc_lower_rebound_probe_energy_soft_block_as_wait_checks"
    assert state["blocked_display_reason"] == "energy_soft_block"


def test_resolve_effective_consumer_check_state_keeps_btc_lower_probe_promotion_wait_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "box_state": "BELOW",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="BTCUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="probe_promotion_gate",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "PROBE"
    assert reason == "lower_rebound_probe_observe"
    assert level >= 6
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "btc_lower_probe_promotion_wait_as_wait_checks"
    assert state["blocked_display_reason"] == "probe_promotion_gate"


def test_resolve_effective_consumer_check_state_keeps_nas_upper_reject_probe_forecast_wait_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="forecast_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "upper_reject_probe_observe"
    assert level >= 6
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "nas_upper_reject_probe_forecast_wait_as_wait_checks"
    assert state["blocked_display_reason"] == "forecast_guard"


def test_resolve_effective_consumer_check_state_keeps_nas_upper_reject_probe_promotion_wait_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="probe_promotion_gate",
        action_none_reason_value="probe_not_promoted",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "probe_promotion_gate",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "upper_reject_probe_observe"
    assert level >= 6
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "nas_upper_reject_probe_promotion_wait_as_wait_checks"
    assert state["blocked_display_reason"] == "probe_promotion_gate"


def test_resolve_effective_consumer_check_state_late_downgrades_btc_lower_probe_to_observe():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_probe_observe",
            "semantic_origin_reason": "lower_rebound_probe_observe",
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "canonical_symbol": "BTCUSD",
            "display_strength_level": 7,
        },
        blocked_by_value="barrier_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 5


def test_resolve_effective_consumer_check_state_late_downgrades_nas_lower_probe_to_observe():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_probe_observe",
            "semantic_origin_reason": "lower_rebound_probe_observe",
            "probe_scene_id": "nas_clean_confirm_probe",
            "canonical_symbol": "NAS100",
            "display_importance_tier": "medium",
            "display_strength_level": 7,
        },
        blocked_by_value="barrier_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 5
    assert state["display_importance_tier"] == "medium"
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_resolve_effective_consumer_check_state_suppresses_repeated_nas_lower_probe_observe():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="barrier_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "lower_rebound_probe_observe",
            "blocked_by": "barrier_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 0
    assert state["blocked_display_reason"] == "nas_lower_probe_cadence_suppressed"


def test_resolve_effective_consumer_check_state_suppresses_repeated_nas_structural_observe():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="outer_band_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "outer_band_reversal_support_required_observe"
    assert level == 0
    assert state["blocked_display_reason"] == "nas_structural_cadence_suppressed"


def test_resolve_effective_consumer_check_state_soft_caps_nas_upper_continuation():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "OBSERVE",
            "check_reason": "lower_rebound_probe_observe",
            "semantic_origin_reason": "lower_rebound_probe_observe",
            "probe_scene_id": "nas_clean_confirm_probe",
            "canonical_symbol": "NAS100",
            "display_box_state": "UPPER",
            "display_bb_state": "MID",
            "display_importance_tier": "medium",
            "display_strength_level": 5,
        },
        blocked_by_value="forecast_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "lower_rebound_probe_observe"
    assert level == 4
    assert state["display_importance_tier"] == ""
    assert state["blocked_display_reason"] == "nas_upper_continuation_soft_cap"
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_resolve_effective_consumer_check_state_keeps_nas_upper_support_awareness_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "box_state": "UPPER",
            "bb_state": "MID",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="outer_band_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "outer_band_reversal_support_required_observe"
    assert level == 5
    assert state["display_importance_source_reason"] == "nas_upper_support_awareness"
    assert state["blocked_display_reason"] == "outer_band_guard"
    assert 0.70 <= state["display_score"] < 0.80
    assert state["display_repeat_count"] == 1


def test_resolve_effective_consumer_check_state_keeps_nas_outer_band_probe_against_default_side_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "entry_probe_plan_v1": {
                "reason": "probe_against_default_side",
                "active": True,
                "ready_for_entry": False,
                "symbol_scene_relief": "nas_clean_confirm_probe",
                "intended_action": "SELL",
            },
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="NAS100",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="outer_band_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "blocked_by": "outer_band_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "nas_clean_confirm_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "OBSERVE"
    assert reason == "outer_band_reversal_support_required_observe"
    assert level == 5
    assert state["display_importance_source_reason"] == "nas_upper_support_awareness"
    assert state["blocked_display_reason"] == "outer_band_guard"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "probe_guard_wait_as_wait_checks"


def test_resolve_effective_consumer_check_state_keeps_nas_breakout_reclaim_visible():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_confirm",
            "semantic_origin_reason": "lower_rebound_confirm",
            "probe_scene_id": "nas_clean_confirm_probe",
            "canonical_symbol": "NAS100",
            "display_box_state": "UPPER",
            "display_bb_state": "UPPER_EDGE",
            "display_importance_tier": "medium",
            "display_importance_source_reason": "nas_breakout_reclaim_confirm",
            "display_strength_level": 7,
        },
        blocked_by_value="probe_promotion_gate",
        action_none_reason_value="probe_not_promoted",
        action_value="BUY",
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "PROBE"
    assert reason == "lower_rebound_confirm"
    assert level == 7
    assert state["display_importance_tier"] == "medium"
    assert state["blocked_display_reason"] in {"", "probe_promotion_gate"}
    assert 0.80 <= state["display_score"] < 0.90
    assert state["display_repeat_count"] == 2


def test_resolve_effective_consumer_check_state_suppresses_repeated_xau_upper_reject_probe_family():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "xau_upper_sell_probe",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="forecast_guard",
        action_none_reason_value="probe_not_promoted",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "xau_upper_sell_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "upper_reject_probe_observe"
    assert level == 0
    assert state["blocked_display_reason"] == "xau_upper_reject_cadence_suppressed"


def test_resolve_effective_consumer_check_state_hides_xau_upper_reject_confirm_under_barrier_wait():
    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1={
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_confirm",
            "semantic_origin_reason": "upper_reject_confirm",
            "canonical_symbol": "XAUUSD",
            "display_strength_level": 7,
        },
        blocked_by_value="barrier_guard",
        action_none_reason_value="observe_state_wait",
        action_value="SELL",
    )

    assert candidate is True
    assert display_ready is False
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "upper_reject_confirm"
    assert level == 0
    assert state["blocked_display_reason"] == "xau_upper_reject_guard_wait_hidden"


def test_resolve_effective_consumer_check_state_keeps_xau_upper_reject_mixed_confirm_barrier_wait_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_mixed_confirm",
            "consumer_effective_action": "SELL",
            "blocked_by": "barrier_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="barrier_guard",
        action_none_reason_value="observe_state_wait",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "upper_reject_mixed_confirm",
            "blocked_by": "barrier_guard",
            "action_none_reason": "observe_state_wait",
            "probe_scene_id": "",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "PROBE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "OBSERVE"
    assert reason == "upper_reject_mixed_confirm"
    assert level >= 5
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_upper_reject_mixed_guard_wait_as_wait_checks"
    assert state["blocked_display_reason"] == "barrier_guard"


def test_build_consumer_check_state_keeps_xau_upper_reject_probe_energy_soft_block_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "MIDDLE",
            "bb_state": "UPPER_EDGE",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "upper_reject",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "SELL",
                "energy_relief_allowed": True,
                "symbol_scene_relief": "xau_upper_sell_probe",
                "candidate_support": 0.16,
                "pair_gap": 0.15,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["blocked_display_reason"] == "energy_soft_block"
    assert state["display_importance_tier"] == "medium"
    assert state["display_importance_source_reason"] == "xau_upper_reject_development"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_upper_reject_probe_energy_soft_block_as_wait_checks"
    assert state["display_strength_level"] >= 6
    assert state["display_repeat_count"] >= 2


def test_build_consumer_check_state_keeps_xau_middle_anchor_probe_energy_soft_block_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_second_support_buy_probe",
            "box_state": "MIDDLE",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "BUY"
    assert state["check_stage"] == "BLOCKED"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["blocked_display_reason"] == "energy_soft_block"
    assert state["display_importance_tier"] == "medium"
    assert state["display_importance_source_reason"] == "xau_second_support_reclaim"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_middle_anchor_probe_energy_soft_block_as_wait_checks"
    assert state["display_strength_level"] >= 5
    assert state["display_repeat_count"] >= 2


def test_build_consumer_check_state_keeps_xau_outer_band_probe_energy_soft_block_visible_as_wait():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "UPPER",
            "bb_state": "UNKNOWN",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "upper_reject",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "SELL",
                "energy_relief_allowed": True,
                "symbol_scene_relief": "xau_upper_sell_probe",
                "candidate_support": 0.19,
                "pair_gap": 0.11,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    assert state["check_candidate"] is True
    assert state["check_display_ready"] is True
    assert state["entry_ready"] is False
    assert state["check_side"] == "SELL"
    assert state["check_stage"] == "PROBE"
    assert state["entry_block_reason"] == "execution_soft_blocked"
    assert state["blocked_display_reason"] == "energy_soft_block"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_outer_band_probe_energy_soft_block_as_wait_checks"
    assert state["display_strength_level"] >= 5
    assert state["display_repeat_count"] >= 2


def test_resolve_effective_consumer_check_state_keeps_xau_upper_reject_probe_energy_soft_block_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "upper_reject_probe_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "MIDDLE",
            "bb_state": "UPPER_EDGE",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "upper_reject",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "SELL",
                "energy_relief_allowed": True,
                "symbol_scene_relief": "xau_upper_sell_probe",
                "candidate_support": 0.16,
                "pair_gap": 0.15,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="energy_soft_block",
        action_none_reason_value="execution_soft_blocked",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "BLOCKED",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "upper_reject_probe_observe"
    assert level >= 6
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_upper_reject_probe_energy_soft_block_as_wait_checks"
    assert state["blocked_display_reason"] == "energy_soft_block"


def test_resolve_effective_consumer_check_state_keeps_xau_middle_anchor_probe_energy_soft_block_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "BUY",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_second_support_buy_probe",
            "box_state": "MIDDLE",
            "bb_state": "LOWER_EDGE",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="energy_soft_block",
        action_none_reason_value="execution_soft_blocked",
        action_value="BUY",
        previous_runtime_row={
            "observe_reason": "middle_sr_anchor_required_observe",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_second_support_buy_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "BLOCKED",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "BUY"
    assert stage == "BLOCKED"
    assert reason == "middle_sr_anchor_required_observe"
    assert level >= 5
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_middle_anchor_probe_energy_soft_block_as_wait_checks"
    assert state["blocked_display_reason"] == "energy_soft_block"


def test_resolve_effective_consumer_check_state_keeps_xau_outer_band_probe_energy_soft_block_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "box_state": "UPPER",
            "bb_state": "UNKNOWN",
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "upper_reject",
                "probe_kind": "edge_probe",
                "candidate_side_hint": "SELL",
                "energy_relief_allowed": True,
                "symbol_scene_relief": "xau_upper_sell_probe",
                "candidate_support": 0.19,
                "pair_gap": 0.11,
            },
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="energy_soft_block",
        action_none_reason_value="execution_soft_blocked",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "probe_scene_id": "xau_upper_sell_probe",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "BLOCKED",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "PROBE"
    assert reason == "outer_band_reversal_support_required_observe"
    assert level >= 5
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_outer_band_probe_energy_soft_block_as_wait_checks"
    assert state["blocked_display_reason"] == "energy_soft_block"


def test_resolve_effective_consumer_check_state_keeps_repeated_xau_middle_anchor_observe_visible():
    initial_state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "middle_sr_anchor_required_observe",
            "consumer_effective_action": "SELL",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "observe_state_wait",
            "core_pass": 0,
        },
        canonical_symbol="XAUUSD",
    )

    (
        candidate,
        display_ready,
        entry_ready,
        side,
        stage,
        reason,
        level,
        state,
    ) = resolve_effective_consumer_check_state_v1(
        consumer_check_state_v1=initial_state,
        blocked_by_value="middle_sr_anchor_guard",
        action_none_reason_value="observe_state_wait",
        action_value="SELL",
        previous_runtime_row={
            "observe_reason": "middle_sr_anchor_required_observe",
            "blocked_by": "middle_sr_anchor_guard",
            "action_none_reason": "observe_state_wait",
            "consumer_check_display_ready": True,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "OBSERVE",
        },
    )

    assert candidate is True
    assert display_ready is True
    assert entry_ready is False
    assert side == "SELL"
    assert stage == "OBSERVE"
    assert reason == "middle_sr_anchor_required_observe"
    assert level >= 5
    assert state["blocked_display_reason"] == "middle_sr_anchor_guard"
    assert state["chart_event_kind_hint"] == "WAIT"
    assert state["chart_display_mode"] == "wait_check_repeat"
    assert state["chart_display_reason"] == "xau_middle_anchor_guard_wait_as_wait_checks"
