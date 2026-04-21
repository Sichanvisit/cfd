from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.xau_refined_gate_timebox_audit import (
    build_xau_refined_gate_timebox_audit_row_v1,
    recompute_xau_effective_chain_row_v1,
)


STATE_FLOW_F0_CHAIN_ALIGNMENT_CONTRACT_VERSION = "state_flow_f0_chain_alignment_contract_v1"
STATE_FLOW_F0_CHAIN_ALIGNMENT_SUMMARY_VERSION = "state_flow_f0_chain_alignment_summary_v1"

STATE_FLOW_F0_ALIGNMENT_STATE_ENUM_V1 = ("READY", "HOLD", "BLOCKED", "NOT_APPLICABLE")
STATE_FLOW_F0_RAW_EFFECTIVE_STATE_ENUM_V1 = (
    "CONSISTENT",
    "PERSISTED_FIELDS_MISSING",
    "PERSISTED_OUTDATED",
    "CONCLUSION_DIVERGENCE",
    "NOT_APPLICABLE",
)
STATE_FLOW_F0_AUDIT_CONSISTENCY_STATE_ENUM_V1 = (
    "CONSISTENT",
    "MISSING_EFFECTIVE_FIELDS",
    "CONFLICT",
    "NOT_APPLICABLE",
)
STATE_FLOW_F0_PRIMARY_LAYER_ENUM_V1 = (
    "NONE",
    "SYMBOL_CALIBRATION",
    "XAU_READONLY_SURFACE",
    "BOUNDED_LIFECYCLE_CANARY",
    "XAU_REFINED_GATE_AUDIT",
    "CHAIN_INPUT",
    "NOT_APPLICABLE",
)

