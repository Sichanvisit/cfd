from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.symbol_specific_state_strength_calibration import (
    attach_symbol_specific_state_strength_calibration_fields_v1,
)


XAU_READONLY_SURFACE_CONTRACT_VERSION = "xau_readonly_surface_contract_v1"
XAU_READONLY_SURFACE_SUMMARY_VERSION = "xau_readonly_surface_summary_v1"

XAU_PILOT_WINDOW_MATCH_ENUM_V1 = (
    "MATCHED_ACTIVE_PROFILE",
    "PARTIAL_ACTIVE_PROFILE",
    "REVIEW_PENDING",
    "OUT_OF_PROFILE",
    "NOT_APPLICABLE",
)
XAU_REJECTION_TYPE_ENUM_V1 = ("NONE", "FRICTION_REJECTION", "REVERSAL_REJECTION")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_xau_readonly_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": XAU_READONLY_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "XAU-specific read-only surface for the common state polarity decomposition frame. "
            "Surfaces polarity, intent, stage, rejection split, texture, location, tempo, and ambiguity "
            "for XAU runtime rows without changing dominance or execution."
        ),
        "pilot_window_match_enum_v1": list(XAU_PILOT_WINDOW_MATCH_ENUM_V1),
        "xau_rejection_type_enum_v1": list(XAU_REJECTION_TYPE_ENUM_V1),
        "row_level_fields_v1": [
            "xau_readonly_surface_profile_v1",
            "xau_polarity_slot_v1",
            "xau_intent_slot_v1",
            "xau_continuation_stage_v1",
            "xau_rejection_type_v1",
            "xau_texture_slot_v1",
            "xau_location_context_v1",
            "xau_tempo_profile_v1",
            "xau_ambiguity_level_v1",
            "xau_state_slot_core_v1",
            "xau_state_slot_modifier_bundle_v1",
            "xau_pilot_window_match_v1",
            "xau_surface_reason_summary_v1",
        ],
        "control_rules_v1": [
            "xau readonly surface exists to make the common decomposition frame visible on XAU rows",
            "xau readonly surface cannot change dominant_side",
            "xau readonly surface remains read-only and cannot change execution or state25",
            "rejection type is split into friction rejection or reversal rejection before any policy bridge",
            "slot core remains polarity plus intent plus stage while texture, location, tempo, and ambiguity remain modifiers",
        ],
        "dominance_protection_v1": {
            "xau_readonly_surface_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_xau_validation_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def _ensure_symbol_profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("symbol_specific_state_strength_profile_v1"), Mapping):
        return row
    minimal_flat_fields = (
        "symbol_state_strength_best_profile_key_v1",
        "symbol_state_strength_profile_status_v1",
        "symbol_state_strength_profile_match_v1",
    )
    if all(key in row and _text(row.get(key)) for key in minimal_flat_fields):
        return row
    required_flat_fields = (
        "symbol_state_strength_best_profile_key_v1",
        "symbol_state_strength_profile_status_v1",
        "symbol_state_strength_profile_match_v1",
        "symbol_state_strength_aggregate_conviction_v1",
        "symbol_state_strength_flow_persistence_v1",
        "symbol_state_strength_flow_support_state_v1",
    )
    if all(key in row and _text(row.get(key)) for key in required_flat_fields):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or row.get("name")) or "_"
    enriched = attach_symbol_specific_state_strength_calibration_fields_v1({symbol: row})
    return dict(enriched.get(symbol, row))


def _resolve_polarity_and_intent(row: Mapping[str, Any]) -> tuple[str, str]:
    profile_key = _text(row.get("symbol_state_strength_best_profile_key_v1")).upper()
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()

    if "XAUUSD_UP_CONTINUATION_RECOVERY_V1" in profile_key:
        return "BULL", "RECOVERY"
    if "XAUUSD_DOWN_CONTINUATION_REJECTION_V1" in profile_key:
        return "BEAR", "REJECTION"
    if "rebound" in consumer_reason or box_state == "BELOW" or bb_state == "LOWER_EDGE":
        return "BULL", "RECOVERY"
    if "reject" in consumer_reason or previous_box_break_state == "BREAKDOWN_HELD":
        return "BEAR", "REJECTION"
    return "NONE", "BOUNDARY"


