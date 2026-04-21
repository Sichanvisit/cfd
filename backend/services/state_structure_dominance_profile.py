from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.runtime_readonly_surface import (
    RUNTIME_READONLY_SURFACE_CONTRACT_VERSION,
    attach_runtime_readonly_surface_fields_v1,
    build_runtime_readonly_surface_row_v1,
)


STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION = "state_structure_dominance_contract_v1"
STATE_STRUCTURE_DOMINANCE_SUMMARY_VERSION = "state_structure_dominance_summary_v1"
DOMINANCE_MODE_ENUM_V1 = (
    "CONTINUATION",
    "CONTINUATION_WITH_FRICTION",
    "BOUNDARY",
    "REVERSAL_RISK",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_state_structure_dominance_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
        "status": "READY",
        "dominance_mode_enum_v1": list(DOMINANCE_MODE_ENUM_V1),
        "dominance_gap_definition_v1": "continuation_integrity - reversal_evidence",
        "row_level_fields_v1": [
            "state_structure_dominance_profile_v1",
            "dominance_shadow_dominant_side_v1",
            "dominance_shadow_dominant_mode_v1",
            "dominance_shadow_caution_level_v1",
            "dominance_shadow_gap_v1",
            "local_continuation_discount_v1",
            "would_override_caution_v1",
            "dominance_reason_summary_v1",
        ],
        "description": (
            "Shadow-only dominance resolver built on top of state strength, local structure, and "
            "runtime read-only surface. Does not change execution or state25 behavior."
        ),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_runtime_readonly(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    upstream_flat_present = any(
        key in row
        for key in (
            "state_strength_side_seed_v1",
            "state_strength_dominant_side_v1",
            "state_strength_dominance_gap_v1",
            "few_candle_higher_low_state_v1",
            "few_candle_structure_bias_v1",
            "consumer_veto_tier_v1",
        )
    )
    if not isinstance(row.get("runtime_readonly_surface_v1"), Mapping):
        if upstream_flat_present:
            row.update(build_runtime_readonly_surface_row_v1(row))
        else:
            row = dict(attach_runtime_readonly_surface_fields_v1({"_": row}).get("_", row))
    return row


def _hold_supports_continuation(row: Mapping[str, Any], *, side_seed: str) -> bool:
    if side_seed == "BULL":
        return _safe_text(row.get("few_candle_higher_low_state_v1")).upper() in {"HELD", "CLEAN_HELD"}
    if side_seed == "BEAR":
        return _safe_text(row.get("few_candle_lower_high_state_v1")).upper() in {"HELD", "CLEAN_HELD"}
    return False


def _local_continuation_discount(row: Mapping[str, Any]) -> float:
    side_seed = _safe_text(row.get("state_strength_side_seed_v1")).upper()
    reversal_evidence = _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    veto_tier = _safe_text(row.get("consumer_veto_tier_v1")).upper()
    breakout_hold_quality = _safe_text(row.get("breakout_hold_quality_v1")).upper()
    body_drive_state = _safe_text(row.get("body_drive_state_v1")).upper()

    if veto_tier == "REVERSAL_OVERRIDE" or reversal_evidence >= 0.55:
        return 0.0
    if not _hold_supports_continuation(row, side_seed=side_seed):
        return 0.0
    if breakout_hold_quality not in {"STABLE", "STRONG"}:
        return 0.0
    if body_drive_state not in {"WEAK_DRIVE", "STRONG_DRIVE"}:
        return 0.0

    if breakout_hold_quality == "STRONG" and body_drive_state == "STRONG_DRIVE":
        return 0.35
    if breakout_hold_quality == "STRONG" or body_drive_state == "STRONG_DRIVE":
        return 0.25
    return 0.15


def _resolve_dominance_gap(row: Mapping[str, Any]) -> float:
    explicit = row.get("state_strength_dominance_gap_v1")
    if explicit is not None and _safe_text(explicit) != "":
        return round(_safe_float(explicit, 0.0), 4)
    continuation_integrity = _safe_float(row.get("state_strength_continuation_integrity_v1"), 0.0)
    reversal_evidence = _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    return round(continuation_integrity - reversal_evidence, 4)


def _resolve_shadow_mode(row: Mapping[str, Any], *, veto_tier: str, dominance_gap: float, discount: float) -> str:
    reversal_evidence = _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    raw_friction = _safe_float(row.get("state_strength_friction_v1"), 0.0)
    friction = max(0.0, raw_friction - discount)
    if veto_tier == "REVERSAL_OVERRIDE" or reversal_evidence >= 0.55:
        return "REVERSAL_RISK"
    if veto_tier == "BOUNDARY_WARNING" or abs(dominance_gap) <= 0.1:
        return "BOUNDARY"
    if dominance_gap > 0.1 and (veto_tier == "FRICTION_ONLY" or raw_friction >= 0.15 or friction >= 0.15):
        return "CONTINUATION_WITH_FRICTION"
    if dominance_gap > 0.1:
        return "CONTINUATION"
    return "BOUNDARY"


def _resolve_shadow_side(row: Mapping[str, Any], *, veto_tier: str) -> str:
    existing = _safe_text(row.get("state_strength_dominant_side_v1")).upper()
    side_seed = _safe_text(row.get("state_strength_side_seed_v1")).upper()
    if veto_tier != "REVERSAL_OVERRIDE":
        return existing or side_seed or "NONE"
    if existing in {"BULL", "BEAR"}:
        return existing
    if side_seed == "BULL":
        return "BEAR"
    if side_seed == "BEAR":
        return "BULL"
    return "NONE"


def _resolve_caution_level(row: Mapping[str, Any], *, veto_tier: str, dominance_gap: float, discount: float) -> str:
    base = _safe_text(row.get("state_strength_caution_level_v1")).upper()
    friction = max(0.0, _safe_float(row.get("state_strength_friction_v1"), 0.0) - discount)
    if veto_tier == "REVERSAL_OVERRIDE":
        return "HIGH"
    if veto_tier == "BOUNDARY_WARNING":
        return "HIGH" if abs(dominance_gap) < 0.08 else "MEDIUM"
    if friction >= 0.25:
        return "MEDIUM"
    if base in {"LOW", "MEDIUM", "HIGH"}:
        return base
    return "LOW"


def _would_override_caution(row: Mapping[str, Any], *, veto_tier: str, dominance_gap: float, discount: float) -> bool:
    reversal_evidence = _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    return (
        veto_tier == "FRICTION_ONLY"
        and dominance_gap >= 0.2
        and discount >= 0.15
        and reversal_evidence < 0.35
    )


def _reason_summary(
    *,
    side: str,
    mode: str,
    caution: str,
    veto_tier: str,
    dominance_gap: float,
    discount: float,
    would_override: bool,
) -> str:
    return (
        f"side={side}; "
        f"mode={mode}; "
        f"caution={caution}; "
        f"veto={veto_tier}; "
        f"gap={round(dominance_gap, 4)}; "
        f"discount={round(discount, 4)}; "
        f"override={str(bool(would_override)).lower()}"
    )


def build_state_structure_dominance_profile_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_runtime_readonly(row or {})
    veto_tier = _safe_text(payload.get("consumer_veto_tier_v1")).upper() or "FRICTION_ONLY"
    dominance_gap = _resolve_dominance_gap(payload)
    discount = round(_local_continuation_discount(payload), 4)
    dominant_mode = _resolve_shadow_mode(payload, veto_tier=veto_tier, dominance_gap=dominance_gap, discount=discount)
    dominant_side = _resolve_shadow_side(payload, veto_tier=veto_tier)
    caution_level = _resolve_caution_level(payload, veto_tier=veto_tier, dominance_gap=dominance_gap, discount=discount)
    would_override = _would_override_caution(payload, veto_tier=veto_tier, dominance_gap=dominance_gap, discount=discount)
    reason_summary = _reason_summary(
        side=dominant_side,
        mode=dominant_mode,
        caution=caution_level,
        veto_tier=veto_tier,
        dominance_gap=dominance_gap,
        discount=discount,
        would_override=would_override,
    )

    profile = {
        "contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
        "runtime_readonly_contract_version": RUNTIME_READONLY_SURFACE_CONTRACT_VERSION,
        "dominance_shadow_dominant_side_v1": dominant_side,
        "dominance_shadow_dominant_mode_v1": dominant_mode,
        "dominance_shadow_caution_level_v1": caution_level,
        "dominance_shadow_gap_v1": dominance_gap,
        "local_continuation_discount_v1": discount,
        "would_override_caution_v1": bool(would_override),
        "dominance_reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "state_structure_dominance_profile_v1": profile,
        "dominance_shadow_dominant_side_v1": dominant_side,
        "dominance_shadow_dominant_mode_v1": dominant_mode,
        "dominance_shadow_caution_level_v1": caution_level,
        "dominance_shadow_gap_v1": dominance_gap,
        "local_continuation_discount_v1": discount,
        "would_override_caution_v1": bool(would_override),
        "dominance_reason_summary_v1": reason_summary,
    }


def attach_state_structure_dominance_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_runtime_readonly(raw)
        row.update(build_state_structure_dominance_profile_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_state_structure_dominance_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_state_structure_dominance_fields_v1(latest_signal_by_symbol)
    side_counts = Counter()
    mode_counts = Counter()
    caution_counts = Counter()
    override_counts = Counter()
    discount_counts = Counter()
    surface_ready_count = 0

    for row in rows_by_symbol.values():
        if isinstance(row.get("state_structure_dominance_profile_v1"), Mapping):
            surface_ready_count += 1
        side_counts.update([_safe_text(row.get("dominance_shadow_dominant_side_v1"))])
        mode_counts.update([_safe_text(row.get("dominance_shadow_dominant_mode_v1"))])
        caution_counts.update([_safe_text(row.get("dominance_shadow_caution_level_v1"))])
        override_counts.update(["OVERRIDE" if _safe_bool(row.get("would_override_caution_v1")) else "KEEP"])
        discount_counts.update(["DISCOUNTED" if _safe_float(row.get("local_continuation_discount_v1"), 0.0) > 0.0 else "NONE"])

    status = "READY" if rows_by_symbol and surface_ready_count == len(rows_by_symbol) else "HOLD"
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["dominance_shadow_surface_available"]
            if status == "READY"
            else ["dominance_shadow_surface_missing_or_no_rows"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "surface_ready_count": int(surface_ready_count),
        "dominant_side_count_summary": dict(side_counts),
        "dominant_mode_count_summary": dict(mode_counts),
        "caution_level_count_summary": dict(caution_counts),
        "would_override_caution_count_summary": dict(override_counts),
        "discount_applied_count_summary": dict(discount_counts),
    }
    return {
        "contract_version": STATE_STRUCTURE_DOMINANCE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_structure_dominance_summary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Structure Dominance Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- surface_ready_count: `{int(summary.get('surface_ready_count', 0) or 0)}`",
        "",
        "## Dominant Mode Count",
        "",
    ]
    for key, count in dict(summary.get("dominant_mode_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: side={row.get('dominance_shadow_dominant_side_v1', '')} | "
            f"mode={row.get('dominance_shadow_dominant_mode_v1', '')} | "
            f"caution={row.get('dominance_shadow_caution_level_v1', '')} | "
            f"discount={row.get('local_continuation_discount_v1', '')} | "
            f"override={row.get('would_override_caution_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_structure_dominance_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_structure_dominance_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "state_structure_dominance_summary_latest.json"
    md_path = output_dir / "state_structure_dominance_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_state_structure_dominance_summary_markdown_v1(report))
    return report
