import pandas as pd

from backend.services.shadow_auto_evaluation import build_shadow_auto_evaluation


def test_build_shadow_auto_evaluation_marks_runtime_unavailable_when_rows_exist_but_shadow_is_off():
    compare_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_a",
                "timestamp": "2026-04-07T03:00:00+09:00",
                "semantic_shadow_available": 0,
                "manual_label": "good_wait_better_entry",
                "match_improvement": "unknown",
                "shadow_match": "unavailable",
            }
        ]
    )
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_a",
                "family_key": "fam_a",
                "patch_version": "shadow_patch::fam_a::v0",
                "candidate_kind": "truth_collection_probe",
                "bridge_status": "await_more_truth",
            }
        ]
    )

    evaluation, summary = build_shadow_auto_evaluation(compare_df, shadow_candidates=candidates_df)

    assert len(evaluation) == 1
    row = evaluation.iloc[0]
    assert row["decision_readiness"] == "shadow_runtime_unavailable"
    assert row["recommended_next_action"] == "enable_shadow_runtime"
    assert summary["decision_readiness_counts"]["shadow_runtime_unavailable"] == 1


def test_build_shadow_auto_evaluation_handles_candidate_without_observed_rows():
    compare_df = pd.DataFrame(columns=["shadow_candidate_id", "timestamp", "semantic_shadow_available", "manual_label", "match_improvement", "shadow_match"])
    candidates_df = pd.DataFrame(
        [
            {
                "shadow_candidate_id": "shadow_candidate::fam_b",
                "family_key": "fam_b",
                "patch_version": "shadow_patch::fam_b::v0",
                "candidate_kind": "freeze_monitor",
                "bridge_status": "freeze_track_only",
            }
        ]
    )

    evaluation, summary = build_shadow_auto_evaluation(compare_df, shadow_candidates=candidates_df)

    assert len(evaluation) == 1
    row = evaluation.iloc[0]
    assert row["decision_readiness"] == "freeze_monitor_only"
    assert row["recommended_next_action"] == "freeze_and_monitor"
    assert summary["candidate_count"] == 1
