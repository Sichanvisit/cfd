from types import SimpleNamespace

import pandas as pd

import backend.services.context_classifier as context_classifier_module
from backend.services.context_classifier import ContextClassifier
from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.core.models import EnergySnapshot, ObserveConfirmSnapshot
from backend.trading.engine.response import build_response_raw_snapshot, build_response_vector
from backend.trading.engine.state import build_state_vector


class _DummySessionMgr:
    def get_session_range(self, *_args, **_kwargs):
        return {"high": 110.0, "low": 90.0}


class _DummyTrendMgr:
    def add_indicators(self, frame):
        out = frame.copy()
        out["bb_20_up"] = 110.0
        out["bb_20_mid"] = 100.0
        out["bb_20_dn"] = 90.0
        out["bb_4_up"] = 112.0
        out["bb_4_dn"] = 88.0
        out["ma_20"] = 99.0
        out["ma_60"] = 98.0
        out["ma_120"] = 97.0
        out["ma_240"] = 96.0
        out["ma_480"] = 95.0
        out["disparity"] = 97.5
        out["rsi"] = 38.0
        out["adx"] = 24.0
        out["plus_di"] = 28.0
        out["minus_di"] = 16.0
        return out

    def get_ma_alignment(self, _candle):
        return "BULL"


class _DummyScorer:
    def __init__(self):
        self.session_mgr = _DummySessionMgr()
        self.trend_mgr = _DummyTrendMgr()


def test_response_vector_detects_lower_band_hold_and_mid_reclaim():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=96.0,
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
        metadata={
            "current_open": 100.2,
            "current_high": 101.0,
            "current_low": 89.95,
            "current_close": 100.5,
            "previous_close": 99.0,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
        },
    )
    vector = build_response_vector(ctx)
    assert vector.r_bb20_lower_hold > 0.0
    assert vector.r_bb20_mid_reclaim > 0.0
    assert vector.r_box_lower_bounce > 0.0
    assert vector.r_candle_lower_reject > 0.0


def test_response_raw_snapshot_detects_lower_band_hold_and_mid_reclaim():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=96.0,
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
        metadata={
            "current_open": 100.2,
            "current_high": 101.0,
            "current_low": 89.95,
            "current_close": 100.5,
            "previous_close": 99.0,
            "band_touch_tolerance": 0.2,
            "box_touch_tolerance": 0.2,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    assert raw.bb20_lower_hold > 0.0
    assert raw.bb20_mid_reclaim > 0.0
    assert raw.box_lower_bounce > 0.0
    assert raw.candle_lower_reject > 0.0


def test_response_vector_detects_mid_hold_and_box_mid_hold():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.2,
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 99.8,
            "current_high": 100.5,
            "current_low": 99.92,
            "current_close": 100.3,
            "previous_close": 100.1,
            "band_touch_tolerance": 0.12,
            "box_touch_tolerance": 0.12,
        },
    )
    vector = build_response_vector(ctx)
    assert vector.r_bb20_mid_hold > 0.0
    assert vector.r_box_mid_hold > 0.0


def test_response_vector_detects_mid_hold_from_proximity_without_touch():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.25,
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 100.05,
            "current_high": 100.42,
            "current_low": 98.55,
            "current_close": 100.28,
            "previous_close": 100.18,
            "band_touch_tolerance": 0.05,
            "box_touch_tolerance": 0.05,
        },
    )
    vector = build_response_vector(ctx)
    assert vector.r_bb20_mid_hold > 0.0
    assert vector.r_box_mid_hold > 0.0


def test_response_vector_detects_upper_reject_from_failed_overshoot():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=110.15,
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
            "current_open": 110.20,
            "current_high": 110.55,
            "current_low": 109.95,
            "current_close": 110.04,
            "previous_close": 110.10,
            "band_touch_tolerance": 0.08,
            "box_touch_tolerance": 0.08,
        },
    )
    vector = build_response_vector(ctx)
    assert vector.r_bb20_upper_reject > 0.0
    assert vector.r_box_upper_reject > 0.0