def _resolve_stage(row: Mapping[str, Any], *, intent: str) -> str:
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()

    if previous_box_break_state in {"BREAKOUT_HELD", "BREAKDOWN_HELD"} and "probe" not in consumer_reason:
        if bb_state in {"UPPER_EDGE", "LOWER_EDGE"} and box_state in {"ABOVE", "BELOW"}:
            return "ACCEPTANCE"
    if bb_state in {"UPPER", "LOWER"} and box_state in {"ABOVE", "BELOW"} and "probe" not in consumer_reason:
        return "EXTENSION"
    if intent in {"RECOVERY", "REJECTION"}:
        return "INITIATION" if "probe" in consumer_reason else "ACCEPTANCE"
    return "NONE"


def _resolve_rejection_type(row: Mapping[str, Any], *, intent: str) -> str:
    if intent != "REJECTION":
        return "NONE"
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    if previous_box_break_state == "BREAKDOWN_HELD":
        return "REVERSAL_REJECTION"
    if "reject" in consumer_reason or "probe" in consumer_reason:
        return "FRICTION_REJECTION"
    return "NONE"


def _resolve_location(row: Mapping[str, Any]) -> str:
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()
    if previous_box_break_state in {"BREAKOUT_HELD", "BREAKDOWN_HELD"}:
        return "POST_BREAKOUT"
    if box_state in {"ABOVE", "BELOW"} and bb_state in {"UPPER_EDGE", "LOWER_EDGE", "UPPER", "LOWER"}:
        return "AT_EDGE"
    if bb_state in {"UPPER", "LOWER"}:
        return "EXTENDED"
    return "IN_BOX"


def _resolve_tempo(row: Mapping[str, Any], *, stage: str, rejection_type: str) -> str:
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    if rejection_type != "NONE" and "probe" not in consumer_reason:
        return "REPEATING"
    if stage == "INITIATION":
        return "EARLY"
    if stage == "EXTENSION":
        return "EXTENDED"
    return "PERSISTING"


def _resolve_texture(row: Mapping[str, Any], *, rejection_type: str, tempo: str) -> str:
    dominant_mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    if dominant_mode == "CONTINUATION_WITH_FRICTION" or rejection_type == "FRICTION_REJECTION":
        return "WITH_FRICTION"
    if tempo == "REPEATING" or dominant_mode == "BOUNDARY":
        return "DRIFT"
    return "CLEAN"


def _resolve_ambiguity(row: Mapping[str, Any], *, intent: str, rejection_type: str) -> str:
    dominant_mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    profile_match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    if dominant_mode == "BOUNDARY":
        return "HIGH"
    if profile_match == "PARTIAL_MATCH" or rejection_type == "FRICTION_REJECTION" or intent == "BOUNDARY":
        return "MEDIUM"
    return "LOW"


def _resolve_window_match(row: Mapping[str, Any]) -> str:
    profile_status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    profile_match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    if profile_status == "ACTIVE_CANDIDATE" and profile_match == "MATCH":
        return "MATCHED_ACTIVE_PROFILE"
    if profile_status == "ACTIVE_CANDIDATE" and profile_match == "PARTIAL_MATCH":
        return "PARTIAL_ACTIVE_PROFILE"
    if profile_status == "SEPARATE_PENDING":
        return "REVIEW_PENDING"
    return "OUT_OF_PROFILE"


