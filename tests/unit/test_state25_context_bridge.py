from backend.services.state25_context_bridge import (
    STATE25_CONTEXT_BRIDGE_CONTRACT_VERSION,
    STATE25_CONTEXT_BRIDGE_FAILURE_LOW_CONFIDENCE_CONTEXT,
    STATE25_CONTEXT_BRIDGE_FAILURE_SIGNED_THRESHOLD_UNAVAILABLE,
    STATE25_CONTEXT_BRIDGE_FAILURE_STALE_CONTEXT_SUPPRESSED,
    STATE25_CONTEXT_BRIDGE_GUARD_DOUBLE_COUNTING_SUPPRESSED,
    build_state25_candidate_context_bridge_v1,
)


def test_bridge_returns_stable_default_contract_for_empty_row():
    payload = build_state25_candidate_context_bridge_v1({})

    assert payload["contract_version"] == STATE25_CONTEXT_BRIDGE_CONTRACT_VERSION
    assert payload["bridge_stage"] == "BC6_THRESHOLD_LOG_ONLY"
    assert payload["translator_state"] == "WEIGHT_THRESHOLD_LOG_ONLY_ACTIVE"
    assert payload["weight_adjustments_requested"] == {}
    assert payload["threshold_adjustment_effective"]["threshold_delta_points"] == 0.0
    assert payload["size_adjustment_state"] == "UNCHANGED"
    assert payload["decision_counterfactual"]["bridge_changed_decision"] is False
    assert payload["bridge_decision_id"].startswith("state25-ctx-")


def test_bridge_computes_activation_and_failure_reasons():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "NAS100",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "signal_timeframe": "15M",
            "htf_alignment_state": "AGAINST_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_confidence": "LOW",
            "previous_box_is_consolidation": False,
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "late_chase_risk_state": "HIGH",
            "cluster_share_symbol_band": "DOMINANT",
            "trend_1h_age_seconds": 1900,
            "trend_4h_age_seconds": 1200,
            "trend_1d_age_seconds": 100,
            "previous_box_age_seconds": 480,
        }
    )

    assert payload["component_activation"]["htf"] == 0.0
    assert payload["component_activation"]["previous_box"] == 0.0
    assert payload["component_activation"]["late_chase"] == 1.0
    assert payload["component_activation"]["share"] == 0.2
    assert "STALE" in payload["component_activation_reasons"]["htf"]
    assert "LOW_CONFIDENCE" in payload["component_activation_reasons"]["previous_box"]
    assert "NON_CONSOLIDATION" in payload["component_activation_reasons"]["previous_box"]
    assert "BOOSTER_ONLY" in payload["component_activation_reasons"]["share"]
    assert STATE25_CONTEXT_BRIDGE_FAILURE_STALE_CONTEXT_SUPPRESSED in payload["failure_modes"]
    assert STATE25_CONTEXT_BRIDGE_FAILURE_LOW_CONFIDENCE_CONTEXT in payload["failure_modes"]
    assert STATE25_CONTEXT_BRIDGE_FAILURE_SIGNED_THRESHOLD_UNAVAILABLE in payload["failure_modes"]


def test_bridge_marks_overlap_guard_modes_when_existing_bridges_exist():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "BTCUSD",
            "consumer_check_side": "BUY",
            "forecast_state25_runtime_bridge_v1": {"enabled": True},
            "belief_state25_runtime_bridge_v1": {"enabled": True},
        }
    )

    assert payload["double_counting_guard_active"] is True
    assert payload["overlap_class"] == "RISK_DUPLICATE"
    assert "forecast_state25_runtime_bridge_v1" in payload["overlap_sources"]
    assert STATE25_CONTEXT_BRIDGE_GUARD_DOUBLE_COUNTING_SUPPRESSED in payload["guard_modes"]
    assert "DOUBLE_COUNTING_GUARD_READY" in payload["trace_reason_codes"]


def test_bridge_translates_against_htf_to_weight_pair_and_bias():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "NAS100",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "AGAINST_HTF",
            "htf_against_severity": "HIGH",
            "trend_1h_age_seconds": 120,
            "trend_4h_age_seconds": 100,
            "trend_1d_age_seconds": 90,
        }
    )

    assert "reversal_risk_weight" in payload["weight_adjustments_requested"]
    assert "directional_bias_weight" in payload["weight_adjustments_requested"]
    assert payload["weight_adjustments_effective"]["reversal_risk_weight"]["delta"] < 0
    assert payload["weight_adjustments_effective"]["directional_bias_weight"]["delta"] > 0
    assert payload["context_bias_side"] == "BUY"
    assert "AGAINST_HTF" in payload["context_bias_side_source_keys"]
    assert "WEIGHT_PAIR_AGAINST_HTF" in payload["trace_reason_codes"]


