from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

import pandas as pd

from backend.services.checkpoint_improvement_cycle_definition import (
    CYCLE_DEFINITION_CONTRACT_VERSION,
    evaluate_cycle_decision,
)
from backend.services.checkpoint_improvement_pa9_handoff_runtime import (
    refresh_checkpoint_improvement_pa9_handoff_runtime,
)
from backend.services.checkpoint_improvement_pa8_closeout_runtime import (
    refresh_checkpoint_improvement_pa8_closeout_runtime,
)
from backend.services.event_bus import (
    EventBus,
    GovernanceActionNeeded,
    LightRefreshCompleted,
    SystemPhaseChanged,
    WatchError,
)
from backend.services.path_checkpoint_analysis_refresh import (
    default_checkpoint_analysis_refresh_report_path,
    default_checkpoint_pa7_review_processor_path,
    maybe_refresh_checkpoint_analysis_chain,
)
from backend.services.path_checkpoint_pa78_review_packet import (
    default_checkpoint_pa78_review_packet_path,
)
from backend.services.path_checkpoint_pa8_canary_refresh import (
    build_checkpoint_pa8_canary_refresh_board,
    default_checkpoint_pa8_canary_refresh_board_json_path,
    load_checkpoint_pa8_canary_refresh_resolved_dataset,
    write_checkpoint_pa8_canary_refresh_outputs,
)
from backend.services.path_checkpoint_context import default_checkpoint_rows_path
from backend.services.path_checkpoint_pa8_action_symbol_review import (
    default_checkpoint_dataset_resolved_path,
)
from backend.services.path_checkpoint_scene_bias_preview import (
    default_checkpoint_trend_exhaustion_scene_bias_preview_path,
)
from backend.services.path_checkpoint_scene_disagreement_audit import (
    default_checkpoint_scene_disagreement_audit_path,
)
from backend.services.system_state_manager import SystemStateManager
from backend.services.trade_csv_schema import now_kst_dt


CHECKPOINT_IMPROVEMENT_WATCH_CONTRACT_VERSION = "checkpoint_improvement_watch_v0"
DEFAULT_CHECKPOINT_IMPROVEMENT_LIGHT_RECENT_LIMIT = 400
DEFAULT_CHECKPOINT_IMPROVEMENT_HEAVY_RECENT_LIMIT = 2000


def default_checkpoint_improvement_watch_report_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_watch_latest.json"
    )


def default_checkpoint_improvement_watch_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_watch_latest.md"
    )


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


