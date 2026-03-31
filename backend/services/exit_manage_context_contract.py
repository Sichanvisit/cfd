"""Shared exit/manage context contract helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.consumer_contract import EXIT_HANDOFF_CONTRACT_V1, resolve_exit_handoff
from backend.services.exit_profile_router import apply_range_lifecycle_profile, resolve_exit_profile


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def build_exit_manage_context_v1(
    *,
    symbol: str = "",
    trade_ctx: Mapping[str, Any] | None = None,
    stage_inputs: Mapping[str, Any] | None = None,
    chosen_stage: str = "",
    policy_stage: str = "",
    exec_profile: str = "",
    confirm_needed: int = 0,
    exit_signal_score: int = 0,
    score_gap: int = 0,
    adverse_risk: bool = False,
    tf_confirm: bool = False,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trade_ctx_map = _as_mapping(trade_ctx)
    stage_inputs_map = _as_mapping(stage_inputs)
    detail_map = _as_mapping(detail)

    symbol_value = _to_str(symbol or trade_ctx_map.get("symbol", "")).upper()
    entry_setup_id = _to_str(trade_ctx_map.get("entry_setup_id", ""))
    entry_direction = _to_str(
        stage_inputs_map.get(
            "entry_direction",
            trade_ctx_map.get("direction", trade_ctx_map.get("entry_direction", "")),
        )
    ).upper()
    exit_handoff_v1 = resolve_exit_handoff(trade_ctx_map)

    management_profile_id = _to_str(exit_handoff_v1.get("management_profile_id", ""))
    invalidation_id = _to_str(exit_handoff_v1.get("invalidation_id", ""))
    base_exit_profile = _to_str(trade_ctx_map.get("exit_profile", ""), _to_str(exec_profile, ""))
    resolved_exit_profile = resolve_exit_profile(
        management_profile_id=management_profile_id,
        invalidation_id=invalidation_id,
        entry_setup_id=entry_setup_id,
        fallback_profile=base_exit_profile,
    )
    regime_now = _to_str(stage_inputs_map.get("regime_now", "UNKNOWN"), "UNKNOWN").upper()
    current_box_state = _to_str(
        stage_inputs_map.get("current_box_state", trade_ctx_map.get("box_state", "UNKNOWN")),
        "UNKNOWN",
    ).upper()
    current_bb_state = _to_str(
        stage_inputs_map.get("current_bb_state", trade_ctx_map.get("bb_state", "UNKNOWN")),
        "UNKNOWN",
    ).upper()
    lifecycle_exit_profile = apply_range_lifecycle_profile(
        base_profile=resolved_exit_profile,
        regime_name=regime_now,
        current_box_state=current_box_state,
    )

    profit = _to_float(stage_inputs_map.get("profit", trade_ctx_map.get("profit", 0.0)), 0.0)
    peak_profit = _to_float(
        stage_inputs_map.get("peak_profit", trade_ctx_map.get("peak_profit_at_exit", profit)),
        profit,
    )
    giveback = max(0.0, float(peak_profit - profit))
    duration_sec = _to_float(stage_inputs_map.get("duration_sec", trade_ctx_map.get("duration_sec", 0.0)), 0.0)

    return {
        "contract_version": "exit_manage_context_v1",
        "identity": {
            "symbol": str(symbol_value),
            "entry_setup_id": str(entry_setup_id),
            "entry_direction": str(entry_direction),
        },
        "handoff": {
            "management_profile_id": str(management_profile_id),
            "invalidation_id": str(invalidation_id),
            "handoff_source": _to_str(exit_handoff_v1.get("handoff_source", "")),
            "exit_handoff_v1": dict(exit_handoff_v1),
            "exit_handoff_contract_v1": dict(EXIT_HANDOFF_CONTRACT_V1),
        },
        "posture": {
            "chosen_stage": _to_str(chosen_stage),
            "policy_stage": _to_str(policy_stage),
            "execution_profile": _to_str(exec_profile),
            "base_exit_profile": str(base_exit_profile),
            "resolved_exit_profile": _to_str(resolved_exit_profile),
            "lifecycle_exit_profile": _to_str(lifecycle_exit_profile or resolved_exit_profile or base_exit_profile),
        },
        "market": {
            "regime_now": str(regime_now),
            "regime_at_entry": _to_str(stage_inputs_map.get("regime_at_entry", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": str(current_box_state),
            "current_bb_state": str(current_bb_state),
        },
        "risk": {
            "profit": float(profit),
            "peak_profit": float(peak_profit),
            "giveback": float(giveback),
            "duration_sec": float(duration_sec),
            "favorable_move_pct": _to_float(stage_inputs_map.get("favorable_move_pct", 0.0), 0.0),
            "spread_ratio": _to_float(stage_inputs_map.get("spread_ratio", 1.0), 1.0),
            "adverse_risk": _to_bool(adverse_risk),
            "tf_confirm": _to_bool(tf_confirm),
            "confirm_needed": _to_int(confirm_needed),
            "exit_signal_score": _to_int(exit_signal_score),
            "score_gap": _to_int(score_gap),
        },
        "detail": {
            "route_txt": _to_str(detail_map.get("route_txt", "")),
            "exit_threshold": detail_map.get("exit_threshold", ""),
            "reverse_signal_threshold": detail_map.get("reverse_signal_threshold", ""),
        },
    }


def compact_exit_manage_context_v1(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context_map = _as_mapping(context)
    identity = _as_mapping(context_map.get("identity"))
    handoff = _as_mapping(context_map.get("handoff"))
    posture = _as_mapping(context_map.get("posture"))
    market = _as_mapping(context_map.get("market"))
    risk = _as_mapping(context_map.get("risk"))
    detail = _as_mapping(context_map.get("detail"))

    return {
        "contract_version": _to_str(context_map.get("contract_version", "exit_manage_context_v1")),
        "identity": {
            "symbol": _to_str(identity.get("symbol", "")).upper(),
            "entry_setup_id": _to_str(identity.get("entry_setup_id", "")),
            "entry_direction": _to_str(identity.get("entry_direction", "")).upper(),
        },
        "handoff": {
            "management_profile_id": _to_str(handoff.get("management_profile_id", "")),
            "invalidation_id": _to_str(handoff.get("invalidation_id", "")),
            "handoff_source": _to_str(handoff.get("handoff_source", "")),
        },
        "posture": {
            "chosen_stage": _to_str(posture.get("chosen_stage", "")),
            "policy_stage": _to_str(posture.get("policy_stage", "")),
            "execution_profile": _to_str(posture.get("execution_profile", "")),
            "resolved_exit_profile": _to_str(posture.get("resolved_exit_profile", "")),
            "lifecycle_exit_profile": _to_str(posture.get("lifecycle_exit_profile", "")),
        },
        "market": {
            "regime_now": _to_str(market.get("regime_now", "UNKNOWN"), "UNKNOWN").upper(),
            "regime_at_entry": _to_str(market.get("regime_at_entry", "UNKNOWN"), "UNKNOWN").upper(),
            "current_box_state": _to_str(market.get("current_box_state", "UNKNOWN"), "UNKNOWN").upper(),
            "current_bb_state": _to_str(market.get("current_bb_state", "UNKNOWN"), "UNKNOWN").upper(),
        },
        "risk": {
            "profit": _to_float(risk.get("profit", 0.0), 0.0),
            "peak_profit": _to_float(risk.get("peak_profit", 0.0), 0.0),
            "giveback": _to_float(risk.get("giveback", 0.0), 0.0),
            "duration_sec": _to_float(risk.get("duration_sec", 0.0), 0.0),
            "adverse_risk": _to_bool(risk.get("adverse_risk", False)),
            "tf_confirm": _to_bool(risk.get("tf_confirm", False)),
            "confirm_needed": _to_int(risk.get("confirm_needed", 0), 0),
            "exit_signal_score": _to_int(risk.get("exit_signal_score", 0), 0),
            "score_gap": _to_int(risk.get("score_gap", 0), 0),
        },
        "detail": {
            "route_txt": _to_str(detail.get("route_txt", "")),
        },
    }
