from pathlib import Path
import json

import pandas as pd

from backend.services.teacher_pattern_candidate_pipeline import (
    build_teacher_pattern_candidate_compare_report,
    build_teacher_pattern_candidate_promotion_decision,
    run_teacher_pattern_candidate_pipeline,
)


def _report(
    *,
    group_macro: float,
    pattern_macro: float,
    economic_macro: float,
    forecast_transition_macro: float | None = None,
    forecast_management_macro: float | None = None,
    belief_macro: float | None = None,
    baseline_ready: bool = True,
    group_weighted: float | None = None,
    group_accuracy: float | None = None,
    group_balanced: float | None = None,
    group_test_support: dict | None = None,
    group_top_confusions: list | None = None,
    pattern_weighted: float | None = None,
    pattern_accuracy: float | None = None,
    pattern_balanced: float | None = None,
    pattern_test_support: dict | None = None,
    pattern_top_confusions: list | None = None,
    forecast_transition_ready: bool = False,
    forecast_management_ready: bool = False,
    belief_ready: bool = False,
    belief_target_rows: int = 0,
    belief_high_medium_rows: int = 0,
    belief_wrong_hold_ratio: float = 0.0,
    belief_premature_flip_ratio: float = 0.0,
    belief_missed_flip_ratio: float = 0.0,
    belief_high_confidence_share: float = 0.0,
    barrier_macro: float | None = None,
    barrier_ready: bool = False,
    barrier_target_rows: int = 0,
    barrier_high_medium_rows: int = 0,
    barrier_usable_rows: int | None = None,
    barrier_overblock_ratio: float = 0.0,
    barrier_avoided_loss_ratio: float = 0.0,
    barrier_missed_profit_ratio: float = 0.0,
    barrier_correct_wait_ratio: float = 0.0,
    barrier_relief_failure_ratio: float = 0.0,
    barrier_loss_avoided_r_mean: float = 0.0,
    barrier_profit_missed_r_mean: float = 0.0,
    barrier_wait_value_r_mean: float = 0.0,
) -> dict:
    group_weighted = group_macro if group_weighted is None else group_weighted
    group_accuracy = group_macro if group_accuracy is None else group_accuracy
    group_balanced = group_macro if group_balanced is None else group_balanced
    pattern_weighted = pattern_macro if pattern_weighted is None else pattern_weighted
    pattern_accuracy = pattern_macro if pattern_accuracy is None else pattern_accuracy
    pattern_balanced = pattern_macro if pattern_balanced is None else pattern_balanced
    barrier_usable_rows = barrier_high_medium_rows if barrier_usable_rows is None else barrier_usable_rows
    barrier_weak_usable_rows = max(int(barrier_usable_rows) - int(barrier_high_medium_rows), 0)
    barrier_weak_usable_share = float(barrier_weak_usable_rows / barrier_usable_rows) if barrier_usable_rows else 0.0
    barrier_weak_to_medium_conversion_rate = (
        float(barrier_high_medium_rows / barrier_usable_rows) if barrier_usable_rows else 0.0
    )
    return {
        "baseline_ready": baseline_ready,
        "seed_summary": {
            "labeled_rows": 1200,
            "belief_outcome_coverage": {
                "rows_with_belief_outcome": belief_target_rows,
                "high_or_medium_confidence_rows": belief_high_medium_rows,
                "label_distribution": {
                    "wrong_hold": {"count": int(round(belief_target_rows * belief_wrong_hold_ratio)), "ratio": belief_wrong_hold_ratio},
                    "premature_flip": {
                        "count": int(round(belief_target_rows * belief_premature_flip_ratio)),
                        "ratio": belief_premature_flip_ratio,
                    },
                    "missed_flip": {
                        "count": int(round(belief_target_rows * belief_missed_flip_ratio)),
                        "ratio": belief_missed_flip_ratio,
                    },
                },
                "confidence_distribution": {
                    "high": {
                        "count": int(round(belief_target_rows * belief_high_confidence_share)),
                        "ratio": belief_high_confidence_share,
                    }
                },
            },
            "barrier_outcome_coverage": {
                "rows_with_barrier_outcome": barrier_target_rows,
                "high_or_medium_confidence_rows": barrier_high_medium_rows,
                "usable_confidence_rows": barrier_usable_rows,
                "weak_usable_rows": barrier_weak_usable_rows,
                "weak_usable_share": barrier_weak_usable_share,
                "weak_to_medium_conversion_rate": barrier_weak_to_medium_conversion_rate,
                "label_distribution": {
                    "overblock": {"count": int(round(barrier_target_rows * barrier_overblock_ratio)), "ratio": barrier_overblock_ratio},
                    "avoided_loss": {"count": int(round(barrier_target_rows * barrier_avoided_loss_ratio)), "ratio": barrier_avoided_loss_ratio},
                    "missed_profit": {"count": int(round(barrier_target_rows * barrier_missed_profit_ratio)), "ratio": barrier_missed_profit_ratio},
                    "correct_wait": {"count": int(round(barrier_target_rows * barrier_correct_wait_ratio)), "ratio": barrier_correct_wait_ratio},
                    "relief_failure": {
                        "count": int(round(barrier_target_rows * barrier_relief_failure_ratio)),
                        "ratio": barrier_relief_failure_ratio,
                    },
                },
                "loss_avoided_r_mean": barrier_loss_avoided_r_mean,
                "profit_missed_r_mean": barrier_profit_missed_r_mean,
                "wait_value_r_mean": barrier_wait_value_r_mean,
            },
        },
        "economic_target_integration": {
            "ready": True,
        },
        "belief_outcome_integration": {
            "ready": belief_ready,
            "target_rows": belief_target_rows,
            "high_medium_confidence_rows": belief_high_medium_rows,
        },
        "barrier_outcome_integration": {
            "ready": barrier_ready,
            "target_rows": barrier_target_rows,
            "high_medium_confidence_rows": barrier_high_medium_rows,
            "usable_confidence_rows": barrier_usable_rows,
        },
        "tasks": {
            "group_task": {
                "rows": 100,
                "skipped": False,
                "model_metrics": {
                    "test": {
                        "macro_f1": group_macro,
                        "balanced_accuracy": group_balanced,
                        "accuracy": group_accuracy,
                        "weighted_f1": group_weighted,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.33,
                        "balanced_accuracy": 0.33,
                        "accuracy": 0.33,
                        "weighted_f1": 0.33,
                    }
                },
                "class_support": {
                    "test": group_test_support or {"A": 60, "D": 30, "E": 10},
                },
                "top_confusions": group_top_confusions or [],
            },
            "pattern_task": {
                "rows": 100,
                "skipped": False,
                "supported_pattern_ids": [1, 5, 9],
                "model_metrics": {
                    "test": {
                        "macro_f1": pattern_macro,
                        "balanced_accuracy": pattern_balanced,
                        "accuracy": pattern_accuracy,
                        "weighted_f1": pattern_weighted,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.20,
                        "balanced_accuracy": 0.20,
                        "accuracy": 0.20,
                        "weighted_f1": 0.20,
                    }
                },
                "class_support": {
                    "test": pattern_test_support or {"1": 20, "5": 18, "9": 12},
                },
                "top_confusions": pattern_top_confusions or [],
            },
            "economic_total_task": {
                "rows": 100,
                "target_rows": 100,
                "skipped": False,
                "supported_labels": ["negative", "neutral", "positive"],
                "model_metrics": {"test": {"macro_f1": economic_macro, "balanced_accuracy": economic_macro}},
                "dummy_metrics": {"test": {"macro_f1": 0.33, "balanced_accuracy": 0.33}},
            },
            "wait_quality_task": {
                "rows": 0,
                "target_rows": 0,
                "skipped": True,
            },
            "belief_outcome_task": {
                "rows": belief_high_medium_rows if belief_ready else 0,
                "target_rows": belief_target_rows,
                "skipped": not belief_ready,
                "supported_labels": ["correct_hold", "wrong_hold"] if belief_ready else [],
                "model_metrics": {
                    "test": {
                        "macro_f1": belief_macro if belief_macro is not None else 0.0,
                        "balanced_accuracy": belief_macro if belief_macro is not None else 0.0,
                        "accuracy": belief_macro if belief_macro is not None else 0.0,
                        "weighted_f1": belief_macro if belief_macro is not None else 0.0,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.50,
                        "balanced_accuracy": 0.50,
                        "accuracy": 0.50,
                        "weighted_f1": 0.50,
                    }
                },
            },
            "barrier_outcome_task": {
                "rows": barrier_high_medium_rows if barrier_ready else 0,
                "target_rows": barrier_target_rows,
                "skipped": not barrier_ready,
                "supported_labels": ["avoided_loss", "overblock"] if barrier_ready else [],
                "model_metrics": {
                    "test": {
                        "macro_f1": barrier_macro if barrier_macro is not None else 0.0,
                        "balanced_accuracy": barrier_macro if barrier_macro is not None else 0.0,
                        "accuracy": barrier_macro if barrier_macro is not None else 0.0,
                        "weighted_f1": barrier_macro if barrier_macro is not None else 0.0,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.50,
                        "balanced_accuracy": 0.50,
                        "accuracy": 0.50,
                        "weighted_f1": 0.50,
                    }
                },
            },
            "forecast_transition_task": {
                "rows": 20 if forecast_transition_ready else 0,
                "target_rows": 20 if forecast_transition_ready else 0,
                "skipped": not forecast_transition_ready,
                "supported_labels": ["confirm_failed", "confirm_success"] if forecast_transition_ready else [],
                "model_metrics": {
                    "test": {
                        "macro_f1": forecast_transition_macro if forecast_transition_macro is not None else 0.0,
                        "balanced_accuracy": forecast_transition_macro if forecast_transition_macro is not None else 0.0,
                        "accuracy": forecast_transition_macro if forecast_transition_macro is not None else 0.0,
                        "weighted_f1": forecast_transition_macro if forecast_transition_macro is not None else 0.0,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.50,
                        "balanced_accuracy": 0.50,
                        "accuracy": 0.50,
                        "weighted_f1": 0.50,
                    }
                },
            },
            "forecast_management_task": {
                "rows": 20 if forecast_management_ready else 0,
                "target_rows": 20 if forecast_management_ready else 0,
                "skipped": not forecast_management_ready,
                "supported_labels": ["cut_was_better", "hold_rewarded"] if forecast_management_ready else [],
                "model_metrics": {
                    "test": {
                        "macro_f1": forecast_management_macro if forecast_management_macro is not None else 0.0,
                        "balanced_accuracy": forecast_management_macro if forecast_management_macro is not None else 0.0,
                        "accuracy": forecast_management_macro if forecast_management_macro is not None else 0.0,
                        "weighted_f1": forecast_management_macro if forecast_management_macro is not None else 0.0,
                    }
                },
                "dummy_metrics": {
                    "test": {
                        "macro_f1": 0.50,
                        "balanced_accuracy": 0.50,
                        "accuracy": 0.50,
                        "weighted_f1": 0.50,
                    }
                },
            },
        },
        "forecast_transition_integration": {
            "ready": forecast_transition_ready,
            "target_rows": 20 if forecast_transition_ready else 0,
        },
        "forecast_management_integration": {
            "ready": forecast_management_ready,
            "target_rows": 20 if forecast_management_ready else 0,
        },
    }


