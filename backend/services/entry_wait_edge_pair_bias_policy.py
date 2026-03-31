"""Shared entry wait edge-pair bias policy helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from backend.services.entry_wait_belief_bias_policy import resolve_entry_wait_acting_side_v1


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


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _upper(value: object, default: str = "") -> str:
    text = str(value or "").strip().upper()
    return text if text else str(default or "").upper()


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def resolve_entry_wait_edge_pair_bias_v1(
    *,
    payload: Mapping[str, Any] | None = None,
    observe_confirm_v2: Mapping[str, Any] | None = None,
    action: str = "",
    core_allowed_action: str = "",
    preflight_allowed_action: str = "",
) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    observe_confirm = _as_mapping(observe_confirm_v2)
    observe_meta = _as_mapping(observe_confirm.get("metadata"))
    edge_pair_law = _as_mapping(
        payload_map.get("edge_pair_law_v1", observe_meta.get("edge_pair_law_v1", {}))
    )
    if not edge_pair_law:
        return {
            "present": False,
            "context_label": "UNRESOLVED",
            "winner_side": "BALANCED",
            "winner_clear": False,
            "pair_gap": 0.0,
            "acting_side": "",
            "prefer_confirm_release": False,
            "prefer_wait_lock": False,
            "wait_soft_mult": 1.0,
            "wait_hard_mult": 1.0,
            "enter_value_delta": 0.0,
            "wait_value_delta": 0.0,
        }

    dominant_side = _upper(edge_pair_law.get("winner_side", "BALANCED"), "BALANCED")
    context_label = _upper(edge_pair_law.get("context_label", "UNRESOLVED"), "UNRESOLVED")
    pair_gap = _to_float(edge_pair_law.get("pair_gap", 0.0), 0.0)
    winner_clear = _to_bool(edge_pair_law.get("winner_clear", False))
    acting_side = resolve_entry_wait_acting_side_v1(
        action=action,
        core_allowed_action=core_allowed_action,
        preflight_allowed_action=preflight_allowed_action,
        dominant_side=dominant_side,
    )

    meaningful_context = context_label in {"LOWER_EDGE", "UPPER_EDGE", "MIDDLE"}
    matching_clear_winner = bool(
        meaningful_context
        and winner_clear
        and acting_side in {"BUY", "SELL"}
        and acting_side == dominant_side
    )
    unresolved_pair = bool(
        meaningful_context and (not winner_clear or dominant_side not in {"BUY", "SELL"} or pair_gap < 0.05)
    )

    wait_soft_mult = 1.0
    wait_hard_mult = 1.0
    enter_value_delta = 0.0
    wait_value_delta = 0.0
    if matching_clear_winner:
        wait_soft_mult += 0.06
        wait_hard_mult += 0.08
        enter_value_delta += 0.16 + min(0.08, max(pair_gap - 0.05, 0.0) * 0.40)
        wait_value_delta -= 0.14
    elif unresolved_pair:
        wait_soft_mult -= 0.05
        wait_hard_mult -= 0.07
        enter_value_delta -= 0.08
        wait_value_delta += 0.14 + max(0.0, 0.06 - pair_gap) * 1.10

    return {
        "present": True,
        "context_label": str(context_label),
        "winner_side": str(dominant_side),
        "winner_clear": bool(winner_clear),
        "pair_gap": float(pair_gap),
        "acting_side": str(acting_side),
        "prefer_confirm_release": bool(matching_clear_winner),
        "prefer_wait_lock": bool(unresolved_pair),
        "wait_soft_mult": float(_clamp(wait_soft_mult, 0.88, 1.16)),
        "wait_hard_mult": float(_clamp(wait_hard_mult, 0.84, 1.20)),
        "enter_value_delta": float(enter_value_delta),
        "wait_value_delta": float(wait_value_delta),
    }
