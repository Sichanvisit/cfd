from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_master_board import (
    build_checkpoint_improvement_master_board,
    default_checkpoint_improvement_master_board_json_path,
)
from backend.services.checkpoint_improvement_orchestrator import (
    default_checkpoint_improvement_orchestrator_report_path,
)
from backend.services.system_state_manager import SystemStateManager


CHECKPOINT_IMPROVEMENT_RECOVERY_HEALTH_CONTRACT_VERSION = (
    "checkpoint_improvement_recovery_health_v0"
)


def default_checkpoint_improvement_recovery_health_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_recovery_health_latest.json"
    )


def default_checkpoint_improvement_recovery_health_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_recovery_health_latest.md"
    )


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _parse_iso(value: object) -> datetime | None:
    text = _to_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _age_seconds(now_dt: datetime, value: object) -> int | None:
    dt = _parse_iso(value)
    if dt is None:
        return None
    return max(0, int((now_dt - dt).total_seconds()))


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _artifact_freshness(
    *,
    label: str,
    generated_at: object,
    now_dt: datetime,
    max_age_sec: int,
) -> dict[str, Any]:
    age_sec = _age_seconds(now_dt, generated_at)
    is_stale = age_sec is None or age_sec > max_age_sec
    return {
        "label": label,
        "generated_at": _to_text(generated_at),
        "age_sec": age_sec,
        "is_stale": is_stale,
    }


