from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.exact_pilot_match_bonus_contract import (
    EXACT_PILOT_MATCH_BONUS_CONTRACT_VERSION,
    attach_exact_pilot_match_bonus_fields_v1,
)


FLOW_SUPPORT_STATE_CONTRACT_VERSION = "flow_support_state_contract_v1"
FLOW_SUPPORT_STATE_SUMMARY_VERSION = "flow_support_state_summary_v1"

FLOW_SUPPORT_STATE_ENUM_V1 = (
    "FLOW_CONFIRMED",
    "FLOW_BUILDING",
    "FLOW_UNCONFIRMED",
    "FLOW_OPPOSED",
)
FLOW_SUPPORT_STATE_AUTHORITY_ENUM_V1 = (
    "STRUCTURE_HARD_OPPOSED",
    "STRUCTURE_BLOCKED_UNCONFIRMED",
    "PROVISIONAL_CONFIRMED",
    "PROVISIONAL_BUILDING",
    "PROVISIONAL_UNCONFIRMED",
    "EXTENSION_CAPPED_BUILDING",
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


def build_flow_support_state_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_SUPPORT_STATE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Final read-only flow acceptance surface. Converts structure, conviction/persistence band, and exact "
            "pilot bonus into a common directional flow state without changing execution or state25."
        ),
        "upstream_contract_versions_v1": [
            EXACT_PILOT_MATCH_BONUS_CONTRACT_VERSION,
        ],
        "flow_support_state_enum_v1": list(FLOW_SUPPORT_STATE_ENUM_V1),
        "flow_support_state_authority_enum_v1": list(FLOW_SUPPORT_STATE_AUTHORITY_ENUM_V1),
        "row_level_fields_v1": [
            "flow_support_state_profile_v1",
            "flow_support_state_v1",
            "flow_support_state_authority_v1",
            "flow_support_structure_gate_v1",
            "flow_support_base_band_state_v1",
            "flow_support_boosted_band_state_v1",
            "flow_support_bonus_effect_v1",
            "flow_support_threshold_profile_v1",
            "flow_support_reason_summary_v1",
        ],
        "control_rules_v1": [
            "flow support state is downstream of structure, band, and bonus layers",
            "hard opposed reasons remain opposed while ambiguous or weakly supported rows stay unconfirmed",
            "extension remains capped away from confirmed even if upstream band says confirmed candidate",
            "exact bonus cannot grow in authority inside F6",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("boosted_provisional_flow_band_state_v1")):
        row = dict(attach_exact_pilot_match_bonus_fields_v1({"_": row}).get("_", row))
    return row


