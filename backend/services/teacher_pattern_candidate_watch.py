"""Recurring state25 candidate watch loop."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.teacher_pattern_candidate_pipeline import (
    DEFAULT_CANDIDATE_ROOT,
    DEFAULT_CURRENT_BASELINE_DIR,
    run_teacher_pattern_candidate_pipeline,
)
from backend.services.teacher_pattern_pilot_baseline import (
    DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    DEFAULT_MIN_SEED_ROWS,
    DEFAULT_PATTERN_MIN_SUPPORT,
    DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
)
from backend.services.teacher_pattern_promotion_gate import (
    DEFAULT_CANARY_EVIDENCE_PATH,
    DEFAULT_STEP9_WATCH_REPORT_PATH,
    run_teacher_pattern_promotion_gate,
)
from backend.services.teacher_pattern_execution_policy_integration import (
    DEFAULT_RUNTIME_STATUS_PATH,
    run_teacher_pattern_execution_policy_integration,
)
from backend.services.teacher_pattern_execution_policy_log_only_binding import (
    run_teacher_pattern_execution_policy_log_only_binding,
)
from backend.services.teacher_pattern_auto_promote_live_actuator import (
    DEFAULT_ACTIVE_CANDIDATE_STATE_PATH,
    DEFAULT_AUTO_PROMOTE_HISTORY_PATH,
    run_teacher_pattern_auto_promote_live_actuator,
)


DEFAULT_CLOSED_HISTORY_PATH = Path("data") / "trades" / "trade_closed_history.csv"
DEFAULT_OUT_DIR = Path("data") / "analysis" / "teacher_pattern_state25"
DEFAULT_INTERVAL_MIN = 15.0
DEFAULT_MAX_CYCLES = 0


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    json_path = Path(path)
    if not json_path.exists():
        return {}
    return dict(json.loads(json_path.read_text(encoding="utf-8")) or {})


def _runtime_fresh(status_file: Path, max_age_sec: float) -> tuple[bool, float]:
    try:
        mtime = float(status_file.stat().st_mtime)
    except Exception:
        return (False, float("inf"))
    age = max(0.0, time.time() - mtime)
    return (age <= max(1.0, float(max_age_sec)), age)


def build_teacher_pattern_candidate_watch_cycle(
    *,
    cycle: int,
    csv_path: Path,
    runtime_status_path: Path,
    candidate_root: Path,
    reference_metrics_path: Path,
    step9_watch_report_path: Path | None,
    canary_evidence_path: Path | None,
    require_runtime_fresh: bool,
    runtime_max_age_sec: float,
    min_seed_rows: int,
    pattern_min_support: int,
    wait_quality_min_support: int,
    economic_target_min_support: int,
    apply_ai6: bool = False,
) -> dict[str, Any]:
    runtime_ok, runtime_age_sec = _runtime_fresh(runtime_status_path, runtime_max_age_sec)
    cycle_started_at = datetime.now().isoformat(timespec="seconds")

    if require_runtime_fresh and not runtime_ok:
        return {
            "contract_version": "teacher_pattern_candidate_watch_cycle_v1",
            "cycle": int(cycle),
            "started_at": cycle_started_at,
            "status": "runtime_stale_skip",
            "runtime_status": {
                "path": str(runtime_status_path),
                "fresh": bool(runtime_ok),
                "age_sec": round(float(runtime_age_sec), 2),
                "required": True,
                "max_age_sec": float(runtime_max_age_sec),
            },
            "next_actions": [
                "Keep the runtime alive and wait for a fresh heartbeat before the next candidate cycle.",
            ],
        }

    frame = pd.read_csv(csv_path, low_memory=False)
    manifest = run_teacher_pattern_candidate_pipeline(
        frame,
        csv_path=csv_path,
        candidate_root=candidate_root,
        reference_metrics_path=reference_metrics_path,
        min_seed_rows=int(min_seed_rows),
        pattern_min_support=int(pattern_min_support),
        wait_quality_min_support=int(wait_quality_min_support),
        economic_target_min_support=int(economic_target_min_support),
    )
    manifest_path = Path(manifest["output_dir"]) / "teacher_pattern_candidate_run_manifest.json"

    gate_result = run_teacher_pattern_promotion_gate(
        candidate_manifest_path=manifest_path,
        step9_watch_report_path=step9_watch_report_path,
        canary_evidence_path=canary_evidence_path,
    )
    gate_report = _load_json(gate_result["gate_report_path"])

    integration_result = run_teacher_pattern_execution_policy_integration(
        gate_report_path=gate_result["gate_report_path"],
        runtime_status_path=runtime_status_path,
    )
    integration_report = _load_json(integration_result["execution_policy_report_path"])

    binding_result = run_teacher_pattern_execution_policy_log_only_binding(
        execution_policy_report_path=integration_result["execution_policy_report_path"],
    )
    binding_report = _load_json(binding_result["log_only_binding_report_path"])

    ai6_result = run_teacher_pattern_auto_promote_live_actuator(
        gate_report_path=gate_result["gate_report_path"],
        execution_policy_report_path=integration_result["execution_policy_report_path"],
        log_only_binding_report_path=binding_result["log_only_binding_report_path"],
        active_candidate_state_path=Path(candidate_root) / DEFAULT_ACTIVE_CANDIDATE_STATE_PATH.name,
        history_path=Path(candidate_root) / DEFAULT_AUTO_PROMOTE_HISTORY_PATH.name,
        apply=bool(apply_ai6),
    )
    ai6_report = _load_json(ai6_result["auto_promote_report_path"])

    return {
        "contract_version": "teacher_pattern_candidate_watch_cycle_v1",
        "cycle": int(cycle),
        "started_at": cycle_started_at,
        "status": "ran",
        "apply_ai6_requested": bool(apply_ai6),
        "runtime_status": {
            "path": str(runtime_status_path),
            "fresh": bool(runtime_ok),
            "age_sec": round(float(runtime_age_sec), 2),
            "required": bool(require_runtime_fresh),
            "max_age_sec": float(runtime_max_age_sec),
        },
        "candidate": {
            "candidate_id": str(manifest.get("candidate_id", "")),
            "output_dir": str(manifest.get("output_dir", "")),
            "promotion_decision": dict(manifest.get("promotion_decision", {}) or {}),
            "summary_md_path": str(manifest.get("summary_md_path", "")),
        },
        "gate": {
            "gate_stage": str(gate_result.get("gate_stage", "")),
            "recommended_action": str(gate_result.get("recommended_action", "")),
            "report_path": str(gate_result.get("gate_report_path", "")),
            "markdown_path": str(gate_result.get("gate_markdown_path", "")),
            "next_actions": list(gate_report.get("next_actions", []) or []),
        },
        "integration": {
            "integration_stage": str(integration_result.get("integration_stage", "")),
            "recommended_action": str(integration_result.get("recommended_action", "")),
            "report_path": str(integration_result.get("execution_policy_report_path", "")),
            "markdown_path": str(integration_result.get("execution_policy_markdown_path", "")),
            "next_actions": list(integration_report.get("next_actions", []) or []),
        },
        "binding": {
            "binding_mode": str(binding_result.get("binding_mode", "")),
            "report_path": str(binding_result.get("log_only_binding_report_path", "")),
            "markdown_path": str(binding_result.get("log_only_binding_markdown_path", "")),
            "next_actions": list(binding_report.get("next_actions", []) or []),
        },
        "ai6": {
            "controller_stage": str(ai6_result.get("controller_stage", "")),
            "recommended_action": str(ai6_result.get("recommended_action", "")),
            "apply_requested": bool(ai6_result.get("apply_requested", apply_ai6)),
            "applied_action": str(ai6_result.get("applied_action", "")),
            "report_path": str(ai6_result.get("auto_promote_report_path", "")),
            "markdown_path": str(ai6_result.get("auto_promote_markdown_path", "")),
            "active_candidate_state_path": str(
                ai6_result.get("active_candidate_state_path", "")
            ),
            "history_path": str(ai6_result.get("history_path", "")),
            "next_actions": list(ai6_report.get("next_actions", []) or []),
        },
    }


def render_teacher_pattern_candidate_watch_markdown(report: dict[str, Any]) -> str:
    latest = dict(report.get("latest_cycle", {}) or {})
    candidate = dict(latest.get("candidate", {}) or {})
    gate = dict(latest.get("gate", {}) or {})
    integration = dict(latest.get("integration", {}) or {})
    binding = dict(latest.get("binding", {}) or {})
    ai6 = dict(latest.get("ai6", {}) or {})
    runtime = dict(latest.get("runtime_status", {}) or {})

    lines = [
        "# State25 Candidate Watch",
        "",
        "## Latest Cycle",
        "",
        f"- cycle: `{latest.get('cycle', 0)}`",
        f"- status: `{latest.get('status', '')}`",
        f"- runtime_fresh: `{runtime.get('fresh', False)}`",
        f"- runtime_age_sec: `{runtime.get('age_sec', 0.0)}`",
        f"- apply_ai6_requested: `{latest.get('apply_ai6_requested', False)}`",
        f"- candidate_id: `{candidate.get('candidate_id', '')}`",
        f"- candidate_offline_decision: `{dict(candidate.get('promotion_decision', {}) or {}).get('decision', '')}`",
        f"- gate_stage: `{gate.get('gate_stage', '')}`",
        f"- integration_stage: `{integration.get('integration_stage', '')}`",
        f"- binding_mode: `{binding.get('binding_mode', '')}`",
        f"- ai6_controller_stage: `{ai6.get('controller_stage', '')}`",
        f"- ai6_apply_requested: `{ai6.get('apply_requested', False)}`",
        f"- ai6_applied_action: `{ai6.get('applied_action', '')}`",
        f"- ai6_active_candidate_state_path: `{ai6.get('active_candidate_state_path', '')}`",
        f"- ai6_history_path: `{ai6.get('history_path', '')}`",
        "",
        "## Next Actions",
        "",
        f"- gate: `{gate.get('next_actions', [])}`",
        f"- integration: `{integration.get('next_actions', [])}`",
        f"- binding: `{binding.get('next_actions', [])}`",
        f"- ai6: `{ai6.get('next_actions', [])}`",
        "",
    ]
    return "\n".join(lines)


def write_teacher_pattern_candidate_watch_outputs(
    *,
    out_dir: Path,
    report: dict[str, Any],
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "state25_candidate_watch_latest.json"
    md_path = out_dir / "state25_candidate_watch_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_teacher_pattern_candidate_watch_markdown(report), encoding="utf-8")
    return json_path, md_path
