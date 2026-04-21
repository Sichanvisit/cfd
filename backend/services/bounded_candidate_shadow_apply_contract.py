from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from backend.services.bounded_calibration_candidate_contract import (
    BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
    build_bounded_calibration_candidate_summary_v1,
)


BOUNDED_CANDIDATE_SHADOW_APPLY_CONTRACT_VERSION = "bounded_candidate_shadow_apply_contract_v1"
BOUNDED_CANDIDATE_SHADOW_APPLY_SUMMARY_VERSION = "bounded_candidate_shadow_apply_summary_v1"

APPLY_MODE_ENUM_V1 = ("NONE", "SHADOW_ONLY")
APPLY_SESSION_STATE_ENUM_V1 = ("NOT_APPLICABLE", "ACTIVE", "HOLD", "BLOCKED")
DRIFT_GUARD_STATE_ENUM_V1 = ("NOT_APPLICABLE", "CLEAR", "BLOCKED_BY_CUMULATIVE_SHIFT")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_bounded_candidate_shadow_apply_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_CANDIDATE_SHADOW_APPLY_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F10 bounded candidate shadow apply layer. Consumes F9 bounded calibration candidates and "
            "creates shadow-only apply sessions for SHADOW_REQUIRED candidates without changing live interpretation."
        ),
        "upstream_contract_versions_v1": [
            BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
        ],
        "apply_mode_enum_v1": list(APPLY_MODE_ENUM_V1),
        "apply_session_state_enum_v1": list(APPLY_SESSION_STATE_ENUM_V1),
        "drift_guard_state_enum_v1": list(DRIFT_GUARD_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_apply_session_id_v1",
            "bounded_apply_candidate_id_v1",
            "bounded_apply_mode_v1",
            "bounded_apply_session_state_v1",
            "bounded_apply_scope_match_v1",
            "flow_support_state_before_v1",
            "flow_support_state_after_v1",
            "flow_structure_gate_before_v1",
            "flow_structure_gate_after_v1",
            "aggregate_conviction_before_v1",
            "aggregate_conviction_after_v1",
            "flow_persistence_before_v1",
            "flow_persistence_after_v1",
            "flow_state_changed_v1",
            "flow_state_change_type_v1",
            "conviction_delta_v1",
            "persistence_delta_v1",
            "candidate_effect_direction_v1",
            "bounded_apply_conflict_flag_v1",
            "bounded_apply_conflict_reason_v1",
            "bounded_apply_block_reason_v1",
            "bounded_apply_drift_guard_state_v1",
            "bounded_apply_reason_summary_v1",
        ],
        "control_rules_v1": [
            "F10 is an operational layer and must not rewrite dominant_side, dominance_gap, rejection split, or structure gate authority",
            "only candidates with graduation state SHADOW_REQUIRED can open apply sessions",
            "default apply mode is SHADOW_ONLY",
            "row-level before and after fields are surfaced without changing live decision state",
            "same-symbol non-primary shadow-required candidates are held instead of activated together",
            "cumulative drift guard blocks additional shift when a learning key would move beyond the bounded memory limit",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _shadow_required_candidate(candidate: Mapping[str, Any]) -> bool:
    payload = _mapping(candidate)
    return (
        _text(payload.get("status")).upper() == "PROPOSED"
        and _text(payload.get("candidate_graduation_state_v1")).upper() == "SHADOW_REQUIRED"
    )


def _candidate_session_id(candidate: Mapping[str, Any]) -> str:
    payload = _mapping(candidate)
    symbol = _text(payload.get("symbol")).upper() or "UNKNOWN"
    learning_key = _text(payload.get("learning_key")).replace(".", "-") or "unknown"
    return f"F10-{symbol}-{learning_key}-SHADOW"


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[float, float, str]:
    payload = _mapping(candidate)
    return (
        _float(payload.get("candidate_priority_score_v1"), 0.0),
        _float(payload.get("importance_score"), 0.0),
        _text(payload.get("candidate_id")),
    )


def _shared_learning_key(candidate: Mapping[str, Any]) -> bool:
    scope = _mapping(_mapping(candidate).get("validation_scope_v1"))
    return _bool(scope.get("cross_symbol_required_v1"))


def _drift_guard_state(row: Mapping[str, Any], candidate: Mapping[str, Any]) -> str:
    payload = _mapping(row)
    candidate_payload = _mapping(candidate)
    learning_key = _text(candidate_payload.get("learning_key"))
    drift_by_key = _mapping(payload.get("bounded_apply_cumulative_shift_by_key_v1"))
    current_shift = _float(drift_by_key.get(learning_key), _float(payload.get("bounded_apply_cumulative_shift_v1"), 0.0))
    next_shift = current_shift + _float(candidate_payload.get("delta"), 0.0)
    limit = 0.1 if _shared_learning_key(candidate_payload) else 0.15
    if abs(next_shift) > limit:
        return "BLOCKED_BY_CUMULATIVE_SHIFT"
    return "CLEAR"


def _candidate_effect_magnitude(candidate: Mapping[str, Any]) -> float:
    payload = _mapping(candidate)
    delta = abs(_float(payload.get("delta"), 0.0))
    max_allowed_delta = max(0.0001, abs(_float(payload.get("max_allowed_delta"), 0.0)))
    ratio = min(1.0, delta / max_allowed_delta)
    return round(min(0.12, ratio * 0.12), 4)


def _shadow_metrics_after(row: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[float, float]:
    payload = _mapping(row)
    candidate_payload = _mapping(candidate)
    before_conviction = _float(payload.get("aggregate_conviction_v1"), 0.0)
    before_persistence = _float(payload.get("flow_persistence_v1"), 0.0)
    learning_key = _text(candidate_payload.get("learning_key"))
    direction = _text(candidate_payload.get("direction")).upper()
    effect = _candidate_effect_magnitude(candidate_payload)
    signed = effect if direction == "RELAX" else -effect if direction == "TIGHTEN" else 0.0

    after_conviction = before_conviction
    after_persistence = before_persistence
    if learning_key in {
        "flow.ambiguity_threshold",
        "flow.conviction_building_floor",
        "flow.ambiguity_penalty_scale",
        "flow.veto_penalty_scale",
    }:
        after_conviction = _clamp01(before_conviction + signed)
    elif learning_key in {
        "flow.persistence_building_floor",
        "flow.persistence_recency_weight_scale",
    }:
        after_persistence = _clamp01(before_persistence + signed)
    elif learning_key == "flow.structure_soft_score_floor":
        after_conviction = _clamp01(before_conviction + (signed * 0.7))
        after_persistence = _clamp01(before_persistence + (signed * 0.3))

    return round(after_conviction, 4), round(after_persistence, 4)


def _flow_state_after(row: Mapping[str, Any], candidate: Mapping[str, Any], after_conviction: float, after_persistence: float) -> str:
    payload = _mapping(row)
    candidate_payload = _mapping(candidate)
    before_state = _text(payload.get("flow_support_state_v1")).upper() or "NONE"
    direction = _text(candidate_payload.get("direction")).upper()
    building_conviction_floor = _float(payload.get("aggregate_conviction_building_floor_v1"), 0.55)
    building_persistence_floor = _float(payload.get("flow_persistence_building_floor_v1"), 0.55)
    confirmed_conviction_floor = _float(
        payload.get("aggregate_conviction_confirmed_floor_v1"),
        min(0.9, building_conviction_floor + 0.1),
    )
    confirmed_persistence_floor = _float(
        payload.get("flow_persistence_confirmed_floor_v1"),
        min(0.9, building_persistence_floor + 0.1),
    )

    if direction == "RELAX":
        if before_state == "FLOW_OPPOSED":
            if after_conviction >= (building_conviction_floor * 0.85) and after_persistence >= (building_persistence_floor * 0.85):
                return "FLOW_UNCONFIRMED"
            return before_state
        if before_state == "FLOW_UNCONFIRMED":
            if after_conviction >= building_conviction_floor and after_persistence >= building_persistence_floor:
                return "FLOW_BUILDING"
            return before_state
        if before_state == "FLOW_BUILDING":
            if after_conviction >= confirmed_conviction_floor and after_persistence >= confirmed_persistence_floor:
                return "FLOW_CONFIRMED"
            return before_state
        return before_state

    if direction == "TIGHTEN":
        if before_state == "FLOW_CONFIRMED":
            if after_conviction >= confirmed_conviction_floor and after_persistence >= confirmed_persistence_floor:
                return before_state
            if after_conviction >= building_conviction_floor and after_persistence >= building_persistence_floor:
                return "FLOW_BUILDING"
            return "FLOW_UNCONFIRMED"
        if before_state == "FLOW_BUILDING":
            if after_conviction >= building_conviction_floor and after_persistence >= building_persistence_floor:
                return before_state
            return "FLOW_UNCONFIRMED"
        if before_state == "FLOW_UNCONFIRMED":
            if after_conviction < (building_conviction_floor * 0.7) or after_persistence < (building_persistence_floor * 0.7):
                return "FLOW_OPPOSED"
            return before_state
    return before_state


def _flow_state_change_type(before_state: str, after_state: str) -> str:
    before = _text(before_state).upper() or "NONE"
    after = _text(after_state).upper() or "NONE"
    if before == after:
        return "UNCHANGED"
    return f"{before}_TO_{after}"


def _scope_match(row: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    payload = _mapping(row)
    candidate_payload = _mapping(candidate)
    current_state = _text(payload.get("flow_support_state_v1")).upper()
    apply_states = [_text(item).upper() for item in list(_mapping(candidate_payload.get("scope")).get("apply_states", []) or []) if _text(item)]
    return current_state in apply_states if current_state and apply_states else False


def _build_candidate_apply_sessions_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    candidate_objects: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key).upper(): _mapping(value) for key, value in dict(rows_by_symbol or {}).items()}
    candidates = {
        _text(candidate_id): _mapping(candidate)
        for candidate_id, candidate in dict(candidate_objects or {}).items()
        if _text(candidate_id)
    }
    primary_by_symbol = {
        _text(row.get("symbol") or symbol).upper() or _text(symbol).upper(): _text(row.get("bounded_calibration_candidate_primary_candidate_id_v1"))
        for symbol, row in rows.items()
    }

    sessions: dict[str, dict[str, Any]] = {}
    now = _now()
    for candidate_id, candidate in candidates.items():
        if not _shadow_required_candidate(candidate):
            continue
        symbol = _text(candidate.get("symbol")).upper()
        primary_candidate_id = _text(primary_by_symbol.get(symbol))
        session_state = "ACTIVE" if candidate_id == primary_candidate_id else "HOLD"
        hold_reason = "" if session_state == "ACTIVE" else "NON_PRIMARY_SCOPE_OVERLAP"
        sessions[candidate_id] = {
            "apply_session_id": _candidate_session_id(candidate),
            "candidate_id": candidate_id,
            "apply_mode": "SHADOW_ONLY",
            "session_state_v1": session_state,
            "session_hold_reason_v1": hold_reason,
            "symbol": symbol,
            "learning_key": _text(candidate.get("learning_key")),
            "scope": _mapping(candidate.get("scope")),
            "candidate_patch": {
                "current_value": _float(candidate.get("current_value"), 0.0),
                "proposed_value": _float(candidate.get("proposed_value"), 0.0),
                "delta": _float(candidate.get("delta"), 0.0),
            },
            "started_at": now.isoformat(timespec="seconds"),
            "scheduled_review_at": (now + timedelta(hours=48)).isoformat(timespec="seconds"),
        }
    return sessions


def _attach_shadow_fields_to_rows_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    candidate_objects: Mapping[str, Any] | None,
    apply_sessions: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(rows_by_symbol or {}).items()}
    candidates = {
        _text(candidate_id): _mapping(candidate)
        for candidate_id, candidate in dict(candidate_objects or {}).items()
        if _text(candidate_id)
    }
    sessions = {
        _text(candidate_id): _mapping(session)
        for candidate_id, session in dict(apply_sessions or {}).items()
        if _text(candidate_id)
    }

    for symbol, row in rows.items():
        primary_candidate_id = _text(row.get("bounded_calibration_candidate_primary_candidate_id_v1"))
        candidate = candidates.get(primary_candidate_id, {})
        session = sessions.get(primary_candidate_id, {})
        before_flow_state = _text(row.get("flow_support_state_v1")) or "NONE"
        before_structure_gate = _text(row.get("flow_structure_gate_v1")) or "NONE"
        before_conviction = round(_float(row.get("aggregate_conviction_v1"), 0.0), 4)
        before_persistence = round(_float(row.get("flow_persistence_v1"), 0.0), 4)

        conflict_flag = False
        conflict_reason = ""
        candidate_ids = [_text(item) for item in list(row.get("bounded_calibration_candidate_ids_v1") or []) if _text(item)]
        active_shadow_candidates = [
            candidates[candidate_id]
            for candidate_id in candidate_ids
            if candidate_id in candidates and _shadow_required_candidate(candidates[candidate_id])
        ]
        active_directions = {
            _text(candidate_payload.get("direction")).upper()
            for candidate_payload in active_shadow_candidates
            if _text(candidate_payload.get("direction")).upper() in {"RELAX", "TIGHTEN"}
        }
        if len(active_directions) > 1:
            conflict_flag = True
            conflict_reason = "CONFLICTING_SHADOW_REQUIRED_DIRECTIONS"

        session_state = _text(session.get("session_state_v1")) or "NOT_APPLICABLE"
        apply_mode = _text(session.get("apply_mode")) if session else "NONE"
        candidate_id = _text(session.get("candidate_id")) if session else ""
        scope_match = False
        block_reason = ""
        drift_guard_state = "NOT_APPLICABLE"
        after_flow_state = before_flow_state
        after_structure_gate = before_structure_gate
        after_conviction = before_conviction
        after_persistence = before_persistence

        if candidate_id and conflict_flag:
            session_state = "BLOCKED"
            block_reason = conflict_reason
        elif candidate_id and session_state == "ACTIVE":
            scope_match = _scope_match(row, candidate)
            drift_guard_state = _drift_guard_state(row, candidate)
            if not scope_match:
                session_state = "BLOCKED"
                block_reason = "OUTSIDE_APPLY_SCOPE"
            elif drift_guard_state != "CLEAR":
                session_state = "BLOCKED"
                block_reason = "DRIFT_GUARD_BLOCKED"
            else:
                after_conviction, after_persistence = _shadow_metrics_after(row, candidate)
                after_flow_state = _flow_state_after(row, candidate, after_conviction, after_persistence)
        elif primary_candidate_id:
            block_reason = "PRIMARY_CANDIDATE_NOT_SHADOW_REQUIRED"

        flow_change_type = _flow_state_change_type(before_flow_state, after_flow_state)
        row["bounded_apply_session_id_v1"] = _text(session.get("apply_session_id"))
        row["bounded_apply_candidate_id_v1"] = candidate_id
        row["bounded_apply_mode_v1"] = apply_mode or "NONE"
        row["bounded_apply_session_state_v1"] = session_state
        row["bounded_apply_scope_match_v1"] = bool(scope_match)
        row["flow_support_state_before_v1"] = before_flow_state
        row["flow_support_state_after_v1"] = after_flow_state
        row["flow_structure_gate_before_v1"] = before_structure_gate
        row["flow_structure_gate_after_v1"] = after_structure_gate
        row["aggregate_conviction_before_v1"] = before_conviction
        row["aggregate_conviction_after_v1"] = round(after_conviction, 4)
        row["flow_persistence_before_v1"] = before_persistence
        row["flow_persistence_after_v1"] = round(after_persistence, 4)
        row["flow_state_changed_v1"] = before_flow_state != after_flow_state
        row["flow_state_change_type_v1"] = flow_change_type
        row["conviction_delta_v1"] = round(after_conviction - before_conviction, 4)
        row["persistence_delta_v1"] = round(after_persistence - before_persistence, 4)
        row["candidate_effect_direction_v1"] = _text(candidate.get("direction")) or "NONE"
        row["bounded_apply_conflict_flag_v1"] = bool(conflict_flag)
        row["bounded_apply_conflict_reason_v1"] = conflict_reason
        row["bounded_apply_block_reason_v1"] = block_reason
        row["bounded_apply_drift_guard_state_v1"] = drift_guard_state
        row["bounded_apply_reason_summary_v1"] = (
            f"candidate_id={candidate_id or 'none'}; "
            f"session_state={session_state}; "
            f"scope_match={scope_match}; "
            f"drift_guard={drift_guard_state}; "
            f"block_reason={block_reason or 'none'}; "
            f"flow_change={flow_change_type}"
        )
        rows[str(symbol)] = row

    return rows


