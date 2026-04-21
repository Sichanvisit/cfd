import pandas as pd

from backend.services.manual_vs_heuristic_patch_draft import (
    build_manual_vs_heuristic_patch_draft,
)


def test_manual_vs_heuristic_patch_draft_builds_truth_collection_and_freeze_rows() -> None:
    sandbox = pd.DataFrame(
        [
            {
                "sandbox_id": "bias_sandbox::fam_collect",
                "family_id": "fam_collect",
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "correction_priority_tier": "P3",
                "sandbox_status": "collect_more_truth_before_patch",
                "patch_hypothesis": "do_not_edit_rule_yet_collect_more_current_rich_truth",
                "patch_scope": "barrier_wait_mapping_logic",
                "validation_plan": "rerun_comparison|rerun_bias_targets",
                "adoption_gate": "mismatch_down_without_new_freeze_regression",
                "rejection_gate": "new_freeze_regression_or_no_material_gain",
                "recommended_next_action": "collect_more_truth_then_rerank",
            },
            {
                "sandbox_id": "bias_sandbox::fam_freeze",
                "family_id": "fam_freeze",
                "miss_type": "insufficient_heuristic_evidence",
                "primary_correction_target": "insufficient_owner_coverage",
                "correction_priority_tier": "HOLD",
                "sandbox_status": "freeze_track_only",
                "patch_hypothesis": "do_not_edit_rule_track_as_freeze_candidate",
                "patch_scope": "owner_logging_coverage_only",
                "validation_plan": "rerun_comparison|rerun_bias_targets",
                "adoption_gate": "mismatch_down_without_new_freeze_regression",
                "rejection_gate": "new_freeze_regression_or_no_material_gain",
                "recommended_next_action": "freeze_and_monitor",
            },
        ]
    )

    draft, summary = build_manual_vs_heuristic_patch_draft(sandbox)

    assert len(draft) == 2
    collect_row = draft[draft["family_id"] == "fam_collect"].iloc[0]
    assert collect_row["patch_draft_status"] == "truth_collection_before_patch"
    assert collect_row["patch_readiness"] == "blocked"
    assert "Do not edit the BCE rule yet" in collect_row["proposed_rule_change_summary"]
    freeze_row = draft[draft["family_id"] == "fam_freeze"].iloc[0]
    assert freeze_row["patch_draft_status"] == "freeze_monitor_only"
    assert freeze_row["approval_status"] == "freeze_monitoring"
    assert summary["next_patch_draft_id"] == collect_row["patch_draft_id"]
