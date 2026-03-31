from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.energy_engine import (
    POSITION_WEIGHT_PRIORITY,
    POSITION_WEIGHT_ROLES,
    POSITION_WEIGHTS,
    compute_energy_snapshot,
)
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EnergySnapshot,
    EvidenceVector,
    PositionVector,
    ResponseVector,
    StateVector,
    StateVectorV2,
    TradeManagementForecast,
    TransitionForecast,
)
from backend.trading.engine.core.observe_confirm_router import route_observe_confirm
from backend.trading.engine.position import build_position_vector, summarize_position
from backend.trading.engine.response import build_response_vector
from backend.trading.engine.state import build_state_vector

_EXPECTED_INVALIDATION_BY_ARCHETYPE = {
    "upper_reject_sell": "upper_break_reclaim",
    "upper_break_buy": "breakout_failure",
    "lower_hold_buy": "lower_support_fail",
    "lower_break_sell": "breakdown_failure",
    "mid_reclaim_buy": "mid_relose",
    "mid_lose_sell": "mid_reclaim",
}

_EXPECTED_MANAGEMENT_PROFILE_BY_ARCHETYPE = {
    "upper_reject_sell": "reversal_profile",
    "upper_break_buy": "breakout_hold_profile",
    "lower_hold_buy": "support_hold_profile",
    "lower_break_sell": "breakdown_hold_profile",
    "mid_reclaim_buy": "mid_reclaim_fast_exit_profile",
    "mid_lose_sell": "mid_lose_fast_exit_profile",
}


def _build_ctx(**metadata):
    return build_engine_context(
        symbol="BTCUSD",
        price=95.0,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        ma20=99.0,
        ma60=98.0,
        ma120=97.0,
        ma240=96.0,
        ma480=95.0,
        support=90.0,
        resistance=110.0,
        volatility_scale=5.0,
        metadata=metadata,
    )


def _route(position: PositionVector, response: ResponseVector, state: StateVector, energy: EnergySnapshot, **kwargs):
    return route_observe_confirm(position, response, state, summarize_position(position), **kwargs)


def _assert_route(
    routed,
    *,
    archetype_id: str,
    action: str,
    state: str | None = None,
    side: str | None = None,
    reason: str | None = None,
) -> None:
    expected_state = state or ("CONFIRM" if action in {"BUY", "SELL"} else "OBSERVE")
    assert routed.state == expected_state
    assert routed.archetype_id == archetype_id
    assert routed.invalidation_id == _EXPECTED_INVALIDATION_BY_ARCHETYPE.get(archetype_id, "")
    assert routed.management_profile_id == _EXPECTED_MANAGEMENT_PROFILE_BY_ARCHETYPE.get(archetype_id, "")
    assert routed.action == action
    if side is not None:
        assert routed.side == side
    if reason is not None:
        assert routed.reason == reason


def test_observe_confirm_forecast_metadata_cannot_override_archetype_identity():
    position = PositionVector(
        x_box=-1.20,
        x_bb20=-0.72,
        x_bb44=-0.38,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=1.0,
        r_box_lower_bounce=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.18,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.64, sell_force=0.12, net_force=0.52)

    routed = _route(
        position,
        response,
        state,
        energy,
        evidence_vector_v1=EvidenceVector(buy_total_evidence=0.82, sell_total_evidence=0.14),
        belief_state_v1=BeliefState(buy_belief=0.71, sell_belief=0.19, buy_persistence=0.66, sell_persistence=0.12),
        barrier_state_v1=BarrierState(buy_barrier=0.18, sell_barrier=0.57),
        transition_forecast_v1=TransitionForecast(
            p_buy_confirm=0.08,
            p_sell_confirm=0.91,
            p_false_break=0.77,
            p_reversal_success=0.22,
            p_continuation_success=0.31,
        ),
        trade_management_forecast_v1=TradeManagementForecast(
            p_continue_favor=0.19,
            p_fail_now=0.74,
            p_recover_after_pullback=0.12,
            p_reach_tp1=0.15,
            p_opposite_edge_reach=0.41,
            p_better_reentry_if_cut=0.58,
        ),
        forecast_gap_metrics_v1={"transition_side_separation": 0.83, "transition_confirm_fake_gap": 0.55},
    )

    assert routed.archetype_id == "lower_hold_buy"
    assert routed.side == "BUY"
    assert routed.metadata["routing_policy_contract_v2"] == "observe_confirm_routing_policy_v2"
    assert routed.metadata["routing_policy_v2"]["forecast_policy"]["identity_override_allowed"] is False
    assert routed.metadata["routing_policy_v2"]["forecast_policy"]["side_override_allowed"] is False
    assert routed.metadata["routing_policy_v2"]["available_inputs"]["transition_forecast_v1"] is True
    assert routed.metadata["confidence_semantics_contract_v2"] == "observe_confirm_confidence_semantics_v2"
    assert routed.metadata["confidence_semantics_v2"]["meaning"] == "execution_readiness_score"
    assert routed.metadata["confidence_semantics_v2"]["identity_separate"] is True


