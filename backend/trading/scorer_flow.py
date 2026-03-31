"""Flow analysis helper extracted from Scorer."""

from __future__ import annotations

import pandas as pd

from backend.core.config import Config


def _sym_int(symbol: str, mapping_name: str, fallback_name: str, fallback: int) -> int:
    mapping = getattr(Config, mapping_name, {})
    base = int(getattr(Config, fallback_name, fallback))
    return int(Config.get_symbol_int(symbol, mapping, base))


def _sym_float(symbol: str, mapping_name: str, fallback_name: str, fallback: float) -> float:
    mapping = getattr(Config, mapping_name, {})
    base = float(getattr(Config, fallback_name, fallback))
    return float(Config.get_symbol_float(symbol, mapping, base))


def analyze_flow(scorer, symbol, current, price, m15=None, h1_current=None):
    result = {
        "buy_score": 0,
        "sell_score": 0,
        "wait_score": 0,
        "wait_conflict_score": 0,
        "wait_noise_score": 0,
        "buy_reasons": [],
        "sell_reasons": [],
        "wait_reasons": [],
        "h1_context_buy_score": 0,
        "h1_context_sell_score": 0,
    }

    if "bb_20_up" in current and not pd.isna(current["bb_20_up"]):
        bb20_up = float(current["bb_20_up"])
        bb20_dn = float(current["bb_20_dn"])
        if price > bb20_up:
            result["buy_score"] += int(getattr(Config, "BB20_FLOW_TREND_SCORE", 140))
            result["buy_reasons"].append("Flow: BB20 breakout up")
        elif price < bb20_dn:
            result["sell_score"] += int(getattr(Config, "BB20_FLOW_TREND_SCORE", 140))
            result["sell_reasons"].append("Flow: BB20 breakout down")

        if m15 is not None and not m15.empty:
            up_add, up_reason = scorer._level_retest_hold_score(
                m15=m15,
                level=bb20_up,
                side="BUY",
                label="Flow: BB20 upper",
                base_score=int(getattr(Config, "BB_LEVEL_RETEST_SCORE", 55)),
                lookback=int(getattr(Config, "BB_LEVEL_RETEST_LOOKBACK", 8)),
                tol_ratio=float(getattr(Config, "BB_LEVEL_RETEST_TOL_RATIO", 0.00030)),
            )
            dn_add, dn_reason = scorer._level_retest_hold_score(
                m15=m15,
                level=bb20_dn,
                side="SELL",
                label="Flow: BB20 lower",
                base_score=int(getattr(Config, "BB_LEVEL_RETEST_SCORE", 55)),
                lookback=int(getattr(Config, "BB_LEVEL_RETEST_LOOKBACK", 8)),
                tol_ratio=float(getattr(Config, "BB_LEVEL_RETEST_TOL_RATIO", 0.00030)),
            )
            if up_add > 0:
                result["buy_score"] += int(up_add)
                result["buy_reasons"].append(str(up_reason))
            if dn_add > 0:
                result["sell_score"] += int(dn_add)
                result["sell_reasons"].append(str(dn_reason))

            s1, s2, s3, tol_mult, squeeze_mult, lookback = scorer._bb_touch_profile(symbol, "BB 20/2")
            buy_add, sell_add, buy_reason, sell_reason = scorer._bb_touch_score(
                m15=m15,
                up_col="bb_20_up",
                dn_col="bb_20_dn",
                label="BB 20/2",
                s1=s1,
                s2=s2,
                s3=s3,
                tol_mult=tol_mult,
                squeeze_mult=squeeze_mult,
                lookback_override=lookback,
            )
            result["buy_score"] += int(buy_add)
            result["sell_score"] += int(sell_add)
            if buy_reason:
                result["buy_reasons"].append(buy_reason)
            if sell_reason:
                result["sell_reasons"].append(sell_reason)

            if "bb_20_mid" in current and not pd.isna(current["bb_20_mid"]):
                mid = float(current["bb_20_mid"])
                m_add_buy, m_reason_buy = scorer._level_retest_hold_score(
                    m15=m15,
                    level=mid,
                    side="BUY",
                    label="Flow: BB20 mid",
                    base_score=int(getattr(Config, "BB_MID_HOLD_SCORE", 45)),
                    lookback=int(getattr(Config, "BB_MID_HOLD_LOOKBACK", 6)),
                    tol_ratio=float(getattr(Config, "BB_LEVEL_RETEST_TOL_RATIO", 0.00030)),
                )
                m_add_sell, m_reason_sell = scorer._level_retest_hold_score(
                    m15=m15,
                    level=mid,
                    side="SELL",
                    label="Flow: BB20 mid",
                    base_score=int(getattr(Config, "BB_MID_HOLD_SCORE", 45)),
                    lookback=int(getattr(Config, "BB_MID_HOLD_LOOKBACK", 6)),
                    tol_ratio=float(getattr(Config, "BB_LEVEL_RETEST_TOL_RATIO", 0.00030)),
                )
                if m_add_buy > 0:
                    result["buy_score"] += int(m_add_buy)
                    result["buy_reasons"].append(str(m_reason_buy))
                if m_add_sell > 0:
                    result["sell_score"] += int(m_add_sell)
                    result["sell_reasons"].append(str(m_reason_sell))

                if bb20_up > bb20_dn:
                    bb_pos = (float(price) - bb20_dn) / max(1e-9, (bb20_up - bb20_dn))
                    bb_edge_band = _sym_float(symbol, "ENTRY_BB_EDGE_BAND_BY_SYMBOL", "ENTRY_BB_EDGE_BAND", 0.20)
                    bb_edge_score = _sym_int(symbol, "ENTRY_BB_EDGE_SCORE_BY_SYMBOL", "ENTRY_BB_EDGE_SCORE", 28)
                    bb_center_wait = _sym_int(
                        symbol, "ENTRY_BB_CENTER_WAIT_SCORE_BY_SYMBOL", "ENTRY_BB_CENTER_WAIT_SCORE", 18
                    )
                    bb_center_low = float(getattr(Config, "ENTRY_BB_CENTER_LOW", 0.45))
                    bb_center_high = float(getattr(Config, "ENTRY_BB_CENTER_HIGH", 0.55))
                    if bb_pos <= max(0.0, bb_edge_band):
                        result["buy_score"] += int(bb_edge_score)
                        result["buy_reasons"].append(f"Flow: BB lower edge ({bb_pos:.2f})")
                    elif bb_pos >= min(1.0, 1.0 - bb_edge_band):
                        result["sell_score"] += int(bb_edge_score)
                        result["sell_reasons"].append(f"Flow: BB upper edge ({bb_pos:.2f})")
                    elif bb_center_low <= bb_pos <= bb_center_high:
                        result["wait_score"] += int(bb_center_wait)
                        result["wait_reasons"].append(f"Wait: BB center ({bb_pos:.2f})")

    if "bb_4_up" in current and not pd.isna(current["bb_4_up"]):
        bb4_up = float(current["bb_4_up"])
        bb4_dn = float(current["bb_4_dn"])
        if price > bb4_up:
            result["buy_score"] += int(getattr(Config, "BB4_FLOW_EXPANSION_SCORE", 95))
            result["buy_reasons"].append("Flow: BB4 expansion up")
        elif price < bb4_dn:
            result["sell_score"] += int(getattr(Config, "BB4_FLOW_EXPANSION_SCORE", 95))
            result["sell_reasons"].append("Flow: BB4 expansion down")
        else:
            width = max(abs(bb4_up - bb4_dn), max(abs(price), 1.0) * 0.0002)
            near = width * float(getattr(Config, "BB4_FLOW_NEAR_WIDTH_RATIO", 0.22))
            if abs(price - bb4_up) <= near:
                result["sell_score"] += int(getattr(Config, "BB4_FLOW_NEAR_SCORE", 48))
                result["sell_reasons"].append("Flow: BB4 near upper")
            if abs(price - bb4_dn) <= near:
                result["buy_score"] += int(getattr(Config, "BB4_FLOW_NEAR_SCORE", 48))
                result["buy_reasons"].append("Flow: BB4 near lower")
        if m15 is not None and not m15.empty:
            s1, s2, s3, tol_mult, squeeze_mult, lookback = scorer._bb_touch_profile(symbol, "BB 4/4")
            buy_add, sell_add, buy_reason, sell_reason = scorer._bb_touch_score(
                m15=m15,
                up_col="bb_4_up",
                dn_col="bb_4_dn",
                label="BB 4/4",
                s1=s1,
                s2=s2,
                s3=s3,
                tol_mult=tol_mult,
                squeeze_mult=squeeze_mult,
                lookback_override=lookback,
            )
            result["buy_score"] += int(buy_add)
            result["sell_score"] += int(sell_add)
            if buy_reason:
                result["buy_reasons"].append(buy_reason)
            if sell_reason:
                result["sell_reasons"].append(sell_reason)

    if "disparity" in current and not pd.isna(current["disparity"]):
        disp = float(current["disparity"])
        if disp >= 106:
            result["sell_score"] += 35
            result["sell_reasons"].append(f"Flow: overbought ({disp:.1f}%)")
        elif disp <= 92:
            result["buy_score"] += 35
            result["buy_reasons"].append(f"Flow: oversold ({disp:.1f}%)")
        elif disp >= 102:
            result["sell_score"] += 20
            result["sell_reasons"].append(f"Flow: upper range ({disp:.1f}%)")
        elif disp <= 98:
            result["buy_score"] += 20
            result["buy_reasons"].append(f"Flow: lower range ({disp:.1f}%)")

    alignment = scorer.trend_mgr.get_ma_alignment(current)
    if alignment == "BULL":
        result["buy_score"] += 50
        result["buy_reasons"].append("Flow: MA alignment bull")
    elif alignment == "BEAR":
        result["sell_score"] += 50
        result["sell_reasons"].append("Flow: MA alignment bear")
        try:
            if ("bb_20_mid" in current) and not pd.isna(current["bb_20_mid"]) and float(price) <= float(current["bb_20_mid"]):
                result["sell_score"] += int(getattr(Config, "ENTRY_BEAR_CONTINUATION_SELL_SCORE", 22))
                w_add = int(getattr(Config, "ENTRY_BEAR_CONTINUATION_WAIT_SCORE", 16))
                result["wait_score"] += int(w_add)
                result["wait_reasons"].append("Wait: bear continuation below BB mid")
                result["sell_reasons"].append("Flow: bear continuation")
        except Exception:
            pass

    if "ma_20" in current and "ma_60" in current and not pd.isna(current["ma_20"]) and not pd.isna(current["ma_60"]):
        ma20 = float(current["ma_20"])
        ma60 = float(current["ma_60"])
        slope_ratio = abs(ma20 - ma60) / max(abs(price), 1.0)
        if slope_ratio >= 0.0004:
            if ma20 > ma60:
                result["buy_score"] += 18
                result["buy_reasons"].append("Flow: trend spread up")
            else:
                result["sell_score"] += 18
                result["sell_reasons"].append("Flow: trend spread down")

    if m15 is not None and len(m15) >= 12 and "rsi" in m15.columns and "close" in m15.columns:
        close_s = pd.to_numeric(m15["close"], errors="coerce").dropna()
        rsi_s = pd.to_numeric(m15["rsi"], errors="coerce").dropna()
        n = min(len(close_s), len(rsi_s))
        if n >= 12:
            c = close_s.iloc[-n:]
            r = rsi_s.iloc[-n:]
            prev_c = c.iloc[-10:-2]
            prev_r = r.iloc[-10:-2]
            if not prev_c.empty and not prev_r.empty:
                c_last = float(c.iloc[-1])
                r_last = float(r.iloc[-1])
                if c_last < float(prev_c.min()) and r_last > float(prev_r.min()):
                    result["buy_score"] += 25
                    result["buy_reasons"].append("Trigger: RSI divergence up")
                elif c_last > float(prev_c.max()) and r_last < float(prev_r.max()):
                    result["sell_score"] += 25
                    result["sell_reasons"].append("Trigger: RSI divergence down")

    try:
        if m15 is not None and len(m15) >= 8:
            lookback = _sym_int(symbol, "ENTRY_BOX_LOOKBACK_BARS_BY_SYMBOL", "ENTRY_BOX_LOOKBACK_BARS", 48)
            edge_band = _sym_float(symbol, "ENTRY_BOX_EDGE_BAND_BY_SYMBOL", "ENTRY_BOX_EDGE_BAND", 0.20)
            edge_score = _sym_int(symbol, "ENTRY_BOX_EDGE_SCORE_BY_SYMBOL", "ENTRY_BOX_EDGE_SCORE", 34)
            center_wait = _sym_int(symbol, "ENTRY_BOX_CENTER_WAIT_SCORE_BY_SYMBOL", "ENTRY_BOX_CENTER_WAIT_SCORE", 24)
            center_low = float(getattr(Config, "ENTRY_BOX_CENTER_LOW", 0.40))
            center_high = float(getattr(Config, "ENTRY_BOX_CENTER_HIGH", 0.60))
            sub = m15.tail(max(8, int(lookback))).copy()
            hi = float(pd.to_numeric(sub.get("high"), errors="coerce").max())
            lo = float(pd.to_numeric(sub.get("low"), errors="coerce").min())
            if hi > lo:
                box_pos = (float(price) - lo) / max(1e-9, (hi - lo))
                if box_pos <= max(0.0, edge_band):
                    result["buy_score"] += int(edge_score)
                    result["buy_reasons"].append(f"Flow: box lower zone ({box_pos:.2f})")
                elif box_pos >= min(1.0, (1.0 - edge_band)):
                    result["sell_score"] += int(edge_score)
                    result["sell_reasons"].append(f"Flow: box upper zone ({box_pos:.2f})")
                elif center_low <= box_pos <= center_high:
                    result["wait_score"] += int(center_wait)
                    result["wait_reasons"].append(f"Wait: box center ({box_pos:.2f})")
    except Exception:
        pass

    try:
        noise_lb = _sym_int(symbol, "ENTRY_WAIT_NOISE_LOOKBACK_BARS_BY_SYMBOL", "ENTRY_WAIT_NOISE_LOOKBACK_BARS", 12)
        if m15 is not None and len(m15) >= max(6, noise_lb + 1):
            close_s = pd.to_numeric(m15.get("close"), errors="coerce").dropna().tail(noise_lb + 1)
            if len(close_s) >= 6:
                diff = close_s.diff().dropna()
                chop_ratio = float(diff.abs().sum() / max(1e-9, abs(float(close_s.iloc[-1] - close_s.iloc[0]))))
                chop_thr = float(getattr(Config, "WAIT_NOISE_CHOP_RATIO", 2.2))
                if chop_ratio >= chop_thr:
                    ns = int(getattr(Config, "WAIT_NOISE_CHOP_SCORE", 14))
                    result["wait_noise_score"] += int(ns)
                    result["wait_score"] += int(ns)
                    result["wait_reasons"].append(f"Wait: chop ({chop_ratio:.2f})")
    except Exception:
        pass

    try:
        gap_thr = int(getattr(Config, "ENTRY_WAIT_CONFLICT_GAP", 20))
        if abs(int(result["buy_score"]) - int(result["sell_score"])) <= max(1, gap_thr):
            cs = _sym_int(symbol, "ENTRY_WAIT_CONFLICT_SCORE_BY_SYMBOL", "ENTRY_WAIT_CONFLICT_SCORE", 20)
            result["wait_conflict_score"] += int(cs)
            result["wait_score"] += int(cs)
            result["wait_reasons"].append("Wait: score conflict")
    except Exception:
        pass

    try:
        fk_lb = max(4, int(getattr(Config, "ENTRY_FALLING_KNIFE_LOOKBACK", 8)))
        fk_min_down = max(3, int(getattr(Config, "ENTRY_FALLING_KNIFE_MIN_DOWN_BARS", 6)))
        need_cols = {"close", "bb_20_up", "bb_20_dn", "bb_20_mid", "ma_20", "ma_60"}
        if m15 is not None and len(m15) >= fk_lb + 2 and need_cols.issubset(set(m15.columns)):
            sub = m15.tail(fk_lb + 1).copy()
            close_s = pd.to_numeric(sub["close"], errors="coerce").dropna()
            up_s = pd.to_numeric(sub["bb_20_up"], errors="coerce").dropna()
            dn_s = pd.to_numeric(sub["bb_20_dn"], errors="coerce").dropna()
            mid = float(pd.to_numeric(sub["bb_20_mid"].iloc[-1], errors="coerce") or price)
            ma20 = float(pd.to_numeric(sub["ma_20"].iloc[-1], errors="coerce") or 0.0)
            ma60 = float(pd.to_numeric(sub["ma_60"].iloc[-1], errors="coerce") or 0.0)
            if len(close_s) >= fk_lb and len(up_s) >= fk_lb and len(dn_s) >= fk_lb:
                down_bars = int((close_s.diff().dropna() < 0).sum())
                bb_down = bool((float(up_s.iloc[-1]) < float(up_s.iloc[0])) and (float(dn_s.iloc[-1]) < float(dn_s.iloc[0])))
                width_now = float(abs(float(up_s.iloc[-1]) - float(dn_s.iloc[-1])))
                bb_pos = (float(price) - float(dn_s.iloc[-1])) / max(1e-9, width_now)
                is_knife = (
                    down_bars >= fk_min_down
                    and bb_down
                    and (ma20 < ma60)
                    and (float(price) <= mid)
                    and (bb_pos <= 0.35)
                )
                if is_knife:
                    w_add = _sym_int(
                        symbol, "ENTRY_FALLING_KNIFE_WAIT_SCORE_BY_SYMBOL", "ENTRY_FALLING_KNIFE_WAIT_SCORE", 22
                    )
                    s_add = _sym_int(
                        symbol, "ENTRY_FALLING_KNIFE_SELL_SCORE_BY_SYMBOL", "ENTRY_FALLING_KNIFE_SELL_SCORE", 28
                    )
                    result["wait_score"] += int(w_add)
                    result["sell_score"] += int(s_add)
                    result["wait_reasons"].append(f"Wait: falling knife ({down_bars}/{fk_lb})")
                    result["sell_reasons"].append(f"Flow: falling knife ({down_bars}/{fk_lb})")
    except Exception:
        pass

    h1_ctx = scorer._analyze_h1_entry_context(h1_current=h1_current, price=price)
    if h1_ctx:
        h1_buy = int(h1_ctx.get("buy_score", 0) or 0)
        h1_sell = int(h1_ctx.get("sell_score", 0) or 0)
        result["h1_context_buy_score"] = int(h1_buy)
        result["h1_context_sell_score"] = int(h1_sell)
        result["buy_score"] += int(h1_buy)
        result["sell_score"] += int(h1_sell)
        result["buy_reasons"].extend(list(h1_ctx.get("buy_reasons", []) or []))
        result["sell_reasons"].extend(list(h1_ctx.get("sell_reasons", []) or []))

    return result
