from __future__ import annotations

from typing import Any

from backend.trading.engine.core.models import (
    POSITION_FALLBACK_LABELS,
    POSITION_ALIGNMENT_LABELS,
    POSITION_BIAS_LABELS,
    POSITION_CONFLICT_LABELS,
    POSITION_DOMINANCE_LABELS,
    POSITION_PRIMARY_LABELS,
    POSITION_PRIMARY_AXES,
    POSITION_SECONDARY_CONTEXT_LABELS,
    POSITION_SECONDARY_AXES,
    POSITION_ZONE_LABELS,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    PositionVector,
    PositionZones,
)

_POSITION_AXIS_WEIGHTS = {
    "box": 0.45,
    "bb20": 0.35,
    "bb44": 0.20,
}
_POSITION_ZONE_VERSION = "v2_standardized"
_POSITION_ZONE_STANDARD_BANDS = {
    "below": -1.00,
    "lower_edge": -0.75,
    "middle": 0.18,
    "upper_edge": 0.75,
    "above": 1.00,
}
_POSITION_ZONE_SPECS = {
    "x_box": dict(_POSITION_ZONE_STANDARD_BANDS),
    "x_bb20": dict(_POSITION_ZONE_STANDARD_BANDS),
    "x_bb44": dict(_POSITION_ZONE_STANDARD_BANDS),
}
_RAW_FALLBACK_WINDOW = 0.06
_MIDDLE_NEUTRALITY_SCALE = 0.18
_CONFLICT_AXIS_THRESHOLD = 0.10
_POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE = 0.58
_POSITION_ENERGY_VERSION = "v2_position_energy"
_MTF_MA_POSITION_WEIGHTS = {
    "1D": 0.34,
    "4H": 0.27,
    "1H": 0.20,
    "30M": 0.11,
    "15M": 0.08,
}
_MTF_TRENDLINE_POSITION_WEIGHTS = {
    "4H": 0.38,
    "1H": 0.30,
    "15M": 0.20,
    "1M": 0.12,
}
_SECONDARY_ZONE_FIELDS = {
    "x_ma20": "ma20_zone",
    "x_ma60": "ma60_zone",
    "x_sr": "sr_zone",
    "x_trendline": "trendline_zone",
}


