"""Build label-resolution queue for unresolved initial-entry preview rows."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_VERSION = "initial_entry_label_resolution_queue_v1"

INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_COLUMNS = [
    "queue_id",
    "market_family",
    "surface_name",
    "preview_row_id",
    "surface_state",
    "action_target",
    "training_weight",
    "time_axis_phase",
    "adapter_mode",
    "recommended_bias_action",
    "resolution_reason",
    "resolution_question",
    "recommended_resolution_path",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _normalize_dataset(frame: pd.DataFrame | None) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    for column in (
        "preview_row_id",
        "market_family",
        "surface_state",
        "action_target",
        "time_axis_phase",
        "adapter_mode",
        "recommended_bias_action",
        "enter_now_binary",
        "training_weight",
    ):
        if column not in dataset.columns:
            dataset[column] = ""
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["preview_row_id"] = dataset["preview_row_id"].fillna("").astype(str)
    dataset["surface_state"] = dataset["surface_state"].fillna("").astype(str)
    dataset["action_target"] = dataset["action_target"].fillna("").astype(str)
    dataset["time_axis_phase"] = dataset["time_axis_phase"].fillna("").astype(str)
    dataset["adapter_mode"] = dataset["adapter_mode"].fillna("").astype(str)
    dataset["recommended_bias_action"] = dataset["recommended_bias_action"].fillna("").astype(str)
    dataset["enter_now_binary"] = pd.to_numeric(dataset["enter_now_binary"], errors="coerce")
    dataset["training_weight"] = pd.to_numeric(dataset["training_weight"], errors="coerce")
    return dataset


def build_initial_entry_label_resolution_queue(
    *,
    symbol_surface_preview_evaluation_payload: Mapping[str, Any] | None,
    initial_entry_dataset: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    eval_frame = _to_frame(symbol_surface_preview_evaluation_payload)
    dataset = _normalize_dataset(initial_entry_dataset)
    if eval_frame.empty or dataset.empty:
        empty = pd.DataFrame(columns=INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_COLUMNS)
        return empty, {
            "initial_entry_label_resolution_queue_version": INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "queue_row_count": 0,
            "market_family_counts": {},
            "recommended_next_action": "await_initial_entry_label_resolution_need",
        }

    needs_resolution = eval_frame.loc[
        (eval_frame["surface_name"] == "initial_entry_surface")
        & (eval_frame["readiness_state"] == "needs_label_resolution")
    ].copy()

    rows: list[dict[str, Any]] = []
    for family in needs_resolution["market_family"].dropna().astype(str).str.upper().tolist():
        eval_row = needs_resolution.loc[needs_resolution["market_family"] == family].iloc[0].to_dict()
        slice_df = dataset.loc[
            (dataset["market_family"] == family)
            & (dataset["enter_now_binary"].isna())
        ].copy()
        for row in slice_df.to_dict(orient="records"):
            action_target = str(row.get("action_target", ""))
            surface_state = str(row.get("surface_state", ""))
            resolution_reason = "unlabeled_probe_or_wait_row"
            if action_target == "PROBE_ENTRY":
                resolution_question = "이 row는 ENTER_NOW로 승격할 가치가 있었는가, 아니면 WAIT_MORE였는가"
                resolution_path = "resolve_probe_entry_vs_wait"
            else:
                resolution_question = "이 row는 WAIT_MORE가 맞는가, 아니면 missed enter candidate였는가"
                resolution_path = "resolve_wait_vs_missed_enter"
            rows.append(
                {
                    "queue_id": f"initial_entry_label_resolution::{family}::{row.get('preview_row_id', '')}",
                    "market_family": family,
                    "surface_name": "initial_entry_surface",
                    "preview_row_id": str(row.get("preview_row_id", "")),
                    "surface_state": surface_state,
                    "action_target": action_target,
                    "training_weight": float(row.get("training_weight", 0.0) or 0.0),
                    "time_axis_phase": str(row.get("time_axis_phase", "")),
                    "adapter_mode": str(eval_row.get("adapter_mode", row.get("adapter_mode", ""))),
                    "recommended_bias_action": str(
                        eval_row.get("recommended_bias_action", row.get("recommended_bias_action", ""))
                    ),
                    "resolution_reason": resolution_reason,
                    "resolution_question": resolution_question,
                    "recommended_resolution_path": resolution_path,
                }
            )

    frame = pd.DataFrame(rows, columns=INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_COLUMNS)
    summary = {
        "initial_entry_label_resolution_queue_version": INITIAL_ENTRY_LABEL_RESOLUTION_QUEUE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "queue_row_count": int(len(frame)),
        "market_family_counts": frame["market_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "manual_label_resolution_for_initial_entry"
            if not frame.empty
            else "await_initial_entry_label_resolution_need"
        ),
    }
    return frame, summary


def render_initial_entry_label_resolution_queue_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Initial Entry Label Resolution Queue",
        "",
        f"- version: `{summary.get('initial_entry_label_resolution_queue_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- queue_row_count: `{summary.get('queue_row_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
