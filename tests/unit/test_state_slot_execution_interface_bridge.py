import json

from backend.services.state_slot_execution_interface_bridge import (
    attach_state_slot_execution_interface_bridge_fields_v1,
    build_state_slot_execution_interface_bridge_contract_v1,
    generate_and_write_state_slot_execution_interface_bridge_summary_v1,
)


def test_state_slot_execution_interface_bridge_contract_exposes_bias_fields():
    contract = build_state_slot_execution_interface_bridge_contract_v1()

    assert contract["contract_version"] == "state_slot_execution_interface_bridge_contract_v1"
    assert "entry_bias_v1" in contract["row_level_fields_v1"]
    assert contract["execution_change_allowed"] is False


def test_attach_state_slot_execution_interface_bridge_fields_maps_xau_biases():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "xau_readonly_surface_profile_v1": {"contract_version": "xau_readonly_surface_contract_v1", "applicable_v1": True},
            "xau_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "xau_continuation_stage_v1": "ACCEPTANCE",
            "xau_texture_slot_v1": "WITH_FRICTION",
            "xau_ambiguity_level_v1": "MEDIUM",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
        }
    }

    enriched = attach_state_slot_execution_interface_bridge_fields_v1(rows)
    row = enriched["XAUUSD"]

    assert row["state_slot_bridge_state_v1"] == "READY"
    assert row["entry_bias_v1"] in {"LOW", "MEDIUM"}
    assert row["hold_bias_v1"] in {"MEDIUM", "HIGH"}


def test_generate_and_write_state_slot_execution_interface_bridge_summary_writes_artifacts(tmp_path):
    report = generate_and_write_state_slot_execution_interface_bridge_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "xau_readonly_surface_profile_v1": {"contract_version": "xau_readonly_surface_contract_v1", "applicable_v1": True},
                "xau_state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
                "xau_continuation_stage_v1": "ACCEPTANCE",
                "xau_texture_slot_v1": "CLEAN",
                "xau_ambiguity_level_v1": "LOW",
                "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_slot_execution_interface_bridge_latest.json"
    md_path = tmp_path / "state_slot_execution_interface_bridge_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["xau_row_count"] == 1
    assert report["artifact_paths"]["json_path"] == str(json_path)
