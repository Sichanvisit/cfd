# 한글 설명: TradeLogger의 OPEN 스냅샷 업서트 로직을 분리한 모듈입니다.
"""OPEN snapshot upsert helper extracted from TradeLogger."""

from __future__ import annotations

import json
import logging

import pandas as pd

from backend.core.config import Config


def _pick_text(new_value, current_value="", *, upper: bool = False, lower: bool = False) -> str:
    text = str(new_value or "").strip()
    if not text:
        text = str(current_value or "").strip()
    if upper:
        text = text.upper()
    if lower:
        text = text.lower()
    return text


def _build_snapshot_signature(snapshot: dict) -> str:
    if not isinstance(snapshot, dict):
        return ""
    normalized = {}
    for key, value in snapshot.items():
        if isinstance(value, dict):
            normalized[str(key)] = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        elif isinstance(value, list):
            normalized[str(key)] = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        else:
            normalized[str(key)] = value
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def upsert_open_snapshots(trade_logger, snapshots, logger: logging.Logger | None = None):
    log = logger or logging.getLogger(__name__)
    if not snapshots:
        return 0
    try:
        signature_cache = getattr(trade_logger, "_open_snapshot_signature_cache", None)
        if not isinstance(signature_cache, dict):
            signature_cache = {}
            setattr(trade_logger, "_open_snapshot_signature_cache", signature_cache)

        signature_by_ticket = {}
        cache_enabled = bool(getattr(Config, "OPEN_SNAPSHOT_CACHE_ENABLED", True))
        all_cached = bool(cache_enabled)
        for snap in snapshots:
            ticket = int(snap.get("ticket", 0) or 0)
            if ticket <= 0:
                continue
            signature = _build_snapshot_signature(dict(snap or {}))
            signature_by_ticket[ticket] = signature
            if signature_cache.get(ticket, "") != signature:
                all_cached = False
        if cache_enabled and signature_by_ticket and all_cached:
            return 0

        df = trade_logger._read_open_df_safe()
        updated = 0

        for snap in snapshots:
            ticket = int(snap.get("ticket", 0) or 0)
            if ticket <= 0:
                continue

            source = str(snap.get("source", "MANUAL")).upper()
            reason = str(snap.get("entry_reason", "") or "").strip()
            if reason and not reason.startswith("["):
                reason = f"[{source}] {reason}"
            regime = snap.get("regime", {}) or {}

            idx_open = df.index[(df["ticket"] == ticket) & (df["status"] == "OPEN")]
            if not idx_open.empty:
                i = idx_open.tolist()[-1]
                row_changed = False

                def _set_value(column: str, value):
                    nonlocal row_changed
                    if str(column) not in df.columns:
                        return
                    current_value = df.at[i, str(column)]
                    if pd.isna(current_value) and pd.isna(value):
                        return
                    if str(current_value) == str(value):
                        return
                    df.at[i, str(column)] = value
                    row_changed = True

                _set_value("symbol", str(snap.get("symbol", df.at[i, "symbol"]) or ""))
                _set_value("direction", str(snap.get("direction", df.at[i, "direction"]) or ""))
                _set_value("lot", float(snap.get("lot", df.at[i, "lot"]) or 0.0))
                _set_value("open_price", float(snap.get("open_price", df.at[i, "open_price"]) or 0.0))
                _set_value("decision_row_key", _pick_text(
                    snap.get("decision_row_key", ""),
                    df.at[i, "decision_row_key"],
                ))
                _set_value("runtime_snapshot_key", _pick_text(
                    snap.get("runtime_snapshot_key", ""),
                    df.at[i, "runtime_snapshot_key"],
                ))
                _set_value("trade_link_key", _pick_text(
                    snap.get("trade_link_key", ""),
                    df.at[i, "trade_link_key"],
                ))
                _set_value("replay_row_key", _pick_text(
                    snap.get("replay_row_key", ""),
                    df.at[i, "replay_row_key"],
                ))
                current_reason = str(df.at[i, "entry_reason"] or "").strip()
                is_manual_locked = current_reason.startswith("[MANUAL]") and source == "MANUAL"
                if not is_manual_locked or int(pd.to_numeric(df.at[i, "entry_score"], errors="coerce") or 0) <= 0:
                    _set_value("entry_score", int(snap.get("entry_score", df.at[i, "entry_score"]) or 0))
                if (not is_manual_locked) or int(pd.to_numeric(df.at[i, "contra_score_at_entry"], errors="coerce") or 0) <= 0:
                    _set_value("contra_score_at_entry", int(snap.get("contra_score_at_entry", df.at[i, "contra_score_at_entry"]) or 0))
                if reason and ((not is_manual_locked) or (not current_reason)):
                    _set_value("entry_reason", reason)
                snap_stage = trade_logger._normalize_entry_stage(snap.get("entry_stage", df.at[i, "entry_stage"]))
                if (not is_manual_locked) or str(df.at[i, "entry_stage"]).strip() == "":
                    _set_value("entry_stage", snap_stage)
                _set_value("entry_setup_id", _pick_text(
                    snap.get("entry_setup_id", ""),
                    df.at[i, "entry_setup_id"],
                    lower=True,
                ))
                _set_value("management_profile_id", _pick_text(
                    snap.get("management_profile_id", ""),
                    df.at[i, "management_profile_id"],
                    lower=True,
                ))
                _set_value("invalidation_id", _pick_text(
                    snap.get("invalidation_id", ""),
                    df.at[i, "invalidation_id"],
                    lower=True,
                ))
                _set_value("exit_profile", _pick_text(
                    snap.get("exit_profile", ""),
                    df.at[i, "exit_profile"],
                    lower=True,
                ))
                _set_value("prediction_bundle", _pick_text(
                    snap.get("prediction_bundle", ""),
                    df.at[i, "prediction_bundle"],
                ))
                _set_value("entry_wait_state", _pick_text(
                    snap.get("entry_wait_state", ""),
                    df.at[i, "entry_wait_state"],
                    upper=True,
                ))
                _set_value("entry_quality", pd.to_numeric(snap.get("entry_quality", df.at[i, "entry_quality"]), errors="coerce"))
                _set_value("entry_model_confidence", pd.to_numeric(snap.get("entry_model_confidence", df.at[i, "entry_model_confidence"]), errors="coerce"))
                _set_value("entry_h1_context_score", pd.to_numeric(snap.get("entry_h1_context_score", df.at[i, "entry_h1_context_score"]), errors="coerce"))
                _set_value("entry_m1_trigger_score", pd.to_numeric(snap.get("entry_m1_trigger_score", df.at[i, "entry_m1_trigger_score"]), errors="coerce"))
                _set_value("entry_h1_gate_pass", pd.to_numeric(snap.get("entry_h1_gate_pass", df.at[i, "entry_h1_gate_pass"]), errors="coerce"))
                _set_value("entry_h1_gate_reason", str(snap.get("entry_h1_gate_reason", df.at[i, "entry_h1_gate_reason"]) or "").strip())
                _set_value("entry_topdown_gate_pass", pd.to_numeric(snap.get("entry_topdown_gate_pass", df.at[i, "entry_topdown_gate_pass"]), errors="coerce"))
                _set_value("entry_topdown_gate_reason", str(snap.get("entry_topdown_gate_reason", df.at[i, "entry_topdown_gate_reason"]) or "").strip())
                _set_value("entry_topdown_align_count", pd.to_numeric(snap.get("entry_topdown_align_count", df.at[i, "entry_topdown_align_count"]), errors="coerce"))
                _set_value("entry_topdown_conflict_count", pd.to_numeric(snap.get("entry_topdown_conflict_count", df.at[i, "entry_topdown_conflict_count"]), errors="coerce"))
                _set_value("entry_topdown_seen_count", pd.to_numeric(snap.get("entry_topdown_seen_count", df.at[i, "entry_topdown_seen_count"]), errors="coerce"))
                _set_value("entry_session_name", str(snap.get("entry_session_name", df.at[i, "entry_session_name"]) or "").strip().upper())
                _set_value("entry_weekday", pd.to_numeric(snap.get("entry_weekday", df.at[i, "entry_weekday"]), errors="coerce"))
                _set_value("entry_session_threshold_mult", pd.to_numeric(snap.get("entry_session_threshold_mult", df.at[i, "entry_session_threshold_mult"]), errors="coerce"))
                _set_value("entry_atr_ratio", pd.to_numeric(snap.get("entry_atr_ratio", df.at[i, "entry_atr_ratio"]), errors="coerce"))
                _set_value("entry_atr_threshold_mult", pd.to_numeric(snap.get("entry_atr_threshold_mult", df.at[i, "entry_atr_threshold_mult"]), errors="coerce"))
                _set_value("entry_request_price", pd.to_numeric(snap.get("entry_request_price", df.at[i, "entry_request_price"]), errors="coerce"))
                _set_value("entry_fill_price", pd.to_numeric(snap.get("entry_fill_price", df.at[i, "entry_fill_price"]), errors="coerce"))
                _set_value("entry_slippage_points", pd.to_numeric(snap.get("entry_slippage_points", df.at[i, "entry_slippage_points"]), errors="coerce"))
                _set_value("signal_age_sec", pd.to_numeric(snap.get("signal_age_sec", df.at[i, "signal_age_sec"]), errors="coerce"))
                _set_value("bar_age_sec", pd.to_numeric(snap.get("bar_age_sec", df.at[i, "bar_age_sec"]), errors="coerce"))
                _set_value("decision_latency_ms", pd.to_numeric(snap.get("decision_latency_ms", df.at[i, "decision_latency_ms"]), errors="coerce"))
                _set_value("order_submit_latency_ms", pd.to_numeric(snap.get("order_submit_latency_ms", df.at[i, "order_submit_latency_ms"]), errors="coerce"))
                _set_value("missing_feature_count", pd.to_numeric(snap.get("missing_feature_count", df.at[i, "missing_feature_count"]), errors="coerce"))
                _set_value("data_completeness_ratio", pd.to_numeric(snap.get("data_completeness_ratio", df.at[i, "data_completeness_ratio"]), errors="coerce"))
                _set_value("used_fallback_count", pd.to_numeric(snap.get("used_fallback_count", df.at[i, "used_fallback_count"]), errors="coerce"))
                _set_value("compatibility_mode", _pick_text(
                    snap.get("compatibility_mode", ""),
                    df.at[i, "compatibility_mode"],
                    lower=True,
                ))
                _set_value("detail_blob_bytes", pd.to_numeric(snap.get("detail_blob_bytes", df.at[i, "detail_blob_bytes"]), errors="coerce"))
                _set_value("snapshot_payload_bytes", pd.to_numeric(snap.get("snapshot_payload_bytes", df.at[i, "snapshot_payload_bytes"]), errors="coerce"))
                _set_value("row_payload_bytes", pd.to_numeric(snap.get("row_payload_bytes", df.at[i, "row_payload_bytes"]), errors="coerce"))
                _set_value("exit_request_price", pd.to_numeric(snap.get("exit_request_price", df.at[i, "exit_request_price"]), errors="coerce"))
                _set_value("exit_fill_price", pd.to_numeric(snap.get("exit_fill_price", df.at[i, "exit_fill_price"]), errors="coerce"))
                _set_value("exit_slippage_points", pd.to_numeric(snap.get("exit_slippage_points", df.at[i, "exit_slippage_points"]), errors="coerce"))
                _set_value("regime_at_entry", str(snap.get("regime_at_entry", df.at[i, "regime_at_entry"] or regime.get("name", "")) or "").strip().upper())
                _set_value("regime_name", str(regime.get("name", df.at[i, "regime_name"]) or ""))
                _set_value("regime_volume_ratio", pd.to_numeric(regime.get("volume_ratio", df.at[i, "regime_volume_ratio"]), errors="coerce"))
                _set_value("regime_volatility_ratio", pd.to_numeric(regime.get("volatility_ratio", df.at[i, "regime_volatility_ratio"]), errors="coerce"))
                _set_value("regime_spread_ratio", pd.to_numeric(regime.get("spread_ratio", df.at[i, "regime_spread_ratio"]), errors="coerce"))
                _set_value("regime_buy_multiplier", pd.to_numeric(regime.get("buy_multiplier", df.at[i, "regime_buy_multiplier"]), errors="coerce"))
                _set_value("regime_sell_multiplier", pd.to_numeric(regime.get("sell_multiplier", df.at[i, "regime_sell_multiplier"]), errors="coerce"))
                indicators = snap.get("indicators", {}) or {}
                for col in trade_logger._indicator_columns():
                    if col in indicators:
                        _set_value(col, pd.to_numeric(indicators.get(col), errors="coerce"))
                if row_changed:
                    trade_logger.active_tickets.add(ticket)
                    signature_cache[ticket] = signature_by_ticket.get(ticket, "")
                    updated += 1
                elif cache_enabled and ticket in signature_by_ticket:
                    signature_cache[ticket] = signature_by_ticket[ticket]
                continue

            idx_any = df.index[df["ticket"] == ticket]
            if not idx_any.empty and (df.loc[idx_any, "status"] == "CLOSED").any():
                continue

            open_ts = int(snap.get("open_ts", 0) or 0)
            open_time = str(snap.get("open_time", "") or "").strip()
            if not open_time:
                if open_ts > 0:
                    open_time = trade_logger._ts_to_kst_text(open_ts)
                else:
                    now_dt = trade_logger._now_kst_dt()
                    open_time = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                    open_ts = int(now_dt.timestamp())

            row = {
                "ticket": ticket,
                "symbol": str(snap.get("symbol", "") or ""),
                "direction": str(snap.get("direction", "") or ""),
                "lot": float(snap.get("lot", 0.0) or 0.0),
                "open_time": open_time,
                "open_ts": int(open_ts),
                "open_price": float(snap.get("open_price", 0.0) or 0.0),
                "decision_row_key": str(snap.get("decision_row_key", "") or "").strip(),
                "runtime_snapshot_key": str(snap.get("runtime_snapshot_key", "") or "").strip(),
                "trade_link_key": str(snap.get("trade_link_key", "") or "").strip(),
                "replay_row_key": str(snap.get("replay_row_key", "") or "").strip(),
                "signal_age_sec": pd.to_numeric(snap.get("signal_age_sec", 0.0), errors="coerce"),
                "bar_age_sec": pd.to_numeric(snap.get("bar_age_sec", 0.0), errors="coerce"),
                "decision_latency_ms": pd.to_numeric(snap.get("decision_latency_ms", 0), errors="coerce"),
                "order_submit_latency_ms": pd.to_numeric(snap.get("order_submit_latency_ms", 0), errors="coerce"),
                "missing_feature_count": pd.to_numeric(snap.get("missing_feature_count", 0), errors="coerce"),
                "data_completeness_ratio": pd.to_numeric(snap.get("data_completeness_ratio", 0.0), errors="coerce"),
                "used_fallback_count": pd.to_numeric(snap.get("used_fallback_count", 0), errors="coerce"),
                "compatibility_mode": str(snap.get("compatibility_mode", "") or "").strip().lower(),
                "detail_blob_bytes": pd.to_numeric(snap.get("detail_blob_bytes", 0), errors="coerce"),
                "snapshot_payload_bytes": pd.to_numeric(snap.get("snapshot_payload_bytes", 0), errors="coerce"),
                "row_payload_bytes": pd.to_numeric(snap.get("row_payload_bytes", 0), errors="coerce"),
                "entry_score": int(snap.get("entry_score", 0) or 0),
                "contra_score_at_entry": int(snap.get("contra_score_at_entry", 0) or 0),
                "entry_stage": trade_logger._normalize_entry_stage(snap.get("entry_stage", "balanced")),
                "entry_setup_id": str(snap.get("entry_setup_id", "") or "").strip().lower(),
                "management_profile_id": str(snap.get("management_profile_id", "") or "").strip().lower(),
                "invalidation_id": str(snap.get("invalidation_id", "") or "").strip().lower(),
                "exit_profile": str(snap.get("exit_profile", "") or "").strip().lower(),
                "prediction_bundle": str(snap.get("prediction_bundle", "") or "").strip(),
                "entry_wait_state": str(snap.get("entry_wait_state", "") or "").strip().upper(),
                "entry_quality": pd.to_numeric(snap.get("entry_quality", 0.0), errors="coerce"),
                "entry_model_confidence": pd.to_numeric(snap.get("entry_model_confidence", 0.0), errors="coerce"),
                "entry_h1_context_score": pd.to_numeric(snap.get("entry_h1_context_score", 0.0), errors="coerce"),
                "entry_m1_trigger_score": pd.to_numeric(snap.get("entry_m1_trigger_score", 0.0), errors="coerce"),
                "entry_h1_gate_pass": pd.to_numeric(snap.get("entry_h1_gate_pass", 0.0), errors="coerce"),
                "entry_h1_gate_reason": str(snap.get("entry_h1_gate_reason", "") or "").strip(),
                "entry_topdown_gate_pass": pd.to_numeric(snap.get("entry_topdown_gate_pass", 0.0), errors="coerce"),
                "entry_topdown_gate_reason": str(snap.get("entry_topdown_gate_reason", "") or "").strip(),
                "entry_topdown_align_count": pd.to_numeric(snap.get("entry_topdown_align_count", 0.0), errors="coerce"),
                "entry_topdown_conflict_count": pd.to_numeric(snap.get("entry_topdown_conflict_count", 0.0), errors="coerce"),
                "entry_topdown_seen_count": pd.to_numeric(snap.get("entry_topdown_seen_count", 0.0), errors="coerce"),
                "entry_session_name": str(snap.get("entry_session_name", "") or "").strip().upper(),
                "entry_weekday": pd.to_numeric(snap.get("entry_weekday", 0.0), errors="coerce"),
                "entry_session_threshold_mult": pd.to_numeric(snap.get("entry_session_threshold_mult", 1.0), errors="coerce"),
                "entry_atr_ratio": pd.to_numeric(snap.get("entry_atr_ratio", 1.0), errors="coerce"),
                "entry_atr_threshold_mult": pd.to_numeric(snap.get("entry_atr_threshold_mult", 1.0), errors="coerce"),
                "entry_request_price": pd.to_numeric(snap.get("entry_request_price", 0.0), errors="coerce"),
                "entry_fill_price": pd.to_numeric(snap.get("entry_fill_price", 0.0), errors="coerce"),
                "entry_slippage_points": pd.to_numeric(snap.get("entry_slippage_points", 0.0), errors="coerce"),
                "exit_request_price": pd.to_numeric(snap.get("exit_request_price", 0.0), errors="coerce"),
                "exit_fill_price": pd.to_numeric(snap.get("exit_fill_price", 0.0), errors="coerce"),
                "exit_slippage_points": pd.to_numeric(snap.get("exit_slippage_points", 0.0), errors="coerce"),
                "regime_at_entry": str(snap.get("regime_at_entry", regime.get("name", "")) or "").strip().upper(),
                "close_time": "",
                "close_ts": 0,
                "close_price": 0.0,
                "profit": 0.0,
                "points": 0.0,
                "entry_reason": reason or f"[{source}] Snapshot",
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
            indicators = snap.get("indicators", {}) or {}
            for col in trade_logger._indicator_columns():
                row[col] = pd.to_numeric(indicators.get(col, float("nan")), errors="coerce")
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            trade_logger.active_tickets.add(ticket)
            signature_cache[ticket] = signature_by_ticket.get(ticket, "")
            updated += 1

        if updated > 0:
            trade_logger._write_open_df(df)
            trade_logger._sync_open_rows_to_store(trade_logger._normalize_dataframe(df[df["status"] == "OPEN"].copy()))
        return int(updated)
    except Exception as exc:
        log.exception("Failed to upsert OPEN snapshots: %s", exc)
        return 0
