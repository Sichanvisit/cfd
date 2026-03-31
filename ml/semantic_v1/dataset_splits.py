from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import pandas as pd
import numpy as np


DATASET_SPLIT_CONTRACT_VERSION = "semantic_dataset_splits_v1"
DATASET_SPLIT_HEALTH_VERSION = "semantic_dataset_split_health_v1"
ADAPTIVE_TIME_SPLIT_VERSION = "semantic_dataset_adaptive_time_split_v1"
DEFAULT_TIME_SPLIT = (0.7, 0.15, 0.15)
DEFAULT_SYMBOL_HOLDOUT_FRACTION = 0.2
DEFAULT_REGIME_HOLDOUT_FRACTION = 0.2
MIN_TRAIN_MINORITY_ROWS = 64
MIN_VALIDATION_MINORITY_ROWS = 32
MIN_TEST_MINORITY_ROWS = 64
MIN_SLICE_ROWS = 50
MIN_SLICE_MINORITY_ROWS = 8


@dataclass(frozen=True)
class SplitSummary:
    time_split_counts: dict[str, int]
    symbol_holdout_counts: dict[str, int]
    regime_holdout_counts: dict[str, int]
    time_split_strategy: str = "fixed_ratio"


@dataclass(frozen=True)
class SplitBucketHealth:
    bucket: str
    rows: int
    class_balance: dict[str, int]
    minority_rows: int
    has_both_classes: bool
    status: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class SliceHealthSummary:
    group_col: str
    status: str
    eligible_slices: int
    failing_slices: int
    unsupported_slices: int
    problems: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SplitHealthSummary:
    overall_status: str
    blocking_issues: tuple[str, ...]
    warning_issues: tuple[str, ...]
    unsupported_issues: tuple[str, ...]
    bucket_health: tuple[SplitBucketHealth, ...]
    slice_health: tuple[SliceHealthSummary, ...]


