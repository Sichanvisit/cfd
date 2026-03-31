from __future__ import annotations

import copy
from pathlib import Path


RUNTIME_ALIGNMENT_SCOPE_FREEZE_V1 = {
    "contract_version": "runtime_alignment_scope_freeze_v1",
    "scope": "doc_code_alignment_only",
    "objective": "Align runtime ownership and live handoff behavior with the documented Position-to-Energy architecture without introducing a new meaning layer.",
    "target_document": "docs/position_to_energy_handoff_ko.md",
    "priority_order": [
        {
            "order": 1,
            "focus": "identity_ownership",
            "owner": "observe_confirm",
        },
        {
            "order": 2,
            "focus": "live_consumer_wiring",
            "owner": "consumer",
        },
        {
            "order": 3,
            "focus": "truthful_logging",
            "owner": "energy_logging_replay",
        },
    ],
    "in_scope": [
        "detach legacy energy_snapshot from observe_confirm identity ownership",
        "make consumer live decisions read observe_confirm identity plus layer_mode policy plus energy helper hints",
        "record only actual consumer energy usage in replay and logging traces",
        "re-freeze docs after runtime ownership matches implementation",
    ],
    "non_goals": [
        "introduce a new semantic layer",
        "redefine the semantic foundation",
        "promote net_utility into a direct order gate",
        "remove compatibility bridges before runtime alignment is verified",
    ],
    "frozen_invariants": [
        "observe_confirm remains the canonical identity owner",
        "layer_mode remains the policy overlay above raw semantic outputs",
        "energy remains a post-layer-mode helper only",
    ],
    "runtime_embedding_field": "runtime_alignment_scope_contract_v1",
    "documentation_path": "docs/runtime_alignment_scope_contract.md",
}


RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1 = {
    "contract_version": "runtime_alignment_scope_v1",
    "scope": "runtime_alignment_hardening_only",
    "scope_freeze_v1": copy.deepcopy(RUNTIME_ALIGNMENT_SCOPE_FREEZE_V1),
    "goals": [
        "observe_confirm owns identity without legacy energy_snapshot",
        "consumer reads observe_confirm plus layer_mode plus energy in the live decision path",
        "energy logging records actual consumer usage only",
        "position_to_energy_handoff_ko.md matches runtime code behavior",
    ],
    "target_components": [
        {
            "component": "ObserveConfirm",
            "owner_question": "who owns identity and lifecycle",
            "runtime_files": [
                "backend/services/context_classifier.py",
                "backend/trading/engine/core/observe_confirm_router.py",
            ],
        },
        {
            "component": "Consumer",
            "owner_question": "who applies identity plus policy plus utility hints in live execution",
            "runtime_files": [
                "backend/services/entry_service.py",
                "backend/services/wait_engine.py",
                "backend/services/setup_detector.py",
            ],
        },
        {
            "component": "EnergyLogging",
            "owner_question": "who records actual helper consumption for replay",
            "runtime_files": [
                "backend/services/energy_contract.py",
                "backend/services/entry_service.py",
                "backend/services/entry_engines.py",
            ],
        },
    ],
    "official_runtime_embedding_field": "runtime_alignment_scope_contract_v1",
    "prs_log_contract_field": "runtime_alignment_scope_contract_field",
    "implementation_sequence": [
        "14.0_scope_freeze",
        "14.1_observe_confirm_legacy_energy_detach",
        "14.2_observe_confirm_semantic_routing_hardening",
        "14.3_entry_service_consumer_stack_activation",
        "14.4_wait_engine_hint_activation",
        "14.5_truthful_consumer_usage_logging",
        "14.6_compatibility_migration_guard",
        "14.7_test_hardening",
        "14.8_docs_handoff_refreeze",
    ],
    "completed_definitions": [
        "14.0_scope_freeze",
        "14.1_observe_confirm_legacy_energy_detach",
        "14.2_observe_confirm_semantic_routing_hardening",
        "14.3_entry_service_consumer_stack_activation",
        "14.4_wait_engine_hint_activation",
        "14.5_truthful_consumer_usage_logging",
        "14.6_compatibility_migration_guard",
        "14.7_test_hardening",
        "14.8_docs_handoff_refreeze",
    ],
    "deferred_definitions": [],
    "documentation_path": "docs/runtime_alignment_scope_contract.md",
}


def runtime_alignment_scope_contract_doc_path(project_root: str | Path) -> Path:
    return Path(project_root) / RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["documentation_path"]
