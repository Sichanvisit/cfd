from __future__ import annotations

from backend.trading.engine.core.models import (
    EnergySnapshot,
    PositionSnapshot,
    PositionVector,
    ResponseVector,
    StateVector,
    StateVectorV2,
)

POSITION_WEIGHTS = {
    "bb20": 0.42,
    "box": 0.34,
    "bb44": 0.16,
    "sr": 0.05,
    "trendline": 0.03,
}
POSITION_WEIGHT_PRIORITY = ("bb20", "box", "bb44", "sr", "trendline")
POSITION_WEIGHT_ROLES = {
    "bb20": "primary_location_anchor",
    "box": "structural_envelope",
    "bb44": "micro_tiebreak",
    "sr": "level_context",
    "trendline": "slope_context",
}

_MIDDLE_BOX_LIMIT = 0.42
_MIDDLE_BB20_LIMIT = 0.42
_MIDDLE_BB44_LIMIT = 0.48

StateInput = StateVector | StateVectorV2


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _state_source_fields(state: StateInput) -> dict[str, float | str]:
    metadata = dict(getattr(state, "metadata", {}) or {})
    if isinstance(state, StateVectorV2):
        return {
            "market_mode": str(metadata.get("source_regime", "UNKNOWN") or "UNKNOWN").upper(),
            "direction_policy": str(metadata.get("source_direction_policy", "UNKNOWN") or "UNKNOWN").upper(),
            "s_noise": float(metadata.get("source_noise", 0.0) or 0.0),
            "s_conflict": float(metadata.get("source_conflict", 0.0) or 0.0),
            "s_alignment": float(metadata.get("source_alignment", 0.0) or 0.0),
            "s_disparity": float(metadata.get("source_disparity", 0.0) or 0.0),
            "s_volatility": float(metadata.get("source_volatility", 0.0) or 0.0),
            "state_contract": str(metadata.get("state_contract", "canonical_v3") or "canonical_v3"),
            "state_mapper_version": str(metadata.get("mapper_version", "") or ""),
            "state_input_mode": "state_vector_v2_direct",
        }
    return {
        "market_mode": str(state.market_mode or "UNKNOWN").upper(),
        "direction_policy": str(state.direction_policy or "UNKNOWN").upper(),
        "s_noise": float(state.s_noise or 0.0),
        "s_conflict": float(state.s_conflict or 0.0),
        "s_alignment": float(state.s_alignment or 0.0),
        "s_disparity": float(state.s_disparity or 0.0),
        "s_volatility": float(state.s_volatility or 0.0),
        "state_contract": str(metadata.get("state_contract", "legacy_v1") or "legacy_v1"),
        "state_mapper_version": str(metadata.get("mapper_version", "") or ""),
        "state_input_mode": "state_vector_legacy",
    }


