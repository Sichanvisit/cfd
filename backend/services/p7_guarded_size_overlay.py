from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.core.config import Config


ROOT = Path(__file__).resolve().parents[2]

P7_GUARDED_SIZE_OVERLAY_CONTRACT_V1 = {
    "contract_version": "p7_guarded_size_overlay_contract_v1",
    "scope": "entry_execution_overlay",
    "purpose": [
        "materialize guarded size reduction candidates from P7",
        "keep overlay outside semantic core and setup logic",
        "support disabled, dry_run, and guarded apply modes",
    ],
    "mode_values": ["disabled", "dry_run", "apply"],
}

_PAYLOAD_CACHE: dict[str, dict[str, Any]] = {}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any, default: float = 0.0) -> float:
    text = _coerce_text(value)
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    text = _coerce_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _resolve_source_path(path_value: str | Path | None = None) -> Path:
    raw = _coerce_text(path_value or getattr(Config, "P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH", ""))
    if not raw:
        raw = r"data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_latest.json"
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate


def _normalize_order_lot(*, base_lot: float, size_multiplier: float, min_lot: float) -> float:
    base = max(0.0, float(base_lot))
    mult = max(0.01, float(size_multiplier))
    floor = max(0.01, float(min_lot))
    return round(max(floor, base * mult), 2)


def _read_payload_cached(path: Path) -> dict[str, Any]:
    cache_key = str(path)
    if not path.exists():
        _PAYLOAD_CACHE.pop(cache_key, None)
        return {}
    try:
        stat = path.stat()
    except Exception:
        return {}
    stamp = (int(stat.st_mtime_ns), int(stat.st_size))
    cache = _PAYLOAD_CACHE.get(cache_key)
    if cache and cache.get("stamp") == stamp:
        return dict(cache.get("payload", {}))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    _PAYLOAD_CACHE[cache_key] = {"stamp": stamp, "payload": dict(payload)}
    return dict(payload)


def load_p7_guarded_size_overlay_payload(
    source_path: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    resolved_path = _resolve_source_path(source_path)
    return _read_payload_cached(resolved_path), resolved_path


def resolve_p7_guarded_size_overlay_v1(
    *,
    symbol: str,
    action: str,
    entry_stage: str,
    base_lot: float,
    proposed_lot: float,
    min_lot: float = 0.01,
    source_path: str | Path | None = None,
) -> dict[str, Any]:
    symbol_u = _coerce_text(symbol).upper()
    action_u = _coerce_text(action).upper()
    stage_u = _coerce_text(entry_stage).lower()
    current_multiplier = max(0.01, round(float(proposed_lot) / max(1e-9, float(base_lot)), 6))
    payload, resolved_path = load_p7_guarded_size_overlay_payload(source_path)
    mode = _coerce_text(getattr(Config, "P7_GUARDED_SIZE_OVERLAY_MODE", "disabled")).lower() or "disabled"
    enabled = bool(getattr(Config, "ENABLE_P7_GUARDED_SIZE_OVERLAY", False))
    allowed_symbols = tuple(
        item.strip().upper()
        for item in getattr(Config, "P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST", ())
        if str(item).strip()
    )
    max_step = max(0.01, _coerce_float(getattr(Config, "P7_GUARDED_SIZE_OVERLAY_MAX_STEP", 0.10), 0.10))

    by_symbol = _coerce_mapping(payload.get("guarded_size_overlay_by_symbol"))
    matched_row = _coerce_mapping(by_symbol.get(symbol_u))
    if not matched_row:
        for row in payload.get("guarded_size_overlay_candidates", []) or []:
            row_local = _coerce_mapping(row)
            if _coerce_text(row_local.get("symbol")).upper() == symbol_u:
                matched_row = row_local
                break

    matched = bool(matched_row)
    target_multiplier = round(
        max(0.01, _coerce_float(matched_row.get("target_multiplier"), current_multiplier)),
        6,
    )
    candidate_multiplier = current_multiplier
    if matched and target_multiplier < current_multiplier:
        candidate_multiplier = max(target_multiplier, round(current_multiplier - max_step, 6))

    source_available = bool(payload)
    source_report_version = _coerce_text(payload.get("report_version"))
    gate_reason = "passed"
    apply_allowed = False
    effective_multiplier = current_multiplier

    if not enabled or mode == "disabled":
        gate_reason = "overlay_disabled"
    elif not source_available:
        gate_reason = "overlay_source_unavailable"
    elif allowed_symbols and symbol_u not in allowed_symbols:
        gate_reason = "symbol_not_allowlisted"
    elif not matched:
        gate_reason = "symbol_not_matched"
    elif target_multiplier >= current_multiplier:
        gate_reason = "no_reduction_needed"
    elif mode != "apply":
        gate_reason = "dry_run_only"
    else:
        apply_allowed = True
        effective_multiplier = candidate_multiplier

    candidate_lot = _normalize_order_lot(
        base_lot=float(base_lot),
        size_multiplier=float(candidate_multiplier),
        min_lot=float(min_lot),
    )
    effective_lot = _normalize_order_lot(
        base_lot=float(base_lot),
        size_multiplier=float(effective_multiplier),
        min_lot=float(min_lot),
    )
    applied = bool(apply_allowed and effective_lot < float(proposed_lot))

    return {
        "contract_version": "p7_guarded_size_overlay_v1",
        "overlay_contract_version": P7_GUARDED_SIZE_OVERLAY_CONTRACT_V1["contract_version"],
        "enabled": bool(enabled),
        "mode": str(mode),
        "symbol": str(symbol_u),
        "action": str(action_u),
        "entry_stage": str(stage_u),
        "source_path": str(resolved_path),
        "source_available": bool(source_available),
        "source_report_version": str(source_report_version or ""),
        "matched": bool(matched),
        "apply_allowed": bool(apply_allowed),
        "applied": bool(applied),
        "gate_reason": str(gate_reason),
        "base_lot": float(base_lot),
        "proposed_lot_before": float(proposed_lot),
        "effective_lot": float(effective_lot),
        "candidate_lot": float(candidate_lot),
        "min_lot": float(min_lot),
        "current_multiplier": float(round(current_multiplier, 6)),
        "target_multiplier": float(round(target_multiplier, 6)),
        "candidate_multiplier": float(round(candidate_multiplier, 6)),
        "effective_multiplier": float(round(effective_multiplier, 6)),
        "max_step": float(round(max_step, 6)),
        "size_action": str(_coerce_text(matched_row.get("size_action"))),
        "health_state": str(_coerce_text(matched_row.get("health_state"))),
        "setup_key": str(_coerce_text(matched_row.get("setup_key"))),
        "scene_key": str(_coerce_text(matched_row.get("scene_key")) or symbol_u),
        "coverage_state": str(_coerce_text(matched_row.get("coverage_state"))),
        "top_alert_type": str(_coerce_text(matched_row.get("top_alert_type"))),
        "candidate_type": str(_coerce_text(matched_row.get("candidate_type"))),
        "evidence_count": int(_coerce_float(matched_row.get("evidence_count"), 0.0)),
        "priority_score": float(round(_coerce_float(matched_row.get("priority_score"), 0.0), 4)),
        "one_line": " | ".join(
            [
                symbol_u or "UNKNOWN",
                mode,
                gate_reason,
                f"{round(current_multiplier, 2)}->{round(target_multiplier, 2)}",
            ]
        ),
    }
