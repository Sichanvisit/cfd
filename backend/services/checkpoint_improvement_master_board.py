from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_watch import (
    default_checkpoint_improvement_watch_report_path,
)
from backend.services.improvement_board_field_policy import (
    IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION,
    CONFIDENCE_LEVEL_LIMITED,
    derive_pa8_closeout_readiness_status,
    derive_pa9_handoff_readiness_status,
    derive_reverse_readiness_status,
)
from backend.services.checkpoint_improvement_pa9_handoff_apply_packet import (
    default_checkpoint_improvement_pa9_handoff_apply_packet_json_path,
)
from backend.services.checkpoint_improvement_pa8_closeout_runtime import (
    default_checkpoint_improvement_pa8_closeout_runtime_json_path,
    refresh_checkpoint_improvement_pa8_closeout_runtime,
)
from backend.services.checkpoint_improvement_pa9_handoff_packet import (
    default_checkpoint_improvement_pa9_handoff_packet_json_path,
)
from backend.services.checkpoint_improvement_pa9_handoff_review_packet import (
    default_checkpoint_improvement_pa9_handoff_review_packet_json_path,
)
from backend.services.improvement_readiness_surface import (
    build_improvement_readiness_surface,
    default_improvement_readiness_surface_json_path,
    default_improvement_readiness_surface_markdown_path,
)
from backend.services.improvement_status_policy import (
    APPROVAL_ACTIONABLE_STATUSES,
    APPROVAL_CONFLICT_TRACKING_STATUSES,
)
from backend.services.path_checkpoint_pa78_review_packet import (
    default_checkpoint_pa78_review_packet_path,
)
from backend.services.path_checkpoint_pa7_review_processor import (
    default_checkpoint_pa7_review_processor_path,
)
from backend.services.path_checkpoint_pa8_canary_refresh import (
    default_checkpoint_pa8_canary_refresh_board_json_path,
)
from backend.services.system_state_manager import SystemStateManager
from backend.services.telegram_state_store import TelegramStateStore


CHECKPOINT_IMPROVEMENT_MASTER_BOARD_CONTRACT_VERSION = (
    "checkpoint_improvement_master_board_v0"
)
_ACTIONABLE_APPROVAL_STATUSES = set(APPROVAL_ACTIONABLE_STATUSES)
_SAME_SCOPE_CONFLICT_STATUSES = set(APPROVAL_CONFLICT_TRACKING_STATUSES)


def default_checkpoint_improvement_master_board_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_master_board_latest.json"
    )


def default_checkpoint_improvement_master_board_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_master_board_latest.md"
    )


def default_runtime_status_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "runtime_status.json"


