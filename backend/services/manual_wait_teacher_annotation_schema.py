"""Schema and normalization helpers for episode-centric manual wait-teacher annotations."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


MANUAL_WAIT_TEACHER_LABEL_VERSION = "manual_wait_teacher_v1"

MANUAL_WAIT_TEACHER_LABEL_MAP: dict[str, dict[str, str]] = {
    "good_wait_better_entry": {
        "manual_wait_teacher_polarity": "good",
        "manual_wait_teacher_family": "timing_improvement",
        "manual_wait_teacher_subtype": "better_entry_after_wait",
        "manual_wait_teacher_usage_bucket": "usable",
    },
    "good_wait_protective_exit": {
        "manual_wait_teacher_polarity": "good",
        "manual_wait_teacher_family": "protective_exit",
        "manual_wait_teacher_subtype": "profitable_wait_then_exit",
        "manual_wait_teacher_usage_bucket": "usable",
    },
    "good_wait_reversal_escape": {
        "manual_wait_teacher_polarity": "good",
        "manual_wait_teacher_family": "reversal_escape",
        "manual_wait_teacher_subtype": "wait_then_escape_on_reversal",
        "manual_wait_teacher_usage_bucket": "usable",
    },
    "neutral_wait_small_value": {
        "manual_wait_teacher_polarity": "neutral",
        "manual_wait_teacher_family": "neutral_wait",
        "manual_wait_teacher_subtype": "small_value_wait",
        "manual_wait_teacher_usage_bucket": "diagnostic",
    },
    "bad_wait_missed_move": {
        "manual_wait_teacher_polarity": "bad",
        "manual_wait_teacher_family": "failed_wait",
        "manual_wait_teacher_subtype": "wait_but_missed_move",
        "manual_wait_teacher_usage_bucket": "usable",
    },
    "bad_wait_no_timing_edge": {
        "manual_wait_teacher_polarity": "bad",
        "manual_wait_teacher_family": "failed_wait",
        "manual_wait_teacher_subtype": "wait_without_timing_edge",
        "manual_wait_teacher_usage_bucket": "diagnostic",
    },
}

MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS = [
    "annotation_id",
    "episode_id",
    "symbol",
    "timeframe",
    "anchor_side",
    "scene_id",
    "chart_context",
    "box_regime_scope",
    "anchor_time",
    "anchor_price",
    "ideal_entry_time",
    "ideal_entry_price",
    "manual_entry_teacher_label",
    "manual_entry_teacher_confidence",
    "manual_entry_teacher_note",
    "manual_wait_teacher_label",
    "manual_wait_teacher_polarity",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "manual_wait_teacher_usage_bucket",
    "manual_wait_teacher_confidence",
    "ideal_exit_time",
    "ideal_exit_price",
    "manual_exit_teacher_label",
    "manual_exit_teacher_confidence",
    "manual_exit_teacher_note",
    "barrier_main_label_hint",
    "wait_outcome_reason_summary",
    "annotation_note",
    "annotation_author",
    "annotation_created_at",
    "annotation_source",
    "review_status",
    "revisit_flag",
    "manual_teacher_confidence",
    "label_version",
]

TEXT_MANUAL_WAIT_TEACHER_COLUMNS = {
    "annotation_id",
    "episode_id",
    "symbol",
    "timeframe",
    "anchor_side",
    "scene_id",
    "chart_context",
    "box_regime_scope",
    "anchor_time",
    "ideal_entry_time",
    "manual_entry_teacher_label",
    "manual_entry_teacher_confidence",
    "manual_entry_teacher_note",
    "manual_wait_teacher_label",
    "manual_wait_teacher_polarity",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "manual_wait_teacher_usage_bucket",
    "manual_wait_teacher_confidence",
    "ideal_exit_time",
    "manual_exit_teacher_label",
    "manual_exit_teacher_confidence",
    "manual_exit_teacher_note",
    "barrier_main_label_hint",
    "wait_outcome_reason_summary",
    "annotation_note",
    "annotation_author",
    "annotation_created_at",
    "annotation_source",
    "review_status",
    "manual_teacher_confidence",
    "label_version",
}

ALIAS_COLUMN_MAP = {
    "side": "anchor_side",
    "annotated_entry_time": "ideal_entry_time",
    "annotated_entry_price": "ideal_entry_price",
    "annotated_exit_time": "ideal_exit_time",
    "annotated_exit_price": "ideal_exit_price",
}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _slug_text(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z]+", "_", str(value or "").strip())
    return text.strip("_").lower()


def manual_wait_teacher_defaults(label: str) -> dict[str, str]:
    key = _to_text(label, "").lower()
    return dict(MANUAL_WAIT_TEACHER_LABEL_MAP.get(key, {}))


def _apply_alias_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for source, target in ALIAS_COLUMN_MAP.items():
        if target not in out.columns:
            out[target] = ""
        if source not in out.columns:
            continue
        missing_mask = out[target].fillna("").astype(str).str.strip().eq("")
        out.loc[missing_mask, target] = out.loc[missing_mask, source]
    return out


def _build_fallback_annotation_id(row: pd.Series, index: int) -> str:
    symbol = _slug_text(row.get("symbol", "manual"))
    anchor_time = _slug_text(row.get("anchor_time", "anchor"))
    label = _slug_text(row.get("manual_wait_teacher_label", "wait"))
    return f"manual_wait_{symbol or 'asset'}_{anchor_time or 'anchor'}_{label or 'label'}_{int(index) + 1}"


def normalize_manual_wait_teacher_annotation_df(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(columns=MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS)

    out = _apply_alias_columns(frame.copy())
    for col in MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS:
        if col not in out.columns:
            out[col] = "" if col in TEXT_MANUAL_WAIT_TEACHER_COLUMNS else 0.0

    for col in TEXT_MANUAL_WAIT_TEACHER_COLUMNS:
        out[col] = out[col].fillna("").astype(str).str.strip()

    for numeric_col in ("anchor_price", "ideal_entry_price", "ideal_exit_price"):
        out[numeric_col] = pd.to_numeric(out[numeric_col], errors="coerce").fillna(0.0).astype(float)

    out["revisit_flag"] = pd.to_numeric(out["revisit_flag"], errors="coerce").fillna(0).astype(int)

    out["anchor_side"] = out["anchor_side"].str.upper()
    out["manual_wait_teacher_label"] = out["manual_wait_teacher_label"].str.lower()
    out["manual_wait_teacher_confidence"] = out["manual_wait_teacher_confidence"].str.lower()
    out["manual_entry_teacher_label"] = out["manual_entry_teacher_label"].str.lower()
    out["manual_entry_teacher_confidence"] = out["manual_entry_teacher_confidence"].str.lower()
    out["manual_exit_teacher_label"] = out["manual_exit_teacher_label"].str.lower()
    out["manual_exit_teacher_confidence"] = out["manual_exit_teacher_confidence"].str.lower()
    out["manual_teacher_confidence"] = out["manual_teacher_confidence"].str.lower()
    out["barrier_main_label_hint"] = out["barrier_main_label_hint"].str.lower()
    out["annotation_source"] = out["annotation_source"].replace("", "chart_annotated")
    out["review_status"] = out["review_status"].replace("", "pending")
    out["label_version"] = out["label_version"].replace("", MANUAL_WAIT_TEACHER_LABEL_VERSION)

    for index, row in out.iterrows():
        defaults = manual_wait_teacher_defaults(row.get("manual_wait_teacher_label", ""))
        for key, value in defaults.items():
            if not _to_text(row.get(key, ""), ""):
                out.at[index, key] = value

        annotation_id = _to_text(row.get("annotation_id", ""))
        episode_id = _to_text(row.get("episode_id", ""))
        if not annotation_id and episode_id:
            annotation_id = episode_id
        if not annotation_id:
            annotation_id = _build_fallback_annotation_id(row, index)
        if not episode_id:
            episode_id = annotation_id
        out.at[index, "annotation_id"] = annotation_id
        out.at[index, "episode_id"] = episode_id

        if not _to_text(row.get("manual_teacher_confidence", ""), ""):
            out.at[index, "manual_teacher_confidence"] = _to_text(
                row.get("manual_wait_teacher_confidence", ""),
                "medium",
            ).lower()

    return out[MANUAL_WAIT_TEACHER_ANNOTATION_COLUMNS].copy()
