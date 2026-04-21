import json

from backend.services.nas_readonly_surface_contract import (
    attach_nas_readonly_surface_fields_v1,
    build_nas_readonly_surface_contract_v1,
    generate_and_write_nas_readonly_surface_summary_v1,
)


def test_nas_readonly_surface_contract_exposes_nas_row_fields():
    contract = build_nas_readonly_surface_contract_v1()

    assert contract["contract_version"] == "nas_readonly_surface_contract_v1"
    assert "nas_state_slot_core_v1" in contract["row_level_fields_v1"]
    assert contract["dominance_protection_v1"]["nas_readonly_surface_can_change_dominant_side"] is False


def test_attach_nas_readonly_surface_fields_surfaces_nas_profile():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "state_slot_symbol_extension_surface_profile_v1": {
                "contract_version": "state_slot_symbol_extension_surface_contract_v1",
            },
            "symbol_state_strength_profile_status_v1": "ACTIVE_CANDIDATE",
            "symbol_state_strength_profile_match_v1": "MATCH",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_intent_slot_v1": "CONTINUATION",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "NONE",
            "common_state_texture_slot_v1": "WITH_FRICTION",
            "common_state_location_context_v1": "POST_BREAKOUT",
            "common_state_tempo_profile_v1": "PERSISTING",
            "common_state_ambiguity_level_v1": "LOW",
            "common_state_slot_core_v1": "BULL_CONTINUATION_ACCEPTANCE",
            "common_state_slot_modifier_bundle_v1": ["WITH_FRICTION"],
        }
    }
    enriched = attach_nas_readonly_surface_fields_v1(rows)
    row = enriched["NAS100"]

    assert row["nas_polarity_slot_v1"] == "BULL"
    assert row["nas_intent_slot_v1"] == "CONTINUATION"
    assert row["nas_pilot_window_match_v1"] == "MATCHED_ACTIVE_PROFILE"


def test_generate_and_write_nas_readonly_surface_summary_writes_artifacts(tmp_path):
    report = generate_and_write_nas_readonly_surface_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "state_slot_symbol_extension_surface_profile_v1": {
                    "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                },
                "symbol_state_strength_profile_status_v1": "SEPARATE_PENDING",
                "symbol_state_strength_profile_match_v1": "SEPARATE_PENDING",
                "common_state_polarity_slot_v1": "BEAR",
                "common_state_intent_slot_v1": "CONTINUATION",
                "common_state_continuation_stage_v1": "INITIATION",
                "common_state_rejection_type_v1": "FRICTION_REJECTION",
                "common_state_texture_slot_v1": "WITH_FRICTION",
                "common_state_location_context_v1": "AT_EDGE",
                "common_state_tempo_profile_v1": "EARLY",
                "common_state_ambiguity_level_v1": "HIGH",
                "common_state_slot_core_v1": "BEAR_CONTINUATION_INITIATION",
                "common_state_slot_modifier_bundle_v1": ["WITH_FRICTION"],
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "nas_readonly_surface_latest.json"
    md_path = tmp_path / "nas_readonly_surface_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["nas_row_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
