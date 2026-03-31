from __future__ import annotations

from typing import Any, Mapping

from backend.core.config import Config
from ml.semantic_v1.runtime_adapter import resolve_trace_quality_state


SEMANTIC_LIVE_ROLLOUT_VERSION = "semantic_live_rollout_v1"
ROLLOUT_MODES = ("disabled", "log_only", "alert_only", "threshold_only", "partial_live")
RULE_BASELINE_OWNER = "rule_baseline"


def _coerce_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _coerce_float(value: Any, default: float | None = None) -> float | None:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    if value in ("", None):
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def normalize_rollout_mode(value: Any) -> str:
    mode = str(value or "disabled").strip().lower()
    if mode not in ROLLOUT_MODES:
        return "disabled"
    return mode


class SemanticPromotionGuard:
    @staticmethod
    def current_mode() -> str:
        return normalize_rollout_mode(getattr(Config, "SEMANTIC_LIVE_ROLLOUT_MODE", "disabled"))

    @staticmethod
    def _allowed_compatibility_modes() -> set[str]:
        modes = getattr(Config, "SEMANTIC_LIVE_ALLOWED_COMPATIBILITY_MODES", ()) or ()
        output = {str(mode).strip().lower() for mode in modes if str(mode).strip()}
        output.add("")
        return output

    @staticmethod
    def _symbol_allowlist() -> set[str]:
        values = getattr(Config, "SEMANTIC_LIVE_SYMBOL_ALLOWLIST", ()) or ()
        return {str(value).strip().upper() for value in values if str(value).strip()}

    @staticmethod
    def _entry_stage_allowlist() -> set[str]:
        values = getattr(Config, "SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST", ()) or ()
        return {str(value).strip().lower() for value in values if str(value).strip()}

    @classmethod
    def _quality_fallback_reason(
        cls,
        *,
        runtime_snapshot_row: Mapping[str, Any] | None,
        trace_quality_state: str,
    ) -> str:
        row = _coerce_mapping(runtime_snapshot_row)
        missing_feature_count = _coerce_int(row.get("missing_feature_count"), 0)
        compatibility_mode = str(row.get("compatibility_mode", "") or "").strip().lower()
        max_missing = max(0, int(getattr(Config, "SEMANTIC_LIVE_MAX_MISSING_FEATURES", 2)))
        if missing_feature_count > max_missing:
            return "missing_feature_count_high"
        if compatibility_mode not in cls._allowed_compatibility_modes():
            return "compatibility_mode_blocked"
        require_clean = bool(getattr(Config, "SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE", True))
        allow_fallback_heavy = bool(getattr(Config, "SEMANTIC_LIVE_ALLOW_FALLBACK_HEAVY", False))
        if require_clean and trace_quality_state != "clean":
            return f"trace_quality_{trace_quality_state}"
        if not require_clean and trace_quality_state in {"unknown", "incomplete"}:
            return f"trace_quality_{trace_quality_state}"
        if not allow_fallback_heavy and trace_quality_state == "fallback_heavy":
            return "trace_quality_fallback_heavy"
        return ""

    @staticmethod
    def _enter_support(
        *,
        semantic_prediction: Mapping[str, Any],
    ) -> tuple[float, float, float, float]:
        timing = _coerce_mapping(semantic_prediction.get("timing"))
        entry_quality = _coerce_mapping(semantic_prediction.get("entry_quality"))
        timing_prob = float(_coerce_float(timing.get("probability"), 0.0) or 0.0)
        entry_prob = _coerce_float(entry_quality.get("probability"))
        if entry_prob is None:
            entry_prob = timing_prob
        timing_threshold = float(_coerce_float(timing.get("threshold"), 0.55) or 0.55)
        entry_threshold = float(_coerce_float(entry_quality.get("threshold"), 0.55) or 0.55)
        support_margin = max(0.0, timing_prob - timing_threshold) + max(0.0, entry_prob - entry_threshold)
        resistance_margin = max(0.0, timing_threshold - timing_prob) + max(0.0, entry_threshold - entry_prob)
        return timing_prob, float(entry_prob), support_margin, resistance_margin

    @classmethod
    def evaluate_entry_rollout(
        cls,
        *,
        symbol: str,
        baseline_action: str,
        entry_stage: str,
        current_threshold: int,
        semantic_prediction: Mapping[str, Any] | None,
        runtime_snapshot_row: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        mode = cls.current_mode()
        prediction = _coerce_mapping(semantic_prediction)
        row = _coerce_mapping(runtime_snapshot_row)
        trace_quality_state = str(
            prediction.get("trace_quality_state", "") or resolve_trace_quality_state(row)
        ).strip() or "unknown"
        semantic_available = bool(prediction.get("available"))
        semantic_should_enter = bool(prediction.get("should_enter"))
        timing_prob, entry_prob, support_margin, resistance_margin = cls._enter_support(
            semantic_prediction=prediction,
        )
        baseline_has_action = str(baseline_action or "").strip().upper() in {"BUY", "SELL"}
        fallback_reason = ""
        symbol_u = str(symbol or "").strip().upper()
        stage_u = str(entry_stage or "").strip().lower()
        symbol_allowlist = cls._symbol_allowlist()
        stage_allowlist = cls._entry_stage_allowlist()
        min_timing_prob = float(getattr(Config, "SEMANTIC_LIVE_MIN_TIMING_PROB", 0.58))
        min_entry_quality_prob = float(getattr(Config, "SEMANTIC_LIVE_MIN_ENTRY_QUALITY_PROB", 0.58))

        if bool(getattr(Config, "SEMANTIC_LIVE_KILL_SWITCH", False)):
            fallback_reason = "kill_switch_enabled"
        elif mode == "disabled":
            fallback_reason = "rollout_disabled"
        elif symbol_allowlist and symbol_u not in symbol_allowlist:
            fallback_reason = "symbol_not_in_allowlist"
        elif stage_allowlist and stage_u not in stage_allowlist:
            fallback_reason = "entry_stage_not_in_allowlist"
        elif not baseline_has_action:
            fallback_reason = "baseline_no_action"
        elif not semantic_available:
            fallback_reason = "semantic_unavailable"
        elif timing_prob < min_timing_prob:
            fallback_reason = "timing_probability_too_low"
        elif entry_prob < min_entry_quality_prob:
            fallback_reason = "entry_quality_probability_too_low"
        else:
            fallback_reason = cls._quality_fallback_reason(
                runtime_snapshot_row=row,
                trace_quality_state=trace_quality_state,
            )

        threshold_before = int(max(1, int(current_threshold or 1)))
        threshold_adjustment_points = 0
        threshold_applied = False
        partial_live_weight = 0.0
        partial_live_applied = False
        alert_active = False
        disagree = bool(baseline_has_action and not semantic_should_enter)

        if not fallback_reason and mode in {"threshold_only", "partial_live"}:
            min_adjust = max(0, int(getattr(Config, "SEMANTIC_LIVE_THRESHOLD_MIN_ADJUST_PTS", 2)))
            if semantic_should_enter:
                relief_gain = float(getattr(Config, "SEMANTIC_LIVE_THRESHOLD_RELIEF_GAIN", 90.0))
                max_relief = max(0, int(getattr(Config, "SEMANTIC_LIVE_THRESHOLD_RELIEF_MAX_PTS", 18)))
                threshold_adjustment_points = -min(
                    max_relief,
                    int(round(float(support_margin) * relief_gain)),
                )
            else:
                raise_gain = float(getattr(Config, "SEMANTIC_LIVE_THRESHOLD_RAISE_GAIN", 72.0))
                max_raise = max(0, int(getattr(Config, "SEMANTIC_LIVE_THRESHOLD_RAISE_MAX_PTS", 12)))
                threshold_adjustment_points = min(
                    max_raise,
                    int(round(float(resistance_margin) * raise_gain)),
                )
            if abs(int(threshold_adjustment_points)) < min_adjust:
                threshold_adjustment_points = 0
            threshold_applied = int(threshold_adjustment_points) != 0

        threshold_after = max(1, int(threshold_before + int(threshold_adjustment_points)))
        if mode == "partial_live" and not fallback_reason and semantic_should_enter:
            partial_weight_max = max(0.0, float(getattr(Config, "SEMANTIC_LIVE_PARTIAL_WEIGHT_MAX", 0.15)))
            partial_weight_gain = max(0.0, float(getattr(Config, "SEMANTIC_LIVE_PARTIAL_WEIGHT_GAIN", 0.80)))
            partial_live_weight = min(partial_weight_max, float(support_margin) * partial_weight_gain)
            partial_live_applied = partial_live_weight > 0.0

        if mode in {"alert_only", "threshold_only", "partial_live"} and bool(
            getattr(Config, "SEMANTIC_LIVE_ALERT_ON_DISAGREEMENT", True)
        ):
            alert_active = bool(disagree or fallback_reason)

        reason_parts = [
            f"mode={mode}",
            f"trace={trace_quality_state}",
            f"timing={timing_prob:.3f}",
            f"entry_quality={entry_prob:.3f}",
        ]
        if fallback_reason:
            reason_parts.append(f"fallback={fallback_reason}")
        elif threshold_applied:
            reason_parts.append(f"threshold_adjustment={int(threshold_adjustment_points)}")
        elif mode == "log_only":
            reason_parts.append("log_only")

        threshold_state = "not_applied"
        threshold_inactive_reason = ""
        if bool(threshold_applied and not fallback_reason):
            threshold_state = "applied"
        elif fallback_reason:
            threshold_state = "fallback_blocked"
            threshold_inactive_reason = str(fallback_reason)
        elif mode in {"disabled", "log_only", "alert_only"}:
            threshold_state = "mode_no_threshold"
            threshold_inactive_reason = f"mode_{mode}"
        elif int(threshold_adjustment_points) == 0:
            threshold_state = "threshold_neutral"
            threshold_inactive_reason = "threshold_adjustment_zero"

        return {
            "contract_version": SEMANTIC_LIVE_ROLLOUT_VERSION,
            "mode": mode,
            "owner": RULE_BASELINE_OWNER,
            "symbol": str(symbol or ""),
            "baseline_action": str(baseline_action or ""),
            "entry_stage": str(entry_stage or ""),
            "symbol_allowed": bool((not symbol_allowlist) or (symbol_u in symbol_allowlist)),
            "entry_stage_allowed": bool((not stage_allowlist) or (stage_u in stage_allowlist)),
            "semantic_available": bool(semantic_available),
            "semantic_should_enter": bool(semantic_should_enter),
            "trace_quality_state": trace_quality_state,
            "fallback_applied": bool(fallback_reason),
            "fallback_reason": str(fallback_reason or ""),
            "alert_active": bool(alert_active),
            "disagree_with_baseline": bool(disagree),
            "threshold_before": int(threshold_before),
            "threshold_after": int(threshold_after),
            "threshold_adjustment_points": int(threshold_adjustment_points),
            "threshold_applied": bool(threshold_applied and not fallback_reason),
            "threshold_state": str(threshold_state),
            "threshold_inactive_reason": str(threshold_inactive_reason),
            "partial_live_weight": float(partial_live_weight),
            "partial_live_applied": bool(partial_live_applied and not fallback_reason),
            "timing_probability": float(timing_prob),
            "entry_quality_probability": float(entry_prob),
            "reason": ", ".join(reason_parts),
        }

    @classmethod
    def build_exit_rollout_summary(cls, *, symbol: str = "") -> dict[str, Any]:
        mode = cls.current_mode()
        enabled = bool(
            getattr(Config, "SEMANTIC_EXIT_ROLLOUT_ENABLED", False)
            and mode in {"alert_only", "threshold_only", "partial_live"}
        )
        reason = "exit_rollout_disabled"
        if enabled:
            reason = "phase5_entry_first_baseline_owner"
        return {
            "contract_version": SEMANTIC_LIVE_ROLLOUT_VERSION,
            "mode": mode,
            "owner": RULE_BASELINE_OWNER,
            "symbol": str(symbol or ""),
            "enabled": bool(enabled),
            "reason": reason,
        }
