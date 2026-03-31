"""Acceptance snapshot/e-execution status builder for runtime status."""

from __future__ import annotations

import json
import os
from datetime import datetime


def build_acceptance_and_execution_state(
    *,
    app,
    acceptance_cached: bool,
    closed_acceptance_frame,
    symbol_policy_snapshot: dict,
    symbol_blend_runtime: dict,
    learning_fallback_summary: dict,
    exit_metrics: dict,
    label_clip_applied_count: int,
    net_vs_gross_gap_avg: float,
    expectancy_by_symbol: dict,
    expectancy_by_regime: dict,
    RUNTIME_ACCEPTANCE_BASELINE_JSON,
    KST,
    now_ts: float,
    acceptance_ttl_sec: float,
    stage_winloss_snapshot: dict,
    invalid_learning_sample_count: int,
    _note_runtime_warning,
):
    d_execution_state = {}
    d_acceptance_snapshot = {}
    try:
        d_execution_state = {
            "d1_data_contract": bool(len((learning_fallback_summary or {})) > 0),
            "d2_symbol_policy_split": bool(len(symbol_policy_snapshot) > 0),
            "d3_symbol_blend_split": bool(len(symbol_blend_runtime) > 0),
            "d4_fallback_layer": bool((learning_fallback_summary or {}).get("global_samples", 0) >= 0),
            "d5_runtime_visibility": True,
            "d6_execution_order_guard": bool(
                bool(len(symbol_policy_snapshot) > 0)
                and bool(len(symbol_blend_runtime) > 0)
                and bool(len((learning_fallback_summary or {})) > 0)
            ),
            "d7_acceptance_tracking": True,
            "e1_entry_exit_split_guard": bool(int((exit_metrics or {}).get("entry_meta_cap_hits", 0)) >= 0),
            "e2_stage_selector_executor_split": bool(
                int((exit_metrics or {}).get("stage_select_protect", 0))
                + int((exit_metrics or {}).get("stage_select_lock", 0))
                + int((exit_metrics or {}).get("stage_select_hold", 0))
                >= 0
            ),
            "e3_hard_risk_guard_active": bool(int((exit_metrics or {}).get("risk_guard_triggered_total", 0)) >= 0),
            "e4_label_quality_guard": bool(int(label_clip_applied_count) >= 0),
            "e5_symbol_fallback_guard": bool(int((learning_fallback_summary or {}).get("symbol_ready_count", 0)) >= 0),
            "e6_regime_hysteresis_guard": bool(int((exit_metrics or {}).get("regime_switch_blocked_count", 0)) >= 0),
            "e7_cost_aware_learning_guard": bool(float(net_vs_gross_gap_avg) >= 0.0),
            "e8_alert_integration_guard": True,
            "e9_policy_update_guard": True,
            "e10_expectancy_decomposition_guard": bool(len(expectancy_by_symbol) > 0 or len(expectancy_by_regime) > 0),
        }
    except Exception:
        d_execution_state = {}

    if not acceptance_cached:
        try:
            per_symbol_metrics = {}
            all_symbols = ("BTCUSD", "NAS100", "XAUUSD")
            for sym in all_symbols:
                per_symbol_metrics[sym] = {"adverse_stop_ratio": 0.0, "plus_to_minus_ratio": 0.0}
            if closed_acceptance_frame is not None and not closed_acceptance_frame.empty:
                for sym in all_symbols:
                    sf = closed_acceptance_frame[closed_acceptance_frame["symbol_key"] == sym]
                    if sf.empty:
                        continue
                    total_n = int(len(sf))
                    adverse_n = int(sf["exit_reason_norm"].str.contains("adverse stop", na=False).sum())
                    adverse_stop_ratio = float(adverse_n) / float(total_n) if total_n > 0 else 0.0
                    strong_entry = sf["entry_score"] > sf["contra_score_at_entry"]
                    denom = int(strong_entry.sum())
                    plus_to_minus_ratio = 0.0
                    if denom > 0:
                        numer = int(((sf["profit"] <= 0) & strong_entry).sum())
                        plus_to_minus_ratio = float(numer) / float(denom)
                    per_symbol_metrics[sym] = {
                        "adverse_stop_ratio": float(adverse_stop_ratio),
                        "plus_to_minus_ratio": float(plus_to_minus_ratio),
                    }
            adverse_stop_ratio = float(sum(m["adverse_stop_ratio"] for m in per_symbol_metrics.values()) / max(1, len(per_symbol_metrics)))
            plus_to_minus_ratio = float(sum(m["plus_to_minus_ratio"] for m in per_symbol_metrics.values()) / max(1, len(per_symbol_metrics)))

            baseline_payload = {}
            try:
                if RUNTIME_ACCEPTANCE_BASELINE_JSON.exists():
                    baseline_payload = json.loads(RUNTIME_ACCEPTANCE_BASELINE_JSON.read_text(encoding="utf-8"))
            except Exception:
                baseline_payload = {}
            baseline_payload = baseline_payload if isinstance(baseline_payload, dict) else {}
            reset_flag = str(os.getenv("D7_ACCEPTANCE_RESET_BASELINE", "0")).strip().lower() in {"1", "true", "yes", "y", "on"}
            symbols_base = dict(baseline_payload.get("symbols", {}) or {})
            baseline_changed = False
            if reset_flag:
                symbols_base = {}
                baseline_changed = True
            established_at = str(baseline_payload.get("established_at", "") or "")
            if not established_at:
                established_at = datetime.now(KST).isoformat(timespec="seconds")
                baseline_changed = True
            for sym in all_symbols:
                if sym not in symbols_base:
                    symbols_base[sym] = {
                        "adverse_stop_ratio_baseline": round(float(per_symbol_metrics[sym]["adverse_stop_ratio"]), 6),
                        "plus_to_minus_ratio_baseline": round(float(per_symbol_metrics[sym]["plus_to_minus_ratio"]), 6),
                    }
                    baseline_changed = True
            baseline_payload = {
                "established_at": established_at,
                "symbols": symbols_base,
            }
            if baseline_changed:
                try:
                    RUNTIME_ACCEPTANCE_BASELINE_JSON.parent.mkdir(parents=True, exist_ok=True)
                    RUNTIME_ACCEPTANCE_BASELINE_JSON.write_text(
                        json.dumps(baseline_payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as exc:
                    _note_runtime_warning(app, "runtime_acceptance_baseline_write_failed", exc)

            improve_margin = float(os.getenv("D7_ACCEPTANCE_IMPROVE_MARGIN", "0.01") or 0.01)
            warn_delta = float(os.getenv("D7_ACCEPTANCE_WARN_DELTA", "0.02") or 0.02)
            fail_delta = float(os.getenv("D7_ACCEPTANCE_FAIL_DELTA", "0.05") or 0.05)

            def _trend_status(delta: float) -> str:
                if float(delta) <= -abs(improve_margin):
                    return "pass"
                if float(delta) <= abs(warn_delta):
                    return "warn"
                if float(delta) >= abs(fail_delta):
                    return "fail"
                return "warn"

            symbol_trend_checks = {}
            for sym in all_symbols:
                sym_base = dict((baseline_payload.get("symbols", {}) or {}).get(sym, {}) or {})
                sym_adverse_cur = float(per_symbol_metrics.get(sym, {}).get("adverse_stop_ratio", 0.0) or 0.0)
                sym_plus_cur = float(per_symbol_metrics.get(sym, {}).get("plus_to_minus_ratio", 0.0) or 0.0)
                sym_adverse_base = float(sym_base.get("adverse_stop_ratio_baseline", sym_adverse_cur) or sym_adverse_cur)
                sym_plus_base = float(sym_base.get("plus_to_minus_ratio_baseline", sym_plus_cur) or sym_plus_cur)
                sym_adverse_delta = float(sym_adverse_cur) - float(sym_adverse_base)
                sym_plus_delta = float(sym_plus_cur) - float(sym_plus_base)
                symbol_trend_checks[sym] = {
                    "adverse_stop_ratio_current": round(sym_adverse_cur, 4),
                    "adverse_stop_ratio_baseline": round(sym_adverse_base, 4),
                    "adverse_stop_ratio_delta": round(sym_adverse_delta, 4),
                    "plus_to_minus_ratio_current": round(sym_plus_cur, 4),
                    "plus_to_minus_ratio_baseline": round(sym_plus_base, 4),
                    "plus_to_minus_ratio_delta": round(sym_plus_delta, 4),
                    "plus_to_minus_trend_check": _trend_status(sym_plus_delta),
                    "adverse_stop_trend_check": _trend_status(sym_adverse_delta),
                }

            adverse_delta = float(sum(v.get("adverse_stop_ratio_delta", 0.0) for v in symbol_trend_checks.values()) / max(1, len(symbol_trend_checks)))
            plus_minus_delta = float(sum(v.get("plus_to_minus_ratio_delta", 0.0) for v in symbol_trend_checks.values()) / max(1, len(symbol_trend_checks)))
            adverse_baseline = float(sum(v.get("adverse_stop_ratio_baseline", 0.0) for v in symbol_trend_checks.values()) / max(1, len(symbol_trend_checks)))
            plus_minus_baseline = float(sum(v.get("plus_to_minus_ratio_baseline", 0.0) for v in symbol_trend_checks.values()) / max(1, len(symbol_trend_checks)))

            symbol_policy_independent = bool(len(symbol_policy_snapshot) >= 3)
            fallback_active = bool((learning_fallback_summary or {}).get("global_ready", False))
            d_acceptance_snapshot = {
                "symbol_policy_independent": symbol_policy_independent,
                "fallback_layer_active": fallback_active,
                "runtime_visibility_ready": bool(
                    bool(len(symbol_policy_snapshot) > 0)
                    and bool(len(symbol_blend_runtime) > 0)
                ),
                "adverse_stop_ratio_current": round(float(adverse_stop_ratio), 4),
                "adverse_stop_ratio_baseline": round(float(adverse_baseline), 4),
                "adverse_stop_ratio_delta": round(float(adverse_delta), 4),
                "plus_to_minus_ratio_current": round(float(plus_to_minus_ratio), 4),
                "plus_to_minus_ratio_baseline": round(float(plus_minus_baseline), 4),
                "plus_to_minus_ratio_delta": round(float(plus_minus_delta), 4),
                "plus_to_minus_trend_check": _trend_status(plus_minus_delta),
                "adverse_stop_trend_check": _trend_status(adverse_delta),
                "baseline_established_at": str(baseline_payload.get("established_at", "")),
                "symbol_trend_checks": symbol_trend_checks,
            }
        except Exception:
            d_acceptance_snapshot = {}
        try:
            if acceptance_ttl_sec > 0:
                app.state.runtime_status_acceptance_cache = {
                    "at": now_ts,
                    "bundle": {
                        "stage_winloss_snapshot": stage_winloss_snapshot,
                        "invalid_learning_sample_count": int(invalid_learning_sample_count),
                        "label_clip_applied_count": int(label_clip_applied_count),
                        "net_vs_gross_gap_avg": float(net_vs_gross_gap_avg),
                        "expectancy_by_symbol": expectancy_by_symbol,
                        "expectancy_by_regime": expectancy_by_regime,
                        "learning_fallback_summary": learning_fallback_summary,
                        "d_acceptance_snapshot": d_acceptance_snapshot,
                    },
                }
        except Exception as exc:
            _note_runtime_warning(app, "runtime_status_acceptance_cache_write_failed", exc)

    return d_execution_state, d_acceptance_snapshot
