import pandas as pd

from backend.services.manual_vs_heuristic_ranking_retrospective import (
    build_manual_vs_heuristic_ranking_retrospective,
)


def test_ranking_retrospective_marks_needed_more_truth_from_correction_run() -> None:
    ranking = pd.DataFrame(
        [
            {
                "family_id": "fam_a",
                "correction_priority_tier": "P3",
                "recommended_next_action": "collect_current_rich_truth",
                "priority_score_total": 3.0,
                "priority_score_evidence": 2.0,
                "priority_score_reproducibility": 1.0,
                "priority_score_correction_cost": 1.0,
                "priority_score_freeze_risk_penalty": 4.0,
            },
            {
                "family_id": "fam_b",
                "correction_priority_tier": "hold",
                "recommended_next_action": "freeze_and_monitor",
                "priority_score_total": 1.0,
                "priority_score_evidence": 1.0,
                "priority_score_reproducibility": 1.0,
                "priority_score_correction_cost": 2.0,
                "priority_score_freeze_risk_penalty": 7.0,
            },
        ]
    )
    correction_runs = pd.DataFrame(
        [
            {
                "family_key": "fam_a",
                "decision": "hold_for_more_truth",
                "started_at": "2026-04-07T12:00:00+09:00",
                "finished_at": "2026-04-07T12:10:00+09:00",
            }
        ]
    )

    history, summary = build_manual_vs_heuristic_ranking_retrospective(ranking, correction_runs)

    assert len(history) == 2
    fam_a = history[history["family_key"] == "fam_a"].iloc[0]
    fam_b = history[history["family_key"] == "fam_b"].iloc[0]
    assert fam_a["retrospective_result"] == "needed_more_truth"
    assert bool(fam_a["actual_followup_taken"]) is True
    assert fam_b["retrospective_result"] == "not_executed"
    assert summary["ranking_execution_rate"] == 0.5
    assert summary["ranking_needed_more_truth_accuracy"] == 1.0
