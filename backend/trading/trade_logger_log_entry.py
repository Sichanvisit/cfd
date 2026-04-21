# 파일 설명: TradeLogger의 log_entry 로직을 분리한 모듈입니다.
"""log_entry helper extracted from TradeLogger."""

from __future__ import annotations

import time

import pandas as pd

from backend.core.config import Config

def log_entry(
    self,
    ticket,
    symbol,
    direction,
    price,
    reason,
    entry_score=0,
    contra_score=0,
    lot=0.0,
    indicators=None,
    regime=None,
    entry_stage="balanced",
    entry_setup_id="",
    management_profile_id="",
    invalidation_id="",
    exit_profile="",
    prediction_bundle="",
    entry_wait_state="",
    entry_quality=0.0,
    entry_model_confidence=0.0,
    regime_at_entry="",
    entry_h1_context_score=0.0,
    entry_m1_trigger_score=0.0,
    entry_h1_gate_pass=0.0,
    entry_h1_gate_reason="",
    entry_topdown_gate_pass=0.0,
    entry_topdown_gate_reason="",
    entry_topdown_align_count=0.0,
    entry_topdown_conflict_count=0.0,
    entry_topdown_seen_count=0.0,
    entry_session_name="",
    entry_weekday=0.0,
    entry_session_threshold_mult=1.0,
    entry_atr_ratio=1.0,
    entry_atr_threshold_mult=1.0,
    entry_request_price=0.0,
    entry_fill_price=0.0,
    entry_slippage_points=0.0,
    exit_request_price=0.0,
    exit_fill_price=0.0,
    exit_slippage_points=0.0,
):
    parsed_entry_atr_ratio = pd.to_numeric(entry_atr_ratio, errors="coerce")
    effective_entry_atr_ratio = 1.0 if pd.isna(parsed_entry_atr_ratio) else float(parsed_entry_atr_ratio)
    regime_volatility_ratio = pd.to_numeric((regime or {}).get("volatility_ratio", float("nan")), errors="coerce")
    if (
        abs(effective_entry_atr_ratio) <= 1e-12
        or abs(effective_entry_atr_ratio - 1.0) <= 1e-12
    ) and (not pd.isna(regime_volatility_ratio)):
        regime_volatility_ratio = float(regime_volatility_ratio)
        if regime_volatility_ratio > 0.0 and abs(regime_volatility_ratio - 1.0) > 1e-6:
            effective_entry_atr_ratio = regime_volatility_ratio
    self.active_tickets.add(ticket)
    indicators = indicators or {}
    regime = regime or {}
    reason_text = str(reason or "").strip()
    if reason_text and not reason_text.startswith("["):
        reason_text = f"[AUTO] {reason_text}"
    now_dt = self._now_kst_dt()
    data = {
        "ticket": ticket,
        "symbol": symbol,
        "direction": direction,
        "lot": float(lot or 0.0),
        "open_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "open_ts": int(now_dt.timestamp()),
        "open_price": price,
        "entry_score": int(entry_score),
        "contra_score_at_entry": int(contra_score),
        "entry_stage": self._normalize_entry_stage(entry_stage),
        "entry_setup_id": str(entry_setup_id or ""),
        "management_profile_id": str(management_profile_id or "").strip().lower(),
        "invalidation_id": str(invalidation_id or "").strip().lower(),
        "exit_profile": str(exit_profile or "").strip().lower(),
        "prediction_bundle": str(prediction_bundle or ""),
        "entry_wait_state": str(entry_wait_state or "").strip().upper(),
        "entry_quality": float(pd.to_numeric(entry_quality, errors="coerce") or 0.0),
        "entry_model_confidence": float(pd.to_numeric(entry_model_confidence, errors="coerce") or 0.0),
        "entry_h1_context_score": float(pd.to_numeric(entry_h1_context_score, errors="coerce") or 0.0),
        "entry_m1_trigger_score": float(pd.to_numeric(entry_m1_trigger_score, errors="coerce") or 0.0),
        "entry_h1_gate_pass": float(pd.to_numeric(entry_h1_gate_pass, errors="coerce") or 0.0),
        "entry_h1_gate_reason": str(entry_h1_gate_reason or "").strip(),
        "entry_topdown_gate_pass": float(pd.to_numeric(entry_topdown_gate_pass, errors="coerce") or 0.0),
        "entry_topdown_gate_reason": str(entry_topdown_gate_reason or "").strip(),
        "entry_topdown_align_count": float(pd.to_numeric(entry_topdown_align_count, errors="coerce") or 0.0),
        "entry_topdown_conflict_count": float(pd.to_numeric(entry_topdown_conflict_count, errors="coerce") or 0.0),
        "entry_topdown_seen_count": float(pd.to_numeric(entry_topdown_seen_count, errors="coerce") or 0.0),
        "entry_session_name": str(entry_session_name or "").strip().upper(),
        "entry_weekday": float(pd.to_numeric(entry_weekday, errors="coerce") or 0.0),
        "entry_session_threshold_mult": float(pd.to_numeric(entry_session_threshold_mult, errors="coerce") or 1.0),
        "entry_atr_ratio": float(effective_entry_atr_ratio),
        "entry_atr_threshold_mult": float(pd.to_numeric(entry_atr_threshold_mult, errors="coerce") or 1.0),
        "entry_request_price": float(pd.to_numeric(entry_request_price, errors="coerce") or 0.0),
        "entry_fill_price": float(pd.to_numeric(entry_fill_price, errors="coerce") or 0.0),
        "entry_slippage_points": float(pd.to_numeric(entry_slippage_points, errors="coerce") or 0.0),
        "exit_request_price": float(pd.to_numeric(exit_request_price, errors="coerce") or 0.0),
        "exit_fill_price": float(pd.to_numeric(exit_fill_price, errors="coerce") or 0.0),
        "exit_slippage_points": float(pd.to_numeric(exit_slippage_points, errors="coerce") or 0.0),
        "regime_at_entry": str(regime_at_entry or regime.get("name", "") or "").strip().upper(),
        "close_time": "",
        "close_ts": 0,
        "close_price": 0.0,
        "profit": 0.0,
        "points": 0.0,
        "entry_reason": reason_text,
        "exit_reason": "",
        "exit_score": 0,
        "status": "OPEN",
        "regime_name": str(regime.get("name", "") or ""),
        "regime_volume_ratio": pd.to_numeric(regime.get("volume_ratio", float("nan")), errors="coerce"),
        "regime_volatility_ratio": pd.to_numeric(regime.get("volatility_ratio", float("nan")), errors="coerce"),
        "regime_spread_ratio": pd.to_numeric(regime.get("spread_ratio", float("nan")), errors="coerce"),
        "regime_buy_multiplier": pd.to_numeric(regime.get("buy_multiplier", float("nan")), errors="coerce"),
        "regime_sell_multiplier": pd.to_numeric(regime.get("sell_multiplier", float("nan")), errors="coerce"),
    }
    for col in self._indicator_columns():
        data[col] = pd.to_numeric(indicators.get(col, float("nan")), errors="coerce")
    try:
        df = self._read_open_df_safe()
        df = self._normalize_dataframe(df)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True, sort=False)
        df = self._normalize_dataframe(df)
        self._write_open_df(df)
    except Exception as exc:
        logger.exception("Failed to append OPEN row atomically: %s", exc)
        raise
    self._upsert_open_rows_to_store(pd.DataFrame([data]))

