import pandas as pd

from backend.services.shadow_auto_manual_reference_audit import (
    build_shadow_auto_manual_reference_audit,
)


def test_build_shadow_auto_manual_reference_audit_marks_missing_manual_truth() -> None:
    divergence_rows = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "manual_reference_found": False,
                "manual_target_match_flag": False,
            },
            {
                "symbol": "BTCUSD",
                "manual_reference_found": False,
                "manual_target_match_flag": False,
            },
        ]
    )

    frame, summary = build_shadow_auto_manual_reference_audit(
        divergence_rows,
        required_manual_reference_row_count=3,
    )

    row = frame.iloc[0]
    assert row["manual_reference_status"] == "manual_truth_missing"
    assert row["recommended_next_action"] == "expand_manual_truth_shadow_overlap"
    assert summary["overall_manual_reference_row_count"] == 0


def test_build_shadow_auto_manual_reference_audit_marks_ready_scope() -> None:
    divergence_rows = pd.DataFrame(
        [
            {
                "symbol": "BTCUSD",
                "manual_reference_found": True,
                "manual_target_match_flag": True,
            },
            {
                "symbol": "BTCUSD",
                "manual_reference_found": True,
                "manual_target_match_flag": True,
            },
        ]
    )

    frame, summary = build_shadow_auto_manual_reference_audit(
        divergence_rows,
        required_manual_reference_row_count=2,
    )

    row = frame.iloc[0]
    assert bool(row["manual_reference_ready_flag"]) is True
    assert row["manual_reference_status"] == "manual_truth_ready"
    assert summary["status_counts"]["manual_truth_ready"] >= 1
