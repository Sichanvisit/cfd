"""Shared entry-wait bias bundle helpers built from frozen wait context."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from backend.services.entry_wait_belief_bias_policy import resolve_entry_wait_belief_bias_v1
from backend.services.entry_wait_edge_pair_bias_policy import resolve_entry_wait_edge_pair_bias_v1
from backend.services.entry_wait_probe_temperament_policy import resolve_entry_wait_probe_temperament_v1
from backend.services.entry_wait_state_bias_policy import resolve_entry_wait_state_bias_v1


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


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _to_str(item)
        if text:
            items.append(text)
    return items


def apply_entry_wait_threshold_bias_v1(
    *,
    entry_wait_context_v1: Mapping[str, Any] | None = None,
    bias_bundle_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _as_mapping(entry_wait_context_v1)
    bundle = _as_mapping(bias_bundle_v1)
    thresholds = _as_mapping(context.get("thresholds"))

    state_wait_bias = _as_mapping(bundle.get("state_wait_bias_v1"))
    belief_wait_bias = _as_mapping(bundle.get("belief_wait_bias_v1"))
    edge_pair_wait_bias = _as_mapping(bundle.get("edge_pair_wait_bias_v1"))

    base_soft_threshold = _to_float(thresholds.get("base_soft_threshold", 0.0), 0.0)
    base_hard_threshold = _to_float(thresholds.get("base_hard_threshold", 0.0), 0.0)
    soft_multiplier_components = {
        "state": _to_float(state_wait_bias.get("wait_soft_mult", 1.0), 1.0),
        "belief": _to_float(belief_wait_bias.get("wait_soft_mult", 1.0), 1.0),
        "edge_pair": _to_float(edge_pair_wait_bias.get("wait_soft_mult", 1.0), 1.0),
    }
    hard_multiplier_components = {
        "state": _to_float(state_wait_bias.get("wait_hard_mult", 1.0), 1.0),
        "belief": _to_float(belief_wait_bias.get("wait_hard_mult", 1.0), 1.0),
        "edge_pair": _to_float(edge_pair_wait_bias.get("wait_hard_mult", 1.0), 1.0),
    }

    combined_soft_multiplier = 1.0
    for value in soft_multiplier_components.values():
        combined_soft_multiplier *= float(value)
    combined_hard_multiplier = 1.0
    for value in hard_multiplier_components.values():
        combined_hard_multiplier *= float(value)

    effective_soft_threshold = float(base_soft_threshold) * float(combined_soft_multiplier)
    effective_hard_threshold = float(base_hard_threshold) * float(combined_hard_multiplier)

    return {
        "contract_version": "entry_wait_threshold_adjustment_v1",
        "base_soft_threshold": float(base_soft_threshold),
        "base_hard_threshold": float(base_hard_threshold),
        "effective_soft_threshold": float(effective_soft_threshold),
        "effective_hard_threshold": float(effective_hard_threshold),
        "combined_soft_multiplier": float(combined_soft_multiplier),
        "combined_hard_multiplier": float(combined_hard_multiplier),
        "soft_multiplier_components": dict(soft_multiplier_components),
        "hard_multiplier_components": dict(hard_multiplier_components),
    }


def compact_entry_wait_bias_bundle_v1(
    bias_bundle_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = _as_mapping(bias_bundle_v1)
    state_wait_bias = _as_mapping(bundle.get("state_wait_bias_v1"))
    belief_wait_bias = _as_mapping(bundle.get("belief_wait_bias_v1"))
    edge_pair_wait_bias = _as_mapping(bundle.get("edge_pair_wait_bias_v1"))
    symbol_probe_temperament = _as_mapping(bundle.get("symbol_probe_temperament_v1"))
    threshold_adjustment = _as_mapping(bundle.get("threshold_adjustment_v1"))

    active_release_sources: list[str] = []
    active_wait_lock_sources: list[str] = []
    for label, bias in (
        ("state", state_wait_bias),
        ("belief", belief_wait_bias),
        ("edge_pair", edge_pair_wait_bias),
        ("probe", symbol_probe_temperament),
    ):
        if _to_bool(bias.get("prefer_confirm_release", False)):
            active_release_sources.append(label)
        if _to_bool(bias.get("prefer_wait_lock", False)):
            active_wait_lock_sources.append(label)

    return {
        "contract_version": _to_str(bundle.get("contract_version", "entry_wait_bias_bundle_v1")),
        "active_release_sources": list(active_release_sources),
        "active_wait_lock_sources": list(active_wait_lock_sources),
        "release_bias_count": len(active_release_sources),
        "wait_lock_bias_count": len(active_wait_lock_sources),
        "threshold_adjustment": {
            "base_soft_threshold": _to_float(threshold_adjustment.get("base_soft_threshold", 0.0), 0.0),
            "base_hard_threshold": _to_float(threshold_adjustment.get("base_hard_threshold", 0.0), 0.0),
            "effective_soft_threshold": _to_float(
                threshold_adjustment.get("effective_soft_threshold", 0.0),
                0.0,
            ),
            "effective_hard_threshold": _to_float(
                threshold_adjustment.get("effective_hard_threshold", 0.0),
                0.0,
            ),
            "combined_soft_multiplier": _to_float(
                threshold_adjustment.get("combined_soft_multiplier", 1.0),
                1.0,
            ),
            "combined_hard_multiplier": _to_float(
                threshold_adjustment.get("combined_hard_multiplier", 1.0),
                1.0,
            ),
        },
    }


def resolve_entry_wait_bias_bundle_v1(
    entry_wait_context_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _as_mapping(entry_wait_context_v1)
    identity = _as_mapping(context.get("identity"))
    state_inputs = _as_mapping(context.get("state_inputs"))
    belief_inputs = _as_mapping(context.get("belief_inputs"))
    observe_probe = _as_mapping(context.get("observe_probe"))

    action = _to_str(identity.get("action", "")).upper()
    core_allowed_action = _to_str(identity.get("core_allowed_action", "NONE"), "NONE").upper()
    preflight_allowed_action = _to_str(
        identity.get("preflight_allowed_action", "BOTH"),
        "BOTH",
    ).upper()
    helper_payload = {
        "edge_pair_law_v1": dict(_as_mapping(observe_probe.get("edge_pair_law_v1"))),
        "entry_probe_plan_v1": dict(_as_mapping(observe_probe.get("entry_probe_plan_v1"))),
        "probe_candidate_v1": dict(_as_mapping(observe_probe.get("probe_candidate_v1"))),
    }
    observe_confirm_v2 = _as_mapping(observe_probe.get("observe_confirm_v2"))

    state_wait_bias = resolve_entry_wait_state_bias_v1(
        state_vector_v2=_as_mapping(state_inputs.get("state_vector_v2")),
        state_metadata=_as_mapping(state_inputs.get("state_metadata")),
    )
    belief_wait_bias = resolve_entry_wait_belief_bias_v1(
        belief_state_v1=_as_mapping(belief_inputs.get("belief_state_v1")),
        belief_metadata=_as_mapping(belief_inputs.get("belief_metadata")),
        action=action,
        core_allowed_action=core_allowed_action,
        preflight_allowed_action=preflight_allowed_action,
    )
    edge_pair_wait_bias = resolve_entry_wait_edge_pair_bias_v1(
        payload=helper_payload,
        observe_confirm_v2=observe_confirm_v2,
        action=action,
        core_allowed_action=core_allowed_action,
        preflight_allowed_action=preflight_allowed_action,
    )
    symbol_probe_temperament = resolve_entry_wait_probe_temperament_v1(
        payload=helper_payload,
        observe_confirm_v2=observe_confirm_v2,
    )

    threshold_adjustment = apply_entry_wait_threshold_bias_v1(
        entry_wait_context_v1=context,
        bias_bundle_v1={
            "state_wait_bias_v1": dict(state_wait_bias),
            "belief_wait_bias_v1": dict(belief_wait_bias),
            "edge_pair_wait_bias_v1": dict(edge_pair_wait_bias),
        },
    )

    bundle = {
        "contract_version": "entry_wait_bias_bundle_v1",
        "state_wait_bias_v1": dict(state_wait_bias),
        "belief_wait_bias_v1": dict(belief_wait_bias),
        "edge_pair_wait_bias_v1": dict(edge_pair_wait_bias),
        "symbol_probe_temperament_v1": dict(symbol_probe_temperament),
        "threshold_adjustment_v1": dict(threshold_adjustment),
    }
    bundle["bundle_summary_v1"] = compact_entry_wait_bias_bundle_v1(bundle)
    bundle["bundle_summary_v1"]["active_release_sources"] = _coerce_str_list(
        bundle["bundle_summary_v1"].get("active_release_sources")
    )
    bundle["bundle_summary_v1"]["active_wait_lock_sources"] = _coerce_str_list(
        bundle["bundle_summary_v1"].get("active_wait_lock_sources")
    )
    return bundle
