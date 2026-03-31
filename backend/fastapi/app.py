"""
FastAPI app skeleton for monitoring and control endpoints.
Run:
    uvicorn backend.fastapi.app:app --reload
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import Config
from backend.core.version import APP_VERSION
from adapters.file_observability_adapter import FileObservabilityAdapter
from backend.fastapi.composition import compose_runtime_components
from backend.fastapi.routers_ops import create_ops_router
from backend.fastapi.routers_trades_basic import create_trades_basic_router
from backend.fastapi.runtime_status_handler import runtime_status_handler
from backend.fastapi.trades_analytics_handler import trades_analytics_handler
from backend.fastapi.runtime_helpers import (
    cache_get as helper_cache_get,
    cache_set as helper_cache_set,
    note_runtime_warning as helper_note_runtime_warning,
    record_api_latency as helper_record_api_latency,
    sync_open_closed_state as helper_sync_open_closed_state,
    to_kst_text as helper_to_kst_text,
)
from backend.services.trade_csv_schema import (
    epoch_to_kst_text as schema_epoch_to_kst_text,
    mt5_ts_to_kst_dt as schema_mt5_ts_to_kst_dt,
    normalize_trade_df,
    text_to_kst_epoch as schema_text_to_kst_epoch,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADE_CSV = PROJECT_ROOT / "data" / "trades" / "trade_history.csv"
METRICS_JSON = PROJECT_ROOT / "models" / "metrics.json"
DEPLOY_STATE_JSON = PROJECT_ROOT / "models" / "deploy_state.json"
RUNTIME_STATUS_JSON = PROJECT_ROOT / "data" / "runtime_status.json"
RUNTIME_ACCEPTANCE_BASELINE_JSON = PROJECT_ROOT / "data" / "runtime_acceptance_baseline.json"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
FASTAPI_LOG = LOG_DIR / "fastapi.log"
DOCS_DIR = PROJECT_ROOT / "docs"
RUNBOOK_DOC = DOCS_DIR / "OPERATIONS_RUNBOOK.md"
ALERT_POLICY_DOC = DOCS_DIR / "ALERT_POLICY.md"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"
STEP11_DOC = PROJECT_ROOT / "0_흐름" / "STEP11_관측성_확정.md"
STEP12_DOC = PROJECT_ROOT / "0_흐름" / "STEP12_운영변경관리_확정.md"


def _configure_app_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("backend.fastapi")
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        fh = RotatingFileHandler(str(FASTAPI_LOG), maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(fh)
    return logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger = _configure_app_logging()
    observability = FileObservabilityAdapter()
    app_logger.info("Application startup begin")
    observability.event("fastapi_startup_begin", payload={"service": "backend.fastapi"})
    components = compose_runtime_components(PROJECT_ROOT, TRADE_CSV)
    mt5_snapshot_service = components["mt5_snapshot_service"]
    try:
        mt5_snapshot_service.start_background_snapshot()
    except Exception:
        app_logger.exception("Failed to start MT5 background snapshot loop")
    for name, instance in components.items():
        setattr(app.state, name, instance)
    app.state.app_logger = app_logger
    app.state.observability = observability
    observability.event("fastapi_startup_complete")
    app_logger.info("Application startup complete")
    try:
        yield
    finally:
        try:
            mt5_snapshot_service.stop_background_snapshot()
        except Exception:
            app_logger.exception("Failed to stop MT5 background snapshot loop")
            observability.incr("fastapi_shutdown_error_total", 1)
            observability.event("fastapi_shutdown_error", level="error")
        observability.event("fastapi_shutdown")
        app_logger.info("Application shutdown")


app = FastAPI(title="CFD Trading API", version=APP_VERSION, lifespan=lifespan)
runtime_router = APIRouter(tags=["runtime"])
trades_router = APIRouter(tags=["trades"])
ml_router = APIRouter(tags=["ml"])
ops_router = APIRouter(tags=["ops"])
KST = ZoneInfo("Asia/Seoul")
_EP_CACHE = {}
_SYNC_STATE = {"last_ts": 0.0}
try:
    _SYNC_MIN_INTERVAL_SEC = max(1.0, float(os.getenv("SYNC_MIN_INTERVAL_SEC", "5.0") or 5.0))
except Exception:
    _SYNC_MIN_INTERVAL_SEC = 5.0
_SYNC_LOCK = Lock()


def _cache_get(key: str, ttl_sec: float):
    return helper_cache_get(_EP_CACHE, key, ttl_sec)


def _cache_set(key: str, value):
    helper_cache_set(_EP_CACHE, key, value)


def _note_runtime_warning(app: FastAPI, key: str, exc: Exception | None = None) -> None:
    helper_note_runtime_warning(app, KST, key, exc)


def _record_api_latency(app: FastAPI, method: str, path: str, status_code: int, elapsed_ms: float, ok: bool) -> None:
    helper_record_api_latency(app, KST, method, path, status_code, elapsed_ms, ok)


def _compute_runtime_acceptance_bundle(trade_read_service, csv_history_service) -> dict:
    stage_winloss_snapshot = {}
    closed_acceptance_frame = pd.DataFrame()
    invalid_learning_sample_count = 0
    label_clip_applied_count = 0
    net_vs_gross_gap_avg = 0.0
    learning_fallback_summary = {}
    expectancy_by_symbol = {}
    expectancy_by_regime = {}
    expectancy_by_hour_bucket = {}

    closed_df = trade_read_service.read_closed_trade_df()
    if closed_df is not None and not closed_df.empty and "profit" in closed_df.columns:
        needed_cols = [c for c in ("profit", "gross_pnl", "cost_total", "net_pnl_after_cost", "close_ts", "row_ts", "exit_policy_stage", "exit_policy_regime", "symbol", "entry_score", "contra_score_at_entry", "exit_reason") if c in closed_df.columns]
        frame = closed_df[needed_cols].copy()
        frame["profit"] = pd.to_numeric(frame.get("profit", 0.0), errors="coerce").fillna(0.0)
        frame["gross_pnl"] = pd.to_numeric(frame.get("gross_pnl", frame["profit"]), errors="coerce").fillna(frame["profit"])
        frame["cost_total"] = pd.to_numeric(frame.get("cost_total", 0.0), errors="coerce").fillna(0.0)
        frame["net_pnl_after_cost"] = pd.to_numeric(frame.get("net_pnl_after_cost", frame["gross_pnl"] - frame["cost_total"]), errors="coerce").fillna(frame["gross_pnl"] - frame["cost_total"])
        frame["close_ts"] = pd.to_numeric(frame.get("close_ts", 0), errors="coerce").fillna(0).astype(int)
        frame["row_ts"] = pd.to_numeric(frame.get("row_ts", frame.get("close_ts", 0)), errors="coerce").fillna(0).astype(int)
        frame["exit_policy_stage"] = frame.get("exit_policy_stage", "").astype(str).str.strip().str.lower()
        frame["exit_policy_regime"] = frame.get("exit_policy_regime", "").fillna("").astype(str).str.strip().str.upper()
        frame = frame[frame["exit_policy_stage"].isin(["short", "mid", "long"])].copy()
        if not frame.empty:
            frame = frame.sort_values("row_ts", ascending=False).head(300)
            for stage in ("short", "mid", "long"):
                part = frame[frame["exit_policy_stage"] == stage]
                if part.empty:
                    stage_winloss_snapshot[stage] = {"trades": 0, "win_rate": 0.0, "pnl": 0.0, "avg_profit": 0.0}
                    continue
                stage_winloss_snapshot[stage] = {
                    "trades": int(len(part)),
                    "win_rate": round(float((part["profit"] > 0).mean()), 4),
                    "pnl": round(float(part["profit"].sum()), 4),
                    "avg_profit": round(float(part["profit"].mean()), 4),
                }
            frame["entry_score"] = pd.to_numeric(frame.get("entry_score", 0.0), errors="coerce").fillna(0.0)
            frame["contra_score_at_entry"] = pd.to_numeric(frame.get("contra_score_at_entry", 0.0), errors="coerce").fillna(0.0)
            frame["symbol_key"] = frame.get("symbol", "").map(_canonical_symbol)
            frame["exit_reason_norm"] = frame.get("exit_reason", "").fillna("").astype(str).str.lower()
            frame["hour_bucket"] = pd.to_numeric(frame.get("close_ts", 0), errors="coerce").fillna(0).astype(int).map(
                lambda ts: datetime.fromtimestamp(int(ts), KST).strftime("%H:00") if int(ts) > 0 else "UNKNOWN"
            )

            def _exp_stats(g: pd.Series) -> dict:
                x = pd.to_numeric(g, errors="coerce").fillna(0.0)
                n = int(len(x))
                if n <= 0:
                    return {"trades": 0, "expectancy": 0.0, "win_rate": 0.0}
                return {
                    "trades": n,
                    "expectancy": round(float(x.mean()), 6),
                    "win_rate": round(float((x > 0).mean()), 4),
                }

            by_sym = frame.groupby("symbol_key", dropna=False)["net_pnl_after_cost"].apply(_exp_stats).to_dict()
            by_reg = frame.groupby(frame["exit_policy_regime"].where(frame["exit_policy_regime"].str.strip() != "", "UNKNOWN"), dropna=False)["net_pnl_after_cost"].apply(_exp_stats).to_dict()
            by_hr = frame.groupby("hour_bucket", dropna=False)["net_pnl_after_cost"].apply(_exp_stats).to_dict()
            expectancy_by_symbol = {str(k): v for k, v in by_sym.items()}
            expectancy_by_regime = {str(k): v for k, v in by_reg.items()}
            expectancy_by_hour_bucket = {str(k): v for k, v in by_hr.items()}
            closed_acceptance_frame = frame

    learning_view = csv_history_service.get_training_and_history_rows(per_symbol_limit=300)
    invalid_learning_sample_count = int(learning_view.get("invalid_learning_sample_count", 0) or 0)
    label_clip_applied_count = int(learning_view.get("label_clip_applied_count", 0) or 0)
    net_vs_gross_gap_avg = float(learning_view.get("net_vs_gross_gap_avg", 0.0) or 0.0)
    learning_fallback_summary = dict(learning_view.get("learning_fallback_summary", {}) or {})

    return {
        "stage_winloss_snapshot": stage_winloss_snapshot,
        "closed_acceptance_frame": closed_acceptance_frame,
        "invalid_learning_sample_count": invalid_learning_sample_count,
        "label_clip_applied_count": label_clip_applied_count,
        "net_vs_gross_gap_avg": net_vs_gross_gap_avg,
        "learning_fallback_summary": learning_fallback_summary,
        "expectancy_by_symbol": expectancy_by_symbol,
        "expectancy_by_regime": expectancy_by_regime,
        "expectancy_by_hour_bucket": expectancy_by_hour_bucket,
    }


def _sync_open_closed_state(force: bool = False) -> None:
    helper_sync_open_closed_state(
        app=app,
        sync_state=_SYNC_STATE,
        sync_lock=_SYNC_LOCK,
        sync_min_interval_sec=_SYNC_MIN_INTERVAL_SEC,
        note_warning=_note_runtime_warning,
        force=force,
    )


def _mt5_ts_to_kst(ts: int) -> datetime:
    return schema_mt5_ts_to_kst_dt(ts)


def _to_kst_text(value: str) -> str:
    return helper_to_kst_text(value, KST)


def _text_to_kst_epoch(value: str) -> int:
    return schema_text_to_kst_epoch(value)


def _epoch_to_kst_text(ts: int) -> str:
    return schema_epoch_to_kst_text(ts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://127.0.0.1:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _request_log_middleware(request: Request, call_next):
    logger = logging.getLogger("backend.fastapi")
    observability = getattr(app.state, "observability", None)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _record_api_latency(app, request.method, request.url.path, int(getattr(response, "status_code", 0) or 0), elapsed_ms, True)
        if observability is not None:
            observability.incr("api_request_total", 1)
            if int(getattr(response, "status_code", 0) or 0) >= 500:
                observability.incr("api_request_5xx_total", 1)
            observability.event(
                "api_request",
                payload={
                    "method": str(request.method or ""),
                    "path": str(request.url.path or ""),
                    "status": int(getattr(response, "status_code", 0) or 0),
                    "elapsed_ms": round(float(elapsed_ms), 3),
                },
            )
        logger.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, elapsed_ms)
        return response
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _record_api_latency(app, request.method, request.url.path, 500, elapsed_ms, False)
        if observability is not None:
            observability.incr("api_request_total", 1)
            observability.incr("api_request_error_total", 1)
            observability.event(
                "api_request_exception",
                level="error",
                payload={
                    "method": str(request.method or ""),
                    "path": str(request.url.path or ""),
                    "elapsed_ms": round(float(elapsed_ms), 3),
                },
            )
        logger.exception("%s %s -> EXCEPTION (%.1fms)", request.method, request.url.path, elapsed_ms)
        raise


def _safe_read_trade_csv():
    return app.state.trade_read_service.read_trade_df()


def _safe_float(v, default=0.0) -> float:
    try:
        n = float(v)
        if pd.isna(n):
            return float(default)
        return n
    except Exception:
        return float(default)


def _canonical_symbol(symbol: str) -> str:
    s = str(symbol or "").upper()
    if "BTC" in s:
        return "BTCUSD"
    if "NAS" in s or "US100" in s or "USTEC" in s:
        return "NAS100"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    return ""


def _runtime_profile_thresholds(profile_name: str) -> dict[str, float]:
    p = str(profile_name or "neutral").strip().lower()
    if p == "conservative":
        return {
            "stoplike_warn_ratio": 0.25,
            "stoplike_bad_ratio": 0.35,
            "capture_warn_ratio": 0.25,
            "capture_good_ratio": 0.40,
            "adverse_reversal_warn_ratio": 0.04,
            "adverse_reversal_bad_ratio": 0.08,
            "reversal_warn_ratio": 0.22,
            "scalp_good_ratio": 0.12,
        }
    if p == "aggressive":
        return {
            "stoplike_warn_ratio": 0.35,
            "stoplike_bad_ratio": 0.55,
            "capture_warn_ratio": 0.15,
            "capture_good_ratio": 0.30,
            "adverse_reversal_warn_ratio": 0.08,
            "adverse_reversal_bad_ratio": 0.16,
            "reversal_warn_ratio": 0.38,
            "scalp_good_ratio": 0.20,
        }
    return {
        "stoplike_warn_ratio": 0.30,
        "stoplike_bad_ratio": 0.45,
        "capture_warn_ratio": 0.20,
        "capture_good_ratio": 0.35,
        "adverse_reversal_warn_ratio": 0.06,
        "adverse_reversal_bad_ratio": 0.12,
        "reversal_warn_ratio": 0.30,
        "scalp_good_ratio": 0.15,
    }


def _runtime_extract_regime_name(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    reg = payload.get("regime")
    if isinstance(reg, dict):
        return str(reg.get("name", "") or "").strip().upper()
    if isinstance(reg, str):
        return reg.strip().upper()
    return str(payload.get("regime_name", "") or "").strip().upper()


def _runtime_env_or(name: str, fallback: float) -> float:
    raw = os.getenv(name, "")
    if str(raw).strip() == "":
        return float(fallback)
    try:
        return float(raw)
    except Exception:
        return float(fallback)


def _classify_release_gate(active_alerts: int, rollback_count: int, warning_total: int) -> dict[str, Any]:
    reasons: list[str] = []
    if int(active_alerts) > 0:
        reasons.append("active_alerts")
    if int(rollback_count) > 0:
        reasons.append("policy_rollback")
    if reasons:
        return {"grade": "fail", "reasons": reasons}
    if int(warning_total) > 0:
        return {"grade": "warn", "reasons": ["runtime_warnings"]}
    return {"grade": "pass", "reasons": []}


ops_router = create_ops_router(
    app=app,
    kst=KST,
    app_version=APP_VERSION,
    runbook_doc=RUNBOOK_DOC,
    alert_policy_doc=ALERT_POLICY_DOC,
    changelog_md=CHANGELOG_MD,
    step11_doc=STEP11_DOC,
    step12_doc=STEP12_DOC,
    runtime_status_json=RUNTIME_STATUS_JSON,
    project_root=PROJECT_ROOT,
    classify_release_gate=_classify_release_gate,
)
trades_basic_router = create_trades_basic_router(
    app=app,
    cache_get=_cache_get,
    cache_set=_cache_set,
    sync_open_closed_state=_sync_open_closed_state,
)


@runtime_router.get("/runtime/observability")
def runtime_observability(last_n: int = 50):
    obs = getattr(app.state, "observability", None)
    if obs is None:
        return {"exists": False, "snapshot": None}
    return {"exists": True, "snapshot": obs.snapshot(last_n=last_n)}


@ml_router.get("/ml/metrics")
def ml_metrics():
    if not METRICS_JSON.exists():
        return {"exists": False, "metrics": None}
    return {"exists": True, "metrics": json.loads(METRICS_JSON.read_text(encoding="utf-8"))}


@ml_router.get("/ml/deploy-state")
def ml_deploy_state():
    if not DEPLOY_STATE_JSON.exists():
        return {"exists": False, "state": None}
    return {"exists": True, "state": json.loads(DEPLOY_STATE_JSON.read_text(encoding="utf-8"))}


@runtime_router.get("/runtime/status")
def runtime_status():
    return runtime_status_handler(
        app=app,
        Config=Config,
        KST=KST,
        RUNTIME_STATUS_JSON=RUNTIME_STATUS_JSON,
        RUNTIME_ACCEPTANCE_BASELINE_JSON=RUNTIME_ACCEPTANCE_BASELINE_JSON,
        _note_runtime_warning=_note_runtime_warning,
        _compute_runtime_acceptance_bundle=_compute_runtime_acceptance_bundle,
        _canonical_symbol=_canonical_symbol,
        _runtime_extract_regime_name=_runtime_extract_regime_name,
        _runtime_profile_thresholds=_runtime_profile_thresholds,
        _runtime_env_or=_runtime_env_or,
    )


@ml_router.get("/ml/learning-overview")
def ml_learning_overview(days: int = 120):
    cache_key = f"ml_learning_overview:{int(days)}"
    cached = _cache_get(cache_key, ttl_sec=30.0)
    if cached is not None:
        return cached

    days = max(14, min(365, int(days)))
    out = {
        "exists": True,
        "days": days,
        "as_of": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "model_metrics": {},
        "runtime_ai_config": {},
        "entry_before_after": {
            "trace_count": 0,
            "avg_raw_score": 0.0,
            "avg_final_score": 0.0,
            "avg_score_adj": 0.0,
            "avg_probability": 0.0,
        },
        "symbol_adjustments": [],
        "exit_before_after": {
            "base_window": {},
            "recent_window": {},
        },
    }

    if METRICS_JSON.exists():
        try:
            out["model_metrics"] = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
        except Exception as exc:
            _note_runtime_warning(app, "learning_overview_metrics_read_failed", exc)

    rt = {}
    if RUNTIME_STATUS_JSON.exists():
        try:
            rt = json.loads(RUNTIME_STATUS_JSON.read_text(encoding="utf-8"))
        except Exception:
            rt = {}
    out["runtime_ai_config"] = rt.get("ai_config", {}) if isinstance(rt, dict) else {}

    traces = (rt.get("ai_entry_traces", []) if isinstance(rt, dict) else []) or []
    if traces:
        tdf = pd.DataFrame(traces)
        for c in ["raw_score", "final_score", "score_adj", "probability"]:
            if c in tdf.columns:
                tdf[c] = pd.to_numeric(tdf[c], errors="coerce")
        out["entry_before_after"] = {
            "trace_count": int(len(tdf)),
            "avg_raw_score": round(float(tdf.get("raw_score", pd.Series(dtype=float)).fillna(0.0).mean()), 4),
            "avg_final_score": round(float(tdf.get("final_score", pd.Series(dtype=float)).fillna(0.0).mean()), 4),
            "avg_score_adj": round(float(tdf.get("score_adj", pd.Series(dtype=float)).fillna(0.0).mean()), 4),
            "avg_probability": round(float(tdf.get("probability", pd.Series(dtype=float)).fillna(0.0).mean()), 4),
        }

    closed = app.state.trade_read_service.read_closed_trade_df()
    if closed.empty:
        _cache_set(cache_key, out)
        return out

    closed = normalize_trade_df(closed)
    closed["dt"] = pd.to_datetime(closed.get("close_time", ""), errors="coerce")
    if "open_time" in closed.columns:
        closed["dt"] = closed["dt"].fillna(pd.to_datetime(closed.get("open_time", ""), errors="coerce"))
    closed = closed[closed["dt"].notna()].copy()
    if closed.empty:
        _cache_set(cache_key, out)
        return out
    cutoff = pd.Timestamp.now(tz=None) - pd.Timedelta(days=days)
    closed = closed[closed["dt"] >= cutoff].copy()
    if closed.empty:
        _cache_set(cache_key, out)
        return out

    for c in ["entry_score", "exit_score", "profit"]:
        closed[c] = pd.to_numeric(closed.get(c, 0.0), errors="coerce").fillna(0.0)
    closed["canonical_symbol"] = closed.get("symbol", "").map(_canonical_symbol)
    closed = closed[closed["canonical_symbol"] != ""].copy()
    if closed.empty:
        _cache_set(cache_key, out)
        return out

    def _window_stats(frame: pd.DataFrame) -> dict:
        if frame.empty:
            return {
                "trades": 0,
                "win_rate": 0.0,
                "avg_profit": 0.0,
                "avg_entry_score": 0.0,
                "avg_exit_score": 0.0,
                "profit_factor": 0.0,
                "payoff_ratio": 0.0,
            }
        wins = frame[frame["profit"] > 0]["profit"]
        losses = frame[frame["profit"] < 0]["profit"].abs()
        gross_profit = float(wins.sum()) if not wins.empty else 0.0
        gross_loss = float(losses.sum()) if not losses.empty else 0.0
        avg_win = float(wins.mean()) if not wins.empty else 0.0
        avg_loss = float(losses.mean()) if not losses.empty else 0.0
        return {
            "trades": int(len(frame)),
            "win_rate": round(float((frame["profit"] > 0).mean()), 4),
            "avg_profit": round(float(frame["profit"].mean()), 4),
            "avg_entry_score": round(float(frame["entry_score"].mean()), 4),
            "avg_exit_score": round(float(frame["exit_score"].mean()), 4),
            "profit_factor": round(float(gross_profit / max(1e-9, gross_loss)), 4),
            "payoff_ratio": round(float(avg_win / max(1e-9, avg_loss)), 4),
        }

    closed = closed.sort_values("dt").reset_index(drop=True)
    split_idx = max(1, len(closed) // 2)
    out["exit_before_after"] = {
        "base_window": _window_stats(closed.iloc[:split_idx]),
        "recent_window": _window_stats(closed.iloc[split_idx:]),
    }

    symbol_rows = []
    for sym in ["BTCUSD", "NAS100", "XAUUSD"]:
        part = closed[closed["canonical_symbol"] == sym].copy()
        if part.empty:
            continue
        part = part.sort_values("dt")
        sx = max(1, len(part) // 2)
        base = _window_stats(part.iloc[:sx])
        recent = _window_stats(part.iloc[sx:])
        winners = part[part["profit"] > 0]
        good_exit = part[part["profit"] >= max(0.0, _safe_float(Config.MIN_NET_PROFIT_USD))]

        suggested_entry = int(round(float(winners["entry_score"].quantile(0.60)))) if len(winners) >= 8 else int(Config.ENTRY_THRESHOLD)
        suggested_exit = int(round(float(good_exit["exit_score"].quantile(0.50)))) if len(good_exit) >= 8 else int(Config.EXIT_THRESHOLD)
        suggested_entry = max(90, min(320, suggested_entry))
        suggested_exit = max(70, min(300, suggested_exit))

        symbol_rows.append(
            {
                "symbol": sym,
                "trades": int(len(part)),
                "current_avg_entry_score": round(float(part["entry_score"].mean()), 4),
                "current_avg_exit_score": round(float(part["exit_score"].mean()), 4),
                "suggested_entry_threshold": suggested_entry,
                "suggested_exit_threshold": suggested_exit,
                "base_window": base,
                "recent_window": recent,
                "delta_win_rate": round(float(recent["win_rate"] - base["win_rate"]), 4),
                "delta_avg_profit": round(float(recent["avg_profit"] - base["avg_profit"]), 4),
                "delta_profit_factor": round(float(recent["profit_factor"] - base["profit_factor"]), 4),
                "delta_avg_exit_score": round(float(recent["avg_exit_score"] - base["avg_exit_score"]), 4),
            }
        )

    out["symbol_adjustments"] = symbol_rows
    _cache_set(cache_key, out)
    return out


@trades_router.get("/trades/analytics")
def trades_analytics(days: int = 30, sync: bool = False):
    return trades_analytics_handler(
        app=app,
        days=days,
        sync=sync,
        _cache_get=_cache_get,
        _cache_set=_cache_set,
        _sync_open_closed_state=_sync_open_closed_state,
        TRADE_CSV=TRADE_CSV,
        RUNTIME_STATUS_JSON=RUNTIME_STATUS_JSON,
        _note_runtime_warning=_note_runtime_warning,
        _safe_float=_safe_float,
        Config=Config,
    )


@runtime_router.get("/mt5/status")
def mt5_status():
    # Phase-2: delegated to snapshot service.
    return app.state.mt5_snapshot_service.get_mt5_status()


@runtime_router.get("/positions/enriched")
def positions_enriched(sync: bool = False, refresh: bool = False, timeout_ms: int = 250):
    # Avoid blocking current-position UI on heavy reconcile path.
    if bool(sync):
        _sync_open_closed_state(force=True)
    # Phase-2: delegated to snapshot service.
    return app.state.mt5_snapshot_service.get_positions_enriched(
        force_refresh=bool(refresh),
        timeout_ms=max(50, min(2000, int(timeout_ms or 250))),
    )


app.include_router(runtime_router)
app.include_router(trades_router)
app.include_router(trades_basic_router)
app.include_router(ml_router)
app.include_router(ops_router)