def attach_bounded_candidate_shadow_apply_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    f9_report = build_bounded_calibration_candidate_summary_v1(latest_signal_by_symbol)
    rows_by_symbol = _mapping(f9_report.get("rows_by_symbol"))
    candidate_objects = _mapping(f9_report.get("candidate_objects_v1"))
    sessions = _build_candidate_apply_sessions_v1(rows_by_symbol, candidate_objects)
    return _attach_shadow_fields_to_rows_v1(rows_by_symbol, candidate_objects, sessions)


def build_bounded_candidate_shadow_apply_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    f9_report = build_bounded_calibration_candidate_summary_v1(latest_signal_by_symbol)
    candidate_objects = _mapping(f9_report.get("candidate_objects_v1"))
    sessions = _build_candidate_apply_sessions_v1(_mapping(f9_report.get("rows_by_symbol")), candidate_objects)
    rows_by_symbol = _attach_shadow_fields_to_rows_v1(_mapping(f9_report.get("rows_by_symbol")), candidate_objects, sessions)

    session_state_counts: dict[str, int] = {}
    row_session_state_counts: dict[str, int] = {}
    row_flow_change_counts: dict[str, int] = {}
    active_row_count = 0
    changed_row_count = 0
    shadow_required_candidate_count = 0

    for candidate in candidate_objects.values():
        if _shadow_required_candidate(candidate):
            shadow_required_candidate_count += 1

    for session in sessions.values():
        state = _text(session.get("session_state_v1"))
        if state:
            session_state_counts[state] = int(session_state_counts.get(state, 0) or 0) + 1

    for row in rows_by_symbol.values():
        state = _text(row.get("bounded_apply_session_state_v1"))
        if state:
            row_session_state_counts[state] = int(row_session_state_counts.get(state, 0) or 0) + 1
        change_type = _text(row.get("flow_state_change_type_v1"))
        if change_type:
            row_flow_change_counts[change_type] = int(row_flow_change_counts.get(change_type, 0) or 0) + 1
        if state == "ACTIVE":
            active_row_count += 1
        if _bool(row.get("flow_state_changed_v1")):
            changed_row_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["bounded_candidate_shadow_apply_surface_available"]
            if rows_by_symbol
            else ["no_rows_for_bounded_candidate_shadow_apply"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "shadow_required_candidate_count": int(shadow_required_candidate_count),
        "apply_session_count": int(len(sessions)),
        "apply_session_state_count_summary": dict(session_state_counts),
        "row_apply_session_state_count_summary": dict(row_session_state_counts),
        "row_flow_state_change_count_summary": dict(row_flow_change_counts),
        "active_row_count": int(active_row_count),
        "changed_row_count": int(changed_row_count),
    }
    return {
        "contract_version": BOUNDED_CANDIDATE_SHADOW_APPLY_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
        "candidate_apply_sessions_v1": sessions,
        "candidate_objects_v1": candidate_objects,
    }


