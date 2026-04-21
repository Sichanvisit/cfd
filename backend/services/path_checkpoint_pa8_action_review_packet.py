from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def default_checkpoint_pa8_action_review_packet_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_action_review_packet_latest.json"
    )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _loads_counts(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    text = _to_text(value)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _rows_by_symbol(payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    body = _mapping(payload)
    rows = body.get("rows")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        symbol = _to_text(row.get("symbol")).upper()
        if symbol:
            result[symbol] = dict(row)
    return result


def _build_symbol_review_focuses(
    *,
    runtime_proxy_match_rate: float,
    hold_precision: float,
    partial_then_hold_quality: float,
    full_exit_precision: float,
    resolved_row_count: int,
    live_runner_source_row_count: int,
    action_eval_focus: str,
    management_focus: str,
    observation_focus: str,
) -> list[str]:
    focuses: list[str] = []
    if runtime_proxy_match_rate < 0.90:
        focuses.append("inspect_runtime_proxy_alignment")
    if hold_precision < 0.80:
        focuses.append("inspect_hold_precision_boundary")
    if partial_then_hold_quality < 0.95:
        focuses.append("inspect_partial_then_hold_boundary")
    if full_exit_precision < 0.99:
        focuses.append("inspect_full_exit_guard")
    if resolved_row_count < 500:
        focuses.append("collect_more_symbol_rows")
    if live_runner_source_row_count < 100:
        focuses.append("collect_more_live_runner_rows")
    for extra in (action_eval_focus, management_focus, observation_focus):
        extra_text = _to_text(extra)
        if extra_text and extra_text not in focuses:
            focuses.append(extra_text)
    return focuses


def _build_symbol_review_state(
    *,
    runtime_proxy_match_rate: float,
    hold_precision: float,
    partial_then_hold_quality: float,
    full_exit_precision: float,
    resolved_row_count: int,
    live_runner_source_row_count: int,
) -> tuple[str, list[str], float]:
    blockers: list[str] = []
    if resolved_row_count < 500:
        blockers.append("resolved_row_count_below_symbol_floor")
    if live_runner_source_row_count < 100:
        blockers.append("live_runner_source_row_count_below_symbol_floor")
    if runtime_proxy_match_rate < 0.90:
        blockers.append("runtime_proxy_match_rate_below_symbol_floor")
    if hold_precision < 0.80:
        blockers.append("hold_precision_below_symbol_floor")
    if partial_then_hold_quality < 0.95:
        blockers.append("partial_then_hold_quality_below_symbol_floor")
    if full_exit_precision < 0.99:
        blockers.append("full_exit_precision_below_symbol_floor")

    severity = 0.0
    severity += max(0.0, 0.90 - runtime_proxy_match_rate) * 100.0
    severity += max(0.0, 0.80 - hold_precision) * 100.0
    severity += max(0.0, 0.95 - partial_then_hold_quality) * 100.0
    severity += max(0.0, 0.99 - full_exit_precision) * 100.0
    if resolved_row_count < 500:
        severity += 5.0
    if live_runner_source_row_count < 100:
        severity += 3.0

    if resolved_row_count < 500 or live_runner_source_row_count < 100:
        return "SUPPORT_REVIEW_ONLY", blockers, round(severity, 6)
    if blockers:
        return "PRIMARY_REVIEW", blockers, round(severity, 6)
    return "CANARY_CANDIDATE", blockers, round(severity, 6)


def build_checkpoint_pa8_action_review_packet(
    *,
    pa78_review_packet_payload: Mapping[str, Any] | None,
    action_eval_payload: Mapping[str, Any] | None,
    management_action_snapshot_payload: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any] | None,
    live_runner_watch_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pa78 = _mapping(pa78_review_packet_payload)
    pa78_summary = _mapping(pa78.get("summary"))
    action_eval = _mapping(action_eval_payload)
    action_eval_summary = _mapping(action_eval.get("summary"))
    action_eval_rows = _rows_by_symbol(action_eval)
    management_snapshot = _mapping(management_action_snapshot_payload)
    management_rows = _rows_by_symbol(management_snapshot)
    observation = _mapping(observation_payload)
    observation_rows = _rows_by_symbol(observation)
    live_runner = _mapping(live_runner_watch_payload)
    live_runner_rows = _rows_by_symbol(live_runner)

    symbols = sorted(
        set(action_eval_rows)
        | set(management_rows)
        | set(observation_rows)
        | set(live_runner_rows)
    )

    symbol_rows: list[dict[str, Any]] = []
    for symbol in symbols:
        action_row = action_eval_rows.get(symbol, {})
        management_row = management_rows.get(symbol, {})
        observation_row = observation_rows.get(symbol, {})
        live_runner_row = live_runner_rows.get(symbol, {})

        resolved_row_count = _to_int(action_row.get("resolved_row_count"))
        runtime_proxy_match_rate = _to_float(action_row.get("runtime_proxy_match_rate"))
        hold_precision = _to_float(action_row.get("hold_precision"))
        partial_then_hold_quality = _to_float(action_row.get("partial_then_hold_quality"))
        full_exit_precision = _to_float(action_row.get("full_exit_precision"))
        live_runner_source_row_count = max(
            _to_int(live_runner_row.get("live_runner_source_row_count")),
            _to_int(observation_row.get("live_runner_source_row_count")),
        )
        review_state, review_blockers, severity_score = _build_symbol_review_state(
            runtime_proxy_match_rate=runtime_proxy_match_rate,
            hold_precision=hold_precision,
            partial_then_hold_quality=partial_then_hold_quality,
            full_exit_precision=full_exit_precision,
            resolved_row_count=resolved_row_count,
            live_runner_source_row_count=live_runner_source_row_count,
        )
        review_focuses = _build_symbol_review_focuses(
            runtime_proxy_match_rate=runtime_proxy_match_rate,
            hold_precision=hold_precision,
            partial_then_hold_quality=partial_then_hold_quality,
            full_exit_precision=full_exit_precision,
            resolved_row_count=resolved_row_count,
            live_runner_source_row_count=live_runner_source_row_count,
            action_eval_focus=_to_text(action_row.get("recommended_focus")),
            management_focus=_to_text(management_row.get("recommended_focus")),
            observation_focus=_to_text(observation_row.get("recommended_focus")),
        )
        symbol_rows.append(
            {
                "symbol": symbol,
                "review_state": review_state,
                "severity_score": severity_score,
                "review_blockers": review_blockers,
                "review_focuses": review_focuses,
                "resolved_row_count": resolved_row_count,
                "runtime_proxy_match_rate": round(runtime_proxy_match_rate, 6),
                "hold_precision": round(hold_precision, 6),
                "partial_then_hold_quality": round(partial_then_hold_quality, 6),
                "full_exit_precision": round(full_exit_precision, 6),
                "manual_exception_count": _to_int(_loads_counts(action_row.get("quality_tier_counts")).get("manual_exception")),
                "live_runner_source_row_count": live_runner_source_row_count,
                "recent_live_runner_source_row_count": _to_int(live_runner_row.get("recent_live_runner_source_row_count")),
                "management_action_counts": _loads_counts(management_row.get("management_action_counts")),
                "hindsight_label_counts": _loads_counts(action_row.get("hindsight_label_counts")),
                "family_counts": _loads_counts(observation_row.get("family_counts")),
            }
        )

    state_rank = {"PRIMARY_REVIEW": 0, "SUPPORT_REVIEW_ONLY": 1, "CANARY_CANDIDATE": 2}
    symbol_rows = sorted(
        symbol_rows,
        key=lambda item: (
            state_rank.get(_to_text(item.get("review_state")), 9),
            -_to_float(item.get("severity_score")),
            _to_text(item.get("symbol")),
        ),
    )

    review_state_counts: dict[str, int] = {}
    for row in symbol_rows:
        review_state = _to_text(row.get("review_state"))
        review_state_counts[review_state] = review_state_counts.get(review_state, 0) + 1

    canary_candidate_symbols = [row["symbol"] for row in symbol_rows if row["review_state"] == "CANARY_CANDIDATE"]
    primary_review_symbols = [row["symbol"] for row in symbol_rows if row["review_state"] == "PRIMARY_REVIEW"]
    support_review_symbols = [row["symbol"] for row in symbol_rows if row["review_state"] == "SUPPORT_REVIEW_ONLY"]

    action_baseline_review_ready = bool(pa78_summary.get("action_baseline_review_ready"))
    if action_baseline_review_ready:
        overall_review_state = "READY_FOR_HUMAN_ACTION_REVIEW"
        if canary_candidate_symbols:
            recommended_next_action = "review_primary_symbols_then_prepare_action_only_canary_scope"
        else:
            recommended_next_action = "review_primary_symbols_then_decide_if_action_only_canary_should_wait"
    else:
        overall_review_state = "HOLD_ACTION_BASELINE_REVIEW"
        recommended_next_action = _to_text(
            pa78_summary.get("recommended_next_action"),
            "stabilize_action_baseline_review_packet",
        )

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_review_packet_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "pa8_review_state": _to_text(pa78_summary.get("pa8_review_state")),
            "scene_bias_review_state": _to_text(pa78_summary.get("scene_bias_review_state")),
            "action_baseline_review_ready": action_baseline_review_ready,
            "overall_review_state": overall_review_state,
            "review_state_counts": review_state_counts,
            "canary_candidate_symbols": canary_candidate_symbols,
            "primary_review_symbols": primary_review_symbols,
            "support_review_symbols": support_review_symbols,
            "review_order": [row["symbol"] for row in symbol_rows],
            "recommended_next_action": recommended_next_action,
            "scene_bias_separation_note": "scene_bias_remains_preview_only_while_pa8_reviews_action_baseline",
            "global_action_metrics": {
                "resolved_row_count": _to_int(action_eval_summary.get("resolved_row_count")),
                "runtime_proxy_match_rate": round(_to_float(action_eval_summary.get("runtime_proxy_match_rate")), 6),
                "hold_precision": round(_to_float(action_eval_summary.get("hold_precision")), 6),
                "partial_then_hold_quality": round(_to_float(action_eval_summary.get("partial_then_hold_quality")), 6),
                "full_exit_precision": round(_to_float(action_eval_summary.get("full_exit_precision")), 6),
            },
        },
        "symbol_rows": symbol_rows,
    }
