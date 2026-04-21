from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.services.checkpoint_improvement_master_board import (
    build_checkpoint_improvement_master_board,
    extract_checkpoint_improvement_orchestrator_contract,
)
from backend.services.checkpoint_improvement_reconcile import (
    run_checkpoint_improvement_reconcile_cycle,
)
from backend.services.checkpoint_improvement_telegram_runtime import (
    build_checkpoint_improvement_telegram_runtime,
)
from backend.services.checkpoint_improvement_watch import (
    run_checkpoint_improvement_watch_governance_cycle,
    run_checkpoint_improvement_watch_heavy_cycle,
    run_checkpoint_improvement_watch_light_cycle,
)
from backend.services.event_bus import EventBus, SystemPhaseChanged, WatchError
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_approval_bridge import TelegramApprovalBridge
from backend.services.telegram_state_store import TelegramStateStore


CHECKPOINT_IMPROVEMENT_ORCHESTRATOR_CONTRACT_VERSION = (
    "checkpoint_improvement_orchestrator_v0"
)


def default_checkpoint_improvement_orchestrator_report_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_orchestrator_latest.json"
    )


def default_checkpoint_improvement_orchestrator_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_orchestrator_latest.md"
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


def _status_counts(groups: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in groups:
        status = _to_text(group.get("status")).lower()
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _approval_apply_backlog_counts(store: TelegramStateStore) -> tuple[int, int]:
    counts = _status_counts(store.list_check_groups(limit=1000))
    approval_backlog_count = _to_int(counts.get("pending")) + _to_int(counts.get("held"))
    apply_backlog_count = _to_int(counts.get("approved"))
    return approval_backlog_count, apply_backlog_count


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    tick = _mapping(payload.get("tick"))
    orchestrator_contract = _mapping(payload.get("orchestrator_contract"))

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Orchestrator")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "trigger_state",
        "recommended_next_action",
        "phase_before",
        "phase_after",
        "total_drained_event_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Tick")
    lines.append("")
    for key in (
        "light_trigger_state",
        "governance_trigger_state",
        "heavy_trigger_state",
        "reconcile_trigger_state",
        "approval_backlog_count",
        "apply_backlog_count",
    ):
        lines.append(f"- {key}: `{tick.get(key)}`")
    lines.append("")
    lines.append("## Orchestrator Contract")
    lines.append("")
    for key in (
        "blocking_reason",
        "next_required_action",
        "approval_backlog_count",
        "apply_backlog_count",
        "reconcile_backlog_count",
        "phase_allows_progress",
    ):
        lines.append(f"- {key}: `{orchestrator_contract.get(key)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class CheckpointImprovementOrchestratorLoop:
    def __init__(
        self,
        *,
        system_state_manager: SystemStateManager | None = None,
        telegram_state_store: TelegramStateStore | None = None,
        event_bus: EventBus | None = None,
        telegram_approval_bridge: TelegramApprovalBridge | None = None,
        light_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_light_cycle,
        governance_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_governance_cycle,
        heavy_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_heavy_cycle,
        master_board_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_master_board,
        reconcile_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_reconcile_cycle,
    ) -> None:
        self._system_state_manager = system_state_manager or SystemStateManager()
        runtime_bundle = None
        if telegram_approval_bridge is None:
            runtime_bundle = build_checkpoint_improvement_telegram_runtime()
        self._telegram_state_store = (
            telegram_state_store
            or (runtime_bundle.telegram_state_store if runtime_bundle is not None else TelegramStateStore())
        )
        self._event_bus = event_bus or (runtime_bundle.event_bus if runtime_bundle is not None else EventBus())
        self._telegram_approval_bridge = (
            telegram_approval_bridge
            or (runtime_bundle.telegram_approval_bridge if runtime_bundle is not None else TelegramApprovalBridge(
                telegram_state_store=self._telegram_state_store,
                event_bus=self._event_bus,
            ))
        )
        self._light_cycle_runner = light_cycle_runner
        self._governance_cycle_runner = governance_cycle_runner
        self._heavy_cycle_runner = heavy_cycle_runner
        self._master_board_builder = master_board_builder
        self._reconcile_cycle_runner = reconcile_cycle_runner

    @property
    def system_state_manager(self) -> SystemStateManager:
        return self._system_state_manager

    @property
    def telegram_state_store(self) -> TelegramStateStore:
        return self._telegram_state_store

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def telegram_approval_bridge(self) -> TelegramApprovalBridge:
        return self._telegram_approval_bridge

    def drain_events(self, *, max_events: int | None = None) -> list[Any]:
        return self._telegram_approval_bridge.drain_pending_events(max_events=max_events)

    def run_tick(
        self,
        *,
        now_ts: object | None = None,
        report_path: str | Path | None = None,
        markdown_path: str | Path | None = None,
    ) -> dict[str, Any]:
        run_started_at = _to_text(now_ts, _now_iso())
        report_file = Path(report_path or default_checkpoint_improvement_orchestrator_report_path())
        markdown_file = Path(markdown_path or default_checkpoint_improvement_orchestrator_markdown_path())
        trace_id = f"orchestrator-{uuid4().hex[:12]}"
        state_before = self._system_state_manager.get_state()
        phase_before = _to_text(state_before.get("phase"), "STARTING").upper()

        payload: dict[str, Any] = {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_ORCHESTRATOR_CONTRACT_VERSION,
                "generated_at": run_started_at,
                "trigger_state": "",
                "recommended_next_action": "",
                "phase_before": phase_before,
                "phase_after": phase_before,
                "total_drained_event_count": 0,
                "report_path": str(report_file),
                "system_state_path": str(self._system_state_manager.state_path),
            },
            "tick": {},
            "light_cycle": {},
            "governance_cycle": {},
            "heavy_cycle": {},
            "reconcile_cycle": {},
            "master_board_before_reconcile": {},
            "master_board_after_reconcile": {},
            "orchestrator_contract": {},
        }

        try:
            light_payload = dict(
                self._light_cycle_runner(
                    system_state_manager=self._system_state_manager,
                    event_bus=self._event_bus,
                    now_ts=run_started_at,
                )
            )
            drained_after_light = self.drain_events()

            approval_backlog_count, apply_backlog_count = _approval_apply_backlog_counts(
                self._telegram_state_store
            )
            governance_payload = dict(
                self._governance_cycle_runner(
                    system_state_manager=self._system_state_manager,
                    event_bus=self._event_bus,
                    approval_backlog_count=approval_backlog_count,
                    apply_backlog_count=apply_backlog_count,
                    row_delta=_to_int(_mapping(light_payload.get("summary")).get("row_delta")),
                    now_ts=run_started_at,
                )
            )
            drained_after_governance = self.drain_events()

            approval_backlog_count, apply_backlog_count = _approval_apply_backlog_counts(
                self._telegram_state_store
            )
            heavy_payload = dict(
                self._heavy_cycle_runner(
                    system_state_manager=self._system_state_manager,
                    event_bus=self._event_bus,
                    now_ts=run_started_at,
                )
            )
            drained_after_heavy = self.drain_events()

            master_board_before_reconcile = dict(
                self._master_board_builder(
                    system_state_manager=self._system_state_manager,
                    telegram_state_store=self._telegram_state_store,
                    now_ts=run_started_at,
                )
            )
            reconcile_payload = dict(
                self._reconcile_cycle_runner(
                    system_state_manager=self._system_state_manager,
                    telegram_state_store=self._telegram_state_store,
                    event_bus=self._event_bus,
                    master_board_payload=master_board_before_reconcile,
                    now_ts=run_started_at,
                )
            )
            drained_after_reconcile = self.drain_events()
            master_board_after_reconcile = dict(
                self._master_board_builder(
                    system_state_manager=self._system_state_manager,
                    telegram_state_store=self._telegram_state_store,
                    now_ts=run_started_at,
                )
            )
            orchestrator_contract = extract_checkpoint_improvement_orchestrator_contract(
                master_board_after_reconcile
            )
            state_after = self._system_state_manager.get_state()
        except Exception as exc:
            error_reason = f"orchestrator_tick_error::{exc.__class__.__name__}"
            error_state = self._system_state_manager.transition(
                "DEGRADED",
                reason=error_reason,
                occurred_at=run_started_at,
            )
            self._event_bus.publish(
                WatchError(
                    trace_id=trace_id,
                    occurred_at=run_started_at,
                    payload={
                        "cycle_name": "orchestrator",
                        "error_reason": error_reason,
                    },
                )
            )
            next_phase = _to_text(error_state.get("phase"), phase_before)
            if next_phase != phase_before:
                self._event_bus.publish(
                    SystemPhaseChanged(
                        trace_id=trace_id,
                        occurred_at=run_started_at,
                        payload={
                            "previous_phase": phase_before,
                            "next_phase": next_phase,
                            "reason": error_reason,
                        },
                    )
                )
            drained = self.drain_events()
            payload["summary"]["trigger_state"] = "WATCH_ERROR"
            payload["summary"]["recommended_next_action"] = "inspect_orchestrator_tick_error_and_retry"
            payload["summary"]["phase_after"] = next_phase
            payload["summary"]["total_drained_event_count"] = len(drained)
            payload["tick"] = {
                "light_trigger_state": "",
                "governance_trigger_state": "",
                "heavy_trigger_state": "",
                "reconcile_trigger_state": "",
                "approval_backlog_count": 0,
                "apply_backlog_count": 0,
            }
            _write_json(report_file, payload)
            _write_text(markdown_file, _render_markdown(payload))
            return payload

        total_drained_event_count = (
            len(drained_after_light)
            + len(drained_after_governance)
            + len(drained_after_heavy)
            + len(drained_after_reconcile)
        )
        payload["summary"]["trigger_state"] = "ORCHESTRATOR_TICK_COMPLETED"
        payload["summary"]["recommended_next_action"] = _to_text(
            orchestrator_contract.get("next_required_action"),
            "continue_checkpoint_improvement_orchestrator_ticks",
        )
        payload["summary"]["phase_after"] = _to_text(state_after.get("phase"), phase_before)
        payload["summary"]["total_drained_event_count"] = total_drained_event_count
        payload["tick"] = {
            "light_trigger_state": _to_text(_mapping(light_payload.get("summary")).get("trigger_state")),
            "governance_trigger_state": _to_text(
                _mapping(governance_payload.get("summary")).get("trigger_state")
            ),
            "heavy_trigger_state": _to_text(_mapping(heavy_payload.get("summary")).get("trigger_state")),
            "reconcile_trigger_state": _to_text(
                _mapping(reconcile_payload.get("summary")).get("trigger_state")
            ),
            "approval_backlog_count": _to_int(orchestrator_contract.get("approval_backlog_count")),
            "apply_backlog_count": _to_int(orchestrator_contract.get("apply_backlog_count")),
        }
        payload["light_cycle"] = light_payload
        payload["governance_cycle"] = governance_payload
        payload["heavy_cycle"] = heavy_payload
        payload["reconcile_cycle"] = reconcile_payload
        payload["master_board_before_reconcile"] = master_board_before_reconcile
        payload["master_board_after_reconcile"] = master_board_after_reconcile
        payload["orchestrator_contract"] = orchestrator_contract
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_markdown(payload))
        return payload


def run_checkpoint_improvement_orchestrator_tick(
    *,
    system_state_manager: SystemStateManager | None = None,
    telegram_state_store: TelegramStateStore | None = None,
    event_bus: EventBus | None = None,
    telegram_approval_bridge: TelegramApprovalBridge | None = None,
    light_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_light_cycle,
    governance_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_governance_cycle,
    heavy_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_watch_heavy_cycle,
    master_board_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_master_board,
    reconcile_cycle_runner: Callable[..., Mapping[str, Any]] = run_checkpoint_improvement_reconcile_cycle,
    now_ts: object | None = None,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    loop = CheckpointImprovementOrchestratorLoop(
        system_state_manager=system_state_manager,
        telegram_state_store=telegram_state_store,
        event_bus=event_bus,
        telegram_approval_bridge=telegram_approval_bridge,
        light_cycle_runner=light_cycle_runner,
        governance_cycle_runner=governance_cycle_runner,
        heavy_cycle_runner=heavy_cycle_runner,
        master_board_builder=master_board_builder,
        reconcile_cycle_runner=reconcile_cycle_runner,
    )
    return loop.run_tick(
        now_ts=now_ts,
        report_path=report_path,
        markdown_path=markdown_path,
    )
