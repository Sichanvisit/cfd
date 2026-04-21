import pandas as pd

from backend.services.wrong_side_conflict_replay_harness import (
    build_wrong_side_conflict_replay_harness,
)


def test_wrong_side_conflict_replay_harness_replays_xau_upper_sell_conflict() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T22:42:21+09:00",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "action": "SELL",
                "outcome": "skipped",
                "blocked_by": "clustered_entry_price_zone",
                "action_none_reason": "execution_soft_blocked",
                "observe_reason": "upper_break_fail_confirm",
                "entry_stage": "balanced",
                "compatibility_mode": "hybrid",
                "core_reason": "energy_soft_block",
                "core_allowed_action": "SELL_ONLY",
                "entry_candidate_bridge_mode": "baseline_action_keep",
                "entry_candidate_bridge_source": "",
                "entry_candidate_bridge_action": "",
                "active_action_conflict_detected": False,
                "active_action_conflict_guard_applied": False,
                "countertrend_continuation_enabled": True,
                "countertrend_continuation_action": "BUY",
                "countertrend_continuation_confidence": 0.66,
                "countertrend_continuation_reason_summary": "forecast_wait_bias|belief_fragile_thesis",
                "countertrend_continuation_warning_count": 2,
                "countertrend_continuation_surface_family": "follow_through_surface",
                "countertrend_continuation_surface_state": "continuation_follow",
                "countertrend_anti_long_score": 0.0,
                "countertrend_anti_short_score": 0.66,
                "countertrend_pro_up_score": 0.58,
                "countertrend_pro_down_score": 0.0,
                "countertrend_directional_bias": "UP",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_directional_execution_action": "",
                "countertrend_directional_state_reason": "up_probe::anti_short_strong_plus_pro_up_supportive",
                "countertrend_directional_state_rank": 2,
                "countertrend_directional_owner_family": "direction_agnostic_continuation",
                "countertrend_directional_down_bias_score": 0.0,
                "countertrend_directional_up_bias_score": 0.624,
                "breakout_candidate_confidence": 0.0,
                "breakout_candidate_source": "breakout_runtime_overlay",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_surface_family": "initial_entry_surface",
                "breakout_candidate_surface_state": "initial_break",
                "forecast_state25_overlay_reason_summary": "wait_bias_hold|wait_reinforce",
                "belief_action_hint_reason_summary": "fragile_thesis|reduce_risk",
                "barrier_action_hint_reason_summary": "",
                "box_state": "ABOVE",
                "bb_state": "BREAKOUT",
            }
        ]
    )

    frame, summary = build_wrong_side_conflict_replay_harness(entry_decisions, recent_limit=50)

    assert summary["target_row_count"] == 1
    assert summary["replay_row_count"] == 1
    assert summary["delta_guard_apply_count"] == 1
    assert summary["replay_bridge_conflict_selected_count"] == 1

    row = frame.iloc[0]
    assert bool(row["replay_conflict_detected"]) is True
    assert bool(row["replay_guard_applied"]) is True
    assert row["replay_resolution_state"] == "WATCH"
    assert row["replay_bridge_mode"] == "active_action_conflict_resolution"
    assert row["replay_bridge_source"] == "countertrend_candidate"
    assert row["replay_bridge_action"] == "BUY"
    assert bool(row["breakout_sensed_up"]) is True


def test_wrong_side_conflict_replay_harness_reports_recent_breakout_conflicts() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T22:40:58+09:00",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "action": "SELL",
                "outcome": "skipped",
                "blocked_by": "clustered_entry_price_zone",
                "action_none_reason": "execution_soft_blocked",
                "observe_reason": "upper_break_fail_confirm",
                "core_allowed_action": "SELL_ONLY",
                "entry_candidate_bridge_mode": "baseline_action_keep",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_up_bias_score": 0.624,
                "breakout_candidate_source": "breakout_runtime_overlay",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-09T22:43:01+09:00",
                "symbol": "NAS100",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "action": "SELL",
                "outcome": "entered",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "upper_break_fail_confirm",
                "core_allowed_action": "SELL_ONLY",
                "entry_candidate_bridge_mode": "baseline_action_keep",
                "countertrend_directional_candidate_action": "",
                "countertrend_action_state": "DO_NOTHING",
                "countertrend_directional_up_bias_score": 0.0,
                "breakout_candidate_source": "breakout_runtime_overlay",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "breakout_candidate_direction": "UP",
            },
        ]
    )

    _, summary = build_wrong_side_conflict_replay_harness(entry_decisions, recent_limit=50)

    breakout_summary = summary["recent_breakout_conflict_summary"]
    assert breakout_summary["row_count"] == 2
    assert breakout_summary["sell_only_conflict_count"] == 2
    assert breakout_summary["action_sell_count"] == 2
    assert breakout_summary["watch_only_target_count"] == 2
    assert breakout_summary["breakout_unselected_count"] == 2


def test_wrong_side_conflict_replay_harness_includes_nas_upper_reversal_sell_targets() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T22:43:01+09:00",
                "symbol": "NAS100",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "action": "SELL",
                "outcome": "entered",
                "blocked_by": "",
                "action_none_reason": "",
                "observe_reason": "upper_break_fail_confirm",
                "entry_stage": "balanced",
                "compatibility_mode": "hybrid",
                "core_reason": "energy_soft_block",
                "core_allowed_action": "SELL_ONLY",
                "entry_candidate_bridge_mode": "baseline_action_keep",
                "entry_candidate_bridge_action": "",
                "countertrend_directional_candidate_action": "BUY",
                "countertrend_action_state": "UP_WATCH",
                "countertrend_directional_up_bias_score": 0.55,
                "breakout_candidate_source": "breakout_runtime_overlay",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "breakout_candidate_direction": "UP",
            }
        ]
    )

    frame, summary = build_wrong_side_conflict_replay_harness(entry_decisions, recent_limit=50)

    assert summary["target_row_count"] == 1
    assert summary["replay_guard_applied_count"] == 1
    assert frame.iloc[0]["symbol"] == "NAS100"
