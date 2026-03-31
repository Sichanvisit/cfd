# 파일 설명: EntryService의 try_open_entry 본문을 분리한 모듈입니다.
"""try_open_entry helper extracted from EntryService."""

from __future__ import annotations

import json
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
from backend.services.exit_profile_router import resolve_exit_profile
from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
)
from backend.services.p7_guarded_size_overlay import (
    P7_GUARDED_SIZE_OVERLAY_CONTRACT_V1,
    resolve_p7_guarded_size_overlay_v1,
)
from backend.services.storage_compaction import resolve_trade_link_key
from ml.semantic_v1.promotion_guard import SemanticPromotionGuard
from ml.semantic_v1.runtime_adapter import (
    SemanticShadowRuntime,
    build_semantic_shadow_feature_row,
    resolve_semantic_shadow_compare_label,
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
    guard_active = bool(
        probe_surface
        and probe_not_ready_surface
        and blocked_by_u in {"", "probe_promotion_gate"}
        and symbol_u in {"XAUUSD", "BTCUSD", "NAS100"}
    )
    failure_code = "probe_promotion_gate" if guard_active else ""
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
        "allows_open": bool(not failure_code),
        "failure_code": str(failure_code or ""),
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
    shadow_entry_context_v1: dict | None = None,
) -> tuple[str, str]:
    observe_confirm = dict(shadow_observe_confirm or {})
    entry_context = dict(shadow_entry_context_v1 or {})
    metadata = (
        dict(entry_context.get("metadata", {}) or {})
        if isinstance(entry_context, dict)
        else {}
    )
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
) -> tuple[bool, str]:
    symbol_u = str(symbol or "").upper().strip()
    core_reason_u = str(core_reason or "").lower().strip()
    setup_reason_u = str(setup_reason or "").lower().strip()
    box_state_u = str(box_state or "").upper().strip()
    bb_state_u = str(bb_state or "").upper().strip()
    preflight_u = str(preflight_allowed_action or "").upper().strip()
    compatibility_mode_u = str(compatibility_mode or "").strip().lower()

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


