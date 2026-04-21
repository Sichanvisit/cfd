"""Economic learning target summaries for state25 experiment seed and pilot reports."""

from __future__ import annotations

from typing import Any

import pandas as pd


ECONOMIC_TARGET_SUMMARY_VERSION = "economic_target_summary_v1"
ECONOMIC_PRIMARY_TARGET_COLUMN = "learning_total_label"
ECONOMIC_PRIMARY_SCORE_COLUMN = "learning_total_score"
ECONOMIC_LOSS_TARGET_COLUMN = "loss_quality_label"
ECONOMIC_SIGNED_EXIT_SCORE_COLUMN = "signed_exit_score"
ECONOMIC_VALUE_BUCKET_COLUMN = "economic_value_bucket_v1"


def _series(frame: pd.DataFrame, column: str, default: Any) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _to_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower()


def _to_float_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


def _distribution(series: pd.Series, denominator: int) -> dict[str, dict[str, float | int]]:
    counts = series[series != ""].value_counts().sort_index()
    return {
        str(key): {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in counts.items()
    }


def _score_summary(series: pd.Series) -> dict[str, float]:
    if series.empty:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p10": 0.0,
            "p90": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "mean": float(series.mean()),
        "median": float(series.median()),
        "p10": float(series.quantile(0.10)),
        "p90": float(series.quantile(0.90)),
        "min": float(series.min()),
        "max": float(series.max()),
    }


def _supported_text_classes(series: pd.Series, *, min_support: int) -> tuple[list[str], list[str]]:
    counts = pd.Series(series).astype(str).value_counts()
    supported = sorted(str(label) for label, count in counts.items() if str(label).strip() and int(count) >= int(min_support))
    excluded = sorted(str(label) for label, count in counts.items() if str(label).strip() and int(count) < int(min_support))
    return supported, excluded


def build_economic_value_bucket(series: pd.Series) -> pd.Series:
    scores = _to_float_series(series)

    def _bucket(value: float) -> str:
        if value >= 0.45:
            return "strong_positive"
        if value >= 0.15:
            return "positive"
        if value <= -0.45:
            return "strong_negative"
        if value <= -0.15:
            return "negative"
        return "neutral"

    return scores.map(_bucket).astype(str)


def build_economic_target_summary(
    frame: pd.DataFrame | None,
    *,
    primary_min_support: int = 25,
    loss_min_support: int = 25,
    bucket_min_support: int = 25,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()

    primary_labels = _to_text_series(_series(dataset, ECONOMIC_PRIMARY_TARGET_COLUMN, ""))
    primary_scores = _to_float_series(_series(dataset, ECONOMIC_PRIMARY_SCORE_COLUMN, 0.0))
    loss_labels = _to_text_series(_series(dataset, ECONOMIC_LOSS_TARGET_COLUMN, ""))
    signed_exit_scores = _to_float_series(_series(dataset, ECONOMIC_SIGNED_EXIT_SCORE_COLUMN, 0.0))
    profit = _to_float_series(_series(dataset, "profit", 0.0))

    primary_mask = primary_labels != ""
    loss_mask = loss_labels != ""
    bucket_labels = build_economic_value_bucket(primary_scores.loc[primary_mask]) if primary_mask.any() else pd.Series(dtype=str)
    primary_supported, primary_excluded = _supported_text_classes(primary_labels.loc[primary_mask], min_support=primary_min_support)
    loss_supported, loss_excluded = _supported_text_classes(loss_labels.loc[loss_mask], min_support=loss_min_support)
    bucket_supported, bucket_excluded = _supported_text_classes(bucket_labels, min_support=bucket_min_support)

    primary_rows = int(primary_mask.sum())
    loss_rows = int(loss_mask.sum())
    bucket_rows = int(len(bucket_labels))
    positive_profit_rows = int((profit > 0).sum())
    negative_profit_rows = int((profit < 0).sum())
    nonzero_signed_exit_rows = int((signed_exit_scores != 0.0).sum())

    return {
        "contract_version": ECONOMIC_TARGET_SUMMARY_VERSION,
        "coverage": {
            "rows_with_learning_total_label": primary_rows,
            "rows_with_loss_quality_label": loss_rows,
            "rows_with_economic_value_bucket": bucket_rows,
            "rows_with_nonzero_signed_exit_score": nonzero_signed_exit_rows,
            "positive_profit_rows": positive_profit_rows,
            "negative_profit_rows": negative_profit_rows,
        },
        "primary_target": {
            "column": ECONOMIC_PRIMARY_TARGET_COLUMN,
            "score_column": ECONOMIC_PRIMARY_SCORE_COLUMN,
            "min_support": int(primary_min_support),
            "target_rows": primary_rows,
            "supported_labels": primary_supported,
            "excluded_labels": primary_excluded,
            "distribution": _distribution(primary_labels.loc[primary_mask], primary_rows),
            "score_summary": _score_summary(primary_scores.loc[primary_mask]),
        },
        "secondary_targets": {
            ECONOMIC_LOSS_TARGET_COLUMN: {
                "column": ECONOMIC_LOSS_TARGET_COLUMN,
                "min_support": int(loss_min_support),
                "target_rows": loss_rows,
                "supported_labels": loss_supported,
                "excluded_labels": loss_excluded,
                "distribution": _distribution(loss_labels.loc[loss_mask], loss_rows),
            },
            ECONOMIC_VALUE_BUCKET_COLUMN: {
                "column": ECONOMIC_VALUE_BUCKET_COLUMN,
                "source_score_column": ECONOMIC_PRIMARY_SCORE_COLUMN,
                "min_support": int(bucket_min_support),
                "target_rows": bucket_rows,
                "supported_labels": bucket_supported,
                "excluded_labels": bucket_excluded,
                "distribution": _distribution(bucket_labels, bucket_rows),
            },
        },
        "score_surfaces": {
            "profit": _score_summary(profit),
            "signed_exit_score": _score_summary(signed_exit_scores),
            ECONOMIC_PRIMARY_SCORE_COLUMN: _score_summary(primary_scores.loc[primary_mask]),
        },
    }
