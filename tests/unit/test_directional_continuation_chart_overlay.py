from backend.services.directional_continuation_chart_overlay import (
    build_directional_continuation_chart_overlay_flat_fields_v1,
    build_directional_continuation_chart_overlay_state,
)


def test_build_directional_continuation_chart_overlay_state_selects_up_watch_on_wrong_side_sell_conflict():
    candidates = [
        {
            "symbol": "XAUUSD",
            "continuation_direction": "UP",
            "summary_ko": "XAUUSD 상승 지속 누락 가능성 관찰",
            "source_kind": "semantic_baseline_no_action_cluster",
            "source_labels_ko": ["semantic observe cluster"],
            "candidate_key": "up-key",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 15,
            "symbol_share": 0.92,
            "global_share": 0.22,
            "priority_score": 81.0,
            "misread_confidence": 0.83,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "XAUUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "XAUUSD 하락 지속 누락 가능성 관찰",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "down-key",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 4,
            "symbol_share": 0.18,
            "global_share": 0.08,
            "priority_score": 26.0,
            "misread_confidence": 0.44,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_side": "SELL",
        "consumer_check_reason": "upper_break_fail_confirm",
        "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF",
        "trend_15m_direction": "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "box_state": "UPPER",
        "bb_state": "UPPER_EDGE",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "XAUUSD",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "UP"
    assert overlay["overlay_event_kind_hint"] == "BUY_WATCH"
    assert overlay["overlay_reason_match"] is True
    assert overlay["overlay_up_score"] > overlay["overlay_down_score"]


def test_build_directional_continuation_chart_overlay_state_selects_down_watch_on_downtrend_reject():
    candidates = [
        {
            "symbol": "BTCUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "BTCUSD 하락 지속 누락 가능성 관찰",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "down-key",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 9,
            "symbol_share": 0.66,
            "global_share": 0.16,
            "priority_score": 63.0,
            "misread_confidence": 0.71,
            "dominant_observe_reason": "upper_reject_probe_observe",
        }
    ]
    row = {
        "observe_reason": "upper_reject_probe_observe",
        "trend_15m_direction": "DOWNTREND",
        "trend_1h_direction": "DOWNTREND",
        "trend_4h_direction": "DOWNTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKDOWN_HELD",
        "previous_box_relation": "BELOW",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "BTCUSD",
        row,
        continuation_candidates=candidates,
    )
    flat = build_directional_continuation_chart_overlay_flat_fields_v1(overlay)

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "DOWN"
    assert overlay["overlay_event_kind_hint"] == "SELL_WATCH"
    assert flat["directional_continuation_overlay_event_kind_hint"] == "SELL_WATCH"
    assert flat["directional_continuation_overlay_enabled"] is True


def test_build_directional_continuation_chart_overlay_state_breaks_tight_btc_tie_with_current_reason_when_no_previous_overlay():
    candidates = [
        {
            "symbol": "BTCUSD",
            "continuation_direction": "UP",
            "summary_ko": "BTCUSD up candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 6,
            "symbol_share": 0.48,
            "global_share": 0.12,
            "priority_score": 65.2,
            "misread_confidence": 0.70,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "BTCUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "BTCUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 5,
            "symbol_share": 0.42,
            "global_share": 0.10,
            "priority_score": 59.2,
            "misread_confidence": 0.65,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_reason": "conflict_box_upper_bb20_lower_upper_dominant_observe",
        "blocked_by": "",
        "action_none_reason": "observe_state_wait",
        "quick_trace_state": "OBSERVE",
        "trend_15m_direction": "MIXED",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "INSIDE",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "breakout_candidate_direction": "NONE",
        "breakout_candidate_action_target": "WAIT_MORE",
        "context_conflict_state": "CONTEXT_MIXED",
        "context_conflict_score": 0.35,
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "BTCUSD",
        row,
        continuation_candidates=candidates,
    )
    flat = build_directional_continuation_chart_overlay_flat_fields_v1(overlay)

    assert overlay["overlay_enabled"] is False
    assert overlay["overlay_selection_state"] == "DIRECTION_TIE"
    assert flat["directional_continuation_overlay_event_kind_hint"] == ""
    assert flat["directional_continuation_overlay_enabled"] is False


def test_build_directional_continuation_chart_overlay_state_prefers_down_over_stale_wrong_side_up_when_current_cycle_is_weak():
    candidates = [
        {
            "symbol": "XAUUSD",
            "continuation_direction": "UP",
            "summary_ko": "XAUUSD stale up candidate",
            "source_kind": "wrong_side_conflict_harvest",
            "source_labels_ko": ["wrong-side conflict"],
            "candidate_key": "wrong-side-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 6,
            "symbol_share": 1.0,
            "global_share": 1.0,
            "priority_score": 82.2,
            "misread_confidence": 0.94,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "XAUUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "XAUUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "market-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 5,
            "symbol_share": 0.55,
            "global_share": 0.18,
            "priority_score": 58.0,
            "misread_confidence": 0.67,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_side": "SELL",
        "consumer_check_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "quick_trace_state": "BLOCKED",
        "active_action_conflict_breakout_failure_risk": 1.0,
        "trend_15m_direction": "MIXED",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKOUT_FAILED",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "MID",
        "breakout_candidate_direction": "DOWN",
        "breakout_candidate_action_target": "PROBE_BREAKOUT",
        "directional_continuation_accuracy_measured_count": 9,
        "directional_continuation_accuracy_sample_count": 9,
        "directional_continuation_accuracy_correct_rate": 0.4444,
        "directional_continuation_accuracy_false_alarm_rate": 0.5556,
        "directional_continuation_accuracy_last_candidate_key": "wrong-side-up",
        "directional_continuation_accuracy_last_state": "CORRECT",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "XAUUSD",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "DOWN"
    assert overlay["overlay_event_kind_hint"] == "SELL_WATCH"


def test_build_directional_continuation_chart_overlay_state_suppresses_poor_accuracy_up_signal_without_fresh_confirmation():
    candidates = [
        {
            "symbol": "NAS100",
            "continuation_direction": "UP",
            "summary_ko": "NAS100 up continuation",
            "source_kind": "semantic_baseline_no_action_cluster",
            "source_labels_ko": ["semantic observe cluster"],
            "candidate_key": "semantic-nas-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 15,
            "symbol_share": 0.94,
            "global_share": 0.22,
            "priority_score": 81.4,
            "misread_confidence": 0.90,
            "dominant_observe_reason": "upper_break_fail_confirm",
        }
    ]
    row = {
        "consumer_check_side": "SELL",
        "consumer_check_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "quick_trace_state": "BLOCKED",
        "active_action_conflict_breakout_failure_risk": 1.0,
        "trend_15m_direction": "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "box_state": "ABOVE",
        "bb_state": "UNKNOWN",
        "breakout_candidate_direction": "NONE",
        "breakout_candidate_action_target": "WAIT_MORE",
        "directional_continuation_accuracy_measured_count": 7,
        "directional_continuation_accuracy_sample_count": 10,
        "directional_continuation_accuracy_correct_rate": 0.4286,
        "directional_continuation_accuracy_false_alarm_rate": 0.5714,
        "directional_continuation_accuracy_last_candidate_key": "semantic-nas-up",
        "directional_continuation_accuracy_last_state": "INCORRECT",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "NAS100",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is False
    assert overlay["overlay_selection_state"] == "LOW_ALIGNMENT"


def test_build_directional_continuation_chart_overlay_state_keeps_nas_up_watch_on_breakout_pullback_resume():
    candidates = [
        {
            "symbol": "NAS100",
            "continuation_direction": "UP",
            "summary_ko": "NAS100 up continuation",
            "source_kind": "semantic_baseline_no_action_cluster",
            "source_labels_ko": ["semantic observe cluster", "market-family observe"],
            "candidate_key": "semantic-nas-up-resume",
            "registry_key": "misread:semantic_continuation_gap_cluster",
            "repeat_count": 2,
            "symbol_share": 0.94,
            "global_share": 0.22,
            "priority_score": 81.4,
            "misread_confidence": 0.90,
            "dominant_observe_reason": "upper_break_fail_confirm",
        }
    ]
    row = {
        "htf_alignment_state": "WITH_HTF",
        "consumer_check_side": "SELL",
        "consumer_check_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_guard",
        "quick_trace_state": "BLOCKED",
        "trend_15m_direction": "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKOUT_HELD",
        "previous_box_relation": "ABOVE",
        "previous_box_low_retest_count": 2,
        "box_state": "ABOVE",
        "bb_state": "UPPER_EDGE",
        "breakout_candidate_direction": "UP",
        "breakout_candidate_action_target": "WATCH_BREAKOUT",
        "breakout_candidate_surface_state": "continuation_follow",
        "directional_continuation_accuracy_measured_count": 12,
        "directional_continuation_accuracy_sample_count": 12,
        "directional_continuation_accuracy_correct_rate": 0.50,
        "directional_continuation_accuracy_false_alarm_rate": 0.50,
        "directional_continuation_accuracy_last_candidate_key": "semantic-nas-up-resume",
        "directional_continuation_accuracy_last_state": "CORRECT",
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
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "NAS100",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "UP"
    assert overlay["overlay_event_kind_hint"] == "BUY_WATCH"


def test_build_directional_continuation_chart_overlay_state_suppresses_ambiguous_btc_direction_when_scores_are_weak():
    candidates = [
        {
            "symbol": "BTCUSD",
            "continuation_direction": "UP",
            "summary_ko": "BTCUSD up candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 6,
            "symbol_share": 0.48,
            "global_share": 0.12,
            "priority_score": 65.2,
            "misread_confidence": 0.70,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "BTCUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "BTCUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 5,
            "symbol_share": 0.42,
            "global_share": 0.10,
            "priority_score": 59.2,
            "misread_confidence": 0.65,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "quick_trace_state": "BLOCKED",
        "active_action_conflict_breakout_failure_risk": 1.0,
        "trend_15m_direction": "MIXED",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "BREAKOUT_FAILED",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "MID",
        "breakout_candidate_direction": "NONE",
        "breakout_candidate_action_target": "WAIT_MORE",
        "directional_continuation_accuracy_measured_count": 3,
        "directional_continuation_accuracy_sample_count": 6,
        "directional_continuation_accuracy_correct_rate": 0.3333,
        "directional_continuation_accuracy_false_alarm_rate": 0.6667,
        "directional_continuation_accuracy_last_candidate_key": "btc-up",
        "directional_continuation_accuracy_last_state": "INCORRECT",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "BTCUSD",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is False
    assert overlay["overlay_selection_state"] == "LOW_ALIGNMENT"


def test_build_directional_continuation_chart_overlay_state_carries_forward_previous_direction_on_btc_tie():
    candidates = [
        {
            "symbol": "BTCUSD",
            "continuation_direction": "UP",
            "summary_ko": "BTCUSD up candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 6,
            "symbol_share": 0.56,
            "global_share": 0.12,
            "priority_score": 63.0,
            "misread_confidence": 0.69,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "BTCUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "BTCUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "btc-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 6,
            "symbol_share": 0.54,
            "global_share": 0.12,
            "priority_score": 62.0,
            "misread_confidence": 0.68,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_reason": "conflict_box_upper_bb20_lower_upper_dominant_observe",
        "blocked_by": "",
        "action_none_reason": "observe_state_wait",
        "quick_trace_state": "OBSERVE",
        "trend_15m_direction": "MIXED",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "INSIDE",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "UNKNOWN",
        "breakout_candidate_direction": "NONE",
        "breakout_candidate_action_target": "WAIT_MORE",
        "context_conflict_state": "CONTEXT_MIXED",
        "context_conflict_score": 0.35,
    }
    previous_overlay = {
        "overlay_enabled": True,
        "overlay_direction": "UP",
        "overlay_event_kind_hint": "BUY_WATCH",
        "overlay_candidate_key": "btc-up",
        "overlay_score": 0.61,
        "overlay_repeat_count": 2,
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "BTCUSD",
        row,
        continuation_candidates=candidates,
        previous_overlay_state=previous_overlay,
    )

    assert overlay["overlay_enabled"] is False
    assert overlay["overlay_selection_state"] == "DIRECTION_TIE"
    assert overlay["overlay_suppression_reason"] == "TIGHT_DIRECTION_TIE"


def test_build_directional_continuation_chart_overlay_state_penalizes_stale_wrong_side_up_when_current_reason_is_lower_dominant():
    candidates = [
        {
            "symbol": "XAUUSD",
            "continuation_direction": "UP",
            "summary_ko": "XAUUSD stale up candidate",
            "source_kind": "wrong_side_conflict_harvest",
            "source_labels_ko": ["wrong-side conflict"],
            "candidate_key": "wrong-side-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 8,
            "symbol_share": 1.0,
            "global_share": 1.0,
            "priority_score": 82.2,
            "misread_confidence": 0.94,
            "dominant_observe_reason": "false_down_pressure_in_uptrend",
        },
        {
            "symbol": "XAUUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "XAUUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "market-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 5,
            "symbol_share": 0.55,
            "global_share": 0.18,
            "priority_score": 58.0,
            "misread_confidence": 0.67,
            "dominant_observe_reason": "upper_edge_observe",
        },
    ]
    row = {
        "consumer_check_reason": "conflict_box_upper_bb20_lower_lower_dominant_observe",
        "consumer_check_side": "",
        "blocked_by": "",
        "action_none_reason": "observe_state_wait",
        "quick_trace_state": "OBSERVE",
        "trend_15m_direction": "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "MIXED",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "RECLAIMED",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "LOWER_EDGE",
        "breakout_candidate_direction": "NONE",
        "breakout_candidate_action_target": "WAIT_MORE",
        "context_conflict_state": "CONTEXT_MIXED",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "XAUUSD",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "DOWN"
    assert overlay["overlay_event_kind_hint"] == "SELL_WATCH"
    assert overlay["overlay_down_score"] > overlay["overlay_up_score"]


def test_build_directional_continuation_chart_overlay_state_uses_structural_alignment_to_escape_low_alignment():
    candidates = [
        {
            "symbol": "XAUUSD",
            "continuation_direction": "UP",
            "summary_ko": "XAUUSD up candidate",
            "source_kind": "semantic_baseline_no_action_cluster",
            "source_labels_ko": ["semantic observe cluster"],
            "candidate_key": "xau-up",
            "registry_key": "misread:directional_up_continuation_conflict",
            "repeat_count": 8,
            "symbol_share": 0.61,
            "global_share": 0.14,
            "priority_score": 49.0,
            "misread_confidence": 0.58,
            "dominant_observe_reason": "upper_break_fail_confirm",
        },
        {
            "symbol": "XAUUSD",
            "continuation_direction": "DOWN",
            "summary_ko": "XAUUSD down candidate",
            "source_kind": "market_family_entry_audit",
            "source_labels_ko": ["market-family observe"],
            "candidate_key": "xau-down",
            "registry_key": "misread:directional_down_continuation_conflict",
            "repeat_count": 7,
            "symbol_share": 0.58,
            "global_share": 0.14,
            "priority_score": 47.0,
            "misread_confidence": 0.57,
            "dominant_observe_reason": "upper_reject_probe_observe",
        },
    ]
    row = {
        "consumer_check_reason": "upper_break_fail_confirm",
        "consumer_check_side": "SELL",
        "htf_alignment_state": "WITH_HTF",
        "trend_15m_direction": "UPTREND",
        "trend_1h_direction": "UPTREND",
        "trend_4h_direction": "UPTREND",
        "trend_1d_direction": "MIXED",
        "previous_box_break_state": "RECLAIMED",
        "previous_box_relation": "INSIDE",
        "box_state": "UPPER",
        "bb_state": "BREAKOUT",
        "breakout_candidate_direction": "UP",
        "breakout_candidate_action_target": "WATCH_BREAKOUT",
        "quick_trace_state": "OBSERVE",
    }

    overlay = build_directional_continuation_chart_overlay_state(
        "XAUUSD",
        row,
        continuation_candidates=candidates,
    )

    assert overlay["overlay_enabled"] is True
    assert overlay["overlay_direction"] == "UP"
    assert overlay["overlay_event_kind_hint"] == "BUY_WATCH"
