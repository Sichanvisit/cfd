from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.semantic_v1.dataset_builder import (
    DEFAULT_OUTPUT_DIR as DEFAULT_DATASET_DIR,
    KEY_COLUMNS,
    LABEL_COLUMNS,
    METADATA_COLUMNS,
    SPLIT_COLUMNS,
)
from ml.semantic_v1.feature_packs import SEMANTIC_INPUT_COLUMNS, TRACE_QUALITY_COLUMNS
from ml.semantic_v1.dataset_splits import (
    build_split_health_payload,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "semantic_v1"
SEMANTIC_MODEL_VERSION = "semantic_tabular_model_v1"
SEMANTIC_METRICS_VERSION = "semantic_tabular_metrics_v1"
DEFAULT_RANDOM_STATE = 42

SAFE_METADATA_FEATURE_COLUMNS = (
    "symbol",
    "signal_timeframe",
    "setup_id",
    "setup_side",
    "entry_stage",
    "preflight_regime",
    "preflight_liquidity",
)

TARGET_TO_DATASET_PATH = {
    "timing": DEFAULT_DATASET_DIR / "timing_dataset.parquet",
    "entry_quality": DEFAULT_DATASET_DIR / "entry_quality_dataset.parquet",
    "exit_management": DEFAULT_DATASET_DIR / "exit_management_dataset.parquet",
}


@dataclass(frozen=True)
class TrainConfig:
    dataset_key: str
    dataset_path: Path
    output_dir: Path
    model_file_name: str
    target_column: str
    margin_column: str
    positive_label: str


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    target = Path(value) if value is not None else default
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    return target


def build_train_config(dataset_key: str, dataset_path: str | Path | None = None, output_dir: str | Path | None = None) -> TrainConfig:
    key = str(dataset_key).strip()
    if key == "timing":
        return TrainConfig(
            dataset_key="timing",
            dataset_path=_resolve_path(dataset_path, TARGET_TO_DATASET_PATH["timing"]),
            output_dir=_resolve_path(output_dir, DEFAULT_MODEL_DIR),
            model_file_name="timing_model.joblib",
            target_column="target_timing_now_vs_wait",
            margin_column="target_timing_margin",
            positive_label="now",
        )
    if key == "entry_quality":
        return TrainConfig(
            dataset_key="entry_quality",
            dataset_path=_resolve_path(dataset_path, TARGET_TO_DATASET_PATH["entry_quality"]),
            output_dir=_resolve_path(output_dir, DEFAULT_MODEL_DIR),
            model_file_name="entry_quality_model.joblib",
            target_column="target_entry_quality",
            margin_column="target_entry_quality_margin",
            positive_label="high_quality",
        )
    if key == "exit_management":
        return TrainConfig(
            dataset_key="exit_management",
            dataset_path=_resolve_path(dataset_path, TARGET_TO_DATASET_PATH["exit_management"]),
            output_dir=_resolve_path(output_dir, DEFAULT_MODEL_DIR),
            model_file_name="exit_management_model.joblib",
            target_column="target_exit_management",
            margin_column="target_exit_management_margin",
            positive_label="favor_exit_management",
        )
    raise ValueError(f"unsupported dataset key: {dataset_key}")


def _read_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")
    frame = pd.read_parquet(path)
    if frame.empty:
        raise ValueError(
            f"dataset is empty: {path}. "
            "build semantic_v1 datasets from matching compact export and replay rows first."
        )
    return frame


def _read_dataset_summary(dataset_path: Path) -> dict[str, Any]:
    summary_path = dataset_path.with_suffix(dataset_path.suffix + ".summary.json")
    if not summary_path.exists():
        return {}
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _dataset_feature_tier_summary(dataset_summary: Mapping[str, Any]) -> dict[str, Any]:
    summary = dataset_summary.get("feature_tier_summary", {})
    if isinstance(summary, dict) and summary:
        return dict(summary)
    policy = dataset_summary.get("feature_tier_policy", {})
    if not isinstance(policy, Mapping):
        return {}
    rebuilt: dict[str, Any] = {}
    for tier_name, mode in policy.items():
        rebuilt[str(tier_name)] = {
            "mode": str(mode),
            "candidate_count": 0,
            "retained_count": 0,
            "dropped_count": 0,
            "observed_only_dropped_count": 0,
        }
    return rebuilt


def _dataset_observed_only_dropped_feature_columns(dataset_summary: Mapping[str, Any]) -> list[str]:
    explicit = dataset_summary.get("observed_only_dropped_feature_columns")
    if isinstance(explicit, list) and explicit:
        return [str(value) for value in explicit]
    dropped_reasons = dataset_summary.get("dropped_feature_reasons", {})
    if not isinstance(dropped_reasons, Mapping):
        return []
    return sorted(
        str(column)
        for column, reason in dropped_reasons.items()
        if str(reason).endswith("_all_missing") and "trace_quality_pack" in str(reason)
    )


def _feature_columns(df: pd.DataFrame, *, target_column: str, margin_column: str) -> list[str]:
    candidates = list(dict.fromkeys([*SAFE_METADATA_FEATURE_COLUMNS, *SEMANTIC_INPUT_COLUMNS, *TRACE_QUALITY_COLUMNS]))
    forbidden = {
        *KEY_COLUMNS,
        *LABEL_COLUMNS,
        *SPLIT_COLUMNS,
        *("time", "signal_bar_ts", "action", "outcome", "blocked_by", "dataset_key", "target_contract", "event_ts"),
        target_column,
        margin_column,
        "target_timing_now_vs_wait",
        "target_timing_margin",
        "target_entry_quality",
        "target_entry_quality_margin",
        "target_exit_management",
        "target_exit_management_margin",
    }
    return [column for column in candidates if column in df.columns and column not in forbidden]


def _is_all_missing(series: pd.Series) -> bool:
    if str(series.dtype) in {"object", "string", "category"}:
        return bool((series.isna() | series.astype(str).str.strip().eq("")).all())
    return bool(series.isna().all())


def _prune_all_missing_feature_columns(df: pd.DataFrame, feature_columns: Iterable[str]) -> tuple[list[str], dict[str, str]]:
    kept: list[str] = []
    dropped: dict[str, str] = {}
    for column in feature_columns:
        if column not in df.columns:
            continue
        if _is_all_missing(df[column]):
            dropped[column] = "all_missing_feature"
            continue
        kept.append(column)
    return kept, dropped


def _categorical_columns(df: pd.DataFrame, feature_columns: Iterable[str]) -> list[str]:
    categorical: list[str] = []
    for column in feature_columns:
        if str(df[column].dtype) in {"object", "string", "category"}:
            categorical.append(column)
    return categorical


def _numeric_columns(feature_columns: Iterable[str], categorical_columns: Iterable[str]) -> list[str]:
    categorical_set = set(categorical_columns)
    return [column for column in feature_columns if column not in categorical_set]


def _split_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "time_split_bucket" not in df.columns:
        ordered = df.sort_values("event_ts" if "event_ts" in df.columns else "signal_bar_ts", kind="mergesort").reset_index(drop=True)
        n = len(ordered)
        train_end = max(1, int(n * 0.7))
        validation_end = max(train_end + 1, int(n * 0.85))
        return ordered.iloc[:train_end].copy(), ordered.iloc[train_end:validation_end].copy(), ordered.iloc[validation_end:].copy()

    train_df = df[df["time_split_bucket"] == "train"].copy()
    validation_df = df[df["time_split_bucket"] == "validation"].copy()
    test_df = df[df["time_split_bucket"] == "test"].copy()

    if validation_df.empty:
        validation_df = test_df.iloc[: max(1, len(test_df) // 2)].copy()
    if test_df.empty:
        test_df = validation_df.copy()
    if train_df.empty:
        ordered = df.sort_values("event_ts" if "event_ts" in df.columns else "signal_bar_ts", kind="mergesort")
        cutoff = max(1, int(len(ordered) * 0.7))
        train_df = ordered.iloc[:cutoff].copy()
    return train_df, validation_df, test_df


def _build_pipeline(categorical_columns: list[str], numeric_columns: list[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            ),
            (
                "num",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]),
                numeric_columns,
            ),
        ],
        remainder="drop",
    )
    model = RandomForestClassifier(
        n_estimators=300,
        min_samples_leaf=4,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=DEFAULT_RANDOM_STATE,
    )
    return Pipeline([("pre", preprocessor), ("model", model)])


