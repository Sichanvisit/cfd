from types import SimpleNamespace

import backend.services.context_classifier as context_classifier_module
import pandas as pd

from backend.services.consumer_contract import CONSUMER_FREEZE_HANDOFF_V1
from backend.services.consumer_contract import CONSUMER_INPUT_CONTRACT_V1, CONSUMER_SCOPE_CONTRACT_V1
from backend.services.consumer_contract import CONSUMER_LAYER_MODE_INTEGRATION_V1
from backend.services.consumer_contract import CONSUMER_LOGGING_CONTRACT_V1
from backend.services.consumer_contract import CONSUMER_MIGRATION_FREEZE_V1
from backend.services.consumer_contract import CONSUMER_TEST_CONTRACT_V1
from backend.services.layer_mode_contract import (
    LAYER_MODE_APPLICATION_CONTRACT_V1,
    LAYER_MODE_DEFAULT_POLICY_V1,
    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    LAYER_MODE_LAYER_INVENTORY_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_MODE_CONTRACT_V1,
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_SCOPE_CONTRACT_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
)
from backend.services.consumer_contract import ENTRY_GUARD_CONTRACT_V1
from backend.services.consumer_contract import ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1
from backend.services.consumer_contract import EXIT_HANDOFF_CONTRACT_V1
from backend.services.consumer_contract import RE_ENTRY_CONTRACT_V1
from backend.services.consumer_contract import SETUP_MAPPING_CONTRACT_V1
from backend.services.consumer_contract import SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1
from backend.services.context_classifier import ContextClassifier
from backend.services.energy_contract import (
    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
    ENERGY_MIGRATION_DUAL_WRITE_V1,
    ENERGY_SCOPE_CONTRACT_V1,
)
from backend.services.runtime_alignment_contract import RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
from backend.trading.engine.core.models import EnergySnapshot, ObserveConfirmSnapshot, StateVectorV2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_INPUT_CONTRACT_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_ROUTING_POLICY_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_STATE_SEMANTICS_V2
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_SCOPE_CONTRACT_V1
from backend.services.outcome_labeler_contract import (
    OUTCOME_LABELER_MANAGEMENT_LABELS_V1,
    OUTCOME_LABELER_TRANSITION_LABELS_V1,
    OUTCOME_LABEL_POLARITY_VALUES_V1,
    OUTCOME_LABEL_STATUS_VALUES_V1,
)


class _DummySessionMgr:
    def get_session_range(self, *_args, **_kwargs):
        return {"high": 110.0, "low": 90.0}

    def get_position_in_box(self, _session, price):
        if price >= 108.0:
            return "UPPER"
        if price <= 92.0:
            return "LOWER"
        return "MIDDLE"


class _DummyTrendMgr:
    def __init__(self):
        self.add_indicator_calls = 0

    def add_indicators(self, frame):
        self.add_indicator_calls += 1
        out = frame.copy()
        out["bb_20_up"] = 110.0
        out["bb_20_mid"] = 100.0
        out["bb_20_dn"] = 90.0
        return out


class _DummyScorer:
    def __init__(self):
        self.session_mgr = _DummySessionMgr()
        self.trend_mgr = _DummyTrendMgr()


def _build_range_lower_entry_bundle():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "close": [100.0, 99.8, 99.6],
                "high": [100.4, 100.0, 99.8],
                "low": [99.6, 99.4, 99.2],
            }
        ),
        "15M": pd.DataFrame({"time": [1773149400], "close": [90.1], "high": [90.4], "low": [89.8]}),
    }
    result = {
        "regime": {"name": "range", "zone": "lower", "volatility_ratio": 0.85, "spread_ratio": 1.0},
        "components": {"wait_score": 12, "wait_conflict": 4, "wait_noise": 3},
    }
    return classifier.build_entry_context(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=90.01, ask=90.02),
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=90.0,
        sell_s=40.0,
    )


def test_context_classifier_build_preflight_trend_buy_only():
    classifier = ContextClassifier()
    h1 = pd.DataFrame(
        {
            "close": [100.0, 100.3, 100.6, 101.0],
            "high": [100.25, 100.55, 100.85, 101.25],
            "low": [99.8, 100.1, 100.4, 100.8],
        }
    )
    out = classifier.build_preflight_2h(
        symbol="NAS100",
        tick=SimpleNamespace(bid=104.0, ask=104.1),
        df_all={"1H": h1},
        result={"regime": {"spread_ratio": 1.0}},
        buy_s=120.0,
        sell_s=80.0,
    )
    assert out["regime"] == "TREND"
    assert out["allowed_action"] == "BUY_ONLY"


def test_context_classifier_relaxes_btc_trend_upper_extreme_to_both():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "close": [100.0, 100.3, 100.6, 101.0],
                "high": [100.25, 100.55, 100.85, 101.25],
                "low": [99.8, 100.1, 100.4, 100.8],
            }
        ),
        "15M": pd.DataFrame({"time": [1773149400], "close": [109.7], "high": [110.0], "low": [109.0]}),
    }
    result = {
        "regime": {"name": "trend", "zone": "upper", "volatility_ratio": 1.1, "spread_ratio": 1.0},
        "components": {"wait_score": 0, "wait_conflict": 0, "wait_noise": 0},
    }
    bundle = classifier.build_entry_context(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=109.98, ask=109.99),
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=120.0,
        sell_s=70.0,
    )
    ctx = bundle["context"]
    assert ctx.market_mode == "TREND"
    assert ctx.box_state == "UPPER"
    assert ctx.bb_state == "UPPER_EDGE"
    assert ctx.direction_policy == "BOTH"
    assert ctx.metadata["preflight_allowed_action_raw"] == "BUY_ONLY"
    assert ctx.metadata["direction_policy_override_reason"] == "btc_trend_upper_extreme_relax"


def test_context_classifier_relaxes_nas_trend_lower_extreme_to_both():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "close": [100.0, 99.7, 99.3, 98.9],
                "high": [100.2, 99.9, 99.6, 99.2],
                "low": [99.8, 99.4, 99.0, 98.6],
            }
        ),
        "15M": pd.DataFrame({"time": [1773149400], "close": [90.2], "high": [90.5], "low": [89.7]}),
    }
    result = {
        "regime": {"name": "trend", "zone": "lower", "volatility_ratio": 1.1, "spread_ratio": 1.0},
        "components": {"wait_score": 0, "wait_conflict": 0, "wait_noise": 0},
    }
    bundle = classifier.build_entry_context(
        symbol="NAS100",
        tick=SimpleNamespace(bid=90.01, ask=90.02),
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=70.0,
        sell_s=120.0,
    )
    ctx = bundle["context"]
    assert ctx.market_mode == "TREND"
    assert ctx.box_state == "LOWER"
    assert ctx.bb_state == "LOWER_EDGE"
    assert ctx.direction_policy == "BOTH"
    assert ctx.metadata["preflight_allowed_action_raw"] == "SELL_ONLY"
    assert ctx.metadata["direction_policy_override_reason"] == "nas_trend_lower_extreme_relax"


def test_context_classifier_resolves_box_and_bb_state():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame({"high": [110.0], "low": [90.0], "close": [109.0]}),
        "15M": pd.DataFrame({"time": [1773149400], "close": [109.6], "high": [110.0], "low": [109.0]}),
    }
    tick = SimpleNamespace(bid=109.98, ask=109.99)

    box_state = classifier.resolve_h1_box_state(df_all=df_all, tick=tick, scorer=scorer)
    bb_state = classifier.resolve_bb_state(symbol="NAS100", tick=tick, df_all=df_all, scorer=scorer)

    assert box_state == "UPPER"
    assert bb_state == "UPPER_EDGE"


