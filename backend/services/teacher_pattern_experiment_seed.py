"""Experiment seed report for teacher-pattern labeled compact datasets."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from backend.services.economic_learning_targets import build_economic_target_summary
from backend.services.teacher_pattern_labeling_qa import build_teacher_pattern_labeling_qa_report
from backend.services.trade_csv_schema import normalize_trade_df


ENTRY_WAIT_QUALITY_POSITIVE_LABELS = {"better_entry_after_wait", "avoided_loss_by_wait"}
ENTRY_WAIT_QUALITY_NEGATIVE_LABELS = {"missed_move_by_wait", "delayed_loss_after_wait"}


def _series(frame: pd.DataFrame, column: str, default: Any) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _to_int_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _to_float_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def _to_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _distribution(series: pd.Series, denominator: int) -> dict[str, dict[str, float | int]]:
    counts = series[series != ""].value_counts().sort_index()
    return {
        str(key): {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in counts.items()
    }


def _pattern_distribution(series: pd.Series, denominator: int) -> dict[int, dict[str, float | int]]:
    counts = series[series > 0].value_counts().sort_index()
    return {
        int(key): {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in counts.items()
    }


def _confidence_summary(confidences: pd.Series) -> dict[str, float]:
    if confidences.empty:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p10": 0.0,
            "p90": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "mean": float(confidences.mean()),
        "median": float(confidences.median()),
        "p10": float(confidences.quantile(0.10)),
        "p90": float(confidences.quantile(0.90)),
        "min": float(confidences.min()),
        "max": float(confidences.max()),
    }


def _recommended_split_counts(labeled_rows: int) -> dict[str, int]:
    if labeled_rows <= 0:
        return {"train": 0, "val": 0, "test": 0}
    train = int(math.floor(labeled_rows * 0.70))
    val = int(math.floor(labeled_rows * 0.15))
    test = max(0, labeled_rows - train - val)
    return {
        "train": train,
        "val": val,
        "test": test,
    }


def build_teacher_pattern_experiment_seed_report(
    frame: pd.DataFrame | None,
    *,
    min_seed_rows: int = 1000,
    economic_primary_min_support: int = 25,
    economic_loss_min_support: int = 25,
    economic_bucket_min_support: int = 25,
) -> dict[str, Any]:
    dataset = normalize_trade_df(frame.copy() if frame is not None else pd.DataFrame())
    qa_report = build_teacher_pattern_labeling_qa_report(dataset)

    primary_ids = _to_int_series(_series(dataset, "teacher_pattern_id", 0))
    symbols = _to_text_series(_series(dataset, "symbol", ""))
    groups = _to_text_series(_series(dataset, "teacher_pattern_group", ""))
    entry_bias = _to_text_series(_series(dataset, "teacher_entry_bias", ""))
    wait_bias = _to_text_series(_series(dataset, "teacher_wait_bias", ""))
    exit_bias = _to_text_series(_series(dataset, "teacher_exit_bias", ""))
    confidences = _to_float_series(_series(dataset, "teacher_label_confidence", 0.0)).clip(0.0, 1.0)
    sources = _to_text_series(_series(dataset, "teacher_label_source", ""))
    review_status = _to_text_series(_series(dataset, "teacher_label_review_status", ""))
    entry_wait_quality = _to_text_series(_series(dataset, "entry_wait_quality_label", "")).str.lower()
    entry_wait_quality_score = _to_float_series(_series(dataset, "entry_wait_quality_score", 0.0))
    forecast_scene_family = _to_text_series(_series(dataset, "forecast_state25_scene_family", "")).str.lower()
    forecast_decision_hint = _to_text_series(_series(dataset, "forecast_decision_hint", "")).str.upper()
    forecast_transition_status = _to_text_series(_series(dataset, "forecast_transition_outcome_status", "")).str.lower()
    forecast_management_status = _to_text_series(_series(dataset, "forecast_management_outcome_status", "")).str.lower()
    forecast_bridge_quality_status = _to_text_series(
        _series(dataset, "forecast_state25_bridge_quality_status", "")
    ).str.lower()
    belief_outcome_label = _to_text_series(_series(dataset, "belief_outcome_label", "")).str.lower()
    belief_label_confidence = _to_text_series(_series(dataset, "belief_label_confidence", "")).str.lower()
    belief_anchor_context = _to_text_series(_series(dataset, "belief_anchor_context", "")).str.lower()
    barrier_outcome_label = _to_text_series(_series(dataset, "barrier_outcome_label", "")).str.lower()
    barrier_label_confidence = _to_text_series(_series(dataset, "barrier_label_confidence", "")).str.lower()
    barrier_anchor_context = _to_text_series(_series(dataset, "barrier_anchor_context", "")).str.lower()
    barrier_primary_component = _to_text_series(_series(dataset, "barrier_primary_component", "")).str.lower()
    barrier_cost_loss_avoided_r = _to_float_series(_series(dataset, "barrier_cost_loss_avoided_r", 0.0))
    barrier_cost_profit_missed_r = _to_float_series(_series(dataset, "barrier_cost_profit_missed_r", 0.0))
    barrier_cost_wait_value_r = _to_float_series(_series(dataset, "barrier_cost_wait_value_r", 0.0))

    labeled_mask = primary_ids > 0
    labeled_rows = int(labeled_mask.sum())
    unlabeled_rows = int(len(dataset) - labeled_rows)

    labeled_symbols = symbols.loc[labeled_mask]
    symbol_distribution = _distribution(labeled_symbols, labeled_rows)
    pattern_distribution = _pattern_distribution(primary_ids.loc[labeled_mask], labeled_rows)
    group_distribution = _distribution(groups.loc[labeled_mask], labeled_rows)
    source_distribution = _distribution(sources.loc[labeled_mask], labeled_rows)
    review_distribution = _distribution(review_status.loc[labeled_mask], labeled_rows)
    bias_distribution = {
        "entry": _distribution(entry_bias.loc[labeled_mask], labeled_rows),
        "wait": _distribution(wait_bias.loc[labeled_mask], labeled_rows),
        "exit": _distribution(exit_bias.loc[labeled_mask], labeled_rows),
    }
    confidence = _confidence_summary(confidences.loc[labeled_mask])
    entry_wait_quality_mask = labeled_mask & (entry_wait_quality != "")
    entry_wait_quality_rows = int(entry_wait_quality_mask.sum())
    entry_wait_quality_distribution = _distribution(
        entry_wait_quality.loc[entry_wait_quality_mask],
        entry_wait_quality_rows,
    )
    economic_target_summary = build_economic_target_summary(
        dataset,
        primary_min_support=int(economic_primary_min_support),
        loss_min_support=int(economic_loss_min_support),
        bucket_min_support=int(economic_bucket_min_support),
    )
    entry_wait_quality_valid_mask = entry_wait_quality_mask & (entry_wait_quality != "insufficient_evidence")
    entry_wait_quality_coverage = {
        "rows_with_entry_wait_quality": entry_wait_quality_rows,
        "coverage_ratio_vs_labeled": float(entry_wait_quality_rows / labeled_rows) if labeled_rows else 0.0,
        "valid_rows": int(entry_wait_quality_valid_mask.sum()),
        "valid_ratio_vs_entry_wait_quality": (
            float(entry_wait_quality_valid_mask.sum() / entry_wait_quality_rows) if entry_wait_quality_rows else 0.0
        ),
        "positive_rows": int((entry_wait_quality_mask & entry_wait_quality.isin(ENTRY_WAIT_QUALITY_POSITIVE_LABELS)).sum()),
        "negative_rows": int((entry_wait_quality_mask & entry_wait_quality.isin(ENTRY_WAIT_QUALITY_NEGATIVE_LABELS)).sum()),
        "insufficient_rows": int((entry_wait_quality_mask & (entry_wait_quality == "insufficient_evidence")).sum()),
        "score_summary": _confidence_summary(entry_wait_quality_score.loc[entry_wait_quality_mask]),
    }
    forecast_state25_total_mask = (forecast_scene_family != "") | (forecast_decision_hint != "")
    forecast_state25_mask = labeled_mask & forecast_state25_total_mask
    forecast_transition_valid_mask = forecast_state25_mask & (forecast_transition_status == "valid")
    forecast_management_valid_mask = forecast_state25_mask & (forecast_management_status == "valid")
    forecast_full_bridge_mask = forecast_state25_mask & (forecast_bridge_quality_status == "full_outcome_bridge")
    forecast_partial_bridge_mask = forecast_state25_mask & (forecast_bridge_quality_status == "partial_outcome_bridge")
    forecast_insufficient_future_mask = forecast_state25_mask & (
        (forecast_transition_status == "insufficient_future_bars")
        | (forecast_management_status == "insufficient_future_bars")
    )
    forecast_state25_total_rows = int(forecast_state25_total_mask.sum())
    forecast_state25_rows = int(forecast_state25_mask.sum())
    forecast_state25_coverage = {
        "rows_with_forecast_state25_total": forecast_state25_total_rows,
        "coverage_ratio_vs_total_rows": float(forecast_state25_total_rows / len(dataset)) if len(dataset) else 0.0,
        "rows_with_forecast_state25": forecast_state25_rows,
        "coverage_ratio_vs_labeled": float(forecast_state25_rows / labeled_rows) if labeled_rows else 0.0,
        "valid_transition_rows": int(forecast_transition_valid_mask.sum()),
        "valid_transition_ratio_vs_forecast_state25": (
            float(forecast_transition_valid_mask.sum() / forecast_state25_rows) if forecast_state25_rows else 0.0
        ),
        "valid_management_rows": int(forecast_management_valid_mask.sum()),
        "valid_management_ratio_vs_forecast_state25": (
            float(forecast_management_valid_mask.sum() / forecast_state25_rows) if forecast_state25_rows else 0.0
        ),
        "full_outcome_eligible_rows": int(forecast_full_bridge_mask.sum()),
        "full_outcome_eligible_ratio_vs_forecast_state25": (
            float(forecast_full_bridge_mask.sum() / forecast_state25_rows) if forecast_state25_rows else 0.0
        ),
        "partial_outcome_eligible_rows": int(forecast_partial_bridge_mask.sum()),
        "partial_outcome_eligible_ratio_vs_forecast_state25": (
            float(forecast_partial_bridge_mask.sum() / forecast_state25_rows) if forecast_state25_rows else 0.0
        ),
        "insufficient_future_bars_rows": int(forecast_insufficient_future_mask.sum()),
        "insufficient_future_bars_ratio_vs_forecast_state25": (
            float(forecast_insufficient_future_mask.sum() / forecast_state25_rows) if forecast_state25_rows else 0.0
        ),
        "scene_family_distribution": _distribution(
            forecast_scene_family.loc[forecast_state25_mask],
            forecast_state25_rows,
        ),
        "decision_hint_distribution": _distribution(
            forecast_decision_hint.loc[forecast_state25_mask],
            forecast_state25_rows,
        ),
        "transition_status_distribution": _distribution(
            forecast_transition_status.loc[forecast_state25_mask],
            forecast_state25_rows,
        ),
        "management_status_distribution": _distribution(
            forecast_management_status.loc[forecast_state25_mask],
            forecast_state25_rows,
        ),
        "bridge_quality_status_distribution": _distribution(
            forecast_bridge_quality_status.loc[forecast_state25_mask],
            forecast_state25_rows,
        ),
    }
    belief_outcome_total_mask = belief_outcome_label != ""
    belief_outcome_mask = labeled_mask & belief_outcome_total_mask
    belief_outcome_total_rows = int(belief_outcome_total_mask.sum())
    belief_outcome_rows = int(belief_outcome_mask.sum())
    belief_high_medium_mask = belief_outcome_mask & belief_label_confidence.isin(["high", "medium"])
    belief_usable_mask = belief_outcome_mask & belief_label_confidence.isin(["high", "medium", "weak_usable"])
    belief_weak_usable_mask = belief_outcome_mask & (belief_label_confidence == "weak_usable")
    belief_outcome_coverage = {
        "rows_with_belief_outcome_total": belief_outcome_total_rows,
        "coverage_ratio_vs_total_rows": float(belief_outcome_total_rows / len(dataset)) if len(dataset) else 0.0,
        "rows_with_belief_outcome": belief_outcome_rows,
        "coverage_ratio_vs_labeled": float(belief_outcome_rows / labeled_rows) if labeled_rows else 0.0,
        "high_or_medium_confidence_rows": int(belief_high_medium_mask.sum()),
        "high_or_medium_confidence_ratio_vs_belief_outcome": (
            float(belief_high_medium_mask.sum() / belief_outcome_rows) if belief_outcome_rows else 0.0
        ),
        "usable_confidence_rows": int(belief_usable_mask.sum()),
        "usable_confidence_ratio_vs_belief_outcome": (
            float(belief_usable_mask.sum() / belief_outcome_rows) if belief_outcome_rows else 0.0
        ),
        "weak_usable_rows": int(belief_weak_usable_mask.sum()),
        "weak_usable_ratio_vs_belief_outcome": (
            float(belief_weak_usable_mask.sum() / belief_outcome_rows) if belief_outcome_rows else 0.0
        ),
        "label_distribution": _distribution(
            belief_outcome_label.loc[belief_outcome_mask],
            belief_outcome_rows,
        ),
        "confidence_distribution": _distribution(
            belief_label_confidence.loc[belief_outcome_mask],
            belief_outcome_rows,
        ),
        "anchor_context_distribution": _distribution(
            belief_anchor_context.loc[belief_outcome_mask],
            belief_outcome_rows,
        ),
    }
    barrier_outcome_total_mask = barrier_outcome_label != ""
    barrier_outcome_mask = labeled_mask & barrier_outcome_total_mask
    barrier_outcome_total_rows = int(barrier_outcome_total_mask.sum())
    barrier_outcome_rows = int(barrier_outcome_mask.sum())
    barrier_high_medium_mask = barrier_outcome_mask & barrier_label_confidence.isin(["high", "medium"])
    barrier_usable_mask = barrier_outcome_mask & barrier_label_confidence.isin(["high", "medium", "weak_usable"])
    barrier_weak_usable_mask = barrier_outcome_mask & (barrier_label_confidence == "weak_usable")
    barrier_outcome_coverage = {
        "rows_with_barrier_outcome_total": barrier_outcome_total_rows,
        "coverage_ratio_vs_total_rows": float(barrier_outcome_total_rows / len(dataset)) if len(dataset) else 0.0,
        "rows_with_barrier_outcome": barrier_outcome_rows,
        "coverage_ratio_vs_labeled": float(barrier_outcome_rows / labeled_rows) if labeled_rows else 0.0,
        "high_or_medium_confidence_rows": int(barrier_high_medium_mask.sum()),
        "high_or_medium_confidence_ratio_vs_barrier_outcome": (
            float(barrier_high_medium_mask.sum() / barrier_outcome_rows) if barrier_outcome_rows else 0.0
        ),
        "usable_confidence_rows": int(barrier_usable_mask.sum()),
        "usable_confidence_ratio_vs_barrier_outcome": (
            float(barrier_usable_mask.sum() / barrier_outcome_rows) if barrier_outcome_rows else 0.0
        ),
        "weak_usable_rows": int(barrier_weak_usable_mask.sum()),
        "weak_usable_ratio_vs_barrier_outcome": (
            float(barrier_weak_usable_mask.sum() / barrier_outcome_rows) if barrier_outcome_rows else 0.0
        ),
        "weak_usable_share": (
            float(barrier_weak_usable_mask.sum() / barrier_usable_mask.sum()) if barrier_usable_mask.sum() else 0.0
        ),
        "weak_to_medium_conversion_rate": (
            float(barrier_high_medium_mask.sum() / barrier_usable_mask.sum()) if barrier_usable_mask.sum() else 0.0
        ),
        "label_distribution": _distribution(
            barrier_outcome_label.loc[barrier_outcome_mask],
            barrier_outcome_rows,
        ),
        "confidence_distribution": _distribution(
            barrier_label_confidence.loc[barrier_outcome_mask],
            barrier_outcome_rows,
        ),
        "anchor_context_distribution": _distribution(
            barrier_anchor_context.loc[barrier_outcome_mask],
            barrier_outcome_rows,
        ),
        "primary_component_distribution": _distribution(
            barrier_primary_component.loc[barrier_outcome_mask],
            barrier_outcome_rows,
        ),
        "loss_avoided_r_mean": float(barrier_cost_loss_avoided_r.loc[barrier_outcome_mask].mean()) if barrier_outcome_rows else 0.0,
        "profit_missed_r_mean": float(barrier_cost_profit_missed_r.loc[barrier_outcome_mask].mean()) if barrier_outcome_rows else 0.0,
        "wait_value_r_mean": float(barrier_cost_wait_value_r.loc[barrier_outcome_mask].mean()) if barrier_outcome_rows else 0.0,
    }

    ready = labeled_rows >= int(min_seed_rows)
    readiness = {
        "min_seed_rows": int(min_seed_rows),
        "seed_ready": bool(ready),
        "shortfall_rows": max(0, int(min_seed_rows) - labeled_rows),
        "recommended_split": _recommended_split_counts(labeled_rows),
    }

    return {
        "seed_readiness": readiness,
        "qa_gate_status": qa_report.get("gate_status", "FAIL"),
        "qa_failures": list(qa_report.get("failures", [])),
        "qa_warnings": list(qa_report.get("warnings", [])),
        "total_rows": int(len(dataset)),
        "labeled_rows": labeled_rows,
        "unlabeled_rows": unlabeled_rows,
        "symbol_distribution": symbol_distribution,
        "pattern_distribution": pattern_distribution,
        "group_distribution": group_distribution,
        "source_distribution": source_distribution,
        "review_status_distribution": review_distribution,
        "bias_distribution": bias_distribution,
        "entry_wait_quality_distribution": entry_wait_quality_distribution,
        "entry_wait_quality_coverage": entry_wait_quality_coverage,
        "forecast_state25_coverage": forecast_state25_coverage,
        "belief_outcome_coverage": belief_outcome_coverage,
        "barrier_outcome_coverage": barrier_outcome_coverage,
        "economic_target_summary": economic_target_summary,
        "confidence_summary": confidence,
        "watchlist_pairs": qa_report.get("watchlist_pairs", {}),
        "rare_pattern_warnings": qa_report.get("rare_pattern_warnings", []),
        "low_confidence_review": qa_report.get("low_confidence_review", {}),
    }
