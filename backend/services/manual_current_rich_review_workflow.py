"""Operational review workflow for current-rich draft canonical promotion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_VERSION = "manual_current_rich_review_workflow_v0"

MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_COLUMNS = [
    "review_item_id",
    "review_batch_id",
    "episode_id",
    "queue_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "manual_teacher_confidence",
    "promotion_readiness",
    "review_priority_tier",
    "capture_priority",
    "row_count",
    "unique_signal_minutes",
    "calibration_value_bucket",
    "episode_detail_status",
    "promotion_decision_reason",
    "promotion_blocking_reason",
    "promotion_followup_needed",
    "suggested_review_focus",
    "suggested_review_action",
    "required_trace_fields",
    "review_trace_status",
    "promotion_reviewer",
    "promotion_reviewed_at",
    "workflow_note",
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


def _review_batch_id(priority_tier: str, readiness: str) -> str:
    tier = _to_text(priority_tier, "").lower()
    readiness = _to_text(readiness, "").lower()
    if tier == "ready_high":
        return "promotion_signoff_p1"
    if tier == "ready_normal":
        return "promotion_signoff_p2"
    if tier == "review_needed_high_priority":
        return "review_batch_p1"
    if tier == "review_needed_normal":
        return "review_batch_p2"
    if tier == "review_needed_low_signal":
        return "review_batch_p3"
    if tier == "control_only" or readiness == "do_not_promote":
        return "control_archive"
    return "review_batch_misc"


def _suggested_review_focus(followup_needed: str, blocking_reason: str) -> str:
    followup = _to_text(followup_needed, "").lower()
    blocker = _to_text(blocking_reason, "").lower()
    if followup == "manual_chart_recheck":
        return "chart_recheck"
    if followup == "fill_episode_coordinates":
        return "episode_detail_completion"
    if followup == "raise_confidence_then_recheck":
        return "confidence_reassessment"
    if followup == "collect_higher_value_current_rich_examples":
        return "current_rich_value_upgrade"
    if followup == "promotion_signoff":
        return "canonical_signoff"
    if followup == "keep_as_control_only":
        return "control_only"
    if "manual_review_pending" in blocker:
        return "manual_first_pass"
    return "general_review"


def _suggested_review_action(followup_needed: str, readiness: str) -> str:
    followup = _to_text(followup_needed, "").lower()
    readiness = _to_text(readiness, "").lower()
    if followup == "manual_chart_recheck":
        return "review_chart_and_confirm_hold_or_promote"
    if followup == "fill_episode_coordinates":
        return "fill_entry_exit_coordinates_before_decision"
    if followup == "raise_confidence_then_recheck":
        return "raise_confidence_then_revisit_promotion"
    if followup == "collect_higher_value_current_rich_examples":
        return "collect_more_signal_dense_examples"
    if followup == "promotion_signoff" or readiness == "ready":
        return "approve_or_reject_canonical_promotion"
    if followup == "keep_as_control_only" or readiness == "do_not_promote":
        return "archive_as_control_reference"
    return "manual_recheck_then_decide"


def _required_trace_fields(readiness: str) -> str:
    base = [
        "promotion_reviewer",
        "promotion_reviewed_at",
        "promotion_decision_reason",
        "promotion_followup_needed",
    ]
    if _to_text(readiness, "").lower() != "ready":
        base.append("promotion_blocking_reason")
    return "|".join(base)


def _review_trace_status(row: Mapping[str, Any]) -> str:
    has_reviewer = bool(_to_text(row.get("promotion_reviewer", ""), ""))
    has_reviewed_at = bool(_to_text(row.get("promotion_reviewed_at", ""), ""))
    return "review_traced" if has_reviewer or has_reviewed_at else "trace_missing"


def build_manual_current_rich_review_workflow(
    promotion_gate: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    gate = promotion_gate.copy() if promotion_gate is not None else pd.DataFrame()
    if gate.empty:
        empty = pd.DataFrame(columns=MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_COLUMNS)
        summary = {
            "review_workflow_version": MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_VERSION,
            "row_count": 0,
            "batch_counts": {},
            "focus_counts": {},
            "trace_status_counts": {},
            "next_review_batch_id": "",
        }
        return empty, summary

    rows: list[dict[str, Any]] = []
    for _, row in gate.iterrows():
        row_dict = row.to_dict()
        readiness = _to_text(row_dict.get("promotion_readiness", ""), "").lower()
        priority_tier = _to_text(row_dict.get("review_priority_tier", ""), "").lower()
        batch_id = _review_batch_id(priority_tier, readiness)
        focus = _suggested_review_focus(
            _to_text(row_dict.get("promotion_followup_needed", ""), ""),
            _to_text(row_dict.get("promotion_blocking_reason", ""), ""),
        )
        action = _suggested_review_action(
            _to_text(row_dict.get("promotion_followup_needed", ""), ""),
            readiness,
        )
        trace_status = _review_trace_status(row_dict)

        rows.append(
            {
                "review_item_id": f"current_rich_review::{_to_text(row_dict.get('episode_id', ''), '')}",
                "review_batch_id": batch_id,
                "episode_id": _to_text(row_dict.get("episode_id", ""), ""),
                "queue_id": _to_text(row_dict.get("queue_id", ""), ""),
                "symbol": _to_text(row_dict.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(row_dict.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(row_dict.get("manual_wait_teacher_label", ""), "").lower(),
                "manual_teacher_confidence": _to_text(row_dict.get("manual_teacher_confidence", ""), "").lower(),
                "promotion_readiness": readiness,
                "review_priority_tier": priority_tier,
                "capture_priority": _to_text(row_dict.get("capture_priority", ""), "").lower(),
                "row_count": _to_text(row_dict.get("row_count", ""), ""),
                "unique_signal_minutes": _to_text(row_dict.get("unique_signal_minutes", ""), ""),
                "calibration_value_bucket": _to_text(row_dict.get("calibration_value_bucket", ""), "").lower(),
                "episode_detail_status": _to_text(row_dict.get("episode_detail_status", ""), "").lower(),
                "promotion_decision_reason": _to_text(row_dict.get("promotion_decision_reason", ""), ""),
                "promotion_blocking_reason": _to_text(row_dict.get("promotion_blocking_reason", ""), ""),
                "promotion_followup_needed": _to_text(row_dict.get("promotion_followup_needed", ""), ""),
                "suggested_review_focus": focus,
                "suggested_review_action": action,
                "required_trace_fields": _required_trace_fields(readiness),
                "review_trace_status": trace_status,
                "promotion_reviewer": _to_text(row_dict.get("promotion_reviewer", ""), ""),
                "promotion_reviewed_at": _to_text(row_dict.get("promotion_reviewed_at", ""), ""),
                "workflow_note": (
                    f"{focus}::{action}::{_to_text(row_dict.get('recommended_next_action', ''), '')}"
                ),
            }
        )

    workflow = pd.DataFrame(rows)
    workflow["batch_rank"] = workflow["review_batch_id"].map(
        {
            "promotion_signoff_p1": 0,
            "promotion_signoff_p2": 1,
            "review_batch_p1": 2,
            "review_batch_p2": 3,
            "review_batch_p3": 4,
            "control_archive": 5,
        }
    ).fillna(6)
    workflow = workflow.sort_values(
        by=["batch_rank", "symbol", "anchor_time", "episode_id"],
        ascending=[True, True, True, True],
        kind="stable",
    ).drop(columns=["batch_rank"]).reset_index(drop=True)

    for column in MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_COLUMNS:
        if column not in workflow.columns:
            workflow[column] = ""
    workflow = workflow[MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_COLUMNS].copy()

    next_batch = workflow[
        workflow["review_batch_id"].fillna("").astype(str).ne("control_archive")
    ]
    summary = {
        "review_workflow_version": MANUAL_CURRENT_RICH_REVIEW_WORKFLOW_VERSION,
        "row_count": int(len(workflow)),
        "batch_counts": workflow["review_batch_id"].value_counts(dropna=False).to_dict(),
        "focus_counts": workflow["suggested_review_focus"].value_counts(dropna=False).to_dict(),
        "trace_status_counts": workflow["review_trace_status"].value_counts(dropna=False).to_dict(),
        "next_review_batch_id": _to_text(next_batch.iloc[0]["review_batch_id"], "") if not next_batch.empty else "",
    }
    return workflow, summary


def render_manual_current_rich_review_workflow_markdown(
    summary: Mapping[str, Any],
    workflow: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Review Workflow v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- next review batch: `{summary.get('next_review_batch_id', '')}`",
        f"- batch counts: `{summary.get('batch_counts', {})}`",
        f"- focus counts: `{summary.get('focus_counts', {})}`",
        f"- trace status counts: `{summary.get('trace_status_counts', {})}`",
        "",
        "## Workflow Preview",
    ]
    preview = workflow.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("review_batch_id", "")),
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("anchor_time", "")),
                        _to_text(row.get("manual_wait_teacher_label", "")),
                        _to_text(row.get("review_priority_tier", "")),
                        _to_text(row.get("suggested_review_focus", "")),
                        _to_text(row.get("review_trace_status", "")),
                    ]
                )
            )
            lines.append(f"  action: {_to_text(row.get('suggested_review_action', ''), '')}")
    return "\n".join(lines) + "\n"
