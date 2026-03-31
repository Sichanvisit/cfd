from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.services.layer_mode_contract import LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1


CONSUMER_INPUT_CONTRACT_V1 = {
    "contract_version": "consumer_input_contract_v1",
    "scope": "decision_context_metadata_consumer_input_only",
    "official_input_container": "DecisionContext.metadata",
    "canonical_observe_confirm_field": "observe_confirm_v2",
    "compatibility_observe_confirm_field_v1": "observe_confirm_v1",
    "canonical_energy_field": "energy_helper_v2",
    "observe_confirm_resolution_order": [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ],
    "required_handoff_fields": [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
    ],
    "allowed_decision_context_fields": [
        "symbol",
        "market_mode",
        "direction_policy",
        "box_state",
        "bb_state",
        "liquidity_state",
        "metadata.observe_confirm_v2",
        "metadata.observe_confirm_v1",
        "metadata.layer_mode_policy_v1",
        "metadata.energy_helper_v2",
        "metadata.prs_log_contract_v2",
    ],
    "allowed_non_semantic_runtime_fields": [
        "preflight_allowed_action",
        "preflight_approach_mode",
        "preflight_reason",
        "preflight_regime",
        "preflight_liquidity",
        "position_lock_state",
        "execution_guard_state",
        "prior_entry_archetype_id",
        "prior_entry_side",
        "prior_invalidation_id",
        "re_entry_cooldown_active",
        "tick_price",
        "symbol",
        "energy_helper_v2",
    ],
    "forbidden_direct_inputs": [
        "raw_detector_score",
        "legacy_rule_branch",
        "response_raw_snapshot_v1",
        "response_vector_v2",
        "state_raw_snapshot_v1",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
        "forecast_features_v1",
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ],
    "principles": [
        "consumer reads canonical observe_confirm handoff from DecisionContext.metadata",
        "consumer reads canonical layer mode policy overlay from DecisionContext.metadata when policy-aware routing is needed",
        "consumer may read energy_helper_v2 only as an action-friendly helper and never as an identity owner",
        "setup naming may skip energy_helper_v2 or use it for reason annotation only",
        "entry service may read readiness, priority, confidence hint, and soft block hint only",
        "wait engine may read energy_helper_v2 only for enter versus wait comparison hints",
        "exit and re-entry may read energy_helper_v2 only as advisory management hints and never for identity decisions",
        "consumer may use non-semantic runtime support fields only for execution gating",
        "consumer may not directly reinterpret semantic vectors or forecast payloads",
    ],
    "consumer_entry_points": [
        "backend/services/setup_detector.py",
        "backend/services/entry_service.py",
        "backend/services/wait_engine.py",
        "backend/services/exit_service.py",
    ],
    "runtime_embedding_field": "consumer_input_contract_v1",
    "documentation_path": "docs/consumer_input_contract.md",
}


CONSUMER_ENERGY_USAGE_FREEZE_V1 = {
    "contract_version": "consumer_energy_usage_freeze_v1",
    "scope": "consumer_energy_helper_usage_only",
    "canonical_energy_field": "energy_helper_v2",
    "helper_role": "action_friendly_helper_only",
    "bridge_strategy": "hint_first_no_direct_order_decision",
    "direct_net_utility_use_allowed": False,
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
    "forbidden_energy_uses": [
        "identity rewrite",
        "place_order_directly_from_net_utility",
        "block_order_directly_from_net_utility",
        "rank_entries_directly_from_net_utility",
        "wait_gate_directly_from_net_utility",
        "selected_side as canonical side",
        "semantic label inference",
        "archetype inference",
        "invalidation override",
        "management_profile rewrite",
    ],
    "principles": [
        "consumer reads energy_helper_v2 only as a helper surface above semantic identity",
        "energy helper usage stays component-specific and execution-facing",
        "net_utility stays summary-only and consumers route through hints before any live decision path",
        "consumer may not promote energy helper into a semantic or identity owner",
    ],
    "documentation_path": "docs/consumer_scope_contract.md",
}


CONSUMER_INPUT_CONTRACT_V1["energy_usage_freeze_v1"] = CONSUMER_ENERGY_USAGE_FREEZE_V1


CONSUMER_LAYER_MODE_INTEGRATION_V1 = {
    "contract_version": "consumer_layer_mode_integration_v1",
    "scope": "consumer_policy_overlay_input_only",
    "official_resolution_helper": "resolve_consumer_layer_mode_policy_resolution",
    "official_payload_helper": "resolve_consumer_layer_mode_policy_input",
    "canonical_policy_field": "layer_mode_policy_v1",
    "canonical_identity_field": "observe_confirm_v2",
    "policy_resolution_order": [
        "prs_log_contract_v2.layer_mode_policy_output_field",
        "layer_mode_policy_v1",
    ],
    "required_policy_fields": [
        "layer_modes",
        "effective_influences",
        "suppressed_reasons",
        "confidence_adjustments",
        "hard_blocks",
        "mode_decision_trace",
    ],
    "principles": [
        "consumer reads canonical identity from observe_confirm and canonical policy input from layer_mode_policy_v1",
        "layer mode policy may modulate readiness or suppression, but may not rewrite archetype_id or side",
        "consumer may not bypass layer_mode_policy_v1 by re-reading semantic vectors directly",
        "setup naming may ignore policy output for identity, but execution-facing consumers must still treat layer_mode_policy_v1 as the official policy input surface",
    ],
    "component_policy_usage": [
        {
            "component": "SetupDetector",
            "policy_usage": "identity_preserving no-op; naming still roots in observe_confirm",
        },
        {
            "component": "EntryService",
            "policy_usage": "official policy input for readiness, suppression, and audit interpretation",
        },
        {
            "component": "Exit",
            "policy_usage": "reads policy payload only as future overlay context, never as identity source",
        },
        {
            "component": "ReEntry",
            "policy_usage": "reads policy payload only as future overlay context, never as identity source",
        },
    ],
    "runtime_embedding_field": "consumer_layer_mode_integration_v1",
    "documentation_path": "docs/consumer_layer_mode_integration.md",
}


CONSUMER_MIGRATION_FREEZE_V1 = {
    "contract_version": "consumer_migration_freeze_v1",
    "scope": "observe_confirm_consumer_resolution_freeze",
    "official_resolution_helper": "resolve_consumer_observe_confirm_resolution",
    "official_payload_helper": "resolve_consumer_observe_confirm_input",
    "official_guard_helper": "build_consumer_migration_guard_metadata",
    "read_order": [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ],
    "canonical_field": "observe_confirm_v2",
    "compatibility_field_v1": "observe_confirm_v1",
    "compatibility_role": "migration_bridge_only",
    "fallback_allowed_only_when_canonical_missing": True,
    "live_runtime_branch_on_compatibility_field_allowed": False,
    "identity_ownership_affected_by_compatibility_field": False,
    "canonical_shadow_rebuild_allowed_for_replay": True,
    "rules": [
        "consumer must resolve observe_confirm through the shared consumer helper only",
        "consumer reads observe_confirm_v2 first and uses observe_confirm_v1 only as compatibility fallback",
        "consumer runtime logic may not branch on observe_confirm_v1 or observe_confirm_v2 directly",
        "observe_confirm_v1 may remain in metadata and replay logs, but only as a migration bridge when canonical observe_confirm_v2 is absent",
        "compatibility fallback may not override or mutate canonical identity when observe_confirm_v2 is present",
        "migration logging must record the actual consumed observe_confirm field",
    ],
    "consumer_entry_points": [
        "backend/services/setup_detector.py",
        "backend/services/entry_service.py",
        "backend/services/exit_service.py",
    ],
    "v1_removal_readiness": [
        "all consumer entry points resolve through the shared helper",
        "logs show no compatibility fallback dependence",
        "observe_confirm_v1 direct reads are absent from consumer runtime logic",
    ],
    "runtime_embedding_field": "consumer_migration_freeze_v1",
    "documentation_path": "docs/consumer_migration_freeze.md",
}


SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1 = {
    "contract_version": "setup_detector_responsibility_v1",
    "scope": "setup_naming_only",
    "consumer_component": "SetupDetector",
    "official_input_fields": [
        "archetype_id",
        "side",
        "reason",
        "market_mode",
    ],
    "input_sources": {
        "archetype_id": "DecisionContext.metadata.observe_confirm_v2.archetype_id",
        "side": "DecisionContext.metadata.observe_confirm_v2.side or action fallback",
        "reason": "DecisionContext.metadata.observe_confirm_v2.reason",
        "market_mode": "DecisionContext.market_mode",
    },
    "responsibilities": [
        "map canonical archetype handoff into setup_id only",
        "specialize setup_id by market_mode and handoff reason only",
        "apply only setup mappings allowed by setup_mapping_contract_v1",
        "preserve upstream archetype identity without semantic reinterpretation",
    ],
    "non_responsibilities": [
        "confirm or wait re-decision",
        "action selection",
        "trigger strength scoring",
        "entry gating",
        "semantic vector reinterpretation",
    ],
    "energy_helper_policy": {
        "usage": "not required; optional reason annotation only",
        "allowed_energy_fields": [],
        "optional_annotation_fields": [
            "soft_block_hint.reason",
            "metadata.utility_hints.priority_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
    },
    "output_contract": {
        "primary_field": "setup_id",
        "support_fields": [
            "side",
            "status",
            "trigger_state",
            "entry_quality",
            "metadata.reason",
        ],
        "matched_trigger_state": "READY",
        "rejected_trigger_state": "UNKNOWN",
        "entry_quality_source": "observe_confirm confidence passthrough",
    },
    "runtime_embedding_field": "setup_detector_responsibility_contract_v1",
    "documentation_path": "docs/setup_detector_responsibility_contract.md",
}


SETUP_MAPPING_CONTRACT_V1 = {
    "contract_version": "setup_mapping_contract_v1",
    "scope": "canonical_archetype_to_setup_mapping_only",
    "consumer_component": "SetupDetector",
    "official_input_fields": [
        "archetype_id",
        "side",
        "reason",
        "market_mode",
    ],
    "principles": [
        "setup specialization may refine setup_id but may not rewrite archetype_id",
        "market_mode and handoff reason may specialize setup_id inside the same archetype family only",
        "unmapped archetypes should be rejected instead of guessed",
    ],
    "canonical_mapping": [
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
            "allowed_setup_ids": [
                "range_lower_reversal_buy",
                "trend_pullback_buy",
            ],
        },
        {
            "archetype_id": "mid_lose_sell",
            "side": "SELL",
            "default_setup_id": "range_upper_reversal_sell",
            "allowed_setup_ids": [
                "range_upper_reversal_sell",
                "trend_pullback_sell",
            ],
        },
    ],
    "specialization_rules": [
        {
            "archetype_id": "mid_reclaim_buy",
            "side": "BUY",
            "default_setup_id": "range_lower_reversal_buy",
            "specializations": [
                {
                    "setup_id": "trend_pullback_buy",
                    "when_any": [
                        "market_mode == TREND",
                        "reason startswith trend_pullback_buy",
                        "reason startswith failed_sell_reclaim_buy",
                    ],
                }
            ],
        },
        {
            "archetype_id": "mid_lose_sell",
            "side": "SELL",
            "default_setup_id": "range_upper_reversal_sell",
            "specializations": [
                {
                    "setup_id": "trend_pullback_sell",
                    "when_any": [
                        "market_mode == TREND",
                        "reason startswith trend_pullback_sell",
                    ],
                }
            ],
        },
    ],
    "runtime_embedding_field": "setup_mapping_contract_v1",
    "documentation_path": "docs/setup_mapping_contract.md",
}


SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1["setup_mapping_contract_v1"] = SETUP_MAPPING_CONTRACT_V1


