from backend.core.config import Config
from backend.services.entry_try_open_entry import (
    _build_active_action_conflict_guard_v1,
    _build_countertrend_continuation_signal_v1,
    _build_directional_continuation_promotion_v1,
    _build_execution_action_diff_v1,
    _build_flow_execution_selection_owner_v1,
    _build_flow_execution_veto_owner_v1,
    _refresh_directional_runtime_execution_surface_v1,
    _resolve_directional_continuation_state_v1,
    _build_probe_promotion_guard_v1,
    _build_trade_logger_micro_payload_from_decision_row,
    _build_teacher_label_exploration_entry_v1,
    _build_runtime_observe_confirm_dual_write,
    _build_semantic_shadow_prediction_cache_key,
    _normalize_order_lot,
    _resolve_entry_handoff_ids,
    _resolve_range_lower_buy_shadow_relief,
    _resolve_probe_execution_plan,
    _resolve_semantic_probe_bridge_action,
    _resolve_semantic_live_threshold_trace,
    _resolve_semantic_shadow_activation,
    _should_block_range_lower_buy_dual_bear_context,
)


class _DirectionalRuntimeSurfaceStub:
    def build_entry_runtime_signal_row(self, symbol: str, runtime_row: dict | None) -> dict:
        row = dict(runtime_row or {})
        row["symbol"] = str(symbol)
        row["consumer_check_side"] = "SELL"
        row["directional_continuation_overlay_v1"] = {
            "overlay_enabled": True,
            "overlay_direction": "UP",
            "overlay_selection_state": "UP_SELECTED",
            "overlay_event_kind_hint": "BUY_WATCH",
            "overlay_score": 0.6372,
        }
        row["directional_continuation_overlay_enabled"] = True
        row["directional_continuation_overlay_direction"] = "UP"
        row["directional_continuation_overlay_selection_state"] = "UP_SELECTED"
        row["directional_continuation_overlay_event_kind_hint"] = "BUY_WATCH"
        row["directional_continuation_overlay_score"] = 0.6372
        row["htf_alignment_state"] = "WITH_HTF"
        row["context_conflict_state"] = "AGAINST_PREV_BOX_AND_HTF"
        row["context_conflict_score"] = 0.95
        row["trend_15m_direction"] = "UPTREND"
        row["trend_1h_direction"] = "UPTREND"
        row["trend_4h_direction"] = "UPTREND"
        row["trend_1d_direction"] = "MIXED"
        row["breakout_candidate_action_target"] = "WATCH_BREAKOUT"
        row["breakout_direction"] = "UP"
        return row


def test_build_trade_logger_micro_payload_from_decision_row_preserves_numeric_and_text_micro_fields():
    payload = _build_trade_logger_micro_payload_from_decision_row(
        {
            "micro_breakout_readiness_state": "COILED_BREAKOUT",
            "micro_reversal_risk_state": "HIGH_RISK",
            "micro_participation_state": "ACTIVE_PARTICIPATION",
            "micro_gap_context_state": "GAP_PARTIAL_FILL",
            "micro_body_size_pct_20": "0.18",
            "micro_doji_ratio_20": 0.22,
            "micro_same_color_run_current": "3",
            "micro_same_color_run_max_20": 5,
            "micro_range_compression_ratio_20": "0.77",
            "micro_volume_burst_ratio_20": 2.4,
            "micro_volume_burst_decay_20": "0.31",
            "micro_gap_fill_progress": "0.48",
            "micro_upper_wick_ratio_20": "0.19",
            "micro_lower_wick_ratio_20": "0.11",
            "micro_swing_high_retest_count_20": "2",
            "micro_swing_low_retest_count_20": 1,
        }
    )

    assert payload["micro_breakout_readiness_state"] == "COILED_BREAKOUT"
    assert payload["micro_gap_context_state"] == "GAP_PARTIAL_FILL"
    assert payload["micro_body_size_pct_20"] == 0.18
    assert payload["micro_same_color_run_current"] == 3
    assert payload["micro_gap_fill_progress"] == 0.48
    assert payload["micro_swing_high_retest_count_20"] == 2


def test_build_trade_logger_micro_payload_from_decision_row_defaults_blank_row_safely():
    payload = _build_trade_logger_micro_payload_from_decision_row({})

    assert payload["micro_breakout_readiness_state"] == ""
    assert payload["micro_body_size_pct_20"] == 0.0
    assert payload["micro_same_color_run_current"] == 0
    assert payload["micro_gap_fill_progress"] == 0.0
    assert payload["micro_swing_low_retest_count_20"] == 0


def test_refresh_directional_runtime_execution_surface_recomputes_from_canonical_runtime_row():
    runtime_owner = _DirectionalRuntimeSurfaceStub()

    payload = _refresh_directional_runtime_execution_surface_v1(
        runtime_owner=runtime_owner,
        symbol="XAUUSD",
        runtime_row={
            "symbol": "XAUUSD",
            "consumer_check_side": "SELL",
        },
        baseline_action="SELL",
        current_action="",
        blocked_by="energy_soft_block",
        observe_reason="upper_reject_mixed_confirm",
        action_none_reason="execution_soft_blocked",
        setup_id="",
        setup_reason="upper_reject_mixed_confirm",
        forecast_state25_log_only_overlay_trace_v1={"reason_summary": "forecast_wait_bias"},
        belief_action_hint_v1={"reason_summary": "belief_fragile_thesis"},
    )

    guard = payload["active_action_conflict_guard_v1"]
    promotion = payload["directional_continuation_promotion_v1"]
    execution_diff = payload["execution_action_diff_v1"]
    runtime_row = payload["runtime_row"]

    assert guard["guard_applied"] is True
    assert guard["overlay_guard_eligible"] is True
    assert promotion["active"] is True
    assert promotion["promoted_action"] == "BUY"
    assert execution_diff["original_action_side"] == "SELL"
    assert execution_diff["guarded_action_side"] == "SKIP"
    assert execution_diff["promoted_action_side"] == "BUY"
    assert execution_diff["final_action_side"] == "SKIP"
    assert runtime_row["directional_continuation_overlay_direction"] == "UP"
    assert runtime_row["execution_diff_guard_applied"] is True
    assert runtime_row["directional_continuation_promotion_active"] == 1


def test_normalize_order_lot_respects_min_lot_floor():
    assert _normalize_order_lot(base_lot=0.01, size_multiplier=0.50, min_lot=0.01) == 0.01
    assert _normalize_order_lot(base_lot=0.10, size_multiplier=0.50, min_lot=0.01) == 0.05


def test_resolve_entry_handoff_ids_prefers_observe_confirm_and_falls_back_to_context_metadata():
    management_profile_id, invalidation_id = _resolve_entry_handoff_ids(
        shadow_observe_confirm={
            "management_profile_id": "Support_Hold_Profile",
            "invalidation_id": "",
        },
        shadow_entry_context_v1={
            "metadata": {
                "management_profile_id": "ignored_profile",
                "invalidation_id": "Second_Support_Break",
            }
        },
    )

    assert management_profile_id == "support_hold_profile"
    assert invalidation_id == "second_support_break"


