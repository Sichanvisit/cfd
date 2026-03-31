"""
Read-model service for trade CSV backed endpoints.
"""

from __future__ import annotations

import time
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

import pandas as pd

from adapters.mt5_broker_adapter import MT5BrokerAdapter
from adapters.mt5_connection_adapter import connect_to_mt5, disconnect_mt5
from backend.core.trade_constants import DEAL_ENTRY_OUT, DEAL_ENTRY_OUT_BY, DEAL_TYPE_BUY, DEAL_TYPE_SELL
from backend.services.trade_csv_schema import (
    TRADE_COLUMNS,
    epoch_to_kst_text,
    mt5_ts_to_kst_dt,
    normalize_trade_df,
    text_to_kst_epoch,
)
from backend.services.trade_sqlite_store import TradeSqliteStore
from backend.trading.trade_logger import TradeLogger
from ports.broker_port import BrokerPort

logger = logging.getLogger(__name__)


class TradeReadService:
    def __init__(
        self,
        trade_csv: Path,
        trade_logger: TradeLogger | None = None,
        broker: BrokerPort | None = None,
    ):
        self.trade_csv = Path(trade_csv)
        self.closed_trade_csv = self.trade_csv.parent / "trade_closed_history.csv"
        self._trade_logger = trade_logger
        self.broker = broker or MT5BrokerAdapter()
        self._store = TradeSqliteStore(
            db_path=self.trade_csv.parent / "trades.db",
            trade_csv=self.trade_csv,
            closed_trade_csv=self.closed_trade_csv,
        )
        self._store.sync_from_csv(force=False)
        self._cache_lock = Lock()
        self._cache_ttl_sec = 2.0
        # Keep request path fast/stable: do not force CSV->SQLite sync on every read burst.
        # Writer path (TradeLogger) already updates SQLite directly.
        self._store_sync_ttl_sec = 60.0
        self._store_last_sync_at = 0.0
        self._allow_request_path_csv_sync = trade_logger is None
        # Default off: frequent CSV mtime changes can cause per-request DB sync and long lock waits.
        env_sync_on_touch = str(os.getenv("TRADE_READ_SYNC_ON_CSV_TOUCH", "0")).strip() in {"1", "true", "TRUE", "yes", "Y"}
        self._sync_on_csv_touch = bool(env_sync_on_touch or trade_logger is None)
        self._cache = {
            "loaded_at": 0.0,
            "trade_mtime_ns": -1,
            "closed_mtime_ns": -1,
            "trade_df": pd.DataFrame(),
            "closed_df": pd.DataFrame(),
            "change_seq": 0,
        }

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

    @staticmethod
    def _file_mtime_ns(path: Path) -> int:
        try:
            return int(path.stat().st_mtime_ns)
        except Exception:
            return -1

    def _read_trade_df_uncached(self) -> pd.DataFrame:
        try:
            return self._store.read_open_df()
        except Exception:
            return pd.DataFrame()

    def _read_closed_trade_df_uncached(self, base_trade_df: pd.DataFrame | None = None) -> pd.DataFrame:
        try:
            out = self._store.read_closed_df()
            if out.empty:
                return out
            out["ticket"] = pd.to_numeric(out.get("ticket", 0), errors="coerce").fillna(0).astype(int)
            out["close_ts"] = pd.to_numeric(out.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
            return out
        except Exception:
            return pd.DataFrame()

    def _refresh_cache_if_needed(self, force: bool = False) -> None:
        now = time.time()
        trade_mtime_ns = self._file_mtime_ns(self.trade_csv)
        closed_mtime_ns = self._file_mtime_ns(self.closed_trade_csv)
        cached_trade_mtime_ns = int(self._cache.get("trade_mtime_ns", -1))
        cached_closed_mtime_ns = int(self._cache.get("closed_mtime_ns", -1))
        csv_touched = (
            trade_mtime_ns != cached_trade_mtime_ns
            or closed_mtime_ns != cached_closed_mtime_ns
        )
        should_sync_store = (
            force
            or (
                self._allow_request_path_csv_sync
                and ((now - float(self._store_last_sync_at)) >= float(self._store_sync_ttl_sec))
            )
            or (self._sync_on_csv_touch and csv_touched)
        )
        if should_sync_store:
            try:
                # Safety net: if any external writer touched CSV directly, mirror DB follows mtime.
                self._store.sync_from_csv(force=bool(force))
            except Exception as exc:
                logger.warning("CSV->SQLite sync skipped due to error: %s", exc)
            finally:
                self._store_last_sync_at = now
                trade_mtime_ns = self._file_mtime_ns(self.trade_csv)
                closed_mtime_ns = self._file_mtime_ns(self.closed_trade_csv)

        with self._cache_lock:
            unchanged = (
                trade_mtime_ns == int(self._cache.get("trade_mtime_ns", -1))
                and closed_mtime_ns == int(self._cache.get("closed_mtime_ns", -1))
            )
            cache_age = now - float(self._cache.get("loaded_at", 0.0))
            if (not force) and unchanged and cache_age < self._cache_ttl_sec:
                return
            if (not force) and unchanged:
                self._cache["loaded_at"] = now
                return

            trade_df = self._read_trade_df_uncached()
            closed_df = self._read_closed_trade_df_uncached(base_trade_df=trade_df)
            next_change_seq = int(self._cache.get("change_seq", 0)) + 1
            self._cache = {
                "loaded_at": now,
                "trade_mtime_ns": trade_mtime_ns,
                "closed_mtime_ns": closed_mtime_ns,
                "trade_df": trade_df,
                "closed_df": closed_df,
                "change_seq": next_change_seq,
            }

    def invalidate_cache(self) -> None:
        with self._cache_lock:
            next_change_seq = int(self._cache.get("change_seq", 0)) + 1
            self._cache = {
                "loaded_at": 0.0,
                "trade_mtime_ns": -1,
                "closed_mtime_ns": -1,
                "trade_df": pd.DataFrame(),
                "closed_df": pd.DataFrame(),
                "change_seq": next_change_seq,
            }

    def force_refresh(self) -> None:
        """Force CSV->SQLite sync and refresh in-memory read cache."""
        try:
            self._store.sync_from_csv(force=True)
            self._store_last_sync_at = time.time()
        except Exception as exc:
            logger.warning("force_refresh sync_from_csv failed: %s", exc)
        self.invalidate_cache()
        self._refresh_cache_if_needed(force=True)

    def read_trade_df(self) -> pd.DataFrame:
        self._refresh_cache_if_needed()
        with self._cache_lock:
            df = self._cache.get("trade_df", pd.DataFrame())
            return df.copy()

    def read_closed_trade_df(self) -> pd.DataFrame:
        self._refresh_cache_if_needed()
        with self._cache_lock:
            df = self._cache.get("closed_df", pd.DataFrame())
            return df.copy()

    @staticmethod
    def _with_row_ts(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = df.copy()
        out["open_ts"] = pd.to_numeric(out.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
        out["close_ts"] = pd.to_numeric(out.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
        if "open_time" in out.columns:
            parsed_open = out["open_time"].map(text_to_kst_epoch)
            out.loc[out["open_ts"] <= 0, "open_ts"] = pd.to_numeric(parsed_open, errors="coerce").fillna(0).astype(int)
        if "close_time" in out.columns:
            parsed_close = out["close_time"].map(text_to_kst_epoch)
            out.loc[out["close_ts"] <= 0, "close_ts"] = pd.to_numeric(parsed_close, errors="coerce").fillna(0).astype(int)
        out["row_ts"] = out["close_ts"].where(out["close_ts"] > 0, out["open_ts"]).fillna(0).astype(int)
        return out

    @staticmethod
    def _symbol_match_mask(series: pd.Series, symbol: str) -> pd.Series:
        if not symbol:
            return pd.Series([True] * len(series), index=series.index)
        s = str(symbol).upper().strip()
        src = series.fillna("").astype(str).str.upper()
        return src.str.contains(s, na=False)

    def _format_rows(self, frame: pd.DataFrame) -> list[dict]:
        if frame.empty:
            return []
        out = frame.copy()
        for col in ["open_time", "close_time"]:
            if col in out.columns:
                out[col] = out[col].fillna("").astype(str).map(self._to_kst_text)
        str_cols = ["symbol", "direction", "status", "entry_reason", "exit_reason"]
        for col in str_cols:
            if col in out.columns:
                out[col] = out[col].fillna("").astype(str)
        num_float_cols = ["lot", "entry_score", "exit_score", "profit", "open_price", "close_price", "points"]
        num_int_cols = ["ticket", "open_ts", "close_ts", "row_ts"]
        for col in num_float_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
        for col in num_int_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)
        cols = [
            c for c in [
                "ticket",
                "symbol",
                "direction",
                "lot",
                "open_time",
                "open_ts",
                "close_time",
                "close_ts",
                "row_ts",
                "open_price",
                "close_price",
                "points",
                "entry_score",
                "exit_score",
                "profit",
                "status",
                "entry_reason",
                "exit_reason",
            ]
            if c in out.columns
        ]
        return out[cols].to_dict(orient="records")

    def get_change_token(self) -> str:
        # SSE(2s poll) path must stay lightweight; force refresh here can stall API endpoints.
        self._refresh_cache_if_needed(force=False)
        with self._cache_lock:
            return str(int(self._cache.get("change_seq", 0)))

    def get_latest(self, symbol: str = ""):
        out = self.get_summary()
        try:
            latest_open = self._with_row_ts(self._store.query_latest_open(symbol=symbol, limit=1))
            latest_closed = self._with_row_ts(self._store.query_latest_closed(symbol=symbol, limit=1))
        except Exception:
            df = self.read_trade_df()
            closed = self.read_closed_trade_df()
            if symbol:
                mask_open = self._symbol_match_mask(df.get("symbol", pd.Series(dtype=str)), symbol)
                mask_closed = self._symbol_match_mask(closed.get("symbol", pd.Series(dtype=str)), symbol)
                df = df.loc[mask_open].copy() if not df.empty else df
                closed = closed.loc[mask_closed].copy() if not closed.empty else closed
            open_rows = self._with_row_ts(df[df["status"].astype(str).str.upper() == "OPEN"].copy()) if not df.empty else pd.DataFrame()
            closed_rows = self._with_row_ts(closed.copy()) if not closed.empty else pd.DataFrame()
            latest_open = open_rows.sort_values("row_ts", ascending=False).head(1) if not open_rows.empty else pd.DataFrame()
            latest_closed = closed_rows.sort_values("row_ts", ascending=False).head(1) if not closed_rows.empty else pd.DataFrame()
        last_row_ts = 0
        if not latest_open.empty:
            last_row_ts = max(last_row_ts, int(pd.to_numeric(latest_open["row_ts"], errors="coerce").fillna(0).max()))
        if not latest_closed.empty:
            last_row_ts = max(last_row_ts, int(pd.to_numeric(latest_closed["row_ts"], errors="coerce").fillna(0).max()))
        return {
            "exists": bool(out.get("exists", False)),
            "symbol": str(symbol or "").upper().strip(),
            "summary": out.get("summary", {}),
            "latest_open": self._format_rows(latest_open),
            "latest_closed": self._format_rows(latest_closed),
            "last_row_ts": int(last_row_ts),
        }

    def get_rows(self, symbol: str = "", since_ts: int = 0, limit: int = 1000, status: str = "ALL"):
        self._refresh_cache_if_needed()
        status_norm = str(status or "ALL").upper().strip()
        limit_norm = max(1, min(5000, int(limit)))
        since_norm = max(0, int(since_ts or 0))
        try:
            merged = self._store.query_rows(
                status=status_norm,
                symbol=symbol,
                since_ts=since_norm,
                limit=limit_norm + 1,
            )
        except Exception:
            trade_df = self.read_trade_df()
            closed_df = self.read_closed_trade_df()
            if status_norm == "OPEN":
                merged = trade_df[trade_df["status"].astype(str).str.upper() == "OPEN"].copy() if not trade_df.empty else pd.DataFrame()
            elif status_norm == "CLOSED":
                merged = closed_df.copy()
            else:
                open_rows = trade_df[trade_df["status"].astype(str).str.upper() == "OPEN"].copy() if not trade_df.empty else pd.DataFrame()
                merged = pd.concat([open_rows, closed_df], ignore_index=True, sort=False) if not closed_df.empty else open_rows

        if merged.empty:
            return {
                "exists": bool(self.trade_csv.exists() or self.closed_trade_csv.exists()),
                "status": status_norm,
                "symbol": str(symbol or "").upper().strip(),
                "since_ts": since_norm,
                "next_since_ts": since_norm,
                "has_more": False,
                "items": [],
            }

        merged = self._with_row_ts(merged)
        merged = merged.sort_values(["row_ts", "ticket"], ascending=[False, False])
        has_more = len(merged) > limit_norm
        page = merged.head(limit_norm).copy()

        next_since = since_norm
        if not page.empty:
            next_since = int(pd.to_numeric(page["row_ts"], errors="coerce").fillna(0).max())
        return {
            "exists": True,
            "status": status_norm,
            "symbol": str(symbol or "").upper().strip(),
            "since_ts": since_norm,
            "next_since_ts": int(next_since),
            "has_more": bool(has_more),
            "items": self._format_rows(page),
        }

    def _persist_closed_mt5_rows(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        if self._trade_logger is None:
            logger.warning("TradeReadService writer is not configured; skipping closed MT5 row persistence.")
            return 0
        try:
            added = int(self._trade_logger.append_closed_rows(rows))
            if added <= 0:
                logger.warning("No closed MT5 rows were persisted by TradeLogger.")
                return 0
            self.invalidate_cache()
            self._refresh_cache_if_needed(force=True)
            return int(added)
        except Exception as exc:
            logger.exception("Failed to persist closed MT5 rows via TradeLogger: %s", exc)
            return 0

    def get_summary(self):
        df = self.read_trade_df()
        closed = self.read_closed_trade_df()
        if df.empty and closed.empty:
            exists = self.trade_csv.exists() or self.closed_trade_csv.exists()
            return {"exists": exists, "summary": {"rows": 0, "total_rows": 0, "closed_count": 0, "open_count": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "total_pnl": 0.0, "last_closed_time": "", "last_open_time": ""}}

        open_rows = df[df["status"].astype(str).str.upper() == "OPEN"].copy()
        closed["profit"] = pd.to_numeric(closed.get("profit"), errors="coerce").fillna(0.0)
        wins = int((closed["profit"] > 0).sum()) if not closed.empty else 0
        losses = int((closed["profit"] <= 0).sum()) if not closed.empty else 0
        pnl = float(closed["profit"].sum()) if not closed.empty else 0.0
        win_rate = float(wins / len(closed)) if len(closed) > 0 else 0.0

        last_closed_time = ""
        if not closed.empty:
            close_ts = pd.to_numeric(closed.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
            open_ts = pd.to_numeric(closed.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
            key_ts = close_ts.where(close_ts > 0, open_ts)
            if len(key_ts) > 0 and int(key_ts.max()) > 0:
                last_closed_time = epoch_to_kst_text(int(key_ts.max()))

        last_open_time = ""
        if not open_rows.empty:
            open_ts = pd.to_numeric(open_rows.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
            if len(open_ts) > 0 and int(open_ts.max()) > 0:
                last_open_time = epoch_to_kst_text(int(open_ts.max()))

        return {
            "exists": True,
            "summary": {
                "rows": int(len(df)),
                "total_rows": int(len(df) + len(closed)),
                "closed_count": int(len(closed)),
                "open_count": int(len(open_rows)),
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 4),
                "total_pnl": round(pnl, 4),
                "last_closed_time": self._to_kst_text(last_closed_time),
                "last_open_time": self._to_kst_text(last_open_time),
            },
        }

    def get_recent(self, limit: int = 20):
        if not self.trade_csv.exists():
            return {"exists": False, "items": []}

        df = self.read_trade_df()
        if df.empty:
            return {"exists": True, "items": []}

        df["sort_key"] = pd.to_numeric(df.get("open_ts", 0), errors="coerce").fillna(0).astype(int)
        recent = df.sort_values("sort_key", ascending=False).head(max(1, min(200, int(limit))))
        cols = [
            c
            for c in [
                "ticket",
                "symbol",
                "direction",
                "lot",
                "open_time",
                "open_ts",
                "close_time",
                "close_ts",
                "entry_score",
                "exit_score",
                "profit",
                "status",
                "entry_reason",
                "exit_reason",
            ]
            if c in recent.columns
        ]
        out = recent[cols].copy()
        for col in ["open_time", "close_time", "entry_reason", "exit_reason", "symbol", "direction", "status"]:
            if col in out.columns:
                out[col] = out[col].fillna("").astype(str)
        for col in ["open_time", "close_time"]:
            if col in out.columns:
                out[col] = out[col].map(self._to_kst_text)
        for col in ["ticket", "lot", "open_ts", "close_ts", "entry_score", "exit_score", "profit"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
        if "ticket" in out.columns:
            out["ticket"] = out["ticket"].astype(int)
        return {"exists": True, "items": out.to_dict(orient="records")}

    def get_closed_recent(self, limit: int = 100, include_mt5: bool = False, lookback_days: int = 1):
        def _prepare_closed_frame(src: pd.DataFrame) -> pd.DataFrame:
            if src.empty:
                src = pd.DataFrame(
                    columns=[
                        "ticket",
                        "symbol",
                        "direction",
                        "lot",
                        "open_time",
                        "close_time",
                        "entry_score",
                        "exit_score",
                        "profit",
                        "status",
                        "entry_reason",
                        "exit_reason",
                    ]
                )
            # SQLite mirror already keeps close_ts/open_ts normalized.
            # Avoid expensive per-row datetime parsing on every API request.
            src["close_ts"] = pd.to_numeric(
                src["close_ts"] if "close_ts" in src.columns else pd.Series(0, index=src.index),
                errors="coerce",
            ).fillna(0).astype(int)
            open_ts = pd.to_numeric(
                src["open_ts"] if "open_ts" in src.columns else pd.Series(0, index=src.index),
                errors="coerce",
            ).fillna(0).astype(int)
            missing_close = src["close_ts"] <= 0
            if missing_close.any():
                src.loc[missing_close, "close_ts"] = open_ts.loc[missing_close]
            src["_source_rank"] = 0
            return src

        df = self.read_trade_df()
        closed = _prepare_closed_frame(self.read_closed_trade_df())
        if df.empty and closed.empty:
            exists = self.trade_csv.exists() or self.closed_trade_csv.exists()
            return {"exists": exists, "items": []}

        mt5_rows = []
        lookback_days_norm = max(1, min(30, int(lookback_days or 1)))
        if include_mt5 and connect_to_mt5():
            match_df = pd.concat([df.copy(), closed.copy()], ignore_index=True, sort=False)
            for col in ["symbol", "direction", "entry_reason", "exit_reason", "open_time"]:
                if col not in match_df.columns:
                    match_df[col] = ""
            for col in ["ticket", "entry_score", "exit_score", "lot", "open_ts", "open_price"]:
                if col not in match_df.columns:
                    match_df[col] = 0.0
            match_df["ticket"] = pd.to_numeric(match_df["ticket"], errors="coerce").fillna(0).astype(int)
            match_df["_symbol_upper"] = match_df["symbol"].fillna("").astype(str).str.upper().str.strip()
            match_df["_open_dt"] = pd.to_datetime(match_df["open_time"], errors="coerce")

            def _best_csv_match(position_ticket: int, symbol: str, deal_dt: datetime):
                symbol_upper = str(symbol or "").upper().strip()
                deal_dt_ts = pd.Timestamp(deal_dt)
                if getattr(deal_dt_ts, "tzinfo", None) is not None:
                    deal_dt_ts = deal_dt_ts.tz_localize(None)
                by_ticket = match_df[match_df["ticket"] == int(position_ticket)].copy()
                if symbol_upper and not by_ticket.empty:
                    by_ticket = by_ticket[by_ticket["_symbol_upper"] == symbol_upper]
                if by_ticket.empty:
                    return None
                if by_ticket["_open_dt"].notna().any():
                    by_ticket["_dist"] = (by_ticket["_open_dt"] - deal_dt_ts).abs()
                    by_ticket = by_ticket.sort_values(["_dist", "_open_dt"], ascending=[True, False])
                return by_ticket.iloc[0]

            try:
                to_dt = datetime.now()
                from_dt = to_dt - timedelta(days=lookback_days_norm)
                deals = self.broker.history_deals_get(from_dt, to_dt) or []
                target_rows = max(200, min(2000, int(limit) * 3))
                for d in reversed(deals):
                    if len(mt5_rows) >= target_rows:
                        break
                    entry_type = int(getattr(d, "entry", -1))
                    if entry_type not in {int(DEAL_ENTRY_OUT), int(DEAL_ENTRY_OUT_BY)}:
                        continue
                    pos_ticket = int(getattr(d, "position_id", 0) or getattr(d, "ticket", 0) or 0)
                    if pos_ticket <= 0:
                        continue
                    deal_dt = mt5_ts_to_kst_dt(int(getattr(d, "time", 0)))
                    deal_symbol = str(getattr(d, "symbol", "") or "")
                    deal_type = int(getattr(d, "type", -1))
                    direction = "BUY" if deal_type == int(DEAL_TYPE_BUY) else ("SELL" if deal_type == int(DEAL_TYPE_SELL) else "")
                    matched = _best_csv_match(pos_ticket, deal_symbol, deal_dt)

                    entry_reason = ""
                    entry_score = 0.0
                    exit_reason = str(getattr(d, "comment", "") or "").strip()
                    exit_score = 0.0
                    open_time = ""
                    open_ts = 0
                    open_price = 0.0
                    lot = float(getattr(d, "volume", 0.0) or 0.0)
                    if matched is not None:
                        matched_direction = str(matched.get("direction", "") or "").upper().strip()
                        matched_lot = float(pd.to_numeric(matched.get("lot", 0.0), errors="coerce") or 0.0)
                        matched_entry_score = float(pd.to_numeric(matched.get("entry_score", 0.0), errors="coerce") or 0.0)
                        matched_exit_score = float(pd.to_numeric(matched.get("exit_score", 0.0), errors="coerce") or 0.0)
                        matched_open_ts = int(pd.to_numeric(matched.get("open_ts", 0), errors="coerce") or 0)
                        matched_open_price = float(pd.to_numeric(matched.get("open_price", 0.0), errors="coerce") or 0.0)
                        entry_reason = str(matched.get("entry_reason", "") or "").strip()
                        if not exit_reason:
                            exit_reason = str(matched.get("exit_reason", "") or "").strip()
                        open_time = str(matched.get("open_time", "") or "")
                        open_ts = matched_open_ts
                        open_price = matched_open_price
                        entry_score = matched_entry_score
                        exit_score = matched_exit_score
                        if matched_lot > 0:
                            lot = matched_lot
                        if matched_direction in {"BUY", "SELL"}:
                            direction = matched_direction

                    mt5_rows.append(
                        {
                            "ticket": pos_ticket,
                            "deal_ticket": int(getattr(d, "ticket", 0) or 0),
                            "symbol": deal_symbol,
                            "direction": direction,
                            "lot": lot,
                            "open_time": open_time,
                            "open_ts": int(open_ts),
                            "open_price": float(open_price),
                            "close_time": deal_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "close_ts": int(deal_dt.timestamp()) if deal_dt else int(getattr(d, "time", 0) or 0),
                            "close_price": float(getattr(d, "price", 0.0) or 0.0),
                            "entry_score": entry_score,
                            "exit_score": exit_score,
                            "profit": float(getattr(d, "profit", 0.0) or 0.0),
                            "status": "CLOSED",
                            "entry_reason": entry_reason,
                            "exit_reason": exit_reason,
                            "_source_rank": 1,
                        }
                    )
            finally:
                pass  # Do NOT disconnect MT5 here; the session is shared with the trading loop

        if mt5_rows:
            try:
                self._persist_closed_mt5_rows(mt5_rows)
            except Exception as exc:
                logger.warning("Failed to persist closed MT5 rows, continuing without persistence: %s", exc)
            mt5_df = pd.DataFrame(mt5_rows)
            if "close_ts" not in mt5_df.columns:
                mt5_df["close_ts"] = 0
            if "_source_rank" not in mt5_df.columns:
                mt5_df["_source_rank"] = 1
            merged = pd.concat([closed, mt5_df], ignore_index=True, sort=False)
        else:
            merged = closed.copy()

        if merged.empty:
            return {"exists": True, "items": []}

        def _col(name: str, default):
            if name in merged.columns:
                return merged[name]
            return pd.Series([default] * len(merged), index=merged.index)

        merged["ticket"] = pd.to_numeric(_col("ticket", 0), errors="coerce").fillna(0).astype(int)
        merged["deal_ticket"] = pd.to_numeric(_col("deal_ticket", 0), errors="coerce").fillna(0).astype(int)
        merged["close_ts"] = pd.to_numeric(_col("close_ts", 0), errors="coerce").fillna(0).astype(int)
        merged["open_ts"] = pd.to_numeric(_col("open_ts", 0), errors="coerce").fillna(0).astype(int)
        merged["close_price"] = pd.to_numeric(_col("close_price", 0.0), errors="coerce").fillna(0.0)
        merged["lot"] = pd.to_numeric(_col("lot", 0.0), errors="coerce").fillna(0.0)
        merged["profit"] = pd.to_numeric(_col("profit", 0.0), errors="coerce").fillna(0.0)
        open_ref = merged["open_ts"].copy()
        close_ref = merged["close_ts"].copy()
        if "open_time" in merged.columns:
            parsed_open = merged["open_time"].map(text_to_kst_epoch)
            open_ref = open_ref.where(open_ref > 0, pd.to_numeric(parsed_open, errors="coerce").fillna(0).astype(int))
        if "close_time" in merged.columns:
            parsed_close = merged["close_time"].map(text_to_kst_epoch)
            close_ref = close_ref.where(close_ref > 0, pd.to_numeric(parsed_close, errors="coerce").fillna(0).astype(int))
        valid_time = ~((open_ref > 0) & (close_ref > 0) & (close_ref < open_ref))
        merged = merged.loc[valid_time].copy()
        merged["_symbol_upper"] = _col("symbol", "").fillna("").astype(str).str.upper().str.strip()
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
            + "|"
            + merged["deal_ticket"].astype(str)
        )
        merged = merged.sort_values(["_dedup_key", "_source_rank", "close_ts"], ascending=[True, True, False])
        merged = merged.drop_duplicates(subset=["_dedup_key"], keep="first")
        merged = merged.sort_values(["close_ts", "ticket"], ascending=[False, False]).head(max(1, min(5000, int(limit))))

        cols = [
            c
            for c in [
                "ticket",
                "symbol",
                "direction",
                "lot",
                "open_time",
                "close_time",
                "close_ts",
                "entry_score",
                "exit_score",
                "profit",
                "status",
                "entry_reason",
                "exit_reason",
            ]
            if c in merged.columns
        ]
        out = merged[cols].copy()
        for col in ["open_time", "close_time"]:
            if col in out.columns:
                out[col] = out[col].map(self._to_kst_text)
        out["ticket"] = out["ticket"].astype(int)
        if "lot" in out.columns:
            out["lot"] = pd.to_numeric(out["lot"], errors="coerce").fillna(0.0)
        if "entry_score" in out.columns:
            out["entry_score"] = pd.to_numeric(out["entry_score"], errors="coerce").fillna(0.0)
        if "exit_score" in out.columns:
            out["exit_score"] = pd.to_numeric(out["exit_score"], errors="coerce").fillna(0.0)
        if "close_ts" in out.columns:
            out["close_ts"] = pd.to_numeric(out["close_ts"], errors="coerce").fillna(0).astype(int)
        return {"exists": True, "items": out.to_dict(orient="records")}

