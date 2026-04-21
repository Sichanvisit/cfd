import pandas as pd

from backend.services.shadow_auto_threshold_sweep import build_shadow_auto_threshold_sweep


def test_build_shadow_auto_threshold_sweep_marks_target_conflict_for_entering_profile():
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "baseline_realized_value": 0.2,
                "target_timing_now_vs_wait": 1,
                "target_exit_management": 0,
                "shadow_timing_probability": 0.9,
                "shadow_entry_quality_probability": 0.9,
                "shadow_exit_management_probability": 0.1,
                "shadow_should_enter": True,
                "shadow_recommendation": "enter_now",
                "shadow_realized_value": 0.2,
            }
        ]
    )
    feature_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "scene_family": "pattern_1",
            }
        ]
    )

    frame, summary = build_shadow_auto_threshold_sweep(
        demo,
        feature_rows=feature_rows,
        threshold_values=(0.55, 0.95),
        exit_threshold_values=(0.8,),
    )

    low_threshold_row = frame.loc[frame["sweep_profile_id"].eq("threshold::0.55::0.55::0.80")].iloc[0]
    assert low_threshold_row["recommended_next_action"] == "reject_or_redesign_targets"
    assert summary["row_count"] == 4


def test_build_shadow_auto_threshold_sweep_reviews_profile_when_bridge_context_prefers_wait_better_entry():
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "baseline_realized_value": 0.2,
                "target_timing_now_vs_wait": 1,
                "target_exit_management": 0,
                "shadow_timing_probability": 0.9,
                "shadow_entry_quality_probability": 0.9,
                "shadow_exit_management_probability": 0.1,
                "shadow_should_enter": True,
                "shadow_recommendation": "enter_now",
                "shadow_realized_value": 0.2,
            }
        ]
    )
    feature_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "learning_total_label": "positive",
                "signed_exit_score": 90.0,
                "wait_bias_hint": "wait",
                "forecast_decision_hint": "BALANCED",
                "scene_family": "pattern_1",
            }
        ]
    )

    frame, _summary = build_shadow_auto_threshold_sweep(
        demo,
        feature_rows=feature_rows,
        threshold_values=(0.55,),
        exit_threshold_values=(0.8,),
    )

    row = frame.iloc[0]
    assert row["mapped_alignment_improvement"] == 0.0
    assert row["recommended_next_action"] == "review_threshold_profile"
