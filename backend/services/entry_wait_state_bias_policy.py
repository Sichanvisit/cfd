"""Shared entry wait state-bias policy helpers."""

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


def _upper(value: object) -> str:
    return str(value or "").strip().upper()


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def resolve_entry_wait_state_bias_v1(
    *,
    state_vector_v2: Mapping[str, Any] | None = None,
    state_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state_vector = _as_mapping(state_vector_v2)
    state_meta = _as_mapping(state_metadata)
    if not state_vector:
        return {
            "wait_soft_mult": 1.0,
            "wait_hard_mult": 1.0,
            "prefer_confirm_release": False,
            "prefer_wait_lock": False,
            "topdown_state_label": "",
            "quality_state_label": "",
            "patience_state_label": "",
            "execution_friction_state": "",
            "event_risk_state": "",
        }

    confirm_gain = _to_float(state_vector.get("confirm_aggression_gain", 1.0), 1.0)
    wait_gain = _to_float(state_vector.get("wait_patience_gain", 1.0), 1.0)
    fast_exit_risk = _to_float(state_vector.get("fast_exit_risk_penalty", 0.0), 0.0)
    topdown_state_label = _upper(state_meta.get("topdown_state_label", ""))
    quality_state_label = _upper(state_meta.get("quality_state_label", ""))
    patience_state_label = _upper(state_meta.get("patience_state_label", ""))
    execution_friction_state = _upper(state_meta.get("execution_friction_state", ""))
    event_risk_state = _upper(state_meta.get("event_risk_state", ""))
    session_regime_state = _upper(state_meta.get("session_regime_state", ""))

    wait_soft_mult = 1.0 + ((confirm_gain - 1.0) * 0.42) - ((wait_gain - 1.0) * 0.32)
    wait_hard_mult = 1.0 + ((confirm_gain - 1.0) * 0.48) - ((wait_gain - 1.0) * 0.35)

    if quality_state_label == "HIGH_QUALITY":
        wait_soft_mult += 0.06
        wait_hard_mult += 0.08
    elif quality_state_label == "LOW_QUALITY":
        wait_soft_mult -= 0.06
        wait_hard_mult -= 0.08

    if patience_state_label == "WAIT_FAVOR":
        wait_soft_mult -= 0.08
        wait_hard_mult -= 0.10
    elif patience_state_label == "CONFIRM_FAVOR":
        wait_soft_mult += 0.08
        wait_hard_mult += 0.10

    if execution_friction_state == "HIGH_FRICTION":
        wait_soft_mult -= 0.10
        wait_hard_mult -= 0.12
    elif execution_friction_state == "MEDIUM_FRICTION":
        wait_soft_mult -= 0.04
        wait_hard_mult -= 0.05

    if event_risk_state == "HIGH_EVENT_RISK":
        wait_soft_mult -= 0.12
        wait_hard_mult -= 0.14
    elif event_risk_state == "WATCH_EVENT_RISK":
        wait_soft_mult -= 0.05
        wait_hard_mult -= 0.06

    if session_regime_state == "SESSION_EDGE_ROTATION":
        wait_soft_mult += 0.05
        wait_hard_mult += 0.06

    wait_soft_mult = _to_float(_clamp(wait_soft_mult - (fast_exit_risk * 0.04), 0.78, 1.24), 1.0)
    wait_hard_mult = _to_float(_clamp(wait_hard_mult - (fast_exit_risk * 0.06), 0.74, 1.28), 1.0)
    prefer_confirm_release = bool(
        confirm_gain >= 1.04
        and patience_state_label in {"CONFIRM_FAVOR", "HOLD_FAVOR"}
        and quality_state_label != "LOW_QUALITY"
        and execution_friction_state != "HIGH_FRICTION"
        and event_risk_state not in {"HIGH_EVENT_RISK", "WATCH_EVENT_RISK"}
    )
    prefer_wait_lock = bool(
        wait_gain >= 1.08
        or patience_state_label == "WAIT_FAVOR"
        or execution_friction_state == "HIGH_FRICTION"
        or event_risk_state == "HIGH_EVENT_RISK"
    )
    return {
        "wait_soft_mult": float(wait_soft_mult),
        "wait_hard_mult": float(wait_hard_mult),
        "prefer_confirm_release": bool(prefer_confirm_release),
        "prefer_wait_lock": bool(prefer_wait_lock),
        "topdown_state_label": str(topdown_state_label),
        "quality_state_label": str(quality_state_label),
        "patience_state_label": str(patience_state_label),
        "execution_friction_state": str(execution_friction_state),
        "event_risk_state": str(event_risk_state),
    }