ENTRY_GUARD_CONTRACT_V1 = {
    "contract_version": "entry_guard_contract_v1",
    "scope": "canonical_consumer_action_block_reasons",
    "consumer_component": "EntryService",
    "official_reason_field": "action_none_reason",
    "normalized_block_fields": [
        "consumer_block_reason",
        "consumer_block_kind",
        "consumer_block_source_layer",
        "consumer_block_is_execution",
        "consumer_block_is_semantic_non_action",
    ],
    "principles": [
        "semantic non-action reasons must stay distinct from execution block reasons",
        "execution block reasons must use canonical ids when action was otherwise actionable",
        "observe_confirm wait or observe reasons may pass through as semantic non-action reasons",
    ],
    "reason_registry": [
        {
            "reason": "observe_confirm_missing",
            "kind": "semantic_non_action",
            "source_layer": "consumer_input",
            "is_execution_block": False,
            "is_semantic_non_action": True,
        },
        {
            "reason": "preflight_no_trade",
            "kind": "preflight_block",
            "source_layer": "preflight",
            "is_execution_block": False,
            "is_semantic_non_action": True,
        },
        {
            "reason": "preflight_action_blocked",
            "kind": "preflight_block",
            "source_layer": "preflight",
            "is_execution_block": False,
            "is_semantic_non_action": True,
        },
        {
            "reason": "opposite_position_lock",
            "kind": "execution_block",
            "source_layer": "position_lock",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "clustered_entry_price_zone",
            "kind": "execution_block",
            "source_layer": "cluster_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "bb_buy_without_lower_touch",
            "kind": "execution_block",
            "source_layer": "bb_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "bb_sell_without_upper_touch",
            "kind": "execution_block",
            "source_layer": "bb_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "box_middle_buy_without_bb_support",
            "kind": "execution_block",
            "source_layer": "box_middle_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "box_middle_sell_without_bb_resistance",
            "kind": "execution_block",
            "source_layer": "box_middle_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "hard_guard_spread_too_wide",
            "kind": "execution_hard_block",
            "source_layer": "hard_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "hard_guard_volatility_too_low",
            "kind": "execution_hard_block",
            "source_layer": "hard_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
        {
            "reason": "hard_guard_volatility_too_high",
            "kind": "execution_hard_block",
            "source_layer": "hard_guard",
            "is_execution_block": True,
            "is_semantic_non_action": False,
        },
    ],
    "passthrough_policy": {
        "kind": "semantic_non_action_passthrough",
        "source_layer": "observe_confirm",
        "applies_when": "action is none and reason is not in the canonical execution registry",
    },
    "runtime_embedding_field": "entry_guard_contract_v1",
    "documentation_path": "docs/entry_guard_contract.md",
}


ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1 = {
    "contract_version": "entry_service_responsibility_v1",
    "scope": "execution_guard_only",
    "consumer_component": "EntryService",
    "official_input_fields": [
        "observe_confirm.state",
        "observe_confirm.action",
        "observe_confirm.side",
        "observe_confirm.confidence",
        "observe_confirm.reason",
        "observe_confirm.archetype_id",
        "observe_confirm.invalidation_id",
        "observe_confirm.management_profile_id",
        "setup_id",
        "setup_reason",
        "preflight_allowed_action",
        "preflight_approach_mode",
        "preflight_regime",
        "preflight_liquidity",
        "position_lock_state",
        "execution_guard_state",
        "energy_helper_v2.action_readiness",
        "energy_helper_v2.confidence_adjustment_hint",
        "energy_helper_v2.soft_block_hint",
        "energy_helper_v2.metadata.utility_hints.priority_hint",
        "cooldown_state",
        "spread_state",
        "tick_price",
    ],
    "responsibilities": [
        "apply execution guard outcomes such as no-trade blocks, opposite-position lock, spread or liquidity blocks, cluster guard, and runtime order plumbing",
        "preserve observe_confirm handoff ids while deciding whether execution is allowed",
        "pass setup_id through to downstream execution without semantic remapping",
        "classify action blocks with entry_guard_contract_v1 so semantic non-action and execution blocks stay separate",
        "read energy helper only for readiness, priority, confidence hint, and soft block hint",
    ],
    "non_responsibilities": [
        "archetype_id rewrite",
        "setup_id rewrite",
        "semantic confirm reversal to the opposite side",
        "invalidation_id recomputation",
        "management_profile_id recomputation",
        "semantic vector reinterpretation",
        "energy selected_side identity promotion",
    ],
    "allowed_actions": [
        "keep_confirmed_action",
        "block_action_with_reason",
        "apply_execution_guards",
        "compute_lot_sizing",
        "send_order",
    ],
    "forbidden_actions": [
        "flip_buy_to_sell",
        "flip_sell_to_buy",
        "remap_archetype_id",
        "remap_setup_id",
        "replace_canonical_handoff_ids",
    ],
    "preservation_rules": [
        "blocking execution may set action to none but must not mutate observe_confirm action in the input handoff",
        "archetype_id, invalidation_id, and management_profile_id remain canonical consumer handoff ids",
        "setup_id may be consumed by execution guards but not replaced by a different semantic family inside EntryService",
    ],
    "energy_helper_policy": {
        "usage": "readiness, priority, confidence hint, and soft block hint only",
        "allowed_energy_fields": [
            "action_readiness",
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
        "forbidden_energy_uses": [
            "place_order_directly_from_net_utility",
            "block_order_directly_from_net_utility",
            "selected_side as canonical side",
            "archetype inference",
            "invalidation override",
            "management_profile rewrite",
        ],
    },
    "runtime_embedding_field": "entry_service_responsibility_contract_v1",
    "documentation_path": "docs/entry_service_responsibility_contract.md",
}


ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1["entry_guard_contract_v1"] = ENTRY_GUARD_CONTRACT_V1


EXIT_HANDOFF_CONTRACT_V1 = {
    "contract_version": "exit_handoff_contract_v1",
    "scope": "canonical_exit_handoff_from_entry_consumer",
    "consumer_component": "Exit",
    "official_input_fields": [
        "management_profile_id",
        "invalidation_id",
    ],
    "compatibility_fallback_fields": [
        "entry_setup_id",
        "exit_profile",
    ],
    "principles": [
        "exit must read canonical management_profile_id and invalidation_id before setup-based fallbacks",
        "entry_setup_id may refine legacy behavior only when canonical handoff fields are absent",
        "invalidation_id remains canonical failure identity and must pass through to exit metadata unchanged",
    ],
    "energy_helper_policy": {
        "usage": "future management hint only; no identity decisions",
        "allowed_energy_fields": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.priority_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
        "forbidden_energy_uses": [
            "place_order_directly_from_net_utility",
            "selected_side as canonical side",
            "invalidation rewrite",
            "management_profile rewrite",
            "archetype inference",
        ],
    },
    "canonical_management_profiles": [
        "reversal_profile",
        "breakout_hold_profile",
        "support_hold_profile",
        "breakdown_hold_profile",
        "mid_reclaim_fast_exit_profile",
        "mid_lose_fast_exit_profile",
    ],
    "canonical_profile_mapping": [
        {
            "management_profile_id": "reversal_profile",
            "default_exit_profile": "tight_protect",
        },
        {
            "management_profile_id": "breakout_hold_profile",
            "default_exit_profile": "hold_then_trail",
        },
        {
            "management_profile_id": "support_hold_profile",
            "default_exit_profile": "tight_protect",
        },
        {
            "management_profile_id": "breakdown_hold_profile",
            "default_exit_profile": "hold_then_trail",
        },
        {
            "management_profile_id": "mid_reclaim_fast_exit_profile",
            "default_exit_profile": "tight_protect",
        },
        {
            "management_profile_id": "mid_lose_fast_exit_profile",
            "default_exit_profile": "tight_protect",
        },
    ],
    "runtime_embedding_field": "exit_handoff_contract_v1",
    "documentation_path": "docs/exit_handoff_contract.md",
}


RE_ENTRY_CONTRACT_V1 = {
    "contract_version": "re_entry_contract_v1",
    "scope": "canonical_re_entry_policy_from_consumer_handoff",
    "consumer_component": "ReEntry",
    "official_input_fields": [
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
    ],
    "principles": [
        "re-entry requires same-archetype confirm from the current observe_confirm handoff",
        "re-entry cooldown is an execution timing guard and stays separate from archetype persistence",
        "middle averaging-in is forbidden even when the archetype family matches",
        "immediate reverse entry after invalidation is forbidden inside the same re-entry cycle",
    ],
    "energy_helper_policy": {
        "usage": "future management hint only; no identity decisions",
        "allowed_energy_fields": [
            "confidence_adjustment_hint",
            "soft_block_hint",
            "metadata.utility_hints.wait_vs_enter_hint",
        ],
        "direct_net_utility_use_allowed": False,
        "identity_decision_allowed": False,
        "forbidden_energy_uses": [
            "place_order_directly_from_net_utility",
            "selected_side as canonical side",
            "same_archetype override",
            "side flip",
            "invalidation rewrite",
        ],
    },
    "required_current_state": {
        "state": "CONFIRM",
        "allowed_actions": ["BUY", "SELL"],
        "same_archetype_confirm_required": True,
    },
    "forbidden_middle_contexts": {
        "box_state": ["MIDDLE"],
        "bb_state": ["MID"],
    },
    "reverse_after_invalidation_policy": {
        "immediate_reverse_allowed": False,
        "unlock_condition": "fresh non-reentry cycle or explicit cooldown reset",
    },
    "blocked_reason_registry": [
        {
            "reason": "reentry_missing_prior_context",
            "kind": "policy_context_missing",
            "dimension": "persistence",
        },
        {
            "reason": "reentry_same_archetype_confirm_required",
            "kind": "policy_block",
            "dimension": "persistence",
        },
        {
            "reason": "reentry_middle_averaging_forbidden",
            "kind": "policy_block",
            "dimension": "averaging",
        },
        {
            "reason": "reentry_immediate_reverse_after_invalidation_forbidden",
            "kind": "policy_block",
            "dimension": "reverse_lock",
        },
        {
            "reason": "reentry_cooldown_active",
            "kind": "execution_timing_block",
            "dimension": "cooldown",
        },
    ],
    "policy_outputs": [
        "eligible",
        "blocked_reason",
        "blocked_reason_kind",
        "same_archetype_confirmed",
        "persistence_ok",
        "cooldown_ok",
        "middle_reentry_forbidden",
        "reverse_after_invalidation_forbidden",
        "current_archetype_id",
        "prior_archetype_id",
        "contract_version",
    ],
    "runtime_embedding_field": "re_entry_contract_v1",
    "documentation_path": "docs/re_entry_contract.md",
}


CONSUMER_LOGGING_CONTRACT_V1 = {
    "contract_version": "consumer_logging_contract_v1",
    "scope": "consumer_audit_logging_only",
    "consumer_component": "ConsumerLogging",
    "official_fields": [
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
    ],
    "supplemental_fields": [
        "consumer_block_is_execution",
        "consumer_block_is_semantic_non_action",
        "consumer_policy_input_field",
        "consumer_policy_contract_version",
        "consumer_policy_identity_preserved",
        "energy_helper_v2",
    ],
    "guard_result_values": [
        "PASS",
        "SEMANTIC_NON_ACTION",
        "EXECUTION_BLOCK",
    ],
    "field_resolution": {
        "consumer_input_observe_confirm_field": "actual field resolved by resolve_consumer_observe_confirm_resolution",
        "consumer_input_contract_version": "consumer_input_contract_v1.contract_version",
        "consumer_setup_id": "setup_id passthrough",
        "consumer_handoff_contract_version": "observe_confirm_output_contract_v2.contract_version",
        "energy_helper_v2": "serialized canonical energy helper including replay trace and actual consumer usage trace",
    },
    "principles": [
        "consumer logs must say which observe_confirm field was consumed",
        "consumer logs must preserve which energy helper hints were actually consumed and keep them advisory unless a later phase promotes live gating",
        "consumer logs must preserve canonical handoff ids even when execution is blocked",
        "consumer guard result must stay separate from detailed block_kind and block_reason",
        "semantic non-action and execution block remain distinguishable in log review",
    ],
    "runtime_embedding_field": "consumer_logging_contract_v1",
    "documentation_path": "docs/consumer_logging_contract.md",
}


CONSUMER_TEST_CONTRACT_V1 = {
    "contract_version": "consumer_test_contract_v1",
    "scope": "consumer_regression_lock_only",
    "consumer_component": "ConsumerTestPlan",
    "required_behavior_axes": [
        {
            "id": "setup_detector_naming_only",
            "guarantee": "SetupDetector performs archetype naming only and does not re-score confirm or wait semantics.",
            "primary_test_file": "tests/unit/test_setup_detector.py",
        },
        {
            "id": "entry_service_no_semantic_reinterpretation",
            "guarantee": "EntryService applies execution guards without rewriting archetype identity or flipping semantic meaning.",
            "primary_test_file": "tests/unit/test_entry_service_guards.py",
        },
        {
            "id": "consumer_v2_canonical_v1_fallback",
            "guarantee": "Consumer resolves observe_confirm with v2 first and uses v1 only as compatibility fallback.",
            "primary_test_file": "tests/unit/test_consumer_scope_contract.py",
        },
        {
            "id": "handoff_ids_stable_per_archetype",
            "guarantee": "The same archetype_id carries deterministic invalidation_id and management_profile_id handoff ids.",
            "primary_test_file": "tests/unit/test_consumer_scope_contract.py",
        },
        {
            "id": "execution_guard_preserves_semantic_identity",
            "guarantee": "Execution guards can block action but cannot mutate canonical archetype or handoff ids.",
            "primary_test_file": "tests/unit/test_entry_service_guards.py",
        },
        {
            "id": "blocked_rows_keep_archetype_metadata",
            "guarantee": "Blocked rows still retain consumer archetype, invalidation, and management profile metadata for review.",
            "primary_test_file": "tests/unit/test_entry_service_guards.py",
        },
        {
            "id": "energy_helper_usage_freeze",
            "guarantee": "Consumer reads energy_helper_v2 only through the frozen component usage boundary and never as an identity owner.",
            "primary_test_file": "tests/unit/test_consumer_scope_contract.py",
        },
    ],
    "supporting_runtime_contract_tests": [
        "tests/unit/test_context_classifier.py",
        "tests/unit/test_entry_engines.py",
        "tests/unit/test_decision_models.py",
        "tests/unit/test_prs_engine.py",
    ],
    "principles": [
        "consumer regression tests must lock behavior, contract embedding, and log output together",
        "behavioral tests stay separate from scope and logging contract tests, but all are required for freeze",
        "execution blocks must remain distinguishable from semantic non-action without losing canonical handoff ids",
    ],
    "runtime_embedding_field": "consumer_test_contract_v1",
    "documentation_path": "docs/consumer_test_contract.md",
}


CONSUMER_FREEZE_HANDOFF_V1 = {
    "contract_version": "consumer_freeze_handoff_v1",
    "scope": "canonical_consumer_freeze_and_handoff_only",
    "consumer_component": "ConsumerFreezeHandoff",
    "official_handoff_helper": "resolve_consumer_handoff_payload",
    "objective": "Freeze the final consumer handoff so setup, entry, exit, and re-entry can operate from ObserveConfirmSnapshot v2 without semantic reinterpretation.",
    "completion_criteria": [
        "consumer can operate from ObserveConfirmSnapshot v2 plus non-semantic runtime support only",
        "setup, entry, exit, and re-entry responsibility boundaries stay separated",
        "semantic layer reinterpretation is absent from consumer execution paths",
        "layer mode overlay result is consumed as official policy input above canonical observe_confirm identity",
    ],
    "consumer_handoff_sections": [
        "observe_confirm_resolution",
        "observe_confirm",
        "layer_mode_policy_resolution",
        "layer_mode_policy",
        "energy_helper",
        "setup_mapping_input",
        "setup_mapping",
        "exit_handoff",
        "re_entry_handoff",
    ],
    "component_handoff_policy": [
        {
            "component": "SetupDetector",
            "official_inputs": ["observe_confirm", "setup_mapping_input"],
            "forbidden_behavior": "confirm or wait semantic reinterpretation",
        },
        {
            "component": "EntryService",
            "official_inputs": [
                "observe_confirm_resolution",
                "observe_confirm",
                "layer_mode_policy_resolution",
                "layer_mode_policy",
                "energy_helper",
            ],
            "forbidden_behavior": "archetype identity rewrite or semantic side flip",
        },
        {
            "component": "WaitEngine",
            "official_inputs": ["energy_helper"],
            "forbidden_behavior": "identity ownership or semantic reinterpretation from energy helper",
        },
        {
            "component": "Exit",
            "official_inputs": ["exit_handoff", "energy_helper"],
            "forbidden_behavior": "setup-name-first exit routing",
        },
        {
            "component": "ReEntry",
            "official_inputs": ["re_entry_handoff", "energy_helper"],
            "forbidden_behavior": "re-entry semantic recomputation outside canonical handoff ids",
        },
    ],
    "future_policy_overlay": {
        "layer_mode_ready": True,
        "integration_point": "consumer handoff reads canonical layer_mode_policy_v1 as the policy-strength overlay while observe_confirm remains the identity source",
    },
    "runtime_embedding_field": "consumer_freeze_handoff_v1",
    "documentation_path": "docs/consumer_freeze_handoff.md",
}


CONSUMER_SCOPE_CONTRACT_V1 = {
    "contract_version": "consumer_scope_v1",
    "scope": "observe_confirm_consumer_only",
    "objective": "Freeze the consumer boundary so downstream layers consume ObserveConfirmSnapshot v2 without reinterpreting semantic layers.",
    "canonical_input_field": "observe_confirm_v2",
    "compatibility_input_field_v1": "observe_confirm_v1",
    "input_contract_v1": CONSUMER_INPUT_CONTRACT_V1,
    "energy_usage_freeze_v1": CONSUMER_ENERGY_USAGE_FREEZE_V1,
    "layer_mode_integration_v1": CONSUMER_LAYER_MODE_INTEGRATION_V1,
    "migration_freeze_v1": CONSUMER_MIGRATION_FREEZE_V1,
    "setup_detector_responsibility_contract_v1": SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1,
    "setup_mapping_contract_v1": SETUP_MAPPING_CONTRACT_V1,
    "entry_guard_contract_v1": ENTRY_GUARD_CONTRACT_V1,
    "entry_service_responsibility_contract_v1": ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
    "exit_handoff_contract_v1": EXIT_HANDOFF_CONTRACT_V1,
    "re_entry_contract_v1": RE_ENTRY_CONTRACT_V1,
    "consumer_logging_contract_v1": CONSUMER_LOGGING_CONTRACT_V1,
    "consumer_test_contract_v1": CONSUMER_TEST_CONTRACT_V1,
    "consumer_freeze_handoff_v1": CONSUMER_FREEZE_HANDOFF_V1,
    "consumer_components": [
        {
            "component": "SetupDetector",
            "file": "backend/services/setup_detector.py",
            "responsibility": "map canonical archetype handoff into setup naming only",
        },
        {
            "component": "EntryService",
            "file": "backend/services/entry_service.py",
            "responsibility": "apply execution guards and order plumbing only",
        },
        {
            "component": "WaitEngine",
            "file": "backend/services/wait_engine.py",
            "responsibility": "consume energy helper only as enter versus wait comparison hints",
        },
        {
            "component": "Exit",
            "file": "backend/services/exit_service.py",
            "responsibility": "consume invalidation_id and management_profile_id as canonical exit handoff ids",
        },
        {
            "component": "ReEntry",
            "file": "backend/services/entry_service.py",
            "responsibility": "consume same-archetype re-entry policy without recomputing semantic meaning",
        },
    ],
    "responsibilities": [
        "read observe_confirm_v2 state, action, side, confidence, reason, archetype_id, invalidation_id, and management_profile_id",
        "read layer_mode_policy_v1 as the official policy input overlay above canonical observe_confirm identity",
        "read energy_helper_v2 only through the frozen component usage boundary",
        "connect observe_confirm output to setup naming, entry guards, exit handoff, and re-entry policy hooks",
        "preserve canonical handoff ids during execution-layer decisions",
        "emit canonical consumer audit fields for pass or block review",
    ],
    "non_responsibilities": [
        "semantic layer reinterpretation",
        "raw detector direct read",
        "response or state vector recomputation",
        "evidence, belief, barrier, or forecast re-scoring",
        "archetype identity rewriting",
        "energy helper identity promotion",
    ],
    "allowed_runtime_inputs": [
        "observe_confirm_v2",
        "observe_confirm_v1",
        "layer_mode_policy_v1",
        "energy_helper_v2",
        "prs_log_contract_v2",
        "preflight context",
        "execution guard state",
        "position lock state",
        "prior entry handoff ids",
        "re-entry cooldown state",
    ],
    "forbidden_runtime_inputs": [
        "raw_detector_score",
        "legacy_rule_branch",
        "response_raw_snapshot_v1",
        "state_raw_snapshot_v1",
        "response_vector_v2_direct_consumer_reinterpretation",
        "state_vector_v2_direct_consumer_reinterpretation",
        "evidence_vector_v1_direct_consumer_reinterpretation",
        "belief_state_v1_direct_consumer_reinterpretation",
        "barrier_state_v1_direct_consumer_reinterpretation",
        "transition_forecast_v1_direct_consumer_reinterpretation",
        "trade_management_forecast_v1_direct_consumer_reinterpretation",
    ],
    "handoff_fields": [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
    ],
    "consumer_boundary": {
        "setup_detector": "Names setup_id only from observe_confirm handoff and market context; energy helper is optional and annotation-only.",
        "entry_service": "Applies preflight and execution guards only; it reads energy_helper_v2 only for readiness, priority, confidence hint, and soft block hint.",
        "wait_engine": "Compares enter versus wait using energy_helper_v2 hints only and never as an identity source.",
        "exit": "Reads management_profile_id and invalidation_id first and may treat energy_helper_v2 only as advisory management hint input.",
        "re_entry": "Requires same-archetype reconfirmation, forbids middle averaging-in, and may read energy_helper_v2 only as a non-identity management hint.",
        "logging": "Records consumed handoff field, canonical ids, policy overlay input, guard result, and block reason without semantic reinterpretation.",
    },
    "runtime_embedding_field": "consumer_scope_contract_v1",
    "documentation_path": "docs/consumer_scope_contract.md",
}


def _consumer_metadata(container: Any) -> Mapping[str, Any]:
    if hasattr(container, "metadata"):
        metadata = getattr(container, "metadata", {})
        if isinstance(metadata, Mapping):
            return metadata
    if isinstance(container, Mapping):
        return container
    return {}


def _coerce_observe_confirm_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str):
        text = str(value).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _coerce_layer_mode_policy_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str):
        text = str(value).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _coerce_energy_helper_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, str):
        text = str(value).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return {str(k): v for k, v in parsed.items()}
    return {}


