"""Shared symbol-aware execution temperament helpers."""

from __future__ import annotations


_SIDE_TO_ALLOWED_ACTION = {
    "BUY": "BUY_ONLY",
    "SELL": "SELL_ONLY",
}

_SCENE_TO_DIRECTION = {
    "xau_upper_sell_probe": "SELL",
    "xau_second_support_buy_probe": "BUY",
    "btc_lower_buy_conservative_probe": "BUY",
    "btc_upper_sell_probe": "SELL",
}

_SCENE_TO_POLICY_FAMILY = {
    "xau_upper_sell_probe": "upper_reject",
    "xau_second_support_buy_probe": "lower_second_support",
    "btc_lower_buy_conservative_probe": "lower_rebound",
    "btc_upper_sell_probe": "upper_reject",
    "nas_clean_confirm_probe": "clean_confirm",
}

_DIRECTIONAL_TRIGGER_TO_SIDE = {
    "upper_reject": "SELL",
    "lower_rebound": "BUY",
}


def _to_str(value, default: str = "") -> str:
    text = str(value or default).strip()
    return text if text else str(default)


def canonical_symbol(symbol: str = "") -> str:
    symbol_u = _to_str(symbol).upper()
    if "BTC" in symbol_u:
        return "BTCUSD"
    if "XAU" in symbol_u or "GOLD" in symbol_u:
        return "XAUUSD"
    if "NAS" in symbol_u or "US100" in symbol_u or "USTEC" in symbol_u:
        return "NAS100"
    return symbol_u


def resolve_archetype_implied_action(archetype_id: str = "") -> str:
    archetype = _to_str(archetype_id).lower()
    if not archetype:
        return ""
    if archetype.endswith("_buy"):
        return "BUY"
    if archetype.endswith("_sell"):
        return "SELL"
    return ""


def resolve_allowed_action(direction: str = "", *, fallback: str = "BOTH") -> str:
    direction_u = _to_str(direction).upper()
    if direction_u in _SIDE_TO_ALLOWED_ACTION:
        return _SIDE_TO_ALLOWED_ACTION[direction_u]
    return _to_str(fallback, "BOTH").upper()


def resolve_probe_scene_direction(
    scene_id: str = "",
    *,
    reason: str = "",
    side: str = "",
    action: str = "",
    trigger_branch: str = "",
    probe_direction: str = "",
) -> str:
    return _resolve_probe_scene_direction(
        scene_id,
        reason=reason,
        side=side,
        action=action,
        trigger_branch=trigger_branch,
        probe_direction=probe_direction,
    )


def resolve_probe_scene_policy_family(
    scene_id: str = "",
    *,
    reason: str = "",
    side: str = "",
    action: str = "",
    trigger_branch: str = "",
    probe_direction: str = "",
) -> str:
    return _resolve_probe_scene_policy_family(
        scene_id,
        reason=reason,
        side=side,
        action=action,
        trigger_branch=trigger_branch,
        probe_direction=probe_direction,
    )


def _resolve_probe_scene_direction(
    scene_id: str = "",
    *,
    reason: str = "",
    side: str = "",
    action: str = "",
    trigger_branch: str = "",
    probe_direction: str = "",
) -> str:
    for candidate in (side, action, probe_direction):
        direction = _to_str(candidate).upper()
        if direction in {"BUY", "SELL"}:
            return direction

    trigger_l = _to_str(trigger_branch).lower()
    if trigger_l in _DIRECTIONAL_TRIGGER_TO_SIDE:
        return _DIRECTIONAL_TRIGGER_TO_SIDE[trigger_l]

    reason_l = _to_str(reason).lower()
    if "upper_reject" in reason_l or "upper_break_fail" in reason_l:
        return "SELL"
    if "lower_rebound" in reason_l:
        return "BUY"

    scene = _to_str(scene_id)
    if not scene:
        return ""
    explicit = _SCENE_TO_DIRECTION.get(scene, "")
    if explicit:
        return explicit
    scene_l = scene.lower()
    if "_buy" in scene_l:
        return "BUY"
    if "_sell" in scene_l:
        return "SELL"
    return ""


