"""Shared policy helpers for exit recovery execution candidates."""

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


def resolve_exit_recovery_execution_candidate_v1(
    *,
    profit: float,
    adverse_risk: bool,
    duration_sec: float,
    tf_confirm: bool,
    score_gap: int,
    wait_state: object | None = None,
    wait_metadata: Mapping[str, Any] | None = None,
    exit_shadow: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    shadow = _as_mapping(exit_shadow)
    wait_meta = _as_mapping(wait_metadata)
    winner = _to_str(shadow.get("winner", "")).lower()
    wait_state_name = _to_str(getattr(wait_state, "state", ""), "NONE").upper()
    reverse_gap = _to_int(
        wait_meta.get(
            "reverse_score_gap",
            getattr(Config, "EXIT_RECOVERY_REVERSE_SCORE_GAP", 26),
        ),
        getattr(Config, "EXIT_RECOVERY_REVERSE_SCORE_GAP", 26),
    )
    reverse_min_prob = _to_float(getattr(Config, "EXIT_RECOVERY_REVERSE_MIN_PROB", 0.58), 0.58)
    reverse_min_hold_seconds = _to_float(
        getattr(Config, "EXIT_RECOVERY_REVERSE_MIN_HOLD_SECONDS", 45), 45.0
    )
    max_wait_seconds = _to_float(
        wait_meta.get(
            "recovery_wait_max_seconds",
            getattr(Config, "EXIT_RECOVERY_WAIT_MAX_SECONDS", 240),
        ),
        240.0,
    )
    be_max_loss = _to_float(
        wait_meta.get(
            "recovery_be_max_loss",
            getattr(Config, "EXIT_RECOVERY_BE_MAX_LOSS_USD", 0.90),
        ),
        0.90,
    )
    tp1_max_loss = _to_float(
        wait_meta.get(
            "recovery_tp1_max_loss",
            getattr(Config, "EXIT_RECOVERY_TP1_MAX_LOSS_USD", 0.35),
        ),
        0.35,
    )
    be_close_profit = _to_float(getattr(Config, "EXIT_RECOVERY_BE_CLOSE_USD", 0.02), 0.02)
    tp1_close_profit = _to_float(getattr(Config, "EXIT_RECOVERY_TP1_CLOSE_USD", 0.12), 0.12)
    reverse_exec_enabled = _to_bool(getattr(Config, "EXIT_RECOVERY_REVERSE_EXEC_ENABLED", True), True)
    p_reverse_valid = _to_float(shadow.get("p_reverse_valid", 0.0), 0.0)

    out = {
        "contract_version": "exit_recovery_execution_candidate_v1",
        "mode": "none",
        "reason": "",
        "close_reason": "",
        "can_reverse": False,
        "reverse_reason": "",
        "candidate_kind": "none",
    }

    if winner == "wait_be":
        if float(profit) >= float(be_close_profit):
            out.update(
                {
                    "mode": "exit",
                    "reason": "recovery_be_close",
                    "close_reason": "Recovery BE",
                    "candidate_kind": "recovery_be_close",
                }
            )
            return out
        if (
            float(profit) < 0.0
            and (not bool(adverse_risk))
            and float(duration_sec) <= float(max_wait_seconds)
            and abs(float(profit)) <= float(be_max_loss)
        ):
            out.update(
                {
                    "mode": "hold",
                    "reason": "recovery_be_hold",
                    "candidate_kind": "recovery_be_hold",
                }
            )
            return out
        out.update({"reason": "recovery_be_expired", "candidate_kind": "recovery_be_expired"})
        return out

    if winner == "wait_tp1":
        if float(profit) >= float(tp1_close_profit):
            out.update(
                {
                    "mode": "exit",
                    "reason": "recovery_tp1_close",
                    "close_reason": "Recovery TP1",
                    "candidate_kind": "recovery_tp1_close",
                }
            )
            return out
        if (
            float(profit) < 0.0
            and (not bool(adverse_risk))
            and float(duration_sec) <= float(max_wait_seconds)
            and abs(float(profit)) <= float(tp1_max_loss)
        ):
            out.update(
                {
                    "mode": "hold",
                    "reason": "recovery_tp1_hold",
                    "candidate_kind": "recovery_tp1_hold",
                }
            )
            return out
        out.update({"reason": "recovery_tp1_expired", "candidate_kind": "recovery_tp1_expired"})
        return out

    if (
        winner == "reverse_now"
        and bool(reverse_exec_enabled)
        and float(profit) < 0.0
        and bool(adverse_risk)
        and bool(tf_confirm)
        and str(wait_state_name) == "REVERSE_READY"
        and int(score_gap) >= int(reverse_gap)
        and float(p_reverse_valid) >= float(reverse_min_prob)
        and float(duration_sec) >= float(reverse_min_hold_seconds)
    ):
        out.update(
            {
                "mode": "reverse",
                "reason": "recovery_reverse_execute",
                "close_reason": "Recovery Reverse",
                "can_reverse": True,
                "reverse_reason": "recovery_reverse_execute",
                "candidate_kind": "recovery_reverse_execute",
            }
        )
        return out

    return out
