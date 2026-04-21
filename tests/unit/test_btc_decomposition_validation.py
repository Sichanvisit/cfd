import json

from backend.services.btc_decomposition_validation import (
    attach_btc_decomposition_validation_fields_v1,
    build_btc_decomposition_validation_contract_v1,
    generate_and_write_btc_decomposition_validation_summary_v1,
)


def test_btc_decomposition_validation_contract_exposes_validation_fields():
    contract = build_btc_decomposition_validation_contract_v1()

    assert contract["contract_version"] == "btc_decomposition_validation_contract_v1"
    assert "btc_slot_alignment_state_v1" in contract["row_level_fields_v1"]
    assert contract["execution_change_allowed"] is False


def test_attach_btc_decomposition_validation_fields_surfaces_alignment():
    rows = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "btc_readonly_surface_profile_v1": {"contract_version": "btc_readonly_surface_contract_v1", "applicable_v1": True},
            "btc_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "btc_pilot_window_match_v1": "REVIEW_PENDING",
            "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
            "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
            "dominance_error_type_v1": "BOUNDARY_STAYED_TOO_LONG",
            "dominance_vs_canonical_alignment_v1": "MATCH",
            "dominance_should_have_done_candidate_v1": True,
            "dominance_over_veto_flag_v1": False,
            "dominance_under_veto_flag_v1": True,
        }
    }
    enriched = attach_btc_decomposition_validation_fields_v1(rows)
    row = enriched["BTCUSD"]

    assert row["btc_slot_alignment_state_v1"] == "REVIEW_PENDING"
    assert row["btc_should_have_done_candidate_v1"] is True


def test_generate_and_write_btc_decomposition_validation_summary_writes_artifacts(tmp_path):
    report = generate_and_write_btc_decomposition_validation_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "btc_readonly_surface_profile_v1": {"contract_version": "btc_readonly_surface_contract_v1", "applicable_v1": True},
                "btc_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
                "btc_pilot_window_match_v1": "OUT_OF_PROFILE",
                "dominance_validation_profile_v1": {"contract_version": "dominance_validation_contract_v1"},
                "dominance_accuracy_shadow_profile_v1": {"contract_version": "dominance_accuracy_shadow_contract_v1"},
                "dominance_error_type_v1": "ALIGNED",
                "dominance_vs_canonical_alignment_v1": "MATCH",
                "dominance_should_have_done_candidate_v1": False,
                "dominance_over_veto_flag_v1": False,
                "dominance_under_veto_flag_v1": False,
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "btc_decomposition_validation_latest.json"
    md_path = tmp_path / "btc_decomposition_validation_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["btc_row_count"] == 1
    assert report["artifact_paths"]["json_path"] == str(json_path)