def _resolve_probe_scene_policy_family(
    scene_id: str = "",
    *,
    reason: str = "",
    side: str = "",
    action: str = "",
    trigger_branch: str = "",
    probe_direction: str = "",
) -> str:
    scene = _to_str(scene_id).lower()
    explicit = _SCENE_TO_POLICY_FAMILY.get(scene, "")
    if explicit:
        return explicit

    trigger_l = _to_str(trigger_branch).lower()
    if trigger_l in {"upper_reject", "lower_rebound"}:
        return trigger_l

    reason_l = _to_str(reason).lower()
    if reason_l in {"outer_band_reversal_support_required_observe", "middle_sr_anchor_required_observe"}:
        return "upper_reject"
    if "upper_reject" in reason_l or "upper_break_fail" in reason_l:
        return "upper_reject"
    if "lower_rebound" in reason_l:
        return "lower_rebound"

    direction = _resolve_probe_scene_direction(
        scene_id,
        reason=reason,
        side=side,
        action=action,
        trigger_branch=trigger_branch,
        probe_direction=probe_direction,
    )
    if direction == "SELL":
        return "upper_reject"
    if direction == "BUY":
        return "lower_rebound"
    return ""


_DEFAULT_PROBE_TEMPERAMENT = {
    "contract_version": "symbol_probe_temperament_v1",
    "scene_id": "default_edge_probe",
    "promotion_bias": "neutral",
    "floor_mult": 0.72,
    "advantage_mult": 0.25,
    "support_tolerance": 0.015,
    "entry_style_hint": "probe_then_confirm",
    "note": "default_probe_temperament",
}

_SCENE_PROBE_TEMPERAMENT = {
    "xau_upper_sell_probe": {
        "scene_id": "xau_upper_sell_probe",
        "promotion_bias": "fast_probe",
        "floor_mult": 0.60,
        "advantage_mult": 0.10,
        "support_tolerance": 0.04,
        "entry_style_hint": "early_upper_reject_probe",
        "note": "xau_upper_sell_probe_faster",
    },
    "xau_second_support_buy_probe": {
        "scene_id": "xau_second_support_buy_probe",
        "promotion_bias": "aggressive_second_support",
        "floor_mult": 0.58,
        "advantage_mult": 0.12,
        "support_tolerance": 0.045,
        "entry_style_hint": "second_support_probe",
        "note": "xau_second_support_buy_more_aggressive",
    },
    "btc_lower_buy_conservative_probe": {
        "scene_id": "btc_lower_buy_conservative_probe",
        "promotion_bias": "conservative_hold_first",
        "floor_mult": 0.86,
        "advantage_mult": 0.42,
        "support_tolerance": 0.010,
        "entry_style_hint": "conservative_lower_probe",
        "note": "btc_lower_buy_less_frequent_hold_longer",
    },
    "btc_upper_sell_probe": {
        "scene_id": "btc_upper_sell_probe",
        "promotion_bias": "measured_upper_sell",
        "floor_mult": 0.68,
        "advantage_mult": 0.18,
        "support_tolerance": 0.020,
        "entry_style_hint": "measured_upper_sell_probe",
        "note": "btc_upper_sell_uses_existing_upper_reject_with_measured_relief",
    },
    "nas_clean_confirm_probe": {
        "scene_id": "nas_clean_confirm_probe",
        "promotion_bias": "clean_confirm",
        "floor_mult": 0.78,
        "advantage_mult": 0.30,
        "support_tolerance": 0.012,
        "entry_style_hint": "clean_confirm_probe",
        "note": "nas_probe_prefers_clean_confirm",
    },
}

_DEFAULT_PROBE_PLAN = {
    "scene_id": "default_edge_probe",
    "promotion_bias": "neutral",
    "min_confirm_fake_gap": 0.03,
    "min_continue_fail_gap": -0.01,
    "min_persistence": 0.18,
    "min_belief": 0.52,
    "min_pair_gap": 0.12,
    "min_candidate_support": 0.30,
    "min_action_confirm_score": 0.22,
    "min_streak": 1,
    "max_side_barrier": 0.42,
    "min_energy_ready": 0.48,
    "min_core_score": 0.52,
    "recommended_size_multiplier": 0.50,
    "recommended_entry_stage": "conservative",
    "confirm_add_size_multiplier": 1.00,
    "allow_energy_relief": True,
    "near_confirm_pair_gap": 0.12,
    "entry_style_hint": "probe_then_confirm",
    "note": "default_probe_temperament",
}

