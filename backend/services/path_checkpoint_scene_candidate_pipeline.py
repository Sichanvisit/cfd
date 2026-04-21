"""Scene candidate retrain / compare / promote scaffold for SA4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.services.path_checkpoint_dataset import (
    PATH_CHECKPOINT_SCENE_DATASET_COLUMNS,
)
from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCENE_CANDIDATE_METRICS_VERSION = "checkpoint_scene_candidate_metrics_v1"
PATH_CHECKPOINT_SCENE_CANDIDATE_COMPARE_VERSION = "checkpoint_scene_candidate_compare_report_v1"
PATH_CHECKPOINT_SCENE_CANDIDATE_PROMOTION_VERSION = "checkpoint_scene_candidate_promote_decision_v1"
PATH_CHECKPOINT_SCENE_CANDIDATE_RUN_MANIFEST_VERSION = "checkpoint_scene_candidate_run_manifest_v1"
DEFAULT_CANDIDATE_ROOT = Path("models") / "path_checkpoint_scene_candidates"
TASK_NAMES = (
    "coarse_family_task",
    "gate_task",
    "resolved_scene_task",
    "late_scene_task",
)
PRIMARY_PROMOTION_TASKS = (
    "coarse_family_task",
    "gate_task",
    "resolved_scene_task",
)
SECONDARY_PROMOTION_TASKS = ("late_scene_task",)
METRIC_NAMES = ("macro_f1", "balanced_accuracy", "accuracy", "weighted_f1")
DEFAULT_RANDOM_STATE = 25
DEFAULT_DELTA_HARD = -0.05
DEFAULT_DELTA_OK = 0.03

SCENE_FEATURE_CATEGORICAL_COLUMNS = [
    "symbol",
    "surface_name",
    "checkpoint_type",
    "leg_direction",
    "position_side",
    "unrealized_pnl_state",
    "source",
    "checkpoint_rule_family_hint",
    "exit_stage_family",
]
SCENE_FEATURE_NUMERIC_COLUMNS = [
    "checkpoint_index_in_leg",
    "current_profit",
    "mfe_since_entry",
    "mae_since_entry",
    "giveback_ratio",
    "runtime_continuation_odds",
    "runtime_reversal_odds",
    "runtime_hold_quality_score",
    "runtime_partial_exit_ev",
    "runtime_full_exit_risk",
    "runtime_scene_confidence",
]
SCENE_TASK_CONFIG = {
    "coarse_family_task": {"min_rows": 30, "min_support": 8},
    "gate_task": {"min_rows": 40, "min_support": 8},
    "resolved_scene_task": {"min_rows": 30, "min_support": 8},
    "late_scene_task": {"min_rows": 20, "min_support": 5},
}
ENTRY_SCENE_LABELS = {
    "trend_ignition",
    "breakout",
    "breakout_retest_hold",
    "liquidity_sweep_reclaim",
    "orderblock_reaction",
}
CONTINUATION_SCENE_LABELS = {
    "pullback_continuation",
    "reaccumulation",
    "redistribution",
}
MANAGEMENT_SCENE_LABELS = {
    "runner_healthy",
    "profit_trim_zone",
    "add_setup",
    "rebuy_setup",
    "fvg_response_zone",
    "time_decay_risk",
}
DEFENSIVE_SCENE_LABELS = {
    "failed_transition",
    "protective_risk",
    "trend_exhaustion",
    "climax_reversal",
}
LATE_SCENE_LABELS = {
    "trend_exhaustion",
    "time_decay_risk",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_scene_candidate_root() -> Path:
    return _repo_root() / DEFAULT_CANDIDATE_ROOT


def default_checkpoint_scene_candidate_latest_run_path() -> Path:
    return default_checkpoint_scene_candidate_root() / "latest_candidate_run.json"


def default_checkpoint_scene_candidate_active_state_path() -> Path:
    return default_checkpoint_scene_candidate_root() / "active_candidate_state.json"


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _json_counts(counts: dict[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _ensure_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    for column in PATH_CHECKPOINT_SCENE_DATASET_COLUMNS:
        if column not in dataset.columns:
            dataset[column] = ""
    for column in SCENE_FEATURE_CATEGORICAL_COLUMNS:
        if column not in dataset.columns:
            dataset[column] = ""
    for column in SCENE_FEATURE_NUMERIC_COLUMNS:
        if column not in dataset.columns:
            dataset[column] = 0.0
    for column in SCENE_FEATURE_NUMERIC_COLUMNS:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    for column in SCENE_FEATURE_CATEGORICAL_COLUMNS:
        dataset[column] = dataset[column].fillna("").astype(str)
    return dataset


def _is_all_missing(series: pd.Series) -> bool:
    return bool(series.empty or series.isna().all())


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


def _evaluate_predictions(y_true: pd.Series, y_pred: Any) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def _top_confusions(y_true: pd.Series, y_pred: Any, *, limit: int = 10) -> list[dict[str, Any]]:
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


def _scene_to_coarse_family(scene_label: str, gate_label: str) -> str:
    if gate_label and gate_label != "none":
        return "NO_TRADE"
    if scene_label in ENTRY_SCENE_LABELS:
        return "ENTRY_INITIATION"
    if scene_label in CONTINUATION_SCENE_LABELS:
        return "CONTINUATION"
    if scene_label in MANAGEMENT_SCENE_LABELS:
        return "POSITION_MANAGEMENT"
    if scene_label in DEFENSIVE_SCENE_LABELS:
        return "DEFENSIVE_EXIT"
    return "UNRESOLVED"


def _prepare_task_frame(scene_dataset: pd.DataFrame, task_name: str) -> tuple[pd.DataFrame, str]:
    frame = _ensure_feature_columns(scene_dataset)
    scoped = frame.copy()
    target_column = "scene_candidate_target"

    if task_name == "coarse_family_task":
        scoped[target_column] = [
            _scene_to_coarse_family(
                _to_text(scene_label, PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL),
                _to_text(gate_label, "none"),
            )
            for scene_label, gate_label in zip(
                scoped["hindsight_scene_fine_label"],
                scoped["runtime_scene_gate_label"],
            )
        ]
        scoped = scoped.loc[scoped[target_column] != "UNRESOLVED"].copy()
    elif task_name == "gate_task":
        scoped[target_column] = scoped["runtime_scene_gate_label"].fillna("none").astype(str)
    elif task_name == "resolved_scene_task":
        scoped[target_column] = scoped["hindsight_scene_fine_label"].fillna(PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL).astype(str)
        scoped = scoped.loc[scoped[target_column] != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL].copy()
    elif task_name == "late_scene_task":
        scoped[target_column] = scoped["hindsight_scene_fine_label"].fillna(PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL).astype(str)
        scoped = scoped.loc[scoped[target_column].isin(LATE_SCENE_LABELS)].copy()
    else:
        raise ValueError(f"unknown task_name: {task_name}")

    return scoped, target_column


def _fit_scene_task(
    task_frame: pd.DataFrame,
    *,
    task_name: str,
    target_column: str,
    min_rows: int,
    min_support: int,
    random_state: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    scoped = _ensure_feature_columns(task_frame)
    rows = int(len(scoped))
    report: dict[str, Any] = {
        "task_name": task_name,
        "rows": rows,
        "target_rows": rows,
        "skipped": True,
        "skip_reason": "",
        "supported_labels": [],
        "excluded_labels": [],
        "feature_columns": {"categorical": [], "numeric": []},
        "class_support": {"all": {}, "train": {}, "val": {}, "test": {}},
        "split": {"train_rows": 0, "val_rows": 0, "test_rows": 0},
        "model_metrics": {},
        "dummy_metrics": {},
        "top_confusions": [],
    }
    if rows < int(min_rows):
        report["skip_reason"] = f"insufficient_rows<{min_rows}"
        return report, None

    supported_labels, excluded_labels = _supported_text_classes(scoped[target_column], min_support=min_support)
    report["supported_labels"] = list(supported_labels)
    report["excluded_labels"] = list(excluded_labels)
    if len(supported_labels) < 2:
        report["skip_reason"] = "insufficient_supported_labels"
        report["class_support"]["all"] = _class_support(scoped[target_column])
        return report, None

    scoped = scoped.loc[scoped[target_column].isin(supported_labels)].copy()
    report["target_rows"] = int(len(scoped))
    if len(scoped) < int(min_rows):
        report["skip_reason"] = f"insufficient_rows_after_support_filter<{min_rows}"
        report["class_support"]["all"] = _class_support(scoped[target_column])
        return report, None

    categorical_cols, numeric_cols = _prune_all_missing_columns(
        scoped,
        categorical_cols=list(SCENE_FEATURE_CATEGORICAL_COLUMNS),
        numeric_cols=list(SCENE_FEATURE_NUMERIC_COLUMNS),
    )
    report["feature_columns"] = {"categorical": list(categorical_cols), "numeric": list(numeric_cols)}
    features = scoped[categorical_cols + numeric_cols].copy()
    target = scoped[target_column].astype(str).copy()
    if target.nunique(dropna=True) < 2:
        report["skip_reason"] = "single_target_after_filter"
        report["class_support"]["all"] = _class_support(target)
        return report, None

    splits = _split_train_val_test(features, target, random_state=random_state)
    x_train, y_train = splits["train"]
    x_val, y_val = splits["val"]
    x_test, y_test = splits["test"]
    model = _build_model_pipeline(categorical_cols, numeric_cols)
    model.fit(x_train, y_train)
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(x_train, y_train)

    val_pred = model.predict(x_val)
    test_pred = model.predict(x_test)
    dummy_val_pred = dummy.predict(x_val)
    dummy_test_pred = dummy.predict(x_test)

    final_model = _build_model_pipeline(categorical_cols, numeric_cols)
    final_model.fit(pd.concat([x_train, x_val], axis=0), pd.concat([y_train, y_val], axis=0))

    report.update(
        {
            "skipped": False,
            "skip_reason": "",
            "class_support": {
                "all": _class_support(target),
                "train": _class_support(y_train),
                "val": _class_support(y_val),
                "test": _class_support(y_test),
            },
            "split": {
                "train_rows": int(len(x_train)),
                "val_rows": int(len(x_val)),
                "test_rows": int(len(x_test)),
            },
            "model_metrics": {
                "val": _evaluate_predictions(y_val, val_pred),
                "test": _evaluate_predictions(y_test, test_pred),
            },
            "dummy_metrics": {
                "val": _evaluate_predictions(y_val, dummy_val_pred),
                "test": _evaluate_predictions(y_test, dummy_test_pred),
            },
            "top_confusions": _top_confusions(y_test, test_pred),
        }
    )
    bundle = {
        "task_name": task_name,
        "target_column": target_column,
        "supported_labels": list(supported_labels),
        "feature_columns": report["feature_columns"],
        "model": final_model,
    }
    return report, bundle


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return dict(json.loads(file_path.read_text(encoding="utf-8")) or {})


def _resolve_reference_metrics_path(candidate_root: Path) -> Path | None:
    active_state = _load_json(candidate_root / "active_candidate_state.json")
    active_candidate_id = _to_text(active_state.get("active_candidate_id"))
    if not active_candidate_id:
        return None
    candidate_metrics_path = candidate_root / active_candidate_id / "checkpoint_scene_candidate_metrics.json"
    return candidate_metrics_path if candidate_metrics_path.exists() else None


def build_checkpoint_scene_candidate_metrics_report(
    scene_dataset: pd.DataFrame | None,
    *,
    scene_eval_summary: dict[str, Any] | None = None,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset = _ensure_feature_columns(scene_dataset.copy() if scene_dataset is not None else pd.DataFrame())
    summary = dict(scene_eval_summary or {})
    report: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_METRICS_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "scene_eval_summary": summary,
        "dataset_rows": int(len(dataset)),
        "tasks": {},
    }
    bundle_payload: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_METRICS_VERSION,
        "generated_at": report["generated_at"],
        "tasks": {},
    }
    for task_name in TASK_NAMES:
        scoped, target_column = _prepare_task_frame(dataset, task_name)
        task_report, task_bundle = _fit_scene_task(
            scoped,
            task_name=task_name,
            target_column=target_column,
            min_rows=int(SCENE_TASK_CONFIG[task_name]["min_rows"]),
            min_support=int(SCENE_TASK_CONFIG[task_name]["min_support"]),
            random_state=random_state,
        )
        report["tasks"][task_name] = task_report
        if task_bundle is not None:
            bundle_payload["tasks"][task_name] = task_bundle
    report["ready_task_count"] = int(
        sum(1 for task_name in TASK_NAMES if not bool((report["tasks"].get(task_name) or {}).get("skipped", True)))
    )
    report["ready_primary_task_count"] = int(
        sum(
            1
            for task_name in PRIMARY_PROMOTION_TASKS
            if not bool((report["tasks"].get(task_name) or {}).get("skipped", True))
        )
    )
    return report, bundle_payload


def build_checkpoint_scene_candidate_compare_report(
    candidate_report: dict[str, Any],
    *,
    reference_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference = dict(reference_report or {})
    compare: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_COMPARE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "tasks": {},
    }
    candidate_tasks = dict(candidate_report.get("tasks", {}) or {})
    reference_tasks = dict(reference.get("tasks", {}) or {})
    for task_name in TASK_NAMES:
        candidate_task = dict(candidate_tasks.get(task_name, {}) or {})
        reference_task = dict(reference_tasks.get(task_name, {}) or {})
        candidate_ready = bool(candidate_task and not bool(candidate_task.get("skipped", True)))
        reference_ready = bool(reference_task and not bool(reference_task.get("skipped", True)))
        candidate_metrics = dict((candidate_task.get("model_metrics", {}) or {}).get("test", {}) or {})
        reference_metrics = dict((reference_task.get("model_metrics", {}) or {}).get("test", {}) or {})
        delta = {
            metric: round(_to_float(candidate_metrics.get(metric), 0.0) - _to_float(reference_metrics.get(metric), 0.0), 6)
            for metric in METRIC_NAMES
        }
        compare["tasks"][task_name] = {
            "candidate_ready": candidate_ready,
            "reference_ready": reference_ready,
            "newly_ready": bool(candidate_ready and not reference_ready),
            "candidate": {
                "rows": int(candidate_task.get("target_rows", candidate_task.get("rows", 0)) or 0),
                "metrics": {metric: _to_float(candidate_metrics.get(metric), 0.0) for metric in METRIC_NAMES},
                "supported_labels": list(candidate_task.get("supported_labels", []) or []),
                "class_support_test": dict((candidate_task.get("class_support", {}) or {}).get("test", {}) or {}),
                "top_confusions": list(candidate_task.get("top_confusions", []) or []),
            },
            "reference": {
                "rows": int(reference_task.get("target_rows", reference_task.get("rows", 0)) or 0),
                "metrics": {metric: _to_float(reference_metrics.get(metric), 0.0) for metric in METRIC_NAMES},
                "supported_labels": list(reference_task.get("supported_labels", []) or []),
                "class_support_test": dict((reference_task.get("class_support", {}) or {}).get("test", {}) or {}),
                "top_confusions": list(reference_task.get("top_confusions", []) or []),
            },
            "delta": delta,
        }
    return compare


def build_checkpoint_scene_candidate_promotion_decision(compare_report: dict[str, Any]) -> dict[str, Any]:
    tasks = dict(compare_report.get("tasks", {}) or {})
    blockers: list[str] = []
    warnings: list[str] = []
    improvements: list[str] = []

    any_reference_ready = any(bool((tasks.get(task_name) or {}).get("reference_ready")) for task_name in PRIMARY_PROMOTION_TASKS)
    if not any_reference_ready:
        return {
            "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_PROMOTION_VERSION,
            "decision": "shadow_only_first_candidate",
            "recommended_action": "sa5_log_only_review",
            "blockers": [],
            "warnings": [],
            "improvements": [],
        }

    for task_name in PRIMARY_PROMOTION_TASKS:
        payload = dict(tasks.get(task_name, {}) or {})
        if not payload.get("candidate_ready"):
            warnings.append(f"{task_name}_candidate_not_ready")
            continue
        delta = dict(payload.get("delta", {}) or {})
        if _to_float(delta.get("macro_f1"), 0.0) < DEFAULT_DELTA_HARD or _to_float(delta.get("balanced_accuracy"), 0.0) < DEFAULT_DELTA_HARD:
            blockers.append(f"{task_name}_metric_regression")
        elif bool(payload.get("newly_ready")) or _to_float(delta.get("macro_f1"), 0.0) > DEFAULT_DELTA_OK:
            improvements.append(f"{task_name}_macro_f1_improved")

    for task_name in SECONDARY_PROMOTION_TASKS:
        payload = dict(tasks.get(task_name, {}) or {})
        delta = dict(payload.get("delta", {}) or {})
        if payload.get("candidate_ready") and payload.get("reference_ready") and _to_float(delta.get("macro_f1"), 0.0) < DEFAULT_DELTA_HARD:
            warnings.append(f"{task_name}_regression_warning")
        elif bool(payload.get("newly_ready")) or _to_float(delta.get("macro_f1"), 0.0) > DEFAULT_DELTA_OK:
            improvements.append(f"{task_name}_macro_f1_improved")

    if blockers:
        decision = "hold_regression"
        recommended_action = "keep_current_scene_candidate"
    elif improvements:
        decision = "promote_review_ready"
        recommended_action = "sa5_log_only_review"
    else:
        decision = "hold_no_material_gain"
        recommended_action = "keep_current_scene_candidate"
    return {
        "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_PROMOTION_VERSION,
        "decision": decision,
        "recommended_action": recommended_action,
        "blockers": blockers,
        "warnings": warnings,
        "improvements": improvements,
    }


def _render_summary_md(
    *,
    candidate_id: str,
    metrics_report: dict[str, Any],
    compare_report: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> str:
    lines = [
        f"# Checkpoint Scene Candidate Summary ({candidate_id})",
        "",
        f"- generated_at: {metrics_report.get('generated_at', '')}",
        f"- dataset_rows: {metrics_report.get('dataset_rows', 0)}",
        f"- decision: {promotion_decision.get('decision', '')}",
        f"- recommended_action: {promotion_decision.get('recommended_action', '')}",
        "",
        "## Task Summary",
    ]
    tasks = dict(metrics_report.get("tasks", {}) or {})
    for task_name in TASK_NAMES:
        task = dict(tasks.get(task_name, {}) or {})
        compare_task = dict((compare_report.get("tasks", {}) or {}).get(task_name, {}) or {})
        status = "ready" if not bool(task.get("skipped", True)) else f"skipped::{task.get('skip_reason', '')}"
        lines.extend(
            [
                f"### {task_name}",
                f"- status: {status}",
                f"- target_rows: {task.get('target_rows', task.get('rows', 0))}",
                f"- supported_labels: {', '.join(task.get('supported_labels', []) or []) or '-'}",
                f"- macro_f1(test): {((task.get('model_metrics', {}) or {}).get('test', {}) or {}).get('macro_f1', 0.0):.4f}"
                if not bool(task.get("skipped", True))
                else "- macro_f1(test): skipped",
                f"- delta_macro_f1: {((compare_task.get('delta', {}) or {}).get('macro_f1', 0.0)):.4f}",
                "",
            ]
        )
    if promotion_decision.get("blockers"):
        lines.append("## Blockers")
        for blocker in promotion_decision.get("blockers", []) or []:
            lines.append(f"- {blocker}")
        lines.append("")
    if promotion_decision.get("warnings"):
        lines.append("## Warnings")
        for warning in promotion_decision.get("warnings", []) or []:
            lines.append(f"- {warning}")
        lines.append("")
    if promotion_decision.get("improvements"):
        lines.append("## Improvements")
        for improvement in promotion_decision.get("improvements", []) or []:
            lines.append(f"- {improvement}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_checkpoint_scene_candidate_pipeline(
    scene_dataset: pd.DataFrame | None,
    *,
    scene_eval_summary: dict[str, Any] | None = None,
    candidate_root: str | Path | None = None,
    candidate_id: str | None = None,
    reference_metrics_path: str | Path | None = None,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> dict[str, Any]:
    root = Path(candidate_root) if candidate_root else default_checkpoint_scene_candidate_root()
    root.mkdir(parents=True, exist_ok=True)
    resolved_candidate_id = str(candidate_id or now_kst_dt().strftime("%Y%m%d_%H%M%S"))
    output_dir = root / resolved_candidate_id
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_report, bundle_payload = build_checkpoint_scene_candidate_metrics_report(
        scene_dataset,
        scene_eval_summary=scene_eval_summary,
        random_state=random_state,
    )
    metrics_report["candidate_id"] = resolved_candidate_id

    reference_path = Path(reference_metrics_path) if reference_metrics_path else _resolve_reference_metrics_path(root)
    reference_report = _load_json(reference_path) if reference_path else {}
    compare_report = build_checkpoint_scene_candidate_compare_report(
        metrics_report,
        reference_report=reference_report,
    )
    compare_report["candidate_id"] = resolved_candidate_id
    compare_report["reference_metrics_path"] = str(reference_path) if reference_path else ""
    promotion_decision = build_checkpoint_scene_candidate_promotion_decision(compare_report)
    summary_md = _render_summary_md(
        candidate_id=resolved_candidate_id,
        metrics_report=metrics_report,
        compare_report=compare_report,
        promotion_decision=promotion_decision,
    )

    bundle_path = output_dir / "checkpoint_scene_candidate_bundle.joblib"
    metrics_path = output_dir / "checkpoint_scene_candidate_metrics.json"
    compare_path = output_dir / "checkpoint_scene_candidate_compare_report.json"
    promotion_path = output_dir / "checkpoint_scene_candidate_promotion_decision.json"
    summary_md_path = output_dir / "checkpoint_scene_candidate_summary.md"
    manifest_path = output_dir / "checkpoint_scene_candidate_run_manifest.json"

    joblib.dump(bundle_payload, bundle_path)
    metrics_path.write_text(json.dumps(metrics_report, ensure_ascii=False, indent=2), encoding="utf-8")
    compare_path.write_text(json.dumps(compare_report, ensure_ascii=False, indent=2), encoding="utf-8")
    promotion_path.write_text(json.dumps(promotion_decision, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text(summary_md, encoding="utf-8")

    manifest = {
        "contract_version": PATH_CHECKPOINT_SCENE_CANDIDATE_RUN_MANIFEST_VERSION,
        "candidate_id": resolved_candidate_id,
        "generated_at": now_kst_dt().isoformat(),
        "output_dir": str(output_dir),
        "reference_metrics_path": str(reference_path) if reference_path else "",
        "candidate_metrics_path": str(metrics_path),
        "candidate_bundle_path": str(bundle_path),
        "compare_report_path": str(compare_path),
        "promotion_decision_path": str(promotion_path),
        "summary_md_path": str(summary_md_path),
        "promotion_decision": promotion_decision,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "latest_candidate_run.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
