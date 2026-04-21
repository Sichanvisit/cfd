import pandas as pd

from backend.services.upper_reversal_breakout_conflict_validation import (
    build_upper_reversal_breakout_conflict_validation,
    render_upper_reversal_breakout_conflict_validation_markdown,
)


def test_upper_reversal_breakout_conflict_validation_proceeds_when_live_guard_materializes() -> None:
    runtime_status = {"updated_at": "2026-04-09T23:35:00+09:00"}
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T23:34:58",
                "symbol": "XAUUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "sell_vs_up_breakout",
                "active_action_conflict_precedence_owner": "directional_breakout",
                "active_action_conflict_breakout_direction": "UP",
                "active_action_conflict_breakout_target": "WATCH_BREAKOUT",
                "active_action_conflict_baseline_action": "SELL",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
            {
                "time": "2026-04-09T23:34:55",
                "symbol": "NAS100",
                "action": "",
                "outcome": "wait",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "PROBE_BREAKOUT",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "PROBE",
                "active_action_conflict_kind": "sell_vs_up_breakout",
                "active_action_conflict_precedence_owner": "breakout",
                "active_action_conflict_breakout_direction": "UP",
                "active_action_conflict_breakout_target": "PROBE_BREAKOUT",
                "active_action_conflict_baseline_action": "SELL",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
        ]
    )
    replay_frame = pd.DataFrame([{"symbol": "XAUUSD"}, {"symbol": "NAS100"}])
    replay_summary = {
        "target_row_count": 2,
        "replay_guard_applied_count": 2,
        "replay_bridge_conflict_selected_count": 2,
        "symbol_counts": '{"NAS100":1,"XAUUSD":1}',
        "replay_bridge_mode_counts": '{"active_action_conflict_resolution":2}',
    }

    frame, summary = build_upper_reversal_breakout_conflict_validation(
        runtime_status,
        entry_decisions,
        recent_limit=20,
        replay_result=(replay_frame, replay_summary),
    )
    markdown = render_upper_reversal_breakout_conflict_validation_markdown(summary, frame)

    assert summary["field_presence_ok"] is True
    assert summary["fresh_target_family_row_count"] == 2
    assert summary["live_conflict_detected_count"] == 2
    assert summary["live_guard_applied_count"] == 2
    assert summary["live_bridge_conflict_selected_count"] >= 2
    assert summary["recommended_next_action"] == "proceed_to_mf17_signoff_after_p0e_validation"
    assert not frame.empty
    assert "Upper-Reversal Breakout Conflict Validation" in markdown


def test_upper_reversal_breakout_conflict_validation_waits_for_fresh_live_rows_when_only_replay_support_exists() -> None:
    runtime_status = {"updated_at": "2026-04-09T23:36:00+09:00"}
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T23:35:58",
                "symbol": "XAUUSD",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "active_action_conflict_detected": False,
                "active_action_conflict_guard_applied": False,
                "active_action_conflict_resolution_state": "",
                "active_action_conflict_kind": "",
                "active_action_conflict_precedence_owner": "",
                "active_action_conflict_breakout_direction": "",
                "active_action_conflict_breakout_target": "",
                "active_action_conflict_baseline_action": "",
                "entry_candidate_bridge_mode": "",
                "entry_candidate_bridge_conflict_selected": False,
                "entry_candidate_bridge_action": "",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
        ]
    )
    replay_summary = {
        "target_row_count": 4,
        "replay_guard_applied_count": 4,
        "replay_bridge_conflict_selected_count": 4,
        "symbol_counts": '{"XAUUSD":4}',
        "replay_bridge_mode_counts": '{"active_action_conflict_resolution":4}',
    }

    _, summary = build_upper_reversal_breakout_conflict_validation(
        runtime_status,
        entry_decisions,
        recent_limit=20,
        replay_result=(pd.DataFrame([{"symbol": "XAUUSD"}]), replay_summary),
    )

    assert summary["fresh_target_family_row_count"] == 1
    assert summary["live_guard_applied_count"] == 0
    assert summary["replay_guard_applied_count"] == 4
    assert summary["recommended_next_action"] == "await_fresh_post_restart_upper_reversal_conflict_rows"


