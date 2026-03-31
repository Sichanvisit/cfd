from pathlib import Path

from backend.services.layer_mode_contract import (
    LAYER_MODE_APPLICATION_CONTRACT_V1,
    LAYER_MODE_DEFAULT_POLICY_V1,
    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    LAYER_MODE_LAYER_INVENTORY_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_MODE_CONTRACT_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
    layer_mode_application_contract_doc_path,
    layer_mode_default_policy_doc_path,
    layer_mode_dual_write_doc_path,
    layer_mode_identity_guard_contract_doc_path,
    layer_mode_influence_semantics_doc_path,
    layer_mode_layer_inventory_doc_path,
    layer_mode_logging_replay_contract_doc_path,
    layer_mode_policy_overlay_output_contract_doc_path,
    LAYER_MODE_SCOPE_CONTRACT_V1,
    build_layer_mode_application_metadata,
    build_layer_mode_effective_metadata,
    build_layer_mode_identity_guard_metadata,
    build_layer_mode_influence_metadata,
    build_layer_mode_logging_replay_metadata,
    build_layer_mode_policy_overlay_metadata,
    resolve_layer_mode_handoff_payload,
    build_layer_mode_test_projection,
    layer_mode_contract_doc_path,
    layer_mode_freeze_handoff_doc_path,
    layer_mode_scope_contract_doc_path,
    layer_mode_test_contract_doc_path,
)


def test_layer_mode_contract_freezes_canonical_mode_values():
    contract = LAYER_MODE_MODE_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_contract_v1"
    assert contract["scope"] == "canonical_layer_mode_values_only"
    assert [item["mode"] for item in contract["canonical_modes"]] == ["shadow", "assist", "enforce"]
    assert contract["mode_order"] == ["shadow", "assist", "enforce"]
    assert contract["runtime_embedding_field"] == "layer_mode_contract_v1"


def test_layer_mode_layer_inventory_freezes_mode_addressable_semantic_layers():
    contract = LAYER_MODE_LAYER_INVENTORY_V1

    assert contract["contract_version"] == "layer_mode_layer_inventory_v1"
    assert contract["scope"] == "semantic_layer_targets_for_mode_only"
    assert contract["layer_order"] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    assert [item["layer"] for item in contract["layers"]] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    assert contract["layers"][0]["raw_fields"] == ["position_snapshot_v2"]
    assert contract["layers"][-1]["raw_fields"] == [
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ]
    assert contract["runtime_embedding_field"] == "layer_mode_layer_inventory_v1"


def test_layer_mode_default_policy_freezes_current_defaults_and_target_sequences():
    contract = LAYER_MODE_DEFAULT_POLICY_V1

    assert contract["contract_version"] == "layer_mode_default_policy_v1"
    assert contract["scope"] == "migration_aware_default_layer_modes_only"
    assert [item["layer"] for item in contract["policy_rows"]] == [
        "Position",
        "Response",
        "State",
        "Evidence",
        "Belief",
        "Barrier",
        "Forecast",
    ]
    assert contract["policy_rows"][0]["current_effective_default_mode"] == "enforce"
    assert contract["policy_rows"][2]["target_mode_sequence"] == ["assist", "enforce"]
    assert contract["policy_rows"][4]["target_mode_sequence"] == ["shadow", "assist", "enforce"]
    assert contract["policy_rows"][-1]["current_effective_default_mode"] == "assist"
    assert contract["policy_rows"][-1]["target_mode_sequence"] == ["assist", "enforce"]
    assert contract["runtime_embedding_field"] == "layer_mode_default_policy_v1"


def test_layer_mode_dual_write_contract_freezes_raw_effective_pairs():
    contract = LAYER_MODE_DUAL_WRITE_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_dual_write_v1"
    assert contract["scope"] == "raw_effective_dual_write_only"
    assert contract["effective_trace_field"] == "layer_mode_effective_trace_v1"
    assert contract["layer_rows"][0]["effective_fields"] == ["position_snapshot_effective_v1"]
    assert contract["layer_rows"][4]["effective_fields"] == ["belief_state_effective_v1"]
    assert contract["layer_rows"][-1]["effective_fields"] == ["forecast_effective_policy_v1"]
    assert contract["runtime_embedding_field"] == "layer_mode_dual_write_contract_v1"


