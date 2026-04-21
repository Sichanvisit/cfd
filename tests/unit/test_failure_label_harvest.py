import pandas as pd

from backend.services.failure_label_harvest import build_failure_label_harvest


def test_failure_label_harvest_collects_confirmed_and_candidate_rows() -> None:
    check_color = pd.DataFrame(
        [
            {
                "observation_event_id": "check_color_label_formalization_v1:btc_episode_001",
                "episode_id": "btc_episode_001",
                "symbol": "BTCUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "pullback_resume",
                "failure_label": "failed_follow_through",
                "supervision_strength": "strong",
                "source_group": "manual_chart",
                "label_reason": "manual pullback resume miss",
                "visual_label_token": "blue_timing:check_better_entry",
                "anchor_time": "2026-04-09T00:15:00+09:00",
            }
        ]
    )
    surface_time_axis = pd.DataFrame(
        [
            {
                "episode_id": "btc_episode_001",
                "symbol": "BTCUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "pullback_resume",
                "time_axis_phase": "continuation_window",
                "time_since_breakout_minutes": 3.0,
                "time_since_entry_minutes": 8.0,
                "bars_in_state": 3.0,
                "momentum_decay": 0.25,
                "anchor_time": "2026-04-09T00:15:00+09:00",
            }
        ]
    )
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T02:26:07+09:00",
                "symbol": "XAUUSD",
                "outcome": "skipped",
                "blocked_by": "range_lower_buy_requires_lower_edge",
                "action_none_reason": "probe_not_promoted",
                "observe_reason": "lower_rebound_probe_observe",
                "entry_candidate_surface_family": "initial_entry_surface",
                "entry_candidate_surface_state": "timing_better_entry",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "breakout_candidate_surface_family": "follow_through_surface",
                "breakout_candidate_surface_state": "continuation_follow",
            },
            {
                "time": "2026-04-09T02:26:09+09:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "blocked_by": "middle_sr_anchor_guard",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "middle_sr_anchor_required_observe",
                "entry_candidate_surface_family": "initial_entry_surface",
                "entry_candidate_surface_state": "timing_better_entry",
                "breakout_candidate_action_target": "WAIT_MORE",
                "breakout_candidate_surface_family": "",
                "breakout_candidate_surface_state": "",
            },
            {
                "time": "2026-04-09T02:26:15+09:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "blocked_by": "forecast_guard",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "upper_reject_probe_observe",
                "entry_candidate_surface_family": "initial_entry_surface",
                "entry_candidate_surface_state": "initial_break",
                "breakout_candidate_action_target": "WAIT_MORE",
                "breakout_candidate_surface_family": "",
                "breakout_candidate_surface_state": "",
            },
            {
                "time": "2026-04-09T02:26:20+09:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "blocked_by": "dynamic_threshold_not_met",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "upper_edge_observe",
                "entry_candidate_surface_family": "initial_entry_surface",
                "entry_candidate_surface_state": "late_release",
                "breakout_candidate_action_target": "WAIT_MORE",
                "breakout_candidate_surface_family": "",
                "breakout_candidate_surface_state": "",
            },
        ]
    )
    market_family_entry_audit = {
        "summary": {
            "symbol_focus_map": '{"BTCUSD":"inspect_btc_middle_anchor_probe_relief","NAS100":"inspect_nas_conflict_observe_decomposition","XAUUSD":"inspect_xau_outer_band_follow_through_bridge"}'
        }
    }
    market_family_exit_audit = {
        "summary": {
            "symbol_focus_map": '{"XAUUSD":"inspect_xauusd_runner_preservation","NAS100":"inspect_nas100_protective_exit_overfire"}',
            "symbol_auto_exit_reason_counts": '{"XAUUSD":{"Target":3,"Lock Exit":2},"NAS100":{"Protect Exit":4}}',
            "generated_at": "2026-04-09T02:30:00+09:00",
        }
    }
    exit_surface_observation = {
        "status": "await_live_runner_preservation",
        "surface_state_counts": {"EXIT_PROTECT": 1},
    }

    frame, summary = build_failure_label_harvest(
        check_color,
        surface_time_axis,
        entry_decisions,
        market_family_entry_audit,
        market_family_exit_audit,
        exit_surface_observation,
        recent_entry_limit=20,
    )

    assert summary["confirmed_row_count"] == 1
    assert summary["candidate_row_count"] >= 5
    assert "failed_follow_through" in summary["failure_label_counts"]
    assert "missed_good_wait_release" in summary["failure_label_counts"]
    assert "false_breakout" in summary["failure_label_counts"]
    assert "late_entry_chase_fail" in summary["failure_label_counts"]
    assert "early_exit_regret" in summary["failure_label_counts"]

    confirmed_row = frame.loc[frame["harvest_strength"] == "confirmed"].iloc[0]
    assert confirmed_row["time_axis_phase"] == "continuation_window"
    assert confirmed_row["bars_in_state"] == 3.0

    xau_row = frame.loc[(frame["symbol"] == "XAUUSD") & (frame["harvest_source"] == "runtime_entry_blocker")].iloc[0]
    assert xau_row["failure_label"] == "failed_follow_through"
    assert xau_row["source_focus"] == "inspect_xau_outer_band_follow_through_bridge"


def test_failure_label_harvest_returns_empty_summary_when_no_inputs() -> None:
    frame, summary = build_failure_label_harvest(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        {},
        {},
        {},
    )

    assert frame.empty
    assert summary["row_count"] == 0
    assert summary["recommended_next_action"] == "collect_failure_label_inputs"


def test_failure_label_harvest_includes_wrong_side_conflict_labels() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T20:36:48+09:00",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "blocked_by": "active_action_conflict_guard",
                "action_none_reason": "wrong_side_sell_pressure",
                "observe_reason": "directional_conflict_watch",
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
                "breakout_candidate_action_target": "",
                "breakout_candidate_surface_family": "",
                "breakout_candidate_surface_state": "",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "baseline_sell_vs_up_directional",
                "active_action_conflict_baseline_action": "SELL",
                "active_action_conflict_directional_action": "BUY",
                "active_action_conflict_directional_state": "UP_PROBE",
                "active_action_conflict_directional_owner_family": "follow_through_surface",
                "active_action_conflict_up_bias_score": 0.91,
                "active_action_conflict_down_bias_score": 0.08,
                "active_action_conflict_bias_gap": 0.83,
                "active_action_conflict_warning_count": 3,
                "active_action_conflict_reason_summary": "baseline_sell_vs_up_directional|up_probe",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
                "entry_candidate_bridge_conflict_selected": True,
            }
        ]
    )
    market_family_entry_audit = {
        "summary": {
            "symbol_focus_map": '{"XAUUSD":"inspect_xau_upper_reversal_conflict_guard"}'
        }
    }

    frame, summary = build_failure_label_harvest(
        pd.DataFrame(),
        pd.DataFrame(),
        entry_decisions,
        market_family_entry_audit,
        {},
        {},
        recent_entry_limit=50,
    )

    assert "wrong_side_sell_pressure" in summary["failure_label_counts"]
    assert "missed_up_continuation" in summary["failure_label_counts"]
    wrong_side = frame.loc[frame["failure_label"] == "wrong_side_sell_pressure"].iloc[0]
    assert wrong_side["harvest_source"] == "wrong_side_conflict_runtime"
    assert wrong_side["surface_label_family"] == "follow_through_surface"
