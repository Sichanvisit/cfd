from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.state_slot_symbol_extension_surface import (
    attach_state_slot_symbol_extension_surface_fields_v1,
)


BTC_READONLY_SURFACE_CONTRACT_VERSION = "btc_readonly_surface_contract_v1"
BTC_READONLY_SURFACE_SUMMARY_VERSION = "btc_readonly_surface_summary_v1"

BTC_PILOT_WINDOW_MATCH_ENUM_V1 = (
    "MATCHED_ACTIVE_PROFILE",
    "PARTIAL_ACTIVE_PROFILE",
    "REVIEW_PENDING",
    "OUT_OF_PROFILE",
    "NOT_APPLICABLE",
)


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


def build_btc_readonly_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BTC_READONLY_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "BTC-specific read-only surface for the common decomposition frame. Re-exposes common slot fields with "
            "BTC-prefixed names so BTC rows can be reviewed like XAU pilot rows."
        ),
        "pilot_window_match_enum_v1": list(BTC_PILOT_WINDOW_MATCH_ENUM_V1),
        "row_level_fields_v1": [
            "btc_readonly_surface_profile_v1",
            "btc_polarity_slot_v1",
            "btc_intent_slot_v1",
            "btc_continuation_stage_v1",
            "btc_rejection_type_v1",
            "btc_texture_slot_v1",
            "btc_location_context_v1",
            "btc_tempo_profile_v1",
            "btc_ambiguity_level_v1",
            "btc_state_slot_core_v1",
            "btc_state_slot_modifier_bundle_v1",
            "btc_pilot_window_match_v1",
            "btc_surface_reason_summary_v1",
        ],
        "control_rules_v1": [
            "btc readonly surface is a read-only view onto the common slot frame",
            "btc readonly surface cannot change dominant_side",
            "btc readonly surface cannot change execution or state25",
            "btc slot naming stays common-first and symbol-prefixed only for visibility",
        ],
        "dominance_protection_v1": {
            "btc_readonly_surface_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_extension_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("state_slot_symbol_extension_surface_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_state_slot_symbol_extension_surface_fields_v1({symbol: row}).get(symbol, row))


def _pilot_window_match(row: Mapping[str, Any]) -> str:
    status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    if status == "ACTIVE_CANDIDATE" and match == "MATCH":
        return "MATCHED_ACTIVE_PROFILE"
    if status == "ACTIVE_CANDIDATE" and match == "PARTIAL_MATCH":
        return "PARTIAL_ACTIVE_PROFILE"
    if status == "SEPARATE_PENDING":
        return "REVIEW_PENDING"
    return "OUT_OF_PROFILE"


