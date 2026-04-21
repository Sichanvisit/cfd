import pandas as pd

from backend.services.shadow_auto_candidate_bridge import build_shadow_auto_candidate_bridge


def test_build_shadow_auto_candidate_bridge_marks_collect_more_truth_and_freeze():
    ranking = pd.DataFrame(
        [
            {
                "family_id": "fam_a",
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
                "recommended_next_action": "collect_current_rich_truth",
                "family_disposition": "collect_more_truth",
            },
            {
                "family_id": "fam_b",
                "miss_type": "insufficient_heuristic_evidence",
                "primary_correction_target": "insufficient_owner_coverage",
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "none",
                "heuristic_barrier_main_label": "none",
                "case_count": 10,
                "correction_worthy_case_count": 0,
                "freeze_worthy_case_count": 10,
                "hold_for_more_truth_case_count": 10,
                "ready_case_count": 0,
                "correction_priority_tier": "hold",
                "recommended_next_action": "freeze_and_monitor",
                "family_disposition": "freeze_candidate",
            },
        ]
    )
    patch_draft = pd.DataFrame(
        [
            {"family_id": "fam_a", "patch_draft_id": "patch_a", "patch_draft_status": "truth_collection_before_patch", "patch_readiness": "blocked"},
            {"family_id": "fam_b", "patch_draft_id": "patch_b", "patch_draft_status": "freeze_monitor_only", "patch_readiness": "blocked"},
        ]
    )
    correction_candidates = pd.DataFrame(
        [
            {"family_key": "fam_a", "run_candidate_id": "cand_a", "selected_for_patch": False, "selection_reason": "collect_more_truth_before_patch"},
            {"family_key": "fam_b", "run_candidate_id": "cand_b", "selected_for_patch": False, "selection_reason": "freeze_monitor_only"},
        ]
    )

    bridge, summary = build_shadow_auto_candidate_bridge(
        ranking,
        patch_draft=patch_draft,
        correction_candidates=correction_candidates,
    )

    assert len(bridge) == 2
    assert summary["candidate_count"] == 2
    row_a = bridge.loc[bridge["family_key"] == "fam_a"].iloc[0]
    row_b = bridge.loc[bridge["family_key"] == "fam_b"].iloc[0]
    assert row_a["bridge_status"] == "await_more_truth"
    assert row_a["candidate_kind"] == "truth_collection_probe"
    assert bool(row_a["selected_for_shadow"]) is False
    assert row_b["bridge_status"] == "freeze_track_only"
    assert row_b["candidate_kind"] == "freeze_monitor"
