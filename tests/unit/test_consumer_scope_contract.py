from pathlib import Path

from backend.services.consumer_contract import (
    CONSUMER_FREEZE_HANDOFF_V1,
    CONSUMER_INPUT_CONTRACT_V1,
    CONSUMER_LAYER_MODE_INTEGRATION_V1,
    CONSUMER_LOGGING_CONTRACT_V1,
    CONSUMER_MIGRATION_FREEZE_V1,
    CONSUMER_SCOPE_CONTRACT_V1,
    CONSUMER_TEST_CONTRACT_V1,
    ENTRY_GUARD_CONTRACT_V1,
    ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
    EXIT_HANDOFF_CONTRACT_V1,
    RE_ENTRY_CONTRACT_V1,
    SETUP_MAPPING_CONTRACT_V1,
    SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1,
    build_consumer_migration_guard_metadata,
    classify_entry_guard_reason,
    consumer_input_contract_doc_path,
    consumer_freeze_handoff_doc_path,
    consumer_layer_mode_integration_doc_path,
    consumer_logging_contract_doc_path,
    consumer_migration_freeze_doc_path,
    consumer_scope_contract_doc_path,
    consumer_test_contract_doc_path,
    entry_guard_contract_doc_path,
    entry_service_responsibility_contract_doc_path,
    exit_handoff_contract_doc_path,
    re_entry_contract_doc_path,
    resolve_consumer_guard_result,
    resolve_consumer_handoff_payload,
    resolve_consumer_layer_mode_policy_input,
    resolve_consumer_layer_mode_policy_resolution,
    resolve_consumer_observe_confirm_resolution,
    resolve_exit_handoff,
    resolve_re_entry_handoff,
    resolve_consumer_observe_confirm_input,
    resolve_setup_mapping,
    setup_mapping_contract_doc_path,
    setup_detector_responsibility_contract_doc_path,
)


