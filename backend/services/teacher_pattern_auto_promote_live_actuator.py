"""AI6 auto-promote / rollback / live-actuator dry-run scaffold."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.services.teacher_pattern_candidate_pipeline import DEFAULT_CANDIDATE_ROOT
from backend.services.teacher_pattern_execution_policy_integration import (
    DEFAULT_LATEST_GATE_REPORT_PATH,
)
from backend.services.teacher_pattern_execution_policy_log_only_binding import (
    DEFAULT_LATEST_EXECUTION_POLICY_REPORT_PATH,
)


DEFAULT_LATEST_LOG_ONLY_BINDING_REPORT_PATH = (
    DEFAULT_CANDIDATE_ROOT / "latest_execution_policy_log_only_binding_report.json"
)
DEFAULT_ACTIVE_CANDIDATE_STATE_PATH = DEFAULT_CANDIDATE_ROOT / "active_candidate_state.json"
DEFAULT_AUTO_PROMOTE_HISTORY_PATH = DEFAULT_CANDIDATE_ROOT / "auto_promote_history.jsonl"


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    json_path = Path(path)
    if not json_path.exists():
        return {}
    return dict(json.loads(json_path.read_text(encoding="utf-8")) or {})


def _default_active_state() -> dict[str, Any]:
    return {
        "contract_version": "teacher_pattern_active_candidate_state_v1",
        "active_candidate_id": "",
        "active_policy_source": "current_baseline",
        "current_rollout_phase": "disabled",
        "current_binding_mode": "disabled",
        "activated_at": "",
        "last_event": "none",
        "desired_runtime_patch": {
            "apply_now": False,
            "state25_execution_bind_mode": "disabled",
        },
    }


def build_teacher_pattern_auto_promote_live_actuator_report(
    gate_report: dict[str, Any],
    *,
    execution_policy_report: dict[str, Any] | None = None,
    log_only_binding_report: dict[str, Any] | None = None,
    active_candidate_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(gate_report or {})
    execution = dict(execution_policy_report or {})
    binding = dict(log_only_binding_report or {})
    active = _default_active_state()
    active.update(dict(active_candidate_state or {}))

    candidate_id = str(
        gate.get("candidate_id")
        or execution.get("candidate_id")
        or binding.get("candidate_id")
        or ""
    )
    gate_stage = str(gate.get("gate_stage", ""))
    integration_stage = str(execution.get("integration_stage", ""))
    binding_mode = str(binding.get("binding_mode", ""))

    active_candidate_id = str(active.get("active_candidate_id", ""))
    active_rollout_phase = str(active.get("current_rollout_phase", "disabled"))
    active_binding_mode = str(active.get("current_binding_mode", "disabled"))

    promotion_eligible = (
        gate_stage in {"log_only_ready", "promote_ready"}
        and integration_stage == "log_only_candidate_bind_ready"
        and binding_mode == "log_only"
    )
    already_active_log_only = (
        promotion_eligible
        and active_candidate_id == candidate_id
        and active_rollout_phase == "log_only"
        and active_binding_mode == "log_only"
    )
    rollback_eligible = (
        gate_stage == "rollback_recommended"
        and bool(active_candidate_id)
        and active_candidate_id == candidate_id
    )

    controller_stage = "hold_disabled"
    recommended_action = "keep_current_baseline"
    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    desired_runtime_patch = dict(binding.get("proposed_runtime_patch", {}) or {})
    if not desired_runtime_patch:
        desired_runtime_patch = {
            "apply_now": False,
            "state25_execution_bind_mode": "disabled",
        }

    promote_state_patch = {
        "contract_version": "teacher_pattern_active_candidate_state_v1",
        "active_candidate_id": candidate_id,
        "active_policy_source": "state25_candidate",
        "current_rollout_phase": "log_only",
        "current_binding_mode": "log_only",
        "activated_at": datetime.now().isoformat(timespec="seconds"),
        "last_event": "promote_log_only",
        "previous_candidate_id": active_candidate_id,
        "desired_runtime_patch": {
            **desired_runtime_patch,
            "apply_now": True,
            "state25_execution_bind_mode": "log_only",
        },
    }
    rollback_state_patch = {
        "contract_version": "teacher_pattern_active_candidate_state_v1",
        "active_candidate_id": "",
        "active_policy_source": "current_baseline",
        "current_rollout_phase": "disabled",
        "current_binding_mode": "disabled",
        "activated_at": datetime.now().isoformat(timespec="seconds"),
        "last_event": "rollback_disable",
        "previous_candidate_id": active_candidate_id,
        "desired_runtime_patch": {
            "apply_now": True,
            "state25_execution_bind_mode": "disabled",
            "state25_threshold_log_only_enabled": False,
            "state25_size_log_only_enabled": False,
        },
    }

    if rollback_eligible:
        controller_stage = "rollback_ready"
        recommended_action = "rollback_to_current_baseline"
        next_actions.extend(
            [
                "Disable candidate-linked execution surfaces.",
                "Return the active policy source to the current baseline.",
            ]
        )
    elif already_active_log_only:
        controller_stage = "already_promoted_log_only"
        recommended_action = "continue_log_only_and_collect_canary"
        warnings.append("candidate_already_active_log_only")
        next_actions.extend(
            [
                "Keep the candidate in log-only mode.",
                "Collect canary evidence before any bounded live rollout.",
            ]
        )
    elif promotion_eligible:
        controller_stage = "promote_log_only_ready"
        recommended_action = "promote_candidate_to_log_only"
        next_actions.extend(
            [
                "Promote the candidate into AI5 log-only mode only.",
                "Keep wait-policy binding disabled until wait_quality_task becomes ready.",
                "Collect canary evidence before any bounded live rollout.",
            ]
        )
    else:
        if gate_stage != "promote_ready":
            blockers.append(f"gate_stage:{gate_stage or 'missing'}")
        if integration_stage != "log_only_candidate_bind_ready":
            blockers.append(f"integration_stage:{integration_stage or 'missing'}")
        if binding_mode != "log_only":
            blockers.append(f"binding_mode:{binding_mode or 'missing'}")
        next_actions.append("Keep the current baseline active and continue running AI3-AI5 loops.")

    return {
        "contract_version": "teacher_pattern_auto_promote_live_actuator_v1",
        "candidate_id": candidate_id,
        "gate_stage": gate_stage,
        "integration_stage": integration_stage,
        "binding_mode": binding_mode,
        "controller_stage": controller_stage,
        "recommended_action": recommended_action,
        "current_active_state": {
            "active_candidate_id": active_candidate_id,
            "active_policy_source": str(active.get("active_policy_source", "current_baseline")),
            "current_rollout_phase": active_rollout_phase,
            "current_binding_mode": active_binding_mode,
        },
        "auto_promote_plan": {
            "eligible": bool(promotion_eligible and not already_active_log_only),
            "apply_now": False,
            "target_rollout_phase": "log_only" if promotion_eligible else "disabled",
            "proposed_active_state_patch": promote_state_patch if promotion_eligible else {},
        },
        "rollback_plan": {
            "eligible": bool(rollback_eligible),
            "apply_now": False,
            "rollback_target_policy_source": "current_baseline",
            "proposed_active_state_patch": rollback_state_patch if rollback_eligible else {},
        },
        "live_actuator_plan": {
            "mode": "log_only" if promotion_eligible else "disabled",
            "apply_now": False,
            "proposed_runtime_patch": (
                promote_state_patch["desired_runtime_patch"]
                if promotion_eligible
                else rollback_state_patch["desired_runtime_patch"]
                if rollback_eligible
                else desired_runtime_patch
            ),
        },
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": next_actions,
        "source_paths": {
            "gate_report_path": str(gate.get("gate_report_path", "")),
            "execution_policy_report_path": str(
                execution.get("execution_policy_report_path", "")
            ),
            "log_only_binding_report_path": str(
                binding.get("log_only_binding_report_path", "")
            ),
            "active_candidate_state_path": str(
                active.get("active_candidate_state_path", "")
            ),
        },
    }


def render_teacher_pattern_auto_promote_live_actuator_markdown(
    report: dict[str, Any],
) -> str:
    active = dict(report.get("current_active_state", {}) or {})
    promote = dict(report.get("auto_promote_plan", {}) or {})
    rollback = dict(report.get("rollback_plan", {}) or {})
    actuator = dict(report.get("live_actuator_plan", {}) or {})
    lines = [
        f"# State25 Auto Promote Live Actuator `{report.get('candidate_id', '')}`",
        "",
        "## Controller Summary",
        "",
        f"- gate_stage: `{report.get('gate_stage', '')}`",
        f"- integration_stage: `{report.get('integration_stage', '')}`",
        f"- binding_mode: `{report.get('binding_mode', '')}`",
        f"- controller_stage: `{report.get('controller_stage', '')}`",
        f"- recommended_action: `{report.get('recommended_action', '')}`",
        f"- apply_requested: `{report.get('apply_requested', False)}`",
        f"- applied_action: `{report.get('applied_action', '')}`",
        "",
        "## Current Active State",
        "",
        f"- active_candidate_id: `{active.get('active_candidate_id', '')}`",
        f"- active_policy_source: `{active.get('active_policy_source', '')}`",
        f"- current_rollout_phase: `{active.get('current_rollout_phase', '')}`",
        f"- current_binding_mode: `{active.get('current_binding_mode', '')}`",
        "",
        "## Plans",
        "",
        f"- auto_promote_eligible: `{promote.get('eligible', False)}`",
        f"- rollback_eligible: `{rollback.get('eligible', False)}`",
        f"- live_actuator_mode: `{actuator.get('mode', '')}`",
        "",
        "## Notes",
        "",
        f"- blockers: `{report.get('blockers', [])}`",
        f"- warnings: `{report.get('warnings', [])}`",
        f"- next_actions: `{report.get('next_actions', [])}`",
        "",
    ]
    return "\n".join(lines)


def _append_history(history_path: Path, payload: dict[str, Any]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_teacher_pattern_auto_promote_live_actuator(
    *,
    gate_report_path: str | Path,
    execution_policy_report_path: str | Path,
    log_only_binding_report_path: str | Path,
    active_candidate_state_path: str | Path | None = None,
    history_path: str | Path | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    gate_path = Path(gate_report_path)
    execution_path = Path(execution_policy_report_path)
    binding_path = Path(log_only_binding_report_path)
    state_path = Path(active_candidate_state_path or DEFAULT_ACTIVE_CANDIDATE_STATE_PATH)
    history_log_path = Path(history_path or DEFAULT_AUTO_PROMOTE_HISTORY_PATH)

    gate_report = _load_json(gate_path)
    execution_report = _load_json(execution_path)
    binding_report = _load_json(binding_path)
    active_state = _load_json(state_path)

    if not gate_report:
        raise FileNotFoundError(f"missing gate report: {gate_path}")
    if not execution_report:
        raise FileNotFoundError(f"missing execution policy report: {execution_path}")
    if not binding_report:
        raise FileNotFoundError(f"missing log-only binding report: {binding_path}")

    report = build_teacher_pattern_auto_promote_live_actuator_report(
        {
            **gate_report,
            "gate_report_path": str(gate_path),
        },
        execution_policy_report={
            **execution_report,
            "execution_policy_report_path": str(execution_path),
        },
        log_only_binding_report={
            **binding_report,
            "log_only_binding_report_path": str(binding_path),
        },
        active_candidate_state={
            **active_state,
            "active_candidate_state_path": str(state_path),
        },
    )

    candidate_id = str(report.get("candidate_id", "")) or "unknown_candidate"
    candidate_manifest_path = str(
        (((gate_report.get("source_paths", {}) or {}).get("candidate_manifest_path", "")) or "")
    )
    candidate_dir = (
        Path(candidate_manifest_path).parent
        if candidate_manifest_path
        else gate_path.parent
    )
    json_path = candidate_dir / "teacher_pattern_auto_promote_live_actuator_report.json"
    md_path = candidate_dir / "teacher_pattern_auto_promote_live_actuator_report.md"

    applied_action = "none"
    applied_state_path = ""
    if apply:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        if report.get("controller_stage") == "promote_log_only_ready":
            state_payload = dict(
                ((report.get("auto_promote_plan", {}) or {}).get("proposed_active_state_patch", {}))
                or {}
            )
            state_path.write_text(
                json.dumps(state_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _append_history(
                history_log_path,
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "action": "promote_log_only",
                    "candidate_id": candidate_id,
                    "state_path": str(state_path),
                },
            )
            applied_action = "promote_log_only"
            applied_state_path = str(state_path)
        elif report.get("controller_stage") == "rollback_ready":
            state_payload = dict(
                ((report.get("rollback_plan", {}) or {}).get("proposed_active_state_patch", {}))
                or {}
            )
            state_path.write_text(
                json.dumps(state_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _append_history(
                history_log_path,
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "action": "rollback_disable",
                    "candidate_id": candidate_id,
                    "state_path": str(state_path),
                },
            )
            applied_action = "rollback_disable"
            applied_state_path = str(state_path)

    final_report = {
        **report,
        "apply_requested": bool(apply),
        "applied_action": applied_action,
        "applied_active_state_path": applied_state_path,
        "active_candidate_state_path": str(state_path),
        "history_path": str(history_log_path),
    }

    json_path.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_teacher_pattern_auto_promote_live_actuator_markdown(final_report),
        encoding="utf-8",
    )

    latest_root = Path(DEFAULT_CANDIDATE_ROOT).resolve()
    latest_root.mkdir(parents=True, exist_ok=True)
    latest_path = latest_root / "latest_auto_promote_live_actuator_report.json"
    latest_path.write_text(json.dumps(final_report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "candidate_id": candidate_id,
        "controller_stage": str(final_report.get("controller_stage", "")),
        "recommended_action": str(final_report.get("recommended_action", "")),
        "apply_requested": bool(final_report.get("apply_requested", False)),
        "applied_action": applied_action,
        "auto_promote_report_path": str(json_path),
        "auto_promote_markdown_path": str(md_path),
        "latest_auto_promote_report_path": str(latest_path),
        "active_candidate_state_path": str(state_path),
        "history_path": str(history_log_path),
    }
