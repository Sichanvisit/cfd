"""Temperament overlays for exit recovery policy."""

from __future__ import annotations

from backend.services.symbol_temperament import resolve_edge_execution_overrides


def _coerce_mapping(payload) -> dict:
    return dict(payload or {}) if isinstance(payload, dict) else {}


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_str(value, default: str = "") -> str:
    text = str(value or default).strip()
    return text if text else str(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


def _state_execution_overrides(*, state_vector_v2=None, state_metadata=None) -> dict:
    state_vector = _coerce_mapping(state_vector_v2)
    metadata = _coerce_mapping(state_metadata or state_vector.get("metadata"))
    if not state_vector:
        return {
            "active": False,
            "max_wait_mult": 1.0,
            "be_loss_mult": 1.0,
            "tp1_loss_mult": 1.0,
            "reverse_gap_mult": 1.0,
            "force_disable_wait_be": False,
            "force_disable_wait_tp1": False,
            "patience_state_label": "",
            "topdown_state_label": "",
            "execution_friction_state": "",
            "session_exhaustion_state": "",
            "event_risk_state": "",
        }

    wait_gain = _clamp(_to_float(state_vector.get("wait_patience_gain", 1.0), 1.0), 0.70, 1.60)
    hold_gain = _clamp(_to_float(state_vector.get("hold_patience_gain", 1.0), 1.0), 0.70, 1.55)
    fast_exit_risk = _clamp(_to_float(state_vector.get("fast_exit_risk_penalty", 0.0), 0.0), 0.0, 1.0)
    patience_state_label = _to_str(metadata.get("patience_state_label", "")).upper()
    topdown_state_label = _to_str(metadata.get("topdown_state_label", "")).upper()
    execution_friction_state = _to_str(metadata.get("execution_friction_state", "")).upper()
    session_exhaustion_state = _to_str(metadata.get("session_exhaustion_state", "")).upper()
    event_risk_state = _to_str(metadata.get("event_risk_state", "")).upper()

    max_wait_mult = 1.0 + ((wait_gain - 1.0) * 0.28) + ((hold_gain - 1.0) * 0.32) - (fast_exit_risk * 0.24)
    be_loss_mult = 1.0 + ((wait_gain - 1.0) * 0.10) + ((hold_gain - 1.0) * 0.08) - (fast_exit_risk * 0.18)
    tp1_loss_mult = 1.0 + ((wait_gain - 1.0) * 0.14) + ((hold_gain - 1.0) * 0.18) - (fast_exit_risk * 0.22)
    reverse_gap_mult = 1.0 + ((hold_gain - 1.0) * 0.18) - (fast_exit_risk * 0.16)
    high_stress_count = 0
    low_stress_count = 0

    if patience_state_label == "HOLD_FAVOR":
        max_wait_mult += 0.08
        tp1_loss_mult += 0.04
        reverse_gap_mult += 0.05
    elif patience_state_label == "WAIT_FAVOR":
        max_wait_mult += 0.05
        be_loss_mult += 0.03
    elif patience_state_label == "FAST_EXIT_FAVOR":
        max_wait_mult -= 0.16
        be_loss_mult -= 0.08
        tp1_loss_mult -= 0.10
        reverse_gap_mult -= 0.08
        high_stress_count += 1

    if execution_friction_state == "HIGH_FRICTION":
        max_wait_mult -= 0.14
        be_loss_mult -= 0.10
        tp1_loss_mult -= 0.12
        reverse_gap_mult -= 0.04
        high_stress_count += 1
    elif execution_friction_state == "LOW_FRICTION":
        max_wait_mult += 0.04
        tp1_loss_mult += 0.02
        low_stress_count += 1

    if session_exhaustion_state == "HIGH_EXHAUSTION_RISK":
        max_wait_mult -= 0.18
        tp1_loss_mult -= 0.12
        reverse_gap_mult -= 0.04
        high_stress_count += 1
    elif session_exhaustion_state == "LOW_EXHAUSTION_RISK":
        max_wait_mult += 0.04
        low_stress_count += 1

    if event_risk_state == "HIGH_EVENT_RISK":
        max_wait_mult -= 0.22
        be_loss_mult -= 0.08
        tp1_loss_mult -= 0.14
        reverse_gap_mult -= 0.08
        high_stress_count += 1
    elif event_risk_state == "LOW_EVENT_RISK":
        max_wait_mult += 0.03
        low_stress_count += 1

    if topdown_state_label in {"BULL_CONFLUENCE", "BEAR_CONFLUENCE"}:
        max_wait_mult += 0.04
        reverse_gap_mult += 0.04
        low_stress_count += 1
    elif topdown_state_label == "TOPDOWN_CONFLICT":
        max_wait_mult -= 0.08
        reverse_gap_mult -= 0.05
        high_stress_count += 1

    return {
        "active": True,
        "max_wait_mult": _clamp(max_wait_mult, 0.65, 1.28),
        "be_loss_mult": _clamp(be_loss_mult, 0.78, 1.18),
        "tp1_loss_mult": _clamp(tp1_loss_mult, 0.72, 1.20),
        "reverse_gap_mult": _clamp(reverse_gap_mult, 0.82, 1.16),
        "force_disable_wait_be": bool(high_stress_count >= 3 and patience_state_label == "FAST_EXIT_FAVOR"),
        "force_disable_wait_tp1": bool(high_stress_count >= 2 and patience_state_label != "HOLD_FAVOR"),
        "patience_state_label": patience_state_label,
        "topdown_state_label": topdown_state_label,
        "execution_friction_state": execution_friction_state,
        "session_exhaustion_state": session_exhaustion_state,
        "event_risk_state": event_risk_state,
        "high_stress_count": int(high_stress_count),
        "low_stress_count": int(low_stress_count),
    }


def _state_edge_rotation_reverse_overrides(
    *,
    state_vector_v2=None,
    state_metadata=None,
    entry_setup_id: str = "",
) -> dict:
    state_vector = _coerce_mapping(state_vector_v2)
    metadata = _coerce_mapping(state_metadata or state_vector.get("metadata"))
    setup_id = _to_str(entry_setup_id).lower()
    if setup_id not in {"range_lower_reversal_buy", "range_upper_reversal_sell"} or not metadata:
        return {
            "active": False,
            "prefer_reverse": False,
            "reverse_gap_mult": 1.0,
            "reason": "",
        }

    regime_state_label = _to_str(metadata.get("regime_state_label", "")).upper()
    session_regime_state = _to_str(metadata.get("session_regime_state", "")).upper()
    topdown_confluence_state = _to_str(metadata.get("topdown_confluence_state", "")).upper()
    execution_friction_state = _to_str(metadata.get("execution_friction_state", "")).upper()
    patience_state_label = _to_str(metadata.get("patience_state_label", "")).upper()

    if session_regime_state != "SESSION_EDGE_ROTATION":
        return {"active": False, "prefer_reverse": False, "reverse_gap_mult": 1.0, "reason": "session_not_edge_rotation"}
    if regime_state_label not in {"RANGE_SWING", "CHOP_NOISE", "RANGE_COMPRESSION"}:
        return {"active": False, "prefer_reverse": False, "reverse_gap_mult": 1.0, "reason": "regime_not_mean_reversion"}
    if topdown_confluence_state in {"BULL_CONFLUENCE", "BEAR_CONFLUENCE"}:
        return {"active": False, "prefer_reverse": False, "reverse_gap_mult": 1.0, "reason": "strong_topdown_confluence"}
    if execution_friction_state == "HIGH_FRICTION":
        return {"active": False, "prefer_reverse": False, "reverse_gap_mult": 1.0, "reason": "high_execution_friction"}
    if patience_state_label == "FAST_EXIT_FAVOR":
        return {"active": False, "prefer_reverse": False, "reverse_gap_mult": 1.0, "reason": "fast_exit_state"}
    return {
        "active": True,
        "prefer_reverse": True,
        "reverse_gap_mult": 0.78,
        "reason": "edge_rotation_reverse_ready",
    }


def _symbol_edge_execution_overrides(
    *,
    symbol: str = "",
    entry_setup_id: str = "",
    entry_direction: str = "",
) -> dict:
    return resolve_edge_execution_overrides(
        symbol=symbol,
        entry_setup_id=entry_setup_id,
        entry_direction=entry_direction,
    )


def _belief_execution_overrides(*, belief_state_v1=None, entry_direction: str = "") -> dict:
    belief_state = _coerce_mapping(belief_state_v1)
    metadata = _coerce_mapping(belief_state.get("metadata"))
    entry_side = _to_str(entry_direction, "").upper()
    if not belief_state or entry_side not in {"BUY", "SELL"}:
        return {
            "active": False,
            "max_wait_mult": 1.0,
            "be_loss_mult": 1.0,
            "tp1_loss_mult": 1.0,
            "reverse_gap_mult": 1.0,
            "prefer_hold_extension": False,
            "prefer_fast_cut": False,
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "same_side_confirmed": False,
            "opposite_side_rising": False,
            "active_persistence": 0.0,
            "opposite_persistence": 0.0,
            "active_streak": 0,
            "opposite_streak": 0,
            "belief_spread": 0.0,
            "dominance_deadband": 0.05,
        }

    dominant_side = _to_str(
        belief_state.get("dominant_side", metadata.get("global_dominant_side", "BALANCED")),
        "BALANCED",
    ).upper()
    dominant_mode = _to_str(
        belief_state.get("dominant_mode", metadata.get("global_dominant_mode", "balanced")),
        "balanced",
    ).lower()
    buy_persistence = _clamp(_to_float(belief_state.get("buy_persistence", 0.0), 0.0), 0.0, 1.0)
    sell_persistence = _clamp(_to_float(belief_state.get("sell_persistence", 0.0), 0.0), 0.0, 1.0)
    buy_streak = max(0, int(_to_float(belief_state.get("buy_streak", metadata.get("buy_streak", 0)), 0)))
    sell_streak = max(0, int(_to_float(belief_state.get("sell_streak", metadata.get("sell_streak", 0)), 0)))
    belief_spread = _to_float(belief_state.get("belief_spread", 0.0), 0.0)
    dominance_deadband = max(0.01, _to_float(metadata.get("dominance_deadband", 0.05), 0.05))
    spread_abs = abs(float(belief_spread))
    spread_clear = spread_abs >= max(dominance_deadband * 1.20, 0.06)

    if entry_side == "BUY":
        active_persistence = buy_persistence
        opposite_persistence = sell_persistence
        active_streak = buy_streak
        opposite_streak = sell_streak
        opposite_dominant = belief_spread <= -max(dominance_deadband, 0.03)
    else:
        active_persistence = sell_persistence
        opposite_persistence = buy_persistence
        active_streak = sell_streak
        opposite_streak = buy_streak
        opposite_dominant = belief_spread >= max(dominance_deadband, 0.03)

    same_side_confirmed = bool(
        dominant_side == entry_side
        and spread_clear
        and active_persistence >= 0.38
        and active_streak >= 2
    )
    opposite_side_rising = bool(
        opposite_dominant
        and opposite_persistence >= 0.24
        and opposite_streak >= 2
    )
    strong_opposite_flip = bool(
        opposite_side_rising
        and opposite_persistence >= 0.38
        and dominant_side not in {"", "BALANCED", entry_side}
    )

    max_wait_mult = 1.0
    be_loss_mult = 1.0
    tp1_loss_mult = 1.0
    reverse_gap_mult = 1.0
    if same_side_confirmed:
        max_wait_mult += 0.12
        be_loss_mult += 0.04
        tp1_loss_mult += 0.08
        reverse_gap_mult += 0.06
        if dominant_mode == "continuation":
            max_wait_mult += 0.03
            tp1_loss_mult += 0.02
    if opposite_side_rising:
        max_wait_mult -= 0.18
        be_loss_mult -= 0.06
        tp1_loss_mult -= 0.10
        reverse_gap_mult -= 0.08
        if strong_opposite_flip:
            max_wait_mult -= 0.14
            tp1_loss_mult -= 0.04
            reverse_gap_mult -= 0.04

    return {
        "active": True,
        "max_wait_mult": _clamp(max_wait_mult, 0.68, 1.24),
        "be_loss_mult": _clamp(be_loss_mult, 0.82, 1.12),
        "tp1_loss_mult": _clamp(tp1_loss_mult, 0.74, 1.18),
        "reverse_gap_mult": _clamp(reverse_gap_mult, 0.78, 1.12),
        "prefer_hold_extension": bool(same_side_confirmed),
        "prefer_fast_cut": bool(strong_opposite_flip),
        "dominant_side": dominant_side,
        "dominant_mode": dominant_mode,
        "same_side_confirmed": bool(same_side_confirmed),
        "opposite_side_rising": bool(opposite_side_rising),
        "active_persistence": float(active_persistence),
        "opposite_persistence": float(opposite_persistence),
        "active_streak": int(active_streak),
        "opposite_streak": int(opposite_streak),
        "belief_spread": float(belief_spread),
        "dominance_deadband": float(dominance_deadband),
    }


def resolve_exit_recovery_temperament_bundle_v1(
    *,
    symbol: str = "",
    entry_setup_id: str = "",
    entry_direction: str = "",
    state_vector_v2: dict | None = None,
    state_metadata: dict | None = None,
    belief_state_v1: dict | None = None,
) -> dict:
    symbol_u = _to_str(symbol).upper()
    setup_id = _to_str(entry_setup_id).lower()
    entry_side = _to_str(entry_direction).upper()
    return {
        "symbol": str(symbol_u),
        "entry_setup_id": str(setup_id),
        "entry_direction": str(entry_side),
        "state_execution_overrides_v1": dict(
            _state_execution_overrides(
                state_vector_v2=state_vector_v2,
                state_metadata=state_metadata,
            )
        ),
        "belief_execution_overrides_v1": dict(
            _belief_execution_overrides(
                belief_state_v1=belief_state_v1,
                entry_direction=entry_side,
            )
        ),
        "state_edge_reverse_v1": dict(
            _state_edge_rotation_reverse_overrides(
                state_vector_v2=state_vector_v2,
                state_metadata=state_metadata,
                entry_setup_id=setup_id,
            )
        ),
        "symbol_edge_execution_overrides_v1": dict(
            _symbol_edge_execution_overrides(
                symbol=symbol_u,
                entry_setup_id=setup_id,
                entry_direction=entry_side,
            )
        ),
    }


def apply_exit_recovery_temperament_v1(
    *,
    base_policy: dict | None,
    temperament_bundle: dict | None,
    default_be_max_loss_usd: float,
    default_tp1_max_loss_usd: float,
    default_max_wait_seconds: int,
    default_reverse_score_gap: int,
) -> dict:
    policy = dict(base_policy or {})
    bundle = dict(temperament_bundle or {})
    state_overrides = _coerce_mapping(bundle.get("state_execution_overrides_v1"))
    belief_overrides = _coerce_mapping(bundle.get("belief_execution_overrides_v1"))
    edge_reverse_overrides = _coerce_mapping(bundle.get("state_edge_reverse_v1"))
    symbol_edge_overrides = _coerce_mapping(bundle.get("symbol_edge_execution_overrides_v1"))

    if state_overrides.get("active"):
        policy["max_wait_seconds"] = max(
            20,
            int(round(float(policy.get("max_wait_seconds", default_max_wait_seconds)) * float(state_overrides["max_wait_mult"]))),
        )
        policy["be_max_loss_usd"] = round(
            max(0.05, float(policy.get("be_max_loss_usd", default_be_max_loss_usd)) * float(state_overrides["be_loss_mult"])),
            4,
        )
        policy["tp1_max_loss_usd"] = round(
            max(0.0, float(policy.get("tp1_max_loss_usd", default_tp1_max_loss_usd)) * float(state_overrides["tp1_loss_mult"])),
            4,
        )
        policy["reverse_score_gap"] = max(
            1,
            int(round(float(policy.get("reverse_score_gap", default_reverse_score_gap)) * float(state_overrides["reverse_gap_mult"]))),
        )
        if bool(state_overrides.get("force_disable_wait_be", False)):
            policy["allow_wait_be"] = False
        if bool(state_overrides.get("force_disable_wait_tp1", False)):
            policy["allow_wait_tp1"] = False

    if belief_overrides.get("active"):
        policy["max_wait_seconds"] = max(
            20,
            int(round(float(policy.get("max_wait_seconds", default_max_wait_seconds)) * float(belief_overrides["max_wait_mult"]))),
        )
        policy["be_max_loss_usd"] = round(
            max(0.05, float(policy.get("be_max_loss_usd", default_be_max_loss_usd)) * float(belief_overrides["be_loss_mult"])),
            4,
        )
        policy["tp1_max_loss_usd"] = round(
            max(0.0, float(policy.get("tp1_max_loss_usd", default_tp1_max_loss_usd)) * float(belief_overrides["tp1_loss_mult"])),
            4,
        )
        policy["reverse_score_gap"] = max(
            1,
            int(round(float(policy.get("reverse_score_gap", default_reverse_score_gap)) * float(belief_overrides["reverse_gap_mult"]))),
        )
        if bool(belief_overrides.get("prefer_fast_cut", False)):
            policy["allow_wait_tp1"] = False

    if edge_reverse_overrides.get("active"):
        policy["prefer_reverse"] = bool(edge_reverse_overrides.get("prefer_reverse", policy.get("prefer_reverse", False)))
        policy["reverse_score_gap"] = max(
            1,
            int(round(float(policy.get("reverse_score_gap", default_reverse_score_gap)) * float(edge_reverse_overrides.get("reverse_gap_mult", 1.0)))),
        )

    policy["state_execution_overrides_v1"] = dict(state_overrides)
    policy["belief_execution_overrides_v1"] = dict(belief_overrides)
    policy["state_edge_reverse_v1"] = dict(edge_reverse_overrides)
    policy["symbol_edge_execution_overrides_v1"] = dict(symbol_edge_overrides)
    return policy
