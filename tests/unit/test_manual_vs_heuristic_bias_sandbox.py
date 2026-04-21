import pandas as pd

from backend.services.manual_vs_heuristic_bias_sandbox import (
    build_manual_vs_heuristic_bias_sandbox,
)


def test_manual_vs_heuristic_bias_sandbox_builds_collect_and_freeze_paths() -> None:
    ranking = pd.DataFrame(
        [
            {
                "family_id": "fam_collect",
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "correction_priority_tier": "P3",
                "family_disposition": "collect_more_truth",
                "case_count": 3,
                "ready_case_count": 0,
                "hold_for_more_truth_case_count": 3,
                "priority_score_total": 3.0,
                "top_episode_ids": "['ep1','ep2']",
            },
            {
                "family_id": "fam_freeze",
                "miss_type": "insufficient_heuristic_evidence",
                "primary_correction_target": "insufficient_owner_coverage",
                "correction_priority_tier": "hold",
                "family_disposition": "freeze_candidate",
                "case_count": 10,
                "ready_case_count": 0,
                "hold_for_more_truth_case_count": 10,
                "priority_score_total": 1.2,
                "top_episode_ids": "['ep3']",
            },
        ]
    )
    targets = pd.DataFrame(
        [
            {
                "miss_type": "wrong_failed_wait_interpretation",
                "primary_correction_target": "barrier_bias_rule",
                "priority": "P1",
                "recommended_bce_step": "BCE bias correction / failed_wait recovery",
            }
        ]
    )

    sandbox, summary = build_manual_vs_heuristic_bias_sandbox(ranking, targets)

    assert len(sandbox) == 2
    assert sandbox.iloc[0]["sandbox_status"] == "collect_more_truth_before_patch"
    assert sandbox.iloc[0]["recommended_bce_step"] == "BCE bias correction / failed_wait recovery"
    assert sandbox.iloc[0]["recommended_next_action"] == "collect_more_truth_then_rerank"
    freeze_row = sandbox[sandbox["family_id"] == "fam_freeze"].iloc[0]
    assert freeze_row["sandbox_status"] == "freeze_track_only"
    assert summary["next_sandbox_id"] == sandbox.iloc[0]["sandbox_id"]