def test_energy_snapshot_biases_buy_on_lower_side_bounce():
    ctx = _build_ctx(
        current_open=99.5,
        current_high=100.8,
        current_low=89.9,
        current_close=100.4,
        previous_close=98.8,
        band_touch_tolerance=0.2,
        box_touch_tolerance=0.2,
        raw_scores={"wait_noise": 5.0, "wait_conflict": 0.0},
        current_disparity=97.4,
        current_volatility_ratio=1.15,
        ma_alignment="BULL",
    )
    position = build_position_vector(ctx)
    response = build_response_vector(ctx)
    state = build_state_vector(ctx)
    energy = compute_energy_snapshot(position, response, state)
    assert energy.buy_force > energy.sell_force
    assert energy.net_force > 0.0


def test_energy_snapshot_uses_explicit_position_weight_priority():
    assert POSITION_WEIGHTS["bb20"] > POSITION_WEIGHTS["box"] > POSITION_WEIGHTS["bb44"]
    assert POSITION_WEIGHTS["bb44"] > POSITION_WEIGHTS["sr"] > POSITION_WEIGHTS["trendline"]
    assert POSITION_WEIGHT_PRIORITY == ("bb20", "box", "bb44", "sr", "trendline")
    assert POSITION_WEIGHT_ROLES["box"] == "structural_envelope"
    assert POSITION_WEIGHT_ROLES["bb20"] == "primary_location_anchor"
    assert POSITION_WEIGHT_ROLES["bb44"] == "micro_tiebreak"


