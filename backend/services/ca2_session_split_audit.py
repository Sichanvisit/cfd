from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.services.session_bucket_helper import (
    SESSION_BUCKET_ENUM_V1,
    resolve_session_bucket_v1,
)


CA2_SESSION_SPLIT_AUDIT_VERSION = "ca2_session_split_audit_v1"
PRIMARY_HORIZON_BARS = 20
MIN_SIGNIFICANCE_SAMPLE = 20


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _default_accuracy_state_path() -> Path:
    return _default_shadow_auto_dir() / "directional_continuation_accuracy_tracker_state.json"


def _default_entry_decision_detail_path() -> Path:
    return _repo_root() / "data" / "trades" / "entry_decisions.detail.jsonl"


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
    return round(float(numerator) / float(denom), 4)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _coerce_bucket_counts() -> dict[str, dict[str, Any]]:
    return {
        bucket: {
            "session_bucket": bucket,
            "sample_count": 0,
            "measured_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "correct_rate": 0.0,
        }
        for bucket in SESSION_BUCKET_ENUM_V1
    }


def _resolve_session_from_timestamp(value: Any) -> str:
    try:
        return resolve_session_bucket_v1(value)
    except Exception:
        return ""


def _build_accuracy_by_session(
    resolved_rows: Iterable[Mapping[str, Any]],
    *,
    primary_horizon_bars: int,
) -> dict[str, dict[str, Any]]:
    summary = _coerce_bucket_counts()
    for raw in list(resolved_rows or []):
        row = _mapping(raw)
        if _safe_int(row.get("horizon_bars"), 0) != int(primary_horizon_bars):
            continue
        session_bucket = _resolve_session_from_timestamp(row.get("observed_at") or row.get("evaluated_at"))
        if session_bucket not in summary:
            continue
        bucket = summary[session_bucket]
        bucket["sample_count"] = int(bucket["sample_count"]) + 1
        state = str(row.get("evaluation_state", "") or "").upper()
        if state == "CORRECT":
            bucket["measured_count"] = int(bucket["measured_count"]) + 1
            bucket["correct_count"] = int(bucket["correct_count"]) + 1
        elif state == "INCORRECT":
            bucket["measured_count"] = int(bucket["measured_count"]) + 1
            bucket["incorrect_count"] = int(bucket["incorrect_count"]) + 1
    for bucket in summary.values():
        bucket["correct_rate"] = _safe_rate(
            int(bucket.get("correct_count", 0)),
            int(bucket.get("measured_count", 0)),
        )
    return summary


def _session_gap_significance(accuracy_by_session: Mapping[str, Any]) -> dict[str, Any]:
    rows = {
        bucket: _mapping(value)
        for bucket, value in dict(accuracy_by_session or {}).items()
        if _safe_int(_mapping(value).get("measured_count"), 0) >= MIN_SIGNIFICANCE_SAMPLE
    }
    if len(rows) < 2:
        return {
            "status": "INSUFFICIENT_SAMPLE",
            "max_gap_pct_points": 0.0,
            "pair": "",
            "sessions_with_min_sample_count": int(len(rows)),
        }

    best_pair = ""
    best_gap = 0.0
    buckets = sorted(rows)
    for idx, left in enumerate(buckets):
        for right in buckets[idx + 1 :]:
            left_rate = _safe_float(rows[left].get("correct_rate"), 0.0)
            right_rate = _safe_float(rows[right].get("correct_rate"), 0.0)
            gap = abs(left_rate - right_rate) * 100.0
            if gap > best_gap:
                best_gap = gap
                best_pair = f"{left}|{right}"

    if best_gap >= 15.0:
        status = "SIGNIFICANT"
    elif best_gap >= 10.0:
        status = "REFERENCE_ONLY"
    else:
        status = "NOT_SIGNIFICANT"
    return {
        "status": status,
        "max_gap_pct_points": round(best_gap, 2),
        "pair": best_pair,
        "sessions_with_min_sample_count": int(len(rows)),
    }


