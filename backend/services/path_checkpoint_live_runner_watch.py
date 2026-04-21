"""Live watch helpers for exit_manage_runner checkpoint source growth."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_LIVE_RUNNER_WATCH_CONTRACT_VERSION = "checkpoint_live_runner_watch_v1"
PATH_CHECKPOINT_LIVE_RUNNER_WATCH_COLUMNS = [
    "symbol",
    "live_runner_source_row_count",
    "recent_live_runner_source_row_count",
    "live_runner_hold_row_count",
    "latest_live_runner_time",
    "latest_live_runner_reason",
    "recommended_focus",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_live_runner_watch_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_live_runner_watch_latest.json"


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def build_checkpoint_live_runner_watch(
    runtime_status: Mapping[str, Any] | None,
    checkpoint_rows: pd.DataFrame | None,
    *,
    previous_summary: Mapping[str, Any] | None = None,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
    recent_minutes: int = 30,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    runtime_map = dict(runtime_status or {})
    previous_map = dict(previous_summary or {})
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_LIVE_RUNNER_WATCH_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "runtime_updated_at": _to_text(runtime_map.get("updated_at")),
        "checkpoint_row_count": 0,
        "live_runner_source_row_count": 0,
        "recent_live_runner_source_row_count": 0,
        "live_runner_hold_row_count": 0,
        "previous_live_runner_source_row_count": _to_int(previous_map.get("live_runner_source_row_count"), 0),
        "live_runner_source_delta": 0,
        "symbols_with_live_runner_source": [],
        "last_live_runner_time": "",
        "last_live_runner_symbol": "",
        "recommended_next_action": "keep_runtime_running_until_exit_manage_runner_rows_appear",
    }
    if frame.empty:
        summary["live_runner_source_delta"] = 0 - int(summary["previous_live_runner_source_row_count"])
        return pd.DataFrame(columns=PATH_CHECKPOINT_LIVE_RUNNER_WATCH_COLUMNS), summary

    for column in ("generated_at", "symbol", "source", "outcome", "blocked_by"):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["source"] = frame["source"].fillna("").astype(str)
    frame["outcome"] = frame["outcome"].fillna("").astype(str)
    frame["blocked_by"] = frame["blocked_by"].fillna("").astype(str)
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")

    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    live_runner = scoped.loc[scoped["source"].fillna("").astype(str) == "exit_manage_runner"].copy()
    recent_cutoff = now_kst_dt() - pd.Timedelta(minutes=max(1, int(recent_minutes)))
    recent_live_runner = live_runner.loc[live_runner["__time_sort"] >= recent_cutoff].copy()
    live_runner_hold = live_runner.loc[live_runner["outcome"].fillna("").astype(str) == "runner_hold"].copy()

    summary["checkpoint_row_count"] = int(len(scoped))
    summary["live_runner_source_row_count"] = int(len(live_runner))
    summary["recent_live_runner_source_row_count"] = int(len(recent_live_runner))
    summary["live_runner_hold_row_count"] = int(len(live_runner_hold))
    summary["live_runner_source_delta"] = int(summary["live_runner_source_row_count"]) - int(summary["previous_live_runner_source_row_count"])
    summary["symbols_with_live_runner_source"] = sorted(set(live_runner["symbol"].dropna().astype(str).tolist()))

    if not live_runner.empty:
        latest = live_runner.sort_values("__time_sort").iloc[-1]
        summary["last_live_runner_time"] = _to_text(latest.get("generated_at"))
        summary["last_live_runner_symbol"] = _to_text(latest.get("symbol"))

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_runner = live_runner.loc[live_runner["symbol"] == symbol].copy().sort_values("__time_sort")
        symbol_recent = recent_live_runner.loc[recent_live_runner["symbol"] == symbol].copy()
        symbol_runner_hold = live_runner_hold.loc[live_runner_hold["symbol"] == symbol].copy()
        if symbol_runner.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "live_runner_source_row_count": 0,
                    "recent_live_runner_source_row_count": 0,
                    "live_runner_hold_row_count": 0,
                    "latest_live_runner_time": "",
                    "latest_live_runner_reason": "",
                    "recommended_focus": f"wait_for_{symbol.lower()}_live_runner_source",
                }
            )
            continue

        latest = symbol_runner.iloc[-1]
        focus = f"inspect_{symbol.lower()}_live_runner_hold_boundary"
        if len(symbol_recent) <= 0:
            focus = f"watch_{symbol.lower()}_live_runner_refresh"

        rows.append(
            {
                "symbol": symbol,
                "live_runner_source_row_count": int(len(symbol_runner)),
                "recent_live_runner_source_row_count": int(len(symbol_recent)),
                "live_runner_hold_row_count": int(len(symbol_runner_hold)),
                "latest_live_runner_time": _to_text(latest.get("generated_at")),
                "latest_live_runner_reason": _to_text(latest.get("blocked_by")),
                "recommended_focus": focus,
            }
        )

    if int(summary["live_runner_source_row_count"]) > int(summary["previous_live_runner_source_row_count"]):
        summary["recommended_next_action"] = "inspect_new_live_runner_rows_and_rebuild_pa5_artifacts"
    elif int(summary["live_runner_source_row_count"]) > 0:
        summary["recommended_next_action"] = "keep_runtime_running_and_track_live_runner_growth"

    return pd.DataFrame(rows, columns=PATH_CHECKPOINT_LIVE_RUNNER_WATCH_COLUMNS), summary
