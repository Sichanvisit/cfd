"""Audit Phase 8 recovery wait winners from runtime and open trade snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config
from backend.services.trade_csv_schema import now_kst_dt, normalize_trade_df, read_csv_resilient, text_to_kst_epoch


RUNTIME_STATUS = ROOT / "data" / "runtime_status.json"
TRADE_HISTORY = ROOT / "data" / "trades" / "trade_history.csv"
OUT_DIR = ROOT / "data" / "analysis"


def _count_nonempty(series: pd.Series) -> dict[str, int]:
    if series is None or series.empty:
        return {}
    cleaned = series.fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    if cleaned.empty:
        return {}
    counts = Counter(cleaned.tolist())
    return {str(k): int(v) for k, v in counts.items()}


def _runtime_snapshot() -> dict:
    if not RUNTIME_STATUS.exists():
        return {"updated_at": "", "symbols": {}}
    try:
        payload = json.loads(RUNTIME_STATUS.read_text(encoding="utf-8"))
    except Exception:
        return {"updated_at": "", "symbols": {}}

    symbols = {}
    latest = payload.get("latest_signal_by_symbol", {}) or {}
    for symbol, row in latest.items():
        if not isinstance(row, dict):
            continue
        symbols[str(symbol)] = {
            "my_position_count": int(row.get("my_position_count", 0) or 0),
            "exit_decision_winner": str(row.get("exit_decision_winner", "") or ""),
            "exit_decision_reason": str(row.get("exit_decision_reason", "") or ""),
            "exit_wait_selected": int(row.get("exit_wait_selected", 0) or 0),
            "exit_wait_decision": str(row.get("exit_wait_decision", "") or ""),
            "exit_wait_state": str(((row.get("exit_wait_state_v1", {}) or {}).get("state", "")) or ""),
            "p_recover_be": float(row.get("p_recover_be", 0.0) or 0.0),
            "p_recover_tp1": float(row.get("p_recover_tp1", 0.0) or 0.0),
            "p_deeper_loss": float(row.get("p_deeper_loss", 0.0) or 0.0),
            "u_cut_now": float(row.get("u_cut_now", 0.0) or 0.0),
            "u_wait_be": float(row.get("u_wait_be", 0.0) or 0.0),
            "u_wait_tp1": float(row.get("u_wait_tp1", 0.0) or 0.0),
            "u_reverse": float(row.get("u_reverse", 0.0) or 0.0),
        }
    return {
        "updated_at": str(payload.get("updated_at", "") or ""),
        "symbols": symbols,
    }


def _open_trade_snapshot() -> tuple[pd.DataFrame, list[dict]]:
    df, _ = read_csv_resilient(TRADE_HISTORY, expected_columns=[])
    df = normalize_trade_df(df)
    if df.empty:
        return df, []
    open_df = df[df["status"].astype(str).str.upper() == "OPEN"].copy()
    if open_df.empty:
        return open_df, []

    now_epoch = int(now_kst_dt().timestamp())
    open_df["open_epoch"] = open_df["open_ts"].fillna(0).astype(int)
    missing_epoch = open_df["open_epoch"] <= 0
    if missing_epoch.any():
        open_df.loc[missing_epoch, "open_epoch"] = open_df.loc[missing_epoch, "open_time"].map(text_to_kst_epoch)
    open_df["age_sec"] = (now_epoch - open_df["open_epoch"]).clip(lower=0)

    long_wait_tp1 = open_df[
        (open_df["decision_winner"].astype(str).str.lower() == "wait_tp1")
        & (open_df["age_sec"] > int(getattr(Config, "EXIT_RECOVERY_WAIT_MAX_SECONDS", 240)))
    ].copy()
    long_wait_rows = []
    for _, row in long_wait_tp1.iterrows():
        long_wait_rows.append(
            {
                "ticket": int(row.get("ticket", 0) or 0),
                "symbol": str(row.get("symbol", "") or ""),
                "profit": float(row.get("profit", 0.0) or 0.0),
                "age_sec": int(row.get("age_sec", 0) or 0),
                "decision_winner": str(row.get("decision_winner", "") or ""),
                "exit_wait_state": str(row.get("exit_wait_state", "") or ""),
                "exit_wait_decision": str(row.get("exit_wait_decision", "") or ""),
            }
        )
    return open_df, long_wait_rows


def _winner_by_setup(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    if df.empty or ("entry_setup_id" not in df.columns) or ("decision_winner" not in df.columns):
        return {}
    work = df.copy()
    work["entry_setup_id"] = work["entry_setup_id"].fillna("").astype(str).str.strip().str.lower()
    work["decision_winner"] = work["decision_winner"].fillna("").astype(str).str.strip().str.lower()
    work = work[(work["entry_setup_id"] != "") & (work["decision_winner"] != "")]
    if work.empty:
        return {}
    out: dict[str, dict[str, int]] = {}
    for setup_id, part in work.groupby("entry_setup_id"):
        out[str(setup_id)] = {
            str(k): int(v)
            for k, v in part["decision_winner"].value_counts().items()
        }
    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Phase 8 recovery wait winners.")
    parser.add_argument("--since", dest="since", default="", help="KST timestamp or ISO datetime. Filters open rows by open_time.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runtime = _runtime_snapshot()
    open_df, long_wait_rows = _open_trade_snapshot()
    since_text = str(args.since or "").strip()
    cutoff = None
    if since_text:
        try:
            cutoff = pd.Timestamp(since_text)
            if cutoff.tzinfo is not None:
                cutoff = cutoff.tz_convert("Asia/Seoul").tz_localize(None)
        except Exception:
            cutoff = None
    if cutoff is not None and not open_df.empty:
        open_time_series = pd.to_datetime(open_df.get("open_time", pd.Series(dtype=str)), errors="coerce")
        open_df = open_df[open_time_series >= cutoff].copy()
        if long_wait_rows:
            kept_rows = []
            open_time_by_ticket = {}
            if not open_df.empty and "ticket" in open_df.columns:
                for _, row in open_df.iterrows():
                    open_time_by_ticket[int(row.get("ticket", 0) or 0)] = pd.Timestamp(str(row.get("open_time", "")))
            for row in long_wait_rows:
                ticket = int(row.get("ticket", 0) or 0)
                open_time = open_time_by_ticket.get(ticket)
                if open_time is not None and open_time >= cutoff:
                    kept_rows.append(row)
            long_wait_rows = kept_rows

    report = {
        "generated_at": now_kst_dt().isoformat(),
        "since": str(since_text),
        "runtime_updated_at": runtime.get("updated_at", ""),
        "runtime_symbols": runtime.get("symbols", {}),
        "runtime_counts": {
            "exit_decision_winner": _count_nonempty(pd.Series([v.get("exit_decision_winner", "") for v in runtime.get("symbols", {}).values()])),
            "exit_wait_state": _count_nonempty(pd.Series([v.get("exit_wait_state", "") for v in runtime.get("symbols", {}).values()])),
            "exit_wait_decision": _count_nonempty(pd.Series([v.get("exit_wait_decision", "") for v in runtime.get("symbols", {}).values()])),
        },
        "open_trade_counts": {
            "rows_total": int(len(open_df)),
            "decision_winner": _count_nonempty(open_df.get("decision_winner", pd.Series(dtype=str))),
            "exit_wait_state": _count_nonempty(open_df.get("exit_wait_state", pd.Series(dtype=str))),
            "exit_wait_decision": _count_nonempty(open_df.get("exit_wait_decision", pd.Series(dtype=str))),
            "entry_setup_id": _count_nonempty(open_df.get("entry_setup_id", pd.Series(dtype=str))),
            "winner_by_setup": _winner_by_setup(open_df),
        },
        "wait_tp1_too_long_rows": long_wait_rows,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"exit_recovery_audit_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
