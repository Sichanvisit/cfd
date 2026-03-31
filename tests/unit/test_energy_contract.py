from backend.services.energy_contract import (
    ENERGY_LOGGING_REPLAY_CONTRACT_V1,
    ENERGY_SCOPE_CONTRACT_V1,
    ENERGY_TEST_CONTRACT_V1,
    attach_energy_consumer_usage_trace,
    build_energy_helper_v2,
    resolve_energy_migration_bridge_state,
    resolve_energy_helper_input,
    resolve_entry_service_energy_usage,
)


def _container(
    *,
    buy_total: float = 0.60,
    sell_total: float = 0.20,
    buy_reversal: float = 0.55,
    sell_reversal: float = 0.10,
    buy_continuation: float = 0.35,
    sell_continuation: float = 0.12,
    buy_belief: float = 0.58,
    sell_belief: float = 0.18,
    buy_persistence: float = 0.52,
    sell_persistence: float = 0.16,
    buy_barrier: float = 0.18,
    sell_barrier: float = 0.42,
    conflict_barrier: float = 0.10,
    middle_chop_barrier: float = 0.08,
    direction_policy_barrier: float = 0.05,
    liquidity_barrier: float = 0.04,
    p_buy_confirm: float = 0.62,
    p_sell_confirm: float = 0.24,
    p_false_break: float = 0.18,
    p_reversal_success: float = 0.44,
    p_continue_favor: float = 0.56,
    p_fail_now: float = 0.16,
    p_recover_after_pullback: float = 0.30,
    p_reach_tp1: float = 0.48,
    p_better_reentry_if_cut: float = 0.22,
    transition_side_separation: float = 0.20,
    observe_state: str = "CONFIRM",
    observe_action: str = "BUY",
    observe_side: str = "BUY",
) -> dict:
    return {
        "evidence_vector_effective_v1": {
            "buy_total_evidence": buy_total,
            "sell_total_evidence": sell_total,
            "buy_reversal_evidence": buy_reversal,
            "sell_reversal_evidence": sell_reversal,
            "buy_continuation_evidence": buy_continuation,
            "sell_continuation_evidence": sell_continuation,
        },
        "belief_state_effective_v1": {
            "buy_belief": buy_belief,
            "sell_belief": sell_belief,
            "buy_persistence": buy_persistence,
            "sell_persistence": sell_persistence,
        },
        "barrier_state_effective_v1": {
            "buy_barrier": buy_barrier,
            "sell_barrier": sell_barrier,
            "conflict_barrier": conflict_barrier,
            "middle_chop_barrier": middle_chop_barrier,
            "direction_policy_barrier": direction_policy_barrier,
            "liquidity_barrier": liquidity_barrier,
        },
        "forecast_effective_policy_v1": {
            "transition_forecast_v1": {
                "p_buy_confirm": p_buy_confirm,
                "p_sell_confirm": p_sell_confirm,
                "p_false_break": p_false_break,
                "p_reversal_success": p_reversal_success,
            },
            "trade_management_forecast_v1": {
                "p_continue_favor": p_continue_favor,
                "p_fail_now": p_fail_now,
                "p_recover_after_pullback": p_recover_after_pullback,
                "p_reach_tp1": p_reach_tp1,
                "p_better_reentry_if_cut": p_better_reentry_if_cut,
            },
            "forecast_gap_metrics_v1": {
                "transition_side_separation": transition_side_separation,
            },
        },
        "observe_confirm_v2": {
            "state": observe_state,
            "action": observe_action,
            "side": observe_side,
            "archetype_id": "lower_hold_buy",
            "invalidation_id": "lower_support_fail",
            "management_profile_id": "support_hold_profile",
        },
    }


