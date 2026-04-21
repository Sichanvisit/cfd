from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.session_bucket_helper import SESSION_BUCKET_ENUM_V1


SESSION_AWARE_ANNOTATION_ACCURACY_CONTRACT_VERSION = "session_aware_annotation_accuracy_contract_v1"
SESSION_AWARE_ANNOTATION_ACCURACY_SUMMARY_VERSION = "session_aware_annotation_accuracy_summary_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_session_aware_annotation_accuracy_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SESSION_AWARE_ANNOTATION_ACCURACY_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only session-aware annotation accuracy summary. "
            "Direction accuracy is available immediately from R1; "
            "phase accuracy remains HOLD until labeled should-have-done annotations accumulate."
        ),
        "fields": [
            "direction_accuracy_by_session",
            "measured_count_by_session",
            "phase_accuracy_by_session",
            "phase_accuracy_data_status",
            "annotation_candidate_count_by_session",
            "runtime_execution_divergence_count_by_session",
            "session_difference_significance",
        ],
    }


def _build_empty_session_float_map() -> dict[str, float | None]:
    return {bucket: None for bucket in SESSION_BUCKET_ENUM_V1}


def _build_empty_session_int_map() -> dict[str, int]:
    return {bucket: 0 for bucket in SESSION_BUCKET_ENUM_V1}


def build_session_aware_annotation_accuracy_summary_v1(
    *,
    session_split_report: Mapping[str, Any] | None = None,
    should_have_done_report: Mapping[str, Any] | None = None,
    canonical_surface_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    session_split = _mapping(session_split_report)
    should_have_done = _mapping(should_have_done_report)
    canonical_surface = _mapping(canonical_surface_report)

    session_split_summary = _mapping(session_split.get("summary"))
    should_have_done_summary = _mapping(should_have_done.get("summary"))
    canonical_rows = {
        str(symbol): _mapping(row)
        for symbol, row in dict(canonical_surface.get("rows_by_symbol") or {}).items()
    }

    direction_accuracy_by_session = _build_empty_session_float_map()
    measured_count_by_session = _build_empty_session_int_map()
    for bucket in SESSION_BUCKET_ENUM_V1:
        direction_accuracy_by_session[bucket] = _mapping(
            session_split_summary.get("correct_rate_by_session")
        ).get(bucket)
        measured_count_by_session[bucket] = _safe_int(
            _mapping(session_split_summary.get("measured_count_by_session")).get(bucket),
            0,
        )

    annotation_candidate_count_by_session = _build_empty_session_int_map()
    for bucket, count in dict(should_have_done_summary.get("candidate_count_by_session") or {}).items():
        if bucket in annotation_candidate_count_by_session:
            annotation_candidate_count_by_session[bucket] = _safe_int(count, 0)

    runtime_execution_divergence_count_by_session = _build_empty_session_int_map()
    for row in canonical_rows.values():
        bucket = _safe_text(row.get("canonical_session_bucket_v1"))
        alignment = _safe_text(row.get("canonical_runtime_execution_alignment_v1"))
        if bucket in runtime_execution_divergence_count_by_session and alignment == "DIVERGED":
            runtime_execution_divergence_count_by_session[bucket] += 1

    phase_accuracy_by_session = _build_empty_session_float_map()
    phase_accuracy_data_status = "INSUFFICIENT_LABELED_ANNOTATIONS"

    has_direction_data = any(_safe_int(v, 0) > 0 for v in measured_count_by_session.values())
    has_labeled_phase_data = False
    if not has_direction_data:
        status = "BLOCKED"
        status_reasons = ["session_direction_accuracy_missing"]
    elif not has_labeled_phase_data:
        status = "HOLD"
        status_reasons = ["direction_ready_phase_pending"]
    else:
        status = "READY"
        status_reasons = ["session_annotation_accuracy_ready"]

    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": status_reasons,
        "direction_accuracy_by_session": direction_accuracy_by_session,
        "measured_count_by_session": measured_count_by_session,
        "phase_accuracy_by_session": phase_accuracy_by_session,
        "phase_accuracy_data_status": phase_accuracy_data_status,
        "annotation_candidate_count_by_session": annotation_candidate_count_by_session,
        "runtime_execution_divergence_count_by_session": runtime_execution_divergence_count_by_session,
        "session_difference_significance": _mapping(session_split_summary.get("session_difference_significance")),
    }
    return {
        "contract_version": SESSION_AWARE_ANNOTATION_ACCURACY_SUMMARY_VERSION,
        "summary": summary,
    }


def render_session_aware_annotation_accuracy_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Session-Aware Annotation Accuracy",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(x) for x in list(summary.get('status_reasons') or []))}`",
        f"- phase_accuracy_data_status: `{summary.get('phase_accuracy_data_status', '')}`",
        "",
        "## Direction Accuracy By Session",
        "",
    ]
    for bucket in SESSION_BUCKET_ENUM_V1:
        lines.append(
            f"- `{bucket}`: measured={_safe_int(_mapping(summary.get('measured_count_by_session')).get(bucket), 0)} "
            f"| direction_accuracy={_mapping(summary.get('direction_accuracy_by_session')).get(bucket)}"
        )
    lines.extend(["", "## Candidate / Divergence By Session", ""])
    for bucket in SESSION_BUCKET_ENUM_V1:
        lines.append(
            f"- `{bucket}`: candidates={_safe_int(_mapping(summary.get('annotation_candidate_count_by_session')).get(bucket), 0)} "
            f"| divergence={_safe_int(_mapping(summary.get('runtime_execution_divergence_count_by_session')).get(bucket), 0)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_session_aware_annotation_accuracy_v1(
    *,
    session_split_report: Mapping[str, Any] | None = None,
    should_have_done_report: Mapping[str, Any] | None = None,
    canonical_surface_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_session_aware_annotation_accuracy_summary_v1(
        session_split_report=session_split_report,
        should_have_done_report=should_have_done_report,
        canonical_surface_report=canonical_surface_report,
    )
    json_path = output_dir / "session_aware_annotation_accuracy_latest.json"
    md_path = output_dir / "session_aware_annotation_accuracy_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_session_aware_annotation_accuracy_markdown(report))
    return report
