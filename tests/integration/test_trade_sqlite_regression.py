from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.services.trade_csv_schema import TRADE_COLUMNS
from backend.services.trade_read_service import TradeReadService
from backend.services.trade_sqlite_store import TradeSqliteStore


def _blank_row() -> dict:
    row = {c: "" for c in TRADE_COLUMNS}
    for c in [
        "ticket",
        "lot",
        "open_ts",
        "open_price",
        "entry_score",
        "contra_score_at_entry",
        "close_ts",
        "close_price",
        "profit",
        "points",
        "exit_score",
    ]:
        row[c] = 0
    row["status"] = "OPEN"
    return row


def _row(**kwargs) -> dict:
    row = _blank_row()
    row.update(kwargs)
    return row


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for c in TRADE_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[TRADE_COLUMNS]
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _build_fixture(tmp_path: Path) -> tuple[Path, Path]:
    trade_csv = tmp_path / "trade_history.csv"
    closed_csv = tmp_path / "trade_closed_history.csv"

    trade_rows = [
        _row(ticket=1001, symbol="NAS100", direction="BUY", lot=0.1, open_time="2026-02-20 09:00:00", open_ts=1771510800, open_price=10.0, entry_score=180, status="OPEN"),
        _row(ticket=1002, symbol="BTCUSD", direction="SELL", lot=0.2, open_time="2026-02-20 09:10:00", open_ts=1771511400, open_price=20.0, entry_score=190, status="OPEN"),
        # Legacy CLOSED row still in trade_history.csv
        _row(ticket=2001, symbol="XAUUSD", direction="BUY", lot=0.1, open_time="2026-02-20 08:00:00", open_ts=1771507200, close_time="2026-02-20 08:30:00", close_ts=1771509000, close_price=30.0, profit=15.0, exit_score=120, status="CLOSED"),
    ]
    closed_rows = [
        _row(ticket=2001, symbol="XAUUSD", direction="BUY", lot=0.1, open_time="2026-02-20 08:00:00", open_ts=1771507200, close_time="2026-02-20 08:30:00", close_ts=1771509000, close_price=30.0, profit=15.0, exit_score=120, status="CLOSED"),
        _row(ticket=2002, symbol="NAS100", direction="SELL", lot=0.1, open_time="2026-02-20 08:40:00", open_ts=1771509600, close_time="2026-02-20 08:55:00", close_ts=1771510500, close_price=11.0, profit=-5.0, exit_score=95, status="CLOSED"),
    ]

    _write_rows(trade_csv, trade_rows)
    _write_rows(closed_csv, closed_rows)
    return trade_csv, closed_csv


def test_summary_latest_and_dedup(tmp_path: Path):
    trade_csv, _ = _build_fixture(tmp_path)
    svc = TradeReadService(trade_csv)

    summary = svc.get_summary()["summary"]
    latest = svc.get_latest()

    assert summary["open_count"] == 2
    # ticket=2001 exists in both CSVs but must be deduped to one CLOSED row.
    assert summary["closed_count"] == 2
    assert summary["total_rows"] == 4
    assert latest["last_row_ts"] > 0
    assert isinstance(latest["latest_closed"], list)


def test_rows_since_and_change_token(tmp_path: Path):
    trade_csv, closed_csv = _build_fixture(tmp_path)
    svc = TradeReadService(trade_csv)

    initial = svc.get_rows(status="CLOSED", since_ts=0, limit=100)
    assert len(initial["items"]) == 2
    old_max_ts = int(initial["next_since_ts"])
    token_before = svc.get_change_token()

    # Append a new closed row to CSV and ensure token + since query reflect it.
    closed_df = pd.read_csv(closed_csv)
    new_row = _row(
        ticket=3001,
        symbol="BTCUSD",
        direction="BUY",
        lot=0.3,
        open_time="2026-02-20 09:20:00",
        open_ts=1771512000,
        close_time="2026-02-20 09:40:00",
        close_ts=old_max_ts + 120,
        close_price=25.0,
        profit=12.5,
        exit_score=140,
        status="CLOSED",
    )
    closed_df = pd.concat([closed_df, pd.DataFrame([new_row])], ignore_index=True)
    closed_df.to_csv(closed_csv, index=False, encoding="utf-8-sig")

    token_after = svc.get_change_token()
    delta = svc.get_rows(status="CLOSED", since_ts=old_max_ts, limit=20)

    assert token_after != token_before
    assert len(delta["items"]) >= 1
    assert any(int(x.get("ticket", 0)) == 3001 for x in delta["items"])


def test_sqlite_mirror_consistency(tmp_path: Path):
    trade_csv, closed_csv = _build_fixture(tmp_path)
    store = TradeSqliteStore(tmp_path / "trades.db", trade_csv, closed_csv)

    changed = store.sync_from_csv(force=True)
    open_df = store.read_open_df()
    closed_df = store.read_closed_df()

    assert changed is True
    assert len(open_df) == 2
    assert len(closed_df) == 2
    assert set(closed_df["ticket"].astype(int).tolist()) == {2001, 2002}


def test_sync_supports_cp949_csv(tmp_path: Path):
    trade_csv, closed_csv = _build_fixture(tmp_path)
    df = pd.read_csv(trade_csv)
    df.to_csv(trade_csv, index=False, encoding="cp949")

    store = TradeSqliteStore(tmp_path / "trades.db", trade_csv, closed_csv)
    changed = store.sync_from_csv(force=True)
    open_df = store.read_open_df()

    assert changed is True
    assert len(open_df) == 2


def test_sync_keeps_existing_rows_when_csv_temporarily_broken(tmp_path: Path):
    trade_csv, closed_csv = _build_fixture(tmp_path)
    store = TradeSqliteStore(tmp_path / "trades.db", trade_csv, closed_csv)
    assert store.sync_from_csv(force=True) is True
    before = store.read_open_df()
    assert len(before) == 2

    # Simulate an external writer leaving CSV in a temporarily invalid state.
    trade_csv.write_text('ticket,symbol,status\n1,"BROKEN,OPEN\n', encoding="utf-8")
    changed = store.sync_from_csv(force=True)
    after = store.read_open_df()

    assert changed is False
    assert len(after) == len(before)


def test_open_trade_context_fast_path_and_patch(tmp_path: Path):
    trade_csv, closed_csv = _build_fixture(tmp_path)
    store = TradeSqliteStore(tmp_path / "trades.db", trade_csv, closed_csv)
    assert store.sync_from_csv(force=True) is True

    ctx = store.get_open_trade_context(1001)
    assert isinstance(ctx, dict)
    assert str(ctx.get("symbol", "")) == "NAS100"

    patched = store.patch_open_trade_fields(
        1001,
        {
            "exit_policy_stage": "continuation_hold_surface",
            "exit_wait_bridge_status": "runner_preservation_active",
        },
    )

    assert patched is True
    ctx_after = store.get_open_trade_context(1001)
    assert str(ctx_after.get("exit_policy_stage", "")) == "continuation_hold_surface"
    assert str(ctx_after.get("exit_wait_bridge_status", "")) == "runner_preservation_active"
