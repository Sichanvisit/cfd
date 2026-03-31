"""Shadow exit predictor."""

from __future__ import annotations

from typing import Any

from backend.domain.decision_models import DecisionContext, ExitProfile, WaitState
from backend.services.predictors.base import ExitPredictor


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(float(low), min(float(high), float(value)))


class ShadowExitPredictor(ExitPredictor):
    def predict(
        self,
        *,
        context: DecisionContext,
        wait_state: WaitState,
        exit_profile: ExitProfile,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = dict(metrics or {})
        profit = float(metrics.get("profit", 0.0) or 0.0)
        score_gap = float(metrics.get("score_gap", 0.0) or 0.0)
        adverse = bool(metrics.get("adverse_risk", False))
        tf_confirm = bool(metrics.get("tf_confirm", False))

        p_more_profit = 0.48
        if profit > 0.0:
            p_more_profit += 0.06
        if str(exit_profile.profile_id).lower() in {"aggressive", "hold_then_trail"}:
            p_more_profit += 0.05
        if adverse:
            p_more_profit -= 0.10
        if tf_confirm:
            p_more_profit -= 0.04

        p_giveback = 0.36
        if profit > 0.0:
            p_giveback += 0.10
        if adverse:
            p_giveback += 0.12
        if abs(score_gap) > 20:
            p_giveback += 0.06

        p_reverse_valid = 0.28
        if adverse and tf_confirm and score_gap > 0:
            p_reverse_valid += 0.18
        if str(wait_state.state).upper() == "REVERSAL_CONFIRM":
            p_reverse_valid += 0.10

        return {
            "model": "shadow_exit_v1",
            "p_more_profit": round(_clamp(p_more_profit, 0.05, 0.95), 6),
            "p_giveback": round(_clamp(p_giveback, 0.05, 0.95), 6),
            "p_reverse_valid": round(_clamp(p_reverse_valid, 0.05, 0.95), 6),
        }