def test_energy_scope_contract_freezes_helper_only_role():
    contract = ENERGY_SCOPE_CONTRACT_V1

    assert contract["contract_version"] == "energy_scope_v1"
    assert contract["canonical_output_field"] == "energy_helper_v2"
    assert contract["compatibility_runtime_field"] == "energy_snapshot"
    assert contract["scope_freeze_v1"]["contract_version"] == "energy_scope_freeze_v1"
    assert contract["scope_freeze_v1"]["semantic_layer_owner"] is False
    assert contract["scope_freeze_v1"]["identity_field_mutation_allowed"] is False
    assert contract["scope_freeze_v1"]["selected_side_semantics"] == "utility_only_not_semantic_side"
    assert contract["scope_freeze_v1"]["protected_identity_fields"] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    assert contract["role_contract_v1"]["official_role"] == "utility_compression_helper"
    assert contract["role_contract_v1"]["semantic_question_owner"] == "semantic_layer"
    assert contract["role_contract_v1"]["utility_question_owner"] == "energy_helper"
    assert contract["role_contract_v1"]["owns_situation_interpretation"] is False
    assert contract["role_contract_v1"]["owns_execution_pressure_compression"] is True
    assert contract["role_contract_v1"]["role_boundary"] == {
        "semantic_layer_question": "what situation is happening",
        "energy_question": "how much the current setup should be pushed or suppressed for action",
    }
    assert contract["input_contract_v1"]["required_fields"] == [
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ]
    assert contract["input_contract_v1"]["optional_fields"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert contract["input_contract_v1"]["allowed_observe_confirm_subfields"] == [
        "action",
        "side",
    ]
    assert contract["input_contract_v1"]["forbidden_observe_confirm_subfields"] == [
        "state",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "reason",
        "confidence",
    ]
    assert "raw_detector_score" in contract["input_contract_v1"]["forbidden_direct_inputs"]
    assert "legacy_rule_branch" in contract["input_contract_v1"]["forbidden_direct_inputs"]
    assert "response_raw_snapshot_v1" in contract["input_contract_v1"]["forbidden_direct_inputs"]
    assert "evidence_vector_v1" in contract["input_contract_v1"]["forbidden_direct_inputs"]
    assert contract["output_contract_v1"]["required_fields"] == [
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
    ]
    assert contract["output_contract_v1"]["exact_top_level_shape_required"] is True
    assert contract["output_contract_v1"]["optional_top_level_fields"] == []
    assert contract["output_contract_v1"]["top_level_field_count"] == 10
    assert contract["output_contract_v1"]["field_semantics"]["selected_side"] == (
        "utility-facing preferred side only; not semantic side and not identity ownership"
    )
    assert contract["output_contract_v1"]["metadata_policy"] == {
        "role": "audit_trace_only",
        "semantic_label_emission_allowed": False,
        "allowed_content": [
            "contract_versions",
            "source_trace",
            "component_contributions",
            "support_vs_suppression_breakdown",
            "final_net_utility",
            "utility_hints",
            "consumer_usage_trace",
            "identity_guard_trace",
            "migration_bridge_trace",
        ],
    }
    assert "side" in contract["output_contract_v1"]["forbidden_outputs"]
    assert contract["output_contract_v1"]["forbidden_semantic_label_like_outputs"] == [
        "state",
        "state_label",
        "semantic_truth_label",
        "setup_id",
        "setup_label",
        "setup_name",
        "archetype_id",
        "archetype_label",
        "invalidation_id",
        "management_profile_id",
        "primary_label",
        "secondary_context_label",
        "market_context_label",
        "outcome_label",
    ]
    assert contract["composition_semantics_v1"]["component_roles"] == {
        "evidence": "setup_strength_support",
        "belief": "persistence_and_continuation_bias",
        "barrier": "suppression_and_risk_pressure",
        "forecast": "forward_support_or_confirm_wait_modulation",
    }
    assert contract["composition_semantics_v1"]["component_output_bindings"] == {
        "evidence": [
            "support_total",
            "action_readiness",
            "continuation_support",
            "reversal_support",
        ],
        "belief": [
            "support_total",
            "action_readiness",
            "continuation_support",
        ],
        "barrier": [
            "suppression_pressure",
            "action_readiness",
            "net_utility",
            "soft_block_hint",
        ],
        "forecast": [
            "forecast_support",
            "support_total",
            "action_readiness",
            "confidence_adjustment_hint",
            "soft_block_hint",
        ],
    }
    assert contract["composition_semantics_v1"]["sign_convention"] == {
        "support_terms": "+",
        "suppression_terms": "-",
        "evidence": "+",
        "belief": "+",
        "barrier": "-",
        "forecast": "+",
    }
    assert contract["composition_semantics_v1"]["support_components"] == [
        "evidence",
        "belief",
        "forecast",
    ]
    assert contract["composition_semantics_v1"]["suppression_components"] == [
        "barrier",
    ]
    assert contract["composition_semantics_v1"]["output_direction_rules"] == {
        "continuation_support": "+",
        "reversal_support": "+",
        "forecast_support": "+",
        "suppression_pressure": "-",
        "action_readiness": "mixed_support_minus_suppression",
        "net_utility": "mixed_support_minus_suppression",
    }
    assert contract["identity_non_ownership_v1"]["energy_is_identity_owner"] is False
    assert contract["identity_non_ownership_v1"]["canonical_identity_owner"] == "observe_confirm_v2"
    assert contract["identity_non_ownership_v1"]["identity_creation_allowed"] is False
    assert contract["identity_non_ownership_v1"]["identity_mutation_allowed"] is False
    assert contract["identity_non_ownership_v1"]["protected_fields"] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    assert contract["identity_non_ownership_v1"]["allowed_context_reads"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert contract["identity_non_ownership_v1"]["forbidden_identity_reads"] == [
        "observe_confirm_v2.archetype_id",
        "observe_confirm_v2.invalidation_id",
        "observe_confirm_v2.management_profile_id",
    ]
    assert contract["identity_non_ownership_v1"]["forbidden_operations"] == [
        "create_identity",
        "rewrite_identity",
        "override_identity",
        "infer_identity",
        "backfill_identity",
    ]
    assert contract["consumer_usage_v1"]["canonical_energy_field"] == "energy_helper_v2"
    assert contract["consumer_usage_v1"]["usage_mode"] == "consumer_hint_only"
    assert contract["consumer_usage_v1"]["component_usage"][0] == {
        "component": "SetupDetector",
        "usage": "not required; optional reason annotation only",
        "allowed_energy_fields": [],
        "optional_annotation_fields": [
            "soft_block_hint.reason",
            "metadata.utility_hints.priority_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
    }
    assert contract["consumer_usage_v1"]["component_usage"][1] == {
        "component": "EntryService",
        "usage": "readiness, priority, confidence hint, and soft block hint only",
        "allowed_energy_fields": [
            "action_readiness",
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
    }
    assert contract["consumer_usage_v1"]["component_usage"][2] == {
        "component": "WaitEngine",
        "usage": "enter versus wait comparison hint only",
        "allowed_energy_fields": [
            "action_readiness",
            "soft_block_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
    }
    assert contract["consumer_usage_v1"]["component_usage"][3]["component"] == "Exit"
    assert contract["consumer_usage_v1"]["component_usage"][4]["component"] == "ReEntry"
    assert "selected_side as canonical side" in contract["consumer_usage_v1"]["forbidden_consumer_uses"]
    assert "energy helper remains optional for setup naming and may annotate reasons only" in (
        contract["consumer_usage_v1"]["principles"]
    )
    assert contract["layer_mode_integration_v1"] == {
        "contract_version": "energy_layer_mode_integration_v1",
        "scope": "post_layer_mode_bridge_only",
        "bridge_position": "post_layer_mode_effective_outputs",
        "helper_identity": "post_layer_mode_utility_bridge_helper",
        "effective_world_required": True,
        "reads_raw_semantics": False,
        "reads_effective_semantics": True,
        "raw_semantic_output_allowed": False,
        "pre_layer_mode_semantic_attachment_allowed": False,
        "required_effective_fields": [
            "evidence_vector_effective_v1",
            "belief_state_effective_v1",
            "barrier_state_effective_v1",
            "forecast_effective_policy_v1",
        ],
        "official_build_order": [
            "build_layer_mode_effective_metadata",
            "build_energy_helper_v2",
        ],
        "principles": [
            "energy helper sits above effective semantic outputs, not below semantic computation",
            "energy helper consumes effective layer payloads after layer mode bridge output exists",
            "energy helper reads the effective world only and never raw semantic outputs for utility compression",
            "energy helper is a bridge helper after layer mode, not a semantic layer participant before it",
            "energy helper is compatible with future policy overlays because it does not own identity",
        ],
        "documentation_path": "docs/energy_scope_contract.md",
    }
    assert contract["utility_bridge_v1"] == {
        "contract_version": "energy_utility_bridge_v1",
        "scope": "hint_bridge_only",
        "bridge_strategy": "hint_first_no_direct_order_decision",
        "direct_net_utility_use_allowed": False,
        "net_utility_role": "summary_only_not_direct_order_gate",
        "canonical_bridge_hints": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "preferred_consumer_hints": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "forbidden_direct_use": [
            "place_order_directly_from_net_utility",
            "block_order_directly_from_net_utility",
            "rank_entries_directly_from_net_utility",
            "wait_gate_directly_from_net_utility",
            "rewrite_observe_confirm_action",
        ],
        "component_bridge_policy": {
            "EntryService": [
                "confidence_adjustment_hint",
                "soft_block_hint",
                "metadata.utility_hints.priority_hint",
            ],
            "WaitEngine": [
                "soft_block_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
            "Exit": [
                "confidence_adjustment_hint",
                "soft_block_hint",
            ],
            "ReEntry": [
                "confidence_adjustment_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
        },
        "principles": [
            "net_utility remains a signed summary for audit and compression, not a direct live order trigger",
            "consumers should route through intermediate hints before any live decision path",
            "utility bridge stays advisory and identity-preserving even when net_utility is high or low",
        ],
        "documentation_path": "docs/energy_scope_contract.md",
    }
    assert contract["migration_dual_write_v1"] == {
        "contract_version": "energy_migration_dual_write_v1",
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
        "rules": [
            "new helper payload is canonical for post-layer-mode utility compression",
            "dual-write must preserve canonical helper output and compatibility runtime snapshot together during migration",
            "legacy energy snapshot may remain alive as a runtime compatibility bridge only",
            "legacy energy snapshot may rebuild helper traces only when canonical energy_helper_v2 is absent",
            "consumers should read canonical helper output first and never promote legacy snapshot back into semantic ownership",
            "legacy energy snapshot may not affect identity ownership or direct live consumer gating",
            "live gate behavior must remain unchanged until a later promotion phase explicitly upgrades it",
            "migration should preserve replayability of both helper output and legacy bridge references",
        ],
        "documentation_path": "docs/energy_scope_contract.md",
    }
    assert "semantic truth creation" in contract["role_contract_v1"]["non_responsibilities"]
    assert "situation interpretation" in contract["role_contract_v1"]["non_responsibilities"]
    assert "summarize support-versus-suppression pressure for execution-facing consumers" in (
        contract["role_contract_v1"]["responsibilities"]
    )
    assert "13.10_logging_replay_freeze" in contract["completed_definitions"]
    assert "13.11_test_contract_freeze" in contract["completed_definitions"]
    assert "13.12_freeze_handoff" in contract["completed_definitions"]


def test_energy_test_contract_freezes_required_regression_axes():
    contract = ENERGY_TEST_CONTRACT_V1

    assert contract["contract_version"] == "energy_test_contract_v1"
    assert contract["scope"] == "energy_helper_required_regression_axes"
    assert [axis["id"] for axis in contract["required_behavior_axes"]] == [
        "deterministic_effective_input",
        "barrier_increases_suppression",
        "evidence_belief_raise_readiness",
        "forecast_cannot_change_identity",
        "energy_cannot_change_identity_fields",
        "raw_and_effective_source_trace_preserved",
        "migration_dual_write_preserved",
    ]
    assert contract["required_behavior_axes"][0] == {
        "id": "deterministic_effective_input",
        "goal": "same semantic or effective input after layer mode produces the same helper output",
        "input_equivalence_domain": "effective_semantics_plus_observe_confirm_action_side_only",
        "primary_test_file": "tests/unit/test_energy_contract.py",
        "covered_by_tests": [
            "test_energy_helper_v2_is_deterministic_for_same_effective_inputs",
        ],
    }
    assert contract["required_behavior_axes"][3] == {
        "id": "forecast_cannot_change_identity",
        "goal": "forecast may modulate forward support or confirm-wait bias but cannot create or mutate identity ownership",
        "primary_test_file": "tests/unit/test_energy_contract.py",
        "covered_by_tests": [
            "test_energy_helper_v2_forecast_changes_do_not_mutate_identity_or_selected_observe_side",
        ],
    }
    assert contract["required_behavior_axes"][4] == {
        "id": "energy_cannot_change_identity_fields",
        "goal": "energy cannot create or change archetype_id, side, invalidation_id, or management_profile_id",
        "primary_test_file": "tests/unit/test_energy_contract.py",
        "covered_by_tests": [
            "test_energy_helper_v2_uses_observe_confirm_side_without_owning_identity_fields",
            "test_energy_helper_v2_ignores_observe_confirm_identity_fields_for_output_identity",
        ],
    }
    assert contract["required_behavior_axes"][5] == {
        "id": "raw_and_effective_source_trace_preserved",
        "goal": "raw semantic source trace and effective helper source trace remain together for replay",
        "primary_test_file": "tests/unit/test_context_classifier.py",
        "covered_by_tests": [
            "test_context_classifier_preserves_raw_and_effective_source_trace_for_energy_replay",
        ],
    }
    assert contract["required_behavior_axes"][6] == {
        "id": "migration_dual_write_preserved",
        "goal": "legacy energy snapshot and canonical helper are both recorded during migration",
        "primary_test_file": "tests/unit/test_context_classifier.py",
        "covered_by_tests": [
            "test_energy_helper_v2_marks_legacy_snapshot_presence_during_migration_dual_write",
            "test_context_classifier_dual_writes_energy_helper_and_legacy_snapshot_for_migration_replay",
        ],
    }
    assert contract["principles"] == [
        "test contract freezes required replay-safe regression axes, not live calibration thresholds",
        "forecast may change utility compression values but never identity ownership",
        "migration coverage must preserve both canonical helper output and the legacy bridge until a later promotion step explicitly changes it",
    ]
    assert ENERGY_SCOPE_CONTRACT_V1["test_contract_v1"] == contract


def test_energy_freeze_handoff_marks_completion_and_owner_split():
    contract = ENERGY_SCOPE_CONTRACT_V1["freeze_handoff_v1"]

    assert contract == {
        "contract_version": "energy_freeze_handoff_v1",
        "status": "freeze_complete_ready_for_handoff",
        "completion_meaning": "energy_redefinition_foundation_complete",
        "acceptance_criteria": [
            "energy is no longer a standalone meaning layer",
            "energy is a helper above effective semantic outputs",
            "consumers read identity from observe_confirm, policy from layer_mode, and utility hints from energy helper",
            "legacy energy snapshot remains a compatibility bridge only",
            "energy_engine may be gradually absorbed into a utility or decision helper path without regaining semantic ownership",
        ],
        "ownership_handoff": {
            "identity_owner": "observe_confirm_v2",
            "policy_owner": "layer_mode",
            "utility_hint_owner": "energy_helper_v2",
        },
        "layer_position": {
            "energy_is_independent_semantic_layer": False,
            "energy_reads_effective_semantic_outputs": True,
            "energy_runtime_role": "post_layer_mode_helper",
        },
        "consumer_read_stack": [
            "ObserveConfirm.identity",
            "LayerMode.policy",
            "Energy.utility_hint",
        ],
        "future_absorption_path": {
            "allowed": True,
            "current_runtime_surface": "energy_helper_v2",
            "legacy_engine_name": "energy_engine",
            "target_direction": "utility_or_decision_helper",
            "migration_style": "gradual_absorption_without_semantic_reownership",
        },
        "deferred_followups": [
            "13.6_live_consumer_gate_promotion",
            "13.8_direct_utility_router_integration",
        ],
        "documentation_path": "docs/energy_scope_contract.md",
    }


def test_energy_logging_replay_contract_freezes_replay_sections_and_consumer_usage_trace():
    contract = ENERGY_LOGGING_REPLAY_CONTRACT_V1

    assert contract["contract_version"] == "energy_logging_replay_contract_v1"
    assert contract["scope"] == "replayable_energy_helper_audit_only"
    assert contract["required_sections"] == [
        "input_source_fields",
        "component_contributions",
        "support_vs_suppression_breakdown",
        "selected_side_breakdown",
        "final_net_utility",
        "legacy_bridge",
        "utility_hints",
        "consumer_usage_trace",
    ]
    assert contract["consumer_usage_required_fields"] == [
        "component",
        "usage_source",
        "usage_mode",
        "consumed_fields",
        "final_net_utility",
        "effective_action",
        "guard_result",
        "block_reason",
        "decision_outcome",
        "wait_state",
        "wait_reason",
        "used_for_identity_decision",
        "used_for_direct_order_gate",
        "live_gate_applied",
    ]
    assert contract["runtime_embedding_field"] == "energy_logging_replay_contract_v1"


def test_energy_helper_v2_exposes_exact_canonical_fields():
    payload = build_energy_helper_v2(_container())

    expected_fields = {
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
    assert set(payload.keys()) == expected_fields
    assert len(payload) == 10
    assert payload["selected_side"] == "BUY"
    assert payload["metadata"]["selected_side_source"] == "observe_confirm_v2"
    assert payload["metadata"]["identity_guard"]["identity_preserved"] is True
    assert payload["metadata"]["input_source_fields"] == {
        "evidence_vector_effective_v1": True,
        "belief_state_effective_v1": True,
        "barrier_state_effective_v1": True,
        "forecast_effective_policy_v1": True,
        "observe_confirm_v2.action": True,
        "observe_confirm_v2.side": True,
    }
    assert payload["metadata"]["input_freeze"]["applied"] is True
    assert payload["metadata"]["input_freeze"]["required_fields"] == [
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ]
    assert payload["metadata"]["input_freeze"]["optional_fields"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert payload["metadata"]["input_freeze"]["allowed_observe_confirm_subfields"] == ["action", "side"]
    assert payload["metadata"]["input_freeze"]["reads_only_contract_inputs"] is True
    assert payload["metadata"]["layer_mode_integration_freeze"] == {
        "applied": True,
        "contract_version": "energy_layer_mode_integration_v1",
        "bridge_position": "post_layer_mode_effective_outputs",
        "helper_identity": "post_layer_mode_utility_bridge_helper",
        "effective_world_required": True,
        "reads_effective_semantics": True,
        "reads_raw_semantics": False,
        "raw_semantic_output_allowed": False,
        "pre_layer_mode_semantic_attachment_allowed": False,
        "required_effective_fields": [
            "evidence_vector_effective_v1",
            "belief_state_effective_v1",
            "barrier_state_effective_v1",
            "forecast_effective_policy_v1",
        ],
        "effective_fields_present": [
            "evidence_vector_effective_v1",
            "belief_state_effective_v1",
            "barrier_state_effective_v1",
            "forecast_effective_policy_v1",
        ],
        "official_build_order": [
            "build_layer_mode_effective_metadata",
            "build_energy_helper_v2",
        ],
        "post_layer_mode_helper": True,
    }
    assert payload["metadata"]["utility_bridge_freeze"] == {
        "applied": True,
        "contract_version": "energy_utility_bridge_v1",
        "bridge_strategy": "hint_first_no_direct_order_decision",
        "direct_net_utility_use_allowed": False,
        "net_utility_role": "summary_only_not_direct_order_gate",
        "canonical_bridge_hints": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "preferred_consumer_hints": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "forbidden_direct_use": [
            "place_order_directly_from_net_utility",
            "block_order_directly_from_net_utility",
            "rank_entries_directly_from_net_utility",
            "wait_gate_directly_from_net_utility",
            "rewrite_observe_confirm_action",
        ],
        "component_bridge_policy": {
            "EntryService": [
                "confidence_adjustment_hint",
                "soft_block_hint",
                "metadata.utility_hints.priority_hint",
            ],
            "WaitEngine": [
                "soft_block_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
            "Exit": [
                "confidence_adjustment_hint",
                "soft_block_hint",
            ],
            "ReEntry": [
                "confidence_adjustment_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
        },
        "hint_payload": {
            "confidence_adjustment_hint": dict(payload["confidence_adjustment_hint"]),
            "soft_block_hint": dict(payload["soft_block_hint"]),
            "priority_hint": payload["metadata"]["utility_hints"]["priority_hint"],
            "wait_vs_enter_hint": payload["metadata"]["utility_hints"]["wait_vs_enter_hint"],
        },
        "net_utility_available_for_audit_only": True,
    }
    assert payload["metadata"]["migration_dual_write_freeze"] == {
        "applied": True,
        "contract_version": "energy_migration_dual_write_v1",
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
        "legacy_snapshot_present": False,
    }
    assert payload["metadata"]["logging_replay_freeze"] == {
        "applied": True,
        "contract_version": "energy_logging_replay_contract_v1",
        "required_sections": [
            "input_source_fields",
            "component_contributions",
            "support_vs_suppression_breakdown",
            "selected_side_breakdown",
            "final_net_utility",
            "legacy_bridge",
            "utility_hints",
            "consumer_usage_trace",
        ],
        "consumer_usage_required_fields": [
            "component",
            "usage_source",
            "usage_mode",
            "consumed_fields",
            "final_net_utility",
            "effective_action",
            "guard_result",
            "block_reason",
            "decision_outcome",
            "wait_state",
            "wait_reason",
            "used_for_identity_decision",
            "used_for_direct_order_gate",
            "live_gate_applied",
        ],
        "required_sections_present": [
            "input_source_fields",
            "component_contributions",
            "support_vs_suppression_breakdown",
            "selected_side_breakdown",
            "final_net_utility",
            "legacy_bridge",
            "utility_hints",
            "consumer_usage_trace",
        ],
        "final_net_utility": payload["net_utility"],
        "consumer_usage_trace_present": False,
        "consumer_usage_source": "not_yet_consumed",
        "consumer_usage_component": "",
        "consumer_usage_mode": "not_yet_consumed",
        "replay_explanation_ready": True,
    }
    assert payload["metadata"]["scope_freeze"]["applied"] is True
    assert payload["metadata"]["scope_freeze"]["helper_only"] is True
    assert payload["metadata"]["scope_freeze"]["semantic_layer_owner"] is False
    assert payload["metadata"]["scope_freeze"]["identity_field_mutation_allowed"] is False
    assert payload["metadata"]["scope_freeze"]["selected_side_is_identity_side"] is False
    assert payload["metadata"]["scope_freeze"]["selected_side_semantics"] == "utility_only_not_semantic_side"
    assert payload["metadata"]["scope_freeze"]["protected_identity_fields"] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    assert "side" in payload["metadata"]["scope_freeze"]["forbidden_output_fields_absent"]
    assert "archetype_id" in payload["metadata"]["scope_freeze"]["forbidden_output_fields_absent"]
    assert payload["metadata"]["role_freeze"]["applied"] is True
    assert payload["metadata"]["role_freeze"]["official_role"] == "utility_compression_helper"
    assert payload["metadata"]["role_freeze"]["semantic_question_owner"] == "semantic_layer"
    assert payload["metadata"]["role_freeze"]["utility_question_owner"] == "energy_helper"
    assert payload["metadata"]["role_freeze"]["owns_situation_interpretation"] is False
    assert payload["metadata"]["role_freeze"]["owns_execution_pressure_compression"] is True
    assert payload["metadata"]["role_freeze"]["role_boundary"] == {
        "semantic_layer_question": "what situation is happening",
        "energy_question": "how much the current setup should be pushed or suppressed for action",
    }
    assert payload["metadata"]["output_freeze"]["applied"] is True
    assert payload["metadata"]["output_freeze"]["canonical_output_field"] == "energy_helper_v2"
    assert payload["metadata"]["output_freeze"]["exact_top_level_shape_required"] is True
    assert payload["metadata"]["output_freeze"]["optional_top_level_fields"] == []
    assert payload["metadata"]["output_freeze"]["canonical_top_level_fields"] == [
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
    ]
    assert payload["metadata"]["output_freeze"]["metadata_role"] == "audit_trace_only"
    assert payload["metadata"]["output_freeze"]["semantic_label_emission_allowed"] is False
    assert payload["metadata"]["output_freeze"]["forbidden_top_level_fields_absent"] == [
        "side",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "semantic_truth_label",
        "setup_id",
    ]
    assert payload["metadata"]["output_freeze"]["forbidden_semantic_label_like_fields_absent"] == [
        "state",
        "state_label",
        "semantic_truth_label",
        "setup_id",
        "setup_label",
        "setup_name",
        "archetype_id",
        "archetype_label",
        "invalidation_id",
        "management_profile_id",
        "primary_label",
        "secondary_context_label",
        "market_context_label",
        "outcome_label",
    ]
    assert payload["metadata"]["composition_freeze"]["applied"] is True
    assert payload["metadata"]["composition_freeze"]["contract_version"] == "energy_composition_semantics_v1"
    assert payload["metadata"]["composition_freeze"]["component_roles"] == {
        "evidence": "setup_strength_support",
        "belief": "persistence_and_continuation_bias",
        "barrier": "suppression_and_risk_pressure",
        "forecast": "forward_support_or_confirm_wait_modulation",
    }
    assert payload["metadata"]["composition_freeze"]["sign_convention"] == {
        "support_terms": "+",
        "suppression_terms": "-",
        "evidence": "+",
        "belief": "+",
        "barrier": "-",
        "forecast": "+",
    }
    assert payload["metadata"]["composition_freeze"]["support_components"] == [
        "evidence",
        "belief",
        "forecast",
    ]
    assert payload["metadata"]["composition_freeze"]["suppression_components"] == [
        "barrier",
    ]
    assert payload["metadata"]["composition_freeze"]["output_direction_rules"] == {
        "continuation_support": "+",
        "reversal_support": "+",
        "forecast_support": "+",
        "suppression_pressure": "-",
        "action_readiness": "mixed_support_minus_suppression",
        "net_utility": "mixed_support_minus_suppression",
    }
    assert payload["metadata"]["composition_freeze"]["selected_side_component_summary"] == {
        "evidence": 0.6,
        "belief": 0.559,
        "barrier": 0.18,
        "forecast": 0.4475,
    }
    assert payload["metadata"]["identity_non_ownership_freeze"]["applied"] is True
    assert payload["metadata"]["identity_non_ownership_freeze"]["contract_version"] == (
        "energy_identity_non_ownership_v1"
    )
    assert payload["metadata"]["identity_non_ownership_freeze"]["energy_is_identity_owner"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["canonical_identity_owner"] == "observe_confirm_v2"
    assert payload["metadata"]["identity_non_ownership_freeze"]["identity_creation_allowed"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["identity_mutation_allowed"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["allowed_context_reads"] == [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ]
    assert payload["metadata"]["identity_non_ownership_freeze"]["forbidden_identity_reads"] == [
        "observe_confirm_v2.archetype_id",
        "observe_confirm_v2.invalidation_id",
        "observe_confirm_v2.management_profile_id",
    ]
    assert payload["metadata"]["identity_non_ownership_freeze"]["forbidden_operations"] == [
        "create_identity",
        "rewrite_identity",
        "override_identity",
        "infer_identity",
        "backfill_identity",
    ]
    assert payload["metadata"]["identity_non_ownership_freeze"]["selected_side_is_identity_side"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["identity_fields_absent_from_output"] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    assert payload["metadata"]["final_net_utility"] == payload["net_utility"]
    assert payload["metadata"]["consumer_usage_trace"] == {
        "contract_version": "consumer_usage_trace_v1",
        "recorded": False,
        "usage_source": "not_yet_consumed",
        "component": "",
        "usage_mode": "not_yet_consumed",
        "consumed_fields": [],
        "branch_records": [],
        "selected_side": "BUY",
        "action_readiness": payload["action_readiness"],
        "final_net_utility": payload["net_utility"],
        "priority_hint": payload["metadata"]["utility_hints"]["priority_hint"],
        "wait_vs_enter_hint": payload["metadata"]["utility_hints"]["wait_vs_enter_hint"],
        "gap_dominant_hint": payload["metadata"]["utility_hints"]["gap_dominant_hint"],
        "forecast_branch_hint": payload["metadata"]["utility_hints"]["forecast_branch_hint"],
        "soft_block_active": payload["soft_block_hint"]["active"],
        "soft_block_reason": payload["soft_block_hint"]["reason"],
        "soft_block_strength": payload["soft_block_hint"]["strength"],
        "confidence_adjustment_direction": payload["confidence_adjustment_hint"]["direction"],
        "confidence_adjustment_delta": 0.0,
        "forecast_gap_usage_active": payload["metadata"]["forecast_gap_usage_v1"]["active"],
        "effective_action": "",
        "guard_result": "",
        "block_reason": "",
        "block_kind": "",
        "block_source_layer": "",
        "decision_outcome": "",
        "wait_state": "",
        "wait_reason": "",
        "used_for_identity_decision": False,
        "used_for_direct_order_gate": False,
        "live_gate_applied": False,
        "identity_preserved": True,
    }
    assert payload["metadata"]["forecast_gap_usage_v1"] == {
        "active": False,
        "transition_confirm_fake_gap": 0.0,
        "wait_confirm_gap": 0.0,
        "management_continue_fail_gap": 0.0,
        "management_recover_reentry_gap": 0.0,
        "hold_exit_gap": 0.0,
        "same_side_flip_gap": 0.0,
        "belief_barrier_tension_gap": 0.0,
        "transition_side_separation": 0.2,
        "dominant_execution_gap": "",
        "branch_hint": "balanced_branch_support",
        "confirm_release_active": False,
        "continue_support_active": False,
        "continue_drag_active": False,
        "recover_reentry_support_active": False,
        "hold_extension_active": False,
        "same_side_flip_risk_active": False,
        "gap_release_active": False,
        "gap_drag_active": False,
        "confidence_assist_active": False,
        "soft_block_assist_active": False,
        "priority_assist_active": False,
        "wait_assist_active": False,
        "usage_mode": "gap_trace_only",
    }
    assert payload["metadata"]["observe_confirm_context"] == {
        "action": "BUY",
        "side": "BUY",
        "allowed_subfields_only": True,
    }
    for forbidden_field in (
        "state",
        "state_label",
        "semantic_truth_label",
        "setup_id",
        "setup_label",
        "setup_name",
        "archetype_id",
        "archetype_label",
        "invalidation_id",
        "management_profile_id",
        "primary_label",
        "secondary_context_label",
        "market_context_label",
        "outcome_label",
    ):
        assert forbidden_field not in payload


def test_energy_helper_v2_is_deterministic_for_same_effective_inputs():
    container = _container()

    first = build_energy_helper_v2(container)
    second = build_energy_helper_v2(container)

    assert first == second


def test_energy_helper_v2_raises_suppression_when_barrier_grows():
    low_barrier = build_energy_helper_v2(_container(buy_barrier=0.08, conflict_barrier=0.02, liquidity_barrier=0.02))
    high_barrier = build_energy_helper_v2(_container(buy_barrier=0.82, conflict_barrier=0.40, liquidity_barrier=0.35))

    assert high_barrier["suppression_pressure"] > low_barrier["suppression_pressure"]
    assert high_barrier["action_readiness"] < low_barrier["action_readiness"]
    assert high_barrier["soft_block_hint"]["active"] is True


def test_energy_helper_v2_raises_readiness_when_evidence_and_belief_grow():
    weak = build_energy_helper_v2(
        _container(
            buy_total=0.18,
            buy_reversal=0.12,
            buy_continuation=0.08,
            buy_belief=0.16,
            buy_persistence=0.12,
            p_buy_confirm=0.28,
            p_continue_favor=0.24,
        )
    )
    strong = build_energy_helper_v2(
        _container(
            buy_total=0.88,
            buy_reversal=0.74,
            buy_continuation=0.62,
            buy_belief=0.80,
            buy_persistence=0.76,
            p_buy_confirm=0.72,
            p_continue_favor=0.68,
        )
    )

    assert strong["action_readiness"] > weak["action_readiness"]
    assert strong["net_utility"] > weak["net_utility"]


def test_energy_helper_v2_uses_observe_confirm_side_without_owning_identity_fields():
    payload = build_energy_helper_v2(
        _container(
            sell_total=0.92,
            sell_reversal=0.78,
            sell_continuation=0.66,
            sell_belief=0.84,
            sell_persistence=0.82,
            p_sell_confirm=0.75,
            observe_state="OBSERVE",
            observe_action="WAIT",
            observe_side="BUY",
        )
    )

    assert payload["selected_side"] == "BUY"
    assert "archetype_id" not in payload
    assert "side" not in payload
    assert "invalidation_id" not in payload
    assert "management_profile_id" not in payload
    assert payload["metadata"]["observe_confirm_context"] == {
        "action": "WAIT",
        "side": "BUY",
        "allowed_subfields_only": True,
    }
    assert payload["metadata"]["scope_freeze"]["selected_side_is_identity_side"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["energy_is_identity_owner"] is False
    assert payload["metadata"]["identity_non_ownership_freeze"]["selected_side_is_identity_side"] is False
    assert payload["soft_block_hint"]["reason"] == "observe_confirm_wait"


def test_energy_helper_v2_ignores_observe_confirm_identity_fields_for_output_identity():
    container = _container()
    mutated_container = _container()
    mutated_container["observe_confirm_v2"]["archetype_id"] = "upper_break_buy"
    mutated_container["observe_confirm_v2"]["invalidation_id"] = "upper_break_fail"
    mutated_container["observe_confirm_v2"]["management_profile_id"] = "breakout_profile"

    original_payload = build_energy_helper_v2(container)
    mutated_payload = build_energy_helper_v2(mutated_container)

    assert mutated_payload == original_payload


def test_energy_helper_v2_forecast_changes_do_not_mutate_identity_or_selected_observe_side():
    baseline = build_energy_helper_v2(
        _container(
            observe_action="BUY",
            observe_side="BUY",
            p_buy_confirm=0.74,
            p_sell_confirm=0.18,
            p_false_break=0.08,
            p_reversal_success=0.24,
            p_continue_favor=0.70,
            p_fail_now=0.06,
        )
    )
    forecast_shifted = build_energy_helper_v2(
        _container(
            observe_action="BUY",
            observe_side="BUY",
            p_buy_confirm=0.10,
            p_sell_confirm=0.92,
            p_false_break=0.82,
            p_reversal_success=0.88,
            p_continue_favor=0.12,
            p_fail_now=0.78,
        )
    )

    assert baseline["selected_side"] == "BUY"
    assert forecast_shifted["selected_side"] == "BUY"
    assert baseline["forecast_support"] != forecast_shifted["forecast_support"]
    assert baseline["net_utility"] != forecast_shifted["net_utility"]
    assert forecast_shifted["metadata"]["selected_side_source"] == "observe_confirm_v2"
    assert forecast_shifted["metadata"]["observe_confirm_context"] == {
        "action": "BUY",
        "side": "BUY",
        "allowed_subfields_only": True,
    }
    assert forecast_shifted["metadata"]["identity_guard"]["identity_preserved"] is True
    assert forecast_shifted["metadata"]["identity_non_ownership_freeze"]["identity_fields_absent_from_output"] == [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ]
    for forbidden_field in ("archetype_id", "side", "invalidation_id", "management_profile_id"):
        assert forbidden_field not in forecast_shifted


def test_energy_helper_v2_ignores_forbidden_direct_inputs_when_effective_inputs_match():
    container = _container()
    noisy_container = {
        **container,
        "raw_detector_score": 999.0,
        "legacy_rule_branch": "force_sell",
        "response_raw_snapshot_v1": {"buy_score": 0.01, "sell_score": 0.99},
        "response_vector_v2": {"buy_pressure": 0.0, "sell_pressure": 1.0},
        "state_raw_snapshot_v1": {"label": "panic"},
        "state_vector_v2": {"volatility_state": "shock"},
        "evidence_vector_v1": {"buy_total_evidence": 0.01, "sell_total_evidence": 0.99},
    }

    clean_payload = build_energy_helper_v2(container)
    noisy_payload = build_energy_helper_v2(noisy_container)

    for field in (
        "selected_side",
        "action_readiness",
        "continuation_support",
        "reversal_support",
        "suppression_pressure",
        "forecast_support",
        "net_utility",
        "confidence_adjustment_hint",
        "soft_block_hint",
    ):
        assert noisy_payload[field] == clean_payload[field]
    assert noisy_payload["metadata"]["component_contributions"] == clean_payload["metadata"]["component_contributions"]
    assert noisy_payload["metadata"]["support_vs_suppression_breakdown"] == (
        clean_payload["metadata"]["support_vs_suppression_breakdown"]
    )
    assert noisy_payload["metadata"]["input_freeze"]["ignored_available_direct_inputs"] == [
        "raw_detector_score",
        "legacy_rule_branch",
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "evidence_vector_v1",
    ]


def test_energy_helper_v2_marks_legacy_snapshot_presence_during_migration_dual_write():
    payload = build_energy_helper_v2(
        _container(),
        legacy_energy_snapshot={
            "buy_force": 0.61,
            "sell_force": 0.19,
            "net_force": 0.42,
        },
    )

    assert payload["metadata"]["migration_dual_write_freeze"]["legacy_snapshot_present"] is True
    assert payload["metadata"]["migration_dual_write_freeze"]["live_gate_promotion_allowed"] is False
    assert payload["metadata"]["legacy_bridge"] == {
        "runtime_field": "energy_snapshot",
        "present": True,
        "buy_force": 0.61,
        "sell_force": 0.19,
        "net_force": 0.42,
    }


def test_resolve_energy_migration_bridge_state_uses_legacy_only_when_helper_missing():
    bridge = resolve_energy_migration_bridge_state(
        {
            "energy_snapshot": {
                "buy_force": 0.61,
                "sell_force": 0.19,
                "net_force": 0.42,
            }
        }
    )
    canonical = resolve_energy_migration_bridge_state(
        {
            "energy_helper_v2": build_energy_helper_v2(_container()),
            "energy_snapshot": {
                "buy_force": 0.11,
                "sell_force": 0.81,
                "net_force": -0.70,
            },
        }
    )

    assert bridge["used_compatibility_bridge"] is True
    assert bridge["canonical_payload_present"] is False
    assert bridge["compatibility_snapshot_present"] is True
    assert bridge["legacy_identity_input_allowed"] is False
    assert bridge["legacy_live_gate_allowed"] is False
    assert bridge["legacy_rebuild_scope"] == "replay_or_transition_when_helper_missing_only"

    assert canonical["used_compatibility_bridge"] is False
    assert canonical["canonical_payload_present"] is True
    assert canonical["compatibility_snapshot_present"] is True


def test_attach_energy_consumer_usage_trace_records_actual_consumer_usage_for_replay():
    payload = build_energy_helper_v2(_container())

    traced = attach_energy_consumer_usage_trace(
        payload,
        component="EntryService",
        consumed_fields=[
            "action_readiness",
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        usage_mode="advisory_only",
        effective_action="NONE",
        guard_result="SEMANTIC_NON_ACTION",
        block_reason="observe_confirm_wait",
        block_kind="semantic_non_action",
        block_source_layer="consumer_guard",
        decision_outcome="wait_selected",
        wait_state="ACTIVE",
        wait_reason="observe_confirm_wait",
        live_gate_applied=False,
    )

    assert traced["metadata"]["consumer_usage_trace"] == {
        "contract_version": "consumer_usage_trace_v1",
        "recorded": True,
        "usage_source": "recorded",
        "component": "EntryService",
        "usage_mode": "advisory_only",
        "consumed_fields": [
            "action_readiness",
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        "branch_records": [],
        "selected_side": traced["selected_side"],
        "action_readiness": traced["action_readiness"],
        "final_net_utility": traced["net_utility"],
        "priority_hint": traced["metadata"]["utility_hints"]["priority_hint"],
        "wait_vs_enter_hint": traced["metadata"]["utility_hints"]["wait_vs_enter_hint"],
        "gap_dominant_hint": traced["metadata"]["utility_hints"]["gap_dominant_hint"],
        "forecast_branch_hint": traced["metadata"]["utility_hints"]["forecast_branch_hint"],
        "soft_block_active": traced["soft_block_hint"]["active"],
        "soft_block_reason": traced["soft_block_hint"]["reason"],
        "soft_block_strength": traced["soft_block_hint"]["strength"],
        "confidence_adjustment_direction": traced["confidence_adjustment_hint"]["direction"],
        "confidence_adjustment_delta": 0.0,
        "forecast_gap_usage_active": traced["metadata"]["forecast_gap_usage_v1"]["active"],
        "effective_action": "NONE",
        "guard_result": "SEMANTIC_NON_ACTION",
        "block_reason": "observe_confirm_wait",
        "block_kind": "semantic_non_action",
        "block_source_layer": "consumer_guard",
        "decision_outcome": "wait_selected",
        "wait_state": "ACTIVE",
        "wait_reason": "observe_confirm_wait",
        "used_for_identity_decision": False,
        "used_for_direct_order_gate": False,
        "live_gate_applied": False,
        "identity_preserved": True,
    }
    assert traced["metadata"]["logging_replay_freeze"]["consumer_usage_trace_present"] is True
    assert traced["metadata"]["logging_replay_freeze"]["consumer_usage_source"] == "recorded"
    assert traced["metadata"]["logging_replay_freeze"]["consumer_usage_component"] == "EntryService"
    assert traced["metadata"]["logging_replay_freeze"]["consumer_usage_mode"] == "advisory_only"


def test_resolve_entry_service_energy_usage_returns_not_consumed_when_live_branch_never_used_helper():
    usage = resolve_entry_service_energy_usage(
        {
            "core_reason": "core_shadow_confirm_action",
            "consumer_block_reason": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_confidence_delta": 0.0,
        }
    )

    assert usage == {
        "component": "EntryService",
        "usage_source": "inferred",
        "consumed_fields": [],
        "branch_records": [],
        "usage_mode": "not_consumed",
        "live_gate_applied": False,
    }


def test_resolve_entry_service_energy_usage_records_only_actual_fields_for_soft_block_branch():
    usage = resolve_entry_service_energy_usage(
        {
            "core_reason": "energy_soft_block",
            "consumer_block_reason": "energy_soft_block",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_confidence_delta": 0.0,
        }
    )

    assert usage == {
        "component": "EntryService",
        "usage_source": "inferred",
        "consumed_fields": [
            "action_readiness",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        "branch_records": [
            {
                "branch": "soft_block_branch",
                "reason": "energy_soft_block",
                "consumed_fields": [
                    "action_readiness",
                    "soft_block_hint",
                    "metadata.utility_hints.priority_hint",
                ],
            }
        ],
        "usage_mode": "live_branch_applied",
        "live_gate_applied": True,
    }


def test_resolve_entry_service_energy_usage_records_confidence_hint_only_when_score_was_modulated():
    usage = resolve_entry_service_energy_usage(
        {
            "core_reason": "core_shadow_confirm_action",
            "consumer_block_reason": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_confidence_delta": 0.05,
        }
    )

    assert usage == {
        "component": "EntryService",
        "usage_source": "inferred",
        "consumed_fields": [
            "confidence_adjustment_hint",
        ],
        "branch_records": [
            {
                "branch": "confidence_adjustment",
                "reason": "",
                "consumed_fields": [
                    "confidence_adjustment_hint",
                ],
            }
        ],
        "usage_mode": "live_branch_applied",
        "live_gate_applied": True,
    }


def test_resolve_entry_service_energy_usage_records_forecast_gap_usage_when_live_gate_was_used():
    usage = resolve_entry_service_energy_usage(
        {
            "core_reason": "core_shadow_confirm_action",
            "consumer_block_reason": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_confidence_delta": 0.0,
            "consumer_energy_forecast_gap_live_gate_used": True,
        }
    )

    assert usage == {
        "component": "EntryService",
        "usage_source": "inferred",
        "consumed_fields": [
            "metadata.forecast_gap_usage_v1",
            "metadata.utility_hints.gap_dominant_hint",
            "metadata.utility_hints.forecast_branch_hint",
        ],
        "branch_records": [
            {
                "branch": "forecast_gap_live_gate",
                "reason": "",
                "consumed_fields": [
                    "metadata.forecast_gap_usage_v1",
                    "metadata.utility_hints.gap_dominant_hint",
                    "metadata.utility_hints.forecast_branch_hint",
                ],
            }
        ],
        "usage_mode": "live_branch_applied",
        "live_gate_applied": True,
    }


def test_resolve_entry_service_energy_usage_prefers_recorded_branch_trace_over_inference():
    usage = resolve_entry_service_energy_usage(
        {
            "consumer_energy_usage_trace_v1": {
                "component": "EntryService",
                "usage_source": "recorded",
                "usage_mode": "advisory_only",
                "consumed_fields": [
                    "metadata.utility_hints.priority_hint",
                ],
                "branch_records": [
                    {
                        "branch": "priority_rank_applied",
                        "reason": "medium",
                        "consumed_fields": [
                            "metadata.utility_hints.priority_hint",
                        ],
                    }
                ],
                "live_gate_applied": False,
            },
            "core_reason": "energy_soft_block",
            "consumer_block_reason": "energy_soft_block",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_confidence_delta": 0.05,
        }
    )

    assert usage == {
        "component": "EntryService",
        "usage_source": "recorded",
        "consumed_fields": [
            "metadata.utility_hints.priority_hint",
        ],
        "branch_records": [
            {
                "branch": "priority_rank_applied",
                "reason": "medium",
                "consumed_fields": [
                    "metadata.utility_hints.priority_hint",
                ],
            }
        ],
        "usage_mode": "advisory_only",
        "live_gate_applied": False,
    }


def test_resolve_energy_helper_input_reads_canonical_field_from_prs_metadata():
    payload = build_energy_helper_v2(_container())
    resolved = resolve_energy_helper_input(
        {
            "prs_log_contract_v2": {
                "canonical_energy_field": "energy_helper_v2",
            },
            "energy_helper_v2": payload,
        }
    )

    assert resolved == payload
