from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


STATE_STRENGTH_PROFILE_CONTRACT_VERSION = "state_strength_profile_contract_v1"
STATE_STRENGTH_SUMMARY_VERSION = "state_strength_summary_v1"
STATE_STRENGTH_SIDE_SEED_ENUM_V1 = ("BULL", "BEAR", "NONE")
STATE_STRENGTH_SIDE_SEED_SOURCE_ENUM_V1 = (
    "OVERLAY_DIRECTION",
    "HTF_ALIGNMENT_PREV_BOX",
    "PREVIOUS_BOX_CONTEXT",
    "NONE",
)
STATE_STRENGTH_CONFIDENCE_ENUM_V1 = ("LOW", "MEDIUM", "HIGH")
STATE_STRENGTH_MODE_ENUM_V1 = (
    "CONTINUATION",
    "CONTINUATION_WITH_FRICTION",
    "BOUNDARY",
    "REVERSAL_RISK",
)
STATE_STRENGTH_CAUTION_LEVEL_ENUM_V1 = ("LOW", "MEDIUM", "HIGH")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
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


def build_state_strength_profile_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_STRENGTH_PROFILE_CONTRACT_VERSION,
        "status": "READY",
        "concept_axes_v1": [
            "trend_pressure",
            "continuation_integrity",
            "reversal_evidence",
            "friction",
            "exhaustion_risk",
            "ambiguity",
        ],
        "v1_priority_axes": [
            "continuation_integrity",
            "reversal_evidence",
            "friction",
            "dominance_gap",
        ],
        "side_seed_enum_v1": list(STATE_STRENGTH_SIDE_SEED_ENUM_V1),
        "side_seed_source_enum_v1": list(STATE_STRENGTH_SIDE_SEED_SOURCE_ENUM_V1),
        "confidence_enum_v1": list(STATE_STRENGTH_CONFIDENCE_ENUM_V1),
        "dominant_mode_enum_v1": list(STATE_STRENGTH_MODE_ENUM_V1),
        "caution_level_enum_v1": list(STATE_STRENGTH_CAUTION_LEVEL_ENUM_V1),
        "dominance_gap_definition_v1": "continuation_integrity - reversal_evidence",
        "principles": [
            "wait_bias_strength is derived, not a raw cause axis",
            "friction does not change dominant_side; it only adjusts dominant_mode and caution_level",
            "reversal override must be expensive and cannot be triggered by a single upper_reject or soft_block",
            "ambiguity is used mainly for boundary/caution interpretation in v1",
        ],
        "description": (
            "Read-only state strength interpretation contract. Surfaces cause-layer and derived-layer fields "
            "without changing execution or state25."
        ),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    upper_text = str(text or "").upper()
    return any(token in upper_text for token in tokens)


def _resolve_side_seed(row: Mapping[str, Any]) -> tuple[str, str, str]:
    overlay_direction = _safe_text(
        row.get("directional_continuation_overlay_direction")
        or row.get("canonical_direction_annotation_v1")
    ).upper()
    overlay_score = _safe_float(row.get("directional_continuation_overlay_score"), 0.0)
    if overlay_direction == "UP":
        return ("BULL", "OVERLAY_DIRECTION", "HIGH" if overlay_score >= 0.65 else "MEDIUM")
    if overlay_direction == "DOWN":
        return ("BEAR", "OVERLAY_DIRECTION", "HIGH" if overlay_score >= 0.65 else "MEDIUM")

    htf_alignment_state = _safe_text(row.get("htf_alignment_state")).upper()
    previous_box_relation = _safe_text(row.get("previous_box_relation")).upper()
    if htf_alignment_state == "WITH_HTF" and previous_box_relation == "ABOVE":
        return ("BULL", "HTF_ALIGNMENT_PREV_BOX", "MEDIUM")
    if htf_alignment_state == "WITH_HTF" and previous_box_relation == "BELOW":
        return ("BEAR", "HTF_ALIGNMENT_PREV_BOX", "MEDIUM")

    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()
    if previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "ABOVE":
        return ("BULL", "PREVIOUS_BOX_CONTEXT", "LOW")
    if previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "BELOW":
        return ("BEAR", "PREVIOUS_BOX_CONTEXT", "LOW")
    return ("NONE", "NONE", "LOW")


