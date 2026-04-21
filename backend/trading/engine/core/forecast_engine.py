from __future__ import annotations

from typing import Protocol

from backend.trading.engine.core.models import ForecastFeaturesV1, TradeManagementForecast, TransitionForecast

FORECAST_RULE_BASELINE_V1 = {
    "baseline_contract": "forecast_rule_baseline_v1",
    "baseline_name": "ForecastRuleV1",
    "baseline_role": "shadow_baseline",
    "score_semantics": "scenario_score",
    "calibrated_probability": False,
    "shadow_ready": True,
    "comparison_target_contract": "ForecastModelV1",
}

FORECAST_FREEZE_CONTRACT_V1 = {
    "semantic_owner_contract": "forecast_branch_interpretation_only_v1",
    "forecast_freeze_phase": "FR0",
    "forecast_role_statement": (
        "Forecast interprets already-built semantic outputs into transition, management, and comparison branches; "
        "it does not create new semantic owners."
    ),
    "owner_boundaries_v1": {
        "position_location_owner": False,
        "response_event_owner": False,
        "state_market_regime_owner": False,
        "evidence_instant_ground_owner": False,
        "belief_persistence_owner": False,
        "barrier_blocking_owner": False,
    },
    "execution_side_creator_allowed": False,
    "direct_action_creator_allowed": False,
    "summary_side_metadata_allowed": True,
    "summary_mode_metadata_allowed": True,
    "branch_layer_only": True,
}

FORECAST_HARVEST_TARGETS_V1 = {
    "state_harvest": [
        "session_regime_state",
        "session_expansion_state",
        "session_exhaustion_state",
        "micro_breakout_readiness_state",
        "micro_reversal_risk_state",
        "micro_participation_state",
        "micro_gap_context_state",
        "topdown_spacing_state",
        "topdown_slope_state",
        "topdown_confluence_state",
        "spread_stress_state",
        "volume_participation_state",
        "execution_friction_state",
        "event_risk_state",
    ],
    "belief_harvest": [
        "dominant_side",
        "dominant_mode",
        "buy_streak",
        "sell_streak",
        "flip_readiness",
        "belief_instability",
    ],
    "barrier_harvest": [
        "edge_turn_relief_v1",
        "breakout_fade_barrier_v1",
        "middle_chop_barrier_v2",
        "session_open_shock_barrier_v1",
        "duplicate_edge_barrier_v1",
        "micro_trap_barrier_v1",
        "post_event_cooldown_barrier_v1",
    ],
    "secondary_harvest": [
        "advanced_input_activation_state",
        "tick_flow_state",
        "order_book_state",
        "source_current_rsi",
        "source_current_adx",
        "source_current_plus_di",
        "source_current_minus_di",
        "source_recent_range_mean",
        "source_recent_body_mean",
        "source_micro_body_size_pct_20",
        "source_micro_upper_wick_ratio_20",
        "source_micro_lower_wick_ratio_20",
        "source_micro_doji_ratio_20",
        "source_micro_same_color_run_current",
        "source_micro_same_color_run_max_20",
        "source_micro_bull_ratio_20",
        "source_micro_bear_ratio_20",
        "source_micro_range_compression_ratio_20",
        "source_micro_volume_burst_ratio_20",
        "source_micro_volume_burst_decay_20",
        "source_micro_swing_high_retest_count_20",
        "source_micro_swing_low_retest_count_20",
        "source_micro_gap_fill_progress",
        "source_sr_level_rank",
        "source_sr_touch_count",
    ],
}

_FORECAST_PRE_ML_PHASE = "FR10"
_FORECAST_PRE_ML_REQUIRED_FEATURE_SPECS = {
    "transition_branch": (
        ("p_buy_confirm", "p_buy_confirm"),
        ("p_sell_confirm", "p_sell_confirm"),
        ("p_reversal_success", "p_reversal_success"),
        ("p_continuation", "p_continuation_success"),
        ("p_false_break", "p_false_break"),
    ),
    "trade_management_branch": (
        ("p_continue_favor", "p_continue_favor"),
        ("p_fail_now", "p_fail_now"),
        ("p_reach_tp1", "p_reach_tp1"),
        ("p_better_reentry_if_cut", "p_better_reentry_if_cut"),
        ("p_recover_after_pullback", "p_recover_after_pullback"),
    ),
    "gap_metrics_branch": (
        ("transition_side_separation", "transition_side_separation"),
        ("transition_confirm_fake_gap", "transition_confirm_fake_gap"),
        ("transition_reversal_continuation_gap", "transition_reversal_continuation_gap"),
        ("management_continue_fail_gap", "management_continue_fail_gap"),
        ("management_recover_reentry_gap", "management_recover_reentry_gap"),
    ),
}
_FORECAST_PRE_ML_RECOMMENDED_FEATURE_SPECS = {
    "transition_branch": (
        ("edge_turn_success", "p_edge_turn_success"),
    ),
    "trade_management_branch": (
        ("premature_exit_risk", "p_premature_exit_risk"),
    ),
    "gap_metrics_branch": (
        ("hold_exit_gap", "hold_exit_gap"),
        ("same_side_flip_gap", "same_side_flip_gap"),
    ),
}


def _forecast_freeze_metadata(branch_role: str) -> dict[str, object]:
    return {
        **dict(FORECAST_FREEZE_CONTRACT_V1),
        "forecast_branch_role": str(branch_role or ""),
    }


