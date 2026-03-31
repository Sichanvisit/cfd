"""Shared result-surface helpers for exit manage execution orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


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


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_exit_execution_result_surface_v1(
    *,
    symbol: str = "",
    ticket: int = 0,
    execution_plan_v1: Mapping[str, Any] | None = None,
    execution_status: str = "",
) -> dict[str, Any]:
    plan = _as_mapping(execution_plan_v1)
    selected = _to_bool(plan.get("selected", False), False)
    phase = _to_str(plan.get("phase", "exit_manage"), "exit_manage")
    candidate_kind = _to_str(plan.get("selected_candidate_kind", ""))
    reason = _to_str(plan.get("selected_reason", ""))
    detail = _to_str(plan.get("selected_detail", ""))
    metric_keys = list(plan.get("selected_metric_keys", []) or [])
    reverse_action = _to_str(plan.get("reverse_action", ""))
    reverse_score = _to_float(plan.get("reverse_score", 0.0), 0.0)
    reverse_reasons = list(plan.get("reverse_reasons", []) or [])
    status = _to_str(execution_status, _to_str(plan.get("plan_status", "hold"), "hold"))

    trade_logger_payload: dict[str, Any] = {}
    if selected:
        trade_logger_payload = {
            "exit_reason": reason,
            "policy_scope": f"exit_execution:{phase}:{candidate_kind}",
        }

    return {
        "contract_version": "exit_execution_result_surface_v1",
        "summary": {
            "symbol": _to_str(symbol).upper(),
            "ticket": _to_int(ticket, 0),
            "phase": phase,
            "execution_status": status,
            "selected": bool(selected),
            "selected_candidate_kind": candidate_kind,
            "selected_reason": reason,
            "reverse_action": reverse_action,
        },
        "trade_logger_payload": trade_logger_payload,
        "live_metrics_payload": {
            "exit_execution_phase": phase,
            "exit_execution_status": status,
            "exit_execution_selected": int(1 if selected else 0),
            "exit_execution_candidate_kind": candidate_kind,
            "exit_execution_reason": reason,
            "exit_execution_detail": detail,
            "exit_execution_metric_keys": ",".join(str(key) for key in metric_keys),
            "exit_execution_reverse_action": reverse_action,
            "exit_execution_reverse_score": reverse_score,
            "exit_execution_reverse_reasons": list(reverse_reasons),
        },
    }
