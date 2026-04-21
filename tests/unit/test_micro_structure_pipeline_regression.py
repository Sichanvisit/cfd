import pandas as pd

from backend.app.trading_application import TradingApplication
from backend.services.storage_compaction import _extract_micro_structure_hot_surface
from backend.trading.engine.core.forecast_features import build_forecast_features
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EngineContext,
    EvidenceVector,
    PositionEnergySnapshot,
    PositionInterpretation,
    PositionSnapshot,
    ResponseVectorV2,
)
from backend.trading.engine.state.builder import build_state_raw_snapshot, build_state_vector_v2_from_raw


def _build_breakout_frame():
    rows = []
    for i in range(25):
        open_price = 105.0 - (i * 0.1)
        close_price = open_price - 0.05
        if i in (6, 12, 18):
            close_price = open_price - 0.002
        high_price = max(open_price, close_price) + 0.08
        low_price = min(open_price, close_price) - 0.07
        tick_volume = 100 + (i * 3)
        if i == 22:
            tick_volume = 500
        elif i == 23:
            tick_volume = 220
        elif i == 24:
            tick_volume = 180
        rows.append(
            {
                "time": pd.Timestamp("2026-04-02 09:00:00") + pd.Timedelta(minutes=i),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "tick_volume": tick_volume,
                "real_volume": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _build_reversal_frame():
    rows = []
    base = 100.0
    for i in range(25):
        open_price = base + (0.02 if i % 2 == 0 else -0.01)
        close_price = base + (0.01 if i % 3 == 0 else -0.005)
        high_price = 101.2 if i in (6, 12, 18, 22, 24) else max(open_price, close_price) + 0.45
        low_price = 99.1 if i in (5, 11, 17) else min(open_price, close_price) - 0.18
        tick_volume = 120 + (10 if i in (6, 12, 18, 22, 24) else 0)
        rows.append(
            {
                "time": pd.Timestamp("2026-04-02 10:00:00") + pd.Timedelta(minutes=i),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "tick_volume": tick_volume,
                "real_volume": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _build_features_from_micro(micro_structure, *, price=100.0):
    ctx = EngineContext(
        symbol="XAUUSD",
        price=price,
        market_mode="RANGE",
        direction_policy="BOTH",
        metadata={
            "recent_body_mean": 4.2,
            "position_gate_input_v1": {
                "interpretation": {
                    "mtf_context_weight_profile_v1": {
                        "bias": 0.35,
                        "agreement_score": 0.62,
                    }
                },
                "energy": {"middle_neutrality": 0.28},
                "position_scale": {"compression_score": 0.41},
            },
            "micro_structure_v1": micro_structure,
        },
    )
    raw = build_state_raw_snapshot(ctx)
    state_vector = build_state_vector_v2_from_raw(raw)
    features = build_forecast_features(
        PositionSnapshot(
            interpretation=PositionInterpretation(
                primary_label="ALIGNED_UPPER_WEAK",
                bias_label="ALIGNED_UPPER_WEAK",
                secondary_context_label="UPPER_CONTEXT",
            ),
            energy=PositionEnergySnapshot(
                middle_neutrality=0.28,
                position_conflict_score=0.12,
            ),
        ),
        ResponseVectorV2(upper_break_up=0.31, upper_reject_down=0.14),
        state_vector,
        EvidenceVector(buy_total_evidence=0.19, sell_total_evidence=0.22),
        BeliefState(buy_belief=0.16, sell_belief=0.18),
        BarrierState(middle_chop_barrier=0.21),
    )
    semantic = dict(features.metadata.get("semantic_forecast_inputs_v2") or {})
    hot_surface = _extract_micro_structure_hot_surface(
        {
            "state_vector_v2": state_vector.to_dict(),
            "forecast_features_v1": semantic,
        }
    )
    return raw, state_vector, features, hot_surface


def test_micro_structure_pipeline_breakout_flow_surfaces_compact_values():
    micro = TradingApplication.build_micro_structure_v1_from_ohlcv(
        _build_breakout_frame(),
        metadata={"session_open": 105.0, "previous_session_close": 100.0},
    )

    raw, state_vector, features, hot_surface = _build_features_from_micro(micro, price=96.0)

    assert raw.metadata["micro_structure_data_state"] == "READY"
    assert state_vector.metadata["micro_breakout_readiness_state"] in {"BREAKOUT_READY", "BREAKOUT_WATCH", "BREAKOUT_NEUTRAL"}
    semantic = features.metadata["semantic_forecast_inputs_v2"]
    assert semantic["state_harvest"]["micro_breakout_readiness_state"] == state_vector.metadata["micro_breakout_readiness_state"]
    assert semantic["secondary_harvest"]["source_micro_body_size_pct_20"] == state_vector.metadata["source_micro_body_size_pct_20"]
    assert hot_surface["micro_breakout_readiness_state"] == state_vector.metadata["micro_breakout_readiness_state"]
    assert hot_surface["micro_body_size_pct_20"] == state_vector.metadata["source_micro_body_size_pct_20"]
    assert hot_surface["micro_doji_ratio_20"] == state_vector.metadata["source_micro_doji_ratio_20"]
    assert hot_surface["micro_same_color_run_current"] == state_vector.metadata["source_micro_same_color_run_current"]
    assert hot_surface["micro_range_compression_ratio_20"] == state_vector.metadata["source_micro_range_compression_ratio_20"]
    assert hot_surface["micro_volume_burst_decay_20"] == state_vector.metadata["source_micro_volume_burst_decay_20"]
    assert hot_surface["micro_gap_fill_progress"] == state_vector.metadata["source_micro_gap_fill_progress"]


def test_micro_structure_pipeline_reversal_flow_flags_wick_and_retest_risk():
    micro = TradingApplication.build_micro_structure_v1_from_ohlcv(
        _build_reversal_frame(),
        metadata={"session_open": 100.8, "previous_session_close": 101.6},
    )

    _, state_vector, features, hot_surface = _build_features_from_micro(micro, price=99.7)

    assert micro["upper_wick_ratio_20"] > 0.2
    assert micro["swing_high_retest_count_20"] >= 2
    assert state_vector.metadata["micro_reversal_risk_state"] in {"REVERSAL_RISK_WATCH", "REVERSAL_RISK_HIGH"}
    assert features.metadata["semantic_forecast_inputs_v2"]["state_harvest"]["micro_reversal_risk_state"] == state_vector.metadata["micro_reversal_risk_state"]
    assert hot_surface["micro_reversal_risk_state"] == state_vector.metadata["micro_reversal_risk_state"]


def test_micro_structure_pipeline_missing_gap_anchor_stays_safe_end_to_end():
    micro = TradingApplication.build_micro_structure_v1_from_ohlcv(_build_breakout_frame(), metadata={})

    raw, state_vector, features, hot_surface = _build_features_from_micro(micro, price=96.0)

    assert micro["anchor_state"] == "MISSING_GAP_ANCHOR"
    assert micro["gap_fill_progress"] is None
    assert raw.s_gap_fill_progress is None
    assert state_vector.metadata["micro_gap_context_state"] == "GAP_CONTEXT_MISSING"
    assert features.metadata["semantic_forecast_inputs_v2"]["state_harvest"]["micro_gap_context_state"] == "GAP_CONTEXT_MISSING"
    assert hot_surface["micro_gap_context_state"] == "GAP_CONTEXT_MISSING"
    assert hot_surface["micro_gap_fill_progress"] == ""
