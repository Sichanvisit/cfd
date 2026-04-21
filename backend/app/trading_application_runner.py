# 한글 설명: TradingApplication의 메인 run 루프(조립/순회/실행 흐름)를 외부로 분리한 실행 모듈입니다.
"""Main run-loop orchestration extracted from TradingApplication."""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from adapters.mt5_connection_adapter import connect_to_mt5, disconnect_mt5
from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY
from backend.trading.chart_painter import Painter
from backend.trading.scorer import Scorer
from backend.trading.symbol_resolver import SymbolResolver
from backend.trading.trade_logger import TradeLogger
from backend.services.entry_service import EntryService
from backend.services.exit_service import ExitService
from backend.services.context_classifier import ContextClassifier
from backend.services.exit_profile_router import resolve_exit_profile
from backend.services.belief_state25_runtime_bridge import (
    build_belief_state25_runtime_bridge_v1,
)
from backend.services.barrier_state25_runtime_bridge import (
    build_barrier_state25_runtime_bridge_v1,
)
from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_state25_runtime_bridge_v1,
)
from backend.services.policy_service import PolicyService
from backend.services.runtime_recycle import evaluate_runtime_recycle
from backend.services.runtime_recycle import (
    build_runtime_recycle_drift_v1,
    build_runtime_recycle_health_v1,
)
from backend.services.telegram_ops_service import TelegramOpsService
from backend.services.storage_compaction import (
    build_probe_quick_trace_fields,
    json_payload_size_bytes,
    resolve_runtime_signal_row_key,
    summarize_trace_quality,
)
from backend.services.strategy_service import StrategyService

logger = logging.getLogger(__name__)


def _safe_boottrace(stage: str) -> None:
    message = str(stage or "").strip()
    if not message:
        return
    try:
        print(f"[boottrace] {message}", flush=True)
    except OSError:
        logger.debug("boottrace suppressed: %s", message)


def _resolve_symbol_loop_profile_path(config=Config) -> Path:
    raw_path = str(getattr(config, "SYMBOL_LOOP_PROFILE_PATH", "") or "").strip()
    path = Path(raw_path) if raw_path else Path(r"data\analysis\symbol_loop_profile_latest.json")
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path.resolve()


def _record_symbol_stage_timing(stage_timings_ms: dict[str, float], stage_name: str, started_at: float) -> None:
    stage_timings_ms[str(stage_name)] = round((time.perf_counter() - float(started_at)) * 1000.0, 3)


def _build_symbol_loop_profile(
    *,
    loop_count: int,
    symbol: str,
    elapsed_sec: float,
    stage_timings_ms: dict[str, float],
    snapshot_row: dict | None = None,
) -> dict:
    stage_timings_ms = {str(k): float(v) for k, v in dict(stage_timings_ms or {}).items()}
    dominant_stage = ""
    dominant_stage_ms = 0.0
    if stage_timings_ms:
        dominant_stage, dominant_stage_ms = max(stage_timings_ms.items(), key=lambda item: float(item[1]))
    snapshot_row = dict(snapshot_row or {})
    return {
        "contract_version": "symbol_loop_profile_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "loop_count": int(loop_count),
        "symbol": str(symbol or ""),
        "elapsed_sec": round(float(elapsed_sec), 6),
        "is_slow": bool(float(elapsed_sec) >= float(getattr(Config, "SYMBOL_LOOP_SLOW_WARN_SEC", 3.0) or 3.0)),
        "dominant_stage": str(dominant_stage or ""),
        "dominant_stage_ms": round(float(dominant_stage_ms or 0.0), 3),
        "stage_timings_ms": stage_timings_ms,
        "snapshot": {
            "observe_reason": str(snapshot_row.get("observe_reason", "") or ""),
            "observe_action": str(snapshot_row.get("observe_action", "") or ""),
            "observe_side": str(snapshot_row.get("observe_side", "") or ""),
            "blocked_by": str(snapshot_row.get("blocked_by", "") or ""),
            "action_none_reason": str(snapshot_row.get("action_none_reason", "") or ""),
            "quick_trace_state": str(snapshot_row.get("quick_trace_state", "") or ""),
            "probe_scene_id": str(snapshot_row.get("probe_scene_id", "") or ""),
            "action": str(snapshot_row.get("action", "") or ""),
            "outcome": str(snapshot_row.get("outcome", "") or ""),
        },
    }


def _snapshot_exit_fields(prev_signal_row: dict | None, *, pos_count: int) -> dict:
    prev_signal_row = dict(prev_signal_row or {})
    if int(pos_count or 0) <= 0:
        return {
            "exit_decision_context_v1": {},
            "exit_decision_result_v1": {},
            "exit_prediction_v1": {},
            "exit_recovery_prediction_v1": {},
            "exit_utility_v1": {},
            "exit_wait_state_v1": {},
            "exit_decision_winner": "",
            "exit_decision_reason": "",
        }
    return {
        "exit_decision_context_v1": prev_signal_row.get("exit_decision_context_v1", {}),
        "exit_decision_result_v1": prev_signal_row.get("exit_decision_result_v1", {}),
        "exit_prediction_v1": prev_signal_row.get("exit_prediction_v1", {}),
        "exit_recovery_prediction_v1": prev_signal_row.get("exit_recovery_prediction_v1", {}),
        "exit_utility_v1": prev_signal_row.get("exit_utility_v1", {}),
        "exit_wait_state_v1": prev_signal_row.get("exit_wait_state_v1", {}),
        "exit_decision_winner": prev_signal_row.get("exit_decision_winner", ""),
        "exit_decision_reason": prev_signal_row.get("exit_decision_reason", ""),
    }


def _write_symbol_loop_profile(app, profile: dict) -> None:
    if not bool(getattr(Config, "SYMBOL_LOOP_PROFILE_ENABLED", True)):
        return
    path = _resolve_symbol_loop_profile_path(Config)
    state = getattr(app, "symbol_loop_profile_state", None)
    if not isinstance(state, dict):
        state = {
            "contract_version": "symbol_loop_profile_collection_v1",
            "latest_by_symbol": {},
            "recent_slow_events": [],
        }
    latest_by_symbol = dict(state.get("latest_by_symbol", {}) or {})
    symbol = str((profile or {}).get("symbol", "") or "")
    if symbol:
        latest_by_symbol[symbol] = dict(profile or {})
    recent_slow_events = list(state.get("recent_slow_events", []) or [])
    if bool((profile or {}).get("is_slow", False)):
        recent_slow_events.append(dict(profile or {}))
        recent_slow_events = recent_slow_events[-12:]
    payload = {
        "contract_version": "symbol_loop_profile_collection_v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "slow_warn_sec": float(getattr(Config, "SYMBOL_LOOP_SLOW_WARN_SEC", 3.0) or 3.0),
        "latest_by_symbol": latest_by_symbol,
        "recent_slow_events": recent_slow_events,
    }
    app.symbol_loop_profile_state = payload
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Failed to write symbol loop profile: %s", path)