def test_energy_snapshot_marks_energy_middle_context_as_coordinate_heuristic():
    position = PositionVector(
        x_box=0.18,
        x_bb20=0.21,
        x_bb44=0.24,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=0.6,
        r_box_mid_hold=0.4,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.20,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.0,
        s_volatility=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    assert energy.metadata["energy_middle_context"] is True
    assert energy.metadata["energy_middle_context_source"] == "coordinate_heuristic"
    assert energy.metadata["upper_conflict_context"] is False
    assert energy.metadata["trend_pullback_buy_boost"] is True


def test_energy_snapshot_accepts_state_vector_v2_direct():
    position = PositionVector(
        x_box=-0.88,
        x_bb20=-0.54,
        x_bb44=-0.18,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.82,
        r_box_lower_bounce=0.74,
        metadata={},
    )
    state_v2 = StateVectorV2(
        wait_patience_gain=0.96,
        confirm_aggression_gain=1.05,
        metadata={
            "source_regime": "RANGE",
            "source_direction_policy": "BOTH",
            "source_noise": 0.14,
            "source_conflict": 0.02,
            "source_alignment": 0.25,
            "source_disparity": 0.18,
            "source_volatility": 0.12,
            "mapper_version": "state_vector_v2_test",
            "state_contract": "canonical_v3",
        },
    )
    energy = compute_energy_snapshot(position, response, state_v2)
    assert energy.buy_force > energy.sell_force
    assert energy.net_force > 0.0
    assert energy.metadata["state_input_mode"] == "state_vector_v2_direct"
    assert energy.metadata["state_contract"] == "canonical_v3"


def test_energy_snapshot_does_not_infer_conflict_alias_without_position_snapshot():
    position = PositionVector(
        x_box=0.58,
        x_bb20=-0.26,
        x_bb44=0.08,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.10,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.0,
        s_volatility=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    assert energy.metadata["energy_middle_context"] is False
    assert energy.metadata["upper_conflict_context"] is False
    assert energy.metadata["position_conflict_kind"] == ""
    assert energy.metadata["position_conflict_source"] == "none"
    assert energy.metadata["position_axis_values"]["x_box"] == position.x_box
    assert energy.metadata["position_axis_values"]["x_bb20"] == position.x_bb20


def test_energy_snapshot_uses_position_snapshot_for_box_bb20_conflict_aliases():
    position = PositionVector(
        x_box=0.58,
        x_bb20=-0.26,
        x_bb44=0.08,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.10,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.0,
        s_volatility=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    position_snapshot = summarize_position(position)
    energy = compute_energy_snapshot(position, response, state, position_snapshot=position_snapshot)
    assert energy.metadata["energy_middle_context"] is False
    assert energy.metadata["upper_conflict_context"] is True
    assert energy.metadata["trend_pullback_buy_boost"] is False
    assert energy.metadata["position_conflict_kind"] == "CONFLICT_BOX_UPPER_BB20_LOWER"
    assert energy.metadata["position_conflict_source"] == "position_snapshot"


def test_energy_snapshot_uses_position_snapshot_for_bb20_bb44_conflict_aliases():
    position = PositionVector(
        x_box=0.05,
        x_bb20=0.35,
        x_bb44=-0.22,
        metadata={"symbol": "BTCUSD", "box_state": "MID", "bb_state": "MID"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.10,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.0,
        s_volatility=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    position_snapshot = summarize_position(position)
    energy = compute_energy_snapshot(position, response, state, position_snapshot=position_snapshot)
    assert energy.metadata["position_primary_label"] == position_snapshot.interpretation.primary_label
    assert energy.metadata["position_conflict_kind"] == "CONFLICT_BB20_UPPER_BB44_LOWER"
    assert energy.metadata["position_conflict_axes"] == ["x_bb20", "x_bb44"]
    assert energy.metadata["position_conflict_dominance"] == "LOWER_DOMINANT_CONFLICT"
    assert energy.metadata["upper_conflict_context"] is True
    assert energy.metadata["position_conflict_confidence"] == position_snapshot.energy.position_conflict_score


def test_observe_confirm_routes_lower_rebound_to_buy_shadow():
    ctx = _build_ctx(
        current_open=99.8,
        current_high=100.7,
        current_low=89.95,
        current_close=100.6,
        previous_close=99.0,
        band_touch_tolerance=0.2,
        box_touch_tolerance=0.2,
        raw_scores={"wait_noise": 3.0, "wait_conflict": 0.0},
        current_disparity=97.2,
        current_volatility_ratio=1.05,
        ma_alignment="BULL",
    )
    position = build_position_vector(ctx)
    response = build_response_vector(ctx)
    state = build_state_vector(ctx)
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="lower_hold_buy", action="BUY")


def test_observe_confirm_routes_upper_reject_to_sell_shadow():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=105.0,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 106.2,
            "current_high": 110.1,
            "current_low": 103.8,
            "current_close": 104.0,
            "previous_close": 105.2,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
            "raw_scores": {"wait_noise": 4.0, "wait_conflict": 0.0},
            "current_disparity": 102.4,
            "current_volatility_ratio": 1.1,
            "ma_alignment": "BEAR",
        },
    )
    position = build_position_vector(ctx)
    response = build_response_vector(ctx)
    state = build_state_vector(ctx)
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_routes_upper_reject_to_sell_shadow_in_trend():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=105.0,
        market_mode="TREND",
        direction_policy="BOTH",
        box_state="ABOVE",
        bb_state="UPPER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 106.2,
            "current_high": 110.1,
            "current_low": 103.8,
            "current_close": 104.0,
            "previous_close": 105.2,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
            "raw_scores": {"wait_noise": 4.0, "wait_conflict": 0.0},
            "current_disparity": 102.4,
            "current_volatility_ratio": 1.1,
            "ma_alignment": "BEAR",
        },
    )
    position = build_position_vector(ctx)
    response = build_response_vector(ctx)
    state = build_state_vector(ctx)
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_routes_btc_failed_upper_break_to_sell_shadow():
    position = PositionVector(
        x_box=1.80,
        x_bb20=0.92,
        x_bb44=0.25,
        metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "UPPER_EDGE"},
    )
    response = ResponseVector(
        r_box_upper_break=1.0,
        r_bb20_upper_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.05, sell_force=0.96, net_force=-0.91)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_keeps_wait_when_upper_break_has_mid_hold_without_reject():
    position = PositionVector(
        x_box=1.30,
        x_bb20=0.14,
        x_bb44=0.14,
        metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=1.0,
        r_bb20_mid_reclaim=1.0,
        r_box_upper_break=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.22, sell_force=0.41, net_force=-0.19)
    routed = _route(position, response, state, energy)
    _assert_route(
        routed,
        archetype_id="",
        action="WAIT",
        side="",
        reason="middle_sr_anchor_required_observe",
    )
    assert routed.metadata["confidence_semantics_v2"]["wait_preserves_archetype_identity"] is True
    assert routed.metadata["confidence_semantics_v2"]["archetype_id_at_emit_time"] == ""


