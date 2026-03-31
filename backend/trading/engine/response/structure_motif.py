from __future__ import annotations

from typing import Any

_STRUCTURE_MOTIF_VERSION = "structure_motif_v1"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _merge(primary: dict[str, float], *, support: dict[str, float] | None = None, penalty: dict[str, float] | None = None) -> tuple[float, dict[str, Any]]:
    primary = dict(primary or {})
    support = dict(support or {})
    penalty = dict(penalty or {})
    dominant_name = ""
    dominant_value = 0.0
    if primary:
        dominant_name, dominant_value = max(primary.items(), key=lambda item: float(item[1]))
    remaining_primary = sum(value for name, value in primary.items() if name != dominant_name)
    primary_support = min(remaining_primary * 0.16, 0.20)
    support_bonus = min(sum(support.values()) * 0.12, 0.14)
    penalty_total = min(sum(penalty.values()) * 0.18, 0.26)
    score = _clamp01(dominant_value + primary_support + support_bonus - penalty_total)
    return score, {
        "dominant_source": dominant_name,
        "dominant_value": dominant_value,
        "primary_support": primary_support,
        "support_bonus": support_bonus,
        "penalty_total": penalty_total,
        "primary_sources": list(primary.keys()),
        "support_sources": list(support.keys()),
        "penalty_sources": list(penalty.keys()),
    }


def compute_structure_motifs(pattern_scores: dict[str, Any] | None) -> dict[str, Any]:
    pattern_scores = dict(pattern_scores or {})
    double_bottom = _to_float(pattern_scores.get("pattern_double_bottom"))
    inverse_head_shoulders = _to_float(pattern_scores.get("pattern_inverse_head_shoulders"))
    double_top = _to_float(pattern_scores.get("pattern_double_top"))
    head_shoulders = _to_float(pattern_scores.get("pattern_head_shoulders"))

    reversal_base_up, reversal_base_up_debug = _merge(
        {
            "pattern_double_bottom": double_bottom,
            "pattern_inverse_head_shoulders": inverse_head_shoulders,
        },
        penalty={
            "pattern_double_top": double_top,
            "pattern_head_shoulders": head_shoulders,
        },
    )
    reversal_top_down, reversal_top_down_debug = _merge(
        {
            "pattern_double_top": double_top,
            "pattern_head_shoulders": head_shoulders,
        },
        penalty={
            "pattern_double_bottom": double_bottom,
            "pattern_inverse_head_shoulders": inverse_head_shoulders,
        },
    )
    support_hold_confirm, support_hold_confirm_debug = _merge(
        {
            "pattern_double_bottom": double_bottom,
        },
        support={
            "pattern_inverse_head_shoulders": inverse_head_shoulders,
        },
        penalty={
            "pattern_double_top": double_top,
        },
    )
    resistance_reject_confirm, resistance_reject_confirm_debug = _merge(
        {
            "pattern_double_top": double_top,
        },
        support={
            "pattern_head_shoulders": head_shoulders,
        },
        penalty={
            "pattern_double_bottom": double_bottom,
        },
    )

    scores = {
        "reversal_base_up": reversal_base_up,
        "reversal_top_down": reversal_top_down,
        "support_hold_confirm": support_hold_confirm,
        "resistance_reject_confirm": resistance_reject_confirm,
    }
    fired = [name for name, value in scores.items() if _to_float(value) >= 0.55]
    return {
        "version": _STRUCTURE_MOTIF_VERSION,
        **scores,
        "fired_motifs": fired,
        "merge_mode": "dominant_support_penalty_v1",
        "merge_debug": {
            "reversal_base_up": reversal_base_up_debug,
            "reversal_top_down": reversal_top_down_debug,
            "support_hold_confirm": support_hold_confirm_debug,
            "resistance_reject_confirm": resistance_reject_confirm_debug,
        },
    }
