"""Step E2 full labeling QA report for teacher-pattern compact datasets."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.services.teacher_pattern_experiment_seed import build_teacher_pattern_experiment_seed_report
from backend.services.teacher_pattern_labeling_qa import WATCHLIST_PAIRS


PATTERN_IDS = tuple(range(1, 26))
DEFAULT_MIN_LABELED_ROWS = 10_000
DEFAULT_GROUP_SKEW_THRESHOLD = 0.80
DEFAULT_PAIR_RATIO_LIMIT = 0.15
DEFAULT_RARE_PATTERN_RATIO = 0.01
DEFAULT_SYMBOLS = ("BTCUSD", "XAUUSD", "NAS100")


def _series(frame: pd.DataFrame, column: str, default: Any) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _to_int_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


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
    payload: dict[int, dict[str, float | int]] = {}
    for pattern_id in PATTERN_IDS:
        count = int(counts.get(pattern_id, 0))
        payload[int(pattern_id)] = {
            "count": count,
            "ratio": float(count / denominator) if denominator else 0.0,
        }
    return payload


def _pair_distribution(
    primary_ids: pd.Series,
    secondary_ids: pd.Series,
    denominator: int,
) -> dict[str, dict[str, float | int]]:
    counts: dict[str, int] = {}
    for primary_id, secondary_id in zip(primary_ids.tolist(), secondary_ids.tolist()):
        if primary_id <= 0 or secondary_id <= 0:
            continue
        left, right = sorted((int(primary_id), int(secondary_id)))
        key = f"{left}-{right}"
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        key: {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in ordered
    }


def _top_n(mapping: dict[str, dict[str, float | int]], limit: int = 10) -> dict[str, dict[str, float | int]]:
    ordered = sorted(mapping.items(), key=lambda item: (-int(item[1]["count"]), item[0]))
    return dict(ordered[:limit])


def build_teacher_pattern_full_labeling_qa_report(
    frame: pd.DataFrame | None,
    *,
    min_labeled_rows: int = DEFAULT_MIN_LABELED_ROWS,
    group_skew_threshold: float = DEFAULT_GROUP_SKEW_THRESHOLD,
    pair_ratio_limit: float = DEFAULT_PAIR_RATIO_LIMIT,
    rare_pattern_ratio: float = DEFAULT_RARE_PATTERN_RATIO,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    seed_report = build_teacher_pattern_experiment_seed_report(
        dataset,
        min_seed_rows=int(min_labeled_rows),
    )

    primary_ids = _to_int_series(_series(dataset, "teacher_pattern_id", 0))
    secondary_ids = _to_int_series(_series(dataset, "teacher_pattern_secondary_id", 0))
    groups = _to_text_series(_series(dataset, "teacher_pattern_group", ""))
    symbols = _to_text_series(_series(dataset, "symbol", ""))

    labeled_mask = primary_ids > 0
    labeled_rows = int(labeled_mask.sum())
    labeled_primary = primary_ids.loc[labeled_mask]
    labeled_secondary = secondary_ids.loc[labeled_mask]
    labeled_groups = groups.loc[labeled_mask]
    labeled_symbols = symbols.loc[labeled_mask]

    primary_distribution = _pattern_distribution(labeled_primary, labeled_rows)
    secondary_distribution = _pattern_distribution(labeled_secondary, labeled_rows)
    pair_distribution = _pair_distribution(labeled_primary, labeled_secondary, labeled_rows)
    group_distribution = _distribution(labeled_groups, labeled_rows)

    covered_primary_ids = [pattern_id for pattern_id, payload in primary_distribution.items() if int(payload["count"]) > 0]
    missing_primary_ids = [pattern_id for pattern_id in PATTERN_IDS if pattern_id not in covered_primary_ids]
    rare_primary_ids = [
        pattern_id
        for pattern_id, payload in primary_distribution.items()
        if 0 < int(payload["count"]) and float(payload["ratio"]) < float(rare_pattern_ratio)
    ]

    warnings: list[str] = list(seed_report.get("qa_warnings", []))
    if labeled_rows < int(min_labeled_rows):
        warnings.append("full_qa_seed_shortfall")
    if missing_primary_ids:
        warnings.append("missing_primary_patterns_present")
    if rare_primary_ids:
        warnings.append("rare_primary_patterns_present")

    if group_distribution:
        top_group, top_payload = max(group_distribution.items(), key=lambda item: float(item[1]["ratio"]))
        if float(top_payload["ratio"]) >= float(group_skew_threshold):
            warnings.append(f"overall_group_skew:{top_group}")

    symbol_reports: dict[str, dict[str, Any]] = {}
    for symbol in DEFAULT_SYMBOLS:
        symbol_mask = labeled_symbols == symbol
        symbol_rows = int(symbol_mask.sum())
        symbol_primary = labeled_primary.loc[symbol_mask]
        symbol_groups = labeled_groups.loc[symbol_mask]
        symbol_primary_distribution = _pattern_distribution(symbol_primary, symbol_rows)
        symbol_group_distribution = _distribution(symbol_groups, symbol_rows)
        symbol_missing_primary_ids = [
            pattern_id
            for pattern_id, payload in symbol_primary_distribution.items()
            if int(payload["count"]) <= 0
        ]
        symbol_top_group = None
        symbol_top_group_ratio = 0.0
        if symbol_group_distribution:
            symbol_top_group, top_payload = max(symbol_group_distribution.items(), key=lambda item: float(item[1]["ratio"]))
            symbol_top_group_ratio = float(top_payload["ratio"])
            if symbol_top_group_ratio >= float(group_skew_threshold):
                warnings.append(f"symbol_group_skew:{symbol}:{symbol_top_group}")
        symbol_reports[symbol] = {
            "rows": symbol_rows,
            "ratio": float(symbol_rows / labeled_rows) if labeled_rows else 0.0,
            "group_distribution": symbol_group_distribution,
            "primary_patterns_top": _top_n(
                {str(k): v for k, v in symbol_primary_distribution.items() if int(v["count"]) > 0},
                limit=10,
            ),
            "covered_primary_count": int(sum(1 for payload in symbol_primary_distribution.values() if int(payload["count"]) > 0)),
            "missing_primary_ids": symbol_missing_primary_ids,
            "top_group": symbol_top_group,
            "top_group_ratio": symbol_top_group_ratio,
        }

    pair_concentration_warnings: list[dict[str, Any]] = []
    for pair_key, payload in pair_distribution.items():
        if float(payload["ratio"]) >= float(pair_ratio_limit):
            pair_concentration_warnings.append(
                {
                    "pair": pair_key,
                    "count": int(payload["count"]),
                    "ratio": float(payload["ratio"]),
                    "threshold": float(pair_ratio_limit),
                }
            )
            warnings.append(f"pair_concentration:{pair_key}")

    watchlist_pair_summary: dict[str, dict[str, float | int]] = {}
    for left, right in WATCHLIST_PAIRS:
        key = f"{min(left, right)}-{max(left, right)}"
        watchlist_pair_summary[key] = pair_distribution.get(
            key,
            {"count": 0, "ratio": 0.0},
        )

    readiness = {
        "min_labeled_rows": int(min_labeled_rows),
        "full_qa_ready": bool(labeled_rows >= int(min_labeled_rows)),
        "shortfall_rows": max(0, int(min_labeled_rows) - labeled_rows),
    }

    return {
        "full_qa_readiness": readiness,
        "qa_gate_status": seed_report.get("qa_gate_status", "FAIL"),
        "qa_failures": list(seed_report.get("qa_failures", [])),
        "qa_warnings": list(seed_report.get("qa_warnings", [])),
        "warnings": sorted(set(warnings)),
        "total_rows": int(len(dataset)),
        "labeled_rows": labeled_rows,
        "unlabeled_rows": int(len(dataset) - labeled_rows),
        "pattern_coverage": {
            "covered_primary_count": int(len(covered_primary_ids)),
            "missing_primary_ids": missing_primary_ids,
            "rare_primary_ids": rare_primary_ids,
            "primary_patterns": primary_distribution,
            "secondary_patterns": secondary_distribution,
        },
        "group_distribution": group_distribution,
        "symbol_reports": symbol_reports,
        "primary_secondary_pairs": pair_distribution,
        "confusion_proxy_summary": {
            "watchlist_pairs": watchlist_pair_summary,
            "top_pairs": _top_n(pair_distribution, limit=10),
            "pair_concentration_warnings": pair_concentration_warnings,
        },
        "source_distribution": seed_report.get("source_distribution", {}),
        "review_status_distribution": seed_report.get("review_status_distribution", {}),
        "bias_distribution": seed_report.get("bias_distribution", {}),
        "confidence_summary": seed_report.get("confidence_summary", {}),
        "rare_pattern_warnings": seed_report.get("rare_pattern_warnings", []),
        "low_confidence_review": seed_report.get("low_confidence_review", {}),
    }