def render_bounded_candidate_shadow_apply_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    sessions = _mapping(payload.get("candidate_apply_sessions_v1"))
    lines = [
        "# Bounded Candidate Shadow Apply",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        f"- shadow_required_candidate_count: {summary.get('shadow_required_candidate_count', 0)}",
        f"- apply_session_count: {summary.get('apply_session_count', 0)}",
        f"- apply_session_state_count_summary: {json.dumps(summary.get('apply_session_state_count_summary', {}), ensure_ascii=False)}",
        f"- row_apply_session_state_count_summary: {json.dumps(summary.get('row_apply_session_state_count_summary', {}), ensure_ascii=False)}",
        f"- row_flow_state_change_count_summary: {json.dumps(summary.get('row_flow_state_change_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: candidate={row.get('bounded_apply_candidate_id_v1', '')}, "
            f"session_state={row.get('bounded_apply_session_state_v1', '')}, "
            f"mode={row.get('bounded_apply_mode_v1', '')}, "
            f"scope_match={row.get('bounded_apply_scope_match_v1', False)}, "
            f"before={row.get('flow_support_state_before_v1', '')}, "
            f"after={row.get('flow_support_state_after_v1', '')}, "
            f"change={row.get('flow_state_change_type_v1', '')}, "
            f"block_reason={row.get('bounded_apply_block_reason_v1', '')}"
        )
    lines.extend(["", "## Sessions"])
    for candidate_id, session in sessions.items():
        lines.append(
            f"- {candidate_id}: session_id={session.get('apply_session_id', '')}, "
            f"state={session.get('session_state_v1', '')}, "
            f"hold_reason={session.get('session_hold_reason_v1', '')}, "
            f"scope={json.dumps(_mapping(session.get('scope')), ensure_ascii=False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_candidate_shadow_apply_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_bounded_candidate_shadow_apply_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "bounded_candidate_shadow_apply_latest.json"
    markdown_path = output_dir / "bounded_candidate_shadow_apply_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_bounded_candidate_shadow_apply_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
