"""Promotion discipline layer for current-rich draft rows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_VERSION = "manual_current_rich_promotion_discipline_v0"

MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_COLUMNS = [
    "discipline_row_id",
    "episode_id",
    "symbol",
    "anchor_time",
    "promotion_level",
    "promotion_decision_type",
    "promotion_reason_code",
    "promotion_evidence_summary",
    "promotion_linked_casebook_id",
    "promotion_linked_family_key",
    "promotion_manual_confidence_floor",
    "promotion_episode_detail_score",
    "canonical_merged_at",
    "canonical_merged_by",
    "canonical_merge_batch_id",
    "canonical_merge_reason",
    "merge_status",
    "next_discipline_action",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(str(value).strip()))
    except Exception:
        return int(default)


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _merge_lookup(entries: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if entries is None or entries.empty or "episode_id" not in entries.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def _promotion_reason_code(reason: str) -> str:
    text = _to_text(reason, "")
    if "::" in text:
        return text.split("::", 1)[0]
    return text or "unspecified"


def _episode_detail_score(row: Mapping[str, Any]) -> int:
    score = 0
    for key in ["anchor_time", "manual_wait_teacher_label", "ideal_entry_time", "ideal_exit_time"]:
        if _to_text(row.get(key, ""), ""):
            score += 1
    return score


def _confidence_floor(value: str) -> str:
    confidence = _to_text(value, "").lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    return "unknown"


def _promotion_level(gate_row: Mapping[str, Any], merge_row: Mapping[str, Any]) -> str:
    if _to_text(merge_row.get("canonical_merged_at", ""), ""):
        return "canonical"
    if _to_text(gate_row.get("promotion_reviewer", ""), "") or _to_text(gate_row.get("promotion_reviewed_at", ""), ""):
        return "validated"
    return "draft"


def build_manual_current_rich_promotion_discipline(
    gate: pd.DataFrame,
    *,
    merge_entries: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    gate_source = gate.copy() if gate is not None else pd.DataFrame()
    if gate_source.empty:
        empty = pd.DataFrame(columns=MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_COLUMNS)
        summary = {
            "promotion_discipline_version": MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_VERSION,
            "row_count": 0,
            "promotion_level_counts": {},
            "merge_status_counts": {},
            "next_discipline_action_counts": {},
        }
        return empty, summary

    merge_lookup = _merge_lookup(merge_entries)
    rows: list[dict[str, Any]] = []
    for _, row in gate_source.iterrows():
        gate_row = row.to_dict()
        episode_id = _to_text(gate_row.get("episode_id", ""), "")
        merge_row = merge_lookup.get(episode_id, {})
        level = _promotion_level(gate_row, merge_row)
        merge_status = (
            "merged_to_canonical" if level == "canonical"
            else ("validated_not_merged" if level == "validated" else "draft_only")
        )
        rows.append(
            {
                "discipline_row_id": f"promotion_discipline::{episode_id}",
                "episode_id": episode_id,
                "symbol": _to_text(gate_row.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(gate_row.get("anchor_time", ""), ""),
                "promotion_level": level,
                "promotion_decision_type": _to_text(
                    merge_row.get("promotion_decision_type", "")
                    or gate_row.get("canonical_action", ""),
                    "",
                ).lower(),
                "promotion_reason_code": _to_text(
                    merge_row.get("promotion_reason_code", ""),
                    "",
                ) or _promotion_reason_code(_to_text(gate_row.get("promotion_decision_reason", ""), "")),
                "promotion_evidence_summary": _to_text(
                    merge_row.get("promotion_evidence_summary", ""),
                    "",
                ) or "|".join(
                    part
                    for part in [
                        f"calibration={_to_text(gate_row.get('calibration_value_bucket', ''), '')}",
                        f"detail={_to_text(gate_row.get('episode_detail_status', ''), '')}",
                        f"blockers={_to_text(gate_row.get('promotion_blockers', ''), '')}",
                    ]
                    if part
                ),
                "promotion_linked_casebook_id": _to_text(
                    merge_row.get("promotion_linked_casebook_id", ""),
                    "",
                ) or episode_id,
                "promotion_linked_family_key": _to_text(
                    merge_row.get("promotion_linked_family_key", ""),
                    "",
                ) or "|".join(
                    [
                        _to_text(gate_row.get("symbol", ""), "").upper(),
                        _to_text(gate_row.get("manual_wait_teacher_label", ""), "").lower(),
                    ]
                ),
                "promotion_manual_confidence_floor": _to_text(
                    merge_row.get("promotion_manual_confidence_floor", ""),
                    "",
                ) or _confidence_floor(_to_text(gate_row.get("manual_teacher_confidence", ""), "")),
                "promotion_episode_detail_score": _to_int(
                    merge_row.get("promotion_episode_detail_score", ""),
                    0,
                ) or _episode_detail_score(gate_row),
                "canonical_merged_at": _to_text(merge_row.get("canonical_merged_at", ""), ""),
                "canonical_merged_by": _to_text(merge_row.get("canonical_merged_by", ""), ""),
                "canonical_merge_batch_id": _to_text(merge_row.get("canonical_merge_batch_id", ""), ""),
                "canonical_merge_reason": _to_text(merge_row.get("canonical_merge_reason", ""), ""),
                "merge_status": merge_status,
                "next_discipline_action": (
                    "run_post_promotion_audit"
                    if level == "canonical"
                    else (
                        "complete_merge_trace"
                        if level == "validated"
                        else "complete_review_then_validate"
                    )
                ),
            }
        )

    discipline = pd.DataFrame(rows)
    for column in MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_COLUMNS:
        if column not in discipline.columns:
            discipline[column] = ""
    discipline = discipline[MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_COLUMNS].copy()

    summary = {
        "promotion_discipline_version": MANUAL_CURRENT_RICH_PROMOTION_DISCIPLINE_VERSION,
        "row_count": int(len(discipline)),
        "promotion_level_counts": discipline["promotion_level"].value_counts(dropna=False).to_dict()
        if not discipline.empty
        else {},
        "merge_status_counts": discipline["merge_status"].value_counts(dropna=False).to_dict()
        if not discipline.empty
        else {},
        "next_discipline_action_counts": discipline["next_discipline_action"].value_counts(dropna=False).to_dict()
        if not discipline.empty
        else {},
    }
    return discipline, summary


def render_manual_current_rich_promotion_discipline_markdown(
    summary: Mapping[str, Any],
    discipline: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Promotion Discipline v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- promotion levels: `{summary.get('promotion_level_counts', {})}`",
        f"- merge statuses: `{summary.get('merge_status_counts', {})}`",
        f"- next actions: `{summary.get('next_discipline_action_counts', {})}`",
        "",
        "## Discipline Preview",
    ]
    if discipline.empty:
        lines.append("- none")
    else:
        for _, row in discipline.head(10).iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("promotion_level", ""), ""),
                        _to_text(row.get("symbol", ""), ""),
                        _to_text(row.get("anchor_time", ""), ""),
                        _to_text(row.get("promotion_reason_code", ""), ""),
                        _to_text(row.get("next_discipline_action", ""), ""),
                    ]
                )
            )
            lines.append(f"  merge: {_to_text(row.get('merge_status', ''), '')}")
    return "\n".join(lines) + "\n"