_SCENE_PROBE_PLAN = {
    "xau_upper_sell_probe": {
        "scene_id": "xau_upper_sell_probe",
        "promotion_bias": "fast_probe",
        "min_confirm_fake_gap": 0.01,
        "min_continue_fail_gap": -0.03,
        "min_persistence": 0.10,
        "min_belief": 0.47,
        "min_pair_gap": 0.08,
        "min_candidate_support": 0.22,
        "min_action_confirm_score": 0.18,
        "max_side_barrier": 0.48,
        "min_energy_ready": 0.40,
        "min_core_score": 0.40,
        "recommended_size_multiplier": 0.40,
        "recommended_entry_stage": "conservative",
        "confirm_add_size_multiplier": 0.95,
        "allow_energy_relief": True,
        "near_confirm_pair_gap": 0.06,
        "structural_relief_active": True,
        "structural_relief_candidate_support": 0.16,
        "structural_relief_pair_gap": 0.05,
        "structural_relief_action_confirm_score": 0.13,
        "structural_relief_confirm_fake_gap": -0.20,
        "structural_relief_wait_confirm_gap": -0.14,
        "structural_relief_continue_fail_gap": -0.30,
        "structural_relief_belief": 0.02,
        "structural_relief_persistence": 0.00,
        "structural_relief_max_side_barrier": 0.66,
    },
    "xau_second_support_buy_probe": {
        "scene_id": "xau_second_support_buy_probe",
        "promotion_bias": "aggressive_second_support",
        "min_confirm_fake_gap": -0.08,
        "min_continue_fail_gap": -0.16,
        "min_persistence": 0.04,
        "min_belief": 0.16,
        "min_pair_gap": 0.06,
        "min_candidate_support": 0.20,
        "min_action_confirm_score": 0.10,
        "max_side_barrier": 0.90,
        "min_energy_ready": 0.34,
        "min_core_score": 0.36,
        "recommended_size_multiplier": 0.60,
        "recommended_entry_stage": "balanced",
        "confirm_add_size_multiplier": 0.95,
        "allow_energy_relief": True,
        "near_confirm_pair_gap": 0.04,
        "structural_relief_active": True,
        "structural_relief_candidate_support": 0.44,
        "structural_relief_pair_gap": 0.18,
        "structural_relief_action_confirm_score": 0.07,
        "structural_relief_confirm_fake_gap": -0.27,
        "structural_relief_wait_confirm_gap": -0.23,
        "structural_relief_continue_fail_gap": -0.30,
        "structural_relief_belief": 0.015,
        "structural_relief_persistence": 0.00,
        "structural_relief_max_side_barrier": 0.90,
    },
    "btc_lower_buy_conservative_probe": {
        "scene_id": "btc_lower_buy_conservative_probe",
        "promotion_bias": "conservative_hold_first",
        "min_confirm_fake_gap": 0.03,
        "min_continue_fail_gap": -0.01,
        "min_persistence": 0.18,
        "min_belief": 0.50,
        "min_pair_gap": 0.18,
        "min_candidate_support": 0.34,
        "min_action_confirm_score": 0.24,
        "min_streak": 1,
        "max_side_barrier": 0.34,
        "min_energy_ready": 0.58,
        "min_core_score": 0.58,
        "recommended_size_multiplier": 0.35,
        "recommended_entry_stage": "conservative",
        "confirm_add_size_multiplier": 1.10,
        "allow_energy_relief": False,
        "near_confirm_pair_gap": 0.18,
        "structural_relief_active": True,
        "structural_relief_candidate_support": 0.85,
        "structural_relief_pair_gap": 0.13,
        "structural_relief_action_confirm_score": 0.20,
        "structural_relief_confirm_fake_gap": -0.10,
        "structural_relief_wait_confirm_gap": -0.05,
        "structural_relief_continue_fail_gap": -0.16,
        "structural_relief_belief": 0.03,
        "structural_relief_persistence": 0.03,
        "structural_relief_max_side_barrier": 0.22,
        "entry_style_hint": "conservative_lower_probe",
        "note": "btc_lower_buy_less_frequent_hold_longer",
    },
    "btc_upper_sell_probe": {
        "scene_id": "btc_upper_sell_probe",
        "promotion_bias": "measured_upper_sell",
        "min_confirm_fake_gap": -0.02,
        "min_continue_fail_gap": -0.08,
        "min_persistence": 0.08,
        "min_belief": 0.12,
        "min_pair_gap": 0.08,
        "min_candidate_support": 0.36,
        "min_action_confirm_score": 0.20,
        "min_streak": 1,
        "max_side_barrier": 0.42,
        "min_energy_ready": 0.46,
        "min_core_score": 0.46,
        "recommended_size_multiplier": 0.45,
        "recommended_entry_stage": "conservative",
        "confirm_add_size_multiplier": 0.95,
        "allow_energy_relief": True,
        "near_confirm_pair_gap": 0.04,
        "structural_relief_active": True,
        "structural_relief_candidate_support": 0.38,
        "structural_relief_pair_gap": 0.04,
        "structural_relief_action_confirm_score": 0.19,
        "structural_relief_confirm_fake_gap": -0.16,
        "structural_relief_wait_confirm_gap": -0.10,
        "structural_relief_continue_fail_gap": -0.22,
        "structural_relief_belief": 0.02,
        "structural_relief_persistence": 0.0,
        "structural_relief_max_side_barrier": 0.30,
        "entry_style_hint": "measured_upper_sell_probe",
        "note": "btc_upper_sell_can_promote_on_structural_upper_reject_before_belief_builds",
    },
    "nas_clean_confirm_probe": {
        "scene_id": "nas_clean_confirm_probe",
        "promotion_bias": "clean_confirm",
        "min_confirm_fake_gap": 0.02,
        "min_continue_fail_gap": -0.04,
        "min_persistence": 0.12,
        "min_belief": 0.28,
        "min_pair_gap": 0.12,
        "min_candidate_support": 0.18,
        "min_action_confirm_score": 0.14,
        "min_streak": 1,
        "max_side_barrier": 0.52,
        "min_energy_ready": 0.44,
        "min_core_score": 0.48,
        "recommended_size_multiplier": 0.45,
        "recommended_entry_stage": "balanced",
        "confirm_add_size_multiplier": 1.00,
        "allow_energy_relief": True,
        "near_confirm_pair_gap": 0.10,
        "structural_relief_active": True,
        "structural_relief_candidate_support": 0.11,
        "structural_relief_pair_gap": 0.17,
        "structural_relief_action_confirm_score": 0.08,
        "structural_relief_confirm_fake_gap": -0.26,
        "structural_relief_wait_confirm_gap": -0.21,
        "structural_relief_continue_fail_gap": -0.28,
        "structural_relief_belief": 0.01,
        "structural_relief_persistence": 0.0,
        "structural_relief_max_side_barrier": 0.56,
        "entry_style_hint": "clean_confirm_probe",
        "note": "nas_probe_prefers_clean_confirm_but_allows_near_confirm_native_relief",
    },
}