def _row(index: int, *, symbol: str, group: str, pattern_id: int, direction: str, setup: str, learning_total_label: str, learning_total_score: float) -> dict:
    return {
        "ticket": 1000 + index,
        "symbol": symbol,
        "direction": direction,
        "entry_stage": "READY",
        "entry_setup_id": setup,
        "entry_wait_state": "NONE",
        "regime_at_entry": "NORMAL",
        "entry_session_name": "LONDON",
        "entry_weekday": 2,
        "regime_name": "NORMAL",
        "micro_breakout_readiness_state": "READY_BREAKOUT",
        "micro_reversal_risk_state": "LOW",
        "micro_participation_state": "ACTIVE",
        "micro_gap_context_state": "NO_GAP",
        "entry_score": 0.8 if learning_total_label == "positive" else 0.2,
        "contra_score_at_entry": 0.2 if learning_total_label == "positive" else 0.8,
        "entry_model_confidence": 0.8,
        "entry_h1_context_score": 0.7,
        "entry_m1_trigger_score": 0.7,
        "entry_topdown_align_count": 3,
        "entry_topdown_conflict_count": 0,
        "entry_topdown_seen_count": 3,
        "entry_session_threshold_mult": 1.0,
        "entry_atr_ratio": 1.1,
        "entry_atr_threshold_mult": 1.0,
        "ind_rsi": 60,
        "ind_adx": 25,
        "ind_plus_di": 24,
        "ind_minus_di": 18,
        "ind_disparity": 1.1,
        "regime_volume_ratio": 1.3,
        "regime_volatility_ratio": 1.2,
        "regime_spread_ratio": 1.0,
        "regime_buy_multiplier": 1.0,
        "regime_sell_multiplier": 1.0,
        "micro_body_size_pct_20": 0.20,
        "micro_doji_ratio_20": 0.10,
        "micro_same_color_run_current": 4,
        "micro_same_color_run_max_20": 6,
        "micro_range_compression_ratio_20": 0.6,
        "micro_volume_burst_ratio_20": 1.9,
        "micro_volume_burst_decay_20": 0.2,
        "micro_gap_fill_progress": 0.0,
        "signal_age_sec": 20,
        "bar_age_sec": 10,
        "missing_feature_count": 0,
        "data_completeness_ratio": 1.0,
        "used_fallback_count": 0,
        "teacher_pattern_id": pattern_id,
        "teacher_pattern_group": group,
        "teacher_pattern_secondary_id": 0,
        "teacher_label_confidence": 0.82,
        "teacher_label_source": "rule_v2_backfill",
        "teacher_label_review_status": "backfilled_unreviewed",
        "teacher_lookback_bars": 20,
        "teacher_label_version": "state25_v2",
        "entry_wait_quality_label": "",
        "entry_wait_quality_score": 0.0,
        "entry_wait_quality_reason": "",
        "learning_total_label": learning_total_label,
        "learning_total_score": learning_total_score,
        "loss_quality_label": "non_loss" if learning_total_label == "positive" else "bad_loss",
        "loss_quality_score": 0.0,
        "signed_exit_score": 20.0 if learning_total_label == "positive" else -20.0,
        "profit": 2.0 if learning_total_label == "positive" else -2.0,
    }


