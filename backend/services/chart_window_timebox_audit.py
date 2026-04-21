from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


CHART_WINDOW_TIMEBOX_AUDIT_VERSION = "chart_window_timebox_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    return text in {"1", "true", "yes", "y"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _nested_execution_diff(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(payload.get("execution_action_diff_v1"))


def _nested_consumer_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(payload.get("consumer_check_state_v1"))


def _execution_value(payload: Mapping[str, Any], flat_key: str, nested_key: str) -> str:
    flat = _text(payload.get(flat_key))
    if flat:
        return flat
    return _text(_nested_execution_diff(payload).get(nested_key))


def _consumer_value(payload: Mapping[str, Any], flat_key: str, nested_key: str) -> str:
    flat = _text(payload.get(flat_key))
    if flat:
        return flat
    return _text(_nested_consumer_state(payload).get(nested_key))


def _normalize_actual_family(payload: Mapping[str, Any]) -> str:
    outcome = _text(payload.get("outcome")).lower()
    action = _text(payload.get("action")).upper()
    exec_final = _execution_value(payload, "execution_diff_final_action_side", "final_action_side").upper()
    overlay_kind = _text(
        payload.get("directional_continuation_overlay_event_kind_hint")
        or payload.get("chart_event_kind_hint")
    ).upper()
    check_side = _consumer_value(payload, "consumer_check_side", "check_side").upper()
    check_stage = _consumer_value(payload, "consumer_check_stage", "check_stage").upper()
    blocked_by = _text(payload.get("blocked_by")).lower()
    reason = _consumer_value(payload, "consumer_check_reason", "check_reason").lower()

    if outcome == "entered":
        effective = exec_final or action
        if effective in {"BUY", "SELL"}:
            return f"{effective}_ENTER"
    if overlay_kind:
        return overlay_kind
    if check_stage == "READY" and check_side in {"BUY", "SELL"}:
        return f"{check_side}_READY"
    if check_stage == "PROBE" and check_side in {"BUY", "SELL"}:
        return f"{check_side}_PROBE"
    if check_stage == "OBSERVE" and check_side in {"BUY", "SELL"}:
        return f"{check_side}_WATCH"
    if blocked_by or outcome == "skipped" or "observe" in reason:
        return "WAIT"
    return "NONE"


def _iter_window_rows(detail_path: Path, *, symbol: str, start: str, end: str) -> Iterable[dict[str, Any]]:
    symbol_upper = _text(symbol).upper()
    with detail_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                raw = json.loads(line)
            except Exception:
                continue
            payload = _mapping(raw.get("payload"))
            if _text(payload.get("symbol")).upper() != symbol_upper:
                continue
            time_text = _text(payload.get("time"))
            if not time_text or time_text < start or time_text > end:
                continue
            actual_family = _normalize_actual_family(payload)
            exec_final = _execution_value(
                payload,
                "execution_diff_final_action_side",
                "final_action_side",
            ).upper()
            row = {
                "time": time_text,
                "symbol": symbol_upper,
                "actual_family": actual_family,
                "action": _text(payload.get("action")).upper(),
                "outcome": _text(payload.get("outcome")).lower(),
                "consumer_check_side": _consumer_value(payload, "consumer_check_side", "check_side").upper(),
                "consumer_check_stage": _consumer_value(payload, "consumer_check_stage", "check_stage").upper(),
                "consumer_check_reason": _consumer_value(payload, "consumer_check_reason", "check_reason"),
                "blocked_by": _text(payload.get("blocked_by")),
                "overlay_direction": _text(payload.get("directional_continuation_overlay_direction")).upper(),
                "overlay_kind": _text(payload.get("directional_continuation_overlay_event_kind_hint")).upper(),
                "overlay_state": _text(payload.get("directional_continuation_overlay_selection_state")).upper(),
                "execution_diff_original_action_side": _execution_value(
                    payload,
                    "execution_diff_original_action_side",
                    "original_action_side",
                ).upper(),
                "execution_diff_guarded_action_side": _execution_value(
                    payload,
                    "execution_diff_guarded_action_side",
                    "guarded_action_side",
                ).upper(),
                "execution_diff_promoted_action_side": _execution_value(
                    payload,
                    "execution_diff_promoted_action_side",
                    "promoted_action_side",
                ).upper(),
                "execution_diff_final_action_side": exec_final,
                "execution_diff_changed": _bool(
                    payload.get("execution_diff_changed")
                    if "execution_diff_changed" in payload
                    else _nested_execution_diff(payload).get("action_changed")
                ),
            }
            yield row


