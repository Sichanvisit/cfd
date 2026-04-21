"""Build review-needed manual seed drafts from shadow manual-overlap queue rows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    manual_wait_teacher_defaults,
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


def _with_kst_suffix(value: object) -> str:
    text = _to_text(value, "")
    if not text:
        return ""
    return text if text.endswith("+09:00") else f"{text}+09:00"


def load_shadow_auto_manual_overlap_queue(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def load_shadow_auto_manual_overlap_review_entries(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(csv_path, low_memory=False)
    return normalize_manual_wait_teacher_annotation_df(frame)


def _merge_review_entries(draft: pd.DataFrame, review_entries: pd.DataFrame | None) -> pd.DataFrame:
    working = draft.copy()
    if working.empty or review_entries is None or review_entries.empty:
        return working

    review_lookup: dict[str, dict[str, object]] = {}
    for _, row in review_entries.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        if episode_id:
            review_lookup[episode_id] = row.to_dict()

    override_text_columns = [
        "anchor_side",
        "scene_id",
        "chart_context",
        "box_regime_scope",
        "ideal_entry_time",
        "manual_wait_teacher_label",
        "manual_wait_teacher_confidence",
        "ideal_exit_time",
        "barrier_main_label_hint",
        "wait_outcome_reason_summary",
        "annotation_note",
        "annotation_author",
        "annotation_created_at",
        "annotation_source",
        "review_status",
        "manual_teacher_confidence",
    ]
    override_numeric_columns = [
        "anchor_price",
        "ideal_entry_price",
        "ideal_exit_price",
        "revisit_flag",
    ]

    for index, row in working.iterrows():
        episode_id = _to_text(row.get("episode_id", ""), "")
        override = review_lookup.get(episode_id)
        if not override:
            continue
        label_override = _to_text(override.get("manual_wait_teacher_label", ""), "").lower()
        for column in override_text_columns:
            if column not in working.columns:
                continue
            override_value = _to_text(override.get(column, ""), "")
            if override_value:
                working.at[index, column] = override_value
        for column in override_numeric_columns:
            if column not in working.columns:
                continue
            value = override.get(column, None)
            try:
                if pd.isna(value):
                    continue
            except TypeError:
                pass
            if value is not None and str(value).strip() != "":
                working.at[index, column] = value
        if label_override:
            for dependent_column in (
                "manual_wait_teacher_polarity",
                "manual_wait_teacher_family",
                "manual_wait_teacher_subtype",
                "manual_wait_teacher_usage_bucket",
            ):
                if dependent_column in working.columns:
                    working.at[index, dependent_column] = ""
            for key, value in manual_wait_teacher_defaults(label_override).items():
                if key in working.columns:
                    working.at[index, key] = value
    return normalize_manual_wait_teacher_annotation_df(working)


def build_shadow_auto_manual_overlap_seed_draft(
    queue: pd.DataFrame | None,
    review_entries: pd.DataFrame | None = None,
) -> pd.DataFrame:
    source = queue.copy() if queue is not None else pd.DataFrame()
    if source.empty:
        return normalize_manual_wait_teacher_annotation_df(pd.DataFrame())

    rows: list[dict[str, object]] = []
    for _, row in source.iterrows():
        queue_id = _to_text(row.get("queue_id", ""), "")
        symbol = _to_text(row.get("symbol", ""), "").upper()
        window_start = _with_kst_suffix(row.get("window_start", ""))
        window_end = _with_kst_suffix(row.get("window_end", ""))
        label_seed = _to_text(row.get("dominant_target_label_seed", ""), "neutral_wait_small_value").lower()
        rows.append(
            {
                "annotation_id": queue_id.replace("shadow_manual_overlap::", "shadow_manual_seed::"),
                "episode_id": queue_id.replace("shadow_manual_overlap::", "shadow_manual_seed::"),
                "symbol": symbol,
                "timeframe": "M1",
                "anchor_side": "",
                "chart_context": "shadow_divergence_manual_overlap",
                "box_regime_scope": "shadow_preview_divergence_window",
                "anchor_time": window_start,
                "anchor_price": 0.0,
                "ideal_entry_time": "",
                "ideal_entry_price": 0.0,
                "manual_wait_teacher_label": label_seed,
                "manual_wait_teacher_confidence": "low",
                "ideal_exit_time": "",
                "ideal_exit_price": 0.0,
                "barrier_main_label_hint": _to_text(row.get("dominant_target_action", ""), "").lower(),
                "wait_outcome_reason_summary": (
                    f"shadow overlap seed profile={_to_text(row.get('selected_sweep_profile_id', ''), '')}; "
                    f"baseline={_to_text(row.get('dominant_baseline_action', ''), '')}; "
                    f"shadow={_to_text(row.get('dominant_shadow_action', ''), '')}; "
                    f"window={window_start}->{window_end}"
                ),
                "annotation_note": "assistant seed for manual-truth overlap needed by shadow bounded gate",
                "annotation_author": "codex",
                "annotation_created_at": "",
                "annotation_source": "assistant_shadow_overlap_seed",
                "review_status": "needs_manual_recheck",
                "revisit_flag": 1,
                "manual_teacher_confidence": "low",
            }
        )
    draft = normalize_manual_wait_teacher_annotation_df(pd.DataFrame(rows))
    return _merge_review_entries(draft, review_entries)