def test_consumer_scope_contract_freezes_consumer_boundary():
    contract = CONSUMER_SCOPE_CONTRACT_V1

    assert contract["contract_version"] == "consumer_scope_v1"
    assert contract["scope"] == "observe_confirm_consumer_only"
    assert contract["canonical_input_field"] == "observe_confirm_v2"
    assert contract["compatibility_input_field_v1"] == "observe_confirm_v1"
    assert contract["input_contract_v1"]["contract_version"] == CONSUMER_INPUT_CONTRACT_V1["contract_version"]
    assert contract["layer_mode_integration_v1"]["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert contract["migration_freeze_v1"]["contract_version"] == CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
    assert contract["setup_detector_responsibility_contract_v1"]["contract_version"] == SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1["contract_version"]
    assert contract["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert contract["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert contract["entry_service_responsibility_contract_v1"]["contract_version"] == ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1["contract_version"]
    assert contract["exit_handoff_contract_v1"]["contract_version"] == EXIT_HANDOFF_CONTRACT_V1["contract_version"]
    assert contract["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert contract["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert contract["consumer_test_contract_v1"]["contract_version"] == CONSUMER_TEST_CONTRACT_V1["contract_version"]
    assert contract["consumer_freeze_handoff_v1"]["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]
    assert contract["energy_usage_freeze_v1"]["contract_version"] == "consumer_energy_usage_freeze_v1"
    assert [item["component"] for item in contract["consumer_components"]] == [
        "SetupDetector",
        "EntryService",
        "WaitEngine",
        "Exit",
        "ReEntry",
    ]
    assert "read observe_confirm_v2 state, action, side, confidence, reason, archetype_id, invalidation_id, and management_profile_id" in contract["responsibilities"]
    assert "connect observe_confirm output to setup naming, entry guards, exit handoff, and re-entry policy hooks" in contract["responsibilities"]
    assert "read layer_mode_policy_v1 as the official policy input overlay above canonical observe_confirm identity" in contract["responsibilities"]
    assert "read energy_helper_v2 only through the frozen component usage boundary" in contract["responsibilities"]
    assert "semantic layer reinterpretation" in contract["non_responsibilities"]
    assert "raw detector direct read" in contract["non_responsibilities"]
    assert "energy helper identity promotion" in contract["non_responsibilities"]
    assert "observe_confirm_v2" in contract["allowed_runtime_inputs"]
    assert "layer_mode_policy_v1" in contract["allowed_runtime_inputs"]
    assert "energy_helper_v2" in contract["allowed_runtime_inputs"]
    assert "raw_detector_score" in contract["forbidden_runtime_inputs"]
    assert contract["handoff_fields"] == [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
    ]
    assert contract["consumer_boundary"]["setup_detector"].startswith("Names setup_id only")
    assert contract["consumer_boundary"]["entry_service"].startswith("Applies preflight and execution guards only")
    assert contract["consumer_boundary"]["wait_engine"].startswith("Compares enter versus wait")
    assert contract["energy_usage_freeze_v1"]["component_usage"][0]["component"] == "SetupDetector"
    assert contract["energy_usage_freeze_v1"]["component_usage"][1]["allowed_energy_fields"] == [
        "action_readiness",
        "confidence_adjustment_hint",
        "soft_block_hint",
        "metadata.utility_hints.priority_hint",
    ]
    assert contract["energy_usage_freeze_v1"]["component_usage"][2]["component"] == "WaitEngine"
    assert contract["energy_usage_freeze_v1"]["component_usage"][2]["allowed_energy_fields"] == [
        "action_readiness",
        "soft_block_hint",
        "metadata.utility_hints.wait_vs_enter_hint",
    ]
    assert contract["energy_usage_freeze_v1"]["bridge_strategy"] == "hint_first_no_direct_order_decision"
    assert contract["energy_usage_freeze_v1"]["direct_net_utility_use_allowed"] is False
    assert contract["energy_usage_freeze_v1"]["component_usage"][1]["direct_net_utility_use_allowed"] is False
    assert "selected_side as canonical side" in contract["energy_usage_freeze_v1"]["forbidden_energy_uses"]
    assert "place_order_directly_from_net_utility" in contract["energy_usage_freeze_v1"]["forbidden_energy_uses"]
    assert "net_utility stays summary-only and consumers route through hints before any live decision path" in (
        contract["energy_usage_freeze_v1"]["principles"]
    )
    assert contract["runtime_embedding_field"] == "consumer_scope_contract_v1"


def test_consumer_input_contract_freezes_official_consumer_inputs():
    contract = CONSUMER_INPUT_CONTRACT_V1

    assert contract["contract_version"] == "consumer_input_contract_v1"
    assert contract["official_input_container"] == "DecisionContext.metadata"
    assert contract["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert contract["compatibility_observe_confirm_field_v1"] == "observe_confirm_v1"
    assert contract["canonical_energy_field"] == "energy_helper_v2"
    assert contract["observe_confirm_resolution_order"] == [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ]
    assert contract["required_handoff_fields"] == [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
    ]
    assert "metadata.observe_confirm_v2" in contract["allowed_decision_context_fields"]
    assert "metadata.layer_mode_policy_v1" in contract["allowed_decision_context_fields"]
    assert "metadata.energy_helper_v2" in contract["allowed_decision_context_fields"]
    assert "preflight_allowed_action" in contract["allowed_non_semantic_runtime_fields"]
    assert "energy_helper_v2" in contract["allowed_non_semantic_runtime_fields"]
    assert "prior_entry_archetype_id" in contract["allowed_non_semantic_runtime_fields"]
    assert "re_entry_cooldown_active" in contract["allowed_non_semantic_runtime_fields"]
    assert "response_vector_v2" in contract["forbidden_direct_inputs"]
    assert "transition_forecast_v1" in contract["forbidden_direct_inputs"]
    assert contract["energy_usage_freeze_v1"]["contract_version"] == "consumer_energy_usage_freeze_v1"
    assert "backend/services/wait_engine.py" in contract["consumer_entry_points"]
    assert contract["runtime_embedding_field"] == "consumer_input_contract_v1"


def test_consumer_layer_mode_integration_contract_freezes_policy_overlay_boundary():
    contract = CONSUMER_LAYER_MODE_INTEGRATION_V1

    assert contract["contract_version"] == "consumer_layer_mode_integration_v1"
    assert contract["scope"] == "consumer_policy_overlay_input_only"
    assert contract["official_resolution_helper"] == "resolve_consumer_layer_mode_policy_resolution"
    assert contract["official_payload_helper"] == "resolve_consumer_layer_mode_policy_input"
    assert contract["canonical_policy_field"] == "layer_mode_policy_v1"
    assert contract["canonical_identity_field"] == "observe_confirm_v2"
    assert contract["policy_resolution_order"] == [
        "prs_log_contract_v2.layer_mode_policy_output_field",
        "layer_mode_policy_v1",
    ]
    assert contract["required_policy_fields"] == [
        "layer_modes",
        "effective_influences",
        "suppressed_reasons",
        "confidence_adjustments",
        "hard_blocks",
        "mode_decision_trace",
    ]
    assert contract["component_policy_usage"][0]["component"] == "SetupDetector"
    assert contract["component_policy_usage"][1]["policy_usage"].startswith("official policy input")
    assert contract["runtime_embedding_field"] == "consumer_layer_mode_integration_v1"


def test_resolve_consumer_layer_mode_policy_resolution_reads_overlay_without_reinterpreting_semantic_vectors():
    resolution = resolve_consumer_layer_mode_policy_resolution(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.72,
                "reason": "lower_rebound_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "layer_mode_policy_v1": {
                "layer_modes": [{"layer": "Forecast", "mode": "shadow"}],
                "effective_influences": [{"layer": "Forecast", "active_effects": ["metadata_log_only", "trace_only"]}],
                "suppressed_reasons": [],
                "confidence_adjustments": [],
                "hard_blocks": [],
                "mode_decision_trace": {"layers": [{"layer": "Forecast", "identity_preserved": True}]},
                "identity_preserved": True,
            },
            "response_vector_v2": {"lower_hold_up": 1.0},
            "transition_forecast_v1": {"p_buy_confirm": 0.81},
            "prs_log_contract_v2": {
                "layer_mode_policy_output_field": "layer_mode_policy_v1",
            },
        }
    )

    payload = resolve_consumer_layer_mode_policy_input(
        {
            "layer_mode_policy_v1": resolution["payload"],
            "prs_log_contract_v2": {"layer_mode_policy_output_field": "layer_mode_policy_v1"},
        }
    )

    assert resolution["field_name"] == "layer_mode_policy_v1"
    assert resolution["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert resolution["payload"]["identity_preserved"] is True
    assert payload["layer_modes"][0]["layer"] == "Forecast"
    assert "response_vector_v2" not in payload
    assert "transition_forecast_v1" not in payload


def test_resolve_consumer_observe_confirm_input_prefers_canonical_v2_and_ignores_raw_vectors():
    payload = resolve_consumer_observe_confirm_input(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.72,
                "reason": "lower_rebound_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "observe_confirm_v1": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "",
                "confidence": 0.11,
                "reason": "legacy_wait",
                "archetype_id": "",
                "invalidation_id": "",
                "management_profile_id": "",
            },
            "response_vector_v2": {"lower_hold_up": 1.0},
            "transition_forecast_v1": {"p_buy_confirm": 0.81},
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        }
    )

    assert payload["state"] == "CONFIRM"
    assert payload["action"] == "BUY"
    assert payload["archetype_id"] == "lower_hold_buy"
    assert "response_vector_v2" not in payload
    assert "transition_forecast_v1" not in payload


def test_consumer_input_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_input_contract_doc_path(root).exists()


def test_consumer_layer_mode_integration_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_layer_mode_integration_doc_path(root).exists()


def test_consumer_migration_freeze_contract_closes_v1_v2_read_order():
    contract = CONSUMER_MIGRATION_FREEZE_V1

    assert contract["contract_version"] == "consumer_migration_freeze_v1"
    assert contract["official_resolution_helper"] == "resolve_consumer_observe_confirm_resolution"
    assert contract["official_payload_helper"] == "resolve_consumer_observe_confirm_input"
    assert contract["official_guard_helper"] == "build_consumer_migration_guard_metadata"
    assert contract["read_order"] == [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ]
    assert contract["canonical_field"] == "observe_confirm_v2"
    assert contract["compatibility_field_v1"] == "observe_confirm_v1"
    assert contract["compatibility_role"] == "migration_bridge_only"
    assert contract["fallback_allowed_only_when_canonical_missing"] is True
    assert contract["live_runtime_branch_on_compatibility_field_allowed"] is False
    assert contract["identity_ownership_affected_by_compatibility_field"] is False
    assert "consumer reads observe_confirm_v2 first and uses observe_confirm_v1 only as compatibility fallback" in contract["rules"]


def test_resolve_consumer_observe_confirm_resolution_tracks_actual_source_field():
    v2_first = resolve_consumer_observe_confirm_resolution(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.72,
                "reason": "lower_rebound_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "observe_confirm_v1": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "confidence": 0.12,
                "reason": "legacy_conflict",
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        }
    )
    fallback_v1 = resolve_consumer_observe_confirm_resolution(
        {
            "observe_confirm_v1": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.51,
                "reason": "legacy_only_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        }
    )

    assert v2_first["field_name"] == "observe_confirm_v2"
    assert v2_first["used_fallback_v1"] is False
    assert v2_first["canonical_payload_present"] is True
    assert v2_first["compatibility_payload_present"] is True
    assert v2_first["payload"]["archetype_id"] == "lower_hold_buy"

    assert fallback_v1["field_name"] == "observe_confirm_v1"
    assert fallback_v1["used_fallback_v1"] is True
    assert fallback_v1["canonical_payload_present"] is False
    assert fallback_v1["compatibility_payload_present"] is True
    assert fallback_v1["payload"]["reason"] == "legacy_only_confirm"


def test_build_consumer_migration_guard_metadata_marks_bridge_only_fallback():
    guard = build_consumer_migration_guard_metadata(
        {
            "observe_confirm_v1": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.51,
                "reason": "legacy_only_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        }
    )

    assert guard == {
        "contract_version": CONSUMER_MIGRATION_FREEZE_V1["contract_version"],
        "canonical_field": "observe_confirm_v2",
        "compatibility_field_v1": "observe_confirm_v1",
        "resolved_field_name": "observe_confirm_v1",
        "canonical_payload_present": False,
        "compatibility_payload_present": True,
        "used_compatibility_fallback_v1": True,
        "compatibility_role": "migration_bridge_only",
        "fallback_allowed_only_when_canonical_missing": True,
        "canonical_shadow_rebuild_active": True,
        "compatibility_field_can_own_identity": False,
        "live_runtime_branch_on_compatibility_field_allowed": False,
        "identity_ownership_preserved": True,
    }


def test_consumer_migration_freeze_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_migration_freeze_doc_path(root).exists()


def test_setup_detector_responsibility_contract_freezes_naming_only_role():
    contract = SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1

    assert contract["contract_version"] == "setup_detector_responsibility_v1"
    assert contract["scope"] == "setup_naming_only"
    assert contract["consumer_component"] == "SetupDetector"
    assert contract["official_input_fields"] == ["archetype_id", "side", "reason", "market_mode"]
    assert "map canonical archetype handoff into setup_id only" in contract["responsibilities"]
    assert "confirm or wait re-decision" in contract["non_responsibilities"]
    assert "trigger strength scoring" in contract["non_responsibilities"]
    assert contract["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert contract["output_contract"]["primary_field"] == "setup_id"
    assert contract["output_contract"]["matched_trigger_state"] == "READY"
    assert contract["runtime_embedding_field"] == "setup_detector_responsibility_contract_v1"


def test_setup_detector_responsibility_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert setup_detector_responsibility_contract_doc_path(root).exists()


def test_setup_mapping_contract_freezes_canonical_archetype_to_setup_rules():
    contract = SETUP_MAPPING_CONTRACT_V1

    assert contract["contract_version"] == "setup_mapping_contract_v1"
    assert contract["scope"] == "canonical_archetype_to_setup_mapping_only"
    assert contract["consumer_component"] == "SetupDetector"
    assert contract["official_input_fields"] == ["archetype_id", "side", "reason", "market_mode"]
    assert contract["canonical_mapping"] == [
        {
            "archetype_id": "upper_reject_sell",
            "side": "SELL",
            "default_setup_id": "range_upper_reversal_sell",
            "allowed_setup_ids": ["range_upper_reversal_sell"],
        },
        {
            "archetype_id": "upper_break_buy",
            "side": "BUY",
            "default_setup_id": "breakout_retest_buy",
            "allowed_setup_ids": ["breakout_retest_buy"],
        },
        {
            "archetype_id": "lower_hold_buy",
            "side": "BUY",
            "default_setup_id": "range_lower_reversal_buy",
            "allowed_setup_ids": ["range_lower_reversal_buy"],
        },
        {
            "archetype_id": "lower_break_sell",
            "side": "SELL",
            "default_setup_id": "breakout_retest_sell",
            "allowed_setup_ids": ["breakout_retest_sell"],
        },
        {
            "archetype_id": "mid_reclaim_buy",
            "side": "BUY",
            "default_setup_id": "range_lower_reversal_buy",
            "allowed_setup_ids": ["range_lower_reversal_buy", "trend_pullback_buy"],
        },
        {
            "archetype_id": "mid_lose_sell",
            "side": "SELL",
            "default_setup_id": "range_upper_reversal_sell",
            "allowed_setup_ids": ["range_upper_reversal_sell", "trend_pullback_sell"],
        },
    ]
    assert contract["runtime_embedding_field"] == "setup_mapping_contract_v1"


def test_resolve_setup_mapping_specializes_without_rewriting_archetype_family():
    trend = resolve_setup_mapping(
        archetype_id="mid_reclaim_buy",
        side="BUY",
        market_mode="TREND",
        reason="lower_reclaim_confirm",
    )
    range_default = resolve_setup_mapping(
        archetype_id="mid_reclaim_buy",
        side="BUY",
        market_mode="RANGE",
        reason="lower_reclaim_confirm",
    )
    reason_specialized = resolve_setup_mapping(
        archetype_id="mid_lose_sell",
        side="SELL",
        market_mode="RANGE",
        reason="trend_pullback_sell_confirm",
    )

    assert trend["setup_id"] == "trend_pullback_buy"
    assert trend["specialized"] is True
    assert trend["archetype_id"] == "mid_reclaim_buy"
    assert range_default["setup_id"] == "range_lower_reversal_buy"
    assert range_default["specialized"] is False
    assert reason_specialized["setup_id"] == "trend_pullback_sell"
    assert reason_specialized["specialized"] is True
    assert reason_specialized["archetype_id"] == "mid_lose_sell"


def test_setup_mapping_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert setup_mapping_contract_doc_path(root).exists()


def test_entry_service_responsibility_contract_freezes_execution_guard_only_role():
    contract = ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1

    assert contract["contract_version"] == "entry_service_responsibility_v1"
    assert contract["scope"] == "execution_guard_only"
    assert contract["consumer_component"] == "EntryService"
    assert "observe_confirm.archetype_id" in contract["official_input_fields"]
    assert "setup_id" in contract["official_input_fields"]
    assert "energy_helper_v2.action_readiness" in contract["official_input_fields"]
    assert "apply execution guard outcomes such as no-trade blocks, opposite-position lock, spread or liquidity blocks, cluster guard, and runtime order plumbing" in contract["responsibilities"]
    assert "read energy helper only for readiness, priority, confidence hint, and soft block hint" in contract["responsibilities"]
    assert contract["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert "archetype_id rewrite" in contract["non_responsibilities"]
    assert "setup_id rewrite" in contract["non_responsibilities"]
    assert "semantic confirm reversal to the opposite side" in contract["non_responsibilities"]
    assert "energy selected_side identity promotion" in contract["non_responsibilities"]
    assert "flip_buy_to_sell" in contract["forbidden_actions"]
    assert contract["energy_helper_policy"]["allowed_energy_fields"] == [
        "action_readiness",
        "confidence_adjustment_hint",
        "soft_block_hint",
        "metadata.utility_hints.priority_hint",
    ]
    assert contract["energy_helper_policy"]["direct_net_utility_use_allowed"] is False
    assert "place_order_directly_from_net_utility" in contract["energy_helper_policy"]["forbidden_energy_uses"]
    assert contract["energy_helper_policy"]["identity_decision_allowed"] is False
    assert contract["runtime_embedding_field"] == "entry_service_responsibility_contract_v1"


def test_entry_service_responsibility_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert entry_service_responsibility_contract_doc_path(root).exists()


def test_entry_guard_contract_freezes_canonical_block_reasons():
    contract = ENTRY_GUARD_CONTRACT_V1

    assert contract["contract_version"] == "entry_guard_contract_v1"
    assert contract["scope"] == "canonical_consumer_action_block_reasons"
    assert contract["official_reason_field"] == "action_none_reason"
    assert contract["normalized_block_fields"] == [
        "consumer_block_reason",
        "consumer_block_kind",
        "consumer_block_source_layer",
        "consumer_block_is_execution",
        "consumer_block_is_semantic_non_action",
    ]
    assert contract["reason_registry"][0]["reason"] == "observe_confirm_missing"
    assert contract["reason_registry"][0]["kind"] == "semantic_non_action"
    assert contract["reason_registry"][3]["reason"] == "opposite_position_lock"
    assert contract["reason_registry"][3]["kind"] == "execution_block"
    assert contract["reason_registry"][-1]["reason"] == "hard_guard_volatility_too_high"
    assert contract["runtime_embedding_field"] == "entry_guard_contract_v1"


def test_classify_entry_guard_reason_separates_semantic_from_execution_blocks():
    semantic = classify_entry_guard_reason("preflight_action_blocked")
    execution = classify_entry_guard_reason("clustered_entry_price_zone")
    passthrough = classify_entry_guard_reason("observe_default")

    assert semantic["kind"] == "preflight_block"
    assert semantic["is_execution_block"] is False
    assert semantic["is_semantic_non_action"] is True
    assert execution["kind"] == "execution_block"
    assert execution["is_execution_block"] is True
    assert execution["source_layer"] == "cluster_guard"
    assert passthrough["kind"] == "semantic_non_action_passthrough"
    assert passthrough["canonical"] is False


def test_entry_guard_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert entry_guard_contract_doc_path(root).exists()


def test_exit_handoff_contract_freezes_canonical_exit_inputs():
    contract = EXIT_HANDOFF_CONTRACT_V1

    assert contract["contract_version"] == "exit_handoff_contract_v1"
    assert contract["official_input_fields"] == ["management_profile_id", "invalidation_id"]
    assert contract["compatibility_fallback_fields"] == ["entry_setup_id", "exit_profile"]
    assert contract["energy_helper_policy"]["usage"] == "future management hint only; no identity decisions"
    assert contract["energy_helper_policy"]["direct_net_utility_use_allowed"] is False
    assert contract["energy_helper_policy"]["identity_decision_allowed"] is False
    assert contract["canonical_management_profiles"] == [
        "reversal_profile",
        "breakout_hold_profile",
        "support_hold_profile",
        "breakdown_hold_profile",
        "mid_reclaim_fast_exit_profile",
        "mid_lose_fast_exit_profile",
    ]
    assert contract["canonical_profile_mapping"][1]["default_exit_profile"] == "hold_then_trail"


def test_resolve_exit_handoff_prefers_canonical_ids_before_setup_fallback():
    payload = resolve_exit_handoff(
        {
            "observe_confirm_v2": {
                "management_profile_id": "support_hold_profile",
                "invalidation_id": "lower_support_fail",
            },
            "entry_setup_id": "range_lower_reversal_buy",
            "exit_profile": "tight_protect",
        }
    )

    assert payload["management_profile_id"] == "support_hold_profile"
    assert payload["invalidation_id"] == "lower_support_fail"
    assert payload["entry_setup_id"] == "range_lower_reversal_buy"
    assert payload["handoff_source"] == "canonical_entry_handoff"


def test_exit_handoff_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert exit_handoff_contract_doc_path(root).exists()


def test_re_entry_contract_freezes_same_archetype_reconfirm_policy():
    contract = RE_ENTRY_CONTRACT_V1

    assert contract["contract_version"] == "re_entry_contract_v1"
    assert contract["scope"] == "canonical_re_entry_policy_from_consumer_handoff"
    assert contract["official_input_fields"] == [
        "current_observe_confirm.state",
        "current_observe_confirm.action",
        "current_observe_confirm.side",
        "current_observe_confirm.reason",
        "current_observe_confirm.archetype_id",
        "current_observe_confirm.invalidation_id",
        "prior_entry_archetype_id",
        "prior_entry_side",
        "prior_invalidation_id",
        "re_entry_cooldown_active",
        "box_state",
        "bb_state",
    ]
    assert contract["required_current_state"]["state"] == "CONFIRM"
    assert contract["required_current_state"]["same_archetype_confirm_required"] is True
    assert contract["energy_helper_policy"]["usage"] == "future management hint only; no identity decisions"
    assert contract["energy_helper_policy"]["direct_net_utility_use_allowed"] is False
    assert contract["energy_helper_policy"]["identity_decision_allowed"] is False
    assert contract["forbidden_middle_contexts"]["box_state"] == ["MIDDLE"]
    assert contract["forbidden_middle_contexts"]["bb_state"] == ["MID"]
    assert contract["reverse_after_invalidation_policy"]["immediate_reverse_allowed"] is False
    assert [item["reason"] for item in contract["blocked_reason_registry"]] == [
        "reentry_missing_prior_context",
        "reentry_same_archetype_confirm_required",
        "reentry_middle_averaging_forbidden",
        "reentry_immediate_reverse_after_invalidation_forbidden",
        "reentry_cooldown_active",
    ]


def test_resolve_re_entry_handoff_separates_persistence_cooldown_and_reverse_guard():
    eligible = resolve_re_entry_handoff(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
            },
            "prior_entry_archetype_id": "lower_hold_buy",
            "prior_entry_side": "BUY",
            "prior_invalidation_id": "lower_support_fail",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "re_entry_cooldown_active": False,
        }
    )
    cooldown_blocked = resolve_re_entry_handoff(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "archetype_id": "lower_hold_buy",
            },
            "prior_entry_archetype_id": "lower_hold_buy",
            "prior_entry_side": "BUY",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "re_entry_cooldown_active": True,
        }
    )
    middle_blocked = resolve_re_entry_handoff(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "archetype_id": "mid_reclaim_buy",
            },
            "prior_entry_archetype_id": "mid_reclaim_buy",
            "prior_entry_side": "BUY",
            "box_state": "MIDDLE",
            "bb_state": "MID",
        }
    )
    reverse_blocked = resolve_re_entry_handoff(
        {
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "archetype_id": "upper_reject_sell",
            },
            "prior_entry_archetype_id": "upper_reject_sell",
            "prior_entry_side": "BUY",
            "prior_invalidation_id": "lower_support_fail",
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
        }
    )

    assert eligible["eligible"] is True
    assert eligible["same_archetype_confirmed"] is True
    assert eligible["persistence_ok"] is True
    assert eligible["cooldown_ok"] is True
    assert eligible["blocked_reason"] == ""

    assert cooldown_blocked["eligible"] is False
    assert cooldown_blocked["same_archetype_confirmed"] is True
    assert cooldown_blocked["persistence_ok"] is True
    assert cooldown_blocked["cooldown_ok"] is False
    assert cooldown_blocked["blocked_reason"] == "reentry_cooldown_active"
    assert cooldown_blocked["blocked_reason_dimension"] == "cooldown"

    assert middle_blocked["eligible"] is False
    assert middle_blocked["middle_reentry_forbidden"] is True
    assert middle_blocked["blocked_reason"] == "reentry_middle_averaging_forbidden"
    assert middle_blocked["blocked_reason_dimension"] == "averaging"

    assert reverse_blocked["eligible"] is False
    assert reverse_blocked["same_archetype_confirmed"] is False
    assert reverse_blocked["reverse_after_invalidation_forbidden"] is True
    assert reverse_blocked["blocked_reason"] == "reentry_immediate_reverse_after_invalidation_forbidden"
    assert reverse_blocked["blocked_reason_dimension"] == "reverse_lock"


