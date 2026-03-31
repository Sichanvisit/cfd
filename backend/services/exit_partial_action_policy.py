"""Shared policy helpers for exit partial-close action candidates."""

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


def resolve_exit_partial_action_candidate_v1(
    *,
    pos_type: int,
    entry_price: float,
    position_volume: float,
    favorable_move_pct: float,
    dynamic_move_pct: float,
    profit: float,
    min_net_guard: float,
    roundtrip_cost: float,
    partial_done: bool,
) -> dict[str, object]:
    candidate = {
        "contract_version": "exit_partial_action_candidate_v1",
        "candidate_kind": "none",
        "should_execute": False,
        "close_reason": "Partial Take Profit",
        "partial_trigger": 0.0,
        "partial_profit_guard": 0.0,
        "partial_volume": 0.0,
        "be_price": 0.0,
        "skip_reason": "",
    }

    if not _to_bool(getattr(Config, "ENABLE_PARTIAL_BE", True), True):
        candidate["skip_reason"] = "disabled"
        return candidate
    if _to_bool(partial_done, False):
        candidate["skip_reason"] = "already_done"
        return candidate

    partial_trigger = max(
        _to_float(dynamic_move_pct) * _to_float(getattr(Config, "PARTIAL_TRIGGER_MOVE_PCT_MULT", 2.0), 2.0),
        _to_float(getattr(Config, "PARTIAL_TRIGGER_MIN_MOVE_PCT", 0.0012), 0.0012),
    )
    partial_profit_guard = max(
        _to_float(min_net_guard),
        _to_float(getattr(Config, "BE_MIN_LOCK_PROFIT_USD", 0.12), 0.12) + _to_float(roundtrip_cost),
    )
    candidate["partial_trigger"] = float(partial_trigger)
    candidate["partial_profit_guard"] = float(partial_profit_guard)

    if _to_float(favorable_move_pct) < float(partial_trigger):
        candidate["skip_reason"] = "move_below_trigger"
        return candidate
    if _to_float(profit) < float(partial_profit_guard):
        candidate["skip_reason"] = "profit_below_guard"
        return candidate

    raw_volume = _to_float(position_volume) * _to_float(getattr(Config, "PARTIAL_CLOSE_RATIO", 0.5), 0.5)
    partial_volume = max(0.01, round(float(raw_volume), 2))
    if partial_volume >= _to_float(position_volume):
        candidate["skip_reason"] = "volume_too_small"
        return candidate

    be_buffer_pct = max(0.0, _to_float(getattr(Config, "BE_BUFFER_PCT", 0.00015), 0.00015))
    if int(pos_type) == int(ORDER_TYPE_BUY):
        be_price = _to_float(entry_price) * (1.0 + be_buffer_pct)
    else:
        be_price = _to_float(entry_price) * (1.0 - be_buffer_pct)

    candidate.update(
        {
            "candidate_kind": "partial_close",
            "should_execute": True,
            "partial_volume": float(partial_volume),
            "be_price": float(be_price),
            "skip_reason": "",
        }
    )
    return candidate