def test_build_runtime_observe_confirm_dual_write_prefers_v2_canonical_and_keeps_v1_bridge():
    payload = _build_runtime_observe_confirm_dual_write(
        shadow_observe_confirm={
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.73,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
            "invalidation_id": "lower_support_fail",
            "management_profile_id": "support_hold_profile",
        }
    )

    assert payload["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert payload["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert payload["observe_confirm_v2"]["archetype_id"] == "lower_hold_buy"
    assert payload["observe_confirm_v1"]["archetype_id"] == "lower_hold_buy"
    assert payload["observe_confirm_output_contract_v2"]["canonical_output_field"] == "observe_confirm_v2"
    assert payload["consumer_input_contract_v1"]["canonical_observe_confirm_field"] == "observe_confirm_v2"


def test_build_semantic_shadow_prediction_cache_key_prefers_runtime_snapshot_anchor():
    key = _build_semantic_shadow_prediction_cache_key(
        symbol="xauusd",
        runtime_snapshot_row={
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=time|anchor_value=1|hint=BUY",
            "decision_row_key": "decision_row_v1|symbol=XAUUSD|anchor=ignored",
        },
        action_hint="buy",
        setup_id="range_upper_reversal_sell",
        setup_side="buy",
        entry_stage="probe_entry",
    )

    assert key == (
        "XAUUSD|BUY|range_upper_reversal_sell|BUY|probe_entry|"
        "runtime_signal_row_v1|symbol=XAUUSD|anchor_field=time|anchor_value=1|hint=BUY"
    )


def test_build_semantic_shadow_prediction_cache_key_returns_blank_without_anchor():
    assert (
        _build_semantic_shadow_prediction_cache_key(
            symbol="BTCUSD",
            runtime_snapshot_row={},
            action_hint="BUY",
            setup_id="breakout_prepare_buy",
            setup_side="BUY",
            entry_stage="probe_entry",
        )
        == ""
    )


def test_build_countertrend_continuation_signal_marks_xau_sell_bias() -> None:
    signal = _build_countertrend_continuation_signal_v1(
        symbol="XAUUSD",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": "wait_bias_hold|wait_reinforce",
        },
        belief_action_hint_v1={
            "reason_summary": "fragile_thesis|reduce_risk",
        },
        barrier_action_hint_v1={
            "reason_summary": "wait_block|unstable",
        },
    )

    assert signal["enabled"] is True
    assert signal["signal_action"] == "SELL"
    assert signal["signal_state"] == "down_continuation_bias"
    assert signal["warning_count"] == 3
    assert signal["anti_long_score"] > 0.0
    assert signal["anti_short_score"] == 0.0
    assert signal["pro_up_score"] == 0.0
    assert signal["pro_down_score"] > 0.0
    assert signal["directional_bias"] == "DOWN"
    assert signal["directional_action_state"] == "DOWN_PROBE"
    assert signal["directional_candidate_action"] == "SELL"
    assert signal["directional_execution_action"] == ""
    assert signal["directional_state_rank"] == 2
    assert signal["directional_state_reason"] == "down_probe::anti_long_strong_plus_pro_down_supportive"
    assert signal["directional_owner_family"] == "direction_agnostic_continuation"


def test_build_countertrend_continuation_signal_stays_blank_without_overlap() -> None:
    signal = _build_countertrend_continuation_signal_v1(
        symbol="XAUUSD",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": "neutral",
        },
        belief_action_hint_v1={
            "reason_summary": "neutral",
        },
        barrier_action_hint_v1={
            "reason_summary": "neutral",
        },
    )

    assert signal["enabled"] is False
    assert signal["signal_action"] == ""
    assert signal["warning_count"] == 0
    assert signal["directional_bias"] == "NONE"
    assert signal["directional_action_state"] == "DO_NOTHING"


def test_build_countertrend_continuation_signal_marks_watch_state_for_single_warning() -> None:
    signal = _build_countertrend_continuation_signal_v1(
        symbol="XAUUSD",
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": "wait_bias_hold",
        },
        belief_action_hint_v1={
            "reason_summary": "neutral",
        },
        barrier_action_hint_v1={
            "reason_summary": "neutral",
        },
    )

    assert signal["enabled"] is False
    assert signal["watch_only"] is True
    assert signal["signal_state"] == "down_continuation_watch"
    assert signal["directional_bias"] == "DOWN"
    assert signal["directional_action_state"] == "DOWN_WATCH"
    assert signal["directional_candidate_action"] == ""
    assert signal["directional_state_rank"] == 1
    assert signal["anti_long_score"] > signal["pro_down_score"]


def test_build_countertrend_continuation_signal_marks_xau_buy_bias_for_upper_sell_family() -> None:
    signal = _build_countertrend_continuation_signal_v1(
        symbol="XAUUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_reject_probe_observe",
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": "wait_bias_hold|wait_reinforce",
        },
        belief_action_hint_v1={
            "reason_summary": "fragile_thesis|reduce_risk",
        },
        barrier_action_hint_v1={
            "reason_summary": "relief_watch|balanced",
        },
    )

    assert signal["enabled"] is True
    assert signal["signal_action"] == "BUY"
    assert signal["signal_state"] == "up_continuation_bias"
    assert signal["anti_long_score"] == 0.0
    assert signal["anti_short_score"] > 0.0
    assert signal["pro_up_score"] > 0.0
    assert signal["pro_down_score"] == 0.0
    assert signal["directional_bias"] == "UP"
    assert signal["directional_action_state"] == "UP_PROBE"
    assert signal["directional_candidate_action"] == "BUY"
    assert signal["directional_execution_action"] == ""
    assert signal["directional_state_rank"] == 2
    assert signal["directional_state_reason"] == "up_probe::anti_short_strong_plus_pro_up_supportive"


def test_build_countertrend_continuation_signal_marks_up_watch_for_single_relief_signal() -> None:
    signal = _build_countertrend_continuation_signal_v1(
        symbol="XAUUSD",
        action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_reject_probe_observe",
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": "neutral",
        },
        belief_action_hint_v1={
            "reason_summary": "neutral",
        },
        barrier_action_hint_v1={
            "reason_summary": "relief_watch|balanced",
        },
    )

    assert signal["enabled"] is False
    assert signal["watch_only"] is True
    assert signal["signal_state"] == "up_continuation_watch"
    assert signal["directional_bias"] == "UP"
    assert signal["directional_action_state"] == "UP_WATCH"
    assert signal["directional_candidate_action"] == ""


def test_build_active_action_conflict_guard_downgrades_xau_upper_sell_conflict() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="XAUUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        runtime_signal_row={
            "forecast_state25_overlay_reason_summary": "wait_bias_hold|wait_reinforce",
            "belief_action_hint_reason_summary": "fragile_thesis|reduce_risk",
            "barrier_action_hint_reason_summary": "relief_watch|balanced",
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["guard_eligible"] is True
    assert guard["guard_applied"] is True
    assert guard["resolution_state"] == "WATCH"
    assert guard["conflict_kind"] == "baseline_sell_vs_up_directional"
    assert guard["failure_label"] == "wrong_side_sell_pressure"
    assert guard["failure_code"] == "active_action_conflict_guard"
    assert guard["directional_candidate_action"] == "BUY"
    assert guard["directional_action_state"] == "UP_PROBE"
    assert guard["up_bias_score"] >= 0.9


def test_build_active_action_conflict_guard_keeps_when_signal_is_weak() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="XAUUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        runtime_signal_row={
            "forecast_state25_overlay_reason_summary": "neutral",
            "belief_action_hint_reason_summary": "neutral",
            "barrier_action_hint_reason_summary": "neutral",
        },
    )

    assert guard["conflict_detected"] is False
    assert guard["guard_applied"] is False
    assert guard["resolution_state"] == "KEEP"
    assert guard["failure_code"] == ""