def test_context_classifier_build_entry_context_contains_classified_fields():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "close": [100.0, 99.8, 99.6],
                "high": [100.4, 100.0, 99.8],
                "low": [99.6, 99.4, 99.2],
            }
        ),
        "15M": pd.DataFrame({"time": [1773149400], "close": [90.1], "high": [90.4], "low": [89.8]}),
    }
    result = {
        "regime": {"name": "range", "zone": "lower", "volatility_ratio": 0.85, "spread_ratio": 1.0},
        "components": {"wait_score": 12, "wait_conflict": 4, "wait_noise": 3},
    }
    bundle = classifier.build_entry_context(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=90.01, ask=90.02),
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=90.0,
        sell_s=40.0,
    )
    ctx = bundle["context"]
    assert ctx.phase == "entry"
    assert ctx.market_mode in {"RANGE", "TREND", "SHOCK", "UNKNOWN"}
    assert ctx.box_state == "LOWER"
    assert ctx.bb_state == "LOWER_EDGE"
    assert ctx.volatility_state == "contracting"
    assert "position_snapshot_v2" in ctx.metadata
    assert "position_vector_v2" in ctx.metadata
    assert "position_zones_v2" in ctx.metadata
    assert "position_interpretation_v2" in ctx.metadata
    assert "position_energy_v2" in ctx.metadata
    assert "response_raw_snapshot_v1" in ctx.metadata
    assert "response_vector_v2" in ctx.metadata
    assert "state_raw_snapshot_v1" in ctx.metadata
    assert "state_vector_v2" in ctx.metadata
    assert "evidence_vector_v1" in ctx.metadata
    assert "belief_state_v1" in ctx.metadata
    assert "barrier_state_v1" in ctx.metadata
    assert "forecast_features_v1" in ctx.metadata
    assert "transition_forecast_v1" in ctx.metadata
    assert "trade_management_forecast_v1" in ctx.metadata
    assert "forecast_gap_metrics_v1" in ctx.metadata
    assert "observe_confirm_input_contract_v2" in ctx.metadata
    assert "observe_confirm_migration_dual_write_v1" in ctx.metadata
    assert "observe_confirm_output_contract_v2" in ctx.metadata
    assert "observe_confirm_scope_contract_v1" in ctx.metadata
    assert "consumer_input_contract_v1" in ctx.metadata
    assert "consumer_layer_mode_integration_v1" in ctx.metadata
    assert "consumer_migration_freeze_v1" in ctx.metadata
    assert "consumer_logging_contract_v1" in ctx.metadata
    assert "consumer_test_contract_v1" in ctx.metadata
    assert "consumer_freeze_handoff_v1" in ctx.metadata
    assert "setup_detector_responsibility_contract_v1" in ctx.metadata
    assert "layer_mode_contract_v1" in ctx.metadata
    assert "layer_mode_layer_inventory_v1" in ctx.metadata
    assert "layer_mode_default_policy_v1" in ctx.metadata
    assert "layer_mode_dual_write_contract_v1" in ctx.metadata
    assert "layer_mode_influence_semantics_v1" in ctx.metadata
    assert "layer_mode_application_contract_v1" in ctx.metadata
    assert "layer_mode_identity_guard_contract_v1" in ctx.metadata
    assert "layer_mode_policy_overlay_output_contract_v1" in ctx.metadata
    assert "layer_mode_logging_replay_contract_v1" in ctx.metadata
    assert "layer_mode_test_contract_v1" in ctx.metadata
    assert "layer_mode_freeze_handoff_v1" in ctx.metadata
    assert "layer_mode_scope_contract_v1" in ctx.metadata
    assert "position_snapshot_effective_v1" in ctx.metadata
    assert "response_vector_effective_v1" in ctx.metadata
    assert "state_vector_effective_v1" in ctx.metadata
    assert "evidence_vector_effective_v1" in ctx.metadata
    assert "belief_state_effective_v1" in ctx.metadata
    assert "barrier_state_effective_v1" in ctx.metadata
    assert "forecast_effective_policy_v1" in ctx.metadata
    assert "energy_helper_v2" in ctx.metadata
    assert "energy_scope_contract_v1" in ctx.metadata
    assert "runtime_alignment_scope_contract_v1" in ctx.metadata
    assert "layer_mode_effective_trace_v1" in ctx.metadata
    assert "layer_mode_influence_trace_v1" in ctx.metadata
    assert "layer_mode_application_trace_v1" in ctx.metadata
    assert "layer_mode_identity_guard_trace_v1" in ctx.metadata
    assert "layer_mode_policy_v1" in ctx.metadata
    assert "layer_mode_logging_replay_v1" in ctx.metadata
    assert "setup_mapping_contract_v1" in ctx.metadata
    assert "entry_guard_contract_v1" in ctx.metadata
    assert "entry_service_responsibility_contract_v1" in ctx.metadata
    assert "exit_handoff_contract_v1" in ctx.metadata
    assert "re_entry_contract_v1" in ctx.metadata
    assert "consumer_scope_contract_v1" in ctx.metadata
    assert "semantic_foundation_contract_v1" in ctx.metadata
    assert "forecast_calibration_contract_v1" in ctx.metadata
    assert "outcome_labeler_scope_contract_v1" in ctx.metadata
    assert "build_entry_context_profile_v1" in ctx.metadata
    assert "engine_context_snapshot_profile_v1" in ctx.metadata
    assert "position_vector_v1" not in ctx.metadata
    assert "response_vector_v1" not in ctx.metadata
    assert "state_vector_v1" not in ctx.metadata
    assert "energy_snapshot_v1" not in ctx.metadata
    assert ctx.metadata["build_entry_context_profile_v1"]["stage_timings_ms"]["build_engine_context_snapshot"] >= 0.0
    assert ctx.metadata["engine_context_snapshot_profile_v1"]["stage_timings_ms"]["m15_indicator_context"] >= 0.0
    assert ctx.metadata["position_snapshot_v2"]["vector"] == ctx.metadata["position_vector_v2"]
    assert ctx.metadata["position_snapshot_v2"]["zones"] == ctx.metadata["position_zones_v2"]
    assert ctx.metadata["position_snapshot_v2"]["interpretation"] == ctx.metadata["position_interpretation_v2"]
    assert ctx.metadata["position_snapshot_v2"]["energy"] == ctx.metadata["position_energy_v2"]
    assert bundle["energy_snapshot"].metadata["position_primary_label"] == ctx.metadata["position_interpretation_v2"]["primary_label"]
    assert bundle["energy_snapshot"].metadata["position_secondary_context_label"] == ctx.metadata["position_interpretation_v2"]["secondary_context_label"]
    assert ctx.metadata["prs_log_contract_v2"]["canonical_position_field"] == "position_snapshot_v2"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_response_field"] == "response_vector_v2"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_state_field"] == "state_vector_v2"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_evidence_field"] == "evidence_vector_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_belief_field"] == "belief_state_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_barrier_field"] == "barrier_state_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_forecast_features_field"] == "forecast_features_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_transition_forecast_field"] == "transition_forecast_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_trade_management_forecast_field"] == "trade_management_forecast_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_energy_field"] == "energy_helper_v2"
    assert ctx.metadata["prs_log_contract_v2"]["energy_migration_guard_field"] == "energy_migration_guard_v1"
    assert ctx.metadata["prs_log_contract_v2"]["energy_scope_contract_field"] == "energy_scope_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["runtime_alignment_scope_contract_field"] == (
        "runtime_alignment_scope_contract_v1"
    )

    assert ctx.metadata["prs_log_contract_v2"]["compatibility_energy_runtime_field"] == "energy_snapshot"
    assert ctx.metadata["runtime_alignment_scope_contract_v1"]["contract_version"] == (
        RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["contract_version"]
    )
    assert ctx.metadata["runtime_alignment_scope_contract_v1"]["scope"] == "runtime_alignment_hardening_only"
    assert ctx.metadata["runtime_alignment_scope_contract_v1"]["completed_definitions"] == [
        "14.0_scope_freeze",
        "14.1_observe_confirm_legacy_energy_detach",
        "14.2_observe_confirm_semantic_routing_hardening",
        "14.3_entry_service_consumer_stack_activation",
        "14.4_wait_engine_hint_activation",
        "14.5_truthful_consumer_usage_logging",
        "14.6_compatibility_migration_guard",
        "14.7_test_hardening",
        "14.8_docs_handoff_refreeze",
    ]
    assert ctx.metadata["runtime_alignment_scope_contract_v1"]["scope_freeze_v1"]["priority_order"] == [
        {"order": 1, "focus": "identity_ownership", "owner": "observe_confirm"},
        {"order": 2, "focus": "live_consumer_wiring", "owner": "consumer"},
        {"order": 3, "focus": "truthful_logging", "owner": "energy_logging_replay"},
    ]
    assert ctx.metadata["runtime_alignment_scope_contract_v1"]["scope_freeze_v1"]["non_goals"] == [
        "introduce a new semantic layer",
        "redefine the semantic foundation",
        "promote net_utility into a direct order gate",
        "remove compatibility bridges before runtime alignment is verified",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["scope_freeze_v1"]["contract_version"] == "energy_scope_freeze_v1"
    assert ctx.metadata["energy_scope_contract_v1"]["scope_freeze_v1"]["semantic_layer_owner"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["scope_freeze_v1"]["identity_field_mutation_allowed"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["scope_freeze_v1"]["selected_side_semantics"] == (
        "utility_only_not_semantic_side"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["input_contract_v1"]["required_fields"] == [
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["input_contract_v1"]["optional_fields"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["input_contract_v1"]["allowed_observe_confirm_subfields"] == [
        "action",
        "side",
    ]
    assert "response_raw_snapshot_v1" in ctx.metadata["energy_scope_contract_v1"]["input_contract_v1"][
        "forbidden_direct_inputs"
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"]["exact_top_level_shape_required"] is True
    assert ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"]["optional_top_level_fields"] == []
    assert ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"]["top_level_field_count"] == 10
    assert ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"]["metadata_policy"]["role"] == (
        "audit_trace_only"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"]["metadata_policy"][
        "semantic_label_emission_allowed"
    ] is False
    assert "setup_label" in ctx.metadata["energy_scope_contract_v1"]["output_contract_v1"][
        "forbidden_semantic_label_like_outputs"
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["composition_semantics_v1"]["component_roles"] == {
        "evidence": "setup_strength_support",
        "belief": "persistence_and_continuation_bias",
        "barrier": "suppression_and_risk_pressure",
        "forecast": "forward_support_or_confirm_wait_modulation",
    }
    assert ctx.metadata["energy_scope_contract_v1"]["composition_semantics_v1"]["sign_convention"] == {
        "support_terms": "+",
        "suppression_terms": "-",
        "evidence": "+",
        "belief": "+",
        "barrier": "-",
        "forecast": "+",
    }
    assert ctx.metadata["energy_scope_contract_v1"]["composition_semantics_v1"]["support_components"] == [
        "evidence",
        "belief",
        "forecast",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["composition_semantics_v1"]["suppression_components"] == [
        "barrier",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["consumer_usage_v1"]["canonical_energy_field"] == (
        "energy_helper_v2"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["consumer_usage_v1"]["component_usage"][2]["component"] == (
        "WaitEngine"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["consumer_usage_v1"]["component_usage"][2][
        "allowed_energy_fields"
    ] == [
        "action_readiness",
        "soft_block_hint",
        "metadata.utility_hints.wait_vs_enter_hint",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["bridge_position"] == (
        "post_layer_mode_effective_outputs"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["helper_identity"] == (
        "post_layer_mode_utility_bridge_helper"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["effective_world_required"] is True
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["reads_raw_semantics"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["reads_effective_semantics"] is True
    assert ctx.metadata["energy_scope_contract_v1"]["layer_mode_integration_v1"]["official_build_order"] == [
        "build_layer_mode_effective_metadata",
        "build_energy_helper_v2",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["utility_bridge_v1"]["bridge_strategy"] == (
        "hint_first_no_direct_order_decision"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["utility_bridge_v1"]["direct_net_utility_use_allowed"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["utility_bridge_v1"]["net_utility_role"] == (
        "summary_only_not_direct_order_gate"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["utility_bridge_v1"]["canonical_bridge_hints"] == [
        "confidence_adjustment_hint",
        "soft_block_hint",
        "metadata.utility_hints.priority_hint",
        "metadata.utility_hints.wait_vs_enter_hint",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["identity_non_ownership_v1"]["energy_is_identity_owner"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["identity_non_ownership_v1"]["canonical_identity_owner"] == (
        "observe_confirm_v2"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["identity_non_ownership_v1"]["identity_creation_allowed"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["identity_non_ownership_v1"]["identity_mutation_allowed"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["identity_non_ownership_v1"]["allowed_context_reads"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["freeze_handoff_v1"]["status"] == (
        "freeze_complete_ready_for_handoff"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["freeze_handoff_v1"]["layer_position"] == {
        "energy_is_independent_semantic_layer": False,
        "energy_reads_effective_semantic_outputs": True,
        "energy_runtime_role": "post_layer_mode_helper",
    }
    assert ctx.metadata["energy_scope_contract_v1"]["freeze_handoff_v1"]["ownership_handoff"] == {
        "identity_owner": "observe_confirm_v2",
        "policy_owner": "layer_mode",
        "utility_hint_owner": "energy_helper_v2",
    }
    assert ctx.metadata["energy_scope_contract_v1"]["freeze_handoff_v1"]["consumer_read_stack"] == [
        "ObserveConfirm.identity",
        "LayerMode.policy",
        "Energy.utility_hint",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["freeze_handoff_v1"]["future_absorption_path"] == {
        "allowed": True,
        "current_runtime_surface": "energy_helper_v2",
        "legacy_engine_name": "energy_engine",
        "target_direction": "utility_or_decision_helper",
        "migration_style": "gradual_absorption_without_semantic_reownership",
    }
    assert ctx.metadata["energy_scope_contract_v1"]["role_contract_v1"]["official_role"] == (
        "utility_compression_helper"
    )
    assert ctx.metadata["energy_scope_contract_v1"]["role_contract_v1"]["semantic_question_owner"] == "semantic_layer"
    assert ctx.metadata["energy_scope_contract_v1"]["role_contract_v1"]["utility_question_owner"] == "energy_helper"
    assert ctx.metadata["energy_scope_contract_v1"]["role_contract_v1"]["owns_situation_interpretation"] is False
    assert ctx.metadata["energy_scope_contract_v1"]["role_contract_v1"]["owns_execution_pressure_compression"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["helper_only"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["semantic_layer_owner"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["identity_field_mutation_allowed"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["selected_side_is_identity_side"] is False
    assert "side" in ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["forbidden_output_fields_absent"]
    assert "archetype_id" in ctx.metadata["energy_helper_v2"]["metadata"]["scope_freeze"]["forbidden_output_fields_absent"]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_source_fields"]["observe_confirm_v2.action"] is True
    assert (
        ctx.metadata["energy_helper_v2"]["metadata"]["input_source_fields"]["observe_confirm_v2.side"]
        is bool(str(ctx.metadata["observe_confirm_v2"]["side"] or "").strip())
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"]["allowed_observe_confirm_subfields"] == [
        "action",
        "side",
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"]["reads_only_contract_inputs"] is True
    assert "response_raw_snapshot_v1" in ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"][
        "ignored_available_direct_inputs"
    ]
    assert "response_vector_v2" in ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"][
        "ignored_available_direct_inputs"
    ]
    assert "state_raw_snapshot_v1" in ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"][
        "ignored_available_direct_inputs"
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"]["bridge_position"] == (
        "post_layer_mode_effective_outputs"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"]["helper_identity"] == (
        "post_layer_mode_utility_bridge_helper"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "effective_world_required"
    ] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "reads_raw_semantics"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "reads_effective_semantics"
    ] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "raw_semantic_output_allowed"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "pre_layer_mode_semantic_attachment_allowed"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "effective_fields_present"
    ] == [
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["layer_mode_integration_freeze"][
        "official_build_order"
    ] == [
        "build_layer_mode_effective_metadata",
        "build_energy_helper_v2",
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"]["bridge_strategy"] == (
        "hint_first_no_direct_order_decision"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"][
        "direct_net_utility_use_allowed"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"]["net_utility_role"] == (
        "summary_only_not_direct_order_gate"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"]["canonical_bridge_hints"] == [
        "confidence_adjustment_hint",
        "soft_block_hint",
        "metadata.utility_hints.priority_hint",
        "metadata.utility_hints.wait_vs_enter_hint",
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"]["hint_payload"] == {
        "confidence_adjustment_hint": dict(ctx.metadata["energy_helper_v2"]["confidence_adjustment_hint"]),
        "soft_block_hint": dict(ctx.metadata["energy_helper_v2"]["soft_block_hint"]),
        "priority_hint": ctx.metadata["energy_helper_v2"]["metadata"]["utility_hints"]["priority_hint"],
        "wait_vs_enter_hint": ctx.metadata["energy_helper_v2"]["metadata"]["utility_hints"]["wait_vs_enter_hint"],
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["utility_bridge_freeze"][
        "net_utility_available_for_audit_only"
    ] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["observe_confirm_context"]["allowed_subfields_only"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["official_role"] == (
        "utility_compression_helper"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["semantic_question_owner"] == "semantic_layer"
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["utility_question_owner"] == "energy_helper"
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["owns_situation_interpretation"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["role_freeze"]["owns_execution_pressure_compression"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["canonical_output_field"] == (
        "energy_helper_v2"
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["exact_top_level_shape_required"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["optional_top_level_fields"] == []
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["metadata_role"] == "audit_trace_only"
    assert ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"]["semantic_label_emission_allowed"] is False
    assert "setup_id" in ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"][
        "forbidden_semantic_label_like_fields_absent"
    ]
    assert "archetype_id" in ctx.metadata["energy_helper_v2"]["metadata"]["output_freeze"][
        "forbidden_semantic_label_like_fields_absent"
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["composition_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["composition_freeze"]["component_roles"] == {
        "evidence": "setup_strength_support",
        "belief": "persistence_and_continuation_bias",
        "barrier": "suppression_and_risk_pressure",
        "forecast": "forward_support_or_confirm_wait_modulation",
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["composition_freeze"]["sign_convention"] == {
        "support_terms": "+",
        "suppression_terms": "-",
        "evidence": "+",
        "belief": "+",
        "barrier": "-",
        "forecast": "+",
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["composition_freeze"]["output_direction_rules"] == {
        "continuation_support": "+",
        "reversal_support": "+",
        "forecast_support": "+",
        "suppression_pressure": "-",
        "action_readiness": "mixed_support_minus_suppression",
        "net_utility": "mixed_support_minus_suppression",
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"]["applied"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "energy_is_identity_owner"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "canonical_identity_owner"
    ] == "observe_confirm_v2"
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "identity_creation_allowed"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "identity_mutation_allowed"
    ] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "allowed_context_reads"
    ] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_non_ownership_freeze"][
        "identity_fields_absent_from_output"
    ] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    assert ctx.metadata["prs_log_contract_v2"]["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert ctx.metadata["prs_log_contract_v2"]["compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert ctx.metadata["prs_log_contract_v2"]["observe_confirm_input_contract_field"] == "observe_confirm_input_contract_v2"
    assert ctx.metadata["prs_log_contract_v2"]["observe_confirm_migration_contract_field"] == "observe_confirm_migration_dual_write_v1"
    assert ctx.metadata["prs_log_contract_v2"]["observe_confirm_output_contract_field"] == "observe_confirm_output_contract_v2"
    assert ctx.metadata["prs_log_contract_v2"]["observe_confirm_scope_contract_field"] == "observe_confirm_scope_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_input_contract_field"] == "consumer_input_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_layer_mode_integration_field"] == "consumer_layer_mode_integration_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_migration_freeze_field"] == "consumer_migration_freeze_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_migration_guard_field"] == "consumer_migration_guard_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_logging_contract_field"] == "consumer_logging_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_test_contract_field"] == "consumer_test_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_freeze_handoff_field"] == "consumer_freeze_handoff_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_contract_field"] == "layer_mode_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_layer_inventory_field"] == "layer_mode_layer_inventory_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_default_policy_field"] == "layer_mode_default_policy_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_dual_write_contract_field"] == "layer_mode_dual_write_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_influence_semantics_field"] == "layer_mode_influence_semantics_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_application_contract_field"] == "layer_mode_application_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_identity_guard_contract_field"] == "layer_mode_identity_guard_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_policy_overlay_output_contract_field"] == "layer_mode_policy_overlay_output_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_logging_replay_contract_field"] == "layer_mode_logging_replay_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_test_contract_field"] == "layer_mode_test_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_freeze_handoff_field"] == "layer_mode_freeze_handoff_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_scope_contract_field"] == "layer_mode_scope_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_position_effective_field"] == "position_snapshot_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_response_effective_field"] == "response_vector_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_state_effective_field"] == "state_vector_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_evidence_effective_field"] == "evidence_vector_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_belief_effective_field"] == "belief_state_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_barrier_effective_field"] == "barrier_state_effective_v1"
    assert ctx.metadata["prs_log_contract_v2"]["canonical_forecast_effective_field"] == "forecast_effective_policy_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_effective_trace_field"] == "layer_mode_effective_trace_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_influence_trace_field"] == "layer_mode_influence_trace_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_application_trace_field"] == "layer_mode_application_trace_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_policy_output_field"] == "layer_mode_policy_v1"
    assert ctx.metadata["prs_log_contract_v2"]["layer_mode_logging_replay_field"] == "layer_mode_logging_replay_v1"
    assert ctx.metadata["prs_log_contract_v2"]["setup_detector_responsibility_contract_field"] == "setup_detector_responsibility_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["setup_mapping_contract_field"] == "setup_mapping_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["entry_guard_contract_field"] == "entry_guard_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["entry_service_responsibility_contract_field"] == "entry_service_responsibility_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["exit_handoff_contract_field"] == "exit_handoff_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["re_entry_contract_field"] == "re_entry_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["consumer_scope_contract_field"] == "consumer_scope_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["semantic_foundation_contract_field"] == "semantic_foundation_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["forecast_calibration_contract_field"] == "forecast_calibration_contract_v1"
    assert ctx.metadata["prs_log_contract_v2"]["outcome_labeler_scope_contract_field"] == "outcome_labeler_scope_contract_v1"
    assert ctx.metadata["observe_confirm_input_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_INPUT_CONTRACT_V2["contract_version"]
    assert [item["field"] for item in ctx.metadata["observe_confirm_input_contract_v2"]["semantic_input_fields"]] == [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ]
    assert "response_raw_snapshot_v1" in ctx.metadata["observe_confirm_input_contract_v2"]["forbidden_direct_inputs"]
    assert ctx.metadata["observe_confirm_migration_dual_write_v1"]["contract_version"] == OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1["contract_version"]
    assert ctx.metadata["observe_confirm_migration_dual_write_v1"]["canonical_output_field_v2"] == "observe_confirm_v2"
    assert ctx.metadata["observe_confirm_migration_dual_write_v1"]["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert ctx.metadata["observe_confirm_output_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["contract_version"]
    assert ctx.metadata["observe_confirm_output_contract_v2"]["canonical_output_field"] == "observe_confirm_v2"
    assert ctx.metadata["observe_confirm_output_contract_v2"]["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert ctx.metadata["observe_confirm_output_contract_v2"]["state_values"] == [
        "OBSERVE",
        "CONFIRM",
        "CONFLICT_OBSERVE",
        "NO_TRADE",
        "INVALIDATED",
    ]
    assert ctx.metadata["observe_confirm_output_contract_v2"]["action_values"] == ["WAIT", "BUY", "SELL", "NONE"]
    assert ctx.metadata["observe_confirm_output_contract_v2"]["side_values"] == ["BUY", "SELL", ""]
    assert ctx.metadata["observe_confirm_output_contract_v2"]["metadata_contract"]["required_fields"] == [
        "raw_contributions",
        "effective_contributions",
        "winning_evidence",
        "blocked_reason",
    ]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["contract_version"] == OBSERVE_CONFIRM_SCOPE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["scope"] == "semantic_archetype_routing_only"
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["canonical_output_field"] == "observe_confirm_v2"
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert "setup naming" in ctx.metadata["observe_confirm_scope_contract_v1"]["non_responsibilities"]
    assert "entry guard or execution gating" in ctx.metadata["observe_confirm_scope_contract_v1"]["non_responsibilities"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["input_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_INPUT_CONTRACT_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["output_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["migration_dual_write_v1"]["contract_version"] == OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["state_semantics_v2"]["contract_version"] == OBSERVE_CONFIRM_STATE_SEMANTICS_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["archetype_taxonomy_v2"]["contract_version"] == OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["invalidation_taxonomy_v2"]["contract_version"] == OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["management_profile_taxonomy_v2"]["contract_version"] == OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["routing_policy_v2"]["contract_version"] == OBSERVE_CONFIRM_ROUTING_POLICY_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["confidence_semantics_v2"]["contract_version"] == OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2["contract_version"]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["action_side_semantics_v2"]["contract_version"] == OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2["contract_version"]
    assert ctx.metadata["consumer_input_contract_v1"]["contract_version"] == CONSUMER_INPUT_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_input_contract_v1"]["official_input_container"] == "DecisionContext.metadata"
    assert ctx.metadata["consumer_input_contract_v1"]["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert ctx.metadata["consumer_input_contract_v1"]["canonical_energy_field"] == "energy_helper_v2"
    assert "metadata.layer_mode_policy_v1" in ctx.metadata["consumer_input_contract_v1"]["allowed_decision_context_fields"]
    assert "prior_entry_archetype_id" in ctx.metadata["consumer_input_contract_v1"]["allowed_non_semantic_runtime_fields"]
    assert "re_entry_cooldown_active" in ctx.metadata["consumer_input_contract_v1"]["allowed_non_semantic_runtime_fields"]
    assert "response_vector_v2" in ctx.metadata["consumer_input_contract_v1"]["forbidden_direct_inputs"]
    assert ctx.metadata["consumer_input_contract_v1"]["energy_usage_freeze_v1"]["contract_version"] == (
        "consumer_energy_usage_freeze_v1"
    )
    assert ctx.metadata["consumer_input_contract_v1"]["energy_usage_freeze_v1"]["direct_net_utility_use_allowed"] is False
    assert ctx.metadata["consumer_input_contract_v1"]["energy_usage_freeze_v1"]["component_usage"][2]["component"] == (
        "WaitEngine"
    )
    assert ctx.metadata["consumer_layer_mode_integration_v1"]["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert ctx.metadata["consumer_layer_mode_integration_v1"]["canonical_policy_field"] == "layer_mode_policy_v1"
    assert ctx.metadata["consumer_layer_mode_integration_v1"]["canonical_identity_field"] == "observe_confirm_v2"
    assert ctx.metadata["consumer_migration_freeze_v1"]["contract_version"] == CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
    assert ctx.metadata["consumer_migration_freeze_v1"]["read_order"] == [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ]
    assert ctx.metadata["consumer_migration_guard_v1"]["compatibility_role"] == "migration_bridge_only"
    assert ctx.metadata["consumer_migration_guard_v1"]["used_compatibility_fallback_v1"] is False
    assert ctx.metadata["consumer_migration_guard_v1"]["identity_ownership_preserved"] is True
    assert ctx.metadata["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_logging_contract_v1"]["guard_result_values"] == ["PASS", "SEMANTIC_NON_ACTION", "EXECUTION_BLOCK"]
    assert ctx.metadata["consumer_test_contract_v1"]["contract_version"] == CONSUMER_TEST_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_test_contract_v1"]["required_behavior_axes"][0]["id"] == "setup_detector_naming_only"
    assert ctx.metadata["consumer_freeze_handoff_v1"]["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]
    assert ctx.metadata["consumer_freeze_handoff_v1"]["official_handoff_helper"] == "resolve_consumer_handoff_payload"
    assert ctx.metadata["layer_mode_contract_v1"]["contract_version"] == LAYER_MODE_MODE_CONTRACT_V1["contract_version"]
    assert [item["mode"] for item in ctx.metadata["layer_mode_contract_v1"]["canonical_modes"]] == ["shadow", "assist", "enforce"]
    assert ctx.metadata["layer_mode_layer_inventory_v1"]["contract_version"] == LAYER_MODE_LAYER_INVENTORY_V1["contract_version"]
    assert ctx.metadata["layer_mode_layer_inventory_v1"]["layer_order"] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    assert ctx.metadata["layer_mode_default_policy_v1"]["contract_version"] == LAYER_MODE_DEFAULT_POLICY_V1["contract_version"]
    assert ctx.metadata["layer_mode_default_policy_v1"]["policy_rows"][2]["target_mode_sequence"] == ["assist", "enforce"]
    assert ctx.metadata["layer_mode_default_policy_v1"]["policy_rows"][4]["current_effective_default_mode"] == "shadow"
    assert ctx.metadata["layer_mode_dual_write_contract_v1"]["contract_version"] == LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_influence_semantics_v1"]["contract_version"] == LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"]
    assert ctx.metadata["layer_mode_application_contract_v1"]["contract_version"] == LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_test_contract_v1"]["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_test_contract_v1"]["official_test_helper"] == "build_layer_mode_test_projection"
    assert ctx.metadata["layer_mode_freeze_handoff_v1"]["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert ctx.metadata["layer_mode_freeze_handoff_v1"]["official_handoff_helper"] == "resolve_layer_mode_handoff_payload"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["contract_version"] == LAYER_MODE_SCOPE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["compute_disable_allowed"] is False
    assert ctx.metadata["layer_mode_scope_contract_v1"]["layer_inventory_v1"]["contract_version"] == LAYER_MODE_LAYER_INVENTORY_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["default_mode_policy_v1"]["contract_version"] == LAYER_MODE_DEFAULT_POLICY_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["dual_write_contract_v1"]["contract_version"] == LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["influence_semantics_v1"]["contract_version"] == LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["application_contract_v1"]["contract_version"] == LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["test_contract_v1"]["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["freeze_handoff_v1"]["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["policy_overlay_output_field"] == "layer_mode_policy_v1"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert ctx.metadata["layer_mode_scope_contract_v1"]["raw_output_policy"]["logging_replay_field"] == "layer_mode_logging_replay_v1"
    assert ctx.metadata["position_snapshot_effective_v1"] == ctx.metadata["position_snapshot_v2"]
    assert ctx.metadata["response_vector_effective_v1"] == ctx.metadata["response_vector_v2"]
    assert ctx.metadata["state_vector_effective_v1"] == ctx.metadata["state_vector_v2"]
    assert ctx.metadata["evidence_vector_effective_v1"] == ctx.metadata["evidence_vector_v1"]
    assert ctx.metadata["belief_state_effective_v1"] == ctx.metadata["belief_state_v1"]
    assert ctx.metadata["barrier_state_effective_v1"] == ctx.metadata["barrier_state_v1"]
    assert ctx.metadata["forecast_effective_policy_v1"]["policy_overlay_applied"] is True
    assert ctx.metadata["forecast_effective_policy_v1"]["utility_overlay_applied"] is True
    assert ctx.metadata["forecast_effective_policy_v1"]["current_effective_mode"] == "assist"
    assert "raw_effective_delta_v1" in ctx.metadata["forecast_effective_policy_v1"]
    assert ctx.metadata["layer_mode_effective_trace_v1"]["layers"][0]["effective_equals_raw"] is True
    assert ctx.metadata["layer_mode_influence_trace_v1"]["layers"][0]["current_effective_mode"] == "enforce"
    assert next(row for row in ctx.metadata["layer_mode_influence_trace_v1"]["layers"] if row["layer"] == "Barrier")["active_effects"] == [
        "metadata_log_only",
        "trace_only",
    ]
    assert next(row for row in ctx.metadata["layer_mode_influence_trace_v1"]["layers"] if row["layer"] == "State")["active_effects"] == [
        "confidence_modulation",
        "reason_annotation",
        "soft_warning",
    ]
    assert next(row for row in ctx.metadata["layer_mode_application_trace_v1"]["layers"] if row["layer"] == "Position")["application_state"] == "enforce_active"
    assert next(row for row in ctx.metadata["layer_mode_application_trace_v1"]["layers"] if row["layer"] == "State")["application_state"] == "assist_active"
    assert next(row for row in ctx.metadata["layer_mode_application_trace_v1"]["layers"] if row["layer"] == "Forecast")["application_state"] == "assist_active"
    assert next(row for row in ctx.metadata["layer_mode_application_trace_v1"]["layers"] if row["layer"] == "Forecast")["forbidden_application"] == [
        "archetype_rewrite",
        "side_rewrite",
        "execution_veto",
    ]
    assert ctx.metadata["layer_mode_identity_guard_trace_v1"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert ctx.metadata["layer_mode_identity_guard_trace_v1"]["routing_policy_contract_ref"] == "observe_confirm_routing_policy_v2"
    assert ctx.metadata["layer_mode_identity_guard_trace_v1"]["confidence_semantics_contract_ref"] == "observe_confirm_confidence_semantics_v2"
    assert next(row for row in ctx.metadata["layer_mode_identity_guard_trace_v1"]["layers"] if row["layer"] == "Belief")["guard_active"] is True
    assert next(row for row in ctx.metadata["layer_mode_identity_guard_trace_v1"]["layers"] if row["layer"] == "Barrier")["protected_fields"] == ["archetype_id", "side"]
    assert next(row for row in ctx.metadata["layer_mode_identity_guard_trace_v1"]["layers"] if row["layer"] == "Forecast")["forbidden_adjustments"] == [
        "archetype_rewrite",
        "side_rewrite",
        "setup_rename",
        "execution_veto",
    ]
    assert ctx.metadata["layer_mode_policy_v1"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert ctx.metadata["layer_mode_policy_v1"]["overlay_execution_state"] == "bridge_ready_no_runtime_delta"
    assert next(row for row in ctx.metadata["layer_mode_policy_v1"]["effective_influences"] if row["layer"] == "State")["active_effects"] == [
        "confidence_modulation",
        "reason_annotation",
        "soft_warning",
    ]
    assert next(row for row in ctx.metadata["layer_mode_policy_v1"]["mode_decision_trace"]["layers"] if row["layer"] == "Forecast")["protected_fields"] == [
        "archetype_id",
        "side",
    ]
    assert ctx.metadata["layer_mode_logging_replay_v1"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert ctx.metadata["layer_mode_logging_replay_v1"]["configured_modes"][0]["layer"] == "Position"
    assert ctx.metadata["layer_mode_logging_replay_v1"]["raw_result_fields"][0]["fields"] == ["position_snapshot_v2"]
    assert ctx.metadata["layer_mode_logging_replay_v1"]["effective_result_fields"][-1]["fields"] == ["forecast_effective_policy_v1"]
    assert ctx.metadata["layer_mode_logging_replay_v1"]["block_suppress_reasons"]["policy_suppressed_reasons"] == []
    assert ctx.metadata["setup_detector_responsibility_contract_v1"]["contract_version"] == SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["setup_detector_responsibility_contract_v1"]["scope"] == "setup_naming_only"
    assert ctx.metadata["setup_detector_responsibility_contract_v1"]["official_input_fields"] == [
        "archetype_id",
        "side",
        "reason",
        "market_mode",
    ]
    assert ctx.metadata["setup_detector_responsibility_contract_v1"]["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert ctx.metadata["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert ctx.metadata["setup_mapping_contract_v1"]["canonical_mapping"][0]["archetype_id"] == "upper_reject_sell"
    assert ctx.metadata["setup_mapping_contract_v1"]["canonical_mapping"][4]["allowed_setup_ids"] == [
        "range_lower_reversal_buy",
        "trend_pullback_buy",
    ]
    assert ctx.metadata["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert ctx.metadata["entry_guard_contract_v1"]["reason_registry"][0]["reason"] == "observe_confirm_missing"
    assert ctx.metadata["entry_guard_contract_v1"]["reason_registry"][3]["reason"] == "opposite_position_lock"
    assert ctx.metadata["entry_service_responsibility_contract_v1"]["contract_version"] == ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["entry_service_responsibility_contract_v1"]["scope"] == "execution_guard_only"
    assert "setup_id" in ctx.metadata["entry_service_responsibility_contract_v1"]["official_input_fields"]
    assert "energy_helper_v2.action_readiness" in ctx.metadata["entry_service_responsibility_contract_v1"][
        "official_input_fields"
    ]
    assert "semantic confirm reversal to the opposite side" in ctx.metadata["entry_service_responsibility_contract_v1"]["non_responsibilities"]
    assert ctx.metadata["entry_service_responsibility_contract_v1"]["energy_helper_policy"]["identity_decision_allowed"] is False
    assert ctx.metadata["exit_handoff_contract_v1"]["contract_version"] == EXIT_HANDOFF_CONTRACT_V1["contract_version"]
    assert ctx.metadata["exit_handoff_contract_v1"]["energy_helper_policy"]["identity_decision_allowed"] is False
    assert ctx.metadata["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["re_entry_contract_v1"]["required_current_state"]["same_archetype_confirm_required"] is True
    assert ctx.metadata["re_entry_contract_v1"]["energy_helper_policy"]["identity_decision_allowed"] is False
    assert ctx.metadata["consumer_scope_contract_v1"]["contract_version"] == CONSUMER_SCOPE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["canonical_input_field"] == "observe_confirm_v2"
    assert ctx.metadata["consumer_scope_contract_v1"]["energy_usage_freeze_v1"]["contract_version"] == (
        "consumer_energy_usage_freeze_v1"
    )
    assert ctx.metadata["consumer_scope_contract_v1"]["energy_usage_freeze_v1"]["direct_net_utility_use_allowed"] is False
    assert ctx.metadata["consumer_scope_contract_v1"]["layer_mode_integration_v1"]["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["exit_handoff_contract_v1"]["contract_version"] == EXIT_HANDOFF_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["migration_freeze_v1"]["contract_version"] == CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["consumer_test_contract_v1"]["contract_version"] == CONSUMER_TEST_CONTRACT_V1["contract_version"]
    assert ctx.metadata["consumer_scope_contract_v1"]["consumer_freeze_handoff_v1"]["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]
    assert "semantic layer reinterpretation" in ctx.metadata["consumer_scope_contract_v1"]["non_responsibilities"]
    assert "energy helper identity promotion" in ctx.metadata["consumer_scope_contract_v1"]["non_responsibilities"]
    assert ctx.metadata["consumer_scope_contract_v1"]["consumer_components"][2]["component"] == "WaitEngine"
    assert ctx.metadata["consumer_scope_contract_v1"]["consumer_boundary"]["wait_engine"].startswith(
        "Compares enter versus wait"
    )
    assert [item["value"] for item in ctx.metadata["observe_confirm_scope_contract_v1"]["state_semantics_v2"]["allowed_values"]] == [
        "OBSERVE",
        "CONFIRM",
        "CONFLICT_OBSERVE",
        "NO_TRADE",
        "INVALIDATED",
    ]
    assert [item["archetype_id"] for item in ctx.metadata["observe_confirm_scope_contract_v1"]["archetype_taxonomy_v2"]["core_set"]] == [
        "upper_reject_sell",
        "upper_break_buy",
        "lower_hold_buy",
        "lower_break_sell",
        "mid_reclaim_buy",
        "mid_lose_sell",
    ]
    assert [(item["archetype_id"], item["invalidation_id"]) for item in ctx.metadata["observe_confirm_scope_contract_v1"]["invalidation_taxonomy_v2"]["canonical_mapping"]] == [
        ("upper_reject_sell", "upper_break_reclaim"),
        ("upper_break_buy", "breakout_failure"),
        ("lower_hold_buy", "lower_support_fail"),
        ("lower_break_sell", "breakdown_failure"),
        ("mid_reclaim_buy", "mid_relose"),
        ("mid_lose_sell", "mid_reclaim"),
    ]
    assert [(item["archetype_id"], item["management_profile_id"]) for item in ctx.metadata["observe_confirm_scope_contract_v1"]["management_profile_taxonomy_v2"]["canonical_mapping"]] == [
        ("upper_reject_sell", "reversal_profile"),
        ("upper_break_buy", "breakout_hold_profile"),
        ("lower_hold_buy", "support_hold_profile"),
        ("lower_break_sell", "breakdown_hold_profile"),
        ("mid_reclaim_buy", "mid_reclaim_fast_exit_profile"),
        ("mid_lose_sell", "mid_lose_fast_exit_profile"),
    ]
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["routing_policy_v2"]["layer_roles"]["position_response"]["role"] == "archetype_candidate_generation"
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["routing_policy_v2"]["layer_roles"]["forecast"]["role"] == "confidence_modulation_and_confirm_wait_split_only"
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["routing_policy_v2"]["identity_guard"]["forecast_identity_override_allowed"] is False
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["confidence_semantics_v2"]["meaning"] == "execution_readiness_score"
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["confidence_semantics_v2"]["identity_separation"]["wait_preserves_archetype_identity"] is True
    assert ctx.metadata["observe_confirm_scope_contract_v1"]["action_side_semantics_v2"]["directional_observe_policy"]["allowed"] is True
    assert ctx.metadata["semantic_foundation_contract_v1"]["contract_version"] == "semantic_foundation_v1"
    assert ctx.metadata["semantic_foundation_contract_v1"]["direct_action_layer"] is False
    assert ctx.metadata["semantic_foundation_contract_v1"]["frozen_for_forecast"] is True
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["contract_version"] == "outcome_labeler_scope_v1"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["offline_only"] is True
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["anchor_basis"]["source"] == "entry_decisions.csv"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["anchor_basis"]["row_unit"] == "entry_decisions.csv row"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["anchor_basis"]["timestamp_priority_fields"] == ["signal_bar_ts", "time"]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["future_source"]["source"] == "trade_closed_history.csv"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["outcome_signal_source_v1"]["required_inputs"][0]["source"] == "entry_decisions.csv"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["outcome_signal_source_v1"]["required_inputs"][1]["path_candidates"] == [
        "data/trades/trade_closed_history.csv",
        "trade_closed_history.csv",
    ]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["label_metadata_v1"]["family_metadata_fields"] == [
        "label_contract",
        "labeler_version",
        "anchor_timestamp",
        "horizon_bars",
        "future_window_start",
        "future_window_end",
        "source_files",
        "matched_outcome_rows",
        "label_reasons",
        "label_status_reason",
    ]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["shadow_label_output_v1"]["row_type"] == "outcome_labels_v1"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["shadow_label_output_v1"]["output_targets"]["analysis_dir"] == "data/analysis"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["dataset_builder_bridge_v1"]["row_type"] == "replay_dataset_row_v1"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["dataset_builder_bridge_v1"]["required_sections"] == [
        "decision_row",
        "semantic_snapshots",
        "forecast_snapshots",
        "outcome_labels_v1",
    ]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["validation_report_v1"]["report_type"] == "outcome_label_validation_report_v1"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["validation_report_v1"]["required_metrics"] == [
        "label_counts",
        "status_counts",
        "unknown_ratio",
        "censored_ratio",
        "symbol_distribution",
        "horizon_distribution",
    ]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["outcome_signal_source_v1"]["required_join_keys"]["setup_side_action"] == "setup_id, setup_side, and action stabilize same-symbol joins"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["anchor_definition_v1"]["transition"]["future_interval"]["start"] == "first_future_bar_after_anchor"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["anchor_definition_v1"]["management"]["future_interval"]["end"] == "management_horizon_close_or_position_close"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["horizon_definition_v1"]["transition"]["horizon_bars"] == 3
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["horizon_definition_v1"]["management"]["horizon_bars"] == 6
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["horizon_definition_v1"]["recommended_metadata"]["transition_horizon_bars"] == 3
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["horizon_definition_v1"]["recommended_metadata"]["management_horizon_bars"] == 6
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["buy_confirm_success_label"]["forecast_probability_field"] == "p_buy_confirm"
    assert "fake behavior" in ctx.metadata["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["sell_confirm_success_label"]["negative_rule"]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["false_break_label"]["forecast_probability_field"] == "p_false_break"
    assert "same-direction extension" in ctx.metadata["outcome_labeler_scope_contract_v1"]["transition_label_rules_v1"]["labels"]["continuation_success_label"]["positive_rule"]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["continue_favor_label"]["forecast_probability_field"] == "p_continue_favor"
    assert "immediate cut or exit outperforms holding" in ctx.metadata["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["fail_now_label"]["positive_rule"]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["reach_tp1_label"]["tp1_definition_ref"] == "project_tp1_definition_v1"
    assert "reached_opposite_edge == True" in " ".join(ctx.metadata["outcome_labeler_scope_contract_v1"]["management_label_rules_v1"]["labels"]["opposite_edge_reach_label"]["positive_signals"])
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["ambiguity_and_censoring_rules_v1"]["mandatory_statuses"] == [
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "NO_POSITION_CONTEXT",
        "AMBIGUOUS",
        "CENSORED",
    ]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["ambiguity_and_censoring_rules_v1"]["status_precedence"] == [
        "INVALID",
        "NO_POSITION_CONTEXT",
        "CENSORED",
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "AMBIGUOUS",
        "VALID",
    ]
    assert "dataset ends or a continuity gap appears" in " ".join(ctx.metadata["outcome_labeler_scope_contract_v1"]["ambiguity_and_censoring_rules_v1"]["statuses"]["CENSORED"]["examples"])
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["label_families"]["transition"] == list(OUTCOME_LABELER_TRANSITION_LABELS_V1)
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["label_families"]["management"] == list(OUTCOME_LABELER_MANAGEMENT_LABELS_V1)
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["label_status_values"] == list(OUTCOME_LABEL_STATUS_VALUES_V1)
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["label_polarity_values"] == list(OUTCOME_LABEL_POLARITY_VALUES_V1)
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["labeling_philosophy_v1"]["role_separation"]["shared_contract"] is True
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["labeling_philosophy_v1"]["status_semantics"]["NO_POSITION_CONTEXT"]["polarity_behavior"] == "UNKNOWN"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["labeling_philosophy_v1"]["status_semantics"]["NO_EXIT_CONTEXT"]["polarity_behavior"] == "UNKNOWN"
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["labeling_philosophy_v1"]["status_semantics"]["INVALID"]["polarity_behavior"] == "UNKNOWN"
    assert "anchor_definition_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "horizon_definition_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "transition_label_rules_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "management_label_rules_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "ambiguity_and_censoring_rules_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "outcome_signal_source_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "outcome_labeler_v1_implementation" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "label_metadata_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "shadow_label_output_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "dataset_builder_bridge_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert "validation_report_v1" in ctx.metadata["outcome_labeler_scope_contract_v1"]["completed_definitions"]
    assert ctx.metadata["outcome_labeler_scope_contract_v1"]["outcome_labeler_v1_implementation"]["transition_function"] == "label_transition_outcomes"
    assert ctx.metadata["engine_context_v1"]["metadata"]["signal_timeframe"] == "15M"
    assert int(ctx.metadata["engine_context_v1"]["metadata"]["signal_bar_ts"]) > 0
    assert ctx.metadata["semantic_foundation_contract_v1"]["feature_layers"] == [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ]
    assert ctx.metadata["energy_scope_contract_v1"]["contract_version"] == ENERGY_SCOPE_CONTRACT_V1["contract_version"]
    assert ctx.metadata["energy_scope_contract_v1"]["canonical_output_field"] == "energy_helper_v2"
    assert ctx.metadata["energy_logging_replay_contract_v1"]["contract_version"] == (
        ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    )
    assert ctx.metadata["energy_migration_dual_write_v1"]["contract_version"] == (
        ENERGY_MIGRATION_DUAL_WRITE_V1["contract_version"]
    )
    assert ctx.metadata["energy_migration_dual_write_v1"]["dual_write_required"] is True
    assert ctx.metadata["energy_migration_dual_write_v1"]["live_gate_promotion_allowed"] is False
    assert ctx.metadata["forecast_calibration_contract_v1"]["contract_version"] == "forecast_calibration_v1"
    assert ctx.metadata["forecast_calibration_contract_v1"]["live_action_gate_changed"] is False
    assert ctx.metadata["forecast_calibration_contract_v1"]["shadow_validation_ready"] is True
    assert ctx.metadata["position_zones_v2"]["box_zone"] == "LOWER_EDGE"
    assert ctx.metadata["position_interpretation_v2"]["primary_label"] == "LOWER_BIAS"
    assert ctx.metadata["position_interpretation_v2"]["bias_label"] == "LOWER_BIAS"
    assert ctx.metadata["position_interpretation_v2"]["secondary_context_label"] == "LOWER_CONTEXT"
    assert ctx.metadata["position_interpretation_v2"]["metadata"]["raw_alignment_label"] == "ALIGNED_LOWER_WEAK"
    assert ctx.metadata["position_interpretation_v2"]["metadata"]["alignment_softening"]["downgraded"] is True
    assert ctx.metadata["position_interpretation_v2"]["metadata"]["alignment_softening"]["reason"] == (
        "weak_alignment_requires_bb44_side_support"
    )
    assert ctx.metadata["response_raw_snapshot_v1"]["box_lower_bounce"] > 0.0
    assert ctx.metadata["response_vector_v2"]["lower_hold_up"] > 0.0
    assert ctx.metadata["state_raw_snapshot_v1"]["market_mode"] == ctx.market_mode
    assert ctx.metadata["state_vector_v2"]["range_reversal_gain"] > 1.0
    assert ctx.metadata["evidence_vector_v1"]["buy_reversal_evidence"] > 0.0
    assert ctx.metadata["belief_state_v1"]["buy_belief"] >= 0.0
    assert ctx.metadata["barrier_state_v1"]["buy_barrier"] >= 0.0
    assert ctx.metadata["forecast_features_v1"]["position_primary_label"] == ctx.metadata["position_interpretation_v2"]["primary_label"]
    assert ctx.metadata["forecast_features_v1"]["metadata"]["signal_timeframe"] == "15M"
    assert int(ctx.metadata["forecast_features_v1"]["metadata"]["signal_bar_ts"]) > 0
    assert ctx.metadata["forecast_features_v1"]["metadata"]["transition_horizon_bars"] == 3
    assert ctx.metadata["forecast_features_v1"]["metadata"]["management_horizon_bars"] == 6
    assert ctx.metadata["forecast_features_v1"]["metadata"]["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert ctx.metadata["forecast_features_v1"]["metadata"]["forecast_freeze_phase"] == "FR0"
    assert ctx.metadata["forecast_features_v1"]["metadata"]["forecast_branch_role"] == "feature_bundle_only"
    assert ctx.metadata["forecast_features_v1"]["metadata"]["semantic_forecast_inputs_v2"]["contract_version"] == "semantic_forecast_inputs_v2"
    assert "state_harvest" in ctx.metadata["forecast_features_v1"]["metadata"]["semantic_forecast_inputs_v2"]
    assert ctx.metadata["transition_forecast_v1"]["metadata"]["forecast_contract"] == "transition_forecast_v1"
    assert ctx.metadata["transition_forecast_v1"]["metadata"]["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert ctx.metadata["transition_forecast_v1"]["metadata"]["forecast_branch_role"] == "transition_branch"
    assert ctx.metadata["transition_forecast_v1"]["metadata"]["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "harvested_with_usage_trace"
    assert "scene_transition_support_v1" in ctx.metadata["transition_forecast_v1"]["metadata"]
    assert ctx.metadata["trade_management_forecast_v1"]["metadata"]["forecast_contract"] == "trade_management_forecast_v1"
    assert ctx.metadata["trade_management_forecast_v1"]["metadata"]["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert ctx.metadata["trade_management_forecast_v1"]["metadata"]["forecast_branch_role"] == "trade_management_branch"
    assert ctx.metadata["trade_management_forecast_v1"]["metadata"]["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "harvested_with_usage_trace"
    assert "management_scene_support_v1" in ctx.metadata["trade_management_forecast_v1"]["metadata"]
    assert "transition_side_separation" in ctx.metadata["forecast_gap_metrics_v1"]
    assert "management_continue_fail_gap" in ctx.metadata["forecast_gap_metrics_v1"]
    assert "wait_confirm_gap" in ctx.metadata["forecast_gap_metrics_v1"]
    assert "hold_exit_gap" in ctx.metadata["forecast_gap_metrics_v1"]
    assert ctx.metadata["forecast_gap_metrics_v1"]["metadata"]["semantic_owner_contract"] == "forecast_branch_interpretation_only_v1"
    assert ctx.metadata["forecast_gap_metrics_v1"]["metadata"]["forecast_branch_role"] == "gap_metrics_branch"
    assert ctx.metadata["forecast_gap_metrics_v1"]["metadata"]["semantic_forecast_inputs_v2_usage_v1"]["usage_status"] == "derived_from_branch_outputs_only"
    assert "execution_gap_support_v1" in ctx.metadata["forecast_gap_metrics_v1"]["metadata"]
    assert ctx.metadata["energy_snapshot"] == bundle["energy_snapshot"].to_dict()
    assert bundle["energy_helper"] == ctx.metadata["energy_helper_v2"]
    assert set(ctx.metadata["energy_helper_v2"].keys()) == {
        "selected_side",
        "action_readiness",
        "continuation_support",
        "reversal_support",
        "suppression_pressure",
        "forecast_support",
        "net_utility",
        "confidence_adjustment_hint",
        "soft_block_hint",
        "metadata",
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_source_fields"]["evidence_vector_effective_v1"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["input_source_fields"]["forecast_effective_policy_v1"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["identity_guard"]["identity_preserved"] is True
    assert "archetype_id" in ctx.metadata["energy_helper_v2"]["metadata"]["identity_guard"]["non_owner_fields"]
    assert ctx.metadata["energy_helper_v2"]["metadata"]["migration_dual_write_freeze"]["dual_write_required"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["migration_dual_write_freeze"]["legacy_snapshot_present"] is True
    assert ctx.metadata["energy_helper_v2"]["metadata"]["migration_dual_write_freeze"]["live_gate_promotion_allowed"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["logging_replay_freeze"]["contract_version"] == (
        ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    )
    assert ctx.metadata["energy_helper_v2"]["metadata"]["logging_replay_freeze"]["consumer_usage_trace_present"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["legacy_bridge"]["runtime_field"] == "energy_snapshot"
    assert ctx.metadata["prs_log_contract_v2"]["energy_migration_contract_field"] == "energy_migration_dual_write_v1"
    assert ctx.metadata["prs_log_contract_v2"]["energy_logging_replay_contract_field"] == "energy_logging_replay_contract_v1"
    assert ctx.metadata["observe_confirm_v1"] == ctx.metadata["observe_confirm_v2"]
    assert ctx.metadata["observe_confirm_v2"]["state"] in {"OBSERVE", "CONFIRM", "CONFLICT_OBSERVE", "NO_TRADE", "INVALIDATED"}
    assert ctx.metadata["observe_confirm_v2"]["action"] in {"WAIT", "BUY", "SELL", "NONE"}
    assert ctx.metadata["observe_confirm_v2"]["side"] in {"BUY", "SELL", ""}
    assert ctx.metadata["observe_confirm_v2"]["archetype_id"] in {
        "",
        "upper_reject_sell",
        "upper_break_buy",
        "lower_hold_buy",
        "lower_break_sell",
        "mid_reclaim_buy",
        "mid_lose_sell",
    }
    expected_invalidation_by_archetype = {
        "upper_reject_sell": "upper_break_reclaim",
        "upper_break_buy": "breakout_failure",
        "lower_hold_buy": "lower_support_fail",
        "lower_break_sell": "breakdown_failure",
        "mid_reclaim_buy": "mid_relose",
        "mid_lose_sell": "mid_reclaim",
    }
    expected_management_profile_by_archetype = {
        "upper_reject_sell": "reversal_profile",
        "upper_break_buy": "breakout_hold_profile",
        "lower_hold_buy": "support_hold_profile",
        "lower_break_sell": "breakdown_hold_profile",
        "mid_reclaim_buy": "mid_reclaim_fast_exit_profile",
        "mid_lose_sell": "mid_lose_fast_exit_profile",
    }
    assert ctx.metadata["observe_confirm_v2"]["invalidation_id"] == expected_invalidation_by_archetype.get(
        ctx.metadata["observe_confirm_v2"]["archetype_id"],
        "",
    )
    assert ctx.metadata["observe_confirm_v2"]["management_profile_id"] == expected_management_profile_by_archetype.get(
        ctx.metadata["observe_confirm_v2"]["archetype_id"],
        "",
    )
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["routing_policy_contract_v2"] == "observe_confirm_routing_policy_v2"
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["routing_policy_v2"]["forecast_policy"]["identity_override_allowed"] is False
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["routing_policy_v2"]["available_inputs"]["evidence_vector_v1"] is True
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["routing_policy_v2"]["available_inputs"]["transition_forecast_v1"] is True
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["confidence_semantics_contract_v2"] == "observe_confirm_confidence_semantics_v2"
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["confidence_semantics_v2"]["meaning"] == "execution_readiness_score"
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["confidence_semantics_v2"]["identity_separate"] is True
    assert "confidence" in ctx.metadata["observe_confirm_v2"]
    assert "reason" in ctx.metadata["observe_confirm_v2"]
    assert "archetype_id" in ctx.metadata["observe_confirm_v2"]
    assert "invalidation_id" in ctx.metadata["observe_confirm_v2"]
    assert "management_profile_id" in ctx.metadata["observe_confirm_v2"]
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"] == {
        "emit_kind": ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"][
            "emit_kind"
        ],
        "buy_support": ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"][
            "buy_support"
        ],
        "sell_support": ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"][
            "sell_support"
        ],
        "support_gap": ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"][
            "support_gap"
        ],
    }
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"]["semantic_readiness_bridge_v1"][
        "emit_kind"
    ] in {"confirm", "observe", "conflict_observe"}
    assert "buy_force" not in ctx.metadata["observe_confirm_v2"]["metadata"]["raw_contributions"][
        "semantic_readiness_bridge_v1"
    ]
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["semantic_readiness_bridge_v1"][
        "legacy_energy_snapshot_dependency"
    ] is False
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["semantic_readiness_bridge_v1"]["final"].keys() == {
        "buy_support",
        "sell_support",
        "support_gap",
    }
    assert ctx.metadata["observe_confirm_v2"]["metadata"]["effective_contributions"] == {}
    assert isinstance(ctx.metadata["observe_confirm_v2"]["metadata"]["winning_evidence"], list)
    assert "blocked_reason" in ctx.metadata["observe_confirm_v2"]["metadata"]


def test_context_classifier_reuses_m15_indicator_frame_between_bb_and_engine_snapshot():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "1H": pd.DataFrame(
            {
                "close": [100.0, 99.8, 99.6],
                "high": [100.4, 100.0, 99.8],
                "low": [99.6, 99.4, 99.2],
            }
        ),
        "15M": pd.DataFrame({"time": [1773149400], "close": [90.1], "high": [90.4], "low": [89.8]}),
    }
    result = {
        "regime": {"name": "range", "zone": "lower", "volatility_ratio": 0.85, "spread_ratio": 1.0},
        "components": {"wait_score": 12, "wait_conflict": 4, "wait_noise": 3},
    }

    bundle = classifier.build_entry_context(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=90.01, ask=90.02),
        df_all=df_all,
        scorer=scorer,
        result=result,
        buy_s=90.0,
        sell_s=40.0,
    )

    assert scorer.trend_mgr.add_indicator_calls == 2
    assert bundle["context"].metadata["build_entry_context_profile_v1"]["m15_indicator_cached"] is True
    assert "15M" in bundle["context"].metadata["engine_context_snapshot_profile_v1"]["indicator_cache_timeframes"]


def test_context_classifier_preserves_raw_and_effective_source_trace_for_energy_replay():
    bundle = _build_range_lower_entry_bundle()
    ctx = bundle["context"]

    for raw_field in ("response_raw_snapshot_v1", "state_raw_snapshot_v1", "evidence_vector_v1"):
        assert raw_field in ctx.metadata
    for effective_field in (
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ):
        assert effective_field in ctx.metadata
        assert ctx.metadata["energy_helper_v2"]["metadata"]["input_source_fields"][effective_field] is True

    ignored_direct_inputs = ctx.metadata["energy_helper_v2"]["metadata"]["input_freeze"][
        "ignored_available_direct_inputs"
    ]
    for raw_trace_field in (
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "evidence_vector_v1",
    ):
        assert raw_trace_field in ignored_direct_inputs


def test_context_classifier_dual_writes_energy_helper_and_legacy_snapshot_for_migration_replay():
    bundle = _build_range_lower_entry_bundle()
    ctx = bundle["context"]

    assert "energy_helper_v2" in ctx.metadata
    assert "energy_snapshot" in ctx.metadata
    assert ctx.metadata["energy_snapshot"] == bundle["energy_snapshot"].to_dict()
    assert ctx.metadata["energy_migration_dual_write_v1"]["dual_write_required"] is True
    assert ctx.metadata["energy_migration_dual_write_v1"]["live_gate_promotion_allowed"] is False
    assert ctx.metadata["energy_migration_guard_v1"]["compatibility_role"] == "compatibility_transition_only"
    assert ctx.metadata["energy_migration_guard_v1"]["used_compatibility_bridge"] is False
    assert ctx.metadata["energy_migration_guard_v1"]["legacy_identity_input_allowed"] is False
    assert ctx.metadata["energy_migration_guard_v1"]["legacy_live_gate_allowed"] is False
    assert ctx.metadata["energy_helper_v2"]["metadata"]["migration_dual_write_freeze"] == {
        "applied": True,
        "contract_version": ENERGY_MIGRATION_DUAL_WRITE_V1["contract_version"],
        "canonical_output_field": "energy_helper_v2",
        "compatibility_runtime_field": "energy_snapshot",
        "runtime_contract_field": "energy_migration_dual_write_v1",
        "official_guard_helper": "resolve_energy_migration_bridge_state",
        "dual_write_required": True,
        "write_targets": [
            "energy_helper_v2",
            "energy_snapshot",
        ],
        "legacy_bridge_role": "compatibility_transition_only",
        "canonical_consumer_read_field": "energy_helper_v2",
        "direct_legacy_consumer_use_allowed": False,
        "fallback_allowed_only_when_canonical_missing": True,
        "legacy_identity_input_allowed": False,
        "legacy_live_gate_allowed": False,
        "legacy_rebuild_scope": "replay_or_transition_when_helper_missing_only",
        "live_gate_promotion_allowed": False,
        "live_gate_behavior": "unchanged_during_migration",
        "replay_preservation_required": True,
        "canonical_payload_emitted": True,
        "legacy_snapshot_present": True,
    }
    assert ctx.metadata["energy_helper_v2"]["metadata"]["legacy_bridge"]["runtime_field"] == "energy_snapshot"
    assert ctx.metadata["energy_helper_v2"]["metadata"]["legacy_bridge"]["present"] is True
    assert ctx.metadata["prs_log_contract_v2"]["canonical_energy_field"] == "energy_helper_v2"
    assert ctx.metadata["prs_log_contract_v2"]["compatibility_energy_runtime_field"] == "energy_snapshot"


def test_context_classifier_observe_confirm_identity_is_independent_of_legacy_energy_snapshot(monkeypatch):
    monkeypatch.setattr(
        context_classifier_module,
        "compute_energy_snapshot",
        lambda *_args, **_kwargs: EnergySnapshot(buy_force=0.01, sell_force=0.98, net_force=-0.97),
    )
    low_bundle = _build_range_lower_entry_bundle()
    low_ctx = low_bundle["context"]

    monkeypatch.setattr(
        context_classifier_module,
        "compute_energy_snapshot",
        lambda *_args, **_kwargs: EnergySnapshot(buy_force=0.98, sell_force=0.01, net_force=0.97),
    )
    high_bundle = _build_range_lower_entry_bundle()
    high_ctx = high_bundle["context"]

    assert low_ctx.metadata["energy_snapshot"] != high_ctx.metadata["energy_snapshot"]
    assert low_ctx.metadata["observe_confirm_v2"]["archetype_id"] == high_ctx.metadata["observe_confirm_v2"][
        "archetype_id"
    ]
    assert low_ctx.metadata["observe_confirm_v2"]["side"] == high_ctx.metadata["observe_confirm_v2"]["side"]
    assert low_ctx.metadata["observe_confirm_v2"]["invalidation_id"] == high_ctx.metadata["observe_confirm_v2"][
        "invalidation_id"
    ]
    assert low_ctx.metadata["observe_confirm_v2"]["management_profile_id"] == high_ctx.metadata["observe_confirm_v2"][
        "management_profile_id"
    ]
    assert low_ctx.metadata["observe_confirm_v2"]["metadata"]["routing_policy_v2"]["implementation_bridge"] == {
        "semantic_readiness_bridge_v1": "internal_readiness_from_semantic_bundle",
        "legacy_energy_snapshot_dependency": False,
    }


def test_context_classifier_passes_state_vector_v2_to_energy_and_observe_confirm(monkeypatch):
    seen = {"energy": None, "observe": None}

    def _energy_probe(position, response, state, **kwargs):
        seen["energy"] = state
        return EnergySnapshot(buy_force=0.31, sell_force=0.10, net_force=0.21)

    def _observe_probe(position, response, state, position_snapshot, **kwargs):
        seen["observe"] = state
        return ObserveConfirmSnapshot(
            state="OBSERVE",
            action="WAIT",
            side="BUY",
            confidence=0.22,
            reason="probe_wait",
            archetype_id="lower_hold_buy",
        )

    monkeypatch.setattr(context_classifier_module, "compute_energy_snapshot", _energy_probe)
    monkeypatch.setattr(context_classifier_module, "route_observe_confirm", _observe_probe)

    bundle = _build_range_lower_entry_bundle()
    ctx = bundle["context"]

    assert isinstance(seen["energy"], StateVectorV2)
    assert isinstance(seen["observe"], StateVectorV2)
    assert ctx.metadata["observe_confirm_v2"]["reason"] == "probe_wait"


def test_context_classifier_resolves_bb_state_from_channel_position_fallback():
    classifier = ContextClassifier()
    scorer = _DummyScorer()
    df_all = {
        "15M": pd.DataFrame({"time": [1773149400], "close": [105.2], "high": [105.4], "low": [105.0]}),
    }
    tick = SimpleNamespace(bid=105.2, ask=105.21)

    bb_state = classifier.resolve_bb_state(symbol="NAS100", tick=tick, df_all=df_all, scorer=scorer)

    assert bb_state == "UPPER_EDGE"
