"""Freshness audit for canonical manual truth and current-rich draft coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


MANUAL_TRUTH_CORPUS_FRESHNESS_VERSION = "manual_truth_corpus_freshness_v0"

MANUAL_TRUTH_CORPUS_FRESHNESS_COLUMNS = [
    "symbol",
    "canonical_row_count",
    "current_rich_draft_row_count",
    "current_rich_queue_count",
    "latest_canonical_anchor_time",
    "latest_current_rich_draft_anchor_time",
    "latest_current_rich_queue_time",
    "latest_current_heuristic_time",
    "canonical_gap_hours_to_current_heuristic",
    "draft_gap_hours_to_current_heuristic",
    "queue_gap_hours_to_current_heuristic",
    "freshness_class",
    "recommended_next_action",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _parse_local_timestamp(value: object) -> pd.Timestamp | pd.NaT:
    text = _to_text(value, "")
    if not text:
        return pd.NaT
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "+" not in text and "T" in text:
        text = f"{text}+09:00"
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return pd.NaT
    if getattr(parsed, "tzinfo", None) is None:
        return parsed.tz_localize("Asia/Seoul")
    return parsed


def load_current_rich_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_current_entry_decisions_frame(path: str | Path) -> pd.DataFrame:
    frame = load_current_rich_frame(path)
    if frame.empty:
        return frame
    if "symbol" not in frame.columns:
        frame["symbol"] = ""
    if "time" not in frame.columns:
        frame["time"] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["heuristic_time"] = frame["time"].apply(_parse_local_timestamp)
    return frame


def _latest_by_symbol(frame: pd.DataFrame, symbol: str, column: str) -> pd.Timestamp | pd.NaT:
    if frame.empty or column not in frame.columns or "symbol" not in frame.columns:
        return pd.NaT
    bucket = frame[frame["symbol"].fillna("").astype(str).str.upper().eq(symbol.upper())].copy()
    if bucket.empty:
        return pd.NaT
    parsed = bucket[column]
    if parsed.empty:
        return pd.NaT
    return parsed.dropna().max() if not parsed.dropna().empty else pd.NaT


def _gap_hours(later: pd.Timestamp | pd.NaT, earlier: pd.Timestamp | pd.NaT) -> float | None:
    if pd.isna(later) or pd.isna(earlier):
        return None
    return round(float((later - earlier).total_seconds() / 3600.0), 3)


def _freshness_class(
    *,
    canonical_gap_hours: float | None,
    draft_gap_hours: float | None,
    draft_count: int,
    queue_count: int,
) -> tuple[str, str]:
    if draft_count > 0 and draft_gap_hours is not None and draft_gap_hours <= 2.0:
        return ("current_rich_ready", "review_current_rich_draft")
    if canonical_gap_hours is not None and canonical_gap_hours <= 12.0:
        return ("canonical_recent", "monitor")
    if queue_count > 0 or draft_count > 0:
        return ("needs_current_rich_review", "review_current_rich_draft")
    return ("stale", "collect_more_manual_truth")


def build_manual_truth_corpus_freshness(
    canonical: pd.DataFrame,
    current_rich_draft: pd.DataFrame,
    current_rich_queue: pd.DataFrame,
    current_entry_decisions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    canonical_frame = normalize_manual_wait_teacher_annotation_df(
        canonical if canonical is not None else pd.DataFrame()
    )
    draft_frame = normalize_manual_wait_teacher_annotation_df(
        current_rich_draft if current_rich_draft is not None else pd.DataFrame()
    )
    queue_frame = current_rich_queue.copy() if current_rich_queue is not None else pd.DataFrame()
    current_frame = current_entry_decisions.copy() if current_entry_decisions is not None else pd.DataFrame()

    canonical_frame["symbol"] = canonical_frame["symbol"].fillna("").astype(str).str.upper()
    canonical_frame["anchor_time_parsed"] = canonical_frame["anchor_time"].apply(_parse_local_timestamp)
    draft_frame["symbol"] = draft_frame["symbol"].fillna("").astype(str).str.upper()
    draft_frame["anchor_time_parsed"] = draft_frame["anchor_time"].apply(_parse_local_timestamp)

    if "window_start" not in queue_frame.columns:
        queue_frame["window_start"] = ""
    if "symbol" not in queue_frame.columns:
        queue_frame["symbol"] = ""
    queue_frame["symbol"] = queue_frame["symbol"].fillna("").astype(str).str.upper()
    queue_frame["window_time_parsed"] = queue_frame["window_start"].apply(_parse_local_timestamp)

    if "symbol" not in current_frame.columns:
        current_frame["symbol"] = ""
    if "heuristic_time" not in current_frame.columns:
        current_frame["heuristic_time"] = pd.Series(dtype="datetime64[ns, Asia/Seoul]")
    current_frame["symbol"] = current_frame["symbol"].fillna("").astype(str).str.upper()

    symbols = sorted(
        set(canonical_frame["symbol"])
        | set(draft_frame["symbol"])
        | set(queue_frame["symbol"])
    )
    symbols = [symbol for symbol in symbols if symbol]

    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        canonical_bucket = canonical_frame[canonical_frame["symbol"].eq(symbol)].copy()
        draft_bucket = draft_frame[draft_frame["symbol"].eq(symbol)].copy()
        queue_bucket = queue_frame[queue_frame["symbol"].eq(symbol)].copy()

        latest_canonical = _latest_by_symbol(canonical_frame, symbol, "anchor_time_parsed")
        latest_draft = _latest_by_symbol(draft_frame, symbol, "anchor_time_parsed")
        latest_queue = _latest_by_symbol(queue_frame, symbol, "window_time_parsed")
        latest_current = _latest_by_symbol(current_frame, symbol, "heuristic_time")

        canonical_gap_hours = _gap_hours(latest_current, latest_canonical)
        draft_gap_hours = _gap_hours(latest_current, latest_draft)
        queue_gap_hours = _gap_hours(latest_current, latest_queue)
        freshness_class, next_action = _freshness_class(
            canonical_gap_hours=canonical_gap_hours,
            draft_gap_hours=draft_gap_hours,
            draft_count=int(len(draft_bucket)),
            queue_count=int(len(queue_bucket)),
        )
        rows.append(
            {
                "symbol": symbol,
                "canonical_row_count": int(len(canonical_bucket)),
                "current_rich_draft_row_count": int(len(draft_bucket)),
                "current_rich_queue_count": int(len(queue_bucket)),
                "latest_canonical_anchor_time": (
                    latest_canonical.isoformat() if not pd.isna(latest_canonical) else ""
                ),
                "latest_current_rich_draft_anchor_time": (
                    latest_draft.isoformat() if not pd.isna(latest_draft) else ""
                ),
                "latest_current_rich_queue_time": (
                    latest_queue.isoformat() if not pd.isna(latest_queue) else ""
                ),
                "latest_current_heuristic_time": (
                    latest_current.isoformat() if not pd.isna(latest_current) else ""
                ),
                "canonical_gap_hours_to_current_heuristic": "" if canonical_gap_hours is None else canonical_gap_hours,
                "draft_gap_hours_to_current_heuristic": "" if draft_gap_hours is None else draft_gap_hours,
                "queue_gap_hours_to_current_heuristic": "" if queue_gap_hours is None else queue_gap_hours,
                "freshness_class": freshness_class,
                "recommended_next_action": next_action,
            }
        )

    freshness = pd.DataFrame(rows)
    for column in MANUAL_TRUTH_CORPUS_FRESHNESS_COLUMNS:
        if column not in freshness.columns:
            freshness[column] = ""
    freshness = freshness[MANUAL_TRUTH_CORPUS_FRESHNESS_COLUMNS].copy()

    summary = {
        "freshness_version": MANUAL_TRUTH_CORPUS_FRESHNESS_VERSION,
        "symbol_count": int(len(freshness)),
        "freshness_class_counts": freshness["freshness_class"].value_counts(dropna=False).to_dict()
        if not freshness.empty
        else {},
        "recommended_next_action_counts": freshness["recommended_next_action"].value_counts(dropna=False).to_dict()
        if not freshness.empty
        else {},
    }
    return freshness, summary


def render_manual_truth_corpus_freshness_markdown(
    summary: Mapping[str, Any],
    freshness: pd.DataFrame,
) -> str:
    lines = [
        "# Manual Truth Corpus Freshness v0",
        "",
        f"- symbols: `{summary.get('symbol_count', 0)}`",
        f"- freshness classes: `{summary.get('freshness_class_counts', {})}`",
        f"- recommended actions: `{summary.get('recommended_next_action_counts', {})}`",
        "",
        "## Symbol Status",
    ]
    preview = freshness.head(10)
    if preview.empty:
        lines.append("- none")
    else:
        for _, row in preview.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("symbol", "")),
                        f"canonical={_to_text(row.get('canonical_row_count', '0'))}",
                        f"draft={_to_text(row.get('current_rich_draft_row_count', '0'))}",
                        _to_text(row.get("freshness_class", "")),
                        _to_text(row.get("recommended_next_action", "")),
                    ]
                )
            )
    return "\n".join(lines) + "\n"