def _looks_like_consumer_observe_confirm_payload(value: Mapping[str, Any] | None) -> bool:
    if not isinstance(value, Mapping):
        return False
    keys = {str(k) for k in value.keys()}
    required = {"state", "action", "archetype_id", "invalidation_id", "management_profile_id"}
    return required.issubset(keys) or bool(required & keys)


def _looks_like_layer_mode_policy_payload(value: Mapping[str, Any] | None) -> bool:
    if not isinstance(value, Mapping):
        return False
    keys = {str(k) for k in value.keys()}
    required = {"layer_modes", "effective_influences", "mode_decision_trace"}
    return required.issubset(keys) or bool(required & keys)


def _resolve_consumer_observe_confirm_field_preferences(
    metadata: Mapping[str, Any],
) -> tuple[list[str], list[str], str, str]:
    prs_log_contract = metadata.get("prs_log_contract_v2")
    if not isinstance(prs_log_contract, Mapping):
        prs_log_contract = {}

    compatibility_field = str(
        metadata.get("prs_compatibility_observe_confirm_field")
        or prs_log_contract.get("compatibility_observe_confirm_field")
        or CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"]
        or ""
    ).strip()
    if not compatibility_field:
        compatibility_field = str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"])

    canonical_candidates: list[str] = []
    for field_name in (
        metadata.get("prs_canonical_observe_confirm_field"),
        prs_log_contract.get("canonical_observe_confirm_field"),
        CONSUMER_MIGRATION_FREEZE_V1["canonical_field"],
    ):
        normalized = str(field_name or "").strip()
        if normalized and normalized != compatibility_field and normalized not in canonical_candidates:
            canonical_candidates.append(normalized)

    if not canonical_candidates:
        canonical_candidates.append(str(CONSUMER_MIGRATION_FREEZE_V1["canonical_field"]))

    compatibility_candidates: list[str] = []
    for field_name in (
        metadata.get("prs_compatibility_observe_confirm_field"),
        prs_log_contract.get("compatibility_observe_confirm_field"),
        CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"],
    ):
        normalized = str(field_name or "").strip()
        if normalized and normalized not in compatibility_candidates:
            compatibility_candidates.append(normalized)

    canonical_field = canonical_candidates[0]
    return canonical_candidates, compatibility_candidates, canonical_field, compatibility_field