def _fit_platt_scaler(probabilities: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels).astype(int)
    probabilities = np.asarray(probabilities, dtype=float).reshape(-1, 1)
    if len(labels) < 8 or len(np.unique(labels)) < 2:
        return {"method": "identity", "estimator": None}
    calibrator = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=DEFAULT_RANDOM_STATE)
    calibrator.fit(probabilities, labels)
    return {"method": "platt_logistic", "estimator": calibrator}


def _apply_calibration(calibration_bundle: Mapping[str, Any], base_probabilities: np.ndarray) -> np.ndarray:
    method = str(calibration_bundle.get("method", "identity") or "identity")
    estimator = calibration_bundle.get("estimator")
    base_probabilities = np.asarray(base_probabilities, dtype=float)
    if method == "platt_logistic" and estimator is not None:
        return estimator.predict_proba(base_probabilities.reshape(-1, 1))[:, 1]
    return base_probabilities


def _positive_class_probability(base_model: Any, frame: pd.DataFrame, *, positive_class: int = 1) -> np.ndarray:
    probabilities = np.asarray(base_model.predict_proba(frame))
    classes = np.asarray(getattr(base_model, "classes_", []))
    if probabilities.ndim == 1:
        probabilities = probabilities.reshape(-1, 1)
    if probabilities.shape[1] <= 0:
        return np.zeros(len(frame), dtype=float)
    if probabilities.shape[1] == 1:
        if len(classes) == 1 and int(classes[0]) == int(positive_class):
            return np.ones(len(frame), dtype=float)
        return np.zeros(len(frame), dtype=float)
    if len(classes) > 0:
        try:
            class_index = int(np.where(classes == positive_class)[0][0])
            return probabilities[:, class_index]
        except Exception:
            pass
    return probabilities[:, 1]


