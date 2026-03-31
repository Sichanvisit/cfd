import copy

import pytest

import backend.trading.engine.core.observe_confirm_router as observe_router
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EnergySnapshot,
    ObserveConfirmSnapshot,
    PositionVector,
    ResponseVector,
    StateVector,
    StateVectorV2,
    TradeManagementForecast,
    TransitionForecast,
)
from backend.trading.engine.core.observe_confirm_router import (
    _apply_forecast_modulation,
    _confirm_floor,
    _probe_support_ready,
    route_observe_confirm,
)
from backend.trading.engine.position import summarize_position


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


def _deep_update(target: dict, updates: dict) -> dict:
    for key, value in dict(updates or {}).items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def _override_router_policy(monkeypatch, *, readiness=None, probe=None):
    policy = copy.deepcopy(observe_router._COMMON_EXPRESSION_POLICY_V1)
    if readiness:
        policy["readiness"] = {
            **policy.get("readiness", {}),
            **readiness,
        }
    if probe:
        policy["probe"] = {
            **policy.get("probe", {}),
            **probe,
        }
    monkeypatch.setattr(observe_router, "_COMMON_EXPRESSION_POLICY_V1", policy)


def _override_symbol_router_policy(monkeypatch, updates: dict):
    policy = copy.deepcopy(observe_router._SYMBOL_OVERRIDE_POLICY_V1)
    _deep_update(policy, updates)
    monkeypatch.setattr(observe_router, "_SYMBOL_OVERRIDE_POLICY_V1", policy)


def test_confirm_floor_respects_policy_override(monkeypatch):
    _override_router_policy(
        monkeypatch,
        readiness={
            "confirm_floor_by_state": {
                **observe_router._COMMON_EXPRESSION_POLICY_V1["readiness"]["confirm_floor_by_state"],
                "LOWER_REBOUND_CONFIRM": 0.27,
            }
        },
    )

    assert _confirm_floor("BTCUSD", "LOWER_REBOUND_CONFIRM") == pytest.approx(0.27)


def test_probe_support_ready_respects_policy_default_floor_mult(monkeypatch):
    assert _probe_support_ready(
        candidate_support=0.11,
        opposing_support=0.01,
        floor=0.20,
        advantage=0.0,
    ) is False

    _override_router_policy(
        monkeypatch,
        probe={
            "default_floor_mult": 0.50,
        },
    )

    assert _probe_support_ready(
        candidate_support=0.11,
        opposing_support=0.01,
        floor=0.20,
        advantage=0.0,
    ) is True


def test_default_symbol_override_policy_keeps_nas_clean_confirm_relief_active():
    clean_confirm = observe_router._SYMBOL_OVERRIDE_POLICY_V1["symbols"]["NAS100"]["router"]["probe"]["clean_confirm"]
    middle_anchor_relief = observe_router._SYMBOL_OVERRIDE_POLICY_V1["symbols"]["NAS100"]["router"]["relief"]["clean_confirm_middle_anchor"]

    assert clean_confirm["enabled"] is True
    assert clean_confirm["floor_mult"] == pytest.approx(0.74)
    assert clean_confirm["advantage_mult"] == pytest.approx(0.26)
    assert clean_confirm["support_tolerance"] == pytest.approx(0.015)
    assert middle_anchor_relief["enabled"] is True
    assert middle_anchor_relief["support_min"] == pytest.approx(0.34)
    assert middle_anchor_relief["pair_gap_min"] == pytest.approx(0.10)
    assert middle_anchor_relief["confirm_fake_gap_min"] == pytest.approx(-0.08)
    assert middle_anchor_relief["wait_confirm_gap_min"] == pytest.approx(-0.05)


def _route(position: PositionVector, response: ResponseVector, state: StateVector | StateVectorV2, energy: EnergySnapshot, **kwargs):
    return route_observe_confirm(
        position,
        response,
        state,
        summarize_position(position),
        **kwargs,
    )


def _lower_hold_buy_case():
    return (
        PositionVector(
            x_box=-1.20,
            x_bb20=-0.72,
            x_bb44=-0.38,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "LOWER_EDGE"},
        ),
        ResponseVector(
            r_bb20_lower_hold=1.0,
            r_box_lower_bounce=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.12,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.64, sell_force=0.12, net_force=0.52),
    )


def _lower_hold_buy_case_v2():
    position, response, _state, energy = _lower_hold_buy_case()
    state_v2 = StateVectorV2(
        wait_patience_gain=0.98,
        confirm_aggression_gain=1.04,
        metadata={
            "symbol": "BTCUSD",
            "source_regime": "RANGE",
            "source_direction_policy": "BOTH",
            "source_noise": 0.12,
            "source_conflict": 0.0,
            "source_alignment": 0.0,
            "source_disparity": 0.0,
            "source_volatility": 0.0,
            "regime_state_label": "RANGE_SWING",
            "session_regime_state": "SESSION_EDGE_ROTATION",
            "topdown_confluence_state": "WEAK_CONFLUENCE",
            "execution_friction_state": "MEDIUM_FRICTION",
            "patience_state_label": "WAIT_FAVOR",
        },
    )
    return position, response, state_v2, energy


def _lower_rebound_probe_case():
    return (
        PositionVector(
            x_box=-1.08,
            x_bb20=-0.66,
            x_bb44=-0.20,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "LOWER_EDGE"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.26,
            r_bb20_mid_reclaim=0.18,
            r_box_lower_bounce=0.22,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.08, sell_force=0.04, net_force=0.04),
    )


def _upper_reject_sell_case():
    return (
        PositionVector(
            x_box=1.20,
            x_bb20=0.86,
            x_bb44=0.30,
            metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_bb20_upper_reject=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.0,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.03, sell_force=0.30, net_force=-0.27),
    )


def _upper_reject_probe_case():
    return (
        PositionVector(
            x_box=1.08,
            x_bb20=0.66,
            x_bb44=0.20,
            metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.26,
            r_box_upper_reject=0.18,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.04, sell_force=0.08, net_force=-0.04),
    )


