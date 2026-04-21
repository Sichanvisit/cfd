from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.services.checkpoint_improvement_orchestrator import (
    CheckpointImprovementOrchestratorLoop,
)
from backend.services.checkpoint_improvement_first_symbol_focus_runtime import (
    build_checkpoint_improvement_first_symbol_focus_runtime,
)
from backend.services.checkpoint_improvement_pa7_narrow_review_runtime import (
    build_checkpoint_improvement_pa7_narrow_review_runtime,
)
from backend.services.checkpoint_improvement_p5_observation_runtime import (
    build_checkpoint_improvement_p5_observation_runtime,
)
from backend.services.checkpoint_pa8_live_window_fill_lane import (
    build_checkpoint_pa8_live_window_fill_lane,
)
from backend.services.checkpoint_pa8_rollback_approval_cleanup_lane import (
    build_checkpoint_pa8_rollback_approval_cleanup_lane,
)
from backend.services.checkpoint_improvement_recovery_health import (
    build_checkpoint_improvement_recovery_health,
)


CHECKPOINT_IMPROVEMENT_ORCHESTRATOR_WATCH_CONTRACT_VERSION = (
    "checkpoint_improvement_orchestrator_watch_v0"
)


def default_checkpoint_improvement_orchestrator_watch_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_orchestrator_watch_latest.json"
    )


def default_checkpoint_improvement_orchestrator_watch_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_orchestrator_watch_latest.md"
    )


def default_runtime_status_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "runtime_status.json"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


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


