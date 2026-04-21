import json

from backend.services.btc_readonly_surface_contract import (
    attach_btc_readonly_surface_fields_v1,
    build_btc_readonly_surface_contract_v1,
    generate_and_write_btc_readonly_surface_summary_v1,
)


def test_btc_readonly_surface_contract_exposes_btc_row_fields():
    contract = build_btc_readonly_surface_contract_v1()

    assert contract["contract_version"] == "btc_readonly_surface_contract_v1"
    assert "btc_state_slot_core_v1" in contract["row_level_fields_v1"]
    assert contract["dominance_protection_v1"]["btc_readonly_surface_can_change_dominant_side"] is False


def test_attach_btc_readonly_surface_fields_surfaces_btc_profile():
    rows = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "state_slot_symbol_extension_surface_profile_v1": {
                "contract_version": "state_slot_symbol_extension_surface_contract_v1",
            },
            "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
            "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_intent_slot_v1": "RECOVERY",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "NONE",
            "common_state_texture_slot_v1": "WITH_FRICTION",
            "common_state_location_context_v1": "IN_BOX",
            "common_state_tempo_profile_v1": "PERSISTING",
            "common_state_ambiguity_level_v1": "MEDIUM",
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "common_state_slot_modifier_bundle_v1": ["WITH_FRICTION"],
        }
    }
    enriched = attach_btc_readonly_surface_fields_v1(rows)
    row = enriched["BTCUSD"]

    assert row["btc_polarity_slot_v1"] == "BULL"
    assert row["btc_intent_slot_v1"] == "RECOVERY"
    assert row["btc_pilot_window_match_v1"] == "REVIEW_PENDING"


def test_generate_and_write_btc_readonly_surface_summary_writes_artifacts(tmp_path):
    report = generate_and_write_btc_readonly_surface_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "state_slot_symbol_extension_surface_profile_v1": {
                    "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                },
                "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
                "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
                "common_state_polarity_slot_v1": "BEAR",
                "common_state_intent_slot_v1": "CONTINUATION",
                "common_state_continuation_stage_v1": "ACCEPTANCE",
                "common_state_rejection_type_v1": "FRICTION_REJECTION",
                "common_state_texture_slot_v1": "DRIFT",
                "common_state_location_context_v1": "AT_EDGE",
                "common_state_tempo_profile_v1": "REPEATING",
                "common_state_ambiguity_level_v1": "HIGH",
                "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
                "common_state_slot_modifier_bundle_v1": ["DRIFT"],
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "btc_readonly_surface_latest.json"
    md_path = tmp_path / "btc_readonly_surface_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["btc_row_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
