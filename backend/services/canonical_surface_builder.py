from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


CANONICAL_SURFACE_CONTRACT_VERSION = "canonical_surface_contract_v1"
CANONICAL_SURFACE_SUMMARY_VERSION = "canonical_surface_summary_v1"
CANONICAL_SURFACE_PRIORITY_RULE_V1 = "phase>continuation>direction"
CANONICAL_RUNTIME_SURFACE_ENUM_V1 = (
    "BUY_WATCH",
    "SELL_WATCH",
    "BUY_PROBE",
    "SELL_PROBE",
    "BUY_READY",
    "SELL_READY",
    "WAIT",
)
CANONICAL_EXECUTION_SURFACE_ENUM_V1 = ("BUY_EXECUTION", "SELL_EXECUTION", "WAIT")
CANONICAL_ALIGNMENT_ENUM_V1 = ("MATCH", "DIVERGED", "WAITING")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_canonical_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": CANONICAL_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "priority_rule_v1": CANONICAL_SURFACE_PRIORITY_RULE_V1,
        "runtime_surface_enum_v1": list(CANONICAL_RUNTIME_SURFACE_ENUM_V1),
        "execution_surface_enum_v1": list(CANONICAL_EXECUTION_SURFACE_ENUM_V1),
        "alignment_enum_v1": list(CANONICAL_ALIGNMENT_ENUM_V1),
        "description": (
            "Read-only canonical surface contract shared by chart/runtime/execution comparison. "
            "Does not alter execution behavior."
        ),
    }


def _runtime_surface_name(row: Mapping[str, Any]) -> str:
    event_kind = _safe_text(row.get("directional_continuation_overlay_event_kind_hint")).upper()
    if event_kind in CANONICAL_RUNTIME_SURFACE_ENUM_V1:
        return event_kind
    overlay_direction = _safe_text(row.get("directional_continuation_overlay_direction")).upper()
    if _safe_bool(row.get("directional_continuation_overlay_enabled")):
        if overlay_direction == "UP":
            return "BUY_WATCH"
        if overlay_direction == "DOWN":
            return "SELL_WATCH"
    return "WAIT"


def _execution_surface_name(row: Mapping[str, Any]) -> str:
    final_side = _safe_text(
        row.get("execution_diff_final_action_side")
        or _mapping(row.get("execution_action_diff_v1")).get("final_action_side")
        or row.get("action")
    ).upper()
    if final_side == "BUY":
        return "BUY_EXECUTION"
    if final_side == "SELL":
        return "SELL_EXECUTION"
    return "WAIT"


def _direction_annotation(runtime_surface: str) -> str:
    if runtime_surface.startswith("BUY"):
        return "UP"
    if runtime_surface.startswith("SELL"):
        return "DOWN"
    return "NEUTRAL"


def _continuation_annotation(runtime_surface: str) -> str:
    if runtime_surface == "WAIT":
        return "UNCLEAR"
    return "CONTINUING"


def _phase_v1(row: Mapping[str, Any], runtime_surface: str) -> str:
    selection_state = _safe_text(row.get("directional_continuation_overlay_selection_state")).upper()
    if selection_state in {"LOW_ALIGNMENT", "DIRECTION_TIE"}:
        return "BOUNDARY"
    if _safe_bool(row.get("countertrend_continuation_enabled")) or _safe_text(
        row.get("countertrend_continuation_action")
    ):
        return "REVERSAL"
    if runtime_surface != "WAIT":
        return "CONTINUATION"
    return "BOUNDARY"


def _alignment_state(direction_annotation: str, execution_surface: str) -> str:
    if execution_surface == "WAIT" or direction_annotation == "NEUTRAL":
        return "WAITING"
    if direction_annotation == "UP" and execution_surface == "BUY_EXECUTION":
        return "MATCH"
    if direction_annotation == "DOWN" and execution_surface == "SELL_EXECUTION":
        return "MATCH"
    return "DIVERGED"


def build_canonical_surface_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    runtime_surface = _runtime_surface_name(payload)
    execution_surface = _execution_surface_name(payload)
    direction_annotation = _direction_annotation(runtime_surface)
    continuation_annotation = _continuation_annotation(runtime_surface)
    phase_v1 = _phase_v1(payload, runtime_surface)
    alignment_state = _alignment_state(direction_annotation, execution_surface)
    return {
        "contract_version": CANONICAL_SURFACE_CONTRACT_VERSION,
        "canonical_runtime_surface_name_v1": runtime_surface,
        "canonical_execution_surface_name_v1": execution_surface,
        "canonical_direction_annotation_v1": direction_annotation,
        "canonical_continuation_annotation_v1": continuation_annotation,
        "canonical_phase_v1": phase_v1,
        "canonical_session_bucket_v1": _safe_text(payload.get("session_bucket_v1")),
        "canonical_surface_priority_rule_v1": CANONICAL_SURFACE_PRIORITY_RULE_V1,
        "canonical_runtime_execution_alignment_v1": alignment_state,
    }


def attach_canonical_surface_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_canonical_surface_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_canonical_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_canonical_surface_fields_v1(latest_signal_by_symbol)
    runtime_surface_counts = Counter()
    execution_surface_counts = Counter()
    alignment_counts = Counter()
    phase_counts = Counter()
    direction_counts = Counter()
    for row in rows_by_symbol.values():
        runtime_surface_counts.update([_safe_text(row.get("canonical_runtime_surface_name_v1"))])
        execution_surface_counts.update([_safe_text(row.get("canonical_execution_surface_name_v1"))])
        alignment_counts.update([_safe_text(row.get("canonical_runtime_execution_alignment_v1"))])
        phase_counts.update([_safe_text(row.get("canonical_phase_v1"))])
        direction_counts.update([_safe_text(row.get("canonical_direction_annotation_v1"))])
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["canonical_surface_available"] if rows_by_symbol else ["no_runtime_rows"],
        "symbol_count": int(len(rows_by_symbol)),
        "runtime_surface_count_summary": dict(runtime_surface_counts),
        "execution_surface_count_summary": dict(execution_surface_counts),
        "alignment_count_summary": dict(alignment_counts),
        "phase_count_summary": dict(phase_counts),
        "direction_count_summary": dict(direction_counts),
    }
    return {
        "contract_version": CANONICAL_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_canonical_surface_summary_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Canonical Surface Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        "",
        "## Runtime Surface Count",
        "",
    ]
    for key, count in dict(summary.get("runtime_surface_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Execution Surface Count", ""])
    for key, count in dict(summary.get("execution_surface_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Alignment Count", ""])
    for key, count in dict(summary.get("alignment_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: runtime={row.get('canonical_runtime_surface_name_v1', '')} | "
            f"execution={row.get('canonical_execution_surface_name_v1', '')} | "
            f"phase={row.get('canonical_phase_v1', '')} | "
            f"alignment={row.get('canonical_runtime_execution_alignment_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_canonical_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_canonical_surface_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "canonical_surface_summary_latest.json"
    md_path = output_dir / "canonical_surface_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_canonical_surface_summary_markdown(report))
    return report
