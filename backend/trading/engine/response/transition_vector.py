from __future__ import annotations

from backend.trading.engine.core.models import ResponseRawSnapshot, ResponseVectorV2

_PRIMARY_SUPPORT_WEIGHT = 0.20
_PRIMARY_SUPPORT_CAP = 0.20
_CONFIRMATION_SUPPORT_WEIGHT = 0.12
_CONFIRMATION_SUPPORT_CAP = 0.12
_CONFIRMATION_ONLY_SCALE = 0.82
_AMPLIFIER_SUPPORT_WEIGHT = 0.10
_AMPLIFIER_SUPPORT_CAP = 0.10
_CONTEXT_CANDIDATE_WEIGHT = 1.0
_LEGACY_FALLBACK_WEIGHT = 0.0

_AXIS_CANDIDATE_KEYS = {
    "lower_hold_up": "lower_hold_candidate",
    "lower_break_down": "lower_break_candidate",
    "mid_reclaim_up": "mid_reclaim_candidate",
    "mid_lose_down": "mid_lose_candidate",
    "upper_reject_down": "upper_reject_candidate",
    "upper_break_up": "upper_break_candidate",
}

_AXIS_SPECS = {
    "lower_hold_up": {
        "primary_sources": ("bb20_lower_hold", "box_lower_bounce"),
        "confirmation_sources": ("bb44_lower_hold", "candle_lower_reject"),
        "amplifier_sources": ("pattern_double_bottom", "pattern_inverse_head_shoulders"),
    },
    "lower_break_down": {
        "primary_sources": ("bb20_lower_break", "box_lower_break"),
        "confirmation_sources": tuple(),
        "amplifier_sources": tuple(),
    },
    "mid_reclaim_up": {
        "primary_sources": ("bb20_mid_hold", "bb20_mid_reclaim", "box_mid_hold"),
        "confirmation_sources": tuple(),
        "amplifier_sources": ("pattern_inverse_head_shoulders",),
    },
    "mid_lose_down": {
        "primary_sources": ("bb20_mid_reject", "bb20_mid_lose", "box_mid_reject"),
        "confirmation_sources": tuple(),
        "amplifier_sources": ("pattern_head_shoulders",),
    },
    "upper_reject_down": {
        "primary_sources": ("bb20_upper_reject", "box_upper_reject"),
        "confirmation_sources": ("bb44_upper_reject", "candle_upper_reject"),
        "amplifier_sources": ("pattern_double_top", "pattern_head_shoulders"),
    },
    "upper_break_up": {
        "primary_sources": ("bb20_upper_break", "box_upper_break"),
        "confirmation_sources": tuple(),
        "amplifier_sources": tuple(),
    },
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _read_context_gate_candidates(raw: ResponseRawSnapshot) -> dict[str, float]:
    metadata = dict(raw.metadata or {})
    gate = dict(metadata.get("response_context_gate_v1") or {})
    candidates = dict(gate.get("pre_axis_candidates") or {})
    return {str(name): _clamp01(value) for name, value in candidates.items()}


def _has_context_gate(raw: ResponseRawSnapshot) -> bool:
    metadata = dict(raw.metadata or {})
    gate = metadata.get("response_context_gate_v1")
    return isinstance(gate, dict)


def _read_scores(raw: ResponseRawSnapshot, source_names: tuple[str, ...]) -> dict[str, float]:
    return {name: _clamp01(getattr(raw, name, 0.0)) for name in source_names}


def _top_source(scores: dict[str, float]) -> tuple[str, float]:
    if not scores:
        return "", 0.0
    name = max(scores, key=scores.get)
    return name, float(scores[name])


def _sum_without(scores: dict[str, float], excluded_name: str) -> float:
    return sum(float(value) for name, value in scores.items() if name != excluded_name)


def _resolve_axis(raw: ResponseRawSnapshot, axis_name: str, spec: dict[str, tuple[str, ...]]) -> tuple[float, dict[str, object]]:
    primary_scores = _read_scores(raw, spec["primary_sources"])
    confirmation_scores = _read_scores(raw, spec["confirmation_sources"])
    amplifier_scores = _read_scores(raw, spec["amplifier_sources"])
    dominant_primary_name, dominant_primary_score = _top_source(primary_scores)
    dominant_confirmation_name, dominant_confirmation_score = _top_source(confirmation_scores)
    dominant_amplifier_name, dominant_amplifier_score = _top_source(amplifier_scores)

    if dominant_primary_score > 0.0:
        dominant_source = dominant_primary_name
        dominant_role = "primary"
        base_value = dominant_primary_score
        primary_support = min(
            _sum_without(primary_scores, dominant_primary_name) * _PRIMARY_SUPPORT_WEIGHT,
            _PRIMARY_SUPPORT_CAP,
        )
        confirmation_support = min(
            sum(confirmation_scores.values()) * _CONFIRMATION_SUPPORT_WEIGHT,
            _CONFIRMATION_SUPPORT_CAP,
        )
        amplifier_support = min(
            sum(amplifier_scores.values()) * _AMPLIFIER_SUPPORT_WEIGHT,
            _AMPLIFIER_SUPPORT_CAP,
        )
    elif dominant_confirmation_score > 0.0:
        dominant_source = dominant_confirmation_name
        dominant_role = "confirmation"
        base_value = dominant_confirmation_score * _CONFIRMATION_ONLY_SCALE
        primary_support = 0.0
        confirmation_support = min(
            _sum_without(confirmation_scores, dominant_confirmation_name) * _CONFIRMATION_SUPPORT_WEIGHT,
            _CONFIRMATION_SUPPORT_CAP,
        )
        amplifier_support = min(
            sum(amplifier_scores.values()) * _AMPLIFIER_SUPPORT_WEIGHT,
            _AMPLIFIER_SUPPORT_CAP,
        )
    else:
        dominant_source = ""
        dominant_role = "none"
        base_value = 0.0
        primary_support = 0.0
        confirmation_support = 0.0
        amplifier_support = 0.0

    resolved_value = _clamp01(base_value + primary_support + confirmation_support + amplifier_support)
    return resolved_value, {
        "axis": axis_name,
        "primary_sources": list(spec["primary_sources"]),
        "confirmation_sources": list(spec["confirmation_sources"]),
        "amplifier_sources": list(spec["amplifier_sources"]),
        "primary_scores": primary_scores,
        "confirmation_scores": confirmation_scores,
        "amplifier_scores": amplifier_scores,
        "dominant_source": dominant_source,
        "dominant_role": dominant_role,
        "dominant_primary_source": dominant_primary_name,
        "dominant_primary_score": float(dominant_primary_score),
        "dominant_confirmation_source": dominant_confirmation_name,
        "dominant_confirmation_score": float(dominant_confirmation_score),
        "dominant_amplifier_source": dominant_amplifier_name,
        "dominant_amplifier_score": float(dominant_amplifier_score),
        "base_value": float(base_value),
        "primary_support": float(primary_support),
        "confirmation_support": float(confirmation_support),
        "amplifier_support": float(amplifier_support),
        "resolved_value": float(resolved_value),
    }


def build_response_vector_v2(raw: ResponseRawSnapshot) -> ResponseVectorV2:
    legacy_resolved_axes = {
        axis_name: _resolve_axis(raw, axis_name, spec)
        for axis_name, spec in _AXIS_SPECS.items()
    }
    legacy_axis_values = {axis_name: float(result[0]) for axis_name, result in legacy_resolved_axes.items()}
    legacy_axis_debug = {axis_name: result[1] for axis_name, result in legacy_resolved_axes.items()}
    context_candidates = _read_context_gate_candidates(raw)
    context_gate_present = _has_context_gate(raw)

    axis_values: dict[str, float] = {}
    axis_debug: dict[str, dict[str, object]] = {}
    dominant_source_by_axis: dict[str, str] = {}
    dominant_role_by_axis: dict[str, str] = {}

    for axis_name in _AXIS_SPECS.keys():
        candidate_key = _AXIS_CANDIDATE_KEYS[axis_name]
        candidate_value = _clamp01(context_candidates.get(candidate_key, 0.0))
        legacy_value = float(legacy_axis_values[axis_name])
        if context_gate_present:
            resolved_value = float(candidate_value)
            dominant_source = candidate_key if candidate_value > 0.0 else ""
            dominant_role = "gated_candidate" if candidate_value > 0.0 else "gated_zero"
            candidate_weight = float(_CONTEXT_CANDIDATE_WEIGHT)
            legacy_fallback_weight = float(_LEGACY_FALLBACK_WEIGHT)
            used_technical_legacy_fallback = False
        else:
            resolved_value = legacy_value
            dominant_source = str(legacy_axis_debug[axis_name]["dominant_source"])
            dominant_role = str(legacy_axis_debug[axis_name]["dominant_role"])
            candidate_weight = 0.0
            legacy_fallback_weight = 1.0
            used_technical_legacy_fallback = True

        axis_values[axis_name] = float(resolved_value)
        dominant_source_by_axis[axis_name] = dominant_source
        dominant_role_by_axis[axis_name] = dominant_role
        axis_debug[axis_name] = {
            "axis": axis_name,
            "candidate_key": candidate_key,
            "candidate_value": float(candidate_value),
            "legacy_value": float(legacy_value),
            "resolved_value": float(resolved_value),
            "context_gate_present": bool(context_gate_present),
            "used_technical_legacy_fallback": bool(used_technical_legacy_fallback),
            "candidate_weight": float(candidate_weight),
            "legacy_fallback_weight": float(legacy_fallback_weight),
            "dominant_source": dominant_source,
            "dominant_role": dominant_role,
            "legacy_axis_debug": legacy_axis_debug[axis_name],
        }

    return ResponseVectorV2(
        lower_hold_up=axis_values["lower_hold_up"],
        lower_break_down=axis_values["lower_break_down"],
        mid_reclaim_up=axis_values["mid_reclaim_up"],
        mid_lose_down=axis_values["mid_lose_down"],
        upper_reject_down=axis_values["upper_reject_down"],
        upper_break_up=axis_values["upper_break_up"],
        metadata={
            "response_contract": "canonical_v2",
            "raw_snapshot_contract": str((raw.metadata or {}).get("response_contract", "raw_snapshot_v1")),
            "raw_snapshot_version": "raw_snapshot_v1",
            "mapper_version": "response_vector_v2_r5",
            "mapping_mode": "context_gated_candidate_primary_only",
            "semantic_owner_contract": "context_gate_candidate_primary_only_v1",
            "legacy_semantic_blend_enabled": False,
            "primary_source_weight": float(_PRIMARY_SUPPORT_WEIGHT),
            "primary_support_cap": float(_PRIMARY_SUPPORT_CAP),
            "confirmation_source_weight": float(_CONFIRMATION_SUPPORT_WEIGHT),
            "confirmation_support_cap": float(_CONFIRMATION_SUPPORT_CAP),
            "confirmation_only_scale": float(_CONFIRMATION_ONLY_SCALE),
            "amplifier_source_weight": float(_AMPLIFIER_SUPPORT_WEIGHT),
            "amplifier_support_cap": float(_AMPLIFIER_SUPPORT_CAP),
            "context_candidate_weight": float(_CONTEXT_CANDIDATE_WEIGHT),
            "legacy_fallback_weight": float(_LEGACY_FALLBACK_WEIGHT),
            "context_gate_present": bool(context_gate_present),
            "technical_legacy_fallback_on_missing_gate_only": True,
            "axis_sources": {
                axis_name: list(spec["primary_sources"] + spec["confirmation_sources"] + spec["amplifier_sources"])
                for axis_name, spec in _AXIS_SPECS.items()
            },
            "axis_source_roles": {
                axis_name: {
                    "primary_sources": list(spec["primary_sources"]),
                    "confirmation_sources": list(spec["confirmation_sources"]),
                    "amplifier_sources": list(spec["amplifier_sources"]),
                }
                for axis_name, spec in _AXIS_SPECS.items()
            },
            "axis_candidate_keys": dict(_AXIS_CANDIDATE_KEYS),
            "axis_candidate_scores": {
                axis_name: float(context_candidates.get(candidate_key, 0.0))
                for axis_name, candidate_key in _AXIS_CANDIDATE_KEYS.items()
            },
            "dominant_source_by_axis": dominant_source_by_axis,
            "dominant_role_by_axis": dominant_role_by_axis,
            "source_scores_by_axis": {
                axis_name: {
                    **legacy_axis_debug[axis_name]["primary_scores"],
                    **legacy_axis_debug[axis_name]["confirmation_scores"],
                    **legacy_axis_debug[axis_name]["amplifier_scores"],
                }
                for axis_name in legacy_axis_debug.keys()
            },
            "axis_merge_debug": axis_debug,
            "legacy_axis_merge_debug": legacy_axis_debug,
        },
    )
