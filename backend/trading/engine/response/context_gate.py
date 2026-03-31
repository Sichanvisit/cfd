from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import EngineContext

_PRIMARY_ZONE_WEIGHTS = {
    "box_zone": 0.45,
    "bb20_zone": 0.35,
    "bb44_zone": 0.20,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _soft_clip01(value: float, *, scale: float = 1.0) -> float:
    if value <= 0.0:
        return 0.0
    return _clamp01(1.0 - pow(2.718281828, -float(value) / max(float(scale), 1e-9)))


def _weighted_sum(pairs: list[tuple[float, float]]) -> float:
    return sum(float(weight) * float(value) for weight, value in pairs)


def _max_from(values: list[float]) -> float:
    return max((float(v) for v in values), default=0.0)


def _zone_to_lower_score(zone: str) -> float:
    mapping = {
        "BELOW": 1.00,
        "LOWER_EDGE": 0.88,
        "LOWER": 0.72,
        "MIDDLE": 0.24,
        "UPPER": 0.06,
        "UPPER_EDGE": 0.00,
        "ABOVE": 0.00,
    }
    return float(mapping.get(str(zone or "MIDDLE").upper(), 0.24))


def _zone_to_upper_score(zone: str) -> float:
    mapping = {
        "ABOVE": 1.00,
        "UPPER_EDGE": 0.88,
        "UPPER": 0.72,
        "MIDDLE": 0.24,
        "LOWER": 0.06,
        "LOWER_EDGE": 0.00,
        "BELOW": 0.00,
    }
    return float(mapping.get(str(zone or "MIDDLE").upper(), 0.24))


def _zone_to_middle_score(zone: str) -> float:
    mapping = {
        "MIDDLE": 1.00,
        "LOWER": 0.38,
        "UPPER": 0.38,
        "LOWER_EDGE": 0.18,
        "UPPER_EDGE": 0.18,
        "BELOW": 0.05,
        "ABOVE": 0.05,
    }
    return float(mapping.get(str(zone or "MIDDLE").upper(), 0.30))


def _fallback_zone(raw_state: str, *, family: str) -> str:
    key = str(raw_state or "").upper()
    if family == "lower":
        if key in {"LOWER", "LOWER_EDGE"}:
            return "LOWER"
        if key in {"BREAKDOWN", "BELOW"}:
            return "BELOW"
        if key in {"UPPER", "UPPER_EDGE", "BREAKOUT", "ABOVE"}:
            return "UPPER"
        return "MIDDLE"
    return "MIDDLE"


def _extract_position_gate_input(ctx: EngineContext) -> dict[str, Any]:
    metadata = dict(ctx.metadata or {})
    gate_input = dict(metadata.get("position_gate_input_v1") or {})
    if gate_input:
        return gate_input
    box_zone = _fallback_zone(ctx.box_state, family="lower")
    bb_zone = _fallback_zone(ctx.bb_state, family="lower")
    return {
        "zones": {
            "box_zone": box_zone,
            "bb20_zone": bb_zone,
            "bb44_zone": "MIDDLE",
        },
        "interpretation": {
            "primary_label": "UNRESOLVED_POSITION",
            "secondary_context_label": "NEUTRAL_CONTEXT",
            "mtf_context_weight_profile_v1": {
                "bias": 0.0,
                "owner": "STATE_CANDIDATE",
            },
        },
        "energy": {
            "middle_neutrality": 0.30,
            "position_conflict_score": 0.0,
            "lower_position_force": 0.0,
            "upper_position_force": 0.0,
        },
        "position_scale": {
            "compression_score": 0.0,
            "expansion_score": 0.0,
            "map_size_state": "NORMAL",
        },
    }


def _zone_context_weights(position_gate_input: dict[str, Any]) -> dict[str, float]:
    zones = dict(position_gate_input.get("zones") or {})
    lower_zone = _weighted_sum(
        [
            (_PRIMARY_ZONE_WEIGHTS["box_zone"], _zone_to_lower_score(str(zones.get("box_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb20_zone"], _zone_to_lower_score(str(zones.get("bb20_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb44_zone"], _zone_to_lower_score(str(zones.get("bb44_zone") or "MIDDLE"))),
        ]
    )
    upper_zone = _weighted_sum(
        [
            (_PRIMARY_ZONE_WEIGHTS["box_zone"], _zone_to_upper_score(str(zones.get("box_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb20_zone"], _zone_to_upper_score(str(zones.get("bb20_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb44_zone"], _zone_to_upper_score(str(zones.get("bb44_zone") or "MIDDLE"))),
        ]
    )
    middle_zone = _weighted_sum(
        [
            (_PRIMARY_ZONE_WEIGHTS["box_zone"], _zone_to_middle_score(str(zones.get("box_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb20_zone"], _zone_to_middle_score(str(zones.get("bb20_zone") or "MIDDLE"))),
            (_PRIMARY_ZONE_WEIGHTS["bb44_zone"], _zone_to_middle_score(str(zones.get("bb44_zone") or "MIDDLE"))),
        ]
    )
    return {
        "lower_zone_weight": _clamp01(lower_zone),
        "upper_zone_weight": _clamp01(upper_zone),
        "middle_zone_weight": _clamp01(middle_zone),
    }


def _support_resistance_anchors(
    sr_subsystem: dict[str, Any],
    trendline_subsystem: dict[str, Any],
) -> dict[str, float]:
    sr_strengths = dict(sr_subsystem.get("strengths") or {})
    trend_strengths = dict(trendline_subsystem.get("strengths") or {})
    trend_per_tf = dict(trendline_subsystem.get("per_timeframe") or {})

    support_proximity = _max_from(
        [
            _to_float(sr_subsystem.get("sr_support_proximity"), 0.0),
            *[_to_float((entry or {}).get("support_proximity"), 0.0) for entry in trend_per_tf.values()],
        ]
    )
    resistance_proximity = _max_from(
        [
            _to_float(sr_subsystem.get("sr_resistance_proximity"), 0.0),
            *[_to_float((entry or {}).get("resistance_proximity"), 0.0) for entry in trend_per_tf.values()],
        ]
    )

    return {
        "support_anchor": _clamp01(
            _max_from(
                [
                    support_proximity,
                    _to_float(sr_strengths.get("support_hold_strength"), 0.0),
                    _to_float(trend_strengths.get("trend_support_hold_strength"), 0.0),
                ]
            )
        ),
        "support_break_anchor": _clamp01(
            _max_from(
                [
                    _to_float(sr_strengths.get("support_break_strength"), 0.0),
                    _to_float(trend_strengths.get("trend_support_break_strength"), 0.0),
                ]
            )
        ),
        "resistance_anchor": _clamp01(
            _max_from(
                [
                    resistance_proximity,
                    _to_float(sr_strengths.get("resistance_reject_strength"), 0.0),
                    _to_float(trend_strengths.get("trend_resistance_reject_strength"), 0.0),
                ]
            )
        ),
        "resistance_break_anchor": _clamp01(
            _max_from(
                [
                    _to_float(sr_strengths.get("resistance_break_strength"), 0.0),
                    _to_float(trend_strengths.get("trend_resistance_break_strength"), 0.0),
                ]
            )
        ),
        "support_proximity": float(support_proximity),
        "resistance_proximity": float(resistance_proximity),
    }


def _big_map_bias(position_gate_input: dict[str, Any]) -> dict[str, float]:
    interpretation = dict(position_gate_input.get("interpretation") or {})
    mtf_context = dict(interpretation.get("mtf_context_weight_profile_v1") or {})
    bias = _to_float(mtf_context.get("bias"), 0.0)
    return {
        "raw_bias": float(bias),
        "bull_bias_weight": _soft_clip01(max(bias, 0.0), scale=0.35),
        "bear_bias_weight": _soft_clip01(max(-bias, 0.0), scale=0.35),
    }


def _ambiguity(position_gate_input: dict[str, Any], micro_subsystem: dict[str, Any]) -> dict[str, float]:
    interpretation = dict(position_gate_input.get("interpretation") or {})
    energy = dict(position_gate_input.get("energy") or {})
    primary_label = str(interpretation.get("primary_label") or "UNRESOLVED_POSITION").upper()
    middle_neutrality = _clamp01(_to_float(energy.get("middle_neutrality"), 0.0))
    conflict_score = _clamp01(_to_float(energy.get("position_conflict_score"), 0.0))
    indecision = _clamp01(_to_float((micro_subsystem.get("strengths") or {}).get("micro_indecision_strength"), 0.0))
    label_penalty = 0.0
    if "CONFLICT" in primary_label:
        label_penalty = 0.82
    elif primary_label == "UNRESOLVED_POSITION":
        label_penalty = 0.58
    return {
        "ambiguity_penalty": _clamp01(max(middle_neutrality, conflict_score, indecision * 0.72, label_penalty)),
        "middle_neutrality": middle_neutrality,
        "position_conflict_score": conflict_score,
        "label_penalty": label_penalty,
    }


def _size_context(position_gate_input: dict[str, Any]) -> dict[str, float]:
    position_scale = dict(position_gate_input.get("position_scale") or {})
    return {
        "compression_score": _clamp01(_to_float(position_scale.get("compression_score"), 0.0)),
        "expansion_score": _clamp01(_to_float(position_scale.get("expansion_score"), 0.0)),
    }


def _contextualize(base: float, *, gate: float, opposite: float = 0.0, ambiguity: float = 0.0, floor: float = 0.16) -> float:
    modifier = _clamp01(float(floor) + (0.76 * float(gate)) - (0.22 * float(opposite)) - (0.18 * float(ambiguity)))
    return _clamp01(float(base) * modifier)


def _candidate_sum(pairs: list[tuple[float, float]]) -> float:
    return _clamp01(sum(float(weight) * float(value) for weight, value in pairs))


def _failed_breakdown_squeeze_signal(
    *,
    lower_zone: float,
    support_anchor: float,
    compression: float,
    ambiguity_penalty: float,
    micro_indecision: float,
    gated_candle_motif: dict[str, float],
    gated_structure_motif: dict[str, float],
    gated_sr: dict[str, float],
    gated_trendline: dict[str, float],
    gated_micro: dict[str, float],
) -> dict[str, float]:
    break_attempt = _clamp01(
        max(
            _to_float(gated_sr.get("support_break_strength"), 0.0),
            _to_float(gated_trendline.get("trend_support_break_strength"), 0.0),
            _to_float(gated_micro.get("micro_bear_break_strength"), 0.0),
            _to_float(gated_micro.get("micro_lose_down_strength"), 0.0) * 0.82,
        )
    )
    rebound_probe = _clamp01(
        max(
            _to_float(gated_micro.get("micro_bull_reject_strength"), 0.0),
            _to_float(gated_candle_motif.get("bull_reject"), 0.0),
            _to_float(gated_structure_motif.get("support_hold_confirm"), 0.0),
            _to_float(gated_structure_motif.get("reversal_base_up"), 0.0),
        )
    )
    reclaim_probe = _clamp01(
        max(
            _to_float(gated_micro.get("micro_reclaim_up_strength"), 0.0),
            _to_float(gated_candle_motif.get("bull_reversal_2bar"), 0.0),
            _to_float(gated_candle_motif.get("bull_reversal_3bar"), 0.0),
            _to_float(gated_candle_motif.get("bull_break_body"), 0.0) * 0.70,
        )
    )
    follow_through = _clamp01(
        max(
            _to_float(gated_micro.get("micro_bear_break_strength"), 0.0),
            _to_float(gated_micro.get("micro_lose_down_strength"), 0.0),
            _to_float(gated_candle_motif.get("bear_break_body"), 0.0),
            _to_float(gated_sr.get("support_break_strength"), 0.0) * 0.72,
        )
    )
    support_rearm = _clamp01(
        max(
            float(lower_zone),
            float(support_anchor),
            _to_float(gated_sr.get("support_hold_strength"), 0.0),
            _to_float(gated_trendline.get("trend_support_hold_strength"), 0.0),
            float(compression) * 0.65,
        )
    )
    coexistence = _clamp01(min(break_attempt, max(rebound_probe, reclaim_probe)))
    failed_breakdown_strength = _soft_clip01(
        max(
            0.0,
            coexistence
            + (0.28 * support_rearm)
            + (0.12 * float(compression))
            - (0.20 * follow_through)
            - (0.12 * float(ambiguity_penalty)),
        ),
        scale=0.45,
    )
    squeeze_up_strength = _soft_clip01(
        max(
            0.0,
            (0.62 * failed_breakdown_strength)
            + (0.28 * max(reclaim_probe, _to_float(gated_micro.get("micro_bull_break_strength"), 0.0)))
            + (0.10 * max(0.0, rebound_probe - follow_through))
            - (0.14 * float(micro_indecision)),
        ),
        scale=0.40,
    )
    return {
        "break_attempt_strength": break_attempt,
        "rebound_probe_strength": rebound_probe,
        "reclaim_probe_strength": reclaim_probe,
        "follow_through_strength": follow_through,
        "support_rearm_strength": support_rearm,
        "failed_breakdown_strength": failed_breakdown_strength,
        "squeeze_up_strength": squeeze_up_strength,
    }


def compute_response_context_gate(
    ctx: EngineContext,
    *,
    candle_motif: dict[str, Any] | None,
    structure_motif: dict[str, Any] | None,
    sr_subsystem: dict[str, Any] | None,
    trendline_subsystem: dict[str, Any] | None,
    micro_subsystem: dict[str, Any] | None,
) -> dict[str, Any]:
    candle_motif = dict(candle_motif or {})
    structure_motif = dict(structure_motif or {})
    sr_subsystem = dict(sr_subsystem or {})
    trendline_subsystem = dict(trendline_subsystem or {})
    micro_subsystem = dict(micro_subsystem or {})

    position_gate_input = _extract_position_gate_input(ctx)
    zone_weights = _zone_context_weights(position_gate_input)
    anchors = _support_resistance_anchors(sr_subsystem, trendline_subsystem)
    bias_weights = _big_map_bias(position_gate_input)
    ambiguity = _ambiguity(position_gate_input, micro_subsystem)
    size_context = _size_context(position_gate_input)
    micro_strengths = dict(micro_subsystem.get("strengths") or {})
    sr_strengths = dict(sr_subsystem.get("strengths") or {})
    trend_strengths = dict(trendline_subsystem.get("strengths") or {})

    lower_zone = zone_weights["lower_zone_weight"]
    upper_zone = zone_weights["upper_zone_weight"]
    middle_zone = zone_weights["middle_zone_weight"]
    support_anchor = anchors["support_anchor"]
    support_break_anchor = anchors["support_break_anchor"]
    resistance_anchor = anchors["resistance_anchor"]
    resistance_break_anchor = anchors["resistance_break_anchor"]
    bull_bias = bias_weights["bull_bias_weight"]
    bear_bias = bias_weights["bear_bias_weight"]
    ambiguity_penalty = ambiguity["ambiguity_penalty"]
    compression = size_context["compression_score"]
    expansion = size_context["expansion_score"]
    micro_bull_reject = _clamp01(_to_float(micro_strengths.get("micro_bull_reject_strength"), 0.0))
    micro_bear_reject = _clamp01(_to_float(micro_strengths.get("micro_bear_reject_strength"), 0.0))
    micro_bull_break = _clamp01(_to_float(micro_strengths.get("micro_bull_break_strength"), 0.0))
    micro_bear_break = _clamp01(_to_float(micro_strengths.get("micro_bear_break_strength"), 0.0))
    micro_reclaim_up = _clamp01(_to_float(micro_strengths.get("micro_reclaim_up_strength"), 0.0))
    micro_lose_down = _clamp01(_to_float(micro_strengths.get("micro_lose_down_strength"), 0.0))
    micro_indecision = _clamp01(_to_float(micro_strengths.get("micro_indecision_strength"), 0.0))

    gate_weights = {
        **zone_weights,
        **anchors,
        **bias_weights,
        **ambiguity,
        **size_context,
        "bull_reversal_gate": _clamp01((0.48 * lower_zone) + (0.26 * support_anchor) + (0.10 * micro_bull_reject) + (0.10 * bull_bias) + (0.06 * (1.0 - ambiguity_penalty))),
        "bear_reversal_gate": _clamp01((0.48 * upper_zone) + (0.26 * resistance_anchor) + (0.10 * micro_bear_reject) + (0.10 * bear_bias) + (0.06 * (1.0 - ambiguity_penalty))),
        "bull_break_gate": _clamp01((0.42 * upper_zone) + (0.20 * resistance_break_anchor) + (0.14 * micro_bull_break) + (0.10 * bull_bias) + (0.08 * expansion) + (0.06 * (1.0 - ambiguity_penalty))),
        "bear_break_gate": _clamp01((0.42 * lower_zone) + (0.20 * support_break_anchor) + (0.14 * micro_bear_break) + (0.10 * bear_bias) + (0.08 * expansion) + (0.06 * (1.0 - ambiguity_penalty))),
        "mid_reclaim_gate": _clamp01((0.54 * middle_zone) + (0.20 * micro_reclaim_up) + (0.12 * bull_bias) + (0.08 * compression) + (0.06 * (1.0 - ambiguity_penalty))),
        "mid_lose_gate": _clamp01((0.54 * middle_zone) + (0.20 * micro_lose_down) + (0.12 * bear_bias) + (0.08 * compression) + (0.06 * (1.0 - ambiguity_penalty))),
    }

    gated_candle_motif = {
        "bull_reject": _contextualize(_to_float(candle_motif.get("bull_reject"), 0.0), gate=gate_weights["bull_reversal_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty),
        "bear_reject": _contextualize(_to_float(candle_motif.get("bear_reject"), 0.0), gate=gate_weights["bear_reversal_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty),
        "bull_reversal_2bar": _contextualize(_to_float(candle_motif.get("bull_reversal_2bar"), 0.0), gate=gate_weights["bull_reversal_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty),
        "bear_reversal_2bar": _contextualize(_to_float(candle_motif.get("bear_reversal_2bar"), 0.0), gate=gate_weights["bear_reversal_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty),
        "bull_reversal_3bar": _contextualize(_to_float(candle_motif.get("bull_reversal_3bar"), 0.0), gate=gate_weights["bull_reversal_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty),
        "bear_reversal_3bar": _contextualize(_to_float(candle_motif.get("bear_reversal_3bar"), 0.0), gate=gate_weights["bear_reversal_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty),
        "bull_break_body": _contextualize(_to_float(candle_motif.get("bull_break_body"), 0.0), gate=gate_weights["bull_break_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty),
        "bear_break_body": _contextualize(_to_float(candle_motif.get("bear_break_body"), 0.0), gate=gate_weights["bear_break_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty),
        "indecision": _clamp01(_to_float(candle_motif.get("indecision"), 0.0) * _clamp01(0.55 + (0.45 * max(middle_zone, ambiguity_penalty, micro_indecision)))),
        "climax": _clamp01(_to_float(candle_motif.get("climax"), 0.0) * _clamp01(0.34 + (0.32 * expansion) + (0.18 * max(gate_weights["bull_break_gate"], gate_weights["bear_break_gate"])) + (0.16 * micro_indecision))),
    }

    gated_structure_motif = {
        "reversal_base_up": _contextualize(_to_float(structure_motif.get("reversal_base_up"), 0.0), gate=gate_weights["bull_reversal_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty),
        "reversal_top_down": _contextualize(_to_float(structure_motif.get("reversal_top_down"), 0.0), gate=gate_weights["bear_reversal_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty),
        "support_hold_confirm": _contextualize(_to_float(structure_motif.get("support_hold_confirm"), 0.0), gate=_clamp01((0.62 * lower_zone) + (0.38 * support_anchor)), opposite=upper_zone, ambiguity=ambiguity_penalty),
        "resistance_reject_confirm": _contextualize(_to_float(structure_motif.get("resistance_reject_confirm"), 0.0), gate=_clamp01((0.62 * upper_zone) + (0.38 * resistance_anchor)), opposite=lower_zone, ambiguity=ambiguity_penalty),
    }

    gated_sr = {
        "support_hold_strength": _contextualize(_to_float(sr_strengths.get("support_hold_strength"), 0.0), gate=_clamp01((0.58 * lower_zone) + (0.42 * support_anchor)), opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "support_break_strength": _contextualize(_to_float(sr_strengths.get("support_break_strength"), 0.0), gate=_clamp01((0.56 * lower_zone) + (0.30 * support_break_anchor) + (0.14 * expansion)), opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "resistance_reject_strength": _contextualize(_to_float(sr_strengths.get("resistance_reject_strength"), 0.0), gate=_clamp01((0.58 * upper_zone) + (0.42 * resistance_anchor)), opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "resistance_break_strength": _contextualize(_to_float(sr_strengths.get("resistance_break_strength"), 0.0), gate=_clamp01((0.56 * upper_zone) + (0.30 * resistance_break_anchor) + (0.14 * expansion)), opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.18),
    }

    gated_trendline = {
        "trend_support_hold_strength": _contextualize(_to_float(trend_strengths.get("trend_support_hold_strength"), 0.0), gate=_clamp01((0.56 * lower_zone) + (0.44 * support_anchor)), opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "trend_support_break_strength": _contextualize(_to_float(trend_strengths.get("trend_support_break_strength"), 0.0), gate=_clamp01((0.54 * lower_zone) + (0.30 * support_break_anchor) + (0.16 * expansion)), opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "trend_resistance_reject_strength": _contextualize(_to_float(trend_strengths.get("trend_resistance_reject_strength"), 0.0), gate=_clamp01((0.56 * upper_zone) + (0.44 * resistance_anchor)), opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.18),
        "trend_resistance_break_strength": _contextualize(_to_float(trend_strengths.get("trend_resistance_break_strength"), 0.0), gate=_clamp01((0.54 * upper_zone) + (0.30 * resistance_break_anchor) + (0.16 * expansion)), opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.18),
    }

    gated_micro = {
        "micro_bull_reject_strength": _contextualize(micro_bull_reject, gate=_clamp01((0.46 * lower_zone) + (0.24 * support_anchor) + (0.18 * middle_zone) + (0.12 * bull_bias)), opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.20),
        "micro_bear_reject_strength": _contextualize(micro_bear_reject, gate=_clamp01((0.46 * upper_zone) + (0.24 * resistance_anchor) + (0.18 * middle_zone) + (0.12 * bear_bias)), opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.20),
        "micro_bull_break_strength": _contextualize(micro_bull_break, gate=gate_weights["bull_break_gate"], opposite=lower_zone, ambiguity=ambiguity_penalty, floor=0.20),
        "micro_bear_break_strength": _contextualize(micro_bear_break, gate=gate_weights["bear_break_gate"], opposite=upper_zone, ambiguity=ambiguity_penalty, floor=0.20),
        "micro_indecision_strength": _clamp01(micro_indecision * _clamp01(0.58 + (0.42 * max(middle_zone, ambiguity_penalty)))),
        "micro_reclaim_up_strength": _contextualize(micro_reclaim_up, gate=gate_weights["mid_reclaim_gate"], opposite=gate_weights["mid_lose_gate"], ambiguity=ambiguity_penalty, floor=0.18),
        "micro_lose_down_strength": _contextualize(micro_lose_down, gate=gate_weights["mid_lose_gate"], opposite=gate_weights["mid_reclaim_gate"], ambiguity=ambiguity_penalty, floor=0.18),
    }

    failed_breakdown = _failed_breakdown_squeeze_signal(
        lower_zone=lower_zone,
        support_anchor=support_anchor,
        compression=compression,
        ambiguity_penalty=ambiguity_penalty,
        micro_indecision=micro_indecision,
        gated_candle_motif=gated_candle_motif,
        gated_structure_motif=gated_structure_motif,
        gated_sr=gated_sr,
        gated_trendline=gated_trendline,
        gated_micro=gated_micro,
    )

    lower_hold_candidate = _candidate_sum(
        [
            (0.20, gated_candle_motif["bull_reject"]),
            (0.11, gated_candle_motif["bull_reversal_2bar"]),
            (0.09, gated_candle_motif["bull_reversal_3bar"]),
            (0.13, gated_structure_motif["support_hold_confirm"]),
            (0.10, gated_structure_motif["reversal_base_up"]),
            (0.14, gated_sr["support_hold_strength"]),
            (0.09, gated_trendline["trend_support_hold_strength"]),
            (0.08, gated_micro["micro_bull_reject_strength"]),
            (0.06, gated_micro["micro_reclaim_up_strength"]),
        ]
    )
    lower_break_candidate = _candidate_sum(
        [
            (0.18, gated_candle_motif["bear_break_body"]),
            (0.18, gated_sr["support_break_strength"]),
            (0.15, gated_trendline["trend_support_break_strength"]),
            (0.17, gated_micro["micro_bear_break_strength"]),
            (0.12, gated_micro["micro_lose_down_strength"]),
            (0.10, gated_candle_motif["bear_reversal_2bar"]),
            (0.10, gated_candle_motif["bear_reversal_3bar"]),
        ]
    )
    mid_reclaim_candidate = _candidate_sum(
        [
            (0.28, gated_micro["micro_reclaim_up_strength"]),
            (0.16, gated_candle_motif["bull_reject"]),
            (0.12, gated_candle_motif["bull_reversal_2bar"]),
            (0.10, gated_candle_motif["bull_reversal_3bar"]),
            (0.12, gated_candle_motif["bull_break_body"]),
            (0.10, gated_structure_motif["reversal_base_up"]),
            (0.12, gated_candle_motif["indecision"] * 0.25),
        ]
    )
    mid_lose_candidate = _candidate_sum(
        [
            (0.28, gated_micro["micro_lose_down_strength"]),
            (0.16, gated_candle_motif["bear_reject"]),
            (0.12, gated_candle_motif["bear_reversal_2bar"]),
            (0.10, gated_candle_motif["bear_reversal_3bar"]),
            (0.12, gated_candle_motif["bear_break_body"]),
            (0.10, gated_structure_motif["reversal_top_down"]),
            (0.12, gated_candle_motif["indecision"] * 0.25),
        ]
    )
    upper_reject_candidate = _candidate_sum(
        [
            (0.20, gated_candle_motif["bear_reject"]),
            (0.11, gated_candle_motif["bear_reversal_2bar"]),
            (0.09, gated_candle_motif["bear_reversal_3bar"]),
            (0.13, gated_structure_motif["resistance_reject_confirm"]),
            (0.10, gated_structure_motif["reversal_top_down"]),
            (0.14, gated_sr["resistance_reject_strength"]),
            (0.09, gated_trendline["trend_resistance_reject_strength"]),
            (0.08, gated_micro["micro_bear_reject_strength"]),
            (0.06, gated_micro["micro_lose_down_strength"]),
        ]
    )
    upper_break_candidate = _candidate_sum(
        [
            (0.18, gated_candle_motif["bull_break_body"]),
            (0.18, gated_sr["resistance_break_strength"]),
            (0.15, gated_trendline["trend_resistance_break_strength"]),
            (0.17, gated_micro["micro_bull_break_strength"]),
            (0.12, gated_micro["micro_reclaim_up_strength"]),
            (0.10, gated_candle_motif["bull_reversal_2bar"]),
            (0.10, gated_candle_motif["bull_reversal_3bar"]),
        ]
    )

    failed_breakdown_strength = _to_float(failed_breakdown.get("failed_breakdown_strength"), 0.0)
    squeeze_up_strength = _to_float(failed_breakdown.get("squeeze_up_strength"), 0.0)
    lower_hold_candidate = _clamp01(lower_hold_candidate + (0.16 * failed_breakdown_strength) + (0.08 * squeeze_up_strength))
    mid_reclaim_candidate = _clamp01(mid_reclaim_candidate + (0.14 * failed_breakdown_strength) + (0.10 * squeeze_up_strength))
    lower_break_candidate = _clamp01(max(0.0, lower_break_candidate - (0.18 * failed_breakdown_strength) - (0.10 * squeeze_up_strength)))
    mid_lose_candidate = _clamp01(max(0.0, mid_lose_candidate - (0.08 * failed_breakdown_strength)))

    pre_axis_candidates = {
        "lower_hold_candidate": lower_hold_candidate,
        "lower_break_candidate": lower_break_candidate,
        "mid_reclaim_candidate": mid_reclaim_candidate,
        "mid_lose_candidate": mid_lose_candidate,
        "upper_reject_candidate": upper_reject_candidate,
        "upper_break_candidate": upper_break_candidate,
    }
    fired_candidates = [name for name, value in pre_axis_candidates.items() if float(value) >= 0.25]

    return {
        "version": "response_context_gate_v1",
        "owner": "RESPONSE_PRE_AXIS_GATE",
        "position_gate_input": position_gate_input,
        "gate_weights": gate_weights,
        "gated_candle_motif_v1": gated_candle_motif,
        "gated_structure_motif_v1": gated_structure_motif,
        "gated_sr_v1": gated_sr,
        "gated_trendline_v1": gated_trendline,
        "gated_micro_v1": gated_micro,
        "failed_breakdown_squeeze_v1": failed_breakdown,
        "pre_axis_candidates": pre_axis_candidates,
        "fired_candidates": fired_candidates,
    }
