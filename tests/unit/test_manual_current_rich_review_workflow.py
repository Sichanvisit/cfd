import pandas as pd

from backend.services.manual_current_rich_review_workflow import (
    build_manual_current_rich_review_workflow,
)


def test_manual_current_rich_review_workflow_builds_batches_and_trace_status() -> None:
    gate = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "queue_id": "current_rich::NAS100::2026-04-07T03:00:00",
                "symbol": "NAS100",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_teacher_confidence": "low",
                "promotion_readiness": "review_needed",
                "review_priority_tier": "review_needed_high_priority",
                "capture_priority": "low",
                "row_count": 55,
                "unique_signal_minutes": 1,
                "calibration_value_bucket": "low",
                "episode_detail_status": "insufficient",
                "promotion_decision_reason": "followup_hold::needs_manual_chart_recheck",
                "promotion_blocking_reason": "followup_review_needs_chart_recheck",
                "promotion_followup_needed": "manual_chart_recheck",
                "promotion_reviewer": "",
                "promotion_reviewed_at": "",
                "recommended_next_action": "manual_recheck_then_decide",
            },
            {
                "episode_id": "manual_seed::XAUUSD::2026-04-07T03:00:00",
                "queue_id": "current_rich::XAUUSD::2026-04-07T03:00:00",
                "symbol": "XAUUSD",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_teacher_confidence": "high",
                "promotion_readiness": "ready",
                "review_priority_tier": "ready_high",
                "capture_priority": "high",
                "row_count": 220,
                "unique_signal_minutes": 4,
                "calibration_value_bucket": "high",
                "episode_detail_status": "complete",
                "promotion_decision_reason": "ready_high_value_reviewed",
                "promotion_blocking_reason": "",
                "promotion_followup_needed": "promotion_signoff",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T10:00:00+09:00",
                "recommended_next_action": "promote_to_canonical",
            },
        ]
    )

    workflow, summary = build_manual_current_rich_review_workflow(gate)

    assert len(workflow) == 2
    assert workflow.iloc[0]["review_batch_id"] == "promotion_signoff_p1"
    assert workflow.iloc[0]["review_trace_status"] == "review_traced"
    pending = workflow[workflow["symbol"] == "NAS100"].iloc[0]
    assert pending["review_batch_id"] == "review_batch_p1"
    assert pending["suggested_review_focus"] == "chart_recheck"
    assert pending["required_trace_fields"] == (
        "promotion_reviewer|promotion_reviewed_at|promotion_decision_reason|promotion_followup_needed|promotion_blocking_reason"
    )
    assert summary["next_review_batch_id"] == "promotion_signoff_p1"
    assert summary["trace_status_counts"]["trace_missing"] == 1
