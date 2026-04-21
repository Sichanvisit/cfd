from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.services.session_bucket_helper import resolve_session_bucket_v1


SHOULD_HAVE_DONE_CANDIDATE_SUMMARY_VERSION = "should_have_done_candidate_summary_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _expected_direction_from_surface_row(row: Mapping[str, Any]) -> str:
    overlay_direction = _safe_text(row.get("directional_continuation_overlay_direction")).upper()
    if overlay_direction in {"UP", "DOWN", "NEUTRAL"}:
        return overlay_direction
    return "NEUTRAL"


def _expected_surface_from_row(row: Mapping[str, Any], expected_direction: str) -> str:
    event_kind = _safe_text(row.get("directional_continuation_overlay_event_kind_hint")).upper()
    if event_kind:
        return event_kind
    if expected_direction == "UP":
        return "BUY_WATCH"
    if expected_direction == "DOWN":
        return "SELL_WATCH"
    return "WAIT"


def _expected_continuation_from_row(row: Mapping[str, Any]) -> str:
    direction = _expected_direction_from_surface_row(row)
    if direction in {"UP", "DOWN"} and _safe_bool(row.get("directional_continuation_overlay_enabled")):
        return "CONTINUING"
    return "UNCLEAR"


def _expected_phase_from_row(row: Mapping[str, Any]) -> str:
    state = _safe_text(row.get("directional_continuation_overlay_selection_state")).upper()
    if state in {"LOW_ALIGNMENT", "DIRECTION_TIE"}:
        return "BOUNDARY"
    direction = _expected_direction_from_surface_row(row)
    if direction in {"UP", "DOWN"}:
        return "CONTINUATION"
    return "BOUNDARY"


def _candidate_confidence_from_row(row: Mapping[str, Any]) -> str:
    score = _safe_float(row.get("directional_continuation_overlay_score"), 0.0)
    if score >= 0.7:
        return "AUTO_HIGH"
    if score >= 0.5:
        return "AUTO_MEDIUM"
    return "AUTO_LOW"


