"""Exit-domain helper engines extracted from ExitService."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable

from backend.core.config import Config
from backend.services.exit_hard_guard_action_policy import (
    resolve_exit_hard_guard_action_candidate_v1,
)

logger = logging.getLogger(__name__)


class ExitMetricsCollector:
    @staticmethod
    def bump(metrics: dict, key: str, amount: int = 1) -> None:
        if key not in metrics:
            metrics[key] = 0
        metrics[key] = int(metrics[key]) + int(amount)

    @staticmethod
    def log_if_due(metrics: dict, last_at: float) -> float:
        now_s = time.time()
        interval = max(10, int(getattr(Config, "EXIT_METRICS_LOG_SEC", 60)))
        if (now_s - float(last_at)) < interval:
            return float(last_at)
        logger.info(
            "[exit.metrics] select(protect=%s,lock=%s,hold=%s) profile(conservative=%s,neutral=%s,aggressive=%s) "
            "exits(protect=%s,lock=%s,target=%s,rsi=%s,bb=%s,reversal=%s,time=%s,emergency=%s,adverse_stop=%s,adverse_reversal=%s) "
            "adverse_recheck_hits=%s",
            int(metrics.get("stage_select_protect", 0)),
            int(metrics.get("stage_select_lock", 0)),
            int(metrics.get("stage_select_hold", 0)),
            int(metrics.get("exec_profile_conservative", 0)),
            int(metrics.get("exec_profile_neutral", 0)),
            int(metrics.get("exec_profile_aggressive", 0)),
            int(metrics.get("exit_protect", 0)),
            int(metrics.get("exit_lock", 0)),
            int(metrics.get("exit_target", 0)),
            int(metrics.get("exit_rsi_scalp", 0)),
            int(metrics.get("exit_bb_scalp", 0)),
            int(metrics.get("exit_reversal", 0)),
            int(metrics.get("exit_time_stop", 0)),
            int(metrics.get("exit_emergency_stop", 0)),
            int(metrics.get("exit_adverse_stop", 0)),
            int(metrics.get("exit_adverse_reversal", 0)),
            int(metrics.get("adverse_recheck_hits", 0)),
        )
        return float(now_s)

    @staticmethod
    def snapshot(metrics: dict, exit_runtime: dict, exit_runtime_by_symbol: dict, regime_runtime_by_symbol: dict) -> dict:
        out = {k: int(v) for k, v in metrics.items()}
        out["exit_total"] = (
            int(out.get("exit_protect", 0))
            + int(out.get("exit_lock", 0))
            + int(out.get("exit_target", 0))
            + int(out.get("exit_rsi_scalp", 0))
            + int(out.get("exit_bb_scalp", 0))
            + int(out.get("exit_reversal", 0))
            + int(out.get("exit_time_stop", 0))
            + int(out.get("exit_emergency_stop", 0))
            + int(out.get("exit_adverse_stop", 0))
            + int(out.get("exit_adverse_reversal", 0))
        )
        out["blend_mode"] = str(exit_runtime.get("blend_mode", "dynamic"))
        out["blend_rule_weight"] = round(float(exit_runtime.get("blend_rule_weight", 0.55)), 4)
        out["blend_model_weight"] = round(float(exit_runtime.get("blend_model_weight", 0.45)), 4)
        out["blend_history"] = list(exit_runtime.get("blend_history", []))
        out["symbol_blend_runtime"] = {
            str(sym): {
                "blend_mode": str(runtime.get("blend_mode", "dynamic")),
                "blend_rule_weight": round(float(runtime.get("blend_rule_weight", 0.55)), 4),
                "blend_model_weight": round(float(runtime.get("blend_model_weight", 0.45)), 4),
                "blend_history": list(runtime.get("blend_history", [])),
            }
            for sym, runtime in exit_runtime_by_symbol.items()
        }
        out["symbol_regime_runtime"] = {
            str(sym): {
                "effective": str(runtime.get("effective", "UNKNOWN")),
                "last_seen": str(runtime.get("last_seen", "UNKNOWN")),
                "seen_streak": int(runtime.get("seen_streak", 0)),
                "switch_count": int(runtime.get("switch_count", 0)),
                "switch_blocked_count": int(runtime.get("switch_blocked_count", 0)),
            }
            for sym, runtime in regime_runtime_by_symbol.items()
        }
        out["regime_switch_blocked_count"] = int(
            sum(int(v.get("switch_blocked_count", 0)) for v in regime_runtime_by_symbol.values())
        )
        out["updated_at"] = datetime.now().isoformat()
        return out


class ExitStageRouter:
    @staticmethod
    def build_stage_execution_plan(chosen_stage: str, confirm_needed: int, adverse_risk: bool) -> dict:
        selected_stage = str(chosen_stage or "auto").strip().lower()
        if selected_stage == "protect":
            policy_stage = "short"
        elif selected_stage == "lock":
            policy_stage = "mid"
        elif selected_stage == "hold":
            policy_stage = "long"
        else:
            policy_stage = "auto"
        return {
            "policy_stage": policy_stage,
            "allow_short": policy_stage in {"short", "auto"},
            "allow_mid": policy_stage in {"mid", "auto"},
            "allow_long": policy_stage in {"long", "auto"},
            "confirm_short": max(1, int(confirm_needed) - (1 if adverse_risk else 0)),
            "confirm_mid": max(1, int(confirm_needed)),
            "confirm_long": max(1, int(confirm_needed) + 1),
        }


class ExitActionExecutor:
    def __init__(self, runtime, trade_logger, bump_metric: Callable[[str, int], None], reset_state: Callable[[int], None]):
        self.runtime = runtime
        self.trade_logger = trade_logger
        self.bump_metric = bump_metric
        self.reset_state = reset_state

    def execute_exit(
        self,
        *,
        pos,
        ticket_i: int,
        reason: str,
        exit_signal_score: int,
        detail: str,
        metric_keys: list[str] | None = None,
    ) -> bool:
        self.trade_logger.register_exit_request(pos.ticket, reason, exit_signal_score, detail=detail)
        for k in (metric_keys or []):
            self.bump_metric(str(k), 1)
        closed = bool(self.runtime.close_position(pos.ticket, reason))
        self.reset_state(ticket_i)
        return closed


class ExitRiskGuard:
    def __init__(
        self,
        action_executor: ExitActionExecutor,
        bump_metric: Callable[[str, int], None],
        check_profit_giveback: Callable[[int, float, float, float], bool],
        check_plus_to_minus: Callable[[int, float, float, float], bool],
        should_delay_adverse: Callable[[int, float, bool, bool, int, bool], tuple[bool, str]],
    ):
        self.action_executor = action_executor
        self.bump_metric = bump_metric
        self.check_profit_giveback = check_profit_giveback
        self.check_plus_to_minus = check_plus_to_minus
        self.should_delay_adverse = should_delay_adverse

    def try_execute_hard_risk_guards(
        self,
        *,
        pos,
        symbol: str,
        ticket_i: int,
        profit: float,
        peak_profit: float,
        adverse_risk: bool,
        duration_sec: float,
        favorable_move_pct: float,
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
        if not bool(getattr(Config, "EXIT_HARD_GUARD_ENABLED", True)):
            return False, None, 0.0, []

        profit_giveback_hit = bool(
            self.check_profit_giveback(ticket_i, profit, duration_sec, min_net_guard)
        )
        plus_to_minus_hit = bool(
            self.check_plus_to_minus(ticket_i, profit, favorable_move_pct, duration_sec)
        )
        adverse_min_hold_seconds = float(getattr(Config, "ADVERSE_MIN_HOLD_SECONDS", 45))
        if float(peak_profit) <= float(getattr(Config, "ADVERSE_WEAK_PEAK_USD", 0.25)):
            adverse_min_hold_seconds = min(
                float(adverse_min_hold_seconds),
                float(getattr(Config, "ADVERSE_WEAK_PEAK_MIN_HOLD_SECONDS", adverse_min_hold_seconds)),
            )
        hold_for_adverse = duration_sec >= float(adverse_min_hold_seconds)
        extreme_adverse = float(profit) <= -abs(float(dynamic_loss_usd) * 1.8)
        wait_adverse = False
        wait_detail = ""
        if bool(adverse_risk) and (bool(hold_for_adverse) or bool(extreme_adverse)):
            wait_adverse, wait_detail = self.should_delay_adverse(
                ticket_i,
                profit,
                hold_strong,
                tf_confirm,
                score_gap,
                extreme_adverse,
            )

        candidate = resolve_exit_hard_guard_action_candidate_v1(
            pos_type=int(pos.type),
            profit=float(profit),
            peak_profit=float(peak_profit),
            adverse_risk=bool(adverse_risk),
            tf_confirm=bool(tf_confirm),
            hold_strong=bool(hold_strong),
            protect_now=int(protect_score) >= int(protect_threshold),
            lock_now=int(lock_score) >= int(lock_threshold),
            min_target_profit=float(min_target_profit),
            min_net_guard=float(min_net_guard),
            exit_detail=str(exit_detail),
            exit_signal_score=int(exit_signal_score),
            reverse_signal_threshold=int(reverse_signal_threshold),
            score_gap=int(score_gap),
            opposite_score=float(opposite_score),
            result=result,
            profit_giveback_hit=bool(profit_giveback_hit),
            plus_to_minus_hit=bool(plus_to_minus_hit),
            hold_for_adverse=bool(hold_for_adverse),
            extreme_adverse=bool(extreme_adverse),
            wait_adverse=bool(wait_adverse),
            wait_detail=str(wait_detail or ""),
        )
        if bool(candidate.get("defer")):
            return False, None, 0.0, []
        if not bool(candidate.get("hit")):
            return False, None, 0.0, []

        closed_ok = self.action_executor.execute_exit(
            pos=pos,
            ticket_i=ticket_i,
            reason=str(candidate.get("reason", "") or ""),
            exit_signal_score=exit_signal_score,
            detail=str(candidate.get("detail", "") or ""),
            metric_keys=list(candidate.get("metric_keys", []) or []),
        )
        for key in list(candidate.get("post_close_metric_keys", []) or []):
            if closed_ok:
                self.bump_metric(str(key), 1)
        if closed_ok and candidate.get("reverse_action"):
            return (
                True,
                str(candidate.get("reverse_action") or ""),
                float(candidate.get("reverse_score", 0.0) or 0.0),
                list(candidate.get("reverse_reasons", []) or []),
            )
        return True, None, 0.0, []
