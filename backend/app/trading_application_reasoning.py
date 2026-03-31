# 한글 설명: TradingApplication에서 점수 사유 계산과 엔트리/익시트 피처 생성 유틸을 모아둔 모듈입니다.
"""Reason/feature helpers for TradingApplication."""

from __future__ import annotations

import re
from datetime import datetime

import pandas as pd


def score_adjustment(probability, weight) -> int:
    return int((float(probability) - 0.5) * int(weight))


def estimate_reason_points(reason: str) -> int:
    raw = str(reason or "").strip()
    s = raw.lower()
    m = re.search(r"\(([+-]?\d+)[^)]*\)\s*$", raw)
    if m:
        return int(m.group(1))
    if "adverse reversal" in s:
        return 220
    if "reversal" in s:
        return 150
    if "adverse stop" in s:
        return 70
    if "target" in s:
        return 120
    if "rsi" in s:
        return 40
    if "bb 20/2" in s:
        return 80
    if "bb 4/4" in s:
        return 50
    if "rule of 4" in s:
        return 80
    if ("1분" in s) or ("1m" in s):
        return 20
    if ("buffer" in s) or ("버퍼" in s):
        return 40
    if ("daily open" in s) or ("시가" in s):
        return 50
    if ("break" in s) or ("돌파" in s):
        return 150
    if ("support" in s) or ("resistance" in s) or ("지지" in s) or ("저항" in s):
        return 120
    if ("disparity" in s) or ("이격" in s) or ("과열" in s) or ("침체" in s):
        return 60
    if ("alignment" in s) or ("정배열" in s) or ("역배열" in s):
        return 80
    if ("wick" in s) or ("캔들" in s) or ("꼬리" in s) or ("망치" in s):
        return 60
    if ("감점" in s) or ("penalty" in s):
        return -30
    if "structure" in s:
        return 80
    if "trigger" in s:
        return 50
    return 30


def build_scored_reasons(reasons, target_total, ai_adj=0):
    rows = []
    for r in (reasons or []):
        txt = str(r or "").strip()
        if not txt:
            continue
        rows.append({"text": txt, "score": int(estimate_reason_points(txt))})
    if ai_adj:
        rows.append({"text": "AI 보정", "score": int(ai_adj)})

    cur = sum(int(x["score"]) for x in rows)
    diff = int(target_total) - cur
    if rows and diff != 0:
        weights = [max(1, abs(int(x["score"]))) for x in rows]
        wsum = sum(weights) or len(rows)
        allocated = 0
        for i, row in enumerate(rows):
            add = int(round(diff * (weights[i] / wsum)))
            row["score"] = int(row["score"]) + add
            allocated += add
        remain = int(diff - allocated)
        if remain != 0:
            pivot = max(range(len(rows)), key=lambda i: abs(int(rows[i]["score"])))
            rows[pivot]["score"] = int(rows[pivot]["score"]) + remain
    elif (not rows) and target_total:
        rows.append({"text": "점수 보정", "score": int(target_total)})
    return [f'{x["text"]} ({int(x["score"]):+d}점)' for x in rows]


def build_scored_reasons_raw(reasons, ai_adj=0):
    rows = []
    for r in (reasons or []):
        txt = str(r or "").strip()
        if not txt:
            continue
        rows.append({"text": txt, "score": int(estimate_reason_points(txt))})
    if ai_adj:
        rows.append({"text": "AI 보정", "score": int(ai_adj)})
    return [f'{x["text"]} ({int(x["score"]):+d}점)' for x in rows]


def _as_float(value, default=0.0):
    try:
        num = pd.to_numeric(value, errors="coerce")
        if pd.isna(num):
            return float(default)
        return float(num)
    except Exception:
        return float(default)


def _as_text(value, default=""):
    text = str(value or "").strip()
    return text if text else str(default or "")


def _normalize_stage(value, default="balanced"):
    stage = _as_text(value, default=default).lower()
    if stage not in {"aggressive", "balanced", "conservative"}:
        return str(default or "balanced")
    return stage


def _symbol_roundtrip_cost(symbol, spread_ratio=1.0):
    upper = str(symbol or "").upper()
    if "BTC" in upper:
        base = 1.2
    elif "NAS" in upper or "US100" in upper or "USTEC" in upper:
        base = 0.6
    elif "XAU" in upper or "GOLD" in upper:
        base = 0.5
    else:
        base = 0.5
    spread_mult = max(0.8, min(2.2, _as_float(spread_ratio, 1.0)))
    return float(base * spread_mult), float(spread_mult)


