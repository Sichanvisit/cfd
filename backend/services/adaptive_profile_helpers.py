# 한글 설명: 엔트리/익시트 서비스의 적응형 프로필(최근 성과 기반 가중치) 갱신 로직을 분리한 헬퍼 모듈입니다.
"""Adaptive profile refresh helpers for entry/exit services."""

from __future__ import annotations

import time

import pandas as pd

from backend.core.config import Config


def _canonical_symbol(symbol: str) -> str:
    s = str(symbol or "").upper().strip()
    if "BTC" in s:
        return "BTCUSD"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    return s


def refresh_entry_profile(current_profile: dict, trade_logger) -> dict:
    if not bool(getattr(Config, "ENABLE_ADAPTIVE_ENTRY_ROUTING", True)):
        return dict(current_profile or {})
    now_s = time.time()
    ttl = max(30, int(getattr(Config, "ENTRY_ADAPTIVE_REFRESH_SEC", 120)))
    profile = dict(current_profile or {})
    if (now_s - float(profile.get("updated_at", 0.0))) < ttl:
        return profile
    reader = getattr(trade_logger, "read_closed_df", None)
    if not callable(reader):
        return profile
    try:
        closed = reader()
    except Exception:
        return profile
    if closed is None or closed.empty:
        profile["updated_at"] = now_s
        return profile
    try:
        frame = closed.copy()
        frame["profit"] = pd.to_numeric(frame.get("profit", 0.0), errors="coerce").fillna(0.0)
        frame["entry_score"] = pd.to_numeric(frame.get("entry_score", 0.0), errors="coerce").fillna(0.0)
        frame["contra_score_at_entry"] = pd.to_numeric(frame.get("contra_score_at_entry", 0.0), errors="coerce").fillna(0.0)
        frame["edge"] = frame["entry_score"] - frame["contra_score_at_entry"]
        min_n = max(12, int(getattr(Config, "ENTRY_ADAPTIVE_MIN_SAMPLES", 30)))
        if len(frame) < min_n:
            profile["updated_at"] = now_s
            return profile

        q1 = float(frame["edge"].quantile(0.35))
        q2 = float(frame["edge"].quantile(0.70))
        stage_masks = {
            "aggressive": (frame["edge"] <= q1),
            "balanced": ((frame["edge"] > q1) & (frame["edge"] < q2)),
            "conservative": (frame["edge"] >= q2),
        }
        scale = max(1.0, float(frame["profit"].abs().median()))
        stage_quality = {"aggressive": 0.0, "balanced": 0.0, "conservative": 0.0}
        stage_wr = {"aggressive": 0.50, "balanced": 0.50, "conservative": 0.50}
        stage_exp = {"aggressive": 0.0, "balanced": 0.0, "conservative": 0.0}
        for stage, mask in stage_masks.items():
            part = frame.loc[mask].copy()
            n = len(part)
            if n < max(6, int(min_n * 0.25)):
                continue
            wr = float((part["profit"] > 0).mean())
            exp = float(part["profit"].mean())
            quality = ((wr - 0.5) * 1.2) + max(-1.0, min(1.0, (exp / scale) * 0.7))
            stage_wr[stage] = max(0.05, min(0.95, wr))
            stage_exp[stage] = exp
            stage_quality[stage] = max(-1.0, min(1.0, quality))

        directional_bias = {}
        if bool(getattr(Config, "ENABLE_ADAPTIVE_ENTRY_DIRECTIONAL_BIAS", True)):
            symbol_col = "symbol" if "symbol" in frame.columns else ("symbol_key" if "symbol_key" in frame.columns else "")
            dir_col = "direction" if "direction" in frame.columns else ""
            if symbol_col and dir_col:
                w = max(
                    pd.to_numeric(frame.get("ind_bb_20_up", 0.0), errors="coerce")
                    - pd.to_numeric(frame.get("ind_bb_20_dn", 0.0), errors="coerce"),
                    1e-9,
                )
                entry_px = pd.to_numeric(frame.get("open_price", frame.get("entry_fill_price", 0.0)), errors="coerce")
                bb_dn = pd.to_numeric(frame.get("ind_bb_20_dn", 0.0), errors="coerce")
                bb_mid = pd.to_numeric(frame.get("ind_bb_20_mid", 0.0), errors="coerce")
                ma20 = pd.to_numeric(frame.get("ind_ma_20", 0.0), errors="coerce")
                ma60 = pd.to_numeric(frame.get("ind_ma_60", 0.0), errors="coerce")
                bb_pos = ((entry_px - bb_dn) / w).clip(lower=0.0, upper=1.0)

                work = frame.copy()
                work["symbol_key"] = work[symbol_col].map(_canonical_symbol)
                work["direction_key"] = work[dir_col].astype(str).str.upper().str.strip()
                work["_bb_pos"] = bb_pos.fillna(0.5)
                work["_bb_mid"] = bb_mid.fillna(0.0)
                work["_entry_px"] = entry_px.fillna(0.0)
                work["_ma20"] = ma20.fillna(0.0)
                work["_ma60"] = ma60.fillna(0.0)

                bb_upper_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_UPPER", 0.78))
                bb_lower_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_LOWER", 0.22))
                bb_fall_thr = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_BB_FALLING", 0.35))
                loss_center = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_LOSS_CENTER", 0.55))
                wr_gain = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_LOSSRATE_GAIN", 28.0))
                case_cap = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_CASE_CAP", 28.0))
                alpha = float(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_EMA_ALPHA", 0.35))
                alpha = max(0.05, min(1.0, alpha))
                prev_bias = dict((current_profile or {}).get("directional_bias", {}) or {})

                def _penalty(sub: pd.DataFrame) -> tuple[float, int]:
                    n = int(len(sub))
                    if n < min_case_n:
                        return 0.0, n
                    loss_rate = float((sub["profit"] <= 0).mean())
                    exp = float(sub["profit"].mean())
                    raw = max(0.0, (-exp / max(1e-9, scale)) * exp_gain) + max(0.0, (loss_rate - loss_center) * wr_gain)
                    return float(max(0.0, min(case_cap, raw))), n

                for sym in sorted([s for s in work["symbol_key"].dropna().astype(str).unique().tolist() if str(s)]):
                    sub = work[work["symbol_key"] == sym].copy()
                    if sub.empty:
                        continue
                    min_case_n = max(
                        4,
                        int(
                            Config.get_symbol_int(
                                sym,
                                getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES_BY_SYMBOL", {}),
                                int(getattr(Config, "ENTRY_ADAPTIVE_DIRECTIONAL_MIN_CASE_SAMPLES", 8)),
                            )
                        ),
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
                    upper_buy_pen, upper_buy_n = _penalty(sub[buy_mask & (sub["_bb_pos"] >= bb_upper_thr)])
                    lower_sell_pen, lower_sell_n = _penalty(sub[sell_mask & (sub["_bb_pos"] <= bb_lower_thr)])
                    falling_buy_pen, falling_buy_n = _penalty(
                        sub[
                            buy_mask
                            & (sub["_ma20"] < sub["_ma60"])
                            & (sub["_entry_px"] <= sub["_bb_mid"])
                            & (sub["_bb_pos"] <= bb_fall_thr)
                        ]
                    )
                    rising_sell_pen, rising_sell_n = _penalty(
                        sub[
                            sell_mask
                            & (sub["_ma20"] > sub["_ma60"])
                            & (sub["_entry_px"] >= sub["_bb_mid"])
                            & (sub["_bb_pos"] >= (1.0 - bb_fall_thr))
                        ]
                    )
                    buy_pen = min(side_cap, upper_buy_pen + falling_buy_pen)
                    sell_pen = min(side_cap, lower_sell_pen + rising_sell_pen)
                    prev = prev_bias.get(sym, {}) if isinstance(prev_bias, dict) else {}
                    prev_buy = float(pd.to_numeric((prev or {}).get("buy_penalty", 0.0), errors="coerce") or 0.0)
                    prev_sell = float(pd.to_numeric((prev or {}).get("sell_penalty", 0.0), errors="coerce") or 0.0)
                    sm_buy = (alpha * float(buy_pen)) + ((1.0 - alpha) * prev_buy)
                    sm_sell = (alpha * float(sell_pen)) + ((1.0 - alpha) * prev_sell)
                    directional_bias[str(sym)] = {
                        "buy_penalty": round(float(max(0.0, min(side_cap, sm_buy))), 4),
                        "sell_penalty": round(float(max(0.0, min(side_cap, sm_sell))), 4),
                        "upper_buy_n": int(upper_buy_n),
                        "lower_sell_n": int(lower_sell_n),
                        "falling_buy_n": int(falling_buy_n),
                        "rising_sell_n": int(rising_sell_n),
                    }
        return {
            "updated_at": now_s,
            "n": int(len(frame)),
            "stage_quality": stage_quality,
            "stage_wr": stage_wr,
            "stage_exp": stage_exp,
            "directional_bias": directional_bias,
        }
    except Exception:
        profile["updated_at"] = now_s
        return profile


def refresh_exit_profile(current_profile: dict, trade_logger, normalize_exit_reason, reason_to_stage) -> dict:
    if not bool(getattr(Config, "ENABLE_ADAPTIVE_EXIT_ROUTING", True)):
        return dict(current_profile or {})
    now_s = time.time()
    ttl = max(30, int(getattr(Config, "EXIT_ADAPTIVE_REFRESH_SEC", 120)))
    profile = dict(current_profile or {})
    if (now_s - float(profile.get("updated_at", 0.0))) < ttl:
        return profile
    reader = getattr(trade_logger, "read_closed_df", None)
    if not callable(reader):
        return profile
    try:
        closed = reader()
    except Exception:
        return profile
    if closed is None or closed.empty:
        profile["updated_at"] = now_s
        return profile
    try:
        frame = closed.copy()
        frame["profit"] = pd.to_numeric(frame.get("profit", 0.0), errors="coerce").fillna(0.0)
        frame["exit_reason_norm"] = frame.get("exit_reason", "").map(normalize_exit_reason)
        frame["stage"] = frame["exit_reason_norm"].map(reason_to_stage)
        frame = frame[frame["stage"] != ""].copy()
        min_n = max(10, int(getattr(Config, "EXIT_ADAPTIVE_MIN_SAMPLES", 20)))
        if frame.empty or len(frame) < min_n:
            profile["updated_at"] = now_s
            return profile
        scale = max(1.0, float(frame["profit"].abs().median()))
        stage_quality = {"protect": 0.0, "lock": 0.0, "hold": 0.0}
        stage_wr = {"protect": 0.50, "lock": 0.50, "hold": 0.50}
        stage_exp = {"protect": 0.0, "lock": 0.0, "hold": 0.0}
        for stage in ("protect", "lock", "hold"):
            part = frame[frame["stage"] == stage]
            n = len(part)
            if n < max(6, int(min_n * 0.3)):
                continue
            wr = float((part["profit"] > 0).mean())
            exp = float(part["profit"].mean())
            quality = ((wr - 0.5) * 1.20) + max(-1.0, min(1.0, (exp / scale) * 0.60))
            stage_wr[stage] = max(0.05, min(0.95, wr))
            stage_exp[stage] = exp
            stage_quality[stage] = max(-1.0, min(1.0, quality))
        return {
            "updated_at": now_s,
            "n": int(len(frame)),
            "stage_quality": stage_quality,
            "stage_wr": stage_wr,
            "stage_exp": stage_exp,
        }
    except Exception:
        profile["updated_at"] = now_s
        return profile
