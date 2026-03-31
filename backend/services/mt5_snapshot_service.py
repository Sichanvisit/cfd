"""
MT5 snapshot service with short TTL cache.
"""

from __future__ import annotations

import time
import os
import re
import threading
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from adapters.mt5_broker_adapter import MT5BrokerAdapter
from adapters.mt5_connection_adapter import connect_to_mt5, disconnect_mt5
from backend.core.trade_constants import (
    ORDER_TYPE_BUY,
    TIMEFRAME_D1,
    TIMEFRAME_H1,
    TIMEFRAME_M1,
    TIMEFRAME_M5,
    TIMEFRAME_M15,
    TIMEFRAME_M30,
)
from backend.services.exit_profile_router import resolve_exit_profile
from backend.services.trade_csv_schema import mt5_ts_to_kst_text
from backend.services.trade_sqlite_store import TradeSqliteStore
from backend.trading.scorer import Scorer
from backend.trading.trade_logger import TradeLogger
from ports.broker_port import BrokerPort

logger = logging.getLogger(__name__)


class Mt5SnapshotService:
    MT5_STATUS_TTL_SEC = 3.0
    POSITIONS_ENRICHED_TTL_SEC = 1.0

    def __init__(self, trade_csv: Path, trade_logger: TradeLogger, broker: BrokerPort | None = None):
        self.trade_csv = Path(trade_csv)
        self.broker = broker or MT5BrokerAdapter()
        try:
            self.MT5_STATUS_TTL_SEC = max(0.2, float(os.getenv("MT5_STATUS_TTL_SEC", str(self.MT5_STATUS_TTL_SEC)) or self.MT5_STATUS_TTL_SEC))
        except Exception:
            self.MT5_STATUS_TTL_SEC = 3.0
        try:
            self.POSITIONS_ENRICHED_TTL_SEC = max(
                0.1,
                float(
                    os.getenv(
                        "POSITIONS_ENRICHED_TTL_SEC",
                        str(self.POSITIONS_ENRICHED_TTL_SEC),
                    )
                    or self.POSITIONS_ENRICHED_TTL_SEC
                ),
            )
        except Exception:
            self.POSITIONS_ENRICHED_TTL_SEC = 1.0
        self._trade_store = TradeSqliteStore(
            db_path=self.trade_csv.parent / "trades.db",
            trade_csv=self.trade_csv,
            closed_trade_csv=self.trade_csv.parent / "trade_closed_history.csv",
        )
        self._trade_store.sync_from_csv(force=False)
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._scorer = None
        self._trade_logger = trade_logger
        try:
            self._store_sync_ttl_sec = max(0.0, float(os.getenv("MT5_STORE_SYNC_TTL_SEC", "5.0") or 5.0))
        except Exception:
            self._store_sync_ttl_sec = 5.0
        self._store_last_sync_at = 0.0
        try:
            self._positions_refresh_interval_sec = max(0.05, float(os.getenv("MT5_POSITIONS_REFRESH_INTERVAL_SEC", "0.5") or 0.5))
        except Exception:
            self._positions_refresh_interval_sec = 0.5
        self._positions_refresh_event = threading.Event()
        self._positions_thread = None
        self._positions_refresh_requested = False

    def _cache_get(self, key: str, ttl_sec: float):
        with self._cache_lock:
            row = self._cache.get(key)
        if not row:
            return None
        if (time.time() - float(row.get("at", 0.0))) > float(ttl_sec):
            return None
        return row.get("value")

    def _cache_get_any(self, key: str):
        with self._cache_lock:
            row = self._cache.get(key)
        if not row:
            return None, -1.0
        age_sec = max(0.0, time.time() - float(row.get("at", 0.0)))
        return row.get("value"), age_sec

    def _cache_set(self, key: str, value):
        with self._cache_lock:
            self._cache[key] = {"at": time.time(), "value": value}

    def invalidate_cache(self, key: str | None = None):
        with self._cache_lock:
            if key:
                self._cache.pop(str(key), None)
                return
            self._cache.clear()

    @staticmethod
    def _to_kst_text(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        dt = pd.to_datetime(text, errors="coerce")
        if pd.isna(dt):
            return text
        try:
            if getattr(dt, "tzinfo", None) is not None:
                dt = dt.tz_convert("Asia/Seoul")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return text

    def _read_trade_df(self) -> pd.DataFrame:
        try:
            now = time.time()
            if (now - float(self._store_last_sync_at)) >= float(self._store_sync_ttl_sec):
                self._trade_store.sync_from_csv(force=False)
                self._store_last_sync_at = now
            return self._trade_store.read_open_df()
        except Exception:
            return pd.DataFrame()

    def _get_scorer(self):
        if self._scorer is None:
            self._scorer = Scorer()
        return self._scorer

    def _get_trade_logger(self):
        return self._trade_logger

    def start_background_snapshot(self):
        if self._positions_thread is not None and self._positions_thread.is_alive():
            return
        self._positions_refresh_event.clear()
        self._positions_thread = threading.Thread(
            target=self._positions_snapshot_loop,
            name="mt5-positions-snapshot",
            daemon=True,
        )
        self._positions_thread.start()

    def stop_background_snapshot(self):
        self._positions_refresh_event.set()
        t = self._positions_thread
        if t is not None and t.is_alive():
            t.join(timeout=2.0)
        self._positions_thread = None

    def request_positions_refresh(self):
        self._positions_refresh_requested = True

    def _positions_snapshot_loop(self):
        while not self._positions_refresh_event.is_set():
            try:
                out = self._build_positions_enriched_snapshot()
                if isinstance(out, dict):
                    self._cache_set("positions_enriched", out)
            except Exception as exc:
                logger.exception("positions_enriched background refresh failed: %s", exc)
            wait_sec = float(self._positions_refresh_interval_sec)
            if self._positions_refresh_requested:
                self._positions_refresh_requested = False
                wait_sec = 0.05
            self._positions_refresh_event.wait(timeout=wait_sec)

    def _fetch_data(self, symbol, tf_const, count=300):
        rates = self.broker.copy_rates_from_pos(symbol, tf_const, 0, count)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    @staticmethod
    def _position_open_ts(position) -> int:
        for key in ("time", "time_msc", "time_update", "time_update_msc"):
            try:
                v = int(getattr(position, key, 0) or 0)
                if v > 0:
                    # *_msc is milliseconds.
                    if key.endswith("_msc"):
                        return int(v / 1000)
                    return int(v)
            except Exception:
                continue
        return 0

    @staticmethod
    def _now_kst_text() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _estimate_reason_points(reason_text: str) -> int:
        text = str(reason_text or "").strip()
        if not text:
            return 0
        nums = re.findall(r"\(([+-]?\d+)[^)]*\)", text)
        if nums:
            try:
                return int(abs(sum(int(x) for x in nums)))
            except Exception:
                pass
        low = text.lower()
        if "structure:" in low:
            return 150
        if "flow:" in low:
            return 110
        if "trigger:" in low:
            return 80
        if "vp" in low:
            return 90
        return 70

    @staticmethod
    def _symbol_variation(symbol: str) -> int:
        s = str(symbol or "").upper().strip()
        if not s:
            return 0
        return (sum(ord(ch) for ch in s) % 17) - 8

    def _score_fallback_from_reason(self, symbol: str, direction: str, entry_reason: str) -> tuple[float, float]:
        base = max(40, int(self._estimate_reason_points(entry_reason)))
        tweak = self._symbol_variation(symbol)
        dir_tweak = 3 if str(direction).upper() == "BUY" else -3
        entry = float(max(35, min(360, base + tweak + dir_tweak)))
        contra = float(max(20, min(260, int(round(entry * 0.58)))))
        return entry, contra

    def _infer_entry_context(self, symbol: str, direction: str):
        try:
            tick = self.broker.symbol_info_tick(symbol)
            if not tick:
                return 0.0, 0.0, []
            df_all = {
                "1M": self._fetch_data(symbol, TIMEFRAME_M1, 300),
                "5M": self._fetch_data(symbol, TIMEFRAME_M5, 300),
                "15M": self._fetch_data(symbol, TIMEFRAME_M15, 300),
                "30M": self._fetch_data(symbol, TIMEFRAME_M30, 300),
                "1H": self._fetch_data(symbol, TIMEFRAME_H1, 300),
                "1D": self._fetch_data(symbol, TIMEFRAME_D1, 120),
            }
            # m1 is optional for trigger detail; core scorer only needs 15M/H1.
            if df_all["15M"] is None or df_all["1H"] is None:
                return 0.0, 0.0, []
            res = self._get_scorer().get_score(symbol, tick, df_all)
            buy = float(res.get("buy", {}).get("total", 0) or 0.0)
            sell = float(res.get("sell", {}).get("total", 0) or 0.0)
            if direction.upper() == "BUY":
                reasons = [str(x) for x in (res.get("buy", {}).get("reasons", []) or [])[:6]]
                return buy, sell, reasons
            reasons = [str(x) for x in (res.get("sell", {}).get("reasons", []) or [])[:6]]
            return sell, buy, reasons
        except Exception:
            return 0.0, 0.0, []

    def get_mt5_status(self):
        cached = self._cache_get("mt5_status", ttl_sec=self.MT5_STATUS_TTL_SEC)
        if cached is not None:
            return cached

        ok = connect_to_mt5()
        if not ok:
            out = {"connected": False, "account": None, "positions": []}
            self._cache_set("mt5_status", out)
            return out

        try:
            account = self.broker.account_info()
            positions = self.broker.positions_get() or []
            pos_items = []
            for p in positions:
                pos_items.append(
                    {
                        "ticket": int(p.ticket),
                        "symbol": p.symbol,
                        "type": int(p.type),
                        "volume": float(p.volume),
                        "profit": float(p.profit),
                        "price_open": float(p.price_open),
                    }
                )

            account_item = None
            if account:
                account_item = {
                    "login": int(account.login),
                    "server": account.server,
                    "balance": float(account.balance),
                    "equity": float(account.equity),
                    "margin": float(account.margin),
                    "profit": float(account.profit),
                }
            out = {"connected": True, "account": account_item, "positions": pos_items}
            self._cache_set("mt5_status", out)
            return out
        finally:
            disconnect_mt5()

    def _build_positions_enriched_snapshot(self):
        ok = connect_to_mt5()
        trade_df = self._read_trade_df()

        if not ok:
            if trade_df.empty:
                out = {"connected": False, "items": [], "source": "empty_fallback", "reason": "mt5_connect_failed"}
                self._cache_set("positions_enriched", out)
                return out
            open_df = trade_df[trade_df["status"] == "OPEN"].copy()
            fallback_items = []
            for _, row in open_df.iterrows():
                reasons = [s.strip() for s in str(row.get("entry_reason", "")).split(",") if s.strip()]
                if not reasons:
                    reasons = ["[SNAPSHOT] context unavailable"]
                fallback_items.append(
                    {
                        "ticket": int(row.get("ticket", 0)),
                        "symbol": str(row.get("symbol", "")),
                        "direction": str(row.get("direction", "")),
                        "lot": float(pd.to_numeric(row.get("lot", 0.0), errors="coerce") or 0.0),
                        "profit": float(row.get("profit", 0.0) or 0.0),
                        "price_open": float(row.get("open_price", 0.0) or 0.0),
                        "open_time": self._to_kst_text(str(row.get("open_time", "") or "")),
                        "entry_score": float(row.get("entry_score", 0.0) or 0.0),
                        "contra_score_at_entry": float(row.get("contra_score_at_entry", 0.0) or 0.0),
                        "entry_reasons": reasons,
                        "source": "csv_fallback",
                    }
                )
            out = {"connected": False, "items": fallback_items, "source": "csv_fallback", "reason": "mt5_connect_failed"}
            self._cache_set("positions_enriched", out)
            return out

        try:
            positions = self.broker.positions_get() or []
            open_df = trade_df[trade_df["status"] == "OPEN"].copy() if not trade_df.empty else pd.DataFrame()

            items = []
            for p in positions:
                ticket = int(p.ticket)
                row = None
                if not open_df.empty:
                    hit = open_df[open_df["ticket"] == ticket]
                    if not hit.empty:
                        row = hit.iloc[-1]
                if row is None and not trade_df.empty:
                    hit = trade_df[trade_df["ticket"] == ticket]
                    if not hit.empty:
                        row = hit.iloc[-1]

                entry_reason = ""
                entry_score = 0.0
                contra_score = 0.0
                open_time = ""
                if row is not None:
                    entry_reason = str(row.get("entry_reason", "") or "")
                    entry_score = float(row.get("entry_score", 0.0) or 0.0)
                    contra_score = float(row.get("contra_score_at_entry", 0.0) or 0.0)
                    open_time = str(row.get("open_time", "") or "")
                if not open_time:
                    pos_ts = self._position_open_ts(p)
                    if pos_ts > 0:
                        open_time = mt5_ts_to_kst_text(pos_ts)
                    else:
                        open_time = self._now_kst_text()
                # Fallback: when snapshot is not ready yet, infer now and backfill CSV.
                if (not str(entry_reason).strip()) or float(entry_score) <= 0.0:
                    direction = "BUY" if int(p.type) == int(ORDER_TYPE_BUY) else "SELL"
                    existing_setup_id = str((row or {}).get("entry_setup_id", "") or "").strip().lower()
                    existing_management_profile_id = str((row or {}).get("management_profile_id", "") or "").strip().lower()
                    existing_invalidation_id = str((row or {}).get("invalidation_id", "") or "").strip().lower()
                    existing_exit_profile = str((row or {}).get("exit_profile", "") or "").strip().lower()
                    snapshot_setup_id = existing_setup_id or "snapshot_restored_auto"
                    snapshot_exit_profile = existing_exit_profile or resolve_exit_profile(
                        management_profile_id=existing_management_profile_id,
                        invalidation_id=existing_invalidation_id,
                        entry_setup_id=snapshot_setup_id,
                        fallback_profile="neutral",
                    )
                    infer_entry, infer_contra, infer_reasons = self._infer_entry_context(p.symbol, direction)
                    if infer_entry > 0:
                        entry_score = infer_entry
                    if infer_contra > 0:
                        contra_score = infer_contra
                    if infer_reasons:
                        entry_reason = ", ".join(infer_reasons)
                    else:
                        entry_reason = "[SNAPSHOT] context unavailable"
                    if float(entry_score) <= 0.0 or float(contra_score) <= 0.0:
                        est_entry, est_contra = self._score_fallback_from_reason(
                            p.symbol,
                            direction,
                            entry_reason,
                        )
                        if float(entry_score) <= 0.0:
                            entry_score = est_entry
                        if float(contra_score) <= 0.0:
                            contra_score = est_contra
                    try:
                        self._get_trade_logger().upsert_open_snapshots(
                            [
                                {
                                    "ticket": int(p.ticket),
                                    "symbol": p.symbol,
                                    "direction": direction,
                                    "lot": float(p.volume),
                                    "open_price": float(p.price_open),
                                    "open_ts": self._position_open_ts(p),
                                    "entry_score": int(entry_score or 0),
                                    "contra_score_at_entry": int(contra_score or 0),
                                    "entry_reason": entry_reason,
                                    "entry_setup_id": snapshot_setup_id,
                                    "management_profile_id": existing_management_profile_id,
                                    "invalidation_id": existing_invalidation_id,
                                    "exit_profile": snapshot_exit_profile,
                                    "source": "SNAPSHOT",
                                    "indicators": {},
                                }
                            ]
                        )
                    except Exception:
                        pass

                reason_list = [s.strip() for s in entry_reason.split(",") if s.strip()]
                if not reason_list:
                    reason_list = ["[SNAPSHOT] 湲곕낯 洹쇨굅"]
                if float(entry_score) <= 0.0 or float(contra_score) <= 0.0:
                    est_entry, est_contra = self._score_fallback_from_reason(
                        p.symbol,
                        "BUY" if int(p.type) == int(ORDER_TYPE_BUY) else "SELL",
                        entry_reason,
                    )
                    if float(entry_score) <= 0.0:
                        entry_score = est_entry
                    if float(contra_score) <= 0.0:
                        contra_score = est_contra
                items.append(
                    {
                        "ticket": ticket,
                        "symbol": p.symbol,
                        "direction": "BUY" if int(p.type) == int(ORDER_TYPE_BUY) else "SELL",
                        "lot": float(p.volume),
                        "profit": float(p.profit),
                        "price_open": float(p.price_open),
                        "open_time": self._to_kst_text(open_time),
                        "entry_score": entry_score,
                        "contra_score_at_entry": contra_score,
                        "entry_reasons": reason_list,
                        "source": "mt5_live",
                    }
                )

            out = {"connected": True, "items": items, "source": "mt5_live"}
            return out
        finally:
            disconnect_mt5()

    def _build_positions_with_timeout(self, timeout_sec: float):
        out_holder = {"value": None, "error": None}

        def _runner():
            try:
                out_holder["value"] = self._build_positions_enriched_snapshot()
            except Exception as exc:
                out_holder["error"] = exc

        t = threading.Thread(target=_runner, name="positions-refresh-timebox", daemon=True)
        t.start()
        t.join(timeout=max(0.05, float(timeout_sec)))
        if t.is_alive():
            return None
        if out_holder["error"] is not None:
            raise out_holder["error"]
        return out_holder["value"]

    @staticmethod
    def _stale_payload(payload, age_sec: float):
        if not isinstance(payload, dict):
            return payload
        out = dict(payload)
        out["_stale"] = True
        out["_cache_age_sec"] = round(float(age_sec), 3)
        if "_stale_reason" not in out:
            out["_stale_reason"] = "cache_fallback"
        return out

    def get_positions_enriched(self, force_refresh: bool = False, timeout_ms: int = 250):
        ttl_sec = max(self.POSITIONS_ENRICHED_TTL_SEC, self._positions_refresh_interval_sec * 4.0)
        cached_fresh = self._cache_get("positions_enriched", ttl_sec=ttl_sec)
        cached_any, cached_age = self._cache_get_any("positions_enriched")

        if not bool(force_refresh):
            if cached_fresh is not None:
                return cached_fresh
            # stale cache first: avoid request-path blocking while background thread catches up.
            if cached_any is not None:
                self.request_positions_refresh()
                return self._stale_payload(cached_any, cached_age)
            self.request_positions_refresh()
            return {"connected": False, "items": [], "source": "empty_fallback", "reason": "snapshot_not_ready"}

        timeout_sec = max(0.05, float(int(timeout_ms or 0)) / 1000.0)
        try:
            out = self._build_positions_with_timeout(timeout_sec=timeout_sec)
            if isinstance(out, dict):
                self._cache_set("positions_enriched", out)
                return out
            logger.warning("positions_enriched refresh timed out (timeout_sec=%.3f)", timeout_sec)
        except Exception as exc:
            logger.warning("positions_enriched refresh failed: %s", exc)

        self.request_positions_refresh()
        if cached_any is not None:
            return self._stale_payload(cached_any, cached_age)
        return {"connected": False, "items": [], "source": "empty_fallback", "reason": "refresh_failed"}

