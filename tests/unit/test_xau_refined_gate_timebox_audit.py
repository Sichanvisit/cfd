import json

from backend.services.xau_refined_gate_timebox_audit import (
    build_xau_refined_gate_timebox_audit_contract_v1,
    attach_xau_refined_gate_timebox_audit_fields_v1,
    generate_and_write_xau_refined_gate_timebox_audit_summary_v1,
)


def test_xau_refined_gate_timebox_audit_contract_exposes_comparison_fields():
    contract = build_xau_refined_gate_timebox_audit_contract_v1()
    assert contract["contract_version"] == "xau_refined_gate_timebox_audit_contract_v1"
    assert "xau_gate_saved_vs_effective_state_v1" in contract["row_level_fields_v1"]


def test_attach_xau_refined_gate_timebox_audit_fields_detects_pilot_match_failure_with_missing_persisted_fields():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "symbol_state_strength_best_profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
            "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
            "symbol_state_strength_profile_match_v1": "NO_MATCH",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "previous_box_break_state": "BREAKOUT_HELD",
            "box_state": "ABOVE",
            "bb_state": "UPPER_EDGE",
            "lifecycle_canary_candidate_state_v1": None,
            "xau_lifecycle_canary_risk_gate_v1": None,
            "xau_lifecycle_canary_scope_detail_v1": None,
        }
    }

    enriched = attach_xau_refined_gate_timebox_audit_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["xau_gate_timebox_audit_state_v1"] == "READY"
    assert row["xau_gate_failure_stage_v1"] == "PILOT_MATCH"
    assert row["xau_gate_failure_primary_driver_v1"] == "FAIL_PILOT_MATCH"
    assert row["xau_gate_saved_vs_effective_state_v1"] == "PERSISTED_FIELDS_MISSING"
    assert row["xau_gate_effective_candidate_state_v1"] == "OBSERVE_ONLY"
    assert row["xau_gate_effective_risk_gate_v1"] == "FAIL_PILOT_MATCH"


def test_generate_and_write_xau_refined_gate_timebox_audit_summary_writes_artifacts(tmp_path):
    report = generate_and_write_xau_refined_gate_timebox_audit_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "symbol_state_strength_best_profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
                "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
                "symbol_state_strength_profile_match_v1": "NO_MATCH",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "previous_box_break_state": "BREAKOUT_HELD",
                "box_state": "ABOVE",
                "bb_state": "UPPER_EDGE",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "xau_refined_gate_timebox_audit_latest.json"
    md_path = tmp_path / "xau_refined_gate_timebox_audit_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["xau_row_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
