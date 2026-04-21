from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


STATE_STRENGTH_S0_STABILITY_GUARD_VERSION = "state_strength_s0_stability_guard_v1"
STATE_STRENGTH_S0_DEFAULT_FRESHNESS_SEC = 900
STATE_STRENGTH_S0_DEPENDENCY_KEYS = (
    "runtime_signal_wiring_audit_summary_v1",
    "ca2_r0_stability_summary_v1",
    "ca2_session_split_summary_v1",
    "should_have_done_summary_v1",
    "canonical_surface_summary_v1",
    "session_bias_shadow_summary_v1",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _age_seconds_from_iso(value: Any, *, now_dt: datetime) -> float | None:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return None
    return max(0.0, (now_dt - parsed).total_seconds())


def _path_from_any(value: Any) -> Path | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        return Path(text)
    except Exception:
        return None


def _mtime_age_seconds(path: Path | None, *, now_dt: datetime) -> float | None:
    if path is None or not path.exists():
        return None
    try:
        return max(0.0, now_dt.timestamp() - path.stat().st_mtime)
    except Exception:
        return None


def _freshness_state(age_seconds: float | None, *, threshold_sec: int) -> str:
    if age_seconds is None:
        return "MISSING"
    if age_seconds <= float(max(int(threshold_sec), 1)):
        return "FRESH"
    return "STALE"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _build_dependency_state(
    dependency_key: str,
    report: Mapping[str, Any] | None,
    *,
    now_dt: datetime,
    freshness_threshold_sec: int,
) -> dict[str, Any]:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    artifact_paths = _mapping(payload.get("artifact_paths"))
    summary_present = bool(summary)
    summary_status = _safe_text(summary.get("status")).upper()
    summary_generated_at = _safe_text(summary.get("generated_at"))
    summary_age_seconds = _age_seconds_from_iso(summary_generated_at, now_dt=now_dt)
    summary_freshness_state = _freshness_state(
        summary_age_seconds,
        threshold_sec=freshness_threshold_sec,
    )

    json_path = _path_from_any(artifact_paths.get("json_path"))
    markdown_path = _path_from_any(artifact_paths.get("markdown_path"))
    artifact_paths_present = json_path is not None and markdown_path is not None
    json_exists = bool(json_path is not None and json_path.exists())
    markdown_exists = bool(markdown_path is not None and markdown_path.exists())
    artifact_files_exist = bool(json_exists and markdown_exists)
    json_age_seconds = _mtime_age_seconds(json_path, now_dt=now_dt)
    markdown_age_seconds = _mtime_age_seconds(markdown_path, now_dt=now_dt)
    artifact_age_candidates = [age for age in (json_age_seconds, markdown_age_seconds) if age is not None]
    artifact_age_seconds = max(artifact_age_candidates) if artifact_age_candidates else None
    artifact_freshness_state = _freshness_state(
        artifact_age_seconds,
        threshold_sec=freshness_threshold_sec,
    )

    reasons: list[str] = []
    if not summary_present:
        dependency_status = "BLOCKED"
        reasons.append("summary_missing")
    elif summary_status == "BLOCKED":
        dependency_status = "BLOCKED"
        reasons.append("upstream_blocked")
    else:
        dependency_status = "READY"
        if not summary_generated_at:
            dependency_status = "HOLD"
            reasons.append("summary_generated_at_missing")
        elif summary_freshness_state != "FRESH":
            dependency_status = "HOLD"
            reasons.append("summary_stale")
        if not artifact_paths_present:
            dependency_status = "HOLD"
            reasons.append("artifact_paths_missing")
        elif not artifact_files_exist:
            dependency_status = "HOLD"
            reasons.append("artifact_files_missing")
        elif artifact_freshness_state != "FRESH":
            dependency_status = "HOLD"
            reasons.append("artifact_stale")

    return {
        "dependency_key": dependency_key,
        "dependency_status": dependency_status,
        "dependency_reasons": reasons or ["stable"],
        "upstream_summary_status": summary_status,
        "summary_present": bool(summary_present),
        "summary_generated_at": summary_generated_at,
        "summary_freshness_state_v1": summary_freshness_state,
        "summary_age_seconds": (
            round(float(summary_age_seconds), 1) if summary_age_seconds is not None else None
        ),
        "artifact_paths_present": bool(artifact_paths_present),
        "artifact_files_exist": bool(artifact_files_exist),
        "artifact_freshness_state_v1": artifact_freshness_state,
        "artifact_age_seconds": (
            round(float(artifact_age_seconds), 1) if artifact_age_seconds is not None else None
        ),
        "artifact_paths": {
            "json_path": str(json_path) if json_path is not None else "",
            "markdown_path": str(markdown_path) if markdown_path is not None else "",
        },
    }


def build_state_strength_s0_stability_report_v1(
    *,
    runtime_signal_wiring_audit_report: Mapping[str, Any] | None = None,
    ca2_r0_stability_report: Mapping[str, Any] | None = None,
    ca2_session_split_report: Mapping[str, Any] | None = None,
    should_have_done_report: Mapping[str, Any] | None = None,
    canonical_surface_report: Mapping[str, Any] | None = None,
    session_bias_shadow_report: Mapping[str, Any] | None = None,
    freshness_threshold_sec: int = STATE_STRENGTH_S0_DEFAULT_FRESHNESS_SEC,
) -> dict[str, Any]:
    now_dt = _now()
    dependency_reports = {
        "runtime_signal_wiring_audit_summary_v1": runtime_signal_wiring_audit_report,
        "ca2_r0_stability_summary_v1": ca2_r0_stability_report,
        "ca2_session_split_summary_v1": ca2_session_split_report,
        "should_have_done_summary_v1": should_have_done_report,
        "canonical_surface_summary_v1": canonical_surface_report,
        "session_bias_shadow_summary_v1": session_bias_shadow_report,
    }

    dependencies = {
        key: _build_dependency_state(
            key,
            report,
            now_dt=now_dt,
            freshness_threshold_sec=freshness_threshold_sec,
        )
        for key, report in dependency_reports.items()
    }

    dependency_status_counter = Counter()
    upstream_status_counter = Counter()
    blocked_dependencies: list[str] = []
    hold_dependencies: list[str] = []
    summary_ready_count = 0
    artifact_ready_count = 0
    fresh_dependency_count = 0

    for key in STATE_STRENGTH_S0_DEPENDENCY_KEYS:
        state = _mapping(dependencies.get(key))
        dependency_status = _safe_text(state.get("dependency_status")).upper()
        upstream_status = _safe_text(state.get("upstream_summary_status")).upper()
        dependency_status_counter.update([dependency_status or "UNKNOWN"])
        if upstream_status:
            upstream_status_counter.update([upstream_status])
        if bool(state.get("summary_present")):
            summary_ready_count += 1
        if bool(state.get("artifact_files_exist")):
            artifact_ready_count += 1
        if dependency_status == "READY":
            fresh_dependency_count += 1
        elif dependency_status == "BLOCKED":
            blocked_dependencies.append(key)
        elif dependency_status == "HOLD":
            hold_dependencies.append(key)

    if blocked_dependencies:
        status = "BLOCKED"
        reasons = [f"blocked_dependency::{key}" for key in blocked_dependencies]
    elif hold_dependencies:
        status = "HOLD"
        reasons = [f"hold_dependency::{key}" for key in hold_dependencies]
    else:
        status = "READY"
        reasons = ["existing_instrumentation_stable"]

    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": reasons,
        "dependency_count": int(len(STATE_STRENGTH_S0_DEPENDENCY_KEYS)),
        "summary_ready_count": int(summary_ready_count),
        "artifact_ready_count": int(artifact_ready_count),
        "fresh_dependency_count": int(fresh_dependency_count),
        "dependency_status_count_summary": dict(dependency_status_counter),
        "upstream_status_count_summary": dict(upstream_status_counter),
        "blocked_dependency_keys": blocked_dependencies,
        "hold_dependency_keys": hold_dependencies,
        "freshness_threshold_sec": int(max(int(freshness_threshold_sec), 1)),
    }
    return {
        "contract_version": STATE_STRENGTH_S0_STABILITY_GUARD_VERSION,
        "summary": summary,
        "dependency_states_v1": dependencies,
    }


