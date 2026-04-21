import json

from backend.services.bounded_lifecycle_canary import (
    build_bounded_lifecycle_canary_contract_v1,
    attach_bounded_lifecycle_canary_fields_v1,
    generate_and_write_bounded_lifecycle_canary_summary_v1,
)


def test_bounded_lifecycle_canary_contract_exposes_candidate_fields():
    contract = build_bounded_lifecycle_canary_contract_v1()
    assert contract["contract_version"] == "bounded_lifecycle_canary_contract_v1"
    assert "lifecycle_canary_candidate_state_v1" in contract["row_level_fields_v1"]


def test_attach_bounded_lifecycle_canary_fields_marks_xau_ready_when_aligned():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "execution_policy_shadow_audit_profile_v1": {
                "contract_version": "execution_policy_shadow_audit_contract_v1",
            },
            "lifecycle_policy_alignment_state_v1": "ALIGNED",
            "state_slot_execution_policy_source_v1": "BRIDGE_BIAS",
            "entry_policy_v1": "DELAYED_ENTRY",
            "hold_policy_v1": "STRONG_HOLD",
            "reduce_policy_v1": "REDUCE_STRONG",
            "exit_policy_v1": "EXIT_PREP",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "xau_ambiguity_level_v1": "LOW",
            "xau_texture_slot_v1": "WITH_FRICTION",
        }
    }
    enriched = attach_bounded_lifecycle_canary_fields_v1(rows)
    row = enriched["XAUUSD"]
    assert row["lifecycle_canary_candidate_state_v1"] == "BOUNDED_READY"
    assert row["lifecycle_canary_scope_v1"] == "XAU_SINGLE_SYMBOL"
    assert row["lifecycle_canary_policy_slice_v1"] == "HOLD_REDUCE_ONLY"
    assert row["xau_lifecycle_canary_risk_gate_v1"] == "PASS"
    assert row["xau_lifecycle_canary_scope_detail_v1"] == "XAU_HOLD_REDUCE"


def test_attach_bounded_lifecycle_canary_fields_keeps_xau_observe_only_when_gate_fails():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "execution_policy_shadow_audit_profile_v1": {
                "contract_version": "execution_policy_shadow_audit_contract_v1",
            },
            "lifecycle_policy_alignment_state_v1": "ALIGNED",
            "state_slot_execution_policy_source_v1": "BRIDGE_BIAS",
            "entry_policy_v1": "DELAYED_ENTRY",
            "hold_policy_v1": "STRONG_HOLD",
            "reduce_policy_v1": "LIGHT_REDUCE",
            "exit_policy_v1": "EXIT_WATCH",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "xau_ambiguity_level_v1": "HIGH",
            "xau_texture_slot_v1": "WITH_FRICTION",
        }
    }
    enriched = attach_bounded_lifecycle_canary_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["lifecycle_canary_candidate_state_v1"] == "OBSERVE_ONLY"
    assert row["xau_lifecycle_canary_risk_gate_v1"] == "FAIL_AMBIGUITY"
    assert row["xau_lifecycle_canary_scope_detail_v1"] == "XAU_DELAY_ENTRY_OBSERVE"


def test_attach_bounded_lifecycle_canary_fields_allows_flow_confirmed_xau_even_when_out_of_profile():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "execution_policy_shadow_audit_profile_v1": {
                "contract_version": "execution_policy_shadow_audit_contract_v1",
            },
            "lifecycle_policy_alignment_state_v1": "ALIGNED",
            "state_slot_execution_policy_source_v1": "BRIDGE_BIAS",
            "entry_policy_v1": "DELAYED_ENTRY",
            "hold_policy_v1": "STRONG_HOLD",
            "reduce_policy_v1": "REDUCE_STRONG",
            "exit_policy_v1": "EXIT_PREP",
            "xau_pilot_window_match_v1": "OUT_OF_PROFILE",
            "xau_ambiguity_level_v1": "LOW",
            "xau_texture_slot_v1": "WITH_FRICTION",
            "symbol_state_strength_flow_support_state_v1": "FLOW_CONFIRMED",
            "symbol_state_strength_aggregate_conviction_v1": 0.74,
            "symbol_state_strength_flow_persistence_v1": 0.67,
        }
    }
    enriched = attach_bounded_lifecycle_canary_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["lifecycle_canary_candidate_state_v1"] == "BOUNDED_READY"
    assert row["xau_lifecycle_canary_risk_gate_v1"] == "PASS_FLOW_CONFIRMED"
    assert row["xau_lifecycle_canary_scope_detail_v1"] == "XAU_HOLD_REDUCE"


def test_generate_and_write_bounded_lifecycle_canary_summary_writes_artifacts(tmp_path):
    report = generate_and_write_bounded_lifecycle_canary_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "execution_policy_shadow_audit_profile_v1": {
                    "contract_version": "execution_policy_shadow_audit_contract_v1",
                },
                "lifecycle_policy_alignment_state_v1": "REVIEW_PENDING",
                "state_slot_execution_policy_source_v1": "COMMON_SLOT_DERIVED",
                "entry_policy_v1": "DELAYED_ENTRY",
                "hold_policy_v1": "HOLD_FAVOR",
                "reduce_policy_v1": "REDUCE_STRONG",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "bounded_lifecycle_canary_latest.json"
    md_path = tmp_path / "bounded_lifecycle_canary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