def compute_energy_snapshot(
    position: PositionVector,
    response: ResponseVector,
    state: StateInput,
    position_snapshot: PositionSnapshot | None = None,
) -> EnergySnapshot:
    state_source = _state_source_fields(state)
    market_mode = str(state_source["market_mode"])
    direction_policy = str(state_source["direction_policy"])
    s_noise = float(state_source["s_noise"])
    s_conflict = float(state_source["s_conflict"])
    s_alignment = float(state_source["s_alignment"])
    s_disparity = float(state_source["s_disparity"])
    s_volatility = float(state_source["s_volatility"])
    energy_middle_context = (
        abs(position.x_box) <= _MIDDLE_BOX_LIMIT
        and abs(position.x_bb20) <= _MIDDLE_BB20_LIMIT
        and abs(position.x_bb44) <= _MIDDLE_BB44_LIMIT
    )
    axis_values = {
        "x_box": float(position.x_box),
        "x_bb20": float(position.x_bb20),
        "x_bb44": float(position.x_bb44),
        "x_sr": float(position.x_sr),
        "x_trendline": float(position.x_trendline),
        "x_ma20": float(position.x_ma20),
        "x_ma60": float(position.x_ma60),
    }
    snapshot_interpretation = position_snapshot.interpretation if position_snapshot is not None else None
    snapshot_energy = position_snapshot.energy if position_snapshot is not None else None
    position_conflict_kind = "" if snapshot_interpretation is None else str(snapshot_interpretation.conflict_kind or "")
    upper_conflict_context = position_conflict_kind in {"CONFLICT_BOX_UPPER_BB20_LOWER", "CONFLICT_BB20_UPPER_BB44_LOWER"}
    lower_conflict_context = position_conflict_kind in {"CONFLICT_BOX_LOWER_BB20_UPPER", "CONFLICT_BB20_LOWER_BB44_UPPER"}
    position_upper_pressure = (
        max(position.x_box, 0.0) * POSITION_WEIGHTS["box"]
        + max(position.x_bb20, 0.0) * POSITION_WEIGHTS["bb20"]
        + max(position.x_bb44, 0.0) * POSITION_WEIGHTS["bb44"]
        + max(position.x_sr, 0.0) * POSITION_WEIGHTS["sr"]
        + max(position.x_trendline, 0.0) * POSITION_WEIGHTS["trendline"]
    )
    position_lower_pressure = (
        max(-position.x_box, 0.0) * POSITION_WEIGHTS["box"]
        + max(-position.x_bb20, 0.0) * POSITION_WEIGHTS["bb20"]
        + max(-position.x_bb44, 0.0) * POSITION_WEIGHTS["bb44"]
        + max(-position.x_sr, 0.0) * POSITION_WEIGHTS["sr"]
        + max(-position.x_trendline, 0.0) * POSITION_WEIGHTS["trendline"]
    )
    pressure_gap = position_upper_pressure - position_lower_pressure
    if snapshot_interpretation is not None and position_conflict_kind:
        position_conflict_dominance = str(snapshot_interpretation.dominance_label or "BALANCED_CONFLICT")
        position_conflict_confidence = float(
            snapshot_energy.position_conflict_score if snapshot_energy is not None else 0.0
        )
    else:
        position_conflict_dominance = "NONE"
        position_conflict_confidence = 0.0

    conflict_axes = {
        "CONFLICT_BOX_UPPER_BB20_LOWER": ("x_box", "x_bb20"),
        "CONFLICT_BOX_LOWER_BB20_UPPER": ("x_box", "x_bb20"),
        "CONFLICT_BB20_UPPER_BB44_LOWER": ("x_bb20", "x_bb44"),
        "CONFLICT_BB20_LOWER_BB44_UPPER": ("x_bb20", "x_bb44"),
    }.get(position_conflict_kind, tuple())
    if len(conflict_axes) == 2:
        position_conflict_magnitude = abs(axis_values[conflict_axes[0]] - axis_values[conflict_axes[1]])
    else:
        position_conflict_magnitude = abs(position.x_box - position.x_bb20)

    # Position is symmetric: lower-side location produces buy energy, upper-side location sell energy.
    buy_position_force = position_lower_pressure
    sell_position_force = position_upper_pressure

    buy_response_force = (
        response.r_bb20_lower_hold * 0.30
        + response.r_bb20_mid_hold * 0.10
        + response.r_bb20_mid_reclaim * 0.15
        + response.r_bb20_upper_break * 0.10
        + response.r_bb44_lower_hold * 0.10
        + response.r_box_lower_bounce * 0.20
        + response.r_box_mid_hold * 0.08
        + response.r_box_upper_break * 0.05
        + response.r_candle_lower_reject * 0.10
    )
    sell_response_force = (
        response.r_bb20_lower_break * 0.18
        + response.r_bb20_mid_reject * 0.10
        + response.r_bb20_mid_lose * 0.15
        + response.r_bb20_upper_reject * 0.20
        + response.r_bb44_upper_reject * 0.10
        + response.r_box_lower_break * 0.15
        + response.r_box_mid_reject * 0.08
        + response.r_box_upper_reject * 0.12
        + response.r_candle_upper_reject * 0.10
    )

    state_damping = _clamp((1.0 - 0.45 * s_noise) * (1.0 - 0.55 * s_conflict), 0.15, 1.0)
    if market_mode == "RANGE":
        regime_multiplier = 1.00
    elif market_mode == "TREND":
        regime_multiplier = 0.90
    elif market_mode == "SHOCK":
        regime_multiplier = 0.55
    else:
        regime_multiplier = 0.85

    alignment_boost = 1.0 + 0.08 * s_alignment
    disparity_boost = 1.0 + 0.05 * s_disparity
    volatility_boost = 1.0 + 0.04 * s_volatility

    direction_buy = 1.0
    direction_sell = 1.0
    if direction_policy == "BUY_ONLY":
        direction_sell = 0.65
    elif direction_policy == "SELL_ONLY":
        direction_buy = 0.65

    buy_response_scale = 1.0
    sell_position_scale = 1.0
    sell_response_scale = 1.0
    buy_position_scale = 1.0

    # Trend pullbacks can reclaim/lose the midline before the outer edge is retested.
    # Add a mild asymmetry so those confirmations are not lost behind upper/lower position pressure.
    trend_pullback_buy_boost = (
        market_mode == "TREND"
        and direction_policy == "BUY_ONLY"
        and energy_middle_context
        and not upper_conflict_context
        and position.x_box <= 0.36
        and position.x_bb20 <= 0.36
        and (
            response.r_bb20_mid_hold > 0.0
            or response.r_bb20_mid_reclaim > 0.0
            or response.r_box_mid_hold > 0.0
            or response.r_candle_lower_reject > 0.0
        )
    )
    trend_pullback_sell_boost = (
        market_mode == "TREND"
        and direction_policy == "SELL_ONLY"
        and energy_middle_context
        and not lower_conflict_context
        and position.x_box >= -0.36
        and position.x_bb20 >= -0.36
        and (
            response.r_bb20_mid_reject > 0.0
            or response.r_bb20_mid_lose > 0.0
            or response.r_box_mid_reject > 0.0
            or response.r_candle_upper_reject > 0.0
        )
    )

    if trend_pullback_buy_boost:
        buy_response_scale *= 1.70
        buy_position_scale *= 1.20
        sell_position_scale *= 0.72
        sell_response_scale *= 0.85
    elif trend_pullback_sell_boost:
        sell_response_scale *= 1.70
        sell_position_scale *= 1.20
        buy_position_scale *= 0.72
        buy_response_scale *= 0.85

    buy_force = ((buy_position_force * buy_position_scale) + (buy_response_force * buy_response_scale)) * state_damping * regime_multiplier * alignment_boost * disparity_boost * volatility_boost * direction_buy
    sell_force = ((sell_position_force * sell_position_scale) + (sell_response_force * sell_response_scale)) * state_damping * regime_multiplier * alignment_boost * disparity_boost * volatility_boost * direction_sell
    net_force = float(buy_force - sell_force)

    return EnergySnapshot(
        buy_position_force=float(buy_position_force),
        sell_position_force=float(sell_position_force),
        buy_response_force=float(buy_response_force),
        sell_response_force=float(sell_response_force),
        state_damping=float(state_damping),
        regime_multiplier=float(regime_multiplier),
        buy_force=float(buy_force),
        sell_force=float(sell_force),
        net_force=float(net_force),
        metadata={
            "position_weights": dict(POSITION_WEIGHTS),
            "position_weight_priority": list(POSITION_WEIGHT_PRIORITY),
            "position_weight_roles": dict(POSITION_WEIGHT_ROLES),
            "alignment_boost": float(alignment_boost),
            "disparity_boost": float(disparity_boost),
            "volatility_boost": float(volatility_boost),
            "direction_buy_scale": float(direction_buy),
            "direction_sell_scale": float(direction_sell),
            "buy_position_scale": float(buy_position_scale),
            "buy_response_scale": float(buy_response_scale),
            "sell_position_scale": float(sell_position_scale),
            "sell_response_scale": float(sell_response_scale),
            "trend_pullback_buy_boost": bool(trend_pullback_buy_boost),
            "trend_pullback_sell_boost": bool(trend_pullback_sell_boost),
            "energy_middle_context": bool(energy_middle_context),
            "energy_middle_context_source": "coordinate_heuristic",
            "energy_middle_thresholds": {
                "x_box": float(_MIDDLE_BOX_LIMIT),
                "x_bb20": float(_MIDDLE_BB20_LIMIT),
                "x_bb44": float(_MIDDLE_BB44_LIMIT),
            },
            "upper_conflict_context": bool(upper_conflict_context),
            "lower_conflict_context": bool(lower_conflict_context),
            "position_axis_values": axis_values,
            "position_primary_label": ("" if snapshot_interpretation is None else str(snapshot_interpretation.primary_label)),
            "position_secondary_context_label": (
                "" if snapshot_interpretation is None else str(snapshot_interpretation.secondary_context_label)
            ),
            "position_dominance_label": (
                "" if snapshot_interpretation is None else str(snapshot_interpretation.dominance_label)
            ),
            "position_conflict_kind": position_conflict_kind,
            "position_conflict_axes": list(conflict_axes),
            "position_conflict_magnitude": float(position_conflict_magnitude),
            "position_conflict_upper_pressure": float(position_upper_pressure),
            "position_conflict_lower_pressure": float(position_lower_pressure),
            "position_conflict_dominance": position_conflict_dominance,
            "position_conflict_dominance_side": (
                "UPPER"
                if position_conflict_dominance == "UPPER_DOMINANT_CONFLICT"
                else "LOWER"
                if position_conflict_dominance == "LOWER_DOMINANT_CONFLICT"
                else "BALANCED"
                if position_conflict_dominance == "BALANCED_CONFLICT"
                else "NONE"
            ),
            "position_conflict_confidence": float(position_conflict_confidence),
            "position_conflict_source": ("position_snapshot" if snapshot_interpretation is not None else "none"),
            "state_contract": str(state_source["state_contract"]),
            "state_mapper_version": str(state_source["state_mapper_version"]),
            "state_input_mode": str(state_source["state_input_mode"]),
            "state_source_fields_v1": {
                "market_mode": market_mode,
                "direction_policy": direction_policy,
                "s_noise": float(s_noise),
                "s_conflict": float(s_conflict),
                "s_alignment": float(s_alignment),
                "s_disparity": float(s_disparity),
                "s_volatility": float(s_volatility),
            },
        },
    )
