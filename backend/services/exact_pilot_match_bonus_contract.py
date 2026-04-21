from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.flow_threshold_provisional_band_contract import (
    FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION,
    attach_flow_threshold_provisional_band_fields_v1,
)
from backend.services.xau_readonly_surface_contract import (
    attach_xau_readonly_surface_fields_v1,
)
from backend.services.nas_readonly_surface_contract import (
    attach_nas_readonly_surface_fields_v1,
)
from backend.services.btc_readonly_surface_contract import (
    attach_btc_readonly_surface_fields_v1,
)


EXACT_PILOT_MATCH_BONUS_CONTRACT_VERSION = "exact_pilot_match_bonus_contract_v1"
EXACT_PILOT_MATCH_BONUS_SUMMARY_VERSION = "exact_pilot_match_bonus_summary_v1"

EXACT_PILOT_MATCH_BONUS_SOURCE_ENUM_V1 = (
    "MATCHED_ACTIVE_PROFILE",
    "PARTIAL_ACTIVE_PROFILE",
    "REVIEW_PENDING",
    "OUT_OF_PROFILE",
    "NOT_APPLICABLE",
    "FALLBACK_MATCH",
    "FALLBACK_PARTIAL",
)
EXACT_PILOT_MATCH_BONUS_EFFECT_ENUM_V1 = (
    "NOT_APPLICABLE",
    "BONUS_BLOCKED",
    "NO_ACTIVE_MATCH",
    "VALIDATION_ONLY",
    "PRIORITY_BOOST",
    "UNCONFIRMED_TO_BUILDING",
    "BUILDING_TO_CONFIRMED",
    "WITHHELD_BY_EXTENSION",
    "WITHHELD_BY_CALIBRATION",
    "WITHHELD_BY_BONUS_CEILING",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_exact_pilot_match_bonus_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": EXACT_PILOT_MATCH_BONUS_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Repositions exact pilot match into a bounded bonus layer that sits below structure and provisional "
            "flow bands. Exact pilot evidence can validate or modestly boost a row, but cannot override "
            "structure blockers or jump unconfirmed rows directly to confirmed."
        ),
        "upstream_contract_versions_v1": [
            FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION,
        ],
        "exact_pilot_match_bonus_source_enum_v1": list(EXACT_PILOT_MATCH_BONUS_SOURCE_ENUM_V1),
        "exact_pilot_match_bonus_effect_enum_v1": list(EXACT_PILOT_MATCH_BONUS_EFFECT_ENUM_V1),
        "row_level_fields_v1": [
            "exact_pilot_match_bonus_profile_v1",
            "exact_pilot_match_bonus_source_v1",
            "exact_pilot_match_bonus_strength_v1",
            "exact_pilot_match_bonus_effect_v1",
            "pilot_match_bonus_applied_v1",
            "pilot_match_bonus_delta_levels_v1",
            "boosted_provisional_flow_band_state_v1",
            "exact_pilot_match_bonus_reason_summary_v1",
        ],
        "control_rules_v1": [
            "exact pilot match is a bonus layer only and cannot replace structure ownership",
            "structure blocked rows cannot receive a boosted provisional state",
            "unconfirmed rows cannot jump directly to confirmed by bonus alone",
            "extension rows cannot be promoted into confirmed by exact match bonus",
            "calibration readiness must be provisional-band-ready before state upgrades are allowed",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("provisional_flow_band_state_v1")):
        row = dict(attach_flow_threshold_provisional_band_fields_v1({"_": row}).get("_", row))

    symbol = _text(row.get("symbol")).upper()
    if symbol == "XAUUSD" and not _text(row.get("xau_pilot_window_match_v1")):
        row = dict(attach_xau_readonly_surface_fields_v1({symbol: row}).get(symbol, row))
    elif symbol == "NAS100" and not _text(row.get("nas_pilot_window_match_v1")):
        row = dict(attach_nas_readonly_surface_fields_v1({symbol: row}).get(symbol, row))
    elif symbol == "BTCUSD" and not _text(row.get("btc_pilot_window_match_v1")):
        row = dict(attach_btc_readonly_surface_fields_v1({symbol: row}).get(symbol, row))
    return row


def _gate_state(row: Mapping[str, Any]) -> str:
    return _text(row.get("aggregate_flow_structure_gate_v1") or row.get("flow_structure_gate_v1")).upper()


def _provisional_state(row: Mapping[str, Any]) -> str:
    return _text(row.get("provisional_flow_band_state_v1")).upper() or "NOT_APPLICABLE"


