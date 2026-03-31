"""
Quick connectivity/consistency check for CSV, MT5 snapshot services, and FastAPI.

Usage:
    py -3.12 check_connections.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.services.mt5_snapshot_service import Mt5SnapshotService
from backend.services.trade_csv_schema import TRADE_COLUMNS, normalize_trade_df
from backend.services.trade_read_service import TradeReadService
from backend.trading.trade_logger import TradeLogger


def main():
    csv_path = Path("data/trades/trade_history.csv")
    print(f"[CSV] path={csv_path.resolve()}")
    print(f"[CSV] exists={csv_path.exists()}")
    if not csv_path.exists():
        return

    raw_df = pd.read_csv(csv_path)
    norm_df = normalize_trade_df(raw_df)
    missing = [c for c in TRADE_COLUMNS if c not in norm_df.columns]
    print(f"[CSV] raw_rows={len(raw_df)} norm_rows={len(norm_df)} cols={len(norm_df.columns)} missing_cols={len(missing)}")
    if missing:
        print(f"[CSV] missing={missing}")
    if not norm_df.empty and "status" in norm_df.columns:
        print(f"[CSV] status_counts={norm_df['status'].value_counts(dropna=False).to_dict()}")

    read_service = TradeReadService(csv_path)
    summary = read_service.get_summary()
    recent = read_service.get_recent(limit=10).get("items", [])
    closed = read_service.get_closed_recent(limit=10, include_mt5=False).get("items", [])
    print(f"[READ] summary={summary}")
    print(f"[READ] recent_items={len(recent)} closed_items={len(closed)}")

    trade_logger = TradeLogger()
    snapshot_service = Mt5SnapshotService(csv_path, trade_logger=trade_logger)
    mt5_status = snapshot_service.get_mt5_status()
    pos_enriched = snapshot_service.get_positions_enriched(force_refresh=True, timeout_ms=1200)
    print(
        f"[MT5] connected={mt5_status.get('connected')} positions={len(mt5_status.get('positions', []))}"
    )
    print(
        f"[POS] connected={pos_enriched.get('connected')} items={len(pos_enriched.get('items', []))}"
    )


if __name__ == "__main__":
    main()