def test_build_active_action_conflict_guard_uses_precomputed_directional_signal() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="XAUUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        countertrend_continuation_signal_v1={
            "directional_candidate_action": "BUY",
            "directional_action_state": "UP_PROBE",
            "directional_bias": "UP",
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_up_bias_score": 0.624,
            "directional_down_bias_score": 0.0,
            "warning_count": 2,
            "reason_summary": "forecast_wait_bias|belief_fragile_thesis",
            "directional_state_reason": "up_probe::anti_short_strong_plus_pro_up_supportive",
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["guard_applied"] is True
    assert guard["directional_candidate_action"] == "BUY"
    assert guard["directional_action_state"] == "UP_PROBE"
    assert guard["resolution_state"] == "WATCH"


def test_build_active_action_conflict_guard_downgrades_sell_when_up_breakout_is_supportive() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_confidence": 0.38,
            "breakout_failure_risk": 0.18,
            "breakout_followthrough_score": 0.22,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "WATCH_BREAKOUT",
            "reason_summary": "watch_breakout_barrier_drag|watch_breakout",
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["guard_applied"] is True
    assert guard["resolution_state"] == "WATCH"
    assert guard["precedence_owner"] == "breakout"
    assert guard["breakout_conflict_detected"] is True
    assert guard["breakout_direction"] == "UP"
    assert guard["breakout_candidate_target"] == "WATCH_BREAKOUT"
    assert guard["failure_label"] == "wrong_side_sell_pressure"


def test_build_active_action_conflict_guard_marks_probe_when_breakout_probe_is_supportive() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="XAUUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_confidence": 0.44,
            "breakout_failure_risk": 0.21,
            "breakout_followthrough_score": 0.26,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "PROBE_BREAKOUT",
            "reason_summary": "supportive_breakout_probe|probe_breakout",
        },
    )

    assert guard["guard_applied"] is True
    assert guard["precedence_owner"] == "breakout"
    assert guard["resolution_state"] == "PROBE"
    assert guard["downgraded_observe_reason"] == "breakout_conflict_probe"


def test_build_active_action_conflict_guard_uses_breakout_target_fallback_when_runtime_scores_are_missing() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        runtime_signal_row={
            "breakout_candidate_action_target": "WATCH_BREAKOUT",
            "breakout_candidate_direction": "UP",
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["guard_applied"] is True
    assert guard["precedence_owner"] == "breakout"
    assert guard["breakout_conflict_detected"] is True
    assert guard["breakout_candidate_target"] == "WATCH_BREAKOUT"
    assert guard["resolution_state"] == "WATCH"


def test_build_active_action_conflict_guard_downgrades_nas_sell_against_strong_up_continuation_overlay() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_break_fail_confirm",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "context_conflict_score": 0.86,
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.79,
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["overlay_conflict_detected"] is True
    assert guard["overlay_guard_eligible"] is True
    assert guard["guard_applied"] is True
    assert guard["precedence_owner"] == "overlay"
    assert guard["resolution_state"] == "WATCH"
    assert guard["conflict_kind"] == "baseline_sell_vs_up_continuation_overlay"
    assert guard["failure_label"] == "wrong_side_sell_pressure"
    assert guard["overlay_direction"] == "UP"


def test_build_active_action_conflict_guard_downgrades_btc_sell_against_up_continuation_overlay() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="BTCUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_break_fail_confirm",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_HTF",
            "context_conflict_score": 0.80,
            "directional_continuation_overlay_v1": {
                "overlay_enabled": True,
                "overlay_direction": "UP",
                "overlay_selection_state": "UP_SELECTED",
                "overlay_event_kind_hint": "BUY_WATCH",
                "overlay_score": 0.77,
            },
        },
    )

    assert guard["guard_applied"] is True
    assert guard["overlay_guard_eligible"] is True
    assert guard["precedence_owner"] == "overlay"
    assert guard["conflict_kind"] == "baseline_sell_vs_up_continuation_overlay"
    assert "overlay::up::up_selected::0.77" in guard["reason_summary"]


def test_build_active_action_conflict_guard_uses_multitf_support_for_btc_overlay_conflict() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="BTCUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_reject_mixed_confirm",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_HTF",
            "context_conflict_score": 0.80,
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "MIXED",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.61,
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["overlay_conflict_detected"] is True
    assert guard["overlay_guard_eligible"] is True
    assert guard["guard_applied"] is True
    assert guard["precedence_owner"] == "overlay"
    assert guard["trend_alignment_count"] == 3


def test_build_active_action_conflict_guard_keeps_overlay_conflict_when_context_confirmation_is_missing() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="BTCUSD",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_break_fail_confirm",
        runtime_signal_row={
            "htf_alignment_state": "MIXED_HTF",
            "context_conflict_state": "CONTEXT_MIXED",
            "context_conflict_score": 0.40,
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.88,
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["overlay_conflict_detected"] is True
    assert guard["overlay_guard_eligible"] is False
    assert guard["guard_applied"] is False
    assert guard["resolution_state"] == "KEEP"


def test_build_active_action_conflict_guard_falls_back_to_runtime_consumer_side_when_baseline_is_blank() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_break_fail_confirm",
        runtime_signal_row={
            "consumer_check_side": "SELL",
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "context_conflict_score": 0.95,
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.76,
        },
    )

    assert guard["baseline_action"] == "SELL"
    assert guard["conflict_detected"] is True
    assert guard["overlay_conflict_detected"] is True


def test_build_directional_continuation_promotion_promotes_nas_sell_to_buy_when_overlay_is_strong() -> None:
    promotion = _build_directional_continuation_promotion_v1(
        symbol="NAS100",
        baseline_action="SELL",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "context_conflict_score": 0.86,
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.91,
            "breakout_direction": "UP",
            "breakout_candidate_action_target": "WATCH_BREAKOUT",
            "breakout_confidence": 0.34,
        },
        active_action_conflict_guard_v1={
            "guard_applied": True,
            "baseline_action": "SELL",
        },
    )

    assert promotion["active"] is True
    assert promotion["promoted_action"] == "BUY"
    assert promotion["recommended_entry_stage"] in {"balanced", "conservative"}
    assert promotion["promotion_reason"] == "directional_continuation_overlay_breakout_promotion"
    assert promotion["promotion_suppressed_reason"] == ""


def test_build_directional_continuation_promotion_can_activate_without_conflict_guard_when_structure_is_confirmed() -> None:
    promotion = _build_directional_continuation_promotion_v1(
        symbol="BTCUSD",
        baseline_action="SELL",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_HTF",
            "context_conflict_score": 0.80,
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "box_state": "ABOVE",
            "bb_state": "BREAKOUT",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.95,
        },
        active_action_conflict_guard_v1={
            "guard_applied": False,
            "baseline_action": "SELL",
        },
    )

    assert promotion["active"] is True
    assert promotion["promoted_action"] == "BUY"
    assert promotion["structural_continuation_confirmed"] is True
    assert promotion["promotion_suppressed_reason"] == ""