def test_observe_confirm_requires_nonnegative_bb20_for_upper_reject_sell():
    position = PositionVector(
        x_box=0.82,
        x_bb20=-0.20,
        x_bb44=0.05,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_box_upper_reject=1.0,
        r_bb20_mid_reject=0.5,
        r_candle_upper_reject=0.3,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.03, sell_force=0.33, net_force=-0.30)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", state="CONFLICT_OBSERVE")


def test_observe_confirm_keeps_failed_sell_reclaim_in_wait_when_box_is_middle_or_upper():
    position = PositionVector(
        x_box=0.80,
        x_bb20=-0.18,
        x_bb44=0.04,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=1.0,
        r_bb20_mid_reclaim=1.0,
        r_box_mid_hold=0.5,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.20,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.08, sell_force=0.04, net_force=0.04)
    routed = _route(position, response, state, energy)
    assert routed.action == "WAIT"


def test_observe_confirm_promotes_lower_dominant_conflict_to_buy_confirm():
    position = PositionVector(
        x_box=0.58,
        x_bb20=-0.22,
        x_bb44=-0.18,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=1.0,
        r_bb20_mid_reclaim=1.0,
        r_box_mid_hold=0.45,
        r_candle_lower_reject=0.30,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.10,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.15, sell_force=0.02, net_force=0.13)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="mid_reclaim_buy", action="BUY")


def test_observe_confirm_routes_upper_box_lower_bb20_conflict_to_wait():
    position = PositionVector(
        x_box=0.48,
        x_bb20=-0.34,
        x_bb44=-0.18,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.10,
        s_conflict=0.15,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.12, sell_force=0.11, net_force=0.01)
    routed = _route(position, response, state, energy)
    _assert_route(
        routed,
        archetype_id="",
        action="WAIT",
        state="CONFLICT_OBSERVE",
        reason="conflict_box_upper_bb20_lower_lower_dominant_observe",
    )


def test_observe_confirm_promotes_upper_box_lower_bb20_conflict_to_buy_when_lower_support_dominates():
    position = PositionVector(
        x_box=0.32,
        x_bb20=-0.45,
        x_bb44=-0.22,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.34,
        r_bb44_lower_hold=0.25,
        r_box_mid_hold=0.18,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.20,
        s_conflict=0.30,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.19, sell_force=0.09, net_force=0.10)
    routed = _route(position, response, state, energy)
    _assert_route(
        routed,
        archetype_id="lower_hold_buy",
        action="BUY",
        reason="conflict_box_upper_bb20_lower_lower_support_confirm",
    )