def _write_runtime_status_progress(app, *, loop_count: int, symbols: dict, policy_service, detail: str = "") -> None:
    try:
        app._write_runtime_status(
            loop_count,
            symbols,
            policy_service.entry_threshold,
            policy_service.exit_threshold,
            adverse_loss_usd=policy_service.adverse_loss_usd,
            reverse_signal_threshold=policy_service.reverse_signal_threshold,
            policy_snapshot=policy_service.get_runtime_snapshot(),
        )
        if detail:
            app._write_loop_debug(loop_count=loop_count, stage="runtime_status_progress", detail=str(detail or ""))
    except Exception:
        logger.exception("Failed to write runtime status progress: %s", detail)


def _sync_flow_history_from_runtime_rows(app, painter: Painter, symbols: dict) -> None:
    if not isinstance(symbols, dict):
        return
    latest_rows = getattr(app, "latest_signal_by_symbol", None)
    if not isinstance(latest_rows, dict):
        return
    timeframe_1m = None
    try:
        timeframe_1m = (getattr(app, "TIMEFRAMES", {}) or {}).get("1M")
    except Exception:
        timeframe_1m = None
    for symbol in symbols.values():
        row = latest_rows.get(symbol, {})
        if not isinstance(row, dict) or not row:
            continue
        try:
            painter.sync_flow_history_from_runtime_row(symbol, row)
        except Exception:
            logger.exception("Failed to sync flow history from runtime row: %s", symbol)


def _decision_time_to_epoch(text: str) -> int:
    value = str(text or "").strip()
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _resolve_recent_setup_from_decisions(*, decision_csv: Path, symbol: str, direction: str, open_ts: int) -> str:
    try:
        if not decision_csv.exists():
            return ""
        matches = []
        with decision_csv.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("symbol", "")).upper() != str(symbol or "").upper():
                    continue
                if str(row.get("action", "")).upper() != str(direction or "").upper():
                    continue
                if str(row.get("outcome", "")).lower() != "entered":
                    continue
                setup_id = str(row.get("setup_id", "") or "").strip().lower()
                if not setup_id:
                    continue
                event_ts = _decision_time_to_epoch(row.get("time", ""))
                if open_ts > 0 and event_ts > 0 and abs(int(open_ts) - int(event_ts)) > 600:
                    continue
                distance = abs(int(open_ts) - int(event_ts)) if (open_ts > 0 and event_ts > 0) else 999999
                matches.append((distance, -event_ts, setup_id))
        if not matches:
            return ""
        matches.sort()
        return str(matches[0][2] or "").strip().lower()
    except Exception:
        return ""


def _collect_runtime_recycle_position_counts(app) -> dict[str, int]:
    total_open_positions = 0
    owned_open_positions = 0
    try:
        positions = app.broker.positions_get() or []
        total_open_positions = len(positions)
        owned_open_positions = sum(
            1
            for position in positions
            if int(getattr(position, "magic", 0) or 0) == int(getattr(Config, "MAGIC_NUMBER", 0))
        )
    except Exception:
        logger.exception("Failed to collect runtime recycle position counts")
    return {
        "open_positions_count": int(total_open_positions),
        "owned_open_positions_count": int(owned_open_positions),
    }


def _maybe_handle_runtime_recycle(app, *, loop_count: int) -> dict:
    counts = _collect_runtime_recycle_position_counts(app)
    now_ts = time.time()
    recent_runtime_summary = dict(getattr(app, "runtime_recent_summary_cache", {}) or {})
    default_recent_window = dict(getattr(app, "runtime_recent_default_window_cache", {}) or {})
    health_snapshot = build_runtime_recycle_health_v1(
        recent_runtime_summary=recent_runtime_summary,
        default_recent_window=default_recent_window,
        latest_signal_by_symbol=getattr(app, "latest_signal_by_symbol", {}),
        now_ts=now_ts,
        signal_stale_sec=int(getattr(Config, "RUNTIME_RECYCLE_SIGNAL_STALE_SEC", 900) or 900),
    )
    drift_snapshot = build_runtime_recycle_drift_v1(
        recent_runtime_summary=recent_runtime_summary,
        default_recent_window=default_recent_window,
        latest_signal_by_symbol=getattr(app, "latest_signal_by_symbol", {}),
        now_ts=now_ts,
        min_rows=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_MIN_ROWS", 40) or 40),
        stage_dominance_threshold=float(getattr(Config, "RUNTIME_RECYCLE_DRIFT_STAGE_DOMINANCE", 0.85) or 0.85),
        block_dominance_threshold=float(getattr(Config, "RUNTIME_RECYCLE_DRIFT_BLOCK_DOMINANCE", 0.85) or 0.85),
        decision_dominance_threshold=float(
            getattr(Config, "RUNTIME_RECYCLE_DRIFT_DECISION_DOMINANCE", 0.90) or 0.90
        ),
        min_signal_count=int(getattr(Config, "RUNTIME_RECYCLE_DRIFT_SIGNAL_MIN_COUNT", 2) or 2),
    )
    app.runtime_recycle_health_state = dict(health_snapshot or {})
    app.runtime_recycle_drift_state = dict(drift_snapshot or {})
    decision = evaluate_runtime_recycle(
        getattr(app, "runtime_recycle_state", {}),
        loop_count=int(loop_count),
        mode=str(getattr(Config, "RUNTIME_RECYCLE_MODE", "log_only") or "log_only"),
        interval_sec=int(getattr(Config, "RUNTIME_RECYCLE_INTERVAL_SEC", 3600) or 0),
        flat_grace_sec=int(getattr(Config, "RUNTIME_RECYCLE_FLAT_GRACE_SEC", 30) or 0),
        post_order_grace_sec=int(getattr(Config, "RUNTIME_RECYCLE_POST_ORDER_GRACE_SEC", 90) or 0),
        open_positions_count=int(counts.get("open_positions_count", 0) or 0),
        owned_open_positions_count=int(counts.get("owned_open_positions_count", 0) or 0),
        last_order_ts=float(getattr(app, "last_order_ts", 0.0) or 0.0),
        health_snapshot=health_snapshot,
        drift_snapshot=drift_snapshot,
        now_ts=now_ts,
    )
    app.runtime_recycle_state = dict(decision.get("state", {}) or {})
    action = str(decision.get("action", "") or "")
    if action == "none":
        return decision

    stage = "runtime_recycle_log_only" if action == "log_only" else "runtime_recycle_reexec"
    detail = (
        f"reason={decision.get('reason', '')} "
        f"trigger_family={decision.get('trigger_family', '')} "
        f"uptime_sec={int(decision.get('uptime_sec', 0) or 0)} "
        f"open_positions={int(decision.get('open_positions_count', 0) or 0)} "
        f"owned_positions={int(decision.get('owned_open_positions_count', 0) or 0)}"
    )
    app._write_loop_debug(loop_count=loop_count, stage=stage, detail=detail)
    app._obs_inc("runtime_recycle_trigger_total", 1)
    app._obs_event(stage, payload={k: v for k, v in decision.items() if k != "state"})
    logger.info(
        "runtime recycle action=%s reason=%s trigger_family=%s uptime_sec=%s open_positions=%s owned_positions=%s",
        action,
        decision.get("reason", ""),
        decision.get("trigger_family", ""),
        int(decision.get("uptime_sec", 0) or 0),
        int(decision.get("open_positions_count", 0) or 0),
        int(decision.get("owned_open_positions_count", 0) or 0),
    )
    return decision


