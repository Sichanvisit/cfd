"""Audit whether the manual corpus overlaps the current hint-rich heuristic window."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


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


def _load_manual_frame(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].fillna("").astype(str).str.upper().str.strip()
    df["anchor_ts"] = df["anchor_time"].apply(_parse_time)
    return df[df["anchor_ts"].notna()].copy()


def _load_current_heuristic_frame(path: str | Path) -> pd.DataFrame:
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            stamp = _parse_time(row.get("time", ""))
            if stamp is None:
                continue
            barrier_present = bool(_to_text(row.get("barrier_candidate_recommended_family", "")) or _to_text(row.get("barrier_state_v1", "")))
            belief_present = bool(_to_text(row.get("belief_candidate_recommended_family", "")) or _to_text(row.get("belief_state_v1", "")))
            forecast_present = bool(_to_text(row.get("forecast_assist_v1", "")) or _to_text(row.get("forecast_decision_hint", "")))
            wait_present = bool(_to_text(row.get("entry_wait_decision", "")))
            rows.append(
                {
                    "time": stamp,
                    "symbol": _to_text(row.get("symbol", "")).upper(),
                    "barrier_present": barrier_present,
                    "belief_present": belief_present,
                    "forecast_present": forecast_present,
                    "wait_present": wait_present,
                }
            )
    return pd.DataFrame(rows)


def build_manual_vs_heuristic_recent_window_audit(
    manual_annotations_path: str | Path,
    current_entry_decisions_path: str | Path,
) -> dict[str, Any]:
    manual = _load_manual_frame(manual_annotations_path)
    heuristic = _load_current_heuristic_frame(current_entry_decisions_path)
    if heuristic.empty:
        return {
            "manual_episode_count": int(len(manual)),
            "current_heuristic_row_count": 0,
            "recent_overlap_episode_count": 0,
            "recent_overlap_symbol_counts": {},
        }

    hmin = heuristic["time"].min()
    hmax = heuristic["time"].max()
    overlap = manual[(manual["anchor_ts"] >= hmin) & (manual["anchor_ts"] <= hmax)].copy()
    summary = {
        "manual_episode_count": int(len(manual)),
        "manual_anchor_time_min": manual["anchor_ts"].min().isoformat() if not manual.empty else "",
        "manual_anchor_time_max": manual["anchor_ts"].max().isoformat() if not manual.empty else "",
        "current_heuristic_row_count": int(len(heuristic)),
        "current_heuristic_time_min": hmin.isoformat(),
        "current_heuristic_time_max": hmax.isoformat(),
        "current_barrier_present_rows": int(heuristic["barrier_present"].sum()),
        "current_belief_present_rows": int(heuristic["belief_present"].sum()),
        "current_forecast_present_rows": int(heuristic["forecast_present"].sum()),
        "current_wait_present_rows": int(heuristic["wait_present"].sum()),
        "recent_overlap_episode_count": int(len(overlap)),
        "recent_overlap_symbol_counts": dict(Counter(overlap["symbol"])) if not overlap.empty else {},
    }
    return summary


def render_manual_vs_heuristic_recent_window_audit_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Manual vs Heuristic Recent Window Audit v0",
            "",
            f"- manual episodes: `{summary.get('manual_episode_count', 0)}`",
            f"- manual anchor window: `{summary.get('manual_anchor_time_min', '')}` -> `{summary.get('manual_anchor_time_max', '')}`",
            f"- current heuristic rows: `{summary.get('current_heuristic_row_count', 0)}`",
            f"- current heuristic window: `{summary.get('current_heuristic_time_min', '')}` -> `{summary.get('current_heuristic_time_max', '')}`",
            f"- current barrier-present rows: `{summary.get('current_barrier_present_rows', 0)}`",
            f"- current belief-present rows: `{summary.get('current_belief_present_rows', 0)}`",
            f"- current forecast-present rows: `{summary.get('current_forecast_present_rows', 0)}`",
            f"- current wait-present rows: `{summary.get('current_wait_present_rows', 0)}`",
            f"- recent overlap episodes: `{summary.get('recent_overlap_episode_count', 0)}`",
            f"- recent overlap by symbol: `{summary.get('recent_overlap_symbol_counts', {})}`",
            "",
            "## Why This Matters",
            "",
            "- This audit answers whether the current hint-rich `entry_decisions.csv` window is already usable for manual-vs-heuristic comparison.",
            "- If overlap is near zero, the right next action is to label more recent manual episodes instead of blaming comparison logic.",
        ]
    )
