from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.flow_structure_gate_contract import (
    FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
    attach_flow_structure_gate_fields_v1,
)


AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION = (
    "aggregate_directional_flow_metrics_contract_v1"
)
AGGREGATE_DIRECTIONAL_FLOW_METRICS_SUMMARY_VERSION = (
    "aggregate_directional_flow_metrics_summary_v1"
)

AGGREGATE_CONVICTION_BUCKET_ENUM_V1 = ("HIGH", "MID", "LOW")
FLOW_PERSISTENCE_STATE_ENUM_V1 = ("PERSISTING", "BUILDING", "FRAGILE", "FADING")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_aggregate_directional_flow_metrics_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Common read-only directional flow metrics contract. Computes aggregate conviction and flow persistence "
            "after structure eligibility has already been determined by flow_structure_gate_v1."
        ),
        "upstream_contract_version_v1": FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
        "aggregate_conviction_minimum_components_v1": [
            "dominance_support",
            "structure_support",
            "decomposition_alignment",
        ],
        "aggregate_conviction_bucket_enum_v1": list(AGGREGATE_CONVICTION_BUCKET_ENUM_V1),
        "flow_persistence_state_enum_v1": list(FLOW_PERSISTENCE_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "aggregate_directional_flow_metrics_profile_v1",
            "aggregate_flow_structure_gate_v1",
            "aggregate_flow_structure_primary_reason_v1",
            "aggregate_conviction_v1",
            "aggregate_conviction_bucket_v1",
            "aggregate_dominance_support_v1",
            "aggregate_structure_support_v1",
            "aggregate_decomposition_alignment_v1",
            "aggregate_ambiguity_penalty_v1",
            "aggregate_veto_penalty_v1",
            "flow_persistence_v1",
            "flow_persistence_state_v1",
            "flow_persistence_recency_weight_v1",
            "aggregate_flow_reason_summary_v1",
        ],
        "authority_order_v1": [
            "flow_structure_gate",
            "aggregate_conviction",
            "flow_persistence",
            "exact_match_bonus",
        ],
        "control_rules_v1": [
            "aggregate conviction is a confidence metric, not a standalone pass/fail gate",
            "flow persistence uses recency weighting so recent persistence matters more than older persistence",
            "structure gate remains upstream and numbers cannot outrank structure eligibility",
            "extension may keep moderate persistence but is not treated as fresh strong flow by conviction alignment alone",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_flow_structure_gate(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("flow_structure_gate_profile_v1"), Mapping):
        return row
    if _text(row.get("flow_structure_gate_v1")):
        return row
    return dict(attach_flow_structure_gate_fields_v1({"_": row}).get("_", row))


def _slot_polarity(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("flow_structure_gate_slot_polarity_v1")
        or row.get("common_state_polarity_slot_v1")
        or row.get("xau_polarity_slot_v1")
    ).upper()


def _relevant_swing_state(row: Mapping[str, Any], *, polarity: str) -> str:
    if polarity == "BULL":
        return _text(row.get("few_candle_higher_low_state_v1")).upper()
    if polarity == "BEAR":
        return _text(row.get("few_candle_lower_high_state_v1")).upper()
    return "INSUFFICIENT"


def _stage(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_continuation_stage_v1")
        or row.get("xau_continuation_stage_v1")
        or row.get("flow_structure_gate_stage_v1")
    ).upper()


def _intent(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_intent_slot_v1") or row.get("xau_intent_slot_v1")).upper()


def _texture(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_texture_slot_v1") or row.get("xau_texture_slot_v1")).upper()


def _location(row: Mapping[str, Any]) -> str:
    return _text(row.get("common_state_location_context_v1") or row.get("xau_location_context_v1")).upper()


def _tempo(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_tempo_profile_v1")
        or row.get("xau_tempo_profile_v1")
        or row.get("flow_structure_gate_tempo_v1")
    ).upper()


def _ambiguity(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_ambiguity_level_v1")
        or row.get("xau_ambiguity_level_v1")
        or row.get("flow_structure_gate_ambiguity_v1")
    ).upper()


def _rejection_type(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_rejection_type_v1")
        or row.get("xau_rejection_type_v1")
        or row.get("flow_structure_gate_rejection_type_v1")
    ).upper()


def _dominance_support(row: Mapping[str, Any], *, polarity: str) -> float:
    dominant_side = _text(row.get("dominance_shadow_dominant_side_v1")).upper()
    dominant_mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    gap = _float(row.get("dominance_shadow_gap_v1"), _float(row.get("state_strength_dominance_gap_v1"), 0.0))
    continuation_integrity = _float(row.get("state_strength_continuation_integrity_v1"), 0.0)
    reversal_evidence = _float(row.get("state_strength_reversal_evidence_v1"), 0.0)

    side_alignment = 1.0 if dominant_side and dominant_side == polarity else 0.2
    gap_support = _clamp01(max(gap, 0.0) / 0.4) if side_alignment >= 1.0 else 0.0
    mode_support = {
        "CONTINUATION": 1.0,
        "CONTINUATION_WITH_FRICTION": 0.82,
        "BOUNDARY": 0.45,
        "REVERSAL_RISK": 0.1,
    }.get(dominant_mode, 0.35)
    raw = (
        (gap_support * 0.4)
        + (_clamp01(continuation_integrity) * 0.35)
        + (mode_support * 0.25)
        - (_clamp01(reversal_evidence) * 0.25)
    )
    return _clamp01(raw * side_alignment)


def _map_breakout_hold(value: str) -> float:
    return {
        "STRONG": 1.0,
        "STABLE": 0.8,
        "WEAK": 0.45,
        "FAILED": 0.1,
        "INSUFFICIENT": 0.0,
    }.get(value, 0.0)


def _map_structure_bias(value: str) -> float:
    return {
        "CONTINUATION_FAVOR": 1.0,
        "MIXED": 0.55,
        "REVERSAL_FAVOR": 0.1,
        "INSUFFICIENT": 0.0,
    }.get(value, 0.0)


def _map_swing_state(value: str) -> float:
    return {
        "CLEAN_HELD": 1.0,
        "HELD": 0.8,
        "FRAGILE": 0.45,
        "BROKEN": 0.1,
        "INSUFFICIENT": 0.0,
    }.get(value, 0.0)


def _map_body_drive(value: str) -> float:
    return {
        "STRONG_DRIVE": 1.0,
        "WEAK_DRIVE": 0.7,
        "NEUTRAL": 0.4,
        "COUNTER_DRIVE": 0.1,
    }.get(value, 0.0)


def _structure_support(row: Mapping[str, Any], *, polarity: str) -> float:
    breakout_hold = _map_breakout_hold(_text(row.get("breakout_hold_quality_v1")).upper())
    structure_bias = _map_structure_bias(_text(row.get("few_candle_structure_bias_v1")).upper())
    swing_state = _map_swing_state(_relevant_swing_state(row, polarity=polarity))
    body_drive = _map_body_drive(_text(row.get("body_drive_state_v1")).upper())
    raw = (
        (breakout_hold * 0.35)
        + (structure_bias * 0.3)
        + (swing_state * 0.2)
        + (body_drive * 0.15)
    )
    return _clamp01(raw)


def _map_intent(value: str, *, rejection_type: str) -> float:
    if value in {"CONTINUATION", "RECOVERY"}:
        return 1.0
    if value == "REJECTION":
        return 0.8 if rejection_type == "FRICTION_REJECTION" else 0.2
    if value == "BOUNDARY":
        return 0.2
    return 0.35


def _map_stage(value: str) -> float:
    return {
        "INITIATION": 0.75,
        "ACCEPTANCE": 1.0,
        "EXTENSION": 0.45,
    }.get(value, 0.3)


def _map_texture(value: str) -> float:
    return {
        "CLEAN": 1.0,
        "WITH_FRICTION": 0.72,
        "DRIFT": 0.45,
        "EXHAUSTING": 0.2,
    }.get(value, 0.45)


def _map_location(value: str) -> float:
    return {
        "POST_BREAKOUT": 0.9,
        "IN_BOX": 0.65,
        "AT_EDGE": 0.55,
        "EXTENDED": 0.3,
    }.get(value, 0.45)


def _decomposition_alignment(row: Mapping[str, Any], *, rejection_type: str) -> float:
    intent = _map_intent(_intent(row), rejection_type=rejection_type)
    stage = _map_stage(_stage(row))
    texture = _map_texture(_texture(row))
    location = _map_location(_location(row))
    raw = (
        (intent * 0.2)
        + (stage * 0.35)
        + (texture * 0.25)
        + (location * 0.2)
    )
    return _clamp01(raw)


def _ambiguity_penalty(row: Mapping[str, Any]) -> float:
    return {
        "LOW": 0.0,
        "MEDIUM": 0.12,
        "HIGH": 0.35,
    }.get(_ambiguity(row), 0.12)


def _veto_penalty(row: Mapping[str, Any]) -> float:
    veto_tier = _text(row.get("consumer_veto_tier_v1")).upper()
    return {
        "NONE": 0.0,
        "FRICTION_ONLY": 0.08,
        "BOUNDARY_WARNING": 0.2,
        "REVERSAL_OVERRIDE": 0.6,
    }.get(veto_tier, 0.0)


def _aggregate_conviction(
    *,
    dominance_support: float,
    structure_support: float,
    decomposition_alignment: float,
    ambiguity_penalty: float,
    veto_penalty: float,
) -> float:
    raw = (
        (dominance_support * 0.4)
        + (structure_support * 0.35)
        + (decomposition_alignment * 0.25)
        - ambiguity_penalty
        - veto_penalty
    )
    return _clamp01(raw)


def _aggregate_bucket(conviction: float) -> str:
    if conviction >= 0.67:
        return "HIGH"
    if conviction >= 0.45:
        return "MID"
    return "LOW"


def _map_tempo(value: str) -> float:
    return {
        "PERSISTING": 0.85,
        "REPEATING": 0.8,
        "EARLY": 0.55,
        "EXTENDED": 0.35,
    }.get(value, 0.2)


def _recency_weight(row: Mapping[str, Any]) -> float:
    stage = _stage(row)
    tempo = _tempo(row)
    texture = _texture(row)
    ambiguity = _ambiguity(row)

    if stage == "ACCEPTANCE" and tempo == "PERSISTING":
        weight = 1.0
    elif stage == "ACCEPTANCE" and tempo == "REPEATING":
        weight = 0.93
    elif stage == "INITIATION" and tempo == "EARLY":
        weight = 0.78
    elif stage == "EXTENSION":
        weight = 0.58
    elif tempo == "PERSISTING":
        weight = 0.92
    else:
        weight = 0.84

    if texture == "DRIFT":
        weight *= 0.9
    if ambiguity == "MEDIUM":
        weight *= 0.92
    elif ambiguity == "HIGH":
        weight *= 0.75
    return _clamp01(weight)


def _flow_persistence(row: Mapping[str, Any], *, polarity: str) -> tuple[float, float]:
    tempo_support = _map_tempo(_tempo(row))
    hold_support = _map_breakout_hold(_text(row.get("breakout_hold_quality_v1")).upper())
    swing_support = _map_swing_state(_relevant_swing_state(row, polarity=polarity))
    drive_support = _map_body_drive(_text(row.get("body_drive_state_v1")).upper())
    recency_weight = _recency_weight(row)
    base = (
        (tempo_support * 0.35)
        + (hold_support * 0.3)
        + (swing_support * 0.2)
        + (drive_support * 0.15)
    )
    veto_tier = _text(row.get("consumer_veto_tier_v1")).upper()
    penalty = 0.08 if veto_tier == "BOUNDARY_WARNING" else 0.0
    persistence = _clamp01((base * recency_weight) - penalty)
    return persistence, recency_weight


def _flow_persistence_state(value: float) -> str:
    if value >= 0.72:
        return "PERSISTING"
    if value >= 0.5:
        return "BUILDING"
    if value >= 0.28:
        return "FRAGILE"
    return "FADING"


def _reason_summary(
    *,
    gate_state: str,
    primary_reason: str,
    conviction: float,
    conviction_bucket: str,
    persistence: float,
    persistence_state: str,
    dominance_support: float,
    structure_support: float,
    decomposition_alignment: float,
    ambiguity_penalty: float,
    veto_penalty: float,
    recency_weight: float,
) -> str:
    return (
        f"gate={gate_state}; "
        f"gate_reason={primary_reason}; "
        f"conviction={round(conviction, 4)}({conviction_bucket}); "
        f"persistence={round(persistence, 4)}({persistence_state}); "
        f"dominance={round(dominance_support, 4)}; "
        f"structure={round(structure_support, 4)}; "
        f"decomposition={round(decomposition_alignment, 4)}; "
        f"ambiguity_penalty={round(ambiguity_penalty, 4)}; "
        f"veto_penalty={round(veto_penalty, 4)}; "
        f"recency_weight={round(recency_weight, 4)}"
    )


def build_aggregate_directional_flow_metrics_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_flow_structure_gate(row or {})
    gate_state = _text(payload.get("flow_structure_gate_v1")).upper() or "NOT_APPLICABLE"
    primary_reason = _text(payload.get("flow_structure_gate_primary_reason_v1")).upper() or "NOT_APPLICABLE"
    polarity = _slot_polarity(payload)
    rejection_type = _rejection_type(payload)

    dominance_support = _dominance_support(payload, polarity=polarity)
    structure_support = _structure_support(payload, polarity=polarity)
    decomposition_alignment = _decomposition_alignment(payload, rejection_type=rejection_type)
    ambiguity_penalty = _ambiguity_penalty(payload)
    veto_penalty = _veto_penalty(payload)
    conviction = _aggregate_conviction(
        dominance_support=dominance_support,
        structure_support=structure_support,
        decomposition_alignment=decomposition_alignment,
        ambiguity_penalty=ambiguity_penalty,
        veto_penalty=veto_penalty,
    )
    conviction_bucket = _aggregate_bucket(conviction)
    persistence, recency_weight = _flow_persistence(payload, polarity=polarity)
    persistence_state = _flow_persistence_state(persistence)
    reason_summary = _reason_summary(
        gate_state=gate_state,
        primary_reason=primary_reason,
        conviction=conviction,
        conviction_bucket=conviction_bucket,
        persistence=persistence,
        persistence_state=persistence_state,
        dominance_support=dominance_support,
        structure_support=structure_support,
        decomposition_alignment=decomposition_alignment,
        ambiguity_penalty=ambiguity_penalty,
        veto_penalty=veto_penalty,
        recency_weight=recency_weight,
    )

    profile = {
        "contract_version": AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION,
        "flow_structure_gate_contract_version_v1": FLOW_STRUCTURE_GATE_CONTRACT_VERSION,
        "aggregate_flow_structure_gate_v1": gate_state,
        "aggregate_flow_structure_primary_reason_v1": primary_reason,
        "aggregate_conviction_v1": conviction,
        "aggregate_conviction_bucket_v1": conviction_bucket,
        "aggregate_dominance_support_v1": dominance_support,
        "aggregate_structure_support_v1": structure_support,
        "aggregate_decomposition_alignment_v1": decomposition_alignment,
        "aggregate_ambiguity_penalty_v1": ambiguity_penalty,
        "aggregate_veto_penalty_v1": veto_penalty,
        "flow_persistence_v1": persistence,
        "flow_persistence_state_v1": persistence_state,
        "flow_persistence_recency_weight_v1": recency_weight,
        "aggregate_flow_reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "aggregate_directional_flow_metrics_profile_v1": profile,
        "aggregate_flow_structure_gate_v1": gate_state,
        "aggregate_flow_structure_primary_reason_v1": primary_reason,
        "aggregate_conviction_v1": conviction,
        "aggregate_conviction_bucket_v1": conviction_bucket,
        "aggregate_dominance_support_v1": dominance_support,
        "aggregate_structure_support_v1": structure_support,
        "aggregate_decomposition_alignment_v1": decomposition_alignment,
        "aggregate_ambiguity_penalty_v1": ambiguity_penalty,
        "aggregate_veto_penalty_v1": veto_penalty,
        "flow_persistence_v1": persistence,
        "flow_persistence_state_v1": persistence_state,
        "flow_persistence_recency_weight_v1": recency_weight,
        "aggregate_flow_reason_summary_v1": reason_summary,
    }


def attach_aggregate_directional_flow_metrics_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_flow_structure_gate(raw)
        row.update(build_aggregate_directional_flow_metrics_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_aggregate_directional_flow_metrics_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_aggregate_directional_flow_metrics_fields_v1(latest_signal_by_symbol)
    symbol_count = len(rows_by_symbol)
    conviction_bucket_counts = Counter()
    persistence_state_counts = Counter()
    gate_state_counts = Counter()
    avg_conviction = 0.0
    avg_persistence = 0.0

    for row in rows_by_symbol.values():
        conviction_bucket_counts.update([_text(row.get("aggregate_conviction_bucket_v1"))])
        persistence_state_counts.update([_text(row.get("flow_persistence_state_v1"))])
        gate_state_counts.update([_text(row.get("aggregate_flow_structure_gate_v1"))])
        avg_conviction += _float(row.get("aggregate_conviction_v1"), 0.0)
        avg_persistence += _float(row.get("flow_persistence_v1"), 0.0)

    if symbol_count:
        avg_conviction = round(avg_conviction / symbol_count, 4)
        avg_persistence = round(avg_persistence / symbol_count, 4)

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["aggregate_directional_flow_metrics_surface_available"]
            if symbol_count
            else ["no_rows_for_aggregate_directional_flow_metrics"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "avg_aggregate_conviction_v1": avg_conviction,
        "avg_flow_persistence_v1": avg_persistence,
        "aggregate_conviction_bucket_count_summary": dict(conviction_bucket_counts),
        "flow_persistence_state_count_summary": dict(persistence_state_counts),
        "aggregate_flow_structure_gate_count_summary": dict(gate_state_counts),
    }
    return {
        "contract_version": AGGREGATE_DIRECTIONAL_FLOW_METRICS_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_aggregate_directional_flow_metrics_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))

    lines = [
        "# Aggregate Directional Flow Metrics",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        f"- avg_aggregate_conviction_v1: {summary.get('avg_aggregate_conviction_v1', 0.0)}",
        f"- avg_flow_persistence_v1: {summary.get('avg_flow_persistence_v1', 0.0)}",
        "",
        "## Counts",
        f"- aggregate_conviction_bucket_count_summary: {json.dumps(summary.get('aggregate_conviction_bucket_count_summary', {}), ensure_ascii=False)}",
        f"- flow_persistence_state_count_summary: {json.dumps(summary.get('flow_persistence_state_count_summary', {}), ensure_ascii=False)}",
        f"- aggregate_flow_structure_gate_count_summary: {json.dumps(summary.get('aggregate_flow_structure_gate_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: gate={row.get('aggregate_flow_structure_gate_v1', '')}, "
            f"conviction={row.get('aggregate_conviction_v1', 0.0)}({row.get('aggregate_conviction_bucket_v1', '')}), "
            f"persistence={row.get('flow_persistence_v1', 0.0)}({row.get('flow_persistence_state_v1', '')})"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_aggregate_directional_flow_metrics_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_aggregate_directional_flow_metrics_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "aggregate_directional_flow_metrics_latest.json"
    markdown_path = output_dir / "aggregate_directional_flow_metrics_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_aggregate_directional_flow_metrics_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
