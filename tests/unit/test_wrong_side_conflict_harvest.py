import pandas as pd

from backend.services.wrong_side_conflict_harvest import (
    build_wrong_side_conflict_failure_rows,
    build_wrong_side_conflict_harvest,
)


def test_wrong_side_conflict_harvest_detects_xau_sell_vs_up_conflict() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T20:36:48+09:00",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "outcome": "wait",
                "action": "",
                "blocked_by": "active_action_conflict_guard",
                "action_none_reason": "wrong_side_sell_pressure",
                "observe_reason": "directional_conflict_watch",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "baseline_sell_vs_up_directional",
                "active_action_conflict_baseline_action": "SELL",
                "active_action_conflict_directional_action": "BUY",
                "active_action_conflict_directional_state": "UP_PROBE",
                "active_action_conflict_directional_owner_family": "follow_through_surface",
                "active_action_conflict_up_bias_score": 0.912,
                "active_action_conflict_down_bias_score": 0.11,
                "active_action_conflict_bias_gap": 0.802,
                "active_action_conflict_warning_count": 3,
                "active_action_conflict_reason_summary": "baseline_sell_vs_up_directional|up_probe",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
            }
        ]
    )

    frame, summary = build_wrong_side_conflict_harvest(entry_decisions, recent_limit=50)

    assert summary["row_count"] == 1
    assert summary["guard_applied_count"] == 1
    assert summary["bridge_conflict_selected_count"] == 1
    assert "wrong_side_sell_pressure" in summary["primary_failure_label_counts"]
    assert "missed_up_continuation" in summary["continuation_failure_label_counts"]
    row = frame.iloc[0]
    assert row["primary_failure_label"] == "wrong_side_sell_pressure"
    assert row["continuation_failure_label"] == "missed_up_continuation"
    assert row["context_failure_label"] == "false_down_pressure_in_uptrend"
    assert row["bridge_mode"] == "active_action_conflict_resolution"


def test_wrong_side_conflict_failure_rows_expand_primary_and_continuation_labels() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T20:36:48+09:00",
                "symbol": "XAUUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_break_fail_confirm",
                "outcome": "wait",
                "blocked_by": "active_action_conflict_guard",
                "action_none_reason": "wrong_side_sell_pressure",
                "observe_reason": "directional_conflict_watch",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "baseline_sell_vs_up_directional",
                "active_action_conflict_baseline_action": "SELL",
                "active_action_conflict_directional_action": "BUY",
                "active_action_conflict_directional_state": "UP_PROBE",
                "active_action_conflict_directional_owner_family": "follow_through_surface",
                "active_action_conflict_up_bias_score": 0.88,
                "active_action_conflict_down_bias_score": 0.12,
                "active_action_conflict_bias_gap": 0.76,
                "active_action_conflict_warning_count": 3,
                "active_action_conflict_reason_summary": "baseline_sell_vs_up_directional|up_probe",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_source": "countertrend_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
                "entry_candidate_surface_family": "follow_through_surface",
                "entry_candidate_surface_state": "continuation_follow",
            }
        ]
    )

    rows = build_wrong_side_conflict_failure_rows(
        entry_decisions,
        generated_at="2026-04-09T20:40:00+09:00",
        recent_limit=20,
        focus_map={"XAUUSD": "inspect_xau_upper_reversal_conflict_guard"},
    )

    labels = {row["failure_label"] for row in rows}
    assert labels == {"wrong_side_sell_pressure", "missed_up_continuation"}
    assert all(row["surface_label_family"] == "follow_through_surface" for row in rows)
    assert all(row["source_focus"] == "inspect_xau_upper_reversal_conflict_guard" for row in rows)


def test_wrong_side_conflict_harvest_accepts_breakout_only_conflict_when_bridge_selects_buy() -> None:
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-10T00:21:31+09:00",
                "symbol": "BTCUSD",
                "setup_id": "range_upper_reversal_sell",
                "setup_reason": "shadow_upper_reject_probe_observe",
                "outcome": "wait",
                "action": "",
                "blocked_by": "active_action_conflict_guard",
                "action_none_reason": "wrong_side_sell_pressure",
                "observe_reason": "breakout_conflict_watch",
                "active_action_conflict_detected": True,
                "active_action_conflict_guard_applied": True,
                "active_action_conflict_resolution_state": "WATCH",
                "active_action_conflict_kind": "baseline_sell_vs_up_breakout",
                "active_action_conflict_baseline_action": "SELL",
                "active_action_conflict_directional_action": "",
                "active_action_conflict_directional_state": "",
                "active_action_conflict_directional_owner_family": "",
                "active_action_conflict_up_bias_score": 0.0,
                "active_action_conflict_down_bias_score": 0.0,
                "active_action_conflict_bias_gap": 0.12,
                "active_action_conflict_warning_count": 0,
                "active_action_conflict_reason_summary": "baseline_sell_vs_up_breakout|watch_breakout",
                "entry_candidate_bridge_mode": "active_action_conflict_resolution",
                "entry_candidate_bridge_source": "breakout_candidate",
                "entry_candidate_bridge_action": "BUY",
                "entry_candidate_bridge_effective_baseline_action": "SELL",
                "entry_candidate_bridge_conflict_selected": True,
                "entry_candidate_surface_family": "initial_entry_surface",
                "entry_candidate_surface_state": "initial_break",
            }
        ]
    )

    frame, summary = build_wrong_side_conflict_harvest(entry_decisions, recent_limit=20)

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["symbol"] == "BTCUSD"
    assert row["primary_failure_label"] == "wrong_side_sell_pressure"
    assert row["continuation_failure_label"] == "missed_up_continuation"
    assert row["bridge_action"] == "BUY"
