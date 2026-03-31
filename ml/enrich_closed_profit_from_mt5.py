"""
One-time enrichment: fill CLOSED rows with zero profit using MT5 history deals.

Run:
    py -3.12 ml/enrich_closed_profit_from_mt5.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import MetaTrader5 as mt5

from backend.integrations.mt5_connection import connect_to_mt5, disconnect_mt5

KST = ZoneInfo("Asia/Seoul")


def _ts_to_kst_text(ts: int) -> str:
    dt_utc = datetime.fromtimestamp(int(ts), tz=ZoneInfo("UTC"))
    now_utc = datetime.now(ZoneInfo("UTC"))
    if dt_utc > (now_utc + pd.Timedelta(minutes=10)):
        skew_h = int(round((dt_utc - now_utc).total_seconds() / 3600.0))
        if 1 <= skew_h <= 5:
            dt_utc = dt_utc - pd.Timedelta(hours=skew_h)
    return dt_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")


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
    base_dir = Path(__file__).resolve().parents[1] / "data" / "trades"
    csv_paths = [
        base_dir / "trade_closed_history.csv",
        base_dir / "trade_history.csv",
    ]
    csv_paths = [p for p in csv_paths if p.exists()]
    if not csv_paths:
        print(f"not found: {base_dir}")
        return

    if not connect_to_mt5():
        print("MT5 connect failed")
        return

    try:
        for csv_path in csv_paths:
            df = pd.read_csv(csv_path)
            if df.empty:
                print(f"empty csv: {csv_path.name}")
                continue

            for col in ("ticket", "open_price", "close_price", "profit", "points"):
                if col not in df.columns:
                    df[col] = 0.0
            for col in ("status", "close_time", "exit_reason", "direction"):
                if col not in df.columns:
                    df[col] = ""

            df["status"] = df["status"].fillna("").astype(str).str.upper()
            df["exit_reason"] = df["exit_reason"].fillna("").astype(str)
            df["ticket_i"] = pd.to_numeric(df["ticket"], errors="coerce").fillna(0).astype(int)
            df["open_price"] = pd.to_numeric(df["open_price"], errors="coerce").fillna(0.0)
            df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0.0)
            df["close_price"] = pd.to_numeric(df["close_price"], errors="coerce").fillna(0.0)
            df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)

            target_idx = df.index[(df["status"] == "CLOSED") & (df["profit"] == 0.0) & (df["ticket_i"] > 0)].tolist()
            if not target_idx:
                print(f"no target rows: {csv_path.name}")
                continue

            updated = 0
            for i in target_idx:
                ticket = int(df.at[i, "ticket_i"])
                deal = _latest_exit_by_position(ticket)
                if deal is None:
                    continue

                profit = float(getattr(deal, "profit", 0.0) or 0.0) + float(getattr(deal, "swap", 0.0) or 0.0) + float(
                    getattr(deal, "commission", 0.0) or 0.0
                )

                symbol_info = mt5.symbol_info(str(getattr(deal, "symbol", "")))
                point = float(getattr(symbol_info, "point", 0.00001) or 0.00001)
                open_price = float(df.at[i, "open_price"] or 0.0)
                direction = str(df.at[i, "direction"] or "").upper()
                if direction == "BUY":
                    points = (float(getattr(deal, "price", 0.0) or 0.0) - open_price) / point
                else:
                    points = (open_price - float(getattr(deal, "price", 0.0) or 0.0)) / point

                df.at[i, "close_time"] = _ts_to_kst_text(int(getattr(deal, "time", 0)))
                df.at[i, "close_price"] = float(getattr(deal, "price", 0.0) or 0.0)
                df.at[i, "profit"] = round(profit, 2)
                df.at[i, "points"] = round(points, 1)
                current_reason = str(df.at[i, "exit_reason"] or "").strip()
                deal_comment = str(getattr(deal, "comment", "") or "").strip()
                if (not current_reason) or (current_reason.upper() in {"MANUAL/UNKNOWN", "UNKNOWN"}):
                    if deal_comment and deal_comment.upper() not in {"AUTOTRADE", "AUTO", "CLOSE"}:
                        df.at[i, "exit_reason"] = deal_comment
                    elif not current_reason:
                        df.at[i, "exit_reason"] = "MT5 History"
                updated += 1

            # Additional pass: fix obviously wrong future close_time (timezone-drifted rows).
            now_kst_naive = pd.Timestamp.now(tz=KST).tz_localize(None)
            df["close_dt_fix"] = pd.to_datetime(df["close_time"], errors="coerce")
            abnormal_idx = df.index[
                (df["status"] == "CLOSED")
                & (df["close_dt_fix"].notna())
                & (df["close_dt_fix"] > (now_kst_naive + pd.Timedelta(minutes=10)))
                & (df["ticket_i"] > 0)
            ].tolist()
            fixed_time_rows = 0
            for i in abnormal_idx:
                ticket = int(df.at[i, "ticket_i"])
                deal = _latest_exit_by_position(ticket)
                if deal is None:
                    continue
                df.at[i, "close_time"] = _ts_to_kst_text(int(getattr(deal, "time", 0)))
                fixed_time_rows += 1

            out_df = df.drop(columns=["ticket_i", "close_dt_fix"], errors="ignore")
            backup = csv_path.with_suffix(f".csv.bak_enrich_{datetime.now(KST).strftime('%Y%m%d_%H%M%S')}")
            try:
                csv_path.replace(backup)
                out_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                print(f"backup: {backup}")
                print(f"saved : {csv_path}")
                print(f"updated_rows: {updated}/{len(target_idx)}")
                print(f"fixed_future_close_time_rows: {fixed_time_rows}/{len(abnormal_idx)}")
            except PermissionError:
                out_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                print("backup: skipped (file lock on rename)")
                print(f"saved : {csv_path} (direct overwrite)")
                print(f"updated_rows: {updated}/{len(target_idx)}")
                print(f"fixed_future_close_time_rows: {fixed_time_rows}/{len(abnormal_idx)}")
    finally:
        disconnect_mt5()


if __name__ == "__main__":
    main()
