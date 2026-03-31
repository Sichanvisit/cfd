from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from backend.services.context_classifier import ContextClassifier
from backend.trading.engine.core.context import build_engine_context
from backend.trading.engine.position import build_position_vector


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
        return out


class _DummyScorer:
    def __init__(self):
        self.session_mgr = _DummySessionMgr()
        self.trend_mgr = _DummyTrendMgr()


class _DummyTrendMgrMTF:
    _ma20_by_tf = {
        "15M": 99.0,
        "30M": 100.0,
        "1H": 101.0,
        "4H": 103.0,
        "1D": 105.0,
    }
    _pivot_idx_by_tf = {
        "1M": {"high": [1, 3], "low": [2, 4]},
        "15M": {"high": [1, 3], "low": [2, 4]},
        "1H": {"high": [1, 3], "low": [2, 4]},
        "4H": {"high": [1, 3], "low": [2, 4]},
    }

    def add_indicators(self, frame):
        out = frame.copy()
        tf_marker = str(out["tf_marker"].iloc[-1]) if "tf_marker" in out.columns else "15M"
        ma20 = float(self._ma20_by_tf.get(tf_marker, 100.0))
        out["bb_20_up"] = ma20 + 10.0
        out["bb_20_mid"] = ma20
        out["bb_20_dn"] = ma20 - 10.0
        out["bb_4_up"] = ma20 + 12.0
        out["bb_4_dn"] = ma20 - 12.0
        out["ma_20"] = ma20
        out["ma_60"] = ma20 - 1.0
        out["ma_120"] = ma20 - 2.0
        out["ma_240"] = ma20 - 3.0
        out["ma_480"] = ma20 - 4.0
        return out

    def get_ma_alignment(self, _candle):
        return "MIXED"

    def get_pivots(self, frame, order=5):
        tf_marker = str(frame["tf_marker"].iloc[-1]) if "tf_marker" in frame.columns else "15M"
        pivots = self._pivot_idx_by_tf.get(tf_marker, {"high": [1, 3], "low": [2, 4]})
        return np.array(pivots["high"]), np.array(pivots["low"])


class _DummyScorerMTF:
    def __init__(self):
        self.session_mgr = _DummySessionMgr()
        self.trend_mgr = _DummyTrendMgrMTF()


def test_position_vector_normalizes_box_and_bands():
    ctx = build_engine_context(
        symbol="BTCUSD",
        price=95.0,
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
        volatility_scale=10.0,
    )
    vector = build_position_vector(ctx)
    assert round(vector.x_box, 2) == -0.5
    assert round(vector.x_bb20, 2) == -0.5
    assert round(vector.x_bb44, 2) == -0.42
    assert vector.x_ma20 < 0.0
    assert vector.x_sr < 0.0
    assert vector.metadata["position_scale"]["box_height_ratio"] == 2.0
    assert vector.metadata["position_scale"]["bb20_width_ratio"] == 2.0
    assert round(vector.metadata["position_scale"]["bb44_width_ratio"], 2) == 2.4
    assert vector.metadata["position_scale"]["box_size_state"] == "WIDE"
    assert vector.metadata["position_scale"]["bb20_width_state"] == "EXPANDED"


