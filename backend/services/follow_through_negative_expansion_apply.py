"""Apply reviewed follow-through negative expansion drafts into an augmented dataset."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_VERSION = "follow_through_negative_expansion_apply_v1"

FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_COLUMNS = [
    "apply_id",
    "market_family",
    "source_observation_id",
    "preview_row_id",
    "continuation_target",
    "continuation_positive_binary",
    "applied_training_weight",
    "draft_reason",
    "apply_status",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    if frame.empty:
        return frame
    for column in ("market_family", "source_observation_id", "draft_reason", "time_axis_phase"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["source_observation_id"] = frame["source_observation_id"].fillna("").astype(str)
    frame["draft_reason"] = frame["draft_reason"].fillna("").astype(str)
    frame["time_axis_phase"] = frame["time_axis_phase"].fillna("").astype(str)
    frame["continuation_positive_binary"] = pd.to_numeric(frame.get("continuation_positive_binary"), errors="coerce")
    frame["draft_weight"] = pd.to_numeric(frame.get("draft_weight"), errors="coerce").fillna(0.45)
    return frame


def _normalize_dataset(frame: pd.DataFrame | None) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    defaults = {
        "preview_row_id": "",
        "symbol": "",
        "market_family": "",
        "surface_state": "",
        "continuation_target": "",
        "continuation_positive_binary": 0,
        "failure_label": "",
        "training_weight": 0.0,
        "time_axis_phase": "",
        "time_since_breakout_minutes": None,
        "bars_in_state": None,
        "momentum_decay": None,
        "adapter_mode": "",
        "recommended_bias_action": "",
        "objective_key": "",
    }
    for column, default in defaults.items():
        if column not in dataset.columns:
            dataset[column] = default
    dataset["preview_row_id"] = dataset["preview_row_id"].fillna("").astype(str)
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["symbol"] = dataset["symbol"].fillna("").astype(str).str.upper()
    return dataset


def _stable_preview_row_id(market_family: str, source_observation_id: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in str(source_observation_id or ""))[:96].strip("_")
    return f"multi_surface_preview::follow_through_aug::{market_family.lower()}::{slug or 'unknown'}"


def _market_defaults(dataset: pd.DataFrame, market_family: str) -> dict[str, Any]:
    slice_frame = dataset.loc[dataset["market_family"] == market_family] if not dataset.empty else pd.DataFrame()
    if slice_frame.empty:
        return {
            "symbol": market_family,
            "adapter_mode": "",
            "recommended_bias_action": "bias_neutral",
            "objective_key": "follow_through_extension_ev",
        }
    row = slice_frame.iloc[0].to_dict()
    return {
        "symbol": str(row.get("symbol", market_family)).upper(),
        "adapter_mode": str(row.get("adapter_mode", "")),
        "recommended_bias_action": str(row.get("recommended_bias_action", "bias_neutral")),
        "objective_key": str(row.get("objective_key", "follow_through_extension_ev")),
    }


def build_follow_through_negative_expansion_apply(
    *,
    follow_through_dataset: pd.DataFrame | None,
    follow_through_negative_expansion_draft_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    dataset = _normalize_dataset(follow_through_dataset)
    draft_frame = _to_frame(follow_through_negative_expansion_draft_payload)

    augmented = dataset.copy()
    for column, default in (
        ("augmentation_status", ""),
        ("augmentation_source", ""),
        ("augmentation_reason", ""),
        ("augmentation_source_observation_id", ""),
        ("augmentation_source_strength", ""),
    ):
        if column not in augmented.columns:
            augmented[column] = default

    if draft_frame.empty:
        empty = pd.DataFrame(columns=FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_COLUMNS)
        return empty, augmented, {
            "follow_through_negative_expansion_apply_version": FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "applied_row_count": 0,
            "market_family_counts": {},
            "recommended_next_action": "await_follow_through_negative_expansion_draft",
        }

    existing_source_ids = set(augmented.get("augmentation_source_observation_id", pd.Series(dtype=str)).fillna("").astype(str).tolist())
    applied_rows: list[dict[str, Any]] = []
    appended_rows: list[dict[str, Any]] = []
    for draft in draft_frame.to_dict(orient="records"):
        market_family = str(draft.get("market_family", "")).upper()
        source_observation_id = str(draft.get("source_observation_id", ""))
        if not market_family or not source_observation_id or source_observation_id in existing_source_ids:
            continue
        defaults = _market_defaults(dataset, market_family)
        preview_row_id = _stable_preview_row_id(market_family, source_observation_id)
        appended_rows.append(
            {
                "preview_row_id": preview_row_id,
                "symbol": defaults["symbol"],
                "market_family": market_family,
                "surface_state": str(draft.get("surface_state", "")),
                "continuation_target": str(draft.get("continuation_target", "NOT_CONTINUE") or "NOT_CONTINUE"),
                "continuation_positive_binary": int(draft.get("continuation_positive_binary", 0) or 0),
                "failure_label": str(draft.get("draft_reason", "")),
                "training_weight": float(draft.get("draft_weight", 0.45) or 0.45),
                "time_axis_phase": str(draft.get("time_axis_phase", "")),
                "time_since_breakout_minutes": None,
                "bars_in_state": None,
                "momentum_decay": None,
                "adapter_mode": defaults["adapter_mode"],
                "recommended_bias_action": defaults["recommended_bias_action"],
                "objective_key": defaults["objective_key"],
                "augmentation_status": "APPLIED_NEGATIVE_EXPANSION_DRAFT",
                "augmentation_source": FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_VERSION,
                "augmentation_reason": str(draft.get("draft_reason", "")),
                "augmentation_source_observation_id": source_observation_id,
                "augmentation_source_strength": str(draft.get("draft_source_strength", "")),
            }
        )
        applied_rows.append(
            {
                "apply_id": f"follow_through_negative_apply::{market_family}::{source_observation_id}",
                "market_family": market_family,
                "source_observation_id": source_observation_id,
                "preview_row_id": preview_row_id,
                "continuation_target": str(draft.get("continuation_target", "NOT_CONTINUE") or "NOT_CONTINUE"),
                "continuation_positive_binary": int(draft.get("continuation_positive_binary", 0) or 0),
                "applied_training_weight": round(float(draft.get("draft_weight", 0.45) or 0.45), 6),
                "draft_reason": str(draft.get("draft_reason", "")),
                "apply_status": "APPLIED_NEGATIVE_EXPANSION_DRAFT",
            }
        )
        existing_source_ids.add(source_observation_id)

    if appended_rows:
        augmented = pd.concat([augmented, pd.DataFrame(appended_rows)], ignore_index=True)

    apply_frame = pd.DataFrame(applied_rows, columns=FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_COLUMNS)
    summary = {
        "follow_through_negative_expansion_apply_version": FOLLOW_THROUGH_NEGATIVE_EXPANSION_APPLY_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "applied_row_count": int(len(apply_frame)),
        "market_family_counts": apply_frame["market_family"].value_counts().to_dict() if not apply_frame.empty else {},
        "recommended_next_action": (
            "rebuild_follow_through_preview_eval_from_augmented_dataset"
            if not apply_frame.empty
            else "await_follow_through_negative_expansion_draft"
        ),
    }
    return apply_frame, augmented, summary


def render_follow_through_negative_expansion_apply_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Follow-Through Negative Expansion Apply",
        "",
        f"- version: `{summary.get('follow_through_negative_expansion_apply_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- applied_row_count: `{summary.get('applied_row_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
