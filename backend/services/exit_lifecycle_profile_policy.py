"""Lifecycle posture adjustment for exit profiles."""

from __future__ import annotations


def _normalize_profile(value: str, default: str = "neutral") -> str:
    text = str(value or default).strip().lower()
    return text if text else str(default).strip().lower()


def _normalize_state(value: str, default: str = "") -> str:
    text = str(value or default).strip().upper()
    return text if text else str(default).strip().upper()


def apply_exit_lifecycle_profile_v1(
    *,
    base_profile: str,
    regime_name: str,
    current_box_state: str = "",
) -> dict:
    profile = _normalize_profile(base_profile, "neutral") or "neutral"
    regime = _normalize_state(regime_name)
    box_state = _normalize_state(current_box_state)

    adjusted_profile = profile
    applied = False
    reason = "no_change"

    if regime == "RANGE":
        if profile == "hold_then_trail":
            adjusted_profile = "tight_protect"
            applied = True
            reason = "range_hold_then_trail_tighten"
        elif profile == "protect_then_hold" and box_state == "MIDDLE":
            adjusted_profile = "tight_protect"
            applied = True
            reason = "range_middle_protect_then_hold_tighten"

    return {
        "base_profile": str(profile),
        "profile_id": str(adjusted_profile),
        "regime_name": str(regime),
        "current_box_state": str(box_state),
        "applied": bool(applied),
        "reason": str(reason),
    }
