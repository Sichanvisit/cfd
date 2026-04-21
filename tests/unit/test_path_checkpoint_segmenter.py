import pandas as pd

from backend.services.path_checkpoint_segmenter import (
    assign_checkpoint_context,
    build_checkpoint_distribution,
)
from backend.services.path_leg_runtime import assign_leg_id, extract_leg_runtime_fields


def test_assign_checkpoint_context_keeps_same_checkpoint_within_same_phase() -> None:
    row = {
        "time": "2026-04-10T12:40:43+09:00",
        "symbol": "BTCUSD",
        "outcome": "wait",
        "observe_action": "WAIT",
        "observe_side": "BUY",
        "breakout_candidate_direction": "UP",
    }
    leg_assignment = assign_leg_id("BTCUSD", row, None)
    row.update(extract_leg_runtime_fields(leg_assignment))
    first = assign_checkpoint_context("BTCUSD", row, None)

    row2 = {
        "time": "2026-04-10T12:40:47+09:00",
        "symbol": "BTCUSD",
        "outcome": "wait",
        "observe_action": "WAIT",
        "observe_side": "BUY",
        "breakout_candidate_direction": "UP",
        **extract_leg_runtime_fields(leg_assignment),
    }
    second = assign_checkpoint_context("BTCUSD", row2, first["symbol_state"])

    assert first["checkpoint_type"] == "INITIAL_PUSH"
    assert second["checkpoint_type"] == "INITIAL_PUSH"
    assert second["checkpoint_id"] == first["checkpoint_id"]


def test_assign_checkpoint_context_progresses_pullback_then_reclaim() -> None:
    checkpoint_state = None
    leg_state = None

    first_row = {
        "time": "2026-04-10T12:40:43+09:00",
        "symbol": "XAUUSD",
        "outcome": "wait",
        "observe_action": "WAIT",
        "observe_side": "BUY",
        "breakout_candidate_direction": "UP",
    }
    leg_assignment = assign_leg_id("XAUUSD", first_row, leg_state)
    leg_state = leg_assignment["symbol_state"]
    first_row.update(extract_leg_runtime_fields(leg_assignment))
    cp1 = assign_checkpoint_context("XAUUSD", first_row, checkpoint_state or leg_state)
    checkpoint_state = cp1["symbol_state"]

    pullback_row = {
        "time": "2026-04-10T12:40:47+09:00",
        "symbol": "XAUUSD",
        "outcome": "wait",
        "blocked_by": "upper_edge_observe",
        "observe_action": "SELL",
        "observe_side": "SELL",
        "breakout_candidate_direction": "UP",
        **extract_leg_runtime_fields(leg_assignment),
    }
    cp2 = assign_checkpoint_context("XAUUSD", pullback_row, checkpoint_state)
    checkpoint_state = cp2["symbol_state"]

    reclaim_row = {
        "time": "2026-04-10T12:40:52+09:00",
        "symbol": "XAUUSD",
        "outcome": "wait",
        "blocked_by": "active_action_conflict_guard",
        "observe_action": "SELL",
        "observe_side": "SELL",
        "entry_candidate_bridge_selected": True,
        "entry_candidate_bridge_action": "BUY",
        "breakout_candidate_direction": "UP",
        "active_action_conflict_guard_applied": True,
        **extract_leg_runtime_fields(leg_assignment),
    }
    cp3 = assign_checkpoint_context("XAUUSD", reclaim_row, checkpoint_state)

    assert cp1["checkpoint_type"] == "INITIAL_PUSH"
    assert cp2["checkpoint_type"] == "FIRST_PULLBACK_CHECK"
    assert cp2["checkpoint_id"] != cp1["checkpoint_id"]
    assert cp3["checkpoint_type"] == "RECLAIM_CHECK"
    assert cp3["checkpoint_id"] != cp2["checkpoint_id"]


def test_assign_checkpoint_context_does_not_open_runner_too_early() -> None:
    checkpoint_state = None
    leg_state = None
    last = None
    for idx in range(1, 7):
        row = {
            "time": f"2026-04-10T12:40:{40 + idx:02d}+09:00",
            "symbol": "NAS100",
            "outcome": "skipped",
            "blocked_by": "energy_soft_block",
            "observe_action": "SELL",
            "observe_side": "SELL",
            "breakout_candidate_direction": "UP",
        }
        if leg_state is None:
            leg_assignment = assign_leg_id("NAS100", row, None)
            leg_state = leg_assignment["symbol_state"]
        row.update(extract_leg_runtime_fields(leg_assignment))
        last = assign_checkpoint_context("NAS100", row, checkpoint_state or leg_state)
        checkpoint_state = last["symbol_state"]

    assert last is not None
    assert last["checkpoint_type"] != "RUNNER_CHECK"


