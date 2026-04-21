"""Suggest coarse replay/manual time corrections for breakout cases that missed strict alignment."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd


BREAKOUT_REPLAY_TIME_CORRECTION_VERSION = "breakout_replay_time_correction_v1"
BREAKOUT_REPLAY_TIME_CORRECTION_COLUMNS = [
    "episode_id",
    "symbol",
    "coverage_state",
    "action_target",
    "continuation_target",
    "matched_job_id",
    "match_reason",
    "coarse_match_status",
    "coarse_gap_sec",
    "coarse_decision_time",
    "coarse_action",
    "coarse_outcome",
    "coarse_setup_id",
    "coarse_observe_reason",
    "coarse_blocked_by",
    "suggested_anchor_time",
    "suggested_entry_time",
    "suggested_exit_time",
    "anchor_shift_sec",
    "entry_shift_sec",
    "exit_shift_sec",
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


def _format_local_timestamp(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).isoformat(timespec="seconds")


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _load_scoped_entry_frame(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(path, low_memory=False)
    if "time" not in frame.columns:
        frame["time"] = ""
    frame["time_parsed"] = frame["time"].apply(_parse_local_timestamp)
    return frame[frame["time_parsed"].notna()].copy()


def _manual_target_times(row: Mapping[str, Any]) -> list[tuple[str, pd.Timestamp]]:
    action_target = _to_text(row.get("action_target"), "").upper()
    order = ["ideal_exit_time", "ideal_entry_time", "anchor_time"] if action_target == "EXIT_PROTECT" else ["ideal_entry_time", "anchor_time", "ideal_exit_time"]
    output: list[tuple[str, pd.Timestamp]] = []
    for field in order:
        parsed = _parse_local_timestamp(row.get(field))
        if parsed is not None:
            output.append((field, parsed))
    return output


def _nearest_scoped_entry(
    frame: pd.DataFrame,
    *,
    target_times: Sequence[tuple[str, pd.Timestamp]],
) -> tuple[dict[str, Any] | None, str, float]:
    if frame.empty or not target_times:
        return None, "", float("inf")
    best_row: dict[str, Any] | None = None
    best_field = ""
    best_gap = float("inf")
    for field_name, target_time in target_times:
        working = frame.copy()
        working["time_gap_sec"] = (working["time_parsed"] - target_time).abs().dt.total_seconds()
        matched = working.sort_values(["time_gap_sec", "time_parsed"], kind="stable").head(1)
        if matched.empty:
            continue
        row = matched.iloc[0].to_dict()
        gap = _to_float(row.get("time_gap_sec"), float("inf"))
        if gap < best_gap:
            best_row = row
            best_field = field_name
            best_gap = gap
    return best_row, best_field, best_gap


def _suggest_shifted_time(original: pd.Timestamp | None, delta_sec: float) -> str:
    if original is None:
        return ""
    return _format_local_timestamp(original + pd.to_timedelta(delta_sec, unit="s"))


def build_breakout_replay_time_correction_report(
    alignment_rows: Sequence[Mapping[str, Any]] | None,
    *,
    scaffold_rows: Sequence[Mapping[str, Any]] | None = None,
    coarse_tolerance_seconds: int = 1800,
    review_tolerance_seconds: int = 7200,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scaffold_by_job = {
        _to_text(row.get("job_id"), ""): dict(row)
        for row in list(scaffold_rows or [])
        if _to_text(row.get("job_id"), "")
    }
    cache: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []

    for raw_row in list(alignment_rows or []):
        alignment_row = dict(raw_row)
        if _to_text(alignment_row.get("match_status"), "") == "matched":
            continue
        if _to_text(alignment_row.get("reason_summary"), "") != "no_replay_row_within_tolerance":
            continue

        job_id = _to_text(alignment_row.get("matched_job_id"), "")
        scaffold_row = scaffold_by_job.get(job_id, {})
        scoped_entry_path = Path(_to_text(scaffold_row.get("job_dir"), "")) / "entry_decisions_scoped.csv" if scaffold_row else None
        cache_key = str(scoped_entry_path) if scoped_entry_path else ""
        if cache_key and cache_key not in cache:
            cache[cache_key] = _load_scoped_entry_frame(scoped_entry_path)
        scoped_frame = cache.get(cache_key, pd.DataFrame())
        nearest_row, matched_field, coarse_gap = _nearest_scoped_entry(
            scoped_frame,
            target_times=_manual_target_times(alignment_row),
        )

        if nearest_row is None or coarse_gap > float(review_tolerance_seconds):
            coarse_status = "no_candidate_found"
            next_step = "create_manual_retime_by_chart_review"
            coarse_time = ""
            delta_sec = 0.0
        else:
            coarse_time = _to_text(nearest_row.get("time"), "")
            target_lookup = dict(_manual_target_times(alignment_row))
            target_time = target_lookup.get(matched_field)
            decision_time = _parse_local_timestamp(coarse_time)
            delta_sec = float((decision_time - target_time).total_seconds()) if decision_time is not None and target_time is not None else 0.0
            if coarse_gap <= float(coarse_tolerance_seconds):
                coarse_status = "auto_retime_candidate"
                next_step = "review_and_promote_coarse_match"
            else:
                coarse_status = "manual_review_candidate"
                next_step = "manual_retime_review_needed"

        anchor_time = _parse_local_timestamp(alignment_row.get("anchor_time"))
        ideal_entry_time = _parse_local_timestamp(alignment_row.get("ideal_entry_time"))
        ideal_exit_time = _parse_local_timestamp(alignment_row.get("ideal_exit_time"))

        rows.append(
            {
                "episode_id": _to_text(alignment_row.get("episode_id"), ""),
                "symbol": _to_text(alignment_row.get("symbol"), ""),
                "coverage_state": _to_text(alignment_row.get("coverage_state"), ""),
                "action_target": _to_text(alignment_row.get("action_target"), ""),
                "continuation_target": _to_text(alignment_row.get("continuation_target"), ""),
                "matched_job_id": job_id,
                "match_reason": _to_text(alignment_row.get("reason_summary"), ""),
                "coarse_match_status": coarse_status,
                "coarse_gap_sec": round(coarse_gap, 3) if coarse_gap != float("inf") else "",
                "coarse_decision_time": coarse_time,
                "coarse_action": _to_text((nearest_row or {}).get("action"), ""),
                "coarse_outcome": _to_text((nearest_row or {}).get("outcome"), ""),
                "coarse_setup_id": _to_text((nearest_row or {}).get("setup_id"), ""),
                "coarse_observe_reason": _to_text((nearest_row or {}).get("observe_reason"), ""),
                "coarse_blocked_by": _to_text((nearest_row or {}).get("blocked_by"), ""),
                "suggested_anchor_time": _suggest_shifted_time(anchor_time, delta_sec),
                "suggested_entry_time": _suggest_shifted_time(ideal_entry_time, delta_sec),
                "suggested_exit_time": _suggest_shifted_time(ideal_exit_time, delta_sec),
                "anchor_shift_sec": round(delta_sec, 3) if coarse_status != "no_candidate_found" else "",
                "entry_shift_sec": round(delta_sec, 3) if coarse_status != "no_candidate_found" else "",
                "exit_shift_sec": round(delta_sec, 3) if coarse_status != "no_candidate_found" else "",
                "recommended_next_step": next_step,
            }
        )

    summary = {
        "contract_version": BREAKOUT_REPLAY_TIME_CORRECTION_VERSION,
        "row_count": len(rows),
        "auto_retime_candidate_count": int(sum(1 for row in rows if _to_text(row.get("coarse_match_status"), "") == "auto_retime_candidate")),
        "manual_review_candidate_count": int(sum(1 for row in rows if _to_text(row.get("coarse_match_status"), "") == "manual_review_candidate")),
        "no_candidate_count": int(sum(1 for row in rows if _to_text(row.get("coarse_match_status"), "") == "no_candidate_found")),
        "symbol_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("symbol"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "coarse_tolerance_seconds": int(coarse_tolerance_seconds),
        "review_tolerance_seconds": int(review_tolerance_seconds),
    }
    return rows, summary


def render_breakout_replay_time_correction_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, Mapping) else {}
    rows = payload.get("rows", []) if isinstance(payload, Mapping) else []
    lines = [
        "# Breakout Replay Time Correction",
        "",
        f"- contract_version: `{_to_text(summary.get('contract_version'), BREAKOUT_REPLAY_TIME_CORRECTION_VERSION)}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- auto_retime_candidate_count: `{summary.get('auto_retime_candidate_count', 0)}`",
        f"- manual_review_candidate_count: `{summary.get('manual_review_candidate_count', 0)}`",
        "",
        "## Top Candidates",
    ]
    for row in rows[:15]:
        lines.append(
            "- "
            f"{_to_text(row.get('episode_id'))} | {_to_text(row.get('symbol'))} | "
            f"{_to_text(row.get('coarse_match_status'))} | gap={_to_text(row.get('coarse_gap_sec'))}s | "
            f"suggested_entry={_to_text(row.get('suggested_entry_time'))}"
        )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_replay_time_correction_report(
    *,
    alignment_csv_path: str | Path | None = None,
    scaffold_csv_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    coarse_tolerance_seconds: int = 1800,
    review_tolerance_seconds: int = 7200,
) -> dict[str, Any]:
    project_root = _project_root()
    alignment_path = _resolve_project_path(
        alignment_csv_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.csv",
    )
    scaffold_path = _resolve_project_path(
        scaffold_csv_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.csv",
    )
    csv_path = _resolve_project_path(
        csv_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_time_correction_latest.csv",
    )
    json_path = _resolve_project_path(
        json_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_time_correction_latest.json",
    )
    markdown_path = _resolve_project_path(
        markdown_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_time_correction_latest.md",
    )

    rows, summary = build_breakout_replay_time_correction_report(
        _load_csv_rows(alignment_path),
        scaffold_rows=_load_csv_rows(scaffold_path),
        coarse_tolerance_seconds=coarse_tolerance_seconds,
        review_tolerance_seconds=review_tolerance_seconds,
    )
    payload = {
        "summary": summary,
        "rows": rows,
        "alignment_csv_path": str(alignment_path),
        "scaffold_csv_path": str(scaffold_path),
        "csv_output_path": str(csv_path),
        "json_output_path": str(json_path),
        "markdown_output_path": str(markdown_path),
    }

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_REPLAY_TIME_CORRECTION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in BREAKOUT_REPLAY_TIME_CORRECTION_COLUMNS})

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_breakout_replay_time_correction_markdown(payload), encoding="utf-8")
    return payload