def build_btc_readonly_surface_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_extension_surface(row or {})
    symbol = _text(payload.get("symbol")).upper()
    if symbol != "BTCUSD":
        profile = {
            "contract_version": BTC_READONLY_SURFACE_CONTRACT_VERSION,
            "applicable_v1": False,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "btc_readonly_surface_profile_v1": profile,
            "btc_polarity_slot_v1": "",
            "btc_intent_slot_v1": "",
            "btc_continuation_stage_v1": "",
            "btc_rejection_type_v1": "",
            "btc_texture_slot_v1": "",
            "btc_location_context_v1": "",
            "btc_tempo_profile_v1": "",
            "btc_ambiguity_level_v1": "",
            "btc_state_slot_core_v1": "",
            "btc_state_slot_modifier_bundle_v1": [],
            "btc_pilot_window_match_v1": "NOT_APPLICABLE",
            "btc_surface_reason_summary_v1": "symbol_not_btc",
        }

    pilot_match = _pilot_window_match(payload)
    profile = {
        "contract_version": BTC_READONLY_SURFACE_CONTRACT_VERSION,
        "applicable_v1": True,
        "btc_polarity_slot_v1": _text(payload.get("common_state_polarity_slot_v1")).upper(),
        "btc_intent_slot_v1": _text(payload.get("common_state_intent_slot_v1")).upper(),
        "btc_continuation_stage_v1": _text(payload.get("common_state_continuation_stage_v1")).upper(),
        "btc_rejection_type_v1": _text(payload.get("common_state_rejection_type_v1")).upper(),
        "btc_texture_slot_v1": _text(payload.get("common_state_texture_slot_v1")).upper(),
        "btc_location_context_v1": _text(payload.get("common_state_location_context_v1")).upper(),
        "btc_tempo_profile_v1": _text(payload.get("common_state_tempo_profile_v1")).upper(),
        "btc_ambiguity_level_v1": _text(payload.get("common_state_ambiguity_level_v1")).upper(),
        "btc_state_slot_core_v1": _text(payload.get("common_state_slot_core_v1")).upper(),
        "btc_state_slot_modifier_bundle_v1": list(payload.get("common_state_slot_modifier_bundle_v1") or []),
        "btc_pilot_window_match_v1": pilot_match,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    reason = (
        f"profile={_text(payload.get('symbol_state_strength_best_profile_key_v1')) or 'none'}; "
        f"match={pilot_match}; core={profile['btc_state_slot_core_v1']}; "
        f"texture={profile['btc_texture_slot_v1']}; tempo={profile['btc_tempo_profile_v1']}"
    )
    return {
        "btc_readonly_surface_profile_v1": profile,
        "btc_polarity_slot_v1": profile["btc_polarity_slot_v1"],
        "btc_intent_slot_v1": profile["btc_intent_slot_v1"],
        "btc_continuation_stage_v1": profile["btc_continuation_stage_v1"],
        "btc_rejection_type_v1": profile["btc_rejection_type_v1"],
        "btc_texture_slot_v1": profile["btc_texture_slot_v1"],
        "btc_location_context_v1": profile["btc_location_context_v1"],
        "btc_tempo_profile_v1": profile["btc_tempo_profile_v1"],
        "btc_ambiguity_level_v1": profile["btc_ambiguity_level_v1"],
        "btc_state_slot_core_v1": profile["btc_state_slot_core_v1"],
        "btc_state_slot_modifier_bundle_v1": profile["btc_state_slot_modifier_bundle_v1"],
        "btc_pilot_window_match_v1": pilot_match,
        "btc_surface_reason_summary_v1": reason,
    }


def attach_btc_readonly_surface_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_extension_surface(raw)
        row.update(build_btc_readonly_surface_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_btc_readonly_surface_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_btc_readonly_surface_fields_v1(latest_signal_by_symbol)
    btc_rows = {symbol: row for symbol, row in rows_by_symbol.items() if _text(row.get("symbol")).upper() == "BTCUSD"}
    core_counts = Counter()
    texture_counts = Counter()
    match_counts = Counter()
    applicable_count = 0
    for row in btc_rows.values():
        if isinstance(row.get("btc_readonly_surface_profile_v1"), Mapping):
            applicable_count += 1
        core_counts.update([_text(row.get("btc_state_slot_core_v1"))])
        texture_counts.update([_text(row.get("btc_texture_slot_v1"))])
        match_counts.update([_text(row.get("btc_pilot_window_match_v1"))])
    status = "READY" if btc_rows and applicable_count == len(btc_rows) else "HOLD"
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["btc_readonly_surface_available"] if status == "READY" else ["btc_row_missing_or_surface_incomplete"]
        ),
        "btc_row_count": int(len(btc_rows)),
        "surface_ready_count": int(applicable_count),
        "state_slot_core_count_summary": dict(core_counts),
        "texture_slot_count_summary": dict(texture_counts),
        "pilot_window_match_count_summary": dict(match_counts),
    }
    return {
        "contract_version": BTC_READONLY_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_btc_readonly_surface_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# BTC Read-only Surface v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- btc_row_count: `{int(summary.get('btc_row_count', 0) or 0)}`",
        "",
        "## BTC Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "BTCUSD":
            continue
        lines.append(
            f"- `{symbol}`: core={row.get('btc_state_slot_core_v1', '')} | "
            f"texture={row.get('btc_texture_slot_v1', '')} | "
            f"location={row.get('btc_location_context_v1', '')} | "
            f"tempo={row.get('btc_tempo_profile_v1', '')} | "
            f"match={row.get('btc_pilot_window_match_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_btc_readonly_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_btc_readonly_surface_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "btc_readonly_surface_latest.json"
    md_path = output_dir / "btc_readonly_surface_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_btc_readonly_surface_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {"json_path": str(json_path), "markdown_path": str(md_path)},
    }
