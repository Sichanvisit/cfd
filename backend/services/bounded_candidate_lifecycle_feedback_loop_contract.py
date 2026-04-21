from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.bounded_calibration_candidate_contract import (
    BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
    build_bounded_calibration_candidate_summary_v1,
)
from backend.services.bounded_candidate_evaluation_dashboard_contract import (
    BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_CONTRACT_VERSION,
    build_bounded_candidate_evaluation_dashboard_summary_v1,
)


BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_CONTRACT_VERSION = "bounded_candidate_lifecycle_feedback_loop_contract_v1"
BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_SUMMARY_VERSION = "bounded_candidate_lifecycle_feedback_loop_summary_v1"

LOOP_ACTION_ENUM_V1 = (
    "NO_ACTION",
    "KEEP_REVIEW",
    "KEEP_SHADOW",
    "PROMOTE_PATCH",
    "EXPIRE_CANDIDATE",
    "ROLLBACK_CANDIDATE",
)
LIFECYCLE_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "REVIEW_ONLY",
    "SHADOW_ACTIVE",
    "PROMOTION_READY",
    "EXPIRED",
    "ROLLED_BACK",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_bounded_candidate_lifecycle_feedback_loop_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F12 bounded promotion and rollback loop. Feeds F11 evaluation outcomes back into the F9 candidate "
            "lifecycle as bounded operational actions without mutating interpretation rules."
        ),
        "upstream_contract_versions_v1": [
            BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
            BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_CONTRACT_VERSION,
        ],
        "loop_action_enum_v1": list(LOOP_ACTION_ENUM_V1),
        "lifecycle_state_enum_v1": list(LIFECYCLE_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_candidate_feedback_candidate_id_v1",
            "bounded_candidate_feedback_loop_action_v1",
            "bounded_candidate_feedback_lifecycle_state_v1",
            "bounded_candidate_feedback_patch_ready_v1",
            "bounded_candidate_feedback_rollback_ready_v1",
            "bounded_candidate_feedback_source_outcome_v1",
            "bounded_candidate_feedback_source_assessment_v1",
            "bounded_candidate_feedback_reason_summary_v1",
        ],
        "control_rules_v1": [
            "F12 is an operational feedback layer and must not change dominant_side, dominance_gap, rejection split, or structure gate authority",
            "candidate outcomes are recycled into bounded lifecycle actions, not directly into live threshold mutation",
            "PROMOTE_PATCH is only emitted when F11 reports PROMOTE",
            "ROLLBACK_CANDIDATE is emitted when F11 reports ROLLBACK",
            "KEEP_SHADOW is emitted when a candidate is still in bounded shadow observation",
            "KEEP_REVIEW is emitted when the candidate remains review-only and is not yet shadow-ready",
            "EXPIRE_CANDIDATE is emitted when a candidate expires without promotion or is filtered out of the loop",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _candidate_feedback_entries_v1(
    candidate_objects: Mapping[str, Any] | None,
    evaluation_entries: Mapping[str, Any] | None,
    apply_sessions: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    candidates = {
        _text(candidate_id): _mapping(candidate)
        for candidate_id, candidate in dict(candidate_objects or {}).items()
        if _text(candidate_id)
    }
    evaluations = {
        _text(candidate_id): _mapping(entry)
        for candidate_id, entry in dict(evaluation_entries or {}).items()
        if _text(candidate_id)
    }
    sessions = {
        _text(candidate_id): _mapping(session)
        for candidate_id, session in dict(apply_sessions or {}).items()
        if _text(candidate_id)
    }

    feedback_entries: dict[str, dict[str, Any]] = {}
    for candidate_id, candidate in candidates.items():
        evaluation = evaluations.get(candidate_id, {})
        session = sessions.get(candidate_id, {})
        status = _text(candidate.get("status")).upper()
        source_outcome = _text(evaluation.get("evaluation_outcome")).upper()
        source_assessment = _text(evaluation.get("evaluation_assessment_v1")).upper()
        session_state = _text(session.get("session_state_v1")).upper()

        loop_action = "NO_ACTION"
        lifecycle_state = "NOT_APPLICABLE"

        if source_outcome == "PROMOTE":
            loop_action = "PROMOTE_PATCH"
            lifecycle_state = "PROMOTION_READY"
        elif source_outcome == "ROLLBACK":
            loop_action = "ROLLBACK_CANDIDATE"
            lifecycle_state = "ROLLED_BACK"
        elif source_outcome == "EXPIRE_WITHOUT_PROMOTION" or status == "FILTERED_OUT":
            loop_action = "EXPIRE_CANDIDATE"
            lifecycle_state = "EXPIRED"
        elif session_state in {"ACTIVE", "HOLD"}:
            loop_action = "KEEP_SHADOW"
            lifecycle_state = "SHADOW_ACTIVE"
        elif status == "REVIEW_ONLY":
            loop_action = "KEEP_REVIEW"
            lifecycle_state = "REVIEW_ONLY"
        elif status == "PROPOSED":
            loop_action = "KEEP_SHADOW"
            lifecycle_state = "SHADOW_ACTIVE"

        patch_ready = loop_action == "PROMOTE_PATCH"
        rollback_ready = loop_action == "ROLLBACK_CANDIDATE"
        reason = (
            f"candidate_id={candidate_id}; "
            f"status={status or 'UNKNOWN'}; "
            f"source_outcome={source_outcome or 'NONE'}; "
            f"source_assessment={source_assessment or 'NONE'}; "
            f"session_state={session_state or 'NONE'}; "
            f"loop_action={loop_action}; "
            f"lifecycle_state={lifecycle_state}; "
            f"patch_ready={patch_ready}; "
            f"rollback_ready={rollback_ready}"
        )

        feedback_entries[candidate_id] = {
            "candidate_id": candidate_id,
            "symbol": _text(candidate.get("symbol")),
            "learning_key": _text(candidate.get("learning_key")),
            "candidate_status_v1": status,
            "candidate_graduation_state_v1": _text(candidate.get("candidate_graduation_state_v1")).upper(),
            "source_outcome_v1": source_outcome or "NONE",
            "source_assessment_v1": source_assessment or "NONE",
            "loop_action_v1": loop_action,
            "lifecycle_state_v1": lifecycle_state,
            "patch_ready_v1": bool(patch_ready),
            "rollback_ready_v1": bool(rollback_ready),
            "promoted_patch_v1": (
                {
                    "symbol": _text(candidate.get("symbol")),
                    "learning_key": _text(candidate.get("learning_key")),
                    "current_value": _float(candidate.get("current_value"), 0.0),
                    "proposed_value": _float(candidate.get("proposed_value"), 0.0),
                    "delta": _float(candidate.get("delta"), 0.0),
                }
                if patch_ready
                else {}
            ),
            "rollback_patch_v1": (
                {
                    "symbol": _text(candidate.get("symbol")),
                    "learning_key": _text(candidate.get("learning_key")),
                    "rollback_to": _float(_mapping(candidate.get("rollback")).get("rollback_to"), 0.0),
                }
                if rollback_ready
                else {}
            ),
            "feedback_reason_summary_v1": reason,
        }
    return feedback_entries


def _attach_feedback_fields_to_rows_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    feedback_entries: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(rows_by_symbol or {}).items()}
    entries = {
        _text(candidate_id): _mapping(entry)
        for candidate_id, entry in dict(feedback_entries or {}).items()
        if _text(candidate_id)
    }
    for symbol, row in rows.items():
        candidate_id = _text(row.get("bounded_calibration_candidate_primary_candidate_id_v1"))
        entry = entries.get(candidate_id, {})
        row["bounded_candidate_feedback_candidate_id_v1"] = _text(entry.get("candidate_id"))
        row["bounded_candidate_feedback_loop_action_v1"] = _text(entry.get("loop_action_v1")) or "NO_ACTION"
        row["bounded_candidate_feedback_lifecycle_state_v1"] = _text(entry.get("lifecycle_state_v1")) or "NOT_APPLICABLE"
        row["bounded_candidate_feedback_patch_ready_v1"] = _bool(entry.get("patch_ready_v1"))
        row["bounded_candidate_feedback_rollback_ready_v1"] = _bool(entry.get("rollback_ready_v1"))
        row["bounded_candidate_feedback_source_outcome_v1"] = _text(entry.get("source_outcome_v1")) or "NONE"
        row["bounded_candidate_feedback_source_assessment_v1"] = _text(entry.get("source_assessment_v1")) or "NONE"
        row["bounded_candidate_feedback_reason_summary_v1"] = _text(entry.get("feedback_reason_summary_v1"))
        rows[str(symbol)] = row
    return rows


def attach_bounded_candidate_lifecycle_feedback_loop_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    f9_report = build_bounded_calibration_candidate_summary_v1(latest_signal_by_symbol)
    f11_report = build_bounded_candidate_evaluation_dashboard_summary_v1(latest_signal_by_symbol)
    feedback_entries = _candidate_feedback_entries_v1(
        _mapping(f9_report.get("candidate_objects_v1")),
        _mapping(f11_report.get("candidate_evaluation_entries_v1")),
        _mapping(f11_report.get("candidate_apply_sessions_v1")),
    )
    return _attach_feedback_fields_to_rows_v1(
        _mapping(f11_report.get("rows_by_symbol")),
        feedback_entries,
    )


def build_bounded_candidate_lifecycle_feedback_loop_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    f9_report = build_bounded_calibration_candidate_summary_v1(latest_signal_by_symbol)
    f11_report = build_bounded_candidate_evaluation_dashboard_summary_v1(latest_signal_by_symbol)
    feedback_entries = _candidate_feedback_entries_v1(
        _mapping(f9_report.get("candidate_objects_v1")),
        _mapping(f11_report.get("candidate_evaluation_entries_v1")),
        _mapping(f11_report.get("candidate_apply_sessions_v1")),
    )
    rows_by_symbol = _attach_feedback_fields_to_rows_v1(
        _mapping(f11_report.get("rows_by_symbol")),
        feedback_entries,
    )

    action_counts: dict[str, int] = {}
    lifecycle_counts: dict[str, int] = {}
    patch_ready_count = 0
    rollback_ready_count = 0
    for entry in feedback_entries.values():
        action = _text(entry.get("loop_action_v1"))
        lifecycle = _text(entry.get("lifecycle_state_v1"))
        if action:
            action_counts[action] = int(action_counts.get(action, 0) or 0) + 1
        if lifecycle:
            lifecycle_counts[lifecycle] = int(lifecycle_counts.get(lifecycle, 0) or 0) + 1
        if _bool(entry.get("patch_ready_v1")):
            patch_ready_count += 1
        if _bool(entry.get("rollback_ready_v1")):
            rollback_ready_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["bounded_candidate_lifecycle_feedback_loop_available"]
            if rows_by_symbol
            else ["no_rows_for_bounded_candidate_lifecycle_feedback_loop"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "candidate_feedback_count": int(len(feedback_entries)),
        "loop_action_count_summary": dict(action_counts),
        "lifecycle_state_count_summary": dict(lifecycle_counts),
        "patch_ready_count": int(patch_ready_count),
        "rollback_ready_count": int(rollback_ready_count),
    }
    return {
        "contract_version": BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
        "candidate_feedback_entries_v1": feedback_entries,
    }


def render_bounded_candidate_lifecycle_feedback_loop_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    feedback_entries = _mapping(payload.get("candidate_feedback_entries_v1"))
    lines = [
        "# Bounded Candidate Lifecycle Feedback Loop",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- candidate_feedback_count: {summary.get('candidate_feedback_count', 0)}",
        f"- loop_action_count_summary: {json.dumps(summary.get('loop_action_count_summary', {}), ensure_ascii=False)}",
        f"- lifecycle_state_count_summary: {json.dumps(summary.get('lifecycle_state_count_summary', {}), ensure_ascii=False)}",
        f"- patch_ready_count: {summary.get('patch_ready_count', 0)}",
        f"- rollback_ready_count: {summary.get('rollback_ready_count', 0)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: candidate={row.get('bounded_candidate_feedback_candidate_id_v1', '')}, "
            f"action={row.get('bounded_candidate_feedback_loop_action_v1', '')}, "
            f"lifecycle={row.get('bounded_candidate_feedback_lifecycle_state_v1', '')}, "
            f"patch_ready={row.get('bounded_candidate_feedback_patch_ready_v1', False)}, "
            f"rollback_ready={row.get('bounded_candidate_feedback_rollback_ready_v1', False)}"
        )
    lines.extend(["", "## Feedback Entries"])
    for candidate_id, entry in feedback_entries.items():
        lines.append(
            f"- {candidate_id}: action={entry.get('loop_action_v1', '')}, "
            f"lifecycle={entry.get('lifecycle_state_v1', '')}, "
            f"source_outcome={entry.get('source_outcome_v1', '')}, "
            f"source_assessment={entry.get('source_assessment_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_bounded_candidate_lifecycle_feedback_loop_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "bounded_candidate_lifecycle_feedback_loop_latest.json"
    markdown_path = output_dir / "bounded_candidate_lifecycle_feedback_loop_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_bounded_candidate_lifecycle_feedback_loop_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
