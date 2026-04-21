from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.canonical_surface_builder import build_canonical_surface_row_v1
from backend.services.state_structure_dominance_profile import (
    STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
    attach_state_structure_dominance_fields_v1,
    build_state_structure_dominance_profile_row_v1,
)


DOMINANCE_VALIDATION_CONTRACT_VERSION = "dominance_validation_contract_v1"
DOMINANCE_VALIDATION_SUMMARY_VERSION = "dominance_validation_summary_v1"
DOMINANCE_ERROR_TYPE_ENUM_V1 = (
    "ALIGNED",
    "CONTINUATION_UNDERPROMOTED",
    "REVERSAL_OVERCALLED",
    "BOUNDARY_STAYED_TOO_LONG",
    "FRICTION_MISREAD_AS_REVERSAL",
    "TRUE_REVERSAL_MISSED",
)
DOMINANCE_ALIGNMENT_ENUM_V1 = ("MATCH", "DIVERGED", "WAITING")


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


def build_dominance_validation_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": DOMINANCE_VALIDATION_CONTRACT_VERSION,
        "status": "READY",
        "dominance_error_type_enum_v1": list(DOMINANCE_ERROR_TYPE_ENUM_V1),
        "dominance_alignment_enum_v1": list(DOMINANCE_ALIGNMENT_ENUM_V1),
        "row_level_fields_v1": [
            "dominance_validation_profile_v1",
            "dominance_expected_side_v1",
            "dominance_expected_mode_v1",
            "dominance_expected_caution_level_v1",
            "dominance_vs_canonical_alignment_v1",
            "dominance_should_have_done_candidate_v1",
            "dominance_error_type_v1",
            "overweighted_caution_fields_v1",
            "undervalued_continuation_evidence_v1",
            "dominance_validation_reason_summary_v1",
        ],
        "description": (
            "Validation layer that joins dominance shadow interpretation with canonical surface and "
            "should-have-done style review signals without changing execution behavior."
        ),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    dominance_flat_present = any(
        key in row
        for key in (
            "dominance_shadow_dominant_side_v1",
            "dominance_shadow_dominant_mode_v1",
            "dominance_shadow_caution_level_v1",
            "dominance_shadow_gap_v1",
        )
    )
    canonical_flat_present = any(
        key in row
        for key in (
            "canonical_direction_annotation_v1",
            "canonical_phase_v1",
            "canonical_runtime_execution_alignment_v1",
        )
    )

    if not isinstance(row.get("state_structure_dominance_profile_v1"), Mapping):
        if dominance_flat_present:
            row["state_structure_dominance_profile_v1"] = {
                "contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
                "dominance_shadow_dominant_side_v1": _safe_text(row.get("dominance_shadow_dominant_side_v1")).upper(),
                "dominance_shadow_dominant_mode_v1": _safe_text(row.get("dominance_shadow_dominant_mode_v1")).upper(),
                "dominance_shadow_caution_level_v1": _safe_text(row.get("dominance_shadow_caution_level_v1")).upper(),
                "dominance_shadow_gap_v1": round(_safe_float(row.get("dominance_shadow_gap_v1"), 0.0), 4),
            }
        else:
            row = dict(attach_state_structure_dominance_fields_v1({"_": row}).get("_", row))

    if not canonical_flat_present:
        row.update(build_canonical_surface_row_v1(row))
    return row


def _expected_side(row: Mapping[str, Any]) -> str:
    direction = _safe_text(row.get("canonical_direction_annotation_v1")).upper()
    if direction == "UP":
        return "BULL"
    if direction == "DOWN":
        return "BEAR"
    return "NONE"


def _expected_mode(row: Mapping[str, Any], *, expected_side: str) -> str:
    canonical_phase = _safe_text(row.get("canonical_phase_v1")).upper()
    veto_tier = _safe_text(row.get("consumer_veto_tier_v1")).upper()
    if canonical_phase == "REVERSAL" or veto_tier == "REVERSAL_OVERRIDE":
        return "REVERSAL_RISK"
    if expected_side in {"BULL", "BEAR"} and veto_tier == "FRICTION_ONLY":
        return "CONTINUATION_WITH_FRICTION"
    if expected_side in {"BULL", "BEAR"} and canonical_phase == "CONTINUATION":
        return "CONTINUATION"
    return "BOUNDARY"


def _expected_caution_level(row: Mapping[str, Any], *, expected_mode: str) -> str:
    veto_tier = _safe_text(row.get("consumer_veto_tier_v1")).upper()
    canonical_alignment = _safe_text(row.get("canonical_runtime_execution_alignment_v1")).upper()
    if veto_tier == "REVERSAL_OVERRIDE" or (canonical_alignment == "DIVERGED" and expected_mode == "REVERSAL_RISK"):
        return "HIGH"
    if expected_mode == "CONTINUATION_WITH_FRICTION":
        return "MEDIUM"
    if expected_mode == "BOUNDARY":
        return "MEDIUM"
    return "LOW"