def test_observe_confirm_routes_lower_box_upper_bb20_conflict_to_wait():
    position = PositionVector(
        x_box=-0.42,
        x_bb20=0.28,
        x_bb44=0.14,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.12,
        s_conflict=0.10,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.10, sell_force=0.09, net_force=0.01)
    routed = _route(position, response, state, energy)
    _assert_route(
        routed,
        archetype_id="",
        action="WAIT",
        state="CONFLICT_OBSERVE",
        reason="conflict_box_lower_bb20_upper_upper_dominant_observe",
    )


def test_observe_confirm_promotes_btc_lower_reclaim_to_buy_even_if_sell_only_when_support_is_strong():
    position = PositionVector(
        x_box=0.12,
        x_bb20=-0.62,
        x_bb44=-0.28,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=0.65,
        r_bb20_mid_reclaim=1.0,
        r_box_mid_hold=0.45,
        r_bb44_lower_hold=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.12,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.03, sell_force=0.05, net_force=-0.02)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_observe_confirm_promotes_middle_box_lower_edge_to_buy_when_lower_response_is_strong():
    position = PositionVector(
        x_box=0.10,
        x_bb20=-0.72,
        x_bb44=-0.26,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.42,
        r_bb20_mid_hold=0.36,
        r_box_mid_hold=0.22,
        r_bb44_lower_hold=0.28,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.10,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.21, sell_force=0.06, net_force=0.15)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_band_response_strengthens_lower_hold_on_proximity_without_exact_touch():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=91.8,
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 91.2,
            "current_high": 92.3,
            "current_low": 90.7,
            "current_close": 92.0,
            "previous_close": 91.1,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
        },
    )
    response = build_response_vector(ctx)
    assert response.r_bb20_lower_hold > 0.0
    assert response.r_bb44_lower_hold > 0.0


def test_structure_response_damps_mid_reject_on_lower_edge():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=94.0,
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 95.2,
            "current_high": 100.1,
            "current_low": 90.4,
            "current_close": 94.1,
            "previous_close": 95.3,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
        },
    )
    response = build_response_vector(ctx)
    assert response.r_box_mid_reject < 0.3


def test_observe_confirm_lower_edge_promotes_buy_with_lower_hold_bias_when_box_is_lower():
    position = PositionVector(
        x_box=-0.22,
        x_bb20=-0.86,
        x_bb44=-0.24,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.55,
        r_bb20_mid_hold=0.30,
        r_box_mid_hold=0.20,
        r_box_mid_reject=0.05,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.10,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.06, sell_force=0.055, net_force=0.005)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="lower_hold_buy", action="BUY", reason="lower_rebound_confirm")


