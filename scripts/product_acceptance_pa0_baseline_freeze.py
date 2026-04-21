from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_VERSION = "product_acceptance_pa0_baseline_v1"
TARGET_SYMBOLS_V1 = ("BTCUSD", "NAS100", "XAUUSD")
DEFAULT_OUTPUT_DIR = ROOT / "data" / "analysis" / "product_acceptance"
DEFAULT_ENTRY_DECISIONS_PATH = ROOT / "data" / "trades" / "entry_decisions.csv"
DEFAULT_RUNTIME_STATUS_PATH = ROOT / "data" / "runtime_status.json"
DEFAULT_CHART_FLOW_DISTRIBUTION_PATH = ROOT / "data" / "analysis" / "chart_flow_distribution_latest.json"
DEFAULT_CLOSED_HISTORY_PATH = ROOT / "data" / "trades" / "trade_closed_history.csv"
LEGACY_CLOSED_HISTORY_PATH = ROOT / "trade_closed_history.csv"
MIN_MEANINGFUL_RELEASE_PEAK_USD = 0.25
STRUCTURAL_GUARDS_V1 = {
    "outer_band_guard",
    "middle_sr_anchor_guard",
    "forecast_guard",
    "barrier_guard",
    "energy_soft_block",
}
ACCEPTABLE_WAIT_CHECK_DISPLAY_REASONS_V1 = {
    "btc_lower_probe_guard_wait_as_wait_checks",
    "btc_lower_probe_promotion_wait_as_wait_checks",
    "btc_lower_rebound_probe_energy_soft_block_as_wait_checks",
    "btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks",
    "btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
    "btc_upper_break_fail_confirm_forecast_wait_as_wait_checks",
    "btc_upper_reject_confirm_forecast_wait_as_wait_checks",
    "btc_upper_reject_confirm_energy_soft_block_as_wait_checks",
    "btc_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
    "btc_upper_reject_confirm_preflight_wait_as_wait_checks",
    "btc_upper_reject_probe_energy_soft_block_as_wait_checks",
    "btc_upper_reject_probe_forecast_wait_as_wait_checks",
    "btc_upper_reject_probe_preflight_wait_as_wait_checks",
    "btc_upper_reject_probe_promotion_wait_as_wait_checks",
    "btc_structural_probe_energy_soft_block_as_wait_checks",
    "nas_upper_reject_probe_promotion_wait_as_wait_checks",
    "nas_upper_reject_probe_forecast_wait_as_wait_checks",
    "nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
    "nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks",
    "nas_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
    "probe_guard_wait_as_wait_checks",
    "xau_middle_anchor_guard_wait_as_wait_checks",
    "xau_lower_probe_guard_wait_as_wait_checks",
    "xau_middle_anchor_probe_energy_soft_block_as_wait_checks",
    "xau_outer_band_probe_entry_gate_wait_as_wait_checks",
    "xau_outer_band_probe_energy_soft_block_as_wait_checks",
    "xau_upper_break_fail_confirm_energy_soft_block_as_wait_checks",
    "xau_upper_reject_confirm_energy_soft_block_as_wait_checks",
    "xau_upper_reject_confirm_forecast_wait_as_wait_checks",
    "xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks",
    "xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks",
    "xau_upper_reject_mixed_guard_wait_as_wait_checks",
    "xau_upper_reject_probe_forecast_wait_as_wait_checks",
    "xau_upper_reject_probe_promotion_wait_as_wait_checks",
    "xau_upper_reject_probe_energy_soft_block_as_wait_checks",
}
ACCEPTABLE_HIDDEN_SUPPRESSION_REASONS_V1 = {
    "balanced_conflict_wait_hide_without_probe",
    "btc_sell_middle_anchor_wait_hide_without_probe",
    "btc_lower_rebound_forecast_wait_hide_without_probe",
    "nas_upper_break_fail_wait_hide_without_probe",
    "nas_upper_reject_wait_hide_without_probe",
    "nas_sell_middle_anchor_wait_hide_without_probe",
    "nas_upper_reclaim_wait_hide_without_probe",
    "xau_upper_reclaim_wait_hide_without_probe",
    "sell_outer_band_wait_hide_without_probe",
    "structural_wait_hide_without_probe",
}