def _validation_alignment(row: Mapping[str, Any], *, expected_side: str) -> str:
    actual_side = _safe_text(row.get("dominance_shadow_dominant_side_v1")).upper()
    if expected_side == "NONE" or actual_side == "NONE":
        return "WAITING"
    return "MATCH" if expected_side == actual_side else "DIVERGED"


def _should_have_done_candidate(row: Mapping[str, Any], *, expected_side: str, expected_mode: str, alignment: str) -> bool:
    actual_mode = _safe_text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    canonical_alignment = _safe_text(row.get("canonical_runtime_execution_alignment_v1")).upper()
    final_side = _safe_text(row.get("execution_diff_final_action_side")).upper()
    promoted_side = _safe_text(row.get("execution_diff_promoted_action_side")).upper()
    if alignment == "DIVERGED":
        return True
    if canonical_alignment == "DIVERGED":
        return True
    if promoted_side and promoted_side != final_side:
        return True
    if expected_mode != actual_mode:
        return True
    if expected_side in {"BULL", "BEAR"} and final_side in {"BUY", "SELL"}:
        expected_action = "BUY" if expected_side == "BULL" else "SELL"
        if final_side != expected_action:
            return True
    return False


def _dominance_error_type(row: Mapping[str, Any], *, expected_mode: str, alignment: str, candidate: bool) -> str:
    actual_mode = _safe_text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    if not candidate and alignment == "MATCH" and actual_mode == expected_mode:
        return "ALIGNED"
    if expected_mode in {"CONTINUATION", "CONTINUATION_WITH_FRICTION"} and actual_mode == "BOUNDARY":
        return "CONTINUATION_UNDERPROMOTED"
    if expected_mode == "CONTINUATION_WITH_FRICTION" and actual_mode == "REVERSAL_RISK":
        return "FRICTION_MISREAD_AS_REVERSAL"
    if expected_mode in {"CONTINUATION", "CONTINUATION_WITH_FRICTION"} and actual_mode == "REVERSAL_RISK":
        return "REVERSAL_OVERCALLED"
    if expected_mode == "REVERSAL_RISK" and actual_mode != "REVERSAL_RISK":
        return "TRUE_REVERSAL_MISSED"
    if candidate and actual_mode == "BOUNDARY":
        return "BOUNDARY_STAYED_TOO_LONG"
    return "ALIGNED"


def _overweighted_caution_fields(row: Mapping[str, Any], *, expected_mode: str) -> list[str]:
    fields: list[str] = []
    if expected_mode not in {"CONTINUATION", "CONTINUATION_WITH_FRICTION"}:
        return fields
    consumer_check_reason = _safe_text(row.get("consumer_check_reason"))
    blocked_by = _safe_text(row.get("blocked_by"))
    forecast_wait = _safe_text(row.get("forecast_state25_candidate_wait_bias_action"))
    belief_family = _safe_text(row.get("belief_candidate_recommended_family"))
    barrier_family = _safe_text(row.get("barrier_candidate_recommended_family"))
    if consumer_check_reason:
        fields.append(consumer_check_reason)
    if blocked_by:
        fields.append(f"blocked_by:{blocked_by}")
    if forecast_wait:
        fields.append(f"forecast:{forecast_wait}")
    if belief_family:
        fields.append(f"belief:{belief_family}")
    if barrier_family:
        fields.append(f"barrier:{barrier_family}")
    return fields[:5]


def _undervalued_continuation_evidence(row: Mapping[str, Any], *, expected_mode: str) -> list[str]:
    fields: list[str] = []
    if expected_mode not in {"CONTINUATION", "CONTINUATION_WITH_FRICTION"}:
        return fields
    if _safe_text(row.get("previous_box_break_state")).upper() == "BREAKOUT_HELD":
        fields.append("breakout_held")
    relation = _safe_text(row.get("previous_box_relation")).upper()
    if relation in {"ABOVE", "BELOW"}:
        fields.append(f"previous_box_{relation.lower()}")
    if _safe_text(row.get("htf_alignment_state")).upper() == "WITH_HTF":
        fields.append("with_htf")
    if _safe_bool(row.get("directional_continuation_overlay_enabled")):
        fields.append("overlay_enabled")
    breakout_candidate_direction = _safe_text(row.get("breakout_candidate_direction")).upper()
    if breakout_candidate_direction in {"UP", "DOWN"}:
        fields.append(f"breakout_candidate_{breakout_candidate_direction.lower()}")
    structure_bias = _safe_text(row.get("few_candle_structure_bias_v1")).upper()
    if structure_bias == "CONTINUATION_FAVOR":
        fields.append("local_structure_continuation_favor")
    hold_quality = _safe_text(row.get("breakout_hold_quality_v1")).upper()
    if hold_quality in {"STABLE", "STRONG"}:
        fields.append(f"hold_{hold_quality.lower()}")
    body_drive = _safe_text(row.get("body_drive_state_v1")).upper()
    if body_drive in {"WEAK_DRIVE", "STRONG_DRIVE"}:
        fields.append(f"drive_{body_drive.lower()}")
    return fields[:6]


