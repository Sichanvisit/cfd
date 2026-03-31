from backend.services.runtime_alignment_contract import (
    RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1,
    RUNTIME_ALIGNMENT_SCOPE_FREEZE_V1,
)


def test_runtime_alignment_scope_freeze_contract_is_locked():
    assert RUNTIME_ALIGNMENT_SCOPE_FREEZE_V1 == {
        "contract_version": "runtime_alignment_scope_freeze_v1",
        "scope": "doc_code_alignment_only",
        "objective": (
            "Align runtime ownership and live handoff behavior with the documented "
            "Position-to-Energy architecture without introducing a new meaning layer."
        ),
        "target_document": "docs/position_to_energy_handoff_ko.md",
        "priority_order": [
            {"order": 1, "focus": "identity_ownership", "owner": "observe_confirm"},
            {"order": 2, "focus": "live_consumer_wiring", "owner": "consumer"},
            {"order": 3, "focus": "truthful_logging", "owner": "energy_logging_replay"},
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


def test_runtime_alignment_scope_contract_tracks_completed_runtime_alignment_up_to_14_8():
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["contract_version"] == "runtime_alignment_scope_v1"
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["scope"] == "runtime_alignment_hardening_only"
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["scope_freeze_v1"] == RUNTIME_ALIGNMENT_SCOPE_FREEZE_V1
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["official_runtime_embedding_field"] == (
        "runtime_alignment_scope_contract_v1"
    )
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["prs_log_contract_field"] == (
        "runtime_alignment_scope_contract_field"
    )
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["completed_definitions"] == [
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
    assert RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["deferred_definitions"] == []
    assert [item["component"] for item in RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["target_components"]] == [
        "ObserveConfirm",
        "Consumer",
        "EnergyLogging",
    ]
