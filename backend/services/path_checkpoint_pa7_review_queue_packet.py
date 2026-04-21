from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def default_checkpoint_pa7_review_queue_packet_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa7_review_queue_packet_latest.json"
    )


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def build_checkpoint_pa7_review_queue_packet(
    resolved: pd.DataFrame,
    *,
    top_n_groups: int = 12,
    sample_rows_per_group: int = 3,
) -> dict[str, Any]:
    frame = resolved.copy() if isinstance(resolved, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        return {
            "summary": {
                "contract_version": "checkpoint_pa7_review_queue_packet_v1",
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": 0,
                "manual_exception_row_count": 0,
                "review_group_count": 0,
                "recommended_next_action": "collect_checkpoint_rows_before_pa7_review",
            },
            "group_rows": [],
        }

    frame["hindsight_quality_tier"] = frame.get("hindsight_quality_tier", "").fillna("").astype(str)
    frame["hindsight_manual_exception_required"] = frame.get(
        "hindsight_manual_exception_required", False
    ).apply(_to_bool)

    manual_mask = (
        frame["hindsight_quality_tier"].eq("manual_exception")
        | frame["hindsight_manual_exception_required"]
    )
    manual = frame.loc[manual_mask].copy()
    if manual.empty:
        return {
            "summary": {
                "contract_version": "checkpoint_pa7_review_queue_packet_v1",
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": int(len(frame)),
                "manual_exception_row_count": 0,
                "review_group_count": 0,
                "recommended_next_action": "manual_exception_queue_empty",
            },
            "group_rows": [],
        }

    for column in (
        "symbol",
        "surface_name",
        "checkpoint_type",
        "management_row_family",
        "checkpoint_rule_family_hint",
        "hindsight_best_management_action_label",
        "management_action_label",
        "scene_candidate_selected_label",
    ):
        if column not in manual.columns:
            manual[column] = ""
        manual[column] = manual[column].fillna("").astype(str)

    for column in (
        "runtime_hindsight_match",
        "runtime_hold_quality_score",
        "runtime_partial_exit_ev",
        "runtime_full_exit_risk",
        "scene_candidate_selected_confidence",
        "current_profit",
        "giveback_ratio",
    ):
        if column not in manual.columns:
            manual[column] = 0.0

    group_columns = [
        "symbol",
        "surface_name",
        "checkpoint_type",
        "management_row_family",
        "checkpoint_rule_family_hint",
        "hindsight_best_management_action_label",
        "management_action_label",
    ]

    grouped = (
        manual.groupby(group_columns, dropna=False)
        .agg(
            row_count=("symbol", "size"),
            avg_runtime_proxy_match=("runtime_hindsight_match", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
            avg_hold_quality=("runtime_hold_quality_score", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
            avg_partial_exit_ev=("runtime_partial_exit_ev", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
            avg_full_exit_risk=("runtime_full_exit_risk", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
            avg_scene_confidence=("scene_candidate_selected_confidence", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
        )
        .reset_index()
        .sort_values(["row_count", "avg_scene_confidence"], ascending=[False, False])
    )

    top_groups = grouped.head(int(max(1, top_n_groups))).to_dict(orient="records")
    group_rows: list[dict[str, Any]] = []

    for group in top_groups:
        mask = pd.Series(True, index=manual.index)
        for column in group_columns:
            mask &= manual[column].eq(_to_text(group.get(column)))
        group_frame = manual.loc[mask].copy().head(int(max(1, sample_rows_per_group)))
        samples: list[dict[str, Any]] = []
        for _, row in group_frame.iterrows():
            samples.append(
                {
                    "generated_at": _to_text(row.get("generated_at")),
                    "source": _to_text(row.get("source")),
                    "symbol": _to_text(row.get("symbol")),
                    "surface_name": _to_text(row.get("surface_name")),
                    "checkpoint_id": _to_text(row.get("checkpoint_id")),
                    "checkpoint_type": _to_text(row.get("checkpoint_type")),
                    "management_row_family": _to_text(row.get("management_row_family")),
                    "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")),
                    "baseline_action_label": _to_text(row.get("management_action_label")),
                    "hindsight_best_management_action_label": _to_text(row.get("hindsight_best_management_action_label")),
                    "runtime_proxy_management_action_label": _to_text(row.get("runtime_proxy_management_action_label")),
                    "scene_candidate_selected_label": _to_text(row.get("scene_candidate_selected_label")),
                    "scene_candidate_selected_confidence": round(
                        _to_float(row.get("scene_candidate_selected_confidence")), 6
                    ),
                    "runtime_hold_quality_score": round(_to_float(row.get("runtime_hold_quality_score")), 6),
                    "runtime_partial_exit_ev": round(_to_float(row.get("runtime_partial_exit_ev")), 6),
                    "runtime_full_exit_risk": round(_to_float(row.get("runtime_full_exit_risk")), 6),
                    "current_profit": round(_to_float(row.get("current_profit")), 6),
                    "giveback_ratio": round(_to_float(row.get("giveback_ratio")), 6),
                    "hindsight_label_reason": _to_text(row.get("hindsight_label_reason")),
                    "hindsight_scene_reason": _to_text(row.get("hindsight_scene_reason")),
                }
            )
        group_rows.append(
            {
                **{column: _to_text(group.get(column)) for column in group_columns},
                "row_count": int(group.get("row_count", 0) or 0),
                "avg_runtime_proxy_match": round(_to_float(group.get("avg_runtime_proxy_match")), 6),
                "avg_hold_quality": round(_to_float(group.get("avg_hold_quality")), 6),
                "avg_partial_exit_ev": round(_to_float(group.get("avg_partial_exit_ev")), 6),
                "avg_full_exit_risk": round(_to_float(group.get("avg_full_exit_risk")), 6),
                "avg_scene_confidence": round(_to_float(group.get("avg_scene_confidence")), 6),
                "samples": samples,
            }
        )

    summary = {
        "contract_version": "checkpoint_pa7_review_queue_packet_v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "resolved_row_count": int(len(frame)),
        "manual_exception_row_count": int(len(manual)),
        "review_group_count": int(len(group_rows)),
        "top_symbols": (
            manual["symbol"].value_counts().head(5).astype(int).to_dict()
            if "symbol" in manual.columns
            else {}
        ),
        "top_hindsight_labels": (
            manual["hindsight_best_management_action_label"].value_counts().head(5).astype(int).to_dict()
            if "hindsight_best_management_action_label" in manual.columns
            else {}
        ),
        "recommended_next_action": "review_top_manual_exception_groups_for_pa7",
    }
    return {"summary": summary, "group_rows": group_rows}