def try_open_entry(self, symbol, tick, df_all, result, my_positions, pos_count, scorer, buy_s, sell_s, entry_threshold):
    regime = result.get("regime", {}) if isinstance(result, dict) else {}
    spread_now = abs(float(getattr(tick, "ask", 0.0) or 0.0) - float(getattr(tick, "bid", 0.0) or 0.0))
    cooldown_remaining = max(
        0,
        int(float(Config.ENTRY_COOLDOWN) - (time.time() - float(self.runtime.last_entry_time.get(symbol, 0.0)))),
    )
    action = None
    action_none_reason = ""
    observe_reason = ""
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
    entry_enter_value = 0.0
    entry_wait_value = 0.0
    entry_wait_energy_usage_trace_v1 = {}
    entry_wait_decision_energy_usage_trace_v1 = {}
    prediction_bundle = {"entry": {}, "wait": {}, "exit": {}, "reverse": {}, "metadata": {}}
    shadow_entry_context_v1 = {}
    shadow_position_snapshot_v2 = {}
    shadow_position_vector = {}
    shadow_response_raw_snapshot_v1 = {}
    shadow_response_vector = {}
    shadow_response_vector_v2 = {}
    shadow_state_raw_snapshot_v1 = {}
    shadow_state_vector = {}
    shadow_state_vector_v2 = {}
    shadow_evidence_vector_v1 = {}
    shadow_belief_state_v1 = {}
    shadow_barrier_state_v1 = {}
    shadow_forecast_features_v1 = {}
    shadow_transition_forecast_v1 = {}
    shadow_trade_management_forecast_v1 = {}
    shadow_energy_snapshot = {}
    shadow_observe_confirm = {}
    core_dec = {}
    entry_probe_plan_v1 = {}
    semantic_shadow_prediction_v1 = None
    semantic_live_guard_v1 = None
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

    def _json_field(payload: dict) -> str:
        if not isinstance(payload, dict) or not payload:
            return ""
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def _current_runtime_snapshot_row() -> dict:
        rows = getattr(self.runtime, "latest_signal_by_symbol", None)
        if not isinstance(rows, dict):
            return {}
        candidate = rows.get(symbol, {})
        if not isinstance(candidate, dict):
            return {}
        return dict(candidate)

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
        return {
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
        nonlocal semantic_shadow_prediction_v1
        nonlocal semantic_live_guard_v1
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
        runtime_snapshot_row = _current_runtime_snapshot_row()
        if semantic_shadow_prediction_v1 is None:
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
                    setup_id=str(setup_id if setup_id_v is None else setup_id_v or ""),
                    setup_side=str(setup_side if setup_side_v is None else setup_side_v or ""),
                    entry_stage=str(entry_stage or ""),
                    preflight_regime=str(preflight_regime or ""),
                    preflight_liquidity=str(preflight_liquidity or ""),
                )
                try:
                    semantic_shadow_prediction_v1 = semantic_runtime.predict_shadow(
                        semantic_feature_row,
                        action_hint=str(action or shadow_observe_confirm.get("action", "") or ""),
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
                        action_hint=str(action or ""),
                    )
            else:
                semantic_shadow_prediction_v1 = SemanticShadowRuntime.unavailable_prediction(
                    reason="semantic_runtime_unavailable",
                    action_hint=str(action or ""),
                )

        if semantic_live_guard_v1 is None:
            semantic_live_guard = getattr(self.runtime, "semantic_promotion_guard", None)
            if semantic_live_guard is None:
                semantic_live_guard = SemanticPromotionGuard()
            current_threshold = max(1, int(round(float(effective_threshold or 1) or 1.0)))
            try:
                semantic_live_guard_v1 = semantic_live_guard.evaluate_entry_rollout(
                    symbol=str(symbol),
                    baseline_action=str(action),
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
        wait_metadata = dict(wait_state.metadata or {})
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
            baseline_action=str(action or ""),
            blocked_by=str(blocked_by or ""),
        )
        observe_confirm_runtime_payload = _build_runtime_observe_confirm_dual_write(
            shadow_observe_confirm=shadow_observe_confirm,
        )
        return {
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
            "prediction_bundle": json.dumps(prediction_bundle, ensure_ascii=False, separators=(",", ":"))
            if any(bool(prediction_bundle.get(k)) for k in ("entry", "wait", "exit", "reverse", "metadata"))
            else "",
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
            "position_snapshot_v2": _json_field(shadow_position_snapshot_v2),
            "response_raw_snapshot_v1": _json_field(shadow_response_raw_snapshot_v1),
            "response_vector_v2": _json_field(shadow_response_vector_v2),
            "state_raw_snapshot_v1": _json_field(shadow_state_raw_snapshot_v1),
            "state_vector_v2": _json_field(shadow_state_vector_v2),
            "evidence_vector_v1": _json_field(shadow_evidence_vector_v1),
            "belief_state_v1": _json_field(shadow_belief_state_v1),
            "barrier_state_v1": _json_field(shadow_barrier_state_v1),
            "forecast_features_v1": _json_field(shadow_forecast_features_v1),
            "transition_forecast_v1": _json_field(shadow_transition_forecast_v1),
            "trade_management_forecast_v1": _json_field(shadow_trade_management_forecast_v1),
            "forecast_gap_metrics_v1": _json_field({
                "transition_side_separation": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("side_separation", 0.0)) or 0.0)),
                "transition_confirm_fake_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("confirm_fake_gap", 0.0)) or 0.0)),
                "transition_reversal_continuation_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("reversal_continuation_gap", 0.0)) or 0.0)),
                "management_continue_fail_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("continue_fail_gap", 0.0)) or 0.0)),
                "management_recover_reentry_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("recover_reentry_gap", 0.0)) or 0.0)),
            }),
            "transition_side_separation": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("side_separation", 0.0)) or 0.0)),
            "transition_confirm_fake_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("confirm_fake_gap", 0.0)) or 0.0)),
            "transition_reversal_continuation_gap": float((((shadow_transition_forecast_v1.get("metadata", {}) or {}).get("reversal_continuation_gap", 0.0)) or 0.0)),
            "management_continue_fail_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("continue_fail_gap", 0.0)) or 0.0)),
            "management_recover_reentry_gap": float((((shadow_trade_management_forecast_v1.get("metadata", {}) or {}).get("recover_reentry_gap", 0.0)) or 0.0)),
            "observe_confirm_v2": _json_field(observe_confirm_runtime_payload.get("observe_confirm_v2", {})),
            "observe_confirm_v1": _json_field(observe_confirm_runtime_payload.get("observe_confirm_v1", {})),
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
        }

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
            wait_metadata = dict(wait_state.metadata or {})
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
        _mark_skip("max_positions_reached", pos_count=int(pos_count), max_positions=max_positions_for_symbol)
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
        _mark_skip("entry_cooldown", cooldown_sec_remaining=max(0, int(Config.ENTRY_COOLDOWN - (time.time() - self.runtime.last_entry_time.get(symbol, 0)))))
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

    try:
        shadow_bundle = self._context_classifier.build_entry_context(
            symbol=symbol,
            tick=tick,
            df_all=df_all,
            scorer=scorer,
            result=result,
            buy_s=buy_s,
            sell_s=sell_s,
        )
        shadow_context = shadow_bundle.get("context")
        shadow_entry_context_v1 = shadow_context.to_dict() if shadow_context is not None else {}
        shadow_position_snapshot = shadow_bundle.get("position_snapshot")
        shadow_position = shadow_bundle.get("position_vector")
        shadow_response_raw = shadow_bundle.get("response_raw_snapshot")
        shadow_response = shadow_bundle.get("response_vector")
        shadow_response_v2 = shadow_bundle.get("response_vector_v2")
        shadow_state_raw = shadow_bundle.get("state_raw_snapshot")
        shadow_state = shadow_bundle.get("state_vector")
        shadow_state_v2 = shadow_bundle.get("state_vector_v2")
        shadow_evidence = shadow_bundle.get("evidence_vector")
        shadow_belief = shadow_bundle.get("belief_state")
        shadow_barrier = shadow_bundle.get("barrier_state")
        shadow_forecast_features = shadow_bundle.get("forecast_features")
        shadow_transition_forecast = shadow_bundle.get("transition_forecast")
        shadow_trade_management_forecast = shadow_bundle.get("trade_management_forecast")
        shadow_energy = shadow_bundle.get("energy_snapshot")
        shadow_observe = shadow_bundle.get("observe_confirm")
        shadow_position_snapshot_v2 = shadow_position_snapshot.to_dict() if shadow_position_snapshot is not None else {}
        shadow_position_vector = shadow_position.to_dict() if shadow_position is not None else {}
        shadow_response_raw_snapshot_v1 = shadow_response_raw.to_dict() if shadow_response_raw is not None else {}
        shadow_response_vector = shadow_response.to_dict() if shadow_response is not None else {}
        shadow_response_vector_v2 = shadow_response_v2.to_dict() if shadow_response_v2 is not None else {}
        shadow_state_raw_snapshot_v1 = shadow_state_raw.to_dict() if shadow_state_raw is not None else {}
        shadow_state_vector = shadow_state.to_dict() if shadow_state is not None else {}
        shadow_state_vector_v2 = shadow_state_v2.to_dict() if shadow_state_v2 is not None else {}
        shadow_evidence_vector_v1 = shadow_evidence.to_dict() if shadow_evidence is not None else {}
        shadow_belief_state_v1 = shadow_belief.to_dict() if shadow_belief is not None else {}
        shadow_barrier_state_v1 = shadow_barrier.to_dict() if shadow_barrier is not None else {}
        shadow_forecast_features_v1 = shadow_forecast_features.to_dict() if shadow_forecast_features is not None else {}
        shadow_transition_forecast_v1 = shadow_transition_forecast.to_dict() if shadow_transition_forecast is not None else {}
        shadow_trade_management_forecast_v1 = shadow_trade_management_forecast.to_dict() if shadow_trade_management_forecast is not None else {}
        shadow_energy_snapshot = shadow_energy.to_dict() if shadow_energy is not None else {}
        shadow_observe_confirm = shadow_observe.to_dict() if shadow_observe is not None else {}
        try:
            self._store_runtime_snapshot(
                runtime=self.runtime,
                symbol=str(symbol),
                key="entry_shadow_compare_v1",
                payload={
                    "context": dict(shadow_entry_context_v1),
                    "position_snapshot_v2": dict(shadow_position_snapshot_v2),
                    "response_raw_snapshot_v1": dict(shadow_response_raw_snapshot_v1),
                    "response_vector_v2": dict(shadow_response_vector_v2),
                    "state_raw_snapshot_v1": dict(shadow_state_raw_snapshot_v1),
                    "state_vector_v2": dict(shadow_state_vector_v2),
                    "evidence_vector_v1": dict(shadow_evidence_vector_v1),
                    "belief_state_v1": dict(shadow_belief_state_v1),
                    "barrier_state_v1": dict(shadow_barrier_state_v1),
                    "forecast_features_v1": dict(shadow_forecast_features_v1),
                    "transition_forecast_v1": dict(shadow_transition_forecast_v1),
                    "trade_management_forecast_v1": dict(shadow_trade_management_forecast_v1),
                    "position": dict(shadow_position_vector),
                    "response": dict(shadow_response_vector),
                    "state": dict(shadow_state_vector),
                    "energy": dict(shadow_energy_snapshot),
                    "observe_confirm": dict(shadow_observe_confirm),
                },
            )
        except Exception:
            pass
    except Exception:
        shadow_entry_context_v1 = {}
        shadow_position_snapshot_v2 = {}
        shadow_position_vector = {}
        shadow_response_raw_snapshot_v1 = {}
        shadow_response_vector = {}
        shadow_response_vector_v2 = {}
        shadow_state_raw_snapshot_v1 = {}
        shadow_state_vector = {}
        shadow_state_vector_v2 = {}
        shadow_evidence_vector_v1 = {}
        shadow_belief_state_v1 = {}
        shadow_barrier_state_v1 = {}
        shadow_forecast_features_v1 = {}
        shadow_transition_forecast_v1 = {}
        shadow_trade_management_forecast_v1 = {}
        shadow_energy_snapshot = {}
        shadow_observe_confirm = {}

    management_profile_id, invalidation_id = _resolve_entry_handoff_ids(
        shadow_observe_confirm=shadow_observe_confirm,
        shadow_entry_context_v1=shadow_entry_context_v1,
    )

    action = None
    score = 0
    reasons = []
    has_sell = any(int(p.type) == int(ORDER_TYPE_SELL) for p in my_positions)
    has_buy = any(int(p.type) == int(ORDER_TYPE_BUY) for p in my_positions)
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
    )
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
    observe_reason = str(
        core_dec.get("observe_reason", "")
        or shadow_observe_confirm.get("reason", "")
        or ""
    )
    action_none_reason = str(core_dec.get("action_none_reason", "") or "")
    core_blocked_reason = str(core_dec.get("blocked_by", "") or "")
    symbol_u = str(symbol or "").upper().strip()
    if not action:
        if semantic_shadow_prediction_v1 is None:
            try:
                _decision_payload(
                    considered=1,
                    raw_score=float(max(buy_s, sell_s)),
                    contra_score=float(min(buy_s, sell_s)),
                    effective_threshold=float(entry_threshold),
                    entry_stage=str(entry_stage or ""),
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
        if bridge_action in {"BUY", "SELL"}:
            action = str(bridge_action)
            core_pass = 1
            core_reason = str(bridge_reason or "semantic_probe_bridge")
            core_allowed_action = str(action)
            action_none_reason = ""
            core_blocked_reason = ""
        blocked_reason = str(core_blocked_reason or "")
    if not action:
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
    entry_blocked_guard_v1 = _build_entry_blocked_guard_v1(
        action=str(action),
        observe_reason=str(observe_reason or ""),
        blocked_by=str(core_blocked_reason or ""),
        action_none_reason=str(action_none_reason or ""),
    )
    if bool(entry_blocked_guard_v1.get("guard_active")) and not bool(entry_blocked_guard_v1.get("allows_open")):
        fail_reason = str(entry_blocked_guard_v1.get("failure_code", "") or "entry_blocked_guard")
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
    observe_confirm_runtime_metadata = _build_runtime_observe_confirm_dual_write(
        shadow_observe_confirm=shadow_observe_confirm,
    )
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
            "position_snapshot_v2": dict(shadow_position_snapshot_v2 or {}),
            "response_raw_snapshot_v1": dict(shadow_response_raw_snapshot_v1 or {}),
            "response_vector_v2": dict(shadow_response_vector_v2 or {}),
            "state_raw_snapshot_v1": dict(shadow_state_raw_snapshot_v1 or {}),
            "state_vector_v2": dict(shadow_state_vector_v2 or {}),
            "evidence_vector_v1": dict(shadow_evidence_vector_v1 or {}),
            "belief_state_v1": dict(shadow_belief_state_v1 or {}),
            "barrier_state_v1": dict(shadow_barrier_state_v1 or {}),
            "forecast_features_v1": dict(shadow_forecast_features_v1 or {}),
            "transition_forecast_v1": dict(shadow_transition_forecast_v1 or {}),
            "trade_management_forecast_v1": dict(shadow_trade_management_forecast_v1 or {}),
            "observe_confirm_v1": dict(observe_confirm_runtime_metadata.get("observe_confirm_v1", {}) or {}),
            "observe_confirm_v2": dict(observe_confirm_runtime_metadata.get("observe_confirm_v2", {}) or {}),
            "prs_canonical_observe_confirm_field": str(
                observe_confirm_runtime_metadata.get("prs_canonical_observe_confirm_field", "") or "observe_confirm_v2"
            ),
            "prs_compatibility_observe_confirm_field": str(
                observe_confirm_runtime_metadata.get("prs_compatibility_observe_confirm_field", "") or "observe_confirm_v1"
            ),
            "prs_log_contract_v2": dict(observe_confirm_runtime_metadata.get("prs_log_contract_v2", {}) or {}),
            "observe_confirm_input_contract_v2": dict(
                observe_confirm_runtime_metadata.get("observe_confirm_input_contract_v2", {}) or {}
            ),
            "observe_confirm_migration_dual_write_v1": dict(
                observe_confirm_runtime_metadata.get("observe_confirm_migration_dual_write_v1", {}) or {}
            ),
            "observe_confirm_output_contract_v2": dict(
                observe_confirm_runtime_metadata.get("observe_confirm_output_contract_v2", {}) or {}
            ),
            "observe_confirm_scope_contract_v1": dict(
                observe_confirm_runtime_metadata.get("observe_confirm_scope_contract_v1", {}) or {}
            ),
            "consumer_input_contract_v1": dict(
                observe_confirm_runtime_metadata.get("consumer_input_contract_v1", {}) or {}
            ),
        },
    )
    setup_candidate = self._setup_detector.detect_entry_setup(
        context=setup_context,
        action=str(action),
        h1_gap=float(entry_h1_context_score - entry_h1_context_opposite),
        m1_gap=float(entry_m1_trigger_score - entry_m1_trigger_opposite),
        score_gap=float(score - contra_score),
    )
    setup_id = str(setup_candidate.setup_id or "")
    setup_side = str(setup_candidate.side or str(action or ""))
    setup_status = str(setup_candidate.status or "pending")
    setup_trigger_state = str(setup_candidate.trigger_state or "UNKNOWN")
    setup_score = float(setup_candidate.score or 0.0)
    setup_entry_quality = float(setup_candidate.entry_quality or 0.0)
    setup_reason = str((setup_candidate.metadata or {}).get("reason", "") or "")
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
        setup_reason_u = str(setup_reason or "").lower().strip()
        compatibility_mode_u = str(_current_runtime_snapshot_row().get("compatibility_mode", "") or "")
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
    probe_promotion_guard_v1 = _build_probe_promotion_guard_v1(
        symbol=str(symbol),
        action=str(action),
        observe_reason=str(observe_reason or ""),
        blocked_by=str(core_blocked_reason or ""),
        action_none_reason=str(action_none_reason or ""),
        entry_probe_plan_v1=entry_probe_plan_v1,
        consumer_check_state_v1=consumer_check_state_v1,
        runtime_snapshot_row=_current_runtime_snapshot_row(),
    )
    if bool(probe_promotion_guard_v1.get("guard_active")) and not bool(probe_promotion_guard_v1.get("allows_open")):
        fail_reason = str(probe_promotion_guard_v1.get("failure_code", "") or "probe_promotion_gate")
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
            "blocked_by": "",
            "p7_guarded_size_overlay_v1": dict(p7_guarded_size_overlay_v1 or {}),
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

    order_submit_started_at = time.time()
    ticket = self.runtime.execute_order(symbol, action, lot)
    order_submit_latency_ms = int(max(0.0, round((time.time() - order_submit_started_at) * 1000.0)))
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
    )
    msg = self.runtime.format_entry_message(
        symbol,
        action,
        final_entry_score,
        price,
        lot,
        scored_reasons[:3],
        pos_count + 1,
        Config.MAX_POSITIONS,
    )
    self.runtime.notify(msg)
    print(f"\n{msg}")