def _trend_pressure(row: Mapping[str, Any], *, side_seed: str) -> float:
    points = 0.0
    overlay_score = _safe_float(row.get("directional_continuation_overlay_score"), 0.0)
    if _safe_bool(row.get("directional_continuation_overlay_enabled")):
        points += 0.2
    points += min(max(overlay_score, 0.0), 1.0) * 0.35
    if _safe_text(row.get("htf_alignment_state")).upper() == "WITH_HTF":
        points += 0.15

    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()
    previous_box_relation = _safe_text(row.get("previous_box_relation")).upper()
    if side_seed == "BULL" and previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "ABOVE":
        points += 0.15
    elif side_seed == "BEAR" and previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "BELOW":
        points += 0.15

    leg_direction = _safe_text(row.get("leg_direction")).upper()
    if (side_seed == "BULL" and leg_direction == "UP") or (side_seed == "BEAR" and leg_direction == "DOWN"):
        points += 0.15
    return _clamp01(points)


def _continuation_integrity(row: Mapping[str, Any], *, side_seed: str) -> float:
    points = 0.0
    points += min(max(_safe_float(row.get("directional_continuation_overlay_score"), 0.0), 0.0), 1.0) * 0.4
    if _safe_text(row.get("htf_alignment_state")).upper() == "WITH_HTF":
        points += 0.15

    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()
    previous_box_relation = _safe_text(row.get("previous_box_relation")).upper()
    if side_seed == "BULL" and previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "ABOVE":
        points += 0.2
    elif side_seed == "BEAR" and previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "BELOW":
        points += 0.2

    leg_direction = _safe_text(row.get("leg_direction")).upper()
    if (side_seed == "BULL" and leg_direction == "UP") or (side_seed == "BEAR" and leg_direction == "DOWN"):
        points += 0.1

    checkpoint_reason = _safe_text(row.get("checkpoint_transition_reason")).upper()
    if "CONTINUATION" in checkpoint_reason or "BREAKOUT" in checkpoint_reason:
        points += 0.1

    breakout_candidate_direction = _safe_text(row.get("breakout_candidate_direction")).upper()
    if (side_seed == "BULL" and breakout_candidate_direction == "UP") or (
        side_seed == "BEAR" and breakout_candidate_direction == "DOWN"
    ):
        points += 0.05
    return _clamp01(points)


def _reversal_evidence(row: Mapping[str, Any], *, side_seed: str) -> float:
    points = 0.0
    consumer_side = _safe_text(row.get("consumer_check_side")).upper()
    if (side_seed == "BULL" and consumer_side == "SELL") or (side_seed == "BEAR" and consumer_side == "BUY"):
        points += 0.15

    consumer_reason = _safe_text(row.get("consumer_check_reason")).upper()
    if _contains_any(
        consumer_reason,
        ("UPPER_REJECT", "LOWER_REJECT", "BREAK_FAIL", "COUNTERTREND", "REVERSAL", "REJECT_CONFIRM"),
    ):
        points += 0.25

    if _safe_bool(row.get("countertrend_continuation_enabled")) or _safe_text(row.get("countertrend_continuation_action")):
        points += 0.2

    context_conflict_state = _safe_text(row.get("context_conflict_state")).upper()
    if _contains_any(context_conflict_state, ("AGAINST", "CONFLICT")):
        points += 0.1

    if _safe_text(row.get("htf_alignment_state")).upper() == "AGAINST_HTF":
        points += 0.1

    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()
    if _contains_any(previous_box_break_state, ("FAILED", "FAIL")):
        points += 0.2
    return _clamp01(points)


