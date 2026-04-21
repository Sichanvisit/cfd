import pandas as pd

from backend.services.manual_vs_heuristic_bias_targets import (
    build_manual_vs_heuristic_bias_targets,
)


def test_manual_vs_heuristic_bias_targets_groups_recovered_mismatches() -> None:
    recovered = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "symbol": "NAS100",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "heuristic_barrier_main_label": "avoided_loss",
                "heuristic_wait_family": "neutral_wait",
                "overall_alignment_grade": "mismatch",
                "miss_type": "false_avoided_loss",
                "primary_correction_target": "barrier_bias_rule",
                "heuristic_reconstruction_source_file": "rotate_a.jsonl",
            },
            {
                "episode_id": "ep2",
                "symbol": "NAS100",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "heuristic_barrier_main_label": "avoided_loss",
                "heuristic_wait_family": "neutral_wait",
                "overall_alignment_grade": "mismatch",
                "miss_type": "false_avoided_loss",
                "primary_correction_target": "barrier_bias_rule",
                "heuristic_reconstruction_source_file": "rotate_a.jsonl",
            },
            {
                "episode_id": "ep3",
                "symbol": "BTCUSD",
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "heuristic_barrier_main_label": "avoided_loss",
                "heuristic_wait_family": "neutral_wait",
                "overall_alignment_grade": "partial_match",
                "miss_type": "wrong_protective_interpretation",
                "primary_correction_target": "protective_exit_interpretation",
                "heuristic_reconstruction_source_file": "rotate_b.jsonl",
            },
        ]
    )

    targets, summary = build_manual_vs_heuristic_bias_targets(recovered)

    assert len(targets) == 2
    assert targets.iloc[0]["priority"] == "P1"
    assert targets.iloc[0]["miss_type"] == "false_avoided_loss"
    assert targets.iloc[0]["case_count"] == 2
    assert "timing_improvement" in targets.iloc[0]["recommended_bias_action"]
    assert summary["target_count"] == 2
    assert summary["priority_counts"] == {"P1": 2}


def test_manual_vs_heuristic_bias_targets_returns_empty_for_no_mismatch() -> None:
    recovered = pd.DataFrame(
        [
            {
                "episode_id": "ep1",
                "overall_alignment_grade": "match",
            }
        ]
    )

    targets, summary = build_manual_vs_heuristic_bias_targets(recovered)

    assert targets.empty
    assert summary["target_count"] == 0
