# 한글 설명: TradingApplication의 즉시 반전 진입(_try_reverse_entry) 로직을 분리한 모듈입니다.
"""Reverse-entry helper extracted from TradingApplication."""

from __future__ import annotations

import time

from backend.core.config import Config
from backend.services.exit_profile_router import resolve_exit_profile


def _ensure_pending_reverse_store(app) -> dict:
    store = getattr(app, "pending_reverse_by_symbol", None)
    if not isinstance(store, dict):
        store = {}
        setattr(app, "pending_reverse_by_symbol", store)
    return store


def _clear_pending_reverse(app, symbol: str) -> None:
    _ensure_pending_reverse_store(app).pop(str(symbol), None)


def _set_pending_reverse(app, *, symbol: str, action: str, score: float, reasons: list[str]) -> None:
    ttl_sec = max(1.0, float(getattr(Config, "IMMEDIATE_REVERSE_PENDING_TTL_SEC", 20.0)))
    now_s = time.time()
    _ensure_pending_reverse_store(app)[str(symbol)] = {
        "action": str(action or "").upper(),
        "score": float(score or 0.0),
        "reasons": list(reasons or []),
        "created_at": now_s,
        "expires_at": now_s + ttl_sec,
    }


def _get_pending_reverse(app, symbol: str) -> dict | None:
    store = _ensure_pending_reverse_store(app)
    symbol_key = str(symbol)
    pending = store.get(symbol_key)
    if not isinstance(pending, dict):
        return None
    expires_at = float(pending.get("expires_at", 0.0) or 0.0)
    if expires_at > 0.0 and time.time() > expires_at:
        store.pop(symbol_key, None)
        return None
    action = str(pending.get("action", "") or "").upper()
    if action not in {"BUY", "SELL"}:
        store.pop(symbol_key, None)
        return None
    return pending


def _resolve_reverse_candidate(app, *, symbol: str, reverse_action, reverse_score, reverse_reasons) -> tuple[str, float, list[str], bool] | None:
    if reverse_action:
        _set_pending_reverse(
            app,
            symbol=symbol,
            action=str(reverse_action),
            score=float(reverse_score or 0.0),
            reasons=list(reverse_reasons or []),
        )
        return str(reverse_action).upper(), float(reverse_score or 0.0), list(reverse_reasons or []), False
    pending = _get_pending_reverse(app, symbol)
    if not pending:
        return None
    return (
        str(pending.get("action", "") or "").upper(),
        float(pending.get("score", 0.0) or 0.0),
        list(pending.get("reasons", []) or []),
        True,
    )


def _get_managed_positions(app, symbol: str) -> list:
    positions_now = app.broker.positions_get(symbol=symbol) or []
    return [p for p in positions_now if int(getattr(p, "magic", 0) or 0) == int(Config.MAGIC_NUMBER)]


def _wait_for_symbol_flat(app, symbol: str) -> list:
    managed_positions = _get_managed_positions(app, symbol)
    if not managed_positions:
        return []
    wait_sec = max(0.0, float(getattr(Config, "IMMEDIATE_REVERSE_FLAT_WAIT_SEC", 1.2)))
    deadline = time.time() + wait_sec
    while managed_positions and time.time() < deadline:
        time.sleep(0.15)
        managed_positions = _get_managed_positions(app, symbol)
    return managed_positions