def test_response_raw_snapshot_detects_lower_break():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=89.0,
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
        metadata={
            "current_open": 90.4,
            "current_high": 90.6,
            "current_low": 88.8,
            "current_close": 89.0,
            "previous_close": 90.8,
            "band_touch_tolerance": 0.08,
            "box_touch_tolerance": 0.08,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    vector = build_response_vector(ctx)
    assert raw.bb20_lower_break > 0.0
    assert raw.box_lower_break > 0.0
    assert vector.r_bb20_lower_break == raw.bb20_lower_break
    assert vector.r_box_lower_break == raw.box_lower_break


def test_response_raw_snapshot_treats_green_close_below_lower_levels_as_break_not_hold():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=89.3,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="BELOW",
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
            "current_open": 88.9,
            "current_high": 89.5,
            "current_low": 88.75,
            "current_close": 89.3,
            "previous_close": 89.5,
            "band_touch_tolerance": 0.08,
            "box_touch_tolerance": 0.08,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    vector = build_response_vector(ctx)
    assert raw.bb20_lower_break > 0.0
    assert raw.box_lower_break > 0.0
    assert raw.bb20_lower_hold == 0.0
    assert raw.box_lower_bounce == 0.0
    assert vector.r_bb20_lower_break == raw.bb20_lower_break
    assert vector.r_box_lower_break == raw.box_lower_break


def test_response_raw_snapshot_detects_mid_lose_and_mid_reject():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=99.7,
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 100.3,
            "current_high": 100.4,
            "current_low": 99.5,
            "current_close": 99.7,
            "previous_close": 100.2,
            "band_touch_tolerance": 0.05,
            "box_touch_tolerance": 0.05,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    vector = build_response_vector(ctx)
    assert raw.bb20_mid_lose > 0.0
    assert raw.bb20_mid_reject > 0.0
    assert raw.box_mid_reject > 0.0
    assert vector.r_bb20_mid_lose == raw.bb20_mid_lose
    assert vector.r_box_mid_reject == raw.box_mid_reject


def test_response_raw_snapshot_detects_upper_break():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=110.5,
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="ABOVE",
        bb_state="BREAKOUT",
        box_low=90.0,
        box_high=110.0,
        bb20_up=110.0,
        bb20_mid=100.0,
        bb20_dn=90.0,
        bb44_up=112.0,
        bb44_mid=100.0,
        bb44_dn=88.0,
        metadata={
            "current_open": 110.1,
            "current_high": 110.8,
            "current_low": 110.0,
            "current_close": 110.5,
            "previous_close": 109.9,
            "band_touch_tolerance": 0.08,
            "box_touch_tolerance": 0.08,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    vector = build_response_vector(ctx)
    assert raw.bb20_upper_break > 0.0
    assert raw.box_upper_break > 0.0
    assert vector.r_bb20_upper_break == raw.bb20_upper_break
    assert vector.r_box_upper_break == raw.box_upper_break


def test_response_raw_snapshot_treats_red_close_above_upper_levels_as_break_not_reject():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=110.7,
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
            "current_open": 111.3,
            "current_high": 111.5,
            "current_low": 110.6,
            "current_close": 110.7,
            "previous_close": 111.0,
            "band_touch_tolerance": 0.08,
            "box_touch_tolerance": 0.08,
        },
    )
    raw = build_response_raw_snapshot(ctx)
    vector = build_response_vector(ctx)
    assert raw.bb20_upper_break > 0.0
    assert raw.box_upper_break > 0.0
    assert raw.bb20_upper_reject == 0.0
    assert raw.box_upper_reject == 0.0
    assert vector.r_bb20_upper_break == raw.bb20_upper_break
    assert vector.r_box_upper_break == raw.box_upper_break