def test_re_entry_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert re_entry_contract_doc_path(root).exists()


def test_consumer_logging_contract_freezes_canonical_consumer_audit_fields():
    contract = CONSUMER_LOGGING_CONTRACT_V1

    assert contract["contract_version"] == "consumer_logging_contract_v1"
    assert contract["scope"] == "consumer_audit_logging_only"
    assert contract["official_fields"] == [
        "consumer_input_observe_confirm_field",
        "consumer_input_contract_version",
        "consumer_archetype_id",
        "consumer_invalidation_id",
        "consumer_management_profile_id",
        "consumer_setup_id",
        "consumer_guard_result",
        "consumer_effective_action",
        "consumer_block_reason",
        "consumer_block_kind",
        "consumer_block_source_layer",
        "consumer_handoff_contract_version",
    ]
    assert "energy_helper_v2" in contract["supplemental_fields"]
    assert contract["field_resolution"]["energy_helper_v2"].startswith("serialized canonical energy helper")
    assert contract["guard_result_values"] == ["PASS", "SEMANTIC_NON_ACTION", "EXECUTION_BLOCK"]
    assert contract["field_resolution"]["consumer_setup_id"] == "setup_id passthrough"


def test_resolve_consumer_guard_result_summarizes_pass_semantic_and_execution():
    assert resolve_consumer_guard_result(effective_action="BUY", block_kind="") == "PASS"
    assert resolve_consumer_guard_result(effective_action="NONE", block_kind="semantic_non_action") == "SEMANTIC_NON_ACTION"
    assert resolve_consumer_guard_result(effective_action="NONE", block_kind="execution_block") == "EXECUTION_BLOCK"
    assert resolve_consumer_guard_result(effective_action="NONE", block_kind="execution_hard_block") == "EXECUTION_BLOCK"


