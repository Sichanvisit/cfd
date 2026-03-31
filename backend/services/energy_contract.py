from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping


ENERGY_INPUT_CONTRACT_V1 = {
    "contract_version": "energy_input_contract_v1",
    "scope": "effective_semantic_inputs_only",
    "official_input_container": "DecisionContext.metadata",
    "required_fields": [
        "evidence_vector_effective_v1",
        "belief_state_effective_v1",
        "barrier_state_effective_v1",
        "forecast_effective_policy_v1",
    ],
    "optional_fields": [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ],
    "allowed_observe_confirm_subfields": [
        "action",
        "side",
    ],
    "forbidden_observe_confirm_subfields": [
        "state",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "reason",
        "confidence",
    ],
    "forbidden_direct_inputs": [
        "raw_detector_score",
        "legacy_rule_branch",
        "position_snapshot_v2",
        "position_vector_v2",
        "position_zones_v2",
        "position_interpretation_v2",
        "position_energy_v2",
        "position_snapshot_effective_v1",
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "response_vector_effective_v1",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "state_vector_effective_v1",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ],
    "principles": [
        "energy helper reads only effective semantic payloads plus observe_confirm action or side context when available",
        "energy helper may read observe_confirm_v2.action or observe_confirm_v2.side only and must ignore other observe_confirm fields",
        "energy helper may not read raw detector scores, legacy rule branches, or raw PRS snapshots directly",
        "energy helper compresses already-resolved semantic payloads into action-friendly numbers only",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_SCOPE_FREEZE_V1 = {
    "contract_version": "energy_scope_freeze_v1",
    "scope": "helper_only_non_semantic",
    "semantic_layer_owner": False,
    "identity_field_mutation_allowed": False,
    "selected_side_semantics": "utility_only_not_semantic_side",
    "protected_identity_fields": [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ],
    "rules": [
        "energy is a helper that compresses effective semantic outputs into action-friendly numeric values only",
        "energy may not create, rewrite, or reinterpret semantic truth",
        "energy may not create, rewrite, or override archetype, side, invalidation, or management profile fields",
        "selected_side is a utility-facing compression field and must never be treated as semantic side ownership",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_OUTPUT_CONTRACT_V1 = {
    "contract_version": "energy_output_contract_v1",
    "canonical_output_field": "energy_helper_v2",
    "bundle_type": "EnergyHelperV2",
    "exact_top_level_shape_required": True,
    "optional_top_level_fields": [],
    "top_level_field_count": 10,
    "required_fields": [
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
    ],
    "field_semantics": {
        "selected_side": "utility-facing preferred side only; not semantic side and not identity ownership",
        "action_readiness": "bounded readiness compression for execution-facing consumers",
        "continuation_support": "support score for same-side continuation handling",
        "reversal_support": "support score for same-side reversal handling",
        "suppression_pressure": "suppression or friction pressure derived from barrier layer",
        "forecast_support": "forward support or confirm-wait modulation score",
        "net_utility": "signed support-minus-suppression utility score",
        "confidence_adjustment_hint": "non-binding hint for confidence modulation only",
        "soft_block_hint": "non-binding hint for wait or soft-block behavior only",
        "metadata": "replay-friendly source trace and contribution breakdown only",
    },
    "metadata_policy": {
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
    },
    "forbidden_outputs": [
        "side",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "semantic_truth_label",
        "setup_id",
    ],
    "forbidden_semantic_label_like_outputs": [
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
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_COMPOSITION_SEMANTICS_V1 = {
    "contract_version": "energy_composition_semantics_v1",
    "component_roles": {
        "evidence": "setup_strength_support",
        "belief": "persistence_and_continuation_bias",
        "barrier": "suppression_and_risk_pressure",
        "forecast": "forward_support_or_confirm_wait_modulation",
    },
    "component_output_bindings": {
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
    },
    "sign_convention": {
        "support_terms": "+",
        "suppression_terms": "-",
        "evidence": "+",
        "belief": "+",
        "barrier": "-",
        "forecast": "+",
    },
    "support_components": [
        "evidence",
        "belief",
        "forecast",
    ],
    "suppression_components": [
        "barrier",
    ],
    "output_direction_rules": {
        "continuation_support": "+",
        "reversal_support": "+",
        "forecast_support": "+",
        "suppression_pressure": "-",
        "action_readiness": "mixed_support_minus_suppression",
        "net_utility": "mixed_support_minus_suppression",
    },
    "identity_override_allowed": False,
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_ROLE_CONTRACT_V1 = {
    "contract_version": "energy_role_contract_v1",
    "scope": "utility_compression_helper_only",
    "official_role": "utility_compression_helper",
    "semantic_question_owner": "semantic_layer",
    "utility_question_owner": "energy_helper",
    "owns_situation_interpretation": False,
    "owns_execution_pressure_compression": True,
    "role_boundary": {
        "semantic_layer_question": "what situation is happening",
        "energy_question": "how much the current setup should be pushed or suppressed for action",
    },
    "responsibilities": [
        "compress effective semantic payloads into action-friendly helper values",
        "summarize support-versus-suppression pressure for execution-facing consumers",
        "expose replayable component contributions and source traces",
        "provide confidence and soft-block hints without owning identity",
    ],
    "non_responsibilities": [
        "semantic truth creation",
        "situation interpretation",
        "archetype selection",
        "side ownership",
        "invalidation rewrite",
        "management profile rewrite",
        "setup naming",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_IDENTITY_NON_OWNERSHIP_V1 = {
    "contract_version": "energy_identity_non_ownership_v1",
    "energy_is_identity_owner": False,
    "canonical_identity_owner": "observe_confirm_v2",
    "identity_creation_allowed": False,
    "identity_mutation_allowed": False,
    "protected_fields": [
        "archetype_id",
        "side",
        "invalidation_id",
        "management_profile_id",
    ],
    "allowed_context_reads": [
        "observe_confirm_v2.action",
        "observe_confirm_v2.side",
    ],
    "forbidden_identity_reads": [
        "observe_confirm_v2.archetype_id",
        "observe_confirm_v2.invalidation_id",
        "observe_confirm_v2.management_profile_id",
    ],
    "forbidden_operations": [
        "create_identity",
        "rewrite_identity",
        "override_identity",
        "infer_identity",
        "backfill_identity",
    ],
    "rules": [
        "energy helper may read observe_confirm action or side as context only",
        "energy helper may not create, rewrite, or override identity-bearing fields",
        "energy helper output remains advisory for utility and consumer hints only",
        "energy helper is not the identity owner and may not infer identity from utility compression",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_CONSUMER_USAGE_V1 = {
    "contract_version": "energy_consumer_usage_v1",
    "canonical_energy_field": "energy_helper_v2",
    "usage_mode": "consumer_hint_only",
    "component_usage": [
        {
            "component": "SetupDetector",
            "usage": "not required; optional reason annotation only",
            "allowed_energy_fields": [],
            "optional_annotation_fields": [
                "soft_block_hint.reason",
                "metadata.utility_hints.priority_hint",
            ],
            "direct_net_utility_use_allowed": False,
            "identity_decision_allowed": False,
        },
        {
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
        },
        {
            "component": "WaitEngine",
            "usage": "enter versus wait comparison hint only",
            "allowed_energy_fields": [
                "action_readiness",
                "soft_block_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
            "direct_net_utility_use_allowed": False,
            "identity_decision_allowed": False,
        },
        {
            "component": "Exit",
            "usage": "future management hint only; no identity decisions",
            "allowed_energy_fields": [
                "confidence_adjustment_hint",
                "soft_block_hint",
                "metadata.utility_hints.priority_hint",
            ],
            "direct_net_utility_use_allowed": False,
            "identity_decision_allowed": False,
        },
        {
            "component": "ReEntry",
            "usage": "future management hint only; no identity decisions",
            "allowed_energy_fields": [
                "confidence_adjustment_hint",
                "soft_block_hint",
                "metadata.utility_hints.wait_vs_enter_hint",
            ],
            "direct_net_utility_use_allowed": False,
            "identity_decision_allowed": False,
        },
    ],
    "forbidden_consumer_uses": [
        "identity rewrite",
        "setup remapping",
        "archetype inference",
        "invalidation override",
        "management_profile rewrite",
        "selected_side as canonical side",
        "semantic label inference",
    ],
    "principles": [
        "energy helper remains optional for setup naming and may annotate reasons only",
        "entry and wait consumers may read energy helper only as execution-facing hints",
        "exit and re-entry consumers may read energy helper only as advisory management hints",
        "no consumer may treat energy helper as an identity owner or semantic label source",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_LAYER_MODE_INTEGRATION_V1 = {
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


ENERGY_UTILITY_BRIDGE_V1 = {
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


ENERGY_MIGRATION_DUAL_WRITE_V1 = {
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


ENERGY_LOGGING_REPLAY_CONTRACT_V1 = {
    "contract_version": "energy_logging_replay_contract_v1",
    "scope": "replayable_energy_helper_audit_only",
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
    "principles": [
        "same effective inputs must produce the same helper output",
        "logs must explain why wait, soften, or confidence modulation happened",
        "final net_utility must stay explicit in replay logs even when support and suppression components are also recorded",
        "consumer logs must say which helper hints were actually consumed and whether they stayed advisory-only",
        "consumer-facing hints must stay inspectable without re-reading raw semantic builders",
    ],
    "runtime_embedding_field": "energy_logging_replay_contract_v1",
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_TEST_CONTRACT_V1 = {
    "contract_version": "energy_test_contract_v1",
    "scope": "energy_helper_required_regression_axes",
    "required_behavior_axes": [
        {
            "id": "deterministic_effective_input",
            "goal": "same semantic or effective input after layer mode produces the same helper output",
            "input_equivalence_domain": "effective_semantics_plus_observe_confirm_action_side_only",
            "primary_test_file": "tests/unit/test_energy_contract.py",
            "covered_by_tests": [
                "test_energy_helper_v2_is_deterministic_for_same_effective_inputs",
            ],
        },
        {
            "id": "barrier_increases_suppression",
            "goal": "higher barrier raises suppression pressure",
            "primary_test_file": "tests/unit/test_energy_contract.py",
            "covered_by_tests": [
                "test_energy_helper_v2_raises_suppression_when_barrier_grows",
            ],
        },
        {
            "id": "evidence_belief_raise_readiness",
            "goal": "higher evidence and belief raise action readiness",
            "primary_test_file": "tests/unit/test_energy_contract.py",
            "covered_by_tests": [
                "test_energy_helper_v2_raises_readiness_when_evidence_and_belief_grow",
            ],
        },
        {
            "id": "forecast_cannot_change_identity",
            "goal": "forecast may modulate forward support or confirm-wait bias but cannot create or mutate identity ownership",
            "primary_test_file": "tests/unit/test_energy_contract.py",
            "covered_by_tests": [
                "test_energy_helper_v2_forecast_changes_do_not_mutate_identity_or_selected_observe_side",
            ],
        },
        {
            "id": "energy_cannot_change_identity_fields",
            "goal": "energy cannot create or change archetype_id, side, invalidation_id, or management_profile_id",
            "primary_test_file": "tests/unit/test_energy_contract.py",
            "covered_by_tests": [
                "test_energy_helper_v2_uses_observe_confirm_side_without_owning_identity_fields",
                "test_energy_helper_v2_ignores_observe_confirm_identity_fields_for_output_identity",
            ],
        },
        {
            "id": "raw_and_effective_source_trace_preserved",
            "goal": "raw semantic source trace and effective helper source trace remain together for replay",
            "primary_test_file": "tests/unit/test_context_classifier.py",
            "covered_by_tests": [
                "test_context_classifier_preserves_raw_and_effective_source_trace_for_energy_replay",
            ],
        },
        {
            "id": "migration_dual_write_preserved",
            "goal": "legacy energy snapshot and canonical helper are both recorded during migration",
            "primary_test_file": "tests/unit/test_context_classifier.py",
            "covered_by_tests": [
                "test_energy_helper_v2_marks_legacy_snapshot_presence_during_migration_dual_write",
                "test_context_classifier_dual_writes_energy_helper_and_legacy_snapshot_for_migration_replay",
            ],
        },
    ],
    "principles": [
        "test contract freezes required replay-safe regression axes, not live calibration thresholds",
        "forecast may change utility compression values but never identity ownership",
        "migration coverage must preserve both canonical helper output and the legacy bridge until a later promotion step explicitly changes it",
    ],
    "documentation_path": "docs/energy_scope_contract.md",
}


ENERGY_FREEZE_HANDOFF_V1 = {
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


ENERGY_SCOPE_CONTRACT_V1 = {
    "contract_version": "energy_scope_v1",
    "scope": "energy_redefinition_helper_only",
    "runtime_only": True,
    "canonical_output_field": "energy_helper_v2",
    "compatibility_runtime_field": "energy_snapshot",
    "objective": "Redefine energy as a post-layer-mode helper that compresses effective semantic outputs into action-friendly utility values without owning meaning or identity.",
    "scope_freeze_v1": copy.deepcopy(ENERGY_SCOPE_FREEZE_V1),
    "role_contract_v1": copy.deepcopy(ENERGY_ROLE_CONTRACT_V1),
    "input_contract_v1": copy.deepcopy(ENERGY_INPUT_CONTRACT_V1),
    "output_contract_v1": copy.deepcopy(ENERGY_OUTPUT_CONTRACT_V1),
    "composition_semantics_v1": copy.deepcopy(ENERGY_COMPOSITION_SEMANTICS_V1),
    "identity_non_ownership_v1": copy.deepcopy(ENERGY_IDENTITY_NON_OWNERSHIP_V1),
    "consumer_usage_v1": copy.deepcopy(ENERGY_CONSUMER_USAGE_V1),
    "layer_mode_integration_v1": copy.deepcopy(ENERGY_LAYER_MODE_INTEGRATION_V1),
    "utility_bridge_v1": copy.deepcopy(ENERGY_UTILITY_BRIDGE_V1),
    "migration_dual_write_v1": copy.deepcopy(ENERGY_MIGRATION_DUAL_WRITE_V1),
    "logging_replay_contract_v1": copy.deepcopy(ENERGY_LOGGING_REPLAY_CONTRACT_V1),
    "test_contract_v1": copy.deepcopy(ENERGY_TEST_CONTRACT_V1),
    "freeze_handoff_v1": copy.deepcopy(ENERGY_FREEZE_HANDOFF_V1),
    "completed_definitions": [
        "13.0_scope_freeze",
        "13.1_role_contract_freeze",
        "13.2_input_contract_freeze",
        "13.3_output_contract_freeze",
        "13.4_composition_semantics_freeze",
        "13.5_identity_non_ownership_freeze",
        "13.7_layer_mode_integration_freeze",
        "13.9_migration_dual_write_freeze",
        "13.10_logging_replay_freeze",
        "13.11_test_contract_freeze",
        "13.12_freeze_handoff",
    ],
    "deferred_definitions": [
        "13.6_live_consumer_gate_promotion",
        "13.8_direct_utility_router_integration",
    ],
    "runtime_embedding_field": "energy_scope_contract_v1",
    "documentation_path": "docs/energy_scope_contract.md",
}


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _container_mapping(container: Any) -> dict[str, Any]:
    if isinstance(container, Mapping):
        metadata = container.get("metadata")
        if isinstance(metadata, Mapping) and (
            "energy_helper_v2" in metadata or "prs_log_contract_v2" in metadata or "observe_confirm_v2" in metadata
        ):
            return {str(k): v for k, v in metadata.items()}
        return {str(k): v for k, v in container.items()}
    metadata = getattr(container, "metadata", None)
    if isinstance(metadata, Mapping):
        return {str(k): v for k, v in metadata.items()}
    return {}


def resolve_energy_migration_bridge_state(container: Any) -> dict[str, Any]:
    metadata = _container_mapping(container)
    helper_payload = _coerce_mapping(metadata.get(ENERGY_MIGRATION_DUAL_WRITE_V1["canonical_output_field"]))
    legacy_snapshot = _coerce_mapping(metadata.get(ENERGY_MIGRATION_DUAL_WRITE_V1["compatibility_runtime_field"]))
    helper_present = bool(helper_payload)
    legacy_present = bool(legacy_snapshot)
    used_compatibility_bridge = bool((not helper_present) and legacy_present)
    return {
        "contract_version": str(ENERGY_MIGRATION_DUAL_WRITE_V1["contract_version"]),
        "canonical_output_field": str(ENERGY_MIGRATION_DUAL_WRITE_V1["canonical_output_field"]),
        "compatibility_runtime_field": str(ENERGY_MIGRATION_DUAL_WRITE_V1["compatibility_runtime_field"]),
        "canonical_payload_present": helper_present,
        "compatibility_snapshot_present": legacy_present,
        "used_compatibility_bridge": used_compatibility_bridge,
        "compatibility_bridge_rebuild_active": used_compatibility_bridge,
        "compatibility_role": str(ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_bridge_role"]),
        "fallback_allowed_only_when_canonical_missing": bool(
            ENERGY_MIGRATION_DUAL_WRITE_V1["fallback_allowed_only_when_canonical_missing"]
        ),
        "legacy_identity_input_allowed": bool(ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_identity_input_allowed"]),
        "legacy_live_gate_allowed": bool(ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_live_gate_allowed"]),
        "legacy_rebuild_scope": str(ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_rebuild_scope"]),
        "live_gate_behavior": str(ENERGY_MIGRATION_DUAL_WRITE_V1["live_gate_behavior"]),
        "legacy_snapshot": legacy_snapshot,
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _round(value: float) -> float:
    return round(float(value), 6)


def _normalize_consumed_fields(value: Any) -> list[str]:
    items = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
    normalized_fields: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if normalized and normalized not in normalized_fields:
            normalized_fields.append(normalized)
    return normalized_fields


def _normalize_usage_branch_records(value: Any) -> list[dict[str, Any]]:
    records = value if isinstance(value, (list, tuple)) else []
    normalized_records: list[dict[str, Any]] = []
    for item in records:
        mapping = _coerce_mapping(item)
        branch = str(mapping.get("branch", "") or "").strip()
        reason = str(mapping.get("reason", "") or "").strip()
        consumed_fields = _normalize_consumed_fields(mapping.get("consumed_fields", []))
        details = _coerce_mapping(mapping.get("details", {}))
        if not (branch or reason or consumed_fields or details):
            continue
        record = {
            "branch": branch,
            "reason": reason,
            "consumed_fields": consumed_fields,
        }
        if details:
            record["details"] = details
        normalized_records.append(record)
    return normalized_records


def create_energy_usage_recorder(*, component: str = "EntryService") -> dict[str, Any]:
    return {
        "contract_version": "consumer_energy_usage_trace_v1",
        "component": str(component or "EntryService"),
        "usage_source": "recorded",
        "usage_mode": "not_consumed",
        "consumed_fields": [],
        "branch_records": [],
        "live_gate_applied": False,
    }


def record_energy_usage(
    recorder: Mapping[str, Any] | None,
    *,
    branch: str,
    consumed_fields: list[str] | tuple[str, ...],
    reason: str = "",
    details: Mapping[str, Any] | None = None,
    active: bool = True,
) -> dict[str, Any]:
    state = dict(recorder or create_energy_usage_recorder())
    if not bool(active):
        return state
    normalized_branch = str(branch or "").strip()
    normalized_fields = _normalize_consumed_fields(consumed_fields)
    normalized_reason = str(reason or "").strip()
    normalized_details = _coerce_mapping(details or {})
    if not (normalized_branch or normalized_reason or normalized_fields or normalized_details):
        return state

    aggregate_fields = _normalize_consumed_fields(state.get("consumed_fields", []))
    for field_name in normalized_fields:
        if field_name not in aggregate_fields:
            aggregate_fields.append(field_name)
    branch_records = _normalize_usage_branch_records(state.get("branch_records", []))
    record = {
        "branch": normalized_branch,
        "reason": normalized_reason,
        "consumed_fields": normalized_fields,
    }
    if normalized_details:
        record["details"] = normalized_details
    branch_records.append(record)
    state["consumed_fields"] = aggregate_fields
    state["branch_records"] = branch_records
    return state


def finalize_energy_usage_recorder(
    recorder: Mapping[str, Any] | None,
    *,
    usage_mode: str = "",
    live_gate_applied: bool = False,
) -> dict[str, Any]:
    state = dict(recorder or {})
    consumed_fields = _normalize_consumed_fields(state.get("consumed_fields", []))
    branch_records = _normalize_usage_branch_records(state.get("branch_records", []))
    live_gate = bool(live_gate_applied)
    normalized_usage_mode = str(usage_mode or "").strip()
    if not normalized_usage_mode:
        if consumed_fields:
            normalized_usage_mode = "live_branch_applied" if live_gate else "advisory_only"
        else:
            normalized_usage_mode = "not_consumed"
    return {
        "contract_version": "consumer_energy_usage_trace_v1",
        "component": str(state.get("component", "EntryService") or "EntryService"),
        "usage_source": str(state.get("usage_source", "recorded") or "recorded"),
        "usage_mode": normalized_usage_mode,
        "consumed_fields": consumed_fields,
        "branch_records": branch_records,
        "live_gate_applied": live_gate,
    }


def _resolve_observe_side(observe_confirm: Mapping[str, Any]) -> str:
    side = str(observe_confirm.get("side", "") or "").strip().upper()
    if side in {"BUY", "SELL"}:
        return side
    action = str(observe_confirm.get("action", "") or "").strip().upper()
    if action in {"BUY", "SELL"}:
        return action
    return ""


def _sanitize_observe_confirm_energy_input(observe_confirm: Mapping[str, Any]) -> dict[str, str]:
    return {
        "action": str(observe_confirm.get("action", "") or "").strip().upper(),
        "side": str(observe_confirm.get("side", "") or "").strip().upper(),
    }


def _forecast_sections(forecast_effective_policy_v1: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        _coerce_mapping(forecast_effective_policy_v1.get("transition_forecast_v1", {})),
        _coerce_mapping(forecast_effective_policy_v1.get("trade_management_forecast_v1", {})),
        _coerce_mapping(forecast_effective_policy_v1.get("forecast_gap_metrics_v1", {})),
    )


def _side_payload(
    *,
    side: str,
    evidence: Mapping[str, Any],
    belief: Mapping[str, Any],
    barrier: Mapping[str, Any],
    transition_forecast: Mapping[str, Any],
    trade_management_forecast: Mapping[str, Any],
) -> dict[str, float]:
    side_u = str(side or "").upper()
    prefix = "buy" if side_u == "BUY" else "sell"
    total_evidence = _clamp(_to_float(evidence.get(f"{prefix}_total_evidence", 0.0)))
    continuation_evidence = _clamp(_to_float(evidence.get(f"{prefix}_continuation_evidence", 0.0)))
    reversal_evidence = _clamp(_to_float(evidence.get(f"{prefix}_reversal_evidence", 0.0)))
    belief_strength = _clamp(
        (_to_float(belief.get(f"{prefix}_belief", 0.0)) * 0.65)
        + (_to_float(belief.get(f"{prefix}_persistence", 0.0)) * 0.35)
    )
    barrier_pressure = _clamp(
        max(
            _to_float(barrier.get(f"{prefix}_barrier", 0.0)),
            _to_float(barrier.get("conflict_barrier", 0.0)),
            _to_float(barrier.get("middle_chop_barrier", 0.0)),
            _to_float(barrier.get("direction_policy_barrier", 0.0)),
            _to_float(barrier.get("liquidity_barrier", 0.0)),
        )
    )
    confirm_key = "p_buy_confirm" if side_u == "BUY" else "p_sell_confirm"
    confirm_support = _clamp(_to_float(transition_forecast.get(confirm_key, 0.0)))
    forecast_positive = _clamp(
        (confirm_support * 0.50)
        + (_to_float(trade_management_forecast.get("p_continue_favor", 0.0)) * 0.20)
        + (_to_float(trade_management_forecast.get("p_reach_tp1", 0.0)) * 0.15)
        + (_to_float(trade_management_forecast.get("p_recover_after_pullback", 0.0)) * 0.15)
    )
    forecast_negative = _clamp(
        (_to_float(transition_forecast.get("p_false_break", 0.0)) * 0.40)
        + (_to_float(trade_management_forecast.get("p_fail_now", 0.0)) * 0.35)
        + (_to_float(trade_management_forecast.get("p_better_reentry_if_cut", 0.0)) * 0.25)
    )
    forecast_support = _clamp(forecast_positive - (forecast_negative * 0.50))
    continuation_support = _clamp(
        (continuation_evidence * 0.55)
        + (_to_float(belief.get(f"{prefix}_persistence", 0.0)) * 0.25)
        + (_to_float(trade_management_forecast.get("p_continue_favor", 0.0)) * 0.20)
    )
    reversal_support = _clamp(
        (reversal_evidence * 0.55)
        + (confirm_support * 0.20)
        + (_to_float(transition_forecast.get("p_reversal_success", 0.0)) * 0.15)
        + ((1.0 - _to_float(transition_forecast.get("p_false_break", 0.0))) * 0.10)
    )
    support_total = _clamp(
        (total_evidence * 0.35)
        + (belief_strength * 0.20)
        + (max(continuation_support, reversal_support) * 0.20)
        + (forecast_support * 0.25)
    )
    action_readiness = _clamp(support_total - (barrier_pressure * 0.55))
    net_utility = max(-1.0, min(1.0, support_total - barrier_pressure))
    return {
        "total_evidence": _round(total_evidence),
        "belief_strength": _round(belief_strength),
        "continuation_support": _round(continuation_support),
        "reversal_support": _round(reversal_support),
        "suppression_pressure": _round(barrier_pressure),
        "forecast_support": _round(forecast_support),
        "support_total": _round(support_total),
        "action_readiness": _round(action_readiness),
        "net_utility": _round(net_utility),
    }


def build_energy_helper_v2(
    container: Any,
    *,
    legacy_energy_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    data = _container_mapping(container)
    evidence = _coerce_mapping(data.get("evidence_vector_effective_v1", {}))
    belief = _coerce_mapping(data.get("belief_state_effective_v1", {}))
    barrier = _coerce_mapping(data.get("barrier_state_effective_v1", {}))
    forecast_effective_policy_v1 = _coerce_mapping(data.get("forecast_effective_policy_v1", {}))
    observe_confirm = _sanitize_observe_confirm_energy_input(_coerce_mapping(data.get("observe_confirm_v2", {})))
    transition_forecast, trade_management_forecast, forecast_gap_metrics = _forecast_sections(
        forecast_effective_policy_v1
    )
    side_from_observe = _resolve_observe_side(observe_confirm)
    buy_payload = _side_payload(
        side="BUY",
        evidence=evidence,
        belief=belief,
        barrier=barrier,
        transition_forecast=transition_forecast,
        trade_management_forecast=trade_management_forecast,
    )
    sell_payload = _side_payload(
        side="SELL",
        evidence=evidence,
        belief=belief,
        barrier=barrier,
        transition_forecast=transition_forecast,
        trade_management_forecast=trade_management_forecast,
    )

    if side_from_observe in {"BUY", "SELL"}:
        selected_side = side_from_observe
        selected_side_source = "observe_confirm_v2"
    elif buy_payload["net_utility"] > sell_payload["net_utility"]:
        selected_side = "BUY"
        selected_side_source = "net_utility_delta"
    elif sell_payload["net_utility"] > buy_payload["net_utility"]:
        selected_side = "SELL"
        selected_side_source = "net_utility_delta"
    else:
        selected_side = ""
        selected_side_source = "balanced"

    selected_payload = buy_payload if selected_side == "BUY" else sell_payload if selected_side == "SELL" else {
        "continuation_support": 0.0,
        "reversal_support": 0.0,
        "suppression_pressure": 0.0,
        "forecast_support": 0.0,
        "action_readiness": 0.0,
        "net_utility": 0.0,
        "support_total": 0.0,
    }

    transition_side_separation = _to_float(forecast_gap_metrics.get("transition_side_separation", 0.0))
    confirm_fake_gap = _to_float(forecast_gap_metrics.get("transition_confirm_fake_gap", 0.0))
    wait_confirm_gap = _to_float(forecast_gap_metrics.get("wait_confirm_gap", 0.0))
    continue_fail_gap = _to_float(forecast_gap_metrics.get("management_continue_fail_gap", 0.0))
    recover_reentry_gap = _to_float(forecast_gap_metrics.get("management_recover_reentry_gap", 0.0))
    hold_exit_gap = _to_float(forecast_gap_metrics.get("hold_exit_gap", 0.0))
    same_side_flip_gap = _to_float(forecast_gap_metrics.get("same_side_flip_gap", 0.0))
    belief_barrier_tension_gap = _to_float(forecast_gap_metrics.get("belief_barrier_tension_gap", 0.0))
    forecast_gap_metadata = _coerce_mapping(forecast_gap_metrics.get("metadata", {}))
    execution_gap_support = _coerce_mapping(forecast_gap_metadata.get("execution_gap_support_v1", {}))
    confirm_release_active = bool(selected_side and confirm_fake_gap >= 0.10)
    continue_support_active = bool(selected_side and continue_fail_gap >= 0.04)
    continue_drag_active = bool(selected_side and continue_fail_gap <= -0.04)
    recover_reentry_support_active = bool(recover_reentry_gap >= 0.08)
    hold_extension_active = bool(selected_side and hold_exit_gap >= 0.08)
    same_side_flip_risk_active = bool(selected_side and same_side_flip_gap <= -0.08)
    gap_release_active = bool(
        selected_side
        and wait_confirm_gap >= 0.10
        and belief_barrier_tension_gap >= -0.02
        and (confirm_release_active or continue_support_active or transition_side_separation >= 0.08)
    )
    gap_drag_active = bool(
        selected_side
        and (
            wait_confirm_gap <= -0.08
            or belief_barrier_tension_gap <= -0.10
            or continue_drag_active
            or same_side_flip_risk_active
        )
    )
    forecast_gap_usage_active = bool(
        abs(confirm_fake_gap) > 1e-9
        or abs(wait_confirm_gap) > 1e-9
        or abs(continue_fail_gap) > 1e-9
        or abs(recover_reentry_gap) > 1e-9
        or abs(hold_exit_gap) > 1e-9
        or abs(same_side_flip_gap) > 1e-9
        or abs(belief_barrier_tension_gap) > 1e-9
        or bool(execution_gap_support)
    )
    if same_side_flip_risk_active:
        forecast_branch_hint = "same_side_flip_risk"
    elif gap_drag_active and continue_drag_active:
        forecast_branch_hint = "continue_fail_drag"
    elif confirm_release_active and continue_support_active:
        forecast_branch_hint = "confirm_continue_alignment"
    elif hold_extension_active:
        forecast_branch_hint = "hold_extension_bias"
    elif recover_reentry_support_active:
        forecast_branch_hint = "reentry_quality_support"
    elif gap_release_active:
        forecast_branch_hint = "gap_release_support"
    else:
        forecast_branch_hint = "balanced_branch_support"
    if (
        selected_side
        and selected_payload["action_readiness"] >= 0.65
        and selected_payload["net_utility"] >= 0.12
        and selected_payload["forecast_support"] >= 0.20
        and selected_payload["suppression_pressure"] < 0.45
        and transition_side_separation >= 0.08
    ):
        confidence_adjustment_hint = {
            "direction": "increase",
            "delta_band": "small_up",
            "reason": "confirm_continue_alignment"
            if confirm_release_active and continue_support_active
            else "support_exceeds_suppression",
        }
    elif gap_release_active:
        confidence_adjustment_hint = {
            "direction": "increase",
            "delta_band": "small_up",
            "reason": forecast_branch_hint,
        }
    elif (
        selected_payload["suppression_pressure"] >= 0.65
        or selected_payload["net_utility"] <= -0.05
        or (
            selected_side
            and selected_payload["forecast_support"] <= 0.10
            and selected_payload["action_readiness"] <= 0.35
        )
        or gap_drag_active
    ):
        confidence_adjustment_hint = {
            "direction": "decrease",
            "delta_band": "small_down",
            "reason": "gap_drag" if gap_drag_active else "suppression_or_forecast_drag",
        }
    else:
        confidence_adjustment_hint = {
            "direction": "neutral",
            "delta_band": "hold",
            "reason": "balanced_helper_state",
        }

    soft_block_reason = ""
    soft_block_strength = 0.0
    if selected_payload["suppression_pressure"] >= 0.85:
        soft_block_reason = "barrier_hard_block"
        soft_block_strength = selected_payload["suppression_pressure"]
    elif selected_payload["suppression_pressure"] >= 0.65:
        soft_block_reason = "barrier_soft_block"
        soft_block_strength = selected_payload["suppression_pressure"]
    elif gap_drag_active and selected_payload["action_readiness"] < 0.55:
        soft_block_reason = "forecast_gap_wait_bias"
        soft_block_strength = max(0.25, abs(min(wait_confirm_gap, belief_barrier_tension_gap)))
    elif str(observe_confirm.get("action", "") or "").upper() in {"WAIT", "NONE"}:
        soft_block_reason = "observe_confirm_wait"
        soft_block_strength = max(selected_payload["suppression_pressure"], 0.35)
    elif selected_side and selected_payload["forecast_support"] <= 0.10 and selected_payload["action_readiness"] <= 0.35:
        soft_block_reason = "forecast_wait_bias"
        soft_block_strength = max(0.25, 1.0 - selected_payload["forecast_support"])
    soft_block_hint = {
        "active": bool(soft_block_reason),
        "reason": soft_block_reason,
        "strength": _round(soft_block_strength),
    }

    priority_hint = (
        "high"
        if (
            selected_payload["action_readiness"] >= 0.75 and selected_payload["net_utility"] >= 0.20
        ) or (
            selected_side
            and selected_payload["action_readiness"] >= 0.55
            and confirm_release_active
            and continue_support_active
        )
        else "medium"
        if selected_payload["action_readiness"] >= 0.45 and selected_side
        else "low"
    )
    wait_vs_enter_hint = (
        "prefer_enter"
        if (
            selected_side
            and selected_payload["action_readiness"] >= 0.60
            and not soft_block_hint["active"]
            and wait_confirm_gap >= -0.02
            and belief_barrier_tension_gap >= -0.05
            and not same_side_flip_risk_active
        )
        else "prefer_wait"
    )
    forecast_gap_usage_v1 = {
        "active": forecast_gap_usage_active,
        "transition_confirm_fake_gap": _round(confirm_fake_gap),
        "wait_confirm_gap": _round(wait_confirm_gap),
        "management_continue_fail_gap": _round(continue_fail_gap),
        "management_recover_reentry_gap": _round(recover_reentry_gap),
        "hold_exit_gap": _round(hold_exit_gap),
        "same_side_flip_gap": _round(same_side_flip_gap),
        "belief_barrier_tension_gap": _round(belief_barrier_tension_gap),
        "transition_side_separation": _round(transition_side_separation),
        "dominant_execution_gap": str(execution_gap_support.get("dominant_execution_gap", "") or ""),
        "branch_hint": forecast_branch_hint,
        "confirm_release_active": confirm_release_active,
        "continue_support_active": continue_support_active,
        "continue_drag_active": continue_drag_active,
        "recover_reentry_support_active": recover_reentry_support_active,
        "hold_extension_active": hold_extension_active,
        "same_side_flip_risk_active": same_side_flip_risk_active,
        "gap_release_active": gap_release_active,
        "gap_drag_active": gap_drag_active,
        "confidence_assist_active": bool(gap_release_active or gap_drag_active),
        "soft_block_assist_active": bool(
            soft_block_reason in {"forecast_gap_wait_bias", "forecast_wait_bias"} or gap_drag_active
        ),
        "priority_assist_active": bool(
            priority_hint == "high" and (confirm_release_active or continue_support_active or hold_extension_active)
        ),
        "wait_assist_active": bool(
            wait_vs_enter_hint == "prefer_wait" and (gap_drag_active or same_side_flip_risk_active)
        ),
        "usage_mode": "active_branch_assist" if forecast_gap_usage_active else "gap_trace_only",
    }

    missing_input_fields = [
        field
        for field in ENERGY_INPUT_CONTRACT_V1["required_fields"]
        if not _coerce_mapping(data.get(field, {}))
    ]
    ignored_direct_inputs = [
        field for field in ENERGY_INPUT_CONTRACT_V1["forbidden_direct_inputs"] if field in data
    ]
    legacy_snapshot = _coerce_mapping(legacy_energy_snapshot or {})
    legacy_bridge = {
        "runtime_field": ENERGY_MIGRATION_DUAL_WRITE_V1["compatibility_runtime_field"],
        "present": bool(legacy_snapshot),
        "buy_force": _round(_to_float(legacy_snapshot.get("buy_force", 0.0))),
        "sell_force": _round(_to_float(legacy_snapshot.get("sell_force", 0.0))),
        "net_force": _round(_to_float(legacy_snapshot.get("net_force", 0.0))),
    }

    output_payload = {
        "selected_side": selected_side,
        "action_readiness": _round(selected_payload["action_readiness"]),
        "continuation_support": _round(selected_payload["continuation_support"]),
        "reversal_support": _round(selected_payload["reversal_support"]),
        "suppression_pressure": _round(selected_payload["suppression_pressure"]),
        "forecast_support": _round(selected_payload["forecast_support"]),
        "net_utility": _round(selected_payload["net_utility"]),
        "confidence_adjustment_hint": confidence_adjustment_hint,
        "soft_block_hint": soft_block_hint,
        "metadata": {
            "energy_contract": "energy_helper_v2",
            "scope_contract_version": ENERGY_SCOPE_CONTRACT_V1["contract_version"],
            "scope_freeze_contract_version": ENERGY_SCOPE_FREEZE_V1["contract_version"],
            "input_contract_version": ENERGY_INPUT_CONTRACT_V1["contract_version"],
            "output_contract_version": ENERGY_OUTPUT_CONTRACT_V1["contract_version"],
            "selected_side_source": selected_side_source,
            "input_source_fields": {
                "evidence_vector_effective_v1": bool(evidence),
                "belief_state_effective_v1": bool(belief),
                "barrier_state_effective_v1": bool(barrier),
                "forecast_effective_policy_v1": bool(forecast_effective_policy_v1),
                "observe_confirm_v2.action": bool(str(observe_confirm.get("action", "") or "").strip()),
                "observe_confirm_v2.side": bool(str(observe_confirm.get("side", "") or "").strip()),
            },
            "missing_input_fields": missing_input_fields,
            "input_freeze": {
                "applied": True,
                "required_fields": list(ENERGY_INPUT_CONTRACT_V1["required_fields"]),
                "optional_fields": list(ENERGY_INPUT_CONTRACT_V1["optional_fields"]),
                "allowed_observe_confirm_subfields": list(ENERGY_INPUT_CONTRACT_V1["allowed_observe_confirm_subfields"]),
                "forbidden_observe_confirm_subfields": list(
                    ENERGY_INPUT_CONTRACT_V1["forbidden_observe_confirm_subfields"]
                ),
                "forbidden_direct_inputs": list(ENERGY_INPUT_CONTRACT_V1["forbidden_direct_inputs"]),
                "ignored_available_direct_inputs": ignored_direct_inputs,
                "reads_only_contract_inputs": True,
            },
            "layer_mode_integration_freeze": {
                "applied": True,
                "contract_version": ENERGY_LAYER_MODE_INTEGRATION_V1["contract_version"],
                "bridge_position": ENERGY_LAYER_MODE_INTEGRATION_V1["bridge_position"],
                "helper_identity": ENERGY_LAYER_MODE_INTEGRATION_V1["helper_identity"],
                "effective_world_required": ENERGY_LAYER_MODE_INTEGRATION_V1["effective_world_required"],
                "reads_effective_semantics": ENERGY_LAYER_MODE_INTEGRATION_V1["reads_effective_semantics"],
                "reads_raw_semantics": ENERGY_LAYER_MODE_INTEGRATION_V1["reads_raw_semantics"],
                "raw_semantic_output_allowed": ENERGY_LAYER_MODE_INTEGRATION_V1["raw_semantic_output_allowed"],
                "pre_layer_mode_semantic_attachment_allowed": ENERGY_LAYER_MODE_INTEGRATION_V1[
                    "pre_layer_mode_semantic_attachment_allowed"
                ],
                "required_effective_fields": list(ENERGY_LAYER_MODE_INTEGRATION_V1["required_effective_fields"]),
                "effective_fields_present": [
                    field
                    for field in ENERGY_LAYER_MODE_INTEGRATION_V1["required_effective_fields"]
                    if _coerce_mapping(data.get(field, {}))
                ],
                "official_build_order": list(ENERGY_LAYER_MODE_INTEGRATION_V1["official_build_order"]),
                "post_layer_mode_helper": True,
            },
            "utility_bridge_freeze": {
                "applied": True,
                "contract_version": ENERGY_UTILITY_BRIDGE_V1["contract_version"],
                "bridge_strategy": ENERGY_UTILITY_BRIDGE_V1["bridge_strategy"],
                "direct_net_utility_use_allowed": ENERGY_UTILITY_BRIDGE_V1["direct_net_utility_use_allowed"],
                "net_utility_role": ENERGY_UTILITY_BRIDGE_V1["net_utility_role"],
                "canonical_bridge_hints": list(ENERGY_UTILITY_BRIDGE_V1["canonical_bridge_hints"]),
                "preferred_consumer_hints": list(ENERGY_UTILITY_BRIDGE_V1["preferred_consumer_hints"]),
                "forbidden_direct_use": list(ENERGY_UTILITY_BRIDGE_V1["forbidden_direct_use"]),
                "component_bridge_policy": {
                    key: list(value)
                    for key, value in ENERGY_UTILITY_BRIDGE_V1["component_bridge_policy"].items()
                },
                "hint_payload": {
                    "confidence_adjustment_hint": dict(confidence_adjustment_hint),
                    "soft_block_hint": dict(soft_block_hint),
                    "priority_hint": priority_hint,
                    "wait_vs_enter_hint": wait_vs_enter_hint,
                },
                "net_utility_available_for_audit_only": True,
            },
            "migration_dual_write_freeze": {
                "applied": True,
                "contract_version": ENERGY_MIGRATION_DUAL_WRITE_V1["contract_version"],
                "canonical_output_field": ENERGY_MIGRATION_DUAL_WRITE_V1["canonical_output_field"],
                "compatibility_runtime_field": ENERGY_MIGRATION_DUAL_WRITE_V1["compatibility_runtime_field"],
                "runtime_contract_field": ENERGY_MIGRATION_DUAL_WRITE_V1["runtime_contract_field"],
                "official_guard_helper": ENERGY_MIGRATION_DUAL_WRITE_V1["official_guard_helper"],
                "dual_write_required": ENERGY_MIGRATION_DUAL_WRITE_V1["dual_write_required"],
                "write_targets": list(ENERGY_MIGRATION_DUAL_WRITE_V1["write_targets"]),
                "legacy_bridge_role": ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_bridge_role"],
                "canonical_consumer_read_field": ENERGY_MIGRATION_DUAL_WRITE_V1["canonical_consumer_read_field"],
                "direct_legacy_consumer_use_allowed": ENERGY_MIGRATION_DUAL_WRITE_V1[
                    "direct_legacy_consumer_use_allowed"
                ],
                "fallback_allowed_only_when_canonical_missing": ENERGY_MIGRATION_DUAL_WRITE_V1[
                    "fallback_allowed_only_when_canonical_missing"
                ],
                "legacy_identity_input_allowed": ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_identity_input_allowed"],
                "legacy_live_gate_allowed": ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_live_gate_allowed"],
                "legacy_rebuild_scope": ENERGY_MIGRATION_DUAL_WRITE_V1["legacy_rebuild_scope"],
                "live_gate_promotion_allowed": ENERGY_MIGRATION_DUAL_WRITE_V1["live_gate_promotion_allowed"],
                "live_gate_behavior": ENERGY_MIGRATION_DUAL_WRITE_V1["live_gate_behavior"],
                "replay_preservation_required": ENERGY_MIGRATION_DUAL_WRITE_V1["replay_preservation_required"],
                "canonical_payload_emitted": True,
                "legacy_snapshot_present": bool(legacy_snapshot),
            },
            "observe_confirm_context": {
                "action": str(observe_confirm.get("action", "") or ""),
                "side": str(observe_confirm.get("side", "") or ""),
                "allowed_subfields_only": True,
            },
            "scope_freeze": {
                "applied": True,
                "helper_only": True,
                "semantic_layer_owner": ENERGY_SCOPE_FREEZE_V1["semantic_layer_owner"],
                "identity_field_mutation_allowed": ENERGY_SCOPE_FREEZE_V1["identity_field_mutation_allowed"],
                "selected_side_semantics": ENERGY_SCOPE_FREEZE_V1["selected_side_semantics"],
                "selected_side_is_identity_side": False,
                "protected_identity_fields": list(ENERGY_SCOPE_FREEZE_V1["protected_identity_fields"]),
                "forbidden_output_fields_absent": [],
            },
            "role_freeze": {
                "applied": True,
                "official_role": ENERGY_ROLE_CONTRACT_V1["official_role"],
                "semantic_question_owner": ENERGY_ROLE_CONTRACT_V1["semantic_question_owner"],
                "utility_question_owner": ENERGY_ROLE_CONTRACT_V1["utility_question_owner"],
                "owns_situation_interpretation": ENERGY_ROLE_CONTRACT_V1["owns_situation_interpretation"],
                "owns_execution_pressure_compression": ENERGY_ROLE_CONTRACT_V1[
                    "owns_execution_pressure_compression"
                ],
                "role_boundary": dict(ENERGY_ROLE_CONTRACT_V1["role_boundary"]),
            },
            "output_freeze": {
                "applied": True,
                "canonical_output_field": ENERGY_OUTPUT_CONTRACT_V1["canonical_output_field"],
                "exact_top_level_shape_required": ENERGY_OUTPUT_CONTRACT_V1["exact_top_level_shape_required"],
                "optional_top_level_fields": list(ENERGY_OUTPUT_CONTRACT_V1["optional_top_level_fields"]),
                "canonical_top_level_fields": list(ENERGY_OUTPUT_CONTRACT_V1["required_fields"]),
                "metadata_role": ENERGY_OUTPUT_CONTRACT_V1["metadata_policy"]["role"],
                "semantic_label_emission_allowed": ENERGY_OUTPUT_CONTRACT_V1["metadata_policy"][
                    "semantic_label_emission_allowed"
                ],
                "transition_side_separation": _round(transition_side_separation),
                "wait_confirm_gap": _round(wait_confirm_gap),
                "hold_exit_gap": _round(hold_exit_gap),
                "same_side_flip_gap": _round(same_side_flip_gap),
                "belief_barrier_tension_gap": _round(belief_barrier_tension_gap),
                "forbidden_top_level_fields_absent": [],
                "forbidden_semantic_label_like_fields_absent": [],
            },
            "composition_freeze": {
                "applied": True,
                "contract_version": ENERGY_COMPOSITION_SEMANTICS_V1["contract_version"],
                "component_roles": dict(ENERGY_COMPOSITION_SEMANTICS_V1["component_roles"]),
                "component_output_bindings": {
                    key: list(value)
                    for key, value in ENERGY_COMPOSITION_SEMANTICS_V1["component_output_bindings"].items()
                },
                "sign_convention": dict(ENERGY_COMPOSITION_SEMANTICS_V1["sign_convention"]),
                "support_components": list(ENERGY_COMPOSITION_SEMANTICS_V1["support_components"]),
                "suppression_components": list(ENERGY_COMPOSITION_SEMANTICS_V1["suppression_components"]),
                "output_direction_rules": dict(ENERGY_COMPOSITION_SEMANTICS_V1["output_direction_rules"]),
                "selected_side_component_summary": {
                    "evidence": _round(selected_payload.get("total_evidence", 0.0)),
                    "belief": _round(selected_payload.get("belief_strength", 0.0)),
                    "barrier": _round(selected_payload.get("suppression_pressure", 0.0)),
                    "forecast": _round(selected_payload.get("forecast_support", 0.0)),
                },
            },
            "identity_non_ownership_freeze": {
                "applied": True,
                "contract_version": ENERGY_IDENTITY_NON_OWNERSHIP_V1["contract_version"],
                "energy_is_identity_owner": ENERGY_IDENTITY_NON_OWNERSHIP_V1["energy_is_identity_owner"],
                "canonical_identity_owner": ENERGY_IDENTITY_NON_OWNERSHIP_V1["canonical_identity_owner"],
                "identity_creation_allowed": ENERGY_IDENTITY_NON_OWNERSHIP_V1["identity_creation_allowed"],
                "identity_mutation_allowed": ENERGY_IDENTITY_NON_OWNERSHIP_V1["identity_mutation_allowed"],
                "protected_fields": list(ENERGY_IDENTITY_NON_OWNERSHIP_V1["protected_fields"]),
                "allowed_context_reads": list(ENERGY_IDENTITY_NON_OWNERSHIP_V1["allowed_context_reads"]),
                "forbidden_identity_reads": list(ENERGY_IDENTITY_NON_OWNERSHIP_V1["forbidden_identity_reads"]),
                "forbidden_operations": list(ENERGY_IDENTITY_NON_OWNERSHIP_V1["forbidden_operations"]),
                "selected_side_is_identity_side": False,
                "identity_fields_absent_from_output": [],
            },
            "component_contributions": {
                "BUY": buy_payload,
                "SELL": sell_payload,
            },
            "selected_side_breakdown": {
                "selected_side": selected_side,
                "support_total": _round(selected_payload.get("support_total", 0.0)),
                "net_utility": _round(selected_payload.get("net_utility", 0.0)),
                "forecast_support": _round(selected_payload.get("forecast_support", 0.0)),
                "transition_side_separation": _round(transition_side_separation),
            },
            "support_vs_suppression_breakdown": {
                "support_total": _round(selected_payload.get("support_total", 0.0)),
                "suppression_pressure": _round(selected_payload.get("suppression_pressure", 0.0)),
                "net_utility": _round(selected_payload.get("net_utility", 0.0)),
            },
            "gap_assist_v1": {
                "transition_side_separation": _round(transition_side_separation),
                "transition_confirm_fake_gap": _round(confirm_fake_gap),
                "wait_confirm_gap": _round(wait_confirm_gap),
                "management_continue_fail_gap": _round(continue_fail_gap),
                "management_recover_reentry_gap": _round(recover_reentry_gap),
                "hold_exit_gap": _round(hold_exit_gap),
                "same_side_flip_gap": _round(same_side_flip_gap),
                "belief_barrier_tension_gap": _round(belief_barrier_tension_gap),
                "confirm_wait_state": str(execution_gap_support.get("confirm_wait_state", "") or ""),
                "hold_exit_state": str(execution_gap_support.get("hold_exit_state", "") or ""),
                "same_side_flip_state": str(execution_gap_support.get("same_side_flip_state", "") or ""),
                "belief_barrier_tension_state": str(
                    execution_gap_support.get("belief_barrier_tension_state", "") or ""
                ),
                "dominant_execution_gap": str(execution_gap_support.get("dominant_execution_gap", "") or ""),
            },
            "forecast_gap_usage_v1": forecast_gap_usage_v1,
            "utility_hints": {
                "priority_hint": priority_hint,
                "wait_vs_enter_hint": wait_vs_enter_hint,
                "gap_dominant_hint": str(execution_gap_support.get("dominant_execution_gap", "") or ""),
                "forecast_branch_hint": forecast_branch_hint,
            },
            "identity_guard": {
                "identity_preserved": True,
                "non_owner_fields": list(ENERGY_IDENTITY_NON_OWNERSHIP_V1["protected_fields"]),
            },
            "final_net_utility": _round(selected_payload.get("net_utility", 0.0)),
            "consumer_usage_trace": {
                "contract_version": "consumer_usage_trace_v1",
                "recorded": False,
                "usage_source": "not_yet_consumed",
                "component": "",
                "usage_mode": "not_yet_consumed",
                "consumed_fields": [],
                "branch_records": [],
                "selected_side": selected_side,
                "action_readiness": _round(selected_payload.get("action_readiness", 0.0)),
                "final_net_utility": _round(selected_payload.get("net_utility", 0.0)),
                "priority_hint": priority_hint,
                "wait_vs_enter_hint": wait_vs_enter_hint,
                "gap_dominant_hint": str(execution_gap_support.get("dominant_execution_gap", "") or ""),
                "forecast_branch_hint": forecast_branch_hint,
                "soft_block_active": bool(soft_block_hint.get("active", False)),
                "soft_block_reason": str(soft_block_hint.get("reason", "") or ""),
                "soft_block_strength": _round(_to_float(soft_block_hint.get("strength", 0.0))),
                "confidence_adjustment_direction": str(confidence_adjustment_hint.get("direction", "") or ""),
                "confidence_adjustment_delta": _round(_to_float(confidence_adjustment_hint.get("delta", 0.0))),
                "forecast_gap_usage_active": forecast_gap_usage_active,
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
            },
            "logging_replay_freeze": {
                "applied": True,
                "contract_version": ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"],
                "required_sections": list(ENERGY_LOGGING_REPLAY_CONTRACT_V1["required_sections"]),
                "consumer_usage_required_fields": list(
                    ENERGY_LOGGING_REPLAY_CONTRACT_V1["consumer_usage_required_fields"]
                ),
                "required_sections_present": [],
                "final_net_utility": _round(selected_payload.get("net_utility", 0.0)),
                "consumer_usage_trace_present": False,
                "consumer_usage_source": "not_yet_consumed",
                "consumer_usage_component": "",
                "consumer_usage_mode": "not_yet_consumed",
                "replay_explanation_ready": True,
            },
            "legacy_bridge": legacy_bridge,
            "logging_replay_ready": True,
        },
    }
    output_payload["metadata"]["scope_freeze"]["forbidden_output_fields_absent"] = [
        field for field in ENERGY_OUTPUT_CONTRACT_V1["forbidden_outputs"] if field not in output_payload
    ]
    output_payload["metadata"]["output_freeze"]["forbidden_top_level_fields_absent"] = [
        field for field in ENERGY_OUTPUT_CONTRACT_V1["forbidden_outputs"] if field not in output_payload
    ]
    output_payload["metadata"]["output_freeze"]["forbidden_semantic_label_like_fields_absent"] = [
        field for field in ENERGY_OUTPUT_CONTRACT_V1["forbidden_semantic_label_like_outputs"] if field not in output_payload
    ]
    output_payload["metadata"]["identity_non_ownership_freeze"]["identity_fields_absent_from_output"] = [
        field for field in ENERGY_IDENTITY_NON_OWNERSHIP_V1["protected_fields"] if field not in output_payload
    ]
    output_payload["metadata"]["logging_replay_freeze"]["required_sections_present"] = [
        section
        for section in ENERGY_LOGGING_REPLAY_CONTRACT_V1["required_sections"]
        if section in output_payload["metadata"]
    ]
    return output_payload


def resolve_entry_service_energy_usage(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    row = _coerce_mapping(payload or {})
    recorded_trace = _coerce_mapping(row.get("consumer_energy_usage_trace_v1", {}))
    if recorded_trace:
        consumed_fields = _normalize_consumed_fields(recorded_trace.get("consumed_fields", []))
        branch_records = _normalize_usage_branch_records(recorded_trace.get("branch_records", []))
        live_gate_applied = _to_bool(recorded_trace.get("live_gate_applied", False), bool(consumed_fields))
        usage_mode = str(recorded_trace.get("usage_mode", "") or "").strip()
        if not usage_mode:
            usage_mode = "live_branch_applied" if live_gate_applied else ("advisory_only" if consumed_fields else "not_consumed")
        return {
            "component": str(recorded_trace.get("component", "EntryService") or "EntryService"),
            "usage_source": str(recorded_trace.get("usage_source", "recorded") or "recorded"),
            "consumed_fields": consumed_fields,
            "branch_records": branch_records,
            "usage_mode": usage_mode,
            "live_gate_applied": live_gate_applied,
        }
    consumed_fields: list[str] = []
    branch_records: list[dict[str, Any]] = []

    def _consume(field_name: str) -> None:
        normalized = str(field_name or "").strip()
        if normalized and normalized not in consumed_fields:
            consumed_fields.append(normalized)

    def _record_inferred_branch(branch: str, reason: str, fields: list[str]) -> None:
        branch_records.append(
            {
                "branch": str(branch or "").strip(),
                "reason": str(reason or "").strip(),
                "consumed_fields": _normalize_consumed_fields(fields),
            }
        )

    core_reason = str(row.get("core_reason", "") or "").strip().lower()
    block_reason = str(
        row.get("consumer_block_reason", row.get("action_none_reason", row.get("blocked_by", ""))) or ""
    ).strip().lower()
    soft_block_active = _to_bool(row.get("consumer_energy_soft_block_active", False))
    confidence_delta = _to_float(row.get("consumer_energy_confidence_delta", 0.0))
    forecast_gap_live_gate_used = _to_bool(row.get("consumer_energy_forecast_gap_live_gate_used", False))
    used_soft_block_branch = bool(
        soft_block_active
        or core_reason == "energy_soft_block"
        or block_reason == "energy_soft_block"
    )

    if used_soft_block_branch:
        _consume("action_readiness")
        _consume("soft_block_hint")
        _consume("metadata.utility_hints.priority_hint")
        _record_inferred_branch(
            "soft_block_branch",
            block_reason or core_reason or "energy_soft_block",
            [
                "action_readiness",
                "soft_block_hint",
                "metadata.utility_hints.priority_hint",
            ],
        )

    if abs(confidence_delta) > 1e-9:
        _consume("confidence_adjustment_hint")
        _record_inferred_branch(
            "confidence_adjustment",
            str(row.get("consumer_energy_confidence_reason", "") or ""),
            ["confidence_adjustment_hint"],
        )

    if forecast_gap_live_gate_used:
        _consume("metadata.forecast_gap_usage_v1")
        _consume("metadata.utility_hints.gap_dominant_hint")
        _consume("metadata.utility_hints.forecast_branch_hint")
        _record_inferred_branch(
            "forecast_gap_live_gate",
            str(
                row.get("consumer_energy_forecast_branch_hint", "")
                or row.get("consumer_energy_gap_dominant_hint", "")
                or ""
            ),
            [
                "metadata.forecast_gap_usage_v1",
                "metadata.utility_hints.gap_dominant_hint",
                "metadata.utility_hints.forecast_branch_hint",
            ],
        )

    live_gate_applied = bool(consumed_fields)
    usage_mode = "live_branch_applied" if live_gate_applied else "not_consumed"

    return {
        "component": "EntryService",
        "usage_source": "inferred",
        "consumed_fields": consumed_fields,
        "branch_records": branch_records,
        "usage_mode": usage_mode,
        "live_gate_applied": live_gate_applied,
    }


def attach_energy_consumer_usage_trace(
    payload: Mapping[str, Any] | None,
    *,
    component: str,
    consumed_fields: list[str] | tuple[str, ...],
    usage_source: str = "recorded",
    usage_mode: str = "advisory_only",
    effective_action: str = "",
    guard_result: str = "",
    block_reason: str = "",
    block_kind: str = "",
    block_source_layer: str = "",
    decision_outcome: str = "",
    wait_state: str = "",
    wait_reason: str = "",
    live_gate_applied: bool = False,
    branch_records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] | None = None,
) -> dict[str, Any]:
    helper_payload = copy.deepcopy(_coerce_mapping(payload or {}))
    if not helper_payload:
        return {}

    metadata = _coerce_mapping(helper_payload.get("metadata", {}))
    utility_hints = _coerce_mapping(metadata.get("utility_hints", {}))
    forecast_gap_usage = _coerce_mapping(metadata.get("forecast_gap_usage_v1", {}))
    soft_block_hint = _coerce_mapping(helper_payload.get("soft_block_hint", {}))
    confidence_adjustment_hint = _coerce_mapping(helper_payload.get("confidence_adjustment_hint", {}))
    normalized_fields = _normalize_consumed_fields(consumed_fields)
    normalized_branch_records = _normalize_usage_branch_records(branch_records or [])
    normalized_usage_source = str(usage_source or "").strip().lower() or "recorded"
    if normalized_usage_source not in {"recorded", "inferred", "not_yet_consumed"}:
        normalized_usage_source = "recorded"

    consumer_usage_trace = {
        "contract_version": "consumer_usage_trace_v1",
        "recorded": normalized_usage_source == "recorded",
        "usage_source": normalized_usage_source,
        "branch_records": normalized_branch_records,
        "component": str(component or ""),
        "usage_mode": str(usage_mode or "advisory_only"),
        "consumed_fields": normalized_fields,
        "selected_side": str(helper_payload.get("selected_side", "") or ""),
        "action_readiness": _round(_to_float(helper_payload.get("action_readiness", 0.0))),
        "final_net_utility": _round(_to_float(helper_payload.get("net_utility", 0.0))),
        "priority_hint": str(utility_hints.get("priority_hint", "") or ""),
        "wait_vs_enter_hint": str(utility_hints.get("wait_vs_enter_hint", "") or ""),
        "gap_dominant_hint": str(utility_hints.get("gap_dominant_hint", "") or ""),
        "forecast_branch_hint": str(utility_hints.get("forecast_branch_hint", "") or ""),
        "soft_block_active": bool(soft_block_hint.get("active", False)),
        "soft_block_reason": str(soft_block_hint.get("reason", "") or ""),
        "soft_block_strength": _round(_to_float(soft_block_hint.get("strength", 0.0))),
        "confidence_adjustment_direction": str(confidence_adjustment_hint.get("direction", "") or ""),
        "confidence_adjustment_delta": _round(_to_float(confidence_adjustment_hint.get("delta", 0.0))),
        "forecast_gap_usage_active": bool(forecast_gap_usage.get("active", False)),
        "effective_action": str(effective_action or "").strip().upper(),
        "guard_result": str(guard_result or ""),
        "block_reason": str(block_reason or ""),
        "block_kind": str(block_kind or ""),
        "block_source_layer": str(block_source_layer or ""),
        "decision_outcome": str(decision_outcome or ""),
        "wait_state": str(wait_state or ""),
        "wait_reason": str(wait_reason or ""),
        "used_for_identity_decision": False,
        "used_for_direct_order_gate": False,
        "live_gate_applied": bool(live_gate_applied),
        "identity_preserved": True,
    }
    metadata["consumer_usage_trace"] = consumer_usage_trace
    metadata["final_net_utility"] = _round(_to_float(helper_payload.get("net_utility", 0.0)))
    logging_replay_freeze = _coerce_mapping(metadata.get("logging_replay_freeze", {}))
    logging_replay_freeze.update(
        {
            "applied": True,
            "contract_version": ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"],
            "required_sections": list(ENERGY_LOGGING_REPLAY_CONTRACT_V1["required_sections"]),
            "consumer_usage_required_fields": list(
                ENERGY_LOGGING_REPLAY_CONTRACT_V1["consumer_usage_required_fields"]
            ),
            "required_sections_present": [
                section
                for section in ENERGY_LOGGING_REPLAY_CONTRACT_V1["required_sections"]
                if section in metadata
            ],
            "final_net_utility": _round(_to_float(helper_payload.get("net_utility", 0.0))),
            "consumer_usage_trace_present": True,
            "consumer_usage_source": normalized_usage_source,
            "consumer_usage_component": str(component or ""),
            "consumer_usage_mode": str(usage_mode or "advisory_only"),
            "replay_explanation_ready": True,
        }
    )
    metadata["logging_replay_freeze"] = logging_replay_freeze
    metadata["logging_replay_ready"] = True
    helper_payload["metadata"] = metadata
    return helper_payload


def resolve_energy_helper_input(container: Any) -> dict[str, Any]:
    mapping = _container_mapping(container)
    prs_log_contract = _coerce_mapping(mapping.get("prs_log_contract_v2", {}))
    candidate_fields: list[str] = []
    for field_name in (
        mapping.get("prs_canonical_energy_field"),
        prs_log_contract.get("canonical_energy_field"),
        "energy_helper_v2",
    ):
        normalized = str(field_name or "").strip()
        if normalized and normalized not in candidate_fields:
            candidate_fields.append(normalized)
    for field_name in candidate_fields:
        payload = _coerce_mapping(mapping.get(field_name, {}))
        if payload:
            return payload
    return {}


def energy_scope_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / ENERGY_SCOPE_CONTRACT_V1["documentation_path"]
