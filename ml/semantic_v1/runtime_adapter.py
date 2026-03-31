from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

from ml.semantic_v1.contracts import SEMANTIC_TARGET_CONTRACT_VERSION
from ml.semantic_v1.evaluate import (
    DEFAULT_MODEL_DIR,
    SEMANTIC_MODEL_VERSION,
    predict_bundle_proba,
)
from ml.semantic_v1.feature_packs import (
    SEMANTIC_FEATURE_CONTRACT_VERSION,
    SEMANTIC_INPUT_COLUMNS,
    TRACE_QUALITY_COLUMNS,
)


SEMANTIC_SHADOW_RUNTIME_CONTRACT_VERSION = "semantic_shadow_runtime_v1"
SEMANTIC_SHADOW_RUNTIME_DIAGNOSTIC_VERSION = "semantic_shadow_runtime_diagnostics_v1"
DEFAULT_TIMING_THRESHOLD = 0.55
DEFAULT_ENTRY_QUALITY_THRESHOLD = 0.55
DEFAULT_EXIT_MANAGEMENT_THRESHOLD = 0.55
SAFE_METADATA_COLUMNS = (
    "symbol",
    "signal_timeframe",
    "setup_id",
    "setup_side",
    "entry_stage",
    "preflight_regime",
    "preflight_liquidity",
)
MODEL_FILE_MAP = {
    "timing": "timing_model.joblib",
    "entry_quality": "entry_quality_model.joblib",
    "exit_management": "exit_management_model.joblib",
}


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


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value or default)


def resolve_trace_quality_state(row: Mapping[str, Any] | None) -> str:
    payload = _coerce_mapping(row)
    completeness = float(_coerce_float(payload.get("data_completeness_ratio"), 0.0) or 0.0)
    missing_count = _coerce_int(payload.get("missing_feature_count"), 0)
    fallback_count = _coerce_int(payload.get("used_fallback_count"), 0)
    compatibility_mode = _coerce_text(payload.get("compatibility_mode", "")).strip()

    if completeness <= 0.0 and missing_count <= 0 and fallback_count <= 0 and not compatibility_mode:
        return "unknown"
    if completeness < 0.90 or missing_count >= 3:
        return "incomplete"
    if fallback_count >= 2 or compatibility_mode:
        return "fallback_heavy"
    if completeness < 0.98 or missing_count > 0 or fallback_count > 0:
        return "degraded"
    return "clean"


def _set_nested_value(target: dict[str, Any], column: str, value: Any) -> None:
    if value in ("", None):
        return
    target[column] = value


