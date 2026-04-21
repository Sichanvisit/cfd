"""Execution-level evaluation for preview semantic shadow runtime."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_EXECUTION_EVALUATION_VERSION = "shadow_auto_execution_evaluation_v0"
SHADOW_AUTO_EXECUTION_EVALUATION_COLUMNS = [
    "evaluation_scope",
    "row_count",
    "available_row_count",
    "shadow_enter_count",
    "baseline_value_sum",
    "shadow_value_sum",
    "value_diff",
    "baseline_drawdown",
    "shadow_drawdown",
    "drawdown_diff",
    "baseline_alignment_rate",
    "shadow_alignment_rate",
    "manual_alignment_improvement",
    "decision_hint",
]


def _max_drawdown(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    cumulative = values.cumsum()
    running_max = cumulative.cummax()
    drawdown = cumulative - running_max
    return float(drawdown.min())


def _apply_candidate_slice(
    demo: pd.DataFrame,
    candidate_rows: pd.DataFrame | None,
) -> tuple[pd.DataFrame, bool]:
    frame = demo.copy() if demo is not None else pd.DataFrame()
    if frame.empty or candidate_rows is None or candidate_rows.empty:
        return frame, False
    candidate = candidate_rows.copy()
    if "bridge_decision_time" not in frame.columns or "bridge_decision_time" not in candidate.columns:
        return frame, False
    frame["_candidate_time"] = frame["bridge_decision_time"].fillna("").astype(str)
    candidate["_candidate_time"] = candidate["bridge_decision_time"].fillna("").astype(str)
    frame["_candidate_symbol"] = frame.get("symbol", pd.Series(dtype=object)).fillna("").astype(str).str.upper()
    candidate["_candidate_symbol"] = candidate.get("symbol", pd.Series(dtype=object)).fillna("").astype(str).str.upper()
    candidate_keys = set(zip(candidate["_candidate_time"], candidate["_candidate_symbol"]))
    filtered = frame.loc[
        [
            (time_key, symbol_key) in candidate_keys
            for time_key, symbol_key in zip(frame["_candidate_time"], frame["_candidate_symbol"])
        ]
    ].copy()
    frame = filtered if not filtered.empty else frame
    return frame.drop(columns=["_candidate_time", "_candidate_symbol"], errors="ignore"), not filtered.empty


def build_shadow_auto_execution_evaluation(
    demo: pd.DataFrame,
    *,
    candidate_rows: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = demo.copy() if demo is not None else pd.DataFrame()
    frame, candidate_slice_applied = _apply_candidate_slice(frame, candidate_rows)
    if frame.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_EXECUTION_EVALUATION_COLUMNS)
        return empty, {
            "shadow_auto_execution_evaluation_version": SHADOW_AUTO_EXECUTION_EVALUATION_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "baseline_value_sum": 0.0,
            "shadow_value_sum": 0.0,
            "value_diff": 0.0,
            "candidate_slice_applied": False,
        }

    frame["baseline_realized_value"] = pd.to_numeric(frame["baseline_realized_value"], errors="coerce").fillna(0.0)
    frame["shadow_realized_value"] = pd.to_numeric(frame["shadow_realized_value"], errors="coerce").fillna(0.0)
    frame["bridge_decision_time"] = pd.to_datetime(frame["bridge_decision_time"], errors="coerce")
    frame = frame.sort_values("bridge_decision_time", kind="mergesort")

    baseline_alignment_rate = float((frame["target_timing_now_vs_wait"].fillna(0).astype(int) == 1).mean())
    shadow_alignment_rate = float(frame["alignment_label"].fillna("").astype(str).eq("aligned").mean())
    row = {
        "evaluation_scope": "preview_bundle_candidate_slice" if candidate_slice_applied else "preview_bundle_test_bucket",
        "row_count": int(len(frame)),
        "available_row_count": int(frame["semantic_shadow_available"].fillna(False).astype(bool).sum()),
        "shadow_enter_count": int(frame["shadow_should_enter"].fillna(False).astype(bool).sum()),
        "baseline_value_sum": round(float(frame["baseline_realized_value"].sum()), 6),
        "shadow_value_sum": round(float(frame["shadow_realized_value"].sum()), 6),
        "value_diff": round(float(frame["shadow_realized_value"].sum() - frame["baseline_realized_value"].sum()), 6),
        "baseline_drawdown": round(_max_drawdown(frame["baseline_realized_value"]), 6),
        "shadow_drawdown": round(_max_drawdown(frame["shadow_realized_value"]), 6),
        "drawdown_diff": round(_max_drawdown(frame["shadow_realized_value"]) - _max_drawdown(frame["baseline_realized_value"]), 6),
        "baseline_alignment_rate": round(baseline_alignment_rate, 6),
        "shadow_alignment_rate": round(shadow_alignment_rate, 6),
        "manual_alignment_improvement": round(shadow_alignment_rate - baseline_alignment_rate, 6),
        "decision_hint": "actual_profit_or_signed_exit_score_proxy",
    }
    evaluation = pd.DataFrame([row], columns=SHADOW_AUTO_EXECUTION_EVALUATION_COLUMNS)
    summary = {
        "shadow_auto_execution_evaluation_version": SHADOW_AUTO_EXECUTION_EVALUATION_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "candidate_slice_applied": bool(candidate_slice_applied),
        **row,
    }
    return evaluation, summary


def render_shadow_auto_execution_evaluation_markdown(summary: Mapping[str, Any], evaluation: pd.DataFrame) -> str:
    lines = [
        "# Shadow Execution Evaluation",
        "",
        f"- version: `{summary.get('shadow_auto_execution_evaluation_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- available_row_count: `{summary.get('available_row_count', 0)}`",
        f"- shadow_enter_count: `{summary.get('shadow_enter_count', 0)}`",
        f"- baseline_value_sum: `{summary.get('baseline_value_sum', 0.0)}`",
        f"- shadow_value_sum: `{summary.get('shadow_value_sum', 0.0)}`",
        f"- value_diff: `{summary.get('value_diff', 0.0)}`",
        f"- baseline_drawdown: `{summary.get('baseline_drawdown', 0.0)}`",
        f"- shadow_drawdown: `{summary.get('shadow_drawdown', 0.0)}`",
        f"- drawdown_diff: `{summary.get('drawdown_diff', 0.0)}`",
        f"- manual_alignment_improvement: `{summary.get('manual_alignment_improvement', 0.0)}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