def test_layer_mode_effective_metadata_builder_preserves_raw_and_effective_bridge():
    payload = build_layer_mode_effective_metadata(
        {
            "position_snapshot_v2": {"vector": {"x_box": -0.4}},
            "response_vector_v2": {"lower_hold_up": 1.0},
            "state_vector_v2": {"range_reversal_gain": 1.1},
            "evidence_vector_v1": {"buy_total_evidence": 0.8},
            "belief_state_v1": {"buy_belief": 0.6},
            "barrier_state_v1": {"buy_barrier": 0.1},
            "forecast_features_v1": {"metadata": {"signal_timeframe": "15M"}},
            "transition_forecast_v1": {"p_buy_confirm": 0.7},
            "trade_management_forecast_v1": {"p_continue_favor": 0.6},
            "forecast_gap_metrics_v1": {"transition_side_separation": 0.2},
        }
    )

    assert payload["position_snapshot_effective_v1"] == {"vector": {"x_box": -0.4}}
    assert payload["belief_state_effective_v1"] == {"buy_belief": 0.6}
    assert payload["forecast_effective_policy_v1"]["policy_overlay_applied"] is True
    assert payload["forecast_effective_policy_v1"]["utility_overlay_applied"] is True
    assert payload["forecast_effective_policy_v1"]["forecast_features_v1"]["metadata"]["signal_timeframe"] == "15M"
    assert payload["layer_mode_effective_trace_v1"]["dual_write_contract_version"] == "layer_mode_dual_write_v1"
    assert payload["layer_mode_effective_trace_v1"]["layers"][0]["block_explainability_ready"] is True


def test_layer_mode_influence_semantics_freeze_global_and_layer_specific_effects():
    contract = LAYER_MODE_INFLUENCE_SEMANTICS_V1

    assert contract["contract_version"] == "layer_mode_influence_semantics_v1"
    assert contract["scope"] == "mode_to_execution_influence_matrix_only"
    assert contract["global_mode_semantics"][0]["mode"] == "shadow"
    assert contract["global_mode_semantics"][1]["allowed_effects"] == [
        "confidence_modulation",
        "priority_boost",
        "reason_annotation",
        "soft_warning",
    ]
    barrier_row = next(row for row in contract["layer_rows"] if row["layer"] == "Barrier")
    forecast_row = next(row for row in contract["layer_rows"] if row["layer"] == "Forecast")
    assert "execution_veto" in barrier_row["enforce_effects"]
    assert forecast_row["assist_effects"] == ["confidence_modulation", "priority_boost", "reason_annotation"]
    assert forecast_row["forbidden_even_in_enforce"] == ["execution_veto"]
    assert contract["runtime_embedding_field"] == "layer_mode_influence_semantics_v1"


def test_layer_mode_influence_metadata_builder_tracks_current_default_effects():
    payload = build_layer_mode_influence_metadata()

    trace = payload["layer_mode_influence_trace_v1"]
    assert trace["influence_semantics_contract_version"] == "layer_mode_influence_semantics_v1"
    assert trace["current_mode_source"] == "layer_mode_default_policy_v1"
    position_row = next(row for row in trace["layers"] if row["layer"] == "Position")
    state_row = next(row for row in trace["layers"] if row["layer"] == "State")
    barrier_row = next(row for row in trace["layers"] if row["layer"] == "Barrier")
    forecast_row = next(row for row in trace["layers"] if row["layer"] == "Forecast")
    assert position_row["current_effective_mode"] == "enforce"
    assert position_row["hard_gate_allowed"] is True
    assert state_row["active_effects"] == ["confidence_modulation", "reason_annotation", "soft_warning"]
    assert barrier_row["active_effects"] == ["metadata_log_only", "trace_only"]
    assert forecast_row["current_effective_mode"] == "assist"
    assert forecast_row["active_effects"] == ["confidence_modulation", "priority_boost", "reason_annotation"]


