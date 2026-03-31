"""
24h directional-learning penalty probe.

- Reads closed history (data/trades/trade_closed_history.csv)
- Rebuilds the same directional penalty cases used by adaptive entry profile
- Prints per-symbol penalty estimate + one/two tuning suggestions
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from backend.core.config import Config  # type: ignore
except Exception:
    class _ConfigShim:
        ENTRY_ADAPTIVE_DIRECTIONAL_BB_UPPER = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_BB_UPPER", "0.78") or 0.78)
        ENTRY_ADAPTIVE_DIRECTIONAL_BB_LOWER = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_BB_LOWER", "0.22") or 0.22)
        ENTRY_ADAPTIVE_DIRECTIONAL_BB_FALLING = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_BB_FALLING", "0.35") or 0.35)
        ENTRY_ADAPTIVE_DIRECTIONAL_LOSS_CENTER = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_LOSS_CENTER", "0.55") or 0.55)
        ENTRY_ADAPTIVE_DIRECTIONAL_LOSSRATE_GAIN = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_LOSSRATE_GAIN", "28.0") or 28.0)
        ENTRY_ADAPTIVE_DIRECTIONAL_CASE_CAP = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_CASE_CAP", "28.0") or 28.0)
        ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES = int(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES", "8") or 8)
        ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN", "22.0") or 22.0)
        ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP = float(os.getenv("ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP", "42.0") or 42.0)
        ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES_BY_SYMBOL = {}
        ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN_BY_SYMBOL = {}
        ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP_BY_SYMBOL = {}

        @classmethod
        def get_symbol_float(cls, symbol: str, mapping: dict, default: float) -> float:
            upper = str(symbol or "").upper()
            for key, val in (mapping or {}).items():
                if key == "DEFAULT":
                    continue
                if key in upper:
                    return float(val)
            return float((mapping or {}).get("DEFAULT", default))

        @classmethod
        def get_symbol_int(cls, symbol: str, mapping: dict, default: int) -> int:
            upper = str(symbol or "").upper()
            for key, val in (mapping or {}).items():
                if key == "DEFAULT":
                    continue
                if key in upper:
                    return int(val)
            return int((mapping or {}).get("DEFAULT", default))

    Config = _ConfigShim


def _canonical_symbol(symbol: str) -> str:
    s = str(symbol or "").upper().strip()
    if "BTC" in s:
        return "BTCUSD"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    return s


def _penalty_from_subset(sub: pd.DataFrame, *, min_case_n: int, scale: float, exp_gain: float, loss_center: float, wr_gain: float, case_cap: float) -> tuple[float, int, float, float]:
    n = int(len(sub))
    if n <= 0:
        return 0.0, 0, 0.0, 0.0
    loss_rate = float((sub["profit"] <= 0).mean())
    exp = float(sub["profit"].mean())
    if n < int(min_case_n):
        return 0.0, n, loss_rate, exp
    raw = max(0.0, (-exp / max(1e-9, float(scale))) * float(exp_gain)) + max(0.0, (loss_rate - float(loss_center)) * float(wr_gain))
    pen = float(max(0.0, min(float(case_cap), raw)))
    return pen, n, loss_rate, exp


def analyze(src: Path, hours: float = 24.0) -> dict[str, Any]:
    now = datetime.now()
    cut = now - timedelta(hours=float(hours))
    if not src.exists():
        return {"ok": False, "reason": f"missing_file:{src}"}

    frame = pd.read_csv(src, encoding="utf-8-sig")
    if frame.empty:
        return {"ok": False, "reason": "empty_closed_history"}

    if "open_time" in frame.columns:
        ts = pd.to_datetime(frame["open_time"], errors="coerce")
    else:
        ts = pd.to_datetime(frame.get("close_time", ""), errors="coerce")
    frame = frame[ts >= pd.Timestamp(cut)].copy()
    if frame.empty:
        return {"ok": False, "reason": "no_rows_in_window", "window_hours": float(hours)}

    frame["symbol_key"] = frame.get("symbol", "").map(_canonical_symbol)
    frame["direction_key"] = frame.get("direction", "").astype(str).str.upper().str.strip()
    frame["profit"] = pd.to_numeric(frame.get("profit", 0.0), errors="coerce").fillna(0.0)
    entry_px = pd.to_numeric(frame.get("open_price", frame.get("entry_fill_price", 0.0)), errors="coerce").fillna(0.0)
    bb_up = pd.to_numeric(frame.get("ind_bb_20_up", 0.0), errors="coerce").fillna(0.0)
    bb_dn = pd.to_numeric(frame.get("ind_bb_20_dn", 0.0), errors="coerce").fillna(0.0)
    bb_mid = pd.to_numeric(frame.get("ind_bb_20_mid", 0.0), errors="coerce").fillna(0.0)
    ma20 = pd.to_numeric(frame.get("ind_ma_20", 0.0), errors="coerce").fillna(0.0)
    ma60 = pd.to_numeric(frame.get("ind_ma_60", 0.0), errors="coerce").fillna(0.0)
    width = (bb_up - bb_dn).abs().clip(lower=1e-9)
    frame["bb_pos"] = ((entry_px - bb_dn) / width).clip(lower=0.0, upper=1.0)
    frame["entry_px"] = entry_px
    frame["bb_mid"] = bb_mid
    frame["ma20"] = ma20
    frame["ma60"] = ma60

    scale = max(1.0, float(frame["profit"].abs().median()))
    bb_upper_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_UPPER", 0.78))
    bb_lower_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_LOWER", 0.22))
    bb_fall_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_FALLING", 0.35))
    loss_center = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_LOSS_CENTER", 0.55))
    wr_gain = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_LOSSRATE_GAIN", 28.0))
    case_cap = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_CASE_CAP", 28.0))
    out: dict[str, Any] = {
        "ok": True,
        "window_hours": float(hours),
        "generated_at": now.isoformat(timespec="seconds"),
        "scale_profit": round(float(scale), 6),
        "symbols": {},
    }

    for sym in ("NAS100", "XAUUSD", "BTCUSD"):
        sub = frame[frame["symbol_key"] == sym].copy()
        if sub.empty:
            out["symbols"][sym] = {"rows_24h": 0}
            continue
        min_case_n = int(
            Config.get_symbol_int(
                sym,
                getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES_BY_SYMBOL", {}),
                int(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES", 8)),
            )
        )
        exp_gain = float(
            Config.get_symbol_float(
                sym,
                getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN_BY_SYMBOL", {}),
                float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN", 22.0)),
            )
        )
        side_cap = float(
            Config.get_symbol_float(
                sym,
                getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP_BY_SYMBOL", {}),
                float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP", 42.0)),
            )
        )

        buy_mask = sub["direction_key"] == "BUY"
        sell_mask = sub["direction_key"] == "SELL"
        upper_buy = sub[buy_mask & (sub["bb_pos"] >= bb_upper_thr)]
        lower_sell = sub[sell_mask & (sub["bb_pos"] <= bb_lower_thr)]
        falling_buy = sub[buy_mask & (sub["ma20"] < sub["ma60"]) & (sub["entry_px"] <= sub["bb_mid"]) & (sub["bb_pos"] <= bb_fall_thr)]
        rising_sell = sub[sell_mask & (sub["ma20"] > sub["ma60"]) & (sub["entry_px"] >= sub["bb_mid"]) & (sub["bb_pos"] >= (1.0 - bb_fall_thr))]

        ub_pen, ub_n, ub_loss, ub_exp = _penalty_from_subset(
            upper_buy, min_case_n=min_case_n, scale=scale, exp_gain=exp_gain, loss_center=loss_center, wr_gain=wr_gain, case_cap=case_cap
        )
        fb_pen, fb_n, fb_loss, fb_exp = _penalty_from_subset(
            falling_buy, min_case_n=min_case_n, scale=scale, exp_gain=exp_gain, loss_center=loss_center, wr_gain=wr_gain, case_cap=case_cap
        )
        ls_pen, ls_n, ls_loss, ls_exp = _penalty_from_subset(
            lower_sell, min_case_n=min_case_n, scale=scale, exp_gain=exp_gain, loss_center=loss_center, wr_gain=wr_gain, case_cap=case_cap
        )
        rs_pen, rs_n, rs_loss, rs_exp = _penalty_from_subset(
            rising_sell, min_case_n=min_case_n, scale=scale, exp_gain=exp_gain, loss_center=loss_center, wr_gain=wr_gain, case_cap=case_cap
        )
        buy_pen = min(float(side_cap), float(ub_pen + fb_pen))
        sell_pen = min(float(side_cap), float(ls_pen + rs_pen))

        suggestions: list[dict[str, Any]] = []
        if (ub_n + fb_n) > 0 and (ub_loss > 0.65 or fb_loss > 0.65) and buy_pen < 6.0:
            suggestions.append(
                {
                    "param": f"ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN_{sym}",
                    "current": round(exp_gain, 4),
                    "suggested": round(min(40.0, exp_gain + 2.0), 4),
                    "reason": "bad BUY-pattern loss-rate high but buy_penalty weak",
                }
            )
        if (ub_n + fb_n) > 0 and (ub_loss < 0.50 and fb_loss < 0.50) and buy_pen > 10.0:
            suggestions.append(
                {
                    "param": f"ENTRY_ADAPTIVE_DIRECTIONAL_EXPECTANCY_GAIN_{sym}",
                    "current": round(exp_gain, 4),
                    "suggested": round(max(8.0, exp_gain - 2.0), 4),
                    "reason": "BUY penalty appears too strong vs recent loss-rate",
                }
            )
        if min(ub_n if ub_n else 9999, fb_n if fb_n else 9999, ls_n if ls_n else 9999, rs_n if rs_n else 9999) < min_case_n:
            suggestions.append(
                {
                    "param": f"ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES_{sym}",
                    "current": int(min_case_n),
                    "suggested": int(max(4, min_case_n - 1)),
                    "reason": "case sample scarcity; speed up adaptation",
                }
            )
        if (buy_pen >= side_cap * 0.95) or (sell_pen >= side_cap * 0.95):
            suggestions.append(
                {
                    "param": f"ENTRY_ADAPTIVE_DIRECTIONAL_SIDE_CAP_{sym}",
                    "current": round(side_cap, 4),
                    "suggested": round(min(70.0, side_cap + 4.0), 4),
                    "reason": "cap frequently saturated; allow stronger penalty",
                }
            )

        out["symbols"][sym] = {
            "rows_24h": int(len(sub)),
            "params": {
                "min_case_samples": int(min_case_n),
                "expectancy_gain": round(exp_gain, 6),
                "side_cap": round(side_cap, 6),
            },
            "penalties": {
                "buy_penalty_est": round(float(buy_pen), 6),
                "sell_penalty_est": round(float(sell_pen), 6),
                "upper_buy_case": {"n": int(ub_n), "loss_rate": round(float(ub_loss), 6), "avg_profit": round(float(ub_exp), 6), "penalty": round(float(ub_pen), 6)},
                "falling_buy_case": {"n": int(fb_n), "loss_rate": round(float(fb_loss), 6), "avg_profit": round(float(fb_exp), 6), "penalty": round(float(fb_pen), 6)},
                "lower_sell_case": {"n": int(ls_n), "loss_rate": round(float(ls_loss), 6), "avg_profit": round(float(ls_exp), 6), "penalty": round(float(ls_pen), 6)},
                "rising_sell_case": {"n": int(rs_n), "loss_rate": round(float(rs_loss), 6), "avg_profit": round(float(rs_exp), 6), "penalty": round(float(rs_pen), 6)},
            },
            "suggestions_top2": suggestions[:2],
        }
    return out


def main() -> int:
    src = ROOT / "data" / "trades" / "trade_closed_history.csv"
    out_dir = ROOT / "data" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = analyze(src, hours=24.0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"directional_bias_24h_{ts}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out_path), "summary": report.get("symbols", {})}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
