"""Shared policy helpers for exit stop-up action candidates."""

from __future__ import annotations

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def resolve_exit_stop_up_action_candidate_v1(
    *,
    pos_type: int,
    entry_price: float,
    current_price: float,
    profit: float,
    peak_profit: float,
    exit_profile_id: str,
    chosen_stage: str,
) -> dict[str, object]:
    profile_id = str(exit_profile_id or "").strip().lower()
    stage_id = str(chosen_stage or "").strip().lower()
    candidate = {
        "contract_version": "exit_stop_up_action_candidate_v1",
        "candidate_kind": "none",
        "should_move": False,
        "target_sl": 0.0,
        "reason": "",
        "profile": profile_id,
        "min_profit": 0.0,
        "lock_peak": 0.0,
        "lock_ratio": 0.0,
    }

    if not _to_bool(getattr(Config, "EXIT_STOP_UP_ENABLED", True), True):
        return candidate

    entry_price_eff = _to_float(entry_price)
    current_price_eff = _to_float(current_price)
    profit_eff = _to_float(profit)
    peak_profit_eff = _to_float(peak_profit)
    if entry_price_eff <= 0.0 or current_price_eff <= 0.0 or max(profit_eff, peak_profit_eff) <= 0.0:
        return candidate

    is_tight = profile_id == "tight_protect" or stage_id in {"protect", "lock"}
    min_profit = _to_float(
        getattr(Config, "EXIT_STOP_UP_TIGHT_MIN_PROFIT_USD", 0.10)
        if is_tight
        else getattr(Config, "EXIT_STOP_UP_MIN_PROFIT_USD", 0.20),
        0.10 if is_tight else 0.20,
    )
    lock_peak = _to_float(
        getattr(Config, "EXIT_STOP_UP_TIGHT_LOCK_PEAK_USD", 0.50)
        if is_tight
        else getattr(Config, "EXIT_STOP_UP_LOCK_PEAK_USD", 0.80),
        0.50 if is_tight else 0.80,
    )
    lock_ratio = _to_float(
        getattr(Config, "EXIT_STOP_UP_TIGHT_LOCK_RATIO", 0.45)
        if is_tight
        else getattr(Config, "EXIT_STOP_UP_LOCK_RATIO", 0.35),
        0.45 if is_tight else 0.35,
    )
    candidate["min_profit"] = float(min_profit)
    candidate["lock_peak"] = float(lock_peak)
    candidate["lock_ratio"] = float(lock_ratio)

    if peak_profit_eff < float(min_profit) and profit_eff < float(min_profit):
        return candidate

    if int(pos_type) == int(ORDER_TYPE_BUY):
        favorable_distance = max(0.0, current_price_eff - entry_price_eff)
    else:
        favorable_distance = max(0.0, entry_price_eff - current_price_eff)
    if favorable_distance <= 0.0:
        return candidate

    be_buffer = max(0.0, entry_price_eff * _to_float(getattr(Config, "BE_BUFFER_PCT", 0.00015), 0.00015))
    lock_profit_now = bool(peak_profit_eff >= float(lock_peak))
    protected_distance = max(float(be_buffer), favorable_distance * float(lock_ratio)) if lock_profit_now else float(be_buffer)

    if int(pos_type) == int(ORDER_TYPE_BUY):
        target_sl = entry_price_eff + float(protected_distance)
        if target_sl >= current_price_eff:
            return candidate
    else:
        target_sl = entry_price_eff - float(protected_distance)
        if target_sl <= current_price_eff:
            return candidate

    candidate.update(
        {
            "candidate_kind": "profit_lock_stop_up" if lock_profit_now else "break_even_stop_up",
            "should_move": True,
            "target_sl": float(target_sl),
            "reason": "profit_lock_stop_up" if lock_profit_now else "break_even_stop_up",
        }
    )
    return candidate
