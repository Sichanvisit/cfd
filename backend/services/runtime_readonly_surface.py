from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.local_structure_profile_contract import (
    LOCAL_STRUCTURE_PROFILE_CONTRACT_VERSION,
    build_local_structure_profile_row_v1,
)
from backend.services.state_strength_profile_contract import (
    STATE_STRENGTH_PROFILE_CONTRACT_VERSION,
    build_state_strength_profile_row_v1,
)


RUNTIME_READONLY_SURFACE_CONTRACT_VERSION = "runtime_readonly_surface_contract_v1"
RUNTIME_READONLY_SURFACE_SUMMARY_VERSION = "runtime_readonly_surface_summary_v1"
CONSUMER_VETO_TIER_ENUM_V1 = ("FRICTION_ONLY", "BOUNDARY_WARNING", "REVERSAL_OVERRIDE")


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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_runtime_readonly_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": RUNTIME_READONLY_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "consumer_veto_tier_enum_v1": list(CONSUMER_VETO_TIER_ENUM_V1),
        "row_level_fields_v1": [
            "state_strength_profile_v1",
            "local_structure_profile_v1",
            "consumer_veto_tier_v1",
            "consumer_veto_reason_summary_v1",
            "runtime_readonly_surface_v1",
        ],
        "description": (
            "Read-only runtime surface that combines state strength and local structure and surfaces "
            "a shared consumer veto tier without changing execution or state25 behavior."
        ),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_profiles(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    state_strength_flat_present = any(
        key in row
        for key in (
            "state_strength_side_seed_v1",
            "state_strength_dominant_side_v1",
            "state_strength_dominant_mode_v1",
            "state_strength_dominance_gap_v1",
            "state_strength_continuation_integrity_v1",
            "state_strength_reversal_evidence_v1",
            "state_strength_friction_v1",
            "state_strength_caution_level_v1",
        )
    )
    local_structure_flat_present = any(
        key in row
        for key in (
            "few_candle_higher_low_state_v1",
            "few_candle_lower_high_state_v1",
            "breakout_hold_quality_v1",
            "body_drive_state_v1",
            "few_candle_structure_bias_v1",
        )
    )

    if not isinstance(row.get("state_strength_profile_v1"), Mapping) and not state_strength_flat_present:
        row.update(build_state_strength_profile_row_v1(row))
    elif not isinstance(row.get("state_strength_profile_v1"), Mapping):
        row["state_strength_profile_v1"] = {
            "contract_version": STATE_STRENGTH_PROFILE_CONTRACT_VERSION,
            "side_seed_v1": _safe_text(row.get("state_strength_side_seed_v1")).upper(),
            "dominant_side_v1": _safe_text(row.get("state_strength_dominant_side_v1")).upper(),
            "dominant_mode_v1": _safe_text(row.get("state_strength_dominant_mode_v1")).upper(),
            "dominance_gap_v1": round(_safe_float(row.get("state_strength_dominance_gap_v1"), 0.0), 4),
            "continuation_integrity_v1": round(_safe_float(row.get("state_strength_continuation_integrity_v1"), 0.0), 4),
            "reversal_evidence_v1": round(_safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0), 4),
            "friction_v1": round(_safe_float(row.get("state_strength_friction_v1"), 0.0), 4),
            "caution_level_v1": _safe_text(row.get("state_strength_caution_level_v1")).upper(),
        }

    if not isinstance(row.get("local_structure_profile_v1"), Mapping) and not local_structure_flat_present:
        row.update(build_local_structure_profile_row_v1(row))
    elif not isinstance(row.get("local_structure_profile_v1"), Mapping):
        row["local_structure_profile_v1"] = {
            "contract_version": LOCAL_STRUCTURE_PROFILE_CONTRACT_VERSION,
            "few_candle_higher_low_state_v1": _safe_text(row.get("few_candle_higher_low_state_v1")).upper(),
            "few_candle_lower_high_state_v1": _safe_text(row.get("few_candle_lower_high_state_v1")).upper(),
            "breakout_hold_quality_v1": _safe_text(row.get("breakout_hold_quality_v1")).upper(),
            "body_drive_state_v1": _safe_text(row.get("body_drive_state_v1")).upper(),
            "few_candle_structure_bias_v1": _safe_text(row.get("few_candle_structure_bias_v1")).upper(),
        }
    return row


