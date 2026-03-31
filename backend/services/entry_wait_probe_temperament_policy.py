"""Shared entry wait probe-temperament policy helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from backend.services.symbol_temperament import resolve_wait_probe_temperament


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


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
        converted = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(converted):
        return float(default)
    return float(converted)


def resolve_entry_wait_probe_temperament_v1(
    *,
    payload: Mapping[str, Any] | None = None,
    observe_confirm_v2: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    observe_confirm = _as_mapping(observe_confirm_v2)
    observe_meta = _as_mapping(observe_confirm.get("metadata"))
    probe_plan_v1 = _as_mapping(payload_map.get("entry_probe_plan_v1"))
    probe_candidate_v1 = _as_mapping(
        payload_map.get("probe_candidate_v1", observe_meta.get("probe_candidate_v1", {}))
    )
    temperament = _as_mapping(
        probe_plan_v1.get(
            "symbol_probe_temperament_v1",
            probe_candidate_v1.get("symbol_probe_temperament_v1", {}),
        )
    )
    if not temperament:
        return {
            "present": False,
            "scene_id": "",
            "promotion_bias": "",
            "active": False,
            "ready_for_entry": False,
            "trigger_branch": "",
            "enter_value_delta": 0.0,
            "wait_value_delta": 0.0,
            "prefer_confirm_release": False,
            "prefer_wait_lock": False,
        }

    scene_id = _to_str(temperament.get("scene_id", ""))
    active = _to_bool(probe_plan_v1.get("active", probe_candidate_v1.get("active", False)))
    ready_for_entry = _to_bool(probe_plan_v1.get("ready_for_entry", False))
    trigger_branch = _to_str(
        probe_plan_v1.get("trigger_branch", probe_candidate_v1.get("trigger_branch", ""))
    )
    wait_temperament = _as_mapping(
        resolve_wait_probe_temperament(scene_id, ready_for_entry=ready_for_entry)
    )
    enter_value_delta = _to_float(wait_temperament.get("enter_value_delta", 0.0), 0.0)
    wait_value_delta = _to_float(wait_temperament.get("wait_value_delta", 0.0), 0.0)
    prefer_confirm_release = _to_bool(wait_temperament.get("prefer_confirm_release", False))
    prefer_wait_lock = _to_bool(wait_temperament.get("prefer_wait_lock", False))

    return {
        "present": True,
        "scene_id": str(scene_id),
        "promotion_bias": _to_str(temperament.get("promotion_bias", "")),
        "active": bool(active),
        "ready_for_entry": bool(ready_for_entry),
        "trigger_branch": str(trigger_branch),
        "enter_value_delta": float(enter_value_delta),
        "wait_value_delta": float(wait_value_delta),
        "prefer_confirm_release": bool(prefer_confirm_release),
        "prefer_wait_lock": bool(prefer_wait_lock),
        "entry_style_hint": _to_str(temperament.get("entry_style_hint", "")),
        "note": _to_str(temperament.get("note", "")),
        "source_map_id": _to_str(wait_temperament.get("source_map_id", "")),
    }
