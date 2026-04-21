from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.session_bucket_helper import resolve_session_bucket_v1


SESSION_BIAS_SHADOW_CONTRACT_VERSION = "session_bias_shadow_contract_v1"
SESSION_BIAS_SHADOW_REPORT_VERSION = "session_bias_shadow_report_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_session_bias_shadow_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SESSION_BIAS_SHADOW_CONTRACT_VERSION,
        "status": "READY",
        "mode": "shadow_only",
        "description": (
            "Read-only session bias shadow layer. "
            "Evaluates whether session-aware bias would raise, lower, or keep continuation confidence "
            "without changing execution or state25."
        ),
        "fields": [
            "session_bias_candidate_state_v1",
            "session_bias_effect_v1",
            "session_bias_confidence_v1",
            "session_bias_reason_v1",
            "would_change_surface_v1",
            "would_change_execution_v1",
            "would_change_state25_v1",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _canonical_direction(row: Mapping[str, Any]) -> str:
    direction = _safe_text(row.get("canonical_direction_annotation_v1")).upper()
    if direction in {"UP", "DOWN", "NEUTRAL"}:
        return direction
    runtime_surface = _safe_text(row.get("canonical_runtime_surface_name_v1")).upper()
    if runtime_surface.startswith("BUY"):
        return "UP"
    if runtime_surface.startswith("SELL"):
        return "DOWN"
    return "NEUTRAL"


def _resolve_session_bucket(row: Mapping[str, Any]) -> str:
    bucket = _safe_text(row.get("canonical_session_bucket_v1") or row.get("session_bucket_v1"))
    if bucket:
        return bucket
    return resolve_session_bucket_v1(row.get("timestamp") or row.get("time") or row.get("generated_at"))


def _confidence_for_effect(effect: str, *, measured_count: int, direction_accuracy: float) -> str:
    if effect == "KEEP_NEUTRAL":
        return "LOW"
    if measured_count >= 40 and (direction_accuracy >= 0.60 or direction_accuracy <= 0.40):
        return "HIGH"
    if measured_count >= 20 and (direction_accuracy >= 0.55 or direction_accuracy <= 0.45):
        return "MEDIUM"
    return "LOW"


def build_session_bias_shadow_row_v1(
    row: Mapping[str, Any] | None,
    *,
    session_aware_annotation_accuracy_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _mapping(row)
    summary = _mapping(_mapping(session_aware_annotation_accuracy_report).get("summary"))
    session_bucket = _resolve_session_bucket(payload)
    measured_count = _safe_int(_mapping(summary.get("measured_count_by_session")).get(session_bucket), 0)
    direction_accuracy = _safe_float(
        _mapping(summary.get("direction_accuracy_by_session")).get(session_bucket),
        0.0,
    )
    significance = _mapping(summary.get("session_difference_significance"))
    significance_status = _safe_text(significance.get("status")).upper()
    canonical_direction = _canonical_direction(payload)
    runtime_surface = _safe_text(payload.get("canonical_runtime_surface_name_v1")).upper()
    alignment = _safe_text(payload.get("canonical_runtime_execution_alignment_v1")).upper()

    if measured_count < 20:
        candidate_state = "INSUFFICIENT_SAMPLE"
        effect = "KEEP_NEUTRAL"
        reason = "session_sample_below_minimum"
    elif significance_status not in {"SIGNIFICANT", "REFERENCE_ONLY"}:
        candidate_state = "NO_SESSION_EDGE"
        effect = "KEEP_NEUTRAL"
        reason = "session_gap_not_meaningful"
    elif canonical_direction not in {"UP", "DOWN"} or runtime_surface == "WAIT":
        candidate_state = "OBSERVE_ONLY"
        effect = "KEEP_NEUTRAL"
        reason = "no_canonical_directional_surface"
    elif direction_accuracy >= 0.55:
        candidate_state = "READY"
        effect = "RAISE_CONTINUATION_CONFIDENCE"
        reason = f"session_direction_accuracy_high::{session_bucket}::{direction_accuracy:.4f}"
    elif direction_accuracy <= 0.45:
        candidate_state = "READY"
        effect = "LOWER_CONTINUATION_CONFIDENCE"
        reason = f"session_direction_accuracy_low::{session_bucket}::{direction_accuracy:.4f}"
    else:
        candidate_state = "OBSERVE_ONLY"
        effect = "KEEP_NEUTRAL"
        reason = f"session_direction_accuracy_mid::{session_bucket}::{direction_accuracy:.4f}"

    would_change_surface = effect != "KEEP_NEUTRAL" and runtime_surface != "WAIT"
    would_change_execution = effect == "RAISE_CONTINUATION_CONFIDENCE" and alignment in {"DIVERGED", "WAITING"}
    would_change_state25 = effect != "KEEP_NEUTRAL"
    confidence = _confidence_for_effect(
        effect,
        measured_count=measured_count,
        direction_accuracy=direction_accuracy,
    )
    return {
        "contract_version": SESSION_BIAS_SHADOW_CONTRACT_VERSION,
        "session_bias_candidate_state_v1": candidate_state,
        "session_bias_effect_v1": effect,
        "session_bias_confidence_v1": confidence,
        "session_bias_reason_v1": reason,
        "session_bias_session_bucket_v1": session_bucket,
        "session_bias_direction_accuracy_v1": round(direction_accuracy, 4),
        "session_bias_measured_count_v1": measured_count,
        "session_bias_significance_status_v1": significance_status,
        "would_change_surface_v1": bool(would_change_surface),
        "would_change_execution_v1": bool(would_change_execution),
        "would_change_state25_v1": bool(would_change_state25),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def attach_session_bias_shadow_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    session_aware_annotation_accuracy_report: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(
            build_session_bias_shadow_row_v1(
                row,
                session_aware_annotation_accuracy_report=session_aware_annotation_accuracy_report,
            )
        )
        enriched[str(symbol)] = row
    return enriched


def build_session_bias_shadow_report_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    session_aware_annotation_accuracy_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows_by_symbol = attach_session_bias_shadow_fields_v1(
        latest_signal_by_symbol,
        session_aware_annotation_accuracy_report=session_aware_annotation_accuracy_report,
    )
    candidate_state_counts = Counter()
    effect_counts = Counter()
    session_counts = Counter()
    for row in rows_by_symbol.values():
        candidate_state_counts.update([_safe_text(row.get("session_bias_candidate_state_v1"))])
        effect_counts.update([_safe_text(row.get("session_bias_effect_v1"))])
        session_counts.update([_safe_text(row.get("session_bias_session_bucket_v1"))])
    any_ready = int(candidate_state_counts.get("READY", 0)) > 0
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["shadow_bias_candidates_available"] if any_ready else ["shadow_bias_observe_only"],
        "mode": "shadow_only",
        "symbol_count": int(len(rows_by_symbol)),
        "candidate_state_count_summary": dict(candidate_state_counts),
        "effect_count_summary": dict(effect_counts),
        "candidate_count_by_session": dict(session_counts),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "contract_version": SESSION_BIAS_SHADOW_REPORT_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_session_bias_shadow_report_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Session Bias Shadow Report",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(x) for x in list(summary.get('status_reasons') or []))}`",
        f"- symbol_count: `{_safe_int(summary.get('symbol_count'), 0)}`",
        "",
        "## Candidate State Count",
        "",
    ]
    for key, count in dict(summary.get("candidate_state_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Effect Count", ""])
    for key, count in dict(summary.get("effect_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: state={row.get('session_bias_candidate_state_v1', '')} | "
            f"effect={row.get('session_bias_effect_v1', '')} | "
            f"session={row.get('session_bias_session_bucket_v1', '')} | "
            f"would_change_execution={row.get('would_change_execution_v1', False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_session_bias_shadow_report_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    session_aware_annotation_accuracy_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_session_bias_shadow_report_v1(
        latest_signal_by_symbol,
        session_aware_annotation_accuracy_report=session_aware_annotation_accuracy_report,
    )
    json_path = output_dir / "session_bias_shadow_report_latest.json"
    md_path = output_dir / "session_bias_shadow_report_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_session_bias_shadow_report_markdown(report))
    return report