_SYMBOL_FIELD_SET = (
    "symbol_state_strength_best_profile_key_v1",
    "symbol_state_strength_profile_status_v1",
    "symbol_state_strength_profile_match_v1",
    "symbol_state_strength_aggregate_conviction_v1",
    "symbol_state_strength_flow_persistence_v1",
    "symbol_state_strength_flow_support_state_v1",
)
_SURFACE_FIELD_SET = (
    "xau_state_slot_core_v1",
    "xau_pilot_window_match_v1",
    "xau_texture_slot_v1",
    "xau_ambiguity_level_v1",
)
_CANARY_FIELD_SET = (
    "lifecycle_canary_candidate_state_v1",
    "xau_lifecycle_canary_risk_gate_v1",
    "xau_lifecycle_canary_scope_detail_v1",
)
_AUDIT_FIELD_SET = (
    "xau_gate_timebox_audit_state_v1",
    "xau_gate_failure_stage_v1",
    "xau_gate_failure_primary_driver_v1",
    "xau_gate_saved_vs_effective_state_v1",
)
_CRITICAL_FIELD_LAYERS = {
    **{field: "SYMBOL_CALIBRATION" for field in _SYMBOL_FIELD_SET},
    **{field: "XAU_READONLY_SURFACE" for field in _SURFACE_FIELD_SET},
    **{field: "BOUNDED_LIFECYCLE_CANARY" for field in _CANARY_FIELD_SET},
    **{field: "XAU_REFINED_GATE_AUDIT" for field in _AUDIT_FIELD_SET},
}
_RAW_EFFECTIVE_DECISION_FIELDS = (
    "symbol_state_strength_best_profile_key_v1",
    "symbol_state_strength_profile_match_v1",
    "symbol_state_strength_flow_support_state_v1",
    "xau_state_slot_core_v1",
    "lifecycle_canary_candidate_state_v1",
    "xau_lifecycle_canary_risk_gate_v1",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_state_flow_f0_chain_alignment_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_FLOW_F0_CHAIN_ALIGNMENT_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F0 diagnostic chain alignment layer for the directional flow transition. Compares the persisted "
            "runtime row, the effective XAU recomputation chain, and the downstream audit/canary interpretation "
            "so we can explain stale fields separately from genuine calculation divergence."
        ),
        "alignment_state_enum_v1": list(STATE_FLOW_F0_ALIGNMENT_STATE_ENUM_V1),
        "raw_vs_effective_state_enum_v1": list(STATE_FLOW_F0_RAW_EFFECTIVE_STATE_ENUM_V1),
        "audit_consistency_state_enum_v1": list(STATE_FLOW_F0_AUDIT_CONSISTENCY_STATE_ENUM_V1),
        "primary_divergence_layer_enum_v1": list(STATE_FLOW_F0_PRIMARY_LAYER_ENUM_V1),
        "row_level_fields_v1": [
            "state_flow_f0_chain_alignment_profile_v1",
            "state_flow_f0_chain_alignment_state_v1",
            "state_flow_f0_raw_vs_effective_state_v1",
            "state_flow_f0_effective_vs_audit_state_v1",
            "state_flow_f0_primary_divergence_layer_v1",
            "state_flow_f0_missing_persisted_fields_v1",
            "state_flow_f0_raw_profile_key_v1",
            "state_flow_f0_effective_profile_key_v1",
            "state_flow_f0_raw_slot_core_v1",
            "state_flow_f0_effective_slot_core_v1",
            "state_flow_f0_raw_flow_support_state_v1",
            "state_flow_f0_effective_flow_support_state_v1",
            "state_flow_f0_raw_canary_state_v1",
            "state_flow_f0_effective_canary_state_v1",
            "state_flow_f0_raw_risk_gate_v1",
            "state_flow_f0_effective_risk_gate_v1",
            "state_flow_f0_audit_failure_stage_v1",
            "state_flow_f0_reason_summary_v1",
        ],
        "control_rules_v1": [
            "diagnostic-only layer that cannot change execution or state25",
            "persisted runtime row gaps must stay distinguishable from effective recomputation results",
            "same effective input cannot lead to conflicting audit/canary conclusions",
            "xau refined gate audit remains the main explanation source for stale-versus-effective differences",
            "F0 should mark READY when differences are explainable, HOLD when stale dependence remains, and BLOCKED when conclusions flip for the same effective input",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _is_missing(value: Any) -> bool:
    return _text(value) == ""


def _compare_floatish(left: Any, right: Any) -> bool:
    left_f = _float_or_none(left)
    right_f = _float_or_none(right)
    if left_f is None or right_f is None:
        return _text(left) == _text(right)
    return round(left_f, 4) == round(right_f, 4)


def _raw_vs_effective_state(
    raw_row: Mapping[str, Any],
    effective_row: Mapping[str, Any],
) -> tuple[str, list[str], list[str]]:
    symbol = _text(raw_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        return "NOT_APPLICABLE", [], []

    missing_fields = [field for field in _CRITICAL_FIELD_LAYERS if _is_missing(raw_row.get(field))]
    differing_fields: list[str] = []
    for field in _CRITICAL_FIELD_LAYERS:
        if field in missing_fields:
            continue
        raw_value = raw_row.get(field)
        effective_value = effective_row.get(field)
        if field in {
            "symbol_state_strength_aggregate_conviction_v1",
            "symbol_state_strength_flow_persistence_v1",
        }:
            same = _compare_floatish(raw_value, effective_value)
        else:
            same = _text(raw_value) == _text(effective_value)
        if not same:
            differing_fields.append(field)

    if missing_fields:
        return "PERSISTED_FIELDS_MISSING", missing_fields, differing_fields
    if any(field in _RAW_EFFECTIVE_DECISION_FIELDS for field in differing_fields):
        return "CONCLUSION_DIVERGENCE", [], differing_fields
    if differing_fields:
        return "PERSISTED_OUTDATED", [], differing_fields
    return "CONSISTENT", [], []


def _effective_vs_audit_state(
    effective_row: Mapping[str, Any],
    audit_row: Mapping[str, Any],
) -> tuple[str, list[str]]:
    symbol = _text(effective_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        return "NOT_APPLICABLE", []

    required_pairs = (
        ("lifecycle_canary_candidate_state_v1", "xau_gate_effective_candidate_state_v1"),
        ("xau_lifecycle_canary_risk_gate_v1", "xau_gate_effective_risk_gate_v1"),
        ("xau_lifecycle_canary_scope_detail_v1", "xau_gate_effective_scope_detail_v1"),
        ("symbol_state_strength_flow_support_state_v1", "xau_gate_effective_flow_support_state_v1"),
        ("symbol_state_strength_aggregate_conviction_v1", "xau_gate_effective_aggregate_conviction_v1"),
        ("symbol_state_strength_flow_persistence_v1", "xau_gate_effective_flow_persistence_v1"),
    )
    missing_effective = [
        effective_field
        for effective_field, _ in required_pairs
        if _is_missing(effective_row.get(effective_field))
    ]
    if missing_effective:
        return "MISSING_EFFECTIVE_FIELDS", missing_effective

    conflicts: list[str] = []
    for effective_field, audit_field in required_pairs:
        left = effective_row.get(effective_field)
        right = audit_row.get(audit_field)
        if effective_field in {
            "symbol_state_strength_aggregate_conviction_v1",
            "symbol_state_strength_flow_persistence_v1",
        }:
            same = _compare_floatish(left, right)
        else:
            same = _text(left) == _text(right)
        if not same:
            conflicts.append(f"{effective_field}->{audit_field}")
    return ("CONFLICT", conflicts) if conflicts else ("CONSISTENT", [])


def _primary_divergence_layer(
    *,
    raw_vs_effective_state: str,
    missing_fields: list[str],
    differing_fields: list[str],
    audit_consistency_state: str,
) -> str:
    if raw_vs_effective_state == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if audit_consistency_state == "CONFLICT":
        return "XAU_REFINED_GATE_AUDIT"
    ordered_fields = [*missing_fields, *differing_fields]
    for field in ordered_fields:
        layer = _CRITICAL_FIELD_LAYERS.get(field)
        if layer:
            return layer
    if raw_vs_effective_state == "CONSISTENT":
        return "NONE"
    return "CHAIN_INPUT"


def build_state_flow_f0_chain_alignment_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    raw_row = dict(_mapping(row))
    symbol = _text(raw_row.get("symbol")).upper()
    if symbol != "XAUUSD":
        profile = {
            "contract_version": STATE_FLOW_F0_CHAIN_ALIGNMENT_CONTRACT_VERSION,
            "alignment_state_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "state_flow_f0_chain_alignment_profile_v1": profile,
            "state_flow_f0_chain_alignment_state_v1": "NOT_APPLICABLE",
            "state_flow_f0_raw_vs_effective_state_v1": "NOT_APPLICABLE",
            "state_flow_f0_effective_vs_audit_state_v1": "NOT_APPLICABLE",
            "state_flow_f0_primary_divergence_layer_v1": "NOT_APPLICABLE",
            "state_flow_f0_missing_persisted_fields_v1": [],
            "state_flow_f0_raw_profile_key_v1": "",
            "state_flow_f0_effective_profile_key_v1": "",
            "state_flow_f0_raw_slot_core_v1": "",
            "state_flow_f0_effective_slot_core_v1": "",
            "state_flow_f0_raw_flow_support_state_v1": "",
            "state_flow_f0_effective_flow_support_state_v1": "",
            "state_flow_f0_raw_canary_state_v1": "",
            "state_flow_f0_effective_canary_state_v1": "",
            "state_flow_f0_raw_risk_gate_v1": "",
            "state_flow_f0_effective_risk_gate_v1": "",
            "state_flow_f0_audit_failure_stage_v1": "",
            "state_flow_f0_reason_summary_v1": "symbol_not_xau",
        }

    effective_row = recompute_xau_effective_chain_row_v1(raw_row)
    audit_row = build_xau_refined_gate_timebox_audit_row_v1(raw_row)
    raw_vs_effective_state, missing_fields, differing_fields = _raw_vs_effective_state(raw_row, effective_row)
    audit_consistency_state, audit_conflicts = _effective_vs_audit_state(effective_row, audit_row)
    primary_layer = _primary_divergence_layer(
        raw_vs_effective_state=raw_vs_effective_state,
        missing_fields=missing_fields,
        differing_fields=differing_fields,
        audit_consistency_state=audit_consistency_state,
    )

    if audit_consistency_state == "CONFLICT":
        alignment_state = "BLOCKED"
    elif raw_vs_effective_state in {"PERSISTED_FIELDS_MISSING", "PERSISTED_OUTDATED"} and audit_consistency_state == "CONSISTENT":
        alignment_state = "READY"
    elif raw_vs_effective_state == "CONCLUSION_DIVERGENCE":
        saved_vs_effective = _text(audit_row.get("xau_gate_saved_vs_effective_state_v1")).upper()
        alignment_state = (
            "READY"
            if saved_vs_effective in {"PERSISTED_FIELDS_MISSING", "PERSISTED_OUTDATED"} and audit_consistency_state == "CONSISTENT"
            else "HOLD"
        )
    elif audit_consistency_state == "MISSING_EFFECTIVE_FIELDS":
        alignment_state = "HOLD"
    else:
        alignment_state = "READY"

    reason = (
        f"raw_vs_effective={raw_vs_effective_state}; effective_vs_audit={audit_consistency_state}; "
        f"primary_layer={primary_layer}; missing={','.join(missing_fields) or 'none'}; "
        f"diff={','.join(differing_fields) or 'none'}; audit_conflicts={','.join(audit_conflicts) or 'none'}; "
        f"raw_profile={_text(raw_row.get('symbol_state_strength_best_profile_key_v1')) or 'none'}; "
        f"effective_profile={_text(effective_row.get('symbol_state_strength_best_profile_key_v1')) or 'none'}; "
        f"raw_flow={_text(raw_row.get('symbol_state_strength_flow_support_state_v1')) or 'none'}; "
        f"effective_flow={_text(effective_row.get('symbol_state_strength_flow_support_state_v1')) or 'none'}; "
        f"raw_canary={_text(raw_row.get('lifecycle_canary_candidate_state_v1')) or 'none'}; "
        f"effective_canary={_text(effective_row.get('lifecycle_canary_candidate_state_v1')) or 'none'}; "
        f"audit_failure={_text(audit_row.get('xau_gate_failure_stage_v1')) or 'none'}"
    )

    profile = {
        "contract_version": STATE_FLOW_F0_CHAIN_ALIGNMENT_CONTRACT_VERSION,
        "alignment_state_v1": alignment_state,
        "raw_vs_effective_state_v1": raw_vs_effective_state,
        "effective_vs_audit_state_v1": audit_consistency_state,
        "primary_divergence_layer_v1": primary_layer,
        "missing_persisted_fields_v1": list(missing_fields),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "state_flow_f0_chain_alignment_profile_v1": profile,
        "state_flow_f0_chain_alignment_state_v1": alignment_state,
        "state_flow_f0_raw_vs_effective_state_v1": raw_vs_effective_state,
        "state_flow_f0_effective_vs_audit_state_v1": audit_consistency_state,
        "state_flow_f0_primary_divergence_layer_v1": primary_layer,
        "state_flow_f0_missing_persisted_fields_v1": list(missing_fields),
        "state_flow_f0_raw_profile_key_v1": _text(raw_row.get("symbol_state_strength_best_profile_key_v1")),
        "state_flow_f0_effective_profile_key_v1": _text(effective_row.get("symbol_state_strength_best_profile_key_v1")),
        "state_flow_f0_raw_slot_core_v1": _text(raw_row.get("xau_state_slot_core_v1")),
        "state_flow_f0_effective_slot_core_v1": _text(effective_row.get("xau_state_slot_core_v1")),
        "state_flow_f0_raw_flow_support_state_v1": _text(raw_row.get("symbol_state_strength_flow_support_state_v1")),
        "state_flow_f0_effective_flow_support_state_v1": _text(
            effective_row.get("symbol_state_strength_flow_support_state_v1")
        ),
        "state_flow_f0_raw_canary_state_v1": _text(raw_row.get("lifecycle_canary_candidate_state_v1")),
        "state_flow_f0_effective_canary_state_v1": _text(effective_row.get("lifecycle_canary_candidate_state_v1")),
        "state_flow_f0_raw_risk_gate_v1": _text(raw_row.get("xau_lifecycle_canary_risk_gate_v1")),
        "state_flow_f0_effective_risk_gate_v1": _text(effective_row.get("xau_lifecycle_canary_risk_gate_v1")),
        "state_flow_f0_audit_failure_stage_v1": _text(audit_row.get("xau_gate_failure_stage_v1")),
        "state_flow_f0_reason_summary_v1": reason,
    }


def attach_state_flow_f0_chain_alignment_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_state_flow_f0_chain_alignment_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_state_flow_f0_chain_alignment_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_state_flow_f0_chain_alignment_fields_v1(latest_signal_by_symbol)
    xau_rows = {
        symbol: row for symbol, row in rows_by_symbol.items() if _text(row.get("symbol")).upper() == "XAUUSD"
    }
    alignment_counts = Counter()
    raw_effective_counts = Counter()
    audit_consistency_counts = Counter()
    primary_layer_counts = Counter()
    ready_count = 0
    hold_count = 0
    blocked_count = 0

    for row in xau_rows.values():
        alignment_state = _text(row.get("state_flow_f0_chain_alignment_state_v1"))
        alignment_counts.update([alignment_state])
        raw_effective_counts.update([_text(row.get("state_flow_f0_raw_vs_effective_state_v1"))])
        audit_consistency_counts.update([_text(row.get("state_flow_f0_effective_vs_audit_state_v1"))])
        primary_layer_counts.update([_text(row.get("state_flow_f0_primary_divergence_layer_v1"))])
        if alignment_state == "READY":
            ready_count += 1
        elif alignment_state == "HOLD":
            hold_count += 1
        elif alignment_state == "BLOCKED":
            blocked_count += 1

    xau_count = len(xau_rows)
    if blocked_count:
        status = "BLOCKED"
        reasons = ["same_input_chain_conflict_detected"]
    elif xau_count and hold_count == 0:
        status = "READY"
        reasons = ["f0_chain_alignment_explainable"]
    else:
        status = "HOLD"
        reasons = ["xau_chain_alignment_still_depends_on_stale_or_missing_fields"] if xau_count else ["xau_row_missing"]

    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": reasons,
        "xau_row_count": int(xau_count),
        "alignment_ready_count": int(ready_count),
        "alignment_hold_count": int(hold_count),
        "alignment_blocked_count": int(blocked_count),
        "alignment_state_count_summary": dict(alignment_counts),
        "raw_vs_effective_state_count_summary": dict(raw_effective_counts),
        "effective_vs_audit_state_count_summary": dict(audit_consistency_counts),
        "primary_divergence_layer_count_summary": dict(primary_layer_counts),
    }
    return {
        "contract_version": STATE_FLOW_F0_CHAIN_ALIGNMENT_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_flow_f0_chain_alignment_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Flow F0 Chain Alignment Audit v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- xau_row_count: `{int(summary.get('xau_row_count', 0) or 0)}`",
        f"- alignment_ready_count: `{int(summary.get('alignment_ready_count', 0) or 0)}`",
        f"- alignment_hold_count: `{int(summary.get('alignment_hold_count', 0) or 0)}`",
        f"- alignment_blocked_count: `{int(summary.get('alignment_blocked_count', 0) or 0)}`",
        "",
        "## XAU Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "XAUUSD":
            continue
        lines.append(
            f"- `{symbol}`: state={row.get('state_flow_f0_chain_alignment_state_v1', '')} | "
            f"raw_vs_effective={row.get('state_flow_f0_raw_vs_effective_state_v1', '')} | "
            f"effective_vs_audit={row.get('state_flow_f0_effective_vs_audit_state_v1', '')} | "
            f"layer={row.get('state_flow_f0_primary_divergence_layer_v1', '')} | "
            f"raw_flow={row.get('state_flow_f0_raw_flow_support_state_v1', '')} | "
            f"effective_flow={row.get('state_flow_f0_effective_flow_support_state_v1', '')} | "
            f"raw_canary={row.get('state_flow_f0_raw_canary_state_v1', '')} | "
            f"effective_canary={row.get('state_flow_f0_effective_canary_state_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_flow_f0_chain_alignment_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_flow_f0_chain_alignment_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "state_flow_f0_chain_alignment_latest.json"
    md_path = output_dir / "state_flow_f0_chain_alignment_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_state_flow_f0_chain_alignment_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
