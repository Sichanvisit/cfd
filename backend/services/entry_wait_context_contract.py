"""Shared entry-wait context contract helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from backend.core.config import Config


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _coerce_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            rows.append(dict(item))
    return rows


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


def _extract_state_vector_v2(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("state_vector_v2", payload_map.get("state_vector_effective_v1", {})))


def _extract_belief_state_v1(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("belief_state_v1", payload_map.get("belief_state_effective_v1", {})))


def _extract_observe_confirm_v2(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("observe_confirm_v2", payload_map.get("observe_confirm", {})))


def build_entry_wait_reason_split_v1(
    *,
    observe_reason: str = "",
    blocked_by: str = "",
    action_none_reason: str = "",
) -> dict[str, str]:
    return {
        "observe_reason": _to_str(observe_reason),
        "blocked_by": _to_str(blocked_by),
        "action_none_reason": _to_str(action_none_reason),
    }


def extract_entry_wait_hints_v1(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    energy_helper = _as_mapping(payload_map.get("energy_helper_v2"))
    energy_metadata = _as_mapping(energy_helper.get("metadata"))
    utility_hints = _as_mapping(energy_metadata.get("utility_hints"))
    soft_block_hint = _as_mapping(energy_helper.get("soft_block_hint"))

    layer_mode_policy = _as_mapping(payload_map.get("layer_mode_policy_v1"))
    policy_hard_blocks = _coerce_rows(layer_mode_policy.get("hard_blocks", []))
    policy_suppressed_reasons = _coerce_rows(layer_mode_policy.get("suppressed_reasons", []))

    explicit_wait_vs_enter_hint = (
        "consumer_energy_wait_vs_enter_hint" in payload_map or "wait_vs_enter_hint" in payload_map
    )
    helper_wait_vs_enter_hint = "wait_vs_enter_hint" in utility_hints
    wait_vs_enter_hint = _to_str(
        payload_map.get("consumer_energy_wait_vs_enter_hint", payload_map.get("wait_vs_enter_hint", "")),
        _to_str(utility_hints.get("wait_vs_enter_hint", "")),
    ).lower()
    if wait_vs_enter_hint not in {"prefer_enter", "prefer_wait"}:
        wait_vs_enter_hint = ""
    wait_vs_enter_hint_source = "default"
    if wait_vs_enter_hint:
        if explicit_wait_vs_enter_hint:
            wait_vs_enter_hint_source = "payload"
        elif helper_wait_vs_enter_hint:
            wait_vs_enter_hint_source = "energy_helper"

    explicit_action_readiness = "consumer_energy_action_readiness" in payload_map
    helper_action_readiness = "action_readiness" in energy_helper
    action_readiness = _to_float(
        payload_map.get("consumer_energy_action_readiness", energy_helper.get("action_readiness", 0.0))
    )
    action_readiness_source = "default"
    if explicit_action_readiness:
        action_readiness_source = "payload"
    elif helper_action_readiness:
        action_readiness_source = "energy_helper"

    explicit_soft_block_active = "consumer_energy_soft_block_active" in payload_map
    explicit_soft_block_reason = "consumer_energy_soft_block_reason" in payload_map
    explicit_soft_block_strength = "consumer_energy_soft_block_strength" in payload_map
    soft_block_active = (
        _to_bool(payload_map.get("consumer_energy_soft_block_active"))
        if explicit_soft_block_active
        else _to_bool(soft_block_hint.get("active", False))
    )
    soft_block_reason = _to_str(
        payload_map.get("consumer_energy_soft_block_reason", ""),
        _to_str(soft_block_hint.get("reason", "")),
    )
    soft_block_strength = _to_float(
        payload_map.get("consumer_energy_soft_block_strength", soft_block_hint.get("strength", 0.0))
    )
    soft_block_hint_source = "default"
    if explicit_soft_block_active or explicit_soft_block_reason or explicit_soft_block_strength:
        soft_block_hint_source = "payload"
    elif bool(soft_block_hint):
        soft_block_hint_source = "energy_helper"

    policy_hard_block_active = _to_bool(payload_map.get("consumer_layer_mode_hard_block_active")) or bool(
        policy_hard_blocks
    )
    policy_suppressed = _to_bool(payload_map.get("consumer_layer_mode_suppressed")) or bool(
        policy_suppressed_reasons
    )
    policy_block_layer = _to_str(
        payload_map.get("consumer_policy_block_layer", ""),
        _to_str((policy_hard_blocks[0] if policy_hard_blocks else {}).get("layer", "")),
    )
    if not policy_block_layer and policy_suppressed_reasons:
        policy_block_layer = _to_str(policy_suppressed_reasons[0].get("layer", ""))
    policy_block_effect = _to_str(
        payload_map.get("consumer_policy_block_effect", ""),
        _to_str((policy_hard_blocks[0] if policy_hard_blocks else {}).get("effect", "")),
    )
    if not policy_block_effect and policy_suppressed_reasons:
        policy_block_effect = _to_str(policy_suppressed_reasons[0].get("effect", ""))

    return {
        "action_readiness": float(action_readiness),
        "has_action_readiness_hint": action_readiness_source != "default",
        "action_readiness_source": str(action_readiness_source),
        "wait_vs_enter_hint": str(wait_vs_enter_hint),
        "has_wait_vs_enter_hint": wait_vs_enter_hint_source != "default",
        "wait_vs_enter_hint_source": str(wait_vs_enter_hint_source),
        "soft_block_active": bool(soft_block_active),
        "soft_block_reason": str(soft_block_reason),
        "soft_block_strength": float(soft_block_strength),
        "has_soft_block_hint": soft_block_hint_source != "default",
        "soft_block_hint_source": str(soft_block_hint_source),
        "policy_hard_block_active": bool(policy_hard_block_active),
        "policy_suppressed": bool(policy_suppressed),
        "policy_block_layer": str(policy_block_layer),
        "policy_block_effect": str(policy_block_effect),
    }


def build_entry_wait_context_v1(
    *,
    symbol: str = "",
    payload: Mapping[str, Any] | None = None,
    observe_confirm_v2: Mapping[str, Any] | None = None,
    wait_hints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    symbol_value = _to_str(symbol or payload_map.get("symbol", "")).upper()
    observe_confirm = _as_mapping(observe_confirm_v2) or _extract_observe_confirm_v2(payload_map)
    observe_meta = _as_mapping(observe_confirm.get("metadata"))
    blocked_by = _to_str(payload_map.get("blocked_by", ""))
    action_none_reason = _to_str(payload_map.get("action_none_reason", ""))
    observe_reason = _to_str(payload_map.get("observe_reason", "") or observe_confirm.get("reason", ""))
    reason_split_v1 = build_entry_wait_reason_split_v1(
        observe_reason=observe_reason,
        blocked_by=blocked_by,
        action_none_reason=action_none_reason,
    )
    base_soft_threshold = float(
        Config.get_symbol_float(
            symbol_value,
            getattr(Config, "ENTRY_WAIT_SOFT_SCORE_BY_SYMBOL", {}),
            float(getattr(Config, "ENTRY_WAIT_SOFT_SCORE", 45.0)),
        )
    )
    base_hard_threshold = float(
        Config.get_symbol_float(
            symbol_value,
            getattr(Config, "ENTRY_WAIT_HARD_BLOCK_SCORE_BY_SYMBOL", {}),
            float(getattr(Config, "ENTRY_WAIT_HARD_BLOCK_SCORE", 70.0)),
        )
    )
    state_vector_v2 = _extract_state_vector_v2(payload_map)
    belief_state_v1 = _extract_belief_state_v1(payload_map)
    belief_metadata = _as_mapping(belief_state_v1.get("metadata"))
    probe_plan_v1 = _as_mapping(payload_map.get("entry_probe_plan_v1"))
    probe_candidate_v1 = _as_mapping(payload_map.get("probe_candidate_v1", observe_meta.get("probe_candidate_v1", {})))
    probe_temperament = _as_mapping(
        probe_plan_v1.get(
            "symbol_probe_temperament_v1",
            probe_candidate_v1.get("symbol_probe_temperament_v1", {}),
        )
    )
    edge_pair_law_v1 = _as_mapping(payload_map.get("edge_pair_law_v1", observe_meta.get("edge_pair_law_v1", {})))
    wait_hints_v1 = _as_mapping(wait_hints) or extract_entry_wait_hints_v1(payload_map)

    return {
        "contract_version": "entry_wait_context_v1",
        "identity": {
            "symbol": str(symbol_value),
            "action": _to_str(payload_map.get("action", "")).upper(),
            "core_allowed_action": _to_str(payload_map.get("core_allowed_action", "NONE"), "NONE").upper(),
            "preflight_allowed_action": _to_str(
                payload_map.get("preflight_allowed_action", "BOTH"),
                "BOTH",
            ).upper(),
        },
        "reasons": {
            "blocked_by": str(blocked_by),
            "observe_reason": str(observe_reason),
            "action_none_reason": str(action_none_reason),
            "reason_split_v1": dict(reason_split_v1),
        },
        "market": {
            "box_state": _to_str(payload_map.get("box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "bb_state": _to_str(payload_map.get("bb_state", "UNKNOWN"), "UNKNOWN").upper(),
            "observe_state": _to_str(observe_confirm.get("state", "")).upper(),
            "observe_action": _to_str(observe_confirm.get("action", "")).upper(),
            "observe_side": _to_str(observe_confirm.get("side", "")).upper(),
            "observe_metadata": dict(observe_meta),
        },
        "setup": {
            "status": _to_str(payload_map.get("setup_status", "pending"), "pending").upper(),
            "reason": _to_str(payload_map.get("setup_reason", "")),
            "trigger_state": _to_str(payload_map.get("setup_trigger_state", "UNKNOWN"), "UNKNOWN").upper(),
        },
        "scores": {
            "wait_score": _to_float(payload_map.get("wait_score", 0.0), 0.0),
            "wait_conflict": _to_float(payload_map.get("wait_conflict", 0.0), 0.0),
            "wait_noise": _to_float(payload_map.get("wait_noise", 0.0), 0.0),
            "wait_penalty": _to_float(payload_map.get("wait_penalty", 0.0), 0.0),
        },
        "thresholds": {
            "base_soft_threshold": float(base_soft_threshold),
            "base_hard_threshold": float(base_hard_threshold),
            "effective_soft_threshold": float(base_soft_threshold),
            "effective_hard_threshold": float(base_hard_threshold),
        },
        "helper_hints": dict(wait_hints_v1),
        "state_inputs": {
            "state_vector_v2": dict(state_vector_v2),
            "state_metadata": dict(_as_mapping(state_vector_v2.get("metadata"))),
        },
        "belief_inputs": {
            "belief_state_v1": dict(belief_state_v1),
            "belief_metadata": dict(belief_metadata),
        },
        "observe_probe": {
            "observe_confirm_v2": dict(observe_confirm),
            "probe_candidate_v1": dict(probe_candidate_v1),
            "entry_probe_plan_v1": dict(probe_plan_v1),
            "edge_pair_law_v1": dict(edge_pair_law_v1),
            "probe_scene_id": _to_str(probe_temperament.get("scene_id", "")),
            "probe_active": _to_bool(probe_plan_v1.get("active", probe_candidate_v1.get("active", False))),
            "probe_ready_for_entry": _to_bool(probe_plan_v1.get("ready_for_entry", False)),
            "probe_trigger_branch": _to_str(
                probe_plan_v1.get("trigger_branch", probe_candidate_v1.get("trigger_branch", ""))
            ),
            "xau_second_support_probe_relief": _to_bool(
                observe_meta.get("xau_second_support_probe_relief", False)
            ),
        },
        "bias": {},
        "policy": {},
    }


def compact_entry_wait_context_v1(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context_map = _as_mapping(context)
    identity = _as_mapping(context_map.get("identity"))
    reasons = _as_mapping(context_map.get("reasons"))
    market = _as_mapping(context_map.get("market"))
    setup = _as_mapping(context_map.get("setup"))
    scores = _as_mapping(context_map.get("scores"))
    thresholds = _as_mapping(context_map.get("thresholds"))
    helper_hints = _as_mapping(context_map.get("helper_hints"))
    observe_probe = _as_mapping(context_map.get("observe_probe"))
    bias = _as_mapping(context_map.get("bias"))
    policy = _as_mapping(context_map.get("policy"))

    state_bias = _as_mapping(bias.get("state_wait_bias_v1"))
    belief_bias = _as_mapping(bias.get("belief_wait_bias_v1"))
    edge_pair_bias = _as_mapping(bias.get("edge_pair_wait_bias_v1"))
    probe_bias = _as_mapping(bias.get("symbol_probe_temperament_v1"))
    bundle_summary = _as_mapping(bias.get("bundle_summary_v1", bias.get("bias_bundle_v1")))
    threshold_adjustment = _as_mapping(
        bias.get("threshold_adjustment_v1", bundle_summary.get("threshold_adjustment"))
    )
    state_policy_input = _as_mapping(policy.get("entry_wait_state_policy_input_v1"))

    return {
        "contract_version": _to_str(context_map.get("contract_version", "entry_wait_context_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")),
            "action": _to_str(identity.get("action", "")).upper(),
            "core_allowed_action": _to_str(identity.get("core_allowed_action", "NONE"), "NONE").upper(),
            "preflight_allowed_action": _to_str(
                identity.get("preflight_allowed_action", "BOTH"),
                "BOTH",
            ).upper(),
        },
        "reasons": {
            "blocked_by": _to_str(reasons.get("blocked_by", "")),
            "observe_reason": _to_str(reasons.get("observe_reason", "")),
            "action_none_reason": _to_str(reasons.get("action_none_reason", "")),
            "reason_split_v1": dict(_as_mapping(reasons.get("reason_split_v1"))),
        },
        "market": {
            "box_state": _to_str(market.get("box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "bb_state": _to_str(market.get("bb_state", "UNKNOWN"), "UNKNOWN").upper(),
            "observe_state": _to_str(market.get("observe_state", "")).upper(),
            "observe_action": _to_str(market.get("observe_action", "")).upper(),
            "observe_side": _to_str(market.get("observe_side", "")).upper(),
        },
        "setup": {
            "status": _to_str(setup.get("status", "PENDING"), "PENDING").upper(),
            "reason": _to_str(setup.get("reason", "")),
            "trigger_state": _to_str(setup.get("trigger_state", "UNKNOWN"), "UNKNOWN").upper(),
        },
        "scores": {
            "wait_score": _to_float(scores.get("wait_score", 0.0), 0.0),
            "wait_conflict": _to_float(scores.get("wait_conflict", 0.0), 0.0),
            "wait_noise": _to_float(scores.get("wait_noise", 0.0), 0.0),
            "wait_penalty": _to_float(scores.get("wait_penalty", 0.0), 0.0),
        },
        "thresholds": {
            "base_soft_threshold": _to_float(thresholds.get("base_soft_threshold", 0.0), 0.0),
            "base_hard_threshold": _to_float(thresholds.get("base_hard_threshold", 0.0), 0.0),
            "effective_soft_threshold": _to_float(thresholds.get("effective_soft_threshold", 0.0), 0.0),
            "effective_hard_threshold": _to_float(thresholds.get("effective_hard_threshold", 0.0), 0.0),
        },
        "helper_hints": {
            "action_readiness": _to_float(helper_hints.get("action_readiness", 0.0), 0.0),
            "has_action_readiness_hint": _to_bool(helper_hints.get("has_action_readiness_hint", False)),
            "action_readiness_source": _to_str(helper_hints.get("action_readiness_source", "")),
            "wait_vs_enter_hint": _to_str(helper_hints.get("wait_vs_enter_hint", "")),
            "has_wait_vs_enter_hint": _to_bool(helper_hints.get("has_wait_vs_enter_hint", False)),
            "wait_vs_enter_hint_source": _to_str(helper_hints.get("wait_vs_enter_hint_source", "")),
            "soft_block_active": _to_bool(helper_hints.get("soft_block_active", False)),
            "soft_block_reason": _to_str(helper_hints.get("soft_block_reason", "")),
            "soft_block_strength": _to_float(helper_hints.get("soft_block_strength", 0.0), 0.0),
            "has_soft_block_hint": _to_bool(helper_hints.get("has_soft_block_hint", False)),
            "soft_block_hint_source": _to_str(helper_hints.get("soft_block_hint_source", "")),
            "policy_hard_block_active": _to_bool(helper_hints.get("policy_hard_block_active", False)),
            "policy_suppressed": _to_bool(helper_hints.get("policy_suppressed", False)),
            "policy_block_layer": _to_str(helper_hints.get("policy_block_layer", "")),
            "policy_block_effect": _to_str(helper_hints.get("policy_block_effect", "")),
        },
        "observe_probe": {
            "probe_scene_id": _to_str(observe_probe.get("probe_scene_id", "")),
            "probe_active": _to_bool(observe_probe.get("probe_active", False)),
            "probe_ready_for_entry": _to_bool(observe_probe.get("probe_ready_for_entry", False)),
            "probe_trigger_branch": _to_str(observe_probe.get("probe_trigger_branch", "")),
            "xau_second_support_probe_relief": _to_bool(
                observe_probe.get("xau_second_support_probe_relief", False)
            ),
        },
        "bias": {
            "state": {
                "prefer_confirm_release": _to_bool(state_bias.get("prefer_confirm_release", False)),
                "prefer_wait_lock": _to_bool(state_bias.get("prefer_wait_lock", False)),
                "wait_soft_mult": _to_float(state_bias.get("wait_soft_mult", 1.0), 1.0),
                "wait_hard_mult": _to_float(state_bias.get("wait_hard_mult", 1.0), 1.0),
            },
            "belief": {
                "prefer_confirm_release": _to_bool(belief_bias.get("prefer_confirm_release", False)),
                "prefer_wait_lock": _to_bool(belief_bias.get("prefer_wait_lock", False)),
                "wait_soft_mult": _to_float(belief_bias.get("wait_soft_mult", 1.0), 1.0),
                "wait_hard_mult": _to_float(belief_bias.get("wait_hard_mult", 1.0), 1.0),
            },
            "edge_pair": {
                "present": _to_bool(edge_pair_bias.get("present", False)),
                "context_label": _to_str(edge_pair_bias.get("context_label", "")),
                "winner_side": _to_str(edge_pair_bias.get("winner_side", "")),
                "pair_gap": _to_float(edge_pair_bias.get("pair_gap", 0.0), 0.0),
                "acting_side": _to_str(edge_pair_bias.get("acting_side", "")),
                "prefer_confirm_release": _to_bool(edge_pair_bias.get("prefer_confirm_release", False)),
                "prefer_wait_lock": _to_bool(edge_pair_bias.get("prefer_wait_lock", False)),
            },
            "probe": {
                "present": _to_bool(probe_bias.get("present", False)),
                "scene_id": _to_str(probe_bias.get("scene_id", "")),
                "active": _to_bool(probe_bias.get("active", False)),
                "ready_for_entry": _to_bool(probe_bias.get("ready_for_entry", False)),
                "prefer_confirm_release": _to_bool(probe_bias.get("prefer_confirm_release", False)),
                "prefer_wait_lock": _to_bool(probe_bias.get("prefer_wait_lock", False)),
            },
            "bundle": {
                "contract_version": _to_str(bundle_summary.get("contract_version", "")),
                "active_release_sources": _coerce_str_list(bundle_summary.get("active_release_sources")),
                "active_wait_lock_sources": _coerce_str_list(bundle_summary.get("active_wait_lock_sources")),
                "release_bias_count": _to_int(bundle_summary.get("release_bias_count", 0), 0),
                "wait_lock_bias_count": _to_int(bundle_summary.get("wait_lock_bias_count", 0), 0),
                "threshold_adjustment": {
                    "base_soft_threshold": _to_float(
                        threshold_adjustment.get("base_soft_threshold", thresholds.get("base_soft_threshold", 0.0)),
                        0.0,
                    ),
                    "base_hard_threshold": _to_float(
                        threshold_adjustment.get("base_hard_threshold", thresholds.get("base_hard_threshold", 0.0)),
                        0.0,
                    ),
                    "effective_soft_threshold": _to_float(
                        threshold_adjustment.get(
                            "effective_soft_threshold",
                            thresholds.get("effective_soft_threshold", 0.0),
                        ),
                        0.0,
                    ),
                    "effective_hard_threshold": _to_float(
                        threshold_adjustment.get(
                            "effective_hard_threshold",
                            thresholds.get("effective_hard_threshold", 0.0),
                        ),
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
            },
        },
        "policy": {
            "state": _to_str(policy.get("state", "")),
            "reason": _to_str(policy.get("reason", "")),
            "hard_wait": _to_bool(policy.get("hard_wait", False)),
            "lower_rebound_probe_active": _to_bool(policy.get("lower_rebound_probe_active", False)),
            "upper_reject_probe_active": _to_bool(policy.get("upper_reject_probe_active", False)),
            "lower_soft_wait_candidate": _to_bool(policy.get("lower_soft_wait_candidate", False)),
            "btc_lower_strong_score_soft_wait": _to_bool(
                policy.get("btc_lower_strong_score_soft_wait", False)
            ),
            "xau_second_support_probe": _to_bool(policy.get("xau_second_support_probe", False)),
            "xau_upper_sell_probe": _to_bool(policy.get("xau_upper_sell_probe", False)),
            "entry_wait_state_policy_input_v1": {
                "contract_version": _to_str(state_policy_input.get("contract_version", "")),
                "identity": dict(_as_mapping(state_policy_input.get("identity"))),
                "reason_split_v1": dict(_as_mapping(state_policy_input.get("reason_split_v1"))),
                "market": dict(_as_mapping(state_policy_input.get("market"))),
                "setup": dict(_as_mapping(state_policy_input.get("setup"))),
                "scores": dict(_as_mapping(state_policy_input.get("scores"))),
                "thresholds": dict(_as_mapping(state_policy_input.get("thresholds"))),
                "helper_hints": dict(_as_mapping(state_policy_input.get("helper_hints"))),
                "special_scenes": dict(_as_mapping(state_policy_input.get("special_scenes"))),
                "bias_bundle": dict(_as_mapping(state_policy_input.get("bias_bundle"))),
            },
        },
    }
