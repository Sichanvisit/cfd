"""
Runtime entry policies: session, ATR normalization, slippage capture.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from zoneinfo import ZoneInfo

from backend.core.config import Config


@dataclass
class SessionPolicyDecision:
    threshold_mult: float
    session_name: str
    weekday: int
    sample_n: int


@dataclass
class AtrPolicyDecision:
    threshold_mult: float
    atr_ratio: float


@dataclass
class SlippageSnapshot:
    entry_request_price: float
    entry_fill_price: float
    entry_slippage_points: float
    exit_request_price: float = 0.0
    exit_fill_price: float = 0.0
    exit_slippage_points: float = 0.0


class SessionPolicy:
    def __init__(self):
        self._profile = {"updated_at": 0.0, "by_symbol_bucket": {}}
        try:
            self._tz = ZoneInfo(str(getattr(Config, "TIMEZONE", "Asia/Seoul") or "Asia/Seoul"))
        except Exception:
            self._tz = ZoneInfo("Asia/Seoul")

    @staticmethod
    def _session_name(hour: int) -> str:
        h = int(hour) % 24
        if 0 <= h < 8:
            return "ASIA"
        if 8 <= h < 16:
            return "EUROPE"
        return "USA"

    def _refresh_if_needed(self) -> None:
        if not bool(getattr(Config, "ENABLE_SESSION_POLICY", True)):
            return
        now_s = time.time()
        ttl = max(60, int(getattr(Config, "SESSION_POLICY_REFRESH_SEC", 300)))
        if (now_s - float(self._profile.get("updated_at", 0.0))) < ttl:
            return

        csv_path = Path(str(getattr(Config, "CLOSED_TRADE_CSV_PATH", r"data\trades\trade_closed_history.csv")))
        if not csv_path.exists():
            self._profile["updated_at"] = now_s
            return

        try:
            try:
                frame = pd.read_csv(csv_path, encoding="utf-8-sig")
            except Exception:
                frame = pd.read_csv(csv_path, encoding="cp949")
        except Exception:
            self._profile["updated_at"] = now_s
            return
        if frame is None or frame.empty:
            self._profile["updated_at"] = now_s
            return

        work = frame.copy()
        work["profit"] = pd.to_numeric(work.get("profit", 0.0), errors="coerce").fillna(0.0)
        work["symbol"] = work.get("symbol", "").fillna("").astype(str).str.upper().str.strip()
        work["open_time"] = pd.to_datetime(work.get("open_time", ""), errors="coerce")
        work = work.dropna(subset=["open_time"])
        if work.empty:
            self._profile["updated_at"] = now_s
            return
        if getattr(work["open_time"].dt, "tz", None) is None:
            work["open_time"] = work["open_time"].dt.tz_localize(self._tz)
        else:
            work["open_time"] = work["open_time"].dt.tz_convert(self._tz)
        work["weekday"] = work["open_time"].dt.weekday
        work["session"] = work["open_time"].dt.hour.map(self._session_name)

        min_n = max(10, int(getattr(Config, "SESSION_POLICY_MIN_SAMPLES", 24)))
        strength = float(getattr(Config, "SESSION_POLICY_STRENGTH", 0.18))
        mult_min = float(getattr(Config, "SESSION_POLICY_MULT_MIN", 0.90))
        mult_max = float(getattr(Config, "SESSION_POLICY_MULT_MAX", 1.10))

        by_symbol_bucket = {}
        for sym, part in work.groupby("symbol", dropna=False):
            sym = str(sym or "").strip().upper()
            if not sym:
                continue
            baseline = float(part["profit"].mean())
            scale = max(1.0, float(part["profit"].abs().median()))
            out = {}
            for (session, weekday), sub in part.groupby(["session", "weekday"], dropna=False):
                n = int(len(sub))
                if n < min_n:
                    continue
                edge = (float(sub["profit"].mean()) - baseline) / scale
                score = float(pd.Series([edge]).clip(lower=-3.0, upper=3.0).iloc[0])
                score = float(math.tanh(score))
                raw_mult = 1.0 - (score * strength)
                shrink = float(n / (n + min_n))
                mult = ((1.0 - shrink) * 1.0) + (shrink * raw_mult)
                key = f"{str(session).upper()}:{int(weekday)}"
                out[key] = {"mult": float(max(mult_min, min(mult_max, mult))), "n": n}
            by_symbol_bucket[sym] = out
        self._profile = {"updated_at": now_s, "by_symbol_bucket": by_symbol_bucket}

    def get_threshold_mult(self, symbol: str, now_dt: datetime | None = None) -> SessionPolicyDecision:
        self._refresh_if_needed()
        dt = now_dt or datetime.now(self._tz)
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=self._tz)
        session = self._session_name(int(dt.hour))
        weekday = int(dt.weekday())
        key = f"{session}:{weekday}"
        by_symbol = dict(self._profile.get("by_symbol_bucket", {}) or {})
        sym = str(symbol or "").upper().strip()
        node = dict(by_symbol.get(sym, {}) or {}).get(key, {})
        mult = float(node.get("mult", 1.0) or 1.0)
        n = int(node.get("n", 0) or 0)
        return SessionPolicyDecision(threshold_mult=mult, session_name=session, weekday=weekday, sample_n=n)


class AtrThresholdPolicy:
    def get_threshold_mult(self, df_all: dict) -> AtrPolicyDecision:
        if not bool(getattr(Config, "ENABLE_ATR_THRESHOLD_POLICY", True)):
            return AtrPolicyDecision(threshold_mult=1.0, atr_ratio=1.0)
        m15 = (df_all or {}).get("15M")
        if m15 is None or m15.empty or len(m15) < 30:
            return AtrPolicyDecision(threshold_mult=1.0, atr_ratio=1.0)

        period = max(5, int(getattr(Config, "ATR_POLICY_PERIOD", 14)))
        ref_lookback = max(period + 10, int(getattr(Config, "ATR_POLICY_REF_LOOKBACK", 96)))
        exp = float(getattr(Config, "ATR_POLICY_THRESHOLD_EXP", 0.35))
        mult_min = float(getattr(Config, "ATR_POLICY_MIN_MULT", 0.85))
        mult_max = float(getattr(Config, "ATR_POLICY_MAX_MULT", 1.25))

        frame = m15[["high", "low", "close"]].tail(ref_lookback + period + 5).copy()
        frame["high"] = pd.to_numeric(frame["high"], errors="coerce")
        frame["low"] = pd.to_numeric(frame["low"], errors="coerce")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna()
        if len(frame) < (period + 5):
            return AtrPolicyDecision(threshold_mult=1.0, atr_ratio=1.0)

        pc = frame["close"].shift(1)
        tr = pd.concat(
            [
                (frame["high"] - frame["low"]).abs(),
                (frame["high"] - pc).abs(),
                (frame["low"] - pc).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(period).mean().dropna()
        if atr.empty:
            return AtrPolicyDecision(threshold_mult=1.0, atr_ratio=1.0)

        atr_cur = float(atr.iloc[-1])
        atr_ref = float(atr.tail(ref_lookback).median()) if len(atr) > 0 else atr_cur
        if atr_ref <= 0:
            return AtrPolicyDecision(threshold_mult=1.0, atr_ratio=1.0)
        ratio = max(0.2, min(5.0, atr_cur / atr_ref))
        mult = max(mult_min, min(mult_max, float(ratio ** exp)))
        return AtrPolicyDecision(threshold_mult=float(mult), atr_ratio=float(ratio))


class SlippagePolicy:
    @staticmethod
    def _point_value(app, symbol: str) -> float:
        try:
            info = app.broker.symbol_info(symbol)
            point = float(getattr(info, "point", 0.0) or 0.0)
            if point > 0:
                return point
        except Exception:
            pass
        return 1.0

    def capture_entry(self, app, symbol: str, action: str, ticket: int, tick) -> SlippageSnapshot:
        side = str(action or "").upper()
        req = float(getattr(tick, "ask", 0.0) if side == "BUY" else getattr(tick, "bid", 0.0) or 0.0)
        fill = req
        try:
            for _ in range(4):
                positions = app.broker.positions_get(symbol=symbol) or []
                hit = next((p for p in positions if int(getattr(p, "ticket", 0) or 0) == int(ticket)), None)
                if hit is not None:
                    px = float(getattr(hit, "price_open", 0.0) or 0.0)
                    if px > 0:
                        fill = px
                        break
                time.sleep(0.05)
        except Exception:
            fill = req
        point = self._point_value(app, symbol)
        slip_pts = abs(float(fill) - float(req)) / max(1e-12, float(point))
        return SlippageSnapshot(
            entry_request_price=float(req),
            entry_fill_price=float(fill),
            entry_slippage_points=float(slip_pts),
        )
