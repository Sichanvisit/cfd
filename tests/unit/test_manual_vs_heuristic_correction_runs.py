import pandas as pd

from backend.services.manual_vs_heuristic_correction_runs import (
    build_manual_vs_heuristic_correction_candidates,
    build_manual_vs_heuristic_correction_runs,
)


def test_manual_vs_heuristic_correction_candidates_select_ready_patch_family() -> None:
    ranking = pd.DataFrame(
        [
            {
                "family_id": "fam_ready",
                "miss_type": "false_avoided_loss",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "neutral_wait",
                "heuristic_barrier_main_label": "avoided_loss",
                "case_count": 4,
                "correction_worthy_case_count": 2,
                "freeze_worthy_case_count": 0,
                "hold_for_more_truth_case_count": 0,
                "ready_case_count": 2,
                "correction_priority_tier": "P1",
                "family_disposition": "correction_candidate",
                "recommended_next_action": "edit_rule_now",
            },
            {
                "family_id": "fam_hold",
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "failed_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_barrier_main_label": "correct_wait",
                "case_count": 3,
                "correction_worthy_case_count": 0,
                "freeze_worthy_case_count": 1,
                "hold_for_more_truth_case_count": 3,
                "ready_case_count": 0,
                "correction_priority_tier": "P3",
                "family_disposition": "collect_more_truth",
                "recommended_next_action": "collect_current_rich_truth",
            },
        ]
    )
    patch_draft = pd.DataFrame(
        [
            {
                "family_id": "fam_ready",
                "patch_draft_status": "rule_patch_ready",
                "patch_readiness": "ready",
            },
            {
                "family_id": "fam_hold",
                "patch_draft_status": "truth_collection_before_patch",
                "patch_readiness": "blocked",
            },
        ]
    )

    candidates, summary = build_manual_vs_heuristic_correction_candidates(
        ranking,
        patch_draft,
        now="2026-04-07T12:00:00+09:00",
    )

    assert len(candidates) == 2
    ready = candidates[candidates["family_key"] == "fam_ready"].iloc[0]
    hold = candidates[candidates["family_key"] == "fam_hold"].iloc[0]
    assert bool(ready["selected_for_patch"]) is True
    assert ready["selection_reason"] == "selected_for_patch::p1::edit_rule_now"
    assert bool(hold["selected_for_patch"]) is False
    assert hold["selection_reason"] == "collect_more_truth_before_patch::collect_current_rich_truth"
    assert summary["selected_for_patch_count"] == 1
    assert summary["next_candidate_id"] == ready["run_candidate_id"]


def test_manual_vs_heuristic_correction_runs_emit_hold_when_truth_collection_required() -> None:
    candidates = pd.DataFrame(
        [
            {
                "run_candidate_id": "correction_candidate::fam_hold",
                "created_at": "2026-04-07T12:00:00+09:00",
                "family_key": "fam_hold",
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "failed_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_barrier_main_label": "correct_wait",
                "case_count": 3,
                "correction_worthy_case_count": 0,
                "freeze_worthy_case_count": 1,
                "hold_for_more_truth_case_count": 3,
                "priority_tier": "P3",
                "recommended_next_action": "collect_current_rich_truth",
                "patch_draft_status": "truth_collection_before_patch",
                "patch_readiness": "blocked",
                "selected_for_patch": False,
                "selection_reason": "collect_more_truth_before_patch::collect_current_rich_truth",
                "selected_by": "",
            }
        ]
    )
    comparison = pd.DataFrame(
        [
            {
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "failed_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_barrier_main_label": "correct_wait",
                "correction_worthiness_class": "candidate_correction",
                "freeze_worthiness_class": "hold_for_more_truth",
                "rule_change_readiness": "needs_more_recent_truth",
            },
            {
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "failed_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_barrier_main_label": "correct_wait",
                "correction_worthiness_class": "candidate_correction",
                "freeze_worthiness_class": "freeze_worthy",
                "rule_change_readiness": "insufficient_evidence",
            },
        ]
    )

    runs, summary = build_manual_vs_heuristic_correction_runs(
        candidates,
        comparison,
        now="2026-04-07T12:00:00+09:00",
    )

    assert len(runs) == 1
    row = runs.iloc[0]
    assert row["decision"] == "hold_for_more_truth"
    assert row["decision_reason"] == "truth_collection_before_patch"
    assert row["patch_version"] == "truth_collection_only_v0"
    assert int(row["before_mismatch_count"]) == 2
    assert int(row["after_mismatch_count"]) == 2
    assert int(row["mismatch_delta"]) == 0
    assert bool(row["side_effect_flag"]) is False
    assert summary["hold_count"] == 1
    assert summary["latest_run_id"] == row["correction_run_id"]