def _count_checkpoint_rows(path: str | Path) -> int:
    file_path = Path(path)
    if not file_path.exists():
        return 0
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _latest_checkpoint_row_ts(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    latest_ts = ""
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not isinstance(row, Mapping):
                continue
            candidate = _to_text(row.get("generated_at"))
            if candidate:
                latest_ts = candidate
    return latest_ts


def _skip_recommended_next_action(skip_reason: str) -> str:
    mapping = {
        "checkpoint_rows_missing": "wait_for_checkpoint_rows_before_light_cycle",
        "row_delta_zero": "wait_for_new_checkpoint_rows",
        "cooldown_active": "wait_for_light_cycle_cooldown_or_more_rows",
        "lock_held": "wait_for_refresh_lock_release",
        "cycle_already_running": "wait_for_inflight_light_cycle_completion",
        "sample_floor_not_met": "wait_for_more_recent_samples_before_heavy_cycle",
        "hot_path_unhealthy": "stabilize_hot_path_before_running_heavy_cycle",
    }
    return mapping.get(skip_reason, "inspect_light_cycle_skip_reason_and_retry")


def _extract_heavy_summary(refresh_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    refresh_map = _mapping(refresh_payload)
    chain = _mapping(refresh_map.get("chain"))
    pa7_summary = _mapping(chain.get("pa7_review_processor_summary"))
    if not pa7_summary:
        pa7_summary = _mapping(_load_json(default_checkpoint_pa7_review_processor_path()).get("summary"))
    pa78_summary = _mapping(chain.get("pa78_review_packet_summary"))
    if not pa78_summary:
        pa78_summary = _mapping(_load_json(default_checkpoint_pa78_review_packet_path()).get("summary"))
    disagreement_summary = _mapping(chain.get("scene_disagreement_summary"))
    if not disagreement_summary:
        disagreement_summary = _mapping(_load_json(default_checkpoint_scene_disagreement_audit_path()).get("summary"))
    preview_summary = _mapping(chain.get("scene_bias_preview_summary"))
    if not preview_summary:
        preview_summary = _mapping(_load_json(default_checkpoint_trend_exhaustion_scene_bias_preview_path()).get("summary"))
    return {
        "deep_scene_review_refreshed": _to_bool(chain.get("deep_scene_review_refreshed"), False),
        "pa7_processed_group_count": _to_int(pa7_summary.get("processed_group_count")),
        "pa7_unresolved_review_group_count": _to_int(pa78_summary.get("pa7_unresolved_review_group_count")),
        "pa7_review_state": _to_text(pa78_summary.get("pa7_review_state")),
        "pa8_review_state": _to_text(pa78_summary.get("pa8_review_state")),
        "scene_bias_review_state": _to_text(pa78_summary.get("scene_bias_review_state")),
        "high_conf_scene_disagreement_count": _to_int(disagreement_summary.get("high_conf_scene_disagreement_count")),
        "scene_expected_action_alignment_rate": disagreement_summary.get("expected_action_alignment_rate"),
        "preview_changed_row_count": _to_int(preview_summary.get("preview_changed_row_count")),
        "preview_improved_row_count": _to_int(preview_summary.get("improved_row_count")),
        "preview_worsened_row_count": _to_int(preview_summary.get("worsened_row_count")),
        "recommended_next_action": _to_text(
            pa78_summary.get("recommended_next_action")
            or preview_summary.get("recommended_next_action")
            or pa7_summary.get("recommended_next_action")
        ),
    }


def _render_watch_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    decision = _mapping(body.get("cycle_decision"))
    refresh_summary = _mapping(body.get("refresh_summary"))
    governance_summary = _mapping(body.get("governance_summary"))
    governance_candidates = list(body.get("governance_candidates", []) or [])
    cycle_name = _to_text(summary.get("cycle_name"), "light").lower()

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Watch")
    lines.append("")
    for key in (
        "trigger_state",
        "recommended_next_action",
        "row_count",
        "row_delta",
        "event_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append(f"## {cycle_name.title()} Cycle Decision")
    lines.append("")
    for key in ("due", "decision_reason", "skip_reason", "elapsed_seconds_since_last_run"):
        lines.append(f"- {key}: `{decision.get(key)}`")
    lines.append("")
    if cycle_name == "light":
        lines.append("## Refresh Summary")
        lines.append("")
        for key in ("trigger_state", "recommended_next_action", "row_count_after", "row_delta"):
            lines.append(f"- {key}: `{refresh_summary.get(key)}`")
        lines.append("")
    elif cycle_name == "heavy":
        heavy_summary = _mapping(body.get("heavy_summary"))
        lines.append("## Heavy Summary")
        lines.append("")
        for key in (
            "deep_scene_review_refreshed",
            "pa7_processed_group_count",
            "pa7_unresolved_review_group_count",
            "high_conf_scene_disagreement_count",
            "preview_changed_row_count",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{heavy_summary.get(key)}`")
        lines.append("")
    elif cycle_name == "governance":
        lines.append("## Governance Summary")
        lines.append("")
        for key in (
            "candidate_count",
            "approval_backlog_count",
            "apply_backlog_count",
            "pa8_closeout_review_state",
            "pa8_closeout_apply_state",
            "pa9_handoff_state",
            "pa9_review_state",
            "pa9_apply_state",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{governance_summary.get(key)}`")
        lines.append("")
        lines.append("## Governance Candidates")
        lines.append("")
        if governance_candidates:
            for candidate in governance_candidates:
                candidate_map = _mapping(candidate)
                lines.append(
                    f"- `{_to_text(candidate_map.get('review_type'))}` / `{_to_text(candidate_map.get('symbol'))}` / `{_to_text(candidate_map.get('scope_key'))}`"
                )
        else:
            lines.append("- `none`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_missing_rows_decision(*, row_delta: int) -> dict[str, Any]:
    return {
        "contract_version": CYCLE_DEFINITION_CONTRACT_VERSION,
        "cycle_name": "light",
        "due": False,
        "decision_reason": "",
        "skip_reason": "checkpoint_rows_missing",
        "elapsed_seconds_since_last_run": None,
        "row_delta": max(0, int(row_delta)),
        "sample_count": 0,
        "row_delta_floor": 25,
        "sample_floor": 0,
        "active_pa8_symbol_count": 0,
        "approval_backlog_count": 0,
        "apply_backlog_count": 0,
    }


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


def _recover_running_after_success(
    *,
    state_manager: SystemStateManager,
    event_bus: EventBus,
    trace_id: str,
    occurred_at: str,
    current_phase: str,
    recovery_reason: str,
) -> dict[str, Any]:
    state_after = state_manager.get_state()
    if current_phase != "DEGRADED":
        return state_after
    state_after = state_manager.transition("RUNNING", occurred_at=occurred_at)
    next_phase = _to_text(state_after.get("phase"), current_phase)
    if next_phase != current_phase:
        _publish_phase_change(
            event_bus=event_bus,
            trace_id=trace_id,
            occurred_at=occurred_at,
            previous_phase=current_phase,
            next_phase=next_phase,
            reason=recovery_reason,
        )
    return state_after


def _default_governance_board_loader() -> dict[str, Any]:
    resolved_dataset: pd.DataFrame = load_checkpoint_pa8_canary_refresh_resolved_dataset(
        default_checkpoint_dataset_resolved_path()
    )
    payload = build_checkpoint_pa8_canary_refresh_board(resolved_dataset)
    write_checkpoint_pa8_canary_refresh_outputs(payload)
    return payload


def _candidate_from_governance_row(row: Mapping[str, Any]) -> dict[str, Any] | None:
    row_map = _mapping(row)
    symbol = _to_text(row_map.get("symbol")).upper()
    if not symbol:
        return None
    closeout_state = _to_text(row_map.get("closeout_state")).upper()
    activation_apply_state = _to_text(row_map.get("activation_apply_state")).upper()
    first_window_status = _to_text(row_map.get("first_window_status")).upper()
    recommended_next_action = _to_text(row_map.get("recommended_next_action"))

    review_type = ""
    governance_action = ""
    scope_suffix = ""
    if closeout_state == "ROLLBACK_REQUIRED":
        review_type = "CANARY_ROLLBACK_REVIEW"
        governance_action = "rollback_review"
        scope_suffix = "rollback"
    elif (
        closeout_state == "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"
        and activation_apply_state == "ACTIVE_ACTION_ONLY_CANARY"
    ):
        review_type = "CANARY_CLOSEOUT_REVIEW"
        governance_action = "closeout_review"
        scope_suffix = "closeout"
    elif activation_apply_state in {"HOLD_CANARY_ACTIVATION_APPLY", "HELD_ACTION_ONLY_CANARY"}:
        review_type = "CANARY_ACTIVATION_REVIEW"
        governance_action = "activation_review"
        scope_suffix = "activation"

    if not review_type:
        return None

    return {
        "review_type": review_type,
        "governance_action": governance_action,
        "scope_key": f"{symbol}::action_only_canary::{scope_suffix}",
        "symbol": symbol,
        "activation_apply_state": activation_apply_state,
        "closeout_state": closeout_state,
        "first_window_status": first_window_status,
        "live_observation_ready": bool(row_map.get("live_observation_ready")),
        "observed_window_row_count": _to_int(row_map.get("observed_window_row_count")),
        "active_trigger_count": _to_int(row_map.get("active_trigger_count")),
        "recommended_next_action": recommended_next_action,
    }


def _candidate_from_pa9_runtime_row(
    row: Mapping[str, Any],
    *,
    review_state: str,
    apply_state: str,
) -> dict[str, Any] | None:
    row_map = _mapping(row)
    symbol = _to_text(row_map.get("symbol")).upper()
    if not symbol:
        return None
    if _to_text(review_state).upper() != "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW":
        return None
    if not _to_bool(row_map.get("handoff_review_candidate")):
        return None
    return {
        "review_type": "PA9_ACTION_BASELINE_HANDOFF_REVIEW",
        "governance_action": "pa9_action_baseline_handoff_review",
        "scope_key": f"{symbol}::pa9_action_baseline_handoff::review",
        "symbol": symbol,
        "handoff_state": _to_text(row_map.get("activation_apply_state")),
        "closeout_state": _to_text(row_map.get("closeout_state")),
        "handoff_review_candidate": True,
        "handoff_apply_candidate": _to_bool(row_map.get("handoff_apply_candidate")),
        "runtime_review_state": _to_text(review_state),
        "runtime_apply_state": _to_text(apply_state),
        "recommended_next_action": _to_text(
            row_map.get("handoff_apply_recommended_next_action")
            or row_map.get("closeout_recommended_next_action")
            or "review_prepared_pa9_action_baseline_handoff_packet"
        ),
    }


def run_checkpoint_improvement_watch_governance_cycle(
    *,
    system_state_manager: SystemStateManager | None = None,
    event_bus: EventBus | None = None,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    row_delta: int = 0,
    approval_backlog_count: int = 0,
    apply_backlog_count: int = 0,
    cycle_running: bool = False,
    now_ts: object | None = None,
    force_run: bool = False,
    governance_board_payload: Mapping[str, Any] | None = None,
    governance_board_loader: Callable[[], Mapping[str, Any]] = _default_governance_board_loader,
) -> dict[str, Any]:
    state_manager = system_state_manager or SystemStateManager()
    bus = event_bus or EventBus()
    report_file = Path(report_path or default_checkpoint_improvement_watch_report_path())
    markdown_file = Path(markdown_path or default_checkpoint_improvement_watch_markdown_path())
    run_started_at = _to_text(now_ts, now_kst_dt().isoformat())
    trace_id = f"watch-governance-{uuid4().hex[:12]}"

    state_before = state_manager.get_state()
    current_phase = _to_text(state_before.get("phase"), "STARTING").upper()
    preloaded_board_payload: dict[str, Any] = {}
    pa8_closeout_runtime: dict[str, Any] = {}
    pa9_runtime_refresh: dict[str, Any] = {}
    try:
        preloaded_board_payload = (
            _mapping(governance_board_payload)
            if governance_board_payload is not None
            else _mapping(governance_board_loader())
        )
        for row in list(preloaded_board_payload.get("rows", []) or []):
            if not isinstance(row, Mapping):
                continue
            row_map = _mapping(row)
            symbol = _to_text(row_map.get("symbol")).upper()
            if not symbol:
                continue
            state_manager.set_pa8_symbol_state(
                symbol,
                canary_active=_to_text(row_map.get("activation_apply_state")).upper() == "ACTIVE_ACTION_ONLY_CANARY",
                live_window_ready=bool(row_map.get("live_observation_ready")),
        )
        state_before = state_manager.get_state()
        pa8_closeout_runtime = refresh_checkpoint_improvement_pa8_closeout_runtime(
            board_payload=preloaded_board_payload,
        )
        pa9_runtime_refresh = refresh_checkpoint_improvement_pa9_handoff_runtime()
    except Exception as exc:
        error_reason = f"governance_cycle_error::{exc.__class__.__name__}"
        error_state = state_manager.transition(
            "DEGRADED",
            reason=error_reason,
            occurred_at=run_started_at,
        )
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "governance",
                    "error_reason": error_reason,
                    "board_path": str(default_checkpoint_pa8_canary_refresh_board_json_path()),
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
        payload = {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_WATCH_CONTRACT_VERSION,
                "generated_at": run_started_at,
                "cycle_name": "governance",
                "trigger_state": "WATCH_ERROR",
                "recommended_next_action": "inspect_governance_cycle_error_and_retry",
                "row_count": 0,
                "row_delta": max(0, int(row_delta)),
                "event_count": bus.pending_count(),
                "report_path": str(report_file),
                "system_state_path": str(state_manager.state_path),
            },
            "cycle_decision": {},
            "governance_summary": {"error_reason": error_reason},
            "governance_candidates": [],
            "state_before": {
                "phase": current_phase,
                "governance_last_run": _to_text(state_before.get("governance_last_run")),
                "pa8_symbols": _mapping(state_before.get("pa8_symbols")),
            },
            "state_after": {
                "phase": _to_text(error_state.get("phase"), current_phase),
                "governance_last_run": _to_text(error_state.get("governance_last_run")),
                "pa8_symbols": _mapping(error_state.get("pa8_symbols")),
            },
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    cycle_decision = evaluate_cycle_decision(
        "governance",
        system_state=state_before,
        row_delta=row_delta,
        now_ts=run_started_at,
        cycle_running=cycle_running,
        approval_backlog_count=approval_backlog_count,
        apply_backlog_count=apply_backlog_count,
        force_run=force_run,
    )

    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_WATCH_CONTRACT_VERSION,
            "generated_at": run_started_at,
            "cycle_name": "governance",
            "trigger_state": "",
            "recommended_next_action": "",
            "row_count": 0,
            "row_delta": max(0, int(row_delta)),
            "event_count": 0,
            "report_path": str(report_file),
            "system_state_path": str(state_manager.state_path),
        },
        "cycle_decision": cycle_decision,
        "governance_summary": {},
        "governance_candidates": [],
        "state_before": {
            "phase": current_phase,
            "governance_last_run": _to_text(state_before.get("governance_last_run")),
            "pa8_symbols": _mapping(state_before.get("pa8_symbols")),
        },
        "state_after": {},
    }

    if not cycle_decision.get("due"):
        payload["summary"]["trigger_state"] = "SKIP_WATCH_DECISION"
        payload["summary"]["recommended_next_action"] = "wait_for_active_canary_rows_or_governance_interval"
        payload["state_after"] = payload["state_before"]
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    board_payload = preloaded_board_payload
    rows = list(board_payload.get("rows", []) or [])
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_map = _mapping(row)
        symbol = _to_text(row_map.get("symbol")).upper()
        if symbol:
            state_manager.set_pa8_symbol_state(
                symbol,
                canary_active=_to_text(row_map.get("activation_apply_state")).upper() == "ACTIVE_ACTION_ONLY_CANARY",
                live_window_ready=bool(row_map.get("live_observation_ready")),
            )
        candidate = _candidate_from_governance_row(row_map)
        if candidate is not None:
            candidates.append(candidate)

    pa9_review_state = _to_text(_mapping(pa9_runtime_refresh.get("summary")).get("review_state"))
    pa9_apply_state = _to_text(_mapping(pa9_runtime_refresh.get("summary")).get("apply_state"))
    for row in list(_mapping(pa9_runtime_refresh.get("review_packet")).get("rows", []) or []):
        if not isinstance(row, Mapping):
            continue
        candidate = _candidate_from_pa9_runtime_row(
            row,
            review_state=pa9_review_state,
            apply_state=pa9_apply_state,
        )
        if candidate is not None:
            candidates.append(candidate)

    state_manager.mark_cycle_run("governance", run_at=run_started_at)
    state_after = _recover_running_after_success(
        state_manager=state_manager,
        event_bus=bus,
        trace_id=trace_id,
        occurred_at=run_started_at,
        current_phase=current_phase,
        recovery_reason="governance_cycle_refresh_recovered_watch_phase",
    )

    for candidate in candidates:
        bus.publish(
            GovernanceActionNeeded(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload=candidate,
            )
        )

    summary_map = _mapping(board_payload.get("summary"))
    governance_summary = {
        "board_contract_version": _to_text(summary_map.get("contract_version")),
        "active_symbol_count": _to_int(summary_map.get("active_symbol_count")),
        "live_observation_ready_count": _to_int(summary_map.get("live_observation_ready_count")),
        "approval_backlog_count": max(0, int(approval_backlog_count)),
        "apply_backlog_count": max(0, int(apply_backlog_count)),
        "candidate_count": len(candidates),
        "pa9_handoff_state": _to_text(
            _mapping(pa9_runtime_refresh.get("summary")).get("handoff_state")
        ),
        "pa9_review_state": _to_text(
            _mapping(pa9_runtime_refresh.get("summary")).get("review_state")
        ),
        "pa9_apply_state": _to_text(
            _mapping(pa9_runtime_refresh.get("summary")).get("apply_state")
        ),
        "recommended_next_action": (
            "dispatch_governance_review_candidates"
            if candidates
            else _to_text(
                _mapping(pa8_closeout_runtime.get("summary")).get("recommended_next_action")
                or _mapping(pa9_runtime_refresh.get("summary")).get("recommended_next_action"),
                "keep_canaries_running_until_review_candidates_appear",
            )
        ),
        "pa8_closeout_review_state": _to_text(
            _mapping(pa8_closeout_runtime.get("summary")).get("review_state")
        ),
        "pa8_closeout_apply_state": _to_text(
            _mapping(pa8_closeout_runtime.get("summary")).get("apply_state")
        ),
    }
    payload["governance_summary"] = governance_summary
    payload["governance_candidates"] = candidates
    payload["summary"]["trigger_state"] = (
        "GOVERNANCE_CANDIDATES_EMITTED" if candidates else "GOVERNANCE_NO_ACTION_NEEDED"
    )
    payload["summary"]["recommended_next_action"] = _to_text(governance_summary.get("recommended_next_action"))
    payload["summary"]["row_count"] = _to_int(summary_map.get("active_symbol_count"))
    payload["summary"]["event_count"] = bus.pending_count()
    payload["state_after"] = {
        "phase": _to_text(state_after.get("phase"), current_phase),
        "governance_last_run": _to_text(state_after.get("governance_last_run")),
        "pa8_symbols": _mapping(state_after.get("pa8_symbols")),
    }
    _write_json(report_file, payload)
    _write_text(markdown_file, _render_watch_markdown(payload))
    return payload


def run_checkpoint_improvement_watch_heavy_cycle(
    *,
    system_state_manager: SystemStateManager | None = None,
    event_bus: EventBus | None = None,
    checkpoint_rows_path: str | Path | None = None,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    recent_limit: int = DEFAULT_CHECKPOINT_IMPROVEMENT_HEAVY_RECENT_LIMIT,
    cycle_running: bool = False,
    now_ts: object | None = None,
    force_run: bool = False,
    heavy_refresh_function: Callable[..., Mapping[str, Any]] = maybe_refresh_checkpoint_analysis_chain,
) -> dict[str, Any]:
    state_manager = system_state_manager or SystemStateManager()
    bus = event_bus or EventBus()
    rows_path = Path(checkpoint_rows_path or default_checkpoint_rows_path())
    report_file = Path(report_path or default_checkpoint_improvement_watch_report_path())
    markdown_file = Path(markdown_path or default_checkpoint_improvement_watch_markdown_path())
    run_started_at = _to_text(now_ts, now_kst_dt().isoformat())
    trace_id = f"watch-heavy-{uuid4().hex[:12]}"

    state_before = state_manager.get_state()
    current_phase = _to_text(state_before.get("phase"), "STARTING").upper()
    row_count = _count_checkpoint_rows(rows_path)
    last_processed_row_count = _to_int(state_before.get("row_count_since_boot"))
    row_delta = max(0, row_count - last_processed_row_count)
    hot_path_healthy = current_phase not in {"EMERGENCY", "SHUTDOWN"}
    cycle_decision = evaluate_cycle_decision(
        "heavy",
        system_state=state_before,
        row_delta=row_delta,
        now_ts=run_started_at,
        cycle_running=cycle_running,
        hot_path_healthy=hot_path_healthy,
        recent_sample_count=row_count,
        force_run=force_run,
    )

    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_WATCH_CONTRACT_VERSION,
            "generated_at": run_started_at,
            "cycle_name": "heavy",
            "trigger_state": "",
            "recommended_next_action": "",
            "row_count": row_count,
            "row_delta": row_delta,
            "event_count": 0,
            "report_path": str(report_file),
            "system_state_path": str(state_manager.state_path),
        },
        "cycle_decision": cycle_decision,
        "refresh_summary": {},
        "heavy_summary": {},
        "state_before": {
            "phase": current_phase,
            "row_count_since_boot": last_processed_row_count,
            "heavy_last_run": _to_text(state_before.get("heavy_last_run")),
            "last_row_ts": _to_text(state_before.get("last_row_ts")),
        },
        "state_after": {},
    }

    if not cycle_decision.get("due"):
        payload["summary"]["trigger_state"] = "SKIP_WATCH_DECISION"
        payload["summary"]["recommended_next_action"] = _skip_recommended_next_action(
            _to_text(cycle_decision.get("skip_reason"))
        )
        payload["state_after"] = payload["state_before"]
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    try:
        refresh_payload = dict(
            heavy_refresh_function(
                checkpoint_rows_path=rows_path,
                runtime_updated_at=run_started_at,
                force=True,
                recent_limit=recent_limit,
                include_deep_scene_review=True,
            )
        )
    except Exception as exc:
        error_reason = f"heavy_cycle_error::{exc.__class__.__name__}"
        error_state = state_manager.transition(
            "DEGRADED",
            reason=error_reason,
            occurred_at=run_started_at,
        )
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "heavy",
                    "error_reason": error_reason,
                    "rows_path": str(rows_path),
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
        payload["summary"]["recommended_next_action"] = "inspect_watch_error_and_retry_heavy_cycle"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["refresh_summary"] = {
            "trigger_state": "WATCH_ERROR",
            "error_reason": error_reason,
        }
        payload["state_after"] = {
            "phase": _to_text(error_state.get("phase"), current_phase),
            "row_count_since_boot": _to_int(error_state.get("row_count_since_boot")),
            "heavy_last_run": _to_text(error_state.get("heavy_last_run")),
            "last_row_ts": _to_text(error_state.get("last_row_ts")),
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    payload["refresh_summary"] = _mapping(refresh_payload.get("summary"))
    refresh_trigger_state = _to_text(payload["refresh_summary"].get("trigger_state"))
    if refresh_trigger_state == "REFRESHED":
        state_manager.mark_cycle_run("heavy", run_at=run_started_at)
        state_after = _recover_running_after_success(
            state_manager=state_manager,
            event_bus=bus,
            trace_id=trace_id,
            occurred_at=run_started_at,
            current_phase=current_phase,
            recovery_reason="heavy_cycle_refresh_recovered_watch_phase",
        )
        heavy_summary = _extract_heavy_summary(refresh_payload)
        payload["summary"]["trigger_state"] = "HEAVY_CYCLE_REFRESHED"
        payload["summary"]["recommended_next_action"] = _to_text(
            heavy_summary.get("recommended_next_action"),
            "continue_governance_and_master_board_refresh_after_heavy_cycle",
        )
        payload["summary"]["event_count"] = bus.pending_count()
        payload["heavy_summary"] = heavy_summary
        payload["state_after"] = {
            "phase": _to_text(state_after.get("phase"), current_phase),
            "row_count_since_boot": _to_int(state_after.get("row_count_since_boot")),
            "heavy_last_run": _to_text(state_after.get("heavy_last_run")),
            "last_row_ts": _to_text(state_after.get("last_row_ts")),
        }
    else:
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "heavy",
                    "error_reason": f"refresh_not_completed::{refresh_trigger_state or 'UNKNOWN'}",
                    "rows_path": str(rows_path),
                },
            )
        )
        payload["summary"]["trigger_state"] = "HEAVY_CYCLE_REFRESH_NOT_COMPLETED"
        payload["summary"]["recommended_next_action"] = "inspect_heavy_refresh_chain_state_before_next_tick"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["state_after"] = payload["state_before"]

    _write_json(report_file, payload)
    _write_text(markdown_file, _render_watch_markdown(payload))
    return payload


