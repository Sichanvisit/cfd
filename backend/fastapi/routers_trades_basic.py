"""Basic trades endpoints extracted from monolithic FastAPI app module."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Callable

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import StreamingResponse


def create_trades_basic_router(
    *,
    app: FastAPI,
    cache_get: Callable[[str, float], object],
    cache_set: Callable[[str, object], None],
    sync_open_closed_state: Callable[..., None],
) -> APIRouter:
    router = APIRouter(tags=["trades"])

    @router.get("/trades/summary")
    def trades_summary(sync: bool = False):
        if bool(sync):
            sync_open_closed_state(force=True)
        return app.state.trade_read_service.get_summary()

    @router.get("/trades/recent")
    def trades_recent(limit: int = 20, sync: bool = False):
        if bool(sync):
            sync_open_closed_state(force=True)
        return app.state.trade_read_service.get_recent(limit=limit)

    @router.get("/trades/latest")
    def trades_latest(symbol: str = "", sync: bool = False):
        cache_key = f"trades_latest:{str(symbol or '').upper().strip()}:{1 if bool(sync) else 0}"
        if not bool(sync):
            cached = cache_get(cache_key, ttl_sec=3.0)
            if cached is not None:
                return cached
        if bool(sync):
            sync_open_closed_state(force=True)
        out = app.state.trade_read_service.get_latest(symbol=symbol)
        cache_set(cache_key, out)
        return out

    @router.get("/trades/rows")
    def trades_rows(symbol: str = "", since_ts: int = 0, limit: int = 1000, status: str = "ALL", sync: bool = False):
        limit_norm = max(1, min(2000, int(limit)))
        cache_key = f"trades_rows:{str(symbol or '').upper().strip()}:{int(since_ts or 0)}:{limit_norm}:{str(status or 'ALL').upper().strip()}:{1 if bool(sync) else 0}"
        if not bool(sync):
            cached = cache_get(cache_key, ttl_sec=2.0)
            if cached is not None:
                return cached
        if bool(sync):
            sync_open_closed_state(force=True)
        out = app.state.trade_read_service.get_rows(
            symbol=symbol,
            since_ts=since_ts,
            limit=limit_norm,
            status=status,
        )
        cache_set(cache_key, out)
        return out

    @router.get("/trades/csv-training-history")
    def trades_csv_training_history(
        per_symbol_limit: int = 1000,
        symbols: str = "BTCUSD,NAS100,XAUUSD",
    ):
        symbol_list = [s.strip() for s in str(symbols or "").split(",") if s.strip()]
        return app.state.csv_history_service.get_training_and_history_rows(
            per_symbol_limit=max(1, min(2000, int(per_symbol_limit))),
            symbols=symbol_list,
        )

    @router.get("/trades/stream")
    async def trades_stream(request: Request):
        async def _event_gen():
            prev_token = app.state.trade_read_service.get_change_token()
            keepalive_at = time.time()
            yield "retry: 2500\n\n"
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(2.0)
                token = app.state.trade_read_service.get_change_token()
                now = time.time()
                if token != prev_token:
                    prev_token = token
                    keepalive_at = now
                    payload = json.dumps({"token": token, "ts": int(now)})
                    yield f"event: update\ndata: {payload}\n\n"
                elif (now - keepalive_at) >= 15.0:
                    keepalive_at = now
                    yield "event: ping\ndata: {}\n\n"

        return StreamingResponse(_event_gen(), media_type="text/event-stream")

    @router.get("/trades/closed_recent")
    def trades_closed_recent(limit: int = 100, include_mt5: bool = False, sync: bool = False, lookback_days: int = 1):
        use_mt5 = bool(include_mt5) or bool(sync)
        lookback_days_norm = max(1, min(30, int(lookback_days or 1)))
        cache_key = (
            f"trades_closed_recent:{int(limit)}:{1 if bool(use_mt5) else 0}:"
            f"{1 if bool(sync) else 0}:{lookback_days_norm}"
        )
        if not bool(sync):
            cached = cache_get(cache_key, ttl_sec=8.0)
            if cached is not None:
                return cached
        if bool(use_mt5):
            sync_open_closed_state(force=bool(sync))
        out = app.state.trade_read_service.get_closed_recent(
            limit=limit,
            include_mt5=bool(use_mt5),
            lookback_days=lookback_days_norm,
        )
        cache_set(cache_key, out)
        return out

    return router
