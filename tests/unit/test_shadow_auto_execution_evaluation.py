import pandas as pd

from backend.services.shadow_auto_execution_evaluation import build_shadow_auto_execution_evaluation


def test_build_shadow_auto_execution_evaluation_computes_value_and_alignment_delta():
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-07T00:00:00",
                "semantic_shadow_available": 1,
                "shadow_should_enter": 1,
                "baseline_realized_value": 1.5,
                "shadow_realized_value": 1.5,
                "target_timing_now_vs_wait": 1,
                "alignment_label": "aligned",
            },
            {
                "bridge_decision_time": "2026-04-07T00:01:00",
                "semantic_shadow_available": 1,
                "shadow_should_enter": 0,
                "baseline_realized_value": -2.0,
                "shadow_realized_value": 0.0,
                "target_timing_now_vs_wait": 0,
                "alignment_label": "aligned",
            },
        ]
    )

    frame, summary = build_shadow_auto_execution_evaluation(demo)

    row = frame.iloc[0]
    assert row["row_count"] == 2
    assert row["available_row_count"] == 2
    assert row["shadow_enter_count"] == 1
    assert row["baseline_value_sum"] == -0.5
    assert row["shadow_value_sum"] == 1.5
    assert row["value_diff"] == 2.0
    assert row["manual_alignment_improvement"] == 0.5
    assert summary["shadow_value_sum"] == 1.5


def test_build_shadow_auto_execution_evaluation_applies_candidate_slice_filter():
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-07T00:00:00",
                "symbol": "BTCUSD",
                "semantic_shadow_available": 1,
                "shadow_should_enter": 0,
                "baseline_realized_value": 1.0,
                "shadow_realized_value": 1.0,
                "target_timing_now_vs_wait": 0,
                "alignment_label": "aligned",
            },
            {
                "bridge_decision_time": "2026-04-07T00:01:00",
                "symbol": "BTCUSD",
                "semantic_shadow_available": 1,
                "shadow_should_enter": 0,
                "baseline_realized_value": 2.0,
                "shadow_realized_value": 1.5,
                "target_timing_now_vs_wait": 0,
                "alignment_label": "aligned",
            },
        ]
    )
    candidate_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-07T00:01:00",
                "symbol": "BTCUSD",
            }
        ]
    )

    frame, summary = build_shadow_auto_execution_evaluation(demo, candidate_rows=candidate_rows)

    row = frame.iloc[0]
    assert row["evaluation_scope"] == "preview_bundle_candidate_slice"
    assert row["row_count"] == 1
    assert row["baseline_value_sum"] == 2.0
    assert row["shadow_value_sum"] == 1.5
    assert row["value_diff"] == -0.5
    assert summary["candidate_slice_applied"] is True
