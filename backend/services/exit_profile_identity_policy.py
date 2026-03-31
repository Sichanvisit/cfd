"""Canonical exit profile identity resolution."""

from __future__ import annotations


def _normalize(value: str, default: str = "") -> str:
    text = str(value or default).strip().lower()
    return text if text else str(default).strip().lower()


def resolve_exit_profile_identity_v1(
    *,
    management_profile_id: str = "",
    invalidation_id: str = "",
    entry_setup_id: str = "",
    fallback_profile: str = "neutral",
) -> dict:
    management_profile = _normalize(management_profile_id)
    invalidation = _normalize(invalidation_id)
    setup_id = _normalize(entry_setup_id)
    fallback = _normalize(fallback_profile, "neutral") or "neutral"

    profile_id = fallback
    source = "fallback"

    if management_profile == "reversal_profile":
        profile_id = "tight_protect"
        source = "management_profile"
    elif management_profile == "breakout_hold_profile":
        profile_id = "hold_then_trail"
        source = "management_profile"
    elif management_profile == "support_hold_profile":
        profile_id = "tight_protect"
        source = "management_profile"
    elif management_profile == "breakdown_hold_profile":
        profile_id = "hold_then_trail"
        source = "management_profile"
    elif management_profile in {"mid_reclaim_fast_exit_profile", "mid_lose_fast_exit_profile"}:
        profile_id = "tight_protect"
        source = "management_profile"
    elif invalidation in {"breakout_failure", "breakdown_failure"}:
        profile_id = "hold_then_trail"
        source = "invalidation"
    elif invalidation in {"upper_break_reclaim", "lower_support_fail", "mid_relose", "mid_reclaim"}:
        profile_id = "tight_protect"
        source = "invalidation"
    elif setup_id in {"range_lower_reversal_buy", "range_upper_reversal_sell"}:
        profile_id = "tight_protect"
        source = "entry_setup"
    elif setup_id in {"trend_pullback_buy", "trend_pullback_sell"}:
        profile_id = "protect_then_hold"
        source = "entry_setup"
    elif setup_id in {"breakout_retest_buy", "breakout_retest_sell"}:
        profile_id = "hold_then_trail"
        source = "entry_setup"

    return {
        "profile_id": str(profile_id),
        "source": str(source),
        "management_profile_id": str(management_profile),
        "invalidation_id": str(invalidation),
        "entry_setup_id": str(setup_id),
        "fallback_profile": str(fallback),
    }
