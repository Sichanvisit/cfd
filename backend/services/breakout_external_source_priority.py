"""Prioritize external source acquisition for breakout backfill jobs."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


BREAKOUT_EXTERNAL_SOURCE_PRIORITY_VERSION = "breakout_external_source_priority_v1"
BREAKOUT_EXTERNAL_SOURCE_PRIORITY_COLUMNS = [
    "job_id",
    "queue_id",
    "symbol",
    "priority",
    "recovery_type",
    "coverage_state",
    "request_scope",
    "request_start",
    "request_end",
    "missing_gap_count",
    "missing_gap_minutes",
    "manual_anchor_rows",
    "source_case_count",
    "scoped_entry_row_count",
    "ready_for_replay_execution",
    "external_source_required",
    "priority_score",
    "recommended_source_kind",
    "reason_summary",
    "source_episode_ids",
    "scene_ids",
    "chart_contexts",
    "manual_targets_path",
    "job_manifest_path",
    "request_manifest_path",
    "request_markdown_path",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_project_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _safe_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _to_text(value, "").lower() in {"1", "true", "yes", "y"}


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _parse_local_dt(value: object) -> datetime | None:
    text = _to_text(value, "")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _minutes_between(start: datetime | None, end: datetime | None) -> float:
    if start is None or end is None:
        return 0.0
    return max(0.0, (end - start).total_seconds() / 60.0)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")) or {})
    except Exception:
        return {}


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _load_manual_subset_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    subset_text = _to_text(manifest.get("manual_anchor_subset_path"), "")
    if not subset_text:
        return []
    subset_path = Path(subset_text)
    return _load_csv_rows(subset_path) if subset_path.exists() and subset_path.is_file() else []


def _discover_job_manifest_paths(bundle_root: Path) -> list[Path]:
    jobs_root = bundle_root / "jobs"
    if not jobs_root.exists():
        return []
    return sorted(jobs_root.glob("*/breakout_backfill_job_manifest.json"))


def _request_scope(coverage_state: str) -> str:
    coverage_state_u = _to_text(coverage_state, "").lower()
    if coverage_state_u == "no_internal_source":
        return "full_window"
    if coverage_state_u == "partial_internal_source":
        return "gap_only"
    return "none"


def _gap_bounds(manifest: Mapping[str, Any]) -> tuple[str, str, int, float]:
    coverage_gaps = list(manifest.get("coverage_gaps", []) or [])
    if not coverage_gaps:
        return "", "", 0, 0.0
    gap_count = len(coverage_gaps)
    total_minutes = 0.0
    starts: list[str] = []
    ends: list[str] = []
    for gap in coverage_gaps:
        if not isinstance(gap, Mapping):
            continue
        gap_start = _to_text(gap.get("gap_start"), "")
        gap_end = _to_text(gap.get("gap_end"), "")
        if gap_start:
            starts.append(gap_start)
        if gap_end:
            ends.append(gap_end)
        total_minutes += _minutes_between(_parse_local_dt(gap_start), _parse_local_dt(gap_end))
    return (
        min(starts) if starts else "",
        max(ends) if ends else "",
        int(gap_count),
        round(float(total_minutes), 3),
    )


def _priority_score(
    *,
    coverage_state: str,
    manual_anchor_rows: int,
    source_case_count: int,
    missing_gap_minutes: float,
    ready_for_replay_execution: bool,
) -> float:
    coverage_state_u = _to_text(coverage_state, "").lower()
    base = 0.0
    if coverage_state_u == "no_internal_source":
        base += 300.0
    elif coverage_state_u == "partial_internal_source":
        base += 180.0
    elif coverage_state_u == "full_internal_source":
        base += 20.0
    base += float(manual_anchor_rows) * 3.0
    base += float(source_case_count) * 12.0
    base += min(float(missing_gap_minutes), 12 * 60.0) * 0.2
    if not ready_for_replay_execution:
        base += 40.0
    return round(base, 3)


def _recommended_source_kind(coverage_state: str) -> str:
    coverage_state_u = _to_text(coverage_state, "").lower()
    if coverage_state_u == "no_internal_source":
        return "mt5_runtime_export_required"
    if coverage_state_u == "partial_internal_source":
        return "legacy_or_mt5_gap_fill_required"
    return "no_external_source_needed"


def _load_scaffold_source_case_counts(scaffold_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in scaffold_rows:
        queue_id = _to_text(row.get("queue_id"), "")
        if not queue_id:
            continue
        counts[queue_id] = _to_int(row.get("manual_anchor_rows"), 0)
    return counts


def _request_manifest_payload(manifest: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    coverage_gaps = list(manifest.get("coverage_gaps", []) or [])
    manual_subset_rows = _load_manual_subset_rows(manifest)
    source_episode_ids = sorted({_to_text(item.get("episode_id"), "") for item in manual_subset_rows if _to_text(item.get("episode_id"), "")})
    scene_ids = sorted({_to_text(item.get("scene_id"), "") for item in manual_subset_rows if _to_text(item.get("scene_id"), "")})
    chart_contexts = sorted({_to_text(item.get("chart_context"), "") for item in manual_subset_rows if _to_text(item.get("chart_context"), "")})
    manual_targets = [
        {
            "episode_id": _to_text(item.get("episode_id"), ""),
            "scene_id": _to_text(item.get("scene_id"), ""),
            "chart_context": _to_text(item.get("chart_context"), ""),
            "anchor_time": _to_text(item.get("anchor_time"), ""),
            "ideal_entry_time": _to_text(item.get("ideal_entry_time"), ""),
            "ideal_exit_time": _to_text(item.get("ideal_exit_time"), ""),
            "manual_wait_teacher_label": _to_text(item.get("manual_wait_teacher_label"), ""),
            "review_status": _to_text(item.get("review_status"), ""),
        }
        for item in manual_subset_rows
    ]
    return {
        "contract_version": BREAKOUT_EXTERNAL_SOURCE_PRIORITY_VERSION,
        "job_id": _to_text(manifest.get("job_id"), ""),
        "queue_id": _to_text(manifest.get("queue_id"), ""),
        "symbol": _to_text(manifest.get("symbol"), ""),
        "request_scope": _to_text(row.get("request_scope"), ""),
        "request_start": _to_text(row.get("request_start"), ""),
        "request_end": _to_text(row.get("request_end"), ""),
        "coverage_state": _to_text(manifest.get("coverage_state"), ""),
        "coverage_gaps": coverage_gaps,
        "required_outputs": [
            "entry_decisions_scoped.csv rows covering the request window",
            "entry_decisions_scoped.detail.jsonl rows covering the same row keys",
            "timestamp coverage matching request window",
            "future bars source usable by build_replay_dataset",
        ],
        "preferred_source_kind": _to_text(row.get("recommended_source_kind"), ""),
        "reason_summary": _to_text(row.get("reason_summary"), ""),
        "source_episode_ids": source_episode_ids,
        "scene_ids": scene_ids,
        "chart_contexts": chart_contexts,
        "manual_targets": manual_targets,
        "replay_command": _to_text(manifest.get("replay_command"), ""),
    }


def _render_request_markdown(request_manifest: Mapping[str, Any]) -> str:
    lines = [
        "# Breakout External Source Request",
        "",
        f"- job_id: `{_to_text(request_manifest.get('job_id'), '')}`",
        f"- queue_id: `{_to_text(request_manifest.get('queue_id'), '')}`",
        f"- symbol: `{_to_text(request_manifest.get('symbol'), '')}`",
        f"- request_scope: `{_to_text(request_manifest.get('request_scope'), '')}`",
        f"- request_window: `{_to_text(request_manifest.get('request_start'), '')}` -> `{_to_text(request_manifest.get('request_end'), '')}`",
        f"- coverage_state: `{_to_text(request_manifest.get('coverage_state'), '')}`",
        f"- preferred_source_kind: `{_to_text(request_manifest.get('preferred_source_kind'), '')}`",
        f"- reason_summary: `{_to_text(request_manifest.get('reason_summary'), '')}`",
        "",
        "## Required Outputs",
        "",
    ]
    for item in list(request_manifest.get("required_outputs", []) or []):
        lines.append(f"- `{_to_text(item, '')}`")
    gaps = list(request_manifest.get("coverage_gaps", []) or [])
    if gaps:
        lines.extend(["", "## Missing Gaps", ""])
        for gap in gaps:
            if not isinstance(gap, Mapping):
                continue
            lines.append(
                f"- `{_to_text(gap.get('gap_start'), '')}` -> `{_to_text(gap.get('gap_end'), '')}`"
            )
    manual_targets = list(request_manifest.get("manual_targets", []) or [])
    if manual_targets:
        lines.extend(["", "## Manual Targets", ""])
        for target in manual_targets:
            if not isinstance(target, Mapping):
                continue
            lines.append(
                "- "
                f"`{_to_text(target.get('episode_id'), '')}` | "
                f"scene=`{_to_text(target.get('scene_id'), '')}` | "
                f"context=`{_to_text(target.get('chart_context'), '')}` | "
                f"anchor=`{_to_text(target.get('anchor_time'), '')}` | "
                f"entry=`{_to_text(target.get('ideal_entry_time'), '')}` | "
                f"exit=`{_to_text(target.get('ideal_exit_time'), '')}` | "
                f"label=`{_to_text(target.get('manual_wait_teacher_label'), '')}` | "
                f"review=`{_to_text(target.get('review_status'), '')}`"
            )
    replay_command = _to_text(request_manifest.get("replay_command"), "")
    if replay_command:
        lines.extend(["", "## Replay Command", "", f"```powershell\n{replay_command}\n```"])
    return "\n".join(lines).rstrip() + "\n"


def build_breakout_external_source_priority_report(
    *,
    manifest_rows: Sequence[Mapping[str, Any]] | None,
    scaffold_rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scaffold_case_counts = _load_scaffold_source_case_counts(scaffold_rows or [])
    rows: list[dict[str, Any]] = []
    for raw_manifest in manifest_rows or []:
        manifest = dict(raw_manifest or {})
        external_required = bool(manifest.get("external_source_required", False))
        if not external_required:
            continue
        coverage_state = _to_text(manifest.get("coverage_state"), "")
        request_scope = _request_scope(coverage_state)
        request_start, request_end, gap_count, gap_minutes = _gap_bounds(manifest)
        if request_scope == "full_window":
            request_start = _to_text(manifest.get("window_start"), request_start)
            request_end = _to_text(manifest.get("window_end"), request_end)
        manual_anchor_rows = _to_int(manifest.get("manual_anchor_rows"), 0)
        queue_id = _to_text(manifest.get("queue_id"), "")
        source_case_count = 0
        if queue_id.startswith("breakout_learning_recovery::"):
            source_case_count = manual_anchor_rows
        else:
            source_case_count = _to_int(scaffold_case_counts.get(queue_id, 0), 0)
        ready = bool(manifest.get("ready_for_replay_execution", False))
        priority_score = _priority_score(
            coverage_state=coverage_state,
            manual_anchor_rows=manual_anchor_rows,
            source_case_count=source_case_count,
            missing_gap_minutes=gap_minutes,
            ready_for_replay_execution=ready,
        )
        row = {
            "job_id": _to_text(manifest.get("job_id"), ""),
            "queue_id": queue_id,
            "symbol": _to_text(manifest.get("symbol"), ""),
            "priority": _to_text(manifest.get("priority"), ""),
            "recovery_type": _to_text(manifest.get("recovery_type"), ""),
            "coverage_state": coverage_state,
            "request_scope": request_scope,
            "request_start": request_start,
            "request_end": request_end,
            "missing_gap_count": int(gap_count),
            "missing_gap_minutes": round(float(gap_minutes), 3),
            "manual_anchor_rows": manual_anchor_rows,
            "source_case_count": int(source_case_count),
            "scoped_entry_row_count": _to_int(manifest.get("scoped_entry_row_count"), 0),
            "ready_for_replay_execution": ready,
            "external_source_required": external_required,
            "priority_score": float(priority_score),
            "recommended_source_kind": _recommended_source_kind(coverage_state),
            "reason_summary": (
                "manual_review_runtime_alignment_blocked_by_missing_source"
                if queue_id.startswith("breakout_learning_recovery::")
                else "accepted_manual_backfill_has_internal_gaps"
            ),
            "source_episode_ids": "",
            "scene_ids": "",
            "chart_contexts": "",
            "manual_targets_path": "",
            "job_manifest_path": _to_text(manifest.get("job_manifest_path", ""), ""),
            "request_manifest_path": "",
            "request_markdown_path": "",
        }
        rows.append(row)

    rows = sorted(
        rows,
        key=lambda item: (
            -float(item.get("priority_score", 0.0) or 0.0),
            _to_text(item.get("symbol"), ""),
            _to_text(item.get("request_start"), ""),
        ),
    )
    summary = {
        "contract_version": BREAKOUT_EXTERNAL_SOURCE_PRIORITY_VERSION,
        "row_count": int(len(rows)),
        "coverage_state_counts": {},
        "symbol_counts": {},
        "request_scope_counts": {},
        "ready_job_count": int(sum(1 for row in rows if _safe_bool(row.get("ready_for_replay_execution")))),
    }
    for row in rows:
        summary["coverage_state_counts"][_to_text(row.get("coverage_state"), "")] = int(
            summary["coverage_state_counts"].get(_to_text(row.get("coverage_state"), ""), 0)
        ) + 1
        summary["symbol_counts"][_to_text(row.get("symbol"), "")] = int(
            summary["symbol_counts"].get(_to_text(row.get("symbol"), ""), 0)
        ) + 1
        summary["request_scope_counts"][_to_text(row.get("request_scope"), "")] = int(
            summary["request_scope_counts"].get(_to_text(row.get("request_scope"), ""), 0)
        ) + 1
    return rows, summary


def render_breakout_external_source_priority_markdown(
    summary: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]] | None,
) -> str:
    lines = [
        "# Breakout External Source Priority",
        "",
        f"- version: `{_to_text(summary.get('contract_version'), '')}`",
        f"- row_count: `{_to_int(summary.get('row_count'), 0)}`",
        f"- coverage_state_counts: `{summary.get('coverage_state_counts', {})}`",
        f"- symbol_counts: `{summary.get('symbol_counts', {})}`",
        f"- request_scope_counts: `{summary.get('request_scope_counts', {})}`",
        "",
    ]
    for row in rows or []:
        lines.extend(
            [
                f"## {_to_text(row.get('job_id'), '')}",
                "",
                f"- symbol: `{_to_text(row.get('symbol'), '')}`",
                f"- coverage_state: `{_to_text(row.get('coverage_state'), '')}`",
                f"- request_scope: `{_to_text(row.get('request_scope'), '')}`",
                f"- request_window: `{_to_text(row.get('request_start'), '')}` -> `{_to_text(row.get('request_end'), '')}`",
                f"- missing_gap_minutes: `{_to_text(row.get('missing_gap_minutes'), '')}`",
                f"- manual_anchor_rows: `{_to_text(row.get('manual_anchor_rows'), '')}`",
                f"- reason_summary: `{_to_text(row.get('reason_summary'), '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_breakout_external_source_priority_report(
    *,
    bundle_root: str | Path | None = None,
    scaffold_csv_path: str | Path | None = None,
    csv_output_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> dict[str, Any]:
    bundle_root_path = _resolve_project_path(bundle_root, Path("data/backfill/breakout_event"))
    scaffold_csv = _resolve_project_path(
        scaffold_csv_path,
        Path("data/analysis/breakout_event/breakout_backfill_runner_scaffold_latest.csv"),
    )
    csv_output_file = _resolve_project_path(
        csv_output_path,
        Path("data/analysis/breakout_event/breakout_external_source_priority_latest.csv"),
    )
    json_output_file = _resolve_project_path(
        json_output_path,
        Path("data/analysis/breakout_event/breakout_external_source_priority_latest.json"),
    )
    markdown_output_file = _resolve_project_path(
        markdown_output_path,
        Path("data/analysis/breakout_event/breakout_external_source_priority_latest.md"),
    )

    manifest_rows: list[dict[str, Any]] = []
    for manifest_path in _discover_job_manifest_paths(bundle_root_path):
        manifest = _load_json(manifest_path)
        if not manifest:
            continue
        manifest["job_manifest_path"] = str(manifest_path)
        manifest_rows.append(manifest)
    scaffold_rows = _load_csv_rows(scaffold_csv)
    rows, summary = build_breakout_external_source_priority_report(
        manifest_rows=manifest_rows,
        scaffold_rows=scaffold_rows,
    )

    for row in rows:
        job_manifest_path = Path(_to_text(row.get("job_manifest_path"), ""))
        job_dir = job_manifest_path.parent if job_manifest_path.parent.exists() else bundle_root_path
        request_manifest_path = job_dir / "external_source_request_manifest.json"
        request_markdown_path = job_dir / "external_source_request.md"
        manual_targets_path = job_dir / "external_source_manual_targets.csv"
        manifest_payload = _request_manifest_payload(_load_json(job_manifest_path), row)
        request_manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        request_markdown_path.write_text(_render_request_markdown(manifest_payload), encoding="utf-8")
        manual_targets = list(manifest_payload.get("manual_targets", []) or [])
        with manual_targets_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "episode_id",
                    "scene_id",
                    "chart_context",
                    "anchor_time",
                    "ideal_entry_time",
                    "ideal_exit_time",
                    "manual_wait_teacher_label",
                    "review_status",
                ],
            )
            writer.writeheader()
            for target in manual_targets:
                if not isinstance(target, Mapping):
                    continue
                writer.writerow({field: _to_text(target.get(field), "") for field in writer.fieldnames or []})
        row["request_manifest_path"] = str(request_manifest_path)
        row["request_markdown_path"] = str(request_markdown_path)
        row["manual_targets_path"] = str(manual_targets_path)
        row["source_episode_ids"] = "|".join(list(manifest_payload.get("source_episode_ids", []) or []))
        row["scene_ids"] = "|".join(list(manifest_payload.get("scene_ids", []) or []))
        row["chart_contexts"] = "|".join(list(manifest_payload.get("chart_contexts", []) or []))

    csv_output_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_output_file.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BREAKOUT_EXTERNAL_SOURCE_PRIORITY_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in BREAKOUT_EXTERNAL_SOURCE_PRIORITY_COLUMNS})

    payload = {
        "summary": summary,
        "rows": rows,
        "bundle_root": str(bundle_root_path),
        "scaffold_csv_path": str(scaffold_csv),
    }
    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    json_output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_file.write_text(
        render_breakout_external_source_priority_markdown(summary, rows),
        encoding="utf-8",
    )
    return payload
