"""Utility helpers for comparing candidate actions."""

from __future__ import annotations

from typing import Mapping


def compute_entry_utility(
    *,
    p_win: float,
    expected_reward: float,
    expected_risk: float,
    cost: float,
    context_adj: float = 0.0,
) -> float:
    return float((float(p_win) * float(expected_reward)) - ((1.0 - float(p_win)) * float(expected_risk)) - float(cost) + float(context_adj))


def compute_wait_utility(
    *,
    p_better_entry_if_wait: float,
    expected_entry_improvement: float,
    expected_miss_cost: float,
    extra_penalty: float = 0.0,
) -> float:
    return float((float(p_better_entry_if_wait) * float(expected_entry_improvement)) - float(expected_miss_cost) - float(extra_penalty))


def compute_exit_utility(
    *,
    locked_profit: float,
    exit_cost: float,
) -> float:
    return float(float(locked_profit) - float(exit_cost))


def compute_hold_utility(
    *,
    p_more_profit: float,
    upside: float,
    p_giveback: float,
    giveback: float,
) -> float:
    return float((float(p_more_profit) * float(upside)) - (float(p_giveback) * float(giveback)))


def compute_reverse_utility(
    *,
    p_reverse_valid: float,
    reverse_edge: float,
    reverse_cost: float,
) -> float:
    return float((float(p_reverse_valid) * float(reverse_edge)) - float(reverse_cost))


def select_utility_winner(
    candidates: Mapping[str, float] | None,
    *,
    priority: list[str] | None = None,
) -> tuple[str, float]:
    pool = {str(k): float(v) for k, v in dict(candidates or {}).items() if str(k)}
    if not pool:
        return "", 0.0
    order = list(priority or [])
    ranked = sorted(
        pool.items(),
        key=lambda item: (
            -float(item[1]),
            order.index(item[0]) if item[0] in order else len(order),
            item[0],
        ),
    )
    winner, value = ranked[0]
    return str(winner), float(value)
