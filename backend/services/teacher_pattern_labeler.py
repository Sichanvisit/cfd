"""Rule-based draft labeler for teacher-state 25 compact schema."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from backend.services.teacher_pattern_active_candidate_runtime import (
    normalize_state25_teacher_weight_overrides,
    render_state25_teacher_weight_override_lines_ko,
)


_PATTERN_META = {
    1: {"name": "쉬운 루즈장", "group": "A", "direction_bias": "neutral", "entry_bias": "avoid", "wait_bias": "wait", "exit_bias": "range_take", "transition_risk": "low"},
    2: {"name": "변동성 큰 장", "group": "E", "direction_bias": "both", "entry_bias": "conditional", "wait_bias": "tight_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    3: {"name": "갑자기 발작장", "group": "C", "direction_bias": "both", "entry_bias": "fast_decision", "wait_bias": "short_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    4: {"name": "추세 지속장", "group": "B", "direction_bias": "both", "entry_bias": "confirm", "wait_bias": "hold", "exit_bias": "hold_runner", "transition_risk": "mid"},
    5: {"name": "Range 반전장", "group": "D", "direction_bias": "both", "entry_bias": "fade", "wait_bias": "short_wait", "exit_bias": "range_take", "transition_risk": "mid"},
    6: {"name": "점진적 추세장", "group": "B", "direction_bias": "both", "entry_bias": "early", "wait_bias": "hold", "exit_bias": "trail", "transition_risk": "mid"},
    7: {"name": "변동성 확대장", "group": "C", "direction_bias": "both", "entry_bias": "conditional", "wait_bias": "tight_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    8: {"name": "죽음의 가위장", "group": "E", "direction_bias": "sell_prefer", "entry_bias": "confirm", "wait_bias": "hold", "exit_bias": "trail", "transition_risk": "mid"},
    9: {"name": "황금십자 직전", "group": "E", "direction_bias": "buy_prefer", "entry_bias": "early", "wait_bias": "hold", "exit_bias": "hold_runner", "transition_risk": "mid"},
    10: {"name": "공허한 횡보장", "group": "A", "direction_bias": "neutral", "entry_bias": "avoid", "wait_bias": "wait", "exit_bias": "range_take", "transition_risk": "low"},
    11: {"name": "눌림목 반등장", "group": "D", "direction_bias": "buy_prefer", "entry_bias": "confirm", "wait_bias": "hold", "exit_bias": "trail", "transition_risk": "mid"},
    12: {"name": "브레이크아웃 직전", "group": "C", "direction_bias": "both", "entry_bias": "breakout", "wait_bias": "short_wait", "exit_bias": "hold_runner", "transition_risk": "mid"},
    13: {"name": "변동성 컨트랙션", "group": "A", "direction_bias": "neutral", "entry_bias": "avoid", "wait_bias": "wait", "exit_bias": "range_take", "transition_risk": "low"},
    14: {"name": "모닝 컨솔리데이션", "group": "A", "direction_bias": "both", "entry_bias": "breakout", "wait_bias": "short_wait", "exit_bias": "range_take", "transition_risk": "mid"},
    15: {"name": "캔들 연속 패턴", "group": "B", "direction_bias": "both", "entry_bias": "early", "wait_bias": "hold", "exit_bias": "trail", "transition_risk": "mid"},
    16: {"name": "페이크아웃 반전", "group": "D", "direction_bias": "opposite_to_break", "entry_bias": "fade", "wait_bias": "short_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    17: {"name": "거래량 폭발장", "group": "C", "direction_bias": "both", "entry_bias": "breakout", "wait_bias": "tight_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    18: {"name": "꼬리물림장", "group": "E", "direction_bias": "neutral", "entry_bias": "avoid", "wait_bias": "avoid_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
    19: {"name": "속도감 추세장", "group": "B", "direction_bias": "both", "entry_bias": "breakout", "wait_bias": "hold", "exit_bias": "hold_runner", "transition_risk": "high"},
    20: {"name": "엔진 꺼짐장", "group": "E", "direction_bias": "neutral", "entry_bias": "avoid", "wait_bias": "short_wait", "exit_bias": "scale_out", "transition_risk": "high"},
    21: {"name": "갭필링 진행장", "group": "D", "direction_bias": "fill_direction", "entry_bias": "confirm", "wait_bias": "short_wait", "exit_bias": "range_take", "transition_risk": "mid"},
    22: {"name": "더블탑/바텀", "group": "D", "direction_bias": "reversal_side", "entry_bias": "confirm", "wait_bias": "short_wait", "exit_bias": "fast_cut", "transition_risk": "mid"},
    23: {"name": "삼각수렴 압축", "group": "A", "direction_bias": "both", "entry_bias": "breakout", "wait_bias": "short_wait", "exit_bias": "hold_runner", "transition_risk": "mid"},
    24: {"name": "플래그 패턴장", "group": "B", "direction_bias": "both", "entry_bias": "confirm", "wait_bias": "hold", "exit_bias": "trail", "transition_risk": "mid"},
    25: {"name": "데드캣 바운스", "group": "D", "direction_bias": "sell_prefer", "entry_bias": "fade", "wait_bias": "avoid_wait", "exit_bias": "fast_cut", "transition_risk": "high"},
}

_PATTERN_WEIGHT_FAMILIES = {
    1: ("doji_weight", "volume_burst_weight", "same_color_run_weight", "participation_weight", "wait_state_weight"),
    2: ("volume_burst_weight", "upper_wick_weight", "lower_wick_weight", "participation_weight", "candle_body_weight"),
    3: ("volume_burst_weight", "candle_body_weight", "upper_wick_weight", "lower_wick_weight", "compression_weight"),
    4: ("same_color_run_weight", "directional_bias_weight", "participation_weight", "volume_decay_weight"),
    5: ("swing_retest_weight", "doji_weight", "range_reversal_weight", "reversal_risk_weight", "wait_state_weight"),
    6: ("same_color_run_weight", "directional_bias_weight", "volume_burst_weight", "compression_weight", "setup_keyword_weight"),
    7: ("volume_burst_weight", "participation_weight", "compression_weight", "candle_body_weight"),
    8: ("same_color_run_weight", "directional_bias_weight", "setup_keyword_weight", "participation_weight", "reversal_risk_weight"),
    9: ("same_color_run_weight", "directional_bias_weight", "setup_keyword_weight", "participation_weight", "reversal_risk_weight"),
    10: ("doji_weight", "same_color_run_weight", "directional_bias_weight", "compression_weight"),
    11: ("setup_keyword_weight", "lower_wick_weight", "directional_bias_weight", "prediction_weight"),
    12: ("compression_weight", "volume_burst_weight", "same_color_run_weight", "setup_keyword_weight", "prediction_weight"),
    13: ("compression_weight", "volume_burst_weight", "participation_weight", "candle_body_weight"),
    14: ("compression_weight", "doji_weight", "volume_burst_weight", "setup_keyword_weight"),
    15: ("same_color_run_weight", "volume_burst_weight", "participation_weight"),
    16: ("setup_keyword_weight", "reversal_risk_weight", "upper_wick_weight", "lower_wick_weight", "doji_weight"),
    17: ("volume_burst_weight", "volume_decay_weight", "participation_weight"),
    18: ("upper_wick_weight", "lower_wick_weight", "doji_weight", "directional_bias_weight"),
    19: ("same_color_run_weight", "volume_burst_weight", "volume_decay_weight", "participation_weight"),
    20: ("doji_weight", "volume_decay_weight", "participation_weight", "same_color_run_weight"),
    21: ("gap_context_weight", "same_color_run_weight", "candle_body_weight"),
    22: ("swing_retest_weight", "doji_weight", "setup_keyword_weight", "reversal_risk_weight"),
    23: ("compression_weight", "swing_retest_weight", "prediction_weight"),
    24: ("setup_keyword_weight", "compression_weight", "same_color_run_weight", "prediction_weight"),
    25: ("directional_bias_weight", "upper_wick_weight", "reversal_risk_weight", "setup_keyword_weight", "participation_weight"),
}


def _to_float(value: Any, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float(default)
    return float(parsed)


def _to_int(value: Any, default: int = 0) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return int(default)
    return int(parsed)


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _weight_multiplier(overrides: dict[str, float], key: str) -> float:
    try:
        return float(overrides.get(key, 1.0) or 1.0)
    except Exception:
        return 1.0


def _pattern_score_multiplier(pattern_id: int, overrides: dict[str, float]) -> float:
    families = _PATTERN_WEIGHT_FAMILIES.get(int(pattern_id), ())
    if not families:
        return 1.0
    values = [_weight_multiplier(overrides, family) for family in families]
    if not values:
        return 1.0
    return float(sum(values) / len(values))


def _parse_prediction_bundle(bundle_text: str) -> dict[str, Any]:
    text = _to_text(bundle_text)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _keyword_hit(setup_id: str, *keywords: str) -> bool:
    return any(keyword in setup_id for keyword in keywords)


def build_teacher_pattern_payload_v2(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    snap = dict(snapshot or {})
    explicit_id = _to_int(snap.get("teacher_pattern_id"), 0)
    explicit_name = _to_text(snap.get("teacher_pattern_name"))
    if explicit_id > 0 or explicit_name:
        return {}

    setup_id = _to_text(snap.get("entry_setup_id")).lower()
    session_name = _to_text(snap.get("entry_session_name")).upper()
    direction = _to_text(snap.get("direction")).upper()
    breakout_state = _to_text(snap.get("micro_breakout_readiness_state")).upper()
    reversal_state = _to_text(snap.get("micro_reversal_risk_state")).upper()
    participation_state = _to_text(snap.get("micro_participation_state")).upper()
    gap_state = _to_text(snap.get("micro_gap_context_state")).upper()
    wait_state = _to_text(snap.get("entry_wait_state")).upper()
    weight_overrides = normalize_state25_teacher_weight_overrides(
        snap.get("state25_teacher_weight_overrides")
    )

    body = _to_float(snap.get("micro_body_size_pct_20"), 0.0) * _weight_multiplier(
        weight_overrides, "candle_body_weight"
    )
    doji = _to_float(snap.get("micro_doji_ratio_20"), 0.0) * _weight_multiplier(
        weight_overrides, "doji_weight"
    )
    entry_score = _to_float(snap.get("entry_score"), 0.0)
    contra_score = _to_float(snap.get("contra_score_at_entry"), 0.0)
    current_run = int(
        round(
            _to_int(snap.get("micro_same_color_run_current"), 0)
            * _weight_multiplier(weight_overrides, "same_color_run_weight")
        )
    )
    max_run = int(
        round(
            _to_int(snap.get("micro_same_color_run_max_20"), 0)
            * _weight_multiplier(weight_overrides, "same_color_run_weight")
        )
    )
    compression = _to_float(
        snap.get("micro_range_compression_ratio_20"), 0.0
    ) * _weight_multiplier(weight_overrides, "compression_weight")
    volume_burst = _to_float(
        snap.get("micro_volume_burst_ratio_20"), 0.0
    ) * _weight_multiplier(weight_overrides, "volume_burst_weight")
    volume_decay = _to_float(
        snap.get("micro_volume_burst_decay_20"), 0.0
    ) * _weight_multiplier(weight_overrides, "volume_decay_weight")
    gap_fill = snap.get("micro_gap_fill_progress")
    gap_fill = (
        None
        if gap_fill is None or _to_text(gap_fill) == ""
        else _to_float(gap_fill, 0.0) * _weight_multiplier(weight_overrides, "gap_context_weight")
    )
    upper_wick = _to_float(
        snap.get("micro_upper_wick_ratio_20", snap.get("upper_wick_ratio_20")), 0.0
    ) * _weight_multiplier(weight_overrides, "upper_wick_weight")
    lower_wick = _to_float(
        snap.get("micro_lower_wick_ratio_20", snap.get("lower_wick_ratio_20")), 0.0
    ) * _weight_multiplier(weight_overrides, "lower_wick_weight")
    swing_high = int(
        round(
            _to_int(
                snap.get("micro_swing_high_retest_count_20", snap.get("swing_high_retest_count_20")),
                0,
            )
            * _weight_multiplier(weight_overrides, "swing_retest_weight")
        )
    )
    swing_low = int(
        round(
            _to_int(
                snap.get("micro_swing_low_retest_count_20", snap.get("swing_low_retest_count_20")),
                0,
            )
            * _weight_multiplier(weight_overrides, "swing_retest_weight")
        )
    )

    pred = _parse_prediction_bundle(snap.get("prediction_bundle"))
    p_cont = _to_float(pred.get("p_continuation_success"), 0.0) * _weight_multiplier(
        weight_overrides, "prediction_weight"
    )
    p_false_break = _to_float(pred.get("p_false_break"), 0.0) * _weight_multiplier(
        weight_overrides, "prediction_weight"
    )

    bull_ratio = _to_float(snap.get("micro_bull_ratio_20"), 0.0) * _weight_multiplier(
        weight_overrides, "directional_bias_weight"
    )
    bear_ratio = _to_float(snap.get("micro_bear_ratio_20"), 0.0) * _weight_multiplier(
        weight_overrides, "directional_bias_weight"
    )
    if bull_ratio <= 0.0 and bear_ratio <= 0.0:
        if direction == "BUY":
            bull_ratio = max(bull_ratio, 0.60 if current_run >= 2 else 0.50)
        elif direction == "SELL":
            bear_ratio = max(bear_ratio, 0.60 if current_run >= 2 else 0.50)

    bullish_dom = bull_ratio >= 0.65 or (direction == "BUY" and current_run >= 3)
    bearish_dom = bear_ratio >= 0.65 or (direction == "SELL" and current_run >= 3)
    thin_participation = "THIN" in participation_state or "LOW" in participation_state
    steady_participation = "STEADY" in participation_state
    active_participation = "ACTIVE" in participation_state or "STRONG" in participation_state
    ready_breakout = breakout_state in {"READY_BREAKOUT", "COILED_BREAKOUT"} or compression >= 0.70
    high_reversal = "HIGH" in reversal_state or p_false_break >= 0.50
    moderate_reversal = high_reversal or "MEDIUM" in reversal_state
    gap_live = ("GAP" in gap_state and "NO_GAP" not in gap_state) or (gap_fill is not None and 0.15 <= gap_fill <= 0.85)
    range_reversal_setup = _keyword_hit(
        setup_id,
        "range_lower_reversal",
        "range_upper_reversal",
        "range_reversal",
        "outer_band_reversal",
        "range_outer_band_reversal",
    )
    passive_wait_context = wait_state in {"CENTER", "NOISE"}
    strong_reversal_wait = wait_state in {
        "EDGE_APPROACH",
        "CONFLICT",
        "HELPER_SOFT_BLOCK",
        "ACTIVE",
    }
    explicit_reversal_context = bool(range_reversal_setup and (moderate_reversal or strong_reversal_wait))
    passive_deadcat_context = bool(
        direction == "SELL"
        and _keyword_hit(setup_id, "range_upper_reversal_sell")
        and high_reversal
        and wait_state in {"CENTER", "NOISE", "NONE"}
        and (thin_participation or steady_participation)
    )
    confirm_pullback_context = bool(
        direction == "BUY"
        and _keyword_hit(setup_id, "lower_rebound", "pullback", "reclaim")
        and wait_state in {"NONE", "HELPER_WAIT"}
        and entry_score > contra_score
    )

    scores: dict[int, float] = {pattern_id: 0.0 for pattern_id in _PATTERN_META}

    scores[1] += 0.35 if doji >= 0.25 else 0.0
    scores[1] += 0.25 if volume_burst < 1.5 else 0.0
    scores[1] += 0.20 if max_run <= 2 else 0.0
    scores[1] += 0.20 if (thin_participation or passive_wait_context) and not range_reversal_setup and not moderate_reversal else 0.0

    scores[10] += 0.35 if doji >= 0.50 else 0.0
    scores[10] += 0.25 if max_run <= 2 else 0.0
    scores[10] += 0.20 if abs(bull_ratio - bear_ratio) <= 0.20 else 0.0
    scores[10] += 0.20 if compression >= 0.25 and not range_reversal_setup and not moderate_reversal else 0.0

    scores[14] += 0.30 if session_name else 0.0
    scores[14] += 0.30 if compression >= 0.40 else 0.0
    scores[14] += 0.20 if doji >= 0.25 else 0.0
    scores[14] += 0.20 if volume_burst < 1.8 and not range_reversal_setup and (compression >= 0.25 or doji >= 0.15) else 0.0

    scores[13] += 0.40 if compression >= 0.50 else 0.0
    scores[13] += 0.25 if volume_burst < 1.2 else 0.0
    scores[13] += 0.20 if thin_participation and not range_reversal_setup and not moderate_reversal else 0.0
    scores[13] += 0.15 if body <= 0.20 and not range_reversal_setup else 0.0

    scores[23] += 0.40 if compression >= 0.75 else 0.0
    scores[23] += 0.20 if swing_high >= 2 else 0.0
    scores[23] += 0.20 if swing_low >= 2 else 0.0
    scores[23] += 0.10 if ready_breakout else 0.0
    scores[23] += 0.10 if compression >= 0.80 else 0.0

    scores[4] += 0.35 if max_run >= 4 else 0.0
    scores[4] += 0.25 if bullish_dom or bearish_dom else 0.0
    scores[4] += 0.20 if active_participation else 0.0
    scores[4] += 0.20 if volume_decay <= 0.35 else 0.0

    scores[6] += 0.30 if current_run >= 3 else 0.0
    scores[6] += 0.20 if bullish_dom or bearish_dom else 0.0
    scores[6] += 0.20 if 1.0 <= volume_burst < 2.0 else 0.0
    scores[6] += 0.15 if 0.10 <= compression <= 0.50 else 0.0
    scores[6] += 0.15 if _keyword_hit(setup_id, "pullback", "rebound", "reclaim") else 0.0

    scores[15] += 0.50 if current_run >= 5 else 0.0
    scores[15] += 0.30 if current_run >= 4 and volume_burst >= 2.0 else 0.0
    scores[15] += 0.20 if active_participation else 0.0

    scores[19] += 0.35 if current_run >= 4 else 0.0
    scores[19] += 0.30 if volume_burst >= 2.5 else 0.0
    scores[19] += 0.20 if volume_decay <= 0.30 else 0.0
    scores[19] += 0.15 if active_participation else 0.0

    scores[24] += 0.30 if _keyword_hit(setup_id, "pullback", "rebound", "reclaim", "flag") else 0.0
    scores[24] += 0.25 if compression >= 0.35 else 0.0
    scores[24] += 0.20 if current_run >= 2 else 0.0
    scores[24] += 0.15 if ready_breakout else 0.0
    scores[24] += 0.10 if p_cont >= 0.50 else 0.0

    scores[12] += 0.35 if ready_breakout else 0.0
    scores[12] += 0.30 if compression >= 0.70 else 0.0
    scores[12] += 0.20 if volume_burst >= 1.8 else 0.0
    scores[12] += 0.15 if current_run <= 3 else 0.0
    scores[12] += 0.10 if _keyword_hit(setup_id, "breakout", "break_fail", "break") else 0.0

    scores[7] += 0.35 if volume_burst >= 1.8 else 0.0
    scores[7] += 0.25 if active_participation else 0.0
    scores[7] += 0.20 if 0.20 <= compression <= 0.60 else 0.0
    scores[7] += 0.20 if body >= 0.15 else 0.0

    scores[17] += 0.50 if volume_burst >= 3.0 else 0.0
    scores[17] += 0.30 if volume_decay <= 0.35 else 0.0
    scores[17] += 0.20 if active_participation else 0.0

    scores[3] += 0.40 if volume_burst >= 3.0 else 0.0
    scores[3] += 0.20 if body >= 0.25 else 0.0
    scores[3] += 0.20 if upper_wick >= 0.25 or lower_wick >= 0.25 else 0.0
    scores[3] += 0.20 if ready_breakout and volume_decay <= 0.40 else 0.0

    scores[5] += 0.35 if max(swing_high, swing_low) >= 2 else 0.0
    scores[5] += 0.25 if doji >= 0.30 else 0.0
    scores[5] += 0.25 if range_reversal_setup or _keyword_hit(setup_id, "range", "outer_band", "support_required") else 0.0
    scores[5] += 0.15 if moderate_reversal else 0.0
    scores[5] += 0.10 if thin_participation and not ready_breakout else 0.0
    scores[5] += 0.15 if explicit_reversal_context else 0.0
    scores[5] += 0.10 if wait_state in {"EDGE_APPROACH", "CONFLICT", "HELPER_SOFT_BLOCK", "ACTIVE"} else 0.0
    scores[5] += 0.05 if range_reversal_setup and wait_state in {"AGAINST_MODE", "HELPER_WAIT"} else 0.0

    if explicit_reversal_context:
        for pattern_id, penalty in ((1, 0.20), (10, 0.15), (13, 0.15), (14, 0.25), (23, 0.10)):
            scores[pattern_id] = max(0.0, float(scores.get(pattern_id, 0.0)) - float(penalty))

    scores[11] += 0.35 if _keyword_hit(setup_id, "lower_rebound", "pullback", "reclaim") else 0.0
    scores[11] += 0.25 if lower_wick >= 0.25 else 0.0
    scores[11] += 0.20 if bullish_dom or direction == "BUY" else 0.0
    scores[11] += 0.20 if p_cont >= 0.45 else 0.0
    scores[11] += 0.10 if confirm_pullback_context else 0.0

    scores[16] += 0.30 if _keyword_hit(setup_id, "break_fail", "upper_reject", "probe_not_promoted") else 0.0
    scores[16] += 0.25 if high_reversal else 0.0
    scores[16] += 0.20 if upper_wick >= 0.30 or lower_wick >= 0.30 else 0.0
    scores[16] += 0.15 if ready_breakout else 0.0
    scores[16] += 0.10 if doji >= 0.20 else 0.0

    scores[22] += 0.40 if swing_high >= 2 or swing_low >= 2 else 0.0
    scores[22] += 0.20 if doji >= 0.20 else 0.0
    scores[22] += 0.20 if _keyword_hit(setup_id, "double", "upper_reject", "support_required", "outer_band") else 0.0
    scores[22] += 0.20 if moderate_reversal else 0.0

    scores[25] += 0.30 if bearish_dom or direction == "SELL" else 0.0
    scores[25] += 0.25 if upper_wick >= 0.25 else 0.0
    scores[25] += 0.25 if high_reversal else 0.0
    scores[25] += 0.20 if _keyword_hit(setup_id, "upper_reject", "break_fail") else 0.0
    scores[25] += 0.25 if passive_deadcat_context else 0.0

    scores[21] += 0.50 if gap_live else 0.0
    scores[21] += 0.20 if gap_fill is not None and 0.20 <= gap_fill <= 0.80 else 0.0
    scores[21] += 0.15 if current_run <= 3 else 0.0
    scores[21] += 0.15 if session_name else 0.0

    scores[2] += 0.30 if volume_burst >= 1.8 else 0.0
    scores[2] += 0.20 if upper_wick >= 0.20 else 0.0
    scores[2] += 0.20 if lower_wick >= 0.20 else 0.0
    scores[2] += 0.15 if active_participation else 0.0
    scores[2] += 0.15 if body >= 0.20 else 0.0

    scores[8] += 0.30 if bearish_dom or direction == "SELL" else 0.0
    scores[8] += 0.25 if current_run >= 4 else 0.0
    scores[8] += 0.20 if _keyword_hit(setup_id, "upper_break_fail", "upper_reject", "break_fail") else 0.0
    scores[8] += 0.15 if active_participation else 0.0
    scores[8] += 0.10 if not high_reversal else 0.0

    scores[9] += 0.30 if bullish_dom or direction == "BUY" else 0.0
    scores[9] += 0.25 if current_run >= 4 else 0.0
    scores[9] += 0.20 if _keyword_hit(setup_id, "lower_rebound", "reclaim", "pullback") else 0.0
    scores[9] += 0.15 if active_participation else 0.0
    scores[9] += 0.10 if not high_reversal else 0.0

    scores[18] += 0.30 if upper_wick >= 0.25 else 0.0
    scores[18] += 0.30 if lower_wick >= 0.25 else 0.0
    scores[18] += 0.20 if doji >= 0.25 else 0.0
    scores[18] += 0.20 if abs(bull_ratio - bear_ratio) <= 0.20 else 0.0

    scores[20] += 0.35 if doji >= 0.30 else 0.0
    scores[20] += 0.30 if volume_decay >= 0.50 else 0.0
    scores[20] += 0.20 if thin_participation else 0.0
    scores[20] += 0.15 if current_run <= 2 else 0.0

    for pattern_id in tuple(scores.keys()):
        scores[pattern_id] = float(scores[pattern_id]) * _pattern_score_multiplier(
            pattern_id,
            weight_overrides,
        )

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    primary_id, primary_score = ranked[0]
    if primary_score < 0.50:
        return {}

    secondary_id = 0
    secondary_name = ""
    secondary_score = 0.0
    if len(ranked) > 1:
        candidate_id, candidate_score = ranked[1]
        if candidate_score >= 0.48 and (primary_score - candidate_score) <= 0.10:
            secondary_id = int(candidate_id)
            secondary_name = _PATTERN_META[candidate_id]["name"]
            secondary_score = float(candidate_score)

    confidence = _clip01(primary_score - (0.05 if secondary_id else 0.0))
    meta = dict(_PATTERN_META[primary_id])
    return {
        "teacher_pattern_id": int(primary_id),
        "teacher_pattern_name": str(meta["name"]),
        "teacher_pattern_group": str(meta["group"]),
        "teacher_pattern_secondary_id": int(secondary_id),
        "teacher_pattern_secondary_name": str(secondary_name),
        "teacher_direction_bias": str(meta["direction_bias"]),
        "teacher_entry_bias": str(meta["entry_bias"]),
        "teacher_wait_bias": str(meta["wait_bias"]),
        "teacher_exit_bias": str(meta["exit_bias"]),
        "teacher_transition_risk": str(meta["transition_risk"]),
        "teacher_label_confidence": float(confidence),
        "teacher_lookback_bars": 20,
        "teacher_label_version": "state25_v5",
        "teacher_label_source": "rule_v2_draft",
        "teacher_label_review_status": "unreviewed",
        "teacher_primary_score": float(primary_score),
        "teacher_secondary_score": float(secondary_score),
        "teacher_weight_override_count": int(len(weight_overrides)),
        "teacher_weight_overrides_applied": dict(weight_overrides),
        "teacher_weight_override_display_ko": render_state25_teacher_weight_override_lines_ko(
            weight_overrides
        ),
    }