def _tail_jsonl_payloads(path: Path, *, limit: int = 800) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: deque[dict[str, Any]] = deque(maxlen=max(int(limit), 1))
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = str(line or "").strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except Exception:
                continue
            items.append(_mapping(payload.get("payload")))
    return [row for row in items if row]


def _build_guard_trace_by_session(payload_rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    summary = {
        bucket: {
            "session_bucket": bucket,
            "trace_count": 0,
            "guard_applied_count": 0,
            "guard_helpful_rate": None,
            "data_status": "INSUFFICIENT_HINDSIGHT",
        }
        for bucket in SESSION_BUCKET_ENUM_V1
    }
    for raw in list(payload_rows or []):
        row = _mapping(raw)
        session_bucket = _resolve_session_from_timestamp(row.get("time") or row.get("timestamp"))
        if session_bucket not in summary:
            continue
        bucket = summary[session_bucket]
        bucket["trace_count"] = int(bucket["trace_count"]) + 1
        if bool(row.get("active_action_conflict_guard_applied")):
            bucket["guard_applied_count"] = int(bucket["guard_applied_count"]) + 1
    return summary


def _build_promotion_trace_by_session(ai_entry_traces: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    summary = {
        bucket: {
            "session_bucket": bucket,
            "trace_count": 0,
            "promotion_active_count": 0,
            "promotion_win_rate": None,
            "data_status": "INSUFFICIENT_HINDSIGHT",
        }
        for bucket in SESSION_BUCKET_ENUM_V1
    }
    for raw in list(ai_entry_traces or []):
        row = _mapping(raw)
        session_bucket = _resolve_session_from_timestamp(row.get("time") or row.get("timestamp"))
        if session_bucket not in summary:
            continue
        bucket = summary[session_bucket]
        bucket["trace_count"] = int(bucket["trace_count"]) + 1
        if bool(row.get("execution_diff_promotion_active")):
            bucket["promotion_active_count"] = int(bucket["promotion_active_count"]) + 1
    return summary


def build_ca2_session_split_audit(
    *,
    accuracy_state_payload: Mapping[str, Any] | None = None,
    entry_payload_rows: Iterable[Mapping[str, Any]] | None = None,
    ai_entry_traces: Iterable[Mapping[str, Any]] | None = None,
    primary_horizon_bars: int = PRIMARY_HORIZON_BARS,
) -> dict[str, Any]:
    accuracy_state = _mapping(accuracy_state_payload)
    resolved_rows = [
        _mapping(row)
        for row in list(accuracy_state.get("resolved_observations") or [])
        if isinstance(row, Mapping)
    ]
    accuracy_by_session = _build_accuracy_by_session(
        resolved_rows,
        primary_horizon_bars=int(primary_horizon_bars),
    )
    significance = _session_gap_significance(accuracy_by_session)
    guard_by_session = _build_guard_trace_by_session(entry_payload_rows or [])
    promotion_by_session = _build_promotion_trace_by_session(ai_entry_traces or [])

    correct_rate_by_session = {
        bucket: round(_safe_float(row.get("correct_rate"), 0.0), 4)
        for bucket, row in accuracy_by_session.items()
    }
    measured_count_by_session = {
        bucket: int(_safe_int(row.get("measured_count"), 0))
        for bucket, row in accuracy_by_session.items()
    }
    guard_helpful_rate_by_session = {
        bucket: _mapping(row).get("guard_helpful_rate")
        for bucket, row in guard_by_session.items()
    }
    promotion_win_rate_by_session = {
        bucket: _mapping(row).get("promotion_win_rate")
        for bucket, row in promotion_by_session.items()
    }

    non_zero_sessions = sum(1 for value in measured_count_by_session.values() if int(value or 0) > 0)
    if significance.get("status") == "INSUFFICIENT_SAMPLE" and non_zero_sessions > 0:
        status = "HOLD"
        reasons = ["session_samples_present_but_insufficient"]
    elif non_zero_sessions <= 0:
        status = "BLOCKED"
        reasons = ["session_accuracy_missing"]
    else:
        status = "READY"
        reasons = [str(significance.get("status", "") or "session_split_ready").lower()]

    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": reasons,
        "primary_horizon_bars": int(primary_horizon_bars),
        "correct_rate_by_session": correct_rate_by_session,
        "measured_count_by_session": measured_count_by_session,
        "guard_helpful_rate_by_session": guard_helpful_rate_by_session,
        "promotion_win_rate_by_session": promotion_win_rate_by_session,
        "session_difference_significance": significance,
    }
    return {
        "contract_version": CA2_SESSION_SPLIT_AUDIT_VERSION,
        "summary": summary,
        "accuracy_by_session": accuracy_by_session,
        "guard_trace_by_session": guard_by_session,
        "promotion_trace_by_session": promotion_by_session,
    }


def render_ca2_session_split_audit_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    significance = _mapping(summary.get("session_difference_significance"))
    lines = [
        "# CA2 Session Split Audit",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(x) for x in list(summary.get('status_reasons') or []))}`",
        f"- primary_horizon_bars: `{_safe_int(summary.get('primary_horizon_bars'), PRIMARY_HORIZON_BARS)}`",
        f"- significance: `{significance.get('status', '')}`",
        f"- significance_pair: `{significance.get('pair', '')}`",
        f"- max_gap_pct_points: `{_safe_float(significance.get('max_gap_pct_points'), 0.0):.2f}`",
        "",
        "## Accuracy By Session",
        "",
    ]
    for bucket in SESSION_BUCKET_ENUM_V1:
        rate = _safe_float(_mapping(summary.get("correct_rate_by_session")).get(bucket), 0.0)
        measured = _safe_int(_mapping(summary.get("measured_count_by_session")).get(bucket), 0)
        lines.append(f"- `{bucket}`: measured={measured} | correct_rate={rate:.4f}")
    lines.extend(["", "## Guard Trace By Session", ""])
    for bucket in SESSION_BUCKET_ENUM_V1:
        row = _mapping(_mapping(payload.get("guard_trace_by_session")).get(bucket))
        lines.append(
            f"- `{bucket}`: trace={_safe_int(row.get('trace_count'), 0)} "
            f"| guard_applied={_safe_int(row.get('guard_applied_count'), 0)} "
            f"| helpful_rate={row.get('guard_helpful_rate')} "
            f"| data_status={row.get('data_status', '')}"
        )
    lines.extend(["", "## Promotion Trace By Session", ""])
    for bucket in SESSION_BUCKET_ENUM_V1:
        row = _mapping(_mapping(payload.get("promotion_trace_by_session")).get(bucket))
        lines.append(
            f"- `{bucket}`: trace={_safe_int(row.get('trace_count'), 0)} "
            f"| promotion_active={_safe_int(row.get('promotion_active_count'), 0)} "
            f"| win_rate={row.get('promotion_win_rate')} "
            f"| data_status={row.get('data_status', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_ca2_session_split_audit(
    *,
    ai_entry_traces: Iterable[Mapping[str, Any]] | None = None,
    accuracy_state_path: str | Path | None = None,
    entry_decision_detail_path: str | Path | None = None,
    shadow_auto_dir: str | Path | None = None,
    primary_horizon_bars: int = PRIMARY_HORIZON_BARS,
) -> dict[str, Any]:
    resolved_accuracy_state_path = (
        Path(accuracy_state_path) if accuracy_state_path is not None else _default_accuracy_state_path()
    )
    resolved_entry_detail_path = (
        Path(entry_decision_detail_path)
        if entry_decision_detail_path is not None
        else _default_entry_decision_detail_path()
    )
    resolved_output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    report = build_ca2_session_split_audit(
        accuracy_state_payload=_load_json(resolved_accuracy_state_path),
        entry_payload_rows=_tail_jsonl_payloads(resolved_entry_detail_path),
        ai_entry_traces=ai_entry_traces or [],
        primary_horizon_bars=int(primary_horizon_bars),
    )
    json_path = resolved_output_dir / "ca2_session_split_audit_latest.json"
    md_path = resolved_output_dir / "ca2_session_split_audit_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "accuracy_state_path": str(resolved_accuracy_state_path),
        "entry_decision_detail_path": str(resolved_entry_detail_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_ca2_session_split_audit_markdown(report))
    return report
