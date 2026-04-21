"""Resolver helpers for direct binding against the learning parameter registry."""

from __future__ import annotations

from typing import Any, Mapping

from backend.services.learning_parameter_registry import build_learning_parameter_registry


LEARNING_REGISTRY_BINDING_VERSION = "learning_registry_binding_v1"

LEARNING_REGISTRY_BINDING_MODE_EXACT = "exact"
LEARNING_REGISTRY_BINDING_MODE_DERIVED = "derived"
LEARNING_REGISTRY_BINDING_MODE_FALLBACK = "fallback"

_DIRECT_BINDING_PLAN_CATEGORY_KEYS = {
    "detector": ("misread_observation",),
    "weight_review": ("state25_teacher_weight",),
    "proposal_runtime": ("feedback_promotion_policy",),
    "forecast_report": ("forecast_runtime",),
}


def _payload_rows(payload: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    source = dict(payload or {}) if isinstance(payload, Mapping) else build_learning_parameter_registry()
    return [dict(row) for row in list(source.get("rows", []) or [])]


def _normalize_registry_key_list(values: list[object] | tuple[object, ...] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def build_learning_registry_index(
    payload: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("registry_key")): row
        for row in _payload_rows(payload)
        if str(row.get("registry_key") or "").strip()
    }


def resolve_learning_registry_row(
    registry_key: object,
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    key = str(registry_key or "").strip()
    if not key:
        return {}
    return dict(build_learning_registry_index(payload).get(key) or {})


def build_learning_registry_binding_fields(
    registry_key: object,
    *,
    binding_mode: str = LEARNING_REGISTRY_BINDING_MODE_EXACT,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = resolve_learning_registry_row(registry_key, payload=payload)
    key = str(registry_key or "").strip()
    return {
        "registry_key": key,
        "registry_label_ko": str(row.get("label_ko", "") or ""),
        "registry_description_ko": str(row.get("description_ko", "") or ""),
        "registry_category": str(row.get("category_key", "") or ""),
        "registry_category_label_ko": str(row.get("category_label_ko", "") or ""),
        "registry_component_key": str(row.get("component_key", "") or ""),
        "registry_runtime_role_ko": str(row.get("runtime_role_ko", "") or ""),
        "registry_proposal_role_ko": str(row.get("proposal_role_ko", "") or ""),
        "registry_source_file": str(row.get("source_file", "") or ""),
        "registry_source_field": str(row.get("source_field", "") or ""),
        "registry_binding_mode": str(binding_mode or LEARNING_REGISTRY_BINDING_MODE_EXACT),
        "registry_binding_version": LEARNING_REGISTRY_BINDING_VERSION,
        "registry_found": bool(row),
    }


def build_learning_registry_relation(
    *,
    evidence_registry_keys: list[object] | tuple[object, ...] | None = None,
    target_registry_keys: list[object] | tuple[object, ...] | None = None,
    binding_mode: str = LEARNING_REGISTRY_BINDING_MODE_DERIVED,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_keys = _normalize_registry_key_list(list(evidence_registry_keys or []))
    target_keys = _normalize_registry_key_list(list(target_registry_keys or []))
    evidence_bindings = [
        build_learning_registry_binding_fields(key, binding_mode=binding_mode, payload=payload)
        for key in evidence_keys
    ]
    target_bindings = [
        build_learning_registry_binding_fields(key, binding_mode=binding_mode, payload=payload)
        for key in target_keys
    ]
    return {
        "registry_binding_version": LEARNING_REGISTRY_BINDING_VERSION,
        "registry_binding_mode": str(binding_mode or LEARNING_REGISTRY_BINDING_MODE_DERIVED),
        "evidence_registry_keys": evidence_keys,
        "target_registry_keys": target_keys,
        "evidence_bindings": evidence_bindings,
        "target_bindings": target_bindings,
        "binding_ready": bool(
            evidence_keys or target_keys
        ) and all(bool(row.get("registry_found")) for row in [*evidence_bindings, *target_bindings]),
    }


def build_learning_registry_direct_binding_plan(
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = _payload_rows(payload)
    rows_by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        category_key = str(row.get("category_key") or "").strip()
        if not category_key:
            continue
        rows_by_category.setdefault(category_key, []).append(row)

    stages: dict[str, Any] = {}
    for stage_key, category_keys in _DIRECT_BINDING_PLAN_CATEGORY_KEYS.items():
        stage_rows: list[dict[str, Any]] = []
        for category_key in category_keys:
            stage_rows.extend(rows_by_category.get(category_key, []))
        target_registry_keys = [
            str(row.get("registry_key"))
            for row in stage_rows
            if str(row.get("registry_key") or "").strip()
        ]
        stages[stage_key] = {
            "stage_key": stage_key,
            "category_keys": list(category_keys),
            "target_registry_keys": target_registry_keys,
            "target_key_count": len(target_registry_keys),
        }

    all_target_registry_keys = _normalize_registry_key_list(
        [key for stage in stages.values() for key in list(stage.get("target_registry_keys") or [])]
    )
    return {
        "binding_version": LEARNING_REGISTRY_BINDING_VERSION,
        "stages": stages,
        "all_target_registry_keys": all_target_registry_keys,
        "all_target_key_count": len(all_target_registry_keys),
    }
