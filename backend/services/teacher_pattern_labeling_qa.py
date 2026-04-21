"""Teacher-pattern labeling QA gate for compact datasets."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


WATCHLIST_PAIRS = (
    (12, 23),
    (5, 10),
    (2, 16),
)
RARE_PATTERN_WATCH_IDS = (3, 17, 19)
DEFAULT_RARE_THRESHOLD = 0.01
DEFAULT_REVIEW_FRACTION = 0.05


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


def _distribution_from_series(series: pd.Series, denominator: int) -> dict[str, dict[str, float | int]]:
    counts = series[series != ""].value_counts().sort_index()
    result: dict[str, dict[str, float | int]] = {}
    for key, count in counts.items():
        result[str(key)] = {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
    return result


def _primary_distribution(pattern_ids: pd.Series, denominator: int) -> dict[int, dict[str, float | int]]:
    counts = pattern_ids[pattern_ids > 0].value_counts().sort_index()
    result: dict[int, dict[str, float | int]] = {}
    for key, count in counts.items():
        result[int(key)] = {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
    return result


def _secondary_pair_counts(primary_ids: pd.Series, secondary_ids: pd.Series) -> dict[str, int]:
    counts: dict[str, int] = {}
    for primary_id, secondary_id in zip(primary_ids.tolist(), secondary_ids.tolist()):
        if primary_id <= 0 or secondary_id <= 0:
            continue
        left, right = sorted((int(primary_id), int(secondary_id)))
        key = f"{left}-{right}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _build_review_targets(
    frame: pd.DataFrame,
    labeled_mask: pd.Series,
    confidences: pd.Series,
    review_fraction: float,
) -> dict[str, Any]:
    labeled_count = int(labeled_mask.sum())
    if labeled_count <= 0:
        return {
            "target_count": 0,
            "cutoff_confidence": None,
            "samples": [],
        }

    target_count = max(1, math.ceil(labeled_count * review_fraction))
    review_frame = frame.loc[labeled_mask].copy()
    review_frame["_teacher_confidence"] = confidences.loc[labeled_mask]
    review_frame = review_frame.sort_values(
        by=["_teacher_confidence", "teacher_pattern_id", "teacher_pattern_secondary_id"],
        ascending=[True, True, True],
        kind="stable",
    ).head(target_count)

    identifier_column = next(
        (column for column in ("trade_link_key", "ticket", "replay_row_key") if column in review_frame.columns),
        None,
    )
    samples = []
    for row_index, row in review_frame.iterrows():
        sample = {
            "row_index": int(row_index) if isinstance(row_index, (int, float)) else str(row_index),
            "symbol": str(row.get("symbol", "") or ""),
            "teacher_pattern_id": int(pd.to_numeric(row.get("teacher_pattern_id"), errors="coerce") or 0),
            "teacher_pattern_secondary_id": int(pd.to_numeric(row.get("teacher_pattern_secondary_id"), errors="coerce") or 0),
            "teacher_label_confidence": float(pd.to_numeric(row.get("_teacher_confidence"), errors="coerce") or 0.0),
        }
        if identifier_column:
            sample["identifier"] = str(row.get(identifier_column, "") or "")
        samples.append(sample)

    cutoff_confidence = None
    if not review_frame.empty:
        cutoff_confidence = float(review_frame["_teacher_confidence"].max())
    return {
        "target_count": int(len(review_frame)),
        "cutoff_confidence": cutoff_confidence,
        "samples": samples,
    }


def build_teacher_pattern_labeling_qa_report(
    frame: pd.DataFrame | None,
    *,
    rare_threshold: float = DEFAULT_RARE_THRESHOLD,
    review_fraction: float = DEFAULT_REVIEW_FRACTION,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    total_rows = int(len(dataset))
    if total_rows <= 0:
        return {
            "gate_status": "FAIL",
            "failures": ["empty_dataset"],
            "warnings": [],
            "total_rows": 0,
            "labeled_rows": 0,
            "unlabeled_rows": 0,
            "unlabeled_ratio": 0.0,
            "distribution": {},
            "watchlist_pairs": {},
            "rare_pattern_warnings": [],
            "low_confidence_review": {
                "target_count": 0,
                "cutoff_confidence": None,
                "samples": [],
            },
            "provenance": {},
        }

    primary_ids = _to_int_series(_series(dataset, "teacher_pattern_id", 0))
    secondary_ids = _to_int_series(_series(dataset, "teacher_pattern_secondary_id", 0))
    confidences = _to_float_series(_series(dataset, "teacher_label_confidence", 0.0)).clip(0.0, 1.0)
    lookbacks = _to_int_series(_series(dataset, "teacher_lookback_bars", 0))
    label_sources = _to_text_series(_series(dataset, "teacher_label_source", ""))
    label_versions = _to_text_series(_series(dataset, "teacher_label_version", ""))
    review_status = _to_text_series(_series(dataset, "teacher_label_review_status", ""))
    groups = _to_text_series(_series(dataset, "teacher_pattern_group", ""))
    symbols = _to_text_series(_series(dataset, "symbol", ""))
    entry_bias = _to_text_series(_series(dataset, "teacher_entry_bias", ""))
    wait_bias = _to_text_series(_series(dataset, "teacher_wait_bias", ""))
    exit_bias = _to_text_series(_series(dataset, "teacher_exit_bias", ""))

    labeled_mask = primary_ids > 0
    labeled_rows = int(labeled_mask.sum())
    unlabeled_rows = total_rows - labeled_rows
    unlabeled_ratio = float(unlabeled_rows / total_rows) if total_rows else 0.0

    primary_distribution = _primary_distribution(primary_ids, labeled_rows)
    pair_counts = _secondary_pair_counts(primary_ids, secondary_ids)
    watchlist_pairs: dict[str, dict[str, float | int]] = {}
    for left, right in WATCHLIST_PAIRS:
        key = f"{min(left, right)}-{max(left, right)}"
        count = int(pair_counts.get(key, 0))
        watchlist_pairs[key] = {
            "count": count,
            "ratio": float(count / labeled_rows) if labeled_rows else 0.0,
        }

    provenance = {
        "missing_source_count": int(((label_sources == "") & labeled_mask).sum()),
        "missing_version_count": int(((label_versions == "") & labeled_mask).sum()),
        "invalid_lookback_count": int(((lookbacks != 20) & labeled_mask).sum()),
        "unreviewed_count": int(((review_status == "unreviewed") & labeled_mask).sum()),
    }

    rare_pattern_warnings = []
    for pattern_id in RARE_PATTERN_WATCH_IDS:
        distribution = primary_distribution.get(pattern_id, {"count": 0, "ratio": 0.0})
        if float(distribution["ratio"]) < rare_threshold:
            rare_pattern_warnings.append(
                {
                    "pattern_id": int(pattern_id),
                    "count": int(distribution["count"]),
                    "ratio": float(distribution["ratio"]),
                    "threshold": float(rare_threshold),
                }
            )

    low_confidence_review = _build_review_targets(dataset, labeled_mask, confidences, review_fraction)

    failures: list[str] = []
    warnings: list[str] = []
    if labeled_rows <= 0:
        failures.append("no_labeled_rows")
    if provenance["missing_source_count"] > 0:
        failures.append("missing_label_source")
    if provenance["missing_version_count"] > 0:
        failures.append("missing_label_version")
    if provenance["invalid_lookback_count"] > 0:
        failures.append("invalid_teacher_lookback")
    if unlabeled_rows > 0:
        warnings.append("unlabeled_rows_present")
    if rare_pattern_warnings:
        warnings.append("rare_pattern_watch_triggered")
    if low_confidence_review["target_count"] > 0:
        warnings.append("low_confidence_review_required")

    gate_status = "PASS"
    if failures:
        gate_status = "FAIL"
    elif warnings:
        gate_status = "PASS_WITH_WARNINGS"

    return {
        "gate_status": gate_status,
        "failures": failures,
        "warnings": warnings,
        "total_rows": total_rows,
        "labeled_rows": labeled_rows,
        "unlabeled_rows": unlabeled_rows,
        "unlabeled_ratio": unlabeled_ratio,
        "distribution": {
            "primary_patterns": primary_distribution,
            "groups": _distribution_from_series(groups.loc[labeled_mask], labeled_rows),
            "symbols": _distribution_from_series(symbols.loc[labeled_mask], labeled_rows),
            "entry_bias": _distribution_from_series(entry_bias.loc[labeled_mask], labeled_rows),
            "wait_bias": _distribution_from_series(wait_bias.loc[labeled_mask], labeled_rows),
            "exit_bias": _distribution_from_series(exit_bias.loc[labeled_mask], labeled_rows),
            "secondary_pairs": {
                key: {
                    "count": int(count),
                    "ratio": float(count / labeled_rows) if labeled_rows else 0.0,
                }
                for key, count in sorted(pair_counts.items())
            },
        },
        "watchlist_pairs": watchlist_pairs,
        "rare_pattern_warnings": rare_pattern_warnings,
        "low_confidence_review": low_confidence_review,
        "provenance": provenance,
    }
