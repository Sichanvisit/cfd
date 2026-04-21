"""Build review-ready bounded rollout manifest from canary candidates."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BOUNDED_ROLLOUT_REVIEW_MANIFEST_VERSION = "bounded_rollout_review_manifest_v1"

BOUNDED_ROLLOUT_REVIEW_MANIFEST_COLUMNS = [
    "manifest_id",
    "market_family",
    "surface_name",
    "adapter_mode",
    "rollout_candidate_state",
    "manifest_status",
    "review_priority",
    "rollout_mode",
    "symbol_allowlist",
    "surface_allowlist",
    "sample_row_count",
    "strong_row_count",
    "positive_count",
    "negative_count",
    "unlabeled_ratio",
    "local_failure_burden",
    "positive_preview_ids",
    "negative_preview_ids",
    "review_checklist",
    "guardrail_contract",
    "recommended_next_step",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _normalize_preview_dataset(frame: pd.DataFrame | None) -> pd.DataFrame:
    dataset = frame.copy() if frame is not None else pd.DataFrame()
    if dataset.empty:
        return dataset
    for column in ("preview_row_id", "market_family", "surface_state", "enter_now_binary", "training_weight"):
        if column not in dataset.columns:
            dataset[column] = ""
    dataset["market_family"] = dataset["market_family"].fillna("").astype(str).str.upper()
    dataset["preview_row_id"] = dataset["preview_row_id"].fillna("").astype(str)
    dataset["enter_now_binary"] = pd.to_numeric(dataset["enter_now_binary"], errors="coerce")
    dataset["training_weight"] = pd.to_numeric(dataset["training_weight"], errors="coerce")
    return dataset


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_bounded_rollout_review_manifest(
    *,
    bounded_rollout_candidate_gate_payload: Mapping[str, Any] | None,
    symbol_surface_preview_evaluation_payload: Mapping[str, Any] | None,
    initial_entry_dataset: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    gate_frame = _to_frame(bounded_rollout_candidate_gate_payload)
    preview_eval_frame = _to_frame(symbol_surface_preview_evaluation_payload)
    initial_entry = _normalize_preview_dataset(initial_entry_dataset)

    if gate_frame.empty:
        empty = pd.DataFrame(columns=BOUNDED_ROLLOUT_REVIEW_MANIFEST_COLUMNS)
        return empty, {
            "bounded_rollout_review_manifest_version": BOUNDED_ROLLOUT_REVIEW_MANIFEST_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "manifest_row_count": 0,
            "review_ready_count": 0,
            "recommended_next_action": "await_review_canary_candidates",
        }

    review_candidates = gate_frame.loc[gate_frame["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE"].copy()
    rows: list[dict[str, Any]] = []
    for candidate in review_candidates.to_dict(orient="records"):
        market_family = str(candidate.get("market_family", "")).upper()
        surface_name = str(candidate.get("surface_name", ""))
        eval_row = (
            preview_eval_frame.loc[
                (preview_eval_frame["market_family"] == market_family)
                & (preview_eval_frame["surface_name"] == surface_name)
            ].iloc[0].to_dict()
            if not preview_eval_frame.empty
            and not preview_eval_frame.loc[
                (preview_eval_frame["market_family"] == market_family)
                & (preview_eval_frame["surface_name"] == surface_name)
            ].empty
            else {}
        )
        dataset_slice = initial_entry.loc[initial_entry["market_family"] == market_family].copy() if not initial_entry.empty else pd.DataFrame()
        positive_ids = dataset_slice.loc[(dataset_slice["enter_now_binary"] == 1) & (dataset_slice["training_weight"] >= 1.0), "preview_row_id"].head(5).tolist() if not dataset_slice.empty else []
        negative_ids = dataset_slice.loc[(dataset_slice["enter_now_binary"] == 0), "preview_row_id"].head(5).tolist() if not dataset_slice.empty else []
        review_checklist = [
            f"confirm_sample_rows_match_{market_family.lower()}_{surface_name}_adapter_thesis",
            "verify_negative_rows_are_true_wait_not_label_noise",
            "confirm_no_recent_entry_performance_regression_over_200ms",
            "keep_live_override_disabled_until_manual_signoff",
            "start_with_review_canary_only_no_auto_activation",
        ]
        guardrail_contract = {
            "allow_live_override": False,
            "rollout_scope": "review_canary_only",
            "allowed_symbol": market_family,
            "allowed_surface": surface_name,
            "max_canary_size_multiplier": 0.25,
            "require_no_unlabeled_rows": True,
            "require_manual_signoff": True,
            "require_strong_rows_at_least": int(candidate.get("strong_row_count", 0) or 0),
        }
        rows.append(
            {
                "manifest_id": f"bounded_rollout_review_manifest::{market_family}::{surface_name}",
                "market_family": market_family,
                "surface_name": surface_name,
                "adapter_mode": str(candidate.get("adapter_mode", "")),
                "rollout_candidate_state": str(candidate.get("rollout_candidate_state", "")),
                "manifest_status": "REVIEW_READY",
                "review_priority": str(candidate.get("rollout_priority", "P1")),
                "rollout_mode": "review_canary_only",
                "symbol_allowlist": _stable_json([market_family]),
                "surface_allowlist": _stable_json([surface_name]),
                "sample_row_count": int(candidate.get("row_count", 0) or 0),
                "strong_row_count": int(candidate.get("strong_row_count", 0) or 0),
                "positive_count": int(candidate.get("positive_count", 0) or 0),
                "negative_count": int(candidate.get("negative_count", 0) or 0),
                "unlabeled_ratio": float(candidate.get("unlabeled_ratio", 0.0) or 0.0),
                "local_failure_burden": float(candidate.get("local_failure_burden", 0.0) or 0.0),
                "positive_preview_ids": _stable_json(positive_ids),
                "negative_preview_ids": _stable_json(negative_ids),
                "review_checklist": _stable_json(review_checklist),
                "guardrail_contract": _stable_json(guardrail_contract),
                "recommended_next_step": str(candidate.get("recommended_next_step", "manual_review_required")),
            }
        )

    frame = pd.DataFrame(rows, columns=BOUNDED_ROLLOUT_REVIEW_MANIFEST_COLUMNS)
    summary = {
        "bounded_rollout_review_manifest_version": BOUNDED_ROLLOUT_REVIEW_MANIFEST_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "manifest_row_count": int(len(frame)),
        "review_ready_count": int((frame["manifest_status"] == "REVIEW_READY").sum()) if not frame.empty else 0,
        "symbol_counts": frame["market_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": "manual_review_signoff_for_canary"
        if not frame.empty
        else "await_review_canary_candidates",
    }
    return frame, summary


def render_bounded_rollout_review_manifest_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Bounded Rollout Review Manifest",
        "",
        f"- version: `{summary.get('bounded_rollout_review_manifest_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- manifest_row_count: `{summary.get('manifest_row_count', 0)}`",
        f"- review_ready_count: `{summary.get('review_ready_count', 0)}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    if not frame.empty:
        lines.extend(["## Review Packets", ""])
        for row in frame.to_dict(orient="records"):
            lines.append(
                "- "
                + f"{row.get('market_family', '')} | {row.get('surface_name', '')} | "
                + f"priority={row.get('review_priority', '')} | mode={row.get('rollout_mode', '')} | next={row.get('recommended_next_step', '')}"
            )
    return "\n".join(lines).rstrip() + "\n"
