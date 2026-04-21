"""Select bounded rollout review candidates from symbol-surface preview evaluation."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BOUNDED_ROLLOUT_CANDIDATE_GATE_VERSION = "bounded_rollout_candidate_gate_v1"

BOUNDED_ROLLOUT_CANDIDATE_GATE_COLUMNS = [
    "candidate_id",
    "market_family",
    "surface_name",
    "adapter_mode",
    "readiness_state",
    "row_count",
    "positive_count",
    "negative_count",
    "unlabeled_ratio",
    "strong_row_count",
    "positive_rate",
    "local_failure_burden",
    "probe_eligible_count",
    "rollout_candidate_state",
    "rollout_priority",
    "gate_reason",
    "recommended_next_step",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or [])
                        )
    if frame.empty:
        return frame
    numeric_columns = [
        "row_count",
        "positive_count",
        "negative_count",
        "unlabeled_ratio",
        "strong_row_count",
        "positive_rate",
        "probe_eligible_count",
        "failed_follow_through_count",
        "early_exit_regret_count",
        "false_breakout_count",
        "missed_good_wait_release_count",
        "late_entry_chase_fail_count",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    for column in ("market_family", "surface_name", "adapter_mode", "readiness_state"):
        if column not in frame.columns:
            frame[column] = ""
    return frame


def build_bounded_rollout_candidate_gate(
    symbol_surface_preview_evaluation_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = _to_frame(symbol_surface_preview_evaluation_payload)
    if frame.empty:
        empty = pd.DataFrame(columns=BOUNDED_ROLLOUT_CANDIDATE_GATE_COLUMNS)
        return empty, {
            "bounded_rollout_candidate_gate_version": BOUNDED_ROLLOUT_CANDIDATE_GATE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "review_canary_count": 0,
            "hold_count": 0,
            "recommended_next_action": "await_symbol_surface_preview_evaluation",
        }

    rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        market_family = str(row.get("market_family", "")).upper()
        surface_name = str(row.get("surface_name", ""))
        readiness_state = str(row.get("readiness_state", ""))
        row_count = int(row.get("row_count", 0) or 0)
        positive_count = int(row.get("positive_count", 0) or 0)
        negative_count = int(row.get("negative_count", 0) or 0)
        unlabeled_ratio = float(row.get("unlabeled_ratio", 0.0) or 0.0)
        strong_row_count = int(row.get("strong_row_count", 0) or 0)
        positive_rate = float(row.get("positive_rate", 0.0) or 0.0)
        probe_eligible_count = int(row.get("probe_eligible_count", 0) or 0)
        local_failure_burden = round(
            float(
                (
                    int(row.get("failed_follow_through_count", 0) or 0)
                    + int(row.get("early_exit_regret_count", 0) or 0)
                    + int(row.get("false_breakout_count", 0) or 0)
                    + int(row.get("late_entry_chase_fail_count", 0) or 0)
                )
                / max(1, row_count)
            ),
            6,
        )

        candidate_state = "HOLD_OUT_OF_SCOPE"
        rollout_priority = "P3"
        gate_reason = "surface_not_in_first_rollout_scope"
        next_step = "defer_until_surface_specific_rollout"

        if surface_name == "initial_entry_surface":
            if readiness_state != "preview_eval_ready":
                candidate_state = "HOLD_NOT_READY"
                rollout_priority = "P2"
                gate_reason = f"preview_not_ready::{readiness_state}"
                next_step = "collect_more_or_resolve_labels"
            elif unlabeled_ratio > 0.10:
                candidate_state = "HOLD_LABEL_RESOLUTION"
                rollout_priority = "P2"
                gate_reason = "unlabeled_ratio_above_rollout_cap"
                next_step = "resolve_probe_and_wait_labels"
            elif strong_row_count < 5:
                candidate_state = "HOLD_WEAK_SUPPORT"
                rollout_priority = "P2"
                gate_reason = "not_enough_strong_rows"
                next_step = "promote_more_strong_rows"
            elif local_failure_burden > 0.45:
                candidate_state = "HOLD_FAILURE_BURDEN"
                rollout_priority = "P2"
                gate_reason = "local_failure_burden_too_high"
                next_step = "reduce_false_positive_and_regret_burden"
            else:
                candidate_state = "REVIEW_CANARY_CANDIDATE"
                rollout_priority = "P1"
                gate_reason = "bounded_initial_entry_canary_ready_for_review"
                next_step = f"prepare_{market_family.lower()}_initial_entry_canary_review"

        rows.append(
            {
                "candidate_id": f"bounded_rollout_candidate::{market_family}::{surface_name}",
                "market_family": market_family,
                "surface_name": surface_name,
                "adapter_mode": str(row.get("adapter_mode", "")),
                "readiness_state": readiness_state,
                "row_count": row_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "unlabeled_ratio": unlabeled_ratio,
                "strong_row_count": strong_row_count,
                "positive_rate": positive_rate,
                "local_failure_burden": local_failure_burden,
                "probe_eligible_count": probe_eligible_count,
                "rollout_candidate_state": candidate_state,
                "rollout_priority": rollout_priority,
                "gate_reason": gate_reason,
                "recommended_next_step": next_step,
            }
        )

    out = pd.DataFrame(rows, columns=BOUNDED_ROLLOUT_CANDIDATE_GATE_COLUMNS)
    summary = {
        "bounded_rollout_candidate_gate_version": BOUNDED_ROLLOUT_CANDIDATE_GATE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(out)),
        "review_canary_count": int((out["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE").sum()),
        "hold_count": int((out["rollout_candidate_state"] != "REVIEW_CANARY_CANDIDATE").sum()),
        "candidate_state_counts": out["rollout_candidate_state"].value_counts().to_dict() if not out.empty else {},
        "recommended_next_action": "review_canary_candidates"
        if int((out["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE").sum()) > 0
        else "collect_more_rollout_readiness_support",
    }
    return out, summary


def render_bounded_rollout_candidate_gate_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Bounded Rollout Candidate Gate",
        "",
        f"- version: `{summary.get('bounded_rollout_candidate_gate_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- candidate_state_counts: `{summary.get('candidate_state_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    if not frame.empty:
        lines.extend(["## Candidates", ""])
        for row in frame.to_dict(orient="records"):
            lines.append(
                "- "
                + f"{row.get('market_family', '')} | {row.get('surface_name', '')} | "
                + f"{row.get('rollout_candidate_state', '')} | reason={row.get('gate_reason', '')} | "
                + f"next={row.get('recommended_next_step', '')}"
            )
    return "\n".join(lines).rstrip() + "\n"
