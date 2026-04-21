import pandas as pd

from backend.services.shadow_auto_manual_overlap_seed_draft import (
    build_shadow_auto_manual_overlap_seed_draft,
)


def test_build_shadow_auto_manual_overlap_seed_draft_creates_review_needed_rows() -> None:
    queue = pd.DataFrame(
        [
            {
                "queue_id": "shadow_manual_overlap::BTCUSD::2026-04-04T14:00:00::threshold::0.35",
                "selected_sweep_profile_id": "threshold::0.35",
                "symbol": "BTCUSD",
                "window_start": "2026-04-04T14:00:00",
                "window_end": "2026-04-04T14:30:00",
                "dominant_baseline_action": "wait_more",
                "dominant_shadow_action": "enter_now",
                "dominant_target_action": "enter_now",
                "dominant_target_label_seed": "bad_wait_missed_move",
            }
        ]
    )

    draft = build_shadow_auto_manual_overlap_seed_draft(queue)

    assert len(draft) == 1
    row = draft.iloc[0]
    assert row["manual_wait_teacher_label"] == "bad_wait_missed_move"
    assert row["annotation_source"] == "assistant_shadow_overlap_seed"
    assert row["review_status"] == "needs_manual_recheck"


def test_build_shadow_auto_manual_overlap_seed_draft_merges_review_entries() -> None:
    queue = pd.DataFrame(
        [
            {
                "queue_id": "shadow_manual_overlap::BTCUSD::2026-04-04T14:00:00::threshold::0.35",
                "selected_sweep_profile_id": "threshold::0.35",
                "symbol": "BTCUSD",
                "window_start": "2026-04-04T14:00:00",
                "window_end": "2026-04-04T14:30:00",
                "dominant_baseline_action": "wait_more",
                "dominant_shadow_action": "enter_now",
                "dominant_target_action": "enter_now",
                "dominant_target_label_seed": "bad_wait_missed_move",
            }
        ]
    )
    review_entries = pd.DataFrame(
        [
            {
                "episode_id": "shadow_manual_seed::BTCUSD::2026-04-04T14:00:00::threshold::0.35",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_confidence": "medium",
                "manual_teacher_confidence": "medium",
                "review_status": "accepted_coarse",
                "annotation_source": "assistant_shadow_overlap_reviewed",
                "annotation_note": "reviewed",
            }
        ]
    )

    draft = build_shadow_auto_manual_overlap_seed_draft(queue, review_entries)

    row = draft.iloc[0]
    assert row["manual_wait_teacher_label"] == "good_wait_better_entry"
    assert row["review_status"] == "accepted_coarse"
    assert row["annotation_source"] == "assistant_shadow_overlap_reviewed"