def test_candidate_compare_report_captures_metric_delta():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        belief_macro=0.63,
        belief_ready=True,
        belief_target_rows=84,
        belief_high_medium_rows=52,
        belief_wrong_hold_ratio=0.12,
        belief_premature_flip_ratio=0.04,
        belief_missed_flip_ratio=0.08,
        belief_high_confidence_share=0.32,
        barrier_macro=0.61,
        barrier_ready=True,
        barrier_target_rows=84,
        barrier_high_medium_rows=52,
        barrier_usable_rows=64,
        barrier_overblock_ratio=0.05,
        barrier_avoided_loss_ratio=0.28,
        barrier_missed_profit_ratio=0.07,
        barrier_relief_failure_ratio=0.03,
        barrier_profit_missed_r_mean=0.18,
        forecast_transition_macro=0.66,
        forecast_management_macro=0.62,
        forecast_transition_ready=True,
        forecast_management_ready=True,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        belief_macro=0.60,
        belief_ready=True,
        belief_target_rows=80,
        belief_high_medium_rows=48,
        belief_wrong_hold_ratio=0.16,
        belief_premature_flip_ratio=0.02,
        belief_missed_flip_ratio=0.10,
        belief_high_confidence_share=0.22,
        barrier_macro=0.58,
        barrier_ready=True,
        barrier_target_rows=80,
        barrier_high_medium_rows=48,
        barrier_usable_rows=56,
        barrier_overblock_ratio=0.11,
        barrier_avoided_loss_ratio=0.20,
        barrier_missed_profit_ratio=0.12,
        barrier_relief_failure_ratio=0.08,
        barrier_profit_missed_r_mean=0.31,
        forecast_transition_macro=0.61,
        forecast_management_macro=0.60,
        forecast_transition_ready=True,
        forecast_management_ready=True,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)

    assert compare["reference_available"] is True
    assert compare["tasks"]["group_task"]["delta"]["macro_f1"] == 0.04
    assert compare["tasks"]["pattern_task"]["delta"]["macro_f1"] == 0.02
    assert compare["tasks"]["belief_outcome_task"]["delta"]["macro_f1"] == 0.03
    assert compare["belief_compare_summary"]["belief_ready_delta"]["target_rows_delta"] == 4
    assert compare["belief_compare_summary"]["belief_quality_delta"]["wrong_hold_ratio_delta"] == -0.04
    assert compare["tasks"]["barrier_outcome_task"]["delta"]["macro_f1"] == 0.03
    assert compare["barrier_compare_summary"]["barrier_ready_delta"]["target_rows_delta"] == 4
    assert compare["barrier_compare_summary"]["barrier_ready_delta"]["usable_confidence_rows_delta"] == 8
    assert compare["barrier_compare_summary"]["barrier_quality_delta"]["overblock_ratio_delta"] == -0.06
    assert compare["barrier_compare_summary"]["barrier_quality_delta"]["weak_usable_share_delta"] == 0.044643
    assert compare["barrier_compare_summary"]["barrier_quality_delta"]["weak_to_medium_conversion_rate_delta"] == -0.044643
    assert compare["tasks"]["forecast_transition_task"]["delta"]["macro_f1"] == 0.05
    assert compare["forecast_state25_compare_summary"]["transition_ready_delta"]["candidate_ready"] is True
    assert compare["forecast_state25_compare_summary"]["management_ready_delta"]["reference_ready"] is True


