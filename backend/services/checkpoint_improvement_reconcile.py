from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.services.checkpoint_improvement_cycle_definition import (
    CYCLE_DEFINITION_CONTRACT_VERSION,
    evaluate_cycle_decision,
)
from backend.services.checkpoint_improvement_master_board import (
    build_checkpoint_improvement_master_board,
    default_checkpoint_improvement_master_board_json_path,
    extract_checkpoint_improvement_orchestrator_contract,
)
from backend.services.event_bus import EventBus, SystemPhaseChanged, WatchError
from backend.services.improvement_status_policy import (
    APPROVAL_ACTIONABLE_STATUSES,
    APPROVAL_CONFLICT_TRACKING_STATUSES,
)
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_state_store import TelegramStateStore


CHECKPOINT_IMPROVEMENT_RECONCILE_CONTRACT_VERSION = (
    "checkpoint_improvement_reconcile_v0"
)
_ACTIONABLE_GROUP_STATUSES = set(APPROVAL_ACTIONABLE_STATUSES)
_SAME_SCOPE_CONFLICT_STATUSES = set(APPROVAL_CONFLICT_TRACKING_STATUSES)


def default_checkpoint_improvement_reconcile_report_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_reconcile_latest.json"
    )


def default_checkpoint_improvement_reconcile_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_reconcile_latest.md"
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


def _publish_phase_change(
    *,
    event_bus: EventBus,
    trace_id: str,
    occurred_at: str,
    previous_phase: str,
    next_phase: str,
    reason: str,
) -> None:
    event_bus.publish(
        SystemPhaseChanged(
            trace_id=trace_id,
            occurred_at=occurred_at,
            payload={
                "previous_phase": previous_phase,
                "next_phase": next_phase,
                "reason": reason,
            },
        )
    )


def _age_seconds(now_dt: datetime, value: object) -> int | None:
    dt = _parse_iso(value)
    if dt is None:
        return None
    return max(0, int((now_dt - dt).total_seconds()))


