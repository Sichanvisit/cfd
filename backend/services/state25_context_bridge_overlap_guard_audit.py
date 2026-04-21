from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_v1,
)
from backend.services.trade_csv_schema import now_kst_dt


STATE25_CONTEXT_BRIDGE_OVERLAP_GUARD_AUDIT_CONTRACT_VERSION = (
    "state25_context_bridge_overlap_guard_audit_v1"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _default_runtime_status_detail_path() -> Path:
    return _repo_root() / "data" / "runtime_status.detail.json"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = _text(raw)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _load_runtime_status_detail(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else _default_runtime_status_detail_path()
    if not target.exists():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_signal_rows(runtime_payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    latest = _mapping(runtime_payload).get("latest_signal_by_symbol")
    if not isinstance(latest, Mapping):
        return {}
    return {
        _text(symbol): dict(row)
        for symbol, row in dict(latest).items()
        if isinstance(row, Mapping)
    }


def _hint_signature(payload: Mapping[str, Any] | None) -> dict[str, str]:
    hint = _mapping(_mapping(payload).get("state25_runtime_hint_v1"))
    return {
        "scene_pattern_id": _text(hint.get("scene_pattern_id")),
        "entry_bias_hint": _text(hint.get("entry_bias_hint")),
        "wait_bias_hint": _text(hint.get("wait_bias_hint")),
        "exit_bias_hint": _text(hint.get("exit_bias_hint")),
        "transition_risk_hint": _text(hint.get("transition_risk_hint")),
        "reason_summary": _text(hint.get("reason_summary")),
    }


def _nonempty_hint_signature_count(signatures: list[dict[str, str]]) -> int:
    nonempty = [
        signature
        for signature in signatures
        if any(_text(value) for value in signature.values())
    ]
    return len(nonempty)


def _all_same_hint_signature(signatures: list[dict[str, str]]) -> bool:
    normalized = [
        json.dumps(signature, ensure_ascii=False, sort_keys=True)
        for signature in signatures
        if any(_text(value) for value in signature.values())
    ]
    if len(normalized) < 2:
        return False
    return len(set(normalized)) == 1


def _build_symbol_row(symbol: str, runtime_row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(runtime_row)
    stored_bridge = _mapping(row_map.get("state25_candidate_context_bridge_v1"))
    rebuilt_bridge = _mapping(build_state25_candidate_context_bridge_v1(row_map))
    bridge = rebuilt_bridge or stored_bridge
    forecast = _mapping(row_map.get("forecast_state25_runtime_bridge_v1"))
    belief = _mapping(row_map.get("belief_state25_runtime_bridge_v1"))
    barrier = _mapping(row_map.get("barrier_state25_runtime_bridge_v1"))
    countertrend = _mapping(row_map.get("countertrend_continuation_signal_v1"))
    overlap_sources = _text_list(bridge.get("overlap_sources"))
    hint_signatures = [
        _hint_signature(forecast),
        _hint_signature(belief),
        _hint_signature(barrier),
    ]
    all_same_hint_signature = _all_same_hint_signature(hint_signatures)
    nonempty_hint_signature_count = _nonempty_hint_signature_count(hint_signatures)

    requested_count = len(_mapping(bridge.get("weight_adjustments_requested")))
    effective_count = len(_mapping(bridge.get("weight_adjustments_effective")))
    suppressed_count = len(_mapping(bridge.get("weight_adjustments_suppressed")))
    overlap_guard_decision = _text(bridge.get("overlap_guard_decision"))
    overlap_same_runtime_hint_duplicate = bool(
        bridge.get("overlap_same_runtime_hint_duplicate")
    )

    blanket_risk_duplicate = (
        _text(bridge.get("overlap_class")) == "RISK_DUPLICATE"
        and {
            "forecast_state25_runtime_bridge_v1",
            "belief_state25_runtime_bridge_v1",
            "barrier_state25_runtime_bridge_v1",
        }.issubset(set(overlap_sources))
        and all_same_hint_signature
    )

    recommended_next_action = "keep_guard"
    if blanket_risk_duplicate and requested_count > 0 and effective_count == 0:
        recommended_next_action = "review_source_sensitive_overlap_guard"
    elif (
        blanket_risk_duplicate
        and overlap_guard_decision == "RELAXED_SAME_RUNTIME_HINT_DUPLICATE"
        and requested_count > 0
        and effective_count > 0
    ):
        recommended_next_action = "observe_relaxed_duplicate_runtime_hint_review_flow"
    elif blanket_risk_duplicate:
        recommended_next_action = "audit_blanket_risk_duplicate_scope"
    elif requested_count > 0 and effective_count == 0:
        recommended_next_action = "review_guard_suppression_path"

    return {
        "symbol": symbol,
        "consumer_check_side": _text(row_map.get("consumer_check_side")),
        "consumer_check_reason": _text(row_map.get("consumer_check_reason")),
        "context_conflict_state": _text(row_map.get("context_conflict_state")),
        "context_conflict_intensity": _text(row_map.get("context_conflict_intensity")),
        "htf_alignment_state": _text(row_map.get("htf_alignment_state")),
        "previous_box_break_state": _text(row_map.get("previous_box_break_state")),
        "previous_box_confidence": _text(row_map.get("previous_box_confidence")),
        "overlap_sources": overlap_sources,
        "overlap_class": _text(bridge.get("overlap_class")),
        "overlap_guard_decision": overlap_guard_decision,
        "overlap_same_runtime_hint_duplicate": overlap_same_runtime_hint_duplicate,
        "bridge_payload_source": "rebuilt" if rebuilt_bridge else "stored",
        "double_counting_guard_active": bool(bridge.get("double_counting_guard_active")),
        "requested_weight_count": requested_count,
        "effective_weight_count": effective_count,
        "suppressed_weight_count": suppressed_count,
        "failure_modes": _text_list(bridge.get("failure_modes")),
        "guard_modes": _text_list(bridge.get("guard_modes")),
        "trace_reason_codes": _text_list(bridge.get("trace_reason_codes")),
        "context_bundle_summary_ko": _text(row_map.get("context_bundle_summary_ko")),
        "all_same_hint_signature": all_same_hint_signature,
        "nonempty_hint_signature_count": nonempty_hint_signature_count,
        "hint_signatures": {
            "forecast": _hint_signature(forecast),
            "belief": _hint_signature(belief),
            "barrier": _hint_signature(barrier),
            "countertrend_present": bool(countertrend),
        },
        "blanket_risk_duplicate": blanket_risk_duplicate,
        "recommended_next_action": recommended_next_action,
    }


def build_state25_context_bridge_overlap_guard_audit_from_runtime_payload(
    runtime_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows = _latest_signal_rows(runtime_payload)
    symbol_rows = [_build_symbol_row(symbol, row) for symbol, row in rows.items()]
    source_presence_counts: dict[str, int] = {}
    overlap_class_counts: dict[str, int] = {}
    guard_active_symbol_count = 0
    requested_but_suppressed_symbol_count = 0
    blanket_risk_duplicate_symbol_count = 0
    relaxed_same_runtime_hint_symbol_count = 0

    for row in symbol_rows:
        if row["double_counting_guard_active"]:
            guard_active_symbol_count += 1
        if row["requested_weight_count"] > 0 and row["effective_weight_count"] == 0:
            requested_but_suppressed_symbol_count += 1
        if row["blanket_risk_duplicate"]:
            blanket_risk_duplicate_symbol_count += 1
        if row["overlap_guard_decision"] == "RELAXED_SAME_RUNTIME_HINT_DUPLICATE":
            relaxed_same_runtime_hint_symbol_count += 1
        overlap_class = _text(row.get("overlap_class"))
        if overlap_class:
            overlap_class_counts[overlap_class] = overlap_class_counts.get(overlap_class, 0) + 1
        for source in row.get("overlap_sources") or []:
            source_presence_counts[source] = source_presence_counts.get(source, 0) + 1

    dominant_issue = "no_overlap_guard"
    if requested_but_suppressed_symbol_count > 0:
        dominant_issue = "requested_rows_fully_suppressed_by_overlap_guard"
    elif (
        blanket_risk_duplicate_symbol_count > 0
        and relaxed_same_runtime_hint_symbol_count == blanket_risk_duplicate_symbol_count
    ):
        dominant_issue = "duplicate_runtime_hint_repetition_without_active_guard"
    elif blanket_risk_duplicate_symbol_count == len(symbol_rows) and symbol_rows:
        dominant_issue = "blanket_risk_duplicate_guard_all_symbols"
    elif guard_active_symbol_count > 0:
        dominant_issue = "overlap_guard_active_without_weight_candidates"

    recommended_next_step = "keep_current_overlap_guard"
    if requested_but_suppressed_symbol_count > 0:
        recommended_next_step = "design_source_sensitive_overlap_guard_for_weight_only_review"
    elif (
        blanket_risk_duplicate_symbol_count > 0
        and relaxed_same_runtime_hint_symbol_count == blanket_risk_duplicate_symbol_count
    ):
        recommended_next_step = "monitor_relaxed_duplicate_runtime_hint_effect"
    elif blanket_risk_duplicate_symbol_count > 0:
        recommended_next_step = "separate_runtime_hint_duplicate_from_true_weight_duplicate"

    generated_at = now_kst_dt().isoformat()
    return {
        "contract_version": STATE25_CONTEXT_BRIDGE_OVERLAP_GUARD_AUDIT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _text(_mapping(runtime_payload).get("updated_at")),
        "symbol_count": len(symbol_rows),
        "guard_active_symbol_count": guard_active_symbol_count,
        "requested_but_suppressed_symbol_count": requested_but_suppressed_symbol_count,
        "blanket_risk_duplicate_symbol_count": blanket_risk_duplicate_symbol_count,
        "relaxed_same_runtime_hint_symbol_count": relaxed_same_runtime_hint_symbol_count,
        "overlap_class_counts": overlap_class_counts,
        "source_presence_counts": source_presence_counts,
        "dominant_issue": dominant_issue,
        "recommended_next_step": recommended_next_step,
        "symbol_rows": symbol_rows,
    }


def build_state25_context_bridge_overlap_guard_audit(
    runtime_status_detail_path: str | Path | None = None,
) -> dict[str, Any]:
    runtime_payload = _load_runtime_status_detail(runtime_status_detail_path)
    return build_state25_context_bridge_overlap_guard_audit_from_runtime_payload(runtime_payload)


def render_state25_context_bridge_overlap_guard_audit_markdown(
    audit_payload: Mapping[str, Any] | None,
) -> str:
    payload = dict(audit_payload or {})
    lines = [
        "# State25 Context Bridge Overlap Guard Audit",
        "",
        f"- generated_at: {_text(payload.get('generated_at'))}",
        f"- runtime_updated_at: {_text(payload.get('runtime_updated_at'))}",
        f"- symbol_count: {int(payload.get('symbol_count') or 0)}",
        f"- guard_active_symbol_count: {int(payload.get('guard_active_symbol_count') or 0)}",
        f"- requested_but_suppressed_symbol_count: {int(payload.get('requested_but_suppressed_symbol_count') or 0)}",
        f"- blanket_risk_duplicate_symbol_count: {int(payload.get('blanket_risk_duplicate_symbol_count') or 0)}",
        f"- relaxed_same_runtime_hint_symbol_count: {int(payload.get('relaxed_same_runtime_hint_symbol_count') or 0)}",
        f"- dominant_issue: {_text(payload.get('dominant_issue'))}",
        f"- recommended_next_step: {_text(payload.get('recommended_next_step'))}",
        "",
        "## Source Presence",
    ]
    for source, count in sorted(dict(payload.get("source_presence_counts") or {}).items()):
        lines.append(f"- {source}: {int(count)}")
    lines.append("")
    lines.append("## Overlap Class Counts")
    for overlap_class, count in sorted(dict(payload.get("overlap_class_counts") or {}).items()):
        lines.append(f"- {overlap_class}: {int(count)}")
    lines.append("")
    lines.append("## Symbol Rows")
    for row in list(payload.get("symbol_rows") or []):
        lines.append(f"- {row.get('symbol')}: {_text(row.get('overlap_class'))} / requested {int(row.get('requested_weight_count') or 0)} / effective {int(row.get('effective_weight_count') or 0)} / suppressed {int(row.get('suppressed_weight_count') or 0)}")
        lines.append(f"  - context: {_text(row.get('context_bundle_summary_ko')) or '-'}")
        lines.append(f"  - overlap_sources: {', '.join(row.get('overlap_sources') or []) or '-'}")
        lines.append(f"  - bridge_payload_source: {_text(row.get('bridge_payload_source')) or '-'}")
        lines.append(f"  - overlap_guard_decision: {_text(row.get('overlap_guard_decision')) or '-'}")
        lines.append(f"  - blanket_risk_duplicate: {'yes' if row.get('blanket_risk_duplicate') else 'no'}")
        lines.append(f"  - recommended_next_action: {_text(row.get('recommended_next_action'))}")
    lines.append("")
    return "\n".join(lines)


def write_state25_context_bridge_overlap_guard_audit(
    runtime_status_detail_path: str | Path | None = None,
) -> dict[str, Any]:
    audit_payload = build_state25_context_bridge_overlap_guard_audit(runtime_status_detail_path)
    output_dir = _shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "state25_context_bridge_overlap_guard_audit_latest.json"
    md_path = output_dir / "state25_context_bridge_overlap_guard_audit_latest.md"
    json_path.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_state25_context_bridge_overlap_guard_audit_markdown(audit_payload),
        encoding="utf-8",
    )
    return audit_payload
