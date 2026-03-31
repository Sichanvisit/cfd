"""Shared entry probe-plan policy helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from backend.services.symbol_temperament import resolve_probe_plan_temperament


DEFAULT_ENTRY_PROBE_MIN_CONFIRM_FAKE_GAP = 0.03
DEFAULT_ENTRY_PROBE_MIN_CONTINUE_FAIL_GAP = -0.01
DEFAULT_ENTRY_PROBE_MIN_PERSISTENCE = 0.18
DEFAULT_ENTRY_PROBE_MIN_BELIEF = 0.52
DEFAULT_ENTRY_PROBE_MAX_SIDE_BARRIER = 0.42
DEFAULT_ENTRY_PROBE_MIN_PAIR_GAP = 0.12
DEFAULT_ENTRY_PROBE_MIN_CANDIDATE_SUPPORT = 0.30
DEFAULT_ENTRY_PROBE_MIN_ACTION_CONFIRM_SCORE = 0.22
DEFAULT_ENTRY_PROBE_MIN_STREAK = 1
DEFAULT_ENTRY_PROBE_SIZE_MULT = 0.50
DEFAULT_ENTRY_PROBE_ENTRY_STAGE = "conservative"
DEFAULT_ENTRY_CONFIRM_ADD_SIZE_MULT = 1.00


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


def _first_directional_value(*values: object) -> str:
    for value in values:
        direction = _upper(value)
        if direction in {"BUY", "SELL"}:
            return direction
    return ""


def resolve_entry_probe_plan_v1(
    *,
    symbol: str = "",
    shadow_action: str = "",
    shadow_side: str = "",
    shadow_stage: str = "",
    box_state: str = "",
    bb_state: str = "",
    observe_metadata: Mapping[str, Any] | None = None,
    default_side_gate_v1: Mapping[str, Any] | None = None,
    min_confirm_fake_gap_default: float = DEFAULT_ENTRY_PROBE_MIN_CONFIRM_FAKE_GAP,
    min_continue_fail_gap_default: float = DEFAULT_ENTRY_PROBE_MIN_CONTINUE_FAIL_GAP,
    min_persistence_default: float = DEFAULT_ENTRY_PROBE_MIN_PERSISTENCE,
    min_belief_default: float = DEFAULT_ENTRY_PROBE_MIN_BELIEF,
    max_side_barrier_default: float = DEFAULT_ENTRY_PROBE_MAX_SIDE_BARRIER,
    min_pair_gap_default: float = DEFAULT_ENTRY_PROBE_MIN_PAIR_GAP,
    min_candidate_support_default: float = DEFAULT_ENTRY_PROBE_MIN_CANDIDATE_SUPPORT,
    min_action_confirm_score_default: float = DEFAULT_ENTRY_PROBE_MIN_ACTION_CONFIRM_SCORE,
    min_streak_default: int = DEFAULT_ENTRY_PROBE_MIN_STREAK,
    recommended_size_multiplier_default: float = DEFAULT_ENTRY_PROBE_SIZE_MULT,
    recommended_entry_stage_default: str = DEFAULT_ENTRY_PROBE_ENTRY_STAGE,
    confirm_add_size_multiplier_default: float = DEFAULT_ENTRY_CONFIRM_ADD_SIZE_MULT,
) -> dict[str, Any]:
    observe_metadata_local = _as_mapping(observe_metadata)
    default_side_gate = _as_mapping(default_side_gate_v1)
    probe_candidate = _as_mapping(observe_metadata_local.get("probe_candidate_v1"))
    probe_direction = _upper(probe_candidate.get("probe_direction", ""))
    candidate_side_hint = _first_directional_value(
        shadow_action,
        shadow_side,
        probe_direction,
        default_side_gate.get("acting_archetype_action", ""),
        default_side_gate.get("winner_side", ""),
    )
    intended_action = (
        probe_direction
        if probe_direction in {"BUY", "SELL"}
        else candidate_side_hint
        if candidate_side_hint in {"BUY", "SELL"}
        else ""
    )
    active = bool(
        _upper(shadow_stage) in {"OBSERVE", "CONFLICT_OBSERVE"}
        and probe_candidate.get("active", False)
        and intended_action in {"BUY", "SELL"}
    )
    if not active:
        inactive_reason = ""
        if not bool(probe_candidate.get("active", False)):
            inactive_reason = "probe_candidate_inactive"
        elif _upper(shadow_stage) not in {"OBSERVE", "CONFLICT_OBSERVE"}:
            inactive_reason = "probe_not_observe_stage"
        elif intended_action not in {"BUY", "SELL"}:
            inactive_reason = "probe_action_unresolved"
        return {
            "contract_version": "entry_probe_plan_v1",
            "active": False,
            "ready_for_entry": False,
            "reason": str(inactive_reason),
            "intended_action": str(intended_action),
            "trigger_branch": str(probe_candidate.get("trigger_branch", "") or ""),
        }

    probe_temperament = resolve_probe_plan_temperament(
        symbol=str(symbol or ""),
        intended_action=str(intended_action),
        trigger_branch=str(probe_candidate.get("trigger_branch", "") or ""),
        probe_candidate=probe_candidate,
        observe_metadata=observe_metadata_local,
    )
    winner_side = _upper(default_side_gate.get("winner_side", ""))
    default_side = _upper(default_side_gate.get("default_side", ""))
    side_match = bool(
        intended_action == candidate_side_hint
        or (winner_side in {"BUY", "SELL"} and intended_action == winner_side)
        or (
            default_side in {"BUY", "SELL"}
            and intended_action == default_side
            and not bool(default_side_gate.get("acting_against_default", False))
        )
    )
    default_side_aligned = not bool(default_side_gate.get("acting_against_default", False))
    confirm_fake_gap = _to_float(default_side_gate.get("confirm_fake_gap", 0.0))
    wait_confirm_gap = _to_float(default_side_gate.get("wait_confirm_gap", 0.0))
    continue_fail_gap = _to_float(default_side_gate.get("continue_fail_gap", 0.0))
    action_confirm_score = _to_float(default_side_gate.get("action_confirm_score", 0.0))
    same_side_persistence = _to_float(default_side_gate.get("same_side_persistence", 0.0))
    same_side_belief = _to_float(default_side_gate.get("same_side_belief", 0.0))
    same_side_streak = _to_int(default_side_gate.get("same_side_streak", 0))
    dominant_side = _upper(default_side_gate.get("dominant_side", ""))
    dominant_mode = str(default_side_gate.get("dominant_mode", "") or "").lower()
    pair_gap = _to_float(default_side_gate.get("pair_gap", 0.0))
    same_side_barrier = _to_float(default_side_gate.get("same_side_barrier", 0.0))
    candidate_support = _to_float(probe_candidate.get("candidate_support", 0.0))
    near_confirm = bool(probe_candidate.get("near_confirm", False))
    min_confirm_fake_gap = _to_float(
        probe_temperament.get("min_confirm_fake_gap", min_confirm_fake_gap_default),
        default=min_confirm_fake_gap_default,
    )
    min_continue_fail_gap = _to_float(
        probe_temperament.get("min_continue_fail_gap", min_continue_fail_gap_default),
        default=min_continue_fail_gap_default,
    )
    min_persistence = _to_float(
        probe_temperament.get("min_persistence", min_persistence_default),
        default=min_persistence_default,
    )
    min_belief = _to_float(
        probe_temperament.get("min_belief", min_belief_default),
        default=min_belief_default,
    )
    min_pair_gap = _to_float(
        probe_temperament.get("min_pair_gap", min_pair_gap_default),
        default=min_pair_gap_default,
    )
    min_candidate_support = _to_float(
        probe_temperament.get("min_candidate_support", min_candidate_support_default),
        default=min_candidate_support_default,
    )
    min_action_confirm_score = _to_float(
        probe_temperament.get("min_action_confirm_score", min_action_confirm_score_default),
        default=min_action_confirm_score_default,
    )
    min_streak = _to_int(probe_temperament.get("min_streak", min_streak_default), default=min_streak_default)
    max_side_barrier = _to_float(
        probe_temperament.get("max_side_barrier", max_side_barrier_default),
        default=max_side_barrier_default,
    )
    near_confirm_pair_gap = _to_float(probe_temperament.get("near_confirm_pair_gap", min_pair_gap), default=min_pair_gap)
    symbol_scene_relief = str(probe_temperament.get("scene_id", "") or "")

    explicit_probe_side = bool(_upper(shadow_action) in {"BUY", "SELL"} and _upper(shadow_action) == intended_action)
    pair_support = bool(
        explicit_probe_side
        or pair_gap >= min_pair_gap
        or candidate_support >= min_candidate_support
        or (near_confirm and pair_gap >= near_confirm_pair_gap)
    )
    forecast_support = bool(
        (
            confirm_fake_gap >= min_confirm_fake_gap
            and continue_fail_gap >= min_continue_fail_gap
        )
        or (
            wait_confirm_gap >= -0.01
            and action_confirm_score >= min_action_confirm_score
            and continue_fail_gap >= (min_continue_fail_gap - 0.12)
        )
    )
    belief_support = bool(
        same_side_persistence >= min_persistence
        or same_side_belief >= min_belief
        or same_side_streak >= min_streak
        or (
            dominant_side == intended_action
            and dominant_mode in {"reversal", "continuation"}
            and pair_gap >= max(0.14, min_pair_gap)
        )
    )
    barrier_support = bool(same_side_barrier <= max_side_barrier)
    structural_relief_active = bool(probe_temperament.get("structural_relief_active", False))
    structural_relief_candidate_support = _to_float(probe_temperament.get("structural_relief_candidate_support", 0.0))
    structural_relief_pair_gap = _to_float(
        probe_temperament.get("structural_relief_pair_gap", min_pair_gap),
        default=min_pair_gap,
    )
    structural_relief_action_confirm_score = _to_float(
        probe_temperament.get("structural_relief_action_confirm_score", min_action_confirm_score),
        default=min_action_confirm_score,
    )
    structural_relief_confirm_fake_gap = _to_float(
        probe_temperament.get("structural_relief_confirm_fake_gap", min_confirm_fake_gap),
        default=min_confirm_fake_gap,
    )
    structural_relief_wait_confirm_gap = _to_float(
        probe_temperament.get("structural_relief_wait_confirm_gap", -0.01),
        default=-0.01,
    )
    structural_relief_continue_fail_gap = _to_float(
        probe_temperament.get("structural_relief_continue_fail_gap", min_continue_fail_gap),
        default=min_continue_fail_gap,
    )
    structural_relief_belief = _to_float(
        probe_temperament.get("structural_relief_belief", min_belief),
        default=min_belief,
    )
    structural_relief_persistence = _to_float(
        probe_temperament.get("structural_relief_persistence", min_persistence),
        default=min_persistence,
    )
    structural_relief_max_side_barrier = _to_float(
        probe_temperament.get("structural_relief_max_side_barrier", max_side_barrier),
        default=max_side_barrier,
    )
    structural_relief_pair_support = bool(
        candidate_support >= structural_relief_candidate_support
        and pair_gap >= structural_relief_pair_gap
    )
    structural_relief_forecast_support = bool(
        action_confirm_score >= structural_relief_action_confirm_score
        and confirm_fake_gap >= structural_relief_confirm_fake_gap
        and wait_confirm_gap >= structural_relief_wait_confirm_gap
        and continue_fail_gap >= structural_relief_continue_fail_gap
    )
    structural_relief_belief_support = bool(
        same_side_belief >= structural_relief_belief
        or same_side_persistence >= structural_relief_persistence
        or same_side_streak >= 1
        or dominant_side == intended_action
    )
    structural_relief_barrier_support = bool(
        same_side_barrier <= structural_relief_max_side_barrier
    )
    structural_relief_applied = bool(
        structural_relief_active
        and active
        and side_match
        and default_side_aligned
        and structural_relief_pair_support
        and structural_relief_forecast_support
        and structural_relief_belief_support
        and structural_relief_barrier_support
    )
    if structural_relief_applied:
        pair_support = True
        forecast_support = True
        belief_support = True
        barrier_support = True

    xau_second_support_forecast_relief = bool(
        _upper(symbol) == "XAUUSD"
        and active
        and side_match
        and default_side_aligned
        and str(symbol_scene_relief or "") == "xau_second_support_buy_probe"
        and intended_action == "BUY"
        and _upper(box_state) in {"LOWER", "LOWER_EDGE", "BELOW"}
        and _upper(bb_state) in {"MID", "MIDDLE", "LOWER", "LOWER_EDGE", "BREAKDOWN"}
        and candidate_support >= 0.44
        and pair_gap >= 0.18
        and action_confirm_score >= 0.07
        and confirm_fake_gap >= -0.27
        and wait_confirm_gap >= -0.23
        and continue_fail_gap >= -0.30
        and (
            same_side_belief >= 0.015
            or same_side_streak >= 1
            or dominant_side == intended_action
        )
    )
    if xau_second_support_forecast_relief:
        forecast_support = True

    ready_for_entry = bool(
        active
        and side_match
        and default_side_aligned
        and pair_support
        and forecast_support
        and belief_support
        and barrier_support
    )
    reason = ""
    if active and not side_match:
        reason = "probe_side_mismatch"
    elif active and not default_side_aligned:
        reason = "probe_against_default_side"
    elif active and not pair_support:
        reason = "probe_pair_gap_not_ready"
    elif active and not forecast_support:
        reason = "probe_forecast_not_ready"
    elif active and not belief_support:
        reason = "probe_belief_not_ready"
    elif active and not barrier_support:
        reason = "probe_barrier_blocked"

    return {
        "contract_version": "entry_probe_plan_v1",
        "active": bool(active),
        "ready_for_entry": bool(ready_for_entry),
        "reason": str(reason),
        "intended_action": str(intended_action),
        "trigger_branch": str(probe_candidate.get("trigger_branch", "") or ""),
        "probe_kind": str(probe_candidate.get("probe_kind", "") or ""),
        "candidate_side_hint": str(candidate_side_hint),
        "explicit_probe_side": bool(explicit_probe_side),
        "default_side_aligned": bool(default_side_aligned),
        "pair_support": bool(pair_support),
        "forecast_support": bool(forecast_support),
        "belief_support": bool(belief_support),
        "barrier_support": bool(barrier_support),
        "action_confirm_score": float(action_confirm_score),
        "confirm_fake_gap": float(confirm_fake_gap),
        "wait_confirm_gap": float(wait_confirm_gap),
        "continue_fail_gap": float(continue_fail_gap),
        "pair_gap": float(pair_gap),
        "candidate_support": float(candidate_support),
        "near_confirm": bool(near_confirm),
        "same_side_persistence": float(same_side_persistence),
        "same_side_belief": float(same_side_belief),
        "same_side_streak": int(same_side_streak),
        "dominant_side": str(dominant_side),
        "dominant_mode": str(dominant_mode),
        "same_side_barrier": float(same_side_barrier),
        "structural_relief_active": bool(structural_relief_active),
        "structural_relief_applied": bool(structural_relief_applied),
        "xau_second_support_forecast_relief": bool(xau_second_support_forecast_relief),
        "structural_relief_pair_support": bool(structural_relief_pair_support),
        "structural_relief_forecast_support": bool(structural_relief_forecast_support),
        "structural_relief_belief_support": bool(structural_relief_belief_support),
        "structural_relief_barrier_support": bool(structural_relief_barrier_support),
        "structural_relief_candidate_support": float(structural_relief_candidate_support),
        "structural_relief_pair_gap": float(structural_relief_pair_gap),
        "structural_relief_action_confirm_score": float(structural_relief_action_confirm_score),
        "structural_relief_confirm_fake_gap": float(structural_relief_confirm_fake_gap),
        "structural_relief_wait_confirm_gap": float(structural_relief_wait_confirm_gap),
        "structural_relief_continue_fail_gap": float(structural_relief_continue_fail_gap),
        "structural_relief_belief": float(structural_relief_belief),
        "structural_relief_persistence": float(structural_relief_persistence),
        "structural_relief_max_side_barrier": float(structural_relief_max_side_barrier),
        "symbol_scene_relief": str(symbol_scene_relief),
        "symbol_probe_temperament_v1": dict(probe_temperament),
        "energy_relief_allowed": bool(
            ready_for_entry
            and default_side_aligned
            and bool(probe_temperament.get("allow_energy_relief", True))
        ),
        "recommended_size_multiplier": float(
            _to_float(
                probe_temperament.get("recommended_size_multiplier", recommended_size_multiplier_default),
                default=recommended_size_multiplier_default,
            )
        ),
        "recommended_entry_stage": str(
            probe_temperament.get("recommended_entry_stage", recommended_entry_stage_default)
            or recommended_entry_stage_default
        ),
        "confirm_add_size_multiplier": float(
            _to_float(
                probe_temperament.get("confirm_add_size_multiplier", confirm_add_size_multiplier_default),
                default=confirm_add_size_multiplier_default,
            )
        ),
        "min_pair_gap": float(min_pair_gap),
        "min_candidate_support": float(min_candidate_support),
        "min_action_confirm_score": float(min_action_confirm_score),
        "max_side_barrier": float(max_side_barrier),
    }