def test_context_classifier_builds_engine_context_snapshot():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "high": [101.0, 105.0, 110.0],
                "low": [89.0, 92.0, 90.0],
                "close": [100.0, 103.0, 95.0],
                "open": [99.0, 100.5, 103.0],
            }
        ),
        "5M": pd.DataFrame(
            {
                "open": [94.8, 95.1, 95.0],
                "high": [95.2, 95.6, 95.4],
                "low": [94.7, 94.9, 94.8],
                "close": [95.0, 95.2, 95.1],
            }
        ),
        "15M": pd.DataFrame(
            {
                "open": [95.0],
                "close": [95.0],
                "high": [96.0],
                "low": [94.0],
            }
        ),
        "1M": pd.DataFrame(
            {
                "open": [94.9, 95.0, 95.0],
                "high": [95.1, 95.2, 95.15],
                "low": [94.8, 94.95, 94.9],
                "close": [95.0, 95.05, 95.0],
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
    )
    engine_ctx = bundle["engine_context"]
    pos = bundle["position_vector"]
    pos_snapshot = bundle["position_snapshot"]
    assert engine_ctx.box_low == 90.0
    assert engine_ctx.box_high == 110.0
    assert engine_ctx.bb20_mid == 100.0
    assert pos.x_box < 0.0
    assert pos.x_bb20 < 0.0
    assert pos.metadata["market_mode"] == "RANGE"
    assert pos.metadata["position_scale"]["version"] == "v1_position_scale"
    assert pos.metadata["position_scale"]["map_size_state"] == "EXPANDED"
    assert bundle["position_zones"].box_zone == "LOWER"
    assert bundle["position_zones"].ma20_zone == "BELOW"
    assert bundle["position_interpretation"].primary_label == "LOWER_BIAS"
    assert bundle["position_interpretation"].bias_label == "LOWER_BIAS"
    assert bundle["position_interpretation"].secondary_context_label == "LOWER_CONTEXT"
    assert bundle["position_interpretation"].metadata["raw_alignment_label"] == "ALIGNED_LOWER_WEAK"
    assert bundle["position_interpretation"].metadata["alignment_softening"]["downgraded"] is True
    assert bundle["position_interpretation"].metadata["position_scale"]["box_height"] == 20.0
    assert bundle["position_energy"].lower_position_force > bundle["position_energy"].upper_position_force
    assert bundle["position_energy"].metadata["position_scale"]["bb20_width_state"] == "EXPANDED"
    micro_bar_map = engine_ctx.metadata["micro_tf_bar_map_v1"]
    assert micro_bar_map["timeframes_available"] == ["1M", "5M"]
    assert micro_bar_map["entries"]["5M"]["close"] == 95.1
    micro_window_map = engine_ctx.metadata["micro_tf_window_map_v1"]
    assert micro_window_map["entries"]["1M"]["window_size"] == 3
    assert micro_window_map["entries"]["5M"]["window_size"] == 3
    assert pos_snapshot.vector.to_dict() == pos.to_dict()


def test_context_classifier_exposes_mtf_ma_big_map_in_position_metadata():
    classifier = ContextClassifier()
    scorer = _DummyScorerMTF()
    df_all = {
        "1D": pd.DataFrame({"close": [100.0], "high": [106.0], "low": [94.0], "tf_marker": ["1D"]}),
        "4H": pd.DataFrame({"close": [100.0], "high": [104.0], "low": [96.0], "tf_marker": ["4H"]}),
        "1H": pd.DataFrame({"close": [100.0], "high": [102.0], "low": [98.0], "tf_marker": ["1H"]}),
        "30M": pd.DataFrame({"close": [100.0], "high": [101.0], "low": [99.0], "tf_marker": ["30M"]}),
        "15M": pd.DataFrame({"close": [100.0], "high": [101.0], "low": [99.0], "tf_marker": ["15M"]}),
    }
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all=df_all,
        scorer=scorer,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="MIDDLE",
        bb_state="MID",
    )

    mtf_map = bundle["position_vector"].metadata["mtf_ma_big_map_v1"]

    assert mtf_map["version"] == "mtf_ma_big_map_v1"
    assert mtf_map["timeframes_available"] == ["1D", "4H", "1H", "30M", "15M"]
    assert mtf_map["entries"]["1H"]["ma20"] == 101.0
    assert mtf_map["entries"]["15M"]["ma20"] == 99.0
    assert mtf_map["entries"]["1H"]["side"] == "BELOW"
    assert mtf_map["entries"]["15M"]["side"] == "ABOVE"
    assert mtf_map["recent_upper_anchor_tf"] == "1H"
    assert mtf_map["recent_upper_anchor_distance"] == 1.0
    assert mtf_map["recent_lower_anchor_tf"] == "15M"
    assert mtf_map["recent_lower_anchor_distance"] == 1.0
    assert mtf_map["stack_state"] == "BEAR_STACK"
    assert bundle["position_interpretation"].metadata["mtf_ma_big_map_v1"]["recent_upper_anchor_tf"] == "1H"
    assert bundle["position_energy"].metadata["mtf_ma_big_map_v1"]["recent_lower_anchor_tf"] == "15M"