def test_layer_mode_application_contract_freezes_layer_specific_rollout_roles():
    contract = LAYER_MODE_APPLICATION_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_application_contract_v1"
    assert contract["scope"] == "layer_specific_application_policy_only"
    position_row = next(row for row in contract["layer_rows"] if row["layer"] == "Position")
    belief_row = next(row for row in contract["layer_rows"] if row["layer"] == "Belief")
    forecast_row = next(row for row in contract["layer_rows"] if row["layer"] == "Forecast")
    assert position_row["first_semantically_active_mode"] == "enforce"
    assert "zone_side_contradiction_veto" in position_row["enforce_application"]
    assert belief_row["first_semantically_active_mode"] == "assist"
    assert forecast_row["identity_guard_fields"] == ["archetype_id", "side"]
    assert forecast_row["forbidden_application"] == ["archetype_rewrite", "side_rewrite", "execution_veto"]
    assert contract["runtime_embedding_field"] == "layer_mode_application_contract_v1"


def test_layer_mode_application_metadata_builder_tracks_current_layer_application_state():
    payload = build_layer_mode_application_metadata()

    trace = payload["layer_mode_application_trace_v1"]
    assert trace["application_contract_version"] == "layer_mode_application_contract_v1"
    position_row = next(row for row in trace["layers"] if row["layer"] == "Position")
    state_row = next(row for row in trace["layers"] if row["layer"] == "State")
    belief_row = next(row for row in trace["layers"] if row["layer"] == "Belief")
    forecast_row = next(row for row in trace["layers"] if row["layer"] == "Forecast")
    assert position_row["application_state"] == "enforce_active"
    assert state_row["application_state"] == "assist_active"
    assert state_row["active_application"] == ["regime_filter", "confidence_modulation", "soft_warning"]
    assert belief_row["application_state"] == "standby"
    assert forecast_row["application_state"] == "assist_active"
    assert forecast_row["forbidden_application"] == ["archetype_rewrite", "side_rewrite", "execution_veto"]


def test_layer_mode_identity_guard_contract_freezes_protected_fields_and_allowed_adjustments():
    contract = LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_identity_guard_v1"
    assert contract["scope"] == "layer_identity_guard_only"
    assert contract["routing_policy_contract_ref"] == "observe_confirm_routing_policy_v2"
    assert contract["confidence_semantics_contract_ref"] == "observe_confirm_confidence_semantics_v2"
    assert contract["protected_fields"] == ["archetype_id", "side"]
    forecast_row = next(row for row in contract["focus_layers"] if row["layer"] == "Forecast")
    assert forecast_row["allowed_adjustments"] == [
        "confidence",
        "action_readiness",
        "confirm_to_wait",
        "block_reason_annotation",
    ]
    assert forecast_row["forbidden_adjustments"] == ["archetype_rewrite", "side_rewrite", "setup_rename", "execution_veto"]
    assert contract["runtime_embedding_field"] == "layer_mode_identity_guard_contract_v1"


