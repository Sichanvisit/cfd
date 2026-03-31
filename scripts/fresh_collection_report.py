"""Aggregate fresh entry/exit distribution since a given timestamp."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.trade_csv_schema import normalize_trade_df, now_kst_dt, read_csv_resilient

ENTRY_DECISIONS = ROOT / "data" / "trades" / "entry_decisions.csv"
TRADE_HISTORY = ROOT / "data" / "trades" / "trade_history.csv"
TRADE_CLOSED = ROOT / "data" / "trades" / "trade_closed_history.csv"
OUT_DIR = ROOT / "data" / "analysis"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()


def _counts(series: pd.Series, top: int = 20) -> dict[str, int]:
    if series is None or series.empty:
        return {}
    s = series.fillna("").astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return {}
    vc = s.value_counts().head(top)
    return {str(k): int(v) for k, v in vc.items()}


def _filter_since(df: pd.DataFrame, col: str, since: str) -> pd.DataFrame:
    if df.empty or col not in df.columns or not since:
        return df.copy()
    ts = pd.to_datetime(df[col], errors="coerce")
    pivot = pd.to_datetime(since, errors="coerce")
    if pd.isna(pivot):
        return df.copy()
    return df.loc[ts >= pivot].copy()


def _symbol_breakdown(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    if df.empty or "symbol" not in df.columns or "outcome" not in df.columns:
        return {}
    out: dict[str, dict[str, int]] = {}
    for symbol, part in df.groupby(df["symbol"].fillna("").astype(str)):
        if not symbol:
            continue
        out[symbol] = {
            "rows": int(len(part)),
            "entered": int((part["outcome"].fillna("").astype(str).str.lower() == "entered").sum()),
            "wait": int((part["outcome"].fillna("").astype(str).str.lower() == "wait").sum()),
            "skipped": int((part["outcome"].fillna("").astype(str).str.lower() == "skipped").sum()),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="", help="ISO-like timestamp, e.g. 2026-03-08 17:13:00")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entry_df = _read_csv(ENTRY_DECISIONS)
    entry_df = _filter_since(entry_df, "time", args.since)

    trade_df, _ = read_csv_resilient(TRADE_HISTORY, expected_columns=[])
    trade_df = normalize_trade_df(trade_df)
    trade_df = _filter_since(trade_df, "open_time", args.since)

    closed_df, _ = read_csv_resilient(TRADE_CLOSED, expected_columns=[])
    closed_df = normalize_trade_df(closed_df)
    closed_df = _filter_since(closed_df, "close_time", args.since)

    report = {
        "generated_at": now_kst_dt().isoformat(),
        "since": args.since,
        "entry": {
            "rows_total": int(len(entry_df)),
            "outcome_counts": _counts(entry_df.get("outcome", pd.Series(dtype=str))),
            "blocked_by_counts": _counts(entry_df.get("blocked_by", pd.Series(dtype=str))),
            "setup_counts": _counts(entry_df.get("setup_id", pd.Series(dtype=str))),
            "wait_state_counts": _counts(entry_df.get("entry_wait_state", pd.Series(dtype=str))),
            "symbol_breakdown": _symbol_breakdown(entry_df),
        },
        "open_positions": {
            "rows_total": int(len(trade_df)),
            "symbol_counts": _counts(trade_df.get("symbol", pd.Series(dtype=str))),
            "setup_counts": _counts(trade_df.get("entry_setup_id", pd.Series(dtype=str))),
            "exit_profile_counts": _counts(trade_df.get("exit_profile", pd.Series(dtype=str))),
            "decision_winner_counts": _counts(trade_df.get("decision_winner", pd.Series(dtype=str))),
        },
        "closed_positions": {
            "rows_total": int(len(closed_df)),
            "symbol_counts": _counts(closed_df.get("symbol", pd.Series(dtype=str))),
            "setup_counts": _counts(closed_df.get("entry_setup_id", pd.Series(dtype=str))),
            "decision_winner_counts": _counts(closed_df.get("decision_winner", pd.Series(dtype=str))),
            "final_outcome_counts": _counts(closed_df.get("final_outcome", pd.Series(dtype=str))),
        },
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"fresh_collection_report_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
