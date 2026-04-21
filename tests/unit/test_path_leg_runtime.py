import pandas as pd

from backend.services.path_leg_runtime import (
    assign_leg_id,
    build_path_leg_snapshot,
    close_active_leg,
)


def test_assign_leg_id_keeps_consecutive_rows_on_same_leg() -> None:
    row1 = {
        "time": "2026-04-10T12:40:43+09:00",
        "symbol": "BTCUSD",
        "outcome": "wait",
        "blocked_by": "outer_band_guard",
        "observe_action": "WAIT",
        "observe_side": "BUY",
        "breakout_candidate_direction": "UP",
    }
    first = assign_leg_id("BTCUSD", row1, None)

    row2 = {
        "time": "2026-04-10T12:40:48+09:00",
        "symbol": "BTCUSD",
        "outcome": "wait",
        "blocked_by": "outer_band_guard",
        "observe_action": "WAIT",
        "observe_side": "BUY",
        "breakout_candidate_direction": "UP",
    }
    second = assign_leg_id("BTCUSD", row2, first["symbol_state"])

    assert first["leg_id"]
    assert second["leg_id"] == first["leg_id"]
    assert second["leg_direction"] == "UP"
    assert second["leg_transition_reason"] == "active_leg_continuation"


def test_close_active_leg_then_new_impulse_opens_new_leg() -> None:
    opened = assign_leg_id(
        "XAUUSD",
        {
            "time": "2026-04-10T12:40:43+09:00",
            "symbol": "XAUUSD",
            "outcome": "wait",
            "blocked_by": "active_action_conflict_guard",
            "entry_candidate_bridge_selected": True,
            "entry_candidate_bridge_action": "BUY",
            "breakout_candidate_direction": "UP",
        },
        None,
    )
    closed = close_active_leg(
        "XAUUSD",
        opened["symbol_state"],
        reason="full_exit",
        event_time="2026-04-10T12:41:00+09:00",
    )
    reopened = assign_leg_id(
        "XAUUSD",
        {
            "time": "2026-04-10T12:41:05+09:00",
            "symbol": "XAUUSD",
            "outcome": "wait",
            "blocked_by": "",
            "observe_action": "BUY",
            "observe_side": "BUY",
            "breakout_candidate_direction": "UP",
        },
        closed["symbol_state"],
    )

    assert closed["leg_state"] == "CLOSED"
    assert reopened["leg_id"]
    assert reopened["leg_id"] != opened["leg_id"]
    assert reopened["leg_direction"] == "UP"


def test_assign_leg_id_does_not_split_shallow_rebuild_when_breakout_direction_stays_up() -> None:
    first = assign_leg_id(
        "NAS100",
        {
            "time": "2026-04-10T12:40:43+09:00",
            "symbol": "NAS100",
            "outcome": "wait",
            "blocked_by": "probe_promotion_gate",
            "observe_action": "SELL",
            "observe_side": "SELL",
            "breakout_candidate_direction": "UP",
        },
        None,
    )
    second = assign_leg_id(
        "NAS100",
        {
            "time": "2026-04-10T12:40:47+09:00",
            "symbol": "NAS100",
            "outcome": "wait",
            "blocked_by": "probe_promotion_gate",
            "observe_action": "SELL",
            "observe_side": "SELL",
            "breakout_candidate_direction": "UP",
        },
        first["symbol_state"],
    )

    assert first["leg_direction"] == "UP"
    assert second["leg_id"] == first["leg_id"]
    assert second["leg_transition_reason"] == "active_leg_continuation"


def test_assign_leg_id_opens_new_leg_on_selected_bridge_flip_without_entered_outcome() -> None:
    first = assign_leg_id(
        "BTCUSD",
        {
            "time": "2026-04-10T18:00:00+09:00",
            "symbol": "BTCUSD",
            "outcome": "wait",
            "blocked_by": "active_action_conflict_guard",
            "entry_candidate_bridge_selected": True,
            "entry_candidate_bridge_action": "BUY",
            "breakout_candidate_direction": "UP",
        },
        None,
    )
    second = assign_leg_id(
        "BTCUSD",
        {
            "time": "2026-04-10T18:00:07+09:00",
            "symbol": "BTCUSD",
            "outcome": "wait",
            "blocked_by": "active_action_conflict_guard",
            "entry_candidate_bridge_selected": True,
            "entry_candidate_bridge_action": "SELL",
            "breakout_candidate_direction": "DOWN",
        },
        first["symbol_state"],
    )

    assert first["leg_id"]
    assert second["leg_id"]
    assert second["leg_id"] != first["leg_id"]
    assert second["leg_direction"] == "DOWN"
    assert second["leg_transition_reason"].startswith("direction_flip_entered_new_leg::")


def test_build_path_leg_snapshot_tracks_market_family_assignment_coverage() -> None:
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
                "blocked_by": "outer_band_guard",
                "observe_action": "WAIT",
                "observe_side": "BUY",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:43+09:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "blocked_by": "probe_promotion_gate",
                "observe_action": "SELL",
                "observe_side": "SELL",
                "breakout_candidate_direction": "UP",
            },
            {
                "time": "2026-04-10T12:40:43+09:00",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "blocked_by": "active_action_conflict_guard",
                "observe_action": "WAIT",
                "observe_side": "SELL",
                "entry_candidate_bridge_selected": True,
                "entry_candidate_bridge_action": "BUY",
                "breakout_candidate_direction": "UP",
            },
        ]
    )

    frame, summary = build_path_leg_snapshot(runtime_status, entry_decisions, recent_limit=20)

    assert set(frame["symbol"]) == {"BTCUSD", "NAS100", "XAUUSD"}
    assert summary["market_family_row_count"] == 3
    assert summary["missing_leg_row_count"] == 0
    assert summary["active_leg_count"] == 3
    assert summary["recommended_next_action"] == "proceed_to_pa2_checkpoint_segmentation"
