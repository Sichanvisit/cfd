from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
import pyarrow.parquet as pq

from ml.semantic_v1.contracts import (
    SEMANTIC_FEATURE_CONTRACT_VERSION,
    SEMANTIC_TARGET_CONTRACT_VERSION,
)
from ml.semantic_v1.dataset_splits import (
    DATASET_SPLIT_CONTRACT_VERSION,
    DEFAULT_REGIME_HOLDOUT_FRACTION,
    DEFAULT_SYMBOL_HOLDOUT_FRACTION,
    DEFAULT_TIME_SPLIT,
    SplitSummary,
    attach_split_columns,
)
from ml.semantic_v1.feature_packs import SEMANTIC_INPUT_COLUMNS, TRACE_QUALITY_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURE_DIR = PROJECT_ROOT / "data" / "datasets" / "ml_exports" / "replay"
DEFAULT_FEATURE_FALLBACK_DIR = PROJECT_ROOT / "data" / "datasets" / "ml_exports" / "forecast"
DEFAULT_REPLAY_DIR = PROJECT_ROOT / "data" / "datasets" / "replay_intermediate"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "datasets" / "semantic_v1"
DEFAULT_MANIFEST_ROOT = PROJECT_ROOT / "data" / "manifests"

DATASET_BUILDER_VERSION = "semantic_v1_dataset_builder_v4"
DATASET_MANIFEST_VERSION = "semantic_v1_dataset_manifest_v1"
DATASET_MISSINGNESS_VERSION = "semantic_v1_dataset_missingness_v1"
DATASET_SUMMARY_VERSION = "semantic_v1_dataset_summary_v1"
DATASET_JOIN_HEALTH_VERSION = "semantic_v1_dataset_join_health_v1"
FEATURE_TIER_POLICY_VERSION = "semantic_feature_tier_policy_v1"
TIMING_TIE_QUALITY_THRESHOLD = 0.0005
ENTRY_QUALITY_POSITIVE_THRESHOLD = 0.0025
ENTRY_QUALITY_NEGATIVE_THRESHOLD = -0.0002
ENTRY_QUALITY_TREND_POSITIVE_THRESHOLD = 0.009
ENTRY_QUALITY_FALLBACK_HEAVY_THRESHOLD = 2
ENTRY_QUALITY_MISSING_FEATURE_HEAVY_THRESHOLD = 4
SOURCE_GENERATION_LEGACY = "legacy"
SOURCE_GENERATION_MODERN = "modern"
SOURCE_GENERATION_MIXED = "mixed"
SOURCE_GENERATION_UNKNOWN = "unknown"

KEY_COLUMNS = (
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
)
JOIN_AUX_COLUMNS = (
    "join_key",
    "join_ordinal",
)

METADATA_COLUMNS = (
    "time",
    "signal_bar_ts",
    "signal_timeframe",
    "symbol",
    "action",
    "outcome",
    "blocked_by",
    "setup_id",
    "setup_side",
    "entry_stage",
    "preflight_regime",
    "preflight_liquidity",
)

LABEL_COLUMNS = (
    "transition_label_status",
    "management_label_status",
    "label_unknown_count",
    "label_positive_count",
    "label_negative_count",
    "label_is_ambiguous",
    "label_source_descriptor",
    "is_censored",
    "transition_positive_count",
    "transition_negative_count",
    "transition_unknown_count",
    "management_positive_count",
    "management_negative_count",
    "management_unknown_count",
    "transition_direction",
    "transition_same_side_positive_count",
    "transition_adverse_positive_count",
    "transition_quality_score",
    "management_exit_favor_positive_count",
    "management_hold_favor_positive_count",
    "semantic_target_source",
)

SPLIT_COLUMNS = (
    "event_ts",
    "time_split_bucket",
    "symbol_holdout_bucket",
    "regime_holdout_bucket",
    "is_symbol_holdout",
    "is_regime_holdout",
)

COMMON_FEATURE_COLUMNS = tuple(dict.fromkeys([*SEMANTIC_INPUT_COLUMNS, *TRACE_QUALITY_COLUMNS]))
COMMON_DATASET_COLUMNS = tuple(dict.fromkeys([*KEY_COLUMNS, *METADATA_COLUMNS, *COMMON_FEATURE_COLUMNS, *LABEL_COLUMNS, *SPLIT_COLUMNS]))
TRACE_QUALITY_VALUE_COLUMNS = tuple(column for column in TRACE_QUALITY_COLUMNS if column not in KEY_COLUMNS)
FEATURE_VALUE_COLUMNS = tuple(column for column in COMMON_FEATURE_COLUMNS if column not in KEY_COLUMNS)
FEATURE_TIER_BY_COLUMN = {
    **{column: "semantic_input_pack" for column in SEMANTIC_INPUT_COLUMNS},
    **{column: "trace_quality_pack" for column in TRACE_QUALITY_VALUE_COLUMNS},
}

TARGET_CONFIG = {
    "timing": {
        "file_name": "timing_dataset.parquet",
        "target_column": "target_timing_now_vs_wait",
        "margin_column": "target_timing_margin",
        "positive_column": "transition_positive_count",
        "negative_column": "transition_negative_count",
        "status_column": "transition_label_status",
    },
    "entry_quality": {
        "file_name": "entry_quality_dataset.parquet",
        "target_column": "target_entry_quality",
        "margin_column": "target_entry_quality_margin",
        "positive_column": "label_positive_count",
        "negative_column": "label_negative_count",
        "status_column": "transition_label_status",
    },
    "exit_management": {
        "file_name": "exit_management_dataset.parquet",
        "target_column": "target_exit_management",
        "margin_column": "target_exit_management_margin",
        "positive_column": "management_positive_count",
        "negative_column": "management_negative_count",
        "status_column": "management_label_status",
    },
}


