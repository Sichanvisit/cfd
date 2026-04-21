"""Unified approval log for manual calibration decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_CALIBRATION_APPROVAL_LOG_VERSION = "manual_calibration_approval_log_v0"

MANUAL_CALIBRATION_APPROVAL_LOG_COLUMNS = [
    "approval_event_id",
    "event_type",
    "event_target_type",
    "event_target_id",
    "decision",
    "decision_by",
    "decision_at",
    "reason_code",
    "reason_summary",
    "linked_artifacts",
    "followup_required",
    "followup_due_at",
    "followup_status",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _event_id(prefix: str, target_id: str) -> str:
    return f"{prefix}::{target_id}"


def _reason_code(text: str) -> str:
    value = _to_text(text, "")
    if "::" in value:
        return value.split("::", 1)[0]
    return value or "unspecified"


def _promotion_events(trace_entries: pd.DataFrame) -> list[dict[str, Any]]:
    if trace_entries.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in trace_entries.iterrows():
        row_dict = row.to_dict()
        episode_id = _to_text(row_dict.get("episode_id", ""), "")
        if not episode_id:
            continue
        decision = _to_text(row_dict.get("canonical_decision", ""), "").lower()
        reason = _to_text(row_dict.get("promotion_decision_reason", ""), "")
        followup = _to_text(row_dict.get("promotion_followup_needed", ""), "")
        rows.append(
            {
                "approval_event_id": _event_id("promotion_gate_review", episode_id),
                "event_type": "promotion_gate_review",
                "event_target_type": "current_rich_episode",
                "event_target_id": episode_id,
                "decision": decision or "review_pending",
                "decision_by": _to_text(row_dict.get("promotion_reviewer", ""), ""),
                "decision_at": _to_text(row_dict.get("promotion_reviewed_at", ""), ""),
                "reason_code": _reason_code(reason),
                "reason_summary": reason,
                "linked_artifacts": "manual_current_rich_review_trace_entries.csv|manual_current_rich_promotion_gate_latest.csv",
                "followup_required": bool(followup),
                "followup_due_at": "",
                "followup_status": "open" if followup else "none",
            }
        )
    return rows


def _correction_events(correction_runs: pd.DataFrame) -> list[dict[str, Any]]:
    if correction_runs.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in correction_runs.iterrows():
        row_dict = row.to_dict()
        run_id = _to_text(row_dict.get("correction_run_id", ""), "")
        if not run_id:
            continue
        decision = _to_text(row_dict.get("decision", ""), "").lower()
        followup_required = decision in {"hold_for_more_truth", "hold_for_patch_execution"}
        rows.append(
            {
                "approval_event_id": _event_id("correction_loop", run_id),
                "event_type": "correction_loop_accept_reject",
                "event_target_type": "mismatch_family",
                "event_target_id": _to_text(row_dict.get("family_key", ""), ""),
                "decision": decision,
                "decision_by": _to_text(row_dict.get("reviewer", ""), ""),
                "decision_at": _to_text(row_dict.get("finished_at", ""), ""),
                "reason_code": _reason_code(_to_text(row_dict.get("decision_reason", ""), "")),
                "reason_summary": _to_text(row_dict.get("decision_reason", ""), ""),
                "linked_artifacts": "manual_vs_heuristic_correction_runs_latest.csv|manual_vs_heuristic_patch_draft_latest.csv",
                "followup_required": followup_required,
                "followup_due_at": "",
                "followup_status": "open" if followup_required else "closed",
            }
        )
    return rows


def _post_promotion_events(audit: pd.DataFrame) -> list[dict[str, Any]]:
    if audit.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in audit.iterrows():
        row_dict = row.to_dict()
        episode_id = _to_text(row_dict.get("episode_id", ""), "")
        result = _to_text(row_dict.get("audit_result", ""), "")
        if not episode_id or not result:
            continue
        followup_required = result in {"needs_relabel", "needs_note_update", "demote_from_canonical"}
        rows.append(
            {
                "approval_event_id": _event_id("post_promotion_audit", episode_id),
                "event_type": "post_promotion_audit_review",
                "event_target_type": "canonical_episode",
                "event_target_id": episode_id,
                "decision": result,
                "decision_by": _to_text(row_dict.get("audit_reviewer", ""), ""),
                "decision_at": _to_text(row_dict.get("audit_executed_at", ""), ""),
                "reason_code": _reason_code(_to_text(row_dict.get("audit_reason", ""), "")),
                "reason_summary": _to_text(row_dict.get("audit_reason", ""), ""),
                "linked_artifacts": "manual_current_rich_post_promotion_audit_latest.csv",
                "followup_required": followup_required,
                "followup_due_at": "",
                "followup_status": "open" if followup_required else "closed",
            }
        )
    return rows


def _shadow_bounded_candidate_events(approval_frame: pd.DataFrame) -> list[dict[str, Any]]:
    if approval_frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in approval_frame.iterrows():
        row_dict = row.to_dict()
        stage_event_id = _to_text(row_dict.get("stage_event_id", ""), "")
        approval_status = _to_text(row_dict.get("approval_status", ""), "")
        if not stage_event_id or not approval_status:
            continue
        rows.append(
            {
                "approval_event_id": _event_id("shadow_bounded_candidate", stage_event_id),
                "event_type": "shadow_bounded_candidate_review",
                "event_target_type": "shadow_candidate_stage",
                "event_target_id": stage_event_id,
                "decision": approval_status,
                "decision_by": _to_text(row_dict.get("decision_by", ""), ""),
                "decision_at": _to_text(row_dict.get("decision_at", ""), ""),
                "reason_code": _reason_code(_to_text(row_dict.get("reason_summary", ""), "")),
                "reason_summary": _to_text(row_dict.get("reason_summary", ""), ""),
                "linked_artifacts": "semantic_shadow_bounded_candidate_stage_latest.csv|semantic_shadow_bounded_candidate_approval_latest.csv",
                "followup_required": approval_status in {"pending_human_review", "hold_candidate", "approved_pending_activation"},
                "followup_due_at": "",
                "followup_status": "open"
                if approval_status in {"pending_human_review", "hold_candidate", "approved_pending_activation"}
                else "closed",
            }
        )
    return rows


def build_manual_calibration_approval_log(
    review_trace_entries: pd.DataFrame,
    correction_runs: pd.DataFrame | None = None,
    post_promotion_audit: pd.DataFrame | None = None,
    shadow_bounded_candidate_approval: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    rows.extend(_promotion_events(review_trace_entries.copy() if review_trace_entries is not None else pd.DataFrame()))
    rows.extend(_correction_events(correction_runs.copy() if correction_runs is not None else pd.DataFrame()))
    rows.extend(_post_promotion_events(post_promotion_audit.copy() if post_promotion_audit is not None else pd.DataFrame()))
    rows.extend(
        _shadow_bounded_candidate_events(
            shadow_bounded_candidate_approval.copy() if shadow_bounded_candidate_approval is not None else pd.DataFrame()
        )
    )

    approval_log = pd.DataFrame(rows)
    if approval_log.empty:
        empty = pd.DataFrame(columns=MANUAL_CALIBRATION_APPROVAL_LOG_COLUMNS)
        summary = {
            "approval_log_version": MANUAL_CALIBRATION_APPROVAL_LOG_VERSION,
            "row_count": 0,
            "event_type_counts": {},
            "decision_counts": {},
            "followup_open_count": 0,
        }
        return empty, summary

    approval_log["decision_at_sort"] = pd.to_datetime(
        approval_log["decision_at"],
        errors="coerce",
    )
    approval_log = approval_log.sort_values(
        by=["decision_at_sort", "event_type", "event_target_id"],
        ascending=[False, True, True],
        kind="stable",
    ).drop(columns=["decision_at_sort"]).reset_index(drop=True)

    for column in MANUAL_CALIBRATION_APPROVAL_LOG_COLUMNS:
        if column not in approval_log.columns:
            approval_log[column] = ""
    approval_log = approval_log[MANUAL_CALIBRATION_APPROVAL_LOG_COLUMNS].copy()

    summary = {
        "approval_log_version": MANUAL_CALIBRATION_APPROVAL_LOG_VERSION,
        "row_count": int(len(approval_log)),
        "event_type_counts": approval_log["event_type"].value_counts(dropna=False).to_dict()
        if not approval_log.empty
        else {},
        "decision_counts": approval_log["decision"].value_counts(dropna=False).to_dict()
        if not approval_log.empty
        else {},
        "followup_open_count": int(
            approval_log["followup_status"].fillna("").astype(str).eq("open").sum()
        )
        if not approval_log.empty
        else 0,
    }
    return approval_log, summary


def render_manual_calibration_approval_log_markdown(
    summary: Mapping[str, Any],
    approval_log: pd.DataFrame,
) -> str:
    lines = [
        "# Manual Calibration Approval Log v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- event types: `{summary.get('event_type_counts', {})}`",
        f"- decisions: `{summary.get('decision_counts', {})}`",
        f"- followup open count: `{summary.get('followup_open_count', 0)}`",
        "",
        "## Approval Preview",
    ]
    if approval_log.empty:
        lines.append("- none")
    else:
        for _, row in approval_log.head(12).iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("event_type", ""), ""),
                        _to_text(row.get("decision", ""), ""),
                        _to_text(row.get("event_target_id", ""), ""),
                    ]
                )
            )
            lines.append(f"  reason: {_to_text(row.get('reason_summary', ''), '')}")
    return "\n".join(lines) + "\n"