def test_consumer_logging_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_logging_contract_doc_path(root).exists()


def test_consumer_test_contract_freezes_required_behavior_axes():
    contract = CONSUMER_TEST_CONTRACT_V1

    assert contract["contract_version"] == "consumer_test_contract_v1"
    assert contract["scope"] == "consumer_regression_lock_only"
    assert [item["id"] for item in contract["required_behavior_axes"]] == [
        "setup_detector_naming_only",
        "entry_service_no_semantic_reinterpretation",
        "consumer_v2_canonical_v1_fallback",
        "handoff_ids_stable_per_archetype",
        "execution_guard_preserves_semantic_identity",
        "blocked_rows_keep_archetype_metadata",
        "energy_helper_usage_freeze",
    ]
    assert contract["required_behavior_axes"][0]["primary_test_file"] == "tests/unit/test_setup_detector.py"
    assert contract["supporting_runtime_contract_tests"] == [
        "tests/unit/test_context_classifier.py",
        "tests/unit/test_entry_engines.py",
        "tests/unit/test_decision_models.py",
        "tests/unit/test_prs_engine.py",
    ]
    assert contract["runtime_embedding_field"] == "consumer_test_contract_v1"


def test_consumer_test_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_test_contract_doc_path(root).exists()


def test_consumer_freeze_handoff_contract_closes_final_consumer_boundary():
    contract = CONSUMER_FREEZE_HANDOFF_V1

    assert contract["contract_version"] == "consumer_freeze_handoff_v1"
    assert contract["scope"] == "canonical_consumer_freeze_and_handoff_only"
    assert contract["official_handoff_helper"] == "resolve_consumer_handoff_payload"
    assert contract["consumer_handoff_sections"] == [
        "observe_confirm_resolution",
        "observe_confirm",
        "layer_mode_policy_resolution",
        "layer_mode_policy",
        "energy_helper",
        "setup_mapping_input",
        "setup_mapping",
        "exit_handoff",
        "re_entry_handoff",
    ]
    assert contract["future_policy_overlay"]["layer_mode_ready"] is True
    assert contract["component_handoff_policy"][2]["component"] == "WaitEngine"


