"""Patch-draft template layer built on top of the bias sandbox output."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_PATCH_DRAFT_VERSION = "manual_vs_heuristic_patch_draft_v0"

MANUAL_VS_HEURISTIC_PATCH_DRAFT_COLUMNS = [
    "patch_draft_id",
    "sandbox_id",
    "family_id",
    "miss_type",
    "primary_correction_target",
    "correction_priority_tier",
    "sandbox_status",
    "patch_draft_status",
    "patch_readiness",
    "patch_hypothesis",
    "proposed_rule_change_summary",
    "proposed_bce_edit_surface",
    "required_truth_actions",
    "required_validation_steps",
    "adoption_gate",
    "rejection_gate",
    "approval_status",
    "draft_owner",
    "recommended_next_action",
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


def _patch_draft_status(sandbox_status: str) -> str:
    status_key = _to_text(sandbox_status, "").lower()
    if status_key == "draft_patch_ready":
        return "rule_patch_ready"
    if status_key == "review_patch_hypothesis":
        return "hypothesis_review_required"
    if status_key == "collect_more_truth_before_patch":
        return "truth_collection_before_patch"
    if status_key == "freeze_track_only":
        return "freeze_monitor_only"
    return "casebook_only"


def _patch_readiness(draft_status: str) -> str:
    if draft_status == "rule_patch_ready":
        return "ready"
    if draft_status == "hypothesis_review_required":
        return "review_required"
    return "blocked"


def _proposed_rule_change_summary(row: Mapping[str, Any]) -> str:
    draft_status = _patch_draft_status(_to_text(row.get("sandbox_status", ""), ""))
    hypothesis = _to_text(row.get("patch_hypothesis", ""), "")
    patch_scope = _to_text(row.get("patch_scope", ""), "")
    if draft_status == "truth_collection_before_patch":
        return (
            "Do not edit the BCE rule yet. Collect closer current-rich truth, rerank the family, "
            "and reopen a rule draft only if the family remains correction-worthy."
        )
    if draft_status == "freeze_monitor_only":
        return (
            "No BCE rule edit. Keep the current rule unchanged and monitor future evidence for "
            "new correction-worthy reproduction."
        )
    if draft_status == "hypothesis_review_required":
        return (
            f"Review the hypothesis `{hypothesis}` against `{patch_scope}` and prepare a narrow "
            "rule diff only after human signoff."
        )
    if draft_status == "rule_patch_ready":
        return (
            f"Draft a narrow BCE edit on `{patch_scope}` following `{hypothesis}`, then validate "
            "with comparison, recovered casebook, and bias targets."
        )
    return "Keep as casebook/reference only; no BCE edit draft is needed."


def _required_truth_actions(row: Mapping[str, Any]) -> str:
    draft_status = _patch_draft_status(_to_text(row.get("sandbox_status", ""), ""))
    if draft_status == "truth_collection_before_patch":
        return "review_current_rich_p1|complete_episode_coordinates|promote_if_confirmed|rerank_family"
    if draft_status == "freeze_monitor_only":
        return "keep_family_frozen|monitor_new_current_rich_cases|do_not_edit_rule"
    if draft_status == "hypothesis_review_required":
        return "confirm_manual_truth_quality|review_family_examples|prepare_patch_diff"
    if draft_status == "rule_patch_ready":
        return "prepare_patch_diff|run_post_edit_audit|collect_adoption_signoff"
    return "archive_as_casebook_reference"


def build_manual_vs_heuristic_patch_draft(
    sandbox: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = sandbox.copy() if sandbox is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_PATCH_DRAFT_COLUMNS)
        summary = {
            "patch_draft_version": MANUAL_VS_HEURISTIC_PATCH_DRAFT_VERSION,
            "row_count": 0,
            "patch_draft_status_counts": {},
            "patch_readiness_counts": {},
            "next_patch_draft_id": "",
        }
        return empty, summary

    rows: list[dict[str, Any]] = []
    for _, row in source.iterrows():
        row_dict = row.to_dict()
        draft_status = _patch_draft_status(_to_text(row_dict.get("sandbox_status", ""), ""))
        rows.append(
            {
                "patch_draft_id": f"patch_draft::{_to_text(row_dict.get('family_id', ''), '')}",
                "sandbox_id": _to_text(row_dict.get("sandbox_id", ""), ""),
                "family_id": _to_text(row_dict.get("family_id", ""), ""),
                "miss_type": _to_text(row_dict.get("miss_type", ""), "").lower(),
                "primary_correction_target": _to_text(
                    row_dict.get("primary_correction_target", ""),
                    "",
                ).lower(),
                "correction_priority_tier": _to_text(
                    row_dict.get("correction_priority_tier", ""),
                    "",
                ).upper(),
                "sandbox_status": _to_text(row_dict.get("sandbox_status", ""), "").lower(),
                "patch_draft_status": draft_status,
                "patch_readiness": _patch_readiness(draft_status),
                "patch_hypothesis": _to_text(row_dict.get("patch_hypothesis", ""), ""),
                "proposed_rule_change_summary": _proposed_rule_change_summary(row_dict),
                "proposed_bce_edit_surface": _to_text(row_dict.get("patch_scope", ""), ""),
                "required_truth_actions": _required_truth_actions(row_dict),
                "required_validation_steps": _to_text(row_dict.get("validation_plan", ""), ""),
                "adoption_gate": _to_text(row_dict.get("adoption_gate", ""), ""),
                "rejection_gate": _to_text(row_dict.get("rejection_gate", ""), ""),
                "approval_status": (
                    "await_more_truth"
                    if draft_status == "truth_collection_before_patch"
                    else (
                        "freeze_monitoring"
                        if draft_status == "freeze_monitor_only"
                        else "await_manual_signoff"
                    )
                ),
                "draft_owner": "manual_truth_calibration",
                "recommended_next_action": _to_text(row_dict.get("recommended_next_action", ""), ""),
            }
        )

    draft = pd.DataFrame(rows)
    draft["status_rank"] = draft["patch_draft_status"].map(
        {
            "rule_patch_ready": 0,
            "hypothesis_review_required": 1,
            "truth_collection_before_patch": 2,
            "freeze_monitor_only": 3,
            "casebook_only": 4,
        }
    ).fillna(5)
    draft = draft.sort_values(
        by=["status_rank", "correction_priority_tier", "family_id"],
        ascending=[True, True, True],
        kind="stable",
    ).drop(columns=["status_rank"]).reset_index(drop=True)

    for column in MANUAL_VS_HEURISTIC_PATCH_DRAFT_COLUMNS:
        if column not in draft.columns:
            draft[column] = ""
    draft = draft[MANUAL_VS_HEURISTIC_PATCH_DRAFT_COLUMNS].copy()

    actionable = draft[
        draft["patch_draft_status"].fillna("").astype(str).isin(
            ["rule_patch_ready", "hypothesis_review_required", "truth_collection_before_patch"]
        )
    ]
    summary = {
        "patch_draft_version": MANUAL_VS_HEURISTIC_PATCH_DRAFT_VERSION,
        "row_count": int(len(draft)),
        "patch_draft_status_counts": draft["patch_draft_status"].value_counts(dropna=False).to_dict()
        if not draft.empty
        else {},
        "patch_readiness_counts": draft["patch_readiness"].value_counts(dropna=False).to_dict()
        if not draft.empty
        else {},
        "next_patch_draft_id": _to_text(actionable.iloc[0]["patch_draft_id"], "") if not actionable.empty else "",
    }
    return draft, summary


def render_manual_vs_heuristic_patch_draft_markdown(
    summary: Mapping[str, Any],
    draft: pd.DataFrame,
) -> str:
    lines = [
        "# Manual vs Heuristic Patch Draft Template v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- patch draft statuses: `{summary.get('patch_draft_status_counts', {})}`",
        f"- patch readiness: `{summary.get('patch_readiness_counts', {})}`",
        f"- next patch draft: `{summary.get('next_patch_draft_id', '')}`",
        "",
        "## Patch Draft Preview",
    ]
    preview = draft.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("patch_draft_status", "")),
                        _to_text(row.get("correction_priority_tier", "")),
                        _to_text(row.get("miss_type", "")),
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
            lines.append(f"  summary: {_to_text(row.get('proposed_rule_change_summary', ''), '')}")
    return "\n".join(lines) + "\n"