def _runtime_freshness(
    *,
    runtime_status_path: str | Path,
    now_ts: object | None = None,
    runtime_max_age_sec: float = 180.0,
) -> dict[str, Any]:
    path = Path(runtime_status_path)
    now_dt = _parse_iso(now_ts) or datetime.now().astimezone()
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "fresh": False,
            "age_sec": None,
            "reason": "runtime_status_missing",
        }
    age_sec = max(0.0, (now_dt - datetime.fromtimestamp(path.stat().st_mtime).astimezone()).total_seconds())
    return {
        "path": str(path),
        "exists": True,
        "fresh": age_sec <= float(runtime_max_age_sec),
        "age_sec": int(age_sec),
        "reason": "runtime_status_fresh" if age_sec <= float(runtime_max_age_sec) else "runtime_status_stale",
    }


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    runtime_gate = _mapping(payload.get("runtime_gate"))
    orchestrator_summary = _mapping(_mapping(payload.get("orchestrator_tick")).get("summary"))
    health_summary = _mapping(_mapping(payload.get("recovery_health")).get("summary"))
    p5_summary = _mapping(_mapping(payload.get("p5_observation")).get("summary"))
    focus_summary = _mapping(_mapping(payload.get("first_symbol_focus")).get("summary"))
    pa7_summary = _mapping(_mapping(payload.get("pa7_narrow_review")).get("summary"))
    pa8_fill_summary = _mapping(_mapping(payload.get("pa8_live_window_fill")).get("summary"))
    pa8_cleanup_summary = _mapping(
        _mapping(payload.get("pa8_rollback_approval_cleanup")).get("summary")
    )

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Orchestrator Watch")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "trigger_state",
        "recommended_next_action",
        "cycle_index",
        "runtime_status_fresh",
        "overall_health_status",
        "recovery_state",
        "p5_trigger_state",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Runtime Gate")
    lines.append("")
    for key in ("exists", "fresh", "age_sec", "reason"):
        lines.append(f"- {key}: `{runtime_gate.get(key)}`")
    lines.append("")
    lines.append("## Orchestrator")
    lines.append("")
    for key in ("trigger_state", "recommended_next_action", "phase_after"):
        lines.append(f"- {key}: `{orchestrator_summary.get(key)}`")
    lines.append("")
    lines.append("## Recovery Health")
    lines.append("")
    for key in ("overall_status", "recovery_state", "recommended_next_action", "blocking_reason"):
        lines.append(f"- {key}: `{health_summary.get(key)}`")
    lines.append("")
    lines.append("## P5 Observation")
    lines.append("")
    for key in ("trigger_state", "recommended_next_action", "first_symbol_status", "first_symbol_symbol", "pa7_narrow_review_status"):
        lines.append(f"- {key}: `{p5_summary.get(key)}`")
    lines.append("")
    lines.append("## First Symbol Focus")
    lines.append("")
    for key in ("trigger_state", "symbol", "status", "progress_pct", "progress_delta_pct", "progress_bucket"):
        lines.append(f"- {key}: `{focus_summary.get(key)}`")
    lines.append("")
    lines.append("## PA7 Narrow Review")
    lines.append("")
    for key in ("trigger_state", "status", "group_count", "primary_symbol", "recommended_next_action"):
        lines.append(f"- {key}: `{pa7_summary.get(key)}`")
    lines.append("")
    lines.append("## PA8 Live Window Fill")
    lines.append("")
    for key in (
        "trigger_state",
        "overall_fill_state",
        "primary_focus_symbol",
        "ready_for_review_count",
        "rollback_pending_count",
        "active_fill_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa8_fill_summary.get(key)}`")
    lines.append("")
    lines.append("## PA8 Rollback Cleanup")
    lines.append("")
    for key in (
        "trigger_state",
        "overall_cleanup_state",
        "primary_cleanup_symbol",
        "approval_backlog_count",
        "rollback_approval_pending_count",
        "closeout_review_candidate_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa8_cleanup_summary.get(key)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class CheckpointImprovementOrchestratorWatchRunner:
    def __init__(
        self,
        *,
        orchestrator_loop: CheckpointImprovementOrchestratorLoop | None = None,
        recovery_health_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_recovery_health,
        p5_observation_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_p5_observation_runtime,
        first_symbol_focus_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_first_symbol_focus_runtime,
        pa7_narrow_review_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_improvement_pa7_narrow_review_runtime,
        pa8_live_window_fill_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_pa8_live_window_fill_lane,
        pa8_rollback_approval_cleanup_builder: Callable[..., Mapping[str, Any]] = build_checkpoint_pa8_rollback_approval_cleanup_lane,
        runtime_status_path: str | Path | None = None,
    ) -> None:
        self._orchestrator_loop = orchestrator_loop or CheckpointImprovementOrchestratorLoop()
        self._recovery_health_builder = recovery_health_builder
        self._p5_observation_builder = p5_observation_builder
        self._first_symbol_focus_builder = first_symbol_focus_builder
        self._pa7_narrow_review_builder = pa7_narrow_review_builder
        self._pa8_live_window_fill_builder = pa8_live_window_fill_builder
        self._pa8_rollback_approval_cleanup_builder = pa8_rollback_approval_cleanup_builder
        self._runtime_status_path = Path(runtime_status_path) if runtime_status_path else default_runtime_status_path()

    @property
    def orchestrator_loop(self) -> CheckpointImprovementOrchestratorLoop:
        return self._orchestrator_loop

    @property
    def runtime_status_path(self) -> Path:
        return self._runtime_status_path

    def run_cycle(
        self,
        *,
        cycle_index: int,
        require_runtime_fresh: bool = False,
        runtime_max_age_sec: float = 180.0,
        now_ts: object | None = None,
        report_path: str | Path | None = None,
        markdown_path: str | Path | None = None,
    ) -> dict[str, Any]:
        run_at = _to_text(now_ts, _now_iso())
        runtime_gate = _runtime_freshness(
            runtime_status_path=self._runtime_status_path,
            now_ts=run_at,
            runtime_max_age_sec=runtime_max_age_sec,
        )

        orchestrator_payload: dict[str, Any]
        if require_runtime_fresh and not _to_bool(runtime_gate.get("fresh")):
            orchestrator_payload = {
                "summary": {
                    "trigger_state": "RUNTIME_STATUS_STALE_WAIT",
                    "recommended_next_action": "wait_for_runtime_status_freshness_before_next_orchestrator_tick",
                    "phase_after": _to_text(
                        self._orchestrator_loop.system_state_manager.get_state().get("phase"),
                        "STARTING",
                    ),
                    "generated_at": run_at,
                },
                "tick": {},
            }
        else:
            orchestrator_payload = dict(self._orchestrator_loop.run_tick(now_ts=run_at))

        recovery_health_payload = dict(
            self._recovery_health_builder(
                system_state_manager=self._orchestrator_loop.system_state_manager,
                orchestrator_payload=orchestrator_payload,
                now_ts=run_at,
            )
        )
        orchestrator_summary = _mapping(orchestrator_payload.get("summary"))
        p5_observation_payload = dict(
            self._p5_observation_builder(
                master_board_payload=_mapping(orchestrator_payload.get("master_board_after_reconcile")),
                now_ts=run_at,
                notify=_to_text(orchestrator_summary.get("trigger_state")) == "ORCHESTRATOR_TICK_COMPLETED",
            )
        )
        first_symbol_focus_payload = dict(
            self._first_symbol_focus_builder(
                master_board_payload=_mapping(orchestrator_payload.get("master_board_after_reconcile")),
                now_ts=run_at,
            )
        )
        pa7_narrow_review_payload = dict(
            self._pa7_narrow_review_builder(
                master_board_payload=_mapping(orchestrator_payload.get("master_board_after_reconcile")),
                now_ts=run_at,
            )
        )
        pa8_live_window_fill_payload = dict(
            self._pa8_live_window_fill_builder(
                master_board_payload=_mapping(orchestrator_payload.get("master_board_after_reconcile")),
                now_ts=run_at,
            )
        )
        pa8_rollback_approval_cleanup_payload = dict(
            self._pa8_rollback_approval_cleanup_builder(
                master_board_payload=_mapping(orchestrator_payload.get("master_board_after_reconcile")),
                now_ts=run_at,
            )
        )
        health_summary = _mapping(recovery_health_payload.get("summary"))
        p5_summary = _mapping(p5_observation_payload.get("summary"))
        focus_summary = _mapping(first_symbol_focus_payload.get("summary"))
        pa7_summary = _mapping(pa7_narrow_review_payload.get("summary"))
        pa8_fill_summary = _mapping(pa8_live_window_fill_payload.get("summary"))
        pa8_cleanup_summary = _mapping(pa8_rollback_approval_cleanup_payload.get("summary"))

        payload: dict[str, Any] = {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_ORCHESTRATOR_WATCH_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": _to_text(orchestrator_summary.get("trigger_state")),
                "recommended_next_action": _to_text(
                    health_summary.get("recommended_next_action"),
                    orchestrator_summary.get("recommended_next_action"),
                ),
                "cycle_index": int(cycle_index),
                "runtime_status_fresh": _to_bool(runtime_gate.get("fresh")),
                "overall_health_status": _to_text(health_summary.get("overall_status")),
                "recovery_state": _to_text(health_summary.get("recovery_state")),
                "p5_trigger_state": _to_text(p5_summary.get("trigger_state")),
                "first_symbol_focus_trigger_state": _to_text(focus_summary.get("trigger_state")),
                "pa7_narrow_review_trigger_state": _to_text(pa7_summary.get("trigger_state")),
                "pa8_live_window_fill_trigger_state": _to_text(pa8_fill_summary.get("trigger_state")),
                "pa8_rollback_cleanup_trigger_state": _to_text(
                    pa8_cleanup_summary.get("trigger_state")
                ),
                "report_path": str(report_path or default_checkpoint_improvement_orchestrator_watch_json_path()),
            },
            "runtime_gate": runtime_gate,
            "orchestrator_tick": orchestrator_payload,
            "recovery_health": recovery_health_payload,
            "p5_observation": p5_observation_payload,
            "first_symbol_focus": first_symbol_focus_payload,
            "pa7_narrow_review": pa7_narrow_review_payload,
            "pa8_live_window_fill": pa8_live_window_fill_payload,
            "pa8_rollback_approval_cleanup": pa8_rollback_approval_cleanup_payload,
        }

        json_path = Path(report_path or default_checkpoint_improvement_orchestrator_watch_json_path())
        markdown_path_value = Path(markdown_path or default_checkpoint_improvement_orchestrator_watch_markdown_path())
        _write_json(json_path, payload)
        _write_text(markdown_path_value, _render_markdown(payload))
        return payload

    def run_forever(
        self,
        *,
        interval_sec: float = 60.0,
        max_cycles: int = 0,
        require_runtime_fresh: bool = False,
        runtime_max_age_sec: float = 180.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        cycle_index = 0
        while True:
            cycle_index += 1
            payload = self.run_cycle(
                cycle_index=cycle_index,
                require_runtime_fresh=require_runtime_fresh,
                runtime_max_age_sec=runtime_max_age_sec,
            )
            history.append(payload)
            if max_cycles > 0 and cycle_index >= max_cycles:
                break
            sleep_fn(max(1.0, float(interval_sec)))
        return history
