"""Entry-domain helper engines extracted from EntryService."""

from __future__ import annotations

import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.core.config import Config
from backend.services.consumer_contract import (
    CONSUMER_FREEZE_HANDOFF_V1,
    CONSUMER_INPUT_CONTRACT_V1,
    CONSUMER_LAYER_MODE_INTEGRATION_V1,
    CONSUMER_LOGGING_CONTRACT_V1,
    CONSUMER_MIGRATION_FREEZE_V1,
    CONSUMER_SCOPE_CONTRACT_V1,
    CONSUMER_TEST_CONTRACT_V1,
    ENTRY_GUARD_CONTRACT_V1,
    ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
    EXIT_HANDOFF_CONTRACT_V1,
    RE_ENTRY_CONTRACT_V1,
    SETUP_MAPPING_CONTRACT_V1,
    SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1,
    build_consumer_migration_guard_metadata,
    resolve_consumer_guard_result,
    resolve_consumer_observe_confirm_resolution,
)
from backend.services.context_classifier import (
    FORECAST_CALIBRATION_CONTRACT_V1,
)
from backend.services.energy_contract import (
    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
    ENERGY_MIGRATION_DUAL_WRITE_V1,
    ENERGY_SCOPE_CONTRACT_V1,
    attach_energy_consumer_usage_trace,
    build_energy_helper_v2,
    resolve_entry_service_energy_usage,
    resolve_energy_migration_bridge_state,
)
from backend.services.entry_decision_rollover import execute_entry_decision_rollover
from backend.services.layer_mode_contract import (
    LAYER_MODE_APPLICATION_CONTRACT_V1,
    LAYER_MODE_DEFAULT_POLICY_V1,
    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    LAYER_MODE_LAYER_INVENTORY_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_MODE_CONTRACT_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_SCOPE_CONTRACT_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
    build_layer_mode_application_metadata,
    build_layer_mode_effective_metadata,
    build_layer_mode_identity_guard_metadata,
    build_layer_mode_influence_metadata,
    build_layer_mode_logging_replay_metadata,
    build_layer_mode_policy_overlay_metadata,
)
from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
)
from backend.services.outcome_labeler_contract import OUTCOME_LABELER_SCOPE_CONTRACT_V1
from backend.services.p0_decision_trace import (
    P0_DECISION_TRACE_CONTRACT_V1,
    build_p0_decision_trace_v1,
)
from backend.services.runtime_alignment_contract import RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
from backend.services.storage_compaction import (
    ENTRY_DECISION_DETAIL_ONLY_COLUMNS,
    ENTRY_DECISION_DETAIL_SCHEMA_VERSION,
    build_entry_decision_detail_record,
    build_entry_decision_hot_payload,
    is_generic_runtime_signal_row_key,
    json_payload_size_bytes,
    rotate_entry_decision_detail_if_needed,
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
    resolve_runtime_signal_row_key,
    summarize_trace_quality,
)

logger = logging.getLogger(__name__)


ENTRY_DECISION_FULL_COLUMNS = [
    "time", "signal_timeframe", "signal_bar_ts", "symbol", "action", "considered", "outcome",
    "observe_action", "observe_side", "observe_reason", "blocked_by",
    "entry_score_raw", "contra_score_raw",
    "decision_row_key", "runtime_snapshot_key", "trade_link_key", "replay_row_key",
    "signal_age_sec", "bar_age_sec", "decision_latency_ms", "order_submit_latency_ms",
    "missing_feature_count", "data_completeness_ratio", "used_fallback_count", "compatibility_mode",
    "detail_blob_bytes", "snapshot_payload_bytes", "row_payload_bytes",
    "effective_entry_threshold", "base_entry_threshold",
    "entry_stage", "ai_probability", "size_multiplier", "utility_u", "utility_p",
    "utility_p_raw", "utility_p_calibrated", "utility_stats_ready", "utility_wins_n", "utility_losses_n",
    "utility_w", "utility_l", "utility_cost", "utility_context_adj", "u_min", "u_pass",
    "decision_rule_version", "entry_decision_mode",
    "core_reason", "action_none_reason", "core_pass", "core_allowed_action",
    "core_resolved_shadow_action", "core_intended_direction", "core_archetype_implied_action", "core_intended_action_source",
    "observe_probe_override_pending",
    "box_state", "bb_state",
    "core_buy_raw", "core_sell_raw", "core_best_raw", "core_min_raw", "core_margin_raw", "core_tie_band_raw",
    "setup_id", "setup_side", "setup_status", "setup_trigger_state", "setup_score", "setup_entry_quality", "setup_reason",
    "wait_score", "wait_conflict", "wait_noise", "wait_penalty",
    "entry_wait_state", "entry_wait_hard", "entry_wait_reason",
    "entry_wait_selected", "entry_wait_decision", "entry_enter_value", "entry_wait_value",
    "entry_wait_context_v1", "entry_wait_bias_bundle_v1", "entry_wait_state_policy_input_v1",
    "entry_wait_energy_usage_trace_v1", "entry_wait_decision_energy_usage_trace_v1",
    "forecast_assist_v1", "entry_default_side_gate_v1", "entry_probe_plan_v1", "edge_pair_law_v1", "probe_candidate_v1",
    "probe_candidate_active", "probe_direction", "probe_scene_id", "probe_candidate_support", "probe_pair_gap",
    "probe_plan_active", "probe_plan_ready", "probe_plan_reason", "probe_plan_scene", "probe_entry_style",
    "quick_trace_state", "quick_trace_reason",
    "r0_non_action_family", "r0_semantic_runtime_state", "r0_row_interpretation_v1",
    "p0_identity_owner", "p0_execution_gate_owner", "p0_decision_owner_relation",
    "p0_coverage_state", "p0_coverage_source", "p0_decision_trace_v1", "p0_decision_trace_contract_v1",
    "p7_guarded_size_overlay_v1", "p7_size_overlay_enabled", "p7_size_overlay_mode",
    "p7_size_overlay_matched", "p7_size_overlay_target_multiplier", "p7_size_overlay_effective_multiplier",
    "p7_size_overlay_apply_allowed", "p7_size_overlay_applied", "p7_size_overlay_gate_reason",
    "p7_size_overlay_source",
    "entry_decision_context_v1", "entry_decision_result_v1",
    "prediction_bundle",
    "prs_contract_version", "prs_canonical_position_field", "prs_canonical_position_effective_field", "prs_canonical_response_field", "prs_canonical_response_effective_field", "prs_canonical_state_field", "prs_canonical_state_effective_field", "prs_canonical_evidence_field", "prs_canonical_evidence_effective_field", "prs_canonical_belief_field", "prs_canonical_belief_effective_field", "prs_canonical_barrier_field", "prs_canonical_barrier_effective_field", "prs_canonical_forecast_features_field", "prs_canonical_transition_forecast_field", "prs_canonical_trade_management_forecast_field", "prs_canonical_forecast_gap_metrics_field", "prs_canonical_forecast_effective_field", "prs_canonical_energy_field", "prs_canonical_observe_confirm_field",
    "prs_compatibility_observe_confirm_field",
    "energy_migration_contract_field",
    "energy_scope_contract_field",
    "runtime_alignment_scope_contract_field",
    "energy_compatibility_runtime_field",
    "energy_logging_replay_contract_field",
    "energy_snapshot",
    "energy_helper_v2",
    "energy_logging_replay_contract_v1",
    "energy_migration_dual_write_v1",
    "energy_migration_guard_v1",
    "energy_scope_contract_v1",
    "runtime_alignment_scope_contract_v1",
    "observe_confirm_input_contract_v2",
    "observe_confirm_migration_dual_write_v1",
    "observe_confirm_output_contract_v2",
    "observe_confirm_scope_contract_v1",
    "consumer_input_contract_v1",
    "consumer_migration_freeze_v1",
    "consumer_migration_guard_v1",
    "consumer_logging_contract_v1",
    "consumer_test_contract_v1",
    "consumer_freeze_handoff_v1",
    "layer_mode_contract_v1",
    "layer_mode_layer_inventory_v1",
    "layer_mode_default_policy_v1",
    "layer_mode_dual_write_contract_v1",
    "layer_mode_influence_semantics_v1",
    "layer_mode_application_contract_v1",
    "layer_mode_identity_guard_contract_v1",
    "layer_mode_policy_overlay_output_contract_v1",
    "layer_mode_logging_replay_contract_v1",
    "layer_mode_test_contract_v1",
    "layer_mode_freeze_handoff_v1",
    "setup_detector_responsibility_contract_v1",
    "setup_mapping_contract_v1",
    "entry_guard_contract_v1",
    "entry_service_responsibility_contract_v1",
    "exit_handoff_contract_v1",
    "re_entry_contract_v1",
    "consumer_scope_contract_v1",
    "consumer_layer_mode_integration_v1",
    "consumer_input_observe_confirm_field",
    "consumer_input_contract_version",
    "consumer_migration_contract_version",
    "consumer_used_compatibility_fallback_v1",
    "consumer_policy_input_field",
    "consumer_policy_contract_version",
    "consumer_policy_identity_preserved",
    "consumer_archetype_id",
    "consumer_invalidation_id",
    "consumer_management_profile_id",
    "consumer_setup_id",
    "consumer_guard_result",
    "consumer_effective_action",
    "consumer_block_reason",
    "consumer_block_kind",
    "consumer_block_source_layer",
    "consumer_block_is_execution",
    "consumer_block_is_semantic_non_action",
    "consumer_check_candidate",
    "consumer_check_display_ready",
    "consumer_check_entry_ready",
    "consumer_check_side",
    "consumer_check_stage",
    "consumer_check_reason",
    "consumer_check_display_strength_level",
    "consumer_check_state_v1",
    "consumer_handoff_contract_version",
    "layer_mode_scope_contract_v1",
    "layer_mode_effective_trace_v1",
    "layer_mode_influence_trace_v1",
    "layer_mode_application_trace_v1",
    "layer_mode_identity_guard_trace_v1",
    "layer_mode_policy_v1",
    "layer_mode_logging_replay_v1",
    "forecast_calibration_contract_v1",
    "outcome_labeler_scope_contract_v1",
    "position_snapshot_v2", "position_snapshot_effective_v1", "response_raw_snapshot_v1", "response_vector_v2", "response_vector_effective_v1", "state_raw_snapshot_v1", "state_vector_v2", "state_vector_effective_v1", "evidence_vector_v1", "evidence_vector_effective_v1", "belief_state_v1", "belief_state_effective_v1", "barrier_state_v1", "barrier_state_effective_v1", "forecast_features_v1", "transition_forecast_v1", "trade_management_forecast_v1", "forecast_gap_metrics_v1", "forecast_effective_policy_v1", "transition_side_separation", "transition_confirm_fake_gap", "transition_reversal_continuation_gap", "management_continue_fail_gap", "management_recover_reentry_gap", "observe_confirm_v1", "observe_confirm_v2",
    "shadow_state_v1", "shadow_action_v1", "shadow_reason_v1",
    "shadow_buy_force_v1", "shadow_sell_force_v1", "shadow_net_force_v1",
    "semantic_shadow_available", "semantic_shadow_model_version", "semantic_shadow_trace_quality",
    "semantic_shadow_timing_probability", "semantic_shadow_timing_threshold", "semantic_shadow_timing_decision",
    "semantic_shadow_entry_quality_probability", "semantic_shadow_entry_quality_threshold", "semantic_shadow_entry_quality_decision",
    "semantic_shadow_exit_management_probability", "semantic_shadow_exit_management_threshold", "semantic_shadow_exit_management_decision",
    "semantic_shadow_should_enter", "semantic_shadow_action_hint", "semantic_shadow_compare_label", "semantic_shadow_reason",
    "semantic_shadow_activation_state", "semantic_shadow_activation_reason",
    "semantic_live_rollout_mode", "semantic_live_alert", "semantic_live_fallback_reason",
    "semantic_live_symbol_allowed", "semantic_live_entry_stage_allowed",
    "semantic_live_threshold_before", "semantic_live_threshold_after", "semantic_live_threshold_adjustment",
    "semantic_live_threshold_applied", "semantic_live_threshold_state", "semantic_live_threshold_reason",
    "semantic_live_partial_weight", "semantic_live_partial_live_applied",
    "semantic_live_reason",
    "preflight_regime", "preflight_liquidity", "preflight_allowed_action", "preflight_approach_mode", "preflight_reason",
    "last_order_retcode", "last_order_comment", "order_block_remaining_sec",
]

