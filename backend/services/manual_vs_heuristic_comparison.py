"""Manual-vs-heuristic comparison report builder."""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


MANUAL_VS_HEURISTIC_COMPARISON_VERSION = "manual_vs_heuristic_comparison_v1"

MANUAL_VS_HEURISTIC_COMPARISON_COLUMNS = [
    "comparison_id",
    "episode_id",
    "symbol",
    "timeframe",
    "scene_id",
    "chart_context",
    "box_regime_scope",
    "anchor_side",
    "anchor_time",
    "anchor_price",
    "manual_truth_source_bucket",
    "manual_truth_review_state",
    "manual_wait_teacher_label",
    "manual_wait_teacher_polarity",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "manual_wait_teacher_usage_bucket",
    "manual_wait_teacher_confidence",
    "ideal_entry_time",
    "ideal_entry_price",
    "ideal_exit_time",
    "ideal_exit_price",
    "manual_teacher_confidence",
    "manual_annotation_note",
    "heuristic_barrier_main_label",
    "heuristic_barrier_confidence_tier",
    "heuristic_barrier_outcome_family",
    "heuristic_wait_family",
    "heuristic_wait_subtype",
    "heuristic_wait_usage_bucket",
    "heuristic_counterfactual_family",
    "heuristic_counterfactual_cost_delta_r",
    "heuristic_drift_status",
    "heuristic_barrier_reason_summary",
    "heuristic_forecast_family",
    "heuristic_forecast_reason_summary",
    "heuristic_belief_family",
    "heuristic_belief_reason_summary",
    "heuristic_evidence_source_kind",
    "heuristic_evidence_recoverability_grade",
    "heuristic_evidence_quality",
    "evidence_gap_minutes",
    "current_rich_overlap_flag",
    "current_rich_proxy_support",
    "heuristic_source_file",
    "heuristic_source_kind",
    "heuristic_match_gap_minutes",
    "heuristic_reconstruction_mode",
    "heuristic_reconstruction_source_file",
    "manual_vs_barrier_match",
    "manual_vs_wait_family_match",
    "manual_vs_forecast_alignment",
    "manual_vs_belief_alignment",
    "overall_alignment_grade",
    "miss_type",
    "mismatch_severity",
    "primary_correction_target",
    "repeated_case_signature",
    "correction_worthiness_class",
    "freeze_worthiness_class",
    "rule_change_readiness",
    "frequency_score",
    "severity_score",
    "current_rich_reproducibility_score",
    "evidence_quality_score",
    "correction_cost_score",
    "correction_priority_score",
    "freeze_risk_score",
    "correction_priority_tier",
    "recommended_next_action",
    "mismatch_disposition",
    "canonical_promotion_readiness",
    "canonical_promotion_reason",
    "canonical_promotion_recommendation",
    "comparison_status",
    "review_round",
    "review_owner",
    "review_comment",
    "created_at",
    "updated_at",
    "comparison_version",
]

ENTRY_DECISION_HEURISTIC_COLUMNS = [
    "decision_row_key",
    "time",
    "signal_bar_ts",
    "symbol",
    "action",
    "observe_action",
    "observe_side",
    "observe_reason",
    "blocked_by",
    "core_reason",
    "entry_wait_decision",
    "barrier_candidate_recommended_family",
    "barrier_candidate_supporting_label",
    "barrier_action_hint_confidence",
    "barrier_action_hint_reason_summary",
    "forecast_decision_hint",
    "forecast_state25_scene_family",
    "belief_candidate_recommended_family",
    "belief_action_hint_reason_summary",
]


def _entry_decision_source_paths(path: str | Path) -> list[Path]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    candidates = [csv_path]
    if csv_path.name == "entry_decisions.csv":
        sibling_legacy = sorted(
            csv_path.parent.glob("entry_decisions.legacy_*.csv"),
            key=lambda item: item.name,
        )
        candidates.extend(sibling_legacy)
    seen: set[str] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)
    return ordered


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
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _parse_local_timestamp(value: object) -> pd.Timestamp | None:
    text = _to_text(value, "")
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        return stamp.tz_convert("Asia/Seoul").tz_localize(None)
    return stamp


def _annotation_source_bucket(annotation_source: object) -> str:
    source = _to_text(annotation_source, "").lower()
    if source == "assistant_current_rich_seed":
        return "current_rich_draft"
    if source == "assistant_chart_inferred":
        return "assistant_inferred_canonical"
    if source == "chart_annotated":
        return "canonical_chart_reviewed"
    if source:
        return source
    return "canonical_unknown_source"


def _manual_truth_review_state(review_status: object, source_bucket: str) -> str:
    review = _to_text(review_status, "").lower()
    if review and review != "pending":
        return review
    if source_bucket == "current_rich_draft":
        return "needs_manual_recheck"
    if source_bucket == "assistant_inferred_canonical":
        return "assistant_inferred_coarse"
    if source_bucket == "canonical_chart_reviewed":
        return "reviewed"
    return "accepted"


def _confidence_rank(value: object) -> int:
    text = _to_text(value, "").lower()
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(text, 0)


def _has_sufficient_episode_detail(row: Mapping[str, Any]) -> bool:
    return bool(
        _to_text(row.get("anchor_time", ""), "")
        and _to_text(row.get("manual_wait_teacher_label", ""), "")
        and (
            _to_text(row.get("ideal_entry_time", ""), "")
            or _to_text(row.get("ideal_exit_time", ""), "")
        )
    )


def _utc_epoch_to_local_timestamp(value: object) -> pd.Timestamp | None:
    try:
        if value in ("", None):
            return None
        return (
            pd.to_datetime(float(value), unit="s", utc=True)
            .tz_convert("Asia/Seoul")
            .tz_localize(None)
        )
    except (TypeError, ValueError, OverflowError):
        return None


