"""SA4c threshold sweep for the shadow preview lane."""

from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from backend.services.shadow_auto_edge_metrics import (
    attach_manual_truth,
    classify_shadow_action,
    classify_shadow_action_variant,
    enrich_action_frame,
    merge_demo_with_feature_rows,
    resolve_shadow_value_proxy,
)
from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_THRESHOLD_SWEEP_VERSION = "shadow_auto_threshold_sweep_v1"
SHADOW_AUTO_THRESHOLD_SWEEP_COLUMNS = [
    "sweep_profile_id",
    "threshold_family",
    "threshold_value",
    "timing_threshold",
    "entry_quality_threshold",
    "exit_management_threshold",
    "row_count",
    "shadow_enter_count",
    "different_action_count",
    "divergence_rate",
    "manual_reference_row_count",
    "manual_alignment_improvement",
    "baseline_alignment_rate_proxy",
    "shadow_alignment_rate_proxy",
    "proxy_alignment_improvement",
    "baseline_alignment_rate_mapped",
    "shadow_alignment_rate_mapped",
    "mapped_alignment_improvement",
    "baseline_value_sum",
    "shadow_value_sum",
    "value_diff_proxy",
    "baseline_drawdown",
    "shadow_drawdown",
    "drawdown_diff",
    "new_false_positive_count",
    "recommended_next_action",
    "sweep_reason",
]

DEFAULT_THRESHOLD_VALUES = (0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.97, 0.98, 0.99)
DEFAULT_EXIT_THRESHOLD_VALUES = (0.65, 0.80, 0.95, 0.99)


