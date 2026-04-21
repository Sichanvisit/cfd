import pandas as pd

from backend.services.manual_vs_heuristic_recovered_casebook import (
    build_manual_vs_heuristic_recovered_casebook,
)


def test_manual_vs_heuristic_recovered_casebook_filters_global_detail_rows() -> None:
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "ep_001",
                "symbol": "NAS100",
                "anchor_time": "2026-04-03T10:00:00+09:00",
                "anchor_side": "BUY",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "manual_wait_teacher_confidence": "medium",
                "heuristic_barrier_main_label": "correct_wait",
                "heuristic_wait_family": "timing_improvement",
                "heuristic_wait_subtype": "better_entry_after_wait",
                "heuristic_barrier_confidence_tier": "fallback_medium",
                "heuristic_barrier_reason_summary": "recovered wait helper",
                "heuristic_reconstruction_mode": "global_detail_fallback",
                "heuristic_reconstruction_source_file": "entry_decisions.detail.rotate_a.jsonl",
                "manual_vs_barrier_match": "match",
                "manual_vs_wait_family_match": "match",
                "overall_alignment_grade": "match",
                "miss_type": "",
                "mismatch_severity": "low",
                "primary_correction_target": "",
                "repeated_case_signature": "NAS100|timing_improvement|timing_improvement|aligned",
                "review_comment": "ok",
            },
            {
                "episode_id": "ep_002",
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-03T11:00:00+09:00",
                "anchor_side": "BUY",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "manual_wait_teacher_family": "timing_improvement",
                "manual_wait_teacher_subtype": "better_entry_after_wait",
                "manual_wait_teacher_confidence": "medium",
                "heuristic_barrier_main_label": "",
                "heuristic_wait_family": "",
                "heuristic_wait_subtype": "",
                "heuristic_barrier_confidence_tier": "",
                "heuristic_barrier_reason_summary": "",
                "heuristic_reconstruction_mode": "",
                "heuristic_reconstruction_source_file": "",
                "manual_vs_barrier_match": "unknown",
                "manual_vs_wait_family_match": "unknown",
                "overall_alignment_grade": "unknown",
                "miss_type": "insufficient_heuristic_evidence",
                "mismatch_severity": "medium",
                "primary_correction_target": "insufficient_owner_coverage",
                "repeated_case_signature": "BTCUSD|timing_improvement|heuristic_none|insufficient_heuristic_evidence",
                "review_comment": "missing",
            },
            {
                "episode_id": "ep_003",
                "symbol": "NAS100",
                "anchor_time": "2026-04-03T12:00:00+09:00",
                "anchor_side": "SELL",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_subtype": "wait_but_missed_move",
                "manual_wait_teacher_confidence": "high",
                "heuristic_barrier_main_label": "avoided_loss",
                "heuristic_wait_family": "neutral_wait",
                "heuristic_wait_subtype": "small_value_wait",
                "heuristic_barrier_confidence_tier": "fallback_low",
                "heuristic_barrier_reason_summary": "lower rebound probe",
                "heuristic_reconstruction_mode": "global_detail_fallback",
                "heuristic_reconstruction_source_file": "entry_decisions.detail.rotate_b.jsonl",
                "manual_vs_barrier_match": "mismatch",
                "manual_vs_wait_family_match": "mismatch",
                "overall_alignment_grade": "mismatch",
                "miss_type": "wrong_failed_wait_interpretation",
                "mismatch_severity": "high",
                "primary_correction_target": "barrier_bias_rule",
                "repeated_case_signature": "NAS100|failed_wait|neutral_wait|wrong_failed_wait_interpretation",
                "review_comment": "bad",
            },
        ]
    )

    casebook, summary = build_manual_vs_heuristic_recovered_casebook(comparison)

    assert len(casebook) == 2
    assert casebook.iloc[0]["episode_id"] == "ep_003"
    assert summary["recovered_case_count"] == 2
    assert summary["symbol_counts"] == {"NAS100": 2}
    assert summary["alignment_counts"] == {"mismatch": 1, "match": 1}
    assert summary["miss_type_counts"] == {"wrong_failed_wait_interpretation": 1, "aligned": 1}


def test_manual_vs_heuristic_recovered_casebook_returns_empty_when_no_recovered_rows() -> None:
    comparison = pd.DataFrame(
        [
            {
                "episode_id": "ep_001",
                "heuristic_reconstruction_mode": "",
            }
        ]
    )

    casebook, summary = build_manual_vs_heuristic_recovered_casebook(comparison)

    assert casebook.empty
    assert summary["recovered_case_count"] == 0
