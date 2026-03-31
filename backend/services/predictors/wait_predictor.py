"""Shadow wait predictor."""

from __future__ import annotations

from typing import Any

from backend.domain.decision_models import DecisionContext, ExitProfile, SetupCandidate, WaitState
from backend.services.predictors.base import WaitPredictor


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(float(low), min(float(high), float(value)))


class ShadowWaitPredictor(WaitPredictor):
    def predict_entry_wait(
        self,
        *,
        context: DecisionContext,
        setup: SetupCandidate | None,
        wait_state: WaitState,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = str(wait_state.state or "NONE").upper()
        base = {
            "AGAINST_MODE": 0.85,
            "NEED_RETEST": 0.80,
            "CENTER": 0.72,
            "NOISE": 0.68,
            "CONFLICT": 0.64,
            "ACTIVE": 0.58,
            "NONE": 0.10,
        }.get(state, 0.10)
        if str(context.bb_state).upper() == "UNKNOWN":
            base -= 0.03
        if str(context.box_state).upper() == "MIDDLE":
            base += 0.05
        if setup is not None and str(setup.status).lower() == "matched":
            base -= 0.06
        p_wait = _clamp(base, 0.05, 0.95)
        expected_improvement = max(0.0, (float(wait_state.score) * 0.025) + (0.20 if state in {"CENTER", "NOISE"} else 0.10))
        expected_miss_cost = max(0.05, 0.18 - (0.04 if state in {"CENTER", "NOISE", "CONFLICT"} else 0.0))
        return {
            "model": "shadow_wait_entry_v1",
            "p_better_entry_if_wait": round(float(p_wait), 6),
            "expected_entry_improvement": round(float(expected_improvement), 6),
            "expected_miss_cost": round(float(expected_miss_cost), 6),
        }

    def predict_exit_wait(
        self,
        *,
        context: DecisionContext,
        wait_state: WaitState,
        exit_profile: ExitProfile | None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = dict(metrics or {})
        state = str(wait_state.state or "NONE").upper()
        profit = float(metrics.get("profit", 0.0) or 0.0)
        giveback = float(metrics.get("giveback", 0.0) or 0.0)
        base = {
            "RECOVERY_BE": 0.66,
            "RECOVERY_TP1": 0.72,
            "GREEN_CLOSE": 0.58,
            "REVERSAL_CONFIRM": 0.54,
            "REVERSE_READY": 0.20,
            "CUT_IMMEDIATE": 0.08,
            "NONE": 0.10,
        }.get(state, 0.10)
        if profit < 0.0 and state in {"RECOVERY_BE", "RECOVERY_TP1"}:
            base += 0.06
        if giveback > 0.0:
            base -= min(0.08, giveback * 0.05)
        p_wait = _clamp(base, 0.05, 0.95)
        expected_improvement = max(
            0.0,
            abs(profit) * (0.45 if state == "RECOVERY_TP1" else 0.35)
            + (0.15 if state in {"RECOVERY_BE", "RECOVERY_TP1"} else 0.08),
        )
        expected_miss_cost = max(
            0.05,
            0.12
            + (0.06 if state == "REVERSAL_CONFIRM" else 0.0)
            + (0.10 if state == "CUT_IMMEDIATE" else 0.0),
        )
        return {
            "model": "shadow_wait_exit_v1",
            "p_better_exit_if_wait": round(float(p_wait), 6),
            "expected_exit_improvement": round(float(expected_improvement), 6),
            "expected_miss_cost": round(float(expected_miss_cost), 6),
        }
