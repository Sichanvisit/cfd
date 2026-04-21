"""Inspect whether the semantic shadow bundle can be linked, built, or is still blocked."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from backend.services.trade_csv_schema import now_kst_dt
from ml.semantic_v1.dataset_builder import (
    DEFAULT_FEATURE_DIR,
    DEFAULT_FEATURE_FALLBACK_DIR,
    DEFAULT_OUTPUT_DIR as DEFAULT_SEMANTIC_DATASET_DIR,
    DEFAULT_REPLAY_DIR,
)
from ml.semantic_v1.evaluate import DEFAULT_MODEL_DIR
from ml.semantic_v1.feature_packs import SEMANTIC_INPUT_COLUMNS, TRACE_QUALITY_COLUMNS
from ml.semantic_v1.runtime_adapter import MODEL_FILE_MAP


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS_ROOT = PROJECT_ROOT / "models"
DEFAULT_ARCHIVE_ROOT = PROJECT_ROOT / "data" / "trades" / "archive" / "entry_decisions"
DEFAULT_TRADES_ROOT = PROJECT_ROOT / "data" / "trades"
DEFAULT_FORECAST_OUTCOME_BRIDGE_PATH = (
    PROJECT_ROOT / "data" / "analysis" / "forecast_state25" / "forecast_state25_outcome_bridge_latest.json"
)
DEFAULT_TRAINING_BRIDGE_PATH = (
    PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_bridge_adapter_latest.json"
)

SEMANTIC_SHADOW_BUNDLE_BOOTSTRAP_VERSION = "semantic_shadow_bundle_bootstrap_v0"

SEMANTIC_SHADOW_BUNDLE_BOOTSTRAP_COLUMNS = [
    "generated_at",
    "model_dir",
    "active_bundle_ready",
    "active_bundle_count",
    "preview_bundle_ready",
    "preview_bundle_dir_count",
    "preview_bundle_dirs",
    "semantic_dataset_dir",
    "semantic_dataset_ready",
    "semantic_dataset_count",
    "timing_dataset_exists",
    "entry_quality_dataset_exists",
    "exit_management_dataset_exists",
    "default_feature_source",
    "default_feature_source_exists",
    "fallback_feature_source",
    "fallback_feature_source_exists",
    "replay_source",
    "replay_source_exists",
    "archive_entry_decision_parquet_count",
    "archive_semantic_feature_column_count",
    "archive_semantic_feature_coverage_ratio",
    "archive_replay_key_supported",
    "detail_jsonl_count",
    "forecast_outcome_bridge_path",
    "forecast_outcome_bridge_exists",
    "forecast_outcome_bridge_row_count",
    "forecast_outcome_bridge_row_key_count",
    "forecast_bridge_archive_key_match_count",
    "training_bridge_path",
    "training_bridge_exists",
    "training_bridge_row_count",
    "training_bridge_matched_row_count",
    "training_bridge_match_rate",
    "training_bridge_ready",
    "bootstrap_status",
    "recommended_next_action",
    "blocking_summary",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else default


def _required_bundle_files() -> list[str]:
    return [
        MODEL_FILE_MAP["timing"],
        MODEL_FILE_MAP["entry_quality"],
        MODEL_FILE_MAP["exit_management"],
        "metrics.json",
    ]


def _bundle_inventory(model_dir: Path) -> dict[str, Any]:
    required = _required_bundle_files()
    exists = {name: (model_dir / name).exists() for name in required}
    return {
        "model_dir": str(model_dir),
        "active_bundle_ready": bool(all(exists.values())),
        "active_bundle_count": int(sum(bool(v) for v in exists.values())),
        "required_file_exists": exists,
    }


def _discover_preview_bundle_dirs(models_root: Path, active_model_dir: Path) -> list[Path]:
    required = _required_bundle_files()
    parents: dict[Path, set[str]] = {}
    for file_name in required:
        for path in models_root.rglob(file_name):
            parent = path.parent
            if parent == active_model_dir:
                continue
            parents.setdefault(parent, set()).add(file_name)
    ready_dirs = [parent for parent, files in parents.items() if all(name in files for name in required)]
    return sorted(set(ready_dirs))


def _semantic_dataset_inventory(dataset_dir: Path) -> dict[str, Any]:
    expected = {
        "timing_dataset_exists": (dataset_dir / "timing_dataset.parquet").exists(),
        "entry_quality_dataset_exists": (dataset_dir / "entry_quality_dataset.parquet").exists(),
        "exit_management_dataset_exists": (dataset_dir / "exit_management_dataset.parquet").exists(),
    }
    return {
        "semantic_dataset_dir": str(dataset_dir),
        "semantic_dataset_ready": bool(all(expected.values())),
        "semantic_dataset_count": int(sum(bool(v) for v in expected.values())),
        **expected,
    }


def _archive_inventory(archive_root: Path) -> dict[str, Any]:
    parquet_files = sorted(archive_root.rglob("*.parquet")) if archive_root.exists() else []
    if not parquet_files:
        return {
            "archive_entry_decision_parquet_count": 0,
            "archive_semantic_feature_column_count": 0,
            "archive_semantic_feature_coverage_ratio": 0.0,
            "archive_replay_key_supported": False,
        }

    semantic_columns = set(SEMANTIC_INPUT_COLUMNS) | set(TRACE_QUALITY_COLUMNS)
    try:
        schema_names = set(pq.ParquetFile(parquet_files[0]).schema_arrow.names)
    except Exception:
        schema_names = set()
    semantic_feature_count = len(schema_names & semantic_columns)
    coverage_ratio = round(
        float(semantic_feature_count) / float(max(1, len(semantic_columns))),
        6,
    )
    replay_key_supported = "replay_row_key" in schema_names
    return {
        "archive_entry_decision_parquet_count": int(len(parquet_files)),
        "archive_semantic_feature_column_count": int(semantic_feature_count),
        "archive_semantic_feature_coverage_ratio": coverage_ratio,
        "archive_replay_key_supported": bool(replay_key_supported),
    }


def _detail_jsonl_count(trades_root: Path) -> int:
    if not trades_root.exists():
        return 0
    return int(len(list(trades_root.glob("entry_decisions.detail*.jsonl"))))


def _forecast_outcome_bridge_inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "forecast_outcome_bridge_path": str(path),
            "forecast_outcome_bridge_exists": False,
            "forecast_outcome_bridge_row_count": 0,
            "forecast_outcome_bridge_row_key_count": 0,
            "forecast_bridge_archive_key_match_count": 0,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    row_keys = {
        str(row.get("row_key", "") or "").strip()
        for row in rows
        if isinstance(row, dict)
    }
    row_keys.discard("")
    return {
        "forecast_outcome_bridge_path": str(path),
        "forecast_outcome_bridge_exists": True,
        "forecast_outcome_bridge_row_count": int(len(rows)),
        "forecast_outcome_bridge_row_key_count": int(len(row_keys)),
        "row_keys": row_keys,
    }


def _training_bridge_inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "training_bridge_path": str(path),
            "training_bridge_exists": False,
            "training_bridge_row_count": 0,
            "training_bridge_matched_row_count": 0,
            "training_bridge_match_rate": 0.0,
            "training_bridge_ready": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    row_count = int(summary.get("bridge_row_count", len(rows)))
    matched_row_count = int(
        summary.get(
            "matched_row_count",
            sum(1 for row in rows if isinstance(row, dict) and _to_text(row.get("match_status")) == "matched"),
        )
    )
    match_rate = float(summary.get("match_rate", float(matched_row_count) / float(max(1, row_count))))
    training_bridge_ready = bool(summary.get("training_bridge_ready", matched_row_count > 0))
    return {
        "training_bridge_path": str(path),
        "training_bridge_exists": True,
        "training_bridge_row_count": row_count,
        "training_bridge_matched_row_count": matched_row_count,
        "training_bridge_match_rate": round(match_rate, 6),
        "training_bridge_ready": training_bridge_ready,
    }


def _archive_bridge_key_match_count(row_keys: set[str], archive_root: Path) -> int:
    if not row_keys or not archive_root.exists():
        return 0
    matched: set[str] = set()
    for parquet_path in archive_root.rglob("*.parquet"):
        try:
            parquet = pq.ParquetFile(parquet_path)
        except Exception:
            continue
        if "replay_row_key" not in parquet.schema_arrow.names:
            continue
        try:
            frame = pd.read_parquet(parquet_path, columns=["replay_row_key"])
        except Exception:
            continue
        archive_keys = set(frame["replay_row_key"].fillna("").astype(str).str.strip())
        archive_keys.discard("")
        overlap = row_keys & archive_keys
        if overlap:
            matched.update(overlap)
            if len(matched) >= len(row_keys):
                break
    return int(len(matched))


def _bootstrap_status(
    *,
    active_bundle_ready: bool,
    preview_bundle_ready: bool,
    semantic_dataset_ready: bool,
    training_bridge_ready: bool,
    default_feature_source_exists: bool,
    fallback_feature_source_exists: bool,
    replay_source_exists: bool,
    archive_entry_decision_parquet_count: int,
    archive_replay_key_supported: bool,
    forecast_outcome_bridge_exists: bool,
    forecast_bridge_archive_key_match_count: int,
) -> tuple[str, str, list[str]]:
    blockers: list[str] = []
    if active_bundle_ready:
        return ("active_bundle_ready", "shadow_runtime_can_activate", blockers)
    if preview_bundle_ready:
        return ("preview_bundle_ready", "promote_preview_bundle", blockers)
    if semantic_dataset_ready:
        return ("semantic_datasets_ready", "train_bundle_from_semantic_datasets", blockers)
    if training_bridge_ready:
        return ("training_bridge_ready", "train_semantic_bundle_from_bridge_adapter", blockers)
    if (default_feature_source_exists or fallback_feature_source_exists) and replay_source_exists:
        return ("raw_sources_ready", "build_semantic_datasets_then_train", blockers)

    if archive_entry_decision_parquet_count <= 0:
        blockers.append("archive_feature_source_missing")
    elif not archive_replay_key_supported:
        blockers.append("archive_replay_key_missing")

    if not forecast_outcome_bridge_exists:
        blockers.append("forecast_outcome_bridge_missing")
    elif forecast_bridge_archive_key_match_count <= 0:
        blockers.append("forecast_bridge_archive_join_keys_missing")

    if archive_entry_decision_parquet_count > 0 and forecast_outcome_bridge_exists:
        return (
            "bridge_adapter_required",
            "build_bridge_adapter_for_semantic_training",
            blockers,
        )
    return ("blocked_missing_semantic_sources", "collect_or_export_semantic_training_sources", blockers)


def build_semantic_shadow_bundle_bootstrap(
    *,
    model_dir: str | Path | None = None,
    models_root: str | Path | None = None,
    semantic_dataset_dir: str | Path | None = None,
    feature_source: str | Path | None = None,
    feature_fallback_source: str | Path | None = None,
    replay_source: str | Path | None = None,
    archive_root: str | Path | None = None,
    trades_root: str | Path | None = None,
    forecast_outcome_bridge_path: str | Path | None = None,
    training_bridge_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    active_model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
    resolved_models_root = Path(models_root) if models_root is not None else DEFAULT_MODELS_ROOT
    resolved_semantic_dataset_dir = Path(semantic_dataset_dir) if semantic_dataset_dir is not None else DEFAULT_SEMANTIC_DATASET_DIR
    resolved_feature_source = Path(feature_source) if feature_source is not None else DEFAULT_FEATURE_DIR
    resolved_feature_fallback_source = Path(feature_fallback_source) if feature_fallback_source is not None else DEFAULT_FEATURE_FALLBACK_DIR
    resolved_replay_source = Path(replay_source) if replay_source is not None else DEFAULT_REPLAY_DIR
    resolved_archive_root = Path(archive_root) if archive_root is not None else DEFAULT_ARCHIVE_ROOT
    resolved_trades_root = Path(trades_root) if trades_root is not None else DEFAULT_TRADES_ROOT
    resolved_outcome_bridge = (
        Path(forecast_outcome_bridge_path) if forecast_outcome_bridge_path is not None else DEFAULT_FORECAST_OUTCOME_BRIDGE_PATH
    )
    resolved_training_bridge = (
        Path(training_bridge_path) if training_bridge_path is not None else DEFAULT_TRAINING_BRIDGE_PATH
    )

    bundle_inventory = _bundle_inventory(active_model_dir)
    preview_dirs = _discover_preview_bundle_dirs(resolved_models_root, active_model_dir)
    dataset_inventory = _semantic_dataset_inventory(resolved_semantic_dataset_dir)
    archive_inventory = _archive_inventory(resolved_archive_root)
    bridge_inventory = _forecast_outcome_bridge_inventory(resolved_outcome_bridge)
    training_bridge_inventory = _training_bridge_inventory(resolved_training_bridge)
    bridge_match_count = _archive_bridge_key_match_count(
        set(bridge_inventory.pop("row_keys", set())),
        resolved_archive_root,
    )
    detail_jsonl_count = _detail_jsonl_count(resolved_trades_root)

    bootstrap_status, recommended_next_action, blockers = _bootstrap_status(
        active_bundle_ready=bool(bundle_inventory["active_bundle_ready"]),
        preview_bundle_ready=bool(preview_dirs),
        semantic_dataset_ready=bool(dataset_inventory["semantic_dataset_ready"]),
        training_bridge_ready=bool(training_bridge_inventory["training_bridge_ready"]),
        default_feature_source_exists=resolved_feature_source.exists(),
        fallback_feature_source_exists=resolved_feature_fallback_source.exists(),
        replay_source_exists=resolved_replay_source.exists(),
        archive_entry_decision_parquet_count=int(archive_inventory["archive_entry_decision_parquet_count"]),
        archive_replay_key_supported=bool(archive_inventory["archive_replay_key_supported"]),
        forecast_outcome_bridge_exists=bool(bridge_inventory["forecast_outcome_bridge_exists"]),
        forecast_bridge_archive_key_match_count=int(bridge_match_count),
    )

    row = {
        "generated_at": now_kst_dt().isoformat(),
        "model_dir": bundle_inventory["model_dir"],
        "active_bundle_ready": bundle_inventory["active_bundle_ready"],
        "active_bundle_count": bundle_inventory["active_bundle_count"],
        "preview_bundle_ready": bool(preview_dirs),
        "preview_bundle_dir_count": int(len(preview_dirs)),
        "preview_bundle_dirs": str([str(path) for path in preview_dirs]),
        "semantic_dataset_dir": dataset_inventory["semantic_dataset_dir"],
        "semantic_dataset_ready": dataset_inventory["semantic_dataset_ready"],
        "semantic_dataset_count": dataset_inventory["semantic_dataset_count"],
        "timing_dataset_exists": dataset_inventory["timing_dataset_exists"],
        "entry_quality_dataset_exists": dataset_inventory["entry_quality_dataset_exists"],
        "exit_management_dataset_exists": dataset_inventory["exit_management_dataset_exists"],
        "default_feature_source": str(resolved_feature_source),
        "default_feature_source_exists": resolved_feature_source.exists(),
        "fallback_feature_source": str(resolved_feature_fallback_source),
        "fallback_feature_source_exists": resolved_feature_fallback_source.exists(),
        "replay_source": str(resolved_replay_source),
        "replay_source_exists": resolved_replay_source.exists(),
        "archive_entry_decision_parquet_count": archive_inventory["archive_entry_decision_parquet_count"],
        "archive_semantic_feature_column_count": archive_inventory["archive_semantic_feature_column_count"],
        "archive_semantic_feature_coverage_ratio": archive_inventory["archive_semantic_feature_coverage_ratio"],
        "archive_replay_key_supported": archive_inventory["archive_replay_key_supported"],
        "detail_jsonl_count": detail_jsonl_count,
        "forecast_outcome_bridge_path": bridge_inventory["forecast_outcome_bridge_path"],
        "forecast_outcome_bridge_exists": bridge_inventory["forecast_outcome_bridge_exists"],
        "forecast_outcome_bridge_row_count": bridge_inventory["forecast_outcome_bridge_row_count"],
        "forecast_outcome_bridge_row_key_count": bridge_inventory["forecast_outcome_bridge_row_key_count"],
        "forecast_bridge_archive_key_match_count": bridge_match_count,
        "training_bridge_path": training_bridge_inventory["training_bridge_path"],
        "training_bridge_exists": training_bridge_inventory["training_bridge_exists"],
        "training_bridge_row_count": training_bridge_inventory["training_bridge_row_count"],
        "training_bridge_matched_row_count": training_bridge_inventory["training_bridge_matched_row_count"],
        "training_bridge_match_rate": training_bridge_inventory["training_bridge_match_rate"],
        "training_bridge_ready": training_bridge_inventory["training_bridge_ready"],
        "bootstrap_status": bootstrap_status,
        "recommended_next_action": recommended_next_action,
        "blocking_summary": "|".join(blockers),
    }
    frame = pd.DataFrame([row], columns=SEMANTIC_SHADOW_BUNDLE_BOOTSTRAP_COLUMNS)
    summary = {
        "semantic_shadow_bundle_bootstrap_version": SEMANTIC_SHADOW_BUNDLE_BOOTSTRAP_VERSION,
        "generated_at": row["generated_at"],
        "bootstrap_status": bootstrap_status,
        "recommended_next_action": recommended_next_action,
        "active_bundle_ready": bool(bundle_inventory["active_bundle_ready"]),
        "preview_bundle_dir_count": int(len(preview_dirs)),
        "semantic_dataset_ready": bool(dataset_inventory["semantic_dataset_ready"]),
        "default_feature_source_exists": resolved_feature_source.exists(),
        "fallback_feature_source_exists": resolved_feature_fallback_source.exists(),
        "replay_source_exists": resolved_replay_source.exists(),
        "archive_entry_decision_parquet_count": int(archive_inventory["archive_entry_decision_parquet_count"]),
        "forecast_outcome_bridge_row_count": int(bridge_inventory["forecast_outcome_bridge_row_count"]),
        "forecast_bridge_archive_key_match_count": int(bridge_match_count),
        "training_bridge_exists": bool(training_bridge_inventory["training_bridge_exists"]),
        "training_bridge_row_count": int(training_bridge_inventory["training_bridge_row_count"]),
        "training_bridge_matched_row_count": int(training_bridge_inventory["training_bridge_matched_row_count"]),
        "training_bridge_match_rate": float(training_bridge_inventory["training_bridge_match_rate"]),
        "training_bridge_ready": bool(training_bridge_inventory["training_bridge_ready"]),
        "blocking_issues": blockers,
    }
    return frame, summary


def render_semantic_shadow_bundle_bootstrap_markdown(
    summary: dict[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Shadow Bundle Bootstrap",
        "",
        f"- version: `{summary.get('semantic_shadow_bundle_bootstrap_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- bootstrap_status: `{summary.get('bootstrap_status', '')}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
        "## Active Bundle",
        "",
        f"- model_dir: `{row.get('model_dir', '')}`",
        f"- active_bundle_ready: `{row.get('active_bundle_ready', False)}`",
        f"- active_bundle_count: `{row.get('active_bundle_count', 0)}`",
        "",
        "## Preview / Dataset Readiness",
        "",
        f"- preview_bundle_dir_count: `{row.get('preview_bundle_dir_count', 0)}`",
        f"- preview_bundle_dirs: `{row.get('preview_bundle_dirs', '')}`",
        f"- semantic_dataset_ready: `{row.get('semantic_dataset_ready', False)}`",
        f"- semantic_dataset_count: `{row.get('semantic_dataset_count', 0)}`",
        "",
        "## Raw / Bridge Inputs",
        "",
        f"- default_feature_source_exists: `{row.get('default_feature_source_exists', False)}`",
        f"- fallback_feature_source_exists: `{row.get('fallback_feature_source_exists', False)}`",
        f"- replay_source_exists: `{row.get('replay_source_exists', False)}`",
        f"- archive_entry_decision_parquet_count: `{row.get('archive_entry_decision_parquet_count', 0)}`",
        f"- archive_semantic_feature_column_count: `{row.get('archive_semantic_feature_column_count', 0)}`",
        f"- archive_semantic_feature_coverage_ratio: `{row.get('archive_semantic_feature_coverage_ratio', 0.0)}`",
        f"- archive_replay_key_supported: `{row.get('archive_replay_key_supported', False)}`",
        f"- detail_jsonl_count: `{row.get('detail_jsonl_count', 0)}`",
        f"- forecast_outcome_bridge_exists: `{row.get('forecast_outcome_bridge_exists', False)}`",
        f"- forecast_outcome_bridge_row_count: `{row.get('forecast_outcome_bridge_row_count', 0)}`",
        f"- forecast_outcome_bridge_row_key_count: `{row.get('forecast_outcome_bridge_row_key_count', 0)}`",
        f"- forecast_bridge_archive_key_match_count: `{row.get('forecast_bridge_archive_key_match_count', 0)}`",
        f"- training_bridge_exists: `{row.get('training_bridge_exists', False)}`",
        f"- training_bridge_row_count: `{row.get('training_bridge_row_count', 0)}`",
        f"- training_bridge_matched_row_count: `{row.get('training_bridge_matched_row_count', 0)}`",
        f"- training_bridge_match_rate: `{row.get('training_bridge_match_rate', 0.0)}`",
        f"- training_bridge_ready: `{row.get('training_bridge_ready', False)}`",
        "",
        "## Blocking Issues",
        "",
        f"- blocking_issues: `{summary.get('blocking_issues', [])}`",
        "",
    ]
    return "\n".join(lines)
