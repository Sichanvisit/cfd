"""Pilot baseline training for teacher-pattern state25 labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler

from backend.services.teacher_pattern_experiment_seed import build_teacher_pattern_experiment_seed_report


DEFAULT_MIN_SEED_ROWS = 1000
DEFAULT_PATTERN_MIN_SUPPORT = 5
DEFAULT_WAIT_QUALITY_MIN_SUPPORT = 3
DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT = 25
DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT = 5
DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT = 8
DEFAULT_BELIEF_OUTCOME_MIN_ROWS = 40
DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT = 8
DEFAULT_BARRIER_OUTCOME_MIN_ROWS = 40
DEFAULT_OUTPUT_DIR = Path("models") / "teacher_pattern_state25_pilot"
DEFAULT_RANDOM_STATE = 42
ENTRY_WAIT_QUALITY_EXCLUDED_LABELS = {"", "insufficient_evidence"}
FORECAST_OUTCOME_EXCLUDED_STATUSES = {"", "insufficient_future_bars"}

BASELINE_CATEGORICAL_COLUMNS = [
    "symbol",
    "direction",
    "entry_stage",
    "entry_setup_id",
    "entry_wait_state",
    "regime_at_entry",
    "entry_session_name",
    "entry_weekday",
    "regime_name",
    "micro_breakout_readiness_state",
    "micro_reversal_risk_state",
    "micro_participation_state",
    "micro_gap_context_state",
]

BASELINE_NUMERIC_COLUMNS = [
    "entry_score",
    "contra_score_at_entry",
    "entry_model_confidence",
    "entry_h1_context_score",
    "entry_m1_trigger_score",
    "entry_topdown_align_count",
    "entry_topdown_conflict_count",
    "entry_topdown_seen_count",
    "entry_session_threshold_mult",
    "entry_atr_ratio",
    "entry_atr_threshold_mult",
    "ind_rsi",
    "ind_adx",
    "ind_plus_di",
    "ind_minus_di",
    "ind_disparity",
    "regime_volume_ratio",
    "regime_volatility_ratio",
    "regime_spread_ratio",
    "regime_buy_multiplier",
    "regime_sell_multiplier",
    "micro_body_size_pct_20",
    "micro_doji_ratio_20",
    "micro_same_color_run_current",
    "micro_same_color_run_max_20",
    "micro_range_compression_ratio_20",
    "micro_volume_burst_ratio_20",
    "micro_volume_burst_decay_20",
    "micro_gap_fill_progress",
    "signal_age_sec",
    "bar_age_sec",
    "missing_feature_count",
    "data_completeness_ratio",
    "used_fallback_count",
]


def _series(frame: pd.DataFrame, column: str, default: Any) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def _to_int_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _to_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _ensure_feature_columns(df: pd.DataFrame, categorical_cols: list[str], numeric_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in categorical_cols:
        if column not in out.columns:
            out[column] = ""
    for column in numeric_cols:
        if column not in out.columns:
            out[column] = np.nan
    return out


def _is_all_missing(series: pd.Series) -> bool:
    if str(series.dtype) in {"object", "string", "category"}:
        return bool((series.isna() | series.astype(str).str.strip().eq("")).all())
    return bool(series.isna().all())


def _prune_all_missing_columns(
    frame: pd.DataFrame,
    *,
    categorical_cols: list[str],
    numeric_cols: list[str],
) -> tuple[list[str], list[str]]:
    kept_cat = [column for column in categorical_cols if column in frame.columns and not _is_all_missing(frame[column])]
    kept_num = [column for column in numeric_cols if column in frame.columns and not _is_all_missing(frame[column])]
    return kept_cat, kept_num


def _build_preprocessor(categorical_cols: list[str], numeric_cols: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_cols,
            ),
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric_cols,
            ),
        ]
    )


def _build_model_pipeline(categorical_cols: list[str], numeric_cols: list[str]) -> Pipeline:
    return Pipeline(
        [
            ("pre", _build_preprocessor(categorical_cols, numeric_cols)),
            (
                "model",
                LogisticRegression(
                    solver="lbfgs",
                    max_iter=2000,
                    random_state=DEFAULT_RANDOM_STATE,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def _can_stratify(target: pd.Series) -> bool:
    counts = target.value_counts()
    return bool(not counts.empty and (counts >= 2).all())


def _split_train_val_test(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    random_state: int,
) -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    stratify_first = target if _can_stratify(target) else None
    x_train, x_temp, y_train, y_temp = train_test_split(
        features,
        target,
        test_size=0.30,
        random_state=random_state,
        stratify=stratify_first,
    )

    stratify_second = y_temp if _can_stratify(y_temp) else None
    x_val, x_test, y_val, y_test = train_test_split(
        x_temp,
        y_temp,
        test_size=0.50,
        random_state=random_state,
        stratify=stratify_second,
    )

    return {
        "train": (x_train, y_train),
        "val": (x_val, y_val),
        "test": (x_test, y_test),
    }


def _evaluate_predictions(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    y_true_series = pd.Series(y_true).astype(str)
    y_pred_series = pd.Series(y_pred, index=y_true_series.index).astype(str)
    labels = sorted(y_true_series.unique().tolist())
    if labels:
        recalls = [
            float((y_pred_series[y_true_series == label] == label).mean())
            for label in labels
        ]
        balanced_accuracy = float(np.mean(recalls))
    else:
        balanced_accuracy = 0.0
    return {
        "accuracy": float(accuracy_score(y_true_series, y_pred_series)),
        "macro_f1": float(f1_score(y_true_series, y_pred_series, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true_series, y_pred_series, average="weighted", zero_division=0)),
        "balanced_accuracy": balanced_accuracy,
    }


def _top_confusions(y_true: pd.Series, y_pred: np.ndarray, *, limit: int = 10) -> list[dict[str, Any]]:
    labels = sorted({*pd.Series(y_true).astype(str).tolist(), *pd.Series(y_pred).astype(str).tolist()})
    if len(labels) <= 1:
        return []
    matrix = confusion_matrix(pd.Series(y_true).astype(str), pd.Series(y_pred).astype(str), labels=labels)
    rows: list[dict[str, Any]] = []
    total = int(matrix.sum())
    for i, true_label in enumerate(labels):
        for j, pred_label in enumerate(labels):
            if i == j:
                continue
            count = int(matrix[i, j])
            if count <= 0:
                continue
            rows.append(
                {
                    "true_label": true_label,
                    "pred_label": pred_label,
                    "count": count,
                    "ratio": float(count / total) if total else 0.0,
                }
            )
    rows.sort(key=lambda row: (-int(row["count"]), str(row["true_label"]), str(row["pred_label"])))
    return rows[:limit]


def _class_support(series: pd.Series) -> dict[str, int]:
    counts = pd.Series(series).astype(str).value_counts().sort_index()
    return {str(label): int(count) for label, count in counts.items()}


def _supported_text_classes(series: pd.Series, *, min_support: int) -> tuple[list[str], list[str]]:
    counts = pd.Series(series).astype(str).value_counts()
    supported = sorted(str(label) for label, count in counts.items() if int(count) >= int(min_support))
    excluded = sorted(str(label) for label, count in counts.items() if int(count) < int(min_support))
    return supported, excluded


def _fit_task(
    frame: pd.DataFrame,
    *,
    target_column: str,
    categorical_cols: list[str],
    numeric_cols: list[str],
    random_state: int,
) -> dict[str, Any]:
    active_categorical_cols, active_numeric_cols = _prune_all_missing_columns(
        frame,
        categorical_cols=list(categorical_cols),
        numeric_cols=list(numeric_cols),
    )
    features = frame[active_categorical_cols + active_numeric_cols].copy()
    target = frame[target_column].copy()
    if pd.Series(target).nunique(dropna=True) < 2:
        dummy = DummyClassifier(strategy="most_frequent")
        dummy.fit(features, target)
        return {
            "model": dummy,
            "rows": int(len(frame)),
            "split": {"train_rows": int(len(frame)), "val_rows": 0, "test_rows": 0},
            "class_support": {
                "train": _class_support(target),
                "val": {},
                "test": {},
                "all": _class_support(target),
            },
            "feature_columns": {
                "categorical": list(active_categorical_cols),
                "numeric": list(active_numeric_cols),
            },
            "model_metrics": {},
            "dummy_metrics": {},
            "top_confusions": [],
            "skipped": True,
        }

    splits = _split_train_val_test(features, target, random_state=random_state)

    x_train, y_train = splits["train"]
    x_val, y_val = splits["val"]
    x_test, y_test = splits["test"]

    model = _build_model_pipeline(active_categorical_cols, active_numeric_cols)
    model.fit(x_train, y_train)

    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(x_train, y_train)

    val_pred = model.predict(x_val)
    test_pred = model.predict(x_test)
    dummy_val_pred = dummy.predict(x_val)
    dummy_test_pred = dummy.predict(x_test)

    model_metrics = {
        "val": _evaluate_predictions(y_val, val_pred),
        "test": _evaluate_predictions(y_test, test_pred),
    }
    dummy_metrics = {
        "val": _evaluate_predictions(y_val, dummy_val_pred),
        "test": _evaluate_predictions(y_test, dummy_test_pred),
    }

    final_model = _build_model_pipeline(active_categorical_cols, active_numeric_cols)
    final_model.fit(pd.concat([x_train, x_val], axis=0), pd.concat([y_train, y_val], axis=0))

    return {
        "model": final_model,
        "rows": int(len(frame)),
        "split": {
            "train_rows": int(len(x_train)),
            "val_rows": int(len(x_val)),
            "test_rows": int(len(x_test)),
        },
        "class_support": {
            "train": _class_support(y_train),
            "val": _class_support(y_val),
            "test": _class_support(y_test),
            "all": _class_support(target),
        },
        "feature_columns": {
            "categorical": list(active_categorical_cols),
            "numeric": list(active_numeric_cols),
        },
        "model_metrics": model_metrics,
        "dummy_metrics": dummy_metrics,
        "top_confusions": _top_confusions(y_test, test_pred),
        "skipped": False,
    }


def _save_bundle(output_dir: Path, payload: dict[str, Any], report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, output_dir / "teacher_pattern_pilot_baseline.joblib")
    (output_dir / "teacher_pattern_pilot_baseline_metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_teacher_pattern_pilot_baseline_report(
    frame: pd.DataFrame | None,
    *,
    min_seed_rows: int = DEFAULT_MIN_SEED_ROWS,
    pattern_min_support: int = DEFAULT_PATTERN_MIN_SUPPORT,
    wait_quality_min_support: int = DEFAULT_WAIT_QUALITY_MIN_SUPPORT,
    economic_target_min_support: int = DEFAULT_ECONOMIC_TARGET_MIN_SUPPORT,
    forecast_outcome_min_support: int = DEFAULT_FORECAST_OUTCOME_MIN_SUPPORT,
    belief_outcome_min_support: int = DEFAULT_BELIEF_OUTCOME_MIN_SUPPORT,
    belief_outcome_min_rows: int = DEFAULT_BELIEF_OUTCOME_MIN_ROWS,
    barrier_outcome_min_support: int = DEFAULT_BARRIER_OUTCOME_MIN_SUPPORT,
    barrier_outcome_min_rows: int = DEFAULT_BARRIER_OUTCOME_MIN_ROWS,
    random_state: int = DEFAULT_RANDOM_STATE,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    dataset = _ensure_feature_columns(dataset, BASELINE_CATEGORICAL_COLUMNS, BASELINE_NUMERIC_COLUMNS)
    active_categorical_cols, active_numeric_cols = _prune_all_missing_columns(
        dataset,
        categorical_cols=list(BASELINE_CATEGORICAL_COLUMNS),
        numeric_cols=list(BASELINE_NUMERIC_COLUMNS),
    )

    seed_report = build_teacher_pattern_experiment_seed_report(
        dataset,
        min_seed_rows=min_seed_rows,
        economic_primary_min_support=economic_target_min_support,
        economic_loss_min_support=economic_target_min_support,
        economic_bucket_min_support=economic_target_min_support,
    )
    primary_ids = _to_int_series(_series(dataset, "teacher_pattern_id", 0))
    groups = _to_text_series(_series(dataset, "teacher_pattern_group", ""))
    entry_wait_quality = _to_text_series(_series(dataset, "entry_wait_quality_label", "")).str.lower()
    learning_total_label = _to_text_series(_series(dataset, "learning_total_label", "")).str.lower()
    forecast_transition_status = _to_text_series(_series(dataset, "forecast_transition_outcome_status", "")).str.lower()
    forecast_management_status = _to_text_series(_series(dataset, "forecast_management_outcome_status", "")).str.lower()
    belief_outcome_label = _to_text_series(_series(dataset, "belief_outcome_label", "")).str.lower()
    belief_label_confidence = _to_text_series(_series(dataset, "belief_label_confidence", "")).str.lower()
    barrier_outcome_label = _to_text_series(_series(dataset, "barrier_outcome_label", "")).str.lower()
    barrier_label_confidence = _to_text_series(_series(dataset, "barrier_label_confidence", "")).str.lower()

    labeled_mask = primary_ids > 0
    labeled = dataset.loc[labeled_mask].copy()
    labeled["teacher_pattern_id"] = primary_ids.loc[labeled_mask]
    labeled["teacher_pattern_group"] = groups.loc[labeled_mask]

    if labeled.empty:
        return {
            "seed_summary": seed_report,
            "baseline_ready": False,
            "baseline_warnings": ["no_labeled_rows"],
            "feature_columns": {
                "categorical": list(BASELINE_CATEGORICAL_COLUMNS),
                "numeric": list(BASELINE_NUMERIC_COLUMNS),
            },
            "wait_quality_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "min_support": int(wait_quality_min_support),
                "target_rows": 0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict(seed_report.get("entry_wait_quality_coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "economic_target_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "primary_target": "learning_total_label",
                "min_support": int(economic_target_min_support),
                "target_rows": 0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict((seed_report.get("economic_target_summary", {}) or {}).get("coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "forecast_transition_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "target_column": "forecast_transition_outcome_status",
                "min_support": int(forecast_outcome_min_support),
                "target_rows": 0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict(seed_report.get("forecast_state25_coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "forecast_management_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "target_column": "forecast_management_outcome_status",
                "min_support": int(forecast_outcome_min_support),
                "target_rows": 0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict(seed_report.get("forecast_state25_coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "belief_outcome_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "target_column": "belief_outcome_label",
                "min_support": int(belief_outcome_min_support),
                "min_ready_rows": int(belief_outcome_min_rows),
                "target_rows": 0,
                "high_medium_confidence_rows": 0,
                "usable_confidence_rows": 0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict(seed_report.get("belief_outcome_coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "barrier_outcome_integration": {
                "mode": "auxiliary_target",
                "ready": False,
                "target_column": "barrier_outcome_label",
                "min_support": int(barrier_outcome_min_support),
                "min_ready_rows": int(barrier_outcome_min_rows),
                "target_rows": 0,
                "high_medium_confidence_rows": 0,
                "usable_confidence_rows": 0,
                "weak_usable_rows": 0,
                "weak_usable_share": 0.0,
                "weak_to_medium_conversion_rate": 0.0,
                "supported_labels": [],
                "excluded_labels": [],
                "notes": ["no_labeled_rows"],
                "coverage": dict(seed_report.get("barrier_outcome_coverage", {})),
                "feature_columns": {
                    "categorical": list(active_categorical_cols),
                    "numeric": list(active_numeric_cols),
                },
            },
            "tasks": {
                "belief_outcome_task": {
                    "rows": 0,
                    "target_rows": 0,
                    "high_medium_confidence_rows": 0,
                    "usable_confidence_rows": 0,
                    "supported_labels": [],
                    "excluded_labels": [],
                    "feature_columns": {
                        "categorical": list(active_categorical_cols),
                        "numeric": list(active_numeric_cols),
                    },
                    "skipped": True,
                },
                "barrier_outcome_task": {
                    "rows": 0,
                    "target_rows": 0,
                    "high_medium_confidence_rows": 0,
                    "usable_confidence_rows": 0,
                    "weak_usable_rows": 0,
                    "weak_usable_share": 0.0,
                    "weak_to_medium_conversion_rate": 0.0,
                    "supported_labels": [],
                    "excluded_labels": [],
                    "feature_columns": {
                        "categorical": list(active_categorical_cols),
                        "numeric": list(active_numeric_cols),
                    },
                    "skipped": True,
                },
                "forecast_transition_task": {
                    "rows": 0,
                    "target_rows": 0,
                    "supported_labels": [],
                    "excluded_labels": [],
                    "feature_columns": {
                        "categorical": list(active_categorical_cols),
                        "numeric": list(active_numeric_cols),
                    },
                    "skipped": True,
                },
                "forecast_management_task": {
                    "rows": 0,
                    "target_rows": 0,
                    "supported_labels": [],
                    "excluded_labels": [],
                    "feature_columns": {
                        "categorical": list(active_categorical_cols),
                        "numeric": list(active_numeric_cols),
                    },
                    "skipped": True,
                },
            },
        }

    baseline_warnings: list[str] = []
    if int(seed_report["labeled_rows"]) < int(min_seed_rows):
        baseline_warnings.append("pilot_seed_shortfall")

    group_rows = labeled[labeled["teacher_pattern_group"] != ""].copy()
    group_task = _fit_task(
        group_rows,
        target_column="teacher_pattern_group",
        categorical_cols=list(active_categorical_cols),
        numeric_cols=list(active_numeric_cols),
        random_state=random_state,
    )
    if group_task.get("skipped"):
        baseline_warnings.append("insufficient_group_classes")

    pattern_counts = labeled["teacher_pattern_id"].value_counts()
    supported_pattern_ids = sorted(int(pattern_id) for pattern_id, count in pattern_counts.items() if int(count) >= int(pattern_min_support))
    excluded_pattern_ids = sorted(int(pattern_id) for pattern_id, count in pattern_counts.items() if int(count) < int(pattern_min_support))
    pattern_rows = labeled[labeled["teacher_pattern_id"].isin(supported_pattern_ids)].copy()
    if len(supported_pattern_ids) < 2 or pattern_rows.empty:
        baseline_warnings.append("insufficient_supported_pattern_classes")
        pattern_task: dict[str, Any] = {
            "rows": int(len(pattern_rows)),
            "supported_pattern_ids": supported_pattern_ids,
            "excluded_pattern_ids": excluded_pattern_ids,
            "skipped": True,
        }
        pattern_model_bundle = None
    else:
        pattern_task = _fit_task(
            pattern_rows,
            target_column="teacher_pattern_id",
            categorical_cols=list(active_categorical_cols),
            numeric_cols=list(active_numeric_cols),
            random_state=random_state,
        )
        pattern_task["supported_pattern_ids"] = supported_pattern_ids
        pattern_task["excluded_pattern_ids"] = excluded_pattern_ids
        pattern_model_bundle = pattern_task.pop("model")

    wait_quality_rows = labeled[
        (entry_wait_quality.loc[labeled.index] != "")
        & (~entry_wait_quality.loc[labeled.index].isin(ENTRY_WAIT_QUALITY_EXCLUDED_LABELS))
    ].copy()
    wait_quality_rows["entry_wait_quality_label"] = entry_wait_quality.loc[wait_quality_rows.index]
    wait_quality_supported_labels, wait_quality_excluded_labels = _supported_text_classes(
        wait_quality_rows["entry_wait_quality_label"] if not wait_quality_rows.empty else pd.Series(dtype=str),
        min_support=wait_quality_min_support,
    )
    wait_quality_notes: list[str] = []
    if wait_quality_rows.empty:
        wait_quality_notes.append("no_entry_wait_quality_rows")
    elif len(wait_quality_supported_labels) < 2:
        wait_quality_notes.append("insufficient_entry_wait_quality_classes")

    wait_quality_feature_categorical = list(active_categorical_cols)
    wait_quality_feature_numeric = list(active_numeric_cols)
    wait_quality_supported_rows = wait_quality_rows[
        wait_quality_rows["entry_wait_quality_label"].isin(wait_quality_supported_labels)
    ].copy()
    if len(wait_quality_supported_labels) < 2 or wait_quality_supported_rows.empty:
        wait_quality_task: dict[str, Any] = {
            "rows": int(len(wait_quality_supported_rows)),
            "target_rows": int(len(wait_quality_rows)),
            "supported_labels": wait_quality_supported_labels,
            "excluded_labels": wait_quality_excluded_labels,
            "feature_columns": {
                "categorical": list(wait_quality_feature_categorical),
                "numeric": list(wait_quality_feature_numeric),
            },
            "skipped": True,
        }
        wait_quality_model_bundle = None
    else:
        wait_quality_task = _fit_task(
            wait_quality_supported_rows,
            target_column="entry_wait_quality_label",
            categorical_cols=list(wait_quality_feature_categorical),
            numeric_cols=list(wait_quality_feature_numeric),
            random_state=random_state,
        )
        wait_quality_task["target_rows"] = int(len(wait_quality_rows))
        wait_quality_task["supported_labels"] = wait_quality_supported_labels
        wait_quality_task["excluded_labels"] = wait_quality_excluded_labels
        wait_quality_model_bundle = wait_quality_task.pop("model")

    economic_summary = dict(seed_report.get("economic_target_summary", {}) or {})
    economic_rows = labeled[learning_total_label.loc[labeled.index] != ""].copy()
    economic_rows["learning_total_label"] = learning_total_label.loc[economic_rows.index]
    economic_supported_labels, economic_excluded_labels = _supported_text_classes(
        economic_rows["learning_total_label"] if not economic_rows.empty else pd.Series(dtype=str),
        min_support=economic_target_min_support,
    )
    economic_target_rows = int(len(economic_rows))
    economic_notes: list[str] = []
    economic_supported_rows = economic_rows[economic_rows["learning_total_label"].isin(economic_supported_labels)].copy()
    if economic_rows.empty:
        economic_notes.append("no_learning_total_rows")
    elif len(economic_supported_labels) < 2:
        economic_notes.append("insufficient_learning_total_classes")

    economic_feature_categorical = list(active_categorical_cols)
    economic_feature_numeric = list(active_numeric_cols)
    if len(economic_supported_labels) < 2 or economic_supported_rows.empty:
        economic_total_task: dict[str, Any] = {
            "rows": int(len(economic_supported_rows)),
            "target_rows": int(economic_target_rows),
            "supported_labels": economic_supported_labels,
            "excluded_labels": economic_excluded_labels,
            "feature_columns": {
                "categorical": list(economic_feature_categorical),
                "numeric": list(economic_feature_numeric),
            },
            "skipped": True,
        }
        economic_total_model_bundle = None
    else:
        economic_total_task = _fit_task(
            economic_supported_rows,
            target_column="learning_total_label",
            categorical_cols=list(economic_feature_categorical),
            numeric_cols=list(economic_feature_numeric),
            random_state=random_state,
        )
        economic_total_task["target_rows"] = int(economic_target_rows)
        economic_total_task["supported_labels"] = economic_supported_labels
        economic_total_task["excluded_labels"] = economic_excluded_labels
        economic_total_model_bundle = economic_total_task.pop("model")

    belief_rows = labeled[belief_outcome_label.loc[labeled.index] != ""].copy()
    belief_rows["belief_outcome_label"] = belief_outcome_label.loc[belief_rows.index]
    belief_rows["belief_label_confidence"] = belief_label_confidence.loc[belief_rows.index]
    belief_high_medium_rows = belief_rows[belief_rows["belief_label_confidence"].isin(["high", "medium"])].copy()
    belief_usable_rows = belief_rows[belief_rows["belief_label_confidence"].isin(["high", "medium", "weak_usable"])].copy()
    belief_supported_labels, belief_excluded_labels = _supported_text_classes(
        belief_high_medium_rows["belief_outcome_label"] if not belief_high_medium_rows.empty else pd.Series(dtype=str),
        min_support=belief_outcome_min_support,
    )
    belief_notes: list[str] = []
    if belief_rows.empty:
        belief_notes.append("no_belief_outcome_rows")
    elif belief_high_medium_rows.empty:
        belief_notes.append("no_high_medium_belief_rows")
    elif len(belief_high_medium_rows) < int(belief_outcome_min_rows):
        belief_notes.append("insufficient_belief_high_medium_rows")
    if not belief_high_medium_rows.empty and len(belief_supported_labels) < 2:
        belief_notes.append("insufficient_belief_outcome_classes")
    belief_feature_categorical = list(active_categorical_cols)
    belief_feature_numeric = list(active_numeric_cols)
    belief_supported_rows = belief_high_medium_rows[
        belief_high_medium_rows["belief_outcome_label"].isin(belief_supported_labels)
    ].copy()
    if (
        len(belief_high_medium_rows) < int(belief_outcome_min_rows)
        or len(belief_supported_labels) < 2
        or belief_supported_rows.empty
    ):
        belief_outcome_task: dict[str, Any] = {
            "rows": int(len(belief_supported_rows)),
            "target_rows": int(len(belief_rows)),
            "high_medium_confidence_rows": int(len(belief_high_medium_rows)),
            "usable_confidence_rows": int(len(belief_usable_rows)),
            "supported_labels": belief_supported_labels,
            "excluded_labels": belief_excluded_labels,
            "feature_columns": {
                "categorical": list(belief_feature_categorical),
                "numeric": list(belief_feature_numeric),
            },
            "skipped": True,
        }
        belief_outcome_model_bundle = None
    else:
        belief_outcome_task = _fit_task(
            belief_supported_rows,
            target_column="belief_outcome_label",
            categorical_cols=list(belief_feature_categorical),
            numeric_cols=list(belief_feature_numeric),
            random_state=random_state,
        )
        belief_outcome_task["target_rows"] = int(len(belief_rows))
        belief_outcome_task["high_medium_confidence_rows"] = int(len(belief_high_medium_rows))
        belief_outcome_task["usable_confidence_rows"] = int(len(belief_usable_rows))
        belief_outcome_task["supported_labels"] = belief_supported_labels
        belief_outcome_task["excluded_labels"] = belief_excluded_labels
        belief_outcome_model_bundle = belief_outcome_task.pop("model")

    barrier_rows = labeled[barrier_outcome_label.loc[labeled.index] != ""].copy()
    barrier_rows["barrier_outcome_label"] = barrier_outcome_label.loc[barrier_rows.index]
    barrier_rows["barrier_label_confidence"] = barrier_label_confidence.loc[barrier_rows.index]
    barrier_high_medium_rows = barrier_rows[barrier_rows["barrier_label_confidence"].isin(["high", "medium"])].copy()
    barrier_usable_rows = barrier_rows[
        barrier_rows["barrier_label_confidence"].isin(["high", "medium", "weak_usable"])
    ].copy()
    barrier_supported_labels, barrier_excluded_labels = _supported_text_classes(
        barrier_high_medium_rows["barrier_outcome_label"] if not barrier_high_medium_rows.empty else pd.Series(dtype=str),
        min_support=barrier_outcome_min_support,
    )
    barrier_notes: list[str] = []
    if barrier_rows.empty:
        barrier_notes.append("no_barrier_outcome_rows")
    elif barrier_high_medium_rows.empty:
        barrier_notes.append("no_high_medium_barrier_rows")
    elif len(barrier_high_medium_rows) < int(barrier_outcome_min_rows):
        barrier_notes.append("insufficient_barrier_high_medium_rows")
    if not barrier_high_medium_rows.empty and len(barrier_supported_labels) < 2:
        barrier_notes.append("insufficient_barrier_outcome_classes")
    barrier_feature_categorical = list(active_categorical_cols)
    barrier_feature_numeric = list(active_numeric_cols)
    barrier_supported_rows = barrier_high_medium_rows[
        barrier_high_medium_rows["barrier_outcome_label"].isin(barrier_supported_labels)
    ].copy()
    barrier_usable_supported_rows = barrier_usable_rows[
        barrier_usable_rows["barrier_outcome_label"].isin(barrier_supported_labels)
    ].copy()
    barrier_weak_usable_rows = barrier_rows[barrier_rows["barrier_label_confidence"] == "weak_usable"].copy()
    barrier_weak_usable_share = float(len(barrier_weak_usable_rows) / len(barrier_usable_rows)) if len(barrier_usable_rows) else 0.0
    barrier_weak_to_medium_conversion_rate = (
        float(len(barrier_high_medium_rows) / len(barrier_usable_rows)) if len(barrier_usable_rows) else 0.0
    )
    if (
        len(barrier_high_medium_rows) < int(barrier_outcome_min_rows)
        or len(barrier_supported_labels) < 2
        or barrier_supported_rows.empty
    ):
        barrier_outcome_task: dict[str, Any] = {
            "rows": int(len(barrier_usable_supported_rows)),
            "target_rows": int(len(barrier_rows)),
            "high_medium_confidence_rows": int(len(barrier_high_medium_rows)),
            "usable_confidence_rows": int(len(barrier_usable_rows)),
            "weak_usable_rows": int(len(barrier_weak_usable_rows)),
            "weak_usable_share": round(barrier_weak_usable_share, 6),
            "weak_to_medium_conversion_rate": round(barrier_weak_to_medium_conversion_rate, 6),
            "supported_labels": barrier_supported_labels,
            "excluded_labels": barrier_excluded_labels,
            "feature_columns": {
                "categorical": list(barrier_feature_categorical),
                "numeric": list(barrier_feature_numeric),
            },
            "skipped": True,
        }
        barrier_outcome_model_bundle = None
    else:
        barrier_outcome_task = _fit_task(
            barrier_usable_supported_rows,
            target_column="barrier_outcome_label",
            categorical_cols=list(barrier_feature_categorical),
            numeric_cols=list(barrier_feature_numeric),
            random_state=random_state,
        )
        barrier_outcome_task["target_rows"] = int(len(barrier_rows))
        barrier_outcome_task["high_medium_confidence_rows"] = int(len(barrier_high_medium_rows))
        barrier_outcome_task["usable_confidence_rows"] = int(len(barrier_usable_rows))
        barrier_outcome_task["weak_usable_rows"] = int(len(barrier_weak_usable_rows))
        barrier_outcome_task["weak_usable_share"] = round(barrier_weak_usable_share, 6)
        barrier_outcome_task["weak_to_medium_conversion_rate"] = round(barrier_weak_to_medium_conversion_rate, 6)
        barrier_outcome_task["supported_labels"] = barrier_supported_labels
        barrier_outcome_task["excluded_labels"] = barrier_excluded_labels
        barrier_outcome_model_bundle = barrier_outcome_task.pop("model")

    forecast_transition_rows = labeled[
        (forecast_transition_status.loc[labeled.index] != "")
        & (~forecast_transition_status.loc[labeled.index].isin(FORECAST_OUTCOME_EXCLUDED_STATUSES))
    ].copy()
    forecast_transition_rows["forecast_transition_outcome_status"] = forecast_transition_status.loc[
        forecast_transition_rows.index
    ]
    forecast_transition_supported_labels, forecast_transition_excluded_labels = _supported_text_classes(
        (
            forecast_transition_rows["forecast_transition_outcome_status"]
            if not forecast_transition_rows.empty
            else pd.Series(dtype=str)
        ),
        min_support=forecast_outcome_min_support,
    )
    forecast_transition_notes: list[str] = []
    if forecast_transition_rows.empty:
        forecast_transition_notes.append("no_forecast_transition_rows")
    elif len(forecast_transition_supported_labels) < 2:
        forecast_transition_notes.append("insufficient_forecast_transition_classes")
    forecast_transition_feature_categorical = list(active_categorical_cols)
    forecast_transition_feature_numeric = list(active_numeric_cols)
    forecast_transition_supported_rows = forecast_transition_rows[
        forecast_transition_rows["forecast_transition_outcome_status"].isin(forecast_transition_supported_labels)
    ].copy()
    if len(forecast_transition_supported_labels) < 2 or forecast_transition_supported_rows.empty:
        forecast_transition_task: dict[str, Any] = {
            "rows": int(len(forecast_transition_supported_rows)),
            "target_rows": int(len(forecast_transition_rows)),
            "supported_labels": forecast_transition_supported_labels,
            "excluded_labels": forecast_transition_excluded_labels,
            "feature_columns": {
                "categorical": list(forecast_transition_feature_categorical),
                "numeric": list(forecast_transition_feature_numeric),
            },
            "skipped": True,
        }
        forecast_transition_model_bundle = None
    else:
        forecast_transition_task = _fit_task(
            forecast_transition_supported_rows,
            target_column="forecast_transition_outcome_status",
            categorical_cols=list(forecast_transition_feature_categorical),
            numeric_cols=list(forecast_transition_feature_numeric),
            random_state=random_state,
        )
        forecast_transition_task["target_rows"] = int(len(forecast_transition_rows))
        forecast_transition_task["supported_labels"] = forecast_transition_supported_labels
        forecast_transition_task["excluded_labels"] = forecast_transition_excluded_labels
        forecast_transition_model_bundle = forecast_transition_task.pop("model")

    forecast_management_rows = labeled[
        (forecast_management_status.loc[labeled.index] != "")
        & (~forecast_management_status.loc[labeled.index].isin(FORECAST_OUTCOME_EXCLUDED_STATUSES))
    ].copy()
    forecast_management_rows["forecast_management_outcome_status"] = forecast_management_status.loc[
        forecast_management_rows.index
    ]
    forecast_management_supported_labels, forecast_management_excluded_labels = _supported_text_classes(
        (
            forecast_management_rows["forecast_management_outcome_status"]
            if not forecast_management_rows.empty
            else pd.Series(dtype=str)
        ),
        min_support=forecast_outcome_min_support,
    )
    forecast_management_notes: list[str] = []
    if forecast_management_rows.empty:
        forecast_management_notes.append("no_forecast_management_rows")
    elif len(forecast_management_supported_labels) < 2:
        forecast_management_notes.append("insufficient_forecast_management_classes")
    forecast_management_feature_categorical = list(active_categorical_cols)
    forecast_management_feature_numeric = list(active_numeric_cols)
    forecast_management_supported_rows = forecast_management_rows[
        forecast_management_rows["forecast_management_outcome_status"].isin(forecast_management_supported_labels)
    ].copy()
    if len(forecast_management_supported_labels) < 2 or forecast_management_supported_rows.empty:
        forecast_management_task: dict[str, Any] = {
            "rows": int(len(forecast_management_supported_rows)),
            "target_rows": int(len(forecast_management_rows)),
            "supported_labels": forecast_management_supported_labels,
            "excluded_labels": forecast_management_excluded_labels,
            "feature_columns": {
                "categorical": list(forecast_management_feature_categorical),
                "numeric": list(forecast_management_feature_numeric),
            },
            "skipped": True,
        }
        forecast_management_model_bundle = None
    else:
        forecast_management_task = _fit_task(
            forecast_management_supported_rows,
            target_column="forecast_management_outcome_status",
            categorical_cols=list(forecast_management_feature_categorical),
            numeric_cols=list(forecast_management_feature_numeric),
            random_state=random_state,
        )
        forecast_management_task["target_rows"] = int(len(forecast_management_rows))
        forecast_management_task["supported_labels"] = forecast_management_supported_labels
        forecast_management_task["excluded_labels"] = forecast_management_excluded_labels
        forecast_management_model_bundle = forecast_management_task.pop("model")

    group_model_bundle = group_task.pop("model")

    report = {
        "seed_summary": seed_report,
        "baseline_ready": len(baseline_warnings) == 0,
        "baseline_warnings": baseline_warnings,
        "feature_columns": {
            "categorical": list(active_categorical_cols),
            "numeric": list(active_numeric_cols),
        },
        "wait_quality_integration": {
            "mode": "auxiliary_target",
            "ready": bool(len(wait_quality_supported_labels) >= 2 and not wait_quality_supported_rows.empty),
            "min_support": int(wait_quality_min_support),
            "target_rows": int(len(wait_quality_rows)),
            "supported_labels": wait_quality_supported_labels,
            "excluded_labels": wait_quality_excluded_labels,
            "notes": wait_quality_notes,
            "coverage": dict(seed_report.get("entry_wait_quality_coverage", {})),
            "feature_columns": {
                "categorical": list(wait_quality_feature_categorical),
                "numeric": list(wait_quality_feature_numeric),
            },
        },
        "economic_target_integration": {
            "mode": "auxiliary_target",
            "ready": bool(len(economic_supported_labels) >= 2 and not economic_supported_rows.empty),
            "primary_target": "learning_total_label",
            "min_support": int(economic_target_min_support),
            "target_rows": int(economic_target_rows),
            "supported_labels": economic_supported_labels,
            "excluded_labels": economic_excluded_labels,
            "notes": economic_notes,
            "coverage": dict(economic_summary.get("coverage", {})),
            "feature_columns": {
                "categorical": list(economic_feature_categorical),
                "numeric": list(economic_feature_numeric),
            },
        },
        "forecast_transition_integration": {
            "mode": "auxiliary_target",
            "ready": bool(len(forecast_transition_supported_labels) >= 2 and not forecast_transition_supported_rows.empty),
            "target_column": "forecast_transition_outcome_status",
            "min_support": int(forecast_outcome_min_support),
            "target_rows": int(len(forecast_transition_rows)),
            "supported_labels": forecast_transition_supported_labels,
            "excluded_labels": forecast_transition_excluded_labels,
            "notes": forecast_transition_notes,
            "coverage": dict(seed_report.get("forecast_state25_coverage", {})),
            "feature_columns": {
                "categorical": list(forecast_transition_feature_categorical),
                "numeric": list(forecast_transition_feature_numeric),
            },
        },
        "forecast_management_integration": {
            "mode": "auxiliary_target",
            "ready": bool(len(forecast_management_supported_labels) >= 2 and not forecast_management_supported_rows.empty),
            "target_column": "forecast_management_outcome_status",
            "min_support": int(forecast_outcome_min_support),
            "target_rows": int(len(forecast_management_rows)),
            "supported_labels": forecast_management_supported_labels,
            "excluded_labels": forecast_management_excluded_labels,
            "notes": forecast_management_notes,
            "coverage": dict(seed_report.get("forecast_state25_coverage", {})),
            "feature_columns": {
                "categorical": list(forecast_management_feature_categorical),
                "numeric": list(forecast_management_feature_numeric),
            },
        },
        "belief_outcome_integration": {
            "mode": "auxiliary_target",
            "ready": bool(
                len(belief_high_medium_rows) >= int(belief_outcome_min_rows)
                and len(belief_supported_labels) >= 2
                and not belief_supported_rows.empty
            ),
            "target_column": "belief_outcome_label",
            "min_support": int(belief_outcome_min_support),
            "min_ready_rows": int(belief_outcome_min_rows),
            "target_rows": int(len(belief_rows)),
            "high_medium_confidence_rows": int(len(belief_high_medium_rows)),
            "usable_confidence_rows": int(len(belief_usable_rows)),
            "supported_labels": belief_supported_labels,
            "excluded_labels": belief_excluded_labels,
            "notes": belief_notes,
            "coverage": dict(seed_report.get("belief_outcome_coverage", {})),
            "feature_columns": {
                "categorical": list(belief_feature_categorical),
                "numeric": list(belief_feature_numeric),
            },
        },
        "barrier_outcome_integration": {
            "mode": "auxiliary_target",
            "ready": bool(
                len(barrier_high_medium_rows) >= int(barrier_outcome_min_rows)
                and len(barrier_supported_labels) >= 2
                and not barrier_supported_rows.empty
            ),
            "target_column": "barrier_outcome_label",
            "min_support": int(barrier_outcome_min_support),
            "min_ready_rows": int(barrier_outcome_min_rows),
            "target_rows": int(len(barrier_rows)),
            "high_medium_confidence_rows": int(len(barrier_high_medium_rows)),
            "usable_confidence_rows": int(len(barrier_usable_rows)),
            "weak_usable_rows": int(len(barrier_weak_usable_rows)),
            "weak_usable_share": round(barrier_weak_usable_share, 6),
            "weak_to_medium_conversion_rate": round(barrier_weak_to_medium_conversion_rate, 6),
            "supported_labels": barrier_supported_labels,
            "excluded_labels": barrier_excluded_labels,
            "notes": barrier_notes,
            "coverage": dict(seed_report.get("barrier_outcome_coverage", {})),
            "feature_columns": {
                "categorical": list(barrier_feature_categorical),
                "numeric": list(barrier_feature_numeric),
            },
        },
        "tasks": {
            "group_task": group_task,
            "pattern_task": pattern_task,
            "wait_quality_task": wait_quality_task,
            "economic_total_task": economic_total_task,
            "belief_outcome_task": belief_outcome_task,
            "barrier_outcome_task": barrier_outcome_task,
            "forecast_transition_task": forecast_transition_task,
            "forecast_management_task": forecast_management_task,
        },
    }

    if output_dir is not None:
        _save_bundle(
            output_dir,
            {
                "group_model": group_model_bundle,
                "pattern_model": pattern_model_bundle,
                "wait_quality_model": wait_quality_model_bundle,
                "economic_total_model": economic_total_model_bundle,
                "belief_outcome_model": belief_outcome_model_bundle,
                "barrier_outcome_model": barrier_outcome_model_bundle,
                "forecast_transition_model": forecast_transition_model_bundle,
                "forecast_management_model": forecast_management_model_bundle,
                "feature_columns": report["feature_columns"],
                "supported_pattern_ids": supported_pattern_ids,
                "wait_quality_integration": report["wait_quality_integration"],
                "economic_target_integration": report["economic_target_integration"],
                "belief_outcome_integration": report["belief_outcome_integration"],
                "barrier_outcome_integration": report["barrier_outcome_integration"],
                "forecast_transition_integration": report["forecast_transition_integration"],
                "forecast_management_integration": report["forecast_management_integration"],
                "version": "teacher_pattern_state25_pilot_v7",
            },
            report,
        )

    return report
