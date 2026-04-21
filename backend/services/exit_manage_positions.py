# 한글 설명: ExitService의 대형 manage_positions 루프를 분리한 모듈입니다.
"""manage_positions helper extracted from ExitService."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import sys
import time

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
from backend.services.path_leg_runtime import (
    assign_leg_id,
    extract_leg_runtime_fields,
)
from backend.services.path_checkpoint_segmenter import (
    assign_checkpoint_context,
    extract_checkpoint_fields,
)
from backend.services.path_checkpoint_context import (
    build_exit_position_state,
    record_checkpoint_context,
)
from backend.services.exit_runner_preservation_policy import (
    resolve_exit_runner_preservation_candidate_v1,
)
from backend.services.exit_surface_state_policy import (
    resolve_exit_surface_state_v1,
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

logger = logging.getLogger(__name__)


def _safe_console_print(message: str) -> None:
    text = f"\n{str(message or '')}"
    try:
        print(text)
        return
    except UnicodeEncodeError:
        pass

    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    buffer = getattr(sys.stdout, "buffer", None)
    try:
        if buffer is not None:
            buffer.write((safe_text + "\n").encode(encoding, errors="replace"))
            buffer.flush()
        else:
            sys.stdout.write(safe_text + "\n")
            sys.stdout.flush()
    except Exception:
        try:
            sys.stdout.write("\n[exit message omitted due to console encoding]\n")
            sys.stdout.flush()
        except Exception:
            return


def _ensure_exit_checkpoint_assignment(
    self,
    *,
    symbol: str,
    runtime_row: dict | None,
) -> tuple[dict[str, object], dict[str, object]]:
    latest_signal_row = dict(runtime_row or {})
    runtime = getattr(self, "runtime", None)
    path_leg_state_by_symbol = getattr(runtime, "path_leg_state_by_symbol", None)
    if not isinstance(path_leg_state_by_symbol, dict):
        path_leg_state_by_symbol = {}
        if runtime is not None:
            setattr(runtime, "path_leg_state_by_symbol", path_leg_state_by_symbol)
    leg_assignment = assign_leg_id(
        str(symbol or ""),
        latest_signal_row,
        path_leg_state_by_symbol.get(str(symbol or ""), latest_signal_row),
    )
    latest_signal_row.update(extract_leg_runtime_fields(leg_assignment))
    path_leg_state_by_symbol[str(symbol or "")] = dict(leg_assignment.get("symbol_state", {}) or {})

    path_checkpoint_state_by_symbol = getattr(runtime, "path_checkpoint_state_by_symbol", None)
    if not isinstance(path_checkpoint_state_by_symbol, dict):
        path_checkpoint_state_by_symbol = {}
        if runtime is not None:
            setattr(runtime, "path_checkpoint_state_by_symbol", path_checkpoint_state_by_symbol)
    checkpoint_assignment = assign_checkpoint_context(
        str(symbol or ""),
        latest_signal_row,
        path_checkpoint_state_by_symbol.get(str(symbol or ""), latest_signal_row),
    )
    latest_signal_row.update(extract_checkpoint_fields(checkpoint_assignment))
    checkpoint_state = dict(checkpoint_assignment.get("symbol_state", {}) or {})
    path_checkpoint_state_by_symbol[str(symbol or "")] = dict(checkpoint_state)

    runtime_rows = getattr(runtime, "latest_signal_by_symbol", None) if runtime is not None else None
    if isinstance(runtime_rows, dict):
        merged_runtime_row = dict(runtime_rows.get(str(symbol or ""), {}) or {})
        merged_runtime_row.update(latest_signal_row)
        runtime_rows[str(symbol or "")] = merged_runtime_row
        latest_signal_row = merged_runtime_row
    return latest_signal_row, checkpoint_state


def _build_exit_checkpoint_runtime_row(
    latest_signal_row: dict | None,
    *,
    symbol: str,
    direction: str,
    ticket_i: int,
    trade_ctx: dict | None,
    source: str,
    final_stage: str,
    reason: str = "",
    outcome: str = "",
) -> dict[str, object]:
    row = dict(latest_signal_row or {})
    trade_ctx_map = dict(trade_ctx or {})
    row["symbol"] = str(symbol or "")
    row["action"] = str(direction or row.get("action") or "").upper()
    row["observe_side"] = str(direction or row.get("observe_side") or "").upper()
    if not str(row.get("observe_action") or "").strip():
        row["observe_action"] = "WAIT"
    row["ticket"] = int(ticket_i or 0)
    row["outcome"] = str(outcome or row.get("outcome") or "")
    row["blocked_by"] = str(reason or final_stage or row.get("blocked_by") or "")
    row["decision_row_key"] = str(trade_ctx_map.get("decision_row_key", row.get("decision_row_key", "")) or row.get("decision_row_key", ""))
    row["runtime_snapshot_key"] = str(
        trade_ctx_map.get("runtime_snapshot_key", row.get("runtime_snapshot_key", "")) or row.get("runtime_snapshot_key", "")
    )
    row["trade_link_key"] = str(trade_ctx_map.get("trade_link_key", row.get("trade_link_key", "")) or row.get("trade_link_key", ""))
    row["exit_manage_source"] = str(source or "")
    row["exit_manage_final_stage"] = str(final_stage or "")
    row["exit_manage_reason"] = str(reason or "")
    return row


def _resolve_checkpoint_stage_family(source: str, final_stage: str) -> str:
    source_text = str(source or "").lower()
    stage_text = str(final_stage or "").lower()
    candidate = " ".join(part for part in (source_text, stage_text) if part)
    if any(token in candidate for token in ("protective", "managed_exit", "recovery")):
        return "protective"
    if "runner" in candidate:
        return "runner"
    if any(token in candidate for token in ("hold", "wait", "delay")):
        return "hold"
    return "exit_manage"


def _resolve_checkpoint_rule_family_hint(
    *,
    stage_family: str,
    outcome: str,
    profit: float,
    peak_profit: float,
    partial_done: bool,
    be_moved: bool,
) -> str:
    if partial_done or be_moved or stage_family == "runner":
        return "runner_secured_continuation"
    if float(profit or 0.0) < 0.0 and stage_family == "protective":
        return "open_loss_protective"
    if float(profit or 0.0) < 0.0:
        return "active_open_loss"
    if float(profit or 0.0) > 0.0:
        if float(peak_profit or 0.0) > float(profit or 0.0):
            return "profit_trim_bias"
        return "profit_hold_bias"
    if float(peak_profit or 0.0) > 0.0:
        return "active_flat_profit"
    return f"{str(outcome or 'active_position').lower()}_bias"


def _record_exit_manage_checkpoint(
    self,
    *,
    symbol: str,
    latest_signal_row: dict | None,
    checkpoint_state: dict | None,
    direction: str,
    ticket_i: int,
    pos,
    trade_ctx: dict | None,
    profit: float,
    peak_profit: float,
    source: str,
    final_stage: str,
    reason: str = "",
    outcome: str = "",
    csv_path: str | Path | None = None,
    detail_path: str | Path | None = None,
) -> dict[str, object]:
    partial_done = bool(getattr(self, "partial_done", {}).get(int(ticket_i or 0), False))
    be_moved = bool(getattr(self, "be_moved", {}).get(int(ticket_i or 0), False))
    stage_family = _resolve_checkpoint_stage_family(str(source or ""), str(final_stage or ""))
    runtime_row = _build_exit_checkpoint_runtime_row(
        latest_signal_row,
        symbol=str(symbol or ""),
        direction=str(direction or ""),
        ticket_i=int(ticket_i or 0),
        trade_ctx=dict(trade_ctx or {}),
        source=str(source or ""),
        final_stage=str(final_stage or ""),
        reason=str(reason or ""),
        outcome=str(outcome or ""),
    )
    runtime_row["exit_stage_family"] = stage_family
    runtime_row["checkpoint_rule_family_hint"] = _resolve_checkpoint_rule_family_hint(
        stage_family=stage_family,
        outcome=str(outcome or ""),
        profit=float(profit or 0.0),
        peak_profit=float(peak_profit or 0.0),
        partial_done=partial_done,
        be_moved=be_moved,
    )
    position_state = build_exit_position_state(
        direction=str(direction or ""),
        ticket=int(ticket_i or 0),
        current_lot=float(getattr(pos, "volume", 0.0) or 0.0),
        entry_lot=float((dict(trade_ctx or {})).get("lot", getattr(pos, "volume", 0.0)) or 0.0),
        entry_price=float(getattr(pos, "price_open", 0.0) or 0.0),
        profit=float(profit or 0.0),
        peak_profit=float(peak_profit or 0.0),
        partial_done=partial_done,
        be_moved=be_moved,
    )
    payload = record_checkpoint_context(
        runtime=getattr(self, "runtime", None),
        symbol=str(symbol or ""),
        runtime_row=runtime_row,
        symbol_state=dict(checkpoint_state or {}),
        position_state=position_state,
        source=str(source or "exit_manage"),
        csv_path=csv_path,
        detail_path=detail_path,
        refresh_analysis=False,
    )
    runtime_rows = getattr(getattr(self, "runtime", None), "latest_signal_by_symbol", None)
    updated_runtime_row = runtime_row
    if isinstance(runtime_rows, dict):
        updated_runtime_row = dict(runtime_rows.get(str(symbol or ""), runtime_row) or runtime_row)
    return {
        "payload": payload,
        "latest_signal_row": updated_runtime_row,
    }


def _resolve_hold_checkpoint_recording(
    self,
    *,
    latest_signal_row: dict | None,
    ticket_i: int,
    final_stage: str,
    reason: str,
    outcome: str,
) -> dict[str, str]:
    partial_done = bool(getattr(self, "partial_done", {}).get(int(ticket_i or 0), False))
    be_moved = bool(getattr(self, "be_moved", {}).get(int(ticket_i or 0), False))
    runtime_row = dict(latest_signal_row or {})
    decision_family = str(runtime_row.get("exit_wait_decision_family", "") or "").strip().lower()
    bridge_status = str(runtime_row.get("exit_wait_bridge_status", "") or "").strip().lower()
    state_family = str(runtime_row.get("exit_wait_state_family", "") or "").strip().lower()
    runner_observe = bool(
        partial_done
        or be_moved
        or "runner" in decision_family
        or "runner" in bridge_status
        or (be_moved and state_family in {"active_hold", "recovery_hold"})
    )
    if runner_observe:
        return {
            "source": "exit_manage_runner",
            "final_stage": f"runner_observe:{str(final_stage or '').strip() or 'hold'}",
            "reason": str(reason or "runner_observe"),
            "outcome": "runner_hold",
        }
    return {
        "source": "exit_manage_hold",
        "final_stage": str(final_stage or ""),
        "reason": str(reason or ""),
        "outcome": str(outcome or "hold"),
    }


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


def _resolve_exit_debug_loop_count(self) -> int:
    try:
        return int((((getattr(getattr(self, "runtime", None), "loop_debug_state", {}) or {}).get("loop_count", 0)) or 0))
    except Exception:
        return 0


def _emit_exit_loop_debug(
    self,
    *,
    symbol: str,
    stage: str,
    ticket: int | None = None,
    detail: str = "",
) -> None:
    runtime = getattr(self, "runtime", None)
    writer = getattr(runtime, "_write_loop_debug", None)
    if not callable(writer):
        return
    detail_parts: list[str] = []
    if ticket is not None and int(ticket) > 0:
        detail_parts.append(f"ticket={int(ticket)}")
    if str(detail or "").strip():
        detail_parts.append(str(detail or "").strip())
    try:
        writer(
            loop_count=_resolve_exit_debug_loop_count(self),
            stage=str(stage or ""),
            symbol=str(symbol or ""),
            detail=" ".join(detail_parts).strip(),
        )
    except Exception:
        pass


def _finish_exit_substage(
    self,
    *,
    symbol: str,
    stage: str,
    started_at: float,
    ticket: int | None = None,
    detail: str = "",
) -> float:
    elapsed_ms = max(0.0, (time.perf_counter() - float(started_at)) * 1000.0)
    detail_txt = str(detail or "").strip()
    if detail_txt:
        detail_txt = f"{detail_txt} elapsed_ms={elapsed_ms:.1f}"
    else:
        detail_txt = f"elapsed_ms={elapsed_ms:.1f}"
    _emit_exit_loop_debug(
        self,
        symbol=str(symbol or ""),
        stage=str(stage or ""),
        ticket=ticket,
        detail=detail_txt,
    )
    warn_ms = float(getattr(Config, "EXIT_EVAL_SUBSTAGE_WARN_MS", 1200.0) or 1200.0)
    if elapsed_ms >= warn_ms:
        logger.warning(
            "slow exit substage: symbol=%s ticket=%s stage=%s elapsed_ms=%.1f detail=%s",
            str(symbol or ""),
            int(ticket or 0),
            str(stage or ""),
            float(elapsed_ms),
            str(detail or ""),
        )
    return float(elapsed_ms)


def _record_exit_substage(
    self,
    *,
    symbol: str,
    stage: str,
    started_at: float,
    ticket: int | None = None,
    detail: str = "",
    stage_timings_ms: dict[str, float] | None = None,
    timing_key: str = "",
) -> float:
    elapsed_ms = _finish_exit_substage(
        self,
        symbol=str(symbol or ""),
        stage=str(stage or ""),
        started_at=started_at,
        ticket=ticket,
        detail=str(detail or ""),
    )
    if isinstance(stage_timings_ms, dict):
        key = str(timing_key or stage or "").strip() or str(stage or "")
        stage_timings_ms[key] = float(stage_timings_ms.get(key, 0.0) or 0.0) + float(elapsed_ms)
    return float(elapsed_ms)


def _log_exit_position_profile(
    self,
    *,
    symbol: str,
    ticket: int,
    started_at: float,
    stage_timings_ms: dict[str, float] | None,
    final_stage: str,
    detail: str = "",
) -> None:
    timings = dict(stage_timings_ms or {})
    total_ms = max(0.0, (time.perf_counter() - float(started_at)) * 1000.0)
    top_parts = []
    for key, value in sorted(timings.items(), key=lambda item: float(item[1]), reverse=True)[:5]:
        top_parts.append(f"{str(key)}={float(value):.1f}ms")
    summary = f"final={str(final_stage or '')} total_ms={float(total_ms):.1f}"
    if top_parts:
        summary = f"{summary} top={'|'.join(top_parts)}"
    if str(detail or "").strip():
        summary = f"{summary} {str(detail or '').strip()}"
    _emit_exit_loop_debug(
        self,
        symbol=str(symbol or ""),
        stage="exit_manage_position_profile",
        ticket=int(ticket or 0),
        detail=summary,
    )
    warn_ms = float(getattr(Config, "EXIT_EVAL_POSITION_WARN_MS", 2500.0) or 2500.0)
    if total_ms >= warn_ms:
        logger.warning(
            "slow exit position profile: symbol=%s ticket=%s final=%s total_ms=%.1f detail=%s",
            str(symbol or ""),
            int(ticket or 0),
            str(final_stage or ""),
            float(total_ms),
            summary,
        )


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
    _emit_exit_loop_debug(
        self,
        symbol=str(symbol or ""),
        stage="exit_manage_start",
        detail=f"pos_count={len(my_positions or [])}",
    )

    for pos in my_positions:
        profit = pos.profit + pos.swap
        direction = "BUY" if int(pos.type) == int(ORDER_TYPE_BUY) else "SELL"
        ticket_i = int(pos.ticket)
        position_started_at = time.perf_counter()
        stage_timings_ms: dict[str, float] = {}
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_position_start",
            ticket=ticket_i,
            detail=f"direction={direction} profit={float(profit):.2f}",
        )
        current_side_score = buy_s if int(pos.type) == int(ORDER_TYPE_BUY) else sell_s
        context_load_started_at = time.perf_counter()
        trade_ctx = self.trade_logger.get_trade_context(pos.ticket) or {}
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_context_loaded",
            started_at=context_load_started_at,
            ticket=ticket_i,
            detail=f"setup={str(trade_ctx.get('entry_setup_id', '') or '')} direction={direction}",
            stage_timings_ms=stage_timings_ms,
            timing_key="trade_context_load",
        )
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
        detail_started_at = time.perf_counter()
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_detail_start",
            ticket=ticket_i,
            detail=f"score_gap={int(score_gap)} opposite_score={float(opposite_score):.2f}",
        )
        exit_detail, exit_context_score = self.runtime.build_exit_detail(opposite_reasons, opposite_score, self.trade_logger, pos.ticket)
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_detail_done",
            ticket=ticket_i,
            started_at=detail_started_at,
            detail=f"exit_context_score={float(exit_context_score):.2f}",
            stage_timings_ms=stage_timings_ms,
            timing_key="detail_build",
        )
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
        snapshot_started_at = time.perf_counter()
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_snapshot_start",
            ticket=ticket_i,
            detail=f"chosen_stage={str(chosen_stage or '')} policy_stage={policy_stage}",
        )
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
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_snapshot_done",
            ticket=ticket_i,
            started_at=snapshot_started_at,
            detail=(
                f"wait_state={str(getattr(exit_wait_state, 'state', '') or '')} "
                f"hard_wait={int(1 if bool(getattr(exit_wait_state, 'hard_wait', False)) else 0)}"
            ),
            stage_timings_ms=stage_timings_ms,
            timing_key="snapshot_eval",
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
        shock_progress_started_at = time.perf_counter()
        shock_progress = self._track_shock_event_progress(
            pos=pos,
            symbol=symbol,
            direction=direction,
            profit=profit,
            shock_ctx=shock_ctx,
            policy_stage=policy_stage,
            tick=tick,
        )
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_shock_progress_done",
            ticket=ticket_i,
            started_at=shock_progress_started_at,
            detail=f"shock_keys={len(dict(shock_progress or {}))}",
            stage_timings_ms=stage_timings_ms,
            timing_key="shock_progress",
        )
        latest_signal_row = (
            (getattr(self.runtime, "latest_signal_by_symbol", {}) or {}).get(symbol, {})
        )
        if not isinstance(latest_signal_row, dict):
            latest_signal_row = {}
        latest_signal_row, checkpoint_symbol_state = _ensure_exit_checkpoint_assignment(
            self,
            symbol=str(symbol or ""),
            runtime_row=latest_signal_row,
        )
        execution_input_started_at = time.perf_counter()
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
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_exec_input_done",
            ticket=ticket_i,
            started_at=execution_input_started_at,
            detail=f"policy_stage={policy_stage}",
            stage_timings_ms=stage_timings_ms,
            timing_key="execution_input",
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
        runtime_sink_started_at = time.perf_counter()
        exit_manage_runtime_sink_v1 = build_exit_manage_runtime_sink_v1(
            exit_manage_execution_input_v1=exit_manage_execution_input_v1
        )
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_runtime_sink_built",
            ticket=ticket_i,
            started_at=runtime_sink_started_at,
            detail=f"winner={str(((exit_manage_runtime_sink_v1.get('summary', {}) or {}).get('decision_winner', '')) or '')}",
            stage_timings_ms=stage_timings_ms,
            timing_key="runtime_sink",
        )
        policy_context_started_at = time.perf_counter()
        self.trade_logger.update_exit_policy_context(
            ticket_i,
            dict(exit_manage_runtime_sink_v1.get("trade_logger_payload", {}) or {}),
        )
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_policy_context_main_done",
            ticket=ticket_i,
            started_at=policy_context_started_at,
            detail=f"payload_keys={len(dict(exit_manage_runtime_sink_v1.get('trade_logger_payload', {}) or {}))}",
            stage_timings_ms=stage_timings_ms,
            timing_key="policy_context_main",
        )
        ai_exit_live_metrics = dict(
            exit_manage_runtime_sink_v1.get("live_metrics_payload", {}) or {}
        )
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_runtime_sink_done",
            ticket=ticket_i,
            detail=(
                f"winner={str(ai_exit_live_metrics.get('decision_winner', '') or '')} "
                f"profile={str(ai_exit_live_metrics.get('exit_profile', '') or '')}"
            ),
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
        hard_guard_started_at = time.perf_counter()
        hard_guard_hit, hard_reverse_action, hard_reverse_score, hard_reverse_reasons = self._try_execute_hard_risk_guards(
            pos=pos,
            symbol=symbol,
            ticket_i=ticket_i,
            profit=profit,
            peak_profit=peak_profit,
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
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_hard_guard_done",
            ticket=ticket_i,
            started_at=hard_guard_started_at,
            detail=f"hit={int(1 if hard_guard_hit else 0)}",
            stage_timings_ms=stage_timings_ms,
            timing_key="hard_guard",
        )
        if hard_guard_hit:
            if hard_reverse_action:
                reverse_action = hard_reverse_action
                reverse_score = hard_reverse_score
                reverse_reasons = hard_reverse_reasons or []
            try:
                checkpoint_record = _record_exit_manage_checkpoint(
                    self,
                    symbol=str(symbol or ""),
                    latest_signal_row=latest_signal_row,
                    checkpoint_state=checkpoint_symbol_state,
                    direction=str(direction or ""),
                    ticket_i=int(ticket_i),
                    pos=pos,
                    trade_ctx=trade_ctx,
                    profit=float(profit),
                    peak_profit=float(peak_profit),
                    source="exit_manage_protective",
                    final_stage="hard_guard_exit",
                    reason=str(hard_reverse_action or "hard_guard_exit"),
                    outcome="full_exit_candidate",
                )
                latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
            except Exception:
                pass
            _log_exit_position_profile(
                self,
                symbol=str(symbol or ""),
                ticket=ticket_i,
                started_at=position_started_at,
                stage_timings_ms=stage_timings_ms,
                final_stage="hard_guard_exit",
            )
            continue

        recovery_plan_started_at = time.perf_counter()
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
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_recovery_plan_done",
            ticket=ticket_i,
            started_at=recovery_plan_started_at,
            detail=f"selected={int(1 if bool(recovery_plan.get('selected')) else 0)}",
            stage_timings_ms=stage_timings_ms,
            timing_key="recovery_plan",
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
            recovery_surface = resolve_exit_surface_state_v1(
                action_source="recovery",
                candidate_kind=str(recovery_plan.get("selected_candidate_kind", "") or ""),
                reason=str(recovery_plan.get("selected_reason", "") or ""),
            )
            recovery_payload = dict(recovery_result_surface.get("trade_logger_payload", {}) or {})
            if bool(recovery_surface.get("should_record")):
                recovery_payload.update(
                    {
                        "policy_scope": str(recovery_surface.get("policy_scope", "") or ""),
                        "exit_policy_stage": str(recovery_surface.get("surface_family", "") or ""),
                        "exit_wait_decision_family": str(recovery_surface.get("surface_state", "") or ""),
                        "exit_wait_bridge_status": str(recovery_surface.get("state_reason", "") or ""),
                    }
                )
            recovery_policy_started_at = time.perf_counter()
            self.trade_logger.update_exit_policy_context(
                ticket_i,
                recovery_payload,
            )
            _record_exit_substage(
                self,
                symbol=str(symbol or ""),
                stage="exit_manage_policy_context_recovery_done",
                ticket=ticket_i,
                started_at=recovery_policy_started_at,
                detail=f"payload_keys={len(recovery_payload)}",
                stage_timings_ms=stage_timings_ms,
                timing_key="policy_context_recovery",
            )
            if bool(recovery_surface.get("should_record")):
                ai_exit_live_metrics.update(
                    {
                        "exit_surface_family": str(recovery_surface.get("surface_family", "") or ""),
                        "exit_surface_state": str(recovery_surface.get("surface_state", "") or ""),
                        "exit_surface_reason": str(recovery_surface.get("state_reason", "") or ""),
                    }
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
            try:
                checkpoint_record = _record_exit_manage_checkpoint(
                    self,
                    symbol=str(symbol or ""),
                    latest_signal_row=latest_signal_row,
                    checkpoint_state=checkpoint_symbol_state,
                    direction=str(direction or ""),
                    ticket_i=int(ticket_i),
                    pos=pos,
                    trade_ctx=trade_ctx,
                    profit=float(profit),
                    peak_profit=float(peak_profit),
                    source="exit_manage_recovery",
                    final_stage="recovery_plan_exit",
                    reason=str(recovery_plan.get("selected_reason", "Recovery Exit") or "Recovery Exit"),
                    outcome="full_exit_candidate",
                )
                latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
            except Exception:
                pass
            _log_exit_position_profile(
                self,
                symbol=str(symbol or ""),
                ticket=ticket_i,
                started_at=position_started_at,
                stage_timings_ms=stage_timings_ms,
                final_stage="recovery_plan_exit",
            )
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
        partial_action_applied = False
        if bool(partial_candidate.get("should_execute")):
            partial_volume = float(partial_candidate.get("partial_volume", 0.0) or 0.0)
            if partial_volume > 0.0 and self.runtime.close_position_partial(
                pos.ticket,
                partial_volume,
                str(partial_candidate.get("close_reason", "Partial Take Profit") or "Partial Take Profit"),
            ):
                self.partial_done[ticket_i] = True
                partial_action_applied = True
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
        profit_stop_target_sl = 0.0
        profit_stop_up_applied = False
        if bool(profit_stop_up.get("should_move")):
            target_sl = float(profit_stop_up.get("target_sl", 0.0) or 0.0)
            profit_stop_target_sl = float(target_sl)
            if target_sl > 0.0 and self.runtime.move_stop_to_break_even(pos.ticket, target_sl):
                self.be_moved[ticket_i] = True
                profit_stop_up_applied = True
                self._bump_metric(str(profit_stop_up.get("reason", "profit_stop_up") or "profit_stop_up"))

        pre_exit_surface = resolve_exit_surface_state_v1(
            action_source="partial_action",
            candidate_kind="partial_then_runner_hold" if bool(partial_action_applied) else "",
            reason=str(partial_candidate.get("close_reason", "Partial Take Profit") or "Partial Take Profit"),
            partial_executed=bool(partial_action_applied),
            stop_lock_applied=bool(profit_stop_up_applied),
        )
        if bool(pre_exit_surface.get("should_record")):
            pre_exit_policy_started_at = time.perf_counter()
            self.trade_logger.update_exit_policy_context(
                ticket_i,
                {
                    "policy_scope": str(pre_exit_surface.get("policy_scope", "") or ""),
                    "exit_policy_stage": str(pre_exit_surface.get("surface_family", "") or ""),
                    "exit_wait_decision_family": str(pre_exit_surface.get("surface_state", "") or ""),
                    "exit_wait_bridge_status": str(pre_exit_surface.get("state_reason", "") or ""),
                },
            )
            _record_exit_substage(
                self,
                symbol=str(symbol or ""),
                stage="exit_manage_policy_context_pre_exit_done",
                ticket=ticket_i,
                started_at=pre_exit_policy_started_at,
                detail=f"surface={str(pre_exit_surface.get('surface_state', '') or '')}",
                stage_timings_ms=stage_timings_ms,
                timing_key="policy_context_pre_exit",
            )
            ai_exit_live_metrics.update(
                {
                    "exit_surface_family": str(pre_exit_surface.get("surface_family", "") or ""),
                    "exit_surface_state": str(pre_exit_surface.get("surface_state", "") or ""),
                    "exit_surface_reason": str(pre_exit_surface.get("state_reason", "") or ""),
                }
            )

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
            hold_recording = _resolve_hold_checkpoint_recording(
                self,
                latest_signal_row=latest_signal_row,
                ticket_i=int(ticket_i),
                final_stage="recovery_wait_hold",
                reason=str(recovery_exec.get("reason", "recovery_wait_hold") or "recovery_wait_hold"),
                outcome="hold",
            )
            try:
                checkpoint_record = _record_exit_manage_checkpoint(
                    self,
                    symbol=str(symbol or ""),
                    latest_signal_row=latest_signal_row,
                    checkpoint_state=checkpoint_symbol_state,
                    direction=str(direction or ""),
                    ticket_i=int(ticket_i),
                    pos=pos,
                    trade_ctx=trade_ctx,
                    profit=float(profit),
                    peak_profit=float(peak_profit),
                    source=str(hold_recording.get("source", "exit_manage_hold") or "exit_manage_hold"),
                    final_stage=str(hold_recording.get("final_stage", "recovery_wait_hold") or "recovery_wait_hold"),
                    reason=str(hold_recording.get("reason", "recovery_wait_hold") or "recovery_wait_hold"),
                    outcome=str(hold_recording.get("outcome", "hold") or "hold"),
                )
                latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
            except Exception:
                pass
            _log_exit_position_profile(
                self,
                symbol=str(symbol or ""),
                ticket=ticket_i,
                started_at=position_started_at,
                stage_timings_ms=stage_timings_ms,
                final_stage="recovery_wait_hold",
            )
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
                hold_recording = _resolve_hold_checkpoint_recording(
                    self,
                    latest_signal_row=latest_signal_row,
                    ticket_i=int(ticket_i),
                    final_stage="adverse_hold_delay",
                    reason="adverse_hold_delay",
                    outcome="hold",
                )
                try:
                    checkpoint_record = _record_exit_manage_checkpoint(
                        self,
                        symbol=str(symbol or ""),
                        latest_signal_row=latest_signal_row,
                        checkpoint_state=checkpoint_symbol_state,
                        direction=str(direction or ""),
                        ticket_i=int(ticket_i),
                        pos=pos,
                        trade_ctx=trade_ctx,
                        profit=float(profit),
                        peak_profit=float(peak_profit),
                        source=str(hold_recording.get("source", "exit_manage_hold") or "exit_manage_hold"),
                        final_stage=str(hold_recording.get("final_stage", "adverse_hold_delay") or "adverse_hold_delay"),
                        reason=str(hold_recording.get("reason", "adverse_hold_delay") or "adverse_hold_delay"),
                        outcome=str(hold_recording.get("outcome", "hold") or "hold"),
                    )
                    latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
                except Exception:
                    pass
                _log_exit_position_profile(
                    self,
                    symbol=str(symbol or ""),
                    ticket=ticket_i,
                    started_at=position_started_at,
                    stage_timings_ms=stage_timings_ms,
                    final_stage="adverse_hold_delay",
                )
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
                hold_recording = _resolve_hold_checkpoint_recording(
                    self,
                    latest_signal_row=latest_signal_row,
                    ticket_i=int(ticket_i),
                    final_stage="adverse_wait_delay",
                    reason=str(wait_detail or "adverse_wait_delay"),
                    outcome="hold",
                )
                try:
                    checkpoint_record = _record_exit_manage_checkpoint(
                        self,
                        symbol=str(symbol or ""),
                        latest_signal_row=latest_signal_row,
                        checkpoint_state=checkpoint_symbol_state,
                        direction=str(direction or ""),
                        ticket_i=int(ticket_i),
                        pos=pos,
                        trade_ctx=trade_ctx,
                        profit=float(profit),
                        peak_profit=float(peak_profit),
                        source=str(hold_recording.get("source", "exit_manage_hold") or "exit_manage_hold"),
                        final_stage=str(hold_recording.get("final_stage", "adverse_wait_delay") or "adverse_wait_delay"),
                        reason=str(hold_recording.get("reason", wait_detail or "adverse_wait_delay") or (wait_detail or "adverse_wait_delay")),
                        outcome=str(hold_recording.get("outcome", "hold") or "hold"),
                    )
                    latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
                except Exception:
                    pass
                _log_exit_position_profile(
                    self,
                    symbol=str(symbol or ""),
                    ticket=ticket_i,
                    started_at=position_started_at,
                    stage_timings_ms=stage_timings_ms,
                    final_stage="adverse_wait_delay",
                    detail=str(wait_detail or ""),
                )
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
        managed_plan_started_at = time.perf_counter()
        managed_exit_plan = resolve_exit_execution_plan_v1(
            phase="managed_exit",
            candidates=[
                emergency_candidate,
                protect_candidate,
                adverse_exit_candidate,
                mid_stage_candidate,
            ],
        )
        _record_exit_substage(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_managed_plan_contract_done",
            ticket=ticket_i,
            started_at=managed_plan_started_at,
            detail=f"selected={int(1 if bool(managed_exit_plan.get('selected')) else 0)}",
            stage_timings_ms=stage_timings_ms,
            timing_key="managed_plan",
        )
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_managed_plan_ready",
            ticket=ticket_i,
            detail=(
                f"selected={int(1 if bool(managed_exit_plan.get('selected')) else 0)} "
                f"kind={str(managed_exit_plan.get('selected_candidate_kind', '') or '')}"
            ),
        )
        managed_exit_result_surface = build_exit_execution_result_surface_v1(
            symbol=str(symbol or ""),
            ticket=int(ticket_i),
            execution_plan_v1=managed_exit_plan,
            execution_status="selected" if bool(managed_exit_plan.get("selected")) else "hold",
        )
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_result_surface_done",
            ticket=ticket_i,
            detail=f"selected={int(1 if bool(managed_exit_plan.get('selected')) else 0)}",
        )
        ai_exit_live_metrics.update(
            dict(managed_exit_result_surface.get("live_metrics_payload", {}) or {})
        )
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_live_metrics_done",
            ticket=ticket_i,
            detail=f"keys={len(dict(managed_exit_result_surface.get('live_metrics_payload', {}) or {}))}",
        )
        if bool(managed_exit_plan.get("selected")):
            _emit_exit_loop_debug(
                self,
                symbol=str(symbol or ""),
                stage="exit_manage_managed_plan_selected",
                ticket=ticket_i,
                detail=f"reason={str(managed_exit_plan.get('selected_reason', '') or '')}",
            )
            runner_preservation_candidate = resolve_exit_runner_preservation_candidate_v1(
                symbol=str(symbol or ""),
                pos_type=int(pos.type),
                entry_price=float(pos.price_open),
                position_volume=float(pos.volume),
                selected_candidate_kind=str(managed_exit_plan.get("selected_candidate_kind", "") or ""),
                selected_reason=str(managed_exit_plan.get("selected_reason", "") or ""),
                profit=float(profit),
                peak_profit=float(peak_profit),
                giveback_usd=float(giveback_usd),
                min_net_guard=float(min_net_guard),
                roundtrip_cost=float(roundtrip_cost),
                favorable_move_pct=float(favorable_move_pct),
                dynamic_move_pct=float(dynamic_move_pct),
                hold_score=int(hold_score),
                lock_score=int(lock_score),
                hold_threshold=int(hold_threshold),
                partial_done=bool(self.partial_done.get(ticket_i, False)),
                be_moved=bool(self.be_moved.get(ticket_i, False)),
                profit_stop_target_sl=float(profit_stop_target_sl),
            )
            if bool(runner_preservation_candidate.get("should_execute")):
                runner_action_applied = False
                runner_kind = str(runner_preservation_candidate.get("candidate_kind", "") or "")
                runner_partial = dict(runner_preservation_candidate.get("partial_candidate", {}) or {})
                if runner_kind == "partial_then_runner_hold":
                    partial_volume = float(runner_partial.get("partial_volume", 0.0) or 0.0)
                    _emit_exit_loop_debug(
                        self,
                        symbol=str(symbol or ""),
                        stage="exit_manage_runner_partial_start",
                        ticket=ticket_i,
                        detail=f"kind={runner_kind} volume={float(partial_volume):.4f}",
                    )
                    if partial_volume > 0.0 and self.runtime.close_position_partial(
                        pos.ticket,
                        partial_volume,
                        str(runner_partial.get("close_reason", "Runner Preserve Partial") or "Runner Preserve Partial"),
                        ):
                        self.partial_done[ticket_i] = True
                        runner_action_applied = True
                runner_lock_price = float(runner_preservation_candidate.get("lock_price", 0.0) or 0.0)
                _emit_exit_loop_debug(
                    self,
                    symbol=str(symbol or ""),
                    stage="exit_manage_runner_lock_start",
                    ticket=ticket_i,
                    detail=f"kind={runner_kind} lock_price={float(runner_lock_price):.5f}",
                )
                if runner_lock_price > 0.0 and self.runtime.move_stop_to_break_even(pos.ticket, runner_lock_price):
                    self.be_moved[ticket_i] = True
                    runner_action_applied = True
                if runner_action_applied or bool(self.be_moved.get(ticket_i, False)):
                    runner_surface = resolve_exit_surface_state_v1(
                        action_source="runner_preservation",
                        candidate_kind=runner_kind,
                        reason=str(runner_preservation_candidate.get("reason", "") or ""),
                        partial_executed=bool(runner_kind == "partial_then_runner_hold"),
                        stop_lock_applied=bool(runner_kind == "runner_lock_only" or self.be_moved.get(ticket_i, False)),
                    )
                    for metric_key in list(runner_preservation_candidate.get("metric_keys", []) or []):
                        self._bump_metric(str(metric_key or "exit_runner_preserve"))
                    runner_policy_started_at = time.perf_counter()
                    self.trade_logger.update_exit_policy_context(
                        ticket_i,
                        {
                            "policy_scope": str(
                                runner_surface.get("policy_scope", runner_preservation_candidate.get("policy_scope", "EXIT_RUNNER_PRESERVATION"))
                                or runner_preservation_candidate.get("policy_scope", "EXIT_RUNNER_PRESERVATION")
                            ),
                            "exit_policy_stage": str(runner_surface.get("surface_family", "continuation_hold_surface") or "continuation_hold_surface"),
                            "exit_wait_decision_family": str(runner_surface.get("surface_state", runner_kind or "runner_preserve") or (runner_kind or "runner_preserve")),
                            "exit_wait_bridge_status": str(runner_surface.get("state_reason", runner_preservation_candidate.get("reason", "runner_preservation_active")) or runner_preservation_candidate.get("reason", "runner_preservation_active")),
                        },
                    )
                    _record_exit_substage(
                        self,
                        symbol=str(symbol or ""),
                        stage="exit_manage_policy_context_runner_done",
                        ticket=ticket_i,
                        started_at=runner_policy_started_at,
                        detail=f"runner_kind={runner_kind}",
                        stage_timings_ms=stage_timings_ms,
                        timing_key="policy_context_runner",
                    )
                    ai_exit_live_metrics.update(
                        {
                            "exit_runner_preservation_selected": 1,
                            "exit_runner_preservation_kind": runner_kind,
                            "exit_runner_preservation_reason": str(runner_preservation_candidate.get("reason", "") or ""),
                            "exit_runner_preservation_detail": str(runner_preservation_candidate.get("detail", "") or ""),
                            "exit_runner_preservation_action_applied": int(1 if runner_action_applied else 0),
                            "exit_runner_preservation_lock_price": float(runner_lock_price),
                            "exit_surface_family": str(runner_surface.get("surface_family", "") or ""),
                            "exit_surface_state": str(runner_surface.get("surface_state", "") or ""),
                            "exit_surface_reason": str(runner_surface.get("state_reason", "") or ""),
                        }
                    )
                    try:
                        checkpoint_record = _record_exit_manage_checkpoint(
                            self,
                            symbol=str(symbol or ""),
                            latest_signal_row=latest_signal_row,
                            checkpoint_state=checkpoint_symbol_state,
                            direction=str(direction or ""),
                            ticket_i=int(ticket_i),
                            pos=pos,
                            trade_ctx=trade_ctx,
                            profit=float(profit),
                            peak_profit=float(peak_profit),
                            source="exit_manage_runner",
                            final_stage=f"runner_preservation:{runner_kind}",
                            reason=str(runner_preservation_candidate.get("reason", runner_kind) or runner_kind),
                            outcome="runner_hold",
                        )
                        latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
                    except Exception:
                        pass
                    _log_exit_position_profile(
                        self,
                        symbol=str(symbol or ""),
                        ticket=ticket_i,
                        started_at=position_started_at,
                        stage_timings_ms=stage_timings_ms,
                        final_stage=f"runner_preservation:{runner_kind}",
                    )
                    continue
            managed_surface = resolve_exit_surface_state_v1(
                action_source="managed_exit",
                candidate_kind=str(managed_exit_plan.get("selected_candidate_kind", "") or ""),
                reason=str(managed_exit_plan.get("selected_reason", "") or ""),
            )
            managed_payload = dict(managed_exit_result_surface.get("trade_logger_payload", {}) or {})
            if bool(managed_surface.get("should_record")):
                managed_payload.update(
                    {
                        "policy_scope": str(managed_surface.get("policy_scope", "") or ""),
                        "exit_policy_stage": str(managed_surface.get("surface_family", "") or ""),
                        "exit_wait_decision_family": str(managed_surface.get("surface_state", "") or ""),
                        "exit_wait_bridge_status": str(managed_surface.get("state_reason", "") or ""),
                    }
                )
            managed_policy_started_at = time.perf_counter()
            self.trade_logger.update_exit_policy_context(
                ticket_i,
                managed_payload,
            )
            _record_exit_substage(
                self,
                symbol=str(symbol or ""),
                stage="exit_manage_policy_context_managed_done",
                ticket=ticket_i,
                started_at=managed_policy_started_at,
                detail=f"payload_keys={len(managed_payload)}",
                stage_timings_ms=stage_timings_ms,
                timing_key="policy_context_managed",
            )
            if bool(managed_surface.get("should_record")):
                ai_exit_live_metrics.update(
                    {
                        "exit_surface_family": str(managed_surface.get("surface_family", "") or ""),
                        "exit_surface_state": str(managed_surface.get("surface_state", "") or ""),
                        "exit_surface_reason": str(managed_surface.get("state_reason", "") or ""),
                    }
                )
            _emit_exit_loop_debug(
                self,
                symbol=str(symbol or ""),
                stage="exit_manage_execute_exit_start",
                ticket=ticket_i,
                detail=(
                    f"kind={str(managed_exit_plan.get('selected_candidate_kind', '') or '')} "
                    f"reason={str(managed_exit_plan.get('selected_reason', '') or '')}"
                ),
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
            try:
                checkpoint_record = _record_exit_manage_checkpoint(
                    self,
                    symbol=str(symbol or ""),
                    latest_signal_row=latest_signal_row,
                    checkpoint_state=checkpoint_symbol_state,
                    direction=str(direction or ""),
                    ticket_i=int(ticket_i),
                    pos=pos,
                    trade_ctx=trade_ctx,
                    profit=float(profit),
                    peak_profit=float(peak_profit),
                    source="exit_manage_managed_exit",
                    final_stage=f"managed_exit:{str(managed_exit_plan.get('selected_candidate_kind', '') or '')}",
                    reason=str(managed_exit_plan.get("selected_reason", "Lock Exit") or "Lock Exit"),
                    outcome="full_exit_candidate",
                )
                latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
            except Exception:
                pass
            _log_exit_position_profile(
                self,
                symbol=str(symbol or ""),
                ticket=ticket_i,
                started_at=position_started_at,
                stage_timings_ms=stage_timings_ms,
                final_stage=f"managed_exit:{str(managed_exit_plan.get('selected_candidate_kind', '') or '')}",
            )
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
            hold_recording = _resolve_hold_checkpoint_recording(
                self,
                latest_signal_row=latest_signal_row,
                ticket_i=int(ticket_i),
                final_stage="allow_long_blocked",
                reason="allow_long_blocked",
                outcome="wait",
            )
            try:
                checkpoint_record = _record_exit_manage_checkpoint(
                    self,
                    symbol=str(symbol or ""),
                    latest_signal_row=latest_signal_row,
                    checkpoint_state=checkpoint_symbol_state,
                    direction=str(direction or ""),
                    ticket_i=int(ticket_i),
                    pos=pos,
                    trade_ctx=trade_ctx,
                    profit=float(profit),
                    peak_profit=float(peak_profit),
                    source=str(hold_recording.get("source", "exit_manage_hold") or "exit_manage_hold"),
                    final_stage=str(hold_recording.get("final_stage", "allow_long_blocked") or "allow_long_blocked"),
                    reason=str(hold_recording.get("reason", "allow_long_blocked") or "allow_long_blocked"),
                    outcome=str(hold_recording.get("outcome", "wait") or "wait"),
                )
                latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
            except Exception:
                pass
            _log_exit_position_profile(
                self,
                symbol=str(symbol or ""),
                ticket=ticket_i,
                started_at=position_started_at,
                stage_timings_ms=stage_timings_ms,
                final_stage="allow_long_blocked",
            )
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
                _emit_exit_loop_debug(
                    self,
                    symbol=str(symbol or ""),
                    stage="exit_manage_reversal_execute_start",
                    ticket=ticket_i,
                    detail=f"score_gap={int(score_gap)} streak={int(streak)}",
                )
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
        _emit_exit_loop_debug(
            self,
            symbol=str(symbol or ""),
            stage="exit_manage_position_done",
            ticket=ticket_i,
            detail="no_exit",
        )
        hold_recording = _resolve_hold_checkpoint_recording(
            self,
            latest_signal_row=latest_signal_row,
            ticket_i=int(ticket_i),
            final_stage="no_exit",
            reason="no_exit",
            outcome="hold",
        )
        try:
            checkpoint_record = _record_exit_manage_checkpoint(
                self,
                symbol=str(symbol or ""),
                latest_signal_row=latest_signal_row,
                checkpoint_state=checkpoint_symbol_state,
                direction=str(direction or ""),
                ticket_i=int(ticket_i),
                pos=pos,
                trade_ctx=trade_ctx,
                profit=float(profit),
                peak_profit=float(peak_profit),
                source=str(hold_recording.get("source", "exit_manage_hold") or "exit_manage_hold"),
                final_stage=str(hold_recording.get("final_stage", "no_exit") or "no_exit"),
                reason=str(hold_recording.get("reason", "no_exit") or "no_exit"),
                outcome=str(hold_recording.get("outcome", "hold") or "hold"),
            )
            latest_signal_row = dict(checkpoint_record.get("latest_signal_row", latest_signal_row) or latest_signal_row)
        except Exception:
            pass
        _log_exit_position_profile(
            self,
            symbol=str(symbol or ""),
            ticket=ticket_i,
            started_at=position_started_at,
            stage_timings_ms=stage_timings_ms,
            final_stage="no_exit",
        )

    return reverse_action, reverse_score, reverse_reasons
