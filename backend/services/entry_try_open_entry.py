# 파일 설명: EntryService의 try_open_entry 본문을 분리한 모듈입니다.
"""try_open_entry helper extracted from EntryService."""

from __future__ import annotations

from collections.abc import Mapping
import json
import sys
import time
from datetime import datetime

import pandas as pd

from backend.core.config import Config
from backend.core.trade_constants import ORDER_TYPE_BUY, ORDER_TYPE_SELL
from backend.domain.decision_models import DecisionContext, SetupCandidate
from backend.services.consumer_contract import CONSUMER_INPUT_CONTRACT_V1
from backend.services.consumer_check_state import (
    evaluate_consumer_open_guard_v1,
    resolve_effective_consumer_check_state_v1,
)
from backend.services.entry_candidate_bridge import (
    build_entry_candidate_bridge_flat_fields,
    build_entry_candidate_bridge_v1,
)
from backend.services.exit_profile_router import resolve_exit_profile
from backend.services.belief_state25_runtime_bridge import (
    build_belief_state25_runtime_bridge_v1,
)
from backend.services.barrier_state25_runtime_bridge import (
    build_barrier_state25_runtime_bridge_v1,
)
from backend.services.breakout_event_overlay import (
    build_breakout_event_overlay_candidates_v1,
    build_breakout_event_overlay_trace_v1,
)
from backend.services.breakout_event_runtime import (
    build_breakout_event_runtime_v1,
)
from backend.services.forecast_state25_runtime_bridge import (
    build_forecast_state25_log_only_overlay_trace_v1,
    build_forecast_state25_runtime_bridge_v1,
)
from backend.services.state25_context_bridge import (
    build_state25_candidate_context_bridge_flat_fields_v1,
    build_state25_candidate_context_bridge_v1,
)
from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
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
    build_flat_position_state,
    record_checkpoint_context,
)
from backend.services.p7_guarded_size_overlay import (
    P7_GUARDED_SIZE_OVERLAY_CONTRACT_V1,
    resolve_p7_guarded_size_overlay_v1,
)
from backend.services.storage_compaction import resolve_trade_link_key
from backend.services.teacher_pattern_active_candidate_runtime import (
    build_state25_candidate_entry_log_only_trace_v1,
    resolve_state25_candidate_live_threshold_adjustment_v1,
)
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard
from ml.semantic_v1.runtime_adapter import (
    SemanticShadowRuntime,
    build_semantic_shadow_feature_row,
    resolve_semantic_shadow_compare_label,
)


def _build_trade_logger_micro_payload_from_decision_row(decision_row: dict | None) -> dict[str, object]:
    row = dict(decision_row or {})
    text_fields = (
        "micro_breakout_readiness_state",
        "micro_reversal_risk_state",
        "micro_participation_state",
        "micro_gap_context_state",
    )
    float_fields = (
        "micro_body_size_pct_20",
        "micro_doji_ratio_20",
        "micro_range_compression_ratio_20",
        "micro_volume_burst_ratio_20",
        "micro_volume_burst_decay_20",
        "micro_gap_fill_progress",
        "micro_upper_wick_ratio_20",
        "micro_lower_wick_ratio_20",
    )
    int_fields = (
        "micro_same_color_run_current",
        "micro_same_color_run_max_20",
        "micro_swing_high_retest_count_20",
        "micro_swing_low_retest_count_20",
    )

    payload: dict[str, object] = {}
    for field in text_fields:
        payload[field] = str(row.get(field, "") or "").strip()
    for field in float_fields:
        parsed = pd.to_numeric(row.get(field), errors="coerce")
        payload[field] = 0.0 if pd.isna(parsed) else float(parsed)
    for field in int_fields:
        parsed = pd.to_numeric(row.get(field), errors="coerce")
        payload[field] = 0 if pd.isna(parsed) else int(parsed)
    return payload


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
            sys.stdout.write("\n[entry message omitted due to console encoding]\n")
            sys.stdout.flush()
        except Exception:
            return


def _build_semantic_shadow_prediction_cache_key(
    *,
    symbol: str,
    runtime_snapshot_row: Mapping[str, object] | None = None,
    action_hint: str = "",
    setup_id: str = "",
    setup_side: str = "",
    entry_stage: str = "",
) -> str:
    row = dict(runtime_snapshot_row or {})
    anchor_candidates = (
        row.get("runtime_snapshot_key"),
        row.get("decision_row_key"),
        row.get("signal_bar_ts"),
        row.get("time"),
        row.get("timestamp"),
        row.get("bar_time"),
    )
    anchor = ""
    for value in anchor_candidates:
        text = str(value or "").strip()
        if text:
            anchor = text
            break
    if not anchor:
        return ""
    return "|".join(
        [
            str(symbol or "").upper().strip(),
            str(action_hint or "").upper().strip(),
            str(setup_id or "").strip().lower(),
            str(setup_side or "").upper().strip(),
            str(entry_stage or "").strip().lower(),
            anchor,
        ]
    )


def _resolve_setup_specific_pyramid_policy(
    *,
    symbol: str,
    action: str,
    setup_id: str,
    setup_reason: str = "",
    preflight_allowed_action: str = "",
    box_state: str,
    same_dir_count: int,
    pyramid_mode: str,
    require_drawdown: bool,
    edge_guard: bool,
    min_prog: float,
) -> dict:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    setup_u = str(setup_id or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()
    preflight_u = str(preflight_allowed_action or "").upper().strip()
    box_u = str(box_state or "").upper().strip()

    out = {
        "pyramid_mode": str(pyramid_mode or "adverse"),
        "require_drawdown": bool(require_drawdown),
        "edge_guard": bool(edge_guard),
        "min_prog": float(min_prog),
    }

    if (
        symbol_u in {"NAS100", "BTCUSD"}
        and setup_u == "breakout_retest_sell"
        and action_u == "SELL"
        and preflight_u in {"SELL_ONLY", "BOTH"}
        and box_u == "BELOW"
        and same_dir_count <= 2
    ):
        out["pyramid_mode"] = "progressive"
        out["require_drawdown"] = False
        out["edge_guard"] = False
        mult = 0.22 if symbol_u == "BTCUSD" else 0.40
        out["min_prog"] = float(max(0.0, float(min_prog) * mult))
        return out

    if (
        symbol_u == "BTCUSD"
        and setup_u == "range_upper_reversal_sell"
        and action_u == "SELL"
        and preflight_u in {"SELL_ONLY", "BOTH"}
        and box_u in {"UPPER", "ABOVE", "UPPER_EDGE"}
        and same_dir_count <= 2
        and setup_reason_u in {
            "shadow_upper_reject_probe_observe",
            "shadow_upper_reject_confirm",
            "shadow_upper_break_fail_confirm",
            "upper_break_fail_confirm",
        }
    ):
        out["pyramid_mode"] = "progressive"
        out["require_drawdown"] = False
        out["edge_guard"] = True
        out["min_prog"] = float(max(0.0, float(min_prog) * 0.32))
        return out

    if (
        symbol_u == "NAS100"
        and setup_u == "range_lower_reversal_buy"
        and action_u == "BUY"
        and preflight_u in {"BUY_ONLY", "BOTH"}
        and box_u in {"LOWER", "BELOW", "LOWER_EDGE"}
        and same_dir_count <= 2
        and (
            setup_reason_u in {
                "shadow_outer_band_reversal_support_required_observe",
                "shadow_lower_rebound_confirm",
            }
            or setup_reason_u.startswith("shadow_lower_rebound_probe_observe")
        )
    ):
        out["pyramid_mode"] = "progressive"
        out["require_drawdown"] = False
        out["edge_guard"] = False
        out["min_prog"] = float(max(0.0, float(min_prog) * 0.36))
        return out

    return out


def _build_entry_blocked_guard_v1(
    *,
    action: str,
    observe_reason: str,
    blocked_by: str,
    action_none_reason: str,
) -> dict:
    action_u = str(action or "").upper().strip()
    blocked_by_u = str(blocked_by or "").strip()
    action_none_u = str(action_none_reason or "").strip()
    strict_block_guards = {
        "forecast_guard",
        "outer_band_guard",
        "barrier_guard",
        "middle_sr_anchor_guard",
    }
    strict_action_none_reasons = {
        "observe_state_wait",
        "confirm_suppressed",
        "execution_soft_blocked",
    }
    guard_active = bool(
        action_u in {"BUY", "SELL"}
        and (
            blocked_by_u in strict_block_guards
            or (
                action_none_u in strict_action_none_reasons
                and blocked_by_u not in {"probe_promotion_gate"}
            )
        )
    )
    failure_code = str((blocked_by_u or action_none_u) if guard_active else "")
    return {
        "contract_version": "entry_blocked_guard_v1",
        "action": str(action_u or ""),
        "observe_reason": str(observe_reason or ""),
        "blocked_by": str(blocked_by_u or ""),
        "action_none_reason": str(action_none_u or ""),
        "guard_active": bool(guard_active),
        "allows_open": bool(not failure_code),
        "failure_code": str(failure_code or ""),
    }


def _build_probe_promotion_guard_v1(
    *,
    symbol: str,
    action: str,
    observe_reason: str,
    blocked_by: str,
    action_none_reason: str,
    entry_probe_plan_v1: dict | None = None,
    consumer_check_state_v1: dict | None = None,
    runtime_snapshot_row: dict | None = None,
) -> dict:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    observe_reason_u = str(observe_reason or "").lower().strip()
    blocked_by_u = str(blocked_by or "").lower().strip()
    action_none_u = str(action_none_reason or "").lower().strip()
    plan = dict(entry_probe_plan_v1 or {})
    consumer_state = dict(consumer_check_state_v1 or {})
    runtime_row = dict(runtime_snapshot_row or {})

    plan_active = bool(plan.get("active", False))
    plan_ready = bool(plan.get("ready_for_entry", False))
    plan_reason = str(plan.get("reason", "") or "").strip()
    probe_scene_id = str(
        plan.get("symbol_scene_relief", "")
        or consumer_state.get("probe_scene_id", "")
        or runtime_row.get("probe_scene_id", "")
        or ""
    ).strip()
    plan_side_u = str(
        plan.get("intended_action", "")
        or plan.get("candidate_side_hint", "")
        or consumer_state.get("check_side", "")
        or runtime_row.get("consumer_check_side", "")
        or action_u
        or ""
    ).upper().strip()
    consumer_stage_u = str(
        consumer_state.get("check_stage", "")
        or runtime_row.get("consumer_check_stage", "")
        or ""
    ).upper().strip()
    consumer_entry_ready = bool(
        consumer_state.get("entry_ready", runtime_row.get("consumer_check_entry_ready", False))
    )
    quick_trace_state_u = str(runtime_row.get("quick_trace_state", "") or "").upper().strip()
    quick_trace_reason = str(runtime_row.get("quick_trace_reason", "") or "").strip()
    default_side_aligned = bool(plan.get("default_side_aligned", False))
    near_confirm = bool(plan.get("near_confirm", False))

    def _plan_float(name: str, default: float = 0.0) -> float:
        try:
            parsed = pd.to_numeric(plan.get(name), errors="coerce")
            if pd.isna(parsed):
                return float(default)
            return float(parsed)
        except Exception:
            return float(default)

    probe_surface = bool(
        action_u in {"BUY", "SELL"}
        and plan_side_u in {"", action_u}
        and (
            "_probe_observe" in observe_reason_u
            or action_none_u == "probe_not_promoted"
            or consumer_stage_u == "PROBE"
            or quick_trace_state_u.startswith("PROBE")
            or plan_active
        )
    )
    probe_not_ready_surface = bool(
        not plan_ready
        and (
            action_none_u == "probe_not_promoted"
            or blocked_by_u == "probe_promotion_gate"
            or consumer_stage_u == "PROBE"
            or (
                quick_trace_state_u.startswith("PROBE")
                and quick_trace_state_u != "PROBE_READY"
            )
        )
        and not consumer_entry_ready
    )
    bounded_middle_sr_probe_relief = bool(
        probe_surface
        and probe_not_ready_surface
        and blocked_by_u == "middle_sr_anchor_guard"
        and observe_reason_u == "middle_sr_anchor_required_observe"
        and plan_active
        and action_u in {"BUY", "SELL"}
        and plan_side_u in {"", action_u}
        and default_side_aligned
        and (
            near_confirm
            or _plan_float("pair_gap") >= 0.17
        )
        and _plan_float("candidate_support") >= 0.11
        and _plan_float("action_confirm_score") >= 0.08
        and _plan_float("confirm_fake_gap") >= -0.26
        and _plan_float("wait_confirm_gap") >= -0.21
        and _plan_float("continue_fail_gap") >= -0.30
        and _plan_float("same_side_barrier", default=1.0) <= 0.60
    )
    bounded_xau_outer_band_followthrough_relief = bool(
        probe_surface
        and probe_not_ready_surface
        and symbol_u == "XAUUSD"
        and action_u == "BUY"
        and blocked_by_u == "outer_band_guard"
        and observe_reason_u == "outer_band_reversal_support_required_observe"
        and plan_active
        and plan_side_u in {"", action_u}
        and default_side_aligned
        and (
            near_confirm
            or bool(plan.get("structural_relief_applied", False))
            or _plan_float("pair_gap") >= 0.18
        )
        and _plan_float("candidate_support") >= 0.14
        and _plan_float("action_confirm_score") >= 0.10
        and _plan_float("confirm_fake_gap") >= -0.18
        and _plan_float("wait_confirm_gap") >= -0.05
        and _plan_float("continue_fail_gap") >= -0.22
        and _plan_float("same_side_barrier", default=1.0) <= 0.66
    )
    bounded_probe_promotion_active = bool(
        bounded_middle_sr_probe_relief or bounded_xau_outer_band_followthrough_relief
    )
    bounded_probe_promotion_reason = ""
    bounded_probe_size_multiplier = 1.0
    bounded_probe_entry_stage = ""
    if bounded_middle_sr_probe_relief:
        bounded_probe_promotion_reason = "bounded_middle_sr_anchor_probe_promotion"
        bounded_probe_size_multiplier = 0.35
        bounded_probe_entry_stage = "conservative"
    elif bounded_xau_outer_band_followthrough_relief:
        bounded_probe_promotion_reason = "bounded_xau_outer_band_followthrough_probe"
        bounded_probe_size_multiplier = 0.45
        bounded_probe_entry_stage = "balanced"
    guard_active = bool(
        probe_surface
        and probe_not_ready_surface
        and blocked_by_u in {"", "probe_promotion_gate", "middle_sr_anchor_guard", "outer_band_guard"}
        and symbol_u in {"XAUUSD", "BTCUSD", "NAS100"}
    )
    allows_open = bool((not guard_active) or bounded_probe_promotion_active)
    failure_code = "probe_promotion_gate" if (guard_active and not allows_open) else ""
    return {
        "contract_version": "probe_promotion_guard_v1",
        "symbol": str(symbol_u or ""),
        "action": str(action_u or ""),
        "observe_reason": str(observe_reason or ""),
        "blocked_by": str(blocked_by or ""),
        "action_none_reason": str(action_none_reason or ""),
        "plan_active": bool(plan_active),
        "plan_ready_for_entry": bool(plan_ready),
        "plan_reason": str(plan_reason or ""),
        "plan_side": str(plan_side_u or ""),
        "probe_scene_id": str(probe_scene_id or ""),
        "consumer_stage": str(consumer_stage_u or ""),
        "consumer_entry_ready": bool(consumer_entry_ready),
        "quick_trace_state": str(quick_trace_state_u or ""),
        "quick_trace_reason": str(quick_trace_reason or ""),
        "guard_active": bool(guard_active),
        "allows_open": bool(allows_open),
        "failure_code": str(failure_code or ""),
        "bounded_probe_promotion_active": bool(bounded_probe_promotion_active),
        "bounded_probe_promotion_reason": str(bounded_probe_promotion_reason or ""),
        "bounded_probe_size_multiplier": float(bounded_probe_size_multiplier),
        "bounded_probe_entry_stage": str(bounded_probe_entry_stage or ""),
    }


def _directional_reason_tokens_v1(direction: str) -> tuple[str, ...]:
    direction_u = str(direction or "").upper().strip()
    if direction_u == "UP":
        return (
            "upper_break_fail",
            "upper_reclaim",
            "lower_rebound",
            "buy_watch",
            "buy_probe",
            "buy_wait",
        )
    return (
        "upper_reject",
        "middle_sr_anchor",
        "upper_dominant",
        "lower_dominant",
        "sell_watch",
        "sell_probe",
        "sell_wait",
        "breakdown",
        "lower_break",
    )


def _build_directional_structural_context_v1(
    direction: str,
    runtime_signal_row: dict | None,
) -> dict[str, object]:
    direction_u = str(direction or "").upper().strip()
    runtime_row = dict(runtime_signal_row or {})
    if direction_u not in {"UP", "DOWN"}:
        return {
            "direction": "",
            "score": 0.0,
            "confirmed": False,
            "trend_alignment_count": 0,
        }

    if direction_u == "UP":
        break_states = {"BREAKOUT_HELD", "RECLAIMED"}
        relations = {"ABOVE", "AT_HIGH"}
        box_states = {"ABOVE", "UPPER", "UPPER_EDGE"}
        bb_states = {"UPPER", "UPPER_EDGE", "ABOVE", "BREAKOUT"}
        side_expected = "BUY"
    else:
        break_states = {"BREAKDOWN_HELD", "BREAKOUT_FAILED", "REJECTED"}
        relations = {"BELOW", "AT_LOW"}
        box_states = {"BELOW", "LOWER", "LOWER_EDGE"}
        bb_states = {"LOWER", "LOWER_EDGE", "BELOW", "BREAKDOWN"}
        side_expected = "SELL"

    htf_alignment_state = str(runtime_row.get("htf_alignment_state", "") or "").upper().strip()
    break_state = str(runtime_row.get("previous_box_break_state", "") or "").upper().strip()
    relation = str(runtime_row.get("previous_box_relation", "") or "").upper().strip()
    box_state = str(runtime_row.get("box_state", "") or "").upper().strip()
    bb_state = str(runtime_row.get("bb_state", "") or "").upper().strip()
    breakout_direction = str(
        runtime_row.get("breakout_direction", runtime_row.get("breakout_candidate_direction", "")) or ""
    ).upper().strip()
    breakout_target = str(runtime_row.get("breakout_candidate_action_target", "") or "").upper().strip()
    current_side = str(
        runtime_row.get("consumer_check_side")
        or runtime_row.get("setup_side")
        or runtime_row.get("observe_side")
        or ""
    ).upper().strip()
    current_reason = str(
        runtime_row.get("consumer_check_reason")
        or runtime_row.get("observe_reason")
        or runtime_row.get("action_none_reason")
        or runtime_row.get("blocked_by")
        or ""
    ).lower().strip()
    breakout_runtime = dict(runtime_row.get("breakout_event_runtime_v1", {}) or {})
    breakout_overlay = dict(runtime_row.get("breakout_event_overlay_candidates_v1", {}) or {})
    trend_alignment_count = 0
    for field in ("trend_15m_direction", "trend_1h_direction", "trend_4h_direction", "trend_1d_direction"):
        trend_direction = str(runtime_row.get(field, "") or "").upper().strip()
        if direction_u == "UP" and trend_direction == "UPTREND":
            trend_alignment_count += 1
        elif direction_u == "DOWN" and trend_direction == "DOWNTREND":
            trend_alignment_count += 1

    supportive_break_state = break_state in break_states
    supportive_relation = relation in relations or (relation == "INSIDE" and supportive_break_state)
    supportive_box = box_state in box_states
    supportive_bb = bb_state in bb_states
    breakout_supportive = bool(
        breakout_direction == direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    breakout_opposing = bool(
        breakout_direction in {"UP", "DOWN"}
        and breakout_direction != direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    reason_tokens = _directional_reason_tokens_v1(direction_u)
    opposite_tokens = _directional_reason_tokens_v1("DOWN" if direction_u == "UP" else "UP")
    reason_supportive = any(token in current_reason for token in reason_tokens)
    reason_opposing = any(token in current_reason for token in opposite_tokens)
    breakout_state = str(
        breakout_runtime.get("breakout_state") or runtime_row.get("breakout_candidate_surface_state") or ""
    ).lower().strip()
    breakout_retest_status = str(breakout_runtime.get("breakout_retest_status", "") or "").lower().strip()
    breakout_reference_type = str(breakout_runtime.get("breakout_reference_type", "") or "").lower().strip()
    breakout_confidence = float(
        breakout_runtime.get("breakout_confidence", runtime_row.get("breakout_candidate_confidence", 0.0))
        or 0.0
    )
    breakout_followthrough = float(
        breakout_runtime.get(
            "breakout_followthrough_score",
            runtime_row.get("breakout_followthrough_score", 0.0),
        )
        or 0.0
    )
    low_retests = float(
        runtime_row.get("previous_box_low_retest_count", runtime_row.get("swing_low_retest_count_20", 0.0))
        or 0.0
    )
    high_retests = float(
        runtime_row.get("previous_box_high_retest_count", runtime_row.get("swing_high_retest_count_20", 0.0))
        or 0.0
    )

    continuation_resume_score = 0.0
    if breakout_direction == direction_u:
        continuation_resume_score += 0.18
    if breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        continuation_resume_score += 0.12
    if breakout_state in {"breakout_pullback", "continuation_follow", "reclaim_breakout_candidate"}:
        continuation_resume_score += 0.14
    if breakout_retest_status in {"passed", "holding", "ready"}:
        continuation_resume_score += 0.12
    if breakout_reference_type in {"squeeze", "reclaim", "retest"}:
        continuation_resume_score += 0.06
    continuation_resume_score += max(0.0, min(1.0, breakout_confidence)) * 0.10
    continuation_resume_score += max(0.0, min(1.0, breakout_followthrough)) * 0.12
    if direction_u == "UP":
        if break_state in {"BREAKOUT_HELD", "RECLAIMED"}:
            continuation_resume_score += 0.08
        if relation in {"ABOVE", "AT_HIGH", "INSIDE"}:
            continuation_resume_score += 0.08
        if low_retests >= 2:
            continuation_resume_score += 0.10
    else:
        if break_state in {"BREAKDOWN_HELD", "BREAKOUT_FAILED", "REJECTED"}:
            continuation_resume_score += 0.08
        if relation in {"BELOW", "AT_LOW", "INSIDE"}:
            continuation_resume_score += 0.08
        if high_retests >= 2:
            continuation_resume_score += 0.10
    continuation_resume_score = max(0.0, min(1.0, float(continuation_resume_score)))
    continuation_resume_confirmed = bool(
        breakout_direction == direction_u
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
        and continuation_resume_score >= 0.44
    )

    score = 0.0
    if htf_alignment_state == "WITH_HTF":
        score += 0.20
    if trend_alignment_count >= 3:
        score += 0.18
    elif trend_alignment_count == 2:
        score += 0.12
    elif trend_alignment_count == 1:
        score += 0.05
    if supportive_break_state:
        score += 0.18
    if supportive_relation:
        score += 0.10
    if supportive_box:
        score += 0.07
    if supportive_bb:
        score += 0.06
    if breakout_supportive:
        score += 0.12
    if reason_supportive:
        score += 0.09
    if continuation_resume_confirmed:
        score += 0.10
    score += continuation_resume_score * 0.08
    if current_side == side_expected:
        score += 0.05
    elif current_side:
        score -= 0.04
    if breakout_opposing:
        score -= 0.15
    if reason_opposing:
        score -= 0.10

    normalized_score = max(0.0, min(1.0, float(score)))
    confirmed = bool(
        normalized_score >= 0.42
        and htf_alignment_state == "WITH_HTF"
        and trend_alignment_count >= 2
        and (
            supportive_break_state
            or breakout_supportive
            or reason_supportive
            or continuation_resume_confirmed
        )
    )
    return {
        "direction": str(direction_u),
        "score": round(normalized_score, 4),
        "confirmed": bool(confirmed),
        "trend_alignment_count": int(trend_alignment_count),
        "supportive_break_state": bool(supportive_break_state),
        "supportive_relation": bool(supportive_relation),
        "breakout_supportive": bool(breakout_supportive),
        "reason_supportive": bool(reason_supportive),
        "reason_opposing": bool(reason_opposing),
        "continuation_resume_score": round(continuation_resume_score, 4),
        "continuation_resume_confirmed": bool(continuation_resume_confirmed),
    }


def _build_directional_continuation_promotion_v1(
    *,
    symbol: str,
    baseline_action: str,
    runtime_signal_row: dict | None = None,
    active_action_conflict_guard_v1: dict | None = None,
) -> dict[str, object]:
    symbol_u = str(symbol or "").upper().strip()
    runtime_row = dict(runtime_signal_row or {})
    baseline_action_u = _resolve_directional_baseline_action_side_v1(
        baseline_action,
        runtime_row.get("consumer_check_side", ""),
        runtime_row.get("setup_side", ""),
        runtime_row.get("action_selected", ""),
        runtime_row.get("core_allowed_action", ""),
    )
    guard = dict(active_action_conflict_guard_v1 or {})

    overlay_payload = _safe_mapping(runtime_row.get("directional_continuation_overlay_v1", {}))
    overlay_enabled = _safe_bool_flag(
        overlay_payload.get(
            "overlay_enabled",
            runtime_row.get("directional_continuation_overlay_enabled", False),
        )
    )
    overlay_direction = str(
        overlay_payload.get(
            "overlay_direction",
            runtime_row.get("directional_continuation_overlay_direction", ""),
        )
        or ""
    ).upper().strip()
    overlay_selection_state = str(
        overlay_payload.get(
            "overlay_selection_state",
            runtime_row.get("directional_continuation_overlay_selection_state", ""),
        )
        or ""
    ).upper().strip()
    overlay_event_kind = str(
        overlay_payload.get(
            "overlay_event_kind_hint",
            runtime_row.get("directional_continuation_overlay_event_kind_hint", ""),
        )
        or ""
    ).upper().strip()
    try:
        overlay_score = max(
            0.0,
            min(
                1.0,
                float(
                    overlay_payload.get(
                        "overlay_score",
                        runtime_row.get("directional_continuation_overlay_score", 0.0),
                    )
                    or 0.0
                ),
            ),
        )
    except (TypeError, ValueError):
        overlay_score = 0.0

    htf_alignment_state = str(runtime_row.get("htf_alignment_state", "") or "").upper().strip()
    context_conflict_state = str(runtime_row.get("context_conflict_state", "") or "").upper().strip()
    try:
        context_conflict_score = float(runtime_row.get("context_conflict_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        context_conflict_score = 0.0
    trend_fields = (
        "trend_15m_direction",
        "trend_1h_direction",
        "trend_4h_direction",
        "trend_1d_direction",
    )
    trend_alignment_count = 0
    for field in trend_fields:
        trend_direction = str(runtime_row.get(field, "") or "").upper().strip()
        if overlay_direction == "UP" and trend_direction == "UPTREND":
            trend_alignment_count += 1
        elif overlay_direction == "DOWN" and trend_direction == "DOWNTREND":
            trend_alignment_count += 1
    structural_context = _build_directional_structural_context_v1(overlay_direction, runtime_row)
    structural_support_score = float(structural_context.get("score", 0.0) or 0.0)
    structural_continuation_confirmed = bool(structural_context.get("confirmed", False))

    breakout_direction = str(
        runtime_row.get("breakout_direction", runtime_row.get("breakout_candidate_direction", "")) or ""
    ).upper().strip()
    breakout_target = str(runtime_row.get("breakout_candidate_action_target", "") or "").upper().strip()
    try:
        breakout_confidence = float(
            runtime_row.get(
                "breakout_confidence",
                runtime_row.get("breakout_candidate_confidence", 0.0),
            )
            or 0.0
        )
    except (TypeError, ValueError):
        breakout_confidence = 0.0

    promoted_action = ""
    if overlay_direction == "UP":
        promoted_action = "BUY"
    elif overlay_direction == "DOWN":
        promoted_action = "SELL"

    action_conflict = bool(
        overlay_enabled
        and baseline_action_u in {"BUY", "SELL"}
        and promoted_action in {"BUY", "SELL"}
        and promoted_action != baseline_action_u
    )
    overlay_side_confirmed = bool(
        (overlay_direction == "UP" and overlay_event_kind in {"BUY_WATCH", "BUY_READY", "BUY"})
        or (overlay_direction == "DOWN" and overlay_event_kind in {"SELL_WATCH", "SELL_READY", "SELL"})
    )
    context_confirmed = bool(
        htf_alignment_state == "WITH_HTF"
        and (
            context_conflict_state in {"AGAINST_HTF", "AGAINST_PREV_BOX", "AGAINST_PREV_BOX_AND_HTF"}
            or context_conflict_score >= 0.80
        )
    )
    multi_tf_supportive = bool(trend_alignment_count >= 3 and htf_alignment_state == "WITH_HTF")
    breakout_supportive = bool(
        breakout_direction == overlay_direction
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
        and breakout_confidence >= 0.28
    )
    strong_overlay = bool(overlay_score >= 0.88)
    supportive_overlay = bool(overlay_score >= 0.74 and breakout_supportive)
    aligned_overlay = bool(overlay_score >= 0.60 and multi_tf_supportive and context_conflict_score >= 0.75)
    structural_overlay = bool(overlay_score >= 0.56 and structural_continuation_confirmed)
    guard_applied = bool(guard.get("guard_applied", False))
    suppressed_reason = ""

    active = bool(
        action_conflict
        and overlay_side_confirmed
        and (context_confirmed or structural_continuation_confirmed)
        and (strong_overlay or supportive_overlay or aligned_overlay or structural_overlay)
    )
    recommended_entry_stage = "balanced" if bool(overlay_score >= 0.86 and breakout_supportive) else "conservative"
    size_multiplier = 0.45 if recommended_entry_stage == "balanced" else 0.30
    reason = ""
    if active:
        reason = (
            "directional_continuation_overlay_breakout_promotion"
            if breakout_supportive
            else "directional_continuation_overlay_structural_promotion"
            if structural_overlay and not context_confirmed
            else "directional_continuation_overlay_multitf_promotion"
            if aligned_overlay and not strong_overlay
            else "directional_continuation_overlay_promotion"
        )
    else:
        if not action_conflict:
            suppressed_reason = "no_action_conflict"
        elif not overlay_side_confirmed:
            suppressed_reason = "overlay_not_confirmed"
        elif not (context_confirmed or structural_continuation_confirmed):
            suppressed_reason = "guard_or_structure_not_confirmed"
        elif not (strong_overlay or supportive_overlay or aligned_overlay or structural_overlay):
            suppressed_reason = (
                "overlay_not_strong_enough"
                if overlay_score > 0.0
                else "overlay_score_missing"
            )
        else:
            suppressed_reason = "inactive_unspecified"

    return {
        "contract_version": "directional_continuation_promotion_v1",
        "symbol": str(symbol_u or ""),
        "baseline_action": str(baseline_action_u or ""),
        "overlay_enabled": bool(overlay_enabled),
        "overlay_direction": str(overlay_direction or ""),
        "overlay_selection_state": str(overlay_selection_state or ""),
        "overlay_event_kind_hint": str(overlay_event_kind or ""),
        "overlay_score": float(overlay_score),
        "htf_alignment_state": str(htf_alignment_state or ""),
        "context_conflict_state": str(context_conflict_state or ""),
        "context_conflict_score": float(context_conflict_score),
        "trend_alignment_count": int(trend_alignment_count),
        "multi_tf_supportive": bool(multi_tf_supportive),
        "breakout_direction": str(breakout_direction or ""),
        "breakout_candidate_target": str(breakout_target or ""),
        "breakout_confidence": float(breakout_confidence),
        "breakout_supportive": bool(breakout_supportive),
        "strong_overlay": bool(strong_overlay),
        "supportive_overlay": bool(supportive_overlay),
        "aligned_overlay": bool(aligned_overlay),
        "structural_continuation_confirmed": bool(structural_continuation_confirmed),
        "structural_support_score": float(structural_support_score),
        "structural_overlay": bool(structural_overlay),
        "guard_applied": bool(guard_applied),
        "promoted_action": str(promoted_action or ""),
        "active": bool(active),
        "recommended_entry_stage": str(recommended_entry_stage or ""),
        "size_multiplier": float(size_multiplier),
        "promotion_reason": str(reason or ""),
        "promotion_suppressed_reason": str(suppressed_reason or ""),
    }


def _normalize_execution_action_side(value: object) -> str:
    text = str(value or "").upper().strip()
    return text if text in {"BUY", "SELL"} else ""


def _resolve_directional_baseline_action_side_v1(*candidates: object) -> str:
    for value in candidates:
        normalized = _normalize_execution_action_side(value)
        if normalized:
            return normalized
        text = str(value or "").upper().strip()
        if text == "BUY_ONLY":
            return "BUY"
        if text == "SELL_ONLY":
            return "SELL"
    return ""


def _display_execution_action_side(
    value: object,
    *,
    default: str = "NONE",
) -> str:
    normalized = _normalize_execution_action_side(value)
    if normalized:
        return normalized
    fallback = str(default or "NONE").upper().strip()
    return fallback or "NONE"


def _build_execution_action_diff_v1(
    *,
    original_action_side: str,
    current_action_side: str,
    blocked_by: str = "",
    observe_reason: str = "",
    action_none_reason: str = "",
    active_action_conflict_guard_v1: dict | None = None,
    directional_continuation_promotion_v1: dict | None = None,
) -> dict[str, object]:
    original_side = _normalize_execution_action_side(original_action_side)
    current_side = _normalize_execution_action_side(current_action_side)
    guard_map = dict(active_action_conflict_guard_v1 or {})
    promotion_map = dict(directional_continuation_promotion_v1 or {})
    guard_applied = bool(guard_map.get("guard_applied", False))
    promotion_active = bool(promotion_map.get("active", False))
    guarded_action_side = "SKIP" if guard_applied else _display_execution_action_side(original_side)
    promoted_action_side = _normalize_execution_action_side(
        promotion_map.get("promoted_action", "")
    )
    final_action_side = current_side or ("SKIP" if guard_applied or blocked_by or action_none_reason else "NONE")
    reason_keys: list[str] = []
    for item in (
        guard_map.get("failure_code", ""),
        promotion_map.get("promotion_reason", ""),
        blocked_by,
        action_none_reason,
    ):
        text = str(item or "").strip()
        if text and text not in reason_keys:
            reason_keys.append(text)
    if observe_reason and final_action_side == "SKIP":
        observe_key = f"observe:{str(observe_reason).strip()}"
        if observe_key not in reason_keys:
            reason_keys.append(observe_key)
    return {
        "contract_version": "execution_action_diff_v1",
        "original_action_side": _display_execution_action_side(original_side),
        "guarded_action_side": str(guarded_action_side),
        "promoted_action_side": _display_execution_action_side(promoted_action_side),
        "final_action_side": str(final_action_side),
        "guard_applied": bool(guard_applied),
        "promotion_active": bool(promotion_active),
        "action_changed": bool(
            guard_applied
            or promotion_active
            or str(original_side) != str(final_action_side)
        ),
        "action_change_reason_keys": list(reason_keys),
        "guard_reason_summary": str(guard_map.get("reason_summary", "") or ""),
        "promotion_reason": str(promotion_map.get("promotion_reason", "") or ""),
        "promotion_suppressed_reason": str(
            promotion_map.get("promotion_suppressed_reason", "") or ""
        ),
        "blocked_by": str(blocked_by or ""),
        "observe_reason": str(observe_reason or ""),
        "action_none_reason": str(action_none_reason or ""),
    }


def _build_execution_action_diff_flat_fields_v1(payload: dict | None) -> dict[str, object]:
    row = dict(payload or {})
    return {
        "execution_diff_original_action_side": str(row.get("original_action_side", "") or ""),
        "execution_diff_guarded_action_side": str(row.get("guarded_action_side", "") or ""),
        "execution_diff_promoted_action_side": str(row.get("promoted_action_side", "") or ""),
        "execution_diff_final_action_side": str(row.get("final_action_side", "") or ""),
        "execution_diff_changed": bool(row.get("action_changed", False)),
        "execution_diff_guard_applied": bool(row.get("guard_applied", False)),
        "execution_diff_promotion_active": bool(row.get("promotion_active", False)),
        "execution_diff_reason_keys": list(row.get("action_change_reason_keys", []) or []),
        "execution_diff_guard_reason_summary": str(row.get("guard_reason_summary", "") or ""),
        "execution_diff_promotion_reason": str(row.get("promotion_reason", "") or ""),
        "execution_diff_promotion_suppressed_reason": str(
            row.get("promotion_suppressed_reason", "") or ""
        ),
    }


def _refresh_directional_runtime_execution_surface_v1(
    *,
    runtime_owner: object | None,
    symbol: str,
    runtime_row: dict | None,
    baseline_action: str,
    current_action: str,
    blocked_by: str = "",
    observe_reason: str = "",
    action_none_reason: str = "",
    setup_id: str = "",
    setup_reason: str = "",
    forecast_state25_log_only_overlay_trace_v1: dict | None = None,
    belief_action_hint_v1: dict | None = None,
    barrier_action_hint_v1: dict | None = None,
    countertrend_continuation_signal_v1: dict | None = None,
    breakout_event_runtime_v1: dict | None = None,
    breakout_event_overlay_candidates_v1: dict | None = None,
) -> dict[str, object]:
    canonical_row = dict(runtime_row or {})
    builder = getattr(runtime_owner, "build_entry_runtime_signal_row", None)
    if callable(builder):
        try:
            rebuilt_row = builder(str(symbol), canonical_row)
            if isinstance(rebuilt_row, dict):
                canonical_row = dict(rebuilt_row)
        except Exception:
            pass

    guard = _build_active_action_conflict_guard_v1(
        symbol=str(symbol),
        baseline_action=str(baseline_action or ""),
        setup_id=str(setup_id or ""),
        setup_reason=str(setup_reason or observe_reason or ""),
        runtime_signal_row=canonical_row,
        forecast_state25_log_only_overlay_trace_v1=dict(
            forecast_state25_log_only_overlay_trace_v1 or {}
        ),
        belief_action_hint_v1=dict(belief_action_hint_v1 or {}),
        barrier_action_hint_v1=dict(barrier_action_hint_v1 or {}),
        countertrend_continuation_signal_v1=dict(countertrend_continuation_signal_v1 or {}),
        breakout_event_runtime_v1=dict(breakout_event_runtime_v1 or {}),
        breakout_event_overlay_candidates_v1=dict(
            breakout_event_overlay_candidates_v1 or {}
        ),
    )
    promotion = _build_directional_continuation_promotion_v1(
        symbol=str(symbol),
        baseline_action=str(guard.get("baseline_action", "") or baseline_action or ""),
        runtime_signal_row=canonical_row,
        active_action_conflict_guard_v1=guard,
    )
    execution_diff = _build_execution_action_diff_v1(
        original_action_side=str(baseline_action or ""),
        current_action_side=str(current_action or ""),
        blocked_by=str(blocked_by or ""),
        observe_reason=str(observe_reason or ""),
        action_none_reason=str(action_none_reason or ""),
        active_action_conflict_guard_v1=guard,
        directional_continuation_promotion_v1=promotion,
    )
    canonical_row["execution_action_diff_v1"] = dict(execution_diff or {})
    canonical_row.update(_build_execution_action_diff_flat_fields_v1(execution_diff))
    canonical_row["directional_continuation_promotion_v1"] = dict(promotion or {})
    canonical_row["directional_continuation_promotion_active"] = int(
        1 if bool((promotion or {}).get("active", False)) else 0
    )
    canonical_row["directional_continuation_promotion_action"] = str(
        (promotion or {}).get("promoted_action", "") or ""
    )
    canonical_row["directional_continuation_promotion_reason"] = str(
        (promotion or {}).get("promotion_reason", "") or ""
    )
    canonical_row["directional_continuation_promotion_overlay_score"] = float(
        (promotion or {}).get("overlay_score", 0.0) or 0.0
    )
    canonical_row["directional_continuation_promotion_entry_stage"] = str(
        (promotion or {}).get("recommended_entry_stage", "") or ""
    )
    canonical_row["directional_continuation_promotion_size_multiplier"] = float(
        (promotion or {}).get("size_multiplier", 0.0) or 0.0
    )
    return {
        "runtime_row": canonical_row,
        "active_action_conflict_guard_v1": guard,
        "directional_continuation_promotion_v1": promotion,
        "execution_action_diff_v1": execution_diff,
    }


def _resolve_teacher_label_exploration_family_v1(
    *,
    symbol: str,
    action: str,
    observe_reason: str,
    probe_scene_id: str,
) -> str:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    observe_reason_u = str(observe_reason or "").strip().lower()
    probe_scene_u = str(probe_scene_id or "").strip().lower()

    if (
        action_u == "BUY"
        and observe_reason_u == "lower_rebound_probe_observe"
        and probe_scene_u
        in {
            "btc_lower_buy_conservative_probe",
            "xau_second_support_buy_probe",
            "nas_clean_confirm_probe",
        }
    ):
        return f"{symbol_u.lower()}_lower_rebound_probe_buy"

    if (
        action_u == "SELL"
        and observe_reason_u == "upper_reject_probe_observe"
        and probe_scene_u
        in {
            "btc_upper_sell_probe",
            "xau_upper_sell_probe",
            "nas_clean_confirm_probe",
        }
    ):
        return f"{symbol_u.lower()}_upper_reject_probe_sell"

    if action_u == "SELL" and observe_reason_u == "upper_break_fail_confirm":
        return f"{symbol_u.lower()}_upper_break_fail_confirm_sell"

    if action_u == "SELL" and observe_reason_u == "outer_band_reversal_support_required_observe":
        if (not probe_scene_u) or probe_scene_u in {
            "btc_upper_sell_probe",
            "xau_upper_sell_probe",
            "nas_clean_confirm_probe",
        }:
            return f"{symbol_u.lower()}_outer_band_reversal_observe_sell"

    return ""


def _build_teacher_label_exploration_entry_v1(
    *,
    symbol: str,
    action: str,
    observe_reason: str,
    action_none_reason: str,
    blocked_by: str,
    probe_scene_id: str,
    consumer_check_state_v1: dict | None,
    guard_failure_code: str,
    score: float,
    effective_threshold: float,
    same_dir_count: int,
) -> dict:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    observe_reason_u = str(observe_reason or "").strip().lower()
    action_none_u = str(action_none_reason or "").strip().lower()
    blocked_u = str(blocked_by or "").strip().lower()
    guard_failure_u = str(guard_failure_code or "").strip().lower()
    probe_scene_u = str(probe_scene_id or "").strip()
    state_local = dict(consumer_check_state_v1 or {})

    allowed_symbols = {
        str(item or "").upper().strip()
        for item in tuple(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SYMBOLS", ()) or ())
        if str(item or "").strip()
    }
    allowed_observe_reasons = {
        str(item or "").strip().lower()
        for item in tuple(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_OBSERVE_REASONS", ()) or ())
        if str(item or "").strip()
    }
    allowed_soft_blocks = {
        str(item or "").strip().lower()
        for item in tuple(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ALLOWED_SOFT_BLOCKS", ()) or ())
        if str(item or "").strip()
    }

    family = _resolve_teacher_label_exploration_family_v1(
        symbol=symbol_u,
        action=action_u,
        observe_reason=observe_reason_u,
        probe_scene_id=probe_scene_u,
    )
    check_side_u = str(state_local.get("check_side", "") or "").upper().strip()
    check_stage_u = str(state_local.get("check_stage", "") or "").upper().strip()
    entry_ready = bool(state_local.get("entry_ready", False))
    check_candidate = bool(state_local.get("check_candidate", False))
    display_ready = bool(state_local.get("check_display_ready", False))
    chart_hint_u = str(state_local.get("chart_event_kind_hint", "") or "").upper().strip()
    chart_display_reason_u = str(state_local.get("chart_display_reason", "") or "").strip().lower()
    state_block_reason_u = str(
        state_local.get("entry_block_reason", "")
        or state_local.get("blocked_display_reason", "")
        or ""
    ).strip().lower()
    soft_block_reason = state_block_reason_u or blocked_u or guard_failure_u
    require_flat_position = bool(
        getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_REQUIRE_FLAT_POSITION", True)
    )
    max_same_dir_count = max(
        0,
        int(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_SAME_DIR_COUNT", 1) or 0),
    )

    score_f = float(score or 0.0)
    threshold_f = max(1.0, float(effective_threshold or 1.0))
    score_ratio = score_f / threshold_f
    threshold_gap = max(0.0, threshold_f - score_f)
    quality_ok = bool(
        score_ratio >= float(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MIN_SCORE_RATIO", 0.82) or 0.82)
        or threshold_gap <= float(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_MAX_THRESHOLD_GAP", 60.0) or 60.0)
    )
    # Some live no-action observe rows reach exploration before consumer display/candidate
    # flags are fully promoted. Once a teacher-label family is already identified, treat
    # that family match itself as sufficient signal presence for the exploration layer.
    signal_present = bool(check_candidate or display_ready or probe_scene_u or family)
    side_ok = bool(not check_side_u or check_side_u == action_u)
    stage_ok = bool(check_stage_u in {"", "PROBE", "OBSERVE", "BLOCKED"})
    family_ok = bool(family and observe_reason_u in allowed_observe_reasons)
    soft_block_ok = bool(
        soft_block_reason in allowed_soft_blocks
        or (
            guard_failure_u in {"consumer_stage_blocked", "consumer_entry_not_ready"}
            and state_block_reason_u in allowed_soft_blocks
        )
    )
    flat_ok = bool((not require_flat_position) or int(same_dir_count or 0) <= max_same_dir_count)
    explicit_wait_guard = bool(
        chart_hint_u == "WAIT"
        and not entry_ready
        and check_stage_u in {"OBSERVE", "PROBE", "BLOCKED"}
        and (
            "wait_as_wait" in chart_display_reason_u
            or "promotion_wait" in chart_display_reason_u
            or "wait_checks" in chart_display_reason_u
        )
    )

    active = bool(
        bool(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED", False))
        and action_u in {"BUY", "SELL"}
        and symbol_u in allowed_symbols
        and family_ok
        and soft_block_ok
        and signal_present
        and side_ok
        and stage_ok
        and not entry_ready
        and flat_ok
        and quality_ok
        and not explicit_wait_guard
    )

    size_multiplier = float(
        Config.get_symbol_float(
            symbol_u,
            getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_SIZE_MULTIPLIER_BY_SYMBOL", {}),
            getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_SIZE_MULTIPLIER", 0.40),
        )
    )
    activation_reason = ""
    if active:
        activation_reason = "teacher_label_exploration_soft_guard_bypass"

    return {
        "contract_version": "teacher_label_exploration_entry_v1",
        "enabled": bool(getattr(Config, "ENTRY_TEACHER_LABEL_EXPLORATION_ENABLED", False)),
        "active": bool(active),
        "symbol": str(symbol_u or ""),
        "action": str(action_u or ""),
        "observe_reason": str(observe_reason or ""),
        "action_none_reason": str(action_none_reason or ""),
        "guard_failure_code": str(guard_failure_u or ""),
        "soft_block_reason": str(soft_block_reason or ""),
        "probe_scene_id": str(probe_scene_u or ""),
        "family": str(family or ""),
        "layer": "teacher_label_exploration_entry_v1",
        "activation_reason": str(activation_reason or ""),
        "require_flat_position": bool(require_flat_position),
        "max_same_dir_count": int(max_same_dir_count),
        "same_dir_count": int(same_dir_count or 0),
        "check_candidate": bool(check_candidate),
        "check_display_ready": bool(display_ready),
        "check_entry_ready": bool(entry_ready),
        "check_side": str(check_side_u or ""),
        "check_stage": str(check_stage_u or ""),
        "check_chart_hint": str(chart_hint_u or ""),
        "check_chart_display_reason": str(chart_display_reason_u or ""),
        "explicit_wait_guard": bool(explicit_wait_guard),
        "score_ratio": round(float(score_ratio), 4),
        "threshold_gap": round(float(threshold_gap), 4),
        "size_multiplier": round(float(size_multiplier), 4),
    }


def _normalize_order_lot(*, base_lot: float, size_multiplier: float = 1.0, min_lot: float = 0.01) -> float:
    base = max(0.0, float(base_lot))
    mult = max(0.01, float(size_multiplier))
    floor = max(0.01, float(min_lot))
    return round(max(floor, base * mult), 2)


def _resolve_probe_execution_plan(
    *,
    symbol: str,
    action: str,
    entry_stage: str,
    base_lot: float,
    min_lot: float,
    same_dir_count: int,
    probe_plan_v1: dict | None = None,
) -> dict:
    plan = dict(probe_plan_v1 or {})
    action_u = str(action or "").strip().upper()
    stage_u = str(entry_stage or "balanced").strip().lower()
    if stage_u not in {"aggressive", "balanced", "conservative"}:
        stage_u = "balanced"
    probe_active = bool(
        plan.get("active", False)
        and plan.get("ready_for_entry", False)
        and str(plan.get("intended_action", "") or "").strip().upper() == action_u
    )
    confirm_add_active = bool((not probe_active) and int(same_dir_count) > 0 and action_u in {"BUY", "SELL"})
    if probe_active:
        size_multiplier = float(plan.get("recommended_size_multiplier", 0.50) or 0.50)
        effective_entry_stage = str(plan.get("recommended_entry_stage", "conservative") or "conservative").strip().lower()
        if effective_entry_stage not in {"aggressive", "balanced", "conservative"}:
            effective_entry_stage = "conservative"
    elif confirm_add_active:
        size_multiplier = float(plan.get("confirm_add_size_multiplier", 1.00) or 1.00)
        effective_entry_stage = stage_u
    else:
        size_multiplier = 1.0
        effective_entry_stage = stage_u
    order_lot = _normalize_order_lot(
        base_lot=float(base_lot),
        size_multiplier=float(size_multiplier),
        min_lot=float(min_lot),
    )
    return {
        "contract_version": "entry_probe_execution_v1",
        "symbol": str(symbol or "").upper().strip(),
        "action": action_u,
        "plan_active": bool(plan.get("active", False)),
        "plan_ready_for_entry": bool(plan.get("ready_for_entry", False)),
        "plan_reason": str(plan.get("reason", "") or ""),
        "trigger_branch": str(plan.get("trigger_branch", "") or ""),
        "probe_scene_id": str(plan.get("symbol_scene_relief", "") or ""),
        "symbol_probe_temperament_v1": (
            dict(plan.get("symbol_probe_temperament_v1", {}) or {})
            if isinstance(plan.get("symbol_probe_temperament_v1", {}), dict)
            else {}
        ),
        "probe_active": bool(probe_active),
        "confirm_add_active": bool(confirm_add_active),
        "base_lot": float(base_lot),
        "order_lot": float(order_lot),
        "size_multiplier": float(size_multiplier),
        "effective_entry_stage": str(effective_entry_stage),
    }


def _resolve_entry_handoff_ids(
    *,
    shadow_observe_confirm: dict | None = None,
    shadow_context_metadata_v1: Mapping[str, object] | None = None,
    shadow_entry_context_v1: Mapping[str, object] | None = None,
) -> tuple[str, str]:
    observe_confirm = dict(shadow_observe_confirm or {})
    metadata = dict(shadow_context_metadata_v1 or {})
    if not metadata and isinstance(shadow_entry_context_v1, Mapping):
        metadata = dict(shadow_entry_context_v1.get("metadata", {}) or {})
    management_profile_id = str(
        observe_confirm.get("management_profile_id", "")
        or metadata.get("management_profile_id", "")
        or ""
    ).strip().lower()
    invalidation_id = str(
        observe_confirm.get("invalidation_id", "")
        or metadata.get("invalidation_id", "")
        or ""
    ).strip().lower()
    return management_profile_id, invalidation_id


def _build_runtime_observe_confirm_dual_write(
    *,
    shadow_observe_confirm: dict | None = None,
) -> dict[str, object]:
    observe_confirm = dict(shadow_observe_confirm or {})
    canonical_field = "observe_confirm_v2"
    compatibility_field = "observe_confirm_v1"
    return {
        "prs_canonical_observe_confirm_field": canonical_field,
        "prs_compatibility_observe_confirm_field": compatibility_field,
        "prs_log_contract_v2": {
            "canonical_observe_confirm_field": canonical_field,
            "compatibility_observe_confirm_field": compatibility_field,
        },
        "observe_confirm_v2": dict(observe_confirm),
        "observe_confirm_v1": dict(observe_confirm),
        "observe_confirm_input_contract_v2": dict(OBSERVE_CONFIRM_INPUT_CONTRACT_V2),
        "observe_confirm_migration_dual_write_v1": dict(OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1),
        "observe_confirm_output_contract_v2": dict(OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2),
        "observe_confirm_scope_contract_v1": dict(OBSERVE_CONFIRM_SCOPE_CONTRACT_V1),
        "consumer_input_contract_v1": dict(CONSUMER_INPUT_CONTRACT_V1),
    }


def _safe_mapping(value: object | None) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            payload = to_dict()
        except Exception:
            return {}
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _safe_float_metric(row: object | None, key: str) -> float:
    row_map = _safe_mapping(row)
    value = row_map.get(key, None)
    if value in ("", None):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_bool_flag(value: object | None) -> bool:
    if isinstance(value, bool):
        return bool(value)
    if value in ("", None):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    value_u = str(value).strip().lower()
    return value_u in {"1", "true", "yes", "y", "on"}


def _wait_state_snapshot(wait_state: object | None) -> dict[str, object]:
    metadata = _safe_mapping(getattr(wait_state, "metadata", {}))
    return {
        "state": str(getattr(wait_state, "state", "") or ""),
        "reason": str(getattr(wait_state, "reason", "") or ""),
        "metadata": metadata,
    }


def _build_semantic_owner_forecast_gap_metrics_v1(
    *,
    runtime_snapshot_row: object | None,
    shadow_transition_forecast_v1: object | None,
    shadow_trade_management_forecast_v1: object | None,
) -> dict[str, float]:
    transition_metadata = _safe_mapping(
        _safe_mapping(shadow_transition_forecast_v1).get("metadata", {})
    )
    management_metadata = _safe_mapping(
        _safe_mapping(shadow_trade_management_forecast_v1).get("metadata", {})
    )
    return {
        "transition_side_separation": float(transition_metadata.get("side_separation", 0.0) or 0.0),
        "transition_confirm_fake_gap": float(transition_metadata.get("confirm_fake_gap", 0.0) or 0.0),
        "transition_reversal_continuation_gap": float(
            transition_metadata.get("reversal_continuation_gap", 0.0) or 0.0
        ),
        "management_continue_fail_gap": float(
            management_metadata.get("continue_fail_gap", 0.0) or 0.0
        ),
        "management_recover_reentry_gap": float(
            management_metadata.get("recover_reentry_gap", 0.0) or 0.0
        ),
        "wait_confirm_gap": _safe_float_metric(runtime_snapshot_row, "wait_confirm_gap"),
        "hold_exit_gap": _safe_float_metric(runtime_snapshot_row, "hold_exit_gap"),
        "same_side_flip_gap": _safe_float_metric(runtime_snapshot_row, "same_side_flip_gap"),
        "belief_barrier_tension_gap": _safe_float_metric(
            runtime_snapshot_row,
            "belief_barrier_tension_gap",
        ),
    }


def _build_semantic_owner_bridge_seed_v1(
    *,
    runtime_snapshot_row: object | None,
    symbol: str,
    action: str,
    setup_id: str,
    setup_side: str,
    entry_session_name: str,
    wait_state: object | None,
    entry_wait_decision: str,
    score: float,
    contra_score: float,
    prediction_bundle: object | None,
    shadow_transition_forecast_v1: object | None,
    shadow_trade_management_forecast_v1: object | None,
    observe_confirm_runtime_payload: object | None,
    state25_candidate_runtime_state: object | None = None,
    forecast_state25_runtime_bridge_v1: object | None = None,
    belief_state25_runtime_bridge_v1: object | None = None,
) -> dict[str, object]:
    runtime_snapshot = _safe_mapping(runtime_snapshot_row)
    wait_snapshot = _wait_state_snapshot(wait_state)
    observe_confirm_payload = _safe_mapping(observe_confirm_runtime_payload)
    seed: dict[str, object] = {
        **runtime_snapshot,
        "symbol": str(symbol),
        "action": str(action or ""),
        "direction": str(action or ""),
        "setup_id": str(setup_id or ""),
        "entry_setup_id": str(setup_id or ""),
        "setup_side": str(setup_side or action or ""),
        "entry_session_name": str(entry_session_name or ""),
        "entry_wait_state": str(wait_snapshot["state"] or ""),
        "entry_wait_reason": str(wait_snapshot["reason"] or ""),
        "entry_wait_decision": str(entry_wait_decision or ""),
        "entry_score": float(score),
        "contra_score_at_entry": float(contra_score),
        "raw_score": float(score),
        "contra_score": float(contra_score),
        "prediction_bundle": prediction_bundle,
        "transition_forecast_v1": _safe_mapping(shadow_transition_forecast_v1),
        "trade_management_forecast_v1": _safe_mapping(shadow_trade_management_forecast_v1),
        "forecast_gap_metrics_v1": _build_semantic_owner_forecast_gap_metrics_v1(
            runtime_snapshot_row=runtime_snapshot_row,
            shadow_transition_forecast_v1=shadow_transition_forecast_v1,
            shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
        ),
        "observe_confirm_v2": _safe_mapping(observe_confirm_payload.get("observe_confirm_v2", {})),
        "state25_candidate_runtime_v1": _safe_mapping(state25_candidate_runtime_state),
    }
    if forecast_state25_runtime_bridge_v1 is not None:
        seed["forecast_state25_runtime_bridge_v1"] = _safe_mapping(
            forecast_state25_runtime_bridge_v1
        )
    if belief_state25_runtime_bridge_v1 is not None:
        seed["belief_state25_runtime_bridge_v1"] = _safe_mapping(
            belief_state25_runtime_bridge_v1
        )
    return seed


def _clone_semantic_owner_bridge_seed_v1(
    base_seed: object | None,
    *,
    forecast_state25_runtime_bridge_v1: object | None = None,
    belief_state25_runtime_bridge_v1: object | None = None,
    barrier_state25_runtime_bridge_v1: object | None = None,
    countertrend_continuation_signal_v1: object | None = None,
) -> dict[str, object]:
    seed = dict(_safe_mapping(base_seed))
    if forecast_state25_runtime_bridge_v1 is not None:
        seed["forecast_state25_runtime_bridge_v1"] = _safe_mapping(
            forecast_state25_runtime_bridge_v1
        )
    else:
        seed.pop("forecast_state25_runtime_bridge_v1", None)
    if belief_state25_runtime_bridge_v1 is not None:
        seed["belief_state25_runtime_bridge_v1"] = _safe_mapping(
            belief_state25_runtime_bridge_v1
        )
    else:
        seed.pop("belief_state25_runtime_bridge_v1", None)
    if barrier_state25_runtime_bridge_v1 is not None:
        seed["barrier_state25_runtime_bridge_v1"] = _safe_mapping(
            barrier_state25_runtime_bridge_v1
        )
    else:
        seed.pop("barrier_state25_runtime_bridge_v1", None)
    if countertrend_continuation_signal_v1 is not None:
        seed["countertrend_continuation_signal_v1"] = _safe_mapping(
            countertrend_continuation_signal_v1
        )
    else:
        seed.pop("countertrend_continuation_signal_v1", None)
    return seed


def _build_semantic_owner_flat_fields_v1(
    *,
    state25_candidate_log_only_trace_v1: object | None,
    forecast_state25_log_only_overlay_trace_v1: object | None,
    belief_action_hint_v1: object | None,
    barrier_action_hint_v1: object | None,
    countertrend_continuation_signal_v1: object | None,
    actual_effective_entry_threshold: float,
    actual_size_multiplier: float,
) -> dict[str, object]:
    candidate_trace = _safe_mapping(state25_candidate_log_only_trace_v1)
    forecast_overlay_trace = _safe_mapping(forecast_state25_log_only_overlay_trace_v1)
    belief_action_hint = _safe_mapping(belief_action_hint_v1)
    barrier_action_hint = _safe_mapping(barrier_action_hint_v1)
    countertrend_signal = _safe_mapping(countertrend_continuation_signal_v1)
    return {
        "state25_candidate_active_candidate_id": str(
            candidate_trace.get("active_candidate_id", "") or ""
        ),
        "state25_candidate_policy_source": str(
            candidate_trace.get("active_policy_source", "") or ""
        ),
        "state25_candidate_rollout_phase": str(candidate_trace.get("rollout_phase", "") or ""),
        "state25_candidate_binding_mode": str(candidate_trace.get("binding_mode", "") or ""),
        "state25_candidate_threshold_log_only_enabled": bool(
            candidate_trace.get("threshold_log_only_enabled", False)
        ),
        "state25_candidate_threshold_symbol_scope_hit": bool(
            candidate_trace.get("threshold_symbol_scope_hit", False)
        ),
        "state25_candidate_threshold_stage_scope_hit": bool(
            candidate_trace.get("threshold_stage_scope_hit", False)
        ),
        "state25_candidate_effective_entry_threshold": float(
            candidate_trace.get(
                "candidate_effective_entry_threshold",
                actual_effective_entry_threshold,
            )
            or 0.0
        ),
        "state25_candidate_entry_threshold_delta": float(
            candidate_trace.get("candidate_entry_threshold_delta", 0.0) or 0.0
        ),
        "state25_candidate_size_log_only_enabled": bool(
            candidate_trace.get("size_log_only_enabled", False)
        ),
        "state25_candidate_size_symbol_scope_hit": bool(
            candidate_trace.get("size_symbol_scope_hit", False)
        ),
        "state25_candidate_size_multiplier": float(
            candidate_trace.get("candidate_size_multiplier", actual_size_multiplier) or 0.0
        ),
        "state25_candidate_size_multiplier_delta": float(
            candidate_trace.get("candidate_size_multiplier_delta", 0.0) or 0.0
        ),
        "state25_candidate_size_min_multiplier": float(
            candidate_trace.get("candidate_size_min_multiplier", actual_size_multiplier) or 0.0
        ),
        "state25_candidate_size_max_multiplier": float(
            candidate_trace.get("candidate_size_max_multiplier", actual_size_multiplier) or 0.0
        ),
        "forecast_state25_overlay_mode": str(
            forecast_overlay_trace.get("binding_mode", "") or ""
        ),
        "forecast_state25_overlay_enabled": bool(
            forecast_overlay_trace.get("overlay_enabled", False)
        ),
        "forecast_state25_candidate_effective_entry_threshold": float(
            forecast_overlay_trace.get(
                "candidate_effective_entry_threshold",
                actual_effective_entry_threshold,
            )
            or 0.0
        ),
        "forecast_state25_candidate_entry_threshold_delta": float(
            forecast_overlay_trace.get("candidate_entry_threshold_delta", 0.0) or 0.0
        ),
        "forecast_state25_candidate_size_multiplier": float(
            forecast_overlay_trace.get("candidate_size_multiplier", actual_size_multiplier) or 0.0
        ),
        "forecast_state25_candidate_size_multiplier_delta": float(
            forecast_overlay_trace.get("candidate_size_multiplier_delta", 0.0) or 0.0
        ),
        "forecast_state25_candidate_wait_bias_action": str(
            forecast_overlay_trace.get("candidate_wait_bias_action", "") or ""
        ),
        "forecast_state25_candidate_management_bias": str(
            forecast_overlay_trace.get("candidate_management_bias", "") or ""
        ),
        "forecast_state25_overlay_reason_summary": str(
            forecast_overlay_trace.get("reason_summary", "") or ""
        ),
        "belief_action_hint_mode": str(belief_action_hint.get("hint_mode", "") or ""),
        "belief_action_hint_enabled": bool(belief_action_hint.get("enabled", False)),
        "belief_candidate_recommended_family": str(
            belief_action_hint.get("recommended_family", "") or ""
        ),
        "belief_candidate_supporting_label": str(
            belief_action_hint.get("supporting_label_candidate", "") or ""
        ),
        "belief_action_hint_confidence": str(
            belief_action_hint.get("overlay_confidence", "") or ""
        ),
        "belief_action_hint_reason_summary": str(
            belief_action_hint.get("reason_summary", "") or ""
        ),
        "barrier_action_hint_mode": str(barrier_action_hint.get("hint_mode", "") or ""),
        "barrier_action_hint_enabled": bool(barrier_action_hint.get("enabled", False)),
        "barrier_candidate_recommended_family": str(
            barrier_action_hint.get("recommended_family", "") or ""
        ),
        "barrier_candidate_supporting_label": str(
            barrier_action_hint.get("supporting_label_candidate", "") or ""
        ),
        "barrier_action_hint_confidence": str(
            barrier_action_hint.get("overlay_confidence", "") or ""
        ),
        "barrier_action_hint_cost_hint": str(
            barrier_action_hint.get("overlay_cost_hint", "") or ""
        ),
        "barrier_action_hint_reason_summary": str(
            barrier_action_hint.get("reason_summary", "") or ""
        ),
        "countertrend_continuation_enabled": bool(
            countertrend_signal.get("enabled", False)
        ),
        "countertrend_continuation_state": str(
            countertrend_signal.get("signal_state", "") or ""
        ),
        "countertrend_continuation_action": str(
            countertrend_signal.get("signal_action", "") or ""
        ),
        "countertrend_continuation_confidence": float(
            countertrend_signal.get("signal_confidence", 0.0) or 0.0
        ),
        "countertrend_continuation_reason_summary": str(
            countertrend_signal.get("reason_summary", "") or ""
        ),
        "countertrend_continuation_warning_count": int(
            countertrend_signal.get("warning_count", 0) or 0
        ),
        "countertrend_continuation_surface_family": str(
            countertrend_signal.get("surface_family", "") or ""
        ),
        "countertrend_continuation_surface_state": str(
            countertrend_signal.get("surface_state", "") or ""
        ),
        "countertrend_anti_long_score": float(
            countertrend_signal.get("anti_long_score", 0.0) or 0.0
        ),
        "countertrend_anti_short_score": float(
            countertrend_signal.get("anti_short_score", 0.0) or 0.0
        ),
        "countertrend_pro_up_score": float(
            countertrend_signal.get("pro_up_score", 0.0) or 0.0
        ),
        "countertrend_pro_down_score": float(
            countertrend_signal.get("pro_down_score", 0.0) or 0.0
        ),
        "countertrend_directional_bias": str(
            countertrend_signal.get("directional_bias", "") or ""
        ),
        "countertrend_action_state": str(
            countertrend_signal.get("directional_action_state", "") or ""
        ),
        "countertrend_directional_candidate_action": str(
            countertrend_signal.get("directional_candidate_action", "") or ""
        ),
        "countertrend_directional_execution_action": str(
            countertrend_signal.get("directional_execution_action", "") or ""
        ),
        "countertrend_directional_state_reason": str(
            countertrend_signal.get("directional_state_reason", "") or ""
        ),
        "countertrend_directional_state_rank": int(
            countertrend_signal.get("directional_state_rank", 0) or 0
        ),
        "countertrend_directional_owner_family": str(
            countertrend_signal.get("directional_owner_family", "") or ""
        ),
        "countertrend_directional_down_bias_score": float(
            countertrend_signal.get("directional_down_bias_score", 0.0) or 0.0
        ),
        "countertrend_directional_up_bias_score": float(
            countertrend_signal.get("directional_up_bias_score", 0.0) or 0.0
        ),
    }


def _build_semantic_owner_runtime_bundle_v1(
    *,
    runtime_snapshot_row: object | None,
    symbol: str,
    action: str,
    setup_id: str,
    setup_reason: str = "",
    setup_side: str,
    entry_session_name: str,
    wait_state: object | None,
    entry_wait_decision: str,
    score: float,
    contra_score: float,
    prediction_bundle: object | None,
    shadow_transition_forecast_v1: object | None,
    shadow_trade_management_forecast_v1: object | None,
    shadow_observe_confirm: dict | None,
    entry_stage: str,
    actual_effective_entry_threshold: float,
    actual_size_multiplier: float,
    state25_candidate_runtime_state: object | None,
) -> dict[str, object]:
    base_bridge_seed_v1 = _build_semantic_owner_bridge_seed_v1(
        runtime_snapshot_row=runtime_snapshot_row,
        symbol=symbol,
        action=action,
        setup_id=setup_id,
        setup_side=setup_side,
        entry_session_name=entry_session_name,
        wait_state=wait_state,
        entry_wait_decision=entry_wait_decision,
        score=score,
        contra_score=contra_score,
        prediction_bundle=prediction_bundle,
        shadow_transition_forecast_v1=shadow_transition_forecast_v1,
        shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
        observe_confirm_runtime_payload=None,
        state25_candidate_runtime_state=state25_candidate_runtime_state,
    )
    state25_candidate_log_only_trace_v1 = build_state25_candidate_entry_log_only_trace_v1(
        _safe_mapping(state25_candidate_runtime_state),
        symbol=str(symbol),
        entry_stage=str(entry_stage or ""),
        actual_effective_entry_threshold=float(actual_effective_entry_threshold),
        actual_size_multiplier=float(actual_size_multiplier),
    )
    observe_confirm_runtime_payload = _build_runtime_observe_confirm_dual_write(
        shadow_observe_confirm=shadow_observe_confirm,
    )
    base_bridge_seed_v1["observe_confirm_v2"] = _safe_mapping(
        _safe_mapping(observe_confirm_runtime_payload).get("observe_confirm_v2", {})
    )
    forecast_state25_runtime_bridge_v1 = build_forecast_state25_runtime_bridge_v1(
        _clone_semantic_owner_bridge_seed_v1(base_bridge_seed_v1)
    )
    forecast_state25_log_only_overlay_trace_v1 = build_forecast_state25_log_only_overlay_trace_v1(
        forecast_state25_runtime_bridge_v1,
        symbol=str(symbol),
        entry_stage=str(entry_stage or ""),
        actual_effective_entry_threshold=float(actual_effective_entry_threshold),
        actual_size_multiplier=float(actual_size_multiplier),
    )
    breakout_event_runtime_v1 = build_breakout_event_runtime_v1(
        _clone_semantic_owner_bridge_seed_v1(
            base_bridge_seed_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
        ),
        forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
    )
    belief_state25_runtime_bridge_v1 = build_belief_state25_runtime_bridge_v1(
        _clone_semantic_owner_bridge_seed_v1(
            base_bridge_seed_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
        )
    )
    belief_action_hint_v1 = _safe_mapping(
        _safe_mapping(belief_state25_runtime_bridge_v1).get("belief_action_hint_v1", {})
    )
    barrier_state25_runtime_bridge_v1 = build_barrier_state25_runtime_bridge_v1(
        _build_semantic_owner_bridge_seed_v1(
            runtime_snapshot_row=runtime_snapshot_row,
            symbol=symbol,
            action=action,
            setup_id=setup_id,
            setup_side=setup_side,
            entry_session_name=entry_session_name,
            wait_state=wait_state,
            entry_wait_decision=entry_wait_decision,
            score=score,
            contra_score=contra_score,
            prediction_bundle=prediction_bundle,
            shadow_transition_forecast_v1=shadow_transition_forecast_v1,
            shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
            observe_confirm_runtime_payload=observe_confirm_runtime_payload,
            state25_candidate_runtime_state=state25_candidate_runtime_state,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
            belief_state25_runtime_bridge_v1=belief_state25_runtime_bridge_v1,
        )
    )
    barrier_action_hint_v1 = _safe_mapping(
        _safe_mapping(barrier_state25_runtime_bridge_v1).get("barrier_action_hint_v1", {})
    )
    countertrend_continuation_signal_v1 = _build_countertrend_continuation_signal_v1(
        symbol=str(symbol),
        action=str(action),
        setup_id=str(setup_id),
        setup_reason=str(setup_reason),
        forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
        belief_action_hint_v1=belief_action_hint_v1,
        barrier_action_hint_v1=barrier_action_hint_v1,
    )
    state25_candidate_context_bridge_v1 = build_state25_candidate_context_bridge_v1(
        _clone_semantic_owner_bridge_seed_v1(
            base_bridge_seed_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
            belief_state25_runtime_bridge_v1=belief_state25_runtime_bridge_v1,
            barrier_state25_runtime_bridge_v1=barrier_state25_runtime_bridge_v1,
            countertrend_continuation_signal_v1=countertrend_continuation_signal_v1,
        )
    )
    breakout_event_overlay_candidates_v1 = build_breakout_event_overlay_candidates_v1(
        _clone_semantic_owner_bridge_seed_v1(
            base_bridge_seed_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
            belief_state25_runtime_bridge_v1=belief_state25_runtime_bridge_v1,
        ),
        breakout_event_runtime_v1=breakout_event_runtime_v1,
        forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
        belief_state25_runtime_bridge_v1=belief_state25_runtime_bridge_v1,
        barrier_state25_runtime_bridge_v1=barrier_state25_runtime_bridge_v1,
    )
    breakout_event_overlay_trace_v1 = build_breakout_event_overlay_trace_v1(
        breakout_event_overlay_candidates_v1,
        symbol=str(symbol),
        entry_stage=str(entry_stage or ""),
    )
    detail_fields = {
        "forecast_state25_runtime_bridge_v1": _safe_mapping(
            forecast_state25_runtime_bridge_v1
        ),
        "breakout_event_runtime_v1": _safe_mapping(breakout_event_runtime_v1),
        "belief_state25_runtime_bridge_v1": _safe_mapping(
            belief_state25_runtime_bridge_v1
        ),
        "barrier_state25_runtime_bridge_v1": _safe_mapping(
            barrier_state25_runtime_bridge_v1
        ),
        "state25_candidate_context_bridge_v1": _safe_mapping(
            state25_candidate_context_bridge_v1
        ),
        "state25_candidate_log_only_trace_v1": _safe_mapping(
            state25_candidate_log_only_trace_v1
        ),
        "forecast_state25_log_only_overlay_trace_v1": _safe_mapping(
            forecast_state25_log_only_overlay_trace_v1
        ),
        "breakout_event_overlay_candidates_v1": _safe_mapping(
            breakout_event_overlay_candidates_v1
        ),
        "breakout_event_overlay_trace_v1": _safe_mapping(
            breakout_event_overlay_trace_v1
        ),
        "countertrend_continuation_signal_v1": _safe_mapping(
            countertrend_continuation_signal_v1
        ),
    }
    flat_fields = _build_semantic_owner_flat_fields_v1(
        state25_candidate_log_only_trace_v1=state25_candidate_log_only_trace_v1,
        forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
        belief_action_hint_v1=belief_action_hint_v1,
        barrier_action_hint_v1=barrier_action_hint_v1,
        countertrend_continuation_signal_v1=countertrend_continuation_signal_v1,
        actual_effective_entry_threshold=actual_effective_entry_threshold,
        actual_size_multiplier=actual_size_multiplier,
    )
    flat_fields.update(
        build_state25_candidate_context_bridge_flat_fields_v1(
            state25_candidate_context_bridge_v1
        )
    )
    return {
        "state25_candidate_context_bridge_v1": _safe_mapping(
            state25_candidate_context_bridge_v1
        ),
        "state25_candidate_log_only_trace_v1": _safe_mapping(
            state25_candidate_log_only_trace_v1
        ),
        "observe_confirm_runtime_payload": _safe_mapping(observe_confirm_runtime_payload),
        "forecast_state25_runtime_bridge_v1": _safe_mapping(
            forecast_state25_runtime_bridge_v1
        ),
        "forecast_state25_log_only_overlay_trace_v1": _safe_mapping(
            forecast_state25_log_only_overlay_trace_v1
        ),
        "breakout_event_runtime_v1": _safe_mapping(breakout_event_runtime_v1),
        "breakout_event_overlay_candidates_v1": _safe_mapping(
            breakout_event_overlay_candidates_v1
        ),
        "breakout_event_overlay_trace_v1": _safe_mapping(
            breakout_event_overlay_trace_v1
        ),
        "belief_state25_runtime_bridge_v1": _safe_mapping(
            belief_state25_runtime_bridge_v1
        ),
        "belief_action_hint_v1": _safe_mapping(belief_action_hint_v1),
        "barrier_state25_runtime_bridge_v1": _safe_mapping(
            barrier_state25_runtime_bridge_v1
        ),
        "barrier_action_hint_v1": _safe_mapping(barrier_action_hint_v1),
        "countertrend_continuation_signal_v1": _safe_mapping(
            countertrend_continuation_signal_v1
        ),
        "detail_fields": detail_fields,
        "flat_fields": flat_fields,
    }


def _build_active_action_conflict_runtime_context_v1(
    *,
    runtime_snapshot_row: object | None,
    symbol: str,
    action: str,
    setup_id: str,
    setup_reason: str = "",
    setup_side: str,
    entry_session_name: str,
    wait_state: object | None,
    entry_wait_decision: str,
    score: float,
    contra_score: float,
    prediction_bundle: object | None,
    shadow_transition_forecast_v1: object | None,
    shadow_trade_management_forecast_v1: object | None,
    shadow_observe_confirm: dict | None,
    entry_stage: str,
    actual_effective_entry_threshold: float,
    actual_size_multiplier: float,
    state25_candidate_runtime_state: object | None,
) -> dict[str, object]:
    semantic_owner_bundle = _build_semantic_owner_runtime_bundle_v1(
        runtime_snapshot_row=runtime_snapshot_row,
        symbol=symbol,
        action=action,
        setup_id=setup_id,
        setup_reason=setup_reason,
        setup_side=setup_side,
        entry_session_name=entry_session_name,
        wait_state=wait_state,
        entry_wait_decision=entry_wait_decision,
        score=score,
        contra_score=contra_score,
        prediction_bundle=prediction_bundle,
        shadow_transition_forecast_v1=shadow_transition_forecast_v1,
        shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
        shadow_observe_confirm=shadow_observe_confirm,
        entry_stage=entry_stage,
        actual_effective_entry_threshold=actual_effective_entry_threshold,
        actual_size_multiplier=actual_size_multiplier,
        state25_candidate_runtime_state=state25_candidate_runtime_state,
    )
    forecast_state25_log_only_overlay_trace_v1 = dict(
        semantic_owner_bundle.get("forecast_state25_log_only_overlay_trace_v1", {}) or {}
    )
    belief_action_hint_v1 = dict(
        semantic_owner_bundle.get("belief_action_hint_v1", {}) or {}
    )
    barrier_action_hint_v1 = dict(
        semantic_owner_bundle.get("barrier_action_hint_v1", {}) or {}
    )
    countertrend_continuation_signal_v1 = dict(
        semantic_owner_bundle.get("countertrend_continuation_signal_v1", {}) or {}
    )
    active_action_conflict_guard_v1 = _build_active_action_conflict_guard_v1(
        symbol=str(symbol),
        baseline_action=str(action or ""),
        setup_id=str(setup_id or ""),
        setup_reason=str(setup_reason or ""),
        runtime_signal_row=_safe_mapping(runtime_snapshot_row),
        forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
        belief_action_hint_v1=belief_action_hint_v1,
        barrier_action_hint_v1=barrier_action_hint_v1,
        countertrend_continuation_signal_v1=countertrend_continuation_signal_v1,
        breakout_event_runtime_v1=_safe_mapping(
            semantic_owner_bundle.get("breakout_event_runtime_v1", {})
        ),
        breakout_event_overlay_candidates_v1=_safe_mapping(
            semantic_owner_bundle.get("breakout_event_overlay_candidates_v1", {})
        ),
    )
    return {
        "semantic_owner_bundle": semantic_owner_bundle,
        "forecast_state25_log_only_overlay_trace_v1": forecast_state25_log_only_overlay_trace_v1,
        "belief_action_hint_v1": belief_action_hint_v1,
        "barrier_action_hint_v1": barrier_action_hint_v1,
        "countertrend_continuation_signal_v1": countertrend_continuation_signal_v1,
        "active_action_conflict_guard_v1": active_action_conflict_guard_v1,
    }


def _resolve_semantic_shadow_activation(
    *,
    semantic_shadow_prediction_v1: dict | None,
    semantic_live_guard_v1: dict | None,
    runtime_diagnostics: dict | None = None,
) -> tuple[str, str]:
    prediction = dict(semantic_shadow_prediction_v1 or {})
    guard = dict(semantic_live_guard_v1 or {})
    diagnostics = dict(runtime_diagnostics or {})

    if bool(prediction.get("available")):
        if not bool(guard.get("symbol_allowed", True)):
            return "active_symbol_blocked", "symbol_not_in_allowlist"
        if not bool(guard.get("entry_stage_allowed", True)):
            return "active_stage_blocked", "entry_stage_not_in_allowlist"
        return "active", "available"

    runtime_reason = str(
        diagnostics.get("reason", "")
        or prediction.get("availability_reason", "")
        or prediction.get("reason", "")
        or ""
    ).strip()
    if runtime_reason:
        return "inactive", runtime_reason
    if not bool(guard.get("symbol_allowed", True)):
        return "inactive", "symbol_not_in_allowlist"
    if not bool(guard.get("entry_stage_allowed", True)):
        return "inactive", "entry_stage_not_in_allowlist"
    return "inactive", "semantic_runtime_unavailable"


def _resolve_semantic_live_threshold_trace(semantic_live_guard_v1: dict | None) -> tuple[str, str]:
    guard = dict(semantic_live_guard_v1 or {})
    if bool(guard.get("threshold_applied")):
        return "applied", "applied"
    state = str(guard.get("threshold_state", "") or "").strip()
    reason = str(
        guard.get("threshold_inactive_reason", "")
        or guard.get("fallback_reason", "")
        or ""
    ).strip()
    if state:
        return state, (reason or state)
    return "not_applied", (reason or "not_applied")


def _resolve_directional_continuation_state_v1(
    *,
    anti_long_score: float,
    anti_short_score: float,
    pro_up_score: float,
    pro_down_score: float,
    owner_family: str = "",
    allow_enter: bool = False,
) -> dict[str, object]:
    anti_long = max(0.0, min(1.0, float(anti_long_score or 0.0)))
    anti_short = max(0.0, min(1.0, float(anti_short_score or 0.0)))
    pro_up = max(0.0, min(1.0, float(pro_up_score or 0.0)))
    pro_down = max(0.0, min(1.0, float(pro_down_score or 0.0)))
    down_bias = round((anti_long * 0.55) + (pro_down * 0.45), 6)
    up_bias = round((anti_short * 0.55) + (pro_up * 0.45), 6)
    watch_threshold = 0.28
    probe_threshold = 0.55
    support_threshold = 0.24
    probe_support_threshold = 0.42
    enter_threshold = 0.82
    enter_support_threshold = 0.78
    bias_margin = 0.03

    directional_bias = "NONE"
    directional_action_state = "DO_NOTHING"
    directional_candidate_action = ""
    directional_execution_action = ""
    directional_state_reason = "no_directional_edge"
    directional_owner_family = ""
    directional_state_rank = 0

    down_enter_ready = bool(
        allow_enter
        and anti_long >= enter_threshold
        and pro_down >= enter_support_threshold
        and down_bias >= (up_bias + bias_margin)
    )
    up_enter_ready = bool(
        allow_enter
        and anti_short >= enter_threshold
        and pro_up >= enter_support_threshold
        and up_bias >= (down_bias + bias_margin)
    )
    down_probe_ready = bool(
        anti_long >= probe_threshold
        and pro_down >= probe_support_threshold
        and down_bias >= (up_bias + bias_margin)
    )
    up_probe_ready = bool(
        anti_short >= probe_threshold
        and pro_up >= probe_support_threshold
        and up_bias >= (down_bias + bias_margin)
    )
    down_watch_ready = bool(
        (anti_long >= watch_threshold or pro_down >= support_threshold)
        and down_bias >= up_bias
    )
    up_watch_ready = bool(
        (anti_short >= watch_threshold or pro_up >= support_threshold)
        and up_bias > down_bias
    )

    if down_enter_ready:
        directional_bias = "DOWN"
        directional_action_state = "DOWN_ENTER"
        directional_candidate_action = "SELL"
        directional_execution_action = "SELL"
        directional_state_reason = "down_enter::anti_long_strong_plus_pro_down_confirmed"
        directional_owner_family = owner_family
        directional_state_rank = 3
    elif up_enter_ready:
        directional_bias = "UP"
        directional_action_state = "UP_ENTER"
        directional_candidate_action = "BUY"
        directional_execution_action = "BUY"
        directional_state_reason = "up_enter::anti_short_strong_plus_pro_up_confirmed"
        directional_owner_family = owner_family
        directional_state_rank = 3
    elif down_probe_ready:
        directional_bias = "DOWN"
        directional_action_state = "DOWN_PROBE"
        directional_candidate_action = "SELL"
        directional_state_reason = "down_probe::anti_long_strong_plus_pro_down_supportive"
        directional_owner_family = owner_family
        directional_state_rank = 2
    elif up_probe_ready:
        directional_bias = "UP"
        directional_action_state = "UP_PROBE"
        directional_candidate_action = "BUY"
        directional_state_reason = "up_probe::anti_short_strong_plus_pro_up_supportive"
        directional_owner_family = owner_family
        directional_state_rank = 2
    elif down_watch_ready:
        directional_bias = "DOWN"
        directional_action_state = "DOWN_WATCH"
        directional_state_reason = "down_watch::anti_long_supportive_or_pro_down_initial"
        directional_owner_family = owner_family
        directional_state_rank = 1
    elif up_watch_ready:
        directional_bias = "UP"
        directional_action_state = "UP_WATCH"
        directional_state_reason = "up_watch::anti_short_supportive_or_pro_up_initial"
        directional_owner_family = owner_family
        directional_state_rank = 1

    return {
        "directional_bias": directional_bias,
        "directional_action_state": directional_action_state,
        "directional_candidate_action": directional_candidate_action,
        "directional_execution_action": directional_execution_action,
        "directional_state_reason": directional_state_reason,
        "directional_owner_family": directional_owner_family,
        "directional_state_rank": int(directional_state_rank),
        "down_bias_score": down_bias,
        "up_bias_score": up_bias,
    }


def _build_countertrend_continuation_signal_v1(
    *,
    symbol: str,
    action: str,
    setup_id: str,
    setup_reason: str,
    forecast_state25_log_only_overlay_trace_v1: dict | None = None,
    belief_action_hint_v1: dict | None = None,
    barrier_action_hint_v1: dict | None = None,
) -> dict[str, object]:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    setup_id_u = str(setup_id or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()
    forecast_reason_u = str(
        ((forecast_state25_log_only_overlay_trace_v1 or {}).get("reason_summary", "")) or ""
    ).lower()
    belief_reason_u = str(((belief_action_hint_v1 or {}).get("reason_summary", "")) or "").lower()
    barrier_reason_u = str(((barrier_action_hint_v1 or {}).get("reason_summary", "")) or "").lower()

    forecast_wait_bias = any(token in forecast_reason_u for token in ("wait_bias_hold", "wait_reinforce"))
    belief_fragile_thesis = any(token in belief_reason_u for token in ("fragile_thesis", "reduce_risk"))
    barrier_wait_block = any(token in barrier_reason_u for token in ("wait_block", "unstable"))
    barrier_relief_watch = any(
        token in barrier_reason_u for token in ("relief_watch", "relief_release_bias")
    )

    xau_countertrend_buy_family = bool(
        symbol_u == "XAUUSD"
        and action_u == "BUY"
        and setup_id_u in {"range_lower_reversal_buy", "trend_pullback_buy"}
        and setup_reason_u in {
            "shadow_lower_rebound_confirm",
            "shadow_failed_sell_reclaim_buy_confirm",
            "shadow_lower_rebound_probe_observe",
            "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
            "shadow_outer_band_reversal_support_required_observe",
            "shadow_outer_band_reversal_support_required_observe_bounded_probe_soft_edge",
        }
    )
    xau_countertrend_sell_family = bool(
        symbol_u == "XAUUSD"
        and action_u == "SELL"
        and setup_id_u == "range_upper_reversal_sell"
        and setup_reason_u in {
            "shadow_upper_reject_probe_observe",
            "shadow_upper_reject_confirm",
            "shadow_upper_break_fail_confirm",
            "upper_break_fail_confirm",
        }
    )
    warning_tokens: list[str] = []
    if xau_countertrend_buy_family:
        if forecast_wait_bias:
            warning_tokens.append("forecast_wait_bias")
        if belief_fragile_thesis:
            warning_tokens.append("belief_fragile_thesis")
        if barrier_wait_block:
            warning_tokens.append("barrier_wait_block")
    elif xau_countertrend_sell_family:
        if forecast_wait_bias:
            warning_tokens.append("forecast_wait_bias")
        if belief_fragile_thesis:
            warning_tokens.append("belief_fragile_thesis")
        if barrier_relief_watch:
            warning_tokens.append("barrier_relief_watch")
    else:
        if forecast_wait_bias:
            warning_tokens.append("forecast_wait_bias")
        if belief_fragile_thesis:
            warning_tokens.append("belief_fragile_thesis")
        if barrier_wait_block:
            warning_tokens.append("barrier_wait_block")
        if barrier_relief_watch:
            warning_tokens.append("barrier_relief_watch")

    warning_count = len(warning_tokens)
    enabled = bool(
        (xau_countertrend_buy_family or xau_countertrend_sell_family) and warning_count >= 2
    )
    watch_only = bool(
        (xau_countertrend_buy_family or xau_countertrend_sell_family) and warning_count == 1
    )
    action_hint = ""
    state = ""
    if xau_countertrend_buy_family:
        action_hint = "SELL" if enabled else ""
        if enabled:
            state = "down_continuation_bias"
        elif watch_only:
            state = "down_continuation_watch"
    elif xau_countertrend_sell_family:
        action_hint = "BUY" if enabled else ""
        if enabled:
            state = "up_continuation_bias"
        elif watch_only:
            state = "up_continuation_watch"
    confidence = 0.0
    if enabled:
        confidence = min(0.92, 0.52 + (0.14 * float(warning_count - 1)))
        if xau_countertrend_buy_family and "forecast_wait_bias" in warning_tokens and "barrier_wait_block" in warning_tokens:
            confidence = min(0.95, confidence + 0.08)
        if xau_countertrend_sell_family and "forecast_wait_bias" in warning_tokens and "barrier_relief_watch" in warning_tokens:
            confidence = min(0.95, confidence + 0.08)
    elif watch_only:
        confidence = 0.46
    anti_long_score = 0.0
    anti_short_score = 0.0
    pro_up_score = 0.0
    pro_down_score = 0.0
    if xau_countertrend_buy_family and warning_tokens:
        if forecast_wait_bias:
            anti_long_score += 0.36
            pro_down_score += 0.34
        if belief_fragile_thesis:
            anti_long_score += 0.32
            pro_down_score += 0.18
        if barrier_wait_block:
            anti_long_score += 0.32
            pro_down_score += 0.30
        if warning_count >= 2:
            pro_down_score += 0.12
        if forecast_wait_bias and barrier_wait_block:
            pro_down_score += 0.08
        anti_long_score = min(1.0, anti_long_score)
        pro_down_score = min(1.0, pro_down_score)
    elif xau_countertrend_sell_family and warning_tokens:
        if forecast_wait_bias:
            anti_short_score += 0.34
            pro_up_score += 0.28
        if belief_fragile_thesis:
            anti_short_score += 0.32
            pro_up_score += 0.18
        if barrier_relief_watch:
            anti_short_score += 0.18
            pro_up_score += 0.38
        if warning_count >= 2:
            pro_up_score += 0.12
        if forecast_wait_bias and barrier_relief_watch:
            pro_up_score += 0.08
        anti_short_score = min(1.0, anti_short_score)
        pro_up_score = min(1.0, pro_up_score)
    directional_state = _resolve_directional_continuation_state_v1(
        anti_long_score=anti_long_score,
        anti_short_score=anti_short_score,
        pro_up_score=pro_up_score,
        pro_down_score=pro_down_score,
        owner_family=(
            "direction_agnostic_continuation"
            if (xau_countertrend_buy_family or xau_countertrend_sell_family)
            else ""
        ),
        allow_enter=False,
    )
    return {
        "contract_version": "countertrend_continuation_signal_v1",
        "enabled": bool(enabled),
        "watch_only": bool(watch_only),
        "signal_family": "countertrend_continuation",
        "signal_state": state,
        "signal_action": action_hint,
        "signal_confidence": round(float(confidence), 6),
        "warning_count": int(warning_count),
        "warning_tokens": list(warning_tokens),
        "reason_summary": "|".join(warning_tokens),
        "surface_family": (
            "follow_through_surface"
            if (xau_countertrend_buy_family or xau_countertrend_sell_family)
            else ""
        ),
        "surface_state": (
            "continuation_follow"
            if (xau_countertrend_buy_family or xau_countertrend_sell_family)
            else ""
        ),
        "anti_long_score": round(float(anti_long_score), 6),
        "anti_short_score": round(float(anti_short_score), 6),
        "pro_up_score": round(float(pro_up_score), 6),
        "pro_down_score": round(float(pro_down_score), 6),
        "directional_bias": str(directional_state.get("directional_bias", "") or ""),
        "directional_action_state": str(
            directional_state.get("directional_action_state", "") or ""
        ),
        "directional_candidate_action": str(
            directional_state.get("directional_candidate_action", "") or ""
        ),
        "directional_execution_action": str(
            directional_state.get("directional_execution_action", "") or ""
        ),
        "directional_state_reason": str(
            directional_state.get("directional_state_reason", "") or ""
        ),
        "directional_owner_family": str(
            directional_state.get("directional_owner_family", "") or ""
        ),
        "directional_state_rank": int(directional_state.get("directional_state_rank", 0) or 0),
        "directional_down_bias_score": float(
            directional_state.get("down_bias_score", 0.0) or 0.0
        ),
        "directional_up_bias_score": float(
            directional_state.get("up_bias_score", 0.0) or 0.0
        ),
    }


def _build_active_action_conflict_guard_flat_fields(
    guard: object | None,
) -> dict[str, object]:
    payload = _safe_mapping(guard)
    return {
        "active_action_conflict_detected": bool(payload.get("conflict_detected", False)),
        "active_action_conflict_guard_eligible": bool(payload.get("guard_eligible", False)),
        "active_action_conflict_guard_applied": bool(payload.get("guard_applied", False)),
        "active_action_conflict_resolution_state": str(
            payload.get("resolution_state", "") or ""
        ),
        "active_action_conflict_kind": str(payload.get("conflict_kind", "") or ""),
        "active_action_conflict_baseline_action": str(
            payload.get("baseline_action", "") or ""
        ),
        "active_action_conflict_directional_action": str(
            payload.get("directional_candidate_action", "") or ""
        ),
        "active_action_conflict_directional_state": str(
            payload.get("directional_action_state", "") or ""
        ),
        "active_action_conflict_directional_bias": str(
            payload.get("directional_bias", "") or ""
        ),
        "active_action_conflict_directional_owner_family": str(
            payload.get("directional_owner_family", "") or ""
        ),
        "active_action_conflict_precedence_owner": str(
            payload.get("precedence_owner", "") or ""
        ),
        "active_action_conflict_up_bias_score": float(
            payload.get("up_bias_score", 0.0) or 0.0
        ),
        "active_action_conflict_down_bias_score": float(
            payload.get("down_bias_score", 0.0) or 0.0
        ),
        "active_action_conflict_bias_gap": float(payload.get("bias_gap", 0.0) or 0.0),
        "active_action_conflict_warning_count": int(
            payload.get("warning_count", 0) or 0
        ),
        "active_action_conflict_breakout_detected": bool(
            payload.get("breakout_conflict_detected", False)
        ),
        "active_action_conflict_breakout_direction": str(
            payload.get("breakout_direction", "") or ""
        ),
        "active_action_conflict_breakout_target": str(
            payload.get("breakout_candidate_target", "") or ""
        ),
        "active_action_conflict_breakout_confidence": float(
            payload.get("breakout_confidence", 0.0) or 0.0
        ),
        "active_action_conflict_breakout_failure_risk": float(
            payload.get("breakout_failure_risk", 0.0) or 0.0
        ),
        "active_action_conflict_overlay_detected": bool(
            payload.get("overlay_conflict_detected", False)
        ),
        "active_action_conflict_overlay_direction": str(
            payload.get("overlay_direction", "") or ""
        ),
        "active_action_conflict_overlay_score": float(
            payload.get("overlay_score", 0.0) or 0.0
        ),
        "active_action_conflict_overlay_selection_state": str(
            payload.get("overlay_selection_state", "") or ""
        ),
        "active_action_conflict_htf_alignment_state": str(
            payload.get("htf_alignment_state", "") or ""
        ),
        "active_action_conflict_context_conflict_state": str(
            payload.get("context_conflict_state", "") or ""
        ),
        "active_action_conflict_failure_code": str(
            payload.get("failure_code", "") or ""
        ),
        "active_action_conflict_failure_label": str(
            payload.get("failure_label", "") or ""
        ),
        "active_action_conflict_reason_summary": str(
            payload.get("reason_summary", "") or ""
        ),
    }


def _build_flow_execution_veto_owner_flat_fields(
    veto: object | None,
) -> dict[str, object]:
    payload = _safe_mapping(veto)
    return {
        "flow_execution_veto_detected": bool(payload.get("veto_detected", False)),
        "flow_execution_veto_applied": bool(payload.get("veto_applied", False)),
        "flow_execution_veto_resolution_state": str(
            payload.get("resolution_state", "") or ""
        ),
        "flow_execution_veto_kind": str(payload.get("veto_kind", "") or ""),
        "flow_execution_veto_baseline_action": str(
            payload.get("baseline_action", "") or ""
        ),
        "flow_execution_veto_slot_core": str(payload.get("slot_core", "") or ""),
        "flow_execution_veto_dominant_side": str(
            payload.get("dominant_side", "") or ""
        ),
        "flow_execution_veto_overlay_direction": str(
            payload.get("overlay_direction", "") or ""
        ),
        "flow_execution_veto_shadow_direction": str(
            payload.get("shadow_direction", "") or ""
        ),
        "flow_execution_veto_gate_state": str(payload.get("gate_state", "") or ""),
        "flow_execution_veto_flow_state": str(payload.get("flow_state", "") or ""),
        "flow_execution_veto_chart_hint": str(payload.get("chart_hint", "") or ""),
        "flow_execution_veto_consumer_side": str(
            payload.get("consumer_side", "") or ""
        ),
        "flow_execution_veto_consumer_entry_ready": bool(
            payload.get("consumer_entry_ready", False)
        ),
        "flow_execution_veto_bearish_evidence_count": int(
            payload.get("bearish_evidence_count", 0) or 0
        ),
        "flow_execution_veto_reason_summary": str(
            payload.get("reason_summary", "") or ""
        ),
    }


def _build_flow_execution_veto_owner_v1(
    *,
    symbol: str,
    baseline_action: str,
    setup_id: str,
    setup_reason: str,
    runtime_signal_row: dict | None = None,
) -> dict[str, object]:
    symbol_u = str(symbol or "").upper().strip()
    runtime_row = dict(runtime_signal_row or {})
    baseline_action_u = _resolve_directional_baseline_action_side_v1(
        baseline_action,
        runtime_row.get("consumer_check_side", ""),
        runtime_row.get("setup_side", ""),
        runtime_row.get("action_selected", ""),
        runtime_row.get("core_allowed_action", ""),
    )
    setup_id_u = str(setup_id or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()
    slot_core = str(runtime_row.get("common_state_slot_core_v1", "") or "").upper().strip()
    dominant_side = str(
        runtime_row.get("dominance_shadow_dominant_side_v1", "") or ""
    ).upper().strip()
    overlay_direction = str(
        runtime_row.get("directional_continuation_overlay_direction", "") or ""
    ).upper().strip()
    shadow_direction = str(
        runtime_row.get("flow_shadow_direction_v1", "") or ""
    ).upper().strip()
    gate_state = str(runtime_row.get("flow_structure_gate_v1", "") or "").upper().strip()
    flow_state = str(runtime_row.get("flow_support_state_v1", "") or "").upper().strip()
    chart_hint = str(runtime_row.get("chart_event_kind_hint", "") or "").upper().strip()
    consumer_side = str(runtime_row.get("consumer_check_side", "") or "").upper().strip()
    consumer_stage = str(runtime_row.get("consumer_check_stage", "") or "").upper().strip()
    consumer_reason = str(runtime_row.get("consumer_check_reason", "") or "").lower().strip()
    consumer_entry_ready = bool(runtime_row.get("consumer_check_entry_ready", False))

    lower_reversal_buy_family = bool(
        baseline_action_u == "BUY"
        and setup_id_u in {"range_lower_reversal_buy", "trend_pullback_buy"}
        and (
            "lower_rebound" in setup_reason_u
            or "lower" in setup_reason_u
            or "reclaim_buy" in setup_reason_u
            or setup_id_u == "range_lower_reversal_buy"
        )
    )
    slot_is_bear_continuation = slot_core.startswith("BEAR_CONTINUATION")
    dominance_is_bear = dominant_side == "BEAR"
    overlay_is_down = overlay_direction == "DOWN"
    shadow_is_sell = shadow_direction == "SELL"
    chart_is_sell = chart_hint.startswith("SELL")
    consumer_is_buy_lower_rebound = bool(
        consumer_side == "BUY"
        and (
            "lower_rebound" in consumer_reason
            or "rebound" in consumer_reason
            or "reclaim" in consumer_reason
        )
    )
    bearish_evidence_count = sum(
        1
        for flag in (
            slot_is_bear_continuation,
            dominance_is_bear,
            overlay_is_down,
            shadow_is_sell,
            chart_is_sell,
        )
        if flag
    )
    veto_detected = bool(
        symbol_u == "BTCUSD"
        and lower_reversal_buy_family
        and bearish_evidence_count >= 3
    )
    veto_applied = bool(
        veto_detected
        and consumer_is_buy_lower_rebound
    )
    veto_kind = "baseline_buy_vs_bear_flow_execution" if veto_detected else ""
    reason_summary = "|".join(
        token
        for token in (
            veto_kind,
            slot_core.lower(),
            dominant_side.lower(),
            f"overlay::{overlay_direction.lower()}" if overlay_direction else "",
            f"shadow::{shadow_direction.lower()}" if shadow_direction else "",
            f"chart::{chart_hint.lower()}" if chart_hint else "",
            (
                f"consumer::{consumer_side.lower()}::{consumer_stage.lower()}::{consumer_reason}"
                if consumer_side or consumer_stage or consumer_reason
                else ""
            ),
            f"gate::{gate_state.lower()}" if gate_state else "",
            f"flow::{flow_state.lower()}" if flow_state else "",
            f"bear_count::{int(bearish_evidence_count)}",
        )
        if token
    )
    return {
        "contract_version": "flow_execution_veto_owner_v1",
        "veto_detected": bool(veto_detected),
        "veto_applied": bool(veto_applied),
        "resolution_state": "WAIT" if veto_applied else "KEEP",
        "baseline_action": str(baseline_action_u),
        "veto_kind": str(veto_kind),
        "slot_core": str(slot_core),
        "dominant_side": str(dominant_side),
        "overlay_direction": str(overlay_direction),
        "shadow_direction": str(shadow_direction),
        "gate_state": str(gate_state),
        "flow_state": str(flow_state),
        "chart_hint": str(chart_hint),
        "consumer_side": str(consumer_side),
        "consumer_stage": str(consumer_stage),
        "consumer_reason": str(consumer_reason),
        "consumer_entry_ready": bool(consumer_entry_ready),
        "bearish_evidence_count": int(bearish_evidence_count),
        "failure_code": "flow_execution_veto_owner" if veto_applied else "",
        "failure_label": "bear_continuation_buy_veto" if veto_applied else "",
        "downgraded_observe_reason": "flow_execution_veto_wait" if veto_applied else "",
        "reason_summary": str(reason_summary),
    }


def _build_flow_execution_selection_owner_flat_fields(
    owner: object | None,
) -> dict[str, object]:
    payload = _safe_mapping(owner)
    return {
        "flow_execution_selection_detected": bool(payload.get("selection_detected", False)),
        "flow_execution_selection_active": bool(payload.get("selection_active", False)),
        "flow_execution_selection_apply_allowed": bool(
            payload.get("execution_apply_allowed", False)
        ),
        "flow_execution_selection_resolution_state": str(
            payload.get("resolution_state", "") or ""
        ),
        "flow_execution_selection_selected_action": str(
            payload.get("selected_action", "") or ""
        ),
        "flow_execution_selection_legacy_action": str(
            payload.get("legacy_action", "") or ""
        ),
        "flow_execution_selection_direction": str(
            payload.get("shadow_direction", "") or ""
        ),
        "flow_execution_selection_chart_hint": str(
            payload.get("chart_hint", "") or ""
        ),
        "flow_execution_selection_gate_state": str(
            payload.get("gate_state", "") or ""
        ),
        "flow_execution_selection_flow_state": str(
            payload.get("flow_state", "") or ""
        ),
        "flow_execution_selection_entry_quality": float(
            payload.get("entry_quality_prob", 0.0) or 0.0
        ),
        "flow_execution_selection_persistence": float(
            payload.get("continuation_persistence_prob", 0.0) or 0.0
        ),
        "flow_execution_selection_reversal_risk": float(
            payload.get("reversal_risk_prob", 0.0) or 0.0
        ),
        "flow_execution_selection_reason_summary": str(
            payload.get("reason_summary", "") or ""
        ),
    }


def _build_flow_execution_selection_owner_v1(
    *,
    symbol: str,
    legacy_action: str,
    runtime_signal_row: dict | None = None,
) -> dict[str, object]:
    symbol_u = str(symbol or "").upper().strip()
    runtime_row = dict(runtime_signal_row or {})
    legacy_action_u = _resolve_directional_baseline_action_side_v1(
        legacy_action,
        runtime_row.get("consumer_check_side", ""),
        runtime_row.get("setup_side", ""),
        runtime_row.get("action_selected", ""),
        runtime_row.get("core_allowed_action", ""),
    )
    shadow_direction = str(
        runtime_row.get("flow_shadow_direction_v1", "") or ""
    ).upper().strip()
    chart_hint = str(runtime_row.get("chart_event_kind_hint", "") or "").upper().strip()
    gate_state = str(runtime_row.get("flow_structure_gate_v1", "") or "").upper().strip()
    flow_state = str(runtime_row.get("flow_support_state_v1", "") or "").upper().strip()
    slot_core = str(runtime_row.get("common_state_slot_core_v1", "") or "").upper().strip()
    dominant_side = str(
        runtime_row.get("dominance_shadow_dominant_side_v1", "") or ""
    ).upper().strip()
    overlay_direction = str(
        runtime_row.get("directional_continuation_overlay_direction", "") or ""
    ).upper().strip()
    try:
        continuation_persistence_prob = max(
            0.0,
            min(
                1.0,
                float(
                    runtime_row.get("flow_shadow_continuation_persistence_prob_v1", 0.0)
                    or 0.0
                ),
            ),
        )
    except (TypeError, ValueError):
        continuation_persistence_prob = 0.0
    try:
        entry_quality_prob = max(
            0.0,
            min(
                1.0,
                float(runtime_row.get("flow_shadow_entry_quality_prob_v1", 0.0) or 0.0),
            ),
        )
    except (TypeError, ValueError):
        entry_quality_prob = 0.0
    try:
        reversal_risk_prob = max(
            0.0,
            min(
                1.0,
                float(runtime_row.get("flow_shadow_reversal_risk_prob_v1", 0.0) or 0.0),
            ),
        )
    except (TypeError, ValueError):
        reversal_risk_prob = 0.0

    selection_detected = False
    selection_active = False
    execution_apply_allowed = False
    selected_action = ""
    resolution_state = "KEEP"

    direction_consistency_count = 0
    if shadow_direction == "SELL":
        direction_consistency_count = sum(
            1
            for flag in (
                slot_core.startswith("BEAR_"),
                dominant_side == "BEAR",
                overlay_direction == "DOWN",
            )
            if flag
        )
        if chart_hint in {"SELL_PROBE", "SELL_READY", "SELL"}:
            selection_detected = True
            selected_action = "SELL"
            execution_apply_allowed = bool(
                symbol_u in {"BTCUSD", "XAUUSD", "NAS100"}
                and direction_consistency_count >= 2
                and gate_state in {"ELIGIBLE", "WEAK"}
                and entry_quality_prob >= 0.42
                and continuation_persistence_prob >= 0.55
                and reversal_risk_prob <= 0.48
            )
            selection_active = bool(execution_apply_allowed)
            resolution_state = "SELECT" if selection_active else "PENDING_HANDOFF"
        elif chart_hint in {"SELL_WAIT", "SELL_WATCH"} or (
            shadow_direction == "SELL"
            and (
                gate_state == "INELIGIBLE"
                or flow_state in {"FLOW_UNCONFIRMED", "FLOW_OPPOSED"}
                or entry_quality_prob < 0.42
            )
        ):
            selection_detected = True
            selection_active = True
            execution_apply_allowed = True
            selected_action = "WAIT"
            resolution_state = "WAIT"
    elif shadow_direction == "BUY":
        direction_consistency_count = sum(
            1
            for flag in (
                slot_core.startswith("BULL_"),
                dominant_side == "BULL",
                overlay_direction == "UP",
            )
            if flag
        )
        if chart_hint in {"BUY_PROBE", "BUY_READY", "BUY"}:
            selection_detected = True
            selected_action = "BUY"
            execution_apply_allowed = bool(
                symbol_u in {"BTCUSD", "XAUUSD", "NAS100"}
                and direction_consistency_count >= 2
                and gate_state in {"ELIGIBLE", "WEAK"}
                and entry_quality_prob >= 0.42
                and continuation_persistence_prob >= 0.55
                and reversal_risk_prob <= 0.48
            )
            selection_active = bool(execution_apply_allowed)
            resolution_state = "SELECT" if selection_active else "PENDING_HANDOFF"
        elif chart_hint in {"BUY_WAIT", "BUY_WATCH"} or (
            shadow_direction == "BUY"
            and (
                gate_state == "INELIGIBLE"
                or flow_state in {"FLOW_UNCONFIRMED", "FLOW_OPPOSED"}
                or entry_quality_prob < 0.42
            )
        ):
            selection_detected = True
            selection_active = True
            execution_apply_allowed = True
            selected_action = "WAIT"
            resolution_state = "WAIT"

    reason_summary = "|".join(
        token
        for token in (
            f"legacy::{legacy_action_u.lower()}" if legacy_action_u else "",
            f"shadow::{shadow_direction.lower()}" if shadow_direction else "",
            f"chart::{chart_hint.lower()}" if chart_hint else "",
            f"slot::{slot_core.lower()}" if slot_core else "",
            f"dominant::{dominant_side.lower()}" if dominant_side else "",
            f"overlay::{overlay_direction.lower()}" if overlay_direction else "",
            f"gate::{gate_state.lower()}" if gate_state else "",
            f"flow::{flow_state.lower()}" if flow_state else "",
            f"entryq::{entry_quality_prob:.2f}",
            f"persist::{continuation_persistence_prob:.2f}",
            f"reversal::{reversal_risk_prob:.2f}",
            f"consistent::{int(direction_consistency_count)}",
            f"selected::{selected_action.lower()}" if selected_action else "",
            f"state::{resolution_state.lower()}",
        )
        if token
    )
    return {
        "contract_version": "flow_execution_selection_owner_v1",
        "selection_detected": bool(selection_detected),
        "selection_active": bool(selection_active),
        "execution_apply_allowed": bool(execution_apply_allowed),
        "resolution_state": str(resolution_state),
        "selected_action": str(selected_action),
        "legacy_action": str(legacy_action_u),
        "shadow_direction": str(shadow_direction),
        "chart_hint": str(chart_hint),
        "gate_state": str(gate_state),
        "flow_state": str(flow_state),
        "slot_core": str(slot_core),
        "dominant_side": str(dominant_side),
        "overlay_direction": str(overlay_direction),
        "continuation_persistence_prob": float(continuation_persistence_prob),
        "entry_quality_prob": float(entry_quality_prob),
        "reversal_risk_prob": float(reversal_risk_prob),
        "failure_code": "flow_execution_selection_owner"
        if selection_active and selected_action == "WAIT"
        else "",
        "failure_label": "flow_selection_wait"
        if selection_active and selected_action == "WAIT"
        else "",
        "downgraded_observe_reason": "flow_selection_owner_wait"
        if selection_active and selected_action == "WAIT"
        else "",
        "reason_summary": str(reason_summary),
    }


def _normalize_breakout_conflict_metrics(
    *,
    breakout_detected: bool,
    breakout_target: str,
    breakout_confidence: float,
    breakout_failure_risk: float,
    breakout_followthrough: float,
) -> tuple[float, float, float]:
    target_u = str(breakout_target or "").upper().strip()
    confidence = float(breakout_confidence or 0.0)
    failure_risk = float(breakout_failure_risk or 0.0)
    followthrough = float(breakout_followthrough or 0.0)
    if not breakout_detected or target_u not in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}:
        return confidence, failure_risk, followthrough

    if confidence <= 0.0:
        confidence = (
            0.30
            if target_u == "WATCH_BREAKOUT"
            else 0.34
            if target_u == "PROBE_BREAKOUT"
            else 0.56
        )
    if failure_risk <= 0.0:
        failure_risk = (
            0.36
            if target_u == "WATCH_BREAKOUT"
            else 0.30
            if target_u == "PROBE_BREAKOUT"
            else 0.22
        )
    if followthrough <= 0.0:
        followthrough = (
            0.10
            if target_u == "WATCH_BREAKOUT"
            else 0.16
            if target_u in {"PROBE_BREAKOUT", "ENTER_NOW"}
            else 0.0
        )
    return confidence, failure_risk, followthrough


def _sync_blocked_by_into_wait_payloads_v1(
    payload_row: Mapping[str, object] | None,
    blocked_by_value: str,
) -> dict[str, object]:
    row_local = dict(payload_row or {})
    blocked_text = str(blocked_by_value or "").strip()
    if not blocked_text:
        return row_local

    wait_context_local = dict(row_local.get("entry_wait_context_v1", {}) or {})
    wait_context_reasons = dict(wait_context_local.get("reasons", {}) or {})
    wait_context_reasons["blocked_by"] = blocked_text
    wait_context_local["reasons"] = wait_context_reasons
    row_local["entry_wait_context_v1"] = wait_context_local

    wait_policy_input_local = dict(row_local.get("entry_wait_state_policy_input_v1", {}) or {})
    wait_policy_reasons = dict(wait_policy_input_local.get("reason_split_v1", {}) or {})
    wait_policy_reasons["blocked_by"] = blocked_text
    wait_policy_input_local["reason_split_v1"] = wait_policy_reasons
    row_local["entry_wait_state_policy_input_v1"] = wait_policy_input_local
    return row_local


def _build_active_action_conflict_guard_v1(
    *,
    symbol: str,
    baseline_action: str,
    setup_id: str,
    setup_reason: str,
    runtime_signal_row: dict | None = None,
    forecast_state25_log_only_overlay_trace_v1: dict | None = None,
    belief_action_hint_v1: dict | None = None,
    barrier_action_hint_v1: dict | None = None,
    countertrend_continuation_signal_v1: dict | None = None,
    breakout_event_runtime_v1: dict | None = None,
    breakout_event_overlay_candidates_v1: dict | None = None,
) -> dict[str, object]:
    symbol_u = str(symbol or "").upper().strip()
    runtime_row = dict(runtime_signal_row or {})
    baseline_action_u = _resolve_directional_baseline_action_side_v1(
        baseline_action,
        runtime_row.get("consumer_check_side", ""),
        runtime_row.get("setup_side", ""),
        runtime_row.get("action_selected", ""),
        runtime_row.get("core_allowed_action", ""),
    )
    setup_id_u = str(setup_id or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()

    conflict_signal = _safe_mapping(countertrend_continuation_signal_v1)
    if not conflict_signal:
        conflict_signal = _build_countertrend_continuation_signal_v1(
            symbol=symbol_u,
            action=baseline_action_u,
            setup_id=setup_id_u,
            setup_reason=setup_reason_u,
            forecast_state25_log_only_overlay_trace_v1=(
                forecast_state25_log_only_overlay_trace_v1
                if forecast_state25_log_only_overlay_trace_v1 is not None
                else {
                    "reason_summary": runtime_row.get("forecast_state25_overlay_reason_summary", "")
                }
            ),
            belief_action_hint_v1=(
                belief_action_hint_v1
                if belief_action_hint_v1 is not None
                else {
                    "reason_summary": runtime_row.get("belief_action_hint_reason_summary", "")
                }
            ),
            barrier_action_hint_v1=(
                barrier_action_hint_v1
                if barrier_action_hint_v1 is not None
                else {
                    "reason_summary": runtime_row.get("barrier_action_hint_reason_summary", "")
                }
            ),
        )
    directional_action = str(
        conflict_signal.get("directional_candidate_action", "") or ""
    ).upper()
    directional_state = str(
        conflict_signal.get("directional_action_state", "") or ""
    ).upper()
    directional_bias = str(conflict_signal.get("directional_bias", "") or "").upper()
    directional_owner_family = str(
        conflict_signal.get("directional_owner_family", "") or ""
    )
    up_bias = float(conflict_signal.get("directional_up_bias_score", 0.0) or 0.0)
    down_bias = float(conflict_signal.get("directional_down_bias_score", 0.0) or 0.0)
    warning_count = int(conflict_signal.get("warning_count", 0) or 0)

    overlay_payload = _safe_mapping(runtime_row.get("directional_continuation_overlay_v1", {}))
    overlay_enabled = _safe_bool_flag(
        overlay_payload.get(
            "overlay_enabled",
            runtime_row.get("directional_continuation_overlay_enabled", False),
        )
    )
    overlay_direction = str(
        overlay_payload.get(
            "overlay_direction",
            runtime_row.get("directional_continuation_overlay_direction", ""),
        )
        or ""
    ).upper()
    overlay_selection_state = str(
        overlay_payload.get(
            "overlay_selection_state",
            runtime_row.get("directional_continuation_overlay_selection_state", ""),
        )
        or ""
    ).upper()
    overlay_event_kind = str(
        overlay_payload.get(
            "overlay_event_kind_hint",
            runtime_row.get("directional_continuation_overlay_event_kind_hint", ""),
        )
        or ""
    ).upper()
    overlay_score = max(
        0.0,
        min(
            1.0,
            float(
                overlay_payload.get(
                    "overlay_score",
                    runtime_row.get("directional_continuation_overlay_score", 0.0),
                )
                or 0.0
            ),
        ),
    )
    htf_alignment_state = str(runtime_row.get("htf_alignment_state", "") or "").upper()
    context_conflict_state = str(runtime_row.get("context_conflict_state", "") or "").upper()
    context_conflict_score = float(runtime_row.get("context_conflict_score", 0.0) or 0.0)
    trend_alignment_count = 0
    for field in ("trend_15m_direction", "trend_1h_direction", "trend_4h_direction", "trend_1d_direction"):
        trend_direction = str(runtime_row.get(field, "") or "").upper().strip()
        if overlay_direction == "UP" and trend_direction == "UPTREND":
            trend_alignment_count += 1
        elif overlay_direction == "DOWN" and trend_direction == "DOWNTREND":
            trend_alignment_count += 1
    structural_context = _build_directional_structural_context_v1(overlay_direction, runtime_row)
    structural_continuation_confirmed = bool(structural_context.get("confirmed", False))
    structural_support_score = float(structural_context.get("score", 0.0) or 0.0)

    breakout_runtime = _safe_mapping(breakout_event_runtime_v1)
    if not breakout_runtime:
        breakout_target_seed = str(
            runtime_row.get("breakout_candidate_action_target", "") or ""
        ).upper()
        breakout_direction_seed = str(
            runtime_row.get("breakout_direction", runtime_row.get("breakout_candidate_direction", ""))
            or ""
        ).upper()
        breakout_detected_seed = str(runtime_row.get("breakout_detected", "") or "").strip().lower()
        inferred_breakout_detected = bool(
            breakout_detected_seed in {"1", "true", "yes", "y", "on"}
            or (
                breakout_target_seed in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
                and breakout_direction_seed in {"UP", "DOWN"}
            )
        )
        inferred_confidence = runtime_row.get(
            "breakout_confidence",
            runtime_row.get("breakout_candidate_confidence", 0.0),
        )
        try:
            inferred_confidence_value = float(inferred_confidence or 0.0)
        except (TypeError, ValueError):
            inferred_confidence_value = 0.0
        if inferred_confidence_value <= 0.0:
            inferred_confidence_value = (
                0.56
                if breakout_target_seed == "ENTER_NOW"
                else 0.34
                if breakout_target_seed == "PROBE_BREAKOUT"
                else 0.30
                if breakout_target_seed == "WATCH_BREAKOUT"
                else 0.0
            )
        inferred_failure_risk = runtime_row.get("breakout_failure_risk", None)
        try:
            inferred_failure_risk_value = float(inferred_failure_risk)
        except (TypeError, ValueError):
            inferred_failure_risk_value = (
                0.22
                if breakout_target_seed == "ENTER_NOW"
                else 0.30
                if breakout_target_seed == "PROBE_BREAKOUT"
                else 0.36
                if breakout_target_seed == "WATCH_BREAKOUT"
                else 1.0
            )
        inferred_followthrough = runtime_row.get("breakout_followthrough_score", None)
        try:
            inferred_followthrough_value = float(inferred_followthrough)
        except (TypeError, ValueError):
            inferred_followthrough_value = (
                0.16
                if breakout_target_seed in {"ENTER_NOW", "PROBE_BREAKOUT"}
                else 0.10
                if breakout_target_seed == "WATCH_BREAKOUT"
                else 0.0
            )
        breakout_runtime = {
            "available": bool(inferred_breakout_detected),
            "breakout_detected": bool(inferred_breakout_detected),
            "breakout_direction": str(breakout_direction_seed),
            "breakout_confidence": float(inferred_confidence_value),
            "breakout_failure_risk": float(inferred_failure_risk_value),
            "breakout_followthrough_score": float(inferred_followthrough_value),
        }
    breakout_overlay = _safe_mapping(breakout_event_overlay_candidates_v1)
    if not breakout_overlay:
        breakout_target_seed = str(
            runtime_row.get("breakout_candidate_action_target", "") or ""
        ).upper()
        breakout_overlay = {
            "enabled": breakout_target_seed in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"},
            "candidate_action_target": breakout_target_seed,
            "reason_summary": str(runtime_row.get("breakout_candidate_reason", "") or ""),
        }
    breakout_direction = str(
        breakout_runtime.get("breakout_direction", breakout_overlay.get("breakout_direction", "")) or ""
    ).upper()
    breakout_target = str(breakout_overlay.get("candidate_action_target", "") or "").upper()
    breakout_confidence = float(
        breakout_runtime.get("breakout_confidence", runtime_row.get("breakout_candidate_confidence", 0.0))
        or 0.0
    )
    breakout_failure_risk = float(
        breakout_runtime.get("breakout_failure_risk", runtime_row.get("breakout_failure_risk", 1.0))
        or 0.0
    )
    breakout_followthrough = float(
        breakout_runtime.get("breakout_followthrough_score", runtime_row.get("breakout_followthrough_score", 0.0))
        or 0.0
    )
    breakout_detected = bool(breakout_runtime.get("breakout_detected", False))
    breakout_enabled = bool(breakout_overlay.get("enabled", False))
    breakout_confidence, breakout_failure_risk, breakout_followthrough = (
        _normalize_breakout_conflict_metrics(
            breakout_detected=breakout_detected,
            breakout_target=breakout_target,
            breakout_confidence=breakout_confidence,
            breakout_failure_risk=breakout_failure_risk,
            breakout_followthrough=breakout_followthrough,
        )
    )

    upper_reversal_sell_family = bool(
        symbol_u == "XAUUSD"
        and baseline_action_u == "SELL"
        and setup_id_u == "range_upper_reversal_sell"
        and setup_reason_u
        in {
            "shadow_upper_reject_probe_observe",
            "shadow_upper_reject_confirm",
            "shadow_upper_break_fail_confirm",
            "upper_break_fail_confirm",
        }
    )
    lower_reversal_buy_family = bool(
        symbol_u == "XAUUSD"
        and baseline_action_u == "BUY"
        and setup_id_u in {"range_lower_reversal_buy", "trend_pullback_buy"}
        and setup_reason_u
        in {
            "shadow_lower_rebound_confirm",
            "shadow_failed_sell_reclaim_buy_confirm",
            "shadow_lower_rebound_probe_observe",
            "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
            "shadow_outer_band_reversal_support_required_observe",
            "shadow_outer_band_reversal_support_required_observe_bounded_probe_soft_edge",
        }
    )
    directional_is_up = directional_action == "BUY" and directional_state in {
        "UP_WATCH",
        "UP_PROBE",
        "UP_ENTER",
    }
    directional_is_down = directional_action == "SELL" and directional_state in {
        "DOWN_WATCH",
        "DOWN_PROBE",
        "DOWN_ENTER",
    }
    breakout_is_up = bool(
        breakout_enabled
        and breakout_detected
        and breakout_direction == "UP"
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    breakout_is_down = bool(
        breakout_enabled
        and breakout_detected
        and breakout_direction == "DOWN"
        and breakout_target in {"WATCH_BREAKOUT", "PROBE_BREAKOUT", "ENTER_NOW"}
    )
    overlay_is_up = bool(
        overlay_enabled
        and overlay_direction == "UP"
        and overlay_selection_state in {"UP_SELECTED", "UP_CONFIRM", "UP"}
        and overlay_event_kind in {"BUY_WATCH", "BUY_READY", "BUY"}
    )
    overlay_is_down = bool(
        overlay_enabled
        and overlay_direction == "DOWN"
        and overlay_selection_state in {"DOWN_SELECTED", "DOWN_CONFIRM", "DOWN"}
        and overlay_event_kind in {"SELL_WATCH", "SELL_READY", "SELL"}
    )
    overlay_conflict_detected = bool(
        (baseline_action_u == "SELL" and overlay_is_up)
        or (baseline_action_u == "BUY" and overlay_is_down)
    )
    overlay_context_confirmed = bool(
        htf_alignment_state == "WITH_HTF"
        and (
            context_conflict_state in {"AGAINST_HTF", "AGAINST_PREV_BOX", "AGAINST_PREV_BOX_AND_HTF"}
            or context_conflict_score >= 0.65
        )
    )

    conflict_detected = bool(
        (upper_reversal_sell_family and directional_is_up)
        or (lower_reversal_buy_family and directional_is_down)
        or (baseline_action_u == "SELL" and breakout_is_up)
        or (baseline_action_u == "BUY" and breakout_is_down)
        or overlay_conflict_detected
    )
    bias_gap = 0.0
    conflict_kind = ""
    failure_label = ""
    precedence_owner = ""
    breakout_conflict_detected = False
    breakout_guard_eligible = False
    breakout_reason_summary = str(breakout_overlay.get("reason_summary", "") or "")
    breakout_signal_gap = round(max(0.0, breakout_confidence - breakout_failure_risk), 6)
    breakout_watch_ready = bool(
        breakout_target == "WATCH_BREAKOUT"
        and breakout_confidence >= 0.28
        and breakout_failure_risk <= 0.40
        and breakout_followthrough >= 0.08
    )
    breakout_probe_ready = bool(
        breakout_target in {"PROBE_BREAKOUT", "ENTER_NOW"}
        and breakout_confidence >= 0.18
        and breakout_failure_risk <= 0.50
        and breakout_followthrough >= 0.08
    )
    if upper_reversal_sell_family and directional_is_up:
        bias_gap = round(max(0.0, up_bias - down_bias), 6)
        conflict_kind = "baseline_sell_vs_up_directional"
        failure_label = "wrong_side_sell_pressure"
    elif lower_reversal_buy_family and directional_is_down:
        bias_gap = round(max(0.0, down_bias - up_bias), 6)
        conflict_kind = "baseline_buy_vs_down_directional"
        failure_label = "wrong_side_buy_pressure"
    elif baseline_action_u == "SELL" and breakout_is_up:
        breakout_conflict_detected = True
        bias_gap = float(breakout_signal_gap)
        conflict_kind = "baseline_sell_vs_up_breakout"
        failure_label = "wrong_side_sell_pressure"
    elif baseline_action_u == "BUY" and breakout_is_down:
        breakout_conflict_detected = True
        bias_gap = float(breakout_signal_gap)
        conflict_kind = "baseline_buy_vs_down_breakout"
        failure_label = "wrong_side_buy_pressure"
    elif baseline_action_u == "SELL" and overlay_is_up:
        bias_gap = float(overlay_score)
        conflict_kind = "baseline_sell_vs_up_continuation_overlay"
        failure_label = "wrong_side_sell_pressure"
    elif baseline_action_u == "BUY" and overlay_is_down:
        bias_gap = float(overlay_score)
        conflict_kind = "baseline_buy_vs_down_continuation_overlay"
        failure_label = "wrong_side_buy_pressure"

    if baseline_action_u == "SELL" and breakout_is_up:
        breakout_conflict_detected = True
    elif baseline_action_u == "BUY" and breakout_is_down:
        breakout_conflict_detected = True

    directional_guard_eligible = bool(
        conflict_detected
        and warning_count >= 2
        and (
            (upper_reversal_sell_family and up_bias >= 0.60 and bias_gap >= 0.10)
            or (lower_reversal_buy_family and down_bias >= 0.60 and bias_gap >= 0.10)
        )
    )
    breakout_guard_eligible = bool(
        breakout_conflict_detected
        and (
            breakout_probe_ready
            or breakout_watch_ready
        )
    )
    overlay_guard_eligible = bool(
        overlay_conflict_detected
        and (
            (
                overlay_context_confirmed
                and overlay_score >= 0.72
            )
            or (
                overlay_score >= 0.60
                and htf_alignment_state == "WITH_HTF"
                and context_conflict_score >= 0.75
                and trend_alignment_count >= 3
            )
            or (
                structural_continuation_confirmed
                and overlay_score >= 0.56
            )
            or (
                structural_support_score >= 0.58
                and overlay_score >= 0.50
                and htf_alignment_state == "WITH_HTF"
                and trend_alignment_count >= 2
            )
        )
    )
    guard_eligible = bool(directional_guard_eligible or breakout_guard_eligible or overlay_guard_eligible)
    if directional_guard_eligible and breakout_guard_eligible and overlay_guard_eligible:
        precedence_owner = "directional_breakout_overlay"
    elif directional_guard_eligible and breakout_guard_eligible:
        precedence_owner = "directional_breakout"
    elif breakout_guard_eligible and overlay_guard_eligible:
        precedence_owner = "breakout_overlay"
    elif directional_guard_eligible and overlay_guard_eligible:
        precedence_owner = "directional_overlay"
    elif directional_guard_eligible:
        precedence_owner = "directional"
    elif breakout_guard_eligible:
        precedence_owner = "breakout"
    elif overlay_guard_eligible:
        precedence_owner = "overlay"
    resolution_state = "KEEP"
    if guard_eligible:
        resolution_state = (
            "PROBE"
            if precedence_owner in {"breakout", "directional_breakout", "breakout_overlay", "directional_breakout_overlay"}
            and breakout_target in {"PROBE_BREAKOUT", "ENTER_NOW"}
            else "WATCH"
        )
    guard_applied = bool(guard_eligible)
    failure_code = "active_action_conflict_guard" if guard_applied else ""
    directional_state_reason = str(
        conflict_signal.get("directional_state_reason", "") or ""
    )
    reason_summary = "|".join(
        token
        for token in (
            conflict_kind,
            str(conflict_signal.get("reason_summary", "") or ""),
            directional_state_reason,
            breakout_reason_summary,
            (
                f"overlay::{overlay_direction.lower()}::{overlay_selection_state.lower()}::{overlay_score:.2f}"
                if overlay_conflict_detected
                else ""
            ),
        )
        if token
    )
    return {
        "contract_version": "active_action_conflict_guard_v1",
        "conflict_detected": bool(conflict_detected),
        "guard_eligible": bool(guard_eligible),
        "guard_applied": bool(guard_applied),
        "resolution_state": str(resolution_state),
        "baseline_action": str(baseline_action_u),
        "directional_candidate_action": str(directional_action),
        "directional_action_state": str(directional_state),
        "directional_bias": str(directional_bias),
        "directional_owner_family": str(directional_owner_family),
        "precedence_owner": str(precedence_owner),
        "up_bias_score": float(up_bias),
        "down_bias_score": float(down_bias),
        "bias_gap": float(bias_gap),
        "warning_count": int(warning_count),
        "warning_tokens": list(conflict_signal.get("warning_tokens", []) or []),
        "breakout_conflict_detected": bool(breakout_conflict_detected),
        "breakout_direction": str(breakout_direction),
        "breakout_candidate_target": str(breakout_target),
        "breakout_confidence": float(breakout_confidence),
        "breakout_failure_risk": float(breakout_failure_risk),
        "overlay_conflict_detected": bool(overlay_conflict_detected),
        "overlay_direction": str(overlay_direction),
        "overlay_selection_state": str(overlay_selection_state),
        "overlay_event_kind_hint": str(overlay_event_kind),
        "overlay_score": float(overlay_score),
        "overlay_guard_eligible": bool(overlay_guard_eligible),
        "structural_continuation_confirmed": bool(structural_continuation_confirmed),
        "structural_support_score": float(structural_support_score),
        "htf_alignment_state": str(htf_alignment_state),
        "context_conflict_state": str(context_conflict_state),
        "context_conflict_score": float(context_conflict_score),
        "trend_alignment_count": int(trend_alignment_count),
        "conflict_kind": str(conflict_kind),
        "failure_code": str(failure_code),
        "failure_label": str(failure_label),
        "downgraded_observe_reason": (
            (
                "breakout_conflict_probe"
                if guard_applied and precedence_owner == "breakout" and resolution_state == "PROBE"
                else "breakout_conflict_watch"
                if guard_applied and precedence_owner == "breakout"
                else "directional_conflict_watch"
                if guard_applied
                else ""
            )
        ),
        "reason_summary": str(reason_summary),
        "countertrend_continuation_signal_v1": _safe_mapping(conflict_signal),
    }


def _resolve_range_lower_buy_shadow_relief(
    *,
    symbol: str,
    core_reason: str,
    setup_reason: str,
    box_state: str,
    bb_state: str,
    wait_conflict: float,
    wait_noise: float,
    wait_score: float,
    preflight_allowed_action: str,
    compatibility_mode: str = "",
    semantic_shadow_prediction_v1: dict | None = None,
    entry_probe_plan_v1: dict | None = None,
    runtime_signal_row: dict | None = None,
) -> tuple[bool, str]:
    symbol_u = str(symbol or "").upper().strip()
    core_reason_u = str(core_reason or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()
    box_state_u = str(box_state or "").upper().strip()
    bb_state_u = str(bb_state or "").upper().strip()
    preflight_u = str(preflight_allowed_action or "").upper().strip()
    compatibility_mode_u = str(compatibility_mode or "").strip().lower()
    plan = dict(entry_probe_plan_v1 or {})
    runtime_row = dict(runtime_signal_row or {})

    countertrend_signal_v1 = _build_countertrend_continuation_signal_v1(
        symbol=symbol_u,
        action="BUY",
        setup_id="range_lower_reversal_buy",
        setup_reason=setup_reason_u,
        forecast_state25_log_only_overlay_trace_v1={
            "reason_summary": runtime_row.get("forecast_state25_overlay_reason_summary", "")
        },
        belief_action_hint_v1={
            "reason_summary": runtime_row.get("belief_action_hint_reason_summary", "")
        },
        barrier_action_hint_v1={
            "reason_summary": runtime_row.get("barrier_action_hint_reason_summary", "")
        },
    )
    xau_countertrend_warning_veto = bool(countertrend_signal_v1.get("enabled", False))

    confirm_allow = bool(
        core_reason_u == "core_shadow_confirm_action"
        and setup_reason_u in {
            "shadow_lower_rebound_confirm",
            "shadow_failed_sell_reclaim_buy_confirm",
            "shadow_box_bb20_conflict_lower_support_confirm",
        }
        and box_state_u in {"LOWER", "MIDDLE"}
        and bb_state_u in {"LOWER_EDGE", "MID", "UNKNOWN"}
        and float(wait_conflict) <= 20.0
        and float(wait_noise) <= 24.0
        and float(wait_score) <= 70.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
    )
    if confirm_allow:
        return True, "soft_edge"

    native_probe_allow = bool(
        symbol_u == "BTCUSD"
        and core_reason_u in {"core_shadow_observe_wait", "core_shadow_probe_action", "energy_soft_block"}
        and setup_reason_u == "shadow_lower_rebound_probe_observe"
        and box_state_u in {"LOWER", "MIDDLE", "BELOW"}
        and bb_state_u in {"MID", "UNKNOWN", "LOWER_EDGE", "BREAKDOWN"}
        and float(wait_conflict) <= 20.0
        and float(wait_noise) <= 16.0
        and float(wait_score) <= 48.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u == "native_v2"
    )
    if native_probe_allow:
        return True, "native_probe"

    nas_native_probe_allow = bool(
        symbol_u == "NAS100"
        and core_reason_u in {"core_shadow_probe_action", "core_shadow_observe_wait"}
        and setup_reason_u in {
            "shadow_lower_rebound_probe_observe",
            "shadow_middle_sr_anchor_required_observe",
            "shadow_outer_band_reversal_support_required_observe",
        }
        and box_state_u in {"LOWER", "MIDDLE"}
        and bb_state_u in {"MID", "UNKNOWN", "LOWER_EDGE"}
        and float(wait_conflict) <= 18.0
        and float(wait_noise) <= 16.0
        and float(wait_score) <= 52.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u == "native_v2"
    )
    if nas_native_probe_allow:
        return True, "nas_native_probe"

    nas_lower_breakdown_probe_allow = bool(
        symbol_u == "NAS100"
        and core_reason_u in {"core_shadow_probe_action", "core_shadow_observe_wait"}
        and setup_reason_u == "shadow_lower_rebound_probe_observe"
        and box_state_u in {"LOWER", "BELOW", "MIDDLE"}
        and bb_state_u in {"LOWER_EDGE", "BREAKDOWN"}
        and float(wait_conflict) <= 18.0
        and float(wait_noise) <= 18.0
        and float(wait_score) <= 54.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u == "native_v2"
    )
    if nas_lower_breakdown_probe_allow:
        return True, "nas_lower_breakdown_probe"

    xau_outer_band_follow_through_allow = bool(
        (not xau_countertrend_warning_veto)
        and symbol_u == "XAUUSD"
        and core_reason_u in {"core_shadow_observe_wait", "core_shadow_probe_action", "energy_soft_block"}
        and setup_reason_u == "shadow_outer_band_reversal_support_required_observe"
        and box_state_u in {"LOWER", "MIDDLE"}
        and bb_state_u in {"MID", "UNKNOWN", "LOWER_EDGE"}
        and float(wait_conflict) <= 22.0
        and float(wait_noise) <= 18.0
        and float(wait_score) <= 58.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u == "native_v2"
        and bool(plan.get("active", False))
        and str(plan.get("intended_action", "") or "").strip().upper() == "BUY"
        and bool(plan.get("default_side_aligned", False))
        and (
            bool(plan.get("structural_relief_applied", False))
            or bool(plan.get("near_confirm", False))
            or float(pd.to_numeric(plan.get("pair_gap"), errors="coerce") or 0.0) >= 0.18
        )
        and float(pd.to_numeric(plan.get("candidate_support"), errors="coerce") or 0.0) >= 0.14
        and float(pd.to_numeric(plan.get("action_confirm_score"), errors="coerce") or 0.0) >= 0.10
        and float(pd.to_numeric(plan.get("confirm_fake_gap"), errors="coerce") or 0.0) >= -0.18
        and float(pd.to_numeric(plan.get("wait_confirm_gap"), errors="coerce") or 0.0) >= -0.05
        and float(pd.to_numeric(plan.get("continue_fail_gap"), errors="coerce") or 0.0) >= -0.22
        and float(pd.to_numeric(plan.get("same_side_barrier"), errors="coerce") or 1.0) <= 0.66
    )
    if xau_outer_band_follow_through_allow:
        return True, "xau_outer_band_follow_through"

    xau_lower_rebound_follow_through_allow = bool(
        (not xau_countertrend_warning_veto)
        and symbol_u == "XAUUSD"
        and core_reason_u in {"core_shadow_observe_wait", "core_shadow_probe_action", "energy_soft_block"}
        and setup_reason_u in {
            "shadow_lower_rebound_probe_observe",
            "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
            "shadow_outer_band_reversal_support_required_observe",
        }
        and box_state_u in {"LOWER", "MIDDLE", "BELOW"}
        and bb_state_u in {"MID", "UNKNOWN", "LOWER_EDGE", "BREAKDOWN"}
        and float(wait_conflict) <= 24.0
        and float(wait_noise) <= 18.0
        and float(wait_score) <= 62.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u == "native_v2"
        and bool(plan.get("active", False))
        and str(plan.get("intended_action", "") or "").strip().upper() == "BUY"
        and bool(plan.get("default_side_aligned", False))
        and (
            bool(plan.get("structural_relief_applied", False))
            or bool(plan.get("near_confirm", False))
            or float(pd.to_numeric(plan.get("pair_gap"), errors="coerce") or 0.0) >= 0.16
        )
        and float(pd.to_numeric(plan.get("candidate_support"), errors="coerce") or 0.0) >= 0.13
        and float(pd.to_numeric(plan.get("action_confirm_score"), errors="coerce") or 0.0) >= 0.09
        and float(pd.to_numeric(plan.get("confirm_fake_gap"), errors="coerce") or 0.0) >= -0.20
        and float(pd.to_numeric(plan.get("wait_confirm_gap"), errors="coerce") or 0.0) >= -0.10
        and float(pd.to_numeric(plan.get("continue_fail_gap"), errors="coerce") or 0.0) >= -0.24
        and float(pd.to_numeric(plan.get("same_side_barrier"), errors="coerce") or 1.0) <= 0.74
    )
    if xau_lower_rebound_follow_through_allow:
        return True, "xau_lower_rebound_follow_through"

    if (
        xau_countertrend_warning_veto
        and setup_reason_u in {
            "shadow_lower_rebound_probe_observe",
            "shadow_lower_rebound_probe_observe_bounded_probe_soft_edge",
            "shadow_outer_band_reversal_support_required_observe",
        }
    ):
        return False, "xau_countertrend_warning_veto"

    bounded_probe_soft_edge_allow = bool(
        symbol_u in {"BTCUSD", "NAS100", "XAUUSD"}
        and core_reason_u in {"core_shadow_observe_wait", "core_shadow_probe_action", "energy_soft_block"}
        and setup_reason_u in {
            "shadow_lower_rebound_probe_observe",
            "shadow_middle_sr_anchor_required_observe",
            "shadow_outer_band_reversal_support_required_observe",
        }
        and box_state_u in {"LOWER", "MIDDLE", "BELOW"}
        and bb_state_u in {"MID", "UNKNOWN", "LOWER_EDGE", "BREAKDOWN"}
        and float(wait_conflict) <= 24.0
        and float(wait_noise) <= 18.0
        and float(wait_score) <= 60.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and bool(plan.get("active", False))
        and str(plan.get("intended_action", "") or "").strip().upper() == "BUY"
        and bool(plan.get("default_side_aligned", False))
        and (
            bool(plan.get("near_confirm", False))
            or float(pd.to_numeric(plan.get("pair_gap"), errors="coerce") or 0.0) >= 0.15
        )
        and float(pd.to_numeric(plan.get("candidate_support"), errors="coerce") or 0.0) >= 0.10
        and float(pd.to_numeric(plan.get("action_confirm_score"), errors="coerce") or 0.0) >= 0.08
        and float(pd.to_numeric(plan.get("confirm_fake_gap"), errors="coerce") or 0.0) >= -0.26
        and float(pd.to_numeric(plan.get("wait_confirm_gap"), errors="coerce") or 0.0) >= -0.21
        and float(pd.to_numeric(plan.get("continue_fail_gap"), errors="coerce") or 0.0) >= -0.30
        and float(pd.to_numeric(plan.get("same_side_barrier"), errors="coerce") or 1.0) <= 0.60
    )
    if bounded_probe_soft_edge_allow:
        return True, "bounded_probe_soft_edge"

    timing_prob = 0.0
    entry_prob = 0.0
    prediction = dict(semantic_shadow_prediction_v1 or {})
    try:
        timing_prob = float(((prediction.get("timing", {}) or {}).get("probability")) or 0.0)
    except (TypeError, ValueError):
        timing_prob = 0.0
    try:
        entry_prob = float(((prediction.get("entry_quality", {}) or {}).get("probability")) or 0.0)
    except (TypeError, ValueError):
        entry_prob = 0.0

    probe_allow = bool(
        symbol_u == "BTCUSD"
        and core_reason_u == "core_shadow_probe_action"
        and setup_reason_u == "shadow_lower_rebound_probe_observe"
        and box_state_u == "LOWER"
        and bb_state_u in {"BREAKDOWN", "LOWER_EDGE"}
        and float(wait_conflict) <= 20.0
        and float(wait_noise) <= 4.0
        and float(wait_score) <= 90.0
        and preflight_u in {"BOTH", "BUY_ONLY"}
        and compatibility_mode_u in {"", "observe_confirm_v1_fallback"}
        and timing_prob >= 0.96
        and entry_prob >= 0.90
    )
    if probe_allow:
        return True, "semantic_probe"
    return False, ""


def _should_block_range_lower_buy_dual_bear_context(
    *,
    symbol: str,
    action: str,
    setup_id: str,
    h1_gate_pass: bool,
    topdown_gate_pass: bool,
) -> bool:
    symbol_u = str(symbol or "").upper().strip()
    action_u = str(action or "").upper().strip()
    setup_u = str(setup_id or "").lower().strip()
    if symbol_u not in {"BTCUSD", "NAS100"}:
        return False
    if action_u != "BUY":
        return False
    if setup_u != "range_lower_reversal_buy":
        return False
    return (not bool(h1_gate_pass)) and (not bool(topdown_gate_pass))


def _resolve_semantic_probe_bridge_action(
    *,
    symbol: str,
    core_reason: str,
    observe_reason: str,
    action_none_reason: str,
    blocked_by: str,
    compatibility_mode: str = "",
    entry_probe_plan_v1: dict | None = None,
    default_side_gate_v1: dict | None = None,
    probe_candidate_v1: dict | None = None,
    semantic_shadow_prediction_v1: dict | None = None,
) -> tuple[str, str]:
    symbol_u = str(symbol or "").upper().strip()
    core_reason_u = str(core_reason or "").lower().strip()
    observe_reason_u = str(observe_reason or "").lower().strip()
    none_reason_u = str(action_none_reason or "").lower().strip()
    blocked_by_u = str(blocked_by or "").lower().strip()
    compatibility_mode_u = str(compatibility_mode or "").lower().strip()
    plan = dict(entry_probe_plan_v1 or {})
    probe_candidate = dict(probe_candidate_v1 or {})
    prediction = dict(semantic_shadow_prediction_v1 or {})

    probe_action = str(
        plan.get("intended_action", "") or plan.get("candidate_side_hint", "") or ""
    ).upper().strip()
    plan_reason_u = str(plan.get("reason", "") or "").lower().strip()
    plan_active = bool(plan.get("active", False))
    plan_ready = bool(plan.get("ready_for_entry", False))
    default_side_aligned = bool(plan.get("default_side_aligned", False))

    def _float_value(name: str) -> float:
        try:
            return float(pd.to_numeric(plan.get(name), errors="coerce") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    try:
        timing_prob = float(((prediction.get("timing", {}) or {}).get("probability")) or 0.0)
    except (TypeError, ValueError):
        timing_prob = 0.0
    try:
        entry_prob = float(((prediction.get("entry_quality", {}) or {}).get("probability")) or 0.0)
    except (TypeError, ValueError):
        entry_prob = 0.0

    allow_btc_lower_probe_bridge = bool(
        symbol_u == "BTCUSD"
        and core_reason_u == "core_shadow_observe_wait"
        and observe_reason_u == "lower_rebound_probe_observe"
        and none_reason_u == "probe_not_promoted"
        and probe_action == "BUY"
        and plan_active
        and not plan_ready
        and default_side_aligned
        and plan_reason_u in {
            "probe_pair_gap_not_ready",
            "probe_forecast_not_ready",
            "probe_belief_not_ready",
            "probe_barrier_blocked",
        }
        and blocked_by_u in {"", "forecast_guard"}
        and compatibility_mode_u in {"", "observe_confirm_v1_fallback"}
        and timing_prob >= 0.97
        and entry_prob >= 0.93
        and _float_value("candidate_support") >= 0.24
        and _float_value("action_confirm_score") >= 0.12
        and _float_value("confirm_fake_gap") >= -0.24
        and _float_value("wait_confirm_gap") >= -0.18
        and _float_value("continue_fail_gap") >= -0.30
        and _float_value("same_side_barrier") <= 0.55
    )
    if allow_btc_lower_probe_bridge:
        return "BUY", "btc_lower_rebound_semantic_probe_bridge"

    allow_btc_lower_native_probe_bridge = bool(
        symbol_u == "BTCUSD"
        and core_reason_u in {"core_shadow_observe_wait", "energy_soft_block"}
        and observe_reason_u == "lower_rebound_probe_observe"
        and none_reason_u == "probe_not_promoted"
        and probe_action == "BUY"
        and plan_active
        and not plan_ready
        and default_side_aligned
        and plan_reason_u in {
            "probe_pair_gap_not_ready",
            "probe_forecast_not_ready",
            "probe_belief_not_ready",
            "probe_barrier_blocked",
        }
        and blocked_by_u in {"", "forecast_guard", "middle_sr_anchor_guard"}
        and compatibility_mode_u == "native_v2"
        and _float_value("candidate_support") >= 0.14
        and _float_value("pair_gap") >= 0.18
        and _float_value("action_confirm_score") >= 0.08
        and _float_value("confirm_fake_gap") >= -0.26
        and _float_value("wait_confirm_gap") >= -0.21
        and _float_value("continue_fail_gap") >= -0.30
        and _float_value("same_side_barrier") <= 0.62
        and (bool(plan.get("near_confirm", False)) or _float_value("pair_gap") >= 0.22)
    )
    if allow_btc_lower_native_probe_bridge:
        return "BUY", "btc_lower_rebound_native_probe_bridge"

    allow_nas_clean_confirm_native_probe_bridge = bool(
        symbol_u == "NAS100"
        and core_reason_u == "core_shadow_observe_wait"
        and observe_reason_u == "middle_sr_anchor_required_observe"
        and none_reason_u == "probe_not_promoted"
        and blocked_by_u == "middle_sr_anchor_guard"
        and probe_action in {"BUY", "SELL"}
        and plan_active
        and not plan_ready
        and default_side_aligned
        and plan_reason_u == "probe_forecast_not_ready"
        and str(plan.get("symbol_scene_relief", "") or "").strip().lower() == "nas_clean_confirm_probe"
        and compatibility_mode_u == "native_v2"
        and bool(plan.get("near_confirm", False))
        and _float_value("candidate_support") >= 0.11
        and _float_value("pair_gap") >= 0.17
        and _float_value("action_confirm_score") >= 0.08
        and _float_value("confirm_fake_gap") >= -0.26
        and _float_value("wait_confirm_gap") >= -0.21
        and _float_value("continue_fail_gap") >= -0.28
        and _float_value("same_side_barrier") <= 0.56
    )
    if allow_nas_clean_confirm_native_probe_bridge:
        return probe_action, "nas_clean_confirm_native_probe_bridge"

    allow_nas_clean_confirm_lower_rebound_ready_bridge = bool(
        symbol_u == "NAS100"
        and core_reason_u in {"core_shadow_observe_wait", "energy_soft_block"}
        and observe_reason_u == "lower_rebound_probe_observe"
        and none_reason_u in {"probe_not_promoted", "execution_soft_blocked"}
        and blocked_by_u in {"forecast_guard", "energy_soft_block"}
        and probe_action == "BUY"
        and plan_active
        and plan_ready
        and default_side_aligned
        and str(plan.get("symbol_scene_relief", "") or "").strip().lower() == "nas_clean_confirm_probe"
        and compatibility_mode_u == "native_v2"
        and bool(plan.get("near_confirm", False))
        and _float_value("candidate_support") >= 0.60
        and _float_value("pair_gap") >= 0.15
        and _float_value("action_confirm_score") >= 0.13
        and _float_value("confirm_fake_gap") >= -0.18
        and _float_value("wait_confirm_gap") >= -0.13
        and _float_value("continue_fail_gap") >= -0.27
        and _float_value("same_side_barrier") <= 0.60
    )
    if allow_nas_clean_confirm_lower_rebound_ready_bridge:
        return "BUY", "nas_clean_confirm_lower_rebound_ready_bridge"

    gate = dict(default_side_gate_v1 or {})
    try:
        probe_candidate_support = float(
            pd.to_numeric(probe_candidate.get("candidate_support"), errors="coerce") or 0.0
        )
    except (TypeError, ValueError):
        probe_candidate_support = 0.0
    allow_btc_upper_probe_bridge = bool(
        symbol_u == "BTCUSD"
        and core_reason_u == "core_shadow_observe_wait"
        and observe_reason_u == "upper_reject_probe_observe"
        and none_reason_u == "probe_not_promoted"
        and probe_action == "SELL"
        and plan_reason_u == "probe_not_observe_stage"
        and not plan_active
        and not plan_ready
        and str(gate.get("reason", "") or "").lower().strip() == "lower_edge_sell_requires_break_override"
        and str(gate.get("winner_side", "") or "").upper().strip() == "SELL"
        and bool(gate.get("winner_clear", False))
        and compatibility_mode_u in {"", "observe_confirm_v1_fallback"}
        and timing_prob >= 0.978
        and entry_prob >= 0.94
        and probe_candidate_support >= 0.50
        and bool(probe_candidate.get("near_confirm", False))
        and float(pd.to_numeric(gate.get("pair_gap"), errors="coerce") or 0.0) >= 0.30
    )
    if allow_btc_upper_probe_bridge:
        return "SELL", "btc_upper_reject_semantic_probe_bridge"
    return "", ""


def _should_attempt_semantic_probe_bridge(
    *,
    symbol: str,
    core_reason: str,
    observe_reason: str,
    action_none_reason: str,
    blocked_by: str,
    compatibility_mode: str = "",
    entry_probe_plan_v1: dict | None = None,
    default_side_gate_v1: dict | None = None,
) -> bool:
    symbol_u = str(symbol or "").upper().strip()
    core_reason_u = str(core_reason or "").lower().strip()
    observe_reason_u = str(observe_reason or "").lower().strip()
    none_reason_u = str(action_none_reason or "").lower().strip()
    blocked_by_u = str(blocked_by or "").lower().strip()
    compatibility_mode_u = str(compatibility_mode or "").lower().strip()
    plan = dict(entry_probe_plan_v1 or {})
    gate = dict(default_side_gate_v1 or {})
    probe_action = str(
        plan.get("intended_action", "") or plan.get("candidate_side_hint", "") or ""
    ).upper().strip()
    plan_reason_u = str(plan.get("reason", "") or "").lower().strip()
    plan_active = bool(plan.get("active", False))
    plan_ready = bool(plan.get("ready_for_entry", False))
    default_side_aligned = bool(plan.get("default_side_aligned", False))
    scene_relief_u = str(plan.get("symbol_scene_relief", "") or "").strip().lower()
    gate_reason_u = str(gate.get("reason", "") or "").lower().strip()
    gate_side_u = str(gate.get("winner_side", "") or "").upper().strip()
    gate_clear = bool(gate.get("winner_clear", False))

    if (
        symbol_u == "BTCUSD"
        and core_reason_u in {"core_shadow_observe_wait", "energy_soft_block"}
        and observe_reason_u == "lower_rebound_probe_observe"
        and none_reason_u == "probe_not_promoted"
        and probe_action == "BUY"
        and plan_active
        and default_side_aligned
        and plan_reason_u in {
            "probe_pair_gap_not_ready",
            "probe_forecast_not_ready",
            "probe_belief_not_ready",
            "probe_barrier_blocked",
        }
        and blocked_by_u in {"", "forecast_guard", "middle_sr_anchor_guard"}
        and compatibility_mode_u in {"", "observe_confirm_v1_fallback", "native_v2"}
    ):
        return True

    if (
        symbol_u == "NAS100"
        and core_reason_u in {"core_shadow_observe_wait", "energy_soft_block"}
        and observe_reason_u in {"middle_sr_anchor_required_observe", "lower_rebound_probe_observe"}
        and none_reason_u in {"probe_not_promoted", "execution_soft_blocked"}
        and probe_action in {"BUY", "SELL"}
        and plan_active
        and default_side_aligned
        and scene_relief_u == "nas_clean_confirm_probe"
        and compatibility_mode_u == "native_v2"
        and (
            (
                observe_reason_u == "middle_sr_anchor_required_observe"
                and blocked_by_u == "middle_sr_anchor_guard"
                and not plan_ready
                and plan_reason_u == "probe_forecast_not_ready"
            )
            or (
                observe_reason_u == "lower_rebound_probe_observe"
                and blocked_by_u in {"forecast_guard", "energy_soft_block"}
                and probe_action == "BUY"
                and plan_ready
            )
        )
    ):
        return True

    if (
        symbol_u == "BTCUSD"
        and core_reason_u == "core_shadow_observe_wait"
        and observe_reason_u == "upper_reject_probe_observe"
        and none_reason_u == "probe_not_promoted"
        and probe_action == "SELL"
        and not plan_active
        and not plan_ready
        and gate_reason_u == "lower_edge_sell_requires_break_override"
        and gate_side_u == "SELL"
        and gate_clear
        and compatibility_mode_u in {"", "observe_confirm_v1_fallback"}
    ):
        return True

    return False


def try_open_entry(self, symbol, tick, df_all, result, my_positions, pos_count, scorer, buy_s, sell_s, entry_threshold):
    regime = result.get("regime", {}) if isinstance(result, dict) else {}
    spread_now = abs(float(getattr(tick, "ask", 0.0) or 0.0) - float(getattr(tick, "bid", 0.0) or 0.0))
    cooldown_remaining = max(
        0,
        int(float(Config.ENTRY_COOLDOWN) - (time.time() - float(self.runtime.last_entry_time.get(symbol, 0.0)))),
    )
    action = None
    original_action_side_v1 = ""
    action_none_reason = ""
    observe_reason = ""
    semantic_probe_bridge_candidate_action = ""
    semantic_probe_bridge_candidate_reason = ""
    directional_continuation_promotion_v1: dict[str, object] = {}
    execution_action_diff_v1: dict[str, object] = {}
    directional_continuation_promotion_lot_applied_v1 = False
    # Initialize early so nested helpers and AI metadata can safely reference
    # the current stage before adaptive routing chooses the final stage later.
    entry_stage = "balanced"
    entry_stage_detail = {"stage": "balanced", "p": {}, "hist_n": 0}
    ai_used = 0
    ai_missing_reason = ""
    bb_penalty_usd = 0.0
    bb_flags: list[str] = []
    core_pass = 0
    core_reason = ""
    core_allowed_action = "NONE"
    h1_bias_strength = 0.0
    m1_trigger_strength = 0.0
    box_state = "UNKNOWN"
    bb_state = "UNKNOWN"
    core_score = 0.0
    core_buy_raw = 0.0
    core_sell_raw = 0.0
    core_best_raw = 0.0
    core_min_raw = 0.0
    core_margin_raw = 0.0
    core_tie_band_raw = 0.0
    score = 0.0
    contra_score = 0.0
    wait_score = 0.0
    wait_conflict = 0.0
    wait_noise = 0.0
    wait_penalty = 0.0
    learn_buy_penalty = 0.0
    learn_sell_penalty = 0.0
    preflight_regime = "UNKNOWN"
    preflight_liquidity = "OK"
    preflight_allowed_action = "BOTH"
    preflight_approach_mode = "MIX"
    preflight_reason = ""
    preflight_direction_penalty_applied = 0.0
    entry_session_name = ""
    entry_weekday = 0
    entry_session_threshold_mult = 1.0
    entry_atr_ratio = 1.0
    entry_atr_threshold_mult = 1.0
    topdown_ok = False
    topdown_reason = ""
    topdown_stat = {"align": 0, "conflict": 0, "seen": 0}
    gate_ok = False
    gate_reason = ""
    setup_id = ""
    setup_side = ""
    setup_status = "pending"
    setup_trigger_state = "UNKNOWN"
    setup_score = 0.0
    setup_entry_quality = 0.0
    setup_reason = ""
    decision_mode = str(getattr(Config, "ENTRY_DECISION_MODE", "utility_only") or "utility_only").strip().lower()
    if decision_mode not in {"legacy", "hybrid", "utility_only"}:
        decision_mode = "hybrid"
    utility_p_raw = None
    utility_p_calibrated = None
    utility_stats_ready = 0
    utility_wins_n = 0
    utility_losses_n = 0
    entry_wait_selected = 0
    entry_wait_decision = ""
    wait_state = None
    entry_enter_value = 0.0
    entry_wait_value = 0.0
    entry_wait_energy_usage_trace_v1 = {}
    entry_wait_decision_energy_usage_trace_v1 = {}
    prediction_bundle = {"entry": {}, "wait": {}, "exit": {}, "reverse": {}, "metadata": {}}
    shadow_bundle = None
    shadow_context_metadata_v1 = {}
    shadow_position_snapshot_obj = None
    shadow_response_raw_obj = None
    shadow_response_v2_obj = None
    shadow_state_raw_obj = None
    shadow_state_v2_obj = None
    shadow_evidence_obj = None
    shadow_belief_obj = None
    shadow_barrier_obj = None
    shadow_forecast_features_obj = None
    shadow_transition_forecast_obj = None
    shadow_trade_management_forecast_obj = None
    shadow_energy_obj = None
    shadow_position_snapshot_v2 = {}
    shadow_response_raw_snapshot_v1 = {}
    shadow_response_vector_v2 = {}
    shadow_state_raw_snapshot_v1 = {}
    shadow_state_vector_v2 = {}
    shadow_evidence_vector_v1 = {}
    shadow_belief_state_v1 = {}
    shadow_barrier_state_v1 = {}
    shadow_forecast_features_v1 = {}
    shadow_transition_forecast_v1 = {}
    shadow_trade_management_forecast_v1 = {}
    shadow_energy_snapshot = {}
    shadow_observe_confirm = {}
    shadow_runtime_maps_materialized = False
    core_dec = {}
    entry_probe_plan_v1 = {}
    semantic_shadow_prediction_v1 = None
    semantic_live_guard_v1 = None
    state25_candidate_log_only_trace_v1 = {}
    forecast_state25_runtime_bridge_v1 = {}
    forecast_state25_log_only_overlay_trace_v1 = {}
    belief_state25_runtime_bridge_v1 = {}
    belief_action_hint_v1 = {}
    barrier_state25_runtime_bridge_v1 = {}
    barrier_action_hint_v1 = {}
    observe_confirm_runtime_payload = {}
    countertrend_continuation_signal_v1 = {}
    breakout_event_runtime_v1 = {}
    breakout_event_overlay_candidates_v1 = {}
    consumer_layer_mode_hard_block_active = False
    consumer_layer_mode_suppressed = False
    consumer_policy_live_gate_applied = False
    consumer_policy_block_layer = ""
    consumer_policy_block_effect = ""
    consumer_energy_action_readiness = 0.0
    consumer_energy_wait_vs_enter_hint = ""
    consumer_energy_soft_block_active = False
    consumer_energy_soft_block_reason = ""
    consumer_energy_soft_block_strength = 0.0
    active_action_conflict_guard_v1: dict[str, object] = {}
    flow_execution_veto_owner_v1: dict[str, object] = {}
    flow_execution_selection_owner_v1: dict[str, object] = {}

    def _materialize_shadow_runtime_maps() -> None:
        nonlocal shadow_runtime_maps_materialized
        nonlocal shadow_position_snapshot_v2
        nonlocal shadow_response_raw_snapshot_v1
        nonlocal shadow_response_vector_v2
        nonlocal shadow_state_raw_snapshot_v1
        nonlocal shadow_state_vector_v2
        nonlocal shadow_evidence_vector_v1
        nonlocal shadow_belief_state_v1
        nonlocal shadow_barrier_state_v1
        nonlocal shadow_forecast_features_v1
        nonlocal shadow_transition_forecast_v1
        nonlocal shadow_trade_management_forecast_v1
        nonlocal shadow_energy_snapshot
        if shadow_runtime_maps_materialized:
            return
        shadow_position_snapshot_v2 = _safe_mapping(shadow_position_snapshot_obj)
        shadow_response_raw_snapshot_v1 = _safe_mapping(shadow_response_raw_obj)
        shadow_response_vector_v2 = _safe_mapping(shadow_response_v2_obj)
        shadow_state_raw_snapshot_v1 = _safe_mapping(shadow_state_raw_obj)
        shadow_state_vector_v2 = _safe_mapping(shadow_state_v2_obj)
        shadow_evidence_vector_v1 = _safe_mapping(shadow_evidence_obj)
        shadow_belief_state_v1 = _safe_mapping(shadow_belief_obj)
        shadow_barrier_state_v1 = _safe_mapping(shadow_barrier_obj)
        shadow_forecast_features_v1 = _safe_mapping(shadow_forecast_features_obj)
        shadow_transition_forecast_v1 = _safe_mapping(shadow_transition_forecast_obj)
        shadow_trade_management_forecast_v1 = _safe_mapping(shadow_trade_management_forecast_obj)
        shadow_energy_snapshot = _safe_mapping(shadow_energy_obj)
        shadow_runtime_maps_materialized = True
    consumer_energy_live_gate_applied = False
    consumer_archetype_id = ""
    consumer_invalidation_id = ""
    consumer_management_profile_id = ""
    consumer_check_state_v1 = {}
    consumer_check_candidate = False
    consumer_check_display_ready = False
    consumer_check_entry_ready = False
    consumer_check_side = ""
    consumer_check_stage = ""
    consumer_check_reason = ""
    consumer_check_display_strength_level = 0
    consumer_check_display_score = 0.0
    consumer_check_display_repeat_count = 0
    p7_guarded_size_overlay_v1 = {}
    teacher_label_exploration_entry_v1 = {}
    teacher_label_exploration_lot_applied_v1 = False

    def _debug_breadcrumb(stage: str, detail: str = "") -> None:
        debug_writer = getattr(self.runtime, "_write_loop_debug", None)
        if not callable(debug_writer):
            return
        try:
            debug_loop_count = int((((getattr(self.runtime, "loop_debug_state", {}) or {}).get("loop_count", 0)) or 0))
            debug_writer(
                loop_count=debug_loop_count,
                stage=f"entry_try:{str(stage or '').strip()}",
                symbol=str(symbol or ""),
                detail=str(detail or "")[:240],
            )
        except Exception:
            return

    def _json_field(payload: dict) -> str:
        if not isinstance(payload, dict) or not payload:
            return ""
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _current_runtime_snapshot_row() -> dict:
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if not isinstance(rows, dict):
            return {}
        candidate = rows.get(symbol, {})
        if not isinstance(candidate, dict):
            return {}
        return dict(candidate)

    _cached_entry_runtime_signal_row_v1: dict | None = None

    def _current_entry_runtime_signal_row(*, refresh_current_cycle: bool = False) -> dict:
        nonlocal _cached_entry_runtime_signal_row_v1
        if not refresh_current_cycle and isinstance(_cached_entry_runtime_signal_row_v1, dict):
            return dict(_cached_entry_runtime_signal_row_v1)

        row = _current_runtime_snapshot_row()
        if refresh_current_cycle:
            builder = getattr(self.runtime, "build_entry_runtime_signal_row", None)
            if callable(builder):
                try:
                    enriched_row = builder(str(symbol), row)
                    if isinstance(enriched_row, dict):
                        row = dict(enriched_row)
                except Exception:
                    pass
        _cached_entry_runtime_signal_row_v1 = dict(row)
        return dict(row)

    entry_prefront_started_at = time.perf_counter()
    entry_prefront_stage_started_at = entry_prefront_started_at
    entry_prefront_stage_timings_ms: dict[str, float] = {}
    entry_prefront_profile_state = {
        "current_stage": "initial_limits",
        "last_completed_stage": "",
        "exit_state": "in_progress",
    }

    def _record_entry_prefront_stage(stage_name: str, started_at: float) -> None:
        entry_prefront_stage_timings_ms[str(stage_name)] = round(
            (time.perf_counter() - float(started_at)) * 1000.0,
            3,
        )
        entry_prefront_profile_state["last_completed_stage"] = str(stage_name)

    def _set_entry_prefront_stage(stage_name: str) -> None:
        nonlocal entry_prefront_stage_started_at
        entry_prefront_profile_state["current_stage"] = str(stage_name)
        entry_prefront_stage_started_at = time.perf_counter()

    def _store_entry_prefront_profile(
        exit_state: str | None = None,
        *,
        blocked_by_value: str = "",
        observe_reason_value: str = "",
        action_none_reason_value: str = "",
        action_value: str = "",
    ) -> None:
        if exit_state is not None:
            entry_prefront_profile_state["exit_state"] = str(exit_state)
        runtime_snapshot_row = _current_runtime_snapshot_row()
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_helper_prefront_profile_v1",
                payload={
                    "contract_version": "entry_helper_prefront_profile_v1",
                    "total_ms": round((time.perf_counter() - entry_prefront_started_at) * 1000.0, 3),
                    "stage_timings_ms": dict(entry_prefront_stage_timings_ms),
                    "current_stage": str(entry_prefront_profile_state.get("current_stage", "") or ""),
                    "last_completed_stage": str(entry_prefront_profile_state.get("last_completed_stage", "") or ""),
                    "exit_state": str(entry_prefront_profile_state.get("exit_state", "") or ""),
                    "action": str(action_value or action or ""),
                    "observe_reason": str(observe_reason_value or observe_reason or ""),
                    "blocked_by": str(blocked_by_value or ""),
                    "action_none_reason": str(action_none_reason_value or action_none_reason or ""),
                    "quick_trace_state": str(runtime_snapshot_row.get("quick_trace_state", "") or ""),
                    "core_reason": str(core_reason or ""),
                    "core_allowed_action": str(core_allowed_action or ""),
                },
            )
        except Exception:
            pass

    def _ensure_semantic_shadow_prediction(
        *,
        runtime_snapshot_row: dict | None = None,
        action_hint: str = "",
        setup_id_value: str = "",
        setup_side_value: str = "",
        entry_stage_value: str = "",
    ) -> dict:
        nonlocal semantic_shadow_prediction_v1
        if semantic_shadow_prediction_v1 is not None:
            return dict(semantic_shadow_prediction_v1 or {})
        runtime_snapshot_row = dict(runtime_snapshot_row or _current_runtime_snapshot_row() or {})
        prediction_cache = getattr(self.runtime, "_semantic_shadow_prediction_cache", None)
        if not isinstance(prediction_cache, dict):
            prediction_cache = {}
            try:
                setattr(self.runtime, "_semantic_shadow_prediction_cache", prediction_cache)
            except Exception:
                prediction_cache = {}
        cache_key = _build_semantic_shadow_prediction_cache_key(
            symbol=str(symbol),
            runtime_snapshot_row=runtime_snapshot_row,
            action_hint=str(action_hint or shadow_observe_confirm.get("action", "") or ""),
            setup_id=str(setup_id_value or ""),
            setup_side=str(setup_side_value or ""),
            entry_stage=str(entry_stage_value or ""),
        )
        if cache_key:
            cached_prediction = prediction_cache.get(cache_key)
            if isinstance(cached_prediction, Mapping):
                semantic_shadow_prediction_v1 = dict(cached_prediction)
                return dict(semantic_shadow_prediction_v1 or {})
        _materialize_shadow_runtime_maps()
        semantic_runtime = None
        refresh_runtime = getattr(self.runtime, "_refresh_semantic_shadow_runtime_if_needed", None)
        if callable(refresh_runtime):
            try:
                refresh_runtime()
            except Exception:
                semantic_runtime = None
        semantic_runtime = semantic_runtime or getattr(self.runtime, "semantic_shadow_runtime", None)
        if semantic_runtime is not None:
            semantic_feature_row = build_semantic_shadow_feature_row(
                runtime_snapshot_row=runtime_snapshot_row,
                position_snapshot_v2=shadow_position_snapshot_v2,
                response_vector_v2=shadow_response_vector_v2,
                state_vector_v2=shadow_state_vector_v2,
                evidence_vector_v1=shadow_evidence_vector_v1,
                forecast_features_v1=shadow_forecast_features_v1,
                signal_timeframe=str(
                    runtime_snapshot_row.get("signal_timeframe", "")
                    or runtime_snapshot_row.get("timeframe", "")
                    or ""
                ),
                setup_id=str(setup_id_value or ""),
                setup_side=str(setup_side_value or ""),
                entry_stage=str(entry_stage_value or ""),
                preflight_regime=str(preflight_regime or ""),
                preflight_liquidity=str(preflight_liquidity or ""),
            )
            try:
                semantic_shadow_prediction_v1 = semantic_runtime.predict_shadow(
                    semantic_feature_row,
                    action_hint=str(action_hint or shadow_observe_confirm.get("action", "") or ""),
                    timing_threshold=float(getattr(Config, "SEMANTIC_TIMING_THRESHOLD", 0.55)),
                    entry_quality_threshold=float(
                        getattr(Config, "SEMANTIC_ENTRY_QUALITY_THRESHOLD", 0.55)
                    ),
                    exit_management_threshold=float(
                        getattr(Config, "SEMANTIC_EXIT_MANAGEMENT_THRESHOLD", 0.55)
                    ),
                )
                try:
                    self._store_runtime_snapshot(
                        runtime=self.runtime,
                        symbol=str(symbol),
                        key="semantic_shadow_prediction_v1",
                        payload=dict(semantic_shadow_prediction_v1),
                    )
                except Exception:
                    pass
            except Exception:
                semantic_shadow_prediction_v1 = SemanticShadowRuntime.unavailable_prediction(
                    reason="semantic_prediction_failed",
                    action_hint=str(action_hint or ""),
                )
        else:
            semantic_shadow_prediction_v1 = SemanticShadowRuntime.unavailable_prediction(
                reason="semantic_runtime_unavailable",
                action_hint=str(action_hint or ""),
            )
        if cache_key:
            prediction_cache[str(cache_key)] = dict(semantic_shadow_prediction_v1 or {})
            max_cache_size = 128
            while len(prediction_cache) > max_cache_size:
                try:
                    oldest_key = next(iter(prediction_cache))
                except StopIteration:
                    break
                prediction_cache.pop(oldest_key, None)
        return dict(semantic_shadow_prediction_v1 or {})

    def _resolve_semantic_shadow_fast_skip_reason(
        *,
        runtime_snapshot_row: dict | None = None,
        action_value: str = "",
        outcome_value: str = "",
        blocked_by_value: str = "",
        observe_reason_value: str = "",
        action_none_reason_value: str = "",
    ) -> str:
        if semantic_shadow_prediction_v1 is not None:
            return ""
        action_u = str(action_value or "").upper().strip()
        outcome_u = str(outcome_value or "").lower().strip()
        if outcome_u not in {"wait", "skipped"}:
            return ""
        semantic_rollout_mode_u = str(
            getattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "disabled") or "disabled"
        ).lower().strip()
        if semantic_rollout_mode_u in {"disabled", "log_only", "alert_only"}:
            return "semantic_non_enter_logonly_fast_path"
        if action_u in {"BUY", "SELL"}:
            return ""
        runtime_snapshot_row = dict(runtime_snapshot_row or {})
        quick_trace_state_u = str(runtime_snapshot_row.get("quick_trace_state", "") or "").upper().strip()
        blocked_by_u = str(blocked_by_value or "").lower().strip()
        observe_reason_u = str(observe_reason_value or "").lower().strip()
        action_none_u = str(action_none_reason_value or "").lower().strip()
        bridge_watch_reasons = {
            "forecast_guard",
            "energy_soft_block",
            "probe_promotion_gate",
            "middle_sr_anchor_guard",
            "outer_band_guard",
            "box_middle_buy_without_bb_support",
        }
        bridge_observe_reasons = {
            "lower_rebound_probe_observe",
            "upper_reject_probe_observe",
            "middle_sr_anchor_required_observe",
        }
        if (
            quick_trace_state_u.startswith("PROBE")
            or blocked_by_u in bridge_watch_reasons
            or observe_reason_u in bridge_observe_reasons
            or action_none_u in {"probe_not_promoted", "execution_soft_blocked"}
        ):
            return ""
        return "semantic_non_action_fast_path"

    def _wait_input_row(
        *,
        action_value: str = "",
        observe_reason_value: str | None = None,
        blocked_by_value: str = "",
        action_none_reason_value: str | None = None,
        box_state_value: str | None = None,
        bb_state_value: str | None = None,
        core_allowed_action_value: str | None = None,
        setup_status_value: str | None = None,
        setup_reason_value: str | None = None,
        setup_trigger_state_value: str | None = None,
    ) -> dict:
        payload = {
            "symbol": str(symbol),
            "action": str(action_value or ""),
            "observe_reason": str(
                observe_reason
                if observe_reason_value is None
                else observe_reason_value or ""
            ),
            "blocked_by": str(blocked_by_value or ""),
            "action_none_reason": str(action_none_reason if action_none_reason_value is None else action_none_reason_value or ""),
            "box_state": str(box_state if box_state_value is None else box_state_value),
            "bb_state": str(bb_state if bb_state_value is None else bb_state_value),
            "core_allowed_action": str(
                core_allowed_action if core_allowed_action_value is None else core_allowed_action_value
            ),
            "preflight_allowed_action": str(preflight_allowed_action),
            "setup_status": str(setup_status if setup_status_value is None else setup_status_value),
            "setup_reason": str(setup_reason if setup_reason_value is None else setup_reason_value),
            "setup_trigger_state": str(
                setup_trigger_state if setup_trigger_state_value is None else setup_trigger_state_value
            ),
            "wait_score": float(wait_score),
            "wait_conflict": float(wait_conflict),
            "wait_noise": float(wait_noise),
            "wait_penalty": float(wait_penalty),
            "consumer_layer_mode_hard_block_active": bool(consumer_layer_mode_hard_block_active),
            "consumer_layer_mode_suppressed": bool(consumer_layer_mode_suppressed),
            "consumer_policy_live_gate_applied": bool(consumer_policy_live_gate_applied),
            "consumer_policy_block_layer": str(consumer_policy_block_layer or ""),
            "consumer_policy_block_effect": str(consumer_policy_block_effect or ""),
            "consumer_energy_action_readiness": float(consumer_energy_action_readiness),
            "consumer_energy_wait_vs_enter_hint": str(consumer_energy_wait_vs_enter_hint or ""),
            "consumer_energy_soft_block_active": bool(consumer_energy_soft_block_active),
            "consumer_energy_soft_block_reason": str(consumer_energy_soft_block_reason or ""),
            "consumer_energy_soft_block_strength": float(consumer_energy_soft_block_strength),
            "consumer_energy_live_gate_applied": bool(consumer_energy_live_gate_applied),
        }

    def _resolve_effective_consumer_check_state(
        *,
        blocked_by_value: str = "",
        action_none_reason_value: str | None = None,
        action_value: str = "",
    ) -> tuple[bool, bool, bool, str, str, str, int, dict]:
        return resolve_effective_consumer_check_state_v1(
            consumer_check_state_v1=consumer_check_state_v1,
            fallback_candidate=consumer_check_candidate,
            fallback_display_ready=consumer_check_display_ready,
            fallback_entry_ready=consumer_check_entry_ready,
            fallback_side=consumer_check_side or action_value or action or "",
            fallback_stage=consumer_check_stage,
            fallback_reason=consumer_check_reason or observe_reason or "",
            fallback_display_strength_level=consumer_check_display_strength_level,
            fallback_action_none_reason=action_none_reason,
            blocked_by_value=blocked_by_value,
            action_none_reason_value=action_none_reason_value,
            action_value=str(action_value or action or ""),
            previous_runtime_row=_current_runtime_snapshot_row(),
        )

    def _decision_payload(
        *,
        action: str = "",
        considered: int = 1,
        outcome: str = "skipped",
        blocked_by: str = "",
        last_order_retcode: int | None = None,
        last_order_comment: str | None = None,
        order_block_remaining_sec: int | None = None,
        core_pass_v: int | None = None,
        core_reason_v: str | None = None,
        core_allowed_action_v: str | None = None,
        h1_bias_strength_v: float | None = None,
        m1_trigger_strength_v: float | None = None,
        box_state_v: str | None = None,
        bb_state_v: str | None = None,
        core_score_v: float | None = None,
        setup_id_v: str | None = None,
        setup_side_v: str | None = None,
        setup_status_v: str | None = None,
        setup_trigger_state_v: str | None = None,
        setup_score_v: float | None = None,
        setup_entry_quality_v: float | None = None,
        setup_reason_v: str | None = None,
        raw_score: float = 0.0,
        contra_score: float = 0.0,
        effective_threshold: float | int | None = None,
        entry_stage: str = "",
        ai_probability: float | None = None,
        size_multiplier: float = 1.0,
        utility_u: float | None = None,
        utility_p: float | None = None,
        utility_w: float | None = None,
        utility_l: float | None = None,
        utility_cost: float | None = None,
        utility_context_adj: float | None = None,
        u_min: float | None = None,
        u_pass: int | None = None,
        decision_rule_version: str = "legacy_v1",
        trade_link_key: str = "",
        order_submit_latency_ms: int | None = None,
    ) -> dict:
        _debug_breadcrumb(
            "decision_payload_begin",
            f"{str(action or '')}|{str(outcome or '')}|{str(blocked_by or '')}",
        )
        payload_started_at = time.perf_counter()
        payload_stage_timings_ms: dict[str, float] = {}

        def _record_payload_stage(stage_name: str, started_at: float) -> None:
            payload_stage_timings_ms[str(stage_name)] = round(
                (time.perf_counter() - float(started_at)) * 1000.0,
                3,
            )

        nonlocal semantic_shadow_prediction_v1
        nonlocal semantic_live_guard_v1
        nonlocal active_action_conflict_guard_v1
        nonlocal flow_execution_veto_owner_v1
        nonlocal flow_execution_selection_owner_v1
        nonlocal directional_continuation_promotion_v1
        flow_execution_selection_owner_flat_fields = (
            _build_flow_execution_selection_owner_flat_fields(
                flow_execution_selection_owner_v1
            )
        )
        flow_execution_veto_owner_flat_fields = _build_flow_execution_veto_owner_flat_fields(
            flow_execution_veto_owner_v1
        )
        veto_applied = bool(flow_execution_veto_owner_v1.get("veto_applied", False))
        selection_active = bool(flow_execution_selection_owner_v1.get("selection_active", False))
        selection_action = str(
            flow_execution_selection_owner_v1.get("selected_action", "") or ""
        ).upper().strip()
        semantic_context_action = str(
            selection_action
            if selection_active and selection_action in {"BUY", "SELL"}
            else ""
            if veto_applied or (selection_active and selection_action == "WAIT")
            else (active_action_conflict_guard_v1 or {}).get("baseline_action", "") or action or ""
        )
        active_action_conflict_guard_flat_fields = _build_active_action_conflict_guard_flat_fields(
            active_action_conflict_guard_v1
        )
        stage_started_at = time.perf_counter()
        (
            effective_consumer_check_candidate,
            effective_consumer_check_display_ready,
            effective_consumer_check_entry_ready,
            effective_consumer_check_side,
            effective_consumer_check_stage,
            effective_consumer_check_reason,
            effective_consumer_check_display_strength_level,
            effective_consumer_check_state_v1,
        ) = _resolve_effective_consumer_check_state(
            blocked_by_value=str(blocked_by or ""),
            action_value=str(action or ""),
        )
        _record_payload_stage("consumer_check_state", stage_started_at)
        runtime_snapshot_row = _current_runtime_snapshot_row()
        stage_started_at = time.perf_counter()
        _materialize_shadow_runtime_maps()
        _record_payload_stage("shadow_runtime_maps", stage_started_at)
        stage_started_at = time.perf_counter()
        semantic_fast_skip_reason = _resolve_semantic_shadow_fast_skip_reason(
            runtime_snapshot_row=runtime_snapshot_row,
            action_value=str(semantic_context_action),
            outcome_value=str(outcome or ""),
            blocked_by_value=str(blocked_by or ""),
            observe_reason_value=str(observe_reason or ""),
            action_none_reason_value=str(action_none_reason or ""),
        )
        if semantic_fast_skip_reason:
            semantic_shadow_prediction_v1 = SemanticShadowRuntime.unavailable_prediction(
                reason=str(semantic_fast_skip_reason),
                action_hint=str(semantic_context_action or shadow_observe_confirm.get("action", "") or ""),
            )
        else:
            _ensure_semantic_shadow_prediction(
                runtime_snapshot_row=runtime_snapshot_row,
                action_hint=str(semantic_context_action or shadow_observe_confirm.get("action", "") or ""),
                setup_id_value=str(setup_id if setup_id_v is None else setup_id_v or ""),
                setup_side_value=str(setup_side if setup_side_v is None else setup_side_v or ""),
                entry_stage_value=str(entry_stage or ""),
            )
        _record_payload_stage("semantic_shadow", stage_started_at)

        stage_started_at = time.perf_counter()
        if semantic_live_guard_v1 is None:
            semantic_live_guard = getattr(self.runtime, "semantic_promotion_guard", None)
            if semantic_live_guard is None:
                semantic_live_guard = SemanticPromotionGuard()
            current_threshold = max(1, int(round(float(effective_threshold or 1) or 1.0)))
            try:
                semantic_live_guard_v1 = semantic_live_guard.evaluate_entry_rollout(
                    symbol=str(symbol),
                    baseline_action=str(semantic_context_action),
                    entry_stage=str(entry_stage),
                    current_threshold=int(current_threshold),
                    semantic_prediction=semantic_shadow_prediction_v1,
                    runtime_snapshot_row=runtime_snapshot_row,
                )
                try:
                    self._store_runtime_snapshot(
                        runtime=self.runtime,
                        symbol=str(symbol),
                        key="semantic_live_guard_v1",
                        payload=dict(semantic_live_guard_v1 or {}),
                    )
                except Exception:
                    pass
                record_rollout = getattr(self.runtime, "record_semantic_rollout_event", None)
                if callable(record_rollout):
                    try:
                        record_rollout(domain="entry", event=dict(semantic_live_guard_v1 or {}))
                    except Exception:
                        pass
                if bool((semantic_live_guard_v1 or {}).get("alert_active")):
                    obs_event = getattr(self.runtime, "_obs_event", None)
                    if callable(obs_event):
                        try:
                            obs_event(
                                "semantic_live_rollout_alert",
                                level="warning",
                                payload={
                                    "symbol": str(symbol),
                                    "mode": str((semantic_live_guard_v1 or {}).get("mode", "") or ""),
                                    "fallback_reason": str(
                                        (semantic_live_guard_v1 or {}).get("fallback_reason", "") or ""
                                    ),
                                    "reason": str((semantic_live_guard_v1 or {}).get("reason", "") or ""),
                                },
                            )
                        except Exception:
                            pass
            except Exception:
                semantic_live_guard_v1 = {
                    "mode": str(getattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "disabled") or "disabled"),
                    "fallback_reason": "promotion_guard_failed",
                    "fallback_applied": True,
                    "threshold_before": int(current_threshold),
                    "threshold_after": int(current_threshold),
                    "threshold_adjustment_points": 0,
                    "threshold_applied": False,
                    "partial_live_weight": 0.0,
                    "partial_live_applied": False,
                    "alert_active": False,
                    "reason": "promotion_guard_failed",
                    "symbol_allowed": False,
                    "entry_stage_allowed": False,
                }
        _record_payload_stage("semantic_live_guard", stage_started_at)
        stage_started_at = time.perf_counter()
        wait_state = self._wait_engine.build_entry_wait_state_from_row(
            symbol=str(symbol),
            row=_wait_input_row(
                action_value=str(action or ""),
                blocked_by_value=str(blocked_by or ""),
                box_state_value=str(box_state if box_state_v is None else box_state_v),
                bb_state_value=str(bb_state if bb_state_v is None else bb_state_v),
                core_allowed_action_value=str(
                    core_allowed_action if core_allowed_action_v is None else core_allowed_action_v
                ),
                setup_status_value=str(setup_status if setup_status_v is None else setup_status_v),
                setup_reason_value=str(setup_reason if setup_reason_v is None else setup_reason_v),
                setup_trigger_state_value=str(
                    setup_trigger_state if setup_trigger_state_v is None else setup_trigger_state_v
                ),
            ),
        )
        _record_payload_stage("wait_state", stage_started_at)
        wait_metadata = _sync_blocked_by_into_wait_payloads_v1(
            dict(wait_state.metadata or {}),
            str(blocked_by or ""),
        )
        vol_ratio = float((regime or {}).get("volatility_ratio", 1.0) or 1.0)
        semantic_timing = (
            semantic_shadow_prediction_v1.get("timing", {})
            if isinstance(semantic_shadow_prediction_v1, dict)
            else {}
        )
        semantic_entry_quality = (
            semantic_shadow_prediction_v1.get("entry_quality", {})
            if isinstance(semantic_shadow_prediction_v1, dict)
            else {}
        )
        semantic_exit_management = (
            semantic_shadow_prediction_v1.get("exit_management", {})
            if isinstance(semantic_shadow_prediction_v1, dict)
            else {}
        )
        semantic_runtime_diagnostics = getattr(self.runtime, "semantic_shadow_runtime_diagnostics", None)
        semantic_shadow_activation_state, semantic_shadow_activation_reason = _resolve_semantic_shadow_activation(
            semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
            semantic_live_guard_v1=semantic_live_guard_v1,
            runtime_diagnostics=semantic_runtime_diagnostics if isinstance(semantic_runtime_diagnostics, dict) else None,
        )
        semantic_live_threshold_state, semantic_live_threshold_reason = _resolve_semantic_live_threshold_trace(
            semantic_live_guard_v1=semantic_live_guard_v1,
        )
        semantic_compare_label = resolve_semantic_shadow_compare_label(
            semantic_shadow_prediction_v1,
            baseline_outcome=str(outcome or ""),
            baseline_action=str(semantic_context_action),
            blocked_by=str(blocked_by or ""),
        )
        actual_effective_entry_threshold = (
            float(effective_threshold)
            if effective_threshold is not None
            else float(entry_threshold)
        )
        _debug_breadcrumb(
            "decision_payload_bridge_begin",
            f"{str(action or '')}|{str(outcome or '')}|{str(blocked_by or '')}",
        )
        stage_started_at = time.perf_counter()
        semantic_owner_bundle = _build_semantic_owner_runtime_bundle_v1(
            runtime_snapshot_row=runtime_snapshot_row,
            symbol=str(symbol),
            action=str(semantic_context_action),
            setup_id=str(setup_id or ""),
            setup_reason=str(setup_reason or ""),
            setup_side=str(setup_side or semantic_context_action or ""),
            entry_session_name=str(entry_session_name or ""),
            wait_state=wait_state,
            entry_wait_decision=str(entry_wait_decision or ""),
            score=float(score),
            contra_score=float(contra_score),
            prediction_bundle=prediction_bundle,
            shadow_transition_forecast_v1=shadow_transition_forecast_v1,
            shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
            shadow_observe_confirm=shadow_observe_confirm,
            entry_stage=str(entry_stage or ""),
            actual_effective_entry_threshold=float(actual_effective_entry_threshold),
            actual_size_multiplier=float(size_multiplier),
            state25_candidate_runtime_state=getattr(
                self.runtime, "state25_candidate_runtime_state", {}
            ),
        )
        _record_payload_stage("semantic_owner_bundle", stage_started_at)
        state25_candidate_log_only_trace_v1 = dict(
            semantic_owner_bundle.get("state25_candidate_log_only_trace_v1", {}) or {}
        )
        observe_confirm_runtime_payload = dict(
            semantic_owner_bundle.get("observe_confirm_runtime_payload", {}) or {}
        )
        forecast_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("forecast_state25_runtime_bridge_v1", {}) or {}
        )
        forecast_state25_log_only_overlay_trace_v1 = dict(
            semantic_owner_bundle.get("forecast_state25_log_only_overlay_trace_v1", {}) or {}
        )
        belief_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("belief_state25_runtime_bridge_v1", {}) or {}
        )
        belief_action_hint_v1 = dict(
            semantic_owner_bundle.get("belief_action_hint_v1", {}) or {}
        )
        barrier_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("barrier_state25_runtime_bridge_v1", {}) or {}
        )
        barrier_action_hint_v1 = dict(
            semantic_owner_bundle.get("barrier_action_hint_v1", {}) or {}
        )
        semantic_owner_flat_fields = dict(
            semantic_owner_bundle.get("flat_fields", {}) or {}
        )
        semantic_owner_detail_fields = dict(
            semantic_owner_bundle.get("detail_fields", {}) or {}
        )
        stage_started_at = time.perf_counter()
        entry_candidate_surface_v1 = build_entry_candidate_bridge_v1(
            symbol=str(symbol),
            action=str(action or ""),
            entry_stage=str(entry_stage or ""),
            core_reason=str(core_reason if core_reason_v is None else core_reason_v),
            observe_reason=str(observe_reason or ""),
            action_none_reason=str(action_none_reason or ""),
            blocked_by=str(blocked_by or ""),
            compatibility_mode=str(runtime_snapshot_row.get("compatibility_mode", "") or ""),
            semantic_probe_bridge_action=str(semantic_probe_bridge_candidate_action or ""),
            semantic_probe_bridge_reason=str(semantic_probe_bridge_candidate_reason or ""),
            entry_probe_plan_v1=dict(entry_probe_plan_v1 or {}),
            entry_default_side_gate_v1=dict(core_dec.get("entry_default_side_gate_v1", {}) or {})
            if isinstance(core_dec.get("entry_default_side_gate_v1", {}), dict)
            else {},
            probe_candidate_v1=_safe_mapping(
                _safe_mapping(
                    _safe_mapping(shadow_observe_confirm).get("metadata", {})
                ).get("probe_candidate_v1", {})
            ),
            semantic_shadow_prediction_v1=dict(semantic_shadow_prediction_v1 or {}),
            state25_candidate_log_only_trace_v1=state25_candidate_log_only_trace_v1,
            forecast_state25_runtime_bridge_v1=forecast_state25_runtime_bridge_v1,
            forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
            breakout_event_runtime_v1=dict(
                semantic_owner_bundle.get("breakout_event_runtime_v1", {}) or {}
            ),
            breakout_event_overlay_candidates_v1=dict(
                semantic_owner_bundle.get("breakout_event_overlay_candidates_v1", {}) or {}
            ),
            countertrend_continuation_signal_v1=dict(
                semantic_owner_bundle.get("countertrend_continuation_signal_v1", {}) or {}
            ),
            active_action_conflict_guard_v1=dict(active_action_conflict_guard_v1 or {}),
        )
        entry_candidate_bridge_fields = build_entry_candidate_bridge_flat_fields(
            entry_candidate_surface_v1
        )
        _record_payload_stage("entry_candidate_bridge", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_bridge_done",
            f"{str(action or '')}|{str(outcome or '')}|{str(blocked_by or '')}",
        )
        stage_started_at = time.perf_counter()
        prediction_bundle_json = (
            json.dumps(prediction_bundle, ensure_ascii=False, separators=(",", ":"))
            if any(bool(prediction_bundle.get(k)) for k in ("entry", "wait", "exit", "reverse", "metadata"))
            else ""
        )
        position_snapshot_v2_json = _json_field(shadow_position_snapshot_v2)
        response_raw_snapshot_v1_json = _json_field(shadow_response_raw_snapshot_v1)
        response_vector_v2_json = _json_field(shadow_response_vector_v2)
        state_raw_snapshot_v1_json = _json_field(shadow_state_raw_snapshot_v1)
        state_vector_v2_json = _json_field(shadow_state_vector_v2)
        evidence_vector_v1_json = _json_field(shadow_evidence_vector_v1)
        belief_state_v1_json = _json_field(shadow_belief_state_v1)
        barrier_state_v1_json = _json_field(shadow_barrier_state_v1)
        forecast_features_v1_json = _json_field(shadow_forecast_features_v1)
        transition_forecast_v1_json = _json_field(shadow_transition_forecast_v1)
        trade_management_forecast_v1_json = _json_field(shadow_trade_management_forecast_v1)
        forecast_gap_metrics_v1_json = _json_field({
            "transition_side_separation": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("side_separation", 0.0)) or 0.0)),
            "transition_confirm_fake_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("confirm_fake_gap", 0.0)) or 0.0)),
            "transition_reversal_continuation_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("reversal_continuation_gap", 0.0)) or 0.0)),
            "management_continue_fail_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("continue_fail_gap", 0.0)) or 0.0)),
            "management_recover_reentry_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("recover_reentry_gap", 0.0)) or 0.0)),
        })
        observe_confirm_v2_json = _json_field(observe_confirm_runtime_payload.get("observe_confirm_v2", {}))
        observe_confirm_v1_json = _json_field(observe_confirm_runtime_payload.get("observe_confirm_v1", {}))
        _record_payload_stage("json_serialize", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_json_done",
            f"{str(action or '')}|{str(outcome or '')}|json",
        )
        helper_payload_profile_v1 = {
            "contract_version": "entry_helper_payload_profile_v1",
            "action": str(action or ""),
            "outcome": str(outcome or ""),
            "blocked_by": str(blocked_by or ""),
            "total_ms": round((time.perf_counter() - payload_started_at) * 1000.0, 3),
            "stage_timings_ms": dict(payload_stage_timings_ms),
        }
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_helper_payload_profile_v1",
                payload=helper_payload_profile_v1,
            )
        except Exception:
            pass
        directional_runtime_surface_v1 = _refresh_directional_runtime_execution_surface_v1(
            runtime_owner=getattr(self, "runtime", None),
            symbol=str(symbol),
            runtime_row=runtime_snapshot_row,
            baseline_action=str(original_action_side_v1 or ""),
            current_action=str(action or ""),
            blocked_by=str(blocked_by or ""),
            observe_reason=str(observe_reason or ""),
            action_none_reason=str(action_none_reason or ""),
            setup_id=str(setup_id or ""),
            setup_reason=str(setup_reason or observe_reason or ""),
            forecast_state25_log_only_overlay_trace_v1=dict(
                forecast_state25_log_only_overlay_trace_v1 or {}
            ),
            belief_action_hint_v1=dict(belief_action_hint_v1 or {}),
            barrier_action_hint_v1=dict(barrier_action_hint_v1 or {}),
            countertrend_continuation_signal_v1=dict(
                countertrend_continuation_signal_v1 or {}
            ),
            breakout_event_runtime_v1=dict(breakout_event_runtime_v1 or {}),
            breakout_event_overlay_candidates_v1=dict(
                breakout_event_overlay_candidates_v1 or {}
            ),
        )
        runtime_snapshot_row = dict(
            directional_runtime_surface_v1.get("runtime_row", runtime_snapshot_row) or {}
        )
        active_action_conflict_guard_v1 = dict(
            directional_runtime_surface_v1.get(
                "active_action_conflict_guard_v1",
                active_action_conflict_guard_v1,
            )
            or {}
        )
        directional_continuation_promotion_v1 = dict(
            directional_runtime_surface_v1.get(
                "directional_continuation_promotion_v1",
                directional_continuation_promotion_v1,
            )
            or {}
        )
        execution_action_diff_v1 = dict(
            directional_runtime_surface_v1.get("execution_action_diff_v1", {}) or {}
        )
        decision_metrics_v1 = {
            "observe_reason": str(observe_reason or ""),
            "action_none_reason": str(action_none_reason or ""),
            **_build_execution_action_diff_flat_fields_v1(execution_action_diff_v1),
        }
        stage_started_at = time.perf_counter()
        payload = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "_decision_generated_ts": time.time(),
            "_runtime_snapshot_generated_ts": runtime_snapshot_row.get("runtime_snapshot_generated_ts", ""),
            "symbol": str(symbol),
            "action": str(action or ""),
            "considered": int(considered),
            "outcome": str(outcome),
            "observe_reason": str(observe_reason or ""),
            "blocked_by": str(blocked_by),
            "runtime_snapshot_key": str(runtime_snapshot_row.get("runtime_snapshot_key", "") or ""),
            "trade_link_key": str(trade_link_key or ""),
            "execution_action_diff_v1": dict(execution_action_diff_v1),
            "signal_age_sec": float(runtime_snapshot_row.get("signal_age_sec", 0.0) or 0.0),
            "bar_age_sec": float(runtime_snapshot_row.get("bar_age_sec", 0.0) or 0.0),
            "decision_latency_ms": int(runtime_snapshot_row.get("decision_latency_ms", 0) or 0),
            "order_submit_latency_ms": int(order_submit_latency_ms or 0),
            "missing_feature_count": int(runtime_snapshot_row.get("missing_feature_count", 0) or 0),
            "data_completeness_ratio": float(runtime_snapshot_row.get("data_completeness_ratio", 0.0) or 0.0),
            "used_fallback_count": int(runtime_snapshot_row.get("used_fallback_count", 0) or 0),
            "compatibility_mode": str(runtime_snapshot_row.get("compatibility_mode", "") or ""),
            "snapshot_payload_bytes": int(runtime_snapshot_row.get("snapshot_payload_bytes", 0) or 0),
            "core_pass": int(core_pass if core_pass_v is None else core_pass_v),
            "core_reason": str(core_reason if core_reason_v is None else core_reason_v),
            "core_allowed_action": str(core_allowed_action if core_allowed_action_v is None else core_allowed_action_v),
            "h1_bias_strength": float(h1_bias_strength if h1_bias_strength_v is None else h1_bias_strength_v),
            "m1_trigger_strength": float(m1_trigger_strength if m1_trigger_strength_v is None else m1_trigger_strength_v),
            "box_state": str(box_state if box_state_v is None else box_state_v),
            "bb_state": str(bb_state if bb_state_v is None else bb_state_v),
            "core_score": float(core_score if core_score_v is None else core_score_v),
            "core_buy_raw": float(core_buy_raw),
            "core_sell_raw": float(core_sell_raw),
            "core_best_raw": float(core_best_raw),
            "core_min_raw": float(core_min_raw),
            "core_margin_raw": float(core_margin_raw),
            "core_tie_band_raw": float(core_tie_band_raw),
            "consumer_archetype_id": str(consumer_archetype_id or ""),
            "consumer_invalidation_id": str(consumer_invalidation_id or ""),
            "consumer_management_profile_id": str(consumer_management_profile_id or ""),
            "setup_id": str(setup_id if setup_id_v is None else setup_id_v),
            "setup_side": str(setup_side if setup_side_v is None else setup_side_v),
            "setup_status": str(setup_status if setup_status_v is None else setup_status_v),
            "setup_trigger_state": str(setup_trigger_state if setup_trigger_state_v is None else setup_trigger_state_v),
            "setup_score": float(setup_score if setup_score_v is None else setup_score_v),
            "setup_entry_quality": float(
                setup_entry_quality if setup_entry_quality_v is None else setup_entry_quality_v
            ),
            "setup_reason": str(setup_reason if setup_reason_v is None else setup_reason_v),
            "wait_score": float(wait_score),
            "wait_conflict": float(wait_conflict),
            "wait_noise": float(wait_noise),
            "wait_penalty": float(wait_penalty),
            "entry_wait_state": str(wait_state.state),
            "entry_wait_hard": int(1 if bool(wait_state.hard_wait) else 0),
            "entry_wait_reason": str(wait_state.reason),
            "entry_wait_selected": int(entry_wait_selected),
            "entry_wait_decision": str(entry_wait_decision),
            "entry_enter_value": float(entry_enter_value),
            "entry_wait_value": float(entry_wait_value),
            "entry_wait_context_v1": dict(wait_metadata.get("entry_wait_context_v1", {}) or {}),
            "entry_wait_bias_bundle_v1": dict(wait_metadata.get("entry_wait_bias_bundle_v1", {}) or {}),
            "entry_wait_state_policy_input_v1": dict(
                wait_metadata.get("entry_wait_state_policy_input_v1", {}) or {}
            ),
            "entry_wait_energy_usage_trace_v1": dict(
                wait_metadata.get("entry_wait_energy_usage_trace_v1", {}) or {}
            ),
            "entry_wait_decision_energy_usage_trace_v1": dict(
                entry_wait_decision_energy_usage_trace_v1 or {}
            ),
            "metrics": dict(decision_metrics_v1),
            "prediction_bundle": prediction_bundle_json,
            "prs_contract_version": "v2",
            "prs_canonical_position_field": "position_snapshot_v2",
            "prs_canonical_response_field": "response_vector_v2",
            "prs_canonical_state_field": "state_vector_v2",
            "prs_canonical_evidence_field": "evidence_vector_v1",
            "prs_canonical_belief_field": "belief_state_v1",
            "prs_canonical_barrier_field": "barrier_state_v1",
            "prs_canonical_forecast_features_field": "forecast_features_v1",
            "prs_canonical_transition_forecast_field": "transition_forecast_v1",
            "prs_canonical_trade_management_forecast_field": "trade_management_forecast_v1",
            "prs_canonical_forecast_gap_metrics_field": "forecast_gap_metrics_v1",
            "prs_canonical_observe_confirm_field": str(
                observe_confirm_runtime_payload.get("prs_canonical_observe_confirm_field", "") or "observe_confirm_v2"
            ),
            "prs_compatibility_observe_confirm_field": str(
                observe_confirm_runtime_payload.get("prs_compatibility_observe_confirm_field", "") or "observe_confirm_v1"
            ),
            "position_snapshot_v2": position_snapshot_v2_json,
            "response_raw_snapshot_v1": response_raw_snapshot_v1_json,
            "response_vector_v2": response_vector_v2_json,
            "state_raw_snapshot_v1": state_raw_snapshot_v1_json,
            "state_vector_v2": state_vector_v2_json,
            "evidence_vector_v1": evidence_vector_v1_json,
            "belief_state_v1": belief_state_v1_json,
            "barrier_state_v1": barrier_state_v1_json,
            "forecast_features_v1": forecast_features_v1_json,
            "transition_forecast_v1": transition_forecast_v1_json,
            "trade_management_forecast_v1": trade_management_forecast_v1_json,
            "forecast_gap_metrics_v1": forecast_gap_metrics_v1_json,
            "transition_side_separation": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("side_separation", 0.0)) or 0.0)),
            "transition_confirm_fake_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("confirm_fake_gap", 0.0)) or 0.0)),
            "transition_reversal_continuation_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("reversal_continuation_gap", 0.0)) or 0.0)),
            "management_continue_fail_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("continue_fail_gap", 0.0)) or 0.0)),
            "management_recover_reentry_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("recover_reentry_gap", 0.0)) or 0.0)),
            "observe_confirm_v2": observe_confirm_v2_json,
            "observe_confirm_v1": observe_confirm_v1_json,
            "observe_confirm_input_contract_v2": dict(
                observe_confirm_runtime_payload.get("observe_confirm_input_contract_v2", {})
            ),
            "observe_confirm_migration_dual_write_v1": dict(
                observe_confirm_runtime_payload.get("observe_confirm_migration_dual_write_v1", {})
            ),
            "observe_confirm_output_contract_v2": dict(
                observe_confirm_runtime_payload.get("observe_confirm_output_contract_v2", {})
            ),
            "observe_confirm_scope_contract_v1": dict(
                observe_confirm_runtime_payload.get("observe_confirm_scope_contract_v1", {})
            ),
            "consumer_input_contract_v1": dict(
                observe_confirm_runtime_payload.get("consumer_input_contract_v1", {})
            ),
            "consumer_input_observe_confirm_field": str(
                observe_confirm_runtime_payload.get("prs_canonical_observe_confirm_field", "") or "observe_confirm_v2"
            ),
            "forecast_assist_v1": dict(core_dec.get("forecast_assist_v1", {}) or {})
            if isinstance(core_dec.get("forecast_assist_v1", {}), dict)
            else {},
            "entry_default_side_gate_v1": dict(core_dec.get("entry_default_side_gate_v1", {}) or {})
            if isinstance(core_dec.get("entry_default_side_gate_v1", {}), dict)
            else {},
            "entry_probe_plan_v1": dict(entry_probe_plan_v1 or {}),
            "edge_pair_law_v1": dict((((shadow_observe_confirm.get("metadata", {}) or {}).get("edge_pair_law_v1", {}) or {})))
            if isinstance(((shadow_observe_confirm.get("metadata", {}) or {}).get("edge_pair_law_v1", {})), dict)
            else {},
            "probe_candidate_v1": dict((((shadow_observe_confirm.get("metadata", {}) or {}).get("probe_candidate_v1", {}) or {})))
            if isinstance(((shadow_observe_confirm.get("metadata", {}) or {}).get("probe_candidate_v1", {})), dict)
            else {},
            "shadow_state_v1": str(shadow_observe_confirm.get("state", "") or ""),
            "shadow_action_v1": str(shadow_observe_confirm.get("action", "") or ""),
            "shadow_reason_v1": str(shadow_observe_confirm.get("reason", "") or ""),
            "shadow_buy_force_v1": (
                "" if shadow_energy_snapshot.get("buy_force", None) is None
                else float(shadow_energy_snapshot.get("buy_force", 0.0) or 0.0)
            ),
            "shadow_sell_force_v1": (
                "" if shadow_energy_snapshot.get("sell_force", None) is None
                else float(shadow_energy_snapshot.get("sell_force", 0.0) or 0.0)
            ),
            "shadow_net_force_v1": (
                "" if shadow_energy_snapshot.get("net_force", None) is None
                else float(shadow_energy_snapshot.get("net_force", 0.0) or 0.0)
            ),
            "semantic_shadow_available": int(
                1 if bool((semantic_shadow_prediction_v1 or {}).get("available")) else 0
            ),
            "semantic_shadow_model_version": str(
                (semantic_shadow_prediction_v1 or {}).get("model_version", "") or ""
            ),
            "semantic_shadow_trace_quality": str(
                (semantic_shadow_prediction_v1 or {}).get("trace_quality_state", "") or ""
            ),
            "semantic_shadow_timing_probability": (
                ""
                if semantic_timing.get("probability") is None
                else float(semantic_timing.get("probability"))
            ),
            "semantic_shadow_timing_threshold": float(
                semantic_timing.get("threshold", getattr(Config, "SEMANTIC_TIMING_THRESHOLD", 0.55))
                or getattr(Config, "SEMANTIC_TIMING_THRESHOLD", 0.55)
            ),
            "semantic_shadow_timing_decision": int(1 if bool(semantic_timing.get("decision")) else 0),
            "semantic_shadow_entry_quality_probability": (
                ""
                if semantic_entry_quality.get("probability") is None
                else float(semantic_entry_quality.get("probability"))
            ),
            "semantic_shadow_entry_quality_threshold": float(
                semantic_entry_quality.get(
                    "threshold",
                    getattr(Config, "SEMANTIC_ENTRY_QUALITY_THRESHOLD", 0.55),
                )
                or getattr(Config, "SEMANTIC_ENTRY_QUALITY_THRESHOLD", 0.55)
            ),
            "semantic_shadow_entry_quality_decision": int(
                1 if bool(semantic_entry_quality.get("decision")) else 0
            ),
            "semantic_shadow_exit_management_probability": (
                ""
                if semantic_exit_management.get("probability") is None
                else float(semantic_exit_management.get("probability"))
            ),
            "semantic_shadow_exit_management_threshold": float(
                semantic_exit_management.get(
                    "threshold",
                    getattr(Config, "SEMANTIC_EXIT_MANAGEMENT_THRESHOLD", 0.55),
                )
                or getattr(Config, "SEMANTIC_EXIT_MANAGEMENT_THRESHOLD", 0.55)
            ),
            "semantic_shadow_exit_management_decision": int(
                1 if bool(semantic_exit_management.get("decision")) else 0
            ),
            "semantic_shadow_should_enter": int(
                1 if bool((semantic_shadow_prediction_v1 or {}).get("should_enter")) else 0
            ),
            "semantic_shadow_action_hint": str(
                (semantic_shadow_prediction_v1 or {}).get("action_hint", "") or ""
            ),
            "semantic_shadow_compare_label": str(semantic_compare_label or ""),
            "semantic_shadow_reason": str((semantic_shadow_prediction_v1 or {}).get("reason", "") or ""),
            "semantic_shadow_activation_state": str(semantic_shadow_activation_state),
            "semantic_shadow_activation_reason": str(semantic_shadow_activation_reason),
            "semantic_live_rollout_mode": str((semantic_live_guard_v1 or {}).get("mode", "") or ""),
            "semantic_live_alert": int(1 if bool((semantic_live_guard_v1 or {}).get("alert_active")) else 0),
            "semantic_live_fallback_reason": str(
                (semantic_live_guard_v1 or {}).get("fallback_reason", "") or ""
            ),
            "semantic_live_symbol_allowed": int(
                1 if bool((semantic_live_guard_v1 or {}).get("symbol_allowed")) else 0
            ),
            "semantic_live_entry_stage_allowed": int(
                1 if bool((semantic_live_guard_v1 or {}).get("entry_stage_allowed")) else 0
            ),
            "semantic_live_threshold_before": int(
                (semantic_live_guard_v1 or {}).get("threshold_before", 0) or 0
            ),
            "semantic_live_threshold_after": int(
                (semantic_live_guard_v1 or {}).get("threshold_after", 0) or 0
            ),
            "semantic_live_threshold_adjustment": int(
                (semantic_live_guard_v1 or {}).get("threshold_adjustment_points", 0) or 0
            ),
            "semantic_live_threshold_applied": int(
                1 if bool((semantic_live_guard_v1 or {}).get("threshold_applied")) else 0
            ),
            "semantic_live_threshold_state": str(semantic_live_threshold_state),
            "semantic_live_threshold_reason": str(semantic_live_threshold_reason),
            "semantic_live_partial_weight": float(
                (semantic_live_guard_v1 or {}).get("partial_live_weight", 0.0) or 0.0
            ),
            "semantic_live_partial_live_applied": int(
                1 if bool((semantic_live_guard_v1 or {}).get("partial_live_applied")) else 0
            ),
            "semantic_live_reason": str((semantic_live_guard_v1 or {}).get("reason", "") or ""),
            "learn_buy_penalty": float(learn_buy_penalty),
            "learn_sell_penalty": float(learn_sell_penalty),
            "preflight_regime": str(preflight_regime),
            "preflight_liquidity": str(preflight_liquidity),
            "preflight_allowed_action": str(preflight_allowed_action),
            "preflight_approach_mode": str(preflight_approach_mode),
            "preflight_reason": str(preflight_reason),
            "last_order_retcode": ("" if last_order_retcode is None else int(last_order_retcode)),
            "last_order_comment": str(last_order_comment or ""),
            "order_block_remaining_sec": ("" if order_block_remaining_sec is None else int(order_block_remaining_sec)),
            "preflight_direction_penalty_applied": float(preflight_direction_penalty_applied),
            "macro_regime": self._regime_name(regime),
            "macro_zone": self._zone_from_regime(regime),
            "volatility_state": self._volatility_state_from_ratio(vol_ratio),
            "entry_score_raw": float(raw_score),
            "contra_score_raw": float(contra_score),
            "effective_entry_threshold": (
                float(effective_threshold) if effective_threshold is not None else float(entry_threshold)
            ),
            "base_entry_threshold": float(entry_threshold),
            "size_multiplier": float(size_multiplier),
            "flow_execution_selection_owner_v1": dict(
                flow_execution_selection_owner_v1 or {}
            ),
            **flow_execution_selection_owner_flat_fields,
            "flow_execution_veto_owner_v1": dict(flow_execution_veto_owner_v1 or {}),
            **flow_execution_veto_owner_flat_fields,
            "active_action_conflict_guard_v1": dict(active_action_conflict_guard_v1 or {}),
            **active_action_conflict_guard_flat_fields,
            **semantic_owner_flat_fields,
            **semantic_owner_detail_fields,
            **entry_candidate_bridge_fields,
            "cooldown_sec": int(cooldown_remaining),
            "entry_stage": str(entry_stage or ""),
            "ai_probability": ("" if ai_probability is None else float(ai_probability)),
            "spread": float(spread_now),
            "utility_u": ("" if utility_u is None else float(utility_u)),
            "utility_p": ("" if utility_p is None else float(utility_p)),
            "utility_p_raw": ("" if utility_p_raw is None else float(utility_p_raw)),
            "utility_p_calibrated": ("" if utility_p_calibrated is None else float(utility_p_calibrated)),
            "utility_w": ("" if utility_w is None else float(utility_w)),
            "utility_l": ("" if utility_l is None else float(utility_l)),
            "utility_cost": ("" if utility_cost is None else float(utility_cost)),
            "utility_context_adj": ("" if utility_context_adj is None else float(utility_context_adj)),
            "utility_stats_ready": int(utility_stats_ready),
            "utility_wins_n": int(utility_wins_n),
            "utility_losses_n": int(utility_losses_n),
            "bb_penalty_usd": float(bb_penalty_usd),
            "bb_flags": "|".join([str(x) for x in (bb_flags or []) if str(x)]),
            "bb_guard_count": int(len(bb_flags or [])),
            "u_min": ("" if u_min is None else float(u_min)),
            "u_pass": ("" if u_pass is None else int(u_pass)),
            "decision_rule_version": str(decision_rule_version or "legacy_v1"),
            "entry_decision_mode": str(decision_mode),
            "action_selected": ("" if action is None else str(action)),
            "action_none_reason": str(action_none_reason or ""),
            "consumer_layer_mode_hard_block_active": bool(consumer_layer_mode_hard_block_active),
            "consumer_layer_mode_suppressed": bool(consumer_layer_mode_suppressed),
            "consumer_policy_live_gate_applied": bool(consumer_policy_live_gate_applied),
            "consumer_policy_block_layer": str(consumer_policy_block_layer or ""),
            "consumer_policy_block_effect": str(consumer_policy_block_effect or ""),
            "consumer_energy_action_readiness": float(consumer_energy_action_readiness),
            "consumer_energy_wait_vs_enter_hint": str(consumer_energy_wait_vs_enter_hint or ""),
            "consumer_energy_soft_block_active": bool(consumer_energy_soft_block_active),
            "consumer_energy_soft_block_reason": str(consumer_energy_soft_block_reason or ""),
            "consumer_energy_soft_block_strength": float(consumer_energy_soft_block_strength),
            "consumer_energy_live_gate_applied": bool(consumer_energy_live_gate_applied),
            "consumer_check_candidate": bool(effective_consumer_check_candidate),
            "consumer_check_display_ready": bool(effective_consumer_check_display_ready),
            "consumer_check_entry_ready": bool(effective_consumer_check_entry_ready),
            "consumer_check_side": str(effective_consumer_check_side or ""),
            "consumer_check_stage": str(effective_consumer_check_stage or ""),
            "consumer_check_reason": str(effective_consumer_check_reason or ""),
            "consumer_check_display_strength_level": int(effective_consumer_check_display_strength_level),
            "consumer_check_display_score": float(
                effective_consumer_check_state_v1.get("display_score", 0.0) or 0.0
            ),
            "consumer_check_display_repeat_count": int(
                effective_consumer_check_state_v1.get("display_repeat_count", 0) or 0
            ),
            "consumer_check_state_v1": dict(effective_consumer_check_state_v1 or {}),
            "ai_used": int(ai_used),
            "ai_missing_reason": str(ai_missing_reason or ""),
            "p7_guarded_size_overlay_v1": dict(p7_guarded_size_overlay_v1 or {}),
            "teacher_label_exploration_active": bool(
                (teacher_label_exploration_entry_v1 or {}).get("active", False)
            ),
            "teacher_label_exploration_enabled": bool(
                (teacher_label_exploration_entry_v1 or {}).get("enabled", False)
            ),
            "teacher_label_exploration_family": str(
                (teacher_label_exploration_entry_v1 or {}).get("family", "") or ""
            ),
            "teacher_label_exploration_reason": str(
                (teacher_label_exploration_entry_v1 or {}).get("activation_reason", "") or ""
            ),
            "teacher_label_exploration_guard_failure_code": str(
                (teacher_label_exploration_entry_v1 or {}).get("guard_failure_code", "") or ""
            ),
            "teacher_label_exploration_soft_block_reason": str(
                (teacher_label_exploration_entry_v1 or {}).get("soft_block_reason", "") or ""
            ),
            "teacher_label_exploration_check_side": str(
                (teacher_label_exploration_entry_v1 or {}).get("check_side", "") or ""
            ),
            "teacher_label_exploration_check_stage": str(
                (teacher_label_exploration_entry_v1 or {}).get("check_stage", "") or ""
            ),
            "teacher_label_exploration_same_dir_count": int(
                (teacher_label_exploration_entry_v1 or {}).get("same_dir_count", 0) or 0
            ),
            "teacher_label_exploration_score_ratio": (
                ""
                if not teacher_label_exploration_entry_v1
                else float((teacher_label_exploration_entry_v1 or {}).get("score_ratio", 0.0) or 0.0)
            ),
            "teacher_label_exploration_threshold_gap": (
                ""
                if not teacher_label_exploration_entry_v1
                else float((teacher_label_exploration_entry_v1 or {}).get("threshold_gap", 0.0) or 0.0)
            ),
            "teacher_label_exploration_size_multiplier": (
                ""
                if not teacher_label_exploration_entry_v1
                else float((teacher_label_exploration_entry_v1 or {}).get("size_multiplier", 0.0) or 0.0)
            ),
            "teacher_label_exploration_entry_v1": dict(teacher_label_exploration_entry_v1 or {}),
        }
        _record_payload_stage("decision_payload_build", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_built",
            f"{str(action or '')}|{str(outcome or '')}|payload",
        )
        stage_started_at = time.perf_counter()
        path_leg_state_by_symbol = getattr(self.runtime, "path_leg_state_by_symbol", None)
        if not isinstance(path_leg_state_by_symbol, dict):
            path_leg_state_by_symbol = {}
            setattr(self.runtime, "path_leg_state_by_symbol", path_leg_state_by_symbol)
        prior_leg_state = path_leg_state_by_symbol.get(str(symbol), runtime_snapshot_row)
        leg_assignment = assign_leg_id(
            str(symbol),
            payload,
            prior_leg_state if isinstance(prior_leg_state, Mapping) else runtime_snapshot_row,
        )
        payload.update(extract_leg_runtime_fields(leg_assignment))
        path_leg_state_by_symbol[str(symbol)] = dict(leg_assignment.get("symbol_state", {}) or {})
        _record_payload_stage("path_leg_assignment", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_leg_done",
            str(payload.get("leg_transition_reason", "") or ""),
        )
        stage_started_at = time.perf_counter()
        path_checkpoint_state_by_symbol = getattr(self.runtime, "path_checkpoint_state_by_symbol", None)
        if not isinstance(path_checkpoint_state_by_symbol, dict):
            path_checkpoint_state_by_symbol = {}
            setattr(self.runtime, "path_checkpoint_state_by_symbol", path_checkpoint_state_by_symbol)
        prior_checkpoint_state = path_checkpoint_state_by_symbol.get(
            str(symbol),
            path_leg_state_by_symbol.get(str(symbol), payload),
        )
        checkpoint_assignment = assign_checkpoint_context(
            str(symbol),
            payload,
            prior_checkpoint_state if isinstance(prior_checkpoint_state, Mapping) else payload,
        )
        payload.update(extract_checkpoint_fields(checkpoint_assignment))
        path_checkpoint_state_by_symbol[str(symbol)] = dict(
            checkpoint_assignment.get("symbol_state", {}) or {}
        )
        _record_payload_stage("path_checkpoint_assignment", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_checkpoint_done",
            str(payload.get("checkpoint_transition_reason", "") or ""),
        )
        stage_started_at = time.perf_counter()
        try:
            record_checkpoint_context(
                runtime=self.runtime,
                symbol=str(symbol),
                runtime_row=payload,
                symbol_state=checkpoint_assignment.get("symbol_state", {}) or {},
                position_state=build_flat_position_state(),
                source="entry_runtime",
                refresh_analysis=False,
            )
        except Exception:
            pass
        _record_payload_stage("path_checkpoint_context_store", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_checkpoint_store_done",
            str(payload.get("checkpoint_type", "") or ""),
        )
        stage_started_at = time.perf_counter()
        payload = _sync_blocked_by_into_wait_payloads_v1(payload, str(blocked_by or ""))
        if isinstance(self.runtime.latest_signal_by_symbol, dict):
            existing_runtime_row = self.runtime.latest_signal_by_symbol.get(str(symbol), {})
            merged_runtime_row = (
                dict(existing_runtime_row)
                if isinstance(existing_runtime_row, dict)
                else {}
            )
            merged_runtime_row.update(payload)
            self.runtime.latest_signal_by_symbol[str(symbol)] = merged_runtime_row
        _record_payload_stage("runtime_row_merge", stage_started_at)
        _debug_breadcrumb(
            "decision_payload_return_ready",
            f"{str(action or '')}|{str(outcome or '')}|return",
        )
        return payload

    def _mark_skip(
        reason: str,
        *,
        blocked_by_value: str = "",
        observe_reason_value: str | None = None,
        action_none_reason_value: str | None = None,
        **extra,
    ):
        nonlocal entry_wait_decision
        try:
            row = self.runtime.latest_signal_by_symbol.get(symbol, {}) if isinstance(self.runtime.latest_signal_by_symbol, dict) else {}
            if not isinstance(row, dict):
                row = {}
            action_v = str((extra or {}).get("action", action or "") or "")
            effective_blocked_by_value = str(blocked_by_value or reason or "")
            wait_input_row = _wait_input_row(
                action_value=action_v,
                observe_reason_value=observe_reason_value,
                blocked_by_value=effective_blocked_by_value,
                action_none_reason_value=action_none_reason_value,
                box_state_value=(
                    None
                    if "box_state" not in (extra or {})
                    else str((extra or {}).get("box_state", "") or "")
                ),
                bb_state_value=(
                    None
                    if "bb_state" not in (extra or {})
                    else str((extra or {}).get("bb_state", "") or "")
                ),
                core_allowed_action_value=(
                    None
                    if "core_allowed_action" not in (extra or {})
                    else str((extra or {}).get("core_allowed_action", "") or "")
                ),
                setup_status_value=(
                    None
                    if "setup_status" not in (extra or {})
                    else str((extra or {}).get("setup_status", "") or "")
                ),
                setup_reason_value=(
                    None
                    if "setup_reason" not in (extra or {})
                    else str((extra or {}).get("setup_reason", "") or "")
                ),
                setup_trigger_state_value=(
                    None
                    if "setup_trigger_state" not in (extra or {})
                    else str((extra or {}).get("setup_trigger_state", "") or "")
                ),
            )
            wait_state = self._wait_engine.build_entry_wait_state_from_row(
                symbol=str(symbol),
                row=wait_input_row,
            )
            wait_metadata = _sync_blocked_by_into_wait_payloads_v1(
                dict(wait_state.metadata or {}),
                str(effective_blocked_by_value or ""),
            )
            normalized_wait_decision = str(entry_wait_decision or ("skip" if int(entry_wait_selected) <= 0 else ""))
            if normalized_wait_decision:
                entry_wait_decision = normalized_wait_decision
            row["entry_considered"] = 1
            row["observe_reason"] = str(wait_input_row.get("observe_reason", "") or "")
            row["blocked_by"] = str(effective_blocked_by_value)
            row["action_none_reason"] = str(wait_input_row.get("action_none_reason", "") or "")
            row["entry_skip_reason"] = str(reason)
            row["entry_wait_state"] = str(wait_state.state)
            row["entry_wait_hard"] = int(1 if bool(wait_state.hard_wait) else 0)
            row["entry_wait_reason"] = str(wait_state.reason)
            row["entry_wait_selected"] = int(entry_wait_selected)
            row["entry_wait_decision"] = str(normalized_wait_decision)
            row["entry_enter_value"] = float(entry_enter_value)
            row["entry_wait_value"] = float(entry_wait_value)
            row["entry_wait_context_v1"] = dict(wait_metadata.get("entry_wait_context_v1", {}) or {})
            row["entry_wait_bias_bundle_v1"] = dict(wait_metadata.get("entry_wait_bias_bundle_v1", {}) or {})
            row["entry_wait_state_policy_input_v1"] = dict(
                wait_metadata.get("entry_wait_state_policy_input_v1", {}) or {}
            )
            row["entry_wait_energy_usage_trace_v1"] = dict(
                wait_metadata.get("entry_wait_energy_usage_trace_v1", {}) or {}
            )
            row["entry_wait_decision_energy_usage_trace_v1"] = dict(
                entry_wait_decision_energy_usage_trace_v1 or {}
            )
            row = _sync_blocked_by_into_wait_payloads_v1(row, str(effective_blocked_by_value or ""))
            for k, v in (extra or {}).items():
                row[k] = v
            (
                effective_consumer_check_candidate,
                effective_consumer_check_display_ready,
                effective_consumer_check_entry_ready,
                effective_consumer_check_side,
                effective_consumer_check_stage,
                effective_consumer_check_reason,
                effective_consumer_check_display_strength_level,
                effective_consumer_check_state_v1,
            ) = _resolve_effective_consumer_check_state(
                blocked_by_value=str(effective_blocked_by_value),
                action_none_reason_value=action_none_reason_value,
                action_value=action_v,
            )
            row["consumer_check_candidate"] = bool(effective_consumer_check_candidate)
            row["consumer_check_display_ready"] = bool(effective_consumer_check_display_ready)
            row["consumer_check_entry_ready"] = bool(effective_consumer_check_entry_ready)
            row["consumer_check_side"] = str(effective_consumer_check_side or "")
            row["consumer_check_stage"] = str(effective_consumer_check_stage or "")
            row["consumer_check_reason"] = str(effective_consumer_check_reason or "")
            row["consumer_check_display_strength_level"] = int(effective_consumer_check_display_strength_level)
            row["consumer_check_display_score"] = float(
                effective_consumer_check_state_v1.get("display_score", 0.0) or 0.0
            )
            row["consumer_check_display_repeat_count"] = int(
                effective_consumer_check_state_v1.get("display_repeat_count", 0) or 0
            )
            row["consumer_check_state_v1"] = dict(effective_consumer_check_state_v1 or {})
            if isinstance(self.runtime.latest_signal_by_symbol, dict):
                self.runtime.latest_signal_by_symbol[symbol] = row
            if str(reason or "").strip().lower() != "entered":
                side = str(action_v or action or "").strip().upper()
                current_price = 0.0
                try:
                    if side == "BUY":
                        current_price = float(getattr(tick, "ask", 0.0) or 0.0)
                    elif side == "SELL":
                        current_price = float(getattr(tick, "bid", 0.0) or 0.0)
                except Exception:
                    current_price = 0.0
                wait_reason_text = str(
                    row.get("entry_wait_reason")
                    or row.get("entry_skip_reason")
                    or row.get("blocked_by")
                    or reason
                    or ""
                )
                wait_signature = self.runtime.build_wait_message_signature(
                    str(symbol),
                    side,
                    reason=wait_reason_text,
                    row=row,
                )
                if self.runtime.should_notify_wait_message(str(symbol), wait_signature):
                    wait_message = self.runtime.format_wait_message(
                        str(symbol),
                        side,
                        float(current_price),
                        int(pos_count),
                        int(Config.MAX_POSITIONS),
                        reason=wait_reason_text,
                        row=row,
                    )
                    if wait_message:
                        self.runtime.notify(wait_message)
        except Exception:
            return

    def _apply_wait_routing(
        blocked_reason: str,
        *,
        blocked_by_value: str = "",
        observe_reason_value: str = "",
        action_none_reason_value: str | None = None,
        action_value: str = "",
        raw_score_value: float = 0.0,
        effective_threshold_value: float | None = None,
        utility_u_value: float | None = None,
        utility_u_min_value: float | None = None,
    ) -> tuple[str, str]:
        nonlocal entry_wait_selected, entry_wait_decision, entry_enter_value, entry_wait_value
        nonlocal entry_wait_energy_usage_trace_v1, entry_wait_decision_energy_usage_trace_v1
        effective_threshold_local = float(dynamic_threshold if effective_threshold_value is None else effective_threshold_value)
        wait_eval = self._wait_engine.evaluate_entry_wait_decision(
            symbol=str(symbol),
            row=_wait_input_row(
                action_value=str(action_value or action or ""),
                observe_reason_value=str(observe_reason_value or ""),
                blocked_by_value=str(blocked_by_value or ""),
                action_none_reason_value=action_none_reason_value,
            ),
            blocked_reason=str(blocked_reason or ""),
            raw_entry_score=float(raw_score_value),
            effective_threshold=float(effective_threshold_local),
            core_score=float(core_score),
            utility_u=utility_u_value,
            utility_u_min=utility_u_min_value,
        )
        entry_wait_selected = int(1 if bool(wait_eval.get("selected", False)) else 0)
        entry_wait_decision = str(wait_eval.get("decision", "skip") or "skip")
        entry_enter_value = float(wait_eval.get("enter_value", 0.0) or 0.0)
        entry_wait_value = float(wait_eval.get("wait_value", 0.0) or 0.0)
        entry_wait_energy_usage_trace_v1 = dict(wait_eval.get("entry_wait_energy_usage_trace_v1", {}) or {})
        entry_wait_decision_energy_usage_trace_v1 = dict(
            wait_eval.get("entry_wait_decision_energy_usage_trace_v1", {}) or {}
        )
        outcome = "wait" if entry_wait_selected > 0 else "skipped"
        return outcome, str(blocked_reason or "")

    def _threshold_relief_points() -> int:
        setup_u = str(setup_id or "").lower()
        stage_u = str(entry_stage or "").lower()
        symbol_u = str(symbol or "").upper()
        if symbol_u == "NAS100":
            if (
                setup_u == "breakout_retest_sell"
                and stage_u == "balanced"
                and str(preflight_allowed_action).upper() == "SELL_ONLY"
                and str(box_state).upper() == "BELOW"
                and str(bb_state).upper() == "LOWER_EDGE"
            ):
                return 8
        if symbol_u == "BTCUSD":
            if (
                setup_u == "range_lower_reversal_buy"
                and stage_u == "balanced"
                and str(box_state).upper() == "LOWER"
                and str(bb_state).upper() in {"MID", "UNKNOWN"}
            ):
                return 5
        return 0

    def _refresh_prediction_bundle(raw_score_value: float, contra_score_value: float, effective_threshold_value: float) -> None:
        nonlocal prediction_bundle
        wait_state = self._wait_engine.build_entry_wait_state_from_row(
            symbol=str(symbol),
            row=_wait_input_row(
                action_value=str(action or ""),
                blocked_by_value="",
            ),
        )
        selected_setup = SetupCandidate(
            setup_id=str(setup_id or ""),
            side=str(setup_side or action or ""),
            status=str(setup_status or "pending"),
            trigger_state=str(setup_trigger_state or "UNKNOWN"),
            entry_quality=float(setup_entry_quality or 0.0),
            score=float(setup_score or 0.0),
            metadata={"reason": str(setup_reason or "")},
        )
        entry_pred = self._entry_predictor.predict(
            context=setup_context,
            setup=selected_setup,
            metrics={
                "raw_score": float(raw_score_value),
                "contra_score": float(contra_score_value),
                "effective_threshold": float(effective_threshold_value),
                "core_score": float(core_score),
            },
        )
        wait_pred = self._wait_predictor.predict_entry_wait(
            context=setup_context,
            setup=selected_setup,
            wait_state=wait_state,
            metrics={
                "raw_score": float(raw_score_value),
                "effective_threshold": float(effective_threshold_value),
                "wait_score": float(wait_score),
            },
        )
        prediction_bundle = {
            "entry": dict(entry_pred or {}),
            "wait": dict(wait_pred or {}),
            "exit": {},
            "reverse": {},
            "metadata": {
                "phase": "entry",
                "mode": "shadow",
                "symbol": str(symbol),
                "decision_mode": str(decision_mode),
            },
        }
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_prediction_v1",
                payload=prediction_bundle,
            )
        except Exception:
            pass

    def _calibrate_p(prob_raw: float, stage_prior: float, stats_obj: dict | None) -> float:
        p = max(0.0, min(1.0, float(prob_raw)))
        prior = max(0.0, min(1.0, float(stage_prior)))
        if not bool(getattr(Config, "ENTRY_UTILITY_P_CALIBRATION_ENABLED", True)):
            return p
        min_blend = max(0.0, min(1.0, float(getattr(Config, "ENTRY_UTILITY_P_CALIBRATION_BLEND_MIN", 0.20))))
        target_n = max(1, int(getattr(Config, "ENTRY_UTILITY_P_CALIBRATION_SAMPLES", 120)))
        wins_n = int((stats_obj or {}).get("wins_n", 0) or 0) if isinstance(stats_obj, dict) else 0
        losses_n = int((stats_obj or {}).get("losses_n", 0) or 0) if isinstance(stats_obj, dict) else 0
        n = max(0, wins_n + losses_n)
        confidence = min(1.0, float(n) / float(target_n))
        blend = min_blend + ((1.0 - min_blend) * confidence)
        out = (blend * p) + ((1.0 - blend) * prior)
        lo = max(0.0, min(1.0, float(getattr(Config, "ENTRY_UTILITY_P_CLIP_LOW", 0.05))))
        hi = max(lo, min(1.0, float(getattr(Config, "ENTRY_UTILITY_P_CLIP_HIGH", 0.95))))
        return max(lo, min(hi, float(out)))

    max_positions_for_symbol = int(Config.get_max_positions(symbol))
    if pos_count >= max_positions_for_symbol:
        _record_entry_prefront_stage("initial_limits", entry_prefront_stage_started_at)
        _mark_skip("max_positions_reached", pos_count=int(pos_count), max_positions=max_positions_for_symbol)
        _store_entry_prefront_profile(
            exit_state="max_positions_reached",
            blocked_by_value="max_positions_reached",
        )
        self._append_entry_decision_log(
            _decision_payload(
                considered=1,
                outcome="skipped",
                blocked_by="max_positions_reached",
                raw_score=float(max(buy_s, sell_s)),
                contra_score=float(min(buy_s, sell_s)),
            )
        )
        return

    cooldown_ok = (time.time() - self.runtime.last_entry_time.get(symbol, 0)) > Config.ENTRY_COOLDOWN
    if not cooldown_ok:
        _record_entry_prefront_stage("initial_limits", entry_prefront_stage_started_at)
        _mark_skip("entry_cooldown", cooldown_sec_remaining=max(0, int(Config.ENTRY_COOLDOWN - (time.time() - self.runtime.last_entry_time.get(symbol, 0)))))
        _store_entry_prefront_profile(
            exit_state="entry_cooldown",
            blocked_by_value="entry_cooldown",
        )
        self._append_entry_decision_log(
            _decision_payload(
                considered=1,
                outcome="skipped",
                blocked_by="entry_cooldown",
                raw_score=float(max(buy_s, sell_s)),
                contra_score=float(min(buy_s, sell_s)),
            )
        )
        return

    _set_entry_prefront_stage("build_entry_context")
    entry_front_started_at = time.perf_counter()
    entry_front_stage_timings_ms: dict[str, float] = {}

    def _record_entry_front_stage(stage_name: str, started_at: float) -> None:
        entry_front_stage_timings_ms[str(stage_name)] = round(
            (time.perf_counter() - float(started_at)) * 1000.0,
            3,
        )

    try:
        stage_started_at = time.perf_counter()
        shadow_bundle = self._context_classifier.build_entry_context(
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            scorer=scorer,
            result=result,
            buy_s=buy_s,
            sell_s=sell_s,
        )
        _record_entry_front_stage("build_entry_context", stage_started_at)
        shadow_context = shadow_bundle.get("context")
        shadow_position_snapshot_obj = shadow_bundle.get("position_snapshot")
        shadow_response_raw_obj = shadow_bundle.get("response_raw_snapshot")
        shadow_response_v2_obj = shadow_bundle.get("response_vector_v2")
        shadow_state_raw_obj = shadow_bundle.get("state_raw_snapshot")
        shadow_state_v2_obj = shadow_bundle.get("state_vector_v2")
        shadow_evidence_obj = shadow_bundle.get("evidence_vector")
        shadow_belief_obj = shadow_bundle.get("belief_state")
        shadow_barrier_obj = shadow_bundle.get("barrier_state")
        shadow_forecast_features_obj = shadow_bundle.get("forecast_features")
        shadow_transition_forecast_obj = shadow_bundle.get("transition_forecast")
        shadow_trade_management_forecast_obj = shadow_bundle.get("trade_management_forecast")
        shadow_energy_obj = shadow_bundle.get("energy_snapshot")
        shadow_observe = shadow_bundle.get("observe_confirm")
        stage_started_at = time.perf_counter()
        _record_entry_prefront_stage("build_entry_context", entry_prefront_stage_started_at)
        _set_entry_prefront_stage("extract_shadow_handoff")
        shadow_context_metadata_v1 = _safe_mapping(getattr(shadow_context, "metadata", {}))
        shadow_observe_confirm = _safe_mapping(shadow_observe)
        _record_entry_front_stage("extract_shadow_handoff", stage_started_at)
        _record_entry_prefront_stage("extract_shadow_handoff", entry_prefront_stage_started_at)
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_shadow_compare_v1",
                payload={
                    "contract_version": "entry_shadow_compare_v1",
                    "symbol": str(symbol),
                    "observe_state": str(shadow_observe_confirm.get("state", "") or ""),
                    "observe_action": str(shadow_observe_confirm.get("action", "") or ""),
                    "observe_reason": str(shadow_observe_confirm.get("reason", "") or ""),
                    "context_metadata_keys": int(len(shadow_context_metadata_v1)),
                    "has_position_snapshot": bool(shadow_position_snapshot_obj is not None),
                    "has_response_snapshot": bool(shadow_response_v2_obj is not None),
                    "has_state_snapshot": bool(shadow_state_v2_obj is not None),
                    "has_evidence_snapshot": bool(shadow_evidence_obj is not None),
                    "has_forecast_snapshot": bool(shadow_forecast_features_obj is not None),
                },
            )
        except Exception:
            pass
    except Exception:
        shadow_context_metadata_v1 = {}
        shadow_position_snapshot_obj = None
        shadow_response_raw_obj = None
        shadow_response_v2_obj = None
        shadow_state_raw_obj = None
        shadow_state_v2_obj = None
        shadow_evidence_obj = None
        shadow_belief_obj = None
        shadow_barrier_obj = None
        shadow_forecast_features_obj = None
        shadow_transition_forecast_obj = None
        shadow_trade_management_forecast_obj = None
        shadow_energy_obj = None
        shadow_position_snapshot_v2 = {}
        shadow_response_raw_snapshot_v1 = {}
        shadow_response_vector_v2 = {}
        shadow_state_raw_snapshot_v1 = {}
        shadow_state_vector_v2 = {}
        shadow_evidence_vector_v1 = {}
        shadow_belief_state_v1 = {}
        shadow_barrier_state_v1 = {}
        shadow_forecast_features_v1 = {}
        shadow_transition_forecast_v1 = {}
        shadow_trade_management_forecast_v1 = {}
        shadow_energy_snapshot = {}
        shadow_observe_confirm = {}
        shadow_runtime_maps_materialized = True

    stage_started_at = time.perf_counter()
    _set_entry_prefront_stage("resolve_entry_handoff_ids")
    management_profile_id, invalidation_id = _resolve_entry_handoff_ids(
        shadow_observe_confirm=shadow_observe_confirm,
        shadow_context_metadata_v1=shadow_context_metadata_v1,
    )
    _record_entry_front_stage("resolve_entry_handoff_ids", stage_started_at)
    _record_entry_prefront_stage("resolve_entry_handoff_ids", entry_prefront_stage_started_at)

    action = None
    score = 0
    reasons = []
    has_sell = any(int(p.type) == int(ORDER_TYPE_SELL) for p in my_positions)
    has_buy = any(int(p.type) == int(ORDER_TYPE_BUY) for p in my_positions)
    stage_started_at = time.perf_counter()
    _set_entry_prefront_stage("core_action_decision")
    core_dec = self._core_action_decision(
        symbol=str(symbol),
        tick=tick,
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=float(buy_s),
        sell_s=float(sell_s),
        has_buy=bool(has_buy),
        has_sell=bool(has_sell),
        entry_context_bundle=shadow_bundle if isinstance(shadow_bundle, dict) else None,
    )
    _record_entry_front_stage("core_action_decision", stage_started_at)
    _record_entry_prefront_stage("core_action_decision", entry_prefront_stage_started_at)
    core_pass = int(core_dec.get("core_pass", 0) or 0)
    core_reason = str(core_dec.get("core_reason", "") or "")
    core_allowed_action = str(core_dec.get("core_allowed_action", "NONE") or "NONE")
    h1_bias_strength = float(core_dec.get("h1_bias_strength", 0.0) or 0.0)
    m1_trigger_strength = float(core_dec.get("m1_trigger_strength", 0.0) or 0.0)
    box_state = str(core_dec.get("box_state", "UNKNOWN") or "UNKNOWN")
    bb_state = str(core_dec.get("bb_state", "UNKNOWN") or "UNKNOWN")
    core_score = float(core_dec.get("core_score", 0.0) or 0.0)
    core_buy_raw = float(core_dec.get("core_buy_raw", 0.0) or 0.0)
    core_sell_raw = float(core_dec.get("core_sell_raw", 0.0) or 0.0)
    core_best_raw = float(core_dec.get("core_best_raw", 0.0) or 0.0)
    core_min_raw = float(core_dec.get("core_min_raw", 0.0) or 0.0)
    core_margin_raw = float(core_dec.get("core_margin_raw", 0.0) or 0.0)
    core_tie_band_raw = float(core_dec.get("core_tie_band_raw", 0.0) or 0.0)
    wait_score = float(core_dec.get("wait_score", 0.0) or 0.0)
    wait_conflict = float(core_dec.get("wait_conflict", 0.0) or 0.0)
    wait_noise = float(core_dec.get("wait_noise", 0.0) or 0.0)
    wait_penalty = float(core_dec.get("wait_penalty", 0.0) or 0.0)
    learn_buy_penalty = float(core_dec.get("learn_buy_penalty", 0.0) or 0.0)
    learn_sell_penalty = float(core_dec.get("learn_sell_penalty", 0.0) or 0.0)
    preflight_regime = str(core_dec.get("preflight_regime", "UNKNOWN") or "UNKNOWN")
    preflight_liquidity = str(core_dec.get("preflight_liquidity", "OK") or "OK")
    preflight_allowed_action = str(core_dec.get("preflight_allowed_action", "BOTH") or "BOTH")
    preflight_approach_mode = str(core_dec.get("preflight_approach_mode", "MIX") or "MIX")
    preflight_reason = str(core_dec.get("preflight_reason", "") or "")
    preflight_direction_penalty_applied = float(core_dec.get("preflight_direction_penalty_applied", 0.0) or 0.0)
    consumer_layer_mode_hard_block_active = bool(core_dec.get("consumer_layer_mode_hard_block_active", False))
    consumer_layer_mode_suppressed = bool(core_dec.get("consumer_layer_mode_suppressed", False))
    consumer_policy_live_gate_applied = bool(core_dec.get("consumer_policy_live_gate_applied", False))
    consumer_policy_block_layer = str(core_dec.get("consumer_policy_block_layer", "") or "")
    consumer_policy_block_effect = str(core_dec.get("consumer_policy_block_effect", "") or "")
    consumer_energy_action_readiness = float(core_dec.get("consumer_energy_action_readiness", 0.0) or 0.0)
    consumer_energy_wait_vs_enter_hint = str(core_dec.get("consumer_energy_wait_vs_enter_hint", "") or "")
    consumer_energy_soft_block_active = bool(core_dec.get("consumer_energy_soft_block_active", False))
    consumer_energy_soft_block_reason = str(core_dec.get("consumer_energy_soft_block_reason", "") or "")
    consumer_energy_soft_block_strength = float(core_dec.get("consumer_energy_soft_block_strength", 0.0) or 0.0)
    consumer_energy_live_gate_applied = bool(core_dec.get("consumer_energy_live_gate_applied", False))
    consumer_archetype_id = str(core_dec.get("consumer_archetype_id", "") or "")
    consumer_invalidation_id = str(core_dec.get("consumer_invalidation_id", "") or "")
    consumer_management_profile_id = str(core_dec.get("consumer_management_profile_id", "") or "")
    if consumer_archetype_id and not str(shadow_observe_confirm.get("archetype_id", "") or "").strip():
        shadow_observe_confirm["archetype_id"] = consumer_archetype_id
    if consumer_invalidation_id and not str(shadow_observe_confirm.get("invalidation_id", "") or "").strip():
        shadow_observe_confirm["invalidation_id"] = consumer_invalidation_id
    if consumer_management_profile_id and not str(shadow_observe_confirm.get("management_profile_id", "") or "").strip():
        shadow_observe_confirm["management_profile_id"] = consumer_management_profile_id
    entry_default_side_gate_v1 = (
        dict(core_dec.get("entry_default_side_gate_v1", {}) or {})
        if isinstance(core_dec.get("entry_default_side_gate_v1", {}), dict)
        else {}
    )
    entry_probe_plan_v1 = (
        dict(core_dec.get("entry_probe_plan_v1", {}) or {})
        if isinstance(core_dec.get("entry_probe_plan_v1", {}), dict)
        else {}
    )
    consumer_check_state_v1 = (
        dict(core_dec.get("consumer_check_state_v1", {}) or {})
        if isinstance(core_dec.get("consumer_check_state_v1", {}), dict)
        else {}
    )
    consumer_check_candidate = bool(core_dec.get("consumer_check_candidate", False))
    consumer_check_display_ready = bool(core_dec.get("consumer_check_display_ready", False))
    consumer_check_entry_ready = bool(core_dec.get("consumer_check_entry_ready", False))
    consumer_check_side = str(core_dec.get("consumer_check_side", "") or "")
    consumer_check_stage = str(core_dec.get("consumer_check_stage", "") or "")
    consumer_check_reason = str(core_dec.get("consumer_check_reason", "") or "")
    consumer_check_display_strength_level = int(
        core_dec.get("consumer_check_display_strength_level", 0) or 0
    )
    consumer_check_display_score = float(
        core_dec.get("consumer_check_display_score", 0.0) or 0.0
    )
    consumer_check_display_repeat_count = int(
        core_dec.get("consumer_check_display_repeat_count", 0) or 0
    )
    action = core_dec.get("action")
    baseline_action_side_v1 = _resolve_directional_baseline_action_side_v1(
        action,
        consumer_check_side,
        setup_side,
        core_allowed_action,
    )
    original_action_side_v1 = str(baseline_action_side_v1 or "")
    observe_reason = str(
        core_dec.get("observe_reason", "")
        or shadow_observe_confirm.get("reason", "")
        or ""
    )
    action_none_reason = str(core_dec.get("action_none_reason", "") or "")
    core_blocked_reason = str(core_dec.get("blocked_by", "") or "")
    blocked_reason = str(core_blocked_reason or "")
    symbol_u = str(symbol or "").upper().strip()
    _set_entry_prefront_stage("active_action_conflict_guard")
    current_cycle_runtime_row_v1 = _current_entry_runtime_signal_row(refresh_current_cycle=True)
    active_action_conflict_guard_v1 = _build_active_action_conflict_guard_v1(
        symbol=str(symbol),
        baseline_action=str(baseline_action_side_v1 or ""),
        setup_id=str(setup_id or ""),
        setup_reason=str(setup_reason or ""),
        runtime_signal_row=current_cycle_runtime_row_v1,
        forecast_state25_log_only_overlay_trace_v1=forecast_state25_log_only_overlay_trace_v1,
        belief_action_hint_v1=belief_action_hint_v1,
        barrier_action_hint_v1=barrier_action_hint_v1,
        countertrend_continuation_signal_v1=countertrend_continuation_signal_v1,
    )
    flow_execution_veto_owner_v1 = _build_flow_execution_veto_owner_v1(
        symbol=str(symbol),
        baseline_action=str(
            active_action_conflict_guard_v1.get("baseline_action", "") or baseline_action_side_v1 or ""
        ),
        setup_id=str(setup_id or ""),
        setup_reason=str(setup_reason or ""),
        runtime_signal_row=current_cycle_runtime_row_v1,
    )
    directional_continuation_promotion_v1 = _build_directional_continuation_promotion_v1(
        symbol=str(symbol),
        baseline_action=str(
            active_action_conflict_guard_v1.get("baseline_action", "") or baseline_action_side_v1 or ""
        ),
        runtime_signal_row=current_cycle_runtime_row_v1,
        active_action_conflict_guard_v1=active_action_conflict_guard_v1,
    )
    flow_execution_selection_owner_v1 = _build_flow_execution_selection_owner_v1(
        symbol=str(symbol),
        legacy_action=str(
            active_action_conflict_guard_v1.get("baseline_action", "") or baseline_action_side_v1 or ""
        ),
        runtime_signal_row=current_cycle_runtime_row_v1,
    )
    if bool(active_action_conflict_guard_v1.get("guard_applied", False)):
        action = None
        observe_reason = str(
            active_action_conflict_guard_v1.get("downgraded_observe_reason", "")
            or observe_reason
            or "directional_conflict_watch"
        )
        action_none_reason = str(
            active_action_conflict_guard_v1.get("failure_label", "")
            or action_none_reason
            or "wrong_side_conflict_pressure"
        )
        core_blocked_reason = str(
            active_action_conflict_guard_v1.get("failure_code", "")
            or "active_action_conflict_guard"
        )
        blocked_reason = str(core_blocked_reason or "")
    if bool(flow_execution_veto_owner_v1.get("veto_applied", False)):
        action = None
        observe_reason = str(
            flow_execution_veto_owner_v1.get("downgraded_observe_reason", "")
            or observe_reason
            or "flow_execution_veto_wait"
        )
        action_none_reason = str(
            flow_execution_veto_owner_v1.get("failure_label", "")
            or action_none_reason
            or "bear_continuation_buy_veto"
        )
        core_blocked_reason = str(
            flow_execution_veto_owner_v1.get("failure_code", "")
            or "flow_execution_veto_owner"
        )
        blocked_reason = str(core_blocked_reason or "")
    if bool(directional_continuation_promotion_v1.get("active", False)) and not bool(
        flow_execution_selection_owner_v1.get("selection_active", False)
    ):
        promoted_action_v1 = str(directional_continuation_promotion_v1.get("promoted_action", "") or "")
        if promoted_action_v1 in {"BUY", "SELL"} and not bool(
            flow_execution_veto_owner_v1.get("veto_applied", False)
        ):
            action = str(promoted_action_v1)
            core_pass = max(1, int(core_pass))
            core_reason = str(
                directional_continuation_promotion_v1.get("promotion_reason", "")
                or "directional_continuation_overlay_promotion"
            )
            core_allowed_action = str(action)
            action_none_reason = ""
            core_blocked_reason = ""
            blocked_reason = ""
            entry_stage = str(
                directional_continuation_promotion_v1.get("recommended_entry_stage", entry_stage)
                or entry_stage
            )
    if bool(flow_execution_selection_owner_v1.get("selection_active", False)):
        selection_action_v1 = str(
            flow_execution_selection_owner_v1.get("selected_action", "") or ""
        ).upper().strip()
        if selection_action_v1 in {"BUY", "SELL"} and bool(
            flow_execution_selection_owner_v1.get("execution_apply_allowed", False)
        ):
            action = str(selection_action_v1)
            setup_side = str(selection_action_v1)
            core_pass = max(1, int(core_pass))
            core_reason = "flow_execution_selection_owner"
            core_allowed_action = str(selection_action_v1)
            action_none_reason = ""
            core_blocked_reason = ""
            blocked_reason = ""
        elif selection_action_v1 == "WAIT":
            action = None
            observe_reason = str(
                flow_execution_selection_owner_v1.get("downgraded_observe_reason", "")
                or observe_reason
                or "flow_selection_owner_wait"
            )
            action_none_reason = str(
                flow_execution_selection_owner_v1.get("failure_label", "")
                or action_none_reason
                or "flow_selection_wait"
            )
            core_blocked_reason = str(
                flow_execution_selection_owner_v1.get("failure_code", "")
                or "flow_execution_selection_owner"
            )
            blocked_reason = str(core_blocked_reason or "")
    _record_entry_prefront_stage("active_action_conflict_guard", entry_prefront_stage_started_at)
    if (
        not action
        and not bool(active_action_conflict_guard_v1.get("guard_applied", False))
        and not bool(flow_execution_veto_owner_v1.get("veto_applied", False))
        and not bool(flow_execution_selection_owner_v1.get("selection_active", False))
    ):
        _set_entry_prefront_stage("teacher_label_exploration")
        teacher_label_side_hint_v1 = str(consumer_check_side or "").upper().strip()
        if teacher_label_side_hint_v1 in {"BUY", "SELL"}:
            teacher_label_runtime_row_v1 = _current_entry_runtime_signal_row()
            try:
                teacher_label_score_v1 = max(
                    float(teacher_label_runtime_row_v1.get("buy_score", 0.0) or 0.0),
                    float(teacher_label_runtime_row_v1.get("sell_score", 0.0) or 0.0),
                    float(max(buy_s, sell_s)),
                )
            except (TypeError, ValueError):
                teacher_label_score_v1 = float(max(buy_s, sell_s))
            try:
                teacher_label_threshold_v1 = float(
                    teacher_label_runtime_row_v1.get("entry_threshold", 0.0)
                    or teacher_label_runtime_row_v1.get("base_entry_threshold", 0.0)
                    or entry_threshold
                    or 0.0
                )
            except (TypeError, ValueError):
                teacher_label_threshold_v1 = float(entry_threshold or 0.0)
            teacher_label_same_dir_count_v1 = sum(
                1
                for p in (my_positions or [])
                if (
                    int(getattr(p, "type", -1)) == int(ORDER_TYPE_BUY)
                    and teacher_label_side_hint_v1 == "BUY"
                )
                or (
                    int(getattr(p, "type", -1)) == int(ORDER_TYPE_SELL)
                    and teacher_label_side_hint_v1 == "SELL"
                )
            )
            teacher_label_exploration_action_hint_v1 = _build_teacher_label_exploration_entry_v1(
                symbol=str(symbol),
                action=str(teacher_label_side_hint_v1),
                observe_reason=str(observe_reason or ""),
                action_none_reason=str(action_none_reason or ""),
                blocked_by=str(core_blocked_reason or ""),
                probe_scene_id=str(
                    entry_probe_plan_v1.get("symbol_scene_relief", "")
                    or consumer_check_state_v1.get("probe_scene_id", "")
                    or ""
                ),
                consumer_check_state_v1=consumer_check_state_v1,
                guard_failure_code=str(core_blocked_reason or action_none_reason or ""),
                score=float(teacher_label_score_v1),
                effective_threshold=float(teacher_label_threshold_v1),
                same_dir_count=int(teacher_label_same_dir_count_v1),
            )
            teacher_label_exploration_entry_v1 = dict(teacher_label_exploration_action_hint_v1)
            if bool(teacher_label_exploration_action_hint_v1.get("active")):
                action = str(teacher_label_side_hint_v1)
                core_pass = max(1, int(core_pass))
                if not str(core_allowed_action or "").strip() or str(core_allowed_action).upper() == "NONE":
                    core_allowed_action = str(teacher_label_side_hint_v1)
                if not str(core_reason or "").strip():
                    core_reason = "teacher_label_exploration_action_hint"
        _record_entry_prefront_stage("teacher_label_exploration", entry_prefront_stage_started_at)
    if (
        not action
        and not bool(active_action_conflict_guard_v1.get("guard_applied", False))
        and not bool(flow_execution_veto_owner_v1.get("veto_applied", False))
        and not bool(flow_execution_selection_owner_v1.get("selection_active", False))
    ):
        _set_entry_prefront_stage("semantic_probe_bridge")
        should_attempt_semantic_probe_bridge = _should_attempt_semantic_probe_bridge(
            symbol=str(symbol),
            core_reason=str(core_reason),
            observe_reason=str(observe_reason),
            action_none_reason=str(action_none_reason),
            blocked_by=str(core_blocked_reason),
            compatibility_mode=str(core_dec.get("compatibility_mode", "") or ""),
            entry_probe_plan_v1=entry_probe_plan_v1,
            default_side_gate_v1=entry_default_side_gate_v1,
        )
        if semantic_shadow_prediction_v1 is None and should_attempt_semantic_probe_bridge:
            try:
                _ensure_semantic_shadow_prediction(
                    runtime_snapshot_row=_current_runtime_snapshot_row(),
                    action_hint=str(action or shadow_observe_confirm.get("action", "") or ""),
                    setup_id_value=str(setup_id or ""),
                    setup_side_value=str(setup_side or ""),
                    entry_stage_value=str(entry_stage or ""),
                )
            except Exception:
                pass
        probe_candidate_raw = ((shadow_observe_confirm.get("metadata", {}) or {}).get("probe_candidate_v1", {}))
        probe_candidate_v1 = dict(probe_candidate_raw or {}) if isinstance(probe_candidate_raw, dict) else {}
        bridge_action, bridge_reason = _resolve_semantic_probe_bridge_action(
            symbol=str(symbol),
            core_reason=str(core_reason),
            observe_reason=str(observe_reason),
            action_none_reason=str(action_none_reason),
            blocked_by=str(core_blocked_reason),
            compatibility_mode=str(core_dec.get("compatibility_mode", "") or ""),
            entry_probe_plan_v1=entry_probe_plan_v1,
            default_side_gate_v1=entry_default_side_gate_v1,
            probe_candidate_v1=probe_candidate_v1,
            semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
        )
        semantic_probe_bridge_candidate_action = str(bridge_action or "")
        semantic_probe_bridge_candidate_reason = str(bridge_reason or "")
        if bridge_action in {"BUY", "SELL"}:
            action = str(bridge_action)
            core_pass = 1
            core_reason = str(bridge_reason or "semantic_probe_bridge")
            core_allowed_action = str(action)
            action_none_reason = ""
            core_blocked_reason = ""
        _record_entry_prefront_stage("semantic_probe_bridge", entry_prefront_stage_started_at)
        blocked_reason = str(core_blocked_reason or "")
    if not action:
        _set_entry_prefront_stage("wait_routing")
        routing_reason = str(blocked_reason or observe_reason or action_none_reason or "") or "core_not_passed"
        if routing_reason in {"WAIT", "NONE"}:
            routing_reason = "core_not_passed"
        if (
            str(observe_reason or "") == "edge_approach_observe"
            or str(action_none_reason or "") == "edge_approach_observe"
            or str(core_reason or "") == "core_edge_approach_observe"
        ):
            routing_reason = "edge_approach_observe"
        skip_outcome, skip_reason = _apply_wait_routing(
            routing_reason,
            blocked_by_value=str(blocked_reason or ""),
            observe_reason_value=str(observe_reason or ""),
            action_none_reason_value=str(action_none_reason or "core_not_passed"),
            raw_score_value=float(max(buy_s, sell_s)),
            effective_threshold_value=float(entry_threshold),
        )
        _record_entry_prefront_stage("wait_routing", entry_prefront_stage_started_at)
        _mark_skip(
            skip_reason,
            blocked_by_value=str(blocked_reason or ""),
            observe_reason_value=str(observe_reason or ""),
            buy_score=float(buy_s),
            sell_score=float(sell_s),
            entry_threshold=float(entry_threshold),
            action_none_reason=str(action_none_reason or "core_not_passed"),
            core_pass=int(core_pass),
            core_reason=str(core_reason),
            core_allowed_action=str(core_allowed_action),
            h1_bias_strength=float(h1_bias_strength),
            m1_trigger_strength=float(m1_trigger_strength),
            box_state=str(box_state),
            core_score=float(core_score),
            preflight_regime=str(preflight_regime),
            preflight_liquidity=str(preflight_liquidity),
            preflight_allowed_action=str(preflight_allowed_action),
            preflight_approach_mode=str(preflight_approach_mode),
            preflight_reason=str(preflight_reason),
        )
        _store_entry_prefront_profile(
            exit_state="observe_return",
            blocked_by_value=str(blocked_reason or ""),
            observe_reason_value=str(observe_reason or ""),
            action_none_reason_value=str(action_none_reason or "core_not_passed"),
        )
        self._append_entry_decision_log(
            _decision_payload(
                considered=1,
                outcome=str(skip_outcome),
                blocked_by=str(blocked_reason),
                raw_score=float(max(buy_s, sell_s)),
                contra_score=float(min(buy_s, sell_s)),
            )
        )
        return
    _store_entry_prefront_profile(
        exit_state="action_selected",
        blocked_by_value=str(core_blocked_reason or ""),
        observe_reason_value=str(observe_reason or ""),
        action_none_reason_value=str(action_none_reason or ""),
        action_value=str(action or ""),
    )
    entry_blocked_guard_v1 = _build_entry_blocked_guard_v1(
        action=str(action),
        observe_reason=str(observe_reason or ""),
        blocked_by=str(core_blocked_reason or ""),
        action_none_reason=str(action_none_reason or ""),
    )
    if bool(entry_blocked_guard_v1.get("guard_active")) and not bool(entry_blocked_guard_v1.get("allows_open")):
        fail_reason = str(entry_blocked_guard_v1.get("failure_code", "") or "entry_blocked_guard")
        if not bool(teacher_label_exploration_entry_v1.get("active")):
            entry_blocked_same_dir_count_v1 = sum(
                1
                for p in (my_positions or [])
                if (
                    int(getattr(p, "type", -1)) == int(ORDER_TYPE_BUY)
                    and str(action).upper() == "BUY"
                )
                or (
                    int(getattr(p, "type", -1)) == int(ORDER_TYPE_SELL)
                    and str(action).upper() == "SELL"
                )
            )
            teacher_label_exploration_entry_v1 = _build_teacher_label_exploration_entry_v1(
                symbol=str(symbol),
                action=str(action),
                observe_reason=str(observe_reason or ""),
                action_none_reason=str(action_none_reason or fail_reason),
                blocked_by=str(core_blocked_reason or fail_reason),
                probe_scene_id=str(
                    entry_probe_plan_v1.get("symbol_scene_relief", "")
                    or consumer_check_state_v1.get("probe_scene_id", "")
                    or ""
                ),
                consumer_check_state_v1=consumer_check_state_v1,
                guard_failure_code=str(fail_reason),
                score=float(max(buy_s, sell_s)),
                effective_threshold=float(entry_threshold),
                same_dir_count=int(entry_blocked_same_dir_count_v1),
            )
        if bool(teacher_label_exploration_entry_v1.get("active")):
            pass
        else:
            _mark_skip(
                fail_reason,
                blocked_by_value=str(core_blocked_reason or fail_reason),
                observe_reason_value=str(observe_reason or ""),
                action_none_reason_value=str(action_none_reason or fail_reason),
                action=str(action),
                entry_blocked_guard_v1=dict(entry_blocked_guard_v1),
            )
            skip_row = _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(core_blocked_reason or fail_reason),
                raw_score=float(max(buy_s, sell_s)),
                contra_score=float(min(buy_s, sell_s)),
                effective_threshold=float(entry_threshold),
                entry_stage=str(entry_stage),
            )
            skip_row["entry_blocked_guard_v1"] = dict(entry_blocked_guard_v1)
            self._append_entry_decision_log(skip_row)
            return
    score = float(buy_s) if str(action).upper() == "BUY" else float(sell_s)
    reasons = list((result or {}).get("buy" if str(action).upper() == "BUY" else "sell", {}).get("reasons", []) or [])

    base_lot = float(self.runtime.get_lot_size(symbol))
    lot = float(base_lot)
    contra_score = sell_s if action == "BUY" else buy_s
    final_entry_score = score
    entry_prob = None
    entry_adj = 0
    entry_blocked = False
    entry_indicators = self.runtime.entry_indicator_snapshot(symbol, scorer, df_all)
    if bool(getattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", True)):
        try:
            m15 = (df_all or {}).get("15M")
            lb = max(3, int(getattr(Config, "ENTRY_BB_CHANNEL_BREAK_LOOKBACK", 3)))
            if m15 is not None and not m15.empty and len(m15) >= lb + 1:
                sub = m15.tail(lb + 1).copy()
                up_s = pd.to_numeric(sub.get("bb_20_up"), errors="coerce").dropna()
                dn_s = pd.to_numeric(sub.get("bb_20_dn"), errors="coerce").dropna()
                mid_s = pd.to_numeric(sub.get("bb_20_mid"), errors="coerce").dropna()
                close_s = pd.to_numeric(sub.get("close"), errors="coerce").dropna()
                if len(up_s) >= lb and len(dn_s) >= lb and len(mid_s) >= lb and len(close_s) >= lb:
                    up_down = bool(all(float(up_s.iloc[-i]) < float(up_s.iloc[-i - 1]) for i in range(1, lb)))
                    dn_down = bool(all(float(dn_s.iloc[-i]) < float(dn_s.iloc[-i - 1]) for i in range(1, lb)))
                    up_up = bool(all(float(up_s.iloc[-i]) > float(up_s.iloc[-i - 1]) for i in range(1, lb)))
                    dn_up = bool(all(float(dn_s.iloc[-i]) > float(dn_s.iloc[-i - 1]) for i in range(1, lb)))
                    c_last = float(close_s.iloc[-1])
                    mid_last = float(mid_s.iloc[-1])
                    dn_last = float(dn_s.iloc[-1])
                    up_last = float(up_s.iloc[-1])
                    near_lower_tol = abs(float(getattr(Config, "ENTRY_BB_CHANNEL_BREAK_NEAR_LOWER_TOL", 0.00025)))
                    near_upper_tol = abs(float(getattr(Config, "ENTRY_BB_CHANNEL_BREAK_NEAR_UPPER_TOL", 0.00025)))
                    if str(action).upper() == "BUY":
                        cond = bool(up_down and dn_down and c_last <= mid_last and c_last <= (dn_last * (1.0 + near_lower_tol)))
                        if cond:
                            _mark_skip(
                                "bb_channel_breakdown_buy_blocked",
                                action=str(action),
                                close=float(c_last),
                                bb_20_dn=float(dn_last),
                                bb_20_mid=float(mid_last),
                            )
                            self._append_entry_decision_log(
                                _decision_payload(
                                    action=str(action),
                                    considered=1,
                                    outcome="skipped",
                                    blocked_by="bb_channel_breakdown_buy_blocked",
                                    raw_score=float(score),
                                    contra_score=float(contra_score),
                                )
                            )
                            return
                    elif str(action).upper() == "SELL":
                        cond = bool(up_up and dn_up and c_last >= mid_last and c_last >= (up_last * (1.0 - near_upper_tol)))
                        if cond:
                            _mark_skip(
                                "bb_channel_breakout_sell_blocked",
                                action=str(action),
                                close=float(c_last),
                                bb_20_up=float(up_last),
                                bb_20_mid=float(mid_last),
                            )
                            self._append_entry_decision_log(
                                _decision_payload(
                                    action=str(action),
                                    considered=1,
                                    outcome="skipped",
                                    blocked_by="bb_channel_breakout_sell_blocked",
                                    raw_score=float(score),
                                    contra_score=float(contra_score),
                                )
                            )
                            return
        except Exception:
            pass
    component_snapshot = self._component_extractor.extract(result=result, action=action)
    entry_h1_context_score = int(component_snapshot.entry_h1_context_score)
    entry_h1_context_opposite = int(component_snapshot.entry_h1_context_opposite)
    entry_m1_trigger_score = int(component_snapshot.entry_m1_trigger_score)
    entry_m1_trigger_opposite = int(component_snapshot.entry_m1_trigger_opposite)
    stage_started_at = time.perf_counter()
    observe_confirm_runtime_metadata = _build_runtime_observe_confirm_dual_write(
        shadow_observe_confirm=shadow_observe_confirm,
    )
    _record_entry_front_stage("observe_confirm_runtime_metadata", stage_started_at)
    stage_started_at = time.perf_counter()
    setup_context = DecisionContext(
        symbol=str(symbol),
        phase="entry",
        market_mode=str(preflight_regime or "UNKNOWN"),
        direction_policy=str(preflight_allowed_action or "UNKNOWN"),
        box_state=str(box_state or "UNKNOWN"),
        bb_state=str(bb_state or "UNKNOWN"),
        liquidity_state=str(preflight_liquidity or "UNKNOWN"),
        regime_name=str(self._regime_name(regime)),
        regime_zone=str(self._zone_from_regime(regime)),
        volatility_state=str(self._volatility_state_from_ratio(float((regime or {}).get("volatility_ratio", 1.0) or 1.0))),
        metadata={
            "preflight_approach_mode": str(preflight_approach_mode or "MIX"),
            "core_allowed_action": str(core_allowed_action or "UNKNOWN"),
            "observe_confirm_v1": observe_confirm_runtime_metadata.get("observe_confirm_v1", {}) or {},
            "observe_confirm_v2": observe_confirm_runtime_metadata.get("observe_confirm_v2", {}) or {},
            "prs_canonical_observe_confirm_field": str(
                observe_confirm_runtime_metadata.get("prs_canonical_observe_confirm_field", "") or "observe_confirm_v2"
            ),
            "prs_compatibility_observe_confirm_field": str(
                observe_confirm_runtime_metadata.get("prs_compatibility_observe_confirm_field", "") or "observe_confirm_v1"
            ),
            "prs_log_contract_v2": observe_confirm_runtime_metadata.get("prs_log_contract_v2", {}) or {},
        },
    )
    _record_entry_front_stage("setup_context_build", stage_started_at)
    stage_started_at = time.perf_counter()
    setup_candidate = self._setup_detector.detect_entry_setup(
        context=setup_context,
        action=str(action),
        h1_gap=float(entry_h1_context_score - entry_h1_context_opposite),
        m1_gap=float(entry_m1_trigger_score - entry_m1_trigger_opposite),
        score_gap=float(score - contra_score),
    )
    _record_entry_front_stage("detect_entry_setup", stage_started_at)
    try:
        self._store_runtime_snapshot(
            runtime=self.runtime,
            symbol=str(symbol),
            key="entry_helper_front_profile_v1",
            payload={
                "contract_version": "entry_helper_front_profile_v1",
                "total_ms": round((time.perf_counter() - entry_front_started_at) * 1000.0, 3),
                "stage_timings_ms": dict(entry_front_stage_timings_ms),
                "observe_state": str(shadow_observe_confirm.get("state", "") or ""),
                "observe_action": str(shadow_observe_confirm.get("action", "") or ""),
                "observe_reason": str(shadow_observe_confirm.get("reason", "") or ""),
                "context_metadata_keys": int(len(shadow_context_metadata_v1)),
                "setup_id": str(getattr(setup_candidate, "setup_id", "") or ""),
                "setup_status": str(getattr(setup_candidate, "status", "") or ""),
                "setup_trigger_state": str(getattr(setup_candidate, "trigger_state", "") or ""),
                "build_entry_context_profile": dict(
                    shadow_context_metadata_v1.get("build_entry_context_profile_v1", {}) or {}
                ),
                "engine_context_snapshot_profile": dict(
                    shadow_context_metadata_v1.get("engine_context_snapshot_profile_v1", {}) or {}
                ),
            },
        )
    except Exception:
        pass
    setup_id = str(setup_candidate.setup_id or "")
    setup_side = str(setup_candidate.side or str(action or ""))
    setup_status = str(setup_candidate.status or "pending")
    setup_trigger_state = str(setup_candidate.trigger_state or "UNKNOWN")
    setup_score = float(setup_candidate.score or 0.0)
    setup_entry_quality = float(setup_candidate.entry_quality or 0.0)
    setup_reason = str((setup_candidate.metadata or {}).get("reason", "") or "")
    entry_back_started_at = time.perf_counter()
    entry_back_stage_started_at = entry_back_started_at
    entry_back_stage_timings_ms: dict[str, float] = {}
    entry_back_profile_state = {
        "current_stage": "setup_post_filter",
        "last_completed_stage": "",
        "exit_state": "in_progress",
    }

    def _record_entry_back_stage(stage_name: str, started_at: float) -> None:
        entry_back_stage_timings_ms[str(stage_name)] = round(
            (time.perf_counter() - float(started_at)) * 1000.0,
            3,
        )
        entry_back_profile_state["last_completed_stage"] = str(stage_name)

    def _set_entry_back_stage(stage_name: str) -> None:
        nonlocal entry_back_stage_started_at
        entry_back_profile_state["current_stage"] = str(stage_name)
        entry_back_stage_started_at = time.perf_counter()

    def _store_entry_back_profile(exit_state: str | None = None) -> None:
        if exit_state is not None:
            entry_back_profile_state["exit_state"] = str(exit_state)
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_helper_back_profile_v1",
                payload={
                    "contract_version": "entry_helper_back_profile_v1",
                    "total_ms": round((time.perf_counter() - entry_back_started_at) * 1000.0, 3),
                    "stage_timings_ms": dict(entry_back_stage_timings_ms),
                    "current_stage": str(entry_back_profile_state.get("current_stage", "") or ""),
                    "last_completed_stage": str(entry_back_profile_state.get("last_completed_stage", "") or ""),
                    "exit_state": str(entry_back_profile_state.get("exit_state", "") or ""),
                    "action": str(action or ""),
                    "setup_id": str(setup_id or ""),
                    "setup_status": str(setup_status or ""),
                    "setup_reason": str(setup_reason or ""),
                },
            )
        except Exception:
            pass

    _store_entry_back_profile()
    _refresh_prediction_bundle(float(score), float(contra_score), float(entry_threshold))
    if setup_status != "matched" or not setup_id:
        observe_reason = "setup_rejected"
        if str(setup_status).lower() == "pending":
            setup_reason_l = str(setup_reason or "").lower()
            if "conflict" in setup_reason_l:
                observe_reason = "conflict_observe_wait"
            elif "edge_approach" in setup_reason_l or "observe" in setup_reason_l:
                observe_reason = "edge_approach_observe"
            else:
                observe_reason = "core_not_passed"
        skip_outcome, skip_reason = _apply_wait_routing(
            observe_reason,
            action_value=str(action),
            raw_score_value=float(score),
            effective_threshold_value=float(entry_threshold),
        )
        _mark_skip(
            skip_reason,
            action=str(action),
            setup_id=str(setup_id),
            setup_side=str(setup_side),
            setup_status=str(setup_status),
            setup_trigger_state=str(setup_trigger_state),
            setup_score=float(setup_score),
            setup_entry_quality=float(setup_entry_quality),
            setup_reason=str(setup_reason),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome=str(skip_outcome),
                blocked_by=str(skip_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    if str(setup_id).lower() == "range_lower_reversal_buy":
        bb_state_u = str(bb_state or "").upper()
        runtime_snapshot_row = _current_entry_runtime_signal_row(refresh_current_cycle=True)
        setup_reason_u = str(setup_reason or "").lower().strip()
        compatibility_mode_u = str(runtime_snapshot_row.get("compatibility_mode", "") or "")
        range_lower_soft_edge_allow, range_lower_soft_edge_reason = _resolve_range_lower_buy_shadow_relief(
            symbol=str(symbol),
            core_reason=str(core_reason),
            setup_reason=str(setup_reason),
            box_state=str(box_state),
            bb_state=str(bb_state),
            wait_conflict=float(wait_conflict),
            wait_noise=float(wait_noise),
            wait_score=float(wait_score),
            preflight_allowed_action=str(preflight_allowed_action),
            compatibility_mode=compatibility_mode_u,
            semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
            entry_probe_plan_v1=entry_probe_plan_v1,
            runtime_signal_row=runtime_snapshot_row,
        )
        if bb_state_u != "LOWER_EDGE" and not range_lower_soft_edge_allow:
            _mark_skip(
                "range_lower_buy_requires_lower_edge",
                action=str(action),
                setup_id=str(setup_id),
                setup_status=str(setup_status),
                setup_reason=str(setup_reason),
                bb_state=str(bb_state),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="range_lower_buy_requires_lower_edge",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                )
            )
            return
        if range_lower_soft_edge_allow:
            setup_reason = f"{setup_reason_u}_{range_lower_soft_edge_reason}"
        if float(wait_conflict) > 0.0 and not range_lower_soft_edge_allow:
            _mark_skip(
                "range_lower_buy_conflict_blocked",
                action=str(action),
                setup_id=str(setup_id),
                setup_status=str(setup_status),
                setup_reason=str(setup_reason),
                wait_conflict=float(wait_conflict),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="range_lower_buy_conflict_blocked",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                )
            )
            return
    edge_guard_enabled = bool(getattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False))
    if edge_guard_enabled:
        h1_gap_now = float(entry_h1_context_score - entry_h1_context_opposite)
        m1_gap_now = float(entry_m1_trigger_score - entry_m1_trigger_opposite)
        score_gap_now = float(score) - float(contra_score)
        ov_h1 = float(getattr(Config, "ENTRY_EDGE_DIRECTION_OVERRIDE_H1_GAP", 28.0))
        ov_m1 = float(getattr(Config, "ENTRY_EDGE_DIRECTION_OVERRIDE_M1_GAP", 16.0))
        ov_score = float(getattr(Config, "ENTRY_EDGE_DIRECTION_OVERRIDE_SCORE_GAP", 120.0))
        buy_upper = str(action).upper() == "BUY" and str(box_state).upper() in {"UPPER", "ABOVE"}
        sell_lower = str(action).upper() == "SELL" and str(box_state).upper() in {"LOWER", "BELOW"}
        buy_breakout_override = bool(
            preflight_allowed_action == "BUY_ONLY"
            and h1_gap_now >= ov_h1
            and m1_gap_now >= ov_m1
            and score_gap_now >= ov_score
        )
        sell_breakout_override = bool(
            preflight_allowed_action == "SELL_ONLY"
            and (-h1_gap_now) >= ov_h1
            and (-m1_gap_now) >= ov_m1
            and (-score_gap_now) >= ov_score
        )
        if buy_upper and (not buy_breakout_override):
            _mark_skip(
                "edge_direction_upper_buy_blocked",
                action=str(action),
                box_state=str(box_state),
                preflight_allowed_action=str(preflight_allowed_action),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="edge_direction_upper_buy_blocked",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                )
            )
            return
        if sell_lower and (not sell_breakout_override):
            _mark_skip(
                "edge_direction_lower_sell_blocked",
                action=str(action),
                box_state=str(box_state),
                preflight_allowed_action=str(preflight_allowed_action),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="edge_direction_lower_sell_blocked",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                )
            )
            return
    _record_entry_back_stage("setup_post_filter", entry_back_stage_started_at)
    _set_entry_back_stage("policy_sync_and_hard_gates")
    _store_entry_back_profile()
    if str(action or "").upper() in {"BUY", "SELL"} and str(setup_id or "").strip():
        current_cycle_runtime_context_row_v1 = _current_entry_runtime_signal_row(
            refresh_current_cycle=True
        )
        active_action_conflict_runtime_context_v1 = (
            _build_active_action_conflict_runtime_context_v1(
                runtime_snapshot_row=current_cycle_runtime_context_row_v1,
                symbol=str(symbol),
                action=str(action or ""),
                setup_id=str(setup_id or ""),
                setup_reason=str(setup_reason or ""),
                setup_side=str(setup_side or action or ""),
                entry_session_name=str(entry_session_name or ""),
                wait_state=wait_state,
                entry_wait_decision=str(entry_wait_decision or ""),
                score=float(score),
                contra_score=float(contra_score),
                prediction_bundle=prediction_bundle,
                shadow_transition_forecast_v1=shadow_transition_forecast_v1,
                shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
                shadow_observe_confirm=shadow_observe_confirm,
                entry_stage=str(entry_stage or ""),
                actual_effective_entry_threshold=float(entry_threshold),
                actual_size_multiplier=1.0,
                state25_candidate_runtime_state=getattr(
                    self.runtime, "state25_candidate_runtime_state", {}
                ),
            )
        )
        forecast_state25_log_only_overlay_trace_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "forecast_state25_log_only_overlay_trace_v1", {}
            )
            or {}
        )
        belief_action_hint_v1 = dict(
            active_action_conflict_runtime_context_v1.get("belief_action_hint_v1", {})
            or {}
        )
        barrier_action_hint_v1 = dict(
            active_action_conflict_runtime_context_v1.get("barrier_action_hint_v1", {})
            or {}
        )
        countertrend_continuation_signal_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "countertrend_continuation_signal_v1", {}
            )
            or {}
        )
        active_action_conflict_guard_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "active_action_conflict_guard_v1", {}
            )
            or {}
        )
        directional_continuation_promotion_v1 = _build_directional_continuation_promotion_v1(
            symbol=str(symbol),
            baseline_action=str(
                active_action_conflict_guard_v1.get("baseline_action", "")
                or baseline_action_side_v1
                or ""
            ),
            runtime_signal_row=current_cycle_runtime_context_row_v1,
            active_action_conflict_guard_v1=active_action_conflict_guard_v1,
        )
        promotion_active_v1 = bool(directional_continuation_promotion_v1.get("active", False))
        if bool(active_action_conflict_guard_v1.get("guard_applied", False)) and not promotion_active_v1:
            baseline_action_value = str(
                active_action_conflict_guard_v1.get("baseline_action", "") or action or ""
            )
            action = None
            observe_reason = str(
                active_action_conflict_guard_v1.get("downgraded_observe_reason", "")
                or observe_reason
                or "directional_conflict_watch"
            )
            action_none_reason = str(
                active_action_conflict_guard_v1.get("failure_label", "")
                or action_none_reason
                or "wrong_side_conflict_pressure"
            )
            blocked_reason = str(
                active_action_conflict_guard_v1.get("failure_code", "")
                or "active_action_conflict_guard"
            )
            core_blocked_reason = str(blocked_reason)
            skip_outcome, skip_reason = _apply_wait_routing(
                blocked_reason,
                blocked_by_value=str(blocked_reason),
                observe_reason_value=str(observe_reason),
                action_none_reason_value=str(action_none_reason),
                action_value=str(baseline_action_value),
                raw_score_value=float(score),
                effective_threshold_value=float(entry_threshold),
            )
            _record_entry_back_stage("policy_sync_and_hard_gates", entry_back_stage_started_at)
            _mark_skip(
                skip_reason,
                action=str(baseline_action_value),
                setup_id=str(setup_id),
                setup_side=str(setup_side),
                setup_status=str(setup_status),
                setup_trigger_state=str(setup_trigger_state),
                setup_score=float(setup_score),
                setup_entry_quality=float(setup_entry_quality),
                setup_reason=str(setup_reason),
            )
            _store_entry_back_profile(exit_state="active_action_conflict_guard")
            self._append_entry_decision_log(
                _decision_payload(
                    action="",
                    considered=1,
                    outcome=str(skip_outcome),
                    blocked_by=str(skip_reason),
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(entry_threshold),
                )
            )
            return
        if promotion_active_v1:
            promoted_action_v1 = str(directional_continuation_promotion_v1.get("promoted_action", "") or "")
            if promoted_action_v1 in {"BUY", "SELL"}:
                action = str(promoted_action_v1)
                core_pass = max(1, int(core_pass))
                core_reason = str(
                    directional_continuation_promotion_v1.get("promotion_reason", "")
                    or "directional_continuation_overlay_promotion"
                )
                core_allowed_action = str(action)
                action_none_reason = ""
                blocked_reason = ""
                core_blocked_reason = ""
                entry_stage = str(
                    directional_continuation_promotion_v1.get("recommended_entry_stage", entry_stage)
                    or entry_stage
                )
    session_dec = self._session_policy.get_threshold_mult(symbol=symbol)
    atr_dec = self._atr_policy.get_threshold_mult(df_all=df_all)
    entry_session_name = str(session_dec.session_name)
    entry_weekday = int(session_dec.weekday)
    entry_session_threshold_mult = float(session_dec.threshold_mult)
    entry_atr_ratio = float(atr_dec.atr_ratio)
    entry_atr_threshold_mult = float(atr_dec.threshold_mult)
    topdown_dec = self._topdown_gate_policy.evaluate(result=result, action=action)
    topdown_ok = bool(topdown_dec.ok)
    topdown_reason = str(topdown_dec.reason)
    topdown_stat = {"align": int(topdown_dec.align), "conflict": int(topdown_dec.conflict), "seen": int(topdown_dec.seen)}
    h1_dec = self._h1_gate_policy.evaluate(
        action=action,
        h1_context_score=entry_h1_context_score,
        h1_context_opposite=entry_h1_context_opposite,
    )
    gate_ok = bool(h1_dec.ok)
    gate_reason = str(h1_dec.reason)
    flow_execution_veto_owner_runtime_v1 = _build_flow_execution_veto_owner_v1(
        symbol=str(symbol),
        baseline_action=str(action or ""),
        setup_id=str(setup_id),
        setup_reason=str(setup_reason),
        runtime_signal_row=_current_entry_runtime_signal_row(refresh_current_cycle=True),
    )
    if bool(flow_execution_veto_owner_runtime_v1.get("veto_applied", False)):
        flow_execution_veto_owner_v1 = dict(flow_execution_veto_owner_runtime_v1 or {})
        _mark_skip(
            "flow_execution_veto_owner_blocked",
            action=str(action),
            setup_id=str(setup_id),
            flow_execution_veto_applied=True,
            flow_execution_veto_kind=str(
                flow_execution_veto_owner_runtime_v1.get("veto_kind", "") or ""
            ),
            flow_execution_veto_reason_summary=str(
                flow_execution_veto_owner_runtime_v1.get("reason_summary", "") or ""
            ),
            flow_execution_veto_bearish_evidence_count=int(
                flow_execution_veto_owner_runtime_v1.get("bearish_evidence_count", 0) or 0
            ),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by="flow_execution_veto_owner_blocked",
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    if _should_block_range_lower_buy_dual_bear_context(
        symbol=str(symbol),
        action=str(action),
        setup_id=str(setup_id),
        h1_gate_pass=gate_ok,
        topdown_gate_pass=topdown_ok,
    ):
        _mark_skip(
            "range_lower_buy_dual_bear_context_blocked",
            action=str(action),
            setup_id=str(setup_id),
            entry_h1_gate_pass=False,
            entry_h1_gate_reason=str(gate_reason),
            entry_topdown_gate_pass=False,
            entry_topdown_gate_reason=str(topdown_reason),
            entry_topdown_align_count=int(topdown_stat.get("align", 0)),
            entry_topdown_conflict_count=int(topdown_stat.get("conflict", 0)),
            entry_topdown_seen_count=int(topdown_stat.get("seen", 0)),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by="range_lower_buy_dual_bear_context_blocked",
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    try:
        row = self.runtime.latest_signal_by_symbol.get(symbol, {}) if isinstance(self.runtime.latest_signal_by_symbol, dict) else {}
        if not isinstance(row, dict):
            row = {}
        row["entry_h1_context_score"] = int(entry_h1_context_score)
        row["entry_h1_context_opposite"] = int(entry_h1_context_opposite)
        row["entry_m1_trigger_score"] = int(entry_m1_trigger_score)
        row["entry_m1_trigger_opposite"] = int(entry_m1_trigger_opposite)
        row["core_pass"] = int(core_pass)
        row["core_reason"] = str(core_reason)
        row["core_allowed_action"] = str(core_allowed_action)
        row["h1_bias_strength"] = float(h1_bias_strength)
        row["m1_trigger_strength"] = float(m1_trigger_strength)
        row["box_state"] = str(box_state)
        row["bb_state"] = str(bb_state)
        row["core_score"] = float(core_score)
        row["core_buy_raw"] = float(core_buy_raw)
        row["core_sell_raw"] = float(core_sell_raw)
        row["core_best_raw"] = float(core_best_raw)
        row["core_min_raw"] = float(core_min_raw)
        row["core_margin_raw"] = float(core_margin_raw)
        row["core_tie_band_raw"] = float(core_tie_band_raw)
        row["setup_id"] = str(setup_id)
        row["setup_side"] = str(setup_side)
        row["setup_status"] = str(setup_status)
        row["setup_trigger_state"] = str(setup_trigger_state)
        row["setup_score"] = float(setup_score)
        row["setup_entry_quality"] = float(setup_entry_quality)
        row["setup_reason"] = str(setup_reason)
        row["management_profile_id"] = str(management_profile_id)
        row["invalidation_id"] = str(invalidation_id)
        row["wait_score"] = float(wait_score)
        row["wait_conflict"] = float(wait_conflict)
        row["wait_noise"] = float(wait_noise)
        row["wait_penalty"] = float(wait_penalty)
        row["learn_buy_penalty"] = float(learn_buy_penalty)
        row["learn_sell_penalty"] = float(learn_sell_penalty)
        row["preflight_regime"] = str(preflight_regime)
        row["preflight_liquidity"] = str(preflight_liquidity)
        row["preflight_allowed_action"] = str(preflight_allowed_action)
        row["preflight_approach_mode"] = str(preflight_approach_mode)
        row["preflight_reason"] = str(preflight_reason)
        row["preflight_direction_penalty_applied"] = float(preflight_direction_penalty_applied)
        row["consumer_check_candidate"] = bool(consumer_check_candidate)
        row["consumer_check_display_ready"] = bool(consumer_check_display_ready)
        row["consumer_check_entry_ready"] = bool(consumer_check_entry_ready)
        row["consumer_check_side"] = str(consumer_check_side)
        row["consumer_check_stage"] = str(consumer_check_stage)
        row["consumer_check_reason"] = str(consumer_check_reason)
        row["consumer_check_display_strength_level"] = int(consumer_check_display_strength_level)
        row["consumer_check_display_score"] = float(consumer_check_display_score)
        row["consumer_check_display_repeat_count"] = int(consumer_check_display_repeat_count)
        row["consumer_check_state_v1"] = dict(consumer_check_state_v1 or {})
        row["entry_h1_gate_pass"] = bool(gate_ok)
        row["entry_h1_gate_reason"] = str(gate_reason)
        row["entry_topdown_gate_pass"] = bool(topdown_ok)
        row["entry_topdown_gate_reason"] = str(topdown_reason)
        row["entry_topdown_align_count"] = int(topdown_stat.get("align", 0))
        row["entry_topdown_conflict_count"] = int(topdown_stat.get("conflict", 0))
        row["entry_topdown_seen_count"] = int(topdown_stat.get("seen", 0))
        row["entry_session_name"] = str(entry_session_name)
        row["entry_weekday"] = int(entry_weekday)
        row["entry_session_threshold_mult"] = float(entry_session_threshold_mult)
        row["entry_atr_ratio"] = float(entry_atr_ratio)
        row["entry_atr_threshold_mult"] = float(entry_atr_threshold_mult)
        if isinstance(self.runtime.latest_signal_by_symbol, dict):
            self.runtime.latest_signal_by_symbol[symbol] = row
    except Exception:
        pass
    topdown_mode = str(getattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft") or "soft").strip().lower()
    h1_mode = str(getattr(Config, "ENTRY_H1_GATE_MODE", "soft") or "soft").strip().lower()
    if not topdown_ok and topdown_mode == "hard":
        _mark_skip(
            "topdown_timeframe_gate_blocked",
            action=str(action),
            entry_topdown_gate_pass=False,
            entry_topdown_gate_reason=str(topdown_reason),
            entry_topdown_align_count=int(topdown_stat.get("align", 0)),
            entry_topdown_conflict_count=int(topdown_stat.get("conflict", 0)),
            entry_topdown_seen_count=int(topdown_stat.get("seen", 0)),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by="topdown_timeframe_gate_blocked",
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    if not gate_ok and h1_mode == "hard":
        _mark_skip(
            "h1_entry_gate_blocked",
            action=str(action),
            entry_h1_context_score=int(entry_h1_context_score),
            entry_h1_context_opposite=int(entry_h1_context_opposite),
            entry_m1_trigger_score=int(entry_m1_trigger_score),
            entry_m1_trigger_opposite=int(entry_m1_trigger_opposite),
            entry_h1_gate_pass=False,
            entry_h1_gate_reason=str(gate_reason),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by="h1_entry_gate_blocked",
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    hard_block_reason = self._check_hard_no_trade_guard(symbol=symbol, regime=regime)
    if hard_block_reason:
        _mark_skip(hard_block_reason, action=str(action))
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(hard_block_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
            )
        )
        return
    _record_entry_back_stage("policy_sync_and_hard_gates", entry_back_stage_started_at)
    _set_entry_back_stage("ai_threshold_and_utility")
    _store_entry_back_profile()

    if self.runtime.ai_runtime:
        ai_used = 1
        entry_features = self.runtime.entry_features(
            symbol,
            action,
            score,
            contra_score,
            reasons,
            regime=regime,
            indicators=entry_indicators,
            metadata={
                "entry_stage": str(entry_stage),
                "entry_setup_id": str(setup_id),
                "management_profile_id": str(management_profile_id),
                "invalidation_id": str(invalidation_id),
                "regime_at_entry": str(regime.get("name", "") or ""),
                "entry_h1_context_score": int(entry_h1_context_score),
                "entry_m1_trigger_score": int(entry_m1_trigger_score),
                "entry_h1_gate_pass": 1 if gate_ok else 0,
                "entry_h1_gate_reason": str(gate_reason),
                "entry_topdown_gate_pass": 1 if topdown_ok else 0,
                "entry_topdown_gate_reason": str(topdown_reason),
                "entry_topdown_align_count": int(topdown_stat.get("align", 0)),
                "entry_topdown_conflict_count": int(topdown_stat.get("conflict", 0)),
                "entry_topdown_seen_count": int(topdown_stat.get("seen", 0)),
                "entry_session_name": str(entry_session_name),
                "entry_weekday": int(entry_weekday),
                "entry_session_threshold_mult": float(entry_session_threshold_mult),
                "entry_atr_ratio": float(entry_atr_ratio),
                "entry_atr_threshold_mult": float(entry_atr_threshold_mult),
            },
        )
        try:
            entry_decision = self.runtime.ai_runtime.predict_entry(
                entry_features, threshold=Config.AI_ENTRY_THRESHOLD
            )
            entry_prob = float(entry_decision.probability)
            entry_adj = self.runtime.score_adjustment(entry_decision.probability, Config.AI_ENTRY_WEIGHT)
            final_entry_score = max(0, score + entry_adj)
            if (
                Config.AI_USE_ENTRY_FILTER
                and (not entry_decision.decision)
                and float(entry_decision.probability) < float(Config.AI_ENTRY_BLOCK_PROB)
            ):
                _mark_skip(
                    "ai_entry_filter_blocked",
                    ai_probability=float(entry_decision.probability),
                    ai_block_prob=float(Config.AI_ENTRY_BLOCK_PROB),
                )
                entry_blocked = True
                self.decision_recorder.record_trace(
                    {
                        "symbol": symbol,
                        "action": action,
                        "raw_score": score,
                        "contra_score": contra_score,
                        "probability": entry_prob,
                        "score_adj": entry_adj,
                        "final_score": final_entry_score,
                        "threshold": Config.AI_ENTRY_THRESHOLD,
                        "blocked": True,
                        "regime": regime.get("name", ""),
                        "volume_ratio": regime.get("volume_ratio"),
                        "volatility_ratio": regime.get("volatility_ratio"),
                        "spread_ratio": regime.get("spread_ratio"),
                        "buy_multiplier": regime.get("buy_multiplier"),
                        "sell_multiplier": regime.get("sell_multiplier"),
                        "entry_h1_context_score": int(entry_h1_context_score),
                        "entry_h1_context_opposite": int(entry_h1_context_opposite),
                        "entry_m1_trigger_score": int(entry_m1_trigger_score),
                        "entry_m1_trigger_opposite": int(entry_m1_trigger_opposite),
                        "entry_h1_gate_pass": bool(gate_ok),
                        "entry_h1_gate_reason": str(gate_reason),
                        "entry_topdown_gate_pass": bool(topdown_ok),
                        "entry_topdown_gate_reason": str(topdown_reason),
                        "entry_topdown_align_count": int(topdown_stat.get("align", 0)),
                        "entry_topdown_conflict_count": int(topdown_stat.get("conflict", 0)),
                        "entry_topdown_seen_count": int(topdown_stat.get("seen", 0)),
                        "preflight_regime": str(preflight_regime),
                        "preflight_liquidity": str(preflight_liquidity),
                        "preflight_allowed_action": str(preflight_allowed_action),
                        "preflight_approach_mode": str(preflight_approach_mode),
                        "preflight_reason": str(preflight_reason),
                        "blocked_by": "ai_entry_filter_blocked",
                        "effective_entry_threshold": float(entry_threshold),
                        "base_entry_threshold": float(entry_threshold),
                        **_build_execution_action_diff_flat_fields_v1(
                            _build_execution_action_diff_v1(
                                original_action_side=str(original_action_side_v1 or ""),
                                current_action_side=str(action or ""),
                                blocked_by="ai_entry_filter_blocked",
                                observe_reason=str(observe_reason or ""),
                                action_none_reason=str(action_none_reason or ""),
                                active_action_conflict_guard_v1=dict(
                                    active_action_conflict_guard_v1 or {}
                                ),
                                directional_continuation_promotion_v1=dict(
                                    directional_continuation_promotion_v1 or {}
                                ),
                            )
                        ),
                    }
                )
                self._append_entry_decision_log(
                    _decision_payload(
                        action=str(action),
                        considered=1,
                        outcome="skipped",
                        blocked_by="ai_entry_filter_blocked",
                        raw_score=float(score),
                        contra_score=float(contra_score),
                        effective_threshold=float(entry_threshold),
                        ai_probability=float(entry_prob) if entry_prob is not None else None,
                    )
                )
                print(f"[AI] entry blocked {symbol} {action} p={entry_decision.probability:.3f}")
                return
        except Exception:
            ai_used = 0
            ai_missing_reason = "predict_failed"
    else:
        ai_missing_reason = "ai_runtime_none"

    if bool(getattr(Config, "ENABLE_ADAPTIVE_ENTRY_ROUTING", True)):
        entry_stage, entry_stage_detail = self._choose_entry_stage(
            score=final_entry_score,
            contra_score=contra_score,
            regime=regime,
            entry_prob=entry_prob,
        )
    stage_mult = {
        "aggressive": float(getattr(Config, "ENTRY_STAGE_AGGRESSIVE_MULT", 0.88)),
        "balanced": float(getattr(Config, "ENTRY_STAGE_BALANCED_MULT", 1.00)),
        "conservative": float(getattr(Config, "ENTRY_STAGE_CONSERVATIVE_MULT", 1.15)),
    }.get(entry_stage, 1.0)
    stage_min_prob = {
        "aggressive": float(getattr(Config, "ENTRY_STAGE_MIN_PROB_AGGRESSIVE", 0.45)),
        "balanced": float(getattr(Config, "ENTRY_STAGE_MIN_PROB_BALANCED", 0.50)),
        "conservative": float(getattr(Config, "ENTRY_STAGE_MIN_PROB_CONSERVATIVE", 0.56)),
    }.get(entry_stage, 0.50)
    stage_mult_min = float(getattr(Config, "ENTRY_DYNAMIC_STAGE_MULT_MIN", 0.45))
    stage_mult_max = float(getattr(Config, "ENTRY_DYNAMIC_STAGE_MULT_MAX", 1.40))
    if stage_mult_min > stage_mult_max:
        stage_mult_min, stage_mult_max = stage_mult_max, stage_mult_min
    dynamic_threshold = int(round(float(entry_threshold) * max(stage_mult_min, min(stage_mult_max, stage_mult))))
    dynamic_threshold = int(
        round(
            float(dynamic_threshold)
            * max(float(getattr(Config, "ENTRY_DYNAMIC_SESSION_MULT_MIN", 0.55)), min(float(getattr(Config, "ENTRY_DYNAMIC_SESSION_MULT_MAX", 1.40)), float(entry_session_threshold_mult)))
            * max(float(getattr(Config, "ENTRY_DYNAMIC_ATR_MULT_MIN", 0.55)), min(float(getattr(Config, "ENTRY_DYNAMIC_ATR_MULT_MAX", 1.40)), float(entry_atr_threshold_mult)))
        )
    )
    context_adj, context_adj_detail = self._compute_context_threshold_adjustment(
        regime=regime,
        topdown_stat=topdown_stat,
        entry_h1_context_score=int(entry_h1_context_score),
        entry_h1_context_opposite=int(entry_h1_context_opposite),
    )
    dynamic_threshold = int(round(float(dynamic_threshold) + float(context_adj)))
    same_dir_positions = [
        p
        for p in (my_positions or [])
        if (int(p.type) == int(ORDER_TYPE_BUY) and action == "BUY")
        or (int(p.type) == int(ORDER_TYPE_SELL) and action == "SELL")
    ]
    if same_dir_positions:
        add_step = max(0, int(getattr(Config, "ENTRY_PYRAMID_SCORE_STEP", 20)))
        dynamic_threshold += int(add_step * len(same_dir_positions))
    dynamic_threshold = max(1, int(dynamic_threshold))
    threshold_relief_pts = int(max(0, _threshold_relief_points()))
    if threshold_relief_pts > 0:
        dynamic_threshold = max(1, int(dynamic_threshold) - int(threshold_relief_pts))
    state25_candidate_threshold_live_v1 = (
        resolve_state25_candidate_live_threshold_adjustment_v1(
            getattr(self.runtime, "state25_candidate_runtime_state", {}),
            symbol=str(symbol),
            entry_stage=str(entry_stage),
            baseline_entry_threshold=float(dynamic_threshold),
        )
    )
    if bool(state25_candidate_threshold_live_v1.get("enabled")):
        dynamic_threshold = max(
            1,
            int(
                round(
                    float(
                        state25_candidate_threshold_live_v1.get(
                            "candidate_effective_entry_threshold",
                            dynamic_threshold,
                        )
                        or dynamic_threshold
                    )
                )
            ),
        )
    if semantic_live_guard_v1 is None:
        semantic_live_guard = getattr(self.runtime, "semantic_promotion_guard", None)
        if semantic_live_guard is None:
            semantic_live_guard = SemanticPromotionGuard()
        try:
            semantic_live_guard_v1 = semantic_live_guard.evaluate_entry_rollout(
                symbol=str(symbol),
                baseline_action=str(action),
                entry_stage=str(entry_stage),
                current_threshold=int(dynamic_threshold),
                semantic_prediction=semantic_shadow_prediction_v1,
                runtime_snapshot_row=_current_runtime_snapshot_row(),
            )
            try:
                self._store_runtime_snapshot(
                    runtime=self.runtime,
                    symbol=str(symbol),
                    key="semantic_live_guard_v1",
                    payload=dict(semantic_live_guard_v1 or {}),
                )
            except Exception:
                pass
            record_rollout = getattr(self.runtime, "record_semantic_rollout_event", None)
            if callable(record_rollout):
                try:
                    record_rollout(domain="entry", event=dict(semantic_live_guard_v1 or {}))
                except Exception:
                    pass
            if bool((semantic_live_guard_v1 or {}).get("alert_active")):
                obs_event = getattr(self.runtime, "_obs_event", None)
                if callable(obs_event):
                    try:
                        obs_event(
                            "semantic_live_rollout_alert",
                            level="warning",
                            payload={
                                "symbol": str(symbol),
                                "mode": str((semantic_live_guard_v1 or {}).get("mode", "") or ""),
                                "fallback_reason": str(
                                    (semantic_live_guard_v1 or {}).get("fallback_reason", "") or ""
                                ),
                                "reason": str((semantic_live_guard_v1 or {}).get("reason", "") or ""),
                            },
                        )
                    except Exception:
                        pass
        except Exception:
            semantic_live_guard_v1 = {
                "mode": str(getattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "disabled") or "disabled"),
                "fallback_reason": "promotion_guard_failed",
                "fallback_applied": True,
                "threshold_before": int(dynamic_threshold),
                "threshold_after": int(dynamic_threshold),
                "threshold_adjustment_points": 0,
                "threshold_applied": False,
                "partial_live_weight": 0.0,
                "partial_live_applied": False,
                "alert_active": False,
                "reason": "promotion_guard_failed",
                "symbol_allowed": False,
                "entry_stage_allowed": False,
            }
    semantic_runtime_diagnostics = getattr(self.runtime, "semantic_shadow_runtime_diagnostics", None)
    semantic_shadow_activation_state, semantic_shadow_activation_reason = _resolve_semantic_shadow_activation(
        semantic_shadow_prediction_v1=semantic_shadow_prediction_v1,
        semantic_live_guard_v1=semantic_live_guard_v1,
        runtime_diagnostics=semantic_runtime_diagnostics if isinstance(semantic_runtime_diagnostics, dict) else None,
    )
    semantic_live_threshold_state, semantic_live_threshold_reason = _resolve_semantic_live_threshold_trace(
        semantic_live_guard_v1=semantic_live_guard_v1,
    )
    if bool((semantic_live_guard_v1 or {}).get("threshold_applied")):
        dynamic_threshold = max(
            1,
            int((semantic_live_guard_v1 or {}).get("threshold_after", dynamic_threshold) or dynamic_threshold),
        )
    try:
        row = self.runtime.latest_signal_by_symbol.get(symbol, {}) if isinstance(self.runtime.latest_signal_by_symbol, dict) else {}
        if not isinstance(row, dict):
            row = {}
        row["entry_considered"] = 1
        row["base_entry_threshold"] = float(entry_threshold)
        row["effective_entry_threshold"] = int(dynamic_threshold)
        row["entry_threshold_relief_pts"] = int(threshold_relief_pts)
        row["entry_context_threshold_adjustment"] = int(context_adj)
        row["entry_context_adjustment_detail"] = dict(context_adj_detail)
        row["state25_candidate_threshold_bounded_live_enabled"] = int(
            1 if bool(state25_candidate_threshold_live_v1.get("enabled")) else 0
        )
        row["state25_candidate_live_threshold_before"] = float(
            state25_candidate_threshold_live_v1.get(
                "baseline_entry_threshold",
                dynamic_threshold,
            )
            or 0.0
        )
        row["state25_candidate_live_threshold_after"] = float(
            state25_candidate_threshold_live_v1.get(
                "candidate_effective_entry_threshold",
                dynamic_threshold,
            )
            or 0.0
        )
        row["state25_candidate_live_threshold_delta"] = float(
            state25_candidate_threshold_live_v1.get(
                "threshold_delta_points",
                0.0,
            )
            or 0.0
        )
        row["state25_candidate_live_threshold_direction"] = str(
            state25_candidate_threshold_live_v1.get(
                "threshold_delta_direction",
                "",
            )
            or ""
        )
        row["semantic_live_rollout_mode"] = str((semantic_live_guard_v1 or {}).get("mode", "") or "")
        row["semantic_live_alert"] = int(1 if bool((semantic_live_guard_v1 or {}).get("alert_active")) else 0)
        row["semantic_live_fallback_reason"] = str(
            (semantic_live_guard_v1 or {}).get("fallback_reason", "") or ""
        )
        row["semantic_shadow_available"] = int(
            1 if bool((semantic_shadow_prediction_v1 or {}).get("available")) else 0
        )
        row["semantic_shadow_reason"] = str((semantic_shadow_prediction_v1 or {}).get("reason", "") or "")
        row["semantic_shadow_activation_state"] = str(semantic_shadow_activation_state or "")
        row["semantic_shadow_activation_reason"] = str(semantic_shadow_activation_reason or "")
        row["semantic_live_symbol_allowed"] = int(
            1 if bool((semantic_live_guard_v1 or {}).get("symbol_allowed")) else 0
        )
        row["semantic_live_entry_stage_allowed"] = int(
            1 if bool((semantic_live_guard_v1 or {}).get("entry_stage_allowed")) else 0
        )
        row["semantic_live_threshold_before"] = int(
            (semantic_live_guard_v1 or {}).get("threshold_before", dynamic_threshold) or dynamic_threshold
        )
        row["semantic_live_threshold_after"] = int(
            (semantic_live_guard_v1 or {}).get("threshold_after", dynamic_threshold) or dynamic_threshold
        )
        row["semantic_live_threshold_adjustment"] = int(
            (semantic_live_guard_v1 or {}).get("threshold_adjustment_points", 0) or 0
        )
        row["semantic_live_threshold_applied"] = int(
            1 if bool((semantic_live_guard_v1 or {}).get("threshold_applied")) else 0
        )
        row["semantic_live_threshold_state"] = str(semantic_live_threshold_state or "")
        row["semantic_live_threshold_reason"] = str(semantic_live_threshold_reason or "")
        row["semantic_live_partial_weight"] = float(
            (semantic_live_guard_v1 or {}).get("partial_live_weight", 0.0) or 0.0
        )
        row["semantic_live_partial_live_applied"] = int(
            1 if bool((semantic_live_guard_v1 or {}).get("partial_live_applied")) else 0
        )
        row["semantic_live_reason"] = str((semantic_live_guard_v1 or {}).get("reason", "") or "")
        row["entry_score_raw"] = float(score)
        row["entry_contra_score_raw"] = float(contra_score)
        row["entry_gate_mode_topdown"] = str(topdown_mode)
        row["entry_gate_mode_h1"] = str(h1_mode)
        if isinstance(self.runtime.latest_signal_by_symbol, dict):
            self.runtime.latest_signal_by_symbol[symbol] = row
    except Exception:
        pass

    if str(action or "").upper() in {"BUY", "SELL"} and str(setup_id or "").strip():
        current_cycle_runtime_context_row_v1 = _current_entry_runtime_signal_row(
            refresh_current_cycle=True
        )
        active_action_conflict_runtime_context_v1 = (
            _build_active_action_conflict_runtime_context_v1(
                runtime_snapshot_row=current_cycle_runtime_context_row_v1,
                symbol=str(symbol),
                action=str(action or ""),
                setup_id=str(setup_id or ""),
                setup_reason=str(setup_reason or ""),
                setup_side=str(setup_side or action or ""),
                entry_session_name=str(entry_session_name or ""),
                wait_state=wait_state,
                entry_wait_decision=str(entry_wait_decision or ""),
                score=float(score),
                contra_score=float(contra_score),
                prediction_bundle=prediction_bundle,
                shadow_transition_forecast_v1=shadow_transition_forecast_v1,
                shadow_trade_management_forecast_v1=shadow_trade_management_forecast_v1,
                shadow_observe_confirm=shadow_observe_confirm,
                entry_stage=str(entry_stage or ""),
                actual_effective_entry_threshold=float(dynamic_threshold),
                actual_size_multiplier=1.0,
                state25_candidate_runtime_state=getattr(
                    self.runtime, "state25_candidate_runtime_state", {}
                ),
            )
        )
        semantic_owner_bundle = dict(
            active_action_conflict_runtime_context_v1.get("semantic_owner_bundle", {}) or {}
        )
        forecast_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("forecast_state25_runtime_bridge_v1", {}) or {}
        )
        forecast_state25_log_only_overlay_trace_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "forecast_state25_log_only_overlay_trace_v1", {}
            )
            or {}
        )
        belief_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("belief_state25_runtime_bridge_v1", {}) or {}
        )
        belief_action_hint_v1 = dict(
            active_action_conflict_runtime_context_v1.get("belief_action_hint_v1", {})
            or {}
        )
        barrier_state25_runtime_bridge_v1 = dict(
            semantic_owner_bundle.get("barrier_state25_runtime_bridge_v1", {}) or {}
        )
        barrier_action_hint_v1 = dict(
            active_action_conflict_runtime_context_v1.get("barrier_action_hint_v1", {})
            or {}
        )
        state25_candidate_log_only_trace_v1 = dict(
            semantic_owner_bundle.get("state25_candidate_log_only_trace_v1", {}) or {}
        )
        observe_confirm_runtime_payload = dict(
            semantic_owner_bundle.get("observe_confirm_runtime_payload", {}) or {}
        )
        countertrend_continuation_signal_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "countertrend_continuation_signal_v1", {}
            )
            or {}
        )
        active_action_conflict_guard_v1 = dict(
            active_action_conflict_runtime_context_v1.get(
                "active_action_conflict_guard_v1", {}
            )
            or {}
        )
        directional_continuation_promotion_v1 = _build_directional_continuation_promotion_v1(
            symbol=str(symbol),
            baseline_action=str(
                active_action_conflict_guard_v1.get("baseline_action", "")
                or baseline_action_side_v1
                or ""
            ),
            runtime_signal_row=current_cycle_runtime_context_row_v1,
            active_action_conflict_guard_v1=active_action_conflict_guard_v1,
        )
        promotion_active_v1 = bool(directional_continuation_promotion_v1.get("active", False))
        if bool(active_action_conflict_guard_v1.get("guard_applied", False)) and not promotion_active_v1:
            baseline_action_value = str(
                active_action_conflict_guard_v1.get("baseline_action", "") or action or ""
            )
            action = None
            observe_reason = str(
                active_action_conflict_guard_v1.get("downgraded_observe_reason", "")
                or observe_reason
                or "directional_conflict_watch"
            )
            action_none_reason = str(
                active_action_conflict_guard_v1.get("failure_label", "")
                or action_none_reason
                or "wrong_side_conflict_pressure"
            )
            blocked_reason = str(
                active_action_conflict_guard_v1.get("failure_code", "")
                or "active_action_conflict_guard"
            )
            core_blocked_reason = str(blocked_reason)
            skip_outcome, skip_reason = _apply_wait_routing(
                blocked_reason,
                blocked_by_value=str(blocked_reason),
                observe_reason_value=str(observe_reason),
                action_none_reason_value=str(action_none_reason),
                action_value=str(baseline_action_value),
                raw_score_value=float(score),
                effective_threshold_value=float(dynamic_threshold),
            )
            _mark_skip(
                skip_reason,
                action=str(baseline_action_value),
                setup_id=str(setup_id),
                setup_side=str(setup_side),
                setup_status=str(setup_status),
                setup_trigger_state=str(setup_trigger_state),
                setup_score=float(setup_score),
                setup_entry_quality=float(setup_entry_quality),
                setup_reason=str(setup_reason),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action="",
                    considered=1,
                    outcome=str(skip_outcome),
                    blocked_by=str(skip_reason),
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                )
            )
            return
        if promotion_active_v1:
            promoted_action_v1 = str(directional_continuation_promotion_v1.get("promoted_action", "") or "")
            if promoted_action_v1 in {"BUY", "SELL"}:
                action = str(promoted_action_v1)
                core_pass = max(1, int(core_pass))
                core_reason = str(
                    directional_continuation_promotion_v1.get("promotion_reason", "")
                    or "directional_continuation_overlay_promotion"
                )
                core_allowed_action = str(action)
                action_none_reason = ""
                blocked_reason = ""
                core_blocked_reason = ""
                entry_stage = str(
                    directional_continuation_promotion_v1.get("recommended_entry_stage", entry_stage)
                    or entry_stage
                )
    utility_p = None
    utility_w = None
    utility_l = None
    utility_cost = None
    utility_context_adj = None
    utility_u = None
    utility_u_min = None
    utility_pass = None
    decision_rule_version = "legacy_v1"
    utility_enabled = bool(getattr(Config, "ENABLE_ENTRY_UTILITY_GATE", True))
    stats = self._load_symbol_utility_stats(symbol) if utility_enabled else None
    utility_ready = bool(
        utility_enabled
        and (entry_prob is not None)
        and isinstance(stats, dict)
        and bool(stats.get("ready", False))
    )
    if isinstance(stats, dict):
        utility_stats_ready = int(1 if bool(stats.get("ready", False)) else 0)
        utility_wins_n = int(stats.get("wins_n", 0) or 0)
        utility_losses_n = int(stats.get("losses_n", 0) or 0)
    stage_probs = entry_stage_detail.get("p", {}) if isinstance(entry_stage_detail, dict) else {}
    stage_prior = float(stage_probs.get(str(entry_stage), 0.50) or 0.50)
    if utility_ready:
        utility_p_raw = max(0.0, min(1.0, float(entry_prob)))
        utility_p_calibrated = _calibrate_p(prob_raw=utility_p_raw, stage_prior=stage_prior, stats_obj=stats)
        p_weight = max(0.0, min(1.0, float(getattr(Config, "ENTRY_UTILITY_P_WEIGHT", 0.35))))
        utility_p = max(0.0, min(1.0, float(0.5 + (p_weight * (utility_p_calibrated - 0.5)))))
        w_mult = max(0.20, float(getattr(Config, "ENTRY_UTILITY_WIN_MULT", 1.0)))
        l_mult = max(0.20, float(getattr(Config, "ENTRY_UTILITY_LOSS_MULT", 0.70)))
        utility_w = max(0.0, float(stats.get("w_avg", 0.0) or 0.0) * w_mult)
        utility_l = max(0.0, float(stats.get("l_avg", 0.0) or 0.0) * l_mult)
        utility_cost = max(0.0, float(self._estimate_entry_cost(symbol=symbol, regime=regime, spread_now=spread_now)))
        utility_context_adj = float(self._context_usd_adjustment(context_adj=context_adj, topdown_ok=topdown_ok, gate_ok=gate_ok))
        if decision_mode == "utility_only":
            score_margin = 0.0
        else:
            score_margin = (float(final_entry_score) - float(dynamic_threshold)) / max(1.0, float(dynamic_threshold))
            score_margin = max(-1.0, min(1.0, float(score_margin)))
        utility_context_adj += float(score_margin * float(getattr(Config, "ENTRY_UTILITY_SCORE_MARGIN_SCALE_USD", 0.45)))
        utility_u = float((utility_p * utility_w) - ((1.0 - utility_p) * utility_l) - utility_cost + utility_context_adj)
        utility_u_min = float(self._utility_min(symbol=symbol, same_dir_count=len(same_dir_positions)))
        decision_rule_version = "utility_ev_lite_v1"
    elif utility_enabled and decision_mode == "utility_only":
        utility_p_raw = float(entry_prob) if entry_prob is not None else stage_prior
        utility_p_raw = max(0.0, min(1.0, utility_p_raw))
        utility_p_calibrated = _calibrate_p(
            prob_raw=utility_p_raw,
            stage_prior=stage_prior,
            stats_obj=stats if isinstance(stats, dict) else None,
        )
        p_weight = max(0.0, min(1.0, float(getattr(Config, "ENTRY_UTILITY_P_WEIGHT", 0.35))))
        utility_p = max(0.0, min(1.0, float(0.5 + (p_weight * (utility_p_calibrated - 0.5)))))
        w_mult = max(0.20, float(getattr(Config, "ENTRY_UTILITY_WIN_MULT", 1.0)))
        l_mult = max(0.20, float(getattr(Config, "ENTRY_UTILITY_LOSS_MULT", 0.70)))
        fallback_w = float(
            Config.get_symbol_float(
                symbol,
                getattr(Config, "ENTRY_UTILITY_FALLBACK_WIN_BY_SYMBOL", {"DEFAULT": float(getattr(Config, "ENTRY_UTILITY_FALLBACK_WIN_USD", 1.0))}),
                float(getattr(Config, "ENTRY_UTILITY_FALLBACK_WIN_USD", 1.0)),
            )
        )
        fallback_l = float(
            Config.get_symbol_float(
                symbol,
                getattr(Config, "ENTRY_UTILITY_FALLBACK_LOSS_BY_SYMBOL", {"DEFAULT": float(getattr(Config, "ENTRY_UTILITY_FALLBACK_LOSS_USD", 1.0))}),
                float(getattr(Config, "ENTRY_UTILITY_FALLBACK_LOSS_USD", 1.0)),
            )
        )
        utility_w = max(0.0, fallback_w * w_mult)
        utility_l = max(0.0, fallback_l * l_mult)
        utility_cost = max(0.0, float(self._estimate_entry_cost(symbol=symbol, regime=regime, spread_now=spread_now)))
        utility_context_adj = float(self._context_usd_adjustment(context_adj=context_adj, topdown_ok=topdown_ok, gate_ok=gate_ok))
        utility_u = float((utility_p * utility_w) - ((1.0 - utility_p) * utility_l) - utility_cost + utility_context_adj)
        utility_u_min = float(self._utility_min(symbol=symbol, same_dir_count=len(same_dir_positions)))
        decision_rule_version = "utility_ev_lite_fallback_v1"
        utility_ready = True

    _refresh_prediction_bundle(float(score), float(contra_score), float(dynamic_threshold))

    ok_bb, bb_reason = self._pass_bb_entry_guard(symbol=symbol, action=action, tick=tick, indicators=entry_indicators)
    if not ok_bb:
        if bool(getattr(Config, "ENABLE_BB_GUARD_HARD_RETURN", False)):
            _mark_skip(bb_reason, entry_stage=str(entry_stage), action=str(action))
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by=str(bb_reason),
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                    entry_stage=str(entry_stage),
                    ai_probability=float(entry_prob) if entry_prob is not None else None,
                )
            )
            return
        if bool(getattr(Config, "ENABLE_UTILITY_BB_PENALTY", True)):
            pen = float(self._bb_penalty_usd(symbol=symbol, reason=bb_reason))
            if pen > 0.0:
                bb_penalty_usd += float(pen)
            bb_flags.append(str(bb_reason))
            try:
                row = self.runtime.latest_signal_by_symbol.get(symbol, {}) if isinstance(self.runtime.latest_signal_by_symbol, dict) else {}
                if not isinstance(row, dict):
                    row = {}
                row["bb_penalty_usd"] = float(bb_penalty_usd)
                row["bb_flags"] = "|".join([str(x) for x in bb_flags if str(x)])
                row["bb_guard_count"] = int(len(bb_flags))
                if isinstance(self.runtime.latest_signal_by_symbol, dict):
                    self.runtime.latest_signal_by_symbol[symbol] = row
            except Exception:
                pass

    if utility_ready:
        utility_u = float((utility_u or 0.0) - float(bb_penalty_usd))
        utility_pass = int(1 if float(utility_u) >= float(utility_u_min or 0.0) else 0)
        if utility_pass <= 0:
            skip_outcome, skip_reason = _apply_wait_routing(
                "utility_below_u_min",
                action_value=str(action),
                raw_score_value=float(score),
                effective_threshold_value=float(dynamic_threshold),
                utility_u_value=utility_u,
                utility_u_min_value=utility_u_min,
            )
            _mark_skip(
                skip_reason,
                utility_u=float(utility_u),
                u_min=float(utility_u_min),
                utility_p=float(utility_p),
                utility_w=float(utility_w),
                utility_l=float(utility_l),
                utility_cost=float(utility_cost),
                utility_context_adj=float(utility_context_adj),
                bb_penalty_usd=float(bb_penalty_usd),
                bb_flags="|".join([str(x) for x in bb_flags if str(x)]),
                entry_stage=str(entry_stage),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome=str(skip_outcome),
                    blocked_by=str(skip_reason),
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                    entry_stage=str(entry_stage),
                    ai_probability=float(entry_prob) if entry_prob is not None else None,
                    utility_u=utility_u,
                    utility_p=utility_p,
                    utility_w=utility_w,
                    utility_l=utility_l,
                    utility_cost=utility_cost,
                    utility_context_adj=utility_context_adj,
                    u_min=utility_u_min,
                    u_pass=utility_pass,
                    decision_rule_version=decision_rule_version,
                                last_order_retcode=order_block_status.get("retcode"),
                last_order_comment=str(order_block_status.get("comment", "") or getattr(self.runtime, "last_order_comment", "")),
                order_block_remaining_sec=int(order_block_status.get("remaining_sec", 0) or 0),
            )
            )
            return
    else:
        if decision_mode == "utility_only":
            _mark_skip(
                "utility_not_ready",
                ai_probability=(None if entry_prob is None else float(entry_prob)),
                entry_stage=str(entry_stage),
                decision_mode=str(decision_mode),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="utility_not_ready",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                    entry_stage=str(entry_stage),
                    ai_probability=float(entry_prob) if entry_prob is not None else None,
                    decision_rule_version=decision_rule_version,
                )
            )
            return
        if bb_penalty_usd > 0.0:
            # Legacy fallback path: convert BB soft penalties into stricter threshold.
            bb_penalty_pts = int(round(float(bb_penalty_usd) * max(8.0, float(dynamic_threshold) * 0.10)))
            dynamic_threshold += max(0, int(bb_penalty_pts))
        if int(final_entry_score) < int(dynamic_threshold):
            skip_outcome, skip_reason = _apply_wait_routing(
                "dynamic_threshold_not_met",
                action_value=str(action),
                raw_score_value=float(final_entry_score),
                effective_threshold_value=float(dynamic_threshold),
                utility_u_value=utility_u,
                utility_u_min_value=utility_u_min,
            )
            _mark_skip(
                skip_reason,
                final_entry_score=float(final_entry_score),
                dynamic_threshold=int(dynamic_threshold),
                entry_stage=str(entry_stage),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome=str(skip_outcome),
                    blocked_by=str(skip_reason),
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                    entry_stage=str(entry_stage),
                    ai_probability=float(entry_prob) if entry_prob is not None else None,
                    size_multiplier=float(max(0.5, min(1.5, (1.0 / max(0.7, min(1.4, stage_mult)))))),
                    decision_rule_version=decision_rule_version,
                )
            )
            return
        if (entry_prob is not None) and (float(entry_prob) < float(stage_min_prob)):
            _mark_skip(
                "stage_min_prob_not_met",
                ai_probability=float(entry_prob),
                stage_min_prob=float(stage_min_prob),
                entry_stage=str(entry_stage),
            )
            self._append_entry_decision_log(
                _decision_payload(
                    action=str(action),
                    considered=1,
                    outcome="skipped",
                    blocked_by="stage_min_prob_not_met",
                    raw_score=float(score),
                    contra_score=float(contra_score),
                    effective_threshold=float(dynamic_threshold),
                    entry_stage=str(entry_stage),
                    ai_probability=float(entry_prob),
                    decision_rule_version=decision_rule_version,
                )
            )
            return
    _record_entry_back_stage("ai_threshold_and_utility", entry_back_stage_started_at)
    _set_entry_back_stage("post_threshold_guards")
    _store_entry_back_profile()

    ok_cluster, cluster_reason = self._pass_cluster_guard(
        symbol=symbol,
        action=action,
        tick=tick,
        setup_id=str(setup_id),
        setup_reason=str(setup_reason),
        preflight_allowed_action=str(preflight_allowed_action),
    )
    if not ok_cluster:
        _mark_skip(cluster_reason, entry_stage=str(entry_stage), action=str(action))
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(cluster_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
            )
        )
        return
    ok_box_mid, box_mid_reason = self._pass_box_middle_guard(
        symbol=symbol,
        action=action,
        tick=tick,
        df_all=df_all,
        scorer=scorer,
        indicators=entry_indicators,
        setup_id=str(setup_id),
        setup_reason=str(setup_reason),
        runtime_signal_row=_current_entry_runtime_signal_row(refresh_current_cycle=True),
    )
    if not ok_box_mid:
        _mark_skip(box_mid_reason, entry_stage=str(entry_stage), action=str(action))
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(box_mid_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
            )
        )
        return

    if same_dir_positions:
        entry_px = self._entry_price_for_action(action, tick)
        avg_open = float(
            sum(float(getattr(p, "price_open", 0.0) or 0.0) for p in same_dir_positions)
            / max(1, len(same_dir_positions))
        )
        dir_profit = float(sum(float(getattr(p, "profit", 0.0) or 0.0) for p in same_dir_positions))
        min_prog = abs(
            float(
                Config.get_symbol_float(
                    symbol,
                    getattr(
                        Config,
                        "ENTRY_PYRAMID_MIN_PROGRESS_PCT_BY_SYMBOL",
                        {"DEFAULT": getattr(Config, "ENTRY_PYRAMID_MIN_PROGRESS_PCT", 0.00035)},
                    ),
                    float(getattr(Config, "ENTRY_PYRAMID_MIN_PROGRESS_PCT", 0.00035)),
                )
            )
        )
        if entry_px > 0.0 and avg_open > 0.0:
            pyramid_mode = str(getattr(Config, "ENTRY_PYRAMID_MODE", "adverse") or "adverse").strip().lower()
            require_drawdown = bool(getattr(Config, "ENTRY_PYRAMID_REQUIRE_DRAWDOWN", True))
            edge_guard = bool(getattr(Config, "ENTRY_PYRAMID_EDGE_GUARD", True))
            pyramid_policy = _resolve_setup_specific_pyramid_policy(
                symbol=str(symbol),
                action=str(action),
                setup_id=str(setup_id),
                setup_reason=str(setup_reason),
                preflight_allowed_action=str(preflight_allowed_action),
                box_state=str(box_state),
                same_dir_count=len(same_dir_positions),
                pyramid_mode=str(pyramid_mode),
                require_drawdown=bool(require_drawdown),
                edge_guard=bool(edge_guard),
                min_prog=float(min_prog),
            )
            pyramid_mode = str(pyramid_policy.get("pyramid_mode", pyramid_mode) or pyramid_mode)
            require_drawdown = bool(pyramid_policy.get("require_drawdown", require_drawdown))
            edge_guard = bool(pyramid_policy.get("edge_guard", edge_guard))
            min_prog = abs(float(pyramid_policy.get("min_prog", min_prog) or min_prog))
            if pyramid_mode not in {"adverse", "progressive"}:
                pyramid_mode = "adverse"

            progressed = (
                (entry_px >= avg_open * (1.0 + min_prog))
                if action == "BUY"
                else (entry_px <= avg_open * (1.0 - min_prog))
            )
            adverse_progressed = (
                (entry_px <= avg_open * (1.0 - min_prog))
                if action == "BUY"
                else (entry_px >= avg_open * (1.0 + min_prog))
            )
            addon_ok = progressed if pyramid_mode == "progressive" else adverse_progressed

            if edge_guard:
                if action == "BUY" and str(box_state).upper() in {"UPPER", "ABOVE"}:
                    addon_ok = False
                if action == "SELL" and str(box_state).upper() in {"LOWER", "BELOW"}:
                    addon_ok = False

            if require_drawdown and dir_profit >= 0.0:
                addon_ok = False

            if not addon_ok:
                blocked = "pyramid_not_progressed"
                if require_drawdown and dir_profit >= 0.0:
                    blocked = "pyramid_not_in_drawdown"
                elif edge_guard and action == "BUY" and str(box_state).upper() in {"UPPER", "ABOVE"}:
                    blocked = "pyramid_chase_upper_blocked"
                elif edge_guard and action == "SELL" and str(box_state).upper() in {"LOWER", "BELOW"}:
                    blocked = "pyramid_chase_lower_blocked"
                _mark_skip(
                    blocked,
                    action=str(action),
                    avg_open=float(avg_open),
                    entry_price=float(entry_px),
                    min_progress_pct=float(min_prog),
                    pyramid_mode=str(pyramid_mode),
                    same_dir_profit=float(dir_profit),
                )
                self._append_entry_decision_log(
                    _decision_payload(
                        action=str(action),
                        considered=1,
                        outcome="skipped",
                        blocked_by=str(blocked),
                        raw_score=float(score),
                        contra_score=float(contra_score),
                        effective_threshold=float(dynamic_threshold),
                        entry_stage=str(entry_stage),
                        ai_probability=float(entry_prob) if entry_prob is not None else None,
                    )
                )
                return
    runtime_snapshot_row = _current_entry_runtime_signal_row(refresh_current_cycle=True)
    probe_promotion_guard_v1 = _build_probe_promotion_guard_v1(
        symbol=str(symbol),
        action=str(action),
        observe_reason=str(observe_reason or ""),
        blocked_by=str(core_blocked_reason or ""),
        action_none_reason=str(action_none_reason or ""),
        entry_probe_plan_v1=entry_probe_plan_v1,
        consumer_check_state_v1=consumer_check_state_v1,
        runtime_snapshot_row=runtime_snapshot_row,
    )
    probe_execution_v1 = _resolve_probe_execution_plan(
        symbol=str(symbol),
        action=str(action),
        entry_stage=str(entry_stage),
        base_lot=float(base_lot),
        min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
        same_dir_count=len(same_dir_positions),
        probe_plan_v1=entry_probe_plan_v1,
    )
    lot = float(probe_execution_v1.get("order_lot", lot) or lot)
    entry_stage = str(probe_execution_v1.get("effective_entry_stage", entry_stage) or entry_stage)
    if bool(probe_promotion_guard_v1.get("bounded_probe_promotion_active")) and bool(
        probe_promotion_guard_v1.get("allows_open")
    ):
        bounded_probe_target_lot = _normalize_order_lot(
            base_lot=float(base_lot),
            size_multiplier=float(probe_promotion_guard_v1.get("bounded_probe_size_multiplier", 0.35) or 0.35),
            min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
        )
        lot = min(float(lot), float(bounded_probe_target_lot))
        entry_stage = str(
            probe_promotion_guard_v1.get("bounded_probe_entry_stage", entry_stage) or entry_stage
        )
    if bool(directional_continuation_promotion_v1.get("active", False)) and not bool(
        directional_continuation_promotion_lot_applied_v1
    ):
        directional_continuation_target_lot_v1 = _normalize_order_lot(
            base_lot=float(base_lot),
            size_multiplier=float(directional_continuation_promotion_v1.get("size_multiplier", 0.30) or 0.30),
            min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
        )
        lot = min(float(lot), float(directional_continuation_target_lot_v1))
        entry_stage = str(
            directional_continuation_promotion_v1.get("recommended_entry_stage", entry_stage)
            or entry_stage
        )
        directional_continuation_promotion_lot_applied_v1 = True
    p7_guarded_size_overlay_v1 = resolve_p7_guarded_size_overlay_v1(
        symbol=str(symbol),
        action=str(action),
        entry_stage=str(entry_stage),
        base_lot=float(base_lot),
        proposed_lot=float(lot),
        min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
    )
    if bool(p7_guarded_size_overlay_v1.get("apply_allowed")):
        lot = float(p7_guarded_size_overlay_v1.get("effective_lot", lot) or lot)
    if bool(teacher_label_exploration_entry_v1.get("active")) and not bool(teacher_label_exploration_lot_applied_v1):
        teacher_label_exploration_target_lot_v1 = _normalize_order_lot(
            base_lot=float(base_lot),
            size_multiplier=float(teacher_label_exploration_entry_v1.get("size_multiplier", 1.0) or 1.0),
            min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
        )
        lot = min(float(lot), float(teacher_label_exploration_target_lot_v1))
        teacher_label_exploration_lot_applied_v1 = True
    if bool(probe_promotion_guard_v1.get("guard_active")) and not bool(probe_promotion_guard_v1.get("allows_open")):
        fail_reason = str(probe_promotion_guard_v1.get("failure_code", "") or "probe_promotion_gate")
        teacher_label_exploration_entry_v1 = _build_teacher_label_exploration_entry_v1(
            symbol=str(symbol),
            action=str(action),
            observe_reason=str(observe_reason or ""),
            action_none_reason=str(action_none_reason or "probe_not_promoted"),
            blocked_by=str(core_blocked_reason or fail_reason),
            probe_scene_id=str(
                probe_promotion_guard_v1.get("probe_scene_id", "")
                or entry_probe_plan_v1.get("symbol_scene_relief", "")
                or consumer_check_state_v1.get("probe_scene_id", "")
                or ""
            ),
            consumer_check_state_v1=consumer_check_state_v1,
            guard_failure_code=str(fail_reason),
            score=float(score),
            effective_threshold=float(dynamic_threshold),
            same_dir_count=len(same_dir_positions),
        )
        if bool(teacher_label_exploration_entry_v1.get("active")):
            if not bool(teacher_label_exploration_lot_applied_v1):
                lot = _normalize_order_lot(
                    base_lot=float(lot),
                    size_multiplier=float(teacher_label_exploration_entry_v1.get("size_multiplier", 1.0) or 1.0),
                    min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
                )
                teacher_label_exploration_lot_applied_v1 = True
        else:
            _mark_skip(
                fail_reason,
                blocked_by_value=str(fail_reason),
                observe_reason_value=str(observe_reason or ""),
                action_none_reason_value=str(action_none_reason or "probe_not_promoted"),
                action=str(action),
                probe_promotion_guard_v1=dict(probe_promotion_guard_v1),
            )
            skip_row = _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(fail_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
                size_multiplier=float(lot / max(1e-9, float(base_lot))),
                utility_u=utility_u,
                utility_p=utility_p,
                utility_w=utility_w,
                utility_l=utility_l,
                utility_cost=utility_cost,
                utility_context_adj=utility_context_adj,
                u_min=utility_u_min,
                u_pass=utility_pass,
                decision_rule_version=decision_rule_version,
            )
            skip_row["probe_promotion_guard_v1"] = dict(probe_promotion_guard_v1)
            self._append_entry_decision_log(skip_row)
            return
    try:
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        row = {}
        if isinstance(rows, dict):
            row = rows.get(symbol, {})
        if not isinstance(row, dict):
            row = {}
        directional_runtime_surface_v1 = _refresh_directional_runtime_execution_surface_v1(
            runtime_owner=getattr(self, "runtime", None),
            symbol=str(symbol),
            runtime_row=row,
            baseline_action=str(original_action_side_v1 or ""),
            current_action=str(action or ""),
            blocked_by=str(blocked_reason or ""),
            observe_reason=str(observe_reason or ""),
            action_none_reason=str(action_none_reason or ""),
            setup_id=str(setup_id or ""),
            setup_reason=str(setup_reason or observe_reason or ""),
            forecast_state25_log_only_overlay_trace_v1=dict(
                forecast_state25_log_only_overlay_trace_v1 or {}
            ),
            belief_action_hint_v1=dict(belief_action_hint_v1 or {}),
            barrier_action_hint_v1=dict(barrier_action_hint_v1 or {}),
            countertrend_continuation_signal_v1=dict(
                countertrend_continuation_signal_v1 or {}
            ),
            breakout_event_runtime_v1=dict(breakout_event_runtime_v1 or {}),
            breakout_event_overlay_candidates_v1=dict(
                breakout_event_overlay_candidates_v1 or {}
            ),
        )
        active_action_conflict_guard_v1 = dict(
            directional_runtime_surface_v1.get(
                "active_action_conflict_guard_v1",
                active_action_conflict_guard_v1,
            )
            or {}
        )
        directional_continuation_promotion_v1 = dict(
            directional_runtime_surface_v1.get(
                "directional_continuation_promotion_v1",
                directional_continuation_promotion_v1,
            )
            or {}
        )
        execution_action_diff_v1 = dict(
            directional_runtime_surface_v1.get("execution_action_diff_v1", {}) or {}
        )
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if isinstance(rows, dict):
            row = dict(directional_runtime_surface_v1.get("runtime_row", row) or {})
            rows[symbol] = row
    except Exception:
        pass
    _record_entry_back_stage("post_threshold_guards", entry_back_stage_started_at)
    _set_entry_back_stage("trace_and_preorder")
    _store_entry_back_profile()
    stage_probs = entry_stage_detail.get("p", {}) if isinstance(entry_stage_detail, dict) else {}
    stage_conf = 0.0
    try:
        stage_conf = max([float(v) for v in dict(stage_probs).values()] or [0.0])
    except Exception:
        stage_conf = 0.0
    model_conf = float(entry_prob) if entry_prob is not None else float(stage_conf)
    threshold_margin = 0.0
    try:
        threshold_margin = (float(final_entry_score) - float(dynamic_threshold)) / max(1.0, float(dynamic_threshold))
    except Exception:
        threshold_margin = 0.0
    threshold_margin = max(-1.0, min(1.0, threshold_margin))
    entry_quality = max(0.0, min(1.0, (0.60 * model_conf) + (0.40 * ((threshold_margin + 1.0) / 2.0))))
    regime_at_entry = str(regime.get("name", "") or "").strip().upper()
    prediction_bundle.setdefault("metadata", {})
    prediction_bundle["metadata"]["entry_probe_execution_v1"] = dict(probe_execution_v1)
    prediction_bundle["metadata"]["p7_guarded_size_overlay_v1"] = dict(p7_guarded_size_overlay_v1 or {})
    prediction_bundle["metadata"]["p7_guarded_size_overlay_contract_v1"] = dict(
        P7_GUARDED_SIZE_OVERLAY_CONTRACT_V1
    )
    wait_state = self._wait_engine.build_entry_wait_state_from_row(
        symbol=str(symbol),
        row=_wait_input_row(
            action_value=str(action or ""),
            observe_reason_value=str(observe_reason or ""),
            blocked_by_value="",
            action_none_reason_value=str(action_none_reason or ""),
        ),
    )
    _materialize_shadow_runtime_maps()

    self.decision_recorder.record_trace(
        {
            "symbol": symbol,
            "action": action,
            "raw_score": score,
            "contra_score": contra_score,
            "probability": entry_prob,
            "score_adj": entry_adj,
            "final_score": final_entry_score,
            "threshold": Config.AI_ENTRY_THRESHOLD,
            "blocked": entry_blocked,
            "regime": regime.get("name", ""),
            "volume_ratio": regime.get("volume_ratio"),
            "volatility_ratio": regime.get("volatility_ratio"),
            "spread_ratio": regime.get("spread_ratio"),
            "buy_multiplier": regime.get("buy_multiplier"),
            "sell_multiplier": regime.get("sell_multiplier"),
            "entry_stage": entry_stage,
            "entry_stage_probs": entry_stage_detail.get("p", {}),
            "entry_stage_hist_n": entry_stage_detail.get("hist_n", 0),
            "entry_dynamic_threshold": int(dynamic_threshold),
            "entry_quality": round(float(entry_quality), 4),
            "entry_model_confidence": round(float(model_conf), 4),
            "regime_at_entry": regime_at_entry,
            "entry_h1_context_score": int(entry_h1_context_score),
            "entry_h1_context_opposite": int(entry_h1_context_opposite),
            "entry_m1_trigger_score": int(entry_m1_trigger_score),
            "entry_m1_trigger_opposite": int(entry_m1_trigger_opposite),
            "entry_h1_gate_pass": bool(gate_ok),
            "entry_h1_gate_reason": str(gate_reason),
            "entry_topdown_gate_pass": bool(topdown_ok),
            "entry_topdown_gate_reason": str(topdown_reason),
            "setup_id": str(setup_id),
            "setup_status": str(setup_status),
            "setup_trigger_state": str(setup_trigger_state),
            "setup_score": float(setup_score),
            "setup_reason": str(setup_reason),
            "entry_topdown_align_count": int(topdown_stat.get("align", 0)),
            "entry_topdown_conflict_count": int(topdown_stat.get("conflict", 0)),
            "entry_topdown_seen_count": int(topdown_stat.get("seen", 0)),
            "entry_session_name": str(entry_session_name),
            "entry_weekday": int(entry_weekday),
            "entry_session_threshold_mult": float(entry_session_threshold_mult),
            "entry_atr_ratio": float(entry_atr_ratio),
            "entry_atr_threshold_mult": float(entry_atr_threshold_mult),
            "preflight_regime": str(preflight_regime),
            "preflight_liquidity": str(preflight_liquidity),
            "preflight_allowed_action": str(preflight_allowed_action),
            "preflight_approach_mode": str(preflight_approach_mode),
            "preflight_reason": str(preflight_reason),
            "effective_entry_threshold": int(dynamic_threshold),
            "base_entry_threshold": int(entry_threshold),
            **_build_execution_action_diff_flat_fields_v1(execution_action_diff_v1),
            "forecast_state25_log_only_overlay_trace_v1": build_forecast_state25_log_only_overlay_trace_v1(
                build_forecast_state25_runtime_bridge_v1(
                    {
                        **dict(runtime_snapshot_row or {}),
                        "symbol": str(symbol),
                        "action": str(action or ""),
                        "direction": str(action or ""),
                        "setup_id": str(setup_id or ""),
                        "entry_setup_id": str(setup_id or ""),
                        "setup_side": str(setup_side or action or ""),
                        "entry_session_name": str(entry_session_name or ""),
                        "entry_wait_state": str(wait_state.state or ""),
                        "entry_wait_reason": str(wait_state.reason or ""),
                        "entry_wait_decision": str(entry_wait_decision or ""),
                        "entry_score": float(score),
                        "contra_score_at_entry": float(contra_score),
                        "raw_score": float(score),
                        "contra_score": float(contra_score),
                        "prediction_bundle": prediction_bundle,
                        "transition_forecast_v1": dict(shadow_transition_forecast_v1),
                        "trade_management_forecast_v1": dict(shadow_trade_management_forecast_v1),
                        "forecast_gap_metrics_v1": {
                            "transition_side_separation": float(
                                (((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("side_separation", 0.0)) or 0.0)
                            ),
                            "transition_confirm_fake_gap": float(
                                (((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("confirm_fake_gap", 0.0)) or 0.0)
                            ),
                            "transition_reversal_continuation_gap": float(
                                (((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("reversal_continuation_gap", 0.0)) or 0.0)
                            ),
                            "management_continue_fail_gap": float(
                                (((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("continue_fail_gap", 0.0)) or 0.0)
                            ),
                            "management_recover_reentry_gap": float(
                                (((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("recover_reentry_gap", 0.0)) or 0.0)
                            ),
                            "wait_confirm_gap": float(
                                runtime_snapshot_row.get("wait_confirm_gap", 0.0)
                                if runtime_snapshot_row.get("wait_confirm_gap", None) not in ("", None)
                                else 0.0
                            ),
                            "hold_exit_gap": float(
                                runtime_snapshot_row.get("hold_exit_gap", 0.0)
                                if runtime_snapshot_row.get("hold_exit_gap", None) not in ("", None)
                                else 0.0
                            ),
                            "same_side_flip_gap": float(
                                runtime_snapshot_row.get("same_side_flip_gap", 0.0)
                                if runtime_snapshot_row.get("same_side_flip_gap", None) not in ("", None)
                                else 0.0
                            ),
                            "belief_barrier_tension_gap": float(
                                runtime_snapshot_row.get("belief_barrier_tension_gap", 0.0)
                                if runtime_snapshot_row.get("belief_barrier_tension_gap", None) not in ("", None)
                                else 0.0
                            ),
                        },
                        "observe_confirm_v2": dict(observe_confirm_runtime_metadata.get("observe_confirm_v2", {})),
                    }
                ),
                symbol=str(symbol),
                entry_stage=str(entry_stage),
                actual_effective_entry_threshold=float(dynamic_threshold),
                actual_size_multiplier=float(lot / max(1e-9, float(base_lot))),
            ),
            "state25_candidate_context_bridge_v1": build_state25_candidate_context_bridge_v1(
                {
                    **dict(runtime_snapshot_row or {}),
                    "symbol": str(symbol),
                    "entry_stage": str(entry_stage),
                    "consumer_check_side": str(action or ""),
                    "state25_candidate_runtime_v1": dict(
                        getattr(self.runtime, "state25_candidate_runtime_state", {}) or {}
                    ),
                }
            ),
            "state25_candidate_log_only_trace_v1": build_state25_candidate_entry_log_only_trace_v1(
                getattr(self.runtime, "state25_candidate_runtime_state", {}),
                symbol=str(symbol),
                entry_stage=str(entry_stage),
                actual_effective_entry_threshold=float(dynamic_threshold),
                actual_size_multiplier=float(lot / max(1e-9, float(base_lot))),
            ),
            "blocked_by": "",
            "p7_guarded_size_overlay_v1": dict(p7_guarded_size_overlay_v1 or {}),
            "teacher_label_exploration_active": bool(
                (teacher_label_exploration_entry_v1 or {}).get("active", False)
            ),
            "teacher_label_exploration_family": str(
                (teacher_label_exploration_entry_v1 or {}).get("family", "") or ""
            ),
            "teacher_label_exploration_reason": str(
                (teacher_label_exploration_entry_v1 or {}).get("activation_reason", "") or ""
            ),
            "teacher_label_exploration_entry_v1": dict(teacher_label_exploration_entry_v1 or {}),
            **build_state25_candidate_context_bridge_flat_fields_v1(
                build_state25_candidate_context_bridge_v1(
                    {
                        **dict(runtime_snapshot_row or {}),
                        "symbol": str(symbol),
                        "entry_stage": str(entry_stage),
                        "consumer_check_side": str(action or ""),
                        "state25_candidate_runtime_v1": dict(
                            getattr(self.runtime, "state25_candidate_runtime_state", {}) or {}
                        ),
                    }
                )
            ),
        }
    )

    (
        effective_consumer_check_candidate,
        effective_consumer_check_display_ready,
        effective_consumer_check_entry_ready,
        effective_consumer_check_side,
        effective_consumer_check_stage,
        effective_consumer_check_reason,
        effective_consumer_check_display_strength_level,
        effective_consumer_check_state_v1,
    ) = _resolve_effective_consumer_check_state(
        blocked_by_value="",
        action_value=str(action),
    )
    consumer_open_guard_v1 = evaluate_consumer_open_guard_v1(
        consumer_check_state_v1=effective_consumer_check_state_v1,
        action=str(action),
    )
    if bool(consumer_open_guard_v1.get("guard_active")) and not bool(consumer_open_guard_v1.get("allows_open")):
        fail_reason = str(consumer_open_guard_v1.get("failure_code", "") or "consumer_open_guard_blocked")
        if not bool(teacher_label_exploration_entry_v1.get("active")):
            teacher_label_exploration_entry_v1 = _build_teacher_label_exploration_entry_v1(
                symbol=str(symbol),
                action=str(action),
                observe_reason=str(observe_reason or ""),
                action_none_reason=str(
                    consumer_open_guard_v1.get("entry_block_reason", "") or action_none_reason or ""
                ),
                blocked_by=str(
                    consumer_open_guard_v1.get("entry_block_reason", "")
                    or effective_consumer_check_state_v1.get("blocked_display_reason", "")
                    or fail_reason
                ),
                probe_scene_id=str(effective_consumer_check_state_v1.get("probe_scene_id", "") or ""),
                consumer_check_state_v1=effective_consumer_check_state_v1,
                guard_failure_code=str(fail_reason),
                score=float(score),
                effective_threshold=float(dynamic_threshold),
                same_dir_count=len(same_dir_positions),
            )
            if bool(teacher_label_exploration_entry_v1.get("active")):
                if not bool(teacher_label_exploration_lot_applied_v1):
                    lot = _normalize_order_lot(
                        base_lot=float(lot),
                        size_multiplier=float(teacher_label_exploration_entry_v1.get("size_multiplier", 1.0) or 1.0),
                        min_lot=float(Config.LOT_SIZES.get("DEFAULT", 0.01)),
                    )
                    teacher_label_exploration_lot_applied_v1 = True
        if not bool(teacher_label_exploration_entry_v1.get("active")):
            _mark_skip(
                fail_reason,
                blocked_by_value=str(fail_reason),
                observe_reason_value=str(observe_reason or ""),
                action_none_reason_value=str(
                    consumer_open_guard_v1.get("entry_block_reason", "") or action_none_reason or ""
                ),
                action=str(action),
                consumer_open_guard_v1=dict(consumer_open_guard_v1),
            )
            skip_row = _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(fail_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
                size_multiplier=float(lot / max(1e-9, float(base_lot))),
                utility_u=utility_u,
                utility_p=utility_p,
                utility_w=utility_w,
                utility_l=utility_l,
                utility_cost=utility_cost,
                utility_context_adj=utility_context_adj,
                u_min=utility_u_min,
                u_pass=utility_pass,
                decision_rule_version=decision_rule_version,
            )
            skip_row["consumer_open_guard_v1"] = dict(consumer_open_guard_v1)
            self._append_entry_decision_log(skip_row)
            return

    order_block_status = {}
    get_order_block_status = getattr(self.runtime, "get_order_block_status", None)
    if callable(get_order_block_status):
        try:
            order_block_status = get_order_block_status(symbol)
        except Exception:
            order_block_status = {}
    if bool(order_block_status.get("active", False)):
        block_reason = str(order_block_status.get("reason", "") or "order_blocked")
        if block_reason == "market_closed":
            block_reason = "market_closed_cooldown"
        _mark_skip(
            block_reason,
            last_order_error=str(getattr(self.runtime, "last_order_error", "")),
            last_order_retcode=order_block_status.get("retcode"),
            order_block_remaining_sec=int(order_block_status.get("remaining_sec", 0) or 0),
        )
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(block_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
                size_multiplier=float(lot / max(1e-9, float(base_lot))),
                utility_u=utility_u,
                utility_p=utility_p,
                utility_w=utility_w,
                utility_l=utility_l,
                utility_cost=utility_cost,
                utility_context_adj=utility_context_adj,
                u_min=utility_u_min,
                u_pass=utility_pass,
                decision_rule_version=decision_rule_version,
                last_order_retcode=order_block_status.get("retcode"),
                last_order_comment=str(order_block_status.get("comment", "") or getattr(self.runtime, "last_order_comment", "")),
                order_block_remaining_sec=int(order_block_status.get("remaining_sec", 0) or 0),
            )
        )
        return

    _record_entry_back_stage("trace_and_preorder", entry_back_stage_started_at)
    _set_entry_back_stage("order_submit_and_log")
    _store_entry_back_profile()
    order_submit_started_at = time.time()
    sub_stage_started_at = time.perf_counter()
    ticket = self.runtime.execute_order(symbol, action, lot)
    order_submit_latency_ms = int(max(0.0, round((time.time() - order_submit_started_at) * 1000.0)))
    _record_entry_back_stage("order_submit_broker", sub_stage_started_at)
    if not ticket:
        last_retcode = getattr(self.runtime, "last_order_retcode", None)
        last_comment = str(getattr(self.runtime, "last_order_comment", "") or "")
        post_block_status = {}
        if callable(get_order_block_status):
            try:
                post_block_status = get_order_block_status(symbol)
            except Exception:
                post_block_status = {}
        fail_reason = "order_send_failed"
        if int(last_retcode or 0) == 10018 or str(post_block_status.get("reason", "")).lower() == "market_closed":
            fail_reason = "market_closed_session"
        _mark_skip(
            fail_reason,
            last_order_error=str(getattr(self.runtime, "last_order_error", "")),
            last_order_retcode=last_retcode,
            last_order_comment=last_comment,
            order_block_remaining_sec=int(post_block_status.get("remaining_sec", 0) or 0),
        )
        sub_stage_started_at = time.perf_counter()
        self._append_entry_decision_log(
            _decision_payload(
                action=str(action),
                considered=1,
                outcome="skipped",
                blocked_by=str(fail_reason),
                raw_score=float(score),
                contra_score=float(contra_score),
                effective_threshold=float(dynamic_threshold),
                entry_stage=str(entry_stage),
                ai_probability=float(entry_prob) if entry_prob is not None else None,
                size_multiplier=float(lot / max(1e-9, float(base_lot))),
                utility_u=utility_u,
                utility_p=utility_p,
                utility_w=utility_w,
                utility_l=utility_l,
                utility_cost=utility_cost,
                utility_context_adj=utility_context_adj,
                u_min=utility_u_min,
                u_pass=utility_pass,
                decision_rule_version=decision_rule_version,
                order_submit_latency_ms=int(order_submit_latency_ms),
                last_order_retcode=last_retcode,
                last_order_comment=last_comment,
                order_block_remaining_sec=int(post_block_status.get("remaining_sec", 0) or 0),
            )
        )
        _record_entry_back_stage("entered_decision_log_append", sub_stage_started_at)
        return

    _mark_skip(
        "entered",
        entry_action=str(action),
        final_entry_score=float(final_entry_score),
        ai_probability=(None if entry_prob is None else float(entry_prob)),
        entry_stage=str(entry_stage),
        entry_h1_context_score=int(entry_h1_context_score),
        entry_h1_context_opposite=int(entry_h1_context_opposite),
        entry_m1_trigger_score=int(entry_m1_trigger_score),
        entry_m1_trigger_opposite=int(entry_m1_trigger_opposite),
        core_pass=int(core_pass),
        core_reason=str(core_reason),
        core_allowed_action=str(core_allowed_action),
        h1_bias_strength=float(h1_bias_strength),
        m1_trigger_strength=float(m1_trigger_strength),
        box_state=str(box_state),
        bb_state=str(bb_state),
        core_score=float(core_score),
        entry_h1_gate_pass=True,
        entry_h1_gate_reason=str(gate_reason),
        setup_id=str(setup_id),
        setup_status=str(setup_status),
        setup_reason=str(setup_reason),
    )
    self.runtime.last_entry_time[symbol] = time.time()
    price = tick.ask if action == "BUY" else tick.bid
    slip = self._slippage_policy.capture_entry(
        app=self.runtime,
        symbol=symbol,
        action=action,
        ticket=int(ticket),
        tick=tick,
    )
    current_runtime_row = {}
    try:
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if isinstance(rows, dict):
            candidate_row = rows.get(symbol, {})
            if isinstance(candidate_row, dict):
                current_runtime_row = dict(candidate_row)
    except Exception:
        current_runtime_row = {}
    entry_semantic_signature = self.guard_engine.build_cluster_semantic_signature(
        current_runtime_row,
        action=str(action or ""),
        setup_id=str(setup_id or ""),
        setup_reason=str(setup_reason or ""),
    )
    self.guard_engine.mark_entry(
        symbol=symbol,
        action=action,
        price=price,
        ts=time.time(),
        semantic_signature=entry_semantic_signature,
    )
    entered_trade_link_key = resolve_trade_link_key(
        {
            "ticket": int(ticket),
            "symbol": str(symbol),
            "action": str(action),
            "open_ts": int(time.time()),
        }
    )
    sub_stage_started_at = time.perf_counter()
    entered_row = self._append_entry_decision_log(
        _decision_payload(
            action=str(action),
            considered=1,
            outcome="entered",
            blocked_by="",
            raw_score=float(score),
            contra_score=float(contra_score),
            effective_threshold=float(dynamic_threshold),
            entry_stage=str(entry_stage),
            ai_probability=float(entry_prob) if entry_prob is not None else None,
            size_multiplier=float(lot / max(1e-9, float(base_lot))),
            utility_u=utility_u,
            utility_p=utility_p,
            utility_w=utility_w,
            utility_l=utility_l,
            utility_cost=utility_cost,
            utility_context_adj=utility_context_adj,
            u_min=utility_u_min,
            u_pass=utility_pass,
            decision_rule_version=decision_rule_version,
            trade_link_key=str(entered_trade_link_key),
            order_submit_latency_ms=int(order_submit_latency_ms),
        )
    )
    _record_entry_back_stage("entered_decision_log_append", sub_stage_started_at)
    scored_reasons = self.runtime.build_scored_reasons(
        reasons,
        target_total=int(final_entry_score),
        ai_adj=int(entry_adj),
    )
    scored_reasons = [
        f"[ENTRY_STAGE:{entry_stage}] p={entry_stage_detail.get('p', {})}",
        *list(scored_reasons),
    ]
    exit_profile_at_entry = resolve_exit_profile(
        entry_setup_id=str(setup_id or ""),
        fallback_profile="neutral",
    )
    sub_stage_started_at = time.perf_counter()
    self.trade_logger.log_entry(
        ticket,
        symbol,
        action,
        price,
        ", ".join(scored_reasons),
        entry_score=final_entry_score,
        contra_score=contra_score,
        lot=lot,
        indicators=entry_indicators,
        regime=regime,
        entry_stage=entry_stage,
        entry_setup_id=setup_id,
        exit_profile=exit_profile_at_entry,
        prediction_bundle=json.dumps(prediction_bundle, ensure_ascii=False, separators=(",", ":")),
        entry_quality=entry_quality,
        entry_model_confidence=model_conf,
        regime_at_entry=regime_at_entry,
        entry_wait_state=str(
            self._wait_engine.build_entry_wait_state_from_row(
                symbol=str(symbol),
                row=_wait_input_row(
                    action_value=str(action),
                    blocked_by_value="",
                ),
            ).state
        ),
        entry_h1_context_score=entry_h1_context_score,
        entry_m1_trigger_score=entry_m1_trigger_score,
        entry_h1_gate_pass=1 if gate_ok else 0,
        entry_h1_gate_reason=gate_reason,
        entry_topdown_gate_pass=1 if topdown_ok else 0,
        entry_topdown_gate_reason=topdown_reason,
        entry_topdown_align_count=int(topdown_stat.get("align", 0)),
        entry_topdown_conflict_count=int(topdown_stat.get("conflict", 0)),
        entry_topdown_seen_count=int(topdown_stat.get("seen", 0)),
        entry_session_name=entry_session_name,
        entry_weekday=entry_weekday,
        entry_session_threshold_mult=entry_session_threshold_mult,
        entry_atr_ratio=entry_atr_ratio,
        entry_atr_threshold_mult=entry_atr_threshold_mult,
        entry_request_price=float(slip.entry_request_price),
        entry_fill_price=float(slip.entry_fill_price),
        entry_slippage_points=float(slip.entry_slippage_points),
        decision_row_key=str((entered_row or {}).get("decision_row_key", "") or ""),
        runtime_snapshot_key=str((entered_row or {}).get("runtime_snapshot_key", "") or ""),
        trade_link_key=str((entered_row or {}).get("trade_link_key", "") or entered_trade_link_key),
        replay_row_key=str((entered_row or {}).get("replay_row_key", "") or ""),
        signal_age_sec=float((entered_row or {}).get("signal_age_sec", 0.0) or 0.0),
        bar_age_sec=float((entered_row or {}).get("bar_age_sec", 0.0) or 0.0),
        decision_latency_ms=int((entered_row or {}).get("decision_latency_ms", 0) or 0),
        order_submit_latency_ms=int((entered_row or {}).get("order_submit_latency_ms", order_submit_latency_ms) or 0),
        missing_feature_count=int((entered_row or {}).get("missing_feature_count", 0) or 0),
        data_completeness_ratio=float((entered_row or {}).get("data_completeness_ratio", 0.0) or 0.0),
        used_fallback_count=int((entered_row or {}).get("used_fallback_count", 0) or 0),
        compatibility_mode=str((entered_row or {}).get("compatibility_mode", "") or ""),
        detail_blob_bytes=int((entered_row or {}).get("detail_blob_bytes", 0) or 0),
        snapshot_payload_bytes=int((entered_row or {}).get("snapshot_payload_bytes", 0) or 0),
        row_payload_bytes=int((entered_row or {}).get("row_payload_bytes", 0) or 0),
        **_build_trade_logger_micro_payload_from_decision_row(entered_row),
    )
    _record_entry_back_stage("trade_logger_log_entry", sub_stage_started_at)
    _record_entry_back_stage("order_submit_and_log", entry_back_stage_started_at)
    _store_entry_back_profile("entered")
    msg = self.runtime.format_entry_message(
        symbol,
        action,
        final_entry_score,
        price,
        lot,
        scored_reasons[:3],
        pos_count + 1,
        Config.MAX_POSITIONS,
        row=current_runtime_row,
    )
    self.runtime.notify(msg)
    _safe_console_print(msg)








