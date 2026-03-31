"""Shared policy helpers for exit hard-guard action candidates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def resolve_exit_hard_guard_action_candidate_v1(
    *,
    pos_type: int,
    profit: float,
    adverse_risk: bool,
    tf_confirm: bool,
    hold_strong: bool,
    protect_now: bool,
    lock_now: bool,
    min_target_profit: float,
    min_net_guard: float,
    exit_detail: str,
    exit_signal_score: int,
    reverse_signal_threshold: int,
    score_gap: int,
    opposite_score: float,
    result: Mapping[str, Any] | None = None,
    profit_giveback_hit: bool = False,
    plus_to_minus_hit: bool = False,
    hold_for_adverse: bool = False,
    extreme_adverse: bool = False,
    wait_adverse: bool = False,
    wait_detail: str = "",
) -> dict[str, Any]:
    result_map = _as_mapping(result)
    candidate = {
        "contract_version": "exit_hard_guard_action_candidate_v1",
        "hit": False,
        "defer": False,
        "candidate_kind": "none",
        "reason": "",
        "detail": "",
        "metric_keys": [],
        "post_close_metric_keys": [],
        "reverse_action": None,
        "reverse_score": 0.0,
        "reverse_reasons": [],
    }

    if not _to_bool(getattr(Config, "EXIT_HARD_GUARD_ENABLED", True), True):
        return candidate

    if _to_bool(getattr(Config, "PROFIT_GIVEBACK_GUARD_ENABLED", True), True) and bool(profit_giveback_hit):
        candidate.update(
            {
                "hit": True,
                "candidate_kind": "profit_giveback_lock",
                "reason": "Lock Exit",
                "detail": f"{exit_detail} | hard_guard=profit_giveback",
                "metric_keys": ["risk_guard_triggered_total", "exit_lock"],
            }
        )
        return candidate

    if _to_bool(getattr(Config, "EXIT_HARD_GUARD_PLUS_TO_MINUS_ENABLED", True), True) and bool(plus_to_minus_hit):
        candidate.update(
            {
                "hit": True,
                "candidate_kind": "plus_to_minus_protect",
                "reason": "Protect Exit",
                "detail": f"{exit_detail} | hard_guard=plus_to_minus",
                "metric_keys": [
                    "risk_guard_triggered_total",
                    "risk_guard_plus_to_minus",
                    "exit_protect",
                ],
            }
        )
        return candidate

    adverse_guard_enabled = (
        _to_bool(getattr(Config, "EXIT_HARD_GUARD_ADVERSE_ENABLED", True), True)
        and _to_bool(getattr(Config, "ENABLE_ADVERSE_STOP", True), True)
        and bool(adverse_risk)
    )
    if not adverse_guard_enabled:
        return candidate

    if (not bool(hold_for_adverse)) and (not bool(extreme_adverse)):
        return candidate

    if bool(tf_confirm) and (not bool(hold_strong)):
        if bool(protect_now) and float(profit) <= float(min_target_profit):
            candidate.update(
                {
                    "hit": True,
                    "candidate_kind": "adverse_protect",
                    "reason": "Protect Exit",
                    "detail": f"{exit_detail} | hard_guard=adverse",
                    "metric_keys": [
                        "risk_guard_triggered_total",
                        "risk_guard_adverse",
                        "adverse_recheck_hits",
                        "exit_protect",
                    ],
                }
            )
            return candidate
        if bool(lock_now) and float(profit) >= float(min_net_guard):
            candidate.update(
                {
                    "hit": True,
                    "candidate_kind": "adverse_lock",
                    "reason": "Lock Exit",
                    "detail": f"{exit_detail} | hard_guard=adverse",
                    "metric_keys": [
                        "risk_guard_triggered_total",
                        "risk_guard_adverse",
                        "adverse_recheck_hits",
                        "exit_lock",
                    ],
                }
            )
            return candidate

    if bool(wait_adverse):
        candidate.update(
            {
                "defer": True,
                "candidate_kind": "adverse_wait",
            }
        )
        return candidate

    adverse_detail = f"{exit_detail} | hard_guard=adverse"
    if _to_str(wait_detail):
        adverse_detail = f"{adverse_detail} | {_to_str(wait_detail)}"

    reverse_threshold_eff = _to_int(reverse_signal_threshold, 0)
    score_gap_eff = _to_int(getattr(Config, "REVERSAL_MIN_SCORE_GAP", 25), 25)
    if bool(plus_to_minus_hit):
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

    can_reverse_on_adverse = (
        _to_bool(getattr(Config, "ENABLE_ADVERSE_REVERSE", True), True)
        and _to_int(exit_signal_score, 0) >= int(reverse_threshold_eff)
        and _to_int(score_gap, 0) >= int(score_gap_eff)
    )

    if can_reverse_on_adverse:
        reverse_action = "SELL" if int(pos_type) == int(ORDER_TYPE_BUY) else "BUY"
        reverse_reasons = (
            list((_as_mapping(result_map.get("sell", {})).get("reasons", [])) or [])
            if reverse_action == "SELL"
            else list((_as_mapping(result_map.get("buy", {})).get("reasons", [])) or [])
        )
        candidate.update(
            {
                "hit": True,
                "candidate_kind": "adverse_reverse",
                "reason": "Adverse Reversal",
                "detail": adverse_detail,
                "metric_keys": [],
                "post_close_metric_keys": ["exit_adverse_reversal"],
                "reverse_action": reverse_action,
                "reverse_score": float(opposite_score),
                "reverse_reasons": reverse_reasons,
            }
        )
        return candidate

    candidate.update(
        {
            "hit": True,
            "candidate_kind": "adverse_stop",
            "reason": "Adverse Stop",
            "detail": adverse_detail,
            "metric_keys": ["exit_adverse_stop"],
        }
    )
    return candidate
