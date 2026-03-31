from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


OBSERVE_CONFIRM_INPUT_CONTRACT_V2 = {
    "contract_version": "observe_confirm_input_contract_v2",
    "scope": "canonical_semantic_inputs_only",
    "router_file": "backend/trading/engine/core/observe_confirm_router.py",
    "semantic_input_fields": [
        {
            "field": "position_snapshot_v2",
            "type": "PositionSnapshot",
            "role": "position structure and normalized zone interpretation",
        },
        {
            "field": "response_vector_v2",
            "type": "ResponseVectorV2",
            "role": "canonical response axes only",
        },
        {
            "field": "state_vector_v2",
            "type": "StateVectorV2",
            "role": "regime and policy-adjusted state only",
        },
        {
            "field": "evidence_vector_v1",
            "type": "EvidenceVector",
            "role": "directional evidence strength",
        },
        {
            "field": "belief_state_v1",
            "type": "BeliefState",
            "role": "persistence and transition-age belief context",
        },
        {
            "field": "barrier_state_v1",
            "type": "BarrierState",
            "role": "execution resistance and friction constraints",
        },
    ],
    "forecast_input_fields": [
        {
            "field": "transition_forecast_v1",
            "type": "TransitionForecast",
            "role": "transition scenario scoring only",
        },
        {
            "field": "trade_management_forecast_v1",
            "type": "TradeManagementForecast",
            "role": "management scenario scoring only",
        },
        {
            "field": "forecast_gap_metrics_v1",
            "type": "dict",
            "role": "forecast competition and separation diagnostics",
        },
    ],
    "forbidden_direct_inputs": [
        "position_vector_v2",
        "response_vector_v1",
        "state_vector_v1",
        "response_raw_snapshot_v1",
        "state_raw_snapshot_v1",
        "energy_snapshot_v1",
        "raw_detector_score",
        "legacy_rule_branch",
    ],
    "forbidden_practices": [
        "raw_detector_direct_read",
        "legacy_rule_branch_read",
        "consumer_side_reinterpretation",
    ],
    "input_principles": [
        "router reads canonical semantic bundle only",
        "router may not read raw detector scores directly",
        "router may not branch on legacy setup or consumer execution labels",
        "forecast may modulate routing confidence but does not replace semantic identity",
    ],
    "runtime_log_fields": [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
        "observe_confirm_input_contract_v2",
    ],
    "documentation_path": "docs/observe_confirm_input_contract.md",
}


OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2 = {
    "contract_version": "observe_confirm_output_contract_v2",
    "bundle_type": "ObserveConfirmSnapshot",
    "canonical_output_field": "observe_confirm_v2",
    "compatibility_output_field_v1": "observe_confirm_v1",
    "required_fields": [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "metadata",
    ],
    "field_semantics": {
        "state": "routing lifecycle state only; not setup naming or execution command",
        "action": "routing action suggestion only; WAIT may still carry a directional side and NONE reserves no-trade output",
        "side": "routing side suggestion aligned with action, except directional WAIT observes which may carry BUY or SELL side",
        "confidence": "routing readiness score, not broker execution permission by itself",
        "reason": "primary semantic routing explanation",
        "archetype_id": "canonical trade-archetype entry identity",
        "invalidation_id": "canonical invalidation identity aligned to archetype_id; not free-text reason",
        "management_profile_id": "canonical management profile identity aligned to archetype_id; official consumer/exit handoff field",
    },
    "state_values": [
        "OBSERVE",
        "CONFIRM",
        "CONFLICT_OBSERVE",
        "NO_TRADE",
        "INVALIDATED",
    ],
    "action_values": [
        "WAIT",
        "BUY",
        "SELL",
        "NONE",
    ],
    "side_values": [
        "BUY",
        "SELL",
        "",
    ],
    "metadata_contract": {
        "required_fields": [
            "raw_contributions",
            "effective_contributions",
            "winning_evidence",
            "blocked_reason",
        ],
        "field_semantics": {
            "raw_contributions": "pre-normalization signal contributions when available",
            "effective_contributions": "post-policy or post-barrier routing contributions when available",
            "winning_evidence": "evidence items that explain the selected routing outcome",
            "blocked_reason": "non-empty only when the router suppresses a directional confirm into wait or no-trade",
        },
    },
    "deferred_value_taxonomies": [],
    "state_semantics_contract_v2": "observe_confirm_state_semantics_v2",
    "action_side_semantics_contract_v2": "observe_confirm_action_side_semantics_v2",
    "archetype_taxonomy_contract_v2": "observe_confirm_archetype_taxonomy_v2",
    "invalidation_taxonomy_contract_v2": "observe_confirm_invalidation_taxonomy_v2",
    "management_profile_taxonomy_contract_v2": "observe_confirm_management_profile_taxonomy_v2",
    "routing_policy_contract_v2": "observe_confirm_routing_policy_v2",
    "confidence_semantics_contract_v2": "observe_confirm_confidence_semantics_v2",
    "migration_dual_write_contract_v1": "observe_confirm_migration_dual_write_v1",
    "runtime_log_fields": [
        "observe_confirm_v1",
        "observe_confirm_v2",
        "observe_confirm_output_contract_v2",
        "observe_confirm_migration_dual_write_v1",
    ],
    "documentation_path": "docs/observe_confirm_output_contract.md",
}


