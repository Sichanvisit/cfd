# 한글 설명: TradeLogger의 쇼크 이벤트 등록/진행 업데이트/종료 확정 처리 로직을 분리한 모듈입니다.
"""Shock-event operation helpers extracted from TradeLogger."""

from __future__ import annotations

import logging

import pandas as pd

from backend.core.config import Config


def _get_cached_active_row(trade_logger, ticket: int) -> dict | None:
    cache = getattr(trade_logger, "_shock_event_runtime_cache", None)
    if not isinstance(cache, dict):
        return None
    row = cache.get(int(ticket or 0))
    if not isinstance(row, dict):
        return None
    if int(pd.to_numeric(row.get("resolved", 0), errors="coerce") or 0) == 1:
        return None
    return dict(row)


def _set_cached_active_row(trade_logger, ticket: int, row: dict | None) -> None:
    cache = getattr(trade_logger, "_shock_event_runtime_cache", None)
    if not isinstance(cache, dict):
        return
    t = int(ticket or 0)
    if t <= 0:
        return
    if isinstance(row, dict) and row:
        cache[t] = dict(row)
    else:
        cache.pop(t, None)


def _load_latest_active_row_from_csv(trade_logger, ticket: int) -> dict | None:
    df = trade_logger._read_shock_df_safe()
    t = int(ticket or 0)
    if t <= 0 or df.empty:
        return None
    cand = df[(df["ticket"] == t) & (df["resolved"] == 0)]
    if cand.empty:
        return None
    row = cand.sort_values("event_ts", ascending=False).iloc[0].to_dict()
    _set_cached_active_row(trade_logger, t, row)
    return dict(row)


