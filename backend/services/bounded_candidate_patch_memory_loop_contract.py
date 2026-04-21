from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.bounded_candidate_lifecycle_feedback_loop_contract import (
    BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_CONTRACT_VERSION,
    build_bounded_candidate_lifecycle_feedback_loop_summary_v1,
)


BOUNDED_CANDIDATE_PATCH_MEMORY_LOOP_CONTRACT_VERSION = "bounded_candidate_patch_memory_loop_contract_v1"
BOUNDED_CANDIDATE_PATCH_MEMORY_LOOP_SUMMARY_VERSION = "bounded_candidate_patch_memory_loop_summary_v1"

PATCH_CATALOG_STATE_ENUM_V1 = (
    "NONE",
    "PATCH_CATALOG_READY",
)
ROLLBACK_MEMORY_STATE_ENUM_V1 = (
    "NONE",
    "RECORDED",
)
PATCH_ENTRY_STATUS_ENUM_V1 = (
    "READY_FOR_REVIEW",
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


def load_bounded_candidate_rollback_memory_by_symbol_v1(
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    json_path = Path(shadow_auto_dir or _default_shadow_auto_dir()) / "bounded_candidate_patch_memory_loop_latest.json"
    try:
        if not json_path.exists():
            return {}
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        memory = _mapping(payload.get("rollback_memory_by_symbol_v1"))
        return {str(symbol).upper(): _mapping(entry) for symbol, entry in memory.items()}
    except Exception:
        return {}


def attach_recent_rollback_memory_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(latest_signal_by_symbol or {}).items()}
    memory_by_symbol = load_bounded_candidate_rollback_memory_by_symbol_v1(shadow_auto_dir=shadow_auto_dir)
    for symbol, row in rows.items():
        symbol_name = _text(row.get("symbol") or symbol).upper()
        memory = _mapping(memory_by_symbol.get(symbol_name))
        row["bounded_calibration_candidate_recent_rollback_keys_v1"] = [
            _text(item)
            for item in list(memory.get("recent_rollback_keys_v1") or [])
            if _text(item)
        ]
        rows[str(symbol)] = row
    return rows


def build_bounded_candidate_patch_memory_loop_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_CANDIDATE_PATCH_MEMORY_LOOP_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F13 patch catalog and rollback memory loop. Converts F12 lifecycle feedback into a bounded patch catalog "
            "for promoted candidates and rollback memory for rolled-back candidates."
        ),
        "upstream_contract_versions_v1": [
            BOUNDED_CANDIDATE_LIFECYCLE_FEEDBACK_LOOP_CONTRACT_VERSION,
        ],
        "patch_catalog_state_enum_v1": list(PATCH_CATALOG_STATE_ENUM_V1),
        "rollback_memory_state_enum_v1": list(ROLLBACK_MEMORY_STATE_ENUM_V1),
        "patch_entry_status_enum_v1": list(PATCH_ENTRY_STATUS_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_candidate_followup_candidate_id_v1",
            "bounded_candidate_followup_action_v1",
            "bounded_candidate_followup_patch_catalog_state_v1",
            "bounded_candidate_followup_rollback_memory_state_v1",
            "bounded_candidate_followup_recent_rollback_keys_v1",
            "bounded_candidate_followup_reason_summary_v1",
        ],
        "control_rules_v1": [
            "F13 is a follow-up operational layer and must not mutate live interpretation or thresholds directly",
            "PROMOTE_PATCH creates a review-ready patch catalog entry only",
            "ROLLBACK_CANDIDATE records rollback memory for later suppression and audit only",
            "rollback memory is symbol-scoped by default and stores recent learning keys plus rollback_to anchors",
            "KEEP_REVIEW and KEEP_SHADOW do not create patch entries or rollback memory by themselves",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _patch_catalog_entries_v1(feedback_entries: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for candidate_id, raw in dict(feedback_entries or {}).items():
        entry = _mapping(raw)
        if _text(entry.get("loop_action_v1")).upper() != "PROMOTE_PATCH":
            continue
        patch = _mapping(entry.get("promoted_patch_v1"))
        catalog[_text(candidate_id)] = {
            "candidate_id": _text(candidate_id),
            "symbol": _text(entry.get("symbol")),
            "learning_key": _text(entry.get("learning_key")),
            "status_v1": "READY_FOR_REVIEW",
            "current_value": _float(patch.get("current_value"), 0.0),
            "proposed_value": _float(patch.get("proposed_value"), 0.0),
            "delta": _float(patch.get("delta"), 0.0),
            "source_outcome_v1": _text(entry.get("source_outcome_v1")) or "NONE",
            "source_assessment_v1": _text(entry.get("source_assessment_v1")) or "NONE",
            "lifecycle_state_v1": _text(entry.get("lifecycle_state_v1")) or "NOT_APPLICABLE",
            "generated_at_v1": _now_iso(),
        }
    return catalog


def _rollback_memory_by_symbol_v1(feedback_entries: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    memory: dict[str, dict[str, Any]] = {}
    for candidate_id, raw in dict(feedback_entries or {}).items():
        entry = _mapping(raw)
        if _text(entry.get("loop_action_v1")).upper() != "ROLLBACK_CANDIDATE":
            continue
        symbol = _text(entry.get("symbol")).upper()
        learning_key = _text(entry.get("learning_key"))
        rollback_patch = _mapping(entry.get("rollback_patch_v1"))
        if not symbol or not learning_key:
            continue
        bucket = memory.setdefault(
            symbol,
            {
                "symbol": symbol,
                "recent_rollback_keys_v1": [],
                "rollback_candidate_ids_v1": [],
                "rollback_to_by_key_v1": {},
                "learning_key_memory_v1": {},
                "recorded_at_v1": _now_iso(),
            },
        )
        if learning_key not in bucket["recent_rollback_keys_v1"]:
            bucket["recent_rollback_keys_v1"].append(learning_key)
        if _text(candidate_id) and _text(candidate_id) not in bucket["rollback_candidate_ids_v1"]:
            bucket["rollback_candidate_ids_v1"].append(_text(candidate_id))
        rollback_to = _float(rollback_patch.get("rollback_to"), 0.0)
        bucket["rollback_to_by_key_v1"][learning_key] = rollback_to
        bucket["learning_key_memory_v1"][learning_key] = {
            "candidate_id": _text(candidate_id),
            "rollback_to": rollback_to,
            "source_outcome_v1": _text(entry.get("source_outcome_v1")) or "NONE",
            "source_assessment_v1": _text(entry.get("source_assessment_v1")) or "NONE",
            "recorded_at_v1": _now_iso(),
        }
    return memory


def _attach_followup_fields_to_rows_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    feedback_entries: Mapping[str, Any] | None,
    patch_catalog: Mapping[str, Any] | None,
    rollback_memory_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(rows_by_symbol or {}).items()}
    entries = {_text(candidate_id): _mapping(entry) for candidate_id, entry in dict(feedback_entries or {}).items()}
    catalog = {_text(candidate_id): _mapping(entry) for candidate_id, entry in dict(patch_catalog or {}).items()}
    rollback_memory = {
        _text(symbol).upper(): _mapping(entry) for symbol, entry in dict(rollback_memory_by_symbol or {}).items()
    }

    for symbol, row in rows.items():
        symbol_name = _text(row.get("symbol") or symbol).upper()
        candidate_id = _text(row.get("bounded_candidate_feedback_candidate_id_v1")) or _text(
            row.get("bounded_calibration_candidate_primary_candidate_id_v1")
        )
        feedback_entry = entries.get(candidate_id, {})
        rollback_memory_entry = rollback_memory.get(symbol_name, {})
        patch_state = "PATCH_CATALOG_READY" if candidate_id in catalog else "NONE"
        learning_key = _text(feedback_entry.get("learning_key"))
        rollback_keys = [
            _text(item)
            for item in list(rollback_memory_entry.get("recent_rollback_keys_v1") or [])
            if _text(item)
        ]
        rollback_state = "RECORDED" if learning_key and learning_key in rollback_keys else "NONE"
        action = _text(feedback_entry.get("loop_action_v1")) or "NO_ACTION"
        reason = (
            f"candidate_id={candidate_id or 'none'}; "
            f"action={action}; "
            f"patch_catalog_state={patch_state}; "
            f"rollback_memory_state={rollback_state}; "
            f"recent_rollback_keys={','.join(rollback_keys) or 'none'}"
        )

        row["bounded_candidate_followup_candidate_id_v1"] = candidate_id
        row["bounded_candidate_followup_action_v1"] = action
        row["bounded_candidate_followup_patch_catalog_state_v1"] = patch_state
        row["bounded_candidate_followup_rollback_memory_state_v1"] = rollback_state
        row["bounded_candidate_followup_recent_rollback_keys_v1"] = rollback_keys
        row["bounded_candidate_followup_reason_summary_v1"] = reason
        rows[str(symbol)] = row
    return rows


def attach_bounded_candidate_patch_memory_loop_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    f12_report = build_bounded_candidate_lifecycle_feedback_loop_summary_v1(latest_signal_by_symbol)
    feedback_entries = _mapping(f12_report.get("candidate_feedback_entries_v1"))
    patch_catalog = _patch_catalog_entries_v1(feedback_entries)
    rollback_memory_by_symbol = _rollback_memory_by_symbol_v1(feedback_entries)
    return _attach_followup_fields_to_rows_v1(
        _mapping(f12_report.get("rows_by_symbol")),
        feedback_entries,
        patch_catalog,
        rollback_memory_by_symbol,
    )


def build_bounded_candidate_patch_memory_loop_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    f12_report = build_bounded_candidate_lifecycle_feedback_loop_summary_v1(latest_signal_by_symbol)
    feedback_entries = _mapping(f12_report.get("candidate_feedback_entries_v1"))
    patch_catalog = _patch_catalog_entries_v1(feedback_entries)
    rollback_memory_by_symbol = _rollback_memory_by_symbol_v1(feedback_entries)
    rows_by_symbol = _attach_followup_fields_to_rows_v1(
        _mapping(f12_report.get("rows_by_symbol")),
        feedback_entries,
        patch_catalog,
        rollback_memory_by_symbol,
    )

    patch_symbol_counts: dict[str, int] = {}
    rollback_symbol_counts: dict[str, int] = {}
    rollback_key_counts: dict[str, int] = {}
    for entry in patch_catalog.values():
        symbol = _text(entry.get("symbol")).upper()
        if symbol:
            patch_symbol_counts[symbol] = int(patch_symbol_counts.get(symbol, 0) or 0) + 1
    for symbol, entry in rollback_memory_by_symbol.items():
        keys = [_text(item) for item in list(_mapping(entry).get("recent_rollback_keys_v1") or []) if _text(item)]
        rollback_symbol_counts[_text(symbol)] = len(keys)
        for key in keys:
            rollback_key_counts[key] = int(rollback_key_counts.get(key, 0) or 0) + 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["bounded_candidate_patch_memory_loop_available"]
            if rows_by_symbol
            else ["no_rows_for_bounded_candidate_patch_memory_loop"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "patch_catalog_count": int(len(patch_catalog)),
        "rollback_memory_symbol_count": int(len(rollback_memory_by_symbol)),
        "patch_catalog_symbol_count_summary": dict(patch_symbol_counts),
        "rollback_memory_symbol_count_summary": dict(rollback_symbol_counts),
        "rollback_memory_key_count_summary": dict(rollback_key_counts),
    }
    return {
        "contract_version": BOUNDED_CANDIDATE_PATCH_MEMORY_LOOP_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
        "patch_catalog_v1": patch_catalog,
        "rollback_memory_by_symbol_v1": rollback_memory_by_symbol,
        "candidate_feedback_entries_v1": feedback_entries,
    }


def render_bounded_candidate_patch_memory_loop_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    patch_catalog = _mapping(payload.get("patch_catalog_v1"))
    rollback_memory = _mapping(payload.get("rollback_memory_by_symbol_v1"))
    lines = [
        "# Bounded Candidate Patch Catalog / Rollback Memory Loop",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- patch_catalog_count: {summary.get('patch_catalog_count', 0)}",
        f"- rollback_memory_symbol_count: {summary.get('rollback_memory_symbol_count', 0)}",
        f"- patch_catalog_symbol_count_summary: {json.dumps(summary.get('patch_catalog_symbol_count_summary', {}), ensure_ascii=False)}",
        f"- rollback_memory_symbol_count_summary: {json.dumps(summary.get('rollback_memory_symbol_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: candidate={row.get('bounded_candidate_followup_candidate_id_v1', '')}, "
            f"action={row.get('bounded_candidate_followup_action_v1', '')}, "
            f"patch_catalog_state={row.get('bounded_candidate_followup_patch_catalog_state_v1', '')}, "
            f"rollback_memory_state={row.get('bounded_candidate_followup_rollback_memory_state_v1', '')}"
        )
    lines.extend(["", "## Patch Catalog"])
    for candidate_id, entry in patch_catalog.items():
        lines.append(
            f"- {candidate_id}: symbol={entry.get('symbol', '')}, "
            f"learning_key={entry.get('learning_key', '')}, "
            f"status={entry.get('status_v1', '')}, "
            f"proposed={entry.get('proposed_value', 0.0)}, "
            f"delta={entry.get('delta', 0.0)}"
        )
    lines.extend(["", "## Rollback Memory"])
    for symbol, entry in rollback_memory.items():
        lines.append(
            f"- {symbol}: recent_rollback_keys={json.dumps(entry.get('recent_rollback_keys_v1', []), ensure_ascii=False)}, "
            f"rollback_candidate_ids={json.dumps(entry.get('rollback_candidate_ids_v1', []), ensure_ascii=False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_candidate_patch_memory_loop_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_bounded_candidate_patch_memory_loop_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "bounded_candidate_patch_memory_loop_latest.json"
    markdown_path = output_dir / "bounded_candidate_patch_memory_loop_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_bounded_candidate_patch_memory_loop_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