def test_candidate_promotion_decision_marks_review_ready_on_improvement():
    candidate = _report(group_macro=0.64, pattern_macro=0.72, economic_macro=0.58)
    reference = _report(group_macro=0.60, pattern_macro=0.70, economic_macro=0.54)

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "promote_review_ready"
    assert "group_task_macro_f1_improved" in decision["improvements"]


def test_candidate_promotion_decision_marks_log_only_ready_on_soft_regression():
    candidate = _report(group_macro=0.57, pattern_macro=0.66, economic_macro=0.53)
    reference = _report(group_macro=0.60, pattern_macro=0.72, economic_macro=0.54)

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "group_task_macro_f1_soft_regression" in decision["warnings"]
    assert "pattern_task_macro_f1_soft_regression" in decision["warnings"]


def test_candidate_promotion_decision_holds_on_primary_regression():
    candidate = _report(group_macro=0.40, pattern_macro=0.72, economic_macro=0.58)
    reference = _report(group_macro=0.60, pattern_macro=0.70, economic_macro=0.54)

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "hold_regression"
    assert "group_task_macro_f1_regressed" in decision["blockers"]


def test_candidate_promotion_decision_downgrades_pattern_macro_regression_when_only_rare_classes_move():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.88,
        pattern_weighted=0.989,
        pattern_accuracy=0.988,
        pattern_balanced=0.96,
        pattern_test_support={"1": 182, "5": 120, "9": 4, "11": 1, "14": 81, "21": 2, "25": 11},
        pattern_top_confusions=[{"true_label": "5", "pred_label": "21", "count": 2}],
        economic_macro=0.58,
    )
    reference = _report(
        group_macro=0.64,
        pattern_macro=1.0,
        pattern_weighted=1.0,
        pattern_accuracy=1.0,
        pattern_balanced=1.0,
        pattern_test_support={"1": 182, "5": 109, "9": 4, "11": 1, "14": 82, "21": 2, "25": 11},
        pattern_top_confusions=[],
        economic_macro=0.54,
    )
    candidate["tasks"]["pattern_task"]["supported_pattern_ids"] = [1, 5, 9, 11, 14, 21, 25]
    reference["tasks"]["pattern_task"]["supported_pattern_ids"] = [1, 5, 9, 11, 14, 21, 25]

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "pattern_task_macro_f1_rare_class_soft_regression" in decision["warnings"]
    assert "economic_total_task_macro_f1_improved" in decision["improvements"]


