from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from typing import Any

import pandas as pd
from backend.services.symbol_temperament import (
    canonical_symbol as normalize_canonical_symbol,
    resolve_probe_scene_direction,
)
from backend.trading.chart_flow_policy import build_common_expression_policy_v1


DEFAULT_LATE_DISPLAY_SUPPRESS_GUARDS_V1 = frozenset(
    {
        "clustered_entry_price_zone",
        "pyramid_not_progressed",
        "pyramid_not_in_drawdown",
        "range_lower_buy_requires_lower_edge",
        "range_lower_buy_conflict_blocked",
        "max_positions_reached",
    }
)

DISPLAY_REPEAT_THRESHOLDS_V1 = {
    "single": 0.70,
    "double": 0.80,
    "triple": 0.90,
}

DISPLAY_IMPORTANCE_SCORE_FLOORS_V1 = {
    "nas_medium": 0.82,
    "nas_high": 0.91,
}

_COMMON_EXPRESSION_POLICY_V1 = build_common_expression_policy_v1()


def _common_expression_policy_v1() -> dict[str, Any]:
    policy = _COMMON_EXPRESSION_POLICY_V1
    return dict(policy) if isinstance(policy, Mapping) else {}


def _display_modifier_policy_v1() -> dict[str, Any]:
    section = _common_expression_policy_v1().get("display_modifier", {})
    return dict(section) if isinstance(section, Mapping) else {}


def _display_modifier_repeat_thresholds_v1() -> dict[str, float]:
    section = _mapping_from_jsonish(_display_modifier_policy_v1().get("repeat_thresholds"))
    return {
        "single": _to_float(section.get("single", DISPLAY_REPEAT_THRESHOLDS_V1["single"]), default=DISPLAY_REPEAT_THRESHOLDS_V1["single"]),
        "double": _to_float(section.get("double", DISPLAY_REPEAT_THRESHOLDS_V1["double"]), default=DISPLAY_REPEAT_THRESHOLDS_V1["double"]),
        "triple": _to_float(section.get("triple", DISPLAY_REPEAT_THRESHOLDS_V1["triple"]), default=DISPLAY_REPEAT_THRESHOLDS_V1["triple"]),
    }


def _display_modifier_importance_score_floors_v1() -> dict[str, float]:
    section = _mapping_from_jsonish(_display_modifier_policy_v1().get("importance_score_floors"))
    return {
        "medium": _to_float(section.get("medium", DISPLAY_IMPORTANCE_SCORE_FLOORS_V1["nas_medium"]), default=DISPLAY_IMPORTANCE_SCORE_FLOORS_V1["nas_medium"]),
        "high": _to_float(section.get("high", DISPLAY_IMPORTANCE_SCORE_FLOORS_V1["nas_high"]), default=DISPLAY_IMPORTANCE_SCORE_FLOORS_V1["nas_high"]),
    }


def _display_modifier_stage_score_policy_v1(stage: str) -> dict[str, float]:
    stage_u = str(stage or "").strip().lower()
    defaults = {
        "ready": {"base": 0.92, "cap": 0.98, "level_start": 8, "level_scale": 0.02},
        "probe": {"base": 0.82, "cap": 0.89, "level_start": 6, "level_scale": 0.04},
        "observe": {"base": 0.72, "cap": 0.79, "level_start": 4, "level_scale": 0.03},
        "blocked": {"base": 0.71, "cap": 0.79, "level_start": 3, "level_scale": 0.02},
    }
    fallback = defaults.get(stage_u, {})
    section = _mapping_from_jsonish(_mapping_from_jsonish(_display_modifier_policy_v1().get("stage_score")).get(stage_u))
    return {
        "base": _to_float(section.get("base", fallback.get("base", 0.0)), default=fallback.get("base", 0.0)),
        "cap": _to_float(section.get("cap", fallback.get("cap", 0.0)), default=fallback.get("cap", 0.0)),
        "level_start": _to_float(section.get("level_start", fallback.get("level_start", 0.0)), default=fallback.get("level_start", 0.0)),
        "level_scale": _to_float(section.get("level_scale", fallback.get("level_scale", 0.0)), default=fallback.get("level_scale", 0.0)),
    }


def _display_strength_level_from_modifier_v1(
    *,
    stage: str,
    display_ready: bool,
    blocked_by: str,
    candidate_support: float,
    pair_gap: float,
) -> int:
    stage_u = str(stage or "").upper().strip()
    strength_policy = _mapping_from_jsonish(_display_modifier_policy_v1().get("strength_level"))
    if stage_u == "READY":
        return int(_to_float(strength_policy.get("ready", 8), default=8.0))
    if stage_u == "PROBE":
        probe_policy = _mapping_from_jsonish(strength_policy.get("probe"))
        probe_high = int(_to_float(probe_policy.get("high", 7), default=7.0))
        probe_base = int(_to_float(probe_policy.get("base", 6), default=6.0))
        support_min = _to_float(probe_policy.get("candidate_support_min", 0.40), default=0.40)
        pair_gap_min = _to_float(probe_policy.get("pair_gap_min", 0.18), default=0.18)
        return probe_high if (candidate_support >= support_min or pair_gap >= pair_gap_min) else probe_base
    if stage_u == "OBSERVE":
        observe_policy = _mapping_from_jsonish(strength_policy.get("observe"))
        if str(blocked_by or "").strip():
            return int(_to_float(observe_policy.get("blocked", 5), default=5.0))
        return int(_to_float(observe_policy.get("default", 4), default=4.0))
    if stage_u == "BLOCKED":
        blocked_policy = _mapping_from_jsonish(strength_policy.get("blocked"))
        if display_ready:
            return int(_to_float(blocked_policy.get("visible", 5), default=5.0))
        return int(_to_float(blocked_policy.get("hidden", 3), default=3.0))
    return 0