@dataclass(frozen=True)
class DatasetArtifact:
    dataset_key: str
    output_path: Path
    summary_path: Path
    missingness_path: Path
    row_count: int
    selected_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    split_summary: SplitSummary
    source_generation: str
    feature_tier_policy: Mapping[str, str]
    feature_tier_summary: Mapping[str, Any]
    retained_feature_columns: tuple[str, ...]
    dropped_feature_columns: tuple[str, ...]
    dropped_feature_reasons: Mapping[str, str]
    observed_only_dropped_feature_columns: tuple[str, ...]


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}


def _normalize_polarity(value: Any) -> str:
    return str(value or "").strip().upper()


def _coerce_bool_or_none(value: Any) -> bool | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _positive_polarity_count(polarities: Mapping[str, Any], *label_names: str) -> int:
    total = 0
    for label_name in label_names:
        if _normalize_polarity(polarities.get(label_name)) == "POSITIVE":
            total += 1
    return total


def _transition_direction(
    *,
    decision_row: Mapping[str, Any],
    transition_metadata: Mapping[str, Any],
) -> str:
    position_context = _coerce_mapping(transition_metadata.get("position_context"))
    if (side := str(position_context.get("direction", "") or "").strip().upper()) in {"BUY", "SELL"}:
        return side
    for field in ("setup_side", "action", "side"):
        side = str(decision_row.get(field, "") or "").strip().upper()
        if side in {"BUY", "SELL"}:
            return side
    return ""


def _transition_quality_score(
    *,
    direction: str,
    path_metrics: Mapping[str, Any],
) -> float:
    bullish = float(path_metrics.get("bullish_move_ratio", 0.0) or 0.0)
    bearish = float(path_metrics.get("bearish_move_ratio", 0.0) or 0.0)
    if direction == "SELL":
        favorable = bearish
        adverse = bullish
    else:
        favorable = bullish
        adverse = bearish
    return round(favorable - (0.8 * adverse), 6)


def _extract_outcome_target_features(
    row: Mapping[str, Any],
) -> dict[str, Any]:
    outcome_bundle = _coerce_mapping(row.get("outcome_labels_v1"))
    if not outcome_bundle:
        return {}

    decision_row = _coerce_mapping(row.get("decision_row"))
    transition_bundle = _coerce_mapping(outcome_bundle.get("transition"))
    transition_metadata = _coerce_mapping(transition_bundle.get("metadata"))
    transition_polarities = _coerce_mapping(transition_metadata.get("label_polarities"))
    transition_path_metrics = _coerce_mapping(transition_metadata.get("path_metrics"))
    direction = _transition_direction(decision_row=decision_row, transition_metadata=transition_metadata)

    same_confirm_label = "buy_confirm_success_label" if direction == "BUY" else "sell_confirm_success_label" if direction == "SELL" else ""
    opposite_confirm_label = "sell_confirm_success_label" if direction == "BUY" else "buy_confirm_success_label" if direction == "SELL" else ""

    transition_same_side_positive_count = _positive_polarity_count(
        transition_polarities,
        same_confirm_label,
        "reversal_success_label",
        "continuation_success_label",
    )
    transition_adverse_positive_count = _positive_polarity_count(
        transition_polarities,
        opposite_confirm_label,
        "false_break_label",
    )

    management_bundle = _coerce_mapping(outcome_bundle.get("trade_management"))
    management_metadata = _coerce_mapping(management_bundle.get("metadata"))
    management_polarities = _coerce_mapping(management_metadata.get("label_polarities"))
    management_exit_favor_positive_count = _positive_polarity_count(
        management_polarities,
        "fail_now_label",
        "better_reentry_if_cut_label",
        "opposite_edge_reach_label",
    )
    management_hold_favor_positive_count = _positive_polarity_count(
        management_polarities,
        "continue_favor_label",
        "reach_tp1_label",
        "recover_after_pullback_label",
    )

    return {
        "transition_direction": direction,
        "transition_same_side_positive_count": transition_same_side_positive_count,
        "transition_adverse_positive_count": transition_adverse_positive_count,
        "transition_quality_score": _transition_quality_score(direction=direction, path_metrics=transition_path_metrics),
        "management_exit_favor_positive_count": management_exit_favor_positive_count,
        "management_hold_favor_positive_count": management_hold_favor_positive_count,
        "semantic_target_source": 1,
    }


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    target = Path(value) if value is not None else default
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    return target


def _ensure_manifest_dirs(manifest_root: Path) -> dict[str, Path]:
    mapping = {"export": manifest_root / "export"}
    for path in mapping.values():
        path.mkdir(parents=True, exist_ok=True)
    return mapping


