"""SA4e dataset bias audit and rebalance suggestions for shadow auto."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.shadow_auto_edge_metrics import (
    attach_manual_truth,
    enrich_action_frame,
)
from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_DATASET_BIAS_AUDIT_VERSION = "shadow_auto_dataset_bias_audit_v1"
SHADOW_AUTO_DATASET_BIAS_AUDIT_COLUMNS = [
    "audit_scope_kind",
    "audit_scope_value",
    "row_count",
    "manual_reference_row_count",
    "manual_truth_share",
    "baseline_copy_share_proxy",
    "baseline_copy_share_mapped",
    "baseline_copy_share_effective",
    "proxy_enter_share",
    "mapped_enter_share",
    "effective_enter_share",
    "target_mapping_disagreement_share",
    "freeze_family_share",
    "collect_more_truth_share",
    "target_action_entropy",
    "scene_family_concentration",
    "evidence_gap_share",
    "recommended_rebalance_action",
]

SHADOW_AUTO_REBALANCED_CORPUS_COLUMNS = [
    "bridge_adapter_row_id",
    "bridge_decision_time",
    "symbol",
    "entry_wait_quality_label",
    "scene_family",
    "baseline_action_class",
    "baseline_action_variant",
    "proxy_target_action_class",
    "proxy_target_action_variant",
    "mapped_target_action_class",
    "mapped_target_action_variant",
    "manual_reference_found",
    "manual_reference_gap_minutes",
    "manual_wait_teacher_label",
    "manual_wait_teacher_family",
    "manual_target_action_class",
    "manual_target_action_variant",
    "effective_target_action_class",
    "effective_target_action_variant",
    "bridge_wait_better_entry_premium",
    "manual_wait_better_entry_premium",
    "effective_wait_better_entry_premium",
    "target_mapping_disagreement_flag",
    "baseline_copy_flag_proxy",
    "baseline_copy_flag_mapped",
    "baseline_copy_flag_effective",
    "freeze_family_flag",
    "collect_more_truth_flag",
    "evidence_gap_flag",
    "exclude_from_preview_train",
    "sample_weight",
    "rebalance_bucket",
]


def load_shadow_auto_dataset_bias_audit_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _target_action_entropy(values: pd.Series) -> float:
    if values is None or values.empty:
        return 0.0
    dist = values.fillna("").astype(str).value_counts(normalize=True)
    entropy = 0.0
    for value in dist.tolist():
        probability = float(value)
        if probability <= 0.0:
            continue
        entropy -= probability * math.log(probability, 2)
    return float(entropy)


def _prepare_feature_rows(
    feature_rows: pd.DataFrame,
    manual_truth: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = enrich_action_frame(
        attach_manual_truth(
            feature_rows.copy() if feature_rows is not None else pd.DataFrame(),
            manual_truth.copy() if manual_truth is not None else pd.DataFrame(),
        )
    )
    if frame.empty:
        return pd.DataFrame(columns=SHADOW_AUTO_REBALANCED_CORPUS_COLUMNS)

    frame["baseline_copy_flag_proxy"] = (
        frame["baseline_action_variant"].fillna("").astype(str)
        == frame["proxy_target_action_variant"].fillna("").astype(str)
    )
    frame["baseline_copy_flag_mapped"] = (
        frame["baseline_action_variant"].fillna("").astype(str)
        == frame["mapped_target_action_variant"].fillna("").astype(str)
    )
    frame["baseline_copy_flag_effective"] = (
        frame["baseline_action_variant"].fillna("").astype(str)
        == frame["effective_target_action_variant"].fillna("").astype(str)
    )
    frame["evidence_gap_flag"] = frame.get("entry_wait_quality_label", pd.Series(dtype=object)).fillna("").astype(str).str.lower().eq("insufficient_evidence")

    target_counts = frame["effective_target_action_variant"].value_counts().to_dict()
    minority_floor = min(target_counts.values()) if target_counts else 0
    weights: list[float] = []
    buckets: list[str] = []
    exclude_flags: list[bool] = []
    for row in frame.to_dict(orient="records"):
        weight = 1.0
        effective_variant = str(row.get("effective_target_action_variant") or "")
        if bool(row.get("manual_reference_found")):
            weight += 2.0
            confidence = str(row.get("manual_wait_teacher_confidence", "") or "").lower()
            if confidence == "high":
                weight += 1.0
            elif confidence == "medium":
                weight += 0.5
        if effective_variant == "wait_better_entry":
            weight += 0.75
        elif effective_variant == "exit_protect":
            weight += 0.5
        elif effective_variant.startswith("enter_now"):
            weight += 0.5
        if bool(row.get("target_mapping_disagreement_flag")):
            weight += 1.0
        if not bool(row.get("baseline_copy_flag_effective")):
            weight += 0.5
        if bool(row.get("freeze_family_flag")):
            weight -= 0.25
        if bool(row.get("collect_more_truth_flag")):
            weight -= 0.25
        if bool(row.get("baseline_copy_flag_effective")) and not bool(row.get("manual_reference_found")):
            weight -= 0.5
        if minority_floor and target_counts.get(effective_variant, 0) == minority_floor:
            weight += 0.5
        weight = max(0.25, round(weight, 2))
        exclude_from_preview_train = bool(row.get("freeze_family_flag")) and not bool(row.get("manual_reference_found"))
        if bool(row.get("manual_reference_found")):
            bucket = "manual_truth_anchor"
        elif exclude_from_preview_train:
            bucket = "separate_freeze_family"
        elif bool(row.get("collect_more_truth_flag")):
            bucket = "collect_more_truth"
        elif bool(row.get("target_mapping_disagreement_flag")):
            bucket = "retarget_priority"
        elif bool(row.get("baseline_copy_flag_effective")):
            bucket = "downweight_baseline_copy"
        elif bool(row.get("freeze_family_flag")):
            bucket = "separate_freeze_family"
        else:
            bucket = "balanced_review"
        weights.append(weight)
        buckets.append(bucket)
        exclude_flags.append(exclude_from_preview_train)
    frame["sample_weight"] = weights
    frame["rebalance_bucket"] = buckets
    frame["exclude_from_preview_train"] = exclude_flags
    return frame[[col for col in SHADOW_AUTO_REBALANCED_CORPUS_COLUMNS if col in frame.columns]].copy()


def _recommended_rebalance_action(
    *,
    row_count: int,
    manual_truth_share: float,
    disagreement_share: float,
    baseline_copy_share_effective: float,
    freeze_family_share: float,
    collect_more_truth_share: float,
    scene_family_concentration: float,
) -> str:
    if row_count <= 0:
        return "collect_more_shadow_training_rows"
    if manual_truth_share < 0.10 and collect_more_truth_share >= 0.50:
        return "collect_more_manual_truth_then_reweight"
    if disagreement_share >= 0.25:
        return "rebuild_targets_from_action_mapping"
    if baseline_copy_share_effective >= 0.75 and manual_truth_share < 0.20:
        return "downweight_baseline_copy_rows"
    if freeze_family_share >= 0.60:
        return "separate_freeze_only_families"
    if scene_family_concentration >= 0.80:
        return "expand_scene_coverage"
    return "maintain_current_mix"


def build_shadow_auto_dataset_bias_audit(
    feature_rows: pd.DataFrame | None,
    *,
    manual_truth: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    prepared = _prepare_feature_rows(
        feature_rows.copy() if feature_rows is not None else pd.DataFrame(),
        manual_truth=manual_truth,
    )

    rows: list[dict[str, Any]] = []
    if not prepared.empty:
        scopes: list[tuple[str, str, pd.DataFrame]] = [("overall", "all", prepared)]
        for symbol, subset in prepared.groupby("symbol", dropna=False):
            scopes.append(("symbol", str(symbol or "unknown"), subset.copy()))
        for scene_family, subset in prepared.groupby("scene_family", dropna=False):
            scopes.append(("scene_family", str(scene_family or "unknown"), subset.copy()))

        for scope_kind, scope_value, subset in scopes:
            row_count = int(len(subset))
            scene_concentration = 0.0
            if scope_kind == "overall" and "scene_family" in subset.columns and row_count:
                scene_concentration = float(subset["scene_family"].fillna("").astype(str).value_counts(normalize=True).iloc[0])
            elif row_count:
                scene_concentration = 1.0
            disagreement_share = float(subset["target_mapping_disagreement_flag"].mean()) if row_count else 0.0
            manual_truth_share = float(subset["manual_reference_found"].mean()) if row_count else 0.0
            freeze_family_share = float(subset["freeze_family_flag"].mean()) if row_count else 0.0
            collect_more_truth_share = float(subset["collect_more_truth_flag"].mean()) if row_count else 0.0
            evidence_gap_share = float(subset["evidence_gap_flag"].mean()) if row_count else 0.0
            baseline_copy_share_effective = float(subset["baseline_copy_flag_effective"].mean()) if row_count else 0.0
            rows.append(
                {
                    "audit_scope_kind": scope_kind,
                    "audit_scope_value": scope_value,
                    "row_count": row_count,
                    "manual_reference_row_count": int(subset["manual_reference_found"].sum()) if row_count else 0,
                    "manual_truth_share": round(manual_truth_share, 6),
                    "baseline_copy_share_proxy": round(float(subset["baseline_copy_flag_proxy"].mean()) if row_count else 0.0, 6),
                    "baseline_copy_share_mapped": round(float(subset["baseline_copy_flag_mapped"].mean()) if row_count else 0.0, 6),
                    "baseline_copy_share_effective": round(baseline_copy_share_effective, 6),
                    "proxy_enter_share": round(float(subset["proxy_target_action_class"].eq("enter_now").mean()) if row_count else 0.0, 6),
                    "mapped_enter_share": round(float(subset["mapped_target_action_class"].eq("enter_now").mean()) if row_count else 0.0, 6),
                    "effective_enter_share": round(float(subset["effective_target_action_class"].eq("enter_now").mean()) if row_count else 0.0, 6),
                    "target_mapping_disagreement_share": round(disagreement_share, 6),
                    "freeze_family_share": round(freeze_family_share, 6),
                    "collect_more_truth_share": round(collect_more_truth_share, 6),
                    "target_action_entropy": round(_target_action_entropy(subset["effective_target_action_class"]), 6),
                    "scene_family_concentration": round(scene_concentration, 6),
                    "evidence_gap_share": round(evidence_gap_share, 6),
                    "recommended_rebalance_action": _recommended_rebalance_action(
                        row_count=row_count,
                        manual_truth_share=manual_truth_share,
                        disagreement_share=disagreement_share,
                        baseline_copy_share_effective=baseline_copy_share_effective,
                        freeze_family_share=freeze_family_share,
                        collect_more_truth_share=collect_more_truth_share,
                        scene_family_concentration=scene_concentration,
                    ),
                }
            )

    audit = pd.DataFrame(rows, columns=SHADOW_AUTO_DATASET_BIAS_AUDIT_COLUMNS)
    summary = {
        "shadow_auto_dataset_bias_audit_version": SHADOW_AUTO_DATASET_BIAS_AUDIT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "audit_row_count": int(len(audit)),
        "rebalanced_row_count": int(len(prepared)),
        "manual_reference_row_count": int(prepared["manual_reference_found"].sum()) if not prepared.empty else 0,
        "manual_truth_share": round(float(prepared["manual_reference_found"].mean()), 6) if not prepared.empty else 0.0,
        "recommended_rebalance_action_counts": audit["recommended_rebalance_action"].value_counts().to_dict() if not audit.empty else {},
        "rebalance_bucket_counts": prepared["rebalance_bucket"].value_counts().to_dict() if not prepared.empty else {},
    }
    return audit, prepared, summary


def render_shadow_auto_dataset_bias_audit_markdown(summary: dict[str, Any], audit: pd.DataFrame, rebalanced: pd.DataFrame) -> str:
    lines = [
        "# Shadow Dataset Bias Audit",
        "",
        f"- version: `{summary.get('shadow_auto_dataset_bias_audit_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- audit_row_count: `{summary.get('audit_row_count', 0)}`",
        f"- rebalanced_row_count: `{summary.get('rebalanced_row_count', 0)}`",
        f"- manual_reference_row_count: `{summary.get('manual_reference_row_count', 0)}`",
        f"- manual_truth_share: `{summary.get('manual_truth_share', 0.0)}`",
        f"- recommended_rebalance_action_counts: `{summary.get('recommended_rebalance_action_counts', {})}`",
        f"- rebalance_bucket_counts: `{summary.get('rebalance_bucket_counts', {})}`",
        "",
        "## Audit Rows",
        "",
    ]
    if audit.empty:
        lines.append("- no dataset bias audit rows available")
        return "\n".join(lines) + "\n"
    for row in audit.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('audit_scope_kind', '')} :: {row.get('audit_scope_value', '')}",
                "",
                f"- manual_truth_share: `{row.get('manual_truth_share', 0.0)}`",
                f"- target_mapping_disagreement_share: `{row.get('target_mapping_disagreement_share', 0.0)}`",
                f"- baseline_copy_share_effective: `{row.get('baseline_copy_share_effective', 0.0)}`",
                f"- freeze_family_share: `{row.get('freeze_family_share', 0.0)}`",
                f"- collect_more_truth_share: `{row.get('collect_more_truth_share', 0.0)}`",
                f"- target_action_entropy: `{row.get('target_action_entropy', 0.0)}`",
                f"- recommended_rebalance_action: `{row.get('recommended_rebalance_action', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