def _resolve_now(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _resolve_closed_history_path(
    preferred_path: Path | None = None,
    *,
    legacy_fallback_path: Path | None = None,
) -> Path:
    preferred = Path(preferred_path or DEFAULT_CLOSED_HISTORY_PATH)
    legacy = Path(legacy_fallback_path or LEGACY_CLOSED_HISTORY_PATH)
    if preferred.exists():
        return preferred
    if legacy.exists():
        return legacy
    return preferred


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_float(value: Any) -> float:
    text = _coerce_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def _coerce_int(value: Any) -> int:
    text = _coerce_text(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _coerce_text(value).lower()
    return text in {"1", "true", "t", "yes", "y", "on"}


def _parse_jsonish(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _coerce_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _top_counts(counter: Counter[str], *, limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, count in counter.most_common(limit):
        rows.append({"name": str(key), "count": int(count)})
    return rows


def _reason_bucket(observe_reason: str, blocked_by: str, probe_scene_id: str) -> str:
    if probe_scene_id:
        return f"probe:{probe_scene_id}"
    observe_u = _coerce_text(observe_reason).lower()
    blocked_u = _coerce_text(blocked_by).lower()
    if observe_u.startswith("conflict_"):
        return "conflict"
    for token in ("lower", "upper", "middle", "mid", "rebound", "reclaim", "reject", "trend", "break"):
        if token in observe_u:
            return token
    if blocked_u.endswith("_guard"):
        return f"guard:{blocked_u}"
    if observe_u:
        return observe_u.split("_")[0]
    return "unclassified"


def _scene_signature(row: dict[str, Any]) -> str:
    box_state = _coerce_text(row.get("box_state") or "UNKNOWN").upper()
    bb_state = _coerce_text(row.get("bb_state") or "UNKNOWN").upper()
    probe_scene_id = _coerce_text(row.get("probe_scene_id"))
    reason_bucket = _reason_bucket(
        _coerce_text(row.get("observe_reason")),
        _coerce_text(row.get("blocked_by")),
        probe_scene_id,
    )
    action_none_reason = _coerce_text(row.get("action_none_reason") or "none").lower()
    probe_flag = "probe" if probe_scene_id else "no_probe"
    return f"{box_state}|{bb_state}|{reason_bucket}|{action_none_reason}|{probe_flag}"


def _normalize_entry_row(row: dict[str, Any]) -> dict[str, Any]:
    consumer_state = _parse_jsonish(row.get("consumer_check_state_v1"))
    symbol = _coerce_text(row.get("symbol") or consumer_state.get("canonical_symbol")).upper()
    observe_reason = _coerce_text(row.get("observe_reason") or consumer_state.get("semantic_origin_reason"))
    blocked_by = _coerce_text(row.get("blocked_by"))
    action_none_reason = _coerce_text(row.get("action_none_reason"))
    probe_scene_id = _coerce_text(row.get("probe_scene_id") or consumer_state.get("probe_scene_id"))
    check_candidate = _coerce_bool(
        consumer_state.get("check_candidate", row.get("consumer_check_candidate", False))
    )
    display_ready = _coerce_bool(
        consumer_state.get("check_display_ready", row.get("consumer_check_display_ready", False))
    )
    entry_ready = _coerce_bool(
        consumer_state.get("entry_ready", row.get("consumer_check_entry_ready", row.get("entry_ready", False)))
    )
    check_stage = _coerce_text(consumer_state.get("check_stage") or row.get("consumer_check_stage")).upper()
    check_side = _coerce_text(consumer_state.get("check_side") or row.get("consumer_check_side")).upper()
    display_score = _coerce_float(consumer_state.get("display_score"))
    display_repeat_count = _coerce_int(consumer_state.get("display_repeat_count"))
    display_strength_level = _coerce_int(
        consumer_state.get("display_strength_level", row.get("consumer_check_display_strength_level"))
    )
    display_importance_tier = _coerce_text(consumer_state.get("display_importance_tier")).lower()
    chart_event_kind_hint = _coerce_text(consumer_state.get("chart_event_kind_hint")).upper()
    chart_display_mode = _coerce_text(consumer_state.get("chart_display_mode")).lower()
    chart_display_reason = _coerce_text(consumer_state.get("chart_display_reason")).lower()
    modifier_primary_reason = _coerce_text(consumer_state.get("modifier_primary_reason")).lower()
    normalized = {
        "time": _coerce_text(row.get("time") or row.get("decision_time")),
        "symbol": symbol,
        "action": _coerce_text(row.get("action")).upper(),
        "observe_reason": observe_reason,
        "blocked_by": blocked_by,
        "action_none_reason": action_none_reason,
        "probe_scene_id": probe_scene_id,
        "box_state": _coerce_text(row.get("box_state") or consumer_state.get("display_box_state")).upper(),
        "bb_state": _coerce_text(row.get("bb_state") or consumer_state.get("display_bb_state")).upper(),
        "check_candidate": bool(check_candidate),
        "display_ready": bool(display_ready),
        "entry_ready": bool(entry_ready),
        "check_stage": str(check_stage or ""),
        "check_side": str(check_side or ""),
        "display_score": float(display_score),
        "display_repeat_count": int(display_repeat_count),
        "display_strength_level": int(display_strength_level),
        "display_importance_tier": str(display_importance_tier or ""),
        "chart_event_kind_hint": str(chart_event_kind_hint or ""),
        "chart_display_mode": str(chart_display_mode or ""),
        "chart_display_reason": str(chart_display_reason or ""),
        "modifier_primary_reason": str(modifier_primary_reason or ""),
        "entry_score_raw": _coerce_float(row.get("entry_score_raw")),
        "decision_row_key": _coerce_text(row.get("decision_row_key")),
        "scene_signature": "",
    }
    normalized["scene_signature"] = _scene_signature(normalized)
    return normalized


def _normalize_closed_trade_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket": _coerce_text(row.get("ticket")),
        "symbol": _coerce_text(row.get("symbol")).upper(),
        "direction": _coerce_text(row.get("direction")).upper(),
        "open_time": _coerce_text(row.get("open_time")),
        "close_time": _coerce_text(row.get("close_time")),
        "entry_reason": _coerce_text(row.get("entry_reason")),
        "exit_reason": _coerce_text(row.get("exit_reason")),
        "net_pnl_after_cost": _coerce_float(row.get("net_pnl_after_cost")),
        "giveback_usd": _coerce_float(row.get("giveback_usd")),
        "peak_profit_at_exit": _coerce_float(row.get("peak_profit_at_exit")),
        "post_exit_mfe": _coerce_float(row.get("post_exit_mfe")),
        "post_exit_mae": _coerce_float(row.get("post_exit_mae")),
        "wait_quality_label": _coerce_text(row.get("wait_quality_label")).lower(),
        "loss_quality_label": _coerce_text(row.get("loss_quality_label")).lower(),
        "exit_policy_profile": _coerce_text(row.get("exit_policy_profile")),
        "exit_wait_state": _coerce_text(row.get("exit_wait_state")).upper(),
        "exit_wait_decision": _coerce_text(row.get("exit_wait_decision")).lower(),
        "decision_reason": _coerce_text(row.get("decision_reason")).lower(),
        "utility_exit_now": _coerce_float(row.get("utility_exit_now")),
        "u_wait_be": _coerce_float(row.get("u_wait_be")),
        "u_wait_tp1": _coerce_float(row.get("u_wait_tp1")),
        "status": _coerce_text(row.get("status")),
    }


def _collect_recent_rows_by_symbol(
    *,
    path: Path,
    row_normalizer,
    max_per_symbol: int,
) -> dict[str, list[dict[str, Any]]]:
    grouped = {symbol: deque(maxlen=max_per_symbol) for symbol in TARGET_SYMBOLS_V1}
    if not path.exists():
        return {symbol: [] for symbol in TARGET_SYMBOLS_V1}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = row_normalizer(dict(raw_row))
            symbol = _coerce_text(row.get("symbol")).upper()
            if symbol in grouped:
                grouped[symbol].append(row)
    return {symbol: list(grouped[symbol]) for symbol in TARGET_SYMBOLS_V1}


def _build_tri_symbol_baseline_summary(
    entry_rows_by_symbol: dict[str, list[dict[str, Any]]],
    chart_flow_payload: dict[str, Any],
    runtime_status_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    chart_symbols = dict(chart_flow_payload.get("symbols", {}) or {})
    runtime_policy = dict(runtime_status_payload.get("policy_snapshot", {}) or {})
    applied_vs_default = dict(runtime_policy.get("symbol_applied_vs_default", {}) or {})
    rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        entry_rows = list(entry_rows_by_symbol.get(symbol, []) or [])
        stage_counter: Counter[str] = Counter()
        observe_reason_counter: Counter[str] = Counter()
        blocked_by_counter: Counter[str] = Counter()
        action_none_counter: Counter[str] = Counter()
        probe_scene_counter: Counter[str] = Counter()
        display_ready_count = 0
        check_candidate_count = 0
        entry_ready_count = 0
        action_open_count = 0
        score_sum = 0.0
        for row in entry_rows:
            stage_counter[_coerce_text(row.get("check_stage")) or "NONE"] += 1
            observe_reason_counter[_coerce_text(row.get("observe_reason")) or "(blank)"] += 1
            blocked_by_counter[_coerce_text(row.get("blocked_by")) or "(blank)"] += 1
            action_none_counter[_coerce_text(row.get("action_none_reason")) or "(blank)"] += 1
            probe_scene_counter[_coerce_text(row.get("probe_scene_id")) or "(blank)"] += 1
            display_ready_count += 1 if bool(row.get("display_ready")) else 0
            check_candidate_count += 1 if bool(row.get("check_candidate")) else 0
            entry_ready_count += 1 if bool(row.get("entry_ready")) else 0
            action_open_count += 1 if _coerce_text(row.get("action")) in {"BUY", "SELL"} else 0
            score_sum += _coerce_float(row.get("display_score"))
        chart_symbol_payload = dict(chart_symbols.get(symbol, {}) or {})
        applied_payload = dict(applied_vs_default.get(symbol, {}) or {})
        row_count = len(entry_rows)
        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": row_count,
                "check_candidate_count": check_candidate_count,
                "display_ready_count": display_ready_count,
                "display_ready_ratio": _ratio(display_ready_count, row_count),
                "entry_ready_count": entry_ready_count,
                "action_open_count": action_open_count,
                "avg_display_score": round(score_sum / row_count, 4) if row_count else 0.0,
                "top_observe_reasons": _top_counts(observe_reason_counter),
                "top_blocked_by": _top_counts(blocked_by_counter),
                "top_action_none_reasons": _top_counts(action_none_counter),
                "top_probe_scenes": _top_counts(probe_scene_counter),
                "stage_counts": dict(stage_counter),
                "chart_window_event_count": _coerce_int(chart_symbol_payload.get("window_event_count")),
                "chart_event_counts": dict(chart_symbol_payload.get("event_counts", {}) or {}),
                "chart_presence": dict(chart_symbol_payload.get("presence", {}) or {}),
                "runtime_entry_threshold_applied": _coerce_float(applied_payload.get("entry_threshold_applied")),
                "runtime_entry_threshold_delta": _coerce_float(applied_payload.get("entry_threshold_delta")),
                "runtime_exit_threshold_applied": _coerce_float(applied_payload.get("exit_threshold_applied")),
                "runtime_exit_threshold_delta": _coerce_float(applied_payload.get("exit_threshold_delta")),
            }
        )
    return rows


def _build_stage_density_snapshot(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        entry_rows = list(entry_rows_by_symbol.get(symbol, []) or [])
        total = len(entry_rows)
        counter = Counter((_coerce_text(row.get("check_stage")) or "NONE") for row in entry_rows)
        for stage in ("NONE", "BLOCKED", "OBSERVE", "PROBE", "READY"):
            count = int(counter.get(stage, 0))
            rows.append(
                {
                    "symbol": symbol,
                    "stage": stage,
                    "count": count,
                    "ratio": _ratio(count, total),
                }
            )
    return rows


def _build_display_ladder_snapshot(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        entry_rows = list(entry_rows_by_symbol.get(symbol, []) or [])
        repeat_counter = Counter(str(_coerce_int(row.get("display_repeat_count"))) for row in entry_rows)
        strength_counter = Counter(str(_coerce_int(row.get("display_strength_level"))) for row in entry_rows)
        total = len(entry_rows)
        for repeat_key, count in sorted(repeat_counter.items(), key=lambda item: int(item[0])):
            rows.append(
                {
                    "symbol": symbol,
                    "ladder_type": "repeat_count",
                    "ladder_value": repeat_key,
                    "count": int(count),
                    "ratio": _ratio(count, total),
                }
            )
        for level_key, count in sorted(strength_counter.items(), key=lambda item: int(item[0])):
            rows.append(
                {
                    "symbol": symbol,
                    "ladder_type": "strength_level",
                    "ladder_value": level_key,
                    "count": int(count),
                    "ratio": _ratio(count, total),
                }
            )
    return rows


def _entry_seed_payload(row: dict[str, Any], *, seed_type: str, ranking_score: float, seed_reason: str) -> dict[str, Any]:
    return {
        "seed_type": seed_type,
        "ranking_score": round(float(ranking_score), 4),
        "seed_reason": str(seed_reason or ""),
        "symbol": _coerce_text(row.get("symbol")),
        "time": _coerce_text(row.get("time")),
        "action": _coerce_text(row.get("action")),
        "observe_reason": _coerce_text(row.get("observe_reason")),
        "blocked_by": _coerce_text(row.get("blocked_by")),
        "action_none_reason": _coerce_text(row.get("action_none_reason")),
        "probe_scene_id": _coerce_text(row.get("probe_scene_id")),
        "check_candidate": bool(row.get("check_candidate")),
        "check_stage": _coerce_text(row.get("check_stage")),
        "check_side": _coerce_text(row.get("check_side")),
        "display_ready": bool(row.get("display_ready")),
        "display_score": _coerce_float(row.get("display_score")),
        "display_repeat_count": _coerce_int(row.get("display_repeat_count")),
        "display_strength_level": _coerce_int(row.get("display_strength_level")),
        "chart_event_kind_hint": _coerce_text(row.get("chart_event_kind_hint")).upper(),
        "chart_display_mode": _coerce_text(row.get("chart_display_mode")).lower(),
        "chart_display_reason": _coerce_text(row.get("chart_display_reason")).lower(),
        "entry_ready": bool(row.get("entry_ready")),
        "box_state": _coerce_text(row.get("box_state")),
        "bb_state": _coerce_text(row.get("bb_state")),
        "decision_row_key": _coerce_text(row.get("decision_row_key")),
    }


def _is_acceptable_wait_check_relief(row: dict[str, Any]) -> bool:
    if not bool(row.get("display_ready")):
        return False
    event_kind_hint = _coerce_text(row.get("chart_event_kind_hint")).upper()
    display_mode = _coerce_text(row.get("chart_display_mode")).lower()
    display_reason = _coerce_text(row.get("chart_display_reason")).lower()
    return bool(
        event_kind_hint == "WAIT"
        and display_mode == "wait_check_repeat"
        and display_reason in ACCEPTABLE_WAIT_CHECK_DISPLAY_REASONS_V1
    )


def _is_acceptable_hidden_suppression(row: dict[str, Any]) -> bool:
    if bool(row.get("display_ready")):
        return False
    modifier_primary_reason = _coerce_text(row.get("modifier_primary_reason")).lower()
    if modifier_primary_reason in ACCEPTABLE_HIDDEN_SUPPRESSION_REASONS_V1:
        return True
    observe_reason = _coerce_text(row.get("observe_reason")).lower()
    action_none_reason = _coerce_text(row.get("action_none_reason")).lower()
    probe_scene_id = _coerce_text(row.get("probe_scene_id"))
    check_side = _coerce_text(row.get("check_side")).upper()
    check_stage = _coerce_text(row.get("check_stage")).upper()
    return bool(
        observe_reason.startswith("conflict_box_")
        and action_none_reason == "observe_state_wait"
        and not probe_scene_id
        and not check_side
        and check_stage in {"", "NONE"}
    )


def _build_must_show_missing_candidates(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(entry_rows_by_symbol.get(symbol, []) or []):
            if _is_acceptable_wait_check_relief(row):
                continue
            if _is_acceptable_hidden_suppression(row):
                continue
            score = 0.0
            reasons: list[str] = []
            if bool(row.get("check_candidate")):
                score += 1.5
                reasons.append("candidate")
            if not bool(row.get("display_ready")):
                score += 2.0
                reasons.append("display_hidden")
            if _coerce_text(row.get("check_stage")) in {"", "BLOCKED"}:
                score += 0.75
                reasons.append("blocked_or_empty_stage")
            blocked_by = _coerce_text(row.get("blocked_by"))
            if blocked_by in STRUCTURAL_GUARDS_V1 or blocked_by.endswith("_guard"):
                score += 1.0
                reasons.append("guard_block")
            action_none_reason = _coerce_text(row.get("action_none_reason"))
            if action_none_reason in {"observe_state_wait", "probe_not_promoted", "confirm_suppressed", "execution_soft_blocked"}:
                score += 0.75
                reasons.append(action_none_reason)
            if _coerce_text(row.get("probe_scene_id")):
                score += 0.25
                reasons.append("scene_probe")
            if _coerce_text(row.get("display_importance_tier")) in {"high", "medium"}:
                score += 0.5
                reasons.append("importance_tier")
            if score >= 3.0:
                seeds.append(
                    _entry_seed_payload(
                        row,
                        seed_type="must_show_missing",
                        ranking_score=score,
                        seed_reason=" / ".join(reasons),
                    )
                )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["time"]))[:15]


def _build_must_hide_leakage_candidates(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(entry_rows_by_symbol.get(symbol, []) or []):
            if not bool(row.get("display_ready")):
                continue
            if _is_acceptable_wait_check_relief(row):
                continue
            if _is_acceptable_hidden_suppression(row):
                continue
            score = 0.0
            reasons: list[str] = []
            score += 1.5
            reasons.append("display_visible")
            if _coerce_text(row.get("check_stage")) in {"OBSERVE", "PROBE", "READY"}:
                score += 0.5
                reasons.append("directional_stage")
            observe_reason = _coerce_text(row.get("observe_reason"))
            if observe_reason.startswith("conflict_"):
                score += 1.5
                reasons.append("conflict_reason")
            blocked_by = _coerce_text(row.get("blocked_by"))
            if blocked_by in STRUCTURAL_GUARDS_V1 or blocked_by.endswith("_guard"):
                score += 1.0
                reasons.append("guard_present")
            action_none_reason = _coerce_text(row.get("action_none_reason"))
            if action_none_reason in {"observe_state_wait", "probe_not_promoted", "confirm_suppressed"}:
                score += 0.75
                reasons.append(action_none_reason)
            if _coerce_float(row.get("display_score")) >= 0.8:
                score += 0.75
                reasons.append("high_score_visible")
            if score >= 3.0:
                seeds.append(
                    _entry_seed_payload(
                        row,
                        seed_type="must_hide_leakage",
                        ranking_score=score,
                        seed_reason=" / ".join(reasons),
                    )
                )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["time"]))[:15]


def _build_must_enter_candidates(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(entry_rows_by_symbol.get(symbol, []) or []):
            if _is_acceptable_wait_check_relief(row):
                continue
            if _is_acceptable_hidden_suppression(row):
                continue
            action = _coerce_text(row.get("action"))
            if action not in {"BUY", "SELL"} and not bool(row.get("entry_ready")):
                continue
            score = 0.0
            reasons: list[str] = []
            if action in {"BUY", "SELL"}:
                score += 2.0
                reasons.append("action_opened")
            if bool(row.get("entry_ready")):
                score += 1.0
                reasons.append("entry_ready")
            if _coerce_text(row.get("check_stage")) == "READY":
                score += 0.5
                reasons.append("ready_stage")
            if bool(row.get("display_ready")):
                score += 0.5
                reasons.append("display_ready")
            score += min(2.0, _coerce_float(row.get("entry_score_raw")) / 100.0)
            seeds.append(
                _entry_seed_payload(
                    row,
                    seed_type="must_enter_candidate",
                    ranking_score=score,
                    seed_reason=" / ".join(reasons),
                )
            )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["time"]))[:12]


def _build_must_block_candidates(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(entry_rows_by_symbol.get(symbol, []) or []):
            if not bool(row.get("check_candidate")):
                continue
            if bool(row.get("entry_ready")) or _coerce_text(row.get("action")) in {"BUY", "SELL"}:
                continue
            if _is_acceptable_wait_check_relief(row):
                continue
            if _is_acceptable_hidden_suppression(row):
                continue
            score = 1.5
            reasons = ["candidate_not_opened"]
            if not bool(row.get("display_ready")):
                score += 1.0
                reasons.append("display_hidden")
            if _coerce_text(row.get("check_stage")) == "BLOCKED":
                score += 1.0
                reasons.append("blocked_stage")
            if _coerce_text(row.get("blocked_by")):
                score += 0.75
                reasons.append("blocked_by_present")
            if _coerce_text(row.get("action_none_reason")):
                score += 0.5
                reasons.append("non_action_reason")
            if score >= 2.5:
                seeds.append(
                    _entry_seed_payload(
                        row,
                        seed_type="must_block_candidate",
                        ranking_score=score,
                        seed_reason=" / ".join(reasons),
                    )
                )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["time"]))[:12]


