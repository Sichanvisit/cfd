"""Step 9-E5 execution handoff gate for teacher-pattern state25."""

from __future__ import annotations

from typing import Any


DEFAULT_MIN_LABELED_ROWS = 10_000
DEFAULT_MIN_COVERED_PRIMARY_COUNT = 8
DEFAULT_MIN_SUPPORTED_PATTERN_COUNT = 6
DEFAULT_MIN_GROUP_TEST_MACRO_F1 = 0.65
DEFAULT_MIN_PATTERN_TEST_MACRO_F1 = 0.60


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _append_unique(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


def build_teacher_pattern_execution_handoff_report(
    *,
    asset_calibration_report: dict[str, Any] | None,
    full_qa_report: dict[str, Any] | None,
    baseline_report: dict[str, Any] | None,
    confusion_report: dict[str, Any] | None,
    min_labeled_rows: int = DEFAULT_MIN_LABELED_ROWS,
    min_covered_primary_count: int = DEFAULT_MIN_COVERED_PRIMARY_COUNT,
    min_supported_pattern_count: int = DEFAULT_MIN_SUPPORTED_PATTERN_COUNT,
    min_group_test_macro_f1: float = DEFAULT_MIN_GROUP_TEST_MACRO_F1,
    min_pattern_test_macro_f1: float = DEFAULT_MIN_PATTERN_TEST_MACRO_F1,
) -> dict[str, Any]:
    asset = _as_mapping(asset_calibration_report)
    full_qa = _as_mapping(full_qa_report)
    baseline = _as_mapping(baseline_report)
    confusion = _as_mapping(confusion_report)

    full_qa_readiness = _as_mapping(full_qa.get("full_qa_readiness"))
    pattern_coverage = _as_mapping(full_qa.get("pattern_coverage"))
    baseline_tasks = _as_mapping(baseline.get("tasks"))
    group_task = _as_mapping(baseline_tasks.get("group_task"))
    pattern_task = _as_mapping(baseline_tasks.get("pattern_task"))
    group_test_metrics = _as_mapping(_as_mapping(group_task.get("model_metrics")).get("test"))
    pattern_test_metrics = _as_mapping(_as_mapping(pattern_task.get("model_metrics")).get("test"))

    labeled_rows = _as_int(full_qa.get("labeled_rows", 0))
    covered_primary_count = _as_int(pattern_coverage.get("covered_primary_count", 0))
    supported_pattern_ids = [int(value) for value in _as_list(pattern_task.get("supported_pattern_ids"))]
    supported_pattern_count = len(supported_pattern_ids)
    group_test_macro_f1 = _as_float(group_test_metrics.get("macro_f1", 0.0))
    pattern_test_macro_f1 = _as_float(pattern_test_metrics.get("macro_f1", 0.0))

    group_candidates = [row for row in _as_list(confusion.get("group_candidates")) if isinstance(row, dict)]
    pattern_candidates = [row for row in _as_list(confusion.get("pattern_candidates")) if isinstance(row, dict)]
    high_confusions = [
        row
        for row in [*group_candidates, *pattern_candidates]
        if str(row.get("severity", "")).strip().lower() == "high"
    ]
    medium_confusions = [
        row
        for row in [*group_candidates, *pattern_candidates]
        if str(row.get("severity", "")).strip().lower() == "medium"
    ]

    blockers: list[dict[str, Any]] = []
    warnings: list[str] = []
    recommended_actions: list[str] = []

    if not bool(full_qa_readiness.get("full_qa_ready", False)) or labeled_rows < int(min_labeled_rows):
        blockers.append(
            {
                "code": "full_qa_seed_shortfall",
                "message": "Labeled seed is still below the execution-handoff minimum.",
                "current": labeled_rows,
                "required": int(min_labeled_rows),
            }
        )
        _append_unique(recommended_actions, "Accumulate more labeled rows or expand bounded backfill before execution handoff.")

    if covered_primary_count < int(min_covered_primary_count):
        blockers.append(
            {
                "code": "insufficient_primary_coverage",
                "message": "Primary pattern coverage is still too narrow for execution handoff.",
                "current": covered_primary_count,
                "required": int(min_covered_primary_count),
            }
        )
        _append_unique(recommended_actions, "Keep collecting live regimes so the seed covers more than the current dominant groups.")

    if supported_pattern_count < int(min_supported_pattern_count):
        blockers.append(
            {
                "code": "insufficient_supported_pattern_classes",
                "message": "Pilot baseline still supports too few primary pattern classes.",
                "current": supported_pattern_count,
                "required": int(min_supported_pattern_count),
                "supported_pattern_ids": supported_pattern_ids,
            }
        )
        _append_unique(recommended_actions, "Increase labeled coverage before treating the pilot baseline as an execution handoff signal.")

    if not bool(baseline.get("baseline_ready", False)):
        blockers.append(
            {
                "code": "pilot_baseline_not_ready",
                "message": "Pilot baseline is not ready yet.",
                "baseline_warnings": list(_as_list(baseline.get("baseline_warnings"))),
            }
        )
        _append_unique(recommended_actions, "Resolve pilot baseline readiness before execution handoff.")

    if bool(group_task.get("skipped", False)):
        blockers.append(
            {
                "code": "group_baseline_skipped",
                "message": "Group-level pilot baseline was skipped.",
            }
        )
        _append_unique(recommended_actions, "Recover group-task baseline coverage before execution handoff.")
    elif group_test_macro_f1 < float(min_group_test_macro_f1):
        blockers.append(
            {
                "code": "group_macro_f1_below_threshold",
                "message": "Group-level pilot baseline macro F1 is below the handoff threshold.",
                "current": group_test_macro_f1,
                "required": float(min_group_test_macro_f1),
            }
        )
        _append_unique(recommended_actions, "Tune group-level thresholds or collect better seed diversity before handoff.")

    if bool(pattern_task.get("skipped", False)):
        blockers.append(
            {
                "code": "pattern_baseline_skipped",
                "message": "Pattern-level pilot baseline was skipped.",
            }
        )
        _append_unique(recommended_actions, "Recover pattern-task baseline coverage before execution handoff.")
    elif pattern_test_macro_f1 < float(min_pattern_test_macro_f1):
        blockers.append(
            {
                "code": "pattern_macro_f1_below_threshold",
                "message": "Pattern-level pilot baseline macro F1 is below the handoff threshold.",
                "current": pattern_test_macro_f1,
                "required": float(min_pattern_test_macro_f1),
            }
        )
        _append_unique(recommended_actions, "Tune pattern thresholds or grow the seed before handoff.")

    if high_confusions:
        blockers.append(
            {
                "code": "unresolved_high_confusions",
                "message": "High-severity confusion pairs are still unresolved.",
                "pairs": [row.get("pair") for row in high_confusions],
            }
        )
        _append_unique(recommended_actions, "Continue Step 9-E4 tuning on the current high-severity confusion pairs.")

    for warning in _as_list(asset.get("warnings")):
        text = str(warning).strip()
        if text:
            _append_unique(warnings, f"asset:{text}")
    for warning in _as_list(full_qa.get("warnings")):
        text = str(warning).strip()
        if text:
            _append_unique(warnings, f"full_qa:{text}")
    for warning in _as_list(confusion.get("warnings")):
        text = str(warning).strip()
        if text:
            _append_unique(warnings, f"confusion:{text}")

    if medium_confusions:
        _append_unique(warnings, "medium_confusions_present")
        _append_unique(recommended_actions, "Observe medium-severity confusions while accumulating more labeled rows.")

    watchlist_status = [row for row in _as_list(confusion.get("watchlist_status")) if isinstance(row, dict)]
    if any(str(row.get("status", "")).strip() == "observe_only" for row in watchlist_status):
        _append_unique(warnings, "watchlist_pairs_still_sparse")

    if blockers:
        handoff_status = "NOT_READY"
    elif warnings:
        handoff_status = "READY_WITH_WARNINGS"
    else:
        handoff_status = "READY"

    if not recommended_actions and handoff_status == "READY":
        recommended_actions.append("Execution handoff can proceed to a narrow, monitored rollout.")

    return {
        "handoff_status": handoff_status,
        "execution_handoff_ready": handoff_status != "NOT_READY",
        "snapshot": {
            "labeled_rows": labeled_rows,
            "min_labeled_rows": int(min_labeled_rows),
            "covered_primary_count": covered_primary_count,
            "min_covered_primary_count": int(min_covered_primary_count),
            "supported_pattern_count": supported_pattern_count,
            "supported_pattern_ids": supported_pattern_ids,
            "min_supported_pattern_count": int(min_supported_pattern_count),
            "group_test_macro_f1": group_test_macro_f1,
            "min_group_test_macro_f1": float(min_group_test_macro_f1),
            "pattern_test_macro_f1": pattern_test_macro_f1,
            "min_pattern_test_macro_f1": float(min_pattern_test_macro_f1),
        },
        "upstream_status": {
            "asset_calibration_warnings": list(_as_list(asset.get("warnings"))),
            "full_qa_ready": bool(full_qa_readiness.get("full_qa_ready", False)),
            "baseline_ready": bool(baseline.get("baseline_ready", False)),
            "high_confusion_count": len(high_confusions),
            "medium_confusion_count": len(medium_confusions),
        },
        "blockers": blockers,
        "warnings": warnings,
        "unresolved_confusions": {
            "high": high_confusions,
            "medium": medium_confusions,
            "watchlist_status": watchlist_status,
        },
        "recommended_actions": recommended_actions,
    }