def test_build_directional_continuation_promotion_activates_on_breakout_pullback_resume_structure() -> None:
    promotion = _build_directional_continuation_promotion_v1(
        symbol="NAS100",
        baseline_action="SELL",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "NONE",
            "context_conflict_score": 0.0,
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "MIXED",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_low_retest_count": 2,
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.73,
            "breakout_candidate_direction": "UP",
            "breakout_candidate_action_target": "WATCH_BREAKOUT",
            "breakout_candidate_surface_state": "continuation_follow",
            "breakout_event_runtime_v1": {
                "breakout_direction": "UP",
                "breakout_state": "breakout_pullback",
                "breakout_retest_status": "passed",
                "breakout_reference_type": "squeeze",
                "breakout_confidence": 0.21,
                "breakout_followthrough_score": 0.27,
            },
            "breakout_event_overlay_candidates_v1": {
                "candidate_action_target": "WATCH_BREAKOUT",
            },
        },
        active_action_conflict_guard_v1={
            "guard_applied": False,
            "baseline_action": "SELL",
        },
    )

    assert promotion["active"] is True
    assert promotion["promoted_action"] == "BUY"
    assert promotion["structural_continuation_confirmed"] is True
    assert promotion["promotion_suppressed_reason"] == ""


def test_build_directional_continuation_promotion_promotes_btc_on_multitf_alignment_even_without_breakout() -> None:
    promotion = _build_directional_continuation_promotion_v1(
        symbol="BTCUSD",
        baseline_action="SELL",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "AGAINST_HTF",
            "context_conflict_score": 0.80,
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "MIXED",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.61,
            "breakout_candidate_action_target": "WAIT_MORE",
            "breakout_candidate_direction": "NONE",
            "breakout_candidate_confidence": 0.0,
        },
        active_action_conflict_guard_v1={
            "guard_applied": True,
            "baseline_action": "SELL",
        },
    )

    assert promotion["active"] is True
    assert promotion["promoted_action"] == "BUY"
    assert promotion["multi_tf_supportive"] is True
    assert promotion["aligned_overlay"] is True
    assert promotion["promotion_reason"] == "directional_continuation_overlay_multitf_promotion"
    assert promotion["promotion_suppressed_reason"] == ""


def test_build_directional_continuation_promotion_requires_confirmed_context() -> None:
    promotion = _build_directional_continuation_promotion_v1(
        symbol="XAUUSD",
        baseline_action="SELL",
        runtime_signal_row={
            "htf_alignment_state": "MIXED_HTF",
            "context_conflict_state": "CONTEXT_MIXED",
            "context_conflict_score": 0.42,
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.93,
            "breakout_direction": "UP",
            "breakout_candidate_action_target": "PROBE_BREAKOUT",
            "breakout_confidence": 0.42,
        },
        active_action_conflict_guard_v1={
            "guard_applied": True,
            "baseline_action": "SELL",
        },
    )

    assert promotion["active"] is False
    assert promotion["breakout_supportive"] is True
    assert promotion["strong_overlay"] is True
    assert promotion["promotion_suppressed_reason"] == "guard_or_structure_not_confirmed"


def test_build_active_action_conflict_guard_uses_structural_continuation_when_context_is_none() -> None:
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="upper_break_fail_confirm",
        runtime_signal_row={
            "htf_alignment_state": "WITH_HTF",
            "context_conflict_state": "NONE",
            "context_conflict_score": 0.0,
            "trend_15m_direction": "UPTREND",
            "trend_1h_direction": "UPTREND",
            "trend_4h_direction": "UPTREND",
            "trend_1d_direction": "MIXED",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "box_state": "ABOVE",
            "bb_state": "BREAKOUT",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_selection_state": "UP_SELECTED",
            "directional_continuation_overlay_event_kind_hint": "BUY_WATCH",
            "directional_continuation_overlay_score": 0.61,
            "consumer_check_reason": "upper_break_fail_confirm",
        },
    )

    assert guard["overlay_conflict_detected"] is True
    assert guard["structural_continuation_confirmed"] is True
    assert guard["overlay_guard_eligible"] is True
    assert guard["guard_applied"] is True


def test_build_execution_action_diff_tracks_guard_and_promotion_path() -> None:
    diff = _build_execution_action_diff_v1(
        original_action_side="SELL",
        current_action_side="BUY",
        blocked_by="",
        observe_reason="upper_break_fail_confirm",
        action_none_reason="",
        active_action_conflict_guard_v1={
            "guard_applied": True,
            "failure_code": "active_action_conflict_guard",
            "reason_summary": "wrong_side_conflict_pressure",
        },
        directional_continuation_promotion_v1={
            "active": True,
            "promoted_action": "BUY",
            "promotion_reason": "directional_continuation_overlay_multitf_promotion",
            "promotion_suppressed_reason": "",
        },
    )

    assert diff["original_action_side"] == "SELL"
    assert diff["guarded_action_side"] == "SKIP"
    assert diff["promoted_action_side"] == "BUY"
    assert diff["final_action_side"] == "BUY"
    assert diff["guard_applied"] is True
    assert diff["promotion_active"] is True
    assert diff["action_changed"] is True
    assert diff["action_change_reason_keys"] == [
        "active_action_conflict_guard",
        "directional_continuation_overlay_multitf_promotion",
    ]
    assert diff["guard_reason_summary"] == "wrong_side_conflict_pressure"
    assert diff["promotion_reason"] == "directional_continuation_overlay_multitf_promotion"
    assert diff["promotion_suppressed_reason"] == ""


def test_build_execution_action_diff_materializes_none_when_original_side_missing() -> None:
    diff = _build_execution_action_diff_v1(
        original_action_side="",
        current_action_side="SELL",
        blocked_by="",
        observe_reason="middle_sr_anchor_required_observe",
        action_none_reason="",
        active_action_conflict_guard_v1={},
        directional_continuation_promotion_v1={},
    )

    assert diff["original_action_side"] == "NONE"
    assert diff["guarded_action_side"] == "NONE"
    assert diff["promoted_action_side"] == "NONE"
    assert diff["final_action_side"] == "SELL"
    assert diff["promotion_suppressed_reason"] == ""


def test_resolve_directional_continuation_state_supports_up_watch_and_up_probe() -> None:
    up_watch = _resolve_directional_continuation_state_v1(
        anti_long_score=0.0,
        anti_short_score=0.36,
        pro_up_score=0.34,
        pro_down_score=0.0,
        owner_family="direction_agnostic_continuation",
        allow_enter=False,
    )
    up_probe = _resolve_directional_continuation_state_v1(
        anti_long_score=0.0,
        anti_short_score=0.72,
        pro_up_score=0.64,
        pro_down_score=0.0,
        owner_family="direction_agnostic_continuation",
        allow_enter=False,
    )

    assert up_watch["directional_bias"] == "UP"
    assert up_watch["directional_action_state"] == "UP_WATCH"
    assert up_watch["directional_candidate_action"] == ""
    assert up_probe["directional_bias"] == "UP"
    assert up_probe["directional_action_state"] == "UP_PROBE"
    assert up_probe["directional_candidate_action"] == "BUY"
    assert up_probe["directional_execution_action"] == ""


def test_resolve_directional_continuation_state_keeps_enter_reserved_without_flag() -> None:
    state = _resolve_directional_continuation_state_v1(
        anti_long_score=1.0,
        anti_short_score=0.0,
        pro_up_score=0.0,
        pro_down_score=1.0,
        owner_family="direction_agnostic_continuation",
        allow_enter=False,
    )

    assert state["directional_action_state"] == "DOWN_PROBE"
    assert state["directional_execution_action"] == ""


