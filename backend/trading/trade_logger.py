"""
Trade history CSV logger.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Condition, RLock
from typing import Dict, Optional, Tuple

import pandas as pd

from adapters.mt5_broker_adapter import MT5BrokerAdapter
from backend.core.config import Config
from backend.core.trade_constants import DEAL_ENTRY_OUT, DEAL_ENTRY_OUT_BY, ORDER_TYPE_BUY
from backend.services.trade_csv_schema import (
    INDICATOR_COLUMNS,
    TRADE_COLUMNS,
    add_signed_exit_score,
    normalize_trade_df,
    normalize_manual_reason_tag,
    now_kst_dt,
)
from backend.services.trade_sqlite_store import TradeSqliteStore
from backend.trading.trade_logger_close_ops import (
    force_close_unknown as helper_force_close_unknown,
    update_closed_trade as helper_update_closed_trade,
)
from backend.trading.trade_logger_closed_batch import (
    append_closed_rows as helper_append_closed_rows,
    append_to_closed_file as helper_append_to_closed_file,
    run_closed_batch_leader_loop as helper_run_closed_batch_leader_loop,
)
from backend.trading.trade_logger_helpers import (
    atomic_write_df as helper_atomic_write_df,
    estimate_reason_points as helper_estimate_reason_points,
    lock_file_handle as helper_lock_file_handle,
    normalize_entry_stage as helper_normalize_entry_stage,
    normalize_exit_reason as helper_normalize_exit_reason,
    now_kst_text as helper_now_kst_text,
    text_to_kst_epoch as helper_text_to_kst_epoch,
    ts_to_kst_dt as helper_ts_to_kst_dt,
    unlock_file_handle as helper_unlock_file_handle,
)
from backend.trading.trade_logger_lifecycle import (
    check_closed_trades as helper_check_closed_trades,
    reconcile_open_trades as helper_reconcile_open_trades,
)
from backend.trading.trade_logger_open_snapshots import (
    upsert_open_snapshots as helper_upsert_open_snapshots,
)
from backend.trading.trade_logger_recommendations import (
    recommend_adverse_policy as helper_recommend_adverse_policy,
    recommend_exit_policy as helper_recommend_exit_policy,
    recommend_thresholds as helper_recommend_thresholds,
)
from backend.trading.trade_logger_shock_ops import (
    register_shock_event as helper_register_shock_event,
    resolve_shock_event_on_close as helper_resolve_shock_event_on_close,
    update_shock_event_progress as helper_update_shock_event_progress,
)
from ports.broker_port import BrokerPort

logger = logging.getLogger(__name__)


class TradeLogger:
    @staticmethod
    def _normalize_entry_stage(value: str) -> str:
        return helper_normalize_entry_stage(value)

    @staticmethod
    def _normalize_exit_reason(reason: str) -> str:
        return helper_normalize_exit_reason(reason)

    @staticmethod
    def _estimate_reason_points(reason: str) -> int:
        return helper_estimate_reason_points(reason)

    @staticmethod
    def _now_kst_dt() -> datetime:
        return now_kst_dt()

    @staticmethod
    def _now_kst_text() -> str:
        return helper_now_kst_text()

    @staticmethod
    def _ts_to_kst_dt(ts: int) -> datetime:
        return helper_ts_to_kst_dt(ts)

    @staticmethod
    def _ts_to_kst_text(ts: int) -> str:
        return helper_ts_to_kst_dt(ts).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _text_to_kst_epoch(value: str) -> int:
        return helper_text_to_kst_epoch(value)

    def __init__(self, filename="trade_history.csv", broker: BrokerPort | None = None):
        self.filepath = str(filename)
        self.closed_filepath = str(Path(self.filepath).with_name("trade_closed_history.csv"))
        self.shock_event_filepath = str(Path(self.filepath).with_name("trade_shock_events.csv"))
        configured_profile_path = str(getattr(Config, "STARTUP_RECONCILE_PROFILE_PATH", "") or "").strip()
        if configured_profile_path:
            profile_path = Path(configured_profile_path)
            if not profile_path.is_absolute():
                profile_path = Path(__file__).resolve().parents[2] / profile_path
            self.startup_reconcile_profile_path = str(profile_path)
        else:
            self.startup_reconcile_profile_path = str(Path(self.filepath).with_name("startup_reconcile_latest.json"))
        self.startup_reconcile_profile = {}
        self.broker: BrokerPort = broker or MT5BrokerAdapter()
        self.active_tickets = set()
        self.pending_exit: Dict[int, dict] = {}
        self.live_exit_context: Dict[int, dict] = {}
        self._pending_open_policy_context: Dict[int, dict] = {}
        self._committed_open_policy_context: Dict[int, dict] = {}
        self._shock_event_runtime_cache: Dict[int, dict] = {}
        self.closed_pending_since: Dict[int, datetime] = {}
        self.closed_pending_checks: Dict[int, int] = {}
        self.last_history_check = datetime.now()
        self._open_snapshot_signature_cache: Dict[int, str] = {}

        self._open_lock = RLock()
        self._closed_lock = RLock()
        self._shock_lock = RLock()
        self._closed_batch_cv = Condition(RLock())
        self._closed_batch_pending = []
        self._closed_batch_leader_active = False
        self._closed_batch_window_sec = float(getattr(Config, "CLOSED_BATCH_WINDOW_SEC", 0.25))

        self._store = TradeSqliteStore(
            db_path=Path(self.filepath).with_name("trades.db"),
            trade_csv=Path(self.filepath),
            closed_trade_csv=Path(self.closed_filepath),
        )
        self._store_health = {
            "last_success_at": 0.0,
            "last_failure_at": 0.0,
            "last_error": "",
            "last_op": "",
        }
        self._create_file()
        self._ensure_closed_file()
        self._ensure_shock_event_file()
        self._sync_store_from_csv(force=True)
        self._load_active_tickets()

    @staticmethod
    def _lock_file_handle(fp, timeout_sec: float = 8.0) -> None:
        helper_lock_file_handle(fp, timeout_sec=timeout_sec)

    @staticmethod
    def _unlock_file_handle(fp) -> None:
        helper_unlock_file_handle(fp)

    @contextmanager
    def _file_guard(self, target_path: str, lock: RLock):
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        with lock:
            with open(target_path, "a+b") as fp:
                self._lock_file_handle(fp)
                try:
                    yield
                finally:
                    self._unlock_file_handle(fp)

    def _atomic_write_df(self, target_path: str, df: pd.DataFrame):
        helper_atomic_write_df(target_path=target_path, df=df)

    def _write_open_df(self, df: pd.DataFrame):
        lock_path = f"{self.filepath}.lock"
        with self._file_guard(lock_path, self._open_lock):
            self._atomic_write_df(self.filepath, self._normalize_dataframe(df))

    def _write_closed_df(self, df: pd.DataFrame):
        lock_path = f"{self.closed_filepath}.lock"
        with self._file_guard(lock_path, self._closed_lock):
            self._atomic_write_df(self.closed_filepath, self._normalize_dataframe(df))

    def _read_open_df_safe(self) -> pd.DataFrame:
        try:
            if not Path(self.filepath).exists():
                return pd.DataFrame(columns=self._columns())
            return self._normalize_dataframe(pd.read_csv(self.filepath, encoding="utf-8-sig"))
        except Exception:
            return pd.DataFrame(columns=self._columns())

    def _read_closed_df_safe(self) -> pd.DataFrame:
        try:
            if not Path(self.closed_filepath).exists():
                return pd.DataFrame(columns=self._columns())
            return self._normalize_dataframe(pd.read_csv(self.closed_filepath, encoding="utf-8-sig"))
        except Exception:
            return pd.DataFrame(columns=self._columns())

    def _read_shock_df_safe(self) -> pd.DataFrame:
        try:
            if not Path(self.shock_event_filepath).exists():
                return pd.DataFrame(columns=self._shock_columns())
            return self._normalize_shock_df(pd.read_csv(self.shock_event_filepath, encoding="utf-8-sig"))
        except Exception:
            return pd.DataFrame(columns=self._shock_columns())

    @staticmethod
    def _indicator_columns():
        return list(INDICATOR_COLUMNS)

    @staticmethod
    def _columns():
        return list(TRADE_COLUMNS)

    @staticmethod
    def _shock_columns():
        return [
            "ticket",
            "symbol",
            "direction",
            "lot",
            "event_time",
            "event_ts",
            "event_bucket",
            "event_price",
            "event_profit",
            "shock_score",
            "shock_level",
            "shock_reason",
            "shock_action",
            "pre_shock_stage",
            "post_shock_stage",
            "ticks_elapsed",
            "shock_hold_delta_10",
            "shock_hold_delta_30",
            "filled_10",
            "filled_30",
            "resolved",
            "close_time",
            "close_ts",
        ]

    def _create_file(self):
        p = Path(self.filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            self._atomic_write_df(str(p), pd.DataFrame(columns=self._columns()))

    def _ensure_closed_file(self):
        p = Path(self.closed_filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            self._atomic_write_df(str(p), pd.DataFrame(columns=self._columns()))

    def _ensure_shock_event_file(self):
        p = Path(self.shock_event_filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            self._atomic_write_df(str(p), pd.DataFrame(columns=self._shock_columns()))

    def _ensure_trade_schema_migrated(self):
        self._create_file()
        self._ensure_closed_file()

    def _sync_store_from_csv(self, force: bool = False):
        try:
            changed = bool(self._store.sync_from_csv(force=bool(force)))
            if changed:
                self._mark_store_success("sync_from_csv")
            return changed
        except Exception as exc:
            self._mark_store_failure("sync_from_csv", exc)
            return False

    def _sync_open_rows_to_store(self, open_rows_df: pd.DataFrame):
        self._upsert_open_rows_to_store(open_rows_df)

    def _upsert_open_rows_to_store(self, open_rows_df: pd.DataFrame):
        try:
            self._store.upsert_open_rows(open_rows_df if open_rows_df is not None else pd.DataFrame(columns=self._columns()))
            self._mark_store_success("upsert_open_rows")
        except Exception as exc:
            self._mark_store_failure("upsert_open_rows", exc)

    def _upsert_closed_rows_to_store(self, closed_rows_df: pd.DataFrame):
        try:
            self._store.upsert_closed_rows(closed_rows_df if closed_rows_df is not None else pd.DataFrame(columns=self._columns()))
            self._mark_store_success("upsert_closed_rows")
        except Exception as exc:
            self._mark_store_failure("upsert_closed_rows", exc)

    def _mark_store_success(self, op: str):
        self._store_health["last_success_at"] = self._now_kst_dt().timestamp()
        self._store_health["last_op"] = str(op or "")
        self._store_health["last_error"] = ""

    def _mark_store_failure(self, op: str, exc: Exception):
        self._store_health["last_failure_at"] = self._now_kst_dt().timestamp()
        self._store_health["last_op"] = str(op or "")
        self._store_health["last_error"] = str(exc)

    def get_store_health_snapshot(self) -> Dict[str, object]:
        return dict(self._store_health)

    def _append_to_closed_file(self, rows_df: pd.DataFrame):
        return helper_append_to_closed_file(self, rows_df)

    def append_closed_rows(self, rows: list[dict]) -> int:
        return helper_append_closed_rows(self, rows=rows)

    def _run_closed_batch_leader_loop(self):
        return helper_run_closed_batch_leader_loop(self)

    def _read_closed_df(self) -> pd.DataFrame:
        return self._read_closed_df_safe()

    def read_closed_df(self) -> pd.DataFrame:
        return self._read_closed_df_safe()

    def query_latest_open(self, symbol: str = "", limit: int = 1) -> pd.DataFrame:
        return self._store.query_latest_open(symbol=symbol, limit=limit)

    def query_latest_closed(self, symbol: str = "", limit: int = 1) -> pd.DataFrame:
        return self._store.query_latest_closed(symbol=symbol, limit=limit)

    def get_change_token(self) -> str:
        return self._store.get_change_token()

    def _migrate_legacy_closed_rows(self):
        return

    def _normalize_dataframe(self, df):
        return normalize_trade_df(df if df is not None else pd.DataFrame(columns=self._columns()))

    def _normalize_shock_df(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = self._shock_columns()
        if df is None:
            return pd.DataFrame(columns=cols)
        out = df.copy()
        for c in cols:
            if c not in out.columns:
                out[c] = 0 if c in {"ticket", "event_ts", "event_bucket", "ticks_elapsed", "filled_10", "filled_30", "resolved", "close_ts"} else ""
        for c in ["ticket", "event_ts", "event_bucket", "ticks_elapsed", "filled_10", "filled_30", "resolved", "close_ts"]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
        for c in ["lot", "event_price", "event_profit", "shock_score", "shock_hold_delta_10", "shock_hold_delta_30"]:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        for c in ["symbol", "direction", "event_time", "shock_level", "shock_reason", "shock_action", "pre_shock_stage", "post_shock_stage", "close_time"]:
            out[c] = out[c].fillna("").astype(str)
        return out[cols]

    def register_shock_event(self, **kwargs):
        return helper_register_shock_event(self, logger=logger, **kwargs)

    @staticmethod
    def _shock_mark_col(direction: str) -> str:
        return "bid" if str(direction or "").upper() == "BUY" else "ask"

    @staticmethod
    def _calc_profit_delta_mt5(direction: str, symbol: str, lot: float, p0: float, p1: float) -> float | None:
        try:
            sign = 1.0 if str(direction or "").upper() == "BUY" else -1.0
            pip_value_hint = float(getattr(Config, "SHOCK_DELTA_PIP_VALUE_HINT", 10.0))
            return float((float(p1) - float(p0)) * sign * float(lot or 0.0) * pip_value_hint)
        except Exception:
            return None

    def refresh_shock_event_from_mt5_ticks(self, ticket: int, symbol: str, direction: str) -> dict:
        if not bool(getattr(Config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
            return {}
        t = int(ticket or 0)
        cached = dict((self._shock_event_runtime_cache.get(t, {}) or {}))
        if not cached:
            df = self._read_shock_df_safe()
            cand = df[(df["ticket"] == t) & (df["resolved"] == 0)]
            if cand.empty:
                return {}
            cached = dict(cand.sort_values("event_ts", ascending=False).iloc[0].to_dict() or {})
            self._shock_event_runtime_cache[t] = dict(cached)
        if not cached:
            return {}
        tick = self.broker.symbol_info_tick(symbol)
        if not tick:
            return {}
        mark_col = self._shock_mark_col(direction)
        now_price = float(getattr(tick, mark_col, 0.0) or 0.0)
        event_price = float(pd.to_numeric(cached.get("event_price", 0.0), errors="coerce") or 0.0)
        lot = float(pd.to_numeric(cached.get("lot", 0.0), errors="coerce") or 0.0)
        now_ts = int(self._now_kst_dt().timestamp())
        event_ts = int(pd.to_numeric(cached.get("event_ts", 0), errors="coerce") or 0)
        ticks_elapsed = max(0, int((now_ts - event_ts) // 3))
        delta = self._calc_profit_delta_mt5(direction=direction, symbol=symbol, lot=lot, p0=event_price, p1=now_price)
        delta_10 = float(delta) if (delta is not None and ticks_elapsed >= 10) else None
        delta_30 = float(delta) if (delta is not None and ticks_elapsed >= 30) else None
        meta = self.update_shock_event_progress(
            ticket=t,
            ticks_elapsed=ticks_elapsed,
            delta_10=delta_10,
            delta_30=delta_30,
        )
        out = {"ticks_elapsed": int(ticks_elapsed)}
        if isinstance(meta, dict):
            out.update(meta)
        return out

    def update_shock_event_progress(self, **kwargs) -> dict:
        return helper_update_shock_event_progress(self, logger=logger, **kwargs)

    def resolve_shock_event_on_close(self, ticket: int, close_time: str, close_ts: int) -> dict:
        return helper_resolve_shock_event_on_close(
            self,
            ticket=int(ticket),
            close_time=str(close_time or ""),
            close_ts=int(close_ts or 0),
            logger=logger,
        )

    def _load_active_tickets(self):
        try:
            df = self._read_open_df_safe()
            df = self._normalize_dataframe(df)
            self.active_tickets = {int(t) for t in pd.to_numeric(df[df["status"] == "OPEN"]["ticket"], errors="coerce").fillna(0).astype(int).tolist() if int(t) > 0}
        except Exception:
            self.active_tickets = set()

    def upsert_open_snapshots(self, snapshots):
        return helper_upsert_open_snapshots(self, snapshots=snapshots, logger=logger)

    def ensure_open_position_logged(self, position, source: str = "MANUAL"):
        if position is None:
            return False
        ticket = int(getattr(position, "ticket", 0) or 0)
        if ticket <= 0:
            return False
        manual_entry_tag = normalize_manual_reason_tag(getattr(position, "comment", "") or "")
        snap = {
            "ticket": ticket,
            "symbol": str(getattr(position, "symbol", "") or ""),
            "direction": "BUY" if int(getattr(position, "type", 0) or 0) == int(ORDER_TYPE_BUY) else "SELL",
            "lot": float(getattr(position, "volume", 0.0) or 0.0),
            "open_price": float(getattr(position, "price_open", 0.0) or 0.0),
            "entry_reason": f"[{str(source or 'MANUAL').upper()}] Position Snapshot",
            "manual_entry_tag": manual_entry_tag,
            "source": str(source or "MANUAL").upper(),
        }
        return bool(self.upsert_open_snapshots([snap]))

    def log_entry(
        self,
        ticket,
        symbol,
        direction,
        price,
        reason,
        entry_score=0,
        contra_score=0,
        lot=0.0,
        indicators=None,
        regime=None,
        entry_stage="balanced",
        entry_setup_id="",
        management_profile_id="",
        invalidation_id="",
        exit_profile="",
        prediction_bundle="",
        entry_wait_state="",
        entry_quality=0.0,
        entry_model_confidence=0.0,
        regime_at_entry="",
        entry_h1_context_score=0.0,
        entry_m1_trigger_score=0.0,
        entry_h1_gate_pass=0.0,
        entry_h1_gate_reason="",
        entry_topdown_gate_pass=0.0,
        entry_topdown_gate_reason="",
        entry_topdown_align_count=0.0,
        entry_topdown_conflict_count=0.0,
        entry_topdown_seen_count=0.0,
        entry_session_name="",
        entry_weekday=0.0,
        entry_session_threshold_mult=1.0,
        entry_atr_ratio=1.0,
        entry_atr_threshold_mult=1.0,
        entry_request_price=0.0,
        entry_fill_price=0.0,
        entry_slippage_points=0.0,
        decision_row_key="",
        runtime_snapshot_key="",
        trade_link_key="",
        replay_row_key="",
        signal_age_sec=0.0,
        bar_age_sec=0.0,
        decision_latency_ms=0,
        order_submit_latency_ms=0,
        missing_feature_count=0,
        data_completeness_ratio=0.0,
        used_fallback_count=0,
        compatibility_mode="",
        detail_blob_bytes=0,
        snapshot_payload_bytes=0,
        row_payload_bytes=0,
        micro_breakout_readiness_state="",
        micro_reversal_risk_state="",
        micro_participation_state="",
        micro_gap_context_state="",
        micro_body_size_pct_20=0.0,
        micro_doji_ratio_20=0.0,
        micro_same_color_run_current=0,
        micro_same_color_run_max_20=0,
        micro_range_compression_ratio_20=0.0,
        micro_volume_burst_ratio_20=0.0,
        micro_volume_burst_decay_20=0.0,
        micro_gap_fill_progress=0.0,
        micro_upper_wick_ratio_20=0.0,
        micro_lower_wick_ratio_20=0.0,
        micro_swing_high_retest_count_20=0,
        micro_swing_low_retest_count_20=0,
    ):
        parsed_entry_atr_ratio = pd.to_numeric(entry_atr_ratio, errors="coerce")
        effective_entry_atr_ratio = 1.0 if pd.isna(parsed_entry_atr_ratio) else float(parsed_entry_atr_ratio)
        regime_volatility_ratio = pd.to_numeric((regime or {}).get("volatility_ratio", float("nan")), errors="coerce")
        if (
            abs(effective_entry_atr_ratio) <= 1e-12
            or abs(effective_entry_atr_ratio - 1.0) <= 1e-12
        ) and (not pd.isna(regime_volatility_ratio)):
            regime_volatility_ratio = float(regime_volatility_ratio)
            if regime_volatility_ratio > 0.0 and abs(regime_volatility_ratio - 1.0) > 1e-6:
                effective_entry_atr_ratio = regime_volatility_ratio
        snap = {
            "ticket": int(ticket),
            "symbol": symbol,
            "direction": direction,
            "lot": float(lot or 0.0),
            "open_price": float(price or 0.0),
            "decision_row_key": str(decision_row_key or ""),
            "runtime_snapshot_key": str(runtime_snapshot_key or ""),
            "trade_link_key": str(trade_link_key or ""),
            "replay_row_key": str(replay_row_key or ""),
            "signal_age_sec": float(pd.to_numeric(signal_age_sec, errors="coerce") or 0.0),
            "bar_age_sec": float(pd.to_numeric(bar_age_sec, errors="coerce") or 0.0),
            "decision_latency_ms": int(pd.to_numeric(decision_latency_ms, errors="coerce") or 0),
            "order_submit_latency_ms": int(pd.to_numeric(order_submit_latency_ms, errors="coerce") or 0),
            "missing_feature_count": int(pd.to_numeric(missing_feature_count, errors="coerce") or 0),
            "data_completeness_ratio": float(pd.to_numeric(data_completeness_ratio, errors="coerce") or 0.0),
            "used_fallback_count": int(pd.to_numeric(used_fallback_count, errors="coerce") or 0),
            "compatibility_mode": str(compatibility_mode or ""),
            "detail_blob_bytes": int(pd.to_numeric(detail_blob_bytes, errors="coerce") or 0),
            "snapshot_payload_bytes": int(pd.to_numeric(snapshot_payload_bytes, errors="coerce") or 0),
            "row_payload_bytes": int(pd.to_numeric(row_payload_bytes, errors="coerce") or 0),
            "micro_breakout_readiness_state": str(micro_breakout_readiness_state or "").strip(),
            "micro_reversal_risk_state": str(micro_reversal_risk_state or "").strip(),
            "micro_participation_state": str(micro_participation_state or "").strip(),
            "micro_gap_context_state": str(micro_gap_context_state or "").strip(),
            "micro_body_size_pct_20": float(pd.to_numeric(micro_body_size_pct_20, errors="coerce") or 0.0),
            "micro_doji_ratio_20": float(pd.to_numeric(micro_doji_ratio_20, errors="coerce") or 0.0),
            "micro_same_color_run_current": int(pd.to_numeric(micro_same_color_run_current, errors="coerce") or 0),
            "micro_same_color_run_max_20": int(pd.to_numeric(micro_same_color_run_max_20, errors="coerce") or 0),
            "micro_range_compression_ratio_20": float(pd.to_numeric(micro_range_compression_ratio_20, errors="coerce") or 0.0),
            "micro_volume_burst_ratio_20": float(pd.to_numeric(micro_volume_burst_ratio_20, errors="coerce") or 0.0),
            "micro_volume_burst_decay_20": float(pd.to_numeric(micro_volume_burst_decay_20, errors="coerce") or 0.0),
            "micro_gap_fill_progress": float(pd.to_numeric(micro_gap_fill_progress, errors="coerce") or 0.0),
            "micro_upper_wick_ratio_20": float(pd.to_numeric(micro_upper_wick_ratio_20, errors="coerce") or 0.0),
            "micro_lower_wick_ratio_20": float(pd.to_numeric(micro_lower_wick_ratio_20, errors="coerce") or 0.0),
            "micro_swing_high_retest_count_20": int(pd.to_numeric(micro_swing_high_retest_count_20, errors="coerce") or 0),
            "micro_swing_low_retest_count_20": int(pd.to_numeric(micro_swing_low_retest_count_20, errors="coerce") or 0),
            "entry_score": int(entry_score or 0),
            "contra_score_at_entry": int(contra_score or 0),
            "entry_stage": self._normalize_entry_stage(entry_stage),
            "entry_setup_id": str(entry_setup_id or ""),
            "management_profile_id": str(management_profile_id or "").strip().lower(),
            "invalidation_id": str(invalidation_id or "").strip().lower(),
            "exit_profile": str(exit_profile or "").strip().lower(),
            "prediction_bundle": str(prediction_bundle or ""),
            "entry_wait_state": str(entry_wait_state or "").strip().upper(),
            "entry_quality": float(pd.to_numeric(entry_quality, errors="coerce") or 0.0),
            "entry_model_confidence": float(pd.to_numeric(entry_model_confidence, errors="coerce") or 0.0),
            "entry_h1_context_score": float(pd.to_numeric(entry_h1_context_score, errors="coerce") or 0.0),
            "entry_m1_trigger_score": float(pd.to_numeric(entry_m1_trigger_score, errors="coerce") or 0.0),
            "entry_h1_gate_pass": float(pd.to_numeric(entry_h1_gate_pass, errors="coerce") or 0.0),
            "entry_h1_gate_reason": str(entry_h1_gate_reason or ""),
            "entry_topdown_gate_pass": float(pd.to_numeric(entry_topdown_gate_pass, errors="coerce") or 0.0),
            "entry_topdown_gate_reason": str(entry_topdown_gate_reason or ""),
            "entry_topdown_align_count": float(pd.to_numeric(entry_topdown_align_count, errors="coerce") or 0.0),
            "entry_topdown_conflict_count": float(pd.to_numeric(entry_topdown_conflict_count, errors="coerce") or 0.0),
            "entry_topdown_seen_count": float(pd.to_numeric(entry_topdown_seen_count, errors="coerce") or 0.0),
            "entry_session_name": str(entry_session_name or "").strip().upper(),
            "entry_weekday": float(pd.to_numeric(entry_weekday, errors="coerce") or 0.0),
            "entry_session_threshold_mult": float(pd.to_numeric(entry_session_threshold_mult, errors="coerce") or 1.0),
            "entry_atr_ratio": float(effective_entry_atr_ratio),
            "entry_atr_threshold_mult": float(pd.to_numeric(entry_atr_threshold_mult, errors="coerce") or 1.0),
            "entry_request_price": float(pd.to_numeric(entry_request_price, errors="coerce") or 0.0),
            "entry_fill_price": float(pd.to_numeric(entry_fill_price, errors="coerce") or 0.0),
            "entry_slippage_points": float(pd.to_numeric(entry_slippage_points, errors="coerce") or 0.0),
            "entry_reason": str(reason or ""),
            "regime": regime or {},
            "regime_at_entry": str(regime_at_entry or ""),
            "indicators": indicators or {},
            "source": "AUTO",
        }
        return bool(self.upsert_open_snapshots([snap]))

    def register_exit_request(self, ticket, reason, exit_score, detail=None):
        self.pending_exit[int(ticket)] = {
            "reason": str(reason or "").strip(),
            "detail": str(detail or "").strip(),
            "exit_score": int(exit_score or 0),
        }

    def update_live_exit_context(self, ticket, reason, exit_score, detail=""):
        self.live_exit_context[int(ticket)] = {
            "reason": str(reason or "").strip(),
            "detail": str(detail or "").strip(),
            "exit_score": int(exit_score or 0),
        }

    def update_exit_policy_context(self, ticket, policy: dict):
        if not isinstance(policy, dict) or not policy:
            return
        t = int(ticket or 0)
        if t <= 0:
            return
        sanitized = {}
        for k, v in policy.items():
            key = str(k)
            if key not in TRADE_COLUMNS:
                continue
            if v is None:
                continue
            sanitized[key] = v
        if not sanitized:
            return
        previous_pending = dict(self._pending_open_policy_context.get(t, {}) or {})
        pending = dict(previous_pending)
        for k, v in sanitized.items():
            current = pending.get(k, "")
            if isinstance(v, str) and str(v).strip() == "" and str(current or "").strip() != "":
                continue
            pending[k] = v
        committed = dict(self._committed_open_policy_context.get(t, {}) or {})
        delta = {k: v for k, v in pending.items() if committed.get(k) != v}
        self._pending_open_policy_context[t] = pending
        if not delta:
            return
        try:
            if delta and self._store.patch_open_trade_fields(t, delta):
                committed.update(delta)
                self._committed_open_policy_context[t] = committed
                self._mark_store_success("patch_open_trade_fields")
                return
        except Exception as exc:
            self._mark_store_failure("patch_open_trade_fields", exc)
        try:
            df = self._read_open_df_safe()
            df = self._normalize_dataframe(df)
            idx = df.index[(df["ticket"] == t) & (df["status"] == "OPEN")]
            if idx.empty:
                return
            i = idx.tolist()[-1]
            for k, v in delta.items():
                current = df.at[i, str(k)] if str(k) in df.columns else ""
                if isinstance(v, str) and str(v).strip() == "" and str(current or "").strip() != "":
                    continue
                if str(k) in df.columns:
                    df.at[i, str(k)] = v
            self._write_open_df(df)
            self._sync_open_rows_to_store(df[df["status"] == "OPEN"].copy())
            committed.update(delta)
            self._committed_open_policy_context[t] = committed
        except Exception as exc:
            logger.exception("Failed to update exit policy context for %s: %s", t, exc)

    def get_trade_context(self, ticket):
        try:
            t = int(ticket or 0)
            if t <= 0:
                return None
            try:
                cached = self._store.get_open_trade_context(t)
            except Exception:
                cached = None
            if isinstance(cached, dict) and cached:
                if t not in self._committed_open_policy_context:
                    self._committed_open_policy_context[t] = dict(cached)
                pending = dict(self._pending_open_policy_context.get(t, {}) or {})
                if pending:
                    cached = dict(cached)
                    cached.update(pending)
                return cached
            df = self._read_open_df_safe()
            if df.empty:
                return None
            df = self._normalize_dataframe(df)
            cand = df[(df["ticket"] == t) & (df["status"] == "OPEN")]
            if cand.empty:
                cand = df[df["ticket"] == t]
            if cand.empty:
                return None
            r = cand.iloc[-1]
            out = {k: r.get(k) for k in self._columns() if k in cand.columns}
            pending = dict(self._pending_open_policy_context.get(t, {}) or {})
            if pending:
                out.update(pending)
            return out
        except Exception as exc:
            logger.exception("Failed to get trade context for %s: %s", ticket, exc)
            return None

    def check_closed_trades(self):
        return helper_check_closed_trades(self)

    @staticmethod
    def _find_latest_exit_deal(history, ticket):
        exit_deal = None
        for deal in history:
            if deal.position_id == ticket and int(deal.entry) in {int(DEAL_ENTRY_OUT), int(DEAL_ENTRY_OUT_BY)}:
                if exit_deal is None or deal.time > exit_deal.time:
                    exit_deal = deal
        return exit_deal

    def _find_latest_exit_deal_direct(self, ticket):
        latest = None
        try:
            deals = self.broker.history_deals_get(position=int(ticket)) or []
            for d in deals:
                if int(getattr(d, "entry", -1)) in {int(DEAL_ENTRY_OUT), int(DEAL_ENTRY_OUT_BY)}:
                    if latest is None or int(getattr(d, "time", 0)) > int(getattr(latest, "time", 0)):
                        latest = d
        except Exception:
            pass
        return latest

    def _sum_exit_profit_for_position(self, ticket) -> Optional[float]:
        try:
            deals = self.broker.history_deals_get(position=int(ticket)) or []
            total = 0.0
            hit = False
            for d in deals:
                if int(getattr(d, "entry", -1)) in {int(DEAL_ENTRY_OUT), int(DEAL_ENTRY_OUT_BY)}:
                    total += float(getattr(d, "profit", 0.0) or 0.0)
                    total += float(getattr(d, "swap", 0.0) or 0.0)
                    total += float(getattr(d, "commission", 0.0) or 0.0)
                    hit = True
            if hit:
                return float(total)
        except Exception:
            pass
        return None

    def reconcile_open_trades(self, lookback_days=30, *, light_mode=False, profile=False):
        try:
            return helper_reconcile_open_trades(
                self,
                lookback_days=lookback_days,
                light_mode=light_mode,
                profile=profile,
            )
        except Exception as exc:
            logger.exception("Failed to reconcile open trades: %s", exc)
            return 0, 0, 0

    def _force_close_unknown(self, ticket, reason="Manual/Unknown", exit_score=0):
        return helper_force_close_unknown(self, ticket=ticket, reason=reason, exit_score=exit_score, logger=logger)

    def _update_closed_trade(self, ticket, deal, fallback_reason="Manual/Unknown"):
        return helper_update_closed_trade(self, ticket=ticket, deal=deal, fallback_reason=fallback_reason, logger=logger)

    def recommend_thresholds(self, default_entry: int, default_exit: int) -> Tuple[int, int, Optional[str]]:
        return helper_recommend_thresholds(
            read_closed_df=self._read_closed_df,
            default_entry=int(default_entry),
            default_exit=int(default_exit),
            logger=logger,
        )

    def recommend_exit_policy(self):
        return helper_recommend_exit_policy(
            read_closed_df=self._read_closed_df,
            normalize_exit_reason=self._normalize_exit_reason,
            logger=logger,
        )

    def recommend_adverse_policy(self, default_loss_usd: float, default_reverse_score: int):
        return helper_recommend_adverse_policy(
            read_closed_df=self._read_closed_df,
            normalize_exit_reason=self._normalize_exit_reason,
            default_loss_usd=float(default_loss_usd),
            default_reverse_score=int(default_reverse_score),
            logger=logger,
        )
