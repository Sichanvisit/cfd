"""Build review-needed manual seed drafts from current-rich heuristic windows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _label_from_queue_row(row: Mapping[str, Any]) -> str:
    barrier_label = _to_text(row.get("barrier_label_top", ""), "").lower()
    family = _to_text(row.get("recommended_family_top", ""), "").lower()
    reason = _to_text(row.get("reason_top", ""), "").lower()

    if barrier_label == "correct_wait":
        if family == "relief_watch":
            return "good_wait_protective_exit"
        return "good_wait_better_entry"
    if barrier_label == "avoided_loss":
        if family == "block_bias" and "barrier" in reason:
            return "bad_wait_missed_move"
        return "neutral_wait_small_value"
    return "neutral_wait_small_value"


def _guess_anchor_side(row: Mapping[str, Any]) -> str:
    reason = _to_text(row.get("reason_top", ""), "").lower()
    if "buy_barrier" in reason:
        return "BUY"
    if "sell_barrier" in reason:
        return "SELL"
    return ""


def _with_kst_suffix(value: object) -> str:
    text = _to_text(value, "")
    if not text:
        return ""
    if text.endswith("+09:00"):
        return text
    return f"{text}+09:00"


def load_queue_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_review_override_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _has_override_value(column: str, value: object) -> bool:
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        # Keep explicit numeric overrides such as prices and revisit flags,
        # but ignore zero placeholders for price-like/manual fields.
        if column in {
            "anchor_price",
            "ideal_entry_price",
            "ideal_exit_price",
        }:
            return float(value) != 0.0
        return True
    return True


def _merge_review_overrides(base: pd.DataFrame, overrides: pd.DataFrame | None) -> pd.DataFrame:
    draft = normalize_manual_wait_teacher_annotation_df(base if base is not None else pd.DataFrame())
    overlay = normalize_manual_wait_teacher_annotation_df(overrides if overrides is not None else pd.DataFrame())
    if draft.empty or overlay.empty or "episode_id" not in overlay.columns:
        return draft

    overlay_lookup = {
        _to_text(row.get("episode_id", ""), ""): row.to_dict()
        for _, row in overlay.iterrows()
        if _to_text(row.get("episode_id", ""), "")
    }
    if not overlay_lookup:
        return draft

    merged_rows: list[dict[str, Any]] = []
    seen_episode_ids: set[str] = set()
    for _, row in draft.iterrows():
        merged = row.to_dict()
        episode_id = _to_text(merged.get("episode_id", ""), "")
        override_row = overlay_lookup.get(episode_id, {})
        for column, value in override_row.items():
            if _has_override_value(column, value):
                merged[column] = value
        merged_rows.append(merged)
        if episode_id:
            seen_episode_ids.add(episode_id)

    for episode_id, override_row in overlay_lookup.items():
        if episode_id in seen_episode_ids:
            continue
        merged_rows.append(override_row)

    return normalize_manual_wait_teacher_annotation_df(pd.DataFrame(merged_rows))


def build_manual_current_rich_seed_draft(
    queue: pd.DataFrame,
    *,
    review_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
    source = queue.copy() if queue is not None else pd.DataFrame()
    if source.empty:
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())

    rows: list[dict[str, Any]] = []
    for _, row in source.iterrows():
        queue_id = _to_text(row.get("queue_id", ""), "")
        symbol = _to_text(row.get("symbol", ""), "").upper()
        window_start = _with_kst_suffix(row.get("window_start", ""))
        window_end = _with_kst_suffix(row.get("window_end", ""))
        label = _label_from_queue_row(row)
        rows.append(
            {
                "annotation_id": queue_id.replace("current_rich::", "manual_seed::"),
                "episode_id": queue_id.replace("current_rich::", "manual_seed::"),
                "symbol": symbol,
                "timeframe": "M1",
                "anchor_side": _guess_anchor_side(row),
                "chart_context": "current_rich_window_seed",
                "box_regime_scope": "current_hint_rich_window",
                "anchor_time": window_start,
                "anchor_price": 0.0,
                "ideal_entry_time": "",
                "ideal_entry_price": 0.0,
                "manual_wait_teacher_label": label,
                "manual_wait_teacher_confidence": "low",
                "ideal_exit_time": "",
                "ideal_exit_price": 0.0,
                "barrier_main_label_hint": _to_text(row.get("barrier_label_top", ""), "").lower(),
                "wait_outcome_reason_summary": _to_text(row.get("reason_top", ""), ""),
                "annotation_note": (
                    f"assistant current-rich seed from {window_start} -> {window_end}; "
                    f"family={_to_text(row.get('recommended_family_top', ''), '')}; "
                    f"wait_decision={_to_text(row.get('wait_decision_top', ''), '')}"
                ),
                "annotation_author": "codex",
                "annotation_created_at": "",
                "annotation_source": "assistant_current_rich_seed",
                "review_status": "needs_manual_recheck",
                "revisit_flag": 1,
                "manual_teacher_confidence": "low",
            }
        )

    draft = normalize_manual_wait_teacher_annotation_df(pd.DataFrame(rows))
    return _merge_review_overrides(draft, review_overrides)