def test_observe_confirm_btc_uses_lower_confirm_floor():
    position = PositionVector(
        x_box=0.82,
        x_bb20=0.86,
        x_bb44=0.48,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "UPPER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_upper_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.03, sell_force=0.22, net_force=-0.19)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_non_btc_uses_unified_confirm_floor():
    position = PositionVector(
        x_box=0.82,
        x_bb20=0.86,
        x_bb44=0.48,
        metadata={"symbol": "XAUUSD", "box_state": "UPPER", "bb_state": "UPPER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_upper_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "XAUUSD"},
    )
    energy = EnergySnapshot(buy_force=0.03, sell_force=0.22, net_force=-0.19)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_keeps_strong_upper_continuation_as_observe_without_confirmed_reversal():
    position = PositionVector(
        x_box=1.25,
        x_bb20=0.86,
        x_bb44=0.30,
        x_ma20=1.10,
        x_ma60=1.25,
        metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "UPPER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_upper_break=1.0,
        r_bb20_upper_reject=0.70,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.05, sell_force=0.30, net_force=-0.25)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL", side="SELL", reason="upper_reject_mixed_confirm")


def test_observe_confirm_allows_strong_upper_continuation_sell_after_confirmed_reversal():
    position = PositionVector(
        x_box=1.25,
        x_bb20=0.86,
        x_bb44=0.30,
        x_ma20=1.10,
        x_ma60=1.25,
        metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "UPPER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_upper_reject=0.70,
        r_bb20_mid_lose=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.05, sell_force=0.30, net_force=-0.25)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="upper_reject_sell", action="SELL")


def test_observe_confirm_keeps_strong_lower_continuation_as_observe_without_confirmed_rebound():
    position = PositionVector(
        x_box=-1.25,
        x_bb20=-0.86,
        x_bb44=-0.30,
        x_ma20=-1.10,
        x_ma60=-1.25,
        metadata={"symbol": "BTCUSD", "box_state": "BELOW", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.70,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.30, sell_force=0.05, net_force=0.25)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="lower_hold_buy", action="WAIT", side="BUY", reason="lower_edge_observe")


def test_observe_confirm_allows_strong_lower_continuation_buy_after_confirmed_rebound():
    position = PositionVector(
        x_box=-1.25,
        x_bb20=-0.86,
        x_bb44=-0.30,
        x_ma20=-1.10,
        x_ma60=-1.25,
        metadata={"symbol": "BTCUSD", "box_state": "BELOW", "bb_state": "LOWER_EDGE"},
    )
    response = ResponseVector(
        r_bb20_lower_hold=0.70,
        r_bb20_mid_reclaim=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BOTH",
        s_noise=0.0,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.30, sell_force=0.05, net_force=0.25)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="lower_hold_buy", action="BUY")


def test_observe_confirm_routes_btc_mid_reclaim_to_buy_shadow():
    position = PositionVector(
        x_box=0.12,
        x_bb20=0.05,
        x_bb44=-0.10,
        x_sr=-0.35,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_reclaim=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.045, sell_force=0.009, net_force=0.036)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="mid_reclaim_buy", action="BUY")


def test_observe_confirm_routes_xau_mid_reclaim_to_buy_shadow():
    position = PositionVector(
        x_box=0.12,
        x_bb20=0.05,
        x_bb44=-0.10,
        x_sr=-0.35,
        metadata={"symbol": "XAUUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_reclaim=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "XAUUSD"},
    )
    energy = EnergySnapshot(buy_force=0.045, sell_force=0.009, net_force=0.036)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="mid_reclaim_buy", action="BUY")


def test_observe_confirm_routes_btc_mid_lose_to_sell_shadow():
    position = PositionVector(
        x_box=-0.08,
        x_bb20=-0.04,
        x_bb44=0.08,
        x_sr=0.30,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_lose=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.010, sell_force=0.048, net_force=-0.038)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_observe_confirm_does_not_flip_to_lower_when_box_and_bb20_are_upper():
    position = PositionVector(
        x_box=1.20,
        x_bb20=0.24,
        x_bb44=-0.36,
        metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_box_upper_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.05, sell_force=0.48, net_force=-0.43)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="outer_band_reversal_support_required_observe")


def test_observe_confirm_does_not_flip_to_upper_when_box_and_bb20_are_lower():
    position = PositionVector(
        x_box=-1.20,
        x_bb20=-0.24,
        x_bb44=0.36,
        metadata={"symbol": "BTCUSD", "box_state": "BELOW", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_box_lower_bounce=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.48, sell_force=0.05, net_force=0.43)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="outer_band_reversal_support_required_observe")


def test_observe_confirm_does_not_emit_lower_state_when_box_context_is_upper():
    position = PositionVector(
        x_box=0.32,
        x_bb20=-0.55,
        x_bb44=-0.35,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "UNKNOWN"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.12, sell_force=0.33, net_force=-0.21)
    routed = _route(position, response, state, energy)
    assert not routed.archetype_id.startswith("LOWER_")


def test_observe_confirm_does_not_emit_upper_state_when_box_context_is_lower():
    position = PositionVector(
        x_box=-0.32,
        x_bb20=0.55,
        x_bb44=0.35,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "UNKNOWN"},
    )
    response = ResponseVector(metadata={})
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.33, sell_force=0.12, net_force=0.21)
    routed = _route(position, response, state, energy)
    assert not routed.archetype_id.startswith("UPPER_")


