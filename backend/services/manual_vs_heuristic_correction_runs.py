"""Correction-loop candidate and run logging built on top of ranking and patch drafts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_CORRECTION_LOOP_VERSION = "manual_vs_heuristic_correction_loop_v0"

FAMILY_KEY_COLUMNS = [
    "miss_type",
    "primary_correction_target",
    "manual_wait_teacher_family",
    "heuristic_wait_family",
    "heuristic_barrier_main_label",
]

MANUAL_VS_HEURISTIC_CORRECTION_CANDIDATE_COLUMNS = [
    "run_candidate_id",
    "created_at",
    "family_key",
    "miss_type",
    "primary_correction_target",
    "manual_wait_teacher_family",
    "heuristic_wait_family",
    "heuristic_barrier_main_label",
    "case_count",
    "correction_worthy_case_count",
    "freeze_worthy_case_count",
    "hold_for_more_truth_case_count",
    "priority_tier",
    "recommended_next_action",
    "patch_draft_status",
    "patch_readiness",
    "selected_for_patch",
    "selection_reason",
    "selected_by",
]

MANUAL_VS_HEURISTIC_CORRECTION_RUN_COLUMNS = [
    "correction_run_id",
    "started_at",
    "finished_at",
    "family_key",
    "miss_type",
    "target_rule_area",
    "patch_version",
    "patch_scope",
    "before_match_count",
    "before_mismatch_count",
    "before_correction_worthy_count",
    "before_freeze_worthy_count",
    "before_needs_more_truth_count",
    "after_match_count",
    "after_mismatch_count",
    "after_correction_worthy_count",
    "after_freeze_worthy_count",
    "after_needs_more_truth_count",
    "mismatch_delta",
    "match_delta",
    "side_effect_flag",
    "side_effect_summary",
    "decision",
    "decision_reason",
    "reviewer",
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


def _family_key_from_mapping(row: Mapping[str, Any]) -> str:
    return "|".join(_to_text(row.get(column, "none"), "none") for column in FAMILY_KEY_COLUMNS)


def _patch_status_rank(status: str) -> int:
    status_key = _to_text(status, "").lower()
    return {
        "rule_patch_ready": 0,
        "hypothesis_review_required": 1,
        "truth_collection_before_patch": 2,
        "freeze_monitor_only": 3,
        "casebook_only": 4,
    }.get(status_key, 5)


def _priority_rank(priority_tier: str) -> int:
    priority_key = _to_text(priority_tier, "").upper()
    return {
        "P1": 0,
        "P2": 1,
        "P3": 2,
        "HOLD": 3,
    }.get(priority_key, 4)


def _selected_for_patch(row: Mapping[str, Any]) -> bool:
    priority_tier = _to_text(row.get("correction_priority_tier", ""), "").upper()
    disposition = _to_text(row.get("family_disposition", ""), "").lower()
    patch_status = _to_text(row.get("patch_draft_status", ""), "").lower()
    ready_count = _to_int(row.get("ready_case_count", 0), 0)
    correction_count = _to_int(row.get("correction_worthy_case_count", 0), 0)
    return (
        priority_tier in {"P1", "P2"}
        and disposition == "correction_candidate"
        and patch_status == "rule_patch_ready"
        and ready_count > 0
        and correction_count > 0
    )


def _selection_reason(row: Mapping[str, Any], *, selected_for_patch: bool) -> str:
    patch_status = _to_text(row.get("patch_draft_status", ""), "").lower()
    next_action = _to_text(row.get("recommended_next_action", ""), "").lower()
    priority_tier = _to_text(row.get("correction_priority_tier", ""), "").upper()
    if selected_for_patch:
        return f"selected_for_patch::{priority_tier.lower()}::{next_action or 'run_sandbox_patch'}"
    if patch_status == "truth_collection_before_patch":
        return f"collect_more_truth_before_patch::{next_action or 'collect_current_rich_truth'}"
    if patch_status == "freeze_monitor_only":
        return f"freeze_monitor_only::{next_action or 'freeze_and_monitor'}"
    if patch_status == "hypothesis_review_required":
        return f"manual_hypothesis_review_required::{next_action or 'review_patch_hypothesis'}"
    return f"not_selected::{next_action or 'casebook_only'}"


def build_manual_vs_heuristic_correction_candidates(
    ranking: pd.DataFrame,
    patch_draft: pd.DataFrame,
    *,
    now: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ranking_source = ranking.copy() if ranking is not None else pd.DataFrame()
    draft_source = patch_draft.copy() if patch_draft is not None else pd.DataFrame()
    created_at = _to_text(now, "") or datetime.now().isoformat(timespec="seconds")
    if ranking_source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_CORRECTION_CANDIDATE_COLUMNS)
        summary = {
            "correction_loop_version": MANUAL_VS_HEURISTIC_CORRECTION_LOOP_VERSION,
            "candidate_count": 0,
            "selected_for_patch_count": 0,
            "selection_reason_counts": {},
            "next_candidate_id": "",
        }
        return empty, summary

    if not draft_source.empty:
        draft_source = draft_source.reindex(
            columns=[
                "family_id",
                "patch_draft_status",
                "patch_readiness",
                "proposed_bce_edit_surface",
                "approval_status",
            ],
            fill_value="",
        ).copy()
    else:
        draft_source = pd.DataFrame(
            columns=[
                "family_id",
                "patch_draft_status",
                "patch_readiness",
                "proposed_bce_edit_surface",
                "approval_status",
            ]
        )

    merged = ranking_source.merge(
        draft_source,
        how="left",
        left_on="family_id",
        right_on="family_id",
    )

    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        row_dict = row.to_dict()
        selected_for_patch = _selected_for_patch(row_dict)
        rows.append(
            {
                "run_candidate_id": f"correction_candidate::{_to_text(row_dict.get('family_id', ''), '')}",
                "created_at": created_at,
                "family_key": _to_text(row_dict.get("family_id", ""), ""),
                "miss_type": _to_text(row_dict.get("miss_type", ""), "").lower(),
                "primary_correction_target": _to_text(
                    row_dict.get("primary_correction_target", ""),
                    "",
                ).lower(),
                "manual_wait_teacher_family": _to_text(
                    row_dict.get("manual_wait_teacher_family", ""),
                    "none",
                ).lower(),
                "heuristic_wait_family": _to_text(
                    row_dict.get("heuristic_wait_family", ""),
                    "none",
                ).lower(),
                "heuristic_barrier_main_label": _to_text(
                    row_dict.get("heuristic_barrier_main_label", ""),
                    "none",
                ).lower(),
                "case_count": _to_int(row_dict.get("case_count", 0), 0),
                "correction_worthy_case_count": _to_int(
                    row_dict.get("correction_worthy_case_count", 0),
                    0,
                ),
                "freeze_worthy_case_count": _to_int(
                    row_dict.get("freeze_worthy_case_count", 0),
                    0,
                ),
                "hold_for_more_truth_case_count": _to_int(
                    row_dict.get("hold_for_more_truth_case_count", 0),
                    0,
                ),
                "priority_tier": _to_text(row_dict.get("correction_priority_tier", ""), "").upper(),
                "recommended_next_action": _to_text(
                    row_dict.get("recommended_next_action", ""),
                    "",
                ).lower(),
                "patch_draft_status": _to_text(row_dict.get("patch_draft_status", ""), "").lower(),
                "patch_readiness": _to_text(row_dict.get("patch_readiness", ""), "").lower(),
                "selected_for_patch": bool(selected_for_patch),
                "selection_reason": _selection_reason(row_dict, selected_for_patch=selected_for_patch),
                "selected_by": "manual_truth_calibration" if selected_for_patch else "",
            }
        )

    candidates = pd.DataFrame(rows)
    candidates["selected_rank"] = candidates["selected_for_patch"].map(lambda value: 0 if bool(value) else 1)
    candidates["priority_rank"] = candidates["priority_tier"].map(_priority_rank).fillna(9)
    candidates["patch_status_rank"] = candidates["patch_draft_status"].map(_patch_status_rank).fillna(9)
    candidates = candidates.sort_values(
        by=["selected_rank", "priority_rank", "patch_status_rank", "case_count", "family_key"],
        ascending=[True, True, True, False, True],
        kind="stable",
    ).drop(columns=["selected_rank", "priority_rank", "patch_status_rank"]).reset_index(drop=True)

    for column in MANUAL_VS_HEURISTIC_CORRECTION_CANDIDATE_COLUMNS:
        if column not in candidates.columns:
            candidates[column] = ""
    candidates = candidates[MANUAL_VS_HEURISTIC_CORRECTION_CANDIDATE_COLUMNS].copy()

    summary = {
        "correction_loop_version": MANUAL_VS_HEURISTIC_CORRECTION_LOOP_VERSION,
        "candidate_count": int(len(candidates)),
        "selected_for_patch_count": int(candidates["selected_for_patch"].astype(bool).sum()) if not candidates.empty else 0,
        "selection_reason_counts": candidates["selection_reason"].value_counts(dropna=False).to_dict()
        if not candidates.empty
        else {},
        "next_candidate_id": _to_text(candidates.iloc[0]["run_candidate_id"], "") if not candidates.empty else "",
    }
    return candidates, summary


def _decision_for_candidate(row: Mapping[str, Any]) -> tuple[str, str, str]:
    selected_for_patch = str(bool(row.get("selected_for_patch", False))).lower() == "true"
    patch_status = _to_text(row.get("patch_draft_status", ""), "").lower()
    family_key = _to_text(row.get("family_key", ""), "")
    if selected_for_patch:
        return (
            "hold_for_patch_execution",
            f"ready_patch_candidate::{family_key}",
            "patch_candidate_v0",
        )
    if patch_status == "truth_collection_before_patch":
        return (
            "hold_for_more_truth",
            "truth_collection_before_patch",
            "truth_collection_only_v0",
        )
    if patch_status == "hypothesis_review_required":
        return (
            "hold_for_more_truth",
            "manual_hypothesis_review_required",
            "hypothesis_review_v0",
        )
    if patch_status == "freeze_monitor_only":
        return (
            "reject",
            "freeze_monitor_only_no_patch",
            "freeze_monitor_only_v0",
        )
    return (
        "reject",
        "casebook_only_no_patch",
        "screening_only_v0",
    )


def _matching_family_rows(comparison: pd.DataFrame, candidate: Mapping[str, Any]) -> pd.DataFrame:
    if comparison is None or comparison.empty:
        return pd.DataFrame()
    group = comparison.copy()
    for column in FAMILY_KEY_COLUMNS:
        group = group[
            group[column].fillna("").astype(str).str.strip().eq(
                _to_text(candidate.get(column, ""), "")
            )
        ]
    return group.copy()


def _count_correction_worthy(group: pd.DataFrame) -> int:
    if group.empty:
        return 0
    return int(
        group["correction_worthiness_class"]
        .fillna("")
        .astype(str)
        .isin(["correction_worthy", "candidate_correction"])
        .sum()
    )


def _count_needs_more_truth(group: pd.DataFrame) -> int:
    if group.empty:
        return 0
    return int(
        group["rule_change_readiness"]
        .fillna("")
        .astype(str)
        .isin(["needs_more_recent_truth", "needs_manual_recheck", "insufficient_evidence"])
        .sum()
    )


def build_manual_vs_heuristic_correction_runs(
    candidates: pd.DataFrame,
    comparison: pd.DataFrame,
    *,
    now: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    candidate_source = candidates.copy() if candidates is not None else pd.DataFrame()
    comparison_source = comparison.copy() if comparison is not None else pd.DataFrame()
    started_at = _to_text(now, "") or datetime.now().isoformat(timespec="seconds")
    if candidate_source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_CORRECTION_RUN_COLUMNS)
        summary = {
            "correction_loop_version": MANUAL_VS_HEURISTIC_CORRECTION_LOOP_VERSION,
            "run_count": 0,
            "decision_counts": {},
            "accepted_count": 0,
            "rejected_count": 0,
            "hold_count": 0,
            "latest_run_id": "",
        }
        return empty, summary

    selected = candidate_source[candidate_source["selected_for_patch"].astype(bool)].copy()
    run_candidates = selected if not selected.empty else candidate_source.head(1).copy()

    rows: list[dict[str, Any]] = []
    for _, row in run_candidates.iterrows():
        row_dict = row.to_dict()
        family_rows = _matching_family_rows(comparison_source, row_dict)
        before_match_count = int(family_rows["miss_type"].fillna("").astype(str).eq("aligned").sum()) if not family_rows.empty else 0
        before_mismatch_count = int(
            family_rows["miss_type"].fillna("").astype(str).ne("aligned").sum()
        ) if not family_rows.empty else 0
        before_correction_worthy_count = _count_correction_worthy(family_rows)
        before_freeze_worthy_count = int(
            family_rows["freeze_worthiness_class"].fillna("").astype(str).eq("freeze_worthy").sum()
        ) if not family_rows.empty else 0
        before_needs_more_truth_count = _count_needs_more_truth(family_rows)

        decision, decision_reason, patch_version = _decision_for_candidate(row_dict)
        after_match_count = before_match_count
        after_mismatch_count = before_mismatch_count
        after_correction_worthy_count = before_correction_worthy_count
        after_freeze_worthy_count = before_freeze_worthy_count
        after_needs_more_truth_count = before_needs_more_truth_count

        rows.append(
            {
                "correction_run_id": f"correction_run::{_to_text(row_dict.get('family_key', ''), '')}",
                "started_at": started_at,
                "finished_at": started_at,
                "family_key": _to_text(row_dict.get("family_key", ""), ""),
                "miss_type": _to_text(row_dict.get("miss_type", ""), "").lower(),
                "target_rule_area": _to_text(row_dict.get("primary_correction_target", ""), "").lower(),
                "patch_version": patch_version,
                "patch_scope": (
                    "barrier_wait_mapping_logic"
                    if _to_text(row_dict.get("primary_correction_target", ""), "").lower() == "barrier_bias_rule"
                    else "owner_logging_coverage_only"
                ),
                "before_match_count": before_match_count,
                "before_mismatch_count": before_mismatch_count,
                "before_correction_worthy_count": before_correction_worthy_count,
                "before_freeze_worthy_count": before_freeze_worthy_count,
                "before_needs_more_truth_count": before_needs_more_truth_count,
                "after_match_count": after_match_count,
                "after_mismatch_count": after_mismatch_count,
                "after_correction_worthy_count": after_correction_worthy_count,
                "after_freeze_worthy_count": after_freeze_worthy_count,
                "after_needs_more_truth_count": after_needs_more_truth_count,
                "mismatch_delta": int(after_mismatch_count - before_mismatch_count),
                "match_delta": int(after_match_count - before_match_count),
                "side_effect_flag": False,
                "side_effect_summary": "no_patch_applied_before_after_identical",
                "decision": decision,
                "decision_reason": decision_reason,
                "reviewer": "manual_truth_calibration",
            }
        )

    runs = pd.DataFrame(rows)
    for column in MANUAL_VS_HEURISTIC_CORRECTION_RUN_COLUMNS:
        if column not in runs.columns:
            runs[column] = ""
    runs = runs[MANUAL_VS_HEURISTIC_CORRECTION_RUN_COLUMNS].copy()

    summary = {
        "correction_loop_version": MANUAL_VS_HEURISTIC_CORRECTION_LOOP_VERSION,
        "run_count": int(len(runs)),
        "decision_counts": runs["decision"].value_counts(dropna=False).to_dict() if not runs.empty else {},
        "accepted_count": int(runs["decision"].fillna("").astype(str).eq("accept").sum()) if not runs.empty else 0,
        "rejected_count": int(runs["decision"].fillna("").astype(str).eq("reject").sum()) if not runs.empty else 0,
        "hold_count": int(
            runs["decision"].fillna("").astype(str).isin(["hold_for_more_truth", "hold_for_patch_execution"]).sum()
        ) if not runs.empty else 0,
        "latest_run_id": _to_text(runs.iloc[0]["correction_run_id"], "") if not runs.empty else "",
    }
    return runs, summary


def render_manual_vs_heuristic_correction_loop_markdown(
    candidate_summary: Mapping[str, Any],
    candidates: pd.DataFrame,
    run_summary: Mapping[str, Any],
    runs: pd.DataFrame,
) -> str:
    lines = [
        "# Manual vs Heuristic Correction Loop v0",
        "",
        "## Candidate Snapshot",
        f"- candidates: `{candidate_summary.get('candidate_count', 0)}`",
        f"- selected_for_patch: `{candidate_summary.get('selected_for_patch_count', 0)}`",
        f"- selection reasons: `{candidate_summary.get('selection_reason_counts', {})}`",
        f"- next candidate: `{candidate_summary.get('next_candidate_id', '')}`",
        "",
        "## Correction Run Snapshot",
        f"- runs: `{run_summary.get('run_count', 0)}`",
        f"- decisions: `{run_summary.get('decision_counts', {})}`",
        f"- latest run: `{run_summary.get('latest_run_id', '')}`",
        "",
        "## Candidate Preview",
    ]
    preview = candidates.head(5)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("priority_tier", "")),
                        _to_text(row.get("patch_draft_status", "")),
                        _to_text(row.get("recommended_next_action", "")),
                        _to_text(row.get("selection_reason", "")),
                    ]
                )
            )
            lines.append(f"  family: {_to_text(row.get('family_key', ''), '')}")
    lines.extend(["", "## Run Preview"])
    run_preview = runs.head(5)
    if run_preview.empty:
        lines.append("- none")
    else:
        for _, row in run_preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("decision", "")),
                        _to_text(row.get("decision_reason", "")),
                        _to_text(row.get("patch_version", "")),
                    ]
                )
            )
            lines.append(
                "  before/after mismatch: "
                f"{_to_text(row.get('before_mismatch_count', ''), '')}"
                f" -> {_to_text(row.get('after_mismatch_count', ''), '')}"
            )
    return "\n".join(lines) + "\n"