def build_semantic_shadow_feature_row(
    *,
    runtime_snapshot_row: Mapping[str, Any] | None = None,
    position_snapshot_v2: Mapping[str, Any] | None = None,
    response_vector_v2: Mapping[str, Any] | None = None,
    state_vector_v2: Mapping[str, Any] | None = None,
    evidence_vector_v1: Mapping[str, Any] | None = None,
    forecast_features_v1: Mapping[str, Any] | None = None,
    signal_timeframe: str = "",
    setup_id: str = "",
    setup_side: str = "",
    entry_stage: str = "",
    preflight_regime: str = "",
    preflight_liquidity: str = "",
) -> dict[str, Any]:
    runtime_row = _coerce_mapping(runtime_snapshot_row)
    position = _coerce_mapping(position_snapshot_v2)
    response = _coerce_mapping(response_vector_v2)
    state = _coerce_mapping(state_vector_v2)
    evidence = _coerce_mapping(evidence_vector_v1)
    forecast = _coerce_mapping(forecast_features_v1)

    vector = _coerce_mapping(position.get("vector"))
    interpretation = _coerce_mapping(position.get("interpretation"))
    energy = _coerce_mapping(position.get("energy"))

    feature_row: dict[str, Any] = {
        "symbol": _coerce_text(runtime_row.get("symbol", "")),
        "signal_timeframe": _coerce_text(signal_timeframe or runtime_row.get("signal_timeframe", "")),
        "setup_id": _coerce_text(setup_id),
        "setup_side": _coerce_text(setup_side),
        "entry_stage": _coerce_text(entry_stage),
        "preflight_regime": _coerce_text(preflight_regime),
        "preflight_liquidity": _coerce_text(preflight_liquidity),
        "decision_row_key": _coerce_text(runtime_row.get("decision_row_key", "")),
        "runtime_snapshot_key": _coerce_text(runtime_row.get("runtime_snapshot_key", "")),
        "trade_link_key": _coerce_text(runtime_row.get("trade_link_key", "")),
        "replay_row_key": _coerce_text(runtime_row.get("replay_row_key", "")),
        "signal_age_sec": _coerce_float(runtime_row.get("signal_age_sec"), 0.0),
        "bar_age_sec": _coerce_float(runtime_row.get("bar_age_sec"), 0.0),
        "decision_latency_ms": _coerce_int(runtime_row.get("decision_latency_ms"), 0),
        "order_submit_latency_ms": _coerce_int(runtime_row.get("order_submit_latency_ms"), 0),
        "missing_feature_count": _coerce_int(runtime_row.get("missing_feature_count"), 0),
        "data_completeness_ratio": _coerce_float(runtime_row.get("data_completeness_ratio"), 0.0),
        "used_fallback_count": _coerce_int(runtime_row.get("used_fallback_count"), 0),
        "compatibility_mode": _coerce_text(runtime_row.get("compatibility_mode", "")),
        "detail_blob_bytes": _coerce_int(runtime_row.get("detail_blob_bytes"), 0),
        "snapshot_payload_bytes": _coerce_int(runtime_row.get("snapshot_payload_bytes"), 0),
        "row_payload_bytes": _coerce_int(runtime_row.get("row_payload_bytes"), 0),
    }

    position_map = {
        "position_x_box": _coerce_float(vector.get("x_box")),
        "position_x_bb20": _coerce_float(vector.get("x_bb20")),
        "position_x_bb44": _coerce_float(vector.get("x_bb44")),
        "position_x_ma20": _coerce_float(vector.get("x_ma20")),
        "position_x_ma60": _coerce_float(vector.get("x_ma60")),
        "position_x_sr": _coerce_float(vector.get("x_sr")),
        "position_x_trendline": _coerce_float(vector.get("x_trendline")),
        "position_pos_composite": _coerce_float(interpretation.get("pos_composite")),
        "position_alignment_label": _coerce_text(interpretation.get("alignment_label", "")),
        "position_bias_label": _coerce_text(interpretation.get("bias_label", "")),
        "position_conflict_kind": _coerce_text(interpretation.get("conflict_kind", "")),
        "position_lower_force": _coerce_float(energy.get("lower_position_force")),
        "position_upper_force": _coerce_float(energy.get("upper_position_force")),
        "position_middle_neutrality": _coerce_float(energy.get("middle_neutrality")),
        "position_conflict_score": _coerce_float(energy.get("position_conflict_score")),
    }
    for key, value in position_map.items():
        _set_nested_value(feature_row, key, value)

    response_map = {
        "response_lower_break_down": _coerce_float(response.get("lower_break_down")),
        "response_lower_hold_up": _coerce_float(response.get("lower_hold_up")),
        "response_mid_lose_down": _coerce_float(response.get("mid_lose_down")),
        "response_mid_reclaim_up": _coerce_float(response.get("mid_reclaim_up")),
        "response_upper_break_up": _coerce_float(response.get("upper_break_up")),
        "response_upper_reject_down": _coerce_float(response.get("upper_reject_down")),
    }
    for key, value in response_map.items():
        _set_nested_value(feature_row, key, value)

    state_map = {
        "state_alignment_gain": _coerce_float(state.get("alignment_gain")),
        "state_breakout_continuation_gain": _coerce_float(state.get("breakout_continuation_gain")),
        "state_trend_pullback_gain": _coerce_float(state.get("trend_pullback_gain")),
        "state_range_reversal_gain": _coerce_float(state.get("range_reversal_gain")),
        "state_conflict_damp": _coerce_float(state.get("conflict_damp")),
        "state_noise_damp": _coerce_float(state.get("noise_damp")),
        "state_liquidity_penalty": _coerce_float(state.get("liquidity_penalty")),
        "state_volatility_penalty": _coerce_float(state.get("volatility_penalty")),
        "state_countertrend_penalty": _coerce_float(state.get("countertrend_penalty")),
    }
    for key, value in state_map.items():
        _set_nested_value(feature_row, key, value)

    evidence_map = {
        "evidence_buy_total": _coerce_float(evidence.get("buy_total_evidence")),
        "evidence_buy_continuation": _coerce_float(evidence.get("buy_continuation_evidence")),
        "evidence_buy_reversal": _coerce_float(evidence.get("buy_reversal_evidence")),
        "evidence_sell_total": _coerce_float(evidence.get("sell_total_evidence")),
        "evidence_sell_continuation": _coerce_float(evidence.get("sell_continuation_evidence")),
        "evidence_sell_reversal": _coerce_float(evidence.get("sell_reversal_evidence")),
    }
    for key, value in evidence_map.items():
        _set_nested_value(feature_row, key, value)

    forecast_map = {
        "forecast_position_primary_label": _coerce_text(forecast.get("position_primary_label", "")),
        "forecast_position_secondary_context_label": _coerce_text(
            forecast.get("position_secondary_context_label", "")
        ),
        "forecast_position_conflict_score": _coerce_float(forecast.get("position_conflict_score")),
        "forecast_middle_neutrality": _coerce_float(forecast.get("middle_neutrality")),
        "forecast_management_horizon_bars": _coerce_int(forecast.get("management_horizon_bars"), 0),
        "forecast_signal_timeframe": _coerce_text(
            forecast.get("signal_timeframe", "") or signal_timeframe or runtime_row.get("signal_timeframe", "")
        ),
    }
    for key, value in forecast_map.items():
        _set_nested_value(feature_row, key, value)

    for column in SAFE_METADATA_COLUMNS:
        feature_row.setdefault(column, "")
    for column in SEMANTIC_INPUT_COLUMNS:
        feature_row.setdefault(column, None)
    for column in TRACE_QUALITY_COLUMNS:
        feature_row.setdefault(column, None if column.endswith("_key") else 0)
    return feature_row