def test_state_vector_normalizes_noise_conflict_alignment_disparity():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=100.0,
        market_mode="RANGE",
        direction_policy="BOTH",
        metadata={
            "raw_scores": {"wait_noise": 12.5, "wait_conflict": 6.25},
            "current_disparity": 97.0,
            "current_volatility_ratio": 1.3,
            "ma_alignment": "BULL",
        },
    )
    vector = build_state_vector(ctx)
    assert 0.4 <= vector.s_noise <= 0.6
    assert 0.2 <= vector.s_conflict <= 0.3
    assert vector.s_alignment == 1.0
    assert vector.s_disparity == 1.0
    assert vector.s_volatility > 0.0


def test_context_classifier_snapshot_includes_response_and_state_vectors():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "high": [101.0, 105.0, 110.0],
                "low": [89.0, 92.0, 90.0],
                "close": [100.0, 103.0, 95.0],
            }
        ),
        "15M": pd.DataFrame(
            {
                "open": [92.0, 94.0],
                "high": [96.0, 101.0],
                "low": [90.0, 89.9],
                "close": [99.0, 100.5],
            }
        ),
    }
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=95.0, ask=95.1),
        df_all=df_all,
        scorer=scorer,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        raw_scores={"wait_noise": 10.0, "wait_conflict": 2.0},
    )
    assert bundle["response_raw_snapshot"].bb20_lower_hold > 0.0
    assert bundle["response_raw_snapshot"].metadata["candle_descriptor_v1"]["version"] == "candle_descriptor_v1"
    assert bundle["response_raw_snapshot"].metadata["candle_pattern_v1"]["version"] == "candle_pattern_v1"
    assert bundle["response_raw_snapshot"].metadata["candle_motif_v1"]["version"] == "candle_motif_v1"
    assert bundle["response_raw_snapshot"].metadata["structure_motif_v1"]["version"] == "structure_motif_v1"
    assert bundle["response_vector"].r_bb20_lower_hold > 0.0
    assert bundle["response_vector"].metadata["response_contract"] == "execution_bridge_v1"
    assert bundle["response_vector_execution_bridge"].metadata["canonical_response_field"] == "response_vector_v2"
    assert bundle["response_vector_v2"].lower_hold_up > 0.0
    assert bundle["state_raw_snapshot"].market_mode == "RANGE"
    assert bundle["state_vector"].market_mode == "RANGE"
    assert bundle["state_vector"].s_noise > 0.0
    assert bundle["state_vector_v2"].range_reversal_gain > 1.0


def test_context_classifier_routes_execution_layers_with_response_execution_bridge(monkeypatch):
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "high": [101.0, 105.0, 110.0],
                "low": [89.0, 92.0, 90.0],
                "close": [100.0, 103.0, 95.0],
            }
        ),
        "15M": pd.DataFrame(
            {
                "open": [92.0, 94.0],
                "high": [96.0, 101.0],
                "low": [90.0, 89.9],
                "close": [99.0, 100.5],
            }
        ),
    }
    seen: dict[str, str] = {}

    def _fake_energy(position, response, state, position_snapshot=None):
        seen["energy_response_contract"] = str((response.metadata or {}).get("response_contract") or "")
        return EnergySnapshot()

    def _fake_observe(position, response, state, position_snapshot, **kwargs):
        seen["observe_response_contract"] = str((response.metadata or {}).get("response_contract") or "")
        return ObserveConfirmSnapshot(state="OBSERVE", action="WAIT", side="", reason="test")

    monkeypatch.setattr(context_classifier_module, "compute_energy_snapshot", _fake_energy)
    monkeypatch.setattr(context_classifier_module, "route_observe_confirm", _fake_observe)

    classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=95.0, ask=95.1),
        df_all=df_all,
        scorer=scorer,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        raw_scores={"wait_noise": 10.0, "wait_conflict": 2.0},
    )

    assert seen["energy_response_contract"] == "execution_bridge_v1"
    assert seen["observe_response_contract"] == "execution_bridge_v1"
