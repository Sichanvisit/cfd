"""SA5a first divergence run selection over threshold sweep profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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


SHADOW_AUTO_FIRST_DIVERGENCE_RUN_VERSION = "shadow_auto_first_divergence_run_v1"
SHADOW_AUTO_FIRST_DIVERGENCE_RUN_COLUMNS = [
    "divergence_run_id",
    "bridge_decision_time",
    "symbol",
    "selected_sweep_profile_id",
    "timing_threshold",
    "entry_quality_threshold",
    "exit_management_threshold",
    "baseline_action_class",
    "baseline_action_variant",
    "shadow_action_class",
    "shadow_action_variant",
    "proxy_target_action_class",
    "proxy_target_action_variant",
    "mapped_target_action_class",
    "mapped_target_action_variant",
    "manual_target_action_class",
    "manual_target_action_variant",
    "effective_target_action_class",
    "effective_target_action_variant",
    "manual_reference_found",
    "action_diverged_flag",
    "proxy_target_match_flag",
    "mapped_target_match_flag",
    "manual_target_match_flag",
    "false_positive_flag",
    "baseline_realized_value",
    "shadow_realized_value",
]


def load_shadow_auto_first_divergence_run_frame(path: str | Path) -> pd.DataFrame:
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


def _select_profile(sweep: pd.DataFrame) -> tuple[dict[str, Any] | None, str]:
    if sweep is None or sweep.empty:
        return None, "missing_threshold_sweep"
    working = sweep.copy()
    for column, default in (
        ("manual_alignment_improvement", 0.0),
        ("mapped_alignment_improvement", 0.0),
        ("value_diff_proxy", 0.0),
        ("drawdown_diff", 0.0),
        ("new_false_positive_count", 0),
        ("divergence_rate", 0.0),
        ("recommended_next_action", ""),
    ):
        if column not in working.columns:
            working[column] = default
    carry = working.loc[working["recommended_next_action"].fillna("").astype(str).eq("carry_forward_to_divergence_run")].copy()
    if not carry.empty:
        carry = carry.sort_values(
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
        return carry.iloc[0].to_dict(), "selected_best_carry_forward_profile"
    candidate = working.loc[working["divergence_rate"].fillna(0.0).astype(float).gt(0.0)].copy()
    if candidate.empty:
        return working.iloc[0].to_dict(), "fallback_first_profile_no_divergence"

    conservative = candidate.sort_values(
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
    return conservative.iloc[0].to_dict(), "selected_best_noncarry_profile"


def _apply_profile(merged: pd.DataFrame, profile: dict[str, Any]) -> pd.DataFrame:
    timing_threshold = float(profile.get("timing_threshold", 0.55) or 0.55)
    entry_threshold = float(profile.get("entry_quality_threshold", 0.55) or 0.55)
    exit_threshold = float(profile.get("exit_management_threshold", 0.8) or 0.8)
    working = merged.copy()
    timing_probability = pd.to_numeric(working.get("shadow_timing_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    entry_probability = pd.to_numeric(working.get("shadow_entry_quality_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    exit_probability = pd.to_numeric(working.get("shadow_exit_management_probability", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    shadow_should_enter = timing_probability.ge(timing_threshold) & entry_probability.ge(entry_threshold)
    shadow_recommendation = [
        (
            "exit_protect"
            if float(exit_prob) >= float(exit_threshold)
            else ("enter_now" if bool(flag) else ("wait_better_entry" if float(entry_prob) >= float(entry_threshold) else "wait_more"))
        )
        for flag, entry_prob, exit_prob in zip(shadow_should_enter, entry_probability, exit_probability)
    ]
    working["shadow_recommendation"] = shadow_recommendation
    working["shadow_action_class"] = [
        classify_shadow_action(
            shadow_should_enter=flag,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
            exit_threshold=exit_threshold,
        )
        for flag, recommendation, exit_prob in zip(shadow_should_enter, shadow_recommendation, exit_probability)
    ]
    working["shadow_action_variant"] = [
        classify_shadow_action_variant(
            shadow_should_enter=flag,
            shadow_recommendation=recommendation,
            shadow_exit_management_probability=exit_prob,
            exit_threshold=exit_threshold,
        )
        for flag, recommendation, exit_prob in zip(shadow_should_enter, shadow_recommendation, exit_probability)
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
    working["action_diverged_flag"] = working["baseline_action_variant"] != working["shadow_action_variant"]
    working["proxy_target_match_flag"] = working["shadow_action_class"] == working["proxy_target_action_class"]
    working["mapped_target_match_flag"] = working["shadow_action_class"] == working["mapped_target_action_class"]
    working["manual_target_match_flag"] = (
        working["shadow_action_class"] == working["manual_target_action_class"]
    ) & working["manual_reference_found"].astype(bool)
    working["false_positive_flag"] = (
        working["action_diverged_flag"].astype(bool)
        & working["shadow_action_class"].eq("enter_now")
        & working["effective_target_action_class"].fillna("").astype(str).ne("enter_now")
    )
    working["selected_sweep_profile_id"] = str(profile.get("sweep_profile_id", ""))
    working["timing_threshold"] = timing_threshold
    working["entry_quality_threshold"] = entry_threshold
    working["exit_management_threshold"] = exit_threshold
    return working


def build_shadow_auto_first_divergence_run(
    demo: pd.DataFrame | None,
    *,
    feature_rows: pd.DataFrame | None = None,
    manual_truth: pd.DataFrame | None = None,
    threshold_sweep: pd.DataFrame | None = None,
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
    freeze_mask = (
        merged.get("freeze_family_flag", pd.Series([False] * len(merged), index=merged.index))
        .fillna(False)
        .astype(bool)
    )
    candidate_merged = merged.loc[~freeze_mask].copy()
    if not candidate_merged.empty:
        merged = candidate_merged
    profile, selection_reason = _select_profile(threshold_sweep.copy() if threshold_sweep is not None else pd.DataFrame())
    if merged.empty or profile is None:
        empty = pd.DataFrame(columns=SHADOW_AUTO_FIRST_DIVERGENCE_RUN_COLUMNS)
        summary = {
            "shadow_auto_first_divergence_run_version": SHADOW_AUTO_FIRST_DIVERGENCE_RUN_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "selected_sweep_profile_id": profile.get("sweep_profile_id", "") if profile else "",
            "selection_reason": selection_reason,
            "run_decision": "hold_for_more_shadow_data",
        }
        return empty, summary

    applied = _apply_profile(merged, profile)
    frame = pd.DataFrame(
        [
            {
                "divergence_run_id": f"shadow_divergence::{idx:04d}",
                "bridge_decision_time": row.get("bridge_decision_time"),
                "symbol": row.get("symbol"),
                "selected_sweep_profile_id": row.get("selected_sweep_profile_id"),
                "timing_threshold": row.get("timing_threshold"),
                "entry_quality_threshold": row.get("entry_quality_threshold"),
                "exit_management_threshold": row.get("exit_management_threshold"),
                "baseline_action_class": row.get("baseline_action_class"),
                "baseline_action_variant": row.get("baseline_action_variant"),
                "shadow_action_class": row.get("shadow_action_class"),
                "shadow_action_variant": row.get("shadow_action_variant"),
                "proxy_target_action_class": row.get("proxy_target_action_class"),
                "proxy_target_action_variant": row.get("proxy_target_action_variant"),
                "mapped_target_action_class": row.get("mapped_target_action_class"),
                "mapped_target_action_variant": row.get("mapped_target_action_variant"),
                "manual_target_action_class": row.get("manual_target_action_class"),
                "manual_target_action_variant": row.get("manual_target_action_variant"),
                "effective_target_action_class": row.get("effective_target_action_class"),
                "effective_target_action_variant": row.get("effective_target_action_variant"),
                "manual_reference_found": bool(row.get("manual_reference_found")),
                "action_diverged_flag": bool(row.get("action_diverged_flag")),
                "proxy_target_match_flag": bool(row.get("proxy_target_match_flag")),
                "mapped_target_match_flag": bool(row.get("mapped_target_match_flag")),
                "manual_target_match_flag": bool(row.get("manual_target_match_flag")),
                "false_positive_flag": bool(row.get("false_positive_flag")),
                "baseline_realized_value": float(row.get("baseline_realized_value", 0.0) or 0.0),
                "shadow_realized_value": float(row.get("shadow_realized_value", 0.0) or 0.0),
            }
            for idx, row in enumerate(applied.to_dict(orient="records"), start=1)
        ],
        columns=SHADOW_AUTO_FIRST_DIVERGENCE_RUN_COLUMNS,
    )
    divergence_rate = float(frame["action_diverged_flag"].mean()) if not frame.empty else 0.0
    proxy_alignment_improvement = float(frame["proxy_target_match_flag"].mean() - applied["baseline_proxy_target_match_flag"].mean()) if not frame.empty else 0.0
    mapped_alignment_improvement = float(frame["mapped_target_match_flag"].mean() - applied["baseline_mapped_target_match_flag"].mean()) if not frame.empty else 0.0
    manual_rows = applied.loc[applied["manual_reference_found"].astype(bool)].copy()
    manual_alignment_improvement = (
        float(manual_rows["manual_target_match_flag"].mean() - manual_rows["baseline_manual_target_match_flag"].mean())
        if not manual_rows.empty
        else 0.0
    )
    value_diff_proxy = float(frame["shadow_realized_value"].sum() - frame["baseline_realized_value"].sum()) if not frame.empty else 0.0
    baseline_drawdown = _sequence_drawdown(frame["baseline_realized_value"]) if not frame.empty else 0.0
    shadow_drawdown = _sequence_drawdown(frame["shadow_realized_value"]) if not frame.empty else 0.0
    drawdown_diff = float(shadow_drawdown - baseline_drawdown)
    new_false_positive_count = int(frame["false_positive_flag"].sum()) if not frame.empty else 0
    manual_reference_row_count = int(frame["manual_reference_found"].sum()) if not frame.empty else 0
    if (
        divergence_rate > 0.0
        and mapped_alignment_improvement >= 0.0
        and value_diff_proxy >= 0.0
        and drawdown_diff <= 0.0
        and new_false_positive_count == 0
        and (manual_reference_row_count <= 0 or manual_alignment_improvement >= 0.0)
    ):
        run_decision = "apply_candidate_preview"
    elif (
        divergence_rate > 0.0
        and (
            mapped_alignment_improvement < 0.0
            or value_diff_proxy < 0.0
            or drawdown_diff > 0.0
            or new_false_positive_count > 0
            or (manual_reference_row_count > 0 and manual_alignment_improvement < 0.0)
        )
    ):
        run_decision = "reject_preview_candidate"
    else:
        run_decision = "hold_for_more_shadow_data"
    summary = {
        "shadow_auto_first_divergence_run_version": SHADOW_AUTO_FIRST_DIVERGENCE_RUN_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "selected_sweep_profile_id": str(profile.get("sweep_profile_id", "")),
        "selection_reason": selection_reason,
        "timing_threshold": float(profile.get("timing_threshold", 0.55) or 0.55),
        "entry_quality_threshold": float(profile.get("entry_quality_threshold", 0.55) or 0.55),
        "exit_management_threshold": float(profile.get("exit_management_threshold", 0.8) or 0.8),
        "divergence_rate": round(divergence_rate, 6),
        "proxy_alignment_improvement": round(proxy_alignment_improvement, 6),
        "mapped_alignment_improvement": round(mapped_alignment_improvement, 6),
        "manual_reference_row_count": manual_reference_row_count,
        "manual_alignment_improvement": round(manual_alignment_improvement, 6),
        "value_diff_proxy": round(value_diff_proxy, 6),
        "drawdown_diff": round(drawdown_diff, 6),
        "new_false_positive_count": new_false_positive_count,
        "run_decision": run_decision,
    }
    return frame, summary


def render_shadow_auto_first_divergence_run_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Shadow First Divergence Run",
        "",
        f"- version: `{summary.get('shadow_auto_first_divergence_run_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- selected_sweep_profile_id: `{summary.get('selected_sweep_profile_id', '')}`",
        f"- selection_reason: `{summary.get('selection_reason', '')}`",
        f"- divergence_rate: `{summary.get('divergence_rate', 0.0)}`",
        f"- manual_reference_row_count: `{summary.get('manual_reference_row_count', 0)}`",
        f"- manual_alignment_improvement: `{summary.get('manual_alignment_improvement', 0.0)}`",
        f"- mapped_alignment_improvement: `{summary.get('mapped_alignment_improvement', 0.0)}`",
        f"- value_diff_proxy: `{summary.get('value_diff_proxy', 0.0)}`",
        f"- drawdown_diff: `{summary.get('drawdown_diff', 0.0)}`",
        f"- new_false_positive_count: `{summary.get('new_false_positive_count', 0)}`",
        f"- run_decision: `{summary.get('run_decision', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
