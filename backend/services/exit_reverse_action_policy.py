"""Shared policy helpers for exit reverse action candidates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def resolve_exit_adverse_reverse_candidate_v1(
    *,
    pos_type: int,
    exit_signal_score: int,
    reverse_signal_threshold: int,
    score_gap: int,
    plus_to_minus_hint: bool,
    opposite_score: float,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result_map = _as_mapping(result)
    reverse_threshold_eff = _to_int(reverse_signal_threshold, 0)
    score_gap_eff = _to_int(getattr(Config, "REVERSAL_MIN_SCORE_GAP", 25), 25)

    if bool(plus_to_minus_hint):
        rev_mult = _to_float(getattr(Config, "ADVERSE_REVERSE_PLUS_TO_MINUS_MULT", 0.78), 0.78)
        reverse_threshold_eff = max(
            60,
            int(round(float(reverse_threshold_eff) * max(0.45, min(1.0, rev_mult)))),
        )
        score_gap_eff = min(
            int(score_gap_eff),
            int(
                max(
                    4,
                    _to_int(
                        getattr(Config, "ADVERSE_REVERSE_PLUS_TO_MINUS_MIN_SCORE_GAP", 12),
                        12,
                    ),
                )
            ),
        )

    should_reverse = (
        _to_bool(getattr(Config, "ENABLE_ADVERSE_REVERSE", True), True)
        and _to_int(exit_signal_score, 0) >= int(reverse_threshold_eff)
        and _to_int(score_gap, 0) >= int(score_gap_eff)
    )

    reverse_action = "SELL" if int(pos_type) == int(ORDER_TYPE_BUY) else "BUY"
    reverse_reasons = (
        list((_as_mapping(result_map.get("sell", {})).get("reasons", [])) or [])
        if reverse_action == "SELL"
        else list((_as_mapping(result_map.get("buy", {})).get("reasons", [])) or [])
    )
    return {
        "contract_version": "exit_adverse_reverse_candidate_v1",
        "candidate_kind": "adverse_reverse" if should_reverse else "adverse_stop",
        "should_reverse": bool(should_reverse),
        "reverse_threshold_eff": int(reverse_threshold_eff),
        "score_gap_eff": int(score_gap_eff),
        "reverse_action": reverse_action,
        "reverse_score": float(opposite_score),
        "reverse_reasons": reverse_reasons,
    }


def resolve_exit_reversal_action_candidate_v1(
    *,
    pos_type: int,
    reversal_hit: bool,
    streak: int,
    reversal_confirm_needed: int,
    opposite_score: float,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result_map = _as_mapping(result)
    should_execute = bool(reversal_hit) and int(streak) >= int(reversal_confirm_needed)
    reverse_action = "SELL" if int(pos_type) == int(ORDER_TYPE_BUY) else "BUY"
    reverse_reasons = (
        list((_as_mapping(result_map.get("sell", {})).get("reasons", [])) or [])
        if reverse_action == "SELL"
        else list((_as_mapping(result_map.get("buy", {})).get("reasons", [])) or [])
    )
    return {
        "contract_version": "exit_reversal_action_candidate_v1",
        "candidate_kind": "reversal_execute" if should_execute else "reversal_hold",
        "should_execute": bool(should_execute),
        "reversal_hit": bool(reversal_hit),
        "streak": int(streak),
        "reversal_confirm_needed": int(reversal_confirm_needed),
        "reverse_action": reverse_action,
        "reverse_score": float(opposite_score),
        "reverse_reasons": reverse_reasons,
    }
