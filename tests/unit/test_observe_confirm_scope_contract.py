from pathlib import Path

from backend.services.observe_confirm_contract import (
    OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2,
    OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2,
    OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2,
    OBSERVE_CONFIRM_FREEZE_HANDOFF_V1,
    OBSERVE_CONFIRM_INPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2,
    OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2,
    OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1,
    OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2,
    OBSERVE_CONFIRM_ROUTING_POLICY_V2,
    OBSERVE_CONFIRM_STATE_SEMANTICS_V2,
    OBSERVE_CONFIRM_SCOPE_CONTRACT_V1,
    OBSERVE_CONFIRM_TEST_CONTRACT_V1,
    observe_confirm_action_side_semantics_doc_path,
    observe_confirm_archetype_taxonomy_doc_path,
    observe_confirm_confidence_semantics_doc_path,
    observe_confirm_freeze_handoff_doc_path,
    observe_confirm_input_contract_doc_path,
    observe_confirm_invalidation_taxonomy_doc_path,
    observe_confirm_management_profile_taxonomy_doc_path,
    observe_confirm_migration_dual_write_doc_path,
    observe_confirm_output_contract_doc_path,
    observe_confirm_routing_policy_doc_path,
    observe_confirm_state_semantics_doc_path,
    observe_confirm_scope_contract_doc_path,
    observe_confirm_test_contract_doc_path,
)
from backend.trading.engine.core.models import ObserveConfirmSnapshot


