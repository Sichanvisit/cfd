"""Trace-sheet scaffold for the highest-priority current-rich review batch."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_CURRENT_RICH_REVIEW_TRACE_VERSION = "manual_current_rich_review_trace_v0"

MANUAL_CURRENT_RICH_REVIEW_TRACE_COLUMNS = [
    "trace_row_id",
    "review_batch_id",
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "review_priority_tier",
    "suggested_review_focus",
    "suggested_review_action",
    "required_trace_fields",
    "trace_prompt",
    "trace_status",
    "promotion_reviewer",
    "promotion_reviewed_at",
    "promotion_decision_reason",
    "promotion_blocking_reason",
    "promotion_followup_needed",
    "canonical_decision",
    "trace_note",
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


def _trace_lookup(entries: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if entries is None or entries.empty or "episode_id" not in entries.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def _default_target_batch(workflow: pd.DataFrame) -> str:
    if workflow.empty or "review_batch_id" not in workflow.columns:
        return ""
    for batch_id in [
        "review_batch_p1",
        "promotion_signoff_p1",
        "review_batch_p2",
        "promotion_signoff_p2",
        "review_batch_p3",
    ]:
        if workflow["review_batch_id"].fillna("").astype(str).eq(batch_id).any():
            return batch_id
    return _to_text(workflow.iloc[0].get("review_batch_id", ""), "")


def _trace_prompt(row: Mapping[str, Any]) -> str:
    return (
        f"Review {_to_text(row.get('symbol', ''), '')} "
        f"{_to_text(row.get('anchor_time', ''), '')} "
        f"for {_to_text(row.get('suggested_review_focus', ''), '')}; "
        "fill reviewer, reviewed_at, decision_reason, blocking_reason, followup_needed, canonical_decision."
    )


def build_manual_current_rich_review_trace(
    workflow: pd.DataFrame,
    *,
    trace_entries: pd.DataFrame | None = None,
    target_batch_id: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = workflow.copy() if workflow is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_CURRENT_RICH_REVIEW_TRACE_COLUMNS)
        summary = {
            "review_trace_version": MANUAL_CURRENT_RICH_REVIEW_TRACE_VERSION,
            "target_batch_id": "",
            "row_count": 0,
            "trace_status_counts": {},
        }
        return empty, summary

    batch_id = _to_text(target_batch_id, "") or _default_target_batch(source)
    scoped = source[source["review_batch_id"].fillna("").astype(str).eq(batch_id)].copy()
    trace_lookup = _trace_lookup(trace_entries)
    rows: list[dict[str, Any]] = []
    for _, row in scoped.iterrows():
        row_dict = row.to_dict()
        trace_entry = trace_lookup.get(_to_text(row_dict.get("episode_id", ""), ""), {})
        merged_reviewer = _to_text(trace_entry.get("promotion_reviewer", ""), "") or _to_text(
            row_dict.get("promotion_reviewer", ""), ""
        )
        merged_reviewed_at = _to_text(trace_entry.get("promotion_reviewed_at", ""), "") or _to_text(
            row_dict.get("promotion_reviewed_at", ""), ""
        )
        merged_reason = _to_text(trace_entry.get("promotion_decision_reason", ""), "") or _to_text(
            row_dict.get("promotion_decision_reason", ""), ""
        )
        merged_blocking = _to_text(trace_entry.get("promotion_blocking_reason", ""), "") or _to_text(
            row_dict.get("promotion_blocking_reason", ""), ""
        )
        merged_followup = _to_text(trace_entry.get("promotion_followup_needed", ""), "") or _to_text(
            row_dict.get("promotion_followup_needed", ""), ""
        )
        merged_canonical_decision = _to_text(trace_entry.get("canonical_decision", ""), "")
        merged_note = _to_text(trace_entry.get("trace_note", ""), "")
        trace_status = (
            "trace_filled"
            if merged_reviewer or merged_reviewed_at or merged_canonical_decision
            else (
                "trace_ready_for_fill"
                if _to_text(row_dict.get("review_trace_status", ""), "") == "trace_missing"
                else "trace_already_present"
            )
        )
        rows.append(
            {
                "trace_row_id": f"current_rich_trace::{_to_text(row_dict.get('episode_id', ''), '')}",
                "review_batch_id": batch_id,
                "episode_id": _to_text(row_dict.get("episode_id", ""), ""),
                "symbol": _to_text(row_dict.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(row_dict.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(row_dict.get("manual_wait_teacher_label", ""), "").lower(),
                "review_priority_tier": _to_text(row_dict.get("review_priority_tier", ""), "").lower(),
                "suggested_review_focus": _to_text(row_dict.get("suggested_review_focus", ""), "").lower(),
                "suggested_review_action": _to_text(row_dict.get("suggested_review_action", ""), "").lower(),
                "required_trace_fields": _to_text(row_dict.get("required_trace_fields", ""), ""),
                "trace_prompt": _trace_prompt(row_dict),
                "trace_status": trace_status,
                "promotion_reviewer": merged_reviewer,
                "promotion_reviewed_at": merged_reviewed_at,
                "promotion_decision_reason": merged_reason,
                "promotion_blocking_reason": merged_blocking,
                "promotion_followup_needed": merged_followup,
                "canonical_decision": merged_canonical_decision,
                "trace_note": merged_note,
            }
        )

    trace = pd.DataFrame(rows)
    for column in MANUAL_CURRENT_RICH_REVIEW_TRACE_COLUMNS:
        if column not in trace.columns:
            trace[column] = ""
    trace = trace[MANUAL_CURRENT_RICH_REVIEW_TRACE_COLUMNS].copy()

    summary = {
        "review_trace_version": MANUAL_CURRENT_RICH_REVIEW_TRACE_VERSION,
        "target_batch_id": batch_id,
        "row_count": int(len(trace)),
        "trace_status_counts": trace["trace_status"].value_counts(dropna=False).to_dict()
        if not trace.empty
        else {},
    }
    return trace, summary


def render_manual_current_rich_review_trace_markdown(
    summary: Mapping[str, Any],
    trace: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Review Trace Sheet v0",
        "",
        f"- target batch: `{summary.get('target_batch_id', '')}`",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- trace statuses: `{summary.get('trace_status_counts', {})}`",
        "",
        "## Trace Rows",
    ]
    if trace.empty:
        lines.append("- none")
    else:
        for _, row in trace.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("review_batch_id", "")),
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("anchor_time", "")),
                        _to_text(row.get("manual_wait_teacher_label", "")),
                        _to_text(row.get("trace_status", "")),
                    ]
                )
            )
            lines.append(f"  prompt: {_to_text(row.get('trace_prompt', ''), '')}")
    return "\n".join(lines) + "\n"
