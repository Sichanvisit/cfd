"""
One-time repair tool for trade_history.csv quality issues.

Run:
    py -3.12 ml/repair_trade_history_once.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    csv_path = project_root / "data" / "trades" / "trade_history.csv"
    if not csv_path.exists():
        print(f"not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("trade_history.csv is empty")
        return

    required_cols = [
        "ticket",
        "symbol",
        "direction",
        "open_time",
        "open_price",
        "entry_score",
        "contra_score_at_entry",
        "close_time",
        "close_price",
        "profit",
        "points",
        "entry_reason",
        "exit_reason",
        "exit_score",
        "status",
    ]
    for col in required_cols:
        if col not in df.columns:
            if col in ("open_time", "close_time", "entry_reason", "exit_reason", "symbol", "direction"):
                df[col] = ""
            elif col == "status":
                df[col] = "OPEN"
            else:
                df[col] = 0.0

    for col in ("open_time", "close_time", "entry_reason", "exit_reason", "status", "symbol", "direction"):
        df[col] = df[col].fillna("").astype(str)
    for col in ("open_price", "entry_score", "contra_score_at_entry", "close_price", "profit", "points", "exit_score"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["status"] = df["status"].str.strip().str.upper()
    invalid_status = df["status"].isin(["", "NAN", "NONE", "NULL"])
    closed_hint = (
        (df["close_time"].str.strip() != "")
        | (df["close_price"] != 0.0)
        | (df["profit"] != 0.0)
    )
    df.loc[invalid_status & closed_hint, "status"] = "CLOSED"
    df.loc[invalid_status & ~closed_hint, "status"] = "OPEN"

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    closed_mask = df["status"] == "CLOSED"
    open_mask = df["status"] == "OPEN"

    missing_close_time = closed_mask & (df["close_time"].str.strip() == "")
    df.loc[missing_close_time, "close_time"] = df.loc[missing_close_time, "open_time"].replace("", now_text)

    missing_exit_reason = closed_mask & (df["exit_reason"].str.strip() == "")
    df.loc[missing_exit_reason, "exit_reason"] = "Manual/Unknown"

    missing_entry_reason = df["entry_reason"].str.strip() == ""
    df.loc[missing_entry_reason, "entry_reason"] = "UNKNOWN"

    # Keep OPEN rows clean.
    df.loc[open_mask, "close_time"] = ""
    df.loc[open_mask, "exit_reason"] = ""
    df.loc[open_mask & (df["close_price"] != 0.0), "close_price"] = 0.0
    df.loc[open_mask & (df["exit_score"] != 0.0), "exit_score"] = 0.0

    backup_path = csv_path.with_suffix(f".csv.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    csv_path.replace(backup_path)
    df[required_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"backup: {backup_path}")
    print(f"saved : {csv_path}")
    print(
        "stats : "
        f"rows={len(df)}, "
        f"closed={int(closed_mask.sum())}, "
        f"missing_close_time_fixed={int(missing_close_time.sum())}, "
        f"missing_exit_reason_fixed={int(missing_exit_reason.sum())}, "
        f"missing_entry_reason_fixed={int(missing_entry_reason.sum())}"
    )


if __name__ == "__main__":
    main()