def _get_position_value(position: Any, name: str) -> float:
    value = 0.0
    if hasattr(position, "get"):
        value = position.get(name, 0.0)
    else:
        value = getattr(position, name, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _metadata_value(position: Any, key: str, default: str = "") -> str:
    metadata = getattr(position, "metadata", {}) or {}
    return str(metadata.get(key, default) or default)


def _position_scale_metadata(position: Any) -> dict[str, Any]:
    metadata = getattr(position, "metadata", {}) or {}
    scale_metadata = metadata.get("position_scale", {}) or {}
    return dict(scale_metadata)


def _mtf_ma_big_map_metadata(position: Any) -> dict[str, Any]:
    metadata = getattr(position, "metadata", {}) or {}
    mtf_map = metadata.get("mtf_ma_big_map_v1", {}) or {}
    return dict(mtf_map)


def _mtf_trendline_map_metadata(position: Any) -> dict[str, Any]:
    metadata = getattr(position, "metadata", {}) or {}
    trendline_map = metadata.get("mtf_trendline_map_v1", {}) or {}
    return dict(trendline_map)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _weighted_mtf_ma_summary(position: Any) -> dict[str, Any]:
    mtf_map = _mtf_ma_big_map_metadata(position)
    entries = dict(mtf_map.get("entries", {}) or {})
    lower_support_force = 0.0
    upper_resistance_force = 0.0
    tf_details: dict[str, dict[str, float | str]] = {}

    for tf, weight in _MTF_MA_POSITION_WEIGHTS.items():
        entry = dict(entries.get(tf, {}) or {})
        side = str(entry.get("side") or "UNKNOWN").upper()
        proximity = _clamp01(float(entry.get("proximity", 0.0) or 0.0))
        if side == "ABOVE":
            lower_support_force += float(weight) * proximity
        elif side == "BELOW":
            upper_resistance_force += float(weight) * proximity
        elif side == "ON_LINE":
            shared = float(weight) * proximity * 0.5
            lower_support_force += shared
            upper_resistance_force += shared
        tf_details[tf] = {
            "weight": float(weight),
            "side": side,
            "proximity": proximity,
            "weighted_contribution": float(weight) * proximity,
        }

    stack_state = str(mtf_map.get("stack_state") or "UNKNOWN").upper()
    if stack_state == "BULL_STACK":
        lower_support_force += 0.08
    elif stack_state == "BEAR_STACK":
        upper_resistance_force += 0.08

    bias = float(lower_support_force - upper_resistance_force)
    return {
        "version": "mtf_ma_weight_profile_v1",
        "weights": dict(_MTF_MA_POSITION_WEIGHTS),
        "details": tf_details,
        "stack_state": stack_state,
        "lower_support_force": float(lower_support_force),
        "upper_resistance_force": float(upper_resistance_force),
        "bias": bias,
    }


def _weighted_mtf_trendline_summary(position: Any) -> dict[str, Any]:
    trendline_map = _mtf_trendline_map_metadata(position)
    entries = dict(trendline_map.get("entries", {}) or {})
    lower_support_force = 0.0
    upper_resistance_force = 0.0
    tf_details: dict[str, dict[str, float | str]] = {}

    for tf, weight in _MTF_TRENDLINE_POSITION_WEIGHTS.items():
        entry = dict(entries.get(tf, {}) or {})
        support_side = str(entry.get("support_side") or "UNKNOWN").upper()
        support_proximity = _clamp01(float(entry.get("support_proximity", 0.0) or 0.0))
        resistance_side = str(entry.get("resistance_side") or "UNKNOWN").upper()
        resistance_proximity = _clamp01(float(entry.get("resistance_proximity", 0.0) or 0.0))

        if support_side == "ABOVE":
            lower_support_force += float(weight) * support_proximity
        elif support_side == "ON_LINE":
            shared = float(weight) * support_proximity * 0.5
            lower_support_force += shared
            upper_resistance_force += shared
        elif support_side == "BELOW":
            upper_resistance_force += float(weight) * support_proximity * 0.5

        if resistance_side == "BELOW":
            upper_resistance_force += float(weight) * resistance_proximity
        elif resistance_side == "ON_LINE":
            shared = float(weight) * resistance_proximity * 0.5
            lower_support_force += shared
            upper_resistance_force += shared
        elif resistance_side == "ABOVE":
            lower_support_force += float(weight) * resistance_proximity * 0.5

        tf_details[tf] = {
            "weight": float(weight),
            "support_side": support_side,
            "support_proximity": support_proximity,
            "resistance_side": resistance_side,
            "resistance_proximity": resistance_proximity,
        }

    bias = float(lower_support_force - upper_resistance_force)
    return {
        "version": "mtf_trendline_weight_profile_v1",
        "weights": dict(_MTF_TRENDLINE_POSITION_WEIGHTS),
        "details": tf_details,
        "lower_support_force": float(lower_support_force),
        "upper_resistance_force": float(upper_resistance_force),
        "bias": bias,
    }


def _axis_payload(position: PositionVector, axes: tuple[str, ...]) -> dict[str, float]:
    return {axis: _get_position_value(position, axis) for axis in axes}


def _zone_spec(axis_name: str) -> dict[str, float]:
    return dict(_POSITION_ZONE_SPECS.get(axis_name, _POSITION_ZONE_STANDARD_BANDS))


def _zone_from_axis_coord(axis_name: str, value: float) -> str:
    spec = _zone_spec(axis_name)
    if value <= float(spec["below"]):
        return "BELOW"
    if value <= float(spec["lower_edge"]):
        return "LOWER_EDGE"
    if value < -float(spec["middle"]):
        return "LOWER"
    if value <= float(spec["middle"]):
        return "MIDDLE"
    if value < float(spec["upper_edge"]):
        return "UPPER"
    if value < float(spec["above"]):
        return "UPPER_EDGE"
    return "ABOVE"


def _normalize_raw_zone(raw: str | None, default: str) -> str:
    key = str(raw or "").strip().upper()
    mapping = {
        "BREAKDOWN": "BELOW",
        "BELOW": "BELOW",
        "LOWER_EDGE": "LOWER_EDGE",
        "LOWER": "LOWER",
        "MID": "MIDDLE",
        "MIDDLE": "MIDDLE",
        "UPPER": "UPPER",
        "UPPER_EDGE": "UPPER_EDGE",
        "BREAKOUT": "ABOVE",
        "ABOVE": "ABOVE",
    }
    return mapping.get(key, default)


def _resolve_raw_states(
    position: PositionVector,
    raw_box_state: str | None,
    raw_bb_state: str | None,
) -> tuple[str, str]:
    resolved_box = raw_box_state or _metadata_value(position, "raw_box_state") or _metadata_value(position, "box_state", "UNKNOWN")
    resolved_bb = raw_bb_state or _metadata_value(position, "raw_bb_state") or _metadata_value(position, "bb_state", "UNKNOWN")
    return str(resolved_box or "UNKNOWN").upper(), str(resolved_bb or "UNKNOWN").upper()


def _should_use_raw_fallback(x_box: float, x_bb20: float, x_bb44: float) -> bool:
    return _raw_fallback_status(x_box, x_bb20, x_bb44)["eligible"]


def _raw_fallback_status(x_box: float, x_bb20: float, x_bb44: float) -> dict[str, Any]:
    ambiguity = {
        "x_box": abs(x_box) <= _RAW_FALLBACK_WINDOW,
        "x_bb20": abs(x_bb20) <= _RAW_FALLBACK_WINDOW,
        "x_bb44": abs(x_bb44) <= _RAW_FALLBACK_WINDOW,
    }
    return {
        "eligible": all(bool(flag) for flag in ambiguity.values()),
        "window": _RAW_FALLBACK_WINDOW,
        "ambiguity": ambiguity,
    }


def _zone_side(zone: str) -> str:
    if zone in {"BELOW", "LOWER_EDGE", "LOWER"}:
        return "LOWER"
    if zone in {"ABOVE", "UPPER_EDGE", "UPPER"}:
        return "UPPER"
    return "MIDDLE"


def _detect_aligned_label(zones: PositionZones) -> str:
    box_zone = zones.box_zone
    bb20_zone = zones.bb20_zone
    bb44_zone = zones.bb44_zone
    if box_zone in {"BELOW", "LOWER_EDGE"} and bb20_zone in {"BELOW", "LOWER_EDGE"} and _zone_side(bb44_zone) == "LOWER":
        return "ALIGNED_LOWER_STRONG"
    if _zone_side(box_zone) == "LOWER" and _zone_side(bb20_zone) == "LOWER" and _zone_side(bb44_zone) != "UPPER":
        return "ALIGNED_LOWER_WEAK"
    if box_zone in {"ABOVE", "UPPER_EDGE"} and bb20_zone in {"ABOVE", "UPPER_EDGE"} and _zone_side(bb44_zone) == "UPPER":
        return "ALIGNED_UPPER_STRONG"
    if _zone_side(box_zone) == "UPPER" and _zone_side(bb20_zone) == "UPPER" and _zone_side(bb44_zone) != "LOWER":
        return "ALIGNED_UPPER_WEAK"
    if box_zone == "MIDDLE" and bb20_zone == "MIDDLE" and bb44_zone == "MIDDLE":
        return "ALIGNED_MIDDLE"
    return ""


def _soften_alignment_label(
    alignment_label: str,
    pos_composite: float,
    zones: PositionZones,
) -> tuple[str, dict[str, Any]]:
    if alignment_label not in {"ALIGNED_LOWER_WEAK", "ALIGNED_UPPER_WEAK"}:
        return alignment_label, {
            "downgraded": False,
            "reason": "alignment_not_softened",
            "min_abs_pos_composite": _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE,
        }

    bb44_side = _zone_side(zones.bb44_zone)
    expected_bb44_side = "LOWER" if alignment_label == "ALIGNED_LOWER_WEAK" else "UPPER"
    if bb44_side != expected_bb44_side:
        return "", {
            "downgraded": True,
            "reason": "weak_alignment_requires_bb44_side_support",
            "min_abs_pos_composite": _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE,
            "abs_pos_composite": abs(float(pos_composite)),
            "bb44_zone": zones.bb44_zone,
            "bb44_side": bb44_side,
            "expected_bb44_side": expected_bb44_side,
        }

    abs_pos_composite = abs(float(pos_composite))
    if abs_pos_composite >= _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE:
        return alignment_label, {
            "downgraded": False,
            "reason": "weak_alignment_kept_by_composite",
            "min_abs_pos_composite": _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE,
            "abs_pos_composite": abs_pos_composite,
        }

    return "", {
        "downgraded": True,
        "reason": "weak_alignment_downgraded_to_bias_or_unresolved",
        "min_abs_pos_composite": _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE,
        "abs_pos_composite": abs_pos_composite,
    }


def _detect_conflict_kind(zones: PositionZones) -> str:
    box_side = _zone_side(zones.box_zone)
    bb20_side = _zone_side(zones.bb20_zone)
    bb44_side = _zone_side(zones.bb44_zone)
    if box_side == "UPPER" and bb20_side == "LOWER":
        return "CONFLICT_BOX_UPPER_BB20_LOWER"
    if box_side == "LOWER" and bb20_side == "UPPER":
        return "CONFLICT_BOX_LOWER_BB20_UPPER"
    if bb20_side == "UPPER" and bb44_side == "LOWER":
        return "CONFLICT_BB20_UPPER_BB44_LOWER"
    if bb20_side == "LOWER" and bb44_side == "UPPER":
        return "CONFLICT_BB20_LOWER_BB44_UPPER"
    active_sides = {_zone_side(zone) for zone in (zones.box_zone, zones.bb20_zone, zones.bb44_zone)}
    if "UPPER" in active_sides and "LOWER" in active_sides:
        return "CONFLICT_MIDDLE_MIXED"
    return ""


def _primary_side_votes(zones: PositionZones) -> dict[str, int]:
    sides = (
        _zone_side(zones.box_zone),
        _zone_side(zones.bb20_zone),
        _zone_side(zones.bb44_zone),
    )
    return {
        "UPPER": sum(1 for side in sides if side == "UPPER"),
        "LOWER": sum(1 for side in sides if side == "LOWER"),
        "MIDDLE": sum(1 for side in sides if side == "MIDDLE"),
    }


def _detect_bias_label(zones: PositionZones) -> str:
    box_side = _zone_side(zones.box_zone)
    bb20_side = _zone_side(zones.bb20_zone)
    bb44_side = _zone_side(zones.bb44_zone)
    if box_side == "MIDDLE" and bb20_side == "UPPER" and bb44_side == "UPPER":
        return "MIDDLE_UPPER_BIAS"
    if box_side == "MIDDLE" and bb20_side == "LOWER" and bb44_side == "LOWER":
        return "MIDDLE_LOWER_BIAS"

    side_votes = _primary_side_votes(zones)
    if side_votes["UPPER"] >= 2 and side_votes["LOWER"] == 0:
        return "UPPER_BIAS"
    if side_votes["LOWER"] >= 2 and side_votes["UPPER"] == 0:
        return "LOWER_BIAS"
    return ""


def _conflict_axes(conflict_kind: str) -> tuple[str, ...]:
    mapping = {
        "CONFLICT_BOX_UPPER_BB20_LOWER": ("x_box", "x_bb20"),
        "CONFLICT_BOX_LOWER_BB20_UPPER": ("x_box", "x_bb20"),
        "CONFLICT_BB20_UPPER_BB44_LOWER": ("x_bb20", "x_bb44"),
        "CONFLICT_BB20_LOWER_BB44_UPPER": ("x_bb20", "x_bb44"),
        "CONFLICT_MIDDLE_MIXED": POSITION_PRIMARY_AXES,
    }
    return mapping.get(conflict_kind, tuple())


def _dominance_from_composite(pos_composite: float, conflict_kind: str, zones: PositionZones, x_bb44: float) -> str:
    if not conflict_kind:
        return ""
    if x_bb44 >= 0.10:
        return "UPPER_DOMINANT_CONFLICT"
    if x_bb44 <= -0.10:
        return "LOWER_DOMINANT_CONFLICT"
    bb44_side = _zone_side(zones.bb44_zone)
    if bb44_side == "UPPER":
        return "UPPER_DOMINANT_CONFLICT"
    if bb44_side == "LOWER":
        return "LOWER_DOMINANT_CONFLICT"
    if pos_composite >= 0.12:
        return "UPPER_DOMINANT_CONFLICT"
    if pos_composite <= -0.12:
        return "LOWER_DOMINANT_CONFLICT"
    return "BALANCED_CONFLICT"


def _zone_sources(*, use_raw_fallback: bool) -> dict[str, str]:
    sources = {
        "x_box": "RAW_FALLBACK" if use_raw_fallback else "COORD",
        "x_bb20": "RAW_FALLBACK" if use_raw_fallback else "COORD",
        "x_bb44": "COORD",
    }
    for axis_name in POSITION_SECONDARY_AXES:
        sources[axis_name] = "COORD"
    return sources


def _secondary_zone_map(zones: PositionZones) -> dict[str, str]:
    return {axis_name: getattr(zones, field_name) for axis_name, field_name in _SECONDARY_ZONE_FIELDS.items()}


def _secondary_zone_signature(zones: PositionZones) -> str:
    return "|".join(_secondary_zone_map(zones).values())


def _detect_secondary_context_label(zones: PositionZones) -> str:
    sides = {_zone_side(zone) for zone in _secondary_zone_map(zones).values()}
    if "UPPER" in sides and "LOWER" in sides:
        return "MIXED_CONTEXT"
    if "UPPER" in sides:
        return "UPPER_CONTEXT"
    if "LOWER" in sides:
        return "LOWER_CONTEXT"
    return "NEUTRAL_CONTEXT"


def _primary_force_components(x_box: float, x_bb20: float, x_bb44: float) -> tuple[dict[str, float], dict[str, float]]:
    upper_components = {
        "x_box": max(x_box, 0.0) * _POSITION_AXIS_WEIGHTS["box"],
        "x_bb20": max(x_bb20, 0.0) * _POSITION_AXIS_WEIGHTS["bb20"],
        "x_bb44": max(x_bb44, 0.0) * _POSITION_AXIS_WEIGHTS["bb44"],
    }
    lower_components = {
        "x_box": max(-x_box, 0.0) * _POSITION_AXIS_WEIGHTS["box"],
        "x_bb20": max(-x_bb20, 0.0) * _POSITION_AXIS_WEIGHTS["bb20"],
        "x_bb44": max(-x_bb44, 0.0) * _POSITION_AXIS_WEIGHTS["bb44"],
    }
    return upper_components, lower_components


def _secondary_force_summary(secondary_axis_payload: dict[str, float]) -> tuple[dict[str, float], dict[str, float], float, float]:
    secondary_upper_components = {
        axis_name: min(max(float(value), 0.0), 1.0) / max(1, len(secondary_axis_payload))
        for axis_name, value in secondary_axis_payload.items()
    }
    secondary_lower_components = {
        axis_name: min(max(-float(value), 0.0), 1.0) / max(1, len(secondary_axis_payload))
        for axis_name, value in secondary_axis_payload.items()
    }
    return (
        secondary_upper_components,
        secondary_lower_components,
        sum(secondary_upper_components.values()),
        sum(secondary_lower_components.values()),
    )


def _position_dominance_label(
    upper_position_force: float,
    lower_position_force: float,
    middle_neutrality: float,
    position_conflict_score: float,
) -> str:
    if middle_neutrality >= 0.80:
        return "NEUTRAL"
    if position_conflict_score >= 0.80 and abs(upper_position_force - lower_position_force) <= 0.05:
        return "BALANCED_CONFLICT"
    if upper_position_force > lower_position_force:
        return "UPPER"
    if lower_position_force > upper_position_force:
        return "LOWER"
    return "BALANCED"


def build_position_zones(
    position: PositionVector,
    raw_box_state: str | None = None,
    raw_bb_state: str | None = None,
) -> PositionZones:
    x_box = _get_position_value(position, "x_box")
    x_bb20 = _get_position_value(position, "x_bb20")
    x_bb44 = _get_position_value(position, "x_bb44")
    raw_fallback = _raw_fallback_status(x_box, x_bb20, x_bb44)
    use_raw_fallback = bool(raw_fallback["eligible"])
    box_zone = _zone_from_axis_coord("x_box", x_box)
    bb20_zone = _zone_from_axis_coord("x_bb20", x_bb20)
    bb44_zone = _zone_from_axis_coord("x_bb44", x_bb44)
    secondary_zone_map = {
        axis_name: _zone_from_axis_coord(axis_name, _get_position_value(position, axis_name))
        for axis_name in POSITION_SECONDARY_AXES
    }

    if use_raw_fallback:
        resolved_box_state, resolved_bb_state = _resolve_raw_states(position, raw_box_state, raw_bb_state)
        box_zone = _normalize_raw_zone(resolved_box_state, box_zone)
        bb20_zone = _normalize_raw_zone(resolved_bb_state, bb20_zone)

    return PositionZones(
        box_zone=box_zone,
        bb20_zone=bb20_zone,
        bb44_zone=bb44_zone,
        ma20_zone=secondary_zone_map["x_ma20"],
        ma60_zone=secondary_zone_map["x_ma60"],
        sr_zone=secondary_zone_map["x_sr"],
        trendline_zone=secondary_zone_map["x_trendline"],
        metadata={
            "zone_version": _POSITION_ZONE_VERSION,
            "zone_specs": {axis: _zone_spec(axis) for axis in POSITION_PRIMARY_AXES + POSITION_SECONDARY_AXES},
            "zone_sources": _zone_sources(use_raw_fallback=use_raw_fallback),
            "used_raw_fallback": {
                "x_box": bool(use_raw_fallback),
                "x_bb20": bool(use_raw_fallback),
                "x_bb44": False,
                "x_ma20": False,
                "x_ma60": False,
                "x_sr": False,
                "x_trendline": False,
            },
            "raw_fallback_window": raw_fallback["window"],
            "raw_fallback_eligible": bool(raw_fallback["eligible"]),
            "raw_fallback_ambiguity": dict(raw_fallback["ambiguity"]),
            "zone_labels": list(POSITION_ZONE_LABELS),
            "primary_zone_signature": "|".join((box_zone, bb20_zone, bb44_zone)),
            "secondary_zones": dict(secondary_zone_map),
            "secondary_zone_signature": "|".join(secondary_zone_map[axis] for axis in POSITION_SECONDARY_AXES),
        },
    )


def build_position_interpretation(
    position: PositionVector,
    zones: PositionZones | None = None,
    raw_box_state: str | None = None,
    raw_bb_state: str | None = None,
) -> PositionInterpretation:
    x_box = _get_position_value(position, "x_box")
    x_bb20 = _get_position_value(position, "x_bb20")
    x_bb44 = _get_position_value(position, "x_bb44")
    resolved_zones = zones or build_position_zones(
        position=position,
        raw_box_state=raw_box_state,
        raw_bb_state=raw_bb_state,
    )
    resolved_box_state, resolved_bb_state = _resolve_raw_states(position, raw_box_state, raw_bb_state)
    raw_fallback = _raw_fallback_status(x_box, x_bb20, x_bb44)
    used_raw_fallback = bool(raw_fallback["eligible"])
    secondary_zone_map = _secondary_zone_map(resolved_zones)
    secondary_context_label = _detect_secondary_context_label(resolved_zones)
    secondary_axis_payload = _axis_payload(position, POSITION_SECONDARY_AXES)
    secondary_axis_values = tuple(float(value) for value in secondary_axis_payload.values())
    secondary_composite = sum(secondary_axis_values) / max(1, len(secondary_axis_values))
    mtf_ma_summary = _weighted_mtf_ma_summary(position)
    mtf_trendline_summary = _weighted_mtf_trendline_summary(position)
    mtf_context_summary = {
        "version": "mtf_context_weight_profile_v1",
        "lower_support_force": (0.60 * float(mtf_ma_summary["lower_support_force"])) + (0.40 * float(mtf_trendline_summary["lower_support_force"])),
        "upper_resistance_force": (0.60 * float(mtf_ma_summary["upper_resistance_force"])) + (0.40 * float(mtf_trendline_summary["upper_resistance_force"])),
    }
    mtf_context_summary["bias"] = float(mtf_context_summary["lower_support_force"] - mtf_context_summary["upper_resistance_force"])
    mtf_context_summary["owner"] = "STATE_CANDIDATE"
    pos_composite = (
        _POSITION_AXIS_WEIGHTS["box"] * x_box
        + _POSITION_AXIS_WEIGHTS["bb20"] * x_bb20
        + _POSITION_AXIS_WEIGHTS["bb44"] * x_bb44
    )
    raw_alignment_label = _detect_aligned_label(resolved_zones)
    alignment_label, alignment_softening = _soften_alignment_label(raw_alignment_label, pos_composite, resolved_zones)
    conflict_kind = _detect_conflict_kind(resolved_zones)
    bias_label = "" if alignment_label or conflict_kind else _detect_bias_label(resolved_zones)
    primary_side_votes = _primary_side_votes(resolved_zones)
    dominance_label = _dominance_from_composite(pos_composite, conflict_kind, resolved_zones, x_bb44)
    primary_label = alignment_label or conflict_kind or bias_label or "UNRESOLVED_POSITION"

    return PositionInterpretation(
        primary_label=primary_label,
        alignment_label=alignment_label,
        bias_label=bias_label,
        conflict_kind=conflict_kind,
        dominance_label=dominance_label,
        secondary_context_label=secondary_context_label,
        pos_composite=pos_composite,
        used_raw_fallback=used_raw_fallback,
        metadata={
            "zone_version": resolved_zones.metadata.get("zone_version", _POSITION_ZONE_VERSION),
            "zone_specs": dict(resolved_zones.metadata.get("zone_specs", {})),
            "zone_sources": dict(resolved_zones.metadata.get("zone_sources", {})),
            "raw_fallback_window": raw_fallback["window"],
            "raw_fallback_eligible": bool(raw_fallback["eligible"]),
            "raw_fallback_ambiguity": dict(raw_fallback["ambiguity"]),
            "zone_signature": "|".join((resolved_zones.box_zone, resolved_zones.bb20_zone, resolved_zones.bb44_zone)),
            "primary_axes": _axis_payload(position, POSITION_PRIMARY_AXES),
            "secondary_axes": secondary_axis_payload,
            "secondary_zones": secondary_zone_map,
            "secondary_zone_signature": _secondary_zone_signature(resolved_zones),
            "secondary_context_label": secondary_context_label,
            "secondary_context_composite": secondary_composite,
            "mtf_ma_weight_profile_v1": mtf_ma_summary,
            "mtf_trendline_weight_profile_v1": mtf_trendline_summary,
            "mtf_context_weight_profile_v1": mtf_context_summary,
            "conflict_axes": list(_conflict_axes(conflict_kind)),
            "primary_side_votes": dict(primary_side_votes),
            "bias_label": bias_label,
            "raw_alignment_label": raw_alignment_label,
            "alignment_softening": alignment_softening,
            "weak_alignment_min_abs_pos_composite": _POSITION_WEAK_ALIGNMENT_MIN_COMPOSITE,
            "label_contract": {
                "primary_labels": list(POSITION_PRIMARY_LABELS),
                "alignment_labels": list(POSITION_ALIGNMENT_LABELS),
                "bias_labels": list(POSITION_BIAS_LABELS),
                "conflict_labels": list(POSITION_CONFLICT_LABELS),
                "dominance_labels": list(POSITION_DOMINANCE_LABELS),
                "secondary_context_labels": list(POSITION_SECONDARY_CONTEXT_LABELS),
            },
            "fallback_labels": {
                POSITION_FALLBACK_LABELS[0]: resolved_box_state,
                POSITION_FALLBACK_LABELS[1]: resolved_bb_state,
            },
            "position_scale": _position_scale_metadata(position),
            "mtf_ma_big_map_v1": _mtf_ma_big_map_metadata(position),
            "mtf_trendline_map_v1": _mtf_trendline_map_metadata(position),
            "box_zone": resolved_zones.box_zone,
            "bb20_zone": resolved_zones.bb20_zone,
            "bb44_zone": resolved_zones.bb44_zone,
            "ma20_zone": resolved_zones.ma20_zone,
            "ma60_zone": resolved_zones.ma60_zone,
            "sr_zone": resolved_zones.sr_zone,
            "trendline_zone": resolved_zones.trendline_zone,
        },
    )


def build_position_energy_snapshot(position: PositionVector) -> PositionEnergySnapshot:
    x_box = _get_position_value(position, "x_box")
    x_bb20 = _get_position_value(position, "x_bb20")
    x_bb44 = _get_position_value(position, "x_bb44")
    secondary_axis_payload = _axis_payload(position, POSITION_SECONDARY_AXES)
    mtf_ma_summary = _weighted_mtf_ma_summary(position)
    mtf_trendline_summary = _weighted_mtf_trendline_summary(position)
    primary_upper_components, primary_lower_components = _primary_force_components(x_box, x_bb20, x_bb44)
    mtf_upper_force = (0.60 * float(mtf_ma_summary["upper_resistance_force"])) + (0.40 * float(mtf_trendline_summary["upper_resistance_force"]))
    mtf_lower_force = (0.60 * float(mtf_ma_summary["lower_support_force"])) + (0.40 * float(mtf_trendline_summary["lower_support_force"]))
    upper_position_force = sum(primary_upper_components.values())
    lower_position_force = sum(primary_lower_components.values())
    weighted_distance_to_middle = (
        min(abs(x_box), 1.0) * _POSITION_AXIS_WEIGHTS["box"]
        + min(abs(x_bb20), 1.0) * _POSITION_AXIS_WEIGHTS["bb20"]
        + min(abs(x_bb44), 1.0) * _POSITION_AXIS_WEIGHTS["bb44"]
    )
    middle_neutrality = max(0.0, 1.0 - min(1.0, weighted_distance_to_middle / _MIDDLE_NEUTRALITY_SCALE))

    positive_conflict_pressure = (
        min(max(x_box, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["box"]
        + min(max(x_bb20, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["bb20"]
        + min(max(x_bb44, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["bb44"]
    )
    negative_conflict_pressure = (
        min(max(-x_box, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["box"]
        + min(max(-x_bb20, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["bb20"]
        + min(max(-x_bb44, 0.0), 1.0) * _POSITION_AXIS_WEIGHTS["bb44"]
    )
    has_upper_axis = any(value >= _CONFLICT_AXIS_THRESHOLD for value in (x_box, x_bb20, x_bb44))
    has_lower_axis = any(value <= -_CONFLICT_AXIS_THRESHOLD for value in (x_box, x_bb20, x_bb44))
    if has_upper_axis and has_lower_axis:
        position_conflict_score = min(positive_conflict_pressure, negative_conflict_pressure) / max(
            positive_conflict_pressure,
            negative_conflict_pressure,
            1e-9,
        )
    else:
        position_conflict_score = 0.0

    (
        secondary_upper_components,
        secondary_lower_components,
        secondary_upper_force,
        secondary_lower_force,
    ) = _secondary_force_summary(secondary_axis_payload)
    position_force_balance = upper_position_force - lower_position_force
    dominance_label = _position_dominance_label(
        upper_position_force=upper_position_force,
        lower_position_force=lower_position_force,
        middle_neutrality=middle_neutrality,
        position_conflict_score=position_conflict_score,
    )

    return PositionEnergySnapshot(
        upper_position_force=upper_position_force,
        lower_position_force=lower_position_force,
        middle_neutrality=middle_neutrality,
        position_conflict_score=max(0.0, min(1.0, position_conflict_score)),
        metadata={
            "energy_version": _POSITION_ENERGY_VERSION,
            "position_force_balance": position_force_balance,
            "position_dominance": dominance_label,
            "weights": dict(_POSITION_AXIS_WEIGHTS),
            "primary_axes": _axis_payload(position, POSITION_PRIMARY_AXES),
            "primary_upper_components": primary_upper_components,
            "primary_lower_components": primary_lower_components,
            "secondary_axes": secondary_axis_payload,
            "secondary_upper_components": secondary_upper_components,
            "secondary_lower_components": secondary_lower_components,
            "secondary_upper_force": secondary_upper_force,
            "secondary_lower_force": secondary_lower_force,
            "secondary_context_balance": secondary_upper_force - secondary_lower_force,
            "mtf_ma_weight_profile_v1": mtf_ma_summary,
            "mtf_trendline_weight_profile_v1": mtf_trendline_summary,
            "mtf_upper_force": float(mtf_upper_force),
            "mtf_lower_force": float(mtf_lower_force),
            "mtf_force_blend": 0.0,
            "mtf_force_owner": "STATE_CANDIDATE",
            "middle_reference_scale": _MIDDLE_NEUTRALITY_SCALE,
            "conflict_axis_threshold": _CONFLICT_AXIS_THRESHOLD,
            "primary_only_outputs": True,
            "weighted_distance_to_middle": weighted_distance_to_middle,
            "position_scale": _position_scale_metadata(position),
            "mtf_ma_big_map_v1": _mtf_ma_big_map_metadata(position),
            "mtf_trendline_map_v1": _mtf_trendline_map_metadata(position),
        },
    )


def summarize_position(
    position: PositionVector,
    raw_box_state: str | None = None,
    raw_bb_state: str | None = None,
) -> PositionSnapshot:
    zones = build_position_zones(
        position=position,
        raw_box_state=raw_box_state,
        raw_bb_state=raw_bb_state,
    )
    interpretation = build_position_interpretation(
        position=position,
        zones=zones,
        raw_box_state=raw_box_state,
        raw_bb_state=raw_bb_state,
    )
    energy = build_position_energy_snapshot(position)
    return PositionSnapshot(
        vector=position,
        zones=zones,
        interpretation=interpretation,
        energy=energy,
    )


__all__ = [
    "build_position_energy_snapshot",
    "build_position_interpretation",
    "build_position_zones",
    "summarize_position",
]
