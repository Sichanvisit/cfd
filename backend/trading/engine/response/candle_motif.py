from __future__ import annotations

from typing import Any

_MOTIF_VERSION = "candle_motif_v1"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _soft_clip01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    return float(value) / (1.0 + float(value))


def _score_map(patterns: dict[str, Any], group_key: str) -> dict[str, float]:
    group = dict(patterns.get(group_key, {}) or {})
    return {str(name): _to_float(value) for name, value in group.items()}


def _merge(
    primary: dict[str, float],
    *,
    support: dict[str, float] | None = None,
    amplifier: dict[str, float] | None = None,
    penalty: dict[str, float] | None = None,
) -> tuple[float, dict[str, Any]]:
    primary = dict(primary or {})
    support = dict(support or {})
    amplifier = dict(amplifier or {})
    penalty = dict(penalty or {})

    dominant_name = ""
    dominant_value = 0.0
    if primary:
        dominant_name, dominant_value = max(primary.items(), key=lambda item: float(item[1]))
    remaining_primary = sum(value for name, value in primary.items() if name != dominant_name)
    primary_support = min(remaining_primary * 0.14, 0.18)
    support_bonus = min(sum(support.values()) * 0.10, 0.12)
    amplifier_bonus = min(sum(amplifier.values()) * 0.08, 0.10)
    penalty_total = min(sum(penalty.values()) * 0.20, 0.30)
    score = _clamp01(dominant_value + primary_support + support_bonus + amplifier_bonus - penalty_total)
    return score, {
        "dominant_source": dominant_name,
        "dominant_value": dominant_value,
        "primary_support": primary_support,
        "support_bonus": support_bonus,
        "amplifier_bonus": amplifier_bonus,
        "penalty_total": penalty_total,
        "primary_sources": list(primary.keys()),
        "support_sources": list(support.keys()),
        "amplifier_sources": list(amplifier.keys()),
        "penalty_sources": list(penalty.keys()),
    }