def _write_manifest(dir_path: Path, prefix: str, payload: Mapping[str, Any], timestamp: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{prefix}_{timestamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _resolve_feature_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    files = sorted(item for item in path.glob("*.parquet") if item.is_file())
    if files:
        return files
    if path == DEFAULT_FEATURE_DIR and DEFAULT_FEATURE_FALLBACK_DIR.exists():
        return sorted(item for item in DEFAULT_FEATURE_FALLBACK_DIR.glob("*.parquet") if item.is_file())
    return []


def _resolve_replay_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(item for item in path.glob("*.jsonl") if item.is_file())


def _detect_source_generation(paths: Iterable[Path]) -> str:
    names = [str(path).lower() for path in paths]
    if not names:
        return SOURCE_GENERATION_UNKNOWN
    legacy_flags = ["legacy" in name for name in names]
    if all(legacy_flags):
        return SOURCE_GENERATION_LEGACY
    if any(legacy_flags):
        return SOURCE_GENERATION_MIXED
    return SOURCE_GENERATION_MODERN


def _feature_tier_policy(source_generation: str) -> dict[str, str]:
    if source_generation in {SOURCE_GENERATION_LEGACY, SOURCE_GENERATION_MIXED, SOURCE_GENERATION_UNKNOWN}:
        return {
            "semantic_input_pack": "enabled",
            "trace_quality_pack": "observed_only",
        }
    return {
        "semantic_input_pack": "enabled",
        "trace_quality_pack": "enabled",
    }


def _resolve_dataset_feature_policy(frame: pd.DataFrame, *, source_generation: str) -> dict[str, Any]:
    tier_policy = _feature_tier_policy(source_generation)
    retained: list[str] = []
    dropped: dict[str, str] = {}
    observed_only_dropped: list[str] = []
    feature_tier_summary: dict[str, dict[str, Any]] = {}
    for column in FEATURE_VALUE_COLUMNS:
        if column not in frame.columns:
            continue
        tier = FEATURE_TIER_BY_COLUMN.get(column, "unknown")
        mode = tier_policy.get(tier, "enabled")
        bucket = feature_tier_summary.setdefault(
            tier,
            {
                "mode": mode,
                "candidate_count": 0,
                "retained_count": 0,
                "dropped_count": 0,
                "observed_only_dropped_count": 0,
            },
        )
        bucket["candidate_count"] += 1
        is_all_missing = bool(_missing_mask(frame[column]).all())
        if is_all_missing:
            if mode == "observed_only":
                dropped[column] = f"{source_generation}_{tier}_all_missing"
                observed_only_dropped.append(column)
                bucket["observed_only_dropped_count"] += 1
            else:
                dropped[column] = "all_missing_feature"
            bucket["dropped_count"] += 1
            continue
        retained.append(column)
        bucket["retained_count"] += 1
    for tier_name, mode in tier_policy.items():
        feature_tier_summary.setdefault(
            tier_name,
            {
                "mode": mode,
                "candidate_count": 0,
                "retained_count": 0,
                "dropped_count": 0,
                "observed_only_dropped_count": 0,
            },
        )
    return {
        "version": FEATURE_TIER_POLICY_VERSION,
        "source_generation": source_generation,
        "feature_tier_policy": tier_policy,
        "feature_tier_summary": feature_tier_summary,
        "retained_feature_columns": retained,
        "dropped_feature_columns": list(dropped.keys()),
        "dropped_feature_reasons": dropped,
        "observed_only_dropped_feature_columns": observed_only_dropped,
    }


def _feature_read_columns(paths: Iterable[Path]) -> list[str]:
    needed = set(KEY_COLUMNS) | set(METADATA_COLUMNS) | set(COMMON_FEATURE_COLUMNS)
    available: set[str] = set()
    for path in paths:
        try:
            available.update(pq.ParquetFile(path).schema_arrow.names)
        except Exception:
            continue
    return sorted(needed & available)


def _load_feature_frame(paths: list[Path]) -> pd.DataFrame:
    if not paths:
        return pd.DataFrame(columns=list(dict.fromkeys([*KEY_COLUMNS, *METADATA_COLUMNS, *COMMON_FEATURE_COLUMNS])))

    read_columns = _feature_read_columns(paths)
    frames: list[pd.DataFrame] = []
    expected = list(dict.fromkeys([*KEY_COLUMNS, *METADATA_COLUMNS, *COMMON_FEATURE_COLUMNS]))
    for path in paths:
        frame = pd.read_parquet(path, columns=read_columns or None)
        frame = frame.reindex(columns=expected)
        frame["__feature_source_path"] = str(path)
        frames.append(frame)
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=expected)
    merged["join_key"] = merged.apply(
        lambda row: str(row.get("replay_row_key", "") or row.get("decision_row_key", "") or "").strip(),
        axis=1,
    )
    merged = merged[merged["join_key"] != ""].copy()
    merged["join_ordinal"] = merged.groupby("join_key", dropna=False).cumcount()
    return merged


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = str(raw_line or "").strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, Mapping):
                yield dict(payload)