def load_shadow_auto_threshold_sweep_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _sequence_drawdown(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if numeric.empty:
        return 0.0
    cumulative = numeric.cumsum()
    drawdown = cumulative - cumulative.cummax()
    return float(drawdown.min())


def _ordered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    sort_columns = [column for column in ("bridge_decision_time", "time") if column in working.columns]
    if not sort_columns:
        return working
    for column in sort_columns:
        working[f"__sort_{column}"] = pd.to_datetime(working[column], errors="coerce")
    order_columns = [f"__sort_{column}" for column in sort_columns]
    working = working.sort_values(order_columns, ascending=True, kind="mergesort").drop(columns=order_columns)
    return working.reset_index(drop=True)


def _apply_threshold_profile(
    frame: pd.DataFrame,
    *,
    timing_threshold: float,
    entry_quality_threshold: float,
    exit_management_threshold: float,
) -> pd.DataFrame:
    working = frame.copy()
    timing_probability = pd.to_numeric(working.get("shadow_timing_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    entry_probability = pd.to_numeric(working.get("shadow_entry_quality_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    exit_probability = pd.to_numeric(working.get("shadow_exit_management_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    working["shadow_should_enter"] = (
        timing_probability.ge(float(timing_threshold)) & entry_probability.ge(float(entry_quality_threshold))
    )
    shadow_recommendation = [
        (
            "exit_protect"
            if float(exit_prob) >= float(exit_management_threshold)
            else ("enter_now" if bool(should_enter) else ("wait_better_entry" if float(entry_prob) >= float(entry_quality_threshold) else "wait_more"))
        )
        for should_enter, entry_prob, exit_prob in zip(working["shadow_should_enter"], entry_probability, exit_probability)
    ]
    working["shadow_recommendation"] = shadow_recommendation
    working["shadow_action_class"] = [
        classify_shadow_action(
            shadow_should_enter=should_enter,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
            exit_threshold=float(exit_management_threshold),
        )
        for should_enter, recommendation, exit_prob in zip(working["shadow_should_enter"], shadow_recommendation, exit_probability)
    ]
    working["shadow_action_variant"] = [
        classify_shadow_action_variant(
            shadow_should_enter=should_enter,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
            exit_threshold=float(exit_management_threshold),
        )
        for should_enter, recommendation, exit_prob in zip(working["shadow_should_enter"], shadow_recommendation, exit_probability)
    ]
    working["shadow_realized_value"] = [
        resolve_shadow_value_proxy(
            baseline_realized_value=baseline_value,
            shadow_action_variant=shadow_variant,
            effective_target_action_variant=target_variant,
            wait_better_entry_premium=premium,
        )
        for baseline_value, shadow_variant, target_variant, premium in zip(
            working["baseline_realized_value"],
            working["shadow_action_variant"],
            working.get("effective_target_action_variant", pd.Series(dtype=object)),
            working.get("effective_wait_better_entry_premium", pd.Series(dtype=float)),
        )
    ]
    working["action_diverged_flag"] = (
        working["baseline_action_variant"].fillna("").astype(str)
        != working["shadow_action_variant"].fillna("").astype(str)
    )
    working["proxy_target_match_flag"] = (
        working["shadow_action_class"].fillna("").astype(str)
        == working["proxy_target_action_class"].fillna("").astype(str)
    )
    working["mapped_target_match_flag"] = (
        working["shadow_action_class"].fillna("").astype(str)
        == working["mapped_target_action_class"].fillna("").astype(str)
    )
    working["manual_target_match_flag"] = (
        working["shadow_action_class"].fillna("").astype(str)
        == working["manual_target_action_class"].fillna("").astype(str)
    ) & working["manual_reference_found"].astype(bool)
    working["false_positive_flag"] = (
        working["action_diverged_flag"].astype(bool)
        & working["shadow_action_class"].fillna("").astype(str).eq("enter_now")
        & working["effective_target_action_class"].fillna("").astype(str).ne("enter_now")
    )
    return working


def _sweep_recommendation(row: dict[str, Any]) -> tuple[str, str]:
    divergence_rate = float(row.get("divergence_rate", 0.0) or 0.0)
    value_diff_proxy = float(row.get("value_diff_proxy", 0.0) or 0.0)
    drawdown_diff = float(row.get("drawdown_diff", 0.0) or 0.0)
    mapped_alignment_improvement = float(row.get("mapped_alignment_improvement", 0.0) or 0.0)
    manual_alignment_improvement = float(row.get("manual_alignment_improvement", 0.0) or 0.0)
    manual_reference_row_count = int(row.get("manual_reference_row_count", 0) or 0)
    row_count = int(row.get("row_count", 0) or 0)
    new_false_positive_count = int(row.get("new_false_positive_count", 0) or 0)
    false_positive_budget = max(1, int(row_count * 0.10)) if row_count else 0
    if divergence_rate <= 0.0:
        return ("increase_divergence", "thresholds_too_conservative")
    if (
        manual_reference_row_count > 0
        and manual_alignment_improvement > 0.0
        and value_diff_proxy >= 0.0
        and drawdown_diff <= 0.0
        and new_false_positive_count == 0
    ):
        return ("carry_forward_to_divergence_run", "manual_truth_supported_profile_found")
    if (
        manual_reference_row_count <= 0
        and mapped_alignment_improvement > 0.0
        and value_diff_proxy >= 0.0
        and drawdown_diff <= 0.0
        and new_false_positive_count <= false_positive_budget
    ):
        return ("carry_forward_to_divergence_run", "bounded_divergence_profile_found")
    if manual_reference_row_count > 0 and manual_alignment_improvement < 0.0:
        return ("reject_or_redesign_targets", "manual_target_conflict")
    if mapped_alignment_improvement < 0.0 or new_false_positive_count > false_positive_budget:
        return ("reject_or_redesign_targets", "threshold_profile_conflicts_with_target")
    if value_diff_proxy < 0.0 or drawdown_diff > 0.0:
        return ("reject_threshold_profile", "threshold_profile_degrades_value_or_drawdown")
    return ("review_threshold_profile", "mixed_threshold_signal")


def _iter_threshold_profiles(
    values: Sequence[float] | None,
    exit_values: Sequence[float] | None,
) -> Iterable[tuple[float, float, float]]:
    sweep_values = tuple(values or DEFAULT_THRESHOLD_VALUES)
    exit_sweep_values = tuple(exit_values or DEFAULT_EXIT_THRESHOLD_VALUES)
    return product(sweep_values, sweep_values, exit_sweep_values)


def build_shadow_auto_threshold_sweep(
    demo: pd.DataFrame | None,
    *,
    feature_rows: pd.DataFrame | None = None,
    manual_truth: pd.DataFrame | None = None,
    threshold_values: Sequence[float] | None = None,
    exit_threshold_values: Sequence[float] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    merged = enrich_action_frame(
        attach_manual_truth(
            merge_demo_with_feature_rows(
                demo.copy() if demo is not None else pd.DataFrame(),
                feature_rows.copy() if feature_rows is not None else pd.DataFrame(),
            ),
            manual_truth.copy() if manual_truth is not None else pd.DataFrame(),
        )
    )
    merged = _ordered_frame(merged)
    freeze_mask = merged.get("freeze_family_flag", pd.Series([False] * len(merged), index=merged.index)).fillna(False).astype(bool)
    candidate_merged = merged.loc[~freeze_mask].copy()
    if not candidate_merged.empty:
        merged = candidate_merged
    rows: list[dict[str, Any]] = []
    if not merged.empty:
        baseline_alignment_rate_proxy = float(merged["baseline_proxy_target_match_flag"].mean())
        baseline_alignment_rate_mapped = float(merged["baseline_mapped_target_match_flag"].mean())
        baseline_value_sum = float(pd.to_numeric(merged["baseline_realized_value"], errors="coerce").fillna(0.0).sum())
        baseline_drawdown = _sequence_drawdown(merged["baseline_realized_value"])
        manual_rows = merged.loc[merged["manual_reference_found"].astype(bool)].copy()
        baseline_manual_alignment_rate = (
            float(manual_rows["baseline_manual_target_match_flag"].mean())
            if not manual_rows.empty
            else 0.0
        )
        for timing_threshold, entry_quality_threshold, exit_management_threshold in _iter_threshold_profiles(
            threshold_values,
            exit_threshold_values,
        ):
            applied = _apply_threshold_profile(
                merged,
                timing_threshold=float(timing_threshold),
                entry_quality_threshold=float(entry_quality_threshold),
                exit_management_threshold=float(exit_management_threshold),
            )
            applied_manual = applied.loc[applied["manual_reference_found"].astype(bool)].copy()
            shadow_value_sum = float(pd.to_numeric(applied["shadow_realized_value"], errors="coerce").fillna(0.0).sum())
            shadow_drawdown = _sequence_drawdown(applied["shadow_realized_value"])
            shadow_manual_alignment_rate = (
                float(applied_manual["manual_target_match_flag"].mean())
                if not applied_manual.empty
                else 0.0
            )
            row = {
                "sweep_profile_id": f"threshold::{timing_threshold:.2f}::{entry_quality_threshold:.2f}::{exit_management_threshold:.2f}",
                "threshold_family": "timing_entry_exit",
                "threshold_value": (
                    f"timing={timing_threshold:.2f}|entry={entry_quality_threshold:.2f}|exit={exit_management_threshold:.2f}"
                ),
                "timing_threshold": float(timing_threshold),
                "entry_quality_threshold": float(entry_quality_threshold),
                "exit_management_threshold": float(exit_management_threshold),
                "row_count": int(len(applied)),
                "shadow_enter_count": int(applied["shadow_action_class"].eq("enter_now").sum()),
                "different_action_count": int(applied["action_diverged_flag"].sum()),
                "divergence_rate": round(float(applied["action_diverged_flag"].mean()), 6),
                "manual_reference_row_count": int(len(applied_manual)),
                "manual_alignment_improvement": round(shadow_manual_alignment_rate - baseline_manual_alignment_rate, 6),
                "baseline_alignment_rate_proxy": round(baseline_alignment_rate_proxy, 6),
                "shadow_alignment_rate_proxy": round(float(applied["proxy_target_match_flag"].mean()), 6),
                "proxy_alignment_improvement": round(float(applied["proxy_target_match_flag"].mean()) - baseline_alignment_rate_proxy, 6),
                "baseline_alignment_rate_mapped": round(baseline_alignment_rate_mapped, 6),
                "shadow_alignment_rate_mapped": round(float(applied["mapped_target_match_flag"].mean()), 6),
                "mapped_alignment_improvement": round(float(applied["mapped_target_match_flag"].mean()) - baseline_alignment_rate_mapped, 6),
                "baseline_value_sum": round(baseline_value_sum, 6),
                "shadow_value_sum": round(shadow_value_sum, 6),
                "value_diff_proxy": round(shadow_value_sum - baseline_value_sum, 6),
                "baseline_drawdown": round(baseline_drawdown, 6),
                "shadow_drawdown": round(shadow_drawdown, 6),
                "drawdown_diff": round(shadow_drawdown - baseline_drawdown, 6),
                "new_false_positive_count": int(applied["false_positive_flag"].sum()),
            }
            action, reason = _sweep_recommendation(row)
            row["recommended_next_action"] = action
            row["sweep_reason"] = reason
            rows.append(row)
    frame = pd.DataFrame(rows, columns=SHADOW_AUTO_THRESHOLD_SWEEP_COLUMNS)
    summary = {
        "shadow_auto_threshold_sweep_version": SHADOW_AUTO_THRESHOLD_SWEEP_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "recommended_next_action_counts": frame["recommended_next_action"].value_counts().to_dict() if not frame.empty else {},
        "best_profile_id": "",
    }
    if not frame.empty:
        carry = frame.loc[frame["recommended_next_action"].eq("carry_forward_to_divergence_run")].copy()
        candidate = carry if not carry.empty else frame.copy()
        candidate = candidate.sort_values(
            [
                "manual_alignment_improvement",
                "mapped_alignment_improvement",
                "value_diff_proxy",
                "drawdown_diff",
                "new_false_positive_count",
                "divergence_rate",
            ],
            ascending=[False, False, False, True, True, False],
            kind="mergesort",
        )
        summary["best_profile_id"] = str(candidate.iloc[0]["sweep_profile_id"])
    return frame, summary


def render_shadow_auto_threshold_sweep_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Shadow Threshold Sweep",
        "",
        f"- version: `{summary.get('shadow_auto_threshold_sweep_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- best_profile_id: `{summary.get('best_profile_id', '')}`",
        f"- recommended_next_action_counts: `{summary.get('recommended_next_action_counts', {})}`",
        "",
        "## Top Profiles",
        "",
    ]
    if frame.empty:
        lines.append("- no threshold sweep rows available")
        return "\n".join(lines) + "\n"
    ordered = frame.sort_values(
        [
            "manual_alignment_improvement",
            "mapped_alignment_improvement",
            "value_diff_proxy",
            "drawdown_diff",
            "new_false_positive_count",
            "divergence_rate",
        ],
        ascending=[False, False, False, True, True, False],
        kind="mergesort",
    ).head(12)
    for row in ordered.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('sweep_profile_id', '')}",
                "",
                f"- divergence_rate: `{row.get('divergence_rate', 0.0)}`",
                f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0.0)}`",
                f"- mapped_alignment_improvement: `{row.get('mapped_alignment_improvement', 0.0)}`",
                f"- value_diff_proxy: `{row.get('value_diff_proxy', 0.0)}`",
                f"- drawdown_diff: `{row.get('drawdown_diff', 0.0)}`",
                f"- new_false_positive_count: `{row.get('new_false_positive_count', 0)}`",
                f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                f"- sweep_reason: `{row.get('sweep_reason', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
