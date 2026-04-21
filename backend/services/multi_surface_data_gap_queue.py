"""Build gap queue for follow-through negatives and hold/exit data expansion."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


MULTI_SURFACE_DATA_GAP_QUEUE_VERSION = "multi_surface_data_gap_queue_v1"

MULTI_SURFACE_DATA_GAP_QUEUE_COLUMNS = [
    "gap_id",
    "market_family",
    "surface_name",
    "readiness_state",
    "row_count",
    "positive_count",
    "negative_count",
    "recommended_action",
    "gap_family",
    "gap_detail",
    "target_collection_goal",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def build_multi_surface_data_gap_queue(
    *,
    symbol_surface_preview_evaluation_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    eval_frame = _to_frame(symbol_surface_preview_evaluation_payload)
    if eval_frame.empty:
        empty = pd.DataFrame(columns=MULTI_SURFACE_DATA_GAP_QUEUE_COLUMNS)
        return empty, {
            "multi_surface_data_gap_queue_version": MULTI_SURFACE_DATA_GAP_QUEUE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "queue_row_count": 0,
            "gap_family_counts": {},
            "recommended_next_action": "await_surface_data_gap_signal",
        }

    rows: list[dict[str, Any]] = []
    for row in eval_frame.to_dict(orient="records"):
        market_family = str(row.get("market_family", "")).upper()
        surface_name = str(row.get("surface_name", ""))
        readiness_state = str(row.get("readiness_state", ""))
        recommended_action = str(row.get("recommended_action", ""))
        row_count = int(row.get("row_count", 0) or 0)
        positive_count = int(row.get("positive_count", 0) or 0)
        negative_count = int(row.get("negative_count", 0) or 0)

        include = False
        gap_family = ""
        gap_detail = ""
        target_collection_goal = ""

        if surface_name == "follow_through_surface" and readiness_state == "single_class_only":
            include = True
            gap_family = "negative_follow_through_gap"
            gap_detail = "positive-only follow_through rows; need contrastive negative continuation failures"
            target_collection_goal = "collect at least 6 negative follow_through rows per market family"
        elif surface_name == "continuation_hold_surface" and readiness_state == "insufficient_rows":
            include = True
            gap_family = "runner_preservation_gap"
            gap_detail = "runner preservation examples are too sparse for evaluation"
            target_collection_goal = "collect at least 8 continuation_hold rows with both hold and not-hold outcomes"
        elif surface_name == "protective_exit_surface" and readiness_state in {"insufficient_rows", "single_class_only"}:
            include = True
            gap_family = "protective_exit_contrast_gap"
            gap_detail = "protective exit surface lacks enough false-cut/contrast rows"
            target_collection_goal = "collect at least 8 protective_exit rows including negative contrasts"

        if include:
            rows.append(
                {
                    "gap_id": f"multi_surface_gap::{market_family}::{surface_name}",
                    "market_family": market_family,
                    "surface_name": surface_name,
                    "readiness_state": readiness_state,
                    "row_count": row_count,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "recommended_action": recommended_action,
                    "gap_family": gap_family,
                    "gap_detail": gap_detail,
                    "target_collection_goal": target_collection_goal,
                }
            )

    frame = pd.DataFrame(rows, columns=MULTI_SURFACE_DATA_GAP_QUEUE_COLUMNS)
    summary = {
        "multi_surface_data_gap_queue_version": MULTI_SURFACE_DATA_GAP_QUEUE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "queue_row_count": int(len(frame)),
        "gap_family_counts": frame["gap_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "collect_multi_surface_gap_rows"
            if not frame.empty
            else "await_surface_data_gap_signal"
        ),
    }
    return frame, summary


def render_multi_surface_data_gap_queue_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Multi-Surface Data Gap Queue",
        "",
        f"- version: `{summary.get('multi_surface_data_gap_queue_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- queue_row_count: `{summary.get('queue_row_count', 0)}`",
        f"- gap_family_counts: `{summary.get('gap_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