def _apply_state_aware_display_modifier_v1(
    *,
    symbol: str,
    candidate: bool,
    display_ready: bool,
    entry_ready: bool,
    side: str,
    stage: str,
    reason: str,
    probe_scene_id: str,
    blocked_by: str,
    action_none_reason: str,
    display_importance_tier: str,
    display_importance_source_reason: str,
    candidate_support: float,
    pair_gap: float,
    bridge_act_vs_wait_bias: float,
    bridge_false_break_risk: float,
    bridge_awareness_keep_allowed: bool,
) -> dict[str, Any]:
    symbol_u = str(symbol or "").upper().strip()
    side_u = str(side or "").upper().strip()
    stage_u = str(stage or "").upper().strip()
    reason_u = str(reason or "").strip().lower()
    probe_scene_u = str(probe_scene_id or "").strip()
    blocked_u = str(blocked_by or "").strip()
    action_none_u = str(action_none_reason or "").strip()
    importance_tier_u = str(display_importance_tier or "").strip().lower()
    importance_source_u = str(display_importance_source_reason or "").strip().lower()

    baseline_level = _display_strength_level_from_modifier_v1(
        stage=stage_u,
        display_ready=bool(display_ready),
        blocked_by=blocked_u,
        candidate_support=float(candidate_support or 0.0),
        pair_gap=float(pair_gap or 0.0),
    )
    baseline_score = _display_score_from_effective_state(
        candidate=bool(candidate),
        display_ready=bool(display_ready),
        entry_ready=bool(entry_ready),
        side=side_u,
        stage=stage_u,
        level=int(baseline_level or 0),
    )
    baseline_score = _apply_display_importance_floor(
        baseline_score,
        display_ready=bool(display_ready),
        importance_tier=importance_tier_u,
    )

    effective_display_ready = bool(display_ready)
    effective_stage = str(stage_u or "")
    modifier_primary_reason = ""
    modifier_reason_codes: list[str] = []
    modifier_stage_adjustment = "none"
    chart_event_kind_hint = ""
    chart_display_mode = ""
    chart_display_reason = ""

    awareness_policy = _mapping_from_jsonish(_mapping_from_jsonish(_display_modifier_policy_v1().get("bridge")).get("awareness_keep"))
    blocked_allow = {
        str(item or "").strip()
        for item in list(awareness_policy.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    action_none_allow = {
        str(item or "").strip()
        for item in list(awareness_policy.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    awareness_enabled = bool(awareness_policy.get("enabled", True))
    restore_stage = str(awareness_policy.get("restore_stage", "OBSERVE") or "OBSERVE").upper().strip()
    min_bias = _to_float(awareness_policy.get("minimum_act_vs_wait_bias", 0.46), default=0.46)
    max_risk = _to_float(awareness_policy.get("maximum_false_break_risk", 0.78), default=0.78)
    soft_wait_awareness_block = bool(blocked_u in blocked_allow or action_none_u in action_none_allow)
    awareness_source_present = bool(display_importance_source_reason)
    if (
        awareness_enabled
        and candidate
        and not entry_ready
        and not effective_display_ready
        and side_u in {"BUY", "SELL"}
        and soft_wait_awareness_block
        and awareness_source_present
        and bridge_awareness_keep_allowed
        and bridge_act_vs_wait_bias >= min_bias
        and bridge_false_break_risk <= max_risk
    ):
        effective_display_ready = True
        if effective_stage in {"", "BLOCKED"}:
            previous_stage = str(effective_stage or "NONE").lower()
            effective_stage = restore_stage
            modifier_stage_adjustment = f"{previous_stage}_to_{str(restore_stage).lower()}"
        else:
            modifier_stage_adjustment = "visibility_restore"
        modifier_primary_reason = "bf1_awareness_keep"
        modifier_reason_codes.append(modifier_primary_reason)

    soft_caps_policy = _mapping_from_jsonish(_display_modifier_policy_v1().get("soft_caps"))
    conflict_wait_hide = _mapping_from_jsonish(soft_caps_policy.get("conflict_wait_hide"))
    conflict_reason_prefixes = tuple(
        str(item or "").strip().lower()
        for item in list(conflict_wait_hide.get("reason_prefixes", []) or [])
        if str(item or "").strip()
    )
    conflict_blocked_allow = {
        str(item or "").strip()
        for item in list(conflict_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    conflict_action_allow = {
        str(item or "").strip()
        for item in list(conflict_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    conflict_soft_cap_applies = bool(
        bool(conflict_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and any(reason_u.startswith(prefix) for prefix in conflict_reason_prefixes)
        and blocked_u in conflict_blocked_allow
        and action_none_u in conflict_action_allow
        and (
            not bool(conflict_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
    )
    if conflict_soft_cap_applies and bool(conflict_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "conflict_wait_hide"
        modifier_reason_codes.append("conflict_wait_hide")
        modifier_stage_adjustment = "visibility_suppressed"

    structural_wait_hide = _mapping_from_jsonish(soft_caps_policy.get("structural_wait_hide_without_probe"))
    structural_side_allow = {
        str(item or "").strip().upper()
        for item in list(structural_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    structural_observe_allow = {
        str(item or "").strip()
        for item in list(structural_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    structural_blocked_allow = {
        str(item or "").strip()
        for item in list(structural_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    structural_action_allow = {
        str(item or "").strip()
        for item in list(structural_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    structural_soft_cap_applies = bool(
        bool(structural_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not structural_side_allow or side_u in structural_side_allow)
        and reason_u in structural_observe_allow
        and blocked_u in structural_blocked_allow
        and action_none_u in structural_action_allow
        and (
            not bool(structural_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(structural_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if structural_soft_cap_applies and bool(structural_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "structural_wait_hide_without_probe"
        modifier_reason_codes.append("structural_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    sell_outer_band_wait_hide = _mapping_from_jsonish(soft_caps_policy.get("sell_outer_band_wait_hide_without_probe"))
    sell_outer_band_side_allow = {
        str(item or "").strip().upper()
        for item in list(sell_outer_band_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    sell_outer_band_observe_allow = {
        str(item or "").strip()
        for item in list(sell_outer_band_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    sell_outer_band_blocked_allow = {
        str(item or "").strip()
        for item in list(sell_outer_band_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    sell_outer_band_action_allow = {
        str(item or "").strip()
        for item in list(sell_outer_band_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    sell_outer_band_soft_cap_applies = bool(
        bool(sell_outer_band_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not sell_outer_band_side_allow or side_u in sell_outer_band_side_allow)
        and reason_u in sell_outer_band_observe_allow
        and blocked_u in sell_outer_band_blocked_allow
        and action_none_u in sell_outer_band_action_allow
        and (
            not bool(sell_outer_band_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(sell_outer_band_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if sell_outer_band_soft_cap_applies and bool(sell_outer_band_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "sell_outer_band_wait_hide_without_probe"
        modifier_reason_codes.append("sell_outer_band_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    nas_sell_middle_anchor_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("nas_sell_middle_anchor_wait_hide_without_probe")
    )
    nas_sell_middle_anchor_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(nas_sell_middle_anchor_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    nas_sell_middle_anchor_side_allow = {
        str(item or "").strip().upper()
        for item in list(nas_sell_middle_anchor_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    nas_sell_middle_anchor_observe_allow = {
        str(item or "").strip()
        for item in list(nas_sell_middle_anchor_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    nas_sell_middle_anchor_blocked_allow = {
        str(item or "").strip()
        for item in list(nas_sell_middle_anchor_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    nas_sell_middle_anchor_action_allow = {
        str(item or "").strip()
        for item in list(nas_sell_middle_anchor_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    nas_sell_middle_anchor_soft_cap_applies = bool(
        bool(nas_sell_middle_anchor_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not nas_sell_middle_anchor_symbol_allow or symbol_u in nas_sell_middle_anchor_symbol_allow)
        and (not nas_sell_middle_anchor_side_allow or side_u in nas_sell_middle_anchor_side_allow)
        and reason_u in nas_sell_middle_anchor_observe_allow
        and blocked_u in nas_sell_middle_anchor_blocked_allow
        and action_none_u in nas_sell_middle_anchor_action_allow
        and (
            not bool(nas_sell_middle_anchor_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(nas_sell_middle_anchor_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if nas_sell_middle_anchor_soft_cap_applies and bool(nas_sell_middle_anchor_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "nas_sell_middle_anchor_wait_hide_without_probe"
        modifier_reason_codes.append("nas_sell_middle_anchor_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    btc_sell_middle_anchor_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("btc_sell_middle_anchor_wait_hide_without_probe")
    )
    btc_sell_middle_anchor_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(btc_sell_middle_anchor_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    btc_sell_middle_anchor_side_allow = {
        str(item or "").strip().upper()
        for item in list(btc_sell_middle_anchor_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    btc_sell_middle_anchor_observe_allow = {
        str(item or "").strip()
        for item in list(btc_sell_middle_anchor_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    btc_sell_middle_anchor_blocked_allow = {
        str(item or "").strip()
        for item in list(btc_sell_middle_anchor_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    btc_sell_middle_anchor_action_allow = {
        str(item or "").strip()
        for item in list(btc_sell_middle_anchor_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    btc_sell_middle_anchor_soft_cap_applies = bool(
        bool(btc_sell_middle_anchor_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not btc_sell_middle_anchor_symbol_allow or symbol_u in btc_sell_middle_anchor_symbol_allow)
        and (not btc_sell_middle_anchor_side_allow or side_u in btc_sell_middle_anchor_side_allow)
        and reason_u in btc_sell_middle_anchor_observe_allow
        and blocked_u in btc_sell_middle_anchor_blocked_allow
        and action_none_u in btc_sell_middle_anchor_action_allow
        and (
            not bool(btc_sell_middle_anchor_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(btc_sell_middle_anchor_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if btc_sell_middle_anchor_soft_cap_applies and bool(
        btc_sell_middle_anchor_wait_hide.get("suppress_display", True)
    ):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "btc_sell_middle_anchor_wait_hide_without_probe"
        modifier_reason_codes.append("btc_sell_middle_anchor_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    nas_upper_reclaim_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("nas_upper_reclaim_wait_hide_without_probe")
    )
    nas_upper_reclaim_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_reclaim_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reclaim_side_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_reclaim_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reclaim_observe_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reclaim_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reclaim_blocked_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reclaim_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reclaim_action_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reclaim_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reclaim_soft_cap_applies = bool(
        bool(nas_upper_reclaim_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not nas_upper_reclaim_symbol_allow or symbol_u in nas_upper_reclaim_symbol_allow)
        and (not nas_upper_reclaim_side_allow or side_u in nas_upper_reclaim_side_allow)
        and reason_u in nas_upper_reclaim_observe_allow
        and blocked_u in nas_upper_reclaim_blocked_allow
        and action_none_u in nas_upper_reclaim_action_allow
        and (
            not bool(nas_upper_reclaim_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(nas_upper_reclaim_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if nas_upper_reclaim_soft_cap_applies and bool(nas_upper_reclaim_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "nas_upper_reclaim_wait_hide_without_probe"
        modifier_reason_codes.append("nas_upper_reclaim_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    xau_upper_reclaim_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("xau_upper_reclaim_wait_hide_without_probe")
    )
    xau_upper_reclaim_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(xau_upper_reclaim_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    xau_upper_reclaim_side_allow = {
        str(item or "").strip().upper()
        for item in list(xau_upper_reclaim_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    xau_upper_reclaim_observe_allow = {
        str(item or "").strip()
        for item in list(xau_upper_reclaim_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    xau_upper_reclaim_blocked_allow = {
        str(item or "").strip()
        for item in list(xau_upper_reclaim_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    xau_upper_reclaim_action_allow = {
        str(item or "").strip()
        for item in list(xau_upper_reclaim_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    xau_upper_reclaim_soft_cap_applies = bool(
        bool(xau_upper_reclaim_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not xau_upper_reclaim_symbol_allow or symbol_u in xau_upper_reclaim_symbol_allow)
        and (not xau_upper_reclaim_side_allow or side_u in xau_upper_reclaim_side_allow)
        and reason_u in xau_upper_reclaim_observe_allow
        and blocked_u in xau_upper_reclaim_blocked_allow
        and action_none_u in xau_upper_reclaim_action_allow
        and (
            not bool(xau_upper_reclaim_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(xau_upper_reclaim_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if xau_upper_reclaim_soft_cap_applies and bool(xau_upper_reclaim_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "xau_upper_reclaim_wait_hide_without_probe"
        modifier_reason_codes.append("xau_upper_reclaim_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    nas_upper_reject_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("nas_upper_reject_wait_hide_without_probe")
    )
    nas_upper_reject_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_reject_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reject_side_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_reject_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reject_observe_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reject_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reject_blocked_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reject_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reject_action_allow = {
        str(item or "").strip()
        for item in list(nas_upper_reject_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_reject_soft_cap_applies = bool(
        bool(nas_upper_reject_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not nas_upper_reject_symbol_allow or symbol_u in nas_upper_reject_symbol_allow)
        and (not nas_upper_reject_side_allow or side_u in nas_upper_reject_side_allow)
        and reason_u in nas_upper_reject_observe_allow
        and blocked_u in nas_upper_reject_blocked_allow
        and action_none_u in nas_upper_reject_action_allow
        and (
            not bool(nas_upper_reject_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(nas_upper_reject_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if nas_upper_reject_soft_cap_applies and bool(nas_upper_reject_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "nas_upper_reject_wait_hide_without_probe"
        modifier_reason_codes.append("nas_upper_reject_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    nas_upper_break_fail_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("nas_upper_break_fail_wait_hide_without_probe")
    )
    nas_upper_break_fail_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_break_fail_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_break_fail_side_allow = {
        str(item or "").strip().upper()
        for item in list(nas_upper_break_fail_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_break_fail_observe_allow = {
        str(item or "").strip()
        for item in list(nas_upper_break_fail_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_break_fail_blocked_allow = {
        str(item or "").strip()
        for item in list(nas_upper_break_fail_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_break_fail_action_allow = {
        str(item or "").strip()
        for item in list(nas_upper_break_fail_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    nas_upper_break_fail_soft_cap_applies = bool(
        bool(nas_upper_break_fail_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not nas_upper_break_fail_symbol_allow or symbol_u in nas_upper_break_fail_symbol_allow)
        and (not nas_upper_break_fail_side_allow or side_u in nas_upper_break_fail_side_allow)
        and reason_u in nas_upper_break_fail_observe_allow
        and blocked_u in nas_upper_break_fail_blocked_allow
        and action_none_u in nas_upper_break_fail_action_allow
        and (
            not bool(nas_upper_break_fail_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not bool(nas_upper_break_fail_wait_hide.get("require_importance_source_absent", True))
            or not str(display_importance_source_reason or "").strip()
        )
    )
    if nas_upper_break_fail_soft_cap_applies and bool(nas_upper_break_fail_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "nas_upper_break_fail_wait_hide_without_probe"
        modifier_reason_codes.append("nas_upper_break_fail_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    btc_lower_rebound_wait_hide = _mapping_from_jsonish(
        soft_caps_policy.get("btc_lower_rebound_forecast_wait_hide_without_probe")
    )
    btc_lower_rebound_symbol_allow = {
        str(item or "").strip().upper()
        for item in list(btc_lower_rebound_wait_hide.get("symbol_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_side_allow = {
        str(item or "").strip().upper()
        for item in list(btc_lower_rebound_wait_hide.get("side_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_observe_allow = {
        str(item or "").strip()
        for item in list(btc_lower_rebound_wait_hide.get("observe_reason_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_blocked_allow = {
        str(item or "").strip()
        for item in list(btc_lower_rebound_wait_hide.get("blocked_by_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_action_allow = {
        str(item or "").strip()
        for item in list(btc_lower_rebound_wait_hide.get("action_none_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_importance_allow = {
        str(item or "").strip().lower()
        for item in list(btc_lower_rebound_wait_hide.get("importance_source_allow", []) or [])
        if str(item or "").strip()
    }
    btc_lower_rebound_soft_cap_applies = bool(
        bool(btc_lower_rebound_wait_hide.get("enabled", True))
        and candidate
        and effective_display_ready
        and not entry_ready
        and (not btc_lower_rebound_symbol_allow or symbol_u in btc_lower_rebound_symbol_allow)
        and (not btc_lower_rebound_side_allow or side_u in btc_lower_rebound_side_allow)
        and reason_u in btc_lower_rebound_observe_allow
        and blocked_u in btc_lower_rebound_blocked_allow
        and action_none_u in btc_lower_rebound_action_allow
        and (
            not bool(btc_lower_rebound_wait_hide.get("require_probe_scene_absent", True))
            or not probe_scene_u
        )
        and (
            not btc_lower_rebound_importance_allow
            or importance_source_u in btc_lower_rebound_importance_allow
        )
    )
    if btc_lower_rebound_soft_cap_applies and bool(btc_lower_rebound_wait_hide.get("suppress_display", True)):
        effective_display_ready = False
        if not modifier_primary_reason:
            modifier_primary_reason = "btc_lower_rebound_forecast_wait_hide_without_probe"
        modifier_reason_codes.append("btc_lower_rebound_forecast_wait_hide_without_probe")
        modifier_stage_adjustment = "visibility_suppressed"

    chart_wait_reliefs = _mapping_from_jsonish(_display_modifier_policy_v1().get("chart_wait_reliefs"))
    for relief_policy in chart_wait_reliefs.values():
        relief = _mapping_from_jsonish(relief_policy)
        relief_restore_hidden_display = bool(relief.get("restore_hidden_display", False))
        relief_restore_stage = str(relief.get("restore_stage", "OBSERVE") or "OBSERVE").upper().strip()
        symbol_allow = {
            str(item or "").strip().upper()
            for item in list(relief.get("symbol_allow", []) or [])
            if str(item or "").strip()
        }
        side_allow = {
            str(item or "").strip().upper()
            for item in list(relief.get("side_allow", []) or [])
            if str(item or "").strip()
        }
        stage_allow = {
            str(item or "").strip().upper()
            for item in list(relief.get("stage_allow", []) or [])
            if str(item or "").strip()
        }
        stage_match = str(effective_stage or stage_u or "").upper().strip()
        observe_allow = {
            str(item or "").strip()
            for item in list(relief.get("observe_reason_allow", []) or [])
            if str(item or "").strip()
        }
        blocked_allow = {
            str(item or "").strip()
            for item in list(relief.get("blocked_by_allow", []) or [])
            if str(item or "").strip()
        }
        probe_scene_allow = {
            str(item or "").strip()
            for item in list(relief.get("probe_scene_allow", []) or [])
            if str(item or "").strip()
        }
        action_allow = {
            str(item or "").strip()
            for item in list(relief.get("action_none_allow", []) or [])
            if str(item or "").strip()
        }
        relief_applies = bool(
            bool(relief.get("enabled", True))
            and candidate
            and not entry_ready
            and (effective_display_ready or relief_restore_hidden_display)
            and (not symbol_allow or symbol_u in symbol_allow)
            and (not side_allow or side_u in side_allow)
            and (not stage_allow or stage_match in stage_allow)
            and (not observe_allow or reason_u in observe_allow)
            and (not blocked_allow or blocked_u in blocked_allow)
            and (not probe_scene_allow or probe_scene_u in probe_scene_allow)
            and (not action_allow or action_none_u in action_allow)
            and (
                not bool(relief.get("require_probe_scene_present", False))
                or bool(probe_scene_u)
            )
            and (
                not bool(relief.get("require_probe_scene_absent", False))
                or not probe_scene_u
            )
        )
        if not relief_applies:
            continue
        if relief_restore_hidden_display and not effective_display_ready:
            effective_display_ready = True
            if effective_stage in {"", "BLOCKED"}:
                previous_stage = str(effective_stage or "NONE").lower()
                effective_stage = relief_restore_stage or "OBSERVE"
                if not modifier_stage_adjustment or modifier_stage_adjustment == "none":
                    modifier_stage_adjustment = f"{previous_stage}_to_{str(effective_stage).lower()}"
            elif not modifier_stage_adjustment or modifier_stage_adjustment == "none":
                modifier_stage_adjustment = "visibility_restore"
            if not modifier_primary_reason:
                modifier_primary_reason = "chart_wait_visibility_restore"
            if "chart_wait_visibility_restore" not in modifier_reason_codes:
                modifier_reason_codes.append("chart_wait_visibility_restore")
        chart_event_kind_hint = str(relief.get("event_kind_hint", "WAIT") or "WAIT").upper().strip()
        chart_display_mode = str(relief.get("display_mode", "wait_check_repeat") or "wait_check_repeat").strip()
        chart_display_reason = str(relief.get("display_reason", "") or "").strip()
        break

    effective_level = _display_strength_level_from_modifier_v1(
        stage=effective_stage,
        display_ready=bool(effective_display_ready),
        blocked_by=blocked_u,
        candidate_support=float(candidate_support or 0.0),
        pair_gap=float(pair_gap or 0.0),
    )
    effective_score = _display_score_from_effective_state(
        candidate=bool(candidate),
        display_ready=bool(effective_display_ready),
        entry_ready=bool(entry_ready),
        side=side_u,
        stage=effective_stage,
        level=int(effective_level or 0),
    )
    effective_score = _apply_display_importance_floor(
        effective_score,
        display_ready=bool(effective_display_ready),
        importance_tier=importance_tier_u,
    )
    return {
        "modifier_contract_version": str(_display_modifier_policy_v1().get("contract_version", "common_state_aware_display_modifier_v1") or "common_state_aware_display_modifier_v1"),
        "modifier_applied": bool(modifier_primary_reason),
        "modifier_primary_reason": str(modifier_primary_reason or ""),
        "modifier_reason_codes": list(modifier_reason_codes),
        "modifier_stage_adjustment": str(modifier_stage_adjustment or "none"),
        "modifier_score_delta": round(float(effective_score - baseline_score), 4),
        "effective_display_ready": bool(effective_display_ready),
        "effective_stage": str(effective_stage or ""),
        "effective_display_strength_level": int(effective_level or 0),
        "effective_display_score": float(effective_score),
        "effective_display_repeat_count": int(_display_repeat_count(effective_score)),
        "chart_event_kind_hint": str(chart_event_kind_hint or ""),
        "chart_display_mode": str(chart_display_mode or ""),
        "chart_display_reason": str(chart_display_reason or ""),
    }


def _first_directional_value(*values: object) -> str:
    for value in values:
        direction = str(value or "").upper()
        if direction in {"BUY", "SELL"}:
            return direction
    return ""


def _directional_side_from_policy(value: object) -> str:
    policy = str(value or "").upper()
    if policy == "BUY_ONLY":
        return "BUY"
    if policy == "SELL_ONLY":
        return "SELL"
    return ""


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        converted = float(pd.to_numeric(value, errors="coerce"))
    except Exception:
        return float(default)
    if pd.isna(converted):
        return float(default)
    return float(converted)


def _mapping_from_jsonish(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}


def _display_repeat_count(display_score: float) -> int:
    score_f = max(0.0, min(1.0, float(display_score or 0.0)))
    thresholds = _display_modifier_repeat_thresholds_v1()
    if score_f >= float(thresholds["triple"]):
        return 3
    if score_f >= float(thresholds["double"]):
        return 2
    if score_f >= float(thresholds["single"]):
        return 1
    return 0


_DISPLAY_LOWER_REBOUND_REASONS_V1 = {
    "lower_rebound_probe_observe",
    "lower_rebound_confirm",
}
_DISPLAY_STRUCTURAL_OBSERVE_REASONS_V1 = {
    "outer_band_reversal_support_required_observe",
    "middle_sr_anchor_required_observe",
}
_DISPLAY_UPPER_REJECT_REASONS_V1 = {
    "upper_reject_probe_observe",
    "upper_reject_confirm",
    "upper_reject_mixed_confirm",
    "upper_break_fail_confirm",
}
_DISPLAY_UPPER_REJECT_CORE_REASONS_V1 = {
    "upper_reject_confirm",
    "upper_break_fail_confirm",
}
_DISPLAY_IMPORTANCE_REASON_ALIAS_V1 = {
    "NAS100": {
        "lower_recovery_start": "nas_lower_recovery_start",
        "breakout_reclaim_confirm": "nas_breakout_reclaim_confirm",
        "structural_rebound": "nas_structural_rebound",
        "upper_support_awareness": "nas_upper_support_awareness",
    },
    "XAUUSD": {
        "lower_recovery_start": "xau_lower_recovery_start",
        "structural_rebound": "xau_second_support_reclaim",
        "upper_reject_core": "xau_upper_reject_core",
        "upper_reject_development": "xau_upper_reject_development",
    },
    "BTCUSD": {
        "lower_recovery_start": "btc_lower_recovery_start",
        "breakout_reclaim_confirm": "btc_breakout_reclaim_confirm",
        "structural_rebound": "btc_structural_rebound",
    },
}


def _display_importance_context_v1(*, box_state: str, bb_state: str) -> dict[str, bool]:
    box_state_u = str(box_state or "").upper().strip()
    bb_state_u = str(bb_state or "").upper().strip()
    lower_deep = bool(box_state_u == "BELOW" or bb_state_u in {"LOWER_EDGE", "BREAKDOWN"})
    lower_context = bool(
        box_state_u in {"BELOW", "LOWER", "LOWER_EDGE"}
        or bb_state_u in {"LOWER_EDGE", "BREAKDOWN"}
    )
    middle_context = bool(
        box_state_u in {"MIDDLE", "MID"}
        or bb_state_u in {"MID", "MIDDLE"}
    )
    upper_context = bool(
        box_state_u in {"UPPER", "UPPER_EDGE", "ABOVE"}
        or bb_state_u in {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
    )
    return {
        "lower_deep": lower_deep,
        "lower_context": lower_context,
        "middle_context": middle_context,
        "upper_context": upper_context,
    }


def _display_importance_direction_v1(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
) -> str:
    symbol_u = normalize_canonical_symbol(str(symbol or ""))
    observe_reason_u = str(observe_reason or "").strip().lower()
    probe_scene_u = str(probe_scene_id or "").strip()
    side_u = str(side or "").upper().strip()
    scene_direction = resolve_probe_scene_direction(probe_scene_u)
    if observe_reason_u in _DISPLAY_LOWER_REBOUND_REASONS_V1:
        return "BUY"
    if observe_reason_u in _DISPLAY_UPPER_REJECT_REASONS_V1:
        return "SELL"
    if observe_reason_u in _DISPLAY_STRUCTURAL_OBSERVE_REASONS_V1:
        if scene_direction:
            return scene_direction
        if symbol_u == "NAS100":
            return _first_directional_value(side_u)
        return ""
    return _first_directional_value(side_u, scene_direction)


def _display_importance_family_v1(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    symbol_u = normalize_canonical_symbol(str(symbol or ""))
    observe_reason_u = str(observe_reason or "").strip().lower()
    probe_scene_u = str(probe_scene_id or "").strip()
    bb_state_u = str(bb_state or "").upper().strip()
    direction_u = _display_importance_direction_v1(
        symbol=symbol_u,
        side=side,
        observe_reason=observe_reason_u,
        probe_scene_id=probe_scene_u,
    )
    context = _display_importance_context_v1(box_state=box_state, bb_state=bb_state)
    lower_context = bool(context["lower_context"])
    middle_context = bool(context["middle_context"])
    upper_context = bool(context["upper_context"])

    if direction_u == "BUY":
        if observe_reason_u in _DISPLAY_LOWER_REBOUND_REASONS_V1:
            if lower_context:
                return "lower_recovery_start"
            if (
                symbol_u in {"NAS100", "BTCUSD"}
                and observe_reason_u == "lower_rebound_confirm"
                and upper_context
                and bb_state_u == "UPPER_EDGE"
                and (symbol_u != "NAS100" or probe_scene_u == "nas_clean_confirm_probe")
            ):
                return "breakout_reclaim_confirm"
            return ""
        if observe_reason_u in _DISPLAY_STRUCTURAL_OBSERVE_REASONS_V1:
            if upper_context and symbol_u == "NAS100":
                return "upper_support_awareness"
            if lower_context or middle_context:
                return "structural_rebound"
            if symbol_u == "NAS100" and direction_u == "BUY":
                return "structural_rebound"
    if direction_u == "SELL" and symbol_u == "XAUUSD":
        if observe_reason_u in _DISPLAY_UPPER_REJECT_CORE_REASONS_V1 and upper_context:
            return "upper_reject_core"
        if observe_reason_u in _DISPLAY_UPPER_REJECT_REASONS_V1 and (upper_context or middle_context):
            return "upper_reject_development"
    return ""


def _display_importance_tier_common_v1(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    symbol_u = normalize_canonical_symbol(str(symbol or ""))
    observe_reason_u = str(observe_reason or "").strip().lower()
    context = _display_importance_context_v1(box_state=box_state, bb_state=bb_state)
    lower_deep = bool(context["lower_deep"])
    lower_context = bool(context["lower_context"])
    middle_context = bool(context["middle_context"])
    upper_context = bool(context["upper_context"])
    direction_u = _display_importance_direction_v1(
        symbol=symbol_u,
        side=side,
        observe_reason=observe_reason_u,
        probe_scene_id=probe_scene_id,
    )
    family = _display_importance_family_v1(
        symbol=symbol_u,
        side=side,
        observe_reason=observe_reason_u,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )

    if observe_reason_u in _DISPLAY_LOWER_REBOUND_REASONS_V1:
        if lower_deep:
            return "high"
        if family == "breakout_reclaim_confirm":
            return "medium"
        if upper_context:
            return ""
        if lower_context or middle_context:
            return "medium"
        return "medium"
    if observe_reason_u in _DISPLAY_STRUCTURAL_OBSERVE_REASONS_V1:
        if family == "upper_support_awareness":
            return ""
        if family == "structural_rebound":
            return "medium"
        return "medium" if symbol_u == "NAS100" and direction_u == "BUY" else ""
    if observe_reason_u in _DISPLAY_UPPER_REJECT_REASONS_V1:
        if family == "upper_reject_core":
            return "high"
        if family == "upper_reject_development":
            return "medium"
    return ""


def _nas_display_importance_tier(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    if normalize_canonical_symbol(str(symbol or "")) != "NAS100":
        return ""
    return _display_importance_tier_common_v1(
        symbol=symbol,
        side=side,
        observe_reason=observe_reason,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )


def _xau_display_importance_tier(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    if normalize_canonical_symbol(str(symbol or "")) != "XAUUSD":
        return ""
    return _display_importance_tier_common_v1(
        symbol=symbol,
        side=side,
        observe_reason=observe_reason,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )


def _btc_display_importance_tier(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    if normalize_canonical_symbol(str(symbol or "")) != "BTCUSD":
        return ""
    return _display_importance_tier_common_v1(
        symbol=symbol,
        side=side,
        observe_reason=observe_reason,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )


def _display_importance_source_reason_v1(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    symbol_u = normalize_canonical_symbol(str(symbol or ""))
    family = _display_importance_family_v1(
        symbol=symbol_u,
        side=side,
        observe_reason=observe_reason,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )
    reason_map = _DISPLAY_IMPORTANCE_REASON_ALIAS_V1.get(symbol_u, {})
    return str(reason_map.get(family, "") or "")


def _upward_breakout_resume_signal_v1(
    *,
    breakout_candidate_direction: str,
    breakout_candidate_action_target: str,
    box_state: str,
    bb_state: str,
    quick_trace_state: str,
) -> bool:
    breakout_direction_u = str(breakout_candidate_direction or "").strip().upper()
    breakout_target_u = str(breakout_candidate_action_target or "").strip().upper()
    box_state_u = str(box_state or "").strip().upper()
    bb_state_u = str(bb_state or "").strip().upper()
    quick_trace_u = str(quick_trace_state or "").strip().upper()
    return bool(
        breakout_direction_u == "UP"
        and breakout_target_u in {"WATCH_BREAKOUT", "PROBE_BREAKOUT"}
        and box_state_u in {"MIDDLE", "MID", "UPPER", "UPPER_EDGE", "ABOVE"}
        and bb_state_u in {"UNKNOWN", "MID", "MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
        and quick_trace_u in {"OBSERVE", "BLOCKED", "PROBE_WAIT"}
    )


def _sell_watch_breakout_resume_relief_v1(
    *,
    side: str,
    observe_reason: str,
    breakout_candidate_direction: str,
    breakout_candidate_action_target: str,
    box_state: str,
    bb_state: str,
    quick_trace_state: str,
) -> bool:
    observe_reason_u = str(observe_reason or "").strip().lower()
    side_u = str(side or "").strip().upper()
    return bool(
        side_u == "SELL"
        and observe_reason_u in {"upper_break_fail_confirm", "upper_reject_probe_observe"}
        and _upward_breakout_resume_signal_v1(
            breakout_candidate_direction=breakout_candidate_direction,
            breakout_candidate_action_target=breakout_candidate_action_target,
            box_state=box_state,
            bb_state=bb_state,
            quick_trace_state=quick_trace_state,
        )
    )


def _conflict_breakout_resume_surface_v1(
    *,
    observe_reason: str,
    breakout_candidate_direction: str,
    breakout_candidate_action_target: str,
    box_state: str,
    bb_state: str,
    quick_trace_state: str,
) -> bool:
    observe_reason_u = str(observe_reason or "").strip().lower()
    return bool(
        observe_reason_u
        in {
            "conflict_box_upper_bb20_lower_upper_dominant_observe",
            "conflict_box_upper_bb20_lower_balanced_observe",
        }
        and _upward_breakout_resume_signal_v1(
            breakout_candidate_direction=breakout_candidate_direction,
            breakout_candidate_action_target=breakout_candidate_action_target,
            box_state=box_state,
            bb_state=bb_state,
            quick_trace_state=quick_trace_state,
        )
    )


def _display_importance_tier_v1(
    *,
    symbol: str,
    side: str,
    observe_reason: str,
    probe_scene_id: str,
    box_state: str,
    bb_state: str,
) -> str:
    return _display_importance_tier_common_v1(
        symbol=symbol,
        side=side,
        observe_reason=observe_reason,
        probe_scene_id=probe_scene_id,
        box_state=box_state,
        bb_state=bb_state,
    )


def _xau_state_importance_soft_cap_v1(
    *,
    symbol: str,
    side: str,
    importance_tier: str,
    payload: Mapping[str, Any] | None,
) -> tuple[str, str]:
    symbol_u = str(symbol or "").upper().strip()
    side_u = str(side or "").upper().strip()
    tier_u = str(importance_tier or "").strip().lower()
    if symbol_u != "XAUUSD" or side_u not in {"BUY", "SELL"} or tier_u not in {"medium", "high"}:
        return str(importance_tier or ""), ""

    payload_local = dict(payload or {})
    position_snapshot = _mapping_from_jsonish(payload_local.get("position_snapshot_v2"))
    state_vector = _mapping_from_jsonish(payload_local.get("state_vector_v2"))
    energy = _mapping_from_jsonish(position_snapshot.get("energy"))
    interpretation = _mapping_from_jsonish(position_snapshot.get("interpretation"))

    middle_neutrality = _to_float(energy.get("middle_neutrality", 0.0), default=0.0)
    conflict_score = _to_float(energy.get("position_conflict_score", 0.0), default=0.0)
    lower_force = _to_float(energy.get("lower_position_force", 0.0), default=0.0)
    upper_force = _to_float(energy.get("upper_position_force", 0.0), default=0.0)
    fast_exit_risk_penalty = _to_float(state_vector.get("fast_exit_risk_penalty", 0.0), default=0.0)
    conflict_damp = _to_float(state_vector.get("conflict_damp", 1.0), default=1.0)

    bias_label = str(
        interpretation.get("bias_label", "")
        or interpretation.get("primary_label", "")
        or interpretation.get("secondary_context_label", "")
        or ""
    ).upper()
    side_bias_match = bool(
        (side_u == "BUY" and ("LOWER" in bias_label or "BULL" in bias_label))
        or (side_u == "SELL" and ("UPPER" in bias_label or "BEAR" in bias_label))
    )
    dominant_force = upper_force if side_u == "SELL" else lower_force
    opposing_force = lower_force if side_u == "SELL" else upper_force
    directional_gap = dominant_force - opposing_force
    strong_directional_context = bool(
        side_bias_match
        and dominant_force >= 0.32
        and directional_gap >= 0.12
        and middle_neutrality <= 0.25
        and conflict_score <= 0.18
    )
    chop_pressure = bool(
        middle_neutrality >= 0.45
        or conflict_score >= 0.30
        or fast_exit_risk_penalty >= 0.28
        or (conflict_damp <= 0.92 and not strong_directional_context)
    )
    if not chop_pressure:
        return str(importance_tier or ""), ""
    if strong_directional_context and tier_u == "high":
        return str(importance_tier or ""), ""
    if tier_u == "high":
        return "medium", "xau_state_chop_soft_cap"
    return "", "xau_state_chop_soft_cap"


def _act_wait_bridge_from_payload_v1(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload_local = dict(payload or {})
    forecast_features = _mapping_from_jsonish(payload_local.get("forecast_features_v1"))
    forecast_meta = _mapping_from_jsonish(forecast_features.get("metadata"))
    bridge_root = _mapping_from_jsonish(forecast_meta.get("bridge_first_v1"))
    bridge = _mapping_from_jsonish(bridge_root.get("act_vs_wait_bias_v1"))
    return {
        "contract_version": str(bridge.get("contract_version", "") or "act_vs_wait_bias_v1"),
        "act_vs_wait_bias": _to_float(bridge.get("act_vs_wait_bias", 0.5), default=0.5),
        "false_break_risk": _to_float(bridge.get("false_break_risk", 0.0), default=0.0),
        "awareness_keep_allowed": bool(bridge.get("awareness_keep_allowed", False)),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _apply_display_importance_floor(
    display_score: float,
    *,
    display_ready: bool,
    importance_tier: str,
) -> float:
    score_f = max(0.0, min(1.0, float(display_score or 0.0)))
    if not display_ready:
        return score_f
    tier_local = str(importance_tier or "").strip().lower()
    floors = _display_modifier_importance_score_floors_v1()
    if tier_local == "high":
        return max(score_f, float(floors["high"]))
    if tier_local == "medium":
        return max(score_f, float(floors["medium"]))
    return score_f


def _display_score_from_effective_state(
    *,
    candidate: bool,
    display_ready: bool,
    entry_ready: bool,
    side: str,
    stage: str,
    level: int,
) -> float:
    side_u = str(side or "").upper()
    stage_u = str(stage or "").upper()
    level_i = max(0, int(level or 0))
    if not candidate or not display_ready or side_u not in {"BUY", "SELL"}:
        return 0.0
    stage_policy_key = "ready" if entry_ready or stage_u == "READY" else stage_u.lower()
    stage_policy = _display_modifier_stage_score_policy_v1(stage_policy_key)
    base = _to_float(stage_policy.get("base", 0.0), default=0.0)
    cap = _to_float(stage_policy.get("cap", 0.0), default=0.0)
    level_start = _to_float(stage_policy.get("level_start", 0.0), default=0.0)
    level_scale = _to_float(stage_policy.get("level_scale", 0.0), default=0.0)
    if cap <= 0.0:
        return 0.0
    return float(min(cap, base + (max(0.0, float(level_i) - level_start) * level_scale)))


def _build_scene_baseline_snapshot_v1(
    *,
    candidate: bool,
    display_ready: bool,
    entry_ready: bool,
    side: str,
    stage: str,
    reason: str,
    entry_block_reason: str,
    blocked_display_reason: str,
    symbol: str,
    probe_scene_id: str,
    display_box_state: str,
    display_bb_state: str,
    display_importance_tier: str,
    display_importance_source_reason: str,
    display_importance_adjustment_reason: str,
) -> dict[str, Any]:
    return {
        "check_candidate": bool(candidate),
        "check_display_ready": bool(display_ready),
        "entry_ready": bool(entry_ready),
        "check_side": str(side or ""),
        "check_stage": str(stage or ""),
        "check_reason": str(reason or ""),
        "entry_block_reason": str(entry_block_reason or ""),
        "blocked_display_reason": str(blocked_display_reason or ""),
        "canonical_symbol": str(symbol or ""),
        "probe_scene_id": str(probe_scene_id or ""),
        "display_box_state": str(display_box_state or ""),
        "display_bb_state": str(display_bb_state or ""),
        "display_importance_tier": str(display_importance_tier or ""),
        "display_importance_source_reason": str(display_importance_source_reason or ""),
        "display_importance_adjustment_reason": str(display_importance_adjustment_reason or ""),
    }


def evaluate_consumer_open_guard_v1(
    *,
    consumer_check_state_v1: Mapping[str, Any] | None,
    action: object,
) -> dict[str, Any]:
    state_local = dict(consumer_check_state_v1 or {})
    action_u = str(action or "").upper().strip()
    candidate = bool(state_local.get("check_candidate", False))
    display_ready = bool(state_local.get("check_display_ready", False))
    entry_ready = bool(state_local.get("entry_ready", False))
    side_u = _first_directional_value(state_local.get("check_side", ""), action_u)
    stage_u = str(state_local.get("check_stage", "") or "").upper().strip()
    guard_active = bool(action_u in {"BUY", "SELL"} and candidate and side_u == action_u)
    failure_code = ""
    if guard_active:
        if stage_u == "BLOCKED":
            failure_code = "consumer_stage_blocked"
        elif not entry_ready:
            failure_code = "consumer_entry_not_ready"
    block_reason = str(
        state_local.get("entry_block_reason", "")
        or state_local.get("blocked_display_reason", "")
        or ""
    ).strip()
    return {
        "contract_version": "consumer_open_guard_v1",
        "action": str(action_u or ""),
        "guard_active": bool(guard_active),
        "allows_open": bool(not failure_code),
        "failure_code": str(failure_code or ""),
        "check_candidate": bool(candidate),
        "check_display_ready": bool(display_ready),
        "entry_ready": bool(entry_ready),
        "check_side": str(side_u or ""),
        "check_stage": str(stage_u or ""),
        "check_reason": str(state_local.get("check_reason", "") or ""),
        "entry_block_reason": str(block_reason or ""),
    }


def _matches_runtime_display_signature(
    row: Mapping[str, Any] | None,
    *,
    side: str,
    stage: str,
    observe_reason: str,
    blocked_by: str,
    action_none_reason: str,
    probe_scene_id: str,
) -> bool:
    row_local = dict(row or {})
    state_local = row_local.get("consumer_check_state_v1", {})
    if not isinstance(state_local, Mapping):
        state_local = {}
    prev_display_ready = bool(
        row_local.get(
            "consumer_check_display_ready",
            state_local.get("check_display_ready", False),
        )
    )
    if not prev_display_ready:
        return False
    prev_side = _first_directional_value(
        row_local.get("consumer_check_side", ""),
        state_local.get("check_side", ""),
    )
    prev_stage = str(
        row_local.get("consumer_check_stage", "")
        or state_local.get("check_stage", "")
        or ""
    ).upper()
    prev_observe_reason = str(
        row_local.get("observe_reason", "")
        or state_local.get("semantic_origin_reason", "")
        or state_local.get("check_reason", "")
        or ""
    )
    prev_blocked_by = str(row_local.get("blocked_by", "") or "")
    prev_action_none_reason = str(
        row_local.get("action_none_reason", "")
        or state_local.get("entry_block_reason", "")
        or ""
    )
    prev_probe_scene_id = str(
        row_local.get("probe_scene_id", "")
        or state_local.get("probe_scene_id", "")
        or ""
    )
    return bool(
        str(prev_side or "").upper() == str(side or "").upper()
        and prev_stage == str(stage or "").upper()
        and prev_observe_reason == str(observe_reason or "")
        and prev_blocked_by == str(blocked_by or "")
        and prev_action_none_reason == str(action_none_reason or "")
        and prev_probe_scene_id == str(probe_scene_id or "")
    )


def build_consumer_check_state_v1(
    *,
    payload: Mapping[str, Any] | None,
    canonical_symbol: str = "",
    shadow_reason: str = "",
    shadow_side: str = "",
    box_state: str = "",
    bb_state: str = "",
    probe_plan_default: Mapping[str, Any] | None = None,
    default_side_gate_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload_local = dict(payload or {})
    probe_plan_seed = probe_plan_default if isinstance(probe_plan_default, Mapping) else {}
    default_side_gate = dict(default_side_gate_v1 or {}) if isinstance(default_side_gate_v1, Mapping) else {}
    probe_plan_local = payload_local.get("entry_probe_plan_v1", probe_plan_seed)
    if not isinstance(probe_plan_local, Mapping):
        probe_plan_local = {}
    symbol_local = str(canonical_symbol or "").upper().strip()
    observe_reason_local = str(payload_local.get("observe_reason", "") or shadow_reason or "")
    blocked_by_local = str(payload_local.get("blocked_by", "") or "")
    action_none_reason_local = str(payload_local.get("action_none_reason", "") or "")
    core_reason_local = str(payload_local.get("core_reason", "") or "")
    box_state_local = str(payload_local.get("box_state", "") or box_state or "").strip().upper()
    bb_state_local = str(payload_local.get("bb_state", "") or bb_state or "").strip().upper()
    consumer_effective_action_local = str(
        payload_local.get("consumer_effective_action", "") or payload_local.get("action", "") or ""
    ).strip().upper()
    display_side = _first_directional_value(
        consumer_effective_action_local,
        payload_local.get("observe_side", ""),
        payload_local.get("core_intended_direction", ""),
        shadow_side,
        probe_plan_local.get("intended_action", ""),
        payload_local.get("core_resolved_shadow_action", ""),
        default_side_gate.get("winner_side", ""),
        _directional_side_from_policy(payload_local.get("core_allowed_action", "")),
        _directional_side_from_policy(payload_local.get("preflight_allowed_action", "")),
    )
    probe_reason_local = str(probe_plan_local.get("reason", "") or "")
    probe_scene_local = str(
        payload_local.get("probe_scene_id", "")
        or probe_plan_local.get("symbol_scene_relief", "")
        or ""
    ).strip()
    breakout_candidate_direction_local = str(
        payload_local.get("breakout_candidate_direction", "") or ""
    ).strip().upper()
    breakout_candidate_action_target_local = str(
        payload_local.get("breakout_candidate_action_target", "") or ""
    ).strip().upper()
    quick_trace_state_local = str(payload_local.get("quick_trace_state", "") or "").strip().upper()
    probe_active_local = bool(probe_plan_local.get("active", False))
    probe_ready_local = bool(probe_plan_local.get("ready_for_entry", False))
    consumer_block_is_execution_local = bool(payload_local.get("consumer_block_is_execution", False))
    explicit_probe_observe = "_probe_observe" in observe_reason_local
    explicit_confirm_surface = observe_reason_local.endswith("_confirm")
    explicit_probe_surface = bool(
        action_none_reason_local == "probe_not_promoted"
        or str(payload_local.get("probe_scene_id", "") or "").strip()
    )
    explicit_watch_surface = observe_reason_local.endswith("_watch")
    explicit_structural_observe_surface = observe_reason_local in {
        "outer_band_reversal_support_required_observe",
        "middle_sr_anchor_required_observe",
    }
    balanced_conflict_display_suppressed = bool(
        observe_reason_local.startswith("conflict_box_")
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
        and not explicit_probe_observe
        and not explicit_probe_surface
        and not explicit_confirm_surface
    )
    if balanced_conflict_display_suppressed:
        display_side = ""
    common_sell_breakout_resume_relief = _sell_watch_breakout_resume_relief_v1(
        side=display_side,
        observe_reason=observe_reason_local,
        breakout_candidate_direction=breakout_candidate_direction_local,
        breakout_candidate_action_target=breakout_candidate_action_target_local,
        box_state=box_state_local,
        bb_state=bb_state_local,
        quick_trace_state=quick_trace_state_local,
    )
    common_conflict_breakout_resume_surface = _conflict_breakout_resume_surface_v1(
        observe_reason=observe_reason_local,
        breakout_candidate_direction=breakout_candidate_direction_local,
        breakout_candidate_action_target=breakout_candidate_action_target_local,
        box_state=box_state_local,
        bb_state=bb_state_local,
        quick_trace_state=quick_trace_state_local,
    )
    if common_sell_breakout_resume_relief or (
        common_conflict_breakout_resume_surface and display_side not in {"BUY", "SELL"}
    ):
        display_side = "BUY"
    breakout_resume_observe_surface = bool(
        common_conflict_breakout_resume_surface
        or (
            common_sell_breakout_resume_relief
            and action_none_reason_local == "observe_state_wait"
            and not probe_ready_local
        )
    )
    weak_observe_surface = bool(
        explicit_watch_surface
        or explicit_structural_observe_surface
        or breakout_resume_observe_surface
    )
    structural_guard_observe_surface = bool(
        explicit_structural_observe_surface
        and blocked_by_local in {"outer_band_guard", "middle_sr_anchor_guard"}
    )
    explicit_execution_surface = bool(
        action_none_reason_local in {"execution_soft_blocked", "confirm_suppressed"}
        or blocked_by_local == "energy_soft_block"
        or blocked_by_local.endswith("_soft_block")
    )
    btc_upper_sell_weak_display_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and probe_scene_local == "btc_upper_sell_probe"
        and action_none_reason_local == "probe_not_promoted"
        and probe_reason_local == "probe_against_default_side"
        and not bool(blocked_by_local)
    )
    nas_outer_band_probe_against_default_side_wait_relief = bool(
        symbol_local == "NAS100"
        and observe_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_by_local == "outer_band_guard"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
        and probe_reason_local == "probe_against_default_side"
    )
    xau_outer_band_probe_against_default_side_wait_relief = bool(
        symbol_local == "XAUUSD"
        and observe_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_by_local == "outer_band_guard"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "xau_upper_sell_probe"
        and probe_reason_local == "probe_against_default_side"
    )
    xau_lower_probe_guard_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local in {"forecast_guard", "barrier_guard"}
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "xau_second_support_buy_probe"
    )
    nas_lower_probe_downgrade = bool(
        symbol_local == "NAS100"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local in {"", "probe_promotion_gate", "forecast_guard", "barrier_guard"}
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
    )
    btc_lower_probe_downgrade = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local in {"barrier_guard", "forecast_guard"}
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
    )
    btc_lower_probe_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
        and probe_ready_local
    )
    btc_lower_probe_promotion_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local == "probe_promotion_gate"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
    )
    btc_lower_probe_guard_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_probe_observe"
        and blocked_by_local in {"forecast_guard", "barrier_guard"}
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
    )
    btc_upper_reject_confirm_forecast_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
    )
    btc_upper_break_fail_confirm_forecast_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
    )
    btc_upper_break_fail_confirm_entry_gate_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_reason_local
        and not probe_scene_local
    )
    nas_upper_break_fail_confirm_entry_gate_wait_relief = bool(
        symbol_local == "NAS100"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_reason_local
        and not probe_scene_local
    )
    xau_upper_reject_mixed_confirm_entry_gate_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_reason_local
        and not probe_scene_local
    )
    xau_outer_band_probe_entry_gate_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_by_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_reason_local
        and probe_scene_local == "xau_upper_sell_probe"
    )
    btc_upper_break_fail_confirm_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    btc_upper_reject_probe_forecast_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "btc_upper_sell_probe"
    )
    btc_upper_reject_probe_preflight_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "preflight_action_blocked"
        and action_none_reason_local == "preflight_blocked"
        and probe_scene_local == "btc_upper_sell_probe"
    )
    btc_upper_reject_probe_promotion_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "probe_promotion_gate"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "btc_upper_sell_probe"
    )
    btc_upper_reject_confirm_preflight_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local == "preflight_action_blocked"
        and action_none_reason_local == "preflight_blocked"
        and not probe_scene_local
    )
    btc_upper_reject_confirm_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    btc_upper_reject_probe_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "btc_upper_sell_probe"
        and probe_ready_local
        and bool(probe_plan_local.get("energy_relief_allowed", False))
    )
    nas_upper_reject_probe_forecast_wait_relief = bool(
        symbol_local == "NAS100"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
    )
    nas_upper_reject_probe_promotion_wait_relief = bool(
        symbol_local == "NAS100"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "probe_promotion_gate"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
    )
    xau_upper_reject_probe_forecast_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "xau_upper_sell_probe"
    )
    xau_upper_reject_probe_promotion_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "probe_promotion_gate"
        and action_none_reason_local == "probe_not_promoted"
        and probe_scene_local == "xau_upper_sell_probe"
    )
    btc_structural_probe_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
    )
    xau_upper_reject_confirm_hidden = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local in {"forecast_guard", "barrier_guard"}
        and action_none_reason_local == "observe_state_wait"
    )
    xau_upper_reject_mixed_confirm_hidden = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local in {"forecast_guard", "barrier_guard"}
        and action_none_reason_local == "observe_state_wait"
    )
    xau_upper_reject_probe_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_probe_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "xau_upper_sell_probe"
        and probe_ready_local
        and bool(probe_plan_local.get("energy_relief_allowed", False))
    )
    xau_middle_anchor_probe_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "BUY"
        and observe_reason_local == "middle_sr_anchor_required_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "xau_second_support_buy_probe"
    )
    xau_upper_reject_confirm_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    xau_upper_reject_mixed_confirm_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    nas_upper_reject_mixed_confirm_energy_wait_relief = bool(
        symbol_local == "NAS100"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    btc_upper_reject_mixed_confirm_energy_wait_relief = bool(
        symbol_local == "BTCUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    xau_upper_break_fail_confirm_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    nas_upper_break_fail_confirm_energy_wait_relief = bool(
        symbol_local == "NAS100"
        and display_side == "SELL"
        and observe_reason_local == "upper_break_fail_confirm"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and not probe_scene_local
    )
    xau_outer_band_probe_energy_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_by_local == "energy_soft_block"
        and action_none_reason_local == "execution_soft_blocked"
        and probe_scene_local == "xau_upper_sell_probe"
        and probe_ready_local
        and bool(probe_plan_local.get("energy_relief_allowed", False))
    )
    hard_block_reasons = {
        "policy_hard_blocked",
        "preflight_blocked",
        "default_side_blocked",
    }
    hard_block_guards = {
        "layer_mode_policy_hard_block",
        "preflight_action_blocked",
        "preflight_no_trade",
        "observe_confirm_missing",
        "opposite_position_lock",
    }
    check_candidate = bool(
        display_side in {"BUY", "SELL"}
        and (
            explicit_probe_observe
            or explicit_confirm_surface
            or explicit_probe_surface
            or explicit_watch_surface
            or explicit_structural_observe_surface
            or breakout_resume_observe_surface
            or explicit_execution_surface
            or core_reason_local
            in {
                "core_shadow_probe_wait",
                "core_shadow_confirm_action",
                "core_shadow_probe_action",
            }
        )
    )
    display_blocked = bool(
        action_none_reason_local in hard_block_reasons
        or blocked_by_local in hard_block_guards
        or (
            probe_reason_local in {"probe_side_mismatch", "probe_against_default_side"}
            and not btc_upper_sell_weak_display_relief
            and not nas_outer_band_probe_against_default_side_wait_relief
            and not xau_outer_band_probe_against_default_side_wait_relief
        )
    )
    core_pass_local = _to_float(payload_local.get("core_pass", 0), default=0.0)
    entry_ready = bool(
        check_candidate
        and core_pass_local >= 1.0
        and consumer_effective_action_local in {"BUY", "SELL"}
        and not bool(action_none_reason_local)
        and not bool(blocked_by_local)
        and not display_blocked
        and not consumer_block_is_execution_local
    )
    probe_ready_but_blocked = bool(
        check_candidate
        and probe_ready_local
        and not entry_ready
        and not btc_upper_sell_weak_display_relief
        and not btc_lower_probe_energy_wait_relief
        and not btc_upper_reject_probe_energy_wait_relief
        and not xau_upper_reject_probe_energy_wait_relief
        and not xau_middle_anchor_probe_energy_wait_relief
        and not xau_outer_band_probe_energy_wait_relief
        and (
            bool(action_none_reason_local)
            or bool(blocked_by_local)
            or display_blocked
            or consumer_block_is_execution_local
        )
    )
    check_stage = ""
    display_ready = False
    blocked_display_reason = ""
    if entry_ready:
        check_stage = "READY"
        display_ready = True
    elif probe_ready_but_blocked:
        check_stage = "BLOCKED"
        display_ready = False
        blocked_display_reason = action_none_reason_local or blocked_by_local or probe_reason_local
    elif display_blocked and check_candidate:
        check_stage = "BLOCKED"
        display_ready = False
        blocked_display_reason = probe_reason_local or blocked_by_local or action_none_reason_local
    elif check_candidate:
        if probe_ready_local:
            check_stage = "PROBE"
            display_ready = True
        if (
            not check_stage
            and (
                action_none_reason_local == "execution_soft_blocked"
                or blocked_by_local == "energy_soft_block"
                or blocked_by_local.endswith("_soft_block")
                or action_none_reason_local == "confirm_suppressed"
                or consumer_block_is_execution_local
            )
        ):
            check_stage = "BLOCKED"
            display_ready = True
        elif not check_stage and btc_upper_sell_weak_display_relief:
            check_stage = "OBSERVE"
            display_ready = True
        elif (
            not check_stage
            and (
                structural_guard_observe_surface
                or (
                    weak_observe_surface
                    and not explicit_probe_observe
                    and not explicit_probe_surface
                    and not probe_ready_local
                )
            )
        ):
            check_stage = "OBSERVE"
            display_ready = True
        elif not check_stage and (
            probe_active_local
            or action_none_reason_local == "probe_not_promoted"
            or probe_reason_local.startswith("probe_")
            or explicit_probe_observe
        ):
            check_stage = "PROBE"
            display_ready = True
        elif not check_stage:
            check_stage = "OBSERVE"
            display_ready = True
    if (
        (nas_lower_probe_downgrade or btc_lower_probe_downgrade)
        and check_stage == "PROBE"
        and display_ready
    ):
        check_stage = "OBSERVE"
    lower_rebound_breakdown_display_suppressed = bool(
        display_side == "BUY"
        and observe_reason_local == "lower_rebound_confirm"
        and box_state_local == "BELOW"
        and bb_state_local in {"LOWER_EDGE", "BREAKDOWN"}
        and (
            blocked_by_local in {"energy_soft_block", "forecast_guard"}
            or core_reason_local == "energy_soft_block"
            or action_none_reason_local in {"execution_soft_blocked", "observe_state_wait"}
        )
        and not probe_ready_local
    )
    xau_upper_sell_repeat_suppressed = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and not entry_ready
        and observe_reason_local in {"upper_break_fail_confirm", "upper_reject_confirm"}
        and check_stage in {"BLOCKED", "PROBE"}
        and (
            blocked_by_local in {"energy_soft_block"}
            or action_none_reason_local in {"execution_soft_blocked", "confirm_suppressed"}
            or (
                observe_reason_local == "upper_break_fail_confirm"
                and action_none_reason_local == "observe_state_wait"
            )
        )
        and not xau_upper_reject_confirm_energy_wait_relief
        and not xau_upper_break_fail_confirm_energy_wait_relief
        and not xau_upper_reject_confirm_hidden
    )
    xau_upper_reject_mixed_guard_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_mixed_confirm"
        and blocked_by_local in {"barrier_guard", "forecast_guard"}
        and action_none_reason_local == "observe_state_wait"
    )
    xau_upper_reject_confirm_forecast_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "upper_reject_confirm"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
    )
    xau_middle_anchor_guard_wait_relief = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local == "middle_sr_anchor_required_observe"
        and blocked_by_local == "middle_sr_anchor_guard"
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
    )
    xau_upper_reject_guard_wait_hidden = bool(
        symbol_local == "XAUUSD"
        and display_side == "SELL"
        and observe_reason_local in {"upper_reject_confirm", "upper_reject_mixed_confirm"}
        and blocked_by_local in {"forecast_guard", "barrier_guard"}
        and action_none_reason_local == "observe_state_wait"
        and not probe_ready_local
        and not xau_upper_reject_confirm_forecast_wait_relief
        and not xau_upper_reject_mixed_guard_wait_relief
    )
    if xau_upper_sell_repeat_suppressed:
        display_ready = False
        if not blocked_display_reason:
            blocked_display_reason = action_none_reason_local or blocked_by_local or probe_reason_local
    if xau_upper_reject_guard_wait_hidden:
        display_ready = False
        if not blocked_display_reason:
            blocked_display_reason = "xau_upper_reject_guard_wait_hidden"
    if btc_upper_reject_confirm_preflight_wait_relief and check_stage == "BLOCKED":
        display_ready = True
        if not blocked_display_reason:
            blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if btc_upper_reject_probe_preflight_wait_relief and check_stage == "BLOCKED":
        display_ready = True
        if not blocked_display_reason:
            blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_confirm_energy_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_lower_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_lower_probe_promotion_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_lower_probe_guard_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_confirm_forecast_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_break_fail_confirm_forecast_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_break_fail_confirm_entry_gate_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_upper_break_fail_confirm_entry_gate_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_mixed_confirm_entry_gate_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_outer_band_probe_entry_gate_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_break_fail_confirm_energy_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_probe_forecast_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_probe_preflight_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_confirm_preflight_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_probe_promotion_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_upper_reject_probe_forecast_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_upper_reject_probe_promotion_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_probe_forecast_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_probe_promotion_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_outer_band_probe_against_default_side_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_outer_band_probe_against_default_side_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_lower_probe_guard_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_structural_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_middle_anchor_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_confirm_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_break_fail_confirm_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_upper_break_fail_confirm_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_outer_band_probe_energy_wait_relief
        and check_stage in {"PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_middle_anchor_guard_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_confirm_forecast_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_mixed_guard_wait_relief
        and check_stage in {"OBSERVE", "PROBE", "BLOCKED"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        xau_upper_reject_mixed_confirm_energy_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        nas_upper_reject_mixed_confirm_energy_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if (
        btc_upper_reject_mixed_confirm_energy_wait_relief
        and check_stage in {"BLOCKED", "PROBE", "OBSERVE"}
        and not blocked_display_reason
    ):
        blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    if lower_rebound_breakdown_display_suppressed:
        display_ready = False
        if not blocked_display_reason:
            blocked_display_reason = blocked_by_local or action_none_reason_local or probe_reason_local
    candidate_support_local = _to_float(
        probe_plan_local.get("candidate_support", payload_local.get("probe_candidate_support", 0.0)),
        default=0.0,
    )
    pair_gap_local = _to_float(
        probe_plan_local.get("pair_gap", payload_local.get("probe_pair_gap", 0.0)),
        default=0.0,
    )
    display_importance_tier = _display_importance_tier_v1(
        symbol=symbol_local,
        side=display_side,
        observe_reason=observe_reason_local,
        probe_scene_id=probe_scene_local,
        box_state=box_state_local,
        bb_state=bb_state_local,
    )
    display_importance_source_reason = _display_importance_source_reason_v1(
        symbol=symbol_local,
        side=display_side,
        observe_reason=observe_reason_local,
        probe_scene_id=probe_scene_local,
        box_state=box_state_local,
        bb_state=bb_state_local,
    )
    btc_lower_rebound_forecast_wait_hidden = bool(
        symbol_local == "BTCUSD"
        and display_side == "BUY"
        and observe_reason_local == "lower_rebound_confirm"
        and blocked_by_local == "forecast_guard"
        and action_none_reason_local == "observe_state_wait"
        and not probe_scene_local
        and display_importance_source_reason == "btc_lower_recovery_start"
        and box_state_local in {"BELOW", "LOWER", "LOWER_EDGE"}
        and bb_state_local in {"LOWER_EDGE", "BREAKDOWN"}
    )
    display_importance_adjustment_reason = ""
    display_importance_tier, display_importance_adjustment_reason = _xau_state_importance_soft_cap_v1(
        symbol=symbol_local,
        side=display_side,
        importance_tier=display_importance_tier,
        payload=payload_local,
    )
    act_wait_bridge = _act_wait_bridge_from_payload_v1(payload_local)
    bridge_act_vs_wait_bias = _to_float(act_wait_bridge.get("act_vs_wait_bias", 0.5), default=0.5)
    bridge_false_break_risk = _to_float(act_wait_bridge.get("false_break_risk", 0.0), default=0.0)
    bridge_awareness_keep_allowed = bool(act_wait_bridge.get("awareness_keep_allowed", False))
    baseline_snapshot = _build_scene_baseline_snapshot_v1(
        candidate=check_candidate,
        display_ready=display_ready,
        entry_ready=entry_ready,
        side=display_side,
        stage=check_stage,
        reason=observe_reason_local or core_reason_local,
        entry_block_reason=(
            action_none_reason_local
            or blocked_by_local
            or probe_reason_local
            or payload_local.get("consumer_block_reason", "")
            or ""
        ),
        blocked_display_reason=blocked_display_reason,
        symbol=symbol_local,
        probe_scene_id=probe_scene_local,
        display_box_state=box_state_local,
        display_bb_state=bb_state_local,
        display_importance_tier=display_importance_tier,
        display_importance_source_reason=display_importance_source_reason,
        display_importance_adjustment_reason=display_importance_adjustment_reason,
    )
    modifier_result = _apply_state_aware_display_modifier_v1(
        symbol=str(symbol_local or ""),
        candidate=bool(baseline_snapshot["check_candidate"]),
        display_ready=bool(baseline_snapshot["check_display_ready"]),
        entry_ready=bool(baseline_snapshot["entry_ready"]),
        side=str(baseline_snapshot["check_side"] or ""),
        stage=str(baseline_snapshot["check_stage"] or ""),
        reason=str(baseline_snapshot["check_reason"] or ""),
        probe_scene_id=str(baseline_snapshot["probe_scene_id"] or ""),
        blocked_by=blocked_by_local,
        action_none_reason=action_none_reason_local,
        display_importance_tier=display_importance_tier,
        display_importance_source_reason=display_importance_source_reason,
        candidate_support=candidate_support_local,
        pair_gap=pair_gap_local,
        bridge_act_vs_wait_bias=bridge_act_vs_wait_bias,
        bridge_false_break_risk=bridge_false_break_risk,
        bridge_awareness_keep_allowed=bridge_awareness_keep_allowed,
    )
    if (
        btc_lower_rebound_forecast_wait_hidden
        and not bool(baseline_snapshot["check_display_ready"])
        and not str(modifier_result.get("modifier_primary_reason", "") or "")
    ):
        reason_code = "btc_lower_rebound_forecast_wait_hide_without_probe"
        modifier_result["modifier_applied"] = True
        modifier_result["modifier_primary_reason"] = reason_code
        modifier_reason_codes = list(modifier_result.get("modifier_reason_codes", []) or [])
        if reason_code not in modifier_reason_codes:
            modifier_reason_codes.append(reason_code)
        modifier_result["modifier_reason_codes"] = modifier_reason_codes
        modifier_result["modifier_stage_adjustment"] = "visibility_suppressed"
    if (
        balanced_conflict_display_suppressed
        and not bool(baseline_snapshot["check_display_ready"])
        and not str(modifier_result.get("modifier_primary_reason", "") or "")
    ):
        reason_code = "balanced_conflict_wait_hide_without_probe"
        modifier_result["modifier_applied"] = True
        modifier_result["modifier_primary_reason"] = reason_code
        modifier_reason_codes = list(modifier_result.get("modifier_reason_codes", []) or [])
        if reason_code not in modifier_reason_codes:
            modifier_reason_codes.append(reason_code)
        modifier_result["modifier_reason_codes"] = modifier_reason_codes
        modifier_result["modifier_stage_adjustment"] = "visibility_suppressed"
    display_ready = bool(modifier_result["effective_display_ready"])
    check_stage = str(modifier_result["effective_stage"] or "")
    display_strength_level = int(modifier_result["effective_display_strength_level"] or 0)
    display_score = float(modifier_result["effective_display_score"] or 0.0)
    display_repeat_count = int(modifier_result["effective_display_repeat_count"] or 0)
    bridge_first_adjustment_reason = (
        str(modifier_result.get("modifier_primary_reason", "") or "")
        if str(modifier_result.get("modifier_primary_reason", "") or "") == "bf1_awareness_keep"
        else ""
    )
    return {
        "contract_version": "consumer_check_state_v1",
        "check_candidate": bool(check_candidate),
        "check_display_ready": bool(display_ready),
        "entry_ready": bool(entry_ready),
        "check_side": str(display_side or ""),
        "check_stage": str(check_stage or ""),
        "check_reason": str(observe_reason_local or core_reason_local or ""),
        "entry_block_reason": str(
            action_none_reason_local
            or blocked_by_local
            or probe_reason_local
            or payload_local.get("consumer_block_reason", "")
            or ""
        ),
        "blocked_display_reason": str(blocked_display_reason or ""),
        "semantic_origin_reason": str(observe_reason_local or ""),
        "canonical_symbol": str(symbol_local or ""),
        "probe_scene_id": str(probe_scene_local or ""),
        "display_box_state": str(box_state_local or ""),
        "display_bb_state": str(bb_state_local or ""),
        "consumer_guard_result": str(payload_local.get("consumer_guard_result", "") or ""),
        "consumer_block_kind": str(payload_local.get("consumer_block_kind", "") or ""),
        "consumer_block_source_layer": str(payload_local.get("consumer_block_source_layer", "") or ""),
        "ml_threshold_assist_applied": bool(
            payload_local.get("semantic_live_threshold_applied", False)
            or payload_local.get("consumer_energy_live_gate_applied", False)
            or payload_local.get("consumer_policy_live_gate_applied", False)
        ),
        "display_importance_source_reason": str(display_importance_source_reason or ""),
        "display_importance_adjustment_reason": str(display_importance_adjustment_reason or ""),
        "display_importance_tier": str(display_importance_tier or ""),
        "bridge_first_adjustment_reason": str(bridge_first_adjustment_reason or ""),
        "bridge_act_vs_wait_bias": float(bridge_act_vs_wait_bias),
        "bridge_false_break_risk": float(bridge_false_break_risk),
        "bridge_awareness_keep_allowed": bool(bridge_awareness_keep_allowed),
        "modifier_contract_version": str(
            modifier_result.get("modifier_contract_version", "common_state_aware_display_modifier_v1")
            or "common_state_aware_display_modifier_v1"
        ),
        "modifier_applied": bool(modifier_result.get("modifier_applied", False)),
        "modifier_primary_reason": str(modifier_result.get("modifier_primary_reason", "") or ""),
        "modifier_reason_codes": list(modifier_result.get("modifier_reason_codes", []) or []),
        "modifier_stage_adjustment": str(modifier_result.get("modifier_stage_adjustment", "none") or "none"),
        "modifier_score_delta": float(_to_float(modifier_result.get("modifier_score_delta", 0.0), default=0.0)),
        "chart_event_kind_hint": str(modifier_result.get("chart_event_kind_hint", "") or ""),
        "chart_display_mode": str(modifier_result.get("chart_display_mode", "") or ""),
        "chart_display_reason": str(modifier_result.get("chart_display_reason", "") or ""),
        "display_strength_level": int(display_strength_level),
        "display_score": float(display_score),
        "display_repeat_count": int(display_repeat_count),
    }


def resolve_effective_consumer_check_state_v1(
    *,
    consumer_check_state_v1: Mapping[str, Any] | None,
    fallback_candidate: bool = False,
    fallback_display_ready: bool = False,
    fallback_entry_ready: bool = False,
    fallback_side: str = "",
    fallback_stage: str = "",
    fallback_reason: str = "",
    fallback_display_strength_level: int = 0,
    fallback_action_none_reason: str = "",
    blocked_by_value: str = "",
    action_none_reason_value: str | None = None,
    action_value: str = "",
    previous_runtime_row: Mapping[str, Any] | None = None,
    late_display_suppress_guards: Collection[str] | None = None,
) -> tuple[bool, bool, bool, str, str, str, int, dict[str, Any]]:
    state = dict(consumer_check_state_v1 or {})
    candidate = bool(state.get("check_candidate", fallback_candidate))
    display_ready_local = bool(state.get("check_display_ready", fallback_display_ready))
    entry_ready_local = bool(state.get("entry_ready", fallback_entry_ready))
    side_local = str(state.get("check_side", fallback_side or action_value or "") or "").upper()
    stage_local = str(state.get("check_stage", fallback_stage or "") or "").upper()
    reason_local = str(state.get("check_reason", fallback_reason or "") or "")
    try:
        level_local = int(state.get("display_strength_level", fallback_display_strength_level) or 0)
    except Exception:
        level_local = int(fallback_display_strength_level or 0)
    blocked_local = str(blocked_by_value or "").strip()
    action_none_source = fallback_action_none_reason if action_none_reason_value is None else action_none_reason_value
    action_none_local = str(action_none_source or "").strip()
    symbol_local = str(state.get("canonical_symbol", "") or "").upper().strip()
    display_importance_tier = str(state.get("display_importance_tier", "") or "").strip().lower()
    display_importance_source_reason = str(state.get("display_importance_source_reason", "") or "").strip()
    box_state_local = str(state.get("display_box_state", "") or "").upper().strip()
    bb_state_local = str(state.get("display_bb_state", "") or "").upper().strip()
    semantic_origin_reason_local = str(
        state.get("semantic_origin_reason", "")
        or reason_local
        or ""
    )
    probe_scene_local = str(state.get("probe_scene_id", "") or "")
    chart_event_kind_hint = str(state.get("chart_event_kind_hint", "") or "").strip().upper()
    chart_display_mode = str(state.get("chart_display_mode", "") or "").strip()
    chart_display_reason = str(state.get("chart_display_reason", "") or "").strip()
    if side_local not in {"BUY", "SELL"}:
        action_upper = str(action_value or "").upper()
        if action_upper in {"BUY", "SELL"}:
            side_local = action_upper
    btc_upper_break_fail_confirm_entry_gate_wait_repeat_relief = bool(
        symbol_local == "BTCUSD"
        and side_local == "SELL"
        and stage_local in {"OBSERVE", "PROBE", "BLOCKED"}
        and display_ready_local
        and semantic_origin_reason_local == "upper_break_fail_confirm"
        and blocked_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_local
        and not probe_scene_local
        and chart_display_reason == "btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks"
    )
    nas_upper_break_fail_confirm_entry_gate_wait_repeat_relief = bool(
        symbol_local == "NAS100"
        and side_local == "SELL"
        and stage_local in {"OBSERVE", "PROBE", "BLOCKED"}
        and display_ready_local
        and semantic_origin_reason_local == "upper_break_fail_confirm"
        and blocked_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_local
        and not probe_scene_local
        and chart_display_reason == "nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks"
    )
    xau_upper_reject_mixed_confirm_entry_gate_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local in {"OBSERVE", "PROBE", "BLOCKED"}
        and display_ready_local
        and semantic_origin_reason_local == "upper_reject_mixed_confirm"
        and blocked_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_local
        and not probe_scene_local
        and chart_display_reason == "xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks"
    )
    xau_outer_band_probe_entry_gate_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local in {"OBSERVE", "PROBE", "BLOCKED"}
        and display_ready_local
        and semantic_origin_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_local in {
            "clustered_entry_price_zone",
            "pyramid_not_progressed",
            "pyramid_not_in_drawdown",
        }
        and not action_none_local
        and probe_scene_local == "xau_upper_sell_probe"
        and chart_display_reason == "xau_outer_band_probe_entry_gate_wait_as_wait_checks"
    )
    suppress_guards = {
        str(item or "").strip()
        for item in (
            late_display_suppress_guards
            if late_display_suppress_guards is not None
            else DEFAULT_LATE_DISPLAY_SUPPRESS_GUARDS_V1
        )
        if str(item or "").strip()
    }
    if blocked_local or action_none_local:
        entry_ready_local = False
        if (
            blocked_local in suppress_guards
            and not btc_upper_break_fail_confirm_entry_gate_wait_repeat_relief
            and not nas_upper_break_fail_confirm_entry_gate_wait_repeat_relief
            and not xau_upper_reject_mixed_confirm_entry_gate_wait_repeat_relief
            and not xau_outer_band_probe_entry_gate_wait_repeat_relief
        ):
            stage_local = "BLOCKED" if candidate or side_local in {"BUY", "SELL"} else ""
            display_ready_local = False
            level_local = 0
        elif stage_local == "READY":
            if "probe" in reason_local.lower():
                stage_local = "PROBE"
                display_ready_local = True
                level_local = 6 if level_local <= 0 else min(level_local, 7)
            else:
                stage_local = "OBSERVE"
                display_ready_local = True
                level_local = 4 if level_local <= 0 else min(level_local, 5)
        elif not stage_local and candidate:
            stage_local = "BLOCKED" if action_none_local else "OBSERVE"
            display_ready_local = blocked_local not in suppress_guards
            level_local = 3 if stage_local == "BLOCKED" else 4
    nas_lower_probe_late_downgrade = bool(
        symbol_local == "NAS100"
        and side_local == "BUY"
        and stage_local == "PROBE"
        and display_ready_local
        and semantic_origin_reason_local == "lower_rebound_probe_observe"
        and blocked_local in {"barrier_guard", "forecast_guard", "probe_promotion_gate"}
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
    )
    btc_lower_probe_late_downgrade = bool(
        symbol_local == "BTCUSD"
        and side_local == "BUY"
        and stage_local == "PROBE"
        and display_ready_local
        and semantic_origin_reason_local == "lower_rebound_probe_observe"
        and blocked_local in {"barrier_guard", "forecast_guard"}
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
    )
    if nas_lower_probe_late_downgrade or btc_lower_probe_late_downgrade:
        stage_local = "OBSERVE"
        level_local = 5
    xau_upper_reject_late_hidden = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local in {"PROBE", "OBSERVE"}
        and display_ready_local
        and semantic_origin_reason_local in {"upper_reject_confirm", "upper_reject_mixed_confirm"}
        and blocked_local in {"forecast_guard", "barrier_guard"}
        and action_none_local == "observe_state_wait"
        and not (
            semantic_origin_reason_local == "upper_reject_confirm"
            and blocked_local == "forecast_guard"
        )
        and not (
            semantic_origin_reason_local == "upper_reject_mixed_confirm"
            and blocked_local in {"barrier_guard", "forecast_guard"}
        )
    )
    btc_outer_band_probe_guard_wait_repeat_relief = bool(
        symbol_local == "BTCUSD"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_local == "outer_band_guard"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
        and chart_display_reason == "probe_guard_wait_as_wait_checks"
    )
    btc_lower_probe_guard_wait_repeat_relief = bool(
        symbol_local == "BTCUSD"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "lower_rebound_probe_observe"
        and blocked_local in {"forecast_guard", "barrier_guard"}
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
        and chart_display_reason == "btc_lower_probe_guard_wait_as_wait_checks"
    )
    btc_lower_structural_cadence_suppressed = bool(
        symbol_local == "BTCUSD"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_local == "outer_band_guard"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
        and not btc_outer_band_probe_guard_wait_repeat_relief
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage="OBSERVE",
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    xau_middle_anchor_guard_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "middle_sr_anchor_required_observe"
        and blocked_local == "middle_sr_anchor_guard"
        and action_none_local == "observe_state_wait"
        and not probe_scene_local
        and chart_display_reason == "xau_middle_anchor_guard_wait_as_wait_checks"
    )
    xau_upper_reject_probe_forecast_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "PROBE"
        and display_ready_local
        and semantic_origin_reason_local == "upper_reject_probe_observe"
        and blocked_local == "forecast_guard"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "xau_upper_sell_probe"
        and chart_display_reason == "xau_upper_reject_probe_forecast_wait_as_wait_checks"
    )
    xau_upper_reject_probe_promotion_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "PROBE"
        and display_ready_local
        and semantic_origin_reason_local == "upper_reject_probe_observe"
        and blocked_local == "probe_promotion_gate"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "xau_upper_sell_probe"
        and chart_display_reason == "xau_upper_reject_probe_promotion_wait_as_wait_checks"
    )
    xau_upper_reject_mixed_guard_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "upper_reject_mixed_confirm"
        and blocked_local in {"barrier_guard", "forecast_guard"}
        and action_none_local == "observe_state_wait"
        and not probe_scene_local
        and chart_display_reason == "xau_upper_reject_mixed_guard_wait_as_wait_checks"
    )
    xau_upper_reject_confirm_forecast_wait_repeat_relief = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "upper_reject_confirm"
        and blocked_local == "forecast_guard"
        and action_none_local == "observe_state_wait"
        and not probe_scene_local
        and chart_display_reason == "xau_upper_reject_confirm_forecast_wait_as_wait_checks"
    )
    xau_middle_anchor_cadence_suppressed = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "middle_sr_anchor_required_observe"
        and blocked_local == "middle_sr_anchor_guard"
        and action_none_local == "observe_state_wait"
        and not xau_middle_anchor_guard_wait_repeat_relief
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage="OBSERVE",
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    xau_upper_reject_cadence_suppressed = bool(
        symbol_local == "XAUUSD"
        and side_local == "SELL"
        and stage_local in {"OBSERVE", "PROBE"}
        and display_ready_local
        and semantic_origin_reason_local in {
            "upper_reject_confirm",
            "upper_reject_mixed_confirm",
            "upper_reject_probe_observe",
        }
        and blocked_local in {"forecast_guard", "barrier_guard", "probe_promotion_gate"}
        and action_none_local in {"observe_state_wait", "probe_not_promoted"}
        and not (
            semantic_origin_reason_local == "upper_reject_confirm"
            and blocked_local == "forecast_guard"
            and action_none_local == "observe_state_wait"
        )
        and not (
            semantic_origin_reason_local == "upper_reject_mixed_confirm"
            and blocked_local == "barrier_guard"
            and action_none_local == "observe_state_wait"
        )
        and not xau_upper_reject_confirm_forecast_wait_repeat_relief
        and not xau_upper_reject_mixed_guard_wait_repeat_relief
        and not xau_upper_reject_probe_forecast_wait_repeat_relief
        and not xau_upper_reject_probe_promotion_wait_repeat_relief
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage=stage_local,
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    nas_structural_cadence_suppressed = bool(
        symbol_local == "NAS100"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and display_importance_source_reason != "nas_upper_support_awareness"
        and semantic_origin_reason_local == "outer_band_reversal_support_required_observe"
        and blocked_local == "outer_band_guard"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage="OBSERVE",
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    btc_lower_probe_cadence_suppressed = bool(
        symbol_local == "BTCUSD"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "lower_rebound_probe_observe"
        and blocked_local == "forecast_guard"
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "btc_lower_buy_conservative_probe"
        and not btc_lower_probe_guard_wait_repeat_relief
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage="OBSERVE",
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    nas_lower_probe_cadence_suppressed = bool(
        symbol_local == "NAS100"
        and side_local == "BUY"
        and stage_local == "OBSERVE"
        and display_ready_local
        and semantic_origin_reason_local == "lower_rebound_probe_observe"
        and blocked_local in {"barrier_guard", "forecast_guard", "probe_promotion_gate"}
        and action_none_local == "probe_not_promoted"
        and probe_scene_local == "nas_clean_confirm_probe"
        and _matches_runtime_display_signature(
            previous_runtime_row,
            side=side_local,
            stage="OBSERVE",
            observe_reason=semantic_origin_reason_local,
            blocked_by=blocked_local,
            action_none_reason=action_none_local,
            probe_scene_id=probe_scene_local,
        )
    )
    if btc_lower_structural_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "btc_lower_structural_cadence_suppressed"
    if xau_upper_reject_late_hidden:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "xau_upper_reject_guard_wait_hidden"
    if btc_lower_probe_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "btc_lower_probe_cadence_suppressed"
    if nas_lower_probe_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "nas_lower_probe_cadence_suppressed"
    if nas_structural_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "nas_structural_cadence_suppressed"
    nas_upper_continuation_soft_cap = bool(
        symbol_local == "NAS100"
        and side_local == "BUY"
        and display_ready_local
        and display_importance_tier == "medium"
        and display_importance_source_reason != "nas_breakout_reclaim_confirm"
        and probe_scene_local == "nas_clean_confirm_probe"
        and (
            box_state_local in {"UPPER", "UPPER_EDGE", "ABOVE"}
            or bb_state_local in {"UPPER", "UPPER_EDGE"}
        )
        and semantic_origin_reason_local in {
            "lower_rebound_probe_observe",
            "lower_rebound_confirm",
            "outer_band_reversal_support_required_observe",
            "middle_sr_anchor_required_observe",
        }
    )
    if nas_upper_continuation_soft_cap:
        display_importance_tier = ""
        level_local = min(int(level_local or 0), 4)
        if not state.get("blocked_display_reason", ""):
            state["blocked_display_reason"] = "nas_upper_continuation_soft_cap"
    if xau_upper_reject_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "xau_upper_reject_cadence_suppressed"
    if xau_middle_anchor_cadence_suppressed:
        display_ready_local = False
        level_local = 0
        state["blocked_display_reason"] = "xau_middle_anchor_cadence_suppressed"
    state["contract_version"] = str(state.get("contract_version", "consumer_check_state_v1") or "consumer_check_state_v1")
    state["check_candidate"] = bool(candidate)
    state["check_display_ready"] = bool(display_ready_local)
    state["entry_ready"] = bool(entry_ready_local)
    state["check_side"] = str(side_local or "")
    state["check_stage"] = str(stage_local or "")
    state["check_reason"] = str(reason_local or "")
    state["entry_block_reason"] = str(action_none_local or blocked_local or state.get("entry_block_reason", "") or "")
    state["blocked_display_reason"] = str(
        state.get("blocked_display_reason", "")
        or blocked_local
        or action_none_local
        or ""
    )
    state["display_importance_tier"] = str(display_importance_tier or "")
    state["modifier_contract_version"] = str(
        state.get("modifier_contract_version", _display_modifier_policy_v1().get("contract_version", "common_state_aware_display_modifier_v1"))
        or "common_state_aware_display_modifier_v1"
    )
    state["modifier_applied"] = bool(state.get("modifier_applied", False))
    state["modifier_primary_reason"] = str(state.get("modifier_primary_reason", "") or "")
    state["modifier_reason_codes"] = list(state.get("modifier_reason_codes", []) or [])
    state["modifier_stage_adjustment"] = str(state.get("modifier_stage_adjustment", "none") or "none")
    state["modifier_score_delta"] = float(_to_float(state.get("modifier_score_delta", 0.0), default=0.0))
    if not display_ready_local:
        chart_event_kind_hint = ""
        chart_display_mode = ""
        chart_display_reason = ""
    state["chart_event_kind_hint"] = str(chart_event_kind_hint or "")
    state["chart_display_mode"] = str(chart_display_mode or "")
    state["chart_display_reason"] = str(chart_display_reason or "")
    state["display_strength_level"] = int(level_local or 0)
    display_score_local = _display_score_from_effective_state(
        candidate=bool(candidate),
        display_ready=bool(display_ready_local),
        entry_ready=bool(entry_ready_local),
        side=str(side_local or ""),
        stage=str(stage_local or ""),
        level=int(level_local or 0),
    )
    display_score_local = _apply_display_importance_floor(
        display_score_local,
        display_ready=bool(display_ready_local),
        importance_tier=display_importance_tier,
    )
    state["display_score"] = float(display_score_local)
    state["display_repeat_count"] = int(_display_repeat_count(display_score_local))
    return (
        bool(candidate),
        bool(display_ready_local),
        bool(entry_ready_local),
        str(side_local or ""),
        str(stage_local or ""),
        str(reason_local or ""),
        int(level_local or 0),
        state,
    )