def _build_divergence_seeds(entry_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(entry_rows_by_symbol.get(symbol, []) or []):
            signature = _coerce_text(row.get("scene_signature"))
            if signature:
                grouped[signature].append(row)
    seeds: list[dict[str, Any]] = []
    for signature, rows in grouped.items():
        unique_symbols = sorted({_coerce_text(row.get("symbol")) for row in rows if _coerce_text(row.get("symbol"))})
        if len(unique_symbols) < 2:
            continue
        distinct_stages = sorted({_coerce_text(row.get("check_stage")) or "NONE" for row in rows})
        distinct_display_states = sorted({str(bool(row.get("display_ready"))) for row in rows})
        distinct_sides = sorted({_coerce_text(row.get("check_side")) or "NONE" for row in rows})
        if len(distinct_stages) == 1 and len(distinct_display_states) == 1 and len(distinct_sides) == 1:
            continue
        samples_by_symbol: dict[str, dict[str, Any]] = {}
        for row in rows:
            samples_by_symbol[_coerce_text(row.get("symbol"))] = {
                "symbol": _coerce_text(row.get("symbol")),
                "time": _coerce_text(row.get("time")),
                "observe_reason": _coerce_text(row.get("observe_reason")),
                "check_stage": _coerce_text(row.get("check_stage")) or "NONE",
                "check_side": _coerce_text(row.get("check_side")) or "NONE",
                "display_ready": bool(row.get("display_ready")),
                "display_score": _coerce_float(row.get("display_score")),
            }
        divergence_score = (len(unique_symbols) * 1.5) + len(distinct_stages) + len(distinct_display_states) + len(distinct_sides)
        seeds.append(
            {
                "seed_type": "visually_similar_divergence",
                "scene_signature": signature,
                "ranking_score": round(divergence_score, 4),
                "symbol_count": len(unique_symbols),
                "symbols": unique_symbols,
                "distinct_stages": distinct_stages,
                "distinct_display_ready_states": distinct_display_states,
                "distinct_sides": distinct_sides,
                "sample_rows": [samples_by_symbol[key] for key in sorted(samples_by_symbol.keys())],
            }
        )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["scene_signature"]))[:12]


