# 한글 설명: TradingApplication의 즉시 반전 진입(_try_reverse_entry) 로직을 분리한 모듈입니다.
"""Reverse-entry helper extracted from TradingApplication."""

from __future__ import annotations

import time

from backend.core.config import Config
from backend.services.exit_profile_router import resolve_exit_profile


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
    if not reverse_action:
        return
    if not Config.ALLOW_IMMEDIATE_REVERSE:
        cooldown_ok = (time.time() - app.last_entry_time.get(symbol, 0)) > Config.ENTRY_COOLDOWN
        if not cooldown_ok:
            return

    positions_now = app.broker.positions_get(symbol=symbol) or []
    my_positions_now = [p for p in positions_now if p.magic == Config.MAGIC_NUMBER]
    # Reverse entries should only happen after the current symbol thesis is fully cleared.
    # If the symbol still has any open managed position, another immediate reverse tends to
    # create duplicate whipsaw trades instead of a fresh confirmed reversal.
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
        len(my_positions_now) + 1,
        max_positions_for_symbol,
    )
    app.notify(msg)
    print(f"\n{msg}")