def resolve_consumer_observe_confirm_resolution(container: Any) -> dict[str, Any]:
    metadata = _consumer_metadata(container)
    if not isinstance(metadata, Mapping):
        return {
            "payload": {},
            "field_name": "",
            "used_fallback_v1": False,
            "canonical_field": str(CONSUMER_MIGRATION_FREEZE_V1["canonical_field"]),
            "compatibility_field_v1": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"]),
            "canonical_payload_present": False,
            "compatibility_payload_present": False,
            "compatibility_role": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_role"]),
            "fallback_allowed_only_when_canonical_missing": bool(
                CONSUMER_MIGRATION_FREEZE_V1["fallback_allowed_only_when_canonical_missing"]
            ),
            "identity_ownership_affected_by_compatibility_field": bool(
                CONSUMER_MIGRATION_FREEZE_V1["identity_ownership_affected_by_compatibility_field"]
            ),
            "live_runtime_branch_on_compatibility_field_allowed": bool(
                CONSUMER_MIGRATION_FREEZE_V1["live_runtime_branch_on_compatibility_field_allowed"]
            ),
            "contract_version": CONSUMER_MIGRATION_FREEZE_V1["contract_version"],
        }
    if _looks_like_consumer_observe_confirm_payload(metadata) and not any(
        key in metadata for key in ("observe_confirm_v2", "observe_confirm_v1", "prs_log_contract_v2", "prs_canonical_observe_confirm_field")
    ):
        return {
            "payload": {str(k): v for k, v in metadata.items()},
            "field_name": "",
            "used_fallback_v1": False,
            "canonical_field": str(CONSUMER_MIGRATION_FREEZE_V1["canonical_field"]),
            "compatibility_field_v1": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"]),
            "canonical_payload_present": True,
            "compatibility_payload_present": False,
            "compatibility_role": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_role"]),
            "fallback_allowed_only_when_canonical_missing": bool(
                CONSUMER_MIGRATION_FREEZE_V1["fallback_allowed_only_when_canonical_missing"]
            ),
            "identity_ownership_affected_by_compatibility_field": bool(
                CONSUMER_MIGRATION_FREEZE_V1["identity_ownership_affected_by_compatibility_field"]
            ),
            "live_runtime_branch_on_compatibility_field_allowed": bool(
                CONSUMER_MIGRATION_FREEZE_V1["live_runtime_branch_on_compatibility_field_allowed"]
            ),
            "contract_version": CONSUMER_MIGRATION_FREEZE_V1["contract_version"],
        }

    canonical_candidates, compatibility_candidates, canonical_field, compatibility_field = (
        _resolve_consumer_observe_confirm_field_preferences(metadata)
    )
    canonical_payload_present = any(
        _looks_like_consumer_observe_confirm_payload(_coerce_observe_confirm_payload(metadata.get(field_name)))
        for field_name in canonical_candidates
    )
    compatibility_payload_present = any(
        _looks_like_consumer_observe_confirm_payload(_coerce_observe_confirm_payload(metadata.get(field_name)))
        for field_name in compatibility_candidates
    )

    for field_name in canonical_candidates + compatibility_candidates:
        payload = _coerce_observe_confirm_payload(metadata.get(field_name))
        if _looks_like_consumer_observe_confirm_payload(payload):
            return {
                "payload": payload,
                "field_name": field_name,
                "used_fallback_v1": field_name in compatibility_candidates,
                "canonical_field": canonical_field,
                "compatibility_field_v1": compatibility_field,
                "canonical_payload_present": canonical_payload_present,
                "compatibility_payload_present": compatibility_payload_present,
                "compatibility_role": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_role"]),
                "fallback_allowed_only_when_canonical_missing": bool(
                    CONSUMER_MIGRATION_FREEZE_V1["fallback_allowed_only_when_canonical_missing"]
                ),
                "identity_ownership_affected_by_compatibility_field": bool(
                    CONSUMER_MIGRATION_FREEZE_V1["identity_ownership_affected_by_compatibility_field"]
                ),
                "live_runtime_branch_on_compatibility_field_allowed": bool(
                    CONSUMER_MIGRATION_FREEZE_V1["live_runtime_branch_on_compatibility_field_allowed"]
                ),
                "contract_version": CONSUMER_MIGRATION_FREEZE_V1["contract_version"],
            }

    return {
        "payload": {},
        "field_name": "",
        "used_fallback_v1": False,
        "canonical_field": canonical_field,
        "compatibility_field_v1": compatibility_field,
        "canonical_payload_present": canonical_payload_present,
        "compatibility_payload_present": compatibility_payload_present,
        "compatibility_role": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_role"]),
        "fallback_allowed_only_when_canonical_missing": bool(
            CONSUMER_MIGRATION_FREEZE_V1["fallback_allowed_only_when_canonical_missing"]
        ),
        "identity_ownership_affected_by_compatibility_field": bool(
            CONSUMER_MIGRATION_FREEZE_V1["identity_ownership_affected_by_compatibility_field"]
        ),
        "live_runtime_branch_on_compatibility_field_allowed": bool(
            CONSUMER_MIGRATION_FREEZE_V1["live_runtime_branch_on_compatibility_field_allowed"]
        ),
        "contract_version": CONSUMER_MIGRATION_FREEZE_V1["contract_version"],
    }


