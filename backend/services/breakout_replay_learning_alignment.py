"""Align breakout manual learning rows with replay datasets produced by backfill jobs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


BREAKOUT_REPLAY_LEARNING_ALIGNMENT_VERSION = "breakout_replay_learning_alignment_v1"
BREAKOUT_REPLAY_LEARNING_ALIGNMENT_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "ideal_entry_time",
    "ideal_exit_time",
    "review_status",
    "annotation_source",
    "coverage_state",
    "action_target",
    "continuation_target",
    "matched_job_id",
    "matched_queue_id",
    "matched_time_field",
    "match_status",
    "matched_decision_time",
    "time_gap_sec",
    "decision_action",
    "decision_outcome",
    "setup_id",
    "observe_reason",
    "blocked_by",
    "transition_label_status",
    "management_label_status",
    "p_buy_confirm",
    "p_continuation_success",
    "p_false_break",
    "p_continue_favor",
    "p_fail_now",
    "p_opposite_edge_reach",
    "actual_buy_confirm",
    "actual_continuation_success",
    "actual_false_break",
    "actual_continue_favor",
    "actual_fail_now",
    "actual_opposite_edge_reach",
    "transition_hit_rate",
    "management_hit_rate",
    "replay_dataset_path",
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


def _discover_replay_dataset_path(job_dir: Path) -> Path | None:
    replay_dir = job_dir / "replay_dataset"
    if not replay_dir.exists():
        return None
    candidates = sorted(replay_dir.glob("replay_dataset_rows_*.jsonl"))
    if not candidates:
        return None
    return candidates[-1]


def _discover_scoped_entry_path(job_dir: Path) -> Path | None:
    candidate = job_dir / "entry_decisions_scoped.csv"
    if candidate.exists():
        return candidate
    return None


def _manual_target_times(row: Mapping[str, Any]) -> list[tuple[str, pd.Timestamp]]:
    action_target = _to_text(row.get("action_target"), "").upper()
    ordered_fields: list[str]
    if action_target == "EXIT_PROTECT":
        ordered_fields = ["ideal_exit_time", "anchor_time", "ideal_entry_time"]
    else:
        ordered_fields = ["ideal_entry_time", "anchor_time", "ideal_exit_time"]

    target_times: list[tuple[str, pd.Timestamp]] = []
    for field in ordered_fields:
        parsed = _parse_local_timestamp(row.get(field))
        if parsed is None:
            continue
        target_times.append((field, parsed))
    return target_times


def _find_candidate_jobs(
    job_rows: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    target_times: Sequence[tuple[str, pd.Timestamp]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for raw_row in job_rows:
        row = dict(raw_row)
        if _to_text(row.get("symbol"), "").upper() != symbol.upper():
            continue
        job_start = _parse_local_timestamp(row.get("window_start"))
        job_end = _parse_local_timestamp(row.get("window_end"))
        if job_start is None or job_end is None:
            continue
        if any(job_start <= target_time <= job_end for _, target_time in target_times):
            replay_dataset_path = _discover_replay_dataset_path(Path(_to_text(row.get("job_dir"), "")))
            row["replay_dataset_path"] = str(replay_dataset_path) if replay_dataset_path else ""
            candidates.append(row)
    return sorted(
        candidates,
        key=lambda item: (
            0 if _to_text(item.get("replay_dataset_path"), "") else 1,
            _to_float(item.get("manual_anchor_rows"), 0.0) * -1.0,
            _to_text(item.get("window_start"), ""),
        ),
    )


def _iter_jsonl_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = line.strip()
            if not payload:
                continue
            try:
                yield json.loads(payload)
            except json.JSONDecodeError:
                continue


def _load_scoped_entry_frame(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        frame = pd.read_csv(path, low_memory=False)
    if frame.empty:
        return frame
    if "time" not in frame.columns:
        frame["time"] = ""
    frame["time_parsed"] = frame["time"].apply(_parse_local_timestamp)
    return frame[frame["time_parsed"].notna()].copy()


def _extract_probability(container: Mapping[str, Any], key: str) -> float:
    return _to_float(container.get(key), 0.0)


def _extract_actual_positive(
    evaluation_map: Mapping[str, Any],
    key: str,
) -> str:
    record = evaluation_map.get(key)
    if not isinstance(record, Mapping):
        return ""
    actual = record.get("actual_positive")
    if actual is None:
        return ""
    return "1" if bool(actual) else "0"


def _match_manual_row_to_scoped_entry(
    manual_row: Mapping[str, Any],
    *,
    scoped_entry_frame: pd.DataFrame,
    tolerance_seconds: float,
) -> dict[str, Any]:
    target_times = _manual_target_times(manual_row)
    if not target_times:
        return {
            "match_status": "unmatched",
            "matched_time_field": "",
            "matched_decision_time": "",
            "time_gap_sec": "",
            "reason_summary": "manual_row_missing_target_times",
            "recommended_next_step": "fill_manual_anchor_or_entry_times",
        }

    if scoped_entry_frame.empty:
        return {
            "match_status": "unmatched",
            "matched_time_field": "",
            "matched_decision_time": "",
            "time_gap_sec": "",
            "reason_summary": "scoped_entry_rows_missing",
            "recommended_next_step": "build_or_refresh_scoped_entry_rows",
        }

    best_row: dict[str, Any] | None = None
    best_gap = float("inf")
    best_field = ""
    for field_name, target_time in target_times:
        working = scoped_entry_frame.copy()
        working["time_gap_sec"] = (working["time_parsed"] - target_time).abs().dt.total_seconds()
        matched = working.sort_values(["time_gap_sec", "time_parsed"], kind="stable").head(1)
        if matched.empty:
            continue
        row = matched.iloc[0].to_dict()
        gap_sec = _to_float(row.get("time_gap_sec"), float("inf"))
        if gap_sec < best_gap:
            best_gap = gap_sec
            best_row = row
            best_field = field_name

    if best_row is None or best_gap > float(tolerance_seconds):
        return {
            "match_status": "unmatched",
            "matched_time_field": best_field,
            "matched_decision_time": "",
            "time_gap_sec": round(best_gap, 3) if best_gap != float("inf") else "",
            "reason_summary": "no_replay_row_within_tolerance",
            "recommended_next_step": "widen_window_or_loosen_match_tolerance",
        }

    return {
        "match_status": "matched",
        "matched_time_field": best_field,
        "matched_decision_time": _to_text(best_row.get("time"), ""),
        "time_gap_sec": round(best_gap, 3),
        "decision_action": _to_text(best_row.get("action"), ""),
        "decision_outcome": _to_text(best_row.get("outcome"), ""),
        "setup_id": _to_text(best_row.get("setup_id"), ""),
        "observe_reason": _to_text(best_row.get("observe_reason"), ""),
        "blocked_by": _to_text(best_row.get("blocked_by"), ""),
        "decision_row_key": _to_text(best_row.get("decision_row_key") or best_row.get("replay_row_key") or best_row.get("row_key"), ""),
        "reason_summary": "matched_replay_row_within_tolerance",
        "recommended_next_step": "promote_to_runtime_aligned_breakout_training_case",
    }


def _load_replay_summary_map(
    replay_dataset_path: Path | None,
    wanted_keys: set[str],
) -> dict[str, dict[str, Any]]:
    if replay_dataset_path is None or not replay_dataset_path.exists() or not wanted_keys:
        return {}

    matched: dict[str, dict[str, Any]] = {}
    for replay_row in _iter_jsonl_rows(replay_dataset_path):
        row_key = _to_text(
            replay_row.get("decision_row_key") or replay_row.get("replay_row_key") or replay_row.get("row_key"),
            "",
        )
        if not row_key or row_key not in wanted_keys:
            continue
        label_summary = replay_row.get("label_quality_summary_v1") if isinstance(replay_row.get("label_quality_summary_v1"), Mapping) else {}
        transition_summary = label_summary.get("transition") if isinstance(label_summary.get("transition"), Mapping) else {}
        management_summary = label_summary.get("management") if isinstance(label_summary.get("management"), Mapping) else {}
        transition_eval = transition_summary.get("forecast_vs_outcome_v1", {}).get("evaluations", {}) if isinstance(transition_summary.get("forecast_vs_outcome_v1"), Mapping) else {}
        management_eval = management_summary.get("forecast_vs_outcome_v1", {}).get("evaluations", {}) if isinstance(management_summary.get("forecast_vs_outcome_v1"), Mapping) else {}
        transition_forecast_probs = transition_summary.get("forecast_probabilities") if isinstance(transition_summary.get("forecast_probabilities"), Mapping) else {}
        management_forecast_probs = management_summary.get("forecast_probabilities") if isinstance(management_summary.get("forecast_probabilities"), Mapping) else {}
        matched[row_key] = {
            "transition_label_status": _to_text(replay_row.get("transition_label_status"), ""),
            "management_label_status": _to_text(replay_row.get("management_label_status"), ""),
            "p_buy_confirm": _extract_probability(transition_forecast_probs, "p_buy_confirm"),
            "p_continuation_success": _extract_probability(transition_forecast_probs, "p_continuation_success"),
            "p_false_break": _extract_probability(transition_forecast_probs, "p_false_break"),
            "p_continue_favor": _extract_probability(management_forecast_probs, "p_continue_favor"),
            "p_fail_now": _extract_probability(management_forecast_probs, "p_fail_now"),
            "p_opposite_edge_reach": _extract_probability(management_forecast_probs, "p_opposite_edge_reach"),
            "actual_buy_confirm": _extract_actual_positive(transition_eval, "p_buy_confirm"),
            "actual_continuation_success": _extract_actual_positive(transition_eval, "p_continuation_success"),
            "actual_false_break": _extract_actual_positive(transition_eval, "p_false_break"),
            "actual_continue_favor": _extract_actual_positive(management_eval, "p_continue_favor"),
            "actual_fail_now": _extract_actual_positive(management_eval, "p_fail_now"),
            "actual_opposite_edge_reach": _extract_actual_positive(management_eval, "p_opposite_edge_reach"),
            "transition_hit_rate": _to_float(
                (((transition_summary.get("forecast_vs_outcome_v1") or {}).get("summary") or {}).get("hit_rate")),
                0.0,
            ),
            "management_hit_rate": _to_float(
                (((management_summary.get("forecast_vs_outcome_v1") or {}).get("summary") or {}).get("hit_rate")),
                0.0,
            ),
        }
        if len(matched) >= len(wanted_keys):
            break
    return matched


def build_breakout_replay_learning_alignment_report(
    learning_rows: Sequence[Mapping[str, Any]] | None,
    *,
    scaffold_rows: Sequence[Mapping[str, Any]] | None = None,
    tolerance_minutes: int = 20,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    job_rows = [dict(row) for row in list(scaffold_rows or [])]
    prepared_rows: list[dict[str, Any]] = []

    for raw_manual_row in list(learning_rows or []):
        manual_row = dict(raw_manual_row)
        symbol = _to_text(manual_row.get("symbol"), "").upper()
        target_times = _manual_target_times(manual_row)
        candidate_jobs = _find_candidate_jobs(job_rows, symbol=symbol, target_times=target_times)
        matched_job = candidate_jobs[0] if candidate_jobs else {}
        replay_dataset_path_text = _to_text(matched_job.get("replay_dataset_path"), "")
        scoped_entry_path = _discover_scoped_entry_path(Path(_to_text(matched_job.get("job_dir"), ""))) if matched_job else None
        prepared_rows.append(
            {
                "manual_row": manual_row,
                "matched_job": matched_job,
                "replay_dataset_path": replay_dataset_path_text,
                "scoped_entry_path": str(scoped_entry_path) if scoped_entry_path else "",
            }
        )

    rows: list[dict[str, Any]] = []
    prepared_by_job: dict[str, list[dict[str, Any]]] = {}
    for prepared in prepared_rows:
        job_id = _to_text((prepared.get("matched_job") or {}).get("job_id"), "__no_job__")
        prepared_by_job.setdefault(job_id, []).append(prepared)

    for prepared_group in prepared_by_job.values():
        matched_job = prepared_group[0].get("matched_job") or {}
        scoped_entry_path_text = _to_text(prepared_group[0].get("scoped_entry_path"), "")
        replay_dataset_path_text = _to_text(prepared_group[0].get("replay_dataset_path"), "")
        scoped_entry_frame = _load_scoped_entry_frame(Path(scoped_entry_path_text)) if scoped_entry_path_text else pd.DataFrame()
        needed_row_keys: set[str] = set()
        intermediate_rows: list[dict[str, Any]] = []

        for prepared in prepared_group:
            manual_row = prepared.get("manual_row") or {}
            if matched_job and scoped_entry_path_text:
                replay_summary = _match_manual_row_to_scoped_entry(
                    manual_row,
                    scoped_entry_frame=scoped_entry_frame,
                    tolerance_seconds=float(tolerance_minutes) * 60.0,
                )
            elif matched_job:
                replay_summary = {
                    "match_status": "unmatched",
                    "matched_time_field": "",
                    "matched_decision_time": "",
                    "time_gap_sec": "",
                    "reason_summary": "job_window_exists_but_scoped_entry_missing",
                    "recommended_next_step": "run_or_refresh_backfill_scaffold",
                }
            else:
                replay_summary = {
                    "match_status": "unmatched",
                    "matched_time_field": "",
                    "matched_decision_time": "",
                    "time_gap_sec": "",
                    "reason_summary": "no_replay_job_window_for_manual_case",
                    "recommended_next_step": "build_or_request_replay_backfill_window",
                }

            row = {
                "episode_id": _to_text(manual_row.get("episode_id"), ""),
                "symbol": _to_text(manual_row.get("symbol"), "").upper(),
                "anchor_time": _to_text(manual_row.get("anchor_time"), ""),
                "ideal_entry_time": _to_text(manual_row.get("ideal_entry_time"), ""),
                "ideal_exit_time": _to_text(manual_row.get("ideal_exit_time"), ""),
                "review_status": _to_text(manual_row.get("review_status"), ""),
                "annotation_source": _to_text(manual_row.get("annotation_source"), ""),
                "coverage_state": _to_text(manual_row.get("coverage_state"), ""),
                "action_target": _to_text(manual_row.get("action_target"), ""),
                "continuation_target": _to_text(manual_row.get("continuation_target"), ""),
                "matched_job_id": _to_text(matched_job.get("job_id"), ""),
                "matched_queue_id": _to_text(matched_job.get("queue_id"), ""),
                "replay_dataset_path": replay_dataset_path_text,
            }
            row.update(replay_summary)
            row_key = _to_text(row.get("decision_row_key"), "")
            if row_key:
                needed_row_keys.add(row_key)
            intermediate_rows.append(row)

        replay_summary_map = _load_replay_summary_map(Path(replay_dataset_path_text), needed_row_keys) if replay_dataset_path_text else {}
        for row in intermediate_rows:
            row_key = _to_text(row.get("decision_row_key"), "")
            if row_key and row_key in replay_summary_map:
                row.update(replay_summary_map[row_key])
            for column in BREAKOUT_REPLAY_LEARNING_ALIGNMENT_COLUMNS:
                row.setdefault(column, "")
            row.pop("decision_row_key", None)
            rows.append(row)

    matched_count = sum(1 for row in rows if _to_text(row.get("match_status"), "") == "matched")
    unmatched_count = len(rows) - matched_count
    summary = {
        "contract_version": BREAKOUT_REPLAY_LEARNING_ALIGNMENT_VERSION,
        "row_count": len(rows),
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "symbol_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("symbol"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "coverage_state_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("coverage_state"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "action_target_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("action_target"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "continuation_target_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("continuation_target"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "match_status_counts": {
            str(key): int(value)
            for key, value in pd.Series([_to_text(row.get("match_status"), "") for row in rows]).value_counts().items()
            if str(key)
        },
        "tolerance_minutes": int(tolerance_minutes),
    }
    return rows, summary


def render_breakout_replay_learning_alignment_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, Mapping) else {}
    rows = payload.get("rows", []) if isinstance(payload, Mapping) else []
    lines = [
        "# Breakout Replay Learning Alignment",
        "",
        f"- contract_version: `{_to_text(summary.get('contract_version'), BREAKOUT_REPLAY_LEARNING_ALIGNMENT_VERSION)}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- matched_count: `{summary.get('matched_count', 0)}`",
        f"- unmatched_count: `{summary.get('unmatched_count', 0)}`",
        f"- tolerance_minutes: `{summary.get('tolerance_minutes', 0)}`",
        "",
        "## Sample Matches",
    ]
    matched_rows = [row for row in rows if _to_text(row.get("match_status"), "") == "matched"][:10]
    if not matched_rows:
        lines.append("- no matched replay rows yet")
    else:
        for row in matched_rows:
            lines.append(
                "- "
                f"{_to_text(row.get('episode_id'))} | {_to_text(row.get('symbol'))} | "
                f"{_to_text(row.get('matched_decision_time'))} | "
                f"{_to_text(row.get('action_target'))} | "
                f"{_to_text(row.get('continuation_target'))} | "
                f"gap={_to_text(row.get('time_gap_sec'))}s"
            )
    return "\n".join(lines).strip() + "\n"


def write_breakout_replay_learning_alignment_report(
    *,
    learning_bridge_path: str | Path | None = None,
    scaffold_csv_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
    tolerance_minutes: int = 20,
) -> dict[str, Any]:
    project_root = _project_root()
    learning_path = _resolve_project_path(
        learning_bridge_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_manual_learning_bridge_latest.csv",
    )
    scaffold_path = _resolve_project_path(
        scaffold_csv_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.csv",
    )
    csv_path = _resolve_project_path(
        csv_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.csv",
    )
    json_path = _resolve_project_path(
        json_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.json",
    )
    markdown_path = _resolve_project_path(
        markdown_output_path,
        project_root / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.md",
    )

    learning_rows = _load_csv_rows(learning_path)
    scaffold_rows = _load_csv_rows(scaffold_path)
    rows, summary = build_breakout_replay_learning_alignment_report(
        learning_rows,
        scaffold_rows=scaffold_rows,
        tolerance_minutes=tolerance_minutes,
    )

    payload = {
        "summary": summary,
        "rows": rows,
        "learning_bridge_path": str(learning_path),
        "scaffold_csv_path": str(scaffold_path),
        "csv_output_path": str(csv_path),
        "json_output_path": str(json_path),
        "markdown_output_path": str(markdown_path),
    }

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_REPLAY_LEARNING_ALIGNMENT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in BREAKOUT_REPLAY_LEARNING_ALIGNMENT_COLUMNS})

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_breakout_replay_learning_alignment_markdown(payload), encoding="utf-8")
    return payload
