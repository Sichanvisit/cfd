import pandas as pd

from backend.services.manual_vs_heuristic_family_ranking import (
    build_manual_vs_heuristic_family_ranking,
)


def test_manual_vs_heuristic_family_ranking_groups_and_prioritizes() -> None:
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "symbol": "NAS100",
                "miss_type": "false_avoided_loss",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "neutral_wait",
                "heuristic_barrier_main_label": "avoided_loss",
                "correction_worthiness_class": "correction_worthy",
                "freeze_worthiness_class": "not_freeze_worthy",
                "rule_change_readiness": "ready",
                "frequency_score": 3,
                "severity_score": 3,
                "correction_priority_score": 12,
                "freeze_risk_score": 2,
                "evidence_quality_score": 3,
                "current_rich_reproducibility_score": 3,
                "correction_cost_score": 2,
                "manual_truth_source_bucket": "canonical_chart_reviewed",
                "heuristic_source_kind": "rotate_detail",
                "mismatch_severity": "high",
            },
            {
                "episode_id": "ep2",
                "symbol": "NAS100",
                "miss_type": "false_avoided_loss",
                "primary_correction_target": "barrier_bias_rule",
                "manual_wait_teacher_family": "timing_improvement",
                "heuristic_wait_family": "neutral_wait",
                "heuristic_barrier_main_label": "avoided_loss",
                "correction_worthiness_class": "correction_worthy",
                "freeze_worthiness_class": "not_freeze_worthy",
                "rule_change_readiness": "ready",
                "frequency_score": 3,
                "severity_score": 3,
                "correction_priority_score": 11,
                "freeze_risk_score": 2,
                "evidence_quality_score": 3,
                "current_rich_reproducibility_score": 3,
                "correction_cost_score": 2,
                "manual_truth_source_bucket": "canonical_chart_reviewed",
                "heuristic_source_kind": "rotate_detail",
                "mismatch_severity": "high",
            },
            {
                "episode_id": "ep3",
                "symbol": "BTCUSD",
                "miss_type": "insufficient_heuristic_evidence",
                "primary_correction_target": "insufficient_owner_coverage",
                "manual_wait_teacher_family": "failed_wait",
                "heuristic_wait_family": "",
                "heuristic_barrier_main_label": "",
                "correction_worthiness_class": "not_correction_worthy",
                "freeze_worthiness_class": "freeze_worthy",
                "rule_change_readiness": "insufficient_evidence",
                "frequency_score": 1,
                "severity_score": 2,
                "correction_priority_score": 9,
                "freeze_risk_score": 8,
                "evidence_quality_score": 1,
                "current_rich_reproducibility_score": 1,
                "correction_cost_score": 2,
                "manual_truth_source_bucket": "canonical_chart_reviewed",
                "heuristic_source_kind": "",
                "mismatch_severity": "medium",
            },
        ]
    )

    ranking, summary = build_manual_vs_heuristic_family_ranking(comparison)

    assert len(ranking) == 2
    assert ranking.iloc[0]["correction_priority_tier"] == "P1"
    assert ranking.iloc[0]["recommended_next_action"] == "edit_rule_now"
    assert float(ranking.iloc[0]["priority_score_total"]) == 12.0
    assert float(ranking.iloc[0]["priority_score_freeze_risk_penalty"]) == 2.0
    assert "ready=2" in ranking.iloc[0]["ranking_reason_summary"]
    assert ranking.iloc[1]["family_disposition"] == "freeze_candidate"
    assert summary["next_target_family_id"] == ranking.iloc[0]["family_id"]
