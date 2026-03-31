"""Shared entry wait belief-bias policy helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(converted):
        return float(default)
    return float(converted)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _upper(value: object) -> str:
    return str(value or "").strip().upper()


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _required_side(policy: object) -> str:
    upper = _upper(policy)
    if upper == "BUY_ONLY":
        return "BUY"
    if upper == "SELL_ONLY":
        return "SELL"
    return ""


def resolve_entry_wait_acting_side_v1(
    *,
    action: str = "",
    core_allowed_action: str = "",
    preflight_allowed_action: str = "",
    dominant_side: str = "",
) -> str:
    action_upper = _upper(action)
    if action_upper in {"BUY", "SELL"}:
        return action_upper
    required_side = _required_side(preflight_allowed_action) or _required_side(core_allowed_action)
    if required_side:
        return required_side
    dominant_side_upper = _upper(dominant_side)
    if dominant_side_upper in {"BUY", "SELL"}:
        return dominant_side_upper
    return ""


def resolve_entry_wait_belief_bias_v1(
    *,
    belief_state_v1: Mapping[str, Any] | None = None,
    belief_metadata: Mapping[str, Any] | None = None,
    action: str = "",
    core_allowed_action: str = "",
    preflight_allowed_action: str = "",
) -> dict[str, Any]:
    belief_state = _as_mapping(belief_state_v1)
    belief_meta = _as_mapping(belief_metadata)
    if not belief_state:
        return {
            "present": False,
            "acting_side": "",
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "buy_persistence": 0.0,
            "sell_persistence": 0.0,
            "active_persistence": 0.0,
            "buy_streak": 0,
            "sell_streak": 0,
            "active_streak": 0,
            "belief_spread": 0.0,
            "spread_abs": 0.0,
            "dominance_deadband": 0.05,
            "spread_clear": False,
            "spread_deadband": True,
            "persistence_low": True,
            "persistence_high": False,
            "prefer_confirm_release": False,
            "prefer_wait_lock": False,
            "wait_soft_mult": 1.0,
            "wait_hard_mult": 1.0,
            "enter_value_delta": 0.0,
            "wait_value_delta": 0.0,
        }

    dominant_side = _upper(
        belief_state.get("dominant_side", belief_meta.get("global_dominant_side", "BALANCED"))
    )
    dominant_mode = str(
        belief_state.get("dominant_mode", belief_meta.get("global_dominant_mode", "balanced")) or "balanced"
    ).lower()
    buy_persistence = _to_float(belief_state.get("buy_persistence", 0.0), 0.0)
    sell_persistence = _to_float(belief_state.get("sell_persistence", 0.0), 0.0)
    buy_streak = _to_int(belief_state.get("buy_streak", belief_meta.get("buy_streak", 0)), 0)
    sell_streak = _to_int(belief_state.get("sell_streak", belief_meta.get("sell_streak", 0)), 0)
    belief_spread = _to_float(belief_state.get("belief_spread", 0.0), 0.0)
    dominance_deadband = max(
        0.01,
        _to_float(belief_meta.get("dominance_deadband", 0.05), 0.05),
    )
    acting_side = resolve_entry_wait_acting_side_v1(
        action=action,
        core_allowed_action=core_allowed_action,
        preflight_allowed_action=preflight_allowed_action,
        dominant_side=dominant_side,
    )
    if acting_side == "BUY":
        active_persistence = buy_persistence
        active_streak = buy_streak
    elif acting_side == "SELL":
        active_persistence = sell_persistence
        active_streak = sell_streak
    else:
        active_persistence = max(buy_persistence, sell_persistence)
        active_streak = max(buy_streak, sell_streak)

    spread_abs = abs(float(belief_spread))
    spread_deadband = spread_abs < float(dominance_deadband)
    spread_clear = spread_abs >= max(float(dominance_deadband) * 1.20, 0.06)
    persistence_low = float(active_persistence) < 0.24 or int(active_streak) <= 1
    persistence_high = float(active_persistence) >= 0.38 and int(active_streak) >= 2
    dominant_matches = bool(acting_side) and str(dominant_side) == str(acting_side)

    prefer_confirm_release = bool(dominant_matches and persistence_high and spread_clear)
    prefer_wait_lock = bool(
        spread_deadband
        or not dominant_matches
        or persistence_low
    )

    wait_soft_mult = 1.0
    wait_hard_mult = 1.0
    enter_value_delta = 0.0
    wait_value_delta = 0.0

    if prefer_confirm_release:
        wait_soft_mult += 0.08
        wait_hard_mult += 0.12
        enter_value_delta += 0.20 + min(0.10, max(0.0, float(active_persistence) - 0.38) * 0.40)
        wait_value_delta -= 0.18
    if prefer_wait_lock:
        wait_soft_mult -= 0.06
        wait_hard_mult -= 0.08
        enter_value_delta -= 0.10
        wait_value_delta += 0.18 + max(0.0, float(dominance_deadband) - float(spread_abs)) * 1.20

    return {
        "present": True,
        "acting_side": str(acting_side),
        "dominant_side": str(dominant_side),
        "dominant_mode": str(dominant_mode),
        "buy_persistence": float(buy_persistence),
        "sell_persistence": float(sell_persistence),
        "active_persistence": float(active_persistence),
        "buy_streak": int(buy_streak),
        "sell_streak": int(sell_streak),
        "active_streak": int(active_streak),
        "belief_spread": float(belief_spread),
        "spread_abs": float(spread_abs),
        "dominance_deadband": float(dominance_deadband),
        "spread_clear": bool(spread_clear),
        "spread_deadband": bool(spread_deadband),
        "persistence_low": bool(persistence_low),
        "persistence_high": bool(persistence_high),
        "prefer_confirm_release": bool(prefer_confirm_release),
        "prefer_wait_lock": bool(prefer_wait_lock),
        "wait_soft_mult": float(_clamp(wait_soft_mult, 0.88, 1.18)),
        "wait_hard_mult": float(_clamp(wait_hard_mult, 0.84, 1.22)),
        "enter_value_delta": float(enter_value_delta),
        "wait_value_delta": float(wait_value_delta),
    }
