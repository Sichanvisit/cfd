from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.bounded_candidate_shadow_apply_contract import (
    BOUNDED_CANDIDATE_SHADOW_APPLY_CONTRACT_VERSION,
    build_bounded_candidate_shadow_apply_summary_v1,
)


BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_CONTRACT_VERSION = "bounded_candidate_evaluation_dashboard_contract_v1"
BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_SUMMARY_VERSION = "bounded_candidate_evaluation_dashboard_summary_v1"

EVALUATION_OUTCOME_ENUM_V1 = (
    "PROMOTE",
    "KEEP_OBSERVING",
    "EXPIRE_WITHOUT_PROMOTION",
    "ROLLBACK",
)
EVALUATION_ASSESSMENT_ENUM_V1 = (
    "POSITIVE",
    "CAUTIOUS_POSITIVE",
    "NEUTRAL",
    "BLOCKED",
    "NEGATIVE",
)


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


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_bounded_candidate_evaluation_dashboard_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F11 candidate evaluation dashboard. Aggregates F10 shadow apply sessions into candidate-level "
            "evaluation outcomes and governance summaries."
        ),
        "upstream_contract_versions_v1": [
            BOUNDED_CANDIDATE_SHADOW_APPLY_CONTRACT_VERSION,
        ],
        "evaluation_outcome_enum_v1": list(EVALUATION_OUTCOME_ENUM_V1),
        "evaluation_assessment_enum_v1": list(EVALUATION_ASSESSMENT_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_candidate_evaluation_candidate_id_v1",
            "bounded_candidate_evaluation_session_id_v1",
            "bounded_candidate_evaluation_outcome_v1",
            "bounded_candidate_evaluation_assessment_v1",
            "bounded_candidate_evaluation_candidate_hit_count_v1",
            "bounded_candidate_evaluation_sample_coverage_v1",
            "bounded_candidate_evaluation_promoted_like_transition_count_v1",
            "bounded_candidate_evaluation_harmful_transition_count_v1",
            "bounded_candidate_over_veto_delta_pct_v1",
            "bounded_candidate_under_veto_delta_pct_v1",
            "bounded_candidate_unverified_widening_delta_pct_v1",
            "bounded_candidate_cross_symbol_drift_score_v1",
            "bounded_candidate_evaluation_reason_summary_v1",
        ],
        "control_rules_v1": [
            "F11 is an operational evaluation layer and must not reinterpret dominant_side, dominance_gap, rejection split, or structure gate",
            "evaluation is derived from F10 before/after shadow rows and candidate sessions",
            "PROMOTE requires positive directional effect plus adequate sample coverage and no harmful widening",
            "ROLLBACK requires harmful transition, under-veto deterioration, widening deterioration, or blocked shadow execution",
            "KEEP_OBSERVING is used when signal is promising but sample coverage is still shallow",
            "EXPIRE_WITHOUT_PROMOTION is used when there is no meaningful change after sufficient observation",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _state_rank(flow_state: str) -> int:
    return {
        "FLOW_OPPOSED": 0,
        "FLOW_UNCONFIRMED": 1,
        "FLOW_BUILDING": 2,
        "FLOW_CONFIRMED": 3,
    }.get(_text(flow_state).upper(), -1)


def _same_symbol_cross_window_stability(candidate: Mapping[str, Any]) -> float:
    payload = _mapping(candidate)
    validation_scope = _mapping(payload.get("validation_scope_v1"))
    retained_count = len(list(validation_scope.get("same_symbol_retained_window_ids_v1") or []))
    min_required = int(
        _mapping(payload.get("candidate_graduation_requirements_v1")).get(
            "minimum_shadow_windows_required_v1",
            2,
        )
        or 2
    )
    if min_required <= 0:
        return 1.0
    return round(min(1.0, retained_count / float(min_required)), 4)


def _sample_coverage(candidate: Mapping[str, Any], matched_rows: list[dict[str, Any]]) -> float:
    payload = _mapping(candidate)
    min_required = int(
        _mapping(payload.get("candidate_graduation_requirements_v1")).get(
            "minimum_shadow_windows_required_v1",
            2,
        )
        or 2
    )
    if min_required <= 0:
        return 1.0
    return round(min(1.0, len(matched_rows) / float(min_required)), 4)


def _evaluation_metrics_for_rows(candidate: Mapping[str, Any], matched_rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _mapping(candidate)
    direction = _text(payload.get("direction")).upper()

    promoted_like_count = 0
    harmful_count = 0
    over_before = 0
    over_after = 0
    under_before = 0
    under_after = 0
    unverified_before = 0
    unverified_after = 0

    for row in matched_rows:
        truth_state = _text(row.get("flow_candidate_truth_state_v1")).upper()
        before_state = _text(row.get("flow_support_state_before_v1")).upper()
        after_state = _text(row.get("flow_support_state_after_v1")).upper()
        before_rank = _state_rank(before_state)
        after_rank = _state_rank(after_state)

        if direction == "RELAX":
            if after_rank > before_rank:
                promoted_like_count += 1
            elif after_rank < before_rank:
                harmful_count += 1
        elif direction == "TIGHTEN":
            if after_rank < before_rank:
                promoted_like_count += 1
            elif after_rank > before_rank:
                harmful_count += 1

        if truth_state == "WIDEN_EXPECTED":
            if before_rank <= 1:
                over_before += 1
            if after_rank <= 1:
                over_after += 1
        if truth_state == "TIGHTEN_EXPECTED":
            if before_rank >= 2:
                under_before += 1
            if after_rank >= 2:
                under_after += 1

        if truth_state != "WIDEN_EXPECTED":
            if before_rank >= 2:
                unverified_before += 1
            if after_rank >= 2:
                unverified_after += 1

    row_count = max(1, len(matched_rows))
    return {
        "candidate_hit_count": int(len(matched_rows)),
        "promoted_like_transition_count": int(promoted_like_count),
        "harmful_transition_count": int(harmful_count),
        "over_veto_rate_before": round(over_before / row_count, 4),
        "over_veto_rate_after": round(over_after / row_count, 4),
        "under_veto_rate_before": round(under_before / row_count, 4),
        "under_veto_rate_after": round(under_after / row_count, 4),
        "unverified_widening_before": round(unverified_before / row_count, 4),
        "unverified_widening_after": round(unverified_after / row_count, 4),
    }


def _cross_symbol_drift_score(candidate: Mapping[str, Any]) -> float:
    payload = _mapping(candidate)
    validation_scope = _mapping(payload.get("validation_scope_v1"))
    if _bool(validation_scope.get("cross_symbol_required_v1")):
        return 0.05
    return 0.0


def _evaluation_outcome(
    *,
    session_state: str,
    row_session_state: str,
    metrics: Mapping[str, Any],
    sample_coverage: float,
    stability: float,
    cross_symbol_drift_score: float,
) -> tuple[str, str, str]:
    session_upper = _text(session_state).upper()
    row_session_upper = _text(row_session_state).upper()
    over_before = _float(_mapping(metrics).get("over_veto_rate_before"), 0.0)
    over_after = _float(_mapping(metrics).get("over_veto_rate_after"), 0.0)
    under_before = _float(_mapping(metrics).get("under_veto_rate_before"), 0.0)
    under_after = _float(_mapping(metrics).get("under_veto_rate_after"), 0.0)
    widening_before = _float(_mapping(metrics).get("unverified_widening_before"), 0.0)
    widening_after = _float(_mapping(metrics).get("unverified_widening_after"), 0.0)
    promoted_like_count = int(_mapping(metrics).get("promoted_like_transition_count", 0) or 0)
    harmful_count = int(_mapping(metrics).get("harmful_transition_count", 0) or 0)
    hit_count = int(_mapping(metrics).get("candidate_hit_count", 0) or 0)

    if row_session_upper == "BLOCKED" or session_upper == "BLOCKED":
        return "ROLLBACK", "BLOCKED", "blocked_shadow_execution"
    if harmful_count > 0 or under_after > under_before or widening_after > widening_before or cross_symbol_drift_score > 0.2:
        return "ROLLBACK", "NEGATIVE", "harmful_or_risky_drift_detected"
    if promoted_like_count > 0 and sample_coverage >= 1.0 and stability >= 1.0 and over_after < over_before:
        return "PROMOTE", "POSITIVE", "stable_positive_shadow_improvement"
    if promoted_like_count > 0:
        return "KEEP_OBSERVING", "CAUTIOUS_POSITIVE", "positive_signal_but_more_coverage_required"
    if session_upper == "HOLD":
        return "KEEP_OBSERVING", "NEUTRAL", "held_due_to_scope_priority"
    if session_upper == "ACTIVE" and hit_count <= 0:
        return "KEEP_OBSERVING", "NEUTRAL", "active_session_without_hits"
    if sample_coverage >= 1.0 and promoted_like_count <= 0:
        return "EXPIRE_WITHOUT_PROMOTION", "NEUTRAL", "sufficient_observation_without_meaningful_change"
    return "KEEP_OBSERVING", "NEUTRAL", "observation_window_still_shallow"


def _evaluate_candidate_entries_v1(
    shadow_report: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    payload = _mapping(shadow_report)
    rows_by_symbol = {
        _text(symbol): dict(_mapping(row))
        for symbol, row in _mapping(payload.get("rows_by_symbol")).items()
    }
    sessions = {
        _text(candidate_id): _mapping(session)
        for candidate_id, session in _mapping(payload.get("candidate_apply_sessions_v1")).items()
    }
    candidates = {
        _text(candidate_id): _mapping(candidate)
        for candidate_id, candidate in _mapping(payload.get("candidate_objects_v1")).items()
    }

    entries: dict[str, dict[str, Any]] = {}
    for candidate_id, session in sessions.items():
        candidate = candidates.get(candidate_id, {})
        matched_rows = [
            row
            for row in rows_by_symbol.values()
            if _text(row.get("bounded_apply_candidate_id_v1")) == candidate_id
        ]
        metrics = _evaluation_metrics_for_rows(candidate, matched_rows)
        stability = _same_symbol_cross_window_stability(candidate)
        coverage = _sample_coverage(candidate, matched_rows)
        cross_symbol_drift = _cross_symbol_drift_score(candidate)
        row_session_state = ""
        if matched_rows:
            row_session_state = _text(matched_rows[0].get("bounded_apply_session_state_v1"))
        outcome, assessment, reason_core = _evaluation_outcome(
            session_state=_text(session.get("session_state_v1")),
            row_session_state=row_session_state,
            metrics=metrics,
            sample_coverage=coverage,
            stability=stability,
            cross_symbol_drift_score=cross_symbol_drift,
        )

        over_delta = round(_float(metrics.get("over_veto_rate_after")) - _float(metrics.get("over_veto_rate_before")), 4)
        under_delta = round(_float(metrics.get("under_veto_rate_after")) - _float(metrics.get("under_veto_rate_before")), 4)
        widening_delta = round(
            _float(metrics.get("unverified_widening_after")) - _float(metrics.get("unverified_widening_before")),
            4,
        )
        evaluation_window_start = _text(session.get("started_at"))
        evaluation_window_end = _text(session.get("scheduled_review_at"))
        reason = (
            f"candidate_id={candidate_id}; "
            f"session_state={_text(session.get('session_state_v1')) or 'UNKNOWN'}; "
            f"outcome={outcome}; "
            f"assessment={assessment}; "
            f"reason={reason_core}; "
            f"sample_coverage={coverage}; "
            f"stability={stability}; "
            f"over_delta={over_delta}; "
            f"under_delta={under_delta}; "
            f"widening_delta={widening_delta}; "
            f"cross_symbol_drift={cross_symbol_drift}"
        )
        entries[candidate_id] = {
            "candidate_id": candidate_id,
            "apply_session_id": _text(session.get("apply_session_id")),
            "symbol": _text(candidate.get("symbol")),
            "learning_key": _text(candidate.get("learning_key")),
            "evaluation_window_start": evaluation_window_start,
            "evaluation_window_end": evaluation_window_end,
            "affected_row_count": int(metrics.get("candidate_hit_count", 0) or 0),
            "over_veto_rate_before": _float(metrics.get("over_veto_rate_before"), 0.0),
            "over_veto_rate_after": _float(metrics.get("over_veto_rate_after"), 0.0),
            "under_veto_rate_before": _float(metrics.get("under_veto_rate_before"), 0.0),
            "under_veto_rate_after": _float(metrics.get("under_veto_rate_after"), 0.0),
            "unverified_widening_before": _float(metrics.get("unverified_widening_before"), 0.0),
            "unverified_widening_after": _float(metrics.get("unverified_widening_after"), 0.0),
            "same_symbol_cross_window_stability": float(stability),
            "cross_symbol_drift_score": float(cross_symbol_drift),
            "sample_coverage": float(coverage),
            "candidate_hit_count": int(metrics.get("candidate_hit_count", 0) or 0),
            "promoted_like_transition_count": int(metrics.get("promoted_like_transition_count", 0) or 0),
            "harmful_transition_count": int(metrics.get("harmful_transition_count", 0) or 0),
            "over_veto_delta_pct": float(over_delta),
            "under_veto_delta_pct": float(under_delta),
            "unverified_widening_delta_pct": float(widening_delta),
            "evaluation_outcome": outcome,
            "evaluation_assessment_v1": assessment,
            "evaluation_reason_summary_v1": reason,
        }
    return entries


def _attach_evaluation_fields_to_rows_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    evaluation_entries: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows = {str(key): dict(_mapping(value)) for key, value in dict(rows_by_symbol or {}).items()}
    entries = {
        _text(candidate_id): _mapping(entry)
        for candidate_id, entry in dict(evaluation_entries or {}).items()
    }
    for symbol, row in rows.items():
        candidate_id = _text(row.get("bounded_apply_candidate_id_v1")) or _text(
            row.get("bounded_calibration_candidate_primary_candidate_id_v1")
        )
        entry = entries.get(candidate_id, {})
        row["bounded_candidate_evaluation_candidate_id_v1"] = _text(entry.get("candidate_id"))
        row["bounded_candidate_evaluation_session_id_v1"] = _text(entry.get("apply_session_id"))
        row["bounded_candidate_evaluation_outcome_v1"] = _text(entry.get("evaluation_outcome")) or "NONE"
        row["bounded_candidate_evaluation_assessment_v1"] = _text(entry.get("evaluation_assessment_v1")) or "NONE"
        row["bounded_candidate_evaluation_candidate_hit_count_v1"] = int(entry.get("candidate_hit_count", 0) or 0)
        row["bounded_candidate_evaluation_sample_coverage_v1"] = _float(entry.get("sample_coverage"), 0.0)
        row["bounded_candidate_evaluation_promoted_like_transition_count_v1"] = int(
            entry.get("promoted_like_transition_count", 0) or 0
        )
        row["bounded_candidate_evaluation_harmful_transition_count_v1"] = int(
            entry.get("harmful_transition_count", 0) or 0
        )
        row["bounded_candidate_over_veto_delta_pct_v1"] = _float(entry.get("over_veto_delta_pct"), 0.0)
        row["bounded_candidate_under_veto_delta_pct_v1"] = _float(entry.get("under_veto_delta_pct"), 0.0)
        row["bounded_candidate_unverified_widening_delta_pct_v1"] = _float(
            entry.get("unverified_widening_delta_pct"),
            0.0,
        )
        row["bounded_candidate_cross_symbol_drift_score_v1"] = _float(entry.get("cross_symbol_drift_score"), 0.0)
        row["bounded_candidate_evaluation_reason_summary_v1"] = _text(entry.get("evaluation_reason_summary_v1"))
        rows[str(symbol)] = row
    return rows


def attach_bounded_candidate_evaluation_dashboard_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    shadow_report = build_bounded_candidate_shadow_apply_summary_v1(latest_signal_by_symbol)
    evaluation_entries = _evaluate_candidate_entries_v1(shadow_report)
    return _attach_evaluation_fields_to_rows_v1(
        _mapping(shadow_report.get("rows_by_symbol")),
        evaluation_entries,
    )


def build_bounded_candidate_evaluation_dashboard_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    shadow_report = build_bounded_candidate_shadow_apply_summary_v1(latest_signal_by_symbol)
    evaluation_entries = _evaluate_candidate_entries_v1(shadow_report)
    rows_by_symbol = _attach_evaluation_fields_to_rows_v1(
        _mapping(shadow_report.get("rows_by_symbol")),
        evaluation_entries,
    )

    outcome_counts: dict[str, int] = {}
    assessment_counts: dict[str, int] = {}
    symbol_apply_counts: dict[str, int] = {}
    learning_key_apply_counts: dict[str, int] = {}
    shared_parameter_apply_count = 0
    cross_symbol_warning_count = 0

    for entry in evaluation_entries.values():
        outcome = _text(entry.get("evaluation_outcome"))
        assessment = _text(entry.get("evaluation_assessment_v1"))
        symbol = _text(entry.get("symbol"))
        learning_key = _text(entry.get("learning_key"))
        if outcome:
            outcome_counts[outcome] = int(outcome_counts.get(outcome, 0) or 0) + 1
        if assessment:
            assessment_counts[assessment] = int(assessment_counts.get(assessment, 0) or 0) + 1
        if symbol:
            symbol_apply_counts[symbol] = int(symbol_apply_counts.get(symbol, 0) or 0) + 1
        if learning_key:
            learning_key_apply_counts[learning_key] = int(learning_key_apply_counts.get(learning_key, 0) or 0) + 1
            if learning_key.startswith("common.") or learning_key.startswith("shared."):
                shared_parameter_apply_count += 1
        if _float(entry.get("cross_symbol_drift_score"), 0.0) > 0.0:
            cross_symbol_warning_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": (
            ["bounded_candidate_evaluation_dashboard_available"]
            if rows_by_symbol
            else ["no_rows_for_bounded_candidate_evaluation_dashboard"]
        ),
        "symbol_count": int(len(rows_by_symbol)),
        "active_apply_session_count": int(
            _mapping(_mapping(shadow_report.get("summary")).get("apply_session_state_count_summary")).get("ACTIVE", 0) or 0
        ),
        "candidate_outcome_count_summary": dict(outcome_counts),
        "candidate_assessment_count_summary": dict(assessment_counts),
        "promote_count": int(outcome_counts.get("PROMOTE", 0) or 0),
        "keep_observing_count": int(outcome_counts.get("KEEP_OBSERVING", 0) or 0),
        "expire_count": int(outcome_counts.get("EXPIRE_WITHOUT_PROMOTION", 0) or 0),
        "rollback_count": int(outcome_counts.get("ROLLBACK", 0) or 0),
        "symbol_apply_count_summary": dict(symbol_apply_counts),
        "learning_key_apply_count_summary": dict(learning_key_apply_counts),
        "shared_parameter_apply_count": int(shared_parameter_apply_count),
        "cross_symbol_warning_count": int(cross_symbol_warning_count),
    }
    return {
        "contract_version": BOUNDED_CANDIDATE_EVALUATION_DASHBOARD_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
        "candidate_evaluation_entries_v1": evaluation_entries,
        "candidate_apply_sessions_v1": _mapping(shadow_report.get("candidate_apply_sessions_v1")),
    }


def render_bounded_candidate_evaluation_dashboard_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    entries = _mapping(payload.get("candidate_evaluation_entries_v1"))
    lines = [
        "# Bounded Candidate Evaluation Dashboard",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- active_apply_session_count: {summary.get('active_apply_session_count', 0)}",
        f"- candidate_outcome_count_summary: {json.dumps(summary.get('candidate_outcome_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_assessment_count_summary: {json.dumps(summary.get('candidate_assessment_count_summary', {}), ensure_ascii=False)}",
        f"- promote_count: {summary.get('promote_count', 0)}",
        f"- keep_observing_count: {summary.get('keep_observing_count', 0)}",
        f"- expire_count: {summary.get('expire_count', 0)}",
        f"- rollback_count: {summary.get('rollback_count', 0)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: candidate={row.get('bounded_candidate_evaluation_candidate_id_v1', '')}, "
            f"outcome={row.get('bounded_candidate_evaluation_outcome_v1', '')}, "
            f"assessment={row.get('bounded_candidate_evaluation_assessment_v1', '')}, "
            f"coverage={row.get('bounded_candidate_evaluation_sample_coverage_v1', 0.0)}, "
            f"promoted_like={row.get('bounded_candidate_evaluation_promoted_like_transition_count_v1', 0)}, "
            f"harmful={row.get('bounded_candidate_evaluation_harmful_transition_count_v1', 0)}"
        )
    lines.extend(["", "## Candidate Evaluations"])
    for candidate_id, entry in entries.items():
        lines.append(
            f"- {candidate_id}: outcome={entry.get('evaluation_outcome', '')}, "
            f"assessment={entry.get('evaluation_assessment_v1', '')}, "
            f"hits={entry.get('candidate_hit_count', 0)}, "
            f"coverage={entry.get('sample_coverage', 0.0)}, "
            f"over_delta={entry.get('over_veto_delta_pct', 0.0)}, "
            f"under_delta={entry.get('under_veto_delta_pct', 0.0)}, "
            f"widening_delta={entry.get('unverified_widening_delta_pct', 0.0)}, "
            f"drift={entry.get('cross_symbol_drift_score', 0.0)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_candidate_evaluation_dashboard_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_bounded_candidate_evaluation_dashboard_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "bounded_candidate_evaluation_dashboard_latest.json"
    markdown_path = output_dir / "bounded_candidate_evaluation_dashboard_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_bounded_candidate_evaluation_dashboard_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
