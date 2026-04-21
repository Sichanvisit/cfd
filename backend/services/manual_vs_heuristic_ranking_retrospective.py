"""Retrospective layer for family-ranking outcomes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_RANKING_RETROSPECTIVE_VERSION = "manual_vs_heuristic_ranking_retrospective_v0"

MANUAL_VS_HEURISTIC_RANKING_HISTORY_COLUMNS = [
    "ranking_snapshot_id",
    "snapshot_at",
    "family_key",
    "priority_tier",
    "recommended_next_action",
    "priority_score_total",
    "priority_score_evidence",
    "priority_score_reproducibility",
    "priority_score_correction_cost",
    "priority_score_freeze_risk_penalty",
    "actual_followup_taken",
    "followup_started_at",
    "followup_finished_at",
    "retrospective_status",
    "retrospective_result",
    "retrospective_reason",
    "was_true_priority",
    "was_false_priority",
    "needed_more_truth",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(str(value).strip())
    except Exception:
        return float(default)


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _correction_run_lookup(runs: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if runs is None or runs.empty or "family_key" not in runs.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in runs.iterrows():
        family_key = _to_text(row.get("family_key", ""), "")
        if family_key:
            lookup[family_key] = row.to_dict()
    return lookup


def _manual_retrospective_lookup(entries: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if entries is None or entries.empty or "family_key" not in entries.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in entries.iterrows():
        family_key = _to_text(row.get("family_key", ""), "")
        if family_key:
            lookup[family_key] = row.to_dict()
    return lookup


def _derive_retrospective_result(
    ranking_row: Mapping[str, Any],
    run_row: Mapping[str, Any],
    manual_row: Mapping[str, Any],
) -> tuple[str, str, str, bool]:
    manual_result = _to_text(manual_row.get("retrospective_result", ""), "").lower()
    manual_reason = _to_text(manual_row.get("retrospective_reason", ""), "")
    if manual_result:
        return (
            manual_result,
            manual_reason or f"manual_override::{manual_result}",
            _to_text(manual_row.get("retrospective_status", ""), "") or "reviewed",
            True,
        )

    decision = _to_text(run_row.get("decision", ""), "").lower()
    next_action = _to_text(ranking_row.get("recommended_next_action", ""), "").lower()
    if decision == "accept":
        return ("correct_priority", "accepted_correction_run", "reviewed", True)
    if decision == "reject":
        return ("false_priority", "rejected_correction_run", "reviewed", True)
    if decision == "hold_for_more_truth":
        return ("needed_more_truth", "hold_for_more_truth_from_correction_run", "reviewed", True)
    if decision == "hold_for_patch_execution":
        return ("not_executed", "patch_candidate_not_executed_yet", "pending_followup", True)
    if next_action == "collect_current_rich_truth":
        return ("needed_more_truth", "ranking_recommended_truth_collection", "pending_followup", False)
    return ("not_executed", "no_followup_recorded_yet", "pending_followup", False)


def build_manual_vs_heuristic_ranking_retrospective(
    ranking: pd.DataFrame,
    correction_runs: pd.DataFrame | None = None,
    *,
    retrospective_entries: pd.DataFrame | None = None,
    now: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ranking_source = ranking.copy() if ranking is not None else pd.DataFrame()
    if ranking_source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_RANKING_HISTORY_COLUMNS)
        summary = {
            "ranking_retrospective_version": MANUAL_VS_HEURISTIC_RANKING_RETROSPECTIVE_VERSION,
            "row_count": 0,
            "retrospective_result_counts": {},
            "ranking_execution_rate": 0.0,
            "ranking_precision": 0.0,
            "ranking_false_priority_rate": 0.0,
            "ranking_needed_more_truth_accuracy": 0.0,
        }
        return empty, summary

    snapshot_at = _to_text(now, "") or datetime.now().isoformat(timespec="seconds")
    run_lookup = _correction_run_lookup(correction_runs)
    manual_lookup = _manual_retrospective_lookup(retrospective_entries)

    rows: list[dict[str, Any]] = []
    for _, row in ranking_source.iterrows():
        row_dict = row.to_dict()
        family_key = _to_text(row_dict.get("family_id", ""), "")
        run_row = run_lookup.get(family_key, {})
        manual_row = manual_lookup.get(family_key, {})
        retrospective_result, retrospective_reason, retrospective_status, followup_taken = _derive_retrospective_result(
            row_dict,
            run_row,
            manual_row,
        )

        followup_started_at = _to_text(
            manual_row.get("followup_started_at", "") or run_row.get("started_at", ""),
            "",
        )
        followup_finished_at = _to_text(
            manual_row.get("followup_finished_at", "") or run_row.get("finished_at", ""),
            "",
        )

        rows.append(
            {
                "ranking_snapshot_id": f"latest::{family_key}",
                "snapshot_at": snapshot_at,
                "family_key": family_key,
                "priority_tier": _to_text(row_dict.get("correction_priority_tier", ""), "").upper(),
                "recommended_next_action": _to_text(row_dict.get("recommended_next_action", ""), "").lower(),
                "priority_score_total": _to_float(row_dict.get("priority_score_total", 0.0), 0.0),
                "priority_score_evidence": _to_float(row_dict.get("priority_score_evidence", 0.0), 0.0),
                "priority_score_reproducibility": _to_float(
                    row_dict.get("priority_score_reproducibility", 0.0),
                    0.0,
                ),
                "priority_score_correction_cost": _to_float(
                    row_dict.get("priority_score_correction_cost", 0.0),
                    0.0,
                ),
                "priority_score_freeze_risk_penalty": _to_float(
                    row_dict.get("priority_score_freeze_risk_penalty", 0.0),
                    0.0,
                ),
                "actual_followup_taken": bool(
                    _to_text(manual_row.get("actual_followup_taken", ""), "").lower() == "true"
                    or followup_taken
                ),
                "followup_started_at": followup_started_at,
                "followup_finished_at": followup_finished_at,
                "retrospective_status": retrospective_status,
                "retrospective_result": retrospective_result,
                "retrospective_reason": retrospective_reason,
                "was_true_priority": retrospective_result == "correct_priority",
                "was_false_priority": retrospective_result == "false_priority",
                "needed_more_truth": retrospective_result == "needed_more_truth",
            }
        )

    history = pd.DataFrame(rows)
    for column in MANUAL_VS_HEURISTIC_RANKING_HISTORY_COLUMNS:
        if column not in history.columns:
            history[column] = ""
    history = history[MANUAL_VS_HEURISTIC_RANKING_HISTORY_COLUMNS].copy()

    executed = history["actual_followup_taken"].astype(bool) if not history.empty else pd.Series(dtype=bool)
    correct = history["retrospective_result"].fillna("").astype(str).eq("correct_priority") if not history.empty else pd.Series(dtype=bool)
    false_priority = history["retrospective_result"].fillna("").astype(str).eq("false_priority") if not history.empty else pd.Series(dtype=bool)
    needed_more_truth = history["retrospective_result"].fillna("").astype(str).eq("needed_more_truth") if not history.empty else pd.Series(dtype=bool)

    executed_count = int(executed.sum()) if not history.empty else 0
    correct_count = int(correct.sum()) if not history.empty else 0
    false_count = int(false_priority.sum()) if not history.empty else 0
    needed_more_truth_count = int(needed_more_truth.sum()) if not history.empty else 0
    summary = {
        "ranking_retrospective_version": MANUAL_VS_HEURISTIC_RANKING_RETROSPECTIVE_VERSION,
        "row_count": int(len(history)),
        "retrospective_result_counts": history["retrospective_result"].value_counts(dropna=False).to_dict()
        if not history.empty
        else {},
        "ranking_execution_rate": round(executed_count / len(history), 3) if len(history) else 0.0,
        "ranking_precision": round(correct_count / max(1, correct_count + false_count), 3) if len(history) else 0.0,
        "ranking_false_priority_rate": round(false_count / max(1, executed_count), 3) if len(history) else 0.0,
        "ranking_needed_more_truth_accuracy": round(
            needed_more_truth_count / max(1, history["recommended_next_action"].fillna("").astype(str).eq("collect_current_rich_truth").sum()),
            3,
        )
        if len(history)
        else 0.0,
    }
    return history, summary


def render_manual_vs_heuristic_ranking_retrospective_markdown(
    summary: Mapping[str, Any],
    history: pd.DataFrame,
) -> str:
    lines = [
        "# Manual vs Heuristic Ranking Retrospective v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- retrospective results: `{summary.get('retrospective_result_counts', {})}`",
        f"- ranking execution rate: `{summary.get('ranking_execution_rate', 0.0)}`",
        f"- ranking precision: `{summary.get('ranking_precision', 0.0)}`",
        f"- false priority rate: `{summary.get('ranking_false_priority_rate', 0.0)}`",
        f"- needed-more-truth accuracy: `{summary.get('ranking_needed_more_truth_accuracy', 0.0)}`",
        "",
        "## Retrospective Preview",
    ]
    if history.empty:
        lines.append("- none")
    else:
        for _, row in history.head(10).iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("priority_tier", ""), ""),
                        _to_text(row.get("retrospective_result", ""), ""),
                        _to_text(row.get("recommended_next_action", ""), ""),
                        _to_text(row.get("retrospective_reason", ""), ""),
                    ]
                )
            )
            lines.append(f"  family: {_to_text(row.get('family_key', ''), '')}")
    return "\n".join(lines) + "\n"