_SCENE_WAIT_TEMPERAMENT = {
    "default_edge_probe": {
        "enter_value_delta": 0.0,
        "wait_value_delta": 0.0,
        "prefer_confirm_release": False,
        "prefer_wait_lock": False,
    },
    "xau_upper_sell_probe": {
        "enter_value_delta": 0.10,
        "wait_value_delta": -0.05,
        "prefer_confirm_release": True,
        "prefer_wait_lock": False,
    },
    "xau_second_support_buy_probe": {
        "enter_value_delta": 0.14,
        "wait_value_delta": -0.08,
        "prefer_confirm_release": True,
        "prefer_wait_lock": False,
    },
}

_EDGE_EXECUTION_OVERRIDES = {
    ("XAUUSD", "range_lower_reversal_buy", "BUY"): {
        "active": True,
        "scene_id": "xau_lower_edge_to_edge_buy",
        "prefer_hold_to_opposite_edge": True,
        "mid_noise_hold_boost": 0.20,
        "premature_exit_relief": 0.18,
        "opposite_edge_exit_boost": 0.22,
        "recovery_support_boost": 0.16,
        "reason": "xau_lower_edge_hold_to_upper_exit",
    },
    ("BTCUSD", "range_lower_reversal_buy", "BUY"): {
        "active": True,
        "scene_id": "btc_lower_edge_noise_hold_buy",
        "prefer_hold_to_opposite_edge": True,
        "mid_noise_hold_boost": 0.20,
        "premature_exit_relief": 0.14,
        "opposite_edge_exit_boost": 0.10,
        "recovery_support_boost": 0.10,
        "reason": "btc_lower_edge_hold_through_noise",
    },
    ("NAS100", "range_lower_reversal_buy", "BUY"): {
        "active": True,
        "scene_id": "nas_lower_edge_clean_buy",
        "prefer_hold_to_opposite_edge": True,
        "mid_noise_hold_boost": 0.08,
        "premature_exit_relief": 0.06,
        "opposite_edge_exit_boost": 0.12,
        "recovery_support_boost": 0.06,
        "reason": "nas_lower_edge_clean_hold_to_upper_exit",
    },
}


