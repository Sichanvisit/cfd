"""Shared entry default-side gate policy helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.symbol_temperament import resolve_archetype_implied_action


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _upper(value: object) -> str:
    return str(value or "").strip().upper()


def _first_directional_value(*values: object) -> str:
    for value in values:
        direction = _upper(value)
        if direction in {"BUY", "SELL"}:
            return direction
    return ""


def resolve_entry_default_side_gate_v1(
    *,
    edge_pair_law_v1: Mapping[str, Any] | None = None,
    consumer_archetype_id: str = "",
    shadow_observe_archetype_id: str = "",
    shadow_action: str = "",
    shadow_side: str = "",
    shadow_reason: str = "",
    shadow_stage: str = "",
    box_state: str = "",
    bb_state: str = "",
    belief_payload: Mapping[str, Any] | None = None,
    barrier_payload: Mapping[str, Any] | None = None,
    forecast_assist_v1: Mapping[str, Any] | None = None,
    observe_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    edge_pair_law = _as_mapping(edge_pair_law_v1)
    belief_state = _as_mapping(belief_payload)
    barrier_state = _as_mapping(barrier_payload)
    forecast_assist = _as_mapping(forecast_assist_v1)
    observe_metadata_local = _as_mapping(observe_metadata)

    context_label = _upper(edge_pair_law.get("context_label", ""))
    winner_side = _upper(edge_pair_law.get("winner_side", ""))
    winner_archetype = str(edge_pair_law.get("winner_archetype", "") or "")
    winner_clear = bool(edge_pair_law.get("winner_clear", False))
    pair_gap = _to_float(edge_pair_law.get("pair_gap", 0.0))
    acting_archetype = (
        str(consumer_archetype_id or "")
        or str(shadow_observe_archetype_id or "")
        or winner_archetype
    )
    acting_archetype_action = resolve_archetype_implied_action(acting_archetype)
    acting_side = _first_directional_value(
        shadow_action,
        shadow_side,
        acting_archetype_action,
        winner_side,
    )

    default_side = ""
    override_side = ""
    required_default_archetype = ""
    required_override_archetype = ""
    allowed_override_archetypes: list[str] = []
    if context_label == "LOWER_EDGE":
        default_side = "BUY"
        override_side = "SELL"
        required_default_archetype = "lower_hold_buy"
        required_override_archetype = "lower_break_sell"
        allowed_override_archetypes = ["lower_break_sell"]
        if _upper(box_state) in {"LOWER", "LOWER_EDGE", "BELOW"} and _upper(bb_state) in {
            "UPPER",
            "UPPER_EDGE",
            "ABOVE",
        }:
            allowed_override_archetypes.append("upper_reject_sell")
    elif context_label == "UPPER_EDGE":
        default_side = "SELL"
        override_side = "BUY"
        required_default_archetype = "upper_reject_sell"
        required_override_archetype = "upper_break_buy"
        allowed_override_archetypes = ["upper_break_buy"]
    if (
        context_label == "LOWER_EDGE"
        and acting_archetype == "upper_reject_sell"
        and _upper(box_state) in {"LOWER", "LOWER_EDGE", "BELOW"}
    ):
        if "upper_reject_sell" not in allowed_override_archetypes:
            allowed_override_archetypes.append("upper_reject_sell")

    same_side_belief = _to_float(
        belief_state.get("buy_belief" if acting_side == "BUY" else "sell_belief", 0.0)
    )
    same_side_persistence = _to_float(
        belief_state.get("buy_persistence" if acting_side == "BUY" else "sell_persistence", 0.0)
    )
    same_side_streak = _to_int(
        belief_state.get("buy_streak" if acting_side == "BUY" else "sell_streak", 0)
    )
    dominant_side = _upper(belief_state.get("dominant_side", ""))
    dominant_mode = str(belief_state.get("dominant_mode", "") or "").lower()
    same_side_barrier = _to_float(
        barrier_state.get("buy_barrier" if acting_side == "BUY" else "sell_barrier", 0.0)
    )

    action_confirm_score = _to_float(forecast_assist.get("action_confirm_score", 0.0))
    confirm_fake_gap = _to_float(forecast_assist.get("confirm_fake_gap", 0.0))
    wait_confirm_gap = _to_float(forecast_assist.get("wait_confirm_gap", 0.0))
    continue_fail_gap = _to_float(forecast_assist.get("continue_fail_gap", 0.0))

    acting_against_default = bool(
        context_label in {"LOWER_EDGE", "UPPER_EDGE"}
        and acting_side in {"BUY", "SELL"}
        and acting_side == override_side
    )
    conflict_local_upper_override = bool(
        context_label == "LOWER_EDGE"
        and acting_side == "SELL"
        and acting_archetype == "upper_reject_sell"
        and str(shadow_reason or "").startswith("upper_reject")
        and _upper(box_state) in {"LOWER", "LOWER_EDGE", "BELOW"}
    )
    branch_match = bool(
        acting_against_default
        and acting_archetype in allowed_override_archetypes
        and (
            (acting_side == winner_side and acting_archetype == winner_archetype)
            or conflict_local_upper_override
        )
    )
    forecast_support = bool(
        action_confirm_score >= 0.55
        and confirm_fake_gap >= 0.08
        and wait_confirm_gap >= 0.03
        and continue_fail_gap >= 0.02
    )
    belief_support = bool(
        (dominant_side == acting_side or same_side_belief >= 0.55)
        and (same_side_persistence >= 0.30 or same_side_streak >= 2)
    )
    barrier_support = bool(same_side_barrier <= 0.45)
    override_package_satisfied = bool(
        acting_against_default
        and winner_clear
        and branch_match
        and forecast_support
        and belief_support
        and barrier_support
    )

    block_reason = ""
    if acting_against_default and not override_package_satisfied:
        block_reason = (
            "upper_edge_buy_requires_break_override"
            if context_label == "UPPER_EDGE"
            else "lower_edge_sell_requires_break_override"
        )
    observe_probe_override_pending = bool(
        _upper(shadow_stage) in {"OBSERVE", "CONFLICT_OBSERVE"}
        and acting_against_default
        and bool(_as_mapping(observe_metadata_local.get("probe_candidate_v1")).get("active", False))
    )
    if observe_probe_override_pending:
        block_reason = ""

    return {
        "contract_version": "entry_default_side_gate_v1",
        "active": bool(context_label in {"LOWER_EDGE", "UPPER_EDGE"}),
        "context_label": str(context_label),
        "default_side": str(default_side),
        "override_side": str(override_side),
        "required_default_archetype": str(required_default_archetype),
        "required_override_archetype": str(required_override_archetype),
        "allowed_override_archetypes": list(allowed_override_archetypes),
        "acting_side": str(acting_side),
        "acting_archetype": str(acting_archetype),
        "acting_archetype_action": str(acting_archetype_action),
        "winner_side": str(winner_side),
        "winner_archetype": str(winner_archetype),
        "winner_clear": bool(winner_clear),
        "pair_gap": float(pair_gap),
        "acting_against_default": bool(acting_against_default),
        "conflict_local_upper_override": bool(conflict_local_upper_override),
        "same_side_belief": float(same_side_belief),
        "same_side_persistence": float(same_side_persistence),
        "same_side_streak": int(same_side_streak),
        "dominant_side": str(dominant_side),
        "dominant_mode": str(dominant_mode),
        "same_side_barrier": float(same_side_barrier),
        "action_confirm_score": float(action_confirm_score),
        "confirm_fake_gap": float(confirm_fake_gap),
        "wait_confirm_gap": float(wait_confirm_gap),
        "continue_fail_gap": float(continue_fail_gap),
        "branch_match": bool(branch_match),
        "forecast_support": bool(forecast_support),
        "belief_support": bool(belief_support),
        "barrier_support": bool(barrier_support),
        "override_package_satisfied": bool(override_package_satisfied),
        "observe_probe_override_pending": bool(observe_probe_override_pending),
        "blocked": bool(bool(block_reason)),
        "reason": str(block_reason),
    }
