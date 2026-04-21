import pandas as pd

from backend.services.manual_current_rich_promotion_discipline import (
    build_manual_current_rich_promotion_discipline,
)


def test_promotion_discipline_marks_reviewed_rows_as_validated() -> None:
    gate = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_teacher_confidence": "low",
                "ideal_entry_time": "",
                "ideal_exit_time": "",
                "canonical_action": "hold_review_needed",
                "promotion_decision_reason": "assistant_review_hold::mixed_proxy_evidence",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T12:00:00+09:00",
                "promotion_blockers": "manual_chart_recheck_still_required_before_canonical_merge",
                "calibration_value_bucket": "medium",
                "episode_detail_status": "insufficient",
            },
            {
                "episode_id": "ep2",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-07T03:30:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_teacher_confidence": "medium",
                "ideal_entry_time": "2026-04-07T03:35:00+09:00",
                "ideal_exit_time": "2026-04-07T03:40:00+09:00",
                "canonical_action": "promote_to_canonical",
                "promotion_decision_reason": "review_complete::promote",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T12:30:00+09:00",
                "promotion_blockers": "",
                "calibration_value_bucket": "high",
                "episode_detail_status": "complete",
            },
        ]
    )
    merge_entries = pd.DataFrame(
        [
            {
                "episode_id": "ep2",
                "promotion_decision_type": "promote_to_canonical",
                "promotion_reason_code": "review_complete",
                "promotion_evidence_summary": "calibration=high|detail=complete",
                "canonical_merged_at": "2026-04-07T13:00:00+09:00",
                "canonical_merged_by": "codex",
                "canonical_merge_batch_id": "merge_001",
                "canonical_merge_reason": "approved_after_review",
            }
        ]
    )

    discipline, summary = build_manual_current_rich_promotion_discipline(
        gate,
        merge_entries=merge_entries,
    )

    assert len(discipline) == 2
    ep1 = discipline[discipline["episode_id"] == "ep1"].iloc[0]
    ep2 = discipline[discipline["episode_id"] == "ep2"].iloc[0]
    assert ep1["promotion_level"] == "validated"
    assert ep1["merge_status"] == "validated_not_merged"
    assert ep2["promotion_level"] == "canonical"
    assert ep2["canonical_merge_batch_id"] == "merge_001"
    assert summary["promotion_level_counts"]["validated"] == 1
    assert summary["promotion_level_counts"]["canonical"] == 1