def _hard_disqualifiers(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("flow_structure_gate_hard_disqualifiers_v1")
    if isinstance(raw, list):
        return [_text(item).upper() for item in raw if _text(item)]
    return []


def _gate_state(row: Mapping[str, Any]) -> str:
    return _text(row.get("aggregate_flow_structure_gate_v1") or row.get("flow_structure_gate_v1")).upper()


def _base_band(row: Mapping[str, Any]) -> str:
    return _text(row.get("provisional_flow_band_state_v1")).upper()


def _boosted_band(row: Mapping[str, Any]) -> str:
    value = _text(row.get("boosted_provisional_flow_band_state_v1")).upper()
    return value or _base_band(row)


def _bonus_effect(row: Mapping[str, Any]) -> str:
    return _text(row.get("exact_pilot_match_bonus_effect_v1")).upper()


def _threshold_profile(row: Mapping[str, Any]) -> str:
    return _text(row.get("flow_threshold_profile_v1")).upper() or "COMMON"


def _stage(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_continuation_stage_v1")
        or row.get("xau_continuation_stage_v1")
        or row.get("nas_continuation_stage_v1")
        or row.get("btc_continuation_stage_v1")
        or row.get("flow_structure_gate_stage_v1")
    ).upper()


def _reason_summary(
    *,
    gate: str,
    authority: str,
    base_band: str,
    boosted_band: str,
    bonus_effect: str,
    threshold_profile: str,
    final_state: str,
) -> str:
    return (
        f"gate={gate}; "
        f"authority={authority}; "
        f"profile={threshold_profile}; "
        f"base={base_band}; "
        f"boosted={boosted_band}; "
        f"bonus={bonus_effect}; "
        f"state={final_state}"
    )


def build_flow_support_state_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    gate = _gate_state(payload)
    hard = _hard_disqualifiers(payload)
    base_band = _base_band(payload) or "NOT_APPLICABLE"
    boosted_band = _boosted_band(payload) or "NOT_APPLICABLE"
    bonus_effect = _bonus_effect(payload) or "NOT_APPLICABLE"
    threshold_profile = _threshold_profile(payload)
    stage = _stage(payload)

    if gate not in {"ELIGIBLE", "WEAK"}:
        if any(item in {"POLARITY_MISMATCH", "REVERSAL_REJECTION", "REVERSAL_OVERRIDE"} for item in hard):
            state = "FLOW_OPPOSED"
            authority = "STRUCTURE_HARD_OPPOSED"
        else:
            state = "FLOW_UNCONFIRMED"
            authority = "STRUCTURE_BLOCKED_UNCONFIRMED"
    elif stage == "EXTENSION" and boosted_band == "CONFIRMED_CANDIDATE":
        state = "FLOW_BUILDING"
        authority = "EXTENSION_CAPPED_BUILDING"
    elif boosted_band == "CONFIRMED_CANDIDATE":
        state = "FLOW_CONFIRMED"
        authority = "PROVISIONAL_CONFIRMED"
    elif boosted_band == "BUILDING_CANDIDATE":
        state = "FLOW_BUILDING"
        authority = "PROVISIONAL_BUILDING"
    elif boosted_band in {"UNCONFIRMED_CANDIDATE", "STRUCTURE_BLOCKED", "NOT_APPLICABLE"}:
        state = "FLOW_UNCONFIRMED"
        authority = "PROVISIONAL_UNCONFIRMED"
    else:
        state = "FLOW_UNCONFIRMED"
        authority = "PROVISIONAL_UNCONFIRMED"

    reason = _reason_summary(
        gate=gate or "UNKNOWN",
        authority=authority,
        base_band=base_band,
        boosted_band=boosted_band,
        bonus_effect=bonus_effect,
        threshold_profile=threshold_profile,
        final_state=state,
    )

    profile = {
        "contract_version": FLOW_SUPPORT_STATE_CONTRACT_VERSION,
        "flow_support_state_v1": state,
        "flow_support_state_authority_v1": authority,
        "flow_support_structure_gate_v1": gate,
        "flow_support_base_band_state_v1": base_band,
        "flow_support_boosted_band_state_v1": boosted_band,
        "flow_support_bonus_effect_v1": bonus_effect,
        "flow_support_threshold_profile_v1": threshold_profile,
        "flow_support_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "flow_support_state_profile_v1": profile,
        "flow_support_state_v1": state,
        "flow_support_state_authority_v1": authority,
        "flow_support_structure_gate_v1": gate,
        "flow_support_base_band_state_v1": base_band,
        "flow_support_boosted_band_state_v1": boosted_band,
        "flow_support_bonus_effect_v1": bonus_effect,
        "flow_support_threshold_profile_v1": threshold_profile,
        "flow_support_reason_summary_v1": reason,
    }


def attach_flow_support_state_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_flow_support_state_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_flow_support_state_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_support_state_fields_v1(latest_signal_by_symbol)
    state_counts = Counter()
    authority_counts = Counter()
    profile_counts = Counter()
    gate_counts = Counter()
    symbol_count = len(rows_by_symbol)

    for row in rows_by_symbol.values():
        state_counts.update([_text(row.get("flow_support_state_v1"))])
        authority_counts.update([_text(row.get("flow_support_state_authority_v1"))])
        profile_counts.update([_text(row.get("flow_support_threshold_profile_v1"))])
        gate_counts.update([_text(row.get("flow_support_structure_gate_v1"))])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["flow_support_state_surface_available"] if symbol_count else ["no_rows_for_flow_support_state"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "flow_support_state_count_summary": dict(state_counts),
        "flow_support_state_authority_count_summary": dict(authority_counts),
        "flow_support_threshold_profile_count_summary": dict(profile_counts),
        "flow_support_structure_gate_count_summary": dict(gate_counts),
    }
    return {
        "contract_version": FLOW_SUPPORT_STATE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_support_state_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Flow Support State",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- flow_support_state_count_summary: {json.dumps(summary.get('flow_support_state_count_summary', {}), ensure_ascii=False)}",
        f"- flow_support_state_authority_count_summary: {json.dumps(summary.get('flow_support_state_authority_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: state={row.get('flow_support_state_v1', '')}, "
            f"authority={row.get('flow_support_state_authority_v1', '')}, "
            f"gate={row.get('flow_support_structure_gate_v1', '')}, "
            f"base={row.get('flow_support_base_band_state_v1', '')}, "
            f"boosted={row.get('flow_support_boosted_band_state_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_support_state_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_flow_support_state_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "flow_support_state_latest.json"
    markdown_path = output_dir / "flow_support_state_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_flow_support_state_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