def _build_closed_trade_baseline_summary(closed_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        closed_rows = list(closed_rows_by_symbol.get(symbol, []) or [])
        total = len(closed_rows)
        exit_reason_counter = Counter(_coerce_text(row.get("exit_reason")) or "(blank)" for row in closed_rows)
        wait_quality_counter = Counter(_coerce_text(row.get("wait_quality_label")) or "(blank)" for row in closed_rows)
        loss_quality_counter = Counter(_coerce_text(row.get("loss_quality_label")) or "(blank)" for row in closed_rows)
        net_sum = sum(_coerce_float(row.get("net_pnl_after_cost")) for row in closed_rows)
        giveback_sum = sum(_coerce_float(row.get("giveback_usd")) for row in closed_rows)
        rows.append(
            {
                "symbol": symbol,
                "recent_closed_trade_count": total,
                "avg_net_pnl_after_cost": round(net_sum / total, 4) if total else 0.0,
                "avg_giveback_usd": round(giveback_sum / total, 4) if total else 0.0,
                "top_exit_reasons": _top_counts(exit_reason_counter),
                "wait_quality_counts": dict(wait_quality_counter),
                "loss_quality_counts": dict(loss_quality_counter),
            }
        )
    return rows


def _effective_release_giveback(row: dict[str, Any]) -> float:
    peak_profit = _coerce_float(row.get("peak_profit_at_exit"))
    giveback = _coerce_float(row.get("giveback_usd"))
    if peak_profit < MIN_MEANINGFUL_RELEASE_PEAK_USD:
        return 0.0
    return giveback


def _supports_must_release_bad_loss_seed(row: dict[str, Any]) -> bool:
    peak_profit = _coerce_float(row.get("peak_profit_at_exit"))
    giveback = _effective_release_giveback(row)
    post_exit_mfe = _coerce_float(row.get("post_exit_mfe"))
    wait_quality = _coerce_text(row.get("wait_quality_label")).lower()

    if peak_profit < MIN_MEANINGFUL_RELEASE_PEAK_USD:
        return False
    if giveback > 0.0 or post_exit_mfe > 0.5:
        return True
    return wait_quality == "bad_wait"


def _supports_bad_exit_bad_loss_seed(row: dict[str, Any]) -> bool:
    peak_profit = _coerce_float(row.get("peak_profit_at_exit"))
    giveback = _effective_release_giveback(row)
    post_exit_mfe = _coerce_float(row.get("post_exit_mfe"))
    wait_quality = _coerce_text(row.get("wait_quality_label")).lower()
    exit_reason = _coerce_text(row.get("exit_reason")).lower()

    if post_exit_mfe > 0.5 or giveback > 0.5:
        return True
    if wait_quality == "bad_wait":
        return True
    if "hard_guard=adverse" in exit_reason and (
        "protect exit" in exit_reason or "adverse stop" in exit_reason
    ):
        return False
    return peak_profit >= MIN_MEANINGFUL_RELEASE_PEAK_USD


def _supports_bad_exit_non_loss_seed(row: dict[str, Any]) -> bool:
    giveback = _effective_release_giveback(row)
    post_exit_mfe = _coerce_float(row.get("post_exit_mfe"))
    wait_quality = _coerce_text(row.get("wait_quality_label")).lower()
    decision_reason = _coerce_text(row.get("decision_reason")).lower()
    exit_reason = _coerce_text(row.get("exit_reason")).lower()

    if post_exit_mfe > 0.5:
        return True
    if giveback <= 0.5:
        return False
    if wait_quality in {"bad_wait", "unnecessary_wait"}:
        return True
    if (
        wait_quality == "no_wait"
        and decision_reason == "exit_now_best"
        and exit_reason.startswith("exit context")
    ):
        return False
    return True


def _closed_seed_payload(row: dict[str, Any], *, seed_type: str, ranking_score: float, seed_reason: str) -> dict[str, Any]:
    return {
        "seed_type": seed_type,
        "ranking_score": round(float(ranking_score), 4),
        "seed_reason": str(seed_reason or ""),
        "symbol": _coerce_text(row.get("symbol")),
        "ticket": _coerce_text(row.get("ticket")),
        "direction": _coerce_text(row.get("direction")),
        "open_time": _coerce_text(row.get("open_time")),
        "close_time": _coerce_text(row.get("close_time")),
        "entry_reason": _coerce_text(row.get("entry_reason")),
        "exit_reason": _coerce_text(row.get("exit_reason")),
        "net_pnl_after_cost": _coerce_float(row.get("net_pnl_after_cost")),
        "giveback_usd": _coerce_float(row.get("giveback_usd")),
        "peak_profit_at_exit": _coerce_float(row.get("peak_profit_at_exit")),
        "post_exit_mfe": _coerce_float(row.get("post_exit_mfe")),
        "post_exit_mae": _coerce_float(row.get("post_exit_mae")),
        "wait_quality_label": _coerce_text(row.get("wait_quality_label")),
        "loss_quality_label": _coerce_text(row.get("loss_quality_label")),
        "exit_policy_profile": _coerce_text(row.get("exit_policy_profile")),
        "exit_wait_state": _coerce_text(row.get("exit_wait_state")),
        "exit_wait_decision": _coerce_text(row.get("exit_wait_decision")),
        "decision_reason": _coerce_text(row.get("decision_reason")),
        "utility_exit_now": _coerce_float(row.get("utility_exit_now")),
        "u_wait_be": _coerce_float(row.get("u_wait_be")),
        "u_wait_tp1": _coerce_float(row.get("u_wait_tp1")),
    }


def _build_good_exit_candidates(closed_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(closed_rows_by_symbol.get(symbol, []) or []):
            net_pnl = _coerce_float(row.get("net_pnl_after_cost"))
            if net_pnl <= 0:
                continue
            score = net_pnl + max(0.0, 1.0 - min(1.0, _coerce_float(row.get("giveback_usd"))))
            if _coerce_text(row.get("loss_quality_label")) in {"non_loss", "good_loss"}:
                score += 1.0
            seeds.append(
                _closed_seed_payload(
                    row,
                    seed_type="good_exit_candidate",
                    ranking_score=score,
                    seed_reason="positive_net_pnl / contained_giveback",
                )
            )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["close_time"]))[:10]


