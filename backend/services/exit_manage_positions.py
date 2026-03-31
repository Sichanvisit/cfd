# 한글 설명: ExitService의 대형 manage_positions 루프를 분리한 모듈입니다.
"""manage_positions helper extracted from ExitService."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.services.exit_execution_orchestrator import (
    resolve_exit_execution_plan_v1,
)
from backend.services.exit_execution_result_surface import (
    build_exit_execution_result_surface_v1,
)
from backend.services.exit_manage_execution_input_contract import (
    build_exit_manage_execution_input_v1,
)
from backend.services.exit_partial_action_policy import (
    resolve_exit_partial_action_candidate_v1,
)
from backend.services.exit_recovery_execution_policy import (
    resolve_exit_recovery_execution_candidate_v1,
)
from backend.services.exit_manage_runtime_sink_contract import (
    build_exit_manage_runtime_sink_v1,
)
from backend.services.exit_reverse_action_policy import (
    resolve_exit_adverse_reverse_candidate_v1,
    resolve_exit_reversal_action_candidate_v1,
)
from backend.services.exit_stage_action_policy import (
    resolve_exit_stage_action_candidate_v1,
)
from backend.services.exit_stop_up_action_policy import (
    resolve_exit_stop_up_action_candidate_v1,
)

def _resolve_profit_stop_up(
    *,
    pos_type: int,
    entry_price: float,
    current_price: float,
    profit: float,
    peak_profit: float,
    exit_profile_id: str,
    chosen_stage: str,
) -> dict:
    return resolve_exit_stop_up_action_candidate_v1(
        pos_type=int(pos_type),
        entry_price=float(entry_price),
        current_price=float(current_price),
        profit=float(profit),
        peak_profit=float(peak_profit),
        exit_profile_id=str(exit_profile_id or ""),
        chosen_stage=str(chosen_stage or ""),
    )


def _resolve_recovery_execution(
    *,
    profit: float,
    adverse_risk: bool,
    duration_sec: float,
    tf_confirm: bool,
    score_gap: int,
    exit_wait_state,
    exit_shadow: dict | None,
) -> dict:
    return resolve_exit_recovery_execution_candidate_v1(
        profit=float(profit),
        adverse_risk=bool(adverse_risk),
        duration_sec=float(duration_sec),
        tf_confirm=bool(tf_confirm),
        score_gap=int(score_gap),
        wait_state=exit_wait_state,
        wait_metadata=dict(getattr(exit_wait_state, "metadata", {}) or {}),
        exit_shadow=dict(exit_shadow or {}),
    )


def _resolve_setup_specific_exit_guard_policy(
    *,
    symbol: str,
    entry_setup_id: str,
    side: str,
) -> dict:
    symbol_u = str(symbol or "").upper().strip()
    setup_u = str(entry_setup_id or "").lower().strip()
    side_u = str(side or "").upper().strip()
    out = {
        "min_net_guard_bonus": 0.0,
        "min_target_profit_bonus": 0.0,
    }
    if symbol_u != "NAS100" or side_u != "SELL":
        return out
    if setup_u == "range_upper_reversal_sell":
        out["min_net_guard_bonus"] = 0.80
        out["min_target_profit_bonus"] = 0.90
    elif setup_u == "breakout_retest_sell":
        out["min_net_guard_bonus"] = 0.60
        out["min_target_profit_bonus"] = 0.70
    return out


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
    reverse_action = None
    reverse_score = 0
    reverse_reasons = []
    self._log_exit_metrics_if_due()

    for pos in my_positions:
        profit = pos.profit + pos.swap
        direction = "BUY" if int(pos.type) == int(ORDER_TYPE_BUY) else "SELL"
        ticket_i = int(pos.ticket)
        current_side_score = buy_s if int(pos.type) == int(ORDER_TYPE_BUY) else sell_s
        trade_ctx = self.trade_logger.get_trade_context(pos.ticket) or {}
        open_time = trade_ctx.get("open_time", "")
        open_dt = pd.to_datetime(open_time, errors="coerce")
        duration_sec = 0.0
        if pd.notna(open_dt):
            duration_sec = float(max(0.0, (datetime.now() - open_dt.to_pydatetime()).total_seconds()))
        entry_ctx_score = float(trade_ctx.get("entry_score", 0.0))
        contra_ctx_score = float(trade_ctx.get("contra_score_at_entry", 0.0))
        entry_ctx_reason = str(trade_ctx.get("entry_reason", "UNKNOWN") or "UNKNOWN")

        reversal_mult = float(exit_policy.get("score_multiplier", {}).get("Reversal", 1.0))
        scalp_profit_mult = exit_policy.get("profit_multiplier", {})
        roundtrip_cost = self._symbol_cost(symbol, live_spread_ratio=1.0)
        min_net_guard = float(Config.MIN_NET_PROFIT_USD) + float(Config.EXTRA_FEE_BUFFER_USD) + float(roundtrip_cost)
        min_profit_rsi = max(
            float(Config.MIN_SCALP_PROFIT) * float(scalp_profit_mult.get("RSI Scalp", 1.0)),
            min_net_guard,
        )
        min_profit_bb = max(
            float(Config.MIN_SCALP_PROFIT) * float(scalp_profit_mult.get("BB Scalp", 1.0)),
            min_net_guard,
        )
        min_target_profit = max(float(Config.HARD_PROFIT_TARGET), min_net_guard)
        reversal_threshold = max(80, int(exit_threshold * reversal_mult))

        regime_now = result.get("regime", {}) if isinstance(result, dict) else {}
        vol_ratio = float(regime_now.get("volatility_ratio") or trade_ctx.get("regime_volatility_ratio") or 1.0)
        spread_ratio = float(regime_now.get("spread_ratio") or trade_ctx.get("regime_spread_ratio") or 0.0)
        roundtrip_cost = self._symbol_cost(symbol, live_spread_ratio=spread_ratio if spread_ratio > 0 else 1.0)
        min_net_guard = float(Config.MIN_NET_PROFIT_USD) + float(Config.EXTRA_FEE_BUFFER_USD) + float(roundtrip_cost)
        min_profit_rsi = max(
            float(Config.MIN_SCALP_PROFIT) * float(scalp_profit_mult.get("RSI Scalp", 1.0)),
            min_net_guard,
        )
        min_profit_bb = max(
            float(Config.MIN_SCALP_PROFIT) * float(scalp_profit_mult.get("BB Scalp", 1.0)),
            min_net_guard,
        )
        min_target_profit = max(float(Config.HARD_PROFIT_TARGET), min_net_guard)
        vol_mult = self._clamp(vol_ratio, float(Config.ADVERSE_VOL_MULT_MIN), float(Config.ADVERSE_VOL_MULT_MAX))
        entry_edge = max(0.0, float(entry_ctx_score - contra_ctx_score))
        edge_norm = min(1.0, entry_edge / max(1.0, float(Config.ENTRY_THRESHOLD)))
        confidence_bonus = min(
            float(Config.ADVERSE_CONFIDENCE_BONUS_MAX),
            edge_norm * float(Config.ADVERSE_CONFIDENCE_BONUS_MAX),
        )
        spread_penalty = 1.0
        if spread_ratio > 1.0:
            spread_penalty = max(0.75, 1.0 - ((spread_ratio - 1.0) * 0.20))

        dynamic_loss_usd = float(adverse_loss_usd) * vol_mult * (1.0 + confidence_bonus) * spread_penalty
        dynamic_move_pct = float(Config.ADVERSE_MOVE_PCT) * vol_mult * (1.0 + confidence_bonus) * spread_penalty
        dynamic_loss_usd = max(0.3, float(dynamic_loss_usd))
        dynamic_move_pct = max(0.0003, float(dynamic_move_pct))
        favorable_move_pct = self._favorable_move_pct(pos, tick)
        regime_observed = str(regime_now.get("name", "") or "").upper() or "UNKNOWN"
        regime_name, regime_switch_detail = self._resolve_effective_regime(symbol, regime_observed)
        is_range_mode = regime_name == "RANGE"
        is_trend_mode = regime_name in {"EXPANSION", "TREND"}
        if is_range_mode:
            min_profit_rsi *= 0.85
            min_profit_bb *= 0.85
            min_target_profit *= 0.90
            reversal_threshold = max(80, int(reversal_threshold * 0.95))
        elif is_trend_mode:
            min_profit_rsi *= 1.20
            min_profit_bb *= 1.15
            min_target_profit *= 1.25
            reversal_threshold = max(90, int(reversal_threshold * 1.10))

        setup_exit_guard_policy = _resolve_setup_specific_exit_guard_policy(
            symbol=symbol,
            entry_setup_id=str(trade_ctx.get("entry_setup_id", "") or ""),
            side=direction,
        )
        min_net_guard += float(setup_exit_guard_policy.get("min_net_guard_bonus", 0.0) or 0.0)
        min_profit_rsi = max(min_profit_rsi, min_net_guard)
        min_profit_bb = max(min_profit_bb, min_net_guard)
        min_target_profit = max(
            min_target_profit,
            min_net_guard + float(setup_exit_guard_policy.get("min_target_profit_bonus", 0.0) or 0.0),
        )

        adverse_move = 0.0
        if int(pos.type) == int(ORDER_TYPE_BUY) and pos.price_open > 0:
            adverse_move = max(0.0, (pos.price_open - tick.bid) / pos.price_open)
        elif int(pos.type) == int(ORDER_TYPE_SELL) and pos.price_open > 0:
            adverse_move = max(0.0, (tick.ask - pos.price_open) / pos.price_open)
        adverse_risk = adverse_move >= dynamic_move_pct or profit <= -abs(dynamic_loss_usd)
        opposite_score = sell_s if int(pos.type) == int(ORDER_TYPE_BUY) else buy_s
        score_gap = int(opposite_score - current_side_score)
        opposite_reasons = result["sell"]["reasons"] if int(pos.type) == int(ORDER_TYPE_BUY) else result["buy"]["reasons"]
        exit_detail, exit_context_score = self.runtime.build_exit_detail(opposite_reasons, opposite_score, self.trade_logger, pos.ticket)
        exit_signal_score = self._build_exit_signal_score(
            opposite_score=opposite_score,
            current_side_score=current_side_score,
            exit_context_score=exit_context_score,
            adverse_risk=adverse_risk,
        )
        protect_score, lock_score, hold_score = self._build_exit_stage_scores(
            ticket=ticket_i,
            direction=direction,
            profit=profit,
            favorable_move_pct=favorable_move_pct,
            adverse_risk=adverse_risk,
            current_side_score=current_side_score,
            opposite_score=opposite_score,
            score_gap=score_gap,
            dynamic_loss_usd=dynamic_loss_usd,
            regime_name=regime_name,
        )
        tf_confirm = self._tf_confirm_opposite(direction=direction, df_all=df_all)
        peak_profit = float(self.peak_profit.get(ticket_i, profit))
        stage_inputs = self._build_exit_stage_inputs(
            trade_ctx=trade_ctx,
            symbol=symbol,
            regime_name=regime_name,
            adverse_risk=adverse_risk,
            profit=profit,
            favorable_move_pct=favorable_move_pct,
            score_gap=score_gap,
            tf_confirm=tf_confirm,
            duration_sec=duration_sec,
            vol_ratio=vol_ratio,
            spread_ratio=spread_ratio,
            peak_profit=peak_profit,
        )
        exec_profile, exec_tuning = self._resolve_exec_profile(
            regime_name=regime_name,
            adverse_risk=adverse_risk,
            profit=profit,
            favorable_move_pct=favorable_move_pct,
            spread_ratio=spread_ratio,
        )
        exec_tuning = self._sanitize_exec_tuning(exec_tuning)
        self._bump_metric(f"exec_profile_{exec_profile}")
        protect_threshold = max(1, int(round(int(Config.EXIT_PROTECT_THRESHOLD) * float(exec_tuning.get("protect_mult", 1.0)))))
        lock_threshold = max(1, int(round(int(Config.EXIT_LOCK_THRESHOLD) * float(exec_tuning.get("lock_mult", 1.0)))))
        hold_threshold = max(1, int(round(int(Config.EXIT_HOLD_THRESHOLD) * float(exec_tuning.get("hold_mult", 1.0)))))
        protect_hit = protect_score >= int(protect_threshold)
        lock_hit = lock_score >= int(lock_threshold)
        hold_strong = hold_score >= int(hold_threshold)
        exit_detail = f"{exit_detail} | exec_profile={exec_profile},regime={regime_name},thr={protect_threshold}/{lock_threshold}/{hold_threshold}"
        protect_streak = self._tick_stage_streak(ticket_i, "protect", protect_hit and tf_confirm)
        lock_streak = self._tick_stage_streak(ticket_i, "lock", lock_hit and tf_confirm)
        opposite_pressure = bool(tf_confirm and (score_gap > 0 or adverse_risk or protect_hit))
        delay_ticks = self._tick_exit_delay(ticket_i, opposite_pressure)
        giveback_usd = max(0.0, float(peak_profit - profit))
        confirm_needed = max(1, int(Config.EXIT_CONFIRM_TICKS))
        if is_range_mode:
            confirm_needed = max(confirm_needed, int(getattr(Config, "EXIT_CONFIRM_TICKS_RANGE", confirm_needed)))
        elif is_trend_mode:
            confirm_needed = max(confirm_needed, int(getattr(Config, "EXIT_CONFIRM_TICKS_EXPANSION", confirm_needed)))
        else:
            confirm_needed = max(confirm_needed, int(getattr(Config, "EXIT_CONFIRM_TICKS_NORMAL", confirm_needed)))
        if adverse_risk:
            confirm_needed = max(1, int(confirm_needed) - 1)
        confirm_needed = max(
            1,
            int(round(float(confirm_needed) * float(exec_tuning.get("confirm_mult", 1.0))) + int(exec_tuning.get("confirm_add", 0))),
        )
        stage_score = int(round((protect_score * 0.55) + (lock_score * 0.35) - (hold_score * 0.20)))
        exit_signal_score = int(max(0, round((exit_signal_score * 0.60) + (stage_score * 0.40))))
        chosen_stage = "auto"
        stage_route = {"chosen": "auto", "p": {}, "ev": {}, "hist_n": 0}
        if bool(getattr(Config, "ENABLE_ADAPTIVE_EXIT_ROUTING", True)):
            chosen_stage, stage_route = self._choose_exit_stage(
                protect_score=protect_score,
                lock_score=lock_score,
                hold_score=hold_score,
                protect_threshold=int(protect_threshold),
                lock_threshold=int(lock_threshold),
                hold_threshold=int(hold_threshold),
                profit=profit,
                adverse_risk=adverse_risk,
                favorable_move_pct=favorable_move_pct,
                score_gap=score_gap,
                regime_name=regime_name,
                stage_inputs=stage_inputs,
            )
        self._bump_metric(f"stage_select_{chosen_stage}")
        route_txt = (
            f"stage={stage_route.get('chosen','hold')},"
            f"p={stage_route.get('p',{})},ev={stage_route.get('ev',{})},n={stage_route.get('hist_n',0)},"
            f"profile={exec_profile},confirm={confirm_needed},thr={protect_threshold}/{lock_threshold}/{hold_threshold},"
            f"conf={stage_route.get('confidence', 0.0)},why={stage_route.get('reason_codes', [])}"
        )
        exec_plan = self._build_stage_execution_plan(chosen_stage=chosen_stage, confirm_needed=confirm_needed, adverse_risk=adverse_risk)
        policy_stage = str(exec_plan.get("policy_stage", "auto"))
        self._bump_metric(f"stage_exec_{policy_stage}")
        allow_short = bool(exec_plan.get("allow_short", True))
        allow_mid = bool(exec_plan.get("allow_mid", True))
        allow_long = bool(exec_plan.get("allow_long", True))
        confirm_short = int(exec_plan.get("confirm_short", confirm_needed))
        confirm_mid = int(exec_plan.get("confirm_mid", confirm_needed))
        confirm_long = int(exec_plan.get("confirm_long", confirm_needed))
        route_txt = f"{route_txt},policy={policy_stage},confirm_s/m/l={confirm_short}/{confirm_mid}/{confirm_long}"
        exit_wait_state = self._snapshot_exit_evaluation(
            symbol=symbol,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            chosen_stage=chosen_stage,
            policy_stage=policy_stage,
            exec_profile=exec_profile,
            confirm_needed=confirm_needed,
            exit_signal_score=exit_signal_score,
            score_gap=score_gap,
            adverse_risk=adverse_risk,
            tf_confirm=tf_confirm,
            detail={
                "route_txt": route_txt,
                "protect_score": protect_score,
                "lock_score": lock_score,
                "hold_score": hold_score,
                "exit_threshold": exit_threshold,
                "reverse_signal_threshold": reverse_signal_threshold,
            },
        )
        shock_ctx = self._build_shock_context(
            score_gap=score_gap,
            vol_ratio=vol_ratio,
            spread_ratio=spread_ratio if spread_ratio > 0 else 1.0,
            adverse_risk=adverse_risk,
            tf_confirm=tf_confirm,
            profit=profit,
            policy_stage=policy_stage,
        )
        shock_progress = self._track_shock_event_progress(
            pos=pos,
            symbol=symbol,
            direction=direction,
            profit=profit,
            shock_ctx=shock_ctx,
            policy_stage=policy_stage,
            tick=tick,
        )
        latest_signal_row = (
            (getattr(self.runtime, "latest_signal_by_symbol", {}) or {}).get(symbol, {})
        )
        exit_manage_execution_input_v1 = build_exit_manage_execution_input_v1(
            symbol=str(symbol or ""),
            ticket=int(ticket_i),
            direction=str(direction or ""),
            trade_ctx=trade_ctx,
            latest_signal_row=latest_signal_row,
            exit_wait_state=exit_wait_state,
            chosen_stage=str(chosen_stage or ""),
            policy_stage=str(policy_stage or ""),
            exec_profile=str(exec_profile or ""),
            protect_threshold=protect_threshold,
            lock_threshold=lock_threshold,
            hold_threshold=hold_threshold,
            confirm_needed=int(confirm_needed),
            delay_ticks=int(delay_ticks),
            stage_route=stage_route,
            regime_name=str(regime_name or ""),
            regime_observed=str(regime_observed or ""),
            regime_switch_detail=regime_switch_detail,
            peak_profit=float(peak_profit),
            giveback_usd=float(giveback_usd),
            shock_ctx=shock_ctx,
            shock_progress=shock_progress,
        )
        exit_shadow = dict(
            (
                (exit_manage_execution_input_v1.get("runtime", {}) or {}).get(
                    "exit_utility_v1",
                    {},
                )
            )
            or {}
        )
        exit_manage_runtime_sink_v1 = build_exit_manage_runtime_sink_v1(
            exit_manage_execution_input_v1=exit_manage_execution_input_v1
        )
        self.trade_logger.update_exit_policy_context(
            ticket_i,
            dict(exit_manage_runtime_sink_v1.get("trade_logger_payload", {}) or {}),
        )
        ai_exit_live_metrics = dict(
            exit_manage_runtime_sink_v1.get("live_metrics_payload", {}) or {}
        )
        recovery_exec = _resolve_recovery_execution(
            profit=float(profit),
            adverse_risk=bool(adverse_risk),
            duration_sec=float(duration_sec),
            tf_confirm=bool(tf_confirm),
            score_gap=int(score_gap),
            exit_wait_state=exit_wait_state,
            exit_shadow=exit_shadow,
        )
        hard_guard_hit, hard_reverse_action, hard_reverse_score, hard_reverse_reasons = self._try_execute_hard_risk_guards(
            pos=pos,
            symbol=symbol,
            ticket_i=ticket_i,
            profit=profit,
            adverse_risk=adverse_risk,
            duration_sec=duration_sec,
            favorable_move_pct=favorable_move_pct,
            dynamic_move_pct=dynamic_move_pct,
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
        if hard_guard_hit:
            if hard_reverse_action:
                reverse_action = hard_reverse_action
                reverse_score = hard_reverse_score
                reverse_reasons = hard_reverse_reasons or []
            continue

        recovery_plan = resolve_exit_execution_plan_v1(
            phase="recovery",
            candidates=[
                {
                    "candidate_kind": "recovery_reverse",
                    "should_execute": str(recovery_exec.get("mode", "")) == "reverse",
                    "reason": str(recovery_exec.get("close_reason", "Recovery Reverse")),
                    "detail": f"{exit_detail} | recovery_reverse score_gap={score_gap} wait={getattr(exit_wait_state, 'state', '')}",
                    "metric_keys": ["exit_reversal"],
                    "reverse_action": "SELL" if int(pos.type) == int(ORDER_TYPE_BUY) else "BUY",
                    "reverse_score": float(opposite_score),
                    "reverse_reasons": (
                        result["sell"]["reasons"]
                        if int(pos.type) == int(ORDER_TYPE_BUY)
                        else result["buy"]["reasons"]
                    ),
                },
                {
                    "candidate_kind": "recovery_exit",
                    "should_execute": str(recovery_exec.get("mode", "")) == "exit",
                    "reason": str(recovery_exec.get("close_reason", "Recovery Exit")),
                    "detail": f"{exit_detail} | {str(recovery_exec.get('reason', 'recovery_exit'))}",
                    "metric_keys": ["exit_lock"],
                },
            ],
        )
        recovery_result_surface = build_exit_execution_result_surface_v1(
            symbol=str(symbol or ""),
            ticket=int(ticket_i),
            execution_plan_v1=recovery_plan,
            execution_status="selected" if bool(recovery_plan.get("selected")) else "hold",
        )
        ai_exit_live_metrics.update(
            dict(recovery_result_surface.get("live_metrics_payload", {}) or {})
        )
        if bool(recovery_plan.get("selected")):
            self.trade_logger.update_exit_policy_context(
                ticket_i,
                dict(recovery_result_surface.get("trade_logger_payload", {}) or {}),
            )
            if self._action_executor.execute_exit(
                pos=pos,
                ticket_i=ticket_i,
                reason=str(recovery_plan.get("selected_reason", "Recovery Exit") or "Recovery Exit"),
                exit_signal_score=exit_signal_score,
                detail=str(recovery_plan.get("selected_detail", exit_detail) or exit_detail),
                metric_keys=list(recovery_plan.get("selected_metric_keys", []) or []),
            ):
                reverse_action_plan = str(recovery_plan.get("reverse_action", "") or "")
                if reverse_action_plan:
                    reverse_action = reverse_action_plan
                    reverse_score = float(recovery_plan.get("reverse_score", 0.0) or 0.0)
                    reverse_reasons = list(recovery_plan.get("reverse_reasons", []) or [])
            continue

        prefer_green_enabled = bool(getattr(Config, "EXIT_PREFER_GREEN_CLOSE_ENABLED", True))
        green_min_profit = float(getattr(Config, "EXIT_GREEN_CLOSE_MIN_PROFIT_USD", 0.03))
        green_loss_frac = self._clamp(float(getattr(Config, "EXIT_GREEN_CLOSE_LOSS_LIMIT_FRACTION", 0.75)), 0.10, 0.98)
        green_max_hold_s = max(0.0, float(getattr(Config, "EXIT_GREEN_CLOSE_MAX_HOLD_SECONDS", 3600)))
        green_hold_soft_exit = bool(
            prefer_green_enabled
            and (float(profit) < float(green_min_profit))
            and (abs(float(profit)) < (abs(float(loss_limit)) * float(green_loss_frac)))
            and (float(duration_sec) < float(green_max_hold_s))
            and (not bool(adverse_risk))
        )
        if green_hold_soft_exit:
            self._bump_metric("exit_hold_for_green")
        recovery_wait_hold = bool(
            getattr(Config, "EXIT_RECOVERY_WAIT_HOLD_ENABLED", True)
            and str(recovery_exec.get("mode", "")) == "hold"
        )
        if recovery_wait_hold:
            self._bump_metric("exit_wait_recovery_hold")

        partial_candidate = resolve_exit_partial_action_candidate_v1(
            pos_type=int(pos.type),
            entry_price=float(pos.price_open),
            position_volume=float(pos.volume),
            favorable_move_pct=float(favorable_move_pct),
            dynamic_move_pct=float(dynamic_move_pct),
            profit=float(profit),
            min_net_guard=float(min_net_guard),
            roundtrip_cost=float(roundtrip_cost),
            partial_done=bool(self.partial_done.get(ticket_i, False)),
        )
        if bool(partial_candidate.get("should_execute")):
            partial_volume = float(partial_candidate.get("partial_volume", 0.0) or 0.0)
            if partial_volume > 0.0 and self.runtime.close_position_partial(
                pos.ticket,
                partial_volume,
                str(partial_candidate.get("close_reason", "Partial Take Profit") or "Partial Take Profit"),
            ):
                self.partial_done[ticket_i] = True
                be_price = float(partial_candidate.get("be_price", 0.0) or 0.0)
                if be_price > 0.0 and self.runtime.move_stop_to_break_even(pos.ticket, be_price):
                    self.be_moved[ticket_i] = True

        current_market_price = float(tick.bid) if int(pos.type) == int(ORDER_TYPE_BUY) else float(tick.ask)
        profit_stop_up = resolve_exit_stop_up_action_candidate_v1(
            pos_type=int(pos.type),
            entry_price=float(pos.price_open),
            current_price=float(current_market_price),
            profit=float(profit),
            peak_profit=float(peak_profit),
            exit_profile_id=str(exec_profile or trade_ctx.get("exit_profile", "") or ""),
            chosen_stage=str(chosen_stage or ""),
        )
        if bool(profit_stop_up.get("should_move")):
            target_sl = float(profit_stop_up.get("target_sl", 0.0) or 0.0)
            if target_sl > 0.0 and self.runtime.move_stop_to_break_even(pos.ticket, target_sl):
                self.be_moved[ticket_i] = True
                self._bump_metric(str(profit_stop_up.get("reason", "profit_stop_up") or "profit_stop_up"))

        emergency_candidate = {
            "candidate_kind": "emergency_stop",
            "should_execute": bool(allow_short and (profit < 0 and abs(profit) >= loss_limit)),
            "reason": "Emergency Stop",
            "detail": str(exit_detail),
            "metric_keys": ["exit_emergency_stop"],
        }
        if False and allow_short and (profit < 0 and abs(profit) >= loss_limit):
            print("\n[경고] 긴급 손절 조건 충족")
            self._action_executor.execute_exit(
                pos=pos,
                ticket_i=ticket_i,
                reason="Emergency Stop",
                exit_signal_score=exit_signal_score,
                detail=exit_detail,
                metric_keys=["exit_emergency_stop"],
            )
            continue

        if recovery_wait_hold:
            continue

        adverse_exit_candidate: dict[str, object] = {}

        protect_candidate = resolve_exit_stage_action_candidate_v1(
            candidate_scope="protect",
            allow_short=bool(allow_short),
            green_hold_soft_exit=bool(green_hold_soft_exit),
            chosen_stage=str(chosen_stage or ""),
            protect_streak=int(protect_streak),
            confirm_short=int(confirm_short),
            profit=float(profit),
            min_target_profit=float(min_target_profit),
            hold_strong=bool(hold_strong),
            protect_score=int(protect_score),
            lock_score=int(lock_score),
            hold_score=int(hold_score),
            exit_detail=str(exit_detail),
            route_txt=str(route_txt),
        )
        if allow_short and Config.ENABLE_ADVERSE_STOP and adverse_risk:
            hold_for_adverse = duration_sec >= float(Config.ADVERSE_MIN_HOLD_SECONDS)
            extreme_adverse = adverse_move >= (dynamic_move_pct * 1.8) or profit <= -abs(dynamic_loss_usd * 1.8)
            if (not hold_for_adverse) and (not extreme_adverse):
                continue

            if tf_confirm and (not hold_strong):
                protect_now = protect_score >= int(protect_threshold)
                lock_now = lock_score >= int(lock_threshold)
                adverse_recheck_candidate = resolve_exit_stage_action_candidate_v1(
                    candidate_scope="adverse_recheck",
                    allow_short=bool(allow_short),
                    profit=float(profit),
                    min_target_profit=float(min_target_profit),
                    min_net_guard=float(min_net_guard),
                    hold_strong=bool(hold_strong),
                    protect_score=int(protect_score),
                    lock_score=int(lock_score),
                    hold_score=int(hold_score),
                    exit_detail=str(exit_detail),
                    protect_now=bool(protect_now),
                    lock_now=bool(lock_now),
                )
                if bool(adverse_recheck_candidate.get("should_execute")):
                    adverse_exit_candidate = dict(adverse_recheck_candidate)

            wait_adverse, wait_detail = self._should_delay_adverse_exit(
                ticket_i=ticket_i,
                profit=profit,
                hold_strong=hold_strong,
                tf_confirm=tf_confirm,
                score_gap=score_gap,
                extreme_adverse=extreme_adverse,
            )
            if wait_adverse:
                continue

            adverse_detail = str(exit_detail)
            if wait_detail:
                adverse_detail = f"{adverse_detail} | {wait_detail}"
            plus_to_minus_hint = bool(
                self._is_plus_to_minus_guard_hit(
                    ticket_i=ticket_i,
                    profit=profit,
                    favorable_move_pct=favorable_move_pct,
                    duration_sec=duration_sec,
                )
            )
            adverse_reverse_candidate = resolve_exit_adverse_reverse_candidate_v1(
                pos_type=int(pos.type),
                exit_signal_score=int(exit_signal_score),
                reverse_signal_threshold=int(reverse_signal_threshold),
                score_gap=int(score_gap),
                plus_to_minus_hint=bool(plus_to_minus_hint),
                opposite_score=float(opposite_score),
                result=result,
            )
            if False and bool(adverse_reverse_candidate.get("should_reverse")):
                if self._action_executor.execute_exit(
                    pos=pos,
                    ticket_i=ticket_i,
                    reason="Adverse Reversal",
                    exit_signal_score=exit_signal_score,
                    detail=adverse_detail,
                    metric_keys=["exit_adverse_reversal"],
                ):
                    reverse_action = str(adverse_reverse_candidate.get("reverse_action") or "")
                    reverse_score = float(adverse_reverse_candidate.get("reverse_score", 0.0) or 0.0)
                    reverse_reasons = list(adverse_reverse_candidate.get("reverse_reasons", []) or [])
                    print(f"\n[반전] 역추세 손절 후 반대방향 진입 준비 {symbol} {reverse_action} (score={reverse_score})")
            elif False:
                self._action_executor.execute_exit(
                    pos=pos,
                    ticket_i=ticket_i,
                    reason="Adverse Stop",
                    exit_signal_score=exit_signal_score,
                    detail=adverse_detail,
                    metric_keys=["exit_adverse_stop"],
                )
            pass
            if not adverse_exit_candidate:
                if bool(adverse_reverse_candidate.get("should_reverse")):
                    adverse_exit_candidate = {
                        "candidate_kind": "adverse_reverse",
                        "should_execute": True,
                        "reason": "Adverse Reversal",
                        "detail": adverse_detail,
                        "metric_keys": ["exit_adverse_reversal"],
                        "reverse_action": str(adverse_reverse_candidate.get("reverse_action") or ""),
                        "reverse_score": float(adverse_reverse_candidate.get("reverse_score", 0.0) or 0.0),
                        "reverse_reasons": list(adverse_reverse_candidate.get("reverse_reasons", []) or []),
                    }
                else:
                    adverse_exit_candidate = {
                        "candidate_kind": "adverse_stop",
                        "should_execute": True,
                        "reason": "Adverse Stop",
                        "detail": adverse_detail,
                        "metric_keys": ["exit_adverse_stop"],
                    }

        mid_stage_candidate = resolve_exit_stage_action_candidate_v1(
            candidate_scope="mid_stage",
            allow_mid=bool(allow_mid),
            green_hold_soft_exit=bool(green_hold_soft_exit),
            chosen_stage=str(chosen_stage or ""),
            lock_streak=int(lock_streak),
            confirm_mid=int(confirm_mid),
            profit=float(profit),
            min_target_profit=float(min_target_profit),
            min_net_guard=float(min_net_guard),
            hold_strong=bool(hold_strong),
            protect_score=int(protect_score),
            lock_score=int(lock_score),
            hold_score=int(hold_score),
            exit_detail=str(exit_detail),
            route_txt=str(route_txt),
            duration_sec=float(duration_sec),
            dynamic_move_pct=float(dynamic_move_pct),
            favorable_move_pct=float(favorable_move_pct),
            hard_profit_target=float(Config.HARD_PROFIT_TARGET),
            is_trend_mode=bool(is_trend_mode),
        )
        managed_exit_plan = resolve_exit_execution_plan_v1(
            phase="managed_exit",
            candidates=[
                emergency_candidate,
                protect_candidate,
                adverse_exit_candidate,
                mid_stage_candidate,
            ],
        )
        managed_exit_result_surface = build_exit_execution_result_surface_v1(
            symbol=str(symbol or ""),
            ticket=int(ticket_i),
            execution_plan_v1=managed_exit_plan,
            execution_status="selected" if bool(managed_exit_plan.get("selected")) else "hold",
        )
        ai_exit_live_metrics.update(
            dict(managed_exit_result_surface.get("live_metrics_payload", {}) or {})
        )
        if bool(managed_exit_plan.get("selected")):
            self.trade_logger.update_exit_policy_context(
                ticket_i,
                dict(managed_exit_result_surface.get("trade_logger_payload", {}) or {}),
            )
            if self._action_executor.execute_exit(
                pos=pos,
                ticket_i=ticket_i,
                reason=str(managed_exit_plan.get("selected_reason", "Lock Exit") or "Lock Exit"),
                exit_signal_score=exit_signal_score,
                detail=str(managed_exit_plan.get("selected_detail", exit_detail) or exit_detail),
                metric_keys=list(managed_exit_plan.get("selected_metric_keys", []) or []),
            ):
                reverse_action_plan = str(managed_exit_plan.get("reverse_action", "") or "")
                if reverse_action_plan:
                    reverse_action = reverse_action_plan
                    reverse_score = float(managed_exit_plan.get("reverse_score", 0.0) or 0.0)
                    reverse_reasons = list(managed_exit_plan.get("reverse_reasons", []) or [])
                    print(f"\n[reverse] {symbol} {reverse_action} (score={reverse_score})")
            continue
        if False and bool(mid_stage_candidate.get("should_execute")):
            if str(mid_stage_candidate.get("candidate_kind", "")) == "target_exit": print(f"\n[泥?궛] 紐⑺몴 ?ъ꽦: ${profit:.2f}")
            self._action_executor.execute_exit(
                pos=pos,
                ticket_i=ticket_i,
                reason=str(mid_stage_candidate.get("reason", "Lock Exit") or "Lock Exit"),
                exit_signal_score=exit_signal_score,
                detail=str(mid_stage_candidate.get("detail", exit_detail) or exit_detail),
                metric_keys=list(mid_stage_candidate.get("metric_keys", []) or []),
            )
            continue

        if allow_mid and int(pos.type) == int(ORDER_TYPE_BUY):
            if profit > min_profit_rsi and sniper["rsi"] >= Config.RSI_UPPER:
                if self.runtime.allow_ai_exit(
                    symbol, direction, open_time, duration_sec, entry_ctx_score,
                    contra_ctx_score, exit_signal_score, entry_ctx_reason, "RSI Scalp",
                    regime=regime_now,
                    trade_ctx=trade_ctx,
                    stage_inputs=stage_inputs,
                    live_metrics=ai_exit_live_metrics,
                ):
                    self._action_executor.execute_exit(
                        pos=pos,
                        ticket_i=ticket_i,
                        reason="RSI Scalp",
                        exit_signal_score=exit_signal_score,
                        detail=exit_detail,
                        metric_keys=["exit_rsi_scalp"],
                    )
                continue
            if profit > min_profit_bb and sniper["bb_up"] > 0 and tick.bid >= sniper["bb_up"]:
                if self.runtime.allow_ai_exit(
                    symbol, direction, open_time, duration_sec, entry_ctx_score,
                    contra_ctx_score, exit_signal_score, entry_ctx_reason, "BB Scalp",
                    regime=regime_now,
                    trade_ctx=trade_ctx,
                    stage_inputs=stage_inputs,
                    live_metrics=ai_exit_live_metrics,
                ):
                    self._action_executor.execute_exit(
                        pos=pos,
                        ticket_i=ticket_i,
                        reason="BB Scalp",
                        exit_signal_score=exit_signal_score,
                        detail=exit_detail,
                        metric_keys=["exit_bb_scalp"],
                    )
                continue
        elif allow_mid:
            if profit > min_profit_rsi and sniper["rsi"] <= Config.RSI_LOWER:
                if self.runtime.allow_ai_exit(
                    symbol, direction, open_time, duration_sec, entry_ctx_score,
                    contra_ctx_score, exit_signal_score, entry_ctx_reason, "RSI Scalp",
                    regime=regime_now,
                    trade_ctx=trade_ctx,
                    stage_inputs=stage_inputs,
                    live_metrics=ai_exit_live_metrics,
                ):
                    self._action_executor.execute_exit(
                        pos=pos,
                        ticket_i=ticket_i,
                        reason="RSI Scalp",
                        exit_signal_score=exit_signal_score,
                        detail=exit_detail,
                        metric_keys=["exit_rsi_scalp"],
                    )
                continue
            if profit > min_profit_bb and sniper["bb_dn"] > 0 and tick.ask <= sniper["bb_dn"]:
                if self.runtime.allow_ai_exit(
                    symbol, direction, open_time, duration_sec, entry_ctx_score,
                    contra_ctx_score, exit_signal_score, entry_ctx_reason, "BB Scalp",
                    regime=regime_now,
                    trade_ctx=trade_ctx,
                    stage_inputs=stage_inputs,
                    live_metrics=ai_exit_live_metrics,
                ):
                    self._action_executor.execute_exit(
                        pos=pos,
                        ticket_i=ticket_i,
                        reason="BB Scalp",
                        exit_signal_score=exit_signal_score,
                        detail=exit_detail,
                        metric_keys=["exit_bb_scalp"],
                    )
                continue

        if not allow_long:
            self._tick_reversal_streak(pos.ticket, False)
            continue
        hold_ok = duration_sec >= float(Config.MIN_HOLD_SECONDS_FOR_REVERSAL)
        reversal_threshold_dyn = int(round(reversal_threshold * self._clamp(vol_ratio, 0.95, 1.20)))
        reversal_profit_lock = max(min_net_guard, float(Config.REVERSAL_PROFIT_LOCK_USD) + float(roundtrip_cost))
        if hold_ok and score_gap >= int(Config.REVERSAL_MIN_SCORE_GAP) and profit >= reversal_profit_lock:
            ai_adj = self.runtime.exit_reversal_ai_adjustment(
                symbol, direction, open_time, duration_sec, entry_ctx_score,
                contra_ctx_score, exit_signal_score, entry_ctx_reason,
                regime=regime_now,
                trade_ctx=trade_ctx,
                stage_inputs=stage_inputs,
                live_metrics=ai_exit_live_metrics,
            )
            reversal_hit = (exit_signal_score + ai_adj) >= reversal_threshold_dyn
            streak = self._tick_reversal_streak(pos.ticket, reversal_hit)
            reversal_confirm_needed = max(int(confirm_long), int(Config.REVERSAL_CONFIRM_TICKS))
            reversal_candidate = resolve_exit_reversal_action_candidate_v1(
                pos_type=int(pos.type),
                reversal_hit=bool(reversal_hit),
                streak=int(streak),
                reversal_confirm_needed=int(reversal_confirm_needed),
                opposite_score=float(opposite_score),
                result=result,
            )

            if bool(reversal_candidate.get("should_execute")):
                print("\n[청산] 추세 반전 감지")
                self._action_executor.execute_exit(
                    pos=pos,
                    ticket_i=ticket_i,
                    reason="Reversal",
                    exit_signal_score=exit_signal_score,
                    detail=exit_detail,
                    metric_keys=["exit_reversal"],
                )
        else:
            self._tick_reversal_streak(pos.ticket, False)

    return reverse_action, reverse_score, reverse_reasons
