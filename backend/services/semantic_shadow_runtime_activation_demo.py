"""Offline activation demo for preview semantic shadow runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from backend.services.shadow_auto_edge_metrics import (
    resolve_shadow_value_proxy,
    resolve_wait_better_entry_premium,
)
from ml.semantic_v1.runtime_adapter import (
    SemanticShadowRuntime,
    resolve_semantic_shadow_compare_label,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURE_ROWS_PATH = PROJECT_ROOT / "data" / "datasets" / "semantic_v1_bridge_proxy" / "bridge_proxy_feature_rows.parquet"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "semantic_v1_preview_bridge_proxy"

SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_VERSION = "semantic_shadow_runtime_activation_demo_v0"
SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_COLUMNS = [
    "demo_row_id",
    "bridge_decision_time",
    "symbol",
    "baseline_action",
    "baseline_outcome",
    "baseline_realized_value",
    "target_timing_now_vs_wait",
    "target_entry_quality",
    "target_exit_management",
    "semantic_shadow_available",
    "shadow_should_enter",
    "shadow_action_variant",
    "shadow_timing_probability",
    "shadow_entry_quality_probability",
    "shadow_exit_management_probability",
    "shadow_recommendation",
    "shadow_compare_label",
    "shadow_reason",
    "shadow_realized_value",
    "alignment_label",
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


def build_semantic_shadow_runtime_activation_demo(
    *,
    feature_rows_path: str | Path | None = None,
    model_dir: str | Path | None = None,
    max_rows: int = 64,
    bucket: str = "test",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    resolved_feature_rows = Path(feature_rows_path) if feature_rows_path is not None else DEFAULT_FEATURE_ROWS_PATH
    resolved_model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
    if not resolved_feature_rows.exists():
        empty = pd.DataFrame(columns=SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_COLUMNS)
        return empty, {
            "semantic_shadow_runtime_activation_demo_version": SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "model_dir": str(resolved_model_dir),
            "feature_rows_path": str(resolved_feature_rows),
            "demo_row_count": 0,
            "available_row_count": 0,
            "shadow_enter_count": 0,
            "bucket": bucket,
        }

    frame = pd.read_parquet(resolved_feature_rows)
    subset = frame.copy()
    if bucket and "time_split_bucket" in subset.columns:
        preferred = subset.loc[subset["time_split_bucket"].fillna("").astype(str) == bucket].copy()
        if not preferred.empty:
            subset = preferred
    if "event_ts" in subset.columns:
        subset = subset.sort_values("event_ts", kind="mergesort")
    subset = subset.tail(int(max_rows)).copy()

    runtime = SemanticShadowRuntime(model_dir=resolved_model_dir)
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(subset.to_dict(orient="records"), start=1):
        prediction = runtime.predict_shadow(row, action_hint=_to_text(row.get("baseline_action")))
        timing = prediction.get("timing", {}) if isinstance(prediction, Mapping) else {}
        entry_quality = prediction.get("entry_quality", {}) if isinstance(prediction, Mapping) else {}
        exit_mgmt = prediction.get("exit_management", {}) if isinstance(prediction, Mapping) else {}
        shadow_should_enter = bool(prediction.get("should_enter", False)) if isinstance(prediction, Mapping) else False
        baseline_value = _to_float(row.get("baseline_realized_value"), 0.0)
        compare_label = resolve_semantic_shadow_compare_label(
            prediction,
            baseline_outcome=_to_text(row.get("baseline_outcome")),
            baseline_action=_to_text(row.get("baseline_action")),
            blocked_by=_to_text(row.get("baseline_blocked_by")),
        )
        shadow_action_variant = _to_text(prediction.get("recommendation"), "wait_more")
        target_timing = int(_to_float(row.get("target_timing_now_vs_wait"), 0.0))
        alignment_label = "aligned" if ((target_timing == 1) == shadow_should_enter) else "misaligned"
        rows.append(
            {
                "demo_row_id": f"shadow_demo::{idx:04d}",
                "bridge_decision_time": _to_text(row.get("bridge_decision_time")),
                "symbol": _to_text(row.get("symbol")).upper(),
                "baseline_action": _to_text(row.get("baseline_action")).upper(),
                "baseline_outcome": _to_text(row.get("baseline_outcome")).lower(),
                "baseline_realized_value": baseline_value,
                "target_timing_now_vs_wait": target_timing,
                "target_entry_quality": int(_to_float(row.get("target_entry_quality"), 0.0)),
                "target_exit_management": int(_to_float(row.get("target_exit_management"), 0.0)),
                "semantic_shadow_available": bool(prediction.get("available", False)) if isinstance(prediction, Mapping) else False,
                "shadow_should_enter": shadow_should_enter,
                "shadow_action_variant": shadow_action_variant,
                "shadow_timing_probability": timing.get("probability"),
                "shadow_entry_quality_probability": entry_quality.get("probability"),
                "shadow_exit_management_probability": exit_mgmt.get("probability"),
                "shadow_recommendation": _to_text(prediction.get("recommendation")) if isinstance(prediction, Mapping) else "",
                "shadow_compare_label": compare_label,
                "shadow_reason": _to_text(prediction.get("reason")) if isinstance(prediction, Mapping) else "",
                "shadow_realized_value": resolve_shadow_value_proxy(
                    baseline_realized_value=baseline_value,
                    shadow_action_variant=shadow_action_variant,
                    effective_target_action_variant=_to_text(
                        row.get("coarse_action_target_variant"),
                        "wait_more",
                    ),
                    wait_better_entry_premium=resolve_wait_better_entry_premium(
                        {
                            **dict(row),
                            "effective_target_action_variant": _to_text(
                                row.get("coarse_action_target_variant"),
                                "wait_more",
                            ),
                            "mapped_target_action_variant": _to_text(
                                row.get("coarse_action_target_variant"),
                                "wait_more",
                            ),
                            "proxy_target_action_variant": _to_text(
                                row.get("coarse_action_target_variant"),
                                "wait_more",
                            ),
                        }
                    ),
                ),
                "alignment_label": alignment_label,
            }
        )

    demo = pd.DataFrame(rows, columns=SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_COLUMNS)
    summary = {
        "semantic_shadow_runtime_activation_demo_version": SEMANTIC_SHADOW_RUNTIME_ACTIVATION_DEMO_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "model_dir": str(resolved_model_dir),
        "feature_rows_path": str(resolved_feature_rows),
        "bucket": bucket,
        "demo_row_count": int(len(demo)),
        "available_row_count": int(demo["semantic_shadow_available"].fillna(False).astype(bool).sum()) if not demo.empty else 0,
        "shadow_enter_count": int(demo["shadow_should_enter"].fillna(False).astype(bool).sum()) if not demo.empty else 0,
        "alignment_label_counts": demo["alignment_label"].value_counts().to_dict() if not demo.empty else {},
    }
    return demo, summary


def render_semantic_shadow_runtime_activation_demo_markdown(summary: Mapping[str, Any], demo: pd.DataFrame) -> str:
    lines = [
        "# Semantic Shadow Runtime Activation Demo",
        "",
        f"- version: `{summary.get('semantic_shadow_runtime_activation_demo_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- model_dir: `{summary.get('model_dir', '')}`",
        f"- bucket: `{summary.get('bucket', '')}`",
        f"- demo_row_count: `{summary.get('demo_row_count', 0)}`",
        f"- available_row_count: `{summary.get('available_row_count', 0)}`",
        f"- shadow_enter_count: `{summary.get('shadow_enter_count', 0)}`",
        f"- alignment_label_counts: `{summary.get('alignment_label_counts', {})}`",
        "",
        "## Sample Rows",
        "",
    ]
    for row in demo.head(10).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('demo_row_id', '')}",
                "",
                f"- bridge_decision_time: `{row.get('bridge_decision_time', '')}`",
                f"- symbol: `{row.get('symbol', '')}`",
                f"- semantic_shadow_available: `{row.get('semantic_shadow_available', False)}`",
                f"- shadow_should_enter: `{row.get('shadow_should_enter', False)}`",
                f"- shadow_compare_label: `{row.get('shadow_compare_label', '')}`",
                f"- shadow_reason: `{row.get('shadow_reason', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
