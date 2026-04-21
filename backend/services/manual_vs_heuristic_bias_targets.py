"""Bias correction target extraction from recovered manual-vs-heuristic cases."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


MANUAL_VS_HEURISTIC_BIAS_TARGETS_VERSION = "manual_vs_heuristic_bias_targets_v0"

MANUAL_VS_HEURISTIC_BIAS_TARGET_COLUMNS = [
    "target_id",
    "priority",
    "miss_type",
    "primary_correction_target",
    "manual_wait_teacher_label",
    "heuristic_barrier_main_label",
    "heuristic_wait_family",
    "case_count",
    "symbol_counts",
    "alignment_counts",
    "top_reconstruction_sources",
    "representative_episode_ids",
    "recommended_bias_action",
    "recommended_bce_step",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def load_manual_vs_heuristic_recovered_casebook_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _recommended_action_for_target(miss_type: str, correction_target: str) -> tuple[str, str]:
    miss_key = _to_text(miss_type, "aligned").lower()
    target_key = _to_text(correction_target, "none").lower()
    if miss_key == "false_avoided_loss":
        return (
            "timing_improvement 승격 경계와 avoided_loss dominance 규칙을 함께 재조정",
            "BCE bias correction / timing_improvement recovery",
        )
    if miss_key == "wrong_failed_wait_interpretation":
        return (
            "failed_wait 또는 missed_profit 복원 규칙을 강화하고 neutral_wait 과흡수를 줄이기",
            "BCE bias correction / failed_wait recovery",
        )
    if miss_key == "wrong_protective_interpretation":
        return (
            "protective_exit 해석과 relief/protective 매핑 규칙을 별도 검토",
            "BCE bias correction / protective_exit refinement",
        )
    if target_key == "barrier_bias_rule":
        return (
            "barrier bias rule을 manual answer key 기준으로 재검토",
            "BCE bias correction / barrier bias rule",
        )
    if target_key == "protective_exit_interpretation":
        return (
            "protective_exit 해석을 wait-family와 분리해 재검토",
            "BCE bias correction / protective_exit refinement",
        )
    return (
        "manual recovered case를 기준으로 mismatch 원인 재검토",
        "BCE review",
    )


def _priority_for_target(case_count: int, miss_type: str, correction_target: str) -> str:
    miss_key = _to_text(miss_type, "aligned").lower()
    if miss_key in {"false_avoided_loss", "wrong_failed_wait_interpretation"} and case_count >= 2:
        return "P1"
    if miss_key == "wrong_protective_interpretation":
        return "P1"
    if _to_text(correction_target, "none").lower() == "barrier_bias_rule":
        return "P2" if case_count < 2 else "P1"
    return "P3"


def build_manual_vs_heuristic_bias_targets(
    recovered_casebook: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = recovered_casebook.copy() if recovered_casebook is not None else pd.DataFrame()
    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_BIAS_TARGET_COLUMNS)
        summary = {
            "bias_targets_version": MANUAL_VS_HEURISTIC_BIAS_TARGETS_VERSION,
            "target_count": 0,
            "priority_counts": {},
            "miss_type_counts": {},
            "recommended_bce_step_counts": {},
            "symbol_coverage": {},
        }
        return empty, summary

    mismatch_like = source[
        source["overall_alignment_grade"].fillna("").astype(str).isin(["mismatch", "partial_match"])
    ].copy()
    if mismatch_like.empty:
        empty = pd.DataFrame(columns=MANUAL_VS_HEURISTIC_BIAS_TARGET_COLUMNS)
        summary = {
            "bias_targets_version": MANUAL_VS_HEURISTIC_BIAS_TARGETS_VERSION,
            "target_count": 0,
            "priority_counts": {},
            "miss_type_counts": {},
            "recommended_bce_step_counts": {},
            "symbol_coverage": {},
        }
        return empty, summary

    group_columns = [
        "miss_type",
        "primary_correction_target",
        "manual_wait_teacher_label",
        "heuristic_barrier_main_label",
        "heuristic_wait_family",
    ]

    rows: list[dict[str, Any]] = []
    for keys, group in mismatch_like.groupby(group_columns, dropna=False, sort=False):
        miss_type, correction_target, manual_label, heuristic_label, heuristic_family = [
            _to_text(value, "aligned" if idx == 0 else "none")
            for idx, value in enumerate(keys)
        ]
        recommended_action, recommended_step = _recommended_action_for_target(miss_type, correction_target)
        case_count = int(len(group))
        priority = _priority_for_target(case_count, miss_type, correction_target)
        symbol_counts = group["symbol"].value_counts(dropna=False).to_dict()
        alignment_counts = group["overall_alignment_grade"].value_counts(dropna=False).to_dict()
        reconstruction_source_counts = (
            group["heuristic_reconstruction_source_file"].fillna("").astype(str).value_counts(dropna=False).to_dict()
        )
        representative_episode_ids = group["episode_id"].fillna("").astype(str).head(5).tolist()
        target_id = "|".join(
            [
                miss_type or "aligned",
                correction_target or "none",
                manual_label or "manual_none",
                heuristic_label or "heuristic_none",
                heuristic_family or "family_none",
            ]
        )
        rows.append(
            {
                "target_id": target_id,
                "priority": priority,
                "miss_type": miss_type,
                "primary_correction_target": correction_target,
                "manual_wait_teacher_label": manual_label,
                "heuristic_barrier_main_label": heuristic_label,
                "heuristic_wait_family": heuristic_family,
                "case_count": case_count,
                "symbol_counts": symbol_counts,
                "alignment_counts": alignment_counts,
                "top_reconstruction_sources": dict(list(reconstruction_source_counts.items())[:3]),
                "representative_episode_ids": representative_episode_ids,
                "recommended_bias_action": recommended_action,
                "recommended_bce_step": recommended_step,
            }
        )

    targets = pd.DataFrame(rows)
    if not targets.empty:
        targets["priority_rank"] = targets["priority"].map({"P1": 0, "P2": 1, "P3": 2}).fillna(3)
        targets = targets.sort_values(
            by=["priority_rank", "case_count", "miss_type", "manual_wait_teacher_label"],
            ascending=[True, False, True, True],
            kind="stable",
        ).copy()
        targets = targets.drop(columns=["priority_rank"])

    for column in MANUAL_VS_HEURISTIC_BIAS_TARGET_COLUMNS:
        if column not in targets.columns:
            targets[column] = ""
    targets = targets[MANUAL_VS_HEURISTIC_BIAS_TARGET_COLUMNS].copy()

    summary = {
        "bias_targets_version": MANUAL_VS_HEURISTIC_BIAS_TARGETS_VERSION,
        "target_count": int(len(targets)),
        "priority_counts": targets["priority"].value_counts(dropna=False).to_dict(),
        "miss_type_counts": targets["miss_type"].value_counts(dropna=False).to_dict(),
        "recommended_bce_step_counts": targets["recommended_bce_step"].value_counts(dropna=False).to_dict(),
        "symbol_coverage": mismatch_like["symbol"].value_counts(dropna=False).to_dict(),
    }
    return targets, summary


def render_manual_vs_heuristic_bias_targets_markdown(summary: Mapping[str, Any], targets: pd.DataFrame) -> str:
    lines = [
        "# Manual vs Heuristic Bias Targets v0",
        "",
        f"- targets: `{summary.get('target_count', 0)}`",
        f"- priority counts: `{summary.get('priority_counts', {})}`",
        f"- miss types: `{summary.get('miss_type_counts', {})}`",
        f"- recommended BCE steps: `{summary.get('recommended_bce_step_counts', {})}`",
        f"- symbol coverage: `{summary.get('symbol_coverage', {})}`",
        "",
        "## Top Targets",
    ]
    preview = targets.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("priority", "")),
                        _to_text(row.get("miss_type", "")),
                        f"cases={_to_text(row.get('case_count', '0'))}",
                        f"manual={_to_text(row.get('manual_wait_teacher_label', ''))}",
                        f"heuristic={_to_text(row.get('heuristic_barrier_main_label', ''))}/{_to_text(row.get('heuristic_wait_family', ''))}",
                        _to_text(row.get("recommended_bce_step", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