def _feature_spec_entries(specs: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [
        {
            "public_name": str(public_name or ""),
            "source_field": str(source_field or ""),
        }
        for public_name, source_field in specs
    ]


def _resolve_feature_values(
    specs: tuple[tuple[str, str], ...],
    source_values: dict[str, float],
) -> dict[str, float]:
    resolved: dict[str, float] = {}
    for public_name, source_field in specs:
        resolved[str(public_name or "")] = float(source_values.get(str(source_field or ""), 0.0) or 0.0)
    return resolved


def _forecast_pre_ml_metadata(branch_role: str, source_values: dict[str, float]) -> dict[str, object]:
    branch_role = str(branch_role or "")
    required_specs = tuple(_FORECAST_PRE_ML_REQUIRED_FEATURE_SPECS.get(branch_role, ()))
    recommended_specs = tuple(_FORECAST_PRE_ML_RECOMMENDED_FEATURE_SPECS.get(branch_role, ()))
    required_values = _resolve_feature_values(required_specs, source_values)
    recommended_values = _resolve_feature_values(recommended_specs, source_values)
    return {
        "forecast_pre_ml_phase": _FORECAST_PRE_ML_PHASE,
        "pre_ml_readiness_contract_v1": {
            "contract_version": "forecast_pre_ml_readiness_v1",
            "forecast_branch_role": branch_role,
            "semantic_owner_contract": FORECAST_FREEZE_CONTRACT_V1["semantic_owner_contract"],
            "ml_usage_role": "feature_only_not_owner",
            "owner_collision_allowed": False,
            "semantic_owner_override_allowed": False,
            "explainable_without_ml": True,
            "required_feature_fields_v1": _feature_spec_entries(required_specs),
            "recommended_feature_fields_v1": _feature_spec_entries(recommended_specs),
        },
        "pre_ml_required_feature_values_v1": required_values,
        "pre_ml_recommended_feature_values_v1": recommended_values,
        "pre_ml_all_feature_values_v1": {
            **required_values,
            **recommended_values,
        },
    }


def _semantic_forecast_inputs_usage(branch_role: str, used_fields: dict[str, list[str]] | None = None) -> dict[str, object]:
    used_fields = {str(k): list(v) for k, v in dict(used_fields or {}).items()}
    grouped_usage: dict[str, dict[str, bool]] = {}
    direct_math_used_fields: list[str] = []
    harvest_only_fields: list[str] = []

    for section, fields in FORECAST_HARVEST_TARGETS_V1.items():
        section_used = set(used_fields.get(section, []))
        grouped_usage[str(section)] = {}
        for field_name in fields:
            used = field_name in section_used
            grouped_usage[str(section)][str(field_name)] = used
            if used:
                direct_math_used_fields.append(str(field_name))
            else:
                harvest_only_fields.append(str(field_name))

    return {
        "contract_version": "semantic_forecast_inputs_v2_usage_v1",
        "branch_role": str(branch_role or ""),
        "input_ref": "forecast_features_v1.metadata.semantic_forecast_inputs_v2",
        "direct_math_used_fields": direct_math_used_fields,
        "harvest_only_fields": harvest_only_fields,
        "grouped_usage": grouped_usage,
        "usage_status": "harvested_with_usage_trace",
    }


def _harvest_sections(features: ForecastFeaturesV1) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    harvest = dict(((features.metadata or {}).get("semantic_forecast_inputs_v2", {}) or {}))
    return (
        dict(harvest.get("state_harvest", {}) or {}),
        dict(harvest.get("belief_harvest", {}) or {}),
        dict(harvest.get("barrier_harvest", {}) or {}),
        dict(harvest.get("secondary_harvest", {}) or {}),
    )


def _bridge_first_act_vs_wait_v1(features: ForecastFeaturesV1) -> dict[str, object]:
    bridge_root = dict(((features.metadata or {}).get("bridge_first_v1", {}) or {}))
    bridge = dict(bridge_root.get("act_vs_wait_bias_v1", {}) or {})
    return {
        "contract_version": str(bridge.get("contract_version", "") or "act_vs_wait_bias_v1"),
        "act_vs_wait_bias": _clamp01(float(bridge.get("act_vs_wait_bias", 0.5) or 0.5)),
        "false_break_risk": _clamp01(float(bridge.get("false_break_risk", 0.0) or 0.0)),
        "awareness_keep_allowed": bool(bridge.get("awareness_keep_allowed", False)),
        "component_scores": dict(bridge.get("component_scores", {}) or {}),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _bridge_first_management_hold_reward_hint_v1(features: ForecastFeaturesV1) -> dict[str, object]:
    bridge_root = dict(((features.metadata or {}).get("bridge_first_v1", {}) or {}))
    bridge = dict(bridge_root.get("management_hold_reward_hint_v1", {}) or {})
    return {
        "contract_version": str(
            bridge.get("contract_version", "") or "management_hold_reward_hint_v1"
        ),
        "hold_reward_hint": _clamp01(float(bridge.get("hold_reward_hint", 0.0) or 0.0)),
        "edge_to_edge_tailwind": _clamp01(float(bridge.get("edge_to_edge_tailwind", 0.0) or 0.0)),
        "hold_patience_allowed": bool(bridge.get("hold_patience_allowed", False)),
        "component_scores": dict(bridge.get("component_scores", {}) or {}),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _bridge_first_management_fast_cut_risk_v1(features: ForecastFeaturesV1) -> dict[str, object]:
    bridge_root = dict(((features.metadata or {}).get("bridge_first_v1", {}) or {}))
    bridge = dict(bridge_root.get("management_fast_cut_risk_v1", {}) or {})
    return {
        "contract_version": str(
            bridge.get("contract_version", "") or "management_fast_cut_risk_v1"
        ),
        "fast_cut_risk": _clamp01(float(bridge.get("fast_cut_risk", 0.0) or 0.0)),
        "collision_risk": _clamp01(float(bridge.get("collision_risk", 0.0) or 0.0)),
        "event_caution": _clamp01(float(bridge.get("event_caution", 0.0) or 0.0)),
        "cut_now_allowed": bool(bridge.get("cut_now_allowed", False)),
        "component_scores": dict(bridge.get("component_scores", {}) or {}),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _bridge_first_trend_continuation_maturity_v1(features: ForecastFeaturesV1) -> dict[str, object]:
    bridge_root = dict(((features.metadata or {}).get("bridge_first_v1", {}) or {}))
    bridge = dict(bridge_root.get("trend_continuation_maturity_v1", {}) or {})
    return {
        "contract_version": str(
            bridge.get("contract_version", "") or "trend_continuation_maturity_v1"
        ),
        "continuation_maturity": _clamp01(float(bridge.get("continuation_maturity", 0.0) or 0.0)),
        "exhaustion_pressure": _clamp01(float(bridge.get("exhaustion_pressure", 0.0) or 0.0)),
        "trend_hold_confidence": _clamp01(float(bridge.get("trend_hold_confidence", 0.0) or 0.0)),
        "component_scores": dict(bridge.get("component_scores", {}) or {}),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _bridge_first_advanced_input_reliability_v1(features: ForecastFeaturesV1) -> dict[str, object]:
    bridge_root = dict(((features.metadata or {}).get("bridge_first_v1", {}) or {}))
    bridge = dict(bridge_root.get("advanced_input_reliability_v1", {}) or {})
    return {
        "contract_version": str(
            bridge.get("contract_version", "") or "advanced_input_reliability_v1"
        ),
        "advanced_reliability": _clamp01(float(bridge.get("advanced_reliability", 0.0) or 0.0)),
        "order_book_reliable": bool(bridge.get("order_book_reliable", False)),
        "event_context_reliable": bool(bridge.get("event_context_reliable", False)),
        "component_scores": dict(bridge.get("component_scores", {}) or {}),
        "reason_summary": str(bridge.get("reason_summary", "") or ""),
    }


def _directional_expansion_support(session_expansion_state: str, session_regime_state: str, side: str) -> float:
    session_expansion_state = str(session_expansion_state or "")
    session_regime_state = str(session_regime_state or "")
    side = str(side or "").upper()
    if side == "BUY":
        if session_expansion_state == "UP_EXTENDED_EXPANSION":
            return 0.95
        if session_expansion_state == "UP_ACTIVE_EXPANSION":
            return 0.80
        if session_expansion_state == "UP_EARLY_EXPANSION":
            return 0.55
    else:
        if session_expansion_state == "DOWN_EXTENDED_EXPANSION":
            return 0.95
        if session_expansion_state == "DOWN_ACTIVE_EXPANSION":
            return 0.80
        if session_expansion_state == "DOWN_EARLY_EXPANSION":
            return 0.55
    if session_regime_state == "SESSION_EXPANSION":
        return 0.35
    return 0.0


def _directional_slope_support(topdown_slope_state: str, side: str) -> float:
    topdown_slope_state = str(topdown_slope_state or "")
    side = str(side or "").upper()
    if side == "BUY":
        if topdown_slope_state == "UP_SLOPE_ALIGNED":
            return 1.0
        if topdown_slope_state == "MIXED_SLOPE":
            return 0.45
    else:
        if topdown_slope_state == "DOWN_SLOPE_ALIGNED":
            return 1.0
        if topdown_slope_state == "MIXED_SLOPE":
            return 0.45
    if topdown_slope_state == "FLAT_SLOPE":
        return 0.20
    return 0.0


def _directional_confluence_support(topdown_confluence_state: str, side: str) -> float:
    topdown_confluence_state = str(topdown_confluence_state or "")
    side = str(side or "").upper()
    if side == "BUY":
        if topdown_confluence_state == "BULL_CONFLUENCE":
            return 1.0
    else:
        if topdown_confluence_state == "BEAR_CONFLUENCE":
            return 1.0
    if topdown_confluence_state == "WEAK_CONFLUENCE":
        return 0.45
    if topdown_confluence_state == "TOPDOWN_CONFLICT":
        return 0.20
    return 0.0


def _flip_instability_support(instability: float) -> float:
    instability = _clamp01(float(instability or 0.0))
    return _clamp01(1.0 - abs(instability - 0.35) / 0.35)


def _scene_transition_support(features: ForecastFeaturesV1) -> dict[str, object]:
    response = features.response_vector_v2
    state_harvest, belief_harvest, barrier_harvest, _secondary = _harvest_sections(features)

    session_regime_state = str(state_harvest.get("session_regime_state", "") or "")
    session_expansion_state = str(state_harvest.get("session_expansion_state", "") or "")
    topdown_slope_state = str(state_harvest.get("topdown_slope_state", "") or "")
    topdown_confluence_state = str(state_harvest.get("topdown_confluence_state", "") or "")
    execution_friction_state = str(state_harvest.get("execution_friction_state", "") or "")
    event_risk_state = str(state_harvest.get("event_risk_state", "") or "")

    flip_readiness = _clamp01(float(belief_harvest.get("flip_readiness", 0.0) or 0.0))
    belief_instability = _clamp01(float(belief_harvest.get("belief_instability", 0.0) or 0.0))
    instability_support = _flip_instability_support(belief_instability)

    edge_turn_relief_v1 = dict(barrier_harvest.get("edge_turn_relief_v1", {}) or {})
    breakout_fade_barrier_v1 = dict(barrier_harvest.get("breakout_fade_barrier_v1", {}) or {})
    duplicate_edge_barrier_v1 = dict(barrier_harvest.get("duplicate_edge_barrier_v1", {}) or {})
    micro_trap_barrier_v1 = dict(barrier_harvest.get("micro_trap_barrier_v1", {}) or {})

    buy_reversal_signal = max(float(response.lower_hold_up or 0.0), 0.65 * float(response.mid_reclaim_up or 0.0))
    sell_reversal_signal = max(float(response.upper_reject_down or 0.0), 0.65 * float(response.mid_lose_down or 0.0))
    buy_continuation_signal = max(float(response.upper_break_up or 0.0), 0.60 * float(response.mid_reclaim_up or 0.0))
    sell_continuation_signal = max(float(response.lower_break_down or 0.0), 0.60 * float(response.mid_lose_down or 0.0))

    edge_session_gate = 1.0 if session_regime_state == "SESSION_EDGE_ROTATION" else 0.0
    edge_confluence_gate = 1.0 if topdown_confluence_state in {"WEAK_CONFLUENCE", "TOPDOWN_CONFLICT"} else 0.0
    buy_edge_relief = _clamp01(float(edge_turn_relief_v1.get("buy_relief", 0.0) or 0.0))
    sell_edge_relief = _clamp01(float(edge_turn_relief_v1.get("sell_relief", 0.0) or 0.0))
    edge_scene_activation = _clamp01(max(edge_session_gate * edge_confluence_gate, buy_edge_relief, sell_edge_relief, 0.75 * flip_readiness))
    buy_edge_turn_support = _clamp01(
        edge_scene_activation
        * (
            (0.42 * buy_reversal_signal)
            + (0.33 * buy_edge_relief)
            + (0.25 * flip_readiness)
        )
    )
    sell_edge_turn_support = _clamp01(
        edge_scene_activation
        * (
            (0.42 * sell_reversal_signal)
            + (0.33 * sell_edge_relief)
            + (0.25 * flip_readiness)
        )
    )
    p_edge_turn_success = max(buy_edge_turn_support, sell_edge_turn_support)

    buy_expansion_support = _directional_expansion_support(session_expansion_state, session_regime_state, "BUY")
    sell_expansion_support = _directional_expansion_support(session_expansion_state, session_regime_state, "SELL")
    buy_slope_support = _directional_slope_support(topdown_slope_state, "BUY")
    sell_slope_support = _directional_slope_support(topdown_slope_state, "SELL")
    buy_confluence_support = _directional_confluence_support(topdown_confluence_state, "BUY")
    sell_confluence_support = _directional_confluence_support(topdown_confluence_state, "SELL")
    buy_fade_barrier = _clamp01(float(breakout_fade_barrier_v1.get("buy_fade_barrier", 0.0) or 0.0))
    sell_fade_barrier = _clamp01(float(breakout_fade_barrier_v1.get("sell_fade_barrier", 0.0) or 0.0))
    buy_breakout_scene_activation = _clamp01(max(buy_expansion_support, buy_slope_support, buy_confluence_support))
    sell_breakout_scene_activation = _clamp01(max(sell_expansion_support, sell_slope_support, sell_confluence_support))
    buy_breakout_continuation_support = _clamp01(
        buy_breakout_scene_activation
        * (
            (0.35 * buy_continuation_signal)
            + (0.24 * buy_expansion_support)
            + (0.18 * buy_slope_support)
            + (0.13 * buy_confluence_support)
            + (0.10 * (1.0 - buy_fade_barrier))
        )
    )
    sell_breakout_continuation_support = _clamp01(
        sell_breakout_scene_activation
        * (
            (0.35 * sell_continuation_signal)
            + (0.24 * sell_expansion_support)
            + (0.18 * sell_slope_support)
            + (0.13 * sell_confluence_support)
            + (0.10 * (1.0 - sell_fade_barrier))
        )
    )
    dominant_continuation_scene_support = max(buy_breakout_continuation_support, sell_breakout_continuation_support)

    duplicate_edge_common_boost = _clamp01(float(duplicate_edge_barrier_v1.get("common_boost", 0.0) or 0.0))
    micro_trap_common_boost = _clamp01(float(micro_trap_barrier_v1.get("common_boost", 0.0) or 0.0))
    failed_break_penalty = _clamp01((0.55 * duplicate_edge_common_boost) + (0.45 * micro_trap_common_boost))
    buy_failed_breakdown_clarity = _clamp01(
        max((float(response.lower_hold_up or 0.0) + (0.55 * float(response.mid_reclaim_up or 0.0))) - float(response.lower_break_down or 0.0), 0.0)
    )
    sell_failed_breakout_clarity = _clamp01(
        max((float(response.upper_reject_down or 0.0) + (0.55 * float(response.mid_lose_down or 0.0))) - float(response.upper_break_up or 0.0), 0.0)
    )
    failed_break_scene_activation = _clamp01(max(flip_readiness, 0.75 * instability_support))
    p_failed_breakdown_reclaim = _clamp01(
        failed_break_scene_activation
        * (
            (0.34 * buy_failed_breakdown_clarity)
            + (0.24 * buy_reversal_signal)
            + (0.22 * flip_readiness)
            + (0.20 * (1.0 - failed_break_penalty))
        )
    )
    p_failed_breakout_flush = _clamp01(
        failed_break_scene_activation
        * (
            (0.34 * sell_failed_breakout_clarity)
            + (0.24 * sell_reversal_signal)
            + (0.22 * flip_readiness)
            + (0.20 * (1.0 - failed_break_penalty))
        )
    )

    directional_exhaustion_basis = max(
        buy_expansion_support * (1.0 - buy_confluence_support),
        sell_expansion_support * (1.0 - sell_confluence_support),
    )
    friction_risk = 1.0 if execution_friction_state == "HIGH_FRICTION" else 0.45 if execution_friction_state == "MEDIUM_FRICTION" else 0.0
    event_risk = 1.0 if event_risk_state == "HIGH_EVENT_RISK" else 0.45 if event_risk_state == "WATCH_EVENT_RISK" else 0.0
    p_continuation_exhaustion = _clamp01(
        (0.45 * directional_exhaustion_basis)
        + (0.25 * max(buy_fade_barrier, sell_fade_barrier))
        + (0.15 * friction_risk)
        + (0.15 * event_risk)
    )

    return {
        "p_edge_turn_success": float(p_edge_turn_success),
        "p_failed_breakdown_reclaim": float(p_failed_breakdown_reclaim),
        "p_failed_breakout_flush": float(p_failed_breakout_flush),
        "p_continuation_exhaustion": float(p_continuation_exhaustion),
        "edge_turn": {
            "session_regime_state": session_regime_state,
            "topdown_confluence_state": topdown_confluence_state,
            "flip_readiness": float(flip_readiness),
            "buy_edge_relief": float(buy_edge_relief),
            "sell_edge_relief": float(sell_edge_relief),
            "buy_edge_turn_support": float(buy_edge_turn_support),
            "sell_edge_turn_support": float(sell_edge_turn_support),
        },
        "breakout_continuation": {
            "session_expansion_state": session_expansion_state,
            "topdown_slope_state": topdown_slope_state,
            "topdown_confluence_state": topdown_confluence_state,
            "buy_fade_barrier": float(buy_fade_barrier),
            "sell_fade_barrier": float(sell_fade_barrier),
            "buy_breakout_continuation_support": float(buy_breakout_continuation_support),
            "sell_breakout_continuation_support": float(sell_breakout_continuation_support),
        },
        "failed_break": {
            "flip_readiness": float(flip_readiness),
            "belief_instability": float(belief_instability),
            "instability_support": float(instability_support),
            "duplicate_edge_common_boost": float(duplicate_edge_common_boost),
            "micro_trap_common_boost": float(micro_trap_common_boost),
            "buy_failed_breakdown_clarity": float(buy_failed_breakdown_clarity),
            "sell_failed_breakout_clarity": float(sell_failed_breakout_clarity),
        },
    }


def _streak_norm(streak: int | float) -> float:
    return _clamp01(float(streak or 0.0) / 3.0)


def _hold_patience_support_gain(hold_gain: float) -> float:
    return _clamp01((float(hold_gain or 1.0) - 0.85) / 0.55)


def _execution_friction_score(state_label: str) -> float:
    state_label = str(state_label or "")
    if state_label == "HIGH_FRICTION":
        return 1.0
    if state_label == "MEDIUM_FRICTION":
        return 0.55
    if state_label == "LOW_FRICTION":
        return 0.10
    return 0.0


def _opposite_belief_rise(features: ForecastFeaturesV1, dominant_side: str) -> float:
    belief = features.belief_state_v1
    dominant_side = str(dominant_side or "BALANCED").upper()
    if dominant_side == "BUY":
        return _clamp01(
            (0.56 * float(belief.sell_belief or 0.0))
            + (0.24 * float(belief.sell_persistence or 0.0))
            + (0.20 * _streak_norm(getattr(belief, "sell_streak", 0)))
        )
    if dominant_side == "SELL":
        return _clamp01(
            (0.56 * float(belief.buy_belief or 0.0))
            + (0.24 * float(belief.buy_persistence or 0.0))
            + (0.20 * _streak_norm(getattr(belief, "buy_streak", 0)))
        )
    return _clamp01(
        max(
            (0.60 * float(belief.buy_belief or 0.0)) + (0.40 * float(belief.buy_persistence or 0.0)),
            (0.60 * float(belief.sell_belief or 0.0)) + (0.40 * float(belief.sell_persistence or 0.0)),
        )
    )


def _scene_management_support(features: ForecastFeaturesV1) -> dict[str, object]:
    belief = features.belief_state_v1
    state = features.state_vector_v2
    barrier = features.barrier_state_v1
    state_harvest, belief_harvest, barrier_harvest, _secondary = _harvest_sections(features)

    dominant_side = str(belief_harvest.get("dominant_side") or belief.dominant_side or "BALANCED").upper()
    dominant_mode = str(belief_harvest.get("dominant_mode") or belief.dominant_mode or "balanced")
    buy_streak = int(belief_harvest.get("buy_streak") or getattr(belief, "buy_streak", 0) or 0)
    sell_streak = int(belief_harvest.get("sell_streak") or getattr(belief, "sell_streak", 0) or 0)
    flip_readiness = _clamp01(float(belief_harvest.get("flip_readiness", getattr(belief, "flip_readiness", 0.0)) or 0.0))
    belief_instability = _clamp01(
        float(belief_harvest.get("belief_instability", getattr(belief, "belief_instability", 0.0)) or 0.0)
    )
    execution_friction_state = str(state_harvest.get("execution_friction_state", "") or "")
    middle_chop_barrier_v2 = dict(barrier_harvest.get("middle_chop_barrier_v2", {}) or {})
    duplicate_edge_barrier_v1 = dict(barrier_harvest.get("duplicate_edge_barrier_v1", {}) or {})
    post_event_cooldown_barrier_v1 = dict(barrier_harvest.get("post_event_cooldown_barrier_v1", {}) or {})

    dominant_persistence = max(float(belief.buy_persistence or 0.0), float(belief.sell_persistence or 0.0))
    dominant_streak = max(buy_streak, sell_streak)
    dominant_streak_norm = _streak_norm(dominant_streak)
    belief_spread_strength = _clamp01(abs(float(belief.belief_spread or 0.0)))
    hold_patience_support = _hold_patience_support_gain(float(state.hold_patience_gain or 1.0))
    fast_exit_bias = _clamp01(float(state.fast_exit_risk_penalty or 0.0))
    friction_score = _execution_friction_score(execution_friction_state)
    middle_scene_boost = _clamp01(float(middle_chop_barrier_v2.get("scene_boost", 0.0) or 0.0))
    duplicate_edge_penalty = _clamp01(float(duplicate_edge_barrier_v1.get("common_boost", 0.0) or 0.0))
    post_event_penalty = _clamp01(float(post_event_cooldown_barrier_v1.get("common_boost", 0.0) or 0.0))
    opposite_belief_rise = _opposite_belief_rise(features, dominant_side)
    dominant_side_clarity = 1.0 if dominant_side in {"BUY", "SELL"} else 0.0
    stability_support = _clamp01(1.0 - (0.55 * belief_instability))

    p_hold_through_noise = _clamp01(
        (0.24 * dominant_persistence)
        + (0.18 * dominant_streak_norm)
        + (0.18 * belief_spread_strength)
        + (0.18 * hold_patience_support)
        + (0.12 * stability_support)
        + (0.10 * dominant_side_clarity)
        - (0.12 * fast_exit_bias)
    )
    p_premature_exit_risk = _clamp01(
        (0.24 * belief_spread_strength)
        + (0.16 * dominant_side_clarity)
        + (0.20 * middle_scene_boost)
        + (0.16 * friction_score)
        + (0.14 * fast_exit_bias)
        + (0.10 * dominant_streak_norm)
        - (0.18 * opposite_belief_rise)
    )
    p_edge_to_edge_completion = _clamp01(
        (0.42 * p_hold_through_noise)
        + (0.20 * belief_spread_strength)
        + (0.16 * (1.0 - barrier.middle_chop_barrier))
        + (0.12 * dominant_persistence)
        + (0.10 * hold_patience_support)
    )
    p_flip_after_exit_quality = _clamp01(
        (0.34 * flip_readiness)
        + (0.24 * opposite_belief_rise)
        + (0.14 * (1.0 - duplicate_edge_penalty))
        + (0.14 * (1.0 - post_event_penalty))
        + (0.14 * stability_support)
    )
    p_stop_then_recover_risk = _clamp01(
        (0.40 * p_premature_exit_risk)
        + (0.32 * p_hold_through_noise)
        + (0.16 * (1.0 - p_flip_after_exit_quality))
        + (0.12 * fast_exit_bias)
    )

    return {
        "p_hold_through_noise": float(p_hold_through_noise),
        "p_premature_exit_risk": float(p_premature_exit_risk),
        "p_edge_to_edge_completion": float(p_edge_to_edge_completion),
        "p_flip_after_exit_quality": float(p_flip_after_exit_quality),
        "p_stop_then_recover_risk": float(p_stop_then_recover_risk),
        "good_entry_hold": {
            "dominant_side": dominant_side,
            "dominant_mode": dominant_mode,
            "dominant_persistence": float(dominant_persistence),
            "dominant_streak": int(dominant_streak),
            "hold_patience_gain": float(state.hold_patience_gain or 1.0),
            "hold_patience_support": float(hold_patience_support),
            "fast_exit_risk_penalty": float(state.fast_exit_risk_penalty or 0.0),
        },
        "premature_exit": {
            "belief_spread_strength": float(belief_spread_strength),
            "middle_scene_boost": float(middle_scene_boost),
            "execution_friction_state": execution_friction_state,
            "friction_score": float(friction_score),
            "opposite_belief_rise": float(opposite_belief_rise),
        },
        "reentry_flip": {
            "flip_readiness": float(flip_readiness),
            "belief_instability": float(belief_instability),
            "duplicate_edge_penalty": float(duplicate_edge_penalty),
            "post_event_penalty": float(post_event_penalty),
            "opposite_belief_rise": float(opposite_belief_rise),
        },
    }


class ForecastEngineInterface(Protocol):
    def build_transition_forecast(self, features: ForecastFeaturesV1) -> TransitionForecast: ...

    def build_trade_management_forecast(self, features: ForecastFeaturesV1) -> TradeManagementForecast: ...


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp11(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _side_readiness(evidence: float, belief: float, persistence: float) -> float:
    return _clamp01((0.50 * evidence) + (0.35 * belief) + (0.15 * persistence))


def _base_readiness(evidence: float, belief: float) -> float:
    return _clamp01((0.58 * evidence) + (0.42 * belief))


def _transition_age_norm(features: ForecastFeaturesV1) -> float:
    return _clamp01(float(getattr(features.belief_state_v1, "transition_age", 0.0) or 0.0) / 5.0)


def _continuation_observe_gate(features: ForecastFeaturesV1, side: str) -> float:
    response = features.response_vector_v2
    belief = features.belief_state_v1
    spread_strength = abs(float(belief.belief_spread or 0.0))
    age_norm = _transition_age_norm(features)
    conflict_score = float(features.position_conflict_score or 0.0)
    secondary = str(features.position_secondary_context_label or "")

    if side == "BUY":
        continuation_signal = max(
            float(response.upper_break_up or 0.0),
            0.50 * float(response.mid_reclaim_up or 0.0),
        )
        opposing_signal = max(
            float(response.upper_reject_down or 0.0),
            0.50 * float(response.mid_lose_down or 0.0),
        )
        persistence = float(belief.buy_persistence or 0.0)
        context_bonus = 1.0 if secondary == "UPPER_CONTEXT" else 0.6 if secondary == "NEUTRAL_CONTEXT" else 0.35
    else:
        continuation_signal = max(
            float(response.lower_break_down or 0.0),
            0.50 * float(response.mid_lose_down or 0.0),
        )
        opposing_signal = max(
            float(response.lower_hold_up or 0.0),
            0.50 * float(response.mid_reclaim_up or 0.0),
        )
        persistence = float(belief.sell_persistence or 0.0)
        context_bonus = 1.0 if secondary == "LOWER_CONTEXT" else 0.6 if secondary == "NEUTRAL_CONTEXT" else 0.35

    edge_conflict = min(continuation_signal, opposing_signal)
    base_support = _clamp01(
        (0.20 * continuation_signal)
        + (0.30 * persistence)
        + (0.20 * age_norm)
        + (0.15 * spread_strength)
        + (0.15 * context_bonus)
    )
    competitive_penalty = _clamp01(
        (0.65 * opposing_signal)
        + (0.35 * edge_conflict)
        + (0.20 * conflict_score)
    )
    gate = _clamp01(base_support * (1.0 - competitive_penalty))
    return gate


def _reversal_path_support(features: ForecastFeaturesV1, side: str, reversal_fit: float) -> tuple[float, float, float]:
    response = features.response_vector_v2
    secondary = str(features.position_secondary_context_label or "")
    if side == "BUY":
        reversal_signal = max(
            float(response.lower_hold_up or 0.0),
            0.50 * float(response.mid_reclaim_up or 0.0),
        )
        competing_break = max(
            float(response.lower_break_down or 0.0),
            0.35 * float(response.upper_break_up or 0.0),
        )
        context_bonus = 1.0 if secondary == "LOWER_CONTEXT" else 0.6 if secondary == "NEUTRAL_CONTEXT" else 0.35
    else:
        reversal_signal = max(
            float(response.upper_reject_down or 0.0),
            0.50 * float(response.mid_lose_down or 0.0),
        )
        competing_break = max(
            float(response.upper_break_up or 0.0),
            0.35 * float(response.lower_break_down or 0.0),
        )
        context_bonus = 1.0 if secondary == "UPPER_CONTEXT" else 0.6 if secondary == "NEUTRAL_CONTEXT" else 0.35

    clarity = _clamp01(max(reversal_signal - competing_break, 0.0))
    support = _clamp01(
        (0.18 * reversal_signal)
        + (0.14 * clarity)
        + (0.06 * reversal_fit)
        + (0.04 * context_bonus)
    )
    return reversal_signal, clarity, support


def _reversal_fit(features: ForecastFeaturesV1, side: str) -> float:
    primary = str(features.position_primary_label or "")
    bias = str(features.position_bias_label or "")
    secondary = str(features.position_secondary_context_label or "")
    lower_friendly = {
        "ALIGNED_LOWER_STRONG": 1.00,
        "ALIGNED_LOWER_WEAK": 0.92,
        "LOWER_BIAS": 0.86,
        "MIDDLE_LOWER_BIAS": 0.78,
        "ALIGNED_MIDDLE": 0.56,
        "UNRESOLVED_POSITION": 0.42,
    }
    upper_friendly = {
        "ALIGNED_UPPER_STRONG": 1.00,
        "ALIGNED_UPPER_WEAK": 0.92,
        "UPPER_BIAS": 0.86,
        "MIDDLE_UPPER_BIAS": 0.78,
        "ALIGNED_MIDDLE": 0.56,
        "UNRESOLVED_POSITION": 0.42,
    }
    if side == "BUY":
        fit = lower_friendly.get(primary, 0.35)
        if bias == "MIDDLE_LOWER_BIAS":
            fit = max(fit, 0.78)
        if secondary == "LOWER_CONTEXT":
            fit += 0.06
        elif secondary == "UPPER_CONTEXT":
            fit -= 0.06
        return _clamp01(fit)
    fit = upper_friendly.get(primary, 0.35)
    if bias == "MIDDLE_UPPER_BIAS":
        fit = max(fit, 0.78)
    if secondary == "UPPER_CONTEXT":
        fit += 0.06
    elif secondary == "LOWER_CONTEXT":
        fit -= 0.06
    return _clamp01(fit)


def _continuation_fit(features: ForecastFeaturesV1, side: str) -> float:
    primary = str(features.position_primary_label or "")
    bias = str(features.position_bias_label or "")
    secondary = str(features.position_secondary_context_label or "")
    upper_friendly = {
        "ALIGNED_UPPER_STRONG": 1.00,
        "ALIGNED_UPPER_WEAK": 0.94,
        "UPPER_BIAS": 0.86,
        "MIDDLE_UPPER_BIAS": 0.74,
        "UNRESOLVED_POSITION": 0.48,
        "ALIGNED_MIDDLE": 0.40,
    }
    lower_friendly = {
        "ALIGNED_LOWER_STRONG": 1.00,
        "ALIGNED_LOWER_WEAK": 0.94,
        "LOWER_BIAS": 0.86,
        "MIDDLE_LOWER_BIAS": 0.74,
        "UNRESOLVED_POSITION": 0.48,
        "ALIGNED_MIDDLE": 0.40,
    }
    if side == "BUY":
        fit = upper_friendly.get(primary, 0.30)
        if bias == "MIDDLE_UPPER_BIAS":
            fit = max(fit, 0.74)
        if secondary == "UPPER_CONTEXT":
            fit += 0.08
        elif secondary == "LOWER_CONTEXT":
            fit -= 0.08
        return _clamp01(fit)
    fit = lower_friendly.get(primary, 0.30)
    if bias == "MIDDLE_LOWER_BIAS":
        fit = max(fit, 0.74)
    if secondary == "LOWER_CONTEXT":
        fit += 0.08
    elif secondary == "UPPER_CONTEXT":
        fit -= 0.08
    return _clamp01(fit)


def extract_forecast_gap_metrics(
    transition_forecast: TransitionForecast | None,
    trade_management_forecast: TradeManagementForecast | None,
) -> dict[str, float]:
    transition_meta = ((getattr(transition_forecast, "metadata", None) or {}) if transition_forecast is not None else {})
    management_meta = (
        ((getattr(trade_management_forecast, "metadata", None) or {}) if trade_management_forecast is not None else {})
    )
    transition_side_separation = float(transition_meta.get("side_separation", 0.0) or 0.0)
    transition_confirm_fake_gap = float(transition_meta.get("confirm_fake_gap", 0.0) or 0.0)
    transition_reversal_continuation_gap = float(transition_meta.get("reversal_continuation_gap", 0.0) or 0.0)
    management_continue_fail_gap = float(management_meta.get("continue_fail_gap", 0.0) or 0.0)
    management_recover_reentry_gap = float(management_meta.get("recover_reentry_gap", 0.0) or 0.0)
    transition_components = dict(transition_meta.get("component_scores", {}) or {})
    management_components = dict(management_meta.get("component_scores", {}) or {})
    management_scene_support = dict(management_meta.get("management_scene_support_v1", {}) or {})

    p_hold_through_noise = _clamp01(float(management_scene_support.get("p_hold_through_noise", 0.0) or 0.0))
    p_premature_exit_risk = _clamp01(float(management_scene_support.get("p_premature_exit_risk", 0.0) or 0.0))
    p_flip_after_exit_quality = _clamp01(float(management_scene_support.get("p_flip_after_exit_quality", 0.0) or 0.0))
    p_continue_favor = _clamp01(float(getattr(trade_management_forecast, "p_continue_favor", 0.0) or 0.0))
    p_fail_now = _clamp01(float(getattr(trade_management_forecast, "p_fail_now", 0.0) or 0.0))
    p_better_reentry_if_cut = _clamp01(float(getattr(trade_management_forecast, "p_better_reentry_if_cut", 0.0) or 0.0))

    wait_confirm_gap = _clamp11(transition_confirm_fake_gap + (0.30 * transition_side_separation))
    hold_exit_gap = _clamp11(
        ((0.60 * p_continue_favor) + (0.40 * p_hold_through_noise))
        - ((0.60 * p_fail_now) + (0.40 * p_premature_exit_risk))
    )
    same_side_flip_gap = _clamp11(
        ((0.55 * p_hold_through_noise) + (0.45 * p_continue_favor))
        - ((0.55 * p_flip_after_exit_quality) + (0.45 * p_better_reentry_if_cut))
    )
    dominant_belief = _clamp01(float(transition_components.get("dominant_belief", 0.0) or 0.0))
    dominant_persistence = _clamp01(float(transition_components.get("dominant_persistence", 0.0) or 0.0))
    belief_support = _clamp01((0.60 * dominant_belief) + (0.40 * dominant_persistence))
    barrier_pressure = _clamp01(
        max(
            float(transition_components.get("structural_friction", 0.0) or 0.0),
            float(management_components.get("active_barrier", 0.0) or 0.0),
            float(management_components.get("opposing_barrier", 0.0) or 0.0),
        )
    )
    belief_barrier_tension_gap = _clamp11(belief_support - barrier_pressure)

    def _gap_state(value: float, positive_label: str, negative_label: str, threshold: float = 0.10) -> str:
        if value >= threshold:
            return positive_label
        if value <= -threshold:
            return negative_label
        return "BALANCED"

    execution_gap_support_v1 = {
        "confirm_wait_state": _gap_state(wait_confirm_gap, "CONFIRM_CLEAR", "WAIT_BIASED"),
        "hold_exit_state": _gap_state(hold_exit_gap, "HOLD_CLEAR", "EXIT_CLEAR"),
        "same_side_flip_state": _gap_state(same_side_flip_gap, "SAME_SIDE_CLEAR", "FLIP_CLEAR"),
        "belief_barrier_tension_state": _gap_state(
            belief_barrier_tension_gap,
            "BELIEF_DOMINANT",
            "BARRIER_DOMINANT",
            threshold=0.08,
        ),
    }

    dominant_execution_gap = max(
        (
            ("wait_confirm_gap", abs(wait_confirm_gap)),
            ("hold_exit_gap", abs(hold_exit_gap)),
            ("same_side_flip_gap", abs(same_side_flip_gap)),
            ("belief_barrier_tension_gap", abs(belief_barrier_tension_gap)),
        ),
        key=lambda item: item[1],
    )[0]

    gap_pre_ml_source_values = {
        "transition_side_separation": float(transition_side_separation),
        "transition_confirm_fake_gap": float(transition_confirm_fake_gap),
        "transition_reversal_continuation_gap": float(transition_reversal_continuation_gap),
        "management_continue_fail_gap": float(management_continue_fail_gap),
        "management_recover_reentry_gap": float(management_recover_reentry_gap),
        "hold_exit_gap": float(hold_exit_gap),
        "same_side_flip_gap": float(same_side_flip_gap),
    }

    return {
        "transition_side_separation": transition_side_separation,
        "transition_confirm_fake_gap": transition_confirm_fake_gap,
        "transition_reversal_continuation_gap": transition_reversal_continuation_gap,
        "management_continue_fail_gap": management_continue_fail_gap,
        "management_recover_reentry_gap": management_recover_reentry_gap,
        "wait_confirm_gap": float(wait_confirm_gap),
        "hold_exit_gap": float(hold_exit_gap),
        "same_side_flip_gap": float(same_side_flip_gap),
        "belief_barrier_tension_gap": float(belief_barrier_tension_gap),
        "metadata": {
            **_forecast_freeze_metadata("gap_metrics_branch"),
            **_forecast_pre_ml_metadata("gap_metrics_branch", gap_pre_ml_source_values),
            "forecast_contract": "forecast_gap_metrics_v1",
            "mapper_version": "forecast_gap_metrics_v1_fg2",
            "promotion_phase": "FR4",
            "comparison_input_fields": [
                "transition_forecast_v1",
                "trade_management_forecast_v1",
            ],
            "semantic_forecast_inputs_v2_usage_v1": {
                "contract_version": "semantic_forecast_inputs_v2_usage_v1",
                "branch_role": "gap_metrics_branch",
                "input_ref": "transition_forecast_v1 + trade_management_forecast_v1",
                "direct_math_used_fields": [],
                "harvest_only_fields": [],
                "grouped_usage": {},
                "usage_status": "derived_from_branch_outputs_only",
            },
            "branch_output_usage_v2": {
                "transition_fields": [
                    "side_separation",
                    "confirm_fake_gap",
                    "reversal_continuation_gap",
                    "component_scores.dominant_belief",
                    "component_scores.dominant_persistence",
                    "component_scores.structural_friction",
                ],
                "trade_management_fields": [
                    "continue_fail_gap",
                    "recover_reentry_gap",
                    "p_continue_favor",
                    "p_fail_now",
                    "p_better_reentry_if_cut",
                    "component_scores.active_barrier",
                    "component_scores.opposing_barrier",
                    "management_scene_support_v1.p_hold_through_noise",
                    "management_scene_support_v1.p_premature_exit_risk",
                    "management_scene_support_v1.p_flip_after_exit_quality",
                ],
            },
            "gap_semantics_v2": {
                "transition_side_separation": "how clearly buy confirm and sell confirm differ",
                "transition_confirm_fake_gap": "whether confirm currently beats false-break pressure",
                "transition_reversal_continuation_gap": "which transition path is clearer",
                "management_continue_fail_gap": "whether hold currently beats immediate fail pressure",
                "management_recover_reentry_gap": "whether recover-through-noise beats cut-and-reenter",
                "wait_confirm_gap": "execution-facing difference between waiting bias and confirm clarity",
                "hold_exit_gap": "execution-facing difference between holding thesis and exiting thesis",
                "same_side_flip_gap": "whether staying with the current side is clearer than flipping after cut",
                "belief_barrier_tension_gap": "whether belief support currently beats barrier pressure",
            },
            "execution_gap_support_v1": {
                **execution_gap_support_v1,
                "dominant_execution_gap": dominant_execution_gap,
            },
        },
    }


def _build_transition_forecast_rule_impl(features: ForecastFeaturesV1) -> TransitionForecast:
    evidence = features.evidence_vector_v1
    belief = features.belief_state_v1
    barrier = features.barrier_state_v1

    buy_readiness = _side_readiness(
        evidence.buy_total_evidence,
        belief.buy_belief,
        belief.buy_persistence,
    )
    sell_readiness = _side_readiness(
        evidence.sell_total_evidence,
        belief.sell_belief,
        belief.sell_persistence,
    )

    buy_confirm_core = _base_readiness(evidence.buy_total_evidence, belief.buy_belief)
    sell_confirm_core = _base_readiness(evidence.sell_total_evidence, belief.sell_belief)
    buy_confirm_support = (0.10 * belief.buy_persistence) + (0.08 * (1.0 - barrier.buy_barrier))
    sell_confirm_support = (0.10 * belief.sell_persistence) + (0.08 * (1.0 - barrier.sell_barrier))
    buy_confirm_readiness = _clamp01(buy_confirm_core + buy_confirm_support)
    sell_confirm_readiness = _clamp01(sell_confirm_core + sell_confirm_support)

    buy_reversal_fit = _reversal_fit(features, "BUY")
    sell_reversal_fit = _reversal_fit(features, "SELL")
    buy_reversal_core = _base_readiness(evidence.buy_reversal_evidence, belief.buy_belief)
    sell_reversal_core = _base_readiness(evidence.sell_reversal_evidence, belief.sell_belief)
    buy_reversal_score = _clamp01(
        (0.72 * buy_reversal_core)
        + (0.18 * buy_reversal_fit)
        + (0.10 * (1.0 - barrier.buy_barrier))
    )
    sell_reversal_score = _clamp01(
        (0.72 * sell_reversal_core)
        + (0.18 * sell_reversal_fit)
        + (0.10 * (1.0 - barrier.sell_barrier))
    )
    p_reversal_success = max(buy_reversal_score, sell_reversal_score)

    buy_continuation_fit = _continuation_fit(features, "BUY")
    sell_continuation_fit = _continuation_fit(features, "SELL")
    buy_continuation_core = _base_readiness(evidence.buy_continuation_evidence, belief.buy_belief)
    sell_continuation_core = _base_readiness(evidence.sell_continuation_evidence, belief.sell_belief)
    buy_continuation_score = _clamp01(
        (0.72 * buy_continuation_core)
        + (0.18 * buy_continuation_fit)
        + (0.10 * (1.0 - barrier.buy_barrier))
    )
    sell_continuation_score = _clamp01(
        (0.72 * sell_continuation_core)
        + (0.18 * sell_continuation_fit)
        + (0.10 * (1.0 - barrier.sell_barrier))
    )
    p_continuation_success = max(buy_continuation_score, sell_continuation_score)

    buy_confirm_momentum = _clamp01(
        (0.18 * max(buy_confirm_readiness - sell_confirm_readiness, 0.0))
        + (0.12 * max(float(belief.belief_spread or 0.0), 0.0))
        + (0.08 * belief.buy_persistence)
    )
    sell_confirm_momentum = _clamp01(
        (0.18 * max(sell_confirm_readiness - buy_confirm_readiness, 0.0))
        + (0.12 * max(-float(belief.belief_spread or 0.0), 0.0))
        + (0.08 * belief.sell_persistence)
    )
    dominant_readiness = max(buy_confirm_readiness, sell_confirm_readiness)
    opposing_readiness = min(buy_confirm_readiness, sell_confirm_readiness)
    dominant_belief = max(belief.buy_belief, belief.sell_belief)
    dominant_persistence = max(belief.buy_persistence, belief.sell_persistence)
    act_wait_bridge = _bridge_first_act_vs_wait_v1(features)
    bf1_act_vs_wait_bias = _clamp01(float(act_wait_bridge.get("act_vs_wait_bias", 0.5) or 0.5))
    bf1_false_break_risk = _clamp01(float(act_wait_bridge.get("false_break_risk", 0.0) or 0.0))
    bf1_awareness_keep_allowed = bool(act_wait_bridge.get("awareness_keep_allowed", False))
    advanced_reliability_bridge = _bridge_first_advanced_input_reliability_v1(features)
    bf5_advanced_reliability = _clamp01(
        float(advanced_reliability_bridge.get("advanced_reliability", 0.0) or 0.0)
    )
    bf5_order_book_reliable = bool(advanced_reliability_bridge.get("order_book_reliable", False))
    bf5_event_context_reliable = bool(
        advanced_reliability_bridge.get("event_context_reliable", False)
    )
    bf5_transition_reliability = _clamp01(
        (0.80 * bf5_advanced_reliability) + (0.20 * float(bf5_event_context_reliable))
    )
    structural_friction = max(barrier.middle_chop_barrier, barrier.conflict_barrier)
    spread_strength = abs(float(belief.belief_spread or 0.0))
    false_break_pressure = _clamp01(
        (
            dominant_readiness
            * (1.0 - dominant_belief)
            * (0.55 + (0.45 * structural_friction))
        )
        + (0.18 * (1.0 - spread_strength))
        + (0.16 * (1.0 - dominant_persistence))
        + (0.12 * opposing_readiness)
    )
    buy_path_mode = "continuation" if buy_continuation_score >= buy_reversal_score else "reversal"
    sell_path_mode = "continuation" if sell_continuation_score >= sell_reversal_score else "reversal"
    buy_continuation_observe_gate = _continuation_observe_gate(features, "BUY")
    sell_continuation_observe_gate = _continuation_observe_gate(features, "SELL")
    buy_confirm_path_gate = buy_continuation_observe_gate if buy_path_mode == "continuation" else 1.0
    sell_confirm_path_gate = sell_continuation_observe_gate if sell_path_mode == "continuation" else 1.0
    buy_reversal_signal, buy_reversal_clarity, buy_reversal_path_support = _reversal_path_support(
        features,
        "BUY",
        buy_reversal_fit,
    )
    sell_reversal_signal, sell_reversal_clarity, sell_reversal_path_support = _reversal_path_support(
        features,
        "SELL",
        sell_reversal_fit,
    )
    buy_confirm_path_support = buy_reversal_path_support if buy_path_mode == "reversal" else 0.0
    sell_confirm_path_support = sell_reversal_path_support if sell_path_mode == "reversal" else 0.0
    dominant_reversal_support = 0.0
    if buy_path_mode == "reversal" and buy_confirm_readiness >= sell_confirm_readiness:
        dominant_reversal_support = buy_reversal_path_support
    if sell_path_mode == "reversal" and sell_confirm_readiness >= buy_confirm_readiness:
        dominant_reversal_support = max(dominant_reversal_support, sell_reversal_path_support)
    scene_transition_support = _scene_transition_support(features)
    edge_turn_support = dict(scene_transition_support.get("edge_turn", {}) or {})
    breakout_scene_support = dict(scene_transition_support.get("breakout_continuation", {}) or {})
    buy_edge_turn_support = _clamp01(float(edge_turn_support.get("buy_edge_turn_support", 0.0) or 0.0))
    sell_edge_turn_support = _clamp01(float(edge_turn_support.get("sell_edge_turn_support", 0.0) or 0.0))
    buy_breakout_scene_support = _clamp01(
        float(breakout_scene_support.get("buy_breakout_continuation_support", 0.0) or 0.0)
    )
    sell_breakout_scene_support = _clamp01(
        float(breakout_scene_support.get("sell_breakout_continuation_support", 0.0) or 0.0)
    )
    p_edge_turn_success = _clamp01(float(scene_transition_support.get("p_edge_turn_success", 0.0) or 0.0))
    p_failed_breakdown_reclaim = _clamp01(
        float(scene_transition_support.get("p_failed_breakdown_reclaim", 0.0) or 0.0)
    )
    p_failed_breakout_flush = _clamp01(
        float(scene_transition_support.get("p_failed_breakout_flush", 0.0) or 0.0)
    )
    p_continuation_exhaustion = _clamp01(
        float(scene_transition_support.get("p_continuation_exhaustion", 0.0) or 0.0)
    )
    if buy_path_mode == "reversal":
        buy_confirm_path_support = _clamp01(
            buy_confirm_path_support + (0.14 * buy_edge_turn_support) + (0.10 * p_failed_breakdown_reclaim)
        )
    else:
        buy_confirm_path_support = _clamp01(buy_confirm_path_support + (0.12 * buy_breakout_scene_support))
    if sell_path_mode == "reversal":
        sell_confirm_path_support = _clamp01(
            sell_confirm_path_support + (0.14 * sell_edge_turn_support) + (0.10 * p_failed_breakout_flush)
        )
    else:
        sell_confirm_path_support = _clamp01(sell_confirm_path_support + (0.12 * sell_breakout_scene_support))
    dominant_reversal_support = max(
        dominant_reversal_support,
        buy_edge_turn_support if buy_path_mode == "reversal" and buy_confirm_readiness >= sell_confirm_readiness else 0.0,
        sell_edge_turn_support if sell_path_mode == "reversal" and sell_confirm_readiness >= buy_confirm_readiness else 0.0,
    )
    false_break_pressure = _clamp01(
        false_break_pressure
        * (1.0 - (0.45 * dominant_reversal_support))
        * (1.0 - (0.10 * max(p_failed_breakdown_reclaim, p_failed_breakout_flush)))
    )
    false_break_pressure = _clamp01(false_break_pressure + (0.08 * p_continuation_exhaustion))
    false_break_pressure = _clamp01(
        (0.84 * false_break_pressure)
        + (0.16 * bf1_false_break_risk * (0.60 + (0.40 * bf5_transition_reliability)))
        - (0.06 * max(bf1_act_vs_wait_bias - 0.50, 0.0))
    )
    p_buy_confirm = _clamp01(
        (buy_confirm_readiness + buy_confirm_momentum + buy_confirm_path_support)
        * buy_confirm_path_gate
        * (1.0 - (0.55 * false_break_pressure))
    )
    p_sell_confirm = _clamp01(
        (sell_confirm_readiness + sell_confirm_momentum + sell_confirm_path_support)
        * sell_confirm_path_gate
        * (1.0 - (0.55 * false_break_pressure))
    )
    dominant_confirm = max(p_buy_confirm, p_sell_confirm)
    p_false_break = _clamp01(false_break_pressure * (1.0 - (0.75 * dominant_confirm)))

    reversal_support = _clamp01(
        (0.70 * max(evidence.buy_reversal_evidence, evidence.sell_reversal_evidence))
        + (0.30 * max(buy_reversal_fit, sell_reversal_fit))
    )
    continuation_support = _clamp01(
        (0.70 * max(evidence.buy_continuation_evidence, evidence.sell_continuation_evidence))
        + (0.30 * max(buy_continuation_fit, sell_continuation_fit))
    )
    reversal_competition_pressure = _clamp01((0.75 * p_continuation_success) + (0.25 * continuation_support))
    continuation_competition_pressure = _clamp01((0.75 * p_reversal_success) + (0.25 * reversal_support))
    p_reversal_success = _clamp01(
        ((0.80 * p_reversal_success) + (0.20 * reversal_support))
        * (1.0 - (0.40 * reversal_competition_pressure))
    )
    p_continuation_success = _clamp01(
        ((0.80 * p_continuation_success) + (0.20 * continuation_support))
        * (1.0 - (0.40 * continuation_competition_pressure))
    )
    p_reversal_success = _clamp01(
        p_reversal_success
        + (0.12 * p_edge_turn_success)
        + (0.14 * max(p_failed_breakdown_reclaim, p_failed_breakout_flush))
    )
    p_continuation_success = _clamp01(
        p_continuation_success
        + (0.12 * max(buy_breakout_scene_support, sell_breakout_scene_support))
        - (0.10 * max(p_failed_breakdown_reclaim, p_failed_breakout_flush))
        - (0.08 * p_continuation_exhaustion)
    )
    side_separation = abs(p_buy_confirm - p_sell_confirm)
    confirm_fake_gap = dominant_confirm - p_false_break
    reversal_continuation_gap = abs(p_reversal_success - p_continuation_success)

    if p_buy_confirm > p_sell_confirm:
        dominant_side = "BUY"
    elif p_sell_confirm > p_buy_confirm:
        dominant_side = "SELL"
    else:
        dominant_side = "BALANCED"

    dominant_mode = "reversal" if p_reversal_success >= p_continuation_success else "continuation"
    transition_pre_ml_source_values = {
        "p_buy_confirm": float(p_buy_confirm),
        "p_sell_confirm": float(p_sell_confirm),
        "p_reversal_success": float(p_reversal_success),
        "p_continuation_success": float(p_continuation_success),
        "p_false_break": float(p_false_break),
        "p_edge_turn_success": float(p_edge_turn_success),
    }

    return TransitionForecast(
        p_buy_confirm=p_buy_confirm,
        p_sell_confirm=p_sell_confirm,
        p_false_break=p_false_break,
        p_reversal_success=p_reversal_success,
        p_continuation_success=p_continuation_success,
        metadata={
            **_forecast_freeze_metadata("transition_branch"),
            **_forecast_pre_ml_metadata("transition_branch", transition_pre_ml_source_values),
            "semantic_forecast_inputs_v2_usage_v1": _semantic_forecast_inputs_usage(
                "transition_branch",
                used_fields={
                    "state_harvest": [
                        "session_regime_state",
                        "session_expansion_state",
                        "topdown_slope_state",
                        "topdown_confluence_state",
                        "execution_friction_state",
                        "event_risk_state",
                    ],
                    "belief_harvest": [
                        "flip_readiness",
                        "belief_instability",
                    ],
                    "barrier_harvest": [
                        "edge_turn_relief_v1",
                        "breakout_fade_barrier_v1",
                        "duplicate_edge_barrier_v1",
                        "micro_trap_barrier_v1",
                    ],
                    "secondary_harvest": [
                        "advanced_input_activation_state",
                        "tick_flow_state",
                        "order_book_state",
                    ],
                },
            ),
            "forecast_contract": "transition_forecast_v1",
            "mapper_version": "transition_forecast_v1_fc11",
            "score_formula_version": "transition_fc11_scene_transition_refinement_v1",
            "features_contract": str(
                ((features.metadata or {}).get("forecast_features_contract", {}) or {}).get("contract_version", "")
                or "forecast_features_v1"
            ),
            "scene_transition_support_v1": scene_transition_support,
            "bridge_first_v1": {
                "act_vs_wait_bias_v1": act_wait_bridge,
                "advanced_input_reliability_v1": advanced_reliability_bridge,
            },
            "component_scores": {
                "buy_total_evidence": evidence.buy_total_evidence,
                "sell_total_evidence": evidence.sell_total_evidence,
                "buy_belief": belief.buy_belief,
                "sell_belief": belief.sell_belief,
                "buy_persistence": belief.buy_persistence,
                "sell_persistence": belief.sell_persistence,
                "buy_barrier": barrier.buy_barrier,
                "sell_barrier": barrier.sell_barrier,
                "buy_readiness": buy_readiness,
                "sell_readiness": sell_readiness,
                "buy_confirm_core": buy_confirm_core,
                "sell_confirm_core": sell_confirm_core,
                "buy_confirm_support": buy_confirm_support,
                "sell_confirm_support": sell_confirm_support,
                "buy_confirm_readiness": buy_confirm_readiness,
                "sell_confirm_readiness": sell_confirm_readiness,
                "buy_confirm_momentum": buy_confirm_momentum,
                "sell_confirm_momentum": sell_confirm_momentum,
                "buy_path_mode": buy_path_mode,
                "sell_path_mode": sell_path_mode,
                "buy_continuation_observe_gate": buy_continuation_observe_gate,
                "sell_continuation_observe_gate": sell_continuation_observe_gate,
                "buy_confirm_path_gate": buy_confirm_path_gate,
                "sell_confirm_path_gate": sell_confirm_path_gate,
                "buy_reversal_signal": buy_reversal_signal,
                "sell_reversal_signal": sell_reversal_signal,
                "buy_reversal_clarity": buy_reversal_clarity,
                "sell_reversal_clarity": sell_reversal_clarity,
                "buy_reversal_path_support": buy_reversal_path_support,
                "sell_reversal_path_support": sell_reversal_path_support,
                  "buy_confirm_path_support": buy_confirm_path_support,
                  "sell_confirm_path_support": sell_confirm_path_support,
                  "buy_edge_turn_support": buy_edge_turn_support,
                  "sell_edge_turn_support": sell_edge_turn_support,
                  "buy_breakout_scene_support": buy_breakout_scene_support,
                  "sell_breakout_scene_support": sell_breakout_scene_support,
                  "p_edge_turn_success": p_edge_turn_success,
                  "p_failed_breakdown_reclaim": p_failed_breakdown_reclaim,
                  "p_failed_breakout_flush": p_failed_breakout_flush,
                  "p_continuation_exhaustion": p_continuation_exhaustion,
                  "dominant_reversal_support": dominant_reversal_support,
                "transition_age_norm": _transition_age_norm(features),
                "buy_continuation_base_support": _clamp01(
                    (0.20 * max(float(features.response_vector_v2.upper_break_up or 0.0), 0.50 * float(features.response_vector_v2.mid_reclaim_up or 0.0)))
                    + (0.30 * float(belief.buy_persistence or 0.0))
                    + (0.20 * _transition_age_norm(features))
                    + (0.15 * spread_strength)
                    + (
                        0.15
                        * (
                            1.0
                            if str(features.position_secondary_context_label or "") == "UPPER_CONTEXT"
                            else 0.6 if str(features.position_secondary_context_label or "") == "NEUTRAL_CONTEXT" else 0.35
                        )
                    )
                ),
                "sell_continuation_base_support": _clamp01(
                    (0.20 * max(float(features.response_vector_v2.lower_break_down or 0.0), 0.50 * float(features.response_vector_v2.mid_lose_down or 0.0)))
                    + (0.30 * float(belief.sell_persistence or 0.0))
                    + (0.20 * _transition_age_norm(features))
                    + (0.15 * spread_strength)
                    + (
                        0.15
                        * (
                            1.0
                            if str(features.position_secondary_context_label or "") == "LOWER_CONTEXT"
                            else 0.6 if str(features.position_secondary_context_label or "") == "NEUTRAL_CONTEXT" else 0.35
                        )
                    )
                ),
                "dominant_readiness": dominant_readiness,
                "opposing_readiness": opposing_readiness,
                "spread_strength": spread_strength,
                "dominant_persistence": dominant_persistence,
                "buy_reversal_fit": buy_reversal_fit,
                "sell_reversal_fit": sell_reversal_fit,
                "buy_reversal_core": buy_reversal_core,
                "sell_reversal_core": sell_reversal_core,
                "buy_reversal_score": buy_reversal_score,
                "sell_reversal_score": sell_reversal_score,
                "reversal_support": reversal_support,
                "reversal_competition_pressure": reversal_competition_pressure,
                "buy_continuation_fit": buy_continuation_fit,
                "sell_continuation_fit": sell_continuation_fit,
                "buy_continuation_core": buy_continuation_core,
                "sell_continuation_core": sell_continuation_core,
                "buy_continuation_score": buy_continuation_score,
                "sell_continuation_score": sell_continuation_score,
                "continuation_support": continuation_support,
                "continuation_competition_pressure": continuation_competition_pressure,
                "middle_chop_barrier": barrier.middle_chop_barrier,
                "conflict_barrier": barrier.conflict_barrier,
                "structural_friction": structural_friction,
                "false_break_pressure": false_break_pressure,
                "bf1_act_vs_wait_bias": bf1_act_vs_wait_bias,
                "bf1_false_break_risk": bf1_false_break_risk,
                "bf1_awareness_keep_allowed": bf1_awareness_keep_allowed,
                "bf5_advanced_reliability": bf5_advanced_reliability,
                "bf5_order_book_reliable": bf5_order_book_reliable,
                "bf5_event_context_reliable": bf5_event_context_reliable,
                "bf5_transition_reliability": bf5_transition_reliability,
            },
            "dominant_side": dominant_side,
            "dominant_mode": dominant_mode,
            "side_separation": side_separation,
            "confirm_fake_gap": confirm_fake_gap,
            "reversal_continuation_gap": reversal_continuation_gap,
            "competition_mode": "confirm_vs_false_break",
            "mode_competition_mode": "reversal_vs_continuation",
            "compression_mode": "core_multiplicative_support_additive",
            "gap_reasons": {
                "side_separation": (
                    f"side_separation={side_separation:.4f}; "
                    f"buy_confirm={p_buy_confirm:.4f}, sell_confirm={p_sell_confirm:.4f}"
                ),
                "confirm_fake_gap": (
                    f"confirm_fake_gap={confirm_fake_gap:.4f}; "
                    f"dominant_confirm={dominant_confirm:.4f}, false_break={p_false_break:.4f}"
                ),
                "reversal_continuation_gap": (
                    f"reversal_continuation_gap={reversal_continuation_gap:.4f}; "
                    f"reversal_success={p_reversal_success:.4f}, continuation_success={p_continuation_success:.4f}"
                ),
            },
            "forecast_reasons": {
                "p_buy_confirm": (
                    f"buy_total_evidence={evidence.buy_total_evidence:.4f} + "
                    f"buy_belief={belief.buy_belief:.4f} + buy_persistence={belief.buy_persistence:.4f} "
                    f"-> buy_readiness={buy_readiness:.4f}, buy_confirm_core={buy_confirm_core:.4f}, "
                    f"buy_confirm_support={buy_confirm_support:.4f}, buy_confirm_readiness={buy_confirm_readiness:.4f}, "
                      f"buy_confirm_momentum={buy_confirm_momentum:.4f}, "
                      f"buy_path_mode={buy_path_mode}, buy_confirm_path_gate={buy_confirm_path_gate:.4f}, "
                      f"buy_confirm_path_support={buy_confirm_path_support:.4f}, "
                      f"buy_edge_turn_support={buy_edge_turn_support:.4f}, "
                      f"buy_breakout_scene_support={buy_breakout_scene_support:.4f}, "
                      f"p_failed_breakdown_reclaim={p_failed_breakdown_reclaim:.4f}, "
                      f"buy_barrier={barrier.buy_barrier:.4f}, false_break_pressure={false_break_pressure:.4f}"
                  ),
                  "p_sell_confirm": (
                    f"sell_total_evidence={evidence.sell_total_evidence:.4f} + "
                    f"sell_belief={belief.sell_belief:.4f} + sell_persistence={belief.sell_persistence:.4f} "
                    f"-> sell_readiness={sell_readiness:.4f}, sell_confirm_core={sell_confirm_core:.4f}, "
                    f"sell_confirm_support={sell_confirm_support:.4f}, sell_confirm_readiness={sell_confirm_readiness:.4f}, "
                      f"sell_confirm_momentum={sell_confirm_momentum:.4f}, "
                      f"sell_path_mode={sell_path_mode}, sell_confirm_path_gate={sell_confirm_path_gate:.4f}, "
                      f"sell_confirm_path_support={sell_confirm_path_support:.4f}, "
                      f"sell_edge_turn_support={sell_edge_turn_support:.4f}, "
                      f"sell_breakout_scene_support={sell_breakout_scene_support:.4f}, "
                      f"p_failed_breakout_flush={p_failed_breakout_flush:.4f}, "
                      f"sell_barrier={barrier.sell_barrier:.4f}, false_break_pressure={false_break_pressure:.4f}"
                  ),
                  "p_false_break": (
                    f"dominant_readiness={dominant_readiness:.4f}, dominant_confirm={dominant_confirm:.4f}, "
                    f"dominant_belief={dominant_belief:.4f}, dominant_persistence={dominant_persistence:.4f}, "
                    f"spread_strength={spread_strength:.4f}, "
                      f"middle_chop_barrier={barrier.middle_chop_barrier:.4f}, "
                      f"conflict_barrier={barrier.conflict_barrier:.4f}, structural_friction={structural_friction:.4f}, "
                      f"dominant_reversal_support={dominant_reversal_support:.4f}, "
                      f"p_continuation_exhaustion={p_continuation_exhaustion:.4f}, "
                      f"bf1_act_vs_wait_bias={bf1_act_vs_wait_bias:.4f}, "
                      f"bf1_false_break_risk={bf1_false_break_risk:.4f}, "
                      f"bf1_awareness_keep_allowed={int(bf1_awareness_keep_allowed)}, "
                      f"bf5_advanced_reliability={bf5_advanced_reliability:.4f}, "
                      f"bf5_order_book_reliable={int(bf5_order_book_reliable)}, "
                      f"bf5_event_context_reliable={int(bf5_event_context_reliable)}, "
                      f"bf5_transition_reliability={bf5_transition_reliability:.4f}, "
                      f"false_break_pressure={false_break_pressure:.4f}"
                  ),
                  "p_reversal_success": (
                      f"buy_reversal_core={buy_reversal_core:.4f} + buy_reversal_fit={buy_reversal_fit:.4f}, "
                      f"sell_reversal_core={sell_reversal_core:.4f} + sell_reversal_fit={sell_reversal_fit:.4f}, "
                      f"reversal_support={reversal_support:.4f}, reversal_competition_pressure={reversal_competition_pressure:.4f}, "
                      f"p_edge_turn_success={p_edge_turn_success:.4f}, "
                      f"failed_break_scene={max(p_failed_breakdown_reclaim, p_failed_breakout_flush):.4f} -> "
                      f"max(buy={buy_reversal_score:.4f}, sell={sell_reversal_score:.4f})"
                  ),
                  "p_continuation_success": (
                      f"buy_continuation_core={buy_continuation_core:.4f} + buy_continuation_fit={buy_continuation_fit:.4f}, "
                      f"sell_continuation_core={sell_continuation_core:.4f} + sell_continuation_fit={sell_continuation_fit:.4f}, "
                      f"continuation_support={continuation_support:.4f}, continuation_competition_pressure={continuation_competition_pressure:.4f}, "
                      f"scene_continuation={max(buy_breakout_scene_support, sell_breakout_scene_support):.4f}, "
                      f"continuation_exhaustion={p_continuation_exhaustion:.4f} -> "
                      f"max(buy={buy_continuation_score:.4f}, sell={sell_continuation_score:.4f})"
                  ),
              },
        },
    )


def _build_trade_management_forecast_rule_impl(features: ForecastFeaturesV1) -> TradeManagementForecast:
    evidence = features.evidence_vector_v1
    belief = features.belief_state_v1
    barrier = features.barrier_state_v1

    buy_side_strength = _side_readiness(
        evidence.buy_total_evidence,
        belief.buy_belief,
        belief.buy_persistence,
    )
    sell_side_strength = _side_readiness(
        evidence.sell_total_evidence,
        belief.sell_belief,
        belief.sell_persistence,
    )
    dominant_strength = max(buy_side_strength, sell_side_strength)
    opposing_strength = min(buy_side_strength, sell_side_strength)
    active_barrier = min(barrier.buy_barrier, barrier.sell_barrier)
    opposing_barrier = max(barrier.buy_barrier, barrier.sell_barrier)
    spread_strength = abs(float(belief.belief_spread or 0.0))
    dominant_persistence = max(belief.buy_persistence, belief.sell_persistence)
    dominant_path_evidence = max(
        evidence.buy_continuation_evidence,
        evidence.sell_continuation_evidence,
        evidence.buy_reversal_evidence,
        evidence.sell_reversal_evidence,
    )
    edge_travel_basis = max(features.position_conflict_score, 1.0 - features.middle_neutrality)
    dominance_strength_gap = max(dominant_strength - opposing_strength, 0.0)

    hold_core = _base_readiness(dominant_strength, dominant_persistence)
    hold_support = (0.12 * spread_strength) + (0.10 * (1.0 - active_barrier))
    hold_readiness = _clamp01(hold_core + hold_support)
    continue_momentum = _clamp01(
        (0.20 * dominance_strength_gap)
        + (0.12 * dominant_persistence)
        + (0.08 * spread_strength)
    )
    fail_pressure = _clamp01(
        (
            opposing_strength
            * (0.55 + (0.45 * max(barrier.conflict_barrier, barrier.middle_chop_barrier)))
        )
        + (0.25 * active_barrier)
        + (0.15 * (1.0 - dominant_persistence))
    )
    p_continue_favor = _clamp01(
        (hold_readiness + continue_momentum)
        * (1.0 - (0.55 * fail_pressure))
    )
    p_fail_now = _clamp01(
        (fail_pressure + (0.12 * opposing_strength))
        * (1.0 - (0.45 * hold_readiness))
    )
    recovery_support = _clamp01(
        (0.55 * dominant_strength)
        + (0.25 * dominant_persistence)
        + (0.20 * (1.0 - max(barrier.middle_chop_barrier, barrier.conflict_barrier)))
    )
    reentry_support = _clamp01(
        (0.50 * p_fail_now)
        + (0.25 * dominant_strength)
        + (0.15 * (1.0 - max(barrier.middle_chop_barrier, barrier.conflict_barrier)))
        + (0.10 * dominance_strength_gap)
    )
    p_recover_after_pullback = _clamp01(recovery_support * (1.0 - (0.40 * p_fail_now)))
    p_reach_tp1 = _clamp01(
        (0.55 * p_continue_favor)
        + (0.25 * dominant_path_evidence)
        + (0.20 * (1.0 - active_barrier))
    )
    p_opposite_edge_reach = _clamp01(
        (0.65 * p_continue_favor)
        + (0.20 * edge_travel_basis)
        + (0.15 * (1.0 - barrier.middle_chop_barrier))
    )
    p_better_reentry_if_cut = _clamp01(reentry_support * (1.0 - (0.35 * p_recover_after_pullback)))
    management_scene_support = _scene_management_support(features)
    p_hold_through_noise = _clamp01(float(management_scene_support.get("p_hold_through_noise", 0.0) or 0.0))
    p_premature_exit_risk = _clamp01(float(management_scene_support.get("p_premature_exit_risk", 0.0) or 0.0))
    p_edge_to_edge_completion = _clamp01(
        float(management_scene_support.get("p_edge_to_edge_completion", 0.0) or 0.0)
    )
    p_flip_after_exit_quality = _clamp01(
        float(management_scene_support.get("p_flip_after_exit_quality", 0.0) or 0.0)
    )
    p_stop_then_recover_risk = _clamp01(
        float(management_scene_support.get("p_stop_then_recover_risk", 0.0) or 0.0)
    )
    hold_reward_bridge = _bridge_first_management_hold_reward_hint_v1(features)
    bf2_hold_reward_hint = _clamp01(float(hold_reward_bridge.get("hold_reward_hint", 0.0) or 0.0))
    bf2_edge_to_edge_tailwind = _clamp01(
        float(hold_reward_bridge.get("edge_to_edge_tailwind", 0.0) or 0.0)
    )
    bf2_hold_patience_allowed = bool(hold_reward_bridge.get("hold_patience_allowed", False))
    bf2_hold_reward_effective = _clamp01(
        bf2_hold_reward_hint * (1.0 if bf2_hold_patience_allowed else 0.55)
    )
    bf2_edge_to_edge_effective = _clamp01(
        bf2_edge_to_edge_tailwind * (1.0 if bf2_hold_patience_allowed else 0.65)
    )
    fast_cut_bridge = _bridge_first_management_fast_cut_risk_v1(features)
    bf3_fast_cut_risk = _clamp01(float(fast_cut_bridge.get("fast_cut_risk", 0.0) or 0.0))
    bf3_collision_risk = _clamp01(float(fast_cut_bridge.get("collision_risk", 0.0) or 0.0))
    bf3_event_caution = _clamp01(float(fast_cut_bridge.get("event_caution", 0.0) or 0.0))
    bf3_cut_now_allowed = bool(fast_cut_bridge.get("cut_now_allowed", False))
    bf3_fast_cut_effective = _clamp01(
        bf3_fast_cut_risk * (1.0 if bf3_cut_now_allowed else 0.70)
    )
    bf3_collision_effective = _clamp01(
        bf3_collision_risk * (1.0 if bf3_cut_now_allowed else 0.75)
    )
    bf3_event_effective = _clamp01(
        bf3_event_caution * (1.0 if bf3_cut_now_allowed else 0.65)
    )
    trend_maturity_bridge = _bridge_first_trend_continuation_maturity_v1(features)
    bf4_continuation_maturity = _clamp01(
        float(trend_maturity_bridge.get("continuation_maturity", 0.0) or 0.0)
    )
    bf4_exhaustion_pressure = _clamp01(
        float(trend_maturity_bridge.get("exhaustion_pressure", 0.0) or 0.0)
    )
    bf4_trend_hold_confidence = _clamp01(
        float(trend_maturity_bridge.get("trend_hold_confidence", 0.0) or 0.0)
    )
    bf4_trend_effective = _clamp01(
        bf4_trend_hold_confidence * (0.70 + (0.30 * (1.0 - bf4_exhaustion_pressure)))
    )
    bf4_reach_effective = _clamp01(
        max(bf4_continuation_maturity, bf4_trend_effective)
        * (1.0 - (0.25 * bf4_exhaustion_pressure))
    )
    advanced_reliability_bridge = _bridge_first_advanced_input_reliability_v1(features)
    bf5_advanced_reliability = _clamp01(
        float(advanced_reliability_bridge.get("advanced_reliability", 0.0) or 0.0)
    )
    bf5_order_book_reliable = bool(advanced_reliability_bridge.get("order_book_reliable", False))
    bf5_event_context_reliable = bool(
        advanced_reliability_bridge.get("event_context_reliable", False)
    )
    bf5_reliability_floor = _clamp01(0.55 + (0.45 * bf5_advanced_reliability))
    bf5_event_scale = _clamp01(0.65 + (0.35 * float(bf5_event_context_reliable)))
    bf5_order_scale = _clamp01(0.60 + (0.40 * float(bf5_order_book_reliable)))
    bf3_fast_cut_effective = _clamp01(bf3_fast_cut_effective * bf5_reliability_floor)
    bf3_collision_effective = _clamp01(bf3_collision_effective * bf5_order_scale)
    bf3_event_effective = _clamp01(bf3_event_effective * bf5_event_scale)
    bf4_trend_effective = _clamp01(bf4_trend_effective * bf5_reliability_floor)
    bf4_reach_effective = _clamp01(
        bf4_reach_effective * (0.70 + (0.30 * bf5_reliability_floor))
    )
    p_continue_favor = _clamp01(
        p_continue_favor
        + (0.12 * p_hold_through_noise)
        + (0.10 * p_edge_to_edge_completion)
        - (0.08 * p_flip_after_exit_quality)
    )
    p_fail_now = _clamp01(
        p_fail_now
        + (0.10 * p_flip_after_exit_quality)
        + (0.08 * p_stop_then_recover_risk)
        - (0.12 * p_hold_through_noise)
    )
    p_recover_after_pullback = _clamp01(
        p_recover_after_pullback
        + (0.12 * p_hold_through_noise)
        - (0.08 * p_flip_after_exit_quality)
    )
    p_reach_tp1 = _clamp01(
        p_reach_tp1
        + (0.08 * p_hold_through_noise)
        + (0.08 * p_edge_to_edge_completion)
    )
    p_opposite_edge_reach = _clamp01(
        p_opposite_edge_reach
        + (0.16 * p_edge_to_edge_completion)
        - (0.08 * p_premature_exit_risk)
    )
    p_better_reentry_if_cut = _clamp01(
        p_better_reentry_if_cut
        + (0.16 * p_flip_after_exit_quality)
        - (0.10 * p_stop_then_recover_risk)
    )
    p_continue_favor = _clamp01((0.90 * p_continue_favor) + (0.10 * bf2_hold_reward_effective))
    p_fail_now = _clamp01((0.94 * p_fail_now) - (0.06 * bf2_hold_reward_effective))
    p_recover_after_pullback = _clamp01(
        (0.92 * p_recover_after_pullback)
        + (0.08 * max(bf2_hold_reward_effective, bf2_edge_to_edge_effective))
    )
    p_reach_tp1 = _clamp01((0.94 * p_reach_tp1) + (0.06 * bf2_hold_reward_effective))
    p_opposite_edge_reach = _clamp01((0.88 * p_opposite_edge_reach) + (0.12 * bf2_edge_to_edge_effective))
    p_continue_favor = _clamp01((0.92 * p_continue_favor) - (0.08 * bf3_fast_cut_effective))
    p_fail_now = _clamp01(
        (0.88 * p_fail_now)
        + (0.08 * bf3_fast_cut_effective)
        + (0.04 * max(bf3_collision_effective, bf3_event_effective))
    )
    p_recover_after_pullback = _clamp01(
        (0.94 * p_recover_after_pullback)
        - (0.06 * max(bf3_fast_cut_effective, bf3_collision_effective))
    )
    p_reach_tp1 = _clamp01((0.95 * p_reach_tp1) - (0.05 * bf3_fast_cut_effective))
    p_opposite_edge_reach = _clamp01((0.92 * p_opposite_edge_reach) - (0.08 * bf3_collision_effective))
    p_better_reentry_if_cut = _clamp01(
        (0.88 * p_better_reentry_if_cut)
        + (
            0.12
            * max(
                bf3_fast_cut_effective,
                bf3_collision_effective,
                bf3_event_effective,
            )
        )
    )
    p_continue_favor = _clamp01((0.90 * p_continue_favor) + (0.10 * bf4_trend_effective))
    p_fail_now = _clamp01((0.95 * p_fail_now) - (0.05 * bf4_trend_effective))
    p_recover_after_pullback = _clamp01(
        (0.94 * p_recover_after_pullback)
        + (0.06 * max(bf4_trend_effective, bf4_reach_effective))
    )
    p_reach_tp1 = _clamp01((0.90 * p_reach_tp1) + (0.10 * bf4_reach_effective))
    p_opposite_edge_reach = _clamp01((0.86 * p_opposite_edge_reach) + (0.14 * bf4_reach_effective))
    continue_fail_gap = p_continue_favor - p_fail_now
    recover_reentry_gap = p_recover_after_pullback - p_better_reentry_if_cut

    if buy_side_strength > sell_side_strength:
        dominant_side = "BUY"
    elif sell_side_strength > buy_side_strength:
        dominant_side = "SELL"
    else:
        dominant_side = "BALANCED"

    buy_mode = "reversal" if evidence.buy_reversal_evidence >= evidence.buy_continuation_evidence else "continuation"
    sell_mode = "reversal" if evidence.sell_reversal_evidence >= evidence.sell_continuation_evidence else "continuation"
    if dominant_side == "BUY":
        dominant_mode = buy_mode
    elif dominant_side == "SELL":
        dominant_mode = sell_mode
    else:
        dominant_mode = "balanced"

    return TradeManagementForecast(
        p_continue_favor=p_continue_favor,
        p_fail_now=p_fail_now,
        p_recover_after_pullback=p_recover_after_pullback,
        p_reach_tp1=p_reach_tp1,
        p_opposite_edge_reach=p_opposite_edge_reach,
        p_better_reentry_if_cut=p_better_reentry_if_cut,
        metadata={
            **_forecast_freeze_metadata("trade_management_branch"),
            **_forecast_pre_ml_metadata(
                "trade_management_branch",
                {
                    "p_continue_favor": float(p_continue_favor),
                    "p_fail_now": float(p_fail_now),
                    "p_reach_tp1": float(p_reach_tp1),
                    "p_better_reentry_if_cut": float(p_better_reentry_if_cut),
                    "p_recover_after_pullback": float(p_recover_after_pullback),
                    "p_premature_exit_risk": float(p_premature_exit_risk),
                },
            ),
            "semantic_forecast_inputs_v2_usage_v1": _semantic_forecast_inputs_usage(
                "trade_management_branch",
                used_fields={
                    "state_harvest": [
                        "execution_friction_state",
                    ],
                    "belief_harvest": [
                        "dominant_side",
                        "dominant_mode",
                        "buy_streak",
                        "sell_streak",
                        "flip_readiness",
                        "belief_instability",
                    ],
                    "barrier_harvest": [
                        "middle_chop_barrier_v2",
                        "duplicate_edge_barrier_v1",
                        "post_event_cooldown_barrier_v1",
                    ],
                    "secondary_harvest": [
                        "advanced_input_activation_state",
                        "tick_flow_state",
                        "order_book_state",
                    ],
                },
            ),
            "forecast_contract": "trade_management_forecast_v1",
            "mapper_version": "trade_management_forecast_v1_fc9",
            "score_formula_version": "management_fc9_scene_hold_cut_trend_reliability_bridge_v1",
            "features_contract": str(
                ((features.metadata or {}).get("forecast_features_contract", {}) or {}).get("contract_version", "")
                or "forecast_features_v1"
            ),
            "bridge_first_v1": {
                "management_hold_reward_hint_v1": hold_reward_bridge,
                "management_fast_cut_risk_v1": fast_cut_bridge,
                "trend_continuation_maturity_v1": trend_maturity_bridge,
                "advanced_input_reliability_v1": advanced_reliability_bridge,
            },
            "management_scene_support_v1": management_scene_support,
            "component_scores": {
                "buy_total_evidence": evidence.buy_total_evidence,
                "sell_total_evidence": evidence.sell_total_evidence,
                "buy_belief": belief.buy_belief,
                "sell_belief": belief.sell_belief,
                "buy_persistence": belief.buy_persistence,
                "sell_persistence": belief.sell_persistence,
                "belief_spread": belief.belief_spread,
                "buy_barrier": barrier.buy_barrier,
                "sell_barrier": barrier.sell_barrier,
                "middle_chop_barrier": barrier.middle_chop_barrier,
                "conflict_barrier": barrier.conflict_barrier,
                "buy_side_strength": buy_side_strength,
                "sell_side_strength": sell_side_strength,
                "dominant_strength": dominant_strength,
                "opposing_strength": opposing_strength,
                "dominance_strength_gap": dominance_strength_gap,
                "hold_core": hold_core,
                "hold_support": hold_support,
                "hold_readiness": hold_readiness,
                "continue_momentum": continue_momentum,
                "fail_pressure": fail_pressure,
                "dominant_persistence": dominant_persistence,
                "dominant_path_evidence": dominant_path_evidence,
                "edge_travel_basis": edge_travel_basis,
                "active_barrier": active_barrier,
                "opposing_barrier": opposing_barrier,
                "spread_strength": spread_strength,
                  "recovery_support": recovery_support,
                  "reentry_support": reentry_support,
                  "p_hold_through_noise": p_hold_through_noise,
                  "p_premature_exit_risk": p_premature_exit_risk,
                  "p_edge_to_edge_completion": p_edge_to_edge_completion,
                  "p_flip_after_exit_quality": p_flip_after_exit_quality,
                  "p_stop_then_recover_risk": p_stop_then_recover_risk,
                  "bf2_hold_reward_hint": bf2_hold_reward_hint,
                  "bf2_edge_to_edge_tailwind": bf2_edge_to_edge_tailwind,
                  "bf2_hold_patience_allowed": bf2_hold_patience_allowed,
                  "bf3_fast_cut_risk": bf3_fast_cut_risk,
                  "bf3_collision_risk": bf3_collision_risk,
                  "bf3_event_caution": bf3_event_caution,
                  "bf3_cut_now_allowed": bf3_cut_now_allowed,
                  "bf4_continuation_maturity": bf4_continuation_maturity,
                  "bf4_exhaustion_pressure": bf4_exhaustion_pressure,
                  "bf4_trend_hold_confidence": bf4_trend_hold_confidence,
                  "bf5_advanced_reliability": bf5_advanced_reliability,
                  "bf5_order_book_reliable": bf5_order_book_reliable,
                  "bf5_event_context_reliable": bf5_event_context_reliable,
                  "bf5_reliability_floor": bf5_reliability_floor,
                  "bf5_event_scale": bf5_event_scale,
                  "bf5_order_scale": bf5_order_scale,
              },
            "dominant_side": dominant_side,
            "dominant_mode": dominant_mode,
            "continue_fail_gap": continue_fail_gap,
            "recover_reentry_gap": recover_reentry_gap,
            "competition_mode": "continue_vs_fail",
            "recovery_competition_mode": "recover_vs_reentry",
            "compression_mode": "core_multiplicative_support_additive",
            "gap_reasons": {
                "continue_fail_gap": (
                    f"continue_fail_gap={continue_fail_gap:.4f}; "
                    f"continue_favor={p_continue_favor:.4f}, fail_now={p_fail_now:.4f}"
                ),
                "recover_reentry_gap": (
                    f"recover_reentry_gap={recover_reentry_gap:.4f}; "
                    f"recover_after_pullback={p_recover_after_pullback:.4f}, "
                    f"better_reentry_if_cut={p_better_reentry_if_cut:.4f}"
                ),
            },
            "forecast_reasons": {
                  "p_continue_favor": (
                      f"dominant_strength={dominant_strength:.4f}, hold_core={hold_core:.4f}, "
                      f"hold_support={hold_support:.4f}, hold_readiness={hold_readiness:.4f}, "
                      f"continue_momentum={continue_momentum:.4f}, "
                      f"belief_spread={belief.belief_spread:.4f}, active_barrier={active_barrier:.4f}, "
                      f"spread_strength={spread_strength:.4f}, fail_pressure={fail_pressure:.4f}, "
                      f"p_hold_through_noise={p_hold_through_noise:.4f}, "
                      f"p_edge_to_edge_completion={p_edge_to_edge_completion:.4f}, "
                      f"bf2_hold_reward_hint={bf2_hold_reward_hint:.4f}, "
                      f"bf2_edge_to_edge_tailwind={bf2_edge_to_edge_tailwind:.4f}, "
                      f"bf2_hold_patience_allowed={int(bf2_hold_patience_allowed)}, "
                      f"bf3_fast_cut_risk={bf3_fast_cut_risk:.4f}, "
                      f"bf3_cut_now_allowed={int(bf3_cut_now_allowed)}, "
                      f"bf4_continuation_maturity={bf4_continuation_maturity:.4f}, "
                      f"bf4_trend_hold_confidence={bf4_trend_hold_confidence:.4f}, "
                      f"bf5_advanced_reliability={bf5_advanced_reliability:.4f}, "
                      f"bf5_reliability_floor={bf5_reliability_floor:.4f}"
                  ),
                  "p_fail_now": (
                      f"opposing_strength={opposing_strength:.4f}, fail_pressure={fail_pressure:.4f}, "
                      f"hold_readiness={hold_readiness:.4f}, conflict_barrier={barrier.conflict_barrier:.4f}, "
                      f"middle_chop_barrier={barrier.middle_chop_barrier:.4f}, active_barrier={active_barrier:.4f}, "
                      f"p_flip_after_exit_quality={p_flip_after_exit_quality:.4f}, "
                      f"p_stop_then_recover_risk={p_stop_then_recover_risk:.4f}, "
                      f"bf3_fast_cut_risk={bf3_fast_cut_risk:.4f}, "
                      f"bf3_collision_risk={bf3_collision_risk:.4f}, "
                      f"bf3_event_caution={bf3_event_caution:.4f}, "
                      f"bf3_cut_now_allowed={int(bf3_cut_now_allowed)}, "
                      f"bf4_trend_hold_confidence={bf4_trend_hold_confidence:.4f}, "
                      f"bf5_order_book_reliable={int(bf5_order_book_reliable)}, "
                      f"bf5_event_context_reliable={int(bf5_event_context_reliable)}"
                  ),
                  "p_recover_after_pullback": (
                      f"recovery_support={recovery_support:.4f}, dominant_strength={dominant_strength:.4f}, "
                      f"dominant_persistence={dominant_persistence:.4f}, middle_chop_barrier={barrier.middle_chop_barrier:.4f}, "
                      f"conflict_barrier={barrier.conflict_barrier:.4f}, fail_now={p_fail_now:.4f}, "
                      f"p_hold_through_noise={p_hold_through_noise:.4f}, "
                      f"bf2_hold_reward_hint={bf2_hold_reward_hint:.4f}, "
                      f"bf3_fast_cut_risk={bf3_fast_cut_risk:.4f}, "
                      f"bf4_trend_hold_confidence={bf4_trend_hold_confidence:.4f}, "
                      f"bf5_reliability_floor={bf5_reliability_floor:.4f}"
                  ),
                  "p_reach_tp1": (
                      f"continue_favor={p_continue_favor:.4f}, dominant_path_evidence={dominant_path_evidence:.4f}, "
                      f"active_barrier={active_barrier:.4f}, "
                      f"p_edge_to_edge_completion={p_edge_to_edge_completion:.4f}, "
                      f"bf2_hold_reward_hint={bf2_hold_reward_hint:.4f}, "
                      f"bf3_fast_cut_risk={bf3_fast_cut_risk:.4f}, "
                      f"bf4_continuation_maturity={bf4_continuation_maturity:.4f}, "
                      f"bf4_exhaustion_pressure={bf4_exhaustion_pressure:.4f}, "
                      f"bf5_advanced_reliability={bf5_advanced_reliability:.4f}"
                  ),
                  "p_opposite_edge_reach": (
                      f"continue_favor={p_continue_favor:.4f} with middle_neutrality={features.middle_neutrality:.4f}, "
                      f"edge_travel_basis={edge_travel_basis:.4f}, middle_chop_barrier={barrier.middle_chop_barrier:.4f}, "
                      f"p_edge_to_edge_completion={p_edge_to_edge_completion:.4f}, "
                      f"bf2_edge_to_edge_tailwind={bf2_edge_to_edge_tailwind:.4f}, "
                      f"bf3_collision_risk={bf3_collision_risk:.4f}, "
                      f"bf4_continuation_maturity={bf4_continuation_maturity:.4f}, "
                      f"bf4_trend_hold_confidence={bf4_trend_hold_confidence:.4f}, "
                      f"bf5_order_book_reliable={int(bf5_order_book_reliable)}"
                  ),
                  "p_better_reentry_if_cut": (
                      f"reentry_support={reentry_support:.4f}, fail_now={p_fail_now:.4f}, "
                      f"dominant_strength={dominant_strength:.4f}, dominant_persistence={dominant_persistence:.4f}, "
                      f"recover_after_pullback={p_recover_after_pullback:.4f}, "
                      f"friction={max(barrier.middle_chop_barrier, barrier.conflict_barrier):.4f}, "
                      f"p_flip_after_exit_quality={p_flip_after_exit_quality:.4f}, "
                      f"p_stop_then_recover_risk={p_stop_then_recover_risk:.4f}, "
                      f"bf3_fast_cut_risk={bf3_fast_cut_risk:.4f}, "
                      f"bf3_collision_risk={bf3_collision_risk:.4f}, "
                      f"bf3_event_caution={bf3_event_caution:.4f}, "
                      f"bf3_cut_now_allowed={int(bf3_cut_now_allowed)}, "
                      f"bf5_event_context_reliable={int(bf5_event_context_reliable)}"
                  ),
              },
          },
      )


class ForecastRuleV1:
    engine_kind = "rule"
    engine_name = "ForecastRuleV1"
    engine_interface_version = "forecast_engine_interface_v1"

    def build_transition_forecast(self, features: ForecastFeaturesV1) -> TransitionForecast:
        forecast = _build_transition_forecast_rule_impl(features)
        forecast.metadata["engine_kind"] = self.engine_kind
        forecast.metadata["engine_name"] = self.engine_name
        forecast.metadata["engine_interface_version"] = self.engine_interface_version
        forecast.metadata["baseline_contract"] = dict(FORECAST_RULE_BASELINE_V1)
        return forecast

    def build_trade_management_forecast(self, features: ForecastFeaturesV1) -> TradeManagementForecast:
        forecast = _build_trade_management_forecast_rule_impl(features)
        forecast.metadata["engine_kind"] = self.engine_kind
        forecast.metadata["engine_name"] = self.engine_name
        forecast.metadata["engine_interface_version"] = self.engine_interface_version
        forecast.metadata["baseline_contract"] = dict(FORECAST_RULE_BASELINE_V1)
        return forecast


_DEFAULT_FORECAST_ENGINE: ForecastEngineInterface = ForecastRuleV1()


def get_default_forecast_engine() -> ForecastEngineInterface:
    return _DEFAULT_FORECAST_ENGINE


def build_transition_forecast(
    features: ForecastFeaturesV1,
    engine: ForecastEngineInterface | None = None,
) -> TransitionForecast:
    return (engine or _DEFAULT_FORECAST_ENGINE).build_transition_forecast(features)


def build_trade_management_forecast(
    features: ForecastFeaturesV1,
    engine: ForecastEngineInterface | None = None,
) -> TradeManagementForecast:
    return (engine or _DEFAULT_FORECAST_ENGINE).build_trade_management_forecast(features)
