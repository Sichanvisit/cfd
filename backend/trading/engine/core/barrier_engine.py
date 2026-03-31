from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from backend.core.config import Config

from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    PositionSnapshot,
    StateVectorV2,
)

_BARRIER_FREEZE_PHASE = "BR0"
_BARRIER_PRE_ML_PHASE = "BR6"
_BARRIER_SEMANTIC_OWNER_CONTRACT = "barrier_blocking_only_v1"
_BARRIER_ROLE_STATEMENT = (
    "Barrier is not the layer that finds entries. "
    "Barrier decides whether the current candidate should be blocked now."
)
_BARRIER_PRE_ML_REQUIRED_FEATURE_FIELDS = (
    "buy_barrier",
    "sell_barrier",
    "conflict_barrier",
    "middle_chop_barrier",
    "direction_policy_barrier",
    "liquidity_barrier",
)
_BARRIER_PRE_ML_RECOMMENDED_FEATURE_FIELDS = (
    "edge_turn_relief_score",
    "breakout_fade_barrier_score",
    "execution_friction_barrier_score",
    "event_risk_barrier_score",
)
_BARRIER_OWNER_BOUNDARIES = {
    "position_owner_claim_allowed": False,
    "response_owner_claim_allowed": False,
    "state_owner_claim_allowed": False,
    "evidence_owner_claim_allowed": False,
    "belief_owner_claim_allowed": False,
    "direct_side_creator_allowed": False,
    "direct_action_creator_allowed": False,
    "semantic_direction_creation_allowed": False,
    "semantic_confirmation_creation_allowed": False,
    "role": "blocking_and_relief_only",
}
_BUY_ONLY_POLICY_BLOCK = 0.40
_SELL_ONLY_POLICY_BLOCK = 0.40
_NONE_POLICY_BLOCK = 0.65
_COMMON_CONFLICT_WEIGHT = 0.38
_COMMON_CHOP_WEIGHT = 0.34
_COMMON_LIQUIDITY_WEIGHT = 0.28
_SIDE_POLICY_WEIGHT = 0.32
_SIDE_READINESS_RELIEF_WEIGHT = 0.22
_MIDDLE_BIAS_LABELS = {"MIDDLE_UPPER_BIAS", "MIDDLE_LOWER_BIAS"}
_EDGE_TURN_CONFLUENCE_LABELS = {"WEAK_CONFLUENCE", "TOPDOWN_CONFLICT"}
_UP_EXPANSION_LABELS = {"UP_EARLY_EXPANSION", "UP_ACTIVE_EXPANSION", "UP_EXTENDED_EXPANSION"}
_DOWN_EXPANSION_LABELS = {"DOWN_EARLY_EXPANSION", "DOWN_ACTIVE_EXPANSION", "DOWN_EXTENDED_EXPANSION"}
_UP_SLOPE_LABELS = {"UP_SLOPE_ALIGNED"}
_DOWN_SLOPE_LABELS = {"DOWN_SLOPE_ALIGNED"}
_HIGH_FRICTION_LABELS = {"HIGH_FRICTION", "MEDIUM_FRICTION"}
_THIN_PARTICIPATION_LABELS = {"THIN_PARTICIPATION", "LOW_PARTICIPATION"}
_ADVANCED_ACTIVE_LABELS = {"ADVANCED_ACTIVE"}
_ADVANCED_PARTIAL_LABELS = {"ADVANCED_PARTIAL", "ADVANCED_PASSIVE"}
_ADVANCED_NEUTRAL_LABELS = {"ADVANCED_UNAVAILABLE", "ADVANCED_DISABLED", "ADVANCED_IDLE"}
_ADVANCED_SOURCE_NEUTRAL_LABELS = {"UNAVAILABLE", "DISABLED", "INACTIVE"}
_SESSION_OPEN_HOURS_KST = {
    "ASIA": 8,
    "EUROPE": 16,
    "USA": 0,
}
_KST = ZoneInfo("Asia/Seoul")
_VP_COL_CANDIDATES = {
    "poc": ("poc", "poc_price", "point_of_control", "point_of_control_price"),
    "vah": ("vah", "va_high", "value_area_high"),
    "val": ("val", "va_low", "value_area_low"),
}
_BARRIER_STATE_V2_PRIMARY_LABEL_FIELDS = (
    "session_regime_state",
    "session_expansion_state",
    "session_exhaustion_state",
    "topdown_spacing_state",
    "topdown_slope_state",
    "topdown_confluence_state",
    "spread_stress_state",
    "volume_participation_state",
    "execution_friction_state",
    "event_risk_state",
)
_BARRIER_STATE_V2_SECONDARY_LABEL_FIELDS = (
    "advanced_input_activation_state",
    "tick_flow_state",
    "order_book_state",
)
_BARRIER_STATE_V2_SECONDARY_SOURCE_FIELDS = (
    "source_current_rsi",
    "source_current_adx",
    "source_current_plus_di",
    "source_current_minus_di",
    "source_recent_range_mean",
    "source_recent_body_mean",
    "source_sr_level_rank",
    "source_sr_touch_count",
)
_VP_ROW_CACHE: dict[str, tuple[float, dict[str, float]]] = {}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _safe_float(value, default: float = 0.0) -> float:
    try:
        cast = float(pd.to_numeric(value, errors="coerce"))
    except Exception:
        return float(default)
    if pd.isna(cast):
        return float(default)
    return float(cast)


def _execution_friction_barrier_score(semantic_inputs_v2: dict[str, dict[str, float | str]]) -> float:
    primary_labels = semantic_inputs_v2.get("primary_state_labels") or {}
    friction_state = str(primary_labels.get("execution_friction_state") or "LOW_FRICTION")
    volume_state = str(primary_labels.get("volume_participation_state") or "NORMAL_PARTICIPATION")

    friction_base = {
        "LOW_FRICTION": 0.0,
        "MEDIUM_FRICTION": 0.18,
        "HIGH_FRICTION": 0.34,
    }.get(friction_state, 0.0)
    volume_boost = 0.05 if volume_state in _THIN_PARTICIPATION_LABELS else 0.0
    return _clamp01(friction_base + volume_boost)


def _event_risk_barrier_score(
    semantic_inputs_v2: dict[str, dict[str, float | str]],
    post_event_cooldown_barrier_v1: dict[str, float | str | bool],
) -> float:
    primary_labels = semantic_inputs_v2.get("primary_state_labels") or {}
    event_state = str(primary_labels.get("event_risk_state") or "LOW_EVENT_RISK")
    event_base = {
        "LOW_EVENT_RISK": 0.0,
        "WATCH_EVENT_RISK": 0.18,
        "HIGH_EVENT_RISK": 0.32,
    }.get(event_state, 0.0)
    cooldown_boost = 0.45 * float(post_event_cooldown_barrier_v1.get("common_boost") or 0.0)
    return _clamp01(event_base + cooldown_boost)


def _extract_position_structure_inputs(position_snapshot: PositionSnapshot) -> dict[str, float | str]:
    interpretation = position_snapshot.interpretation
    energy = position_snapshot.energy
    return {
        "primary_label": str(interpretation.primary_label or ""),
        "bias_label": str(interpretation.bias_label or ""),
        "secondary_context_label": str(interpretation.secondary_context_label or ""),
        "position_conflict_score": float(energy.position_conflict_score or 0.0),
        "middle_neutrality": _clamp01(float(energy.middle_neutrality or 0.0)),
    }


def _extract_semantic_barrier_inputs(
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
) -> dict[str, float | str]:
    state_meta = state_vector_v2.metadata or {}
    belief_meta = belief_state_v1.metadata or {}
    return {
        "direction_policy": str(state_meta.get("source_direction_policy") or "").upper() or "UNKNOWN",
        "liquidity_penalty": _clamp01(float(state_vector_v2.liquidity_penalty or 0.0)),
        "volatility_penalty": _clamp01(float(state_vector_v2.volatility_penalty or 0.0)),
        "buy_total_evidence": _clamp01(float(evidence_vector_v1.buy_total_evidence or 0.0)),
        "sell_total_evidence": _clamp01(float(evidence_vector_v1.sell_total_evidence or 0.0)),
        "buy_belief": _clamp01(float(belief_state_v1.buy_belief or 0.0)),
        "sell_belief": _clamp01(float(belief_state_v1.sell_belief or 0.0)),
        "buy_persistence": _clamp01(float(belief_state_v1.buy_persistence or 0.0)),
        "sell_persistence": _clamp01(float(belief_state_v1.sell_persistence or 0.0)),
        "belief_spread": float(belief_state_v1.belief_spread or 0.0),
        "dominance_deadband": float(belief_meta.get("dominance_deadband", 0.05) or 0.05),
        "global_dominant_side": str(belief_meta.get("global_dominant_side") or "BALANCED"),
        "global_dominant_mode": str(belief_meta.get("global_dominant_mode") or "balanced"),
    }


