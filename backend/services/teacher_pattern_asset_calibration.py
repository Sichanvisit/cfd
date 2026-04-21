"""Asset-level calibration summary for teacher-pattern labeled compact datasets."""

from __future__ import annotations

from typing import Any

import pandas as pd


WATCHLIST_PAIRS: dict[tuple[int, int], str] = {
    (5, 10): "5-10",
    (2, 16): "2-16",
    (12, 23): "12-23",
}
DEFAULT_SYMBOLS = ("BTCUSD", "XAUUSD", "NAS100")


def _series(frame: pd.DataFrame, column: str, default: Any) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _to_int_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _to_float_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([float("inf"), float("-inf")], pd.NA)


def _to_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _distribution(series: pd.Series, denominator: int, *, limit: int | None = None) -> dict[str, dict[str, float | int]]:
    counts = series[series != ""].value_counts()
    if limit is not None:
        counts = counts.head(limit)
    return {
        str(key): {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in counts.items()
    }


def _pattern_distribution(series: pd.Series, denominator: int, *, limit: int | None = None) -> dict[int, dict[str, float | int]]:
    counts = series[series > 0].value_counts()
    if limit is not None:
        counts = counts.head(limit)
    return {
        int(key): {
            "count": int(count),
            "ratio": float(count / denominator) if denominator else 0.0,
        }
        for key, count in counts.items()
    }


def _numeric_summary(series: pd.Series) -> dict[str, float | int]:
    numeric = _to_float_series(series).dropna()
    if numeric.empty:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "p10": 0.0,
            "p90": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "count": int(numeric.shape[0]),
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
        "p10": float(numeric.quantile(0.10)),
        "p90": float(numeric.quantile(0.90)),
        "min": float(numeric.min()),
        "max": float(numeric.max()),
    }


def _is_flat(summary: dict[str, float | int], *, value: float | None = None) -> bool:
    count = int(summary.get("count", 0))
    if count <= 0:
        return False
    min_value = float(summary.get("min", 0.0))
    max_value = float(summary.get("max", 0.0))
    if value is None:
        return abs(max_value - min_value) <= 1e-12
    return abs(min_value - value) <= 1e-12 and abs(max_value - value) <= 1e-12


def _watchlist_pair_counts(primary_ids: pd.Series, secondary_ids: pd.Series) -> dict[str, int]:
    counts = {label: 0 for label in WATCHLIST_PAIRS.values()}
    for primary, secondary in zip(primary_ids.tolist(), secondary_ids.tolist()):
        if primary <= 0 or secondary <= 0:
            continue
        label = WATCHLIST_PAIRS.get(tuple(sorted((int(primary), int(secondary)))))
        if label:
            counts[label] += 1
    return counts


