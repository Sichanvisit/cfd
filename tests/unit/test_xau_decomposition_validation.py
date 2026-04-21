import json

from backend.services.xau_decomposition_validation import (
    attach_xau_decomposition_validation_fields_v1,
    build_xau_decomposition_validation_contract_v1,
    generate_and_write_xau_decomposition_validation_summary_v1,
)


def test_xau_decomposition_validation_contract_exposes_validation_fields():
    contract = build_xau_decomposition_validation_contract_v1()

    assert contract["contract_version"] == "xau_decomposition_validation_contract_v1"
    assert "xau_slot_alignment_state_v1" in contract["row_level_fields_v1"]
    assert contract["execution_change_allowed"] is False


def test_attach_xau_decomposition_validation_fields_surfaces_xau_alignment():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "xau_readonly_surface_profile_v1": {"contract_version": "xau_readonly_surface_contract_v1", "applicable_v1": True},
            "xau_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
            "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
            "dominance_error_type_v1": "BOUNDARY_STAYED_TOO_LONG",
            "dominance_vs_canonical_alignment_v1": "MATCH",
            "dominance_should_have_done_candidate_v1": True,
            "dominance_over_veto_flag_v1": True,
            "dominance_under_veto_flag_v1": False,
            "dominance_friction_separation_state_v1": "SEPARATED",
            "dominance_boundary_dwell_risk_v1": True,
        }
    }

    enriched = attach_xau_decomposition_validation_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["xau_slot_alignment_state_v1"] == "BOUNDARY_OVERRUN"
    assert row["xau_should_have_done_candidate_v1"] is True
    assert row["xau_over_veto_flag_v1"] is True


def test_generate_and_write_xau_decomposition_validation_summary_writes_artifacts(tmp_path):
    report = generate_and_write_xau_decomposition_validation_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "xau_readonly_surface_profile_v1": {"contract_version": "xau_readonly_surface_contract_v1", "applicable_v1": True},
                "xau_state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
                "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
                "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
                "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
                "dominance_error_type_v1": "ALIGNED",
                "dominance_vs_canonical_alignment_v1": "MATCH",
                "dominance_should_have_done_candidate_v1": False,
                "dominance_over_veto_flag_v1": False,
                "dominance_under_veto_flag_v1": False,
                "dominance_friction_separation_state_v1": "SEPARATED",
                "dominance_boundary_dwell_risk_v1": False,
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "xau_decomposition_validation_latest.json"
    md_path = tmp_path / "xau_decomposition_validation_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["xau_row_count"] == 1
    assert report["artifact_paths"]["json_path"] == str(json_path)
