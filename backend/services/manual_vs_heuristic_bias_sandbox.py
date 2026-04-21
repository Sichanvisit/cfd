"""Bias-correction sandbox loop scaffolding from ranking and target outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_BIAS_SANDBOX_VERSION = "manual_vs_heuristic_bias_sandbox_v0"

MANUAL_VS_HEURISTIC_BIAS_SANDBOX_COLUMNS = [
    "sandbox_id",
    "family_id",
    "miss_type",
    "primary_correction_target",
    "correction_priority_tier",
    "family_disposition",
    "case_count",
    "ready_case_count",
    "hold_for_more_truth_case_count",
    "priority_score_total",
    "top_representative_episode_ids",
    "bias_target_priority",
    "recommended_bce_step",
    "sandbox_status",
    "patch_hypothesis",
    "patch_scope",
    "precheck_requirements",
    "validation_plan",
    "adoption_gate",
    "rejection_gate",
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


def _bias_target_lookup(targets: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    if targets is None or targets.empty:
        return lookup
    for _, row in targets.iterrows():
        key = (
            _to_text(row.get("miss_type", ""), "").lower(),
            _to_text(row.get("primary_correction_target", ""), "").lower(),
        )
        if key not in lookup:
            lookup[key] = row.to_dict()
    return lookup


def _sandbox_status(disposition: str, tier: str) -> str:
    disposition_key = _to_text(disposition, "").lower()
    tier_key = _to_text(tier, "").upper()
    if disposition_key == "correction_candidate" and tier_key in {"P1", "P2"}:
        return "draft_patch_ready"
    if disposition_key == "correction_candidate":
        return "review_patch_hypothesis"
    if disposition_key == "collect_more_truth":
        return "collect_more_truth_before_patch"
    if disposition_key == "freeze_candidate":
        return "freeze_track_only"
    return "casebook_monitor_only"


def _patch_hypothesis(miss_type: str, correction_target: str, disposition: str) -> str:
    miss_key = _to_text(miss_type, "").lower()
    target_key = _to_text(correction_target, "").lower()
    disposition_key = _to_text(disposition, "").lower()
    if disposition_key == "collect_more_truth":
        return "do_not_edit_rule_yet_collect_more_current_rich_truth"
    if disposition_key == "freeze_candidate":
        return "do_not_edit_rule_track_as_freeze_candidate"
    if miss_key == "false_avoided_loss":
        return "reduce_avoided_loss_dominance_when_manual_truth_points_to_timing_improvement"
    if miss_key == "wrong_protective_interpretation":
        return "separate_protective_exit_mapping_from_generic_neutral_wait"
    if miss_key == "wrong_failed_wait_interpretation":
        return "tighten_failed_wait_shift_only_after_current_rich_reproduction"
    if target_key == "barrier_bias_rule":
        return "draft_barrier_bias_rule_patch_for_next_family"
    return "review_family_then_draft_patch"


def _patch_scope(correction_target: str) -> str:
    target_key = _to_text(correction_target, "").lower()
    if target_key == "barrier_bias_rule":
        return "barrier_wait_mapping_logic"
    if target_key == "protective_exit_interpretation":
        return "protective_exit_wait_family_mapping"
    if target_key == "insufficient_owner_coverage":
        return "owner_logging_coverage_only"
    return "manual_vs_heuristic_calibration_layer"


def build_manual_vs_heuristic_bias_sandbox(
    family_ranking: pd.DataFrame,
    bias_targets: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ranking = family_ranking.copy() if family_ranking is not None else pd.DataFrame()
    targets = bias_targets.copy() if bias_targets is not None else pd.DataFrame()

    if ranking.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_BIAS_SANDBOX_COLUMNS)
        summary = {
            "bias_sandbox_version": MANUAL_VS_HEURISTIC_BIAS_SANDBOX_VERSION,
            "row_count": 0,
            "sandbox_status_counts": {},
            "recommended_next_action_counts": {},
            "next_sandbox_id": "",
        }
        return empty, summary

    target_lookup = _bias_target_lookup(targets)
    rows: list[dict[str, Any]] = []
    for _, row in ranking.iterrows():
        row_dict = row.to_dict()
        miss_type = _to_text(row_dict.get("miss_type", ""), "").lower()
        correction_target = _to_text(row_dict.get("primary_correction_target", ""), "").lower()
        lookup = target_lookup.get((miss_type, correction_target), {})
        disposition = _to_text(row_dict.get("family_disposition", ""), "").lower()
        tier = _to_text(row_dict.get("correction_priority_tier", ""), "").upper()
        sandbox_status = _sandbox_status(disposition, tier)
        recommended_bce_step = _to_text(lookup.get("recommended_bce_step", ""), "")
        if not recommended_bce_step:
            recommended_bce_step = _to_text(row_dict.get("recommended_next_action", ""), "")

        rows.append(
            {
                "sandbox_id": f"bias_sandbox::{_to_text(row_dict.get('family_id', ''), '')}",
                "family_id": _to_text(row_dict.get("family_id", ""), ""),
                "miss_type": miss_type,
                "primary_correction_target": correction_target,
                "correction_priority_tier": tier,
                "family_disposition": disposition,
                "case_count": _to_text(row_dict.get("case_count", ""), ""),
                "ready_case_count": _to_text(row_dict.get("ready_case_count", ""), ""),
                "hold_for_more_truth_case_count": _to_text(row_dict.get("hold_for_more_truth_case_count", ""), ""),
                "priority_score_total": _to_text(row_dict.get("priority_score_total", ""), ""),
                "top_representative_episode_ids": _to_text(row_dict.get("top_episode_ids", ""), ""),
                "bias_target_priority": _to_text(lookup.get("priority", ""), ""),
                "recommended_bce_step": recommended_bce_step,
                "sandbox_status": sandbox_status,
                "patch_hypothesis": _patch_hypothesis(miss_type, correction_target, disposition),
                "patch_scope": _patch_scope(correction_target),
                "precheck_requirements": "confirm_manual_truth_quality|confirm_current_rich_support|confirm_no_legacy_gap_artifact",
                "validation_plan": "rerun_comparison|rerun_recovered_casebook|rerun_bias_targets",
                "adoption_gate": "mismatch_down_without_new_freeze_regression",
                "rejection_gate": "new_freeze_regression_or_no_material_gain",
                "recommended_next_action": (
                    "draft_patch_then_recompare"
                    if sandbox_status in {"draft_patch_ready", "review_patch_hypothesis"}
                    else (
                        "collect_more_truth_then_rerank"
                        if sandbox_status == "collect_more_truth_before_patch"
                        else "freeze_and_monitor"
                    )
                ),
            }
        )

    sandbox = pd.DataFrame(rows)
    sandbox["status_rank"] = sandbox["sandbox_status"].map(
        {
            "draft_patch_ready": 0,
            "review_patch_hypothesis": 1,
            "collect_more_truth_before_patch": 2,
            "freeze_track_only": 3,
            "casebook_monitor_only": 4,
        }
    ).fillna(5)
    sandbox = sandbox.sort_values(
        by=["status_rank", "priority_score_total", "case_count", "family_id"],
        ascending=[True, False, False, True],
        kind="stable",
    ).drop(columns=["status_rank"]).reset_index(drop=True)

    for column in MANUAL_VS_HEURISTIC_BIAS_SANDBOX_COLUMNS:
        if column not in sandbox.columns:
            sandbox[column] = ""
    sandbox = sandbox[MANUAL_VS_HEURISTIC_BIAS_SANDBOX_COLUMNS].copy()

    next_sandbox = sandbox[
        sandbox["sandbox_status"].fillna("").astype(str).isin(
            ["draft_patch_ready", "review_patch_hypothesis", "collect_more_truth_before_patch"]
        )
    ]
    summary = {
        "bias_sandbox_version": MANUAL_VS_HEURISTIC_BIAS_SANDBOX_VERSION,
        "row_count": int(len(sandbox)),
        "sandbox_status_counts": sandbox["sandbox_status"].value_counts(dropna=False).to_dict()
        if not sandbox.empty
        else {},
        "recommended_next_action_counts": sandbox["recommended_next_action"].value_counts(dropna=False).to_dict()
        if not sandbox.empty
        else {},
        "next_sandbox_id": _to_text(next_sandbox.iloc[0]["sandbox_id"], "") if not next_sandbox.empty else "",
    }
    return sandbox, summary


def render_manual_vs_heuristic_bias_sandbox_markdown(
    summary: Mapping[str, Any],
    sandbox: pd.DataFrame,
) -> str:
    lines = [
        "# Manual vs Heuristic Bias Sandbox Loop v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- sandbox statuses: `{summary.get('sandbox_status_counts', {})}`",
        f"- recommended actions: `{summary.get('recommended_next_action_counts', {})}`",
        f"- next sandbox: `{summary.get('next_sandbox_id', '')}`",
        "",
        "## Sandbox Preview",
    ]
    preview = sandbox.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("sandbox_status", "")),
                        _to_text(row.get("correction_priority_tier", "")),
                        _to_text(row.get("miss_type", "")),
                        f"cases={_to_text(row.get('case_count', '0'))}",
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
            lines.append(f"  hypothesis: {_to_text(row.get('patch_hypothesis', ''), '')}")
    return "\n".join(lines) + "\n"