def test_bridge_suppresses_weight_effective_when_overlap_guard_is_active():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "BTCUSD",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "AGAINST_HTF",
            "htf_against_severity": "MEDIUM",
            "trend_1h_age_seconds": 60,
            "trend_4h_age_seconds": 60,
            "trend_1d_age_seconds": 60,
            "forecast_state25_runtime_bridge_v1": {"enabled": True},
        }
    )

    assert payload["weight_adjustments_requested"] != {}
    assert payload["weight_adjustments_effective"] == {}
    assert "reversal_risk_weight" not in payload["weight_adjustments_effective"]
    assert payload["weight_adjustments_suppressed"]["reversal_risk_weight"]["reason"] == "DOUBLE_COUNTING_GUARD"


def test_bridge_keeps_late_chase_out_of_weight_translation_in_v1():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "NAS100",
            "consumer_check_side": "BUY",
            "late_chase_risk_state": "HIGH",
        }
    )

    assert payload["weight_adjustments_requested"] == {}
    assert payload["weight_adjustments_suppressed"]["LATE_CHASE_RISK"]["reason"] == "DEFER_TO_THRESHOLD_SIZE_V1"
    assert "LATE_CHASE_WEIGHT_SKIPPED_V1" in payload["trace_reason_codes"]


def test_bridge_enables_review_only_relief_for_low_confidence_breakout_held_conflict():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "BTCUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_confidence": "LOW",
            "previous_box_is_consolidation": False,
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "context_conflict_flags": ["AGAINST_HTF", "AGAINST_PREV_BOX"],
            "context_conflict_intensity": "MEDIUM",
            "trend_1h_age_seconds": 120,
            "trend_4h_age_seconds": 120,
            "trend_1d_age_seconds": 120,
            "previous_box_age_seconds": 60,
            "forecast_state25_runtime_bridge_v1": {"enabled": True},
        }
    )

    assert payload["component_activation"]["previous_box"] == 0.35
    assert "LOW_CONFIDENCE_REVIEW_RELIEF" in payload["component_activation_reasons"]["previous_box"]
    assert "range_reversal_weight" in payload["weight_adjustments_requested"]
    assert "directional_bias_weight" in payload["weight_adjustments_requested"]
    assert payload["weight_adjustments_effective"] == {}
    assert payload["weight_adjustments_suppressed"]["range_reversal_weight"]["reason"] == "DOUBLE_COUNTING_GUARD"
    assert "LOW_CONFIDENCE_PREVIOUS_BOX_REVIEW_RELIEF" in payload["trace_reason_codes"]


def test_bridge_keeps_low_confidence_previous_box_inactive_without_conflict_relief():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "BTCUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_confidence": "LOW",
            "previous_box_is_consolidation": False,
            "context_conflict_state": "NONE",
            "context_conflict_flags": [],
            "context_conflict_intensity": "LOW",
            "trend_1h_age_seconds": 120,
            "trend_4h_age_seconds": 120,
            "trend_1d_age_seconds": 120,
            "previous_box_age_seconds": 60,
        }
    )

    assert payload["component_activation"]["previous_box"] == 0.0
    assert "LOW_CONFIDENCE_REVIEW_RELIEF" not in payload["component_activation_reasons"]["previous_box"]
    assert payload["weight_adjustments_requested"] == {}


def test_bridge_relaxes_overlap_guard_for_same_runtime_hint_duplicate_in_bc5():
    shared_hint = {
        "scene_pattern_id": 21,
        "entry_bias_hint": "confirm",
        "wait_bias_hint": "short_wait",
        "exit_bias_hint": "range_take",
        "transition_risk_hint": "mid",
        "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
    }
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "XAUUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_confidence": "HIGH",
            "previous_box_is_consolidation": True,
            "trend_1h_age_seconds": 120,
            "trend_4h_age_seconds": 120,
            "trend_1d_age_seconds": 120,
            "previous_box_age_seconds": 60,
            "forecast_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
            "belief_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
            "barrier_state25_runtime_bridge_v1": {"state25_runtime_hint_v1": shared_hint},
        }
    )

    assert payload["overlap_same_runtime_hint_duplicate"] is True
    assert payload["overlap_guard_decision"] == "RELAXED_SAME_RUNTIME_HINT_DUPLICATE"
    assert payload["double_counting_guard_active"] is False
    assert payload["weight_adjustments_requested"] != {}
    assert payload["weight_adjustments_effective"] != {}
    assert "OVERLAP_GUARD_RELAXED_SAME_RUNTIME_HINT" in payload["trace_reason_codes"]


