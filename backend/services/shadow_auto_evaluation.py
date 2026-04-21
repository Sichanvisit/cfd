"""Aggregate evaluation layer for shadow-vs-baseline storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_EVALUATION_VERSION = "shadow_auto_evaluation_v0"

SHADOW_AUTO_EVALUATION_COLUMNS = [
    "shadow_candidate_id",
    "family_key",
    "patch_version",
    "candidate_kind",
    "bridge_status",
    "evaluation_window_start",
    "evaluation_window_end",
    "target_family_key",
    "observed_row_count",
    "shadow_available_row_count",
    "manual_reference_row_count",
    "improved_row_count",
    "regression_row_count",
    "no_change_row_count",
    "unavailable_row_count",
    "shadow_win_rate",
    "shadow_pnl_diff",
    "shadow_drawdown",
    "manual_alignment_improvement",
    "new_false_positive_count",
    "new_freeze_worthy_case_count",
    "pnl_signal_status",
    "decision_readiness",
    "recommended_next_action",
    "evaluation_reason_summary",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else default


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def load_shadow_auto_evaluation_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _decision_readiness(
    *,
    bridge_status: str,
    observed_row_count: int,
    shadow_available_row_count: int,
    manual_reference_row_count: int,
    improved_row_count: int,
    regression_row_count: int,
) -> str:
    if bridge_status == "freeze_track_only":
        return "freeze_monitor_only"
    if observed_row_count == 0:
        return "await_matching_rows"
    if shadow_available_row_count == 0:
        return "shadow_runtime_unavailable"
    if manual_reference_row_count < 3:
        return "insufficient_manual_overlap"
    if regression_row_count > improved_row_count:
        return "reject_candidate"
    if improved_row_count >= 3 and regression_row_count == 0:
        return "ready_for_auto_decision"
    if improved_row_count > regression_row_count:
        return "review_shadow_candidate"
    return "hold"


def _recommended_next_action(decision_readiness: str) -> str:
    mapping = {
        "freeze_monitor_only": "freeze_and_monitor",
        "await_matching_rows": "collect_runtime_overlap",
        "shadow_runtime_unavailable": "enable_shadow_runtime",
        "insufficient_manual_overlap": "collect_more_manual_truth",
        "reject_candidate": "freeze_shadow_candidate",
        "ready_for_auto_decision": "prepare_auto_decision_candidate",
        "review_shadow_candidate": "review_before_shadow_decision",
        "hold": "hold_and_monitor",
    }
    return mapping.get(decision_readiness, "hold_and_monitor")


def _window_bounds(subset: pd.DataFrame) -> tuple[str, str]:
    if subset is None or subset.empty or "timestamp" not in subset.columns:
        return "", ""
    timestamps = pd.to_datetime(subset["timestamp"], errors="coerce")
    valid_mask = timestamps.notna()
    if not bool(valid_mask.any()):
        return (_to_text(subset["timestamp"].iloc[0]), _to_text(subset["timestamp"].iloc[-1]))
    valid_subset = subset.loc[valid_mask].copy()
    valid_subset["__ts__"] = timestamps.loc[valid_mask]
    start_row = valid_subset.sort_values("__ts__", ascending=True).iloc[0]
    end_row = valid_subset.sort_values("__ts__", ascending=False).iloc[0]
    return (_to_text(start_row.get("timestamp")), _to_text(end_row.get("timestamp")))


def _reason_summary(
    *,
    decision_readiness: str,
    observed_row_count: int,
    shadow_available_row_count: int,
    improved_row_count: int,
    regression_row_count: int,
    manual_reference_row_count: int,
) -> str:
    return (
        f"{decision_readiness}::observed={observed_row_count}"
        f"::shadow_available={shadow_available_row_count}"
        f"::manual_refs={manual_reference_row_count}"
        f"::improved={improved_row_count}"
        f"::regression={regression_row_count}"
    )


def build_shadow_auto_evaluation(
    shadow_vs_baseline: pd.DataFrame,
    *,
    shadow_candidates: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    compare_df = shadow_vs_baseline.copy() if shadow_vs_baseline is not None else pd.DataFrame()
    candidates_df = shadow_candidates.copy() if shadow_candidates is not None else pd.DataFrame()

    candidate_rows = candidates_df.to_dict(orient="records") if not candidates_df.empty else []
    compare_df = compare_df.copy()
    if compare_df.empty:
        compare_df = pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for candidate in candidate_rows:
        shadow_candidate_id = _to_text(candidate.get("shadow_candidate_id"))
        subset = compare_df.loc[
            compare_df.get("shadow_candidate_id", pd.Series(dtype=str)).fillna("").astype(str) == shadow_candidate_id
        ].copy()
        observed_row_count = int(len(subset))
        shadow_available_row_count = int(subset.get("semantic_shadow_available", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if observed_row_count else 0
        manual_reference_row_count = int(subset.get("manual_label", pd.Series(dtype=str)).fillna("").astype(str).ne("").sum()) if observed_row_count else 0
        improved_row_count = int(subset.get("match_improvement", pd.Series(dtype=str)).fillna("").astype(str).eq("improved").sum()) if observed_row_count else 0
        regression_row_count = int(subset.get("match_improvement", pd.Series(dtype=str)).fillna("").astype(str).eq("regression").sum()) if observed_row_count else 0
        no_change_row_count = int(subset.get("match_improvement", pd.Series(dtype=str)).fillna("").astype(str).eq("no_material_change").sum()) if observed_row_count else 0
        unavailable_row_count = int(subset.get("shadow_match", pd.Series(dtype=str)).fillna("").astype(str).isin(["unavailable", "unknown"]).sum()) if observed_row_count else 0
        actionable = improved_row_count + regression_row_count + no_change_row_count
        shadow_win_rate = round(improved_row_count / actionable, 4) if actionable > 0 else None
        manual_alignment_improvement = improved_row_count - regression_row_count
        new_false_positive_count = int(subset.get("shadow_match", pd.Series(dtype=str)).fillna("").astype(str).isin(["risk_of_overtrade", "likely_worse"]).sum()) if observed_row_count else 0
        new_freeze_worthy_case_count = int(subset.get("shadow_match", pd.Series(dtype=str)).fillna("").astype(str).eq("likely_worse").sum()) if observed_row_count else 0
        evaluation_window_start, evaluation_window_end = _window_bounds(subset)
        bridge_status = _to_text(candidate.get("bridge_status"))
        decision_readiness = _decision_readiness(
            bridge_status=bridge_status,
            observed_row_count=observed_row_count,
            shadow_available_row_count=shadow_available_row_count,
            manual_reference_row_count=manual_reference_row_count,
            improved_row_count=improved_row_count,
            regression_row_count=regression_row_count,
        )
        rows.append(
            {
                "shadow_candidate_id": shadow_candidate_id,
                "family_key": _to_text(candidate.get("family_key")),
                "patch_version": _to_text(candidate.get("patch_version")),
                "candidate_kind": _to_text(candidate.get("candidate_kind")),
                "bridge_status": bridge_status,
                "evaluation_window_start": evaluation_window_start,
                "evaluation_window_end": evaluation_window_end,
                "target_family_key": _to_text(candidate.get("family_key")),
                "observed_row_count": observed_row_count,
                "shadow_available_row_count": shadow_available_row_count,
                "manual_reference_row_count": manual_reference_row_count,
                "improved_row_count": improved_row_count,
                "regression_row_count": regression_row_count,
                "no_change_row_count": no_change_row_count,
                "unavailable_row_count": unavailable_row_count,
                "shadow_win_rate": shadow_win_rate,
                "shadow_pnl_diff": None,
                "shadow_drawdown": None,
                "manual_alignment_improvement": manual_alignment_improvement,
                "new_false_positive_count": new_false_positive_count,
                "new_freeze_worthy_case_count": new_freeze_worthy_case_count,
                "pnl_signal_status": "pending_shadow_execution",
                "decision_readiness": decision_readiness,
                "recommended_next_action": _recommended_next_action(decision_readiness),
                "evaluation_reason_summary": _reason_summary(
                    decision_readiness=decision_readiness,
                    observed_row_count=observed_row_count,
                    shadow_available_row_count=shadow_available_row_count,
                    improved_row_count=improved_row_count,
                    regression_row_count=regression_row_count,
                    manual_reference_row_count=manual_reference_row_count,
                ),
            }
        )

    evaluation = pd.DataFrame(rows, columns=SHADOW_AUTO_EVALUATION_COLUMNS)
    summary = {
        "shadow_auto_evaluation_version": SHADOW_AUTO_EVALUATION_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "candidate_count": int(len(evaluation)),
        "observed_candidate_count": int(evaluation["observed_row_count"].fillna(0).astype(int).gt(0).sum()) if not evaluation.empty else 0,
        "shadow_available_candidate_count": int(evaluation["shadow_available_row_count"].fillna(0).astype(int).gt(0).sum()) if not evaluation.empty else 0,
        "decision_readiness_counts": evaluation["decision_readiness"].value_counts().to_dict() if not evaluation.empty else {},
        "recommended_next_action_counts": evaluation["recommended_next_action"].value_counts().to_dict() if not evaluation.empty else {},
        "pnl_signal_status": "pending_shadow_execution",
    }
    return evaluation, summary


def render_shadow_auto_evaluation_markdown(summary: dict[str, Any], evaluation: pd.DataFrame) -> str:
    lines = [
        "# Shadow Evaluation",
        "",
        f"- version: `{summary.get('shadow_auto_evaluation_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- observed_candidate_count: `{summary.get('observed_candidate_count', 0)}`",
        f"- shadow_available_candidate_count: `{summary.get('shadow_available_candidate_count', 0)}`",
        f"- pnl_signal_status: `{summary.get('pnl_signal_status', '')}`",
        "",
        "## Aggregate",
        "",
        f"- decision_readiness_counts: `{summary.get('decision_readiness_counts', {})}`",
        f"- recommended_next_action_counts: `{summary.get('recommended_next_action_counts', {})}`",
        "",
        "## Candidate Rows",
        "",
    ]
    if evaluation.empty:
        lines.append("- no shadow evaluation rows available")
        return "\n".join(lines) + "\n"

    for row in evaluation.head(10).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('family_key', '')}",
                "",
                f"- decision_readiness: `{row.get('decision_readiness', '')}`",
                f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                f"- observed_row_count: `{row.get('observed_row_count', 0)}`",
                f"- shadow_available_row_count: `{row.get('shadow_available_row_count', 0)}`",
                f"- manual_alignment_improvement: `{row.get('manual_alignment_improvement', 0)}`",
                f"- reason: `{row.get('evaluation_reason_summary', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