def resolve_consumer_observe_confirm_input(container: Any) -> dict[str, Any]:
    return dict(resolve_consumer_observe_confirm_resolution(container).get("payload", {}) or {})


def build_consumer_migration_guard_metadata(container: Any) -> dict[str, Any]:
    resolution = resolve_consumer_observe_confirm_resolution(container)
    canonical_present = bool(resolution.get("canonical_payload_present", False))
    compatibility_present = bool(resolution.get("compatibility_payload_present", False))
    used_fallback = bool(resolution.get("used_fallback_v1", False))
    return {
        "contract_version": str(CONSUMER_MIGRATION_FREEZE_V1["contract_version"]),
        "canonical_field": str(resolution.get("canonical_field", CONSUMER_MIGRATION_FREEZE_V1["canonical_field"]) or ""),
        "compatibility_field_v1": str(
            resolution.get("compatibility_field_v1", CONSUMER_MIGRATION_FREEZE_V1["compatibility_field_v1"]) or ""
        ),
        "resolved_field_name": str(resolution.get("field_name", "") or ""),
        "canonical_payload_present": canonical_present,
        "compatibility_payload_present": compatibility_present,
        "used_compatibility_fallback_v1": used_fallback,
        "compatibility_role": str(CONSUMER_MIGRATION_FREEZE_V1["compatibility_role"]),
        "fallback_allowed_only_when_canonical_missing": bool(
            CONSUMER_MIGRATION_FREEZE_V1["fallback_allowed_only_when_canonical_missing"]
        ),
        "canonical_shadow_rebuild_active": bool(used_fallback and (not canonical_present) and compatibility_present),
        "compatibility_field_can_own_identity": False,
        "live_runtime_branch_on_compatibility_field_allowed": bool(
            CONSUMER_MIGRATION_FREEZE_V1["live_runtime_branch_on_compatibility_field_allowed"]
        ),
        "identity_ownership_preserved": True,
    }


def resolve_consumer_layer_mode_policy_resolution(container: Any) -> dict[str, Any]:
    metadata = _consumer_metadata(container)
    if not isinstance(metadata, Mapping):
        return {
            "payload": {},
            "field_name": "",
            "contract_version": CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"],
        }

    prs_log_contract = metadata.get("prs_log_contract_v2")
    if not isinstance(prs_log_contract, Mapping):
        prs_log_contract = {}

    candidate_fields: list[str] = []
    for field_name in (
        prs_log_contract.get("layer_mode_policy_output_field"),
        CONSUMER_LAYER_MODE_INTEGRATION_V1["canonical_policy_field"],
    ):
        normalized = str(field_name or "").strip()
        if normalized and normalized not in candidate_fields:
            candidate_fields.append(normalized)

    for field_name in candidate_fields:
        payload = _coerce_layer_mode_policy_payload(metadata.get(field_name))
        if _looks_like_layer_mode_policy_payload(payload):
            return {
                "payload": payload,
                "field_name": field_name,
                "contract_version": CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"],
            }

    return {
        "payload": {},
        "field_name": "",
        "contract_version": CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"],
    }


def resolve_consumer_layer_mode_policy_input(container: Any) -> dict[str, Any]:
    return dict(resolve_consumer_layer_mode_policy_resolution(container).get("payload", {}) or {})


