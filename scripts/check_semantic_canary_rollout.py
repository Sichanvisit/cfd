"""Summarize semantic canary rollout health from runtime status and recent decision rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
ENTRY_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
RUNTIME_STATUS = ROOT / "data" / "runtime_status.json"
ROLLOUT_MANIFEST = ROOT / "data" / "manifests" / "rollout" / "semantic_live_rollout_latest.json"
OUT_DIR = ROOT / "data" / "analysis" / "semantic_canary"

ENTRY_COLUMNS = (
    "time",
    "symbol",
    "entry_stage",
    "outcome",
    "blocked_by",
    "semantic_shadow_available",
    "semantic_shadow_trace_quality",
    "semantic_live_rollout_mode",
    "semantic_live_alert",
    "semantic_live_fallback_reason",
    "semantic_live_symbol_allowed",
    "semantic_live_entry_stage_allowed",
    "semantic_live_threshold_before",
    "semantic_live_threshold_after",
    "semantic_live_threshold_adjustment",
    "semantic_live_threshold_applied",
    "semantic_live_partial_weight",
    "semantic_live_partial_live_applied",
    "semantic_live_reason",
    "semantic_shadow_compare_label",
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KST)
    return dt


def _resolve_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(KST)
    if now.tzinfo is None:
        return now.replace(tzinfo=KST)
    return now.astimezone(KST)


def _to_int(value: Any, default: int = 0) -> int:
    if value in ("", None):
        return int(default)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _stream_recent_rows(
    *,
    path: Path,
    symbol: str = "",
    since: datetime | None = None,
    limit: int = 4000,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[dict[str, Any]] = deque(maxlen=max(10, int(limit)))
    symbol_u = str(symbol or "").strip().upper()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = {column: raw_row.get(column, "") for column in ENTRY_COLUMNS}
            if symbol_u and str(row.get("symbol", "")).strip().upper() != symbol_u:
                continue
            dt = _parse_dt(row.get("time"))
            if since is not None and dt is not None and dt < since:
                continue
            if str(row.get("semantic_live_rollout_mode", "")).strip() == "":
                continue
            row["time_dt"] = dt.isoformat() if dt is not None else ""
            rows.append(row)
    return list(rows)


def _counter(rows: list[dict[str, Any]], key: str, *, non_empty: bool = True) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = str(row.get(key, "") or "").strip()
        if non_empty and not value:
            continue
        counts[value or "UNKNOWN"] += 1
    return dict(counts.most_common())


def build_canary_report(
    *,
    entry_rows: list[dict[str, Any]],
    runtime_status: dict[str, Any] | None = None,
    rollout_manifest: dict[str, Any] | None = None,
    symbol: str = "",
    hours: int = 24,
    now: datetime | None = None,
) -> dict[str, Any]:
    rows = list(entry_rows or [])
    now_kst = _resolve_now(now)
    window_hours = max(1, int(hours))
    window_start = now_kst - timedelta(hours=window_hours)
    threshold_adjustments = [_to_int(row.get("semantic_live_threshold_adjustment"), 0) for row in rows]
    applied_rows = [row for row in rows if _to_int(row.get("semantic_live_threshold_applied"), 0) > 0]
    fallback_rows = [row for row in rows if str(row.get("semantic_live_fallback_reason", "")).strip()]
    alert_rows = [row for row in rows if _to_int(row.get("semantic_live_alert"), 0) > 0]
    latest_runtime = (
        _load_json(RUNTIME_STATUS).get("latest_signal_by_symbol", {}).get(str(symbol or "").upper(), {})
        if runtime_status is None
        else (runtime_status.get("latest_signal_by_symbol", {}).get(str(symbol or "").upper(), {}))
    )
    report = {
        "generated_at": now_kst.isoformat(timespec="seconds"),
        "report_type": "semantic_canary_rollout_report_v1",
        "symbol": str(symbol or ""),
        "window_hours": int(window_hours),
        "window_start": window_start.isoformat(timespec="seconds"),
        "semantic_live_config": dict((runtime_status or {}).get("semantic_live_config", {})),
        "rollout_manifest": dict(rollout_manifest or {}),
        "summary": {
            "recent_rows": int(len(rows)),
            "threshold_applied_rows": int(len(applied_rows)),
            "fallback_rows": int(len(fallback_rows)),
            "alert_rows": int(len(alert_rows)),
            "shadow_available_rows": int(
                sum(1 for row in rows if _to_int(row.get("semantic_shadow_available"), 0) > 0)
            ),
            "threshold_adjustment_mean": (
                round(sum(threshold_adjustments) / len(threshold_adjustments), 4) if threshold_adjustments else 0.0
            ),
            "threshold_adjustment_min": min(threshold_adjustments) if threshold_adjustments else 0,
            "threshold_adjustment_max": max(threshold_adjustments) if threshold_adjustments else 0,
        },
        "stage_counts": _counter(rows, "entry_stage"),
        "rollout_mode_counts": _counter(rows, "semantic_live_rollout_mode"),
        "trace_quality_counts": _counter(rows, "semantic_shadow_trace_quality"),
        "fallback_reason_counts": _counter(rows, "semantic_live_fallback_reason"),
        "semantic_live_reason_counts": _counter(rows, "semantic_live_reason"),
        "compare_label_counts": _counter(rows, "semantic_shadow_compare_label"),
        "blocked_by_counts": _counter(rows, "blocked_by"),
        "recent_rows": rows[-20:],
        "latest_runtime_symbol_row": dict(latest_runtime or {}),
    }

    recent_count = int(report["summary"]["recent_rows"])
    fallback_ratio = (len(fallback_rows) / recent_count) if recent_count > 0 else None
    applied_ratio = (len(applied_rows) / recent_count) if recent_count > 0 else None
    recommendation = "insufficient_data"
    if recent_count >= 150:
        if fallback_ratio is not None and fallback_ratio >= 0.70:
            recommendation = "too_strict_fallback"
        elif applied_ratio is not None and applied_ratio <= 0.02:
            recommendation = "threshold_adjustment_too_rare"
        else:
            recommendation = "observe_more_before_phase5c"
    report["recommendation"] = {
        "value": recommendation,
        "fallback_ratio": (None if fallback_ratio is None else round(fallback_ratio, 4)),
        "threshold_applied_ratio": (None if applied_ratio is None else round(applied_ratio, 4)),
    }
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary", {})
    recommendation = report.get("recommendation", {})
    lines = [
        "# Semantic Canary Rollout",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- symbol: `{report.get('symbol', '')}`",
        f"- window_hours: `{report.get('window_hours', 0)}`",
        f"- window_start: `{report.get('window_start', '')}`",
        f"- recommendation: `{recommendation.get('value', '')}`",
        f"- fallback_ratio: `{recommendation.get('fallback_ratio', None)}`",
        f"- threshold_applied_ratio: `{recommendation.get('threshold_applied_ratio', None)}`",
        "",
        "## Summary",
        f"- recent_rows: `{summary.get('recent_rows', 0)}`",
        f"- threshold_applied_rows: `{summary.get('threshold_applied_rows', 0)}`",
        f"- fallback_rows: `{summary.get('fallback_rows', 0)}`",
        f"- alert_rows: `{summary.get('alert_rows', 0)}`",
        f"- shadow_available_rows: `{summary.get('shadow_available_rows', 0)}`",
        f"- threshold_adjustment_mean: `{summary.get('threshold_adjustment_mean', 0.0)}`",
        f"- threshold_adjustment_range: `{summary.get('threshold_adjustment_min', 0)} .. {summary.get('threshold_adjustment_max', 0)}`",
        "",
        "## Fallback Reasons",
    ]
    fallback_counts = report.get("fallback_reason_counts", {})
    if fallback_counts:
        for key, value in fallback_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none: `0`")
    lines.extend(["", "## Trace Quality"])
    for key, value in (report.get("trace_quality_counts", {}) or {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Semantic Live Reasons"])
    reason_counts = report.get("semantic_live_reason_counts", {})
    if reason_counts:
        for key, value in reason_counts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- none: `0`")
    lines.extend(["", "## Entry Stages"])
    for key, value in (report.get("stage_counts", {}) or {}).items():
        lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_canary_report(
    *,
    symbol: str = "BTCUSD",
    hours: int = 24,
    max_rows: int = 4000,
    output_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    out_dir = Path(output_dir) if output_dir is not None else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    now_kst = _resolve_now(now)
    window_hours = max(1, int(hours))
    since = now_kst - timedelta(hours=window_hours)
    runtime_status = _load_json(RUNTIME_STATUS)
    rollout_manifest = _load_json(ROLLOUT_MANIFEST)
    entry_rows = _stream_recent_rows(
        path=ENTRY_DECISIONS,
        symbol=symbol,
        since=since,
        limit=max_rows,
    )
    report = build_canary_report(
        entry_rows=entry_rows,
        runtime_status=runtime_status,
        rollout_manifest=rollout_manifest,
        symbol=symbol,
        hours=window_hours,
        now=now_kst,
    )
    timestamp = now_kst.strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"semantic_canary_rollout_{str(symbol or '').upper()}_{timestamp}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    latest_json = out_dir / f"semantic_canary_rollout_{str(symbol or '').upper()}_latest.json"
    latest_md = out_dir / f"semantic_canary_rollout_{str(symbol or '').upper()}_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "latest_json_path": str(latest_json),
        "latest_markdown_path": str(latest_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--max-rows", type=int, default=4000)
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    paths = write_canary_report(
        symbol=args.symbol,
        hours=args.hours,
        max_rows=args.max_rows,
        output_dir=Path(args.output_dir),
    )
    print(paths["latest_json_path"])
    print(paths["latest_markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
