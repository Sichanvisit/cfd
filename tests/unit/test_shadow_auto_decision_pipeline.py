import pandas as pd

from backend.services.shadow_auto_correction_loop import (
    build_shadow_auto_correction_loop,
)
from backend.services.shadow_auto_decision_engine import (
    build_shadow_auto_decision_engine,
)


def test_shadow_correction_loop_and_decision_engine_accept_candidate_when_preview_improves():
    evaluation = pd.DataFrame(
        [
            {
                "evaluation_scope": "preview_bundle_test_bucket",
                "row_count": 16,
                "available_row_count": 16,
                "baseline_value_sum": 1.0,
                "shadow_value_sum": 2.0,
                "value_diff": 1.0,
                "baseline_drawdown": -1.0,
                "shadow_drawdown": -0.5,
                "drawdown_diff": -0.5,
                "manual_alignment_improvement": 0.2,
            }
        ]
    )

    correction, _summary = build_shadow_auto_correction_loop(evaluation)
    decision, _decision_summary = build_shadow_auto_decision_engine(
        correction,
        preview_bundle_ready=True,
    )

    assert correction.iloc[0]["decision"] == "accept_preview_candidate"
    assert decision.iloc[0]["decision"] == "APPLY_CANDIDATE"
