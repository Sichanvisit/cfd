"""Evaluate multi-surface preview datasets by symbol and surface."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SYMBOL_SURFACE_PREVIEW_EVALUATION_VERSION = "symbol_surface_preview_evaluation_v1"

SYMBOL_SURFACE_PREVIEW_EVALUATION_COLUMNS = [
    "evaluation_id",
    "market_family",
    "surface_name",
    "dataset_name",
    "adapter_mode",
    "recommended_bias_action",
    "objective_key",
    "current_focus",
    "row_count",
    "positive_count",
    "negative_count",
    "unlabeled_count",
    "positive_rate",
    "avg_training_weight",
    "unlabeled_ratio",
    "strong_row_count",
    "strong_row_ratio",
    "time_axis_phase_count",
    "underfire_count",
    "overfire_count",
    "probe_eligible_count",
    "failed_follow_through_count",
    "early_exit_regret_count",
    "false_breakout_count",
    "missed_good_wait_release_count",
    "late_entry_chase_fail_count",
    "harvest_failed_follow_through_count",
    "harvest_early_exit_regret_count",
    "harvest_false_breakout_count",
    "harvest_missed_good_wait_release_count",
    "harvest_late_entry_chase_fail_count",
    "readiness_state",
    "recommended_action",
]

SURFACE_DATASET_CONFIG = {
    "initial_entry_surface": {"dataset_name": "initial_entry", "target_column": "enter_now_binary", "min_rows": 10, "needs_dual_class": True},
    "follow_through_surface": {"dataset_name": "follow_through", "target_column": "continuation_positive_binary", "min_rows": 12, "needs_dual_class": True},
    "continuation_hold_surface": {"dataset_name": "continuation_hold", "target_column": "hold_runner_binary", "min_rows": 8, "needs_dual_class": True},
    "protective_exit_surface": {"dataset_name": "protective_exit", "target_column": "protect_exit_binary", "min_rows": 8, "needs_dual_class": True},
}


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _json_rows(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    return list((payload or {}).get("rows", []) or [])


def _failure_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(_json_rows(payload))
    if frame.empty:
        return frame
    for column in ("market_family", "surface_label_family", "failure_label"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["surface_label_family"] = frame["surface_label_family"].fillna("").astype(str)
    frame["failure_label"] = frame["failure_label"].fillna("").astype(str)
    return frame


def _distribution_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(_json_rows(payload))
    if frame.empty:
        return frame
    for column in ("market_family", "surface_family", "promotion_gap_note", "combined_gate_state"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["surface_family"] = frame["surface_family"].fillna("").astype(str)
    frame["promotion_gap_note"] = frame["promotion_gap_note"].fillna("").astype(str)
    frame["combined_gate_state"] = frame["combined_gate_state"].fillna("").astype(str)
    return frame


def _adapter_lookup(payload: Mapping[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _json_rows(payload):
        market_family = _to_text(row.get("market_family")).upper()
        surface_name = _to_text(row.get("surface_name"))
        if market_family and surface_name:
            lookup[(market_family, surface_name)] = dict(row)
    return lookup


def _normalize_dataset(frame: pd.DataFrame | None) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    for column in ("symbol", "market_family", "surface_state", "training_weight", "time_axis_phase"):
        if column not in dataset.columns:
            dataset[column] = ""
    dataset["symbol"] = dataset["symbol"].fillna("").astype(str).str.upper()
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["surface_state"] = dataset["surface_state"].fillna("").astype(str)
    dataset["time_axis_phase"] = dataset["time_axis_phase"].fillna("").astype(str)
    dataset["training_weight"] = pd.to_numeric(dataset["training_weight"], errors="coerce")
    return dataset


def _count_failure(frame: pd.DataFrame, failure_label: str) -> int:
    if frame.empty or "failure_label" not in frame.columns:
        return 0
    return int(frame.loc[frame["failure_label"] == failure_label].shape[0])


def _readiness_state(
    *,
    row_count: int,
    positive_count: int,
    negative_count: int,
    min_rows: int,
    needs_dual_class: bool,
    unlabeled_ratio: float,
    strong_row_count: int,
) -> str:
    if row_count < min_rows:
        return "insufficient_rows"
    if unlabeled_ratio > 0.10:
        return "needs_label_resolution"
    if needs_dual_class and (positive_count == 0 or negative_count == 0):
        return "single_class_only"
    if strong_row_count < max(3, min_rows // 3):
        return "weak_supervision_only"
    return "preview_eval_ready"


def _recommended_action(
    *,
    surface_name: str,
    readiness_state: str,
    failed_follow_through_count: int,
    early_exit_regret_count: int,
    false_breakout_count: int,
    missed_good_wait_release_count: int,
) -> str:
    if readiness_state == "insufficient_rows":
        if surface_name == "continuation_hold_surface":
            return "harvest_more_runner_preservation_rows"
        return "collect_more_symbol_surface_rows"
    if readiness_state == "needs_label_resolution":
        return "resolve_probe_and_wait_labels"
    if readiness_state == "single_class_only":
        if surface_name == "follow_through_surface":
            return "collect_negative_follow_through_rows"
        if surface_name == "protective_exit_surface":
            return "collect_false_cut_negative_rows"
        if surface_name == "continuation_hold_surface":
            return "collect_lock_profit_contrast_rows"
        return "collect_counter_class_rows"
    if failed_follow_through_count > 0:
        return "inspect_follow_through_miss_precision"
    if early_exit_regret_count > 0:
        return "inspect_runner_preservation_precision"
    if false_breakout_count > 0 or missed_good_wait_release_count > 0:
        return "inspect_initial_entry_release_precision"
    return "ready_for_preview_evaluation"


def build_symbol_surface_preview_evaluation(
    *,
    initial_entry_dataset: pd.DataFrame | None,
    follow_through_dataset: pd.DataFrame | None,
    continuation_hold_dataset: pd.DataFrame | None,
    protective_exit_dataset: pd.DataFrame | None,
    failure_label_harvest_payload: Mapping[str, Any] | None,
    distribution_promotion_gate_payload: Mapping[str, Any] | None,
    market_adapter_layer_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    datasets = {
        "initial_entry": _normalize_dataset(initial_entry_dataset),
        "follow_through": _normalize_dataset(follow_through_dataset),
        "continuation_hold": _normalize_dataset(continuation_hold_dataset),
        "protective_exit": _normalize_dataset(protective_exit_dataset),
    }
    failure_frame = _failure_frame(failure_label_harvest_payload)
    distribution_frame = _distribution_frame(distribution_promotion_gate_payload)
    adapter_lookup = _adapter_lookup(market_adapter_layer_payload)

    families: set[str] = set()
    for dataset in datasets.values():
        if not dataset.empty:
            families.update(dataset["market_family"].dropna().astype(str).str.upper().tolist())
    families.update(key[0] for key in adapter_lookup.keys())
    families = {family for family in families if family}

    rows: list[dict[str, Any]] = []
    for market_family in sorted(families):
        for surface_name, config in SURFACE_DATASET_CONFIG.items():
            dataset_name = str(config["dataset_name"])
            target_column = str(config["target_column"])
            dataset = datasets[dataset_name]
            symbol_slice = dataset.loc[dataset["market_family"] == market_family].copy() if not dataset.empty else pd.DataFrame()
            target_series = pd.to_numeric(symbol_slice[target_column], errors="coerce") if (not symbol_slice.empty and target_column in symbol_slice.columns) else pd.Series(dtype=float)
            positive_count = int((target_series == 1).sum()) if not target_series.empty else 0
            negative_count = int((target_series == 0).sum()) if not target_series.empty else 0
            unlabeled_count = int(target_series.isna().sum()) if not target_series.empty else int(len(symbol_slice))
            row_count = int(len(symbol_slice))
            positive_rate = round(float(positive_count / max(1, positive_count + negative_count)), 6) if (positive_count + negative_count) else 0.0
            avg_training_weight = round(float(symbol_slice["training_weight"].mean()), 6) if row_count else 0.0
            unlabeled_ratio = round(float(unlabeled_count / max(1, row_count)), 6) if row_count else 0.0
            strong_row_count = int((pd.to_numeric(symbol_slice["training_weight"], errors="coerce") >= 1.0).sum()) if row_count else 0
            strong_row_ratio = round(float(strong_row_count / max(1, row_count)), 6) if row_count else 0.0
            phase_count = int(symbol_slice["time_axis_phase"].replace("", pd.NA).dropna().nunique()) if row_count else 0

            failure_slice = failure_frame.loc[(failure_frame["market_family"] == market_family) & (failure_frame["surface_label_family"] == surface_name)].copy() if not failure_frame.empty else pd.DataFrame()
            distribution_slice = distribution_frame.loc[(distribution_frame["market_family"] == market_family) & (distribution_frame["surface_family"] == surface_name)].copy() if not distribution_frame.empty else pd.DataFrame()
            adapter_row = adapter_lookup.get((market_family, surface_name), {})

            local_failed_follow_through_count = _count_failure(symbol_slice, "failed_follow_through")
            local_early_exit_regret_count = _count_failure(symbol_slice, "early_exit_regret")
            local_false_breakout_count = _count_failure(symbol_slice, "false_breakout")
            local_missed_good_wait_release_count = _count_failure(symbol_slice, "missed_good_wait_release")
            local_late_entry_chase_fail_count = _count_failure(symbol_slice, "late_entry_chase_fail")
            harvest_failed_follow_through_count = _count_failure(failure_slice, "failed_follow_through")
            harvest_early_exit_regret_count = _count_failure(failure_slice, "early_exit_regret")
            harvest_false_breakout_count = _count_failure(failure_slice, "false_breakout")
            harvest_missed_good_wait_release_count = _count_failure(failure_slice, "missed_good_wait_release")
            harvest_late_entry_chase_fail_count = _count_failure(failure_slice, "late_entry_chase_fail")

            readiness_state = _readiness_state(
                row_count=row_count,
                positive_count=positive_count,
                negative_count=negative_count,
                min_rows=int(config["min_rows"]),
                needs_dual_class=bool(config["needs_dual_class"]),
                unlabeled_ratio=unlabeled_ratio,
                strong_row_count=strong_row_count,
            )
            recommended_action = _recommended_action(
                surface_name=surface_name,
                readiness_state=readiness_state,
                failed_follow_through_count=local_failed_follow_through_count,
                early_exit_regret_count=local_early_exit_regret_count,
                false_breakout_count=local_false_breakout_count,
                missed_good_wait_release_count=local_missed_good_wait_release_count,
            )

            rows.append(
                {
                    "evaluation_id": f"symbol_surface_preview_eval::{market_family}::{surface_name}",
                    "market_family": market_family,
                    "surface_name": surface_name,
                    "dataset_name": dataset_name,
                    "adapter_mode": _to_text(adapter_row.get("adapter_mode")),
                    "recommended_bias_action": _to_text(adapter_row.get("recommended_bias_action")),
                    "objective_key": _to_text(adapter_row.get("objective_key")),
                    "current_focus": _to_text(adapter_row.get("current_focus")),
                    "row_count": row_count,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "unlabeled_count": unlabeled_count,
                    "positive_rate": positive_rate,
                    "avg_training_weight": avg_training_weight,
                    "unlabeled_ratio": unlabeled_ratio,
                    "strong_row_count": strong_row_count,
                    "strong_row_ratio": strong_row_ratio,
                    "time_axis_phase_count": phase_count,
                    "underfire_count": int((distribution_slice["promotion_gap_note"] == "underfired_vs_distribution").sum()) if not distribution_slice.empty else 0,
                    "overfire_count": int((distribution_slice["promotion_gap_note"] == "overfired_vs_distribution").sum()) if not distribution_slice.empty else 0,
                    "probe_eligible_count": int((distribution_slice["combined_gate_state"] == "PROBE_ELIGIBLE").sum()) if not distribution_slice.empty else 0,
                    "failed_follow_through_count": local_failed_follow_through_count,
                    "early_exit_regret_count": local_early_exit_regret_count,
                    "false_breakout_count": local_false_breakout_count,
                    "missed_good_wait_release_count": local_missed_good_wait_release_count,
                    "late_entry_chase_fail_count": local_late_entry_chase_fail_count,
                    "harvest_failed_follow_through_count": harvest_failed_follow_through_count,
                    "harvest_early_exit_regret_count": harvest_early_exit_regret_count,
                    "harvest_false_breakout_count": harvest_false_breakout_count,
                    "harvest_missed_good_wait_release_count": harvest_missed_good_wait_release_count,
                    "harvest_late_entry_chase_fail_count": harvest_late_entry_chase_fail_count,
                    "readiness_state": readiness_state,
                    "recommended_action": recommended_action,
                }
            )

    frame = pd.DataFrame(rows, columns=SYMBOL_SURFACE_PREVIEW_EVALUATION_COLUMNS)
    summary = {
        "symbol_surface_preview_evaluation_version": SYMBOL_SURFACE_PREVIEW_EVALUATION_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "market_family_count": int(frame["market_family"].nunique()) if not frame.empty else 0,
        "surface_count": int(frame["surface_name"].nunique()) if not frame.empty else 0,
        "readiness_state_counts": frame["readiness_state"].value_counts().to_dict() if not frame.empty else {},
        "recommended_action_counts": frame["recommended_action"].value_counts().to_dict() if not frame.empty else {},
        "preview_eval_ready_count": int((frame["readiness_state"] == "preview_eval_ready").sum()) if not frame.empty else 0,
        "needs_label_resolution_count": int((frame["readiness_state"] == "needs_label_resolution").sum()) if not frame.empty else 0,
        "single_class_only_count": int((frame["readiness_state"] == "single_class_only").sum()) if not frame.empty else 0,
        "insufficient_rows_count": int((frame["readiness_state"] == "insufficient_rows").sum()) if not frame.empty else 0,
        "recommended_next_action": "prepare_mf17_bounded_rollout_candidates" if not frame.empty and int((frame["readiness_state"] == "preview_eval_ready").sum()) > 0 else "collect_more_symbol_surface_contrast_rows",
    }
    return frame, summary


def render_symbol_surface_preview_evaluation_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Symbol-Surface Preview Evaluation",
        "",
        f"- version: `{summary.get('symbol_surface_preview_evaluation_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- market_family_count: `{summary.get('market_family_count', 0)}`",
        f"- surface_count: `{summary.get('surface_count', 0)}`",
        f"- readiness_state_counts: `{summary.get('readiness_state_counts', {})}`",
        f"- recommended_action_counts: `{summary.get('recommended_action_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    if not frame.empty:
        lines.extend(["## Rows", ""])
        for row in frame.to_dict(orient="records"):
            lines.append(
                "- "
                + f"{row.get('market_family', '')} | {row.get('surface_name', '')} | rows={row.get('row_count', 0)} | "
                + f"pos={row.get('positive_count', 0)} | neg={row.get('negative_count', 0)} | "
                + f"readiness={row.get('readiness_state', '')} | action={row.get('recommended_action', '')}"
            )
    return "\n".join(lines).rstrip() + "\n"
