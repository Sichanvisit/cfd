"""Bounded teacher-pattern backfill for closed-history compact datasets."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import pandas as pd

from backend.services.teacher_pattern_labeler import build_teacher_pattern_payload_v2
from backend.services.trade_csv_schema import TEACHER_PATTERN_COLUMNS, normalize_trade_df


BACKFILL_LABEL_SOURCE = "rule_v2_backfill"
BACKFILL_LABEL_REVIEW_STATUS = "backfilled_unreviewed"
RELABEL_LABEL_SOURCE = "rule_v2_tuned_relabel"
RELABEL_LABEL_REVIEW_STATUS = "backfilled_unreviewed"


def _truthy_text(value: Any) -> str:
    return str(value or "").strip()


def _is_labeled_row(row: pd.Series | dict[str, Any]) -> bool:
    teacher_pattern_id = pd.to_numeric((row.get("teacher_pattern_id") if isinstance(row, dict) else row.get("teacher_pattern_id")), errors="coerce")
    teacher_pattern_name = _truthy_text(row.get("teacher_pattern_name") if isinstance(row, dict) else row.get("teacher_pattern_name"))
    return bool((not pd.isna(teacher_pattern_id) and int(teacher_pattern_id) > 0) or teacher_pattern_name)


def _scoped_indices(frame: pd.DataFrame, recent_limit: int | None) -> list[int]:
    if recent_limit is None or int(recent_limit) <= 0 or len(frame) <= int(recent_limit):
        return list(frame.index)
    return list(frame.tail(int(recent_limit)).index)


def _payload_to_schema_values(payload: dict[str, Any], *, relabel: bool = False) -> dict[str, Any]:
    values = {column: payload.get(column, "") for column in TEACHER_PATTERN_COLUMNS}
    values["teacher_label_source"] = RELABEL_LABEL_SOURCE if relabel else BACKFILL_LABEL_SOURCE
    values["teacher_label_review_status"] = RELABEL_LABEL_REVIEW_STATUS if relabel else BACKFILL_LABEL_REVIEW_STATUS
    return values


def _build_label_candidate_row(row: pd.Series, *, relabel: bool) -> dict[str, Any]:
    candidate = row.to_dict()
    if relabel:
        for column in TEACHER_PATTERN_COLUMNS:
            candidate[column] = "" if "id" not in column and "lookback" not in column and "confidence" not in column and "score" not in column else 0
        candidate["teacher_pattern_id"] = 0
        candidate["teacher_pattern_secondary_id"] = 0
        candidate["teacher_label_confidence"] = 0.0
        candidate["teacher_lookback_bars"] = 0
        candidate["teacher_primary_score"] = 0.0
        candidate["teacher_secondary_score"] = 0.0
    return candidate


def build_teacher_pattern_backfill_plan(
    frame: pd.DataFrame | None,
    *,
    recent_limit: int = 1000,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    dataset = normalize_trade_df(frame)
    scoped_index = _scoped_indices(dataset, recent_limit)

    already_labeled = 0
    candidates = 0
    relabel_candidates = 0
    predicted_rows = 0
    distribution: dict[int, int] = {}
    preview_samples: list[dict[str, Any]] = []

    for index in scoped_index:
        row = dataset.loc[index]
        labeled = _is_labeled_row(row)
        if labeled:
            already_labeled += 1
            if not overwrite_existing:
                continue
            relabel_candidates += 1
        candidates += 1
        payload = build_teacher_pattern_payload_v2(_build_label_candidate_row(row, relabel=bool(labeled and overwrite_existing)))
        if not payload:
            continue
        predicted_rows += 1
        pattern_id = int(pd.to_numeric(payload.get("teacher_pattern_id"), errors="coerce") or 0)
        if pattern_id > 0:
            distribution[pattern_id] = distribution.get(pattern_id, 0) + 1
        if len(preview_samples) < 10:
            preview_samples.append(
                {
                    "row_index": int(index) if isinstance(index, (int, float)) else str(index),
                    "ticket": str(row.get("ticket", "") or ""),
                    "symbol": str(row.get("symbol", "") or ""),
                    "teacher_pattern_id": pattern_id,
                    "teacher_pattern_secondary_id": int(pd.to_numeric(payload.get("teacher_pattern_secondary_id"), errors="coerce") or 0),
                    "teacher_label_confidence": float(pd.to_numeric(payload.get("teacher_label_confidence"), errors="coerce") or 0.0),
                }
            )

    return {
        "total_rows": int(len(dataset)),
        "scoped_rows": int(len(scoped_index)),
        "recent_limit": int(recent_limit) if recent_limit is not None else None,
        "overwrite_existing": bool(overwrite_existing),
        "already_labeled_rows": int(already_labeled),
        "candidate_rows": int(candidates),
        "relabel_candidates": int(relabel_candidates),
        "predicted_rows": int(predicted_rows),
        "predicted_distribution": {int(key): int(value) for key, value in sorted(distribution.items())},
        "preview_samples": preview_samples,
    }


def apply_teacher_pattern_backfill(
    frame: pd.DataFrame | None,
    *,
    recent_limit: int = 1000,
    overwrite_existing: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataset = normalize_trade_df(frame)
    scoped_index = _scoped_indices(dataset, recent_limit)

    updated_rows = 0
    skipped_labeled_rows = 0
    skipped_unmatched_rows = 0
    relabeled_rows = 0

    for index in scoped_index:
        row = dataset.loc[index]
        labeled = _is_labeled_row(row)
        if labeled and not overwrite_existing:
            skipped_labeled_rows += 1
            continue

        payload = build_teacher_pattern_payload_v2(_build_label_candidate_row(row, relabel=bool(labeled)))
        if not payload:
            skipped_unmatched_rows += 1
            continue

        values = _payload_to_schema_values(payload, relabel=bool(labeled))
        for column, value in values.items():
            dataset.at[index, column] = value
        updated_rows += 1
        if labeled:
            relabeled_rows += 1

    report = build_teacher_pattern_backfill_plan(
        dataset,
        recent_limit=recent_limit,
        overwrite_existing=overwrite_existing,
    )
    report.update(
        {
            "updated_rows": int(updated_rows),
            "relabeled_rows": int(relabeled_rows),
            "skipped_labeled_rows": int(skipped_labeled_rows),
            "skipped_unmatched_rows": int(skipped_unmatched_rows),
        }
    )
    return dataset, report


def read_closed_history_for_backfill(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return normalize_trade_df(pd.DataFrame())
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return normalize_trade_df(pd.read_csv(csv_path, encoding=encoding, low_memory=False))
        except Exception:
            continue
    return normalize_trade_df(pd.read_csv(csv_path, low_memory=False))


def write_closed_history_backfill(
    path: str | Path,
    frame: pd.DataFrame,
    *,
    backup: bool = True,
    backup_suffix: str = "teacher_pattern_backfill",
) -> Path | None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if backup and csv_path.exists():
        backup_path = csv_path.with_name(f"{csv_path.stem}.backup_{backup_suffix}{csv_path.suffix}")
        if backup_path.exists():
            counter = 1
            while True:
                candidate = csv_path.with_name(f"{csv_path.stem}.backup_{backup_suffix}_{counter}{csv_path.suffix}")
                if not candidate.exists():
                    backup_path = candidate
                    break
                counter += 1
        shutil.copy2(csv_path, backup_path)
    normalize_trade_df(frame).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return backup_path
