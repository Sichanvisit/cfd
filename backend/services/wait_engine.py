"""Wait-state classification helpers for entry/exit flows."""

from __future__ import annotations

import json

import pandas as pd

from backend.core.config import Config
from backend.domain.decision_models import WaitState
from backend.services.entry_wait_context_bias_bundle import (
    compact_entry_wait_bias_bundle_v1,
    resolve_entry_wait_bias_bundle_v1,
)
from backend.services.entry_wait_context_contract import (
    build_entry_wait_context_v1,
    compact_entry_wait_context_v1,
    extract_entry_wait_hints_v1,
)
from backend.services.entry_wait_decision_policy import resolve_entry_wait_decision_policy_v1
from backend.services.entry_wait_state_policy_contract import (
    resolve_entry_wait_state_policy_from_context_v1,
)
from backend.services.energy_contract import (
    create_energy_usage_recorder,
    finalize_energy_usage_recorder,
    record_energy_usage,
)
from backend.services.exit_wait_state_input_contract import (
    build_exit_wait_state_input_v1,
    compact_exit_wait_state_input_v1,
)
from backend.services.exit_wait_state_policy import resolve_exit_wait_state_policy_v1
from backend.services.exit_wait_state_rewrite_policy import apply_exit_wait_state_rewrite_v1
from backend.services.exit_wait_state_surface_contract import (
    build_exit_wait_state_surface_v1,
    compact_exit_wait_state_surface_v1,
)
from backend.services.exit_wait_taxonomy_contract import (
    build_exit_wait_taxonomy_v1,
    compact_exit_wait_taxonomy_v1,
)
from backend.services.exit_utility_base_bundle import (
    compact_exit_utility_base_bundle_v1,
    resolve_exit_utility_base_bundle_v1,
)
from backend.services.exit_utility_input_contract import (
    build_exit_utility_input_v1,
    compact_exit_utility_input_v1,
)
from backend.services.exit_recovery_utility_bundle import (
    compact_exit_recovery_utility_bundle_v1,
    resolve_exit_recovery_utility_bundle_v1,
)
from backend.services.exit_reverse_eligibility_policy import (
    compact_exit_reverse_eligibility_v1,
    resolve_exit_reverse_eligibility_v1,
)
from backend.services.exit_utility_scene_bias_policy import (
    compact_exit_utility_scene_bias_bundle_v1,
    resolve_exit_utility_scene_bias_bundle_v1,
)
from backend.services.exit_utility_decision_policy import (
    compact_exit_utility_decision_policy_v1,
    resolve_exit_utility_decision_policy_v1,
)