def test_resolve_consumer_handoff_payload_keeps_setup_entry_exit_and_reentry_separated():
    payload = resolve_consumer_handoff_payload(
        {
            "market_mode": "TREND",
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.81,
                "reason": "trend_pullback_buy",
                "archetype_id": "mid_reclaim_buy",
                "invalidation_id": "mid_relose",
                "management_profile_id": "mid_reclaim_fast_exit_profile",
            },
            "layer_mode_policy_v1": {
                "layer_modes": [{"layer": "State", "mode": "assist"}],
                "effective_influences": [{"layer": "State", "active_effects": ["confidence_modulation", "soft_warning"]}],
                "suppressed_reasons": [],
                "confidence_adjustments": [],
                "hard_blocks": [],
                "mode_decision_trace": {"layers": [{"layer": "State", "identity_preserved": True}]},
                "identity_preserved": True,
            },
            "energy_helper_v2": {
                "action_readiness": 0.74,
                "soft_block_hint": {"active": False, "reason": "", "strength": 0.0},
                "metadata": {"utility_hints": {"wait_vs_enter_hint": "prefer_enter"}},
            },
            "prior_entry_archetype_id": "mid_reclaim_buy",
            "prior_entry_side": "BUY",
            "prior_invalidation_id": "mid_relose",
            "entry_setup_id": "range_lower_reversal_buy",
            "exit_profile": "tight_protect",
            "box_state": "LOWER",
            "bb_state": "LOWER_EDGE",
            "re_entry_cooldown_active": False,
        }
    )

    assert payload["canonical_only_ready"] is True
    assert payload["used_compatibility_fallback_v1"] is False
    assert payload["semantic_reinterpretation_required"] is False
    assert payload["observe_confirm_resolution"]["field_name"] == "observe_confirm_v2"
    assert payload["observe_confirm"]["archetype_id"] == "mid_reclaim_buy"
    assert payload["layer_mode_policy_resolution"]["field_name"] == "layer_mode_policy_v1"
    assert payload["policy_input_ready"] is True
    assert payload["policy_identity_preserved"] is True
    assert payload["energy_helper"]["action_readiness"] == 0.74
    assert payload["setup_mapping_input"]["market_mode"] == "TREND"
    assert payload["setup_mapping"]["setup_id"] == "trend_pullback_buy"
    assert payload["exit_handoff"]["management_profile_id"] == "mid_reclaim_fast_exit_profile"
    assert payload["re_entry_handoff"]["same_archetype_confirmed"] is True
    assert payload["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]


def test_consumer_freeze_handoff_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_freeze_handoff_doc_path(root).exists()


def test_consumer_scope_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert consumer_scope_contract_doc_path(root).exists()
