"""Execution policy integration recommendation scaffold for state25 candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.teacher_pattern_candidate_pipeline import DEFAULT_CANDIDATE_ROOT


DEFAULT_LATEST_GATE_REPORT_PATH = DEFAULT_CANDIDATE_ROOT / "latest_gate_report.json"
DEFAULT_RUNTIME_STATUS_PATH = Path("data") / "runtime_status.json"
DEFAULT_EXECUTION_STAGE_ALLOWLIST = ["PROBE", "READY"]
DEFAULT_EXECUTION_SYMBOL_ALLOWLIST = ["BTCUSD", "NAS100"]


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


def _task_ready(compare_report: dict[str, Any], task_name: str) -> bool:
    task = dict(((compare_report.get("tasks", {}) or {}).get(task_name, {})) or {})
    candidate = dict(task.get("candidate", {}) or {})
    return bool(candidate.get("ready", False))


def _runtime_snapshot(runtime_status: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(runtime_status or {})
    semantic_config = dict(payload.get("semantic_live_config", {}) or {})
    return {
        "available": bool(payload),
        "entry_threshold": _to_float(payload.get("entry_threshold", 0.0), 0.0),
        "exit_threshold": _to_float(payload.get("exit_threshold", 0.0), 0.0),
        "semantic_mode": str(semantic_config.get("mode", "")),
        "symbol_allowlist": list(semantic_config.get("symbol_allowlist", []) or []),
        "entry_stage_allowlist": list(semantic_config.get("entry_stage_allowlist", []) or []),
    }


def build_teacher_pattern_execution_policy_integration_report(
    gate_report: dict[str, Any],
    *,
    compare_report: dict[str, Any] | None = None,
    runtime_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate_report or {})
    compare = dict(compare_report or {})
    runtime = _runtime_snapshot(runtime_status)
    gate_stage = str(gate.get("gate_stage", ""))
    recommended_action = str(gate.get("recommended_action", ""))

    economic_ready = _task_ready(compare, "economic_total_task")
    wait_quality_ready = _task_ready(compare, "wait_quality_task")
    belief_outcome_ready = _task_ready(compare, "belief_outcome_task")
    barrier_outcome_ready = _task_ready(compare, "barrier_outcome_task")
    pattern_ready = _task_ready(compare, "pattern_task")
    group_ready = _task_ready(compare, "group_task")
    forecast_transition_ready = _task_ready(compare, "forecast_transition_task")
    forecast_management_ready = _task_ready(compare, "forecast_management_task")

    current_symbols = runtime["symbol_allowlist"] or list(DEFAULT_EXECUTION_SYMBOL_ALLOWLIST)
    current_stages = runtime["entry_stage_allowlist"] or []

    integration_stage = "disabled_hold"
    next_actions: list[str] = []

    if gate_stage in {"hold_offline", "hold_step9"}:
        integration_stage = "disabled_hold"
        next_actions.append("Keep execution binding disabled and continue using the current runtime policy.")
    elif gate_stage == "shadow_only":
        integration_stage = "read_only_recommendation"
        next_actions.append("Keep candidate influence disabled and prepare a read-only execution recommendation only.")
    elif gate_stage == "shadow_ready":
        integration_stage = "read_only_recommendation"
        next_actions.append("Keep execution binding read-only until canary evidence is available.")
    elif gate_stage in {"log_only_ready", "promote_ready"}:
        integration_stage = "log_only_candidate_bind_ready"
        next_actions.append("Enable only log-only candidate policy traces before any bounded live action.")
    elif gate_stage == "rollback_recommended":
        integration_stage = "disabled_rollback_hold"
        next_actions.append("Disable candidate-linked execution policy and keep the current baseline active.")
    else:
        next_actions.append("Keep execution binding disabled until the gate stage becomes explicit.")

    gate_allows_log_only = gate_stage in {"log_only_ready", "promote_ready"}
    threshold_enabled = gate_allows_log_only and economic_ready and pattern_ready and group_ready
    size_enabled = gate_allows_log_only and economic_ready
    wait_enabled = gate_allows_log_only and wait_quality_ready
    risk_enabled = False
    belief_overlay_enabled = gate_allows_log_only and belief_outcome_ready
    barrier_overlay_enabled = gate_allows_log_only and barrier_outcome_ready
    forecast_overlay_enabled = gate_allows_log_only and (
        forecast_transition_ready or forecast_management_ready
    )

    threshold_surface = {
        "enabled": threshold_enabled,
        "mode": "log_only" if threshold_enabled else "disabled",
        "current_entry_threshold": runtime["entry_threshold"],
        "recommended_adjustment_points_max_abs": 4 if threshold_enabled else 0,
        "symbol_scope": list(current_symbols),
        "entry_stage_scope": list(DEFAULT_EXECUTION_STAGE_ALLOWLIST if threshold_enabled else current_stages),
        "reason": (
            "economic_total_task_ready"
            if threshold_enabled
            else "candidate_not_gate_ready_or_economic_task_not_ready"
        ),
    }

    size_surface = {
        "enabled": size_enabled,
        "mode": "log_only" if size_enabled else "disabled",
        "recommended_min_multiplier": 0.75 if size_enabled else 1.0,
        "recommended_max_multiplier": 1.00 if size_enabled else 1.0,
        "symbol_scope": list(current_symbols),
        "reason": (
            "economic_total_task_ready"
            if size_enabled
            else "candidate_not_gate_ready_or_economic_task_not_ready"
        ),
    }

    wait_surface = {
        "enabled": wait_enabled,
        "mode": "log_only" if wait_enabled else "disabled",
        "recommended_policy_scope": "good_wait_preserve_bad_wait_suppress" if wait_enabled else "observe_only",
        "reason": "wait_quality_task_ready" if wait_enabled else "wait_quality_task_not_ready",
    }

    belief_overlay_surface = {
        "enabled": belief_overlay_enabled,
        "mode": "log_only" if belief_overlay_enabled else "disabled",
        "recommended_scope": (
            "hold_wait_flip_reduce_hypothesis_trace"
            if belief_overlay_enabled
            else "observe_only"
        ),
        "recommended_families": (
            ["hold_bias", "wait_bias", "flip_alert", "reduce_alert"]
            if belief_overlay_enabled
            else []
        ),
        "reason": (
            "belief_outcome_auxiliary_task_ready"
            if belief_overlay_enabled
            else "belief_outcome_auxiliary_task_not_ready"
        ),
    }

    barrier_overlay_surface = {
        "enabled": barrier_overlay_enabled,
        "mode": "log_only" if barrier_overlay_enabled else "disabled",
        "recommended_scope": (
            "block_wait_relief_hypothesis_trace"
            if barrier_overlay_enabled
            else "observe_only"
        ),
        "recommended_families": (
            ["block_bias", "wait_bias", "relief_watch", "relief_release_bias"]
            if barrier_overlay_enabled
            else []
        ),
        "reason": (
            "barrier_outcome_auxiliary_task_ready"
            if barrier_overlay_enabled
            else "barrier_outcome_auxiliary_task_not_ready"
        ),
    }

    forecast_overlay_surface = {
        "enabled": forecast_overlay_enabled,
        "mode": "log_only" if forecast_overlay_enabled else "disabled",
        "recommended_scope": (
            "threshold_size_wait_management_hypothesis_trace"
            if forecast_overlay_enabled
            else "observe_only"
        ),
        "transition_task_ready": bool(forecast_transition_ready),
        "management_task_ready": bool(forecast_management_ready),
        "reason": (
            "forecast_state25_auxiliary_task_ready"
            if forecast_overlay_enabled
            else "forecast_state25_auxiliary_tasks_not_ready"
        ),
    }

    risk_surface = {
        "enabled": risk_enabled,
        "mode": "disabled",
        "recommended_scope": "spread_slippage_noise_guard_only",
        "reason": "defer_until_ai5_canary_phase",
    }

    rollout_plan = {
        "current_runtime_mode": runtime["semantic_mode"],
        "recommended_rollout_mode": (
            "log_only"
            if gate_allows_log_only
            else "disabled"
        ),
        "read_only_recommendation": True,
        "log_only_comparison": bool(gate_allows_log_only),
        "narrow_canary_after_log_only": bool(gate_stage == "promote_ready"),
        "bounded_live_action_after_canary": bool(gate_stage == "promote_ready"),
        "symbol_allowlist_target": list(current_symbols),
        "entry_stage_allowlist_target": list(DEFAULT_EXECUTION_STAGE_ALLOWLIST),
    }

    if gate_stage == "log_only_ready":
        next_actions.extend(
            [
                "Open only threshold and size in log_only mode while Step 9 full handoff is still accumulating.",
                "Do not open canary or bounded live yet.",
            ]
        )
    elif gate_stage == "promote_ready":
        next_actions.extend(
            [
                "Start with threshold and size in log_only mode only.",
                "Keep wait-policy binding disabled until wait_quality_task becomes ready.",
                "After one clean log-only cycle, move to a narrow canary on BTCUSD/NAS100 only.",
            ]
        )
    elif gate_stage == "shadow_ready":
        next_actions.append("Run shadow/log-only recommendation traces before exposing any execution surface.")
    elif gate_stage == "rollback_recommended":
        next_actions.append("Do not bind threshold, size, or wait-policy surfaces until the rollback reasons are cleared.")

    return {
        "contract_version": "teacher_pattern_execution_policy_integration_v1",
        "candidate_id": str(gate.get("candidate_id", "")),
        "gate_stage": gate_stage,
        "integration_stage": integration_stage,
        "recommended_action": recommended_action,
        "runtime_snapshot": runtime,
        "task_readiness": {
            "group_task_ready": group_ready,
            "pattern_task_ready": pattern_ready,
            "economic_total_task_ready": economic_ready,
            "wait_quality_task_ready": wait_quality_ready,
            "belief_outcome_task_ready": belief_outcome_ready,
            "barrier_outcome_task_ready": barrier_outcome_ready,
            "forecast_transition_task_ready": forecast_transition_ready,
            "forecast_management_task_ready": forecast_management_ready,
        },
        "recommended_surfaces": {
            "threshold_surface": threshold_surface,
            "size_surface": size_surface,
            "wait_surface": wait_surface,
            "belief_overlay_surface": belief_overlay_surface,
            "barrier_overlay_surface": barrier_overlay_surface,
            "forecast_overlay_surface": forecast_overlay_surface,
            "risk_surface": risk_surface,
        },
        "rollout_plan": rollout_plan,
        "next_actions": next_actions,
        "source_paths": {
            "gate_report_path": str(gate.get("gate_report_path", "")),
            "compare_report_path": str(((gate.get("source_paths", {}) or {}).get("compare_report_path", ""))),
        },
    }


def render_teacher_pattern_execution_policy_integration_markdown(report: dict[str, Any]) -> str:
    runtime = dict(report.get("runtime_snapshot", {}) or {})
    readiness = dict(report.get("task_readiness", {}) or {})
    surfaces = dict(report.get("recommended_surfaces", {}) or {})
    lines = [
        f"# State25 Execution Policy Integration `{report.get('candidate_id', '')}`",
        "",
        "## Integration Summary",
        "",
        f"- gate_stage: `{report.get('gate_stage', '')}`",
        f"- integration_stage: `{report.get('integration_stage', '')}`",
        f"- recommended_action: `{report.get('recommended_action', '')}`",
        "",
        "## Runtime Snapshot",
        "",
        f"- current_semantic_mode: `{runtime.get('semantic_mode', '')}`",
        f"- current_entry_threshold: `{runtime.get('entry_threshold', 0.0)}`",
        f"- current_symbol_allowlist: `{runtime.get('symbol_allowlist', [])}`",
        f"- current_entry_stage_allowlist: `{runtime.get('entry_stage_allowlist', [])}`",
        "",
        "## Task Readiness",
        "",
        f"- group_task_ready: `{readiness.get('group_task_ready', False)}`",
        f"- pattern_task_ready: `{readiness.get('pattern_task_ready', False)}`",
        f"- economic_total_task_ready: `{readiness.get('economic_total_task_ready', False)}`",
        f"- wait_quality_task_ready: `{readiness.get('wait_quality_task_ready', False)}`",
        f"- belief_outcome_task_ready: `{readiness.get('belief_outcome_task_ready', False)}`",
        f"- barrier_outcome_task_ready: `{readiness.get('barrier_outcome_task_ready', False)}`",
        f"- forecast_transition_task_ready: `{readiness.get('forecast_transition_task_ready', False)}`",
        f"- forecast_management_task_ready: `{readiness.get('forecast_management_task_ready', False)}`",
        "",
        "## Recommended Surfaces",
        "",
    ]
    for name in (
        "threshold_surface",
        "size_surface",
        "wait_surface",
        "belief_overlay_surface",
        "barrier_overlay_surface",
        "forecast_overlay_surface",
        "risk_surface",
    ):
        payload = dict(surfaces.get(name, {}) or {})
        lines.append(
            f"- {name}: enabled=`{payload.get('enabled', False)}` mode=`{payload.get('mode', '')}` reason=`{payload.get('reason', '')}`"
        )
    lines.extend(
        [
            "",
            "## Next Actions",
            "",
            f"- next_actions: `{report.get('next_actions', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_teacher_pattern_execution_policy_integration(
    *,
    gate_report_path: str | Path,
    runtime_status_path: str | Path | None = None,
) -> dict[str, Any]:
    gate_path = Path(gate_report_path)
    gate_report = _load_json(gate_path)
    if not gate_report:
        raise FileNotFoundError(f"missing gate report: {gate_path}")

    compare_report_path = ((gate_report.get("source_paths", {}) or {}).get("compare_report_path", ""))
    compare_report = _load_json(compare_report_path)
    runtime_status = _load_json(runtime_status_path)

    report = build_teacher_pattern_execution_policy_integration_report(
        {
            **gate_report,
            "gate_report_path": str(gate_path),
        },
        compare_report=compare_report,
        runtime_status=runtime_status,
    )

    candidate_report_path = str(gate_report.get("gate_report_path", "") or "")
    if candidate_report_path:
        candidate_dir = Path(candidate_report_path).parent
    else:
        compare_report_path = str(((gate_report.get("source_paths", {}) or {}).get("compare_report_path", "")) or "")
        candidate_dir = Path(compare_report_path).parent if compare_report_path else gate_path.parent
    json_path = candidate_dir / "teacher_pattern_execution_policy_integration_report.json"
    md_path = candidate_dir / "teacher_pattern_execution_policy_integration_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_teacher_pattern_execution_policy_integration_markdown(report),
        encoding="utf-8",
    )

    latest_root = Path(DEFAULT_CANDIDATE_ROOT).resolve()
    latest_root.mkdir(parents=True, exist_ok=True)
    latest_path = latest_root / "latest_execution_policy_integration_report.json"
    latest_path.write_text(
        json.dumps(
            {
                **report,
                "execution_policy_report_path": str(json_path),
                "execution_policy_markdown_path": str(md_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "candidate_id": report.get("candidate_id", ""),
        "integration_stage": report.get("integration_stage", ""),
        "recommended_action": report.get("recommended_action", ""),
        "execution_policy_report_path": str(json_path),
        "execution_policy_markdown_path": str(md_path),
        "latest_execution_policy_report_path": str(latest_path),
    }