def register_shock_event(
    trade_logger,
    *,
    ticket: int,
    symbol: str,
    direction: str,
    lot: float,
    event_price: float,
    event_profit: float,
    shock_score: float,
    shock_level: str,
    shock_reason: str,
    shock_action: str,
    pre_shock_stage: str,
    post_shock_stage: str,
    logger: logging.Logger | None = None,
) -> bool:
    log = logger or logging.getLogger(__name__)
    if not bool(getattr(Config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
        return False
    t = int(ticket or 0)
    if t <= 0:
        return False
    trade_logger._ensure_shock_event_file()
    now_text = trade_logger._now_kst_text()
    now_ts = int(trade_logger._text_to_kst_epoch(now_text))
    bucket = int(now_ts // 10)
    cached = _get_cached_active_row(trade_logger, t)
    if isinstance(cached, dict) and int(pd.to_numeric(cached.get("event_bucket", 0), errors="coerce") or 0) == bucket:
        return False
    try:
        with trade_logger._file_guard(f"{trade_logger.shock_event_filepath}.lock", trade_logger._shock_lock):
            try:
                base = pd.read_csv(trade_logger.shock_event_filepath, encoding="utf-8-sig")
            except Exception:
                base = pd.DataFrame(columns=trade_logger._shock_columns())
            base = trade_logger._normalize_shock_df(base)
            dupe = base[(base["ticket"] == t) & (base["event_bucket"] == bucket)]
            if not dupe.empty:
                return False
            row = {
                "ticket": t,
                "symbol": str(symbol or "").strip().upper(),
                "direction": str(direction or "").strip().upper(),
                "lot": float(lot or 0.0),
                "event_time": now_text,
                "event_ts": now_ts,
                "event_bucket": bucket,
                "event_price": float(event_price or 0.0),
                "event_profit": float(event_profit or 0.0),
                "shock_score": float(shock_score or 0.0),
                "shock_level": str(shock_level or "").strip().lower(),
                "shock_reason": str(shock_reason or "").strip(),
                "shock_action": str(shock_action or "").strip().lower(),
                "pre_shock_stage": str(pre_shock_stage or "").strip().lower(),
                "post_shock_stage": str(post_shock_stage or "").strip().lower(),
                "ticks_elapsed": 0,
                "shock_hold_delta_10": float("nan"),
                "shock_hold_delta_30": float("nan"),
                "filled_10": 0,
                "filled_30": 0,
                "resolved": 0,
                "close_time": "",
                "close_ts": 0,
            }
            merged = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
            merged = trade_logger._normalize_shock_df(merged)
            trade_logger._atomic_write_df(trade_logger.shock_event_filepath, merged)
            _set_cached_active_row(trade_logger, t, row)
        return True
    except Exception as exc:
        log.exception("Failed to register shock event ticket=%s: %s", t, exc)
        return False


def update_shock_event_progress(
    trade_logger,
    *,
    ticket: int,
    ticks_elapsed: int,
    delta_10: float | None = None,
    delta_30: float | None = None,
    logger: logging.Logger | None = None,
) -> dict:
    log = logger or logging.getLogger(__name__)
    if not bool(getattr(Config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
        return {}
    t = int(ticket or 0)
    if t <= 0:
        return {}
    trade_logger._ensure_shock_event_file()
    cached = _get_cached_active_row(trade_logger, t)
    if cached is None:
        cached = _load_latest_active_row_from_csv(trade_logger, t)
    if cached is None:
        return {}
    cached["ticks_elapsed"] = max(
        int(pd.to_numeric(cached.get("ticks_elapsed", 0), errors="coerce") or 0),
        int(ticks_elapsed or 0),
    )
    changed = False
    if delta_10 is not None and int(pd.to_numeric(cached.get("filled_10", 0), errors="coerce") or 0) == 0:
        cached["shock_hold_delta_10"] = float(delta_10)
        cached["filled_10"] = 1
        changed = True
    if delta_30 is not None and int(pd.to_numeric(cached.get("filled_30", 0), errors="coerce") or 0) == 0:
        cached["shock_hold_delta_30"] = float(delta_30)
        cached["filled_30"] = 1
        changed = True
    _set_cached_active_row(trade_logger, t, cached)
    if not changed:
        return {
            "shock_hold_delta_10": float(pd.to_numeric(cached.get("shock_hold_delta_10", 0.0), errors="coerce"))
            if int(pd.to_numeric(cached.get("filled_10", 0), errors="coerce") or 0) == 1
            else None,
            "shock_hold_delta_30": float(pd.to_numeric(cached.get("shock_hold_delta_30", 0.0), errors="coerce"))
            if int(pd.to_numeric(cached.get("filled_30", 0), errors="coerce") or 0) == 1
            else None,
        }
    try:
        with trade_logger._file_guard(f"{trade_logger.shock_event_filepath}.lock", trade_logger._shock_lock):
            try:
                base = pd.read_csv(trade_logger.shock_event_filepath, encoding="utf-8-sig")
            except Exception:
                base = pd.DataFrame(columns=trade_logger._shock_columns())
            base = trade_logger._normalize_shock_df(base)
            cand = base[(base["ticket"] == t) & (base["resolved"] == 0)]
            if cand.empty:
                return {}
            idx = int(cand.sort_values("event_ts", ascending=False).index[0])
            base.at[idx, "ticks_elapsed"] = int(cached.get("ticks_elapsed", 0) or 0)
            if int(pd.to_numeric(cached.get("filled_10", 0), errors="coerce") or 0) == 1:
                base.at[idx, "shock_hold_delta_10"] = float(cached.get("shock_hold_delta_10", 0.0) or 0.0)
                base.at[idx, "filled_10"] = 1
            if int(pd.to_numeric(cached.get("filled_30", 0), errors="coerce") or 0) == 1:
                base.at[idx, "shock_hold_delta_30"] = float(cached.get("shock_hold_delta_30", 0.0) or 0.0)
                base.at[idx, "filled_30"] = 1
            base = trade_logger._normalize_shock_df(base)
            trade_logger._atomic_write_df(trade_logger.shock_event_filepath, base)
            return {
                "shock_hold_delta_10": float(pd.to_numeric(cached.get("shock_hold_delta_10", 0.0), errors="coerce"))
                if int(pd.to_numeric(cached.get("filled_10", 0), errors="coerce") or 0) == 1
                else None,
                "shock_hold_delta_30": float(pd.to_numeric(cached.get("shock_hold_delta_30", 0.0), errors="coerce"))
                if int(pd.to_numeric(cached.get("filled_30", 0), errors="coerce") or 0) == 1
                else None,
            }
    except Exception as exc:
        log.exception("Failed to update shock progress ticket=%s: %s", t, exc)
        return {}


def resolve_shock_event_on_close(
    trade_logger,
    *,
    ticket: int,
    close_time: str,
    close_ts: int,
    logger: logging.Logger | None = None,
) -> dict:
    log = logger or logging.getLogger(__name__)
    if not bool(getattr(Config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
        return {}
    t = int(ticket or 0)
    if t <= 0:
        return {}
    trade_logger._ensure_shock_event_file()
    cached = _get_cached_active_row(trade_logger, t)
    try:
        with trade_logger._file_guard(f"{trade_logger.shock_event_filepath}.lock", trade_logger._shock_lock):
            try:
                base = pd.read_csv(trade_logger.shock_event_filepath, encoding="utf-8-sig")
            except Exception:
                base = pd.DataFrame(columns=trade_logger._shock_columns())
            base = trade_logger._normalize_shock_df(base)
            cand = base[(base["ticket"] == t) & (base["resolved"] == 0)]
            if cand.empty:
                return {}
            idx = int(cand.sort_values("event_ts", ascending=False).index[0])
            base.at[idx, "resolved"] = 1
            base.at[idx, "close_time"] = str(close_time or "").strip()
            base.at[idx, "close_ts"] = int(close_ts or 0)
            row = base.loc[idx]
            base = trade_logger._normalize_shock_df(base)
            trade_logger._atomic_write_df(trade_logger.shock_event_filepath, base)
            out = {
                "shock_score": float(pd.to_numeric(row.get("shock_score", 0.0), errors="coerce") or 0.0),
                "shock_level": str(row.get("shock_level", "") or "").strip().lower(),
                "shock_reason": str(row.get("shock_reason", "") or "").strip(),
                "shock_action": str(row.get("shock_action", "") or "").strip().lower(),
                "pre_shock_stage": str(row.get("pre_shock_stage", "") or "").strip().lower(),
                "post_shock_stage": str(row.get("post_shock_stage", "") or "").strip().lower(),
                "shock_at_profit": float(pd.to_numeric(row.get("event_profit", 0.0), errors="coerce") or 0.0),
            }
            if int(pd.to_numeric(row.get("filled_10", 0), errors="coerce") or 0) == 1:
                out["shock_hold_delta_10"] = float(pd.to_numeric(row.get("shock_hold_delta_10", 0.0), errors="coerce") or 0.0)
            if int(pd.to_numeric(row.get("filled_30", 0), errors="coerce") or 0) == 1:
                out["shock_hold_delta_30"] = float(pd.to_numeric(row.get("shock_hold_delta_30", 0.0), errors="coerce") or 0.0)
            _set_cached_active_row(trade_logger, t, None)
            return out
    except Exception as exc:
        log.exception("Failed to resolve shock event ticket=%s: %s", t, exc)
        return {}
