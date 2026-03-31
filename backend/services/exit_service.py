"""
Exit execution service.
"""

from datetime import datetime
import logging
import math
import time

import pandas as pd

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.domain.decision_models import DecisionContext, DecisionResult, ExitProfile, PredictionBundle, WaitState
from backend.services.consumer_contract import EXIT_HANDOFF_CONTRACT_V1
from backend.services.context_classifier import ContextClassifier
from backend.services.exit_manage_context_contract import (
    build_exit_manage_context_v1,
    compact_exit_manage_context_v1,
)
from backend.services.exit_recovery_predictor import ExitRecoveryPredictor
from backend.services.predictors import ShadowExitPredictor, ShadowWaitPredictor
from backend.services.wait_engine import WaitEngine
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard
from backend.services.exit_engines import (
    ExitActionExecutor,
    ExitMetricsCollector,
    ExitRiskGuard,
    ExitStageRouter,
)
from backend.services.exit_manage_positions import manage_positions as helper_manage_positions
from backend.services.adaptive_profile_helpers import refresh_exit_profile
from ports.closed_trade_read_port import ClosedTradeReadPort
from ports.trading_runtime_port import ExitRuntimePort

logger = logging.getLogger(__name__)


class ExitService:
    def __init__(self, runtime: ExitRuntimePort, trade_logger: ClosedTradeReadPort):
        self.runtime = runtime
        self.trade_logger = trade_logger
        self.reversal_streak = {}
        self.partial_done = {}
        self.be_moved = {}
        self.peak_profit = {}
        self.exit_delay_ticks = {}
        self.shock_tick_state = {}
        self.adverse_wait_state = {}
        self.stage_streak = {}
        self._spread_cache = {}
        self._adaptive_exit_profile = {
            "updated_at": 0.0,
            "n": 0,
            "stage_quality": {"protect": 0.0, "lock": 0.0, "hold": 0.0},
            "stage_wr": {"protect": 0.50, "lock": 0.50, "hold": 0.50},
            "stage_exp": {"protect": 0.0, "lock": 0.0, "hold": 0.0},
        }
        self._exit_metrics = {
            "stage_select_protect": 0,
            "stage_select_lock": 0,
            "stage_select_hold": 0,
            "exec_profile_conservative": 0,
            "exec_profile_neutral": 0,
            "exec_profile_aggressive": 0,
            "exit_protect": 0,
            "exit_lock": 0,
            "exit_target": 0,
            "exit_rsi_scalp": 0,
            "exit_bb_scalp": 0,
            "exit_reversal": 0,
            "exit_time_stop": 0,
            "exit_emergency_stop": 0,
            "exit_adverse_stop": 0,
            "exit_adverse_reversal": 0,
            "adverse_recheck_hits": 0,
            "risk_guard_triggered_total": 0,
            "risk_guard_plus_to_minus": 0,
            "risk_guard_adverse": 0,
            "entry_meta_cap_hits": 0,
        }
        self._exit_runtime = {
            "blend_mode": str(getattr(Config, "EXIT_ADAPTIVE_BLEND_MODE", "dynamic") or "dynamic").strip().lower(),
            "blend_rule_weight": float(getattr(Config, "EXIT_ADAPTIVE_RULE_WEIGHT", 0.55)),
            "blend_model_weight": float(getattr(Config, "EXIT_ADAPTIVE_MODEL_WEIGHT", 0.45)),
            "blend_history": [],
        }
        self._exit_runtime_by_symbol = {}
        self._regime_runtime_by_symbol = {}
        self._last_metrics_log_at = 0.0
        self._context_classifier = ContextClassifier(getattr(runtime, "broker", None))
        self._wait_engine = WaitEngine()
        self._wait_predictor = ShadowWaitPredictor()
        self._exit_predictor = ShadowExitPredictor()
        self._recovery_predictor = ExitRecoveryPredictor()
        self._metrics_collector = ExitMetricsCollector()
        self._stage_router = ExitStageRouter()
        self._action_executor = ExitActionExecutor(
            runtime=self.runtime,
            trade_logger=self.trade_logger,
            bump_metric=self._bump_metric,
            reset_state=self._reset_position_runtime_state,
        )
        self._risk_guard = ExitRiskGuard(
            action_executor=self._action_executor,
            bump_metric=self._bump_metric,
            check_profit_giveback=self._is_profit_giveback_guard_hit,
            check_plus_to_minus=self._is_plus_to_minus_guard_hit,
            should_delay_adverse=self._should_delay_adverse_exit,
        )

    @staticmethod
    def _base_symbol_cost(symbol: str) -> float:
        upper = str(symbol or "").upper()
        for k, v in Config.ROUNDTRIP_COST_USD.items():
            if k == "DEFAULT":
                continue
            if k in upper:
                return float(v)
        return float(Config.ROUNDTRIP_COST_USD.get("DEFAULT", 0.5))

    def _recent_spread_ratio(self, symbol: str) -> float:
        if not Config.ENABLE_DYNAMIC_SPREAD_COST:
            return 1.0
        key = str(symbol or "").upper()
        now_s = time.time()
        cached = self._spread_cache.get(key)
        ttl = max(10, int(getattr(Config, "DYNAMIC_COST_CACHE_TTL_SEC", 60)))
        if cached and (now_s - float(cached.get("ts", 0.0)) <= ttl):
            return float(cached.get("ratio", 1.0))

        ratio = 1.0
        try:
            reader = getattr(self.trade_logger, "read_closed_df", None)
            if callable(reader):
                closed = reader()
                if closed is not None and not closed.empty and "regime_spread_ratio" in closed.columns:
                    subset = closed[closed["symbol"].astype(str).str.upper() == key].copy()
                    subset["regime_spread_ratio"] = pd.to_numeric(subset["regime_spread_ratio"], errors="coerce")
                    subset = subset[subset["regime_spread_ratio"] > 0]
                    if not subset.empty:
                        lookback = max(10, int(getattr(Config, "DYNAMIC_COST_RECENT_TRADES", 40)))
                        ratio = float(subset["regime_spread_ratio"].tail(lookback).median())
        except Exception:
            ratio = 1.0

        if not (ratio > 0):
            ratio = 1.0
        self._spread_cache[key] = {"ratio": float(ratio), "ts": now_s}
        return float(ratio)

    def _symbol_cost(self, symbol: str, live_spread_ratio: float = 1.0) -> float:
        base = float(self._base_symbol_cost(symbol))
        if not Config.ENABLE_DYNAMIC_SPREAD_COST:
            return base
        current_ratio = float(live_spread_ratio) if float(live_spread_ratio) > 0 else 1.0
        recent_ratio = self._recent_spread_ratio(symbol)
        spread_mult = (current_ratio / recent_ratio) if recent_ratio > 0 else 1.0
        spread_mult = self._clamp(
            spread_mult,
            float(getattr(Config, "DYNAMIC_COST_SPREAD_MIN_MULT", 0.8)),
            float(getattr(Config, "DYNAMIC_COST_SPREAD_MAX_MULT", 2.2)),
        )
        return float(base * spread_mult)

    def _tick_reversal_streak(self, ticket: int, hit: bool) -> int:
        t = int(ticket)
        if not hit:
            self.reversal_streak.pop(t, None)
            return 0
        n = int(self.reversal_streak.get(t, 0)) + 1
        self.reversal_streak[t] = n
        return n

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(float(lo), min(float(hi), float(v)))

    @staticmethod
    def _store_runtime_snapshot(runtime, symbol: str, key: str, payload: dict) -> None:
        try:
            rows = getattr(runtime, "latest_signal_by_symbol", None)
            if not isinstance(rows, dict):
                return
            row = rows.get(symbol, {})
            if not isinstance(row, dict):
                row = {}
            row[str(key)] = dict(payload or {})
            rows[symbol] = row
        except Exception:
            return

    @staticmethod
    def _merge_runtime_fields(runtime, symbol: str, payload: dict) -> None:
        try:
            rows = getattr(runtime, "latest_signal_by_symbol", None)
            if not isinstance(rows, dict):
                return
            row = rows.get(symbol, {})
            if not isinstance(row, dict):
                row = {}
            row.update(dict(payload or {}))
            rows[symbol] = row
        except Exception:
            return

    def _snapshot_exit_evaluation(
        self,
        *,
        symbol: str,
        trade_ctx: dict,
        stage_inputs: dict,
        chosen_stage: str,
        policy_stage: str,
        exec_profile: str,
        confirm_needed: int,
        exit_signal_score: int,
        score_gap: int,
        adverse_risk: bool,
        tf_confirm: bool,
        detail: dict | None = None,
    ) -> WaitState:
        payload = dict(detail or {})
        context = self._context_classifier.build_exit_context(
            symbol=str(symbol or ""),
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            adverse_risk=bool(adverse_risk),
            tf_confirm=bool(tf_confirm),
        )
        context.raw_scores.update(
            {
                "exit_signal_score": int(exit_signal_score),
                "score_gap": int(score_gap),
            }
        )
        context.thresholds.update(
            {
                "exit_threshold": payload.get("exit_threshold", ""),
                "reverse_signal_threshold": payload.get("reverse_signal_threshold", ""),
                "confirm_needed": int(confirm_needed),
            }
        )
        context.metadata.update(
            {
                "chosen_stage": str(chosen_stage or ""),
                "policy_stage": str(policy_stage or ""),
            }
        )
        exit_manage_context_v1 = build_exit_manage_context_v1(
            symbol=str(symbol or ""),
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            chosen_stage=str(chosen_stage or ""),
            policy_stage=str(policy_stage or ""),
            exec_profile=str(exec_profile or ""),
            confirm_needed=int(confirm_needed),
            exit_signal_score=int(exit_signal_score),
            score_gap=int(score_gap),
            adverse_risk=bool(adverse_risk),
            tf_confirm=bool(tf_confirm),
            detail=payload,
        )
        compact_exit_context_v1 = compact_exit_manage_context_v1(exit_manage_context_v1)
        exit_identity_context = dict(exit_manage_context_v1.get("identity", {}) or {})
        exit_handoff_context = dict(exit_manage_context_v1.get("handoff", {}) or {})
        exit_posture_context = dict(exit_manage_context_v1.get("posture", {}) or {})
        exit_market_context = dict(exit_manage_context_v1.get("market", {}) or {})
        exit_risk_context = dict(exit_manage_context_v1.get("risk", {}) or {})
        context.metadata.update(
            {
                "management_profile_id": str(exit_handoff_context.get("management_profile_id", "") or ""),
                "invalidation_id": str(exit_handoff_context.get("invalidation_id", "") or ""),
                "exit_manage_context_v1": dict(compact_exit_context_v1),
            }
        )
        wait_state = self._wait_engine.build_exit_wait_state(
            symbol=str(symbol or ""),
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            adverse_risk=bool(adverse_risk),
            tf_confirm=bool(tf_confirm),
            chosen_stage=str(chosen_stage or ""),
            policy_stage=str(policy_stage or ""),
            confirm_needed=int(confirm_needed),
            exit_signal_score=int(exit_signal_score),
            score_gap=int(score_gap),
            detail={**payload, "exit_manage_context_v1": dict(exit_manage_context_v1)},
        )
        exit_profile = ExitProfile(
            profile_id=str(
                exit_posture_context.get("lifecycle_exit_profile", "")
                or exit_posture_context.get("resolved_exit_profile", "")
                or exit_posture_context.get("base_exit_profile", "")
                or exec_profile
                or ""
            ),
            policy_stage=str(exit_posture_context.get("policy_stage", policy_stage) or ""),
            selector_stage=str(exit_posture_context.get("chosen_stage", chosen_stage) or ""),
            confirm_needed=int(confirm_needed),
            regime_name=str(exit_market_context.get("regime_now", "UNKNOWN") or "UNKNOWN"),
            metadata={
                "entry_setup_id": str(exit_identity_context.get("entry_setup_id", "") or ""),
                "management_profile_id": str(exit_handoff_context.get("management_profile_id", "") or ""),
                "invalidation_id": str(exit_handoff_context.get("invalidation_id", "") or ""),
                "entry_exit_profile": str(exit_posture_context.get("resolved_exit_profile", "") or ""),
                "execution_profile": str(exit_posture_context.get("execution_profile", exec_profile) or ""),
                "exit_handoff_v1": dict(exit_handoff_context.get("exit_handoff_v1", {}) or {}),
                "exit_handoff_contract_v1": dict(EXIT_HANDOFF_CONTRACT_V1),
                "exit_manage_context_v1": dict(compact_exit_context_v1),
                "regime_at_entry": str(exit_market_context.get("regime_at_entry", "UNKNOWN") or "UNKNOWN"),
                "profit": exit_risk_context.get("profit", (stage_inputs or {}).get("profit", "")),
                "duration_sec": exit_risk_context.get("duration_sec", (stage_inputs or {}).get("duration_sec", "")),
                "favorable_move_pct": exit_risk_context.get(
                    "favorable_move_pct",
                    (stage_inputs or {}).get("favorable_move_pct", ""),
                ),
            },
        )
        exit_predictions = self._exit_predictor.predict(
            context=context,
            wait_state=wait_state,
            exit_profile=exit_profile,
            metrics={
                "profit": (stage_inputs or {}).get("profit", 0.0),
                "score_gap": int(score_gap),
                "adverse_risk": bool(adverse_risk),
                "tf_confirm": bool(tf_confirm),
            },
        )
        wait_predictions = self._wait_predictor.predict_exit_wait(
            context=context,
            wait_state=wait_state,
            exit_profile=exit_profile,
            metrics={
                "profit": (stage_inputs or {}).get("profit", 0.0),
                "giveback": max(
                    0.0,
                    float((stage_inputs or {}).get("peak_profit", (stage_inputs or {}).get("profit", 0.0)) or 0.0)
                    - float((stage_inputs or {}).get("profit", 0.0) or 0.0),
                ),
            },
        )
        recovery_predictions = self._recovery_predictor.predict(
            context=context,
            wait_state=wait_state,
            exit_profile=exit_profile,
            metrics={
                "profit": (stage_inputs or {}).get("profit", 0.0),
                "giveback": max(
                    0.0,
                    float((stage_inputs or {}).get("peak_profit", (stage_inputs or {}).get("profit", 0.0)) or 0.0)
                    - float((stage_inputs or {}).get("profit", 0.0) or 0.0),
                ),
                "score_gap": int(score_gap),
                "adverse_risk": bool(adverse_risk),
                "tf_confirm": bool(tf_confirm),
                "management_profile_id": str(exit_handoff_context.get("management_profile_id", "") or ""),
                "invalidation_id": str(exit_handoff_context.get("invalidation_id", "") or ""),
                "duration_sec": float(
                    exit_risk_context.get("duration_sec", (stage_inputs or {}).get("duration_sec", 0.0)) or 0.0
                ),
                "entry_setup_id": str(exit_identity_context.get("entry_setup_id", "") or ""),
                "entry_direction": str(exit_identity_context.get("entry_direction", "") or "").upper(),
                "state_vector_v2": dict((stage_inputs or {}).get("state_vector_v2", {}) or {}) if isinstance((stage_inputs or {}).get("state_vector_v2", {}), dict) else {},
                "state_metadata": dict((((stage_inputs or {}).get("state_vector_v2", {}) or {}).get("metadata", {})) or {}) if isinstance(((stage_inputs or {}).get("state_vector_v2", {}) or {}).get("metadata", {}), dict) else {},
                "belief_state_v1": dict((stage_inputs or {}).get("belief_state_v1", {}) or {}) if isinstance((stage_inputs or {}).get("belief_state_v1", {}), dict) else {},
            },
        )
        utility_shadow = self._wait_engine.evaluate_exit_utility_decision(
            symbol=str(symbol or ""),
            wait_state=wait_state,
            stage_inputs={
                **stage_inputs,
                "score_gap": int(score_gap),
                "adverse_risk": bool(adverse_risk),
            },
            exit_predictions=exit_predictions,
            wait_predictions=wait_predictions,
            recovery_predictions=recovery_predictions,
            exit_profile_id=str(exec_profile or ""),
            roundtrip_cost=self._symbol_cost(
                str(symbol or ""),
                live_spread_ratio=float((stage_inputs or {}).get("spread_ratio", 1.0) or 1.0),
            ),
        )
        exit_wait_taxonomy_v1 = dict(utility_shadow.get("exit_wait_taxonomy_v1", {}) or {})
        wait_metadata = dict(wait_state.metadata or {})
        wait_metadata["exit_wait_taxonomy_v1"] = dict(exit_wait_taxonomy_v1)
        wait_state.metadata = dict(wait_metadata)
        predictions = PredictionBundle(
            entry={},
            wait=dict(wait_predictions or {}),
            exit={**dict(exit_predictions or {}), **dict(recovery_predictions or {})},
            reverse={"p_reverse_valid": float((recovery_predictions or {}).get("p_reverse_valid", (exit_predictions or {}).get("p_reverse_valid", 0.0)) or 0.0)},
            metadata={"phase": "exit", "mode": "shadow"},
        )
        decision_result = DecisionResult(
            phase="exit",
            symbol=str(symbol or ""),
            action="EVALUATE",
            outcome="evaluated",
            blocked_by="",
            reason=str(payload.get("route_txt", "") or ""),
            decision_rule_version="legacy_v1",
            context=context,
            wait_state=wait_state,
            exit_profile=exit_profile,
            predictions=predictions,
            metrics={
                "exit_signal_score": int(exit_signal_score),
                "score_gap": int(score_gap),
                "protect_score": payload.get("protect_score", ""),
                "lock_score": payload.get("lock_score", ""),
                "hold_score": payload.get("hold_score", ""),
                "decision_winner": str(utility_shadow.get("winner", "") or ""),
                "decision_reason": str(utility_shadow.get("decision_reason", "") or ""),
                "utility_exit_now": float(utility_shadow.get("utility_exit_now", 0.0) or 0.0),
                "utility_hold": float(utility_shadow.get("utility_hold", 0.0) or 0.0),
                "utility_reverse": float(utility_shadow.get("utility_reverse", 0.0) or 0.0),
                "utility_wait_exit": float(utility_shadow.get("utility_wait_exit", 0.0) or 0.0),
                "u_cut_now": float(utility_shadow.get("u_cut_now", 0.0) or 0.0),
                "u_wait_be": float(utility_shadow.get("u_wait_be", 0.0) or 0.0),
                "u_wait_tp1": float(utility_shadow.get("u_wait_tp1", 0.0) or 0.0),
                "u_reverse": float(utility_shadow.get("u_reverse", 0.0) or 0.0),
                "p_recover_be": float(utility_shadow.get("p_recover_be", 0.0) or 0.0),
                "p_recover_tp1": float(utility_shadow.get("p_recover_tp1", 0.0) or 0.0),
                "p_deeper_loss": float(utility_shadow.get("p_deeper_loss", 0.0) or 0.0),
                "p_reverse_valid": float(utility_shadow.get("p_reverse_valid", 0.0) or 0.0),
            },
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_manage_context_v1",
            payload=dict(exit_manage_context_v1),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_decision_context_v1",
            payload=context.to_dict(),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_decision_result_v1",
            payload=decision_result.to_dict(),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_wait_state_v1",
            payload=wait_state.to_dict(),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_wait_taxonomy_v1",
            payload=dict(exit_wait_taxonomy_v1),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_prediction_v1",
            payload=predictions.to_dict(),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_recovery_prediction_v1",
            payload=dict(recovery_predictions or {}),
        )
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="exit_utility_v1",
            payload=dict(utility_shadow or {}),
        )
        semantic_exit_rollout = SemanticPromotionGuard.build_exit_rollout_summary(symbol=str(symbol or ""))
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            key="semantic_exit_rollout_v1",
            payload=dict(semantic_exit_rollout),
        )
        self._merge_runtime_fields(
            runtime=self.runtime,
            symbol=str(symbol or ""),
            payload={
                "exit_decision_winner": str(utility_shadow.get("winner", "") or ""),
                "exit_decision_reason": str(utility_shadow.get("decision_reason", "") or ""),
                "utility_exit_now": float(utility_shadow.get("utility_exit_now", 0.0) or 0.0),
                "utility_hold": float(utility_shadow.get("utility_hold", 0.0) or 0.0),
                "utility_reverse": float(utility_shadow.get("utility_reverse", 0.0) or 0.0),
                "utility_wait_exit": float(utility_shadow.get("utility_wait_exit", 0.0) or 0.0),
                "exit_wait_selected": int(1 if utility_shadow.get("wait_selected") else 0),
                "exit_wait_decision": str(utility_shadow.get("wait_decision", "") or ""),
                "p_recover_be": float(utility_shadow.get("p_recover_be", 0.0) or 0.0),
                "p_recover_tp1": float(utility_shadow.get("p_recover_tp1", 0.0) or 0.0),
                "p_deeper_loss": float(utility_shadow.get("p_deeper_loss", 0.0) or 0.0),
                "p_reverse_valid": float(utility_shadow.get("p_reverse_valid", 0.0) or 0.0),
                "u_cut_now": float(utility_shadow.get("u_cut_now", 0.0) or 0.0),
                "u_wait_be": float(utility_shadow.get("u_wait_be", 0.0) or 0.0),
                "u_wait_tp1": float(utility_shadow.get("u_wait_tp1", 0.0) or 0.0),
                "u_reverse": float(utility_shadow.get("u_reverse", 0.0) or 0.0),
                "exit_wait_state_family": str(
                    ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("state_family", "")) or ""
                ),
                "exit_wait_hold_class": str(
                    ((exit_wait_taxonomy_v1.get("state", {}) or {}).get("hold_class", "")) or ""
                ),
                "exit_wait_decision_family": str(
                    ((exit_wait_taxonomy_v1.get("decision", {}) or {}).get("decision_family", "")) or ""
                ),
                "exit_wait_bridge_status": str(
                    ((exit_wait_taxonomy_v1.get("bridge", {}) or {}).get("bridge_status", "")) or ""
                ),
                "semantic_exit_rollout_mode": str(semantic_exit_rollout.get("mode", "") or ""),
                "semantic_exit_rollout_enabled": int(1 if semantic_exit_rollout.get("enabled") else 0),
                "semantic_exit_rollout_owner": str(semantic_exit_rollout.get("owner", "") or ""),
            },
        )
        record_rollout = getattr(self.runtime, "record_semantic_rollout_event", None)
        if callable(record_rollout):
            try:
                record_rollout(domain="exit", event=dict(semantic_exit_rollout))
            except Exception:
                pass
        return wait_state

    def _bump_metric(self, key: str, amount: int = 1) -> None:
        self._metrics_collector.bump(self._exit_metrics, key, amount)

    def _build_shock_context(
        self,
        score_gap: int,
        vol_ratio: float,
        spread_ratio: float,
        adverse_risk: bool,
        tf_confirm: bool,
        profit: float,
        policy_stage: str,
    ) -> dict:
        gap_n = self._clamp(float(score_gap) / 40.0, 0.0, 1.0)
        vol_n = self._clamp((float(vol_ratio) - 1.0) / 0.8, 0.0, 1.0)
        spread_n = self._clamp((float(spread_ratio) - 1.0) / 0.8, 0.0, 1.0)
        adverse_n = 1.0 if adverse_risk else 0.0
        confirm_n = 1.0 if (tf_confirm and int(score_gap) > 0) else 0.0
        shock = 100.0 * (
            (gap_n * 0.35)
            + (vol_n * 0.20)
            + (spread_n * 0.20)
            + (adverse_n * 0.15)
            + (confirm_n * 0.10)
        )
        shock = self._clamp(shock, 0.0, 100.0)

        reasons = []
        if gap_n >= 0.60:
            reasons.append("opposite_score_spike")
        if vol_n >= 0.55:
            reasons.append("volatility_spike")
        if spread_n >= 0.55:
            reasons.append("spread_jump")
        if adverse_n > 0:
            reasons.append("adverse_risk")
        if confirm_n > 0:
            reasons.append("tf_confirm")

        level = "none"
        watch_thr = float(getattr(Config, "SHOCK_LEVEL_WATCH_THRESHOLD", 35.0))
        alert_thr = float(getattr(Config, "SHOCK_LEVEL_ALERT_THRESHOLD", 60.0))
        if shock >= float(alert_thr):
            level = "alert"
        elif shock >= float(watch_thr):
            level = "watch"

        stage_now = str(policy_stage or "auto").strip().lower()
        action = "hold"
        stage_after = stage_now
        if level == "alert":
            if float(profit) > 0.0:
                action = "downgrade_to_short"
                stage_after = "short"
            else:
                action = "force_exit_candidate"
                stage_after = "short"
        elif level == "watch":
            if float(profit) > 0.0:
                action = "downgrade_to_mid"
                stage_after = "mid"

        return {
            "shock_score": round(float(shock), 3),
            "shock_level": str(level),
            "shock_reason": "|".join(reasons) if reasons else "none",
            "shock_action": str(action),
            "pre_shock_stage": stage_now,
            "post_shock_stage": stage_after,
            "shock_at_profit": round(float(profit), 6),
            # Placeholder fields for future counterfactual profit tracking.
            "shock_hold_delta_10": 0.0,
            "shock_hold_delta_30": 0.0,
        }

    @staticmethod
    def _mark_price_for_direction(pos, tick) -> float:
        if int(pos.type) == int(ORDER_TYPE_BUY):
            return float(getattr(tick, "bid", 0.0) or 0.0)
        return float(getattr(tick, "ask", 0.0) or 0.0)

    def _track_shock_event_progress(
        self,
        pos,
        symbol: str,
        direction: str,
        profit: float,
        shock_ctx: dict,
        policy_stage: str,
        tick,
    ) -> dict:
        t = int(getattr(pos, "ticket", 0) or 0)
        if t <= 0:
            return {}
        if not bool(getattr(Config, "ENABLE_SHOCK_COUNTERFACTUAL", True)):
            self.shock_tick_state.pop(t, None)
            return {}
        state = self.shock_tick_state.get(t)
        if not isinstance(state, dict):
            state = {
                "active": False,
                "ticks_elapsed": 0,
                "baseline_profit": float(profit),
                "delta_10": None,
                "delta_30": None,
            }
        level = str((shock_ctx or {}).get("shock_level", "none") or "none").strip().lower()
        if (not state.get("active", False)) and level in {"watch", "alert"}:
            mark_price = self._mark_price_for_direction(pos, tick)
            ok = False
            try:
                ok = bool(
                    self.trade_logger.register_shock_event(
                        ticket=t,
                        symbol=str(symbol or ""),
                        direction=str(direction or ""),
                        lot=float(getattr(pos, "volume", 0.0) or 0.0),
                        event_price=float(mark_price),
                        event_profit=float(profit),
                        shock_score=float((shock_ctx or {}).get("shock_score", 0.0) or 0.0),
                        shock_level=str((shock_ctx or {}).get("shock_level", "") or ""),
                        shock_reason=str((shock_ctx or {}).get("shock_reason", "") or ""),
                        shock_action=str((shock_ctx or {}).get("shock_action", "") or ""),
                        pre_shock_stage=str((shock_ctx or {}).get("pre_shock_stage", policy_stage) or policy_stage),
                        post_shock_stage=str((shock_ctx or {}).get("post_shock_stage", policy_stage) or policy_stage),
                    )
                )
            except Exception:
                ok = False
            if ok:
                state["active"] = True
                state["ticks_elapsed"] = 0
                state["baseline_profit"] = float(profit)
                state["delta_10"] = None
                state["delta_30"] = None

        if state.get("active", False):
            try:
                stream_meta = self.trade_logger.refresh_shock_event_from_mt5_ticks(
                    ticket=t,
                    symbol=str(symbol or ""),
                    direction=str(direction or ""),
                )
            except Exception:
                stream_meta = {}
            if isinstance(stream_meta, dict):
                state["ticks_elapsed"] = int(stream_meta.get("ticks_elapsed", state.get("ticks_elapsed", 0)) or 0)
                if stream_meta.get("shock_hold_delta_10") is not None:
                    state["delta_10"] = float(stream_meta.get("shock_hold_delta_10"))
                if stream_meta.get("shock_hold_delta_30") is not None:
                    state["delta_30"] = float(stream_meta.get("shock_hold_delta_30"))

        self.shock_tick_state[t] = state
        out = {}
        if state.get("delta_10") is not None:
            out["shock_hold_delta_10"] = float(state.get("delta_10"))
        if state.get("delta_30") is not None:
            out["shock_hold_delta_30"] = float(state.get("delta_30"))
        return out

    def _log_exit_metrics_if_due(self) -> None:
        self._last_metrics_log_at = self._metrics_collector.log_if_due(self._exit_metrics, self._last_metrics_log_at)

    def get_exit_metrics(self) -> dict:
        return self._metrics_collector.snapshot(
            metrics=self._exit_metrics,
            exit_runtime=self._exit_runtime,
            exit_runtime_by_symbol=self._exit_runtime_by_symbol,
            regime_runtime_by_symbol=self._regime_runtime_by_symbol,
        )

    def _runtime_slot(self, symbol: str) -> dict:
        key = str(symbol or "").upper().strip() or "GLOBAL"
        if key not in self._exit_runtime_by_symbol:
            self._exit_runtime_by_symbol[key] = {
                "blend_mode": str(getattr(Config, "EXIT_ADAPTIVE_BLEND_MODE", "dynamic") or "dynamic").strip().lower(),
                "blend_rule_weight": float(getattr(Config, "EXIT_ADAPTIVE_RULE_WEIGHT", 0.55)),
                "blend_model_weight": float(getattr(Config, "EXIT_ADAPTIVE_MODEL_WEIGHT", 0.45)),
                "blend_history": [],
            }
        return self._exit_runtime_by_symbol[key]

    def _resolve_effective_regime(self, symbol: str, observed_regime: str) -> tuple[str, dict]:
        key = str(symbol or "").upper().strip() or "GLOBAL"
        obs = str(observed_regime or "UNKNOWN").upper().strip() or "UNKNOWN"
        slot = self._regime_runtime_by_symbol.get(key)
        if not isinstance(slot, dict):
            slot = {
                "effective": obs,
                "last_seen": obs,
                "seen_streak": 1,
                "last_switch_ts": 0.0,
                "switch_count": 0,
                "switch_blocked_count": 0,
            }
            self._regime_runtime_by_symbol[key] = slot
        now_s = time.time()
        if obs == str(slot.get("last_seen", "UNKNOWN")):
            slot["seen_streak"] = int(slot.get("seen_streak", 0)) + 1
        else:
            slot["last_seen"] = obs
            slot["seen_streak"] = 1
        min_streak = max(1, int(getattr(Config, "REGIME_SWITCH_MIN_STREAK", 2)))
        cooldown_sec = max(0.0, float(getattr(Config, "REGIME_SWITCH_COOLDOWN_SEC", 45.0)))
        effective = str(slot.get("effective", obs))
        can_switch = ((now_s - float(slot.get("last_switch_ts", 0.0))) >= cooldown_sec) and (
            int(slot.get("seen_streak", 0)) >= min_streak
        )
        if obs != effective:
            if can_switch:
                slot["effective"] = obs
                slot["last_switch_ts"] = now_s
                slot["switch_count"] = int(slot.get("switch_count", 0)) + 1
            else:
                slot["switch_blocked_count"] = int(slot.get("switch_blocked_count", 0)) + 1
        remain = max(0.0, float(cooldown_sec - (now_s - float(slot.get("last_switch_ts", 0.0)))))
        return str(slot.get("effective", obs)), {
            "observed": obs,
            "effective": str(slot.get("effective", obs)),
            "seen_streak": int(slot.get("seen_streak", 0)),
            "switch_count": int(slot.get("switch_count", 0)),
            "switch_blocked_count": int(slot.get("switch_blocked_count", 0)),
            "cooldown_remaining_sec": round(remain, 3),
        }

    @staticmethod
    def _build_exit_signal_score(opposite_score, current_side_score, exit_context_score, adverse_risk):
        opp = max(0.0, float(opposite_score))
        cur = max(0.0, float(current_side_score))
        ctx = max(0.0, float(exit_context_score))
        gap = max(0.0, opp - cur)
        score = (
            ctx
            + (opp * float(Config.EXIT_SCORE_OPPOSITE_WEIGHT))
            + (gap * float(Config.EXIT_SCORE_GAP_WEIGHT))
        )
        if adverse_risk:
            score += float(Config.EXIT_SCORE_ADVERSE_BONUS)
        score = ExitService._clamp(score, float(Config.EXIT_SCORE_MIN), float(Config.EXIT_SCORE_MAX))
        return int(round(score))

    @staticmethod
    def _favorable_move_pct(pos, tick) -> float:
        if int(pos.type) == int(ORDER_TYPE_BUY) and pos.price_open > 0:
            return max(0.0, (tick.bid - pos.price_open) / pos.price_open)
        if int(pos.type) == int(ORDER_TYPE_SELL) and pos.price_open > 0:
            return max(0.0, (pos.price_open - tick.ask) / pos.price_open)
        return 0.0

    def _tick_stage_streak(self, ticket: int, stage: str, hit: bool) -> int:
        key = f"{int(ticket)}:{str(stage)}"
        if not hit:
            self.stage_streak.pop(key, None)
            return 0
        n = int(self.stage_streak.get(key, 0)) + 1
        self.stage_streak[key] = n
        return n

    def _tick_exit_delay(self, ticket: int, opposite_pressure: bool) -> int:
        t = int(ticket)
        if not opposite_pressure:
            self.exit_delay_ticks[t] = 0
            return 0
        n = int(self.exit_delay_ticks.get(t, 0)) + 1
        self.exit_delay_ticks[t] = n
        return n

    @staticmethod
    def _sigmoid(x: float) -> float:
        z = max(-60.0, min(60.0, float(x)))
        return 1.0 / (1.0 + math.exp(-z))

    @staticmethod
    def _normalize_exit_reason(reason: str) -> str:
        s = str(reason or "").strip().lower()
        if not s:
            return ""
        if "protect exit" in s:
            return "Protect Exit"
        if "lock exit" in s:
            return "Lock Exit"
        if "target" in s:
            return "Target"
        if "rsi scalp" in s:
            return "RSI Scalp"
        if "bb scalp" in s:
            return "BB Scalp"
        if "reversal" in s:
            return "Reversal"
        if "adverse stop" in s:
            return "Adverse Stop"
        if "adverse reversal" in s:
            return "Adverse Reversal"
        if "time stop" in s:
            return "Time Stop"
        return str(reason or "").strip()

    def _reason_to_stage(self, reason_norm: str) -> str:
        r = str(reason_norm or "")
        if r in {"Protect Exit", "Emergency Stop", "Adverse Stop", "Time Stop"}:
            return "protect"
        if r in {"Lock Exit", "Target", "RSI Scalp", "BB Scalp"}:
            return "lock"
        if r in {"Reversal", "Adverse Reversal"}:
            return "hold"
        return ""

    def _resolve_exec_profile(
        self,
        regime_name: str,
        adverse_risk: bool,
        profit: float,
        favorable_move_pct: float,
        spread_ratio: float,
    ) -> tuple[str, dict]:
        profile_req = str(getattr(Config, "EXIT_EXEC_PROFILE", "auto") or "auto").strip().lower()
        rn = str(regime_name or "").upper()
        if profile_req == "auto":
            spread_v = float(spread_ratio or 0.0)
            if adverse_risk or rn in {"RANGE", "LOW_LIQUIDITY"} or spread_v >= float(getattr(Config, "EXIT_EXEC_AUTO_SPREAD_CONSERVATIVE", 1.30)):
                profile = "conservative"
            elif (
                rn in {"EXPANSION", "TREND"}
                and spread_v <= float(getattr(Config, "EXIT_EXEC_AUTO_SPREAD_AGGRESSIVE_MAX", 1.05))
                and (float(profit) > 0)
                and (float(favorable_move_pct) >= float(getattr(Config, "EXIT_EXEC_AUTO_TREND_FAVORABLE_MIN", 0.0004)))
            ):
                profile = "aggressive"
            else:
                profile = "neutral"
        elif profile_req in {"conservative", "aggressive", "neutral"}:
            profile = profile_req
        else:
            profile = "neutral"

        if profile == "conservative":
            return profile, {
                "protect_mult": float(getattr(Config, "EXIT_EXEC_CONSERVATIVE_PROTECT_MULT", 0.90)),
                "lock_mult": float(getattr(Config, "EXIT_EXEC_CONSERVATIVE_LOCK_MULT", 0.92)),
                "hold_mult": float(getattr(Config, "EXIT_EXEC_CONSERVATIVE_HOLD_MULT", 1.08)),
                "confirm_mult": float(getattr(Config, "EXIT_EXEC_CONSERVATIVE_CONFIRM_MULT", 0.85)),
                "confirm_add": int(getattr(Config, "EXIT_EXEC_CONSERVATIVE_CONFIRM_ADD", -1)),
            }
        if profile == "aggressive":
            return profile, {
                "protect_mult": float(getattr(Config, "EXIT_EXEC_AGGRESSIVE_PROTECT_MULT", 1.08)),
                "lock_mult": float(getattr(Config, "EXIT_EXEC_AGGRESSIVE_LOCK_MULT", 1.06)),
                "hold_mult": float(getattr(Config, "EXIT_EXEC_AGGRESSIVE_HOLD_MULT", 0.92)),
                "confirm_mult": float(getattr(Config, "EXIT_EXEC_AGGRESSIVE_CONFIRM_MULT", 1.15)),
                "confirm_add": int(getattr(Config, "EXIT_EXEC_AGGRESSIVE_CONFIRM_ADD", 1)),
            }
        return profile, {
            "protect_mult": 1.0,
            "lock_mult": 1.0,
            "hold_mult": 1.0,
            "confirm_mult": 1.0,
            "confirm_add": 0,
        }

    def _resolve_dynamic_blend(self, profile_n: int, regime_name: str, adverse_risk: bool, symbol: str = "") -> tuple[float, float]:
        runtime = self._runtime_slot(symbol)
        mode = str(getattr(Config, "EXIT_ADAPTIVE_BLEND_MODE", "dynamic") or "dynamic").strip().lower()
        base_rule = float(getattr(Config, "EXIT_ADAPTIVE_RULE_WEIGHT", 0.55))
        base_model = float(getattr(Config, "EXIT_ADAPTIVE_MODEL_WEIGHT", 0.45))
        if mode not in {"dynamic", "auto"}:
            s = max(1e-9, base_rule + base_model)
            rule_w = base_rule / s
            model_w = base_model / s
            runtime["blend_mode"] = mode
            runtime["blend_rule_weight"] = float(rule_w)
            runtime["blend_model_weight"] = float(model_w)
            history = list(runtime.get("blend_history", []))
            history.append(
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "mode": str(mode),
                    "rule_weight": round(float(rule_w), 4),
                    "model_weight": round(float(model_w), 4),
                    "profile_n": int(profile_n),
                    "regime": str(regime_name or "").upper(),
                    "adverse_risk": bool(adverse_risk),
                }
            )
            runtime["blend_history"] = history[-30:]
            if str(symbol or "").upper().strip() in {"", "GLOBAL"}:
                self._exit_runtime = runtime
            return rule_w, model_w

        min_rule = float(getattr(Config, "EXIT_ADAPTIVE_DYNAMIC_MIN_RULE_WEIGHT", 0.35))
        max_rule = float(getattr(Config, "EXIT_ADAPTIVE_DYNAMIC_MAX_RULE_WEIGHT", 0.75))
        target_n = max(1, int(getattr(Config, "EXIT_ADAPTIVE_DYNAMIC_TARGET_SAMPLES", 180)))
        progress = self._clamp(float(profile_n) / float(target_n), 0.0, 1.0)
        target_rule = float(max_rule - ((max_rule - min_rule) * progress))
        rn = str(regime_name or "").upper()
        if adverse_risk or rn in {"RANGE", "LOW_LIQUIDITY"}:
            target_rule += 0.08
        elif rn in {"EXPANSION", "TREND"} and progress >= 0.65:
            target_rule -= 0.05
        target_rule = self._clamp(target_rule, min_rule, max_rule)
        target_model = 1.0 - target_rule

        prev_rule = float(runtime.get("blend_rule_weight", base_rule))
        prev_model = float(runtime.get("blend_model_weight", base_model))
        alpha = self._clamp(float(getattr(Config, "EXIT_ADAPTIVE_DYNAMIC_EMA_ALPHA", 0.25)), 0.05, 1.0)
        rule_w = ((1.0 - alpha) * prev_rule) + (alpha * target_rule)
        model_w = ((1.0 - alpha) * prev_model) + (alpha * target_model)
        s = max(1e-9, rule_w + model_w)
        rule_w /= s
        model_w /= s

        runtime["blend_mode"] = "dynamic"
        runtime["blend_rule_weight"] = float(rule_w)
        runtime["blend_model_weight"] = float(model_w)
        history = list(runtime.get("blend_history", []))
        history.append(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "mode": "dynamic",
                "rule_weight": round(float(rule_w), 4),
                "model_weight": round(float(model_w), 4),
                "profile_n": int(profile_n),
                "regime": str(regime_name or "").upper(),
                "adverse_risk": bool(adverse_risk),
            }
        )
        runtime["blend_history"] = history[-30:]
        if str(symbol or "").upper().strip() in {"", "GLOBAL"}:
            self._exit_runtime = runtime
        return rule_w, model_w

    def _sanitize_exec_tuning(self, tuning: dict) -> dict:
        lo = float(getattr(Config, "EXIT_EXEC_MULT_MIN", 0.70))
        hi = float(getattr(Config, "EXIT_EXEC_MULT_MAX", 1.40))
        cadd_lo = int(getattr(Config, "EXIT_EXEC_CONFIRM_ADD_MIN", -2))
        cadd_hi = int(getattr(Config, "EXIT_EXEC_CONFIRM_ADD_MAX", 3))
        t = dict(tuning or {})
        t["protect_mult"] = self._clamp(float(t.get("protect_mult", 1.0)), lo, hi)
        t["lock_mult"] = self._clamp(float(t.get("lock_mult", 1.0)), lo, hi)
        t["hold_mult"] = self._clamp(float(t.get("hold_mult", 1.0)), lo, hi)
        t["confirm_mult"] = self._clamp(float(t.get("confirm_mult", 1.0)), lo, hi)
        t["confirm_add"] = int(max(cadd_lo, min(cadd_hi, int(t.get("confirm_add", 0)))))
        return t

    def _build_exit_stage_inputs(
        self,
        trade_ctx: dict,
        symbol: str,
        regime_name: str,
        adverse_risk: bool,
        profit: float,
        favorable_move_pct: float,
        score_gap: int,
        tf_confirm: bool,
        duration_sec: float,
        vol_ratio: float,
        spread_ratio: float,
        peak_profit: float,
    ) -> dict:
        entry_stage = str(trade_ctx.get("entry_stage", "balanced") or "balanced").strip().lower()
        if entry_stage not in {"aggressive", "balanced", "conservative"}:
            entry_stage = "balanced"
        entry_quality = self._clamp(
            float(pd.to_numeric(trade_ctx.get("entry_quality", 0.0), errors="coerce") or 0.0), 0.0, 1.0
        )
        entry_model_conf = self._clamp(
            float(pd.to_numeric(trade_ctx.get("entry_model_confidence", 0.0), errors="coerce") or 0.0), 0.0, 1.0
        )
        regime_at_entry = str(trade_ctx.get("regime_at_entry", trade_ctx.get("regime_name", "")) or "").strip().upper()
        latest_signal = {}
        try:
            latest_signal = dict(((getattr(self.runtime, "latest_signal_by_symbol", {}) or {}).get(symbol, {})) or {})
        except Exception:
            latest_signal = {}
        state_vector_v2 = latest_signal.get("state_vector_v2", latest_signal.get("state_vector_effective_v1", {}))
        state_execution_bridge = latest_signal.get("state_execution_bridge_v1", {})
        belief_state_v1 = latest_signal.get("belief_state_v1", latest_signal.get("belief_state_effective_v1", {}))
        return {
            "symbol": str(symbol or "").upper().strip(),
            "entry_stage": entry_stage,
            "entry_quality": round(entry_quality, 4),
            "entry_model_confidence": round(entry_model_conf, 4),
            "regime_at_entry": regime_at_entry,
            "regime_now": str(regime_name or "").upper(),
            "adverse_risk": bool(adverse_risk),
            "profit": float(profit),
            "favorable_move_pct": float(favorable_move_pct),
            "score_gap": int(score_gap),
            "tf_confirm": bool(tf_confirm),
            "duration_sec": float(duration_sec),
            "vol_ratio": float(vol_ratio),
            "spread_ratio": float(spread_ratio),
            "peak_profit": float(peak_profit),
            "current_box_state": str(latest_signal.get("box_state", trade_ctx.get("box_state", "UNKNOWN")) or "UNKNOWN").upper(),
            "current_bb_state": str(latest_signal.get("bb_state", trade_ctx.get("bb_state", "UNKNOWN")) or "UNKNOWN").upper(),
            "current_market_mode": str(latest_signal.get("market_mode", regime_name) or regime_name).upper(),
            "current_direction_policy": str(latest_signal.get("direction_policy", trade_ctx.get("entry_direction", "")) or ""),
            "entry_direction": str(trade_ctx.get("direction", trade_ctx.get("entry_direction", "")) or "").upper(),
            "state_vector_v2": dict(state_vector_v2 or {}) if isinstance(state_vector_v2, dict) else {},
            "state_execution_bridge_v1": dict(state_execution_bridge or {}) if isinstance(state_execution_bridge, dict) else {},
            "belief_state_v1": dict(belief_state_v1 or {}) if isinstance(belief_state_v1, dict) else {},
        }

    def _build_stage_execution_plan(self, chosen_stage: str, confirm_needed: int, adverse_risk: bool) -> dict:
        return self._stage_router.build_stage_execution_plan(chosen_stage, confirm_needed, adverse_risk)

    def _reset_position_runtime_state(self, ticket_i: int) -> None:
        self.reversal_streak.pop(ticket_i, None)
        self.partial_done.pop(ticket_i, None)
        self.be_moved.pop(ticket_i, None)
        self.peak_profit.pop(ticket_i, None)
        self.exit_delay_ticks.pop(ticket_i, None)
        self.shock_tick_state.pop(ticket_i, None)
        self.adverse_wait_state.pop(ticket_i, None)

    def _should_delay_adverse_exit(
        self,
        ticket_i: int,
        profit: float,
        hold_strong: bool,
        tf_confirm: bool,
        score_gap: int,
        extreme_adverse: bool,
    ) -> tuple[bool, str]:
        if not bool(getattr(Config, "ADVERSE_WAIT_FOR_BETTER_EXIT_ENABLED", True)):
            self.adverse_wait_state.pop(ticket_i, None)
            return False, ""
        if extreme_adverse:
            self.adverse_wait_state.pop(ticket_i, None)
            return False, "adverse_wait=extreme"
        if bool(getattr(Config, "ADVERSE_WAIT_DISABLE_ON_GIVEBACK", True)):
            peak = float(self.peak_profit.get(ticket_i, profit))
            giveback = max(0.0, float(peak - float(profit)))
            min_peak = abs(float(getattr(Config, "ADVERSE_WAIT_GIVEBACK_MIN_PEAK_USD", 0.25)))
            min_giveback = abs(float(getattr(Config, "ADVERSE_WAIT_GIVEBACK_MIN_USD", 0.20)))
            floor = abs(float(getattr(Config, "ADVERSE_WAIT_GIVEBACK_PROFIT_FLOOR_USD", 0.05)))
            if float(peak) >= min_peak and giveback >= min_giveback and float(profit) <= floor:
                self.adverse_wait_state.pop(ticket_i, None)
                return False, f"adverse_wait=giveback_skip({giveback:.2f})"
        if float(profit) >= 0.0:
            self.adverse_wait_state.pop(ticket_i, None)
            return False, ""

        min_loss = abs(float(getattr(Config, "ADVERSE_WAIT_MIN_LOSS_USD", 0.8)))
        if abs(float(profit)) < min_loss:
            self.adverse_wait_state.pop(ticket_i, None)
            return False, ""

        no_turn_gap = int(getattr(Config, "ADVERSE_WAIT_NO_TURN_SCORE_GAP", 35))
        no_turn_sign = (not bool(hold_strong)) and (bool(tf_confirm) or int(score_gap) >= no_turn_gap)
        if not no_turn_sign:
            self.adverse_wait_state.pop(ticket_i, None)
            return False, ""

        now_s = time.time()
        state = self.adverse_wait_state.get(ticket_i)
        if not isinstance(state, dict):
            state = {"started_at": now_s, "worst_profit": float(profit)}
        state["worst_profit"] = min(float(state.get("worst_profit", profit)), float(profit))
        state["updated_at"] = now_s
        self.adverse_wait_state[ticket_i] = state

        min_wait_s = max(0.0, float(getattr(Config, "ADVERSE_WAIT_MIN_SECONDS", 10.0)))
        max_wait_s = max(min_wait_s, float(getattr(Config, "ADVERSE_WAIT_MAX_SECONDS", 120.0)))
        recovery_need = abs(float(getattr(Config, "ADVERSE_WAIT_RECOVERY_USD", 0.35)))
        waited_s = max(0.0, now_s - float(state.get("started_at", now_s)))
        worst_profit = float(state.get("worst_profit", profit))
        recovery = float(profit) - float(worst_profit)

        if waited_s < min_wait_s:
            return True, f"adverse_wait=warmup({waited_s:.0f}s/{min_wait_s:.0f}s)"
        if recovery >= recovery_need:
            return False, f"adverse_wait=recovery({recovery:.2f}/{recovery_need:.2f})"
        if waited_s >= max_wait_s:
            return False, f"adverse_wait=timeout({waited_s:.0f}s)"
        return True, f"adverse_wait=holding({recovery:.2f}/{recovery_need:.2f})"

    def _is_plus_to_minus_guard_hit(
        self,
        ticket_i: int,
        profit: float,
        favorable_move_pct: float,
        duration_sec: float,
    ) -> bool:
        peak = float(self.peak_profit.get(ticket_i, profit))
        peak_min = float(getattr(Config, "PLUS_TO_MINUS_PEAK_PROFIT_USD", 1.0))
        floor = float(getattr(Config, "PLUS_TO_MINUS_PROFIT_FLOOR_USD", 0.0))
        min_retrace = float(getattr(Config, "PLUS_TO_MINUS_MIN_RETRACE_USD", 0.6))
        min_hold = float(getattr(Config, "PLUS_TO_MINUS_MIN_HOLD_SECONDS", 20.0))
        if float(duration_sec) < float(min_hold):
            return False
        retrace = max(0.0, float(peak - profit))
        return bool(
            float(peak) >= float(peak_min)
            and float(profit) <= float(floor)
            and float(retrace) >= float(min_retrace)
        )

    def _is_profit_giveback_guard_hit(
        self,
        ticket_i: int,
        profit: float,
        duration_sec: float,
        min_net_guard: float,
    ) -> bool:
        peak = float(self.peak_profit.get(ticket_i, profit))
        peak_min = float(getattr(Config, "PROFIT_GIVEBACK_MIN_PEAK_USD", 1.2))
        retrace_need = float(getattr(Config, "PROFIT_GIVEBACK_RETRACE_USD", 0.7))
        min_hold = float(getattr(Config, "PLUS_TO_MINUS_MIN_HOLD_SECONDS", 20.0))
        if float(duration_sec) < float(min_hold):
            return False
        retrace = max(0.0, float(peak - profit))
        return bool(
            float(peak) >= float(peak_min)
            and float(profit) >= float(min_net_guard)
            and float(retrace) >= float(retrace_need)
        )

    def _try_execute_hard_risk_guards(
        self,
        pos,
        symbol: str,
        ticket_i: int,
        profit: float,
        adverse_risk: bool,
        duration_sec: float,
        favorable_move_pct: float,
        dynamic_move_pct: float,
        dynamic_loss_usd: float,
        tf_confirm: bool,
        hold_strong: bool,
        protect_score: int,
        protect_threshold: int,
        lock_score: int,
        lock_threshold: int,
        min_target_profit: float,
        min_net_guard: float,
        exit_signal_score: int,
        exit_detail: str,
        reverse_signal_threshold: int,
        score_gap: int,
        opposite_score: float,
        result: dict,
    ) -> tuple[bool, str | None, float, list]:
        return self._risk_guard.try_execute_hard_risk_guards(
            pos=pos,
            symbol=symbol,
            ticket_i=ticket_i,
            profit=profit,
            adverse_risk=adverse_risk,
            duration_sec=duration_sec,
            favorable_move_pct=favorable_move_pct,
            dynamic_loss_usd=dynamic_loss_usd,
            tf_confirm=tf_confirm,
            hold_strong=hold_strong,
            protect_score=protect_score,
            protect_threshold=protect_threshold,
            lock_score=lock_score,
            lock_threshold=lock_threshold,
            min_target_profit=min_target_profit,
            min_net_guard=min_net_guard,
            exit_signal_score=exit_signal_score,
            exit_detail=exit_detail,
            reverse_signal_threshold=reverse_signal_threshold,
            score_gap=score_gap,
            opposite_score=opposite_score,
            result=result,
        )

    def _refresh_adaptive_exit_profile_if_needed(self) -> None:
        self._adaptive_exit_profile = refresh_exit_profile(
            current_profile=self._adaptive_exit_profile,
            trade_logger=self.trade_logger,
            normalize_exit_reason=self._normalize_exit_reason,
            reason_to_stage=self._reason_to_stage,
        )

    def _choose_exit_stage(
        self,
        protect_score: int,
        lock_score: int,
        hold_score: int,
        protect_threshold: int,
        lock_threshold: int,
        hold_threshold: int,
        profit: float,
        adverse_risk: bool,
        favorable_move_pct: float,
        score_gap: int,
        regime_name: str,
        stage_inputs: dict | None = None,
    ) -> tuple[str, dict]:
        p_protect_rule = self._sigmoid((float(protect_score) - float(protect_threshold)) / 18.0)
        p_lock_rule = self._sigmoid((float(lock_score) - float(lock_threshold)) / 18.0)
        p_hold_rule = self._sigmoid((float(hold_score) - float(hold_threshold)) / 18.0)

        self._refresh_adaptive_exit_profile_if_needed()
        prof = self._adaptive_exit_profile
        q = prof.get("stage_quality", {})
        wr = prof.get("stage_wr", {})
        exp = prof.get("stage_exp", {})

        rule_w, model_w = self._resolve_dynamic_blend(
            profile_n=int(prof.get("n", 0) or 0),
            regime_name=str(regime_name or ""),
            adverse_risk=bool(adverse_risk),
            symbol=str((stage_inputs or {}).get("symbol", "") or ""),
        )

        p_protect_model = max(0.05, min(0.95, float(wr.get("protect", 0.50)) + (0.18 * float(q.get("protect", 0.0)))))
        p_lock_model = max(0.05, min(0.95, float(wr.get("lock", 0.50)) + (0.18 * float(q.get("lock", 0.0)))))
        p_hold_model = max(0.05, min(0.95, float(wr.get("hold", 0.50)) + (0.18 * float(q.get("hold", 0.0)))))

        p_protect = (rule_w * p_protect_rule) + (model_w * p_protect_model) + float(
            getattr(Config, "EXIT_ADAPTIVE_PROTECT_BIAS", 0.10)
        )
        p_lock = (rule_w * p_lock_rule) + (model_w * p_lock_model) + float(
            getattr(Config, "EXIT_ADAPTIVE_LOCK_BIAS", 0.05)
        )
        p_hold = (rule_w * p_hold_rule) + (model_w * p_hold_model) + float(
            getattr(Config, "EXIT_ADAPTIVE_HOLD_BIAS", 0.00)
        )

        if adverse_risk:
            p_protect += 0.25
            p_hold -= 0.12
        if profit > 0:
            p_lock += min(0.22, (float(profit) / 10.0))
        if float(favorable_move_pct) > 0.0:
            p_hold += min(0.15, float(favorable_move_pct) * 800.0)
            p_lock += min(0.15, float(favorable_move_pct) * 600.0)
        if int(score_gap) > 0:
            p_protect += min(0.15, int(score_gap) / 220.0)
            p_hold -= min(0.10, int(score_gap) / 260.0)
        rn = str(regime_name or "").upper()
        reason_codes = []
        if rn in {"RANGE", "LOW_LIQUIDITY"}:
            p_protect += float(getattr(Config, "EXIT_ADAPTIVE_RANGE_PROTECT_BIAS", 0.05))
            p_lock += float(getattr(Config, "EXIT_ADAPTIVE_RANGE_LOCK_BIAS", 0.04))
            p_hold += float(getattr(Config, "EXIT_ADAPTIVE_RANGE_HOLD_BIAS", -0.06))
        elif rn in {"EXPANSION", "TREND"}:
            p_protect += float(getattr(Config, "EXIT_ADAPTIVE_TREND_PROTECT_BIAS", -0.02))
            p_lock += float(getattr(Config, "EXIT_ADAPTIVE_TREND_LOCK_BIAS", 0.02))
            p_hold += float(getattr(Config, "EXIT_ADAPTIVE_TREND_HOLD_BIAS", 0.06))
        else:
            reason_codes.append("regime_unknown_neutral")
            rn = "UNKNOWN"
        if adverse_risk:
            reason_codes.append("adverse_risk")
        if float(profit) > 0:
            reason_codes.append("in_profit")
        if float(favorable_move_pct) > 0:
            reason_codes.append("favorable_move")
        if int(score_gap) > 0:
            reason_codes.append("opposite_score_gap")
        if rn:
            reason_codes.append(f"regime_{rn.lower()}")

        # Entry meta is auxiliary only: bounded small bias, never dominant.
        pre_meta = {"protect": float(p_protect), "lock": float(p_lock), "hold": float(p_hold)}
        if bool(getattr(Config, "EXIT_STAGE_ENTRY_META_ENABLED", True)) and isinstance(stage_inputs, dict):
            entry_stage = str(stage_inputs.get("entry_stage", "balanced") or "balanced").strip().lower()
            entry_quality = self._clamp(float(stage_inputs.get("entry_quality", 0.0) or 0.0), 0.0, 1.0)
            model_conf = self._clamp(float(stage_inputs.get("entry_model_confidence", 0.0) or 0.0), 0.0, 1.0)
            meta_max = self._clamp(float(getattr(Config, "EXIT_STAGE_ENTRY_META_MAX_BIAS", 0.06)), 0.0, 0.12)
            meta_w = meta_max * ((entry_quality + model_conf) * 0.5)
            if entry_stage == "conservative":
                p_protect += (meta_w * 0.80)
                p_lock += (meta_w * 0.35)
                p_hold -= (meta_w * 0.60)
                reason_codes.append("entry_meta_conservative")
            elif entry_stage == "aggressive":
                p_hold += (meta_w * 0.75)
                p_lock += (meta_w * 0.20)
                p_protect -= (meta_w * 0.50)
                reason_codes.append("entry_meta_aggressive")
            else:
                p_lock += (meta_w * 0.20)
                reason_codes.append("entry_meta_balanced")
        elif not bool(getattr(Config, "EXIT_STAGE_ENTRY_META_ENABLED", True)):
            reason_codes.append("entry_meta_disabled")
        else:
            reason_codes.append("entry_meta_missing")
        meta_delta_cap = self._clamp(float(getattr(Config, "EXIT_STAGE_ENTRY_META_MAX_DELTA", 0.08)), 0.01, 0.20)
        for key, pre_v in pre_meta.items():
            cur_v = float({"protect": p_protect, "lock": p_lock, "hold": p_hold}[key])
            delta = cur_v - float(pre_v)
            if abs(delta) > float(meta_delta_cap):
                self._bump_metric("entry_meta_cap_hits")
                adj = float(pre_v) + (float(meta_delta_cap) if delta > 0 else -float(meta_delta_cap))
                if key == "protect":
                    p_protect = adj
                elif key == "lock":
                    p_lock = adj
                else:
                    p_hold = adj

        p_protect = max(0.01, min(0.99, p_protect))
        p_lock = max(0.01, min(0.99, p_lock))
        p_hold = max(0.01, min(0.99, p_hold))

        # EV proxy: combine probability with expected payoff from recent history.
        ev_protect = p_protect * (0.8 + max(0.0, -float(profit)) * 0.15 + max(0.0, float(exp.get("protect", 0.0)) * 0.02))
        ev_lock = p_lock * (0.8 + max(0.0, float(profit)) * 0.12 + max(0.0, float(exp.get("lock", 0.0)) * 0.02))
        ev_hold = p_hold * (0.8 + max(0.0, float(exp.get("hold", 0.0)) * 0.02))

        scores = {"protect": ev_protect, "lock": ev_lock, "hold": ev_hold}
        chosen = max(scores, key=scores.get)
        ordered = sorted(scores.values(), reverse=True)
        top = float(ordered[0]) if ordered else 0.0
        second = float(ordered[1]) if len(ordered) > 1 else 0.0
        confidence = self._clamp((top - second) / max(1e-9, top), 0.0, 1.0)
        reason_codes.append(f"ev_{chosen}")
        detail = {
            "chosen": chosen,
            "p": {"protect": round(p_protect, 4), "lock": round(p_lock, 4), "hold": round(p_hold, 4)},
            "ev": {"protect": round(ev_protect, 4), "lock": round(ev_lock, 4), "hold": round(ev_hold, 4)},
            "confidence": round(float(confidence), 4),
            "reason_codes": reason_codes,
            "hist_n": int(prof.get("n", 0)),
            "blend": {"rule_weight": round(float(rule_w), 4), "model_weight": round(float(model_w), 4)},
        }
        return chosen, detail

    @staticmethod
    def _tf_confirm_opposite(direction: str, df_all: dict) -> bool:
        try:
            m1 = (df_all or {}).get("1M")
            if m1 is None or len(m1) < 8 or "close" not in m1.columns:
                return False
            close = pd.to_numeric(m1["close"], errors="coerce").dropna()
            if len(close) < 8:
                return False
            fast = float(close.tail(3).mean())
            slow = float(close.tail(5).mean())
            if str(direction).upper() == "BUY":
                return fast < slow
            return fast > slow
        except Exception:
            return False

    def _build_exit_stage_scores(
        self,
        ticket: int,
        direction: str,
        profit: float,
        favorable_move_pct: float,
        adverse_risk: bool,
        current_side_score: float,
        opposite_score: float,
        score_gap: int,
        dynamic_loss_usd: float,
        regime_name: str,
    ) -> tuple[int, int, int]:
        t = int(ticket)
        peak = float(self.peak_profit.get(t, profit))
        peak = max(peak, float(profit))
        self.peak_profit[t] = peak
        retrace = max(0.0, float(peak - profit))
        loss_norm = 0.0
        if dynamic_loss_usd > 0:
            loss_norm = abs(float(profit)) / max(0.1, float(dynamic_loss_usd))

        protect = 0.0
        if adverse_risk:
            protect += 95.0
        if profit < 0:
            protect += min(120.0, loss_norm * 55.0)
        protect += max(0.0, float(score_gap)) * 0.8

        lock = 0.0
        if peak > 0:
            lock += min(110.0, peak * 10.0)
        lock += min(120.0, retrace * 14.0)
        if favorable_move_pct >= float(Config.PARTIAL_TRIGGER_MIN_MOVE_PCT):
            lock += 35.0

        hold = 0.0
        hold += max(0.0, float(current_side_score) - float(opposite_score)) * 0.7
        hold += max(0.0, favorable_move_pct * 100000.0) * 0.05
        rn = str(regime_name or "").upper()
        if rn in {"EXPANSION", "TREND"}:
            hold += float(Config.HOLD_SCORE_TREND_BONUS)
        elif rn == "RANGE":
            hold -= float(Config.HOLD_SCORE_RANGE_PENALTY)
        return int(round(protect)), int(round(lock)), int(round(max(0.0, hold)))

    def manage_positions(
        self,
        symbol,
        tick,
        my_positions,
        result,
        df_all,
        sniper,
        loss_limit,
        buy_s,
        sell_s,
        exit_threshold,
        adverse_loss_usd,
        reverse_signal_threshold,
        exit_policy,
    ):
        return helper_manage_positions(
            self,
            symbol=symbol,
            tick=tick,
            my_positions=my_positions,
            result=result,
            df_all=df_all,
            sniper=sniper,
            loss_limit=loss_limit,
            buy_s=buy_s,
            sell_s=sell_s,
            exit_threshold=exit_threshold,
            adverse_loss_usd=adverse_loss_usd,
            reverse_signal_threshold=reverse_signal_threshold,
            exit_policy=exit_policy,
        )

