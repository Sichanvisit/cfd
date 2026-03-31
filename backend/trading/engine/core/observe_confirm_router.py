from __future__ import annotations

from types import SimpleNamespace

from backend.services.symbol_temperament import canonical_symbol, resolve_probe_temperament
from backend.trading.chart_flow_policy import build_common_expression_policy_v1
from backend.trading.chart_symbol_override_policy import build_symbol_override_policy_v1

from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    ObserveConfirmSnapshot,
    PositionSnapshot,
    PositionVector,
    ResponseVector,
    StateVector,
    StateVectorV2,
    TradeManagementForecast,
    TransitionForecast,
)

ARCHETYPE_UPPER_REJECT_SELL = "upper_reject_sell"
ARCHETYPE_UPPER_BREAK_BUY = "upper_break_buy"
ARCHETYPE_LOWER_HOLD_BUY = "lower_hold_buy"
ARCHETYPE_LOWER_BREAK_SELL = "lower_break_sell"
ARCHETYPE_MID_RECLAIM_BUY = "mid_reclaim_buy"
ARCHETYPE_MID_LOSE_SELL = "mid_lose_sell"

INVALIDATION_BY_ARCHETYPE = {
    ARCHETYPE_UPPER_REJECT_SELL: "upper_break_reclaim",
    ARCHETYPE_UPPER_BREAK_BUY: "breakout_failure",
    ARCHETYPE_LOWER_HOLD_BUY: "lower_support_fail",
    ARCHETYPE_LOWER_BREAK_SELL: "breakdown_failure",
    ARCHETYPE_MID_RECLAIM_BUY: "mid_relose",
    ARCHETYPE_MID_LOSE_SELL: "mid_reclaim",
}

MANAGEMENT_PROFILE_BY_ARCHETYPE = {
    ARCHETYPE_UPPER_REJECT_SELL: "reversal_profile",
    ARCHETYPE_UPPER_BREAK_BUY: "breakout_hold_profile",
    ARCHETYPE_LOWER_HOLD_BUY: "support_hold_profile",
    ARCHETYPE_LOWER_BREAK_SELL: "breakdown_hold_profile",
    ARCHETYPE_MID_RECLAIM_BUY: "mid_reclaim_fast_exit_profile",
    ARCHETYPE_MID_LOSE_SELL: "mid_lose_fast_exit_profile",
}

_READINESS_POSITION_WEIGHTS = {
    "bb20": 0.42,
    "box": 0.34,
    "bb44": 0.16,
    "sr": 0.05,
    "trendline": 0.03,
}
_READINESS_MIDDLE_BOX_LIMIT = 0.42
_READINESS_MIDDLE_BB20_LIMIT = 0.42
_READINESS_MIDDLE_BB44_LIMIT = 0.48
_MIDDLE_ENTRY_SR_ANCHOR_THRESHOLD = 0.35
_REVERSAL_BB44_SUPPORT_THRESHOLD = 0.12
_REVERSAL_SR_OVERRIDE_THRESHOLD = 0.55
_MIXED_UPPER_REJECT_MIN_RESPONSE = 0.70
_MIXED_UPPER_REJECT_BB44_CONFIRM_THRESHOLD = 0.18
_MIXED_UPPER_REJECT_BB20_MIN = -0.02
_UPPER_RECLAIM_DOMINANCE_MIN = 0.16
_UPPER_RECLAIM_DOMINANCE_ADVANTAGE = 0.04
_UPPER_RECLAIM_SELL_SUPPORT_MARGIN = 0.35
_UPPER_BREAK_CONTINUATION_ADVANTAGE = 0.03
_UPPER_BREAK_CONTINUATION_OPPOSING_SCALE = 0.45
_EDGE_PROBE_FLOOR_MULT = 0.72
_EDGE_PROBE_ADVANTAGE_MULT = 0.25
_EDGE_PROBE_SUPPORT_TOLERANCE = 0.015
_XAU_UPPER_STRUCTURAL_REJECT_MIN = 0.12
_XAU_UPPER_PROBE_FLOOR_MULT = 0.60
_XAU_UPPER_PROBE_ADVANTAGE_MULT = 0.10
_XAU_UPPER_PROBE_SUPPORT_TOLERANCE = 0.04
_XAU_LOWER_SECOND_SUPPORT_STRUCTURAL_MIN = 0.14
_XAU_LOWER_SECOND_SUPPORT_RECLAIM_MIN = 0.18
_XAU_LOWER_SECOND_SUPPORT_SECONDARY_MIN = 0.10
_XAU_LOWER_SECOND_SUPPORT_PERSISTENCE_MIN = 0.10
_XAU_LOWER_SECOND_SUPPORT_BELIEF_MIN = 0.46
_BTC_LOWER_PROBE_FLOOR_MULT = 0.86
_BTC_LOWER_PROBE_ADVANTAGE_MULT = 0.42
_BTC_LOWER_PROBE_SUPPORT_TOLERANCE = 0.010
_BTC_LOWER_STRUCTURAL_SUPPORT_MIN = 0.22
_BTC_LOWER_STRUCTURAL_RECLAIM_MIN = 0.16
_BTC_LOWER_STRUCTURAL_SECONDARY_MIN = 0.08
_BTC_LOWER_CONTEXT_SUPPORT_MIN = 0.46
_BTC_LOWER_CONTEXT_PAIR_GAP_MIN = 0.18
_BTC_LOWER_CONTEXT_BB44_MAX = 0.18
_BTC_LOWER_CONTEXT_SR_MIN = -0.18
_NAS_CLEAN_PROBE_FLOOR_MULT = 0.78
_NAS_CLEAN_PROBE_ADVANTAGE_MULT = 0.30
_NAS_CLEAN_PROBE_SUPPORT_TOLERANCE = 0.012

StateInput = StateVector | StateVectorV2

_COMMON_EXPRESSION_POLICY_V1 = build_common_expression_policy_v1()
_SYMBOL_OVERRIDE_POLICY_V1 = build_symbol_override_policy_v1()


def _common_policy_section(section_name: str) -> dict:
    section = _COMMON_EXPRESSION_POLICY_V1.get(str(section_name or ""))
    return section if isinstance(section, dict) else {}


def _policy_upper_map(values, *, default=None) -> dict[str, object]:
    mapping = values if isinstance(values, dict) else (default or {})
    out = {}
    for key, value in dict(mapping).items():
        key_n = str(key).strip().upper()
        if key_n:
            out[key_n] = value
    return out