def test_resolve_probe_execution_plan_uses_smaller_probe_lot_and_conservative_stage():
    out = _resolve_probe_execution_plan(
        symbol="NAS100",
        action="BUY",
        entry_stage="balanced",
        base_lot=0.10,
        min_lot=0.01,
        same_dir_count=0,
        probe_plan_v1={
            "active": True,
            "ready_for_entry": True,
            "intended_action": "BUY",
            "recommended_size_multiplier": 0.50,
            "recommended_entry_stage": "conservative",
        },
    )

    assert out["contract_version"] == "entry_probe_execution_v1"
    assert out["probe_active"] is True
    assert out["confirm_add_active"] is False
    assert out["order_lot"] == 0.05
    assert out["size_multiplier"] == 0.50
    assert out["effective_entry_stage"] == "conservative"


def test_resolve_probe_execution_plan_keeps_normal_size_for_confirm_add():
    out = _resolve_probe_execution_plan(
        symbol="BTCUSD",
        action="BUY",
        entry_stage="balanced",
        base_lot=0.01,
        min_lot=0.01,
        same_dir_count=1,
        probe_plan_v1={},
    )

    assert out["probe_active"] is False
    assert out["confirm_add_active"] is True
    assert out["order_lot"] == 0.01


def test_build_probe_promotion_guard_allows_bounded_middle_anchor_probe_open():
    out = _build_probe_promotion_guard_v1(
        symbol="NAS100",
        action="BUY",
        observe_reason="middle_sr_anchor_required_observe",
        blocked_by="middle_sr_anchor_guard",
        action_none_reason="probe_not_promoted",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "default_side_aligned": True,
            "intended_action": "BUY",
            "near_confirm": True,
            "candidate_support": 0.12,
            "pair_gap": 0.18,
            "action_confirm_score": 0.09,
            "confirm_fake_gap": -0.24,
            "wait_confirm_gap": -0.20,
            "continue_fail_gap": -0.27,
            "same_side_barrier": 0.55,
        },
        consumer_check_state_v1={
            "check_stage": "PROBE",
            "entry_ready": False,
        },
        runtime_snapshot_row={
            "quick_trace_state": "PROBE",
            "quick_trace_reason": "probe_candidate_active",
        },
    )

    assert out["guard_active"] is True
    assert out["allows_open"] is True
    assert out["failure_code"] == ""
    assert out["bounded_probe_promotion_active"] is True
    assert out["bounded_probe_promotion_reason"] == "bounded_middle_sr_anchor_probe_promotion"
    assert out["bounded_probe_size_multiplier"] == 0.35
    assert out["bounded_probe_entry_stage"] == "conservative"


def test_build_probe_promotion_guard_allows_bounded_xau_outer_band_followthrough_probe():
    out = _build_probe_promotion_guard_v1(
        symbol="XAUUSD",
        action="BUY",
        observe_reason="outer_band_reversal_support_required_observe",
        blocked_by="outer_band_guard",
        action_none_reason="probe_not_promoted",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "default_side_aligned": True,
            "intended_action": "BUY",
            "near_confirm": False,
            "structural_relief_applied": True,
            "candidate_support": 0.18,
            "pair_gap": 0.20,
            "action_confirm_score": 0.12,
            "confirm_fake_gap": -0.10,
            "wait_confirm_gap": -0.04,
            "continue_fail_gap": -0.18,
            "same_side_barrier": 0.58,
        },
        consumer_check_state_v1={
            "check_stage": "PROBE",
            "entry_ready": False,
        },
        runtime_snapshot_row={
            "quick_trace_state": "PROBE",
            "quick_trace_reason": "probe_candidate_active",
        },
    )

    assert out["guard_active"] is True
    assert out["allows_open"] is True
    assert out["failure_code"] == ""
    assert out["bounded_probe_promotion_active"] is True
    assert out["bounded_probe_promotion_reason"] == "bounded_xau_outer_band_followthrough_probe"
    assert out["bounded_probe_size_multiplier"] == 0.45
    assert out["bounded_probe_entry_stage"] == "balanced"


def test_resolve_range_lower_buy_shadow_relief_allows_nas_lower_breakdown_probe():
    allow, reason = _resolve_range_lower_buy_shadow_relief(
        symbol="NAS100",
        core_reason="core_shadow_observe_wait",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="BELOW",
        bb_state="BREAKDOWN",
        wait_conflict=8.0,
        wait_noise=10.0,
        wait_score=32.0,
        preflight_allowed_action="BUY_ONLY",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1={},
    )

    assert allow is True
    assert reason == "nas_lower_breakdown_probe"


def test_resolve_range_lower_buy_shadow_relief_allows_bounded_probe_soft_edge_when_plan_is_supportive():
    allow, reason = _resolve_range_lower_buy_shadow_relief(
        symbol="XAUUSD",
        core_reason="core_shadow_observe_wait",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="LOWER",
        bb_state="MID",
        wait_conflict=12.0,
        wait_noise=14.0,
        wait_score=44.0,
        preflight_allowed_action="BUY_ONLY",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1={},
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "intended_action": "BUY",
            "default_side_aligned": True,
            "near_confirm": True,
            "candidate_support": 0.16,
            "pair_gap": 0.18,
            "action_confirm_score": 0.09,
            "confirm_fake_gap": -0.24,
            "wait_confirm_gap": -0.19,
            "continue_fail_gap": -0.28,
            "same_side_barrier": 0.57,
        },
    )

    assert allow is True
    assert reason == "bounded_probe_soft_edge"


def test_resolve_range_lower_buy_shadow_relief_allows_xau_outer_band_follow_through_when_plan_is_supportive():
    allow, reason = _resolve_range_lower_buy_shadow_relief(
        symbol="XAUUSD",
        core_reason="core_shadow_observe_wait",
        setup_reason="shadow_outer_band_reversal_support_required_observe",
        box_state="LOWER",
        bb_state="MID",
        wait_conflict=12.0,
        wait_noise=16.0,
        wait_score=44.0,
        preflight_allowed_action="BUY_ONLY",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1={},
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "intended_action": "BUY",
            "default_side_aligned": True,
            "near_confirm": False,
            "structural_relief_applied": True,
            "candidate_support": 0.16,
            "pair_gap": 0.20,
            "action_confirm_score": 0.11,
            "confirm_fake_gap": -0.11,
            "wait_confirm_gap": -0.03,
            "continue_fail_gap": -0.18,
            "same_side_barrier": 0.61,
        },
    )

    assert allow is True
    assert reason == "xau_outer_band_follow_through"


def test_resolve_range_lower_buy_shadow_relief_allows_xau_lower_rebound_follow_through_extension():
    allow, reason = _resolve_range_lower_buy_shadow_relief(
        symbol="XAUUSD",
        core_reason="energy_soft_block",
        setup_reason="shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
        box_state="LOWER",
        bb_state="MID",
        wait_conflict=14.0,
        wait_noise=16.0,
        wait_score=51.0,
        preflight_allowed_action="BUY_ONLY",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1={},
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": True,
            "intended_action": "BUY",
            "default_side_aligned": True,
            "near_confirm": True,
            "structural_relief_applied": True,
            "candidate_support": 0.62,
            "pair_gap": 0.28,
            "action_confirm_score": 0.33,
            "confirm_fake_gap": 0.08,
            "wait_confirm_gap": 0.18,
            "continue_fail_gap": 0.08,
            "same_side_barrier": 0.41,
        },
    )

    assert allow is True
    assert reason == "xau_lower_rebound_follow_through"


