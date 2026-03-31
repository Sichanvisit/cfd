"""Runtime status endpoint handler extracted from app.py."""

from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd

from backend.fastapi.runtime_status_acceptance import build_acceptance_and_execution_state
from backend.fastapi.runtime_status_alerts import build_runtime_alerts
from backend.fastapi.runtime_status_kpi import evaluate_runtime_kpi
from backend.fastapi.runtime_market_view import build_current_market_view
from backend.fastapi.runtime_status_policy import build_policy_learning_state
from backend.fastapi.runtime_status_ui_map import build_ui_card_field_map


def runtime_status_handler(
    *,
    app,
    Config,
    KST,
    RUNTIME_STATUS_JSON,
    RUNTIME_ACCEPTANCE_BASELINE_JSON,
    _note_runtime_warning,
    _compute_runtime_acceptance_bundle,
    _canonical_symbol,
    _runtime_extract_regime_name,
    _runtime_profile_thresholds,
    _runtime_env_or,
):
    try:
        runtime_ttl_sec = max(0.0, float(os.getenv("RUNTIME_STATUS_TTL_SEC", "8.0") or 8.0))
    except Exception:
        runtime_ttl_sec = 8.0
    now_ts = float(datetime.now(KST).timestamp())
    cache_obj = None
    cached_payload = None
    try:
        if runtime_ttl_sec > 0:
            cache_obj = getattr(app.state, "runtime_status_cache", None)
            if isinstance(cache_obj, dict):
                cached_payload = cache_obj.get("payload")
                cached_at = float(cache_obj.get("at", 0.0) or 0.0)
                if cached_payload is not None and (now_ts - cached_at) <= runtime_ttl_sec:
                    return cached_payload
    except Exception as exc:
        _note_runtime_warning(app, "runtime_status_cache_read_failed", exc)
    def _cache_and_return(resp: dict):
        try:
            if runtime_ttl_sec > 0:
                app.state.runtime_status_cache = {"at": now_ts, "payload": resp}
        except Exception as exc:
            _note_runtime_warning(app, "runtime_status_cache_write_failed", exc)
        return resp

    def _read_runtime_status_payload_cached():
        try:
            if not RUNTIME_STATUS_JSON.exists():
                return None
            mtime_ns = int(RUNTIME_STATUS_JSON.stat().st_mtime_ns)
        except Exception:
            return None
        try:
            cache_obj = getattr(app.state, "runtime_status_payload_cache", None)
            if isinstance(cache_obj, dict) and int(cache_obj.get("mtime_ns", -1)) == mtime_ns:
                cached_payload = cache_obj.get("payload")
                if isinstance(cached_payload, dict):
                    return cached_payload
        except Exception as exc:
            _note_runtime_warning(app, "runtime_status_payload_cache_read_failed", exc)
        try:
            payload_obj = json.loads(RUNTIME_STATUS_JSON.read_text(encoding="utf-8"))
            if isinstance(payload_obj, dict):
                app.state.runtime_status_payload_cache = {"mtime_ns": mtime_ns, "payload": payload_obj}
                return payload_obj
        except Exception:
            return None
        return None

    base_profile = str(getattr(Config, "EXIT_UI_PROFILE", "neutral") or "neutral").strip().lower()
    effective_profile = base_profile
    exit_metrics = {}
    payload = None
    stage_selection_distribution = {}
    stage_winloss_snapshot = {}
    invalid_learning_sample_count = 0
    label_clip_applied_count = 0
    net_vs_gross_gap_avg = 0.0
    expectancy_by_symbol = {}
    expectancy_by_regime = {}
    expectancy_by_hour_bucket = {}
    runtime_warning_counters = dict(getattr(app.state, "runtime_warning_counters", {}) or {})
    api_latency_snapshot = dict(getattr(app.state, "api_latency_snapshot", {}) or {})
    closed_acceptance_frame = pd.DataFrame()
    learning_fallback_summary = {}
    policy_snapshot = {}
    learning_apply_loop = {}
    exit_blend_runtime = {}
    d_acceptance_snapshot = {}
    kpi_evaluation = {}
    sqlite_mirror_status = {}
    runtime_alerts = {"active_count": 0, "items": [], "last_transition_at": ""}
    acceptance_cached = False
    try:
        acceptance_ttl_sec = max(0.0, float(os.getenv("RUNTIME_STATUS_ACCEPTANCE_TTL_SEC", "30.0") or 30.0))
    except Exception:
        acceptance_ttl_sec = 30.0
    try:
        acceptance_cache_obj = getattr(app.state, "runtime_status_acceptance_cache", None)
        if acceptance_ttl_sec > 0 and isinstance(acceptance_cache_obj, dict):
            cached_at = float(acceptance_cache_obj.get("at", 0.0) or 0.0)
            if (now_ts - cached_at) <= acceptance_ttl_sec:
                bundle = acceptance_cache_obj.get("bundle", {}) or {}
                stage_winloss_snapshot = dict(bundle.get("stage_winloss_snapshot", {}) or {})
                invalid_learning_sample_count = int(bundle.get("invalid_learning_sample_count", 0) or 0)
                label_clip_applied_count = int(bundle.get("label_clip_applied_count", 0) or 0)
                net_vs_gross_gap_avg = float(bundle.get("net_vs_gross_gap_avg", 0.0) or 0.0)
                expectancy_by_symbol = dict(bundle.get("expectancy_by_symbol", {}) or {})
                expectancy_by_regime = dict(bundle.get("expectancy_by_regime", {}) or {})
                expectancy_by_hour_bucket = dict(bundle.get("expectancy_by_hour_bucket", {}) or {})
                learning_fallback_summary = dict(bundle.get("learning_fallback_summary", {}) or {})
                d_acceptance_snapshot = dict(bundle.get("d_acceptance_snapshot", {}) or {})
                acceptance_cached = True
    except Exception as exc:
        _note_runtime_warning(app, "runtime_status_acceptance_cache_read_failed", exc)
        acceptance_cached = False
    try:
        exit_service = getattr(app.state, "exit_service", None)
        if exit_service is None:
            trading_app = getattr(app.state, "trading_app", None)
            if trading_app is not None:
                exit_service = getattr(trading_app, "exit_service", None)
        if exit_service is None:
            snapshot_service = getattr(app.state, "mt5_snapshot_service", None)
            if snapshot_service is not None:
                exit_service = getattr(snapshot_service, "exit_service", None)
        if exit_service is not None and hasattr(exit_service, "get_exit_metrics"):
            exit_metrics = exit_service.get_exit_metrics() or {}
    except Exception:
        exit_metrics = {}
    try:
        trade_logger = getattr(app.state, "trade_logger", None)
        if trade_logger is not None and hasattr(trade_logger, "get_store_health_snapshot"):
            sqlite_mirror_status = dict(trade_logger.get_store_health_snapshot() or {})
    except Exception:
        sqlite_mirror_status = {}

    try:
        ss_protect = int(exit_metrics.get("stage_select_protect", 0))
        ss_lock = int(exit_metrics.get("stage_select_lock", 0))
        ss_hold = int(exit_metrics.get("stage_select_hold", 0))
        ss_total = max(1, ss_protect + ss_lock + ss_hold)
        stage_selection_distribution = {
            "short": {"count": ss_protect, "ratio": round(float(ss_protect / ss_total), 4)},
            "mid": {"count": ss_lock, "ratio": round(float(ss_lock / ss_total), 4)},
            "long": {"count": ss_hold, "ratio": round(float(ss_hold / ss_total), 4)},
            "protect": {"count": ss_protect, "ratio": round(float(ss_protect / ss_total), 4)},
            "lock": {"count": ss_lock, "ratio": round(float(ss_lock / ss_total), 4)},
            "hold": {"count": ss_hold, "ratio": round(float(ss_hold / ss_total), 4)},
            "total": int(ss_protect + ss_lock + ss_hold),
        }
    except Exception:
        stage_selection_distribution = {}

    if not acceptance_cached:
        try:
            acceptance_bundle = _compute_runtime_acceptance_bundle(
                app.state.trade_read_service,
                app.state.csv_history_service,
            )
            stage_winloss_snapshot = dict(acceptance_bundle.get("stage_winloss_snapshot", {}) or {})
            closed_acceptance_frame = acceptance_bundle.get("closed_acceptance_frame", pd.DataFrame())
            invalid_learning_sample_count = int(acceptance_bundle.get("invalid_learning_sample_count", 0) or 0)
            label_clip_applied_count = int(acceptance_bundle.get("label_clip_applied_count", 0) or 0)
            net_vs_gross_gap_avg = float(acceptance_bundle.get("net_vs_gross_gap_avg", 0.0) or 0.0)
            learning_fallback_summary = dict(acceptance_bundle.get("learning_fallback_summary", {}) or {})
            expectancy_by_symbol = dict(acceptance_bundle.get("expectancy_by_symbol", {}) or {})
            expectancy_by_regime = dict(acceptance_bundle.get("expectancy_by_regime", {}) or {})
            expectancy_by_hour_bucket = dict(acceptance_bundle.get("expectancy_by_hour_bucket", {}) or {})
        except Exception as exc:
            _note_runtime_warning(app, "runtime_acceptance_compute_failed", exc)
            stage_winloss_snapshot = {}
            closed_acceptance_frame = pd.DataFrame()
            invalid_learning_sample_count = 0
            label_clip_applied_count = 0
            net_vs_gross_gap_avg = 0.0
            learning_fallback_summary = {}
            expectancy_by_symbol = {}
            expectancy_by_regime = {}
            expectancy_by_hour_bucket = {}

    payload = _read_runtime_status_payload_cached()
    if isinstance(payload, dict):
        if not exit_metrics:
            status_obj = payload.get("status", {})
            if isinstance(status_obj, dict):
                payload_exit_metrics = status_obj.get("exit_metrics")
                if isinstance(payload_exit_metrics, dict):
                    exit_metrics = payload_exit_metrics
            if not exit_metrics:
                payload_exit_metrics = payload.get("exit_metrics")
                if isinstance(payload_exit_metrics, dict):
                    exit_metrics = payload_exit_metrics
        p_policy = payload.get("policy_snapshot")
        if isinstance(p_policy, dict):
            policy_snapshot = p_policy

    if isinstance(exit_metrics, dict):
        exit_blend_runtime = {
            "mode": str(exit_metrics.get("blend_mode", "") or ""),
            "rule_weight": float(exit_metrics.get("blend_rule_weight", 0.0) or 0.0),
            "model_weight": float(exit_metrics.get("blend_model_weight", 0.0) or 0.0),
            "history": list(exit_metrics.get("blend_history", []) or []),
            "symbol_blend_runtime": dict(exit_metrics.get("symbol_blend_runtime", {}) or {}),
        }
    policy_learning_state = build_policy_learning_state(
        Config=Config,
        policy_snapshot=policy_snapshot,
        payload=payload,
        now_ts=float(now_ts),
        _canonical_symbol=_canonical_symbol,
        exit_blend_runtime=exit_blend_runtime,
    )
    symbol_policy_snapshot = dict(policy_learning_state.get("symbol_policy_snapshot", {}) or {})
    symbol_default_snapshot = dict(policy_learning_state.get("symbol_default_snapshot", {}) or {})
    symbol_applied_vs_default = dict(policy_learning_state.get("symbol_applied_vs_default", {}) or {})
    symbol_learning_split = dict(policy_learning_state.get("symbol_learning_split", {}) or {})
    learning_apply_loop = dict(policy_learning_state.get("learning_apply_loop", {}) or {})
    symbol_blend_runtime = dict(policy_learning_state.get("symbol_blend_runtime", {}) or {})
    d_execution_state, d_acceptance_snapshot = build_acceptance_and_execution_state(
        app=app,
        acceptance_cached=acceptance_cached,
        closed_acceptance_frame=closed_acceptance_frame,
        symbol_policy_snapshot=symbol_policy_snapshot,
        symbol_blend_runtime=symbol_blend_runtime,
        learning_fallback_summary=learning_fallback_summary,
        exit_metrics=exit_metrics,
        label_clip_applied_count=int(label_clip_applied_count),
        net_vs_gross_gap_avg=float(net_vs_gross_gap_avg),
        expectancy_by_symbol=expectancy_by_symbol,
        expectancy_by_regime=expectancy_by_regime,
        RUNTIME_ACCEPTANCE_BASELINE_JSON=RUNTIME_ACCEPTANCE_BASELINE_JSON,
        KST=KST,
        now_ts=float(now_ts),
        acceptance_ttl_sec=float(acceptance_ttl_sec),
        stage_winloss_snapshot=stage_winloss_snapshot,
        invalid_learning_sample_count=int(invalid_learning_sample_count),
        _note_runtime_warning=_note_runtime_warning,
    )

    try:
        kpi_evaluation = evaluate_runtime_kpi(
            expectancy_by_symbol=expectancy_by_symbol,
            d_acceptance_snapshot=d_acceptance_snapshot,
            stage_winloss_snapshot=stage_winloss_snapshot,
        )
    except Exception as exc:
        _note_runtime_warning(app, "runtime_kpi_evaluation_failed", exc)
        kpi_evaluation = {}

    try:
        runtime_alerts = build_runtime_alerts(
            KST=KST,
            sqlite_mirror_status=sqlite_mirror_status,
            d_acceptance_snapshot=d_acceptance_snapshot,
            exit_metrics=exit_metrics,
            policy_snapshot=policy_snapshot,
        )
    except Exception as exc:
        _note_runtime_warning(app, "runtime_alerts_build_failed", exc)
        runtime_alerts = {"active_count": 0, "items": [], "last_transition_at": ""}

    if base_profile == "auto":
        regime_name = _runtime_extract_regime_name(payload if isinstance(payload, dict) else {})
        if regime_name in {"EXPANSION", "TREND"}:
            effective_profile = "aggressive"
        elif regime_name in {"RANGE", "LOW_LIQUIDITY"}:
            effective_profile = "conservative"
        else:
            effective_profile = "neutral"

    preset_thresholds = _runtime_profile_thresholds(effective_profile)
    exit_metric_thresholds = {
        "profile": effective_profile,
        "profile_source": base_profile,
        "stoplike_warn_ratio": _runtime_env_or("EXIT_UI_STOPLIKE_WARN_RATIO", preset_thresholds["stoplike_warn_ratio"]),
        "stoplike_bad_ratio": _runtime_env_or("EXIT_UI_STOPLIKE_BAD_RATIO", preset_thresholds["stoplike_bad_ratio"]),
        "capture_warn_ratio": _runtime_env_or("EXIT_UI_CAPTURE_WARN_RATIO", preset_thresholds["capture_warn_ratio"]),
        "capture_good_ratio": _runtime_env_or("EXIT_UI_CAPTURE_GOOD_RATIO", preset_thresholds["capture_good_ratio"]),
        "adverse_reversal_warn_ratio": _runtime_env_or("EXIT_UI_ADVERSE_REV_WARN_RATIO", preset_thresholds["adverse_reversal_warn_ratio"]),
        "adverse_reversal_bad_ratio": _runtime_env_or("EXIT_UI_ADVERSE_REV_BAD_RATIO", preset_thresholds["adverse_reversal_bad_ratio"]),
        "reversal_warn_ratio": _runtime_env_or("EXIT_UI_REVERSAL_WARN_RATIO", preset_thresholds["reversal_warn_ratio"]),
        "scalp_good_ratio": _runtime_env_or("EXIT_UI_SCALP_GOOD_RATIO", preset_thresholds["scalp_good_ratio"]),
        "blend_rule_warn_low": _runtime_env_or("EXIT_UI_BLEND_RULE_WARN_LOW", 0.30),
        "blend_rule_warn_high": _runtime_env_or("EXIT_UI_BLEND_RULE_WARN_HIGH", 0.70),
        "blend_rule_bad_low": _runtime_env_or("EXIT_UI_BLEND_RULE_BAD_LOW", 0.15),
        "blend_rule_bad_high": _runtime_env_or("EXIT_UI_BLEND_RULE_BAD_HIGH", 0.85),
        "blend_model_warn_low": _runtime_env_or("EXIT_UI_BLEND_MODEL_WARN_LOW", 0.30),
        "blend_model_warn_high": _runtime_env_or("EXIT_UI_BLEND_MODEL_WARN_HIGH", 0.70),
        "blend_model_bad_low": _runtime_env_or("EXIT_UI_BLEND_MODEL_BAD_LOW", 0.15),
        "blend_model_bad_high": _runtime_env_or("EXIT_UI_BLEND_MODEL_BAD_HIGH", 0.85),
        "blend_drift_warn": _runtime_env_or("EXIT_UI_BLEND_DRIFT_WARN", 0.20),
        "blend_drift_bad": _runtime_env_or("EXIT_UI_BLEND_DRIFT_BAD", 0.40),
        "blend_sticky_min_history": _runtime_env_or("EXIT_UI_BLEND_STICKY_MIN_HISTORY", 8.0),
        "blend_sticky_max_drift": _runtime_env_or("EXIT_UI_BLEND_STICKY_MAX_DRIFT", 0.03),
    }
    regime_name_now = _runtime_extract_regime_name(payload if isinstance(payload, dict) else {})
    exit_exec_profile_cfg = str(getattr(Config, "EXIT_EXEC_PROFILE", "auto") or "auto").strip().lower()
    if exit_exec_profile_cfg == "auto":
        if regime_name_now in {"EXPANSION", "TREND"}:
            exit_exec_profile_eff = "aggressive"
        elif regime_name_now in {"RANGE", "LOW_LIQUIDITY"}:
            exit_exec_profile_eff = "conservative"
        else:
            exit_exec_profile_eff = "neutral"
    elif exit_exec_profile_cfg in {"conservative", "aggressive", "neutral"}:
        exit_exec_profile_eff = exit_exec_profile_cfg
    else:
        exit_exec_profile_eff = "neutral"
    exit_execution_profile = {
        "configured": exit_exec_profile_cfg,
        "effective": exit_exec_profile_eff,
        "regime": regime_name_now,
    }
    ui_card_field_map = build_ui_card_field_map()
    current_market_view = build_current_market_view(payload if isinstance(payload, dict) else None)

    if payload is None:
        return _cache_and_return({
            "exists": False,
            "status": None,
            "exit_metrics": exit_metrics,
            "exit_metric_thresholds": exit_metric_thresholds,
            "exit_execution_profile": exit_execution_profile,
            "stage_selection_distribution": stage_selection_distribution,
            "stage_winloss_snapshot": stage_winloss_snapshot,
            "invalid_learning_sample_count": invalid_learning_sample_count,
            "label_clip_applied_count": label_clip_applied_count,
            "net_vs_gross_gap_avg": net_vs_gross_gap_avg,
            "expectancy_by_symbol": expectancy_by_symbol,
            "expectancy_by_regime": expectancy_by_regime,
            "expectancy_by_hour_bucket": expectancy_by_hour_bucket,
            "runtime_warning_counters": runtime_warning_counters,
            "api_latency_snapshot": api_latency_snapshot,
            "learning_fallback_summary": learning_fallback_summary,
            "policy_snapshot": policy_snapshot,
            "sqlite_mirror_status": sqlite_mirror_status,
            "exit_blend_runtime": exit_blend_runtime,
            "alerts": runtime_alerts,
            "symbol_policy_snapshot": symbol_policy_snapshot,
            "symbol_default_snapshot": symbol_default_snapshot,
            "symbol_applied_vs_default": symbol_applied_vs_default,
            "symbol_learning_split": symbol_learning_split,
            "symbol_blend_runtime": symbol_blend_runtime,
            "learning_apply_loop": learning_apply_loop,
            "d_execution_state": d_execution_state,
            "d_acceptance_snapshot": d_acceptance_snapshot,
            "kpi_evaluation": kpi_evaluation,
            "current_market_view": current_market_view,
            "ui_card_field_map": ui_card_field_map,
        })
    if isinstance(payload, dict):
        payload["exit_metrics"] = exit_metrics
        payload["exit_metric_thresholds"] = exit_metric_thresholds
        payload["exit_execution_profile"] = exit_execution_profile
        payload["stage_selection_distribution"] = stage_selection_distribution
        payload["stage_winloss_snapshot"] = stage_winloss_snapshot
        payload["invalid_learning_sample_count"] = invalid_learning_sample_count
        payload["label_clip_applied_count"] = label_clip_applied_count
        payload["net_vs_gross_gap_avg"] = net_vs_gross_gap_avg
        payload["expectancy_by_symbol"] = expectancy_by_symbol
        payload["expectancy_by_regime"] = expectancy_by_regime
        payload["expectancy_by_hour_bucket"] = expectancy_by_hour_bucket
        payload["runtime_warning_counters"] = runtime_warning_counters
        payload["api_latency_snapshot"] = api_latency_snapshot
        payload["learning_fallback_summary"] = learning_fallback_summary
        payload["policy_snapshot"] = policy_snapshot
        payload["sqlite_mirror_status"] = sqlite_mirror_status
        payload["exit_blend_runtime"] = exit_blend_runtime
        payload["alerts"] = runtime_alerts
        payload["symbol_policy_snapshot"] = symbol_policy_snapshot
        payload["symbol_default_snapshot"] = symbol_default_snapshot
        payload["symbol_applied_vs_default"] = symbol_applied_vs_default
        payload["symbol_learning_split"] = symbol_learning_split
        payload["symbol_blend_runtime"] = symbol_blend_runtime
        payload["learning_apply_loop"] = learning_apply_loop
        payload["d_execution_state"] = d_execution_state
        payload["d_acceptance_snapshot"] = d_acceptance_snapshot
        payload["kpi_evaluation"] = kpi_evaluation
        payload["current_market_view"] = current_market_view
        payload["ui_card_field_map"] = ui_card_field_map
    return _cache_and_return({
        "exists": True,
        "status": payload,
        "exit_metrics": exit_metrics,
        "exit_metric_thresholds": exit_metric_thresholds,
        "exit_execution_profile": exit_execution_profile,
        "stage_selection_distribution": stage_selection_distribution,
        "stage_winloss_snapshot": stage_winloss_snapshot,
        "invalid_learning_sample_count": invalid_learning_sample_count,
        "label_clip_applied_count": label_clip_applied_count,
        "net_vs_gross_gap_avg": net_vs_gross_gap_avg,
        "expectancy_by_symbol": expectancy_by_symbol,
        "expectancy_by_regime": expectancy_by_regime,
        "expectancy_by_hour_bucket": expectancy_by_hour_bucket,
        "runtime_warning_counters": runtime_warning_counters,
        "api_latency_snapshot": api_latency_snapshot,
        "learning_fallback_summary": learning_fallback_summary,
        "policy_snapshot": policy_snapshot,
        "sqlite_mirror_status": sqlite_mirror_status,
        "exit_blend_runtime": exit_blend_runtime,
        "alerts": runtime_alerts,
        "symbol_policy_snapshot": symbol_policy_snapshot,
        "symbol_default_snapshot": symbol_default_snapshot,
        "symbol_applied_vs_default": symbol_applied_vs_default,
        "symbol_learning_split": symbol_learning_split,
        "symbol_blend_runtime": symbol_blend_runtime,
        "learning_apply_loop": learning_apply_loop,
        "d_execution_state": d_execution_state,
        "d_acceptance_snapshot": d_acceptance_snapshot,
        "kpi_evaluation": kpi_evaluation,
        "current_market_view": current_market_view,
        "ui_card_field_map": ui_card_field_map,
    })