def run_checkpoint_improvement_watch_light_cycle(
    *,
    system_state_manager: SystemStateManager | None = None,
    event_bus: EventBus | None = None,
    checkpoint_rows_path: str | Path | None = None,
    report_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
    recent_limit: int = DEFAULT_CHECKPOINT_IMPROVEMENT_LIGHT_RECENT_LIMIT,
    cycle_running: bool = False,
    lock_held: bool = False,
    now_ts: object | None = None,
    force_run: bool = False,
    refresh_function: Callable[..., Mapping[str, Any]] = maybe_refresh_checkpoint_analysis_chain,
) -> dict[str, Any]:
    state_manager = system_state_manager or SystemStateManager()
    bus = event_bus or EventBus()
    rows_path = Path(checkpoint_rows_path or default_checkpoint_rows_path())
    report_file = Path(report_path or default_checkpoint_improvement_watch_report_path())
    markdown_file = Path(markdown_path or default_checkpoint_improvement_watch_markdown_path())
    run_started_at = _to_text(now_ts, now_kst_dt().isoformat())
    trace_id = f"watch-light-{uuid4().hex[:12]}"

    state_before = state_manager.get_state()
    current_phase = _to_text(state_before.get("phase"), "STARTING").upper()
    row_count = _count_checkpoint_rows(rows_path)
    last_processed_row_count = _to_int(state_before.get("row_count_since_boot"))
    row_delta = max(0, row_count - last_processed_row_count)
    latest_row_ts = _latest_checkpoint_row_ts(rows_path)

    if not rows_path.exists():
        cycle_decision = _build_missing_rows_decision(row_delta=row_delta)
    else:
        cycle_decision = evaluate_cycle_decision(
            "light",
            system_state=state_before,
            row_delta=row_delta,
            now_ts=run_started_at,
            cycle_running=cycle_running,
            lock_held=lock_held,
            force_run=force_run,
        )

    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_WATCH_CONTRACT_VERSION,
            "generated_at": run_started_at,
            "cycle_name": "light",
            "trigger_state": "",
            "recommended_next_action": "",
            "row_count": row_count,
            "row_delta": row_delta,
            "event_count": 0,
            "report_path": str(report_file),
            "system_state_path": str(state_manager.state_path),
        },
        "cycle_decision": cycle_decision,
        "refresh_summary": {},
        "state_before": {
            "phase": current_phase,
            "row_count_since_boot": last_processed_row_count,
            "light_last_run": _to_text(state_before.get("light_last_run")),
            "last_row_ts": _to_text(state_before.get("last_row_ts")),
        },
        "state_after": {},
    }

    if not cycle_decision.get("due"):
        payload["summary"]["trigger_state"] = "SKIP_WATCH_DECISION"
        payload["summary"]["recommended_next_action"] = _skip_recommended_next_action(
            _to_text(cycle_decision.get("skip_reason"))
        )
        payload["state_after"] = payload["state_before"]
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    try:
        refresh_payload = dict(
            refresh_function(
                checkpoint_rows_path=rows_path,
                runtime_updated_at=run_started_at,
                force=True,
                recent_limit=recent_limit,
                include_deep_scene_review=False,
            )
        )
    except Exception as exc:
        error_reason = f"light_cycle_error::{exc.__class__.__name__}"
        error_state = state_manager.transition(
            "DEGRADED",
            reason=error_reason,
            occurred_at=run_started_at,
        )
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "light",
                    "error_reason": error_reason,
                    "rows_path": str(rows_path),
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
        payload["summary"]["recommended_next_action"] = "inspect_watch_error_and_retry_light_cycle"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["refresh_summary"] = {
            "trigger_state": "WATCH_ERROR",
            "error_reason": error_reason,
        }
        payload["state_after"] = {
            "phase": _to_text(error_state.get("phase"), current_phase),
            "row_count_since_boot": _to_int(error_state.get("row_count_since_boot")),
            "light_last_run": _to_text(error_state.get("light_last_run")),
            "last_row_ts": _to_text(error_state.get("last_row_ts")),
        }
        _write_json(report_file, payload)
        _write_text(markdown_file, _render_watch_markdown(payload))
        return payload

    refresh_summary = _mapping(refresh_payload.get("summary"))
    payload["refresh_summary"] = refresh_summary
    refresh_trigger_state = _to_text(refresh_summary.get("trigger_state"))

    if refresh_trigger_state == "REFRESHED":
        state_manager.record_row_observation(
            last_row_ts=latest_row_ts or run_started_at,
            row_count_increment=row_delta,
        )
        state_manager.mark_cycle_run("light", run_at=run_started_at)
        state_after = state_manager.get_state()
        next_phase = _to_text(state_after.get("phase"), current_phase)
        if current_phase == "STARTING":
            state_after = state_manager.transition(
                "RUNNING",
                reason="light_cycle_first_refresh_completed",
                occurred_at=run_started_at,
            )
            next_phase = _to_text(state_after.get("phase"), current_phase)
            _publish_phase_change(
                event_bus=bus,
                trace_id=trace_id,
                occurred_at=run_started_at,
                previous_phase=current_phase,
                next_phase=next_phase,
                reason="light_cycle_first_refresh_completed",
            )
        elif current_phase == "DEGRADED":
            state_after = _recover_running_after_success(
                state_manager=state_manager,
                event_bus=bus,
                trace_id=trace_id,
                occurred_at=run_started_at,
                current_phase=current_phase,
                recovery_reason="light_cycle_refresh_recovered_watch_phase",
            )
            next_phase = _to_text(state_after.get("phase"), current_phase)

        bus.publish(
            LightRefreshCompleted(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "light",
                    "row_delta": row_delta,
                    "row_count": row_count,
                    "recent_limit": int(recent_limit),
                    "rows_path": str(rows_path),
                    "analysis_refresh_report_path": str(default_checkpoint_analysis_refresh_report_path()),
                },
            )
        )
        payload["summary"]["trigger_state"] = "LIGHT_CYCLE_REFRESHED"
        payload["summary"]["recommended_next_action"] = "continue_with_governance_cycle_when_ready"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["state_after"] = {
            "phase": next_phase,
            "row_count_since_boot": _to_int(state_after.get("row_count_since_boot")),
            "light_last_run": _to_text(state_after.get("light_last_run")),
            "last_row_ts": _to_text(state_after.get("last_row_ts")),
        }
    else:
        bus.publish(
            WatchError(
                trace_id=trace_id,
                occurred_at=run_started_at,
                payload={
                    "cycle_name": "light",
                    "error_reason": f"refresh_not_completed::{refresh_trigger_state or 'UNKNOWN'}",
                    "rows_path": str(rows_path),
                },
            )
        )
        payload["summary"]["trigger_state"] = "LIGHT_CYCLE_REFRESH_NOT_COMPLETED"
        payload["summary"]["recommended_next_action"] = "inspect_refresh_chain_state_before_next_light_tick"
        payload["summary"]["event_count"] = bus.pending_count()
        payload["state_after"] = payload["state_before"]

    _write_json(report_file, payload)
    _write_text(markdown_file, _render_watch_markdown(payload))
    return payload