def load_manual_wait_teacher_annotations(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return normalize_manual_wait_teacher_annotation_df(
                pd.read_csv(csv_path, encoding=encoding, low_memory=False)
            )
        except Exception:
            continue
    return normalize_manual_wait_teacher_annotation_df(pd.read_csv(csv_path, low_memory=False))


def load_entry_decision_heuristic_frame(path: str | Path) -> pd.DataFrame:
    source_paths = _entry_decision_source_paths(path)
    if not source_paths:
        return pd.DataFrame(columns=ENTRY_DECISION_HEURISTIC_COLUMNS + ["heuristic_time"])
    frames: list[pd.DataFrame] = []
    for csv_path in source_paths:
        frame: pd.DataFrame | None = None
        for encoding in ("utf-8-sig", "utf-8", "cp949"):
            try:
                frame = pd.read_csv(
                    csv_path,
                    usecols=lambda col: col in ENTRY_DECISION_HEURISTIC_COLUMNS,
                    encoding=encoding,
                    low_memory=False,
                )
                break
            except Exception:
                continue
        if frame is None:
            frame = pd.read_csv(
                csv_path,
                usecols=lambda col: col in ENTRY_DECISION_HEURISTIC_COLUMNS,
                low_memory=False,
            )
        frame["heuristic_source_file"] = csv_path.name
        frame["heuristic_source_kind"] = "current" if csv_path.name == "entry_decisions.csv" else "legacy"
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    for column in ENTRY_DECISION_HEURISTIC_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper().str.strip()
    frame["heuristic_time"] = frame["signal_bar_ts"].apply(_utc_epoch_to_local_timestamp)
    missing_mask = frame["heuristic_time"].isna()
    if missing_mask.any():
        fallback = frame.loc[missing_mask, "time"].apply(_parse_local_timestamp)
        frame.loc[missing_mask, "heuristic_time"] = fallback
    frame = frame[frame["symbol"].ne("") & frame["heuristic_time"].notna()].copy()
    if "decision_row_key" in frame.columns:
        dedupe_key = frame["decision_row_key"].fillna("").astype(str).str.strip()
        keyed = frame[dedupe_key.ne("")].copy()
        unkeyed = frame[dedupe_key.eq("")].copy()
        if not keyed.empty:
            keyed = keyed.drop_duplicates(subset=["decision_row_key"], keep="last")
        if not unkeyed.empty:
            unkeyed = unkeyed.drop_duplicates(
                subset=["symbol", "time", "action", "observe_reason", "blocked_by"],
                keep="last",
            )
        frame = pd.concat([keyed, unkeyed], ignore_index=True)
    else:
        frame = frame.drop_duplicates(
            subset=["symbol", "time", "action", "observe_reason", "blocked_by"],
            keep="last",
        )
    return frame


def load_global_detail_fallback_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _manual_to_expected_barrier_labels(label: str) -> tuple[set[str], set[str]]:
    key = _to_text(label, "").lower()
    exact: set[str] = set()
    partial: set[str] = set()
    if key == "good_wait_better_entry":
        exact = {"correct_wait"}
        partial = {"relief_success"}
    elif key == "good_wait_protective_exit":
        exact = {"relief_success"}
        partial = {"avoided_loss"}
    elif key == "good_wait_reversal_escape":
        exact = {"relief_failure"}
        partial = {"avoided_loss"}
    elif key == "neutral_wait_small_value":
        exact = {"avoided_loss"}
    elif key == "bad_wait_missed_move":
        exact = {"missed_profit"}
        partial = {"overblock"}
    elif key == "bad_wait_no_timing_edge":
        exact = {"avoided_loss"}
        partial = {"overblock"}
    return exact, partial


def _derive_wait_family_from_barrier(
    barrier_label: str,
    recommended_family: str,
) -> tuple[str, str, str]:
    label = _to_text(barrier_label, "").lower()
    recommended = _to_text(recommended_family, "").lower()
    if label == "correct_wait":
        return "timing_improvement", "correct_wait_strict", "strict"
    if label == "missed_profit":
        return "failed_wait", "wait_but_missed_move", "usable"
    if label == "overblock":
        return "failed_wait", "wait_but_missed_move", "usable"
    if label == "relief_success":
        return "protective_exit", "profitable_wait_then_exit", "usable"
    if label == "relief_failure":
        return "reversal_escape", "wait_then_escape_on_reversal", "usable"
    if label == "avoided_loss":
        if recommended in {"relief_watch", "relief_release_bias"}:
            return "protective_exit", "profitable_wait_then_exit", "usable"
        return "neutral_wait", "small_value_wait", "diagnostic"
    if recommended in {"wait_bias", "block_bias"}:
        return "neutral_wait", "small_value_wait", "diagnostic"
    if recommended in {"relief_watch", "relief_release_bias"}:
        return "protective_exit", "profitable_wait_then_exit", "usable"
    return "", "", ""


def _derive_heuristic_snapshot(row: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(row or {})
    barrier_label = _to_text(source.get("barrier_candidate_supporting_label", ""), "").lower()
    recommended_family = _to_text(source.get("barrier_candidate_recommended_family", ""), "").lower()
    wait_family, wait_subtype, wait_usage_bucket = _derive_wait_family_from_barrier(
        barrier_label,
        recommended_family,
    )
    barrier_outcome_family = wait_family
    reason = _to_text(
        source.get("barrier_action_hint_reason_summary", "")
        or source.get("core_reason", "")
        or source.get("observe_reason", "")
        or source.get("blocked_by", ""),
        "",
    ).lower()
    return {
        "heuristic_barrier_main_label": barrier_label,
        "heuristic_barrier_confidence_tier": _to_text(source.get("barrier_action_hint_confidence", ""), "").lower(),
        "heuristic_barrier_outcome_family": barrier_outcome_family,
        "heuristic_wait_family": wait_family,
        "heuristic_wait_subtype": wait_subtype,
        "heuristic_wait_usage_bucket": wait_usage_bucket,
        "heuristic_counterfactual_family": _to_text(source.get("entry_wait_decision", ""), "").lower(),
        "heuristic_counterfactual_cost_delta_r": "",
        "heuristic_drift_status": "",
        "heuristic_barrier_reason_summary": reason,
        "heuristic_forecast_family": _to_text(source.get("forecast_decision_hint", ""), "").lower(),
        "heuristic_forecast_reason_summary": _to_text(source.get("forecast_state25_scene_family", ""), "").lower(),
        "heuristic_belief_family": _to_text(source.get("belief_candidate_recommended_family", ""), "").lower(),
        "heuristic_belief_reason_summary": _to_text(source.get("belief_action_hint_reason_summary", ""), "").lower(),
        "heuristic_source_file": _to_text(source.get("heuristic_source_file", ""), ""),
        "heuristic_source_kind": _to_text(source.get("heuristic_source_kind", ""), "").lower(),
        "heuristic_reconstruction_mode": "",
        "heuristic_reconstruction_source_file": "",
    }


def _heuristic_snapshot_has_semantic_evidence(snapshot: Mapping[str, Any]) -> bool:
    return any(
        _to_text(snapshot.get(key, ""), "")
        for key in [
            "heuristic_barrier_main_label",
            "heuristic_wait_family",
            "heuristic_forecast_family",
            "heuristic_belief_family",
            "heuristic_barrier_reason_summary",
        ]
    )


def _derive_heuristic_snapshot_from_global_detail(row: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(row or {})
    wait_decision = _to_text(source.get("global_detail_entry_wait_decision", ""), "").lower()
    blocked_by = _to_text(source.get("global_detail_blocked_by", ""), "").lower()
    observe_reason = _to_text(source.get("global_detail_observe_reason", ""), "").lower()
    core_reason = _to_text(source.get("global_detail_core_reason", ""), "").lower()

    recommended_family = ""
    barrier_label = ""
    wait_family = ""
    wait_subtype = ""
    wait_usage_bucket = ""
    confidence_tier = ""

    # Recent recovered NAS mismatches show that lower-edge rebound-probe blocks were being
    # over-normalized into generic avoided-loss / neutral-wait. Treat them as timing-improvement
    # or protective-exit flavored waits before falling back to the generic blocked/skip branch.
    if (
        wait_decision == "skip"
        and "range_lower_buy_requires_lower_edge" in blocked_by
        and "lower_rebound_probe_observe" in observe_reason
    ):
        if "probe_action" in core_reason:
            recommended_family = "relief_watch"
            barrier_label = "relief_success"
            wait_family = "protective_exit"
            wait_subtype = "profitable_wait_then_exit"
            wait_usage_bucket = "usable"
            confidence_tier = "fallback_low"
        else:
            recommended_family = "wait_bias"
            barrier_label = "correct_wait"
            wait_family = "timing_improvement"
            wait_subtype = "better_entry_after_wait"
            wait_usage_bucket = "usable"
            confidence_tier = "fallback_low"
    elif "wait" in wait_decision:
        recommended_family = "wait_bias"
        barrier_label = "correct_wait"
        wait_family = "timing_improvement"
        wait_subtype = "better_entry_after_wait"
        wait_usage_bucket = "usable"
        confidence_tier = "fallback_medium"
    elif wait_decision == "skip" or blocked_by:
        recommended_family = "block_bias"
        barrier_label = "avoided_loss"
        wait_family, wait_subtype, wait_usage_bucket = _derive_wait_family_from_barrier(
            barrier_label,
            recommended_family,
        )
        confidence_tier = "fallback_low"
    elif observe_reason:
        recommended_family = "observe_only"
        confidence_tier = "fallback_low"

    reason = _to_text(
        observe_reason or core_reason or blocked_by or source.get("global_detail_recoverability_reason", ""),
        "",
    )

    return {
        "heuristic_barrier_main_label": barrier_label,
        "heuristic_barrier_confidence_tier": confidence_tier,
        "heuristic_barrier_outcome_family": wait_family,
        "heuristic_wait_family": wait_family,
        "heuristic_wait_subtype": wait_subtype,
        "heuristic_wait_usage_bucket": wait_usage_bucket,
        "heuristic_counterfactual_family": wait_decision,
        "heuristic_counterfactual_cost_delta_r": "",
        "heuristic_drift_status": "",
        "heuristic_barrier_reason_summary": reason,
        "heuristic_forecast_family": "",
        "heuristic_forecast_reason_summary": "",
        "heuristic_belief_family": "",
        "heuristic_belief_reason_summary": "",
        "heuristic_source_file": _to_text(source.get("heuristic_source_file", ""), ""),
        "heuristic_source_kind": _to_text(source.get("global_detail_source_kind", ""), "").lower(),
        "heuristic_reconstruction_mode": "global_detail_fallback",
        "heuristic_reconstruction_source_file": _to_text(source.get("global_detail_source_file", ""), ""),
    }


def _derive_evidence_fields(
    snapshot: Mapping[str, Any],
    match_meta: Mapping[str, Any],
    fallback_row: Mapping[str, Any] | None,
    manual_truth_source_bucket: str,
) -> dict[str, Any]:
    reconstruction_mode = _to_text(snapshot.get("heuristic_reconstruction_mode", ""), "").lower()
    source_kind_raw = _to_text(snapshot.get("heuristic_source_kind", ""), "").lower()
    has_semantic_evidence = _heuristic_snapshot_has_semantic_evidence(snapshot)
    gap_minutes = match_meta.get("gap_minutes", "")
    gap_value = _to_float(gap_minutes, 0.0)

    if reconstruction_mode == "global_detail_fallback":
        evidence_source_kind = "global_detail_fallback"
        recoverability = _to_text(
            (fallback_row or {}).get("global_detail_recoverability_grade", ""),
            "medium",
        ).lower()
    elif source_kind_raw == "current":
        evidence_source_kind = "current_csv"
        recoverability = "high" if has_semantic_evidence else "none"
    elif source_kind_raw == "legacy":
        evidence_source_kind = "legacy_csv"
        recoverability = "medium" if has_semantic_evidence else "none"
    else:
        evidence_source_kind = "manual_only"
        recoverability = "none"

    if evidence_source_kind == "manual_only":
        evidence_quality = "missing"
    elif evidence_source_kind == "global_detail_fallback":
        if recoverability == "high" and gap_value <= 30:
            evidence_quality = "rich"
        elif recoverability in {"high", "medium"} and gap_value <= 120:
            evidence_quality = "usable"
        elif recoverability != "none":
            evidence_quality = "thin"
        else:
            evidence_quality = "missing"
    elif evidence_source_kind == "current_csv":
        if has_semantic_evidence and gap_value <= 30:
            evidence_quality = "rich"
        elif has_semantic_evidence:
            evidence_quality = "usable"
        else:
            evidence_quality = "missing"
    else:
        if has_semantic_evidence and gap_value <= 60:
            evidence_quality = "usable"
        elif has_semantic_evidence:
            evidence_quality = "thin"
        else:
            evidence_quality = "missing"

    current_rich_overlap = (
        "yes"
        if evidence_source_kind == "current_csv" or manual_truth_source_bucket == "current_rich_draft"
        else "no"
    )
    return {
        "heuristic_evidence_source_kind": evidence_source_kind,
        "heuristic_evidence_recoverability_grade": recoverability,
        "heuristic_evidence_quality": evidence_quality,
        "evidence_gap_minutes": gap_minutes,
        "current_rich_overlap_flag": current_rich_overlap,
    }


def _derive_current_rich_proxy_support(
    *,
    current_rich_overlap_flag: str,
    overall_alignment_grade: str,
    miss_type: str,
) -> str:
    if current_rich_overlap_flag != "yes":
        return "not_checked"
    if overall_alignment_grade == "unknown":
        return "not_checked"
    if miss_type in {
        "false_avoided_loss",
        "missed_good_wait",
        "wrong_protective_interpretation",
        "wrong_reversal_escape_interpretation",
    }:
        return "supports_shift" if overall_alignment_grade == "mismatch" else "mixed"
    if miss_type == "wrong_failed_wait_interpretation":
        return "mixed" if overall_alignment_grade == "mismatch" else "supports_hold"
    if overall_alignment_grade in {"match", "partial_match"}:
        return "supports_hold"
    return "mixed"


def _severity_score(value: object) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(_to_text(value, "").lower(), 0)


def _evidence_quality_score(value: object) -> int:
    return {
        "rich": 3,
        "usable": 2,
        "thin": 1,
        "missing": 1,
    }.get(_to_text(value, "").lower(), 1)


def _correction_cost_score(miss_type: object, correction_target: object) -> int:
    miss_key = _to_text(miss_type, "").lower()
    target_key = _to_text(correction_target, "").lower()
    if miss_key == "wrong_failed_wait_interpretation":
        return 1
    if miss_key in {"false_avoided_loss", "wrong_protective_interpretation", "wrong_reversal_escape_interpretation"}:
        return 2
    if target_key == "wait_family_mapping":
        return 3
    if target_key == "barrier_bias_rule":
        return 2
    return 2


def _derive_canonical_promotion_fields(row: Mapping[str, Any]) -> dict[str, str]:
    source_bucket = _to_text(row.get("manual_truth_source_bucket", ""), "")
    review_state = _to_text(row.get("manual_truth_review_state", ""), "")
    confidence = _to_text(
        row.get("manual_teacher_confidence", "")
        or row.get("manual_wait_teacher_confidence", ""),
        "",
    )
    sufficient_detail = _has_sufficient_episode_detail(row)

    if source_bucket == "current_rich_draft":
        if review_state in {"needs_manual_recheck", "review_needed"}:
            return {
                "canonical_promotion_readiness": "review_needed",
                "canonical_promotion_reason": "current-rich draft still needs manual review",
                "canonical_promotion_recommendation": "keep_in_current_rich_draft",
            }
        if _confidence_rank(confidence) < 2:
            return {
                "canonical_promotion_readiness": "hold_current_rich_only",
                "canonical_promotion_reason": "confidence below medium",
                "canonical_promotion_recommendation": "keep_in_current_rich_draft",
            }
        if not sufficient_detail:
            return {
                "canonical_promotion_readiness": "insufficient_episode_detail",
                "canonical_promotion_reason": "episode coordinates are incomplete",
                "canonical_promotion_recommendation": "keep_in_current_rich_draft",
            }
        return {
            "canonical_promotion_readiness": "ready",
            "canonical_promotion_reason": "reviewed current-rich draft with sufficient confidence",
            "canonical_promotion_recommendation": "promote_to_canonical",
        }

    return {
        "canonical_promotion_readiness": "ready",
        "canonical_promotion_reason": "already part of canonical manual truth corpus",
        "canonical_promotion_recommendation": "promote_to_canonical",
    }


def _apply_priority_decision_fields(report: pd.DataFrame) -> pd.DataFrame:
    if report.empty:
        return report
    signature_counts = report["repeated_case_signature"].fillna("").astype(str).value_counts().to_dict()
    updated_rows: list[dict[str, Any]] = []
    for _, base_row in report.iterrows():
        row = base_row.to_dict()
        miss_type = _to_text(row.get("miss_type", ""), "")
        signature = _to_text(row.get("repeated_case_signature", ""), "")
        gap_value = _to_float(row.get("evidence_gap_minutes", ""), 0.0)
        current_support = _to_text(row.get("current_rich_proxy_support", ""), "")
        evidence_quality = _to_text(row.get("heuristic_evidence_quality", ""), "")

        frequency_score = 1
        if signature_counts.get(signature, 0) >= 3:
            frequency_score = 3
        elif signature_counts.get(signature, 0) == 2:
            frequency_score = 2

        severity_score = _severity_score(row.get("mismatch_severity", ""))
        reproducibility_score = {
            "supports_shift": 3,
            "supports_hold": 3,
            "mixed": 2,
            "not_checked": 1,
        }.get(current_support, 1)
        evidence_score = _evidence_quality_score(evidence_quality)
        cost_score = _correction_cost_score(
            row.get("miss_type", ""),
            row.get("primary_correction_target", ""),
        )
        correction_priority_score = (
            frequency_score
            + severity_score
            + reproducibility_score
            + evidence_score
            + cost_score
        )

        freeze_risk_score = 0
        if evidence_quality in {"thin", "missing"}:
            freeze_risk_score += 2
        if gap_value > 120:
            freeze_risk_score += 2
        elif gap_value > 60:
            freeze_risk_score += 1
        if current_support in {"mixed", "not_checked"}:
            freeze_risk_score += 2
        if cost_score <= 1:
            freeze_risk_score += 1
        if miss_type == "insufficient_heuristic_evidence":
            freeze_risk_score += 2

        if not miss_type or miss_type == "insufficient_heuristic_evidence":
            correction_class = "not_correction_worthy"
        elif (
            evidence_score >= 2
            and reproducibility_score >= 3
            and severity_score >= 2
            and cost_score >= 2
        ):
            correction_class = "correction_worthy"
        elif evidence_score >= 2 and severity_score >= 1:
            correction_class = "candidate_correction"
        else:
            correction_class = "not_correction_worthy"

        if not miss_type:
            freeze_class = "not_freeze_worthy"
        elif freeze_risk_score >= 5:
            freeze_class = "freeze_worthy"
        elif current_support in {"mixed", "not_checked"}:
            freeze_class = "hold_for_more_truth"
        else:
            freeze_class = "not_freeze_worthy"

        if not miss_type:
            readiness = "ready"
        elif miss_type == "insufficient_heuristic_evidence" or evidence_quality == "missing":
            readiness = "insufficient_evidence"
        elif _to_text(row.get("manual_truth_review_state", ""), "") in {"needs_manual_recheck", "review_needed"}:
            readiness = "needs_manual_recheck"
        elif current_support == "not_checked" or gap_value > 60:
            readiness = "needs_more_recent_truth"
        else:
            readiness = "ready"

        if correction_class == "correction_worthy" and readiness == "ready":
            priority_tier = "P1" if correction_priority_score >= 11 else "P2"
            next_action = "edit_rule_now"
            mismatch_disposition = "edit_rule_now"
        elif freeze_class == "freeze_worthy":
            priority_tier = "hold"
            next_action = "freeze_and_monitor"
            mismatch_disposition = "freeze_and_monitor"
        elif readiness in {"needs_more_recent_truth", "needs_manual_recheck"}:
            priority_tier = "hold"
            next_action = "collect_current_rich_truth"
            mismatch_disposition = "collect_current_rich_truth"
        elif correction_class == "candidate_correction":
            priority_tier = "P3"
            next_action = "review_as_next_family_candidate"
            mismatch_disposition = "keep_as_casebook_only"
        else:
            priority_tier = "hold"
            next_action = "keep_as_casebook_only"
            mismatch_disposition = "keep_as_casebook_only"

        promotion_fields = _derive_canonical_promotion_fields(row)
        row.update(
            {
                "correction_worthiness_class": correction_class,
                "freeze_worthiness_class": freeze_class,
                "rule_change_readiness": readiness,
                "frequency_score": frequency_score,
                "severity_score": severity_score,
                "current_rich_reproducibility_score": reproducibility_score,
                "evidence_quality_score": evidence_score,
                "correction_cost_score": cost_score,
                "correction_priority_score": correction_priority_score,
                "freeze_risk_score": freeze_risk_score,
                "correction_priority_tier": priority_tier,
                "recommended_next_action": next_action,
                "mismatch_disposition": mismatch_disposition,
                **promotion_fields,
            }
        )
        updated_rows.append(row)
    return pd.DataFrame(updated_rows)


def _build_global_detail_fallback_lookup(frame: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty or "episode_id" not in frame.columns:
        return {}
    source = frame.copy()
    if "global_detail_row_found" in source.columns:
        source = source[source["global_detail_row_found"].fillna(0).astype(int).eq(1)].copy()
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in source.iterrows():
        lookup[_to_text(row.get("episode_id", ""), "")] = row.to_dict()
    return lookup


def _compare_manual_vs_barrier(manual_label: str, heuristic_label: str, heuristic_family: str) -> str:
    if not heuristic_label:
        return "unknown"
    exact, partial = _manual_to_expected_barrier_labels(manual_label)
    if heuristic_label in exact:
        return "match"
    if heuristic_label in partial:
        return "partial_match"
    manual_family = _to_text(_manual_wait_teacher_defaults(manual_label).get("manual_wait_teacher_family", ""), "").lower()
    if manual_family and heuristic_family and manual_family == heuristic_family:
        return "partial_match"
    return "mismatch"


def _manual_wait_teacher_defaults(label: str) -> Mapping[str, str]:
    from backend.services.manual_wait_teacher_annotation_schema import manual_wait_teacher_defaults

    return manual_wait_teacher_defaults(label)


def _compare_manual_vs_wait_family(manual_family: str, manual_subtype: str, heuristic_family: str, heuristic_subtype: str) -> str:
    if not heuristic_family:
        return "unknown"
    if manual_family == heuristic_family and manual_subtype == heuristic_subtype and manual_subtype:
        return "match"
    if manual_family == heuristic_family:
        return "partial_match"
    return "mismatch"


def _compute_miss_type(
    manual_label: str,
    manual_family: str,
    heuristic_label: str,
    heuristic_family: str,
) -> tuple[str, str, str]:
    if not heuristic_label and not heuristic_family:
        return "insufficient_heuristic_evidence", "medium", "insufficient_owner_coverage"
    label = _to_text(manual_label, "").lower()
    h_label = _to_text(heuristic_label, "").lower()
    h_family = _to_text(heuristic_family, "").lower()
    if label == "good_wait_better_entry" and h_family != "timing_improvement":
        if h_label == "avoided_loss":
            return "false_avoided_loss", "high", "barrier_bias_rule"
        return "missed_good_wait", "high", "wait_family_mapping"
    if label == "good_wait_protective_exit" and h_family != "protective_exit":
        return "wrong_protective_interpretation", "high", "protective_exit_interpretation"
    if label == "good_wait_reversal_escape" and h_family != "reversal_escape":
        return "wrong_reversal_escape_interpretation", "high", "reversal_escape_interpretation"
    if label == "neutral_wait_small_value" and h_family == "failed_wait":
        return "overly_neutral_wait", "medium", "wait_family_mapping"
    if label in {"bad_wait_missed_move", "bad_wait_no_timing_edge"} and h_family not in {"failed_wait", "neutral_wait"}:
        return "wrong_failed_wait_interpretation", "medium", "barrier_bias_rule"
    if label == "bad_wait_missed_move" and h_label not in {"missed_profit", "overblock"}:
        return "wrong_failed_wait_interpretation", "high", "barrier_bias_rule"
    return "", "low", ""


def _overall_alignment(*statuses: str) -> str:
    filtered = [status for status in statuses if status]
    if not filtered:
        return "unknown"
    if all(status == "match" for status in filtered):
        return "match"
    if any(status == "mismatch" for status in filtered):
        if any(status in {"match", "partial_match"} for status in filtered):
            return "partial_match"
        return "mismatch"
    if any(status == "partial_match" for status in filtered):
        return "partial_match"
    if all(status == "unknown" for status in filtered):
        return "unknown"
    return filtered[0]


def _build_heuristic_index(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for symbol, group in frame.groupby("symbol", sort=False):
        ordered = group.sort_values("heuristic_time", kind="stable")
        times = [pd.Timestamp(value).value for value in ordered["heuristic_time"]]
        rows = [record for _, record in ordered.iterrows()]
        index[str(symbol)] = {
            "times": times,
            "rows": rows,
        }
    return index


def _nearest_heuristic_row(
    anchor_time: pd.Timestamp | None,
    symbol: str,
    heuristic_index: Mapping[str, Any],
    *,
    max_gap_minutes: int,
) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    if anchor_time is None:
        return None, {"reason": "manual_anchor_missing"}
    bucket = heuristic_index.get(symbol.upper())
    if not bucket:
        return None, {"reason": "heuristic_symbol_missing"}
    times = list(bucket.get("times", []) or [])
    rows = list(bucket.get("rows", []) or [])
    if not times:
        return None, {"reason": "heuristic_symbol_empty"}
    target = pd.Timestamp(anchor_time).value
    pos = bisect_left(times, target)
    candidates: list[tuple[float, int]] = []
    for idx in (pos - 1, pos):
        if 0 <= idx < len(times):
            gap_minutes = abs(times[idx] - target) / 60_000_000_000
            candidates.append((gap_minutes, idx))
    if not candidates:
        return None, {"reason": "heuristic_time_missing"}
    gap_minutes, best_idx = min(candidates, key=lambda item: (item[0], item[1]))
    if gap_minutes > float(max_gap_minutes):
        return None, {"reason": "heuristic_gap_exceeds_limit", "gap_minutes": round(gap_minutes, 3)}
    return rows[best_idx].to_dict(), {"reason": "matched", "gap_minutes": round(gap_minutes, 3)}


def build_manual_vs_heuristic_comparison_report(
    annotations: pd.DataFrame,
    heuristic_frame: pd.DataFrame,
    *,
    global_detail_fallback_frame: pd.DataFrame | None = None,
    max_gap_minutes: int = 120,
    created_at: str | None = None,
    review_owner: str = "codex",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manual = normalize_manual_wait_teacher_annotation_df(annotations)
    heuristics = heuristic_frame.copy()
    heuristic_index = _build_heuristic_index(heuristics)
    global_detail_lookup = _build_global_detail_fallback_lookup(global_detail_fallback_frame)
    now_text = _to_text(created_at, datetime.now().astimezone().isoformat())

    rows: list[dict[str, Any]] = []
    match_reason_counts: Counter[str] = Counter()
    symbol_match_counts: Counter[str] = Counter()

    for _, manual_row in manual.iterrows():
        manual_dict = manual_row.to_dict()
        anchor_time = _parse_local_timestamp(manual_dict.get("anchor_time", ""))
        manual_truth_source_bucket = _annotation_source_bucket(manual_dict.get("annotation_source", ""))
        manual_truth_review_state = _manual_truth_review_state(
            manual_dict.get("review_status", ""),
            manual_truth_source_bucket,
        )
        heuristic_row, match_meta = _nearest_heuristic_row(
            anchor_time,
            _to_text(manual_dict.get("symbol", "")),
            heuristic_index,
            max_gap_minutes=max_gap_minutes,
        )
        match_reason = _to_text(match_meta.get("reason", "unknown"))
        match_reason_counts[match_reason] += 1
        if heuristic_row is not None:
            symbol_match_counts[_to_text(manual_dict.get("symbol", "")).upper()] += 1
        heuristic_snapshot = _derive_heuristic_snapshot(heuristic_row)
        fallback_row = global_detail_lookup.get(_to_text(manual_dict.get("episode_id", ""), ""))
        if not _heuristic_snapshot_has_semantic_evidence(heuristic_snapshot) and fallback_row:
            heuristic_snapshot = _derive_heuristic_snapshot_from_global_detail(fallback_row)
            if not heuristic_snapshot.get("heuristic_source_file", ""):
                heuristic_snapshot["heuristic_source_file"] = _to_text(
                    manual_dict.get("heuristic_source_file", ""),
                    "",
                )
        manual_family = _to_text(manual_dict.get("manual_wait_teacher_family", ""), "").lower()
        manual_subtype = _to_text(manual_dict.get("manual_wait_teacher_subtype", ""), "").lower()
        manual_label = _to_text(manual_dict.get("manual_wait_teacher_label", ""), "").lower()

        barrier_match = _compare_manual_vs_barrier(
            manual_label,
            heuristic_snapshot.get("heuristic_barrier_main_label", ""),
            heuristic_snapshot.get("heuristic_wait_family", ""),
        )
        wait_match = _compare_manual_vs_wait_family(
            manual_family,
            manual_subtype,
            heuristic_snapshot.get("heuristic_wait_family", ""),
            heuristic_snapshot.get("heuristic_wait_subtype", ""),
        )
        forecast_alignment = (
            "unknown"
            if not heuristic_snapshot.get("heuristic_forecast_family", "")
            else "partial_match"
        )
        belief_alignment = (
            "unknown"
            if not heuristic_snapshot.get("heuristic_belief_family", "")
            else "partial_match"
        )
        overall = _overall_alignment(barrier_match, wait_match)
        miss_type, mismatch_severity, correction_target = _compute_miss_type(
            manual_label,
            manual_family,
            heuristic_snapshot.get("heuristic_barrier_main_label", ""),
            heuristic_snapshot.get("heuristic_wait_family", ""),
        )
        evidence_fields = _derive_evidence_fields(
            heuristic_snapshot,
            match_meta,
            fallback_row,
            manual_truth_source_bucket,
        )
        current_rich_proxy_support = _derive_current_rich_proxy_support(
            current_rich_overlap_flag=_to_text(evidence_fields.get("current_rich_overlap_flag", ""), ""),
            overall_alignment_grade=overall,
            miss_type=miss_type,
        )
        signature_parts = [
            _to_text(manual_dict.get("symbol", "")).upper(),
            manual_family or "manual_none",
            heuristic_snapshot.get("heuristic_wait_family", "") or "heuristic_none",
            miss_type or "aligned",
        ]
        row = {
            "comparison_id": f"manual_vs_heuristic::{_to_text(manual_dict.get('episode_id', ''))}",
            "episode_id": _to_text(manual_dict.get("episode_id", "")),
            "symbol": _to_text(manual_dict.get("symbol", "")).upper(),
            "timeframe": _to_text(manual_dict.get("timeframe", "")),
            "scene_id": _to_text(manual_dict.get("scene_id", "")),
            "chart_context": _to_text(manual_dict.get("chart_context", "")),
            "box_regime_scope": _to_text(manual_dict.get("box_regime_scope", "")),
            "anchor_side": _to_text(manual_dict.get("anchor_side", "")).upper(),
            "anchor_time": _to_text(manual_dict.get("anchor_time", "")),
            "anchor_price": _to_text(manual_dict.get("anchor_price", "")),
            "manual_truth_source_bucket": manual_truth_source_bucket,
            "manual_truth_review_state": manual_truth_review_state,
            "manual_wait_teacher_label": manual_label,
            "manual_wait_teacher_polarity": _to_text(manual_dict.get("manual_wait_teacher_polarity", "")).lower(),
            "manual_wait_teacher_family": manual_family,
            "manual_wait_teacher_subtype": manual_subtype,
            "manual_wait_teacher_usage_bucket": _to_text(manual_dict.get("manual_wait_teacher_usage_bucket", "")).lower(),
            "manual_wait_teacher_confidence": _to_text(manual_dict.get("manual_wait_teacher_confidence", "")).lower(),
            "ideal_entry_time": _to_text(manual_dict.get("ideal_entry_time", "")),
            "ideal_entry_price": _to_text(manual_dict.get("ideal_entry_price", "")),
            "ideal_exit_time": _to_text(manual_dict.get("ideal_exit_time", "")),
            "ideal_exit_price": _to_text(manual_dict.get("ideal_exit_price", "")),
            "manual_teacher_confidence": _to_text(manual_dict.get("manual_teacher_confidence", "")).lower(),
            "manual_annotation_note": _to_text(manual_dict.get("annotation_note", "")),
            **heuristic_snapshot,
            **evidence_fields,
            "heuristic_match_gap_minutes": match_meta.get("gap_minutes", ""),
            "current_rich_proxy_support": current_rich_proxy_support,
            "manual_vs_barrier_match": barrier_match,
            "manual_vs_wait_family_match": wait_match,
            "manual_vs_forecast_alignment": forecast_alignment,
            "manual_vs_belief_alignment": belief_alignment,
            "overall_alignment_grade": overall,
            "miss_type": miss_type,
            "mismatch_severity": mismatch_severity,
            "primary_correction_target": correction_target,
            "repeated_case_signature": "|".join(signature_parts),
            "comparison_status": "draft",
            "review_round": "v0",
            "review_owner": review_owner,
            "review_comment": (
                f"nearest entry_decisions heuristic snapshot; match_reason={match_reason}; "
                f"gap_minutes={match_meta.get('gap_minutes', '')}"
            ),
            "created_at": now_text,
            "updated_at": now_text,
            "comparison_version": MANUAL_VS_HEURISTIC_COMPARISON_VERSION,
        }
        rows.append(row)

    report = pd.DataFrame(rows)
    report = _apply_priority_decision_fields(report)
    for column in MANUAL_VS_HEURISTIC_COMPARISON_COLUMNS:
        if column not in report.columns:
            report[column] = ""
    report = report[MANUAL_VS_HEURISTIC_COMPARISON_COLUMNS].copy()

    manual_anchor_times = manual["anchor_time"].apply(_parse_local_timestamp)
    heuristic_times = heuristics["heuristic_time"] if "heuristic_time" in heuristics.columns else pd.Series(dtype="datetime64[ns]")
    summary = {
        "comparison_version": MANUAL_VS_HEURISTIC_COMPARISON_VERSION,
        "manual_episode_count": int(len(report)),
        "symbol_counts": report["symbol"].value_counts(dropna=False).to_dict(),
        "match_reason_counts": dict(match_reason_counts),
        "heuristic_matched_rows": int(sum(symbol_match_counts.values())),
        "heuristic_unmatched_rows": int(len(report) - sum(symbol_match_counts.values())),
        "global_detail_fallback_used_rows": int(
            (report["heuristic_reconstruction_mode"].fillna("").astype(str) == "global_detail_fallback").sum()
        ),
        "symbol_match_counts": dict(symbol_match_counts),
        "barrier_match_counts": report["manual_vs_barrier_match"].value_counts(dropna=False).to_dict(),
        "wait_family_match_counts": report["manual_vs_wait_family_match"].value_counts(dropna=False).to_dict(),
        "overall_alignment_counts": report["overall_alignment_grade"].value_counts(dropna=False).to_dict(),
        "miss_type_counts": report["miss_type"].replace("", "aligned").value_counts(dropna=False).to_dict(),
        "primary_correction_target_counts": report["primary_correction_target"].replace("", "none").value_counts(dropna=False).to_dict(),
        "correction_worthiness_counts": report["correction_worthiness_class"].value_counts(dropna=False).to_dict(),
        "freeze_worthiness_counts": report["freeze_worthiness_class"].value_counts(dropna=False).to_dict(),
        "rule_change_readiness_counts": report["rule_change_readiness"].value_counts(dropna=False).to_dict(),
        "correction_priority_tier_counts": report["correction_priority_tier"].value_counts(dropna=False).to_dict(),
        "recommended_next_action_counts": report["recommended_next_action"].value_counts(dropna=False).to_dict(),
        "canonical_promotion_readiness_counts": report["canonical_promotion_readiness"].value_counts(dropna=False).to_dict(),
        "assistant_inferred_rows": int((manual["annotation_source"] == "assistant_chart_inferred").sum()),
        "current_rich_draft_rows": int((manual["annotation_source"] == "assistant_current_rich_seed").sum()),
        "chart_annotated_rows": int((manual["annotation_source"] == "chart_annotated").sum()),
        "manual_anchor_time_min": (
            manual_anchor_times.dropna().min().isoformat() if not manual_anchor_times.dropna().empty else ""
        ),
        "manual_anchor_time_max": (
            manual_anchor_times.dropna().max().isoformat() if not manual_anchor_times.dropna().empty else ""
        ),
        "heuristic_time_min": (
            pd.Timestamp(heuristic_times.dropna().min()).isoformat() if not heuristic_times.dropna().empty else ""
        ),
        "heuristic_time_max": (
            pd.Timestamp(heuristic_times.dropna().max()).isoformat() if not heuristic_times.dropna().empty else ""
        ),
    }
    return report, summary


def render_manual_vs_heuristic_markdown(summary: Mapping[str, Any]) -> str:
    miss_counts = dict(summary.get("miss_type_counts", {}) or {})
    top_miss = ", ".join(
        f"{key}={value}"
        for key, value in sorted(miss_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ) or "none"
    next_actions = dict(summary.get("recommended_next_action_counts", {}) or {})
    top_next_actions = ", ".join(
        f"{key}={value}"
        for key, value in sorted(next_actions.items(), key=lambda item: (-item[1], item[0]))[:5]
    ) or "none"
    lines = [
        "# Manual vs Heuristic Comparison Report v1",
        "",
        f"- episodes: `{summary.get('manual_episode_count', 0)}`",
        f"- symbols: `{summary.get('symbol_counts', {})}`",
        f"- match reasons: `{summary.get('match_reason_counts', {})}`",
        f"- heuristic matched rows: `{summary.get('heuristic_matched_rows', 0)}`",
        f"- heuristic unmatched rows: `{summary.get('heuristic_unmatched_rows', 0)}`",
        f"- manual anchor window: `{summary.get('manual_anchor_time_min', '')}` -> `{summary.get('manual_anchor_time_max', '')}`",
        f"- heuristic window: `{summary.get('heuristic_time_min', '')}` -> `{summary.get('heuristic_time_max', '')}`",
        f"- barrier match counts: `{summary.get('barrier_match_counts', {})}`",
        f"- wait-family match counts: `{summary.get('wait_family_match_counts', {})}`",
        f"- overall alignment counts: `{summary.get('overall_alignment_counts', {})}`",
        f"- top miss types: `{top_miss}`",
        f"- correction worthiness: `{summary.get('correction_worthiness_counts', {})}`",
        f"- freeze worthiness: `{summary.get('freeze_worthiness_counts', {})}`",
        f"- rule change readiness: `{summary.get('rule_change_readiness_counts', {})}`",
        f"- correction priority tiers: `{summary.get('correction_priority_tier_counts', {})}`",
        f"- recommended next actions: `{top_next_actions}`",
        f"- canonical promotion readiness: `{summary.get('canonical_promotion_readiness_counts', {})}`",
        f"- chart annotated rows: `{summary.get('chart_annotated_rows', 0)}`",
        f"- assistant inferred rows: `{summary.get('assistant_inferred_rows', 0)}`",
        f"- current-rich draft rows: `{summary.get('current_rich_draft_rows', 0)}`",
    ]
    return "\n".join(lines) + "\n"
