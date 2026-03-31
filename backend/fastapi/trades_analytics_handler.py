"""Trades analytics endpoint handler extracted from app.py."""

from __future__ import annotations

import json

import pandas as pd


def trades_analytics_handler(
    *,
    app,
    days: int = 30,
    sync: bool = False,
    _cache_get,
    _cache_set,
    _sync_open_closed_state,
    TRADE_CSV,
    RUNTIME_STATUS_JSON,
    _note_runtime_warning,
    _safe_float,
    Config,
):
    cache_key = f"trades_analytics:{int(days)}:{1 if bool(sync) else 0}"
    if not bool(sync):
        cached = _cache_get(cache_key, ttl_sec=20.0)
        if cached is not None:
            return cached
    if bool(sync):
        _sync_open_closed_state(force=True)

    empty_quality = {
        "closed_count": 0,
        "unknown_entry_count": 0,
        "unknown_exit_count": 0,
        "unknown_entry_ratio": 0.0,
        "unknown_exit_ratio": 0.0,
    }
    # Use read-service unified sources:
    # - OPEN: trade_history.csv
    # - CLOSED: trade_closed_history.csv + legacy CLOSED fallback
    df = app.state.trade_read_service.read_trade_df()
    closed = app.state.trade_read_service.read_closed_trade_df()
    if df.empty and closed.empty:
        exists = TRADE_CSV.exists() or (TRADE_CSV.parent / "trade_closed_history.csv").exists()
        return {"exists": exists, "daily": [], "entry_reasons": [], "exit_reasons": [], "quality": empty_quality}

    for col in ["open_time", "close_time", "entry_reason", "exit_reason", "status"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    for col in ["open_time", "close_time", "entry_reason", "exit_reason", "status"]:
        if col in closed.columns:
            closed[col] = closed[col].fillna("").astype(str)
    for col in ["profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        if col in closed.columns:
            closed[col] = pd.to_numeric(closed[col], errors="coerce").fillna(0.0)

    if closed.empty:
        return {"exists": True, "daily": [], "entry_reasons": [], "exit_reasons": [], "quality": empty_quality}

    closed["dt"] = pd.to_datetime(closed["close_time"], errors="coerce")
    if "open_time" in closed.columns:
        fallback_dt = pd.to_datetime(closed["open_time"], errors="coerce")
        closed["dt"] = closed["dt"].fillna(fallback_dt)
    closed = closed[closed["dt"].notna()].copy()
    if closed.empty:
        return {"exists": True, "daily": [], "entry_reasons": [], "exit_reasons": [], "quality": empty_quality}

    days = max(7, min(180, int(days)))
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    closed = closed[closed["dt"] >= cutoff].copy()
    if closed.empty:
        return {"exists": True, "daily": [], "entry_reasons": [], "exit_reasons": [], "quality": empty_quality}

    closed["day"] = closed["dt"].dt.strftime("%Y-%m-%d")
    closed["is_win"] = (closed["profit"] > 0).astype(int)

    daily = (
        closed.groupby("day", as_index=False)
        .agg(trades=("profit", "count"), pnl=("profit", "sum"), wins=("is_win", "sum"))
        .sort_values("day")
    )
    daily["win_rate"] = (daily["wins"] / daily["trades"]).fillna(0.0)
    daily["cum_pnl"] = daily["pnl"].cumsum()

    unknown_set = {"", "UNKNOWN", "MANUAL/UNKNOWN", "MANUAL", "NONE", "NULL", "N/A"}
    entry_reason_norm = closed["entry_reason"].fillna("").astype(str).str.strip().str.upper()
    exit_reason_norm = closed["exit_reason"].fillna("").astype(str).str.strip().str.upper()
    closed_count = int(len(closed))
    unknown_entry_count = int(entry_reason_norm.isin(unknown_set).sum())
    unknown_exit_count = int(exit_reason_norm.isin(unknown_set).sum())
    quality = {
        "closed_count": closed_count,
        "unknown_entry_count": unknown_entry_count,
        "unknown_exit_count": unknown_exit_count,
        "unknown_entry_ratio": round(float(unknown_entry_count / closed_count), 4) if closed_count else 0.0,
        "unknown_exit_ratio": round(float(unknown_exit_count / closed_count), 4) if closed_count else 0.0,
    }

    def reason_stats(reason_col: str):
        rows = closed.copy()
        rows["reason"] = rows[reason_col].fillna("").astype(str).str.strip()
        rows.loc[rows["reason"] == "", "reason"] = "UNKNOWN"
        if rows.empty:
            return []
        g = (
            rows.groupby("reason", as_index=False)
            .agg(count=("profit", "count"), pnl=("profit", "sum"), wins=("is_win", "sum"))
            .sort_values("count", ascending=False)
            .head(8)
        )
        g["win_rate"] = (g["wins"] / g["count"]).fillna(0.0)
        return g.to_dict(orient="records")

    closed["bucket_4h"] = closed["dt"].dt.floor("4h")
    pnl_4h = (
        closed.groupby("bucket_4h", as_index=False)
        .agg(trades=("profit", "count"), pnl=("profit", "sum"), wins=("is_win", "sum"))
        .sort_values("bucket_4h")
    )
    pnl_4h["losses"] = pnl_4h["trades"] - pnl_4h["wins"]
    pnl_4h["win_rate"] = (pnl_4h["wins"] / pnl_4h["trades"]).fillna(0.0)
    pnl_4h["bucket"] = pnl_4h["bucket_4h"].dt.strftime("%m-%d %H:%M")

    symbol_4h = {}
    if "symbol" in closed.columns:
        for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
            part = closed[closed["symbol"].astype(str).str.upper().str.contains(sym, na=False)].copy()
            if part.empty:
                symbol_4h[sym] = []
                continue
            g = (
                part.groupby("bucket_4h", as_index=False)
                .agg(trades=("profit", "count"), pnl=("profit", "sum"), wins=("is_win", "sum"))
                .sort_values("bucket_4h")
            )
            g["losses"] = g["trades"] - g["wins"]
            g["win_rate"] = (g["wins"] / g["trades"]).fillna(0.0)
            g["bucket"] = g["bucket_4h"].dt.strftime("%m-%d %H:%M")
            symbol_4h[sym] = g[["bucket", "trades", "wins", "losses", "pnl", "win_rate"]].to_dict(orient="records")
    else:
        symbol_4h = {"BTCUSD": [], "NAS100": [], "XAUUSD": []}

    fee_total = 0.0
    if "commission" in closed.columns:
        comm = pd.to_numeric(closed["commission"], errors="coerce").fillna(0.0)
        fee_total += float(comm.abs().sum())
    if "swap" in closed.columns:
        swap = pd.to_numeric(closed["swap"], errors="coerce").fillna(0.0)
        fee_total += float(swap.abs().sum())

    # Verification stats: condition coverage / indicator coverage / learned effect.
    rule_groups = [
        ("session_box", "3단 세션박스", ["박스", "session"]),
        ("daily_open", "당일 시가", ["당일 시가", "daily open"]),
        ("multi_sr", "다중 지지/저항", ["지지", "저항", "support", "resistance"]),
        ("rule_of_4", "4번의 법칙", ["4번", "4번의 법칙", "rule of 4"]),
        ("double_bb_20_2", "더블 BB(20,2)", ["bb 20/2", "bb20", "bollinger 20,2", "볼린저 20,2"]),
        ("double_bb_4_4", "더블 BB(4,4)", ["bb 4/4", "bb4", "bollinger 4,4", "볼린저 4,4"]),
        ("disparity", "이격도(DI)", ["이격", "disparity", "di"]),
        ("ma_align", "다중 이평선 정/역배열", ["이평", "ma", "정배열", "역배열"]),
        ("trendline", "추세선", ["추세선", "trendline", "trend"]),
        ("rsi_div", "RSI 다이버전스", ["rsi 다이버", "다이버전스", "divergence"]),
        ("wick", "캔들 꼬리", ["망치", "윗꼬리", "아랫꼬리", "꼬리", "wick", "캔들"]),
    ]

    def _rule_hit_masks(frame: pd.DataFrame, key: str, kws: list[str]):
        if frame is None or frame.empty:
            empty = pd.Series(dtype=bool)
            return empty, empty, empty
        ent = frame["entry_reason"].fillna("").astype(str) if "entry_reason" in frame.columns else pd.Series("", index=frame.index)
        ext = frame["exit_reason"].fillna("").astype(str) if "exit_reason" in frame.columns else pd.Series("", index=frame.index)
        reason = (ent + " | " + ext).str.lower()
        reason_hit = pd.Series(False, index=frame.index)
        for kw in kws:
            reason_hit = reason_hit | reason.str.contains(str(kw).lower(), regex=False, na=False)

        # Indicator-based fallback matching to avoid undercount when reason text is sparse.
        close = pd.to_numeric(frame.get("close_price", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        bb4_up = pd.to_numeric(frame.get("ind_bb_4_up", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        bb4_dn = pd.to_numeric(frame.get("ind_bb_4_dn", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        disp = pd.to_numeric(frame.get("ind_disparity", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        ma20 = pd.to_numeric(frame.get("ind_ma_20", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        ma60 = pd.to_numeric(frame.get("ind_ma_60", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        ma120 = pd.to_numeric(frame.get("ind_ma_120", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        ma240 = pd.to_numeric(frame.get("ind_ma_240", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        ma480 = pd.to_numeric(frame.get("ind_ma_480", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        indicator_hit = pd.Series(False, index=frame.index)

        if key == "double_bb_4_4":
            width = (bb4_up - bb4_dn).abs()
            near_band = ((close - bb4_up).abs() <= (width * 0.20)) | ((close - bb4_dn).abs() <= (width * 0.20))
            breakout = (close >= bb4_up) | (close <= bb4_dn)
            indicator_hit = indicator_hit | ((width > 0) & (near_band | breakout))
        elif key == "disparity":
            indicator_hit = indicator_hit | ((disp.notna()) & ((disp - 100.0).abs() >= 1.5))
        elif key == "trendline":
            slope = (ma20 - ma60).abs() / close.abs().clip(lower=1.0)
            aligned3 = ((ma20 > ma60) & (ma60 > ma120)) | ((ma20 < ma60) & (ma60 < ma120))
            indicator_hit = indicator_hit | (aligned3 | (slope >= 0.0004))
        elif key == "ma_align":
            bull = (ma20 > ma60) & (ma60 > ma120) & (ma120 > ma240) & (ma240 > ma480)
            bear = (ma20 < ma60) & (ma60 < ma120) & (ma120 < ma240) & (ma240 < ma480)
            indicator_hit = indicator_hit | (bull | bear)
        hit = (reason_hit | indicator_hit).fillna(False)
        return reason_hit.fillna(False), indicator_hit.fillna(False), hit

    # Coverage should be based on CLOSED history (actual executed outcomes), not OPEN snapshots.
    entry_reason_series = (
        closed["entry_reason"].fillna("").astype(str) if "entry_reason" in closed.columns else pd.Series(dtype=str)
    )
    exit_reason_series = (
        closed["exit_reason"].fillna("").astype(str) if "exit_reason" in closed.columns else pd.Series(dtype=str)
    )
    reason_series = (entry_reason_series + " | " + exit_reason_series).str.strip()
    reason_lower = reason_series.str.lower()
    condition_coverage = []
    for key, label, kws in rule_groups:
        reason_hit, indicator_hit, hit = _rule_hit_masks(closed, key, kws)
        cnt = int(hit.sum())
        reason_cnt = int(reason_hit.sum())
        indicator_cnt = int(indicator_hit.sum())
        ratio = float(cnt / len(reason_lower)) if len(reason_lower) > 0 else 0.0
        reason_ratio = float(reason_cnt / len(reason_lower)) if len(reason_lower) > 0 else 0.0
        indicator_ratio = float(indicator_cnt / len(reason_lower)) if len(reason_lower) > 0 else 0.0
        condition_coverage.append(
            {
                "key": key,
                "label": label,
                "count": cnt,
                "ratio": round(ratio, 4),
                "reason_count": reason_cnt,
                "reason_ratio": round(reason_ratio, 4),
                "indicator_count": indicator_cnt,
                "indicator_ratio": round(indicator_ratio, 4),
            }
        )

    # by symbol condition coverage
    condition_coverage_by_symbol = {"BTCUSD": [], "NAS100": [], "XAUUSD": []}
    if "symbol" in closed.columns:
        sym_series = closed["symbol"].fillna("").astype(str).str.upper()
        for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
            mask_sym = sym_series.str.contains(sym, na=False)
            entry_sym = (
                closed.loc[mask_sym, "entry_reason"].fillna("").astype(str)
                if "entry_reason" in closed.columns
                else pd.Series(dtype=str)
            )
            exit_sym = (
                closed.loc[mask_sym, "exit_reason"].fillna("").astype(str)
                if "exit_reason" in closed.columns
                else pd.Series(dtype=str)
            )
            reason_sym = (entry_sym + " | " + exit_sym).str.lower()
            df_sym = closed.loc[mask_sym].copy()
            rows = []
            for key, label, kws in rule_groups:
                reason_hit, indicator_hit, hit = _rule_hit_masks(df_sym, key, kws)
                cnt = int(hit.sum())
                reason_cnt = int(reason_hit.sum())
                indicator_cnt = int(indicator_hit.sum())
                total = int(len(reason_sym))
                rows.append(
                    {
                        "key": key,
                        "label": label,
                        "count": cnt,
                        "ratio": round(float(cnt / total), 4) if total else 0.0,
                        "reason_count": reason_cnt,
                        "reason_ratio": round(float(reason_cnt / total), 4) if total else 0.0,
                        "indicator_count": indicator_cnt,
                        "indicator_ratio": round(float(indicator_cnt / total), 4) if total else 0.0,
                    }
                )
            condition_coverage_by_symbol[sym] = rows

    ind_cols = [
        "ind_rsi", "ind_adx", "ind_plus_di", "ind_minus_di", "ind_disparity",
        "ind_ma_20", "ind_ma_60", "ind_ma_120", "ind_ma_240", "ind_ma_480",
        "ind_bb_20_up", "ind_bb_20_mid", "ind_bb_20_dn", "ind_bb_4_up", "ind_bb_4_dn",
    ]
    recent_for_ind = df.tail(300).copy()
    indicator_coverage = []
    for col in ind_cols:
        if col in recent_for_ind.columns:
            s = pd.to_numeric(recent_for_ind[col], errors="coerce")
            nn = int(s.notna().sum())
            nz = int((s.fillna(0.0) != 0.0).sum())
            total = int(len(recent_for_ind))
            indicator_coverage.append(
                {
                    "column": col,
                    "nonnull_count": nn,
                    "nonzero_count": nz,
                    "total": total,
                    "nonnull_ratio": round(float(nn / total), 4) if total else 0.0,
                    "nonzero_ratio": round(float(nz / total), 4) if total else 0.0,
                }
            )

    indicator_coverage_by_symbol = {"BTCUSD": [], "NAS100": [], "XAUUSD": []}
    if "symbol" in recent_for_ind.columns:
        sym_u = recent_for_ind["symbol"].fillna("").astype(str).str.upper()
        for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
            part = recent_for_ind[sym_u.str.contains(sym, na=False)].copy()
            rows = []
            total = int(len(part))
            for col in ind_cols:
                if col not in part.columns:
                    continue
                s = pd.to_numeric(part[col], errors="coerce")
                nn = int(s.notna().sum())
                nz = int((s.fillna(0.0) != 0.0).sum())
                rows.append(
                    {
                        "column": col,
                        "nonnull_count": nn,
                        "nonzero_count": nz,
                        "total": total,
                        "nonnull_ratio": round(float(nn / total), 4) if total else 0.0,
                        "nonzero_ratio": round(float(nz / total), 4) if total else 0.0,
                    }
                )
            indicator_coverage_by_symbol[sym] = rows

    # detailed rule performance (closed trades)
    rule_performance = []
    rule_performance_by_symbol = {"BTCUSD": [], "NAS100": [], "XAUUSD": []}
    closed_entry = closed["entry_reason"].fillna("").astype(str) if "entry_reason" in closed.columns else pd.Series(dtype=str)
    closed_exit = closed["exit_reason"].fillna("").astype(str) if "exit_reason" in closed.columns else pd.Series(dtype=str)
    closed_reason = (closed_entry + " | " + closed_exit).str.lower()
    for key, label, kws in rule_groups:
        reason_hit, indicator_hit, hit = _rule_hit_masks(closed, key, kws)
        part = closed.loc[hit].copy()
        cnt = int(len(part))
        total_closed = int(len(closed))
        row = {
            "key": key,
            "label": label,
            "count": cnt,
            "ratio": round(float(cnt / total_closed), 4) if total_closed else 0.0,
            "reason_count": int(reason_hit.sum()),
            "reason_ratio": round(float(reason_hit.sum() / total_closed), 4) if total_closed else 0.0,
            "indicator_count": int(indicator_hit.sum()),
            "indicator_ratio": round(float(indicator_hit.sum() / total_closed), 4) if total_closed else 0.0,
            "win_rate": 0.0,
            "pnl": 0.0,
            "avg_profit": 0.0,
            "avg_entry_score": 0.0,
            "avg_exit_score": 0.0,
        }
        if cnt > 0:
            row["win_rate"] = round(float((part["profit"] > 0).mean()), 4)
            row["pnl"] = round(float(part["profit"].sum()), 4)
            row["avg_profit"] = round(float(part["profit"].mean()), 4)
            if "entry_score" in part.columns:
                row["avg_entry_score"] = round(
                    float(pd.to_numeric(part["entry_score"], errors="coerce").fillna(0.0).mean()),
                    4,
                )
            if "exit_score" in part.columns:
                row["avg_exit_score"] = round(
                    float(pd.to_numeric(part["exit_score"], errors="coerce").fillna(0.0).mean()),
                    4,
                )
        rule_performance.append(row)

    if "symbol" in closed.columns:
        sym_closed = closed["symbol"].fillna("").astype(str).str.upper()
        for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
            part_sym = closed[sym_closed.str.contains(sym, na=False)].copy()
            entry_sym = part_sym["entry_reason"].fillna("").astype(str) if "entry_reason" in part_sym.columns else pd.Series(dtype=str)
            exit_sym = part_sym["exit_reason"].fillna("").astype(str) if "exit_reason" in part_sym.columns else pd.Series(dtype=str)
            reason_sym = (entry_sym + " | " + exit_sym).str.lower()
            rows = []
            for key, label, kws in rule_groups:
                reason_hit, indicator_hit, hit = _rule_hit_masks(part_sym, key, kws)
                part = part_sym.loc[hit].copy()
                cnt = int(len(part))
                total_sym = int(len(part_sym))
                item = {
                    "key": key,
                    "label": label,
                    "count": cnt,
                    "ratio": round(float(cnt / total_sym), 4) if total_sym else 0.0,
                    "reason_count": int(reason_hit.sum()),
                    "reason_ratio": round(float(reason_hit.sum() / total_sym), 4) if total_sym else 0.0,
                    "indicator_count": int(indicator_hit.sum()),
                    "indicator_ratio": round(float(indicator_hit.sum() / total_sym), 4) if total_sym else 0.0,
                    "win_rate": 0.0,
                    "pnl": 0.0,
                    "avg_profit": 0.0,
                    "avg_entry_score": 0.0,
                    "avg_exit_score": 0.0,
                }
                if cnt > 0:
                    item["win_rate"] = round(float((part["profit"] > 0).mean()), 4)
                    item["pnl"] = round(float(part["profit"].sum()), 4)
                    item["avg_profit"] = round(float(part["profit"].mean()), 4)
                    if "entry_score" in part.columns:
                        item["avg_entry_score"] = round(
                            float(pd.to_numeric(part["entry_score"], errors="coerce").fillna(0.0).mean()),
                            4,
                        )
                    if "exit_score" in part.columns:
                        item["avg_exit_score"] = round(
                            float(pd.to_numeric(part["exit_score"], errors="coerce").fillna(0.0).mean()),
                            4,
                        )
                rows.append(item)
            rule_performance_by_symbol[sym] = rows

    # latest indicator values per symbol (sanity check for ingestion)
    indicator_latest_by_symbol = {"BTCUSD": [], "NAS100": [], "XAUUSD": []}
    latest_src = pd.concat([df.copy(), closed.copy()], ignore_index=True, sort=False)
    if "symbol" in latest_src.columns and not latest_src.empty:
        dt_for_latest = pd.to_datetime(latest_src.get("open_time", pd.Series(dtype=str)), errors="coerce")
        if "close_time" in latest_src.columns:
            dt_close = pd.to_datetime(latest_src["close_time"], errors="coerce")
            dt_for_latest = dt_close.fillna(dt_for_latest)
        tmp = latest_src.copy()
        tmp["_dt_latest"] = dt_for_latest
        sym_all = tmp["symbol"].fillna("").astype(str).str.upper()
        for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
            part = tmp[sym_all.str.contains(sym, na=False)].copy()
            if part.empty:
                continue
            part = part.sort_values("_dt_latest")
            rows = []
            for col in ind_cols:
                if col not in part.columns:
                    continue
                s = pd.to_numeric(part[col], errors="coerce")
                s_nonnull = s.dropna()
                latest = float(s_nonnull.iloc[-1]) if not s_nonnull.empty else 0.0
                s_nonzero = s[(s.fillna(0.0) != 0.0)].dropna()
                latest_nonzero = float(s_nonzero.iloc[-1]) if not s_nonzero.empty else 0.0
                rows.append(
                    {
                        "column": col,
                        "latest": round(latest, 6),
                        "latest_nonzero": round(latest_nonzero, 6),
                        "has_nonzero": bool(not s_nonzero.empty),
                    }
                )
            indicator_latest_by_symbol[sym] = rows

    learned_effect = {"trace_count": 0, "avg_adj": 0.0, "avg_prob": 0.0, "avg_final_minus_raw": 0.0, "timeline": []}
    learned_effect_by_symbol = {
        "BTCUSD": {"trace_count": 0, "avg_adj": 0.0, "avg_prob": 0.0, "avg_final_minus_raw": 0.0, "timeline": []},
        "NAS100": {"trace_count": 0, "avg_adj": 0.0, "avg_prob": 0.0, "avg_final_minus_raw": 0.0, "timeline": []},
        "XAUUSD": {"trace_count": 0, "avg_adj": 0.0, "avg_prob": 0.0, "avg_final_minus_raw": 0.0, "timeline": []},
    }
    if RUNTIME_STATUS_JSON.exists():
        try:
            rt = json.loads(RUNTIME_STATUS_JSON.read_text(encoding="utf-8"))
            traces = rt.get("ai_entry_traces", []) or []
            if traces:
                tdf = pd.DataFrame(traces)
                for c in ["raw_score", "score_adj", "final_score", "probability"]:
                    if c in tdf.columns:
                        tdf[c] = pd.to_numeric(tdf[c], errors="coerce")
                learned_effect["trace_count"] = int(len(tdf))
                if "score_adj" in tdf.columns:
                    learned_effect["avg_adj"] = round(float(tdf["score_adj"].fillna(0.0).mean()), 4)
                if "probability" in tdf.columns:
                    learned_effect["avg_prob"] = round(float(tdf["probability"].fillna(0.0).mean()), 4)
                if "final_score" in tdf.columns and "raw_score" in tdf.columns:
                    delta = (tdf["final_score"].fillna(0.0) - tdf["raw_score"].fillna(0.0))
                    learned_effect["avg_final_minus_raw"] = round(float(delta.mean()), 4)
                if "time" in tdf.columns and "score_adj" in tdf.columns:
                    tdf["dt"] = pd.to_datetime(tdf["time"], errors="coerce")
                    tdf = tdf[tdf["dt"].notna()].copy()
                    if not tdf.empty:
                        tdf["bucket"] = tdf["dt"].dt.floor("15min")
                        g = (
                            tdf.groupby("bucket", as_index=False)
                            .agg(count=("score_adj", "count"), avg_adj=("score_adj", "mean"))
                            .sort_values("bucket")
                        )
                        g["bucket"] = g["bucket"].dt.strftime("%m-%d %H:%M")
                        learned_effect["timeline"] = g.to_dict(orient="records")

                if "symbol" in tdf.columns:
                    sym_u = tdf["symbol"].fillna("").astype(str).str.upper()
                    for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
                        part = tdf[sym_u.str.contains(sym, na=False)].copy()
                        if part.empty:
                            continue
                        out = learned_effect_by_symbol[sym]
                        out["trace_count"] = int(len(part))
                        if "score_adj" in part.columns:
                            out["avg_adj"] = round(float(part["score_adj"].fillna(0.0).mean()), 4)
                        if "probability" in part.columns:
                            out["avg_prob"] = round(float(part["probability"].fillna(0.0).mean()), 4)
                        if "final_score" in part.columns and "raw_score" in part.columns:
                            delta = (part["final_score"].fillna(0.0) - part["raw_score"].fillna(0.0))
                            out["avg_final_minus_raw"] = round(float(delta.mean()), 4)
                        if "dt" in part.columns and "score_adj" in part.columns:
                            part = part.copy()
                            part["bucket_dt"] = part["dt"].dt.floor("15min")
                            g2 = (
                                part.groupby("bucket_dt", as_index=False)
                                .agg(count=("score_adj", "count"), avg_adj=("score_adj", "mean"))
                                .sort_values("bucket_dt")
                            )
                            g2["bucket"] = pd.to_datetime(g2["bucket_dt"], errors="coerce").dt.strftime("%m-%d %H:%M")
                            out["timeline"] = g2[["bucket", "count", "avg_adj"]].to_dict(orient="records")
        except Exception as exc:
            _note_runtime_warning(app, "analytics_learning_effect_build_failed", exc)

    out = {
        "exists": True,
        "daily": daily.to_dict(orient="records"),
        "pnl_4h": pnl_4h[["bucket", "trades", "wins", "losses", "pnl", "win_rate"]].to_dict(orient="records"),
        "pnl_4h_by_symbol": symbol_4h,
        "fee_total": round(float(fee_total), 4),
        "entry_reasons": reason_stats("entry_reason"),
        "exit_reasons": reason_stats("exit_reason"),
        "quality": quality,
        "condition_coverage": condition_coverage,
        "condition_coverage_by_symbol": condition_coverage_by_symbol,
        "rule_performance": rule_performance,
        "rule_performance_by_symbol": rule_performance_by_symbol,
        "indicator_coverage": indicator_coverage,
        "indicator_coverage_by_symbol": indicator_coverage_by_symbol,
        "indicator_latest_by_symbol": indicator_latest_by_symbol,
        "learned_effect": learned_effect,
        "learned_effect_by_symbol": learned_effect_by_symbol,
    }
    _cache_set(cache_key, out)
    return out

