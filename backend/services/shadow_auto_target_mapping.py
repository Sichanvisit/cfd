"""Action-target mapping redesign surface for shadow auto."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.shadow_auto_edge_metrics import (
    DEFAULT_BRIDGE_TARGET_MAPPING,
    DEFAULT_BRIDGE_TARGET_VARIANT_MAPPING,
    DEFAULT_MANUAL_TARGET_MAPPING,
    DEFAULT_MANUAL_TARGET_VARIANT_MAPPING,
    classify_bridge_target,
    classify_bridge_target_variant,
    classify_manual_target,
    classify_manual_target_variant,
)
from backend.services.trade_csv_schema import now_kst_dt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANUAL_PATH = PROJECT_ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"
DEFAULT_TRAINING_CORPUS_PATH = PROJECT_ROOT / "data" / "analysis" / "shadow_auto" / "semantic_shadow_training_corpus_latest.json"

SHADOW_AUTO_TARGET_MAPPING_VERSION = "shadow_auto_target_mapping_v1"
SHADOW_AUTO_TARGET_MAPPING_COLUMNS = [
    "mapping_namespace",
    "source_label",
    "source_family",
    "target_action_class",
    "target_action_variant",
    "target_reason",
    "confidence_floor",
    "mapping_confidence",
    "mapping_reason",
    "shadow_usage_rule",
    "current_count",
    "priority_hint",
]


def load_shadow_auto_target_mapping_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_shadow_training_corpus_context_frame(path: str | Path) -> pd.DataFrame:
    json_path = Path(path)
    if not json_path.exists():
        return pd.DataFrame()
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return pd.DataFrame()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    flattened: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        economic = row.get("economic_target_summary") if isinstance(row.get("economic_target_summary"), dict) else {}
        state_hint = row.get("state25_runtime_hint_v1") if isinstance(row.get("state25_runtime_hint_v1"), dict) else {}
        forecast = row.get("forecast_runtime_summary_v1") if isinstance(row.get("forecast_runtime_summary_v1"), dict) else {}
        flattened.append(
            {
                "entry_wait_quality_label": str(row.get("entry_wait_quality_label", "") or "").lower(),
                "learning_total_label": str(economic.get("learning_total_label", "") or "").lower(),
                "signed_exit_score": economic.get("signed_exit_score", 0.0),
                "wait_bias_hint": str(state_hint.get("wait_bias_hint", "") or "").lower(),
                "forecast_decision_hint": str(forecast.get("decision_hint", "") or "").upper(),
            }
        )
    return pd.DataFrame(flattened)


def _confidence_floor(label: str, family: str, counts: pd.DataFrame) -> str:
    subset = counts.loc[
        counts["manual_wait_teacher_label"].fillna("").astype(str).eq(label)
        & counts["manual_wait_teacher_family"].fillna("").astype(str).eq(family)
    ].copy()
    if subset.empty or "manual_wait_teacher_confidence" not in subset.columns:
        return "medium" if label in DEFAULT_MANUAL_TARGET_MAPPING else "low"
    values = subset["manual_wait_teacher_confidence"].fillna("").astype(str).str.lower().tolist()
    if "high" in values:
        return "high"
    if "medium" in values:
        return "medium"
    return "low"


def build_shadow_auto_target_mapping(
    manual_truth: pd.DataFrame | None,
    training_corpus: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manual_df = manual_truth.copy() if manual_truth is not None else pd.DataFrame()
    training_df = training_corpus.copy() if training_corpus is not None else pd.DataFrame()
    for column in ("manual_wait_teacher_label", "manual_wait_teacher_family", "manual_wait_teacher_confidence"):
        if column not in manual_df.columns:
            manual_df[column] = ""
    rows: list[dict[str, Any]] = []

    manual_counts = (
        manual_df.groupby(
            ["manual_wait_teacher_label", "manual_wait_teacher_family", "manual_wait_teacher_confidence"],
            dropna=False,
        )
        .size()
        .reset_index(name="current_count")
        if not manual_df.empty
        else pd.DataFrame(
            columns=[
                "manual_wait_teacher_label",
                "manual_wait_teacher_family",
                "manual_wait_teacher_confidence",
                "current_count",
            ]
        )
    )
    collapsed_counts = (
        manual_counts.groupby(["manual_wait_teacher_label", "manual_wait_teacher_family"], dropna=False)["current_count"]
        .sum()
        .reset_index()
        if not manual_counts.empty
        else pd.DataFrame(columns=["manual_wait_teacher_label", "manual_wait_teacher_family", "current_count"])
    )
    for row in collapsed_counts.to_dict(orient="records"):
        label = str(row.get("manual_wait_teacher_label", "") or "")
        family = str(row.get("manual_wait_teacher_family", "") or "")
        target_action_class = classify_manual_target(label, family)
        confidence_floor = _confidence_floor(label, family, manual_counts)
        target_reason = f"manual_label_family_to_direct_action::{target_action_class}"
        rows.append(
            {
                "mapping_namespace": "manual_wait_teacher_label",
                "source_label": label,
                "source_family": family,
                "target_action_class": target_action_class,
                "target_action_variant": classify_manual_target_variant(label, family),
                "target_reason": target_reason,
                "confidence_floor": confidence_floor,
                "mapping_confidence": "high" if label in DEFAULT_MANUAL_TARGET_MAPPING else confidence_floor,
                "mapping_reason": target_reason,
                "shadow_usage_rule": "use_for_target_redesign_reference",
                "current_count": int(row.get("current_count", 0) or 0),
                "priority_hint": "high" if target_action_class != "wait_more" else "normal",
            }
        )

    bridge_priority = {
        "bad_wait_missed_move": "high",
        "missed_move_by_wait": "high",
        "good_wait_protective_exit": "high",
        "good_wait_reversal_escape": "high",
    }
    bridge_context_rows: dict[str, dict[str, Any]] = {}
    if not training_df.empty and "entry_wait_quality_label" in training_df.columns:
        for label, subset in training_df.groupby("entry_wait_quality_label", dropna=False):
            label_text = str(label or "").strip().lower()
            if not label_text:
                continue
            target_series = pd.Series(
                [classify_bridge_target_variant(row) for row in subset.to_dict(orient="records")]
            )
            if target_series.empty:
                continue
            counts = target_series.value_counts()
            dominant_variant = str(counts.index[0])
            dominant_target = classify_bridge_target(label_text, subset.iloc[0].to_dict())
            dominant_share = float(counts.iloc[0]) / float(max(1, len(subset)))
            bridge_context_rows[label_text] = {
                "target_action_class": dominant_target,
                "target_action_variant": dominant_variant,
                "confidence_floor": "high" if dominant_share >= 0.85 else ("medium" if dominant_share >= 0.6 else "low"),
                "target_reason": f"bridge_context_majority::{dominant_target}",
                "mapping_reason": f"bridge_context_majority::{dominant_target}::{int(counts.iloc[0])}/{int(len(subset))}",
                "current_count": int(len(subset)),
            }

    all_bridge_labels = sorted(set(DEFAULT_BRIDGE_TARGET_MAPPING) | set(bridge_context_rows))
    for label in all_bridge_labels:
        context_row = bridge_context_rows.get(label, {})
        target_action_variant = str(
            context_row.get("target_action_variant")
            or DEFAULT_BRIDGE_TARGET_VARIANT_MAPPING.get(label, "wait_more")
        )
        target_action_class = str(
            context_row.get("target_action_class")
            or DEFAULT_BRIDGE_TARGET_MAPPING.get(label, "wait_more")
        )
        confidence_floor = str(context_row.get("confidence_floor") or ("low" if label == "insufficient_evidence" else "medium"))
        target_reason = str(context_row.get("target_reason") or f"bridge_proxy_label_to_direct_action::{target_action_class}")
        rows.append(
            {
                "mapping_namespace": "bridge_entry_wait_quality_label",
                "source_label": label,
                "source_family": "",
                "target_action_class": target_action_class,
                "target_action_variant": target_action_variant,
                "target_reason": target_reason,
                "confidence_floor": confidence_floor,
                "mapping_confidence": confidence_floor,
                "mapping_reason": str(context_row.get("mapping_reason") or target_reason),
                "shadow_usage_rule": "use_for_preview_alignment_audit",
                "current_count": int(context_row.get("current_count", 0) or 0),
                "priority_hint": bridge_priority.get(label, "normal"),
            }
        )

    frame = pd.DataFrame(rows, columns=SHADOW_AUTO_TARGET_MAPPING_COLUMNS)
    summary = {
        "shadow_auto_target_mapping_version": SHADOW_AUTO_TARGET_MAPPING_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "namespace_counts": frame["mapping_namespace"].value_counts().to_dict() if not frame.empty else {},
        "target_action_class_counts": frame["target_action_class"].value_counts().to_dict() if not frame.empty else {},
        "target_action_variant_counts": frame["target_action_variant"].value_counts().to_dict() if not frame.empty else {},
        "high_priority_row_count": int(frame["priority_hint"].fillna("").astype(str).eq("high").sum()) if not frame.empty else 0,
        "confidence_floor_counts": frame["confidence_floor"].value_counts().to_dict() if not frame.empty else {},
    }
    return frame, summary


def render_shadow_auto_target_mapping_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Shadow Target Mapping",
        "",
        f"- version: `{summary.get('shadow_auto_target_mapping_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- namespace_counts: `{summary.get('namespace_counts', {})}`",
        f"- target_action_class_counts: `{summary.get('target_action_class_counts', {})}`",
        f"- target_action_variant_counts: `{summary.get('target_action_variant_counts', {})}`",
        f"- confidence_floor_counts: `{summary.get('confidence_floor_counts', {})}`",
        "",
        "## Mapping Rows",
        "",
    ]
    if frame.empty:
        lines.append("- no target mappings available")
        return "\n".join(lines) + "\n"
    for row in frame.head(20).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('mapping_namespace', '')} :: {row.get('source_label', '')}",
                "",
                f"- target_action_class: `{row.get('target_action_class', '')}`",
                f"- target_action_variant: `{row.get('target_action_variant', '')}`",
                f"- target_reason: `{row.get('target_reason', '')}`",
                f"- confidence_floor: `{row.get('confidence_floor', '')}`",
                f"- current_count: `{row.get('current_count', 0)}`",
                f"- shadow_usage_rule: `{row.get('shadow_usage_rule', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