def _build_surface_mismatch_candidates(latest_signal_by_symbol: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _mapping(raw)
        expected_direction = _expected_direction_from_surface_row(row)
        final_side = _safe_text(
            row.get("execution_diff_final_action_side")
            or _mapping(row.get("execution_action_diff_v1")).get("final_action_side")
        ).upper()
        if expected_direction not in {"UP", "DOWN"}:
            continue
        if (expected_direction == "UP" and final_side == "BUY") or (
            expected_direction == "DOWN" and final_side == "SELL"
        ):
            continue
        out.append(
            {
                "symbol": str(symbol),
                "time": _safe_text(row.get("timestamp") or row.get("time") or row.get("generated_at")),
                "session_bucket_v1": resolve_session_bucket_v1(
                    row.get("timestamp") or row.get("time") or row.get("generated_at")
                ),
                "candidate_source_v1": "AUTO_SURFACE_EXECUTION_MISMATCH",
                "expected_direction": expected_direction,
                "expected_continuation": _expected_continuation_from_row(row),
                "expected_phase_v1": _expected_phase_from_row(row),
                "expected_surface": _expected_surface_from_row(row, expected_direction),
                "annotation_confidence_v1": _candidate_confidence_from_row(row),
                "operator_note": "",
                "actual_final_action_side": final_side,
            }
        )
    return out


def _build_trace_promotion_candidates(ai_entry_traces: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in list(ai_entry_traces or []):
        row = _mapping(raw)
        promoted = _safe_text(row.get("execution_diff_promoted_action_side")).upper()
        final_side = _safe_text(row.get("execution_diff_final_action_side")).upper()
        if promoted not in {"BUY", "SELL"}:
            continue
        if promoted == final_side:
            continue
        expected_direction = "UP" if promoted == "BUY" else "DOWN"
        out.append(
            {
                "symbol": _safe_text(row.get("symbol")),
                "time": _safe_text(row.get("time")),
                "session_bucket_v1": resolve_session_bucket_v1(row.get("time")),
                "candidate_source_v1": "AUTO_PROMOTION_REVIEW",
                "expected_direction": expected_direction,
                "expected_continuation": "CONTINUING",
                "expected_phase_v1": "CONTINUATION",
                "expected_surface": "BUY_WATCH" if promoted == "BUY" else "SELL_WATCH",
                "annotation_confidence_v1": (
                    "AUTO_HIGH"
                    if _safe_text(row.get("execution_diff_promotion_suppressed_reason"))
                    in {"overlay_not_strong_enough", "probe_not_promoted", "guard_not_applied"}
                    else "AUTO_MEDIUM"
                ),
                "operator_note": "",
                "actual_final_action_side": final_side,
                "promotion_suppressed_reason": _safe_text(row.get("execution_diff_promotion_suppressed_reason")),
            }
        )
    return out


def build_should_have_done_candidate_summary(
    *,
    latest_signal_by_symbol: Mapping[str, Any] | None = None,
    ai_entry_traces: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    surface_candidates = _build_surface_mismatch_candidates(latest_signal_by_symbol or {})
    promotion_candidates = _build_trace_promotion_candidates(ai_entry_traces or [])
    candidates = surface_candidates + promotion_candidates

    confidence_count_summary: dict[str, int] = {}
    source_count_summary: dict[str, int] = {}
    session_count_summary: dict[str, int] = {}
    symbol_count_summary: dict[str, int] = {}
    for row in candidates:
        confidence = _safe_text(row.get("annotation_confidence_v1"))
        source = _safe_text(row.get("candidate_source_v1"))
        session_bucket = _safe_text(row.get("session_bucket_v1"))
        symbol = _safe_text(row.get("symbol"))
        confidence_count_summary[confidence] = int(confidence_count_summary.get(confidence, 0)) + 1
        source_count_summary[source] = int(source_count_summary.get(source, 0)) + 1
        session_count_summary[session_bucket] = int(session_count_summary.get(session_bucket, 0)) + 1
        symbol_count_summary[symbol] = int(symbol_count_summary.get(symbol, 0)) + 1

    status = "READY" if candidates else "HOLD"
    reasons = ["auto_candidates_available"] if candidates else ["no_should_have_done_candidates_yet"]
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": reasons,
        "candidate_count": int(len(candidates)),
        "auto_candidate_count": int(len(candidates)),
        "manual_candidate_count": 0,
        "confidence_count_summary": confidence_count_summary,
        "candidate_source_count_summary": source_count_summary,
        "candidate_count_by_session": session_count_summary,
        "candidate_count_by_symbol": symbol_count_summary,
    }
    return {
        "contract_version": SHOULD_HAVE_DONE_CANDIDATE_SUMMARY_VERSION,
        "summary": summary,
        "recent_candidate_rows": candidates[-20:],
    }


def render_should_have_done_candidate_summary_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Should-Have-Done Candidate Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(x) for x in list(summary.get('status_reasons') or []))}`",
        f"- candidate_count: `{int(summary.get('candidate_count', 0) or 0)}`",
        "",
        "## Candidate Count By Session",
        "",
    ]
    for bucket, count in dict(summary.get("candidate_count_by_session") or {}).items():
        lines.append(f"- `{bucket}`: {int(count or 0)}")
    lines.extend(["", "## Candidate Count By Source", ""])
    for source, count in dict(summary.get("candidate_source_count_summary") or {}).items():
        lines.append(f"- `{source}`: {int(count or 0)}")
    lines.extend(["", "## Recent Candidate Rows", ""])
    for row in list(payload.get("recent_candidate_rows") or [])[:10]:
        row_map = _mapping(row)
        lines.append(
            f"- `{row_map.get('time', '')}` | `{row_map.get('symbol', '')}` | "
            f"{row_map.get('candidate_source_v1', '')} | expected={row_map.get('expected_direction', '')}/"
            f"{row_map.get('expected_phase_v1', '')} | actual={row_map.get('actual_final_action_side', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_should_have_done_candidate_summary(
    *,
    latest_signal_by_symbol: Mapping[str, Any] | None = None,
    ai_entry_traces: Iterable[Mapping[str, Any]] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_should_have_done_candidate_summary(
        latest_signal_by_symbol=latest_signal_by_symbol,
        ai_entry_traces=ai_entry_traces,
    )
    json_path = output_dir / "should_have_done_candidate_summary_latest.json"
    md_path = output_dir / "should_have_done_candidate_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_should_have_done_candidate_summary_markdown(report))
    return report