def _reason_summary(
    *,
    expected_side: str,
    expected_mode: str,
    expected_caution: str,
    alignment: str,
    candidate: bool,
    error_type: str,
) -> str:
    return (
        f"expected_side={expected_side}; "
        f"expected_mode={expected_mode}; "
        f"expected_caution={expected_caution}; "
        f"alignment={alignment}; "
        f"candidate={str(bool(candidate)).lower()}; "
        f"error_type={error_type}"
    )


def build_dominance_validation_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    expected_side = _expected_side(payload)
    expected_mode = _expected_mode(payload, expected_side=expected_side)
    expected_caution = _expected_caution_level(payload, expected_mode=expected_mode)
    alignment = _validation_alignment(payload, expected_side=expected_side)
    candidate = _should_have_done_candidate(
        payload,
        expected_side=expected_side,
        expected_mode=expected_mode,
        alignment=alignment,
    )
    error_type = _dominance_error_type(
        payload,
        expected_mode=expected_mode,
        alignment=alignment,
        candidate=candidate,
    )
    overweighted_caution = _overweighted_caution_fields(payload, expected_mode=expected_mode)
    undervalued_continuation = _undervalued_continuation_evidence(payload, expected_mode=expected_mode)
    reason_summary = _reason_summary(
        expected_side=expected_side,
        expected_mode=expected_mode,
        expected_caution=expected_caution,
        alignment=alignment,
        candidate=candidate,
        error_type=error_type,
    )

    profile = {
        "contract_version": DOMINANCE_VALIDATION_CONTRACT_VERSION,
        "upstream_contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
        "dominance_expected_side_v1": expected_side,
        "dominance_expected_mode_v1": expected_mode,
        "dominance_expected_caution_level_v1": expected_caution,
        "dominance_vs_canonical_alignment_v1": alignment,
        "dominance_should_have_done_candidate_v1": bool(candidate),
        "dominance_error_type_v1": error_type,
        "overweighted_caution_fields_v1": list(overweighted_caution),
        "undervalued_continuation_evidence_v1": list(undervalued_continuation),
        "dominance_validation_reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "dominance_validation_profile_v1": profile,
        "dominance_expected_side_v1": expected_side,
        "dominance_expected_mode_v1": expected_mode,
        "dominance_expected_caution_level_v1": expected_caution,
        "dominance_vs_canonical_alignment_v1": alignment,
        "dominance_should_have_done_candidate_v1": bool(candidate),
        "dominance_error_type_v1": error_type,
        "overweighted_caution_fields_v1": list(overweighted_caution),
        "undervalued_continuation_evidence_v1": list(undervalued_continuation),
        "dominance_validation_reason_summary_v1": reason_summary,
    }


def attach_dominance_validation_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_dominance_validation_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_dominance_validation_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_dominance_validation_fields_v1(latest_signal_by_symbol)
    error_counts = Counter()
    alignment_counts = Counter()
    expected_mode_counts = Counter()
    actual_mode_counts = Counter()
    candidate_counts = Counter()
    candidate_count_by_symbol = Counter()
    for symbol, row in rows_by_symbol.items():
        error_counts.update([_safe_text(row.get("dominance_error_type_v1"))])
        alignment_counts.update([_safe_text(row.get("dominance_vs_canonical_alignment_v1"))])
        expected_mode_counts.update([_safe_text(row.get("dominance_expected_mode_v1"))])
        actual_mode_counts.update([_safe_text(row.get("dominance_shadow_dominant_mode_v1"))])
        if _safe_bool(row.get("dominance_should_have_done_candidate_v1")):
            candidate_counts.update(["CANDIDATE"])
            candidate_count_by_symbol.update([str(symbol)])
        else:
            candidate_counts.update(["NO_CANDIDATE"])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["dominance_validation_available"] if rows_by_symbol else ["no_runtime_rows"],
        "symbol_count": int(len(rows_by_symbol)),
        "candidate_count": int(candidate_counts.get("CANDIDATE", 0)),
        "dominance_error_type_count_summary": dict(error_counts),
        "canonical_alignment_count_summary": dict(alignment_counts),
        "expected_mode_count_summary": dict(expected_mode_counts),
        "actual_dominant_mode_count_summary": dict(actual_mode_counts),
        "candidate_count_by_symbol": dict(candidate_count_by_symbol),
    }
    return {
        "contract_version": DOMINANCE_VALIDATION_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_dominance_validation_summary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Dominance Validation Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- candidate_count: `{int(summary.get('candidate_count', 0) or 0)}`",
        "",
        "## Dominance Error Type Count",
        "",
    ]
    for key, count in dict(summary.get("dominance_error_type_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: expected={row.get('dominance_expected_side_v1', '')}/{row.get('dominance_expected_mode_v1', '')} | "
            f"actual={row.get('dominance_shadow_dominant_side_v1', '')}/{row.get('dominance_shadow_dominant_mode_v1', '')} | "
            f"error={row.get('dominance_error_type_v1', '')} | "
            f"candidate={row.get('dominance_should_have_done_candidate_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_dominance_validation_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_dominance_validation_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "dominance_validation_summary_latest.json"
    md_path = output_dir / "dominance_validation_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_dominance_validation_summary_markdown_v1(report))
    return report