def _policy_float(value, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = float(default)
    return float(parsed) if parsed == parsed else float(default)


def _readiness_by_state(field_name: str, *, default: dict[str, float]) -> dict[str, float]:
    readiness = _common_policy_section("readiness")
    mapping = _policy_upper_map(readiness.get(str(field_name or "")), default=default)
    out = {}
    for key, fallback in dict(default).items():
        out[str(key).upper()] = _policy_float(mapping.get(str(key).upper(), fallback), default=float(fallback))
    return out


def _probe_policy_value(field_name: str, *, default: float) -> float:
    probe = _common_policy_section("probe")
    return _policy_float(probe.get(str(field_name or "")), default=default)


def _symbol_override_policy_root() -> dict:
    payload = _SYMBOL_OVERRIDE_POLICY_V1
    return payload if isinstance(payload, dict) else {}


def _symbol_override_lookup(symbol: str, *path: str):
    symbols = _symbol_override_policy_root().get("symbols", {})
    if not isinstance(symbols, dict):
        return None
    node = symbols.get(canonical_symbol(symbol), {})
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(str(key or ""))
    return node


def _symbol_override_dict(symbol: str, *path: str) -> dict:
    payload = _symbol_override_lookup(symbol, *path)
    return dict(payload or {}) if isinstance(payload, dict) else {}


def _symbol_override_flag(symbol: str, *path: str, default: bool) -> bool:
    value = _symbol_override_lookup(symbol, *path)
    if isinstance(value, dict):
        value = value.get("enabled", default)
    return bool(default if value is None else value)


def _symbol_override_float(symbol: str, *path: str, default: float) -> float:
    value = _symbol_override_lookup(symbol, *path)
    return _policy_float(value, default=default)


def _apply_symbol_override_probe_temperament(symbol: str, temperament: dict[str, object]) -> dict[str, object]:
    payload = dict(temperament or {})
    scene_id = str(payload.get("scene_id", "") or "").strip()
    override_path: tuple[str, ...] | None = None
    if scene_id == "xau_upper_sell_probe":
        override_path = ("router", "probe", "upper_reject")
    elif scene_id == "btc_lower_buy_conservative_probe":
        override_path = ("router", "probe", "lower_rebound")
    elif scene_id == "btc_upper_sell_probe":
        override_path = ("router", "probe", "upper_reject")
    elif scene_id == "nas_clean_confirm_probe":
        override_path = ("router", "probe", "clean_confirm")

    if override_path is None or not _symbol_override_flag(symbol, *override_path, default=True):
        return payload

    for field_name in ("floor_mult", "advantage_mult", "support_tolerance"):
        if field_name in payload or _symbol_override_lookup(symbol, *override_path, field_name) is not None:
            payload[field_name] = _symbol_override_float(
                symbol,
                *override_path,
                field_name,
                default=_policy_float(payload.get(field_name), default=0.0),
            )
    return payload


def _probe_temperament_value(
    temperament: dict | None,
    *,
    key: str,
    policy_field: str,
    default: float,
) -> float:
    payload = temperament if isinstance(temperament, dict) else {}
    baseline = _probe_policy_value(policy_field, default=default)
    return _policy_float(payload.get(str(key or ""), baseline), default=baseline)


def _nas_clean_confirm_middle_anchor_relief(
    *,
    symbol: str,
    side: str,
    direction_policy: str,
    candidate_support: float,
    edge_pair_law: dict | None,
    probe_temperament: dict | None,
    forecast_assist: dict | None,
) -> bool:
    symbol_u = canonical_symbol(symbol)
    scene_id = str((probe_temperament or {}).get("scene_id", "") or "")
    side_u = str(side or "").upper()
    direction_policy_u = str(direction_policy or "").upper()
    edge = dict(edge_pair_law or {})
    forecast = dict(forecast_assist or {})

    if symbol_u != "NAS100" or scene_id != "nas_clean_confirm_probe":
        return False
    if not _symbol_override_flag(symbol_u, "router", "relief", "clean_confirm_middle_anchor", default=True):
        return False
    if side_u not in {"BUY", "SELL"}:
        return False
    if side_u == "BUY" and direction_policy_u not in {"BOTH", "BUY_ONLY"}:
        return False
    if side_u == "SELL" and direction_policy_u not in {"BOTH", "SELL_ONLY"}:
        return False
    if str(edge.get("winner_side", "") or "").upper() != side_u or not bool(edge.get("winner_clear")):
        return False

    context_label = str(edge.get("context_label", "") or "").upper()
    if side_u == "BUY" and context_label not in {"LOWER_EDGE", "LOWER"}:
        return False
    if side_u == "SELL" and context_label not in {"UPPER_EDGE", "UPPER"}:
        return False

    if float(candidate_support) < _symbol_override_float(
        symbol_u,
        "router",
        "relief",
        "clean_confirm_middle_anchor",
        "support_min",
        default=0.34,
    ):
        return False
    if float(edge.get("pair_gap", 0.0) or 0.0) < _symbol_override_float(
        symbol_u,
        "router",
        "relief",
        "clean_confirm_middle_anchor",
        "pair_gap_min",
        default=0.10,
    ):
        return False

    if bool(forecast.get("present")):
        if float(forecast.get("confirm_fake_gap", 0.0) or 0.0) < _symbol_override_float(
            symbol_u,
            "router",
            "relief",
            "clean_confirm_middle_anchor",
            "confirm_fake_gap_min",
            default=-0.08,
        ):
            return False
        if float(forecast.get("wait_confirm_gap", 0.0) or 0.0) < _symbol_override_float(
            symbol_u,
            "router",
            "relief",
            "clean_confirm_middle_anchor",
            "wait_confirm_gap_min",
            default=-0.05,
        ):
            return False

    return True


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _max_abs(*values: float) -> float:
    return max(abs(float(v)) for v in values)


def _gap_value(gaps: dict[str, float] | None, key: str, default: float = 0.0) -> float:
    if not isinstance(gaps, dict):
        return float(default)
    return float(gaps.get(key, default) or default)


def _symbol(position: PositionVector, state: StateInput) -> str:
    return str((position.metadata or {}).get("symbol") or (state.metadata or {}).get("symbol") or "").upper()


def _symbol_probe_temperament(
    symbol: str,
    *,
    context_label: str,
    trigger_branch: str,
    probe_direction: str,
    second_support_relief: bool = False,
) -> dict[str, object]:
    return _apply_symbol_override_probe_temperament(
        symbol,
        resolve_probe_temperament(
            symbol,
            context_label=context_label,
            trigger_branch=trigger_branch,
            probe_direction=probe_direction,
            second_support_relief=second_support_relief,
        ),
    )


def _state_v2_payload(state: StateInput) -> tuple[dict, dict]:
    if isinstance(state, StateVectorV2):
        payload = dict(state.to_dict() or {})
        meta = dict(payload.get("metadata") or {})
        return payload, meta
    metadata = dict(getattr(state, "metadata", {}) or {})
    payload = metadata.get("state_vector_v2", {})
    if not isinstance(payload, dict):
        payload = {}
    payload = dict(payload)
    meta = dict(payload.get("metadata") or {})
    return payload, meta


def _state_source_fields(state: StateInput) -> dict[str, float | str]:
    metadata = dict(getattr(state, "metadata", {}) or {})
    if isinstance(state, StateVectorV2):
        return {
            "market_mode": str(metadata.get("source_regime", "UNKNOWN") or "UNKNOWN").upper(),
            "direction_policy": str(metadata.get("source_direction_policy", "UNKNOWN") or "UNKNOWN").upper(),
            "s_noise": float(metadata.get("source_noise", 0.0) or 0.0),
            "s_conflict": float(metadata.get("source_conflict", 0.0) or 0.0),
            "s_alignment": float(metadata.get("source_alignment", 0.0) or 0.0),
            "s_disparity": float(metadata.get("source_disparity", 0.0) or 0.0),
            "s_volatility": float(metadata.get("source_volatility", 0.0) or 0.0),
            "state_contract": str(metadata.get("state_contract", "canonical_v3") or "canonical_v3"),
            "state_mapper_version": str(metadata.get("mapper_version", "") or ""),
            "state_input_mode": "state_vector_v2_direct",
        }
    return {
        "market_mode": str(state.market_mode or "UNKNOWN").upper(),
        "direction_policy": str(state.direction_policy or "UNKNOWN").upper(),
        "s_noise": float(state.s_noise or 0.0),
        "s_conflict": float(state.s_conflict or 0.0),
        "s_alignment": float(state.s_alignment or 0.0),
        "s_disparity": float(state.s_disparity or 0.0),
        "s_volatility": float(state.s_volatility or 0.0),
        "state_contract": str(metadata.get("state_contract", "legacy_v1") or "legacy_v1"),
        "state_mapper_version": str(metadata.get("mapper_version", "") or ""),
        "state_input_mode": "state_vector_legacy",
    }


def _state_execution_scales(state: StateInput) -> dict[str, float | str]:
    payload, meta = _state_v2_payload(state)
    if not payload:
        return {
            "buy_scale": 1.0,
            "sell_scale": 1.0,
            "confirm_gain": 1.0,
            "wait_gain": 1.0,
            "hold_gain": 1.0,
            "fast_exit_risk": 0.0,
            "topdown_state_label": "",
            "quality_state_label": "",
            "patience_state_label": "",
            "execution_friction_state": "",
            "session_exhaustion_state": "",
            "event_risk_state": "",
        }

    confirm_gain = float(payload.get("confirm_aggression_gain", 1.0) or 1.0)
    wait_gain = float(payload.get("wait_patience_gain", 1.0) or 1.0)
    hold_gain = float(payload.get("hold_patience_gain", 1.0) or 1.0)
    fast_exit_risk = float(payload.get("fast_exit_risk_penalty", 0.0) or 0.0)
    buy_scale = 1.0 + ((confirm_gain - 1.0) * 0.22) - ((wait_gain - 1.0) * 0.16)
    sell_scale = 1.0 + ((confirm_gain - 1.0) * 0.22) - ((wait_gain - 1.0) * 0.16)

    topdown_state_label = str(meta.get("topdown_state_label", "") or "").upper()
    quality_state_label = str(meta.get("quality_state_label", "") or "").upper()
    patience_state_label = str(meta.get("patience_state_label", "") or "").upper()
    execution_friction_state = str(meta.get("execution_friction_state", "") or "").upper()
    session_exhaustion_state = str(meta.get("session_exhaustion_state", "") or "").upper()
    event_risk_state = str(meta.get("event_risk_state", "") or "").upper()

    if topdown_state_label == "BULL_ALIGNED":
        buy_scale += 0.05
        sell_scale -= 0.03
    elif topdown_state_label == "BEAR_ALIGNED":
        sell_scale += 0.05
        buy_scale -= 0.03

    if quality_state_label == "HIGH_QUALITY":
        buy_scale += 0.03
        sell_scale += 0.03
    elif quality_state_label == "LOW_QUALITY":
        buy_scale -= 0.04
        sell_scale -= 0.04

    if patience_state_label == "WAIT_FAVOR":
        buy_scale -= 0.04
        sell_scale -= 0.04
    elif patience_state_label == "CONFIRM_FAVOR":
        buy_scale += 0.05
        sell_scale += 0.05

    if execution_friction_state == "HIGH_FRICTION":
        buy_scale -= 0.06
        sell_scale -= 0.06
    elif execution_friction_state == "MEDIUM_FRICTION":
        buy_scale -= 0.02
        sell_scale -= 0.02

    if session_exhaustion_state == "HIGH_EXHAUSTION_RISK":
        buy_scale -= 0.03
        sell_scale -= 0.03
    elif session_exhaustion_state == "LOW_EXHAUSTION_RISK":
        buy_scale += 0.02
        sell_scale += 0.02

    if event_risk_state == "HIGH_EVENT_RISK":
        buy_scale -= 0.08
        sell_scale -= 0.08
    elif event_risk_state == "WATCH_EVENT_RISK":
        buy_scale -= 0.03
        sell_scale -= 0.03

    buy_scale = _clamp(buy_scale - (fast_exit_risk * 0.04), 0.86, 1.18)
    sell_scale = _clamp(sell_scale - (fast_exit_risk * 0.04), 0.86, 1.18)
    return {
        "buy_scale": float(buy_scale),
        "sell_scale": float(sell_scale),
        "confirm_gain": float(confirm_gain),
        "wait_gain": float(wait_gain),
        "hold_gain": float(hold_gain),
        "fast_exit_risk": float(fast_exit_risk),
        "topdown_state_label": topdown_state_label,
        "quality_state_label": quality_state_label,
        "patience_state_label": patience_state_label,
        "execution_friction_state": execution_friction_state,
        "session_exhaustion_state": session_exhaustion_state,
        "event_risk_state": event_risk_state,
    }


def _build_forecast_assist(
    *,
    transition_forecast_v1: TransitionForecast | None,
    trade_management_forecast_v1: TradeManagementForecast | None,
    forecast_gap_metrics_v1: dict[str, float] | None,
    side: str = "",
) -> dict[str, object]:
    if transition_forecast_v1 is None and trade_management_forecast_v1 is None and not forecast_gap_metrics_v1:
        return {
            "present": False,
            "target_side": str(side or "").upper(),
            "dominant_transition_side": "BALANCED",
            "confirm_fake_gap": 0.0,
            "wait_confirm_gap": 0.0,
            "continue_fail_gap": 0.0,
            "transition_side_separation": 0.0,
            "management_recover_reentry_gap": 0.0,
            "confirm_bias": 0.0,
            "caution_bias": 0.0,
            "buy_boost": 0.0,
            "sell_boost": 0.0,
            "decision_hint": "NEUTRAL",
        }

    buy_confirm = float(getattr(transition_forecast_v1, "p_buy_confirm", 0.0) or 0.0)
    sell_confirm = float(getattr(transition_forecast_v1, "p_sell_confirm", 0.0) or 0.0)
    false_break = float(getattr(transition_forecast_v1, "p_false_break", 0.0) or 0.0)
    continue_favor = float(getattr(trade_management_forecast_v1, "p_continue_favor", 0.0) or 0.0)
    fail_now = float(getattr(trade_management_forecast_v1, "p_fail_now", 0.0) or 0.0)
    recover_after_pullback = float(getattr(trade_management_forecast_v1, "p_recover_after_pullback", 0.0) or 0.0)
    opposite_edge_reach = float(getattr(trade_management_forecast_v1, "p_opposite_edge_reach", 0.0) or 0.0)

    dominant_transition_side = (
        "BUY"
        if buy_confirm > sell_confirm
        else "SELL"
        if sell_confirm > buy_confirm
        else "BALANCED"
    )
    target_side = str(side or "").upper()
    if target_side not in {"BUY", "SELL"}:
        target_side = dominant_transition_side if dominant_transition_side in {"BUY", "SELL"} else ""

    confirm_fake_gap = _gap_value(
        forecast_gap_metrics_v1,
        "transition_confirm_fake_gap",
        max(max(buy_confirm, sell_confirm) - false_break, 0.0),
    )
    wait_confirm_gap = _gap_value(
        forecast_gap_metrics_v1,
        "wait_confirm_gap",
        max(max(buy_confirm, sell_confirm) - false_break, 0.0),
    )
    continue_fail_gap = _gap_value(
        forecast_gap_metrics_v1,
        "management_continue_fail_gap",
        continue_favor - fail_now,
    )
    transition_side_separation = _gap_value(
        forecast_gap_metrics_v1,
        "transition_side_separation",
        abs(buy_confirm - sell_confirm),
    )
    management_recover_reentry_gap = _gap_value(
        forecast_gap_metrics_v1,
        "management_recover_reentry_gap",
        recover_after_pullback - opposite_edge_reach,
    )

    side_confirm = max(buy_confirm, sell_confirm)
    opposite_confirm = min(buy_confirm, sell_confirm)
    if target_side == "BUY":
        side_confirm = buy_confirm
        opposite_confirm = sell_confirm
    elif target_side == "SELL":
        side_confirm = sell_confirm
        opposite_confirm = buy_confirm

    confirm_bias = _clamp(
        max(side_confirm - opposite_confirm, 0.0) * 0.55
        + max(confirm_fake_gap, 0.0) * 0.35
        + max(transition_side_separation, 0.0) * 0.25
        + max(wait_confirm_gap, 0.0) * 0.20,
        0.0,
        1.0,
    )
    caution_bias = _clamp(
        max(0.04 - wait_confirm_gap, 0.0) * 8.0
        + max(0.04 - continue_fail_gap, 0.0) * 8.0
        + max(false_break - 0.70, 0.0) * 0.40
        + max(fail_now - continue_favor, 0.0) * 0.35,
        0.0,
        1.0,
    )

    buy_boost = max(buy_confirm - sell_confirm, 0.0) * 0.08
    sell_boost = max(sell_confirm - buy_confirm, 0.0) * 0.08
    if dominant_transition_side == "BUY":
        buy_boost += min(0.05, max(confirm_fake_gap, 0.0) * 0.15)
        buy_boost += min(0.03, max(wait_confirm_gap, 0.0) * 0.12)
        buy_boost += min(0.02, max(continue_fail_gap, 0.0) * 0.10)
    elif dominant_transition_side == "SELL":
        sell_boost += min(0.05, max(confirm_fake_gap, 0.0) * 0.15)
        sell_boost += min(0.03, max(wait_confirm_gap, 0.0) * 0.12)
        sell_boost += min(0.02, max(continue_fail_gap, 0.0) * 0.10)

    if caution_bias > 0.0:
        drag = min(0.05, caution_bias * 0.06)
        buy_boost = max(0.0, buy_boost - drag)
        sell_boost = max(0.0, sell_boost - drag)

    decision_hint = "NEUTRAL"
    if confirm_bias >= caution_bias + 0.08:
        decision_hint = "CONFIRM_FAVOR"
    elif caution_bias >= confirm_bias + 0.08:
        decision_hint = "OBSERVE_FAVOR"
    elif max(abs(wait_confirm_gap), abs(continue_fail_gap), abs(confirm_fake_gap)) > 0.0:
        decision_hint = "BALANCED"

    return {
        "present": True,
        "target_side": target_side,
        "dominant_transition_side": dominant_transition_side,
        "buy_confirm": float(buy_confirm),
        "sell_confirm": float(sell_confirm),
        "false_break_score": float(false_break),
        "continue_favor": float(continue_favor),
        "fail_now": float(fail_now),
        "confirm_fake_gap": float(confirm_fake_gap),
        "wait_confirm_gap": float(wait_confirm_gap),
        "continue_fail_gap": float(continue_fail_gap),
        "transition_side_separation": float(transition_side_separation),
        "management_recover_reentry_gap": float(management_recover_reentry_gap),
        "confirm_bias": float(confirm_bias),
        "caution_bias": float(caution_bias),
        "buy_boost": float(max(buy_boost, 0.0)),
        "sell_boost": float(max(sell_boost, 0.0)),
        "decision_hint": decision_hint,
    }


def _confirm_floor(_symbol: str, state_name: str) -> float:
    mapping = _readiness_by_state(
        "confirm_floor_by_state",
        default={
            "TREND_PULLBACK_BUY_CONFIRM": 0.03,
            "TREND_PULLBACK_SELL_CONFIRM": 0.03,
            "FAILED_SELL_RECLAIM_BUY_CONFIRM": 0.03,
            "MID_RECLAIM_CONFIRM": 0.035,
            "MID_REJECT_CONFIRM": 0.035,
            "LOWER_REBOUND_CONFIRM": 0.20,
            "UPPER_REJECT_CONFIRM": 0.20,
            "LOWER_FAIL_CONFIRM": 0.24,
            "UPPER_BREAK_CONFIRM": 0.24,
            "DEFAULT": 0.20,
        },
    )
    state_name_u = str(state_name or "").upper()
    return float(mapping.get(state_name_u, mapping.get("DEFAULT", 0.20)))


def _confirm_advantage(_symbol: str, state_name: str) -> float:
    mapping = _readiness_by_state(
        "confirm_advantage_by_state",
        default={
            "TREND_PULLBACK_BUY_CONFIRM": 0.003,
            "TREND_PULLBACK_SELL_CONFIRM": 0.003,
            "FAILED_SELL_RECLAIM_BUY_CONFIRM": 0.003,
            "MID_RECLAIM_CONFIRM": 0.01,
            "MID_REJECT_CONFIRM": 0.01,
            "LOWER_REBOUND_CONFIRM": 0.003,
            "DEFAULT": 0.02,
        },
    )
    state_name_u = str(state_name or "").upper()
    return float(mapping.get(state_name_u, mapping.get("DEFAULT", 0.02)))


def _btc_lower_buy_context_ok(symbol: str, box_zone: str, x_box: float) -> bool:
    if canonical_symbol(symbol) != "BTCUSD":
        return True
    if box_zone in {"BELOW", "LOWER_EDGE", "LOWER"}:
        return True
    if not _symbol_override_flag(symbol, "router", "context", "lower_buy_context", default=True):
        return False
    middle_x_box_max = _symbol_override_float(
        symbol,
        "router",
        "context",
        "lower_buy_context",
        "middle_x_box_max",
        default=0.12,
    )
    return box_zone == "MIDDLE" and x_box <= middle_x_box_max


def _btc_midline_rebound_transition(
    *,
    symbol: str,
    box_zone: str,
    bb_zone: str,
    x_bb20: float,
    lower_reclaim_response: float,
    upper_reject_response: float,
    mid_lose_response: float,
    upper_break_response: float,
    buy_support: float,
    sell_support: float,
    strong_lower_continuation_context: bool,
    upper_break_continuation_context: bool,
    explicit_upper_reject_signal: bool,
) -> dict[str, object]:
    transition = {
        "active": False,
        "side": "",
        "reason": "",
        "archetype_id": "",
        "confidence": 0.0,
    }
    if canonical_symbol(symbol) != "BTCUSD":
        return transition
    if not _symbol_override_flag(symbol, "router", "context", "midline_rebound_transition", default=True):
        return transition
    if str(box_zone or "").upper() != "LOWER":
        return transition
    if str(bb_zone or "").upper() not in {"MID", "MIDDLE"}:
        return transition
    # Once BTC reclaims the BB20 centerline, keep the original lower-edge
    # buy only when there is a clear continuation/breakout context.
    if float(x_bb20) < 0.0 or float(lower_reclaim_response) <= 0.0:
        return transition
    if bool(strong_lower_continuation_context):
        return transition
    breakout_continuation = bool(
        upper_break_continuation_context
        and float(upper_break_response) >= max(0.12, float(upper_reject_response) + 0.08)
        and float(buy_support) >= float(sell_support) + 0.06
    )
    if breakout_continuation:
        return transition

    if bool(explicit_upper_reject_signal) or float(upper_reject_response) >= 0.08 or float(mid_lose_response) >= 0.06:
        transition["active"] = True
        transition["side"] = "SELL"
        transition["reason"] = "btc_midline_sell_watch"
        transition["archetype_id"] = ARCHETYPE_MID_LOSE_SELL
        transition["confidence"] = _support_confidence(
            max(float(sell_support), float(upper_reject_response), float(mid_lose_response)),
            float(buy_support),
            minimum=0.1,
        )
        return transition

    transition["active"] = True
    transition["side"] = ""
    transition["reason"] = "btc_lower_rebound_mid_expired"
    transition["confidence"] = _support_confidence(abs(float(buy_support) - float(sell_support)), minimum=0.1)
    return transition


def _lower_context_ok(box_zone: str) -> bool:
    return box_zone in {"BELOW", "LOWER_EDGE", "LOWER", "MIDDLE"}


def _upper_context_ok(box_zone: str) -> bool:
    return box_zone in {"MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE"}


def _dominance_side_from_label(dominance_label: str) -> str:
    if dominance_label == "UPPER_DOMINANT_CONFLICT":
        return "UPPER"
    if dominance_label == "LOWER_DOMINANT_CONFLICT":
        return "LOWER"
    if dominance_label == "BALANCED_CONFLICT":
        return "BALANCED"
    return "NONE"


def _strong_continuation_context(primary_label: str, secondary_context_label: str, side: str) -> bool:
    side_n = str(side or "").upper()
    if side_n == "UPPER":
        return primary_label == "ALIGNED_UPPER_STRONG" and secondary_context_label == "UPPER_CONTEXT"
    if side_n == "LOWER":
        return primary_label == "ALIGNED_LOWER_STRONG" and secondary_context_label == "LOWER_CONTEXT"
    return False


def _confirmed_upper_reversal_response(response: ResponseVector) -> bool:
    return (
        float(response.r_bb20_mid_lose) > 0.0
        or float(response.r_box_mid_reject) > 0.0
        or float(response.r_bb20_upper_reject) >= 0.95
        or float(response.r_box_upper_reject) >= 0.95
    )


def _confirmed_lower_reversal_response(response: ResponseVector) -> bool:
    return (
        float(response.r_bb20_mid_reclaim) > 0.0
        or float(response.r_box_mid_hold) > 0.0
        or float(response.r_bb20_lower_hold) >= 0.95
        or float(response.r_box_lower_bounce) >= 0.95
    )


def _explicit_upper_reject_signal(response: ResponseVector) -> bool:
    return (
        float(response.r_bb20_upper_reject) >= 0.70
        or float(response.r_box_upper_reject) >= 0.70
        or float(response.r_bb44_upper_reject) >= _REVERSAL_BB44_SUPPORT_THRESHOLD
        or float(response.r_candle_upper_reject) > 0.0
    )


def _upper_reclaim_dominates_reject(
    *,
    upper_reject_response: float,
    upper_break_response: float,
    buy_support: float,
    sell_support: float,
) -> bool:
    reclaim_pressure = float(upper_break_response)
    return (
        reclaim_pressure >= _UPPER_RECLAIM_DOMINANCE_MIN
        and reclaim_pressure >= float(upper_reject_response) + _UPPER_RECLAIM_DOMINANCE_ADVANTAGE
        and float(buy_support) >= 0.10
        and float(sell_support) <= float(buy_support) + _UPPER_RECLAIM_SELL_SUPPORT_MARGIN
    )


def _upper_break_continuation_context(
    *,
    strong_upper_continuation_context: bool,
    state_meta: dict,
) -> bool:
    regime_state_label = str(state_meta.get("regime_state_label", "") or "").upper()
    topdown_confluence_state = str(state_meta.get("topdown_confluence_state", "") or "").upper()
    return bool(
        strong_upper_continuation_context
        or regime_state_label == "BREAKOUT_EXPANSION"
        or topdown_confluence_state == "BULL_CONFLUENCE"
    )


def _edge_pair_context_label(
    *,
    box_state: str,
    bb_state: str,
    lower_edge_active: bool,
    upper_edge_active: bool,
    lower_depth: float,
    upper_depth: float,
) -> str:
    box_state_u = str(box_state or "").upper()
    bb_state_u = str(bb_state or "").upper()
    middle_box = box_state_u == "MIDDLE"
    middle_bb = bb_state_u in {"MID", "MIDDLE"}
    if lower_edge_active and not upper_edge_active:
        return "LOWER_EDGE"
    if upper_edge_active and not lower_edge_active:
        return "UPPER_EDGE"
    if middle_box and middle_bb:
        return "MIDDLE"
    if lower_edge_active and upper_edge_active:
        return "MIXED_EDGE"
    if lower_depth >= upper_depth + 0.08 and box_state_u in {"BELOW", "LOWER_EDGE", "LOWER", "MIDDLE"}:
        return "LOWER_EDGE"
    if upper_depth >= lower_depth + 0.08 and box_state_u in {"MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE"}:
        return "UPPER_EDGE"
    if middle_box or middle_bb:
        return "MIDDLE"
    return "UNRESOLVED"


def _build_edge_pair_law(
    *,
    context_label: str,
    lower_reclaim_response: float,
    lower_break_response: float,
    upper_reject_response: float,
    upper_break_response: float,
    mid_reclaim_response: float,
    mid_lose_response: float,
) -> dict[str, object]:
    context_label_u = str(context_label or "UNRESOLVED").upper()
    active_branch_side = ""
    active_branch_archetype = ""
    opposing_branch_side = ""
    opposing_branch_archetype = ""
    candidate_buy = 0.0
    candidate_sell = 0.0

    if context_label_u == "LOWER_EDGE":
        candidate_buy = float(lower_reclaim_response)
        candidate_sell = float(lower_break_response)
        active_branch_side = "BUY"
        active_branch_archetype = ARCHETYPE_LOWER_HOLD_BUY
        opposing_branch_side = "SELL"
        opposing_branch_archetype = ARCHETYPE_LOWER_BREAK_SELL
    elif context_label_u == "UPPER_EDGE":
        candidate_buy = float(upper_break_response)
        candidate_sell = float(upper_reject_response)
        active_branch_side = "SELL"
        active_branch_archetype = ARCHETYPE_UPPER_REJECT_SELL
        opposing_branch_side = "BUY"
        opposing_branch_archetype = ARCHETYPE_UPPER_BREAK_BUY
    elif context_label_u == "MIDDLE":
        candidate_buy = float(mid_reclaim_response)
        candidate_sell = float(mid_lose_response)
        active_branch_side = "BUY"
        active_branch_archetype = ARCHETYPE_MID_RECLAIM_BUY
        opposing_branch_side = "SELL"
        opposing_branch_archetype = ARCHETYPE_MID_LOSE_SELL

    pair_gap = float(abs(candidate_buy - candidate_sell))
    winner_side = "BALANCED"
    winner_archetype = ""
    if candidate_buy > candidate_sell:
        winner_side = "BUY"
        winner_archetype = (
            ARCHETYPE_UPPER_BREAK_BUY
            if context_label_u == "UPPER_EDGE"
            else ARCHETYPE_MID_RECLAIM_BUY
            if context_label_u == "MIDDLE"
            else ARCHETYPE_LOWER_HOLD_BUY
        )
    elif candidate_sell > candidate_buy:
        winner_side = "SELL"
        winner_archetype = (
            ARCHETYPE_UPPER_REJECT_SELL
            if context_label_u == "UPPER_EDGE"
            else ARCHETYPE_MID_LOSE_SELL
            if context_label_u == "MIDDLE"
            else ARCHETYPE_LOWER_BREAK_SELL
        )
    winner_clear = bool(max(candidate_buy, candidate_sell) >= 0.05 and pair_gap >= 0.05)
    return {
        "contract_version": "edge_pair_law_v1",
        "context_label": context_label_u,
        "candidate_buy": float(candidate_buy),
        "candidate_sell": float(candidate_sell),
        "pair_gap": float(pair_gap),
        "winner_side": str(winner_side),
        "winner_archetype": str(winner_archetype),
        "winner_clear": bool(winner_clear),
        "active_branch_side": str(active_branch_side),
        "active_branch_archetype": str(active_branch_archetype),
        "opposing_branch_side": str(opposing_branch_side),
        "opposing_branch_archetype": str(opposing_branch_archetype),
    }


def _default_invalidation_id(archetype_id: str) -> str:
    return INVALIDATION_BY_ARCHETYPE.get(str(archetype_id or ""), "")


def _default_management_profile_id(archetype_id: str) -> str:
    return MANAGEMENT_PROFILE_BY_ARCHETYPE.get(str(archetype_id or ""), "")


def _confirm_support_met(
    *,
    candidate_support: float,
    opposing_support: float,
    floor: float,
    advantage: float = 0.0,
) -> bool:
    return float(candidate_support) >= max(float(floor), float(opposing_support) + float(advantage))


def _probe_support_ready(
    *,
    candidate_support: float,
    opposing_support: float,
    floor: float,
    advantage: float = 0.0,
    floor_mult: float | None = None,
    advantage_mult: float | None = None,
    tolerance: float | None = None,
) -> bool:
    if floor_mult is None:
        floor_mult = _probe_policy_value("default_floor_mult", default=_EDGE_PROBE_FLOOR_MULT)
    if advantage_mult is None:
        advantage_mult = _probe_policy_value("default_advantage_mult", default=_EDGE_PROBE_ADVANTAGE_MULT)
    if tolerance is None:
        tolerance = _probe_policy_value("default_support_tolerance", default=_EDGE_PROBE_SUPPORT_TOLERANCE)
    probe_floor = max(0.0, float(floor) * float(floor_mult))
    probe_advantage = max(0.0, float(advantage) * float(advantage_mult))
    return float(candidate_support) >= probe_floor and (
        float(candidate_support) + float(tolerance)
    ) >= (float(opposing_support) + float(probe_advantage))


def _support_confidence(*values: float, minimum: float = 0.0) -> float:
    return min(0.99, max(float(minimum), *(float(value) for value in values)))


def _build_probe_candidate_metadata(
    *,
    probe_direction: str,
    trigger_branch: str,
    candidate_support: float,
    opposing_support: float,
    floor: float,
    advantage: float,
    near_confirm: bool,
    probe_temperament: dict | None = None,
) -> dict:
    return {
        "contract_version": "probe_candidate_v1",
        "active": True,
        "probe_kind": "edge_probe",
        "probe_direction": str(probe_direction or ""),
        "trigger_branch": str(trigger_branch or ""),
        "candidate_support": float(candidate_support),
        "opposing_support": float(opposing_support),
        "floor": float(floor),
        "advantage": float(advantage),
        "near_confirm": bool(near_confirm),
        "symbol_probe_temperament_v1": dict(probe_temperament or {}),
    }


def _resolve_probe_transition_reason(
    *,
    action: str,
    probe_ready: bool,
    confirm_reason: str,
    probe_reason: str,
    observe_reason: str,
) -> str:
    action_u = str(action or "").upper()
    if action_u in {"BUY", "SELL"}:
        return str(probe_reason if probe_ready else confirm_reason)
    return str(observe_reason)


def _emit_probe_transition(
    *,
    emit_confirm,
    emit_observe,
    action: str,
    side: str,
    probe_ready: bool,
    confidence: float,
    confirm_reason: str,
    probe_reason: str,
    observe_reason: str,
    archetype_id: str,
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    reason = _resolve_probe_transition_reason(
        action=action,
        probe_ready=probe_ready,
        confirm_reason=confirm_reason,
        probe_reason=probe_reason,
        observe_reason=observe_reason,
    )
    emitter = emit_confirm if str(action or "").upper() in {"BUY", "SELL"} and not bool(probe_ready) else emit_observe
    return emitter(
        action=action,
        side=side,
        confidence=float(confidence),
        reason=reason,
        archetype_id=archetype_id,
        metadata=dict(metadata or {}),
    )


def _emit_threshold_transition(
    *,
    emit_confirm,
    emit_observe,
    side: str,
    candidate_support: float,
    opposing_support: float,
    floor: float,
    advantage: float,
    confirm_reason: str,
    observe_reason: str,
    archetype_id: str,
    confidence_values: tuple[float, ...] | None = None,
    minimum_confidence: float = 0.1,
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    side_u = str(side or "").upper()
    action = (
        side_u
        if _confirm_support_met(
            candidate_support=candidate_support,
            opposing_support=opposing_support,
            floor=floor,
            advantage=advantage,
        )
        else "WAIT"
    )
    emitter = emit_confirm if action == side_u else emit_observe
    confidence_inputs = tuple(float(value) for value in (confidence_values or (candidate_support,)))
    return emitter(
        action=action,
        side=side_u,
        confidence=_support_confidence(*confidence_inputs, minimum=minimum_confidence),
        reason=confirm_reason if action == side_u else observe_reason,
        archetype_id=archetype_id,
        metadata=dict(metadata or {}),
    )


def _snapshot_guard_exempt(snapshot: ObserveConfirmSnapshot, guard_name: str) -> bool:
    metadata = dict(snapshot.metadata or {})
    exemptions = dict(metadata.get("routing_guard_exemptions") or {})
    return bool(exemptions.get(str(guard_name or "")))


def _has_middle_sr_anchor(position: PositionVector, position_snapshot: PositionSnapshot, *, side: str) -> bool:
    side_n = str(side or "").upper()
    sr_zone = str(position_snapshot.zones.sr_zone or "").upper()
    x_sr = float(position.x_sr)
    if side_n == "BUY":
        return sr_zone in {"BELOW", "LOWER_EDGE", "LOWER"} and x_sr <= -_MIDDLE_ENTRY_SR_ANCHOR_THRESHOLD
    if side_n == "SELL":
        return sr_zone in {"UPPER", "UPPER_EDGE", "ABOVE"} and x_sr >= _MIDDLE_ENTRY_SR_ANCHOR_THRESHOLD
    return False


def _has_outer_band_reversal_support(
    position: PositionVector,
    response: ResponseVector,
    position_snapshot: PositionSnapshot,
    *,
    side: str,
) -> bool:
    side_n = str(side or "").upper()
    bb44_zone = str(position_snapshot.zones.bb44_zone or "").upper()
    x_bb44 = float(position.x_bb44)
    if side_n == "BUY":
        return (
            bb44_zone in {"LOWER", "LOWER_EDGE", "BELOW"}
            or x_bb44 <= -_REVERSAL_BB44_SUPPORT_THRESHOLD
            or float(response.r_bb44_lower_hold) >= _REVERSAL_BB44_SUPPORT_THRESHOLD
        )
    if side_n == "SELL":
        return (
            bb44_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
            or x_bb44 >= _REVERSAL_BB44_SUPPORT_THRESHOLD
            or float(response.r_bb44_upper_reject) >= _REVERSAL_BB44_SUPPORT_THRESHOLD
        )
    return False


def _state_edge_rotation_turn_exempt(snapshot: ObserveConfirmSnapshot, state: StateInput) -> bool:
    side = _directional_side(snapshot)
    if side not in {"BUY", "SELL"}:
        return False
    archetype_id = str(snapshot.archetype_id or "").lower()
    allowed_archetypes = {
        "BUY": {ARCHETYPE_LOWER_HOLD_BUY, ARCHETYPE_MID_RECLAIM_BUY},
        "SELL": {ARCHETYPE_UPPER_REJECT_SELL, ARCHETYPE_MID_LOSE_SELL},
    }
    if archetype_id not in allowed_archetypes.get(side, set()):
        return False
    if float(snapshot.confidence) < 0.10:
        return False
    _, state_meta = _state_v2_payload(state)
    if not state_meta:
        return False

    regime_state_label = str(state_meta.get("regime_state_label", "") or "").upper()
    session_regime_state = str(state_meta.get("session_regime_state", "") or "").upper()
    topdown_confluence_state = str(state_meta.get("topdown_confluence_state", "") or "").upper()
    execution_friction_state = str(state_meta.get("execution_friction_state", "") or "").upper()
    patience_state_label = str(state_meta.get("patience_state_label", "") or "").upper()

    if session_regime_state != "SESSION_EDGE_ROTATION":
        return False
    if regime_state_label not in {"RANGE_SWING", "CHOP_NOISE", "RANGE_COMPRESSION"}:
        return False
    if topdown_confluence_state in {"BULL_CONFLUENCE", "BEAR_CONFLUENCE"}:
        return False
    if execution_friction_state == "HIGH_FRICTION":
        return False
    if patience_state_label == "FAST_EXIT_FAVOR":
        return False
    return True


def _apply_middle_sr_suppression(
    snapshot: ObserveConfirmSnapshot,
    *,
    position: PositionVector,
    position_snapshot: PositionSnapshot,
    state: StateInput,
) -> ObserveConfirmSnapshot:
    if _snapshot_guard_exempt(snapshot, "middle_sr_anchor_guard"):
        return snapshot
    side = _directional_side(snapshot)
    if side not in {"BUY", "SELL"}:
        return snapshot
    zones = position_snapshot.zones
    middle_sensitive = str(zones.box_zone or "").upper() == "MIDDLE" or str(zones.bb20_zone or "").upper() == "MIDDLE"
    if not middle_sensitive:
        return snapshot
    if _has_middle_sr_anchor(position, position_snapshot, side=side):
        return snapshot
    if _state_edge_rotation_turn_exempt(snapshot, state):
        metadata = dict(snapshot.metadata or {})
        raw_contributions = dict(metadata.get("raw_contributions") or {})
        raw_contributions["middle_sr_anchor_guard_v1"] = {
            "suppressed": False,
            "exempted": True,
            "exemption_reason": "edge_rotation_turn_context",
            "side": side,
            "box_zone": str(zones.box_zone or ""),
            "bb20_zone": str(zones.bb20_zone or ""),
            "sr_zone": str(zones.sr_zone or ""),
            "x_sr": float(position.x_sr),
            "threshold": _MIDDLE_ENTRY_SR_ANCHOR_THRESHOLD,
        }
        metadata["raw_contributions"] = raw_contributions
        metadata["middle_sr_anchor_guard_v1"] = dict(raw_contributions["middle_sr_anchor_guard_v1"])
        return ObserveConfirmSnapshot(
            state=snapshot.state,
            action=snapshot.action,
            side=snapshot.side,
            confidence=float(snapshot.confidence),
            reason=snapshot.reason,
            archetype_id=snapshot.archetype_id,
            invalidation_id=snapshot.invalidation_id,
            management_profile_id=snapshot.management_profile_id,
            metadata=metadata,
        )
    metadata = dict(snapshot.metadata or {})
    raw_contributions = dict(metadata.get("raw_contributions") or {})
    raw_contributions["middle_sr_anchor_guard_v1"] = {
        "suppressed": True,
        "side": side,
        "box_zone": str(zones.box_zone or ""),
        "bb20_zone": str(zones.bb20_zone or ""),
        "bb44_zone": str(zones.bb44_zone or ""),
        "sr_zone": str(zones.sr_zone or ""),
        "x_sr": float(position.x_sr),
        "threshold": _MIDDLE_ENTRY_SR_ANCHOR_THRESHOLD,
    }
    metadata["raw_contributions"] = raw_contributions
    metadata["blocked_reason"] = f"middle_{side.lower()}_requires_sr_anchor"
    metadata["blocked_guard"] = "middle_sr_anchor_guard"
    metadata["middle_sr_anchor_guard_v1"] = dict(raw_contributions["middle_sr_anchor_guard_v1"])
    return ObserveConfirmSnapshot(
        state="OBSERVE",
        action="WAIT",
        side="",
        confidence=min(float(snapshot.confidence), 0.35),
        reason="middle_sr_anchor_required_observe",
        archetype_id="",
        invalidation_id="",
        management_profile_id="",
        metadata=metadata,
    )


def _apply_outer_band_reversal_suppression(
    snapshot: ObserveConfirmSnapshot,
    *,
    position: PositionVector,
    response: ResponseVector,
    position_snapshot: PositionSnapshot,
) -> ObserveConfirmSnapshot:
    if _snapshot_guard_exempt(snapshot, "outer_band_reversal_guard"):
        return snapshot
    snapshot_meta = dict(snapshot.metadata or {})
    if bool(snapshot_meta.get("xau_second_support_probe_relief", False)):
        return snapshot
    if bool(snapshot_meta.get("btc_lower_structural_probe_relief", False)):
        return snapshot
    side = _directional_side(snapshot)
    archetype_id = str(snapshot.archetype_id or "").lower()
    if (side, archetype_id) not in {("BUY", ARCHETYPE_LOWER_HOLD_BUY), ("SELL", ARCHETYPE_UPPER_REJECT_SELL)}:
        return snapshot
    if _has_outer_band_reversal_support(position, response, position_snapshot, side=side):
        return snapshot
    metadata = dict(snapshot.metadata or {})
    raw_contributions = dict(metadata.get("raw_contributions") or {})
    raw_contributions["outer_band_reversal_guard_v1"] = {
        "suppressed": True,
        "side": side,
        "archetype_id": archetype_id,
        "bb44_zone": str(position_snapshot.zones.bb44_zone or ""),
        "x_bb44": float(position.x_bb44),
        "sr_zone": str(position_snapshot.zones.sr_zone or ""),
        "x_sr": float(position.x_sr),
        "bb44_threshold": _REVERSAL_BB44_SUPPORT_THRESHOLD,
    }
    metadata["raw_contributions"] = raw_contributions
    metadata["blocked_reason"] = f"outer_band_{side.lower()}_reversal_support_required"
    metadata["blocked_guard"] = "outer_band_guard"
    metadata["outer_band_reversal_guard_v1"] = dict(raw_contributions["outer_band_reversal_guard_v1"])
    return ObserveConfirmSnapshot(
        state="OBSERVE",
        action="WAIT",
        side="",
        confidence=min(float(snapshot.confidence), 0.35),
        reason="outer_band_reversal_support_required_observe",
        archetype_id="",
        invalidation_id="",
        management_profile_id="",
        metadata=metadata,
    )


def _build_semantic_readiness_bridge(
    position: PositionVector,
    response: ResponseVector,
    state: StateInput,
    position_snapshot: PositionSnapshot,
    *,
    evidence_vector_v1: EvidenceVector | None,
    belief_state_v1: BeliefState | None,
    barrier_state_v1: BarrierState | None,
    transition_forecast_v1: TransitionForecast | None,
    trade_management_forecast_v1: TradeManagementForecast | None,
    forecast_gap_metrics_v1: dict[str, float] | None,
) -> SimpleNamespace:
    interpretation = position_snapshot.interpretation
    position_energy = position_snapshot.energy
    state_source = _state_source_fields(state)
    market_mode = str(state_source["market_mode"])
    direction_policy = str(state_source["direction_policy"])
    s_noise = float(state_source["s_noise"])
    s_conflict = float(state_source["s_conflict"])
    s_alignment = float(state_source["s_alignment"])
    s_disparity = float(state_source["s_disparity"])
    s_volatility = float(state_source["s_volatility"])
    energy_middle_context = (
        abs(float(position.x_box)) <= _READINESS_MIDDLE_BOX_LIMIT
        and abs(float(position.x_bb20)) <= _READINESS_MIDDLE_BB20_LIMIT
        and abs(float(position.x_bb44)) <= _READINESS_MIDDLE_BB44_LIMIT
    )
    position_conflict_kind = str(interpretation.conflict_kind or "")
    upper_conflict_context = position_conflict_kind in {
        "CONFLICT_BOX_UPPER_BB20_LOWER",
        "CONFLICT_BB20_UPPER_BB44_LOWER",
    }
    lower_conflict_context = position_conflict_kind in {
        "CONFLICT_BOX_LOWER_BB20_UPPER",
        "CONFLICT_BB20_LOWER_BB44_UPPER",
    }
    position_upper_pressure = (
        max(float(position.x_box), 0.0) * _READINESS_POSITION_WEIGHTS["box"]
        + max(float(position.x_bb20), 0.0) * _READINESS_POSITION_WEIGHTS["bb20"]
        + max(float(position.x_bb44), 0.0) * _READINESS_POSITION_WEIGHTS["bb44"]
        + max(float(position.x_sr), 0.0) * _READINESS_POSITION_WEIGHTS["sr"]
        + max(float(position.x_trendline), 0.0) * _READINESS_POSITION_WEIGHTS["trendline"]
    )
    position_lower_pressure = (
        max(-float(position.x_box), 0.0) * _READINESS_POSITION_WEIGHTS["box"]
        + max(-float(position.x_bb20), 0.0) * _READINESS_POSITION_WEIGHTS["bb20"]
        + max(-float(position.x_bb44), 0.0) * _READINESS_POSITION_WEIGHTS["bb44"]
        + max(-float(position.x_sr), 0.0) * _READINESS_POSITION_WEIGHTS["sr"]
        + max(-float(position.x_trendline), 0.0) * _READINESS_POSITION_WEIGHTS["trendline"]
    )
    buy_position_force = position_lower_pressure
    sell_position_force = position_upper_pressure
    buy_response_force = (
        float(response.r_bb20_lower_hold) * 0.30
        + float(response.r_bb20_mid_hold) * 0.10
        + float(response.r_bb20_mid_reclaim) * 0.15
        + float(response.r_bb20_upper_break) * 0.10
        + float(response.r_bb44_lower_hold) * 0.10
        + float(response.r_box_lower_bounce) * 0.20
        + float(response.r_box_mid_hold) * 0.08
        + float(response.r_box_upper_break) * 0.05
        + float(response.r_candle_lower_reject) * 0.10
    )
    sell_response_force = (
        float(response.r_bb20_lower_break) * 0.18
        + float(response.r_bb20_mid_reject) * 0.10
        + float(response.r_bb20_mid_lose) * 0.15
        + float(response.r_bb20_upper_reject) * 0.20
        + float(response.r_bb44_upper_reject) * 0.10
        + float(response.r_box_lower_break) * 0.15
        + float(response.r_box_mid_reject) * 0.08
        + float(response.r_box_upper_reject) * 0.12
        + float(response.r_candle_upper_reject) * 0.10
    )
    state_damping = _clamp((1.0 - 0.45 * s_noise) * (1.0 - 0.55 * s_conflict), 0.15, 1.0)
    if market_mode == "RANGE":
        regime_multiplier = 1.00
    elif market_mode == "TREND":
        regime_multiplier = 0.90
    elif market_mode == "SHOCK":
        regime_multiplier = 0.55
    else:
        regime_multiplier = 0.85
    alignment_boost = 1.0 + 0.08 * s_alignment
    disparity_boost = 1.0 + 0.05 * s_disparity
    volatility_boost = 1.0 + 0.04 * s_volatility
    direction_buy = 1.0
    direction_sell = 1.0
    if direction_policy == "BUY_ONLY":
        direction_sell = 0.65
    elif direction_policy == "SELL_ONLY":
        direction_buy = 0.65
    buy_response_scale = 1.0
    sell_position_scale = 1.0
    sell_response_scale = 1.0
    buy_position_scale = 1.0
    trend_pullback_buy_boost = (
        market_mode == "TREND"
        and direction_policy == "BUY_ONLY"
        and energy_middle_context
        and not upper_conflict_context
        and float(position.x_box) <= 0.36
        and float(position.x_bb20) <= 0.36
        and (
            float(response.r_bb20_mid_hold) > 0.0
            or float(response.r_bb20_mid_reclaim) > 0.0
            or float(response.r_box_mid_hold) > 0.0
            or float(response.r_candle_lower_reject) > 0.0
        )
    )
    trend_pullback_sell_boost = (
        market_mode == "TREND"
        and direction_policy == "SELL_ONLY"
        and energy_middle_context
        and not lower_conflict_context
        and float(position.x_box) >= -0.36
        and float(position.x_bb20) >= -0.36
        and (
            float(response.r_bb20_mid_reject) > 0.0
            or float(response.r_bb20_mid_lose) > 0.0
            or float(response.r_box_mid_reject) > 0.0
            or float(response.r_candle_upper_reject) > 0.0
        )
    )
    if trend_pullback_buy_boost:
        buy_response_scale *= 1.70
        buy_position_scale *= 1.20
        sell_position_scale *= 0.72
        sell_response_scale *= 0.85
    elif trend_pullback_sell_boost:
        sell_response_scale *= 1.70
        sell_position_scale *= 1.20
        buy_position_scale *= 0.72
        buy_response_scale *= 0.85
    base_buy_support = (
        ((buy_position_force * buy_position_scale) + (buy_response_force * buy_response_scale))
        * state_damping
        * regime_multiplier
        * alignment_boost
        * disparity_boost
        * volatility_boost
        * direction_buy
    )
    base_sell_support = (
        ((sell_position_force * sell_position_scale) + (sell_response_force * sell_response_scale))
        * state_damping
        * regime_multiplier
        * alignment_boost
        * disparity_boost
        * volatility_boost
        * direction_sell
    )

    evidence_buy_boost = 0.0
    evidence_sell_boost = 0.0
    if evidence_vector_v1 is not None:
        evidence_buy_boost = (
            float(evidence_vector_v1.buy_total_evidence) * 0.18
            + float(evidence_vector_v1.buy_reversal_evidence) * 0.08
            + float(evidence_vector_v1.buy_continuation_evidence) * 0.05
        )
        evidence_sell_boost = (
            float(evidence_vector_v1.sell_total_evidence) * 0.18
            + float(evidence_vector_v1.sell_reversal_evidence) * 0.08
            + float(evidence_vector_v1.sell_continuation_evidence) * 0.05
        )

    belief_buy_boost = 0.0
    belief_sell_boost = 0.0
    if belief_state_v1 is not None:
        belief_buy_boost = (
            float(belief_state_v1.buy_belief) * 0.10
            + float(belief_state_v1.buy_persistence) * 0.06
            + max(float(belief_state_v1.belief_spread), 0.0) * 0.04
        )
        belief_sell_boost = (
            float(belief_state_v1.sell_belief) * 0.10
            + float(belief_state_v1.sell_persistence) * 0.06
            + max(-float(belief_state_v1.belief_spread), 0.0) * 0.04
        )

    forecast_assist = _build_forecast_assist(
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )
    buy_forecast_boost = float(forecast_assist.get("buy_boost", 0.0) or 0.0)
    sell_forecast_boost = float(forecast_assist.get("sell_boost", 0.0) or 0.0)
    if trade_management_forecast_v1 is not None:
        buy_forecast_boost += max(
            float(trade_management_forecast_v1.p_continue_favor),
            float(trade_management_forecast_v1.p_recover_after_pullback),
        ) * 0.02
        sell_forecast_boost += max(
            float(trade_management_forecast_v1.p_continue_favor),
            float(trade_management_forecast_v1.p_opposite_edge_reach),
        ) * 0.01

    barrier_buy_penalty = 0.0
    barrier_sell_penalty = 0.0
    if barrier_state_v1 is not None:
        barrier_buy_penalty = min(
            0.12,
            max(
                float(barrier_state_v1.buy_barrier),
                float(barrier_state_v1.conflict_barrier) * 0.5,
                float(barrier_state_v1.direction_policy_barrier) * 0.5,
                float(barrier_state_v1.liquidity_barrier) * 0.5,
            )
            * 0.12,
        )
        barrier_sell_penalty = min(
            0.12,
            max(
                float(barrier_state_v1.sell_barrier),
                float(barrier_state_v1.conflict_barrier) * 0.5,
                float(barrier_state_v1.direction_policy_barrier) * 0.5,
                float(barrier_state_v1.liquidity_barrier) * 0.5,
            )
            * 0.12,
        )

    state_execution = _state_execution_scales(state)
    buy_support = max(
        0.0,
        float(
            (base_buy_support + evidence_buy_boost + belief_buy_boost + buy_forecast_boost - barrier_buy_penalty)
            * float(state_execution["buy_scale"])
        ),
    )
    sell_support = max(
        0.0,
        float(
            (base_sell_support + evidence_sell_boost + belief_sell_boost + sell_forecast_boost - barrier_sell_penalty)
            * float(state_execution["sell_scale"])
        ),
    )
    return SimpleNamespace(
        buy_support=float(buy_support),
        sell_support=float(sell_support),
        support_gap=float(buy_support - sell_support),
        conflict_confidence=float(position_energy.position_conflict_score),
        secondary_lower_context_support=float((position_energy.metadata or {}).get("secondary_lower_force") or 0.0),
        secondary_upper_context_support=float((position_energy.metadata or {}).get("secondary_upper_force") or 0.0),
        metadata={
            "contract_version": "observe_confirm_semantic_readiness_bridge_v1",
            "source": "position_response_state_plus_semantic_bundle",
            "legacy_energy_snapshot_dependency": False,
            "base": {
                "buy_support": float(base_buy_support),
                "sell_support": float(base_sell_support),
                "state_damping": float(state_damping),
                "regime_multiplier": float(regime_multiplier),
                "trend_pullback_buy_boost": bool(trend_pullback_buy_boost),
                "trend_pullback_sell_boost": bool(trend_pullback_sell_boost),
            },
            "components": {
                "state_source": {
                    "input_mode": str(state_source["state_input_mode"]),
                    "state_contract": str(state_source["state_contract"]),
                    "state_mapper_version": str(state_source["state_mapper_version"]),
                    "market_mode": market_mode,
                    "direction_policy": direction_policy,
                },
                "evidence": {
                    "buy_boost": float(evidence_buy_boost),
                    "sell_boost": float(evidence_sell_boost),
                    "present": evidence_vector_v1 is not None,
                },
                "belief": {
                    "buy_boost": float(belief_buy_boost),
                    "sell_boost": float(belief_sell_boost),
                    "present": belief_state_v1 is not None,
                },
                "barrier": {
                    "buy_penalty": float(barrier_buy_penalty),
                    "sell_penalty": float(barrier_sell_penalty),
                    "present": barrier_state_v1 is not None,
                },
                "forecast": {
                    "buy_boost": float(buy_forecast_boost),
                    "sell_boost": float(sell_forecast_boost),
                    "present": transition_forecast_v1 is not None or trade_management_forecast_v1 is not None,
                    "assist": dict(forecast_assist),
                },
                "state_execution": dict(state_execution),
            },
            "final": {
                "buy_support": float(buy_support),
                "sell_support": float(sell_support),
                "support_gap": float(buy_support - sell_support),
            },
        },
    )


def _attach_routing_policy_metadata(
    snapshot: ObserveConfirmSnapshot,
    *,
    evidence_vector_v1: EvidenceVector | None,
    belief_state_v1: BeliefState | None,
    barrier_state_v1: BarrierState | None,
    transition_forecast_v1: TransitionForecast | None,
    trade_management_forecast_v1: TradeManagementForecast | None,
    forecast_gap_metrics_v1: dict[str, float] | None,
) -> ObserveConfirmSnapshot:
    metadata = dict(snapshot.metadata or {})
    metadata["routing_policy_contract_v2"] = "observe_confirm_routing_policy_v2"
    metadata["routing_policy_v2"] = {
        "position_response_role": "archetype_candidate_generation",
        "state_role": "regime_filter",
        "evidence_role": "setup_strength",
        "belief_role": "persistence_bias",
        "barrier_role": "action_suppression",
        "forecast_role": "confidence_modulation_and_confirm_wait_split_only",
        "identity_source_layers": ["position_snapshot_v2", "response_vector_v2"],
        "non_identity_layers": [
            "state_vector_v2",
            "evidence_vector_v1",
            "belief_state_v1",
            "barrier_state_v1",
            "transition_forecast_v1",
            "trade_management_forecast_v1",
            "forecast_gap_metrics_v1",
        ],
        "forecast_policy": {
            "identity_override_allowed": False,
            "side_override_allowed": False,
            "allowed_influence_fields": ["confidence", "action", "metadata.blocked_reason"],
        },
        "available_inputs": {
            "evidence_vector_v1": evidence_vector_v1 is not None,
            "belief_state_v1": belief_state_v1 is not None,
            "barrier_state_v1": barrier_state_v1 is not None,
            "transition_forecast_v1": transition_forecast_v1 is not None,
            "trade_management_forecast_v1": trade_management_forecast_v1 is not None,
            "forecast_gap_metrics_v1": bool(forecast_gap_metrics_v1),
        },
        "implementation_bridge": {
            "semantic_readiness_bridge_v1": "internal_readiness_from_semantic_bundle",
            "legacy_energy_snapshot_dependency": False,
        },
    }
    metadata["confidence_semantics_contract_v2"] = "observe_confirm_confidence_semantics_v2"
    metadata["confidence_semantics_v2"] = {
        "meaning": "execution_readiness_score",
        "identity_separate": True,
        "wait_preserves_archetype_identity": True,
        "action_at_emit_time": str(snapshot.action or ""),
        "archetype_id_at_emit_time": str(snapshot.archetype_id or ""),
    }
    metadata["forecast_assist_v1"] = dict(
        metadata.get("forecast_assist_v1")
        or _build_forecast_assist(
            transition_forecast_v1=transition_forecast_v1,
            trade_management_forecast_v1=trade_management_forecast_v1,
            forecast_gap_metrics_v1=forecast_gap_metrics_v1,
            side=_directional_side(snapshot),
        )
    )
    snapshot.metadata = metadata
    return snapshot


def _directional_side(snapshot: ObserveConfirmSnapshot) -> str:
    side = str(snapshot.side or "").upper()
    if side in {"BUY", "SELL"}:
        return side
    action = str(snapshot.action or "").upper()
    if action in {"BUY", "SELL"}:
        return action
    return ""


def _blocked_guard_from_reason(reason: str) -> str:
    reason_s = str(reason or "").strip().lower()
    if not reason_s:
        return ""
    if reason_s.startswith("outer_band_") and reason_s.endswith("_reversal_support_required"):
        return "outer_band_guard"
    if reason_s.startswith("middle_") and reason_s.endswith("_requires_sr_anchor"):
        return "middle_sr_anchor_guard"
    if reason_s.endswith("_barrier_suppressed_confirm"):
        return "barrier_guard"
    if reason_s.endswith("_forecast_suppressed_confirm"):
        return "forecast_guard"
    return ""


def _demote_confirm_to_observe(
    snapshot: ObserveConfirmSnapshot,
    *,
    blocked_reason: str,
    confidence: float,
    effective_updates: dict[str, object] | None = None,
) -> ObserveConfirmSnapshot:
    side = _directional_side(snapshot)
    metadata = dict(snapshot.metadata or {})
    effective = dict(metadata.get("effective_contributions") or {})
    if effective_updates:
        effective.update(effective_updates)
    metadata["effective_contributions"] = effective
    metadata["blocked_reason"] = str(blocked_reason or "")
    blocked_guard = _blocked_guard_from_reason(blocked_reason)
    if blocked_guard:
        metadata["blocked_guard"] = blocked_guard
    return ObserveConfirmSnapshot(
        state="OBSERVE",
        action="WAIT",
        side=side,
        confidence=max(0.0, min(0.99, float(confidence))),
        reason=str(snapshot.reason or ""),
        archetype_id=str(snapshot.archetype_id or ""),
        invalidation_id=str(snapshot.invalidation_id or ""),
        management_profile_id=str(snapshot.management_profile_id or ""),
        metadata=metadata,
    )


def _apply_barrier_suppression(
    snapshot: ObserveConfirmSnapshot,
    *,
    barrier_state_v1: BarrierState | None,
) -> ObserveConfirmSnapshot:
    if barrier_state_v1 is None or str(snapshot.action or "").upper() not in {"BUY", "SELL"}:
        return snapshot
    side = _directional_side(snapshot)
    if side == "BUY":
        side_barrier = float(barrier_state_v1.buy_barrier)
    elif side == "SELL":
        side_barrier = float(barrier_state_v1.sell_barrier)
    else:
        return snapshot
    total_barrier = max(
        side_barrier,
        float(barrier_state_v1.conflict_barrier),
        float(barrier_state_v1.middle_chop_barrier),
        float(barrier_state_v1.direction_policy_barrier),
        float(barrier_state_v1.liquidity_barrier),
    )
    if total_barrier < 0.85:
        return snapshot
    return _demote_confirm_to_observe(
        snapshot,
        blocked_reason=f"{side.lower()}_barrier_suppressed_confirm",
        confidence=min(float(snapshot.confidence), max(0.01, 1.0 - total_barrier)),
        effective_updates={
            "barrier_state_v1": {
                "side": side,
                "side_barrier": side_barrier,
                "total_barrier": total_barrier,
                "suppressed_confirm": True,
            }
        },
    )


def _apply_forecast_modulation(
    snapshot: ObserveConfirmSnapshot,
    *,
    transition_forecast_v1: TransitionForecast | None,
    trade_management_forecast_v1: TradeManagementForecast | None,
    forecast_gap_metrics_v1: dict[str, float] | None,
) -> ObserveConfirmSnapshot:
    if transition_forecast_v1 is None and trade_management_forecast_v1 is None and not forecast_gap_metrics_v1:
        return snapshot
    side = _directional_side(snapshot)
    forecast_assist = _build_forecast_assist(
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
        side=side,
    )
    metadata = dict(snapshot.metadata or {})
    metadata["forecast_assist_v1"] = dict(forecast_assist)
    if str(snapshot.action or "").upper() not in {"BUY", "SELL"} or side not in {"BUY", "SELL"} or transition_forecast_v1 is None:
        snapshot.metadata = metadata
        return snapshot
    if side == "BUY":
        confirm_score = float(transition_forecast_v1.p_buy_confirm)
    else:
        confirm_score = float(transition_forecast_v1.p_sell_confirm)
    false_break_score = float(transition_forecast_v1.p_false_break)
    fail_now_score = float((trade_management_forecast_v1 or TradeManagementForecast()).p_fail_now)
    side_separation = float(forecast_assist.get("transition_side_separation", 0.0) or 0.0)
    wait_confirm_gap = float(forecast_assist.get("wait_confirm_gap", 0.0) or 0.0)
    continue_fail_gap = float(forecast_assist.get("continue_fail_gap", 0.0) or 0.0)
    decision_hint = str(forecast_assist.get("decision_hint", "") or "")
    edge_pair_law = dict(metadata.get("edge_pair_law_v1") or {})
    upper_reject_reason = str(snapshot.reason or "")
    upper_reject_context = str(edge_pair_law.get("context_label", "") or "").upper()
    upper_reject_box_zone = str(metadata.get("box_zone", "") or "").upper()
    upper_reject_bb20_zone = str(metadata.get("bb20_zone", "") or "").upper()
    upper_reject_context_supported = bool(
        upper_reject_context == "UPPER_EDGE"
        or upper_reject_box_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
        or upper_reject_bb20_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
    )
    upper_break_fail_relief = bool(
        upper_reject_reason == "upper_break_fail_confirm"
        and upper_reject_context_supported
        and confirm_score >= 0.16
        and fail_now_score <= 0.35
        and wait_confirm_gap >= -0.24
        and continue_fail_gap >= -0.30
    )
    upper_reject_forecast_relief = bool(
        side == "SELL"
        and str(snapshot.archetype_id or "") == ARCHETYPE_UPPER_REJECT_SELL
        and (
            (
                upper_reject_reason.startswith("upper_reject")
                and upper_reject_context_supported
                and confirm_score >= 0.14
                and fail_now_score <= 0.40
                and wait_confirm_gap >= -0.18
                and continue_fail_gap >= -0.30
            )
            or upper_break_fail_relief
        )
    )

    if decision_hint == "CONFIRM_FAVOR":
        return ObserveConfirmSnapshot(
            state=snapshot.state,
            action=snapshot.action,
            side=snapshot.side,
            confidence=min(
                0.99,
                float(snapshot.confidence) + min(0.04, float(forecast_assist.get("confirm_bias", 0.0) or 0.0) * 0.05),
            ),
            reason=snapshot.reason,
            archetype_id=snapshot.archetype_id,
            invalidation_id=snapshot.invalidation_id,
            management_profile_id=snapshot.management_profile_id,
            metadata=metadata,
        )
    if upper_reject_forecast_relief:
        metadata["forecast_upper_reject_relief_v1"] = {
            "applied": True,
            "reason": upper_reject_reason,
            "context_label": upper_reject_context,
            "box_zone": upper_reject_box_zone,
            "bb20_zone": upper_reject_bb20_zone,
            "confirm_score": float(confirm_score),
            "fail_now_score": float(fail_now_score),
            "wait_confirm_gap": float(wait_confirm_gap),
            "continue_fail_gap": float(continue_fail_gap),
        }
        return ObserveConfirmSnapshot(
            state=snapshot.state,
            action=snapshot.action,
            side=snapshot.side,
            confidence=float(snapshot.confidence),
            reason=snapshot.reason,
            archetype_id=snapshot.archetype_id,
            invalidation_id=snapshot.invalidation_id,
            management_profile_id=snapshot.management_profile_id,
            metadata=metadata,
        )
    if (
        confirm_score > 0.08
        or false_break_score < 0.80
        or fail_now_score < 0.65
        or side_separation > 0.10
    ) and not (wait_confirm_gap < 0.03 or continue_fail_gap < 0.03):
        return ObserveConfirmSnapshot(
            state=snapshot.state,
            action=snapshot.action,
            side=snapshot.side,
            confidence=float(snapshot.confidence),
            reason=snapshot.reason,
            archetype_id=snapshot.archetype_id,
            invalidation_id=snapshot.invalidation_id,
            management_profile_id=snapshot.management_profile_id,
            metadata=metadata,
        )
    return _demote_confirm_to_observe(
        ObserveConfirmSnapshot(
            state=snapshot.state,
            action=snapshot.action,
            side=snapshot.side,
            confidence=float(snapshot.confidence),
            reason=snapshot.reason,
            archetype_id=snapshot.archetype_id,
            invalidation_id=snapshot.invalidation_id,
            management_profile_id=snapshot.management_profile_id,
            metadata=metadata,
        ),
        blocked_reason=f"{side.lower()}_forecast_suppressed_confirm",
        confidence=min(float(snapshot.confidence), max(0.01, confirm_score + 0.02)),
        effective_updates={
            "forecast_v1": {
                "side": side,
                "confirm_score": confirm_score,
                "false_break_score": false_break_score,
                "fail_now_score": fail_now_score,
                "transition_side_separation": side_separation,
                "wait_confirm_gap": wait_confirm_gap,
                "continue_fail_gap": continue_fail_gap,
                "decision_hint": decision_hint,
                "suppressed_confirm": True,
            }
        },
    )


def _snapshot(
    *,
    state: str,
    action: str,
    side: str,
    confidence: float,
    reason: str,
    archetype_id: str = "",
    invalidation_id: str = "",
    management_profile_id: str = "",
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    return ObserveConfirmSnapshot(
        state=state,
        action=action,
        side=side,
        confidence=confidence,
        reason=reason,
        archetype_id=archetype_id,
        invalidation_id=invalidation_id or _default_invalidation_id(archetype_id),
        management_profile_id=management_profile_id or _default_management_profile_id(archetype_id),
        metadata=metadata or {},
    )


def _confirm(
    *,
    action: str,
    side: str,
    confidence: float,
    reason: str,
    archetype_id: str,
    invalidation_id: str = "",
    management_profile_id: str = "",
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    return _snapshot(
        state="CONFIRM",
        action=action,
        side=side,
        confidence=confidence,
        reason=reason,
        archetype_id=archetype_id,
        invalidation_id=invalidation_id,
        management_profile_id=management_profile_id,
        metadata=metadata,
    )


def _observe(
    *,
    action: str,
    side: str,
    confidence: float,
    reason: str,
    archetype_id: str = "",
    invalidation_id: str = "",
    management_profile_id: str = "",
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    return _snapshot(
        state="OBSERVE",
        action=action,
        side=side,
        confidence=confidence,
        reason=reason,
        archetype_id=archetype_id,
        invalidation_id=invalidation_id,
        management_profile_id=management_profile_id,
        metadata=metadata,
    )


def _conflict_observe(
    *,
    action: str,
    side: str,
    confidence: float,
    reason: str,
    archetype_id: str,
    invalidation_id: str = "",
    management_profile_id: str = "",
    metadata: dict | None = None,
) -> ObserveConfirmSnapshot:
    return _snapshot(
        state="CONFLICT_OBSERVE",
        action=action,
        side=side,
        confidence=confidence,
        reason=reason,
        archetype_id=archetype_id,
        invalidation_id=invalidation_id,
        management_profile_id=management_profile_id,
        metadata=metadata,
    )


def _route_observe_confirm_base(
    position: PositionVector,
    response: ResponseVector,
    state: StateInput,
    position_snapshot: PositionSnapshot,
    *,
    evidence_vector_v1: EvidenceVector | None,
    belief_state_v1: BeliefState | None,
    barrier_state_v1: BarrierState | None,
    transition_forecast_v1: TransitionForecast | None,
    trade_management_forecast_v1: TradeManagementForecast | None,
    forecast_gap_metrics_v1: dict[str, float] | None,
) -> ObserveConfirmSnapshot:
    symbol = _symbol(position, state)
    state_source = _state_source_fields(state)
    market_mode = str(state_source["market_mode"])
    direction_policy = str(state_source["direction_policy"])
    semantic_readiness = _build_semantic_readiness_bridge(
        position,
        response,
        state,
        position_snapshot,
        evidence_vector_v1=evidence_vector_v1,
        belief_state_v1=belief_state_v1,
        barrier_state_v1=barrier_state_v1,
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )
    buy_support = float(semantic_readiness.buy_support)
    sell_support = float(semantic_readiness.sell_support)
    support_gap = float(semantic_readiness.support_gap)
    x_box = float(position.x_box)
    x_bb20 = float(position.x_bb20)
    x_bb44 = float(position.x_bb44)
    x_sr = float(position.x_sr)
    raw_box_state = str((position.metadata or {}).get("box_state", "UNKNOWN") or "UNKNOWN").upper()
    raw_bb_state = str((position.metadata or {}).get("bb_state", "UNKNOWN") or "UNKNOWN").upper()
    zones = position_snapshot.zones
    interpretation = position_snapshot.interpretation
    coord_box_zone = zones.box_zone
    coord_bb20_zone = zones.bb20_zone
    coord_bb44_zone = zones.bb44_zone
    box_state = zones.box_zone
    bb_state = zones.bb20_zone
    bb44_state = zones.bb44_zone
    used_raw_fallback = dict(zones.metadata.get("used_raw_fallback", {}))
    box_label_fallback = bool(used_raw_fallback.get("x_box", False))
    bb20_label_fallback = bool(used_raw_fallback.get("x_bb20", False))
    lower_edge_active = bb_state in {"BELOW", "LOWER_EDGE"} or box_state in {"BELOW", "LOWER_EDGE", "LOWER"}
    upper_edge_active = bb_state in {"ABOVE", "UPPER_EDGE"} or box_state in {"ABOVE", "UPPER_EDGE", "UPPER"}
    lower_context_ok = _lower_context_ok(box_state)
    upper_context_ok = _upper_context_ok(box_state)
    primary_lower_depth = _max_abs(min(x_box, 0.0), min(x_bb20, 0.0))
    primary_upper_depth = _max_abs(max(x_box, 0.0), max(x_bb20, 0.0))
    lower_support_depth = abs(min(x_bb44, 0.0)) if (box_state in {"BELOW", "LOWER_EDGE", "LOWER", "MIDDLE"} or bb_state in {"BELOW", "LOWER_EDGE", "LOWER"} or lower_edge_active) else 0.0
    upper_support_depth = abs(max(x_bb44, 0.0)) if (box_state in {"MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE"} or bb_state in {"UPPER", "UPPER_EDGE", "ABOVE"} or upper_edge_active) else 0.0
    lower_depth = max(primary_lower_depth, lower_support_depth)
    upper_depth = max(primary_upper_depth, upper_support_depth)
    conflict_kind = str(interpretation.conflict_kind or "")
    upper_lower_conflict = interpretation.conflict_kind == "CONFLICT_BOX_UPPER_BB20_LOWER"
    lower_upper_conflict = interpretation.conflict_kind == "CONFLICT_BOX_LOWER_BB20_UPPER"
    middle_zone = box_state == "MIDDLE" and bb_state == "MIDDLE" and bb44_state == "MIDDLE"
    trend_pullback_zone = abs(x_box) < 0.42 and abs(x_bb20) < 0.42 and abs(x_bb44) < 0.48
    mid_buy_support = max(
        float(response.r_bb20_mid_hold),
        float(response.r_bb20_mid_reclaim),
        float(response.r_box_mid_hold),
        float(response.r_candle_lower_reject),
    )
    failed_sell_reclaim_signal = max(
        float(response.r_bb20_mid_hold),
        float(response.r_bb20_mid_reclaim),
        float(response.r_box_mid_hold),
        float(response.r_candle_lower_reject),
    )
    upper_structural_reject_response = max(
        float(response.r_sr_resistance_reject),
        float(response.r_trend_resistance_reject_m15),
        float(response.r_trend_resistance_reject_h1),
        float(response.r_trend_resistance_reject_h4),
    )
    lower_structural_support_response = max(
        float(response.r_sr_support_hold),
        float(response.r_sr_support_reclaim),
        float(response.r_trend_support_hold_m15),
        float(response.r_trend_support_hold_h1),
        float(response.r_trend_support_hold_h4),
    )
    upper_reject_response = max(
        float(response.r_bb20_upper_reject),
        float(response.r_box_upper_reject),
        float(response.r_candle_upper_reject),
        float(response.r_bb20_mid_reject),
        float(response.r_bb20_mid_lose),
        float(response.r_box_mid_reject),
        float(upper_structural_reject_response),
    )
    explicit_lower_break_response = max(
        float(response.r_bb20_lower_break),
        float(response.r_box_lower_break),
    )
    lower_break_response = float(explicit_lower_break_response)
    lower_hold_response = max(
        float(response.r_bb20_lower_hold),
        float(response.r_box_lower_bounce),
        float(response.r_candle_lower_reject),
    )
    mid_reclaim_response = max(
        float(response.r_bb20_mid_hold),
        float(response.r_bb20_mid_reclaim),
        float(response.r_box_mid_hold),
    )
    mid_lose_response = max(
        float(response.r_bb20_mid_reject),
        float(response.r_bb20_mid_lose),
        float(response.r_box_mid_reject),
        float(response.r_candle_upper_reject),
    )
    lower_reclaim_response = max(
        lower_hold_response,
        mid_reclaim_response,
        float(response.r_bb44_lower_hold),
    )
    explicit_upper_break_response = max(
        float(response.r_bb20_upper_break),
        float(response.r_box_upper_break),
    )
    upper_break_response = max(
        explicit_upper_break_response,
        mid_reclaim_response,
    )
    upper_reclaim_dominance = _upper_reclaim_dominates_reject(
        upper_reject_response=upper_reject_response,
        upper_break_response=upper_break_response,
        buy_support=buy_support,
        sell_support=sell_support,
    )
    structural_lower_break_override = (
        float(response.r_box_lower_break) >= 0.95
        and box_state == "BELOW"
        and float(response.r_box_lower_bounce) <= 0.0
        and float(response.r_bb20_mid_hold) <= 0.0
        and float(response.r_bb20_mid_reclaim) <= 0.0
        and float(response.r_box_mid_hold) <= 0.0
        and lower_hold_response < 0.35
        and float(response.r_bb44_lower_hold) < 0.10
    )
    edge_pair_context = _edge_pair_context_label(
        box_state=box_state,
        bb_state=bb_state,
        lower_edge_active=lower_edge_active,
        upper_edge_active=upper_edge_active,
        lower_depth=lower_depth,
        upper_depth=upper_depth,
    )
    edge_pair_law = _build_edge_pair_law(
        context_label=edge_pair_context,
        lower_reclaim_response=lower_reclaim_response,
        lower_break_response=explicit_lower_break_response,
        upper_reject_response=upper_reject_response,
        upper_break_response=explicit_upper_break_response,
        mid_reclaim_response=mid_reclaim_response,
        mid_lose_response=mid_lose_response,
    )
    def _decorate_metadata(metadata: dict | None, *, emit_kind: str) -> dict:
        merged = dict(metadata or {})
        raw_contributions = dict(merged.get("raw_contributions") or {})
        raw_contributions["semantic_readiness_bridge_v1"] = {
            "emit_kind": emit_kind,
            "buy_support": float(buy_support),
            "sell_support": float(sell_support),
            "support_gap": float(support_gap),
        }
        raw_contributions["edge_pair_law_v1"] = {
            "emit_kind": emit_kind,
            "context_label": str(edge_pair_law["context_label"]),
            "pair_gap": float(edge_pair_law["pair_gap"]),
            "winner_side": str(edge_pair_law["winner_side"]),
            "winner_clear": bool(edge_pair_law["winner_clear"]),
        }
        merged["raw_contributions"] = raw_contributions
        merged["semantic_readiness_bridge_v1"] = dict(semantic_readiness.metadata or {})
        merged["edge_pair_law_v1"] = dict(edge_pair_law)
        return merged

    def _emit_confirm(**kwargs) -> ObserveConfirmSnapshot:
        kwargs["metadata"] = _decorate_metadata(kwargs.get("metadata"), emit_kind="confirm")
        return _confirm(**kwargs)

    def _emit_observe(**kwargs) -> ObserveConfirmSnapshot:
        kwargs["metadata"] = _decorate_metadata(kwargs.get("metadata"), emit_kind="observe")
        return _observe(**kwargs)

    def _emit_conflict_observe(**kwargs) -> ObserveConfirmSnapshot:
        kwargs["metadata"] = _decorate_metadata(kwargs.get("metadata"), emit_kind="conflict_observe")
        return _conflict_observe(**kwargs)

    conflict_dominance = str(interpretation.dominance_label or "NONE")
    conflict_dominance_side = _dominance_side_from_label(conflict_dominance)
    conflict_confidence = float(semantic_readiness.conflict_confidence)
    secondary_lower_context_support = float(semantic_readiness.secondary_lower_context_support)
    secondary_upper_context_support = float(semantic_readiness.secondary_upper_context_support)
    primary_label = str(interpretation.primary_label or "")
    secondary_context_label = str(interpretation.secondary_context_label or "")
    _, state_meta = _state_v2_payload(state)
    buy_belief = float(belief_state_v1.buy_belief) if belief_state_v1 is not None else 0.0
    buy_persistence = float(belief_state_v1.buy_persistence) if belief_state_v1 is not None else 0.0
    buy_streak = int(belief_state_v1.buy_streak) if belief_state_v1 is not None else 0
    strong_upper_continuation_context = _strong_continuation_context(primary_label, secondary_context_label, "UPPER")
    strong_lower_continuation_context = _strong_continuation_context(primary_label, secondary_context_label, "LOWER")
    upper_break_continuation_context = _upper_break_continuation_context(
        strong_upper_continuation_context=strong_upper_continuation_context,
        state_meta=state_meta,
    )
    confirmed_upper_reversal = _confirmed_upper_reversal_response(response)
    confirmed_lower_reversal = _confirmed_lower_reversal_response(response)
    middle_anchor_forecast_assist = _build_forecast_assist(
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )

    if upper_lower_conflict:
        if conflict_dominance_side == "BALANCED" or conflict_confidence < 0.10:
            return _emit_conflict_observe(
                action="WAIT",
                side="",
                confidence=min(0.99, max(upper_depth, abs(x_bb20), conflict_confidence)),
                reason="conflict_box_upper_bb20_lower_balanced_observe",
                archetype_id="",
                metadata={
                    "conflict": conflict_kind,
                    "dominance": conflict_dominance,
                    "dominance_side": conflict_dominance_side,
                    "confidence": conflict_confidence,
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        conflict_lower_rebound_signal = max(
            lower_hold_response,
            float(response.r_bb20_lower_hold),
            float(response.r_bb44_lower_hold),
            float(response.r_box_mid_hold),
        )
        if (
            conflict_dominance_side == "LOWER"
            and x_box <= 0.35
            and x_bb20 <= -0.35
            and x_bb44 <= -0.12
            and conflict_lower_rebound_signal > 0.12
            and _confirm_support_met(
                candidate_support=buy_support,
                opposing_support=sell_support,
                floor=min(_confirm_floor(symbol, "LOWER_REBOUND_CONFIRM"), 0.08),
                advantage=0.03,
            )
        ):
            return _emit_confirm(
                action="BUY",
                side="BUY",
                confidence=_support_confidence(buy_support, conflict_lower_rebound_signal),
                reason="conflict_box_upper_bb20_lower_lower_support_confirm",
                archetype_id=ARCHETYPE_LOWER_HOLD_BUY,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": "LOWER_DOMINANT_CONFLICT",
                    "dominance_side": "LOWER",
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        if (
            failed_sell_reclaim_signal > 0.0
            and (x_bb20 <= -0.18 or x_bb44 <= -0.08 or _btc_lower_buy_context_ok(symbol, box_state, x_box))
            and upper_reject_response <= 0.0
            and _confirm_support_met(
                candidate_support=buy_support,
                opposing_support=sell_support,
                floor=_confirm_floor(symbol, "FAILED_SELL_RECLAIM_BUY_CONFIRM"),
                advantage=_confirm_advantage(symbol, "FAILED_SELL_RECLAIM_BUY_CONFIRM"),
            )
        ):
            return _emit_confirm(
                action="BUY",
                side="BUY",
                confidence=_support_confidence(buy_support, failed_sell_reclaim_signal),
                reason="failed_sell_reclaim_buy_confirm",
                archetype_id=ARCHETYPE_MID_RECLAIM_BUY,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": "LOWER_DOMINANT_CONFLICT",
                    "dominance_side": "LOWER",
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        return _emit_conflict_observe(
            action="WAIT",
            side="",
            confidence=min(0.99, max(upper_depth, abs(x_bb20))),
            reason="conflict_box_upper_bb20_lower_upper_dominant_observe" if conflict_dominance_side == "UPPER" else "conflict_box_upper_bb20_lower_lower_dominant_observe",
            archetype_id="",
            metadata={
                "conflict": conflict_kind,
                "dominance": conflict_dominance,
                "dominance_side": conflict_dominance_side,
                "x_box": float(x_box),
                "x_bb20": float(x_bb20),
                "x_bb44": float(x_bb44),
                "coord_box_zone": coord_box_zone,
                "coord_bb20_zone": coord_bb20_zone,
                "coord_bb44_zone": coord_bb44_zone,
                "raw_box_state": raw_box_state,
                "raw_bb_state": raw_bb_state,
                "label_fallback_box_used": bool(box_label_fallback),
                "label_fallback_bb20_used": bool(bb20_label_fallback),
            },
        )

    if lower_upper_conflict:
        upper_sell_policy_ok = direction_policy in {"BOTH", "SELL_ONLY"}
        conflict_upper_probe_temperament = _symbol_probe_temperament(
            symbol,
            context_label="UPPER_EDGE",
            trigger_branch="upper_reject",
            probe_direction="SELL",
        )
        xau_upper_watch_enabled = _symbol_override_flag(
            symbol,
            "router",
            "context",
            "upper_reject_watch",
            default=True,
        )
        xau_local_upper_reject_watch = bool(
            symbol == "XAUUSD"
            and upper_sell_policy_ok
            and xau_upper_watch_enabled
            and x_bb20 >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "upper_reject_watch",
                "bb20_min",
                default=-0.08,
            )
            and upper_reject_response >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "upper_reject_watch",
                "upper_reject_min",
                default=0.06,
            )
            and (
                sell_support >= max(
                    _symbol_override_float(
                        symbol,
                        "router",
                        "context",
                        "upper_reject_watch",
                        "sell_support_floor",
                        default=0.14,
                    ),
                    buy_support
                    + _symbol_override_float(
                        symbol,
                        "router",
                        "context",
                        "upper_reject_watch",
                        "sell_support_buy_margin",
                        default=-0.02,
                    ),
                )
                or float(response.r_sr_resistance_reject)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_watch",
                    "sr_resistance_min",
                    default=0.10,
                )
                or float(response.r_trend_resistance_reject_m15)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_watch",
                    "trend_resistance_m15_min",
                    default=0.08,
                )
                or float(response.r_bb20_mid_lose)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_watch",
                    "bb20_mid_lose_min",
                    default=0.06,
                )
                or float(response.r_box_mid_reject)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_watch",
                    "box_mid_reject_min",
                    default=0.06,
                )
            )
        )
        conflict_upper_reject_present = bool(
            upper_sell_policy_ok
            and (
                upper_context_ok
                or coord_bb20_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
                or raw_bb_state in {"UPPER", "UPPER_EDGE", "ABOVE"}
            )
            and x_bb20 >= 0.0
            and upper_reject_response >= 0.08
            and not upper_reclaim_dominance
        ) or xau_local_upper_reject_watch
        conflict_upper_reject_watch = bool(
            upper_sell_policy_ok
            and (
                conflict_upper_reject_present
                or (
                    (
                        upper_context_ok
                        or coord_bb20_zone in {"UPPER", "UPPER_EDGE", "ABOVE"}
                        or raw_bb_state in {"UPPER", "UPPER_EDGE", "ABOVE"}
                    )
                    and x_bb20 >= 0.30
                    and (
                        upper_reject_response >= 0.025
                        or (
                            sell_support >= 0.18
                            and sell_support >= buy_support - 0.02
                        )
                    )
                )
            )
            or xau_local_upper_reject_watch
        )
        conflict_upper_reject_probe_ready = bool(
            conflict_upper_reject_watch
            and _probe_support_ready(
                candidate_support=max(sell_support, upper_reject_response),
                opposing_support=buy_support,
                floor=min(_confirm_floor(symbol, "UPPER_REJECT_CONFIRM"), 0.10),
                advantage=0.03,
                floor_mult=_probe_temperament_value(
                    conflict_upper_probe_temperament,
                    key="floor_mult",
                    policy_field="default_floor_mult",
                    default=_EDGE_PROBE_FLOOR_MULT,
                ),
                advantage_mult=_probe_temperament_value(
                    conflict_upper_probe_temperament,
                    key="advantage_mult",
                    policy_field="default_advantage_mult",
                    default=_EDGE_PROBE_ADVANTAGE_MULT,
                ),
                tolerance=_probe_temperament_value(
                    conflict_upper_probe_temperament,
                    key="support_tolerance",
                    policy_field="default_support_tolerance",
                    default=_EDGE_PROBE_SUPPORT_TOLERANCE,
                ),
            )
        )
        if conflict_upper_reject_watch:
            edge_pair_law["candidate_sell"] = float(
                max(
                    float(edge_pair_law.get("candidate_sell", 0.0) or 0.0),
                    float(upper_reject_response),
                    float(sell_support),
                )
            )
            edge_pair_law["pair_gap"] = float(
                abs(float(edge_pair_law.get("candidate_buy", 0.0) or 0.0) - float(edge_pair_law["candidate_sell"]))
            )
            edge_pair_law["opposing_branch_side"] = "SELL"
            edge_pair_law["opposing_branch_archetype"] = ARCHETYPE_UPPER_REJECT_SELL
            if float(edge_pair_law["candidate_sell"]) > float(edge_pair_law.get("candidate_buy", 0.0) or 0.0):
                edge_pair_law["winner_side"] = "SELL"
                edge_pair_law["winner_archetype"] = ARCHETYPE_UPPER_REJECT_SELL
            edge_pair_law["winner_clear"] = bool(
                max(
                    float(edge_pair_law.get("candidate_buy", 0.0) or 0.0),
                    float(edge_pair_law["candidate_sell"]),
                )
                >= 0.05
                and float(edge_pair_law["pair_gap"]) >= 0.05
            )
        conflict_upper_probe_metadata = {
            "contract_version": "probe_candidate_v1",
            "active": True,
            "probe_kind": "edge_probe",
            "probe_direction": "SELL",
            "trigger_branch": "upper_reject",
            "candidate_support": float(max(sell_support, upper_reject_response)),
            "opposing_support": float(buy_support),
            "floor": float(min(_confirm_floor(symbol, "UPPER_REJECT_CONFIRM"), 0.10)),
            "advantage": 0.03,
            "near_confirm": bool(conflict_upper_reject_probe_ready),
            "symbol_probe_temperament_v1": dict(conflict_upper_probe_temperament),
        }
        if conflict_dominance_side == "BALANCED" or conflict_confidence < 0.10:
            if conflict_upper_reject_watch:
                return _emit_conflict_observe(
                    action="WAIT",
                    side="SELL",
                    confidence=min(0.99, max(lower_depth, abs(x_bb20), upper_reject_response, conflict_confidence)),
                    reason="upper_reject_probe_observe",
                    archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                    metadata={
                        "conflict": conflict_kind,
                        "dominance": conflict_dominance,
                        "dominance_side": conflict_dominance_side,
                        "confidence": conflict_confidence,
                        "x_box": float(x_box),
                        "x_bb20": float(x_bb20),
                        "x_bb44": float(x_bb44),
                        "coord_box_zone": coord_box_zone,
                        "coord_bb20_zone": coord_bb20_zone,
                        "coord_bb44_zone": coord_bb44_zone,
                        "raw_box_state": raw_box_state,
                        "raw_bb_state": raw_bb_state,
                        "upper_reject_response": float(upper_reject_response),
                        "conflict_upper_reject_watch": True,
                        "conflict_upper_reject_probe_ready": bool(conflict_upper_reject_probe_ready),
                        "probe_candidate_v1": dict(conflict_upper_probe_metadata),
                        "symbol_probe_temperament_v1": dict(conflict_upper_probe_temperament),
                        "routing_guard_exemptions": {
                            "outer_band_reversal_guard": True,
                        },
                        "label_fallback_box_used": bool(box_label_fallback),
                        "label_fallback_bb20_used": bool(bb20_label_fallback),
                    },
                )
            return _emit_conflict_observe(
                action="WAIT",
                side="",
                confidence=min(0.99, max(lower_depth, abs(x_bb20), conflict_confidence)),
                reason="conflict_box_lower_bb20_upper_balanced_observe",
                archetype_id="",
                metadata={
                    "conflict": conflict_kind,
                    "dominance": conflict_dominance,
                    "dominance_side": conflict_dominance_side,
                    "confidence": conflict_confidence,
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        if (
            conflict_dominance_side == "LOWER"
            and lower_reclaim_response > 0.0
            and lower_context_ok
            and not conflict_upper_reject_present
            and _confirm_support_met(
                candidate_support=buy_support,
                opposing_support=sell_support,
                floor=_confirm_floor(symbol, "LOWER_REBOUND_CONFIRM"),
                advantage=_confirm_advantage(symbol, "LOWER_REBOUND_CONFIRM"),
            )
        ):
            return _emit_confirm(
                action="BUY",
                side="BUY",
                confidence=_support_confidence(buy_support, lower_reclaim_response),
                reason="conflict_box_lower_bb20_upper_lower_rebound_confirm",
                archetype_id=ARCHETYPE_LOWER_HOLD_BUY,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": "LOWER_DOMINANT_CONFLICT",
                    "dominance_side": "LOWER",
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        if (
            conflict_dominance_side == "UPPER"
            and upper_reject_response > 0.0
            and conflict_upper_reject_watch
            and _confirm_support_met(
                candidate_support=sell_support,
                opposing_support=buy_support,
                floor=min(_confirm_floor(symbol, "UPPER_REJECT_CONFIRM"), 0.12),
                advantage=max(0.02, _confirm_advantage(symbol, "UPPER_REJECT_CONFIRM")),
            )
        ):
            return _emit_confirm(
                action="SELL",
                side="SELL",
                confidence=_support_confidence(sell_support, upper_reject_response),
                reason="conflict_box_lower_bb20_upper_upper_reject_confirm",
                archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": "UPPER_DOMINANT_CONFLICT",
                    "dominance_side": "UPPER",
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "upper_reject_response": float(upper_reject_response),
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        if conflict_upper_reject_probe_ready:
            return _emit_conflict_observe(
                action="WAIT",
                side="SELL",
                confidence=min(0.99, max(abs(x_bb20), upper_reject_response)),
                reason="upper_reject_probe_observe",
                archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": conflict_dominance,
                    "dominance_side": conflict_dominance_side,
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "upper_reject_response": float(upper_reject_response),
                    "conflict_upper_reject_probe_ready": True,
                    "conflict_upper_reject_watch": True,
                    "probe_candidate_v1": dict(conflict_upper_probe_metadata),
                    "symbol_probe_temperament_v1": dict(conflict_upper_probe_temperament),
                    "routing_guard_exemptions": {
                        "outer_band_reversal_guard": True,
                    },
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        if conflict_upper_reject_watch:
            return _emit_conflict_observe(
                action="WAIT",
                side="SELL",
                confidence=min(0.99, max(abs(x_bb20), upper_reject_response)),
                reason="upper_reject_probe_observe",
                archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                metadata={
                    "conflict": conflict_kind,
                    "dominance": conflict_dominance,
                    "dominance_side": conflict_dominance_side,
                    "x_box": float(x_box),
                    "x_bb20": float(x_bb20),
                    "x_bb44": float(x_bb44),
                    "coord_box_zone": coord_box_zone,
                    "coord_bb20_zone": coord_bb20_zone,
                    "coord_bb44_zone": coord_bb44_zone,
                    "raw_box_state": raw_box_state,
                    "raw_bb_state": raw_bb_state,
                    "upper_reject_response": float(upper_reject_response),
                    "conflict_upper_reject_watch": True,
                    "conflict_upper_reject_probe_ready": False,
                    "probe_candidate_v1": dict(conflict_upper_probe_metadata),
                    "symbol_probe_temperament_v1": dict(conflict_upper_probe_temperament),
                    "routing_guard_exemptions": {
                        "outer_band_reversal_guard": True,
                    },
                    "label_fallback_box_used": bool(box_label_fallback),
                    "label_fallback_bb20_used": bool(bb20_label_fallback),
                },
            )
        return _emit_conflict_observe(
            action="WAIT",
            side="",
            confidence=min(0.99, max(lower_depth, abs(x_bb20))),
            reason="conflict_box_lower_bb20_upper_lower_dominant_observe" if conflict_dominance_side == "LOWER" else "conflict_box_lower_bb20_upper_upper_dominant_observe",
            archetype_id="",
            metadata={
                "conflict": conflict_kind,
                "dominance": conflict_dominance,
                "dominance_side": conflict_dominance_side,
                "x_box": float(x_box),
                "x_bb20": float(x_bb20),
                "x_bb44": float(x_bb44),
                "coord_box_zone": coord_box_zone,
                "coord_bb20_zone": coord_bb20_zone,
                "coord_bb44_zone": coord_bb44_zone,
                "raw_box_state": raw_box_state,
                "raw_bb_state": raw_bb_state,
                "label_fallback_box_used": bool(box_label_fallback),
                "label_fallback_bb20_used": bool(bb20_label_fallback),
            },
        )

    if market_mode == "TREND" and trend_pullback_zone:
        if (
            direction_policy == "BUY_ONLY"
            and x_box <= 0.38
            and x_bb20 <= 0.35
            and (
                response.r_bb20_mid_hold > 0.0
                or
                response.r_bb20_mid_reclaim > 0.0
                or response.r_candle_lower_reject > 0.0
                or response.r_box_lower_bounce > 0.0
                or response.r_box_mid_hold > 0.0
            )
        ):
            trend_buy_support = float(buy_support)
            if interpretation.secondary_context_label == "LOWER_CONTEXT":
                trend_buy_support += min(0.02, secondary_lower_context_support * 0.20)
            return _emit_threshold_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                side="BUY",
                candidate_support=trend_buy_support,
                opposing_support=sell_support,
                floor=_confirm_floor(symbol, "TREND_PULLBACK_BUY_CONFIRM"),
                advantage=_confirm_advantage(symbol, "TREND_PULLBACK_BUY_CONFIRM"),
                confirm_reason="trend_pullback_buy_confirm",
                observe_reason="trend_pullback_buy_observe",
                archetype_id=ARCHETYPE_MID_RECLAIM_BUY,
                confidence_values=(trend_buy_support,),
                metadata={"zone": "middle", "trigger": "trend_pullback_buy", "trend_buy_support": trend_buy_support},
            )
        if (
            direction_policy == "SELL_ONLY"
            and x_box >= -0.38
            and x_bb20 >= -0.35
            and (
                response.r_bb20_mid_reject > 0.0
                or
                response.r_bb20_mid_lose > 0.0
                or response.r_candle_upper_reject > 0.0
                or response.r_box_upper_reject > 0.0
                or response.r_box_mid_reject > 0.0
            )
        ):
            trend_sell_support = float(sell_support)
            if interpretation.secondary_context_label == "UPPER_CONTEXT":
                trend_sell_support += min(0.02, secondary_upper_context_support * 0.20)
            return _emit_threshold_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                side="SELL",
                candidate_support=trend_sell_support,
                opposing_support=buy_support,
                floor=_confirm_floor(symbol, "TREND_PULLBACK_SELL_CONFIRM"),
                advantage=_confirm_advantage(symbol, "TREND_PULLBACK_SELL_CONFIRM"),
                confirm_reason="trend_pullback_sell_confirm",
                observe_reason="trend_pullback_sell_observe",
                archetype_id=ARCHETYPE_MID_LOSE_SELL,
                confidence_values=(trend_sell_support,),
                metadata={"zone": "middle", "trigger": "trend_pullback_sell", "trend_sell_support": trend_sell_support},
            )

    # Midline reclaim/lose can confirm before an explicit edge state.
    if middle_zone:
        if (
            response.r_bb20_mid_reclaim > 0.0
            and x_box <= 0.28
            and x_bb20 <= 0.18
            and (x_bb44 <= -0.02 or float(position.x_sr) <= -0.20)
        ):
            return _emit_threshold_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                side="BUY",
                candidate_support=buy_support,
                opposing_support=sell_support,
                floor=_confirm_floor(symbol, "MID_RECLAIM_CONFIRM"),
                advantage=0.02,
                confirm_reason="mid_reclaim_confirm",
                observe_reason="middle_wait",
                archetype_id=ARCHETYPE_MID_RECLAIM_BUY,
                confidence_values=(buy_support,),
                metadata={"zone": "middle", "trigger": "mid_reclaim"},
            )
        if (
            response.r_bb20_mid_lose > 0.0
            and x_box >= -0.28
            and x_bb20 >= -0.18
            and (x_bb44 >= 0.02 or float(position.x_sr) >= 0.20)
        ):
            return _emit_threshold_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                side="SELL",
                candidate_support=sell_support,
                opposing_support=buy_support,
                floor=_confirm_floor(symbol, "MID_REJECT_CONFIRM"),
                advantage=0.02,
                confirm_reason="mid_reject_confirm",
                observe_reason="middle_wait",
                archetype_id=ARCHETYPE_MID_LOSE_SELL,
                confidence_values=(sell_support,),
                metadata={"zone": "middle", "trigger": "mid_lose"},
            )

    if middle_zone:
        return _emit_observe(
            action="WAIT",
            side="",
            confidence=0.5,
            reason="middle_wait",
            archetype_id="",
            metadata={"zone": "middle"},
        )

    xau_mixed_upper_reject_enabled = _symbol_override_flag(
        symbol,
        "router",
        "context",
        "mixed_upper_reject",
        default=True,
    )
    xau_local_mixed_upper_reject_override = (
        symbol == "XAUUSD"
        and xau_mixed_upper_reject_enabled
        and upper_structural_reject_response
        >= _symbol_override_float(
            symbol,
            "router",
            "context",
            "mixed_upper_reject",
            "structural_reject_min",
            default=_XAU_UPPER_STRUCTURAL_REJECT_MIN,
        )
        and lower_break_response <= 0.0
        and x_bb20
        >= _symbol_override_float(
            symbol,
            "router",
            "context",
            "mixed_upper_reject",
            "bb20_min",
            default=-0.16,
        )
        and (
            bb44_state in {"MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE"}
            or x_bb44
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "bb44_min",
                default=-0.10,
            )
        )
        and not _upper_reclaim_dominates_reject(
            upper_reject_response=upper_reject_response,
            upper_break_response=upper_break_response,
            buy_support=buy_support,
            sell_support=sell_support,
        )
        and (
            float(response.r_sr_resistance_reject)
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "sr_resistance_min",
                default=0.10,
            )
            or float(response.r_trend_resistance_reject_m15)
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "trend_resistance_m15_min",
                default=0.08,
            )
            or float(response.r_bb20_mid_lose)
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "bb20_mid_lose_min",
                default=0.06,
            )
            or float(response.r_box_mid_reject)
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "box_mid_reject_min",
                default=0.06,
            )
            or sell_support
            >= max(
                _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "sell_support_floor",
                    default=0.12,
                ),
                buy_support
                + _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "sell_support_buy_margin",
                    default=-0.02,
                ),
            )
        )
    )
    mixed_upper_reject_override = (
        upper_reject_response >= _MIXED_UPPER_REJECT_MIN_RESPONSE
        and _explicit_upper_reject_signal(response)
        and lower_break_response <= 0.0
        and x_bb20 >= _MIXED_UPPER_REJECT_BB20_MIN
        and (bb44_state in {"MIDDLE", "UPPER", "UPPER_EDGE", "ABOVE"} or x_bb44 >= 0.0)
        and not upper_reclaim_dominance
    ) or xau_local_mixed_upper_reject_override
    if mixed_upper_reject_override:
        explicit_upper_confirm = (
            float(response.r_bb20_upper_reject) >= 1.0
            or float(response.r_box_upper_reject) >= 1.0
            or bb44_state in {"UPPER", "UPPER_EDGE", "ABOVE"}
            or x_bb44 >= _MIXED_UPPER_REJECT_BB44_CONFIRM_THRESHOLD
        )
        mixed_upper_reject_support = (
            float(sell_support)
            + min(0.18, upper_reject_response * 0.18)
            + min(0.10, max(x_bb20, 0.0) * 0.20 + max(x_bb44, 0.0) * 0.24)
        )
        xau_local_upper_confirm = bool(
            xau_local_mixed_upper_reject_override
            and upper_reject_response
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "mixed_upper_reject",
                "confirm_response_min",
                default=0.12,
            )
            and mixed_upper_reject_support
            >= max(
                _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "mixed_support_floor",
                    default=0.18,
                ),
                buy_support
                + _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "confirm_buy_support_margin",
                    default=0.02,
                ),
            )
            and sell_support
            >= max(
                _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "confirm_sell_support_floor",
                    default=0.10,
                ),
                buy_support
                + _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "mixed_upper_reject",
                    "confirm_sell_support_buy_margin",
                    default=-0.04,
                ),
            )
        )
        action = "SELL" if (explicit_upper_confirm or xau_local_upper_confirm) else "WAIT"
        reason = "upper_reject_mixed_confirm" if action == "SELL" else "upper_reject_mixed_observe"
        return (_emit_confirm if action == "SELL" else _emit_observe)(
            action=action,
            side="SELL",
            confidence=_support_confidence(
                mixed_upper_reject_support,
                upper_reject_response,
                minimum=max(0.22, upper_reject_response * 0.72),
            ),
            reason=reason,
            archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
            metadata={
                "mixed_upper_reject_override": True,
                "xau_local_upper_reject_context": bool(xau_local_mixed_upper_reject_override),
                "xau_local_upper_confirm": bool(xau_local_upper_confirm),
                "upper_reject_response": upper_reject_response,
                "lower_reclaim_response": lower_reclaim_response,
                "box_zone": box_state,
                "bb20_zone": bb_state,
                "bb44_zone": bb44_state,
                "routing_guard_exemptions": {
                    "middle_sr_anchor_guard": True,
                    "outer_band_reversal_guard": True,
                },
            },
        )

    if (lower_depth >= 0.35 or lower_edge_active) and lower_context_ok:
        if structural_lower_break_override and lower_break_response > 0.0:
            action = (
                "SELL"
                if _confirm_support_met(
                    candidate_support=max(sell_support, lower_break_response),
                    opposing_support=buy_support,
                    floor=_confirm_floor(symbol, "LOWER_FAIL_CONFIRM"),
                    advantage=0.0,
                )
                else "WAIT"
            )
            reason = "lower_support_fail_confirm" if action == "SELL" else "lower_support_fail_observe"
            return (_emit_confirm if action == "SELL" else _emit_observe)(
                action=action,
                side="SELL",
                confidence=_support_confidence(max(sell_support, lower_break_response), sell_support),
                reason=reason,
                archetype_id=ARCHETYPE_LOWER_BREAK_SELL,
                metadata={
                    "lower_depth": lower_depth,
                    "structural_break_override": True,
                    "box_lower_break": float(response.r_box_lower_break),
                    "bb20_lower_hold": float(response.r_bb20_lower_hold),
                },
            )
        btc_midline_transition = _btc_midline_rebound_transition(
            symbol=symbol,
            box_zone=box_state,
            bb_zone=bb_state,
            x_bb20=float(x_bb20),
            lower_reclaim_response=float(lower_reclaim_response),
            upper_reject_response=float(upper_reject_response),
            mid_lose_response=float(mid_lose_response),
            upper_break_response=float(upper_break_response),
            buy_support=float(buy_support),
            sell_support=float(sell_support),
            strong_lower_continuation_context=bool(strong_lower_continuation_context),
            upper_break_continuation_context=bool(upper_break_continuation_context),
            explicit_upper_reject_signal=bool(_explicit_upper_reject_signal(response)),
        )
        if bool(btc_midline_transition.get("active")):
            transition_side = str(btc_midline_transition.get("side", "") or "")
            return _emit_observe(
                action="WAIT",
                side=transition_side,
                confidence=float(btc_midline_transition.get("confidence", 0.0) or 0.0),
                reason=str(btc_midline_transition.get("reason", "") or "middle_wait"),
                archetype_id=str(btc_midline_transition.get("archetype_id", "") or ""),
                metadata={
                    "lower_depth": lower_depth,
                    "lower_reclaim_response": float(lower_reclaim_response),
                    "upper_reject_response": float(upper_reject_response),
                    "mid_lose_response": float(mid_lose_response),
                    "upper_break_response": float(upper_break_response),
                    "btc_midline_rebound_transition_v1": {
                        "active": True,
                        "side": transition_side,
                        "reason": str(btc_midline_transition.get("reason", "") or ""),
                        "box_zone": str(box_state or ""),
                        "bb20_zone": str(bb_state or ""),
                        "x_bb20": float(x_bb20),
                    },
                    "routing_guard_exemptions": (
                        {"middle_sr_anchor_guard": True}
                        if transition_side == "SELL"
                        else {}
                    ),
                },
            )
        lower_rebound_floor = _confirm_floor(symbol, "LOWER_REBOUND_CONFIRM")
        lower_rebound_advantage = _confirm_advantage(symbol, "LOWER_REBOUND_CONFIRM")
        rebound_buy_support = buy_support
        if lower_reclaim_response > 0.0:
            lower_rebound_floor = min(lower_rebound_floor, 0.06)
            lower_rebound_advantage = min(lower_rebound_advantage, 0.003)
            rebound_buy_support += min(0.10, lower_reclaim_response * 0.12)
        if interpretation.secondary_context_label == "LOWER_CONTEXT":
            rebound_buy_support += min(0.03, secondary_lower_context_support * 0.25)
        xau_second_support_relief_enabled = _symbol_override_flag(
            symbol,
            "router",
            "relief",
            "second_support_probe",
            default=True,
        )
        xau_second_support_probe_relief = bool(
            symbol == "XAUUSD"
            and xau_second_support_relief_enabled
            and box_state in {"LOWER", "LOWER_EDGE"}
            and bb_state in {"MID", "MIDDLE", "LOWER", "LOWER_EDGE", "UNKNOWN"}
            and direction_policy in {"BOTH", "BUY_ONLY"}
            and not strong_lower_continuation_context
            and lower_structural_support_response
            >= _symbol_override_float(
                symbol,
                "router",
                "probe",
                "lower_second_support",
                "structural_support_min",
                default=_XAU_LOWER_SECOND_SUPPORT_STRUCTURAL_MIN,
            )
            and lower_reclaim_response
            >= _symbol_override_float(
                symbol,
                "router",
                "probe",
                "lower_second_support",
                "reclaim_min",
                default=_XAU_LOWER_SECOND_SUPPORT_RECLAIM_MIN,
            )
            and (
                secondary_lower_context_support
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "probe",
                    "lower_second_support",
                    "secondary_min",
                    default=_XAU_LOWER_SECOND_SUPPORT_SECONDARY_MIN,
                )
                or buy_persistence
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "probe",
                    "lower_second_support",
                    "persistence_min",
                    default=_XAU_LOWER_SECOND_SUPPORT_PERSISTENCE_MIN,
                )
                or buy_belief
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "probe",
                    "lower_second_support",
                    "belief_min",
                    default=_XAU_LOWER_SECOND_SUPPORT_BELIEF_MIN,
                )
                or buy_streak >= 1
            )
        )
        btc_lower_structural_relief_enabled = _symbol_override_flag(
            symbol,
            "router",
            "relief",
            "lower_structural_probe",
            default=True,
        )
        btc_lower_probe_support_ready = _probe_support_ready(
            candidate_support=float(rebound_buy_support) + min(0.04, float(lower_structural_support_response) * 0.16),
            opposing_support=sell_support,
            floor=lower_rebound_floor,
            advantage=lower_rebound_advantage,
            floor_mult=_symbol_override_float(
                symbol,
                "router",
                "probe",
                "lower_rebound",
                "floor_mult",
                default=_BTC_LOWER_PROBE_FLOOR_MULT,
            ),
            advantage_mult=_symbol_override_float(
                symbol,
                "router",
                "probe",
                "lower_rebound",
                "advantage_mult",
                default=_BTC_LOWER_PROBE_ADVANTAGE_MULT,
            ),
            tolerance=_symbol_override_float(
                symbol,
                "router",
                "probe",
                "lower_rebound",
                "support_tolerance",
                default=_BTC_LOWER_PROBE_SUPPORT_TOLERANCE,
            ),
        )
        btc_lower_structural_probe_relief_strict = bool(
            symbol == "BTCUSD"
            and btc_lower_structural_relief_enabled
            and box_state in {"LOWER", "LOWER_EDGE"}
            and bb_state in {"MID", "MIDDLE", "LOWER", "LOWER_EDGE", "UNKNOWN"}
            and direction_policy in {"BOTH", "BUY_ONLY"}
            and not strong_lower_continuation_context
            and lower_structural_support_response
            >= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "support_min",
                default=_BTC_LOWER_STRUCTURAL_SUPPORT_MIN,
            )
            and lower_reclaim_response
            >= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "reclaim_min",
                default=_BTC_LOWER_STRUCTURAL_RECLAIM_MIN,
            )
            and (
                secondary_lower_context_support
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "relief",
                    "lower_structural_probe",
                    "secondary_min",
                    default=_BTC_LOWER_STRUCTURAL_SECONDARY_MIN,
                )
                or lower_hold_response >= 0.16
                or rebound_buy_support >= 0.30
            )
            and btc_lower_probe_support_ready
        )
        btc_lower_structural_probe_relief_context = bool(
            symbol == "BTCUSD"
            and btc_lower_structural_relief_enabled
            and raw_box_state == "MIDDLE"
            and _btc_lower_buy_context_ok(symbol, raw_box_state, x_box)
            and raw_bb_state in {"LOWER", "LOWER_EDGE", "UNKNOWN"}
            and direction_policy in {"BOTH", "BUY_ONLY"}
            and not strong_lower_continuation_context
            and confirmed_lower_reversal
            and str(edge_pair_law.get("winner_side", "") or "") == "BUY"
            and lower_structural_support_response
            < _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "support_min",
                default=_BTC_LOWER_STRUCTURAL_SUPPORT_MIN,
            )
            and lower_reclaim_response
            >= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "reclaim_min",
                default=_BTC_LOWER_STRUCTURAL_RECLAIM_MIN,
            )
            and rebound_buy_support
            >= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "context_support_min",
                default=_BTC_LOWER_CONTEXT_SUPPORT_MIN,
            )
            and float(edge_pair_law.get("pair_gap", 0.0) or 0.0)
            >= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "context_pair_gap_min",
                default=_BTC_LOWER_CONTEXT_PAIR_GAP_MIN,
            )
            and float(x_bb44)
            <= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "context_bb44_max",
                default=_BTC_LOWER_CONTEXT_BB44_MAX,
            )
            and float(x_sr)
            <= _symbol_override_float(
                symbol,
                "router",
                "relief",
                "lower_structural_probe",
                "context_sr_min",
                default=_BTC_LOWER_CONTEXT_SR_MIN,
            )
            and btc_lower_probe_support_ready
        )
        btc_lower_structural_probe_relief = bool(
            btc_lower_structural_probe_relief_strict or btc_lower_structural_probe_relief_context
        )
        btc_lower_structural_probe_relief_mode = (
            "structural"
            if btc_lower_structural_probe_relief_strict
            else ("contextual" if btc_lower_structural_probe_relief_context else "")
        )
        if xau_second_support_probe_relief:
            rebound_buy_support += min(0.06, lower_structural_support_response * 0.20)
            rebound_buy_support += min(0.03, max(secondary_lower_context_support, buy_persistence) * 0.20)
        if btc_lower_structural_probe_relief:
            rebound_buy_support += min(0.04, lower_structural_support_response * 0.16)
            rebound_buy_support += min(0.02, max(secondary_lower_context_support, lower_hold_response) * 0.14)
        if lower_edge_active:
            lower_rebound_floor = min(lower_rebound_floor, 0.04)
            lower_rebound_advantage = min(lower_rebound_advantage, 0.001)
            if lower_hold_response > 0.0 or float(response.r_bb20_mid_hold) > 0.0 or float(response.r_box_mid_hold) > 0.0:
                rebound_buy_support += min(
                    0.14,
                    lower_hold_response * 0.18
                    + float(response.r_bb20_mid_hold) * 0.08
                    + float(response.r_box_mid_hold) * 0.06,
                )
        if strong_lower_continuation_context:
            lower_rebound_floor = max(lower_rebound_floor, 0.20)
            lower_rebound_advantage = max(lower_rebound_advantage, 0.05)
        if lower_reclaim_response > 0.0:
            lower_probe_temperament = _symbol_probe_temperament(
                symbol,
                context_label=str(edge_pair_law.get("context_label", "") or ""),
                trigger_branch="lower_rebound",
                probe_direction="BUY",
                second_support_relief=xau_second_support_probe_relief,
            )
            confirm_ready = _confirm_support_met(
                candidate_support=rebound_buy_support,
                opposing_support=sell_support,
                floor=lower_rebound_floor,
                advantage=lower_rebound_advantage,
            )
            probe_ready = (
                not confirm_ready
                and (lower_edge_active or lower_depth >= 0.90)
                    and _probe_support_ready(
                        candidate_support=rebound_buy_support,
                        opposing_support=sell_support,
                        floor=lower_rebound_floor,
                        advantage=lower_rebound_advantage,
                        floor_mult=_probe_temperament_value(
                            lower_probe_temperament,
                            key="floor_mult",
                            policy_field="default_floor_mult",
                            default=_EDGE_PROBE_FLOOR_MULT,
                        ),
                        advantage_mult=_probe_temperament_value(
                            lower_probe_temperament,
                            key="advantage_mult",
                            policy_field="default_advantage_mult",
                            default=_EDGE_PROBE_ADVANTAGE_MULT,
                        ),
                        tolerance=_probe_temperament_value(
                            lower_probe_temperament,
                            key="support_tolerance",
                            policy_field="default_support_tolerance",
                            default=_EDGE_PROBE_SUPPORT_TOLERANCE,
                        ),
                    )
                )
            probe_ready = bool(
                probe_ready
                or (
                    not confirm_ready
                    and (xau_second_support_probe_relief or btc_lower_structural_probe_relief)
                )
            )
            nas_clean_confirm_middle_anchor_relief = _nas_clean_confirm_middle_anchor_relief(
                symbol=symbol,
                side="BUY",
                direction_policy=direction_policy,
                candidate_support=float(rebound_buy_support),
                edge_pair_law=edge_pair_law,
                probe_temperament=lower_probe_temperament,
                forecast_assist=middle_anchor_forecast_assist,
            )
            if confirm_ready and lower_reclaim_response < 0.40 and not strong_lower_continuation_context:
                confirm_ready = False
                probe_ready = True
            action = "BUY" if (confirm_ready or probe_ready) else "WAIT"
            if action == "BUY" and not _btc_lower_buy_context_ok(symbol, box_state, x_box):
                action = "WAIT"
                probe_ready = False
            if action == "BUY" and strong_lower_continuation_context and not confirmed_lower_reversal:
                action = "WAIT"
                probe_ready = False
            probe_metadata = (
                _build_probe_candidate_metadata(
                    probe_direction="BUY",
                    trigger_branch="lower_rebound",
                    candidate_support=float(rebound_buy_support),
                    opposing_support=float(sell_support),
                    floor=float(lower_rebound_floor),
                    advantage=float(lower_rebound_advantage),
                    near_confirm=True,
                    probe_temperament=dict(lower_probe_temperament),
                )
                if action == "BUY" and probe_ready
                else {}
            )
            return _emit_probe_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                action=action,
                side="BUY",
                probe_ready=probe_ready,
                confidence=_support_confidence(rebound_buy_support),
                confirm_reason="lower_rebound_confirm",
                probe_reason="lower_rebound_probe_observe",
                observe_reason="lower_edge_observe",
                archetype_id=ARCHETYPE_LOWER_HOLD_BUY,
                metadata={
                    "lower_depth": lower_depth,
                    "lower_reclaim_response": lower_reclaim_response,
                    "strong_lower_continuation_context": bool(strong_lower_continuation_context),
                    "confirmed_lower_reversal": bool(confirmed_lower_reversal),
                    "lower_structural_support_response": float(lower_structural_support_response),
                    "xau_second_support_probe_relief": bool(xau_second_support_probe_relief),
                    "btc_lower_structural_probe_relief": bool(btc_lower_structural_probe_relief),
                    "btc_lower_structural_probe_relief_mode": str(btc_lower_structural_probe_relief_mode or ""),
                    "nas_clean_confirm_middle_anchor_relief": bool(nas_clean_confirm_middle_anchor_relief),
                    "symbol_probe_temperament_v1": dict(lower_probe_temperament),
                    "probe_candidate_v1": probe_metadata,
                    "routing_guard_exemptions": {
                        "middle_sr_anchor_guard": bool(nas_clean_confirm_middle_anchor_relief),
                    },
                },
            )
        if response.r_bb20_lower_break > 0.0 or response.r_box_lower_break > 0.0:
            action = (
                "SELL"
                if _confirm_support_met(
                    candidate_support=sell_support,
                    opposing_support=buy_support,
                    floor=_confirm_floor(symbol, "LOWER_FAIL_CONFIRM"),
                    advantage=0.05,
                )
                else "WAIT"
            )
            return _emit_probe_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                action=action,
                side="SELL",
                probe_ready=False,
                confidence=_support_confidence(sell_support, buy_support),
                confirm_reason="lower_support_fail_confirm",
                probe_reason="lower_support_fail_confirm",
                observe_reason="lower_support_fail_observe",
                archetype_id=ARCHETYPE_LOWER_BREAK_SELL,
                metadata={"lower_depth": lower_depth},
            )
        if lower_depth < 0.75 and not lower_edge_active:
            return _emit_observe(
                action="WAIT",
                side="BUY",
                confidence=min(0.99, lower_depth),
                reason="lower_approach_observe",
                archetype_id=ARCHETYPE_LOWER_HOLD_BUY,
                metadata={"lower_depth": lower_depth},
            )
        return _emit_observe(
            action="WAIT",
            side="BUY",
            confidence=min(0.99, lower_depth),
            reason="lower_edge_observe",
            archetype_id=ARCHETYPE_LOWER_HOLD_BUY,
            metadata={"lower_depth": lower_depth},
        )

    if (upper_depth >= 0.35 or upper_edge_active) and upper_context_ok:
        upper_break_branch_ready = bool(explicit_upper_break_response > 0.0 or upper_reclaim_dominance)
        if upper_depth < 0.75 and not upper_edge_active:
            return _emit_observe(
                action="WAIT",
                side="BUY",
                confidence=min(0.99, upper_depth),
                reason="upper_approach_observe",
                archetype_id=ARCHETYPE_UPPER_BREAK_BUY,
                metadata={"upper_depth": upper_depth},
            )
        if upper_reclaim_dominance:
            reclaim_buy_support = float(buy_support) + min(
                0.24,
                (float(upper_break_response) * 0.34) + min(0.12, float(upper_depth) * 0.06),
            )
            reclaim_opposing = max(
                float(upper_reject_response) + 0.01,
                float(sell_support) * (_UPPER_BREAK_CONTINUATION_OPPOSING_SCALE if upper_break_continuation_context else 1.0),
            )
            action = (
                "BUY"
                if _confirm_support_met(
                    candidate_support=reclaim_buy_support,
                    opposing_support=reclaim_opposing,
                    floor=min(_confirm_floor(symbol, "UPPER_BREAK_CONFIRM"), 0.10),
                    advantage=0.0,
                )
                else "WAIT"
            )
            reason = "upper_reclaim_strength_confirm" if action == "BUY" else "upper_reclaim_strength_observe"
            return (_emit_confirm if action == "BUY" else _emit_observe)(
                action=action,
                side="BUY",
                confidence=_support_confidence(
                    reclaim_buy_support,
                    upper_break_response,
                    minimum=max(0.12, upper_break_response * 0.70),
                ),
                reason=reason,
                archetype_id=ARCHETYPE_UPPER_BREAK_BUY,
                metadata={
                    "upper_depth": upper_depth,
                    "upper_reject_response": upper_reject_response,
                    "upper_break_response": upper_break_response,
                    "upper_reclaim_dominance": True,
                    "upper_break_continuation_context": bool(upper_break_continuation_context),
                    "reclaim_buy_support": reclaim_buy_support,
                    "reclaim_opposing": reclaim_opposing,
                },
            )
        if (
            failed_sell_reclaim_signal > 0.0
            and upper_break_branch_ready
            and _btc_lower_buy_context_ok(symbol, box_state, x_box)
            and x_bb20 < 0.0
            and upper_reject_response <= 0.0
            and _confirm_support_met(
                candidate_support=buy_support,
                opposing_support=sell_support,
                floor=_confirm_floor(symbol, "FAILED_SELL_RECLAIM_BUY_CONFIRM"),
                advantage=_confirm_advantage(symbol, "FAILED_SELL_RECLAIM_BUY_CONFIRM"),
            )
        ):
            return _emit_confirm(
                action="BUY",
                side="BUY",
                confidence=_support_confidence(buy_support, failed_sell_reclaim_signal),
                reason="failed_sell_reclaim_buy_confirm",
                archetype_id=ARCHETYPE_MID_RECLAIM_BUY,
                metadata={
                    "upper_depth": upper_depth,
                    "mid_buy_support": mid_buy_support,
                    "x_bb20": float(x_bb20),
                },
            )
        if mid_buy_support > 0.0 and upper_reject_response <= 0.0:
            if not upper_break_branch_ready:
                return _emit_observe(
                    action="WAIT",
                    side="SELL",
                    confidence=min(0.99, max(upper_depth, mid_buy_support)),
                    reason="upper_edge_observe",
                    archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                    metadata={
                        "upper_depth": upper_depth,
                        "mid_buy_support": mid_buy_support,
                        "upper_break_branch_ready": False,
                        "edge_pair_enforced": True,
                    },
                )
            return _emit_observe(
                action="WAIT",
                side="BUY",
                confidence=min(0.99, max(upper_depth, mid_buy_support)),
                reason="upper_support_hold_observe",
                archetype_id=ARCHETYPE_UPPER_BREAK_BUY,
                metadata={"upper_depth": upper_depth, "mid_buy_support": mid_buy_support},
            )
        if (
            (response.r_bb20_upper_break > 0.0 or response.r_box_upper_break > 0.0)
            and upper_reject_response > 0.0
            and (not strong_upper_continuation_context or confirmed_upper_reversal)
            and _confirm_support_met(
                candidate_support=sell_support,
                opposing_support=buy_support,
                floor=_confirm_floor(symbol, "UPPER_REJECT_CONFIRM"),
                advantage=0.08,
            )
            and upper_depth >= 1.0
            and direction_policy in {"BOTH", "SELL_ONLY"}
        ):
            return _emit_confirm(
                action="SELL",
                side="SELL",
                confidence=_support_confidence(sell_support),
                reason="upper_break_fail_confirm",
                archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                metadata={
                    "upper_depth": upper_depth,
                    "trigger": "upper_break_fail",
                    "strong_upper_continuation_context": bool(strong_upper_continuation_context),
                    "confirmed_upper_reversal": bool(confirmed_upper_reversal),
                },
            )
        xau_upper_context_enabled = _symbol_override_flag(
            symbol,
            "router",
            "context",
            "upper_reject_context",
            default=True,
        )
        xau_local_upper_reject_context = bool(
            symbol == "XAUUSD"
            and xau_upper_context_enabled
            and not strong_upper_continuation_context
            and not upper_reclaim_dominance
            and direction_policy in {"BOTH", "SELL_ONLY"}
            and x_bb20
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "upper_reject_context",
                "bb20_min",
                default=-0.08,
            )
            and upper_structural_reject_response
            >= _symbol_override_float(
                symbol,
                "router",
                "context",
                "upper_reject_context",
                "structural_reject_min",
                default=_XAU_UPPER_STRUCTURAL_REJECT_MIN,
            )
            and (
                float(response.r_sr_resistance_reject)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_context",
                    "sr_resistance_min",
                    default=0.10,
                )
                or float(response.r_trend_resistance_reject_m15)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_context",
                    "trend_resistance_m15_min",
                    default=0.08,
                )
                or float(response.r_bb20_mid_lose)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_context",
                    "bb20_mid_lose_min",
                    default=0.06,
                )
                or float(response.r_box_mid_reject)
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "context",
                    "upper_reject_context",
                    "box_mid_reject_min",
                    default=0.06,
                )
                or sell_support
                >= max(
                    _symbol_override_float(
                        symbol,
                        "router",
                        "context",
                        "upper_reject_context",
                        "sell_support_floor",
                        default=0.12,
                    ),
                    buy_support
                    + _symbol_override_float(
                        symbol,
                        "router",
                        "context",
                        "upper_reject_context",
                        "sell_support_buy_margin",
                        default=-0.02,
                    ),
                )
            )
        )
        if upper_reject_response > 0.0 and (x_bb20 >= 0.0 or xau_local_upper_reject_context):
            upper_probe_temperament = _symbol_probe_temperament(
                symbol,
                context_label=str(edge_pair_law.get("context_label", "") or ""),
                trigger_branch="upper_reject",
                probe_direction="SELL",
            )
            upper_reject_floor = _confirm_floor(symbol, "UPPER_REJECT_CONFIRM")
            upper_reject_advantage = 0.05
            if strong_upper_continuation_context:
                upper_reject_floor = max(upper_reject_floor, 0.20)
                upper_reject_advantage = max(upper_reject_advantage, 0.08)
            confirm_ready = _confirm_support_met(
                candidate_support=sell_support,
                opposing_support=buy_support,
                floor=upper_reject_floor,
                advantage=upper_reject_advantage,
            )
            xau_upper_structural_relief_enabled = _symbol_override_flag(
                symbol,
                "router",
                "relief",
                "upper_structural_probe",
                default=True,
            )
            xau_structural_probe_relief = bool(
                symbol == "XAUUSD"
                and xau_upper_structural_relief_enabled
                and (upper_edge_active or xau_local_upper_reject_context)
                and not strong_upper_continuation_context
                and not upper_reclaim_dominance
                and upper_structural_reject_response
                >= _symbol_override_float(
                    symbol,
                    "router",
                    "probe",
                    "upper_reject",
                    "structural_reject_min",
                    default=_XAU_UPPER_STRUCTURAL_REJECT_MIN,
                )
                and direction_policy in {"BOTH", "SELL_ONLY"}
                and _probe_support_ready(
                    candidate_support=float(sell_support) + min(0.05, float(upper_structural_reject_response) * 0.20),
                    opposing_support=buy_support,
                    floor=upper_reject_floor,
                    advantage=upper_reject_advantage,
                    floor_mult=_symbol_override_float(
                        symbol,
                        "router",
                        "probe",
                        "upper_reject",
                        "floor_mult",
                        default=_XAU_UPPER_PROBE_FLOOR_MULT,
                    ),
                    advantage_mult=_symbol_override_float(
                        symbol,
                        "router",
                        "probe",
                        "upper_reject",
                        "advantage_mult",
                        default=_XAU_UPPER_PROBE_ADVANTAGE_MULT,
                    ),
                    tolerance=_symbol_override_float(
                        symbol,
                        "router",
                        "probe",
                        "upper_reject",
                        "support_tolerance",
                        default=_XAU_UPPER_PROBE_SUPPORT_TOLERANCE,
                    ),
                )
            )
            probe_ready = (
                not confirm_ready
                and (upper_edge_active or upper_depth >= 0.90 or xau_local_upper_reject_context)
                and _probe_support_ready(
                    candidate_support=sell_support,
                    opposing_support=buy_support,
                    floor=upper_reject_floor,
                    advantage=upper_reject_advantage,
                    floor_mult=_probe_temperament_value(
                        upper_probe_temperament,
                        key="floor_mult",
                        policy_field="default_floor_mult",
                        default=_EDGE_PROBE_FLOOR_MULT,
                    ),
                    advantage_mult=_probe_temperament_value(
                        upper_probe_temperament,
                        key="advantage_mult",
                        policy_field="default_advantage_mult",
                        default=_EDGE_PROBE_ADVANTAGE_MULT,
                    ),
                    tolerance=_probe_temperament_value(
                        upper_probe_temperament,
                        key="support_tolerance",
                        policy_field="default_support_tolerance",
                        default=_EDGE_PROBE_SUPPORT_TOLERANCE,
                    ),
                )
            )
            probe_ready = bool(probe_ready or (not confirm_ready and xau_structural_probe_relief))
            nas_clean_confirm_middle_anchor_relief = _nas_clean_confirm_middle_anchor_relief(
                symbol=symbol,
                side="SELL",
                direction_policy=direction_policy,
                candidate_support=float(sell_support),
                edge_pair_law=edge_pair_law,
                probe_temperament=upper_probe_temperament,
                forecast_assist=middle_anchor_forecast_assist,
            )
            if confirm_ready and upper_reject_response < 0.40 and not strong_upper_continuation_context:
                confirm_ready = False
                probe_ready = True
            action = "SELL" if (confirm_ready or probe_ready) else "WAIT"
            if action == "SELL" and strong_upper_continuation_context and not confirmed_upper_reversal:
                action = "WAIT"
                probe_ready = False
            probe_metadata = (
                _build_probe_candidate_metadata(
                    probe_direction="SELL",
                    trigger_branch="upper_reject",
                    candidate_support=float(sell_support),
                    opposing_support=float(buy_support),
                    floor=float(upper_reject_floor),
                    advantage=float(upper_reject_advantage),
                    near_confirm=True,
                    probe_temperament=dict(upper_probe_temperament),
                )
                if action == "SELL" and probe_ready
                else {}
            )
            return _emit_probe_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                action=action,
                side="SELL",
                probe_ready=probe_ready,
                confidence=_support_confidence(sell_support),
                confirm_reason="upper_reject_confirm",
                probe_reason="upper_reject_probe_observe",
                observe_reason="upper_edge_observe",
                archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
                metadata={
                    "upper_depth": upper_depth,
                    "upper_structural_reject_response": float(upper_structural_reject_response),
                    "strong_upper_continuation_context": bool(strong_upper_continuation_context),
                    "confirmed_upper_reversal": bool(confirmed_upper_reversal),
                    "xau_local_upper_reject_context": bool(xau_local_upper_reject_context),
                    "xau_structural_probe_relief": bool(xau_structural_probe_relief),
                    "nas_clean_confirm_middle_anchor_relief": bool(nas_clean_confirm_middle_anchor_relief),
                    "symbol_probe_temperament_v1": dict(upper_probe_temperament),
                    "probe_candidate_v1": probe_metadata,
                    "routing_guard_exemptions": {
                        "middle_sr_anchor_guard": bool(
                            xau_structural_probe_relief
                            or xau_local_upper_reject_context
                            or nas_clean_confirm_middle_anchor_relief
                        ),
                        "outer_band_reversal_guard": bool(
                            xau_structural_probe_relief or xau_local_upper_reject_context
                        ),
                    },
                },
            )
        if response.r_bb20_upper_break > 0.0 or response.r_box_upper_break > 0.0:
            action = (
                "BUY"
                if _confirm_support_met(
                    candidate_support=buy_support,
                    opposing_support=sell_support,
                    floor=_confirm_floor(symbol, "UPPER_BREAK_CONFIRM"),
                    advantage=0.05,
                )
                else "WAIT"
            )
            return _emit_probe_transition(
                emit_confirm=_emit_confirm,
                emit_observe=_emit_observe,
                action=action,
                side="BUY",
                probe_ready=False,
                confidence=_support_confidence(buy_support, sell_support),
                confirm_reason="upper_break_confirm",
                probe_reason="upper_break_confirm",
                observe_reason="upper_break_observe",
                archetype_id=ARCHETYPE_UPPER_BREAK_BUY,
                metadata={"upper_depth": upper_depth},
            )
        return _emit_observe(
            action="WAIT",
            side="SELL",
            confidence=min(0.99, upper_depth),
            reason="upper_edge_observe",
            archetype_id=ARCHETYPE_UPPER_REJECT_SELL,
            metadata={"upper_depth": upper_depth},
        )

    return _emit_observe(
        action="WAIT",
        side="",
        confidence=_support_confidence(abs(support_gap), minimum=0.1),
        reason="observe_default",
        archetype_id="",
        metadata={"support_gap": float(support_gap)},
    )


