import pandas as pd

from backend.services.manual_vs_heuristic_current_rich_queue import (
    build_manual_vs_heuristic_current_rich_queue,
)


def test_manual_vs_heuristic_current_rich_queue_builds_recent_windows_after_manual_max() -> None:
    manual = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T09:24:00+09:00",
            }
        ]
    )
    heuristics = pd.DataFrame(
        [
            {
                "symbol": "NAS100",
                "heuristic_source_kind": "current",
                "heuristic_time": pd.Timestamp("2026-04-06 14:30:00"),
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_candidate_recommended_family": "wait_bias",
                "barrier_action_hint_reason_summary": "wait_for_pullback",
                "entry_wait_decision": "prefer_wait",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_forecast_family": "",
                "heuristic_belief_family": "",
                "core_reason": "core_wait",
            },
            {
                "symbol": "NAS100",
                "heuristic_source_kind": "current",
                "heuristic_time": pd.Timestamp("2026-04-06 14:41:00"),
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_candidate_recommended_family": "wait_bias",
                "barrier_action_hint_reason_summary": "wait_for_pullback",
                "entry_wait_decision": "prefer_wait",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_forecast_family": "",
                "heuristic_belief_family": "",
                "core_reason": "core_wait",
            },
            {
                "symbol": "BTCUSD",
                "heuristic_source_kind": "legacy",
                "heuristic_time": pd.Timestamp("2026-04-06 14:35:00"),
                "barrier_candidate_supporting_label": "avoided_loss",
                "barrier_candidate_recommended_family": "block_bias",
                "barrier_action_hint_reason_summary": "legacy",
                "entry_wait_decision": "skip",
                "heuristic_barrier_main_label": "avoided_loss",
                "heuristic_wait_family": "neutral_wait",
                "heuristic_forecast_family": "",
                "heuristic_belief_family": "",
                "core_reason": "legacy_core",
            },
        ]
    )

    queue, summary = build_manual_vs_heuristic_current_rich_queue(
        manual,
        heuristics,
        window_minutes=30,
        limit_per_symbol=4,
    )

    assert len(queue) == 1
    row = queue.iloc[0].to_dict()
    assert row["symbol"] == "NAS100"
    assert row["barrier_label_top"] == "correct_wait"
    assert row["recommended_family_top"] == "wait_bias"
    assert row["wait_decision_top"] == "prefer_wait"
    assert summary["queue_count"] == 1
    assert summary["symbol_counts"] == {"NAS100": 1}


def test_manual_vs_heuristic_current_rich_queue_returns_empty_when_no_current_overlap() -> None:
    manual = pd.DataFrame([{"anchor_time": "2026-04-06T19:50:00+09:00"}])
    heuristics = pd.DataFrame(
        [
            {
                "symbol": "NAS100",
                "heuristic_source_kind": "current",
                "heuristic_time": pd.Timestamp("2026-04-06 19:40:00"),
                "barrier_candidate_supporting_label": "correct_wait",
                "barrier_candidate_recommended_family": "wait_bias",
                "barrier_action_hint_reason_summary": "wait_for_pullback",
                "entry_wait_decision": "prefer_wait",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_forecast_family": "",
                "heuristic_belief_family": "",
                "core_reason": "core_wait",
            }
        ]
    )

    queue, summary = build_manual_vs_heuristic_current_rich_queue(manual, heuristics)

    assert queue.empty
    assert summary["queue_count"] == 0