OBSERVE_CONFIRM_STATE_SEMANTICS_V2 = {
    "contract_version": "observe_confirm_state_semantics_v2",
    "state_field": "state",
    "scope": "lifecycle_only",
    "allowed_values": [
        {
            "value": "OBSERVE",
            "meaning": "candidate archetype is present only as a watch state; no execution confirmation is granted",
        },
        {
            "value": "CONFIRM",
            "meaning": "candidate archetype is semantically confirmed and may be consumed by downstream setup naming",
        },
        {
            "value": "CONFLICT_OBSERVE",
            "meaning": "conflicting semantic evidence exists, so the router stays in observe mode instead of confirming",
        },
        {
            "value": "NO_TRADE",
            "meaning": "router intentionally exposes no tradeable archetype at the current bar",
        },
        {
            "value": "INVALIDATED",
            "meaning": "previous candidate archetype is explicitly invalidated by current semantic structure",
        },
    ],
    "state_principles": [
        "state is lifecycle only",
        "pattern or setup identity does not live in state",
        "legacy pattern-shaped state ids move to archetype_id",
        "consumer setup naming must read archetype_id rather than reinterpret lifecycle state",
    ],
    "legacy_transition_rule": {
        "legacy_pattern_state_field": "archetype_id",
        "compatibility_shadow_field": "shadow_state_v1",
        "compatibility_shadow_rule": "when archetype_id is present, compatibility shadow fields mirror archetype identity instead of lifecycle state",
    },
    "documentation_path": "docs/observe_confirm_state_semantics.md",
}


OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2 = {
    "contract_version": "observe_confirm_archetype_taxonomy_v2",
    "field": "archetype_id",
    "principle": "archetype is entry identity",
    "core_set": [
        {
            "archetype_id": "upper_reject_sell",
            "side": "SELL",
            "family": "upper_reversal",
            "meaning": "upper-side rejection or failed upper extension resolved as sell entry identity",
        },
        {
            "archetype_id": "upper_break_buy",
            "side": "BUY",
            "family": "upper_continuation",
            "meaning": "upper-side breakout or hold-above continuation resolved as buy entry identity",
        },
        {
            "archetype_id": "lower_hold_buy",
            "side": "BUY",
            "family": "lower_reversal",
            "meaning": "lower-side support hold or rebound resolved as buy entry identity",
        },
        {
            "archetype_id": "lower_break_sell",
            "side": "SELL",
            "family": "lower_continuation",
            "meaning": "lower-side support failure or breakdown resolved as sell entry identity",
        },
        {
            "archetype_id": "mid_reclaim_buy",
            "side": "BUY",
            "family": "middle_reclaim",
            "meaning": "middle reclaim or trend pullback buy resolved as buy entry identity",
        },
        {
            "archetype_id": "mid_lose_sell",
            "side": "SELL",
            "family": "middle_loss",
            "meaning": "middle lose or trend pullback sell resolved as sell entry identity",
        },
    ],
    "router_rules": [
        "observe and confirm may share the same archetype_id",
        "neutral or unresolved observe states may emit empty archetype_id",
        "conflict observe without a stable entry identity emits empty archetype_id",
        "setup naming may further specialize canonical archetype_id using market mode, reason, and context",
    ],
    "documentation_path": "docs/observe_confirm_archetype_taxonomy.md",
}


OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2 = {
    "contract_version": "observe_confirm_invalidation_taxonomy_v2",
    "field": "invalidation_id",
    "principle": "invalidation is canonical failure identity, not free-text reason",
    "canonical_mapping": [
        {
            "archetype_id": "upper_reject_sell",
            "invalidation_id": "upper_break_reclaim",
            "meaning": "upper rejection sell is invalidated when price reclaims and holds the upper break structure",
        },
        {
            "archetype_id": "upper_break_buy",
            "invalidation_id": "breakout_failure",
            "meaning": "upper breakout buy is invalidated when breakout continuation fails and falls back into the prior structure",
        },
        {
            "archetype_id": "lower_hold_buy",
            "invalidation_id": "lower_support_fail",
            "meaning": "lower hold buy is invalidated when lower support fails instead of holding or rebounding",
        },
        {
            "archetype_id": "lower_break_sell",
            "invalidation_id": "breakdown_failure",
            "meaning": "lower breakdown sell is invalidated when breakdown continuation fails and price reclaims the broken support",
        },
        {
            "archetype_id": "mid_reclaim_buy",
            "invalidation_id": "mid_relose",
            "meaning": "mid reclaim buy is invalidated when the reclaimed middle is lost again",
        },
        {
            "archetype_id": "mid_lose_sell",
            "invalidation_id": "mid_reclaim",
            "meaning": "mid lose sell is invalidated when the middle is reclaimed against the sell thesis",
        },
    ],
    "router_rules": [
        "stable archetype_id outputs should emit the matching canonical invalidation_id",
        "observe and confirm may share the same invalidation_id when archetype_id is the same",
        "neutral or unresolved observe states may emit empty invalidation_id only when archetype_id is empty",
        "invalidation_id is canonical contract data and must not be replaced by free-text reason strings",
    ],
    "documentation_path": "docs/observe_confirm_invalidation_taxonomy.md",
}


OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2 = {
    "contract_version": "observe_confirm_management_profile_taxonomy_v2",
    "field": "management_profile_id",
    "principle": "management profile is canonical post-entry handling identity, not entry archetype itself",
    "canonical_mapping": [
        {
            "archetype_id": "upper_reject_sell",
            "management_profile_id": "reversal_profile",
            "meaning": "manage a rejection/reversal entry with reclaim-failure and opposite-edge style handling",
        },
        {
            "archetype_id": "upper_break_buy",
            "management_profile_id": "breakout_hold_profile",
            "meaning": "manage continuation or breakout buy entries with hold-until-breakout-failure behavior",
        },
        {
            "archetype_id": "lower_hold_buy",
            "management_profile_id": "support_hold_profile",
            "meaning": "manage lower support hold buys with support-invalidation aware holding behavior",
        },
        {
            "archetype_id": "lower_break_sell",
            "management_profile_id": "breakdown_hold_profile",
            "meaning": "manage continuation or breakdown sell entries with hold-until-breakdown-failure behavior",
        },
        {
            "archetype_id": "mid_reclaim_buy",
            "management_profile_id": "mid_reclaim_fast_exit_profile",
            "meaning": "manage middle reclaim buys with fast exit on middle reloss or reclaim failure",
        },
        {
            "archetype_id": "mid_lose_sell",
            "management_profile_id": "mid_lose_fast_exit_profile",
            "meaning": "manage middle lose sells with fast exit on middle reclaim against the sell thesis",
        },
    ],
    "router_rules": [
        "stable archetype_id outputs should emit the matching canonical management_profile_id",
        "management_profile_id is the official consumer and exit handoff field",
        "observe and confirm may share the same management_profile_id when archetype_id is the same",
        "neutral or unresolved observe states may emit empty management_profile_id only when archetype_id is empty",
    ],
    "documentation_path": "docs/observe_confirm_management_profile_taxonomy.md",
}