def test_observe_confirm_routes_btc_trend_pullback_buy_confirm():
    position = PositionVector(
        x_box=0.18,
        x_bb20=0.16,
        x_bb44=0.10,
        x_sr=-0.12,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_reclaim=1.0,
        r_candle_lower_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.18,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.09, sell_force=0.03, net_force=0.06)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_observe_confirm_routes_btc_trend_pullback_sell_confirm():
    position = PositionVector(
        x_box=-0.14,
        x_bb20=-0.12,
        x_bb44=-0.08,
        x_sr=0.15,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_lose=1.0,
        r_candle_upper_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.18,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.02, sell_force=0.08, net_force=-0.06)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_observe_confirm_routes_btc_trend_pullback_buy_confirm_from_mid_hold():
    position = PositionVector(
        x_box=0.20,
        x_bb20=0.18,
        x_bb44=0.12,
        x_sr=-0.08,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=1.0,
        r_box_mid_hold=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.10,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = EnergySnapshot(buy_force=0.08, sell_force=0.02, net_force=0.06)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="", action="WAIT", reason="middle_sr_anchor_required_observe")


def test_energy_snapshot_boosts_trend_pullback_buy_force():
    position = PositionVector(
        x_box=0.32,
        x_bb20=0.31,
        x_bb44=0.29,
        x_sr=-0.26,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "UNKNOWN"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=0.6,
        r_box_mid_hold=0.5,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.05,
        s_volatility=0.72,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    assert energy.metadata["trend_pullback_buy_boost"] is True
    assert energy.buy_force > energy.sell_force


def test_energy_snapshot_boosts_nas_trend_pullback_buy_force():
    position = PositionVector(
        x_box=0.32,
        x_bb20=0.31,
        x_bb44=0.29,
        x_sr=-0.26,
        metadata={"symbol": "NAS100", "box_state": "MIDDLE", "bb_state": "UNKNOWN"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=0.6,
        r_box_mid_hold=0.5,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.05,
        s_volatility=0.72,
        metadata={"symbol": "NAS100"},
    )
    energy = compute_energy_snapshot(position, response, state)
    assert energy.metadata["trend_pullback_buy_boost"] is True
    assert energy.buy_force > energy.sell_force


def test_observe_confirm_routes_btc_trend_pullback_buy_confirm_with_small_advantage():
    position = PositionVector(
        x_box=0.32,
        x_bb20=0.31,
        x_bb44=0.29,
        x_sr=-0.26,
        metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "UNKNOWN"},
    )
    response = ResponseVector(
        r_bb20_mid_hold=0.38,
        r_box_mid_hold=0.35,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        s_alignment=0.0,
        s_disparity=0.05,
        s_volatility=0.72,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    _assert_route(routed, archetype_id="mid_reclaim_buy", action="BUY")


def test_observe_confirm_does_not_route_upper_box_into_lower_state():
    position = PositionVector(
        x_box=0.72,
        x_bb20=-0.24,
        x_bb44=-0.01,
        metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_box_mid_hold=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    assert not routed.archetype_id.startswith("LOWER_")
    _assert_route(routed, archetype_id="", action="WAIT", state="CONFLICT_OBSERVE", side="")


def test_observe_confirm_does_not_route_lower_box_into_upper_state():
    position = PositionVector(
        x_box=-0.74,
        x_bb20=0.26,
        x_bb44=0.02,
        metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_box_mid_reject=1.0,
        metadata={},
    )
    state = StateVector(
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        s_noise=0.56,
        s_conflict=0.0,
        metadata={"symbol": "BTCUSD"},
    )
    energy = compute_energy_snapshot(position, response, state)
    routed = _route(position, response, state, energy)
    assert not routed.archetype_id.startswith("UPPER_")
    _assert_route(routed, archetype_id="", action="WAIT", state="CONFLICT_OBSERVE", side="")