def _friction(row: Mapping[str, Any]) -> float:
    points = 0.0
    blocked_by = _safe_text(row.get("blocked_by")).upper()
    action_none_reason = _safe_text(row.get("action_none_reason")).upper()
    if _contains_any(f"{blocked_by}::{action_none_reason}", ("SOFT_BLOCK", "WRONG_SIDE", "WAIT", "BLOCK", "PRESSURE")):
        points += 0.25

    consumer_reason = _safe_text(row.get("consumer_check_reason")).upper()
    if _contains_any(
        consumer_reason,
        ("UPPER_REJECT", "LOWER_REJECT", "OUTER_BAND", "REBOUND_PROBE", "DIRECTIONAL_CONFLICT", "SUPPORT_REQUIRED"),
    ):
        points += 0.25

    forecast_wait_bias = _safe_text(row.get("forecast_state25_candidate_wait_bias_action")).upper()
    belief_family = _safe_text(row.get("belief_candidate_recommended_family")).upper()
    barrier_family = _safe_text(row.get("barrier_candidate_recommended_family")).upper()
    if _contains_any(f"{forecast_wait_bias}::{belief_family}::{barrier_family}", ("WAIT", "REDUCE", "RELIEF", "BLOCK", "CAUTION", "ALERT")):
        points += 0.25

    late_chase_risk_state = _safe_text(row.get("late_chase_risk_state")).upper()
    if late_chase_risk_state not in {"", "NONE", "LOW"}:
        points += 0.15
    if "ENERGY" in blocked_by:
        points += 0.1
    return _clamp01(points)


def _exhaustion_risk(row: Mapping[str, Any]) -> float:
    points = 0.0
    late_chase_risk_state = _safe_text(row.get("late_chase_risk_state")).upper()
    if late_chase_risk_state == "HIGH":
        points += 0.6
    elif late_chase_risk_state == "MEDIUM":
        points += 0.4
    elif late_chase_risk_state == "LOW":
        points += 0.2
    blocked_by = _safe_text(row.get("blocked_by")).upper()
    if "LATE" in blocked_by or "CHASE" in blocked_by:
        points += 0.2
    return _clamp01(points)


def _ambiguity(continuation_integrity: float, reversal_evidence: float, side_seed: str) -> float:
    if side_seed == "NONE":
        return 0.8
    gap = abs(float(continuation_integrity) - float(reversal_evidence))
    if float(continuation_integrity) >= 0.35 and float(reversal_evidence) >= 0.35:
        return _clamp01(0.75 - min(gap, 0.75))
    if gap <= 0.1:
        return 0.55
    if gap <= 0.2:
        return 0.35
    return 0.1


def _wait_bias_strength(row: Mapping[str, Any], *, friction: float, exhaustion_risk: float, ambiguity: float) -> float:
    boost = 0.0
    if _safe_text(row.get("forecast_state25_candidate_wait_bias_action")):
        boost += 0.1
    if _safe_text(row.get("belief_candidate_recommended_family")):
        boost += 0.05
    if _safe_text(row.get("barrier_candidate_recommended_family")):
        boost += 0.05
    return _clamp01((float(friction) * 0.5) + (float(exhaustion_risk) * 0.25) + (float(ambiguity) * 0.25) + boost)


def _dominant_side(*, side_seed: str, continuation_integrity: float, reversal_evidence: float, dominance_gap: float) -> str:
    if side_seed not in {"BULL", "BEAR"}:
        return "NONE"
    if float(dominance_gap) >= -0.1:
        return side_seed
    if float(reversal_evidence) >= 0.75 and float(continuation_integrity) <= 0.25:
        return "BEAR" if side_seed == "BULL" else "BULL"
    return "NONE"


def _dominant_mode(
    *,
    continuation_integrity: float,
    reversal_evidence: float,
    friction: float,
    ambiguity: float,
    dominance_gap: float,
    dominant_side: str,
) -> str:
    if dominant_side == "NONE":
        return "BOUNDARY"
    if float(reversal_evidence) >= 0.7 and float(continuation_integrity) <= 0.4 and float(dominance_gap) < -0.1:
        return "REVERSAL_RISK"
    if float(ambiguity) >= 0.6 and abs(float(dominance_gap)) < 0.2:
        return "BOUNDARY"
    if float(dominance_gap) > 0.15:
        if float(friction) >= 0.4:
            return "CONTINUATION_WITH_FRICTION"
        return "CONTINUATION"
    if float(dominance_gap) < -0.15:
        return "REVERSAL_RISK"
    return "BOUNDARY"


