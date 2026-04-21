"""Shared policy helpers for continuation-hold / runner-preservation candidates."""

from __future__ import annotations

from backend.core.config import Config
from backend.services.exit_partial_action_policy import (
    resolve_exit_partial_action_candidate_v1,
)


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


def resolve_exit_runner_preservation_candidate_v1(
    *,
    symbol: str = "",
    pos_type: int = 0,
    entry_price: float = 0.0,
    position_volume: float = 0.0,
    selected_candidate_kind: str = "",
    selected_reason: str = "",
    profit: float = 0.0,
    peak_profit: float = 0.0,
    giveback_usd: float = 0.0,
    min_net_guard: float = 0.0,
    roundtrip_cost: float = 0.0,
    favorable_move_pct: float = 0.0,
    dynamic_move_pct: float = 0.0,
    hold_score: int = 0,
    lock_score: int = 0,
    hold_threshold: int = 0,
    partial_done: bool = False,
    be_moved: bool = False,
    profit_stop_target_sl: float = 0.0,
) -> dict[str, object]:
    candidate = {
        "contract_version": "exit_runner_preservation_candidate_v1",
        "candidate_kind": "none",
        "should_execute": False,
        "skip_full_exit": False,
        "reason": "",
        "detail": "",
        "metric_keys": [],
        "skip_reason": "",
        "partial_candidate": {},
        "lock_price": 0.0,
        "policy_scope": "",
    }

    if not _to_bool(getattr(Config, "ENABLE_EXIT_RUNNER_PRESERVATION", True), True):
        candidate["skip_reason"] = "disabled"
        return candidate

    selected_kind = str(selected_candidate_kind or "").strip().lower()
    selected_reason_text = str(selected_reason or "").strip().lower()
    if selected_kind not in {"lock_exit", "target_exit", "adverse_recheck_lock"} and selected_reason_text not in {
        "lock exit",
        "target",
    }:
        candidate["skip_reason"] = "non_runner_exit_candidate"
        return candidate

    profit_v = _to_float(profit)
    peak_v = max(_to_float(peak_profit), profit_v)
    giveback_v = max(0.0, _to_float(giveback_usd))
    min_peak = _to_float(getattr(Config, "EXIT_RUNNER_PRESERVATION_MIN_PEAK_USD", 0.80), 0.80)
    if peak_v < min_peak:
        candidate["skip_reason"] = "peak_below_floor"
        return candidate
    if profit_v < _to_float(min_net_guard):
        candidate["skip_reason"] = "profit_below_guard"
        return candidate

    max_giveback = max(
        _to_float(getattr(Config, "EXIT_RUNNER_PRESERVATION_MAX_GIVEBACK_USD", 0.90), 0.90),
        peak_v * _to_float(getattr(Config, "EXIT_RUNNER_PRESERVATION_MAX_GIVEBACK_RATIO", 0.55), 0.55),
    )
    if giveback_v > max_giveback:
        candidate["skip_reason"] = "giveback_too_large"
        return candidate

    symbol_u = str(symbol or "").strip().upper()
    hold_ratio = _to_float(
        getattr(
            Config,
            "EXIT_RUNNER_PRESERVATION_XAU_HOLD_RATIO" if symbol_u == "XAUUSD" else "EXIT_RUNNER_PRESERVATION_DEFAULT_HOLD_RATIO",
            0.82 if symbol_u == "XAUUSD" else 0.92,
        ),
        0.82 if symbol_u == "XAUUSD" else 0.92,
    )
    hold_score_v = _to_int(hold_score)
    lock_score_v = _to_int(lock_score)
    hold_threshold_v = _to_int(hold_threshold)
    favorable_move_v = _to_float(favorable_move_pct)
    min_favorable = max(
        _to_float(dynamic_move_pct) * 0.8,
        _to_float(getattr(Config, "EXIT_RUNNER_PRESERVATION_MIN_FAVORABLE_MOVE_PCT", 0.0008), 0.0008),
    )
    if favorable_move_v < min_favorable:
        candidate["skip_reason"] = "favorable_move_too_small"
        return candidate
    if hold_score_v < max(int(round(lock_score_v * hold_ratio)), int(round(hold_threshold_v * 0.75))):
        candidate["skip_reason"] = "hold_strength_too_low"
        return candidate

    partial_candidate = resolve_exit_partial_action_candidate_v1(
        pos_type=_to_int(pos_type),
        entry_price=_to_float(entry_price),
        position_volume=_to_float(position_volume),
        favorable_move_pct=favorable_move_v,
        dynamic_move_pct=_to_float(dynamic_move_pct),
        profit=profit_v,
        min_net_guard=_to_float(min_net_guard),
        roundtrip_cost=_to_float(roundtrip_cost),
        partial_done=_to_bool(partial_done, False),
    )
    lock_price = _to_float(profit_stop_target_sl)

    if _to_bool(partial_candidate.get("should_execute", False), False):
        lock_price = max(lock_price, _to_float(partial_candidate.get("be_price", 0.0), 0.0))
        candidate.update(
            {
                "candidate_kind": "partial_then_runner_hold",
                "should_execute": True,
                "skip_full_exit": True,
                "reason": "Runner Preserve",
                "detail": f"selected={selected_kind or selected_reason_text},hold={hold_score_v},lock={lock_score_v},peak={peak_v:.2f},giveback={giveback_v:.2f}",
                "metric_keys": ["exit_runner_preserve", "exit_runner_partial_hold"],
                "partial_candidate": dict(partial_candidate),
                "lock_price": float(lock_price),
                "policy_scope": "EXIT_RUNNER_PRESERVATION_PARTIAL",
            }
        )
        return candidate

    if _to_bool(partial_done, False) or _to_bool(be_moved, False) or lock_price > 0.0:
        candidate.update(
            {
                "candidate_kind": "runner_lock_only",
                "should_execute": True,
                "skip_full_exit": True,
                "reason": "Runner Preserve",
                "detail": f"selected={selected_kind or selected_reason_text},hold={hold_score_v},lock={lock_score_v},peak={peak_v:.2f},giveback={giveback_v:.2f}",
                "metric_keys": ["exit_runner_preserve", "exit_runner_lock_only"],
                "partial_candidate": dict(partial_candidate),
                "lock_price": float(lock_price),
                "policy_scope": "EXIT_RUNNER_PRESERVATION_LOCK",
            }
        )
        return candidate

    candidate["skip_reason"] = "no_runner_protection_path"
    return candidate
