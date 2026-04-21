import json

from backend.services.nas_decomposition_validation import (
    attach_nas_decomposition_validation_fields_v1,
    build_nas_decomposition_validation_contract_v1,
    generate_and_write_nas_decomposition_validation_summary_v1,
)


def test_nas_decomposition_validation_contract_exposes_validation_fields():
    contract = build_nas_decomposition_validation_contract_v1()

    assert contract["contract_version"] == "nas_decomposition_validation_contract_v1"
    assert "nas_slot_alignment_state_v1" in contract["row_level_fields_v1"]
    assert contract["execution_change_allowed"] is False


def test_attach_nas_decomposition_validation_fields_surfaces_alignment():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "nas_readonly_surface_profile_v1": {"contract_version": "nas_readonly_surface_contract_v1", "applicable_v1": True},
            "nas_state_slot_core_v1": "BULL_CONTINUATION_ACCEPTANCE",
            "nas_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
            "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
            "dominance_error_type_v1": "ALIGNED",
            "dominance_vs_canonical_alignment_v1": "MATCH",
            "dominance_should_have_done_candidate_v1": False,
            "dominance_over_veto_flag_v1": False,
            "dominance_under_veto_flag_v1": False,
        }
    }
    enriched = attach_nas_decomposition_validation_fields_v1(rows)
    row = enriched["NAS100"]

    assert row["nas_slot_alignment_state_v1"] == "ALIGNED"
    assert row["nas_should_have_done_candidate_v1"] is False


def test_generate_and_write_nas_decomposition_validation_summary_writes_artifacts(tmp_path):
    report = generate_and_write_nas_decomposition_validation_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "nas_readonly_surface_profile_v1": {"contract_version": "nas_readonly_surface_contract_v1", "applicable_v1": True},
                "nas_state_slot_core_v1": "BEAR_CONTINUATION_INITIATION",
                "nas_pilot_window_match_v1": "REVIEW_PENDING",
                "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
                "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
                "dominance_error_type_v1": "BOUNDARY_STAYED_TOO_LONG",
                "dominance_vs_canonical_alignment_v1": "MATCH",
                "dominance_should_have_done_candidate_v1": True,
                "dominance_over_veto_flag_v1": True,
                "dominance_under_veto_flag_v1": False,
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "nas_decomposition_validation_latest.json"
    md_path = tmp_path / "nas_decomposition_validation_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["nas_row_count"] == 1
    assert report["artifact_paths"]["json_path"] == str(json_path)
