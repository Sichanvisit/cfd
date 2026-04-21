"""Post-promotion audit layer for current-rich rows promoted toward canonical."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_VERSION = "manual_current_rich_post_promotion_audit_v0"

MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_COLUMNS = [
    "promotion_audit_id",
    "episode_id",
    "canonical_row_id",
    "promoted_at",
    "promoted_by",
    "promotion_reason",
    "promotion_source",
    "audit_due_at_short",
    "audit_due_at_long",
    "audit_executed_at",
    "audit_status",
    "heuristic_match_after_promotion",
    "heuristic_gap_after_promotion",
    "family_consistency_after_promotion",
    "scene_consistency_after_promotion",
    "audit_result",
    "audit_reason",
    "audit_reviewer",
    "keep_canonical",
    "needs_relabel",
    "needs_note_update",
    "demote_from_canonical",
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


def _to_dt(value: object) -> datetime | None:
    text = _to_text(value, "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _is_promoted_decision(value: object) -> bool:
    decision = _to_text(value, "").lower()
    return decision in {
        "promote_to_canonical",
        "canonical",
        "validated",
        "promote_to_validated",
    }


def _audit_lookup(entries: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if entries is None or entries.empty or "episode_id" not in entries.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def _canonical_lookup(canonical: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if canonical is None or canonical.empty or "episode_id" not in canonical.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in canonical.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def _comparison_lookup(comparison: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if comparison is None or comparison.empty or "episode_id" not in comparison.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in comparison.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def _family_consistency(comparison_row: Mapping[str, Any], canonical_row: Mapping[str, Any]) -> str:
    manual_family = _to_text(
        comparison_row.get("manual_wait_teacher_family", "") or canonical_row.get("manual_wait_teacher_family", ""),
        "",
    ).lower()
    heuristic_family = _to_text(comparison_row.get("heuristic_wait_family", ""), "").lower()
    if not manual_family:
        return "unknown"
    if not heuristic_family:
        return "heuristic_blank"
    return "aligned" if manual_family == heuristic_family else "diverged"


def _scene_consistency(canonical_row: Mapping[str, Any], comparison_row: Mapping[str, Any]) -> str:
    canonical_scene = _to_text(canonical_row.get("scene_id", ""), "")
    comparison_scene = _to_text(comparison_row.get("scene_id", ""), "")
    if not canonical_scene and not comparison_scene:
        return "unknown"
    if canonical_scene == comparison_scene:
        return "aligned"
    return "diverged"


def _audit_status(
    *,
    promoted_at: datetime | None,
    audit_executed_at: datetime | None,
    now: datetime,
) -> str:
    if promoted_at is not None and now.tzinfo is None and promoted_at.tzinfo is not None:
        now = now.replace(tzinfo=promoted_at.tzinfo)
    elif promoted_at is not None and now.tzinfo is not None and promoted_at.tzinfo is None:
        promoted_at = promoted_at.replace(tzinfo=now.tzinfo)
    if audit_executed_at is not None and now.tzinfo is None and audit_executed_at.tzinfo is not None:
        now = now.replace(tzinfo=audit_executed_at.tzinfo)
    elif audit_executed_at is not None and now.tzinfo is not None and audit_executed_at.tzinfo is None:
        audit_executed_at = audit_executed_at.replace(tzinfo=now.tzinfo)

    if audit_executed_at is not None:
        return "audit_executed"
    if promoted_at is None:
        return "promotion_time_missing"
    short_due = promoted_at + timedelta(days=3)
    long_due = promoted_at + timedelta(days=14)
    if now >= long_due:
        return "overdue_long"
    if now >= short_due:
        return "due_short"
    return "scheduled"


def build_manual_current_rich_post_promotion_audit(
    review_trace_entries: pd.DataFrame,
    canonical: pd.DataFrame | None = None,
    comparison: pd.DataFrame | None = None,
    *,
    audit_entries: pd.DataFrame | None = None,
    now: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    trace_source = review_trace_entries.copy() if review_trace_entries is not None else pd.DataFrame()
    if trace_source.empty:
        empty = pd.DataFrame(columns=MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_COLUMNS)
        summary = {
            "post_promotion_audit_version": MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_VERSION,
            "row_count": 0,
            "audit_status_counts": {},
            "audit_result_counts": {},
            "due_count": 0,
            "overdue_count": 0,
        }
        return empty, summary

    canonical_rows = _canonical_lookup(canonical)
    comparison_rows = _comparison_lookup(comparison)
    audit_rows = _audit_lookup(audit_entries)
    now_dt = _to_dt(now) or datetime.now().astimezone()

    promoted = trace_source[
        trace_source["canonical_decision"].fillna("").astype(str).map(_is_promoted_decision)
    ].copy()

    rows: list[dict[str, Any]] = []
    for _, row in promoted.iterrows():
        row_dict = row.to_dict()
        episode_id = _to_text(row_dict.get("episode_id", ""), "")
        canonical_row = canonical_rows.get(episode_id, {})
        comparison_row = comparison_rows.get(episode_id, {})
        audit_row = audit_rows.get(episode_id, {})

        promoted_at = _to_dt(row_dict.get("promotion_reviewed_at", ""))
        audit_executed_at = _to_dt(audit_row.get("audit_executed_at", ""))
        audit_due_short = promoted_at + timedelta(days=3) if promoted_at else None
        audit_due_long = promoted_at + timedelta(days=14) if promoted_at else None

        rows.append(
            {
                "promotion_audit_id": f"post_promotion_audit::{episode_id}",
                "episode_id": episode_id,
                "canonical_row_id": _to_text(canonical_row.get("annotation_id", ""), "") or episode_id,
                "promoted_at": promoted_at.isoformat(timespec="seconds") if promoted_at else "",
                "promoted_by": _to_text(row_dict.get("promotion_reviewer", ""), ""),
                "promotion_reason": _to_text(row_dict.get("promotion_decision_reason", ""), ""),
                "promotion_source": "current_rich_review_trace",
                "audit_due_at_short": audit_due_short.isoformat(timespec="seconds") if audit_due_short else "",
                "audit_due_at_long": audit_due_long.isoformat(timespec="seconds") if audit_due_long else "",
                "audit_executed_at": audit_executed_at.isoformat(timespec="seconds") if audit_executed_at else "",
                "audit_status": _audit_status(
                    promoted_at=promoted_at,
                    audit_executed_at=audit_executed_at,
                    now=now_dt,
                ),
                "heuristic_match_after_promotion": _to_text(comparison_row.get("manual_vs_barrier_match", ""), ""),
                "heuristic_gap_after_promotion": _to_text(comparison_row.get("evidence_gap_minutes", ""), ""),
                "family_consistency_after_promotion": _family_consistency(comparison_row, canonical_row),
                "scene_consistency_after_promotion": _scene_consistency(canonical_row, comparison_row),
                "audit_result": _to_text(audit_row.get("audit_result", ""), ""),
                "audit_reason": _to_text(audit_row.get("audit_reason", ""), ""),
                "audit_reviewer": _to_text(audit_row.get("audit_reviewer", ""), ""),
                "keep_canonical": _to_text(audit_row.get("keep_canonical", ""), ""),
                "needs_relabel": _to_text(audit_row.get("needs_relabel", ""), ""),
                "needs_note_update": _to_text(audit_row.get("needs_note_update", ""), ""),
                "demote_from_canonical": _to_text(audit_row.get("demote_from_canonical", ""), ""),
            }
        )

    audit = pd.DataFrame(rows)
    for column in MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_COLUMNS:
        if column not in audit.columns:
            audit[column] = ""
    audit = audit[MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_COLUMNS].copy()

    due_mask = audit["audit_status"].isin(["due_short", "overdue_long"]) if not audit.empty else pd.Series(dtype=bool)
    overdue_mask = audit["audit_status"].eq("overdue_long") if not audit.empty else pd.Series(dtype=bool)
    summary = {
        "post_promotion_audit_version": MANUAL_CURRENT_RICH_POST_PROMOTION_AUDIT_VERSION,
        "row_count": int(len(audit)),
        "audit_status_counts": audit["audit_status"].value_counts(dropna=False).to_dict() if not audit.empty else {},
        "audit_result_counts": audit["audit_result"].value_counts(dropna=False).to_dict() if not audit.empty else {},
        "completed_count": int(audit["audit_status"].eq("audit_executed").sum()) if not audit.empty else 0,
        "scheduled_count": int(audit["audit_status"].eq("scheduled").sum()) if not audit.empty else 0,
        "due_count": int(due_mask.sum()) if not audit.empty else 0,
        "overdue_count": int(overdue_mask.sum()) if not audit.empty else 0,
        "next_due_episode_ids": (
            audit.loc[audit["audit_status"].isin(["scheduled", "due_short", "overdue_long"]), "episode_id"]
            .astype(str)
            .head(5)
            .tolist()
            if not audit.empty
            else []
        ),
    }
    return audit, summary


def render_manual_current_rich_post_promotion_audit_markdown(
    summary: Mapping[str, Any],
    audit: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Post-Promotion Audit v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- audit statuses: `{summary.get('audit_status_counts', {})}`",
        f"- audit results: `{summary.get('audit_result_counts', {})}`",
        f"- completed count: `{summary.get('completed_count', 0)}`",
        f"- scheduled count: `{summary.get('scheduled_count', 0)}`",
        f"- due count: `{summary.get('due_count', 0)}`",
        f"- overdue count: `{summary.get('overdue_count', 0)}`",
        f"- next due episodes: `{summary.get('next_due_episode_ids', [])}`",
        "",
        "## Audit Preview",
    ]
    if audit.empty:
        lines.append("- none")
    else:
        for _, row in audit.head(10).iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("episode_id", ""), ""),
                        _to_text(row.get("audit_status", ""), ""),
                        _to_text(row.get("heuristic_match_after_promotion", ""), "") or "unknown",
                        _to_text(row.get("family_consistency_after_promotion", ""), "") or "unknown",
                    ]
                )
            )
            lines.append(
                "  due: "
                + " / ".join(
                    [
                        _to_text(row.get("audit_due_at_short", ""), "") or "-",
                        _to_text(row.get("audit_due_at_long", ""), "") or "-",
                    ]
                )
            )
    return "\n".join(lines) + "\n"