def _stage(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_continuation_stage_v1")
        or row.get("xau_continuation_stage_v1")
        or row.get("nas_continuation_stage_v1")
        or row.get("btc_continuation_stage_v1")
        or row.get("flow_structure_gate_stage_v1")
    ).upper()


def _bonus_strength(row: Mapping[str, Any]) -> str:
    nested = _mapping(row.get("retained_window_flow_calibration_profile_v1"))
    value = _text(
        row.get("exact_match_bonus_strength_v1")
        or nested.get("exact_match_bonus_strength_v1")
    ).upper()
    return value or "LOW"


def _calibration_state(row: Mapping[str, Any]) -> str:
    return _text(row.get("retained_window_calibration_state_v1")).upper()


def _fallback_source(row: Mapping[str, Any]) -> str:
    status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    if status == "ACTIVE_CANDIDATE" and match == "MATCH":
        return "FALLBACK_MATCH"
    if status == "ACTIVE_CANDIDATE" and match == "PARTIAL_MATCH":
        return "FALLBACK_PARTIAL"
    if match == "SEPARATE_PENDING" or status == "SEPARATE_PENDING":
        return "REVIEW_PENDING"
    if match in {"OUT_OF_PROFILE", "UNCONFIGURED"}:
        return "OUT_OF_PROFILE"
    return "NOT_APPLICABLE"


def _bonus_source(row: Mapping[str, Any]) -> str:
    symbol = _text(row.get("symbol")).upper()
    if symbol == "XAUUSD":
        source = _text(row.get("xau_pilot_window_match_v1")).upper()
    elif symbol == "NAS100":
        source = _text(row.get("nas_pilot_window_match_v1")).upper()
    elif symbol == "BTCUSD":
        source = _text(row.get("btc_pilot_window_match_v1")).upper()
    else:
        source = ""
    return source or _fallback_source(row)


def _strength_value(strength: str) -> int:
    return {
        "NONE": -1,
        "LOW": 0,
        "LOW_MEDIUM": 1,
        "MEDIUM": 2,
        "HIGH": 3,
    }.get(_text(strength).upper(), 0)


def _is_full_match(source: str) -> bool:
    return source in {"MATCHED_ACTIVE_PROFILE", "FALLBACK_MATCH"}


def _is_partial_match(source: str) -> bool:
    return source in {"PARTIAL_ACTIVE_PROFILE", "FALLBACK_PARTIAL"}


def _reason_summary(
    *,
    source: str,
    strength: str,
    gate: str,
    calibration_state: str,
    stage: str,
    base_state: str,
    boosted_state: str,
    effect: str,
) -> str:
    return (
        f"source={source}; "
        f"strength={strength}; "
        f"gate={gate}; "
        f"calibration={calibration_state or 'UNKNOWN'}; "
        f"stage={stage or 'NONE'}; "
        f"base={base_state}; "
        f"boosted={boosted_state}; "
        f"effect={effect}"
    )