def test_assign_checkpoint_context_uses_runner_context_before_raw_runner_threshold() -> None:
    state = {
        "symbol": "BTCUSD",
        "active_leg_id": "BTC_L1",
        "active_checkpoint_id": "BTC_L1_CP001",
        "active_checkpoint_type": "INITIAL_PUSH",
        "active_checkpoint_index": 1,
        "leg_row_count": 8,
        "rows_since_checkpoint_start": 5,
        "last_transition_reason": "seeded",
        "last_seen_at": "2026-04-10T12:40:50+09:00",
    }
    row = {
        "time": "2026-04-10T12:40:55+09:00",
        "symbol": "BTCUSD",
        "leg_id": "BTC_L1",
        "leg_direction": "UP",
        "runner_secured": True,
        "exit_stage_family": "runner",
        "checkpoint_rule_family_hint": "runner_secured_continuation",
        "source": "exit_manage_runner",
    }

    assigned = assign_checkpoint_context("BTCUSD", row, state)

    assert assigned["checkpoint_type"] == "RUNNER_CHECK"
    assert assigned["checkpoint_candidate_reason"] == "explicit_runner_context"
    assert assigned["checkpoint_transition_reason"] == "checkpoint_progression::INITIAL_PUSH_to_RUNNER_CHECK"


def test_assign_checkpoint_context_keeps_protective_late_rows_out_of_runner_bucket() -> None:
    state = {
        "symbol": "NAS100",
        "active_leg_id": "NAS_L1",
        "active_checkpoint_id": "NAS_L1_CP003",
        "active_checkpoint_type": "FIRST_PULLBACK_CHECK",
        "active_checkpoint_index": 3,
        "leg_row_count": 20,
        "rows_since_checkpoint_start": 8,
        "last_transition_reason": "seeded",
        "last_seen_at": "2026-04-10T12:41:20+09:00",
    }
    row = {
        "time": "2026-04-10T12:41:25+09:00",
        "symbol": "NAS100",
        "leg_id": "NAS_L1",
        "leg_direction": "UP",
        "runner_secured": False,
        "exit_stage_family": "protective",
        "checkpoint_rule_family_hint": "open_loss_protective",
        "source": "exit_manage_protective",
    }

    assigned = assign_checkpoint_context("NAS100", row, state)

    assert assigned["checkpoint_type"] == "LATE_TREND_CHECK"
    assert assigned["checkpoint_candidate_reason"] == "contextual_late_management"
    assert assigned["checkpoint_transition_reason"] == "checkpoint_progression::FIRST_PULLBACK_CHECK_to_LATE_TREND_CHECK"


def test_build_checkpoint_distribution_returns_market_family_rows() -> None:
    runtime_status = {
        "updated_at": "2026-04-10T12:45:00+09:00",
        "latest_signal_by_symbol": {
            "BTCUSD": {"symbol": "BTCUSD", "time": "2026-04-10T12:41:04+09:00"},
            "NAS100": {"symbol": "NAS100", "time": "2026-04-10T12:41:02+09:00"},
            "XAUUSD": {"symbol": "XAUUSD", "time": "2026-04-10T12:41:03+09:00"},
        },
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-10T12:40:43+09:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:47+09:00",
                "symbol": "NAS100",
                "outcome": "skipped",
                "blocked_by": "energy_soft_block",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:52+09:00",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "blocked_by": "active_action_conflict_guard",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "entry_candidate_bridge_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "breakout_candidate_direction": "UP",
                "active_action_conflict_guard_applied": True,
            },
        ]
    )

    frame, summary = build_checkpoint_distribution(runtime_status, entry_decisions, recent_limit=20)

    assert set(frame["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}
    assert summary["market_family_row_count"] == 3
    assert summary["checkpoint_count"] >= 3
    assert summary["recommended_next_action"] in {
        "proceed_to_pa3_checkpoint_context_storage",
        "refine_checkpoint_segmentation_before_pa3",
    }