def render_state_strength_s0_stability_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    dependency_states = {
        key: _mapping(value)
        for key, value in dict(payload.get("dependency_states_v1") or {}).items()
    }
    lines = [
        "# State Strength S0 Stability Guard",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- status_reasons: `{', '.join(str(x) for x in list(summary.get('status_reasons') or []))}`",
        f"- dependency_count: `{_safe_int(summary.get('dependency_count'), 0)}`",
        f"- summary_ready_count: `{_safe_int(summary.get('summary_ready_count'), 0)}`",
        f"- artifact_ready_count: `{_safe_int(summary.get('artifact_ready_count'), 0)}`",
        f"- fresh_dependency_count: `{_safe_int(summary.get('fresh_dependency_count'), 0)}`",
        "",
        "## Dependencies",
        "",
    ]
    for key in STATE_STRENGTH_S0_DEPENDENCY_KEYS:
        state = dependency_states.get(key, {})
        reasons = ", ".join(str(x) for x in list(state.get("dependency_reasons") or []))
        lines.append(
            f"- `{key}`: dependency_status={state.get('dependency_status', '')} | "
            f"upstream_status={state.get('upstream_summary_status', '')} | "
            f"summary={state.get('summary_freshness_state_v1', '')} | "
            f"artifact={state.get('artifact_freshness_state_v1', '')} | "
            f"reasons={reasons}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_strength_s0_stability_report_v1(
    *,
    runtime_signal_wiring_audit_report: Mapping[str, Any] | None = None,
    ca2_r0_stability_report: Mapping[str, Any] | None = None,
    ca2_session_split_report: Mapping[str, Any] | None = None,
    should_have_done_report: Mapping[str, Any] | None = None,
    canonical_surface_report: Mapping[str, Any] | None = None,
    session_bias_shadow_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
    freshness_threshold_sec: int = STATE_STRENGTH_S0_DEFAULT_FRESHNESS_SEC,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_strength_s0_stability_report_v1(
        runtime_signal_wiring_audit_report=runtime_signal_wiring_audit_report,
        ca2_r0_stability_report=ca2_r0_stability_report,
        ca2_session_split_report=ca2_session_split_report,
        should_have_done_report=should_have_done_report,
        canonical_surface_report=canonical_surface_report,
        session_bias_shadow_report=session_bias_shadow_report,
        freshness_threshold_sec=freshness_threshold_sec,
    )
    json_path = output_dir / "state_strength_s0_stability_latest.json"
    md_path = output_dir / "state_strength_s0_stability_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_state_strength_s0_stability_markdown_v1(report))
    return report
