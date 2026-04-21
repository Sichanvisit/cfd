from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.execution_policy_shadow_audit import (
    attach_execution_policy_shadow_audit_fields_v1,
)


BOUNDED_LIFECYCLE_CANARY_CONTRACT_VERSION = "bounded_lifecycle_canary_contract_v1"
BOUNDED_LIFECYCLE_CANARY_SUMMARY_VERSION = "bounded_lifecycle_canary_summary_v1"

LIFECYCLE_CANARY_STATE_ENUM_V1 = ("BLOCKED", "OBSERVE_ONLY", "BOUNDED_READY")
LIFECYCLE_CANARY_SCOPE_ENUM_V1 = ("NONE", "XAU_SINGLE_SYMBOL", "SINGLE_SYMBOL_SINGLE_POLICY")
LIFECYCLE_CANARY_POLICY_SLICE_ENUM_V1 = (
    "NONE",
    "ENTRY_DELAY_ONLY",
    "HOLD_ONLY",
    "HOLD_REDUCE_ONLY",
    "REDUCE_EXIT_ONLY",
)
XAU_LIFECYCLE_CANARY_RISK_GATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "PASS",
    "PASS_FLOW_CONFIRMED",
    "FAIL_PILOT_MATCH",
    "FAIL_AMBIGUITY",
    "FAIL_TEXTURE_DRIFT",
    "FAIL_ENTRY_TOO_OPEN",
    "FAIL_HOLD_POLICY",
)
XAU_LIFECYCLE_CANARY_SCOPE_DETAIL_ENUM_V1 = (
    "NONE",
    "XAU_HOLD_ONLY",
    "XAU_HOLD_REDUCE",
    "XAU_DELAY_ENTRY_OBSERVE",
)


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


