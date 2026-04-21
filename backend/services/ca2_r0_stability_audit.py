from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


CA2_R0_STABILITY_AUDIT_VERSION = "ca2_r0_stability_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_rate(numerator: int, denominator: int) -> float:
    denom = int(denominator or 0)
    if denom <= 0:
        return 0.0
    return float(numerator) / float(denom)


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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _summary_from_previous_artifact(path: Path) -> dict[str, Any]:
    payload = _mapping(_load_json(path))
    return _mapping(payload.get("summary"))


def build_ca2_r0_stability_audit(
    runtime_signal_wiring_audit: Mapping[str, Any] | None,
    *,
    accuracy_report: Mapping[str, Any] | None = None,
    previous_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wiring_summary = _mapping(_mapping(runtime_signal_wiring_audit).get("summary"))
    accuracy_summary = _mapping(_mapping(accuracy_report).get("summary"))
    previous = _mapping(previous_summary)

    symbol_count = _safe_int(wiring_summary.get("symbol_count"), 0)
    execution_diff_surface_count = _safe_int(wiring_summary.get("execution_diff_surface_count"), 0)
    flow_sync_match_count = _safe_int(wiring_summary.get("flow_sync_match_count"), 0)
    ai_entry_trace_count = _safe_int(wiring_summary.get("ai_entry_trace_count"), 0)
    ai_entry_trace_execution_diff_count = _safe_int(
        wiring_summary.get("ai_entry_trace_execution_diff_count"),
        0,
    )
    primary_measured_count = _safe_int(accuracy_summary.get("primary_measured_count"), 0)
    primary_correct_rate = round(_safe_float(accuracy_summary.get("primary_correct_rate"), 0.0), 4)
    resolved_observation_count = _safe_int(accuracy_summary.get("resolved_observation_count"), 0)

    previous_primary_measured_count = _safe_int(previous.get("primary_measured_count"), 0)
    previous_resolved_observation_count = _safe_int(previous.get("resolved_observation_count"), 0)
    previous_execution_diff_surface_count = _safe_int(previous.get("execution_diff_surface_count"), 0)
    previous_flow_sync_match_count = _safe_int(previous.get("flow_sync_match_count"), 0)
    first_snapshot = not bool(previous)

    primary_measured_count_delta = primary_measured_count - previous_primary_measured_count
    resolved_observation_count_delta = resolved_observation_count - previous_resolved_observation_count
    execution_diff_surface_count_delta = execution_diff_surface_count - previous_execution_diff_surface_count
    flow_sync_match_count_delta = flow_sync_match_count - previous_flow_sync_match_count

    execution_diff_surface_ratio = round(
        _safe_rate(execution_diff_surface_count, symbol_count),
        4,
    )
    flow_sync_match_ratio = round(
        _safe_rate(flow_sync_match_count, symbol_count),
        4,
    )

    blocked_reasons: list[str] = []
    hold_reasons: list[str] = []

    if symbol_count <= 0:
        blocked_reasons.append("symbol_rows_missing")
    if execution_diff_surface_count <= 0 and ai_entry_trace_execution_diff_count <= 0:
        blocked_reasons.append("execution_diff_surface_missing")
    if flow_sync_match_count <= 0 and symbol_count > 0:
        blocked_reasons.append("flow_sync_missing")
    if primary_measured_count <= 0:
        blocked_reasons.append("accuracy_not_accumulating")
    if not first_snapshot and primary_measured_count_delta < 0:
        blocked_reasons.append("primary_measured_regressed")
    if not first_snapshot and resolved_observation_count_delta < 0:
        blocked_reasons.append("resolved_observation_regressed")

    if not blocked_reasons:
        if first_snapshot:
            hold_reasons.append("first_snapshot")
        if symbol_count > 0 and execution_diff_surface_count < symbol_count:
            hold_reasons.append("execution_diff_surface_partial")
        if symbol_count > 0 and flow_sync_match_count < symbol_count:
            hold_reasons.append("flow_sync_partial")
        if not first_snapshot and primary_measured_count_delta == 0:
            hold_reasons.append("primary_measured_flat")
        if not first_snapshot and resolved_observation_count_delta == 0:
            hold_reasons.append("resolved_observation_flat")

    if blocked_reasons:
        status = "BLOCKED"
        reasons = list(blocked_reasons)
    elif hold_reasons:
        status = "HOLD"
        reasons = list(hold_reasons)
    else:
        status = "READY"
        reasons = ["stable_accumulating"]

    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": reasons,
        "first_snapshot": bool(first_snapshot),
        "symbol_count": int(symbol_count),
        "execution_diff_surface_count": int(execution_diff_surface_count),
        "flow_sync_match_count": int(flow_sync_match_count),
        "ai_entry_trace_count": int(ai_entry_trace_count),
        "ai_entry_trace_execution_diff_count": int(ai_entry_trace_execution_diff_count),
        "execution_diff_surface_ratio": float(execution_diff_surface_ratio),
        "flow_sync_match_ratio": float(flow_sync_match_ratio),
        "primary_measured_count": int(primary_measured_count),
        "primary_correct_rate": float(primary_correct_rate),
        "resolved_observation_count": int(resolved_observation_count),
        "primary_measured_count_delta": int(primary_measured_count_delta),
        "resolved_observation_count_delta": int(resolved_observation_count_delta),
        "execution_diff_surface_count_delta": int(execution_diff_surface_count_delta),
        "flow_sync_match_count_delta": int(flow_sync_match_count_delta),
    }
    return {
        "contract_version": CA2_R0_STABILITY_AUDIT_VERSION,
        "summary": summary,
        "inputs": {
            "runtime_signal_wiring_audit_summary": wiring_summary,
            "directional_continuation_accuracy_summary": accuracy_summary,
        },
    }