OBSERVE_CONFIRM_ROUTING_POLICY_V2 = {
    "contract_version": "observe_confirm_routing_policy_v2",
    "objective": "Freeze which semantic layers may create archetype identity, which layers may filter or suppress, and which layers may only modulate confidence.",
    "layer_roles": {
        "position_response": {
            "inputs": ["position_snapshot_v2", "response_vector_v2"],
            "role": "archetype_candidate_generation",
            "allowed_outputs": ["archetype_id", "side"],
            "forbidden_outputs": ["setup_id", "management_profile_redefinition", "execution_guard"],
        },
        "state": {
            "inputs": ["state_vector_v2"],
            "role": "regime_filter",
            "allowed_outputs": ["state", "action"],
            "forbidden_outputs": ["archetype_id_redefinition"],
        },
        "evidence": {
            "inputs": ["evidence_vector_v1"],
            "role": "setup_strength",
            "allowed_outputs": ["confidence", "action"],
            "forbidden_outputs": ["archetype_id_redefinition"],
        },
        "belief": {
            "inputs": ["belief_state_v1"],
            "role": "persistence_bias",
            "allowed_outputs": ["confidence", "action"],
            "forbidden_outputs": ["archetype_id_redefinition"],
        },
        "barrier": {
            "inputs": ["barrier_state_v1"],
            "role": "action_suppression",
            "allowed_outputs": ["action", "metadata.blocked_reason", "confidence"],
            "forbidden_outputs": ["archetype_id_redefinition", "side_flip"],
        },
        "forecast": {
            "inputs": [
                "transition_forecast_v1",
                "trade_management_forecast_v1",
                "forecast_gap_metrics_v1",
            ],
            "role": "confidence_modulation_and_confirm_wait_split_only",
            "allowed_outputs": ["confidence", "action", "metadata.blocked_reason"],
            "forbidden_outputs": ["archetype_id_redefinition", "side_flip", "setup_naming"],
        },
    },
    "identity_guard": {
        "identity_fields": ["archetype_id", "side"],
        "identity_source_layers": ["position_snapshot_v2", "response_vector_v2"],
        "filter_only_layers": ["state_vector_v2"],
        "non_identity_layers": [
            "evidence_vector_v1",
            "belief_state_v1",
            "barrier_state_v1",
            "transition_forecast_v1",
            "trade_management_forecast_v1",
            "forecast_gap_metrics_v1",
        ],
        "forecast_identity_override_allowed": False,
        "forecast_side_override_allowed": False,
    },
    "confirm_wait_split_policy": {
        "layers": [
            "evidence_vector_v1",
            "belief_state_v1",
            "barrier_state_v1",
            "transition_forecast_v1",
            "trade_management_forecast_v1",
            "forecast_gap_metrics_v1",
        ],
        "forecast_role": "modulates confirm strength and may keep a candidate in WAIT, but may not rename the candidate archetype",
        "barrier_role": "suppresses directional action when semantic readiness is blocked",
        "branch_basis": "candidate support, opposition, and suppression thresholds derived from semantic bundle inputs",
        "forbidden_branch_basis": ["buy_force", "sell_force", "net_force", "energy_snapshot_v1"],
    },
    "implementation_bridge": {
        "semantic_readiness_bridge_v1": "internal_readiness_from_semantic_bundle",
        "legacy_energy_snapshot_dependency": False,
        "meaning": "router builds confirm readiness from the semantic bundle internally and does not read legacy energy_snapshot as a routing input",
    },
    "documentation_path": "docs/observe_confirm_routing_policy.md",
}


OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2 = {
    "contract_version": "observe_confirm_confidence_semantics_v2",
    "field": "confidence",
    "meaning": "execution_readiness_score",
    "scale": {
        "type": "bounded_float",
        "min": 0.0,
        "max": 1.0,
    },
    "principles": [
        "confidence is execution readiness, not calibrated outcome probability",
        "confidence is separate from archetype identity",
        "the same archetype_id may emit WAIT when confidence is insufficient for confirm",
        "barrier and forecast may reduce confirm readiness without renaming the archetype",
    ],
    "action_relationship": {
        "BUY_or_SELL": "higher readiness score consistent with a confirmed directional action",
        "WAIT": "candidate archetype may remain in observe state when readiness is present but not confirmable",
        "NONE": "no-trade output may carry zero or negligible readiness",
    },
    "non_meanings": [
        "not broker fill probability",
        "not pnl expectation",
        "not forecast calibration probability",
        "not a substitute for archetype_id",
    ],
    "identity_separation": {
        "archetype_id_owned_elsewhere": True,
        "forecast_identity_override_allowed": False,
        "barrier_identity_override_allowed": False,
        "wait_preserves_archetype_identity": True,
    },
    "documentation_path": "docs/observe_confirm_confidence_semantics.md",
}


OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1 = {
    "contract_version": "observe_confirm_migration_dual_write_v1",
    "canonical_output_field_v2": "observe_confirm_v2",
    "compatibility_output_field_v1": "observe_confirm_v1",
    "consumer_read_preference": ["observe_confirm_v2", "observe_confirm_v1"],
    "log_required_fields": ["observe_confirm_v1", "observe_confirm_v2"],
    "equivalence_rule": "during migration, v1 and v2 must carry semantically equivalent ObserveConfirmSnapshot payloads",
    "prs_contract_fields": {
        "canonical_field": "prs_canonical_observe_confirm_field",
        "compatibility_field": "prs_compatibility_observe_confirm_field",
    },
    "shadow_field_rule": "compatibility shadow fields may remain v1-named, but should mirror canonical v2 payload identity when available",
    "documentation_path": "docs/observe_confirm_migration_dual_write.md",
}


OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2 = {
    "contract_version": "observe_confirm_action_side_semantics_v2",
    "action_field": "action",
    "side_field": "side",
    "allowed_action_values": [
        "WAIT",
        "BUY",
        "SELL",
        "NONE",
    ],
    "allowed_side_values": [
        "BUY",
        "SELL",
        "",
    ],
    "pairing_rules": [
        {
            "action": "BUY",
            "allowed_sides": ["BUY"],
            "meaning": "confirmed buy intent must carry buy side",
        },
        {
            "action": "SELL",
            "allowed_sides": ["SELL"],
            "meaning": "confirmed sell intent must carry sell side",
        },
        {
            "action": "WAIT",
            "allowed_sides": ["BUY", "SELL", ""],
            "meaning": "wait may be neutral or directional observe",
        },
        {
            "action": "NONE",
            "allowed_sides": [""],
            "meaning": "no-trade output may not carry directional side",
        },
    ],
    "directional_observe_policy": {
        "allowed": True,
        "canonical_pair": "WAIT + BUY|SELL",
        "meaning": "router may emit directional observe without confirming execution",
        "typical_states": [
            "OBSERVE",
            "CONFLICT_OBSERVE",
        ],
    },
    "lifecycle_expectations": {
        "OBSERVE": {
            "typical_actions": ["WAIT"],
            "side_policy": "BUY|SELL|'' allowed",
        },
        "CONFIRM": {
            "typical_actions": ["BUY", "SELL"],
            "side_policy": "must align with action",
        },
        "CONFLICT_OBSERVE": {
            "typical_actions": ["WAIT"],
            "side_policy": "BUY|SELL|'' allowed",
        },
        "NO_TRADE": {
            "typical_actions": ["NONE"],
            "side_policy": "must be empty",
        },
        "INVALIDATED": {
            "typical_actions": ["WAIT", "NONE"],
            "side_policy": "directional side optional only if invalidation still points to watched side",
        },
    },
    "documentation_path": "docs/observe_confirm_action_side_semantics.md",
}


