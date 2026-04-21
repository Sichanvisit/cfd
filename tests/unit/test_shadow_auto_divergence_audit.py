import pandas as pd

from backend.services.shadow_auto_divergence_audit import build_shadow_auto_divergence_audit


def test_build_shadow_auto_divergence_audit_detects_divergence_and_target_conflict():
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
                "shadow_should_enter": True,
                "shadow_recommendation": "enter_now",
                "shadow_exit_management_probability": 0.1,
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

    frame, summary = build_shadow_auto_divergence_audit(demo, feature_rows=feature_rows)

    row = frame.loc[frame["scope_kind"].eq("overall")].iloc[0]
    assert row["divergence_rate"] == 1.0
    assert row["recommended_next_action"] == "redesign_target_mapping_or_thresholds"
    assert summary["row_count"] >= 1


def test_build_shadow_auto_divergence_audit_surfaces_manual_reference_metrics():
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "baseline_realized_value": 0.4,
                "target_timing_now_vs_wait": 0,
                "target_exit_management": 0,
                "shadow_should_enter": True,
                "shadow_recommendation": "enter_now",
                "shadow_exit_management_probability": 0.1,
                "shadow_realized_value": 0.4,
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
    manual_truth = pd.DataFrame(
        [
            {
                "annotation_id": "m1",
                "episode_id": "m1",
                "symbol": "BTCUSD",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-08T09:58:00+09:00",
                "ideal_entry_time": "2026-04-08T10:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_confidence": "high",
                "review_status": "accepted",
                "annotation_source": "chart_annotated",
            }
        ]
    )

    frame, summary = build_shadow_auto_divergence_audit(
        demo,
        feature_rows=feature_rows,
        manual_truth=manual_truth,
    )

    row = frame.loc[frame["scope_kind"].eq("overall")].iloc[0]
    assert row["manual_reference_row_count"] == 1
    assert row["manual_alignment_delta"] == 1.0
    assert row["bounded_risk_flag"] == "bounded"
    assert summary["manual_reference_row_count"] == 1


def test_build_shadow_auto_divergence_audit_requests_redesign_when_context_prefers_wait_better_entry():
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
                "shadow_should_enter": True,
                "shadow_recommendation": "enter_now",
                "shadow_exit_management_probability": 0.1,
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

    frame, summary = build_shadow_auto_divergence_audit(demo, feature_rows=feature_rows)

    row = frame.loc[frame["scope_kind"].eq("overall")].iloc[0]
    assert row["mapped_alignment_improvement"] == 0.0
    assert row["recommended_next_action"] == "redesign_target_mapping_or_thresholds"
    assert summary["recommended_next_action_counts"]["redesign_target_mapping_or_thresholds"] >= 1