def _extract_semantic_barrier_inputs_v2(state_vector_v2: StateVectorV2) -> dict[str, dict[str, float | str]]:
    state_meta = state_vector_v2.metadata or {}
    primary_labels = {
        field: str(state_meta.get(field) or "UNKNOWN")
        for field in _BARRIER_STATE_V2_PRIMARY_LABEL_FIELDS
    }
    secondary_labels = {
        field: str(state_meta.get(field) or "INACTIVE")
        for field in _BARRIER_STATE_V2_SECONDARY_LABEL_FIELDS
    }
    secondary_sources = {
        field: float(state_meta.get(field) or 0.0)
        for field in _BARRIER_STATE_V2_SECONDARY_SOURCE_FIELDS
    }
    runtime_source_inputs = {
        "source_symbol": str(state_meta.get("source_symbol") or ""),
        "source_price": float(state_meta.get("source_price") or 0.0),
        "source_signal_timeframe": str(state_meta.get("source_signal_timeframe") or ""),
        "source_signal_bar_ts": int(state_meta.get("source_signal_bar_ts") or 0),
        "source_session_state_source": str(state_meta.get("source_session_state_source") or "UNKNOWN"),
        "source_position_in_session_box": str(state_meta.get("source_position_in_session_box") or "UNKNOWN"),
        "source_event_risk_score": float(state_meta.get("source_event_risk_score") or 0.0),
        "source_event_risk_match_count": int(
            ((state_meta.get("advanced_input_detail_v1") or {}) or {}).get("event_risk_match_count", 0) or 0
        ),
    }
    return {
        "primary_state_labels": primary_labels,
        "secondary_state_labels": secondary_labels,
        "secondary_source_inputs": secondary_sources,
        "runtime_source_inputs": runtime_source_inputs,
    }


def _conflict_barrier(position_inputs: dict[str, float | str]) -> tuple[float, str]:
    primary_label = str(position_inputs.get("primary_label") or "")
    conflict_score = float(position_inputs.get("position_conflict_score") or 0.0)

    if primary_label.startswith("CONFLICT_"):
        barrier = max(conflict_score, 0.45)
        reason = f"{primary_label} with position_conflict_score={conflict_score:.4f}"
    elif primary_label == "UNRESOLVED_POSITION":
        barrier = max(conflict_score, 0.22)
        reason = f"unresolved position with position_conflict_score={conflict_score:.4f}"
    else:
        barrier = conflict_score * 0.75
        reason = f"aligned/bias structure with scaled position_conflict_score={conflict_score:.4f}"
    return _clamp01(barrier), reason


def _middle_chop_barrier(
    position_inputs: dict[str, float | str],
    semantic_inputs: dict[str, float | str],
) -> tuple[float, dict[str, float | str]]:
    primary_label = str(position_inputs.get("primary_label") or "")
    bias_label = str(position_inputs.get("bias_label") or "")
    secondary_context_label = str(position_inputs.get("secondary_context_label") or "")
    middle_neutrality = float(position_inputs.get("middle_neutrality") or 0.0)
    belief_spread = float(semantic_inputs.get("belief_spread") or 0.0)
    dominant_deadband = float(semantic_inputs.get("dominance_deadband") or 0.05)
    max_persistence = _clamp01(
        max(
            float(semantic_inputs.get("buy_persistence") or 0.0),
            float(semantic_inputs.get("sell_persistence") or 0.0),
        )
    )
    buy_total = float(semantic_inputs.get("buy_total_evidence") or 0.0)
    sell_total = float(semantic_inputs.get("sell_total_evidence") or 0.0)
    evidence_max = max(buy_total, sell_total, 0.10)
    evidence_balance = _clamp01(1.0 - (abs(buy_total - sell_total) / evidence_max))
    spread_balance = _clamp01(1.0 - (abs(belief_spread) / max(dominant_deadband * 2.0, 1e-9)))

    if primary_label == "ALIGNED_MIDDLE":
        structure_base = 0.55
        structure_reason = "aligned middle"
    elif primary_label == "UNRESOLVED_POSITION":
        structure_base = 0.42
        structure_reason = "unresolved position"
    elif primary_label in _MIDDLE_BIAS_LABELS or bias_label in _MIDDLE_BIAS_LABELS:
        structure_base = 0.32
        structure_reason = "middle bias position"
    elif primary_label.startswith("CONFLICT_"):
        structure_base = 0.18
        structure_reason = "explicit conflict structure"
    else:
        structure_base = middle_neutrality * 0.08
        structure_reason = "non-middle structure"

    barrier = _clamp01(
        structure_base
        + (0.15 * middle_neutrality)
        + (0.12 * spread_balance)
        + (0.12 * (1.0 - max_persistence))
        + (0.10 * evidence_balance)
    )
    return barrier, {
        "structure_base": float(structure_base),
        "middle_neutrality": float(middle_neutrality),
        "spread_balance": float(spread_balance),
        "persistence_weakness": float(1.0 - max_persistence),
        "evidence_balance": float(evidence_balance),
        "primary_label": primary_label,
        "bias_label": bias_label,
        "secondary_context_label": secondary_context_label,
        "global_dominant_mode": str(semantic_inputs.get("global_dominant_mode") or "balanced"),
        "reason": structure_reason,
    }