def test_resolve_range_lower_buy_shadow_relief_blocks_xau_countertrend_warning_veto():
    allow, reason = _resolve_range_lower_buy_shadow_relief(
        symbol="XAUUSD",
        core_reason="energy_soft_block",
        setup_reason="shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
        box_state="LOWER",
        bb_state="MID",
        wait_conflict=14.0,
        wait_noise=16.0,
        wait_score=51.0,
        preflight_allowed_action="BUY_ONLY",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1={},
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": True,
            "intended_action": "BUY",
            "default_side_aligned": True,
            "near_confirm": True,
            "candidate_support": 0.62,
            "pair_gap": 0.28,
            "action_confirm_score": 0.33,
            "confirm_fake_gap": 0.08,
            "wait_confirm_gap": 0.18,
            "continue_fail_gap": 0.08,
            "same_side_barrier": 0.41,
        },
        runtime_signal_row={
            "forecast_state25_overlay_reason_summary": "wait_bias_hold|wait_reinforce",
            "belief_action_hint_reason_summary": "fragile_thesis|reduce_risk",
            "barrier_action_hint_reason_summary": "wait_block|unstable",
        },
    )

    assert allow is False
    assert reason == "xau_countertrend_warning_veto"


def test_build_teacher_label_exploration_entry_allows_one_same_dir_position_for_outer_band_family(monkeypatch):
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED", True, raising=False)
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SYMBOLS",
        ("NAS100",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_OBSERVE_REASONS",
        ("outer_band_reversal_support_required_observe",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SOFT_BLOCKS",
        ("outer_band_guard", "observe_state_wait"),
        raising=False,
    )
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_REQUIRE_FLAT_POSITION", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_SAME_DIR_COUNT", 1, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MIN_SCORE_RATIO", 0.80, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_THRESHOLD_GAP", 12.0, raising=False)

    out = _build_teacher_label_exploration_entry_v1(
        symbol="NAS100",
        action="SELL",
        observe_reason="outer_band_reversal_support_required_observe",
        action_none_reason="observe_state_wait",
        blocked_by="outer_band_guard",
        probe_scene_id="",
        consumer_check_state_v1={
            "check_candidate": False,
            "check_display_ready": False,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "entry_block_reason": "observe_state_wait",
            "blocked_display_reason": "outer_band_guard",
        },
        guard_failure_code="outer_band_guard",
        score=6.025,
        effective_threshold=1.0,
        same_dir_count=1,
    )

    assert out["active"] is True
    assert out["family"] == "nas100_outer_band_reversal_observe_sell"
    assert out["same_dir_count"] == 1
    assert out["max_same_dir_count"] == 1


def test_build_teacher_label_exploration_entry_allows_probe_not_promoted_for_outer_band_family(monkeypatch):
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED", True, raising=False)
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SYMBOLS",
        ("BTCUSD",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_OBSERVE_REASONS",
        ("outer_band_reversal_support_required_observe",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SOFT_BLOCKS",
        ("outer_band_guard", "observe_state_wait", "probe_not_promoted"),
        raising=False,
    )
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_REQUIRE_FLAT_POSITION", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_SAME_DIR_COUNT", 1, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MIN_SCORE_RATIO", 0.80, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_THRESHOLD_GAP", 12.0, raising=False)

    out = _build_teacher_label_exploration_entry_v1(
        symbol="BTCUSD",
        action="SELL",
        observe_reason="outer_band_reversal_support_required_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="outer_band_guard",
        probe_scene_id="",
        consumer_check_state_v1={
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "OBSERVE",
            "entry_block_reason": "probe_not_promoted",
            "blocked_display_reason": "outer_band_guard",
        },
        guard_failure_code="outer_band_guard",
        score=5.2667,
        effective_threshold=1.0,
        same_dir_count=1,
    )

    assert out["active"] is True
    assert out["family"] == "btcusd_outer_band_reversal_observe_sell"
    assert out["soft_block_reason"] == "probe_not_promoted"


def test_build_teacher_label_exploration_entry_respects_explicit_consumer_wait_hint(monkeypatch):
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED", True, raising=False)
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SYMBOLS",
        ("BTCUSD",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_OBSERVE_REASONS",
        ("lower_rebound_probe_observe",),
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SOFT_BLOCKS",
        ("probe_not_promoted", "probe_promotion_gate"),
        raising=False,
    )
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_REQUIRE_FLAT_POSITION", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_SAME_DIR_COUNT", 1, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MIN_SCORE_RATIO", 0.80, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_THRESHOLD_GAP", 60.0, raising=False)

    out = _build_teacher_label_exploration_entry_v1(
        symbol="BTCUSD",
        action="BUY",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="probe_promotion_gate",
        probe_scene_id="btc_lower_buy_conservative_probe",
        consumer_check_state_v1={
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "entry_block_reason": "probe_not_promoted",
            "blocked_display_reason": "probe_promotion_gate",
            "chart_event_kind_hint": "WAIT",
            "chart_display_reason": "btc_lower_probe_promotion_wait_as_wait_checks",
        },
        guard_failure_code="consumer_entry_not_ready",
        score=240.0,
        effective_threshold=45.0,
        same_dir_count=0,
    )

    assert out["active"] is False
    assert out["family"] == "btcusd_lower_rebound_probe_buy"
    assert out["explicit_wait_guard"] is True

def test_resolve_semantic_shadow_activation_reports_runtime_unavailable_reason():
    state, reason = _resolve_semantic_shadow_activation(
        semantic_shadow_prediction_v1={"available": False, "reason": "semantic_runtime_unavailable"},
        semantic_live_guard_v1={"symbol_allowed": True, "entry_stage_allowed": True},
        runtime_diagnostics={"reason": "model_files_missing"},
    )

    assert state == "inactive"
    assert reason == "model_files_missing"


def test_resolve_semantic_shadow_activation_reports_symbol_block_when_prediction_active():
    state, reason = _resolve_semantic_shadow_activation(
        semantic_shadow_prediction_v1={"available": True},
        semantic_live_guard_v1={"symbol_allowed": False, "entry_stage_allowed": True},
        runtime_diagnostics={"reason": "loaded"},
    )

    assert state == "active_symbol_blocked"
    assert reason == "symbol_not_in_allowlist"


def test_resolve_semantic_live_threshold_trace_reports_mode_and_fallback():
    state, reason = _resolve_semantic_live_threshold_trace(
        {"mode": "log_only", "threshold_applied": False, "threshold_state": "mode_no_threshold"}
    )
    assert state == "mode_no_threshold"
    assert reason == "mode_no_threshold"

    state, reason = _resolve_semantic_live_threshold_trace(
        {
            "mode": "threshold_only",
            "threshold_applied": False,
            "threshold_state": "fallback_blocked",
            "threshold_inactive_reason": "symbol_not_in_allowlist",
        }
    )
    assert state == "fallback_blocked"
    assert reason == "symbol_not_in_allowlist"


def test_resolve_range_lower_buy_shadow_relief_allows_btc_probe_observe_breakdown_when_semantic_is_strong():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="BTCUSD",
        core_reason="core_shadow_probe_action",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="LOWER",
        bb_state="BREAKDOWN",
        wait_conflict=0.0,
        wait_noise=0.0,
        wait_score=70.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="observe_confirm_v1_fallback",
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9845},
            "entry_quality": {"probability": 0.9310},
        },
    )

    assert allowed is True
    assert tag == "semantic_probe"


