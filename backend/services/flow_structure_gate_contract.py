from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.state_slot_symbol_extension_surface import (
    attach_state_slot_symbol_extension_surface_fields_v1,
)


FLOW_STRUCTURE_GATE_CONTRACT_VERSION = "flow_structure_gate_contract_v1"
FLOW_STRUCTURE_GATE_SUMMARY_VERSION = "flow_structure_gate_summary_v1"

FLOW_STRUCTURE_GATE_STATE_ENUM_V1 = ("ELIGIBLE", "WEAK", "INELIGIBLE", "NOT_APPLICABLE")
FLOW_STRUCTURE_GATE_HARD_DISQUALIFIER_ENUM_V1 = (
    "UNMAPPED_SLOT",
    "POLARITY_MISMATCH",
    "REVERSAL_REJECTION",
    "REVERSAL_OVERRIDE",
    "AMBIGUITY_HIGH",
)
FLOW_STRUCTURE_GATE_PRIMARY_REASON_ENUM_V1 = (
    "NONE",
    "STRUCTURE_ELIGIBLE",
    "SOFT_SUPPORT_BORDERLINE",
    "UNMAPPED_SLOT",
    "POLARITY_MISMATCH",
    "REVERSAL_REJECTION",
    "REVERSAL_OVERRIDE",
    "AMBIGUITY_HIGH",
    "SOFT_SUPPORT_MISSING",
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


def build_flow_structure_gate_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Structure-first directional flow eligibility gate. Uses decomposition and local structure to decide "
            "whether a row is allowed to become a directional flow candidate before any aggregate thresholding."
        ),
        "flow_structure_gate_state_enum_v1": list(FLOW_STRUCTURE_GATE_STATE_ENUM_V1),
        "hard_disqualifier_enum_v1": list(FLOW_STRUCTURE_GATE_HARD_DISQUALIFIER_ENUM_V1),
        "primary_reason_enum_v1": list(FLOW_STRUCTURE_GATE_PRIMARY_REASON_ENUM_V1),
        "row_level_fields_v1": [
            "flow_structure_gate_profile_v1",
            "flow_structure_gate_v1",
            "flow_structure_gate_primary_reason_v1",
            "flow_structure_gate_hard_disqualifiers_v1",
            "flow_structure_gate_soft_qualifiers_v1",
            "flow_structure_gate_soft_score_v1",
            "flow_structure_gate_slot_core_v1",
            "flow_structure_gate_slot_polarity_v1",
            "flow_structure_gate_stage_v1",
            "flow_structure_gate_rejection_type_v1",
            "flow_structure_gate_tempo_v1",
            "flow_structure_gate_ambiguity_v1",
            "flow_structure_gate_reason_summary_v1",
        ],
        "authority_order_v1": [
            "hard_disqualifier",
            "soft_qualifier_strength",
            "aggregate_flow_threshold",
            "exact_match_bonus",
        ],
        "control_rules_v1": [
            "structure gate decides candidate eligibility before aggregate thresholds are interpreted",
            "hard disqualifiers always win over soft qualifiers",
            "extension can remain flow-eligible only as weak structure, not as fresh strong eligibility",
            "structure gate remains read-only and cannot change execution or state25",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_extension_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("state_slot_symbol_extension_surface_profile_v1"), Mapping):
        return row
    if _text(row.get("common_state_slot_core_v1")):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_state_slot_symbol_extension_surface_fields_v1({symbol: row}).get(symbol, row))


def _slot_polarity(row: Mapping[str, Any]) -> str:
    for key in ("common_state_polarity_slot_v1", "xau_polarity_slot_v1"):
        value = _text(row.get(key)).upper()
        if value in {"BULL", "BEAR"}:
            return value
    return "NONE"


def _dominant_side(row: Mapping[str, Any]) -> str:
    for key in ("dominance_shadow_dominant_side_v1", "state_strength_dominant_side_v1", "state_strength_side_seed_v1"):
        value = _text(row.get(key)).upper()
        if value in {"BULL", "BEAR"}:
            return value
    direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    if direction == "UP":
        return "BULL"
    if direction == "DOWN":
        return "BEAR"
    return "NONE"