def _derive_recovery_state(
    *,
    phase: str,
    blocking_reason: str,
    next_required_action: str,
    degraded_components: list[str],
    stale_artifacts: list[str],
    watch_trigger_state: str,
    approval_backlog_count: int,
    apply_backlog_count: int,
) -> tuple[str, str, str, bool, bool]:
    if phase == "EMERGENCY":
        return (
            "RED",
            "ESCALATE_OPERATOR_ACTION",
            "inspect_emergency_state_and_restore_hot_path_before_new_orchestrator_ticks",
            False,
            True,
        )
    if phase == "SHUTDOWN":
        return (
            "YELLOW",
            "SHUTDOWN_PENDING",
            "keep_runner_idle_until_manage_cfd_restart_or_manual_resume",
            False,
            False,
        )
    if phase == "DEGRADED" or degraded_components or watch_trigger_state == "WATCH_ERROR":
        return (
            "YELLOW",
            "RETRY_ORCHESTRATOR_NEXT_TICK",
            "inspect_degraded_components_and_retry_next_orchestrator_tick",
            True,
            False,
        )
    if stale_artifacts:
        return (
            "YELLOW",
            "REFRESH_STALE_ARTIFACTS",
            "refresh_orchestrator_and_master_board_artifacts_before_next_governance_step",
            True,
            False,
        )
    if apply_backlog_count > 0:
        return (
            "GREEN",
            "WAIT_FOR_APPLY_BACKLOG_DRAIN",
            "keep_runner_active_and_drain_approved_apply_backlog",
            False,
            False,
        )
    if approval_backlog_count > 0:
        return (
            "GREEN",
            "WAIT_FOR_APPROVAL_DECISIONS",
            "keep_runner_active_and_process_pending_governance_reviews",
            False,
            False,
        )
    if blocking_reason == "pa8_live_window_pending":
        if next_required_action == "wait_for_new_pa8_candidate_rows_or_market_reopen":
            return (
                "GREEN",
                "WAIT_FOR_PA8_LIVE_WINDOW",
                "keep_runner_active_and_wait_for_new_pa8_candidate_rows_or_market_reopen",
                False,
                False,
            )
        return (
            "GREEN",
            "WAIT_FOR_PA8_LIVE_WINDOW",
            "keep_runner_active_and_wait_for_post_activation_live_rows",
            False,
            False,
        )
    if blocking_reason == "pa7_review_backlog":
        return (
            "GREEN",
            "WAIT_FOR_PA7_REVIEW_BACKLOG",
            "keep_runner_active_and_continue_collecting_rows_before_pa7_review",
            False,
            False,
        )
    return (
        "GREEN",
        "HEALTHY_CONTINUE",
        "continue_checkpoint_improvement_orchestrator_ticks",
        False,
        False,
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    health_state = _mapping(payload.get("health_state"))
    recovery_state = _mapping(payload.get("recovery_state"))
    freshness = list(payload.get("artifact_freshness", []) or [])

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Recovery Health")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "overall_status",
        "recovery_state",
        "recommended_next_action",
        "blocking_reason",
        "approval_backlog_count",
        "apply_backlog_count",
        "reconcile_backlog_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Health")
    lines.append("")
    for key in (
        "phase",
        "telegram_healthy",
        "watch_trigger_state",
        "last_error",
        "degraded_components",
        "stale_artifacts",
    ):
        lines.append(f"- {key}: `{health_state.get(key)}`")
    lines.append("")
    lines.append("## Recovery")
    lines.append("")
    for key in (
        "runner_should_continue",
        "retry_recommended",
        "operator_action_required",
        "recovery_reason",
    ):
        lines.append(f"- {key}: `{recovery_state.get(key)}`")
    lines.append("")
    lines.append("## Artifact Freshness")
    lines.append("")
    if freshness:
        for row in freshness:
            row_map = _mapping(row)
            lines.append(
                f"- `{_to_text(row_map.get('label'))}` age_sec=`{row_map.get('age_sec')}` stale=`{row_map.get('is_stale')}`"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_checkpoint_improvement_recovery_health(
    *,
    system_state_manager: SystemStateManager | None = None,
    master_board_payload: Mapping[str, Any] | None = None,
    orchestrator_payload: Mapping[str, Any] | None = None,
    master_board_builder=build_checkpoint_improvement_master_board,
    master_board_path: str | Path | None = None,
    orchestrator_report_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
    max_artifact_age_sec: int = 900,
    now_ts: object | None = None,
) -> dict[str, Any]:
    manager = system_state_manager or SystemStateManager()
    run_at = _to_text(now_ts, _now_iso())
    now_dt = _parse_iso(run_at) or datetime.now().astimezone()

    board = (
        _mapping(master_board_payload)
        if master_board_payload is not None
        else _mapping(
            master_board_builder(
                system_state_manager=manager,
                output_json_path=master_board_path or default_checkpoint_improvement_master_board_json_path(),
            )
        )
    )
    orchestrator = (
        _mapping(orchestrator_payload)
        if orchestrator_payload is not None
        else _load_json(orchestrator_report_path or default_checkpoint_improvement_orchestrator_report_path())
    )
    state = manager.get_state()

    board_summary = _mapping(board.get("summary"))
    board_health = _mapping(board.get("health_state"))
    orchestrator_summary = _mapping(orchestrator.get("summary"))
    tick_summary = _mapping(orchestrator.get("tick"))

    phase = _to_text(state.get("phase"), board_summary.get("phase")).upper() or "STARTING"
    blocking_reason = _to_text(board_summary.get("blocking_reason"))
    next_required_action = _to_text(
        board_summary.get("next_required_action"),
        orchestrator_summary.get("recommended_next_action"),
    )
    degraded_components = list(board_health.get("degraded_components", []) or [])
    telegram_healthy = _to_bool(state.get("telegram_healthy"), _to_bool(board_health.get("telegram_healthy"), True))
    watch_trigger_state = _to_text(orchestrator_summary.get("trigger_state"))

    artifact_freshness = [
        _artifact_freshness(
            label="system_state",
            generated_at=state.get("updated_at"),
            now_dt=now_dt,
            max_age_sec=max_artifact_age_sec,
        ),
        _artifact_freshness(
            label="master_board",
            generated_at=board_summary.get("generated_at"),
            now_dt=now_dt,
            max_age_sec=max_artifact_age_sec,
        ),
        _artifact_freshness(
            label="orchestrator",
            generated_at=orchestrator_summary.get("generated_at"),
            now_dt=now_dt,
            max_age_sec=max_artifact_age_sec,
        ),
    ]
    stale_artifacts = [
        _to_text(row.get("label"))
        for row in artifact_freshness
        if _to_bool(row.get("is_stale"))
    ]

    approval_backlog_count = _to_int(board_summary.get("pending_approval_count")) + _to_int(
        board_summary.get("held_approval_count")
    )
    apply_backlog_count = _to_int(board_summary.get("approved_apply_backlog_count"))
    reconcile_backlog_count = _to_int(board_summary.get("reconcile_backlog_count"))

    overall_status, recovery_state_name, recovery_reason, retry_recommended, operator_action_required = (
        _derive_recovery_state(
            phase=phase,
            blocking_reason=blocking_reason,
            next_required_action=next_required_action,
            degraded_components=degraded_components,
            stale_artifacts=stale_artifacts,
            watch_trigger_state=watch_trigger_state,
            approval_backlog_count=approval_backlog_count,
            apply_backlog_count=apply_backlog_count,
        )
    )

    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_RECOVERY_HEALTH_CONTRACT_VERSION,
            "generated_at": run_at,
            "trigger_state": "RECOVERY_HEALTH_REFRESHED",
            "overall_status": overall_status,
            "recovery_state": recovery_state_name,
            "recommended_next_action": next_required_action or recovery_reason,
            "blocking_reason": blocking_reason,
            "approval_backlog_count": approval_backlog_count,
            "apply_backlog_count": apply_backlog_count,
            "reconcile_backlog_count": reconcile_backlog_count,
            "report_path": str(output_json_path or default_checkpoint_improvement_recovery_health_json_path()),
        },
        "health_state": {
            "phase": phase,
            "telegram_healthy": telegram_healthy,
            "watch_trigger_state": watch_trigger_state,
            "last_error": _to_text(state.get("last_error"), board_health.get("last_error")),
            "degraded_components": degraded_components,
            "stale_artifacts": stale_artifacts,
            "orchestrator_trigger_state": _to_text(orchestrator_summary.get("trigger_state")),
            "light_trigger_state": _to_text(tick_summary.get("light_trigger_state")),
            "governance_trigger_state": _to_text(tick_summary.get("governance_trigger_state")),
            "heavy_trigger_state": _to_text(tick_summary.get("heavy_trigger_state")),
            "reconcile_trigger_state": _to_text(tick_summary.get("reconcile_trigger_state")),
        },
        "recovery_state": {
            "recovery_state": recovery_state_name,
            "recovery_reason": recovery_reason,
            "runner_should_continue": phase != "SHUTDOWN",
            "retry_recommended": retry_recommended,
            "operator_action_required": operator_action_required,
        },
        "artifact_freshness": artifact_freshness,
        "artifacts": {
            "system_state_path": str(manager.state_path),
            "master_board_path": str(master_board_path or default_checkpoint_improvement_master_board_json_path()),
            "orchestrator_report_path": str(
                orchestrator_report_path or default_checkpoint_improvement_orchestrator_report_path()
            ),
        },
    }

    json_path = Path(output_json_path or default_checkpoint_improvement_recovery_health_json_path())
    markdown_path = Path(output_markdown_path or default_checkpoint_improvement_recovery_health_markdown_path())
    _write_json(json_path, payload)
    _write_text(markdown_path, _render_markdown(payload))
    return payload