def test_resolve_range_lower_buy_shadow_relief_rejects_probe_when_semantic_is_not_strong_enough():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="BTCUSD",
        core_reason="core_shadow_probe_action",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="LOWER",
        bb_state="BREAKDOWN",
        wait_conflict=0.0,
        wait_noise=0.0,
        wait_score=70.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="observe_confirm_v1_fallback",
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.70},
            "entry_quality": {"probability": 0.65},
        },
    )

    assert allowed is False
    assert tag == ""


def test_resolve_range_lower_buy_shadow_relief_allows_btc_native_probe_soft_edge_without_semantic_runtime():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        setup_reason="shadow_lower_rebound_probe_observe",
        box_state="MIDDLE",
        bb_state="MID",
        wait_conflict=20.0,
        wait_noise=14.0,
        wait_score=34.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1=None,
    )

    assert allowed is True
    assert tag == "native_probe"


def test_resolve_range_lower_buy_shadow_relief_allows_nas_native_probe_when_clean_confirm_is_ready():
    allowed, tag = _resolve_range_lower_buy_shadow_relief(
        symbol="NAS100",
        core_reason="core_shadow_probe_action",
        setup_reason="shadow_middle_sr_anchor_required_observe",
        box_state="LOWER",
        bb_state="MID",
        wait_conflict=18.0,
        wait_noise=14.0,
        wait_score=48.0,
        preflight_allowed_action="BOTH",
        compatibility_mode="native_v2",
        semantic_shadow_prediction_v1=None,
    )

    assert allowed is True
    assert tag == "nas_native_probe"


def test_should_block_range_lower_buy_dual_bear_context_for_btc_when_both_gates_fail():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is True
    )


def test_should_block_range_lower_buy_dual_bear_context_for_nas_when_both_gates_fail():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="NAS100",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is True
    )


def test_should_not_block_range_lower_buy_when_one_gate_still_passes():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=True,
            topdown_gate_pass=False,
        )
        is False
    )
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="NAS100",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=True,
        )
        is False
    )


def test_should_not_block_other_symbols_or_setups_for_dual_bear_context():
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="XAUUSD",
            action="BUY",
            setup_id="range_lower_reversal_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is False
    )
    assert (
        _should_block_range_lower_buy_dual_bear_context(
            symbol="BTCUSD",
            action="BUY",
            setup_id="trend_pullback_buy",
            h1_gate_pass=False,
            topdown_gate_pass=False,
        )
        is False
    )


def test_build_flow_execution_veto_owner_applies_for_btc_lower_buy_in_bear_continuation():
    veto = _build_flow_execution_veto_owner_v1(
        symbol="BTCUSD",
        baseline_action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_confirm",
        runtime_signal_row={
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "directional_continuation_overlay_direction": "DOWN",
            "flow_shadow_direction_v1": "SELL",
            "flow_structure_gate_v1": "INELIGIBLE",
            "flow_support_state_v1": "FLOW_UNCONFIRMED",
            "chart_event_kind_hint": "SELL_WAIT",
            "consumer_check_side": "BUY",
            "consumer_check_stage": "BLOCKED",
            "consumer_check_reason": "lower_rebound_confirm",
            "consumer_check_entry_ready": False,
            "core_allowed_action": "BUY_ONLY",
        },
    )

    assert veto["veto_detected"] is True
    assert veto["veto_applied"] is True
    assert veto["resolution_state"] == "WAIT"
    assert veto["failure_code"] == "flow_execution_veto_owner"
    assert veto["bearish_evidence_count"] >= 3


def test_build_flow_execution_veto_owner_keeps_when_rebound_context_is_not_present():
    veto = _build_flow_execution_veto_owner_v1(
        symbol="BTCUSD",
        baseline_action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason="shadow_lower_rebound_confirm",
        runtime_signal_row={
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "directional_continuation_overlay_direction": "DOWN",
            "flow_shadow_direction_v1": "SELL",
            "chart_event_kind_hint": "SELL_WAIT",
            "consumer_check_side": "SELL",
            "consumer_check_stage": "WAIT",
            "consumer_check_reason": "upper_reject_probe_observe",
            "consumer_check_entry_ready": True,
        },
    )

    assert veto["veto_detected"] is True
    assert veto["veto_applied"] is False
    assert veto["resolution_state"] == "KEEP"


def test_build_flow_execution_selection_owner_chooses_wait_for_bearish_sell_wait_context():
    owner = _build_flow_execution_selection_owner_v1(
        symbol="BTCUSD",
        legacy_action="BUY",
        runtime_signal_row={
            "flow_shadow_direction_v1": "SELL",
            "chart_event_kind_hint": "SELL_WAIT",
            "flow_structure_gate_v1": "INELIGIBLE",
            "flow_support_state_v1": "FLOW_UNCONFIRMED",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "directional_continuation_overlay_direction": "DOWN",
            "flow_shadow_entry_quality_prob_v1": 0.18,
            "flow_shadow_continuation_persistence_prob_v1": 0.76,
            "flow_shadow_reversal_risk_prob_v1": 0.29,
        },
    )

    assert owner["selection_detected"] is True
    assert owner["selection_active"] is True
    assert owner["selected_action"] == "WAIT"
    assert owner["resolution_state"] == "WAIT"


def test_build_flow_execution_selection_owner_can_select_sell_when_legacy_matches():
    owner = _build_flow_execution_selection_owner_v1(
        symbol="BTCUSD",
        legacy_action="SELL",
        runtime_signal_row={
            "flow_shadow_direction_v1": "SELL",
            "chart_event_kind_hint": "SELL_PROBE",
            "flow_structure_gate_v1": "ELIGIBLE",
            "flow_support_state_v1": "FLOW_BUILDING",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "directional_continuation_overlay_direction": "DOWN",
            "flow_shadow_entry_quality_prob_v1": 0.58,
            "flow_shadow_continuation_persistence_prob_v1": 0.72,
            "flow_shadow_reversal_risk_prob_v1": 0.22,
        },
    )

    assert owner["selection_detected"] is True
    assert owner["selection_active"] is True
    assert owner["execution_apply_allowed"] is True
    assert owner["selected_action"] == "SELL"
    assert owner["resolution_state"] == "SELECT"


def test_build_flow_execution_selection_owner_hands_off_to_sell_when_legacy_is_opposite():
    owner = _build_flow_execution_selection_owner_v1(
        symbol="BTCUSD",
        legacy_action="BUY",
        runtime_signal_row={
            "flow_shadow_direction_v1": "SELL",
            "chart_event_kind_hint": "SELL_PROBE",
            "flow_structure_gate_v1": "ELIGIBLE",
            "flow_support_state_v1": "FLOW_BUILDING",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "directional_continuation_overlay_direction": "DOWN",
            "flow_shadow_entry_quality_prob_v1": 0.58,
            "flow_shadow_continuation_persistence_prob_v1": 0.72,
            "flow_shadow_reversal_risk_prob_v1": 0.22,
        },
    )

    assert owner["selection_detected"] is True
    assert owner["selection_active"] is True
    assert owner["execution_apply_allowed"] is True
    assert owner["selected_action"] == "SELL"
    assert owner["resolution_state"] == "SELECT"


