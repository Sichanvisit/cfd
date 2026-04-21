"""Build proposed negative follow-through expansion rows from failure harvest."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_VERSION = "follow_through_negative_expansion_draft_v1"

FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_COLUMNS = [
    "draft_id",
    "market_family",
    "source_observation_id",
    "surface_state",
    "continuation_target",
    "continuation_positive_binary",
    "draft_weight",
    "draft_source_strength",
    "draft_reason",
    "time_axis_phase",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def build_follow_through_negative_expansion_draft(
    *,
    failure_label_harvest_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    failure_frame = _to_frame(failure_label_harvest_payload)
    if failure_frame.empty:
        empty = pd.DataFrame(columns=FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_COLUMNS)
        return empty, {
            "follow_through_negative_expansion_draft_version": FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "market_family_counts": {},
            "recommended_next_action": "await_follow_through_negative_candidates",
        }

    candidates = failure_frame.loc[
        (failure_frame["surface_label_family"] == "follow_through_surface")
        & (
            failure_frame["failure_label"].isin(
                [
                    "failed_follow_through",
                    "false_breakout",
                    "wrong_side_sell_pressure",
                    "wrong_side_buy_pressure",
                    "missed_up_continuation",
                    "missed_down_continuation",
                ]
            )
        )
    ].copy()

    rows: list[dict[str, Any]] = []
    for row in candidates.to_dict(orient="records"):
        strength = str(row.get("harvest_strength", "candidate"))
        rows.append(
            {
                "draft_id": f"follow_through_negative_draft::{row.get('market_family', '')}::{row.get('observation_event_id', '')}",
                "market_family": str(row.get("market_family", "")).upper(),
                "source_observation_id": str(row.get("observation_event_id", "")),
                "surface_state": str(row.get("surface_label_state", "")),
                "continuation_target": "NOT_CONTINUE",
                "continuation_positive_binary": 0,
                "draft_weight": 1.0 if strength == "confirmed" else 0.45,
                "draft_source_strength": strength,
                "draft_reason": str(row.get("failure_label", "")),
                "time_axis_phase": str(row.get("time_axis_phase", "")),
            }
        )

    frame = pd.DataFrame(rows, columns=FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_COLUMNS)
    summary = {
        "follow_through_negative_expansion_draft_version": FOLLOW_THROUGH_NEGATIVE_EXPANSION_DRAFT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "market_family_counts": frame["market_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "review_follow_through_negative_draft"
            if not frame.empty
            else "await_follow_through_negative_candidates"
        ),
    }
    return frame, summary


def render_follow_through_negative_expansion_draft_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Follow-Through Negative Expansion Draft",
        "",
        f"- version: `{summary.get('follow_through_negative_expansion_draft_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