def test_layer_mode_identity_guard_metadata_builder_tracks_always_on_guard_state():
    payload = build_layer_mode_identity_guard_metadata()

    trace = payload["layer_mode_identity_guard_trace_v1"]
    assert trace["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert trace["routing_policy_contract_ref"] == "observe_confirm_routing_policy_v2"
    belief_row = next(row for row in trace["layers"] if row["layer"] == "Belief")
    barrier_row = next(row for row in trace["layers"] if row["layer"] == "Barrier")
    forecast_row = next(row for row in trace["layers"] if row["layer"] == "Forecast")
    assert belief_row["guard_active"] is True
    assert barrier_row["protected_fields"] == ["archetype_id", "side"]
    assert forecast_row["forbidden_adjustments"] == ["archetype_rewrite", "side_rewrite", "setup_rename", "execution_veto"]
    assert forecast_row["current_effective_mode"] == "assist"


def test_layer_mode_policy_overlay_output_contract_freezes_canonical_payload_shape():
    contract = LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert contract["scope"] == "canonical_policy_applied_overlay_output_only"
    assert contract["canonical_output_field"] == "layer_mode_policy_v1"
    assert contract["required_fields"] == [
        "layer_modes",
        "effective_influences",
        "suppressed_reasons",
        "confidence_adjustments",
        "hard_blocks",
        "mode_decision_trace",
    ]
    assert contract["runtime_embedding_field"] == "layer_mode_policy_overlay_output_contract_v1"


def test_layer_mode_policy_overlay_metadata_builder_emits_bridge_ready_policy_payload():
    payload = build_layer_mode_policy_overlay_metadata()

    policy = payload["layer_mode_policy_v1"]
    assert policy["contract_version"] == "layer_mode_policy_v1"
    assert policy["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert policy["overlay_execution_state"] == "bridge_ready_no_runtime_delta"
    assert policy["identity_preserved"] is True
    assert [row["layer"] for row in policy["layer_modes"]] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    assert next(row for row in policy["effective_influences"] if row["layer"] == "State")["active_effects"] == [
        "confidence_modulation",
        "reason_annotation",
        "soft_warning",
    ]
    assert next(row for row in policy["effective_influences"] if row["layer"] == "Forecast")["active_effects"] == [
        "confidence_modulation",
        "priority_boost",
        "reason_annotation",
    ]
    assert next(row for row in policy["effective_influences"] if row["layer"] == "Forecast")["identity_guard_active"] is True
    assert policy["suppressed_reasons"] == []
    assert policy["confidence_adjustments"] == []
    assert policy["hard_blocks"] == []
    assert policy["mode_decision_trace"]["trace_version"] == "layer_mode_mode_decision_trace_v1"
    assert next(row for row in policy["mode_decision_trace"]["layers"] if row["layer"] == "Forecast")["protected_fields"] == [
        "archetype_id",
        "side",
    ]


def test_layer_mode_logging_replay_contract_freezes_replayable_audit_shape():
    contract = LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert contract["scope"] == "replayable_layer_mode_audit_only"
    assert contract["canonical_output_field"] == "layer_mode_logging_replay_v1"
    assert contract["required_fields"] == [
        "configured_modes",
        "raw_result_fields",
        "effective_result_fields",
        "applied_adjustments",
        "block_suppress_reasons",
        "final_consumer_action",
    ]
    assert contract["runtime_embedding_field"] == "layer_mode_logging_replay_contract_v1"


def test_layer_mode_logging_replay_metadata_builder_emits_replay_ready_summary():
    payload = build_layer_mode_logging_replay_metadata(
        {
            "consumer_effective_action": "BUY",
            "consumer_guard_result": "PASS",
            "consumer_block_reason": "",
            "consumer_block_kind": "",
            "consumer_block_source_layer": "",
            **build_layer_mode_policy_overlay_metadata(),
        }
    )

    replay = payload["layer_mode_logging_replay_v1"]
    assert replay["contract_version"] == "layer_mode_logging_replay_v1"
    assert replay["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert replay["replay_ready"] is True
    assert replay["configured_modes"][0]["layer"] == "Position"
    assert replay["raw_result_fields"][0]["fields"] == ["position_snapshot_v2"]
    assert replay["effective_result_fields"][-1]["fields"] == ["forecast_effective_policy_v1"]
    assert next(row for row in replay["applied_adjustments"] if row["layer"] == "Forecast")["identity_guard_active"] is True
    assert replay["block_suppress_reasons"]["policy_suppressed_reasons"] == []
    assert replay["final_consumer_action"]["consumer_effective_action"] == "BUY"
    assert replay["final_consumer_action"]["consumer_guard_result"] == "PASS"


def test_layer_mode_test_contract_freezes_required_behavior_axes():
    contract = LAYER_MODE_TEST_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_test_contract_v1"
    assert contract["scope"] == "layer_mode_regression_lock_only"
    assert contract["official_test_helper"] == "build_layer_mode_test_projection"
    assert [item["id"] for item in contract["required_behavior_axes"]] == [
        "deterministic_mode_output",
        "shadow_no_action_change",
        "assist_identity_preserving_modulation",
        "enforce_identity_preserving_block",
        "forecast_enforce_no_archetype_rewrite",
        "barrier_enforce_confirm_to_observe",
        "raw_effective_dual_write_present",
    ]
    assert contract["supporting_runtime_contract_tests"] == [
        "tests/unit/test_context_classifier.py",
        "tests/unit/test_entry_engines.py",
        "tests/unit/test_decision_models.py",
        "tests/unit/test_prs_engine.py",
    ]
    assert contract["runtime_embedding_field"] == "layer_mode_test_contract_v1"


def test_layer_mode_test_projection_is_deterministic_for_same_semantic_input():
    first = build_layer_mode_test_projection(
        mode_overrides={"State": "assist", "Forecast": "shadow"},
    )
    second = build_layer_mode_test_projection(
        mode_overrides={"State": "assist", "Forecast": "shadow"},
    )

    assert first == second


def test_layer_mode_test_projection_shadow_keeps_action_and_identity_unchanged():
    projection = build_layer_mode_test_projection(
        mode_overrides={"Belief": "shadow", "Barrier": "shadow", "Forecast": "shadow"},
    )

    assert projection["effective_observe_confirm"]["action"] == projection["source_observe_confirm"]["action"]
    assert projection["effective_observe_confirm"]["state"] == projection["source_observe_confirm"]["state"]
    assert projection["projected_consumer_action"] == "BUY"
    assert projection["identity_preserved"] is True


def test_layer_mode_test_projection_assist_modulates_confidence_without_identity_rewrite():
    projection = build_layer_mode_test_projection(
        mode_overrides={"State": "assist", "Forecast": "assist"},
    )

    assert projection["effective_observe_confirm"]["confidence"] != projection["source_observe_confirm"]["confidence"]
    assert projection["projected_consumer_action"] == "BUY"
    assert projection["hard_blocks"] == []
    assert projection["identity_preserved"] is True


def test_layer_mode_test_projection_enforce_may_block_but_keeps_identity():
    projection = build_layer_mode_test_projection(
        mode_overrides={"State": "enforce"},
        force_hard_block_layers=["State"],
    )

    assert projection["projected_consumer_action"] == "NONE"
    assert projection["projected_consumer_guard_result"] == "EXECUTION_BLOCK"
    assert projection["hard_blocks"][0]["layer"] == "State"
    assert projection["effective_observe_confirm"]["archetype_id"] == projection["source_observe_confirm"]["archetype_id"]
    assert projection["effective_observe_confirm"]["side"] == projection["source_observe_confirm"]["side"]
    assert projection["identity_preserved"] is True


def test_layer_mode_test_projection_forecast_enforce_may_downgrade_without_rewriting_archetype():
    projection = build_layer_mode_test_projection(
        mode_overrides={"Forecast": "enforce"},
    )

    assert projection["effective_observe_confirm"]["state"] == "OBSERVE"
    assert projection["effective_observe_confirm"]["action"] == "WAIT"
    assert projection["effective_observe_confirm"]["archetype_id"] == projection["source_observe_confirm"]["archetype_id"]
    assert projection["effective_observe_confirm"]["side"] == projection["source_observe_confirm"]["side"]
    assert projection["identity_preserved"] is True


def test_layer_mode_test_projection_barrier_enforce_suppresses_confirm_to_observe():
    projection = build_layer_mode_test_projection(
        mode_overrides={"Barrier": "enforce"},
    )

    assert projection["effective_observe_confirm"]["state"] == "OBSERVE"
    assert projection["effective_observe_confirm"]["action"] == "WAIT"
    assert projection["suppressed_reasons"][0]["layer"] == "Barrier"
    assert projection["identity_preserved"] is True


def test_layer_mode_test_projection_keeps_raw_and_effective_dual_write_together():
    projection = build_layer_mode_test_projection(
        mode_overrides={"Belief": "assist"},
    )

    raw_effective = projection["raw_effective_bundle"]
    assert "position_snapshot_effective_v1" in raw_effective
    assert "belief_state_effective_v1" in raw_effective
    assert "forecast_effective_policy_v1" in raw_effective
    assert raw_effective["layer_mode_effective_trace_v1"]["layers"][0]["block_explainability_ready"] is True


def test_layer_mode_freeze_handoff_contract_closes_final_overlay_boundary():
    contract = LAYER_MODE_FREEZE_HANDOFF_V1

    assert contract["contract_version"] == "layer_mode_freeze_handoff_v1"
    assert contract["scope"] == "canonical_layer_mode_freeze_and_handoff_only"
    assert contract["official_handoff_helper"] == "resolve_layer_mode_handoff_payload"
    assert contract["handoff_sections"] == [
        "raw_semantic_fields",
        "effective_semantic_fields",
        "policy_overlay",
        "logging_replay",
        "consumer_policy_bridge",
        "energy_future_role",
    ]
    assert contract["policy_overlay_position"] == "above consumer handoff and below execution"
    assert contract["energy_future_role"]["standalone_semantic_layer"] is False
    assert contract["energy_future_role"]["allowed_future_roles"] == ["utility_helper", "compression_helper"]


def test_resolve_layer_mode_handoff_payload_keeps_compute_dual_write_and_policy_overlay_together():
    raw = {
        **build_layer_mode_effective_metadata(
            {
                "position_snapshot_v2": {"vector": {"x_box": -0.4}},
                "response_vector_v2": {"lower_hold_up": 1.0},
                "state_vector_v2": {"range_reversal_gain": 1.1},
                "evidence_vector_v1": {"buy_total_evidence": 0.8},
                "belief_state_v1": {"buy_belief": 0.6},
                "barrier_state_v1": {"buy_barrier": 0.1},
                "forecast_features_v1": {"metadata": {"signal_timeframe": "15M"}},
                "transition_forecast_v1": {"p_buy_confirm": 0.7},
                "trade_management_forecast_v1": {"p_continue_favor": 0.6},
                "forecast_gap_metrics_v1": {"transition_side_separation": 0.2},
            }
        ),
        **build_layer_mode_policy_overlay_metadata(mode_overrides={"State": "assist"}),
        **build_layer_mode_logging_replay_metadata(
            {
                "consumer_effective_action": "BUY",
                "consumer_guard_result": "PASS",
                **build_layer_mode_policy_overlay_metadata(mode_overrides={"State": "assist"}),
            }
        ),
        "position_snapshot_v2": {"vector": {"x_box": -0.4}},
        "response_vector_v2": {"lower_hold_up": 1.0},
        "state_vector_v2": {"range_reversal_gain": 1.1},
        "evidence_vector_v1": {"buy_total_evidence": 0.8},
        "belief_state_v1": {"buy_belief": 0.6},
        "barrier_state_v1": {"buy_barrier": 0.1},
        "forecast_features_v1": {"metadata": {"signal_timeframe": "15M"}},
        "transition_forecast_v1": {"p_buy_confirm": 0.7},
        "trade_management_forecast_v1": {"p_continue_favor": 0.6},
        "forecast_gap_metrics_v1": {"transition_side_separation": 0.2},
    }
    payload = resolve_layer_mode_handoff_payload(raw)

    assert payload["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert payload["all_semantic_layers_compute"] is True
    assert payload["mode_controls_influence_only"] is True
    assert payload["dual_write_ready"] is True
    assert payload["policy_overlay_ready"] is True
    assert payload["logging_replay_ready"] is True
    assert payload["consumer_policy_bridge"]["input_field"] == "layer_mode_policy_v1"
    assert payload["consumer_policy_bridge"]["identity_preserved"] is True
    assert payload["energy_future_role"]["allowed_future_roles"] == ["utility_helper", "compression_helper"]
    assert next(row for row in payload["raw_semantic_fields"] if row["layer"] == "Forecast")["present"] is True
    assert next(row for row in payload["effective_semantic_fields"] if row["layer"] == "Forecast")["present"] is True


def test_layer_mode_scope_contract_freezes_always_compute_boundary():
    contract = LAYER_MODE_SCOPE_CONTRACT_V1

    assert contract["contract_version"] == "layer_mode_scope_v1"
    assert contract["scope"] == "always_compute_policy_overlay_only"
    assert contract["mode_contract_v1"]["contract_version"] == LAYER_MODE_MODE_CONTRACT_V1["contract_version"]
    assert contract["layer_inventory_v1"]["contract_version"] == LAYER_MODE_LAYER_INVENTORY_V1["contract_version"]
    assert contract["default_mode_policy_v1"]["contract_version"] == LAYER_MODE_DEFAULT_POLICY_V1["contract_version"]
    assert contract["dual_write_contract_v1"]["contract_version"] == LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"]
    assert contract["influence_semantics_v1"]["contract_version"] == LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"]
    assert contract["application_contract_v1"]["contract_version"] == LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"]
    assert contract["identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert contract["policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert contract["logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert contract["test_contract_v1"]["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert contract["freeze_handoff_v1"]["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert contract["raw_output_policy"]["raw_outputs_always_emitted"] is True
    assert contract["raw_output_policy"]["compute_disable_allowed"] is False
    assert contract["raw_output_policy"]["dual_write_contract_version"] == "layer_mode_dual_write_v1"
    assert contract["raw_output_policy"]["effective_trace_field"] == "layer_mode_effective_trace_v1"
    assert contract["raw_output_policy"]["influence_semantics_contract_version"] == "layer_mode_influence_semantics_v1"
    assert contract["raw_output_policy"]["influence_trace_field"] == "layer_mode_influence_trace_v1"
    assert contract["raw_output_policy"]["application_contract_version"] == "layer_mode_application_contract_v1"
    assert contract["raw_output_policy"]["application_trace_field"] == "layer_mode_application_trace_v1"
    assert contract["raw_output_policy"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert contract["raw_output_policy"]["identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert contract["raw_output_policy"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert contract["raw_output_policy"]["policy_overlay_output_field"] == "layer_mode_policy_v1"
    assert contract["raw_output_policy"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert contract["raw_output_policy"]["logging_replay_field"] == "layer_mode_logging_replay_v1"
    assert contract["integration_target"]["consumer_handoff_contract"] == "consumer_freeze_handoff_v1"
    assert contract["integration_target"]["layer_mode_ready"] is True
    assert "turning semantic layer computation on or off" in contract["non_responsibilities"]
    assert contract["runtime_embedding_field"] == "layer_mode_scope_contract_v1"


def test_layer_mode_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_contract_doc_path(root).exists()


def test_layer_mode_layer_inventory_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_layer_inventory_doc_path(root).exists()


def test_layer_mode_default_policy_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_default_policy_doc_path(root).exists()


def test_layer_mode_dual_write_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_dual_write_doc_path(root).exists()


def test_layer_mode_influence_semantics_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_influence_semantics_doc_path(root).exists()


def test_layer_mode_application_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_application_contract_doc_path(root).exists()


def test_layer_mode_identity_guard_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_identity_guard_contract_doc_path(root).exists()


def test_layer_mode_policy_overlay_output_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_policy_overlay_output_contract_doc_path(root).exists()


def test_layer_mode_logging_replay_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_logging_replay_contract_doc_path(root).exists()


def test_layer_mode_test_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_test_contract_doc_path(root).exists()


def test_layer_mode_freeze_handoff_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_freeze_handoff_doc_path(root).exists()


def test_layer_mode_scope_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert layer_mode_scope_contract_doc_path(root).exists()