def _normalized_token(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _stable_ratio(value: Any, *, salt: str) -> float:
    token = f"{salt}|{_normalized_token(value, fallback='__missing__')}"
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    numerator = int(digest[:8], 16)
    return numerator / 0xFFFFFFFF


def build_event_ts_series(df: pd.DataFrame, *, time_col: str = "time", signal_bar_ts_col: str = "signal_bar_ts") -> pd.Series:
    base = pd.to_numeric(df.get(signal_bar_ts_col), errors="coerce")
    parsed = pd.to_datetime(df.get(time_col), errors="coerce", utc=True)
    fallback = parsed.map(lambda value: value.timestamp() if not pd.isna(value) else float("nan"))
    if isinstance(base, pd.Series):
        return base.fillna(fallback).astype(float)
    return pd.Series(fallback, index=df.index, dtype="float64")


def build_time_split_bucket(
    df: pd.DataFrame,
    *,
    event_ts_col: str = "event_ts",
    ratios: tuple[float, float, float] = DEFAULT_TIME_SPLIT,
    target_col: str | None = None,
) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="object")

    train_ratio, validation_ratio, test_ratio = ratios
    total = train_ratio + validation_ratio + test_ratio
    if total <= 0:
        raise ValueError("split ratios must sum to a positive value")

    normalized = (train_ratio / total, validation_ratio / total, test_ratio / total)
    ordered = df[[event_ts_col]].copy()
    ordered[event_ts_col] = pd.to_numeric(ordered[event_ts_col], errors="coerce").fillna(float("inf"))
    if target_col and target_col in df.columns:
        ordered[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    ordered = ordered.sort_values(event_ts_col, kind="mergesort")
    row_count = len(ordered)

    train_end = int(row_count * normalized[0])
    validation_end = int(row_count * (normalized[0] + normalized[1]))
    train_end = max(1, min(row_count, train_end))
    validation_end = max(train_end, min(row_count, validation_end))

    strategy = "fixed_ratio"
    if target_col and target_col in ordered.columns:
        adaptive = _adaptive_time_split_boundaries(
            ordered[target_col],
            row_count=row_count,
            desired_train_end=train_end,
            desired_validation_end=validation_end,
        )
        if adaptive is not None:
            train_end, validation_end = adaptive
            strategy = "adaptive_target_balance"

    bucket = pd.Series("test", index=ordered.index, dtype="object")
    bucket.iloc[:train_end] = "train"
    bucket.iloc[train_end:validation_end] = "validation"
    if validation_end >= row_count:
        bucket.iloc[-1:] = "test"
    bucket = bucket.reindex(df.index)
    bucket.attrs["time_split_strategy"] = strategy
    return bucket


def _adaptive_time_split_boundaries(
    targets: pd.Series,
    *,
    row_count: int,
    desired_train_end: int,
    desired_validation_end: int,
) -> tuple[int, int] | None:
    if row_count < 3:
        return None
    target_values = pd.to_numeric(targets, errors="coerce")
    if target_values.nunique(dropna=True) < 2:
        return None

    y = target_values.fillna(-1).astype(int).to_numpy()
    positives = np.cumsum((y == 1).astype(int))
    negatives = np.cumsum((y == 0).astype(int))
    total_pos = int(positives[-1]) if len(positives) else 0
    total_neg = int(negatives[-1]) if len(negatives) else 0
    if total_pos <= 0 or total_neg <= 0:
        return None

    step = max(1, row_count // 200)
    train_start = max(1, min(row_count - 2, int(row_count * 0.55)))
    train_stop = max(train_start + 1, min(row_count - 2, int(row_count * 0.8)))
    val_start_floor = int(row_count * 0.7)
    val_stop = max(val_start_floor + 1, min(row_count - 1, int(row_count * 0.95)))

    def _slice_counts(start: int, end: int) -> tuple[int, int]:
        if end <= start:
            return (0, 0)
        pos = int(positives[end - 1] - (positives[start - 1] if start > 0 else 0))
        neg = int(negatives[end - 1] - (negatives[start - 1] if start > 0 else 0))
        return pos, neg

    best: tuple[Any, int, int] | None = None
    for train_end in range(train_start, train_stop + 1, step):
        train_pos, train_neg = _slice_counts(0, train_end)
        train_minority = min(train_pos, train_neg) if train_pos > 0 and train_neg > 0 else 0

        validation_start = max(train_end + 1, val_start_floor)
        for validation_end in range(validation_start, val_stop + 1, step):
            val_pos, val_neg = _slice_counts(train_end, validation_end)
            test_pos = total_pos - int(positives[validation_end - 1])
            test_neg = total_neg - int(negatives[validation_end - 1])
            if min(val_pos, val_neg, test_pos, test_neg) < 0:
                continue
            val_minority = min(val_pos, val_neg) if val_pos > 0 and val_neg > 0 else 0
            test_minority = min(test_pos, test_neg) if test_pos > 0 and test_neg > 0 else 0

            score = (
                1 if train_minority >= MIN_TRAIN_MINORITY_ROWS else 0,
                1 if val_minority >= MIN_VALIDATION_MINORITY_ROWS else 0,
                1 if test_minority >= MIN_TEST_MINORITY_ROWS else 0,
                train_minority + val_minority + test_minority,
                -(abs(train_end - desired_train_end) + abs(validation_end - desired_validation_end)),
            )
            if best is None or score > best[0]:
                best = (score, train_end, validation_end)

    if best is None:
        return None

    _, train_end, validation_end = best
    train_pos, train_neg = _slice_counts(0, train_end)
    val_pos, val_neg = _slice_counts(train_end, validation_end)
    test_pos = total_pos - int(positives[validation_end - 1])
    test_neg = total_neg - int(negatives[validation_end - 1])
    if not (
        min(train_pos, train_neg) >= MIN_TRAIN_MINORITY_ROWS
        and min(val_pos, val_neg) >= MIN_VALIDATION_MINORITY_ROWS
        and min(test_pos, test_neg) >= MIN_TEST_MINORITY_ROWS
    ):
        return None
    return train_end, validation_end


def build_holdout_bucket(
    series: pd.Series,
    *,
    salt: str,
    holdout_fraction: float,
    target_series: pd.Series | None = None,
) -> pd.Series:
    if series.empty:
        return pd.Series(dtype="object")
    if holdout_fraction <= 0:
        return pd.Series("train", index=series.index, dtype="object")

    normalized = series.apply(lambda value: _normalized_token(value, fallback="__missing__")).astype("object")
    unique_tokens = sorted({str(value) for value in normalized.tolist()})
    if len(unique_tokens) <= 1:
        return pd.Series("train", index=series.index, dtype="object")

    selection_tokens = unique_tokens
    if target_series is not None and len(target_series) == len(normalized):
        target_frame = pd.DataFrame(
            {
                "token": normalized.astype(str),
                "target": pd.to_numeric(target_series, errors="coerce"),
            }
        )
        eligible_tokens = sorted(
            {
                str(token)
                for token, group in target_frame.groupby("token", dropna=False)
                if group["target"].dropna().nunique() >= 2
            }
        )
        if eligible_tokens:
            selection_tokens = eligible_tokens

    desired_holdout = int(np.ceil(len(unique_tokens) * float(holdout_fraction)))
    desired_holdout = max(1, desired_holdout)
    desired_holdout = min(max(1, len(selection_tokens) - 1), desired_holdout) if len(selection_tokens) > 1 else 1

    ranked_tokens = sorted(selection_tokens, key=lambda token: (_stable_ratio(token, salt=salt), token))
    holdout_tokens = set(ranked_tokens[:desired_holdout])
    return normalized.apply(lambda value: "holdout" if str(value) in holdout_tokens else "train").astype("object")


def attach_split_columns(
    df: pd.DataFrame,
    *,
    time_col: str = "time",
    signal_bar_ts_col: str = "signal_bar_ts",
    symbol_col: str = "symbol",
    regime_col: str = "preflight_regime",
    time_split: tuple[float, float, float] = DEFAULT_TIME_SPLIT,
    symbol_holdout_fraction: float = DEFAULT_SYMBOL_HOLDOUT_FRACTION,
    regime_holdout_fraction: float = DEFAULT_REGIME_HOLDOUT_FRACTION,
    target_col: str | None = None,
) -> tuple[pd.DataFrame, SplitSummary]:
    out = df.copy()
    out["event_ts"] = build_event_ts_series(out, time_col=time_col, signal_bar_ts_col=signal_bar_ts_col)
    time_split_bucket = build_time_split_bucket(out, event_ts_col="event_ts", ratios=time_split, target_col=target_col)
    out["time_split_bucket"] = time_split_bucket
    out["symbol_holdout_bucket"] = build_holdout_bucket(
        out.get(symbol_col, pd.Series(index=out.index, dtype="object")),
        salt="symbol_holdout",
        holdout_fraction=symbol_holdout_fraction,
        target_series=out.get(target_col) if target_col and target_col in out.columns else None,
    )
    out["regime_holdout_bucket"] = build_holdout_bucket(
        out.get(regime_col, pd.Series(index=out.index, dtype="object")),
        salt="regime_holdout",
        holdout_fraction=regime_holdout_fraction,
        target_series=out.get(target_col) if target_col and target_col in out.columns else None,
    )
    out["is_symbol_holdout"] = (out["symbol_holdout_bucket"] == "holdout").astype(int)
    out["is_regime_holdout"] = (out["regime_holdout_bucket"] == "holdout").astype(int)

    summary = SplitSummary(
        time_split_counts={str(key): int(value) for key, value in out["time_split_bucket"].value_counts(dropna=False).to_dict().items()},
        symbol_holdout_counts={str(key): int(value) for key, value in out["symbol_holdout_bucket"].value_counts(dropna=False).to_dict().items()},
        regime_holdout_counts={str(key): int(value) for key, value in out["regime_holdout_bucket"].value_counts(dropna=False).to_dict().items()},
        time_split_strategy=str(getattr(time_split_bucket, "attrs", {}).get("time_split_strategy", "fixed_ratio") or "fixed_ratio"),
    )
    return out, summary


def _class_balance(frame: pd.DataFrame, *, target_col: str) -> dict[str, int]:
    if frame.empty or target_col not in frame.columns:
        return {}
    counts = frame[target_col].value_counts(dropna=False).to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _minority_count(class_balance: dict[str, int]) -> int:
    if not class_balance:
        return 0
    return int(min(class_balance.values()))


def _bucket_threshold(bucket: str) -> int:
    normalized = str(bucket or "").strip().lower()
    if normalized == "train":
        return MIN_TRAIN_MINORITY_ROWS
    if normalized == "validation":
        return MIN_VALIDATION_MINORITY_ROWS
    return MIN_TEST_MINORITY_ROWS


def _bucket_health(frame: pd.DataFrame, *, bucket: str, target_col: str) -> SplitBucketHealth:
    class_balance = _class_balance(frame, target_col=target_col)
    rows = int(len(frame))
    minority_rows = _minority_count(class_balance)
    has_both_classes = len(class_balance) >= 2
    issues: list[str] = []

    if rows <= 0:
        issues.append("empty_split_bucket")
    if not has_both_classes:
        issues.append("single_class_split_bucket")
    min_required = _bucket_threshold(bucket)
    if has_both_classes and minority_rows < min_required:
        issues.append(f"minority_class_below_minimum:{minority_rows}<{min_required}")

    status = "healthy" if not issues else "fail"
    return SplitBucketHealth(
        bucket=str(bucket),
        rows=rows,
        class_balance=class_balance,
        minority_rows=minority_rows,
        has_both_classes=has_both_classes,
        status=status,
        issues=tuple(issues),
    )


def _slice_health(frame: pd.DataFrame, *, group_col: str, target_col: str) -> SliceHealthSummary:
    if frame.empty or group_col not in frame.columns:
        return SliceHealthSummary(
            group_col=group_col,
            status="insufficient",
            eligible_slices=0,
            failing_slices=0,
            unsupported_slices=0,
            problems=tuple(),
        )

    problems: list[dict[str, Any]] = []
    unsupported_slices = 0
    eligible_slices = 0
    for key, group in frame.groupby(frame[group_col].fillna("__missing__"), dropna=False):
        rows = int(len(group))
        if rows < MIN_SLICE_ROWS:
            continue
        eligible_slices += 1
        class_balance = _class_balance(group, target_col=target_col)
        minority_rows = _minority_count(class_balance)
        if len(class_balance) < 2 or minority_rows <= 1:
            unsupported_slices += 1
            problems.append(
                {
                    "slice": str(key),
                    "rows": rows,
                    "class_balance": class_balance,
                    "minority_rows": minority_rows,
                    "issue_kind": "unsupported_sparse_slice",
                }
            )
        elif minority_rows < MIN_SLICE_MINORITY_ROWS:
            problems.append(
                {
                    "slice": str(key),
                    "rows": rows,
                    "class_balance": class_balance,
                    "minority_rows": minority_rows,
                    "issue_kind": "minority_below_minimum",
                }
            )

    if eligible_slices <= 0:
        status = "insufficient"
    elif problems and unsupported_slices == len(problems):
        status = "unsupported"
    elif problems:
        status = "warning"
    else:
        status = "healthy"

    return SliceHealthSummary(
        group_col=group_col,
        status=status,
        eligible_slices=eligible_slices,
        failing_slices=len(problems) - unsupported_slices,
        unsupported_slices=unsupported_slices,
        problems=tuple(problems),
    )


def assess_split_health(
    df: pd.DataFrame,
    *,
    target_col: str,
    split_col: str = "time_split_bucket",
    slice_cols: tuple[str, ...] = ("symbol", "preflight_regime", "setup_id"),
) -> SplitHealthSummary:
    if df.empty or target_col not in df.columns:
        return SplitHealthSummary(
            overall_status="fail",
            blocking_issues=("empty_dataset",),
            warning_issues=tuple(),
            unsupported_issues=tuple(),
            bucket_health=tuple(),
            slice_health=tuple(),
        )

    bucket_health_rows: list[SplitBucketHealth] = []
    blocking_issues: list[str] = []
    for bucket in ("train", "validation", "test"):
        bucket_frame = df[df[split_col] == bucket].copy() if split_col in df.columns else df.copy()
        health = _bucket_health(bucket_frame, bucket=bucket, target_col=target_col)
        bucket_health_rows.append(health)
        if health.status == "fail":
            blocking_issues.extend(f"{bucket}:{issue}" for issue in health.issues)

    test_frame = df[df[split_col] == "test"].copy() if split_col in df.columns else df.copy()
    slice_health_rows = tuple(_slice_health(test_frame, group_col=group_col, target_col=target_col) for group_col in slice_cols)
    warning_issues: list[str] = []
    unsupported_issues: list[str] = []
    for summary in slice_health_rows:
        if summary.status == "warning":
            warning_issues.append(f"{summary.group_col}:failing_slices={summary.failing_slices}/{summary.eligible_slices}")
        elif summary.status == "unsupported":
            unsupported_issues.append(
                f"{summary.group_col}:unsupported_slices={summary.unsupported_slices}/{summary.eligible_slices}"
            )

    overall_status = "fail" if blocking_issues else "warning" if warning_issues else "healthy"
    return SplitHealthSummary(
        overall_status=overall_status,
        blocking_issues=tuple(blocking_issues),
        warning_issues=tuple(warning_issues),
        unsupported_issues=tuple(unsupported_issues),
        bucket_health=tuple(bucket_health_rows),
        slice_health=slice_health_rows,
    )


def _event_ts_range(frame: pd.DataFrame, *, event_ts_col: str = "event_ts") -> dict[str, Any]:
    if frame.empty or event_ts_col not in frame.columns:
        return {
            "rows": int(len(frame)),
            "start_event_ts": None,
            "end_event_ts": None,
        }
    series = pd.to_numeric(frame[event_ts_col], errors="coerce").dropna()
    if series.empty:
        return {
            "rows": int(len(frame)),
            "start_event_ts": None,
            "end_event_ts": None,
        }
    return {
        "rows": int(len(frame)),
        "start_event_ts": int(series.min()),
        "end_event_ts": int(series.max()),
    }


def _value_counts_map(frame: pd.DataFrame, *, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("__missing__").astype(str).str.strip()
    series = series.replace("", "__missing__")
    counts = series.value_counts(dropna=False).to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _class_imbalance_ratio(class_balance: dict[str, int]) -> float | None:
    if not class_balance:
        return None
    values = [int(v) for v in class_balance.values() if int(v) >= 0]
    if not values:
        return None
    total = int(sum(values))
    if total <= 0:
        return None
    majority = int(max(values))
    minority = int(min(values))
    return round(float((majority - minority) / total), 6)


def _bucket_coverage_payload(
    df: pd.DataFrame,
    *,
    split_col: str = "time_split_bucket",
    event_ts_col: str = "event_ts",
    symbol_col: str = "symbol",
    regime_col: str = "preflight_regime",
    target_col: str,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for bucket in ("train", "validation", "test"):
        frame = df[df[split_col] == bucket].copy() if split_col in df.columns else df.copy()
        class_balance = _class_balance(frame, target_col=target_col)
        payload.append(
            {
                "bucket": str(bucket),
                **_event_ts_range(frame, event_ts_col=event_ts_col),
                "class_balance": class_balance,
                "class_imbalance_ratio": _class_imbalance_ratio(class_balance),
                "symbol_counts": _value_counts_map(frame, column=symbol_col),
                "regime_counts": _value_counts_map(frame, column=regime_col),
            }
        )
    return payload


def _holdout_health_payload(
    df: pd.DataFrame,
    *,
    holdout_col: str,
    target_col: str,
    label: str,
) -> dict[str, Any]:
    if holdout_col not in df.columns:
        return {
            "label": str(label),
            "bucket_col": str(holdout_col),
            "status": "missing",
            "train_rows": int(len(df)),
            "holdout_rows": 0,
            "class_balance": {},
            "minority_rows": 0,
            "issues": ["missing_holdout_column"],
        }

    holdout_frame = df[df[holdout_col] == "holdout"].copy()
    train_frame = df[df[holdout_col] != "holdout"].copy()
    class_balance = _class_balance(holdout_frame, target_col=target_col)
    minority_rows = _minority_count(class_balance)
    issues: list[str] = []

    if holdout_frame.empty:
        issues.append("empty_holdout_bucket")
    if holdout_frame.shape[0] > 0 and len(class_balance) < 2:
        issues.append("single_class_holdout_bucket")
    if holdout_frame.shape[0] > 0 and len(class_balance) >= 2 and minority_rows < MIN_SLICE_MINORITY_ROWS:
        issues.append(f"holdout_minority_below_minimum:{minority_rows}<{MIN_SLICE_MINORITY_ROWS}")

    if not issues:
        status = "healthy"
    elif "empty_holdout_bucket" in issues:
        status = "warning"
    else:
        status = "warning"

    return {
        "label": str(label),
        "bucket_col": str(holdout_col),
        "status": str(status),
        "train_rows": int(len(train_frame)),
        "holdout_rows": int(len(holdout_frame)),
        "class_balance": class_balance,
        "class_imbalance_ratio": _class_imbalance_ratio(class_balance),
        "minority_rows": int(minority_rows),
        "issues": list(issues),
    }


def build_split_health_payload(
    df: pd.DataFrame,
    *,
    target_col: str,
    split_col: str = "time_split_bucket",
    slice_cols: tuple[str, ...] = ("symbol", "preflight_regime", "setup_id"),
    event_ts_col: str = "event_ts",
    symbol_col: str = "symbol",
    regime_col: str = "preflight_regime",
    symbol_holdout_col: str = "symbol_holdout_bucket",
    regime_holdout_col: str = "regime_holdout_bucket",
) -> dict[str, Any]:
    summary = assess_split_health(df, target_col=target_col, split_col=split_col, slice_cols=slice_cols)
    return {
        "version": DATASET_SPLIT_HEALTH_VERSION,
        "overall_status": summary.overall_status,
        "blocking_issues": list(summary.blocking_issues),
        "warning_issues": list(summary.warning_issues),
        "unsupported_issues": list(summary.unsupported_issues),
        "bucket_health": [
            {
                "bucket": item.bucket,
                "rows": item.rows,
                "class_balance": item.class_balance,
                "class_imbalance_ratio": _class_imbalance_ratio(item.class_balance),
                "minority_rows": item.minority_rows,
                "has_both_classes": item.has_both_classes,
                "status": item.status,
                "issues": list(item.issues),
            }
            for item in summary.bucket_health
        ],
        "slice_health": [
            {
                "group_col": item.group_col,
                "status": item.status,
                "eligible_slices": item.eligible_slices,
                "failing_slices": item.failing_slices,
                "unsupported_slices": item.unsupported_slices,
                "problems": list(item.problems),
            }
            for item in summary.slice_health
        ],
        "bucket_coverage": _bucket_coverage_payload(
            df,
            split_col=split_col,
            event_ts_col=event_ts_col,
            symbol_col=symbol_col,
            regime_col=regime_col,
            target_col=target_col,
        ),
        "holdout_health": [
            _holdout_health_payload(df, holdout_col=symbol_holdout_col, target_col=target_col, label="symbol"),
            _holdout_health_payload(df, holdout_col=regime_holdout_col, target_col=target_col, label="regime"),
        ],
        "time_split_strategy": str(
            df.get(split_col, pd.Series(dtype="object")).attrs.get("time_split_strategy", "unknown")
            if isinstance(df.get(split_col), pd.Series)
            else "unknown"
        ),
        "promotion_blocked": summary.overall_status == "fail",
    }
