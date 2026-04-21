import pandas as pd

from backend.services.manual_current_rich_review_trace import (
    build_manual_current_rich_review_trace,
)


def test_manual_current_rich_review_trace_targets_p1_batch() -> None:
    workflow = pd.DataFrame(
        [
            {
                "review_batch_id": "review_batch_p1",
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "symbol": "NAS100",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "review_priority_tier": "review_needed_high_priority",
                "suggested_review_focus": "chart_recheck",
                "suggested_review_action": "review_chart_and_confirm_hold_or_promote",
                "required_trace_fields": "promotion_reviewer|promotion_reviewed_at",
                "review_trace_status": "trace_missing",
                "promotion_reviewer": "",
                "promotion_reviewed_at": "",
                "promotion_decision_reason": "followup_hold::needs_manual_chart_recheck",
                "promotion_blocking_reason": "followup_review_needs_chart_recheck",
                "promotion_followup_needed": "manual_chart_recheck",
            },
            {
                "review_batch_id": "review_batch_p3",
                "episode_id": "manual_seed::BTCUSD::2026-04-07T03:00:00",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "review_priority_tier": "review_needed_low_signal",
                "suggested_review_focus": "episode_detail_completion",
                "suggested_review_action": "fill_entry_exit_coordinates_before_decision",
                "required_trace_fields": "promotion_reviewer|promotion_reviewed_at",
                "review_trace_status": "trace_missing",
                "promotion_reviewer": "",
                "promotion_reviewed_at": "",
                "promotion_decision_reason": "manual_review_pending",
                "promotion_blocking_reason": "manual_review_pending",
                "promotion_followup_needed": "fill_episode_coordinates",
            },
        ]
    )

    trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "manual_seed::NAS100::2026-04-07T03:00:00",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T12:00:00+09:00",
                "promotion_decision_reason": "assistant_review_hold",
                "promotion_blocking_reason": "manual_chart_recheck_still_required_before_canonical_merge",
                "promotion_followup_needed": "manual_chart_recheck",
                "canonical_decision": "hold_review_needed",
            }
        ]
    )

    trace, summary = build_manual_current_rich_review_trace(workflow, trace_entries=trace_entries)

    assert len(trace) == 1
    assert trace.iloc[0]["review_batch_id"] == "review_batch_p1"
    assert trace.iloc[0]["trace_status"] == "trace_filled"
    assert trace.iloc[0]["promotion_reviewer"] == "codex"
    assert trace.iloc[0]["canonical_decision"] == "hold_review_needed"
    assert summary["target_batch_id"] == "review_batch_p1"
