from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.bounded_lifecycle_canary import (
    attach_bounded_lifecycle_canary_fields_v1,
)
from backend.services.execution_policy_shadow_audit import (
    attach_execution_policy_shadow_audit_fields_v1,
)
from backend.services.state_slot_execution_interface_bridge import (
    attach_state_slot_execution_interface_bridge_fields_v1,
)
from backend.services.state_slot_position_lifecycle_policy import (
    attach_state_slot_position_lifecycle_policy_fields_v1,
)
from backend.services.symbol_specific_state_strength_calibration import (
    attach_symbol_specific_state_strength_calibration_fields_v1,
)
from backend.services.xau_readonly_surface_contract import (
    attach_xau_readonly_surface_fields_v1,
)


XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION = "xau_refined_gate_timebox_audit_contract_v1"
XAU_REFINED_GATE_TIMEBOX_AUDIT_SUMMARY_VERSION = "xau_refined_gate_timebox_audit_summary_v1"

XAU_GATE_TIMEBOX_AUDIT_STATE_ENUM_V1 = ("READY", "HOLD", "NOT_APPLICABLE")
XAU_GATE_FAILURE_STAGE_ENUM_V1 = (
    "NONE",
    "ALIGNMENT",
    "PILOT_MATCH",
    "AMBIGUITY",
    "TEXTURE",
    "ENTRY_POLICY",
    "HOLD_POLICY",
    "CANARY_SCOPE",
    "NOT_APPLICABLE",
)
XAU_GATE_SAVED_EFFECTIVE_STATE_ENUM_V1 = (
    "CONSISTENT",
    "PERSISTED_FIELDS_MISSING",
    "PERSISTED_OUTDATED",
    "NOT_APPLICABLE",
)