def _load_replay_label_frame(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in _iter_jsonl(path):
            summary = _coerce_mapping(row.get("label_quality_summary_v1"))
            transition = _coerce_mapping(summary.get("transition"))
            management = _coerce_mapping(summary.get("management"))
            decision_row = _coerce_mapping(row.get("decision_row"))
            outcome_target_features = _extract_outcome_target_features(row)
            replay_row_key = str(row.get("replay_row_key", "") or row.get("row_key", "") or summary.get("row_key", "") or "").strip()
            decision_row_key = str(
                row.get("decision_row_key", "")
                or decision_row.get("decision_row_key", "")
                or replay_row_key
                or ""
            ).strip()
            runtime_snapshot_key = str(
                row.get("runtime_snapshot_key", "")
                or decision_row.get("runtime_snapshot_key", "")
                or ""
            ).strip()
            trade_link_key = str(
                row.get("trade_link_key", "")
                or decision_row.get("trade_link_key", "")
                or ""
            ).strip()
            join_key = replay_row_key or decision_row_key
            if not join_key:
                continue
            rows.append(
                {
                    "join_key": join_key,
                    "decision_row_key": decision_row_key,
                    "runtime_snapshot_key": runtime_snapshot_key,
                    "trade_link_key": trade_link_key,
                    "replay_row_key": replay_row_key or decision_row_key,
                    "transition_label_status": str(row.get("transition_label_status", "") or summary.get("transition_label_status", "") or ""),
                    "management_label_status": str(row.get("management_label_status", "") or summary.get("management_label_status", "") or ""),
                    "label_unknown_count": int(row.get("label_unknown_count", summary.get("label_unknown_count", 0)) or 0),
                    "label_positive_count": int(row.get("label_positive_count", summary.get("label_positive_count", 0)) or 0),
                    "label_negative_count": int(row.get("label_negative_count", summary.get("label_negative_count", 0)) or 0),
                    "label_is_ambiguous": int(bool(row.get("label_is_ambiguous", summary.get("label_is_ambiguous")))),
                    "label_source_descriptor": str(row.get("label_source_descriptor", "") or summary.get("label_source_descriptor", "") or ""),
                    "is_censored": int(bool(row.get("is_censored", summary.get("is_censored")))),
                    "transition_positive_count": int(transition.get("positive_count", 0) or 0),
                    "transition_negative_count": int(transition.get("negative_count", 0) or 0),
                    "transition_unknown_count": int(transition.get("unknown_count", 0) or 0),
                    "management_positive_count": int(management.get("positive_count", 0) or 0),
                    "management_negative_count": int(management.get("negative_count", 0) or 0),
                    "management_unknown_count": int(management.get("unknown_count", 0) or 0),
                    "transition_direction": str(outcome_target_features.get("transition_direction", "") or ""),
                    "transition_same_side_positive_count": int(outcome_target_features.get("transition_same_side_positive_count", 0) or 0),
                    "transition_adverse_positive_count": int(outcome_target_features.get("transition_adverse_positive_count", 0) or 0),
                    "transition_quality_score": float(outcome_target_features.get("transition_quality_score", 0.0) or 0.0),
                    "management_exit_favor_positive_count": int(outcome_target_features.get("management_exit_favor_positive_count", 0) or 0),
                    "management_hold_favor_positive_count": int(outcome_target_features.get("management_hold_favor_positive_count", 0) or 0),
                    "semantic_target_source": int(outcome_target_features.get("semantic_target_source", 0) or 0),
                    "__replay_source_path": str(path),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["join_key", "join_ordinal", *KEY_COLUMNS, *LABEL_COLUMNS, "__replay_source_path"])
    frame = pd.DataFrame(rows)
    frame["join_ordinal"] = frame.groupby("join_key", dropna=False).cumcount()
    return frame


def _missing_mask(series: pd.Series) -> pd.Series:
    if series.dtype == "object":
        return series.isna() | series.astype(str).str.strip().eq("")
    return series.isna()


def _normalized_text_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index, dtype="string")
    return frame[column].fillna("").astype("string").str.strip()


def _duplicate_join_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if "join_key" not in frame.columns or frame.empty:
        return {
            "duplicate_group_count": 0,
            "duplicate_row_excess_count": 0,
            "sample_groups": {},
        }
    join_keys = _normalized_text_series(frame, "join_key")
    non_empty = join_keys[join_keys.ne("")]
    if non_empty.empty:
        return {
            "duplicate_group_count": 0,
            "duplicate_row_excess_count": 0,
            "sample_groups": {},
        }
    counts = non_empty.value_counts()
    duplicates = counts[counts > 1]
    return {
        "duplicate_group_count": int(len(duplicates)),
        "duplicate_row_excess_count": int((duplicates - 1).sum()) if not duplicates.empty else 0,
        "sample_groups": {str(key): int(value) for key, value in duplicates.head(5).items()},
    }


def _sample_sorted(values: set[str], *, limit: int = 5) -> list[str]:
    return sorted(str(value) for value in values if str(value).strip())[:limit]


def _build_join_health_report(
    *,
    feature_df: pd.DataFrame,
    label_df: pd.DataFrame,
    joined_df: pd.DataFrame,
    feature_source: Path,
    replay_source: Path,
) -> dict[str, Any]:
    feature_join_keys = set(_normalized_text_series(feature_df, "join_key").tolist()) - {""}
    label_join_keys = set(_normalized_text_series(label_df, "join_key").tolist()) - {""}
    joined_join_keys = set(_normalized_text_series(joined_df, "join_key").tolist()) - {""}

    key_mismatches: dict[str, int] = {}
    for key_name in KEY_COLUMNS:
        label_key = f"{key_name}_label"
        if label_key not in joined_df.columns:
            key_mismatches[key_name] = 0
            continue
        left = _normalized_text_series(joined_df, key_name)
        right = _normalized_text_series(joined_df, label_key)
        mismatch_mask = left.ne("") & right.ne("") & left.ne(right)
        key_mismatches[key_name] = int(mismatch_mask.sum())

    missing_joined_keys = {
        key_name: int(_normalized_text_series(joined_df, key_name).eq("").sum())
        for key_name in KEY_COLUMNS
    }

    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "report_version": DATASET_JOIN_HEALTH_VERSION,
        "builder_version": DATASET_BUILDER_VERSION,
        "feature_source": str(feature_source),
        "replay_source": str(replay_source),
        "feature_rows": int(len(feature_df)),
        "label_rows": int(len(label_df)),
        "joined_rows": int(len(joined_df)),
        "feature_unique_join_keys": int(len(feature_join_keys)),
        "label_unique_join_keys": int(len(label_join_keys)),
        "joined_unique_join_keys": int(len(joined_join_keys)),
        "feature_only_join_keys_count": int(len(feature_join_keys - label_join_keys)),
        "feature_only_join_keys_sample": _sample_sorted(feature_join_keys - label_join_keys),
        "label_only_join_keys_count": int(len(label_join_keys - feature_join_keys)),
        "label_only_join_keys_sample": _sample_sorted(label_join_keys - feature_join_keys),
        "duplicate_join_groups": {
            "feature": _duplicate_join_summary(feature_df),
            "label": _duplicate_join_summary(label_df),
            "joined": _duplicate_join_summary(joined_df),
        },
        "joined_missing_key_rows": missing_joined_keys,
        "joined_key_mismatch_rows": key_mismatches,
    }


