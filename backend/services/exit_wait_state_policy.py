"""Base exit wait-state policy helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config


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


def resolve_exit_wait_state_policy_v1(
    exit_wait_state_input_v1: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = _as_mapping(exit_wait_state_input_v1)
    identity = _as_mapping(contract.get("identity"))
    market = _as_mapping(contract.get("market"))
    risk = _as_mapping(contract.get("risk"))
    policy = _as_mapping(contract.get("policy"))

    symbol = _to_str(identity.get("symbol", "")).upper()
    regime_now = _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper()
    current_box_state = _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper()
    profit = _to_float(risk.get("profit", 0.0), 0.0)
    giveback = _to_float(risk.get("giveback", 0.0), 0.0)
    duration_sec = _to_float(risk.get("duration_sec", 0.0), 0.0)
    adverse_risk = _to_bool(risk.get("adverse_risk", False))
    tf_confirm = _to_bool(risk.get("tf_confirm", False))
    score_gap = _to_int(risk.get("score_gap", 0), 0)

    allow_wait_be = _to_bool(policy.get("allow_wait_be", True))
    allow_wait_tp1 = _to_bool(policy.get("allow_wait_tp1", False))
    prefer_reverse = _to_bool(policy.get("prefer_reverse", False))
    recovery_be_max_loss = max(0.05, _to_float(policy.get("recovery_be_max_loss", 0.0), 0.0))
    recovery_tp1_max_loss = max(0.0, _to_float(policy.get("recovery_tp1_max_loss", 0.0), 0.0))
    recovery_wait_max_seconds = max(0.0, _to_float(policy.get("recovery_wait_max_seconds", 0.0), 0.0))
    reverse_gap = max(1, _to_int(policy.get("reverse_score_gap", 1), 1))

    state = "NONE"
    reason = ""
    hard_wait = False
    matched_rule = "none"

    if adverse_risk and not tf_confirm:
        state = "REVERSAL_CONFIRM"
        reason = "opposite_signal_unconfirmed"
        hard_wait = True
        matched_rule = "reversal_confirm"
    elif regime_now == "RANGE" and current_box_state == "MIDDLE" and profit >= 0.0:
        state = "ACTIVE"
        reason = "range_middle_observe"
        matched_rule = "range_middle_active"
    elif (
        bool(getattr(Config, "EXIT_RECOVERY_WAIT_ENABLED", True))
        and allow_wait_tp1
        and (profit < 0.0)
        and (duration_sec <= recovery_wait_max_seconds)
        and (not adverse_risk)
        and (abs(float(profit)) <= recovery_tp1_max_loss)
        and (abs(int(score_gap)) < reverse_gap)
    ):
        state = "RECOVERY_TP1"
        reason = "recovery_to_small_profit"
        matched_rule = "recovery_tp1"
    elif (
        bool(getattr(Config, "EXIT_RECOVERY_WAIT_ENABLED", True))
        and allow_wait_be
        and (profit < 0.0)
        and (duration_sec <= recovery_wait_max_seconds)
        and (abs(float(profit)) <= recovery_be_max_loss)
        and (not adverse_risk)
    ):
        state = "RECOVERY_BE"
        reason = "recovery_to_breakeven"
        matched_rule = "recovery_be"
    elif profit < 0.0 and prefer_reverse and tf_confirm and int(score_gap) >= reverse_gap:
        state = "REVERSE_READY"
        reason = "reverse_ready_after_confirm"
        matched_rule = "reverse_ready"
    elif adverse_risk and profit < 0.0:
        state = "CUT_IMMEDIATE"
        reason = "adverse_loss_expand"
        matched_rule = "cut_immediate"
    elif profit >= 0.0 and giveback <= max(0.0, abs(profit) * 0.35) and not tf_confirm and score_gap <= 0:
        state = "GREEN_CLOSE"
        reason = "green_close_hold"
        matched_rule = "green_close"

    return {
        "contract_version": "exit_wait_state_policy_v1",
        "symbol": str(symbol),
        "state": str(state),
        "reason": str(reason),
        "hard_wait": bool(hard_wait),
        "matched_rule": str(matched_rule),
    }
