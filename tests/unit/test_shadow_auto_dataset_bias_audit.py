import pandas as pd

from backend.services.shadow_auto_dataset_bias_audit import build_shadow_auto_dataset_bias_audit


def test_build_shadow_auto_dataset_bias_audit_detects_target_mapping_disagreement():
    feature_rows = pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "r1",
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "scene_family": "pattern_1",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "target_timing_now_vs_wait": 1,
                "target_exit_management": 0,
            },
            {
                "bridge_adapter_row_id": "r2",
                "bridge_decision_time": "2026-04-08T10:01:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "scene_family": "pattern_1",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "target_timing_now_vs_wait": 1,
                "target_exit_management": 0,
            },
        ]
    )

    audit, rebalanced, summary = build_shadow_auto_dataset_bias_audit(feature_rows)

    overall = audit.loc[audit["audit_scope_kind"].eq("overall")].iloc[0]
    assert overall["target_mapping_disagreement_share"] == 1.0
    assert overall["recommended_rebalance_action"] == "collect_more_manual_truth_then_reweight"
    assert not rebalanced.empty
    assert summary["rebalanced_row_count"] == 2
    assert summary["manual_truth_share"] == 0.0


def test_build_shadow_auto_dataset_bias_audit_upweights_manual_truth_anchors():
    feature_rows = pd.DataFrame(
        [
            {
                "bridge_adapter_row_id": "r1",
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "scene_family": "pattern_1",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "target_timing_now_vs_wait": 0,
                "target_exit_management": 0,
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
                "anchor_time": "2026-04-08T09:59:00+09:00",
                "ideal_entry_time": "2026-04-08T10:00:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_family": "failed_wait",
                "manual_wait_teacher_confidence": "high",
                "review_status": "accepted",
                "annotation_source": "chart_annotated",
            }
        ]
    )

    audit, rebalanced, summary = build_shadow_auto_dataset_bias_audit(
        feature_rows,
        manual_truth=manual_truth,
    )

    overall = audit.loc[audit["audit_scope_kind"].eq("overall")].iloc[0]
    assert overall["manual_truth_share"] == 1.0
    assert rebalanced.iloc[0]["rebalance_bucket"] == "manual_truth_anchor"
    assert rebalanced.iloc[0]["sample_weight"] > 2.0
    assert summary["manual_reference_row_count"] == 1
