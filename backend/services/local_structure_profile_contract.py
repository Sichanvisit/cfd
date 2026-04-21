from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


LOCAL_STRUCTURE_PROFILE_CONTRACT_VERSION = "local_structure_profile_contract_v1"
LOCAL_STRUCTURE_SUMMARY_VERSION = "local_structure_summary_v1"
LOCAL_STRUCTURE_SWING_STATE_ENUM_V1 = ("INSUFFICIENT", "BROKEN", "FRAGILE", "HELD", "CLEAN_HELD")
LOCAL_STRUCTURE_BREAKOUT_HOLD_ENUM_V1 = ("INSUFFICIENT", "FAILED", "WEAK", "STABLE", "STRONG")
LOCAL_STRUCTURE_BODY_DRIVE_ENUM_V1 = ("COUNTER_DRIVE", "NEUTRAL", "WEAK_DRIVE", "STRONG_DRIVE")
LOCAL_STRUCTURE_BIAS_ENUM_V1 = ("CONTINUATION_FAVOR", "MIXED", "REVERSAL_FAVOR", "INSUFFICIENT")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_local_structure_profile_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": LOCAL_STRUCTURE_PROFILE_CONTRACT_VERSION,
        "status": "READY",
        "primary_axes_v1": [
            "few_candle_higher_low_state_v1",
            "few_candle_lower_high_state_v1",
            "breakout_hold_quality_v1",
            "body_drive_state_v1",
        ],
        "secondary_axes_deferred_v1": [
            "retest_quality_state_v1",
            "wick_rejection_state_v1",
            "few_candle_continuation_hint_v1",
            "few_candle_reversal_hint_v1",
        ],
        "swing_state_enum_v1": list(LOCAL_STRUCTURE_SWING_STATE_ENUM_V1),
        "breakout_hold_quality_enum_v1": list(LOCAL_STRUCTURE_BREAKOUT_HOLD_ENUM_V1),
        "body_drive_state_enum_v1": list(LOCAL_STRUCTURE_BODY_DRIVE_ENUM_V1),
        "structure_bias_enum_v1": list(LOCAL_STRUCTURE_BIAS_ENUM_V1),
        "description": (
            "Read-only local structure contract. Uses recent breakout/retest/hold proxies to surface "
            "few-candle continuation and reversal structure without changing execution."
        ),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _resolve_side_seed(row: Mapping[str, Any]) -> str:
    seed = _safe_text(row.get("state_strength_side_seed_v1")).upper()
    if seed in {"BULL", "BEAR"}:
        return seed
    overlay_direction = _safe_text(row.get("directional_continuation_overlay_direction")).upper()
    if overlay_direction == "UP":
        return "BULL"
    if overlay_direction == "DOWN":
        return "BEAR"
    return "NONE"


