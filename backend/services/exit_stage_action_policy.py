"""Shared policy helpers for exit stage action candidates."""

from __future__ import annotations

from backend.core.config import Config


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


def _stage_score_detail(exit_detail: str, protect_score: int, lock_score: int, hold_score: int, suffix: str) -> str:
    base = f"{str(exit_detail or '')} | protect={int(protect_score)} lock={int(lock_score)} hold={int(hold_score)}"
    suffix_text = str(suffix or "").strip()
    return f"{base} | {suffix_text}" if suffix_text else base


def resolve_exit_stage_action_candidate_v1(
    *,
    candidate_scope: str,
    allow_short: bool = False,
    allow_mid: bool = False,
    green_hold_soft_exit: bool = False,
    chosen_stage: str = "",
    protect_streak: int = 0,
    lock_streak: int = 0,
    confirm_short: int = 0,
    confirm_mid: int = 0,
    profit: float = 0.0,
    min_target_profit: float = 0.0,
    min_net_guard: float = 0.0,
    hold_strong: bool = False,
    protect_score: int = 0,
    lock_score: int = 0,
    hold_score: int = 0,
    exit_detail: str = "",
    route_txt: str = "",
    protect_now: bool = False,
    lock_now: bool = False,
    duration_sec: float = 0.0,
    dynamic_move_pct: float = 0.0,
    favorable_move_pct: float = 0.0,
    hard_profit_target: float = 0.0,
    is_trend_mode: bool = False,
) -> dict[str, object]:
    scope = str(candidate_scope or "").strip().lower()
    candidate = {
        "contract_version": "exit_stage_action_candidate_v1",
        "candidate_scope": scope,
        "candidate_kind": "none",
        "should_execute": False,
        "reason": "",
        "detail": "",
        "metric_keys": [],
        "stale_threshold": 0.0,
    }

    if scope == "protect":
        if (
            _to_bool(allow_short)
            and (not _to_bool(green_hold_soft_exit))
            and str(chosen_stage or "").strip().lower() in {"protect", "auto"}
            and _to_int(protect_streak) >= _to_int(confirm_short)
            and _to_float(profit) <= _to_float(min_target_profit)
            and (not _to_bool(hold_strong))
        ):
            candidate.update(
                {
                    "candidate_kind": "protect_exit",
                    "should_execute": True,
                    "reason": "Protect Exit",
                    "detail": _stage_score_detail(exit_detail, protect_score, lock_score, hold_score, route_txt),
                    "metric_keys": ["exit_protect"],
                }
            )
        return candidate

    if scope == "adverse_recheck":
        if not _to_bool(allow_short) or _to_bool(hold_strong):
            return candidate
        if _to_bool(protect_now) and _to_float(profit) <= _to_float(min_target_profit):
            candidate.update(
                {
                    "candidate_kind": "adverse_recheck_protect",
                    "should_execute": True,
                    "reason": "Protect Exit",
                    "detail": _stage_score_detail(exit_detail, protect_score, lock_score, hold_score, "adverse_recheck"),
                    "metric_keys": ["adverse_recheck_hits", "exit_protect"],
                }
            )
            return candidate
        if _to_bool(lock_now) and _to_float(profit) >= _to_float(min_net_guard):
            candidate.update(
                {
                    "candidate_kind": "adverse_recheck_lock",
                    "should_execute": True,
                    "reason": "Lock Exit",
                    "detail": _stage_score_detail(exit_detail, protect_score, lock_score, hold_score, "adverse_recheck"),
                    "metric_keys": ["adverse_recheck_hits", "exit_lock"],
                }
            )
        return candidate

    if scope == "mid_stage":
        if (
            _to_bool(allow_mid)
            and (not _to_bool(green_hold_soft_exit))
            and _to_bool(getattr(Config, "ENABLE_TIME_STOP", True), True)
            and _to_float(duration_sec) >= _to_float(getattr(Config, "TIME_STOP_SECONDS", 600), 600.0)
        ):
            stale_threshold = max(
                _to_float(getattr(Config, "TIME_STOP_MIN_FAVORABLE_MOVE_PCT", 0.0005), 0.0005),
                _to_float(dynamic_move_pct) * 0.5,
            )
            candidate["stale_threshold"] = float(stale_threshold)
            if _to_float(favorable_move_pct) < float(stale_threshold) and _to_float(profit) < _to_float(min_target_profit):
                candidate.update(
                    {
                        "candidate_kind": "time_stop",
                        "should_execute": True,
                        "reason": "Time Stop",
                        "detail": str(exit_detail or ""),
                        "metric_keys": ["exit_time_stop"],
                    }
                )
                return candidate

        if (
            _to_bool(allow_mid)
            and str(chosen_stage or "").strip().lower() in {"lock", "auto"}
            and _to_int(lock_streak) >= _to_int(confirm_mid)
            and _to_float(profit) >= _to_float(min_net_guard)
            and (not _to_bool(hold_strong))
        ):
            candidate.update(
                {
                    "candidate_kind": "lock_exit",
                    "should_execute": True,
                    "reason": "Lock Exit",
                    "detail": _stage_score_detail(exit_detail, protect_score, lock_score, hold_score, route_txt),
                    "metric_keys": ["exit_lock"],
                }
            )
            return candidate

        if _to_bool(allow_mid) and _to_float(profit) >= _to_float(hard_profit_target or getattr(Config, "HARD_PROFIT_TARGET", 0.0), 0.0):
            trend_min_profit = _to_float(min_target_profit) * 1.35
            if (not _to_bool(is_trend_mode)) or _to_float(profit) >= float(trend_min_profit):
                if _to_float(profit) >= _to_float(min_target_profit):
                    candidate.update(
                        {
                            "candidate_kind": "target_exit",
                            "should_execute": True,
                            "reason": "Target",
                            "detail": str(exit_detail or ""),
                            "metric_keys": ["exit_target"],
                        }
                    )
            return candidate

        return candidate

    return candidate
