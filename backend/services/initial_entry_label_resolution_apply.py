"""Apply accepted initial-entry label resolutions into a resolved dataset."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_VERSION = "initial_entry_label_resolution_apply_v1"

INITIAL_ENTRY_LABEL_RESOLUTION_STATUS_COLUMN = "label_resolution_status"
INITIAL_ENTRY_LABEL_RESOLUTION_SOURCE_COLUMN = "label_resolution_source"
INITIAL_ENTRY_LABEL_RESOLUTION_CONFIDENCE_COLUMN = "label_resolution_confidence"
INITIAL_ENTRY_LABEL_RESOLUTION_REASON_COLUMN = "label_resolution_reason"
INITIAL_ENTRY_LABEL_RESOLUTION_PREVIOUS_ACTION_COLUMN = "label_resolution_previous_action_target"

INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_COLUMNS = [
    "resolution_id",
    "market_family",
    "preview_row_id",
    "previous_action_target",
    "resolved_action_target",
    "resolved_enter_now_binary",
    "resolved_training_weight",
    "proposal_confidence",
    "resolution_reason",
    "resolution_status",
]


def _normalize_dataset(frame: pd.DataFrame | None) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    for column in (
        "preview_row_id",
        "market_family",
        "action_target",
        "enter_now_binary",
        "training_weight",
    ):
        if column not in dataset.columns:
            dataset[column] = ""
    dataset["preview_row_id"] = dataset["preview_row_id"].fillna("").astype(str)
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["action_target"] = dataset["action_target"].fillna("").astype(str)
    dataset["enter_now_binary"] = pd.to_numeric(dataset["enter_now_binary"], errors="coerce")
    dataset["training_weight"] = pd.to_numeric(dataset["training_weight"], errors="coerce")
    return dataset


def _draft_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    if frame.empty:
        return frame
    for column in (
        "preview_row_id",
        "market_family",
        "proposed_action_target",
        "proposed_enter_now_binary",
        "proposal_confidence",
        "proposal_reason",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["preview_row_id"] = frame["preview_row_id"].fillna("").astype(str)
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["proposed_action_target"] = frame["proposed_action_target"].fillna("").astype(str)
    frame["proposed_enter_now_binary"] = pd.to_numeric(frame["proposed_enter_now_binary"], errors="coerce")
    frame["proposal_confidence"] = pd.to_numeric(frame["proposal_confidence"], errors="coerce").fillna(0.0)
    frame["proposal_reason"] = frame["proposal_reason"].fillna("").astype(str)
    return frame


def build_initial_entry_label_resolution_apply(
    *,
    initial_entry_dataset: pd.DataFrame | None,
    initial_entry_label_resolution_draft_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    dataset = _normalize_dataset(initial_entry_dataset)
    draft_frame = _draft_frame(initial_entry_label_resolution_draft_payload)

    if dataset.empty:
        empty_resolutions = pd.DataFrame(columns=INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_COLUMNS)
        empty_dataset = pd.DataFrame()
        return empty_resolutions, empty_dataset, {
            "initial_entry_label_resolution_apply_version": INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "applied_row_count": 0,
            "market_family_counts": {},
            "missing_preview_row_count": 0,
            "recommended_next_action": "await_initial_entry_dataset",
        }

    resolved_dataset = dataset.copy()
    for column, default in (
        (INITIAL_ENTRY_LABEL_RESOLUTION_STATUS_COLUMN, ""),
        (INITIAL_ENTRY_LABEL_RESOLUTION_SOURCE_COLUMN, ""),
        (INITIAL_ENTRY_LABEL_RESOLUTION_CONFIDENCE_COLUMN, 0.0),
        (INITIAL_ENTRY_LABEL_RESOLUTION_REASON_COLUMN, ""),
        (INITIAL_ENTRY_LABEL_RESOLUTION_PREVIOUS_ACTION_COLUMN, ""),
    ):
        if column not in resolved_dataset.columns:
            resolved_dataset[column] = default
    for column in (
        INITIAL_ENTRY_LABEL_RESOLUTION_STATUS_COLUMN,
        INITIAL_ENTRY_LABEL_RESOLUTION_SOURCE_COLUMN,
        INITIAL_ENTRY_LABEL_RESOLUTION_REASON_COLUMN,
        INITIAL_ENTRY_LABEL_RESOLUTION_PREVIOUS_ACTION_COLUMN,
    ):
        resolved_dataset[column] = resolved_dataset[column].astype("object")
    resolved_dataset[INITIAL_ENTRY_LABEL_RESOLUTION_CONFIDENCE_COLUMN] = pd.to_numeric(
        resolved_dataset[INITIAL_ENTRY_LABEL_RESOLUTION_CONFIDENCE_COLUMN],
        errors="coerce",
    ).fillna(0.0)
    for column in ("adapter_mode", "recommended_bias_action"):
        if column not in resolved_dataset.columns:
            resolved_dataset[column] = ""
        resolved_dataset[column] = resolved_dataset[column].astype("object")

    applied_rows: list[dict[str, Any]] = []
    missing_preview_row_count = 0

    if not draft_frame.empty:
        for proposal in draft_frame.to_dict(orient="records"):
            preview_row_id = str(proposal.get("preview_row_id", ""))
            if not preview_row_id:
                continue
            mask = resolved_dataset["preview_row_id"] == preview_row_id
            if not mask.any():
                missing_preview_row_count += 1
                continue

            current_row = resolved_dataset.loc[mask].iloc[0]
            previous_action_target = str(current_row.get("action_target", ""))
            current_weight = float(current_row.get("training_weight", 0.0) or 0.0)
            resolved_action_target = str(proposal.get("proposed_action_target", "") or previous_action_target)
            resolved_enter_now_binary = proposal.get("proposed_enter_now_binary")
            proposal_confidence = float(proposal.get("proposal_confidence", 0.0) or 0.0)
            resolution_reason = str(proposal.get("proposal_reason", ""))
            resolved_training_weight = max(current_weight, 1.0 if proposal_confidence >= 0.6 else 0.7)

            resolved_dataset.loc[mask, "action_target"] = resolved_action_target
            resolved_dataset.loc[mask, "enter_now_binary"] = resolved_enter_now_binary
            resolved_dataset.loc[mask, "training_weight"] = resolved_training_weight
            resolved_dataset.loc[mask, INITIAL_ENTRY_LABEL_RESOLUTION_STATUS_COLUMN] = "APPLIED_PROPOSED_DRAFT"
            resolved_dataset.loc[mask, INITIAL_ENTRY_LABEL_RESOLUTION_SOURCE_COLUMN] = INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_VERSION
            resolved_dataset.loc[mask, INITIAL_ENTRY_LABEL_RESOLUTION_CONFIDENCE_COLUMN] = proposal_confidence
            resolved_dataset.loc[mask, INITIAL_ENTRY_LABEL_RESOLUTION_REASON_COLUMN] = resolution_reason
            resolved_dataset.loc[mask, INITIAL_ENTRY_LABEL_RESOLUTION_PREVIOUS_ACTION_COLUMN] = previous_action_target
            if str(proposal.get("adapter_mode", "")).strip():
                resolved_dataset.loc[mask, "adapter_mode"] = str(proposal.get("adapter_mode", ""))
            if str(proposal.get("recommended_bias_action", "")).strip():
                resolved_dataset.loc[mask, "recommended_bias_action"] = str(proposal.get("recommended_bias_action", ""))

            applied_rows.append(
                {
                    "resolution_id": f"initial_entry_label_resolution_apply::{proposal.get('market_family', '')}::{preview_row_id}",
                    "market_family": str(proposal.get("market_family", "")).upper(),
                    "preview_row_id": preview_row_id,
                    "previous_action_target": previous_action_target,
                    "resolved_action_target": resolved_action_target,
                    "resolved_enter_now_binary": int(resolved_enter_now_binary) if pd.notna(resolved_enter_now_binary) else None,
                    "resolved_training_weight": round(resolved_training_weight, 6),
                    "proposal_confidence": round(proposal_confidence, 6),
                    "resolution_reason": resolution_reason,
                    "resolution_status": "APPLIED_PROPOSED_DRAFT",
                }
            )

    resolution_frame = pd.DataFrame(applied_rows, columns=INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_COLUMNS)
    summary = {
        "initial_entry_label_resolution_apply_version": INITIAL_ENTRY_LABEL_RESOLUTION_APPLY_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "applied_row_count": int(len(resolution_frame)),
        "market_family_counts": resolution_frame["market_family"].value_counts().to_dict() if not resolution_frame.empty else {},
        "missing_preview_row_count": int(missing_preview_row_count),
        "recommended_next_action": (
            "rebuild_symbol_surface_preview_eval_from_resolved_initial_entry"
            if not resolution_frame.empty
            else "await_initial_entry_label_resolution_draft"
        ),
    }
    return resolution_frame, resolved_dataset, summary


def render_initial_entry_label_resolution_apply_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Initial Entry Label Resolution Apply",
        "",
        f"- version: `{summary.get('initial_entry_label_resolution_apply_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- applied_row_count: `{summary.get('applied_row_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- missing_preview_row_count: `{summary.get('missing_preview_row_count', 0)}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
