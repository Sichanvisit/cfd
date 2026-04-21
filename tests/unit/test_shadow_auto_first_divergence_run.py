import pandas as pd

from backend.services.shadow_auto_first_divergence_run import build_shadow_auto_first_divergence_run


def test_build_shadow_auto_first_divergence_run_can_reject_conflicting_profile():
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
    threshold_sweep = pd.DataFrame(
        [
            {
                "sweep_profile_id": "threshold::0.55::0.55",
                "timing_threshold": 0.55,
                "entry_quality_threshold": 0.55,
                "divergence_rate": 1.0,
                "value_diff_proxy": 0.0,
                "mapped_alignment_improvement": -1.0,
                "recommended_next_action": "reject_or_redesign_targets",
            }
        ]
    )

    frame, summary = build_shadow_auto_first_divergence_run(
        demo,
        feature_rows=feature_rows,
        threshold_sweep=threshold_sweep,
    )

    assert len(frame) == 1
    assert summary["selected_sweep_profile_id"] == "threshold::0.55::0.55"
    assert summary["run_decision"] == "reject_preview_candidate"
    assert summary["new_false_positive_count"] == 1


def test_build_shadow_auto_first_divergence_run_prefers_best_noncarry_profile() -> None:
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
    threshold_sweep = pd.DataFrame(
        [
            {
                "sweep_profile_id": "threshold::aggressive",
                "timing_threshold": 0.35,
                "entry_quality_threshold": 0.35,
                "divergence_rate": 1.0,
                "manual_alignment_improvement": -1.0,
                "mapped_alignment_improvement": 1.0,
                "value_diff_proxy": 0.0,
                "drawdown_diff": 0.0,
                "new_false_positive_count": 5,
                "recommended_next_action": "reject_or_redesign_targets",
            },
            {
                "sweep_profile_id": "threshold::conservative",
                "timing_threshold": 0.95,
                "entry_quality_threshold": 0.95,
                "divergence_rate": 0.2,
                "manual_alignment_improvement": 0.1,
                "mapped_alignment_improvement": 0.1,
                "value_diff_proxy": -0.1,
                "drawdown_diff": 0.0,
                "new_false_positive_count": 0,
                "recommended_next_action": "reject_threshold_profile",
            },
        ]
    )

    _frame, summary = build_shadow_auto_first_divergence_run(
        demo,
        feature_rows=feature_rows,
        threshold_sweep=threshold_sweep,
    )

    assert summary["selected_sweep_profile_id"] == "threshold::conservative"
    assert summary["selection_reason"] == "selected_best_noncarry_profile"


def test_build_shadow_auto_first_divergence_run_excludes_freeze_family_rows() -> None:
    demo = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "baseline_realized_value": 0.2,
                "target_timing_now_vs_wait": 0,
                "target_exit_management": 0,
                "shadow_timing_probability": 0.2,
                "shadow_entry_quality_probability": 0.9,
                "shadow_exit_management_probability": 0.1,
            },
            {
                "bridge_decision_time": "2026-04-08T10:01:00+09:00",
                "symbol": "BTCUSD",
                "baseline_action": "",
                "baseline_outcome": "wait",
                "baseline_realized_value": 0.2,
                "target_timing_now_vs_wait": 0,
                "target_exit_management": 0,
                "shadow_timing_probability": 0.2,
                "shadow_entry_quality_probability": 0.9,
                "shadow_exit_management_probability": 0.1,
            },
        ]
    )
    feature_rows = pd.DataFrame(
        [
            {
                "bridge_decision_time": "2026-04-08T10:00:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "insufficient_evidence",
                "learning_total_label": "positive",
                "signed_exit_score": 50.0,
                "wait_bias_hint": "wait",
                "scene_family": "pattern_1",
            },
            {
                "bridge_decision_time": "2026-04-08T10:01:00+09:00",
                "symbol": "BTCUSD",
                "entry_wait_quality_label": "skip",
                "manual_wait_teacher_usage_bucket": "diagnostic",
                "scene_family": "unknown",
            },
        ]
    )
    threshold_sweep = pd.DataFrame(
        [
            {
                "sweep_profile_id": "threshold::candidate",
                "timing_threshold": 0.35,
                "entry_quality_threshold": 0.35,
                "exit_management_threshold": 0.65,
                "divergence_rate": 1.0,
                "manual_alignment_improvement": 0.0,
                "mapped_alignment_improvement": 0.0,
                "value_diff_proxy": 0.0,
                "drawdown_diff": 0.0,
                "new_false_positive_count": 0,
                "recommended_next_action": "carry_forward_to_divergence_run",
            }
        ]
    )

    frame, summary = build_shadow_auto_first_divergence_run(
        demo,
        feature_rows=feature_rows,
        threshold_sweep=threshold_sweep,
    )

    assert len(frame) == 1
    assert summary["row_count"] == 1
    assert frame.iloc[0]["bridge_decision_time"] == "2026-04-08T10:01:00+09:00"
