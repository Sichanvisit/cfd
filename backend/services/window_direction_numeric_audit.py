from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping


WINDOW_DIRECTION_NUMERIC_AUDIT_VERSION = "window_direction_numeric_audit_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _ratio(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _support_box_state(expected_direction: str) -> str:
    return "ABOVE" if expected_direction == "UP" else "BELOW"


def _support_bb_states(expected_direction: str) -> set[str]:
    if expected_direction == "UP":
        return {"UPPER_EDGE", "BREAKOUT", "UPPER"}
    return {"LOWER_EDGE", "BREAKOUT", "LOWER"}


def _opposite_side(expected_direction: str) -> str:
    return "SELL" if expected_direction == "UP" else "BUY"


def _continuation_reason_hint(value: str) -> bool:
    text = _text(value).lower()
    if not text:
        return False
    return any(
        token in text
        for token in (
            "checkpoint_continuation",
            "pullback_resume",
            "follow_through",
            "initial_break",
            "directional_continuation_overlay_structural_promotion",
        )
    )


def _iter_payload_rows(detail_path: Path, *, symbol: str, start: str, end: str) -> Iterable[dict[str, Any]]:
    if not detail_path.exists():
        return
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
            yield payload


def _build_window_report(spec: Mapping[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_direction = _text(spec.get("expected_direction")).upper() or "UP"
    total = len(rows)
    box_support_target = _support_box_state(expected_direction)
    bb_support_targets = _support_bb_states(expected_direction)
    opposite_side = _opposite_side(expected_direction)

    leg_match = sum(1 for row in rows if _text(row.get("leg_direction")).upper() == expected_direction)
    breakout_match = sum(
        1 for row in rows if _text(row.get("breakout_candidate_direction")).upper() == expected_direction
    )
    checkpoint_continuation = sum(
        1 for row in rows if _continuation_reason_hint(row.get("checkpoint_transition_reason"))
    )
    core_continuation = sum(
        1 for row in rows if _continuation_reason_hint(row.get("core_reason"))
    )
    box_support = sum(1 for row in rows if _text(row.get("box_state")).upper() == box_support_target)
    bb_support = sum(1 for row in rows if _text(row.get("bb_state")).upper() in bb_support_targets)
    consumer_opposite = sum(1 for row in rows if _text(row.get("consumer_check_side")).upper() == opposite_side)
    wait_bias = sum(
        1 for row in rows if _text(row.get("forecast_state25_candidate_wait_bias_action")) == "reinforce_wait_bias"
    )
    belief_reduce = sum(
        1 for row in rows if _text(row.get("belief_candidate_recommended_family")) == "reduce_alert"
    )
    barrier_block_or_wait = sum(
        1
        for row in rows
        if _text(row.get("barrier_candidate_recommended_family")) in {"block_bias", "wait_bias"}
    )

    leg_match_rate = _ratio(leg_match, total)
    breakout_match_rate = _ratio(breakout_match, total)
    checkpoint_continuation_rate = _ratio(checkpoint_continuation, total)
    core_continuation_rate = _ratio(core_continuation, total)
    box_support_rate = _ratio(box_support, total)
    bb_support_rate = _ratio(bb_support, total)
    consumer_opposite_rate = _ratio(consumer_opposite, total)
    wait_bias_rate = _ratio(wait_bias, total)
    belief_reduce_rate = _ratio(belief_reduce, total)
    barrier_block_or_wait_rate = _ratio(barrier_block_or_wait, total)

    structural_support_rate = round(
        mean(
            [
                leg_match_rate,
                breakout_match_rate,
                checkpoint_continuation_rate,
                box_support_rate,
                bb_support_rate,
            ]
        ),
        4,
    ) if total else 0.0
    caution_pressure_rate = round(
        mean(
            [
                consumer_opposite_rate,
                wait_bias_rate,
                belief_reduce_rate,
                barrier_block_or_wait_rate,
            ]
        ),
        4,
    ) if total else 0.0

    if total <= 0:
        calibration_state = "NO_DATA"
    elif structural_support_rate >= 0.85 and consumer_opposite_rate >= 0.7:
        calibration_state = "CONTINUATION_UNDER_VETO"
    elif structural_support_rate >= 0.65 and consumer_opposite_rate >= 0.5:
        calibration_state = "FRICTION_HEAVY"
    else:
        calibration_state = "MIXED"

    continuation_integrity_floor_hint = round(_clamp(structural_support_rate - 0.05, 0.4, 0.95), 4)
    reversal_evidence_ceiling_hint = round(_clamp(1.0 - structural_support_rate, 0.05, 0.45), 4)

    top_consumer_reasons = Counter(
        _text(row.get("consumer_check_reason")) for row in rows if _text(row.get("consumer_check_reason"))
    ).most_common(6)
    top_box_states = Counter(_text(row.get("box_state")).upper() for row in rows if _text(row.get("box_state"))).most_common(4)
    top_bb_states = Counter(_text(row.get("bb_state")).upper() for row in rows if _text(row.get("bb_state"))).most_common(4)

    return {
        "window_id": _text(spec.get("window_id")),
        "label": _text(spec.get("label")),
        "symbol": _text(spec.get("symbol")).upper(),
        "expected_direction": expected_direction,
        "start": _text(spec.get("start")),
        "end": _text(spec.get("end")),
        "row_count": total,
        "first_seen_at": _text(rows[0].get("time")) if rows else "",
        "last_seen_at": _text(rows[-1].get("time")) if rows else "",
        "metric_rates_v1": {
            "leg_direction_match_rate": leg_match_rate,
            "breakout_candidate_direction_match_rate": breakout_match_rate,
            "checkpoint_continuation_rate": checkpoint_continuation_rate,
            "core_continuation_reason_rate": core_continuation_rate,
            "box_support_rate": box_support_rate,
            "bb_support_rate": bb_support_rate,
            "consumer_opposite_side_rate": consumer_opposite_rate,
            "wait_bias_rate": wait_bias_rate,
            "belief_reduce_alert_rate": belief_reduce_rate,
            "barrier_block_or_wait_rate": barrier_block_or_wait_rate,
            "structural_support_rate": structural_support_rate,
            "caution_pressure_rate": caution_pressure_rate,
        },
        "candidate_threshold_hints_v1": {
            "continuation_integrity_floor_hint": continuation_integrity_floor_hint,
            "reversal_evidence_ceiling_hint": reversal_evidence_ceiling_hint,
            "consumer_veto_tier_hint": (
                "FRICTION_ONLY" if calibration_state == "CONTINUATION_UNDER_VETO"
                else "BOUNDARY_WARNING" if calibration_state == "FRICTION_HEAVY"
                else "MIXED_REVIEW"
            ),
            "caution_discount_candidate": calibration_state in {"CONTINUATION_UNDER_VETO", "FRICTION_HEAVY"},
            "calibration_state": calibration_state,
        },
        "top_consumer_reasons": top_consumer_reasons,
        "top_box_states": top_box_states,
        "top_bb_states": top_bb_states,
    }


def build_window_direction_numeric_audit(
    detail_path: str | Path,
    window_specs: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    resolved_path = Path(detail_path)
    windows: list[dict[str, Any]] = []
    for spec in list(window_specs or []):
        rows = list(
            _iter_payload_rows(
                resolved_path,
                symbol=_text(spec.get("symbol")).upper(),
                start=_text(spec.get("start")),
                end=_text(spec.get("end")),
            )
        )
        windows.append(_build_window_report(spec, rows))

    return {
        "contract_version": WINDOW_DIRECTION_NUMERIC_AUDIT_VERSION,
        "generated_at": _now_iso(),
        "detail_path": str(resolved_path),
        "window_count": len(windows),
        "windows": windows,
    }


def render_window_direction_numeric_audit_markdown(report: Mapping[str, Any] | None) -> str:
    payload = dict(report or {})
    lines = [
        "# Window Direction Numeric Audit",
        "",
        f"- generated_at: {_text(payload.get('generated_at'))}",
        f"- window_count: {int(payload.get('window_count') or 0)}",
        "",
    ]
    for window in list(payload.get("windows") or []):
        lines.extend(
            [
                f"## {_text(window.get('window_id'))} / {_text(window.get('symbol'))}",
                "",
                f"- label: {_text(window.get('label'))}",
                f"- expected_direction: {_text(window.get('expected_direction'))}",
                f"- window: {_text(window.get('start'))} ~ {_text(window.get('end'))}",
                f"- row_count: {int(window.get('row_count') or 0)}",
                f"- first_seen_at: {_text(window.get('first_seen_at'))}",
                f"- last_seen_at: {_text(window.get('last_seen_at'))}",
                f"- structural_support_rate: {window.get('metric_rates_v1', {}).get('structural_support_rate', 0.0)}",
                f"- caution_pressure_rate: {window.get('metric_rates_v1', {}).get('caution_pressure_rate', 0.0)}",
                f"- continuation_integrity_floor_hint: {window.get('candidate_threshold_hints_v1', {}).get('continuation_integrity_floor_hint', 0.0)}",
                f"- reversal_evidence_ceiling_hint: {window.get('candidate_threshold_hints_v1', {}).get('reversal_evidence_ceiling_hint', 0.0)}",
                f"- consumer_veto_tier_hint: {_text(window.get('candidate_threshold_hints_v1', {}).get('consumer_veto_tier_hint'))}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_window_direction_numeric_audit(
    detail_path: str | Path,
    window_specs: Iterable[Mapping[str, Any]],
    *,
    shadow_auto_dir: str | Path | None = None,
    output_stem: str = "window_direction_numeric_audit_latest",
) -> dict[str, Any]:
    report = build_window_direction_numeric_audit(detail_path, window_specs)
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir else _default_shadow_auto_dir()
    json_path = output_dir / f"{output_stem}.json"
    md_path = output_dir / f"{output_stem}.md"
    _write_json(json_path, report)
    _write_text(md_path, render_window_direction_numeric_audit_markdown(report))
    return {
        "report": report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
