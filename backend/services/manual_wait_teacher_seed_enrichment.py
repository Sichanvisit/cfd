"""Closed-history enrichment for episode-centric manual wait-teacher truth."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.services.manual_wait_teacher_annotation_schema import (
    normalize_manual_wait_teacher_annotation_df,
)
from backend.services.trade_csv_schema import normalize_trade_df


MANUAL_WAIT_TEACHER_SEED_ENRICHMENT_VERSION = "manual_wait_teacher_seed_enrichment_v1"
DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES = 360
DEFAULT_AMBIGUITY_GAP_SECONDS = 300


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


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


def _safe_seconds_delta(left: pd.Timestamp | None, right: pd.Timestamp | None, *, default: float = 0.0) -> float:
    if left is None or right is None:
        return float(default)
    return float(abs((left - right).total_seconds()))


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


def _build_closed_history_match_index(frame: pd.DataFrame) -> dict[str, Any]:
    by_symbol_side: dict[tuple[str, str], list[int]] = defaultdict(list)
    by_symbol: dict[str, list[int]] = defaultdict(list)
    open_time_map: dict[int, pd.Timestamp | None] = {}
    close_time_map: dict[int, pd.Timestamp | None] = {}

    for index, row in frame.iterrows():
        row_index = int(index)
        symbol = _to_text(row.get("symbol", "")).upper()
        side = _to_text(row.get("direction", "")).upper()
        if symbol:
            by_symbol[symbol].append(row_index)
            if side:
                by_symbol_side[(symbol, side)].append(row_index)
        open_time_map[row_index] = _parse_local_timestamp(row.get("open_time", ""))
        close_time_map[row_index] = _parse_local_timestamp(row.get("close_time", ""))

    return {
        "by_symbol_side": dict(by_symbol_side),
        "by_symbol": dict(by_symbol),
        "open_time_map": open_time_map,
        "close_time_map": close_time_map,
    }


def _annotation_confidence_rank(value: object) -> int:
    text = _to_text(value, "").lower()
    if text == "high":
        return 3
    if text == "medium":
        return 2
    if text in {"low", "weak"}:
        return 1
    return 0


def _annotation_sort_key(annotation: Mapping[str, Any] | None) -> tuple[int, int, str]:
    row = dict(annotation or {})
    wait_label = _to_text(row.get("manual_wait_teacher_label", ""))
    return (
        1 if wait_label else 0,
        _annotation_confidence_rank(row.get("manual_teacher_confidence", row.get("manual_wait_teacher_confidence", ""))),
        _to_text(row.get("annotation_created_at", "")),
    )


def _existing_enrichment_present(row: pd.Series | Mapping[str, Any]) -> bool:
    return bool(
        _to_text(row.get("manual_wait_teacher_label", ""))
        or _to_text(row.get("manual_wait_teacher_family", ""))
        or _to_text(row.get("manual_wait_teacher_episode_id", ""))
    )


def _resolve_closed_row_index_from_annotation(
    annotation_row: Mapping[str, Any] | None,
    *,
    match_index: Mapping[str, Any],
    max_entry_time_gap_minutes: int = DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES,
    ambiguity_gap_seconds: int = DEFAULT_AMBIGUITY_GAP_SECONDS,
) -> tuple[int | None, dict[str, Any]]:
    row = dict(annotation_row or {})
    symbol = _to_text(row.get("symbol", "")).upper()
    side = _to_text(row.get("anchor_side", "")).upper()
    if not symbol:
        return None, {"reason": "symbol_missing"}
    if not side:
        return None, {"reason": "anchor_side_missing"}

    candidate_indices = list((match_index.get("by_symbol_side", {}) or {}).get((symbol, side), []) or [])
    if not candidate_indices:
        symbol_candidates = list((match_index.get("by_symbol", {}) or {}).get(symbol, []) or [])
        reason = "symbol_side_unmatched" if symbol_candidates else "symbol_unmatched"
        return None, {"reason": reason}

    entry_target = _parse_local_timestamp(row.get("ideal_entry_time", ""))
    anchor_target = _parse_local_timestamp(row.get("anchor_time", ""))
    if entry_target is None and anchor_target is None:
        return None, {"reason": "anchor_entry_time_missing"}
    close_target = _parse_local_timestamp(row.get("ideal_exit_time", ""))

    max_gap_seconds = max(int(max_entry_time_gap_minutes), 0) * 60
    scored_candidates: list[dict[str, Any]] = []
    for row_index in candidate_indices:
        open_time = (match_index.get("open_time_map", {}) or {}).get(int(row_index))
        close_time = (match_index.get("close_time_map", {}) or {}).get(int(row_index))
        reference_target = entry_target or anchor_target
        primary_gap_seconds = _safe_seconds_delta(open_time, reference_target, default=float("inf"))
        if primary_gap_seconds > float(max_gap_seconds):
            continue
        close_gap_seconds = _safe_seconds_delta(close_time, close_target, default=0.0)
        anchor_gap_seconds = _safe_seconds_delta(open_time, anchor_target, default=primary_gap_seconds)
        score = primary_gap_seconds + (0.35 * close_gap_seconds)
        scored_candidates.append(
            {
                "row_index": int(row_index),
                "score": float(score),
                "primary_gap_seconds": float(primary_gap_seconds),
                "close_gap_seconds": float(close_gap_seconds),
                "anchor_gap_seconds": float(anchor_gap_seconds),
            }
        )

    if not scored_candidates:
        return None, {"reason": "time_gap_exceeds_limit"}

    scored_candidates.sort(key=lambda item: (item["score"], item["primary_gap_seconds"], item["row_index"]))
    best = dict(scored_candidates[0])
    if len(scored_candidates) > 1:
        runner_up = dict(scored_candidates[1])
        if abs(float(runner_up["score"]) - float(best["score"])) <= float(ambiguity_gap_seconds):
            return None, {
                "reason": "ambiguous_time_match",
                "best_score": float(best["score"]),
                "runner_up_score": float(runner_up["score"]),
            }

    return int(best["row_index"]), {
        "reason": "matched",
        "score": float(best["score"]),
        "primary_gap_seconds": float(best["primary_gap_seconds"]),
        "close_gap_seconds": float(best["close_gap_seconds"]),
        "anchor_gap_seconds": float(best["anchor_gap_seconds"]),
    }


def _build_enrichment_value(annotation_row: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(annotation_row or {})
    wait_label = _to_text(row.get("manual_wait_teacher_label", "")).lower()
    if not wait_label:
        return {column: "" for column in ()}

    return {
        "manual_wait_teacher_label": wait_label,
        "manual_wait_teacher_polarity": _to_text(row.get("manual_wait_teacher_polarity", "")).lower(),
        "manual_wait_teacher_family": _to_text(row.get("manual_wait_teacher_family", "")).lower(),
        "manual_wait_teacher_subtype": _to_text(row.get("manual_wait_teacher_subtype", "")).lower(),
        "manual_wait_teacher_usage_bucket": _to_text(row.get("manual_wait_teacher_usage_bucket", "")).lower(),
        "manual_wait_teacher_confidence": _to_text(row.get("manual_wait_teacher_confidence", "")).lower(),
        "manual_wait_teacher_source": _to_text(row.get("annotation_source", "chart_annotated")).lower(),
        "manual_wait_teacher_review_status": _to_text(row.get("review_status", "pending")).lower(),
        "manual_wait_teacher_episode_id": _to_text(row.get("episode_id", "")),
        "manual_wait_teacher_anchor_time": _to_text(row.get("anchor_time", "")),
        "manual_wait_teacher_anchor_price": _to_float(row.get("anchor_price", 0.0), 0.0),
        "manual_wait_teacher_entry_time": _to_text(row.get("ideal_entry_time", "")),
        "manual_wait_teacher_entry_price": _to_float(row.get("ideal_entry_price", 0.0), 0.0),
        "manual_wait_teacher_exit_time": _to_text(row.get("ideal_exit_time", "")),
        "manual_wait_teacher_exit_price": _to_float(row.get("ideal_exit_price", 0.0), 0.0),
        "manual_wait_teacher_reason": _to_text(row.get("wait_outcome_reason_summary", "")).lower(),
        "manual_wait_teacher_note": _to_text(row.get("annotation_note", "")),
        "manual_wait_teacher_box_regime": _to_text(row.get("box_regime_scope", "")).lower(),
        "manual_wait_teacher_revisit_flag": _to_int(row.get("revisit_flag", 0), 0),
    }


def _group_annotations_by_closed_row(
    annotations: pd.DataFrame,
    *,
    match_index: Mapping[str, Any],
    max_entry_time_gap_minutes: int = DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES,
    ambiguity_gap_seconds: int = DEFAULT_AMBIGUITY_GAP_SECONDS,
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, int], list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    reason_counts: dict[str, int] = defaultdict(int)
    preview_matches: list[dict[str, Any]] = []

    for _, annotation in annotations.iterrows():
        annotation_row = annotation.to_dict()
        wait_label = _to_text(annotation_row.get("manual_wait_teacher_label", ""))
        if not wait_label:
            reason_counts["wait_label_missing"] += 1
            continue
        matched_index, meta = _resolve_closed_row_index_from_annotation(
            annotation_row,
            match_index=match_index,
            max_entry_time_gap_minutes=max_entry_time_gap_minutes,
            ambiguity_gap_seconds=ambiguity_gap_seconds,
        )
        reason = _to_text(meta.get("reason", "unknown"))
        if matched_index is None:
            reason_counts[reason or "unmatched"] += 1
            continue
        grouped[int(matched_index)].append(annotation_row)
        if len(preview_matches) < 10:
            preview_matches.append(
                {
                    "row_index": int(matched_index),
                    "annotation_id": _to_text(annotation_row.get("annotation_id", "")),
                    "episode_id": _to_text(annotation_row.get("episode_id", "")),
                    "symbol": _to_text(annotation_row.get("symbol", "")).upper(),
                    "anchor_side": _to_text(annotation_row.get("anchor_side", "")).upper(),
                    "manual_wait_teacher_label": wait_label.lower(),
                    "primary_gap_seconds": _to_float(meta.get("primary_gap_seconds", 0.0), 0.0),
                    "close_gap_seconds": _to_float(meta.get("close_gap_seconds", 0.0), 0.0),
                }
            )

    return dict(grouped), dict(sorted(reason_counts.items())), preview_matches


def build_manual_wait_teacher_seed_enrichment_plan(
    frame: pd.DataFrame | None,
    *,
    annotations: pd.DataFrame | None = None,
    overwrite_existing: bool = False,
    max_entry_time_gap_minutes: int = DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES,
    ambiguity_gap_seconds: int = DEFAULT_AMBIGUITY_GAP_SECONDS,
) -> dict[str, Any]:
    dataset = normalize_trade_df(frame)
    normalized_annotations = normalize_manual_wait_teacher_annotation_df(annotations)
    match_index = _build_closed_history_match_index(dataset)
    grouped, reason_counts, preview_matches = _group_annotations_by_closed_row(
        normalized_annotations,
        match_index=match_index,
        max_entry_time_gap_minutes=max_entry_time_gap_minutes,
        ambiguity_gap_seconds=ambiguity_gap_seconds,
    )

    label_distribution: dict[str, int] = {}
    family_distribution: dict[str, int] = {}
    box_regime_distribution: dict[str, int] = {}
    existing_enriched_rows = 0
    skipped_existing_rows = 0
    collided_rows = 0
    matched_annotations = int(sum(len(rows) for rows in grouped.values()))
    collided_annotations = 0
    preview_samples: list[dict[str, Any]] = []

    for row_index, annotations_for_row in grouped.items():
        if len(annotations_for_row) > 1:
            collided_rows += 1
            collided_annotations += int(len(annotations_for_row) - 1)
        existing = _existing_enrichment_present(dataset.loc[row_index])
        if existing:
            existing_enriched_rows += 1
            if not overwrite_existing:
                skipped_existing_rows += 1
                continue
        selected = max(annotations_for_row, key=_annotation_sort_key)
        enrichment = _build_enrichment_value(selected)
        if not enrichment:
            continue
        for target, source in (
            (label_distribution, "manual_wait_teacher_label"),
            (family_distribution, "manual_wait_teacher_family"),
            (box_regime_distribution, "manual_wait_teacher_box_regime"),
        ):
            value = _to_text(enrichment.get(source, ""))
            if value:
                target[value] = int(target.get(value, 0)) + 1
        if len(preview_samples) < 10:
            preview_samples.append(
                {
                    "row_index": int(row_index),
                    "ticket": str(dataset.loc[row_index].get("ticket", "") or ""),
                    "symbol": str(dataset.loc[row_index].get("symbol", "") or ""),
                    "episode_id": _to_text(selected.get("episode_id", "")),
                    **enrichment,
                }
            )

    return {
        "contract_version": MANUAL_WAIT_TEACHER_SEED_ENRICHMENT_VERSION,
        "total_closed_rows": int(len(dataset)),
        "annotations_total": int(len(normalized_annotations)),
        "matched_annotations": int(matched_annotations),
        "unmatched_annotations": int(len(normalized_annotations) - matched_annotations),
        "matched_trade_rows": int(len(grouped)),
        "existing_enriched_rows": int(existing_enriched_rows),
        "skipped_existing_rows": int(skipped_existing_rows),
        "collided_rows": int(collided_rows),
        "collided_annotations": int(collided_annotations),
        "overwrite_existing": bool(overwrite_existing),
        "max_entry_time_gap_minutes": int(max_entry_time_gap_minutes),
        "ambiguity_gap_seconds": int(ambiguity_gap_seconds),
        "match_reason_counts": reason_counts,
        "label_distribution": dict(sorted(label_distribution.items())),
        "family_distribution": dict(sorted(family_distribution.items())),
        "box_regime_distribution": dict(sorted(box_regime_distribution.items())),
        "preview_matches": preview_matches,
        "preview_samples": preview_samples,
    }


def apply_manual_wait_teacher_seed_enrichment(
    frame: pd.DataFrame | None,
    *,
    annotations: pd.DataFrame | None = None,
    overwrite_existing: bool = False,
    max_entry_time_gap_minutes: int = DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES,
    ambiguity_gap_seconds: int = DEFAULT_AMBIGUITY_GAP_SECONDS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    normalized_annotations = normalize_manual_wait_teacher_annotation_df(annotations)
    initial_plan = build_manual_wait_teacher_seed_enrichment_plan(
        dataset,
        annotations=normalized_annotations,
        overwrite_existing=overwrite_existing,
        max_entry_time_gap_minutes=max_entry_time_gap_minutes,
        ambiguity_gap_seconds=ambiguity_gap_seconds,
    )
    match_index = _build_closed_history_match_index(dataset)
    grouped, reason_counts, _preview_matches = _group_annotations_by_closed_row(
        normalized_annotations,
        match_index=match_index,
        max_entry_time_gap_minutes=max_entry_time_gap_minutes,
        ambiguity_gap_seconds=ambiguity_gap_seconds,
    )

    updated_rows = 0
    skipped_existing_rows = 0
    skipped_unlabeled_rows = 0
    collided_rows = 0
    collided_annotations = 0
    for row_index, annotations_for_row in grouped.items():
        if len(annotations_for_row) > 1:
            collided_rows += 1
            collided_annotations += int(len(annotations_for_row) - 1)
        if _existing_enrichment_present(dataset.loc[row_index]) and not overwrite_existing:
            skipped_existing_rows += 1
            continue
        selected = max(annotations_for_row, key=_annotation_sort_key)
        enrichment = _build_enrichment_value(selected)
        if not enrichment:
            skipped_unlabeled_rows += 1
            continue
        for column, value in enrichment.items():
            dataset.at[row_index, column] = value
        updated_rows += 1

    report = dict(initial_plan)
    report.update(
        {
            "match_reason_counts": reason_counts,
            "updated_rows": int(updated_rows),
            "skipped_existing_rows": int(skipped_existing_rows),
            "skipped_unlabeled_rows": int(skipped_unlabeled_rows),
            "collided_rows": int(collided_rows),
            "collided_annotations": int(collided_annotations),
        }
    )
    return dataset, report