def entry_features(symbol, action, score, contra_score, reasons, regime=None, indicators=None, metadata=None):
    now = datetime.now()
    top_reason = reasons[0] if reasons else "UNKNOWN"
    regime = regime or {}
    indicators = indicators or {}
    metadata = metadata or {}
    regime_name = str(regime.get("name", "") or "UNKNOWN")
    return {
        "symbol": symbol,
        "direction": action,
        "open_hour": now.hour,
        "open_weekday": now.weekday(),
        "entry_score": float(score),
        "contra_score_at_entry": float(contra_score),
        "score_gap": float(score - contra_score),
        "abs_score_gap": float(abs(score - contra_score)),
        "entry_reason": top_reason,
        "regime_name": regime_name,
        "regime_volume_ratio": float(regime.get("volume_ratio", 1.0) or 1.0),
        "regime_volatility_ratio": float(regime.get("volatility_ratio", 1.0) or 1.0),
        "regime_spread_ratio": float(regime.get("spread_ratio", 0.0) or 0.0),
        "regime_buy_multiplier": float(regime.get("buy_multiplier", 1.0) or 1.0),
        "regime_sell_multiplier": float(regime.get("sell_multiplier", 1.0) or 1.0),
        "ind_rsi": float(indicators.get("ind_rsi", 0.0) or 0.0),
        "ind_adx": float(indicators.get("ind_adx", 0.0) or 0.0),
        "ind_disparity": float(indicators.get("ind_disparity", 0.0) or 0.0),
        "ind_bb_20_up": float(indicators.get("ind_bb_20_up", 0.0) or 0.0),
        "ind_bb_20_dn": float(indicators.get("ind_bb_20_dn", 0.0) or 0.0),
        "ind_bb_4_up": float(indicators.get("ind_bb_4_up", 0.0) or 0.0),
        "ind_bb_4_dn": float(indicators.get("ind_bb_4_dn", 0.0) or 0.0),
        "entry_stage": _normalize_stage(metadata.get("entry_stage", "balanced")),
        "entry_setup_id": _as_text(metadata.get("entry_setup_id", metadata.get("setup_id", ""))).lower(),
        "management_profile_id": _as_text(metadata.get("management_profile_id", "")).lower(),
        "invalidation_id": _as_text(metadata.get("invalidation_id", "")).lower(),
        "regime_at_entry": _as_text(metadata.get("regime_at_entry", regime_name), default=regime_name).upper(),
        "entry_h1_context_score": _as_float(metadata.get("entry_h1_context_score", 0.0)),
        "entry_m1_trigger_score": _as_float(metadata.get("entry_m1_trigger_score", 0.0)),
        "entry_h1_gate_pass": _as_float(metadata.get("entry_h1_gate_pass", 0.0)),
        "entry_h1_gate_reason": _as_text(metadata.get("entry_h1_gate_reason", "")),
        "entry_topdown_gate_pass": _as_float(metadata.get("entry_topdown_gate_pass", 0.0)),
        "entry_topdown_gate_reason": _as_text(metadata.get("entry_topdown_gate_reason", "")),
        "entry_topdown_align_count": _as_float(metadata.get("entry_topdown_align_count", 0.0)),
        "entry_topdown_conflict_count": _as_float(metadata.get("entry_topdown_conflict_count", 0.0)),
        "entry_topdown_seen_count": _as_float(metadata.get("entry_topdown_seen_count", 0.0)),
        "entry_session_name": _as_text(metadata.get("entry_session_name", "")).upper(),
        "entry_weekday": _as_float(metadata.get("entry_weekday", now.weekday()), default=now.weekday()),
        "entry_session_threshold_mult": _as_float(metadata.get("entry_session_threshold_mult", 1.0), default=1.0),
        "entry_atr_ratio": _as_float(metadata.get("entry_atr_ratio", 1.0), default=1.0),
        "entry_atr_threshold_mult": _as_float(metadata.get("entry_atr_threshold_mult", 1.0), default=1.0),
    }


