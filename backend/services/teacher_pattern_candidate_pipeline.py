"""Candidate retrain / compare / promote scaffold for state25 pilot models."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.teacher_pattern_pilot_baseline import (
    DEFAULT_BARRIER_OUTCOME_MIN_ROWS,
    DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT,
    DEFAULT_BELIEF_OUTCOME_MIN_ROWS,
    DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT,
    DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT,
    DEFAULT_MIN_SEED_ROWS,
    DEFAULT_PATTERN_MIN_SUPPORT,
    DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
    build_teacher_pattern_pilot_baseline_report,
)


DEFAULT_CANDIDATE_ROOT = Path("models") / "teacher_pattern_state25_candidates"
DEFAULT_CURRENT_BASELINE_DIR = Path("models") / "teacher_pattern_state25_pilot"
TASK_NAMES = (
    "group_task",
    "pattern_task",
    "economic_total_task",
    "wait_quality_task",
    "belief_outcome_task",
    "barrier_outcome_task",
    "forecast_transition_task",
    "forecast_management_task",
)
PRIMARY_PROMOTION_TASKS = ("group_task", "pattern_task", "economic_total_task")
FORECAST_AUXILIARY_TASKS = ("forecast_transition_task", "forecast_management_task")
BELIEF_AUXILIARY_TASKS = ("belief_outcome_task",)
BARRIER_AUXILIARY_TASKS = ("barrier_outcome_task",)
METRIC_NAMES = ("macro_f1", "balanced_accuracy", "accuracy", "weighted_f1")
DELTA_HARD = -0.10
DELTA_OK = -0.02
DELTA_WARN = -0.05
BELIEF_PREMATURE_FLIP_HARD_DELTA = 0.10
BELIEF_WARNING_RATIO_DELTA = 0.05
BELIEF_IMPROVEMENT_RATIO_DELTA = -0.03
BELIEF_HIGH_CONFIDENCE_SHARE_WARN_DELTA = -0.05
BELIEF_HIGH_CONFIDENCE_SHARE_IMPROVE_DELTA = 0.05
BARRIER_OVERBLOCK_HARD_DELTA = 0.10
BARRIER_RELIEF_FAILURE_HARD_DELTA = 0.10
BARRIER_WARNING_RATIO_DELTA = 0.05
BARRIER_IMPROVEMENT_RATIO_DELTA = -0.03
BARRIER_COST_WARN_DELTA = 0.10
BARRIER_COST_IMPROVEMENT_DELTA = -0.05


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    json_path = Path(path)
    if not json_path.exists():
        return {}
    return dict(json.loads(json_path.read_text(encoding="utf-8")) or {})


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object) -> bool:
    return bool(value)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _task_payload(report: dict[str, Any], task_name: str) -> dict[str, Any]:
    return dict(((report.get("tasks", {}) or {}).get(task_name, {})) or {})


def _task_ready(report: dict[str, Any], task_name: str) -> bool:
    task = _task_payload(report, task_name)
    return bool(task and not _to_bool(task.get("skipped", True)))


def _metric_summary(report: dict[str, Any], task_name: str) -> dict[str, Any]:
    task = _task_payload(report, task_name)
    metrics = dict((task.get("model_metrics", {}) or {}).get("test", {}) or {})
    dummy = dict((task.get("dummy_metrics", {}) or {}).get("test", {}) or {})
    return {
        "ready": bool(task and not _to_bool(task.get("skipped", True))),
        "rows": int(task.get("rows", 0) or 0),
        "target_rows": int(task.get("target_rows", task.get("rows", 0)) or 0),
        "metrics": {name: _to_float(metrics.get(name), 0.0) for name in METRIC_NAMES},
        "dummy_metrics": {name: _to_float(dummy.get(name), 0.0) for name in METRIC_NAMES},
        "supported_labels": list(task.get("supported_labels", task.get("supported_pattern_ids", [])) or []),
        "class_support_test": dict(((task.get("class_support", {}) or {}).get("test", {})) or {}),
        "top_confusions": list(task.get("top_confusions", []) or []),
    }


def _belief_ratio_from_coverage(coverage: dict[str, Any], label: str) -> float:
    distribution = dict((coverage.get("label_distribution", {}) or {}).get(label, {}) or {})
    if distribution:
        ratio = distribution.get("ratio")
        if ratio not in ("", None):
            return _to_float(ratio, 0.0)
    total_rows = _to_int(coverage.get("rows_with_belief_outcome", 0), 0)
    count = _to_int(distribution.get("count", 0), 0)
    return float(count / total_rows) if total_rows else 0.0


def _belief_high_confidence_share(coverage: dict[str, Any]) -> float:
    confidence_distribution = dict((coverage.get("confidence_distribution", {}) or {}).get("high", {}) or {})
    if confidence_distribution:
        ratio = confidence_distribution.get("ratio")
        if ratio not in ("", None):
            return _to_float(ratio, 0.0)
    total_rows = _to_int(coverage.get("rows_with_belief_outcome", 0), 0)
    high_count = _to_int(confidence_distribution.get("count", 0), 0)
    return float(high_count / total_rows) if total_rows else 0.0


def _barrier_ratio_from_coverage(coverage: dict[str, Any], label: str) -> float:
    distribution = dict((coverage.get("label_distribution", {}) or {}).get(label, {}) or {})
    if distribution:
        ratio = distribution.get("ratio")
        if ratio not in ("", None):
            return _to_float(ratio, 0.0)
    total_rows = _to_int(coverage.get("rows_with_barrier_outcome", 0), 0)
    count = _to_int(distribution.get("count", 0), 0)
    return float(count / total_rows) if total_rows else 0.0


def _barrier_cost_mean(coverage: dict[str, Any], field_name: str) -> float:
    return _to_float(coverage.get(field_name, 0.0), 0.0)


def _barrier_weak_usable_share(coverage: dict[str, Any]) -> float:
    explicit = coverage.get("weak_usable_share")
    if explicit not in ("", None):
        return _to_float(explicit, 0.0)
    usable_rows = _to_int(
        coverage.get("usable_confidence_rows", coverage.get("high_or_medium_confidence_rows", 0)),
        0,
    )
    weak_rows = _to_int(
        coverage.get(
            "weak_usable_rows",
            dict((coverage.get("confidence_distribution", {}) or {}).get("weak_usable", {}) or {}).get("count", 0),
        ),
        0,
    )
    return float(weak_rows / usable_rows) if usable_rows else 0.0


def _barrier_weak_to_medium_conversion_rate(coverage: dict[str, Any]) -> float:
    explicit = coverage.get("weak_to_medium_conversion_rate")
    if explicit not in ("", None):
        return _to_float(explicit, 0.0)
    usable_rows = _to_int(
        coverage.get("usable_confidence_rows", coverage.get("high_or_medium_confidence_rows", 0)),
        0,
    )
    strict_rows = _to_int(coverage.get("high_or_medium_confidence_rows", 0), 0)
    return float(strict_rows / usable_rows) if usable_rows else 0.0


def _pattern_task_regression_is_soft(task: dict[str, Any]) -> bool:
    candidate = dict(task.get("candidate", {}) or {})
    reference = dict(task.get("reference", {}) or {})
    delta = dict(task.get("delta", {}) or {})
    if _to_float(delta.get("macro_f1"), 0.0) >= DELTA_HARD:
        return False

    candidate_labels = sorted(str(label) for label in candidate.get("supported_labels", []) or [])
    reference_labels = sorted(str(label) for label in reference.get("supported_labels", []) or [])
    if not candidate_labels or candidate_labels != reference_labels:
        return False

    if _to_float(delta.get("weighted_f1"), 0.0) < -0.02:
        return False
    if _to_float(delta.get("accuracy"), 0.0) < -0.02:
        return False
    if _to_float(delta.get("balanced_accuracy"), 0.0) < -0.05:
        return False

    candidate_support = {
        str(label): int(count)
        for label, count in dict(candidate.get("class_support_test", {}) or {}).items()
    }
    reference_support = {
        str(label): int(count)
        for label, count in dict(reference.get("class_support_test", {}) or {}).items()
    }
    rare_labels = [
        label
        for label in candidate_labels
        if 0 < int(candidate_support.get(label, 0)) <= 4 or 0 < int(reference_support.get(label, 0)) <= 4
    ]
    if len(rare_labels) < 2:
        return False

    max_confusion = max(
        (int(item.get("count", 0) or 0) for item in list(candidate.get("top_confusions", []) or [])),
        default=0,
    )
    return bool(max_confusion <= 2)


def _group_task_regression_is_soft(task: dict[str, Any]) -> bool:
    candidate = dict(task.get("candidate", {}) or {})
    reference = dict(task.get("reference", {}) or {})
    delta = dict(task.get("delta", {}) or {})
    if _to_float(delta.get("macro_f1"), 0.0) >= DELTA_HARD:
        return False

    if _to_float(delta.get("weighted_f1"), 0.0) < -0.02:
        return False
    if _to_float(delta.get("accuracy"), 0.0) < -0.02:
        return False
    if _to_float(delta.get("balanced_accuracy"), 0.0) < -0.30:
        return False

    candidate_support = {
        str(label): int(count)
        for label, count in dict(candidate.get("class_support_test", {}) or {}).items()
    }
    reference_support = {
        str(label): int(count)
        for label, count in dict(reference.get("class_support_test", {}) or {}).items()
    }
    label_union = sorted(set(candidate_support) | set(reference_support))
    if not label_union:
        return False

    rare_labels = [
        label
        for label in label_union
        if 0 < int(candidate_support.get(label, 0)) <= 4 or 0 < int(reference_support.get(label, 0)) <= 4
    ]
    if len(rare_labels) < 2:
        return False

    significant_only_candidate = [
        label
        for label in label_union
        if int(candidate_support.get(label, 0)) > 4 and int(reference_support.get(label, 0)) == 0
    ]
    significant_only_reference = [
        label
        for label in label_union
        if int(reference_support.get(label, 0)) > 4 and int(candidate_support.get(label, 0)) == 0
    ]
    if significant_only_candidate or significant_only_reference:
        return False

    max_confusion = max(
        (int(item.get("count", 0) or 0) for item in list(candidate.get("top_confusions", []) or [])),
        default=0,
    )
    return bool(max_confusion <= 2)


def build_teacher_pattern_candidate_compare_report(
    candidate_report: dict[str, Any],
    reference_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference = dict(reference_report or {})
    comparison_tasks: dict[str, Any] = {}

    for task_name in TASK_NAMES:
        candidate_summary = _metric_summary(candidate_report, task_name)
        reference_summary = _metric_summary(reference, task_name)
        delta = {
            metric_name: round(
                candidate_summary["metrics"][metric_name] - reference_summary["metrics"][metric_name],
                6,
            )
            for metric_name in METRIC_NAMES
        }
        comparison_tasks[task_name] = {
            "candidate": candidate_summary,
            "reference": reference_summary,
            "delta": delta,
        }

    candidate_seed = dict(candidate_report.get("seed_summary", {}) or {})
    reference_seed = dict(reference.get("seed_summary", {}) or {})
    candidate_economic = dict(candidate_report.get("economic_target_integration", {}) or {})
    reference_economic = dict(reference.get("economic_target_integration", {}) or {})
    candidate_belief = dict(candidate_report.get("belief_outcome_integration", {}) or {})
    reference_belief = dict(reference.get("belief_outcome_integration", {}) or {})
    candidate_belief_coverage = dict((candidate_seed.get("belief_outcome_coverage", {}) or {}) or {})
    reference_belief_coverage = dict((reference_seed.get("belief_outcome_coverage", {}) or {}) or {})
    candidate_forecast_transition = dict(candidate_report.get("forecast_transition_integration", {}) or {})
    reference_forecast_transition = dict(reference.get("forecast_transition_integration", {}) or {})
    candidate_forecast_management = dict(candidate_report.get("forecast_management_integration", {}) or {})
    reference_forecast_management = dict(reference.get("forecast_management_integration", {}) or {})
    candidate_barrier = dict(candidate_report.get("barrier_outcome_integration", {}) or {})
    reference_barrier = dict(reference.get("barrier_outcome_integration", {}) or {})
    candidate_barrier_coverage = dict((candidate_seed.get("barrier_outcome_coverage", {}) or {}) or {})
    reference_barrier_coverage = dict((reference_seed.get("barrier_outcome_coverage", {}) or {}) or {})

    return {
        "contract_version": "teacher_pattern_candidate_compare_v1",
        "reference_available": bool(reference),
        "reference_baseline_ready": bool(reference.get("baseline_ready", False)),
        "candidate_baseline_ready": bool(candidate_report.get("baseline_ready", False)),
        "seed_delta": {
            "labeled_rows": int((candidate_seed.get("labeled_rows", 0) or 0) - (reference_seed.get("labeled_rows", 0) or 0)),
            "supported_pattern_count": int(
                len((_task_payload(candidate_report, "pattern_task").get("supported_pattern_ids", []) or []))
                - len((_task_payload(reference, "pattern_task").get("supported_pattern_ids", []) or []))
            ),
        },
        "economic_target_ready_delta": {
            "candidate_ready": bool(candidate_economic.get("ready", False)),
            "reference_ready": bool(reference_economic.get("ready", False)),
        },
        "belief_compare_summary": {
            "belief_ready_delta": {
                "candidate_ready": bool(candidate_belief.get("ready", False)),
                "reference_ready": bool(reference_belief.get("ready", False)),
                "target_rows_delta": int(
                    _to_int(candidate_belief.get("target_rows", 0), 0)
                    - _to_int(reference_belief.get("target_rows", 0), 0)
                ),
                "high_medium_confidence_rows_delta": int(
                    _to_int(candidate_belief.get("high_medium_confidence_rows", 0), 0)
                    - _to_int(reference_belief.get("high_medium_confidence_rows", 0), 0)
                ),
                "usable_confidence_rows_delta": int(
                    _to_int(candidate_belief.get("usable_confidence_rows", 0), 0)
                    - _to_int(reference_belief.get("usable_confidence_rows", 0), 0)
                ),
            },
            "belief_quality_delta": {
                "wrong_hold_ratio_delta": round(
                    _belief_ratio_from_coverage(candidate_belief_coverage, "wrong_hold")
                    - _belief_ratio_from_coverage(reference_belief_coverage, "wrong_hold"),
                    6,
                ),
                "premature_flip_ratio_delta": round(
                    _belief_ratio_from_coverage(candidate_belief_coverage, "premature_flip")
                    - _belief_ratio_from_coverage(reference_belief_coverage, "premature_flip"),
                    6,
                ),
                "missed_flip_ratio_delta": round(
                    _belief_ratio_from_coverage(candidate_belief_coverage, "missed_flip")
                    - _belief_ratio_from_coverage(reference_belief_coverage, "missed_flip"),
                    6,
                ),
                "high_confidence_share_delta": round(
                    _belief_high_confidence_share(candidate_belief_coverage)
                    - _belief_high_confidence_share(reference_belief_coverage),
                    6,
                ),
            },
        },
        "barrier_compare_summary": {
            "barrier_ready_delta": {
                "candidate_ready": bool(candidate_barrier.get("ready", False)),
                "reference_ready": bool(reference_barrier.get("ready", False)),
                "target_rows_delta": int(
                    _to_int(candidate_barrier.get("target_rows", 0), 0)
                    - _to_int(reference_barrier.get("target_rows", 0), 0)
                ),
                "high_medium_confidence_rows_delta": int(
                    _to_int(candidate_barrier.get("high_medium_confidence_rows", 0), 0)
                    - _to_int(reference_barrier.get("high_medium_confidence_rows", 0), 0)
                ),
                "usable_confidence_rows_delta": int(
                    _to_int(
                        candidate_barrier.get("usable_confidence_rows", candidate_barrier.get("high_medium_confidence_rows", 0)),
                        0,
                    )
                    - _to_int(
                        reference_barrier.get("usable_confidence_rows", reference_barrier.get("high_medium_confidence_rows", 0)),
                        0,
                    )
                ),
            },
            "barrier_quality_delta": {
                "overblock_ratio_delta": round(
                    _barrier_ratio_from_coverage(candidate_barrier_coverage, "overblock")
                    - _barrier_ratio_from_coverage(reference_barrier_coverage, "overblock"),
                    6,
                ),
                "avoided_loss_rate_delta": round(
                    _barrier_ratio_from_coverage(candidate_barrier_coverage, "avoided_loss")
                    - _barrier_ratio_from_coverage(reference_barrier_coverage, "avoided_loss"),
                    6,
                ),
                "missed_profit_rate_delta": round(
                    _barrier_ratio_from_coverage(candidate_barrier_coverage, "missed_profit")
                    - _barrier_ratio_from_coverage(reference_barrier_coverage, "missed_profit"),
                    6,
                ),
                "correct_wait_rate_delta": round(
                    _barrier_ratio_from_coverage(candidate_barrier_coverage, "correct_wait")
                    - _barrier_ratio_from_coverage(reference_barrier_coverage, "correct_wait"),
                    6,
                ),
                "relief_failure_rate_delta": round(
                    _barrier_ratio_from_coverage(candidate_barrier_coverage, "relief_failure")
                    - _barrier_ratio_from_coverage(reference_barrier_coverage, "relief_failure"),
                    6,
                ),
                "loss_avoided_r_mean_delta": round(
                    _barrier_cost_mean(candidate_barrier_coverage, "loss_avoided_r_mean")
                    - _barrier_cost_mean(reference_barrier_coverage, "loss_avoided_r_mean"),
                    6,
                ),
                "profit_missed_r_mean_delta": round(
                    _barrier_cost_mean(candidate_barrier_coverage, "profit_missed_r_mean")
                    - _barrier_cost_mean(reference_barrier_coverage, "profit_missed_r_mean"),
                    6,
                ),
                "wait_value_r_mean_delta": round(
                    _barrier_cost_mean(candidate_barrier_coverage, "wait_value_r_mean")
                    - _barrier_cost_mean(reference_barrier_coverage, "wait_value_r_mean"),
                    6,
                ),
                "weak_usable_share_delta": round(
                    _barrier_weak_usable_share(candidate_barrier_coverage)
                    - _barrier_weak_usable_share(reference_barrier_coverage),
                    6,
                ),
                "weak_to_medium_conversion_rate_delta": round(
                    _barrier_weak_to_medium_conversion_rate(candidate_barrier_coverage)
                    - _barrier_weak_to_medium_conversion_rate(reference_barrier_coverage),
                    6,
                ),
            },
        },
        "forecast_state25_compare_summary": {
            "transition_ready_delta": {
                "candidate_ready": bool(candidate_forecast_transition.get("ready", False)),
                "reference_ready": bool(reference_forecast_transition.get("ready", False)),
                "target_rows_delta": int(
                    _to_int(candidate_forecast_transition.get("target_rows", 0), 0)
                    - _to_int(reference_forecast_transition.get("target_rows", 0), 0)
                ),
            },
            "management_ready_delta": {
                "candidate_ready": bool(candidate_forecast_management.get("ready", False)),
                "reference_ready": bool(reference_forecast_management.get("ready", False)),
                "target_rows_delta": int(
                    _to_int(candidate_forecast_management.get("target_rows", 0), 0)
                    - _to_int(reference_forecast_management.get("target_rows", 0), 0)
                ),
            },
        },
        "tasks": comparison_tasks,
    }


def build_teacher_pattern_candidate_promotion_decision(
    candidate_report: dict[str, Any],
    compare_report: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    improvements: list[str] = []

    if not bool(candidate_report.get("baseline_ready", False)):
        blockers.append("candidate_baseline_not_ready")

    if not bool(compare_report.get("reference_available", False)):
        warnings.append("no_reference_baseline")
        return {
            "contract_version": "teacher_pattern_candidate_promote_decision_v1",
            "decision": "shadow_only_first_candidate",
            "recommended_action": "hold_for_reference_compare",
            "blockers": blockers,
            "warnings": warnings,
            "improvements": improvements,
        }

    for task_name in PRIMARY_PROMOTION_TASKS:
        task = dict((compare_report.get("tasks", {}) or {}).get(task_name, {}) or {})
        candidate = dict(task.get("candidate", {}) or {})
        reference = dict(task.get("reference", {}) or {})
        delta = dict(task.get("delta", {}) or {})
        metric_delta = _to_float(delta.get("macro_f1"), 0.0)

        if reference.get("ready") and not candidate.get("ready"):
            blockers.append(f"{task_name}_candidate_not_ready")
            continue
        if candidate.get("ready") and reference.get("ready"):
            if task_name == "group_task" and metric_delta < DELTA_HARD and _group_task_regression_is_soft(task):
                warnings.append("group_task_macro_f1_rare_class_soft_regression")
            elif task_name == "pattern_task" and metric_delta < DELTA_HARD and _pattern_task_regression_is_soft(task):
                warnings.append("pattern_task_macro_f1_rare_class_soft_regression")
            elif metric_delta < DELTA_HARD:
                blockers.append(f"{task_name}_macro_f1_regressed")
            elif metric_delta < DELTA_OK:
                warnings.append(f"{task_name}_macro_f1_soft_regression")
            elif metric_delta > 0.01:
                improvements.append(f"{task_name}_macro_f1_improved")
        elif candidate.get("ready") and not reference.get("ready"):
            improvements.append(f"{task_name}_new_ready_task")

    wait_task = dict((compare_report.get("tasks", {}) or {}).get("wait_quality_task", {}) or {})
    if wait_task:
        wait_delta = _to_float(dict(wait_task.get("delta", {}) or {}).get("macro_f1"), 0.0)
        wait_reference_ready = bool(dict(wait_task.get("reference", {}) or {}).get("ready", False))
        wait_candidate_ready = bool(dict(wait_task.get("candidate", {}) or {}).get("ready", False))
        if wait_reference_ready and not wait_candidate_ready:
            warnings.append("wait_quality_candidate_not_ready")
        elif wait_reference_ready and wait_candidate_ready:
            if wait_delta < DELTA_HARD:
                warnings.append("wait_quality_macro_f1_hard_regression")
            elif wait_delta < DELTA_WARN:
                warnings.append("wait_quality_macro_f1_regressed")
            elif wait_delta > 0.01:
                improvements.append("wait_quality_macro_f1_improved")
        elif wait_candidate_ready and not wait_reference_ready:
            improvements.append("wait_quality_new_ready_task")

    belief_task = dict((compare_report.get("tasks", {}) or {}).get("belief_outcome_task", {}) or {})
    belief_compare_summary = dict(compare_report.get("belief_compare_summary", {}) or {})
    belief_ready_delta = dict(belief_compare_summary.get("belief_ready_delta", {}) or {})
    belief_quality_delta = dict(belief_compare_summary.get("belief_quality_delta", {}) or {})
    if belief_task:
        belief_delta = _to_float(dict(belief_task.get("delta", {}) or {}).get("macro_f1", 0.0), 0.0)
        belief_reference_ready = bool(belief_ready_delta.get("reference_ready", False))
        belief_candidate_ready = bool(belief_ready_delta.get("candidate_ready", False))
        premature_flip_ratio_delta = _to_float(belief_quality_delta.get("premature_flip_ratio_delta", 0.0), 0.0)
        wrong_hold_ratio_delta = _to_float(belief_quality_delta.get("wrong_hold_ratio_delta", 0.0), 0.0)
        missed_flip_ratio_delta = _to_float(belief_quality_delta.get("missed_flip_ratio_delta", 0.0), 0.0)
        high_confidence_share_delta = _to_float(belief_quality_delta.get("high_confidence_share_delta", 0.0), 0.0)

        if belief_reference_ready and not belief_candidate_ready:
            warnings.append("belief_outcome_candidate_not_ready")
        elif belief_reference_ready and belief_candidate_ready:
            if belief_delta < DELTA_HARD:
                warnings.append("belief_outcome_macro_f1_hard_regression")
            elif belief_delta < DELTA_WARN:
                warnings.append("belief_outcome_macro_f1_regressed")
            elif belief_delta > 0.01:
                improvements.append("belief_outcome_macro_f1_improved")

            if premature_flip_ratio_delta > BELIEF_PREMATURE_FLIP_HARD_DELTA:
                blockers.append("belief_premature_flip_ratio_spike")
            elif premature_flip_ratio_delta > BELIEF_WARNING_RATIO_DELTA:
                warnings.append("belief_premature_flip_ratio_up")
            elif premature_flip_ratio_delta < BELIEF_IMPROVEMENT_RATIO_DELTA:
                improvements.append("belief_premature_flip_ratio_down")

            if wrong_hold_ratio_delta > BELIEF_WARNING_RATIO_DELTA:
                warnings.append("belief_wrong_hold_ratio_up")
            elif wrong_hold_ratio_delta < BELIEF_IMPROVEMENT_RATIO_DELTA:
                improvements.append("belief_wrong_hold_ratio_down")

            if missed_flip_ratio_delta > BELIEF_WARNING_RATIO_DELTA:
                warnings.append("belief_missed_flip_ratio_up")
            elif missed_flip_ratio_delta < BELIEF_IMPROVEMENT_RATIO_DELTA:
                improvements.append("belief_missed_flip_ratio_down")

            if high_confidence_share_delta < BELIEF_HIGH_CONFIDENCE_SHARE_WARN_DELTA:
                warnings.append("belief_high_confidence_share_down")
            elif high_confidence_share_delta > BELIEF_HIGH_CONFIDENCE_SHARE_IMPROVE_DELTA:
                improvements.append("belief_high_confidence_share_up")
        elif belief_candidate_ready and not belief_reference_ready:
            improvements.append("belief_outcome_new_ready_task")

    barrier_task = dict((compare_report.get("tasks", {}) or {}).get("barrier_outcome_task", {}) or {})
    barrier_compare_summary = dict(compare_report.get("barrier_compare_summary", {}) or {})
    barrier_ready_delta = dict(barrier_compare_summary.get("barrier_ready_delta", {}) or {})
    barrier_quality_delta = dict(barrier_compare_summary.get("barrier_quality_delta", {}) or {})
    if barrier_task:
        barrier_delta = _to_float(dict(barrier_task.get("delta", {}) or {}).get("macro_f1", 0.0), 0.0)
        barrier_reference_ready = bool(barrier_ready_delta.get("reference_ready", False))
        barrier_candidate_ready = bool(barrier_ready_delta.get("candidate_ready", False))
        overblock_ratio_delta = _to_float(barrier_quality_delta.get("overblock_ratio_delta", 0.0), 0.0)
        avoided_loss_rate_delta = _to_float(barrier_quality_delta.get("avoided_loss_rate_delta", 0.0), 0.0)
        missed_profit_rate_delta = _to_float(barrier_quality_delta.get("missed_profit_rate_delta", 0.0), 0.0)
        correct_wait_rate_delta = _to_float(barrier_quality_delta.get("correct_wait_rate_delta", 0.0), 0.0)
        relief_failure_rate_delta = _to_float(barrier_quality_delta.get("relief_failure_rate_delta", 0.0), 0.0)
        loss_avoided_r_mean_delta = _to_float(barrier_quality_delta.get("loss_avoided_r_mean_delta", 0.0), 0.0)
        profit_missed_r_mean_delta = _to_float(barrier_quality_delta.get("profit_missed_r_mean_delta", 0.0), 0.0)
        wait_value_r_mean_delta = _to_float(barrier_quality_delta.get("wait_value_r_mean_delta", 0.0), 0.0)

        if barrier_reference_ready and not barrier_candidate_ready:
            warnings.append("barrier_outcome_candidate_not_ready")
        elif barrier_reference_ready and barrier_candidate_ready:
            if barrier_delta < DELTA_HARD:
                warnings.append("barrier_outcome_macro_f1_hard_regression")
            elif barrier_delta < DELTA_WARN:
                warnings.append("barrier_outcome_macro_f1_regressed")
            elif barrier_delta > 0.01:
                improvements.append("barrier_outcome_macro_f1_improved")

            if overblock_ratio_delta > BARRIER_OVERBLOCK_HARD_DELTA:
                blockers.append("barrier_overblock_ratio_spike")
            elif overblock_ratio_delta > BARRIER_WARNING_RATIO_DELTA:
                warnings.append("barrier_overblock_ratio_up")
            elif overblock_ratio_delta < BARRIER_IMPROVEMENT_RATIO_DELTA:
                improvements.append("barrier_overblock_ratio_down")

            if relief_failure_rate_delta > BARRIER_RELIEF_FAILURE_HARD_DELTA:
                blockers.append("barrier_relief_failure_ratio_spike")
            elif relief_failure_rate_delta > BARRIER_WARNING_RATIO_DELTA:
                warnings.append("barrier_relief_failure_ratio_up")
            elif relief_failure_rate_delta < BARRIER_IMPROVEMENT_RATIO_DELTA:
                improvements.append("barrier_relief_failure_ratio_down")

            if avoided_loss_rate_delta > BARRIER_WARNING_RATIO_DELTA:
                improvements.append("barrier_avoided_loss_rate_up")
            elif avoided_loss_rate_delta < BARRIER_IMPROVEMENT_RATIO_DELTA:
                warnings.append("barrier_avoided_loss_rate_down")

            if missed_profit_rate_delta > BARRIER_WARNING_RATIO_DELTA:
                warnings.append("barrier_missed_profit_rate_up")
            elif missed_profit_rate_delta < BARRIER_IMPROVEMENT_RATIO_DELTA:
                improvements.append("barrier_missed_profit_rate_down")

            if correct_wait_rate_delta > BARRIER_WARNING_RATIO_DELTA:
                improvements.append("barrier_correct_wait_rate_up")
            elif correct_wait_rate_delta < BARRIER_IMPROVEMENT_RATIO_DELTA:
                warnings.append("barrier_correct_wait_rate_down")

            if loss_avoided_r_mean_delta > BARRIER_COST_WARN_DELTA:
                improvements.append("barrier_loss_avoided_r_mean_up")
            elif loss_avoided_r_mean_delta < BARRIER_COST_IMPROVEMENT_DELTA:
                warnings.append("barrier_loss_avoided_r_mean_down")

            if profit_missed_r_mean_delta > BARRIER_COST_WARN_DELTA:
                warnings.append("barrier_profit_missed_r_mean_up")
            elif profit_missed_r_mean_delta < BARRIER_COST_IMPROVEMENT_DELTA:
                improvements.append("barrier_profit_missed_r_mean_down")

            if wait_value_r_mean_delta > BARRIER_COST_WARN_DELTA:
                improvements.append("barrier_wait_value_r_mean_up")
            elif wait_value_r_mean_delta < BARRIER_COST_IMPROVEMENT_DELTA:
                warnings.append("barrier_wait_value_r_mean_down")
        elif barrier_candidate_ready and not barrier_reference_ready:
            improvements.append("barrier_outcome_new_ready_task")

    for task_name in FORECAST_AUXILIARY_TASKS:
        task = dict((compare_report.get("tasks", {}) or {}).get(task_name, {}) or {})
        if not task:
            continue
        task_prefix = task_name.replace("_task", "")
        task_delta = _to_float(dict(task.get("delta", {}) or {}).get("macro_f1", 0.0), 0.0)
        task_reference_ready = bool(dict(task.get("reference", {}) or {}).get("ready", False))
        task_candidate_ready = bool(dict(task.get("candidate", {}) or {}).get("ready", False))
        if task_reference_ready and not task_candidate_ready:
            warnings.append(f"{task_prefix}_candidate_not_ready")
        elif task_reference_ready and task_candidate_ready:
            if task_delta < DELTA_HARD:
                warnings.append(f"{task_prefix}_macro_f1_hard_regression")
            elif task_delta < DELTA_WARN:
                warnings.append(f"{task_prefix}_macro_f1_regressed")
            elif task_delta > 0.01:
                improvements.append(f"{task_prefix}_macro_f1_improved")
        elif task_candidate_ready and not task_reference_ready:
            improvements.append(f"{task_prefix}_new_ready_task")

    if blockers:
        decision = "hold_regression"
        action = "keep_current_baseline"
    elif warnings:
        decision = "log_only_review_ready"
        action = "ai4_log_only_review"
    elif improvements:
        decision = "promote_review_ready"
        action = "ai4_gate_review"
    else:
        decision = "hold_no_material_gain"
        action = "keep_current_baseline"

    return {
        "contract_version": "teacher_pattern_candidate_promote_decision_v1",
        "decision": decision,
        "recommended_action": action,
        "blockers": blockers,
        "warnings": warnings,
        "improvements": improvements,
    }


def render_teacher_pattern_candidate_summary_markdown(
    *,
    candidate_id: str,
    candidate_report: dict[str, Any],
    compare_report: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> str:
    seed = dict(candidate_report.get("seed_summary", {}) or {})
    economic = dict(candidate_report.get("economic_target_integration", {}) or {})
    belief = dict(candidate_report.get("belief_outcome_integration", {}) or {})
    pattern_task = _task_payload(candidate_report, "pattern_task")
    belief_compare = dict(compare_report.get("belief_compare_summary", {}) or {})
    belief_ready_delta = dict(belief_compare.get("belief_ready_delta", {}) or {})
    belief_quality_delta = dict(belief_compare.get("belief_quality_delta", {}) or {})
    barrier_compare = dict(compare_report.get("barrier_compare_summary", {}) or {})
    barrier_ready_delta = dict(barrier_compare.get("barrier_ready_delta", {}) or {})
    barrier_quality_delta = dict(barrier_compare.get("barrier_quality_delta", {}) or {})
    lines = [
        f"# State25 Candidate Summary `{candidate_id}`",
        "",
        "## Current Summary",
        "",
        f"- baseline_ready: `{bool(candidate_report.get('baseline_ready', False))}`",
        f"- labeled_rows: `{int(seed.get('labeled_rows', 0) or 0)}`",
        f"- supported_pattern_ids: `{pattern_task.get('supported_pattern_ids', [])}`",
        f"- economic_target_ready: `{bool(economic.get('ready', False))}`",
        f"- belief_outcome_ready: `{bool(belief.get('ready', False))}`",
        f"- barrier_outcome_ready: `{bool(candidate_report.get('barrier_outcome_integration', {}).get('ready', False))}`",
        "",
        "## Compare",
        "",
    ]
    for task_name in PRIMARY_PROMOTION_TASKS:
        task = dict((compare_report.get("tasks", {}) or {}).get(task_name, {}) or {})
        delta = dict(task.get("delta", {}) or {})
        lines.append(
            f"- {task_name}: candidate_ready=`{task.get('candidate', {}).get('ready', False)}` "
            f"reference_ready=`{task.get('reference', {}).get('ready', False)}` "
            f"test_macro_f1_delta=`{delta.get('macro_f1', 0.0):.4f}`"
        )
    wait_task = dict((compare_report.get("tasks", {}) or {}).get("wait_quality_task", {}) or {})
    if wait_task:
        lines.append(
            f"- wait_quality_task: candidate_ready=`{wait_task.get('candidate', {}).get('ready', False)}` "
            f"reference_ready=`{wait_task.get('reference', {}).get('ready', False)}` "
            f"test_macro_f1_delta=`{dict(wait_task.get('delta', {}) or {}).get('macro_f1', 0.0):.4f}`"
        )
    belief_task = dict((compare_report.get("tasks", {}) or {}).get("belief_outcome_task", {}) or {})
    if belief_task:
        lines.append(
            f"- belief_outcome_task: candidate_ready=`{belief_task.get('candidate', {}).get('ready', False)}` "
            f"reference_ready=`{belief_task.get('reference', {}).get('ready', False)}` "
            f"test_macro_f1_delta=`{dict(belief_task.get('delta', {}) or {}).get('macro_f1', 0.0):.4f}`"
        )
        lines.append(
            f"- belief_quality_delta: wrong_hold=`{belief_quality_delta.get('wrong_hold_ratio_delta', 0.0):.4f}` "
            f"premature_flip=`{belief_quality_delta.get('premature_flip_ratio_delta', 0.0):.4f}` "
            f"missed_flip=`{belief_quality_delta.get('missed_flip_ratio_delta', 0.0):.4f}` "
            f"high_conf_share=`{belief_quality_delta.get('high_confidence_share_delta', 0.0):.4f}` "
            f"(strict_rows_delta=`{belief_ready_delta.get('high_medium_confidence_rows_delta', 0)}`, "
            f"usable_rows_delta=`{belief_ready_delta.get('usable_confidence_rows_delta', 0)}`)"
        )
    barrier_task = dict((compare_report.get("tasks", {}) or {}).get("barrier_outcome_task", {}) or {})
    if barrier_task:
        lines.append(
            f"- barrier_outcome_task: candidate_ready=`{barrier_task.get('candidate', {}).get('ready', False)}` "
            f"reference_ready=`{barrier_task.get('reference', {}).get('ready', False)}` "
            f"test_macro_f1_delta=`{dict(barrier_task.get('delta', {}) or {}).get('macro_f1', 0.0):.4f}`"
        )
        lines.append(
            f"- barrier_quality_delta: overblock=`{barrier_quality_delta.get('overblock_ratio_delta', 0.0):.4f}` "
            f"avoided_loss=`{barrier_quality_delta.get('avoided_loss_rate_delta', 0.0):.4f}` "
            f"missed_profit=`{barrier_quality_delta.get('missed_profit_rate_delta', 0.0):.4f}` "
            f"relief_failure=`{barrier_quality_delta.get('relief_failure_rate_delta', 0.0):.4f}` "
            f"profit_missed_r=`{barrier_quality_delta.get('profit_missed_r_mean_delta', 0.0):.4f}` "
            f"weak_share=`{barrier_quality_delta.get('weak_usable_share_delta', 0.0):.4f}` "
            f"(strict_rows_delta=`{barrier_ready_delta.get('high_medium_confidence_rows_delta', 0)}`, "
            f"usable_rows_delta=`{barrier_ready_delta.get('usable_confidence_rows_delta', 0)}`)"
        )
    for task_name in FORECAST_AUXILIARY_TASKS:
        task = dict((compare_report.get("tasks", {}) or {}).get(task_name, {}) or {})
        if not task:
            continue
        lines.append(
            f"- {task_name}: candidate_ready=`{task.get('candidate', {}).get('ready', False)}` "
            f"reference_ready=`{task.get('reference', {}).get('ready', False)}` "
            f"test_macro_f1_delta=`{dict(task.get('delta', {}) or {}).get('macro_f1', 0.0):.4f}`"
        )
    lines.extend(
        [
            "",
            "## Promotion Skeleton",
            "",
            f"- decision: `{promotion_decision.get('decision', '')}`",
            f"- recommended_action: `{promotion_decision.get('recommended_action', '')}`",
            f"- blockers: `{promotion_decision.get('blockers', [])}`",
            f"- warnings: `{promotion_decision.get('warnings', [])}`",
            f"- improvements: `{promotion_decision.get('improvements', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_teacher_pattern_candidate_pipeline(
    frame: pd.DataFrame | None,
    *,
    csv_path: str | Path,
    candidate_root: str | Path,
    reference_metrics_path: str | Path | None = None,
    min_seed_rows: int = DEFAULT_MIN_SEED_ROWS,
    pattern_min_support: int = DEFAULT_PATTERN_MIN_SUPPORT,
    wait_quality_min_support: int = DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
    economic_target_min_support: int = DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    forecast_outcome_min_support: int = DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT,
    belief_outcome_min_support: int = DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT,
    belief_outcome_min_rows: int = DEFAULT_BELIEF_OUTCOME_MIN_ROWS,
    barrier_outcome_min_support: int = DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT,
    barrier_outcome_min_rows: int = DEFAULT_BARRIER_OUTCOME_MIN_ROWS,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    candidate_root_path = Path(candidate_root)
    candidate_root_path.mkdir(parents=True, exist_ok=True)
    candidate_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = candidate_root_path / candidate_id
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate_report = build_teacher_pattern_pilot_baseline_report(
        dataset,
        min_seed_rows=int(min_seed_rows),
        pattern_min_support=int(pattern_min_support),
        wait_quality_min_support=int(wait_quality_min_support),
        economic_target_min_support=int(economic_target_min_support),
        forecast_outcome_min_support=int(forecast_outcome_min_support),
        belief_outcome_min_support=int(belief_outcome_min_support),
        belief_outcome_min_rows=int(belief_outcome_min_rows),
        barrier_outcome_min_support=int(barrier_outcome_min_support),
        barrier_outcome_min_rows=int(barrier_outcome_min_rows),
        output_dir=output_dir,
    )

    reference_report = _load_json(reference_metrics_path)
    compare_report = build_teacher_pattern_candidate_compare_report(candidate_report, reference_report)
    promotion_decision = build_teacher_pattern_candidate_promotion_decision(candidate_report, compare_report)

    compare_path = output_dir / "teacher_pattern_candidate_compare_report.json"
    compare_path.write_text(json.dumps(compare_report, ensure_ascii=False, indent=2), encoding="utf-8")

    decision_path = output_dir / "teacher_pattern_candidate_promotion_decision.json"
    decision_path.write_text(json.dumps(promotion_decision, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_md_path = output_dir / "teacher_pattern_candidate_summary.md"
    summary_md_path.write_text(
        render_teacher_pattern_candidate_summary_markdown(
            candidate_id=candidate_id,
            candidate_report=candidate_report,
            compare_report=compare_report,
            promotion_decision=promotion_decision,
        ),
        encoding="utf-8",
    )

    manifest = {
        "contract_version": "teacher_pattern_candidate_run_manifest_v1",
        "candidate_id": candidate_id,
        "csv_path": str(Path(csv_path)),
        "output_dir": str(output_dir),
        "reference_metrics_path": str(reference_metrics_path) if reference_metrics_path else "",
        "candidate_metrics_path": str(output_dir / "teacher_pattern_pilot_baseline_metrics.json"),
        "candidate_bundle_path": str(output_dir / "teacher_pattern_pilot_baseline.joblib"),
        "compare_report_path": str(compare_path),
        "promotion_decision_path": str(decision_path),
        "summary_md_path": str(summary_md_path),
        "promotion_decision": promotion_decision,
    }
    (output_dir / "teacher_pattern_candidate_run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (candidate_root_path / "latest_candidate_run.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
