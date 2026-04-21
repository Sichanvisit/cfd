"""Second-stage PA7 review queue processor."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_action_resolver import resolve_management_action


PATH_CHECKPOINT_PA7_REVIEW_PROCESSOR_CONTRACT_VERSION = "checkpoint_pa7_review_processor_v3"
_BACKFILL_SOURCES = {"open_trade_backfill", "closed_trade_hold_backfill", "closed_trade_runner_backfill"}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa7_review_processor_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa7_review_processor_latest.json"


def _to_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _to_text(value).lower() in {"1", "true", "yes", "y"}


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _median_abs(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return round(float(cleaned.abs().median()), 6)


def _scale_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if abs(float(denominator)) <= 1e-9:
        return None
    return round(float(numerator) / float(denominator), 6)


def _resolve_baseline_action(row: Mapping[str, Any]) -> str:
    baseline = _to_text(row.get("management_action_label")).upper()
    if baseline:
        return baseline
    return _to_text(row.get("runtime_proxy_management_action_label")).upper()


def _resolve_policy_replay_action(row: Mapping[str, Any]) -> str:
    payload = resolve_management_action(checkpoint_ctx=dict(row))
    return _to_text(payload.get("management_action_label")).upper()


def _review_group_key(row: Mapping[str, Any]) -> str:
    return " | ".join(
        [
            _to_text(row.get("symbol")).upper(),
            _to_text(row.get("surface_name")),
            _to_text(row.get("checkpoint_type")).upper(),
            _to_text(row.get("management_row_family")),
            _to_text(row.get("checkpoint_rule_family_hint")),
            _to_text(row.get("hindsight_best_management_action_label")).upper(),
        ]
    )


def _classify_group(
    *,
    row_count: int,
    checkpoint_type: str,
    blank_baseline_share: float,
    missing_score_share: float,
    baseline_match_rate: float,
    policy_replay_match_rate: float,
    resolved_baseline_action_label: str,
    policy_replay_action_label: str,
    hindsight_label: str,
    backfill_source_share: float,
    avg_abs_current_profit: float | None,
    avg_giveback_ratio: float | None,
) -> tuple[str, str, str]:
    if blank_baseline_share >= 0.60 and missing_score_share >= 0.60:
        if (
            baseline_match_rate >= 0.66
            and policy_replay_match_rate >= 0.66
            and resolved_baseline_action_label
            and policy_replay_action_label
            and hindsight_label
            and resolved_baseline_action_label == policy_replay_action_label == hindsight_label
        ):
            return (
                "hydration_gap_confirmed_cluster",
                "low",
                "sparse_baseline_but_group_is_already_consistently_aligned",
            )
        if (
            policy_replay_match_rate >= 0.80
            and policy_replay_action_label
            and hindsight_label
            and policy_replay_action_label == hindsight_label
        ):
            return (
                "hydration_gap_resolved_by_current_policy",
                "low",
                "blank_baseline_but_policy_replay_aligns_with_hindsight",
            )
        return (
            "baseline_hydration_gap",
            "high" if row_count >= 25 else "medium",
            "blank_baseline_and_missing_scores_dominate_group",
        )
    if (
        policy_replay_match_rate >= 0.85
        and policy_replay_action_label
        and hindsight_label
        and policy_replay_action_label == hindsight_label
        and (
            row_count >= 2
            or baseline_match_rate >= 0.85
            or (
                row_count == 1
                and policy_replay_match_rate >= 1.0
                and resolved_baseline_action_label == "PARTIAL_THEN_HOLD"
                and policy_replay_action_label == "PARTIAL_EXIT"
            )
        )
    ):
        return (
            "resolved_by_current_policy",
            "low",
            "current_policy_replay_now_aligns_with_hindsight",
        )
    if (
        backfill_source_share >= 0.60
        and row_count >= 2
        and (avg_abs_current_profit or 0.0) >= 50.0
        and (avg_giveback_ratio or 0.0) <= 0.10
        and hindsight_label == "WAIT"
        and baseline_match_rate <= 0.50
    ):
        return (
            "mixed_backfill_value_scale_review",
            "medium",
            "backfill_dominated_group_with_extreme_profit_scale_and_wait_hindsight",
        )
    if (
        baseline_match_rate >= 0.85
        and resolved_baseline_action_label
        and hindsight_label
        and row_count >= 10
    ):
        return (
            "confidence_only_confirmed",
            "low",
            "baseline_and_hindsight_already_mostly_agree",
        )
    if (
        resolved_baseline_action_label == "PARTIAL_EXIT"
        and policy_replay_action_label == "PARTIAL_EXIT"
        and hindsight_label == "WAIT"
        and 1 <= row_count <= 3
        and baseline_match_rate <= 0.50
        and policy_replay_match_rate <= 0.50
        and (avg_abs_current_profit or 0.0) <= 0.10
        and (avg_giveback_ratio or 0.0) >= 0.95
    ):
        return (
            "resolved_by_current_policy",
            "low",
            "near_flat_wait_boundary_already_safely_de_risked_by_partial_exit",
        )
    if (
        checkpoint_type == "FIRST_PULLBACK_CHECK"
        and resolved_baseline_action_label == "WAIT"
        and policy_replay_action_label == "WAIT"
        and hindsight_label == "WAIT"
        and row_count >= 3
        and baseline_match_rate >= 0.60
        and policy_replay_match_rate >= 0.60
        and (avg_abs_current_profit or 0.0) <= 0.25
        and (avg_giveback_ratio or 0.0) >= 0.95
    ):
        return (
            "resolved_by_current_policy",
            "low",
            "near_flat_first_pullback_wait_cluster_already_safely_aligned",
        )
    if (
        resolved_baseline_action_label
        and policy_replay_action_label
        and hindsight_label == "WAIT"
        and resolved_baseline_action_label == policy_replay_action_label
        and row_count >= 2
        and baseline_match_rate <= 0.50
        and policy_replay_match_rate <= 0.50
    ):
        return (
            "mixed_wait_boundary_review",
            "medium",
            "group_clusters_around_wait_boundary_but_current_policy_still_disagrees",
        )
    if (
        baseline_match_rate <= 0.25
        and resolved_baseline_action_label
        and hindsight_label
        and resolved_baseline_action_label != hindsight_label
    ):
        return (
            "policy_mismatch_review",
            "high",
            "baseline_and_hindsight_diverge_at_group_level",
        )
    return (
        "mixed_review",
        "medium",
        "group_contains_mixed_confidence_or_partial_alignment_signals",
    )


def _build_backfill_normalization_preview(
    *,
    group: pd.DataFrame,
    disposition: str,
    resolved_baseline_action_label: str,
    policy_replay_action_label: str,
    hindsight_label: str,
    baseline_match_rate: float,
    policy_replay_match_rate: float,
) -> dict[str, Any]:
    preview = {
        "backfill_profit_scale_ratio_hint": None,
        "backfill_abs_profit_median": None,
        "non_backfill_abs_profit_median": None,
        "normalized_backfill_abs_profit_median": None,
        "normalized_preview_state": "not_applicable",
        "normalized_preview_review_disposition": "",
        "normalized_preview_recommendation": "",
    }
    if disposition != "mixed_backfill_value_scale_review":
        return preview

    source_series = group["source"].fillna("").astype(str)
    backfill = group.loc[source_series.isin(_BACKFILL_SOURCES)].copy()
    non_backfill = group.loc[~source_series.isin(_BACKFILL_SOURCES)].copy()
    backfill_abs_profit_median = _median_abs(backfill["current_profit"])
    non_backfill_abs_profit_median = _median_abs(non_backfill["current_profit"])
    scale_ratio_hint = _scale_ratio(backfill_abs_profit_median, non_backfill_abs_profit_median)
    normalized_backfill_abs_profit_median = None
    if (
        scale_ratio_hint is not None
        and backfill_abs_profit_median is not None
        and abs(float(scale_ratio_hint)) > 1e-9
    ):
        normalized_backfill_abs_profit_median = round(
            float(backfill_abs_profit_median) / float(scale_ratio_hint),
            6,
        )

    preview.update(
        {
            "backfill_profit_scale_ratio_hint": scale_ratio_hint,
            "backfill_abs_profit_median": backfill_abs_profit_median,
            "non_backfill_abs_profit_median": non_backfill_abs_profit_median,
            "normalized_backfill_abs_profit_median": normalized_backfill_abs_profit_median,
        }
    )
    if scale_ratio_hint is None or scale_ratio_hint < 5.0:
        preview["normalized_preview_state"] = "insufficient_live_peer_reference"
        preview["normalized_preview_recommendation"] = "collect_more_live_peer_rows_before_normalization_preview"
        return preview

    preview["normalized_preview_state"] = "normalization_preview_supported"
    if (
        policy_replay_match_rate >= 0.85
        and policy_replay_action_label
        and hindsight_label
        and policy_replay_action_label == hindsight_label
    ):
        preview["normalized_preview_review_disposition"] = "resolved_by_current_policy"
        preview["normalized_preview_recommendation"] = "normalization_preview_says_current_policy_is_already_enough"
        return preview

    if (
        resolved_baseline_action_label
        and policy_replay_action_label
        and hindsight_label == "WAIT"
        and resolved_baseline_action_label == policy_replay_action_label
        and baseline_match_rate <= 0.50
        and policy_replay_match_rate <= 0.50
    ):
        preview["normalized_preview_review_disposition"] = "mixed_wait_boundary_review"
        preview["normalized_preview_recommendation"] = "normalization_preview_points_to_wait_boundary_review_after_scale_fix"
        return preview

    preview["normalized_preview_review_disposition"] = "mixed_review"
    preview["normalized_preview_recommendation"] = "normalization_preview_reduces_scale_noise_but_group_stays_mixed"
    return preview


def _build_normalized_review_handoff(
    *,
    disposition: str,
    normalization_preview: Mapping[str, Any] | None,
) -> dict[str, Any]:
    preview = dict(normalization_preview or {})
    normalized_disposition = _to_text(preview.get("normalized_preview_review_disposition"))
    if disposition != "mixed_backfill_value_scale_review" or not normalized_disposition:
        return {
            "normalized_review_handoff_state": "not_applicable",
            "normalized_review_handoff_disposition": "",
            "normalized_review_handoff_priority": "",
            "normalized_review_handoff_reason": "",
            "raw_rule_patch_blocked_by_backfill_scale": False,
        }

    if normalized_disposition == "mixed_wait_boundary_review":
        return {
            "normalized_review_handoff_state": "ready",
            "normalized_review_handoff_disposition": normalized_disposition,
            "normalized_review_handoff_priority": "medium",
            "normalized_review_handoff_reason": (
                "raw_backfill_scale_issue_isolated_so_group_moves_to_normalized_wait_boundary_review"
            ),
            "raw_rule_patch_blocked_by_backfill_scale": True,
        }
    if normalized_disposition == "resolved_by_current_policy":
        return {
            "normalized_review_handoff_state": "resolved_after_normalization_preview",
            "normalized_review_handoff_disposition": normalized_disposition,
            "normalized_review_handoff_priority": "low",
            "normalized_review_handoff_reason": (
                "normalization_preview_indicates_current_policy_is_already_sufficient"
            ),
            "raw_rule_patch_blocked_by_backfill_scale": True,
        }
    return {
        "normalized_review_handoff_state": "preview_only",
        "normalized_review_handoff_disposition": normalized_disposition,
        "normalized_review_handoff_priority": "medium",
        "normalized_review_handoff_reason": "normalization_preview_available_but_not_ready_for_handoff",
        "raw_rule_patch_blocked_by_backfill_scale": True,
    }


def build_checkpoint_pa7_review_processor(
    resolved: pd.DataFrame,
    *,
    top_n_groups: int = 12,
    sample_rows_per_group: int = 3,
) -> dict[str, Any]:
    frame = resolved.copy() if isinstance(resolved, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        return {
            "summary": {
                "contract_version": PATH_CHECKPOINT_PA7_REVIEW_PROCESSOR_CONTRACT_VERSION,
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": 0,
                "manual_exception_row_count": 0,
                "processed_group_count": 0,
                "recommended_next_action": "collect_checkpoint_rows_before_pa7_processing",
            },
            "group_rows": [],
        }

    frame["hindsight_quality_tier"] = frame.get("hindsight_quality_tier", "").fillna("").astype(str)
    frame["hindsight_manual_exception_required"] = frame.get(
        "hindsight_manual_exception_required", False
    ).apply(_to_bool)
    manual = frame.loc[
        frame["hindsight_quality_tier"].eq("manual_exception")
        | frame["hindsight_manual_exception_required"]
    ].copy()
    if manual.empty:
        return {
            "summary": {
                "contract_version": PATH_CHECKPOINT_PA7_REVIEW_PROCESSOR_CONTRACT_VERSION,
                "generated_at": datetime.now().astimezone().isoformat(),
                "resolved_row_count": int(len(frame)),
                "manual_exception_row_count": 0,
                "processed_group_count": 0,
                "recommended_next_action": "manual_exception_queue_empty",
            },
            "group_rows": [],
        }

    required_text_cols = (
        "symbol",
        "surface_name",
        "checkpoint_type",
        "management_row_family",
        "checkpoint_rule_family_hint",
        "hindsight_best_management_action_label",
        "management_action_label",
        "runtime_proxy_management_action_label",
        "source",
    )
    for column in required_text_cols:
        if column not in manual.columns:
            manual[column] = ""
        manual[column] = manual[column].fillna("").astype(str)

    for column in (
        "runtime_hold_quality_score",
        "runtime_partial_exit_ev",
        "runtime_full_exit_risk",
        "current_profit",
        "giveback_ratio",
    ):
        manual[column] = pd.to_numeric(manual.get(column), errors="coerce")

    manual["resolved_baseline_action_label"] = manual.apply(_resolve_baseline_action, axis=1)
    manual["policy_replay_action_label"] = manual.apply(_resolve_policy_replay_action, axis=1)
    manual["group_key"] = manual.apply(_review_group_key, axis=1)
    manual["baseline_matches_hindsight"] = (
        manual["resolved_baseline_action_label"].fillna("").astype(str).str.upper()
        == manual["hindsight_best_management_action_label"].fillna("").astype(str).str.upper()
    )
    manual["policy_replay_matches_hindsight"] = (
        manual["policy_replay_action_label"].fillna("").astype(str).str.upper()
        == manual["hindsight_best_management_action_label"].fillna("").astype(str).str.upper()
    )
    manual["baseline_blank"] = manual["management_action_label"].fillna("").astype(str).str.strip().eq("")
    manual["missing_all_scores"] = (
        manual["runtime_hold_quality_score"].isna()
        & manual["runtime_partial_exit_ev"].isna()
        & manual["runtime_full_exit_risk"].isna()
    )

    rows: list[dict[str, Any]] = []
    grouped = manual.groupby("group_key", dropna=False)
    for group_key, group in grouped:
        group = group.copy()
        row_count = int(len(group))
        baseline_mode = (
            group["resolved_baseline_action_label"]
            .fillna("")
            .astype(str)
            .replace("", pd.NA)
            .dropna()
            .mode()
        )
        resolved_baseline_action_label = _to_text(baseline_mode.iloc[0] if not baseline_mode.empty else "")
        hindsight_mode = (
            group["hindsight_best_management_action_label"]
            .fillna("")
            .astype(str)
            .replace("", pd.NA)
            .dropna()
            .mode()
        )
        hindsight_label = _to_text(hindsight_mode.iloc[0] if not hindsight_mode.empty else "")
        blank_baseline_share = _safe_rate(int(group["baseline_blank"].sum()), row_count)
        missing_score_share = _safe_rate(int(group["missing_all_scores"].sum()), row_count)
        baseline_match_rate = _safe_rate(int(group["baseline_matches_hindsight"].sum()), row_count)
        policy_replay_mode = (
            group["policy_replay_action_label"]
            .fillna("")
            .astype(str)
            .replace("", pd.NA)
            .dropna()
            .mode()
        )
        policy_replay_action_label = _to_text(policy_replay_mode.iloc[0] if not policy_replay_mode.empty else "")
        policy_replay_match_rate = _safe_rate(int(group["policy_replay_matches_hindsight"].sum()), row_count)
        backfill_source_share = _safe_rate(
            int(group["source"].fillna("").astype(str).isin(_BACKFILL_SOURCES).sum()),
            row_count,
        )
        avg_current_profit = (
            round(float(group["current_profit"].dropna().mean()), 6)
            if not group["current_profit"].dropna().empty
            else None
        )
        avg_abs_current_profit = abs(avg_current_profit) if avg_current_profit is not None else None
        avg_giveback_ratio = (
            round(float(group["giveback_ratio"].dropna().mean()), 6)
            if not group["giveback_ratio"].dropna().empty
            else None
        )
        disposition, priority, reason = _classify_group(
            row_count=row_count,
            checkpoint_type=_to_text(group["checkpoint_type"].mode().iloc[0] if not group["checkpoint_type"].mode().empty else "").upper(),
            blank_baseline_share=blank_baseline_share,
            missing_score_share=missing_score_share,
            baseline_match_rate=baseline_match_rate,
            policy_replay_match_rate=policy_replay_match_rate,
            resolved_baseline_action_label=resolved_baseline_action_label,
            policy_replay_action_label=policy_replay_action_label,
            hindsight_label=hindsight_label,
            backfill_source_share=backfill_source_share,
            avg_abs_current_profit=avg_abs_current_profit,
            avg_giveback_ratio=avg_giveback_ratio,
        )
        normalization_preview = _build_backfill_normalization_preview(
            group=group,
            disposition=disposition,
            resolved_baseline_action_label=resolved_baseline_action_label,
            policy_replay_action_label=policy_replay_action_label,
            hindsight_label=hindsight_label,
            baseline_match_rate=baseline_match_rate,
            policy_replay_match_rate=policy_replay_match_rate,
        )
        normalized_handoff = _build_normalized_review_handoff(
            disposition=disposition,
            normalization_preview=normalization_preview,
        )

        top_examples: list[dict[str, Any]] = []
        for _, sample in group.sort_values("generated_at").head(max(1, int(sample_rows_per_group))).iterrows():
            top_examples.append(
                {
                    "generated_at": _to_text(sample.get("generated_at")),
                    "symbol": _to_text(sample.get("symbol")).upper(),
                    "source": _to_text(sample.get("source")),
                    "surface_name": _to_text(sample.get("surface_name")),
                    "checkpoint_id": _to_text(sample.get("checkpoint_id")),
                    "checkpoint_type": _to_text(sample.get("checkpoint_type")).upper(),
                    "resolved_baseline_action_label": _to_text(sample.get("resolved_baseline_action_label")).upper(),
                    "policy_replay_action_label": _to_text(sample.get("policy_replay_action_label")).upper(),
                    "hindsight_best_management_action_label": _to_text(sample.get("hindsight_best_management_action_label")).upper(),
                    "current_profit": _to_float(sample.get("current_profit")),
                    "giveback_ratio": _to_float(sample.get("giveback_ratio")),
                    "runtime_hold_quality_score": _to_float(sample.get("runtime_hold_quality_score")),
                    "runtime_partial_exit_ev": _to_float(sample.get("runtime_partial_exit_ev")),
                    "runtime_full_exit_risk": _to_float(sample.get("runtime_full_exit_risk")),
                }
            )

        latest = group.sort_values("generated_at").iloc[-1].to_dict()
        rows.append(
            {
                "group_key": group_key,
                "symbol": _to_text(latest.get("symbol")).upper(),
                "surface_name": _to_text(latest.get("surface_name")),
                "checkpoint_type": _to_text(latest.get("checkpoint_type")).upper(),
                "management_row_family": _to_text(latest.get("management_row_family")),
                "checkpoint_rule_family_hint": _to_text(latest.get("checkpoint_rule_family_hint")),
                "resolved_baseline_action_label": resolved_baseline_action_label,
                "policy_replay_action_label": policy_replay_action_label,
                "hindsight_best_management_action_label": hindsight_label,
                "row_count": row_count,
                "blank_baseline_share": blank_baseline_share,
                "missing_score_share": missing_score_share,
                "baseline_match_rate": baseline_match_rate,
                "policy_replay_match_rate": policy_replay_match_rate,
                "avg_current_profit": avg_current_profit,
                "avg_abs_current_profit": round(float(avg_abs_current_profit), 6) if avg_abs_current_profit is not None else None,
                "avg_giveback_ratio": avg_giveback_ratio,
                "backfill_source_share": backfill_source_share,
                "review_disposition": disposition,
                "review_priority": priority,
                "review_reason": reason,
                **normalization_preview,
                **normalized_handoff,
                "samples": top_examples,
            }
        )

    disposition_rank = {
        "policy_mismatch_review": 0,
        "baseline_hydration_gap": 1,
        "mixed_backfill_value_scale_review": 2,
        "mixed_wait_boundary_review": 3,
        "mixed_review": 4,
        "resolved_by_current_policy": 5,
        "hydration_gap_resolved_by_current_policy": 6,
        "hydration_gap_confirmed_cluster": 7,
        "confidence_only_confirmed": 8,
    }
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    rows = sorted(
        rows,
        key=lambda item: (
            priority_rank.get(_to_text(item.get("review_priority")).lower(), 9),
            disposition_rank.get(_to_text(item.get("review_disposition")), 9),
            -int(item.get("row_count", 0)),
        ),
    )
    rows = rows[: max(1, int(top_n_groups))]

    disposition_counts = pd.Series([_to_text(row.get("review_disposition")) for row in rows]).value_counts().to_dict()
    normalized_preview_counts = (
        pd.Series(
            [
                _to_text(row.get("normalized_preview_review_disposition"))
                for row in rows
                if _to_text(row.get("normalized_preview_review_disposition"))
            ]
        ).value_counts().to_dict()
        if rows
        else {}
    )
    normalized_handoff_counts = (
        pd.Series(
            [
                _to_text(row.get("normalized_review_handoff_disposition"))
                for row in rows
                if _to_text(row.get("normalized_review_handoff_disposition"))
            ]
        ).value_counts().to_dict()
        if rows
        else {}
    )
    summary = {
        "contract_version": PATH_CHECKPOINT_PA7_REVIEW_PROCESSOR_CONTRACT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
        "resolved_row_count": int(len(frame)),
        "manual_exception_row_count": int(len(manual)),
        "processed_group_count": int(len(rows)),
        "review_disposition_counts": disposition_counts,
        "normalized_preview_disposition_counts": normalized_preview_counts,
        "normalized_review_handoff_counts": normalized_handoff_counts,
        "recommended_next_action": (
                "review_policy_mismatch_groups_first"
                if disposition_counts.get("policy_mismatch_review", 0) > 0
                else (
                    "work_through_baseline_hydration_gap_groups"
                    if disposition_counts.get("baseline_hydration_gap", 0) > 0
                    else (
                        "work_through_normalized_wait_boundary_handoffs"
                        if normalized_handoff_counts.get("mixed_wait_boundary_review", 0) > 0
                        else (
                            "inspect_mixed_backfill_value_scale_groups"
                            if disposition_counts.get("mixed_backfill_value_scale_review", 0) > 0
                            else (
                                "inspect_mixed_wait_boundary_groups"
                                if disposition_counts.get("mixed_wait_boundary_review", 0) > 0
                                else (
                                    "record_resolved_by_current_policy_groups_and_continue_pa7"
                                    if disposition_counts.get("resolved_by_current_policy", 0) > 0
                                    else (
                                        "record_hydration_resolved_groups_and_continue_pa7"
                                        if disposition_counts.get("hydration_gap_resolved_by_current_policy", 0) > 0
                                        else (
                                            "record_hydration_confirmed_clusters_and_continue_pa7"
                                            if disposition_counts.get("hydration_gap_confirmed_cluster", 0) > 0
                                            else "monitor_confidence_only_groups_before_pa8"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
        ),
    }
    return {"summary": summary, "group_rows": rows}
