import json

import backend.services.state_flow_f0_chain_alignment_audit as service


def test_state_flow_f0_chain_alignment_contract_exposes_core_fields():
    contract = service.build_state_flow_f0_chain_alignment_contract_v1()
    assert contract["contract_version"] == "state_flow_f0_chain_alignment_contract_v1"
    assert "state_flow_f0_raw_vs_effective_state_v1" in contract["row_level_fields_v1"]
    assert "state_flow_f0_effective_vs_audit_state_v1" in contract["row_level_fields_v1"]


def test_state_flow_f0_chain_alignment_row_ready_when_missing_fields_are_explainable():
    row = service.build_state_flow_f0_chain_alignment_row_v1(
        {
            "symbol": "XAUUSD",
            "symbol_state_strength_best_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
            "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
            "symbol_state_strength_profile_match_v1": "OUT_OF_PROFILE",
            "previous_box_break_state": "BREAKOUT_HELD",
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "lifecycle_canary_candidate_state_v1": "",
            "xau_lifecycle_canary_risk_gate_v1": "",
            "xau_lifecycle_canary_scope_detail_v1": "",
        }
    )

    assert row["state_flow_f0_chain_alignment_state_v1"] == "READY"
    assert row["state_flow_f0_raw_vs_effective_state_v1"] == "PERSISTED_FIELDS_MISSING"
    assert row["state_flow_f0_effective_vs_audit_state_v1"] == "CONSISTENT"
    assert row["state_flow_f0_primary_divergence_layer_v1"] in {
        "SYMBOL_CALIBRATION",
        "BOUNDED_LIFECYCLE_CANARY",
    }


def test_state_flow_f0_chain_alignment_row_blocked_on_effective_vs_audit_conflict(monkeypatch):
    def _fake_effective(_row):
        return {
            "symbol": "XAUUSD",
            "symbol_state_strength_best_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
            "symbol_state_strength_flow_support_state_v1": "FLOW_UNCONFIRMED",
            "symbol_state_strength_aggregate_conviction_v1": 0.34,
            "symbol_state_strength_flow_persistence_v1": 0.41,
            "xau_state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
            "lifecycle_canary_candidate_state_v1": "OBSERVE_ONLY",
            "xau_lifecycle_canary_risk_gate_v1": "FAIL_PILOT_MATCH",
            "xau_lifecycle_canary_scope_detail_v1": "XAU_DELAY_ENTRY_OBSERVE",
        }

    def _fake_audit(_row):
        return {
            "xau_gate_failure_stage_v1": "PILOT_MATCH",
            "xau_gate_saved_vs_effective_state_v1": "CONSISTENT",
            "xau_gate_effective_candidate_state_v1": "BOUNDED_READY",
            "xau_gate_effective_risk_gate_v1": "PASS",
            "xau_gate_effective_scope_detail_v1": "XAU_HOLD_REDUCE",
            "xau_gate_effective_flow_support_state_v1": "FLOW_CONFIRMED",
            "xau_gate_effective_aggregate_conviction_v1": 0.82,
            "xau_gate_effective_flow_persistence_v1": 0.73,
        }

    monkeypatch.setattr(service, "recompute_xau_effective_chain_row_v1", _fake_effective)
    monkeypatch.setattr(service, "build_xau_refined_gate_timebox_audit_row_v1", _fake_audit)

    row = service.build_state_flow_f0_chain_alignment_row_v1({"symbol": "XAUUSD"})
    assert row["state_flow_f0_chain_alignment_state_v1"] == "BLOCKED"
    assert row["state_flow_f0_effective_vs_audit_state_v1"] == "CONFLICT"
    assert row["state_flow_f0_primary_divergence_layer_v1"] == "XAU_REFINED_GATE_AUDIT"


def test_generate_and_write_state_flow_f0_chain_alignment_summary_writes_artifacts(tmp_path):
    report = service.generate_and_write_state_flow_f0_chain_alignment_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "symbol_state_strength_best_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
                "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
                "symbol_state_strength_profile_match_v1": "OUT_OF_PROFILE",
                "previous_box_break_state": "BREAKOUT_HELD",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "state_flow_f0_chain_alignment_latest.json"
    md_path = tmp_path / "state_flow_f0_chain_alignment_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["xau_row_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