def test_observe_confirm_scope_contract_freezes_responsibility_boundary():
    contract = OBSERVE_CONFIRM_SCOPE_CONTRACT_V1

    assert contract["contract_version"] == "observe_confirm_scope_v1"
    assert contract["scope"] == "semantic_archetype_routing_only"
    assert contract["canonical_output_field"] == "observe_confirm_v2"
    assert contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert "determine whether the current semantic state is observe, confirm, or no-trade for a candidate trade archetype" in contract["responsibilities"]
    assert "setup naming" in contract["non_responsibilities"]
    assert "entry guard or execution gating" in contract["non_responsibilities"]
    assert "exit rule selection" in contract["non_responsibilities"]
    assert "re-entry authorization" in contract["non_responsibilities"]
    assert contract["consumer_boundary"]["setup_detector"].startswith("Maps or names a confirmed archetype only")
    assert "raw_detector_direct_read" in contract["forbidden_changes"]
    assert contract["input_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_INPUT_CONTRACT_V2["contract_version"]
    assert contract["output_contract_v2"]["contract_version"] == OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["contract_version"]
    assert contract["completed_definitions"] == [
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
    ]
    assert contract["deferred_definitions"] == []


def test_observe_confirm_input_contract_v2_freezes_canonical_inputs():
    contract = OBSERVE_CONFIRM_INPUT_CONTRACT_V2

    assert contract["contract_version"] == "observe_confirm_input_contract_v2"
    assert [item["field"] for item in contract["semantic_input_fields"]] == [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ]
    assert [item["field"] for item in contract["forecast_input_fields"]] == [
        "transition_forecast_v1",
        "trade_management_forecast_v1",
        "forecast_gap_metrics_v1",
    ]
    assert "response_raw_snapshot_v1" in contract["forbidden_direct_inputs"]
    assert "state_raw_snapshot_v1" in contract["forbidden_direct_inputs"]
    assert "energy_snapshot_v1" in contract["forbidden_direct_inputs"]
    assert "legacy_rule_branch" in contract["forbidden_direct_inputs"]
    assert "raw_detector_direct_read" in contract["forbidden_practices"]
    assert "router reads canonical semantic bundle only" in contract["input_principles"]
    assert "observe_confirm_input_contract_v2" in contract["runtime_log_fields"]


def test_observe_confirm_output_contract_v2_freezes_canonical_outputs():
    contract = OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2

    assert contract["contract_version"] == "observe_confirm_output_contract_v2"
    assert contract["canonical_output_field"] == "observe_confirm_v2"
    assert contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert contract["required_fields"] == [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "metadata",
    ]
    assert contract["state_values"] == [
        "OBSERVE",
        "CONFIRM",
        "CONFLICT_OBSERVE",
        "NO_TRADE",
        "INVALIDATED",
    ]
    assert contract["action_values"] == ["WAIT", "BUY", "SELL", "NONE"]
    assert contract["side_values"] == ["BUY", "SELL", ""]
    assert contract["metadata_contract"]["required_fields"] == [
        "raw_contributions",
        "effective_contributions",
        "winning_evidence",
        "blocked_reason",
    ]
    assert contract["state_semantics_contract_v2"] == "observe_confirm_state_semantics_v2"
    assert contract["action_side_semantics_contract_v2"] == "observe_confirm_action_side_semantics_v2"
    assert contract["archetype_taxonomy_contract_v2"] == "observe_confirm_archetype_taxonomy_v2"
    assert contract["invalidation_taxonomy_contract_v2"] == "observe_confirm_invalidation_taxonomy_v2"
    assert contract["management_profile_taxonomy_contract_v2"] == "observe_confirm_management_profile_taxonomy_v2"
    assert contract["routing_policy_contract_v2"] == "observe_confirm_routing_policy_v2"
    assert contract["confidence_semantics_contract_v2"] == "observe_confirm_confidence_semantics_v2"
    assert contract["migration_dual_write_contract_v1"] == "observe_confirm_migration_dual_write_v1"
    assert contract["deferred_value_taxonomies"] == []
    assert "observe_confirm_output_contract_v2" in contract["runtime_log_fields"]


def test_observe_confirm_state_semantics_v2_freezes_lifecycle_only_state_meaning():
    contract = OBSERVE_CONFIRM_STATE_SEMANTICS_V2

    assert contract["contract_version"] == "observe_confirm_state_semantics_v2"
    assert contract["state_field"] == "state"
    assert contract["scope"] == "lifecycle_only"
    assert [item["value"] for item in contract["allowed_values"]] == [
        "OBSERVE",
        "CONFIRM",
        "CONFLICT_OBSERVE",
        "NO_TRADE",
        "INVALIDATED",
    ]
    assert "pattern or setup identity does not live in state" in [
        item.replace("`", "") for item in contract["state_principles"]
    ]
    assert contract["legacy_transition_rule"]["legacy_pattern_state_field"] == "archetype_id"
    assert contract["legacy_transition_rule"]["compatibility_shadow_field"] == "shadow_state_v1"


def test_observe_confirm_archetype_taxonomy_v2_freezes_canonical_entry_identity_set():
    contract = OBSERVE_CONFIRM_ARCHETYPE_TAXONOMY_V2

    assert contract["contract_version"] == "observe_confirm_archetype_taxonomy_v2"
    assert contract["field"] == "archetype_id"
    assert contract["principle"] == "archetype is entry identity"
    assert [item["archetype_id"] for item in contract["core_set"]] == [
        "upper_reject_sell",
        "upper_break_buy",
        "lower_hold_buy",
        "lower_break_sell",
        "mid_reclaim_buy",
        "mid_lose_sell",
    ]
    assert contract["core_set"][0]["side"] == "SELL"
    assert contract["core_set"][1]["side"] == "BUY"
    assert "observe and confirm may share the same archetype_id" in contract["router_rules"]


def test_observe_confirm_invalidation_taxonomy_v2_freezes_canonical_failure_identity_set():
    contract = OBSERVE_CONFIRM_INVALIDATION_TAXONOMY_V2

    assert contract["contract_version"] == "observe_confirm_invalidation_taxonomy_v2"
    assert contract["field"] == "invalidation_id"
    assert contract["principle"] == "invalidation is canonical failure identity, not free-text reason"
    assert [(item["archetype_id"], item["invalidation_id"]) for item in contract["canonical_mapping"]] == [
        ("upper_reject_sell", "upper_break_reclaim"),
        ("upper_break_buy", "breakout_failure"),
        ("lower_hold_buy", "lower_support_fail"),
        ("lower_break_sell", "breakdown_failure"),
        ("mid_reclaim_buy", "mid_relose"),
        ("mid_lose_sell", "mid_reclaim"),
    ]
    assert "invalidation_id is canonical contract data and must not be replaced by free-text reason strings" in contract["router_rules"]


def test_observe_confirm_management_profile_taxonomy_v2_freezes_canonical_consumer_handoff_set():
    contract = OBSERVE_CONFIRM_MANAGEMENT_PROFILE_TAXONOMY_V2

    assert contract["contract_version"] == "observe_confirm_management_profile_taxonomy_v2"
    assert contract["field"] == "management_profile_id"
    assert contract["principle"] == "management profile is canonical post-entry handling identity, not entry archetype itself"
    assert [(item["archetype_id"], item["management_profile_id"]) for item in contract["canonical_mapping"]] == [
        ("upper_reject_sell", "reversal_profile"),
        ("upper_break_buy", "breakout_hold_profile"),
        ("lower_hold_buy", "support_hold_profile"),
        ("lower_break_sell", "breakdown_hold_profile"),
        ("mid_reclaim_buy", "mid_reclaim_fast_exit_profile"),
        ("mid_lose_sell", "mid_lose_fast_exit_profile"),
    ]
    assert "management_profile_id is the official consumer and exit handoff field" in contract["router_rules"]


def test_observe_confirm_routing_policy_v2_freezes_layer_role_boundaries():
    contract = OBSERVE_CONFIRM_ROUTING_POLICY_V2

    assert contract["contract_version"] == "observe_confirm_routing_policy_v2"
    assert contract["layer_roles"]["position_response"]["role"] == "archetype_candidate_generation"
    assert contract["layer_roles"]["state"]["role"] == "regime_filter"
    assert contract["layer_roles"]["evidence"]["role"] == "setup_strength"
    assert contract["layer_roles"]["belief"]["role"] == "persistence_bias"
    assert contract["layer_roles"]["barrier"]["role"] == "action_suppression"
    assert contract["layer_roles"]["forecast"]["role"] == "confidence_modulation_and_confirm_wait_split_only"
    assert contract["identity_guard"]["identity_fields"] == ["archetype_id", "side"]
    assert contract["identity_guard"]["identity_source_layers"] == ["position_snapshot_v2", "response_vector_v2"]
    assert contract["identity_guard"]["forecast_identity_override_allowed"] is False
    assert contract["identity_guard"]["forecast_side_override_allowed"] is False
    assert "transition_forecast_v1" in contract["confirm_wait_split_policy"]["layers"]
    assert contract["confirm_wait_split_policy"]["branch_basis"] == (
        "candidate support, opposition, and suppression thresholds derived from semantic bundle inputs"
    )
    assert contract["confirm_wait_split_policy"]["forbidden_branch_basis"] == [
        "buy_force",
        "sell_force",
        "net_force",
        "energy_snapshot_v1",
    ]
    assert contract["implementation_bridge"]["semantic_readiness_bridge_v1"] == (
        "internal_readiness_from_semantic_bundle"
    )
    assert contract["implementation_bridge"]["legacy_energy_snapshot_dependency"] is False


def test_observe_confirm_confidence_semantics_v2_freezes_readiness_not_probability():
    contract = OBSERVE_CONFIRM_CONFIDENCE_SEMANTICS_V2

    assert contract["contract_version"] == "observe_confirm_confidence_semantics_v2"
    assert contract["field"] == "confidence"
    assert contract["meaning"] == "execution_readiness_score"
    assert contract["scale"] == {"type": "bounded_float", "min": 0.0, "max": 1.0}
    assert "confidence is execution readiness, not calibrated outcome probability" in contract["principles"]
    assert "the same archetype_id may emit WAIT when confidence is insufficient for confirm" in contract["principles"]
    assert contract["identity_separation"]["archetype_id_owned_elsewhere"] is True
    assert contract["identity_separation"]["wait_preserves_archetype_identity"] is True


def test_observe_confirm_migration_dual_write_v1_freezes_v1_v2_parallel_output_rule():
    contract = OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1

    assert contract["contract_version"] == "observe_confirm_migration_dual_write_v1"
    assert contract["canonical_output_field_v2"] == "observe_confirm_v2"
    assert contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert contract["consumer_read_preference"] == ["observe_confirm_v2", "observe_confirm_v1"]
    assert contract["log_required_fields"] == ["observe_confirm_v1", "observe_confirm_v2"]
    assert contract["prs_contract_fields"]["canonical_field"] == "prs_canonical_observe_confirm_field"
    assert contract["prs_contract_fields"]["compatibility_field"] == "prs_compatibility_observe_confirm_field"


def test_observe_confirm_action_side_semantics_v2_freezes_pairing_rules():
    contract = OBSERVE_CONFIRM_ACTION_SIDE_SEMANTICS_V2

    assert contract["contract_version"] == "observe_confirm_action_side_semantics_v2"
    assert contract["action_field"] == "action"
    assert contract["side_field"] == "side"
    assert contract["allowed_action_values"] == ["WAIT", "BUY", "SELL", "NONE"]
    assert contract["allowed_side_values"] == ["BUY", "SELL", ""]
    assert contract["pairing_rules"] == [
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
    ]
    assert contract["directional_observe_policy"]["allowed"] is True
    assert contract["directional_observe_policy"]["canonical_pair"] == "WAIT + BUY|SELL"


def test_observe_confirm_test_contract_v1_freezes_required_router_cases():
    contract = OBSERVE_CONFIRM_TEST_CONTRACT_V1

    assert contract["contract_version"] == "observe_confirm_test_contract_v1"
    assert contract["router_test_file"] == "tests/unit/test_observe_confirm_router_v2.py"
    assert "tests freeze semantic routing behavior, not setup naming or execution guards" in contract["principles"]
    assert [item["id"] for item in contract["required_scenarios"]] == [
        "deterministic_replay_v2",
        "semantic_bundle_only_route",
        "state_archetype_separation",
        "forecast_identity_guard",
        "barrier_confirm_suppression",
        "canonical_handoff_ids",
    ]
    assert contract["required_scenarios"][0]["assertions"] == [
        "same state",
        "same action",
        "same side",
        "same confidence",
        "same archetype_id",
        "same invalidation_id",
        "same management_profile_id",
    ]


def test_observe_confirm_freeze_handoff_v1_closes_consumer_boundary():
    contract = OBSERVE_CONFIRM_FREEZE_HANDOFF_V1

    assert contract["contract_version"] == "observe_confirm_freeze_handoff_v1"
    assert contract["consumer_entry_points"] == [
        "backend/services/setup_detector.py",
        "backend/services/entry_service.py",
    ]
    assert contract["consumer_resolution_helper"] == "resolve_observe_confirm_handoff_payload"
    assert contract["consumer_resolution_order"] == [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ]
    assert "ObserveConfirmSnapshot v2 is fixed in contract, test, and log paths" in contract["acceptance_criteria"]
    assert "consumer may not reinterpret semantic layer vectors directly" in contract["consumer_rules"]


def test_observe_confirm_snapshot_normalizes_output_metadata_defaults():
    snapshot = ObserveConfirmSnapshot(state="OBSERVE", action="WAIT")
    payload = snapshot.to_dict()

    assert payload["state"] == "OBSERVE"
    assert payload["action"] == "WAIT"
    assert payload["side"] == ""
    assert payload["confidence"] == 0.0
    assert payload["reason"] == ""
    assert payload["archetype_id"] == ""
    assert payload["invalidation_id"] == ""
    assert payload["management_profile_id"] == ""
    assert payload["metadata"] == {
        "raw_contributions": {},
        "effective_contributions": {},
        "winning_evidence": [],
        "blocked_reason": "",
    }


def test_observe_confirm_snapshot_defaults_to_none_action_and_empty_side():
    payload = ObserveConfirmSnapshot().to_dict()

    assert payload["state"] == "NO_TRADE"
    assert payload["action"] == "NONE"
    assert payload["side"] == ""


def test_observe_confirm_snapshot_preserves_directional_wait_side():
    payload = ObserveConfirmSnapshot(state="OBSERVE", action="WAIT", side="buy").to_dict()

    assert payload["state"] == "OBSERVE"
    assert payload["action"] == "WAIT"
    assert payload["side"] == "BUY"


def test_observe_confirm_scope_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_scope_contract_doc_path(root).exists()


def test_observe_confirm_input_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_input_contract_doc_path(root).exists()


def test_observe_confirm_output_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_output_contract_doc_path(root).exists()


def test_observe_confirm_state_semantics_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_state_semantics_doc_path(root).exists()


def test_observe_confirm_action_side_semantics_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_action_side_semantics_doc_path(root).exists()


def test_observe_confirm_archetype_taxonomy_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_archetype_taxonomy_doc_path(root).exists()


def test_observe_confirm_invalidation_taxonomy_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_invalidation_taxonomy_doc_path(root).exists()


def test_observe_confirm_management_profile_taxonomy_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_management_profile_taxonomy_doc_path(root).exists()


def test_observe_confirm_routing_policy_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_routing_policy_doc_path(root).exists()


def test_observe_confirm_confidence_semantics_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_confidence_semantics_doc_path(root).exists()


def test_observe_confirm_migration_dual_write_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_migration_dual_write_doc_path(root).exists()


def test_observe_confirm_test_contract_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_test_contract_doc_path(root).exists()


def test_observe_confirm_freeze_handoff_doc_exists():
    root = Path(__file__).resolve().parents[2]
    assert observe_confirm_freeze_handoff_doc_path(root).exists()