ENTRY_DECISION_LOG_COLUMNS = [
    column
    for column in ENTRY_DECISION_FULL_COLUMNS
    if column not in ENTRY_DECISION_DETAIL_ONLY_COLUMNS
] + [
    "detail_schema_version",
    "detail_row_key",
]


class EntryGuardEngine:
    def __init__(self):
        self._last_entry_signature: dict[str, dict] = {}
        self._last_cluster_trace: dict[str, dict] = {}

    @staticmethod
    def _safe_dict(value) -> dict:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _is_edge_aligned(side: str, box_state: str, bb_state: str) -> tuple[bool, str]:
        box_u = str(box_state or "").upper()
        bb_u = str(bb_state or "").upper()
        if str(side or "").upper() == "BUY":
            aligned = ("LOWER" in box_u) or ("LOWER" in bb_u)
            return bool(aligned), ("LOWER" if aligned else "NONE")
        if str(side or "").upper() == "SELL":
            aligned = ("UPPER" in box_u) or ("UPPER" in bb_u)
            return bool(aligned), ("UPPER" if aligned else "NONE")
        return False, "NONE"

    @classmethod
    def build_cluster_semantic_signature(
        cls,
        payload: dict | None,
        *,
        action: str = "",
        setup_id: str = "",
        setup_reason: str = "",
    ) -> dict:
        row = cls._safe_dict(payload)
        observe = cls._safe_dict(row.get("observe_confirm_v2") or row.get("observe_confirm_v1"))
        observe_meta = cls._safe_dict(observe.get("metadata"))
        belief = cls._safe_dict(row.get("belief_state_v1"))
        barrier = cls._safe_dict(row.get("barrier_state_v1"))
        side = str(action or observe.get("action") or observe.get("side") or "").upper()
        box_state = str(row.get("box_state", "") or "")
        bb_state = str(row.get("bb_state", "") or "")
        edge_aligned, edge_bias = cls._is_edge_aligned(side=side, box_state=box_state, bb_state=bb_state)
        observe_state = str(observe.get("state", "") or "").upper()
        observe_reason = str(observe.get("reason", "") or "")
        observe_archetype = str(observe.get("archetype_id", "") or "")
        confidence = cls._safe_float(observe.get("confidence"), 0.0)
        transition_gap = cls._safe_float(row.get("transition_confirm_fake_gap"), 0.0)
        management_gap = cls._safe_float(row.get("management_continue_fail_gap"), 0.0)
        dominant_side = str(belief.get("dominant_side", "") or "").upper()
        dominant_mode = str(belief.get("dominant_mode", "") or "").lower()
        buy_persistence = cls._safe_float(belief.get("buy_persistence"), 0.0)
        sell_persistence = cls._safe_float(belief.get("sell_persistence"), 0.0)
        buy_streak = cls._safe_int(belief.get("buy_streak"), 0)
        sell_streak = cls._safe_int(belief.get("sell_streak"), 0)
        buy_barrier = cls._safe_float(barrier.get("buy_barrier"), 0.0)
        sell_barrier = cls._safe_float(barrier.get("sell_barrier"), 0.0)
        side_persistence = buy_persistence if side == "BUY" else sell_persistence
        side_streak = buy_streak if side == "BUY" else sell_streak
        side_barrier = buy_barrier if side == "BUY" else sell_barrier
        confirm_like = observe_state == "CONFIRM" or ("confirm" in observe_reason.lower())
        observe_side_match = side in {
            str(observe.get("action", "") or "").upper(),
            str(observe.get("side", "") or "").upper(),
        }

        semantic_score = 0.0
        semantic_score += 1.0 if edge_aligned else 0.0
        semantic_score += 1.0 if observe_side_match else 0.0
        semantic_score += 1.0 if confirm_like else 0.0
        semantic_score += 1.0 if confidence >= float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_CONFIDENCE", 0.58)) else 0.0
        semantic_score += 1.0 if transition_gap >= float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_CONFIRM_FAKE_GAP", 0.12)) else 0.0
        semantic_score += 1.0 if management_gap >= float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_CONTINUE_FAIL_GAP", 0.18)) else 0.0
        semantic_score += 1.0 if side_persistence >= float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_PERSISTENCE", 0.50)) else 0.0
        semantic_score += 1.0 if side_streak >= int(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_STREAK", 2)) else 0.0
        semantic_score += 1.0 if side_barrier <= float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MAX_SIDE_BARRIER", 0.22)) else 0.0
        semantic_score += 1.0 if dominant_side == side else 0.0

        return {
            "side": side,
            "setup_id": str(setup_id or row.get("setup_id") or ""),
            "setup_reason": str(setup_reason or row.get("setup_reason") or ""),
            "observe_state": observe_state,
            "observe_reason": observe_reason,
            "observe_archetype": observe_archetype,
            "scene_relief": (
                "xau_second_support_buy_probe"
                if cls._safe_int(observe_meta.get("xau_second_support_probe_relief"), 0)
                and str(side).upper() == "BUY"
                else ""
            ),
            "confidence": confidence,
            "box_state": box_state,
            "bb_state": bb_state,
            "edge_aligned": bool(edge_aligned),
            "edge_bias": edge_bias,
            "transition_confirm_fake_gap": transition_gap,
            "management_continue_fail_gap": management_gap,
            "dominant_side": dominant_side,
            "dominant_mode": dominant_mode,
            "side_persistence": side_persistence,
            "side_streak": side_streak,
            "side_barrier": side_barrier,
            "semantic_score": float(semantic_score),
        }

    @staticmethod
    def _same_thesis(previous: dict | None, current: dict | None) -> bool:
        prev = previous if isinstance(previous, dict) else {}
        curr = current if isinstance(current, dict) else {}
        if str(prev.get("side", "")).upper() != str(curr.get("side", "")).upper():
            return False
        prev_setup = str(prev.get("setup_id", "") or "")
        curr_setup = str(curr.get("setup_id", "") or "")
        if prev_setup and curr_setup and prev_setup == curr_setup:
            return True
        prev_archetype = str(prev.get("observe_archetype", "") or "")
        curr_archetype = str(curr.get("observe_archetype", "") or "")
        if prev_archetype and curr_archetype and prev_archetype == curr_archetype:
            return True
        prev_edge = str(prev.get("edge_bias", "") or "")
        curr_edge = str(curr.get("edge_bias", "") or "")
        prev_mode = str(prev.get("dominant_mode", "") or "")
        curr_mode = str(curr.get("dominant_mode", "") or "")
        return bool(prev_edge and curr_edge and prev_edge == curr_edge and prev_mode and curr_mode and prev_mode == curr_mode)

    @staticmethod
    def entry_price_for_action(action: str, tick) -> float:
        if str(action).upper() == "BUY":
            return float(getattr(tick, "ask", 0.0) or 0.0)
        return float(getattr(tick, "bid", 0.0) or 0.0)

    def pass_bb_entry_guard(self, symbol: str, action: str, tick, indicators: dict) -> tuple[bool, str]:
        if not bool(getattr(Config, "ENABLE_ENTRY_BB_GUARD", True)):
            return True, ""
        side = str(action or "").upper()
        if side not in {"BUY", "SELL"}:
            return True, ""
        mid = float(pd.to_numeric((indicators or {}).get("ind_bb_20_mid", 0.0), errors="coerce") or 0.0)
        up = float(pd.to_numeric((indicators or {}).get("ind_bb_20_up", 0.0), errors="coerce") or 0.0)
        dn = float(pd.to_numeric((indicators or {}).get("ind_bb_20_dn", 0.0), errors="coerce") or 0.0)
        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
        mid_tol = abs(
            float(
                Config.get_symbol_float(
                    symbol,
                    getattr(Config, "ENTRY_BB_MID_TOL_PCT_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_BB_MID_TOL_PCT", 0.00015)}),
                    float(getattr(Config, "ENTRY_BB_MID_TOL_PCT", 0.00015)),
                )
            )
        )
        near_band = abs(
            float(
                Config.get_symbol_float(
                    symbol,
                    getattr(Config, "ENTRY_BB_NEAR_BAND_PCT_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_BB_NEAR_BAND_PCT", 0.00020)}),
                    float(getattr(Config, "ENTRY_BB_NEAR_BAND_PCT", 0.00020)),
                )
            )
        )
        breakout_block_pct = abs(
            float(
                Config.get_symbol_float(
                    symbol,
                    getattr(Config, "ENTRY_BB_BREAKOUT_BLOCK_PCT_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_BB_BREAKOUT_BLOCK_PCT", 0.00005)}),
                    float(getattr(Config, "ENTRY_BB_BREAKOUT_BLOCK_PCT", 0.00005)),
                )
            )
        )
        if side == "BUY" and dn > 0 and bid <= (dn * (1.0 - breakout_block_pct)):
            return False, "bb_breakdown_block_buy"
        if side == "SELL" and up > 0 and ask >= (up * (1.0 + breakout_block_pct)):
            return False, "bb_breakout_block_sell"
        mid_bias_mode = str(getattr(Config, "ENTRY_BB_MID_BIAS_MODE", "trend") or "trend").strip().lower()
        if mid > 0 and mid_bias_mode in {"trend", "mean_reversion"}:
            if mid_bias_mode == "trend":
                if side == "BUY" and bid < (mid * (1.0 - mid_tol)):
                    return False, "bb_mid_not_supporting_buy"
                if side == "SELL" and ask > (mid * (1.0 + mid_tol)):
                    return False, "bb_mid_not_resisting_sell"
            else:
                if side == "BUY" and bid > (mid * (1.0 + mid_tol)):
                    return False, "bb_mid_not_discounted_buy"
                if side == "SELL" and ask < (mid * (1.0 - mid_tol)):
                    return False, "bb_mid_not_premium_sell"
        if side == "BUY" and up > 0 and ask >= (up * (1.0 - near_band)):
            return False, "bb_upper_too_close_buy"
        if side == "SELL" and dn > 0 and bid <= (dn * (1.0 + near_band)):
            return False, "bb_lower_too_close_sell"
        require_touch_default = bool(getattr(Config, "ENTRY_BB_REQUIRE_EDGE_TOUCH", False))
        require_touch_sym = float(
            Config.get_symbol_float(
                symbol,
                getattr(Config, "ENTRY_BB_REQUIRE_EDGE_TOUCH_BY_SYMBOL", {"DEFAULT": (1.0 if require_touch_default else 0.0)}),
                (1.0 if require_touch_default else 0.0),
            )
        )
        require_touch = bool(require_touch_sym >= 0.5)
        if require_touch:
            touch_pct = abs(
                float(
                    Config.get_symbol_float(
                        symbol,
                        getattr(Config, "ENTRY_BB_EDGE_TOUCH_PCT_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_BB_EDGE_TOUCH_PCT", near_band)}),
                        float(getattr(Config, "ENTRY_BB_EDGE_TOUCH_PCT", near_band)),
                    )
                )
            )
            if side == "BUY" and dn > 0 and ask > (dn * (1.0 + touch_pct)):
                return False, "bb_buy_without_lower_touch"
            if side == "SELL" and up > 0 and bid < (up * (1.0 - touch_pct)):
                return False, "bb_sell_without_upper_touch"
        return True, ""

    def pass_cluster_guard(
        self,
        symbol: str,
        action: str,
        tick,
        *,
        setup_id: str = "",
        setup_reason: str = "",
        preflight_allowed_action: str = "",
        semantic_signature: dict | None = None,
    ) -> tuple[bool, str]:
        key = str(symbol or "").upper()
        base_trace = {
            "contract_version": "entry_cluster_semantic_guard_v1",
            "symbol": key,
            "action": str(action or "").upper(),
            "setup_id": str(setup_id or ""),
            "setup_reason": str(setup_reason or ""),
            "semantic_relief_enabled": bool(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)),
        }
        if not bool(getattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)):
            self._last_cluster_trace[key] = {
                **base_trace,
                "decision": "allow_guard_disabled",
            }
            return True, ""
        now_s = time.time()
        info = self._last_entry_signature.get(key, {})
        side = str(action or "").upper()
        px = self.entry_price_for_action(side, tick)
        if px <= 0:
            self._last_cluster_trace[key] = {
                **base_trace,
                "decision": "allow_invalid_price",
            }
            return True, ""
        if str(info.get("action", "")).upper() != side:
            self._last_cluster_trace[key] = {
                **base_trace,
                "decision": "allow_side_changed",
            }
            return True, ""
        prev_px = float(info.get("price", 0.0) or 0.0)
        prev_ts = float(info.get("ts", 0.0) or 0.0)
        if prev_px <= 0.0 or prev_ts <= 0.0:
            self._last_cluster_trace[key] = {
                **base_trace,
                "decision": "allow_no_previous_signature",
            }
            return True, ""
        window_s = max(
            1,
            int(
                Config.get_symbol_int(
                    symbol,
                    getattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 180)}),
                    int(getattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 180)),
                )
            ),
        )
        if (now_s - prev_ts) > float(window_s):
            self._last_cluster_trace[key] = {
                **base_trace,
                "decision": "allow_outside_window",
                "elapsed_sec": float(now_s - prev_ts),
                "window_sec": int(window_s),
            }
            return True, ""
        move_pct = abs(px - prev_px) / max(1e-9, prev_px)
        need_pct = abs(
            float(
                Config.get_symbol_float(
                    symbol,
                    getattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT_BY_SYMBOL", {"DEFAULT": getattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0004)}),
                    float(getattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0004)),
                )
            )
        )
        setup_id_l = str(setup_id or "").lower()
        if (
            str(symbol or "").upper() in {"NAS100", "BTCUSD"}
            and setup_id_l == "breakout_retest_sell"
            and str(side or "").upper() == "SELL"
            and str(preflight_allowed_action or "").upper() in {"SELL_ONLY", "BOTH"}
        ):
            is_btc = str(symbol or "").upper() == "BTCUSD"
            window_s = min(int(window_s), 60 if is_btc else 45)
            need_pct = float(max(0.0, need_pct * (0.30 if is_btc else 0.38)))
            if (now_s - prev_ts) > float(window_s):
                return True, ""
        if setup_id_l in {"range_upper_reversal_sell", "range_lower_reversal_buy"}:
            # Reversal setups should not spray-add around the same price zone.
            # Even if a symbol override is looser, keep at least the global cluster floor.
            window_s = max(int(window_s), int(getattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 180)))
            need_pct = max(float(need_pct), abs(float(getattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0004))))
        current_sig = semantic_signature if isinstance(semantic_signature, dict) else {}
        prev_sig = info.get("semantic_signature") if isinstance(info.get("semantic_signature"), dict) else {}
        semantic_same_thesis = False
        semantic_relief_applied = False
        btc_duplicate_edge_suppression = False
        btc_duplicate_repeat_quality = False
        btc_duplicate_full_suppression_need_pct = 0.0
        btc_duplicate_effective_need_pct_floor = 0.0
        base_window_s = int(window_s)
        base_need_pct = float(need_pct)
        if bool(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)) and current_sig and prev_sig:
            semantic_same_thesis = self._same_thesis(prev_sig, current_sig)
            current_score = self._safe_float(current_sig.get("semantic_score"), 0.0)
            previous_score = self._safe_float(prev_sig.get("semantic_score"), 0.0)
            min_score = float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_MIN_SCORE", 6))
            if semantic_same_thesis:
                btc_duplicate_lower_buy = bool(
                    key == "BTCUSD"
                    and setup_id_l == "range_lower_reversal_buy"
                    and side == "BUY"
                    and str(prev_sig.get("edge_bias", "")).upper() == "LOWER"
                    and str(current_sig.get("edge_bias", "")).upper() == "LOWER"
                )
                if btc_duplicate_lower_buy:
                    btc_duplicate_edge_suppression = True
                    window_s = max(int(window_s), 300)
                    btc_min_move = max(float(base_need_pct) * 2.10, 0.0010)
                    btc_relief_window_s = max(int(base_window_s), 240)
                    btc_relief_move = max(float(base_need_pct) * 1.45, 0.0006)
                    btc_duplicate_full_suppression_need_pct = float(btc_min_move)
                    strong_repeat_quality = bool(
                        current_score >= max(min_score + 2.5, 8.5)
                        and previous_score >= max(min_score + 1.0, 7.0)
                        and self._safe_float(current_sig.get("side_persistence"), 0.0) >= 0.66
                        and self._safe_int(current_sig.get("side_streak"), 0) >= 4
                        and self._safe_float(current_sig.get("side_barrier"), 1.0) <= 0.16
                        and str(current_sig.get("observe_state", "")).upper() == "CONFIRM"
                    )
                    btc_duplicate_repeat_quality = strong_repeat_quality
                    if strong_repeat_quality:
                        window_s = max(int(base_window_s), int(btc_relief_window_s))
                        need_pct = max(float(need_pct), btc_relief_move)
                        btc_duplicate_effective_need_pct_floor = float(btc_relief_move)
                        semantic_relief_applied = True
                    else:
                        need_pct = max(float(need_pct), btc_min_move)
                        btc_duplicate_effective_need_pct_floor = float(btc_min_move)
                elif (
                    key == "XAUUSD"
                    and setup_id_l == "range_lower_reversal_buy"
                    and side == "BUY"
                    and str(current_sig.get("scene_relief", "")).lower() == "xau_second_support_buy_probe"
                    and str(prev_sig.get("edge_bias", "")).upper() == "LOWER"
                    and str(current_sig.get("edge_bias", "")).upper() == "LOWER"
                ):
                    strong_retest_quality = bool(
                        current_score >= max(min_score - 2.0, 4.0)
                        and (
                            self._safe_float(current_sig.get("side_persistence"), 0.0) >= 0.10
                            or self._safe_int(current_sig.get("side_streak"), 0) >= 1
                            or str(current_sig.get("dominant_side", "")).upper() == "BUY"
                        )
                        and self._safe_float(current_sig.get("side_barrier"), 1.0) <= 0.24
                    )
                    if strong_retest_quality:
                        window_s = min(int(window_s), 90)
                        need_pct = max(0.0, float(need_pct) * 0.25)
                        semantic_relief_applied = True
                elif current_score >= min_score and current_score >= max(min_score - 1.0, previous_score - 1.0):
                    window_mult = max(0.10, min(1.0, float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_WINDOW_MULT", 0.55))))
                    move_mult = max(0.05, min(1.0, float(getattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_MOVE_MULT", 0.35))))
                    window_s = max(15, int(round(float(window_s) * window_mult)))
                    need_pct = max(0.0, float(need_pct) * move_mult)
                    semantic_relief_applied = True
        trace = {
            **base_trace,
            "elapsed_sec": float(now_s - prev_ts),
            "window_sec_base": int(base_window_s),
            "window_sec_effective": int(window_s),
            "need_pct_base": float(base_need_pct),
            "need_pct_effective": float(need_pct),
            "move_pct": float(move_pct),
            "semantic_same_thesis": bool(semantic_same_thesis),
            "semantic_relief_applied": bool(semantic_relief_applied),
            "btc_duplicate_edge_suppression": bool(btc_duplicate_edge_suppression),
            "btc_duplicate_repeat_quality": bool(btc_duplicate_repeat_quality),
            "btc_duplicate_full_suppression_need_pct": float(btc_duplicate_full_suppression_need_pct),
            "btc_duplicate_effective_need_pct_floor": float(btc_duplicate_effective_need_pct_floor),
            "previous_signature": dict(prev_sig or {}),
            "current_signature": dict(current_sig or {}),
        }
        if move_pct < need_pct:
            self._last_cluster_trace[key] = {
                **trace,
                "decision": "block_clustered_entry_price_zone",
            }
            return False, "clustered_entry_price_zone"
        self._last_cluster_trace[key] = {
            **trace,
            "decision": "allow_cluster_spacing_ok",
        }
        return True, ""

    def pass_box_middle_guard(
        self,
        symbol: str,
        action: str,
        tick,
        df_all: dict,
        scorer,
        indicators: dict,
        *,
        setup_id: str = "",
        setup_reason: str = "",
    ) -> tuple[bool, str]:
        if not bool(getattr(Config, "ENABLE_ENTRY_BOX_MID_GUARD", True)):
            return True, ""
        h1 = (df_all or {}).get("1H")
        m15 = (df_all or {}).get("15M")
        if h1 is None or m15 is None or h1.empty or m15.empty:
            return True, ""
        try:
            london = scorer.session_mgr.get_session_range(h1, 8, 16)
        except Exception:
            london = None
        if not london:
            return True, ""
        side = str(action or "").upper()
        if side not in {"BUY", "SELL"}:
            return True, ""
        px = self.entry_price_for_action(side, tick)
        if px <= 0:
            return True, ""
        try:
            pos_in_box = scorer.session_mgr.get_position_in_box(london, px)
        except Exception:
            pos_in_box = "UNKNOWN"
        if str(pos_in_box).upper() != "MIDDLE":
            return True, ""
        bb_mid = float(pd.to_numeric((indicators or {}).get("ind_bb_20_mid", 0.0), errors="coerce") or 0.0)
        bb_up = float(pd.to_numeric((indicators or {}).get("ind_bb_20_up", 0.0), errors="coerce") or 0.0)
        bb_dn = float(pd.to_numeric((indicators or {}).get("ind_bb_20_dn", 0.0), errors="coerce") or 0.0)
        if bb_mid <= 0.0:
            return False, "box_middle_no_bb_context"
        near_ratio = abs(float(getattr(Config, "ENTRY_BOX_MID_NEAR_RATIO", 0.0008)))
        retest_tol = abs(float(getattr(Config, "ENTRY_BOX_MID_RETEST_TOL_PCT", 0.00025)))
        band_near = abs(float(getattr(Config, "ENTRY_BOX_MID_BAND_NEAR_PCT", 0.00035)))
        lookback = max(3, int(getattr(Config, "ENTRY_BOX_MID_RETEST_LOOKBACK", 4)))
        near_mid = abs(px - bb_mid) / max(1e-9, abs(px)) <= near_ratio
        frame = m15[["high", "low", "close"]].tail(lookback).copy()
        for c in ("high", "low", "close"):
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
        frame = frame.dropna()
        if len(frame) < 3:
            return False, "box_middle_insufficient_m15"
        last_close = float(frame["close"].iloc[-1])
        if side == "BUY":
            near_lower = (bb_dn > 0.0) and (px <= bb_dn * (1.0 + band_near))
            mid_retest_hold = near_mid and last_close >= bb_mid * (1.0 - retest_tol) and float(frame["low"].min()) <= bb_mid * (1.0 + retest_tol)
            if (
                str(symbol or "").upper() in {"BTCUSD", "NAS100", "XAUUSD"}
                and str(setup_id or "").lower() in {"range_lower_reversal_buy", "trend_pullback_buy"}
                and str(setup_reason or "").lower() in {
                    "shadow_lower_rebound_confirm",
                    "shadow_failed_sell_reclaim_buy_confirm",
                }
                and bb_up > bb_dn > 0.0
            ):
                channel_pos = float((px - bb_dn) / max(1e-9, (bb_up - bb_dn)))
                near_mid_support = last_close >= bb_mid * (1.0 - retest_tol) and float(frame["low"].min()) <= bb_mid * (1.0 + retest_tol)
                lower_band_reaction = float(frame["low"].min()) <= bb_dn * (1.0 + (band_near * 4.0))
                mid_reclaim_hold = last_close >= bb_mid * (1.0 - (retest_tol * 2.0))
                if channel_pos <= 0.68 or near_mid_support or (lower_band_reaction and mid_reclaim_hold):
                    return True, ""
            if near_lower or mid_retest_hold:
                return True, ""
            return False, "box_middle_buy_without_bb_support"
        near_upper = (bb_up > 0.0) and (px >= bb_up * (1.0 - band_near))
        mid_retest_hold = near_mid and last_close <= bb_mid * (1.0 + retest_tol) and float(frame["high"].max()) >= bb_mid * (1.0 - retest_tol)
        if (
            str(symbol or "").upper() in {"BTCUSD", "NAS100", "XAUUSD"}
            and side == "SELL"
            and str(setup_id or "").lower() == "range_upper_reversal_sell"
            and str(setup_reason or "").lower() in {"shadow_upper_reject_confirm", "shadow_mid_reject_confirm"}
            and bb_up > bb_dn > 0.0
        ):
            channel_pos = float((px - bb_dn) / max(1e-9, (bb_up - bb_dn)))
            if channel_pos >= 0.62:
                return True, ""
        if near_upper or mid_retest_hold:
            return True, ""
        return False, "box_middle_sell_without_bb_resistance"

    def mark_entry(
        self,
        symbol: str,
        action: str,
        price: float,
        ts: float,
        *,
        semantic_signature: dict | None = None,
    ) -> None:
        self._last_entry_signature[str(symbol).upper()] = {
            "action": str(action),
            "price": float(price),
            "ts": float(ts),
            "semantic_signature": dict(semantic_signature or {}),
        }


class EntryThresholdEngine:
    def __init__(self, trade_logger):
        self.trade_logger = trade_logger
        self._utility_stats_cache: dict[str, dict] = {}
        self._utility_spread_cache: dict[str, dict] = {}

    @staticmethod
    def trimmed_mean(series: pd.Series, q: float) -> float:
        if series is None:
            return 0.0
        s = pd.to_numeric(series, errors="coerce").dropna()
        if s.empty:
            return 0.0
        qq = max(0.0, min(0.20, float(q)))
        if qq > 0.0 and len(s) >= 8:
            lo = float(s.quantile(qq))
            hi = float(s.quantile(1.0 - qq))
            s = s[(s >= lo) & (s <= hi)]
        if s.empty:
            return 0.0
        return float(s.mean())

    @staticmethod
    def base_symbol_cost(symbol: str) -> float:
        upper = str(symbol or "").upper()
        for k, v in Config.ROUNDTRIP_COST_USD.items():
            if k == "DEFAULT":
                continue
            if k in upper:
                return float(v)
        return float(Config.ROUNDTRIP_COST_USD.get("DEFAULT", 0.5))

    def load_symbol_utility_stats(self, symbol: str) -> dict | None:
        key = str(symbol or "").upper()
        now_s = time.time()
        ttl = max(10, int(getattr(Config, "ENTRY_UTILITY_STATS_CACHE_TTL_SEC", 60)))
        cached = self._utility_stats_cache.get(key)
        if isinstance(cached, dict) and (now_s - float(cached.get("ts", 0.0)) <= ttl):
            return dict(cached.get("stats", {}))
        reader = getattr(self.trade_logger, "read_closed_df", None)
        if not callable(reader):
            return None
        try:
            closed = reader()
        except Exception:
            logger.exception("utility stats read failed: symbol=%s", key)
            return None
        if closed is None or closed.empty:
            return None
        try:
            work = closed.copy()
            work["symbol"] = work.get("symbol", "").astype(str).str.upper()
            work["profit"] = pd.to_numeric(work.get("profit", 0.0), errors="coerce").fillna(0.0)
            work = work[work["symbol"] == key]
            lookback = max(30, int(getattr(Config, "ENTRY_UTILITY_LOOKBACK_TRADES", 200)))
            work = work.tail(lookback)
            wins = work[work["profit"] > 0]["profit"]
            losses = work[work["profit"] < 0]["profit"].abs()
            min_wins = max(1, int(getattr(Config, "ENTRY_UTILITY_MIN_WINS", 30)))
            min_losses = max(1, int(getattr(Config, "ENTRY_UTILITY_MIN_LOSSES", 30)))
            trim_q = float(getattr(Config, "ENTRY_UTILITY_TRIM_Q", 0.05))
            stats = {
                "ready": bool(len(wins) >= min_wins and len(losses) >= min_losses),
                "wins_n": int(len(wins)),
                "losses_n": int(len(losses)),
                "w_avg": float(self.trimmed_mean(wins, trim_q)),
                "l_avg": float(self.trimmed_mean(losses, trim_q)),
            }
            self._utility_stats_cache[key] = {"ts": now_s, "stats": dict(stats)}
            return stats
        except Exception:
            logger.exception("utility stats calc failed: symbol=%s", key)
            return None

    def recent_spread_ratio(self, symbol: str) -> float:
        key = str(symbol or "").upper()
        now_s = time.time()
        ttl = max(10, int(getattr(Config, "DYNAMIC_COST_CACHE_TTL_SEC", 60)))
        cached = self._utility_spread_cache.get(key)
        if isinstance(cached, dict) and (now_s - float(cached.get("ts", 0.0)) <= ttl):
            return float(cached.get("ratio", 1.0))
        ratio = 1.0
        reader = getattr(self.trade_logger, "read_closed_df", None)
        if not callable(reader):
            return ratio
        try:
            closed = reader()
            if closed is not None and not closed.empty and "regime_spread_ratio" in closed.columns:
                work = closed.copy()
                work["symbol"] = work.get("symbol", "").astype(str).str.upper()
                work = work[work["symbol"] == key]
                work["regime_spread_ratio"] = pd.to_numeric(work["regime_spread_ratio"], errors="coerce")
                work = work[work["regime_spread_ratio"] > 0]
                if not work.empty:
                    lookback = max(10, int(getattr(Config, "DYNAMIC_COST_RECENT_TRADES", 40)))
                    ratio = float(work["regime_spread_ratio"].tail(lookback).median())
        except Exception:
            ratio = 1.0
        if not (ratio > 0):
            ratio = 1.0
        self._utility_spread_cache[key] = {"ratio": float(ratio), "ts": now_s}
        return float(ratio)

    def estimate_entry_cost(self, symbol: str, regime: dict, spread_now: float) -> float:
        base = float(self.base_symbol_cost(symbol))
        live_ratio = float((regime or {}).get("spread_ratio", 1.0) or 1.0)
        if spread_now > 0.0:
            live_ratio = max(live_ratio, 1.0)
        if not bool(getattr(Config, "ENABLE_DYNAMIC_SPREAD_COST", True)):
            return base
        recent_ratio = self.recent_spread_ratio(symbol)
        spread_mult = (live_ratio / recent_ratio) if recent_ratio > 0 else 1.0
        spread_mult = max(
            float(getattr(Config, "DYNAMIC_COST_SPREAD_MIN_MULT", 0.8)),
            min(float(getattr(Config, "DYNAMIC_COST_SPREAD_MAX_MULT", 2.2)), float(spread_mult)),
        )
        return float(base * spread_mult)

    @staticmethod
    def utility_min(symbol: str, same_dir_count: int) -> float:
        # Backward/forward compatible key resolution:
        # - current config: ENTRY_UTILITY_MIN(_BY_SYMBOL)
        # - legacy key: ENTRY_UTILITY_U_MIN(_BY_SYMBOL)
        base_default = float(
            getattr(
                Config,
                "ENTRY_UTILITY_U_MIN",
                getattr(Config, "ENTRY_UTILITY_MIN", 0.15),
            )
        )
        by_symbol = getattr(
            Config,
            "ENTRY_UTILITY_U_MIN_BY_SYMBOL",
            getattr(Config, "ENTRY_UTILITY_MIN_BY_SYMBOL", {"DEFAULT": base_default}),
        )
        base = float(
            Config.get_symbol_float(
                symbol,
                by_symbol,
                base_default,
            )
        )
        step = float(getattr(Config, "ENTRY_UTILITY_U_MIN_PYRAMID_STEP", 0.05))
        return float(base + (max(0, int(same_dir_count)) * max(0.0, step)))

    @staticmethod
    def context_usd_adjustment(context_adj: int, topdown_ok: bool, gate_ok: bool) -> float:
        per = float(
            getattr(
                Config,
                "ENTRY_UTILITY_CONTEXT_SCALE_USD",
                getattr(Config, "ENTRY_UTILITY_CONTEXT_USD_PER_POINT", 0.01),
            )
        )
        bonus = float(getattr(Config, "ENTRY_UTILITY_GATE_BONUS_USD", 0.0))
        cap = max(0.01, float(getattr(Config, "ENTRY_UTILITY_CONTEXT_CAP_USD", 0.80)))
        val = float(context_adj) * per
        if bool(topdown_ok) and bool(gate_ok):
            val += bonus
        if val > cap:
            val = cap
        elif val < -cap:
            val = -cap
        return float(val)

    @staticmethod
    def bb_penalty_usd(symbol: str, reason: str) -> float:
        text = str(reason or "").lower()
        if not text:
            return 0.0
        key = "ENTRY_BB_GUARD_PENALTY_USD_BY_SYMBOL"
        default = float(getattr(Config, "ENTRY_BB_GUARD_PENALTY_USD", 0.0))
        by_symbol = getattr(Config, key, {"DEFAULT": default})
        if ("bb_" in text) or ("box_middle" in text):
            return float(Config.get_symbol_float(symbol, by_symbol, default))
        return 0.0

    @staticmethod
    def _regime_name(regime: dict) -> str:
        name = str((regime or {}).get("name", "") or "").strip().upper()
        return name if name else "UNKNOWN"

    def compute_context_threshold_adjustment(
        self,
        regime: dict,
        topdown_stat: dict,
        entry_h1_context_score: int,
        entry_h1_context_opposite: int,
    ) -> tuple[int, dict]:
        regime_name = self._regime_name(regime)
        spread_ratio = float((regime or {}).get("spread_ratio", 0.0) or 0.0)
        vol_ratio = float((regime or {}).get("volatility_ratio", 1.0) or 1.0)
        align = int((topdown_stat or {}).get("align", 0) or 0)
        conflict = int((topdown_stat or {}).get("conflict", 0) or 0)
        min_align = max(0, int(getattr(Config, "TOPDOWN_HIGHER_TF_MIN_ALIGN", 2)))
        max_conflict = max(0, int(getattr(Config, "TOPDOWN_HIGHER_TF_MAX_CONFLICT", 1)))
        min_ctx = max(0, int(getattr(Config, "H1_ENTRY_GATE_MIN_CONTEXT", 20)))
        min_gap = max(0, int(getattr(Config, "H1_ENTRY_GATE_MIN_GAP", 8)))
        details = {"regime": 0, "spread": 0, "volatility": 0, "topdown": 0, "h1": 0}
        if regime_name in {"TREND", "EXPANSION"}:
            details["regime"] -= int(getattr(Config, "ENTRY_CTX_TREND_BONUS", 20))
        if regime_name in {"RANGE", "LOW_LIQUIDITY"}:
            details["regime"] += int(getattr(Config, "ENTRY_CTX_RANGE_PENALTY", 18))
        if spread_ratio > 1.15:
            details["spread"] += int(getattr(Config, "ENTRY_CTX_SPREAD_PENALTY", 14))
        if vol_ratio >= 1.18:
            details["volatility"] -= int(getattr(Config, "ENTRY_CTX_VOL_EXPANSION_BONUS", 8))
        elif vol_ratio <= 0.90:
            details["volatility"] += int(getattr(Config, "ENTRY_CTX_VOL_CONTRACTION_PENALTY", 10))
        if align >= min_align and conflict <= max_conflict:
            details["topdown"] -= int(getattr(Config, "ENTRY_CTX_TOPDOWN_BONUS", 8))
        elif conflict > max_conflict:
            details["topdown"] += int(getattr(Config, "ENTRY_CTX_TOPDOWN_PENALTY", 12))
        if entry_h1_context_score >= min_ctx and (entry_h1_context_score - entry_h1_context_opposite) >= min_gap:
            details["h1"] -= int(getattr(Config, "ENTRY_CTX_H1_BONUS", 8))
        elif entry_h1_context_opposite > entry_h1_context_score:
            details["h1"] += int(getattr(Config, "ENTRY_CTX_H1_PENALTY", 10))
        total = int(sum(int(v) for v in details.values()))
        total = max(-40, min(60, total))
        return int(total), details

    @staticmethod
    def check_hard_no_trade_guard(symbol: str, regime: dict) -> str:
        spread_ratio = float((regime or {}).get("spread_ratio", 0.0) or 0.0)
        vol_ratio = float((regime or {}).get("volatility_ratio", 1.0) or 1.0)
        regime_name = str((regime or {}).get("name", "") or "").upper()
        min_vol = float(
            Config.get_symbol_float(
                symbol,
                getattr(
                    Config,
                    "ENTRY_HARD_MIN_VOL_RATIO_BY_SYMBOL",
                    {"DEFAULT": float(getattr(Config, "ENTRY_HARD_MIN_VOL_RATIO", 0.55))},
                ),
                float(getattr(Config, "ENTRY_HARD_MIN_VOL_RATIO", 0.55)),
            )
        )
        if regime_name == "RANGE":
            min_vol = float(
                Config.get_symbol_float(
                    symbol,
                    getattr(
                        Config,
                        "ENTRY_HARD_MIN_VOL_RATIO_RANGE_BY_SYMBOL",
                        {"DEFAULT": float(getattr(Config, "ENTRY_HARD_MIN_VOL_RATIO_RANGE", min_vol))},
                    ),
                    float(getattr(Config, "ENTRY_HARD_MIN_VOL_RATIO_RANGE", min_vol)),
                )
            )
        if spread_ratio > float(getattr(Config, "ENTRY_HARD_MAX_SPREAD_RATIO", 1.80)):
            return "hard_guard_spread_too_wide"
        if vol_ratio < float(min_vol):
            return "hard_guard_volatility_too_low"
        if vol_ratio > float(getattr(Config, "ENTRY_HARD_MAX_VOL_RATIO", 2.40)):
            return "hard_guard_volatility_too_high"
        return ""


class EntryDecisionRecorder:
    def __init__(self, runtime):
        self.runtime = runtime

    @staticmethod
    def _rollover_if_needed(path: Path, cols: list[str]) -> dict[str, object]:
        return execute_entry_decision_rollover(
            path=path,
            columns=list(cols),
            root=Path(__file__).resolve().parents[2],
            create_if_missing=False,
            trigger_mode="runtime_append",
        )

    def append_entry_decision_log(self, row: dict) -> dict[str, object]:
        if not bool(getattr(Config, "ENTRY_DECISION_LOG_ENABLED", True)):
            return {}
        try:
            path = Path(getattr(Config, "ENTRY_DECISION_LOG_PATH", "data/trades/entry_decisions.csv"))
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[2] / path
            path.parent.mkdir(parents=True, exist_ok=True)
            cols = list(ENTRY_DECISION_LOG_COLUMNS)
            full_cols = list(ENTRY_DECISION_FULL_COLUMNS)
            payload = {}
            for c in full_cols:
                payload[c] = row.get(c, "")
            # Backward-compatible aliases
            if payload.get("entry_score_raw", "") == "":
                payload["entry_score_raw"] = row.get("raw_score", "")
            if payload.get("contra_score_raw", "") == "":
                payload["contra_score_raw"] = row.get("contra_score", "")
            if payload.get("effective_entry_threshold", "") == "":
                payload["effective_entry_threshold"] = row.get("effective_threshold", "")
            if payload.get("prs_contract_version", "") == "":
                payload["prs_contract_version"] = "v2"
            if payload.get("prs_canonical_position_field", "") == "":
                payload["prs_canonical_position_field"] = "position_snapshot_v2"
            if payload.get("prs_canonical_position_effective_field", "") == "":
                payload["prs_canonical_position_effective_field"] = "position_snapshot_effective_v1"
            if payload.get("prs_canonical_response_field", "") == "":
                payload["prs_canonical_response_field"] = "response_vector_v2"
            if payload.get("prs_canonical_response_effective_field", "") == "":
                payload["prs_canonical_response_effective_field"] = "response_vector_effective_v1"
            if payload.get("prs_canonical_state_field", "") == "":
                payload["prs_canonical_state_field"] = "state_vector_v2"
            if payload.get("prs_canonical_state_effective_field", "") == "":
                payload["prs_canonical_state_effective_field"] = "state_vector_effective_v1"
            if payload.get("prs_canonical_evidence_field", "") == "":
                payload["prs_canonical_evidence_field"] = "evidence_vector_v1"
            if payload.get("prs_canonical_evidence_effective_field", "") == "":
                payload["prs_canonical_evidence_effective_field"] = "evidence_vector_effective_v1"
            if payload.get("prs_canonical_belief_field", "") == "":
                payload["prs_canonical_belief_field"] = "belief_state_v1"
            if payload.get("prs_canonical_belief_effective_field", "") == "":
                payload["prs_canonical_belief_effective_field"] = "belief_state_effective_v1"
            if payload.get("prs_canonical_barrier_field", "") == "":
                payload["prs_canonical_barrier_field"] = "barrier_state_v1"
            if payload.get("prs_canonical_barrier_effective_field", "") == "":
                payload["prs_canonical_barrier_effective_field"] = "barrier_state_effective_v1"
            if payload.get("prs_canonical_forecast_features_field", "") == "":
                payload["prs_canonical_forecast_features_field"] = "forecast_features_v1"
            if payload.get("prs_canonical_transition_forecast_field", "") == "":
                payload["prs_canonical_transition_forecast_field"] = "transition_forecast_v1"
            if payload.get("prs_canonical_trade_management_forecast_field", "") == "":
                payload["prs_canonical_trade_management_forecast_field"] = "trade_management_forecast_v1"
            if payload.get("prs_canonical_forecast_gap_metrics_field", "") == "":
                payload["prs_canonical_forecast_gap_metrics_field"] = "forecast_gap_metrics_v1"
            if payload.get("prs_canonical_forecast_effective_field", "") == "":
                payload["prs_canonical_forecast_effective_field"] = "forecast_effective_policy_v1"
            if payload.get("prs_canonical_energy_field", "") == "":
                payload["prs_canonical_energy_field"] = "energy_helper_v2"
            if str(payload.get("prs_canonical_observe_confirm_field", "") or "") in {"", "observe_confirm_v1"}:
                payload["prs_canonical_observe_confirm_field"] = "observe_confirm_v2"
            if payload.get("prs_compatibility_observe_confirm_field", "") == "":
                payload["prs_compatibility_observe_confirm_field"] = "observe_confirm_v1"
            if payload.get("energy_migration_contract_field", "") == "":
                payload["energy_migration_contract_field"] = "energy_migration_dual_write_v1"
            if payload.get("energy_scope_contract_field", "") == "":
                payload["energy_scope_contract_field"] = "energy_scope_contract_v1"
            if payload.get("runtime_alignment_scope_contract_field", "") == "":
                payload["runtime_alignment_scope_contract_field"] = "runtime_alignment_scope_contract_v1"
            if payload.get("energy_compatibility_runtime_field", "") == "":
                payload["energy_compatibility_runtime_field"] = "energy_snapshot"
            if payload.get("energy_logging_replay_contract_field", "") == "":
                payload["energy_logging_replay_contract_field"] = "energy_logging_replay_contract_v1"
            observe_confirm_payload_v2 = row.get("observe_confirm_v2", "")
            if isinstance(observe_confirm_payload_v2, str) and observe_confirm_payload_v2.strip():
                try:
                    observe_confirm_payload_v2 = json.loads(observe_confirm_payload_v2)
                except Exception:
                    observe_confirm_payload_v2 = {}
            elif not isinstance(observe_confirm_payload_v2, dict):
                observe_confirm_payload_v2 = {}
            observe_confirm_payload_v1 = row.get("observe_confirm_v1", "")
            if isinstance(observe_confirm_payload_v1, str) and observe_confirm_payload_v1.strip():
                try:
                    observe_confirm_payload_v1 = json.loads(observe_confirm_payload_v1)
                except Exception:
                    observe_confirm_payload_v1 = {}
            elif not isinstance(observe_confirm_payload_v1, dict):
                observe_confirm_payload_v1 = {}
            raw_observe_confirm_payload_v2 = dict(observe_confirm_payload_v2 or {})
            raw_observe_confirm_payload_v1 = dict(observe_confirm_payload_v1 or {})
            original_v2_missing = not bool(observe_confirm_payload_v2)
            original_v1_present = bool(observe_confirm_payload_v1)
            if not observe_confirm_payload_v2 and observe_confirm_payload_v1:
                observe_confirm_payload_v2 = dict(observe_confirm_payload_v1)
            if not observe_confirm_payload_v1 and observe_confirm_payload_v2:
                observe_confirm_payload_v1 = dict(observe_confirm_payload_v2)
            observe_confirm_resolution_container = {
                "observe_confirm_v2": dict(raw_observe_confirm_payload_v2 or {}),
                "observe_confirm_v1": dict(raw_observe_confirm_payload_v1 or {}),
                "prs_canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                "prs_compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                "prs_log_contract_v2": {
                    "canonical_observe_confirm_field": payload.get("prs_canonical_observe_confirm_field", ""),
                    "compatibility_observe_confirm_field": payload.get("prs_compatibility_observe_confirm_field", ""),
                },
            }
            consumer_migration_guard_v1 = build_consumer_migration_guard_metadata(
                observe_confirm_resolution_container
            )
            resolved_observe_confirm_payload = dict(
                resolve_consumer_observe_confirm_resolution(
                    observe_confirm_resolution_container
                ).get("payload", {})
                or {}
            )
            if payload.get("observe_confirm_v2", "") == "" and observe_confirm_payload_v2:
                payload["observe_confirm_v2"] = json.dumps(
                    observe_confirm_payload_v2,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("observe_confirm_v1", "") == "" and observe_confirm_payload_v1:
                payload["observe_confirm_v1"] = json.dumps(
                    observe_confirm_payload_v1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_archetype_id", "") == "":
                payload["consumer_archetype_id"] = str(
                    resolved_observe_confirm_payload.get("archetype_id", "") or ""
                )
            if payload.get("consumer_invalidation_id", "") == "":
                payload["consumer_invalidation_id"] = str(
                    resolved_observe_confirm_payload.get("invalidation_id", "") or ""
                )
            if payload.get("consumer_management_profile_id", "") == "":
                payload["consumer_management_profile_id"] = str(
                    resolved_observe_confirm_payload.get("management_profile_id", "") or ""
                )
            lifecycle_states = {"OBSERVE", "CONFIRM", "CONFLICT_OBSERVE", "NO_TRADE", "INVALIDATED"}
            if (
                str(payload.get("shadow_state_v1", "") or "").upper() in lifecycle_states
                and str(resolved_observe_confirm_payload.get("archetype_id", "") or "").strip()
            ):
                payload["shadow_state_v1"] = str(resolved_observe_confirm_payload.get("archetype_id", "") or "")
            if payload.get("observe_confirm_input_contract_v2", "") == "":
                payload["observe_confirm_input_contract_v2"] = json.dumps(
                    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("observe_confirm_migration_dual_write_v1", "") == "":
                payload["observe_confirm_migration_dual_write_v1"] = json.dumps(
                    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("observe_confirm_output_contract_v2", "") == "":
                payload["observe_confirm_output_contract_v2"] = json.dumps(
                    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("observe_confirm_scope_contract_v1", "") == "":
                payload["observe_confirm_scope_contract_v1"] = json.dumps(
                    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_input_contract_v1", "") == "":
                payload["consumer_input_contract_v1"] = json.dumps(
                    CONSUMER_INPUT_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_migration_freeze_v1", "") == "":
                payload["consumer_migration_freeze_v1"] = json.dumps(
                    CONSUMER_MIGRATION_FREEZE_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            payload["consumer_migration_guard_v1"] = json.dumps(
                dict(consumer_migration_guard_v1 or {}),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if payload.get("consumer_logging_contract_v1", "") == "":
                payload["consumer_logging_contract_v1"] = json.dumps(
                    CONSUMER_LOGGING_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_test_contract_v1", "") == "":
                payload["consumer_test_contract_v1"] = json.dumps(
                    CONSUMER_TEST_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_freeze_handoff_v1", "") == "":
                payload["consumer_freeze_handoff_v1"] = json.dumps(
                    CONSUMER_FREEZE_HANDOFF_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_contract_v1", "") == "":
                payload["layer_mode_contract_v1"] = json.dumps(
                    LAYER_MODE_MODE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_layer_inventory_v1", "") == "":
                payload["layer_mode_layer_inventory_v1"] = json.dumps(
                    LAYER_MODE_LAYER_INVENTORY_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_default_policy_v1", "") == "":
                payload["layer_mode_default_policy_v1"] = json.dumps(
                    LAYER_MODE_DEFAULT_POLICY_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_dual_write_contract_v1", "") == "":
                payload["layer_mode_dual_write_contract_v1"] = json.dumps(
                    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_influence_semantics_v1", "") == "":
                payload["layer_mode_influence_semantics_v1"] = json.dumps(
                    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_application_contract_v1", "") == "":
                payload["layer_mode_application_contract_v1"] = json.dumps(
                    LAYER_MODE_APPLICATION_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_identity_guard_contract_v1", "") == "":
                payload["layer_mode_identity_guard_contract_v1"] = json.dumps(
                    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_policy_overlay_output_contract_v1", "") == "":
                payload["layer_mode_policy_overlay_output_contract_v1"] = json.dumps(
                    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_logging_replay_contract_v1", "") == "":
                payload["layer_mode_logging_replay_contract_v1"] = json.dumps(
                    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_scope_contract_v1", "") == "":
                payload["layer_mode_scope_contract_v1"] = json.dumps(
                    LAYER_MODE_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_effective_defaults = build_layer_mode_effective_metadata(payload)
            if payload.get("position_snapshot_effective_v1", "") == "":
                payload["position_snapshot_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("position_snapshot_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("response_vector_effective_v1", "") == "":
                payload["response_vector_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("response_vector_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("state_vector_effective_v1", "") == "":
                payload["state_vector_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("state_vector_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("evidence_vector_effective_v1", "") == "":
                payload["evidence_vector_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("evidence_vector_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("belief_state_effective_v1", "") == "":
                payload["belief_state_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("belief_state_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("barrier_state_effective_v1", "") == "":
                payload["barrier_state_effective_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("barrier_state_effective_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("forecast_effective_policy_v1", "") == "":
                payload["forecast_effective_policy_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("forecast_effective_policy_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_effective_trace_v1", "") == "":
                payload["layer_mode_effective_trace_v1"] = json.dumps(
                    layer_mode_effective_defaults.get("layer_mode_effective_trace_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_influence_defaults = build_layer_mode_influence_metadata()
            if payload.get("layer_mode_influence_trace_v1", "") == "":
                payload["layer_mode_influence_trace_v1"] = json.dumps(
                    layer_mode_influence_defaults.get("layer_mode_influence_trace_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_application_defaults = build_layer_mode_application_metadata()
            if payload.get("layer_mode_application_trace_v1", "") == "":
                payload["layer_mode_application_trace_v1"] = json.dumps(
                    layer_mode_application_defaults.get("layer_mode_application_trace_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_identity_guard_defaults = build_layer_mode_identity_guard_metadata()
            if payload.get("layer_mode_identity_guard_trace_v1", "") == "":
                payload["layer_mode_identity_guard_trace_v1"] = json.dumps(
                    layer_mode_identity_guard_defaults.get("layer_mode_identity_guard_trace_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_policy_overlay_defaults = build_layer_mode_policy_overlay_metadata()
            if payload.get("layer_mode_policy_v1", "") == "":
                payload["layer_mode_policy_v1"] = json.dumps(
                    layer_mode_policy_overlay_defaults.get("layer_mode_policy_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            layer_mode_logging_replay_defaults = build_layer_mode_logging_replay_metadata(payload)
            if payload.get("layer_mode_logging_replay_v1", "") == "":
                payload["layer_mode_logging_replay_v1"] = json.dumps(
                    layer_mode_logging_replay_defaults.get("layer_mode_logging_replay_v1", {}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_test_contract_v1", "") == "":
                payload["layer_mode_test_contract_v1"] = json.dumps(
                    LAYER_MODE_TEST_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("layer_mode_freeze_handoff_v1", "") == "":
                payload["layer_mode_freeze_handoff_v1"] = json.dumps(
                    LAYER_MODE_FREEZE_HANDOFF_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("setup_detector_responsibility_contract_v1", "") == "":
                payload["setup_detector_responsibility_contract_v1"] = json.dumps(
                    SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("setup_mapping_contract_v1", "") == "":
                payload["setup_mapping_contract_v1"] = json.dumps(
                    SETUP_MAPPING_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("entry_guard_contract_v1", "") == "":
                payload["entry_guard_contract_v1"] = json.dumps(
                    ENTRY_GUARD_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("entry_service_responsibility_contract_v1", "") == "":
                payload["entry_service_responsibility_contract_v1"] = json.dumps(
                    ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("exit_handoff_contract_v1", "") == "":
                payload["exit_handoff_contract_v1"] = json.dumps(
                    EXIT_HANDOFF_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("re_entry_contract_v1", "") == "":
                payload["re_entry_contract_v1"] = json.dumps(
                    RE_ENTRY_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_scope_contract_v1", "") == "":
                payload["consumer_scope_contract_v1"] = json.dumps(
                    CONSUMER_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_layer_mode_integration_v1", "") == "":
                payload["consumer_layer_mode_integration_v1"] = json.dumps(
                    CONSUMER_LAYER_MODE_INTEGRATION_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("consumer_input_observe_confirm_field", "") == "":
                inferred_field = (
                    CONSUMER_INPUT_CONTRACT_V1["compatibility_observe_confirm_field_v1"]
                    if original_v2_missing and original_v1_present
                    else str(
                        payload.get("prs_canonical_observe_confirm_field", "")
                        or CONSUMER_INPUT_CONTRACT_V1["canonical_observe_confirm_field"]
                    )
                )
                payload["consumer_input_observe_confirm_field"] = str(inferred_field)
            if payload.get("consumer_input_contract_version", "") == "":
                payload["consumer_input_contract_version"] = str(CONSUMER_INPUT_CONTRACT_V1["contract_version"])
            if payload.get("consumer_migration_contract_version", "") == "":
                payload["consumer_migration_contract_version"] = str(CONSUMER_MIGRATION_FREEZE_V1["contract_version"])
            if payload.get("consumer_used_compatibility_fallback_v1", "") == "":
                payload["consumer_used_compatibility_fallback_v1"] = str(
                    bool(consumer_migration_guard_v1.get("used_compatibility_fallback_v1", False))
                )
            if payload.get("consumer_policy_input_field", "") == "":
                payload["consumer_policy_input_field"] = str(
                    payload.get("layer_mode_policy_output_field", "")
                    or CONSUMER_LAYER_MODE_INTEGRATION_V1["canonical_policy_field"]
                )
            if payload.get("consumer_policy_contract_version", "") == "":
                payload["consumer_policy_contract_version"] = str(CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"])
            if payload.get("consumer_policy_identity_preserved", "") == "":
                policy_payload = payload.get("layer_mode_policy_v1", {})
                if isinstance(policy_payload, str):
                    try:
                        policy_payload = json.loads(policy_payload)
                    except Exception:
                        policy_payload = {}
                payload["consumer_policy_identity_preserved"] = str(
                    bool((policy_payload or {}).get("identity_preserved", False))
                )
            if payload.get("consumer_setup_id", "") == "":
                payload["consumer_setup_id"] = str(payload.get("setup_id", "") or "")
            effective_action = str(payload.get("consumer_effective_action") or payload.get("action", "") or "").strip().upper()
            if effective_action not in {"BUY", "SELL"}:
                effective_action = "NONE"
            payload["consumer_effective_action"] = effective_action
            if payload.get("consumer_guard_result", "") == "":
                payload["consumer_guard_result"] = str(
                    resolve_consumer_guard_result(
                        effective_action=effective_action,
                        block_kind=str(payload.get("consumer_block_kind", "") or ""),
                    )
                )
            if payload.get("consumer_handoff_contract_version", "") == "":
                output_contract = OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2
                payload["consumer_handoff_contract_version"] = str(
                    output_contract.get("contract_version", "") or "observe_confirm_output_contract_v2"
                )
            energy_snapshot_payload = row.get("energy_snapshot", "")
            if isinstance(energy_snapshot_payload, str) and energy_snapshot_payload.strip():
                try:
                    energy_snapshot_payload = json.loads(energy_snapshot_payload)
                except Exception:
                    energy_snapshot_payload = {}
            elif not isinstance(energy_snapshot_payload, dict):
                energy_snapshot_payload = {}
            if payload.get("energy_migration_dual_write_v1", "") == "":
                payload["energy_migration_dual_write_v1"] = json.dumps(
                    ENERGY_MIGRATION_DUAL_WRITE_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("energy_scope_contract_v1", "") == "":
                payload["energy_scope_contract_v1"] = json.dumps(
                    ENERGY_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("runtime_alignment_scope_contract_v1", "") == "":
                payload["runtime_alignment_scope_contract_v1"] = json.dumps(
                    RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("energy_logging_replay_contract_v1", "") == "":
                payload["energy_logging_replay_contract_v1"] = json.dumps(
                    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            energy_helper_payload = row.get("energy_helper_v2", "")
            if isinstance(energy_helper_payload, str) and energy_helper_payload.strip():
                try:
                    energy_helper_payload = json.loads(energy_helper_payload)
                except Exception:
                    energy_helper_payload = {}
            elif not isinstance(energy_helper_payload, dict):
                energy_helper_payload = {}
            energy_migration_guard_v1 = resolve_energy_migration_bridge_state(
                {
                    "energy_helper_v2": dict(energy_helper_payload or {}),
                    "energy_snapshot": dict(energy_snapshot_payload or {}),
                }
            )
            energy_bridge_rebuild_active = bool(energy_migration_guard_v1.get("used_compatibility_bridge", False))
            if not energy_helper_payload:
                energy_helper_payload = build_energy_helper_v2(
                    {
                        **payload,
                        "observe_confirm_v2": dict(resolved_observe_confirm_payload or {}),
                    },
                    legacy_energy_snapshot=dict(energy_migration_guard_v1.get("legacy_snapshot", {}) or {}),
                )
                energy_migration_guard_v1 = resolve_energy_migration_bridge_state(
                    {
                        "energy_helper_v2": dict(energy_helper_payload or {}),
                        "energy_snapshot": dict(energy_snapshot_payload or {}),
                    }
                )
            energy_migration_guard_v1["compatibility_bridge_rebuild_active"] = bool(energy_bridge_rebuild_active)
            energy_usage_trace = resolve_entry_service_energy_usage(payload)
            energy_helper_payload = attach_energy_consumer_usage_trace(
                energy_helper_payload,
                component=str(energy_usage_trace.get("component", "EntryService") or "EntryService"),
                consumed_fields=list(energy_usage_trace.get("consumed_fields", []) or []),
                usage_source=str(energy_usage_trace.get("usage_source", "inferred") or "inferred"),
                usage_mode=str(energy_usage_trace.get("usage_mode", "not_consumed") or "not_consumed"),
                effective_action=effective_action,
                guard_result=str(payload.get("consumer_guard_result", "") or ""),
                block_reason=str(payload.get("consumer_block_reason", "") or ""),
                block_kind=str(payload.get("consumer_block_kind", "") or ""),
                block_source_layer=str(payload.get("consumer_block_source_layer", "") or ""),
                decision_outcome=str(payload.get("entry_wait_decision", "") or payload.get("outcome", "") or ""),
                wait_state=str(payload.get("entry_wait_state", "") or ""),
                wait_reason=str(
                    payload.get("entry_wait_reason", "") or payload.get("consumer_block_reason", "") or ""
                ),
                live_gate_applied=bool(energy_usage_trace.get("live_gate_applied", False)),
                branch_records=list(energy_usage_trace.get("branch_records", []) or []),
            )
            payload["energy_helper_v2"] = json.dumps(
                energy_helper_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            payload["energy_migration_guard_v1"] = json.dumps(
                dict(energy_migration_guard_v1 or {}),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if energy_snapshot_payload:
                payload["energy_snapshot"] = json.dumps(
                    energy_snapshot_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            payload["layer_mode_logging_replay_v1"] = json.dumps(
                build_layer_mode_logging_replay_metadata(payload).get("layer_mode_logging_replay_v1", {}),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if payload.get("forecast_calibration_contract_v1", "") == "":
                payload["forecast_calibration_contract_v1"] = json.dumps(
                    FORECAST_CALIBRATION_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if payload.get("outcome_labeler_scope_contract_v1", "") == "":
                payload["outcome_labeler_scope_contract_v1"] = json.dumps(
                    OUTCOME_LABELER_SCOPE_CONTRACT_V1,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            payload["time"] = payload.get("time") or datetime.now().isoformat(timespec="seconds")
            decision_generated_ts = row.get("_decision_generated_ts", payload.get("_decision_generated_ts"))
            runtime_snapshot_generated_ts = row.get("_runtime_snapshot_generated_ts", payload.get("_runtime_snapshot_generated_ts"))
            payload.pop("_decision_generated_ts", None)
            payload.pop("_runtime_snapshot_generated_ts", None)
            key_payload = dict(payload)
            if decision_generated_ts not in ("", None):
                key_payload["decision_generated_ts"] = float(decision_generated_ts)
            detail_row_key = resolve_entry_decision_row_key(key_payload)
            payload["decision_row_key"] = str(payload.get("decision_row_key", "") or detail_row_key)
            payload["replay_row_key"] = str(payload.get("replay_row_key", "") or payload["decision_row_key"])
            existing_runtime_snapshot_key = str(payload.get("runtime_snapshot_key", "") or "")
            if existing_runtime_snapshot_key and not is_generic_runtime_signal_row_key(existing_runtime_snapshot_key):
                payload["runtime_snapshot_key"] = existing_runtime_snapshot_key
            else:
                payload["runtime_snapshot_key"] = str(resolve_runtime_signal_row_key(payload))
            detail_path = resolve_entry_decision_detail_path(path)
            trace_quality = summarize_trace_quality(
                payload,
                decision_ts=(float(decision_generated_ts) if decision_generated_ts not in ("", None) else None),
                runtime_snapshot_ts=(
                    float(runtime_snapshot_generated_ts)
                    if runtime_snapshot_generated_ts not in ("", None)
                    else None
                ),
            )
            payload.update(trace_quality)
            p0_decision_trace = build_p0_decision_trace_v1(payload)
            payload["p0_identity_owner"] = str(p0_decision_trace.get("identity_owner", "") or "")
            payload["p0_execution_gate_owner"] = str(p0_decision_trace.get("execution_gate_owner", "") or "")
            payload["p0_decision_owner_relation"] = str(p0_decision_trace.get("decision_owner_relation", "") or "")
            payload["p0_coverage_state"] = str(p0_decision_trace.get("coverage_state", "") or "")
            payload["p0_coverage_source"] = str(p0_decision_trace.get("coverage_source", "") or "")
            payload["p0_decision_trace_v1"] = json.dumps(
                p0_decision_trace,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            payload["p0_decision_trace_contract_v1"] = json.dumps(
                P0_DECISION_TRACE_CONTRACT_V1,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            p7_size_overlay = payload.get("p7_guarded_size_overlay_v1", {})
            if isinstance(p7_size_overlay, str):
                try:
                    p7_size_overlay = json.loads(p7_size_overlay)
                except Exception:
                    p7_size_overlay = {}
            if not isinstance(p7_size_overlay, dict):
                p7_size_overlay = {}
            payload["p7_guarded_size_overlay_v1"] = json.dumps(
                p7_size_overlay,
                ensure_ascii=False,
                separators=(",", ":"),
            ) if p7_size_overlay else ""
            payload["p7_size_overlay_enabled"] = int(1 if bool(p7_size_overlay.get("enabled")) else 0)
            payload["p7_size_overlay_mode"] = str(p7_size_overlay.get("mode", "") or "")
            payload["p7_size_overlay_matched"] = int(1 if bool(p7_size_overlay.get("matched")) else 0)
            payload["p7_size_overlay_target_multiplier"] = (
                "" if p7_size_overlay.get("target_multiplier") in {"", None}
                else float(p7_size_overlay.get("target_multiplier", 0.0) or 0.0)
            )
            payload["p7_size_overlay_effective_multiplier"] = (
                "" if p7_size_overlay.get("effective_multiplier") in {"", None}
                else float(p7_size_overlay.get("effective_multiplier", 0.0) or 0.0)
            )
            payload["p7_size_overlay_apply_allowed"] = int(
                1 if bool(p7_size_overlay.get("apply_allowed")) else 0
            )
            payload["p7_size_overlay_applied"] = int(1 if bool(p7_size_overlay.get("applied")) else 0)
            payload["p7_size_overlay_gate_reason"] = str(p7_size_overlay.get("gate_reason", "") or "")
            payload["p7_size_overlay_source"] = str(p7_size_overlay.get("source_path", "") or "")
            detail_record = build_entry_decision_detail_record(payload, row_key=detail_row_key)
            hot_payload = build_entry_decision_hot_payload(payload, detail_row_key=detail_row_key)
            detail_blob_bytes = json_payload_size_bytes(detail_record)
            snapshot_payload_bytes = int(
                row.get("snapshot_payload_bytes", payload.get("snapshot_payload_bytes", 0) or 0)
            )
            row_payload_bytes = json_payload_size_bytes(hot_payload)
            payload["detail_blob_bytes"] = int(detail_blob_bytes)
            payload["snapshot_payload_bytes"] = int(snapshot_payload_bytes)
            payload["row_payload_bytes"] = int(row_payload_bytes)
            hot_payload["decision_row_key"] = str(payload.get("decision_row_key", "") or detail_row_key)
            hot_payload["runtime_snapshot_key"] = str(payload.get("runtime_snapshot_key", "") or "")
            hot_payload["trade_link_key"] = str(payload.get("trade_link_key", "") or "")
            hot_payload["replay_row_key"] = str(payload.get("replay_row_key", "") or hot_payload["decision_row_key"])
            hot_payload["signal_age_sec"] = float(payload.get("signal_age_sec", 0.0) or 0.0)
            hot_payload["bar_age_sec"] = float(payload.get("bar_age_sec", 0.0) or 0.0)
            hot_payload["decision_latency_ms"] = int(payload.get("decision_latency_ms", 0) or 0)
            hot_payload["order_submit_latency_ms"] = int(payload.get("order_submit_latency_ms", 0) or 0)
            hot_payload["missing_feature_count"] = int(payload.get("missing_feature_count", 0) or 0)
            hot_payload["data_completeness_ratio"] = float(payload.get("data_completeness_ratio", 0.0) or 0.0)
            hot_payload["used_fallback_count"] = int(payload.get("used_fallback_count", 0) or 0)
            hot_payload["compatibility_mode"] = str(payload.get("compatibility_mode", "") or "")
            hot_payload["detail_blob_bytes"] = int(detail_blob_bytes)
            hot_payload["snapshot_payload_bytes"] = int(snapshot_payload_bytes)
            hot_payload["row_payload_bytes"] = int(row_payload_bytes)
            hot_payload = {column: hot_payload.get(column, "") for column in cols}
            rollover_result = self._rollover_if_needed(path, cols)
            if rollover_result.get("error") and "WinError 32" not in str(rollover_result.get("error", "")):
                logger.warning(
                    "entry decision rollover skipped: %s",
                    str(rollover_result.get("error", "") or ""),
                )
            is_new = not path.exists()
            detail_path.parent.mkdir(parents=True, exist_ok=True)
            detail_rotation = rotate_entry_decision_detail_if_needed(path)
            if detail_rotation.get("error") and "WinError 32" not in str(detail_rotation.get("error", "")):
                logger.warning(
                    "entry decision detail rotation skipped: %s",
                    str(detail_rotation.get("error", "") or ""),
                )
            with detail_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(detail_record, ensure_ascii=False, separators=(",", ":")) + "\n")
            with path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                if is_new:
                    writer.writeheader()
                writer.writerow(hot_payload)
            return dict(hot_payload)
        except Exception:
            logger.exception("entry decision log append failed")
            return {}

    def record_trace(self, trace: dict) -> None:
        try:
            self.runtime.append_ai_entry_trace(trace)
        except Exception:
            logger.exception("entry trace record failed")