def build_exact_pilot_match_bonus_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    gate = _gate_state(payload)
    base_state = _provisional_state(payload)
    stage = _stage(payload)
    calibration_state = _calibration_state(payload)
    source = _bonus_source(payload)
    strength = _bonus_strength(payload)
    strength_value = _strength_value(strength)

    boosted_state = base_state
    effect = "NOT_APPLICABLE"
    applied = False
    delta_levels = 0

    if base_state == "NOT_APPLICABLE":
        effect = "NOT_APPLICABLE"
    elif gate not in {"ELIGIBLE", "WEAK"} or base_state == "STRUCTURE_BLOCKED":
        effect = "BONUS_BLOCKED"
        boosted_state = "STRUCTURE_BLOCKED"
    elif source in {"NOT_APPLICABLE", "OUT_OF_PROFILE", "REVIEW_PENDING"}:
        effect = "NO_ACTIVE_MATCH"
    elif stage == "EXTENSION":
        if base_state in {"CONFIRMED_CANDIDATE", "BUILDING_CANDIDATE"}:
            effect = "PRIORITY_BOOST" if base_state == "BUILDING_CANDIDATE" else "VALIDATION_ONLY"
            applied = True
        else:
            effect = "WITHHELD_BY_EXTENSION"
    elif calibration_state != "PROVISIONAL_BAND_READY":
        if base_state == "CONFIRMED_CANDIDATE":
            effect = "VALIDATION_ONLY"
            applied = True
        elif base_state == "BUILDING_CANDIDATE":
            effect = "PRIORITY_BOOST"
            applied = True
        else:
            effect = "WITHHELD_BY_CALIBRATION"
    elif base_state == "CONFIRMED_CANDIDATE":
        effect = "VALIDATION_ONLY"
        applied = True
    elif base_state == "BUILDING_CANDIDATE":
        if _is_full_match(source) and strength_value >= 1:
            boosted_state = "CONFIRMED_CANDIDATE"
            effect = "BUILDING_TO_CONFIRMED"
            applied = True
            delta_levels = 1
        else:
            effect = "PRIORITY_BOOST"
            applied = True
    elif base_state == "UNCONFIRMED_CANDIDATE":
        if (_is_full_match(source) and strength_value >= 0) or (_is_partial_match(source) and strength_value >= 2):
            boosted_state = "BUILDING_CANDIDATE"
            effect = "UNCONFIRMED_TO_BUILDING"
            applied = True
            delta_levels = 1
        else:
            effect = "WITHHELD_BY_BONUS_CEILING"
    else:
        effect = "NO_ACTIVE_MATCH"

    reason = _reason_summary(
        source=source,
        strength=strength,
        gate=gate,
        calibration_state=calibration_state,
        stage=stage,
        base_state=base_state,
        boosted_state=boosted_state,
        effect=effect,
    )

    profile = {
        "contract_version": EXACT_PILOT_MATCH_BONUS_CONTRACT_VERSION,
        "upstream_flow_threshold_contract_version_v1": FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION,
        "exact_pilot_match_bonus_source_v1": source,
        "exact_pilot_match_bonus_strength_v1": strength,
        "exact_pilot_match_bonus_effect_v1": effect,
        "pilot_match_bonus_applied_v1": applied,
        "pilot_match_bonus_delta_levels_v1": delta_levels,
        "boosted_provisional_flow_band_state_v1": boosted_state,
        "exact_pilot_match_bonus_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "exact_pilot_match_bonus_profile_v1": profile,
        "exact_pilot_match_bonus_source_v1": source,
        "exact_pilot_match_bonus_strength_v1": strength,
        "exact_pilot_match_bonus_effect_v1": effect,
        "pilot_match_bonus_applied_v1": applied,
        "pilot_match_bonus_delta_levels_v1": delta_levels,
        "boosted_provisional_flow_band_state_v1": boosted_state,
        "exact_pilot_match_bonus_reason_summary_v1": reason,
    }


def attach_exact_pilot_match_bonus_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_exact_pilot_match_bonus_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_exact_pilot_match_bonus_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_exact_pilot_match_bonus_fields_v1(latest_signal_by_symbol)
    source_counts = Counter()
    strength_counts = Counter()
    effect_counts = Counter()
    boosted_counts = Counter()
    symbol_count = len(rows_by_symbol)

    for row in rows_by_symbol.values():
        source_counts.update([_text(row.get("exact_pilot_match_bonus_source_v1"))])
        strength_counts.update([_text(row.get("exact_pilot_match_bonus_strength_v1"))])
        effect_counts.update([_text(row.get("exact_pilot_match_bonus_effect_v1"))])
        boosted_counts.update([_text(row.get("boosted_provisional_flow_band_state_v1"))])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["exact_pilot_match_bonus_surface_available"] if symbol_count else ["no_rows_for_exact_pilot_match_bonus"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "exact_pilot_match_bonus_source_count_summary": dict(source_counts),
        "exact_pilot_match_bonus_strength_count_summary": dict(strength_counts),
        "exact_pilot_match_bonus_effect_count_summary": dict(effect_counts),
        "boosted_provisional_flow_band_state_count_summary": dict(boosted_counts),
    }
    return {
        "contract_version": EXACT_PILOT_MATCH_BONUS_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_exact_pilot_match_bonus_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Exact Pilot Match Bonus",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- exact_pilot_match_bonus_source_count_summary: {json.dumps(summary.get('exact_pilot_match_bonus_source_count_summary', {}), ensure_ascii=False)}",
        f"- exact_pilot_match_bonus_effect_count_summary: {json.dumps(summary.get('exact_pilot_match_bonus_effect_count_summary', {}), ensure_ascii=False)}",
        f"- boosted_provisional_flow_band_state_count_summary: {json.dumps(summary.get('boosted_provisional_flow_band_state_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: source={row.get('exact_pilot_match_bonus_source_v1', '')}, "
            f"effect={row.get('exact_pilot_match_bonus_effect_v1', '')}, "
            f"boosted={row.get('boosted_provisional_flow_band_state_v1', '')}, "
            f"strength={row.get('exact_pilot_match_bonus_strength_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_exact_pilot_match_bonus_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_exact_pilot_match_bonus_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "exact_pilot_match_bonus_latest.json"
    markdown_path = output_dir / "exact_pilot_match_bonus_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_exact_pilot_match_bonus_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
