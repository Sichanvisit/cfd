"""Build proposed label-resolution draft for initial-entry unresolved rows."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_VERSION = "initial_entry_label_resolution_draft_v1"

INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_COLUMNS = [
    "draft_id",
    "market_family",
    "preview_row_id",
    "surface_state",
    "action_target",
    "adapter_mode",
    "recommended_bias_action",
    "proposed_action_target",
    "proposed_enter_now_binary",
    "proposal_confidence",
    "proposal_reason",
    "manual_review_required",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _proposal_for_row(row: Mapping[str, Any]) -> tuple[str, int, float, str]:
    market_family = str(row.get("market_family", "")).upper()
    action_target = str(row.get("action_target", ""))
    bias = str(row.get("recommended_bias_action", ""))
    adapter_mode = str(row.get("adapter_mode", ""))
    surface_state = str(row.get("surface_state", ""))

    if (
        market_family == "BTCUSD"
        and action_target == "PROBE_ENTRY"
        and surface_state == "timing_better_entry"
        and adapter_mode == "btc_observe_relief_adapter"
        and bias == "bias_follow_through_capture"
    ):
        return (
            "ENTER_NOW",
            1,
            0.63,
            "btc observe-relief adapter suggests capture bias on unlabeled timing-better probe rows",
        )
    if (
        market_family == "NAS100"
        and action_target == "PROBE_ENTRY"
        and surface_state == "timing_better_entry"
        and adapter_mode == "nas_conflict_observe_adapter"
    ):
        return (
            "ENTER_NOW",
            1,
            0.61,
            "nas conflict-observe adapter suggests enter-now resolution for unlabeled timing-better probe rows",
        )
    if (
        market_family == "XAUUSD"
        and action_target == "PROBE_ENTRY"
        and surface_state == "timing_better_entry"
        and adapter_mode == "xau_initial_entry_selective_adapter"
    ):
        return (
            "WAIT_MORE",
            0,
            0.64,
            "xau initial-entry selective adapter suggests conservative resolution for unlabeled probe rows",
        )
    return (
        "WAIT_MORE",
        0,
        0.5,
        "default conservative resolution for unresolved unlabeled initial-entry row",
    )


def build_initial_entry_label_resolution_draft(
    *,
    initial_entry_label_resolution_queue_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    queue_frame = _to_frame(initial_entry_label_resolution_queue_payload)
    if queue_frame.empty:
        empty = pd.DataFrame(columns=INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_COLUMNS)
        return empty, {
            "initial_entry_label_resolution_draft_version": INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "market_family_counts": {},
            "recommended_next_action": "await_label_resolution_queue",
        }

    rows: list[dict[str, Any]] = []
    for row in queue_frame.to_dict(orient="records"):
        proposed_action_target, proposed_enter_now_binary, proposal_confidence, proposal_reason = _proposal_for_row(row)
        rows.append(
            {
                "draft_id": f"initial_entry_label_draft::{row.get('market_family', '')}::{row.get('preview_row_id', '')}",
                "market_family": str(row.get("market_family", "")).upper(),
                "preview_row_id": str(row.get("preview_row_id", "")),
                "surface_state": str(row.get("surface_state", "")),
                "action_target": str(row.get("action_target", "")),
                "adapter_mode": str(row.get("adapter_mode", "")),
                "recommended_bias_action": str(row.get("recommended_bias_action", "")),
                "proposed_action_target": proposed_action_target,
                "proposed_enter_now_binary": proposed_enter_now_binary,
                "proposal_confidence": proposal_confidence,
                "proposal_reason": proposal_reason,
                "manual_review_required": True,
            }
        )

    frame = pd.DataFrame(rows, columns=INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_COLUMNS)
    summary = {
        "initial_entry_label_resolution_draft_version": INITIAL_ENTRY_LABEL_RESOLUTION_DRAFT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "market_family_counts": frame["market_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "review_and_accept_initial_entry_label_draft"
            if not frame.empty
            else "await_label_resolution_queue"
        ),
    }
    return frame, summary


def render_initial_entry_label_resolution_draft_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Initial Entry Label Resolution Draft",
        "",
        f"- version: `{summary.get('initial_entry_label_resolution_draft_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