def _segment_signature(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _text(row.get("actual_family")).upper(),
        _text(row.get("consumer_check_reason")),
        _text(row.get("execution_diff_final_action_side")).upper(),
    )


def _summarize_segments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    segments: list[dict[str, Any]] = []
    current_rows: list[dict[str, Any]] = []
    current_signature: tuple[str, str, str] | None = None
    for row in rows:
        signature = _segment_signature(row)
        if current_signature is None or signature == current_signature:
            current_signature = signature
            current_rows.append(row)
            continue
        segments.append(_build_segment(current_rows))
        current_signature = signature
        current_rows = [row]
    if current_rows:
        segments.append(_build_segment(current_rows))
    return segments


def _build_segment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    last = rows[-1]
    family_counts = Counter(_text(row.get("actual_family")).upper() for row in rows)
    final_counts = Counter(_text(row.get("execution_diff_final_action_side")).upper() or "NONE" for row in rows)
    return {
        "segment_start": _text(first.get("time")),
        "segment_end": _text(last.get("time")),
        "row_count": int(len(rows)),
        "actual_family": _text(first.get("actual_family")).upper(),
        "consumer_check_reason": _text(first.get("consumer_check_reason")),
        "final_action_side": _text(first.get("execution_diff_final_action_side")).upper(),
        "family_counts": dict(family_counts),
        "final_action_counts": dict(final_counts),
    }


def _phase_report(rows: list[dict[str, Any]], phase: Mapping[str, Any]) -> dict[str, Any]:
    phase_start = _text(phase.get("start"))
    phase_end = _text(phase.get("end"))
    preferred = {_text(value).upper() for value in list(phase.get("preferred_families") or []) if _text(value)}
    forbidden = {_text(value).upper() for value in list(phase.get("forbidden_families") or []) if _text(value)}
    phase_rows = [row for row in rows if phase_start <= _text(row.get("time")) <= phase_end]
    family_counts = Counter(_text(row.get("actual_family")).upper() for row in phase_rows)
    preferred_hits = sum(count for family, count in family_counts.items() if family in preferred)
    forbidden_hits = sum(count for family, count in family_counts.items() if family in forbidden)
    row_count = len(phase_rows)
    preferred_rate = round(preferred_hits / row_count, 4) if row_count else 0.0
    forbidden_rate = round(forbidden_hits / row_count, 4) if row_count else 0.0
    if row_count == 0:
        alignment = "NO_DATA"
    elif forbidden_hits == 0 and preferred_rate >= 0.6:
        alignment = "GOOD"
    elif forbidden_rate > preferred_rate:
        alignment = "MISMATCH"
    else:
        alignment = "MIXED"
    return {
        "phase_name": _text(phase.get("name")),
        "phase_note": _text(phase.get("note")),
        "start": phase_start,
        "end": phase_end,
        "row_count": int(row_count),
        "preferred_families": sorted(preferred),
        "forbidden_families": sorted(forbidden),
        "preferred_hit_count": int(preferred_hits),
        "forbidden_hit_count": int(forbidden_hits),
        "preferred_hit_rate": preferred_rate,
        "forbidden_hit_rate": forbidden_rate,
        "dominant_actual_families": family_counts.most_common(5),
        "alignment_state": alignment,
    }