def _finalize_missingness_bucket(rows: int, missing_rows: Mapping[str, int]) -> dict[str, Any]:
    payload: dict[str, Any] = {"rows": int(rows), "missing_rows": {str(k): int(v) for k, v in missing_rows.items()}}
    if rows > 0:
        payload["missing_ratio"] = {str(k): round(int(v) / rows, 6) for k, v in missing_rows.items()}
    else:
        payload["missing_ratio"] = {str(k): None for k in missing_rows}
    return payload


def _build_missingness_report(df: pd.DataFrame, *, dataset_key: str, output_path: Path) -> dict[str, Any]:
    selected_columns = list(df.columns)
    missing_masks = {column: _missing_mask(df[column]) for column in selected_columns}
    overall_missing_rows = {column: int(mask.sum()) for column, mask in missing_masks.items()}
    missing_columns = [
        str(column)
        for column in selected_columns
        if int(overall_missing_rows.get(column, 0)) >= int(len(df))
    ]

    def by_group(column_name: str) -> dict[str, Any]:
        if column_name not in df.columns:
            return {}
        output: dict[str, Any] = {}
        groups = df.groupby(df[column_name].fillna("__missing__"), dropna=False)
        for key, group in groups:
            output[str(key)] = _finalize_missingness_bucket(
                len(group),
                {column: int(missing_masks[column].loc[group.index].sum()) for column in selected_columns},
            )
        return output

    return {
        "created_at": datetime.now().astimezone().isoformat(),
        "report_version": DATASET_MISSINGNESS_VERSION,
        "builder_version": DATASET_BUILDER_VERSION,
        "schema_version": dataset_key,
        "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
        "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
        "output_path": str(output_path),
        "selected_columns": selected_columns,
        "selected_column_count": len(selected_columns),
        "missing_columns": missing_columns,
        "overall": _finalize_missingness_bucket(len(df), overall_missing_rows),
        "by_symbol": by_group("symbol"),
        "by_regime": by_group("preflight_regime"),
        "by_setup_id": by_group("setup_id"),
    }


def _resolve_binary_target(
    *,
    positive: Any,
    negative: Any,
    status: Any,
    is_ambiguous: Any,
    is_censored: Any,
) -> int | None:
    if str(status or "").strip().upper() != "VALID":
        return None
    if bool(is_ambiguous) or bool(is_censored):
        return None
    pos = int(positive or 0)
    neg = int(negative or 0)
    if pos > neg:
        return 1
    if neg > pos:
        return 0
    return None


def _timing_count_delta(row: Mapping[str, Any]) -> int:
    same_side = int(row.get("transition_same_side_positive_count", 0) or 0)
    adverse = int(row.get("transition_adverse_positive_count", 0) or 0)
    return same_side - adverse


def _timing_fallback_delta(row: Mapping[str, Any]) -> int:
    positive = int(row.get("transition_positive_count", 0) or 0)
    negative = int(row.get("transition_negative_count", 0) or 0)
    return positive - negative


def _timing_quality_score(row: Mapping[str, Any]) -> float:
    return float(row.get("transition_quality_score", 0.0) or 0.0)


def _resolve_timing_target_reason(row: Mapping[str, Any]) -> str:
    count_delta = _timing_count_delta(row)
    fallback_delta = _timing_fallback_delta(row)
    quality = _timing_quality_score(row)
    if count_delta > 0:
        if fallback_delta < 0 and quality < -TIMING_TIE_QUALITY_THRESHOLD:
            return "count_positive_conflict_veto"
        return "count_positive"
    if count_delta < 0:
        if fallback_delta > 0 and quality > TIMING_TIE_QUALITY_THRESHOLD:
            return "count_negative_conflict_veto"
        return "count_negative"

    if fallback_delta > 0 and quality > TIMING_TIE_QUALITY_THRESHOLD:
        return "tie_break_positive"
    if fallback_delta < 0 and quality < -TIMING_TIE_QUALITY_THRESHOLD:
        return "tie_break_negative"
    if fallback_delta != 0 and abs(quality) > TIMING_TIE_QUALITY_THRESHOLD:
        return "tie_break_conflict"
    return "ambiguous_tie"


def _resolve_timing_target(row: Mapping[str, Any]) -> int | None:
    reason = _resolve_timing_target_reason(row)
    if reason in {"count_positive", "tie_break_positive"}:
        return 1
    if reason in {"count_negative", "tie_break_negative"}:
        return 0
    return None


def _resolve_timing_margin(row: Mapping[str, Any]) -> float:
    count_delta = _timing_count_delta(row)
    quality = _timing_quality_score(row)
    if count_delta != 0:
        return round(float(count_delta) + quality, 6)
    return round(quality, 6)


def _entry_quality_support_delta(row: Mapping[str, Any]) -> int:
    same_side = int(row.get("transition_same_side_positive_count", 0) or 0)
    adverse = int(row.get("transition_adverse_positive_count", 0) or 0)
    return same_side - adverse


def _entry_quality_score(row: Mapping[str, Any]) -> float:
    return float(row.get("transition_quality_score", 0.0) or 0.0)


def _entry_quality_positive_threshold(row: Mapping[str, Any]) -> float:
    regime = str(row.get("preflight_regime", "") or "").strip().upper()
    if regime == "TREND":
        return ENTRY_QUALITY_TREND_POSITIVE_THRESHOLD
    return ENTRY_QUALITY_POSITIVE_THRESHOLD