def _breakout_runtime(row: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(row.get("breakout_event_runtime_v1"))


def _breakout_hold_quality(row: Mapping[str, Any], *, side_seed: str) -> str:
    breakout_runtime = _breakout_runtime(row)
    hold_score = _safe_float(row.get("checkpoint_runtime_hold_quality_score"), 0.0)
    breakout_detected = _safe_bool(breakout_runtime.get("breakout_detected"))
    breakout_state = _safe_text(breakout_runtime.get("breakout_state")).lower()
    breakout_retest_status = _safe_text(breakout_runtime.get("breakout_retest_status")).lower()
    breakout_direction = _safe_text(breakout_runtime.get("breakout_direction")).upper()
    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()
    breakout_failure_risk = _safe_float(breakout_runtime.get("breakout_failure_risk"), 1.0)

    if side_seed == "NONE" and not breakout_detected and previous_box_break_state != "BREAKOUT_HELD":
        return "INSUFFICIENT"

    directional_match = (
        (side_seed == "BULL" and breakout_direction == "UP")
        or (side_seed == "BEAR" and breakout_direction == "DOWN")
        or previous_box_break_state == "BREAKOUT_HELD"
    )

    if not directional_match and breakout_failure_risk >= 0.6:
        return "FAILED"
    if previous_box_break_state == "BREAKOUT_HELD" and hold_score >= 0.55 and breakout_failure_risk < 0.45:
        if breakout_retest_status in {"passed", "none"} or "continuation" in breakout_state or "pullback" in breakout_state:
            return "STRONG"
    if hold_score >= 0.35 or breakout_retest_status == "passed":
        return "STABLE"
    if breakout_detected or hold_score >= 0.15:
        return "WEAK"
    return "FAILED"


def _body_drive_state(row: Mapping[str, Any], *, side_seed: str) -> str:
    breakout_runtime = _breakout_runtime(row)
    breakout_direction = _safe_text(breakout_runtime.get("breakout_direction")).upper()
    breakout_strength = _safe_float(breakout_runtime.get("breakout_strength"), 0.0)
    followthrough = _safe_float(breakout_runtime.get("breakout_followthrough_score"), 0.0)
    failure_risk = _safe_float(breakout_runtime.get("breakout_failure_risk"), 1.0)
    leg_direction = _safe_text(row.get("leg_direction")).upper()

    directional_match = (
        (side_seed == "BULL" and breakout_direction == "UP")
        or (side_seed == "BEAR" and breakout_direction == "DOWN")
        or (side_seed == "BULL" and breakout_direction == "NONE" and leg_direction == "UP")
        or (side_seed == "BEAR" and breakout_direction == "NONE" and leg_direction == "DOWN")
    )
    directional_counter = (
        (side_seed == "BULL" and breakout_direction == "DOWN")
        or (side_seed == "BEAR" and breakout_direction == "UP")
        or (side_seed == "BULL" and leg_direction == "DOWN")
        or (side_seed == "BEAR" and leg_direction == "UP")
    )

    strength = max(breakout_strength, followthrough)
    if directional_counter and failure_risk >= 0.5 and strength >= 0.2:
        return "COUNTER_DRIVE"
    if directional_match and strength >= 0.45 and failure_risk < 0.45:
        return "STRONG_DRIVE"
    if directional_match and strength >= 0.2:
        return "WEAK_DRIVE"
    return "NEUTRAL"


def _higher_low_state(row: Mapping[str, Any], *, side_seed: str, breakout_hold_quality: str, body_drive_state: str) -> str:
    low_retests = int(_safe_float(row.get("previous_box_low_retest_count"), 0.0))
    hold_score = _safe_float(row.get("checkpoint_runtime_hold_quality_score"), 0.0)
    previous_box_relation = _safe_text(row.get("previous_box_relation")).upper()
    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()

    if side_seed == "NONE":
        return "INSUFFICIENT"
    if side_seed == "BEAR":
        if breakout_hold_quality in {"FAILED"} or body_drive_state == "COUNTER_DRIVE":
            return "BROKEN"
        return "FRAGILE"

    if previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "ABOVE":
        if low_retests >= 2 and breakout_hold_quality in {"STRONG", "STABLE"} and hold_score >= 0.45:
            return "CLEAN_HELD"
        if low_retests >= 1 and breakout_hold_quality in {"STRONG", "STABLE"}:
            return "HELD"
        if breakout_hold_quality in {"WEAK", "STABLE"} or hold_score >= 0.2:
            return "FRAGILE"
    return "BROKEN"


def _lower_high_state(row: Mapping[str, Any], *, side_seed: str, breakout_hold_quality: str, body_drive_state: str) -> str:
    high_retests = int(_safe_float(row.get("previous_box_high_retest_count"), 0.0))
    hold_score = _safe_float(row.get("checkpoint_runtime_hold_quality_score"), 0.0)
    previous_box_relation = _safe_text(row.get("previous_box_relation")).upper()
    previous_box_break_state = _safe_text(row.get("previous_box_break_state")).upper()

    if side_seed == "NONE":
        return "INSUFFICIENT"
    if side_seed == "BULL":
        if breakout_hold_quality in {"FAILED"} or body_drive_state == "COUNTER_DRIVE":
            return "BROKEN"
        return "FRAGILE"

    if previous_box_break_state == "BREAKOUT_HELD" and previous_box_relation == "BELOW":
        if high_retests >= 2 and breakout_hold_quality in {"STRONG", "STABLE"} and hold_score >= 0.45:
            return "CLEAN_HELD"
        if high_retests >= 1 and breakout_hold_quality in {"STRONG", "STABLE"}:
            return "HELD"
        if breakout_hold_quality in {"WEAK", "STABLE"} or hold_score >= 0.2:
            return "FRAGILE"
    return "BROKEN"


def _structure_bias(*, side_seed: str, higher_low_state: str, lower_high_state: str, breakout_hold_quality: str, body_drive_state: str) -> str:
    if side_seed == "NONE":
        return "INSUFFICIENT"
    if side_seed == "BULL":
        if higher_low_state in {"HELD", "CLEAN_HELD"} and breakout_hold_quality in {"STABLE", "STRONG"} and body_drive_state in {"WEAK_DRIVE", "STRONG_DRIVE"}:
            return "CONTINUATION_FAVOR"
        if body_drive_state == "COUNTER_DRIVE" or breakout_hold_quality == "FAILED":
            return "REVERSAL_FAVOR"
        return "MIXED"
    if lower_high_state in {"HELD", "CLEAN_HELD"} and breakout_hold_quality in {"STABLE", "STRONG"} and body_drive_state in {"WEAK_DRIVE", "STRONG_DRIVE"}:
        return "CONTINUATION_FAVOR"
    if body_drive_state == "COUNTER_DRIVE" or breakout_hold_quality == "FAILED":
        return "REVERSAL_FAVOR"
    return "MIXED"


def _reason_summary(*, side_seed: str, higher_low_state: str, lower_high_state: str, breakout_hold_quality: str, body_drive_state: str, structure_bias: str) -> str:
    return (
        f"seed={side_seed}; "
        f"higher_low={higher_low_state}; "
        f"lower_high={lower_high_state}; "
        f"hold={breakout_hold_quality}; "
        f"drive={body_drive_state}; "
        f"bias={structure_bias}"
    )


def build_local_structure_profile_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    side_seed = _resolve_side_seed(payload)
    breakout_hold_quality = _breakout_hold_quality(payload, side_seed=side_seed)
    body_drive_state = _body_drive_state(payload, side_seed=side_seed)
    higher_low_state = _higher_low_state(
        payload,
        side_seed=side_seed,
        breakout_hold_quality=breakout_hold_quality,
        body_drive_state=body_drive_state,
    )
    lower_high_state = _lower_high_state(
        payload,
        side_seed=side_seed,
        breakout_hold_quality=breakout_hold_quality,
        body_drive_state=body_drive_state,
    )
    structure_bias = _structure_bias(
        side_seed=side_seed,
        higher_low_state=higher_low_state,
        lower_high_state=lower_high_state,
        breakout_hold_quality=breakout_hold_quality,
        body_drive_state=body_drive_state,
    )
    reason_summary = _reason_summary(
        side_seed=side_seed,
        higher_low_state=higher_low_state,
        lower_high_state=lower_high_state,
        breakout_hold_quality=breakout_hold_quality,
        body_drive_state=body_drive_state,
        structure_bias=structure_bias,
    )

    profile = {
        "contract_version": LOCAL_STRUCTURE_PROFILE_CONTRACT_VERSION,
        "few_candle_higher_low_state_v1": higher_low_state,
        "few_candle_lower_high_state_v1": lower_high_state,
        "breakout_hold_quality_v1": breakout_hold_quality,
        "body_drive_state_v1": body_drive_state,
        "few_candle_structure_bias_v1": structure_bias,
        "local_structure_reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "local_structure_profile_v1": profile,
        "few_candle_higher_low_state_v1": higher_low_state,
        "few_candle_lower_high_state_v1": lower_high_state,
        "breakout_hold_quality_v1": breakout_hold_quality,
        "body_drive_state_v1": body_drive_state,
        "few_candle_structure_bias_v1": structure_bias,
        "local_structure_reason_summary_v1": reason_summary,
    }


def attach_local_structure_profile_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_local_structure_profile_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_local_structure_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_local_structure_profile_fields_v1(latest_signal_by_symbol)
    higher_low_counts = Counter()
    lower_high_counts = Counter()
    hold_quality_counts = Counter()
    body_drive_counts = Counter()
    structure_bias_counts = Counter()

    for row in rows_by_symbol.values():
        higher_low_counts.update([_safe_text(row.get("few_candle_higher_low_state_v1"))])
        lower_high_counts.update([_safe_text(row.get("few_candle_lower_high_state_v1"))])
        hold_quality_counts.update([_safe_text(row.get("breakout_hold_quality_v1"))])
        body_drive_counts.update([_safe_text(row.get("body_drive_state_v1"))])
        structure_bias_counts.update([_safe_text(row.get("few_candle_structure_bias_v1"))])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if rows_by_symbol else "HOLD",
        "status_reasons": ["local_structure_surface_available"] if rows_by_symbol else ["no_runtime_rows"],
        "symbol_count": int(len(rows_by_symbol)),
        "higher_low_state_count_summary": dict(higher_low_counts),
        "lower_high_state_count_summary": dict(lower_high_counts),
        "breakout_hold_quality_count_summary": dict(hold_quality_counts),
        "body_drive_state_count_summary": dict(body_drive_counts),
        "structure_bias_count_summary": dict(structure_bias_counts),
    }
    return {
        "contract_version": LOCAL_STRUCTURE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_local_structure_summary_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Local Structure Summary",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        "",
        "## Breakout Hold Quality Count",
        "",
    ]
    for key, count in dict(summary.get("breakout_hold_quality_count_summary") or {}).items():
        lines.append(f"- `{key}`: {int(count or 0)}")
    lines.extend(["", "## Symbol Rows", ""])
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: higher_low={row.get('few_candle_higher_low_state_v1', '')} | "
            f"lower_high={row.get('few_candle_lower_high_state_v1', '')} | "
            f"hold={row.get('breakout_hold_quality_v1', '')} | "
            f"drive={row.get('body_drive_state_v1', '')} | "
            f"bias={row.get('few_candle_structure_bias_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_local_structure_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_local_structure_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "local_structure_summary_latest.json"
    md_path = output_dir / "local_structure_summary_latest.md"
    report["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, report)
    _write_text(md_path, render_local_structure_summary_markdown_v1(report))
    return report