def _build_runtime_reexec_argv() -> list[str]:
    project_root = Path(__file__).resolve().parents[2]
    argv = list(sys.argv or [])
    if not argv:
        return [sys.executable, str(project_root / "main.py")]

    first = str(argv[0] or "").strip()
    if first.endswith(".py"):
        script_path = Path(first)
        if not script_path.is_absolute():
            argv[0] = str((project_root / script_path).resolve())
        return [sys.executable, *argv]

    return list(argv)


def _perform_runtime_reexec() -> None:
    exec_argv = _build_runtime_reexec_argv()
    if exec_argv and exec_argv[0] != sys.executable:
        program = exec_argv[0]
    else:
        program = sys.executable
    os.chdir(Path(__file__).resolve().parents[2])
    logger.warning("Executing guarded runtime recycle via execv: %s", exec_argv)
    os.execv(program, exec_argv)


def _wait_for_mt5_connection(app) -> None:
    retry_delay_sec = max(1.0, float(getattr(Config, "MT5_CONNECT_RETRY_DELAY_SEC", 10) or 10))
    attempt = 0
    while True:
        attempt += 1
        if connect_to_mt5():
            app._obs_inc("mt5_connect_success_total", 1)
            app._obs_event("mt5_connect_success", payload={"attempt": int(attempt)})
            if attempt > 1:
                logger.info("MT5 connection recovered after %s attempts", attempt)
            return

        app._obs_inc("mt5_connect_failed_total", 1)
        app._obs_event(
            "mt5_connect_failed",
            level="error",
            payload={"attempt": int(attempt), "retry_in_sec": float(retry_delay_sec)},
        )
        app.last_order_error = "MT5 connect/login failed"
        app.last_order_comment = "retry_pending"
        app.last_order_retcode = None
        app._write_loop_debug(
            loop_count=0,
            stage="mt5_connect_failed",
            detail=f"attempt={attempt} retry_in_sec={retry_delay_sec:.0f}",
        )
        app.refresh_state25_candidate_runtime_state()
        app._write_runtime_status(
            0,
            {},
            int(getattr(Config, "ENTRY_THRESHOLD", 0) or 0),
            int(getattr(Config, "EXIT_THRESHOLD", 0) or 0),
            policy_snapshot={
                "boot_state": "mt5_connect_failed",
                "connect_attempt": int(attempt),
                "connect_retry_delay_sec": float(retry_delay_sec),
            },
        )
        logger.warning(
            "MT5 connection unavailable. retrying in %.1fs (attempt=%s)",
            retry_delay_sec,
            attempt,
        )
        time.sleep(retry_delay_sec)


