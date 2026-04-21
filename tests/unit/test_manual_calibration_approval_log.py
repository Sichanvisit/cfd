import pandas as pd

from backend.services.manual_calibration_approval_log import (
    build_manual_calibration_approval_log,
)


def test_approval_log_collects_promotion_and_correction_events() -> None:
    trace_entries = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "promotion_reviewer": "codex",
                "promotion_reviewed_at": "2026-04-07T12:00:00+09:00",
                "promotion_decision_reason": "assistant_review_hold::need_chart_recheck",
                "promotion_followup_needed": "manual_chart_recheck",
                "canonical_decision": "hold_review_needed",
            }
        ]
    )
    correction_runs = pd.DataFrame(
        [
            {
                "correction_run_id": "run1",
                "family_key": "fam1",
                "decision": "hold_for_more_truth",
                "decision_reason": "truth_collection_before_patch",
                "reviewer": "manual_truth_calibration",
                "finished_at": "2026-04-07T12:10:00+09:00",
            }
        ]
    )
    post_promotion_audit = pd.DataFrame()
    shadow_bounded_candidate_approval = pd.DataFrame(
        [
            {
                "stage_event_id": "semantic_shadow_stage::0001",
                "approval_status": "pending_human_review",
                "decision_by": "",
                "decision_at": "",
                "reason_summary": "",
            }
        ]
    )

    approval_log, summary = build_manual_calibration_approval_log(
        trace_entries,
        correction_runs,
        post_promotion_audit,
        shadow_bounded_candidate_approval,
    )

    assert len(approval_log) == 3
    assert set(approval_log["event_type"]) == {
        "promotion_gate_review",
        "correction_loop_accept_reject",
        "shadow_bounded_candidate_review",
    }
    assert summary["followup_open_count"] == 3
    assert summary["event_type_counts"]["promotion_gate_review"] == 1
