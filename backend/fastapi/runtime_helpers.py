"""Shared runtime helper functions extracted from FastAPI app module."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import pandas as pd
from fastapi import FastAPI


def cache_get(cache: dict, key: str, ttl_sec: float):
    row = cache.get(key)
    if not row:
        return None
    if (time.time() - float(row.get("at", 0.0))) > float(ttl_sec):
        return None
    return row.get("value")


def cache_set(cache: dict, key: str, value) -> None:
    cache[key] = {"at": time.time(), "value": value}


def note_runtime_warning(app: FastAPI, kst, key: str, exc: Exception | None = None) -> None:
    k = str(key or "unknown_warning")
    logger = getattr(app.state, "app_logger", logging.getLogger("backend.fastapi"))
    try:
        counters = getattr(app.state, "runtime_warning_counters", None)
        if not isinstance(counters, dict):
            counters = {}
        row = counters.get(k, {})
        row["count"] = int(row.get("count", 0)) + 1
        row["last_at"] = datetime.now(kst).isoformat(timespec="seconds")
        if exc is not None:
            row["last_error"] = str(exc)
        counters[k] = row
        app.state.runtime_warning_counters = counters
    except Exception as warn_exc:
        logger.warning("[runtime.warn] counter_update_failed(%s): %s", k, warn_exc)
    if exc is None:
        logger.warning("[runtime.warn] %s", k)
    else:
        logger.warning("[runtime.warn] %s: %s", k, exc)


def record_api_latency(app: FastAPI, kst, method: str, path: str, status_code: int, elapsed_ms: float, ok: bool) -> None:
    try:
        key = f"{str(method or 'GET').upper()} {str(path or '')}"
        now_iso = datetime.now(kst).isoformat(timespec="seconds")
        snap = getattr(app.state, "api_latency_snapshot", None)
        if not isinstance(snap, dict):
            snap = {}
        row = snap.get(
            key,
            {
                "count": 0,
                "error_count": 0,
                "last_ms": 0.0,
                "ema_ms": 0.0,
                "max_ms": 0.0,
                "last_status": 0,
                "updated_at": "",
            },
        )
        prev_ema = float(row.get("ema_ms", 0.0) or 0.0)
        alpha = 0.20
        row["count"] = int(row.get("count", 0)) + 1
        row["error_count"] = int(row.get("error_count", 0)) + (0 if ok else 1)
        row["last_ms"] = round(float(elapsed_ms), 3)
        row["ema_ms"] = round(float((prev_ema * (1.0 - alpha)) + (float(elapsed_ms) * alpha)) if prev_ema > 0 else float(elapsed_ms), 3)
        row["max_ms"] = round(max(float(row.get("max_ms", 0.0) or 0.0), float(elapsed_ms)), 3)
        row["last_status"] = int(status_code or 0)
        row["updated_at"] = now_iso
        snap[key] = row
        if len(snap) > 80:
            ordered = sorted(snap.items(), key=lambda kv: str(kv[1].get("updated_at", "")), reverse=True)[:80]
            snap = dict(ordered)
        app.state.api_latency_snapshot = snap
    except Exception:
        return


def sync_open_closed_state(
    *,
    app: FastAPI,
    sync_state: dict,
    sync_lock,
    sync_min_interval_sec: float,
    note_warning,
    force: bool = False,
) -> None:
    now = time.time()
    if (not bool(force)) and ((now - float(sync_state.get("last_ts", 0.0))) < sync_min_interval_sec):
        return
    if not sync_lock.acquire(blocking=False):
        return
    try:
        try:
            app.state.trade_logger.check_closed_trades()
        except Exception as exc:
            note_warning(app, "sync_check_closed_trades_failed", exc)
        try:
            app.state.trade_logger.reconcile_open_trades(lookback_days=120)
        except Exception as exc:
            note_warning(app, "sync_reconcile_open_trades_failed", exc)
        try:
            app.state.trade_read_service.force_refresh()
        except Exception as exc:
            note_warning(app, "sync_trade_read_force_refresh_failed", exc)
        try:
            app.state.mt5_snapshot_service.invalidate_cache("positions_enriched")
        except Exception as exc:
            note_warning(app, "sync_invalidate_positions_cache_failed", exc)
        sync_state["last_ts"] = now
    finally:
        sync_lock.release()


def to_kst_text(value: str, kst) -> str:
    """Normalize datetime-like text to YYYY-MM-DD HH:MM:SS in KST."""
    text = str(value or "").strip()
    if not text:
        return ""
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return text
    try:
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.tz_convert(kst)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text