def _collect_stale_actionable_groups(
    *,
    groups: list[Mapping[str, Any]],
    now_dt: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        status = _to_text(group.get("status")).lower()
        if status not in _ACTIONABLE_GROUP_STATUSES:
            continue
        deadline = _parse_iso(group.get("decision_deadline_ts"))
        if deadline is None or deadline >= now_dt:
            continue
        overdue_age_sec = max(0, int((now_dt - deadline).total_seconds()))
        rows.append(
            {
                "group_id": _to_int(group.get("group_id")),
                "group_key": _to_text(group.get("group_key")),
                "status": status,
                "review_type": _to_text(group.get("review_type")),
                "approval_id": _to_text(group.get("approval_id")),
                "scope_key": _to_text(group.get("scope_key")),
                "decision_deadline_ts": _to_text(group.get("decision_deadline_ts")),
                "overdue_age_sec": overdue_age_sec,
            }
        )
    return rows


def _collect_approved_not_applied_groups(
    *,
    groups: list[Mapping[str, Any]],
    now_dt: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        if _to_text(group.get("status")).lower() != "approved":
            continue
        rows.append(
            {
                "group_id": _to_int(group.get("group_id")),
                "group_key": _to_text(group.get("group_key")),
                "review_type": _to_text(group.get("review_type")),
                "approval_id": _to_text(group.get("approval_id")),
                "scope_key": _to_text(group.get("scope_key")),
                "apply_job_key": _to_text(group.get("apply_job_key")),
                "approval_age_sec": _age_seconds(now_dt, group.get("updated_at")),
            }
        )
    return rows


def _sort_groups_for_scope_resolution(groups: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    def _sort_key(group: Mapping[str, Any]) -> tuple[datetime, int]:
        ts = (
            _parse_iso(group.get("updated_at"))
            or _parse_iso(group.get("last_event_ts"))
            or _parse_iso(group.get("created_at"))
            or datetime.min.astimezone()
        )
        return (ts, _to_int(group.get("group_id")))

    sorted_groups = sorted(groups, key=_sort_key, reverse=True)
    return [dict(group) for group in sorted_groups]


def _collect_same_scope_conflicts(
    *,
    groups: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_scope: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        status = _to_text(group.get("status")).lower()
        scope_key = _to_text(group.get("scope_key"))
        if status not in _SAME_SCOPE_CONFLICT_STATUSES or not scope_key:
            continue
        by_scope.setdefault(scope_key, []).append(dict(group))

    conflicts: list[dict[str, Any]] = []
    for scope_key, scope_groups in by_scope.items():
        if len(scope_groups) <= 1:
            continue
        ordered = _sort_groups_for_scope_resolution(scope_groups)
        canonical = ordered[0]
        for duplicate in ordered[1:]:
            conflicts.append(
                {
                    "scope_key": scope_key,
                    "canonical_group_id": _to_int(canonical.get("group_id")),
                    "canonical_status": _to_text(canonical.get("status")),
                    "duplicate_group_id": _to_int(duplicate.get("group_id")),
                    "duplicate_group_key": _to_text(duplicate.get("group_key")),
                    "duplicate_status": _to_text(duplicate.get("status")),
                    "duplicate_approval_id": _to_text(duplicate.get("approval_id")),
                    "canonical_approval_id": _to_text(canonical.get("approval_id")),
                }
            )
    return conflicts


def _collect_late_callback_invalidations(
    *,
    groups: list[Mapping[str, Any]],
    actions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    group_by_id = {
        _to_int(group.get("group_id")): dict(group)
        for group in groups
        if _to_int(group.get("group_id")) > 0
    }
    rows: list[dict[str, Any]] = []
    for action in actions:
        action_type = _to_text(action.get("action")).lower()
        callback_query_id = _to_text(action.get("callback_query_id"))
        if action_type not in {"approve", "hold", "reject"} or not callback_query_id:
            continue
        group_id = _to_int(action.get("group_id"))
        group = group_by_id.get(group_id, {})
        group_approval_id = _to_text(group.get("approval_id"))
        action_approval_id = _to_text(action.get("approval_id"))
        if not group or not action_approval_id or not group_approval_id or action_approval_id == group_approval_id:
            continue
        rows.append(
            {
                "group_id": group_id,
                "group_key": _to_text(group.get("group_key")),
                "scope_key": _to_text(group.get("scope_key")),
                "current_approval_id": group_approval_id,
                "late_approval_id": action_approval_id,
                "callback_query_id": callback_query_id,
                "action": action_type,
                "created_at": _to_text(action.get("created_at")),
            }
        )
    return rows


def _resolve_same_scope_conflicts(
    *,
    same_scope_conflicts: list[Mapping[str, Any]],
    telegram_state_store: TelegramStateStore,
    run_at: str,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for conflict in same_scope_conflicts:
        duplicate_group_id = _to_int(conflict.get("duplicate_group_id"))
        if duplicate_group_id <= 0:
            continue
        group = telegram_state_store.get_check_group(group_id=duplicate_group_id)
        status = _to_text(group.get("status")).lower()
        if status not in _ACTIONABLE_GROUP_STATUSES:
            continue
        updated_group = telegram_state_store.update_check_group(
            group_id=duplicate_group_id,
            status="cancelled",
            pending_count=0,
            expires_at=run_at,
            last_event_ts=run_at,
        )
        action_record = telegram_state_store.append_check_action(
            group_id=duplicate_group_id,
            telegram_user_id="system_reconcile",
            telegram_username="reconcile",
            action="cancel",
            note=f"same_scope_superseded_by_group_id={_to_int(conflict.get('canonical_group_id'))}",
            callback_query_id="",
            approval_id=_to_text(group.get("approval_id")),
            trace_id=f"reconcile-{duplicate_group_id}",
        )
        resolved.append(
            {
                "duplicate_group_id": duplicate_group_id,
                "scope_key": _to_text(conflict.get("scope_key")),
                "resolution": "cancelled_duplicate_actionable_group",
                "group_after": updated_group,
                "action_record": action_record,
            }
        )
    return resolved


def _recommended_next_action(
    *,
    approved_not_applied_count: int,
    stale_actionable_count: int,
    same_scope_conflict_count: int,
    late_callback_invalidation_count: int,
    board_next_action: str,
) -> str:
    if approved_not_applied_count > 0:
        return "inspect_apply_backlog_and_drain_executor_before_new_reviews"
    if same_scope_conflict_count > 0:
        return "resolve_same_scope_governance_conflicts_before_new_reviews"
    if stale_actionable_count > 0:
        return "expire_or_reopen_stale_governance_approvals_before_new_reviews"
    if late_callback_invalidation_count > 0:
        return "inspect_late_callback_invalidations_and_keep_current_active_approval_ids"
    return _to_text(
        board_next_action,
        "keep_reconcile_placeholder_idle_until_new_backlog_or_signal",
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    reconcile_summary = _mapping(payload.get("reconcile_summary"))
    orchestrator_contract = _mapping(payload.get("orchestrator_contract"))
    stale_rows = list(payload.get("stale_actionable_groups", []) or [])
    approved_rows = list(payload.get("approved_not_applied_groups", []) or [])
    same_scope_rows = list(payload.get("same_scope_conflicts", []) or [])
    late_callback_rows = list(payload.get("late_callback_invalidations", []) or [])

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Reconcile")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "trigger_state",
        "recommended_next_action",
        "approval_backlog_count",
        "apply_backlog_count",
        "reconcile_signal",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Reconcile Summary")
    lines.append("")
    for key in (
        "stale_actionable_count",
        "approved_not_applied_count",
        "same_scope_conflict_count",
        "late_callback_invalidation_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{reconcile_summary.get(key)}`")
    lines.append("")
    lines.append("## Orchestrator Contract")
    lines.append("")
    for key in (
        "blocking_reason",
        "next_required_action",
        "approval_backlog_count",
        "apply_backlog_count",
        "reconcile_backlog_count",
    ):
        lines.append(f"- {key}: `{orchestrator_contract.get(key)}`")
    lines.append("")
    lines.append("## Stale Actionable Groups")
    lines.append("")
    if stale_rows:
        for row in stale_rows:
            row_map = _mapping(row)
            lines.append(
                f"- `{_to_text(row_map.get('group_key'))}` status=`{_to_text(row_map.get('status'))}` overdue_sec=`{row_map.get('overdue_age_sec')}`"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    lines.append("## Approved Not Applied Groups")
    lines.append("")
    if approved_rows:
        for row in approved_rows:
            row_map = _mapping(row)
            lines.append(
                f"- `{_to_text(row_map.get('group_key'))}` review_type=`{_to_text(row_map.get('review_type'))}` age_sec=`{row_map.get('approval_age_sec')}`"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    lines.append("## Same Scope Conflicts")
    lines.append("")
    if same_scope_rows:
        for row in same_scope_rows:
            row_map = _mapping(row)
            lines.append(
                f"- `{_to_text(row_map.get('scope_key'))}` duplicate_group_id=`{row_map.get('duplicate_group_id')}` canonical_group_id=`{row_map.get('canonical_group_id')}`"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    lines.append("## Late Callback Invalidations")
    lines.append("")
    if late_callback_rows:
        for row in late_callback_rows:
            row_map = _mapping(row)
            lines.append(
                f"- `{_to_text(row_map.get('group_key'))}` callback=`{_to_text(row_map.get('callback_query_id'))}` late_approval_id=`{_to_text(row_map.get('late_approval_id'))}`"
            )
    else:
        lines.append("- `none`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_checkpoint_improvement_reconcile_cycle(
    *,
    system_state_manager: SystemStateManager | None = None,
    telegram_state_store: TelegramStateStore | None = None,
    event_bus: EventBus | None = None,
    master_board_payload: Mapping[str, Any] | None = None,
    master_board_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_master_board,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    now_ts: object | None = None,
    cycle_running: bool = False,
    force_run: bool = False,
) -> dict[str, Any]:
    manager = system_state_manager or SystemStateManager()
    store = telegram_state_store or TelegramStateStore()
    bus = event_bus or EventBus()
    report_file = Path(report_path or default_checkpoint_improvement_reconcile_report_path())
    markdown_file = Path(markdown_path or default_checkpoint_improvement_reconcile_markdown_path())
    run_started_at = _to_text(now_ts, _now_iso())
    now_dt = _parse_iso(run_started_at) or datetime.now().astimezone()
    trace_id = f"watch-reconcile-{uuid4().hex[:12]}"

    state_before = manager.get_state()
    current_phase = _to_text(state_before.get("phase"), "STARTING").upper()
    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_RECONCILE_CONTRACT_VERSION,
            "generated_at": run_started_at,
            "trigger_state": "",
            "recommended_next_action": "",
            "approval_backlog_count": 0,
            "apply_backlog_count": 0,
            "reconcile_signal": False,
            "event_count": 0,
            "report_path": str(report_file),
            "system_state_path": str(manager.state_path),
            "master_board_path": str(default_checkpoint_improvement_master_board_json_path()),
        },
        "cycle_decision": {},
        "reconcile_summary": {},
        "orchestrator_contract": {},
        "stale_actionable_groups": [],
        "approved_not_applied_groups": [],
        "same_scope_conflicts": [],
        "late_callback_invalidations": [],
        "same_scope_resolutions": [],
        "state_before": {
            "phase": current_phase,
            "reconcile_last_run": _to_text(state_before.get("reconcile_last_run")),
        },
        "state_after": {},
    }

    try:
        board_payload = (
            _mapping(master_board_payload)
            if master_board_payload is not None
            else _mapping(master_board_builder(
                system_state_manager=manager,
                telegram_state_store=store,
            ))
        )
        orchestrator_contract = extract_checkpoint_improvement_orchestrator_contract(board_payload)
        approval_backlog_count = _to_int(orchestrator_contract.get("approval_backlog_count"))
        apply_backlog_count = _to_int(orchestrator_contract.get("apply_backlog_count"))
        reconcile_signal = bool(orchestrator_contract.get("reconcile_signal"))
        cycle_decision = evaluate_cycle_decision(
            "reconcile",
            system_state=state_before,
            now_ts=run_started_at,
            approval_backlog_count=approval_backlog_count,
            apply_backlog_count=apply_backlog_count,
            reconcile_signal=reconcile_signal,
            cycle_running=cycle_running,
            force_run=force_run,
        )
    except Exception as exc:
        error_reason = f"reconcile_cycle_error::{exc.__class__.__name__}"
        error_state = manager.transition(
            "DEGRADED",
            reason=error_reason,
            occurred_at=run_started_at,
        )
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "reconcile",
                    "error_reason": error_reason,
                    "master_board_path": str(default_checkpoint_improvement_master_board_json_path()),
                },
            )
        )
        if current_phase != _to_text(error_state.get("phase"), current_phase):
            _publish_phase_change(
                event_bus=bus,
                trace_id=trace_id,
                occurred_at=run_started_at,
                previous_phase=current_phase,
                next_phase=_to_text(error_state.get("phase"), current_phase),
                reason=error_reason,
            )
        payload["summary"]["trigger_state"] = "WATCH_ERROR"
        payload["summary"]["recommended_next_action"] = "inspect_reconcile_cycle_error_and_retry"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["state_after"] = {
            "phase": _to_text(error_state.get("phase"), current_phase),
            "reconcile_last_run": _to_text(error_state.get("reconcile_last_run")),
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_markdown(payload))
        return payload

    payload["cycle_decision"] = cycle_decision
    payload["orchestrator_contract"] = orchestrator_contract
    payload["summary"]["approval_backlog_count"] = approval_backlog_count
    payload["summary"]["apply_backlog_count"] = apply_backlog_count
    payload["summary"]["reconcile_signal"] = reconcile_signal

    if not cycle_decision.get("due"):
        payload["summary"]["trigger_state"] = "SKIP_WATCH_DECISION"
        payload["summary"]["recommended_next_action"] = _to_text(
            orchestrator_contract.get("next_required_action"),
            "wait_for_reconcile_signal_or_preferred_interval",
        )
        payload["state_after"] = payload["state_before"]
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_markdown(payload))
        return payload

    groups = store.list_check_groups(limit=1000)
    actions = store.list_recent_check_actions(limit=5000)
    stale_actionable_groups = _collect_stale_actionable_groups(groups=groups, now_dt=now_dt)
    approved_not_applied_groups = _collect_approved_not_applied_groups(groups=groups, now_dt=now_dt)
    same_scope_conflicts = _collect_same_scope_conflicts(groups=groups)
    late_callback_invalidations = _collect_late_callback_invalidations(groups=groups, actions=actions)
    same_scope_resolutions = _resolve_same_scope_conflicts(
        same_scope_conflicts=same_scope_conflicts,
        telegram_state_store=store,
        run_at=run_started_at,
    )
    recommended_next_action = _recommended_next_action(
        approved_not_applied_count=len(approved_not_applied_groups),
        stale_actionable_count=len(stale_actionable_groups),
        same_scope_conflict_count=len(same_scope_conflicts),
        late_callback_invalidation_count=len(late_callback_invalidations),
        board_next_action=_to_text(orchestrator_contract.get("next_required_action")),
    )

    manager.mark_cycle_run("reconcile", run_at=run_started_at)
    state_after = manager.get_state()

    payload["summary"]["trigger_state"] = "RECONCILE_PLACEHOLDER_REFRESHED"
    payload["summary"]["recommended_next_action"] = recommended_next_action
    payload["summary"]["event_count"] = bus.pending_count()
    payload["reconcile_summary"] = {
        "stale_actionable_count": len(stale_actionable_groups),
        "approved_not_applied_count": len(approved_not_applied_groups),
        "same_scope_conflict_count": len(same_scope_conflicts),
        "late_callback_invalidation_count": len(late_callback_invalidations),
        "same_scope_resolution_count": len(same_scope_resolutions),
        "recommended_next_action": recommended_next_action,
    }
    payload["stale_actionable_groups"] = stale_actionable_groups
    payload["approved_not_applied_groups"] = approved_not_applied_groups
    payload["same_scope_conflicts"] = same_scope_conflicts
    payload["late_callback_invalidations"] = late_callback_invalidations
    payload["same_scope_resolutions"] = same_scope_resolutions
    payload["state_after"] = {
        "phase": _to_text(state_after.get("phase"), current_phase),
        "reconcile_last_run": _to_text(state_after.get("reconcile_last_run")),
    }
    _write_json(report_file, payload)
    _write_text(markdown_file, _render_markdown(payload))
    return payload