def test_context_classifier_exposes_mtf_trendline_map_in_position_metadata():
    classifier = ContextClassifier()
    scorer = _DummyScorerMTF()
    frame_template = {
        "open": [99.8, 100.2, 100.5, 99.8, 100.2, 100.1],
        "close": [100.0, 101.0, 99.0, 100.5, 100.0, 100.0],
        "high": [101.0, 105.0, 103.0, 103.0, 102.0, 101.5],
        "low": [99.0, 98.5, 96.5, 97.0, 98.0, 98.5],
    }
    df_all = {
        "1M": pd.DataFrame({**frame_template, "tf_marker": ["1M"] * 6}),
        "15M": pd.DataFrame({**frame_template, "tf_marker": ["15M"] * 6}),
        "1H": pd.DataFrame({**frame_template, "tf_marker": ["1H"] * 6}),
        "4H": pd.DataFrame({**frame_template, "tf_marker": ["4H"] * 6}),
        "1D": pd.DataFrame({"close": [100.0], "high": [106.0], "low": [94.0], "tf_marker": ["1D"]}),
        "30M": pd.DataFrame({"close": [100.0], "high": [101.0], "low": [99.0], "tf_marker": ["30M"]}),
    }
    bundle = classifier.build_engine_context_snapshot(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all=df_all,
        scorer=scorer,
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="MIDDLE",
        bb_state="MID",
    )

    trend_map = bundle["position_vector"].metadata["mtf_trendline_map_v1"]

    assert trend_map["version"] == "mtf_trendline_map_v1"
    assert trend_map["timeframes_available"] == ["1M", "15M", "1H", "4H"]
    assert trend_map["entries"]["1H"]["support_value"] is not None
    assert trend_map["entries"]["1H"]["resistance_value"] is not None
    assert abs(trend_map["x_tl_m1"]) > 0.0
    assert abs(trend_map["x_tl_h1"]) > 0.0
    assert trend_map["tl_proximity_m1"] > 0.0
    assert trend_map["tl_kind_h1"] == "RESISTANCE"
    assert trend_map["recent_upper_anchor_tf"] != ""
    assert trend_map["recent_lower_anchor_tf"] != ""
    assert bundle["position_vector"].metadata["x_tl_h1"] == trend_map["x_tl_h1"]
    assert bundle["position_vector"].metadata["tl_proximity_h1"] == trend_map["tl_proximity_h1"]
    assert bundle["position_interpretation"].metadata["mtf_trendline_map_v1"]["timeframes_available"] == ["1M", "15M", "1H", "4H"]
    assert bundle["position_energy"].metadata["mtf_trendline_map_v1"]["recent_lower_anchor_tf"] != ""
    trend_bar_map = bundle["engine_context"].metadata["mtf_trendline_bar_map_v1"]
    assert trend_bar_map["version"] == "mtf_trendline_bar_map_v1"
    assert trend_bar_map["timeframes_available"] == ["1M", "15M", "1H", "4H"]
    assert trend_bar_map["entries"]["1H"]["close"] == 100.0