def build_teacher_pattern_asset_calibration_report(
    frame: pd.DataFrame | None,
    *,
    min_rows_per_symbol: int = 200,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()

    primary_ids = _to_int_series(_series(dataset, "teacher_pattern_id", 0))
    secondary_ids = _to_int_series(_series(dataset, "teacher_pattern_secondary_id", 0))
    symbols = _to_text_series(_series(dataset, "symbol", ""))
    groups = _to_text_series(_series(dataset, "teacher_pattern_group", ""))
    entry_bias = _to_text_series(_series(dataset, "teacher_entry_bias", ""))
    wait_bias = _to_text_series(_series(dataset, "teacher_wait_bias", ""))
    exit_bias = _to_text_series(_series(dataset, "teacher_exit_bias", ""))
    confidences = _to_float_series(_series(dataset, "teacher_label_confidence", 0.0)).fillna(0.0).clip(0.0, 1.0)

    labeled_mask = primary_ids > 0
    labeled = dataset.loc[labeled_mask].copy()
    labeled_primary_ids = primary_ids.loc[labeled_mask]
    labeled_secondary_ids = secondary_ids.loc[labeled_mask]
    labeled_symbols = symbols.loc[labeled_mask]
    labeled_groups = groups.loc[labeled_mask]
    labeled_entry_bias = entry_bias.loc[labeled_mask]
    labeled_wait_bias = wait_bias.loc[labeled_mask]
    labeled_exit_bias = exit_bias.loc[labeled_mask]
    labeled_confidences = confidences.loc[labeled_mask]

    labeled_rows = int(labeled_mask.sum())
    warnings: list[str] = []
    symbols_present = [symbol for symbol in DEFAULT_SYMBOLS if symbol in set(labeled_symbols.tolist())]
    missing_symbols = [symbol for symbol in DEFAULT_SYMBOLS if symbol not in symbols_present]
    warnings.extend(f"missing_symbol_seed:{symbol}" for symbol in missing_symbols)

    per_symbol: dict[str, dict[str, Any]] = {}
    overall_watchlist = _watchlist_pair_counts(labeled_primary_ids, labeled_secondary_ids)

    for symbol in DEFAULT_SYMBOLS:
        symbol_mask = labeled_symbols == symbol
        symbol_rows = int(symbol_mask.sum())
        if symbol_rows <= 0:
            per_symbol[symbol] = {
                "rows": 0,
                "ratio": 0.0,
                "warnings": ["no_labeled_rows"],
                "primary_patterns": {},
                "group_distribution": {},
                "bias_distribution": {"entry": {}, "wait": {}, "exit": {}},
                "confidence_summary": _numeric_summary(pd.Series(dtype=float)),
                "entry_atr_ratio_summary": _numeric_summary(pd.Series(dtype=float)),
                "regime_volatility_ratio_summary": _numeric_summary(pd.Series(dtype=float)),
                "micro_body_size_pct_20_summary": _numeric_summary(pd.Series(dtype=float)),
                "micro_doji_ratio_20_summary": _numeric_summary(pd.Series(dtype=float)),
                "micro_range_compression_ratio_20_summary": _numeric_summary(pd.Series(dtype=float)),
                "micro_volume_burst_ratio_20_summary": _numeric_summary(pd.Series(dtype=float)),
                "micro_volume_burst_decay_20_summary": _numeric_summary(pd.Series(dtype=float)),
                "watchlist_pairs": {label: 0 for label in WATCHLIST_PAIRS.values()},
            }
            continue

        symbol_frame = labeled.loc[symbol_mask].copy()
        symbol_primary = labeled_primary_ids.loc[symbol_mask]
        symbol_secondary = labeled_secondary_ids.loc[symbol_mask]
        symbol_groups = labeled_groups.loc[symbol_mask]
        symbol_entry_bias = labeled_entry_bias.loc[symbol_mask]
        symbol_wait_bias = labeled_wait_bias.loc[symbol_mask]
        symbol_exit_bias = labeled_exit_bias.loc[symbol_mask]
        symbol_confidence = labeled_confidences.loc[symbol_mask]

        symbol_warnings: list[str] = []
        if symbol_rows < int(min_rows_per_symbol):
            symbol_warnings.append("insufficient_rows")
            warnings.append(f"insufficient_symbol_seed:{symbol}")

        group_distribution = _distribution(symbol_groups, symbol_rows)
        if group_distribution:
            top_group, top_group_payload = next(iter(group_distribution.items()))
            if float(top_group_payload["ratio"]) >= 0.80:
                symbol_warnings.append(f"group_skew:{top_group}")
                warnings.append(f"group_skew:{symbol}:{top_group}")

        atr_summary = _numeric_summary(symbol_frame.get("entry_atr_ratio", pd.Series(dtype=float)))
        volatility_summary = _numeric_summary(symbol_frame.get("regime_volatility_ratio", pd.Series(dtype=float)))
        body_summary = _numeric_summary(symbol_frame.get("micro_body_size_pct_20", pd.Series(dtype=float)))
        doji_summary = _numeric_summary(symbol_frame.get("micro_doji_ratio_20", pd.Series(dtype=float)))
        compression_summary = _numeric_summary(symbol_frame.get("micro_range_compression_ratio_20", pd.Series(dtype=float)))
        burst_summary = _numeric_summary(symbol_frame.get("micro_volume_burst_ratio_20", pd.Series(dtype=float)))
        decay_summary = _numeric_summary(symbol_frame.get("micro_volume_burst_decay_20", pd.Series(dtype=float)))

        if _is_flat(atr_summary):
            symbol_warnings.append("entry_atr_ratio_flat")
            warnings.append(f"entry_atr_ratio_flat:{symbol}")

        micro_summaries = [body_summary, doji_summary, compression_summary, burst_summary, decay_summary]
        if all(_is_flat(summary, value=0.0) for summary in micro_summaries):
            symbol_warnings.append("micro_payload_zero")
            warnings.append(f"micro_payload_zero:{symbol}")

        per_symbol[symbol] = {
            "rows": symbol_rows,
            "ratio": float(symbol_rows / labeled_rows) if labeled_rows else 0.0,
            "warnings": symbol_warnings,
            "primary_patterns": _pattern_distribution(symbol_primary, symbol_rows, limit=5),
            "group_distribution": group_distribution,
            "bias_distribution": {
                "entry": _distribution(symbol_entry_bias, symbol_rows, limit=5),
                "wait": _distribution(symbol_wait_bias, symbol_rows, limit=5),
                "exit": _distribution(symbol_exit_bias, symbol_rows, limit=5),
            },
            "confidence_summary": _numeric_summary(symbol_confidence),
            "entry_atr_ratio_summary": atr_summary,
            "regime_volatility_ratio_summary": volatility_summary,
            "micro_body_size_pct_20_summary": body_summary,
            "micro_doji_ratio_20_summary": doji_summary,
            "micro_range_compression_ratio_20_summary": compression_summary,
            "micro_volume_burst_ratio_20_summary": burst_summary,
            "micro_volume_burst_decay_20_summary": decay_summary,
            "watchlist_pairs": _watchlist_pair_counts(symbol_primary, symbol_secondary),
        }

    return {
        "labeled_rows": labeled_rows,
        "min_rows_per_symbol": int(min_rows_per_symbol),
        "symbols_present": symbols_present,
        "missing_symbols": missing_symbols,
        "warnings": sorted(set(warnings)),
        "overall_pattern_distribution": _pattern_distribution(labeled_primary_ids, labeled_rows, limit=10),
        "overall_group_distribution": _distribution(labeled_groups, labeled_rows),
        "overall_watchlist_pairs": overall_watchlist,
        "symbol_reports": per_symbol,
    }
