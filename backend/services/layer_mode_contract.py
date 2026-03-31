from __future__ import annotations

import copy
import json
from pathlib import Path

from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2,
    OBSERVE_CONFIRM_ROUTING_POLICY_V2,
)


LAYER_MODE_MODE_CONTRACT_V1 = {
    "contract_version": "layer_mode_contract_v1",
    "scope": "canonical_layer_mode_values_only",
    "layer_mode_component": "LayerModeVocabulary",
    "canonical_modes": [
        {
            "mode": "shadow",
            "role": "compute and log only",
            "execution_influence": "none_direct",
        },
        {
            "mode": "assist",
            "role": "softly influence effective output",
            "execution_influence": "confidence_or_priority_adjustment",
        },
        {
            "mode": "enforce",
            "role": "allow direct policy-strength enforcement",
            "execution_influence": "hard_gate_or_suppression_allowed",
        },
    ],
    "mode_order": ["shadow", "assist", "enforce"],
    "principles": [
        "layer mode vocabulary is global and canonical across semantic layers",
        "mode meaning applies to influence strength, not semantic existence",
        "mode values stay lowercase and stable in logs and config",
    ],
    "runtime_embedding_field": "layer_mode_contract_v1",
    "documentation_path": "docs/layer_mode_mode_contract.md",
}


LAYER_MODE_LAYER_INVENTORY_V1 = {
    "contract_version": "layer_mode_layer_inventory_v1",
    "scope": "semantic_layer_targets_for_mode_only",
    "layer_mode_component": "LayerModeLayerInventory",
    "layers": [
        {
            "layer": "Position",
            "raw_fields": ["position_snapshot_v2"],
            "semantic_role": "structural position context",
        },
        {
            "layer": "Response",
            "raw_fields": ["response_vector_v2"],
            "semantic_role": "trigger-direction response context",
        },
        {
            "layer": "State",
            "raw_fields": ["state_vector_v2"],
            "semantic_role": "regime and state interpretation",
        },
        {
            "layer": "Evidence",
            "raw_fields": ["evidence_vector_v1"],
            "semantic_role": "setup-strength evidence aggregation",
        },
        {
            "layer": "Belief",
            "raw_fields": ["belief_state_v1"],
            "semantic_role": "persistence and directional belief",
        },
        {
            "layer": "Barrier",
            "raw_fields": ["barrier_state_v1"],
            "semantic_role": "suppression and invalidation pressure",
        },
        {
            "layer": "Forecast",
            "raw_fields": [
                "forecast_features_v1",
                "transition_forecast_v1",
                "trade_management_forecast_v1",
                "forecast_gap_metrics_v1",
            ],
            "semantic_role": "forward-looking confidence and management scoring",
        },
    ],
    "layer_order": ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"],
    "principles": [
        "layer inventory defines which semantic outputs may receive a later mode policy",
        "inventory membership does not imply current enforcement strength",
        "observe_confirm and consumer are downstream consumers, not mode-owned semantic layers",
    ],
    "runtime_embedding_field": "layer_mode_layer_inventory_v1",
    "documentation_path": "docs/layer_mode_layer_inventory.md",
}


LAYER_MODE_DEFAULT_POLICY_V1 = {
    "contract_version": "layer_mode_default_policy_v1",
    "scope": "migration_aware_default_layer_modes_only",
    "layer_mode_component": "LayerModeDefaultPolicy",
    "policy_rows": [
        {
            "layer": "Position",
            "current_effective_default_mode": "enforce",
            "target_mode_sequence": ["enforce"],
        },
        {
            "layer": "Response",
            "current_effective_default_mode": "enforce",
            "target_mode_sequence": ["enforce"],
        },
        {
            "layer": "State",
            "current_effective_default_mode": "assist",
            "target_mode_sequence": ["assist", "enforce"],
        },
        {
            "layer": "Evidence",
            "current_effective_default_mode": "enforce",
            "target_mode_sequence": ["enforce"],
        },
        {
            "layer": "Belief",
            "current_effective_default_mode": "shadow",
            "target_mode_sequence": ["shadow", "assist", "enforce"],
        },
        {
            "layer": "Barrier",
            "current_effective_default_mode": "shadow",
            "target_mode_sequence": ["shadow", "assist", "enforce"],
        },
        {
            "layer": "Forecast",
            "current_effective_default_mode": "assist",
            "target_mode_sequence": ["assist", "enforce"],
        },
    ],
    "principles": [
        "current effective defaults may intentionally lag the final target sequence",
        "target sequence defines migration direction without implying immediate enforcement",
        "single-step sequences mean current default and target are already aligned",
    ],
    "runtime_embedding_field": "layer_mode_default_policy_v1",
    "documentation_path": "docs/layer_mode_default_policy.md",
}


