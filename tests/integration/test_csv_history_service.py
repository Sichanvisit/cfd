from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.services.csv_history_service import CsvHistoryService
from backend.services.trade_csv_schema import TRADE_COLUMNS
from backend.services.trade_read_service import TradeReadService


def _blank_row() -> dict:
    row = {c: "" for c in TRADE_COLUMNS}
    for c in ["ticket", "lot", "open_ts", "close_ts", "entry_score", "contra_score_at_entry", "exit_score", "profit", "points"]:
        row[c] = 0
    row["status"] = "CLOSED"
    return row


def test_csv_training_history_is_capped_100_per_symbol(tmp_path: Path):
    trade_csv = tmp_path / "trade_history.csv"
    closed_csv = tmp_path / "trade_closed_history.csv"
    pd.DataFrame(columns=TRADE_COLUMNS).to_csv(trade_csv, index=False, encoding="utf-8-sig")

    rows = []
    symbols = ["BTCUSD", "NAS100", "XAUUSD"]
    for s_idx, symbol in enumerate(symbols):
        for i in range(130):
            row = _blank_row()
            ticket = (s_idx + 1) * 10000 + i
            row.update(
                {
                    "ticket": ticket,
                    "symbol": symbol,
                    "direction": "BUY" if i % 2 == 0 else "SELL",
                    "open_time": f"2026-02-20 09:{i % 60:02d}:00",
                    "close_time": f"2026-02-20 10:{i % 60:02d}:00",
                    "open_ts": 1771510800 + i,
                    "close_ts": 1771514400 + i,
                    "entry_score": 120 + (i % 30),
                    "contra_score_at_entry": 80 + (i % 15),
                    "exit_score": 100 + (i % 20),
                    "profit": float((i % 9) - 4),
                    "points": float((i % 11) - 5),
                }
            )
            rows.append(row)
    pd.DataFrame(rows)[TRADE_COLUMNS].to_csv(closed_csv, index=False, encoding="utf-8-sig")

    read_service = TradeReadService(trade_csv)
    svc = CsvHistoryService(read_service)
    out = svc.get_training_and_history_rows()

    assert len(out["history_rows"]) == 300
    assert len(out["learning_rows"]) == 300
    first = out["learning_rows"][0]
    for key in [
        "loss_quality_label",
        "loss_quality_score",
        "loss_quality_reason",
        "wait_quality_label",
        "wait_quality_score",
        "wait_quality_reason",
    ]:
        assert key in first
