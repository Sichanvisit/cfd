import json

import pandas as pd

from backend.services.surface_time_axis_contract import build_surface_time_axis_contract


def test_surface_time_axis_contract_materializes_expected_fields_for_surfaces() -> None:
    labels = pd.DataFrame(
        [
            {
                "annotation_id": "initial_001",
                "episode_id": "initial_001",
                "symbol": "NAS100",
                "market_family": "NAS100",
                "surface_label_family": "initial_entry_surface",
                "surface_label_state": "initial_break",
                "surface_action_bias": "ENTER_NOW",
            },
            {
                "annotation_id": "follow_001",
                "episode_id": "follow_001",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "pullback_resume",
                "surface_action_bias": "PROBE_ENTRY",
                "chart_context": "pullback resume",
                "barrier_main_label_hint": "wait_then_enter",
            },
            {
                "annotation_id": "protect_001",
                "episode_id": "protect_001",
                "symbol": "BTCUSD",
                "market_family": "BTCUSD",
                "surface_label_family": "protective_exit_surface",
                "surface_label_state": "protect_exit",
                "surface_action_bias": "EXIT_PROTECT",
            },
        ]
    )
    surface_spec = pd.DataFrame(
        [
            {
                "surface_name": "initial_entry_surface",
                "time_axis_fields": json.dumps(["bars_in_state", "time_since_last_relief"]),
            },
            {
                "surface_name": "follow_through_surface",
                "time_axis_fields": json.dumps(["time_since_breakout", "bars_in_state", "momentum_decay"]),
            },
            {
                "surface_name": "protective_exit_surface",
                "time_axis_fields": json.dumps(["time_since_entry", "bars_in_state", "momentum_decay"]),
            },
        ]
    )
    manual_wait = pd.DataFrame(
        [
            {
                "annotation_id": "initial_001",
                "episode_id": "initial_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "ideal_entry_time": "2026-04-08T06:56:00+09:00",
                "ideal_exit_time": "2026-04-08T07:10:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_confidence": "medium",
                "review_status": "accepted_coarse",
                "annotation_source": "chart_annotated",
            },
            {
                "annotation_id": "follow_001",
                "episode_id": "follow_001",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "anchor_time": "2026-04-09T00:20:00+09:00",
                "ideal_entry_time": "2026-04-09T00:24:00+09:00",
                "ideal_exit_time": "2026-04-09T00:36:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "review_status": "accepted_coarse",
                "annotation_source": "chart_annotated",
            },
            {
                "annotation_id": "protect_001",
                "episode_id": "protect_001",
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "anchor_time": "2026-04-08T10:00:00+09:00",
                "ideal_entry_time": "2026-04-08T10:02:00+09:00",
                "ideal_exit_time": "2026-04-08T10:09:00+09:00",
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "manual_wait_teacher_confidence": "medium",
                "review_status": "accepted_coarse",
                "annotation_source": "chart_annotated",
            },
        ]
    )

    frame, summary = build_surface_time_axis_contract(
        labels,
        surface_spec,
        manual_wait,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert summary["row_count"] == 3
    assert "follow_through_surface" in summary["surface_label_family_counts"]
    assert "entry_exit_direct" in summary["time_axis_quality_counts"]

    initial_row = frame.loc[frame["annotation_id"] == "initial_001"].iloc[0]
    assert initial_row["time_since_breakout_minutes"] == 6.0
    assert initial_row["bars_in_state"] == 6.0
    assert initial_row["time_axis_phase"] == "late_initial"
    assert "time_since_last_relief" in initial_row["expected_time_axis_fields"]

    follow_row = frame.loc[frame["annotation_id"] == "follow_001"].iloc[0]
    assert follow_row["time_since_breakout_minutes"] == 4.0
    assert follow_row["bars_since_probe_activation"] == 4.0
    assert follow_row["time_since_last_relief_minutes"] == 4.0
    assert follow_row["time_axis_phase"] == "continuation_window"

    protect_row = frame.loc[frame["annotation_id"] == "protect_001"].iloc[0]
    assert protect_row["time_since_entry_minutes"] == 7.0
    assert protect_row["bars_in_state"] == 7.0
    assert protect_row["time_axis_phase"] == "protect_active"


def test_surface_time_axis_contract_falls_back_to_anchor_only_when_entry_exit_missing() -> None:
    labels = pd.DataFrame(
        [
            {
                "annotation_id": "anchor_only_001",
                "episode_id": "anchor_only_001",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_label_family": "initial_entry_surface",
                "surface_label_state": "observe_filter",
                "surface_action_bias": "WAIT_MORE",
            }
        ]
    )
    source = pd.DataFrame(
        [
            {
                "annotation_id": "anchor_only_001",
                "episode_id": "anchor_only_001",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "anchor_time": "2026-04-09T00:00:00+09:00",
                "ideal_entry_time": "",
                "ideal_exit_time": "",
                "manual_wait_teacher_label": "neutral_wait_small_value",
                "manual_wait_teacher_confidence": "low",
                "review_status": "needs_manual_recheck",
                "annotation_source": "assistant_breakout_overlap_seed",
            }
        ]
    )

    frame, summary = build_surface_time_axis_contract(
        labels,
        pd.DataFrame(),
        source,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["time_axis_quality"] == "anchor_only"
    assert row["time_since_breakout_minutes"] == 0.0
    assert row["time_since_entry_minutes"] == 0.0
    assert row["bars_in_state"] == 0.0