OBSERVE_CONFIRM_TEST_CONTRACT_V1 = {
    "contract_version": "observe_confirm_test_contract_v1",
    "router_test_file": "tests/unit/test_observe_confirm_router_v2.py",
    "scope": "observe_confirm_v2_router_contract",
    "principles": [
        "tests freeze semantic routing behavior, not setup naming or execution guards",
        "tests compare canonical observe_confirm_v2 semantics only",
        "tests may not rely on raw detector inputs or legacy pattern-shaped state strings",
        "tests must keep archetype identity and lifecycle state separation explicit",
    ],
    "required_scenarios": [
        {
            "id": "deterministic_replay_v2",
            "goal": "same semantic input produces the same ObserveConfirmSnapshot v2",
            "assertions": [
                "same state",
                "same action",
                "same side",
                "same confidence",
                "same archetype_id",
                "same invalidation_id",
                "same management_profile_id",
            ],
        },
        {
            "id": "semantic_bundle_only_route",
            "goal": "router works from position/response/state plus position snapshot and semantic bundle inputs without legacy energy routing input",
            "assertions": [
                "route call succeeds without raw detector payload",
                "output still uses canonical lifecycle state",
            ],
        },
        {
            "id": "state_archetype_separation",
            "goal": "state remains lifecycle-only while archetype_id carries entry identity",
            "assertions": [
                "state in OBSERVE|CONFIRM|CONFLICT_OBSERVE|NO_TRADE|INVALIDATED",
                "archetype_id never mirrors lifecycle state names",
            ],
        },
        {
            "id": "forecast_identity_guard",
            "goal": "forecast may only modulate confidence or confirm-vs-wait, never archetype identity",
            "assertions": [
                "archetype_id unchanged under hostile forecast",
                "side unchanged under hostile forecast",
                "invalidation_id unchanged under hostile forecast",
                "management_profile_id unchanged under hostile forecast",
            ],
        },
        {
            "id": "barrier_confirm_suppression",
            "goal": "barrier can demote confirm into directional observe without renaming archetype",
            "assertions": [
                "BUY_or_SELL may become WAIT",
                "CONFIRM may become OBSERVE",
                "blocked_reason populated",
                "archetype_id preserved",
            ],
        },
        {
            "id": "canonical_handoff_ids",
            "goal": "invalidation_id and management_profile_id attach deterministically from archetype_id",
            "assertions": [
                "invalidation_id follows archetype mapping",
                "management_profile_id follows archetype mapping",
            ],
        },
    ],
    "documentation_path": "docs/observe_confirm_test_contract.md",
}


OBSERVE_CONFIRM_FREEZE_HANDOFF_V1 = {
    "contract_version": "observe_confirm_freeze_handoff_v1",
    "objective": "Freeze the final ObserveConfirmSnapshot v2 handoff boundary so downstream consumers read canonical routing output only.",
    "acceptance_criteria": [
        "router may not read raw detector scores directly",
        "ObserveConfirmSnapshot v2 is fixed in contract, test, and log paths",
        "archetype_id, invalidation_id, and management_profile_id are canonical handoff ids",
        "consumer layers read observe_confirm_v2 first and use observe_confirm_v1 only as migration fallback",
    ],
    "consumer_entry_points": [
        "backend/services/setup_detector.py",
        "backend/services/entry_service.py",
    ],
    "consumer_resolution_helper": "resolve_observe_confirm_handoff_payload",
    "consumer_resolution_order": [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ],
    "consumer_rules": [
        "consumer may read only ObserveConfirmSnapshot payload fields",
        "consumer may not reinterpret semantic layer vectors directly",
        "consumer may not depend on legacy pattern-shaped state ids",
    ],
    "documentation_path": "docs/observe_confirm_freeze_handoff.md",
}


OBSERVE_CONFIRM_SCOPE_CONTRACT_V1 = {
    "contract_version": "observe_confirm_scope_v1",
    "scope": "semantic_archetype_routing_only",
    "runtime_only": True,
    "offline_only": False,
    "canonical_output_field": "observe_confirm_v2",
    "compatibility_output_field_v1": "observe_confirm_v1",
    "router_file": "backend/trading/engine/core/observe_confirm_router.py",
    "objective": "Resolve the current semantic state into an observe/confirm/action routing output without execution-layer reinterpretation.",
    "responsibilities": [
        "determine whether the current semantic state is observe, confirm, or no-trade for a candidate trade archetype",
        "emit action-side suggestion only as routing output",
        "attach semantic reason and routing metadata for downstream consumers",
    ],
    "non_responsibilities": [
        "setup naming",
        "entry guard or execution gating",
        "exit rule selection",
        "re-entry authorization",
        "order send, lot sizing, or broker execution",
    ],
    "consumer_boundary": {
        "setup_detector": "Maps or names a confirmed archetype only; it does not recompute observe/confirm state.",
        "entry_service": "Consumes routing output only for execution guards and order plumbing; it does not reinterpret semantic archetype state.",
        "exit": "Binds management behavior later from the entry archetype and management profile; it is outside observe/confirm scope.",
        "re_entry": "May require same-archetype confirmation later, but observe/confirm does not authorize re-entry by itself.",
    },
    "allowed_changes": [
        "observe_confirm_contract",
        "semantic_archetype_resolution",
        "router_normalization",
        "runtime_log_dual_write",
    ],
    "forbidden_changes": [
        "setup_detector_reinterpretation",
        "entry_guard_execution",
        "exit_rule_binding",
        "reentry_rule_binding",
        "consumer_retuning",
        "raw_detector_direct_read",
    ],
    "input_contract_v2": dict(OBSERVE_CONFIRM_INPUT_CONTRACT_V2),
    "output_contract_v2": dict(OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2),
    "state_semantics_v2": dict(OBSERVE_CONFIRM_STATE_SEMANTICS_V2),
    "archetype_taxonomy_v2": dict(OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2),
    "invalidation_taxonomy_v2": dict(OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2),
    "management_profile_taxonomy_v2": dict(OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2),
    "routing_policy_v2": dict(OBSERVE_CONFIRM_ROUTING_POLICY_V2),
    "confidence_semantics_v2": dict(OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2),
    "migration_dual_write_v1": dict(OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1),
    "action_side_semantics_v2": dict(OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2),
    "test_contract_v1": dict(OBSERVE_CONFIRM_TEST_CONTRACT_V1),
    "freeze_handoff_v1": dict(OBSERVE_CONFIRM_FREEZE_HANDOFF_V1),
    "completed_definitions": [
        "scope_freeze_v1",
        "input_contract_v2",
        "output_contract_v2",
        "state_semantics_v2",
        "archetype_taxonomy_v2",
        "invalidation_taxonomy_v2",
        "management_profile_taxonomy_v2",
        "routing_policy_v2",
        "confidence_semantics_v2",
        "migration_dual_write_v1",
        "action_side_semantics_v2",
        "test_contract_v1",
        "freeze_handoff_v1",
    ],
    "deferred_definitions": [],
    "runtime_log_embedded": True,
    "documentation_path": "docs/observe_confirm_scope_contract.md",
}


