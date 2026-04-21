"""Materialize proxy semantic_v1 datasets from training bridge corpus + archive features."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.semantic_shadow_training_bridge_adapter import (
    load_semantic_shadow_training_bridge_adapter_frame,
)
from backend.services.trade_csv_schema import now_kst_dt
from ml.semantic_v1.dataset_splits import attach_split_columns
from ml.semantic_v1.feature_packs import SEMANTIC_INPUT_COLUMNS, TRACE_QUALITY_COLUMNS
from ml.semantic_v1.runtime_adapter import build_semantic_shadow_feature_row


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_PATH = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.json"
DEFAULT_ADAPTER_PATH = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_bridge_adapter_latest.csv"
DEFAULT_REBALANCED_CORPUS_PATH = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "shadow_rebalanced_training_corpus_latest.csv"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy"

SEMANTIC_SHADOW_PROXY_DATASET_VERSION = "semantic_shadow_proxy_dataset_materializer_v0"
SEMANTIC_SHADOW_PROXY_TARGET_VERSION = "semantic_shadow_proxy_targets_v2"
REQUIRED_ARCHIVE_COLUMNS = [
    "time",
    "signal_timeframe",
    "signal_bar_ts",
    "symbol",
    "action",
    "outcome",
    "blocked_by",
    "decision_row_key",
    "runtime_snapshot_key",
    "trade_link_key",
    "replay_row_key",
    "entry_stage",
    "setup_id",
    "setup_side",
    "preflight_regime",
    "preflight_liquidity",
    "position_snapshot_v2",
    "response_vector_v2",
    "state_vector_v2",
    "evidence_vector_v1",
    "belief_state_v1",
    "barrier_state_v1",
    "forecast_features_v1",
]


def _to_text(value: Any, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_float(value: Any, default: float = 0.0) -> float:
    text = _to_text(value)
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _as_mapping(value: Any) -> dict[str, Any]:
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
        return dict(parsed) if isinstance(parsed, Mapping) else {}
    return {}


def _load_rebalanced_lookup(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception:
            return {}
    lookup: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        bridge_adapter_row_id = _to_text(row.get("bridge_adapter_row_id"))
        if bridge_adapter_row_id:
            lookup[bridge_adapter_row_id] = row
    return lookup


def _load_corpus_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_key = _to_text(row.get("row_key"))
        if row_key:
            by_key[row_key] = dict(row)
    return by_key


def _load_archive_rows(adapter_df: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    if adapter_df.empty:
        return lookup
    for source_file, group in adapter_df.groupby("archive_source_file", dropna=False):
        source_text = _to_text(source_file)
        if not source_text:
            continue
        parquet_path = Path(source_text)
        if not parquet_path.is_absolute():
            parquet_path = PROJECT_ROOT / parquet_path
        if not parquet_path.exists():
            continue
        wanted_keys = {
            _to_text(value)
            for value in group["archive_replay_row_key"].tolist()
            if _to_text(value)
        }
        if not wanted_keys:
            continue
        try:
            frame = pd.read_parquet(parquet_path, columns=REQUIRED_ARCHIVE_COLUMNS)
        except Exception:
            continue
        frame = frame.loc[
            frame["replay_row_key"].fillna("").astype(str).isin(wanted_keys)
        ].copy()
        for row in frame.to_dict(orient="records"):
            replay_key = _to_text(row.get("replay_row_key"))
            if replay_key:
                lookup[(source_text, replay_key)] = row
    return lookup


def _timing_target(bridge_row: Mapping[str, Any]) -> tuple[int, float]:
    wait_label = _to_text(bridge_row.get("entry_wait_quality_label")).lower()
    score = _to_float(_as_mapping(bridge_row.get("economic_target_summary")).get("learning_total_score"), 0.0)
    if wait_label in {"avoided_loss_by_wait", "neutral_wait", "missed_move_by_wait", "bad_wait_missed_move"}:
        return (0, max(abs(score), 0.05))
    return (1 if score >= 0.0 else 0, max(abs(score), 0.05))


def _entry_quality_target(bridge_row: Mapping[str, Any]) -> tuple[int, float]:
    signed_exit_score = _to_float(_as_mapping(bridge_row.get("economic_target_summary")).get("signed_exit_score"), 0.0)
    return (1 if signed_exit_score > 0.0 else 0, max(abs(signed_exit_score), 1.0))


def _exit_management_target(bridge_row: Mapping[str, Any]) -> tuple[int, float]:
    signed_exit_score = _to_float(_as_mapping(bridge_row.get("economic_target_summary")).get("signed_exit_score"), 0.0)
    return (1 if signed_exit_score < 0.0 else 0, max(abs(signed_exit_score), 1.0))


def _feature_row(adapter_row: Mapping[str, Any], bridge_row: Mapping[str, Any], archive_row: Mapping[str, Any]) -> dict[str, Any]:
    feature_row = build_semantic_shadow_feature_row(
        runtime_snapshot_row=dict(archive_row),
        position_snapshot_v2=_as_mapping(archive_row.get("position_snapshot_v2")),
        response_vector_v2=_as_mapping(archive_row.get("response_vector_v2")),
        state_vector_v2=_as_mapping(archive_row.get("state_vector_v2")),
        evidence_vector_v1=_as_mapping(archive_row.get("evidence_vector_v1")),
        forecast_features_v1=_as_mapping(archive_row.get("forecast_features_v1")),
        signal_timeframe=_to_text(archive_row.get("signal_timeframe")),
        setup_id=_to_text(archive_row.get("setup_id")),
        setup_side=_to_text(archive_row.get("setup_side")),
        entry_stage=_to_text(archive_row.get("entry_stage")),
        preflight_regime=_to_text(archive_row.get("preflight_regime")),
        preflight_liquidity=_to_text(archive_row.get("preflight_liquidity")),
    )
    timing_target, timing_margin = _timing_target(bridge_row)
    entry_quality_target, entry_quality_margin = _entry_quality_target(bridge_row)
    exit_management_target, exit_management_margin = _exit_management_target(bridge_row)
    economic = _as_mapping(bridge_row.get("economic_target_summary"))
    realized_profit = _to_float(economic.get("profit"), 0.0)
    signed_exit_score = _to_float(economic.get("signed_exit_score"), 0.0)
    realized_value = realized_profit if abs(realized_profit) > 1e-9 else signed_exit_score
    return {
        "bridge_adapter_row_id": _to_text(adapter_row.get("bridge_adapter_row_id")),
        "bridge_row_key": _to_text(bridge_row.get("row_key")),
        "bridge_decision_time": _to_text(adapter_row.get("bridge_decision_time") or archive_row.get("time")),
        "time": _to_text(archive_row.get("time")),
        "signal_bar_ts": _to_float(archive_row.get("signal_bar_ts"), 0.0),
        "bridge_quality_status": _to_text(bridge_row.get("bridge_quality_status")),
        "corpus_source_id": _to_text(bridge_row.get("corpus_source_id")),
        "baseline_action": _to_text(archive_row.get("action")).upper(),
        "baseline_outcome": _to_text(archive_row.get("outcome")).lower(),
        "baseline_blocked_by": _to_text(archive_row.get("blocked_by")),
        "entry_wait_quality_label": _to_text(bridge_row.get("entry_wait_quality_label")).lower(),
        "learning_total_label": _to_text(economic.get("learning_total_label")).lower(),
        "learning_total_score": _to_float(economic.get("learning_total_score"), 0.0),
        "loss_quality_label": _to_text(economic.get("loss_quality_label")).lower(),
        "signed_exit_score": signed_exit_score,
        "realized_profit": realized_profit,
        "baseline_realized_value": realized_value,
        "baseline_realized_value_mode": "profit" if abs(realized_profit) > 1e-9 else "signed_exit_score",
        "scene_family": _to_text(_as_mapping(bridge_row.get("state25_runtime_hint_v1")).get("scene_family")).lower(),
        "wait_bias_hint": _to_text(_as_mapping(bridge_row.get("state25_runtime_hint_v1")).get("wait_bias_hint")).lower(),
        "forecast_decision_hint": _to_text(_as_mapping(bridge_row.get("forecast_runtime_summary_v1")).get("decision_hint")).upper(),
        "target_timing_now_vs_wait": timing_target,
        "target_timing_margin": timing_margin,
        "target_entry_quality": entry_quality_target,
        "target_entry_quality_margin": entry_quality_margin,
        "target_exit_management": exit_management_target,
        "target_exit_management_margin": exit_management_margin,
        "proxy_target_source": SEMANTIC_SHADOW_PROXY_TARGET_VERSION,
        **feature_row,
    }


def _apply_rebalanced_action_target(
    feature_row: dict[str, Any],
    *,
    action_target: str,
    action_variant: str,
    sample_weight: float,
) -> dict[str, Any]:
    target = _to_text(action_target).lower()
    variant = _to_text(action_variant).lower()
    weight = max(1.0, _to_float(sample_weight, 1.0))
    feature_row["sample_weight"] = weight
    feature_row["coarse_action_target_class"] = target
    feature_row["coarse_action_target_variant"] = variant or target
    if variant in {"enter_now", "enter_now_weak"} or target == "enter_now":
        feature_row["target_timing_now_vs_wait"] = 1
        feature_row["target_entry_quality"] = 0 if variant == "enter_now_weak" else 1
        feature_row["target_exit_management"] = 0
        feature_row["target_timing_margin"] = max(_to_float(feature_row.get("target_timing_margin"), 0.0), weight)
        feature_row["target_entry_quality_margin"] = max(
            _to_float(feature_row.get("target_entry_quality_margin"), 0.0),
            weight if feature_row["target_entry_quality"] == 1 else max(1.0, weight * 0.5),
        )
    elif variant == "wait_better_entry":
        feature_row["target_timing_now_vs_wait"] = 0
        feature_row["target_entry_quality"] = 1
        feature_row["target_exit_management"] = 0
        feature_row["target_timing_margin"] = max(_to_float(feature_row.get("target_timing_margin"), 0.0), max(1.0, weight * 0.75))
        feature_row["target_entry_quality_margin"] = max(_to_float(feature_row.get("target_entry_quality_margin"), 0.0), weight)
    elif target == "exit_protect":
        feature_row["target_timing_now_vs_wait"] = 0
        feature_row["target_entry_quality"] = 0
        feature_row["target_exit_management"] = 1
        feature_row["target_exit_management_margin"] = max(_to_float(feature_row.get("target_exit_management_margin"), 0.0), weight)
    else:
        feature_row["target_timing_now_vs_wait"] = 0
        feature_row["target_entry_quality"] = 0
        feature_row["target_exit_management"] = 0
        feature_row["target_timing_margin"] = max(_to_float(feature_row.get("target_timing_margin"), 0.0), weight)
    return feature_row


def _preferred_rebalanced_action_target(override: Mapping[str, Any]) -> str:
    for key in (
        "effective_target_action_class",
        "manual_target_action_class",
        "mapped_target_action_class",
    ):
        target = _to_text(override.get(key)).lower()
        if target:
            return target
    return ""


def _preferred_rebalanced_action_variant(override: Mapping[str, Any]) -> str:
    for key in (
        "effective_target_action_variant",
        "manual_target_action_variant",
        "mapped_target_action_variant",
    ):
        target = _to_text(override.get(key)).lower()
        if target:
            return target
    return ""


def build_semantic_shadow_proxy_datasets(
    *,
    corpus_path: str | Path | None = None,
    adapter_path: str | Path | None = None,
    rebalanced_corpus_path: str | Path | None = None,
    use_rebalanced_targets: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any], pd.DataFrame]:
    resolved_corpus_path = Path(corpus_path) if corpus_path is not None else DEFAULT_CORPUS_PATH
    resolved_adapter_path = Path(adapter_path) if adapter_path is not None else DEFAULT_ADAPTER_PATH
    resolved_rebalanced_path = Path(rebalanced_corpus_path) if rebalanced_corpus_path is not None else DEFAULT_REBALANCED_CORPUS_PATH

    corpus_rows = _load_corpus_rows(resolved_corpus_path)
    adapter_df = load_semantic_shadow_training_bridge_adapter_frame(resolved_adapter_path)
    adapter_df = adapter_df.loc[
        adapter_df["match_status"].fillna("").astype(str).eq("matched")
    ].copy() if not adapter_df.empty else pd.DataFrame()
    archive_lookup = _load_archive_rows(adapter_df)
    rebalanced_lookup = _load_rebalanced_lookup(resolved_rebalanced_path) if use_rebalanced_targets else {}

    feature_rows: list[dict[str, Any]] = []
    for adapter_row in adapter_df.to_dict(orient="records"):
        bridge_row_key = _to_text(adapter_row.get("bridge_row_key"))
        bridge_row = corpus_rows.get(bridge_row_key)
        if not bridge_row:
            continue
        archive_row = archive_lookup.get(
            (
                _to_text(adapter_row.get("archive_source_file")),
                _to_text(adapter_row.get("archive_replay_row_key")),
            )
        )
        if not archive_row:
            continue
        feature_row = _feature_row(adapter_row, bridge_row, archive_row)
        feature_row["sample_weight"] = 1.0
        feature_row["rebalance_bucket"] = ""
        feature_row["coarse_action_target_class"] = ""
        override = rebalanced_lookup.get(_to_text(adapter_row.get("bridge_adapter_row_id")))
        if override:
            if use_rebalanced_targets and _to_text(override.get("exclude_from_preview_train")).lower() in {"true", "1", "yes"}:
                continue
            feature_row["rebalance_bucket"] = _to_text(override.get("rebalance_bucket"))
            feature_row["sample_weight"] = _to_float(override.get("sample_weight"), 1.0)
            feature_row["coarse_action_target_class"] = _preferred_rebalanced_action_target(override)
            feature_row["coarse_action_target_variant"] = _preferred_rebalanced_action_variant(override)
            if use_rebalanced_targets and feature_row["coarse_action_target_class"]:
                feature_row = _apply_rebalanced_action_target(
                    feature_row,
                    action_target=feature_row["coarse_action_target_class"],
                    action_variant=feature_row.get("coarse_action_target_variant", ""),
                    sample_weight=feature_row["sample_weight"],
                )
                feature_row["proxy_target_source"] = f"{SEMANTIC_SHADOW_PROXY_TARGET_VERSION}::rebalanced"
        feature_rows.append(feature_row)

    base_frame = pd.DataFrame(feature_rows)
    datasets: dict[str, pd.DataFrame] = {}
    class_balance: dict[str, Any] = {}
    for dataset_key, target_col in (
        ("timing", "target_timing_now_vs_wait"),
        ("entry_quality", "target_entry_quality"),
        ("exit_management", "target_exit_management"),
    ):
        if base_frame.empty:
            datasets[dataset_key] = pd.DataFrame()
            class_balance[dataset_key] = {}
            continue
        split_frame, split_summary = attach_split_columns(base_frame, target_col=target_col)
        split_frame.attrs["split_summary"] = {
            "time_split_counts": split_summary.time_split_counts,
            "symbol_holdout_counts": split_summary.symbol_holdout_counts,
            "regime_holdout_counts": split_summary.regime_holdout_counts,
            "time_split_strategy": split_summary.time_split_strategy,
        }
        datasets[dataset_key] = split_frame
        class_balance[dataset_key] = split_frame[target_col].value_counts(dropna=False).to_dict()

    summary = {
        "semantic_shadow_proxy_dataset_version": SEMANTIC_SHADOW_PROXY_DATASET_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "corpus_path": str(resolved_corpus_path),
        "adapter_path": str(resolved_adapter_path),
        "rebalanced_corpus_path": str(resolved_rebalanced_path),
        "use_rebalanced_targets": bool(use_rebalanced_targets),
        "matched_feature_row_count": int(len(base_frame)),
        "dataset_row_counts": {key: int(len(value)) for key, value in datasets.items()},
        "dataset_class_balance": class_balance,
    }
    return datasets, summary, base_frame


def render_semantic_shadow_proxy_dataset_markdown(summary: Mapping[str, Any], datasets: Mapping[str, pd.DataFrame]) -> str:
    lines = [
        "# Semantic Shadow Proxy Datasets",
        "",
        f"- version: `{summary.get('semantic_shadow_proxy_dataset_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- matched_feature_row_count: `{summary.get('matched_feature_row_count', 0)}`",
        f"- dataset_row_counts: `{summary.get('dataset_row_counts', {})}`",
        "",
        "## Datasets",
        "",
    ]
    for key, frame in datasets.items():
        split_summary = getattr(frame, "attrs", {}).get("split_summary", {})
        lines.extend(
            [
                f"### {key}",
                "",
                f"- row_count: `{len(frame)}`",
                f"- class_balance: `{summary.get('dataset_class_balance', {}).get(key, {})}`",
                f"- split_summary: `{split_summary}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