def _edge_turn_relief(
    *,
    position_inputs: dict[str, float | str],
    semantic_inputs: dict[str, float | str],
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> tuple[float, dict[str, float | str]]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    session_regime_state = str(primary_state_labels.get("session_regime_state") or "UNKNOWN")
    topdown_confluence_state = str(primary_state_labels.get("topdown_confluence_state") or "UNKNOWN")
    secondary_context_label = str(position_inputs.get("secondary_context_label") or "")
    primary_label = str(position_inputs.get("primary_label") or "")
    buy_total = float(semantic_inputs.get("buy_total_evidence") or 0.0)
    sell_total = float(semantic_inputs.get("sell_total_evidence") or 0.0)
    buy_belief = float(semantic_inputs.get("buy_belief") or 0.0)
    sell_belief = float(semantic_inputs.get("sell_belief") or 0.0)
    buy_bias = max(buy_total + buy_belief - sell_total - sell_belief, 0.0)
    sell_bias = max(sell_total + sell_belief - buy_total - buy_belief, 0.0)

    buy_edge_ready = (
        secondary_context_label == "LOWER_CONTEXT"
        or primary_label.startswith("ALIGNED_LOWER")
        or primary_label == "LOWER_BIAS"
    )
    sell_edge_ready = (
        secondary_context_label == "UPPER_CONTEXT"
        or primary_label.startswith("ALIGNED_UPPER")
        or primary_label == "UPPER_BIAS"
    )
    session_ok = session_regime_state == "SESSION_EDGE_ROTATION"
    confluence_ok = topdown_confluence_state in _EDGE_TURN_CONFLUENCE_LABELS

    buy_relief = 0.0
    sell_relief = 0.0
    if session_ok and confluence_ok and buy_edge_ready:
        buy_relief = _clamp01(0.18 + (0.22 * _clamp01(buy_bias)))
    if session_ok and confluence_ok and sell_edge_ready:
        sell_relief = _clamp01(0.18 + (0.22 * _clamp01(sell_bias)))

    return _clamp01(max(buy_relief, sell_relief)), {
        "buy_relief": float(buy_relief),
        "sell_relief": float(sell_relief),
        "session_regime_state": session_regime_state,
        "topdown_confluence_state": topdown_confluence_state,
        "buy_edge_ready": bool(buy_edge_ready),
        "sell_edge_ready": bool(sell_edge_ready),
        "reason": (
            "edge turn relief enabled"
            if max(buy_relief, sell_relief) > 0.0
            else "edge turn relief inactive"
        ),
    }


def _breakout_fade_barrier(
    *,
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    session_expansion_state = str(primary_state_labels.get("session_expansion_state") or "UNKNOWN")
    topdown_slope_state = str(primary_state_labels.get("topdown_slope_state") or "UNKNOWN")
    topdown_confluence_state = str(primary_state_labels.get("topdown_confluence_state") or "UNKNOWN")

    buy_fade_barrier = 0.0
    sell_fade_barrier = 0.0
    direction = "NEUTRAL"

    if (
        session_expansion_state in _UP_EXPANSION_LABELS
        and topdown_slope_state in _UP_SLOPE_LABELS
        and topdown_confluence_state in {"BULL_CONFLUENCE", "WEAK_CONFLUENCE"}
    ):
        sell_fade_barrier = 0.26 if topdown_confluence_state == "WEAK_CONFLUENCE" else 0.34
        direction = "UP_CONTINUATION"
    elif (
        session_expansion_state in _DOWN_EXPANSION_LABELS
        and topdown_slope_state in _DOWN_SLOPE_LABELS
        and topdown_confluence_state in {"BEAR_CONFLUENCE", "WEAK_CONFLUENCE"}
    ):
        buy_fade_barrier = 0.26 if topdown_confluence_state == "WEAK_CONFLUENCE" else 0.34
        direction = "DOWN_CONTINUATION"

    return {
        "buy_fade_barrier": float(_clamp01(buy_fade_barrier)),
        "sell_fade_barrier": float(_clamp01(sell_fade_barrier)),
        "session_expansion_state": session_expansion_state,
        "topdown_slope_state": topdown_slope_state,
        "topdown_confluence_state": topdown_confluence_state,
        "direction": direction,
    }


def _middle_chop_barrier_v2(
    *,
    base_barrier: float,
    position_inputs: dict[str, float | str],
    semantic_inputs: dict[str, float | str],
    semantic_inputs_v2: dict[str, dict[str, float | str]],
    edge_turn_relief_v1: dict[str, float | str],
) -> tuple[float, dict[str, float | str]]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    execution_friction_state = str(primary_state_labels.get("execution_friction_state") or "UNKNOWN")
    volume_participation_state = str(primary_state_labels.get("volume_participation_state") or "UNKNOWN")
    middle_neutrality = float(position_inputs.get("middle_neutrality") or 0.0)
    belief_spread = abs(float(semantic_inputs.get("belief_spread") or 0.0))
    dominance_deadband = max(float(semantic_inputs.get("dominance_deadband") or 0.05), 1e-9)

    friction_boost = 0.10 if execution_friction_state in _HIGH_FRICTION_LABELS else 0.0
    participation_boost = 0.08 if volume_participation_state in _THIN_PARTICIPATION_LABELS else 0.0
    deadband_boost = 0.08 if belief_spread <= dominance_deadband else 0.0
    edge_relief = float(edge_turn_relief_v1.get("buy_relief", 0.0) or 0.0)
    edge_relief = max(edge_relief, float(edge_turn_relief_v1.get("sell_relief", 0.0) or 0.0))

    boost = _clamp01((friction_boost + participation_boost + deadband_boost) * _clamp01(0.35 + middle_neutrality))
    relief = _clamp01(edge_relief * (0.40 + (0.40 * (1.0 - middle_neutrality))))
    refined = _clamp01(base_barrier + boost - relief)

    return refined, {
        "base_barrier": float(base_barrier),
        "friction_boost": float(friction_boost),
        "participation_boost": float(participation_boost),
        "deadband_boost": float(deadband_boost),
        "scene_boost": float(boost),
        "edge_relief": float(relief),
        "execution_friction_state": execution_friction_state,
        "volume_participation_state": volume_participation_state,
        "reason": "middle scene refinement",
    }


def _advanced_input_gating_v1(
    *,
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    secondary_state_labels = semantic_inputs_v2.get("secondary_state_labels", {})
    activation_state = str(secondary_state_labels.get("advanced_input_activation_state") or "ADVANCED_IDLE")
    tick_flow_state = str(secondary_state_labels.get("tick_flow_state") or "UNAVAILABLE")
    order_book_state = str(secondary_state_labels.get("order_book_state") or "UNAVAILABLE")
    event_risk_state = str(primary_state_labels.get("event_risk_state") or "UNKNOWN")

    if activation_state in _ADVANCED_ACTIVE_LABELS:
        activation_weight = 1.0
        activation_mode = "ACTIVE"
    elif activation_state in _ADVANCED_PARTIAL_LABELS:
        activation_weight = 0.42
        activation_mode = "PARTIAL"
    elif activation_state in _ADVANCED_NEUTRAL_LABELS:
        activation_weight = 0.0
        activation_mode = "NEUTRAL"
    else:
        activation_weight = 0.0
        activation_mode = "IDLE"

    event_risk_boost = 0.0
    if activation_weight > 0.0:
        if event_risk_state == "HIGH_EVENT_RISK":
            event_risk_boost = 0.18 * activation_weight
        elif event_risk_state == "WATCH_EVENT_RISK":
            event_risk_boost = 0.08 * activation_weight

    tick_common_boost = 0.0
    buy_side_boost = 0.0
    sell_side_boost = 0.0
    if activation_weight > 0.0 and tick_flow_state not in _ADVANCED_SOURCE_NEUTRAL_LABELS:
        if tick_flow_state == "QUIET_FLOW":
            tick_common_boost = 0.06 * activation_weight
        elif tick_flow_state == "BURST_UP_FLOW":
            sell_side_boost += 0.08 * activation_weight
        elif tick_flow_state == "BURST_DOWN_FLOW":
            buy_side_boost += 0.08 * activation_weight

    order_book_common_boost = 0.0
    if activation_weight > 0.0 and order_book_state not in _ADVANCED_SOURCE_NEUTRAL_LABELS:
        if order_book_state == "THIN_BOOK":
            order_book_common_boost = 0.07 * activation_weight
        elif order_book_state == "ASK_IMBALANCE":
            buy_side_boost += 0.06 * activation_weight
        elif order_book_state == "BID_IMBALANCE":
            sell_side_boost += 0.06 * activation_weight

    common_boost = _clamp01(event_risk_boost + tick_common_boost + order_book_common_boost)
    buy_side_boost = _clamp01(buy_side_boost)
    sell_side_boost = _clamp01(sell_side_boost)
    active = activation_weight > 0.0 and (
        common_boost > 0.0 or buy_side_boost > 0.0 or sell_side_boost > 0.0
    )

    return {
        "activation_state": activation_state,
        "activation_mode": activation_mode,
        "activation_weight": float(activation_weight),
        "tick_flow_state": tick_flow_state,
        "order_book_state": order_book_state,
        "event_risk_state": event_risk_state,
        "event_risk_boost": float(event_risk_boost),
        "tick_common_boost": float(tick_common_boost),
        "order_book_common_boost": float(order_book_common_boost),
        "common_boost": float(common_boost),
        "buy_side_boost": float(buy_side_boost),
        "sell_side_boost": float(sell_side_boost),
        "active": bool(active),
        "reason": (
            "advanced inputs gated into barrier"
            if active
            else "advanced inputs neutralized"
        ),
    }


def _session_open_shock_barrier_v1(
    *,
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    runtime_source_inputs = semantic_inputs_v2.get("runtime_source_inputs", {})
    session_state_source = str(runtime_source_inputs.get("source_session_state_source") or "UNKNOWN").upper()
    signal_bar_ts = int(runtime_source_inputs.get("source_signal_bar_ts") or 0)
    session_expansion_state = str(primary_state_labels.get("session_expansion_state") or "UNKNOWN")
    execution_friction_state = str(primary_state_labels.get("execution_friction_state") or "UNKNOWN")
    spread_stress_state = str(primary_state_labels.get("spread_stress_state") or "UNKNOWN")

    if session_state_source not in _SESSION_OPEN_HOURS_KST or signal_bar_ts <= 0:
        return {
            "active": False,
            "minutes_from_open": -1.0,
            "session_state_source": session_state_source,
            "common_boost": 0.0,
            "reason": "session open source unavailable",
        }

    signal_dt = datetime.fromtimestamp(signal_bar_ts, _KST)
    session_open = datetime(
        signal_dt.year,
        signal_dt.month,
        signal_dt.day,
        _SESSION_OPEN_HOURS_KST[session_state_source],
        0,
        0,
        tzinfo=_KST,
    )
    minutes_from_open = max((signal_dt - session_open).total_seconds() / 60.0, 0.0)
    if minutes_from_open > 45.0:
        return {
            "active": False,
            "minutes_from_open": float(minutes_from_open),
            "session_state_source": session_state_source,
            "common_boost": 0.0,
            "reason": "outside session open shock window",
        }

    open_decay = _clamp01(1.0 - (minutes_from_open / 45.0))
    expansion_bonus = 0.04 if session_expansion_state != "IN_SESSION_BOX" else 0.0
    friction_mult = 1.10 if execution_friction_state in _HIGH_FRICTION_LABELS else 1.0
    spread_bonus = 0.04 if spread_stress_state in {"ELEVATED_SPREAD_STRESS", "HIGH_SPREAD_STRESS"} else 0.0
    common_boost = _clamp01(((0.06 + (0.16 * open_decay)) + expansion_bonus + spread_bonus) * friction_mult)

    return {
        "active": bool(common_boost > 0.0),
        "minutes_from_open": float(minutes_from_open),
        "session_state_source": session_state_source,
        "signal_timeframe": str(runtime_source_inputs.get("source_signal_timeframe") or ""),
        "common_boost": float(common_boost),
        "reason": "session open shock barrier active",
    }


def _duplicate_edge_barrier_v1(
    *,
    position_inputs: dict[str, float | str],
    semantic_inputs: dict[str, float | str],
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    secondary_context_label = str(position_inputs.get("secondary_context_label") or "")
    primary_label = str(position_inputs.get("primary_label") or "")
    secondary_sources = semantic_inputs_v2.get("secondary_source_inputs", {})
    touch_count = max(float(secondary_sources.get("source_sr_touch_count") or 0.0), 0.0)
    level_rank = max(float(secondary_sources.get("source_sr_level_rank") or 0.0), 0.0)
    belief_spread = abs(float(semantic_inputs.get("belief_spread") or 0.0))
    dominance_deadband = max(float(semantic_inputs.get("dominance_deadband") or 0.05), 1e-9)

    if touch_count < 2.0:
        return {
            "active": False,
            "common_boost": 0.0,
            "buy_side_boost": 0.0,
            "sell_side_boost": 0.0,
            "touch_count": float(touch_count),
            "level_rank": float(level_rank),
            "reason": "insufficient repeated edge touches",
        }

    buy_edge_ready = (
        secondary_context_label == "LOWER_CONTEXT"
        or primary_label.startswith("ALIGNED_LOWER")
        or primary_label == "LOWER_BIAS"
    )
    sell_edge_ready = (
        secondary_context_label == "UPPER_CONTEXT"
        or primary_label.startswith("ALIGNED_UPPER")
        or primary_label == "UPPER_BIAS"
    )
    touch_factor = _clamp01((touch_count - 1.5) / 2.5)
    if level_rank <= 1.0:
        rank_factor = 1.0
    elif level_rank <= 2.0:
        rank_factor = 0.80
    elif level_rank <= 3.0:
        rank_factor = 0.60
    else:
        rank_factor = 0.35
    ambiguity_factor = 1.0 if belief_spread <= (dominance_deadband * 1.5) else 0.35
    buy_conviction = _clamp01(
        max(
            float(semantic_inputs.get("buy_belief") or 0.0),
            float(semantic_inputs.get("buy_persistence") or 0.0),
        )
    )
    sell_conviction = _clamp01(
        max(
            float(semantic_inputs.get("sell_belief") or 0.0),
            float(semantic_inputs.get("sell_persistence") or 0.0),
        )
    )

    buy_side_boost = 0.0
    sell_side_boost = 0.0
    if buy_edge_ready:
        buy_side_boost = 0.22 * touch_factor * rank_factor * ambiguity_factor * (1.0 - buy_conviction)
    if sell_edge_ready:
        sell_side_boost = 0.22 * touch_factor * rank_factor * ambiguity_factor * (1.0 - sell_conviction)

    common_boost = 0.05 * touch_factor * ambiguity_factor
    return {
        "active": bool(max(common_boost, buy_side_boost, sell_side_boost) > 0.0),
        "common_boost": float(_clamp01(common_boost)),
        "buy_side_boost": float(_clamp01(buy_side_boost)),
        "sell_side_boost": float(_clamp01(sell_side_boost)),
        "touch_count": float(touch_count),
        "level_rank": float(level_rank),
        "belief_spread": float(belief_spread),
        "reason": "duplicate edge barrier active",
    }


def _micro_trap_barrier_v1(
    *,
    position_inputs: dict[str, float | str],
    semantic_inputs: dict[str, float | str],
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    secondary_state_labels = semantic_inputs_v2.get("secondary_state_labels", {})
    secondary_sources = semantic_inputs_v2.get("secondary_source_inputs", {})
    secondary_context_label = str(position_inputs.get("secondary_context_label") or "")

    recent_range_mean = max(float(secondary_sources.get("source_recent_range_mean") or 0.0), 0.0)
    recent_body_mean = max(float(secondary_sources.get("source_recent_body_mean") or 0.0), 0.0)
    current_adx = max(float(secondary_sources.get("source_current_adx") or 0.0), 0.0)
    current_plus_di = float(secondary_sources.get("source_current_plus_di") or 0.0)
    current_minus_di = float(secondary_sources.get("source_current_minus_di") or 0.0)
    body_share = recent_body_mean / max(recent_range_mean, 1e-9) if recent_range_mean > 0.0 else 0.0
    di_gap = abs(current_plus_di - current_minus_di)
    belief_spread = abs(float(semantic_inputs.get("belief_spread") or 0.0))
    dominance_deadband = max(float(semantic_inputs.get("dominance_deadband") or 0.05), 1e-9)

    adx_weakness = _clamp01((18.0 - current_adx) / 18.0)
    di_indecision = _clamp01((8.0 - di_gap) / 8.0)
    body_weakness = _clamp01((0.26 - body_share) / 0.26)
    deadband_flag = 1.0 if belief_spread <= (dominance_deadband * 1.4) else 0.0
    participation_flag = 1.0 if str(primary_state_labels.get("volume_participation_state") or "") in _THIN_PARTICIPATION_LABELS else 0.0
    quiet_flow_flag = 1.0 if str(secondary_state_labels.get("tick_flow_state") or "") in {"QUIET_FLOW", "BALANCED_FLOW"} else 0.0

    trap_score = _clamp01(
        (adx_weakness * 0.24)
        + (di_indecision * 0.20)
        + (body_weakness * 0.24)
        + (deadband_flag * 0.14)
        + (participation_flag * 0.10)
        + (quiet_flow_flag * 0.08)
    )
    common_boost = 0.20 * trap_score
    buy_side_boost = 0.0
    sell_side_boost = 0.0
    if secondary_context_label == "LOWER_CONTEXT" and current_minus_di >= current_plus_di + 3.0:
        buy_side_boost = common_boost * 0.62
    if secondary_context_label == "UPPER_CONTEXT" and current_plus_di >= current_minus_di + 3.0:
        sell_side_boost = common_boost * 0.62

    return {
        "active": bool(max(common_boost, buy_side_boost, sell_side_boost) > 0.0),
        "common_boost": float(_clamp01(common_boost)),
        "buy_side_boost": float(_clamp01(buy_side_boost)),
        "sell_side_boost": float(_clamp01(sell_side_boost)),
        "trap_score": float(trap_score),
        "body_share": float(body_share),
        "adx": float(current_adx),
        "di_gap": float(di_gap),
        "reason": "micro trap barrier active" if trap_score > 0.0 else "micro trap inactive",
    }


def _canonical_symbol(symbol: str) -> str:
    s = str(symbol or "").upper().strip()
    if "BTC" in s:
        return "BTCUSD"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    return s


def _vp_symbol_candidates(symbol: str) -> list[str]:
    canonical = _canonical_symbol(symbol)
    raw = str(symbol or "").upper().strip()
    candidates = [canonical]
    if raw and raw not in candidates:
        candidates.append(raw)
    return candidates


def _find_vp_col(row: pd.Series, names: tuple[str, ...]) -> str | None:
    cols = {str(col).lower(): str(col) for col in row.index}
    for name in names:
        key = str(name).lower()
        if key in cols:
            return cols[key]
    return None


def _read_vp_row(path: Path) -> dict[str, float] | None:
    try:
        if not path.exists():
            return None
        mtime = float(path.stat().st_mtime)
        cached = _VP_ROW_CACHE.get(str(path))
        if cached and cached[0] == mtime:
            return dict(cached[1])
        df = pd.read_csv(path, encoding="utf-8-sig")
        if df.empty:
            return None
        row = df.iloc[-1]
        poc_col = _find_vp_col(row, _VP_COL_CANDIDATES["poc"])
        vah_col = _find_vp_col(row, _VP_COL_CANDIDATES["vah"])
        val_col = _find_vp_col(row, _VP_COL_CANDIDATES["val"])
        if not poc_col or not vah_col or not val_col:
            return None
        payload = {
            "poc": _safe_float(row.get(poc_col), 0.0),
            "vah": _safe_float(row.get(vah_col), 0.0),
            "val": _safe_float(row.get(val_col), 0.0),
        }
        _VP_ROW_CACHE[str(path)] = (mtime, payload)
        return dict(payload)
    except Exception:
        return None


def _load_vp_row(symbol: str) -> tuple[dict[str, float] | None, str]:
    vp_dir = Path(getattr(Config, "VP_DATA_DIR", "") or "")
    vp_suffix = str(getattr(Config, "VP_FILENAME_SUFFIX", "_vp_data.csv") or "_vp_data.csv")
    if not str(vp_dir):
        return None, ""
    for candidate in _vp_symbol_candidates(symbol):
        path = vp_dir / f"{candidate}{vp_suffix}"
        payload = _read_vp_row(path)
        if payload:
            return payload, str(path)
    return None, ""


def _vp_collision_barrier_v1(
    *,
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    runtime_source_inputs = semantic_inputs_v2.get("runtime_source_inputs", {})
    symbol = str(runtime_source_inputs.get("source_symbol") or "")
    price = max(float(runtime_source_inputs.get("source_price") or 0.0), 0.0)
    if not symbol or price <= 0.0:
        return {
            "active": False,
            "available": False,
            "common_boost": 0.0,
            "reason": "vp source unavailable",
        }

    payload, source_path = _load_vp_row(symbol)
    if not payload:
        return {
            "active": False,
            "available": False,
            "common_boost": 0.0,
            "reason": "vp row unavailable",
        }

    poc = max(float(payload.get("poc") or 0.0), 0.0)
    vah = max(float(payload.get("vah") or 0.0), 0.0)
    val = max(float(payload.get("val") or 0.0), 0.0)
    width = max(abs(vah - val), max(price, 1e-9) * 0.001)
    near_ratio = float(getattr(Config, "VP_NEAR_POC_RATIO", 0.12) or 0.12)
    near_poc = abs(price - poc) <= (width * near_ratio)
    inside_value_area = bool(vah > 0.0 and val > 0.0 and val <= price <= vah)

    common_boost = 0.0
    if inside_value_area and near_poc:
        common_boost = 0.18
    elif inside_value_area:
        common_boost = 0.08

    return {
        "active": bool(common_boost > 0.0),
        "available": True,
        "common_boost": float(_clamp01(common_boost)),
        "source_path": source_path,
        "poc": float(poc),
        "vah": float(vah),
        "val": float(val),
        "inside_value_area": bool(inside_value_area),
        "near_poc": bool(near_poc),
        "reason": "vp collision barrier active" if common_boost > 0.0 else "vp collision inactive",
    }


def _post_event_cooldown_barrier_v1(
    *,
    semantic_inputs_v2: dict[str, dict[str, float | str]],
) -> dict[str, float | str]:
    primary_state_labels = semantic_inputs_v2.get("primary_state_labels", {})
    secondary_state_labels = semantic_inputs_v2.get("secondary_state_labels", {})
    runtime_source_inputs = semantic_inputs_v2.get("runtime_source_inputs", {})
    event_risk_state = str(primary_state_labels.get("event_risk_state") or "UNKNOWN")
    execution_friction_state = str(primary_state_labels.get("execution_friction_state") or "UNKNOWN")
    volume_participation_state = str(primary_state_labels.get("volume_participation_state") or "UNKNOWN")
    tick_flow_state = str(secondary_state_labels.get("tick_flow_state") or "UNAVAILABLE")
    activation_state = str(secondary_state_labels.get("advanced_input_activation_state") or "ADVANCED_IDLE")
    event_risk_score = float(runtime_source_inputs.get("source_event_risk_score") or 0.0)
    event_match_count = int(runtime_source_inputs.get("source_event_risk_match_count") or 0)

    if event_risk_state != "WATCH_EVENT_RISK" or activation_state in _ADVANCED_NEUTRAL_LABELS:
        return {
            "active": False,
            "common_boost": 0.0,
            "event_risk_state": event_risk_state,
            "reason": "post-event cooldown inactive",
        }

    friction_flag = 1.0 if execution_friction_state in _HIGH_FRICTION_LABELS else 0.0
    thin_flag = 1.0 if volume_participation_state in _THIN_PARTICIPATION_LABELS else 0.0
    quiet_flag = 1.0 if tick_flow_state in {"QUIET_FLOW", "BALANCED_FLOW"} else 0.0
    match_bonus = 1.0 if event_match_count > 0 else 0.0
    score = _clamp01(
        (0.24 * _clamp01(event_risk_score))
        + (0.28 * friction_flag)
        + (0.24 * thin_flag)
        + (0.14 * quiet_flag)
        + (0.10 * match_bonus)
    )
    common_boost = 0.18 * score
    return {
        "active": bool(common_boost > 0.0),
        "common_boost": float(_clamp01(common_boost)),
        "event_risk_state": event_risk_state,
        "event_risk_score": float(event_risk_score),
        "event_match_count": int(event_match_count),
        "reason": "post-event cooldown barrier active",
    }


def _policy_side_barriers(
    state_vector_v2: StateVectorV2,
    semantic_inputs: dict[str, float | str],
) -> tuple[float, float, float, str]:
    policy = str(semantic_inputs.get("direction_policy") or "UNKNOWN").upper()
    penalty = _clamp01(float(state_vector_v2.countertrend_penalty or 0.0))

    if policy == "BUY_ONLY":
        buy = 0.0
        sell = max(penalty, _BUY_ONLY_POLICY_BLOCK)
    elif policy == "SELL_ONLY":
        buy = max(penalty, _SELL_ONLY_POLICY_BLOCK)
        sell = 0.0
    elif policy == "NONE":
        buy = max(penalty, _NONE_POLICY_BLOCK)
        sell = max(penalty, _NONE_POLICY_BLOCK)
    elif policy == "BOTH":
        buy = 0.0
        sell = 0.0
    else:
        buy = penalty * 0.25
        sell = penalty * 0.25

    return _clamp01(buy), _clamp01(sell), _clamp01(max(buy, sell)), policy or "UNKNOWN"


def _liquidity_barrier(semantic_inputs: dict[str, float | str]) -> tuple[float, str]:
    liquidity_penalty = _clamp01(float(semantic_inputs.get("liquidity_penalty") or 0.0))
    volatility_penalty = _clamp01(float(semantic_inputs.get("volatility_penalty") or 0.0))
    barrier = max(liquidity_penalty, volatility_penalty * 0.85)
    reason = (
        f"liquidity_penalty={liquidity_penalty:.4f}, "
        f"volatility_penalty={volatility_penalty:.4f}"
    )
    return _clamp01(barrier), reason


def _side_readiness_relief(
    *,
    side: str,
    semantic_inputs: dict[str, float | str],
) -> tuple[float, str]:
    side_upper = str(side or "").upper()
    if side_upper == "BUY":
        belief = _clamp01(float(semantic_inputs.get("buy_belief") or 0.0))
        persistence = _clamp01(float(semantic_inputs.get("buy_persistence") or 0.0))
        evidence = _clamp01(float(semantic_inputs.get("buy_total_evidence") or 0.0))
    else:
        belief = _clamp01(float(semantic_inputs.get("sell_belief") or 0.0))
        persistence = _clamp01(float(semantic_inputs.get("sell_persistence") or 0.0))
        evidence = _clamp01(float(semantic_inputs.get("sell_total_evidence") or 0.0))

    relief = _clamp01((0.50 * belief) + (0.30 * persistence) + (0.20 * evidence))
    reason = (
        f"{side_upper.lower()} belief={belief:.4f}, "
        f"persistence={persistence:.4f}, evidence={evidence:.4f}"
    )
    return relief, reason


def _dominant_component_name(component_scores: dict[str, float], candidates: list[str]) -> str:
    best_name = candidates[0]
    best_score = float(component_scores.get(best_name, 0.0))
    for candidate in candidates[1:]:
        score = float(component_scores.get(candidate, 0.0))
        if score > best_score:
            best_name = candidate
            best_score = score
    return best_name


def build_barrier_state(
    position_snapshot: PositionSnapshot,
    state_vector_v2: StateVectorV2,
    evidence_vector_v1: EvidenceVector,
    belief_state_v1: BeliefState,
) -> BarrierState:
    position_inputs = _extract_position_structure_inputs(position_snapshot)
    semantic_inputs = _extract_semantic_barrier_inputs(state_vector_v2, evidence_vector_v1, belief_state_v1)
    semantic_inputs_v2 = _extract_semantic_barrier_inputs_v2(state_vector_v2)
    conflict_barrier, conflict_reason = _conflict_barrier(position_inputs)
    middle_chop_barrier_base, middle_meta = _middle_chop_barrier(position_inputs, semantic_inputs)
    edge_turn_relief_v1_score, edge_turn_relief_v1 = _edge_turn_relief(
        position_inputs=position_inputs,
        semantic_inputs=semantic_inputs,
        semantic_inputs_v2=semantic_inputs_v2,
    )
    middle_chop_barrier, middle_chop_barrier_v2 = _middle_chop_barrier_v2(
        base_barrier=middle_chop_barrier_base,
        position_inputs=position_inputs,
        semantic_inputs=semantic_inputs,
        semantic_inputs_v2=semantic_inputs_v2,
        edge_turn_relief_v1=edge_turn_relief_v1,
    )
    breakout_fade_barrier_v1 = _breakout_fade_barrier(
        semantic_inputs_v2=semantic_inputs_v2,
    )
    advanced_input_gating_v1 = _advanced_input_gating_v1(
        semantic_inputs_v2=semantic_inputs_v2,
    )
    session_open_shock_barrier_v1 = _session_open_shock_barrier_v1(
        semantic_inputs_v2=semantic_inputs_v2,
    )
    duplicate_edge_barrier_v1 = _duplicate_edge_barrier_v1(
        position_inputs=position_inputs,
        semantic_inputs=semantic_inputs,
        semantic_inputs_v2=semantic_inputs_v2,
    )
    micro_trap_barrier_v1 = _micro_trap_barrier_v1(
        position_inputs=position_inputs,
        semantic_inputs=semantic_inputs,
        semantic_inputs_v2=semantic_inputs_v2,
    )
    vp_collision_barrier_v1 = _vp_collision_barrier_v1(
        semantic_inputs_v2=semantic_inputs_v2,
    )
    post_event_cooldown_barrier_v1 = _post_event_cooldown_barrier_v1(
        semantic_inputs_v2=semantic_inputs_v2,
    )
    buy_policy_barrier, sell_policy_barrier, direction_policy_barrier, policy = _policy_side_barriers(
        state_vector_v2,
        semantic_inputs,
    )
    liquidity_barrier, liquidity_reason = _liquidity_barrier(semantic_inputs)
    buy_readiness_relief, buy_readiness_reason = _side_readiness_relief(
        side="BUY",
        semantic_inputs=semantic_inputs,
    )
    sell_readiness_relief, sell_readiness_reason = _side_readiness_relief(
        side="SELL",
        semantic_inputs=semantic_inputs,
    )

    common_barrier = (
        (_COMMON_CONFLICT_WEIGHT * conflict_barrier)
        + (_COMMON_CHOP_WEIGHT * middle_chop_barrier)
        + (_COMMON_LIQUIDITY_WEIGHT * liquidity_barrier)
        + float(advanced_input_gating_v1.get("common_boost") or 0.0)
        + float(session_open_shock_barrier_v1.get("common_boost") or 0.0)
        + float(duplicate_edge_barrier_v1.get("common_boost") or 0.0)
        + float(micro_trap_barrier_v1.get("common_boost") or 0.0)
        + float(vp_collision_barrier_v1.get("common_boost") or 0.0)
        + float(post_event_cooldown_barrier_v1.get("common_boost") or 0.0)
    )
    buy_barrier = _clamp01(
        common_barrier
        + (_SIDE_POLICY_WEIGHT * buy_policy_barrier)
        + float(breakout_fade_barrier_v1.get("buy_fade_barrier") or 0.0)
        + float(advanced_input_gating_v1.get("buy_side_boost") or 0.0)
        + float(duplicate_edge_barrier_v1.get("buy_side_boost") or 0.0)
        + float(micro_trap_barrier_v1.get("buy_side_boost") or 0.0)
        - (_SIDE_READINESS_RELIEF_WEIGHT * buy_readiness_relief)
        - (0.16 * float(edge_turn_relief_v1.get("buy_relief") or 0.0))
    )
    sell_barrier = _clamp01(
        common_barrier
        + (_SIDE_POLICY_WEIGHT * sell_policy_barrier)
        + float(breakout_fade_barrier_v1.get("sell_fade_barrier") or 0.0)
        + float(advanced_input_gating_v1.get("sell_side_boost") or 0.0)
        + float(duplicate_edge_barrier_v1.get("sell_side_boost") or 0.0)
        + float(micro_trap_barrier_v1.get("sell_side_boost") or 0.0)
        - (_SIDE_READINESS_RELIEF_WEIGHT * sell_readiness_relief)
        - (0.16 * float(edge_turn_relief_v1.get("sell_relief") or 0.0))
    )

    if buy_barrier < sell_barrier:
        dominant_side = "BUY"
    elif sell_barrier < buy_barrier:
        dominant_side = "SELL"
    else:
        dominant_side = "BALANCED"

    component_scores = {
        "common_barrier": float(common_barrier),
        "conflict_barrier": float(conflict_barrier),
        "middle_chop_barrier": float(middle_chop_barrier),
        "direction_policy_barrier": float(direction_policy_barrier),
        "liquidity_barrier": float(liquidity_barrier),
        "advanced_common_barrier": float(advanced_input_gating_v1.get("common_boost") or 0.0),
        "advanced_buy_side_barrier": float(advanced_input_gating_v1.get("buy_side_boost") or 0.0),
        "advanced_sell_side_barrier": float(advanced_input_gating_v1.get("sell_side_boost") or 0.0),
        "session_open_shock_barrier": float(session_open_shock_barrier_v1.get("common_boost") or 0.0),
        "duplicate_edge_common_barrier": float(duplicate_edge_barrier_v1.get("common_boost") or 0.0),
        "duplicate_edge_buy_side_barrier": float(duplicate_edge_barrier_v1.get("buy_side_boost") or 0.0),
        "duplicate_edge_sell_side_barrier": float(duplicate_edge_barrier_v1.get("sell_side_boost") or 0.0),
        "micro_trap_common_barrier": float(micro_trap_barrier_v1.get("common_boost") or 0.0),
        "micro_trap_buy_side_barrier": float(micro_trap_barrier_v1.get("buy_side_boost") or 0.0),
        "micro_trap_sell_side_barrier": float(micro_trap_barrier_v1.get("sell_side_boost") or 0.0),
        "vp_collision_barrier": float(vp_collision_barrier_v1.get("common_boost") or 0.0),
        "post_event_cooldown_barrier": float(post_event_cooldown_barrier_v1.get("common_boost") or 0.0),
        "buy_policy_barrier": float(buy_policy_barrier),
        "sell_policy_barrier": float(sell_policy_barrier),
        "buy_readiness_relief": float(buy_readiness_relief),
        "sell_readiness_relief": float(sell_readiness_relief),
    }
    buy_dominant_component = _dominant_component_name(
        component_scores,
        [
            "conflict_barrier",
            "middle_chop_barrier",
            "buy_policy_barrier",
            "liquidity_barrier",
            "advanced_common_barrier",
            "advanced_buy_side_barrier",
            "session_open_shock_barrier",
            "duplicate_edge_common_barrier",
            "duplicate_edge_buy_side_barrier",
            "micro_trap_common_barrier",
            "micro_trap_buy_side_barrier",
            "vp_collision_barrier",
            "post_event_cooldown_barrier",
        ],
    )
    sell_dominant_component = _dominant_component_name(
        component_scores,
        [
            "conflict_barrier",
            "middle_chop_barrier",
            "sell_policy_barrier",
            "liquidity_barrier",
            "advanced_common_barrier",
            "advanced_sell_side_barrier",
            "session_open_shock_barrier",
            "duplicate_edge_common_barrier",
            "duplicate_edge_sell_side_barrier",
            "micro_trap_common_barrier",
            "micro_trap_sell_side_barrier",
            "vp_collision_barrier",
            "post_event_cooldown_barrier",
        ],
    )
    breakout_fade_barrier_score = _clamp01(
        max(
            float(breakout_fade_barrier_v1.get("buy_fade_barrier") or 0.0),
            float(breakout_fade_barrier_v1.get("sell_fade_barrier") or 0.0),
        )
    )
    execution_friction_barrier_score = _execution_friction_barrier_score(semantic_inputs_v2)
    event_risk_barrier_score = _event_risk_barrier_score(
        semantic_inputs_v2,
        post_event_cooldown_barrier_v1,
    )
    pre_ml_feature_snapshot_v1 = {
        "required": {
            "buy_barrier": float(buy_barrier),
            "sell_barrier": float(sell_barrier),
            "conflict_barrier": float(conflict_barrier),
            "middle_chop_barrier": float(middle_chop_barrier),
            "direction_policy_barrier": float(direction_policy_barrier),
            "liquidity_barrier": float(liquidity_barrier),
        },
        "recommended": {
            "edge_turn_relief_score": float(edge_turn_relief_v1_score),
            "breakout_fade_barrier_score": float(breakout_fade_barrier_score),
            "execution_friction_barrier_score": float(execution_friction_barrier_score),
            "event_risk_barrier_score": float(event_risk_barrier_score),
        },
    }

    return BarrierState(
        buy_barrier=float(buy_barrier),
        sell_barrier=float(sell_barrier),
        conflict_barrier=float(conflict_barrier),
        middle_chop_barrier=float(middle_chop_barrier),
        direction_policy_barrier=float(direction_policy_barrier),
        liquidity_barrier=float(liquidity_barrier),
        metadata={
            "barrier_contract": "canonical_v1",
            "mapper_version": "barrier_state_v1_br11",
            "semantic_owner_contract": _BARRIER_SEMANTIC_OWNER_CONTRACT,
            "barrier_freeze_phase": _BARRIER_FREEZE_PHASE,
            "barrier_pre_ml_phase": _BARRIER_PRE_ML_PHASE,
            "barrier_role_statement": _BARRIER_ROLE_STATEMENT,
            "owner_boundaries_v1": dict(_BARRIER_OWNER_BOUNDARIES),
            "pre_ml_readiness_contract_v1": {
                "phase": _BARRIER_PRE_ML_PHASE,
                "status": "READY",
                "required_feature_fields": list(_BARRIER_PRE_ML_REQUIRED_FEATURE_FIELDS),
                "recommended_feature_fields": list(_BARRIER_PRE_ML_RECOMMENDED_FEATURE_FIELDS),
                "semantic_explainable_without_ml": True,
                "ml_usage_role": "feature_only_not_owner",
                "owner_collision_allowed": False,
                "owner_collision_boundary": (
                    "Barrier may be consumed by ML as a calibration feature, "
                    "but ML must not redefine position identity, response event identity, "
                    "state regime identity, evidence strength identity, belief persistence identity, "
                    "or direct action ownership."
                ),
                "safe_ml_targets": [
                    "entry_block_threshold_calibration",
                    "scene_relief_calibration",
                    "execution_friction_calibration",
                    "event_risk_block_calibration",
                ],
            },
            "semantic_owner_scope": {
                "allowed_domains": [
                    "entry_blocking",
                    "execution_risk_blocking",
                    "scene_relief_scaling",
                ],
                "forbidden_domains": [
                    "position_location_identity",
                    "response_event_identity",
                    "state_regime_identity",
                    "evidence_strength_identity",
                    "belief_persistence_identity",
                    "direct_buy_sell_side_identity",
                    "direct_action_identity",
                ],
                "identity_override_allowed": False,
            },
            "position_contract": "position_snapshot_v2",
            "state_contract": str((state_vector_v2.metadata or {}).get("state_contract") or "canonical_v2"),
            "state_mapper_version": str((state_vector_v2.metadata or {}).get("mapper_version") or ""),
            "evidence_contract": str((evidence_vector_v1.metadata or {}).get("evidence_contract") or "canonical_v1"),
            "evidence_mapper_version": str((evidence_vector_v1.metadata or {}).get("mapper_version") or ""),
            "belief_contract": str((belief_state_v1.metadata or {}).get("belief_contract") or "canonical_v1"),
            "belief_mapper_version": str((belief_state_v1.metadata or {}).get("mapper_version") or ""),
            "position_barrier_contract": {
                "inputs": [
                    "PositionInterpretation.primary_label",
                    "PositionInterpretation.bias_label",
                    "PositionInterpretation.secondary_context_label",
                    "PositionEnergySnapshot.position_conflict_score",
                    "PositionEnergySnapshot.middle_neutrality",
                ],
                "direction_source_used": False,
            },
            "position_structure_inputs": dict(position_inputs),
            "semantic_barrier_contract": {
                "state_inputs": [
                    "StateVectorV2.metadata.source_direction_policy",
                    "StateVectorV2.liquidity_penalty",
                    "StateVectorV2.volatility_penalty",
                    "StateVectorV2.countertrend_penalty",
                ],
                "evidence_inputs": [
                    "EvidenceVector.buy_total_evidence",
                    "EvidenceVector.sell_total_evidence",
                ],
                "belief_inputs": [
                    "BeliefState.buy_belief",
                    "BeliefState.sell_belief",
                    "BeliefState.buy_persistence",
                    "BeliefState.sell_persistence",
                    "BeliefState.belief_spread",
                    "BeliefState.metadata.global_dominant_mode",
                    "BeliefState.metadata.global_dominant_side",
                    "BeliefState.metadata.dominance_deadband",
                ],
                "state_v2_harvest_primary_labels": list(_BARRIER_STATE_V2_PRIMARY_LABEL_FIELDS),
                "state_v2_harvest_secondary_labels": list(_BARRIER_STATE_V2_SECONDARY_LABEL_FIELDS),
                "state_v2_harvest_secondary_sources": list(_BARRIER_STATE_V2_SECONDARY_SOURCE_FIELDS),
                "state_v2_harvest_used": True,
                "state_v2_harvest_math_used": True,
                "advanced_input_gating_used": True,
                "missing_barrier_inputs_v1_used": True,
                "semantic_reinterpretation_used": False,
            },
            "semantic_barrier_inputs": dict(semantic_inputs),
            "semantic_barrier_inputs_v2": dict(semantic_inputs_v2),
            "merge_mode": "weighted_common_barrier_with_policy_and_readiness_relief",
            "component_scores": component_scores,
            "edge_turn_relief_v1": edge_turn_relief_v1,
            "edge_turn_relief_score": float(edge_turn_relief_v1_score),
            "breakout_fade_barrier_v1": breakout_fade_barrier_v1,
            "breakout_fade_barrier_score": float(breakout_fade_barrier_score),
            "middle_chop_barrier_v2": middle_chop_barrier_v2,
            "advanced_input_gating_v1": advanced_input_gating_v1,
            "session_open_shock_barrier_v1": session_open_shock_barrier_v1,
            "duplicate_edge_barrier_v1": duplicate_edge_barrier_v1,
            "micro_trap_barrier_v1": micro_trap_barrier_v1,
            "vp_collision_barrier_v1": vp_collision_barrier_v1,
            "post_event_cooldown_barrier_v1": post_event_cooldown_barrier_v1,
            "execution_friction_barrier_score": float(execution_friction_barrier_score),
            "event_risk_barrier_score": float(event_risk_barrier_score),
            "pre_ml_feature_snapshot_v1": pre_ml_feature_snapshot_v1,
            "policy_side_barriers": {
                "BUY": float(buy_policy_barrier),
                "SELL": float(sell_policy_barrier),
                "source_direction_policy": policy,
            },
            "dominant_side": dominant_side,
            "dominant_component_by_side": {
                "BUY": buy_dominant_component,
                "SELL": sell_dominant_component,
            },
            "barrier_reasons": {
                "conflict_barrier": (
                    f"position conflict structure -> {conflict_reason}"
                ),
                "middle_chop_barrier": (
                    f"{middle_meta['primary_label']} / {middle_meta['reason']} -> "
                    f"middle_neutrality={middle_meta['middle_neutrality']:.4f}, "
                    f"spread_balance={middle_meta['spread_balance']:.4f}, "
                    f"persistence_weakness={middle_meta['persistence_weakness']:.4f}, "
                    f"evidence_balance={middle_meta['evidence_balance']:.4f}, "
                    f"dominant_mode={middle_meta['global_dominant_mode']}"
                ),
                "edge_turn_relief_v1": (
                    f"session_regime_state={edge_turn_relief_v1['session_regime_state']}, "
                    f"topdown_confluence_state={edge_turn_relief_v1['topdown_confluence_state']} -> "
                    f"buy_relief={float(edge_turn_relief_v1['buy_relief']):.4f}, "
                    f"sell_relief={float(edge_turn_relief_v1['sell_relief']):.4f}"
                ),
                "breakout_fade_barrier_v1": (
                    f"session_expansion_state={breakout_fade_barrier_v1['session_expansion_state']}, "
                    f"topdown_slope_state={breakout_fade_barrier_v1['topdown_slope_state']}, "
                    f"topdown_confluence_state={breakout_fade_barrier_v1['topdown_confluence_state']} -> "
                    f"buy_fade_barrier={float(breakout_fade_barrier_v1['buy_fade_barrier']):.4f}, "
                    f"sell_fade_barrier={float(breakout_fade_barrier_v1['sell_fade_barrier']):.4f}"
                ),
                "middle_chop_barrier_v2": (
                    f"base={middle_chop_barrier_v2['base_barrier']:.4f}, "
                    f"scene_boost={middle_chop_barrier_v2['scene_boost']:.4f}, "
                    f"edge_relief={middle_chop_barrier_v2['edge_relief']:.4f}, "
                    f"execution_friction_state={middle_chop_barrier_v2['execution_friction_state']}, "
                    f"volume_participation_state={middle_chop_barrier_v2['volume_participation_state']}"
                ),
                "advanced_input_gating_v1": (
                    f"activation_state={advanced_input_gating_v1['activation_state']}, "
                    f"activation_mode={advanced_input_gating_v1['activation_mode']}, "
                    f"event_risk_state={advanced_input_gating_v1['event_risk_state']}, "
                    f"tick_flow_state={advanced_input_gating_v1['tick_flow_state']}, "
                    f"order_book_state={advanced_input_gating_v1['order_book_state']} -> "
                    f"common_boost={float(advanced_input_gating_v1['common_boost']):.4f}, "
                    f"buy_side_boost={float(advanced_input_gating_v1['buy_side_boost']):.4f}, "
                    f"sell_side_boost={float(advanced_input_gating_v1['sell_side_boost']):.4f}"
                ),
                "session_open_shock_barrier_v1": (
                    f"session_state_source={session_open_shock_barrier_v1['session_state_source']}, "
                    f"minutes_from_open={float(session_open_shock_barrier_v1['minutes_from_open']):.2f}, "
                    f"common_boost={float(session_open_shock_barrier_v1['common_boost']):.4f}"
                ),
                "duplicate_edge_barrier_v1": (
                    f"touch_count={float(duplicate_edge_barrier_v1['touch_count']):.4f}, "
                    f"level_rank={float(duplicate_edge_barrier_v1['level_rank']):.4f}, "
                    f"common_boost={float(duplicate_edge_barrier_v1['common_boost']):.4f}, "
                    f"buy_side_boost={float(duplicate_edge_barrier_v1['buy_side_boost']):.4f}, "
                    f"sell_side_boost={float(duplicate_edge_barrier_v1['sell_side_boost']):.4f}"
                ),
                "micro_trap_barrier_v1": (
                    f"trap_score={float(micro_trap_barrier_v1['trap_score']):.4f}, "
                    f"body_share={float(micro_trap_barrier_v1['body_share']):.4f}, "
                    f"adx={float(micro_trap_barrier_v1['adx']):.4f}, "
                    f"di_gap={float(micro_trap_barrier_v1['di_gap']):.4f}, "
                    f"common_boost={float(micro_trap_barrier_v1['common_boost']):.4f}, "
                    f"buy_side_boost={float(micro_trap_barrier_v1['buy_side_boost']):.4f}, "
                    f"sell_side_boost={float(micro_trap_barrier_v1['sell_side_boost']):.4f}"
                ),
                "vp_collision_barrier_v1": (
                    f"available={bool(vp_collision_barrier_v1.get('available', False))}, "
                    f"inside_value_area={bool(vp_collision_barrier_v1.get('inside_value_area', False))}, "
                    f"near_poc={bool(vp_collision_barrier_v1.get('near_poc', False))}, "
                    f"common_boost={float(vp_collision_barrier_v1['common_boost']):.4f}"
                ),
                "post_event_cooldown_barrier_v1": (
                    f"event_risk_state={post_event_cooldown_barrier_v1['event_risk_state']}, "
                    f"event_risk_score={float(post_event_cooldown_barrier_v1.get('event_risk_score', 0.0) or 0.0):.4f}, "
                    f"event_match_count={int(post_event_cooldown_barrier_v1.get('event_match_count', 0) or 0)}, "
                    f"common_boost={float(post_event_cooldown_barrier_v1['common_boost']):.4f}"
                ),
                "direction_policy_barrier": (
                    f"direction_policy={policy} -> buy_policy_barrier={buy_policy_barrier:.4f}, "
                    f"sell_policy_barrier={sell_policy_barrier:.4f}"
                ),
                "liquidity_barrier": liquidity_reason,
                "buy_barrier": (
                    f"buy barrier dominated by {buy_dominant_component} with "
                    f"common={common_barrier:.4f}, buy_policy={buy_policy_barrier:.4f}, "
                    f"liquidity={liquidity_barrier:.4f}, "
                    f"breakout_fade={float(breakout_fade_barrier_v1.get('buy_fade_barrier') or 0.0):.4f}, "
                    f"advanced_side={float(advanced_input_gating_v1.get('buy_side_boost') or 0.0):.4f}, "
                    f"edge_relief={float(edge_turn_relief_v1.get('buy_relief') or 0.0):.4f}, "
                    f"buy_readiness_relief={buy_readiness_relief:.4f} ({buy_readiness_reason})"
                ),
                "sell_barrier": (
                    f"sell barrier dominated by {sell_dominant_component} with "
                    f"common={common_barrier:.4f}, sell_policy={sell_policy_barrier:.4f}, "
                    f"liquidity={liquidity_barrier:.4f}, "
                    f"breakout_fade={float(breakout_fade_barrier_v1.get('sell_fade_barrier') or 0.0):.4f}, "
                    f"advanced_side={float(advanced_input_gating_v1.get('sell_side_boost') or 0.0):.4f}, "
                    f"edge_relief={float(edge_turn_relief_v1.get('sell_relief') or 0.0):.4f}, "
                    f"sell_readiness_relief={sell_readiness_relief:.4f} ({sell_readiness_reason})"
                ),
            },
        },
    )