class WaitEngine:
    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(float(low), min(float(high), float(value)))

    @staticmethod
    def _to_float(value, default: float = 0.0) -> float:
        try:
            return float(pd.to_numeric(value, errors="coerce") or default)
        except Exception:
            return float(default)

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(pd.to_numeric(value, errors="coerce") or default)
        except Exception:
            return int(default)

    @staticmethod
    def _to_str(value, default: str = "") -> str:
        text = str(value or "").strip()
        return text if text else str(default or "")

    @staticmethod
    def _to_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off", ""}:
            return False
        return bool(default)

    @staticmethod
    def _coerce_mapping(value) -> dict:
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str) and value.strip():
            try:
                loaded = json.loads(value)
            except Exception:
                return {}
            if isinstance(loaded, dict):
                return dict(loaded)
        return {}

    @staticmethod
    def _coerce_rows(value) -> list[dict]:
        if not isinstance(value, list):
            return []
        rows: list[dict] = []
        for item in value:
            if isinstance(item, dict):
                rows.append(dict(item))
        return rows

    @classmethod
    def _extract_entry_wait_hints(cls, payload: dict) -> dict:
        return dict(extract_entry_wait_hints_v1(payload))

    @classmethod
    def _build_entry_wait_energy_usage_trace(
        cls,
        *,
        wait_hints: dict,
        state: str,
        reason: str,
        hard_wait: bool,
    ) -> dict:
        recorder = create_energy_usage_recorder(component="WaitEngine.build_entry_wait_state")
        wait_vs_enter_hint = cls._to_str(wait_hints.get("wait_vs_enter_hint", "")).lower()
        action_readiness = cls._to_float(wait_hints.get("action_readiness", 0.0))
        soft_block_active = cls._to_bool(wait_hints.get("soft_block_active", False))
        soft_block_reason = cls._to_str(wait_hints.get("soft_block_reason", ""))
        soft_block_strength = cls._to_float(wait_hints.get("soft_block_strength", 0.0))
        has_action_readiness_hint = cls._to_bool(wait_hints.get("has_action_readiness_hint", False))
        has_wait_vs_enter_hint = cls._to_bool(wait_hints.get("has_wait_vs_enter_hint", False))
        has_soft_block_hint = cls._to_bool(wait_hints.get("has_soft_block_hint", False))

        if has_soft_block_hint and soft_block_active:
            recorder = record_energy_usage(
                recorder,
                branch="helper_soft_block_state",
                consumed_fields=[
                    "consumer_energy_soft_block_active",
                    "consumer_energy_soft_block_reason",
                    "consumer_energy_soft_block_strength",
                ],
                reason=soft_block_reason or "energy_soft_block",
                details={
                    "state": str(state or ""),
                    "reason": str(reason or ""),
                    "hard_wait": bool(hard_wait),
                    "soft_block_strength": round(float(soft_block_strength), 6),
                    "hint_source": str(wait_hints.get("soft_block_hint_source", "") or ""),
                },
            )
        if (
            (has_wait_vs_enter_hint or has_action_readiness_hint)
            and wait_vs_enter_hint == "prefer_wait"
            and action_readiness <= 0.40
        ):
            recorder = record_energy_usage(
                recorder,
                branch="helper_wait_bias_state",
                consumed_fields=[
                    "consumer_energy_action_readiness",
                    "consumer_energy_wait_vs_enter_hint",
                ],
                reason="prefer_wait_low_readiness",
                details={
                    "state": str(state or ""),
                    "reason": str(reason or ""),
                    "hard_wait": bool(hard_wait),
                    "action_readiness": round(float(action_readiness), 6),
                    "hint_source": {
                        "action_readiness": str(wait_hints.get("action_readiness_source", "") or ""),
                        "wait_vs_enter_hint": str(wait_hints.get("wait_vs_enter_hint_source", "") or ""),
                    },
                },
                active=str(state or "").upper() == "HELPER_WAIT",
            )
        if has_soft_block_hint and soft_block_active and soft_block_strength >= 0.75 and wait_vs_enter_hint != "prefer_enter":
            recorder = record_energy_usage(
                recorder,
                branch="helper_soft_block_hard_wait",
                consumed_fields=[
                    "consumer_energy_soft_block_active",
                    "consumer_energy_soft_block_strength",
                    "consumer_energy_wait_vs_enter_hint",
                ],
                reason="helper_soft_block_hard_wait",
                details={
                    "state": str(state or ""),
                    "reason": str(reason or ""),
                    "hard_wait": bool(hard_wait),
                    "soft_block_strength": round(float(soft_block_strength), 6),
                    "wait_vs_enter_hint": str(wait_vs_enter_hint or ""),
                },
                active=bool(hard_wait),
            )
        return finalize_energy_usage_recorder(
            recorder,
            usage_mode=(
                "wait_state_branch_applied"
                if list(recorder.get("branch_records", []) or [])
                else "not_consumed"
            ),
            live_gate_applied=False,
        )

    @classmethod
    def _build_entry_wait_decision_energy_usage_trace(
        cls,
        *,
        wait_metadata: dict,
        state: str,
        selected: bool,
        decision: str,
        enter_value: float,
        wait_value: float,
    ) -> dict:
        recorder = create_energy_usage_recorder(component="WaitEngine.evaluate_entry_wait_decision")
        action_readiness = cls._to_float(wait_metadata.get("action_readiness", 0.0))
        wait_vs_enter_hint = cls._to_str(wait_metadata.get("wait_vs_enter_hint", "")).lower()
        soft_block_active = cls._to_bool(wait_metadata.get("soft_block_active", False))
        soft_block_reason = cls._to_str(wait_metadata.get("soft_block_reason", ""))
        soft_block_strength = cls._to_float(wait_metadata.get("soft_block_strength", 0.0))
        has_action_readiness_hint = cls._to_bool(wait_metadata.get("has_action_readiness_hint", False))
        has_wait_vs_enter_hint = cls._to_bool(wait_metadata.get("has_wait_vs_enter_hint", False))
        has_soft_block_hint = cls._to_bool(wait_metadata.get("has_soft_block_hint", False))

        if has_action_readiness_hint:
            recorder = record_energy_usage(
                recorder,
                branch="action_readiness_utility",
                consumed_fields=["consumer_energy_action_readiness"],
                reason="action_readiness_adjustment",
                details={
                    "state": str(state or ""),
                    "action_readiness": round(float(action_readiness), 6),
                    "hint_source": str(wait_metadata.get("action_readiness_source", "") or ""),
                },
            )
        if has_wait_vs_enter_hint and wait_vs_enter_hint in {"prefer_enter", "prefer_wait"}:
            recorder = record_energy_usage(
                recorder,
                branch=f"wait_vs_enter_hint_{wait_vs_enter_hint}",
                consumed_fields=["consumer_energy_wait_vs_enter_hint"],
                reason="wait_vs_enter_hint_adjustment",
                details={
                    "state": str(state or ""),
                    "wait_vs_enter_hint": str(wait_vs_enter_hint or ""),
                    "hint_source": str(wait_metadata.get("wait_vs_enter_hint_source", "") or ""),
                },
            )
        if has_soft_block_hint and soft_block_active:
            recorder = record_energy_usage(
                recorder,
                branch="soft_block_utility",
                consumed_fields=[
                    "consumer_energy_soft_block_active",
                    "consumer_energy_soft_block_reason",
                    "consumer_energy_soft_block_strength",
                ],
                reason=soft_block_reason or "energy_soft_block",
                details={
                    "state": str(state or ""),
                    "soft_block_strength": round(float(soft_block_strength), 6),
                    "hint_source": str(wait_metadata.get("soft_block_hint_source", "") or ""),
                },
            )
        if decision == "wait_soft_helper_block":
            recorder = record_energy_usage(
                recorder,
                branch="wait_soft_helper_block_decision",
                consumed_fields=[
                    "consumer_energy_soft_block_active",
                    "consumer_energy_wait_vs_enter_hint",
                    "consumer_energy_soft_block_strength",
                ],
                reason="wait_soft_helper_block",
                details={
                    "state": str(state or ""),
                    "selected": bool(selected),
                    "enter_value": round(float(enter_value), 6),
                    "wait_value": round(float(wait_value), 6),
                },
                active=bool(selected),
            )
        elif decision == "wait_soft_helper_bias":
            recorder = record_energy_usage(
                recorder,
                branch="wait_soft_helper_bias_decision",
                consumed_fields=[
                    "consumer_energy_action_readiness",
                    "consumer_energy_wait_vs_enter_hint",
                ],
                reason="wait_soft_helper_bias",
                details={
                    "state": str(state or ""),
                    "selected": bool(selected),
                    "action_readiness": round(float(action_readiness), 6),
                    "enter_value": round(float(enter_value), 6),
                    "wait_value": round(float(wait_value), 6),
                },
                active=bool(selected),
            )
        return finalize_energy_usage_recorder(
            recorder,
            usage_mode=(
                "wait_decision_branch_applied"
                if list(recorder.get("branch_records", []) or [])
                else "not_consumed"
            ),
            live_gate_applied=False,
        )

    @staticmethod
    def _required_side(policy: str) -> str:
        upper = str(policy or "").upper().strip()
        if upper == "BUY_ONLY":
            return "BUY"
        if upper == "SELL_ONLY":
            return "SELL"
        return ""

    @classmethod
    def _extract_state_vector_v2(cls, payload: dict) -> dict:
        state_vector_v2 = payload.get("state_vector_v2", payload.get("state_vector_effective_v1", {}))
        return cls._coerce_mapping(state_vector_v2)

    @classmethod
    def _extract_state_v2_meta(cls, payload: dict) -> tuple[dict, dict]:
        state_vector_v2 = cls._extract_state_vector_v2(payload)
        return state_vector_v2, cls._coerce_mapping(state_vector_v2.get("metadata"))

    @classmethod
    def _extract_belief_state_v1(cls, payload: dict) -> dict:
        belief_state_v1 = payload.get("belief_state_v1", payload.get("belief_state_effective_v1", {}))
        return cls._coerce_mapping(belief_state_v1)

    @classmethod
    def _extract_observe_confirm_v2(cls, payload: dict) -> dict:
        return cls._coerce_mapping(payload.get("observe_confirm_v2", payload.get("observe_confirm", {})))

    @classmethod
    def build_entry_wait_state_from_row(cls, *, symbol: str = "", row: dict | None = None) -> WaitState:
        payload = dict(row or {})
        wait_context_v1 = build_entry_wait_context_v1(symbol=symbol, payload=payload)
        identity_context = cls._coerce_mapping(wait_context_v1.get("identity"))
        reason_context = cls._coerce_mapping(wait_context_v1.get("reasons"))
        market_context = cls._coerce_mapping(wait_context_v1.get("market"))
        setup_context = cls._coerce_mapping(wait_context_v1.get("setup"))
        score_context = cls._coerce_mapping(wait_context_v1.get("scores"))
        threshold_context = cls._coerce_mapping(wait_context_v1.get("thresholds"))
        helper_hint_context = cls._coerce_mapping(wait_context_v1.get("helper_hints"))

        symbol = cls._to_str(identity_context.get("symbol", symbol or payload.get("symbol", "")))
        wait_score = cls._to_float(score_context.get("wait_score", 0.0))
        wait_conflict = cls._to_float(score_context.get("wait_conflict", 0.0))
        wait_noise = cls._to_float(score_context.get("wait_noise", 0.0))
        wait_penalty = cls._to_float(score_context.get("wait_penalty", 0.0))
        blocked_by = cls._to_str(reason_context.get("blocked_by", ""))
        action_none_reason = cls._to_str(reason_context.get("action_none_reason", ""))
        action = cls._to_str(identity_context.get("action", "")).upper()
        box_state = cls._to_str(market_context.get("box_state", "UNKNOWN"), "UNKNOWN").upper()
        bb_state = cls._to_str(market_context.get("bb_state", "UNKNOWN"), "UNKNOWN").upper()
        observe_reason = cls._to_str(reason_context.get("observe_reason", ""))
        core_allowed_action = cls._to_str(identity_context.get("core_allowed_action", "NONE"), "NONE").upper()
        preflight_allowed_action = cls._to_str(
            identity_context.get("preflight_allowed_action", "BOTH"),
            "BOTH",
        ).upper()
        setup_status = cls._to_str(setup_context.get("status", "pending"), "pending").upper()
        setup_reason = cls._to_str(setup_context.get("reason", ""))
        setup_trigger_state = cls._to_str(setup_context.get("trigger_state", "UNKNOWN"), "UNKNOWN").upper()
        wait_soft = float(threshold_context.get("base_soft_threshold", 45.0))
        wait_hard = float(threshold_context.get("base_hard_threshold", 70.0))
        bias_bundle_v1 = resolve_entry_wait_bias_bundle_v1(wait_context_v1)
        state_wait_bias = cls._coerce_mapping(bias_bundle_v1.get("state_wait_bias_v1"))
        belief_wait_bias = cls._coerce_mapping(bias_bundle_v1.get("belief_wait_bias_v1"))
        edge_pair_wait_bias = cls._coerce_mapping(bias_bundle_v1.get("edge_pair_wait_bias_v1"))
        symbol_probe_temperament = cls._coerce_mapping(bias_bundle_v1.get("symbol_probe_temperament_v1"))
        threshold_adjustment_v1 = cls._coerce_mapping(bias_bundle_v1.get("threshold_adjustment_v1"))
        compact_bias_bundle_v1 = compact_entry_wait_bias_bundle_v1(bias_bundle_v1)
        wait_soft = float(threshold_adjustment_v1.get("effective_soft_threshold", wait_soft))
        wait_hard = float(threshold_adjustment_v1.get("effective_hard_threshold", wait_hard))
        threshold_context["base_soft_threshold"] = float(
            threshold_adjustment_v1.get("base_soft_threshold", threshold_context.get("base_soft_threshold", wait_soft))
        )
        threshold_context["base_hard_threshold"] = float(
            threshold_adjustment_v1.get("base_hard_threshold", threshold_context.get("base_hard_threshold", wait_hard))
        )
        threshold_context["effective_soft_threshold"] = float(wait_soft)
        threshold_context["effective_hard_threshold"] = float(wait_hard)
        wait_context_v1["thresholds"] = dict(threshold_context)
        wait_context_v1["bias"] = {
            "state_wait_bias_v1": dict(state_wait_bias),
            "belief_wait_bias_v1": dict(belief_wait_bias),
            "edge_pair_wait_bias_v1": dict(edge_pair_wait_bias),
            "symbol_probe_temperament_v1": dict(symbol_probe_temperament),
            "threshold_adjustment_v1": dict(threshold_adjustment_v1),
            "bundle_summary_v1": dict(compact_bias_bundle_v1),
        }
        wait_hints = dict(helper_hint_context)
        action_readiness = float(wait_hints["action_readiness"])
        has_action_readiness_hint = bool(wait_hints["has_action_readiness_hint"])
        action_readiness_source = str(wait_hints["action_readiness_source"])
        wait_vs_enter_hint = str(wait_hints["wait_vs_enter_hint"])
        has_wait_vs_enter_hint = bool(wait_hints["has_wait_vs_enter_hint"])
        wait_vs_enter_hint_source = str(wait_hints["wait_vs_enter_hint_source"])
        soft_block_active = bool(wait_hints["soft_block_active"])
        soft_block_reason = str(wait_hints["soft_block_reason"])
        soft_block_strength = float(wait_hints["soft_block_strength"])
        has_soft_block_hint = bool(wait_hints["has_soft_block_hint"])
        soft_block_hint_source = str(wait_hints["soft_block_hint_source"])
        policy_hard_block_active = bool(wait_hints["policy_hard_block_active"])
        policy_suppressed = bool(wait_hints["policy_suppressed"])
        policy_block_layer = str(wait_hints["policy_block_layer"])
        policy_block_effect = str(wait_hints["policy_block_effect"])
        state_policy_resolution_v1 = resolve_entry_wait_state_policy_from_context_v1(wait_context_v1)
        state_policy = cls._coerce_mapping(state_policy_resolution_v1.get("entry_wait_state_policy_v1"))
        compact_state_policy_input_v1 = cls._coerce_mapping(
            state_policy_resolution_v1.get("compact_entry_wait_state_policy_input_v1")
        )
        state = str(state_policy.get("state", "NONE"))
        reason = str(state_policy.get("reason", ""))
        hard_wait = bool(state_policy.get("hard_wait", False))
        btc_lower_strong_score_soft_wait = bool(state_policy.get("btc_lower_strong_score_soft_wait", False))
        xau_second_support_probe = bool(state_policy.get("xau_second_support_probe", False))
        xau_upper_sell_probe = bool(state_policy.get("xau_upper_sell_probe", False))
        wait_context_v1["policy"] = {
            "state": str(state or ""),
            "reason": str(reason or ""),
            "hard_wait": bool(hard_wait),
            "btc_lower_strong_score_soft_wait": bool(btc_lower_strong_score_soft_wait),
            "xau_second_support_probe": bool(xau_second_support_probe),
            "xau_upper_sell_probe": bool(xau_upper_sell_probe),
            "entry_wait_state_policy_input_v1": dict(compact_state_policy_input_v1),
            "entry_wait_state_policy_v1": dict(state_policy),
        }
        compact_wait_context_v1 = compact_entry_wait_context_v1(wait_context_v1)
        wait_energy_usage_trace_v1 = cls._build_entry_wait_energy_usage_trace(
            wait_hints=wait_hints,
            state=str(state or ""),
            reason=str(reason or ""),
            hard_wait=bool(hard_wait),
        )

        return WaitState(
            phase="entry",
            state=state,
            hard_wait=bool(hard_wait),
            score=float(wait_score),
            conflict=float(wait_conflict),
            noise=float(wait_noise),
            penalty=float(wait_penalty),
            reason=str(reason),
            metadata={
                "symbol": str(symbol),
                "box_state": str(box_state),
                "bb_state": str(bb_state),
                "observe_reason": str(observe_reason),
                "blocked_by": str(blocked_by),
                "action_none_reason": str(action_none_reason),
                "reason_split_v1": {
                    "observe_reason": str(observe_reason),
                    "blocked_by": str(blocked_by),
                    "action_none_reason": str(action_none_reason),
                },
                "action": str(action),
                "core_allowed_action": str(core_allowed_action),
                "preflight_allowed_action": str(preflight_allowed_action),
                "setup_status": str(setup_status),
                "setup_reason": str(setup_reason),
                "setup_trigger_state": str(setup_trigger_state),
                "wait_soft_threshold": float(wait_soft),
                "wait_hard_threshold": float(wait_hard),
                "btc_lower_strong_score_soft_wait": bool(btc_lower_strong_score_soft_wait),
                "action_readiness": float(action_readiness),
                "has_action_readiness_hint": bool(has_action_readiness_hint),
                "action_readiness_source": str(action_readiness_source),
                "wait_vs_enter_hint": str(wait_vs_enter_hint),
                "has_wait_vs_enter_hint": bool(has_wait_vs_enter_hint),
                "wait_vs_enter_hint_source": str(wait_vs_enter_hint_source),
                "soft_block_active": bool(soft_block_active),
                "soft_block_reason": str(soft_block_reason),
                "soft_block_strength": float(soft_block_strength),
                "has_soft_block_hint": bool(has_soft_block_hint),
                "soft_block_hint_source": str(soft_block_hint_source),
                "policy_hard_block_active": bool(policy_hard_block_active),
                "policy_suppressed": bool(policy_suppressed),
                "policy_block_layer": str(policy_block_layer),
                "policy_block_effect": str(policy_block_effect),
                "xau_second_support_probe": bool(xau_second_support_probe),
                "xau_upper_sell_probe": bool(xau_upper_sell_probe),
                "entry_wait_state_policy_input_v1": dict(compact_state_policy_input_v1),
                "entry_wait_state_policy_v1": dict(state_policy),
                "entry_wait_context_v1": dict(compact_wait_context_v1),
                "entry_wait_bias_bundle_v1": dict(compact_bias_bundle_v1),
                "entry_wait_energy_usage_trace_v1": dict(wait_energy_usage_trace_v1 or {}),
                "state_wait_bias_v1": dict(state_wait_bias),
                "belief_wait_bias_v1": dict(belief_wait_bias),
                "edge_pair_wait_bias_v1": dict(edge_pair_wait_bias),
                "symbol_probe_temperament_v1": dict(symbol_probe_temperament),
            },
        )

    @classmethod
    def build_exit_wait_state(
        cls,
        *,
        symbol: str = "",
        trade_ctx: dict | None = None,
        stage_inputs: dict | None = None,
        adverse_risk: bool = False,
        tf_confirm: bool = False,
        chosen_stage: str = "",
        policy_stage: str = "",
        confirm_needed: int = 0,
        exit_signal_score: int = 0,
        score_gap: int = 0,
        detail: dict | None = None,
    ) -> WaitState:
        trade_ctx = dict(trade_ctx or {})
        stage_inputs = dict(stage_inputs or {})
        detail = dict(detail or {})
        exit_wait_state_input_v1 = build_exit_wait_state_input_v1(
            symbol=symbol,
            trade_ctx=trade_ctx,
            stage_inputs=stage_inputs,
            adverse_risk=adverse_risk,
            tf_confirm=tf_confirm,
            chosen_stage=chosen_stage,
            policy_stage=policy_stage,
            confirm_needed=confirm_needed,
            exit_signal_score=exit_signal_score,
            score_gap=score_gap,
            detail=detail,
        )
        identity_context = cls._coerce_mapping(exit_wait_state_input_v1.get("identity"))
        market_context = cls._coerce_mapping(exit_wait_state_input_v1.get("market"))
        risk_context = cls._coerce_mapping(exit_wait_state_input_v1.get("risk"))
        policy_context = cls._coerce_mapping(exit_wait_state_input_v1.get("policy"))
        bias_context = cls._coerce_mapping(exit_wait_state_input_v1.get("bias"))
        detail_context = cls._coerce_mapping(exit_wait_state_input_v1.get("detail"))
        context_context = cls._coerce_mapping(exit_wait_state_input_v1.get("context"))

        symbol = cls._to_str(identity_context.get("symbol", symbol), symbol).upper()
        profit = cls._to_float(risk_context.get("profit", 0.0))
        peak_profit = cls._to_float(risk_context.get("peak_profit", profit), profit)
        giveback = cls._to_float(risk_context.get("giveback", max(0.0, peak_profit - profit)), 0.0)
        duration_sec = cls._to_float(risk_context.get("duration_sec", 0.0))
        regime_now = cls._to_str(market_context.get("regime_now", "UNKNOWN"), "UNKNOWN").upper()
        current_box_state = cls._to_str(market_context.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper()
        current_bb_state = cls._to_str(market_context.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper()
        reached_opposite_edge = bool(market_context.get("reached_opposite_edge", False))
        entry_direction = cls._to_str(identity_context.get("entry_direction", ""), "").upper()

        allow_wait_be = bool(policy_context.get("allow_wait_be", True))
        allow_wait_tp1 = bool(policy_context.get("allow_wait_tp1", False))
        prefer_reverse = bool(policy_context.get("prefer_reverse", False))
        recovery_be_max_loss = max(0.05, cls._to_float(policy_context.get("recovery_be_max_loss", 0.0), 0.0))
        recovery_tp1_max_loss = max(0.0, cls._to_float(policy_context.get("recovery_tp1_max_loss", 0.0), 0.0))
        recovery_wait_max_seconds = max(0.0, cls._to_float(policy_context.get("recovery_wait_max_seconds", 0.0), 0.0))
        reverse_gap = max(1, cls._to_int(policy_context.get("reverse_score_gap", 1), 1))
        state_execution_bias = cls._coerce_mapping(bias_context.get("state_exit_bias_v1"))
        belief_execution_bias = cls._coerce_mapping(bias_context.get("belief_execution_overrides_v1"))
        symbol_edge_execution_bias = cls._coerce_mapping(bias_context.get("symbol_edge_execution_overrides_v1"))
        compact_exit_context_v1 = cls._coerce_mapping(context_context.get("exit_manage_context_v1"))
        state_policy = resolve_exit_wait_state_policy_v1(exit_wait_state_input_v1)
        state_rewrite = apply_exit_wait_state_rewrite_v1(
            exit_wait_state_input_v1=exit_wait_state_input_v1,
            base_state_policy_v1=state_policy,
        )
        state = cls._to_str(state_rewrite.get("state", "NONE"), "NONE").upper()
        reason = cls._to_str(state_rewrite.get("reason", ""), "")
        hard_wait = bool(state_rewrite.get("hard_wait", False))

        score = max(0.0, abs(float(score_gap))) if state in {"REVERSAL_CONFIRM", "REVERSE_READY"} else max(0.0, giveback)
        penalty = max(0.0, abs(min(0.0, profit))) if state in {"RECOVERY_BE", "RECOVERY_TP1", "CUT_IMMEDIATE"} else 0.0
        exit_wait_state_surface_v1 = compact_exit_wait_state_surface_v1(
            build_exit_wait_state_surface_v1(
                exit_wait_state_input_v1=exit_wait_state_input_v1,
                exit_wait_state_policy_v1=state_policy,
                exit_wait_state_rewrite_v1=state_rewrite,
                score=float(score),
                penalty=float(penalty),
                conflict=0.0,
                noise=0.0,
            )
        )
        return WaitState(
            phase="exit",
            state=state,
            hard_wait=bool(hard_wait),
            score=float(score),
            conflict=0.0,
            noise=0.0,
            penalty=float(penalty),
            reason=str(reason),
            metadata={
                "symbol": str(symbol),
                "profit": float(profit),
                "peak_profit": float(peak_profit),
                "giveback": float(giveback),
                "duration_sec": float(duration_sec),
                "tf_confirm": bool(tf_confirm),
                "adverse_risk": bool(adverse_risk),
                "chosen_stage": str(chosen_stage),
                "policy_stage": str(policy_stage),
                "confirm_needed": int(confirm_needed),
                "exit_signal_score": int(exit_signal_score),
                "score_gap": int(score_gap),
                "recovery_be_max_loss": float(recovery_be_max_loss),
                "recovery_tp1_max_loss": float(recovery_tp1_max_loss),
                "recovery_wait_max_seconds": float(recovery_wait_max_seconds),
                "recovery_policy_id": str(policy_context.get("recovery_policy_id", "")),
                "management_profile_id": str(policy_context.get("management_profile_id", "")),
                "invalidation_id": str(policy_context.get("invalidation_id", "")),
                "entry_setup_id": str(policy_context.get("entry_setup_id", "")),
                "allow_wait_be": bool(allow_wait_be),
                "allow_wait_tp1": bool(allow_wait_tp1),
                "prefer_reverse": bool(prefer_reverse),
                "reverse_score_gap": int(reverse_gap),
                "state_execution_overrides_v1": dict(bias_context.get("state_execution_overrides_v1", {}) or {}),
                "state_exit_bias_v1": dict(state_execution_bias),
                "belief_execution_overrides_v1": dict(belief_execution_bias),
                "symbol_edge_execution_overrides_v1": dict(symbol_edge_execution_bias),
                "exit_manage_context_v1": dict(compact_exit_context_v1),
                "exit_wait_state_input_v1": dict(compact_exit_wait_state_input_v1(exit_wait_state_input_v1)),
                "exit_wait_state_rewrite_v1": dict(state_rewrite),
                "exit_wait_state_surface_v1": dict(exit_wait_state_surface_v1),
                "regime_now": str(regime_now),
                "current_box_state": str(current_box_state),
                "current_bb_state": str(current_bb_state),
                "entry_direction": str(entry_direction),
                "route_txt": str(detail_context.get("route_txt", detail.get("route_txt", ""))),
            },
        )

    @classmethod
    def evaluate_entry_wait_decision(
        cls,
        *,
        symbol: str,
        row: dict | None,
        blocked_reason: str,
        raw_entry_score: float,
        effective_threshold: float,
        core_score: float = 0.0,
        utility_u: float | None = None,
        utility_u_min: float | None = None,
    ) -> dict:
        wait_state = cls.build_entry_wait_state_from_row(symbol=symbol, row=row)
        wait_metadata = dict(wait_state.metadata or {})
        decision_policy = resolve_entry_wait_decision_policy_v1(
            blocked_reason=blocked_reason,
            raw_entry_score=raw_entry_score,
            effective_threshold=effective_threshold,
            core_score=core_score,
            utility_u=utility_u,
            utility_u_min=utility_u_min,
            wait_state_state=str(wait_state.state or "NONE"),
            wait_state_score=float(wait_state.score),
            wait_state_penalty=float(wait_state.penalty),
            wait_state_hard_wait=bool(wait_state.hard_wait),
            wait_metadata=wait_metadata,
        )
        selected = bool(decision_policy.get("selected", False))
        decision = str(decision_policy.get("decision", "skip"))
        enter_value = float(decision_policy.get("enter_value", 0.0))
        wait_value = float(decision_policy.get("wait_value", 0.0))

        wait_decision_energy_usage_trace_v1 = cls._build_entry_wait_decision_energy_usage_trace(
            wait_metadata=wait_metadata,
            state=str(wait_state.state or ""),
            selected=bool(selected),
            decision=str(decision or ""),
            enter_value=float(enter_value),
            wait_value=float(wait_value),
        )
        wait_metadata["entry_wait_decision_energy_usage_trace_v1"] = dict(
            wait_decision_energy_usage_trace_v1 or {}
        )
        wait_state.metadata = dict(wait_metadata)

        return {
            "wait_state": wait_state,
            "selected": bool(selected),
            "decision": str(decision),
            "enter_value": round(float(enter_value), 6),
            "wait_value": round(float(wait_value), 6),
            "blocked_reason": str(blocked_reason),
            "policy_hint_applied": bool(decision_policy.get("policy_hint_applied", False)),
            "energy_hint_applied": bool(decision_policy.get("energy_hint_applied", False)),
            "entry_wait_energy_usage_trace_v1": dict(
                wait_state.metadata.get("entry_wait_energy_usage_trace_v1", {}) or {}
            ),
            "entry_wait_decision_energy_usage_trace_v1": dict(
                wait_decision_energy_usage_trace_v1 or {}
            ),
        }

    @classmethod
    def evaluate_exit_utility_decision(
        cls,
        *,
        symbol: str,
        wait_state: WaitState,
        stage_inputs: dict | None,
        exit_predictions: dict | None,
        wait_predictions: dict | None,
        recovery_predictions: dict | None = None,
        exit_profile_id: str = "",
        roundtrip_cost: float = 0.0,
    ) -> dict:
        stage_inputs = dict(stage_inputs or {})
        exit_predictions = dict(exit_predictions or {})
        wait_predictions = dict(wait_predictions or {})
        recovery_predictions = dict(recovery_predictions or {})
        exit_utility_input_v1 = build_exit_utility_input_v1(
            symbol=symbol,
            wait_state=wait_state,
            stage_inputs=stage_inputs,
            exit_predictions=exit_predictions,
            wait_predictions=wait_predictions,
            exit_profile_id=exit_profile_id,
            roundtrip_cost=roundtrip_cost,
        )
        compact_exit_utility_input_v1_value = compact_exit_utility_input_v1(
            exit_utility_input_v1
        )
        exit_utility_base_bundle_v1 = resolve_exit_utility_base_bundle_v1(
            exit_utility_input_v1=exit_utility_input_v1
        )
        compact_exit_utility_base_bundle_v1_value = compact_exit_utility_base_bundle_v1(
            exit_utility_base_bundle_v1
        )

        utility_identity = dict(exit_utility_input_v1.get("identity", {}) or {})
        utility_market = dict(exit_utility_input_v1.get("market", {}) or {})
        utility_risk = dict(exit_utility_input_v1.get("risk", {}) or {})
        utility_policy = dict(exit_utility_input_v1.get("policy", {}) or {})
        utility_bias = dict(exit_utility_input_v1.get("bias", {}) or {})
        base_inputs = dict(exit_utility_base_bundle_v1.get("inputs", {}) or {})
        base_utilities = dict(exit_utility_base_bundle_v1.get("utilities", {}) or {})

        profit = cls._to_float(utility_risk.get("profit", 0.0))
        peak_profit = cls._to_float(utility_risk.get("peak_profit", profit))
        giveback = cls._to_float(utility_risk.get("giveback", max(0.0, peak_profit - profit)))
        score_gap = abs(cls._to_float(utility_risk.get("score_gap", 0.0)))
        adverse_risk = bool(utility_risk.get("adverse_risk", False))
        duration_sec = cls._to_float(utility_risk.get("duration_sec", 0.0))
        state = cls._to_str(utility_identity.get("state", "NONE"), "NONE").upper()
        exit_profile_id = cls._to_str(utility_identity.get("exit_profile_id", ""), "").lower()
        symbol_u = cls._to_str(utility_identity.get("symbol", symbol), "").upper()
        entry_setup_id = cls._to_str(utility_identity.get("entry_setup_id", ""), "").lower()
        regime_now = cls._to_str(utility_market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper()
        current_box_state = cls._to_str(
            utility_market.get("current_box_state", "UNKNOWN"),
            "UNKNOWN",
        ).upper()
        current_bb_state = cls._to_str(
            utility_market.get("current_bb_state", "UNKNOWN"),
            "UNKNOWN",
        ).upper()
        entry_direction = cls._to_str(utility_identity.get("entry_direction", ""), "").upper()
        state_execution_bias = dict(
            utility_bias.get("state_execution_bias_v1", {}) or {}
        )
        locked_profit = cls._to_float(base_inputs.get("locked_profit", max(0.0, profit)))
        reverse_edge = cls._to_float(base_inputs.get("reverse_edge", 0.10))
        utility_exit_now = cls._to_float(base_utilities.get("utility_exit_now", 0.0))
        utility_hold = cls._to_float(base_utilities.get("utility_hold", 0.0))
        utility_reverse = cls._to_float(base_utilities.get("utility_reverse", 0.0))
        utility_wait_exit = cls._to_float(base_utilities.get("utility_wait_exit", 0.0))
        if bool(state_execution_bias.get("aligned_with_entry", False)):
            utility_hold += 0.08 + float(state_execution_bias.get("hold_bias", 0.0))
            utility_wait_exit += 0.04 + float(state_execution_bias.get("wait_bias", 0.0))
            utility_exit_now -= 0.06
        if bool(state_execution_bias.get("countertrend_with_entry", False)):
            utility_exit_now += 0.08 + min(0.10, float(state_execution_bias.get("exit_pressure", 0.0)))
            utility_hold -= 0.08
            utility_wait_exit -= 0.05
        if bool(state_execution_bias.get("prefer_hold_through_green", False)) and state in {"GREEN_CLOSE", "ACTIVE"} and profit > 0.0 and not adverse_risk:
            utility_hold += 0.14 + float(state_execution_bias.get("hold_bias", 0.0))
            utility_wait_exit += 0.08 + float(state_execution_bias.get("wait_bias", 0.0))
            utility_exit_now -= 0.14
        if bool(state_execution_bias.get("prefer_fast_cut", False)):
            exit_pressure = float(state_execution_bias.get("exit_pressure", 0.0))
            utility_exit_now += 0.12 + exit_pressure
            utility_hold -= 0.12 + min(0.08, exit_pressure * 0.60)
            utility_wait_exit -= 0.08 + min(0.06, exit_pressure * 0.45)
        allow_wait_be = bool(utility_policy.get("allow_wait_be", True))
        allow_wait_tp1 = bool(utility_policy.get("allow_wait_tp1", False))
        prefer_reverse = bool(utility_policy.get("prefer_reverse", False))
        recovery_policy_id = str(utility_policy.get("recovery_policy_id", "") or "")
        exit_utility_scene_bias_bundle_v1 = resolve_exit_utility_scene_bias_bundle_v1(
            exit_utility_input_v1=exit_utility_input_v1,
            exit_utility_base_bundle_v1=exit_utility_base_bundle_v1,
        )
        compact_exit_utility_scene_bias_bundle_v1_value = (
            compact_exit_utility_scene_bias_bundle_v1(exit_utility_scene_bias_bundle_v1)
        )
        scene_flags = dict(exit_utility_scene_bias_bundle_v1.get("flags", {}) or {})
        scene_utility_deltas = dict(
            exit_utility_scene_bias_bundle_v1.get("utility_deltas", {}) or {}
        )
        scene_recovery_overrides = dict(
            exit_utility_scene_bias_bundle_v1.get("recovery_overrides", {}) or {}
        )
        range_middle_observe = bool(scene_flags.get("range_middle_observe", False))
        reached_opposite_edge = bool(scene_flags.get("reached_opposite_edge", False))
        lower_reversal_hold_bias = bool(
            scene_flags.get("lower_reversal_hold_bias", False)
        )
        xau_lower_edge_to_edge_hold_bias = bool(
            scene_flags.get("xau_lower_edge_to_edge_hold_bias", False)
        )

        # Mean-reversion reversal entries should protect green quickly instead of
        # letting a small winner degrade into a loser.
        if exit_profile_id == "tight_protect" and profit > 0.0:
            tight_exit_bonus = 0.18 + min(0.20, locked_profit * 0.08)
            tight_hold_penalty = 0.22 + min(0.20, giveback * 0.35)
            tight_wait_penalty = 0.12
            if lower_reversal_hold_bias:
                tight_exit_bonus *= 0.35
                tight_hold_penalty *= 0.30
                tight_wait_penalty *= 0.25
            utility_exit_now += tight_exit_bonus
            utility_hold -= tight_hold_penalty
            utility_wait_exit -= tight_wait_penalty
            if (not lower_reversal_hold_bias) and (
                state == "GREEN_CLOSE" or giveback > max(0.05, locked_profit * 0.20) or score_gap <= 0.0
            ):
                utility_exit_now += 0.08
                utility_hold -= 0.25
                utility_wait_exit -= 0.18

        nas_upper_hold_bias = bool(
            symbol_u == "NAS100"
            and entry_direction == "SELL"
            and recovery_policy_id in {"range_upper_reversal_sell_nas_balanced", "breakout_retest_nas_balanced"}
            and float(profit) > 0.0
            and not bool(adverse_risk)
            and not bool(reached_opposite_edge)
        )
        btc_lower_hold_bias = bool(
            symbol_u == "BTCUSD"
            and entry_direction == "BUY"
            and recovery_policy_id == "range_lower_reversal_buy_btc_balanced"
            and (float(profit) > 0.0 or float(peak_profit) >= 0.12)
            and not bool(adverse_risk)
            and not bool(reached_opposite_edge)
            and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
            and current_bb_state in {"LOWER_EDGE", "BREAKDOWN", "MID", "UNKNOWN"}
            and float(giveback) <= max(0.22, float(max(peak_profit, profit, 0.0)) * 0.92)
        )
        btc_lower_mid_noise_hold_bias = bool(
            symbol_u == "BTCUSD"
            and entry_direction == "BUY"
            and recovery_policy_id == "range_lower_reversal_buy_btc_balanced"
            and not bool(adverse_risk)
            and not bool(reached_opposite_edge)
            and regime_now in {"RANGE", "UNKNOWN"}
            and current_box_state in {"LOWER", "BELOW", "MIDDLE"}
            and current_bb_state in {"LOWER_EDGE", "BREAKDOWN", "MID", "UNKNOWN"}
            and float(peak_profit) >= 0.06
            and float(giveback) <= max(0.20, float(max(peak_profit, profit, 0.0)) * 0.90)
        )
        exit_recovery_utility_bundle_v1 = resolve_exit_recovery_utility_bundle_v1(
            exit_utility_input_v1=exit_utility_input_v1,
            exit_utility_base_bundle_v1=exit_utility_base_bundle_v1,
            recovery_predictions=recovery_predictions,
            lower_reversal_hold_bias=lower_reversal_hold_bias,
        )
        compact_exit_recovery_utility_bundle_v1_value = (
            compact_exit_recovery_utility_bundle_v1(exit_recovery_utility_bundle_v1)
        )
        recovery_probabilities = dict(
            exit_recovery_utility_bundle_v1.get("probabilities", {}) or {}
        )
        recovery_gating = dict(exit_recovery_utility_bundle_v1.get("gating", {}) or {})
        recovery_utilities = dict(
            exit_recovery_utility_bundle_v1.get("utilities", {}) or {}
        )

        p_recover_be = cls._to_float(recovery_probabilities.get("p_recover_be", 0.10))
        p_recover_tp1 = cls._to_float(recovery_probabilities.get("p_recover_tp1", 0.08))
        p_deeper_loss = cls._to_float(recovery_probabilities.get("p_deeper_loss", 0.30))
        p_reverse_valid = cls._to_float(recovery_probabilities.get("p_reverse_valid", 0.25))
        u_cut_now = cls._to_float(recovery_utilities.get("u_cut_now", 0.0))
        u_wait_be = cls._to_float(recovery_utilities.get("u_wait_be", -999.0))
        u_wait_tp1 = cls._to_float(recovery_utilities.get("u_wait_tp1", -999.0))
        u_reverse_candidate = cls._to_float(
            recovery_utilities.get("u_reverse_candidate", 0.0)
        )
        tight_protect_green_disable = bool(
            recovery_gating.get("tight_protect_green_disable", False)
        )
        # Tight-protect exits should not let a green trade round-trip back through
        # breakeven recovery logic once the trade already proved it can pay.
        if tight_protect_green_disable:
            utility_exit_now += 0.20 + min(0.25, float(peak_profit) * 0.10)
            utility_hold -= 0.28 + min(0.25, float(giveback) * 0.40)
            utility_wait_exit -= 0.22
        utility_exit_now += cls._to_float(
            scene_utility_deltas.get("utility_exit_now_delta", 0.0)
        )
        utility_hold += cls._to_float(
            scene_utility_deltas.get("utility_hold_delta", 0.0)
        )
        utility_wait_exit += cls._to_float(
            scene_utility_deltas.get("utility_wait_exit_delta", 0.0)
        )
        if bool(scene_recovery_overrides.get("force_disable_wait_be", False)):
            u_wait_be = -999.0
        if bool(scene_recovery_overrides.get("force_disable_wait_tp1", False)):
            u_wait_tp1 = -999.0
        btc_upper_tight = bool(scene_flags.get("btc_upper_tight", False))
        btc_upper_support_bounce_exit = bool(
            scene_flags.get("btc_upper_support_bounce_exit", False)
        )
        nas_upper_hold_bias = bool(scene_flags.get("nas_upper_hold_bias", False))
        btc_lower_hold_bias = bool(scene_flags.get("btc_lower_hold_bias", False))
        btc_lower_mid_noise_hold_bias = bool(
            scene_flags.get("btc_lower_mid_noise_hold_bias", False)
        )
        symbol_edge_completion_bias = dict(
            exit_utility_scene_bias_bundle_v1.get("symbol_edge_completion_bias_v1", {})
            or {}
        )
        exit_reverse_eligibility_v1 = resolve_exit_reverse_eligibility_v1(
            exit_utility_input_v1=exit_utility_input_v1,
            exit_recovery_utility_bundle_v1=exit_recovery_utility_bundle_v1,
        )
        compact_exit_reverse_eligibility_v1_value = compact_exit_reverse_eligibility_v1(
            exit_reverse_eligibility_v1
        )
        reverse_result = dict(exit_reverse_eligibility_v1.get("result", {}) or {})
        reverse_eligible = bool(reverse_result.get("reverse_eligible", False))
        u_reverse = cls._to_float(reverse_result.get("u_reverse", u_reverse_candidate))

        exit_utility_decision_policy_v1 = resolve_exit_utility_decision_policy_v1(
            exit_utility_input_v1=exit_utility_input_v1,
            utility_candidates_v1={
                "utility_exit_now": float(utility_exit_now),
                "utility_hold": float(utility_hold),
                "utility_reverse": float(utility_reverse),
                "utility_wait_exit": float(utility_wait_exit),
                "u_cut_now": float(u_cut_now),
                "u_wait_be": float(u_wait_be),
                "u_wait_tp1": float(u_wait_tp1),
                "u_reverse": float(u_reverse),
            },
            exit_utility_scene_bias_bundle_v1=exit_utility_scene_bias_bundle_v1,
        )
        compact_exit_utility_decision_policy_v1_value = (
            compact_exit_utility_decision_policy_v1(exit_utility_decision_policy_v1)
        )
        decision_result = dict(
            exit_utility_decision_policy_v1.get("result", {}) or {}
        )
        taxonomy_input = dict(
            exit_utility_decision_policy_v1.get("taxonomy_input", {}) or {}
        )
        winner = str(decision_result.get("winner", "") or "")
        winner_value = cls._to_float(decision_result.get("winner_value", 0.0))
        decision_reason = str(decision_result.get("decision_reason", "") or "")
        wait_selected = bool(decision_result.get("wait_selected", False))
        wait_decision = str(decision_result.get("wait_decision", "") or "")

        exit_wait_taxonomy_v1 = compact_exit_wait_taxonomy_v1(
            build_exit_wait_taxonomy_v1(
                wait_state=wait_state,
                utility_result=dict(taxonomy_input),
            )
        )

        return {
            "wait_state": str(state),
            "wait_selected": bool(wait_selected),
            "wait_decision": str(wait_decision),
            "utility_exit_now": round(float(utility_exit_now), 6),
            "utility_hold": round(float(utility_hold), 6),
            "utility_reverse": round(float(utility_reverse), 6),
            "utility_wait_exit": round(float(utility_wait_exit), 6),
            "u_cut_now": round(float(u_cut_now), 6),
            "u_wait_be": round(float(u_wait_be), 6),
            "u_wait_tp1": round(float(u_wait_tp1), 6),
            "u_reverse": round(float(u_reverse), 6),
            "p_recover_be": round(float(p_recover_be), 6),
            "p_recover_tp1": round(float(p_recover_tp1), 6),
            "p_deeper_loss": round(float(p_deeper_loss), 6),
            "p_reverse_valid": round(float(p_reverse_valid), 6),
            "winner": str(winner),
            "winner_value": round(float(winner_value), 6),
            "decision_reason": str(decision_reason),
            "profit": round(float(profit), 6),
            "giveback": round(float(giveback), 6),
            "score_gap": round(float(score_gap), 6),
            "regime_now": str(regime_now),
            "current_box_state": str(current_box_state),
            "current_bb_state": str(current_bb_state),
            "entry_direction": str(entry_direction),
            "entry_setup_id": str(entry_setup_id),
            "symbol": str(symbol_u),
            "exit_wait_taxonomy_v1": dict(exit_wait_taxonomy_v1),
            "exit_utility_input_v1": dict(compact_exit_utility_input_v1_value),
            "exit_utility_base_bundle_v1": dict(
                compact_exit_utility_base_bundle_v1_value
            ),
            "exit_recovery_utility_bundle_v1": dict(
                compact_exit_recovery_utility_bundle_v1_value
            ),
            "exit_reverse_eligibility_v1": dict(
                compact_exit_reverse_eligibility_v1_value
            ),
            "exit_utility_scene_bias_bundle_v1": dict(
                compact_exit_utility_scene_bias_bundle_v1_value
            ),
            "exit_utility_decision_policy_v1": dict(
                compact_exit_utility_decision_policy_v1_value
            ),
            "btc_upper_tight": bool(btc_upper_tight),
            "btc_upper_support_bounce_exit": bool(btc_upper_support_bounce_exit),
            "btc_lower_hold_bias": bool(btc_lower_hold_bias),
            "btc_lower_mid_noise_hold_bias": bool(btc_lower_mid_noise_hold_bias),
            "xau_lower_edge_to_edge_hold_bias": bool(xau_lower_edge_to_edge_hold_bias),
            "nas_upper_hold_bias": bool(nas_upper_hold_bias),
            "lower_reversal_hold_bias": bool(lower_reversal_hold_bias),
            "range_middle_observe": bool(range_middle_observe),
            "reached_opposite_edge": bool(reached_opposite_edge),
            "symbol_edge_completion_bias_v1": dict(symbol_edge_completion_bias),
            "state_exit_bias_v1": dict(state_execution_bias),
        }
