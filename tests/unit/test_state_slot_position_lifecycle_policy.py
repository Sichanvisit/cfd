import json

from backend.services.state_slot_position_lifecycle_policy import (
    attach_state_slot_position_lifecycle_policy_fields_v1,
    build_state_slot_position_lifecycle_policy_contract_v1,
    generate_and_write_state_slot_position_lifecycle_policy_summary_v1,
)


def test_state_slot_position_lifecycle_policy_contract_exposes_policy_fields():
    contract = build_state_slot_position_lifecycle_policy_contract_v1()

    assert contract["contract_version"] == "state_slot_position_lifecycle_policy_contract_v1"
    assert "entry_policy_v1" in contract["row_level_fields_v1"]
    assert contract["execution_change_allowed"] is False


def test_attach_state_slot_position_lifecycle_policy_fields_uses_bridge_for_xau_and_surface_for_nas():
    rows = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "state_slot_execution_interface_bridge_profile_v1": {
                "contract_version": "state_slot_execution_interface_bridge_contract_v1",
                "bridge_state_v1": "READY",
            },
            "state_slot_bridge_state_v1": "READY",
            "bridge_source_slot_v1": "BULL_RECOVERY_ACCEPTANCE",
            "entry_bias_v1": "LOW",
            "hold_bias_v1": "HIGH",
            "add_bias_v1": "NONE",
            "reduce_bias_v1": "MEDIUM",
            "exit_bias_v1": "LOW",
            "state_slot_symbol_extension_surface_profile_v1": {
                "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                "applicable_v1": True,
            },
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
        },
        "NAS100": {
            "symbol": "NAS100",
            "state_slot_symbol_extension_surface_profile_v1": {
                "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                "applicable_v1": True,
            },
            "common_state_slot_core_v1": "BULL_CONTINUATION_EXTENTION".replace("EXTENTION", "EXTENSION"),
            "common_state_continuation_stage_v1": "EXTENSION",
            "common_state_texture_slot_v1": "WITH_FRICTION",
            "common_state_ambiguity_level_v1": "LOW",
            "common_vocabulary_compatibility_v1": "COMPATIBLE",
        },
    }

    enriched = attach_state_slot_position_lifecycle_policy_fields_v1(rows)
    xau = enriched["XAUUSD"]
    nas = enriched["NAS100"]

    assert xau["state_slot_execution_policy_source_v1"] == "BRIDGE_BIAS"
    assert xau["hold_policy_v1"] == "STRONG_HOLD"
    assert xau["entry_policy_v1"] == "DELAYED_ENTRY"

    assert nas["state_slot_execution_policy_source_v1"] == "COMMON_SLOT_DERIVED"
    assert nas["entry_policy_v1"] in {"DELAYED_ENTRY", "NO_NEW_ENTRY"}
    assert nas["reduce_policy_v1"] in {"REDUCE_FAVOR", "REDUCE_STRONG"}


def test_generate_and_write_state_slot_position_lifecycle_policy_summary_writes_artifacts(tmp_path):
    report = generate_and_write_state_slot_position_lifecycle_policy_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "state_slot_execution_interface_bridge_profile_v1": {
                    "contract_version": "state_slot_execution_interface_bridge_contract_v1",
                    "bridge_state_v1": "READY",
                },
                "state_slot_bridge_state_v1": "READY",
                "bridge_source_slot_v1": "BEAR_REJECTION_ACCEPTANCE",
                "entry_bias_v1": "LOW",
                "hold_bias_v1": "HIGH",
                "add_bias_v1": "NONE",
                "reduce_bias_v1": "MEDIUM",
                "exit_bias_v1": "LOW",
                "state_slot_symbol_extension_surface_profile_v1": {
                    "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                    "applicable_v1": True,
                },
                "common_state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
            },
            "NAS100": {
                "symbol": "NAS100",
                "state_slot_symbol_extension_surface_profile_v1": {
                    "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                    "applicable_v1": True,
                },
                "common_state_slot_core_v1": "BULL_CONTINUATION_ACCEPTANCE",
                "common_state_continuation_stage_v1": "ACCEPTANCE",
                "common_state_texture_slot_v1": "CLEAN",
                "common_state_ambiguity_level_v1": "LOW",
                "common_vocabulary_compatibility_v1": "COMPATIBLE",
            },
            "BTCUSD": {
                "symbol": "BTCUSD",
                "state_slot_symbol_extension_surface_profile_v1": {
                    "contract_version": "state_slot_symbol_extension_surface_contract_v1",
                    "applicable_v1": True,
                },
                "common_state_slot_core_v1": "BULL_RECOVERY_INITIATION",
                "common_state_continuation_stage_v1": "INITIATION",
                "common_state_texture_slot_v1": "DRIFT",
                "common_state_ambiguity_level_v1": "MEDIUM",
                "common_vocabulary_compatibility_v1": "REVIEW_PENDING",
            },
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_slot_position_lifecycle_policy_latest.json"
    md_path = tmp_path / "state_slot_position_lifecycle_policy_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 3
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