def build_bounded_lifecycle_canary_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_LIFECYCLE_CANARY_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only bounded lifecycle canary recommendation layer. Selects only narrowly scoped lifecycle "
            "policy slices that are aligned enough for future bounded canary review."
        ),
        "lifecycle_canary_state_enum_v1": list(LIFECYCLE_CANARY_STATE_ENUM_V1),
        "lifecycle_canary_scope_enum_v1": list(LIFECYCLE_CANARY_SCOPE_ENUM_V1),
        "lifecycle_canary_policy_slice_enum_v1": list(LIFECYCLE_CANARY_POLICY_SLICE_ENUM_V1),
        "xau_lifecycle_canary_risk_gate_enum_v1": list(XAU_LIFECYCLE_CANARY_RISK_GATE_ENUM_V1),
        "xau_lifecycle_canary_scope_detail_enum_v1": list(XAU_LIFECYCLE_CANARY_SCOPE_DETAIL_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_lifecycle_canary_profile_v1",
            "lifecycle_canary_candidate_state_v1",
            "lifecycle_canary_scope_v1",
            "lifecycle_canary_policy_slice_v1",
            "lifecycle_canary_eligibility_v1",
            "xau_lifecycle_canary_risk_gate_v1",
            "xau_lifecycle_canary_scope_detail_v1",
            "lifecycle_canary_reason_summary_v1",
        ],
        "control_rules_v1": [
            "bounded canary remains recommendation-only in v1",
            "review_pending or misaligned lifecycle rows cannot become bounded ready",
            "xau bridge-backed hold or hold-plus-reduce slices can be proposed before broader multi-symbol scope",
            "xau bounded ready requires either pilot match or confirmed directional flow support, plus non-high ambiguity, non-drift texture, delayed entry, and hold support",
            "no order placement or state25 change is allowed here",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("execution_policy_shadow_audit_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_execution_policy_shadow_audit_fields_v1({symbol: row}).get(symbol, row))


def _xau_risk_gate(row: Mapping[str, Any]) -> str:
    pilot_match = _text(row.get("xau_pilot_window_match_v1")).upper()
    flow_state = _text(row.get("symbol_state_strength_flow_support_state_v1")).upper()
    aggregate_conviction = float(row.get("symbol_state_strength_aggregate_conviction_v1") or 0.0)
    flow_persistence = float(row.get("symbol_state_strength_flow_persistence_v1") or 0.0)
    ambiguity = _text(row.get("xau_ambiguity_level_v1")).upper()
    texture = _text(row.get("xau_texture_slot_v1")).upper()
    entry_policy = _text(row.get("entry_policy_v1")).upper()
    hold_policy = _text(row.get("hold_policy_v1")).upper()

    pilot_or_flow_pass = pilot_match in {"MATCHED_ACTIVE_PROFILE", "PARTIAL_ACTIVE_PROFILE"}
    if not pilot_or_flow_pass and flow_state == "FLOW_CONFIRMED" and aggregate_conviction >= 0.7 and flow_persistence >= 0.6:
        pilot_or_flow_pass = True
        pass_state = "PASS_FLOW_CONFIRMED"
    else:
        pass_state = "PASS"

    if not pilot_or_flow_pass:
        return "FAIL_PILOT_MATCH"
    if ambiguity == "HIGH":
        return "FAIL_AMBIGUITY"
    if texture == "DRIFT":
        return "FAIL_TEXTURE_DRIFT"
    if entry_policy not in {"DELAYED_ENTRY", "NO_NEW_ENTRY"}:
        return "FAIL_ENTRY_TOO_OPEN"
    if hold_policy not in {"HOLD_FAVOR", "STRONG_HOLD"}:
        return "FAIL_HOLD_POLICY"
    return pass_state


def build_bounded_lifecycle_canary_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_audit(row or {})
    symbol = _text(payload.get("symbol")).upper()
    alignment = _text(payload.get("lifecycle_policy_alignment_state_v1")).upper()
    source = _text(payload.get("state_slot_execution_policy_source_v1")).upper()
    hold_policy = _text(payload.get("hold_policy_v1")).upper()
    reduce_policy = _text(payload.get("reduce_policy_v1")).upper()
    entry_policy = _text(payload.get("entry_policy_v1")).upper()

    state = "BLOCKED"
    scope = "NONE"
    slice_name = "NONE"
    eligibility = "not_eligible"
    xau_risk_gate = "NOT_APPLICABLE"
    xau_scope_detail = "NONE"

    if alignment == "ALIGNED":
        if symbol == "XAUUSD" and source == "BRIDGE_BIAS":
            xau_risk_gate = _xau_risk_gate(payload)
            scope = "XAU_SINGLE_SYMBOL"
            if xau_risk_gate in {"PASS", "PASS_FLOW_CONFIRMED"} and hold_policy == "STRONG_HOLD" and reduce_policy in {"REDUCE_FAVOR", "REDUCE_STRONG"}:
                state = "BOUNDED_READY"
                slice_name = "HOLD_REDUCE_ONLY"
                xau_scope_detail = "XAU_HOLD_REDUCE"
                eligibility = "aligned_xau_hold_reduce_canary"
            elif xau_risk_gate in {"PASS", "PASS_FLOW_CONFIRMED"} and hold_policy in {"HOLD_FAVOR", "STRONG_HOLD"} and reduce_policy in {"HOLD_SIZE", "LIGHT_REDUCE"}:
                state = "BOUNDED_READY"
                slice_name = "HOLD_ONLY"
                xau_scope_detail = "XAU_HOLD_ONLY"
                eligibility = "aligned_xau_hold_only_canary"
            else:
                state = "OBSERVE_ONLY"
                slice_name = "ENTRY_DELAY_ONLY" if entry_policy == "DELAYED_ENTRY" else "NONE"
                xau_scope_detail = "XAU_DELAY_ENTRY_OBSERVE" if slice_name == "ENTRY_DELAY_ONLY" else "NONE"
                eligibility = f"xau_gate_{xau_risk_gate.lower()}"
        elif source == "COMMON_SLOT_DERIVED" and entry_policy == "DELAYED_ENTRY":
            state = "OBSERVE_ONLY"
            scope = "SINGLE_SYMBOL_SINGLE_POLICY"
            slice_name = "ENTRY_DELAY_ONLY"
            eligibility = "aligned_but_symbol_threshold_still_pending"
        else:
            state = "OBSERVE_ONLY"
            scope = "SINGLE_SYMBOL_SINGLE_POLICY"
            slice_name = "REDUCE_EXIT_ONLY" if reduce_policy in {"REDUCE_FAVOR", "REDUCE_STRONG"} else "NONE"
            eligibility = "aligned_but_scope_still_narrow"
    elif alignment == "REVIEW_PENDING":
        state = "OBSERVE_ONLY"
        scope = "SINGLE_SYMBOL_SINGLE_POLICY"
        slice_name = "ENTRY_DELAY_ONLY" if entry_policy == "DELAYED_ENTRY" else "NONE"
        eligibility = "review_pending_requires_more_data"
    else:
        eligibility = "blocked_by_shadow_audit"

    reason = (
        f"symbol={symbol}; alignment={alignment}; source={source}; entry={entry_policy}; "
        f"hold={hold_policy}; reduce={reduce_policy}; state={state}; slice={slice_name}; "
        f"xau_risk_gate={xau_risk_gate}; xau_scope_detail={xau_scope_detail}"
    )
    profile = {
        "contract_version": BOUNDED_LIFECYCLE_CANARY_CONTRACT_VERSION,
        "candidate_state_v1": state,
        "scope_v1": scope,
        "policy_slice_v1": slice_name,
        "eligibility_v1": eligibility,
        "xau_lifecycle_canary_risk_gate_v1": xau_risk_gate,
        "xau_lifecycle_canary_scope_detail_v1": xau_scope_detail,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "bounded_lifecycle_canary_profile_v1": profile,
        "lifecycle_canary_candidate_state_v1": state,
        "lifecycle_canary_scope_v1": scope,
        "lifecycle_canary_policy_slice_v1": slice_name,
        "lifecycle_canary_eligibility_v1": eligibility,
        "xau_lifecycle_canary_risk_gate_v1": xau_risk_gate,
        "xau_lifecycle_canary_scope_detail_v1": xau_scope_detail,
        "lifecycle_canary_reason_summary_v1": reason,
    }


def attach_bounded_lifecycle_canary_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_audit(raw)
        row.update(build_bounded_lifecycle_canary_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_bounded_lifecycle_canary_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_bounded_lifecycle_canary_fields_v1(latest_signal_by_symbol)
    state_counts = Counter()
    scope_counts = Counter()
    slice_counts = Counter()
    xau_risk_gate_counts = Counter()
    xau_scope_detail_counts = Counter()
    symbol_count = len(rows_by_symbol)
    ready_count = 0
    for row in rows_by_symbol.values():
        state = _text(row.get("lifecycle_canary_candidate_state_v1"))
        state_counts.update([state])
        scope_counts.update([_text(row.get("lifecycle_canary_scope_v1"))])
        slice_counts.update([_text(row.get("lifecycle_canary_policy_slice_v1"))])
        xau_risk_gate_counts.update([_text(row.get("xau_lifecycle_canary_risk_gate_v1"))])
        xau_scope_detail_counts.update([_text(row.get("xau_lifecycle_canary_scope_detail_v1"))])
        if state == "BOUNDED_READY":
            ready_count += 1
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["bounded_lifecycle_canary_candidates_available"] if symbol_count else ["no_lifecycle_rows"]
        ),
        "symbol_count": int(symbol_count),
        "bounded_ready_count": int(ready_count),
        "lifecycle_canary_candidate_state_count_summary": dict(state_counts),
        "lifecycle_canary_scope_count_summary": dict(scope_counts),
        "lifecycle_canary_policy_slice_count_summary": dict(slice_counts),
        "xau_lifecycle_canary_risk_gate_count_summary": dict(xau_risk_gate_counts),
        "xau_lifecycle_canary_scope_detail_count_summary": dict(xau_scope_detail_counts),
    }
    return {
        "contract_version": BOUNDED_LIFECYCLE_CANARY_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_bounded_lifecycle_canary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Bounded Lifecycle Canary v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- bounded_ready_count: `{int(summary.get('bounded_ready_count', 0) or 0)}`",
        "",
        "## Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: state={row.get('lifecycle_canary_candidate_state_v1', '')} | "
            f"scope={row.get('lifecycle_canary_scope_v1', '')} | "
            f"slice={row.get('lifecycle_canary_policy_slice_v1', '')} | "
            f"xau_risk_gate={row.get('xau_lifecycle_canary_risk_gate_v1', '')} | "
            f"xau_scope_detail={row.get('xau_lifecycle_canary_scope_detail_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_lifecycle_canary_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_bounded_lifecycle_canary_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "bounded_lifecycle_canary_latest.json"
    md_path = output_dir / "bounded_lifecycle_canary_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_bounded_lifecycle_canary_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
