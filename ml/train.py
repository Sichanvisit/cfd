"""
Train entry/exit models from datasets built by ml/dataset_builder.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.feature_schema import (
    ENTRY_CATEGORICAL_COLS,
    ENTRY_FEATURE_COLS,
    EXIT_CATEGORICAL_COLS,
    EXIT_FEATURE_COLS,
)


def _time_split(df: pd.DataFrame, time_col: str, train_ratio: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    sorted_df = df.sort_values(time_col).reset_index(drop=True)
    if len(sorted_df) < 10:
        return sorted_df, sorted_df.iloc[0:0]
    split_idx = int(len(sorted_df) * train_ratio)
    split_idx = max(1, min(len(sorted_df) - 1, split_idx))
    return sorted_df.iloc[:split_idx].copy(), sorted_df.iloc[split_idx:].copy()


def _build_classifier(cat_cols, num_cols):
    pre = ColumnTransformer(
        transformers=[
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), num_cols),
        ]
    )
    model = LogisticRegression(
        solver="liblinear",
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    )
    return Pipeline([("pre", pre), ("model", model)])


def _evaluate(model, x_test, y_test) -> Dict[str, float]:
    if len(x_test) == 0 or len(y_test) == 0:
        return {"accuracy": np.nan, "auc": np.nan, "samples": 0}

    pred = model.predict(x_test)
    acc = float(accuracy_score(y_test, pred))
    out = {"accuracy": acc, "samples": int(len(y_test))}
    if len(np.unique(y_test)) > 1:
        prob = model.predict_proba(x_test)[:, 1]
        out["auc"] = float(roc_auc_score(y_test, prob))
    else:
        out["auc"] = np.nan
    return out


def _fit_with_fallback(model, x_train, y_train):
    y_train = y_train.astype(int)
    if len(np.unique(y_train)) < 2:
        fallback = DummyClassifier(strategy="most_frequent")
        fallback.fit(x_train, y_train)
        return fallback
    model.fit(x_train, y_train)
    return model


def _ensure_feature_columns(df: pd.DataFrame, feature_cols: list[str], cat_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    cat_set = set(cat_cols)
    for column in feature_cols:
        if column not in out.columns:
            out[column] = "" if column in cat_set else 0.0
    return out


def _load_previous_metrics(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _metric_delta(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None:
        return None
    if pd.isna(current) or pd.isna(previous):
        return None
    return round(float(current) - float(previous), 6)


def train(entry_csv: Path, exit_csv: Path, out_dir: Path):
    entry_df = pd.read_csv(entry_csv)
    exit_df = pd.read_csv(exit_csv)

    for df in (entry_df, exit_df):
        df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")

    entry_feature_cols = list(ENTRY_FEATURE_COLS)
    exit_feature_cols = list(EXIT_FEATURE_COLS)

    entry_cat_cols = list(ENTRY_CATEGORICAL_COLS)
    entry_num_cols = [c for c in entry_feature_cols if c not in entry_cat_cols]
    exit_cat_cols = list(EXIT_CATEGORICAL_COLS)
    exit_num_cols = [c for c in exit_feature_cols if c not in exit_cat_cols]
    entry_df = _ensure_feature_columns(entry_df, entry_feature_cols, entry_cat_cols)
    exit_df = _ensure_feature_columns(exit_df, exit_feature_cols, exit_cat_cols)

    entry_train, entry_test = _time_split(entry_df, "event_time")
    exit_train, exit_test = _time_split(exit_df, "event_time")

    entry_model = _build_classifier(entry_cat_cols, entry_num_cols)
    exit_model = _build_classifier(exit_cat_cols, exit_num_cols)

    entry_model = _fit_with_fallback(entry_model, entry_train[entry_feature_cols], entry_train["is_win"])
    exit_model = _fit_with_fallback(exit_model, exit_train[exit_feature_cols], exit_train["is_good_exit"])

    entry_metrics = _evaluate(
        entry_model, entry_test[entry_feature_cols], entry_test["is_win"].astype(int)
    )
    exit_metrics = _evaluate(
        exit_model, exit_test[exit_feature_cols], exit_test["is_good_exit"].astype(int)
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    previous_metrics = _load_previous_metrics(out_dir / "metrics.json")
    model_bundle = {
        "entry_model": entry_model,
        "exit_model": exit_model,
        "entry_feature_cols": entry_feature_cols,
        "exit_feature_cols": exit_feature_cols,
    }
    joblib.dump(model_bundle, out_dir / "ai_models.joblib")

    metrics = {
        "entry_metrics": entry_metrics,
        "exit_metrics": exit_metrics,
        "entry_train_samples": int(len(entry_train)),
        "entry_test_samples": int(len(entry_test)),
        "exit_train_samples": int(len(exit_train)),
        "exit_test_samples": int(len(exit_test)),
        "entry_feature_count": len(entry_feature_cols),
        "exit_feature_count": len(exit_feature_cols),
        "entry_categorical_cols": entry_cat_cols,
        "exit_categorical_cols": exit_cat_cols,
        "feature_pack_version": "live_ml_step4_v1",
        "comparison_to_previous": {
            "entry_auc_delta": _metric_delta(
                entry_metrics.get("auc"),
                ((previous_metrics.get("entry_metrics") or {}) if isinstance(previous_metrics.get("entry_metrics"), dict) else {}).get("auc"),
            ),
            "entry_accuracy_delta": _metric_delta(
                entry_metrics.get("accuracy"),
                ((previous_metrics.get("entry_metrics") or {}) if isinstance(previous_metrics.get("entry_metrics"), dict) else {}).get("accuracy"),
            ),
            "exit_auc_delta": _metric_delta(
                exit_metrics.get("auc"),
                ((previous_metrics.get("exit_metrics") or {}) if isinstance(previous_metrics.get("exit_metrics"), dict) else {}).get("auc"),
            ),
            "exit_accuracy_delta": _metric_delta(
                exit_metrics.get("accuracy"),
                ((previous_metrics.get("exit_metrics") or {}) if isinstance(previous_metrics.get("exit_metrics"), dict) else {}).get("accuracy"),
            ),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    model_path = out_dir / "ai_models.joblib"
    metrics_path = out_dir / "metrics.json"
    print("saved:", model_path)
    print("saved:", metrics_path)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return {
        "model_path": model_path,
        "metrics_path": metrics_path,
        "metrics": metrics,
    }


def train_exit_only(exit_csv: Path, base_model_path: Path, out_dir: Path, base_metrics_path: Path | None = None):
    if not base_model_path.exists():
        raise FileNotFoundError(f"base model not found: {base_model_path}")

    bundle = joblib.load(base_model_path)
    if "entry_model" not in bundle or "entry_feature_cols" not in bundle:
        raise ValueError("base model bundle missing entry model/feature columns")

    exit_df = pd.read_csv(exit_csv)
    exit_df["event_time"] = pd.to_datetime(exit_df["event_time"], errors="coerce")

    exit_feature_cols = list(EXIT_FEATURE_COLS)
    exit_cat_cols = list(EXIT_CATEGORICAL_COLS)
    exit_num_cols = [c for c in exit_feature_cols if c not in exit_cat_cols]
    exit_df = _ensure_feature_columns(exit_df, exit_feature_cols, exit_cat_cols)

    exit_train, exit_test = _time_split(exit_df, "event_time")
    exit_model = _build_classifier(exit_cat_cols, exit_num_cols)
    exit_model = _fit_with_fallback(exit_model, exit_train[exit_feature_cols], exit_train["is_good_exit"])
    exit_metrics = _evaluate(
        exit_model, exit_test[exit_feature_cols], exit_test["is_good_exit"].astype(int)
    )

    entry_metrics = {"accuracy": np.nan, "auc": np.nan, "samples": 0}
    if base_metrics_path and base_metrics_path.exists():
        try:
            prev = json.loads(base_metrics_path.read_text(encoding="utf-8"))
            em = prev.get("entry_metrics")
            if isinstance(em, dict):
                entry_metrics = em
        except Exception:
            pass

    out_dir.mkdir(parents=True, exist_ok=True)
    previous_metrics = _load_previous_metrics(out_dir / "metrics.json")
    model_bundle = {
        "entry_model": bundle["entry_model"],
        "exit_model": exit_model,
        "entry_feature_cols": bundle["entry_feature_cols"],
        "exit_feature_cols": exit_feature_cols,
    }
    joblib.dump(model_bundle, out_dir / "ai_models.joblib")

    metrics = {
        "entry_metrics": entry_metrics,
        "exit_metrics": exit_metrics,
        "entry_train_samples": 0,
        "entry_test_samples": 0,
        "exit_train_samples": int(len(exit_train)),
        "exit_test_samples": int(len(exit_test)),
        "mode": "exit_only",
        "entry_feature_count": len(bundle["entry_feature_cols"]),
        "exit_feature_count": len(exit_feature_cols),
        "entry_categorical_cols": list(ENTRY_CATEGORICAL_COLS),
        "exit_categorical_cols": exit_cat_cols,
        "feature_pack_version": "live_ml_step4_v1",
        "comparison_to_previous": {
            "exit_auc_delta": _metric_delta(
                exit_metrics.get("auc"),
                ((previous_metrics.get("exit_metrics") or {}) if isinstance(previous_metrics.get("exit_metrics"), dict) else {}).get("auc"),
            ),
            "exit_accuracy_delta": _metric_delta(
                exit_metrics.get("accuracy"),
                ((previous_metrics.get("exit_metrics") or {}) if isinstance(previous_metrics.get("exit_metrics"), dict) else {}).get("accuracy"),
            ),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    model_path = out_dir / "ai_models.joblib"
    metrics_path = out_dir / "metrics.json"
    print("saved:", model_path)
    print("saved:", metrics_path)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return {
        "model_path": model_path,
        "metrics_path": metrics_path,
        "metrics": metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Train entry/exit AI models.")
    parser.add_argument("--entry-csv", default=str(PROJECT_ROOT / "data" / "datasets" / "entry_dataset.csv"))
    parser.add_argument("--exit-csv", default=str(PROJECT_ROOT / "data" / "datasets" / "exit_dataset.csv"))
    parser.add_argument("--out-dir", default=str(PROJECT_ROOT / "models"))
    args = parser.parse_args()
    train(Path(args.entry_csv), Path(args.exit_csv), Path(args.out_dir))


if __name__ == "__main__":
    main()
