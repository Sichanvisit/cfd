import pandas as pd

from backend.services.manual_current_rich_wrong_failed_wait_review_queue import (
    build_current_rich_wrong_failed_wait_review_queue,
)


def test_review_queue_prioritizes_btc_and_nas_failed_wait_proxies() -> None:
    seeds = pd.DataFrame(
        [
            {
                "episode_id": "btc_seed_1",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T18:30:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "barrier_main_label_hint": "avoided_loss",
                "wait_outcome_reason_summary": "hard_block|buy_barrier",
                "annotation_note": "family=block_bias; wait_decision=wait_soft_helper_block",
            },
            {
                "episode_id": "nas_seed_1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T19:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "barrier_main_label_hint": "avoided_loss",
                "wait_outcome_reason_summary": "hard_block|middle_chop_barrier",
                "annotation_note": "family=block_bias; wait_decision=wait_soft_helper_block",
            },
            {
                "episode_id": "xau_seed_1",
                "symbol": "XAUUSD",
                "anchor_time": "2026-04-06T19:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "barrier_main_label_hint": "correct_wait",
                "wait_outcome_reason_summary": "wait_block|unstable",
                "annotation_note": "family=wait_bias; wait_decision=wait_soft_helper_block",
            },
        ]
    )
    audit = pd.DataFrame(
        [
            {"symbol": "BTCUSD"},
            {"symbol": "NAS100"},
        ]
    )

    queue, summary = build_current_rich_wrong_failed_wait_review_queue(seeds, audit)

    assert len(queue) == 2
    assert summary["row_count"] == 2
    assert summary["priority_counts"] == {"p1": 2}
    assert summary["pattern_counts"] == {
        "btc_helper_wait_failed_wait_check": 1,
        "nas_failed_wait_shift_proxy": 1,
    }


def test_review_queue_includes_btc_control_case() -> None:
    seeds = pd.DataFrame(
        [
            {
                "episode_id": "btc_seed_control",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T22:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "barrier_main_label_hint": "correct_wait",
                "wait_outcome_reason_summary": "relief_watch|balanced",
                "annotation_note": "family=relief_watch; wait_decision=wait_soft_helper_block",
            }
        ]
    )
    audit = pd.DataFrame([{"symbol": "BTCUSD"}])

    queue, summary = build_current_rich_wrong_failed_wait_review_queue(seeds, audit)

    assert len(queue) == 1
    row = queue.iloc[0].to_dict()
    assert row["target_followup_pattern"] == "btc_helper_wait_control"
    assert row["review_priority"] == "p2"
    assert summary["target_symbols"] == ["BTCUSD"]