def _build_bad_exit_candidates(closed_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(closed_rows_by_symbol.get(symbol, []) or []):
            net_pnl = _coerce_float(row.get("net_pnl_after_cost"))
            giveback = _effective_release_giveback(row)
            post_exit_mfe = _coerce_float(row.get("post_exit_mfe"))
            loss_quality = _coerce_text(row.get("loss_quality_label")).lower()
            if loss_quality == "bad_loss":
                if not _supports_bad_exit_bad_loss_seed(row):
                    continue
            elif not _supports_bad_exit_non_loss_seed(row):
                continue
            score = max(0.0, -net_pnl) + giveback + post_exit_mfe
            if loss_quality == "bad_loss":
                score += 1.0
            seeds.append(
                _closed_seed_payload(
                    row,
                    seed_type="bad_exit_candidate",
                    ranking_score=score,
                    seed_reason="negative_pnl_or_giveback_or_post_exit_mfe",
                )
            )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["close_time"]))[:10]


def _build_must_hold_candidates(closed_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(closed_rows_by_symbol.get(symbol, []) or []):
            post_exit_mfe = _coerce_float(row.get("post_exit_mfe"))
            wait_quality = _coerce_text(row.get("wait_quality_label"))
            if wait_quality != "bad_wait" and post_exit_mfe <= 0.5:
                continue
            score = post_exit_mfe + (1.0 if wait_quality == "bad_wait" else 0.0)
            seeds.append(
                _closed_seed_payload(
                    row,
                    seed_type="must_hold_candidate",
                    ranking_score=score,
                    seed_reason="bad_wait_or_large_post_exit_mfe",
                )
            )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["close_time"]))[:10]


