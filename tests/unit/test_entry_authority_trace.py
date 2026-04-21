import pandas as pd

from backend.services.entry_authority_trace import (
    build_entry_authority_fields,
    build_entry_authority_trace,
)


def test_build_entry_authority_fields_marks_baseline_no_action() -> None:
    fields = build_entry_authority_fields(
        {
            "outcome": "skipped",
            "action": "",
            "core_reason": "core_not_passed",
            "action_none_reason": "core_not_passed",
            "blocked_by": "",
            "semantic_live_threshold_applied": 0,
        }
    )

    assert fields["entry_authority_owner"] == "baseline_score"
    assert fields["entry_candidate_action_source"] == "none"
    assert fields["entry_candidate_rejected_by"] == "baseline_no_action"
    assert fields["entry_authority_stage"] == "baseline_action_selection"


def test_build_entry_authority_fields_marks_utility_gate_veto() -> None:
    fields = build_entry_authority_fields(
        {
            "outcome": "skipped",
            "action": "BUY",
            "core_reason": "breakout_retest_buy",
            "blocked_by": "utility_u_below_floor",
            "u_pass": 0,
            "semantic_live_threshold_applied": 0,
        }
    )

    assert fields["entry_authority_owner"] == "utility_gate"
    assert fields["entry_candidate_action_source"] == "baseline_score"
    assert fields["entry_candidate_rejected_by"] == "utility_gate"
    assert fields["entry_authority_stage"] == "utility_gate"


def test_build_entry_authority_fields_marks_semantic_threshold_veto() -> None:
    fields = build_entry_authority_fields(
        {
            "outcome": "skipped",
            "action": "SELL",
            "core_reason": "breakout_retest_sell",
            "blocked_by": "dynamic_threshold_not_met",
            "semantic_live_threshold_applied": 1,
        }
    )

    assert fields["entry_authority_owner"] == "semantic_threshold_guard"
    assert fields["entry_candidate_rejected_by"] == "semantic_threshold_guard"
    assert fields["entry_authority_stage"] == "score_threshold_gate"
    assert fields["entry_authority_threshold_owner"] == "semantic_threshold_guard"


def test_build_entry_authority_fields_marks_active_action_conflict_guard() -> None:
    fields = build_entry_authority_fields(
        {
            "outcome": "wait",
            "action": "",
            "blocked_by": "active_action_conflict_guard",
            "action_none_reason": "wrong_side_sell_pressure",
            "active_action_conflict_guard_applied": True,
            "semantic_live_threshold_applied": 0,
        }
    )

    assert fields["entry_authority_owner"] == "active_action_conflict_guard"
    assert fields["entry_candidate_rejected_by"] == "active_action_conflict_guard"
    assert fields["entry_authority_stage"] == "active_action_conflict_guard"


def test_entry_authority_trace_summary_recommends_ai2_for_baseline_no_action() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T20:00:00+09:00",
        "semantic_live_config": {
            "mode": "log_only",
            "shadow_runtime_state": "active",
        },
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T20:00:01",
                "symbol": "BTCUSD",
                "outcome": "skipped",
                "action": "",
                "blocked_by": "",
                "action_none_reason": "core_not_passed",
                "core_reason": "core_not_passed",
            },
            {
                "time": "2026-04-08T19:59:01",
                "symbol": "NAS100",
                "outcome": "skipped",
                "action": "BUY",
                "blocked_by": "utility_u_below_floor",
                "u_pass": 0,
                "core_reason": "breakout_retest_buy",
            },
            {
                "time": "2026-04-08T19:58:01",
                "symbol": "XAUUSD",
                "outcome": "entered",
                "action": "SELL",
                "blocked_by": "",
                "core_reason": "breakout_retest_sell",
            },
        ]
    )

    frame, summary = build_entry_authority_trace(runtime_status, entry_decisions, recent_limit=20)

    row = frame.iloc[0]
    assert int(row["baseline_no_action_count"]) == 1
    assert int(row["utility_gate_veto_count"]) == 1
    assert int(row["entered_count"]) == 1
    assert row["recommended_next_action"] == "implement_ai2_baseline_no_action_candidate_bridge"
    assert summary["rollout_mode"] == "log_only"


def test_entry_authority_trace_summary_counts_active_action_conflict_guard() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T22:00:00+09:00",
        "semantic_live_config": {
            "mode": "log_only",
            "shadow_runtime_state": "active",
        },
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T22:00:01",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "action": "",
                "blocked_by": "active_action_conflict_guard",
                "action_none_reason": "wrong_side_sell_pressure",
                "active_action_conflict_guard_applied": True,
            }
        ]
    )

    frame, summary = build_entry_authority_trace(runtime_status, entry_decisions, recent_limit=20)

    row = frame.iloc[0]
    assert int(row["active_action_conflict_guard_count"]) == 1
    assert row["recommended_next_action"] == "validate_active_action_conflict_guard_precision"
    assert summary["recent_row_count"] == 1


def test_build_entry_authority_fields_uses_bridge_candidate_when_conflict_guard_downgrades() -> None:
    fields = build_entry_authority_fields(
        {
            "outcome": "wait",
            "action": "",
            "blocked_by": "active_action_conflict_guard",
            "action_none_reason": "wrong_side_sell_pressure",
            "active_action_conflict_guard_applied": True,
            "entry_candidate_bridge_selected": True,
            "entry_candidate_bridge_source": "countertrend_candidate",
            "entry_candidate_bridge_action": "BUY",
            "semantic_live_threshold_applied": 0,
        }
    )

    assert fields["entry_authority_owner"] == "active_action_conflict_guard"
    assert fields["entry_candidate_action_source"] == "countertrend_candidate"
    assert fields["entry_candidate_action"] == "BUY"