def resolve_consumer_handoff_payload(
    container: Any,
    *,
    market_mode: str = "",
    prior_archetype_id: str = "",
    prior_side: str = "",
    prior_invalidation_id: str = "",
    cooldown_active: bool | None = None,
    box_state: str = "",
    bb_state: str = "",
) -> dict[str, Any]:
    metadata = _consumer_metadata(container)
    observe_confirm_resolution = resolve_consumer_observe_confirm_resolution(metadata)
    observe_confirm = dict(observe_confirm_resolution.get("payload", {}) or {})
    layer_mode_policy_resolution = resolve_consumer_layer_mode_policy_resolution(metadata)
    layer_mode_policy = dict(layer_mode_policy_resolution.get("payload", {}) or {})
    energy_helper = _coerce_energy_helper_payload(metadata.get(CONSUMER_INPUT_CONTRACT_V1["canonical_energy_field"]))

    current_action = str(observe_confirm.get("action", "") or "").strip().upper()
    current_side = str(observe_confirm.get("side", "") or "").strip().upper()
    if current_side not in {"BUY", "SELL"} and current_action in {"BUY", "SELL"}:
        current_side = current_action

    base: Mapping[str, Any]
    if isinstance(container, Mapping):
        base = container
    else:
        base = metadata

    market_mode_value = str(
        base.get("market_mode", "")
        or metadata.get("market_mode", "")
        or market_mode
        or ""
    ).strip().upper()
    reason_value = str(observe_confirm.get("reason", "") or "").strip()
    archetype_id_value = str(observe_confirm.get("archetype_id", "") or "").strip().lower()

    setup_mapping_input = {
        "archetype_id": archetype_id_value,
        "side": current_side,
        "reason": reason_value,
        "market_mode": market_mode_value,
    }

    setup_mapping = resolve_setup_mapping(
        archetype_id=setup_mapping_input["archetype_id"],
        side=setup_mapping_input["side"],
        market_mode=setup_mapping_input["market_mode"],
        reason=setup_mapping_input["reason"],
    )
    exit_handoff = resolve_exit_handoff(base)
    re_entry_handoff = resolve_re_entry_handoff(
        base,
        prior_archetype_id=prior_archetype_id,
        prior_side=prior_side,
        prior_invalidation_id=prior_invalidation_id,
        cooldown_active=cooldown_active,
        box_state=box_state,
        bb_state=bb_state,
    )

    required_fields = set(CONSUMER_INPUT_CONTRACT_V1["required_handoff_fields"])
    canonical_only_ready = bool(required_fields.issubset({str(k) for k in observe_confirm.keys()}))

    return {
        "observe_confirm_resolution": dict(observe_confirm_resolution),
        "observe_confirm": observe_confirm,
        "layer_mode_policy_resolution": dict(layer_mode_policy_resolution),
        "layer_mode_policy": layer_mode_policy,
        "energy_helper": dict(energy_helper),
        "setup_mapping_input": setup_mapping_input,
        "setup_mapping": dict(setup_mapping),
        "exit_handoff": dict(exit_handoff),
        "re_entry_handoff": dict(re_entry_handoff),
        "canonical_only_ready": canonical_only_ready,
        "policy_input_ready": _looks_like_layer_mode_policy_payload(layer_mode_policy),
        "policy_identity_preserved": bool(layer_mode_policy.get("identity_preserved", False)),
        "used_compatibility_fallback_v1": bool(observe_confirm_resolution.get("used_fallback_v1", False)),
        "semantic_reinterpretation_required": False,
        "layer_mode_overlay_ready": bool(CONSUMER_FREEZE_HANDOFF_V1["future_policy_overlay"]["layer_mode_ready"]),
        "contract_version": CONSUMER_FREEZE_HANDOFF_V1["contract_version"],
    }


def resolve_setup_mapping(
    *,
    archetype_id: str,
    side: str,
    market_mode: str = "",
    reason: str = "",
) -> dict[str, Any]:
    archetype_u = str(archetype_id or "").strip().lower()
    side_u = str(side or "").strip().upper()
    market_mode_u = str(market_mode or "").strip().upper()
    reason_u = str(reason or "").strip().lower()

    base_mapping = {
        ("upper_reject_sell", "SELL"): "range_upper_reversal_sell",
        ("upper_break_buy", "BUY"): "breakout_retest_buy",
        ("lower_hold_buy", "BUY"): "range_lower_reversal_buy",
        ("lower_break_sell", "SELL"): "breakout_retest_sell",
        ("mid_reclaim_buy", "BUY"): "range_lower_reversal_buy",
        ("mid_lose_sell", "SELL"): "range_upper_reversal_sell",
    }

    setup_id = base_mapping.get((archetype_u, side_u), "")
    rule_id = "unmapped"
    specialization_basis: list[str] = []

    if not setup_id:
        return {
            "setup_id": "",
            "rule_id": rule_id,
            "specialized": False,
            "specialization_basis": specialization_basis,
            "mapping_contract_version": SETUP_MAPPING_CONTRACT_V1["contract_version"],
            "archetype_id": archetype_u,
            "side": side_u,
        }

    specialized = False
    if archetype_u == "mid_reclaim_buy" and side_u == "BUY":
        rule_id = "mid_reclaim_buy_range_default"
        if reason_u.startswith("trend_pullback_buy"):
            setup_id = "trend_pullback_buy"
            rule_id = "mid_reclaim_buy_reason_trend_pullback"
            specialization_basis.append("reason_prefix:trend_pullback_buy")
            specialized = True
        elif reason_u.startswith("failed_sell_reclaim_buy"):
            setup_id = "trend_pullback_buy"
            rule_id = "mid_reclaim_buy_reason_failed_sell_reclaim"
            specialization_basis.append("reason_prefix:failed_sell_reclaim_buy")
            specialized = True
        elif market_mode_u == "TREND":
            setup_id = "trend_pullback_buy"
            rule_id = "mid_reclaim_buy_market_mode_trend"
            specialization_basis.append("market_mode:TREND")
            specialized = True
    elif archetype_u == "mid_lose_sell" and side_u == "SELL":
        rule_id = "mid_lose_sell_range_default"
        if reason_u.startswith("trend_pullback_sell"):
            setup_id = "trend_pullback_sell"
            rule_id = "mid_lose_sell_reason_trend_pullback"
            specialization_basis.append("reason_prefix:trend_pullback_sell")
            specialized = True
        elif market_mode_u == "TREND":
            setup_id = "trend_pullback_sell"
            rule_id = "mid_lose_sell_market_mode_trend"
            specialization_basis.append("market_mode:TREND")
            specialized = True
    else:
        rule_id = f"{archetype_u}_default"

    return {
        "setup_id": setup_id,
        "rule_id": rule_id,
        "specialized": specialized,
        "specialization_basis": specialization_basis,
        "mapping_contract_version": SETUP_MAPPING_CONTRACT_V1["contract_version"],
        "archetype_id": archetype_u,
        "side": side_u,
    }


def classify_entry_guard_reason(reason: str) -> dict[str, Any]:
    reason_s = str(reason or "").strip()
    if not reason_s:
        return {
            "reason": "",
            "kind": "",
            "source_layer": "",
            "is_execution_block": False,
            "is_semantic_non_action": False,
            "canonical": False,
        }

    registry = {
        item["reason"]: item
        for item in ENTRY_GUARD_CONTRACT_V1["reason_registry"]
        if isinstance(item, Mapping) and str(item.get("reason", "")).strip()
    }
    matched = registry.get(reason_s)
    if matched:
        payload = dict(matched)
        payload["canonical"] = True
        return payload

    return {
        "reason": reason_s,
        "kind": str(ENTRY_GUARD_CONTRACT_V1["passthrough_policy"]["kind"]),
        "source_layer": str(ENTRY_GUARD_CONTRACT_V1["passthrough_policy"]["source_layer"]),
        "is_execution_block": False,
        "is_semantic_non_action": True,
        "canonical": False,
    }


def resolve_consumer_guard_result(*, effective_action: str, block_kind: str) -> str:
    action_u = str(effective_action or "").strip().upper()
    block_kind_s = str(block_kind or "").strip().lower()
    if action_u in {"BUY", "SELL"}:
        return "PASS"
    if "execution" in block_kind_s:
        return "EXECUTION_BLOCK"
    return "SEMANTIC_NON_ACTION"