def _build_must_release_candidates(closed_rows_by_symbol: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        for row in list(closed_rows_by_symbol.get(symbol, []) or []):
            net_pnl = _coerce_float(row.get("net_pnl_after_cost"))
            giveback = _effective_release_giveback(row)
            loss_quality = _coerce_text(row.get("loss_quality_label")).lower()
            if loss_quality == "bad_loss":
                if not _supports_must_release_bad_loss_seed(row):
                    continue
            elif giveback <= 0.5:
                continue
            score = max(0.0, -net_pnl) + giveback + (1.0 if loss_quality == "bad_loss" else 0.0)
            seeds.append(
                _closed_seed_payload(
                    row,
                    seed_type="must_release_candidate",
                    ranking_score=score,
                    seed_reason="negative_pnl_or_giveback_or_bad_loss",
                )
            )
    return sorted(seeds, key=lambda item: (-_coerce_float(item.get("ranking_score")), item["symbol"], item["close_time"]))[:10]


def _build_runtime_policy_snapshot(runtime_status_payload: dict[str, Any]) -> dict[str, Any]:
    semantic_live_config = dict(runtime_status_payload.get("semantic_live_config", {}) or {})
    policy_snapshot = dict(runtime_status_payload.get("policy_snapshot", {}) or {})
    applied_vs_default = dict(policy_snapshot.get("symbol_applied_vs_default", {}) or {})
    symbol_rows: list[dict[str, Any]] = []
    for symbol in TARGET_SYMBOLS_V1:
        applied_payload = dict(applied_vs_default.get(symbol, {}) or {})
        symbol_rows.append(
            {
                "symbol": symbol,
                "entry_threshold_applied": _coerce_float(applied_payload.get("entry_threshold_applied")),
                "entry_threshold_delta": _coerce_float(applied_payload.get("entry_threshold_delta")),
                "exit_threshold_applied": _coerce_float(applied_payload.get("exit_threshold_applied")),
                "exit_threshold_delta": _coerce_float(applied_payload.get("exit_threshold_delta")),
                "policy_scope": _coerce_text(applied_payload.get("policy_scope")),
                "sample_count": _coerce_int(applied_payload.get("sample_count")),
            }
        )
    return {
        "updated_at": _coerce_text(runtime_status_payload.get("updated_at")),
        "entry_threshold": _coerce_float(runtime_status_payload.get("entry_threshold")),
        "exit_threshold": _coerce_float(runtime_status_payload.get("exit_threshold")),
        "semantic_live_mode": _coerce_text(semantic_live_config.get("mode")),
        "symbol_policy_snapshot": symbol_rows,
    }


def build_product_acceptance_pa0_baseline_report(
    *,
    entry_decisions_path: Path = DEFAULT_ENTRY_DECISIONS_PATH,
    runtime_status_path: Path = DEFAULT_RUNTIME_STATUS_PATH,
    chart_flow_distribution_path: Path = DEFAULT_CHART_FLOW_DISTRIBUTION_PATH,
    closed_history_path: Path = DEFAULT_CLOSED_HISTORY_PATH,
    recent_rows_per_symbol: int = 120,
    recent_closed_trades_per_symbol: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    report_now = _resolve_now(now)
    resolved_closed_history_path = _resolve_closed_history_path(closed_history_path)
    entry_rows_by_symbol = _collect_recent_rows_by_symbol(
        path=entry_decisions_path,
        row_normalizer=_normalize_entry_row,
        max_per_symbol=recent_rows_per_symbol,
    )
    closed_rows_by_symbol = _collect_recent_rows_by_symbol(
        path=resolved_closed_history_path,
        row_normalizer=_normalize_closed_trade_row,
        max_per_symbol=recent_closed_trades_per_symbol,
    )
    runtime_status_payload = _read_json(runtime_status_path)
    chart_flow_payload = _read_json(chart_flow_distribution_path)

    tri_symbol_baseline_summary = _build_tri_symbol_baseline_summary(
        entry_rows_by_symbol,
        chart_flow_payload,
        runtime_status_payload,
    )
    stage_density_snapshot = _build_stage_density_snapshot(entry_rows_by_symbol)
    display_ladder_snapshot = _build_display_ladder_snapshot(entry_rows_by_symbol)
    must_show_missing = _build_must_show_missing_candidates(entry_rows_by_symbol)
    must_hide_leakage = _build_must_hide_leakage_candidates(entry_rows_by_symbol)
    must_enter_candidates = _build_must_enter_candidates(entry_rows_by_symbol)
    must_block_candidates = _build_must_block_candidates(entry_rows_by_symbol)
    divergence_seeds = _build_divergence_seeds(entry_rows_by_symbol)
    closed_trade_baseline_summary = _build_closed_trade_baseline_summary(closed_rows_by_symbol)
    must_hold_candidates = _build_must_hold_candidates(closed_rows_by_symbol)
    must_release_candidates = _build_must_release_candidates(closed_rows_by_symbol)
    good_exit_candidates = _build_good_exit_candidates(closed_rows_by_symbol)
    bad_exit_candidates = _build_bad_exit_candidates(closed_rows_by_symbol)
    runtime_policy_snapshot = _build_runtime_policy_snapshot(runtime_status_payload)

    recent_entry_row_count = sum(len(rows) for rows in entry_rows_by_symbol.values())
    recent_closed_trade_count = sum(len(rows) for rows in closed_rows_by_symbol.values())
    casebook_seed_queue = {
        "must_show_missing": must_show_missing,
        "must_hide_leakage": must_hide_leakage,
        "must_enter_candidates": must_enter_candidates,
        "must_block_candidates": must_block_candidates,
        "visually_similar_divergence": divergence_seeds,
        "must_hold_candidates": must_hold_candidates,
        "must_release_candidates": must_release_candidates,
        "good_exit_candidates": good_exit_candidates,
        "bad_exit_candidates": bad_exit_candidates,
    }
    quick_read_summary = {
        "top_must_show_missing": [f"{row['symbol']} @ {row['time']}" for row in must_show_missing[:3]],
        "top_must_hide_leakage": [f"{row['symbol']} @ {row['time']}" for row in must_hide_leakage[:3]],
        "top_bad_exit_candidates": [f"{row['symbol']} @ {row['close_time']}" for row in bad_exit_candidates[:3]],
        "top_divergence_signatures": [row["scene_signature"] for row in divergence_seeds[:3]],
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": report_now.isoformat(timespec="seconds"),
        "input_scope": {
            "entry_decisions_path": str(entry_decisions_path),
            "runtime_status_path": str(runtime_status_path),
            "chart_flow_distribution_path": str(chart_flow_distribution_path),
            "closed_history_path": str(resolved_closed_history_path),
            "recent_rows_per_symbol": int(recent_rows_per_symbol),
            "recent_closed_trades_per_symbol": int(recent_closed_trades_per_symbol),
            "target_symbols": list(TARGET_SYMBOLS_V1),
        },
        "baseline_summary": {
            "tri_symbol_count": len(TARGET_SYMBOLS_V1),
            "recent_entry_row_count": recent_entry_row_count,
            "recent_closed_trade_count": recent_closed_trade_count,
            "must_show_missing_count": len(must_show_missing),
            "must_hide_leakage_count": len(must_hide_leakage),
            "must_enter_candidate_count": len(must_enter_candidates),
            "must_block_candidate_count": len(must_block_candidates),
            "divergence_seed_count": len(divergence_seeds),
            "must_hold_candidate_count": len(must_hold_candidates),
            "must_release_candidate_count": len(must_release_candidates),
            "good_exit_candidate_count": len(good_exit_candidates),
            "bad_exit_candidate_count": len(bad_exit_candidates),
        },
        "runtime_policy_snapshot": runtime_policy_snapshot,
        "tri_symbol_baseline_summary": tri_symbol_baseline_summary,
        "stage_density_snapshot": stage_density_snapshot,
        "display_ladder_snapshot": display_ladder_snapshot,
        "closed_trade_baseline_summary": closed_trade_baseline_summary,
        "chart_flow_snapshot": chart_flow_payload,
        "casebook_seed_queue": casebook_seed_queue,
        "quick_read_summary": quick_read_summary,
    }


def _csv_safe(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _flatten_csv_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list(report.get("tri_symbol_baseline_summary", []) or []):
        row = {"row_group": "tri_symbol_baseline"}
        row.update(item)
        rows.append(row)
    for item in list(report.get("stage_density_snapshot", []) or []):
        row = {"row_group": "stage_density"}
        row.update(item)
        rows.append(row)
    for item in list(report.get("display_ladder_snapshot", []) or []):
        row = {"row_group": "display_ladder"}
        row.update(item)
        rows.append(row)
    for item in list(report.get("closed_trade_baseline_summary", []) or []):
        row = {"row_group": "closed_trade_baseline"}
        row.update(item)
        rows.append(row)
    seed_queue = dict(report.get("casebook_seed_queue", {}) or {})
    for seed_group, items in seed_queue.items():
        for item in list(items or []):
            row = {"row_group": seed_group}
            row.update(item)
            rows.append(row)
    return rows


def _write_csv(report: dict[str, Any], path: Path) -> None:
    rows = _flatten_csv_rows(report)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["row_group"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_safe(value) for key, value in row.items()})


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = dict(report.get("baseline_summary", {}) or {})
    runtime_snapshot = dict(report.get("runtime_policy_snapshot", {}) or {})
    tri_symbol_summary = list(report.get("tri_symbol_baseline_summary", []) or [])
    seed_queue = dict(report.get("casebook_seed_queue", {}) or {})
    lines = [
        "# Product Acceptance PA0 Baseline Freeze",
        "",
        f"- `report_version`: `{report.get('report_version', '')}`",
        f"- `generated_at`: `{report.get('generated_at', '')}`",
        f"- `recent_entry_row_count`: `{summary.get('recent_entry_row_count', 0)}`",
        f"- `recent_closed_trade_count`: `{summary.get('recent_closed_trade_count', 0)}`",
        f"- `semantic_live_mode`: `{runtime_snapshot.get('semantic_live_mode', '')}`",
        "",
        "## Tri-Symbol Summary",
        "",
        "| symbol | recent_row_count | display_ready_ratio | entry_ready_count | chart_window_event_count |",
        "|---|---|---|---|---|",
    ]
    for row in tri_symbol_summary:
        lines.append(
            f"| {row.get('symbol', '')} | {row.get('recent_row_count', 0)} | {row.get('display_ready_ratio', 0)} | {row.get('entry_ready_count', 0)} | {row.get('chart_window_event_count', 0)} |"
        )

    lines.extend(["", "## Top Must-Show Missing"])
    must_show_missing = list(seed_queue.get("must_show_missing", []) or [])
    lines.extend(
        [f"- {row['symbol']} | {row['time']} | {row['seed_reason']}" for row in must_show_missing[:5]]
        or ["- (none)"]
    )

    lines.extend(["", "## Top Must-Hide Leakage"])
    must_hide_leakage = list(seed_queue.get("must_hide_leakage", []) or [])
    lines.extend(
        [f"- {row['symbol']} | {row['time']} | {row['seed_reason']}" for row in must_hide_leakage[:5]]
        or ["- (none)"]
    )

    lines.extend(["", "## Top Bad Exit Candidates"])
    bad_exit_candidates = list(seed_queue.get("bad_exit_candidates", []) or [])
    lines.extend(
        [f"- {row['symbol']} | {row['close_time']} | {row['seed_reason']}" for row in bad_exit_candidates[:5]]
        or ["- (none)"]
    )

    lines.extend(["", "## Divergence Seeds"])
    divergence_seeds = list(seed_queue.get("visually_similar_divergence", []) or [])
    lines.extend(
        [f"- {row['scene_signature']} | symbols={', '.join(row['symbols'])}" for row in divergence_seeds[:5]]
        or ["- (none)"]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_product_acceptance_pa0_baseline_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    entry_decisions_path: Path = DEFAULT_ENTRY_DECISIONS_PATH,
    runtime_status_path: Path = DEFAULT_RUNTIME_STATUS_PATH,
    chart_flow_distribution_path: Path = DEFAULT_CHART_FLOW_DISTRIBUTION_PATH,
    closed_history_path: Path = DEFAULT_CLOSED_HISTORY_PATH,
    recent_rows_per_symbol: int = 120,
    recent_closed_trades_per_symbol: int = 40,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = build_product_acceptance_pa0_baseline_report(
        entry_decisions_path=entry_decisions_path,
        runtime_status_path=runtime_status_path,
        chart_flow_distribution_path=chart_flow_distribution_path,
        closed_history_path=closed_history_path,
        recent_rows_per_symbol=recent_rows_per_symbol,
        recent_closed_trades_per_symbol=recent_closed_trades_per_symbol,
        now=now,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json_path = output_dir / "product_acceptance_pa0_baseline_latest.json"
    latest_csv_path = output_dir / "product_acceptance_pa0_baseline_latest.csv"
    latest_markdown_path = output_dir / "product_acceptance_pa0_baseline_latest.md"

    latest_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, latest_csv_path)
    _write_markdown(report, latest_markdown_path)
    return {
        "report_version": REPORT_VERSION,
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_markdown_path": str(latest_markdown_path),
        "baseline_summary": report["baseline_summary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze PA0 product acceptance baseline and capture casebook seeds.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--closed-history-path", type=Path, default=DEFAULT_CLOSED_HISTORY_PATH)
    parser.add_argument("--recent-rows-per-symbol", type=int, default=120)
    parser.add_argument("--recent-closed-trades-per-symbol", type=int, default=40)
    args = parser.parse_args()

    result = write_product_acceptance_pa0_baseline_report(
        output_dir=args.output_dir,
        closed_history_path=args.closed_history_path,
        recent_rows_per_symbol=args.recent_rows_per_symbol,
        recent_closed_trades_per_symbol=args.recent_closed_trades_per_symbol,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