def predict_bundle_proba(bundle: Mapping[str, Any], frame: pd.DataFrame) -> np.ndarray:
    feature_columns = list(bundle["feature_columns"])
    base_model = bundle["base_model"]
    calibration = bundle.get("calibration", {"method": "identity", "estimator": None})
    base_prob = _positive_class_probability(base_model, frame[feature_columns], positive_class=1)
    return _apply_calibration(calibration, base_prob)


def _safe_auc(y_true: np.ndarray, probabilities: np.ndarray) -> float | None:
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, probabilities))


def _calibration_error(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float | None:
    if len(y_true) == 0:
        return None
    y_true = np.asarray(y_true).astype(float)
    probabilities = np.asarray(probabilities).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    error = 0.0
    counted = 0
    for idx in range(bins):
        lower = edges[idx]
        upper = edges[idx + 1]
        if idx == bins - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        bucket_size = int(mask.sum())
        if bucket_size <= 0:
            continue
        counted += bucket_size
        bucket_accuracy = float(y_true[mask].mean())
        bucket_confidence = float(probabilities[mask].mean())
        error += abs(bucket_accuracy - bucket_confidence) * bucket_size
    if counted <= 0:
        return None
    return round(error / counted, 6)


def _top_k_precision(y_true: np.ndarray, probabilities: np.ndarray, ratio: float) -> float | None:
    if len(y_true) == 0:
        return None
    k = max(1, int(len(y_true) * ratio))
    order = np.argsort(-probabilities)[:k]
    return round(float(np.asarray(y_true)[order].mean()), 6)


def _expected_value_proxy(y_true: np.ndarray, probabilities: np.ndarray, margin: np.ndarray) -> float | None:
    if len(y_true) == 0:
        return None
    signed_margin = np.where(np.asarray(y_true).astype(int) > 0, np.abs(margin), -np.abs(margin))
    predicted_edge = (np.asarray(probabilities) * 2.0) - 1.0
    return round(float(np.mean(predicted_edge * signed_margin)), 6)


def _slice_auc(frame: pd.DataFrame, *, group_col: str, target_col: str, prob_col: str, min_rows: int = 8) -> dict[str, Any]:
    if group_col not in frame.columns:
        return {}
    output: dict[str, Any] = {}
    for key, group in frame.groupby(frame[group_col].fillna("__missing__"), dropna=False):
        if len(group) < min_rows:
            output[str(key)] = {"rows": int(len(group)), "auc": None}
            continue
        auc = _safe_auc(group[target_col].to_numpy(dtype=int), group[prob_col].to_numpy(dtype=float))
        output[str(key)] = {"rows": int(len(group)), "auc": auc}
    return output


def _subset_metrics(frame: pd.DataFrame, *, target_col: str, prob_col: str, margin_col: str) -> dict[str, Any]:
    if frame.empty:
        return {"rows": 0, "auc": None, "calibration_error": None, "expected_value_proxy": None}
    y_true = frame[target_col].to_numpy(dtype=int)
    prob = frame[prob_col].to_numpy(dtype=float)
    margin = frame[margin_col].to_numpy(dtype=float)
    return {
        "rows": int(len(frame)),
        "auc": _safe_auc(y_true, prob),
        "calibration_error": _calibration_error(y_true, prob),
        "expected_value_proxy": _expected_value_proxy(y_true, prob, margin),
    }


def _numeric_series_or_default(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _string_series_or_default(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="object")
    return frame[column].fillna("").astype(str).str.strip()


def _fallback_comparison(frame: pd.DataFrame, *, target_col: str, prob_col: str, margin_col: str) -> dict[str, Any]:
    used_fallback = _numeric_series_or_default(frame, "used_fallback_count", default=0.0)
    missing_feature = _numeric_series_or_default(frame, "missing_feature_count", default=0.0)
    compatibility = _string_series_or_default(frame, "compatibility_mode", default="")
    heavy_mask = (used_fallback > 0) | (missing_feature > 0) | compatibility.ne("")
    clean_mask = ~heavy_mask
    return {
        "fallback_heavy": _subset_metrics(frame[heavy_mask], target_col=target_col, prob_col=prob_col, margin_col=margin_col),
        "clean": _subset_metrics(frame[clean_mask], target_col=target_col, prob_col=prob_col, margin_col=margin_col),
    }


def _feature_importances(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    base_model = bundle["base_model"]
    if not hasattr(base_model.named_steps["model"], "feature_importances_"):
        return []
    preprocessor = base_model.named_steps["pre"]
    model = base_model.named_steps["model"]
    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        feature_names = [f"feature_{idx}" for idx in range(len(model.feature_importances_))]
    rows = [
        {"feature": str(name), "importance": round(float(score), 6)}
        for name, score in zip(feature_names, model.feature_importances_)
    ]
    rows.sort(key=lambda item: (-item["importance"], item["feature"]))
    return rows[:25]


def evaluate_model_bundle(
    bundle: Mapping[str, Any],
    test_df: pd.DataFrame,
    *,
    target_column: str,
    margin_column: str,
) -> dict[str, Any]:
    probabilities = predict_bundle_proba(bundle, test_df)
    y_true = test_df[target_column].to_numpy(dtype=int)
    margins = pd.to_numeric(test_df[margin_column], errors="coerce").fillna(0).to_numpy(dtype=float)
    predictions = (probabilities >= 0.5).astype(int)

    evaluation_frame = test_df.copy()
    evaluation_frame["predicted_probability"] = probabilities

    return {
        "rows": int(len(test_df)),
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6) if len(test_df) > 0 else None,
        "auc": _safe_auc(y_true, probabilities),
        "brier_score": (round(float(brier_score_loss(y_true, probabilities)), 6) if len(np.unique(y_true)) >= 1 and len(test_df) > 0 else None),
        "calibration_error": _calibration_error(y_true, probabilities),
        "top_k_precision": {
            "top_10pct": _top_k_precision(y_true, probabilities, 0.10),
            "top_20pct": _top_k_precision(y_true, probabilities, 0.20),
        },
        "expected_value_proxy": _expected_value_proxy(y_true, probabilities, margins),
        "symbol_auc": _slice_auc(evaluation_frame, group_col="symbol", target_col=target_column, prob_col="predicted_probability"),
        "regime_auc": _slice_auc(evaluation_frame, group_col="preflight_regime", target_col=target_column, prob_col="predicted_probability"),
        "setup_auc": _slice_auc(evaluation_frame, group_col="setup_id", target_col=target_column, prob_col="predicted_probability"),
        "fallback_vs_clean": _fallback_comparison(evaluation_frame, target_col=target_column, prob_col="predicted_probability", margin_col=margin_column),
    }


def _load_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _class_balance(frame: pd.DataFrame, *, target_column: str) -> dict[str, int]:
    if target_column not in frame.columns or frame.empty:
        return {}
    counts = frame[target_column].value_counts(dropna=False).to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def train_semantic_model(config: TrainConfig) -> dict[str, Any]:
    dataset = _read_dataset(config.dataset_path)
    dataset_summary = _read_dataset_summary(config.dataset_path)
    feature_columns = _feature_columns(dataset, target_column=config.target_column, margin_column=config.margin_column)
    feature_columns, dropped_feature_columns = _prune_all_missing_feature_columns(dataset, feature_columns)
    if not feature_columns:
        raise ValueError(f"no usable feature columns found in {config.dataset_path}")
    categorical_columns = _categorical_columns(dataset, feature_columns)
    numeric_columns = _numeric_columns(feature_columns, categorical_columns)

    train_df, validation_df, test_df = _split_frame(dataset)
    if test_df.empty:
        raise ValueError("test split is empty; cannot evaluate semantic model")
    split_health = build_split_health_payload(dataset, target_col=config.target_column)

    pipeline = _build_pipeline(categorical_columns, numeric_columns)
    y_train = train_df[config.target_column].astype(int)
    fit_kwargs: dict[str, Any] = {}
    if "sample_weight" in train_df.columns:
        sample_weight = pd.to_numeric(train_df["sample_weight"], errors="coerce").fillna(1.0).clip(lower=0.01)
        fit_kwargs["model__sample_weight"] = sample_weight.to_numpy(dtype=float)
    pipeline.fit(train_df[feature_columns], y_train, **fit_kwargs)

    validation_prob = (
        _positive_class_probability(pipeline, validation_df[feature_columns], positive_class=1)
        if not validation_df.empty
        else _positive_class_probability(pipeline, train_df[feature_columns], positive_class=1)
    )
    validation_y = validation_df[config.target_column].astype(int).to_numpy() if not validation_df.empty else train_df[config.target_column].astype(int).to_numpy()
    calibration = _fit_platt_scaler(validation_prob, validation_y)

    bundle = {
        "model_version": SEMANTIC_MODEL_VERSION,
        "dataset_key": config.dataset_key,
        "dataset_path": str(config.dataset_path),
        "target_column": config.target_column,
        "margin_column": config.margin_column,
        "feature_columns": feature_columns,
        "categorical_columns": categorical_columns,
        "numeric_columns": numeric_columns,
        "base_model": pipeline,
        "calibration": calibration,
        "positive_label": config.positive_label,
        "weighted_training": bool("sample_weight" in dataset.columns),
    }

    metrics = evaluate_model_bundle(bundle, test_df, target_column=config.target_column, margin_column=config.margin_column)
    metrics.update(
        {
            "metrics_version": SEMANTIC_METRICS_VERSION,
            "model_version": SEMANTIC_MODEL_VERSION,
            "dataset_key": config.dataset_key,
            "dataset_path": str(config.dataset_path),
            "target_column": config.target_column,
            "margin_column": config.margin_column,
            "train_rows": int(len(train_df)),
            "validation_rows": int(len(validation_df)),
            "test_rows": int(len(test_df)),
            "train_class_balance": _class_balance(train_df, target_column=config.target_column),
            "validation_class_balance": _class_balance(validation_df, target_column=config.target_column),
            "test_class_balance": _class_balance(test_df, target_column=config.target_column),
            "split_health": split_health,
            "split_health_status": split_health["overall_status"],
            "split_health_promotion_blocked": bool(split_health["promotion_blocked"]),
            "feature_columns": feature_columns,
            "categorical_columns": categorical_columns,
            "numeric_columns": numeric_columns,
            "dataset_source_generation": dataset_summary.get("source_generation"),
            "dataset_feature_tier_policy": dataset_summary.get("feature_tier_policy", {}),
            "dataset_feature_tier_summary": _dataset_feature_tier_summary(dataset_summary),
            "dataset_dropped_feature_columns": list(dataset_summary.get("dropped_feature_columns", [])),
            "dataset_dropped_feature_reasons": dict(dataset_summary.get("dropped_feature_reasons", {})),
            "dataset_observed_only_dropped_feature_columns": _dataset_observed_only_dropped_feature_columns(dataset_summary),
            "training_dropped_feature_columns": list(dropped_feature_columns.keys()),
            "training_dropped_feature_reasons": dict(dropped_feature_columns),
            "calibration_method": str(calibration.get("method", "identity") or "identity"),
            "feature_importances_top25": _feature_importances(bundle),
        }
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = config.output_dir / config.model_file_name
    joblib.dump(bundle, model_path)

    metrics_path = config.output_dir / "metrics.json"
    all_metrics = _load_metrics(metrics_path)
    all_metrics.update(
        {
            "metrics_version": SEMANTIC_METRICS_VERSION,
            "model_version": SEMANTIC_MODEL_VERSION,
            f"{config.dataset_key}_metrics": metrics,
        }
    )
    metrics_path.write_text(json.dumps(all_metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    model_summary_path = model_path.with_suffix(".summary.json")
    model_summary_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "model_path": str(model_path),
        "model_summary_path": str(model_summary_path),
        "metrics_path": str(metrics_path),
        "metrics": metrics,
    }
