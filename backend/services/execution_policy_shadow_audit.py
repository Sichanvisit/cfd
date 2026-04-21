from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.state_slot_position_lifecycle_policy import (
    attach_state_slot_position_lifecycle_policy_fields_v1,
)


EXECUTION_POLICY_SHADOW_AUDIT_CONTRACT_VERSION = "execution_policy_shadow_audit_contract_v1"
EXECUTION_POLICY_SHADOW_AUDIT_SUMMARY_VERSION = "execution_policy_shadow_audit_summary_v1"

LIFECYCLE_POLICY_ALIGNMENT_ENUM_V1 = (
    "ALIGNED",
    "ENTRY_TOO_AGGRESSIVE",
    "REDUCE_TOO_EARLY",
    "HOLD_TOO_WEAK",
    "REVIEW_PENDING",
    "NOT_APPLICABLE",
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
    return bool(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_execution_policy_shadow_audit_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": EXECUTION_POLICY_SHADOW_AUDIT_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only shadow audit for lifecycle policy. Checks whether translated entry/hold/reduce/exit posture "
            "is coherent with state slot stage, texture, ambiguity, and compatibility before any canary rollout."
        ),
        "lifecycle_policy_alignment_enum_v1": list(LIFECYCLE_POLICY_ALIGNMENT_ENUM_V1),
        "row_level_fields_v1": [
            "execution_policy_shadow_audit_profile_v1",
            "lifecycle_policy_alignment_state_v1",
            "entry_delay_conflict_flag_v1",
            "hold_support_alignment_v1",
            "reduce_exit_pressure_alignment_v1",
            "execution_policy_shadow_error_type_v1",
            "execution_policy_shadow_reason_summary_v1",
        ],
        "control_rules_v1": [
            "shadow audit is diagnostic only",
            "review_pending policy rows remain review_pending instead of being forced into aligned or failed",
            "extension stage should not produce active entry",
            "clean acceptance should not produce weak hold without explicit ambiguity or pending state",
            "initiation should not produce strong reduce without high ambiguity",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("state_slot_position_lifecycle_policy_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_state_slot_position_lifecycle_policy_fields_v1({symbol: row}).get(symbol, row))


def build_execution_policy_shadow_audit_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_policy(row or {})
    slot_core = _text(payload.get("common_state_slot_core_v1")).upper()
    policy_state = _text(payload.get("state_slot_lifecycle_policy_state_v1")).upper()
    stage = _text(payload.get("common_state_continuation_stage_v1")).upper()
    texture = _text(payload.get("common_state_texture_slot_v1")).upper()
    ambiguity = _text(payload.get("common_state_ambiguity_level_v1")).upper()
    entry_policy = _text(payload.get("entry_policy_v1")).upper()
    hold_policy = _text(payload.get("hold_policy_v1")).upper()
    reduce_policy = _text(payload.get("reduce_policy_v1")).upper()
    exit_policy = _text(payload.get("exit_policy_v1")).upper()

    if not slot_core:
        profile = {
            "contract_version": EXECUTION_POLICY_SHADOW_AUDIT_CONTRACT_VERSION,
            "alignment_state_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "execution_policy_shadow_audit_profile_v1": profile,
            "lifecycle_policy_alignment_state_v1": "NOT_APPLICABLE",
            "entry_delay_conflict_flag_v1": False,
            "hold_support_alignment_v1": "NOT_APPLICABLE",
            "reduce_exit_pressure_alignment_v1": "NOT_APPLICABLE",
            "execution_policy_shadow_error_type_v1": "",
            "execution_policy_shadow_reason_summary_v1": "slot_missing",
        }

    if policy_state == "REVIEW_PENDING":
        profile = {
            "contract_version": EXECUTION_POLICY_SHADOW_AUDIT_CONTRACT_VERSION,
            "alignment_state_v1": "REVIEW_PENDING",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "execution_policy_shadow_audit_profile_v1": profile,
            "lifecycle_policy_alignment_state_v1": "REVIEW_PENDING",
            "entry_delay_conflict_flag_v1": False,
            "hold_support_alignment_v1": "REVIEW_PENDING",
            "reduce_exit_pressure_alignment_v1": "REVIEW_PENDING",
            "execution_policy_shadow_error_type_v1": "REVIEW_PENDING",
            "execution_policy_shadow_reason_summary_v1": "policy_review_pending",
        }

    entry_conflict = stage == "EXTENSION" and entry_policy == "ACTIVE_ENTRY"
    reduce_too_early = (
        stage == "INITIATION"
        and ambiguity != "HIGH"
        and reduce_policy in {"REDUCE_FAVOR", "REDUCE_STRONG"}
    )
    hold_too_weak = (
        stage == "ACCEPTANCE"
        and texture == "CLEAN"
        and ambiguity == "LOW"
        and hold_policy in {"NO_HOLD_EDGE", "LIGHT_HOLD"}
    )

    if entry_conflict:
        alignment = "ENTRY_TOO_AGGRESSIVE"
        error_type = "ENTRY_TOO_AGGRESSIVE"
    elif reduce_too_early:
        alignment = "REDUCE_TOO_EARLY"
        error_type = "REDUCE_TOO_EARLY"
    elif hold_too_weak:
        alignment = "HOLD_TOO_WEAK"
        error_type = "HOLD_TOO_WEAK"
    else:
        alignment = "ALIGNED"
        error_type = "ALIGNED"

    hold_alignment = "SUPPORTED" if alignment != "HOLD_TOO_WEAK" else "WEAK"
    reduce_alignment = "SUPPORTED" if alignment != "REDUCE_TOO_EARLY" else "TOO_EARLY"
    reason = (
        f"slot={slot_core}; stage={stage}; texture={texture}; ambiguity={ambiguity}; "
        f"entry={entry_policy}; hold={hold_policy}; reduce={reduce_policy}; exit={exit_policy}; "
        f"alignment={alignment}"
    )
    profile = {
        "contract_version": EXECUTION_POLICY_SHADOW_AUDIT_CONTRACT_VERSION,
        "alignment_state_v1": alignment,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "execution_policy_shadow_audit_profile_v1": profile,
        "lifecycle_policy_alignment_state_v1": alignment,
        "entry_delay_conflict_flag_v1": bool(entry_conflict),
        "hold_support_alignment_v1": hold_alignment,
        "reduce_exit_pressure_alignment_v1": reduce_alignment,
        "execution_policy_shadow_error_type_v1": error_type,
        "execution_policy_shadow_reason_summary_v1": reason,
    }


def attach_execution_policy_shadow_audit_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_policy(raw)
        row.update(build_execution_policy_shadow_audit_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_execution_policy_shadow_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_execution_policy_shadow_audit_fields_v1(latest_signal_by_symbol)
    alignment_counts = Counter()
    error_counts = Counter()
    entry_conflicts = 0
    hold_supported = 0
    reduce_supported = 0
    symbol_count = len(rows_by_symbol)
    review_pending = 0
    aligned = 0
    for row in rows_by_symbol.values():
        alignment = _text(row.get("lifecycle_policy_alignment_state_v1"))
        alignment_counts.update([alignment])
        error_counts.update([_text(row.get("execution_policy_shadow_error_type_v1"))])
        if _bool(row.get("entry_delay_conflict_flag_v1")):
            entry_conflicts += 1
        if _text(row.get("hold_support_alignment_v1")) == "SUPPORTED":
            hold_supported += 1
        if _text(row.get("reduce_exit_pressure_alignment_v1")) == "SUPPORTED":
            reduce_supported += 1
        if alignment == "REVIEW_PENDING":
            review_pending += 1
        if alignment == "ALIGNED":
            aligned += 1
    effective_count = symbol_count - review_pending
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["execution_policy_shadow_audit_available"] if symbol_count else ["no_lifecycle_policy_rows"]
        ),
        "symbol_count": int(symbol_count),
        "effective_symbol_count": int(max(effective_count, 0)),
        "alignment_rate": round(aligned / effective_count, 4) if effective_count > 0 else None,
        "entry_conflict_rate": round(entry_conflicts / symbol_count, 4) if symbol_count else None,
        "hold_support_rate": round(hold_supported / effective_count, 4) if effective_count > 0 else None,
        "reduce_pressure_support_rate": (
            round(reduce_supported / effective_count, 4) if effective_count > 0 else None
        ),
        "lifecycle_policy_alignment_count_summary": dict(alignment_counts),
        "execution_policy_shadow_error_type_count_summary": dict(error_counts),
    }
    return {
        "contract_version": EXECUTION_POLICY_SHADOW_AUDIT_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_execution_policy_shadow_audit_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Execution Policy Shadow Audit v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- alignment_rate: `{summary.get('alignment_rate')}`",
        f"- entry_conflict_rate: `{summary.get('entry_conflict_rate')}`",
        "",
        "## Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: alignment={row.get('lifecycle_policy_alignment_state_v1', '')} | "
            f"error={row.get('execution_policy_shadow_error_type_v1', '')} | "
            f"hold={row.get('hold_support_alignment_v1', '')} | reduce={row.get('reduce_exit_pressure_alignment_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_execution_policy_shadow_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_execution_policy_shadow_audit_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "execution_policy_shadow_audit_latest.json"
    md_path = output_dir / "execution_policy_shadow_audit_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_execution_policy_shadow_audit_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
