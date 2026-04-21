import pandas as pd

from backend.services.entry_candidate_bridge import (
    build_baseline_no_action_bridge,
    build_entry_candidate_bridge_flat_fields,
    build_entry_candidate_bridge_v1,
)


def test_entry_candidate_bridge_selects_breakout_candidate() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="NAS100",
        action="",
        entry_stage="READY",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_state": "initial_breakout",
            "breakout_confidence": 0.82,
            "breakout_failure_risk": 0.12,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "ENTER_NOW",
            "reason_summary": "breakout_entry|breakout_then_continue",
        },
        state25_candidate_log_only_trace_v1={
            "binding_mode": "log_only",
            "threshold_symbol_scope_hit": True,
            "threshold_stage_scope_hit": True,
        },
        forecast_state25_runtime_bridge_v1={
            "forecast_runtime_summary_v1": {
                "confirm_side": "SELL",
                "confirm_score": 0.61,
                "decision_hint": "CONFIRM_BIASED",
            }
        },
        forecast_state25_log_only_overlay_trace_v1={
            "candidate_wait_bias_action": "release_wait_bias",
        },
    )

    assert surface["baseline_no_action"] is True
    assert surface["candidate_available"] is True
    assert surface["selected_source"] == "breakout_candidate"
    assert surface["selected_action"] == "BUY"

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_source"] == "breakout_candidate"
    assert flat["breakout_candidate_action"] == "BUY"
    assert flat["breakout_candidate_source"] == "breakout_runtime_overlay"


def test_baseline_no_action_bridge_summary_counts_breakout_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:00:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:00:01",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "entry_candidate_bridge_available": True,
                "entry_candidate_bridge_selected": True,
                "entry_candidate_bridge_source": "breakout_candidate",
                "breakout_candidate_action": "BUY",
                "breakout_candidate_reason": "initial_breakout|breakout_entry",
            },
            {
                "time": "2026-04-08T21:59:01",
                "symbol": "NAS100",
                "action": "",
                "outcome": "skipped",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "entry_candidate_bridge_available": False,
                "entry_candidate_bridge_selected": False,
                "entry_candidate_bridge_source": "",
                "breakout_candidate_action": "",
                "breakout_candidate_reason": "",
            },
        ]
    )

    frame, summary = build_baseline_no_action_bridge(runtime_status, entry_decisions, recent_limit=20)

    assert len(frame) == 1
    assert summary["baseline_no_action_row_count"] == 2
    assert summary["bridge_selected_count"] == 1
    assert summary["breakout_candidate_count"] == 1
    assert summary["recommended_next_action"] == "implement_ai3_utility_gate_recast"


def test_entry_candidate_bridge_exposes_follow_through_surface_for_probe_breakout_candidate() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="outer_band_reversal_support_required_observe",
        blocked_by="outer_band_guard",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_state": "breakout_pullback",
            "breakout_type_candidate": "reclaim_breakout_candidate",
            "breakout_confidence": 0.44,
            "breakout_failure_risk": 0.31,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "PROBE_BREAKOUT",
            "reason_summary": "supportive_breakout_probe|probe_breakout",
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_selected"] is False
    assert flat["entry_candidate_surface_family"] == "follow_through_surface"
    assert flat["entry_candidate_surface_state"] == "pullback_resume"
    assert flat["breakout_candidate_surface_family"] == "follow_through_surface"
    assert flat["breakout_candidate_surface_state"] == "pullback_resume"
    assert flat["breakout_candidate_action_target"] == "PROBE_BREAKOUT"


