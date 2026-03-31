"""Shared execution-plan orchestrator helpers for exit manage actions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_candidate(
    candidate: Mapping[str, Any] | None,
    index: int,
) -> dict[str, Any]:
    candidate_map = _as_mapping(candidate)
    return {
        "candidate_index": int(index),
        "candidate_kind": _to_str(candidate_map.get("candidate_kind", "")),
        "should_execute": _to_bool(candidate_map.get("should_execute", False), False),
        "reason": _to_str(candidate_map.get("reason", "")),
        "detail": _to_str(candidate_map.get("detail", "")),
        "metric_keys": list(candidate_map.get("metric_keys", []) or []),
        "reverse_action": _to_str(candidate_map.get("reverse_action", "")),
        "reverse_score": _to_float(candidate_map.get("reverse_score", 0.0), 0.0),
        "reverse_reasons": list(candidate_map.get("reverse_reasons", []) or []),
        "candidate_source": _to_str(candidate_map.get("candidate_source", "")),
        "raw_candidate": dict(candidate_map),
    }


def resolve_exit_execution_plan_v1(
    *,
    phase: str = "",
    candidates: list[Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    normalized = [
        _normalize_candidate(candidate, index)
        for index, candidate in enumerate(list(candidates or []))
    ]
    selected = next((candidate for candidate in normalized if bool(candidate.get("should_execute"))), None)
    selected_map = dict(selected or {})

    return {
        "contract_version": "exit_execution_plan_v1",
        "phase": _to_str(phase, "exit_manage"),
        "candidate_count": len(normalized),
        "selected": bool(selected_map),
        "selected_index": int(selected_map.get("candidate_index", -1)),
        "selected_candidate_kind": _to_str(selected_map.get("candidate_kind", "")),
        "selected_reason": _to_str(selected_map.get("reason", "")),
        "selected_detail": _to_str(selected_map.get("detail", "")),
        "selected_metric_keys": list(selected_map.get("metric_keys", []) or []),
        "reverse_action": _to_str(selected_map.get("reverse_action", "")),
        "reverse_score": _to_float(selected_map.get("reverse_score", 0.0), 0.0),
        "reverse_reasons": list(selected_map.get("reverse_reasons", []) or []),
        "plan_status": "execute" if bool(selected_map) else "hold",
        "candidates": normalized,
    }
