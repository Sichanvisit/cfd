from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


IMPROVEMENT_DETECTOR_FEEDBACK_CONTRACT_VERSION = "improvement_detector_feedback_v0"
MANUAL_DETECT_FEEDBACK_COMMAND = "/detect_feedback"

DETECTOR_FEEDBACK_CONFIRMED = "confirmed"
DETECTOR_FEEDBACK_OVERSENSITIVE = "oversensitive"
DETECTOR_FEEDBACK_MISSED = "missed"
DETECTOR_FEEDBACK_AMBIGUOUS = "ambiguous"

DETECTOR_FEEDBACK_VERDICTS = (
    DETECTOR_FEEDBACK_CONFIRMED,
    DETECTOR_FEEDBACK_OVERSENSITIVE,
    DETECTOR_FEEDBACK_MISSED,
    DETECTOR_FEEDBACK_AMBIGUOUS,
)

DETECTOR_NARROWING_NEUTRAL = "NEUTRAL"
DETECTOR_NARROWING_KEEP = "KEEP"
DETECTOR_NARROWING_PROMOTE = "PROMOTE"
DETECTOR_NARROWING_CAUTION = "CAUTION"
DETECTOR_NARROWING_SUPPRESS = "SUPPRESS"

_DETECTOR_FEEDBACK_TOKEN_MAP = {
    "맞았음": DETECTOR_FEEDBACK_CONFIRMED,
    "맞음": DETECTOR_FEEDBACK_CONFIRMED,
    "confirmed": DETECTOR_FEEDBACK_CONFIRMED,
    "confirm": DETECTOR_FEEDBACK_CONFIRMED,
    "과민했음": DETECTOR_FEEDBACK_OVERSENSITIVE,
    "과민": DETECTOR_FEEDBACK_OVERSENSITIVE,
    "oversensitive": DETECTOR_FEEDBACK_OVERSENSITIVE,
    "over": DETECTOR_FEEDBACK_OVERSENSITIVE,
    "놓쳤음": DETECTOR_FEEDBACK_MISSED,
    "놓침": DETECTOR_FEEDBACK_MISSED,
    "missed": DETECTOR_FEEDBACK_MISSED,
    "miss": DETECTOR_FEEDBACK_MISSED,
    "애매함": DETECTOR_FEEDBACK_AMBIGUOUS,
    "애매": DETECTOR_FEEDBACK_AMBIGUOUS,
    "ambiguous": DETECTOR_FEEDBACK_AMBIGUOUS,
    "maybe": DETECTOR_FEEDBACK_AMBIGUOUS,
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def normalize_detector_feedback_verdict(value: object) -> str:
    text = _text(value).lower()
    if not text:
        return ""
    return _DETECTOR_FEEDBACK_TOKEN_MAP.get(text, "")


def detector_feedback_verdict_label_ko(value: object) -> str:
    verdict = normalize_detector_feedback_verdict(value) or _text(value)
    mapping = {
        DETECTOR_FEEDBACK_CONFIRMED: "맞았음",
        DETECTOR_FEEDBACK_OVERSENSITIVE: "과민했음",
        DETECTOR_FEEDBACK_MISSED: "놓쳤음",
        DETECTOR_FEEDBACK_AMBIGUOUS: "애매함",
    }
    return _text(mapping.get(verdict), verdict or "-")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_improvement_detector_feedback_paths() -> tuple[Path, Path]:
    directory = _repo_root() / "data" / "analysis" / "shadow_auto"
    return (
        directory / "improvement_detector_feedback_latest.json",
        directory / "improvement_detector_feedback_latest.md",
    )


def default_improvement_detector_confusion_paths() -> tuple[Path, Path]:
    directory = _repo_root() / "data" / "analysis" / "shadow_auto"
    return (
        directory / "improvement_detector_confusion_latest.json",
        directory / "improvement_detector_confusion_latest.md",
    )


def build_detector_feedback_scope_key(
    *,
    detector_key: object,
    symbol: object,
    summary_ko: object,
) -> str:
    detector = _text(detector_key).strip().lower() or "unknown"
    symbol_text = _text(symbol).strip().upper() or "ALL"
    summary = _text(summary_ko).strip().lower() or "unspecified"
    normalized_summary = "_".join(summary.replace("/", " ").replace("|", " ").split())[:96] or "unspecified"
    return f"{detector}::{symbol_text}::{normalized_summary}"


def _empty_verdict_counts() -> dict[str, int]:
    return {verdict_name: 0 for verdict_name in DETECTOR_FEEDBACK_VERDICTS}


def find_detect_issue_ref(
    latest_issue_refs: list[Mapping[str, Any]] | None,
    issue_ref_token: object,
) -> dict[str, Any]:
    token = _text(issue_ref_token).strip()
    if not token:
        return {}
    normalized = token.upper()
    normalized_index = normalized[1:] if normalized.startswith("D") else normalized
    for raw_issue in list(latest_issue_refs or []):
        issue = _mapping(raw_issue)
        feedback_ref = _text(issue.get("feedback_ref")).upper()
        feedback_key = _text(issue.get("feedback_key"))
        if normalized == feedback_ref:
            return issue
        if normalized_index and feedback_ref == f"D{normalized_index}":
            return issue
        if token == feedback_key:
            return issue
    return {}


def build_detector_feedback_entry(
    *,
    issue_ref: Mapping[str, Any],
    verdict: str,
    user_id: object,
    username: object,
    note: object = "",
    proposal_id: object = "",
    now_ts: object = "",
) -> dict[str, Any]:
    normalized_verdict = normalize_detector_feedback_verdict(verdict)
    if not normalized_verdict:
        raise ValueError("invalid_detector_feedback_verdict")
    issue = _mapping(issue_ref)
    feedback_scope_key = _text(issue.get("feedback_scope_key")) or build_detector_feedback_scope_key(
        detector_key=issue.get("detector_key"),
        symbol=issue.get("symbol"),
        summary_ko=issue.get("summary_ko"),
    )
    return {
        "feedback_at": _text(now_ts, _now_iso()),
        "proposal_id": _text(proposal_id),
        "feedback_ref": _text(issue.get("feedback_ref")),
        "feedback_key": _text(issue.get("feedback_key")),
        "feedback_scope_key": feedback_scope_key,
        "detector_key": _text(issue.get("detector_key")),
        "symbol": _text(issue.get("symbol")).upper(),
        "summary_ko": _text(issue.get("summary_ko")),
        "verdict": normalized_verdict,
        "verdict_label_ko": detector_feedback_verdict_label_ko(normalized_verdict),
        "telegram_user_id": _text(user_id),
        "telegram_username": _text(username),
        "note": _text(note),
    }


def build_detector_feedback_snapshot(
    feedback_entries: list[Mapping[str, Any]] | None,
    latest_issue_refs: list[Mapping[str, Any]] | None = None,
    *,
    now_ts: object = "",
) -> dict[str, Any]:
    entries = [_mapping(row) for row in list(feedback_entries or []) if _mapping(row)]
    latest = [_mapping(row) for row in list(latest_issue_refs or []) if _mapping(row)]
    counts_by_verdict = {verdict: 0 for verdict in DETECTOR_FEEDBACK_VERDICTS}
    counts_by_detector: dict[str, dict[str, int]] = {}
    latest_by_key: dict[str, dict[str, Any]] = {}

    for entry in entries:
        verdict = normalize_detector_feedback_verdict(entry.get("verdict"))
        detector_key = _text(entry.get("detector_key"))
        feedback_key = _text(entry.get("feedback_key"))
        if verdict:
            counts_by_verdict[verdict] = counts_by_verdict.get(verdict, 0) + 1
        if detector_key:
            detector_bucket = counts_by_detector.setdefault(
                detector_key,
                {verdict_name: 0 for verdict_name in DETECTOR_FEEDBACK_VERDICTS},
            )
            if verdict:
                detector_bucket[verdict] = detector_bucket.get(verdict, 0) + 1
        if feedback_key:
            current = latest_by_key.get(feedback_key)
            if current is None or _text(entry.get("feedback_at")) >= _text(current.get("feedback_at")):
                latest_by_key[feedback_key] = dict(entry)

    issue_rows: list[dict[str, Any]] = []
    for issue in latest:
        feedback_key = _text(issue.get("feedback_key"))
        feedback_scope_key = _text(issue.get("feedback_scope_key")) or build_detector_feedback_scope_key(
            detector_key=issue.get("detector_key"),
            symbol=issue.get("symbol"),
            summary_ko=issue.get("summary_ko"),
        )
        latest_entry = _mapping(latest_by_key.get(feedback_key))
        issue_rows.append(
            {
                "feedback_ref": _text(issue.get("feedback_ref")),
                "feedback_key": feedback_key,
                "feedback_scope_key": feedback_scope_key,
                "detector_key": _text(issue.get("detector_key")),
                "symbol": _text(issue.get("symbol")).upper(),
                "summary_ko": _text(issue.get("summary_ko")),
                "latest_verdict": _text(latest_entry.get("verdict")),
                "latest_verdict_label_ko": detector_feedback_verdict_label_ko(latest_entry.get("verdict")),
                "latest_feedback_at": _text(latest_entry.get("feedback_at")),
                "latest_note": _text(latest_entry.get("note")),
            }
        )

    report_lines = [
        f"누적 피드백: {len(entries)}건",
        "verdict 요약:",
        f"- 맞았음: {counts_by_verdict.get(DETECTOR_FEEDBACK_CONFIRMED, 0)}건",
        f"- 과민했음: {counts_by_verdict.get(DETECTOR_FEEDBACK_OVERSENSITIVE, 0)}건",
        f"- 놓쳤음: {counts_by_verdict.get(DETECTOR_FEEDBACK_MISSED, 0)}건",
        f"- 애매함: {counts_by_verdict.get(DETECTOR_FEEDBACK_AMBIGUOUS, 0)}건",
    ]
    if issue_rows:
        report_lines.append("")
        report_lines.append("latest refs:")
        for row in issue_rows[:10]:
            report_lines.append(
                f"- {_text(row.get('feedback_ref'))} | {_text(row.get('summary_ko'))} | latest={_text(row.get('latest_verdict_label_ko'), '-')}"
            )

    return {
        "contract_version": IMPROVEMENT_DETECTOR_FEEDBACK_CONTRACT_VERSION,
        "generated_at": _text(now_ts, _now_iso()),
        "feedback_entry_count": len(entries),
        "latest_issue_ref_count": len(issue_rows),
        "counts_by_verdict": counts_by_verdict,
        "counts_by_detector": counts_by_detector,
        "latest_issue_feedback": issue_rows,
        "report_lines_ko": report_lines,
    }


def build_detector_feedback_narrowing_index(
    feedback_entries: list[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw_entry in list(feedback_entries or []):
        entry = _mapping(raw_entry)
        detector_key = _text(entry.get("detector_key"))
        symbol = _text(entry.get("symbol")).upper()
        summary_ko = _text(entry.get("summary_ko"))
        scope_key = _text(entry.get("feedback_scope_key")) or build_detector_feedback_scope_key(
            detector_key=detector_key,
            symbol=symbol,
            summary_ko=summary_ko,
        )
        verdict = normalize_detector_feedback_verdict(entry.get("verdict"))
        bucket = index.setdefault(
            scope_key,
            {
                "feedback_scope_key": scope_key,
                "detector_key": detector_key,
                "symbol": symbol,
                "summary_ko": summary_ko,
                "counts": _empty_verdict_counts(),
                "total_feedback": 0,
                "latest_feedback_at": "",
                "latest_verdict": "",
                "latest_note": "",
            },
        )
        if verdict:
            bucket["counts"][verdict] = _to_int(bucket["counts"].get(verdict)) + 1
        bucket["total_feedback"] = _to_int(bucket.get("total_feedback")) + 1
        feedback_at = _text(entry.get("feedback_at"))
        if feedback_at >= _text(bucket.get("latest_feedback_at")):
            bucket["latest_feedback_at"] = feedback_at
            bucket["latest_verdict"] = verdict
            bucket["latest_note"] = _text(entry.get("note"))
    return index


def evaluate_detector_feedback_narrowing(profile: Mapping[str, Any] | None) -> str:
    bucket = _mapping(profile)
    counts = _mapping(bucket.get("counts"))
    confirmed = _to_int(counts.get(DETECTOR_FEEDBACK_CONFIRMED))
    oversensitive = _to_int(counts.get(DETECTOR_FEEDBACK_OVERSENSITIVE))
    missed = _to_int(counts.get(DETECTOR_FEEDBACK_MISSED))
    positives = confirmed + missed
    if oversensitive >= 2 and positives == 0:
        return DETECTOR_NARROWING_SUPPRESS
    if oversensitive >= 2 and oversensitive > positives:
        return DETECTOR_NARROWING_CAUTION
    if positives >= 2 and oversensitive == 0:
        return DETECTOR_NARROWING_PROMOTE
    if positives >= 1:
        return DETECTOR_NARROWING_KEEP
    return DETECTOR_NARROWING_NEUTRAL


def detector_narrowing_label_ko(value: object) -> str:
    mapping = {
        DETECTOR_NARROWING_NEUTRAL: "중립",
        DETECTOR_NARROWING_KEEP: "유지",
        DETECTOR_NARROWING_PROMOTE: "우선 승격",
        DETECTOR_NARROWING_CAUTION: "주의 유지",
        DETECTOR_NARROWING_SUPPRESS: "surface 억제",
    }
    return _text(mapping.get(_text(value).upper()), _text(value, "-"))


def build_detector_confusion_snapshot(
    feedback_entries: list[Mapping[str, Any]] | None,
    latest_issue_refs: list[Mapping[str, Any]] | None = None,
    *,
    now_ts: object = "",
) -> dict[str, Any]:
    entries = [_mapping(row) for row in list(feedback_entries or []) if _mapping(row)]
    latest = [_mapping(row) for row in list(latest_issue_refs or []) if _mapping(row)]
    verdict_totals = _empty_verdict_counts()
    detector_rows_map: dict[str, dict[str, Any]] = {}
    narrowing_index = build_detector_feedback_narrowing_index(entries)
    latest_by_scope: dict[str, dict[str, Any]] = {}

    for entry in entries:
        verdict = normalize_detector_feedback_verdict(entry.get("verdict"))
        detector_key = _text(entry.get("detector_key"))
        scope_key = _text(entry.get("feedback_scope_key")) or build_detector_feedback_scope_key(
            detector_key=detector_key,
            symbol=entry.get("symbol"),
            summary_ko=entry.get("summary_ko"),
        )
        if verdict:
            verdict_totals[verdict] = _to_int(verdict_totals.get(verdict)) + 1
        if detector_key:
            detector_bucket = detector_rows_map.setdefault(
                detector_key,
                {
                    "detector_key": detector_key,
                    "counts": _empty_verdict_counts(),
                    "total_feedback": 0,
                },
            )
            if verdict:
                detector_bucket["counts"][verdict] = _to_int(detector_bucket["counts"].get(verdict)) + 1
            detector_bucket["total_feedback"] = _to_int(detector_bucket.get("total_feedback")) + 1
        current_latest = latest_by_scope.get(scope_key)
        if current_latest is None or _text(entry.get("feedback_at")) >= _text(current_latest.get("feedback_at")):
            latest_by_scope[scope_key] = dict(entry)

    scope_rows: list[dict[str, Any]] = []
    for scope_key, profile in narrowing_index.items():
        profile_map = _mapping(profile)
        latest_entry = _mapping(latest_by_scope.get(scope_key))
        counts = _mapping(profile_map.get("counts"))
        scope_rows.append(
            {
                "feedback_scope_key": scope_key,
                "detector_key": _text(profile_map.get("detector_key")),
                "symbol": _text(profile_map.get("symbol")).upper(),
                "summary_ko": _text(profile_map.get("summary_ko")),
                "total_feedback": _to_int(profile_map.get("total_feedback")),
                "confirmed_count": _to_int(counts.get(DETECTOR_FEEDBACK_CONFIRMED)),
                "oversensitive_count": _to_int(counts.get(DETECTOR_FEEDBACK_OVERSENSITIVE)),
                "missed_count": _to_int(counts.get(DETECTOR_FEEDBACK_MISSED)),
                "ambiguous_count": _to_int(counts.get(DETECTOR_FEEDBACK_AMBIGUOUS)),
                "latest_feedback_at": _text(profile_map.get("latest_feedback_at")),
                "latest_verdict": _text(latest_entry.get("verdict") or profile_map.get("latest_verdict")),
                "latest_verdict_label_ko": detector_feedback_verdict_label_ko(
                    latest_entry.get("verdict") or profile_map.get("latest_verdict")
                ),
                "narrowing_decision": evaluate_detector_feedback_narrowing(profile_map),
                "narrowing_label_ko": detector_narrowing_label_ko(evaluate_detector_feedback_narrowing(profile_map)),
            }
        )
    scope_rows.sort(
        key=lambda row: (
            _text(_mapping(row).get("latest_feedback_at")),
            _to_int(_mapping(row).get("total_feedback")),
        ),
        reverse=True,
    )

    detector_rows: list[dict[str, Any]] = []
    for detector_key, profile in sorted(detector_rows_map.items()):
        counts = _mapping(profile.get("counts"))
        detector_rows.append(
            {
                "detector_key": detector_key,
                "total_feedback": _to_int(profile.get("total_feedback")),
                "confirmed_count": _to_int(counts.get(DETECTOR_FEEDBACK_CONFIRMED)),
                "oversensitive_count": _to_int(counts.get(DETECTOR_FEEDBACK_OVERSENSITIVE)),
                "missed_count": _to_int(counts.get(DETECTOR_FEEDBACK_MISSED)),
                "ambiguous_count": _to_int(counts.get(DETECTOR_FEEDBACK_AMBIGUOUS)),
            }
        )

    latest_issue_rows: list[dict[str, Any]] = []
    for raw_issue in latest:
        issue = _mapping(raw_issue)
        scope_key = _text(issue.get("feedback_scope_key")) or build_detector_feedback_scope_key(
            detector_key=issue.get("detector_key"),
            symbol=issue.get("symbol"),
            summary_ko=issue.get("summary_ko"),
        )
        matching_scope = next((row for row in scope_rows if _text(row.get("feedback_scope_key")) == scope_key), {})
        latest_issue_rows.append(
            {
                "feedback_ref": _text(issue.get("feedback_ref")),
                "feedback_key": _text(issue.get("feedback_key")),
                "feedback_scope_key": scope_key,
                "detector_key": _text(issue.get("detector_key")),
                "symbol": _text(issue.get("symbol")).upper(),
                "summary_ko": _text(issue.get("summary_ko")),
                "narrowing_decision": _text(_mapping(matching_scope).get("narrowing_decision")),
                "narrowing_label_ko": _text(_mapping(matching_scope).get("narrowing_label_ko")),
                "latest_verdict_label_ko": _text(_mapping(matching_scope).get("latest_verdict_label_ko")),
            }
        )

    report_lines = [
        f"누적 피드백 {len(entries)}건",
        f"- 맞았음: {_to_int(verdict_totals.get(DETECTOR_FEEDBACK_CONFIRMED))}건",
        f"- 과민했음: {_to_int(verdict_totals.get(DETECTOR_FEEDBACK_OVERSENSITIVE))}건",
        f"- 놓쳤음: {_to_int(verdict_totals.get(DETECTOR_FEEDBACK_MISSED))}건",
        f"- 애매함: {_to_int(verdict_totals.get(DETECTOR_FEEDBACK_AMBIGUOUS))}건",
    ]
    if scope_rows:
        report_lines.append("")
        report_lines.append("feedback-aware narrowing:")
        for row in scope_rows[:8]:
            report_lines.append(
                f"- {_text(row.get('symbol'), 'ALL')} / {_text(row.get('summary_ko'))} | "
                f"{_text(row.get('narrowing_label_ko'))} | "
                f"맞음 {_to_int(row.get('confirmed_count'))} / 과민 {_to_int(row.get('oversensitive_count'))} / 놓침 {_to_int(row.get('missed_count'))}"
            )

    return {
        "contract_version": "improvement_detector_confusion_v0",
        "generated_at": _text(now_ts, _now_iso()),
        "feedback_entry_count": len(entries),
        "latest_issue_ref_count": len(latest_issue_rows),
        "verdict_totals": verdict_totals,
        "detector_rows": detector_rows,
        "scope_rows": scope_rows,
        "latest_issue_rows": latest_issue_rows,
        "report_lines_ko": report_lines,
    }


def render_detector_feedback_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Improvement Detector Feedback Snapshot",
        "",
        f"- contract_version: `{_text(_mapping(payload).get('contract_version'))}`",
        f"- generated_at: `{_text(_mapping(payload).get('generated_at'))}`",
        f"- feedback_entry_count: `{_to_int(_mapping(payload).get('feedback_entry_count'))}`",
        f"- latest_issue_ref_count: `{_to_int(_mapping(payload).get('latest_issue_ref_count'))}`",
        "",
        "## Report",
    ]
    for row in list(_mapping(payload).get("report_lines_ko") or []):
        lines.append(f"- {_text(row)}")
    return "\n".join(lines)


def write_detector_feedback_snapshot(
    payload: Mapping[str, Any],
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    default_json_path, default_markdown_path = default_improvement_detector_feedback_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_detector_feedback_markdown(payload),
        encoding="utf-8",
    )
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }


def render_detector_confusion_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Improvement Detector Confusion Snapshot",
        "",
        f"- contract_version: `{_text(_mapping(payload).get('contract_version'))}`",
        f"- generated_at: `{_text(_mapping(payload).get('generated_at'))}`",
        f"- feedback_entry_count: `{_to_int(_mapping(payload).get('feedback_entry_count'))}`",
        f"- latest_issue_ref_count: `{_to_int(_mapping(payload).get('latest_issue_ref_count'))}`",
        "",
        "## Report",
    ]
    for row in list(_mapping(payload).get("report_lines_ko") or []):
        lines.append(f"- {_text(row)}")
    return "\n".join(lines)


def write_detector_confusion_snapshot(
    payload: Mapping[str, Any],
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    default_json_path, default_markdown_path = default_improvement_detector_confusion_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_detector_confusion_markdown(payload),
        encoding="utf-8",
    )
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
