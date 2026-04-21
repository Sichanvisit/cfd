"""Promotion gate / rollback scaffold for state25 candidate bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.teacher_pattern_candidate_pipeline import DEFAULT_CANDIDATE_ROOT


DEFAULT_LATEST_CANDIDATE_MANIFEST = DEFAULT_CANDIDATE_ROOT / "latest_candidate_run.json"
DEFAULT_STEP9_WATCH_REPORT_PATH = (
    Path("data") / "analysis" / "teacher_pattern_state25" / "teacher_pattern_step9_watch_latest.json"
)
DEFAULT_CANARY_EVIDENCE_PATH = (
    DEFAULT_CANDIDATE_ROOT / "latest_candidate_canary_evidence.json"
)
DEFAULT_CANARY_THRESHOLDS = {
    "min_rows_observed": 50,
    "min_utility_delta": 0.0,
    "max_must_release_delta": 0,
    "max_bad_exit_delta": 0,
    "max_wait_drift_delta": 0.05,
    "max_symbol_skew_delta": 0.10,
    "max_watchlist_confusion_delta": 0,
}
DEFAULT_LOG_ONLY_SOFT_BLOCKER_CODES = {
    "full_qa_seed_shortfall",
    "insufficient_primary_coverage",
    "insufficient_supported_pattern_classes",
}
ROLLBACK_TRIGGER_SUMMARY = [
    "must_release candidate count increases above the allowed delta",
    "bad_exit candidate count increases above the allowed delta",
    "utility delta turns negative beyond the gate threshold",
    "wait drift rises beyond the allowed delta",
    "symbol skew widens beyond the allowed delta",
    "watchlist confusion count increases above the allowed delta",
]


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _step9_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(report or {})
    snapshot = dict(payload.get("snapshot", {}) or {})
    execution = dict(((payload.get("watch_items", {}) or {}).get("execution_handoff", {})) or {})
    recheck = dict(payload.get("recheck_timing", {}) or {})
    blocker_codes = list(execution.get("blocker_codes", []) or [])
    soft_blocker_codes = [
        str(code).strip()
        for code in blocker_codes
        if str(code).strip() in DEFAULT_LOG_ONLY_SOFT_BLOCKER_CODES
    ]
    critical_blocker_codes = [
        str(code).strip()
        for code in blocker_codes
        if str(code).strip() and str(code).strip() not in DEFAULT_LOG_ONLY_SOFT_BLOCKER_CODES
    ]
    execution_handoff_ready = bool(execution.get("execution_handoff_ready", False))
    log_only_gate_ready = bool(payload) and (
        execution_handoff_ready
        or (
            str(execution.get("handoff_status", "")).strip().upper() == "NOT_READY"
            and bool(blocker_codes)
            and not critical_blocker_codes
        )
    )
    return {
        "available": bool(payload),
        "execution_handoff_ready": execution_handoff_ready,
        "log_only_gate_ready": log_only_gate_ready,
        "handoff_status": str(execution.get("handoff_status", "")),
        "blocker_codes": blocker_codes,
        "soft_blocker_codes": soft_blocker_codes,
        "critical_blocker_codes": critical_blocker_codes,
        "warning_codes": list(execution.get("warning_codes", []) or []),
        "labeled_rows": _to_int(snapshot.get("labeled_rows", 0), 0),
        "rows_to_target": _to_int(snapshot.get("rows_to_target", 0), 0),
        "recheck_status": str(recheck.get("status", "")),
    }


def _canary_summary(
    evidence: dict[str, Any] | None,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(evidence or {})
    metrics = {
        "rows_observed": _to_int(payload.get("rows_observed", 0), 0),
        "utility_delta": _to_float(payload.get("utility_delta", 0.0), 0.0),
        "must_release_delta": _to_int(payload.get("must_release_delta", 0), 0),
        "bad_exit_delta": _to_int(payload.get("bad_exit_delta", 0), 0),
        "wait_drift_delta": _to_float(payload.get("wait_drift_delta", 0.0), 0.0),
        "symbol_skew_delta": _to_float(payload.get("symbol_skew_delta", 0.0), 0.0),
        "watchlist_confusion_delta": _to_int(payload.get("watchlist_confusion_delta", 0), 0),
    }
    available = bool(payload)
    complete = available and metrics["rows_observed"] >= _to_int(
        thresholds.get("min_rows_observed", 0),
        0,
    )
    return {
        "available": available,
        "complete": complete,
        "candidate_id": str(payload.get("candidate_id", "")),
        "metrics": metrics,
    }


def build_teacher_pattern_promotion_gate_report(
    candidate_manifest: dict[str, Any],
    *,
    compare_report: dict[str, Any] | None = None,
    promotion_decision: dict[str, Any] | None = None,
    step9_watch_report: dict[str, Any] | None = None,
    canary_evidence: dict[str, Any] | None = None,
    canary_thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = dict(candidate_manifest or {})
    compare = dict(compare_report or {})
    decision = dict(promotion_decision or {})
    thresholds = dict(DEFAULT_CANARY_THRESHOLDS)
    thresholds.update(dict(canary_thresholds or {}))

    step9 = _step9_summary(step9_watch_report)
    canary = _canary_summary(canary_evidence, thresholds)

    blockers: list[str] = []
    warnings: list[str] = []
    rollback_reasons: list[str] = []
    next_actions: list[str] = []
    stage = "hold_offline"
    recommended_action = "keep_current_baseline"

    decision_name = str(decision.get("decision", ""))
    decision_blockers = list(decision.get("blockers", []) or [])
    decision_warnings = list(decision.get("warnings", []) or [])

    if decision_name == "shadow_only_first_candidate":
        stage = "shadow_only"
        recommended_action = "collect_reference_and_shadow_feedback"
        warnings.extend(decision_warnings or ["no_reference_baseline"])
        next_actions.append("Keep the candidate offline and collect one clean reference baseline for the next compare.")
    elif decision_name not in {"promote_review_ready", "log_only_review_ready"}:
        stage = "hold_offline"
        recommended_action = "keep_current_baseline"
        blockers.extend(decision_blockers)
        warnings.extend(decision_warnings)
        next_actions.append("Keep the current baseline and wait for a materially better candidate.")
    elif not step9["log_only_gate_ready"]:
        stage = "hold_step9"
        recommended_action = "wait_for_step9_execution_handoff"
        blocker_source = step9["critical_blocker_codes"] or step9["blocker_codes"]
        blockers.extend([f"step9:{code}" for code in blocker_source])
        warnings.extend(decision_warnings)
        next_actions.append("Keep the candidate offline until Step 9 critical blockers are cleared.")
    elif decision_name == "log_only_review_ready":
        stage = "log_only_ready"
        recommended_action = "promote_log_only_after_offline_soft_regression_review"
        warnings.extend(decision_warnings)
        next_actions.extend(
            [
                "Offline compare shows only soft regression, so allow log-only review first.",
                "Do not open canary or bounded live until a stronger candidate is available.",
            ]
        )
    elif not step9["execution_handoff_ready"]:
        stage = "log_only_ready"
        recommended_action = "promote_log_only_while_seed_accumulates"
        warnings.extend([f"step9_soft:{code}" for code in step9["soft_blocker_codes"]])
        warnings.extend(decision_warnings)
        next_actions.extend(
            [
                "Allow log-only candidate traces while Step 9 seed and coverage continue accumulating.",
                "Do not open canary or bounded live until full execution handoff becomes ready.",
            ]
        )
    elif not canary["available"]:
        stage = "log_only_ready"
        recommended_action = "run_log_only_then_collect_canary_evidence"
        next_actions.append("Run the candidate in log-only first and capture canary evidence.")
    elif not canary["complete"]:
        stage = "log_only_ready"
        recommended_action = "collect_more_canary_rows"
        warnings.append("canary_rows_short")
        next_actions.append("Keep log-only active; canary evidence exists, but the observed row count is still below the minimum gate threshold.")
    else:
        metrics = dict(canary.get("metrics", {}) or {})
        if metrics["utility_delta"] < _to_float(thresholds.get("min_utility_delta", 0.0), 0.0):
            rollback_reasons.append("utility_delta_below_threshold")
        if metrics["must_release_delta"] > _to_int(thresholds.get("max_must_release_delta", 0), 0):
            rollback_reasons.append("must_release_delta_above_threshold")
        if metrics["bad_exit_delta"] > _to_int(thresholds.get("max_bad_exit_delta", 0), 0):
            rollback_reasons.append("bad_exit_delta_above_threshold")
        if metrics["wait_drift_delta"] > _to_float(thresholds.get("max_wait_drift_delta", 0.0), 0.0):
            rollback_reasons.append("wait_drift_delta_above_threshold")
        if metrics["symbol_skew_delta"] > _to_float(thresholds.get("max_symbol_skew_delta", 0.0), 0.0):
            rollback_reasons.append("symbol_skew_delta_above_threshold")
        if metrics["watchlist_confusion_delta"] > _to_int(
            thresholds.get("max_watchlist_confusion_delta", 0),
            0,
        ):
            rollback_reasons.append("watchlist_confusion_delta_above_threshold")

        if rollback_reasons:
            stage = "rollback_recommended"
            recommended_action = "rollback_to_current_baseline"
            blockers.extend(rollback_reasons)
            next_actions.append("Do not promote the candidate. Roll back or keep the current baseline.")
        else:
            stage = "promote_ready"
            recommended_action = "promote_with_bounded_ai5_bind"
            next_actions.append("The canary checks passed. You can bind the candidate to a narrow AI5 execution surface.")

    return {
        "contract_version": "teacher_pattern_promotion_gate_report_v1",
        "candidate_id": str(manifest.get("candidate_id", "")),
        "gate_stage": stage,
        "recommended_action": recommended_action,
        "offline_decision": {
            "decision": decision_name,
            "recommended_action": str(decision.get("recommended_action", "")),
        },
        "offline_compare_summary": {
            "reference_available": bool(compare.get("reference_available", False)),
            "reference_baseline_ready": bool(compare.get("reference_baseline_ready", False)),
            "candidate_baseline_ready": bool(compare.get("candidate_baseline_ready", False)),
            "belief_compare_summary": dict(compare.get("belief_compare_summary", {}) or {}),
            "barrier_compare_summary": dict(compare.get("barrier_compare_summary", {}) or {}),
            "forecast_state25_compare_summary": dict(compare.get("forecast_state25_compare_summary", {}) or {}),
        },
        "step9_summary": step9,
        "canary_summary": canary,
        "canary_thresholds": thresholds,
        "blockers": blockers,
        "warnings": warnings,
        "rollback_reasons": rollback_reasons,
        "rollback_trigger_summary": list(ROLLBACK_TRIGGER_SUMMARY),
        "next_actions": next_actions,
        "source_paths": {
            "candidate_manifest_path": str(manifest.get("manifest_path", "")),
            "compare_report_path": str(manifest.get("compare_report_path", "")),
            "promotion_decision_path": str(manifest.get("promotion_decision_path", "")),
        },
    }


def render_teacher_pattern_promotion_gate_markdown(report: dict[str, Any]) -> str:
    step9 = dict(report.get("step9_summary", {}) or {})
    canary = dict(report.get("canary_summary", {}) or {})
    canary_metrics = dict(canary.get("metrics", {}) or {})
    offline_compare = dict(report.get("offline_compare_summary", {}) or {})
    belief_compare = dict(offline_compare.get("belief_compare_summary", {}) or {})
    belief_ready_delta = dict(belief_compare.get("belief_ready_delta", {}) or {})
    belief_quality_delta = dict(belief_compare.get("belief_quality_delta", {}) or {})
    barrier_compare = dict(offline_compare.get("barrier_compare_summary", {}) or {})
    barrier_ready_delta = dict(barrier_compare.get("barrier_ready_delta", {}) or {})
    barrier_quality_delta = dict(barrier_compare.get("barrier_quality_delta", {}) or {})
    forecast_compare = dict(offline_compare.get("forecast_state25_compare_summary", {}) or {})
    transition_compare = dict(forecast_compare.get("transition_ready_delta", {}) or {})
    management_compare = dict(forecast_compare.get("management_ready_delta", {}) or {})
    lines = [
        f"# State25 Promotion Gate `{report.get('candidate_id', '')}`",
        "",
        "## Gate Summary",
        "",
        f"- gate_stage: `{report.get('gate_stage', '')}`",
        f"- recommended_action: `{report.get('recommended_action', '')}`",
        f"- offline_decision: `{dict(report.get('offline_decision', {}) or {}).get('decision', '')}`",
        f"- belief_ready: `candidate={belief_ready_delta.get('candidate_ready', False)} / reference={belief_ready_delta.get('reference_ready', False)}`",
        f"- belief_quality_delta: `wrong_hold={belief_quality_delta.get('wrong_hold_ratio_delta', 0.0)} / premature_flip={belief_quality_delta.get('premature_flip_ratio_delta', 0.0)} / missed_flip={belief_quality_delta.get('missed_flip_ratio_delta', 0.0)} / high_conf_share={belief_quality_delta.get('high_confidence_share_delta', 0.0)}`",
        f"- barrier_ready: `candidate={barrier_ready_delta.get('candidate_ready', False)} / reference={barrier_ready_delta.get('reference_ready', False)} / strict_rows_delta={barrier_ready_delta.get('high_medium_confidence_rows_delta', 0)} / usable_rows_delta={barrier_ready_delta.get('usable_confidence_rows_delta', 0)}`",
        f"- barrier_quality_delta: `overblock={barrier_quality_delta.get('overblock_ratio_delta', 0.0)} / avoided_loss={barrier_quality_delta.get('avoided_loss_rate_delta', 0.0)} / missed_profit={barrier_quality_delta.get('missed_profit_rate_delta', 0.0)} / relief_failure={barrier_quality_delta.get('relief_failure_rate_delta', 0.0)} / weak_usable_share={barrier_quality_delta.get('weak_usable_share_delta', 0.0)} / weak_to_medium_conversion={barrier_quality_delta.get('weak_to_medium_conversion_rate_delta', 0.0)}`",
        f"- forecast_transition_ready: `candidate={transition_compare.get('candidate_ready', False)} / reference={transition_compare.get('reference_ready', False)}`",
        f"- forecast_management_ready: `candidate={management_compare.get('candidate_ready', False)} / reference={management_compare.get('reference_ready', False)}`",
        "",
        "## Step9",
        "",
        f"- execution_handoff_ready: `{step9.get('execution_handoff_ready', False)}`",
        f"- handoff_status: `{step9.get('handoff_status', '')}`",
        f"- labeled_rows: `{step9.get('labeled_rows', 0)}`",
        f"- rows_to_target: `{step9.get('rows_to_target', 0)}`",
        f"- blocker_codes: `{step9.get('blocker_codes', [])}`",
        "",
        "## Canary",
        "",
        f"- available: `{canary.get('available', False)}`",
        f"- complete: `{canary.get('complete', False)}`",
        f"- rows_observed: `{canary_metrics.get('rows_observed', 0)}`",
        f"- utility_delta: `{canary_metrics.get('utility_delta', 0.0)}`",
        f"- must_release_delta: `{canary_metrics.get('must_release_delta', 0)}`",
        f"- bad_exit_delta: `{canary_metrics.get('bad_exit_delta', 0)}`",
        f"- wait_drift_delta: `{canary_metrics.get('wait_drift_delta', 0.0)}`",
        f"- symbol_skew_delta: `{canary_metrics.get('symbol_skew_delta', 0.0)}`",
        f"- watchlist_confusion_delta: `{canary_metrics.get('watchlist_confusion_delta', 0)}`",
        "",
        "## Gate Notes",
        "",
        f"- blockers: `{report.get('blockers', [])}`",
        f"- warnings: `{report.get('warnings', [])}`",
        f"- rollback_reasons: `{report.get('rollback_reasons', [])}`",
        f"- next_actions: `{report.get('next_actions', [])}`",
        "",
    ]
    return "\n".join(lines)


def run_teacher_pattern_promotion_gate(
    *,
    candidate_manifest_path: str | Path,
    step9_watch_report_path: str | Path | None = None,
    canary_evidence_path: str | Path | None = None,
    canary_thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_path = Path(candidate_manifest_path)
    manifest = _load_json(manifest_path)
    if not manifest:
        raise FileNotFoundError(f"missing candidate manifest: {manifest_path}")

    compare_report = _load_json(manifest.get("compare_report_path"))
    promotion_decision = _load_json(manifest.get("promotion_decision_path"))
    step9_watch_report = _load_json(step9_watch_report_path)
    canary_evidence = _load_json(canary_evidence_path)

    report = build_teacher_pattern_promotion_gate_report(
        {
            **manifest,
            "manifest_path": str(manifest_path),
        },
        compare_report=compare_report,
        promotion_decision=promotion_decision,
        step9_watch_report=step9_watch_report,
        canary_evidence=canary_evidence,
        canary_thresholds=canary_thresholds,
    )

    output_dir = Path(manifest.get("output_dir", manifest_path.parent))
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "teacher_pattern_promotion_gate_report.json"
    md_path = output_dir / "teacher_pattern_promotion_gate_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_teacher_pattern_promotion_gate_markdown(report), encoding="utf-8")

    latest_root_path = Path(DEFAULT_CANDIDATE_ROOT).resolve()
    latest_root_path.mkdir(parents=True, exist_ok=True)
    (latest_root_path / "latest_gate_report.json").write_text(
        json.dumps(
            {
                **report,
                "gate_report_path": str(json_path),
                "gate_markdown_path": str(md_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "candidate_id": report.get("candidate_id", ""),
        "gate_stage": report.get("gate_stage", ""),
        "recommended_action": report.get("recommended_action", ""),
        "gate_report_path": str(json_path),
        "gate_markdown_path": str(md_path),
        "latest_gate_report_path": str(latest_root_path / "latest_gate_report.json"),
    }
