"""Closed-row append and micro-batch flush helpers for TradeLogger."""

from __future__ import annotations

import logging
import time
from threading import Event

import pandas as pd

_log = logging.getLogger(__name__)


def append_to_closed_file(owner, rows_df: pd.DataFrame) -> None:
    if rows_df is None or rows_df.empty:
        return
    owner._ensure_closed_file()
    with owner._file_guard(f"{owner.closed_filepath}.lock", owner._closed_lock):
        try:
            base = pd.read_csv(owner.closed_filepath, encoding="utf-8-sig")
            base = owner._normalize_dataframe(base)
        except UnicodeDecodeError:
            try:
                try:
                    base = pd.read_csv(owner.closed_filepath, encoding="utf-8")
                    base = owner._normalize_dataframe(base)
                except UnicodeDecodeError:
                    base = pd.read_csv(owner.closed_filepath, encoding="cp949")
                    base = owner._normalize_dataframe(base)
            except Exception:
                base = pd.DataFrame(columns=owner._columns())
        except Exception:
            base = pd.DataFrame(columns=owner._columns())
        add = owner._normalize_dataframe(rows_df.copy())
        add["status"] = "CLOSED"
        add["profit"] = pd.to_numeric(add.get("profit", 0.0), errors="coerce").fillna(0.0)
        if add.empty:
            return
        base["profit"] = pd.to_numeric(base.get("profit", 0.0), errors="coerce").fillna(0.0)
        merged = pd.concat([base, add], ignore_index=True)
        merged["ticket"] = pd.to_numeric(merged["ticket"], errors="coerce").fillna(0).astype(int)
        merged["close_ts"] = pd.to_numeric(merged["close_ts"], errors="coerce").fillna(0).astype(int)
        merged["close_price"] = pd.to_numeric(merged.get("close_price", 0.0), errors="coerce").fillna(0.0)
        merged["lot"] = pd.to_numeric(merged.get("lot", 0.0), errors="coerce").fillna(0.0)
        merged["_symbol_upper"] = merged["symbol"].fillna("").astype(str).str.upper().str.strip()
        merged["_dedup_key"] = (
            merged["ticket"].astype(str)
            + "|"
            + merged["_symbol_upper"]
            + "|"
            + merged["close_ts"].astype(str)
            + "|"
            + merged["close_price"].round(6).astype(str)
            + "|"
            + merged["lot"].round(4).astype(str)
            + "|"
            + merged["profit"].round(2).astype(str)
        )
        merged = merged.sort_values(["_dedup_key", "close_ts"], ascending=[True, False])
        merged = merged.drop_duplicates(subset=["_dedup_key"], keep="first")
        merged = merged.drop(columns=["_symbol_upper", "_dedup_key"], errors="ignore")
        owner._atomic_write_df(owner.closed_filepath, merged)
    owner._upsert_closed_rows_to_store(add)


def append_closed_rows(owner, rows: list[dict]) -> int:
    if not rows:
        return 0
    add = owner._normalize_dataframe(pd.DataFrame(rows))
    if add.empty:
        return 0
    add["status"] = "CLOSED"
    add["ticket"] = pd.to_numeric(add.get("ticket", 0), errors="coerce").fillna(0).astype(int)
    add = add[add["ticket"] > 0].copy()
    if add.empty:
        return 0
    req = {"df": add, "event": Event(), "error": None}
    is_leader = False
    with owner._closed_batch_cv:
        owner._closed_batch_pending.append(req)
        if not owner._closed_batch_leader_active:
            owner._closed_batch_leader_active = True
            is_leader = True
        owner._closed_batch_cv.notify_all()
    if is_leader:
        run_closed_batch_leader_loop(owner)
    wait_timeout = max(5.0, float(owner._closed_batch_window_sec) * 40.0)
    if not req["event"].wait(timeout=wait_timeout):
        raise TimeoutError("Timed out waiting for closed-row batch flush completion.")
    if req["error"] is not None:
        raise RuntimeError(f"Closed-row batch flush failed: {req['error']}")
    return int(len(add))


def run_closed_batch_leader_loop(owner) -> None:
    while True:
        deadline = time.time() + float(owner._closed_batch_window_sec)
        while True:
            remain = deadline - time.time()
            if remain <= 0:
                break
            with owner._closed_batch_cv:
                owner._closed_batch_cv.wait(timeout=remain)
        with owner._closed_batch_cv:
            batch = list(owner._closed_batch_pending)
            owner._closed_batch_pending = []
        if not batch:
            with owner._closed_batch_cv:
                if not owner._closed_batch_pending:
                    owner._closed_batch_leader_active = False
                    owner._closed_batch_cv.notify_all()
                    return
            continue
        flush_exc = None
        try:
            batch_df = pd.concat([item["df"] for item in batch], ignore_index=True, sort=False)
            append_to_closed_file(owner, batch_df)
        except Exception as exc:
            flush_exc = exc
            _log.exception("Failed to flush closed-row micro-batch: %s", exc)
        for item in batch:
            item["error"] = flush_exc
            try:
                item["event"].set()
            except Exception:
                pass
        with owner._closed_batch_cv:
            if not owner._closed_batch_pending:
                owner._closed_batch_leader_active = False
                owner._closed_batch_cv.notify_all()
                return
