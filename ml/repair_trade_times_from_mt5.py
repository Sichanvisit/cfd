"""
One-time repair for trade_history.csv time fields.

What it does:
1) Ensure `lot`, `open_ts`, `close_ts` columns exist.
2) Fill missing/invalid ts values from existing text fields.
3) Detect suspicious CLOSED rows:
   - close_ts in future (> now + 10 min)
   - close_ts <= 0
   - close_time earlier than open_time
4) Try to repair suspicious close time from MT5 history by ticket(position_id).
5) If MT5 deal is not found for future rows, apply a conservative hour-shift fallback.

Run:
    py -3.12 ml/repair_trade_times_from_mt5.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import MetaTrader5 as mt5

from backend.integrations.mt5_connection import connect_to_mt5, disconnect_mt5

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")


def _ts_to_kst_dt(ts: int) -> datetime:
    dt_utc = datetime.fromtimestamp(int(ts), tz=UTC)
    now_utc = datetime.now(UTC)
    if dt_utc > (now_utc + timedelta(minutes=10)):
        skew_h = int(round((dt_utc - now_utc).total_seconds() / 3600.0))
        if 1 <= skew_h <= 5:
            dt_utc = dt_utc - timedelta(hours=skew_h)
    return dt_utc.astimezone(KST)


def _text_to_kst_epoch(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return 0
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.tz_localize(KST)
        else:
            dt = dt.tz_convert(KST)
        return int(dt.timestamp())
    except Exception:
        return 0


def _epoch_to_kst_text(ts: int) -> str:
    n = int(ts or 0)
    if n <= 0:
        return ""
    return datetime.fromtimestamp(n, tz=KST).strftime("%Y-%m-%d %H:%M:%S")


def _latest_exit_by_position(position_id: int):
    latest = None
    try:
        deals = mt5.history_deals_get(position=int(position_id)) or []
    except Exception:
        deals = []
    for d in deals:
        if int(getattr(d, "entry", -1)) not in {int(mt5.DEAL_ENTRY_OUT), int(mt5.DEAL_ENTRY_OUT_BY)}:
            continue
        if latest is None or int(getattr(d, "time", 0)) > int(getattr(latest, "time", 0)):
            latest = d
    return latest


def main() -> None:
    csv_path = Path(__file__).resolve().parents[1] / "data" / "trades" / "trade_history.csv"
    if not csv_path.exists():
        print(f"not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("empty csv")
        return

    required = [
        "ticket",
        "symbol",
        "direction",
        "lot",
        "open_time",
        "open_ts",
        "open_price",
        "entry_score",
        "contra_score_at_entry",
        "close_time",
        "close_ts",
        "close_price",
        "profit",
        "points",
        "entry_reason",
        "exit_reason",
        "exit_score",
        "status",
    ]
    for col in required:
        if col not in df.columns:
            if col in {"symbol", "direction", "open_time", "close_time", "entry_reason", "exit_reason"}:
                df[col] = ""
            elif col == "status":
                df[col] = "OPEN"
            else:
                df[col] = 0.0

    for col in ("symbol", "direction", "open_time", "close_time", "entry_reason", "exit_reason", "status"):
        df[col] = df[col].fillna("").astype(str)
    for col in ("ticket", "lot", "open_ts", "close_ts", "open_price", "close_price", "profit", "points", "entry_score", "exit_score", "contra_score_at_entry"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["ticket_i"] = df["ticket"].astype(int)
    df["open_ts"] = df["open_ts"].astype(int)
    df["close_ts"] = df["close_ts"].astype(int)
    df["status"] = df["status"].str.upper().str.strip()

    open_from_text = df["open_time"].map(_text_to_kst_epoch)
    close_from_text = df["close_time"].map(_text_to_kst_epoch)
    df.loc[df["open_ts"] <= 0, "open_ts"] = pd.to_numeric(open_from_text, errors="coerce").fillna(0).astype(int)
    df.loc[df["close_ts"] <= 0, "close_ts"] = pd.to_numeric(close_from_text, errors="coerce").fillna(0).astype(int)

    closed = df["status"] == "CLOSED"
    now_ts = int(datetime.now(KST).timestamp())
    future_cut = now_ts + 600
    bad_order = (df["close_ts"] > 0) & (df["open_ts"] > 0) & (df["close_ts"] < df["open_ts"])
    suspicious = closed & ((df["close_ts"] <= 0) | (df["close_ts"] > future_cut) | bad_order)
    target_idx = df.index[suspicious & (df["ticket_i"] > 0)].tolist()

    repaired_by_mt5 = 0
    fallback_shifted = 0

    mt5_ok = connect_to_mt5()
    try:
        if mt5_ok:
            for i in target_idx:
                t = int(df.at[i, "ticket_i"])
                deal = _latest_exit_by_position(t)
                if deal is None:
                    continue
                dt = _ts_to_kst_dt(int(getattr(deal, "time", 0)))
                ts = int(dt.timestamp())
                if ts <= 0:
                    continue
                df.at[i, "close_ts"] = ts
                df.at[i, "close_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                repaired_by_mt5 += 1
    finally:
        if mt5_ok:
            disconnect_mt5()

    # Fallback: remaining future close_ts rows -> apply inferred hour shift (1~5h).
    remain_future = df.index[(df["status"] == "CLOSED") & (df["close_ts"] > future_cut)].tolist()
    if remain_future:
        ahead_hours = []
        for i in remain_future:
            ahead_sec = int(df.at[i, "close_ts"]) - now_ts
            if ahead_sec > 0:
                h = int(round(ahead_sec / 3600.0))
                if 1 <= h <= 5:
                    ahead_hours.append(h)
        shift_h = 0
        if ahead_hours:
            # Use the most common inferred offset.
            shift_h = pd.Series(ahead_hours).mode().iloc[0]
        if shift_h > 0:
            delta = int(shift_h * 3600)
            for i in remain_future:
                new_ts = int(df.at[i, "close_ts"]) - delta
                if new_ts <= 0:
                    continue
                if int(df.at[i, "open_ts"]) > 0 and new_ts < int(df.at[i, "open_ts"]):
                    continue
                df.at[i, "close_ts"] = new_ts
                df.at[i, "close_time"] = _epoch_to_kst_text(new_ts)
                fallback_shifted += 1

    # Normalize text from ts for rows that have valid ts.
    open_has_ts = df["open_ts"] > 0
    close_has_ts = (df["status"] == "CLOSED") & (df["close_ts"] > 0)
    df.loc[open_has_ts, "open_time"] = df.loc[open_has_ts, "open_ts"].map(_epoch_to_kst_text)
    df.loc[close_has_ts, "close_time"] = df.loc[close_has_ts, "close_ts"].map(_epoch_to_kst_text)
    df.loc[df["status"] == "OPEN", "close_time"] = ""
    df.loc[df["status"] == "OPEN", "close_ts"] = 0

    backup = csv_path.with_suffix(f".csv.bak_timefix_{datetime.now(KST).strftime('%Y%m%d_%H%M%S')}")
    out = df[[c for c in required if c in df.columns]].copy()

    try:
        csv_path.replace(backup)
        out.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"backup: {backup}")
    except PermissionError:
        out.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("backup: skipped (rename blocked by file lock)")

    future_after = int(((out["status"].astype(str).str.upper() == "CLOSED") & (pd.to_numeric(out["close_ts"], errors="coerce").fillna(0).astype(int) > future_cut)).sum())
    print(f"saved : {csv_path}")
    print(
        "stats : "
        f"rows={len(out)}, "
        f"suspicious_target={len(target_idx)}, "
        f"repaired_by_mt5={repaired_by_mt5}, "
        f"fallback_shifted={fallback_shifted}, "
        f"future_after={future_after}"
    )


if __name__ == "__main__":
    main()