def route_observe_confirm(
    position: PositionVector,
    response: ResponseVector,
    state: StateInput,
    position_snapshot: PositionSnapshot,
    *,
    evidence_vector_v1: EvidenceVector | None = None,
    belief_state_v1: BeliefState | None = None,
    barrier_state_v1: BarrierState | None = None,
    transition_forecast_v1: TransitionForecast | None = None,
    trade_management_forecast_v1: TradeManagementForecast | None = None,
    forecast_gap_metrics_v1: dict[str, float] | None = None,
) -> ObserveConfirmSnapshot:
    snapshot = _route_observe_confirm_base(
        position,
        response,
        state,
        position_snapshot,
        evidence_vector_v1=evidence_vector_v1,
        belief_state_v1=belief_state_v1,
        barrier_state_v1=barrier_state_v1,
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )
    snapshot = _apply_middle_sr_suppression(
        snapshot,
        position=position,
        position_snapshot=position_snapshot,
        state=state,
    )
    snapshot = _apply_outer_band_reversal_suppression(
        snapshot,
        position=position,
        response=response,
        position_snapshot=position_snapshot,
    )
    snapshot = _apply_barrier_suppression(
        snapshot,
        barrier_state_v1=barrier_state_v1,
    )
    snapshot = _apply_forecast_modulation(
        snapshot,
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )
    return _attach_routing_policy_metadata(
        snapshot,
        evidence_vector_v1=evidence_vector_v1,
        belief_state_v1=belief_state_v1,
        barrier_state_v1=barrier_state_v1,
        transition_forecast_v1=transition_forecast_v1,
        trade_management_forecast_v1=trade_management_forecast_v1,
        forecast_gap_metrics_v1=forecast_gap_metrics_v1,
    )