def test_candidate_promotion_decision_downgrades_group_macro_regression_when_only_rare_classes_move():
    candidate = _report(
        group_macro=0.7490566037735849,
        group_weighted=0.9962733502299822,
        group_accuracy=0.9975124378109452,
        group_balanced=0.75,
        group_test_support={"A": 265, "C": 1, "D": 132, "E": 4},
        group_top_confusions=[{"true_label": "C", "pred_label": "D", "count": 1}],
        pattern_macro=0.93,
        economic_macro=0.58,
    )
    reference = _report(
        group_macro=1.0,
        group_weighted=1.0,
        group_accuracy=1.0,
        group_balanced=1.0,
        group_test_support={"A": 265, "D": 124, "E": 2},
        group_top_confusions=[],
        pattern_macro=0.93,
        economic_macro=0.54,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "group_task_macro_f1_rare_class_soft_regression" in decision["warnings"]
    assert "economic_total_task_macro_f1_improved" in decision["improvements"]


def test_candidate_promotion_decision_treats_forecast_auxiliary_regression_as_warning_only():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        forecast_transition_macro=0.30,
        forecast_management_macro=0.32,
        forecast_transition_ready=True,
        forecast_management_ready=True,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        forecast_transition_macro=0.50,
        forecast_management_macro=0.50,
        forecast_transition_ready=True,
        forecast_management_ready=True,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "forecast_transition_macro_f1_hard_regression" in decision["warnings"]
    assert "forecast_management_macro_f1_hard_regression" in decision["warnings"]
    assert all("forecast_transition" not in blocker for blocker in decision["blockers"])


def test_candidate_promotion_decision_treats_belief_auxiliary_regression_as_warning_only():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        belief_macro=0.30,
        belief_ready=True,
        belief_target_rows=84,
        belief_high_medium_rows=52,
        belief_wrong_hold_ratio=0.18,
        belief_premature_flip_ratio=0.05,
        belief_missed_flip_ratio=0.12,
        belief_high_confidence_share=0.10,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        belief_macro=0.50,
        belief_ready=True,
        belief_target_rows=80,
        belief_high_medium_rows=48,
        belief_wrong_hold_ratio=0.10,
        belief_premature_flip_ratio=0.01,
        belief_missed_flip_ratio=0.04,
        belief_high_confidence_share=0.22,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "belief_outcome_macro_f1_hard_regression" in decision["warnings"]
    assert "belief_wrong_hold_ratio_up" in decision["warnings"]
    assert "belief_high_confidence_share_down" in decision["warnings"]
    assert all("belief" not in blocker for blocker in decision["blockers"])


def test_candidate_promotion_decision_blocks_on_belief_premature_flip_spike():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        belief_macro=0.52,
        belief_ready=True,
        belief_target_rows=84,
        belief_high_medium_rows=52,
        belief_wrong_hold_ratio=0.08,
        belief_premature_flip_ratio=0.18,
        belief_missed_flip_ratio=0.06,
        belief_high_confidence_share=0.24,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        belief_macro=0.50,
        belief_ready=True,
        belief_target_rows=80,
        belief_high_medium_rows=48,
        belief_wrong_hold_ratio=0.10,
        belief_premature_flip_ratio=0.02,
        belief_missed_flip_ratio=0.08,
        belief_high_confidence_share=0.20,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "hold_regression"
    assert "belief_premature_flip_ratio_spike" in decision["blockers"]


def test_candidate_promotion_decision_treats_barrier_auxiliary_regression_as_warning_only():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        barrier_macro=0.30,
        barrier_ready=True,
        barrier_target_rows=84,
        barrier_high_medium_rows=52,
        barrier_overblock_ratio=0.12,
        barrier_avoided_loss_ratio=0.18,
        barrier_missed_profit_ratio=0.18,
        barrier_relief_failure_ratio=0.09,
        barrier_profit_missed_r_mean=0.34,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        barrier_macro=0.50,
        barrier_ready=True,
        barrier_target_rows=80,
        barrier_high_medium_rows=48,
        barrier_overblock_ratio=0.08,
        barrier_avoided_loss_ratio=0.22,
        barrier_missed_profit_ratio=0.10,
        barrier_relief_failure_ratio=0.04,
        barrier_profit_missed_r_mean=0.22,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "log_only_review_ready"
    assert "barrier_outcome_macro_f1_hard_regression" in decision["warnings"]
    assert "barrier_missed_profit_rate_up" in decision["warnings"]
    assert "barrier_profit_missed_r_mean_up" in decision["warnings"]
    assert all("barrier_" not in blocker for blocker in decision["blockers"])


def test_candidate_promotion_decision_blocks_on_barrier_overblock_spike():
    candidate = _report(
        group_macro=0.64,
        pattern_macro=0.72,
        economic_macro=0.58,
        barrier_macro=0.52,
        barrier_ready=True,
        barrier_target_rows=84,
        barrier_high_medium_rows=52,
        barrier_overblock_ratio=0.24,
        barrier_avoided_loss_ratio=0.24,
        barrier_missed_profit_ratio=0.06,
        barrier_relief_failure_ratio=0.03,
    )
    reference = _report(
        group_macro=0.60,
        pattern_macro=0.70,
        economic_macro=0.54,
        barrier_macro=0.50,
        barrier_ready=True,
        barrier_target_rows=80,
        barrier_high_medium_rows=48,
        barrier_overblock_ratio=0.06,
        barrier_avoided_loss_ratio=0.20,
        barrier_missed_profit_ratio=0.08,
        barrier_relief_failure_ratio=0.02,
    )

    compare = build_teacher_pattern_candidate_compare_report(candidate, reference)
    decision = build_teacher_pattern_candidate_promotion_decision(candidate, compare)

    assert decision["decision"] == "hold_regression"
    assert "barrier_overblock_ratio_spike" in decision["blockers"]


def test_run_candidate_pipeline_writes_manifest_and_reports(tmp_path: Path):
    rows = []
    for i in range(6):
        rows.append(_row(i, symbol="BTCUSD", group="A", pattern_id=1, direction="BUY", setup="range_idle", learning_total_label="positive", learning_total_score=0.42))
        rows.append(_row(100 + i, symbol="NAS100", group="D", pattern_id=5, direction="SELL", setup="range_reject", learning_total_label="negative", learning_total_score=-0.33))
        rows.append(_row(200 + i, symbol="XAUUSD", group="A", pattern_id=14, direction="BUY", setup="morning_breakout", learning_total_label="neutral", learning_total_score=0.0))
    frame = pd.DataFrame(rows)

    reference = _report(group_macro=0.50, pattern_macro=0.50, economic_macro=0.45)
    reference_path = tmp_path / "reference_metrics.json"
    reference_path.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = run_teacher_pattern_candidate_pipeline(
        frame,
        csv_path=tmp_path / "seed.csv",
        candidate_root=tmp_path / "candidates",
        reference_metrics_path=reference_path,
        min_seed_rows=6,
        pattern_min_support=2,
        wait_quality_min_support=2,
        economic_target_min_support=2,
    )

    assert Path(manifest["candidate_metrics_path"]).exists()
    assert Path(manifest["compare_report_path"]).exists()
    assert Path(manifest["promotion_decision_path"]).exists()
    assert Path(manifest["summary_md_path"]).exists()
    assert Path(tmp_path / "candidates" / "latest_candidate_run.json").exists()