def _entry_quality_hold_conflict(row: Mapping[str, Any]) -> bool:
    hold_favor = pd.to_numeric(row.get("management_hold_favor_positive_count"), errors="coerce")
    exit_favor = pd.to_numeric(row.get("management_exit_favor_positive_count"), errors="coerce")
    hold_favor = 0 if pd.isna(hold_favor) else int(hold_favor)
    exit_favor = 0 if pd.isna(exit_favor) else int(exit_favor)
    return hold_favor > exit_favor


def _entry_quality_fallback_heavy(row: Mapping[str, Any]) -> bool:
    compatibility_mode = str(row.get("compatibility_mode", "") or "").strip().lower()
    if compatibility_mode and compatibility_mode not in {"clean", "none"}:
        return True
    used_fallback_count = pd.to_numeric(row.get("used_fallback_count"), errors="coerce")
    missing_feature_count = pd.to_numeric(row.get("missing_feature_count"), errors="coerce")
    used_fallback_count = 0 if pd.isna(used_fallback_count) else int(used_fallback_count)
    missing_feature_count = 0 if pd.isna(missing_feature_count) else int(missing_feature_count)
    return (
        used_fallback_count >= ENTRY_QUALITY_FALLBACK_HEAVY_THRESHOLD
        or missing_feature_count >= ENTRY_QUALITY_MISSING_FEATURE_HEAVY_THRESHOLD
    )


def _resolve_entry_quality_target_reason(row: Mapping[str, Any]) -> str:
    support_delta = _entry_quality_support_delta(row)
    quality = _entry_quality_score(row)
    positive_threshold = _entry_quality_positive_threshold(row)
    hold_conflict = _entry_quality_hold_conflict(row)
    fallback_heavy = _entry_quality_fallback_heavy(row)

    if support_delta >= 1 and quality >= positive_threshold:
        if hold_conflict:
            return "support_positive_hold_conflict_veto"
        if fallback_heavy:
            return "support_positive_fallback_veto"
        return "support_positive"
    if support_delta < 0 and quality <= 0.0:
        if hold_conflict:
            return "support_negative_hold_conflict_veto"
        if fallback_heavy:
            return "support_negative_fallback_veto"
        return "support_negative"
    if support_delta <= 0 and quality <= ENTRY_QUALITY_NEGATIVE_THRESHOLD:
        if hold_conflict:
            return "quality_negative_hold_conflict_veto"
        if fallback_heavy:
            return "quality_negative_fallback_veto"
        return "quality_negative_only"
    if support_delta > 0 and quality > 0.0:
        return "support_positive_quality_short"
    if support_delta > 0:
        return "support_positive_quality_conflict"
    if support_delta < 0 and quality > 0.0:
        return "support_negative_quality_conflict"
    if quality >= positive_threshold:
        return "quality_positive_without_support"
    return "ambiguous"


def _resolve_entry_quality_target(row: Mapping[str, Any]) -> int | None:
    reason = _resolve_entry_quality_target_reason(row)
    if reason == "support_positive":
        return 1
    if reason in {"support_negative", "quality_negative_only"}:
        return 0
    return None


def _resolve_entry_quality_margin(row: Mapping[str, Any]) -> float:
    support_delta = _entry_quality_support_delta(row)
    quality = _entry_quality_score(row)
    if support_delta != 0:
        return round(float(support_delta) + quality, 6)
    return round(quality, 6)


def _resolve_semantic_target(
    row: Mapping[str, Any],
    *,
    dataset_key: str,
    positive: Any,
    negative: Any,
    status: Any,
    is_ambiguous: Any,
    is_censored: Any,
) -> int | None:
    status_value = str(status or "").strip().upper()
    if status_value != "VALID":
        return None
    if bool(is_ambiguous) or bool(is_censored):
        return None

    if int(row.get("semantic_target_source", 0) or 0) <= 0:
        return _resolve_binary_target(
            positive=positive,
            negative=negative,
            status=status,
            is_ambiguous=is_ambiguous,
            is_censored=is_censored,
        )

    if dataset_key == "timing":
        return _resolve_timing_target(row)
    elif dataset_key == "entry_quality":
        return _resolve_entry_quality_target(row)
    elif dataset_key == "exit_management":
        exit_favor = int(row.get("management_exit_favor_positive_count", 0) or 0)
        hold_favor = int(row.get("management_hold_favor_positive_count", 0) or 0)
        if exit_favor > 0 or hold_favor > 0:
            return 1 if exit_favor > hold_favor else 0

    return _resolve_binary_target(
        positive=positive,
        negative=negative,
        status=status,
        is_ambiguous=is_ambiguous,
        is_censored=is_censored,
    )


def _joined_base_frame(feature_df: pd.DataFrame, label_df: pd.DataFrame) -> pd.DataFrame:
    merged = feature_df.merge(
        label_df,
        on=["join_key", "join_ordinal"],
        how="inner",
        suffixes=("", "_label"),
    )
    for key in KEY_COLUMNS:
        label_key = f"{key}_label"
        if key not in merged.columns and label_key in merged.columns:
            merged[key] = merged[label_key]
        elif label_key in merged.columns:
            merged[key] = merged[key].where(merged[key].fillna("").astype(str).str.strip().ne(""), merged[label_key])
    return merged