def test_build_flow_execution_selection_owner_hands_off_to_buy_when_legacy_is_opposite():
    owner = _build_flow_execution_selection_owner_v1(
        symbol="BTCUSD",
        legacy_action="SELL",
        runtime_signal_row={
            "flow_shadow_direction_v1": "BUY",
            "chart_event_kind_hint": "BUY_PROBE",
            "flow_structure_gate_v1": "ELIGIBLE",
            "flow_support_state_v1": "FLOW_BUILDING",
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "dominance_shadow_dominant_side_v1": "BULL",
            "directional_continuation_overlay_direction": "UP",
            "flow_shadow_entry_quality_prob_v1": 0.57,
            "flow_shadow_continuation_persistence_prob_v1": 0.69,
            "flow_shadow_reversal_risk_prob_v1": 0.24,
        },
    )

    assert owner["selection_detected"] is True
    assert owner["selection_active"] is True
    assert owner["execution_apply_allowed"] is True
    assert owner["selected_action"] == "BUY"
    assert owner["resolution_state"] == "SELECT"


def test_resolve_semantic_probe_bridge_action_allows_btc_lower_rebound_when_semantic_is_strong():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="forecast_guard",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_pair_gap_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.26,
            "action_confirm_score": 0.13,
            "confirm_fake_gap": -0.20,
            "wait_confirm_gap": -0.15,
            "continue_fail_gap": -0.28,
            "same_side_barrier": 0.50,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.98},
            "entry_quality": {"probability": 0.94},
        },
    )

    assert action == "BUY"
    assert reason == "btc_lower_rebound_semantic_probe_bridge"


def test_resolve_semantic_probe_bridge_action_rejects_when_semantic_is_not_strong_enough():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="forecast_guard",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_pair_gap_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.26,
            "action_confirm_score": 0.13,
            "confirm_fake_gap": -0.20,
            "wait_confirm_gap": -0.15,
            "continue_fail_gap": -0.28,
            "same_side_barrier": 0.50,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.80},
            "entry_quality": {"probability": 0.70},
        },
    )

    assert action == ""
    assert reason == ""


def test_resolve_semantic_probe_bridge_action_allows_btc_lower_rebound_when_native_probe_is_near_confirm():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="forecast_guard",
        compatibility_mode="native_v2",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_forecast_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.15,
            "pair_gap": 0.22,
            "action_confirm_score": 0.09,
            "confirm_fake_gap": -0.24,
            "wait_confirm_gap": -0.20,
            "continue_fail_gap": -0.27,
            "same_side_barrier": 0.58,
            "near_confirm": True,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1=None,
    )

    assert action == "BUY"
    assert reason == "btc_lower_rebound_native_probe_bridge"


def test_resolve_semantic_probe_bridge_action_allows_nas_clean_confirm_when_near_confirm_native_relief_is_ready():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="NAS100",
        core_reason="core_shadow_observe_wait",
        observe_reason="middle_sr_anchor_required_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="middle_sr_anchor_guard",
        compatibility_mode="native_v2",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_forecast_not_ready",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.12,
            "pair_gap": 0.19,
            "action_confirm_score": 0.09,
            "confirm_fake_gap": -0.25,
            "wait_confirm_gap": -0.20,
            "continue_fail_gap": -0.27,
            "same_side_barrier": 0.55,
            "near_confirm": True,
            "symbol_scene_relief": "nas_clean_confirm_probe",
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1=None,
    )

    assert action == "BUY"
    assert reason == "nas_clean_confirm_native_probe_bridge"


def test_resolve_semantic_probe_bridge_action_allows_nas_clean_confirm_lower_rebound_ready_bridge():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="NAS100",
        core_reason="energy_soft_block",
        observe_reason="lower_rebound_probe_observe",
        action_none_reason="execution_soft_blocked",
        blocked_by="energy_soft_block",
        compatibility_mode="native_v2",
        entry_probe_plan_v1={
            "active": True,
            "ready_for_entry": True,
            "reason": "",
            "intended_action": "BUY",
            "default_side_aligned": True,
            "candidate_support": 0.6523,
            "pair_gap": 0.1530,
            "action_confirm_score": 0.13739,
            "confirm_fake_gap": -0.1667,
            "wait_confirm_gap": -0.1156,
            "continue_fail_gap": -0.2568,
            "same_side_barrier": 0.5877,
            "symbol_scene_relief": "nas_clean_confirm_probe",
            "near_confirm": True,
        },
        default_side_gate_v1={},
        probe_candidate_v1={},
        semantic_shadow_prediction_v1=None,
    )

    assert action == "BUY"
    assert reason == "nas_clean_confirm_lower_rebound_ready_bridge"


def test_resolve_semantic_probe_bridge_action_allows_btc_upper_reject_when_semantic_is_strong():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="upper_reject_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": False,
            "ready_for_entry": False,
            "reason": "probe_not_observe_stage",
            "intended_action": "SELL",
            "candidate_support": 0.51,
        },
        default_side_gate_v1={
            "reason": "lower_edge_sell_requires_break_override",
            "winner_side": "SELL",
            "winner_clear": True,
            "pair_gap": 0.32,
        },
        probe_candidate_v1={
            "candidate_support": 0.51,
            "near_confirm": True,
        },
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9793},
            "entry_quality": {"probability": 0.9482},
        },
    )

    assert action == "SELL"
    assert reason == "btc_upper_reject_semantic_probe_bridge"


def test_resolve_semantic_probe_bridge_action_rejects_btc_upper_reject_when_gate_is_weak():
    action, reason = _resolve_semantic_probe_bridge_action(
        symbol="BTCUSD",
        core_reason="core_shadow_observe_wait",
        observe_reason="upper_reject_probe_observe",
        action_none_reason="probe_not_promoted",
        blocked_by="",
        compatibility_mode="observe_confirm_v1_fallback",
        entry_probe_plan_v1={
            "active": False,
            "ready_for_entry": False,
            "reason": "probe_not_observe_stage",
            "intended_action": "SELL",
            "candidate_support": 0.44,
        },
        default_side_gate_v1={
            "reason": "lower_edge_sell_requires_break_override",
            "winner_side": "SELL",
            "winner_clear": True,
            "pair_gap": 0.28,
        },
        probe_candidate_v1={
            "candidate_support": 0.44,
            "near_confirm": False,
        },
        semantic_shadow_prediction_v1={
            "timing": {"probability": 0.9793},
            "entry_quality": {"probability": 0.9482},
        },
    )

    assert action == ""
    assert reason == ""


def test_active_action_conflict_guard_downgrades_breakout_watch_conflict_with_missing_breakout_metrics():
    guard = _build_active_action_conflict_guard_v1(
        symbol="NAS100",
        baseline_action="SELL",
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_reject_probe_observe",
        runtime_signal_row={
            "breakout_candidate_direction": "UP",
            "breakout_candidate_action_target": "WATCH_BREAKOUT",
            "breakout_candidate_confidence": "",
            "breakout_failure_risk": "",
            "breakout_followthrough_score": "",
        },
    )

    assert guard["conflict_detected"] is True
    assert guard["guard_eligible"] is True
    assert guard["guard_applied"] is True
    assert guard["resolution_state"] == "WATCH"
    assert guard["precedence_owner"] == "breakout"
    assert guard["breakout_confidence"] >= 0.30
    assert guard["breakout_failure_risk"] <= 0.40