def compute_candle_motifs(
    descriptor: dict[str, Any] | None,
    patterns: dict[str, Any] | None,
) -> dict[str, Any]:
    descriptor = dict(descriptor or {})
    patterns = dict(patterns or {})
    single = _score_map(patterns, "single_candle_patterns_v1")
    two_bar = _score_map(patterns, "two_bar_patterns_v1")
    three_bar = _score_map(patterns, "three_bar_patterns_v1")

    indecision, indecision_debug = _merge(
        {
            "doji_like": single.get("doji_like", 0.0),
            "long_legged_doji_like": single.get("long_legged_doji_like", 0.0),
            "spinning_top_like": single.get("spinning_top_like", 0.0),
            "harami_like": two_bar.get("harami_like", 0.0),
            "harami_cross_like": two_bar.get("harami_cross_like", 0.0),
        }
    )

    bull_reject, bull_reject_debug = _merge(
        {
            "hammer_like": single.get("hammer_like", 0.0),
            "dragonfly_doji_like": single.get("dragonfly_doji_like", 0.0),
            "tweezer_bottom_like": two_bar.get("tweezer_bottom_like", 0.0),
        },
        support={
            "inverted_hammer_like": single.get("inverted_hammer_like", 0.0),
        },
        amplifier={
            "bullish_engulfing_like": two_bar.get("bullish_engulfing_like", 0.0),
            "morning_star_like": three_bar.get("morning_star_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bearish_marubozu_like": single.get("bearish_marubozu_like", 0.0),
            "three_black_crows_like": three_bar.get("three_black_crows_like", 0.0),
        },
    )

    bear_reject, bear_reject_debug = _merge(
        {
            "shooting_star_like": single.get("shooting_star_like", 0.0),
            "gravestone_doji_like": single.get("gravestone_doji_like", 0.0),
            "tweezer_top_like": two_bar.get("tweezer_top_like", 0.0),
            "hanging_man_like": single.get("hanging_man_like", 0.0),
        },
        support={},
        amplifier={
            "bearish_engulfing_like": two_bar.get("bearish_engulfing_like", 0.0),
            "evening_star_like": three_bar.get("evening_star_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bullish_marubozu_like": single.get("bullish_marubozu_like", 0.0),
            "three_white_soldiers_like": three_bar.get("three_white_soldiers_like", 0.0),
        },
    )

    bull_reversal_2bar, bull_reversal_2bar_debug = _merge(
        {
            "bullish_engulfing_like": two_bar.get("bullish_engulfing_like", 0.0),
            "tweezer_bottom_like": two_bar.get("tweezer_bottom_like", 0.0),
        },
        support={
            "harami_like": two_bar.get("harami_like", 0.0),
            "harami_cross_like": two_bar.get("harami_cross_like", 0.0),
        },
        amplifier={
            "hammer_like": single.get("hammer_like", 0.0),
            "dragonfly_doji_like": single.get("dragonfly_doji_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bearish_engulfing_like": two_bar.get("bearish_engulfing_like", 0.0),
            "bear_break_body": single.get("bearish_marubozu_like", 0.0),
        },
    )

    bear_reversal_2bar, bear_reversal_2bar_debug = _merge(
        {
            "bearish_engulfing_like": two_bar.get("bearish_engulfing_like", 0.0),
            "tweezer_top_like": two_bar.get("tweezer_top_like", 0.0),
        },
        support={
            "harami_like": two_bar.get("harami_like", 0.0),
            "harami_cross_like": two_bar.get("harami_cross_like", 0.0),
        },
        amplifier={
            "shooting_star_like": single.get("shooting_star_like", 0.0),
            "gravestone_doji_like": single.get("gravestone_doji_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bullish_engulfing_like": two_bar.get("bullish_engulfing_like", 0.0),
            "bull_break_body": single.get("bullish_marubozu_like", 0.0),
        },
    )

    bull_reversal_3bar, bull_reversal_3bar_debug = _merge(
        {
            "morning_star_like": three_bar.get("morning_star_like", 0.0),
        },
        support={
            "three_white_soldiers_like": three_bar.get("three_white_soldiers_like", 0.0),
        },
        amplifier={
            "bullish_engulfing_like": two_bar.get("bullish_engulfing_like", 0.0),
            "hammer_like": single.get("hammer_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "evening_star_like": three_bar.get("evening_star_like", 0.0),
        },
    )

    bear_reversal_3bar, bear_reversal_3bar_debug = _merge(
        {
            "evening_star_like": three_bar.get("evening_star_like", 0.0),
        },
        support={
            "three_black_crows_like": three_bar.get("three_black_crows_like", 0.0),
        },
        amplifier={
            "bearish_engulfing_like": two_bar.get("bearish_engulfing_like", 0.0),
            "shooting_star_like": single.get("shooting_star_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "morning_star_like": three_bar.get("morning_star_like", 0.0),
        },
    )

    bull_break_body, bull_break_body_debug = _merge(
        {
            "bullish_marubozu_like": single.get("bullish_marubozu_like", 0.0),
            "three_white_soldiers_like": three_bar.get("three_white_soldiers_like", 0.0),
        },
        support={
            "bullish_engulfing_like": two_bar.get("bullish_engulfing_like", 0.0),
            "inverted_hammer_like": single.get("inverted_hammer_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bear_reject": bear_reject,
            "bearish_marubozu_like": single.get("bearish_marubozu_like", 0.0),
        },
    )

    bear_break_body, bear_break_body_debug = _merge(
        {
            "bearish_marubozu_like": single.get("bearish_marubozu_like", 0.0),
            "three_black_crows_like": three_bar.get("three_black_crows_like", 0.0),
        },
        support={
            "bearish_engulfing_like": two_bar.get("bearish_engulfing_like", 0.0),
            "hanging_man_like": single.get("hanging_man_like", 0.0),
        },
        penalty={
            "indecision": indecision,
            "bull_reject": bull_reject,
            "bullish_marubozu_like": single.get("bullish_marubozu_like", 0.0),
        },
    )

    size_energy = _soft_clip01(max(_to_float(descriptor.get("range_size_energy")) - 1.0, 0.0))
    rejection_energy = max(bull_reject, bear_reject)
    break_energy = max(bull_break_body, bear_break_body)
    climax = _clamp01(
        (0.45 * size_energy)
        + (0.30 * max(rejection_energy, break_energy))
        + (0.25 * indecision)
    )

    scores = {
        "bull_reject": bull_reject,
        "bear_reject": bear_reject,
        "bull_reversal_2bar": bull_reversal_2bar,
        "bear_reversal_2bar": bear_reversal_2bar,
        "bull_reversal_3bar": bull_reversal_3bar,
        "bear_reversal_3bar": bear_reversal_3bar,
        "bull_break_body": bull_break_body,
        "bear_break_body": bear_break_body,
        "indecision": indecision,
        "climax": climax,
    }
    fired = [name for name, value in scores.items() if _to_float(value) >= 0.55]
    return {
        "version": _MOTIF_VERSION,
        **scores,
        "fired_motifs": fired,
        "merge_mode": "dominant_support_penalty_v1",
        "merge_debug": {
            "bull_reject": bull_reject_debug,
            "bear_reject": bear_reject_debug,
            "bull_reversal_2bar": bull_reversal_2bar_debug,
            "bear_reversal_2bar": bear_reversal_2bar_debug,
            "bull_reversal_3bar": bull_reversal_3bar_debug,
            "bear_reversal_3bar": bear_reversal_3bar_debug,
            "bull_break_body": bull_break_body_debug,
            "bear_break_body": bear_break_body_debug,
            "indecision": indecision_debug,
        },
    }
