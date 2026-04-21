import pandas as pd

from backend.services.shadow_auto_manual_overlap_queue import (
    build_shadow_auto_manual_overlap_queue,
)


def test_build_shadow_auto_manual_overlap_queue_collects_divergent_rows_without_manual_truth() -> None:
    divergence_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-04T14:16:34",
                "symbol": "BTCUSD",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "baseline_action_class": "wait_more",
                "shadow_action_class": "enter_now",
                "effective_target_action_class": "enter_now",
                "action_diverged_flag": True,
                "manual_reference_found": False,
            },
            {
                "bridge_decision_time": "2026-04-04T14:18:00",
                "symbol": "BTCUSD",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "baseline_action_class": "wait_more",
                "shadow_action_class": "enter_now",
                "effective_target_action_class": "enter_now",
                "action_diverged_flag": True,
                "manual_reference_found": False,
            },
        ]
    )

    queue, summary = build_shadow_auto_manual_overlap_queue(divergence_rows, window_minutes=30, limit_per_symbol=4)

    assert len(queue) == 1
    row = queue.iloc[0]
    assert row["dominant_target_label_seed"] == "bad_wait_missed_move"
    assert row["capture_priority"] in {"low", "medium", "high"}
    assert summary["queue_count"] == 1


def test_build_shadow_auto_manual_overlap_queue_skips_rows_with_manual_reference() -> None:
    divergence_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-04T14:16:34",
                "symbol": "BTCUSD",
                "selected_sweep_profile_id": "threshold::0.35::0.35::0.65",
                "baseline_action_class": "wait_more",
                "shadow_action_class": "enter_now",
                "effective_target_action_class": "enter_now",
                "action_diverged_flag": True,
                "manual_reference_found": True,
            }
        ]
    )

    queue, summary = build_shadow_auto_manual_overlap_queue(divergence_rows)

    assert queue.empty
    assert summary["queue_count"] == 0