def _decision_block(probability: float | None, threshold: float, *, available: bool) -> dict[str, Any]:
    decision = bool(available and probability is not None and float(probability) >= float(threshold))
    return {
        "available": bool(available),
        "probability": (None if probability is None else float(probability)),
        "threshold": float(threshold),
        "decision": bool(decision),
    }


def resolve_semantic_shadow_compare_label(
    shadow_prediction: Mapping[str, Any] | None,
    *,
    baseline_outcome: str = "",
    baseline_action: str = "",
    blocked_by: str = "",
) -> str:
    prediction = _coerce_mapping(shadow_prediction)
    if not bool(prediction.get("available")):
        return "unavailable"

    semantic_enter = bool(prediction.get("should_enter"))
    baseline_enter = str(baseline_outcome or "").strip().lower() == "entered"
    if semantic_enter and baseline_enter:
        return "agree_enter"
    if semantic_enter and not baseline_enter:
        return "semantic_earlier_enter"
    if (not semantic_enter) and baseline_enter:
        return "semantic_later_block"
    if str(baseline_outcome or "").strip().lower() == "wait":
        return "agree_wait"
    if str(blocked_by or "").strip():
        return "agree_block"
    if str(baseline_action or "").strip().upper() in {"BUY", "SELL"}:
        return "agree_wait"
    return "agree_block"


