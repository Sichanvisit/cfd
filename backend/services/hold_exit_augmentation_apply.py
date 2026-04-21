"""Apply continuation-hold and protective-exit augmentation drafts."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


HOLD_EXIT_AUGMENTATION_APPLY_VERSION = "hold_exit_augmentation_apply_v1"

HOLD_EXIT_AUGMENTATION_APPLY_COLUMNS = [
    "apply_id",
    "market_family",
    "target_surface",
    "target_binary",
    "source_row_id",
    "preview_row_id",
    "draft_reason",
    "draft_weight",
    "apply_status",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    if frame.empty:
        return frame
    for column in ("market_family", "target_surface", "source_row_id", "draft_reason", "time_axis_phase"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["target_surface"] = frame["target_surface"].fillna("").astype(str)
    frame["source_row_id"] = frame["source_row_id"].fillna("").astype(str)
    frame["draft_reason"] = frame["draft_reason"].fillna("").astype(str)
    frame["time_axis_phase"] = frame["time_axis_phase"].fillna("").astype(str)
    frame["target_binary"] = pd.to_numeric(frame.get("target_binary"), errors="coerce").fillna(0).astype(int)
    frame["draft_weight"] = pd.to_numeric(frame.get("draft_weight"), errors="coerce").fillna(0.45)
    return frame


def _normalize_dataset(frame: pd.DataFrame | None, defaults: Mapping[str, Any]) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    for column, default in defaults.items():
        if column not in dataset.columns:
            dataset[column] = default
    dataset["preview_row_id"] = dataset["preview_row_id"].fillna("").astype(str)
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["symbol"] = dataset["symbol"].fillna("").astype(str).str.upper()
    return dataset


def _stable_preview_row_id(prefix: str, market_family: str, source_row_id: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in str(source_row_id or ""))[:96].strip("_")
    return f"multi_surface_preview::{prefix}::{market_family.lower()}::{slug or 'unknown'}"


def _hold_defaults(dataset: pd.DataFrame, market_family: str) -> dict[str, Any]:
    slice_frame = dataset.loc[dataset["market_family"] == market_family] if not dataset.empty else pd.DataFrame()
    if slice_frame.empty:
        adapter_mode = "xau_runner_preservation_adapter" if market_family == "XAUUSD" else "runner_hold_balance_adapter"
        return {
            "symbol": market_family,
            "adapter_mode": adapter_mode,
            "recommended_bias_action": "bias_runner_hold",
            "objective_key": "runner_hold_ev",
        }
    row = slice_frame.iloc[0].to_dict()
    return {
        "symbol": str(row.get("symbol", market_family)).upper(),
        "adapter_mode": str(row.get("adapter_mode", "")),
        "recommended_bias_action": str(row.get("recommended_bias_action", "bias_runner_hold")),
        "objective_key": str(row.get("objective_key", "runner_hold_ev")),
    }


def _protect_defaults(dataset: pd.DataFrame, market_family: str) -> dict[str, Any]:
    slice_frame = dataset.loc[dataset["market_family"] == market_family] if not dataset.empty else pd.DataFrame()
    if slice_frame.empty:
        return {
            "symbol": market_family,
            "adapter_mode": "protective_exit_balance_adapter",
            "recommended_bias_action": "bias_protective_dampen",
            "objective_key": "protect_exit_loss_avoidance_ev",
        }
    row = slice_frame.iloc[0].to_dict()
    return {
        "symbol": str(row.get("symbol", market_family)).upper(),
        "adapter_mode": str(row.get("adapter_mode", "protective_exit_balance_adapter")),
        "recommended_bias_action": str(row.get("recommended_bias_action", "bias_protective_dampen")),
        "objective_key": str(row.get("objective_key", "protect_exit_loss_avoidance_ev")),
    }


def build_hold_exit_augmentation_apply(
    *,
    continuation_hold_dataset: pd.DataFrame | None,
    protective_exit_dataset: pd.DataFrame | None,
    hold_exit_augmentation_draft_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    hold_defaults = {
        "preview_row_id": "",
        "symbol": "",
        "market_family": "",
        "surface_state": "",
        "hold_target": "",
        "hold_runner_binary": 0,
        "failure_label": "",
        "training_weight": 0.0,
        "time_axis_phase": "",
        "time_since_entry_minutes": None,
        "bars_in_state": None,
        "momentum_decay": None,
        "adapter_mode": "",
        "recommended_bias_action": "",
        "objective_key": "",
    }
    protect_defaults = {
        "preview_row_id": "",
        "symbol": "",
        "market_family": "",
        "surface_state": "",
        "protect_target": "",
        "protect_exit_binary": 0,
        "failure_label": "",
        "training_weight": 0.0,
        "time_axis_phase": "",
        "time_since_entry_minutes": None,
        "bars_in_state": None,
        "momentum_decay": None,
        "adapter_mode": "",
        "recommended_bias_action": "",
        "objective_key": "",
    }
    hold_dataset = _normalize_dataset(continuation_hold_dataset, hold_defaults)
    protect_dataset = _normalize_dataset(protective_exit_dataset, protect_defaults)
    draft_frame = _to_frame(hold_exit_augmentation_draft_payload)

    augmented_hold = hold_dataset.copy()
    augmented_protect = protect_dataset.copy()
    for dataset in (augmented_hold, augmented_protect):
        for column, default in (
            ("augmentation_status", ""),
            ("augmentation_source", ""),
            ("augmentation_reason", ""),
            ("augmentation_source_row_id", ""),
        ):
            if column not in dataset.columns:
                dataset[column] = default

    if draft_frame.empty:
        empty = pd.DataFrame(columns=HOLD_EXIT_AUGMENTATION_APPLY_COLUMNS)
        return empty, augmented_hold, augmented_protect, {
            "hold_exit_augmentation_apply_version": HOLD_EXIT_AUGMENTATION_APPLY_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "applied_row_count": 0,
            "target_surface_counts": {},
            "recommended_next_action": "await_hold_exit_augmentation_draft",
        }

    existing_hold_source_ids = set(augmented_hold.get("augmentation_source_row_id", pd.Series(dtype=str)).fillna("").astype(str).tolist())
    existing_protect_source_ids = set(augmented_protect.get("augmentation_source_row_id", pd.Series(dtype=str)).fillna("").astype(str).tolist())
    applied_rows: list[dict[str, Any]] = []
    appended_hold: list[dict[str, Any]] = []
    appended_protect: list[dict[str, Any]] = []

    for draft in draft_frame.to_dict(orient="records"):
        market_family = str(draft.get("market_family", "")).upper()
        target_surface = str(draft.get("target_surface", ""))
        source_row_id = str(draft.get("source_row_id", ""))
        if not market_family or not source_row_id:
            continue
        target_binary = int(draft.get("target_binary", 0) or 0)
        draft_reason = str(draft.get("draft_reason", ""))
        draft_weight = float(draft.get("draft_weight", 0.45) or 0.45)
        time_axis_phase = str(draft.get("time_axis_phase", ""))

        if target_surface == "continuation_hold_surface":
            if source_row_id in existing_hold_source_ids:
                continue
            defaults = _hold_defaults(hold_dataset, market_family)
            preview_row_id = _stable_preview_row_id("continuation_hold_aug", market_family, source_row_id)
            appended_hold.append(
                {
                    "preview_row_id": preview_row_id,
                    "symbol": defaults["symbol"],
                    "market_family": market_family,
                    "surface_state": "runner_hold" if target_binary == 1 else "runner_release",
                    "hold_target": "HOLD_RUNNER" if target_binary == 1 else "NOT_HOLD_RUNNER",
                    "hold_runner_binary": target_binary,
                    "failure_label": draft_reason,
                    "training_weight": draft_weight,
                    "time_axis_phase": time_axis_phase,
                    "time_since_entry_minutes": None,
                    "bars_in_state": None,
                    "momentum_decay": None,
                    "adapter_mode": defaults["adapter_mode"],
                    "recommended_bias_action": defaults["recommended_bias_action"],
                    "objective_key": defaults["objective_key"],
                    "augmentation_status": "APPLIED_HOLD_EXIT_AUGMENTATION_DRAFT",
                    "augmentation_source": HOLD_EXIT_AUGMENTATION_APPLY_VERSION,
                    "augmentation_reason": draft_reason,
                    "augmentation_source_row_id": source_row_id,
                }
            )
            existing_hold_source_ids.add(source_row_id)
        elif target_surface == "protective_exit_surface":
            if source_row_id in existing_protect_source_ids:
                continue
            defaults = _protect_defaults(protect_dataset, market_family)
            preview_row_id = _stable_preview_row_id("protective_exit_aug", market_family, source_row_id)
            appended_protect.append(
                {
                    "preview_row_id": preview_row_id,
                    "symbol": defaults["symbol"],
                    "market_family": market_family,
                    "surface_state": "protect_exit",
                    "protect_target": "EXIT_PROTECT" if target_binary == 1 else "NOT_PROTECT_EXIT",
                    "protect_exit_binary": target_binary,
                    "failure_label": draft_reason,
                    "training_weight": draft_weight,
                    "time_axis_phase": time_axis_phase,
                    "time_since_entry_minutes": None,
                    "bars_in_state": None,
                    "momentum_decay": None,
                    "adapter_mode": defaults["adapter_mode"],
                    "recommended_bias_action": defaults["recommended_bias_action"],
                    "objective_key": defaults["objective_key"],
                    "augmentation_status": "APPLIED_HOLD_EXIT_AUGMENTATION_DRAFT",
                    "augmentation_source": HOLD_EXIT_AUGMENTATION_APPLY_VERSION,
                    "augmentation_reason": draft_reason,
                    "augmentation_source_row_id": source_row_id,
                }
            )
            existing_protect_source_ids.add(source_row_id)
        else:
            continue

        applied_rows.append(
            {
                "apply_id": f"hold_exit_augmentation_apply::{market_family}::{target_surface}::{source_row_id}",
                "market_family": market_family,
                "target_surface": target_surface,
                "target_binary": target_binary,
                "source_row_id": source_row_id,
                "preview_row_id": preview_row_id,
                "draft_reason": draft_reason,
                "draft_weight": round(draft_weight, 6),
                "apply_status": "APPLIED_HOLD_EXIT_AUGMENTATION_DRAFT",
            }
        )

    if appended_hold:
        augmented_hold = pd.concat([augmented_hold, pd.DataFrame(appended_hold)], ignore_index=True)
    if appended_protect:
        augmented_protect = pd.concat([augmented_protect, pd.DataFrame(appended_protect)], ignore_index=True)

    apply_frame = pd.DataFrame(applied_rows, columns=HOLD_EXIT_AUGMENTATION_APPLY_COLUMNS)
    summary = {
        "hold_exit_augmentation_apply_version": HOLD_EXIT_AUGMENTATION_APPLY_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "applied_row_count": int(len(apply_frame)),
        "target_surface_counts": apply_frame["target_surface"].value_counts().to_dict() if not apply_frame.empty else {},
        "recommended_next_action": (
            "rebuild_hold_exit_preview_eval_from_augmented_datasets"
            if not apply_frame.empty
            else "await_hold_exit_augmentation_draft"
        ),
    }
    return apply_frame, augmented_hold, augmented_protect, summary


def render_hold_exit_augmentation_apply_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Hold/Exit Augmentation Apply",
        "",
        f"- version: `{summary.get('hold_exit_augmentation_apply_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- applied_row_count: `{summary.get('applied_row_count', 0)}`",
        f"- target_surface_counts: `{summary.get('target_surface_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
