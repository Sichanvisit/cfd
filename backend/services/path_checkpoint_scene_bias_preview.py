"""Trend-exhaustion scene bias preview helpers for SA6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_scene_runtime_bridge import (
    build_checkpoint_scene_log_only_bridge_v1,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_VERSION = "checkpoint_scene_bias_preview_v1"
PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_COLUMNS = [
    "symbol",
    "checkpoint_id",
    "surface_name",
    "checkpoint_type",
    "baseline_action_label",
    "preview_action_label",
    "preview_changed",
    "scene_candidate_selected_confidence",
    "preview_reason",
    "hindsight_best_management_action_label",
    "baseline_hindsight_match",
    "preview_hindsight_match",
]
_TREND_EXHAUSTION_LATE_TYPES = {"RUNNER_CHECK", "LATE_TREND_CHECK"}
_TRIM_OR_EXIT_ACTIONS = {"FULL_EXIT", "PARTIAL_EXIT", "PARTIAL_THEN_HOLD"}


def default_checkpoint_trend_exhaustion_scene_bias_preview_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_trend_exhaustion_scene_bias_preview_latest.json"
    )


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _eligible_trend_exhaustion_bias(
    row: dict[str, Any],
    bridge_row: dict[str, Any],
    *,
    confidence_threshold: float,
) -> tuple[bool, str]:
    selected_label = _to_text(bridge_row.get("scene_candidate_selected_label"))
    selected_confidence = _to_float(bridge_row.get("scene_candidate_selected_confidence"), 0.0)
    surface_name = _to_text(row.get("surface_name"))
    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    position_side = _to_text(row.get("position_side")).upper()
    if selected_label != "trend_exhaustion":
        return False, "scene_not_trend_exhaustion"
    if selected_confidence < confidence_threshold:
        return False, "trend_exhaustion_confidence_too_low"
    if surface_name != "continuation_hold_surface":
        return False, "trend_exhaustion_surface_out_of_scope"
    if checkpoint_type not in _TREND_EXHAUSTION_LATE_TYPES:
        return False, "trend_exhaustion_checkpoint_out_of_scope"
    if position_side == "FLAT":
        return False, "trend_exhaustion_flat_position"
    return True, "trend_exhaustion_preview_candidate"


def _resolve_baseline_action(row: dict[str, Any]) -> str:
    return (
        _to_text(row.get("management_action_label")).upper()
        or _to_text(row.get("runtime_proxy_management_action_label"), "WAIT").upper()
    )


def _preview_trend_exhaustion_action(row: dict[str, Any], baseline_action: str) -> tuple[str, str]:
    if baseline_action in _TRIM_OR_EXIT_ACTIONS:
        return baseline_action, "baseline_already_trim_or_exit"

    current_profit = _to_float(row.get("current_profit"), 0.0)
    partial_exit_ev = _to_float(row.get("runtime_partial_exit_ev"), 0.0)
    hold_quality = _to_float(row.get("runtime_hold_quality_score"), 0.0)
    giveback_ratio = _to_float(row.get("giveback_ratio"), 0.0)
    unrealized = _to_text(row.get("unrealized_pnl_state")).upper()
    runner_secured = _to_bool(row.get("runner_secured"), False)
    position_side = _to_text(row.get("position_side")).upper()
    row_family = _to_text(row.get("checkpoint_rule_family_hint")).lower()
    exit_stage_family = _to_text(row.get("exit_stage_family")).lower()

    if baseline_action == "HOLD":
        if (row_family == "runner_secured_continuation" or exit_stage_family == "runner" or runner_secured) and giveback_ratio < 0.20:
            return baseline_action, "trend_exhaustion_preview_runner_keep"
        if giveback_ratio >= 0.28 and partial_exit_ev >= 0.46:
            return "PARTIAL_EXIT", "trend_exhaustion_preview_giveback_trim"
        if (
            (unrealized == "OPEN_PROFIT" or current_profit >= 0.04)
            and partial_exit_ev >= hold_quality + 0.05
            and (
                exit_stage_family == "protective"
                or hold_quality <= 0.50
                or giveback_ratio >= 0.18
            )
        ):
            return "PARTIAL_THEN_HOLD", "trend_exhaustion_preview_trim_runner"
        return baseline_action, "trend_exhaustion_preview_hold_no_trim_signal"

    if baseline_action == "WAIT" and position_side != "FLAT":
        if (unrealized == "OPEN_PROFIT" and giveback_ratio >= 0.10) or partial_exit_ev >= 0.50:
            return "PARTIAL_THEN_HOLD", "trend_exhaustion_preview_wait_to_trim"
        return baseline_action, "trend_exhaustion_preview_wait_keep"

    return baseline_action, "trend_exhaustion_preview_no_change"


def build_trend_exhaustion_scene_bias_preview(
    resolved_dataset: pd.DataFrame | None,
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
    confidence_threshold: float = 0.75,
    symbols: tuple[str, ...] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "resolved_row_count": 0,
        "eligible_row_count": 0,
        "preview_changed_row_count": 0,
        "changed_action_counts": {},
        "baseline_hindsight_match_rate": 0.0,
        "preview_hindsight_match_rate": 0.0,
        "improved_row_count": 0,
        "worsened_row_count": 0,
        "unchanged_row_count": 0,
        "top_changed_slices": [],
        "casebook_examples": [],
        "recommended_next_action": "collect_more_trend_exhaustion_preview_rows_before_sa6",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_COLUMNS), summary

    for column in (
        "symbol",
        "surface_name",
        "checkpoint_type",
        "position_side",
        "management_action_label",
        "runtime_proxy_management_action_label",
        "hindsight_best_management_action_label",
        "runtime_partial_exit_ev",
        "runtime_hold_quality_score",
        "current_profit",
        "giveback_ratio",
        "unrealized_pnl_state",
        "runner_secured",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    summary["resolved_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_COLUMNS), summary

    preview_rows: list[dict[str, Any]] = []
    for row in scoped.to_dict(orient="records"):
        bridge_row = build_checkpoint_scene_log_only_bridge_v1(
            row,
            active_state_path=active_state_path,
            latest_run_path=latest_run_path,
        )["row"]
        eligible, eligibility_reason = _eligible_trend_exhaustion_bias(
            row,
            bridge_row,
            confidence_threshold=confidence_threshold,
        )
        if not eligible:
            continue
        baseline_action = _resolve_baseline_action(row)
        preview_action, preview_reason = _preview_trend_exhaustion_action(row, baseline_action)
        hindsight_action = _to_text(row.get("hindsight_best_management_action_label")).upper()
        baseline_match = bool(baseline_action and hindsight_action and baseline_action == hindsight_action)
        preview_match = bool(preview_action and hindsight_action and preview_action == hindsight_action)
        preview_rows.append(
            {
                "symbol": _to_text(row.get("symbol")).upper(),
                "checkpoint_id": _to_text(row.get("checkpoint_id")),
                "surface_name": _to_text(row.get("surface_name")),
                "checkpoint_type": _to_text(row.get("checkpoint_type")).upper(),
                "baseline_action_label": baseline_action,
                "preview_action_label": preview_action,
                "preview_changed": bool(preview_action != baseline_action),
                "scene_candidate_selected_confidence": round(
                    _to_float(bridge_row.get("scene_candidate_selected_confidence"), 0.0), 6
                ),
                "preview_reason": f"{eligibility_reason}|{preview_reason}",
                "hindsight_best_management_action_label": hindsight_action,
                "baseline_hindsight_match": baseline_match,
                "preview_hindsight_match": preview_match,
                "current_profit": round(_to_float(row.get("current_profit"), 0.0), 6),
                "giveback_ratio": round(_to_float(row.get("giveback_ratio"), 0.0), 6),
                "runtime_partial_exit_ev": round(_to_float(row.get("runtime_partial_exit_ev"), 0.0), 6),
                "runtime_hold_quality_score": round(_to_float(row.get("runtime_hold_quality_score"), 0.0), 6),
                "checkpoint_rule_family_hint": _to_text(row.get("checkpoint_rule_family_hint")).lower(),
                "exit_stage_family": _to_text(row.get("exit_stage_family")).lower(),
            }
        )

    preview_frame = pd.DataFrame(preview_rows)
    if preview_frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_COLUMNS), summary

    summary["eligible_row_count"] = int(len(preview_frame))
    summary["preview_changed_row_count"] = int(preview_frame["preview_changed"].sum())
    summary["changed_action_counts"] = (
        preview_frame.loc[preview_frame["preview_changed"]]
        .assign(change_key=lambda f: f["baseline_action_label"] + "->" + f["preview_action_label"])
        ["change_key"]
        .value_counts()
        .to_dict()
    )
    summary["baseline_hindsight_match_rate"] = _safe_rate(
        int(preview_frame["baseline_hindsight_match"].sum()),
        int(len(preview_frame)),
    )
    summary["preview_hindsight_match_rate"] = _safe_rate(
        int(preview_frame["preview_hindsight_match"].sum()),
        int(len(preview_frame)),
    )
    improved = int(((preview_frame["preview_hindsight_match"]) & (~preview_frame["baseline_hindsight_match"])).sum())
    worsened = int(((~preview_frame["preview_hindsight_match"]) & (preview_frame["baseline_hindsight_match"])).sum())
    unchanged = int(len(preview_frame) - improved - worsened)
    summary["improved_row_count"] = improved
    summary["worsened_row_count"] = worsened
    summary["unchanged_row_count"] = unchanged
    top_slices = (
        preview_frame.loc[preview_frame["preview_changed"]]
        .groupby(["symbol", "checkpoint_type", "preview_action_label"])
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    summary["top_changed_slices"] = [
        {
            "symbol": str(symbol),
            "checkpoint_type": str(checkpoint_type),
            "preview_action_label": str(preview_action_label),
            "count": int(count),
        }
        for (symbol, checkpoint_type, preview_action_label), count in top_slices.items()
    ]
    casebook = (
        preview_frame.loc[preview_frame["preview_changed"]]
        .sort_values(
            by=["scene_candidate_selected_confidence", "symbol", "checkpoint_id"],
            ascending=[False, True, True],
        )
        .head(20)
    )
    summary["casebook_examples"] = casebook.to_dict(orient="records")

    if summary["eligible_row_count"] >= 50 and summary["preview_hindsight_match_rate"] >= summary["baseline_hindsight_match_rate"] + 0.05:
        summary["recommended_next_action"] = "review_trend_exhaustion_scene_bias_for_sa6_bounded_integration"
    else:
        summary["recommended_next_action"] = "keep_trend_exhaustion_scene_bias_preview_only"

    return preview_frame.loc[:, PATH_CHECKPOINT_SCENE_BIAS_PREVIEW_COLUMNS], summary