def resolve_exit_handoff(container: Any) -> dict[str, Any]:
    metadata = _consumer_metadata(container)
    observe_confirm = resolve_consumer_observe_confirm_input(metadata)

    base: Mapping[str, Any]
    if isinstance(container, Mapping):
        base = container
    else:
        base = metadata

    management_profile_id = str(
        base.get("management_profile_id", "")
        or metadata.get("management_profile_id", "")
        or observe_confirm.get("management_profile_id", "")
        or ""
    ).strip().lower()
    invalidation_id = str(
        base.get("invalidation_id", "")
        or metadata.get("invalidation_id", "")
        or observe_confirm.get("invalidation_id", "")
        or ""
    ).strip().lower()
    entry_setup_id = str(
        base.get("entry_setup_id", "")
        or metadata.get("entry_setup_id", "")
        or ""
    ).strip().lower()
    exit_profile = str(
        base.get("exit_profile", "")
        or metadata.get("exit_profile", "")
        or ""
    ).strip().lower()

    if management_profile_id or invalidation_id:
        handoff_source = "canonical_entry_handoff"
    elif entry_setup_id or exit_profile:
        handoff_source = "legacy_setup_fallback"
    else:
        handoff_source = "missing"

    return {
        "management_profile_id": management_profile_id,
        "invalidation_id": invalidation_id,
        "entry_setup_id": entry_setup_id,
        "exit_profile": exit_profile,
        "handoff_source": handoff_source,
        "contract_version": EXIT_HANDOFF_CONTRACT_V1["contract_version"],
    }


def resolve_re_entry_handoff(
    container: Any,
    *,
    prior_archetype_id: str = "",
    prior_side: str = "",
    prior_invalidation_id: str = "",
    cooldown_active: bool | None = None,
    box_state: str = "",
    bb_state: str = "",
) -> dict[str, Any]:
    metadata = _consumer_metadata(container)
    observe_confirm = resolve_consumer_observe_confirm_input(metadata)

    base: Mapping[str, Any]
    if isinstance(container, Mapping):
        base = container
    else:
        base = metadata

    current_state = str(observe_confirm.get("state", "") or "").strip().upper()
    current_action = str(observe_confirm.get("action", "") or "").strip().upper()
    current_side = str(
        observe_confirm.get("side", "") or (current_action if current_action in {"BUY", "SELL"} else "")
    ).strip().upper()
    current_archetype_id = str(observe_confirm.get("archetype_id", "") or "").strip().lower()
    prior_archetype_id_v = str(
        base.get("prior_entry_archetype_id", "")
        or metadata.get("prior_entry_archetype_id", "")
        or prior_archetype_id
        or ""
    ).strip().lower()
    prior_side_v = str(
        base.get("prior_entry_side", "")
        or metadata.get("prior_entry_side", "")
        or prior_side
        or ""
    ).strip().upper()
    prior_invalidation_id_v = str(
        base.get("prior_invalidation_id", "")
        or metadata.get("prior_invalidation_id", "")
        or prior_invalidation_id
        or ""
    ).strip().lower()
    box_state_v = str(base.get("box_state", "") or metadata.get("box_state", "") or box_state or "").strip().upper()
    bb_state_v = str(base.get("bb_state", "") or metadata.get("bb_state", "") or bb_state or "").strip().upper()

    cooldown_raw = (
        base.get("re_entry_cooldown_active", None)
        if cooldown_active is None
        else cooldown_active
    )
    if cooldown_raw is None:
        cooldown_raw = metadata.get("re_entry_cooldown_active", False)
    if isinstance(cooldown_raw, str):
        cooldown_active_v = str(cooldown_raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    else:
        cooldown_active_v = bool(cooldown_raw)

    same_archetype_confirmed = bool(
        current_state == str(RE_ENTRY_CONTRACT_V1["required_current_state"]["state"]).upper()
        and current_action in {"BUY", "SELL"}
        and current_side in {"BUY", "SELL"}
        and current_archetype_id
        and current_archetype_id == prior_archetype_id_v
        and current_side == prior_side_v
    )
    persistence_ok = bool(same_archetype_confirmed)
    middle_reentry_forbidden = bool(
        box_state_v in set(RE_ENTRY_CONTRACT_V1["forbidden_middle_contexts"]["box_state"])
        or bb_state_v in set(RE_ENTRY_CONTRACT_V1["forbidden_middle_contexts"]["bb_state"])
    )
    reverse_after_invalidation_forbidden = bool(
        prior_invalidation_id_v
        and prior_side_v in {"BUY", "SELL"}
        and current_side in {"BUY", "SELL"}
        and current_side != prior_side_v
    )
    cooldown_ok = not cooldown_active_v

    if not prior_archetype_id_v or not prior_side_v:
        blocked_reason = "reentry_missing_prior_context"
    elif middle_reentry_forbidden:
        blocked_reason = "reentry_middle_averaging_forbidden"
    elif reverse_after_invalidation_forbidden:
        blocked_reason = "reentry_immediate_reverse_after_invalidation_forbidden"
    elif not persistence_ok:
        blocked_reason = "reentry_same_archetype_confirm_required"
    elif not cooldown_ok:
        blocked_reason = "reentry_cooldown_active"
    else:
        blocked_reason = ""

    registry = {
        str(item.get("reason", "")): item
        for item in RE_ENTRY_CONTRACT_V1["blocked_reason_registry"]
        if isinstance(item, Mapping) and str(item.get("reason", "")).strip()
    }
    blocked_meta = dict(registry.get(blocked_reason, {}) or {})

    return {
        "eligible": blocked_reason == "",
        "blocked_reason": blocked_reason,
        "blocked_reason_kind": str(blocked_meta.get("kind", "") or ""),
        "blocked_reason_dimension": str(blocked_meta.get("dimension", "") or ""),
        "same_archetype_confirmed": same_archetype_confirmed,
        "persistence_ok": persistence_ok,
        "cooldown_ok": cooldown_ok,
        "middle_reentry_forbidden": middle_reentry_forbidden,
        "reverse_after_invalidation_forbidden": reverse_after_invalidation_forbidden,
        "current_archetype_id": current_archetype_id,
        "current_side": current_side,
        "prior_archetype_id": prior_archetype_id_v,
        "prior_side": prior_side_v,
        "prior_invalidation_id": prior_invalidation_id_v,
        "box_state": box_state_v,
        "bb_state": bb_state_v,
        "contract_version": RE_ENTRY_CONTRACT_V1["contract_version"],
    }


def consumer_input_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_INPUT_CONTRACT_V1["documentation_path"]


def consumer_layer_mode_integration_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_LAYER_MODE_INTEGRATION_V1["documentation_path"]


def consumer_migration_freeze_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_MIGRATION_FREEZE_V1["documentation_path"]


def setup_detector_responsibility_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / SETUP_DETECTOR_RESPONSIBILITY_CONTRACT_V1["documentation_path"]


def setup_mapping_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / SETUP_MAPPING_CONTRACT_V1["documentation_path"]


def entry_service_responsibility_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1["documentation_path"]


def entry_guard_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / ENTRY_GUARD_CONTRACT_V1["documentation_path"]


def exit_handoff_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / EXIT_HANDOFF_CONTRACT_V1["documentation_path"]


def re_entry_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / RE_ENTRY_CONTRACT_V1["documentation_path"]


def consumer_logging_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_LOGGING_CONTRACT_V1["documentation_path"]


def consumer_test_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_TEST_CONTRACT_V1["documentation_path"]


def consumer_freeze_handoff_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_FREEZE_HANDOFF_V1["documentation_path"]


def consumer_scope_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / CONSUMER_SCOPE_CONTRACT_V1["documentation_path"]
