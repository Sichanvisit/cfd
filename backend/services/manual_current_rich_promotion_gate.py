"""Promotion gate between current-rich draft rows and canonical manual truth."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


MANUAL_CURRENT_RICH_PROMOTION_GATE_VERSION = "manual_current_rich_promotion_gate_v0"

MANUAL_CURRENT_RICH_PROMOTION_GATE_COLUMNS = [
    "gate_id",
    "episode_id",
    "queue_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "manual_teacher_confidence",
    "review_status",
    "capture_priority",
    "row_count",
    "unique_signal_minutes",
    "review_decision",
    "canonical_action",
    "calibration_value_bucket",
    "episode_detail_status",
    "promotion_readiness",
    "promotion_score",
    "review_priority_tier",
    "promotion_decision_reason",
    "promotion_reviewer",
    "promotion_reviewed_at",
    "promotion_blockers",
    "promotion_blocking_reason",
    "promotion_followup_needed",
    "recommended_next_action",
    "canonical_promotion_recommendation",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(str(value).strip()))
    except Exception:
        return int(default)


def _confidence_rank(value: object) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(_to_text(value, "").lower(), 0)


def _episode_to_queue_id(episode_id: object) -> str:
    text = _to_text(episode_id, "")
    if text.startswith("manual_seed::"):
        return text.replace("manual_seed::", "current_rich::", 1)
    return text


def _has_sufficient_episode_detail(row: Mapping[str, Any]) -> bool:
    has_anchor = bool(_to_text(row.get("anchor_time", ""), ""))
    has_label = bool(_to_text(row.get("manual_wait_teacher_label", ""), ""))
    has_entry = bool(_to_text(row.get("ideal_entry_time", ""), ""))
    has_exit = bool(_to_text(row.get("ideal_exit_time", ""), ""))
    return has_anchor and has_label and has_entry and has_exit


def _review_priority_tier(
    *,
    promotion_readiness: str,
    calibration_value_bucket: str,
    capture_priority: str,
    confidence_rank: int,
    episode_detail_status: str,
    canonical_action: str,
) -> str:
    if promotion_readiness == "ready":
        return "ready_high" if calibration_value_bucket == "high" and confidence_rank >= 3 else "ready_normal"
    if promotion_readiness == "do_not_promote":
        return "control_only"
    if canonical_action == "hold_review_needed":
        return "review_needed_high_priority"
    if promotion_readiness == "insufficient_episode_detail":
        return "review_needed_high_priority" if capture_priority == "high" else "review_needed_normal"
    if promotion_readiness == "review_needed":
        if capture_priority == "high" or calibration_value_bucket == "high":
            return "review_needed_high_priority"
        if capture_priority == "medium" or confidence_rank >= 2:
            return "review_needed_normal"
        return "review_needed_low_signal"
    if promotion_readiness in {"hold_current_rich_only", "low_calibration_value"}:
        if capture_priority == "high" and episode_detail_status == "complete":
            return "review_needed_normal"
        return "review_needed_low_signal"
    return "review_needed_normal"


def _promotion_followup_needed(
    *,
    promotion_readiness: str,
    canonical_action: str,
    episode_detail_status: str,
) -> str:
    if promotion_readiness == "ready":
        return "promotion_signoff"
    if canonical_action == "do_not_promote_failed_wait_seed" or promotion_readiness == "do_not_promote":
        return "keep_as_control_only"
    if canonical_action == "hold_review_needed":
        return "manual_chart_recheck"
    if promotion_readiness == "insufficient_episode_detail" or episode_detail_status != "complete":
        return "fill_episode_coordinates"
    if promotion_readiness == "hold_current_rich_only":
        return "raise_confidence_then_recheck"
    if promotion_readiness == "low_calibration_value":
        return "collect_higher_value_current_rich_examples"
    return "manual_review"


def _promotion_decision_reason(
    *,
    promotion_readiness: str,
    blockers: list[str],
    review_decision: str,
    canonical_action: str,
    calibration_value_bucket: str,
    confidence_rank: int,
) -> str:
    if promotion_readiness == "ready":
        if calibration_value_bucket == "high" and confidence_rank >= 3:
            return "ready_high_value_reviewed"
        return "ready_after_gate_checks"
    if canonical_action == "do_not_promote_failed_wait_seed":
        return f"followup_rejected::{review_decision or 'reviewed'}"
    if canonical_action == "hold_review_needed":
        return f"followup_hold::{review_decision or 'needs_recheck'}"
    if blockers:
        return blockers[0]
    return "gate_review_pending"


def load_current_rich_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _trace_lookup(trace_entries: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if trace_entries is None or trace_entries.empty or "episode_id" not in trace_entries.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in trace_entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            lookup[episode_id] = row.to_dict()
    return lookup


def build_manual_current_rich_promotion_gate(
    draft: pd.DataFrame,
    *,
    queue: pd.DataFrame | None = None,
    review_results: pd.DataFrame | None = None,
    review_trace_entries: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source = normalize_manual_wait_teacher_annotation_df(
        draft if draft is not None else pd.DataFrame()
    )
    queue_frame = queue.copy() if queue is not None else pd.DataFrame()
    review_frame = review_results.copy() if review_results is not None else pd.DataFrame()

    if source.empty:
        empty = pd.DataFrame(columns=MANUAL_CURRENT_RICH_PROMOTION_GATE_COLUMNS)
        summary = {
            "promotion_gate_version": MANUAL_CURRENT_RICH_PROMOTION_GATE_VERSION,
            "row_count": 0,
            "promotion_readiness_counts": {},
            "review_priority_tier_counts": {},
            "recommended_next_action_counts": {},
            "ready_for_canonical_count": 0,
        }
        return empty, summary

    queue_lookup = {
        _to_text(row.get("queue_id", ""), ""): row.to_dict()
        for _, row in queue_frame.iterrows()
    }
    review_lookup = {
        _to_text(row.get("episode_id", ""), ""): row.to_dict()
        for _, row in review_frame.iterrows()
    }
    trace_lookup = _trace_lookup(review_trace_entries)

    rows: list[dict[str, Any]] = []
    for _, row in source.iterrows():
        row_dict = row.to_dict()
        queue_id = _episode_to_queue_id(row_dict.get("episode_id", ""))
        queue_row = queue_lookup.get(queue_id, {})
        review_row = review_lookup.get(_to_text(row_dict.get("episode_id", ""), ""), {})
        trace_row = trace_lookup.get(_to_text(row_dict.get("episode_id", ""), ""), {})
        blockers: list[str] = []

        confidence = _to_text(
            row_dict.get("manual_teacher_confidence", "")
            or row_dict.get("manual_wait_teacher_confidence", ""),
            "",
        ).lower()
        confidence_rank = _confidence_rank(confidence)
        row_count = _to_int(queue_row.get("row_count", 0), 0)
        unique_signal_minutes = _to_int(queue_row.get("unique_signal_minutes", 0), 0)
        capture_priority = _to_text(queue_row.get("capture_priority", "unknown"), "unknown").lower()

        calibration_score = 0
        if capture_priority == "high":
            calibration_score += 2
        elif capture_priority == "medium":
            calibration_score += 1
        if row_count >= 200:
            calibration_score += 1
        if unique_signal_minutes >= 3:
            calibration_score += 1
        calibration_value_bucket = "low"
        if calibration_score >= 4:
            calibration_value_bucket = "high"
        elif calibration_score >= 2:
            calibration_value_bucket = "medium"

        episode_detail_status = "complete" if _has_sufficient_episode_detail(row_dict) else "insufficient"
        review_decision = _to_text(review_row.get("review_decision", ""), "")
        canonical_action = _to_text(
            trace_row.get("canonical_decision", "")
            or review_row.get("canonical_action", ""),
            "",
        )
        review_status = _to_text(row_dict.get("review_status", ""), "").lower()
        promotion_reviewer = _to_text(
            trace_row.get("promotion_reviewer", "")
            or review_row.get("promotion_reviewer", "")
            or review_row.get("review_reviewer", "")
            or review_row.get("review_owner", ""),
            "",
        )
        promotion_reviewed_at = _to_text(
            trace_row.get("promotion_reviewed_at", "")
            or review_row.get("promotion_reviewed_at", "")
            or review_row.get("reviewed_at", "")
            or review_row.get("updated_at", ""),
            "",
        )

        if canonical_action == "do_not_promote_failed_wait_seed":
            blockers.append("followup_review_rejected")
            promotion_readiness = "do_not_promote"
            recommended_next_action = "keep_as_control_only"
            promotion_recommendation = "keep_in_current_rich_draft"
        elif canonical_action == "hold_review_needed":
            blockers.append("followup_review_needs_chart_recheck")
            promotion_readiness = "review_needed"
            recommended_next_action = "manual_recheck_then_decide"
            promotion_recommendation = "keep_in_current_rich_draft"
        elif review_status in {"needs_manual_recheck", "review_needed", "pending"}:
            blockers.append("manual_review_pending")
            promotion_readiness = "review_needed"
            recommended_next_action = "manual_recheck_then_decide"
            promotion_recommendation = "keep_in_current_rich_draft"
        elif confidence_rank < 2:
            blockers.append("confidence_below_medium")
            promotion_readiness = "hold_current_rich_only"
            recommended_next_action = "raise_confidence_then_decide"
            promotion_recommendation = "keep_in_current_rich_draft"
        elif episode_detail_status != "complete":
            blockers.append("episode_detail_incomplete")
            promotion_readiness = "insufficient_episode_detail"
            recommended_next_action = "fill_episode_coordinates"
            promotion_recommendation = "keep_in_current_rich_draft"
        elif calibration_value_bucket == "low":
            blockers.append("low_calibration_value")
            promotion_readiness = "low_calibration_value"
            recommended_next_action = "collect_better_current_rich_examples"
            promotion_recommendation = "keep_in_current_rich_draft"
        else:
            promotion_readiness = "ready"
            recommended_next_action = "promote_to_canonical"
            promotion_recommendation = "promote_to_canonical"

        promotion_score = (
            confidence_rank
            + (2 if episode_detail_status == "complete" else 0)
            + {"high": 3, "medium": 2, "low": 1}.get(calibration_value_bucket, 1)
        )
        review_priority_tier = _review_priority_tier(
            promotion_readiness=promotion_readiness,
            calibration_value_bucket=calibration_value_bucket,
            capture_priority=capture_priority,
            confidence_rank=confidence_rank,
            episode_detail_status=episode_detail_status,
            canonical_action=canonical_action,
        )
        promotion_followup_needed = _promotion_followup_needed(
            promotion_readiness=promotion_readiness,
            canonical_action=canonical_action,
            episode_detail_status=episode_detail_status,
        )
        promotion_decision_reason = _promotion_decision_reason(
            promotion_readiness=promotion_readiness,
            blockers=blockers,
            review_decision=review_decision,
            canonical_action=canonical_action,
            calibration_value_bucket=calibration_value_bucket,
            confidence_rank=confidence_rank,
        )
        if _to_text(trace_row.get("promotion_decision_reason", ""), ""):
            promotion_decision_reason = _to_text(trace_row.get("promotion_decision_reason", ""), "")
        if _to_text(trace_row.get("promotion_blocking_reason", ""), ""):
            blockers = [_to_text(trace_row.get("promotion_blocking_reason", ""), "")]
        promotion_blocking_reason = blockers[0] if blockers else ""
        if _to_text(trace_row.get("promotion_followup_needed", ""), ""):
            promotion_followup_needed = _to_text(trace_row.get("promotion_followup_needed", ""), "")
        rows.append(
            {
                "gate_id": f"current_rich_promotion::{_to_text(row_dict.get('episode_id', ''), '')}",
                "episode_id": _to_text(row_dict.get("episode_id", ""), ""),
                "queue_id": queue_id,
                "symbol": _to_text(row_dict.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(row_dict.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(row_dict.get("manual_wait_teacher_label", ""), "").lower(),
                "manual_teacher_confidence": confidence,
                "review_status": _to_text(row_dict.get("review_status", ""), "").lower(),
                "capture_priority": capture_priority,
                "row_count": row_count,
                "unique_signal_minutes": unique_signal_minutes,
                "review_decision": review_decision,
                "canonical_action": canonical_action,
                "calibration_value_bucket": calibration_value_bucket,
                "episode_detail_status": episode_detail_status,
                "promotion_readiness": promotion_readiness,
                "promotion_score": promotion_score,
                "review_priority_tier": review_priority_tier,
                "promotion_decision_reason": promotion_decision_reason,
                "promotion_reviewer": promotion_reviewer,
                "promotion_reviewed_at": promotion_reviewed_at,
                "promotion_blockers": "|".join(blockers),
                "promotion_blocking_reason": promotion_blocking_reason,
                "promotion_followup_needed": promotion_followup_needed,
                "recommended_next_action": recommended_next_action,
                "canonical_promotion_recommendation": promotion_recommendation,
            }
        )

    gate = pd.DataFrame(rows)
    if not gate.empty:
        gate["priority_rank"] = gate["review_priority_tier"].map(
            {
                "ready_high": 0,
                "ready_normal": 1,
                "review_needed_high_priority": 2,
                "review_needed_normal": 3,
                "review_needed_low_signal": 4,
                "control_only": 5,
            }
        ).fillna(6)
        gate["capture_priority_rank"] = gate["capture_priority"].map(
            {
                "high": 0,
                "medium": 1,
                "low": 2,
                "unknown": 3,
            }
        ).fillna(4)
        gate = gate.sort_values(
            by=["priority_rank", "promotion_score", "capture_priority_rank", "symbol", "anchor_time"],
            ascending=[True, False, True, True, True],
            kind="stable",
        ).copy()
        gate = gate.drop(columns=["priority_rank", "capture_priority_rank"])

    for column in MANUAL_CURRENT_RICH_PROMOTION_GATE_COLUMNS:
        if column not in gate.columns:
            gate[column] = ""
    gate = gate[MANUAL_CURRENT_RICH_PROMOTION_GATE_COLUMNS].copy()

    summary = {
        "promotion_gate_version": MANUAL_CURRENT_RICH_PROMOTION_GATE_VERSION,
        "row_count": int(len(gate)),
        "promotion_readiness_counts": gate["promotion_readiness"].value_counts(dropna=False).to_dict(),
        "review_priority_tier_counts": gate["review_priority_tier"].value_counts(dropna=False).to_dict(),
        "recommended_next_action_counts": gate["recommended_next_action"].value_counts(dropna=False).to_dict(),
        "ready_for_canonical_count": int(
            gate["promotion_readiness"].fillna("").astype(str).eq("ready").sum()
        ),
    }
    return gate, summary


def render_manual_current_rich_promotion_gate_markdown(
    summary: Mapping[str, Any],
    gate: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Draft Canonical Promotion Gate v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- readiness counts: `{summary.get('promotion_readiness_counts', {})}`",
        f"- review priority tiers: `{summary.get('review_priority_tier_counts', {})}`",
        f"- recommended actions: `{summary.get('recommended_next_action_counts', {})}`",
        f"- ready for canonical: `{summary.get('ready_for_canonical_count', 0)}`",
        "",
        "## Gate Preview",
    ]
    preview = gate.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("anchor_time", "")),
                        _to_text(row.get("manual_wait_teacher_label", "")),
                        _to_text(row.get("promotion_readiness", "")),
                        _to_text(row.get("review_priority_tier", "")),
                        f"score={_to_text(row.get('promotion_score', '0'))}",
                        _to_text(row.get("promotion_decision_reason", "")),
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