def render_ca2_r0_stability_audit_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    reasons = list(summary.get("status_reasons") or [])
    lines = [
        "# CA2 R0 Stability Audit",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(item) for item in reasons)}`",
        f"- first_snapshot: `{bool(summary.get('first_snapshot', False))}`",
        f"- symbol_count: `{_safe_int(summary.get('symbol_count'), 0)}`",
        f"- execution_diff_surface_count: `{_safe_int(summary.get('execution_diff_surface_count'), 0)}`",
        f"- flow_sync_match_count: `{_safe_int(summary.get('flow_sync_match_count'), 0)}`",
        f"- execution_diff_surface_ratio: `{_safe_float(summary.get('execution_diff_surface_ratio'), 0.0):.4f}`",
        f"- flow_sync_match_ratio: `{_safe_float(summary.get('flow_sync_match_ratio'), 0.0):.4f}`",
        f"- primary_measured_count: `{_safe_int(summary.get('primary_measured_count'), 0)}`",
        f"- primary_correct_rate: `{_safe_float(summary.get('primary_correct_rate'), 0.0):.4f}`",
        f"- resolved_observation_count: `{_safe_int(summary.get('resolved_observation_count'), 0)}`",
        "",
        "## Deltas",
        "",
        f"- primary_measured_count_delta: `{_safe_int(summary.get('primary_measured_count_delta'), 0)}`",
        f"- resolved_observation_count_delta: `{_safe_int(summary.get('resolved_observation_count_delta'), 0)}`",
        f"- execution_diff_surface_count_delta: `{_safe_int(summary.get('execution_diff_surface_count_delta'), 0)}`",
        f"- flow_sync_match_count_delta: `{_safe_int(summary.get('flow_sync_match_count_delta'), 0)}`",
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def generate_and_write_ca2_r0_stability_audit(
    runtime_signal_wiring_audit: Mapping[str, Any] | None,
    *,
    accuracy_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved_output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    json_path = resolved_output_dir / "ca2_r0_stability_latest.json"
    md_path = resolved_output_dir / "ca2_r0_stability_latest.md"
    previous_summary = _summary_from_previous_artifact(json_path) if json_path.exists() else {}
    report = build_ca2_r0_stability_audit(
        runtime_signal_wiring_audit,
        accuracy_report=accuracy_report,
        previous_summary=previous_summary,
    )
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_ca2_r0_stability_audit_markdown(report))
    return report
