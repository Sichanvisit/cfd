from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from backend.services.state25_threshold_patch_apply_handlers import (
    State25ThresholdPatchApplyHandlerSet,
)
from backend.services.state25_threshold_patch_review import (
    build_state25_threshold_patch_review_candidate_from_context_bridge_v1,
)
from backend.services.state25_weight_patch_apply_handlers import (
    State25WeightPatchApplyHandlerSet,
)
from backend.services.state25_weight_patch_review import (
    build_state25_weight_patch_review_candidate_from_context_bridge_v1,
)
from backend.services.teacher_pattern_active_candidate_runtime import (
    build_default_active_candidate_state,
)


STATE25_CONTEXT_BRIDGE_BOUNDED_LIVE_READINESS_CONTRACT_VERSION = (
    "state25_context_bridge_bounded_live_readiness_v1"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_detector_snapshot_path() -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / "improvement_log_only_detector_latest.json"
    )


def _default_runtime_status_detail_path() -> Path:
    return _repo_root() / "data" / "runtime_status.detail.json"


def _default_active_candidate_state_path() -> Path:
    return (
        _repo_root()
        / "models"
        / "teacher_pattern_state25_candidates"
        / "active_candidate_state.json"
    )


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _latest_signal_index(payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    latest_signal_by_symbol = _mapping(_mapping(payload).get("latest_signal_by_symbol"))
    index: dict[str, dict[str, Any]] = {}
    for raw_symbol, raw_row in latest_signal_by_symbol.items():
        symbol = _to_text(raw_symbol).upper()
        row = _mapping(raw_row)
        if symbol and row:
            index[symbol] = row
    return index


def _iter_candle_weight_rows(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    section = _mapping(_mapping(payload).get("candle_weight_detector"))
    rows: list[dict[str, Any]] = []
    for bucket in ("surfaced_rows", "cooldown_suppressed_rows"):
        for raw_row in list(section.get(bucket) or []):
            row = _mapping(raw_row)
            if not row:
                continue
            row["_source_bucket"] = bucket
            rows.append(row)
    return rows


def _cooldown_meta(payload: Mapping[str, Any] | None, scope_key: str) -> dict[str, Any]:
    rows_by_scope = _mapping(
        _mapping(_mapping(payload).get("cooldown_state")).get("rows_by_scope")
    )
    return _mapping(rows_by_scope.get(scope_key))


def _render_markdown(report: Mapping[str, Any] | None) -> str:
    row = _mapping(report)
    summary = _mapping(row.get("summary"))
    lines = [
        "# State25 Context Bridge Bounded Live Readiness",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- active_binding_mode: `{_to_text(summary.get('active_binding_mode'))}`",
        f"- weight_candidate_count: `{int(_to_float(summary.get('weight_candidate_count'), 0.0))}`",
        f"- threshold_candidate_count: `{int(_to_float(summary.get('threshold_candidate_count'), 0.0))}`",
        f"- weight_apply_ready_count: `{int(_to_float(summary.get('weight_apply_ready_count'), 0.0))}`",
        f"- threshold_apply_ready_count: `{int(_to_float(summary.get('threshold_apply_ready_count'), 0.0))}`",
        f"- threshold_shared_delta_blocked: `{str(bool(summary.get('threshold_shared_delta_blocked'))).lower()}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        "",
        "## Weight Candidates",
        "",
    ]
    weight_rows = list(row.get("weight_candidates") or [])
    if not weight_rows:
        lines.append("- none")
    for candidate in weight_rows:
        candidate_map = _mapping(candidate)
        lines.append(
            f"- {_to_text(candidate_map.get('summary_ko'))}: ready={str(bool(candidate_map.get('apply_ready'))).lower()} "
            f"| bucket={_to_text(candidate_map.get('source_bucket')) or '-'} "
            f"| block={', '.join(list(candidate_map.get('apply_block_reasons') or []) or ['none'])}"
        )
    lines.extend(["", "## Threshold Candidates", ""])
    threshold_rows = list(row.get("threshold_candidates") or [])
    if not threshold_rows:
        lines.append("- none")
    for candidate in threshold_rows:
        candidate_map = _mapping(candidate)
        lines.append(
            f"- {_to_text(candidate_map.get('summary_ko'))}: ready={str(bool(candidate_map.get('apply_ready'))).lower()} "
            f"| bucket={_to_text(candidate_map.get('source_bucket')) or '-'} "
            f"| delta=+{_to_float(candidate_map.get('bridge_threshold_effective_points'), 0.0):.2f}pt "
            f"| block={', '.join(list(candidate_map.get('apply_block_reasons') or []) or ['none'])}"
        )
    return "\n".join(lines) + "\n"


def _build_weight_candidate_readiness(
    issue_row: Mapping[str, Any],
    *,
    runtime_row: Mapping[str, Any] | None,
    detector_snapshot_payload: Mapping[str, Any] | None,
    now_dt: datetime,
) -> dict[str, Any]:
    issue_map = _mapping(issue_row)
    preview = build_state25_weight_patch_review_candidate_from_context_bridge_v1(
        runtime_row or issue_map,
        bridge_payload=_mapping(issue_map.get("state25_candidate_context_bridge_v1")),
        state25_execution_bind_mode="bounded_live",
    )
    if not preview:
        return {}
    scope_key = _to_text(issue_map.get("feedback_scope_key"))
    cooldown = _cooldown_meta(detector_snapshot_payload, scope_key)
    last_surfaced_dt = _parse_iso(cooldown.get("last_surfaced_at"))
    cooldown_window_min = int(_to_float(cooldown.get("cooldown_window_min"), 0.0))
    next_eligible_dt = (
        last_surfaced_dt + timedelta(minutes=cooldown_window_min)
        if last_surfaced_dt is not None and cooldown_window_min > 0
        else None
    )
    cooldown_active = bool(next_eligible_dt and next_eligible_dt > now_dt)
    runtime_map = _mapping(runtime_row)
    current_requested_count = int(
        _to_float(runtime_map.get("state25_context_bridge_weight_requested_count"), 0.0)
    )
    current_effective_count = int(
        _to_float(runtime_map.get("state25_context_bridge_weight_effective_count"), 0.0)
    )
    block_reasons: list[str] = []
    if cooldown_active:
        block_reasons.append("COOLDOWN_ACTIVE")
    if current_requested_count <= 0:
        block_reasons.append("RUNTIME_BRIDGE_ZERO")
    return {
        **preview,
        "source_bucket": _to_text(issue_map.get("_source_bucket")),
        "source_feedback_scope_key": scope_key,
        "cooldown_active": cooldown_active,
        "cooldown_window_min": cooldown_window_min,
        "last_surfaced_at": _to_text(cooldown.get("last_surfaced_at")),
        "next_eligible_at": next_eligible_dt.isoformat() if next_eligible_dt else "",
        "current_runtime_weight_requested_count": current_requested_count,
        "current_runtime_weight_effective_count": current_effective_count,
        "apply_block_reasons": block_reasons,
        "apply_ready": not block_reasons,
    }


def _build_threshold_candidate_readiness(
    issue_row: Mapping[str, Any],
    *,
    runtime_row: Mapping[str, Any] | None,
    detector_snapshot_payload: Mapping[str, Any] | None,
    now_dt: datetime,
) -> dict[str, Any]:
    issue_map = _mapping(issue_row)
    preview = build_state25_threshold_patch_review_candidate_from_context_bridge_v1(
        runtime_row or issue_map,
        bridge_payload=_mapping(issue_map.get("state25_candidate_context_bridge_v1")),
        state25_execution_bind_mode="bounded_live",
    )
    if not preview:
        return {}
    scope_key = _to_text(issue_map.get("feedback_scope_key"))
    cooldown = _cooldown_meta(detector_snapshot_payload, scope_key)
    last_surfaced_dt = _parse_iso(cooldown.get("last_surfaced_at"))
    cooldown_window_min = int(_to_float(cooldown.get("cooldown_window_min"), 0.0))
    next_eligible_dt = (
        last_surfaced_dt + timedelta(minutes=cooldown_window_min)
        if last_surfaced_dt is not None and cooldown_window_min > 0
        else None
    )
    cooldown_active = bool(next_eligible_dt and next_eligible_dt > now_dt)
    runtime_map = _mapping(runtime_row)
    current_requested_points = _to_float(
        runtime_map.get("state25_context_bridge_threshold_requested_points"), 0.0
    )
    current_effective_points = _to_float(
        runtime_map.get("state25_context_bridge_threshold_effective_points"), 0.0
    )
    block_reasons: list[str] = []
    if cooldown_active:
        block_reasons.append("COOLDOWN_ACTIVE")
    if current_requested_points <= 0.0:
        block_reasons.append("RUNTIME_BRIDGE_ZERO")
    return {
        **preview,
        "source_bucket": _to_text(issue_map.get("_source_bucket")),
        "source_feedback_scope_key": scope_key,
        "cooldown_active": cooldown_active,
        "cooldown_window_min": cooldown_window_min,
        "last_surfaced_at": _to_text(cooldown.get("last_surfaced_at")),
        "next_eligible_at": next_eligible_dt.isoformat() if next_eligible_dt else "",
        "current_runtime_threshold_requested_points": current_requested_points,
        "current_runtime_threshold_effective_points": current_effective_points,
        "apply_block_reasons": block_reasons,
        "apply_ready": not block_reasons,
    }


def build_state25_context_bridge_bounded_live_readiness(
    *,
    detector_snapshot_payload: Mapping[str, Any] | None = None,
    runtime_status_detail_payload: Mapping[str, Any] | None = None,
    active_candidate_state_payload: Mapping[str, Any] | None = None,
    execute_apply: bool = False,
    active_candidate_state_path: str | Path | None = None,
    shadow_auto_dir: str | Path | None = None,
    now_ts: object | None = None,
) -> dict[str, Any]:
    generated_at = _to_text(now_ts, _now_iso())
    now_dt = _parse_iso(generated_at) or datetime.now().astimezone()
    detector_snapshot = _mapping(detector_snapshot_payload) or _load_json(
        _default_detector_snapshot_path()
    )
    runtime_detail = _mapping(runtime_status_detail_payload) or _load_json(
        _default_runtime_status_detail_path()
    )
    active_state = build_default_active_candidate_state()
    active_state.update(
        _mapping(active_candidate_state_payload)
        or _load_json(
            Path(active_candidate_state_path)
            if active_candidate_state_path is not None
            else _default_active_candidate_state_path()
        )
    )
    runtime_index = _latest_signal_index(runtime_detail)

    weight_candidates: list[dict[str, Any]] = []
    threshold_candidates: list[dict[str, Any]] = []
    for issue_row in _iter_candle_weight_rows(detector_snapshot):
        issue_map = _mapping(issue_row)
        symbol = _to_text(issue_map.get("symbol")).upper()
        runtime_row = _mapping(runtime_index.get(symbol))
        if _mapping(issue_map.get("weight_patch_preview")):
            candidate = _build_weight_candidate_readiness(
                issue_map,
                runtime_row=runtime_row,
                detector_snapshot_payload=detector_snapshot,
                now_dt=now_dt,
            )
            if candidate:
                weight_candidates.append(candidate)
        if _mapping(issue_map.get("threshold_patch_preview")):
            candidate = _build_threshold_candidate_readiness(
                issue_map,
                runtime_row=runtime_row,
                detector_snapshot_payload=detector_snapshot,
                now_dt=now_dt,
            )
            if candidate:
                threshold_candidates.append(candidate)

    weight_apply_ready = [row for row in weight_candidates if bool(row.get("apply_ready"))]
    threshold_apply_ready = [row for row in threshold_candidates if bool(row.get("apply_ready"))]
    threshold_effective_points = {
        round(_to_float(row.get("bridge_threshold_effective_points"), 0.0), 6)
        for row in threshold_apply_ready
    }
    threshold_shared_delta_blocked = len(threshold_effective_points) > 1
    if threshold_shared_delta_blocked:
        for row in threshold_apply_ready:
            row.setdefault("apply_block_reasons", []).append(
                "SHARED_THRESHOLD_DELTA_CONTRACT_BLOCKED"
            )
            row["apply_ready"] = False
        threshold_apply_ready = []

    applied_weight = {}
    applied_threshold = {}
    if execute_apply and weight_apply_ready:
        weight_handler = State25WeightPatchApplyHandlerSet(
            active_candidate_state_path=active_candidate_state_path,
            shadow_auto_dir=shadow_auto_dir,
        )
        applied_weight = weight_handler.handle_weight_patch_review(
            approval_event_payload={
                "approval_id": f"auto-weight-{now_dt.strftime('%Y%m%d%H%M%S')}",
                "scope_key": _to_text(weight_apply_ready[0].get("scope_key")),
            },
            group={"scope_key": _to_text(weight_apply_ready[0].get("scope_key"))},
            review_payload=weight_apply_ready[0],
            now_ts=generated_at,
        )
    if execute_apply and threshold_apply_ready:
        threshold_handler = State25ThresholdPatchApplyHandlerSet(
            active_candidate_state_path=active_candidate_state_path,
            shadow_auto_dir=shadow_auto_dir,
        )
        applied_threshold = threshold_handler.handle_threshold_patch_review(
            approval_event_payload={
                "approval_id": f"auto-threshold-{now_dt.strftime('%Y%m%d%H%M%S')}",
                "scope_key": _to_text(threshold_apply_ready[0].get("scope_key")),
            },
            group={"scope_key": _to_text(threshold_apply_ready[0].get("scope_key"))},
            review_payload=threshold_apply_ready[0],
            now_ts=generated_at,
        )

    recommended_next_action = "wait_for_fresh_state25_context_bridge_surface_after_cooldown"
    if threshold_shared_delta_blocked:
        recommended_next_action = "split_threshold_bounded_live_by_symbol_before_apply"
    elif execute_apply and (applied_weight or applied_threshold):
        recommended_next_action = "observe_bounded_live_runtime_and_collect_evidence"
    elif weight_apply_ready:
        recommended_next_action = "review_weight_bounded_live_candidate_for_apply"
    elif threshold_apply_ready:
        recommended_next_action = "review_threshold_bounded_live_candidate_for_apply"

    report = {
        "contract_version": STATE25_CONTEXT_BRIDGE_BOUNDED_LIVE_READINESS_CONTRACT_VERSION,
        "summary": {
            "generated_at": generated_at,
            "active_candidate_id": _to_text(active_state.get("active_candidate_id")),
            "active_rollout_phase": _to_text(active_state.get("current_rollout_phase")),
            "active_binding_mode": _to_text(active_state.get("current_binding_mode")),
            "weight_candidate_count": len(weight_candidates),
            "threshold_candidate_count": len(threshold_candidates),
            "weight_apply_ready_count": len(weight_apply_ready),
            "threshold_apply_ready_count": len(threshold_apply_ready),
            "threshold_shared_delta_blocked": threshold_shared_delta_blocked,
            "execute_apply": bool(execute_apply),
            "recommended_next_action": recommended_next_action,
        },
        "active_candidate_state": active_state,
        "weight_candidates": weight_candidates,
        "threshold_candidates": threshold_candidates,
        "applied_weight": applied_weight,
        "applied_threshold": applied_threshold,
    }
    output_dir = (
        Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    )
    json_path = output_dir / "state25_context_bridge_bounded_live_readiness_latest.json"
    md_path = output_dir / "state25_context_bridge_bounded_live_readiness_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, _render_markdown(report))
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    return report
