"""
Scoring engine for entry/exit signal strengths.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from backend.core.config import Config
from backend.trading.scorer_flow import analyze_flow as helper_analyze_flow
from backend.trading.scorer_get_score import get_score as helper_get_score
from backend.trading.session_manager import SessionManager
from backend.trading.trend_manager import TrendManager


class Scorer:
    """Rule-based scorer with market-regime adaptation."""

    def __init__(self):
        self.session_mgr = SessionManager()
        self.trend_mgr = TrendManager()
        self._vp_cache: dict[str, dict] = {}
        self._entry_condition_profile = {
            "updated_at": 0.0,
            "symbol_family_mult": {},
            "symbol_feature_meta": {},
        }

    def get_score(self, symbol, tick, df_all):
        return helper_get_score(self, symbol=symbol, tick=tick, df_all=df_all)

    @staticmethod
    def _tf_mult(tf: str) -> float:
        return {
            "1D": 1.15,
            "4H": 1.05,
            "2H": 1.00,
            "1H": 0.90,
            "30M": 0.75,
            "15M": 0.60,
            "5M": 0.45,
            "1M": 0.35,
        }.get(str(tf or "").upper(), 0.50)

    def _analyze_single_tf_context(self, row, price: float, tf: str) -> dict:
        out = {"buy_score": 0, "sell_score": 0, "buy_reasons": [], "sell_reasons": [], "bias": "neutral"}
        if row is None:
            return out
        mult = float(self._tf_mult(tf))
        close_v = float(pd.to_numeric(row.get("close", np.nan), errors="coerce"))
        ma20 = float(pd.to_numeric(row.get("ma_20", np.nan), errors="coerce"))
        ma60 = float(pd.to_numeric(row.get("ma_60", np.nan), errors="coerce"))
        if math.isnan(close_v) or math.isnan(ma20) or math.isnan(ma60):
            return out
        if close_v >= ma20 >= ma60:
            out["buy_score"] += int(round(40 * mult))
            out["buy_reasons"].append(f"TopDown {tf}: bullish")
            out["bias"] = "buy"
        elif close_v <= ma20 <= ma60:
            out["sell_score"] += int(round(40 * mult))
            out["sell_reasons"].append(f"TopDown {tf}: bearish")
            out["bias"] = "sell"
        return out

    def _analyze_topdown_context(self, tf_rows: dict, price: float) -> dict:
        out = {"buy_score": 0, "sell_score": 0, "buy_reasons": [], "sell_reasons": [], "stack": {}}
        if not isinstance(tf_rows, dict):
            return out
        for tf, row in tf_rows.items():
            one = self._analyze_single_tf_context(row=row, price=price, tf=tf)
            out["buy_score"] += int(one.get("buy_score", 0) or 0)
            out["sell_score"] += int(one.get("sell_score", 0) or 0)
            out["buy_reasons"].extend(list(one.get("buy_reasons", []) or []))
            out["sell_reasons"].extend(list(one.get("sell_reasons", []) or []))
            out["stack"][str(tf)] = str(one.get("bias", "neutral"))
        return out

    @staticmethod
    def _rebalance_family_scores(parts: dict[str, float]) -> dict[str, float]:
        if not parts:
            return {}
        out = {}
        for k, v in parts.items():
            out[str(k)] = max(0.0, float(v or 0.0))
        return out

    @staticmethod
    def _canonical_symbol(symbol: str) -> str:
        s = str(symbol or "").upper().strip()
        if "BTC" in s:
            return "BTCUSD"
        if "XAU" in s or "GOLD" in s:
            return "XAUUSD"
        if "NAS" in s or "US100" in s or "USTEC" in s:
            return "NAS100"
        return s

    @staticmethod
    def _reason_has_family(reason_text: str, family: str) -> bool:
        return str(family or "").lower() in str(reason_text or "").lower()

    def _refresh_entry_condition_profile_if_needed(self) -> None:
        return

    def _get_entry_feature_meta(self, symbol: str) -> dict:
        return {}

    def _get_entry_family_multipliers(self, symbol: str) -> dict:
        return {}

    def _get_spread_limit(self, symbol, price):
        s = str(symbol or "").upper()
        if "BTC" in s:
            return float(getattr(Config, "SPREAD_LIMIT_BTC", 80.0))
        if "XAU" in s:
            return float(getattr(Config, "SPREAD_LIMIT_XAU", 1.2))
        return float(getattr(Config, "SPREAD_LIMIT_DEFAULT", max(0.2, abs(float(price or 0.0)) * 0.0015)))

    def _level_retest_hold_score(
        self,
        m15,
        level,
        side="BUY",
        label="LEVEL",
        base_score=55,
        lookback=8,
        tol_ratio=0.00030,
    ):
        if m15 is None or m15.empty:
            return 0, ""
        sub = m15.tail(max(2, int(lookback))).copy()
        if sub.empty:
            return 0, ""
        high = pd.to_numeric(sub.get("high", pd.Series(dtype=float)), errors="coerce")
        low = pd.to_numeric(sub.get("low", pd.Series(dtype=float)), errors="coerce")
        close = pd.to_numeric(sub.get("close", pd.Series(dtype=float)), errors="coerce")
        if high.empty or low.empty or close.empty:
            return 0, ""
        tol = max(abs(float(level)) * float(tol_ratio), 1e-12)
        near = ((high >= (float(level) - tol)) & (low <= (float(level) + tol))).fillna(False)
        if not bool(near.any()):
            return 0, ""
        last_close = float(pd.to_numeric(close.iloc[-1], errors="coerce") or 0.0)
        side_u = str(side or "BUY").upper()
        if side_u == "BUY":
            if last_close >= float(level) - tol:
                return int(base_score), f"{label} 돌파지지"
            return 0, ""
        if last_close <= float(level) + tol:
            return int(base_score), f"{label} 이탈저항"
        return 0, ""

    def _analyze_structure(self, h1, d1, price, m15=None):
        out = {"buy_score": 0, "sell_score": 0, "buy_reasons": [], "sell_reasons": []}
        if h1 is None or h1.empty:
            return out
        h1i = self.trend_mgr.add_indicators(h1.copy())
        row = h1i.iloc[-1] if h1i is not None and not h1i.empty else h1.iloc[-1]
        ma20 = float(pd.to_numeric(row.get("ma_20", np.nan), errors="coerce"))
        ma60 = float(pd.to_numeric(row.get("ma_60", np.nan), errors="coerce"))
        if not math.isnan(ma20) and not math.isnan(ma60):
            if float(price) >= ma20 >= ma60:
                out["buy_score"] += 70
                out["buy_reasons"].append("Structure: H1 bull stack")
            elif float(price) <= ma20 <= ma60:
                out["sell_score"] += 70
                out["sell_reasons"].append("Structure: H1 bear stack")
        return out

    @staticmethod
    def _symbol_family(symbol: str) -> str:
        s = str(symbol or "").upper()
        if "BTC" in s:
            return "CRYPTO"
        if "XAU" in s or "GOLD" in s:
            return "METAL"
        if "NAS" in s or "US100" in s or "USTEC" in s:
            return "INDEX"
        return "FX"

    def _bb_touch_profile(self, symbol: str, label: str):
        return 30, 55, 80, 1.0, 1.0, 24

    def _analyze_flow(self, symbol, current, price, m15=None, h1_current=None):
        return helper_analyze_flow(self, symbol=symbol, current=current, price=price, m15=m15, h1_current=h1_current)

    def _analyze_h1_entry_context(self, h1_current, price: float):
        out = {"buy_score": 0, "sell_score": 0, "buy_reasons": [], "sell_reasons": []}
        if h1_current is None:
            return out
        rsi = float(pd.to_numeric(h1_current.get("rsi", np.nan), errors="coerce"))
        if not math.isnan(rsi):
            if rsi <= float(getattr(Config, "RSI_LOWER", 30)):
                out["buy_score"] += 20
                out["buy_reasons"].append("H1 Context: RSI oversold")
            elif rsi >= float(getattr(Config, "RSI_UPPER", 70)):
                out["sell_score"] += 20
                out["sell_reasons"].append("H1 Context: RSI overbought")
        return out

    @staticmethod
    def _count_consecutive_touches(mask: pd.Series) -> int:
        if mask is None or len(mask) == 0:
            return 0
        n = 0
        for v in reversed(mask.fillna(False).tolist()):
            if bool(v):
                n += 1
            else:
                break
        return int(n)

    @staticmethod
    def _touch_score_by_count(touch_count: int, s1: int, s2: int, s3: int) -> int:
        c = int(touch_count or 0)
        if c >= 3:
            return int(s3)
        if c == 2:
            return int(s2)
        if c == 1:
            return int(s1)
        return 0

    def _bb_touch_score(
        self,
        m15,
        up_col,
        dn_col,
        label,
        s1=30,
        s2=55,
        s3=80,
        tol_mult=1.0,
        squeeze_mult=1.0,
        lookback_override=24,
        count_mode="consecutive",
        window_bars=12,
    ):
        if m15 is None or m15.empty or up_col not in m15.columns or dn_col not in m15.columns:
            return 0, 0, "", ""
        sub = m15.tail(max(5, int(lookback_override))).copy()
        if sub.empty:
            return 0, 0, "", ""
        high = pd.to_numeric(sub.get("high"), errors="coerce")
        low = pd.to_numeric(sub.get("low"), errors="coerce")
        up = pd.to_numeric(sub.get(up_col), errors="coerce")
        dn = pd.to_numeric(sub.get(dn_col), errors="coerce")
        width = (up - dn).abs().fillna(0.0)
        tol = (width * (0.03 * float(tol_mult))).clip(lower=1e-8)
        touch_up = ((high >= (up - tol)) & (low <= (up + tol))).fillna(False)
        touch_dn = ((high >= (dn - tol)) & (low <= (dn + tol))).fillna(False)
        mode = str(count_mode or "consecutive").strip().lower()
        if mode == "window":
            w = max(3, int(window_bars or lookback_override or 12))
            sell_cnt = int(touch_up.tail(w).fillna(False).sum())
            buy_cnt = int(touch_dn.tail(w).fillna(False).sum())
        else:
            sell_cnt = int(self._count_consecutive_touches(touch_up))
            buy_cnt = int(self._count_consecutive_touches(touch_dn))
        buy_add = self._touch_score_by_count(buy_cnt, s1, s2, s3)
        sell_add = self._touch_score_by_count(sell_cnt, s1, s2, s3)
        mode_tag = "win" if mode == "window" else "consec"
        buy_reason = f"Flow: {label} touch({mode_tag}) x{buy_cnt}" if buy_add > 0 else ""
        sell_reason = f"Flow: {label} touch({mode_tag}) x{sell_cnt}" if sell_add > 0 else ""
        return int(buy_add), int(sell_add), buy_reason, sell_reason

    def _analyze_trigger(self, current, m1):
        out = {
            "buy_score": 0,
            "sell_score": 0,
            "buy_reasons": [],
            "sell_reasons": [],
            "m1_trigger_buy_score": 0,
            "m1_trigger_sell_score": 0,
        }
        if current is None:
            return out
        rsi = float(pd.to_numeric(current.get("rsi", np.nan), errors="coerce"))
        if not math.isnan(rsi):
            if rsi <= float(getattr(Config, "RSI_LOWER", 30)):
                out["buy_score"] += 45
                out["m1_trigger_buy_score"] += 45
                out["buy_reasons"].append("Trigger: RSI low")
            elif rsi >= float(getattr(Config, "RSI_UPPER", 70)):
                out["sell_score"] += 45
                out["m1_trigger_sell_score"] += 45
                out["sell_reasons"].append("Trigger: RSI high")
        return out

    def _vp_symbol_candidates(self, symbol: str):
        c = self._canonical_symbol(symbol)
        return [c, str(symbol or "").upper().strip()]

    @staticmethod
    def _find_col(df: pd.DataFrame, names):
        if df is None or df.empty:
            return None
        cols = {str(c).lower(): c for c in df.columns}
        for n in names:
            key = str(n).lower()
            if key in cols:
                return cols[key]
        return None

    @staticmethod
    def _read_vp_row(path: Path):
        try:
            if not path.exists():
                return None
            df = pd.read_csv(path, encoding="utf-8-sig")
            if df.empty:
                return None
            return df.iloc[-1]
        except Exception:
            return None

    def _load_volume_profile(self, symbol: str):
        return None

    def _analyze_volume_profile(self, symbol: str, price: float, current):
        return {"buy_score": 0, "sell_score": 0, "buy_reasons": [], "sell_reasons": []}

    @staticmethod
    def _safe_ratio(num, den, default=1.0):
        try:
            n = float(num)
            d = float(den)
            if abs(d) < 1e-12:
                return float(default)
            return float(n / d)
        except Exception:
            return float(default)

    def _apply_market_regime_adjustment(
        self,
        m15,
        spread,
        spread_limit,
        buy_score,
        sell_score,
        buy_reasons,
        sell_reasons,
    ):
        vol_ratio = 1.0
        try:
            if m15 is not None and not m15.empty:
                close = pd.to_numeric(m15.get("close"), errors="coerce").dropna()
                if len(close) >= 30:
                    ret = close.pct_change().dropna()
                    curr = float(ret.tail(20).std() or 0.0)
                    base = float(ret.tail(120).std() or 0.0)
                    if base > 1e-12:
                        vol_ratio = max(0.2, min(3.5, curr / base))
        except Exception:
            vol_ratio = 1.0
        spread_ratio = self._safe_ratio(spread, spread_limit, default=1.0)
        liquidity_ratio = max(0.2, min(3.0, 1.0 / max(0.25, spread_ratio)))
        if vol_ratio > 1.5:
            buy_score = int(round(float(buy_score) * 0.95))
            sell_score = int(round(float(sell_score) * 0.95))
            buy_reasons.append("Regime: high volatility damp")
            sell_reasons.append("Regime: high volatility damp")
            regime_name = "EXPANSION"
        elif vol_ratio < 0.75:
            regime_name = "RANGE"
        else:
            regime_name = "NORMAL"
        regime = {
            "name": regime_name,
            "volume_ratio": float(liquidity_ratio),
            "volatility_ratio": float(vol_ratio),
            "spread_ratio": float(spread_ratio),
            "buy_multiplier": 1.0,
            "sell_multiplier": 1.0,
        }
        return int(buy_score), int(sell_score), list(buy_reasons), list(sell_reasons), regime