def exit_features(
    symbol,
    direction,
    open_time,
    duration_sec,
    entry_score,
    contra_score,
    exit_score,
    entry_reason,
    exit_reason,
    regime=None,
    trade_ctx=None,
    stage_inputs=None,
    live_metrics=None,
):
    now = datetime.now()
    open_dt = pd.to_datetime(open_time, errors="coerce")
    open_hour = int(open_dt.hour) if pd.notna(open_dt) else now.hour
    open_weekday = int(open_dt.weekday()) if pd.notna(open_dt) else now.weekday()
    regime = regime or {}
    trade_ctx = trade_ctx or {}
    stage_inputs = stage_inputs or {}
    live_metrics = live_metrics or {}
    regime_name = str(regime.get("name", "") or trade_ctx.get("regime_name", "") or "UNKNOWN")
    peak_profit = _as_float(
        live_metrics.get("peak_profit_at_exit", trade_ctx.get("peak_profit_at_exit", stage_inputs.get("peak_profit", 0.0)))
    )
    giveback_usd = _as_float(live_metrics.get("giveback_usd", trade_ctx.get("giveback_usd", 0.0)))
    current_profit = _as_float(stage_inputs.get("profit", trade_ctx.get("profit", 0.0)))
    roundtrip_cost, spread_cost_mult = _symbol_roundtrip_cost(symbol, regime.get("spread_ratio", 1.0))
    mfe_proxy = max(peak_profit, max(0.0, current_profit))
    mae_proxy = max(0.0, abs(min(0.0, current_profit)))
    ev_exit = float(current_profit - roundtrip_cost)
    ev_hold = float((mfe_proxy - roundtrip_cost) - (1.2 * (mae_proxy + roundtrip_cost)))
    ev_delta = float(ev_hold - ev_exit)
    return {
        "symbol": symbol,
        "direction": direction,
        "close_hour": now.hour,
        "open_hour": open_hour,
        "open_weekday": open_weekday,
        "duration_sec": float(max(0.0, duration_sec)),
        "entry_score": float(entry_score),
        "contra_score_at_entry": float(contra_score),
        "exit_score": float(exit_score),
        "entry_reason": entry_reason or "UNKNOWN",
        "exit_reason": exit_reason or "UNKNOWN",
        "regime_name": regime_name,
        "regime_volume_ratio": float(regime.get("volume_ratio", 1.0) or 1.0),
        "regime_volatility_ratio": float(regime.get("volatility_ratio", 1.0) or 1.0),
        "regime_spread_ratio": float(regime.get("spread_ratio", 0.0) or 0.0),
        "regime_buy_multiplier": float(regime.get("buy_multiplier", 1.0) or 1.0),
        "regime_sell_multiplier": float(regime.get("sell_multiplier", 1.0) or 1.0),
        "roundtrip_cost": roundtrip_cost,
        "spread_cost_mult": spread_cost_mult,
        "mfe_proxy": mfe_proxy,
        "mae_proxy": mae_proxy,
        "ev_exit": ev_exit,
        "ev_hold": ev_hold,
        "ev_delta": ev_delta,
        "entry_stage": _normalize_stage(trade_ctx.get("entry_stage", "balanced")),
        "entry_setup_id": _as_text(trade_ctx.get("entry_setup_id", "")).lower(),
        "management_profile_id": _as_text(trade_ctx.get("management_profile_id", "")).lower(),
        "invalidation_id": _as_text(trade_ctx.get("invalidation_id", "")).lower(),
        "entry_wait_state": _as_text(trade_ctx.get("entry_wait_state", "")).upper(),
        "entry_quality": _as_float(trade_ctx.get("entry_quality", 0.0)),
        "entry_model_confidence": _as_float(trade_ctx.get("entry_model_confidence", 0.0)),
        "regime_at_entry": _as_text(trade_ctx.get("regime_at_entry", regime_name), default=regime_name).upper(),
        "entry_h1_context_score": _as_float(trade_ctx.get("entry_h1_context_score", 0.0)),
        "entry_m1_trigger_score": _as_float(trade_ctx.get("entry_m1_trigger_score", 0.0)),
        "entry_h1_gate_pass": _as_float(trade_ctx.get("entry_h1_gate_pass", 0.0)),
        "entry_h1_gate_reason": _as_text(trade_ctx.get("entry_h1_gate_reason", "")),
        "entry_topdown_gate_pass": _as_float(trade_ctx.get("entry_topdown_gate_pass", 0.0)),
        "entry_topdown_gate_reason": _as_text(trade_ctx.get("entry_topdown_gate_reason", "")),
        "entry_topdown_align_count": _as_float(trade_ctx.get("entry_topdown_align_count", 0.0)),
        "entry_topdown_conflict_count": _as_float(trade_ctx.get("entry_topdown_conflict_count", 0.0)),
        "entry_topdown_seen_count": _as_float(trade_ctx.get("entry_topdown_seen_count", 0.0)),
        "entry_session_name": _as_text(trade_ctx.get("entry_session_name", "")).upper(),
        "entry_weekday": _as_float(trade_ctx.get("entry_weekday", open_weekday), default=open_weekday),
        "entry_session_threshold_mult": _as_float(trade_ctx.get("entry_session_threshold_mult", 1.0), default=1.0),
        "entry_atr_ratio": _as_float(trade_ctx.get("entry_atr_ratio", 1.0), default=1.0),
        "entry_atr_threshold_mult": _as_float(trade_ctx.get("entry_atr_threshold_mult", 1.0), default=1.0),
        "decision_winner": _as_text(live_metrics.get("decision_winner", trade_ctx.get("decision_winner", ""))).lower(),
        "utility_exit_now": _as_float(live_metrics.get("utility_exit_now", trade_ctx.get("utility_exit_now", 0.0))),
        "utility_hold": _as_float(live_metrics.get("utility_hold", trade_ctx.get("utility_hold", 0.0))),
        "utility_reverse": _as_float(live_metrics.get("utility_reverse", trade_ctx.get("utility_reverse", 0.0))),
        "utility_wait_exit": _as_float(live_metrics.get("utility_wait_exit", trade_ctx.get("utility_wait_exit", 0.0))),
        "u_cut_now": _as_float(live_metrics.get("u_cut_now", trade_ctx.get("u_cut_now", 0.0))),
        "u_wait_be": _as_float(live_metrics.get("u_wait_be", trade_ctx.get("u_wait_be", 0.0))),
        "u_wait_tp1": _as_float(live_metrics.get("u_wait_tp1", trade_ctx.get("u_wait_tp1", 0.0))),
        "u_reverse": _as_float(live_metrics.get("u_reverse", trade_ctx.get("u_reverse", 0.0))),
        "exit_policy_stage": _as_text(live_metrics.get("exit_policy_stage", trade_ctx.get("exit_policy_stage", ""))).lower(),
        "exit_policy_profile": _as_text(live_metrics.get("exit_policy_profile", trade_ctx.get("exit_policy_profile", ""))).lower(),
        "exit_profile": _as_text(live_metrics.get("exit_profile", trade_ctx.get("exit_profile", ""))).lower(),
        "exit_wait_state": _as_text(live_metrics.get("exit_wait_state", trade_ctx.get("exit_wait_state", ""))).upper(),
        "exit_wait_selected": _as_float(live_metrics.get("exit_wait_selected", trade_ctx.get("exit_wait_selected", 0.0))),
        "exit_wait_decision": _as_text(live_metrics.get("exit_wait_decision", trade_ctx.get("exit_wait_decision", ""))).lower(),
        "p_recover_be": _as_float(live_metrics.get("p_recover_be", trade_ctx.get("p_recover_be", 0.0))),
        "p_recover_tp1": _as_float(live_metrics.get("p_recover_tp1", trade_ctx.get("p_recover_tp1", 0.0))),
        "p_deeper_loss": _as_float(live_metrics.get("p_deeper_loss", trade_ctx.get("p_deeper_loss", 0.0))),
        "p_reverse_valid": _as_float(live_metrics.get("p_reverse_valid", trade_ctx.get("p_reverse_valid", 0.0))),
        "exit_policy_regime": _as_text(
            live_metrics.get("exit_policy_regime", trade_ctx.get("exit_policy_regime", stage_inputs.get("regime_now", regime_name)))
        ).upper(),
        "exit_threshold_triplet": _as_text(live_metrics.get("exit_threshold_triplet", trade_ctx.get("exit_threshold_triplet", ""))),
        "exit_route_ev": _as_text(live_metrics.get("exit_route_ev", trade_ctx.get("exit_route_ev", ""))),
        "exit_confidence": _as_float(live_metrics.get("exit_confidence", trade_ctx.get("exit_confidence", 0.0))),
        "exit_delay_ticks": _as_float(live_metrics.get("exit_delay_ticks", trade_ctx.get("exit_delay_ticks", 0.0))),
        "peak_profit_at_exit": peak_profit,
        "giveback_usd": giveback_usd,
        "shock_score": _as_float(live_metrics.get("shock_score", trade_ctx.get("shock_score", 0.0))),
        "shock_hold_delta_30": _as_float(live_metrics.get("shock_hold_delta_30", trade_ctx.get("shock_hold_delta_30", 0.0))),
    }
