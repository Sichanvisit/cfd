"""Build continuation-hold and protective-exit augmentation drafts."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


HOLD_EXIT_AUGMENTATION_DRAFT_VERSION = "hold_exit_augmentation_draft_v1"

HOLD_EXIT_AUGMENTATION_DRAFT_COLUMNS = [
    "draft_id",
    "market_family",
    "target_surface",
    "target_binary",
    "source_row_id",
    "draft_source",
    "draft_reason",
    "draft_weight",
    "time_axis_phase",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _normalize_dataset(frame: pd.DataFrame | None, id_col: str) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    if id_col not in dataset.columns:
        dataset[id_col] = ""
    if "market_family" not in dataset.columns:
        dataset["market_family"] = ""
    if "time_axis_phase" not in dataset.columns:
        dataset["time_axis_phase"] = ""
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["time_axis_phase"] = dataset["time_axis_phase"].fillna("").astype(str)
    return dataset


def build_hold_exit_augmentation_draft(
    *,
    failure_label_harvest_payload: Mapping[str, Any] | None,
    continuation_hold_dataset: pd.DataFrame | None,
    protective_exit_dataset: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    failure_frame = _to_frame(failure_label_harvest_payload)
    hold_dataset = _normalize_dataset(continuation_hold_dataset, "preview_row_id")
    protect_dataset = _normalize_dataset(protective_exit_dataset, "preview_row_id")

    rows: list[dict[str, Any]] = []

    if not failure_frame.empty:
        early_exit = failure_frame.loc[failure_frame["failure_label"] == "early_exit_regret"].copy()
        for row in early_exit.to_dict(orient="records"):
            market_family = str(row.get("market_family", "")).upper()
            observation_id = str(row.get("observation_event_id", ""))
            phase = str(row.get("time_axis_phase", ""))
            rows.append(
                {
                    "draft_id": f"hold_exit_aug::{market_family}::continuation_hold::{observation_id}",
                    "market_family": market_family,
                    "target_surface": "continuation_hold_surface",
                    "target_binary": 1,
                    "source_row_id": observation_id,
                    "draft_source": "failure_label_harvest",
                    "draft_reason": "early_exit_regret_should_expand_runner_hold_positive",
                    "draft_weight": 1.0 if str(row.get("harvest_strength", "")) == "confirmed" else 0.45,
                    "time_axis_phase": phase,
                }
            )
            rows.append(
                {
                    "draft_id": f"hold_exit_aug::{market_family}::protective_exit::{observation_id}",
                    "market_family": market_family,
                    "target_surface": "protective_exit_surface",
                    "target_binary": 0,
                    "source_row_id": observation_id,
                    "draft_source": "failure_label_harvest",
                    "draft_reason": "early_exit_regret_should_add_false_cut_negative_contrast",
                    "draft_weight": 1.0 if str(row.get("harvest_strength", "")) == "confirmed" else 0.45,
                    "time_axis_phase": phase,
                }
            )

    if not protect_dataset.empty:
        late_protect = protect_dataset.loc[protect_dataset["time_axis_phase"].isin(["protect_late", "protect_active"])].copy()
        for row in late_protect.to_dict(orient="records"):
            market_family = str(row.get("market_family", "")).upper()
            preview_row_id = str(row.get("preview_row_id", ""))
            rows.append(
                {
                    "draft_id": f"hold_exit_aug::{market_family}::continuation_hold::{preview_row_id}",
                    "market_family": market_family,
                    "target_surface": "continuation_hold_surface",
                    "target_binary": 0,
                    "source_row_id": preview_row_id,
                    "draft_source": "protective_exit_dataset",
                    "draft_reason": "late_or_active_protect_exit_can_supply_not_hold_runner_contrast",
                    "draft_weight": 0.7,
                    "time_axis_phase": str(row.get("time_axis_phase", "")),
                }
            )

    frame = pd.DataFrame(rows, columns=HOLD_EXIT_AUGMENTATION_DRAFT_COLUMNS).drop_duplicates("draft_id", keep="first")
    summary = {
        "hold_exit_augmentation_draft_version": HOLD_EXIT_AUGMENTATION_DRAFT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "target_surface_counts": frame["target_surface"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "review_hold_exit_augmentation_draft"
            if not frame.empty
            else "await_hold_exit_augmentation_candidates"
        ),
    }
    return frame, summary


def render_hold_exit_augmentation_draft_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Hold/Exit Augmentation Draft",
        "",
        f"- version: `{summary.get('hold_exit_augmentation_draft_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- target_surface_counts: `{summary.get('target_surface_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
