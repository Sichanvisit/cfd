"""SA4b divergence audit for shadow-vs-baseline behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.shadow_auto_edge_metrics import (
    attach_manual_truth,
    enrich_action_frame,
    load_demo_frame,
    load_feature_rows_frame,
    load_manual_truth_frame,
    merge_demo_with_feature_rows,
    summarize_action_frame,
)
from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_DIVERGENCE_AUDIT_VERSION = "shadow_auto_divergence_audit_v1"
SHADOW_AUTO_DIVERGENCE_AUDIT_COLUMNS = [
    "candidate_id",
    "family_key",
    "scope_kind",
    "scope_value",
    "row_count",
    "baseline_enter_count",
    "shadow_enter_count",
    "baseline_wait_count",
    "shadow_wait_count",
    "baseline_exit_count",
    "shadow_exit_count",
    "same_action_count",
    "different_action_count",
    "divergence_rate",
    "enter_flip_count",
    "wait_flip_count",
    "exit_flip_count",
    "manual_reference_row_count",
    "manual_alignment_rate_baseline",
    "manual_alignment_rate_shadow",
    "manual_alignment_delta",
    "baseline_alignment_rate_proxy",
    "shadow_alignment_rate_proxy",
    "proxy_alignment_improvement",
    "baseline_alignment_rate_mapped",
    "shadow_alignment_rate_mapped",
    "mapped_alignment_improvement",
    "baseline_value_sum",
    "shadow_value_sum",
    "value_diff_proxy",
    "recommended_next_action",
    "risk_flag",
    "bounded_risk_flag",
]


def load_shadow_auto_divergence_audit_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _recommended_next_action(row: dict[str, Any]) -> tuple[str, str]:
    divergence_rate = float(row.get("divergence_rate", 0.0) or 0.0)
    value_diff_proxy = float(row.get("value_diff_proxy", 0.0) or 0.0)
    mapped_alignment_improvement = float(row.get("mapped_alignment_improvement", 0.0) or 0.0)
    manual_alignment_delta = float(row.get("manual_alignment_delta", 0.0) or 0.0)
    manual_reference_row_count = int(row.get("manual_reference_row_count", 0) or 0)
    bounded_risk_flag = str(row.get("bounded_risk_flag", "") or "")
    if divergence_rate <= 0.0:
        return ("increase_divergence", "no_behavior_difference_detected")
    if manual_reference_row_count > 0 and manual_alignment_delta < 0.0:
        return ("redesign_target_mapping_or_thresholds", "manual_truth_alignment_regressed")
    if mapped_alignment_improvement > 0.0 and value_diff_proxy >= 0.0:
        return ("carry_forward_to_threshold_sweep", "divergence_present_and_bounded")
    if manual_reference_row_count <= 0 and bounded_risk_flag == "manual_truth_missing":
        return ("redesign_target_mapping_or_thresholds", "manual_truth_missing_for_divergence")
    if mapped_alignment_improvement < 0.0:
        return ("redesign_target_mapping_or_thresholds", "divergence_conflicts_with_mapped_target")
    if value_diff_proxy < 0.0:
        return ("reject_current_profile", "divergence_reduces_value_proxy")
    return ("review_divergence_profile", "mixed_divergence_signal")


def build_shadow_auto_divergence_audit(
    demo: pd.DataFrame | None,
    *,
    feature_rows: pd.DataFrame | None = None,
    manual_truth: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    demo_df = demo.copy() if demo is not None else pd.DataFrame()
    feature_df = feature_rows.copy() if feature_rows is not None else pd.DataFrame()
    manual_df = manual_truth.copy() if manual_truth is not None else pd.DataFrame()
    merged = enrich_action_frame(
        attach_manual_truth(
            merge_demo_with_feature_rows(demo_df, feature_df),
            manual_df,
        )
    )

    rows: list[dict[str, Any]] = []
    if not merged.empty:
        scopes: list[tuple[str, str, pd.DataFrame]] = [("overall", "all", merged)]
        for symbol, subset in merged.groupby("symbol", dropna=False):
            scopes.append(("symbol", str(symbol or "unknown"), subset.copy()))
        for scene_family, subset in merged.groupby("scene_family", dropna=False):
            scopes.append(("scene_family", str(scene_family or "unknown"), subset.copy()))
        for scope_kind, scope_value, subset in scopes:
            row = summarize_action_frame(subset, scope_kind=scope_kind, scope_value=scope_value)
            action, risk_flag = _recommended_next_action(row)
            row["recommended_next_action"] = action
            row["risk_flag"] = risk_flag
            rows.append(row)

    frame = pd.DataFrame(rows, columns=SHADOW_AUTO_DIVERGENCE_AUDIT_COLUMNS)
    summary = {
        "shadow_auto_divergence_audit_version": SHADOW_AUTO_DIVERGENCE_AUDIT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "overall_divergence_rate": float(frame.iloc[0]["divergence_rate"]) if not frame.empty else 0.0,
        "manual_reference_row_count": int(frame.iloc[0]["manual_reference_row_count"]) if not frame.empty else 0,
        "recommended_next_action_counts": frame["recommended_next_action"].value_counts().to_dict() if not frame.empty else {},
        "bounded_risk_flag_counts": frame["bounded_risk_flag"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_shadow_auto_divergence_audit_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Shadow Divergence Audit",
        "",
        f"- version: `{summary.get('shadow_auto_divergence_audit_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- overall_divergence_rate: `{summary.get('overall_divergence_rate', 0.0)}`",
        f"- manual_reference_row_count: `{summary.get('manual_reference_row_count', 0)}`",
        f"- recommended_next_action_counts: `{summary.get('recommended_next_action_counts', {})}`",
        f"- bounded_risk_flag_counts: `{summary.get('bounded_risk_flag_counts', {})}`",
        "",
        "## Audit Rows",
        "",
    ]
    if frame.empty:
        lines.append("- no divergence audit rows available")
        return "\n".join(lines) + "\n"
    for row in frame.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('scope_kind', '')} :: {row.get('scope_value', '')}",
                "",
                f"- divergence_rate: `{row.get('divergence_rate', 0.0)}`",
                f"- enter_flip_count: `{row.get('enter_flip_count', 0)}`",
                f"- wait_flip_count: `{row.get('wait_flip_count', 0)}`",
                f"- exit_flip_count: `{row.get('exit_flip_count', 0)}`",
                f"- manual_reference_row_count: `{row.get('manual_reference_row_count', 0)}`",
                f"- manual_alignment_delta: `{row.get('manual_alignment_delta', 0.0)}`",
                f"- mapped_alignment_improvement: `{row.get('mapped_alignment_improvement', 0.0)}`",
                f"- value_diff_proxy: `{row.get('value_diff_proxy', 0.0)}`",
                f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                f"- bounded_risk_flag: `{row.get('bounded_risk_flag', '')}`",
                f"- risk_flag: `{row.get('risk_flag', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