_PERSISTED_COMPARE_FIELDS = (
    "lifecycle_policy_alignment_state_v1",
    "lifecycle_canary_candidate_state_v1",
    "xau_lifecycle_canary_risk_gate_v1",
    "xau_lifecycle_canary_scope_detail_v1",
)
_DOWNSTREAM_STRIP_PREFIXES = (
    "xau_readonly_surface_profile_v1",
    "xau_decomposition_validation_profile_v1",
    "state_slot_execution_interface_bridge_profile_v1",
    "state_slot_position_lifecycle_policy_profile_v1",
    "execution_policy_shadow_audit_profile_v1",
    "bounded_lifecycle_canary_profile_v1",
)
_DOWNSTREAM_STRIP_FIELDS = {
    "xau_polarity_slot_v1",
    "xau_intent_slot_v1",
    "xau_continuation_stage_v1",
    "xau_rejection_type_v1",
    "xau_texture_slot_v1",
    "xau_location_context_v1",
    "xau_tempo_profile_v1",
    "xau_ambiguity_level_v1",
    "xau_state_slot_core_v1",
    "xau_state_slot_modifier_bundle_v1",
    "xau_pilot_window_match_v1",
    "xau_surface_reason_summary_v1",
    "xau_slot_alignment_state_v1",
    "xau_should_have_done_candidate_v1",
    "xau_over_veto_flag_v1",
    "xau_under_veto_flag_v1",
    "xau_decomposition_error_type_v1",
    "xau_dominance_validation_reason_summary_v1",
    "state_slot_bridge_state_v1",
    "bridge_source_slot_v1",
    "entry_bias_v1",
    "hold_bias_v1",
    "add_bias_v1",
    "reduce_bias_v1",
    "exit_bias_v1",
    "state_slot_execution_bridge_reason_summary_v1",
    "state_slot_lifecycle_policy_state_v1",
    "state_slot_execution_policy_source_v1",
    "entry_policy_v1",
    "hold_policy_v1",
    "add_policy_v1",
    "reduce_policy_v1",
    "exit_policy_v1",
    "state_slot_lifecycle_policy_reason_summary_v1",
    "lifecycle_policy_alignment_state_v1",
    "entry_delay_conflict_flag_v1",
    "hold_support_alignment_v1",
    "reduce_exit_pressure_alignment_v1",
    "execution_policy_shadow_error_type_v1",
    "execution_policy_shadow_reason_summary_v1",
    "lifecycle_canary_candidate_state_v1",
    "lifecycle_canary_scope_v1",
    "lifecycle_canary_policy_slice_v1",
    "lifecycle_canary_eligibility_v1",
    "xau_lifecycle_canary_risk_gate_v1",
    "xau_lifecycle_canary_scope_detail_v1",
    "lifecycle_canary_reason_summary_v1",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_xau_refined_gate_timebox_audit_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Timebox-style diagnostic audit for the current XAU refined lifecycle gate. Compares persisted "
            "runtime row fields with an effective recomputation chain so we can separate stale payload gaps "
            "from the actual gate failure driver."
        ),
        "xau_gate_timebox_audit_state_enum_v1": list(XAU_GATE_TIMEBOX_AUDIT_STATE_ENUM_V1),
        "xau_gate_failure_stage_enum_v1": list(XAU_GATE_FAILURE_STAGE_ENUM_V1),
        "xau_gate_saved_effective_state_enum_v1": list(XAU_GATE_SAVED_EFFECTIVE_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "xau_refined_gate_timebox_audit_profile_v1",
            "xau_gate_timebox_audit_state_v1",
            "xau_gate_failure_stage_v1",
            "xau_gate_failure_primary_driver_v1",
            "xau_gate_saved_vs_effective_state_v1",
            "xau_gate_persisted_alignment_state_v1",
            "xau_gate_effective_alignment_state_v1",
            "xau_gate_persisted_candidate_state_v1",
            "xau_gate_effective_candidate_state_v1",
            "xau_gate_persisted_risk_gate_v1",
            "xau_gate_effective_risk_gate_v1",
            "xau_gate_effective_scope_detail_v1",
            "xau_gate_effective_flow_support_state_v1",
            "xau_gate_effective_aggregate_conviction_v1",
            "xau_gate_effective_flow_persistence_v1",
            "xau_gate_persisted_field_gap_v1",
            "xau_gate_timebox_reason_summary_v1",
        ],
        "control_rules_v1": [
            "audit is diagnostic-only and cannot change execution or state25",
            "persisted runtime detail and effective recomputation must be compared side by side",
            "effective failure driver is determined from alignment then refined gate risk order",
            "pilot mismatch should remain distinguishable from ambiguity or texture failure",
            "missing persisted fields should not be mistaken for a true lifecycle gate failure",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _strip_downstream_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    for prefix in _DOWNSTREAM_STRIP_PREFIXES:
        row.pop(prefix, None)
    for field in _DOWNSTREAM_STRIP_FIELDS:
        row.pop(field, None)
    return row


def recompute_xau_effective_chain_row_v1(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    row = _strip_downstream_fields(payload)
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    row = dict(attach_symbol_specific_state_strength_calibration_fields_v1({symbol: row}).get(symbol, row))
    row = dict(attach_xau_readonly_surface_fields_v1({symbol: row}).get(symbol, row))
    row = dict(attach_state_slot_execution_interface_bridge_fields_v1({symbol: row}).get(symbol, row))
    row = dict(attach_state_slot_position_lifecycle_policy_fields_v1({symbol: row}).get(symbol, row))
    row = dict(attach_execution_policy_shadow_audit_fields_v1({symbol: row}).get(symbol, row))
    row = dict(attach_bounded_lifecycle_canary_fields_v1({symbol: row}).get(symbol, row))
    return row


def _saved_vs_effective_state(
    persisted_row: Mapping[str, Any],
    effective_row: Mapping[str, Any],
) -> tuple[str, list[str]]:
    symbol = _text(persisted_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        return "NOT_APPLICABLE", []
    missing_fields = [field for field in _PERSISTED_COMPARE_FIELDS if not _text(persisted_row.get(field))]
    if missing_fields:
        return "PERSISTED_FIELDS_MISSING", missing_fields
    for field in _PERSISTED_COMPARE_FIELDS:
        if _text(persisted_row.get(field)) != _text(effective_row.get(field)):
            return "PERSISTED_OUTDATED", []
    return "CONSISTENT", []


def _failure_stage(effective_row: Mapping[str, Any]) -> tuple[str, str]:
    symbol = _text(effective_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        return "NOT_APPLICABLE", "symbol_not_xau"

    candidate_state = _text(effective_row.get("lifecycle_canary_candidate_state_v1")).upper()
    alignment = _text(effective_row.get("lifecycle_policy_alignment_state_v1")).upper()
    risk_gate = _text(effective_row.get("xau_lifecycle_canary_risk_gate_v1")).upper()
    eligibility = _text(effective_row.get("lifecycle_canary_eligibility_v1")).lower()

    if candidate_state == "BOUNDED_READY":
        return "NONE", "ready"
    if alignment and alignment != "ALIGNED":
        return "ALIGNMENT", alignment or "alignment_unknown"
    stage_by_risk_gate = {
        "FAIL_PILOT_MATCH": "PILOT_MATCH",
        "FAIL_AMBIGUITY": "AMBIGUITY",
        "FAIL_TEXTURE_DRIFT": "TEXTURE",
        "FAIL_ENTRY_TOO_OPEN": "ENTRY_POLICY",
        "FAIL_HOLD_POLICY": "HOLD_POLICY",
    }
    if risk_gate in stage_by_risk_gate:
        return stage_by_risk_gate[risk_gate], risk_gate
    if candidate_state == "OBSERVE_ONLY":
        return "CANARY_SCOPE", eligibility or "scope_still_observe_only"
    return "NONE", "not_applicable"


def build_xau_refined_gate_timebox_audit_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    persisted_row = dict(_mapping(row))
    symbol = _text(persisted_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        profile = {
            "contract_version": XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION,
            "audit_state_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "xau_refined_gate_timebox_audit_profile_v1": profile,
            "xau_gate_timebox_audit_state_v1": "NOT_APPLICABLE",
            "xau_gate_failure_stage_v1": "NOT_APPLICABLE",
            "xau_gate_failure_primary_driver_v1": "symbol_not_xau",
            "xau_gate_saved_vs_effective_state_v1": "NOT_APPLICABLE",
            "xau_gate_persisted_alignment_state_v1": "",
            "xau_gate_effective_alignment_state_v1": "",
            "xau_gate_persisted_candidate_state_v1": "",
            "xau_gate_effective_candidate_state_v1": "",
            "xau_gate_persisted_risk_gate_v1": "",
            "xau_gate_effective_risk_gate_v1": "",
            "xau_gate_effective_scope_detail_v1": "",
            "xau_gate_effective_flow_support_state_v1": "",
            "xau_gate_effective_aggregate_conviction_v1": None,
            "xau_gate_effective_flow_persistence_v1": None,
            "xau_gate_persisted_field_gap_v1": [],
            "xau_gate_timebox_reason_summary_v1": "symbol_not_xau",
        }

    effective_row = recompute_xau_effective_chain_row_v1(persisted_row)
    saved_vs_effective, missing_fields = _saved_vs_effective_state(persisted_row, effective_row)
    failure_stage, primary_driver = _failure_stage(effective_row)
    audit_state = "READY"
    if failure_stage == "NOT_APPLICABLE":
        audit_state = "NOT_APPLICABLE"
    elif not _text(effective_row.get("xau_state_slot_core_v1")):
        audit_state = "HOLD"

    persisted_alignment = _text(persisted_row.get("lifecycle_policy_alignment_state_v1"))
    effective_alignment = _text(effective_row.get("lifecycle_policy_alignment_state_v1"))
    persisted_candidate = _text(persisted_row.get("lifecycle_canary_candidate_state_v1"))
    effective_candidate = _text(effective_row.get("lifecycle_canary_candidate_state_v1"))
    persisted_risk_gate = _text(persisted_row.get("xau_lifecycle_canary_risk_gate_v1"))
    effective_risk_gate = _text(effective_row.get("xau_lifecycle_canary_risk_gate_v1"))
    effective_scope_detail = _text(effective_row.get("xau_lifecycle_canary_scope_detail_v1"))
    effective_flow_state = _text(effective_row.get("symbol_state_strength_flow_support_state_v1"))
    effective_aggregate = effective_row.get("symbol_state_strength_aggregate_conviction_v1")
    effective_persistence = effective_row.get("symbol_state_strength_flow_persistence_v1")
    effective_slot = _text(effective_row.get("xau_state_slot_core_v1"))
    effective_match = _text(effective_row.get("xau_pilot_window_match_v1"))
    effective_texture = _text(effective_row.get("xau_texture_slot_v1"))
    effective_ambiguity = _text(effective_row.get("xau_ambiguity_level_v1"))
    effective_entry = _text(effective_row.get("entry_policy_v1"))
    effective_hold = _text(effective_row.get("hold_policy_v1"))
    effective_reduce = _text(effective_row.get("reduce_policy_v1"))

    reason = (
        f"saved_vs_effective={saved_vs_effective}; failure_stage={failure_stage}; driver={primary_driver}; "
        f"effective_slot={effective_slot or 'none'}; pilot_match={effective_match or 'none'}; "
        f"flow_state={effective_flow_state or 'none'}; aggregate={effective_aggregate}; persistence={effective_persistence}; "
        f"ambiguity={effective_ambiguity or 'none'}; texture={effective_texture or 'none'}; "
        f"alignment={effective_alignment or 'none'}; canary={effective_candidate or 'none'}; "
        f"risk_gate={effective_risk_gate or 'none'}; entry={effective_entry or 'none'}; "
        f"hold={effective_hold or 'none'}; reduce={effective_reduce or 'none'}"
    )
    profile = {
        "contract_version": XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION,
        "audit_state_v1": audit_state,
        "failure_stage_v1": failure_stage,
        "failure_primary_driver_v1": primary_driver,
        "saved_vs_effective_state_v1": saved_vs_effective,
        "persisted_field_gap_v1": list(missing_fields),
        "effective_slot_core_v1": effective_slot,
        "effective_pilot_match_v1": effective_match,
        "effective_candidate_state_v1": effective_candidate,
        "effective_risk_gate_v1": effective_risk_gate,
        "effective_scope_detail_v1": effective_scope_detail,
        "effective_flow_support_state_v1": effective_flow_state,
        "effective_aggregate_conviction_v1": effective_aggregate,
        "effective_flow_persistence_v1": effective_persistence,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "xau_refined_gate_timebox_audit_profile_v1": profile,
        "xau_gate_timebox_audit_state_v1": audit_state,
        "xau_gate_failure_stage_v1": failure_stage,
        "xau_gate_failure_primary_driver_v1": primary_driver,
        "xau_gate_saved_vs_effective_state_v1": saved_vs_effective,
        "xau_gate_persisted_alignment_state_v1": persisted_alignment,
        "xau_gate_effective_alignment_state_v1": effective_alignment,
        "xau_gate_persisted_candidate_state_v1": persisted_candidate,
        "xau_gate_effective_candidate_state_v1": effective_candidate,
        "xau_gate_persisted_risk_gate_v1": persisted_risk_gate,
        "xau_gate_effective_risk_gate_v1": effective_risk_gate,
        "xau_gate_effective_scope_detail_v1": effective_scope_detail,
        "xau_gate_effective_flow_support_state_v1": effective_flow_state,
        "xau_gate_effective_aggregate_conviction_v1": effective_aggregate,
        "xau_gate_effective_flow_persistence_v1": effective_persistence,
        "xau_gate_persisted_field_gap_v1": list(missing_fields),
        "xau_gate_timebox_reason_summary_v1": reason,
    }


def attach_xau_refined_gate_timebox_audit_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_xau_refined_gate_timebox_audit_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_xau_refined_gate_timebox_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_xau_refined_gate_timebox_audit_fields_v1(latest_signal_by_symbol)
    xau_rows = {
        symbol: row for symbol, row in rows_by_symbol.items() if _text(row.get("symbol")).upper() == "XAUUSD"
    }
    audit_state_counts = Counter()
    failure_stage_counts = Counter()
    saved_effective_counts = Counter()
    risk_gate_counts = Counter()
    for row in xau_rows.values():
        audit_state_counts.update([_text(row.get("xau_gate_timebox_audit_state_v1"))])
        failure_stage_counts.update([_text(row.get("xau_gate_failure_stage_v1"))])
        saved_effective_counts.update([_text(row.get("xau_gate_saved_vs_effective_state_v1"))])
        risk_gate_counts.update([_text(row.get("xau_gate_effective_risk_gate_v1"))])

    xau_count = len(xau_rows)
    ready_count = int(audit_state_counts.get("READY", 0))
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if xau_count and ready_count == xau_count else "HOLD",
        "status_reasons": (
            ["xau_refined_gate_timebox_audit_available"] if xau_count else ["xau_row_missing_for_gate_audit"]
        ),
        "xau_row_count": int(xau_count),
        "audit_ready_count": int(ready_count),
        "gate_failure_stage_count_summary": dict(failure_stage_counts),
        "saved_vs_effective_state_count_summary": dict(saved_effective_counts),
        "effective_risk_gate_count_summary": dict(risk_gate_counts),
    }
    return {
        "contract_version": XAU_REFINED_GATE_TIMEBOX_AUDIT_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_xau_refined_gate_timebox_audit_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# XAU Refined Gate Timebox Audit v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- xau_row_count: `{int(summary.get('xau_row_count', 0) or 0)}`",
        f"- audit_ready_count: `{int(summary.get('audit_ready_count', 0) or 0)}`",
        "",
        "## XAU Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "XAUUSD":
            continue
        lines.append(
            f"- `{symbol}`: failure_stage={row.get('xau_gate_failure_stage_v1', '')} | "
            f"driver={row.get('xau_gate_failure_primary_driver_v1', '')} | "
            f"saved_vs_effective={row.get('xau_gate_saved_vs_effective_state_v1', '')} | "
            f"effective_canary={row.get('xau_gate_effective_candidate_state_v1', '')} | "
            f"effective_risk_gate={row.get('xau_gate_effective_risk_gate_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_xau_refined_gate_timebox_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_xau_refined_gate_timebox_audit_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "xau_refined_gate_timebox_audit_latest.json"
    md_path = output_dir / "xau_refined_gate_timebox_audit_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_xau_refined_gate_timebox_audit_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
