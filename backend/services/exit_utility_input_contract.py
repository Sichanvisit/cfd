"""Shared input contract helpers for exit utility decision construction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.core.config import Config
from backend.services.exit_wait_state_surface_contract import (
    compact_exit_wait_state_surface_v1,
)


def _as_mapping(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _to_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _round6(value: object, default: float = 0.0) -> float:
    return round(_to_float(value, default), 6)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _extract_state_vector_v2(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload_map = _as_mapping(payload)
    return _as_mapping(payload_map.get("state_vector_v2", payload_map.get("state_vector_effective_v1", {})))


def _extract_state_v2_meta(payload: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    state_vector_v2 = _extract_state_vector_v2(payload)
    return state_vector_v2, _as_mapping(state_vector_v2.get("metadata"))


def resolve_exit_utility_state_bias_v1(
    payload: Mapping[str, Any] | None = None,
    *,
    entry_direction: str = "",
) -> dict[str, Any]:
    state_vector_v2, state_meta = _extract_state_v2_meta(payload)
    if not state_vector_v2:
        return {
            "prefer_hold_through_green": False,
            "prefer_fast_cut": False,
            "hold_bias": 0.0,
            "wait_bias": 0.0,
            "exit_pressure": 0.0,
            "aligned_with_entry": False,
            "countertrend_with_entry": False,
            "topdown_state_label": "",
            "patience_state_label": "",
            "execution_friction_state": "",
            "session_exhaustion_state": "",
            "event_risk_state": "",
        }

    wait_gain = _to_float(state_vector_v2.get("wait_patience_gain", 1.0), 1.0)
    hold_gain = _to_float(state_vector_v2.get("hold_patience_gain", 1.0), 1.0)
    fast_exit_risk = _to_float(state_vector_v2.get("fast_exit_risk_penalty", 0.0), 0.0)
    topdown_state_label = _to_str(state_meta.get("topdown_state_label", "")).upper()
    patience_state_label = _to_str(state_meta.get("patience_state_label", "")).upper()
    execution_friction_state = _to_str(state_meta.get("execution_friction_state", "")).upper()
    session_exhaustion_state = _to_str(state_meta.get("session_exhaustion_state", "")).upper()
    event_risk_state = _to_str(state_meta.get("event_risk_state", "")).upper()
    entry_direction = _to_str(entry_direction, "").upper()

    aligned_with_entry = bool(
        (entry_direction == "BUY" and topdown_state_label == "BULL_CONFLUENCE")
        or (entry_direction == "SELL" and topdown_state_label == "BEAR_CONFLUENCE")
    )
    countertrend_with_entry = bool(
        (entry_direction == "BUY" and topdown_state_label == "BEAR_CONFLUENCE")
        or (entry_direction == "SELL" and topdown_state_label == "BULL_CONFLUENCE")
        or topdown_state_label == "TOPDOWN_CONFLICT"
    )
    hold_bias = max(0.0, (hold_gain - 1.0) * 0.34)
    wait_bias = max(0.0, (wait_gain - 1.0) * 0.28)
    exit_pressure = max(0.0, fast_exit_risk * 0.28)

    if aligned_with_entry:
        hold_bias += 0.08
        wait_bias += 0.04
    if countertrend_with_entry:
        exit_pressure += 0.10
    if patience_state_label == "HOLD_FAVOR":
        hold_bias += 0.06
    elif patience_state_label == "WAIT_FAVOR":
        wait_bias += 0.06
    elif patience_state_label == "FAST_EXIT_FAVOR":
        exit_pressure += 0.12
    if execution_friction_state == "HIGH_FRICTION":
        exit_pressure += 0.12
    elif execution_friction_state == "LOW_FRICTION":
        hold_bias += 0.03
    if session_exhaustion_state == "HIGH_EXHAUSTION_RISK":
        exit_pressure += 0.10
    elif session_exhaustion_state == "LOW_EXHAUSTION_RISK":
        hold_bias += 0.02
    if event_risk_state == "HIGH_EVENT_RISK":
        exit_pressure += 0.14
    elif event_risk_state == "LOW_EVENT_RISK":
        wait_bias += 0.02

    prefer_hold_through_green = bool(
        hold_gain >= 1.02
        and fast_exit_risk < 0.52
        and execution_friction_state != "HIGH_FRICTION"
        and event_risk_state != "HIGH_EVENT_RISK"
        and session_exhaustion_state != "HIGH_EXHAUSTION_RISK"
    )
    prefer_fast_cut = bool(
        fast_exit_risk >= 0.55
        or patience_state_label == "FAST_EXIT_FAVOR"
        or execution_friction_state == "HIGH_FRICTION"
        or event_risk_state == "HIGH_EVENT_RISK"
        or session_exhaustion_state == "HIGH_EXHAUSTION_RISK"
    )

    return {
        "prefer_hold_through_green": bool(prefer_hold_through_green),
        "prefer_fast_cut": bool(prefer_fast_cut),
        "hold_bias": _round6(_clamp(hold_bias, 0.0, 0.32), 0.0),
        "wait_bias": _round6(_clamp(wait_bias, 0.0, 0.24), 0.0),
        "exit_pressure": _round6(_clamp(exit_pressure, 0.0, 0.40), 0.0),
        "aligned_with_entry": bool(aligned_with_entry),
        "countertrend_with_entry": bool(countertrend_with_entry),
        "topdown_state_label": str(topdown_state_label),
        "patience_state_label": str(patience_state_label),
        "execution_friction_state": str(execution_friction_state),
        "session_exhaustion_state": str(session_exhaustion_state),
        "event_risk_state": str(event_risk_state),
    }


def build_exit_utility_input_v1(
    *,
    symbol: str = "",
    wait_state: Any = None,
    stage_inputs: Mapping[str, Any] | None = None,
    exit_predictions: Mapping[str, Any] | None = None,
    wait_predictions: Mapping[str, Any] | None = None,
    exit_profile_id: str = "",
    roundtrip_cost: float = 0.0,
) -> dict[str, Any]:
    stage_inputs_map = _as_mapping(stage_inputs)
    exit_predictions_map = _as_mapping(exit_predictions)
    wait_predictions_map = _as_mapping(wait_predictions)
    wait_meta = _as_mapping(getattr(wait_state, "metadata", {}))
    wait_surface = compact_exit_wait_state_surface_v1(wait_meta.get("exit_wait_state_surface_v1"))
    wait_state_input = _as_mapping(wait_meta.get("exit_wait_state_input_v1"))
    wait_state_identity = _as_mapping(wait_state_input.get("identity"))
    wait_state_market = _as_mapping(wait_state_input.get("market"))
    wait_state_policy = _as_mapping(wait_state_input.get("policy"))

    symbol_u = _to_str(symbol or wait_state_identity.get("symbol", ""), "").upper()
    state = _to_str(getattr(wait_state, "state", "NONE"), "NONE").upper()
    reason = _to_str(getattr(wait_state, "reason", ""))
    exit_profile = _to_str(exit_profile_id, "").lower()
    entry_setup_id = _to_str(
        wait_meta.get("entry_setup_id", wait_state_identity.get("entry_setup_id", "")),
        "",
    ).lower()
    regime_now = _to_str(
        stage_inputs_map.get(
            "regime_now",
            wait_meta.get("regime_now", wait_state_market.get("regime_now", "UNKNOWN")),
        ),
        "UNKNOWN",
    ).upper()
    current_box_state = _to_str(
        stage_inputs_map.get(
            "current_box_state",
            wait_meta.get("current_box_state", wait_state_market.get("current_box_state", "UNKNOWN")),
        ),
        "UNKNOWN",
    ).upper()
    current_bb_state = _to_str(
        stage_inputs_map.get(
            "current_bb_state",
            wait_meta.get("current_bb_state", wait_state_market.get("current_bb_state", "UNKNOWN")),
        ),
        "UNKNOWN",
    ).upper()
    entry_direction = _to_str(
        stage_inputs_map.get(
            "entry_direction",
            wait_meta.get("entry_direction", wait_state_identity.get("entry_direction", "")),
        ),
        "",
    ).upper()
    profit = _to_float(stage_inputs_map.get("profit", 0.0), 0.0)
    peak_profit = _to_float(stage_inputs_map.get("peak_profit", profit), profit)
    giveback = max(0.0, float(peak_profit - profit))
    score_gap = abs(_to_float(stage_inputs_map.get("score_gap", 0.0), 0.0))
    adverse_risk = _to_bool(stage_inputs_map.get("adverse_risk", False), False)
    duration_sec = _to_float(stage_inputs_map.get("duration_sec", 0.0), 0.0)
    reverse_gap_required = max(
        1,
        int(
            wait_meta.get(
                "reverse_score_gap",
                wait_state_policy.get(
                    "reverse_score_gap",
                    getattr(Config, "EXIT_RECOVERY_REVERSE_SCORE_GAP", 26),
                ),
            )
            or getattr(Config, "EXIT_RECOVERY_REVERSE_SCORE_GAP", 26)
        ),
    )
    reverse_min_prob = max(
        0.05,
        float(getattr(Config, "EXIT_RECOVERY_REVERSE_MIN_PROB", 0.58)),
    )
    reverse_min_hold_seconds = max(
        0.0,
        float(getattr(Config, "EXIT_RECOVERY_REVERSE_MIN_HOLD_SECONDS", 45)),
    )
    state_execution_bias_v1 = resolve_exit_utility_state_bias_v1(
        stage_inputs_map,
        entry_direction=entry_direction,
    )
    expected_exit_improvement_default = max(
        0.05,
        (abs(float(profit)) * 0.35) + (0.10 if state != "NONE" else 0.0),
    )

    return {
        "contract_version": "exit_utility_input_v1",
        "identity": {
            "symbol": str(symbol_u),
            "state": str(state),
            "reason": str(reason),
            "exit_profile_id": str(exit_profile),
            "entry_setup_id": str(entry_setup_id),
            "entry_direction": str(entry_direction),
        },
        "market": {
            "regime_now": str(regime_now),
            "current_box_state": str(current_box_state),
            "current_bb_state": str(current_bb_state),
        },
        "risk": {
            "profit": _round6(profit, 0.0),
            "peak_profit": _round6(peak_profit, profit),
            "giveback": _round6(giveback, 0.0),
            "score_gap": _round6(score_gap, 0.0),
            "adverse_risk": bool(adverse_risk),
            "duration_sec": _round6(duration_sec, 0.0),
            "roundtrip_cost": _round6(roundtrip_cost, 0.0),
        },
        "policy": {
            "allow_wait_be": _to_bool(wait_meta.get("allow_wait_be", True), True),
            "allow_wait_tp1": _to_bool(wait_meta.get("allow_wait_tp1", False), False),
            "prefer_reverse": _to_bool(wait_meta.get("prefer_reverse", False), False),
            "recovery_policy_id": _to_str(wait_meta.get("recovery_policy_id", ""), ""),
            "reverse_gap_required": int(reverse_gap_required),
            "reverse_min_prob": _round6(reverse_min_prob, 0.58),
            "reverse_min_hold_seconds": _round6(reverse_min_hold_seconds, 45.0),
        },
        "prediction": {
            "p_more_profit": _round6(exit_predictions_map.get("p_more_profit", 0.5), 0.5),
            "p_giveback": _round6(exit_predictions_map.get("p_giveback", 0.4), 0.4),
            "p_reverse_valid": _round6(exit_predictions_map.get("p_reverse_valid", 0.25), 0.25),
            "p_better_exit_if_wait": _round6(
                wait_predictions_map.get("p_better_exit_if_wait", 0.10),
                0.10,
            ),
            "expected_exit_improvement": _round6(
                wait_predictions_map.get(
                    "expected_exit_improvement",
                    expected_exit_improvement_default,
                ),
                expected_exit_improvement_default,
            ),
            "expected_miss_cost": _round6(
                wait_predictions_map.get("expected_miss_cost", 0.12),
                0.12,
            ),
            "expected_exit_improvement_default": _round6(
                expected_exit_improvement_default,
                expected_exit_improvement_default,
            ),
        },
        "bias": {
            "state_execution_bias_v1": dict(state_execution_bias_v1),
            "symbol_edge_execution_overrides_v1": dict(
                _as_mapping(wait_meta.get("symbol_edge_execution_overrides_v1"))
            ),
        },
        "detail": {
            "wait_surface_contract_version": _to_str(wait_surface.get("contract_version", "")),
            "wait_state_input_contract_version": _to_str(
                wait_state_input.get("contract_version", "")
            ),
        },
        "context": {
            "exit_wait_state_surface_v1": dict(wait_surface),
            "exit_wait_state_input_v1": dict(wait_state_input),
        },
    }


def compact_exit_utility_input_v1(
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract_map = _as_mapping(contract)
    identity = _as_mapping(contract_map.get("identity"))
    market = _as_mapping(contract_map.get("market"))
    risk = _as_mapping(contract_map.get("risk"))
    policy = _as_mapping(contract_map.get("policy"))
    prediction = _as_mapping(contract_map.get("prediction"))
    bias = _as_mapping(contract_map.get("bias"))
    detail = _as_mapping(contract_map.get("detail"))
    context = _as_mapping(contract_map.get("context"))
    wait_surface = compact_exit_wait_state_surface_v1(context.get("exit_wait_state_surface_v1"))

    return {
        "contract_version": _to_str(contract_map.get("contract_version", "exit_utility_input_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "state": _to_str(identity.get("state", "NONE"), "NONE").upper(),
            "reason": _to_str(identity.get("reason", "")),
            "exit_profile_id": _to_str(identity.get("exit_profile_id", "")),
            "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
        },
        "market": {
            "regime_now": _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": _to_str(
                market.get("current_box_state", "UNKNOWN"),
                "UNKNOWN",
            ).upper(),
            "current_bb_state": _to_str(
                market.get("current_bb_state", "UNKNOWN"),
                "UNKNOWN",
            ).upper(),
        },
        "risk": {
            "profit": _round6(risk.get("profit", 0.0), 0.0),
            "peak_profit": _round6(risk.get("peak_profit", 0.0), 0.0),
            "giveback": _round6(risk.get("giveback", 0.0), 0.0),
            "score_gap": _round6(risk.get("score_gap", 0.0), 0.0),
            "adverse_risk": _to_bool(risk.get("adverse_risk", False), False),
            "duration_sec": _round6(risk.get("duration_sec", 0.0), 0.0),
            "roundtrip_cost": _round6(risk.get("roundtrip_cost", 0.0), 0.0),
        },
        "policy": {
            "allow_wait_be": _to_bool(policy.get("allow_wait_be", False), False),
            "allow_wait_tp1": _to_bool(policy.get("allow_wait_tp1", False), False),
            "prefer_reverse": _to_bool(policy.get("prefer_reverse", False), False),
            "recovery_policy_id": _to_str(policy.get("recovery_policy_id", "")),
            "reverse_gap_required": int(_to_float(policy.get("reverse_gap_required", 0), 0.0)),
            "reverse_min_prob": _round6(policy.get("reverse_min_prob", 0.0), 0.0),
            "reverse_min_hold_seconds": _round6(
                policy.get("reverse_min_hold_seconds", 0.0),
                0.0,
            ),
        },
        "prediction": {
            "p_more_profit": _round6(prediction.get("p_more_profit", 0.0), 0.0),
            "p_giveback": _round6(prediction.get("p_giveback", 0.0), 0.0),
            "p_reverse_valid": _round6(prediction.get("p_reverse_valid", 0.0), 0.0),
            "p_better_exit_if_wait": _round6(
                prediction.get("p_better_exit_if_wait", 0.0),
                0.0,
            ),
            "expected_exit_improvement": _round6(
                prediction.get("expected_exit_improvement", 0.0),
                0.0,
            ),
            "expected_miss_cost": _round6(prediction.get("expected_miss_cost", 0.0), 0.0),
        },
        "bias": {
            "state_execution_bias_v1": dict(
                _as_mapping(bias.get("state_execution_bias_v1"))
            ),
            "symbol_edge_execution_overrides_v1": dict(
                _as_mapping(bias.get("symbol_edge_execution_overrides_v1"))
            ),
        },
        "detail": {
            "wait_surface_contract_version": _to_str(
                detail.get("wait_surface_contract_version", "")
            ),
            "wait_state_input_contract_version": _to_str(
                detail.get("wait_state_input_contract_version", "")
            ),
        },
        "context": {
            "exit_wait_state_surface_v1": dict(wait_surface),
        },
    }