def build_xau_readonly_surface_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_symbol_profile(row or {})
    symbol = _text(payload.get("symbol")).upper()
    if symbol != "XAUUSD":
        profile = {
            "contract_version": XAU_READONLY_SURFACE_CONTRACT_VERSION,
            "applicable_v1": False,
            "xau_pilot_window_match_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "xau_readonly_surface_profile_v1": profile,
            "xau_polarity_slot_v1": "",
            "xau_intent_slot_v1": "",
            "xau_continuation_stage_v1": "",
            "xau_rejection_type_v1": "NONE",
            "xau_texture_slot_v1": "",
            "xau_location_context_v1": "",
            "xau_tempo_profile_v1": "",
            "xau_ambiguity_level_v1": "",
            "xau_state_slot_core_v1": "",
            "xau_state_slot_modifier_bundle_v1": [],
            "xau_pilot_window_match_v1": "NOT_APPLICABLE",
            "xau_surface_reason_summary_v1": "symbol_not_xau",
        }

    polarity, intent = _resolve_polarity_and_intent(payload)
    stage = _resolve_stage(payload, intent=intent)
    rejection_type = _resolve_rejection_type(payload, intent=intent)
    location = _resolve_location(payload)
    tempo = _resolve_tempo(payload, stage=stage, rejection_type=rejection_type)
    texture = _resolve_texture(payload, rejection_type=rejection_type, tempo=tempo)
    ambiguity = _resolve_ambiguity(payload, intent=intent, rejection_type=rejection_type)
    window_match = _resolve_window_match(payload)
    state_slot_core = f"{polarity}_{intent}_{stage}" if polarity != "NONE" and intent != "BOUNDARY" and stage != "NONE" else ""
    modifier_bundle = [value for value in (texture, location, tempo, f"AMBIGUITY_{ambiguity}" if ambiguity else "") if value]
    reason_summary = (
        f"profile={_text(payload.get('symbol_state_strength_best_profile_key_v1')) or 'none'}; "
        f"match={window_match}; polarity={polarity}; intent={intent}; stage={stage}; "
        f"rejection={rejection_type}; texture={texture}; location={location}; tempo={tempo}; ambiguity={ambiguity}"
    )
    profile = {
        "contract_version": XAU_READONLY_SURFACE_CONTRACT_VERSION,
        "applicable_v1": True,
        "source_profile_key_v1": _text(payload.get("symbol_state_strength_best_profile_key_v1")),
        "xau_polarity_slot_v1": polarity,
        "xau_intent_slot_v1": intent,
        "xau_continuation_stage_v1": stage,
        "xau_rejection_type_v1": rejection_type,
        "xau_texture_slot_v1": texture,
        "xau_location_context_v1": location,
        "xau_tempo_profile_v1": tempo,
        "xau_ambiguity_level_v1": ambiguity,
        "xau_state_slot_core_v1": state_slot_core,
        "xau_state_slot_modifier_bundle_v1": list(modifier_bundle),
        "xau_pilot_window_match_v1": window_match,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "xau_readonly_surface_profile_v1": profile,
        "xau_polarity_slot_v1": polarity,
        "xau_intent_slot_v1": intent,
        "xau_continuation_stage_v1": stage,
        "xau_rejection_type_v1": rejection_type,
        "xau_texture_slot_v1": texture,
        "xau_location_context_v1": location,
        "xau_tempo_profile_v1": tempo,
        "xau_ambiguity_level_v1": ambiguity,
        "xau_state_slot_core_v1": state_slot_core,
        "xau_state_slot_modifier_bundle_v1": list(modifier_bundle),
        "xau_pilot_window_match_v1": window_match,
        "xau_surface_reason_summary_v1": reason_summary,
    }


def attach_xau_readonly_surface_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_symbol_profile(raw)
        row.update(build_xau_readonly_surface_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_xau_readonly_surface_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_xau_readonly_surface_fields_v1(latest_signal_by_symbol)
    xau_rows = {symbol: row for symbol, row in rows_by_symbol.items() if _text(row.get("symbol")).upper() == "XAUUSD"}
    core_counts = Counter()
    texture_counts = Counter()
    match_counts = Counter()
    applicable_count = 0
    for row in xau_rows.values():
        if isinstance(row.get("xau_readonly_surface_profile_v1"), Mapping):
            applicable_count += 1
        core_counts.update([_text(row.get("xau_state_slot_core_v1"))])
        texture_counts.update([_text(row.get("xau_texture_slot_v1"))])
        match_counts.update([_text(row.get("xau_pilot_window_match_v1"))])
    status = "READY" if xau_rows and applicable_count == len(xau_rows) else "HOLD"
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["xau_readonly_surface_available"] if status == "READY" else ["xau_row_missing_or_surface_incomplete"]
        ),
        "xau_row_count": int(len(xau_rows)),
        "surface_ready_count": int(applicable_count),
        "state_slot_core_count_summary": dict(core_counts),
        "texture_slot_count_summary": dict(texture_counts),
        "pilot_window_match_count_summary": dict(match_counts),
    }
    return {
        "contract_version": XAU_READONLY_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_xau_readonly_surface_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# XAU Read-only Surface v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- xau_row_count: `{int(summary.get('xau_row_count', 0) or 0)}`",
        f"- surface_ready_count: `{int(summary.get('surface_ready_count', 0) or 0)}`",
        "",
        "## XAU Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "XAUUSD":
            continue
        lines.append(
            f"- `{symbol}`: core={row.get('xau_state_slot_core_v1', '')} | "
            f"texture={row.get('xau_texture_slot_v1', '')} | "
            f"location={row.get('xau_location_context_v1', '')} | "
            f"tempo={row.get('xau_tempo_profile_v1', '')} | "
            f"match={row.get('xau_pilot_window_match_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_xau_readonly_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_xau_readonly_surface_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "xau_readonly_surface_latest.json"
    md_path = output_dir / "xau_readonly_surface_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_xau_readonly_surface_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
