"""Phase-2 log-only binding scaffold for state25 execution integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.teacher_pattern_candidate_pipeline import DEFAULT_CANDIDATE_ROOT


DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH = (
    DEFAULT_CANDIDATE_ROOT / "latest_execution_policy_integration_report.json"
)


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    json_path = Path(path)
    if not json_path.exists():
        return {}
    return dict(json.loads(json_path.read_text(encoding="utf-8")) or {})


def build_teacher_pattern_execution_policy_log_only_binding_report(
    execution_report: dict[str, Any],
) -> dict[str, Any]:
    report = dict(execution_report or {})
    candidate_id = str(report.get("candidate_id", ""))
    integration_stage = str(report.get("integration_stage", ""))
    surfaces = dict(report.get("recommended_surfaces", {}) or {})
    runtime_snapshot = dict(report.get("runtime_snapshot", {}) or {})
    rollout_plan = dict(report.get("rollout_plan", {}) or {})

    threshold_surface = dict(surfaces.get("threshold_surface", {}) or {})
    size_surface = dict(surfaces.get("size_surface", {}) or {})
    wait_surface = dict(surfaces.get("wait_surface", {}) or {})
    belief_overlay_surface = dict(surfaces.get("belief_overlay_surface", {}) or {})
    barrier_overlay_surface = dict(surfaces.get("barrier_overlay_surface", {}) or {})
    forecast_overlay_surface = dict(surfaces.get("forecast_overlay_surface", {}) or {})

    ready_for_log_only = integration_stage == "log_only_candidate_bind_ready"
    binding_mode = "log_only" if ready_for_log_only else "disabled"
    blockers: list[str] = []
    next_actions: list[str] = []

    if not ready_for_log_only:
        blockers.append("integration_stage_not_log_only_ready")
        next_actions.append("Keep the log-only binding disabled until AI4 reaches promote_ready.")

    threshold_binding = {
        "enabled": bool(ready_for_log_only and threshold_surface.get("enabled", False)),
        "mode": "log_only" if ready_for_log_only and threshold_surface.get("enabled", False) else "disabled",
        "symbol_scope": list(threshold_surface.get("symbol_scope", []) or []),
        "entry_stage_scope": list(threshold_surface.get("entry_stage_scope", []) or []),
        "max_adjustment_points_abs": int(threshold_surface.get("recommended_adjustment_points_max_abs", 0) or 0),
        "baseline_entry_threshold": float(threshold_surface.get("current_entry_threshold", 0.0) or 0.0),
        "reason": str(threshold_surface.get("reason", "")),
    }
    size_binding = {
        "enabled": bool(ready_for_log_only and size_surface.get("enabled", False)),
        "mode": "log_only" if ready_for_log_only and size_surface.get("enabled", False) else "disabled",
        "symbol_scope": list(size_surface.get("symbol_scope", []) or []),
        "min_multiplier": float(size_surface.get("recommended_min_multiplier", 1.0) or 1.0),
        "max_multiplier": float(size_surface.get("recommended_max_multiplier", 1.0) or 1.0),
        "reason": str(size_surface.get("reason", "")),
    }
    wait_binding = {
        "enabled": False,
        "mode": "disabled",
        "reason": (
            "phase2_threshold_size_first"
            if bool(wait_surface)
            else "wait_surface_unavailable"
        ),
    }
    belief_overlay_binding = {
        "enabled": bool(ready_for_log_only and belief_overlay_surface.get("enabled", False)),
        "mode": (
            "log_only"
            if ready_for_log_only and belief_overlay_surface.get("enabled", False)
            else "disabled"
        ),
        "recommended_scope": str(
            belief_overlay_surface.get("recommended_scope", "observe_only")
            or "observe_only"
        ),
        "recommended_families": list(
            belief_overlay_surface.get("recommended_families", []) or []
        ),
        "reason": str(belief_overlay_surface.get("reason", "")),
    }
    barrier_overlay_binding = {
        "enabled": bool(ready_for_log_only and barrier_overlay_surface.get("enabled", False)),
        "mode": (
            "log_only"
            if ready_for_log_only and barrier_overlay_surface.get("enabled", False)
            else "disabled"
        ),
        "recommended_scope": str(
            barrier_overlay_surface.get("recommended_scope", "observe_only")
            or "observe_only"
        ),
        "recommended_families": list(
            barrier_overlay_surface.get("recommended_families", []) or []
        ),
        "reason": str(barrier_overlay_surface.get("reason", "")),
    }
    forecast_overlay_binding = {
        "enabled": bool(ready_for_log_only and forecast_overlay_surface.get("enabled", False)),
        "mode": (
            "log_only"
            if ready_for_log_only and forecast_overlay_surface.get("enabled", False)
            else "disabled"
        ),
        "recommended_scope": str(
            forecast_overlay_surface.get("recommended_scope", "observe_only")
            or "observe_only"
        ),
        "transition_task_ready": bool(
            forecast_overlay_surface.get("transition_task_ready", False)
        ),
        "management_task_ready": bool(
            forecast_overlay_surface.get("management_task_ready", False)
        ),
        "reason": str(forecast_overlay_surface.get("reason", "")),
    }

    proposed_runtime_patch = {
        "apply_now": False,
        "state25_execution_bind_mode": binding_mode,
        "state25_execution_symbol_allowlist": list(
            rollout_plan.get("symbol_allowlist_target", runtime_snapshot.get("symbol_allowlist", [])) or []
        ),
        "state25_execution_entry_stage_allowlist": list(
            rollout_plan.get("entry_stage_allowlist_target", []) or []
        ),
        "state25_threshold_log_only_enabled": bool(threshold_binding["enabled"]),
        "state25_threshold_log_only_max_adjustment_abs": int(threshold_binding["max_adjustment_points_abs"]),
        "state25_size_log_only_enabled": bool(size_binding["enabled"]),
        "state25_size_log_only_min_multiplier": float(size_binding["min_multiplier"]),
        "state25_size_log_only_max_multiplier": float(size_binding["max_multiplier"]),
        "state25_belief_overlay_log_only_enabled": bool(belief_overlay_binding["enabled"]),
        "state25_barrier_overlay_log_only_enabled": bool(barrier_overlay_binding["enabled"]),
    }

    if ready_for_log_only:
        next_actions.extend(
            [
                "Keep threshold binding in log_only first.",
                "Keep size binding in log_only first.",
                "Do not bind wait policy in phase 2 yet.",
            ]
        )

    return {
        "contract_version": "teacher_pattern_execution_policy_log_only_binding_v1",
        "candidate_id": candidate_id,
        "integration_stage": integration_stage,
        "binding_mode": binding_mode,
        "threshold_binding": threshold_binding,
        "size_binding": size_binding,
        "wait_binding": wait_binding,
        "belief_overlay_binding": belief_overlay_binding,
        "barrier_overlay_binding": barrier_overlay_binding,
        "forecast_overlay_binding": forecast_overlay_binding,
        "proposed_runtime_patch": proposed_runtime_patch,
        "blockers": blockers,
        "next_actions": next_actions,
        "source_paths": {
            "execution_policy_report_path": str(report.get("execution_policy_report_path", "")),
        },
    }


def render_teacher_pattern_execution_policy_log_only_binding_markdown(report: dict[str, Any]) -> str:
    threshold = dict(report.get("threshold_binding", {}) or {})
    size = dict(report.get("size_binding", {}) or {})
    wait = dict(report.get("wait_binding", {}) or {})
    belief_overlay = dict(report.get("belief_overlay_binding", {}) or {})
    barrier_overlay = dict(report.get("barrier_overlay_binding", {}) or {})
    forecast_overlay = dict(report.get("forecast_overlay_binding", {}) or {})
    lines = [
        f"# State25 Execution Log-Only Binding `{report.get('candidate_id', '')}`",
        "",
        "## Binding Summary",
        "",
        f"- integration_stage: `{report.get('integration_stage', '')}`",
        f"- binding_mode: `{report.get('binding_mode', '')}`",
        f"- blockers: `{report.get('blockers', [])}`",
        "",
        "## Threshold Binding",
        "",
        f"- enabled: `{threshold.get('enabled', False)}`",
        f"- mode: `{threshold.get('mode', '')}`",
        f"- symbol_scope: `{threshold.get('symbol_scope', [])}`",
        f"- entry_stage_scope: `{threshold.get('entry_stage_scope', [])}`",
        f"- max_adjustment_points_abs: `{threshold.get('max_adjustment_points_abs', 0)}`",
        "",
        "## Size Binding",
        "",
        f"- enabled: `{size.get('enabled', False)}`",
        f"- mode: `{size.get('mode', '')}`",
        f"- symbol_scope: `{size.get('symbol_scope', [])}`",
        f"- min_multiplier: `{size.get('min_multiplier', 1.0)}`",
        f"- max_multiplier: `{size.get('max_multiplier', 1.0)}`",
        "",
        "## Wait Binding",
        "",
        f"- enabled: `{wait.get('enabled', False)}`",
        f"- mode: `{wait.get('mode', '')}`",
        f"- reason: `{wait.get('reason', '')}`",
            "",
            "## Belief Overlay Binding",
            "",
        f"- enabled: `{belief_overlay.get('enabled', False)}`",
        f"- mode: `{belief_overlay.get('mode', '')}`",
        f"- recommended_scope: `{belief_overlay.get('recommended_scope', '')}`",
            f"- reason: `{belief_overlay.get('reason', '')}`",
            "",
            "## Barrier Overlay Binding",
            "",
            f"- enabled: `{barrier_overlay.get('enabled', False)}`",
            f"- mode: `{barrier_overlay.get('mode', '')}`",
            f"- recommended_scope: `{barrier_overlay.get('recommended_scope', '')}`",
            f"- recommended_families: `{barrier_overlay.get('recommended_families', [])}`",
            f"- reason: `{barrier_overlay.get('reason', '')}`",
            "",
            "## Forecast Overlay Binding",
            "",
        f"- enabled: `{forecast_overlay.get('enabled', False)}`",
        f"- mode: `{forecast_overlay.get('mode', '')}`",
        f"- recommended_scope: `{forecast_overlay.get('recommended_scope', '')}`",
        f"- reason: `{forecast_overlay.get('reason', '')}`",
        "",
        "## Next Actions",
        "",
        f"- next_actions: `{report.get('next_actions', [])}`",
        "",
    ]
    return "\n".join(lines)


def run_teacher_pattern_execution_policy_log_only_binding(
    *,
    execution_policy_report_path: str | Path,
) -> dict[str, Any]:
    report_path = Path(execution_policy_report_path)
    execution_report = _load_json(report_path)
    if not execution_report:
        raise FileNotFoundError(f"missing execution policy report: {report_path}")

    binding_report = build_teacher_pattern_execution_policy_log_only_binding_report(
        {
            **execution_report,
            "execution_policy_report_path": str(report_path),
        }
    )

    candidate_report_path = str(execution_report.get("execution_policy_report_path", "") or "")
    if candidate_report_path:
        candidate_dir = Path(candidate_report_path).parent
    else:
        candidate_dir = report_path.parent

    json_path = candidate_dir / "teacher_pattern_execution_policy_log_only_binding_report.json"
    md_path = candidate_dir / "teacher_pattern_execution_policy_log_only_binding_report.md"
    json_path.write_text(json.dumps(binding_report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_teacher_pattern_execution_policy_log_only_binding_markdown(binding_report),
        encoding="utf-8",
    )

    latest_root = Path(DEFAULT_CANDIDATE_ROOT).resolve()
    latest_root.mkdir(parents=True, exist_ok=True)
    latest_path = latest_root / "latest_execution_policy_log_only_binding_report.json"
    latest_path.write_text(
        json.dumps(
            {
                **binding_report,
                "log_only_binding_report_path": str(json_path),
                "log_only_binding_markdown_path": str(md_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "candidate_id": binding_report.get("candidate_id", ""),
        "binding_mode": binding_report.get("binding_mode", ""),
        "log_only_binding_report_path": str(json_path),
        "log_only_binding_markdown_path": str(md_path),
        "latest_log_only_binding_report_path": str(latest_path),
    }
