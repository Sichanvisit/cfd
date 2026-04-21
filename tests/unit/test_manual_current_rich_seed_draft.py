import pandas as pd

from backend.services.manual_current_rich_seed_draft import (
    build_manual_current_rich_seed_draft,
)


def test_manual_current_rich_seed_draft_builds_review_needed_rows() -> None:
    queue = pd.DataFrame(
        [
            {
                "queue_id": "current_rich::XAUUSD::2026-04-06T18:30:00",
                "symbol": "XAUUSD",
                "window_start": "2026-04-06T18:30:00",
                "window_end": "2026-04-06T19:00:00",
                "barrier_label_top": "correct_wait",
                "recommended_family_top": "relief_watch",
                "wait_decision_top": "skip",
                "reason_top": "relief_watch|balanced",
            },
            {
                "queue_id": "current_rich::NAS100::2026-04-06T17:30:00",
                "symbol": "NAS100",
                "window_start": "2026-04-06T17:30:00",
                "window_end": "2026-04-06T18:00:00",
                "barrier_label_top": "avoided_loss",
                "recommended_family_top": "block_bias",
                "wait_decision_top": "wait_soft_helper_block",
                "reason_top": "hard_block|sell_barrier",
            },
        ]
    )

    draft = build_manual_current_rich_seed_draft(queue)

    assert len(draft) == 2
    assert draft.iloc[0]["annotation_source"] == "assistant_current_rich_seed"
    assert draft.iloc[0]["review_status"] == "needs_manual_recheck"
    assert draft.iloc[0]["manual_wait_teacher_label"] == "good_wait_protective_exit"
    assert draft.iloc[1]["manual_wait_teacher_label"] == "bad_wait_missed_move"
    assert draft.iloc[1]["anchor_side"] == "SELL"


def test_manual_current_rich_seed_draft_applies_review_overrides() -> None:
    queue = pd.DataFrame(
        [
            {
                "queue_id": "current_rich::BTCUSD::2026-04-07T03:00:00",
                "symbol": "BTCUSD",
                "window_start": "2026-04-07T03:00:00",
                "window_end": "2026-04-07T03:30:00",
                "barrier_label_top": "correct_wait",
                "recommended_family_top": "wait_bias",
                "wait_decision_top": "wait_soft_helper_block",
                "reason_top": "wait_block|unstable",
            }
        ]
    )
    overrides = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "anchor_side": "SELL",
                "anchor_price": 69578.23,
                "ideal_entry_time": "2026-04-07T04:30:00+09:00",
                "ideal_entry_price": 70074.9,
                "ideal_exit_time": "2026-04-07T04:45:00+09:00",
                "ideal_exit_price": 69769.12,
                "review_status": "reviewed_for_promotion",
                "manual_wait_teacher_confidence": "medium",
                "manual_teacher_confidence": "medium",
            }
        ]
    )

    draft = build_manual_current_rich_seed_draft(queue, review_overrides=overrides)

    assert len(draft) == 1
    assert draft.iloc[0]["anchor_side"] == "SELL"
    assert float(draft.iloc[0]["anchor_price"]) == 69578.23
    assert draft.iloc[0]["ideal_entry_time"] == "2026-04-07T04:30:00+09:00"
    assert draft.iloc[0]["ideal_exit_time"] == "2026-04-07T04:45:00+09:00"
    assert draft.iloc[0]["review_status"] == "reviewed_for_promotion"
    assert draft.iloc[0]["manual_teacher_confidence"] == "medium"