def observe_confirm_scope_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_SCOPE_CONTRACT_V1["documentation_path"]


def observe_confirm_input_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_INPUT_CONTRACT_V2["documentation_path"]


def observe_confirm_output_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["documentation_path"]


def observe_confirm_state_semantics_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_STATE_SEMANTICS_V2["documentation_path"]


def observe_confirm_archetype_taxonomy_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2["documentation_path"]


def observe_confirm_invalidation_taxonomy_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2["documentation_path"]


def observe_confirm_management_profile_taxonomy_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2["documentation_path"]


def observe_confirm_routing_policy_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_ROUTING_POLICY_V2["documentation_path"]


def observe_confirm_confidence_semantics_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2["documentation_path"]


def observe_confirm_migration_dual_write_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1["documentation_path"]


def observe_confirm_action_side_semantics_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2["documentation_path"]


def observe_confirm_test_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_TEST_CONTRACT_V1["documentation_path"]


def observe_confirm_freeze_handoff_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / OBSERVE_CONFIRM_FREEZE_HANDOFF_V1["documentation_path"]


def _coerce_observe_confirm_payload(value: Any) -> dict[str, Any]:
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


def _looks_like_observe_confirm_payload(value: Mapping[str, Any] | None) -> bool:
    if not isinstance(value, Mapping):
        return False
    keys = {str(k) for k in value.keys()}
    return bool({"state", "action", "archetype_id", "invalidation_id", "management_profile_id"} & keys)


def resolve_observe_confirm_handoff_payload(container: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(container, Mapping):
        return {}
    if _looks_like_observe_confirm_payload(container) and not any(
        key in container for key in ("observe_confirm_v2", "observe_confirm_v1", "prs_log_contract_v2", "prs_canonical_observe_confirm_field")
    ):
        return {str(k): v for k, v in container.items()}

    prs_log_contract = container.get("prs_log_contract_v2")
    if not isinstance(prs_log_contract, Mapping):
        prs_log_contract = {}

    candidate_fields: list[str] = []
    for field_name in (
        container.get("prs_canonical_observe_confirm_field"),
        prs_log_contract.get("canonical_observe_confirm_field"),
        "observe_confirm_v2",
        container.get("prs_compatibility_observe_confirm_field"),
        prs_log_contract.get("compatibility_observe_confirm_field"),
        "observe_confirm_v1",
    ):
        normalized = str(field_name or "").strip()
        if normalized and normalized not in candidate_fields:
            candidate_fields.append(normalized)

    for field_name in candidate_fields:
        payload = _coerce_observe_confirm_payload(container.get(field_name))
        if _looks_like_observe_confirm_payload(payload):
            return payload
    return {}
