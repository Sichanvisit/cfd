"""State-policy input contracts for entry wait classification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.entry_wait_state_policy import resolve_entry_wait_state_policy_v1


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _to_str(item)
        if text:
            items.append(text)
    return items


def _required_side(policy: object) -> str:
    upper = _to_str(policy).upper()
    if upper == "BUY_ONLY":
        return "BUY"
    if upper == "SELL_ONLY":
        return "SELL"
    return ""


def build_entry_wait_state_policy_input_v1(
    entry_wait_context_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _as_mapping(entry_wait_context_v1)
    identity = _as_mapping(context.get("identity"))
    reasons = _as_mapping(context.get("reasons"))
    market = _as_mapping(context.get("market"))
    setup = _as_mapping(context.get("setup"))
    scores = _as_mapping(context.get("scores"))
    thresholds = _as_mapping(context.get("thresholds"))
    helper_hints = _as_mapping(context.get("helper_hints"))
    observe_probe = _as_mapping(context.get("observe_probe"))
    bias = _as_mapping(context.get("bias"))

    state_wait_bias = _as_mapping(bias.get("state_wait_bias_v1"))
    belief_wait_bias = _as_mapping(bias.get("belief_wait_bias_v1"))
    edge_pair_wait_bias = _as_mapping(bias.get("edge_pair_wait_bias_v1"))
    symbol_probe_temperament = _as_mapping(bias.get("symbol_probe_temperament_v1"))
    bundle_summary = _as_mapping(bias.get("bundle_summary_v1", bias.get("bias_bundle_v1")))
    threshold_adjustment = _as_mapping(
        bias.get("threshold_adjustment_v1", bundle_summary.get("threshold_adjustment"))
    )

    symbol = _to_str(identity.get("symbol", "")).upper()
    action = _to_str(identity.get("action", "")).upper()
    core_allowed_action = _to_str(identity.get("core_allowed_action", "NONE"), "NONE").upper()
    preflight_allowed_action = _to_str(
        identity.get("preflight_allowed_action", "BOTH"),
        "BOTH",
    ).upper()
    blocked_by = _to_str(reasons.get("blocked_by", ""))
    box_state = _to_str(market.get("box_state", "UNKNOWN"), "UNKNOWN").upper()
    bb_state = _to_str(market.get("bb_state", "UNKNOWN"), "UNKNOWN").upper()
    wait_score = _to_float(scores.get("wait_score", 0.0), 0.0)
    wait_conflict = _to_float(scores.get("wait_conflict", 0.0), 0.0)
    wait_noise = _to_float(scores.get("wait_noise", 0.0), 0.0)

    required_side = _required_side(preflight_allowed_action) or _required_side(core_allowed_action)
    btc_lower_strong_score_soft_wait_candidate = bool(
        symbol == "BTCUSD"
        and box_state == "LOWER"
        and bb_state in {"MID", "UNKNOWN"}
        and preflight_allowed_action in {"BOTH", "BUY_ONLY"}
        and blocked_by in {"core_not_passed", "dynamic_threshold_not_met"}
        and action in {"", "BUY"}
        and wait_score <= 80.0
        and wait_conflict <= 20.0
        and wait_noise <= 18.0
    )

    return {
        "contract_version": "entry_wait_state_policy_input_v1",
        "identity": {
            "symbol": str(symbol),
            "action": str(action),
            "core_allowed_action": str(core_allowed_action),
            "preflight_allowed_action": str(preflight_allowed_action),
            "required_side": str(required_side),
        },
        "reasons": {
            "blocked_by": str(blocked_by),
            "observe_reason": _to_str(reasons.get("observe_reason", "")),
            "action_none_reason": _to_str(reasons.get("action_none_reason", "")),
            "reason_split_v1": dict(_as_mapping(reasons.get("reason_split_v1"))),
        },
        "market": {
            "box_state": str(box_state),
            "bb_state": str(bb_state),
            "observe_metadata": dict(_as_mapping(market.get("observe_metadata"))),
        },
        "setup": {
            "status": _to_str(setup.get("status", "PENDING"), "PENDING").upper(),
            "reason": _to_str(setup.get("reason", "")),
            "trigger_state": _to_str(setup.get("trigger_state", "UNKNOWN"), "UNKNOWN").upper(),
        },
        "scores": {
            "wait_score": float(wait_score),
            "wait_conflict": float(wait_conflict),
            "wait_noise": float(wait_noise),
            "wait_penalty": _to_float(scores.get("wait_penalty", 0.0), 0.0),
        },
        "thresholds": {
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
        },
        "helper_hints": {
            "action_readiness": _to_float(helper_hints.get("action_readiness", 0.0), 0.0),
            "wait_vs_enter_hint": _to_str(helper_hints.get("wait_vs_enter_hint", "")).lower(),
            "soft_block_active": _to_bool(helper_hints.get("soft_block_active", False)),
            "soft_block_reason": _to_str(helper_hints.get("soft_block_reason", "")),
            "soft_block_strength": _to_float(helper_hints.get("soft_block_strength", 0.0), 0.0),
            "policy_hard_block_active": _to_bool(helper_hints.get("policy_hard_block_active", False)),
            "policy_suppressed": _to_bool(helper_hints.get("policy_suppressed", False)),
            "action_readiness_source": _to_str(helper_hints.get("action_readiness_source", "")),
            "wait_vs_enter_hint_source": _to_str(helper_hints.get("wait_vs_enter_hint_source", "")),
            "soft_block_hint_source": _to_str(helper_hints.get("soft_block_hint_source", "")),
            "policy_block_layer": _to_str(helper_hints.get("policy_block_layer", "")),
            "policy_block_effect": _to_str(helper_hints.get("policy_block_effect", "")),
        },
        "bias": {
            "state_wait_bias_v1": dict(state_wait_bias),
            "belief_wait_bias_v1": dict(belief_wait_bias),
            "edge_pair_wait_bias_v1": dict(edge_pair_wait_bias),
            "symbol_probe_temperament_v1": dict(symbol_probe_temperament),
            "bundle_summary_v1": dict(bundle_summary),
        },
        "special_scenes": {
            "probe_scene_id": _to_str(
                observe_probe.get("probe_scene_id", symbol_probe_temperament.get("scene_id", ""))
            ),
            "probe_active": _to_bool(
                observe_probe.get("probe_active", symbol_probe_temperament.get("active", False))
            ),
            "probe_ready_for_entry": _to_bool(
                observe_probe.get(
                    "probe_ready_for_entry",
                    symbol_probe_temperament.get("ready_for_entry", False),
                )
            ),
            "xau_second_support_probe_relief": _to_bool(
                observe_probe.get(
                    "xau_second_support_probe_relief",
                    _as_mapping(market.get("observe_metadata")).get("xau_second_support_probe_relief", False),
                )
            ),
            "btc_lower_strong_score_soft_wait_candidate": bool(
                btc_lower_strong_score_soft_wait_candidate
            ),
        },
    }


def compact_entry_wait_state_policy_input_v1(
    entry_wait_state_policy_input_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_input = _as_mapping(entry_wait_state_policy_input_v1)
    identity = _as_mapping(policy_input.get("identity"))
    reasons = _as_mapping(policy_input.get("reasons"))
    market = _as_mapping(policy_input.get("market"))
    setup = _as_mapping(policy_input.get("setup"))
    scores = _as_mapping(policy_input.get("scores"))
    thresholds = _as_mapping(policy_input.get("thresholds"))
    helper_hints = _as_mapping(policy_input.get("helper_hints"))
    special_scenes = _as_mapping(policy_input.get("special_scenes"))
    bias = _as_mapping(policy_input.get("bias"))
    bundle_summary = _as_mapping(bias.get("bundle_summary_v1"))

    return {
        "contract_version": _to_str(policy_input.get("contract_version", "entry_wait_state_policy_input_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")),
            "action": _to_str(identity.get("action", "")).upper(),
            "core_allowed_action": _to_str(identity.get("core_allowed_action", "NONE"), "NONE").upper(),
            "preflight_allowed_action": _to_str(
                identity.get("preflight_allowed_action", "BOTH"),
                "BOTH",
            ).upper(),
            "required_side": _to_str(identity.get("required_side", "")).upper(),
        },
        "reason_split_v1": dict(_as_mapping(reasons.get("reason_split_v1"))),
        "market": {
            "box_state": _to_str(market.get("box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "bb_state": _to_str(market.get("bb_state", "UNKNOWN"), "UNKNOWN").upper(),
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
            "wait_vs_enter_hint": _to_str(helper_hints.get("wait_vs_enter_hint", "")),
            "soft_block_active": _to_bool(helper_hints.get("soft_block_active", False)),
            "soft_block_reason": _to_str(helper_hints.get("soft_block_reason", "")),
            "soft_block_strength": _to_float(helper_hints.get("soft_block_strength", 0.0), 0.0),
            "policy_hard_block_active": _to_bool(helper_hints.get("policy_hard_block_active", False)),
            "policy_suppressed": _to_bool(helper_hints.get("policy_suppressed", False)),
        },
        "special_scenes": {
            "probe_scene_id": _to_str(special_scenes.get("probe_scene_id", "")),
            "probe_active": _to_bool(special_scenes.get("probe_active", False)),
            "probe_ready_for_entry": _to_bool(special_scenes.get("probe_ready_for_entry", False)),
            "xau_second_support_probe_relief": _to_bool(
                special_scenes.get("xau_second_support_probe_relief", False)
            ),
            "btc_lower_strong_score_soft_wait_candidate": _to_bool(
                special_scenes.get("btc_lower_strong_score_soft_wait_candidate", False)
            ),
        },
        "bias_bundle": {
            "active_release_sources": _coerce_str_list(bundle_summary.get("active_release_sources")),
            "active_wait_lock_sources": _coerce_str_list(bundle_summary.get("active_wait_lock_sources")),
            "release_bias_count": _to_int(bundle_summary.get("release_bias_count", 0), 0),
            "wait_lock_bias_count": _to_int(bundle_summary.get("wait_lock_bias_count", 0), 0),
        },
    }


def resolve_entry_wait_state_policy_from_context_v1(
    entry_wait_context_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_input = build_entry_wait_state_policy_input_v1(entry_wait_context_v1)
    identity = _as_mapping(policy_input.get("identity"))
    reasons = _as_mapping(policy_input.get("reasons"))
    market = _as_mapping(policy_input.get("market"))
    setup = _as_mapping(policy_input.get("setup"))
    scores = _as_mapping(policy_input.get("scores"))
    thresholds = _as_mapping(policy_input.get("thresholds"))
    helper_hints = _as_mapping(policy_input.get("helper_hints"))
    bias = _as_mapping(policy_input.get("bias"))

    state_policy = resolve_entry_wait_state_policy_v1(
        symbol=_to_str(identity.get("symbol", "")),
        action=_to_str(identity.get("action", "")),
        blocked_by=_to_str(reasons.get("blocked_by", "")),
        action_none_reason=_to_str(reasons.get("action_none_reason", "")),
        box_state=_to_str(market.get("box_state", "")),
        bb_state=_to_str(market.get("bb_state", "")),
        observe_reason=_to_str(reasons.get("observe_reason", "")),
        core_allowed_action=_to_str(identity.get("core_allowed_action", "")),
        preflight_allowed_action=_to_str(identity.get("preflight_allowed_action", "")),
        setup_reason=_to_str(setup.get("reason", "")),
        setup_trigger_state=_to_str(setup.get("trigger_state", "")),
        wait_score=_to_float(scores.get("wait_score", 0.0), 0.0),
        wait_conflict=_to_float(scores.get("wait_conflict", 0.0), 0.0),
        wait_noise=_to_float(scores.get("wait_noise", 0.0), 0.0),
        wait_soft=_to_float(thresholds.get("effective_soft_threshold", 0.0), 0.0),
        wait_hard=_to_float(thresholds.get("effective_hard_threshold", 0.0), 0.0),
        action_readiness=_to_float(helper_hints.get("action_readiness", 0.0), 0.0),
        wait_vs_enter_hint=_to_str(helper_hints.get("wait_vs_enter_hint", "")),
        soft_block_active=_to_bool(helper_hints.get("soft_block_active", False)),
        soft_block_reason=_to_str(helper_hints.get("soft_block_reason", "")),
        soft_block_strength=_to_float(helper_hints.get("soft_block_strength", 0.0), 0.0),
        policy_hard_block_active=_to_bool(helper_hints.get("policy_hard_block_active", False)),
        policy_suppressed=_to_bool(helper_hints.get("policy_suppressed", False)),
        observe_metadata=_as_mapping(market.get("observe_metadata")),
        state_wait_bias_v1=_as_mapping(bias.get("state_wait_bias_v1")),
        belief_wait_bias_v1=_as_mapping(bias.get("belief_wait_bias_v1")),
        edge_pair_wait_bias_v1=_as_mapping(bias.get("edge_pair_wait_bias_v1")),
        symbol_probe_temperament_v1=_as_mapping(bias.get("symbol_probe_temperament_v1")),
    )

    return {
        "contract_version": "entry_wait_state_policy_resolution_v1",
        "entry_wait_state_policy_input_v1": dict(policy_input),
        "compact_entry_wait_state_policy_input_v1": dict(
            compact_entry_wait_state_policy_input_v1(policy_input)
        ),
        "entry_wait_state_policy_v1": dict(state_policy),
    }