def try_reverse_entry(
    app,
    *,
    reverse_action,
    reverse_score,
    reverse_reasons,
    symbol,
    buy_s,
    sell_s,
    tick,
    scorer,
    df_all,
    trade_logger,
):
    resolved_candidate = _resolve_reverse_candidate(
        app,
        symbol=symbol,
        reverse_action=reverse_action,
        reverse_score=reverse_score,
        reverse_reasons=reverse_reasons,
    )
    if not resolved_candidate:
        return
    reverse_action, reverse_score, reverse_reasons, _loaded_from_pending = resolved_candidate
    if not Config.ALLOW_IMMEDIATE_REVERSE:
        cooldown_ok = (time.time() - app.last_entry_time.get(symbol, 0)) > Config.ENTRY_COOLDOWN
        if not cooldown_ok:
            return

    my_positions_now = _wait_for_symbol_flat(app, symbol)
    # We still avoid opening a reverse order while our managed position is visibly alive,
    # but we now give the just-closed thesis a short grace window and keep the reverse
    # candidate alive for the next loops instead of dropping it immediately.
    if my_positions_now:
        return
    max_positions_for_symbol = int(Config.get_max_positions(symbol))
    if len(my_positions_now) >= max_positions_for_symbol:
        return

    lot = app.get_lot_size(symbol)
    final_reverse_score = reverse_score
    reverse_prob = None
    reverse_adj = 0
    entry_threshold = int(
        ((app.latest_signal_by_symbol.get(symbol, {}) if isinstance(app.latest_signal_by_symbol, dict) else {}) or {}).get(
            "entry_threshold", int(Config.ENTRY_THRESHOLD)
        )
    )
    if app.ai_runtime:
        contra_for_reverse = buy_s if reverse_action == "SELL" else sell_s
        feat = app._entry_features(
            symbol,
            reverse_action,
            reverse_score,
            contra_for_reverse,
            reverse_reasons,
            regime=app.latest_regime_by_symbol.get(symbol, {}),
            indicators=app._entry_indicator_snapshot(symbol, scorer, df_all),
        )
        dec = app.ai_runtime.predict_entry(feat, threshold=Config.AI_ENTRY_THRESHOLD)
        reverse_prob = float(dec.probability)
        reverse_adj = app._score_adjustment(dec.probability, Config.AI_ENTRY_WEIGHT)
        final_reverse_score = max(0, reverse_score + reverse_adj)
        if Config.AI_USE_ENTRY_FILTER and (not dec.decision) and float(dec.probability) < float(Config.AI_ENTRY_BLOCK_PROB):
            app._append_ai_entry_trace(
                {
                    "symbol": symbol,
                    "action": reverse_action,
                    "raw_score": reverse_score,
                    "contra_score": contra_for_reverse,
                    "probability": reverse_prob,
                    "score_adj": reverse_adj,
                    "final_score": final_reverse_score,
                    "threshold": Config.AI_ENTRY_THRESHOLD,
                    "blocked": True,
                }
            )
            _clear_pending_reverse(app, symbol)
            return
    reverse_threshold = max(
        int(
            Config.get_symbol_int(
                symbol,
                getattr(
                    Config,
                    "REVERSE_ENTRY_MIN_SCORE_BY_SYMBOL",
                    {"DEFAULT": int(getattr(Config, "REVERSE_ENTRY_MIN_SCORE", 170))},
                ),
                int(getattr(Config, "REVERSE_ENTRY_MIN_SCORE", 170)),
            )
        ),
        int(
            round(
                float(entry_threshold)
                * float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(
                            Config,
                            "REVERSE_ENTRY_THRESHOLD_MULT_BY_SYMBOL",
                            {"DEFAULT": float(getattr(Config, "REVERSE_ENTRY_THRESHOLD_MULT", 0.65))},
                        ),
                        float(getattr(Config, "REVERSE_ENTRY_THRESHOLD_MULT", 0.65)),
                    )
                )
            )
        ),
    )
    if int(final_reverse_score) < int(reverse_threshold):
        _clear_pending_reverse(app, symbol)
        return

    app._append_ai_entry_trace(
        {
            "symbol": symbol,
            "action": reverse_action,
            "raw_score": reverse_score,
            "contra_score": (buy_s if reverse_action == "SELL" else sell_s),
            "probability": reverse_prob,
            "score_adj": reverse_adj,
            "final_score": final_reverse_score,
            "threshold": Config.AI_ENTRY_THRESHOLD,
            "reverse_threshold": int(reverse_threshold),
            "blocked": False,
        }
    )

    ticket = app.execute_order(symbol, reverse_action, lot)
    if not ticket:
        return

    _clear_pending_reverse(app, symbol)
    app.last_entry_time[symbol] = time.time()
    price = tick.ask if reverse_action == "BUY" else tick.bid
    contra_for_reverse = buy_s if reverse_action == "SELL" else sell_s
    reverse_indicators = app._entry_indicator_snapshot(symbol, scorer, df_all)
    reverse_scored_reasons = app._build_scored_reasons(
        reverse_reasons if reverse_reasons else ["Adverse Reverse"],
        target_total=int(final_reverse_score),
        ai_adj=int(reverse_adj),
    )
    trade_logger.log_entry(
        ticket,
        symbol,
        reverse_action,
        price,
        ", ".join(reverse_scored_reasons),
        entry_score=final_reverse_score,
        contra_score=contra_for_reverse,
        indicators=reverse_indicators,
        regime=app.latest_regime_by_symbol.get(symbol, {}),
        entry_stage="balanced",
        entry_setup_id="immediate_reverse",
        exit_profile=resolve_exit_profile(entry_setup_id="range_upper_reversal_sell", fallback_profile="tight_protect"),
        entry_quality=max(0.0, min(1.0, float(reverse_prob) if reverse_prob is not None else 0.0)),
        entry_model_confidence=max(0.0, min(1.0, float(reverse_prob) if reverse_prob is not None else 0.0)),
        regime_at_entry=str((app.latest_regime_by_symbol.get(symbol, {}) or {}).get("name", "")).strip().upper(),
    )
    msg = app.format_entry_message(
        symbol,
        reverse_action,
        final_reverse_score,
        price,
        lot,
        reverse_scored_reasons[:3],
        1,
        max_positions_for_symbol,
        row=dict((app.latest_signal_by_symbol or {}).get(symbol, {}) or {}),
    )
    app.notify(msg)
    print(f"\n{msg}")