def run_trading_application(app) -> None:
    log_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(str(log_dir / "bot.log"), maxBytes=10_000_000, backupCount=5, encoding="utf-8"),
        ],
    )
    app._obs_event("trading_loop_start", payload={"service": "trading_application"})

    _wait_for_mt5_connection(app)

    resolver = SymbolResolver()
    symbols = resolver.find_symbols()
    if not symbols:
        print("[오류] 거래 가능한 심볼을 찾지 못했습니다.")
        disconnect_mt5()
        return

    scorer = Scorer()
    strategy_service = StrategyService(scorer)
    trade_logger = TradeLogger(filename=str(getattr(Config, "TRADE_HISTORY_CSV_PATH", r"data\trades\trade_history.csv")))
    telegram_ops = TelegramOpsService()
    decision_csv = Path(trade_logger.filepath).with_name("entry_decisions.csv")
    policy_service = PolicyService(trade_logger, Config)
    entry_service = EntryService(app, trade_logger)
    exit_service = ExitService(app, trade_logger)
    context_classifier = ContextClassifier(app.broker)

    open_rows, closed_with_deal, force_closed_unknown = policy_service.reconcile_startup(lookback_days=120)
    if open_rows > 0:
        print(
            f"[Startup] trade log reconcile: open={open_rows}, "
            f"closed_with_deal={closed_with_deal}, force_closed_unknown={force_closed_unknown}"
        )
    painter = Painter()
    def _runtime_flow_history_sync_hook(rows: dict) -> None:
        if not isinstance(rows, dict):
            return
        for symbol, row in rows.items():
            if not isinstance(row, dict):
                continue
            try:
                painter.sync_flow_history_from_runtime_row(str(symbol), row)
            except Exception:
                logger.exception("Failed to sync runtime flow history hook: %s", symbol)

    app.runtime_flow_history_sync_hook = _runtime_flow_history_sync_hook
    if getattr(scorer, "session_mgr", None) is not None:
        painter.session_mgr = scorer.session_mgr
    if getattr(scorer, "trend_mgr", None) is not None:
        painter.trend_mgr = scorer.trend_mgr

    app._print_startup_symbols(symbols)
    for sym in symbols.values():
        app.last_entry_time[sym] = 0

    loop_count = 0
    recycle_request = None
    try:
        while True:
            loop_count += 1
            if loop_count == 1:
                _safe_boottrace("stage=loop_start")
            app._write_loop_debug(loop_count=loop_count, stage="loop_start")
            app.refresh_state25_candidate_runtime_state()
            _sync_flow_history_from_runtime_rows(app, painter, symbols)
            app._write_runtime_status(
                loop_count,
                symbols,
                policy_service.entry_threshold,
                policy_service.exit_threshold,
                adverse_loss_usd=policy_service.adverse_loss_usd,
                reverse_signal_threshold=policy_service.reverse_signal_threshold,
                policy_snapshot=policy_service.get_runtime_snapshot(),
            )
            if loop_count == 1:
                _safe_boottrace("stage=runtime_status_returned")
            app._write_loop_debug(loop_count=loop_count, stage="runtime_status_written")
            app._write_loop_debug(loop_count=loop_count, stage="runtime_flow_history_synced")
            app._refresh_ai_runtime_if_needed()
            if loop_count == 1:
                _safe_boottrace("stage=ai_runtime_refreshed")
            app._write_loop_debug(loop_count=loop_count, stage="ai_runtime_refreshed")

            if loop_count % 10 == 1:
                if loop_count == 1:
                    _safe_boottrace("stage=active_symbols_refresh_start")
                app._write_loop_debug(loop_count=loop_count, stage="active_symbols_refresh_start")
                resolver.get_active_symbols()
                if loop_count == 1:
                    _safe_boottrace("stage=active_symbols_refresh_done")
                app._write_loop_debug(loop_count=loop_count, stage="active_symbols_refresh_done")
                if loop_count % 100 == 1:
                    if loop_count == 1:
                        _safe_boottrace("stage=resolver_status_print_start")
                    app._write_loop_debug(loop_count=loop_count, stage="resolver_status_print_start")
                    resolver.print_status()
                    if loop_count == 1:
                        _safe_boottrace("stage=resolver_status_print_done")
                    app._write_loop_debug(loop_count=loop_count, stage="resolver_status_print_done")

            if loop_count == 1:
                _safe_boottrace("stage=policy_refresh_start")
            app._write_loop_debug(loop_count=loop_count, stage="policy_refresh_start")
            if bool(getattr(Config, "ENABLE_POLICY_LOOP_REFRESH", False)):
                for note in policy_service.maybe_refresh(loop_count):
                    print(f"[Policy] {note}")
                for note in policy_service.maybe_maintain_shock_ops(loop_count):
                    print(f"[ShockOps] {note}")
                if loop_count == 1:
                    _safe_boottrace("stage=policy_refresh_done")
                app._write_loop_debug(loop_count=loop_count, stage="policy_refresh_done")
            else:
                if loop_count == 1:
                    _safe_boottrace("stage=policy_refresh_skipped")
                app._write_loop_debug(loop_count=loop_count, stage="policy_refresh_skipped")

            if loop_count == 1:
                _safe_boottrace("stage=account_info_start")
            app._write_loop_debug(loop_count=loop_count, stage="account_info_start")
            account = app.broker.account_info()
            if loop_count == 1:
                _safe_boottrace("stage=account_info_done")
            app._write_loop_debug(loop_count=loop_count, stage="account_info_done")
            loss_limit = account.balance * Config.LOSS_LIMIT_PERCENT if account else 99999

            for _, symbol in symbols.items():
                started_at = time.perf_counter()
                stage_timings_ms = {}
                app._write_loop_debug(loop_count=loop_count, stage="symbol_start", symbol=symbol)
                stage_started_at = time.perf_counter()
                sym_policy = policy_service.get_symbol_policy(symbol)
                is_active, reason = resolver.check_market_active(symbol)
                tick = app.broker.symbol_info_tick(symbol)
                _record_symbol_stage_timing(stage_timings_ms, "market_gate", stage_started_at)
                if not tick:
                    elapsed = time.perf_counter() - started_at
                    _write_symbol_loop_profile(
                        app,
                        _build_symbol_loop_profile(
                            loop_count=loop_count,
                            symbol=symbol,
                            elapsed_sec=elapsed,
                            stage_timings_ms=stage_timings_ms,
                        ),
                    )
                    app._write_loop_debug(loop_count=loop_count, stage="symbol_skip_no_tick", symbol=symbol)
                    continue

                df_all = {}
                stage_started_at = time.perf_counter()
                for tf_name, tf_const in app.TIMEFRAMES.items():
                    df = app.fetch_data(symbol, tf_const)
                    if df is not None:
                        df_all[tf_name] = df
                _record_symbol_stage_timing(stage_timings_ms, "fetch_data", stage_started_at)

                if "1M" not in df_all or "15M" not in df_all or "1H" not in df_all:
                    elapsed = time.perf_counter() - started_at
                    _write_symbol_loop_profile(
                        app,
                        _build_symbol_loop_profile(
                            loop_count=loop_count,
                            symbol=symbol,
                            elapsed_sec=elapsed,
                            stage_timings_ms=stage_timings_ms,
                        ),
                    )
                    app._write_loop_debug(loop_count=loop_count, stage="symbol_skip_missing_tf", symbol=symbol)
                    continue

                stage_started_at = time.perf_counter()
                result = strategy_service.evaluate(symbol, tick, df_all)
                _record_symbol_stage_timing(stage_timings_ms, "strategy_evaluate", stage_started_at)
                if isinstance(result, dict):
                    app.latest_regime_by_symbol[symbol] = result.get("regime", {})
                buy_s = result["buy"]["total"]
                sell_s = result["sell"]["total"]
                wait_s = int(((result or {}).get("wait", {}) or {}).get("total", 0) or 0)
                wait_reasons = list(((result or {}).get("wait", {}) or {}).get("reasons", []) or [])
                wait_conflict = int(((result or {}).get("components", {}) or {}).get("wait_conflict", 0) or 0)
                wait_noise = int(((result or {}).get("components", {}) or {}).get("wait_noise", 0) or 0)
                sniper = app.calculate_sniper_indicators(df_all["1M"])

                positions = app.broker.positions_get(symbol=symbol)
                my_positions = [p for p in positions if p.magic == Config.MAGIC_NUMBER] if positions else []
                pos_count = len(my_positions)
                can_long = bool(buy_s >= int(sym_policy.get("entry_threshold", policy_service.entry_threshold)))
                can_short = bool(sell_s >= int(sym_policy.get("entry_threshold", policy_service.entry_threshold)))
                max_positions_for_symbol = int(Config.get_max_positions(symbol))
                stage_started_at = time.perf_counter()
                context_bundle = context_classifier.build_entry_context(
                    symbol=symbol,
                    tick=tick,
                    df_all=df_all,
                    scorer=scorer,
                    result=result,
                    buy_s=float(buy_s),
                    sell_s=float(sell_s),
                )
                _record_symbol_stage_timing(stage_timings_ms, "context_build", stage_started_at)
                current_context = context_bundle.get("context")
                position_snapshot = context_bundle.get("position_snapshot")
                position_snapshot_v2 = position_snapshot.to_dict() if position_snapshot is not None else {}
                response_raw_snapshot_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("response_raw_snapshot_v1", {}) or {}))
                )
                response_vector_v2 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("response_vector_v2", {}) or {}))
                )
                state_raw_snapshot_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("state_raw_snapshot_v1", {}) or {}))
                )
                state_vector_v2 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("state_vector_v2", {}) or {}))
                )
                evidence_vector_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("evidence_vector_v1", {}) or {}))
                )
                belief_state_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("belief_state_v1", {}) or {}))
                )
                barrier_state_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("barrier_state_v1", {}) or {}))
                )
                forecast_features_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("forecast_features_v1", {}) or {}))
                )
                transition_forecast_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("transition_forecast_v1", {}) or {}))
                )
                trade_management_forecast_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("trade_management_forecast_v1", {}) or {}))
                )
                forecast_gap_metrics_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("forecast_gap_metrics_v1", {}) or {}))
                )
                observe_confirm_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_v1", {}) or {}))
                )
                observe_confirm_v2 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_v2", {}) or {}))
                )
                observe_confirm_migration_dual_write_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_migration_dual_write_v1", {}) or {}))
                )
                observe_confirm_input_contract_v2 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_input_contract_v2", {}) or {}))
                )
                observe_confirm_output_contract_v2 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_output_contract_v2", {}) or {}))
                )
                observe_confirm_scope_contract_v1 = dict(
                    (((getattr(current_context, "metadata", {}) or {}).get("observe_confirm_scope_contract_v1", {}) or {}))
                )
                prev_signal_row = app.latest_signal_by_symbol.get(symbol, {}) if isinstance(app.latest_signal_by_symbol, dict) else {}
                if not isinstance(prev_signal_row, dict):
                    prev_signal_row = {}
                stage_started_at = time.perf_counter()
                snapshot_generated_ts = time.time()
                runtime_signal_timeframe = "15M"
                runtime_signal_bar_ts = 0
                try:
                    signal_frame = df_all.get(str(runtime_signal_timeframe), None)
                    if signal_frame is not None and len(signal_frame) > 0:
                        last_index = signal_frame.index[-1]
                        if hasattr(last_index, "timestamp"):
                            runtime_signal_bar_ts = int(last_index.timestamp())
                except Exception:
                    runtime_signal_bar_ts = 0
                app.latest_signal_by_symbol[symbol] = {
                    "symbol": str(symbol),
                    "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "signal_timeframe": str(runtime_signal_timeframe),
                    "signal_bar_ts": int(runtime_signal_bar_ts),
                    "is_active": bool(is_active),
                    "inactive_reason": str(reason or ""),
                    "buy_score": int(buy_s),
                    "sell_score": int(sell_s),
                    "wait_score": int(wait_s),
                    "wait_reasons": wait_reasons[:5],
                    "wait_conflict": int(wait_conflict),
                    "wait_noise": int(wait_noise),
                    "entry_threshold": int(sym_policy.get("entry_threshold", policy_service.entry_threshold)),
                    "exit_threshold": int(sym_policy.get("exit_threshold", policy_service.exit_threshold)),
                    "policy_scope": str(sym_policy.get("policy_scope", "GLOBAL")),
                    "sample_confidence": float(sym_policy.get("sample_confidence", 0.0)),
                    "can_long": can_long,
                    "can_short": can_short,
                    "my_position_count": int(pos_count),
                    "max_positions": max_positions_for_symbol,
                    "market_mode": ("" if current_context is None else str(current_context.market_mode)),
                    "direction_policy": ("" if current_context is None else str(current_context.direction_policy)),
                    "box_state": ("" if current_context is None else str(current_context.box_state)),
                    "bb_state": ("" if current_context is None else str(current_context.bb_state)),
                    "liquidity_state": ("" if current_context is None else str(current_context.liquidity_state)),
                    "current_entry_context_v1": ({} if current_context is None else current_context.to_dict()),
                    "position_snapshot_v2": dict(position_snapshot_v2),
                    "position_vector_v2": dict(position_snapshot_v2.get("vector", {}) or {}),
                    "position_zones_v2": dict(position_snapshot_v2.get("zones", {}) or {}),
                    "position_interpretation_v2": dict(position_snapshot_v2.get("interpretation", {}) or {}),
                    "position_energy_v2": dict(position_snapshot_v2.get("energy", {}) or {}),
                    "response_raw_snapshot_v1": dict(response_raw_snapshot_v1),
                    "response_vector_v2": dict(response_vector_v2),
                    "state_raw_snapshot_v1": dict(state_raw_snapshot_v1),
                    "state_vector_v2": dict(state_vector_v2),
                    "evidence_vector_v1": dict(evidence_vector_v1),
                    "belief_state_v1": dict(belief_state_v1),
                    "barrier_state_v1": dict(barrier_state_v1),
                    "forecast_features_v1": dict(forecast_features_v1),
                    "transition_forecast_v1": dict(transition_forecast_v1),
                    "trade_management_forecast_v1": dict(trade_management_forecast_v1),
                    "forecast_gap_metrics_v1": dict(forecast_gap_metrics_v1),
                    "transition_side_separation": float(forecast_gap_metrics_v1.get("transition_side_separation", 0.0) or 0.0),
                    "transition_confirm_fake_gap": float(
                        forecast_gap_metrics_v1.get("transition_confirm_fake_gap", 0.0) or 0.0
                    ),
                    "transition_reversal_continuation_gap": float(
                        forecast_gap_metrics_v1.get("transition_reversal_continuation_gap", 0.0) or 0.0
                    ),
                    "management_continue_fail_gap": float(
                        forecast_gap_metrics_v1.get("management_continue_fail_gap", 0.0) or 0.0
                    ),
                    "management_recover_reentry_gap": float(
                        forecast_gap_metrics_v1.get("management_recover_reentry_gap", 0.0) or 0.0
                    ),
                    "observe_confirm_v1": dict(observe_confirm_v1),
                    "observe_confirm_v2": dict(observe_confirm_v2),
                    "observe_confirm_migration_dual_write_v1": dict(observe_confirm_migration_dual_write_v1),
                    "observe_confirm_input_contract_v2": dict(observe_confirm_input_contract_v2),
                    "observe_confirm_output_contract_v2": dict(observe_confirm_output_contract_v2),
                    "observe_confirm_scope_contract_v1": dict(observe_confirm_scope_contract_v1),
                    "semantic_foundation_contract_v1": dict(
                        (((getattr(current_context, "metadata", {}) or {}).get("semantic_foundation_contract_v1", {}) or {}))
                    ),
                    "forecast_calibration_contract_v1": dict(
                        (((getattr(current_context, "metadata", {}) or {}).get("forecast_calibration_contract_v1", {}) or {}))
                    ),
                    "outcome_labeler_scope_contract_v1": dict(
                        (((getattr(current_context, "metadata", {}) or {}).get("outcome_labeler_scope_contract_v1", {}) or {}))
                    ),
                    "prs_log_contract_v2": {
                        "canonical_position_field": "position_snapshot_v2",
                        "canonical_response_field": "response_vector_v2",
                        "canonical_state_field": "state_vector_v2",
                        "canonical_evidence_field": "evidence_vector_v1",
                        "canonical_belief_field": "belief_state_v1",
                        "canonical_barrier_field": "barrier_state_v1",
                        "canonical_forecast_features_field": "forecast_features_v1",
                        "canonical_transition_forecast_field": "transition_forecast_v1",
                        "canonical_trade_management_forecast_field": "trade_management_forecast_v1",
                        "canonical_forecast_gap_metrics_field": "forecast_gap_metrics_v1",
                        "canonical_observe_confirm_field": "observe_confirm_v2",
                        "compatibility_observe_confirm_field": "observe_confirm_v1",
                        "observe_confirm_input_contract_field": "observe_confirm_input_contract_v2",
                        "observe_confirm_migration_contract_field": "observe_confirm_migration_dual_write_v1",
                        "observe_confirm_output_contract_field": "observe_confirm_output_contract_v2",
                        "observe_confirm_scope_contract_field": "observe_confirm_scope_contract_v1",
                        "semantic_foundation_contract_field": "semantic_foundation_contract_v1",
                        "forecast_calibration_contract_field": "forecast_calibration_contract_v1",
                        "outcome_labeler_scope_contract_field": "outcome_labeler_scope_contract_v1",
                    },
                    "cooldown_sec_remaining": max(
                        0,
                        int(float(Config.ENTRY_COOLDOWN) - (time.time() - float(app.last_entry_time.get(symbol, 0.0)))),
                    ),
                    "next_action_hint": (
                        "BUY"
                        if can_long and not can_short
                        else ("SELL" if can_short and not can_long else ("BOTH" if can_long and can_short else "HOLD"))
                    ),
                    "entry_decision_context_v1": prev_signal_row.get("entry_decision_context_v1", {}),
                    "entry_decision_result_v1": prev_signal_row.get("entry_decision_result_v1", {}),
                    "entry_prediction_v1": prev_signal_row.get("entry_prediction_v1", {}),
                    "entry_wait_state": prev_signal_row.get("entry_wait_state", ""),
                    "entry_wait_reason": prev_signal_row.get("entry_wait_reason", ""),
                    "entry_wait_selected": prev_signal_row.get("entry_wait_selected", 0),
                    "entry_wait_decision": prev_signal_row.get("entry_wait_decision", ""),
                    "semantic_shadow_available": prev_signal_row.get("semantic_shadow_available", ""),
                    "semantic_shadow_reason": prev_signal_row.get("semantic_shadow_reason", ""),
                    "semantic_shadow_activation_state": prev_signal_row.get("semantic_shadow_activation_state", ""),
                    "semantic_shadow_activation_reason": prev_signal_row.get("semantic_shadow_activation_reason", ""),
                    "semantic_live_rollout_mode": prev_signal_row.get("semantic_live_rollout_mode", ""),
                    "semantic_live_alert": prev_signal_row.get("semantic_live_alert", 0),
                    "semantic_live_fallback_reason": prev_signal_row.get("semantic_live_fallback_reason", ""),
                    "semantic_live_symbol_allowed": prev_signal_row.get("semantic_live_symbol_allowed", ""),
                    "semantic_live_entry_stage_allowed": prev_signal_row.get("semantic_live_entry_stage_allowed", ""),
                    "semantic_live_threshold_before": prev_signal_row.get("semantic_live_threshold_before", ""),
                    "semantic_live_threshold_after": prev_signal_row.get("semantic_live_threshold_after", ""),
                    "semantic_live_threshold_adjustment": prev_signal_row.get("semantic_live_threshold_adjustment", ""),
                    "semantic_live_threshold_applied": prev_signal_row.get("semantic_live_threshold_applied", ""),
                    "semantic_live_threshold_state": prev_signal_row.get("semantic_live_threshold_state", ""),
                    "semantic_live_threshold_reason": prev_signal_row.get("semantic_live_threshold_reason", ""),
                    "semantic_live_partial_weight": prev_signal_row.get("semantic_live_partial_weight", ""),
                    "semantic_live_partial_live_applied": prev_signal_row.get("semantic_live_partial_live_applied", ""),
                    "semantic_live_reason": prev_signal_row.get("semantic_live_reason", ""),
                    **_snapshot_exit_fields(prev_signal_row, pos_count=pos_count),
                    "runtime_snapshot_generated_ts": float(snapshot_generated_ts),
                }
                current_snapshot_row = dict(app.latest_signal_by_symbol.get(symbol, {}) or {})
                observe_summary = (
                    dict(current_snapshot_row.get("observe_confirm_v2", {}) or {})
                    if isinstance(current_snapshot_row.get("observe_confirm_v2"), dict)
                    else {}
                )
                observe_metadata = (
                    dict(observe_summary.get("metadata", {}) or {})
                    if isinstance(observe_summary.get("metadata"), dict)
                    else {}
                )
                for trace_key in ("probe_candidate_v1", "edge_pair_law_v1"):
                    trace_payload = observe_metadata.get(trace_key)
                    if isinstance(trace_payload, dict) and trace_payload and not isinstance(current_snapshot_row.get(trace_key), dict):
                        current_snapshot_row[trace_key] = dict(trace_payload)
                current_snapshot_row["symbol"] = str(symbol)
                current_snapshot_row["time"] = float(snapshot_generated_ts)
                current_snapshot_row["timestamp"] = datetime.fromtimestamp(
                    float(snapshot_generated_ts)
                ).isoformat()
                current_snapshot_row["state25_candidate_runtime_v1"] = dict(
                    getattr(app, "state25_candidate_runtime_state", {}) or {}
                )
                current_snapshot_row["observe_action"] = str(observe_summary.get("action", "") or "")
                current_snapshot_row["observe_side"] = str(observe_summary.get("side", "") or "")
                current_snapshot_row["observe_reason"] = str(observe_summary.get("reason", "") or "")
                if not current_snapshot_row.get("blocked_by"):
                    current_snapshot_row["blocked_by"] = str(
                        observe_metadata.get("blocked_guard", "")
                        or observe_metadata.get("blocked_reason", "")
                        or ""
                    )
                current_snapshot_row.update(build_probe_quick_trace_fields(current_snapshot_row))
                current_snapshot_row["runtime_snapshot_key"] = resolve_runtime_signal_row_key(current_snapshot_row)
                current_snapshot_row.update(
                    summarize_trace_quality(
                        current_snapshot_row,
                        decision_ts=float(snapshot_generated_ts),
                        runtime_snapshot_ts=float(snapshot_generated_ts),
                    )
                )
                current_snapshot_row["forecast_state25_runtime_bridge_v1"] = (
                    build_forecast_state25_runtime_bridge_v1(current_snapshot_row)
                )
                current_snapshot_row["belief_state25_runtime_bridge_v1"] = (
                    build_belief_state25_runtime_bridge_v1(current_snapshot_row)
                )
                current_snapshot_row["barrier_state25_runtime_bridge_v1"] = (
                    build_barrier_state25_runtime_bridge_v1(current_snapshot_row)
                )
                current_snapshot_row["snapshot_payload_bytes"] = int(json_payload_size_bytes(current_snapshot_row))
                app.latest_signal_by_symbol[symbol] = current_snapshot_row
                _record_symbol_stage_timing(stage_timings_ms, "snapshot_prepare", stage_started_at)

                if positions:
                    stage_started_at = time.perf_counter()
                    sub_stage_started_at = time.perf_counter()
                    entry_indicators = app._entry_indicator_snapshot(symbol, scorer, df_all)
                    _record_symbol_stage_timing(
                        stage_timings_ms,
                        "position_snapshot_indicator",
                        sub_stage_started_at,
                    )
                    snapshots = []
                    context_lookup_ms = 0.0
                    exit_detail_ms = 0.0
                    for p in positions:
                        direction = "BUY" if int(p.type) == int(ORDER_TYPE_BUY) else "SELL"
                        if direction == "BUY":
                            base_score = int(buy_s)
                            contra_score = int(sell_s)
                            base_reasons = result["buy"]["reasons"]
                        else:
                            base_score = int(sell_s)
                            contra_score = int(buy_s)
                            base_reasons = result["sell"]["reasons"]
                        scored_reasons = app._build_scored_reasons(base_reasons, target_total=base_score, ai_adj=0)
                        source = "AUTO" if int(getattr(p, "magic", 0) or 0) == int(Config.MAGIC_NUMBER) else "MANUAL"
                        pos_ts = int(getattr(p, "time", 0) or 0)
                        context_started_at = time.perf_counter()
                        existing_trade_ctx = trade_logger.get_trade_context(int(p.ticket)) or {}
                        context_lookup_ms += (time.perf_counter() - context_started_at) * 1000.0
                        entry_result = ((app.latest_signal_by_symbol.get(symbol, {}) or {}).get("entry_decision_result_v1", {}) or {})
                        selected_setup = (entry_result.get("selected_setup", {}) or {}) if isinstance(entry_result, dict) else {}
                        snapshot_setup_id = str(existing_trade_ctx.get("entry_setup_id", "") or "").strip().lower()
                        snapshot_management_profile_id = str(existing_trade_ctx.get("management_profile_id", "") or "").strip().lower()
                        snapshot_invalidation_id = str(existing_trade_ctx.get("invalidation_id", "") or "").strip().lower()
                        unresolved_setup = snapshot_setup_id in ("", "snapshot_restored_auto")
                        if unresolved_setup and source == "AUTO":
                            candidate_setup = str(selected_setup.get("setup_id", "") or "").strip().lower()
                            candidate_side = str(selected_setup.get("side", "") or "").strip().upper()
                            if candidate_setup and candidate_side == direction:
                                snapshot_setup_id = candidate_setup
                            else:
                                snapshot_setup_id = _resolve_recent_setup_from_decisions(
                                    decision_csv=decision_csv,
                                    symbol=p.symbol,
                                    direction=direction,
                                    open_ts=pos_ts,
                                ) or "snapshot_restored_auto"
                        snapshot_exit_profile = str(existing_trade_ctx.get("exit_profile", "") or "").strip().lower()
                        if (not snapshot_exit_profile) or (
                            snapshot_setup_id
                            and snapshot_setup_id != "snapshot_restored_auto"
                            and snapshot_exit_profile == "neutral"
                        ):
                            snapshot_exit_profile = resolve_exit_profile(
                                management_profile_id=snapshot_management_profile_id,
                                invalidation_id=snapshot_invalidation_id,
                                entry_setup_id=snapshot_setup_id,
                                fallback_profile="neutral",
                            )
                        snapshots.append(
                            {
                                "ticket": int(p.ticket),
                                "symbol": p.symbol,
                                "direction": direction,
                                "lot": float(p.volume),
                                "open_price": float(p.price_open),
                                "open_ts": pos_ts,
                                "entry_score": base_score,
                                "contra_score_at_entry": contra_score,
                                "entry_reason": ", ".join(scored_reasons),
                                "entry_setup_id": snapshot_setup_id,
                                "management_profile_id": snapshot_management_profile_id,
                                "invalidation_id": snapshot_invalidation_id,
                                "exit_profile": snapshot_exit_profile,
                                "manual_entry_tag": str(
                                    getattr(p, "comment", "") or existing_trade_ctx.get("manual_entry_tag", "") or ""
                                ).strip(),
                                "entry_wait_state": str(((app.latest_signal_by_symbol.get(symbol, {}) or {}).get("entry_wait_state", "") or "")).strip().upper(),
                                "indicators": entry_indicators,
                                "source": source,
                                "regime": result.get("regime", {}),
                            }
                        )
                        opposite_score = int(sell_s if direction == "BUY" else buy_s)
                        opposite_reasons = result["sell"]["reasons"] if direction == "BUY" else result["buy"]["reasons"]
                        exit_detail_started_at = time.perf_counter()
                        app._build_exit_detail(
                            opposite_reasons=opposite_reasons,
                            exit_signal_score=opposite_score,
                            trade_logger=trade_logger,
                            ticket=int(p.ticket),
                        )
                        exit_detail_ms += (time.perf_counter() - exit_detail_started_at) * 1000.0
                    stage_timings_ms["position_snapshot_context_lookup"] = round(float(context_lookup_ms), 3)
                    stage_timings_ms["position_snapshot_exit_detail"] = round(float(exit_detail_ms), 3)
                    sub_stage_started_at = time.perf_counter()
                    trade_logger.upsert_open_snapshots(snapshots)
                    _record_symbol_stage_timing(
                        stage_timings_ms,
                        "position_snapshot_upsert",
                        sub_stage_started_at,
                    )
                    _record_symbol_stage_timing(stage_timings_ms, "position_snapshot_sync", stage_started_at)
                else:
                    stage_timings_ms.setdefault("position_snapshot_sync", 0.0)

                if symbol == list(symbols.values())[0]:
                    app.print_dashboard(
                        symbol,
                        buy_s,
                        sell_s,
                        sniper["rsi"],
                        pos_count,
                        is_active,
                        reason,
                        int(sym_policy.get("entry_threshold", policy_service.entry_threshold)),
                    )

                if not is_active:
                    app._write_loop_debug(loop_count=loop_count, stage="symbol_inactive", symbol=symbol, detail=str(reason or ""))
                    continue

                stage_started_at = time.perf_counter()
                entry_runtime_row = app.build_entry_runtime_signal_row(
                    symbol,
                    dict((app.latest_signal_by_symbol.get(symbol, {}) or {})),
                )
                entry_runtime_row["symbol"] = str(symbol)
                app.latest_signal_by_symbol[symbol] = dict(entry_runtime_row)
                _record_symbol_stage_timing(stage_timings_ms, "entry_runtime_enrich", stage_started_at)
                try:
                    painter.sync_flow_history_from_runtime_row(symbol, entry_runtime_row)
                except Exception:
                    logger.exception("Failed to sync entry runtime flow history: %s", symbol)
                _write_runtime_status_progress(
                    app,
                    loop_count=loop_count,
                    symbols=symbols,
                    policy_service=policy_service,
                    detail=f"entry_runtime_ready:{symbol}",
                )

                app._write_loop_debug(loop_count=loop_count, stage="entry_eval", symbol=symbol)
                stage_started_at = time.perf_counter()
                entry_service.try_open_entry(
                    symbol=symbol,
                    tick=tick,
                    df_all=df_all,
                    result=result,
                    my_positions=my_positions,
                    pos_count=pos_count,
                    scorer=scorer,
                    buy_s=buy_s,
                    sell_s=sell_s,
                    entry_threshold=int(sym_policy.get("entry_threshold", policy_service.entry_threshold)),
                )
                _record_symbol_stage_timing(stage_timings_ms, "entry_eval", stage_started_at)

                app._write_loop_debug(
                    loop_count=loop_count,
                    stage="exit_eval",
                    symbol=symbol,
                    detail=f"pos_count={int(pos_count)}",
                )
                stage_started_at = time.perf_counter()
                reverse_action, reverse_score, reverse_reasons = exit_service.manage_positions(
                    symbol=symbol,
                    tick=tick,
                    my_positions=my_positions,
                    result=result,
                    df_all=df_all,
                    sniper=sniper,
                    loss_limit=loss_limit,
                    buy_s=buy_s,
                    sell_s=sell_s,
                    exit_threshold=int(sym_policy.get("exit_threshold", policy_service.exit_threshold)),
                    adverse_loss_usd=float(sym_policy.get("adverse_loss_usd", policy_service.adverse_loss_usd)),
                    reverse_signal_threshold=int(
                        sym_policy.get("reverse_signal_threshold", policy_service.reverse_signal_threshold)
                    ),
                    exit_policy=sym_policy.get("exit_policy", policy_service.exit_policy),
                )
                app._write_loop_debug(
                    loop_count=loop_count,
                    stage="exit_eval_done",
                    symbol=symbol,
                    detail=(
                        f"pos_count={int(pos_count)} reverse_action={str(reverse_action or '')} "
                        f"reverse_score={float(reverse_score or 0.0):.2f}"
                    ),
                )
                _record_symbol_stage_timing(stage_timings_ms, "exit_eval", stage_started_at)

                if reverse_action:
                    live_positions_after_exit = app.broker.positions_get(symbol=symbol) or []
                    managed_positions_after_exit = [
                        p
                        for p in live_positions_after_exit
                        if int(getattr(p, "magic", 0) or 0) == int(Config.MAGIC_NUMBER)
                    ]
                    reverse_pending = bool(managed_positions_after_exit)
                    reverse_price = (
                        float(tick.ask if str(reverse_action).upper() == "BUY" else tick.bid)
                        if tick is not None
                        else 0.0
                    )
                    reverse_signature = app.build_reverse_message_signature(
                        symbol,
                        reverse_action,
                        reverse_score,
                        reverse_reasons,
                        pending=reverse_pending,
                    )
                    if app.should_notify_reverse_message(symbol, reverse_signature):
                        reverse_message = app.format_reverse_message(
                            symbol,
                            reverse_action,
                            reverse_score,
                            reverse_price,
                            reverse_reasons,
                            len(managed_positions_after_exit),
                            int(Config.get_max_positions(symbol)),
                            pending=reverse_pending,
                            row=dict((app.latest_signal_by_symbol or {}).get(symbol, {}) or {}),
                        )
                        app.notify(reverse_message)

                stage_started_at = time.perf_counter()
                app._try_reverse_entry(
                    reverse_action=reverse_action,
                    reverse_score=reverse_score,
                    reverse_reasons=reverse_reasons,
                    symbol=symbol,
                    buy_s=buy_s,
                    sell_s=sell_s,
                    tick=tick,
                    scorer=scorer,
                    df_all=df_all,
                    trade_logger=trade_logger,
                )
                _record_symbol_stage_timing(stage_timings_ms, "reverse_entry", stage_started_at)

                stage_started_at = time.perf_counter()
                painter.clear()
                painter.add_session_boxes(df_all["1H"])
                painter.add_mtf_trend_lines(df_all)
                painter.add_bollinger_lines(df_all["1H"], period=20, std_mult=2.0, lookback=60)
                painter.add_mtf_ma_lines(df_all)
                latest_row = {}
                painter_row = {}
                try:
                    if isinstance(app.latest_signal_by_symbol, dict):
                        latest_row = app.latest_signal_by_symbol.get(symbol, {})
                        if not isinstance(latest_row, dict):
                            latest_row = {}
                except Exception:
                    latest_row = {}
                try:
                    painter_row = app.build_chart_painter_runtime_row(symbol, latest_row)
                    if not isinstance(painter_row, dict):
                        painter_row = dict(latest_row)
                except Exception:
                    painter_row = dict(latest_row)
                painter.add_decision_flow_overlay(symbol, painter_row, df_all, tick)
                painter_status = painter.save(symbol) or {}
                try:
                    if isinstance(app.latest_signal_by_symbol, dict):
                        row = dict(painter_row or {})
                        if not row:
                            row = app.latest_signal_by_symbol.get(symbol, {})
                        if not isinstance(row, dict):
                            row = {}
                        row["chart_painter"] = painter_status
                        row["chart_painter_ok"] = bool(painter_status.get("ok", False))
                        row["chart_painter_fail_count"] = int(painter_status.get("fail_count", 0) or 0)
                        app.latest_signal_by_symbol[symbol] = row
                except Exception:
                    pass
                _record_symbol_stage_timing(stage_timings_ms, "painter", stage_started_at)
                elapsed = time.perf_counter() - started_at
                snapshot_for_profile = dict(app.latest_signal_by_symbol.get(symbol, {}) or {})
                profile = _build_symbol_loop_profile(
                    loop_count=loop_count,
                    symbol=symbol,
                    elapsed_sec=elapsed,
                    stage_timings_ms=stage_timings_ms,
                    snapshot_row=snapshot_for_profile,
                )
                _write_symbol_loop_profile(app, profile)
                slow_warn_sec = float(getattr(Config, "SYMBOL_LOOP_SLOW_WARN_SEC", 3.0) or 3.0)
                if elapsed >= slow_warn_sec:
                    logger.warning(
                        "slow symbol loop: symbol=%s elapsed=%.2fs dominant_stage=%s(%.1fms)",
                        symbol,
                        elapsed,
                        profile.get("dominant_stage", ""),
                        float(profile.get("dominant_stage_ms", 0.0) or 0.0),
                    )
                app._write_loop_debug(loop_count=loop_count, stage="symbol_done", symbol=symbol, detail=f"elapsed={elapsed:.2f}")
                try:
                    synced_flow_row = dict((app.latest_signal_by_symbol.get(symbol, {}) or {}))
                    if synced_flow_row:
                        painter.clear()
                        painter.add_decision_flow_overlay(symbol, synced_flow_row, df_all, tick)
                except Exception:
                    logger.exception("Failed to sync chart flow history from enriched runtime row: %s", symbol)
                _write_runtime_status_progress(
                    app,
                    loop_count=loop_count,
                    symbols=symbols,
                    policy_service=policy_service,
                    detail=f"symbol_done:{symbol}",
                )

            app._write_loop_debug(loop_count=loop_count, stage="check_closed_start")
            exit_msgs = trade_logger.check_closed_trades()
            app._write_loop_debug(loop_count=loop_count, stage="check_closed_done", detail=f"count={len(exit_msgs)}")
            _sync_flow_history_from_runtime_rows(app, painter, symbols)
            _write_runtime_status_progress(
                app,
                loop_count=loop_count,
                symbols=symbols,
                policy_service=policy_service,
                detail=f"check_closed_done:{len(exit_msgs)}",
            )
            for msg in exit_msgs:
                app.notify(msg)
                print(f"\n{msg}")

            try:
                telegram_ops.tick(trade_logger)
            except Exception:
                logger.exception("Telegram ops tick failed")

            recycle_request = _maybe_handle_runtime_recycle(app, loop_count=loop_count)
            if str(recycle_request.get("action", "") or "") != "none":
                app._write_runtime_status(
                    loop_count,
                    symbols,
                    policy_service.entry_threshold,
                    policy_service.exit_threshold,
                    adverse_loss_usd=policy_service.adverse_loss_usd,
                    reverse_signal_threshold=policy_service.reverse_signal_threshold,
                    policy_snapshot=policy_service.get_runtime_snapshot(),
                )
            if str(recycle_request.get("action", "") or "") == "reexec":
                break

            app._write_loop_debug(loop_count=loop_count, stage="loop_sleep")
            time.sleep(1)

    except KeyboardInterrupt:
        app._obs_event("trading_loop_stopped", payload={"reason": "keyboard_interrupt"})
        print("\n\nSystem terminated by user.")
    except Exception as exc:
        logger.exception("Unhandled error in main loop: %s", exc)
        app._obs_inc("trading_loop_unhandled_error_total", 1)
        app._obs_event("trading_loop_unhandled_error", level="error", payload={"error": str(exc)})
    finally:
        app._obs_event("trading_loop_shutdown")
        app.notify_shutdown()
        disconnect_mt5()
    if str((recycle_request or {}).get("action", "") or "") == "reexec":
        _perform_runtime_reexec()