class SemanticShadowRuntime:
    def __init__(self, model_dir: str | Path | None = None, *, bundles: Mapping[str, Any] | None = None):
        self.model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
        self.bundles = dict(bundles or self._load_bundles(self.model_dir))
        self.available_targets = tuple(key for key in MODEL_FILE_MAP if key in self.bundles)
        self.model_version = SEMANTIC_MODEL_VERSION

    @staticmethod
    def unavailable_prediction(*, reason: str = "", action_hint: str = "") -> dict[str, Any]:
        availability_reason = str(reason or "semantic_models_unavailable")
        return {
            "contract_version": SEMANTIC_SHADOW_RUNTIME_CONTRACT_VERSION,
            "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
            "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
            "model_version": SEMANTIC_MODEL_VERSION,
            "available": False,
            "availability_state": "unavailable",
            "availability_reason": availability_reason,
            "available_targets": [],
            "action_hint": str(action_hint or ""),
            "trace_quality_state": "unavailable",
            "timing": _decision_block(None, DEFAULT_TIMING_THRESHOLD, available=False),
            "entry_quality": _decision_block(None, DEFAULT_ENTRY_QUALITY_THRESHOLD, available=False),
            "exit_management": _decision_block(None, DEFAULT_EXIT_MANAGEMENT_THRESHOLD, available=False),
            "should_enter": False,
            "recommendation": "unavailable",
            "reason": availability_reason,
        }

    @staticmethod
    def _load_bundles(model_dir: Path) -> dict[str, Any]:
        if not model_dir.exists():
            return {}
        bundles: dict[str, Any] = {}
        for key, file_name in MODEL_FILE_MAP.items():
            path = model_dir / file_name
            if not path.exists():
                continue
            bundles[key] = joblib.load(path)
        return bundles

    def predict_shadow(
        self,
        feature_row: Mapping[str, Any] | None,
        *,
        action_hint: str = "",
        timing_threshold: float = DEFAULT_TIMING_THRESHOLD,
        entry_quality_threshold: float = DEFAULT_ENTRY_QUALITY_THRESHOLD,
        exit_management_threshold: float = DEFAULT_EXIT_MANAGEMENT_THRESHOLD,
    ) -> dict[str, Any]:
        row = dict(feature_row or {})
        if not self.available_targets:
            return self.unavailable_prediction(reason="semantic_models_unavailable", action_hint=action_hint)

        frame = pd.DataFrame([row])
        timing_prob = None
        entry_quality_prob = None
        exit_management_prob = None

        if "timing" in self.bundles:
            timing_prob = float(predict_bundle_proba(self.bundles["timing"], frame)[0])
        if "entry_quality" in self.bundles:
            entry_quality_prob = float(predict_bundle_proba(self.bundles["entry_quality"], frame)[0])
        if "exit_management" in self.bundles:
            exit_management_prob = float(predict_bundle_proba(self.bundles["exit_management"], frame)[0])

        timing_block = _decision_block(timing_prob, timing_threshold, available=("timing" in self.bundles))
        entry_quality_block = _decision_block(
            entry_quality_prob,
            entry_quality_threshold,
            available=("entry_quality" in self.bundles),
        )
        exit_management_block = _decision_block(
            exit_management_prob,
            exit_management_threshold,
            available=("exit_management" in self.bundles),
        )

        if timing_block["available"] and entry_quality_block["available"]:
            should_enter = bool(timing_block["decision"] and entry_quality_block["decision"])
        elif timing_block["available"]:
            should_enter = bool(timing_block["decision"])
        elif entry_quality_block["available"]:
            should_enter = bool(entry_quality_block["decision"])
        else:
            should_enter = False

        trace_quality_state = resolve_trace_quality_state(row)
        reason_parts: list[str] = []
        if timing_prob is not None:
            reason_parts.append(f"timing={timing_prob:.3f}")
        if entry_quality_prob is not None:
            reason_parts.append(f"entry_quality={entry_quality_prob:.3f}")
        if exit_management_prob is not None:
            reason_parts.append(f"exit_management={exit_management_prob:.3f}")
        reason_parts.append(f"trace={trace_quality_state}")

        return {
            "contract_version": SEMANTIC_SHADOW_RUNTIME_CONTRACT_VERSION,
            "semantic_feature_contract_version": SEMANTIC_FEATURE_CONTRACT_VERSION,
            "semantic_target_contract_version": SEMANTIC_TARGET_CONTRACT_VERSION,
            "model_version": self.model_version,
            "available": True,
            "availability_state": "available",
            "availability_reason": "",
            "available_targets": list(self.available_targets),
            "action_hint": str(action_hint or ""),
            "trace_quality_state": trace_quality_state,
            "timing": timing_block,
            "entry_quality": entry_quality_block,
            "exit_management": exit_management_block,
            "should_enter": bool(should_enter),
            "recommendation": ("enter_now" if should_enter else "wait"),
            "reason": ", ".join(reason_parts),
        }
