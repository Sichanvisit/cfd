"""Shared entry probe-ready handoff helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ENTRY_HANDOFF_INVALIDATION_BY_ARCHETYPE = {
    "upper_reject_sell": "upper_break_reclaim",
    "upper_break_buy": "breakout_failure",
    "lower_hold_buy": "lower_support_fail",
    "lower_break_sell": "breakdown_failure",
    "mid_reclaim_buy": "mid_relose",
    "mid_lose_sell": "mid_reclaim",
}

ENTRY_HANDOFF_MANAGEMENT_PROFILE_BY_ARCHETYPE = {
    "upper_reject_sell": "reversal_profile",
    "upper_break_buy": "breakout_hold_profile",
    "lower_hold_buy": "support_hold_profile",
    "lower_break_sell": "breakdown_hold_profile",
    "mid_reclaim_buy": "mid_reclaim_fast_exit_profile",
    "mid_lose_sell": "mid_lose_fast_exit_profile",
}


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def resolve_entry_probe_ready_handoff_v1(
    *,
    probe_plan_v1: Mapping[str, Any] | None = None,
    consumer_archetype_id: str = "",
    consumer_invalidation_id: str = "",
    consumer_management_profile_id: str = "",
    default_side_gate_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    probe_plan = _as_mapping(probe_plan_v1)
    default_side_gate = _as_mapping(default_side_gate_v1)
    probe_ready_handoff = bool(
        probe_plan.get("active", False)
        and probe_plan.get("ready_for_entry", False)
    )
    resolved_archetype = str(consumer_archetype_id or "")
    resolved_invalidation = str(consumer_invalidation_id or "")
    resolved_management_profile = str(consumer_management_profile_id or "")
    fallback_archetype = ""

    if probe_ready_handoff:
        fallback_archetype = str(
            resolved_archetype
            or default_side_gate.get("acting_archetype", "")
            or default_side_gate.get("winner_archetype", "")
            or ""
        )
        if not resolved_archetype and fallback_archetype:
            resolved_archetype = fallback_archetype
        if resolved_archetype and not resolved_invalidation:
            resolved_invalidation = str(
                ENTRY_HANDOFF_INVALIDATION_BY_ARCHETYPE.get(str(resolved_archetype or ""), "") or ""
            )
        if resolved_archetype and not resolved_management_profile:
            resolved_management_profile = str(
                ENTRY_HANDOFF_MANAGEMENT_PROFILE_BY_ARCHETYPE.get(str(resolved_archetype or ""), "") or ""
            )

    return {
        "contract_version": "entry_probe_ready_handoff_v1",
        "probe_ready_handoff": bool(probe_ready_handoff),
        "fallback_archetype": str(fallback_archetype),
        "consumer_archetype_id": str(resolved_archetype),
        "consumer_invalidation_id": str(resolved_invalidation),
        "consumer_management_profile_id": str(resolved_management_profile),
    }