def build_chart_window_timebox_audit(
    detail_path: str | Path,
    window_specs: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    resolved_path = Path(detail_path)
    windows: list[dict[str, Any]] = []
    for spec in list(window_specs or []):
        window_id = _text(spec.get("window_id")) or _text(spec.get("symbol")).lower()
        symbol = _text(spec.get("symbol")).upper()
        start = _text(spec.get("start"))
        end = _text(spec.get("end"))
        rows = list(_iter_window_rows(resolved_path, symbol=symbol, start=start, end=end))
        family_counts = Counter(_text(row.get("actual_family")).upper() for row in rows)
        reason_counts = Counter(_text(row.get("consumer_check_reason")) for row in rows if _text(row.get("consumer_check_reason")))
        phase_reports = [_phase_report(rows, phase) for phase in list(spec.get("expected_phases") or [])]
        windows.append(
            {
                "window_id": window_id,
                "symbol": symbol,
                "label": _text(spec.get("label")),
                "anchor_note": _text(spec.get("anchor_note")),
                "start": start,
                "end": end,
                "row_count": int(len(rows)),
                "top_actual_family_counts": family_counts.most_common(10),
                "top_consumer_reason_counts": reason_counts.most_common(10),
                "segments": _summarize_segments(rows),
                "expected_phase_reports": phase_reports,
                "sample_rows_head": rows[:5],
                "sample_rows_tail": rows[-5:],
            }
        )
    return {
        "contract_version": CHART_WINDOW_TIMEBOX_AUDIT_VERSION,
        "generated_at": _now_iso(),
        "detail_path": str(resolved_path),
        "windows": windows,
    }


def render_chart_window_timebox_audit_markdown(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    windows = list(payload.get("windows") or [])
    lines = [
        "# Chart Window Timebox Audit",
        "",
        f"- generated_at: `{_text(payload.get('generated_at'))}`",
        f"- detail_path: `{_text(payload.get('detail_path'))}`",
        "",
    ]
    if not windows:
        lines.append("- no windows")
        return "\n".join(lines).strip() + "\n"
    for window in windows:
        row = _mapping(window)
        lines.extend(
            [
                f"## {row.get('window_id','')}",
                "",
                f"- symbol: `{_text(row.get('symbol'))}`",
                f"- label: `{_text(row.get('label'))}`",
                f"- anchor_note: `{_text(row.get('anchor_note'))}`",
                f"- window: `{_text(row.get('start'))}` -> `{_text(row.get('end'))}`",
                f"- row_count: `{int(row.get('row_count', 0) or 0)}`",
                f"- top_actual_family_counts: `{row.get('top_actual_family_counts', [])}`",
                f"- top_consumer_reason_counts: `{row.get('top_consumer_reason_counts', [])}`",
                "",
                "### Expected Phase Reports",
                "",
            ]
        )
        phase_reports = list(row.get("expected_phase_reports") or [])
        if not phase_reports:
            lines.append("- none")
        for phase in phase_reports:
            phase_row = _mapping(phase)
            lines.append(
                f"- `{_text(phase_row.get('phase_name'))}` "
                f"({ _text(phase_row.get('start')) } -> { _text(phase_row.get('end')) }): "
                f"alignment={_text(phase_row.get('alignment_state'))}, "
                f"preferred={phase_row.get('preferred_hit_count', 0)}/{phase_row.get('row_count', 0)}, "
                f"forbidden={phase_row.get('forbidden_hit_count', 0)}/{phase_row.get('row_count', 0)}, "
                f"dominant={phase_row.get('dominant_actual_families', [])}"
            )
        lines.extend(
            [
                "",
                "### Segments",
                "",
            ]
        )
        segments = list(row.get("segments") or [])
        for segment in segments[:12]:
            seg = _mapping(segment)
            lines.append(
                f"- `{_text(seg.get('segment_start'))}` -> `{_text(seg.get('segment_end'))}` "
                f"| family={_text(seg.get('actual_family')).upper()} "
                f"| final={_text(seg.get('final_action_side')).upper() or 'NONE'} "
                f"| reason={_text(seg.get('consumer_check_reason'))} "
                f"| rows={int(seg.get('row_count', 0) or 0)}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_chart_window_timebox_audit(
    detail_path: str | Path,
    window_specs: Iterable[Mapping[str, Any]],
    *,
    shadow_auto_dir: str | Path | None = None,
    output_stem: str = "chart_window_timebox_audit_latest",
) -> dict[str, Any]:
    report = build_chart_window_timebox_audit(detail_path, window_specs)
    resolved_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    json_path = resolved_dir / f"{output_stem}.json"
    md_path = resolved_dir / f"{output_stem}.md"
    _write_json(json_path, report)
    _write_text(md_path, render_chart_window_timebox_audit_markdown(report))
    with_paths = dict(report)
    with_paths["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, with_paths)
    return with_paths
