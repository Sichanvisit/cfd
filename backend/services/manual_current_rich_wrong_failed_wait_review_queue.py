"""Build a focused current-rich review queue for remaining wrong_failed_wait cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_VERSION = "manual_current_rich_wrong_failed_wait_review_queue_v0"

CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "barrier_main_label_hint",
    "wait_outcome_reason_summary",
    "target_followup_pattern",
    "review_priority",
    "priority_score",
    "recommended_action",
    "review_rationale",
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


def _classify_followup_pattern(row: Mapping[str, Any]) -> tuple[str, int, str]:
    symbol = _to_text(row.get("symbol", ""), "").upper()
    manual_label = _to_text(row.get("manual_wait_teacher_label", ""), "").lower()
    barrier_hint = _to_text(row.get("barrier_main_label_hint", ""), "").lower()
    reason_summary = _to_text(row.get("wait_outcome_reason_summary", ""), "").lower()
    annotation_note = _to_text(row.get("annotation_note", ""), "").lower()

    if (
        symbol == "NAS100"
        and manual_label == "bad_wait_missed_move"
        and barrier_hint == "avoided_loss"
        and "wait_soft_helper_block" in annotation_note
    ):
        return (
            "nas_failed_wait_shift_proxy",
            95,
            "nearest current-rich proxy for the NAS rebound-probe false wait pattern",
        )

    if (
        symbol == "BTCUSD"
        and manual_label == "bad_wait_missed_move"
        and "wait_soft_helper_block" in annotation_note
    ):
        return (
            "btc_helper_wait_failed_wait_check",
            100,
            "tests whether helper-wait should remain wait-biased or shift toward failed_wait",
        )

    if (
        symbol == "BTCUSD"
        and manual_label == "good_wait_protective_exit"
        and ("relief_watch" in reason_summary or "relief_watch" in annotation_note)
    ):
        return (
            "btc_helper_wait_control",
            70,
            "control case for a wait/protective interpretation that should likely remain valid",
        )

    if (
        symbol == "NAS100"
        and manual_label == "good_wait_better_entry"
        and barrier_hint == "correct_wait"
    ):
        return (
            "nas_timing_improvement_control",
            60,
            "control case for a clean timing-improvement interpretation",
        )

    return ("out_of_scope", 0, "not directly tied to the remaining wrong_failed_wait patterns")


def _review_priority(score: int) -> str:
    if score >= 95:
        return "p1"
    if score >= 70:
        return "p2"
    if score > 0:
        return "p3"
    return "skip"


def build_current_rich_wrong_failed_wait_review_queue(
    seed_draft: pd.DataFrame,
    wrong_failed_wait_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    seeds = seed_draft.copy() if seed_draft is not None else pd.DataFrame()
    audit = wrong_failed_wait_audit.copy() if wrong_failed_wait_audit is not None else pd.DataFrame()

    if seeds.empty or audit.empty:
        empty = pd.DataFrame(columns=CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_COLUMNS)
        return empty, {
            "queue_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_VERSION,
            "row_count": 0,
            "priority_counts": {},
            "pattern_counts": {},
            "target_symbols": [],
        }

    target_symbols = sorted(
        {
            _to_text(value, "").upper()
            for value in audit["symbol"].tolist()
            if _to_text(value, "")
        }
    )
    if not target_symbols:
        empty = pd.DataFrame(columns=CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_COLUMNS)
        return empty, {
            "queue_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_VERSION,
            "row_count": 0,
            "priority_counts": {},
            "pattern_counts": {},
            "target_symbols": [],
        }

    rows: list[dict[str, Any]] = []
    for _, row in seeds.iterrows():
        symbol = _to_text(row.get("symbol", ""), "").upper()
        if symbol not in target_symbols:
            continue

        pattern, score, rationale = _classify_followup_pattern(row)
        if pattern == "out_of_scope":
            continue

        rows.append(
            {
                "episode_id": _to_text(row.get("episode_id", ""), ""),
                "symbol": symbol,
                "anchor_time": _to_text(row.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(row.get("manual_wait_teacher_label", ""), "").lower(),
                "barrier_main_label_hint": _to_text(row.get("barrier_main_label_hint", ""), "").lower(),
                "wait_outcome_reason_summary": _to_text(row.get("wait_outcome_reason_summary", ""), "").lower(),
                "target_followup_pattern": pattern,
                "review_priority": _review_priority(score),
                "priority_score": score,
                "recommended_action": "manual_recheck_before_failed_wait_rule_shift",
                "review_rationale": rationale,
            }
        )

    queue = pd.DataFrame(rows)
    if not queue.empty:
        queue = queue.sort_values(
            by=["priority_score", "symbol", "anchor_time", "episode_id"],
            ascending=[False, True, True, True],
        ).reset_index(drop=True)
    for column in CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_COLUMNS:
        if column not in queue.columns:
            queue[column] = ""
    queue = queue[CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_COLUMNS].copy()

    summary = {
        "queue_version": CURRENT_RICH_WRONG_FAILED_WAIT_REVIEW_VERSION,
        "row_count": int(len(queue)),
        "priority_counts": queue["review_priority"].value_counts(dropna=False).to_dict() if not queue.empty else {},
        "pattern_counts": queue["target_followup_pattern"].value_counts(dropna=False).to_dict() if not queue.empty else {},
        "target_symbols": target_symbols,
    }
    return queue, summary


def render_current_rich_wrong_failed_wait_review_queue_markdown(
    summary: Mapping[str, Any],
    queue: pd.DataFrame,
) -> str:
    lines = [
        "# Current-Rich Wrong Failed-Wait Review Queue v0",
        "",
        f"- rows: `{summary.get('row_count', 0)}`",
        f"- target symbols: `{summary.get('target_symbols', [])}`",
        f"- priority counts: `{summary.get('priority_counts', {})}`",
        f"- pattern counts: `{summary.get('pattern_counts', {})}`",
        "",
        "## Queue",
    ]
    if queue.empty:
        lines.append("- none")
    else:
        for _, row in queue.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("episode_id", "")),
                        _to_text(row.get("symbol", "")),
                        _to_text(row.get("anchor_time", "")),
                        _to_text(row.get("target_followup_pattern", "")),
                        _to_text(row.get("review_priority", "")),
                    ]
                )
            )
            lines.append(f"  rationale: {_to_text(row.get('review_rationale', ''), '')}")
    return "\n".join(lines) + "\n"