def _caution_level(*, friction: float, exhaustion_risk: float, ambiguity: float, dominance_gap: float, dominant_mode: str) -> str:
    if dominant_mode == "BOUNDARY" or float(ambiguity) >= 0.6 or abs(float(dominance_gap)) < 0.1:
        return "HIGH"
    if float(friction) >= 0.55 or float(exhaustion_risk) >= 0.55:
        return "HIGH"
    if float(friction) >= 0.3 or float(exhaustion_risk) >= 0.3 or float(ambiguity) >= 0.35:
        return "MEDIUM"
    return "LOW"


def _reason_summary(
    *,
    side_seed: str,
    side_seed_source: str,
    continuation_integrity: float,
    reversal_evidence: float,
    friction: float,
    dominance_gap: float,
    dominant_mode: str,
) -> str:
    return (
        f"seed={side_seed}/{side_seed_source}; "
        f"continuation={continuation_integrity:.2f}; "
        f"reversal={reversal_evidence:.2f}; "
        f"friction={friction:.2f}; "
        f"gap={dominance_gap:.2f}; "
        f"mode={dominant_mode}"
    )


def build_state_strength_profile_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    side_seed, side_seed_source, side_seed_confidence = _resolve_side_seed(payload)
    trend_pressure = _trend_pressure(payload, side_seed=side_seed)
    continuation_integrity = _continuation_integrity(payload, side_seed=side_seed)
    reversal_evidence = _reversal_evidence(payload, side_seed=side_seed)
    friction = _friction(payload)
    exhaustion_risk = _exhaustion_risk(payload)
    ambiguity = _ambiguity(continuation_integrity, reversal_evidence, side_seed)
    wait_bias_strength = _wait_bias_strength(payload, friction=friction, exhaustion_risk=exhaustion_risk, ambiguity=ambiguity)
    dominance_gap = round(float(continuation_integrity) - float(reversal_evidence), 4)
    dominant_side = _dominant_side(
        side_seed=side_seed,
        continuation_integrity=continuation_integrity,
        reversal_evidence=reversal_evidence,
        dominance_gap=dominance_gap,
    )
    dominant_mode = _dominant_mode(
        continuation_integrity=continuation_integrity,
        reversal_evidence=reversal_evidence,
        friction=friction,
        ambiguity=ambiguity,
        dominance_gap=dominance_gap,
        dominant_side=dominant_side,
    )
    caution_level = _caution_level(
        friction=friction,
        exhaustion_risk=exhaustion_risk,
        ambiguity=ambiguity,
        dominance_gap=dominance_gap,
        dominant_mode=dominant_mode,
    )
    reason_summary = _reason_summary(
        side_seed=side_seed,
        side_seed_source=side_seed_source,
        continuation_integrity=continuation_integrity,
        reversal_evidence=reversal_evidence,
        friction=friction,
        dominance_gap=dominance_gap,
        dominant_mode=dominant_mode,
    )

    profile = {
        "contract_version": STATE_STRENGTH_PROFILE_CONTRACT_VERSION,
        "side_seed_v1": side_seed,
        "side_seed_source_v1": side_seed_source,
        "side_seed_confidence_v1": side_seed_confidence,
        "trend_pressure_v1": trend_pressure,
        "continuation_integrity_v1": continuation_integrity,
        "reversal_evidence_v1": reversal_evidence,
        "friction_v1": friction,
        "exhaustion_risk_v1": exhaustion_risk,
        "ambiguity_v1": ambiguity,
        "wait_bias_strength_v1": wait_bias_strength,
        "dominance_gap_v1": dominance_gap,
        "dominant_side_v1": dominant_side,
        "dominant_mode_v1": dominant_mode,
        "caution_level_v1": caution_level,
        "reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "state_strength_profile_v1": profile,
        "state_strength_side_seed_v1": side_seed,
        "state_strength_side_seed_source_v1": side_seed_source,
        "state_strength_side_seed_confidence_v1": side_seed_confidence,
        "state_strength_trend_pressure_v1": trend_pressure,
        "state_strength_continuation_integrity_v1": continuation_integrity,
        "state_strength_reversal_evidence_v1": reversal_evidence,
        "state_strength_friction_v1": friction,
        "state_strength_exhaustion_risk_v1": exhaustion_risk,
        "state_strength_ambiguity_v1": ambiguity,
        "state_strength_wait_bias_strength_v1": wait_bias_strength,
        "state_strength_dominance_gap_v1": dominance_gap,
        "state_strength_dominant_side_v1": dominant_side,
        "state_strength_dominant_mode_v1": dominant_mode,
        "state_strength_caution_level_v1": caution_level,
        "state_strength_reason_summary_v1": reason_summary,
    }