def test_observe_confirm_router_consumes_position_snapshot_contract():
    root = Path(__file__).resolve().parents[2]
    router_path = root / "backend" / "trading" / "engine" / "core" / "observe_confirm_router.py"
    classifier_path = root / "backend" / "services" / "context_classifier.py"
    runner_path = root / "backend" / "app" / "trading_application_runner.py"
    consumer_contract_path = root / "backend" / "services" / "consumer_contract.py"
    layer_mode_contract_path = root / "backend" / "services" / "layer_mode_contract.py"
    setup_detector_path = root / "backend" / "services" / "setup_detector.py"
    entry_service_path = root / "backend" / "services" / "entry_service.py"
    router_source = router_path.read_text(encoding="utf-8")
    classifier_source = classifier_path.read_text(encoding="utf-8")
    runner_source = runner_path.read_text(encoding="utf-8")
    consumer_contract_source = consumer_contract_path.read_text(encoding="utf-8")
    layer_mode_contract_source = layer_mode_contract_path.read_text(encoding="utf-8")
    setup_detector_source = setup_detector_path.read_text(encoding="utf-8")
    entry_service_source = entry_service_path.read_text(encoding="utf-8")

    assert "position_snapshot: PositionSnapshot" in router_source
    assert "def _coord_zone" not in router_source
    assert "def _effective_box_zone" not in router_source
    assert "def _effective_bb20_zone" not in router_source
    assert "def _conflict_kind" not in router_source
    assert "def _conflict_dominance" not in router_source
    assert "position_snapshot" in classifier_source
    assert "observe_confirm_input_contract_v2" in classifier_source
    assert "observe_confirm_input_contract_field" in classifier_source
    assert "observe_confirm_migration_dual_write_v1" in classifier_source
    assert "observe_confirm_migration_contract_field" in classifier_source
    assert "observe_confirm_output_contract_v2" in classifier_source
    assert "observe_confirm_output_contract_field" in classifier_source
    assert "observe_confirm_scope_contract_v1" in classifier_source
    assert "observe_confirm_scope_contract_field" in classifier_source
    assert "consumer_input_contract_v1" in classifier_source
    assert "consumer_input_contract_field" in classifier_source
    assert "consumer_layer_mode_integration_v1" in classifier_source
    assert "consumer_layer_mode_integration_field" in classifier_source
    assert "consumer_migration_freeze_v1" in classifier_source
    assert "consumer_migration_freeze_field" in classifier_source
    assert "consumer_logging_contract_v1" in classifier_source
    assert "consumer_logging_contract_field" in classifier_source
    assert "consumer_test_contract_v1" in classifier_source
    assert "consumer_test_contract_field" in classifier_source
    assert "consumer_freeze_handoff_v1" in classifier_source
    assert "consumer_freeze_handoff_field" in classifier_source
    assert "layer_mode_contract_v1" in classifier_source
    assert "layer_mode_contract_field" in classifier_source
    assert "layer_mode_layer_inventory_v1" in classifier_source
    assert "layer_mode_layer_inventory_field" in classifier_source
    assert "layer_mode_default_policy_v1" in classifier_source
    assert "layer_mode_default_policy_field" in classifier_source
    assert "layer_mode_dual_write_contract_v1" in classifier_source
    assert "layer_mode_dual_write_contract_field" in classifier_source
    assert "layer_mode_influence_semantics_v1" in classifier_source
    assert "layer_mode_influence_semantics_field" in classifier_source
    assert "layer_mode_application_contract_v1" in classifier_source
    assert "layer_mode_application_contract_field" in classifier_source
    assert "layer_mode_identity_guard_contract_v1" in classifier_source
    assert "layer_mode_identity_guard_contract_field" in classifier_source
    assert "layer_mode_policy_overlay_output_contract_v1" in classifier_source
    assert "layer_mode_policy_overlay_output_contract_field" in classifier_source
    assert "layer_mode_logging_replay_contract_v1" in classifier_source
    assert "layer_mode_logging_replay_contract_field" in classifier_source
    assert "layer_mode_test_contract_v1" in classifier_source
    assert "layer_mode_test_contract_field" in classifier_source
    assert "layer_mode_freeze_handoff_v1" in classifier_source
    assert "layer_mode_freeze_handoff_field" in classifier_source
    assert "layer_mode_scope_contract_v1" in classifier_source
    assert "layer_mode_scope_contract_field" in classifier_source
    assert "position_snapshot_effective_v1" in classifier_source
    assert "response_vector_effective_v1" in classifier_source
    assert "state_vector_effective_v1" in classifier_source
    assert "evidence_vector_effective_v1" in classifier_source
    assert "belief_state_effective_v1" in classifier_source
    assert "barrier_state_effective_v1" in classifier_source
    assert "forecast_effective_policy_v1" in classifier_source
    assert "layer_mode_effective_trace_v1" in classifier_source
    assert "layer_mode_influence_trace_v1" in classifier_source
    assert "layer_mode_application_trace_v1" in classifier_source
    assert "layer_mode_identity_guard_trace_v1" in classifier_source
    assert "layer_mode_policy_v1" in classifier_source
    assert "layer_mode_logging_replay_v1" in classifier_source
    assert "setup_detector_responsibility_contract_v1" in classifier_source
    assert "setup_detector_responsibility_contract_field" in classifier_source
    assert "setup_mapping_contract_v1" in classifier_source
    assert "setup_mapping_contract_field" in classifier_source
    assert "entry_guard_contract_v1" in classifier_source
    assert "entry_guard_contract_field" in classifier_source
    assert "entry_service_responsibility_contract_v1" in classifier_source
    assert "entry_service_responsibility_contract_field" in classifier_source
    assert "exit_handoff_contract_v1" in classifier_source
    assert "exit_handoff_contract_field" in classifier_source
    assert "re_entry_contract_v1" in classifier_source
    assert "re_entry_contract_field" in classifier_source
    assert "consumer_scope_contract_v1" in classifier_source
    assert "consumer_scope_contract_field" in classifier_source
    assert "\"canonical_observe_confirm_field\": \"observe_confirm_v2\"" in classifier_source
    assert "\"compatibility_observe_confirm_field\": \"observe_confirm_v1\"" in classifier_source
    assert "\"canonical_observe_confirm_field\": \"observe_confirm_v2\"" in consumer_contract_source
    assert "\"canonical_policy_field\": \"layer_mode_policy_v1\"" in consumer_contract_source
    assert "\"canonical_observe_confirm_field\": \"observe_confirm_v2\"" in runner_source
    assert "\"compatibility_observe_confirm_field\": \"observe_confirm_v1\"" in runner_source
    assert "\"official_input_container\": \"DecisionContext.metadata\"" in consumer_contract_source
    assert "\"scope\": \"setup_naming_only\"" in consumer_contract_source
    assert "\"scope\": \"canonical_archetype_to_setup_mapping_only\"" in consumer_contract_source
    assert "\"scope\": \"canonical_consumer_action_block_reasons\"" in consumer_contract_source
    assert "\"scope\": \"execution_guard_only\"" in consumer_contract_source
    assert "\"scope\": \"canonical_exit_handoff_from_entry_consumer\"" in consumer_contract_source
    assert "\"scope\": \"canonical_re_entry_policy_from_consumer_handoff\"" in consumer_contract_source
    assert "\"scope\": \"consumer_audit_logging_only\"" in consumer_contract_source
    assert "\"scope\": \"consumer_regression_lock_only\"" in consumer_contract_source
    assert "\"scope\": \"canonical_consumer_freeze_and_handoff_only\"" in consumer_contract_source
    assert "\"scope\": \"observe_confirm_consumer_resolution_freeze\"" in consumer_contract_source
    assert "\"scope\": \"consumer_policy_overlay_input_only\"" in consumer_contract_source
    assert "resolve_consumer_handoff_payload" in setup_detector_source
    assert "resolve_setup_mapping" in setup_detector_source
    assert "resolve_consumer_observe_confirm_input" in entry_service_source
    assert "resolve_consumer_handoff_payload" in entry_service_source
    assert "resolve_consumer_layer_mode_policy_resolution" in entry_service_source
    assert "ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1" in entry_service_source
    assert "classify_entry_guard_reason" in entry_service_source
    assert "consumer_archetype_id" in entry_service_source
    assert "consumer_guard_result" in entry_service_source
    assert "consumer_input_observe_confirm_field" in entry_service_source
    assert "resolve_consumer_observe_confirm_resolution" in entry_service_source
    assert "consumer_block_reason" in entry_service_source
    assert "CONSUMER_TEST_CONTRACT_V1" in entry_service_source
    assert "CONSUMER_FREEZE_HANDOFF_V1" in entry_service_source
    assert "LAYER_MODE_MODE_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_LAYER_INVENTORY_V1" in entry_service_source
    assert "LAYER_MODE_DEFAULT_POLICY_V1" in entry_service_source
    assert "LAYER_MODE_DUAL_WRITE_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_INFLUENCE_SEMANTICS_V1" in entry_service_source
    assert "LAYER_MODE_APPLICATION_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_SCOPE_CONTRACT_V1" in entry_service_source
    assert "build_layer_mode_effective_metadata" in entry_service_source
    assert "build_layer_mode_influence_metadata" in entry_service_source
    assert "build_layer_mode_application_metadata" in entry_service_source
    assert "build_layer_mode_identity_guard_metadata" in entry_service_source
    assert "build_layer_mode_policy_overlay_metadata" in entry_service_source
    assert "build_layer_mode_logging_replay_metadata" in entry_service_source
    assert "LAYER_MODE_TEST_CONTRACT_V1" in entry_service_source
    assert "LAYER_MODE_FREEZE_HANDOFF_V1" in entry_service_source
    assert "CONSUMER_SCOPE_CONTRACT_V1" in entry_service_source
    assert "resolve_exit_handoff" in consumer_contract_source
    assert "resolve_re_entry_handoff" in consumer_contract_source
    assert "resolve_consumer_handoff_payload" in consumer_contract_source
    assert "resolve_consumer_layer_mode_policy_resolution" in consumer_contract_source
    assert "resolve_consumer_layer_mode_policy_input" in consumer_contract_source
    assert "LAYER_MODE_TEST_CONTRACT_V1" in layer_mode_contract_source
    assert "LAYER_MODE_FREEZE_HANDOFF_V1" in layer_mode_contract_source
    assert "build_layer_mode_test_projection" in layer_mode_contract_source
    assert "resolve_layer_mode_handoff_payload" in layer_mode_contract_source
    assert "evidence_vector_v1=evidence_vector" in classifier_source
    assert "belief_state_v1=belief_state" in classifier_source
    assert "barrier_state_v1=barrier_state" in classifier_source
    assert "transition_forecast_v1=transition_forecast" in classifier_source