def test_upper_reversal_breakout_conflict_validation_flags_scope_gap_when_live_guard_and_residual_sell_coexist() -> None:
    runtime_status = {"updated_at": "2026-04-09T23:37:00+09:00"}
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T23:36:58",
                "symbol": "XAUUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "countertrend_action_state": "UP_PROBE",
                "countertrend_directional_candidate_action": "BUY",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "sell_vs_up_breakout",
                "active_action_conflict_precedence_owner": "directional_breakout",
                "active_action_conflict_breakout_direction": "UP",
                "active_action_conflict_breakout_target": "WATCH_BREAKOUT",
                "active_action_conflict_baseline_action": "SELL",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
            {
                "time": "2026-04-09T23:36:55",
                "symbol": "NAS100",
                "action": "SELL",
                "outcome": "entered",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_confirm",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "countertrend_action_state": "UP_WATCH",
                "countertrend_directional_candidate_action": "BUY",
                "active_action_conflict_detected": False,
                "active_action_conflict_guard_applied": False,
                "active_action_conflict_resolution_state": "",
                "active_action_conflict_kind": "",
                "active_action_conflict_precedence_owner": "",
                "active_action_conflict_breakout_direction": "",
                "active_action_conflict_breakout_target": "",
                "active_action_conflict_baseline_action": "",
                "entry_candidate_bridge_mode": "",
                "entry_candidate_bridge_conflict_selected": False,
                "entry_candidate_bridge_action": "",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
        ]
    )
    replay_summary = {
        "target_row_count": 6,
        "replay_guard_applied_count": 6,
        "replay_bridge_conflict_selected_count": 6,
        "symbol_counts": '{"NAS100":3,"XAUUSD":3}',
        "replay_bridge_mode_counts": '{"active_action_conflict_resolution":6}',
    }

    _, summary = build_upper_reversal_breakout_conflict_validation(
        runtime_status,
        entry_decisions,
        recent_limit=20,
        replay_result=(pd.DataFrame([{"symbol": "XAUUSD"}, {"symbol": "NAS100"}]), replay_summary),
    )

    assert summary["live_guard_applied_count"] == 1
    assert summary["live_residual_entered_sell_count"] == 1
    assert summary["recommended_next_action"] == "inspect_breakout_execution_precedence_scope_gap"


def test_upper_reversal_breakout_conflict_validation_includes_btc_upper_reversal_rows() -> None:
    runtime_status = {"updated_at": "2026-04-10T00:22:00+09:00"}
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-10T00:21:31",
                "symbol": "BTCUSD",
                "action": "",
                "outcome": "wait",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "breakout_candidate_direction": "UP",
                "breakout_candidate_action_target": "WATCH_BREAKOUT",
                "countertrend_action_state": "DO_NOTHING",
                "countertrend_directional_candidate_action": "",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "baseline_sell_vs_up_breakout",
                "active_action_conflict_precedence_owner": "breakout",
                "active_action_conflict_breakout_direction": "UP",
                "active_action_conflict_breakout_target": "WATCH_BREAKOUT",
                "active_action_conflict_baseline_action": "SELL",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
            },
        ]
    )
    replay_summary = {
        "target_row_count": 1,
        "replay_guard_applied_count": 1,
        "replay_bridge_conflict_selected_count": 1,
        "symbol_counts": '{"BTCUSD":1}',
        "replay_bridge_mode_counts": '{"active_action_conflict_resolution":1}',
    }

    frame, summary = build_upper_reversal_breakout_conflict_validation(
        runtime_status,
        entry_decisions,
        recent_limit=20,
        replay_result=(pd.DataFrame([{"symbol": "BTCUSD"}]), replay_summary),
    )

    assert summary["fresh_target_family_row_count"] == 1
    assert summary["live_guard_applied_count"] == 1
    assert summary["live_bridge_conflict_selected_count"] >= 1
    assert frame.iloc[0]["symbol"] == "BTCUSD"
