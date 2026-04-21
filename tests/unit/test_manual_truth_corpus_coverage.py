import pandas as pd

from backend.services.manual_truth_corpus_coverage import (
    build_manual_truth_corpus_coverage,
)


def test_manual_truth_corpus_coverage_maps_family_pattern_density() -> None:
    canonical = pd.DataFrame(
        [
            {
                "episode_id": "canon1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T17:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "annotation_source": "chart_annotated",
            },
            {
                "episode_id": "canon2",
                "symbol": "NAS100",
                "anchor_time": "2026-04-06T18:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "annotation_source": "assistant_chart_inferred",
            },
        ]
    )
    draft = pd.DataFrame(
        [
            {
                "episode_id": "draft1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-07T03:00:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "annotation_source": "assistant_current_rich_seed",
                "review_status": "needs_manual_recheck",
            }
        ]
    )

    coverage, summary = build_manual_truth_corpus_coverage(canonical, draft)

    assert len(coverage) == 1
    row = coverage.iloc[0]
    assert row["symbol"] == "NAS100"
    assert row["coverage_class"] == "thin"
    assert row["review_pressure_class"] == "high"
    assert row["recommended_next_action"] == "review_current_rich_then_promote"
    assert summary["coverage_row_count"] == 1