def _xau_upper_reject_structural_probe_case():
    return (
        PositionVector(
            x_box=1.04,
            x_bb20=0.52,
            x_bb44=0.18,
            metadata={"symbol": "XAUUSD", "box_state": "UPPER", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.14,
            r_box_upper_reject=0.10,
            r_sr_resistance_reject=0.22,
            r_trend_resistance_reject_m15=0.16,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.06,
            s_conflict=0.0,
            metadata={"symbol": "XAUUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.09, net_force=-0.04),
    )


def _xau_second_support_probe_case():
    return (
        PositionVector(
            x_box=-0.78,
            x_bb20=-0.06,
            x_bb44=0.04,
            x_sr=-0.41,
            metadata={"symbol": "XAUUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.24,
            r_bb20_mid_reclaim=0.20,
            r_box_lower_bounce=0.42,
            r_sr_support_hold=0.26,
            r_trend_support_hold_m15=0.18,
            metadata={},
        ),
        StateVectorV2(
            wait_patience_gain=1.02,
            confirm_aggression_gain=1.00,
            metadata={
                "symbol": "XAUUSD",
                "source_regime": "RANGE",
                "source_direction_policy": "BOTH",
                "source_noise": 0.08,
                "source_conflict": 0.0,
                "source_alignment": 0.0,
                "source_disparity": 0.0,
                "source_volatility": 0.0,
                "regime_state_label": "RANGE_SWING",
                "session_regime_state": "SESSION_EDGE_ROTATION",
                "topdown_confluence_state": "WEAK_CONFLUENCE",
                "execution_friction_state": "MEDIUM_FRICTION",
                "patience_state_label": "WAIT_FAVOR",
            },
        ),
        EnergySnapshot(buy_force=0.11, sell_force=0.05, net_force=0.06),
    )


def _btc_structural_lower_probe_case():
    return (
        PositionVector(
            x_box=-0.82,
            x_bb20=-0.06,
            x_bb44=0.03,
            x_sr=-0.38,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.26,
            r_bb20_mid_reclaim=0.18,
            r_box_lower_bounce=0.40,
            r_sr_support_hold=0.24,
            r_trend_support_hold_m15=0.16,
            metadata={},
        ),
        StateVectorV2(
            wait_patience_gain=1.04,
            confirm_aggression_gain=0.98,
            metadata={
                "symbol": "BTCUSD",
                "source_regime": "RANGE",
                "source_direction_policy": "BOTH",
                "source_noise": 0.10,
                "source_conflict": 0.0,
                "source_alignment": 0.0,
                "source_disparity": 0.0,
                "source_volatility": 0.0,
                "regime_state_label": "RANGE_SWING",
                "session_regime_state": "SESSION_EDGE_ROTATION",
                "topdown_confluence_state": "WEAK_CONFLUENCE",
                "execution_friction_state": "MEDIUM_FRICTION",
                "patience_state_label": "WAIT_FAVOR",
            },
        ),
        EnergySnapshot(buy_force=0.10, sell_force=0.04, net_force=0.06),
    )


def _btc_middle_lower_edge_context_probe_case():
    return (
        PositionVector(
            x_box=-0.31,
            x_bb20=-0.62,
            x_bb44=0.142,
            x_sr=-0.48,
            metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "LOWER_EDGE"},
        ),
        ResponseVector(
            r_bb20_mid_reclaim=0.239,
            r_box_lower_bounce=0.18,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.11, sell_force=0.02, net_force=0.09),
    )


def _btc_middle_lower_edge_context_probe_blocked_case():
    position, response, state, energy = _btc_middle_lower_edge_context_probe_case()
    blocked_position = PositionVector(
        x_box=position.x_box,
        x_bb20=position.x_bb20,
        x_bb44=0.24,
        x_sr=position.x_sr,
        metadata=dict(position.metadata or {}),
    )
    return blocked_position, response, state, energy


def _btc_midline_rebound_sell_watch_case():
    return (
        PositionVector(
            x_box=-0.54,
            x_bb20=0.03,
            x_bb44=0.06,
            x_sr=-0.12,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.18,
            r_bb20_mid_reclaim=0.16,
            r_box_lower_bounce=0.22,
            r_bb20_upper_reject=0.12,
            r_bb20_mid_lose=0.08,
            r_box_mid_reject=0.06,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.06,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.08, net_force=-0.03),
    )


def _btc_midline_rebound_neutral_wait_case():
    return (
        PositionVector(
            x_box=-0.58,
            x_bb20=0.02,
            x_bb44=0.01,
            x_sr=-0.16,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.18,
            r_bb20_mid_reclaim=0.14,
            r_box_lower_bounce=0.20,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.06,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.05, net_force=0.0),
    )


def _lower_upper_conflict_upper_reject_case():
    return (
        PositionVector(
            x_box=-0.52,
            x_bb20=0.68,
            x_bb44=-0.12,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "UPPER"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.20,
            r_box_upper_reject=0.16,
            r_bb20_mid_reject=0.08,
            r_box_mid_reject=0.06,
            r_sr_resistance_reject=0.12,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.08, net_force=-0.03),
    )


def _lower_upper_conflict_balanced_upper_reject_watch_case():
    return (
        PositionVector(
            x_box=-0.50,
            x_bb20=0.47,
            x_bb44=0.03,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_box_lower_bounce=0.18,
            r_bb20_mid_reclaim=0.16,
            r_bb20_upper_reject=0.10,
            r_box_upper_reject=0.08,
            r_bb20_mid_reject=0.06,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.08, net_force=-0.03),
    )


def _xau_lower_upper_conflict_local_upper_reject_case():
    return (
        PositionVector(
            x_box=-0.44,
            x_bb20=0.06,
            x_bb44=-0.04,
            metadata={"symbol": "XAUUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.10,
            r_box_upper_reject=0.08,
            r_sr_resistance_reject=0.16,
            r_trend_resistance_reject_m15=0.12,
            r_bb20_mid_lose=0.08,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "XAUUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.09, net_force=-0.04),
    )


def _upper_break_buy_case():
    return (
        PositionVector(
            x_box=1.20,
            x_bb20=0.86,
            x_bb44=0.30,
            metadata={"symbol": "BTCUSD", "box_state": "ABOVE", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_bb20_upper_break=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="TREND",
            direction_policy="BOTH",
            s_noise=0.0,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.40, sell_force=0.05, net_force=0.35),
    )


def _upper_edge_mid_buy_without_break_case():
    return (
        PositionVector(
            x_box=1.05,
            x_bb20=0.72,
            x_bb44=0.22,
            metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "UPPER_EDGE"},
        ),
        ResponseVector(
            r_bb20_mid_hold=0.42,
            r_bb20_mid_reclaim=0.38,
            r_box_mid_hold=0.22,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.24, sell_force=0.09, net_force=0.15),
    )


def _lower_break_sell_case():
    return (
        PositionVector(
            x_box=-1.20,
            x_bb20=-0.86,
            x_bb44=-0.30,
            metadata={"symbol": "BTCUSD", "box_state": "BELOW", "bb_state": "LOWER_EDGE"},
        ),
        ResponseVector(
            r_bb20_lower_break=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="TREND",
            direction_policy="BOTH",
            s_noise=0.0,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.40, net_force=-0.35),
    )


def _mid_reclaim_buy_case():
    return (
        PositionVector(
            x_box=0.12,
            x_bb20=0.05,
            x_bb44=-0.10,
            x_sr=-0.35,
            metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_mid_reclaim=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.20,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.08, sell_force=0.01, net_force=0.07),
    )


def _mid_lose_sell_case():
    return (
        PositionVector(
            x_box=-0.08,
            x_bb20=-0.04,
            x_bb44=0.08,
            x_sr=0.38,
            metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_mid_lose=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.20,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.01, sell_force=0.08, net_force=-0.07),
    )


def _mid_reclaim_buy_without_sr_case():
    return (
        PositionVector(
            x_box=0.10,
            x_bb20=0.04,
            x_bb44=-0.08,
            x_sr=-0.12,
            metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_mid_reclaim=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.20,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.08, sell_force=0.01, net_force=0.07),
    )


def _mid_reclaim_buy_edge_rotation_case():
    return (
        PositionVector(
            x_box=0.10,
            x_bb20=0.04,
            x_bb44=-0.08,
            x_sr=-0.12,
            metadata={"symbol": "BTCUSD", "box_state": "MIDDLE", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_mid_reclaim=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.20,
            s_conflict=0.0,
            metadata={
                "symbol": "BTCUSD",
                "state_vector_v2": {
                    "metadata": {
                        "regime_state_label": "CHOP_NOISE",
                        "session_regime_state": "SESSION_EDGE_ROTATION",
                        "topdown_confluence_state": "WEAK_CONFLUENCE",
                        "execution_friction_state": "MEDIUM_FRICTION",
                        "patience_state_label": "WAIT_FAVOR",
                    }
                },
            },
        ),
        EnergySnapshot(buy_force=0.08, sell_force=0.01, net_force=0.07),
    )


def _mixed_lower_buy_without_sr_case():
    return (
        PositionVector(
            x_box=-0.72,
            x_bb20=-0.08,
            x_bb44=0.20,
            x_sr=-0.29,
            metadata={"symbol": "XAUUSD", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.57,
            r_box_lower_bounce=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "XAUUSD"},
        ),
        EnergySnapshot(buy_force=0.31, sell_force=0.08, net_force=0.23),
    )


def _nas_clean_confirm_probe_without_sr_case(*, strong: bool):
    response_kwargs = (
        {
            "r_bb20_lower_hold": 0.10,
            "r_bb20_mid_reclaim": 0.14,
            "r_box_lower_bounce": 0.16,
        }
        if strong
        else {
            "r_bb20_lower_hold": 0.08,
            "r_bb20_mid_reclaim": 0.08,
            "r_box_lower_bounce": 0.08,
        }
    )
    return (
        PositionVector(
            x_box=-0.62,
            x_bb20=-0.15,
            x_bb44=-0.29,
            x_sr=0.20,
            metadata={"symbol": "NAS100", "box_state": "LOWER", "bb_state": "MID"},
        ),
        ResponseVector(
            metadata={},
            **response_kwargs,
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "NAS100"},
        ),
        EnergySnapshot(buy_force=0.11, sell_force=0.05, net_force=0.06),
    )


def _nas_clean_confirm_upper_probe_without_sr_case():
    return (
        PositionVector(
            x_box=0.62,
            x_bb20=0.15,
            x_bb44=0.29,
            x_sr=-0.20,
            metadata={"symbol": "NAS100", "box_state": "UPPER", "bb_state": "MID"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.10,
            r_bb20_mid_reject=0.14,
            r_box_upper_reject=0.16,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.08,
            s_conflict=0.0,
            metadata={"symbol": "NAS100"},
        ),
        EnergySnapshot(buy_force=0.05, sell_force=0.11, net_force=-0.06),
    )


def _lower_hold_buy_without_outer_band_support_case():
    return (
        PositionVector(
            x_box=-0.96,
            x_bb20=-0.42,
            x_bb44=-0.05,
            x_sr=-0.42,
            metadata={"symbol": "XAUUSD", "box_state": "LOWER", "bb_state": "UNKNOWN"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.54,
            r_bb44_lower_hold=0.02,
            r_box_lower_bounce=0.96,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "XAUUSD"},
        ),
        EnergySnapshot(buy_force=0.40, sell_force=0.10, net_force=0.30),
    )


def _lower_hold_buy_with_sr_only_case():
    return (
        PositionVector(
            x_box=-1.02,
            x_bb20=-0.44,
            x_bb44=-0.05,
            x_sr=-0.72,
            metadata={"symbol": "NAS100", "box_state": "BELOW", "bb_state": "LOWER"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.56,
            r_box_lower_bounce=0.35,
            r_bb44_lower_hold=0.0,
            metadata={},
        ),
        StateVector(
            market_mode="TREND",
            direction_policy="SELL_ONLY",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "NAS100"},
        ),
        EnergySnapshot(buy_force=0.18, sell_force=0.22, net_force=-0.04),
    )


def _structural_lower_break_override_case():
    return (
        PositionVector(
            x_box=-1.24,
            x_bb20=-0.66,
            x_bb44=-0.04,
            metadata={"symbol": "BTCUSD", "box_state": "BELOW", "bb_state": "LOWER"},
        ),
        ResponseVector(
            r_bb20_lower_hold=0.12,
            r_box_lower_break=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.28, sell_force=0.22, net_force=0.06),
    )


def _structural_lower_break_with_strong_hold_case():
    return (
        PositionVector(
            x_box=-1.43,
            x_bb20=-0.46,
            x_bb44=-0.15,
            x_sr=-0.44,
            metadata={"symbol": "XAUUSD", "box_state": "BELOW", "bb_state": "UNKNOWN"},
        ),
        ResponseVector(
            r_box_lower_break=1.0,
            r_bb20_lower_hold=0.58,
            r_candle_lower_reject=0.62,
            metadata={},
        ),
        StateVector(
            market_mode="NORMAL",
            direction_policy="BOTH",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "XAUUSD"},
        ),
        EnergySnapshot(buy_force=0.30, sell_force=0.20, net_force=0.10),
    )


def _mixed_upper_reject_override_case():
    return (
        PositionVector(
            x_box=-0.84,
            x_bb20=0.01,
            x_bb44=0.27,
            x_sr=-0.61,
            metadata={"symbol": "BTCUSD", "box_state": "LOWER_EDGE", "bb_state": "MIDDLE"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.70,
            r_box_lower_bounce=1.0,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.18,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.32, sell_force=0.18, net_force=0.14),
    )


def _upper_reclaim_strength_case():
    return (
        PositionVector(
            x_box=0.96,
            x_bb20=0.18,
            x_bb44=0.08,
            x_sr=0.22,
            metadata={"symbol": "BTCUSD", "box_state": "UPPER", "bb_state": "MIDDLE"},
        ),
        ResponseVector(
            r_bb20_upper_reject=0.22,
            r_bb20_mid_reclaim=0.64,
            r_bb20_mid_hold=0.52,
            metadata={},
        ),
        StateVector(
            market_mode="RANGE",
            direction_policy="BOTH",
            s_noise=0.10,
            s_conflict=0.0,
            metadata={"symbol": "BTCUSD"},
        ),
        EnergySnapshot(buy_force=0.28, sell_force=0.16, net_force=0.12),
    )


def test_observe_confirm_router_v2_is_deterministic_for_same_semantic_bundle():
    position, response, state, energy = _lower_hold_buy_case()

    first = _route(position, response, state, energy)
    second = _route(position, response, state, energy)

    assert first.to_dict() == second.to_dict()


def test_observe_confirm_router_v2_routes_from_semantic_bundle_only():
    position, response, state, energy = _lower_hold_buy_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFIRM"
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["routing_policy_v2"]["available_inputs"]["evidence_vector_v1"] is False
    assert routed.metadata["routing_policy_v2"]["available_inputs"]["transition_forecast_v1"] is False


def test_observe_confirm_router_v2_accepts_state_vector_v2_direct():
    position, response, state, energy = _lower_hold_buy_case_v2()

    routed = _route(position, response, state, energy)

    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["semantic_readiness_bridge_v1"]["components"]["state_execution"]["confirm_gain"] > 1.0
    assert routed.metadata["semantic_readiness_bridge_v1"]["components"]["state_source"]["input_mode"] == "state_vector_v2_direct"


def test_observe_confirm_router_v2_keeps_state_and_archetype_separate():
    position, response, state, energy = _upper_reject_sell_case()

    routed = _route(position, response, state, energy)

    assert routed.state in {"OBSERVE", "CONFIRM", "CONFLICT_OBSERVE", "NO_TRADE", "INVALIDATED"}
    assert routed.archetype_id in {
        "upper_reject_sell",
        "upper_break_buy",
        "lower_hold_buy",
        "lower_break_sell",
        "mid_reclaim_buy",
        "mid_lose_sell",
    }
    assert routed.state != routed.archetype_id
    assert routed.state != "UPPER_REJECT_CONFIRM"


def test_observe_confirm_router_v2_defers_upper_reject_sell_when_reclaim_strength_dominates():
    position, response, state, energy = _upper_reclaim_strength_case()

    routed = _route(position, response, state, energy)

    assert routed.action != "SELL"
    assert routed.reason in {"upper_reclaim_strength_confirm", "upper_reclaim_strength_observe", "middle_sr_anchor_required_observe"}
    assert routed.metadata["raw_contributions"]["middle_sr_anchor_guard_v1"]["side"] == "BUY"


def test_observe_confirm_router_v2_keeps_upper_edge_buy_wait_disabled_without_upper_break_branch():
    position, response, state, energy = _upper_edge_mid_buy_without_break_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "SELL"
    assert routed.reason == "upper_edge_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["edge_pair_law_v1"]["context_label"] == "UPPER_EDGE"
    assert routed.metadata["edge_pair_law_v1"]["winner_side"] == "BALANCED"
    assert routed.metadata["edge_pair_law_v1"]["winner_clear"] is False


def test_observe_confirm_router_v2_forecast_can_demote_confirm_without_renaming_archetype():
    position, response, state, energy = _lower_hold_buy_case()

    baseline = _route(position, response, state, energy)
    routed = _route(
        position,
        response,
        state,
        energy,
        transition_forecast_v1=TransitionForecast(
            p_buy_confirm=0.04,
            p_sell_confirm=0.11,
            p_false_break=0.91,
            p_reversal_success=0.18,
            p_continuation_success=0.09,
        ),
        trade_management_forecast_v1=TradeManagementForecast(
            p_continue_favor=0.11,
            p_fail_now=0.74,
            p_recover_after_pullback=0.08,
            p_reach_tp1=0.10,
            p_opposite_edge_reach=0.37,
            p_better_reentry_if_cut=0.58,
        ),
        forecast_gap_metrics_v1={"transition_side_separation": 0.03},
    )

    assert baseline.state == "CONFIRM"
    assert baseline.action == "BUY"
    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "BUY"
    assert routed.archetype_id == baseline.archetype_id == "lower_hold_buy"
    assert routed.invalidation_id == baseline.invalidation_id == "lower_support_fail"
    assert routed.management_profile_id == baseline.management_profile_id == "support_hold_profile"
    assert routed.metadata["blocked_reason"] == "buy_forecast_suppressed_confirm"
    assert routed.metadata["forecast_assist_v1"]["present"] is True
    assert routed.metadata["forecast_assist_v1"]["decision_hint"] == "OBSERVE_FAVOR"
    assert routed.metadata["forecast_assist_v1"]["wait_confirm_gap"] <= 0.0


def test_observe_confirm_router_v2_records_forecast_assist_when_confirm_bias_is_clear():
    position, response, state, energy = _lower_hold_buy_case()

    routed = _route(
        position,
        response,
        state,
        energy,
        transition_forecast_v1=TransitionForecast(
            p_buy_confirm=0.61,
            p_sell_confirm=0.08,
            p_false_break=0.18,
            p_reversal_success=0.62,
            p_continuation_success=0.29,
        ),
        trade_management_forecast_v1=TradeManagementForecast(
            p_continue_favor=0.64,
            p_fail_now=0.16,
            p_recover_after_pullback=0.42,
            p_reach_tp1=0.38,
            p_opposite_edge_reach=0.12,
            p_better_reentry_if_cut=0.08,
        ),
        forecast_gap_metrics_v1={
            "transition_side_separation": 0.26,
            "transition_confirm_fake_gap": 0.21,
            "wait_confirm_gap": 0.12,
            "management_continue_fail_gap": 0.19,
        },
    )

    assert routed.action == "BUY"
    assert routed.metadata["forecast_assist_v1"]["present"] is True
    assert routed.metadata["forecast_assist_v1"]["decision_hint"] == "CONFIRM_FAVOR"
    assert routed.metadata["forecast_assist_v1"]["confirm_fake_gap"] == pytest.approx(0.21)


def test_observe_confirm_router_v2_keeps_clean_upper_reject_confirm_when_forecast_relief_applies():
    position, response, state, energy = _upper_reject_sell_case()

    routed = _route(
        position,
        response,
        state,
        energy,
        transition_forecast_v1=TransitionForecast(
            p_buy_confirm=0.08,
            p_sell_confirm=0.16,
            p_false_break=0.62,
            p_reversal_success=0.31,
            p_continuation_success=0.11,
        ),
        trade_management_forecast_v1=TradeManagementForecast(
            p_continue_favor=0.18,
            p_fail_now=0.31,
            p_recover_after_pullback=0.12,
            p_reach_tp1=0.20,
            p_opposite_edge_reach=0.26,
            p_better_reentry_if_cut=0.24,
        ),
        forecast_gap_metrics_v1={
            "transition_side_separation": 0.08,
            "transition_confirm_fake_gap": -0.14,
            "wait_confirm_gap": -0.12,
            "management_continue_fail_gap": -0.18,
        },
    )

    assert routed.state == "CONFIRM"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_mixed_confirm"
    assert routed.metadata["forecast_upper_reject_relief_v1"]["applied"] is True
    assert routed.metadata["forecast_upper_reject_relief_v1"]["context_label"] == "UPPER_EDGE"


def test_apply_forecast_modulation_keeps_upper_break_fail_confirm_when_near_ready():
    snapshot = ObserveConfirmSnapshot(
        state="CONFIRM",
        action="SELL",
        side="SELL",
        confidence=0.81,
        reason="upper_break_fail_confirm",
        archetype_id="upper_reject_sell",
        invalidation_id="upper_break_reclaim",
        management_profile_id="reversal_profile",
        metadata={
            "edge_pair_law_v1": {
                "context_label": "UPPER_EDGE",
            }
        },
    )

    routed = _apply_forecast_modulation(
        snapshot,
        transition_forecast_v1=TransitionForecast(
            p_buy_confirm=0.10,
            p_sell_confirm=0.1738,
            p_false_break=0.37,
            p_reversal_success=0.29,
            p_continuation_success=0.11,
        ),
        trade_management_forecast_v1=TradeManagementForecast(
            p_continue_favor=0.12,
            p_fail_now=0.1601,
            p_recover_after_pullback=0.15,
            p_reach_tp1=0.20,
            p_opposite_edge_reach=0.27,
            p_better_reentry_if_cut=0.24,
        ),
        forecast_gap_metrics_v1={
            "transition_side_separation": 0.18,
            "transition_confirm_fake_gap": -0.2476,
            "wait_confirm_gap": -0.2258,
            "management_continue_fail_gap": 0.2759,
        },
    )

    assert routed.state == "CONFIRM"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "upper_break_fail_confirm"
    assert routed.metadata["forecast_upper_reject_relief_v1"]["applied"] is True


def test_observe_confirm_router_v2_barrier_can_suppress_confirm_into_directional_observe():
    position, response, state, energy = _lower_hold_buy_case()

    baseline = _route(position, response, state, energy)
    routed = _route(
        position,
        response,
        state,
        energy,
        barrier_state_v1=BarrierState(
            buy_barrier=0.92,
            middle_chop_barrier=0.11,
        ),
    )

    assert baseline.state == "CONFIRM"
    assert baseline.action == "BUY"
    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "BUY"
    assert routed.archetype_id == baseline.archetype_id == "lower_hold_buy"
    assert routed.invalidation_id == baseline.invalidation_id == "lower_support_fail"
    assert routed.management_profile_id == baseline.management_profile_id == "support_hold_profile"
    assert routed.metadata["blocked_reason"] == "buy_barrier_suppressed_confirm"


@pytest.mark.parametrize(
    ("case_builder", "expected_archetype"),
    [
        (_lower_hold_buy_case, "lower_hold_buy"),
        (_upper_reject_sell_case, "upper_reject_sell"),
        (_upper_break_buy_case, "upper_break_buy"),
        (_lower_break_sell_case, "lower_break_sell"),
        (_mid_reclaim_buy_case, "mid_reclaim_buy"),
        (_mid_lose_sell_case, "mid_lose_sell"),
    ],
)
def test_observe_confirm_router_v2_attaches_canonical_handoff_ids(case_builder, expected_archetype):
    position, response, state, energy = case_builder()

    routed = _route(position, response, state, energy)

    assert routed.archetype_id == expected_archetype
    assert routed.invalidation_id == _EXPECTED_INVALIDATION_BY_ARCHETYPE[expected_archetype]
    assert routed.management_profile_id == _EXPECTED_MANAGEMENT_PROFILE_BY_ARCHETYPE[expected_archetype]


def test_observe_confirm_router_v2_identity_does_not_depend_on_legacy_energy_snapshot():
    position, response, state, _energy = _lower_hold_buy_case()

    low_energy = _route(
        position,
        response,
        state,
        EnergySnapshot(buy_force=0.01, sell_force=0.95, net_force=-0.94),
    )
    high_energy = _route(
        position,
        response,
        state,
        EnergySnapshot(buy_force=0.95, sell_force=0.01, net_force=0.94),
    )

    assert low_energy.archetype_id == high_energy.archetype_id == "lower_hold_buy"
    assert low_energy.side == high_energy.side == "BUY"
    assert low_energy.invalidation_id == high_energy.invalidation_id == "lower_support_fail"
    assert low_energy.management_profile_id == high_energy.management_profile_id == "support_hold_profile"


def test_observe_confirm_router_v2_requires_sr_anchor_for_middle_buy_entries():
    position, response, state, energy = _mid_reclaim_buy_without_sr_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "middle_sr_anchor_required_observe"
    assert routed.archetype_id == ""
    assert routed.metadata["blocked_reason"] == "middle_buy_requires_sr_anchor"


def test_observe_confirm_router_v2_keeps_edge_rotation_turn_buy_without_middle_sr_anchor():
    position, response, state, energy = _mid_reclaim_buy_edge_rotation_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFIRM"
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason == "mid_reclaim_confirm"
    assert routed.archetype_id == "mid_reclaim_buy"
    assert routed.metadata["middle_sr_anchor_guard_v1"]["suppressed"] is False
    assert routed.metadata["middle_sr_anchor_guard_v1"]["exempted"] is True
    assert routed.metadata["middle_sr_anchor_guard_v1"]["exemption_reason"] == "edge_rotation_turn_context"


def test_observe_confirm_router_v2_suppresses_lower_buy_candidate_when_bb20_is_middle_without_sr_anchor():
    position, response, state, energy = _mixed_lower_buy_without_sr_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "middle_sr_anchor_required_observe"
    assert routed.archetype_id == ""
    assert routed.metadata["blocked_reason"] == "middle_buy_requires_sr_anchor"


def test_observe_confirm_router_v2_keeps_strong_nas_clean_confirm_probe_directional_without_middle_sr_anchor():
    position, response, state, energy = _nas_clean_confirm_probe_without_sr_case(strong=True)

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason == "lower_rebound_probe_observe"
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["routing_guard_exemptions"]["middle_sr_anchor_guard"] is True
    assert routed.metadata["nas_clean_confirm_middle_anchor_relief"] is True
    assert routed.metadata["probe_candidate_v1"]["symbol_probe_temperament_v1"]["scene_id"] == "nas_clean_confirm_probe"


def test_observe_confirm_router_v2_keeps_weak_nas_clean_confirm_probe_blocked_by_middle_sr_anchor():
    position, response, state, energy = _nas_clean_confirm_probe_without_sr_case(strong=False)

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "middle_sr_anchor_required_observe"
    assert routed.metadata["blocked_guard"] == "middle_sr_anchor_guard"
    assert routed.metadata["middle_sr_anchor_guard_v1"]["suppressed"] is True


def test_observe_confirm_router_v2_keeps_nas_clean_confirm_upper_probe_directional_without_middle_sr_anchor():
    position, response, state, energy = _nas_clean_confirm_upper_probe_without_sr_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_probe_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["routing_guard_exemptions"]["middle_sr_anchor_guard"] is True
    assert routed.metadata["nas_clean_confirm_middle_anchor_relief"] is True
    assert routed.metadata["probe_candidate_v1"]["symbol_probe_temperament_v1"]["scene_id"] == "nas_clean_confirm_probe"


def test_observe_confirm_router_v2_requires_outer_band_support_for_lower_reversal_buy():
    position, response, state, energy = _lower_hold_buy_without_outer_band_support_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "outer_band_reversal_support_required_observe"
    assert routed.archetype_id == ""
    assert routed.metadata["blocked_reason"] == "outer_band_buy_reversal_support_required"


def test_observe_confirm_router_v2_does_not_allow_sr_alone_to_replace_outer_band_support():
    position, response, state, energy = _lower_hold_buy_with_sr_only_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.reason == "outer_band_reversal_support_required_observe"
    assert routed.archetype_id == ""
    assert routed.metadata["blocked_reason"] == "outer_band_buy_reversal_support_required"


def test_observe_confirm_router_v2_prioritizes_structural_lower_break_over_band_hold():
    position, response, state, energy = _structural_lower_break_override_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFIRM"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "lower_support_fail_confirm"
    assert routed.archetype_id == "lower_break_sell"
    assert routed.metadata["structural_break_override"] is True


def test_observe_confirm_router_v2_does_not_force_structural_break_sell_when_lower_hold_is_strong():
    position, response, state, energy = _structural_lower_break_with_strong_hold_case()

    routed = _route(position, response, state, energy)

    assert routed.action != "SELL"
    assert routed.metadata.get("structural_break_override") is not True
    assert routed.reason in {"lower_rebound_confirm", "lower_edge_observe"}


def test_observe_confirm_router_v2_prioritizes_mixed_upper_reject_over_lower_context_buy():
    position, response, state, energy = _mixed_upper_reject_override_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFIRM"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_mixed_confirm"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["mixed_upper_reject_override"] is True


def test_observe_confirm_router_v2_records_support_not_force_in_runtime_trace():
    position, response, state, energy = _lower_hold_buy_case()

    routed = _route(position, response, state, energy)

    assert routed.metadata["raw_contributions"]["semantic_readiness_bridge_v1"].keys() == {
        "emit_kind",
        "buy_support",
        "sell_support",
        "support_gap",
    }
    assert "buy_force" not in routed.metadata["raw_contributions"]["semantic_readiness_bridge_v1"]
    assert routed.metadata["semantic_readiness_bridge_v1"]["final"].keys() == {
        "buy_support",
        "sell_support",
        "support_gap",
    }
    assert routed.metadata["edge_pair_law_v1"]["context_label"] == "LOWER_EDGE"
    assert routed.metadata["edge_pair_law_v1"]["winner_side"] == "BUY"


def test_observe_confirm_router_v2_emits_lower_rebound_probe_before_confirm():
    position, response, state, energy = _lower_rebound_probe_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason == "lower_rebound_probe_observe"
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["probe_candidate_v1"]["active"] is True
    assert routed.metadata["probe_candidate_v1"]["probe_direction"] == "BUY"


def test_observe_confirm_router_v2_emits_upper_reject_probe_before_confirm():
    position, response, state, energy = _upper_reject_probe_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_probe_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["probe_candidate_v1"]["active"] is True
    assert routed.metadata["probe_candidate_v1"]["probe_direction"] == "SELL"


def test_observe_confirm_router_v2_uses_structural_resistance_to_unlock_xau_upper_probe():
    position, response, state, energy = _xau_upper_reject_structural_probe_case()

    routed = _route(position, response, state, energy)

    assert routed.state in {"OBSERVE", "CONFIRM"}
    assert routed.action == "SELL"
    assert routed.side == "SELL"
    assert routed.reason in {"upper_reject_probe_observe", "upper_reject_mixed_confirm"}
    assert routed.archetype_id == "upper_reject_sell"
    assert (
        routed.metadata.get("xau_structural_probe_relief") is True
        or routed.metadata.get("mixed_upper_reject_override") is True
    )
    if "upper_structural_reject_response" in routed.metadata:
        assert routed.metadata["upper_structural_reject_response"] == pytest.approx(0.22)
    else:
        assert routed.metadata["upper_reject_response"] == pytest.approx(0.22)
    if routed.state == "OBSERVE":
        assert routed.metadata["probe_candidate_v1"]["active"] is True
        assert routed.metadata["probe_candidate_v1"]["trigger_branch"] == "upper_reject"


def test_observe_confirm_router_v2_uses_second_support_relief_to_unlock_xau_lower_probe_without_outer_band():
    position, response, state, energy = _xau_second_support_probe_case()
    belief = BeliefState(
        buy_belief=0.48,
        sell_belief=0.18,
        buy_persistence=0.12,
        sell_persistence=0.02,
        dominant_side="BUY",
        dominant_mode="reversal",
        buy_streak=1,
    )

    routed = _route(position, response, state, energy, belief_state_v1=belief)

    assert routed.state in {"OBSERVE", "CONFIRM"}
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason in {"lower_rebound_probe_observe", "lower_rebound_confirm"}
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["xau_second_support_probe_relief"] is True
    assert routed.metadata["lower_structural_support_response"] == pytest.approx(0.26)
    if routed.state == "OBSERVE":
        assert routed.metadata["probe_candidate_v1"]["active"] is True
        assert routed.metadata["probe_candidate_v1"]["trigger_branch"] == "lower_rebound"


def test_observe_confirm_router_v2_respects_symbol_override_when_xau_second_support_relief_is_disabled(monkeypatch):
    _override_symbol_router_policy(
        monkeypatch,
        {
            "symbols": {
                "XAUUSD": {
                    "router": {
                        "relief": {
                            "second_support_probe": {
                                "enabled": False,
                            }
                        }
                    }
                }
            }
        },
    )
    position, response, state, energy = _xau_second_support_probe_case()
    belief = BeliefState(
        buy_belief=0.48,
        sell_belief=0.18,
        buy_persistence=0.12,
        sell_persistence=0.02,
        dominant_side="BUY",
        dominant_mode="reversal",
        buy_streak=1,
    )

    routed = _route(position, response, state, energy, belief_state_v1=belief)

    assert routed.metadata.get("xau_second_support_probe_relief") is False
    assert routed.action == "WAIT"


def test_observe_confirm_router_v2_uses_structural_relief_to_unlock_btc_lower_probe_without_outer_band():
    position, response, state, energy = _btc_structural_lower_probe_case()

    routed = _route(position, response, state, energy)

    assert routed.state in {"OBSERVE", "CONFIRM"}
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason in {"lower_rebound_probe_observe", "lower_rebound_confirm"}
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["btc_lower_structural_probe_relief"] is True
    assert routed.metadata["lower_structural_support_response"] == pytest.approx(0.24)
    if routed.state == "OBSERVE":
        assert routed.metadata["probe_candidate_v1"]["active"] is True
        assert routed.metadata["probe_candidate_v1"]["trigger_branch"] == "lower_rebound"


def test_observe_confirm_router_v2_uses_context_relief_to_unlock_btc_middle_lower_edge_probe_without_outer_band():
    position, response, state, energy = _btc_middle_lower_edge_context_probe_case()

    routed = _route(position, response, state, energy)

    assert routed.state in {"OBSERVE", "CONFIRM"}
    assert routed.action == "BUY"
    assert routed.side == "BUY"
    assert routed.reason in {"lower_rebound_probe_observe", "lower_rebound_confirm"}
    assert routed.archetype_id == "lower_hold_buy"
    assert routed.metadata["btc_lower_structural_probe_relief"] is True
    assert routed.metadata["btc_lower_structural_probe_relief_mode"] == "contextual"
    assert routed.metadata["lower_structural_support_response"] == pytest.approx(0.0)


def test_observe_confirm_router_v2_keeps_btc_middle_lower_edge_probe_blocked_when_context_relief_is_too_weak():
    position, response, state, energy = _btc_middle_lower_edge_context_probe_blocked_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "outer_band_reversal_support_required_observe"
    assert routed.metadata["btc_lower_structural_probe_relief"] is False
    assert routed.metadata["blocked_guard"] == "outer_band_guard"


def test_observe_confirm_router_v2_respects_symbol_override_when_btc_midline_transition_is_disabled(monkeypatch):
    _override_symbol_router_policy(
        monkeypatch,
        {
            "symbols": {
                "BTCUSD": {
                    "router": {
                        "context": {
                            "midline_rebound_transition": {
                                "enabled": False,
                            }
                        }
                    }
                }
            }
        },
    )
    position, response, state, energy = _btc_midline_rebound_sell_watch_case()

    routed = _route(position, response, state, energy)

    assert routed.reason != "btc_midline_sell_watch"
    assert routed.metadata.get("btc_midline_rebound_transition_v1") is None


def test_observe_confirm_router_v2_flips_btc_midline_rebound_to_sell_watch_after_bb20_cross():
    position, response, state, energy = _btc_midline_rebound_sell_watch_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "SELL"
    assert routed.reason == "btc_midline_sell_watch"
    assert routed.archetype_id == "mid_lose_sell"
    assert routed.metadata["btc_midline_rebound_transition_v1"]["active"] is True
    assert routed.metadata["btc_midline_rebound_transition_v1"]["bb20_zone"] == "MIDDLE"


def test_observe_confirm_router_v2_expires_btc_midline_rebound_buy_without_upper_reject_evidence():
    position, response, state, energy = _btc_midline_rebound_neutral_wait_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == ""
    assert routed.reason == "btc_lower_rebound_mid_expired"
    assert routed.metadata["btc_midline_rebound_transition_v1"]["active"] is True
    assert routed.metadata["btc_midline_rebound_transition_v1"]["x_bb20"] == pytest.approx(0.02)


def test_observe_confirm_router_v2_keeps_upper_reject_sell_visible_in_lower_upper_conflict():
    position, response, state, energy = _lower_upper_conflict_upper_reject_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFLICT_OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_probe_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["conflict_upper_reject_probe_ready"] is True
    assert routed.metadata["routing_guard_exemptions"]["outer_band_reversal_guard"] is True
    assert routed.metadata["dominance_side"] in {"LOWER", "UPPER"}


def test_observe_confirm_router_v2_keeps_balanced_lower_upper_conflict_sell_watch_visible():
    position, response, state, energy = _lower_upper_conflict_balanced_upper_reject_watch_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "CONFLICT_OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_probe_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["conflict_upper_reject_watch"] is True
    assert routed.metadata["probe_candidate_v1"]["active"] is True
    assert routed.metadata["routing_guard_exemptions"]["outer_band_reversal_guard"] is True


def test_observe_confirm_router_v2_keeps_xau_local_upper_reject_visible_in_lower_upper_conflict():
    position, response, state, energy = _xau_lower_upper_conflict_local_upper_reject_case()

    routed = _route(position, response, state, energy)

    assert routed.state == "OBSERVE"
    assert routed.action == "WAIT"
    assert routed.side == "SELL"
    assert routed.reason == "upper_reject_mixed_observe"
    assert routed.archetype_id == "upper_reject_sell"
    assert routed.metadata["xau_local_upper_reject_context"] is True
    assert routed.metadata["mixed_upper_reject_override"] is True
    assert routed.metadata["routing_guard_exemptions"]["middle_sr_anchor_guard"] is True
    assert routed.metadata["routing_guard_exemptions"]["outer_band_reversal_guard"] is True


def test_observe_confirm_router_v2_can_confirm_xau_local_upper_reject_when_sell_support_is_clear():
    position = PositionVector(
        x_box=-0.36,
        x_bb20=0.14,
        x_bb44=0.02,
        metadata={"symbol": "XAUUSD", "box_state": "LOWER", "bb_state": "MID"},
    )
    response = ResponseVector(
        r_bb20_upper_reject=0.14,
        r_box_upper_reject=0.10,
        r_sr_resistance_reject=0.22,
        r_trend_resistance_reject_m15=0.16,
        r_bb20_mid_lose=0.10,
        metadata={},
    )
    state = StateVector(
        market_mode="RANGE",
        direction_policy="BOTH",
        s_noise=0.06,
        s_conflict=0.0,
        metadata={"symbol": "XAUUSD"},
    )
    energy = EnergySnapshot(buy_force=0.02, sell_force=0.18, net_force=-0.16)

    routed = _route(position, response, state, energy)

    assert routed.action == "SELL"
    assert routed.reason == "upper_reject_mixed_confirm"
    assert routed.metadata["xau_local_upper_reject_context"] is True
    assert routed.metadata["xau_local_upper_confirm"] is True