def _resolve_readiness_surface_output_paths(
    *,
    output_json_path: str | Path | None,
) -> tuple[Path, Path]:
    if output_json_path:
        base_dir = Path(output_json_path).resolve().parent
        return (
            base_dir / "improvement_readiness_surface_latest.json",
            base_dir / "improvement_readiness_surface_latest.md",
        )
    return (
        default_improvement_readiness_surface_json_path(),
        default_improvement_readiness_surface_markdown_path(),
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


def _age_seconds(now_dt: datetime, created_at: object) -> int | None:
    created_dt = _parse_iso(created_at)
    if created_dt is None:
        return None
    age = (now_dt - created_dt).total_seconds()
    return max(0, int(age))


def _group_status_counts(groups: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in groups:
        status = _to_text(group.get("status")).lower()
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _same_scope_conflict_count(groups: list[Mapping[str, Any]]) -> int:
    scope_counts: dict[str, int] = {}
    for group in groups:
        status = _to_text(group.get("status")).lower()
        scope_key = _to_text(group.get("scope_key"))
        if status not in _SAME_SCOPE_CONFLICT_STATUSES or not scope_key:
            continue
        scope_counts[scope_key] = scope_counts.get(scope_key, 0) + 1
    return sum(max(0, count - 1) for count in scope_counts.values())


def _late_callback_invalidation_count(
    *,
    groups: list[Mapping[str, Any]],
    actions: list[Mapping[str, Any]],
) -> int:
    approval_by_group = {
        _to_int(group.get("group_id")): _to_text(group.get("approval_id"))
        for group in groups
        if _to_int(group.get("group_id")) > 0
    }
    count = 0
    for action in actions:
        action_type = _to_text(action.get("action")).lower()
        callback_query_id = _to_text(action.get("callback_query_id"))
        if action_type not in {"approve", "hold", "reject"} or not callback_query_id:
            continue
        group_id = _to_int(action.get("group_id"))
        action_approval_id = _to_text(action.get("approval_id"))
        current_approval_id = approval_by_group.get(group_id, "")
        if action_approval_id and current_approval_id and action_approval_id != current_approval_id:
            count += 1
    return count


def _compute_degraded_components(
    *,
    phase: str,
    telegram_healthy: bool,
    watch_cycle_name: str,
    watch_trigger_state: str,
) -> list[str]:
    components: list[str] = []
    if phase == "DEGRADED":
        components.append("system_phase:degraded")
    elif phase == "EMERGENCY":
        components.append("system_phase:emergency")
    if not telegram_healthy:
        components.append("telegram")
    if watch_trigger_state == "WATCH_ERROR":
        components.append(f"watch:{watch_cycle_name or 'unknown'}")
    return components


def _extract_runtime_state(runtime_payload: Mapping[str, Any]) -> dict[str, Any]:
    runtime_recycle = _mapping(runtime_payload.get("runtime_recycle"))
    return {
        "updated_at": _to_text(runtime_payload.get("updated_at")),
        "open_positions_count": _to_int(runtime_recycle.get("last_open_positions_count")),
        "owned_open_positions_count": _to_int(
            runtime_recycle.get("last_owned_open_positions_count")
        ),
        "flat_since": _to_text(runtime_recycle.get("flat_since")),
    }


def _blocking_and_next_action(
    *,
    phase: str,
    degraded_components: list[str],
    apply_backlog_count: int,
    approval_backlog_count: int,
    pa7_unresolved_review_group_count: int,
    pa7_narrow_review_status: str,
    pa7_narrow_review_group_count: int,
    active_symbol_count: int,
    live_observation_ready_count: int,
    pa9_handoff_state: str,
    pa9_review_state: str,
    runtime_open_positions_count: int,
    watch_next_action: str,
    pa78_next_action: str,
    pa8_next_action: str,
) -> tuple[str, str]:
    if phase == "EMERGENCY":
        return (
            "system_phase_emergency",
            "inspect_emergency_state_and_restore_hot_path_before_any_new_governance",
        )
    if phase == "DEGRADED":
        return (
            "system_phase_degraded",
            "inspect_degraded_components_and_restore_dependencies",
        )
    if degraded_components:
        return (
            "dependency_degraded",
            "inspect_degraded_components_and_restore_dependencies",
        )
    if apply_backlog_count > 0:
        return (
            "approved_apply_backlog",
            "drain_approved_apply_backlog_before_new_governance_reviews",
        )
    if approval_backlog_count > 0:
        return (
            "approval_backlog_pending",
            "process_pending_or_held_governance_reviews_in_telegram",
        )
    if pa7_narrow_review_group_count > 0 or _to_text(pa7_narrow_review_status).upper() == "REVIEW_NEEDED":
        return (
            "pa7_review_backlog",
            _to_text(pa78_next_action, "work_through_pa7_review_groups_before_pa8"),
        )
    if pa7_unresolved_review_group_count > 0 and not _to_text(pa7_narrow_review_status):
        return (
            "pa7_review_backlog",
            _to_text(pa78_next_action, "work_through_pa7_review_groups_before_pa8"),
        )
    if _to_text(pa9_review_state).upper() == "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW":
        return (
            "pa9_handoff_review_ready",
            "review_prepared_pa9_action_baseline_handoff_packet",
        )
    if _to_text(pa9_handoff_state).upper() == "WAIT_FOR_CLOSEOUT_APPROVAL_APPLICATION":
        return (
            "pa8_closeout_apply_pending_before_pa9",
            "approve_and_apply_pa8_closeout_review_before_pa9_handoff",
        )
    if active_symbol_count > 0 and live_observation_ready_count < active_symbol_count:
        if runtime_open_positions_count <= 0:
            return (
                "pa8_live_window_pending",
                "wait_for_new_pa8_candidate_rows_or_market_reopen",
            )
        return (
            "pa8_live_window_pending",
            _to_text(
                pa8_next_action,
                "wait_for_live_first_window_rows_and_refresh_canary_board",
            ),
        )
    return (
        "none",
        _to_text(
            watch_next_action or pa78_next_action or pa8_next_action,
            "continue_checkpoint_improvement_watch_cycles",
        ),
    )


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    readiness_state = _mapping(payload.get("readiness_state"))
    pa8_surface = _mapping(readiness_state.get("pa8_closeout_surface"))
    pa8_focus_surface = _mapping(readiness_state.get("pa8_closeout_focus_surface"))
    first_symbol_surface = _mapping(readiness_state.get("first_symbol_closeout_handoff_surface"))
    pa9_surface = _mapping(readiness_state.get("pa9_handoff_surface"))
    pa7_narrow_review_surface = _mapping(readiness_state.get("pa7_narrow_review_surface"))
    reverse_surface = _mapping(readiness_state.get("reverse_surface"))
    historical_cost_surface = _mapping(readiness_state.get("historical_cost_surface"))
    system_state = _mapping(payload.get("system_state"))
    watch_state = _mapping(payload.get("watch_state"))
    runtime_state = _mapping(payload.get("runtime_state"))
    pa_state = _mapping(payload.get("pa_state"))
    approval_state = _mapping(payload.get("approval_state"))
    health_state = _mapping(payload.get("health_state"))
    orchestrator_contract = _mapping(payload.get("orchestrator_contract"))

    lines: list[str] = []
    lines.append("# Checkpoint Improvement Master Board")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "phase",
        "blocking_reason",
        "next_required_action",
        "field_policy_version",
        "active_pa8_symbol_count",
        "live_window_ready_count",
        "runtime_open_positions_count",
        "runtime_flat_since",
        "pending_approval_count",
        "held_approval_count",
        "approved_apply_backlog_count",
        "oldest_pending_approval_age_sec",
        "last_successful_apply_ts",
        "reconcile_backlog_count",
        "same_scope_conflict_count",
        "pa8_closeout_readiness_status",
        "pa8_closeout_focus_status",
        "pa8_focus_symbol_count",
        "pa8_primary_focus_symbol",
        "first_symbol_closeout_handoff_status",
        "first_symbol_closeout_handoff_symbol",
        "pa9_handoff_readiness_status",
        "pa7_narrow_review_status",
        "pa7_narrow_review_group_count",
        "reverse_readiness_status",
        "historical_cost_confidence_level",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Readiness")
    lines.append("")
    for key in (
        "pa8_closeout_readiness_status",
        "pa8_closeout_blocking_reason",
        "pa8_closeout_next_required_action",
        "pa8_closeout_focus_status",
        "pa8_closeout_focus_reason",
        "pa8_closeout_focus_next_required_action",
        "pa8_primary_focus_symbol",
        "pa8_focus_symbol_count",
        "pa8_focus_watchlist_symbol_count",
        "first_symbol_closeout_handoff_status",
        "first_symbol_closeout_handoff_symbol",
        "first_symbol_closeout_handoff_stage",
        "first_symbol_closeout_handoff_reason",
        "first_symbol_closeout_handoff_next_required_action",
        "pa9_handoff_readiness_status",
        "pa9_handoff_blocking_reason",
        "pa9_handoff_next_required_action",
        "pa7_narrow_review_status",
        "pa7_narrow_review_group_count",
        "pa7_narrow_review_primary_group_key",
        "pa7_narrow_review_next_required_action",
        "reverse_readiness_status",
        "reverse_blocking_reason",
        "reverse_next_required_action",
        "historical_cost_confidence_level",
        "historical_cost_blocking_reason",
        "historical_cost_note",
    ):
        lines.append(f"- {key}: `{readiness_state.get(key)}`")
    lines.append("")
    lines.append("## PA8 Readiness Surface")
    lines.append("")
    for key in (
        "ready_symbol_count",
        "pending_symbol_count",
        "blocked_symbol_count",
        "active_symbol_count",
        "live_window_ready_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa8_surface.get(key)}`")
    for row in list(pa8_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` rows=`{row_map.get('observed_window_row_count')}` triggers=`{row_map.get('active_trigger_count')}`"
        )
    lines.append("")
    lines.append("## PA8 Closeout Focus Surface")
    lines.append("")
    for key in (
        "focus_status",
        "blocking_reason",
        "focus_symbol_count",
        "concentrated_symbol_count",
        "watchlist_symbol_count",
        "primary_focus_symbol",
        "primary_focus_reason_ko",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa8_focus_surface.get(key)}`")
    for row in list(pa8_focus_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` focus=`{row_map.get('focus_status')}` progress=`{row_map.get('window_progress_ratio')}` reason=`{row_map.get('focus_reason_ko')}`"
        )
    lines.append("")
    lines.append("## First Symbol Closeout/Handoff Surface")
    lines.append("")
    for key in (
        "observation_status",
        "observation_stage",
        "primary_symbol",
        "reason_ko",
        "recommended_next_action",
        "focus_progress_ratio",
        "observed_window_row_count",
        "sample_floor",
        "active_trigger_count",
        "handoff_review_candidate",
        "handoff_apply_candidate",
    ):
        lines.append(f"- {key}: `{first_symbol_surface.get(key)}`")
    lines.append("")
    lines.append("## PA9 Readiness Surface")
    lines.append("")
    for key in (
        "handoff_state",
        "review_state",
        "apply_state",
        "ready_for_review_symbol_count",
        "ready_for_apply_symbol_count",
        "pending_symbol_count",
        "recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa9_surface.get(key)}`")
    for row in list(pa9_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` review=`{row_map.get('handoff_review_candidate')}` apply=`{row_map.get('handoff_apply_candidate')}`"
        )
    lines.append("")
    lines.append("## PA7 Narrow Review Lane")
    lines.append("")
    for key in (
        "status",
        "reason_ko",
        "recommended_next_action",
        "group_count",
        "mixed_wait_boundary_group_count",
        "mixed_review_group_count",
        "primary_group_key",
        "primary_symbol",
        "primary_review_disposition",
    ):
        lines.append(f"- {key}: `{pa7_narrow_review_surface.get(key)}`")
    for row in list(pa7_narrow_review_surface.get("rows", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` lane=`{row_map.get('lane_status')}` disposition=`{row_map.get('review_disposition')}` rows=`{row_map.get('row_count')}` key=`{row_map.get('group_key')}`"
        )
    lines.append("")
    lines.append("## Reverse Readiness Surface")
    lines.append("")
    for key in (
        "runtime_open_positions_count",
        "ready_symbol_count",
        "pending_symbol_count",
        "blocked_symbol_count",
        "blocking_reason",
    ):
        lines.append(f"- {key}: `{reverse_surface.get(key)}`")
    for row in list(reverse_surface.get("symbols", []) or []):
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('symbol')}` status=`{row_map.get('readiness_status')}` pending_action=`{row_map.get('pending_action')}` block=`{row_map.get('order_block_reason')}`"
        )
    lines.append("")
    lines.append("## Historical Cost Surface")
    lines.append("")
    for key in (
        "confidence_level",
        "blocking_reason",
        "recent_trade_count",
        "recent_safe_trade_count",
        "recent_safe_ratio",
        "note",
    ):
        lines.append(f"- {key}: `{historical_cost_surface.get(key)}`")
    lines.append("")
    lines.append("## Watch")
    lines.append("")
    for key in ("cycle_name", "trigger_state", "recommended_next_action", "generated_at"):
        lines.append(f"- {key}: `{watch_state.get(key)}`")
    lines.append("")
    lines.append("## Runtime")
    lines.append("")
    for key in ("updated_at", "open_positions_count", "owned_open_positions_count", "flat_since"):
        lines.append(f"- {key}: `{runtime_state.get(key)}`")
    lines.append("")
    lines.append("## PA")
    lines.append("")
    for key in (
        "pa7_review_state",
        "pa8_review_state",
        "scene_bias_review_state",
        "pa7_unresolved_review_group_count",
        "pa8_recommended_next_action",
        "pa78_recommended_next_action",
        "pa9_handoff_state",
        "pa9_review_state",
        "pa9_apply_state",
        "pa9_recommended_next_action",
    ):
        lines.append(f"- {key}: `{pa_state.get(key)}`")
    lines.append("")
    lines.append("## Approval")
    lines.append("")
    for key in (
        "group_status_counts",
        "approval_backlog_count",
        "apply_backlog_count",
        "oldest_pending_approval_age_sec",
        "last_successful_apply_ts",
        "same_scope_conflict_count",
        "late_callback_invalidation_count",
    ):
        lines.append(f"- {key}: `{approval_state.get(key)}`")
    lines.append("")
    lines.append("## Health")
    lines.append("")
    for key in (
        "degraded_components",
        "telegram_healthy",
        "last_error",
        "watch_error_state",
        "reconcile_backlog_count",
    ):
        lines.append(f"- {key}: `{health_state.get(key)}`")
    lines.append("")
    lines.append("## Orchestrator Contract")
    lines.append("")
    for key in (
        "phase_allows_progress",
        "reconcile_signal",
        "approval_backlog_count",
        "apply_backlog_count",
        "reconcile_backlog_count",
        "blocking_reason",
        "next_required_action",
    ):
        lines.append(f"- {key}: `{orchestrator_contract.get(key)}`")
    lines.append("")
    lines.append("## PA8 Symbols")
    lines.append("")
    pa8_symbols = _mapping(system_state.get("pa8_symbols"))
    if not pa8_symbols:
        lines.append("- `none`")
    else:
        for symbol, symbol_state in pa8_symbols.items():
            state_map = _mapping(symbol_state)
            lines.append(
                f"- `{symbol}` active=`{state_map.get('canary_active')}` live_ready=`{state_map.get('live_window_ready')}`"
            )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def extract_checkpoint_improvement_orchestrator_contract(
    board_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    board = _mapping(board_payload)
    contract = _mapping(board.get("orchestrator_contract"))
    if contract:
        return contract
    summary = _mapping(board.get("summary"))
    health_state = _mapping(board.get("health_state"))
    watch_state = _mapping(board.get("watch_state"))
    return {
        "phase": _to_text(summary.get("phase")),
        "phase_allows_progress": _to_text(summary.get("phase")).upper() not in {"EMERGENCY", "SHUTDOWN"},
        "reconcile_signal": _to_int(summary.get("reconcile_backlog_count")) > 0,
        "approval_backlog_count": _to_int(summary.get("pending_approval_count")) + _to_int(summary.get("held_approval_count")),
        "apply_backlog_count": _to_int(summary.get("approved_apply_backlog_count")),
        "reconcile_backlog_count": _to_int(summary.get("reconcile_backlog_count")),
        "blocking_reason": _to_text(summary.get("blocking_reason")),
        "next_required_action": _to_text(summary.get("next_required_action")),
        "degraded_components": list(health_state.get("degraded_components", []) or []),
        "telegram_healthy": _to_bool(health_state.get("telegram_healthy"), True),
        "watch_cycle_name": _to_text(watch_state.get("cycle_name")),
        "watch_trigger_state": _to_text(watch_state.get("trigger_state")),
        "active_pa8_symbol_count": _to_int(summary.get("active_pa8_symbol_count")),
        "live_window_ready_count": _to_int(summary.get("live_window_ready_count")),
    }


def build_checkpoint_improvement_master_board(
    *,
    system_state_manager: SystemStateManager | None = None,
    telegram_state_store: TelegramStateStore | None = None,
    watch_report_path: str | Path | None = None,
    pa8_board_path: str | Path | None = None,
    pa78_review_packet_path: str | Path | None = None,
    pa7_review_processor_path: str | Path | None = None,
    runtime_status_path: str | Path | None = None,
    pa9_handoff_packet_path: str | Path | None = None,
    pa9_review_packet_path: str | Path | None = None,
    pa9_apply_packet_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    manager = system_state_manager or SystemStateManager()
    store = telegram_state_store or TelegramStateStore()
    run_at = _to_text(now_ts, _now_iso())
    now_dt = _parse_iso(run_at) or datetime.now().astimezone()

    state = manager.get_state()
    watch_payload = _load_json(watch_report_path or default_checkpoint_improvement_watch_report_path())
    pa8_payload = _load_json(pa8_board_path or default_checkpoint_pa8_canary_refresh_board_json_path())
    pa78_payload = _load_json(pa78_review_packet_path or default_checkpoint_pa78_review_packet_path())
    pa7_review_processor_payload = _load_json(
        pa7_review_processor_path or default_checkpoint_pa7_review_processor_path()
    )
    runtime_payload = _load_json(runtime_status_path or default_runtime_status_path())
    pa9_handoff_payload = _load_json(
        pa9_handoff_packet_path or default_checkpoint_improvement_pa9_handoff_packet_json_path()
    )
    pa9_review_payload = _load_json(
        pa9_review_packet_path or default_checkpoint_improvement_pa9_handoff_review_packet_json_path()
    )
    pa9_apply_payload = _load_json(
        pa9_apply_packet_path or default_checkpoint_improvement_pa9_handoff_apply_packet_json_path()
    )
    pa8_closeout_runtime = refresh_checkpoint_improvement_pa8_closeout_runtime(
        board_payload=pa8_payload,
    )

    watch_summary = _mapping(watch_payload.get("summary"))
    pa8_summary = _mapping(pa8_payload.get("summary"))
    pa78_summary = _mapping(pa78_payload.get("summary"))
    pa9_handoff_summary = _mapping(pa9_handoff_payload.get("summary"))
    pa9_review_summary = _mapping(pa9_review_payload.get("summary"))
    pa9_apply_summary = _mapping(pa9_apply_payload.get("summary"))
    pa8_closeout_runtime_summary = _mapping(pa8_closeout_runtime.get("summary"))
    runtime_state = _extract_runtime_state(runtime_payload)
    groups = store.list_check_groups(limit=1000)
    recent_actions = store.list_recent_check_actions(limit=5000)
    group_status_counts = _group_status_counts(groups)

    actionable_groups = [
        group for group in groups if _to_text(group.get("status")).lower() in _ACTIONABLE_APPROVAL_STATUSES
    ]
    stale_actionable_count = sum(
        1
        for group in actionable_groups
        if (_parse_iso(group.get("decision_deadline_ts")) or now_dt) < now_dt
        and bool(_to_text(group.get("decision_deadline_ts")))
    )
    pending_approval_count = group_status_counts.get("pending", 0)
    held_approval_count = group_status_counts.get("held", 0)
    approval_backlog_count = pending_approval_count + held_approval_count
    apply_backlog_count = group_status_counts.get("approved", 0)
    same_scope_conflict_count = _same_scope_conflict_count(groups)
    late_callback_invalidation_count = _late_callback_invalidation_count(
        groups=groups,
        actions=recent_actions,
    )
    oldest_pending_approval_age_sec = None
    if actionable_groups:
        pending_ages = [
            age
            for age in (_age_seconds(now_dt, group.get("first_event_ts")) for group in actionable_groups)
            if age is not None
        ]
        if pending_ages:
            oldest_pending_approval_age_sec = max(pending_ages)

    phase = _to_text(state.get("phase"), "STARTING").upper()
    telegram_healthy = _to_bool(state.get("telegram_healthy"), True)
    watch_cycle_name = _to_text(watch_summary.get("cycle_name"))
    watch_trigger_state = _to_text(watch_summary.get("trigger_state"))
    degraded_components = _compute_degraded_components(
        phase=phase,
        telegram_healthy=telegram_healthy,
        watch_cycle_name=watch_cycle_name,
        watch_trigger_state=watch_trigger_state,
    )
    readiness_surface_json_path, readiness_surface_markdown_path = _resolve_readiness_surface_output_paths(
        output_json_path=output_json_path,
    )
    readiness_surface = build_improvement_readiness_surface(
        phase=phase,
        degraded_components=degraded_components,
        pa8_payload=pa8_payload,
        pa7_review_processor_payload=pa7_review_processor_payload,
        pa9_handoff_payload=pa9_handoff_payload,
        pa9_review_payload=pa9_review_payload,
        pa9_apply_payload=pa9_apply_payload,
        runtime_status_payload=runtime_payload,
        runtime_status_path=runtime_status_path or default_runtime_status_path(),
        output_json_path=readiness_surface_json_path,
        output_markdown_path=readiness_surface_markdown_path,
        now_ts=run_at,
    )
    readiness_surface_summary = _mapping(readiness_surface.get("summary"))
    pa8_readiness_surface = _mapping(readiness_surface.get("pa8_closeout_surface"))
    pa8_focus_surface = _mapping(readiness_surface.get("pa8_closeout_focus_surface"))
    first_symbol_surface = _mapping(readiness_surface.get("first_symbol_closeout_handoff_surface"))
    pa9_handoff_surface = _mapping(readiness_surface.get("pa9_handoff_surface"))
    pa7_narrow_review_surface = _mapping(readiness_surface.get("pa7_narrow_review_surface"))
    reverse_surface = _mapping(readiness_surface.get("reverse_surface"))
    historical_cost_surface = _mapping(readiness_surface.get("historical_cost_surface"))
    active_symbol_count = _to_int(pa8_summary.get("active_symbol_count"))
    live_observation_ready_count = _to_int(pa8_summary.get("live_observation_ready_count"))
    pa7_unresolved_review_group_count = _to_int(pa78_summary.get("pa7_unresolved_review_group_count"))
    recent_apply_actions = store.list_recent_check_actions(action="apply", limit=1)
    last_successful_apply_ts = (
        _to_text(_mapping(recent_apply_actions[0]).get("created_at"))
        if recent_apply_actions
        else ""
    )
    if not last_successful_apply_ts:
        applied_group_times = [
            _to_text(group.get("last_event_ts"))
            for group in groups
            if _to_text(group.get("status")).lower() == "applied"
        ]
        candidates = [
            dt for dt in (_parse_iso(value) for value in applied_group_times) if dt is not None
        ]
        if candidates:
            last_successful_apply_ts = max(candidates).isoformat()
    blocking_reason, next_required_action = _blocking_and_next_action(
        phase=phase,
        degraded_components=degraded_components,
        apply_backlog_count=apply_backlog_count,
        approval_backlog_count=approval_backlog_count,
        pa7_unresolved_review_group_count=pa7_unresolved_review_group_count,
        pa7_narrow_review_status=_to_text(readiness_surface_summary.get("pa7_narrow_review_status")),
        pa7_narrow_review_group_count=_to_int(readiness_surface_summary.get("pa7_narrow_review_group_count")),
        active_symbol_count=active_symbol_count,
        live_observation_ready_count=live_observation_ready_count,
        pa9_handoff_state=_to_text(pa9_handoff_summary.get("handoff_state")),
        pa9_review_state=_to_text(pa9_review_summary.get("review_state")),
        runtime_open_positions_count=_to_int(runtime_state.get("open_positions_count")),
        watch_next_action=_to_text(watch_summary.get("recommended_next_action")),
        pa78_next_action=_to_text(pa78_summary.get("recommended_next_action")),
        pa8_next_action=_to_text(pa8_summary.get("recommended_next_action")),
    )
    reconcile_backlog_count = apply_backlog_count + stale_actionable_count + same_scope_conflict_count
    pa8_closeout_readiness_status = _to_text(
        readiness_surface_summary.get("pa8_closeout_readiness_status"),
        derive_pa8_closeout_readiness_status(
            phase=phase,
            active_symbol_count=active_symbol_count,
            live_window_ready_count=live_observation_ready_count,
        ),
    )
    pa9_handoff_state = _to_text(pa9_handoff_summary.get("handoff_state"))
    pa9_review_state = _to_text(pa9_review_summary.get("review_state"))
    pa9_apply_state = _to_text(pa9_apply_summary.get("apply_state"))
    pa9_handoff_readiness_status = _to_text(
        readiness_surface_summary.get("pa9_handoff_readiness_status"),
        derive_pa9_handoff_readiness_status(
            pa9_handoff_state=pa9_handoff_state,
            pa9_review_state=pa9_review_state,
            pa9_apply_state=pa9_apply_state,
        ),
    )
    reverse_readiness_status = _to_text(
        readiness_surface_summary.get("reverse_readiness_status"),
        derive_reverse_readiness_status(
            phase=phase,
            degraded_components=degraded_components,
            runtime_open_positions_count=_to_int(runtime_state.get("open_positions_count")),
        ),
    )
    readiness_state = {
        "pa8_closeout_readiness_status": pa8_closeout_readiness_status,
        "pa8_closeout_blocking_reason": (
            _to_text(pa8_readiness_surface.get("blocking_reason"))
            or (
                "live_window_pending"
                if pa8_closeout_readiness_status == "PENDING_EVIDENCE"
                else ("system_phase_degraded" if pa8_closeout_readiness_status == "BLOCKED" else "none")
            )
        ),
        "pa8_closeout_next_required_action": (
            (
                _to_text(pa8_readiness_surface.get("recommended_next_action"))
                or _to_text(pa8_summary.get("recommended_next_action"))
            )
            if pa8_closeout_readiness_status in {"PENDING_EVIDENCE", "BLOCKED"}
            else "review_pa8_closeout_candidate"
        ),
        "pa8_closeout_focus_status": _to_text(
            pa8_focus_surface.get("focus_status"),
            "NOT_APPLICABLE",
        ),
        "pa8_closeout_focus_reason": _to_text(
            pa8_focus_surface.get("primary_focus_reason_ko"),
            "아직 집중 관찰할 closeout 후보가 없습니다.",
        ),
        "pa8_closeout_focus_next_required_action": _to_text(
            pa8_focus_surface.get("recommended_next_action"),
            "wait_for_active_pa8_canary",
        ),
        "pa8_primary_focus_symbol": _to_text(pa8_focus_surface.get("primary_focus_symbol")),
        "pa8_focus_symbol_count": _to_int(pa8_focus_surface.get("focus_symbol_count")),
        "pa8_focus_watchlist_symbol_count": _to_int(pa8_focus_surface.get("watchlist_symbol_count")),
        "first_symbol_closeout_handoff_status": _to_text(
            first_symbol_surface.get("observation_status"),
            "NOT_APPLICABLE",
        ),
        "first_symbol_closeout_handoff_symbol": _to_text(
            first_symbol_surface.get("primary_symbol")
        ),
        "first_symbol_closeout_handoff_stage": _to_text(
            first_symbol_surface.get("observation_stage"),
            "NONE",
        ),
        "first_symbol_closeout_handoff_reason": _to_text(
            first_symbol_surface.get("reason_ko"),
            "아직 first symbol closeout/handoff 관찰 대상이 없습니다.",
        ),
        "first_symbol_closeout_handoff_next_required_action": _to_text(
            first_symbol_surface.get("recommended_next_action"),
            "wait_for_first_pa8_symbol_candidate",
        ),
        "pa8_closeout_review_state": _to_text(
            pa8_closeout_runtime_summary.get("review_state"),
            "HOLD_NO_ACTIVE_PA8_CANARY",
        ),
        "pa8_closeout_apply_state": _to_text(
            pa8_closeout_runtime_summary.get("apply_state"),
            "HOLD_PENDING_PA8_CLOSEOUT_REVIEW",
        ),
        "pa9_handoff_readiness_status": pa9_handoff_readiness_status,
        "pa9_handoff_blocking_reason": (
            _to_text(pa9_handoff_surface.get("blocking_reason"))
            or (
                "live_window_pending"
                if pa9_handoff_readiness_status == "PENDING_EVIDENCE"
                else "none"
            )
        ),
        "pa9_handoff_next_required_action": _to_text(
            pa9_handoff_surface.get("recommended_next_action")
            or pa9_apply_summary.get("recommended_next_action")
            or pa9_review_summary.get("recommended_next_action")
            or pa9_handoff_summary.get("recommended_next_action")
            or "review_pa9_handoff_state"
        ),
        "pa7_narrow_review_status": _to_text(
            pa7_narrow_review_surface.get("status"),
            "NOT_APPLICABLE",
        ),
        "pa7_narrow_review_group_count": _to_int(
            pa7_narrow_review_surface.get("group_count")
        ),
        "pa7_narrow_review_primary_group_key": _to_text(
            pa7_narrow_review_surface.get("primary_group_key")
        ),
        "pa7_narrow_review_next_required_action": _to_text(
            pa7_narrow_review_surface.get("recommended_next_action"),
            "wait_for_pa7_review_processor_refresh",
        ),
        "reverse_readiness_status": reverse_readiness_status,
        "reverse_blocking_reason": (
            _to_text(reverse_surface.get("blocking_reason"))
            or (
                "system_phase_degraded"
                if reverse_readiness_status == "BLOCKED"
                else ("reverse_wait_for_flat" if reverse_readiness_status == "PENDING_EVIDENCE" else "none")
            )
        ),
        "reverse_next_required_action": (
            "review_pending_reverse_candidate_and_wait_for_flat_transition"
            if reverse_readiness_status == "READY_FOR_APPLY"
            else (
                "inspect_runtime_reverse_state_and_wait_for_flat_transition"
                if reverse_readiness_status == "PENDING_EVIDENCE"
                else (
                    "inspect_degraded_components_and_restore_dependencies"
                    if reverse_readiness_status == "BLOCKED"
                    else "wait_for_reverse_candidate"
                )
            )
        ),
        "historical_cost_confidence_level": _to_text(
            historical_cost_surface.get("confidence_level"),
            CONFIDENCE_LEVEL_LIMITED,
        ),
        "historical_cost_blocking_reason": _to_text(
            historical_cost_surface.get("blocking_reason"),
            "historical_cost_limited",
        ),
        "historical_cost_note": _to_text(
            historical_cost_surface.get("note"),
            "historical trade cost metadata is incomplete before the recent cost schema upgrade",
        ),
        "pa8_closeout_surface": pa8_readiness_surface,
        "pa8_closeout_focus_surface": pa8_focus_surface,
        "first_symbol_closeout_handoff_surface": first_symbol_surface,
        "pa8_closeout_runtime": pa8_closeout_runtime,
        "pa9_handoff_surface": pa9_handoff_surface,
        "pa7_narrow_review_surface": pa7_narrow_review_surface,
        "reverse_surface": reverse_surface,
        "historical_cost_surface": historical_cost_surface,
    }
    pa8_closeout_focus_status = _to_text(readiness_state.get("pa8_closeout_focus_status"))
    pa8_closeout_focus_next_action = _to_text(
        readiness_state.get("pa8_closeout_focus_next_required_action")
    )
    if (
        blocking_reason == "pa8_live_window_pending"
        and pa8_closeout_focus_status in {"CONCENTRATED", "READY_FOR_REVIEW"}
        and pa8_closeout_focus_next_action
    ):
        next_required_action = pa8_closeout_focus_next_action
    orchestrator_contract = {
        "phase": phase,
        "phase_allows_progress": phase not in {"EMERGENCY", "SHUTDOWN"},
        "reconcile_signal": reconcile_backlog_count > 0,
        "approval_backlog_count": approval_backlog_count,
        "apply_backlog_count": apply_backlog_count,
        "reconcile_backlog_count": reconcile_backlog_count,
        "blocking_reason": blocking_reason,
        "next_required_action": next_required_action,
        "degraded_components": degraded_components,
        "telegram_healthy": telegram_healthy,
        "watch_cycle_name": watch_cycle_name,
        "watch_trigger_state": watch_trigger_state,
        "active_pa8_symbol_count": active_symbol_count,
        "live_window_ready_count": live_observation_ready_count,
        "runtime_open_positions_count": _to_int(runtime_state.get("open_positions_count")),
    }

    payload: dict[str, Any] = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_MASTER_BOARD_CONTRACT_VERSION,
            "field_policy_version": IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION,
            "generated_at": run_at,
            "trigger_state": "MASTER_BOARD_REFRESHED",
            "recommended_next_action": next_required_action,
            "phase": phase,
            "blocking_reason": blocking_reason,
            "next_required_action": next_required_action,
            "active_pa8_symbol_count": active_symbol_count,
            "live_window_ready_count": live_observation_ready_count,
            "runtime_open_positions_count": _to_int(runtime_state.get("open_positions_count")),
            "runtime_flat_since": _to_text(runtime_state.get("flat_since")),
            "pending_approval_count": pending_approval_count,
            "held_approval_count": held_approval_count,
            "approved_apply_backlog_count": apply_backlog_count,
            "oldest_pending_approval_age_sec": oldest_pending_approval_age_sec,
            "last_successful_apply_ts": last_successful_apply_ts,
            "degraded_components": degraded_components,
            "reconcile_backlog_count": reconcile_backlog_count,
            "same_scope_conflict_count": same_scope_conflict_count,
            "pa8_closeout_readiness_status": pa8_closeout_readiness_status,
            "pa8_closeout_focus_status": readiness_state["pa8_closeout_focus_status"],
            "pa8_focus_symbol_count": readiness_state["pa8_focus_symbol_count"],
            "pa8_primary_focus_symbol": readiness_state["pa8_primary_focus_symbol"],
            "first_symbol_closeout_handoff_status": readiness_state["first_symbol_closeout_handoff_status"],
            "first_symbol_closeout_handoff_symbol": readiness_state["first_symbol_closeout_handoff_symbol"],
            "pa8_closeout_review_state": readiness_state["pa8_closeout_review_state"],
            "pa8_closeout_apply_state": readiness_state["pa8_closeout_apply_state"],
            "pa9_handoff_readiness_status": pa9_handoff_readiness_status,
            "pa7_narrow_review_status": readiness_state["pa7_narrow_review_status"],
            "pa7_narrow_review_group_count": readiness_state["pa7_narrow_review_group_count"],
            "reverse_readiness_status": reverse_readiness_status,
            "historical_cost_confidence_level": readiness_state["historical_cost_confidence_level"],
        },
        "readiness_state": readiness_state,
        "system_state": {
            "phase": phase,
            "last_row_ts": _to_text(state.get("last_row_ts")),
            "row_count_since_boot": _to_int(state.get("row_count_since_boot")),
            "light_last_run": _to_text(state.get("light_last_run")),
            "heavy_last_run": _to_text(state.get("heavy_last_run")),
            "governance_last_run": _to_text(state.get("governance_last_run")),
            "telegram_healthy": telegram_healthy,
            "last_error": _to_text(state.get("last_error")),
            "pa8_symbols": _mapping(state.get("pa8_symbols")),
        },
        "watch_state": {
            "cycle_name": watch_cycle_name,
            "trigger_state": watch_trigger_state,
            "recommended_next_action": _to_text(watch_summary.get("recommended_next_action")),
            "generated_at": _to_text(watch_summary.get("generated_at")),
        },
        "runtime_state": runtime_state,
        "pa_state": {
            "pa7_review_state": _to_text(pa78_summary.get("pa7_review_state")),
            "pa8_review_state": _to_text(pa78_summary.get("pa8_review_state")),
            "scene_bias_review_state": _to_text(pa78_summary.get("scene_bias_review_state")),
            "pa7_unresolved_review_group_count": pa7_unresolved_review_group_count,
            "pa8_recommended_next_action": _to_text(pa8_summary.get("recommended_next_action")),
            "pa8_closeout_review_state": readiness_state["pa8_closeout_review_state"],
            "pa8_closeout_apply_state": readiness_state["pa8_closeout_apply_state"],
            "pa8_closeout_recommended_next_action": _to_text(
                pa8_closeout_runtime_summary.get("recommended_next_action")
            ),
            "pa78_recommended_next_action": _to_text(pa78_summary.get("recommended_next_action")),
            "pa7_narrow_review_status": readiness_state["pa7_narrow_review_status"],
            "pa7_narrow_review_group_count": readiness_state["pa7_narrow_review_group_count"],
            "pa7_narrow_review_primary_group_key": readiness_state["pa7_narrow_review_primary_group_key"],
            "pa9_handoff_state": pa9_handoff_state,
            "pa9_review_state": pa9_review_state,
            "pa9_apply_state": pa9_apply_state,
            "pa9_recommended_next_action": _to_text(
                pa9_apply_summary.get("recommended_next_action")
                or pa9_review_summary.get("recommended_next_action")
                or pa9_handoff_summary.get("recommended_next_action")
            ),
        },
        "approval_state": {
            "group_status_counts": group_status_counts,
            "approval_backlog_count": approval_backlog_count,
            "apply_backlog_count": apply_backlog_count,
            "oldest_pending_approval_age_sec": oldest_pending_approval_age_sec,
            "last_successful_apply_ts": last_successful_apply_ts,
            "stale_actionable_count": stale_actionable_count,
            "same_scope_conflict_count": same_scope_conflict_count,
            "late_callback_invalidation_count": late_callback_invalidation_count,
        },
        "health_state": {
            "degraded_components": degraded_components,
            "telegram_healthy": telegram_healthy,
            "last_error": _to_text(state.get("last_error")),
            "watch_error_state": watch_trigger_state if watch_trigger_state == "WATCH_ERROR" else "",
            "reconcile_backlog_count": reconcile_backlog_count,
        },
        "orchestrator_contract": orchestrator_contract,
        "artifacts": {
            "watch_report_path": str(watch_report_path or default_checkpoint_improvement_watch_report_path()),
            "pa8_board_path": str(pa8_board_path or default_checkpoint_pa8_canary_refresh_board_json_path()),
            "pa78_review_packet_path": str(pa78_review_packet_path or default_checkpoint_pa78_review_packet_path()),
            "pa7_review_processor_path": str(
                pa7_review_processor_path or default_checkpoint_pa7_review_processor_path()
            ),
            "pa9_handoff_packet_path": str(
                pa9_handoff_packet_path or default_checkpoint_improvement_pa9_handoff_packet_json_path()
            ),
            "pa9_review_packet_path": str(
                pa9_review_packet_path or default_checkpoint_improvement_pa9_handoff_review_packet_json_path()
            ),
            "pa9_apply_packet_path": str(
                pa9_apply_packet_path or default_checkpoint_improvement_pa9_handoff_apply_packet_json_path()
            ),
            "pa8_closeout_runtime_path": str(
                default_checkpoint_improvement_pa8_closeout_runtime_json_path()
            ),
            "runtime_status_path": str(runtime_status_path or default_runtime_status_path()),
            "system_state_path": str(manager.state_path),
            "telegram_state_store_path": str(store.db_path),
            "readiness_surface_path": str(readiness_surface_json_path),
            "readiness_surface_markdown_path": str(readiness_surface_markdown_path),
        },
    }

    json_path = Path(output_json_path or default_checkpoint_improvement_master_board_json_path())
    markdown_path = Path(output_markdown_path or default_checkpoint_improvement_master_board_markdown_path())
    _write_json(json_path, payload)
    _write_text(markdown_path, _render_markdown(payload))
    return payload
