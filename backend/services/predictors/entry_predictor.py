"""Shadow entry predictor."""

from __future__ import annotations

from typing import Any

from backend.domain.decision_models import DecisionContext, SetupCandidate
from backend.services.predictors.base import EntryPredictor


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(float(low), min(float(high), float(value)))


class ShadowEntryPredictor(EntryPredictor):
    def predict(
        self,
        *,
        context: DecisionContext,
        setup: SetupCandidate,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = dict(metrics or {})
        raw_score = float(metrics.get("raw_score", 0.0) or 0.0)
        contra_score = float(metrics.get("contra_score", 0.0) or 0.0)
        effective_threshold = float(metrics.get("effective_threshold", 0.0) or 0.0)
        core_score = float(metrics.get("core_score", 0.0) or 0.0)
        score_gap = 0.0
        if abs(raw_score) + abs(contra_score) > 0:
            score_gap = (raw_score - contra_score) / max(1.0, abs(raw_score) + abs(contra_score))
        threshold_gap = 0.0
        if effective_threshold > 0:
            threshold_gap = (raw_score - effective_threshold) / max(1.0, effective_threshold)

        p_win = 0.50
        p_win += float(setup.score) * 0.12
        p_win += float(setup.entry_quality) * 0.10
        p_win += float(core_score) * 0.12
        p_win += float(score_gap) * 0.18
        p_win += float(threshold_gap) * 0.10

        if str(context.market_mode).upper() == "RANGE" and str(setup.setup_id).startswith("range_"):
            p_win += 0.04
        if str(context.market_mode).upper() == "TREND" and "pullback" in str(setup.setup_id):
            p_win += 0.04
        if str(context.box_state).upper() == "MIDDLE":
            p_win -= 0.06
        if str(context.bb_state).upper() == "UNKNOWN":
            p_win -= 0.03
        if str(setup.status).lower() != "matched":
            p_win -= 0.15

        p_win = _clamp(p_win, 0.05, 0.95)
        p_tp_first = _clamp(p_win + 0.04, 0.05, 0.98)
        expected_reward = round(max(0.1, 0.8 + (p_win * 1.2) + max(0.0, threshold_gap * 0.5)), 6)
        expected_risk = round(max(0.1, 0.9 + ((1.0 - p_win) * 1.1) + max(0.0, -threshold_gap * 0.6)), 6)
        return {
            "model": "shadow_entry_v1",
            "p_win": round(float(p_win), 6),
            "p_tp_first": round(float(p_tp_first), 6),
            "expected_reward": float(expected_reward),
            "expected_risk": float(expected_risk),
        }