def attach_state_strength_profile_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_state_strength_profile_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_state_strength_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_state_strength_profile_fields_v1(latest_signal_by_symbol)
    side_seed_counts = Counter()
    dominant_side_counts = Counter()
    dominant_mode_counts = Counter()
    caution_level_counts = Counter()
    trend_total = 0.0
    continuation_total = 0.0
    reversal_total = 0.0
    friction_total = 0.0
    gap_total = 0.0

    for row in rows_by_symbol.values():
        side_seed_counts.update([_safe_text(row.get("state_strength_side_seed_v1"))])
        dominant_side_counts.update([_safe_text(row.get("state_strength_dominant_side_v1"))])
        dominant_mode_counts.update([_safe_text(row.get("state_strength_dominant_mode_v1"))])
        caution_level_counts.update([_safe_text(row.get("state_strength_caution_level_v1"))])
        trend_total += _safe_float(row.get("state_strength_trend_pressure_v1"), 0.0)
        continuation_total += _safe_float(row.get("state_strength_continuation_integrity_v1"), 0.0)
        reversal_total += _safe_float(row.get("state_strength_reversal_evidence_v1"), 0.0)
        friction_total += _safe_float(row.get("state_strength_friction_v1"), 0.0)
        gap_total += _safe_float(row.get("state_strength_dominance_gap_v1"), 0.0)

    symbol_count = max(len(rows_by_symbol), 1)
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["state_strength_surface_available"] if rows_by_symbol else ["no_runtime_rows"],
        "symbol_count": int(len(rows_by_symbol)),
        "side_seed_count_summary": dict(side_seed_counts),
        "dominant_side_count_summary": dict(dominant_side_counts),
        "dominant_mode_count_summary": dict(dominant_mode_counts),
        "caution_level_count_summary": dict(caution_level_counts),
        "avg_trend_pressure_v1": round(trend_total / symbol_count, 4) if rows_by_symbol else 0.0,
        "avg_continuation_integrity_v1": round(continuation_total / symbol_count, 4) if rows_by_symbol else 0.0,
        "avg_reversal_evidence_v1": round(reversal_total / symbol_count, 4) if rows_by_symbol else 0.0,
        "avg_friction_v1": round(friction_total / symbol_count, 4) if rows_by_symbol else 0.0,
        "avg_dominance_gap_v1": round(gap_total / symbol_count, 4) if rows_by_symbol else 0.0,
    }
    return {
        "contract_version": STATE_STRENGTH_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_strength_summary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Strength Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- avg_continuation_integrity_v1: `{_safe_float(summary.get('avg_continuation_integrity_v1'), 0.0):.4f}`",
        f"- avg_reversal_evidence_v1: `{_safe_float(summary.get('avg_reversal_evidence_v1'), 0.0):.4f}`",
        f"- avg_friction_v1: `{_safe_float(summary.get('avg_friction_v1'), 0.0):.4f}`",
        f"- avg_dominance_gap_v1: `{_safe_float(summary.get('avg_dominance_gap_v1'), 0.0):.4f}`",
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
            f"- `{symbol}`: seed={row.get('state_strength_side_seed_v1', '')}/{row.get('state_strength_side_seed_source_v1', '')} | "
            f"dominant={row.get('state_strength_dominant_side_v1', '')}/{row.get('state_strength_dominant_mode_v1', '')} | "
            f"gap={_safe_float(row.get('state_strength_dominance_gap_v1'), 0.0):.4f} | "
            f"caution={row.get('state_strength_caution_level_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_strength_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_strength_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "state_strength_summary_latest.json"
    md_path = output_dir / "state_strength_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_state_strength_summary_markdown_v1(report))
    return report