def _resolve_consumer_veto_tier(row: Mapping[str, Any]) -> tuple[str, str]:
    continuation_integrity = _safe_float(row.get("state_strength_continuation_integrity_v1"), 0.0)
    reversal_evidence = _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    friction = _safe_float(row.get("state_strength_friction_v1"), 0.0)
    dominant_mode = _safe_text(row.get("state_strength_dominant_mode_v1")).upper()
    caution_level = _safe_text(row.get("state_strength_caution_level_v1")).upper()
    structure_bias = _safe_text(row.get("few_candle_structure_bias_v1")).upper()
    breakout_hold_quality = _safe_text(row.get("breakout_hold_quality_v1")).upper()
    body_drive_state = _safe_text(row.get("body_drive_state_v1")).upper()
    consumer_check_reason = _safe_text(row.get("consumer_check_reason")).lower()
    blocked_by = _safe_text(row.get("blocked_by")).lower()

    reversal_structure = (
        structure_bias == "REVERSAL_FAVOR"
        or breakout_hold_quality == "FAILED"
        or body_drive_state == "COUNTER_DRIVE"
    )
    boundary_structure = (
        structure_bias == "MIXED"
        or breakout_hold_quality in {"WEAK", "FAILED"}
        or body_drive_state == "NEUTRAL"
        or caution_level == "HIGH"
    )
    friction_signal = (
        dominant_mode == "CONTINUATION_WITH_FRICTION"
        or friction >= 0.25
        or "upper_reject" in consumer_check_reason
        or "outer_band_reversal_support_required_observe" in consumer_check_reason
        or blocked_by in {"energy_soft_block", "active_action_conflict_guard"}
    )

    if (
        (dominant_mode == "REVERSAL_RISK" or reversal_evidence >= 0.55)
        and reversal_structure
        and continuation_integrity <= 0.45
    ):
        return (
            "REVERSAL_OVERRIDE",
            "reversal_evidence_high_with_structure_break",
        )
    if dominant_mode == "BOUNDARY" or (boundary_structure and reversal_evidence >= 0.25):
        return (
            "BOUNDARY_WARNING",
            "mixed_structure_or_boundary_mode",
        )
    if friction_signal:
        return (
            "FRICTION_ONLY",
            "continuation_intact_but_entry_friction_present",
        )
    return (
        "FRICTION_ONLY",
        "default_readonly_friction_tier",
    )


def build_runtime_readonly_surface_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_profiles(row or {})
    veto_tier, veto_reason = _resolve_consumer_veto_tier(payload)
    runtime_surface = {
        "contract_version": RUNTIME_READONLY_SURFACE_CONTRACT_VERSION,
        "state_strength_dominant_side_v1": _safe_text(payload.get("state_strength_dominant_side_v1")).upper(),
        "state_strength_dominant_mode_v1": _safe_text(payload.get("state_strength_dominant_mode_v1")).upper(),
        "state_strength_dominance_gap_v1": round(_safe_float(payload.get("state_strength_dominance_gap_v1"), 0.0), 4),
        "few_candle_structure_bias_v1": _safe_text(payload.get("few_candle_structure_bias_v1")).upper(),
        "breakout_hold_quality_v1": _safe_text(payload.get("breakout_hold_quality_v1")).upper(),
        "body_drive_state_v1": _safe_text(payload.get("body_drive_state_v1")).upper(),
        "consumer_veto_tier_v1": veto_tier,
        "consumer_veto_reason_summary_v1": veto_reason,
        "read_only_surface_state_v1": "READY",
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "runtime_readonly_surface_v1": runtime_surface,
        "consumer_veto_tier_v1": veto_tier,
        "consumer_veto_reason_summary_v1": veto_reason,
    }


def attach_runtime_readonly_surface_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_profiles(raw)
        row.update(build_runtime_readonly_surface_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_runtime_readonly_surface_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_runtime_readonly_surface_fields_v1(latest_signal_by_symbol)
    tier_counts = Counter()
    dominant_side_counts = Counter()
    dominant_mode_counts = Counter()
    structure_bias_counts = Counter()
    surface_ready_count = 0

    for row in rows_by_symbol.values():
        if isinstance(row.get("runtime_readonly_surface_v1"), Mapping):
            surface_ready_count += 1
        tier_counts.update([_safe_text(row.get("consumer_veto_tier_v1"))])
        dominant_side_counts.update([_safe_text(row.get("state_strength_dominant_side_v1"))])
        dominant_mode_counts.update([_safe_text(row.get("state_strength_dominant_mode_v1"))])
        structure_bias_counts.update([_safe_text(row.get("few_candle_structure_bias_v1"))])

    status = "READY" if rows_by_symbol and surface_ready_count == len(rows_by_symbol) else "HOLD"
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["runtime_readonly_surface_available"]
            if status == "READY"
            else ["surface_missing_or_no_rows"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "surface_ready_count": int(surface_ready_count),
        "consumer_veto_tier_count_summary": dict(tier_counts),
        "dominant_side_count_summary": dict(dominant_side_counts),
        "dominant_mode_count_summary": dict(dominant_mode_counts),
        "structure_bias_count_summary": dict(structure_bias_counts),
    }
    return {
        "contract_version": RUNTIME_READONLY_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_runtime_readonly_surface_summary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Runtime Read-Only Surface Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- surface_ready_count: `{int(summary.get('surface_ready_count', 0) or 0)}`",
        "",
        "## Consumer Veto Tier Count",
        "",
    ]
    for key, count in dict(summary.get("consumer_veto_tier_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: side={row.get('state_strength_dominant_side_v1', '')} | "
            f"mode={row.get('state_strength_dominant_mode_v1', '')} | "
            f"bias={row.get('few_candle_structure_bias_v1', '')} | "
            f"veto={row.get('consumer_veto_tier_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_runtime_readonly_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_runtime_readonly_surface_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "runtime_readonly_surface_summary_latest.json"
    md_path = output_dir / "runtime_readonly_surface_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_runtime_readonly_surface_summary_markdown_v1(report))
    return report
