"""Formalize check/color-style manual supervision into market-family surface labels."""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)
from backend.services.trade_csv_schema import now_kst_dt


CHECK_COLOR_LABEL_FORMALIZATION_CONTRACT_VERSION = "check_color_label_formalization_v1"

CHECK_COLOR_LABEL_FORMALIZATION_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "annotation_id",
    "episode_id",
    "symbol",
    "market_family",
    "anchor_side",
    "anchor_time",
    "scene_id",
    "chart_context",
    "annotation_source",
    "source_group",
    "review_status",
    "supervision_strength",
    "visual_check_family",
    "visual_color_family",
    "visual_label_token",
    "manual_wait_teacher_label",
    "manual_wait_teacher_family",
    "manual_wait_teacher_subtype",
    "barrier_main_label_hint",
    "surface_label_family",
    "surface_label_state",
    "surface_action_bias",
    "continuation_support_label",
    "exit_management_support_label",
    "failure_label",
    "aligned_action_target",
    "aligned_continuation_target",
    "aligned_seed_status",
    "aligned_seed_grade",
    "label_reason",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _slug_text(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z]+", "_", _to_text(value).lower())
    return text.strip("_")


def _series_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    series = frame[column].fillna("").astype(str).str.strip()
    series = series.replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def _json_counts(counts: dict[str, int]) -> str:
    return json.dumps(counts, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _source_group(annotation_source: object) -> str:
    source = _to_text(annotation_source).lower()
    if source == "chart_annotated":
        return "manual_chart"
    if "breakout_chart_inferred" in source:
        return "breakout_chart_seed"
    if "breakout_overlap_seed" in source:
        return "breakout_overlap_seed"
    if "current_rich_seed" in source:
        return "current_rich_seed"
    if "assistant" in source:
        return "assistant_seed"
    return "manual_seed"


def _source_rank(source_group: str) -> int:
    return {
        "manual_chart": 4,
        "breakout_chart_seed": 3,
        "breakout_overlap_seed": 2,
        "current_rich_seed": 1,
        "assistant_seed": 1,
        "manual_seed": 2,
    }.get(source_group, 1)


def _review_rank(review_status: object) -> int:
    status = _to_text(review_status).lower()
    if status in {"accepted_canonical", "accepted_strict", "accepted_coarse", "approved", "canonical"}:
        return 4
    if status in {"accepted", "pending_review", "pending"}:
        return 3
    if status in {"needs_manual_recheck", "draft", "queued"}:
        return 2
    return 1


def _confidence_rank(confidence: object) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(_to_text(confidence).lower(), 1)


def _supervision_strength(
    row: pd.Series,
    *,
    aligned_seed_status: str,
    aligned_seed_grade: str,
) -> str:
    usage_bucket = _to_text(row.get("manual_wait_teacher_usage_bucket")).lower()
    if usage_bucket == "diagnostic":
        return "diagnostic"
    if aligned_seed_status == "promoted_canonical" and aligned_seed_grade in {"strict", "good"}:
        return "strong"
    review_status = _to_text(row.get("review_status")).lower()
    confidence = _to_text(row.get("manual_teacher_confidence") or row.get("manual_wait_teacher_confidence")).lower()
    if review_status in {"accepted_canonical", "accepted_strict", "accepted_coarse", "approved"} and confidence in {
        "high",
        "medium",
    }:
        return "strong"
    return "weak"


def _visual_check_family(row: pd.Series) -> str:
    hint = _to_text(row.get("barrier_main_label_hint")).lower()
    family = _to_text(row.get("manual_wait_teacher_family")).lower()
    if hint == "enter_now":
        return "check_enter_now"
    if hint == "wait_then_enter":
        return "check_wait_then_enter"
    if hint == "exit_protect":
        return "check_exit_protect"
    if hint == "wait_bias":
        return "check_wait_bias"
    if hint == "block_bias":
        return "check_block_bias"
    if hint == "avoided_loss":
        return "check_avoided_loss"
    if family == "protective_exit":
        return "check_exit_protect"
    if family == "failed_wait":
        return "check_release_missed"
    if family == "timing_improvement":
        return "check_better_entry"
    return "check_context_only"


def _visual_color_family(row: pd.Series) -> str:
    hint = _to_text(row.get("barrier_main_label_hint")).lower()
    family = _to_text(row.get("manual_wait_teacher_family")).lower()
    polarity = _to_text(row.get("manual_wait_teacher_polarity")).lower()
    if hint in {"enter_now"}:
        return "green_go"
    if hint in {"wait_then_enter"}:
        return "blue_reclaim"
    if hint in {"exit_protect", "avoided_loss"} or family in {"protective_exit", "reversal_escape"}:
        return "amber_protect"
    if hint in {"wait_bias", "block_bias"} or family == "neutral_wait":
        return "gray_wait"
    if family == "failed_wait" or polarity == "bad":
        return "red_missed"
    if family == "timing_improvement" or polarity == "good":
        return "blue_timing"
    return "gray_context"


def _combined_context(row: pd.Series, *, aligned_action_target: str, aligned_continuation_target: str) -> str:
    parts = [
        row.get("scene_id"),
        row.get("chart_context"),
        row.get("box_regime_scope"),
        row.get("barrier_main_label_hint"),
        row.get("wait_outcome_reason_summary"),
        row.get("annotation_note"),
        row.get("manual_wait_teacher_subtype"),
        aligned_action_target,
        aligned_continuation_target,
    ]
    return " ".join(_to_text(part).lower() for part in parts if _to_text(part))


def _infer_failure_label(row: pd.Series, *, context: str) -> str:
    family = _to_text(row.get("manual_wait_teacher_family")).lower()
    hint = _to_text(row.get("barrier_main_label_hint")).lower()
    if any(token in context for token in ("fail_confirm", "false_break", "upper_break_fail", "lower_break_fail", "fake")):
        return "false_breakout"
    if family == "failed_wait" and any(token in context for token in ("pullback", "reclaim", "resume", "continuation")):
        return "failed_follow_through"
    if family == "failed_wait" and any(token in context for token in ("late", "extension", "chase")):
        return "late_entry_chase_fail"
    if family == "protective_exit" and any(token in context for token in ("runner", "regret", "too_early")):
        return "early_exit_regret"
    if family == "failed_wait" or hint == "enter_now":
        return "missed_good_wait_release"
    return ""


def _infer_surface_label(
    row: pd.Series,
    *,
    aligned_action_target: str,
    aligned_continuation_target: str,
) -> tuple[str, str, str, str]:
    family = _to_text(row.get("manual_wait_teacher_family")).lower()
    hint = _to_text(row.get("barrier_main_label_hint")).lower()
    context = _combined_context(
        row,
        aligned_action_target=aligned_action_target,
        aligned_continuation_target=aligned_continuation_target,
    )
    failure_label = _infer_failure_label(row, context=context)

    is_protect = family in {"protective_exit", "reversal_escape"} or hint in {"exit_protect", "avoided_loss"}
    is_runner = any(token in context for token in ("runner", "hold_runner", "partial_then_hold", "continuation_hold"))
    is_pullback = aligned_continuation_target == "PULLBACK_THEN_CONTINUE" or any(
        token in context for token in ("pullback", "reclaim", "resume", "retest", "wait_then_enter")
    )
    is_initial = aligned_action_target == "ENTER_NOW" or any(
        token in context for token in ("breakout", "release", "launch", "open_box", "enter_now")
    )

    if is_protect:
        state = "reversal_escape" if family == "reversal_escape" else "protect_exit"
        return "protective_exit_surface", state, "EXIT_PROTECT", failure_label

    if is_runner:
        action_bias = "HOLD_RUNNER"
        if failure_label == "early_exit_regret":
            action_bias = "PARTIAL_THEN_HOLD"
        return "continuation_hold_surface", "runner_hold", action_bias, failure_label

    if is_pullback:
        action_bias = "WATCH"
        if family == "failed_wait" or hint == "wait_then_enter":
            action_bias = "PROBE_ENTRY"
        if aligned_action_target == "ENTER_NOW":
            action_bias = "ENTER_NOW"
        return "follow_through_surface", "pullback_resume", action_bias, failure_label

    if is_initial:
        action_bias = "WAIT_MORE"
        if family == "failed_wait" or hint == "enter_now" or aligned_action_target == "ENTER_NOW":
            action_bias = "ENTER_NOW"
        elif family == "timing_improvement":
            action_bias = "PROBE_ENTRY"
        return "initial_entry_surface", "initial_break", action_bias, failure_label

    if family == "neutral_wait":
        return "initial_entry_surface", "observe_filter", "WAIT_MORE", failure_label
    if family == "timing_improvement":
        return "initial_entry_surface", "timing_better_entry", "PROBE_ENTRY", failure_label
    if family == "failed_wait":
        return "initial_entry_surface", "late_release", "ENTER_NOW", failure_label or "missed_good_wait_release"
    return "initial_entry_surface", "observe_filter", "WAIT_MORE", failure_label


def _label_reason(
    row: pd.Series,
    *,
    aligned_action_target: str,
    aligned_continuation_target: str,
    surface_label_family: str,
    surface_label_state: str,
) -> str:
    tokens = [
        _to_text(row.get("manual_wait_teacher_family")),
        _to_text(row.get("barrier_main_label_hint")),
        _to_text(aligned_action_target),
        _to_text(aligned_continuation_target),
        surface_label_family,
        surface_label_state,
    ]
    parts = [token for token in tokens if token]
    return " | ".join(parts)


def _prepare_label_source(frame: pd.DataFrame | None) -> pd.DataFrame:
    normalized = normalize_manual_wait_teacher_annotation_df(frame)
    if normalized.empty:
        return normalized
    out = normalized.copy()
    out["source_group"] = out["annotation_source"].apply(_source_group)
    out["__label_key"] = out["episode_id"].replace("", pd.NA).fillna(out["annotation_id"])
    out["__review_rank"] = out["review_status"].apply(_review_rank)
    out["__confidence_rank"] = (
        out["manual_teacher_confidence"].replace("", pd.NA).fillna(out["manual_wait_teacher_confidence"]).apply(_confidence_rank)
    )
    out["__source_rank"] = out["source_group"].apply(_source_rank)
    out["__quality_rank"] = out["__review_rank"] * 100 + out["__confidence_rank"] * 10 + out["__source_rank"]
    return out


def _join_aligned_seed(frame: pd.DataFrame, aligned_seed: pd.DataFrame | None) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    if aligned_seed is None or aligned_seed.empty:
        out = frame.copy()
        out["aligned_action_target"] = ""
        out["aligned_continuation_target"] = ""
        out["aligned_seed_status"] = ""
        out["aligned_seed_grade"] = ""
        return out

    aligned = aligned_seed.copy()
    rename_map = {
        "action_target": "aligned_action_target",
        "continuation_target": "aligned_continuation_target",
        "seed_status": "aligned_seed_status",
        "seed_grade": "aligned_seed_grade",
    }
    aligned = aligned.rename(columns=rename_map)
    keep_columns = [
        "episode_id",
        "symbol",
        "aligned_action_target",
        "aligned_continuation_target",
        "aligned_seed_status",
        "aligned_seed_grade",
    ]
    for column in keep_columns:
        if column not in aligned.columns:
            aligned[column] = ""
    aligned = aligned[keep_columns].copy()
    aligned = aligned.sort_values(["episode_id", "symbol"]).drop_duplicates(["episode_id", "symbol"], keep="first")
    return frame.merge(aligned, on=["episode_id", "symbol"], how="left")


def build_check_color_label_formalization(
    manual_wait_teacher_annotations: pd.DataFrame | None,
    breakout_manual_overlap_seed_draft: pd.DataFrame | None,
    breakout_manual_overlap_seed_review_entries: pd.DataFrame | None,
    manual_current_rich_seed_draft: pd.DataFrame | None,
    breakout_aligned_training_seed: pd.DataFrame | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()

    source_frames = [
        _prepare_label_source(manual_wait_teacher_annotations),
        _prepare_label_source(breakout_manual_overlap_seed_draft),
        _prepare_label_source(breakout_manual_overlap_seed_review_entries),
        _prepare_label_source(manual_current_rich_seed_draft),
    ]
    combined = pd.concat([frame for frame in source_frames if frame is not None and not frame.empty], ignore_index=True)
    if combined.empty:
        summary = {
            "contract_version": CHECK_COLOR_LABEL_FORMALIZATION_CONTRACT_VERSION,
            "generated_at": generated_at,
            "row_count": 0,
            "market_family_counts": "{}",
            "surface_label_family_counts": "{}",
            "surface_label_state_counts": "{}",
            "failure_label_counts": "{}",
            "supervision_strength_counts": "{}",
            "visual_check_family_counts": "{}",
            "visual_color_family_counts": "{}",
            "source_group_counts": "{}",
            "recommended_next_action": "collect_manual_check_color_labels",
        }
        return pd.DataFrame(columns=CHECK_COLOR_LABEL_FORMALIZATION_COLUMNS), summary

    combined = combined.sort_values(
        ["__label_key", "__quality_rank", "annotation_created_at"],
        ascending=[True, False, False],
    ).drop_duplicates("__label_key", keep="first")
    combined = _join_aligned_seed(combined, breakout_aligned_training_seed)

    rows: list[dict[str, Any]] = []
    for _, row in combined.iterrows():
        aligned_action_target = _to_text(row.get("aligned_action_target")).upper()
        aligned_continuation_target = _to_text(row.get("aligned_continuation_target")).upper()
        aligned_seed_status = _to_text(row.get("aligned_seed_status"))
        aligned_seed_grade = _to_text(row.get("aligned_seed_grade")).lower()
        surface_label_family, surface_label_state, surface_action_bias, failure_label = _infer_surface_label(
            row,
            aligned_action_target=aligned_action_target,
            aligned_continuation_target=aligned_continuation_target,
        )
        visual_check_family = _visual_check_family(row)
        visual_color_family = _visual_color_family(row)
        supervision_strength = _supervision_strength(
            row,
            aligned_seed_status=aligned_seed_status,
            aligned_seed_grade=aligned_seed_grade,
        )
        observation_event_id = (
            f"{CHECK_COLOR_LABEL_FORMALIZATION_CONTRACT_VERSION}:{_slug_text(row.get('episode_id') or row.get('annotation_id'))}"
        )
        rows.append(
            {
                "observation_event_id": observation_event_id,
                "generated_at": generated_at,
                "annotation_id": _to_text(row.get("annotation_id")),
                "episode_id": _to_text(row.get("episode_id") or row.get("annotation_id")),
                "symbol": _to_text(row.get("symbol")),
                "market_family": _to_text(row.get("symbol")),
                "anchor_side": _to_text(row.get("anchor_side")).upper(),
                "anchor_time": _to_text(row.get("anchor_time")),
                "scene_id": _to_text(row.get("scene_id")),
                "chart_context": _to_text(row.get("chart_context")),
                "annotation_source": _to_text(row.get("annotation_source")),
                "source_group": _to_text(row.get("source_group")),
                "review_status": _to_text(row.get("review_status")),
                "supervision_strength": supervision_strength,
                "visual_check_family": visual_check_family,
                "visual_color_family": visual_color_family,
                "visual_label_token": f"{visual_color_family}:{visual_check_family}",
                "manual_wait_teacher_label": _to_text(row.get("manual_wait_teacher_label")),
                "manual_wait_teacher_family": _to_text(row.get("manual_wait_teacher_family")),
                "manual_wait_teacher_subtype": _to_text(row.get("manual_wait_teacher_subtype")),
                "barrier_main_label_hint": _to_text(row.get("barrier_main_label_hint")),
                "surface_label_family": surface_label_family,
                "surface_label_state": surface_label_state,
                "surface_action_bias": surface_action_bias,
                "continuation_support_label": aligned_continuation_target,
                "exit_management_support_label": "EXIT_PROTECT"
                if surface_label_family == "protective_exit_surface"
                else "",
                "failure_label": failure_label,
                "aligned_action_target": aligned_action_target,
                "aligned_continuation_target": aligned_continuation_target,
                "aligned_seed_status": aligned_seed_status,
                "aligned_seed_grade": aligned_seed_grade,
                "label_reason": _label_reason(
                    row,
                    aligned_action_target=aligned_action_target,
                    aligned_continuation_target=aligned_continuation_target,
                    surface_label_family=surface_label_family,
                    surface_label_state=surface_label_state,
                ),
            }
        )

    frame = pd.DataFrame(rows, columns=CHECK_COLOR_LABEL_FORMALIZATION_COLUMNS)
    summary = {
        "contract_version": CHECK_COLOR_LABEL_FORMALIZATION_CONTRACT_VERSION,
        "generated_at": generated_at,
        "row_count": int(len(frame)),
        "market_family_counts": _json_counts(_series_counts(frame, "market_family")),
        "surface_label_family_counts": _json_counts(_series_counts(frame, "surface_label_family")),
        "surface_label_state_counts": _json_counts(_series_counts(frame, "surface_label_state")),
        "failure_label_counts": _json_counts(_series_counts(frame, "failure_label")),
        "supervision_strength_counts": _json_counts(_series_counts(frame, "supervision_strength")),
        "visual_check_family_counts": _json_counts(_series_counts(frame, "visual_check_family")),
        "visual_color_family_counts": _json_counts(_series_counts(frame, "visual_color_family")),
        "source_group_counts": _json_counts(_series_counts(frame, "source_group")),
        "recommended_next_action": "implement_mf4_time_axis_contract",
    }
    return frame, summary


def render_check_color_label_formalization_markdown(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Check / Color Label Formalization",
        "",
        f"- generated_at: `{_to_text(summary.get('generated_at'))}`",
        f"- row_count: `{int(summary.get('row_count', 0) or 0)}`",
        f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`",
        f"- market_family_counts: `{_to_text(summary.get('market_family_counts'), '{}')}`",
        f"- surface_label_family_counts: `{_to_text(summary.get('surface_label_family_counts'), '{}')}`",
        f"- surface_label_state_counts: `{_to_text(summary.get('surface_label_state_counts'), '{}')}`",
        f"- failure_label_counts: `{_to_text(summary.get('failure_label_counts'), '{}')}`",
        "",
        "## Preview",
        "",
    ]

    if frame.empty:
        lines.append("- no rows")
        return "\n".join(lines)

    preview_columns = [
        "symbol",
        "source_group",
        "supervision_strength",
        "visual_label_token",
        "surface_label_family",
        "surface_label_state",
        "surface_action_bias",
        "failure_label",
    ]
    preview = frame.loc[:, preview_columns].head(12)
    header = "| " + " | ".join(preview_columns) + " |"
    divider = "| " + " | ".join(["---"] * len(preview_columns)) + " |"
    lines.append(header)
    lines.append(divider)
    for _, row in preview.iterrows():
        values = [_to_text(row.get(column)).replace("|", "/") for column in preview_columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
