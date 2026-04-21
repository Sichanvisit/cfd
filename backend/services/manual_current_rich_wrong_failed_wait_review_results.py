"""Review current-rich wrong-failed-wait follow-up candidates against current entry decisions."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_VERSION = (
    "manual_current_rich_wrong_failed_wait_review_results_v0"
)

CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "target_followup_pattern",
    "review_priority",
    "sampled_row_count",
    "top_barrier_family",
    "top_supporting_label",
    "top_reason_summary",
    "top_wait_decision",
    "top_observe_reason",
    "top_blocked_by",
    "top_core_reason",
    "top_action",
    "review_decision",
    "canonical_action",
    "review_comment",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _top_value(values: pd.Series) -> str:
    cleaned = [str(v).strip() for v in values.fillna("") if str(v).strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def _review_decision(
    pattern: str,
    top_family: str,
    top_label: str,
    top_wait_decision: str,
    top_action: str,
) -> tuple[str, str, str]:
    family = top_family.lower()
    label = top_label.lower()
    wait_decision = top_wait_decision.lower()
    action = top_action.upper()

    if pattern == "btc_helper_wait_failed_wait_check":
        if label == "correct_wait" and family in {"relief_watch", "wait_bias"} and wait_decision == "wait_soft_helper_block":
            return (
                "keep_wait_bias",
                "do_not_promote_failed_wait_seed",
                "current helper-wait window still behaves like a valid wait/protective interpretation",
            )
    if pattern == "nas_failed_wait_shift_proxy":
        if label == "correct_wait" and family in {"relief_watch", "wait_bias"}:
            return (
                "do_not_shift_failed_wait",
                "do_not_promote_failed_wait_seed",
                "nearest current NAS proxy still supports correct_wait / wait-bias rather than failed_wait",
            )
    if pattern == "btc_helper_wait_control":
        return (
            "control_confirms_wait_bias",
            "keep_as_control_only",
            "control case supports the existing wait/protective interpretation",
        )
    if pattern == "nas_timing_improvement_control":
        return (
            "control_confirms_timing_improvement",
            "keep_as_control_only",
            "control case supports a clean timing-improvement interpretation",
        )
    if label == "correct_wait" and family in {"relief_watch", "wait_bias"} and action in {"SELL", ""}:
        return (
            "keep_wait_bias",
            "do_not_promote_failed_wait_seed",
            "current raw evidence is still dominated by correct_wait semantics",
        )
    return (
        "needs_manual_chart_recheck",
        "hold_review_needed",
        "raw evidence mixed; keep out of canonical until manually rechecked",
    )


def build_current_rich_wrong_failed_wait_review_results(
    review_queue: pd.DataFrame,
    entry_decisions: pd.DataFrame,
    window_minutes: int = 30,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    queue = review_queue.copy() if review_queue is not None else pd.DataFrame()
    decisions = entry_decisions.copy() if entry_decisions is not None else pd.DataFrame()

    if queue.empty or decisions.empty:
        empty = pd.DataFrame(columns=CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_COLUMNS)
        return empty, {
            "review_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_VERSION,
            "row_count": 0,
            "decision_counts": {},
            "canonical_action_counts": {},
        }

    if "time" not in decisions.columns:
        empty = pd.DataFrame(columns=CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_COLUMNS)
        return empty, {
            "review_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_VERSION,
            "row_count": 0,
            "decision_counts": {},
            "canonical_action_counts": {},
        }

    decisions = decisions.copy()
    decisions["time"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.dropna(subset=["time"]).copy()

    rows: list[dict[str, Any]] = []
    for _, queue_row in queue.iterrows():
        anchor_text = _to_text(queue_row.get("anchor_time", ""), "")
        if not anchor_text:
            continue

        anchor_time = pd.to_datetime(anchor_text, errors="coerce", utc=False)
        if pd.isna(anchor_time):
            continue
        # compare on naive local timestamps because entry_decisions.csv stores local naive timestamps
        anchor_naive = pd.Timestamp(anchor_time).tz_localize(None) if getattr(anchor_time, "tzinfo", None) else pd.Timestamp(anchor_time)
        window_end = anchor_naive + pd.Timedelta(minutes=window_minutes)
        symbol = _to_text(queue_row.get("symbol", ""), "").upper()
        pattern = _to_text(queue_row.get("target_followup_pattern", ""), "")
        subset = decisions[
            (decisions["symbol"].fillna("").astype(str).str.upper() == symbol)
            & (decisions["time"] >= anchor_naive)
            & (decisions["time"] < window_end)
        ].copy()

        top_family = _top_value(subset.get("barrier_candidate_recommended_family", pd.Series(dtype=object)))
        top_label = _top_value(subset.get("barrier_candidate_supporting_label", pd.Series(dtype=object)))
        top_reason = _top_value(subset.get("barrier_action_hint_reason_summary", pd.Series(dtype=object)))
        top_wait_decision = _top_value(subset.get("entry_wait_decision", pd.Series(dtype=object)))
        top_observe_reason = _top_value(subset.get("observe_reason", pd.Series(dtype=object)))
        top_blocked_by = _top_value(subset.get("blocked_by", pd.Series(dtype=object)))
        top_core_reason = _top_value(subset.get("core_reason", pd.Series(dtype=object)))
        top_action = _top_value(subset.get("action", pd.Series(dtype=object)))

        decision, canonical_action, comment = _review_decision(
            pattern,
            top_family,
            top_label,
            top_wait_decision,
            top_action,
        )

        rows.append(
            {
                "episode_id": _to_text(queue_row.get("episode_id", ""), ""),
                "symbol": symbol,
                "anchor_time": anchor_text,
                "target_followup_pattern": pattern,
                "review_priority": _to_text(queue_row.get("review_priority", ""), ""),
                "sampled_row_count": int(len(subset)),
                "top_barrier_family": top_family.lower(),
                "top_supporting_label": top_label.lower(),
                "top_reason_summary": top_reason.lower(),
                "top_wait_decision": top_wait_decision.lower(),
                "top_observe_reason": top_observe_reason.lower(),
                "top_blocked_by": top_blocked_by.lower(),
                "top_core_reason": top_core_reason.lower(),
                "top_action": top_action.upper(),
                "review_decision": decision,
                "canonical_action": canonical_action,
                "review_comment": comment,
            }
        )

    review = pd.DataFrame(rows)
    if not review.empty:
        review = review.sort_values(
            by=["review_priority", "symbol", "anchor_time", "episode_id"],
            ascending=[True, True, True, True],
        ).reset_index(drop=True)
    for column in CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_COLUMNS:
        if column not in review.columns:
            review[column] = ""
    review = review[CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_COLUMNS].copy()

    summary = {
        "review_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_RESULTS_VERSION,
        "row_count": int(len(review)),
        "decision_counts": review["review_decision"].value_counts(dropna=False).to_dict() if not review.empty else {},
        "canonical_action_counts": review["canonical_action"].value_counts(dropna=False).to_dict() if not review.empty else {},
    }
    return review, summary


def render_current_rich_wrong_failed_wait_review_results_markdown(
    summary: Mapping[str, Any],
    review: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Wrong Failed-Wait Review Results v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- review decisions: `{summary.get('decision_counts', {})}`",
        f"- canonical actions: `{summary.get('canonical_action_counts', {})}`",
        "",
        "## Reviewed Cases",
    ]
    if review.empty:
        lines.append("- none")
    else:
        for _, row in review.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("episode_id", "")),
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("target_followup_pattern", "")),
                        _to_text(row.get("review_decision", "")),
                        _to_text(row.get("canonical_action", "")),
                    ]
                )
            )
            lines.append(f"  comment: {_to_text(row.get('review_comment', ''), '')}")
    return "\n".join(lines) + "\n"
