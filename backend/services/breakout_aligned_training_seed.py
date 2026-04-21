"""Promote replay-aligned breakout manual-learning rows into canonical training seeds."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd


BREAKOUT_ALIGNED_TRAINING_SEED_VERSION = "breakout_aligned_training_seed_v1"
BREAKOUT_ALIGNED_TRAINING_SEED_COLUMNS = [
    "episode_id",
    "symbol",
    "coverage_state",
    "review_status",
    "annotation_source",
    "action_target",
    "continuation_target",
    "matched_job_id",
    "matched_decision_time",
    "time_gap_sec",
    "seed_grade",
    "seed_status",
    "promote_to_training",
    "transition_label_status",
    "management_label_status",
    "transition_hit_rate",
    "management_hit_rate",
    "p_buy_confirm",
    "actual_buy_confirm",
    "p_continuation_success",
    "actual_continuation_success",
    "p_false_break",
    "actual_false_break",
    "p_continue_favor",
    "actual_continue_favor",
    "p_fail_now",
    "actual_fail_now",
    "p_opposite_edge_reach",
    "actual_opposite_edge_reach",
    "reason_summary",
    "recommended_next_step",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _seed_grade(time_gap_sec: float) -> str:
    if time_gap_sec <= 60.0:
        return "strict"
    if time_gap_sec <= 300.0:
        return "good"
    if time_gap_sec <= 900.0:
        return "coarse_review"
    return "loose_review"


def _seed_status(seed_grade: str, match_status: str) -> tuple[str, bool]:
    if match_status != "matched":
        return "skip_unmatched", False
    if seed_grade in {"strict", "good"}:
        return "promoted_canonical", True
    if seed_grade == "coarse_review":
        return "review_coarse_alignment", False
    return "review_loose_alignment", False


def build_breakout_aligned_training_seed_report(
    alignment_rows: Sequence[Mapping[str, Any]] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_row in list(alignment_rows or []):
        row = dict(raw_row)
        match_status = _to_text(row.get("match_status"), "")
        time_gap_sec = _to_float(row.get("time_gap_sec"), 0.0)
        grade = _seed_grade(time_gap_sec) if match_status == "matched" else ""
        seed_status, promote = _seed_status(grade, match_status)
        rows.append(
            {
                "episode_id": _to_text(row.get("episode_id"), ""),
                "symbol": _to_text(row.get("symbol"), ""),
                "coverage_state": _to_text(row.get("coverage_state"), ""),
                "review_status": _to_text(row.get("review_status"), ""),
                "annotation_source": _to_text(row.get("annotation_source"), ""),
                "action_target": _to_text(row.get("action_target"), ""),
                "continuation_target": _to_text(row.get("continuation_target"), ""),
                "matched_job_id": _to_text(row.get("matched_job_id"), ""),
                "matched_decision_time": _to_text(row.get("matched_decision_time"), ""),
                "time_gap_sec": round(time_gap_sec, 3) if match_status == "matched" else "",
                "seed_grade": grade,
                "seed_status": seed_status,
                "promote_to_training": bool(promote),
                "transition_label_status": _to_text(row.get("transition_label_status"), ""),
                "management_label_status": _to_text(row.get("management_label_status"), ""),
                "transition_hit_rate": _to_float(row.get("transition_hit_rate"), 0.0),
                "management_hit_rate": _to_float(row.get("management_hit_rate"), 0.0),
                "p_buy_confirm": _to_float(row.get("p_buy_confirm"), 0.0),
                "actual_buy_confirm": _to_text(row.get("actual_buy_confirm"), ""),
                "p_continuation_success": _to_float(row.get("p_continuation_success"), 0.0),
                "actual_continuation_success": _to_text(row.get("actual_continuation_success"), ""),
                "p_false_break": _to_float(row.get("p_false_break"), 0.0),
                "actual_false_break": _to_text(row.get("actual_false_break"), ""),
                "p_continue_favor": _to_float(row.get("p_continue_favor"), 0.0),
                "actual_continue_favor": _to_text(row.get("actual_continue_favor"), ""),
                "p_fail_now": _to_float(row.get("p_fail_now"), 0.0),
                "actual_fail_now": _to_text(row.get("actual_fail_now"), ""),
                "p_opposite_edge_reach": _to_float(row.get("p_opposite_edge_reach"), 0.0),
                "actual_opposite_edge_reach": _to_text(row.get("actual_opposite_edge_reach"), ""),
                "reason_summary": _to_text(row.get("reason_summary"), ""),
                "recommended_next_step": "use_in_breakout_preview_training" if promote else _to_text(row.get("recommended_next_step"), ""),
            }
        )

    summary = {
        "contract_version": BREAKOUT_ALIGNED_TRAINING_SEED_VERSION,
        "row_count": len(rows),
        "promoted_count": int(sum(1 for row in rows if bool(row.get("promote_to_training", False)))),
        "strict_count": int(sum(1 for row in rows if _to_text(row.get("seed_grade"), "") == "strict")),
        "good_count": int(sum(1 for row in rows if _to_text(row.get("seed_grade"), "") == "good")),
        "coarse_review_count": int(sum(1 for row in rows if _to_text(row.get("seed_grade"), "") == "coarse_review")),
        "loose_review_count": int(sum(1 for row in rows if _to_text(row.get("seed_grade"), "") == "loose_review")),
        "symbol_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("symbol"), "") for row in rows if bool(row.get("promote_to_training", False))]).value_counts().items()
            if str(key)
        },
        "action_target_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("action_target"), "") for row in rows if bool(row.get("promote_to_training", False))]).value_counts().items()
            if str(key)
        },
    }
    return rows, summary


def render_breakout_aligned_training_seed_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, Mapping) else {}
    rows = payload.get("rows", []) if isinstance(payload, Mapping) else []
    lines = [
        "# Breakout Aligned Training Seed",
        "",
        f"- contract_version: `{_to_text(summary.get('contract_version'), BREAKOUT_ALIGNED_TRAINING_SEED_VERSION)}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- promoted_count: `{summary.get('promoted_count', 0)}`",
        f"- strict_count: `{summary.get('strict_count', 0)}`",
        f"- good_count: `{summary.get('good_count', 0)}`",
        "",
        "## Promoted Seeds",
    ]
    promoted_rows = [row for row in rows if bool(row.get("promote_to_training", False))][:15]
    if not promoted_rows:
        lines.append("- no promoted rows")
    else:
        for row in promoted_rows:
            lines.append(
                "- "
                f"{_to_text(row.get('episode_id'))} | {_to_text(row.get('symbol'))} | "
                f"{_to_text(row.get('action_target'))} | {_to_text(row.get('continuation_target'))} | "
                f"gap={_to_text(row.get('time_gap_sec'))}s | grade={_to_text(row.get('seed_grade'))}"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_aligned_training_seed_report(
    *,
    alignment_csv_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> dict[str, Any]:
    project_root = _project_root()
    alignment_path = _resolve_project_path(
        alignment_csv_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.csv",
    )
    csv_path = _resolve_project_path(
        csv_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_aligned_training_seed_latest.csv",
    )
    json_path = _resolve_project_path(
        json_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_aligned_training_seed_latest.json",
    )
    markdown_path = _resolve_project_path(
        markdown_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_aligned_training_seed_latest.md",
    )

    rows, summary = build_breakout_aligned_training_seed_report(_load_csv_rows(alignment_path))
    payload = {
        "summary": summary,
        "rows": rows,
        "alignment_csv_path": str(alignment_path),
        "csv_output_path": str(csv_path),
        "json_output_path": str(json_path),
        "markdown_output_path": str(markdown_path),
    }

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_ALIGNED_TRAINING_SEED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in BREAKOUT_ALIGNED_TRAINING_SEED_COLUMNS})

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_breakout_aligned_training_seed_markdown(payload), encoding="utf-8")
    return payload