def _slot_stage(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_continuation_stage_v1") or row.get("xau_continuation_stage_v1")).upper()


def _slot_rejection(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_rejection_type_v1") or row.get("xau_rejection_type_v1")).upper()


def _slot_tempo(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_tempo_profile_v1") or row.get("xau_tempo_profile_v1")).upper()


def _slot_ambiguity(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_ambiguity_level_v1") or row.get("xau_ambiguity_level_v1")).upper()


def _slot_support_side(row: Mapping[str, Any]) -> str:
    consumer_side = _text(row.get("consumer_check_side")).upper()
    if consumer_side in {"BUY", "SELL"}:
        return consumer_side
    overlay_side = _text(row.get("directional_continuation_overlay_side")).upper()
    if overlay_side in {"BUY", "SELL"}:
        return overlay_side
    chart_hint = _text(row.get("chart_event_kind_hint")).upper()
    if chart_hint.startswith("BUY"):
        return "BUY"
    if chart_hint.startswith("SELL"):
        return "SELL"
    breakout_direction = _text(row.get("breakout_candidate_direction") or row.get("breakout_direction")).upper()
    if breakout_direction == "UP":
        return "BUY"
    if breakout_direction == "DOWN":
        return "SELL"
    return "NONE"


def _ambiguity_high_soft_hold_override(row: Mapping[str, Any]) -> bool:
    symbol = _text(row.get("symbol")).upper()
    if symbol not in {"XAUUSD", "BTCUSD"}:
        return False
    slot_polarity = _slot_polarity(row)
    dominant_side = _dominant_side(row)
    support_side = _slot_support_side(row)
    expected_support_side = "BUY" if slot_polarity == "BULL" else "SELL"
    if slot_polarity not in {"BULL", "BEAR"}:
        return False
    if _slot_ambiguity(row) != "HIGH":
        return False
    if _text(row.get("consumer_veto_tier_v1")).upper() == "REVERSAL_OVERRIDE":
        return False
    if _slot_rejection(row) == "REVERSAL_REJECTION":
        return False
    if dominant_side not in {slot_polarity, "NONE"} and support_side != expected_support_side:
        return False
    if dominant_side == "NONE" and support_side != expected_support_side:
        return False

    break_state = _text(row.get("previous_box_break_state")).upper()
    relation = _text(row.get("previous_box_relation")).upper()
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    stage = _slot_stage(row)
    structure_bias = _text(row.get("few_candle_structure_bias_v1")).upper()
    body_drive = _text(row.get("body_drive_state_v1")).upper()

    if slot_polarity == "BULL":
        location_support = break_state in {"BREAKOUT_HELD", "RECLAIMED"} and relation in {"ABOVE", "AT_HIGH"}
        if not location_support and breakout_hold not in {"STABLE", "STRONG"}:
            return False
    else:
        location_support = break_state in {"BREAKDOWN_HELD", "REJECTED"} and relation in {"BELOW", "AT_LOW"}
        if not location_support and breakout_hold not in {"WEAK", "STABLE", "STRONG"}:
            return False
    if stage not in {"INITIATION", "ACCEPTANCE", "EXTENSION"}:
        return False
    if structure_bias not in {"CONTINUATION_FAVOR", "MIXED", ""} and body_drive not in {"WEAK_DRIVE", "STRONG_DRIVE"}:
        return False

    return breakout_hold in {"WEAK", "STABLE", "STRONG"}


def _hard_disqualifiers(row: Mapping[str, Any]) -> list[str]:
    disqualifiers: list[str] = []
    slot_polarity = _slot_polarity(row)
    if not _text(row.get("common_state_slot_core_v1") or row.get("xau_state_slot_core_v1")) or slot_polarity == "NONE":
        disqualifiers.append("UNMAPPED_SLOT")
        return disqualifiers
    dominant_side = _dominant_side(row)
    if dominant_side in {"BULL", "BEAR"} and dominant_side != slot_polarity:
        disqualifiers.append("POLARITY_MISMATCH")
    if _slot_rejection(row) == "REVERSAL_REJECTION":
        disqualifiers.append("REVERSAL_REJECTION")
    if _text(row.get("consumer_veto_tier_v1")).upper() == "REVERSAL_OVERRIDE":
        disqualifiers.append("REVERSAL_OVERRIDE")
    if _slot_ambiguity(row) == "HIGH" and not _ambiguity_high_soft_hold_override(row):
        disqualifiers.append("AMBIGUITY_HIGH")
    return disqualifiers


def _soft_qualifiers(row: Mapping[str, Any]) -> tuple[list[str], float]:
    qualifiers: list[str] = []
    score = 0.0

    stage = _slot_stage(row)
    tempo = _slot_tempo(row)
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    structure_bias = _text(row.get("few_candle_structure_bias_v1")).upper()
    body_drive = _text(row.get("body_drive_state_v1")).upper()
    side = _slot_polarity(row)
    higher_low = _text(row.get("few_candle_higher_low_state_v1")).upper()
    lower_high = _text(row.get("few_candle_lower_high_state_v1")).upper()

    if stage in {"INITIATION", "ACCEPTANCE"}:
        qualifiers.append("STAGE_FLOW_ELIGIBLE")
        score += 1.0
    elif stage == "EXTENSION":
        qualifiers.append("STAGE_EXTENSION_CAP")
        score += 0.5

    if tempo in {"PERSISTING", "REPEATING"}:
        qualifiers.append("TEMPO_PERSISTING")
        score += 1.0
    elif tempo == "EARLY" and stage == "INITIATION":
        qualifiers.append("TEMPO_EARLY_BUILDING")
        score += 0.5

    if breakout_hold in {"STABLE", "STRONG"}:
        qualifiers.append("BREAKOUT_HOLD_OK")
        score += 1.0
    elif breakout_hold == "WEAK":
        qualifiers.append("BREAKOUT_HOLD_WEAK")
        score += 0.5

    swing_intact = (
        side == "BULL" and higher_low in {"HELD", "CLEAN_HELD"}
    ) or (
        side == "BEAR" and lower_high in {"HELD", "CLEAN_HELD"}
    )
    if structure_bias == "CONTINUATION_FAVOR":
        qualifiers.append("STRUCTURE_BIAS_SUPPORT")
        score += 1.0
    elif structure_bias == "MIXED":
        qualifiers.append("STRUCTURE_BIAS_MIXED")
        score += 0.5

    if swing_intact:
        qualifiers.append("SWING_STRUCTURE_INTACT")
        score += 1.0

    if body_drive in {"WEAK_DRIVE", "STRONG_DRIVE"}:
        qualifiers.append("BODY_DRIVE_SUPPORT")
        score += 0.5

    return qualifiers, round(score, 2)


def build_flow_structure_gate_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_extension_surface(row or {})
    symbol = _text(payload.get("symbol")).upper()
    if symbol not in {"XAUUSD", "NAS100", "BTCUSD"}:
        profile = {
            "contract_version": FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
            "gate_state_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "flow_structure_gate_profile_v1": profile,
            "flow_structure_gate_v1": "NOT_APPLICABLE",
            "flow_structure_gate_primary_reason_v1": "NOT_APPLICABLE",
            "flow_structure_gate_hard_disqualifiers_v1": [],
            "flow_structure_gate_soft_qualifiers_v1": [],
            "flow_structure_gate_soft_score_v1": None,
            "flow_structure_gate_slot_core_v1": "",
            "flow_structure_gate_slot_polarity_v1": "",
            "flow_structure_gate_stage_v1": "",
            "flow_structure_gate_rejection_type_v1": "",
            "flow_structure_gate_tempo_v1": "",
            "flow_structure_gate_ambiguity_v1": "",
            "flow_structure_gate_reason_summary_v1": "symbol_not_supported_for_flow_structure_gate",
        }

    hard_disqualifiers = _hard_disqualifiers(payload)
    soft_qualifiers, soft_score = _soft_qualifiers(payload)
    stage = _slot_stage(payload)

    if hard_disqualifiers:
        gate_state = "INELIGIBLE"
        primary_reason = hard_disqualifiers[0]
    else:
        if stage == "EXTENSION":
            if soft_score >= 2.0:
                gate_state = "WEAK"
                primary_reason = "SOFT_SUPPORT_BORDERLINE"
            else:
                gate_state = "INELIGIBLE"
                primary_reason = "SOFT_SUPPORT_MISSING"
        elif soft_score >= 3.0:
            gate_state = "ELIGIBLE"
            primary_reason = "STRUCTURE_ELIGIBLE"
        elif soft_score >= 1.5:
            gate_state = "WEAK"
            primary_reason = "SOFT_SUPPORT_BORDERLINE"
        else:
            gate_state = "INELIGIBLE"
            primary_reason = "SOFT_SUPPORT_MISSING"

        if _ambiguity_high_soft_hold_override(payload) and gate_state == "ELIGIBLE":
            gate_state = "WEAK"
            primary_reason = "SOFT_SUPPORT_BORDERLINE"

    reason = (
        f"symbol={symbol}; slot={_text(payload.get('common_state_slot_core_v1') or payload.get('xau_state_slot_core_v1')) or 'none'}; "
        f"polarity={_slot_polarity(payload) or 'none'}; dominant_side={_dominant_side(payload) or 'none'}; "
        f"stage={stage or 'none'}; rejection={_slot_rejection(payload) or 'none'}; "
        f"tempo={_slot_tempo(payload) or 'none'}; ambiguity={_slot_ambiguity(payload) or 'none'}; "
        f"hard={','.join(hard_disqualifiers) or 'none'}; soft={','.join(soft_qualifiers) or 'none'}; "
        f"soft_score={soft_score}; gate={gate_state}"
    )

    profile = {
        "contract_version": FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
        "gate_state_v1": gate_state,
        "primary_reason_v1": primary_reason,
        "hard_disqualifiers_v1": list(hard_disqualifiers),
        "soft_qualifiers_v1": list(soft_qualifiers),
        "soft_score_v1": soft_score,
        "slot_core_v1": _text(payload.get("common_state_slot_core_v1") or payload.get("xau_state_slot_core_v1")),
        "slot_polarity_v1": _slot_polarity(payload),
        "stage_v1": stage,
        "rejection_type_v1": _slot_rejection(payload),
        "tempo_v1": _slot_tempo(payload),
        "ambiguity_v1": _slot_ambiguity(payload),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "flow_structure_gate_profile_v1": profile,
        "flow_structure_gate_v1": gate_state,
        "flow_structure_gate_primary_reason_v1": primary_reason,
        "flow_structure_gate_hard_disqualifiers_v1": list(hard_disqualifiers),
        "flow_structure_gate_soft_qualifiers_v1": list(soft_qualifiers),
        "flow_structure_gate_soft_score_v1": soft_score,
        "flow_structure_gate_slot_core_v1": profile["slot_core_v1"],
        "flow_structure_gate_slot_polarity_v1": profile["slot_polarity_v1"],
        "flow_structure_gate_stage_v1": profile["stage_v1"],
        "flow_structure_gate_rejection_type_v1": profile["rejection_type_v1"],
        "flow_structure_gate_tempo_v1": profile["tempo_v1"],
        "flow_structure_gate_ambiguity_v1": profile["ambiguity_v1"],
        "flow_structure_gate_reason_summary_v1": reason,
    }


def attach_flow_structure_gate_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_extension_surface(raw)
        row.update(build_flow_structure_gate_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_flow_structure_gate_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_structure_gate_fields_v1(latest_signal_by_symbol)
    state_counts = Counter()
    reason_counts = Counter()
    slot_counts = Counter()
    hard_counts = Counter()
    symbol_count = len(rows_by_symbol)
    eligible_or_weak_count = 0

    for row in rows_by_symbol.values():
        state = _text(row.get("flow_structure_gate_v1"))
        state_counts.update([state])
        reason_counts.update([_text(row.get("flow_structure_gate_primary_reason_v1"))])
        slot_counts.update([_text(row.get("flow_structure_gate_slot_core_v1"))])
        for item in list(row.get("flow_structure_gate_hard_disqualifiers_v1") or []):
            hard_counts.update([_text(item)])
        if state in {"ELIGIBLE", "WEAK"}:
            eligible_or_weak_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["flow_structure_gate_surface_available"] if symbol_count else ["no_rows_for_flow_structure_gate"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "eligible_or_weak_count": int(eligible_or_weak_count),
        "flow_structure_gate_state_count_summary": dict(state_counts),
        "flow_structure_gate_primary_reason_count_summary": dict(reason_counts),
        "flow_structure_gate_hard_disqualifier_count_summary": dict(hard_counts),
        "flow_structure_gate_slot_core_count_summary": dict(slot_counts),
    }
    return {
        "contract_version": FLOW_STRUCTURE_GATE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_structure_gate_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Flow Structure Gate v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- surface_ready_count: `{int(summary.get('surface_ready_count', 0) or 0)}`",
        "",
        "## Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: gate={row.get('flow_structure_gate_v1', '')} | "
            f"reason={row.get('flow_structure_gate_primary_reason_v1', '')} | "
            f"slot={row.get('flow_structure_gate_slot_core_v1', '')} | "
            f"stage={row.get('flow_structure_gate_stage_v1', '')} | "
            f"tempo={row.get('flow_structure_gate_tempo_v1', '')} | "
            f"hard={', '.join(str(x) for x in list(row.get('flow_structure_gate_hard_disqualifiers_v1') or [])) or 'none'}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_structure_gate_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_flow_structure_gate_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "flow_structure_gate_latest.json"
    md_path = output_dir / "flow_structure_gate_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_flow_structure_gate_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