def test_bridge_keeps_overlap_guard_when_runtime_hint_signatures_differ():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "XAUUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_confidence": "HIGH",
            "previous_box_is_consolidation": True,
            "trend_1h_age_seconds": 120,
            "trend_4h_age_seconds": 120,
            "trend_1d_age_seconds": 120,
            "previous_box_age_seconds": 60,
            "forecast_state25_runtime_bridge_v1": {
                "state25_runtime_hint_v1": {
                    "scene_pattern_id": 21,
                    "entry_bias_hint": "confirm",
                    "wait_bias_hint": "short_wait",
                    "exit_bias_hint": "range_take",
                    "transition_risk_hint": "mid",
                    "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                }
            },
            "belief_state25_runtime_bridge_v1": {
                "state25_runtime_hint_v1": {
                    "scene_pattern_id": 22,
                    "entry_bias_hint": "wait",
                    "wait_bias_hint": "long_wait",
                    "exit_bias_hint": "hold",
                    "transition_risk_hint": "high",
                    "reason_summary": "다른 장면",
                }
            },
            "barrier_state25_runtime_bridge_v1": {
                "state25_runtime_hint_v1": {
                    "scene_pattern_id": 21,
                    "entry_bias_hint": "confirm",
                    "wait_bias_hint": "short_wait",
                    "exit_bias_hint": "range_take",
                    "transition_risk_hint": "mid",
                    "reason_summary": "갭필링 진행장|D|confirm|short_wait|mid",
                }
            },
        }
    )

    assert payload["overlap_same_runtime_hint_duplicate"] is False
    assert payload["overlap_guard_decision"] == "BLOCKED_OVERLAP_DUPLICATE"
    assert payload["double_counting_guard_active"] is True
    assert payload["weight_adjustments_requested"] != {}
    assert payload["weight_adjustments_effective"] == {}
    assert payload["weight_adjustments_suppressed"]["range_reversal_weight"]["reason"] == "DOUBLE_COUNTING_GUARD"


def test_bridge_builds_threshold_harden_and_changes_decision_for_strong_conflict():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "NAS100",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "AGAINST_HTF",
            "htf_against_severity": "HIGH",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_confidence": "HIGH",
            "previous_box_is_consolidation": True,
            "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
            "context_conflict_intensity": "HIGH",
            "trend_1h_age_seconds": 60,
            "trend_4h_age_seconds": 60,
            "trend_1d_age_seconds": 60,
            "previous_box_age_seconds": 60,
            "effective_entry_threshold": 40,
            "final_score": 42,
        }
    )

    assert payload["threshold_adjustment_requested"]["threshold_delta_direction"] == "HARDEN"
    assert payload["threshold_adjustment_requested"]["threshold_delta_points"] > 0.0
    assert payload["threshold_adjustment_effective"]["threshold_delta_points"] > 0.0
    assert "AGAINST_PREV_BOX_AND_HTF" in payload["threshold_adjustment_requested"]["threshold_delta_reason_keys"]
    assert payload["decision_counterfactual"]["without_bridge_decision"] == "ENTER"
    assert payload["decision_counterfactual"]["with_bridge_decision"] == "SKIP"
    assert payload["decision_counterfactual"]["bridge_changed_decision"] is True
    assert "THRESHOLD_DECISION_CHANGED" in payload["trace_reason_codes"]


def test_bridge_uses_late_chase_for_threshold_but_not_weight():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "XAUUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "BUY",
            "late_chase_risk_state": "HIGH",
            "late_chase_confidence": 0.8,
            "effective_entry_threshold": 45,
            "final_score": 49,
        }
    )

    assert payload["weight_adjustments_requested"] == {}
    assert payload["weight_adjustments_suppressed"]["LATE_CHASE_RISK"]["reason"] == "DEFER_TO_THRESHOLD_SIZE_V1"
    assert payload["threshold_adjustment_requested"]["threshold_delta_direction"] == "HARDEN"
    assert payload["threshold_adjustment_requested"]["threshold_delta_points"] > 0.0
    assert "LATE_CHASE_RISK" in payload["threshold_adjustment_requested"]["threshold_delta_reason_keys"]


def test_bridge_marks_signed_threshold_unavailable_when_base_threshold_missing():
    payload = build_state25_candidate_context_bridge_v1(
        {
            "symbol": "BTCUSD",
            "entry_stage": "balanced",
            "consumer_check_side": "SELL",
            "htf_alignment_state": "AGAINST_HTF",
            "htf_against_severity": "MEDIUM",
            "trend_1h_age_seconds": 60,
            "trend_4h_age_seconds": 60,
            "trend_1d_age_seconds": 60,
        }
    )

    assert STATE25_CONTEXT_BRIDGE_FAILURE_SIGNED_THRESHOLD_UNAVAILABLE in payload["failure_modes"]
    assert payload["threshold_adjustment_requested"]["threshold_delta_points"] == 0.0
    assert payload["threshold_adjustment_suppressed"]["reason"] == "NO_BASE_THRESHOLD"
