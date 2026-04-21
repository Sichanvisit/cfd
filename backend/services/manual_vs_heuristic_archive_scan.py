"""Scan historical semantic archives relevant to manual-vs-heuristic comparison."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


ARCHIVE_SCAN_COLUMNS = [
    "archive_file",
    "archive_kind",
    "archive_format",
    "row_count",
    "time_min",
    "time_max",
    "signal_bar_min",
    "signal_bar_max",
    "barrier_field_present",
    "barrier_value_rows",
    "belief_field_present",
    "belief_value_rows",
    "forecast_field_present",
    "forecast_value_rows",
    "wait_field_present",
    "wait_value_rows",
]


def _to_text(value: object) -> str:
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value or "").strip()


def _parse_time(value: object) -> pd.Timestamp | None:
    text = _to_text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        return stamp.tz_convert("Asia/Seoul").tz_localize(None)
    return stamp


def _parse_signal_bar(value: object) -> pd.Timestamp | None:
    try:
        if value in ("", None):
            return None
        return (
            pd.to_datetime(float(value), unit="s", utc=True)
            .tz_convert("Asia/Seoul")
            .tz_localize(None)
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _archive_kind_from_name(name: str) -> str:
    if name == "entry_decisions.csv":
        return "current_csv"
    if name == "entry_decisions.detail.jsonl":
        return "current_detail"
    if ".legacy_" in name and name.endswith(".csv"):
        return "legacy_csv"
    if ".legacy_" in name and name.endswith(".detail.jsonl"):
        return "legacy_detail"
    if ".detail.rotate_" in name:
        return "rotate_detail"
    return "other"


def discover_archive_paths(trades_dir: str | Path) -> list[Path]:
    root = Path(trades_dir)
    if not root.exists():
        return []
    patterns = [
        "entry_decisions.csv",
        "entry_decisions.legacy_*.csv",
        "entry_decisions.detail.jsonl",
        "entry_decisions.legacy_*.detail.jsonl",
        "entry_decisions.detail.rotate_*.jsonl",
    ]
    unique: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            unique[str(path.resolve())] = path
    return sorted(unique.values(), key=lambda item: item.name)


def _scan_csv_archive(path: Path) -> dict[str, Any]:
    fieldnames: list[str] = []
    row_count = 0
    time_min: pd.Timestamp | None = None
    time_max: pd.Timestamp | None = None
    signal_min: pd.Timestamp | None = None
    signal_max: pd.Timestamp | None = None
    barrier_rows = 0
    belief_rows = 0
    forecast_rows = 0
    wait_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            row_count += 1
            stamp = _parse_time(row.get("time", ""))
            if stamp is not None:
                time_min = stamp if time_min is None or stamp < time_min else time_min
                time_max = stamp if time_max is None or stamp > time_max else time_max
            signal = _parse_signal_bar(row.get("signal_bar_ts", ""))
            if signal is not None:
                signal_min = signal if signal_min is None or signal < signal_min else signal_min
                signal_max = signal if signal_max is None or signal > signal_max else signal_max
            if _to_text(row.get("barrier_state_v1", "")) or _to_text(row.get("barrier_candidate_recommended_family", "")):
                barrier_rows += 1
            if _to_text(row.get("belief_state_v1", "")) or _to_text(row.get("belief_candidate_recommended_family", "")):
                belief_rows += 1
            if _to_text(row.get("forecast_assist_v1", "")) or _to_text(row.get("forecast_decision_hint", "")):
                forecast_rows += 1
            if _to_text(row.get("entry_wait_decision", "")):
                wait_rows += 1
    cols = set(fieldnames)
    return {
        "archive_file": path.name,
        "archive_kind": _archive_kind_from_name(path.name),
        "archive_format": "csv",
        "row_count": row_count,
        "time_min": time_min.isoformat() if time_min is not None else "",
        "time_max": time_max.isoformat() if time_max is not None else "",
        "signal_bar_min": signal_min.isoformat() if signal_min is not None else "",
        "signal_bar_max": signal_max.isoformat() if signal_max is not None else "",
        "barrier_field_present": 1 if ("barrier_state_v1" in cols or "barrier_candidate_recommended_family" in cols) else 0,
        "barrier_value_rows": barrier_rows,
        "belief_field_present": 1 if ("belief_state_v1" in cols or "belief_candidate_recommended_family" in cols) else 0,
        "belief_value_rows": belief_rows,
        "forecast_field_present": 1 if ("forecast_assist_v1" in cols or "forecast_decision_hint" in cols) else 0,
        "forecast_value_rows": forecast_rows,
        "wait_field_present": 1 if "entry_wait_decision" in cols else 0,
        "wait_value_rows": wait_rows,
    }


def _scan_detail_archive(path: Path) -> dict[str, Any]:
    row_count = 0
    time_min: pd.Timestamp | None = None
    time_max: pd.Timestamp | None = None
    signal_min: pd.Timestamp | None = None
    signal_max: pd.Timestamp | None = None
    barrier_rows = 0
    belief_rows = 0
    forecast_rows = 0
    wait_rows = 0
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            payload = obj.get("payload", {}) if isinstance(obj, dict) else {}
            row_count += 1
            stamp = _parse_time(payload.get("time", ""))
            if stamp is not None:
                time_min = stamp if time_min is None or stamp < time_min else time_min
                time_max = stamp if time_max is None or stamp > time_max else time_max
            signal = _parse_signal_bar(payload.get("signal_bar_ts", ""))
            if signal is not None:
                signal_min = signal if signal_min is None or signal < signal_min else signal_min
                signal_max = signal if signal_max is None or signal > signal_max else signal_max
            if _to_text(payload.get("barrier_state_v1", "")):
                barrier_rows += 1
            if _to_text(payload.get("belief_state_v1", "")):
                belief_rows += 1
            if _to_text(payload.get("forecast_assist_v1", "")) or _to_text(payload.get("forecast_effective_policy_v1", "")):
                forecast_rows += 1
            if _to_text(payload.get("entry_wait_decision", "")):
                wait_rows += 1
    return {
        "archive_file": path.name,
        "archive_kind": _archive_kind_from_name(path.name),
        "archive_format": "detail_jsonl",
        "row_count": row_count,
        "time_min": time_min.isoformat() if time_min is not None else "",
        "time_max": time_max.isoformat() if time_max is not None else "",
        "signal_bar_min": signal_min.isoformat() if signal_min is not None else "",
        "signal_bar_max": signal_max.isoformat() if signal_max is not None else "",
        "barrier_field_present": 1,
        "barrier_value_rows": barrier_rows,
        "belief_field_present": 1,
        "belief_value_rows": belief_rows,
        "forecast_field_present": 1,
        "forecast_value_rows": forecast_rows,
        "wait_field_present": 1,
        "wait_value_rows": wait_rows,
    }


def build_manual_vs_heuristic_archive_scan(trades_dir: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for path in discover_archive_paths(trades_dir):
        if path.suffix.lower() == ".csv":
            rows.append(_scan_csv_archive(path))
        else:
            rows.append(_scan_detail_archive(path))
    frame = pd.DataFrame(rows)
    for column in ARCHIVE_SCAN_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[ARCHIVE_SCAN_COLUMNS].copy()
    kind_counts = Counter(frame["archive_kind"]) if not frame.empty else Counter()
    summary = {
        "archive_count": int(len(frame)),
        "archive_kind_counts": dict(kind_counts),
        "detail_archive_count": int((frame["archive_format"] == "detail_jsonl").sum()) if not frame.empty else 0,
        "csv_archive_count": int((frame["archive_format"] == "csv").sum()) if not frame.empty else 0,
        "archives_with_barrier_values": int((frame["barrier_value_rows"].fillna(0).astype(int) > 0).sum()) if not frame.empty else 0,
        "archives_with_belief_values": int((frame["belief_value_rows"].fillna(0).astype(int) > 0).sum()) if not frame.empty else 0,
        "archives_with_forecast_values": int((frame["forecast_value_rows"].fillna(0).astype(int) > 0).sum()) if not frame.empty else 0,
        "archives_with_wait_values": int((frame["wait_value_rows"].fillna(0).astype(int) > 0).sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_manual_vs_heuristic_archive_scan_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Manual vs Heuristic Historical Archive Scan v0",
            "",
            f"- archive count: `{summary.get('archive_count', 0)}`",
            f"- archive kinds: `{summary.get('archive_kind_counts', {})}`",
            f"- csv archives: `{summary.get('csv_archive_count', 0)}`",
            f"- detail archives: `{summary.get('detail_archive_count', 0)}`",
            f"- archives with barrier values: `{summary.get('archives_with_barrier_values', 0)}`",
            f"- archives with belief values: `{summary.get('archives_with_belief_values', 0)}`",
            f"- archives with forecast values: `{summary.get('archives_with_forecast_values', 0)}`",
            f"- archives with wait values: `{summary.get('archives_with_wait_values', 0)}`",
            "",
            "## Why This Matters",
            "",
            "- This scan inventories where historical semantic hints actually live.",
            "- It distinguishes current CSV, legacy CSV, legacy detail JSONL, and rotated detail archives.",
            "- It is the first check before concluding that manual-vs-heuristic comparison is blocked by missing history.",
        ]
    )