def _pick_probe_scene(
    *,
    symbol: str,
    context_label: str,
    trigger_branch: str,
    probe_direction: str,
    second_support_relief: bool = False,
) -> str:
    symbol_u = canonical_symbol(symbol)
    context = _to_str(context_label, "UNRESOLVED").upper()
    branch = _to_str(trigger_branch).lower()
    direction = _to_str(probe_direction).upper()
    if symbol_u == "XAUUSD" and branch == "upper_reject" and direction == "SELL":
        return "xau_upper_sell_probe"
    if symbol_u == "XAUUSD" and branch == "lower_rebound" and direction == "BUY" and (
        context == "LOWER_EDGE" or second_support_relief
    ):
        return "xau_second_support_buy_probe"
    if symbol_u == "BTCUSD" and branch == "lower_rebound" and direction == "BUY":
        return "btc_lower_buy_conservative_probe"
    if symbol_u == "BTCUSD" and branch == "upper_reject" and direction == "SELL":
        return "btc_upper_sell_probe"
    if symbol_u == "NAS100" and branch in {"lower_rebound", "upper_reject"} and direction in {"BUY", "SELL"}:
        return "nas_clean_confirm_probe"
    return "default_edge_probe"


def resolve_probe_temperament(
    symbol: str,
    *,
    context_label: str,
    trigger_branch: str,
    probe_direction: str,
    second_support_relief: bool = False,
) -> dict[str, object]:
    symbol_u = canonical_symbol(symbol)
    scene_id = _pick_probe_scene(
        symbol=symbol_u,
        context_label=context_label,
        trigger_branch=trigger_branch,
        probe_direction=probe_direction,
        second_support_relief=second_support_relief,
    )
    payload = dict(_DEFAULT_PROBE_TEMPERAMENT)
    payload.update(_SCENE_PROBE_TEMPERAMENT.get(scene_id, {}))
    payload.update(
        {
            "symbol": symbol_u,
            "context_label": _to_str(context_label, "UNRESOLVED").upper(),
            "trigger_branch": _to_str(trigger_branch).lower(),
            "probe_direction": _to_str(probe_direction).upper(),
            "source_map_id": "shared_symbol_temperament_map_v1",
        }
    )
    return payload


def resolve_probe_plan_temperament(
    *,
    symbol: str,
    intended_action: str,
    trigger_branch: str,
    probe_candidate: dict | None = None,
    observe_metadata: dict | None = None,
) -> dict[str, object]:
    candidate = dict(probe_candidate or {})
    observe_meta = dict(observe_metadata or {})
    candidate_temperament = candidate.get("symbol_probe_temperament_v1", {})
    candidate_temperament = dict(candidate_temperament or {}) if isinstance(candidate_temperament, dict) else {}
    scene_id = _to_str(candidate_temperament.get("scene_id", "")).lower()
    symbol_u = canonical_symbol(symbol)
    action_u = _to_str(intended_action).upper()
    trigger = _to_str(trigger_branch).lower()
    if not scene_id:
        if symbol_u == "XAUUSD" and action_u == "SELL" and trigger == "upper_reject":
            scene_id = "xau_upper_sell_probe"
        elif symbol_u == "XAUUSD" and action_u == "BUY" and trigger == "lower_rebound" and bool(
            observe_meta.get("xau_second_support_probe_relief", False)
        ):
            scene_id = "xau_second_support_buy_probe"
        elif symbol_u == "BTCUSD" and action_u == "BUY" and trigger == "lower_rebound":
            scene_id = "btc_lower_buy_conservative_probe"
        elif symbol_u == "BTCUSD" and action_u == "SELL" and trigger == "upper_reject":
            scene_id = "btc_upper_sell_probe"
        elif symbol_u == "NAS100" and action_u in {"BUY", "SELL"} and trigger in {"lower_rebound", "upper_reject"}:
            scene_id = "nas_clean_confirm_probe"
        else:
            scene_id = _pick_probe_scene(
                symbol=symbol_u,
                context_label=_to_str(candidate.get("context_label", candidate.get("edge_context_label", ""))),
                trigger_branch=trigger,
                probe_direction=action_u,
                second_support_relief=bool(observe_meta.get("xau_second_support_probe_relief", False)),
            )
    payload = dict(_DEFAULT_PROBE_PLAN)
    payload.update(_SCENE_PROBE_PLAN.get(scene_id, {}))
    if candidate_temperament:
        payload["entry_style_hint"] = _to_str(
            candidate_temperament.get("entry_style_hint", payload.get("entry_style_hint", "probe_then_confirm"))
        )
        payload["note"] = _to_str(candidate_temperament.get("note", payload.get("note", "default_probe_temperament")))
    payload.update(
        {
            "scene_id": scene_id or "default_edge_probe",
            "symbol": symbol_u,
            "intended_action": action_u,
            "trigger_branch": trigger,
            "contract_version": "symbol_probe_plan_temperament_v1",
            "source_map_id": "shared_symbol_temperament_map_v1",
        }
    )
    return payload