def _build_dataset_frame(base_df: pd.DataFrame, *, dataset_key: str, source_generation: str) -> pd.DataFrame:
    config = TARGET_CONFIG[dataset_key]
    frame = base_df.copy()
    fallback_margin = pd.to_numeric(frame[config["positive_column"]], errors="coerce").fillna(0) - pd.to_numeric(
        frame[config["negative_column"]], errors="coerce"
    ).fillna(0)
    semantic_source_mask = pd.to_numeric(frame.get("semantic_target_source"), errors="coerce").fillna(0).astype(int) > 0
    if dataset_key == "timing":
        semantic_margin = frame.apply(_resolve_timing_margin, axis=1)
    elif dataset_key == "entry_quality":
        semantic_margin = frame.apply(_resolve_entry_quality_margin, axis=1)
    elif dataset_key == "exit_management":
        semantic_margin = pd.to_numeric(frame.get("management_exit_favor_positive_count"), errors="coerce").fillna(0) - pd.to_numeric(
            frame.get("management_hold_favor_positive_count"), errors="coerce"
        ).fillna(0)
    else:
        semantic_margin = fallback_margin
    frame[config["margin_column"]] = fallback_margin.where(~semantic_source_mask, semantic_margin)
    frame[config["target_column"]] = frame.apply(
        lambda row: _resolve_semantic_target(
            row,
            dataset_key=dataset_key,
            positive=row.get(config["positive_column"]),
            negative=row.get(config["negative_column"]),
            status=row.get(config["status_column"]),
            is_ambiguous=row.get("label_is_ambiguous"),
            is_censored=row.get("is_censored"),
        ),
        axis=1,
    )
    frame = frame[frame[config["target_column"]].notna()].copy()
    frame[config["target_column"]] = frame[config["target_column"]].astype(int)
    frame, split_summary = attach_split_columns(
        frame,
        time_col="time",
        signal_bar_ts_col="signal_bar_ts",
        symbol_col="symbol",
        regime_col="preflight_regime",
        time_split=DEFAULT_TIME_SPLIT,
        symbol_holdout_fraction=DEFAULT_SYMBOL_HOLDOUT_FRACTION,
        regime_holdout_fraction=DEFAULT_REGIME_HOLDOUT_FRACTION,
        target_col=config["target_column"],
    )
    frame["dataset_key"] = dataset_key
    frame["target_contract"] = config["target_column"]
    feature_policy = _resolve_dataset_feature_policy(frame, source_generation=source_generation)
    selected_columns = list(
        dict.fromkeys(
            [
                *KEY_COLUMNS,
                *METADATA_COLUMNS,
                *feature_policy["retained_feature_columns"],
                *LABEL_COLUMNS,
                *SPLIT_COLUMNS,
                config["target_column"],
                config["margin_column"],
                "dataset_key",
                "target_contract",
            ]
        )
    )
    for column in selected_columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[selected_columns], split_summary, feature_policy


