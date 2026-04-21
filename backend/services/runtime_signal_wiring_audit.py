from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


RUNTIME_SIGNAL_WIRING_AUDIT_VERSION = "runtime_signal_wiring_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _default_flow_history_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return bool(value)
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_flow_entry(payload: Any) -> dict[str, Any]:
    rows: list[Any] = []
    if isinstance(payload, list):
        rows = list(payload)
    elif isinstance(payload, Mapping):
        for key in ("history", "rows", "events", "items"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                rows = list(candidate)
                break
    for raw in reversed(rows):
        row = _mapping(raw)
        if row:
            return {
                "event_kind": _text(row.get("event_kind") or row.get("kind") or row.get("action")),
                "side": _text(row.get("side")),
                "reason": _text(row.get("reason") or row.get("display_reason")),
                "time": _text(row.get("time") or row.get("timestamp") or row.get("ts")),
            }
    return {}


def _active_overlay_present(row: Mapping[str, Any]) -> bool:
    payload = _mapping(row)
    overlay = _mapping(payload.get("directional_continuation_overlay_v1"))
    return bool(
        _truthy(payload.get("directional_continuation_overlay_enabled"))
        or _truthy(overlay.get("overlay_enabled"))
    )


def _resolve_runtime_row_flow_event(row: Mapping[str, Any], *, symbol: str) -> dict[str, Any]:
    payload = _mapping(row)
    if not payload:
        return {}
    try:
        from backend.trading.chart_painter import Painter

        if Painter._consumer_check_hidden_flow_suppressed(payload):
            overlay = _mapping(payload.get("directional_continuation_overlay_v1"))
            selection_state = _text(
                payload.get("directional_continuation_overlay_selection_state")
                or overlay.get("overlay_selection_state")
            ).upper()
            if selection_state not in {
                "LOW_ALIGNMENT",
                "DIRECTION_TIE",
                "NO_DIRECTIONAL_CANDIDATE",
                "NO_CANDIDATE",
            }:
                return {
                    "event_kind": "",
                    "side": "",
                    "reason": "",
                    "source": "SUPPRESSED",
                }
            return {
                "event_kind": "WAIT",
                "side": "",
                "reason": _text(
                    payload.get("action_none_reason")
                    or payload.get("consumer_check_reason")
                    or payload.get("observe_reason")
                    or "directional_signal_unresolved"
                ),
                "source": "SUPPRESSED_UNRESOLVED_WAIT",
            }

        event_kind, side, reason = Painter._resolve_flow_event_kind(symbol, payload)
        return {
            "event_kind": _text(event_kind).upper(),
            "side": _text(side).upper(),
            "reason": _text(reason),
            "source": "CHART_PAINTER_RESOLUTION",
        }
    except Exception as exc:
        return {
            "event_kind": "",
            "side": "",
            "reason": _text(exc),
            "source": "RESOLUTION_ERROR",
        }


def _resolve_runtime_row_flow_signature(row: Mapping[str, Any]) -> str:
    payload = _mapping(row)
    if not payload:
        return ""
    try:
        from backend.trading.chart_painter import Painter

        return _text(Painter._flow_event_signature(payload))
    except Exception:
        return ""


def _flow_history_status(row: Mapping[str, Any], *, symbol: str, flow_history_dir: Path) -> dict[str, Any]:
    flow_path = flow_history_dir / f"{symbol}_flow_history.json"
    row_event_kind_hint = _text(
        row.get("chart_event_kind_hint") or row.get("directional_continuation_overlay_event_kind_hint")
    ).upper()
    resolved_event = _resolve_runtime_row_flow_event(row, symbol=symbol)
    row_resolved_event_kind = _text(resolved_event.get("event_kind")).upper()
    row_event_kind_for_sync = row_event_kind_hint or row_resolved_event_kind
    row_flow_event_signature = _resolve_runtime_row_flow_signature(row)
    latest_event = {}
    flow_history_payload = None
    if flow_path.exists():
        flow_history_payload = _load_json(flow_path)
        latest_event = _latest_flow_entry(flow_history_payload)
    flow_history_last_signature = (
        _text(_mapping(flow_history_payload).get("last_signature"))
        if isinstance(flow_history_payload, Mapping)
        else ""
    )
    flow_event_kind = _text(latest_event.get("event_kind")).upper()
    if row_event_kind_for_sync and flow_event_kind:
        if row_event_kind_for_sync == flow_event_kind:
            sync_state = "MATCH"
        elif row_flow_event_signature and flow_history_last_signature == row_flow_event_signature:
            sync_state = "SIGNATURE_MATCH_EVENT_COMPACTED"
        elif row_flow_event_signature and flow_history_last_signature and flow_history_last_signature != row_flow_event_signature:
            sync_state = "PENDING_SYNC"
        else:
            sync_state = "MISMATCH"
    elif row_event_kind_for_sync and not flow_event_kind:
        sync_state = "FLOW_MISSING"
    elif not row_event_kind_for_sync and flow_event_kind:
        sync_state = "ROW_MISSING"
    else:
        sync_state = "NO_SIGNAL"
    return {
        "flow_history_path": str(flow_path),
        "flow_history_exists": bool(flow_path.exists()),
        "row_event_kind_hint": row_event_kind_hint,
        "row_resolved_event_kind": row_resolved_event_kind,
        "row_resolved_event_side": _text(resolved_event.get("side")).upper(),
        "row_resolved_event_reason": _text(resolved_event.get("reason")),
        "row_flow_event_resolution_source": _text(resolved_event.get("source")),
        "row_event_kind_for_sync": row_event_kind_for_sync,
        "row_flow_event_signature": row_flow_event_signature,
        "flow_history_last_signature": flow_history_last_signature,
        "flow_history_event_kind": flow_event_kind,
        "flow_history_event_reason": _text(latest_event.get("reason")),
        "flow_history_sync_state": sync_state,
    }


def _row_accuracy_surface_status(row: Mapping[str, Any], accuracy_report: Mapping[str, Any] | None) -> dict[str, Any]:
    row_direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    row_symbol = _text(row.get("symbol")).upper()
    summary_map = _mapping(_mapping(accuracy_report).get("symbol_direction_primary_summary"))
    summary_key = f"{row_symbol}|{row_direction}" if row_symbol and row_direction else ""
    summary_row = _mapping(summary_map.get(summary_key))
    sample_count = int(row.get("directional_continuation_accuracy_sample_count", 0) or 0)
    surface_present = bool(
        row.get("directional_continuation_accuracy_horizon_bars")
        or row.get("directional_continuation_accuracy_last_state")
        or sample_count > 0
    )
    return {
        "accuracy_surface_present": surface_present,
        "accuracy_summary_present": bool(summary_row),
        "accuracy_horizon_bars": int(row.get("directional_continuation_accuracy_horizon_bars", 0) or 0),
        "accuracy_sample_count": sample_count,
        "accuracy_measured_count": int(row.get("directional_continuation_accuracy_measured_count", 0) or 0),
        "accuracy_correct_rate": round(
            _safe_float(row.get("directional_continuation_accuracy_correct_rate"), 0.0),
            4,
        ),
        "accuracy_last_state": _text(row.get("directional_continuation_accuracy_last_state")),
    }


def _row_execution_diff_status(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = _mapping(row.get("execution_action_diff_v1"))
    flat_original = _text(row.get("execution_diff_original_action_side"))
    flat_final = _text(row.get("execution_diff_final_action_side"))
    nested_original = _text(nested.get("original_action_side"))
    nested_final = _text(nested.get("final_action_side"))
    return {
        "execution_diff_flat_present": bool(flat_original or flat_final),
        "execution_diff_nested_present": bool(nested),
        "execution_diff_surface_complete": bool((flat_original or nested_original) and (flat_final or nested_final)),
        "execution_diff_original_action_side": flat_original or nested_original,
        "execution_diff_guarded_action_side": _text(row.get("execution_diff_guarded_action_side") or nested.get("guarded_action_side")),
        "execution_diff_promoted_action_side": _text(row.get("execution_diff_promoted_action_side") or nested.get("promoted_action_side")),
        "execution_diff_final_action_side": flat_final or nested_final,
        "execution_diff_changed": bool(
            row.get("execution_diff_changed", nested.get("action_changed", False))
        ),
    }


def build_runtime_signal_wiring_audit(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    ai_entry_traces: list[Mapping[str, Any]] | None = None,
    accuracy_report: Mapping[str, Any] | None = None,
    flow_history_dir: str | Path | None = None,
) -> dict[str, Any]:
    rows = {
        _text(symbol).upper(): _mapping(row)
        for symbol, row in dict(latest_signal_by_symbol or {}).items()
        if _text(symbol) and isinstance(row, Mapping)
    }
    traces = [_mapping(row) for row in list(ai_entry_traces or []) if isinstance(row, Mapping)]
    resolved_flow_dir = Path(flow_history_dir) if flow_history_dir is not None else _default_flow_history_dir()
    per_symbol: dict[str, dict[str, Any]] = {}
    overlay_present_count = 0
    execution_diff_surface_count = 0
    accuracy_surface_count = 0
    flow_sync_match_count = 0
    flow_signature_match_count = 0
    flow_pending_sync_count = 0
    flow_mismatch_count = 0
    for symbol, row in rows.items():
        overlay_present = _active_overlay_present(row)
        if overlay_present:
            overlay_present_count += 1
        execution_status = _row_execution_diff_status(row)
        if execution_status["execution_diff_surface_complete"]:
            execution_diff_surface_count += 1
        accuracy_status = _row_accuracy_surface_status(row, accuracy_report)
        if accuracy_status["accuracy_surface_present"]:
            accuracy_surface_count += 1
        flow_status = _flow_history_status(row, symbol=symbol, flow_history_dir=resolved_flow_dir)
        if flow_status["flow_history_sync_state"] in {"MATCH", "SIGNATURE_MATCH_EVENT_COMPACTED"}:
            flow_sync_match_count += 1
        if flow_status["flow_history_sync_state"] == "SIGNATURE_MATCH_EVENT_COMPACTED":
            flow_signature_match_count += 1
        if flow_status["flow_history_sync_state"] == "PENDING_SYNC":
            flow_pending_sync_count += 1
        if flow_status["flow_history_sync_state"] == "MISMATCH":
            flow_mismatch_count += 1
        per_symbol[symbol] = {
            "symbol": symbol,
            "overlay_enabled": bool(overlay_present),
            "overlay_direction": _text(row.get("directional_continuation_overlay_direction")).upper(),
            "overlay_event_kind_hint": _text(row.get("directional_continuation_overlay_event_kind_hint")),
            **execution_status,
            **accuracy_status,
            **flow_status,
        }

    ai_trace_execution_diff_count = sum(
        1
        for row in traces
        if _text(row.get("execution_diff_original_action_side"))
        or _text(row.get("execution_diff_final_action_side"))
    )
    accuracy_summary = _mapping(_mapping(accuracy_report).get("summary"))
    summary = {
        "generated_at": _now_iso(),
        "symbol_count": int(len(per_symbol)),
        "overlay_present_count": int(overlay_present_count),
        "execution_diff_surface_count": int(execution_diff_surface_count),
        "accuracy_surface_count": int(accuracy_surface_count),
        "flow_sync_match_count": int(flow_sync_match_count),
        "flow_signature_match_count": int(flow_signature_match_count),
        "flow_pending_sync_count": int(flow_pending_sync_count),
        "flow_mismatch_count": int(flow_mismatch_count),
        "ai_entry_trace_count": int(len(traces)),
        "ai_entry_trace_execution_diff_count": int(ai_trace_execution_diff_count),
        "primary_accuracy_measured_count": int(accuracy_summary.get("primary_measured_count", 0) or 0),
        "primary_accuracy_correct_rate": round(
            _safe_float(accuracy_summary.get("primary_correct_rate"), 0.0),
            4,
        ),
    }
    return {
        "contract_version": RUNTIME_SIGNAL_WIRING_AUDIT_VERSION,
        "summary": summary,
        "per_symbol": per_symbol,
    }


def render_runtime_signal_wiring_audit_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    per_symbol = _mapping(payload.get("per_symbol"))
    lines = [
        "# Runtime Signal Wiring Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- overlay_present_count: `{int(summary.get('overlay_present_count', 0) or 0)}`",
        f"- execution_diff_surface_count: `{int(summary.get('execution_diff_surface_count', 0) or 0)}`",
        f"- accuracy_surface_count: `{int(summary.get('accuracy_surface_count', 0) or 0)}`",
        f"- flow_sync_match_count: `{int(summary.get('flow_sync_match_count', 0) or 0)}`",
        f"- flow_signature_match_count: `{int(summary.get('flow_signature_match_count', 0) or 0)}`",
        f"- flow_pending_sync_count: `{int(summary.get('flow_pending_sync_count', 0) or 0)}`",
        f"- flow_mismatch_count: `{int(summary.get('flow_mismatch_count', 0) or 0)}`",
        f"- ai_entry_trace_count: `{int(summary.get('ai_entry_trace_count', 0) or 0)}`",
        f"- ai_entry_trace_execution_diff_count: `{int(summary.get('ai_entry_trace_execution_diff_count', 0) or 0)}`",
        f"- primary_accuracy_measured_count: `{int(summary.get('primary_accuracy_measured_count', 0) or 0)}`",
        f"- primary_accuracy_correct_rate: `{_safe_float(summary.get('primary_accuracy_correct_rate'), 0.0):.4f}`",
        "",
        "## Per Symbol",
        "",
    ]
    if not per_symbol:
        lines.append("- none")
    for symbol in sorted(per_symbol):
        row = _mapping(per_symbol.get(symbol))
        lines.append(
            f"- `{symbol}`: overlay={row.get('overlay_direction','')}/{row.get('overlay_event_kind_hint','')} "
            f"| exec={row.get('execution_diff_original_action_side','')}->{row.get('execution_diff_final_action_side','')} "
            f"| accuracy={_safe_float(row.get('accuracy_correct_rate'), 0.0):.4f} "
            f"| flow_sync={row.get('flow_history_sync_state','')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_runtime_signal_wiring_audit(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    ai_entry_traces: list[Mapping[str, Any]] | None = None,
    accuracy_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
    flow_history_dir: str | Path | None = None,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    report = build_runtime_signal_wiring_audit(
        latest_signal_by_symbol,
        ai_entry_traces=ai_entry_traces,
        accuracy_report=accuracy_report,
        flow_history_dir=flow_history_dir,
    )
    if not write_artifacts or int(_mapping(report.get("summary")).get("symbol_count", 0) or 0) <= 0:
        report["artifact_paths"] = {}
        return report
    resolved_output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    json_path = resolved_output_dir / "runtime_signal_wiring_audit_latest.json"
    md_path = resolved_output_dir / "runtime_signal_wiring_audit_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_runtime_signal_wiring_audit_markdown(report))
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    return report
