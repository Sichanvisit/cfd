"""Train a preview semantic shadow model bundle from proxy datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from ml.semantic_v1.evaluate import build_train_config, train_semantic_model
from ml.semantic_v1.runtime_adapter import MODEL_FILE_MAP


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "models" / "semantic_v1_preview_bridge_proxy"

SEMANTIC_SHADOW_PREVIEW_BUNDLE_VERSION = "semantic_shadow_preview_bundle_v0"
SEMANTIC_SHADOW_PREVIEW_BUNDLE_COLUMNS = [
    "dataset_key",
    "dataset_path",
    "model_path",
    "model_summary_path",
    "metrics_path",
    "rows",
    "accuracy",
    "auc",
    "expected_value_proxy",
    "split_health_status",
    "train_rows",
    "validation_rows",
    "test_rows",
]


def build_semantic_shadow_preview_bundle(
    *,
    dataset_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    resolved_dataset_dir = Path(dataset_dir) if dataset_dir is not None else DEFAULT_DATASET_DIR
    resolved_output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    rows: list[dict[str, Any]] = []
    trained_targets: list[str] = []
    for dataset_key in ("timing", "entry_quality", "exit_management"):
        config = build_train_config(
            dataset_key,
            dataset_path=resolved_dataset_dir / f"{dataset_key}_dataset.parquet",
            output_dir=resolved_output_dir,
        )
        result = train_semantic_model(config)
        metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), Mapping) else {}
        rows.append(
            {
                "dataset_key": dataset_key,
                "dataset_path": str(config.dataset_path),
                "model_path": str(result.get("model_path", "")),
                "model_summary_path": str(result.get("model_summary_path", "")),
                "metrics_path": str(result.get("metrics_path", "")),
                "rows": int(metrics.get("rows", 0) or 0),
                "accuracy": metrics.get("accuracy"),
                "auc": metrics.get("auc"),
                "expected_value_proxy": metrics.get("expected_value_proxy"),
                "split_health_status": str(metrics.get("split_health_status", "") or ""),
                "train_rows": int(metrics.get("train_rows", 0) or 0),
                "validation_rows": int(metrics.get("validation_rows", 0) or 0),
                "test_rows": int(metrics.get("test_rows", 0) or 0),
            }
        )
        trained_targets.append(dataset_key)

    frame = pd.DataFrame(rows, columns=SEMANTIC_SHADOW_PREVIEW_BUNDLE_COLUMNS)
    bundle_ready = all((resolved_output_dir / name).exists() for name in [*MODEL_FILE_MAP.values(), "metrics.json"])
    summary = {
        "semantic_shadow_preview_bundle_version": SEMANTIC_SHADOW_PREVIEW_BUNDLE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "dataset_dir": str(resolved_dataset_dir),
        "output_dir": str(resolved_output_dir),
        "trained_targets": trained_targets,
        "bundle_ready": bundle_ready,
        "target_auc": frame.set_index("dataset_key")["auc"].to_dict() if not frame.empty else {},
        "target_accuracy": frame.set_index("dataset_key")["accuracy"].to_dict() if not frame.empty else {},
        "split_health_status": frame.set_index("dataset_key")["split_health_status"].to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_semantic_shadow_preview_bundle_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Semantic Shadow Preview Bundle",
        "",
        f"- version: `{summary.get('semantic_shadow_preview_bundle_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- bundle_ready: `{summary.get('bundle_ready', False)}`",
        f"- output_dir: `{summary.get('output_dir', '')}`",
        "",
        "## Targets",
        "",
    ]
    for row in frame.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('dataset_key', '')}",
                "",
                f"- rows: `{row.get('rows', 0)}`",
                f"- accuracy: `{row.get('accuracy', None)}`",
                f"- auc: `{row.get('auc', None)}`",
                f"- expected_value_proxy: `{row.get('expected_value_proxy', None)}`",
                f"- split_health_status: `{row.get('split_health_status', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