def _write_dataset_artifact(
    df: pd.DataFrame,
    *,
    dataset_key: str,
    output_dir: Path,
    split_summary: SplitSummary,
    source_generation: str,
    feature_policy: Mapping[str, Any],
) -> DatasetArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = TARGET_CONFIG[dataset_key]
    output_path = output_dir / config["file_name"]
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    missingness_path = output_path.with_suffix(output_path.suffix + ".missingness.json")

    df.to_parquet(output_path, index=False)
    missingness = _build_missingness_report(df, dataset_key=dataset_key, output_path=output_path)
    missingness_path.write_text(json.dumps(missingness, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "created_at": datetime.now().astimezone().isoformat(),
        "summary_version": DATASET_SUMMARY_VERSION,
        "builder_version": DATASET_BUILDER_VERSION,
        "feature_tier_policy_version": FEATURE_TIER_POLICY_VERSION,
        "dataset_key": dataset_key,
        "source_generation": source_generation,
        "output_path": str(output_path),
        "row_count": int(len(df)),
        "selected_columns": list(df.columns),
        "selected_column_count": len(df.columns),
        "missing_columns": list(missingness.get("missing_columns", [])),
        "feature_column_count": len(feature_policy["retained_feature_columns"]),
        "feature_columns": list(feature_policy["retained_feature_columns"]),
        "feature_tier_policy": dict(feature_policy["feature_tier_policy"]),
        "feature_tier_summary": dict(feature_policy["feature_tier_summary"]),
        "dropped_feature_columns": list(feature_policy["dropped_feature_columns"]),
        "dropped_feature_reasons": dict(feature_policy["dropped_feature_reasons"]),
        "observed_only_dropped_feature_columns": list(feature_policy["observed_only_dropped_feature_columns"]),
        "key_columns": list(KEY_COLUMNS),
        "time_split_counts": split_summary.time_split_counts,
        "time_split_strategy": split_summary.time_split_strategy,
        "symbol_holdout_counts": split_summary.symbol_holdout_counts,
        "regime_holdout_counts": split_summary.regime_holdout_counts,
        "missingness_report_path": str(missingness_path),
        "dataset_split_contract": DATASET_SPLIT_CONTRACT_VERSION,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return DatasetArtifact(
        dataset_key=dataset_key,
        output_path=output_path,
        summary_path=summary_path,
        missingness_path=missingness_path,
        row_count=int(len(df)),
        selected_columns=tuple(df.columns),
        missing_columns=tuple(missingness.get("missing_columns", []) or []),
        split_summary=split_summary,
        source_generation=source_generation,
        feature_tier_policy=dict(feature_policy["feature_tier_policy"]),
        feature_tier_summary=dict(feature_policy["feature_tier_summary"]),
        retained_feature_columns=tuple(feature_policy["retained_feature_columns"]),
        dropped_feature_columns=tuple(feature_policy["dropped_feature_columns"]),
        dropped_feature_reasons=dict(feature_policy["dropped_feature_reasons"]),
        observed_only_dropped_feature_columns=tuple(feature_policy["observed_only_dropped_feature_columns"]),
    )


def build_semantic_v1_datasets(
    *,
    feature_source: str | Path | None = None,
    replay_source: str | Path | None = None,
    output_dir: str | Path | None = None,
    manifest_root: str | Path | None = None,
) -> dict[str, Any]:
    feature_path = _resolve_path(feature_source, DEFAULT_FEATURE_DIR)
    replay_path = _resolve_path(replay_source, DEFAULT_REPLAY_DIR)
    output_path = _resolve_path(output_dir, DEFAULT_OUTPUT_DIR)
    manifest_path_root = _resolve_path(manifest_root, DEFAULT_MANIFEST_ROOT)

    feature_files = _resolve_feature_files(feature_path)
    replay_files = _resolve_replay_files(replay_path)
    if not feature_files:
        raise FileNotFoundError(f"No semantic compact parquet files found under {feature_path}")
    if not replay_files:
        raise FileNotFoundError(f"No replay intermediate jsonl files found under {replay_path}")

    source_generation = _detect_source_generation([*feature_files, *replay_files])
    feature_df = _load_feature_frame(feature_files)
    label_df = _load_replay_label_frame(replay_files)
    base_df = _joined_base_frame(feature_df, label_df)
    if base_df.empty:
        raise ValueError(
            "semantic_v1 dataset build produced zero joined rows; "
            "check compact export coverage and replay row key overlap"
        )
    join_health_report = _build_join_health_report(
        feature_df=feature_df,
        label_df=label_df,
        joined_df=base_df,
        feature_source=feature_path,
        replay_source=replay_path,
    )

    artifacts: list[DatasetArtifact] = []
    for dataset_key in TARGET_CONFIG:
        dataset_df, split_summary, feature_policy = _build_dataset_frame(
            base_df,
            dataset_key=dataset_key,
            source_generation=source_generation,
        )
        artifacts.append(
            _write_dataset_artifact(
                dataset_df,
                dataset_key=dataset_key,
                output_dir=output_path,
                split_summary=split_summary,
                source_generation=source_generation,
                feature_policy=feature_policy,
            )
        )

    now = datetime.now().astimezone()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    manifest_dirs = _ensure_manifest_dirs(manifest_path_root)
    join_health_path = _write_manifest(manifest_dirs["export"], "semantic_v1_dataset_join_health", join_health_report, timestamp)
    manifest = {
        "created_at": now.isoformat(),
        "manifest_version": DATASET_MANIFEST_VERSION,
        "builder_version": DATASET_BUILDER_VERSION,
        "feature_tier_policy_version": FEATURE_TIER_POLICY_VERSION,
        "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
        "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
        "dataset_split_contract": DATASET_SPLIT_CONTRACT_VERSION,
        "source_generation": source_generation,
        "feature_tier_policy": _feature_tier_policy(source_generation),
        "feature_source": str(feature_path),
        "replay_source": str(replay_path),
        "feature_files": [str(path) for path in feature_files],
        "replay_files": [str(path) for path in replay_files],
        "joined_rows": int(len(base_df)),
        "join_health_report_path": str(join_health_path),
        "datasets": {
            artifact.dataset_key: {
                "output_path": str(artifact.output_path),
                "summary_path": str(artifact.summary_path),
                "missingness_path": str(artifact.missingness_path),
                "row_count": artifact.row_count,
                "selected_columns": list(artifact.selected_columns),
                "missing_columns": list(artifact.missing_columns),
                "time_split_counts": artifact.split_summary.time_split_counts,
                "time_split_strategy": artifact.split_summary.time_split_strategy,
                "symbol_holdout_counts": artifact.split_summary.symbol_holdout_counts,
                "regime_holdout_counts": artifact.split_summary.regime_holdout_counts,
                "source_generation": artifact.source_generation,
                "feature_tier_policy": dict(artifact.feature_tier_policy),
                "feature_tier_summary": dict(artifact.feature_tier_summary),
                "feature_columns": list(artifact.retained_feature_columns),
                "dropped_feature_columns": list(artifact.dropped_feature_columns),
                "dropped_feature_reasons": dict(artifact.dropped_feature_reasons),
                "observed_only_dropped_feature_columns": list(artifact.observed_only_dropped_feature_columns),
            }
            for artifact in artifacts
        },
    }
    manifest_file = _write_manifest(manifest_dirs["export"], "semantic_v1_dataset_build", manifest, timestamp)
    return {
        "manifest_path": str(manifest_file),
        "feature_source": str(feature_path),
        "replay_source": str(replay_path),
        "joined_rows": int(len(base_df)),
        "join_health_report_path": str(join_health_path),
        "datasets": {
            artifact.dataset_key: {
                "output_path": str(artifact.output_path),
                "summary_path": str(artifact.summary_path),
                "missingness_path": str(artifact.missingness_path),
                "row_count": artifact.row_count,
            }
            for artifact in artifacts
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build semantic ML v1 compact datasets from export parquet and replay labels.")
    parser.add_argument("--feature-source", default=str(DEFAULT_FEATURE_DIR), help="Replay or forecast compact parquet path.")
    parser.add_argument("--replay-source", default=str(DEFAULT_REPLAY_DIR), help="Replay intermediate jsonl path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for semantic_v1 datasets.")
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT), help="Manifest root directory.")
    args = parser.parse_args()

    summary = build_semantic_v1_datasets(
        feature_source=args.feature_source,
        replay_source=args.replay_source,
        output_dir=args.output_dir,
        manifest_root=args.manifest_root,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