def test_entry_candidate_bridge_selects_countertrend_sell_candidate() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="outer_band_reversal_support_required_observe",
        blocked_by="outer_band_guard",
        countertrend_continuation_signal_v1={
            "enabled": True,
            "signal_action": "SELL",
            "signal_confidence": 0.84,
            "reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_wait_block",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
            "warning_count": 3,
            "anti_long_score": 1.0,
            "anti_short_score": 0.0,
            "pro_up_score": 0.0,
            "pro_down_score": 0.92,
            "directional_bias": "DOWN",
            "directional_action_state": "DOWN_PROBE",
            "directional_candidate_action": "SELL",
            "directional_execution_action": "",
            "directional_state_reason": "down_probe::anti_long_strong_plus_pro_down_supportive",
            "directional_state_rank": 2,
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_down_bias_score": 0.964,
            "directional_up_bias_score": 0.0,
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_selected"] is True
    assert flat["entry_candidate_bridge_source"] == "countertrend_candidate"
    assert flat["entry_candidate_bridge_action"] == "SELL"
    assert flat["entry_candidate_surface_family"] == "follow_through_surface"
    assert flat["entry_candidate_surface_state"] == "continuation_follow"
    assert flat["countertrend_candidate_action"] == "SELL"
    assert flat["countertrend_continuation_enabled"] is True
    assert flat["countertrend_continuation_warning_count"] == 3
    assert flat["countertrend_anti_long_score"] == 1.0
    assert flat["countertrend_pro_down_score"] == 0.92
    assert flat["countertrend_directional_bias"] == "DOWN"
    assert flat["countertrend_action_state"] == "DOWN_PROBE"
    assert flat["countertrend_directional_candidate_action"] == "SELL"
    assert flat["countertrend_directional_execution_action"] == ""
    assert flat["countertrend_directional_state_reason"] == "down_probe::anti_long_strong_plus_pro_down_supportive"
    assert flat["countertrend_directional_state_rank"] == 2
    assert flat["countertrend_directional_owner_family"] == "direction_agnostic_continuation"
    assert flat["countertrend_directional_down_bias_score"] == 0.964
    assert flat["countertrend_directional_up_bias_score"] == 0.0


def test_entry_candidate_bridge_preserves_down_watch_without_selecting_sell() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="outer_band_reversal_support_required_observe",
        blocked_by="outer_band_guard",
        countertrend_continuation_signal_v1={
            "enabled": False,
            "watch_only": True,
            "signal_action": "",
            "signal_state": "down_continuation_watch",
            "signal_confidence": 0.46,
            "reason_summary": "forecast_wait_bias",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
            "warning_count": 1,
            "anti_long_score": 0.36,
            "anti_short_score": 0.0,
            "pro_up_score": 0.0,
            "pro_down_score": 0.34,
            "directional_bias": "DOWN",
            "directional_action_state": "DOWN_WATCH",
            "directional_candidate_action": "",
            "directional_execution_action": "",
            "directional_state_reason": "down_watch::anti_long_supportive_or_pro_down_initial",
            "directional_state_rank": 1,
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_down_bias_score": 0.351,
            "directional_up_bias_score": 0.0,
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_selected"] is False
    assert flat["countertrend_candidate_action"] == ""
    assert flat["countertrend_continuation_state"] == "down_continuation_watch"
    assert flat["countertrend_directional_bias"] == "DOWN"
    assert flat["countertrend_action_state"] == "DOWN_WATCH"
    assert flat["countertrend_directional_candidate_action"] == ""
    assert flat["countertrend_directional_execution_action"] == ""


def test_entry_candidate_bridge_selects_countertrend_buy_candidate_from_up_probe() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="upper_reject_probe_observe",
        blocked_by="forecast_guard",
        countertrend_continuation_signal_v1={
            "enabled": True,
            "signal_action": "BUY",
            "signal_state": "up_continuation_bias",
            "signal_confidence": 0.84,
            "reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_relief_watch",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
            "warning_count": 3,
            "anti_long_score": 0.0,
            "anti_short_score": 0.84,
            "pro_up_score": 0.92,
            "pro_down_score": 0.0,
            "directional_bias": "UP",
            "directional_action_state": "UP_PROBE",
            "directional_candidate_action": "BUY",
            "directional_execution_action": "",
            "directional_state_reason": "up_probe::anti_short_strong_plus_pro_up_supportive",
            "directional_state_rank": 2,
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_down_bias_score": 0.0,
            "directional_up_bias_score": 0.874,
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_selected"] is True
    assert flat["entry_candidate_bridge_source"] == "countertrend_candidate"
    assert flat["entry_candidate_bridge_action"] == "BUY"
    assert flat["countertrend_directional_bias"] == "UP"
    assert flat["countertrend_action_state"] == "UP_PROBE"
    assert flat["countertrend_directional_candidate_action"] == "BUY"
    assert flat["countertrend_candidate_action"] == "BUY"


def test_entry_candidate_bridge_selects_conflict_candidate_when_active_sell_is_downgraded() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="directional_conflict_watch",
        blocked_by="active_action_conflict_guard",
        countertrend_continuation_signal_v1={
            "enabled": True,
            "signal_action": "BUY",
            "signal_state": "up_continuation_bias",
            "signal_confidence": 0.84,
            "reason_summary": "forecast_wait_bias|belief_fragile_thesis|barrier_relief_watch",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
            "warning_count": 3,
            "anti_long_score": 0.0,
            "anti_short_score": 0.84,
            "pro_up_score": 0.92,
            "pro_down_score": 0.0,
            "directional_bias": "UP",
            "directional_action_state": "UP_PROBE",
            "directional_candidate_action": "BUY",
            "directional_execution_action": "",
            "directional_state_reason": "up_probe::anti_short_strong_plus_pro_up_supportive",
            "directional_state_rank": 2,
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_down_bias_score": 0.0,
            "directional_up_bias_score": 0.912,
        },
        active_action_conflict_guard_v1={
            "conflict_detected": True,
            "guard_eligible": True,
            "guard_applied": True,
            "resolution_state": "WATCH",
            "baseline_action": "SELL",
            "conflict_kind": "baseline_sell_vs_up_directional",
        },
    )

    assert surface["baseline_no_action"] is False
    assert surface["bridge_mode"] == "active_action_conflict_resolution"
    assert surface["candidate_available"] is True
    assert surface["candidate_count"] == 1
    assert surface["selected_source"] == "countertrend_candidate"
    assert surface["selected_action"] == "BUY"

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_mode"] == "active_action_conflict_resolution"
    assert flat["entry_candidate_bridge_active_conflict"] is True
    assert flat["entry_candidate_bridge_conflict_selected"] is True
    assert flat["entry_candidate_bridge_effective_baseline_action"] == "SELL"
    assert flat["entry_candidate_bridge_conflict_kind"] == "baseline_sell_vs_up_directional"
    assert flat["entry_candidate_bridge_selected"] is True
    assert flat["entry_candidate_bridge_source"] == "countertrend_candidate"
    assert flat["entry_candidate_bridge_action"] == "BUY"


def test_entry_candidate_bridge_selects_breakout_candidate_when_active_conflict_prefers_probe_breakout() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        observe_reason="breakout_conflict_probe",
        blocked_by="active_action_conflict_guard",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_state": "breakout_pullback",
            "breakout_confidence": 0.41,
            "breakout_failure_risk": 0.18,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "PROBE_BREAKOUT",
            "reason_summary": "supportive_breakout_probe|probe_breakout",
        },
        active_action_conflict_guard_v1={
            "conflict_detected": True,
            "guard_eligible": True,
            "guard_applied": True,
            "resolution_state": "PROBE",
            "baseline_action": "SELL",
            "conflict_kind": "baseline_sell_vs_up_breakout",
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_mode"] == "active_action_conflict_resolution"
    assert flat["entry_candidate_bridge_conflict_selected"] is True
    assert flat["entry_candidate_bridge_source"] == "breakout_candidate"
    assert flat["entry_candidate_bridge_action"] == "BUY"
    assert flat["breakout_candidate_conflict_action"] == "BUY"
    assert flat["breakout_candidate_conflict_mode"] == "active_action_conflict_resolution"


def test_entry_candidate_bridge_selects_breakout_candidate_when_watch_breakout_conflict_has_missing_metrics() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="BTCUSD",
        action="SELL",
        entry_stage="BALANCED",
        observe_reason="upper_reject_probe_observe",
        blocked_by="",
        breakout_event_runtime_v1={
            "available": True,
            "breakout_detected": True,
            "breakout_direction": "UP",
            "breakout_confidence": 0.0,
            "breakout_failure_risk": 0.0,
        },
        breakout_event_overlay_candidates_v1={
            "available": True,
            "enabled": True,
            "candidate_action_target": "WATCH_BREAKOUT",
            "reason_summary": "watch_breakout",
        },
        active_action_conflict_guard_v1={
            "conflict_detected": True,
            "guard_eligible": True,
            "guard_applied": True,
            "resolution_state": "WATCH",
            "baseline_action": "SELL",
            "conflict_kind": "baseline_sell_vs_up_breakout",
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_mode"] == "active_action_conflict_resolution"
    assert flat["entry_candidate_bridge_selected"] is True
    assert flat["entry_candidate_bridge_source"] == "breakout_candidate"
    assert flat["entry_candidate_bridge_action"] == "BUY"
    assert flat["breakout_candidate_conflict_mode"] == "watch_only_conflict_guard"


def test_entry_candidate_bridge_keeps_baseline_mode_when_conflict_not_eligible() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="SELL",
        entry_stage="BALANCED",
        blocked_by="",
        countertrend_continuation_signal_v1={
            "enabled": False,
            "watch_only": True,
            "signal_action": "",
            "signal_state": "up_continuation_watch",
            "signal_confidence": 0.46,
            "reason_summary": "barrier_relief_watch",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
            "warning_count": 1,
            "anti_long_score": 0.0,
            "anti_short_score": 0.18,
            "pro_up_score": 0.38,
            "pro_down_score": 0.0,
            "directional_bias": "UP",
            "directional_action_state": "UP_WATCH",
            "directional_candidate_action": "",
            "directional_execution_action": "",
            "directional_state_reason": "up_watch::anti_short_supportive_or_pro_up_initial",
            "directional_state_rank": 1,
            "directional_owner_family": "direction_agnostic_continuation",
            "directional_down_bias_score": 0.0,
            "directional_up_bias_score": 0.271,
        },
        active_action_conflict_guard_v1={
            "conflict_detected": True,
            "guard_eligible": False,
            "guard_applied": False,
            "resolution_state": "KEEP",
            "baseline_action": "SELL",
            "conflict_kind": "baseline_sell_vs_up_directional",
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_mode"] == "baseline_action_keep"
    assert flat["entry_candidate_bridge_active_conflict"] is True
    assert flat["entry_candidate_bridge_conflict_selected"] is False
    assert flat["entry_candidate_bridge_selected"] is False


def test_entry_candidate_bridge_falls_back_to_legacy_countertrend_signal_action() -> None:
    surface = build_entry_candidate_bridge_v1(
        symbol="XAUUSD",
        action="",
        entry_stage="BALANCED",
        countertrend_continuation_signal_v1={
            "enabled": True,
            "signal_action": "SELL",
            "signal_confidence": 0.78,
            "reason_summary": "legacy_countertrend",
            "surface_family": "follow_through_surface",
            "surface_state": "continuation_follow",
        },
    )

    flat = build_entry_candidate_bridge_flat_fields(surface)
    assert flat["entry_candidate_bridge_selected"] is True
    assert flat["entry_candidate_bridge_action"] == "SELL"
    assert flat["countertrend_action_state"] == ""
