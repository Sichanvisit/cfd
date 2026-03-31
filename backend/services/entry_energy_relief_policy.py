"""Shared entry energy soft-block relief policy helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DEFAULT_ENTRY_PROBE_MIN_ENERGY_READY = 0.48
DEFAULT_ENTRY_PROBE_MIN_CORE_SCORE = 0.52


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


def _lower(value: object) -> str:
    return str(value or "").strip().lower()


def resolve_entry_energy_soft_block_policy_v1(
    *,
    symbol: str = "",
    shadow_action: str = "",
    shadow_reason: str = "",
    consumer_archetype_id: str = "",
    box_state: str = "",
    bb_state: str = "",
    default_side_gate_v1: Mapping[str, Any] | None = None,
    probe_plan_v1: Mapping[str, Any] | None = None,
    observe_metadata: Mapping[str, Any] | None = None,
    forecast_assist_v1: Mapping[str, Any] | None = None,
    energy_soft_block_active: bool = False,
    energy_soft_block_reason: str = "",
    energy_soft_block_strength: float = 0.0,
    energy_action_readiness: float = 0.0,
    effective_priority_rank: int = 0,
    adjusted_core_score: float = 0.0,
    probe_energy_ready_default: float = DEFAULT_ENTRY_PROBE_MIN_ENERGY_READY,
    probe_core_score_default: float = DEFAULT_ENTRY_PROBE_MIN_CORE_SCORE,
) -> dict[str, Any]:
    default_side_gate = _as_mapping(default_side_gate_v1)
    probe_plan = _as_mapping(probe_plan_v1)
    observe_metadata_local = _as_mapping(observe_metadata)
    forecast_assist = _as_mapping(forecast_assist_v1)
    probe_temperament_v1 = _as_mapping(probe_plan.get("symbol_probe_temperament_v1"))
    forecast_upper_reject_relief = _as_mapping(
        observe_metadata_local.get("forecast_upper_reject_relief_v1")
    )

    probe_energy_ready_min = _to_float(
        probe_temperament_v1.get("min_energy_ready", probe_energy_ready_default),
        default=probe_energy_ready_default,
    )
    probe_core_score_min = _to_float(
        probe_temperament_v1.get("min_core_score", probe_core_score_default),
        default=probe_core_score_default,
    )
    priority_override_relief_applied = bool(
        _to_int(effective_priority_rank) >= 2
        and _to_float(energy_action_readiness) >= 0.60
        and _to_float(adjusted_core_score) >= 0.60
    )
    probe_energy_relief = bool(
        bool(probe_plan.get("ready_for_entry", False))
        and bool(probe_plan.get("energy_relief_allowed", False))
        and _to_int(effective_priority_rank) >= 1
        and _to_float(energy_action_readiness) >= probe_energy_ready_min
        and _to_float(adjusted_core_score) >= probe_core_score_min
    )
    confirm_energy_relief_local_ready = bool(
        _to_float(forecast_assist.get("action_confirm_score", 0.0)) >= 0.17
        and _to_float(forecast_assist.get("wait_confirm_gap", 0.0)) >= -0.20
        and _to_float(forecast_assist.get("continue_fail_gap", 0.0)) >= -0.22
    )
    confirm_energy_relief = bool(
        _upper(shadow_action) == "SELL"
        and str(shadow_reason or "") in {"upper_reject_confirm", "upper_break_fail_confirm"}
        and _upper(box_state) in {"UPPER", "ABOVE"}
        and _upper(bb_state) in {"UPPER_EDGE", "BREAKOUT"}
        and _upper(default_side_gate.get("context_label", "")) == "UPPER_EDGE"
        and not bool(default_side_gate.get("acting_against_default", False))
        and (
            bool(forecast_upper_reject_relief.get("applied", False))
            or confirm_energy_relief_local_ready
        )
        and str(energy_soft_block_reason or "") in {"forecast_gap_wait_bias", "forecast_wait_bias"}
        and _to_float(adjusted_core_score) >= 0.70
        and _to_float(default_side_gate.get("same_side_barrier", 1.0), default=1.0) <= 0.35
    )
    xau_second_support_energy_relief = bool(
        _upper(symbol) == "XAUUSD"
        and bool(probe_plan.get("ready_for_entry", False))
        and str(probe_plan.get("symbol_scene_relief", "") or "") == "xau_second_support_buy_probe"
        and _upper(probe_plan.get("intended_action", "")) == "BUY"
        and _upper(box_state) in {"LOWER", "LOWER_EDGE", "BELOW"}
        and _upper(bb_state) in {"MID", "MIDDLE", "LOWER", "LOWER_EDGE", "BREAKDOWN"}
        and str(energy_soft_block_reason or "")
        in {"forecast_gap_wait_bias", "forecast_wait_bias", "barrier_soft_block"}
        and _to_float(energy_soft_block_strength) <= 0.85
        and _to_float(probe_plan.get("candidate_support", 0.0)) >= 0.44
        and _to_float(probe_plan.get("pair_gap", 0.0)) >= 0.18
        and _to_float(probe_plan.get("same_side_barrier", 1.0), default=1.0) <= 0.90
    )
    xau_upper_sell_probe_energy_relief = bool(
        _upper(symbol) == "XAUUSD"
        and bool(probe_plan.get("ready_for_entry", False))
        and str(probe_plan.get("symbol_scene_relief", "") or "") == "xau_upper_sell_probe"
        and _upper(probe_plan.get("intended_action", "")) == "SELL"
        and _upper(box_state) in {"UPPER", "UPPER_EDGE", "ABOVE"}
        and _upper(bb_state) in {"MID", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT", "UNKNOWN"}
        and str(energy_soft_block_reason or "") in {"forecast_gap_wait_bias", "forecast_wait_bias"}
        and _to_float(energy_soft_block_strength) <= 0.45
        and _to_float(probe_plan.get("candidate_support", 0.0)) >= 0.16
        and _to_float(probe_plan.get("pair_gap", 0.0)) >= 0.08
        and _to_float(probe_plan.get("action_confirm_score", 0.0)) >= 0.13
        and _to_float(probe_plan.get("wait_confirm_gap", 0.0)) >= -0.14
        and _to_float(probe_plan.get("continue_fail_gap", 0.0)) >= -0.30
        and _to_float(probe_plan.get("same_side_barrier", 1.0), default=1.0) <= 0.66
    )
    xau_upper_mixed_confirm_energy_relief = bool(
        _upper(symbol) == "XAUUSD"
        and _upper(shadow_action) == "SELL"
        and str(shadow_reason or "") == "upper_reject_mixed_confirm"
        and _lower(consumer_archetype_id or default_side_gate.get("acting_archetype", "")) == "upper_reject_sell"
        and _upper(default_side_gate.get("default_side", "")) == "SELL"
        and _upper(default_side_gate.get("context_label", "")) == "UPPER_EDGE"
        and _upper(box_state) in {"MIDDLE", "UPPER", "ABOVE"}
        and _upper(bb_state) in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
        and str(energy_soft_block_reason or "") in {"forecast_gap_wait_bias", "forecast_wait_bias"}
        and _to_float(energy_soft_block_strength) <= 0.75
        and _to_float(adjusted_core_score) >= 0.46
        and _to_float(default_side_gate.get("same_side_barrier", 1.0), default=1.0) <= 0.45
        and (
            bool(forecast_upper_reject_relief.get("applied", False))
            or confirm_energy_relief_local_ready
            or _to_float(forecast_assist.get("action_confirm_score", 0.0)) >= 0.12
        )
    )
    relief_flags = [
        label
        for label, active in (
            ("probe_energy_relief", probe_energy_relief),
            ("confirm_energy_relief", confirm_energy_relief),
            ("xau_second_support_energy_relief", xau_second_support_energy_relief),
            ("xau_upper_sell_probe_energy_relief", xau_upper_sell_probe_energy_relief),
            ("xau_upper_mixed_confirm_energy_relief", xau_upper_mixed_confirm_energy_relief),
        )
        if bool(active)
    ]
    energy_soft_block_should_block = bool(
        bool(energy_soft_block_active)
        and not (
            priority_override_relief_applied
            or probe_energy_relief
            or confirm_energy_relief
            or xau_second_support_energy_relief
            or xau_upper_sell_probe_energy_relief
            or xau_upper_mixed_confirm_energy_relief
        )
    )
    return {
        "contract_version": "entry_energy_soft_block_policy_v1",
        "probe_energy_ready_min": float(probe_energy_ready_min),
        "probe_core_score_min": float(probe_core_score_min),
        "priority_override_relief_applied": bool(priority_override_relief_applied),
        "probe_energy_relief": bool(probe_energy_relief),
        "confirm_energy_relief_local_ready": bool(confirm_energy_relief_local_ready),
        "confirm_energy_relief": bool(confirm_energy_relief),
        "xau_second_support_energy_relief": bool(xau_second_support_energy_relief),
        "xau_upper_sell_probe_energy_relief": bool(xau_upper_sell_probe_energy_relief),
        "xau_upper_mixed_confirm_energy_relief": bool(xau_upper_mixed_confirm_energy_relief),
        "relief_flags": relief_flags,
        "energy_soft_block_should_block": bool(energy_soft_block_should_block),
    }
