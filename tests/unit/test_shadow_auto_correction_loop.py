import pandas as pd

from backend.services.shadow_auto_correction_loop import build_shadow_auto_correction_loop


def test_build_shadow_auto_correction_loop_accepts_when_value_and_alignment_improve():
    evaluation = pd.DataFrame(
        [
            {
                "evaluation_scope": "preview_bundle_test_bucket",
                "row_count": 12,
                "available_row_count": 12,
                "baseline_value_sum": 1.0,
                "shadow_value_sum": 3.0,
                "value_diff": 2.0,
                "baseline_drawdown": -2.0,
                "shadow_drawdown": -2.0,
                "drawdown_diff": 0.0,
                "manual_alignment_improvement": 0.2,
            }
        ]
    )

    frame, summary = build_shadow_auto_correction_loop(evaluation)

    row = frame.iloc[0]
    assert row["decision"] == "accept_preview_candidate"
    assert summary["decision_counts"]["accept_preview_candidate"] == 1


def test_build_shadow_auto_correction_loop_rejects_when_value_diff_is_negative():
    evaluation = pd.DataFrame(
        [
            {
                "evaluation_scope": "preview_bundle_test_bucket",
                "row_count": 10,
                "available_row_count": 10,
                "baseline_value_sum": 3.0,
                "shadow_value_sum": 1.0,
                "value_diff": -2.0,
                "baseline_drawdown": -1.0,
                "shadow_drawdown": -3.0,
                "drawdown_diff": -2.0,
                "manual_alignment_improvement": -0.1,
            }
        ]
    )

    frame, _summary = build_shadow_auto_correction_loop(evaluation)

    assert frame.iloc[0]["decision"] == "reject_preview_candidate"
