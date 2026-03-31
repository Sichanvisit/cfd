"""Rule-based recovery predictor for exit wait routing."""

from __future__ import annotations

from typing import Any

from backend.domain.decision_models import DecisionContext, ExitProfile, WaitState
from backend.services.exit_profile_router import resolve_recovery_policy


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(float(low), min(float(high), float(value)))


class ExitRecoveryPredictor:
    def predict(
        self,
        *,
        context: DecisionContext,
        wait_state: WaitState,
        exit_profile: ExitProfile | None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = dict(metrics or {})
        state = str(getattr(wait_state, "state", "NONE") or "NONE").upper()
        profit = float(metrics.get("profit", 0.0) or 0.0)
        giveback = float(metrics.get("giveback", 0.0) or 0.0)
        score_gap = float(metrics.get("score_gap", 0.0) or 0.0)
        adverse_risk = bool(metrics.get("adverse_risk", False))
        tf_confirm = bool(metrics.get("tf_confirm", False))
        duration_sec = float(metrics.get("duration_sec", 0.0) or 0.0)
        recovery_policy = resolve_recovery_policy(
            symbol=str(metrics.get("symbol", getattr(context, "symbol", "")) or getattr(context, "symbol", "") or ""),
            management_profile_id=str(metrics.get("management_profile_id", "") or ""),
            invalidation_id=str(metrics.get("invalidation_id", "") or ""),
            entry_setup_id=str(metrics.get("entry_setup_id", "") or ""),
            state_vector_v2=dict(metrics.get("state_vector_v2", {}) or {}) if isinstance(metrics.get("state_vector_v2", {}), dict) else {},
            state_metadata=dict(metrics.get("state_metadata", {}) or {}) if isinstance(metrics.get("state_metadata", {}), dict) else {},
            belief_state_v1=dict(metrics.get("belief_state_v1", {}) or {}) if isinstance(metrics.get("belief_state_v1", {}), dict) else {},
            entry_direction=str(metrics.get("entry_direction", "") or ""),
            default_be_max_loss_usd=0.90,
            default_tp1_max_loss_usd=0.35,
            default_max_wait_seconds=240,
            default_reverse_score_gap=18,
        )

        edge_bias = 0.0
        if str(context.box_state).upper() in {"UPPER", "LOWER"}:
            edge_bias += 0.05
        if str(context.bb_state).upper() in {"UPPER_EDGE", "LOWER_EDGE"}:
            edge_bias += 0.06
        if str((exit_profile or ExitProfile()).profile_id).lower() in {"neutral", "tight_protect"}:
            edge_bias += 0.03

        loss_mag = abs(min(0.0, profit))
        p_recover_be = 0.32 + edge_bias
        p_recover_tp1 = 0.24 + edge_bias
        p_deeper_loss = 0.28
        p_reverse_valid = 0.08
        reverse_gap = max(1, int(recovery_policy.get("reverse_score_gap", 18) or 18))

        if state == "RECOVERY_BE":
            p_recover_be += 0.22
            p_recover_tp1 += 0.12
        elif state == "RECOVERY_TP1":
            p_recover_be += 0.16
            p_recover_tp1 += 0.22
        elif state == "REVERSAL_CONFIRM":
            p_reverse_valid += 0.08
            p_deeper_loss += 0.10
        elif state == "REVERSE_READY":
            p_reverse_valid += 0.16
            p_deeper_loss += 0.12
        elif state == "CUT_IMMEDIATE":
            p_deeper_loss += 0.26
            p_recover_be -= 0.10
            p_recover_tp1 -= 0.12

        if loss_mag <= 0.35:
            p_recover_be += 0.12
            p_recover_tp1 += 0.10
        elif loss_mag >= 0.90:
            p_recover_be -= 0.14
            p_recover_tp1 -= 0.16
            p_deeper_loss += 0.18

        if giveback > 0.0:
            p_deeper_loss += min(0.12, giveback * 0.06)
        if adverse_risk:
            p_recover_be -= 0.16
            p_recover_tp1 -= 0.20
            p_deeper_loss += 0.22
        if tf_confirm and score_gap >= reverse_gap:
            p_reverse_valid += 0.06
            p_deeper_loss += 0.06
        if score_gap >= reverse_gap:
            p_recover_be -= 0.08
            p_recover_tp1 -= 0.10
            p_reverse_valid += 0.05
        if duration_sec > 300:
            p_recover_tp1 -= 0.06
            p_deeper_loss += 0.05

        policy_id = str(recovery_policy.get("policy_id", "") or "")
        if policy_id in {"range_reversal", "support_hold_profile"}:
            p_recover_be += 0.08
            p_recover_tp1 += 0.10
            p_deeper_loss -= 0.04
        elif policy_id == "trend_pullback":
            p_recover_be += 0.04
            p_recover_tp1 -= 0.08
            p_reverse_valid -= 0.05
        elif policy_id in {
            "breakout_retest",
            "breakout_hold_profile",
            "breakdown_hold_profile",
            "breakout_failure",
        }:
            p_recover_be -= 0.12
            p_recover_tp1 -= 0.16
            p_deeper_loss += 0.12
            p_reverse_valid += 0.05
        elif policy_id in {
            "reversal_profile",
            "reversal_profile_btc_tight",
            "mid_reclaim_fast_exit_profile",
            "mid_lose_fast_exit_profile",
        }:
            p_recover_be -= 0.06
            p_recover_tp1 -= 0.12
            p_deeper_loss += 0.08
        elif policy_id == "range_lower_reversal_buy_xau_balanced":
            p_recover_be += 0.12
            p_recover_tp1 += 0.14
            p_deeper_loss -= 0.08
        elif policy_id == "range_lower_reversal_buy_btc_balanced":
            p_recover_be += 0.08
            p_recover_tp1 += 0.06
            p_deeper_loss -= 0.05

        symbol_edge_overrides = dict(recovery_policy.get("symbol_edge_execution_overrides_v1", {}) or {})
        recovery_support_boost = 0.0
        if bool(symbol_edge_overrides.get("active", False)):
            recovery_support_boost = _clamp(float(symbol_edge_overrides.get("recovery_support_boost", 0.0) or 0.0), 0.0, 0.20)
            p_recover_be += recovery_support_boost
            p_recover_tp1 += recovery_support_boost * 0.85
            if not adverse_risk:
                p_deeper_loss -= recovery_support_boost * 0.60

        belief_overrides = dict(recovery_policy.get("belief_execution_overrides_v1", {}) or {})
        if bool(belief_overrides.get("prefer_hold_extension", False)):
            p_recover_be += 0.10
            p_recover_tp1 += 0.08
            p_deeper_loss -= 0.08
        if bool(belief_overrides.get("opposite_side_rising", False)):
            p_recover_be -= 0.08
            p_recover_tp1 -= 0.10
            p_deeper_loss += 0.12
            p_reverse_valid += 0.04
        if bool(belief_overrides.get("prefer_fast_cut", False)):
            p_recover_be -= 0.14
            p_recover_tp1 -= 0.14
            p_deeper_loss += 0.20
            p_reverse_valid += 0.06
        if recovery_support_boost > 0.0 and (
            bool(belief_overrides.get("prefer_fast_cut", False))
            or bool(belief_overrides.get("opposite_side_rising", False))
        ):
            p_recover_be -= recovery_support_boost * 0.95
            p_recover_tp1 -= recovery_support_boost * 0.85
            p_deeper_loss += recovery_support_boost * 1.10
        if (
            policy_id == "range_lower_reversal_buy_btc_balanced"
            and (
                bool(belief_overrides.get("prefer_fast_cut", False))
                or bool(belief_overrides.get("opposite_side_rising", False))
            )
        ):
            p_deeper_loss = max(p_deeper_loss, p_recover_be + 0.04)

        return {
            "model": "shadow_exit_recovery_v1",
            "p_recover_be": round(_clamp(p_recover_be, 0.05, 0.95), 6),
            "p_recover_tp1": round(_clamp(p_recover_tp1, 0.05, 0.95), 6),
            "p_deeper_loss": round(_clamp(p_deeper_loss, 0.05, 0.95), 6),
            "p_reverse_valid": round(_clamp(p_reverse_valid, 0.05, 0.95), 6),
            "recovery_policy_id": policy_id,
        }
