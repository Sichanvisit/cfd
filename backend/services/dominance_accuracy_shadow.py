from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.dominance_validation_profile import (
    DOMINANCE_VALIDATION_CONTRACT_VERSION,
    attach_dominance_validation_fields_v1,
    build_dominance_validation_row_v1,
)
from backend.services.session_bucket_helper import resolve_session_bucket_v1


DOMINANCE_ACCURACY_SHADOW_CONTRACT_VERSION = "dominance_accuracy_shadow_contract_v1"
DOMINANCE_ACCURACY_SUMMARY_VERSION = "dominance_accuracy_summary_v1"
DOMINANCE_CANDIDATE_SHADOW_REPORT_VERSION = "dominance_candidate_shadow_report_v1"


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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_dominance_accuracy_shadow_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": DOMINANCE_ACCURACY_SHADOW_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Proxy dominance accuracy and shadow-only bias recommendation layer. "
            "Builds over-veto/under-veto metrics and continuation confidence shadow actions "
            "without changing execution or state25."
        ),
        "row_level_fields_v1": [
            "dominance_accuracy_shadow_profile_v1",
            "dominance_over_veto_flag_v1",
            "dominance_under_veto_flag_v1",
            "dominance_friction_separation_state_v1",
            "dominance_boundary_dwell_risk_v1",
            "dominance_shadow_bias_candidate_state_v1",
            "dominance_shadow_bias_effect_v1",
            "dominance_shadow_bias_confidence_v1",
            "dominance_shadow_bias_reason_v1",
            "dominance_shadow_would_change_execution_v1",
            "dominance_shadow_would_change_state25_v1",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_validation(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    validation_flat_present = any(
        key in row
        for key in (
            "dominance_error_type_v1",
            "dominance_expected_side_v1",
            "dominance_expected_mode_v1",
            "dominance_expected_caution_level_v1",
            "dominance_vs_canonical_alignment_v1",
            "dominance_shadow_dominant_mode_v1",
        )
    )
    if not isinstance(row.get("dominance_validation_profile_v1"), Mapping):
        if validation_flat_present:
            row["dominance_validation_profile_v1"] = {
                "contract_version": DOMINANCE_VALIDATION_CONTRACT_VERSION,
                "dominance_expected_side_v1": _safe_text(row.get("dominance_expected_side_v1")).upper(),
                "dominance_expected_mode_v1": _safe_text(row.get("dominance_expected_mode_v1")).upper(),
                "dominance_expected_caution_level_v1": _safe_text(row.get("dominance_expected_caution_level_v1")).upper(),
                "dominance_vs_canonical_alignment_v1": _safe_text(row.get("dominance_vs_canonical_alignment_v1")).upper(),
                "dominance_error_type_v1": _safe_text(row.get("dominance_error_type_v1")).upper(),
            }
        elif any(
            key in row
            for key in (
                "dominance_error_type_v1",
                "dominance_expected_mode_v1",
                "dominance_shadow_dominant_mode_v1",
            )
        ):
            row.update(build_dominance_validation_row_v1(row))
        else:
            row = dict(attach_dominance_validation_fields_v1({"_": row}).get("_", row))
    return row


def _resolve_session_bucket(row: Mapping[str, Any]) -> str:
    bucket = _safe_text(row.get("canonical_session_bucket_v1") or row.get("session_bucket_v1"))
    if bucket:
        return bucket
    return resolve_session_bucket_v1(row.get("timestamp") or row.get("time") or row.get("generated_at"))


def _friction_separation_state(row: Mapping[str, Any]) -> str:
    expected_mode = _safe_text(row.get("dominance_expected_mode_v1")).upper()
    actual_mode = _safe_text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    if expected_mode != "CONTINUATION_WITH_FRICTION":
        return "NOT_APPLICABLE"
    if actual_mode == "CONTINUATION_WITH_FRICTION":
        return "SEPARATED"
    if actual_mode == "REVERSAL_RISK":
        return "MISREAD_AS_REVERSAL"
    return "MIXED"


def _shadow_effect(error_type: str) -> tuple[str, str, str]:
    if error_type in {
        "CONTINUATION_UNDERPROMOTED",
        "FRICTION_MISREAD_AS_REVERSAL",
        "BOUNDARY_STAYED_TOO_LONG",
        "REVERSAL_OVERCALLED",
    }:
        confidence = "HIGH" if error_type == "FRICTION_MISREAD_AS_REVERSAL" else "MEDIUM"
        return ("READY", "RAISE_CONTINUATION_CONFIDENCE", confidence)
    if error_type == "TRUE_REVERSAL_MISSED":
        return ("READY", "LOWER_CONTINUATION_CONFIDENCE", "HIGH")
    return ("OBSERVE_ONLY", "KEEP_NEUTRAL", "LOW")


def build_dominance_accuracy_shadow_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_validation(row or {})
    error_type = _safe_text(payload.get("dominance_error_type_v1")).upper()
    session_bucket = _resolve_session_bucket(payload)
    over_veto = error_type in {
        "CONTINUATION_UNDERPROMOTED",
        "REVERSAL_OVERCALLED",
        "FRICTION_MISREAD_AS_REVERSAL",
        "BOUNDARY_STAYED_TOO_LONG",
    }
    under_veto = error_type == "TRUE_REVERSAL_MISSED"
    friction_state = _friction_separation_state(payload)
    boundary_dwell_risk = error_type == "BOUNDARY_STAYED_TOO_LONG"
    candidate_state, effect, confidence = _shadow_effect(error_type)
    alignment = _safe_text(payload.get("dominance_vs_canonical_alignment_v1")).upper()
    would_change_execution = candidate_state == "READY" and alignment in {"DIVERGED", "WAITING"}
    would_change_state25 = candidate_state == "READY"
    reason = f"error_type={error_type.lower() or 'aligned'}::{session_bucket}"

    profile = {
        "contract_version": DOMINANCE_ACCURACY_SHADOW_CONTRACT_VERSION,
        "upstream_contract_version": DOMINANCE_VALIDATION_CONTRACT_VERSION,
        "dominance_over_veto_flag_v1": bool(over_veto),
        "dominance_under_veto_flag_v1": bool(under_veto),
        "dominance_friction_separation_state_v1": friction_state,
        "dominance_boundary_dwell_risk_v1": bool(boundary_dwell_risk),
        "dominance_shadow_bias_candidate_state_v1": candidate_state,
        "dominance_shadow_bias_effect_v1": effect,
        "dominance_shadow_bias_confidence_v1": confidence,
        "dominance_shadow_bias_reason_v1": reason,
        "dominance_shadow_session_bucket_v1": session_bucket,
        "dominance_shadow_would_change_execution_v1": bool(would_change_execution),
        "dominance_shadow_would_change_state25_v1": bool(would_change_state25),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "dominance_accuracy_shadow_profile_v1": profile,
        "dominance_over_veto_flag_v1": bool(over_veto),
        "dominance_under_veto_flag_v1": bool(under_veto),
        "dominance_friction_separation_state_v1": friction_state,
        "dominance_boundary_dwell_risk_v1": bool(boundary_dwell_risk),
        "dominance_shadow_bias_candidate_state_v1": candidate_state,
        "dominance_shadow_bias_effect_v1": effect,
        "dominance_shadow_bias_confidence_v1": confidence,
        "dominance_shadow_bias_reason_v1": reason,
        "dominance_shadow_session_bucket_v1": session_bucket,
        "dominance_shadow_would_change_execution_v1": bool(would_change_execution),
        "dominance_shadow_would_change_state25_v1": bool(would_change_state25),
    }


def attach_dominance_accuracy_shadow_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_validation(raw)
        row.update(build_dominance_accuracy_shadow_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_dominance_accuracy_shadow_reports_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_dominance_accuracy_shadow_fields_v1(latest_signal_by_symbol)
    symbol_count = len(rows_by_symbol)
    over_veto_count = 0
    under_veto_count = 0
    friction_relevant = 0
    friction_good = 0
    boundary_relevant = 0
    boundary_bad = 0
    candidate_state_counts = Counter()
    effect_counts = Counter()
    candidate_count_by_session = Counter()

    for row in rows_by_symbol.values():
        if _safe_bool(row.get("dominance_over_veto_flag_v1")):
            over_veto_count += 1
        if _safe_bool(row.get("dominance_under_veto_flag_v1")):
            under_veto_count += 1
        friction_state = _safe_text(row.get("dominance_friction_separation_state_v1"))
        if friction_state != "NOT_APPLICABLE":
            friction_relevant += 1
            if friction_state == "SEPARATED":
                friction_good += 1
        if _safe_text(row.get("dominance_shadow_dominant_mode_v1")).upper() == "BOUNDARY" or _safe_text(
            row.get("dominance_expected_mode_v1")
        ).upper() == "BOUNDARY":
            boundary_relevant += 1
            if _safe_bool(row.get("dominance_boundary_dwell_risk_v1")):
                boundary_bad += 1
        candidate_state = _safe_text(row.get("dominance_shadow_bias_candidate_state_v1"))
        effect = _safe_text(row.get("dominance_shadow_bias_effect_v1"))
        bucket = _safe_text(row.get("dominance_shadow_session_bucket_v1"))
        candidate_state_counts.update([candidate_state])
        effect_counts.update([effect])
        if bucket:
            candidate_count_by_session.update([bucket])

    accuracy_summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["proxy_accuracy_available_future_join_pending"] if rows_by_symbol else ["no_runtime_rows"]
        ),
        "symbol_count": int(symbol_count),
        "candidate_count": int(candidate_state_counts.get("READY", 0)),
        "over_veto_rate": round(over_veto_count / symbol_count, 4) if symbol_count else None,
        "under_veto_rate": round(under_veto_count / symbol_count, 4) if symbol_count else None,
        "friction_separation_quality": (
            round(friction_good / friction_relevant, 4) if friction_relevant else None
        ),
        "boundary_dwell_quality": (
            round(1.0 - (boundary_bad / boundary_relevant), 4) if boundary_relevant else None
        ),
        "candidate_count_by_session": dict(candidate_count_by_session),
        "future_outcome_join_status_v1": "PENDING",
        "discount_comparison_status_v1": "PENDING",
        "guard_promotion_alignment_status_v1": "PENDING",
    }
    shadow_summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["dominance_shadow_bias_candidates_available"] if candidate_state_counts.get("READY", 0) else ["observe_only_or_pending"]
        ),
        "symbol_count": int(symbol_count),
        "candidate_state_count_summary": dict(candidate_state_counts),
        "effect_count_summary": dict(effect_counts),
        "candidate_count_by_session": dict(candidate_count_by_session),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "contract_version": DOMINANCE_ACCURACY_SHADOW_CONTRACT_VERSION,
        "accuracy_summary": accuracy_summary,
        "shadow_summary": shadow_summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_dominance_accuracy_shadow_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    accuracy = _mapping(payload.get("accuracy_summary"))
    shadow = _mapping(payload.get("shadow_summary"))
    lines = [
        "# Dominance Accuracy / Shadow Bias",
        "",
        f"- generated_at: `{accuracy.get('generated_at', '')}`",
        f"- status: `{accuracy.get('status', '')}`",
        f"- symbol_count: `{int(accuracy.get('symbol_count', 0) or 0)}`",
        f"- over_veto_rate: `{accuracy.get('over_veto_rate')}`",
        f"- under_veto_rate: `{accuracy.get('under_veto_rate')}`",
        f"- friction_separation_quality: `{accuracy.get('friction_separation_quality')}`",
        f"- boundary_dwell_quality: `{accuracy.get('boundary_dwell_quality')}`",
        "",
        "## Shadow Bias Effect Count",
        "",
    ]
    for key, count in dict(shadow.get("effect_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: over_veto={row.get('dominance_over_veto_flag_v1', False)} | "
            f"under_veto={row.get('dominance_under_veto_flag_v1', False)} | "
            f"friction={row.get('dominance_friction_separation_state_v1', '')} | "
            f"effect={row.get('dominance_shadow_bias_effect_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_dominance_accuracy_shadow_reports_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_dominance_accuracy_shadow_reports_v1(latest_signal_by_symbol)
    json_path = output_dir / "dominance_accuracy_shadow_latest.json"
    md_path = output_dir / "dominance_accuracy_shadow_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_dominance_accuracy_shadow_markdown_v1(report))
    return report