LAYER_MODE_DUAL_WRITE_CONTRACT_V1 = {
    "contract_version": "layer_mode_dual_write_v1",
    "scope": "raw_effective_dual_write_only",
    "layer_mode_component": "LayerModeDualWrite",
    "effective_trace_field": "layer_mode_effective_trace_v1",
    "layer_rows": [
        {
            "layer": "Position",
            "raw_fields": ["position_snapshot_v2"],
            "effective_fields": ["position_snapshot_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "Response",
            "raw_fields": ["response_vector_v2"],
            "effective_fields": ["response_vector_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "State",
            "raw_fields": ["state_vector_v2"],
            "effective_fields": ["state_vector_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "Evidence",
            "raw_fields": ["evidence_vector_v1"],
            "effective_fields": ["evidence_vector_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "Belief",
            "raw_fields": ["belief_state_v1"],
            "effective_fields": ["belief_state_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "Barrier",
            "raw_fields": ["barrier_state_v1"],
            "effective_fields": ["barrier_state_effective_v1"],
            "effective_shape": "same_shape_copy",
        },
        {
            "layer": "Forecast",
            "raw_fields": [
                "forecast_features_v1",
                "transition_forecast_v1",
                "trade_management_forecast_v1",
                "forecast_gap_metrics_v1",
            ],
            "effective_fields": ["forecast_effective_policy_v1"],
            "effective_shape": "policy_bundle_copy",
        },
    ],
    "principles": [
        "raw semantic outputs remain preserved beside effective outputs",
        "effective outputs must stay explainable in terms of later blocks or suppressions",
        "before a dedicated overlay exists, effective outputs may bridge to raw-equivalent copies",
        "identity-bearing fields stay unchanged while mode policy is still bridge-only",
    ],
    "runtime_embedding_field": "layer_mode_dual_write_contract_v1",
    "documentation_path": "docs/layer_mode_dual_write_contract.md",
}


LAYER_MODE_INFLUENCE_SEMANTICS_V1 = {
    "contract_version": "layer_mode_influence_semantics_v1",
    "scope": "mode_to_execution_influence_matrix_only",
    "layer_mode_component": "LayerModeInfluenceSemantics",
    "global_mode_semantics": [
        {
            "mode": "shadow",
            "summary": "metadata or log only",
            "allowed_effects": ["metadata_log_only", "trace_only"],
            "forbidden_effects": [
                "confidence_modulation",
                "priority_boost",
                "reason_annotation",
                "soft_warning",
                "hard_block",
                "action_downgrade",
                "confirm_to_observe_suppression",
                "execution_veto",
            ],
        },
        {
            "mode": "assist",
            "summary": "soft influence only",
            "allowed_effects": ["confidence_modulation", "priority_boost", "reason_annotation", "soft_warning"],
            "forbidden_effects": ["hard_block", "action_downgrade", "confirm_to_observe_suppression", "execution_veto"],
        },
        {
            "mode": "enforce",
            "summary": "hard execution influence allowed where the layer matrix permits it",
            "allowed_effects": [
                "confidence_modulation",
                "priority_boost",
                "reason_annotation",
                "soft_warning",
                "hard_block",
                "action_downgrade",
                "confirm_to_observe_suppression",
                "execution_veto",
            ],
            "forbidden_effects": ["archetype_rewrite", "side_rewrite", "semantic_redefinition"],
        },
    ],
    "layer_rows": [
        {
            "layer": "Position",
            "assist_effects": ["reason_annotation", "priority_boost"],
            "enforce_effects": ["hard_block", "execution_veto"],
            "dominant_assist_role": "structural_priority_hint",
            "dominant_enforce_role": "structural_veto",
        },
        {
            "layer": "Response",
            "assist_effects": ["reason_annotation", "priority_boost", "confidence_modulation"],
            "enforce_effects": ["hard_block", "action_downgrade"],
            "dominant_assist_role": "trigger_strength_hint",
            "dominant_enforce_role": "trigger_validity_gate",
        },
        {
            "layer": "State",
            "assist_effects": ["confidence_modulation", "reason_annotation", "soft_warning"],
            "enforce_effects": ["hard_block", "action_downgrade"],
            "dominant_assist_role": "regime_filter_hint",
            "dominant_enforce_role": "regime_gate",
        },
        {
            "layer": "Evidence",
            "assist_effects": ["confidence_modulation", "priority_boost", "reason_annotation"],
            "enforce_effects": ["hard_block", "action_downgrade"],
            "dominant_assist_role": "setup_strength_hint",
            "dominant_enforce_role": "setup_strength_gate",
        },
        {
            "layer": "Belief",
            "assist_effects": ["confidence_modulation", "reason_annotation", "soft_warning"],
            "enforce_effects": ["action_downgrade", "confirm_to_observe_suppression"],
            "dominant_assist_role": "persistence_bias",
            "dominant_enforce_role": "persistence_suppression",
        },
        {
            "layer": "Barrier",
            "assist_effects": ["reason_annotation", "soft_warning"],
            "enforce_effects": ["confirm_to_observe_suppression", "execution_veto", "hard_block"],
            "dominant_assist_role": "suppression_warning",
            "dominant_enforce_role": "suppression_veto",
        },
        {
            "layer": "Forecast",
            "assist_effects": ["confidence_modulation", "priority_boost", "reason_annotation"],
            "enforce_effects": ["action_downgrade", "confirm_to_observe_suppression"],
            "forbidden_even_in_enforce": ["execution_veto"],
            "dominant_assist_role": "readiness_modulation",
            "dominant_enforce_role": "confirm_wait_split",
        },
    ],
    "principles": [
        "mode meaning is global, but allowed execution effects vary by layer",
        "shadow never changes execution behavior directly",
        "assist can shape confidence, priority, or reasoning but cannot hard block",
        "enforce may block or suppress only when the layer row explicitly allows it",
        "forecast influence stays centered on readiness or confirm-wait splitting, not archetype identity changes",
        "barrier influence stays centered on suppression and invalidation pressure",
    ],
    "runtime_embedding_field": "layer_mode_influence_semantics_v1",
    "documentation_path": "docs/layer_mode_influence_semantics.md",
}


LAYER_MODE_APPLICATION_CONTRACT_V1 = {
    "contract_version": "layer_mode_application_contract_v1",
    "scope": "layer_specific_application_policy_only",
    "layer_mode_component": "LayerModeLayerApplication",
    "layer_rows": [
        {
            "layer": "Position",
            "application_role": "structural_truth",
            "first_semantically_active_mode": "enforce",
            "assist_application": ["reason_annotation"],
            "enforce_application": ["zone_side_contradiction_veto", "structural_execution_veto"],
            "policy_summary": "structural truth is almost always enforce; zone or side contradiction may veto immediately",
        },
        {
            "layer": "Response",
            "application_role": "core_trigger_candidate",
            "first_semantically_active_mode": "enforce",
            "assist_application": ["reason_annotation", "priority_boost"],
            "enforce_application": ["core_trigger_gate", "trigger_validity_veto"],
            "policy_summary": "response is the core trigger candidate and therefore lives mostly in enforce",
        },
        {
            "layer": "State",
            "application_role": "regime_filter",
            "first_semantically_active_mode": "assist",
            "assist_application": ["regime_filter", "confidence_modulation", "soft_warning"],
            "enforce_application": ["regime_gate", "action_downgrade"],
            "policy_summary": "state starts as a regime filter in assist and can later graduate into enforce",
        },
        {
            "layer": "Evidence",
            "application_role": "setup_strength",
            "first_semantically_active_mode": "enforce",
            "assist_application": ["confidence_modulation", "reason_annotation"],
            "enforce_application": ["setup_strength_gate", "setup_strength_veto"],
            "policy_summary": "evidence is setup-strength based and is expected to enforce once active",
        },
        {
            "layer": "Belief",
            "application_role": "persistence_continuation_bias",
            "first_semantically_active_mode": "assist",
            "assist_application": ["persistence_bias", "continuation_bias", "confidence_modulation"],
            "enforce_application": ["confirm_to_observe_suppression", "action_downgrade"],
            "policy_summary": "belief should first shape persistence or continuation bias in assist, then only later suppress in enforce",
        },
        {
            "layer": "Barrier",
            "application_role": "suppression_and_risk",
            "first_semantically_active_mode": "assist",
            "assist_application": ["suppression_warning", "risk_annotation", "soft_warning"],
            "enforce_application": ["confirm_to_observe_suppression", "risk_block", "execution_veto"],
            "policy_summary": "barrier is suppression and risk focused, with stronger enforce behavior deferred until later rollout",
        },
        {
            "layer": "Forecast",
            "application_role": "readiness_and_management_preference",
            "first_semantically_active_mode": "assist",
            "assist_application": ["confidence_modulation", "confirm_wait_guidance", "management_preference_annotation"],
            "enforce_application": ["confirm_to_observe_suppression", "action_downgrade", "management_preference_weighting"],
            "identity_guard_fields": ["archetype_id", "side"],
            "forbidden_application": ["archetype_rewrite", "side_rewrite", "execution_veto"],
            "policy_summary": "forecast may not change archetype identity; it only shapes confidence, confirm-wait split, and management preference",
        },
    ],
    "principles": [
        "layer application policy is separate from the global mode vocabulary",
        "first_semantically_active_mode defines when a layer starts affecting execution rather than only logging",
        "position, response, and evidence are treated as more immediately enforceable layers",
        "belief, barrier, and forecast keep a softer rollout path before stronger enforcement",
        "forecast application stays under identity guard and cannot rewrite archetype or side",
    ],
    "runtime_embedding_field": "layer_mode_application_contract_v1",
    "documentation_path": "docs/layer_mode_application_contract.md",
}


LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1 = {
    "contract_version": "layer_mode_identity_guard_v1",
    "scope": "layer_identity_guard_only",
    "layer_mode_component": "LayerModeIdentityGuard",
    "routing_policy_contract_ref": OBSERVE_CONFIRM_ROUTING_POLICY_V2["contract_version"],
    "confidence_semantics_contract_ref": OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2["contract_version"],
    "protected_fields": ["archetype_id", "side"],
    "focus_layers": [
        {
            "layer": "Belief",
            "guard_active": True,
            "protected_fields": ["archetype_id", "side"],
            "allowed_adjustments": ["confidence", "action_readiness", "confirm_to_wait", "block_reason_annotation"],
            "forbidden_adjustments": ["archetype_rewrite", "side_rewrite", "setup_rename"],
            "reason": "belief may bias persistence but may not rename the candidate identity",
        },
        {
            "layer": "Barrier",
            "guard_active": True,
            "protected_fields": ["archetype_id", "side"],
            "allowed_adjustments": ["confidence", "action_readiness", "confirm_to_wait", "block_reason_annotation"],
            "forbidden_adjustments": ["archetype_rewrite", "side_rewrite", "setup_rename"],
            "reason": "barrier may suppress or block, but only against the existing candidate identity",
        },
        {
            "layer": "Forecast",
            "guard_active": True,
            "protected_fields": ["archetype_id", "side"],
            "allowed_adjustments": ["confidence", "action_readiness", "confirm_to_wait", "block_reason_annotation"],
            "forbidden_adjustments": ["archetype_rewrite", "side_rewrite", "setup_rename", "execution_veto"],
            "reason": "forecast may modulate readiness or confirm-wait split, but may not replace semantic identity",
        },
    ],
    "principles": [
        "identity guard is always on for belief, barrier, and forecast regardless of their current rollout mode",
        "archetype_id and side remain owned by the observe-confirm identity path",
        "non-identity layers may adjust readiness or annotate block reasons only within the allowed adjustment set",
        "identity guard follows observe_confirm_routing_policy_v2 and observe_confirm_confidence_semantics_v2",
    ],
    "runtime_embedding_field": "layer_mode_identity_guard_contract_v1",
    "documentation_path": "docs/layer_mode_identity_guard_contract.md",
}


LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1 = {
    "contract_version": "layer_mode_policy_overlay_output_v1",
    "scope": "canonical_policy_applied_overlay_output_only",
    "layer_mode_component": "LayerModePolicyOverlayOutput",
    "canonical_output_field": "layer_mode_policy_v1",
    "required_fields": [
        "layer_modes",
        "effective_influences",
        "suppressed_reasons",
        "confidence_adjustments",
        "hard_blocks",
        "mode_decision_trace",
    ],
    "field_roles": {
        "layer_modes": "current effective mode by semantic layer",
        "effective_influences": "currently active influence and application effects by layer",
        "suppressed_reasons": "applied suppression reasons emitted by policy overlay",
        "confidence_adjustments": "applied confidence or readiness modulation rows",
        "hard_blocks": "applied hard block or veto rows",
        "mode_decision_trace": "deterministic explanation trace for the current overlay result",
    },
    "principles": [
        "policy overlay output is emitted separately from raw semantic outputs",
        "layer mode output may be bridge-only before dedicated runtime deltas are introduced",
        "identity-preserving overlays may change readiness, suppression state, or block reasons without changing archetype_id or side",
        "empty suppression, confidence, or hard block lists are valid when no runtime overlay delta is applied yet",
    ],
    "runtime_embedding_field": "layer_mode_policy_overlay_output_contract_v1",
    "documentation_path": "docs/layer_mode_policy_overlay_output_contract.md",
}


LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1 = {
    "contract_version": "layer_mode_logging_replay_contract_v1",
    "scope": "replayable_layer_mode_audit_only",
    "layer_mode_component": "LayerModeLoggingReplay",
    "canonical_output_field": "layer_mode_logging_replay_v1",
    "required_fields": [
        "configured_modes",
        "raw_result_fields",
        "effective_result_fields",
        "applied_adjustments",
        "block_suppress_reasons",
        "final_consumer_action",
    ],
    "principles": [
        "logging payload must be replayable from a single decision row",
        "configured mode, raw result, effective result, applied adjustment, and final consumer action must be inspectable together",
        "logging payload may be bridge-only before runtime layer-mode deltas are introduced",
        "block or suppress reasoning must preserve the distinction between policy-layer output and final consumer block outcome",
    ],
    "runtime_embedding_field": "layer_mode_logging_replay_contract_v1",
    "documentation_path": "docs/layer_mode_logging_replay_contract.md",
}


LAYER_MODE_TEST_CONTRACT_V1 = {
    "contract_version": "layer_mode_test_contract_v1",
    "scope": "layer_mode_regression_lock_only",
    "layer_mode_component": "LayerModeTestContract",
    "official_test_helper": "build_layer_mode_test_projection",
    "required_behavior_axes": [
        {
            "id": "deterministic_mode_output",
            "description": "the same semantic input and the same layer-mode configuration produce the same projected output",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "shadow_no_action_change",
            "description": "shadow mode leaves action and identity unchanged while staying log-only",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "assist_identity_preserving_modulation",
            "description": "assist may modulate confidence or priority, but keeps archetype_id and side unchanged",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "enforce_identity_preserving_block",
            "description": "enforce may project a hard block while preserving semantic identity",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "forecast_enforce_no_archetype_rewrite",
            "description": "Forecast.enforce may downgrade confirm readiness, but may not rewrite archetype_id or side",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "barrier_enforce_confirm_to_observe",
            "description": "Barrier.enforce may suppress CONFIRM into OBSERVE or WAIT while preserving identity",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
        {
            "id": "raw_effective_dual_write_present",
            "description": "raw and effective payloads remain emitted together for replay or explainability",
            "primary_test_file": "tests/unit/test_layer_mode_scope_contract.py",
        },
    ],
    "supporting_runtime_contract_tests": [
        "tests/unit/test_context_classifier.py",
        "tests/unit/test_entry_engines.py",
        "tests/unit/test_decision_models.py",
        "tests/unit/test_prs_engine.py",
    ],
    "runtime_embedding_field": "layer_mode_test_contract_v1",
    "documentation_path": "docs/layer_mode_test_contract.md",
}


LAYER_MODE_FREEZE_HANDOFF_V1 = {
    "contract_version": "layer_mode_freeze_handoff_v1",
    "scope": "canonical_layer_mode_freeze_and_handoff_only",
    "layer_mode_component": "LayerModeFreezeHandoff",
    "official_handoff_helper": "resolve_layer_mode_handoff_payload",
    "consumer_policy_input_field": "layer_mode_policy_v1",
    "logging_replay_field": "layer_mode_logging_replay_v1",
    "handoff_sections": [
        "raw_semantic_fields",
        "effective_semantic_fields",
        "policy_overlay",
        "logging_replay",
        "consumer_policy_bridge",
        "energy_future_role",
    ],
    "completion_criteria": [
        "all semantic layers always compute",
        "mode controls influence strength only",
        "raw and effective dual-write remains present",
        "policy overlay stays above consumer handoff and below execution",
        "energy may be redefined later as a utility or compression helper rather than a standalone semantic layer",
    ],
    "policy_overlay_position": "above consumer handoff and below execution",
    "energy_future_role": {
        "standalone_semantic_layer": False,
        "allowed_future_roles": ["utility_helper", "compression_helper"],
        "blocked_future_roles": ["independent_meaning_layer"],
    },
    "runtime_embedding_field": "layer_mode_freeze_handoff_v1",
    "documentation_path": "docs/layer_mode_freeze_handoff.md",
}


LAYER_MODE_SCOPE_CONTRACT_V1 = {
    "contract_version": "layer_mode_scope_v1",
    "scope": "always_compute_policy_overlay_only",
    "layer_mode_component": "LayerModePolicy",
    "objective": "Freeze Layer Mode as a policy overlay that never disables semantic computation and only changes effective outputs or execution influence.",
    "mode_contract_v1": LAYER_MODE_MODE_CONTRACT_V1,
    "layer_inventory_v1": LAYER_MODE_LAYER_INVENTORY_V1,
    "default_mode_policy_v1": LAYER_MODE_DEFAULT_POLICY_V1,
    "dual_write_contract_v1": LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    "influence_semantics_v1": LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    "application_contract_v1": LAYER_MODE_APPLICATION_CONTRACT_V1,
    "identity_guard_contract_v1": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    "policy_overlay_output_contract_v1": LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    "logging_replay_contract_v1": LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    "test_contract_v1": LAYER_MODE_TEST_CONTRACT_V1,
    "freeze_handoff_v1": LAYER_MODE_FREEZE_HANDOFF_V1,
    "core_principles": [
        "semantic layers always compute their raw outputs",
        "raw outputs remain available regardless of future layer mode selection",
        "layer mode changes only effective outputs and execution influence",
        "layer mode does not rewrite semantic meaning, archetype identity, or side identity",
    ],
    "in_scope": [
        "preserve raw semantic outputs for Position, Response, State, Evidence, Belief, Barrier, and Forecast",
        "define layer mode as an overlay above raw semantic outputs and below execution decisions",
        "reserve effective-output shaping for future policy definitions without disabling computation",
        "prepare a later layer-mode policy overlay to sit above consumer handoff outputs",
    ],
    "non_responsibilities": [
        "turning semantic layer computation on or off",
        "redefining semantic layer meaning",
        "rewriting ObserveConfirmSnapshot identity fields directly",
        "allowing consumer execution paths to re-interpret raw semantic vectors",
    ],
    "raw_output_policy": {
        "raw_outputs_always_emitted": True,
        "compute_disable_allowed": False,
        "effective_output_role": "derived layer-mode overlay only",
        "execution_influence_role": "policy-strength adjustment only",
        "raw_effective_dual_write_principle": "when effective outputs are introduced, raw outputs remain preserved beside them",
        "dual_write_contract_version": "layer_mode_dual_write_v1",
        "effective_trace_field": "layer_mode_effective_trace_v1",
        "influence_semantics_contract_version": "layer_mode_influence_semantics_v1",
        "influence_trace_field": "layer_mode_influence_trace_v1",
        "application_contract_version": "layer_mode_application_contract_v1",
        "application_trace_field": "layer_mode_application_trace_v1",
        "identity_guard_contract_version": "layer_mode_identity_guard_v1",
        "identity_guard_trace_field": "layer_mode_identity_guard_trace_v1",
        "policy_overlay_output_contract_version": "layer_mode_policy_overlay_output_v1",
        "policy_overlay_output_field": "layer_mode_policy_v1",
        "logging_replay_contract_version": "layer_mode_logging_replay_contract_v1",
        "logging_replay_field": "layer_mode_logging_replay_v1",
    },
    "integration_target": {
        "consumer_handoff_contract": "consumer_freeze_handoff_v1",
        "overlay_position": "above consumer handoff and below execution",
        "layer_mode_ready": True,
    },
    "deferred_definitions": [],
    "runtime_embedding_field": "layer_mode_scope_contract_v1",
    "documentation_path": "docs/layer_mode_scope_contract.md",
}


def _coerce_layer_mode_payload(value):
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
        except Exception:
            return {}
    if value is None:
        return {}
    return copy.deepcopy(value)


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _round6(value: float) -> float:
    return round(float(value), 6)


def _round_gap(value: float) -> float:
    return round(float(value), 6)


def _forecast_overlay_mode_profile(mode: str, gap_payload: dict) -> dict[str, object]:
    normalized_mode = str(mode or "shadow").strip().lower()
    dominant_gap = str(
        (
            ((gap_payload.get("metadata", {}) or {}).get("execution_gap_support_v1", {}) or {}).get(
                "dominant_execution_gap",
                "",
            )
            or ""
        )
    )
    if normalized_mode == "assist":
        return {
            "mode": normalized_mode,
            "policy_overlay_applied": True,
            "utility_overlay_applied": True,
            "consumer_hint_strength": "soft",
            "confirm_scale": 1.0 + (0.16 * _to_float(gap_payload.get("wait_confirm_gap", 0.0))),
            "false_break_scale": 1.0 - (0.12 * _to_float(gap_payload.get("wait_confirm_gap", 0.0))),
            "hold_scale": 1.0 + (0.15 * _to_float(gap_payload.get("hold_exit_gap", 0.0))),
            "fail_scale": 1.0 - (0.15 * _to_float(gap_payload.get("hold_exit_gap", 0.0))),
            "reentry_scale": 1.0 - (0.12 * _to_float(gap_payload.get("same_side_flip_gap", 0.0))),
            "barrier_drag": max(0.0, -_to_float(gap_payload.get("belief_barrier_tension_gap", 0.0))),
            "dominant_execution_gap": dominant_gap,
            "summary": "assist mode softly modulates confirm, hold, and cut hints using promoted gap metrics",
        }
    if normalized_mode == "enforce":
        return {
            "mode": normalized_mode,
            "policy_overlay_applied": True,
            "utility_overlay_applied": True,
            "consumer_hint_strength": "strong",
            "confirm_scale": 1.0 + (0.24 * _to_float(gap_payload.get("wait_confirm_gap", 0.0))),
            "false_break_scale": 1.0 - (0.18 * _to_float(gap_payload.get("wait_confirm_gap", 0.0))),
            "hold_scale": 1.0 + (0.22 * _to_float(gap_payload.get("hold_exit_gap", 0.0))),
            "fail_scale": 1.0 - (0.22 * _to_float(gap_payload.get("hold_exit_gap", 0.0))),
            "reentry_scale": 1.0 - (0.18 * _to_float(gap_payload.get("same_side_flip_gap", 0.0))),
            "barrier_drag": max(0.0, -_to_float(gap_payload.get("belief_barrier_tension_gap", 0.0))),
            "dominant_execution_gap": dominant_gap,
            "summary": "enforce mode increases confirm-wait and hold-exit separation without changing semantic identity",
        }
    return {
        "mode": normalized_mode,
        "policy_overlay_applied": True,
        "utility_overlay_applied": True,
        "consumer_hint_strength": "log_only",
        "confirm_scale": 1.0,
        "false_break_scale": 1.0,
        "hold_scale": 1.0,
        "fail_scale": 1.0,
        "reentry_scale": 1.0,
        "barrier_drag": 0.0,
        "dominant_execution_gap": dominant_gap,
        "summary": "shadow mode preserves raw forecast values while still recording overlay-ready utility semantics",
    }


def _apply_transition_overlay(transition_payload: dict, profile: dict[str, object]) -> tuple[dict, dict]:
    effective = _coerce_layer_mode_payload(transition_payload)
    raw_buy = _to_float(effective.get("p_buy_confirm", 0.0))
    raw_sell = _to_float(effective.get("p_sell_confirm", 0.0))
    raw_false_break = _to_float(effective.get("p_false_break", 0.0))
    raw_reversal = _to_float(effective.get("p_reversal_success", 0.0))
    raw_continuation = _to_float(effective.get("p_continuation_success", 0.0))
    confirm_scale = _to_float(profile.get("confirm_scale", 1.0), 1.0)
    false_break_scale = _to_float(profile.get("false_break_scale", 1.0), 1.0)
    barrier_drag = _to_float(profile.get("barrier_drag", 0.0), 0.0)

    effective["p_buy_confirm"] = _round6(_clamp01((raw_buy * confirm_scale) - (0.04 * barrier_drag)))
    effective["p_sell_confirm"] = _round6(_clamp01((raw_sell * confirm_scale) - (0.04 * barrier_drag)))
    effective["p_false_break"] = _round6(_clamp01((raw_false_break * false_break_scale) + (0.08 * barrier_drag)))
    effective["p_reversal_success"] = _round6(_clamp01(raw_reversal + (0.03 * barrier_drag)))
    effective["p_continuation_success"] = _round6(_clamp01(raw_continuation + (0.04 * max(confirm_scale - 1.0, -0.4))))

    meta = dict(effective.get("metadata", {}) or {})
    meta["effective_overlay_v1"] = {
        "layer": "Forecast",
        "branch": "transition",
        "mode": str(profile.get("mode", "") or ""),
        "overlay_strength": str(profile.get("consumer_hint_strength", "") or ""),
        "confirm_scale": _round_gap(confirm_scale),
        "false_break_scale": _round_gap(false_break_scale),
        "barrier_drag": _round_gap(barrier_drag),
    }
    effective["metadata"] = meta

    deltas = {
        "p_buy_confirm_delta": _round_gap(_to_float(effective.get("p_buy_confirm", 0.0)) - raw_buy),
        "p_sell_confirm_delta": _round_gap(_to_float(effective.get("p_sell_confirm", 0.0)) - raw_sell),
        "p_false_break_delta": _round_gap(_to_float(effective.get("p_false_break", 0.0)) - raw_false_break),
        "p_reversal_success_delta": _round_gap(_to_float(effective.get("p_reversal_success", 0.0)) - raw_reversal),
        "p_continuation_success_delta": _round_gap(
            _to_float(effective.get("p_continuation_success", 0.0)) - raw_continuation
        ),
    }
    return effective, deltas


def _apply_management_overlay(management_payload: dict, profile: dict[str, object]) -> tuple[dict, dict]:
    effective = _coerce_layer_mode_payload(management_payload)
    raw_continue = _to_float(effective.get("p_continue_favor", 0.0))
    raw_fail = _to_float(effective.get("p_fail_now", 0.0))
    raw_recover = _to_float(effective.get("p_recover_after_pullback", 0.0))
    raw_tp1 = _to_float(effective.get("p_reach_tp1", 0.0))
    raw_opposite = _to_float(effective.get("p_opposite_edge_reach", 0.0))
    raw_reentry = _to_float(effective.get("p_better_reentry_if_cut", 0.0))
    hold_scale = _to_float(profile.get("hold_scale", 1.0), 1.0)
    fail_scale = _to_float(profile.get("fail_scale", 1.0), 1.0)
    reentry_scale = _to_float(profile.get("reentry_scale", 1.0), 1.0)
    barrier_drag = _to_float(profile.get("barrier_drag", 0.0), 0.0)

    effective["p_continue_favor"] = _round6(_clamp01((raw_continue * hold_scale) - (0.03 * barrier_drag)))
    effective["p_fail_now"] = _round6(_clamp01((raw_fail * fail_scale) + (0.05 * barrier_drag)))
    effective["p_recover_after_pullback"] = _round6(_clamp01((raw_recover * hold_scale) - (0.02 * barrier_drag)))
    effective["p_reach_tp1"] = _round6(_clamp01((raw_tp1 * hold_scale) - (0.02 * barrier_drag)))
    effective["p_opposite_edge_reach"] = _round6(_clamp01((raw_opposite * hold_scale) - (0.01 * barrier_drag)))
    effective["p_better_reentry_if_cut"] = _round6(_clamp01((raw_reentry * reentry_scale) + (0.03 * barrier_drag)))

    meta = dict(effective.get("metadata", {}) or {})
    meta["effective_overlay_v1"] = {
        "layer": "Forecast",
        "branch": "trade_management",
        "mode": str(profile.get("mode", "") or ""),
        "overlay_strength": str(profile.get("consumer_hint_strength", "") or ""),
        "hold_scale": _round_gap(hold_scale),
        "fail_scale": _round_gap(fail_scale),
        "reentry_scale": _round_gap(reentry_scale),
        "barrier_drag": _round_gap(barrier_drag),
    }
    effective["metadata"] = meta

    deltas = {
        "p_continue_favor_delta": _round_gap(_to_float(effective.get("p_continue_favor", 0.0)) - raw_continue),
        "p_fail_now_delta": _round_gap(_to_float(effective.get("p_fail_now", 0.0)) - raw_fail),
        "p_recover_after_pullback_delta": _round_gap(
            _to_float(effective.get("p_recover_after_pullback", 0.0)) - raw_recover
        ),
        "p_reach_tp1_delta": _round_gap(_to_float(effective.get("p_reach_tp1", 0.0)) - raw_tp1),
        "p_opposite_edge_reach_delta": _round_gap(
            _to_float(effective.get("p_opposite_edge_reach", 0.0)) - raw_opposite
        ),
        "p_better_reentry_if_cut_delta": _round_gap(
            _to_float(effective.get("p_better_reentry_if_cut", 0.0)) - raw_reentry
        ),
    }
    return effective, deltas


def _apply_gap_overlay(gap_payload: dict, profile: dict[str, object]) -> tuple[dict, dict]:
    effective = _coerce_layer_mode_payload(gap_payload)
    raw_wait = _to_float(effective.get("wait_confirm_gap", 0.0))
    raw_hold = _to_float(effective.get("hold_exit_gap", 0.0))
    raw_same = _to_float(effective.get("same_side_flip_gap", 0.0))
    raw_tension = _to_float(effective.get("belief_barrier_tension_gap", 0.0))
    confirm_scale = _to_float(profile.get("confirm_scale", 1.0), 1.0)
    hold_scale = _to_float(profile.get("hold_scale", 1.0), 1.0)
    reentry_scale = _to_float(profile.get("reentry_scale", 1.0), 1.0)
    barrier_drag = _to_float(profile.get("barrier_drag", 0.0), 0.0)

    effective["wait_confirm_gap"] = _round_gap(raw_wait * confirm_scale)
    effective["hold_exit_gap"] = _round_gap(raw_hold * hold_scale)
    effective["same_side_flip_gap"] = _round_gap(raw_same * reentry_scale)
    effective["belief_barrier_tension_gap"] = _round_gap(raw_tension - (0.08 * barrier_drag))

    meta = dict(effective.get("metadata", {}) or {})
    execution_gap_support = dict(meta.get("execution_gap_support_v1", {}) or {})
    execution_gap_support["effective_overlay_mode"] = str(profile.get("mode", "") or "")
    meta["execution_gap_support_v1"] = execution_gap_support
    meta["effective_overlay_v1"] = {
        "layer": "Forecast",
        "branch": "gap_metrics",
        "mode": str(profile.get("mode", "") or ""),
        "overlay_strength": str(profile.get("consumer_hint_strength", "") or ""),
        "confirm_scale": _round_gap(confirm_scale),
        "hold_scale": _round_gap(hold_scale),
        "reentry_scale": _round_gap(reentry_scale),
        "barrier_drag": _round_gap(barrier_drag),
    }
    effective["metadata"] = meta

    deltas = {
        "wait_confirm_gap_delta": _round_gap(_to_float(effective.get("wait_confirm_gap", 0.0)) - raw_wait),
        "hold_exit_gap_delta": _round_gap(_to_float(effective.get("hold_exit_gap", 0.0)) - raw_hold),
        "same_side_flip_gap_delta": _round_gap(_to_float(effective.get("same_side_flip_gap", 0.0)) - raw_same),
        "belief_barrier_tension_gap_delta": _round_gap(
            _to_float(effective.get("belief_barrier_tension_gap", 0.0)) - raw_tension
        ),
    }
    return effective, deltas


def _current_layer_mode_defaults(mode_overrides: dict | None = None) -> dict[str, str]:
    defaults = {
        str(row.get("layer", "") or ""): str(row.get("current_effective_default_mode", "shadow") or "shadow")
        for row in LAYER_MODE_DEFAULT_POLICY_V1.get("policy_rows", [])
        if str(row.get("layer", "") or "")
    }
    valid_modes = set(LAYER_MODE_MODE_CONTRACT_V1.get("mode_order", []))
    for layer, mode in dict(mode_overrides or {}).items():
        layer_name = str(layer or "")
        mode_name = str(mode or "").strip().lower()
        if layer_name in defaults and mode_name in valid_modes:
            defaults[layer_name] = mode_name
    return defaults


def build_layer_mode_effective_metadata(raw_metadata: dict | None, mode_overrides: dict | None = None) -> dict:
    raw = dict(raw_metadata or {})
    current_modes = _current_layer_mode_defaults(mode_overrides)
    payload: dict[str, object] = {}
    trace_rows: list[dict[str, object]] = []

    for row in LAYER_MODE_DUAL_WRITE_CONTRACT_V1.get("layer_rows", []):
        layer = str(row.get("layer", "") or "")
        raw_fields = list(row.get("raw_fields", []) or [])
        effective_fields = list(row.get("effective_fields", []) or [])
        mode = current_modes.get(layer, "shadow")

        if layer == "Forecast":
            raw_features = _coerce_layer_mode_payload(raw.get("forecast_features_v1", {}))
            raw_transition = _coerce_layer_mode_payload(raw.get("transition_forecast_v1", {}))
            raw_management = _coerce_layer_mode_payload(raw.get("trade_management_forecast_v1", {}))
            raw_gap = _coerce_layer_mode_payload(raw.get("forecast_gap_metrics_v1", {}))
            profile = _forecast_overlay_mode_profile(mode, raw_gap)
            effective_transition, transition_delta = _apply_transition_overlay(raw_transition, profile)
            effective_management, management_delta = _apply_management_overlay(raw_management, profile)
            effective_gap, gap_delta = _apply_gap_overlay(raw_gap, profile)
            all_delta_values = list(transition_delta.values()) + list(management_delta.values()) + list(gap_delta.values())
            effective_equals_raw = max((abs(_to_float(value, 0.0)) for value in all_delta_values), default=0.0) < 1e-9

            payload["forecast_effective_policy_v1"] = {
                "layer": "Forecast",
                "current_effective_mode": mode,
                "semantic_owner_contract": "forecast_branch_interpretation_only_v1",
                "forecast_freeze_phase": "FR0",
                "forecast_role_statement": (
                    "Forecast effective wrapper preserves already-built forecast branches without becoming a new "
                    "semantic owner."
                ),
                "forecast_branch_role": "effective_wrapper_only",
                "owner_boundaries_v1": {
                    "position_location_owner": False,
                    "response_event_owner": False,
                    "state_market_regime_owner": False,
                    "evidence_instant_ground_owner": False,
                    "belief_persistence_owner": False,
                    "barrier_blocking_owner": False,
                },
                "execution_side_creator_allowed": False,
                "direct_action_creator_allowed": False,
                "summary_side_metadata_allowed": False,
                "summary_mode_metadata_allowed": False,
                "policy_overlay_applied": bool(profile.get("policy_overlay_applied", False)),
                "utility_overlay_applied": bool(profile.get("utility_overlay_applied", False)),
                "effective_equals_raw": bool(effective_equals_raw),
                "raw_field_refs": list(raw_fields),
                "forecast_features_v1": raw_features,
                "transition_forecast_v1": effective_transition,
                "trade_management_forecast_v1": effective_management,
                "forecast_gap_metrics_v1": effective_gap,
                "policy_overlay_trace_v1": {
                    "layer": "Forecast",
                    "mode": mode,
                    "consumer_hint_strength": str(profile.get("consumer_hint_strength", "") or ""),
                    "dominant_execution_gap": str(profile.get("dominant_execution_gap", "") or ""),
                    "summary": str(profile.get("summary", "") or ""),
                },
                "utility_overlay_trace_v1": {
                    "applied": bool(profile.get("utility_overlay_applied", False)),
                    "wait_confirm_gap_effective": _round_gap(_to_float(effective_gap.get("wait_confirm_gap", 0.0))),
                    "hold_exit_gap_effective": _round_gap(_to_float(effective_gap.get("hold_exit_gap", 0.0))),
                    "same_side_flip_gap_effective": _round_gap(_to_float(effective_gap.get("same_side_flip_gap", 0.0))),
                    "belief_barrier_tension_gap_effective": _round_gap(
                        _to_float(effective_gap.get("belief_barrier_tension_gap", 0.0))
                    ),
                },
                "raw_effective_delta_v1": {
                    "transition_branch": transition_delta,
                    "trade_management_branch": management_delta,
                    "gap_branch": gap_delta,
                },
                "raw_effective_difference_summary_v1": {
                    "difference_detected": not bool(effective_equals_raw),
                    "dominant_delta_branch": (
                        "transition"
                        if sum(abs(_to_float(v, 0.0)) for v in transition_delta.values())
                        >= max(
                            sum(abs(_to_float(v, 0.0)) for v in management_delta.values()),
                            sum(abs(_to_float(v, 0.0)) for v in gap_delta.values()),
                        )
                        else "trade_management"
                        if sum(abs(_to_float(v, 0.0)) for v in management_delta.values())
                        >= sum(abs(_to_float(v, 0.0)) for v in gap_delta.values())
                        else "gap_metrics"
                    ),
                    "difference_reason": (
                        "raw_equivalent_shadow_overlay"
                        if effective_equals_raw
                        else "mode_weighted_forecast_assist_overlay"
                    ),
                },
            }
        elif raw_fields and effective_fields:
            payload[str(effective_fields[0])] = _coerce_layer_mode_payload(raw.get(str(raw_fields[0]), {}))

        trace_rows.append(
            {
                "layer": layer,
                "current_effective_mode": mode,
                "raw_fields": list(raw_fields),
                "effective_fields": list(effective_fields),
                "policy_overlay_applied": bool(layer == "Forecast"),
                "effective_equals_raw": bool(
                    payload.get("forecast_effective_policy_v1", {}).get("effective_equals_raw", True)
                )
                if layer == "Forecast"
                else True,
                "identity_preserved": True,
                "block_explainability_ready": True,
            }
        )

    payload["layer_mode_effective_trace_v1"] = {
        "contract_version": "layer_mode_effective_trace_v1",
        "dual_write_contract_version": LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"],
        "raw_outputs_preserved": True,
        "effective_outputs_emitted": True,
        "bridge_status": "identity_preserving_raw_equivalent",
        "explainability_goal": "preserve raw and effective payloads together so later blocks, suppressions, or assists can be explained deterministically",
        "layers": trace_rows,
    }
    return payload


def _layer_mode_influence_rows_by_layer() -> dict[str, dict]:
    return {
        str(row.get("layer", "") or ""): dict(row)
        for row in LAYER_MODE_INFLUENCE_SEMANTICS_V1.get("layer_rows", [])
        if str(row.get("layer", "") or "")
    }


def _layer_mode_application_rows_by_layer() -> dict[str, dict]:
    return {
        str(row.get("layer", "") or ""): dict(row)
        for row in LAYER_MODE_APPLICATION_CONTRACT_V1.get("layer_rows", [])
        if str(row.get("layer", "") or "")
    }


def _layer_mode_identity_guard_rows_by_layer() -> dict[str, dict]:
    return {
        str(row.get("layer", "") or ""): dict(row)
        for row in LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1.get("focus_layers", [])
        if str(row.get("layer", "") or "")
    }


def build_layer_mode_influence_metadata(mode_overrides: dict | None = None) -> dict:
    current_modes = _current_layer_mode_defaults(mode_overrides)
    influence_rows = _layer_mode_influence_rows_by_layer()
    trace_rows: list[dict[str, object]] = []

    for layer in LAYER_MODE_LAYER_INVENTORY_V1.get("layer_order", []):
        row = influence_rows.get(str(layer), {})
        mode = current_modes.get(str(layer), "shadow")
        if mode == "shadow":
            active_effects = ["metadata_log_only", "trace_only"]
            dominant_role = "metadata_only"
        else:
            active_effects = list(row.get(f"{mode}_effects", []) or [])
            dominant_role = str(row.get(f"dominant_{mode}_role", "") or "")
        trace_rows.append(
            {
                "layer": str(layer),
                "current_effective_mode": mode,
                "active_effects": active_effects,
                "dominant_role": dominant_role,
                "hard_gate_allowed": bool("hard_block" in active_effects or "execution_veto" in active_effects),
                "identity_preserved": True,
                "forbidden_even_in_enforce": list(row.get("forbidden_even_in_enforce", []) or []),
            }
        )

    return {
        "layer_mode_influence_trace_v1": {
            "contract_version": "layer_mode_influence_trace_v1",
            "influence_semantics_contract_version": LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"],
            "current_mode_source": LAYER_MODE_DEFAULT_POLICY_V1["contract_version"],
            "identity_preserved": True,
            "trace_goal": "show which execution influence types are active for each layer under the current default mode policy",
            "layers": trace_rows,
        }
    }


def build_layer_mode_application_metadata(mode_overrides: dict | None = None) -> dict:
    current_modes = _current_layer_mode_defaults(mode_overrides)
    application_rows = _layer_mode_application_rows_by_layer()
    trace_rows: list[dict[str, object]] = []

    for layer in LAYER_MODE_LAYER_INVENTORY_V1.get("layer_order", []):
        row = application_rows.get(str(layer), {})
        mode = current_modes.get(str(layer), "shadow")
        first_active = str(row.get("first_semantically_active_mode", "assist") or "assist")
        if mode == "shadow":
            active_application = ["metadata_log_only", "trace_only"]
            application_state = "standby"
        elif mode == "assist":
            active_application = list(row.get("assist_application", []) or [])
            application_state = "assist_active"
        else:
            active_application = list(row.get("enforce_application", []) or [])
            application_state = "enforce_active"
        trace_rows.append(
            {
                "layer": str(layer),
                "current_effective_mode": mode,
                "first_semantically_active_mode": first_active,
                "application_state": application_state,
                "active_application": active_application,
                "policy_summary": str(row.get("policy_summary", "") or ""),
                "identity_guard_fields": list(row.get("identity_guard_fields", []) or []),
                "forbidden_application": list(row.get("forbidden_application", []) or []),
            }
        )

    return {
        "layer_mode_application_trace_v1": {
            "contract_version": "layer_mode_application_trace_v1",
            "application_contract_version": LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"],
            "current_mode_source": LAYER_MODE_DEFAULT_POLICY_V1["contract_version"],
            "trace_goal": "show how each layer is currently applied under the default mode rollout, separated from influence semantics and raw/effective dual-write",
            "layers": trace_rows,
        }
    }


def build_layer_mode_identity_guard_metadata(mode_overrides: dict | None = None) -> dict:
    current_modes = _current_layer_mode_defaults(mode_overrides)
    guard_rows = _layer_mode_identity_guard_rows_by_layer()
    trace_rows: list[dict[str, object]] = []

    for layer in ["Belief", "Barrier", "Forecast"]:
        row = guard_rows.get(layer, {})
        trace_rows.append(
            {
                "layer": layer,
                "current_effective_mode": current_modes.get(layer, "shadow"),
                "guard_active": bool(row.get("guard_active", False)),
                "protected_fields": list(row.get("protected_fields", []) or []),
                "allowed_adjustments": list(row.get("allowed_adjustments", []) or []),
                "forbidden_adjustments": list(row.get("forbidden_adjustments", []) or []),
                "identity_preserved": True,
                "routing_policy_contract_ref": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["routing_policy_contract_ref"],
            }
        )

    return {
        "layer_mode_identity_guard_trace_v1": {
            "contract_version": "layer_mode_identity_guard_trace_v1",
            "identity_guard_contract_version": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"],
            "routing_policy_contract_ref": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["routing_policy_contract_ref"],
            "confidence_semantics_contract_ref": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["confidence_semantics_contract_ref"],
            "trace_goal": "show which non-identity layers are under always-on identity guard and what they are still allowed to adjust",
            "layers": trace_rows,
        }
    }


def build_layer_mode_policy_overlay_metadata(mode_overrides: dict | None = None) -> dict:
    current_modes = _current_layer_mode_defaults(mode_overrides)
    influence_rows = _layer_mode_influence_rows_by_layer()
    application_rows = _layer_mode_application_rows_by_layer()
    guard_rows = _layer_mode_identity_guard_rows_by_layer()
    layer_modes: list[dict[str, object]] = []
    effective_influences: list[dict[str, object]] = []
    mode_decision_rows: list[dict[str, object]] = []

    for layer in LAYER_MODE_LAYER_INVENTORY_V1.get("layer_order", []):
        layer_name = str(layer)
        mode = current_modes.get(layer_name, "shadow")
        influence_row = influence_rows.get(layer_name, {})
        application_row = application_rows.get(layer_name, {})
        guard_row = guard_rows.get(layer_name, {})
        if mode == "shadow":
            active_effects = ["metadata_log_only", "trace_only"]
            active_application = ["metadata_log_only", "trace_only"]
        else:
            active_effects = list(influence_row.get(f"{mode}_effects", []) or [])
            active_application = list(application_row.get(f"{mode}_application", []) or [])
        layer_modes.append(
            {
                "layer": layer_name,
                "mode": mode,
            }
        )
        effective_influences.append(
            {
                "layer": layer_name,
                "mode": mode,
                "active_effects": active_effects,
                "active_application": active_application,
                "identity_guard_active": bool(guard_row.get("guard_active", False)),
            }
        )
        mode_decision_rows.append(
            {
                "layer": layer_name,
                "mode": mode,
                "bridge_only": True,
                "identity_preserved": True,
                "protected_fields": list(guard_row.get("protected_fields", []) or []),
                "allowed_adjustments": list(guard_row.get("allowed_adjustments", []) or []),
                "active_effects": active_effects,
                "active_application": active_application,
            }
        )

    return {
        "layer_mode_policy_v1": {
            "contract_version": "layer_mode_policy_v1",
            "policy_overlay_output_contract_version": LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"],
            "mode_source_contract_version": LAYER_MODE_DEFAULT_POLICY_V1["contract_version"],
            "identity_guard_contract_version": LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"],
            "overlay_execution_state": "bridge_ready_no_runtime_delta",
            "identity_preserved": True,
            "layer_modes": layer_modes,
            "effective_influences": effective_influences,
            "suppressed_reasons": [],
            "confidence_adjustments": [],
            "hard_blocks": [],
            "mode_decision_trace": {
                "trace_version": "layer_mode_mode_decision_trace_v1",
                "mode_source_contract_version": LAYER_MODE_DEFAULT_POLICY_V1["contract_version"],
                "bridge_status": "policy_overlay_ready_no_runtime_delta",
                "identity_preserved": True,
                "layers": mode_decision_rows,
            },
        }
    }


def build_layer_mode_logging_replay_metadata(raw_metadata: dict | None = None, mode_overrides: dict | None = None) -> dict:
    raw = dict(raw_metadata or {})
    policy = _coerce_layer_mode_payload(raw.get("layer_mode_policy_v1", {}))
    if not policy:
        policy = build_layer_mode_policy_overlay_metadata(mode_overrides=mode_overrides).get("layer_mode_policy_v1", {})
    configured_modes = copy.deepcopy(policy.get("layer_modes", [])) if isinstance(policy.get("layer_modes"), list) else []
    effective_influences = (
        copy.deepcopy(policy.get("effective_influences", []))
        if isinstance(policy.get("effective_influences"), list)
        else []
    )
    raw_result_fields = []
    effective_result_fields = []
    for row in LAYER_MODE_DUAL_WRITE_CONTRACT_V1.get("layer_rows", []):
        raw_result_fields.append(
            {
                "layer": str(row.get("layer", "") or ""),
                "fields": list(row.get("raw_fields", []) or []),
            }
        )
        effective_result_fields.append(
            {
                "layer": str(row.get("layer", "") or ""),
                "fields": list(row.get("effective_fields", []) or []),
            }
        )
    block_reason = str(raw.get("consumer_block_reason", "") or "")
    block_kind = str(raw.get("consumer_block_kind", "") or "")
    block_source_layer = str(raw.get("consumer_block_source_layer", "") or "")
    consumer_action = str(raw.get("consumer_effective_action", "") or "")
    consumer_guard_result = str(raw.get("consumer_guard_result", "") or "")
    return {
        "layer_mode_logging_replay_v1": {
            "contract_version": "layer_mode_logging_replay_v1",
            "logging_replay_contract_version": LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"],
            "policy_overlay_output_contract_version": LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"],
            "configured_modes": configured_modes,
            "raw_result_fields": raw_result_fields,
            "effective_result_fields": effective_result_fields,
            "applied_adjustments": effective_influences,
            "block_suppress_reasons": {
                "policy_suppressed_reasons": copy.deepcopy(policy.get("suppressed_reasons", []))
                if isinstance(policy.get("suppressed_reasons"), list)
                else [],
                "policy_hard_blocks": copy.deepcopy(policy.get("hard_blocks", []))
                if isinstance(policy.get("hard_blocks"), list)
                else [],
                "consumer_block_reason": block_reason,
                "consumer_block_kind": block_kind,
                "consumer_block_source_layer": block_source_layer,
            },
            "final_consumer_action": {
                "consumer_effective_action": consumer_action,
                "consumer_guard_result": consumer_guard_result,
            },
            "replay_ready": True,
        }
    }


def _default_layer_mode_test_observe_confirm() -> dict[str, object]:
    return {
        "state": "CONFIRM",
        "action": "BUY",
        "side": "BUY",
        "confidence": 0.72,
        "reason": "synthetic_confirm",
        "archetype_id": "lower_hold_buy",
        "invalidation_id": "lower_support_fail",
        "management_profile_id": "support_hold_profile",
    }


def _default_layer_mode_test_raw_metadata() -> dict[str, object]:
    return {
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


def build_layer_mode_test_projection(
    mode_overrides: dict | None = None,
    observe_confirm: dict | None = None,
    raw_metadata: dict | None = None,
    force_hard_block_layers: list[str] | None = None,
) -> dict:
    source_observe_confirm = _coerce_layer_mode_payload(observe_confirm or _default_layer_mode_test_observe_confirm())
    effective_observe_confirm = copy.deepcopy(source_observe_confirm)
    resolved_modes = _current_layer_mode_defaults(mode_overrides)
    overlay_payload = build_layer_mode_policy_overlay_metadata(mode_overrides=mode_overrides).get("layer_mode_policy_v1", {})
    confidence_adjustments: list[dict[str, object]] = []
    priority_adjustments: list[dict[str, object]] = []
    suppressed_reasons: list[dict[str, object]] = []
    hard_blocks: list[dict[str, object]] = []
    reason_annotations: list[dict[str, object]] = []
    projected_consumer_action = str(source_observe_confirm.get("action", "") or "").strip().upper()
    if projected_consumer_action not in {"BUY", "SELL"}:
        projected_consumer_action = "NONE"
    projected_consumer_guard_result = "PASS" if projected_consumer_action in {"BUY", "SELL"} else "SEMANTIC_NON_ACTION"
    block_layers = {str(layer or "") for layer in list(force_hard_block_layers or []) if str(layer or "")}

    for row in overlay_payload.get("effective_influences", []):
        layer = str(row.get("layer", "") or "")
        mode = str(resolved_modes.get(layer, "shadow") or "shadow")
        active_effects = list(row.get("active_effects", []) or [])
        if mode == "shadow":
            continue
        if "confidence_modulation" in active_effects:
            delta = 0.05 if mode == "assist" else -0.08
            current_confidence = float(effective_observe_confirm.get("confidence", 0.0) or 0.0)
            next_confidence = max(0.0, min(1.0, round(current_confidence + delta, 4)))
            effective_observe_confirm["confidence"] = next_confidence
            confidence_adjustments.append(
                {
                    "layer": layer,
                    "mode": mode,
                    "delta": delta,
                    "resulting_confidence": next_confidence,
                }
            )
        if mode == "assist" and "priority_boost" in active_effects:
            priority_adjustments.append(
                {
                    "layer": layer,
                    "mode": mode,
                    "effect": "priority_boost",
                }
            )
        if "reason_annotation" in active_effects:
            reason_annotations.append(
                {
                    "layer": layer,
                    "mode": mode,
                    "effect": "reason_annotation",
                }
            )
        if mode == "enforce" and layer in block_layers and "hard_block" in active_effects:
            hard_blocks.append(
                {
                    "layer": layer,
                    "mode": mode,
                    "effect": "hard_block",
                }
            )
            projected_consumer_action = "NONE"
            projected_consumer_guard_result = "EXECUTION_BLOCK"
            continue
        if (
            mode == "enforce"
            and layer in {"Barrier", "Forecast"}
            and "confirm_to_observe_suppression" in active_effects
            and str(effective_observe_confirm.get("state", "") or "") == "CONFIRM"
            and str(effective_observe_confirm.get("action", "") or "").upper() in {"BUY", "SELL"}
            and projected_consumer_action != "NONE"
        ):
            effective_observe_confirm["state"] = "OBSERVE"
            effective_observe_confirm["action"] = "WAIT"
            suppressed_reasons.append(
                {
                    "layer": layer,
                    "mode": mode,
                    "effect": "confirm_to_observe_suppression",
                }
            )
            projected_consumer_action = "NONE"
            projected_consumer_guard_result = "SEMANTIC_NON_ACTION"

    identity_preserved = (
        str(source_observe_confirm.get("archetype_id", "") or "") == str(effective_observe_confirm.get("archetype_id", "") or "")
        and str(source_observe_confirm.get("side", "") or "") == str(effective_observe_confirm.get("side", "") or "")
    )
    raw_effective_bundle = build_layer_mode_effective_metadata(
        raw_metadata or _default_layer_mode_test_raw_metadata(),
        mode_overrides=mode_overrides,
    )
    logging_replay = build_layer_mode_logging_replay_metadata(
        {
            "layer_mode_policy_v1": overlay_payload,
            "consumer_effective_action": projected_consumer_action,
            "consumer_guard_result": projected_consumer_guard_result,
            "consumer_block_reason": hard_blocks[0]["effect"] if hard_blocks else "",
            "consumer_block_kind": "execution_block" if hard_blocks else "",
            "consumer_block_source_layer": hard_blocks[0]["layer"] if hard_blocks else "",
        },
        mode_overrides=mode_overrides,
    )
    return {
        "contract_version": "layer_mode_test_projection_v1",
        "test_contract_version": LAYER_MODE_TEST_CONTRACT_V1["contract_version"],
        "resolved_modes": resolved_modes,
        "source_observe_confirm": source_observe_confirm,
        "effective_observe_confirm": effective_observe_confirm,
        "projected_consumer_action": projected_consumer_action,
        "projected_consumer_guard_result": projected_consumer_guard_result,
        "confidence_adjustments": confidence_adjustments,
        "priority_adjustments": priority_adjustments,
        "reason_annotations": reason_annotations,
        "suppressed_reasons": suppressed_reasons,
        "hard_blocks": hard_blocks,
        "identity_preserved": identity_preserved,
        "raw_effective_bundle": raw_effective_bundle,
        "policy_overlay": overlay_payload,
        "logging_replay": logging_replay.get("layer_mode_logging_replay_v1", {}),
    }


def _layer_mode_metadata(container) -> dict:
    if hasattr(container, "metadata"):
        metadata = getattr(container, "metadata", {})
        if isinstance(metadata, dict):
            return metadata
    if isinstance(container, dict):
        return container
    return {}


def resolve_layer_mode_handoff_payload(container) -> dict:
    metadata = _layer_mode_metadata(container)
    policy_overlay = _coerce_layer_mode_payload(metadata.get("layer_mode_policy_v1", {}))
    logging_replay = _coerce_layer_mode_payload(metadata.get("layer_mode_logging_replay_v1", {}))
    raw_semantic_fields = []
    effective_semantic_fields = []
    dual_write_ready = True

    for row in LAYER_MODE_DUAL_WRITE_CONTRACT_V1.get("layer_rows", []):
        layer = str(row.get("layer", "") or "")
        raw_fields = list(row.get("raw_fields", []) or [])
        effective_fields = list(row.get("effective_fields", []) or [])
        raw_present = all(field in metadata for field in raw_fields)
        effective_present = all(field in metadata for field in effective_fields)
        dual_write_ready = dual_write_ready and raw_present and effective_present
        raw_semantic_fields.append(
            {
                "layer": layer,
                "fields": raw_fields,
                "present": raw_present,
            }
        )
        effective_semantic_fields.append(
            {
                "layer": layer,
                "fields": effective_fields,
                "present": effective_present,
            }
        )

    return {
        "contract_version": LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"],
        "all_semantic_layers_compute": True,
        "mode_controls_influence_only": True,
        "dual_write_ready": dual_write_ready,
        "policy_overlay_ready": bool(policy_overlay),
        "logging_replay_ready": bool(logging_replay),
        "policy_overlay_position": LAYER_MODE_FREEZE_HANDOFF_V1["policy_overlay_position"],
        "consumer_policy_bridge": {
            "input_field": LAYER_MODE_FREEZE_HANDOFF_V1["consumer_policy_input_field"],
            "overlay_ready": bool(policy_overlay),
            "identity_preserved": bool(policy_overlay.get("identity_preserved", False)),
        },
        "raw_semantic_fields": raw_semantic_fields,
        "effective_semantic_fields": effective_semantic_fields,
        "policy_overlay": policy_overlay,
        "logging_replay": logging_replay,
        "energy_future_role": copy.deepcopy(LAYER_MODE_FREEZE_HANDOFF_V1["energy_future_role"]),
    }


def layer_mode_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_MODE_CONTRACT_V1["documentation_path"]


def layer_mode_layer_inventory_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_LAYER_INVENTORY_V1["documentation_path"]


def layer_mode_default_policy_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_DEFAULT_POLICY_V1["documentation_path"]


def layer_mode_dual_write_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_DUAL_WRITE_CONTRACT_V1["documentation_path"]


def layer_mode_influence_semantics_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_INFLUENCE_SEMANTICS_V1["documentation_path"]


def layer_mode_application_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_APPLICATION_CONTRACT_V1["documentation_path"]


def layer_mode_identity_guard_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["documentation_path"]


def layer_mode_policy_overlay_output_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["documentation_path"]


def layer_mode_logging_replay_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["documentation_path"]


def layer_mode_test_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_TEST_CONTRACT_V1["documentation_path"]


def layer_mode_freeze_handoff_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_FREEZE_HANDOFF_V1["documentation_path"]


def layer_mode_scope_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / LAYER_MODE_SCOPE_CONTRACT_V1["documentation_path"]