def resolve_wait_probe_temperament(
    scene_id: str,
    *,
    ready_for_entry: bool = False,
) -> dict[str, object]:
    scene = _to_str(scene_id).lower() or "default_edge_probe"
    payload = dict(_SCENE_WAIT_TEMPERAMENT.get(scene, _SCENE_WAIT_TEMPERAMENT["default_edge_probe"]))
    if scene == "btc_lower_buy_conservative_probe":
        if ready_for_entry:
            payload.update(
                {
                    "enter_value_delta": 0.04,
                    "wait_value_delta": 0.0,
                    "prefer_confirm_release": False,
                    "prefer_wait_lock": False,
                }
            )
        else:
            payload.update(
                {
                    "enter_value_delta": -0.10,
                    "wait_value_delta": 0.16,
                    "prefer_confirm_release": False,
                    "prefer_wait_lock": True,
                }
            )
    elif scene == "nas_clean_confirm_probe":
        if ready_for_entry:
            payload.update(
                {
                    "enter_value_delta": 0.05,
                    "wait_value_delta": -0.02,
                    "prefer_confirm_release": True,
                    "prefer_wait_lock": False,
                }
            )
        else:
            payload.update(
                {
                    "enter_value_delta": -0.03,
                    "wait_value_delta": 0.06,
                    "prefer_confirm_release": False,
                    "prefer_wait_lock": False,
                }
            )
    elif scene == "btc_upper_sell_probe":
        if ready_for_entry:
            payload.update(
                {
                    "enter_value_delta": 0.06,
                    "wait_value_delta": -0.03,
                    "prefer_confirm_release": True,
                    "prefer_wait_lock": False,
                }
            )
        else:
            payload.update(
                {
                    "enter_value_delta": 0.01,
                    "wait_value_delta": 0.02,
                    "prefer_confirm_release": False,
                    "prefer_wait_lock": False,
                }
            )
    payload.update(
        {
            "contract_version": "symbol_probe_wait_temperament_v1",
            "scene_id": scene,
            "ready_for_entry": bool(ready_for_entry),
            "source_map_id": "shared_symbol_temperament_map_v1",
        }
    )
    return payload


def resolve_edge_execution_overrides(
    *,
    symbol: str = "",
    entry_setup_id: str = "",
    entry_direction: str = "",
) -> dict[str, object]:
    symbol_u = canonical_symbol(symbol)
    setup_id = _to_str(entry_setup_id).lower()
    direction = _to_str(entry_direction).upper()
    payload = dict(
        _EDGE_EXECUTION_OVERRIDES.get(
            (symbol_u, setup_id, direction),
            {
                "active": False,
                "scene_id": "",
                "prefer_hold_to_opposite_edge": False,
                "mid_noise_hold_boost": 0.0,
                "premature_exit_relief": 0.0,
                "opposite_edge_exit_boost": 0.0,
                "recovery_support_boost": 0.0,
                "reason": "",
            },
        )
    )
    payload.update(
        {
            "contract_version": "symbol_edge_execution_overrides_v1",
            "symbol": symbol_u,
            "entry_setup_id": setup_id,
            "entry_direction": direction,
            "source_map_id": "shared_symbol_temperament_map_v1",
        }
    )
    return payload
