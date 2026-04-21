import json

from backend.services.execution_policy_shadow_audit import (
    build_execution_policy_shadow_audit_contract_v1,
    attach_execution_policy_shadow_audit_fields_v1,
    generate_and_write_execution_policy_shadow_audit_summary_v1,
)


def test_execution_policy_shadow_audit_contract_exposes_alignment_fields():
    contract = build_execution_policy_shadow_audit_contract_v1()
    assert contract["contract_version"] == "execution_policy_shadow_audit_contract_v1"
    assert "lifecycle_policy_alignment_state_v1" in contract["row_level_fields_v1"]


def test_attach_execution_policy_shadow_audit_fields_flags_misaligned_policy():
    rows = {
        "NAS100": {
            "symbol": "NAS100",
            "state_slot_position_lifecycle_policy_profile_v1": {
                "contract_version": "state_slot_position_lifecycle_policy_contract_v1",
            },
            "common_state_slot_core_v1": "BULL_CONTINUATION_EXTENTION".replace("EXTENTION", "EXTENSION"),
            "common_state_continuation_stage_v1": "EXTENSION",
            "common_state_texture_slot_v1": "CLEAN",
            "common_state_ambiguity_level_v1": "LOW",
            "state_slot_lifecycle_policy_state_v1": "READY",
            "entry_policy_v1": "ACTIVE_ENTRY",
            "hold_policy_v1": "HOLD_FAVOR",
            "reduce_policy_v1": "LIGHT_REDUCE",
            "exit_policy_v1": "EXIT_WATCH",
        }
    }
    enriched = attach_execution_policy_shadow_audit_fields_v1(rows)
    row = enriched["NAS100"]
    assert row["lifecycle_policy_alignment_state_v1"] == "ENTRY_TOO_AGGRESSIVE"
    assert row["entry_delay_conflict_flag_v1"] is True


def test_generate_and_write_execution_policy_shadow_audit_summary_writes_artifacts(tmp_path):
    report = generate_and_write_execution_policy_shadow_audit_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "state_slot_position_lifecycle_policy_profile_v1": {
                    "contract_version": "state_slot_position_lifecycle_policy_contract_v1",
                },
                "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
                "common_state_continuation_stage_v1": "ACCEPTANCE",
                "common_state_texture_slot_v1": "WITH_FRICTION",
                "common_state_ambiguity_level_v1": "LOW",
                "state_slot_lifecycle_policy_state_v1": "READY",
                "entry_policy_v1": "DELAYED_ENTRY",
                "hold_policy_v1": "STRONG_HOLD",
                "reduce_policy_v1": "REDUCE_STRONG",
                "exit_policy_v1": "EXIT_PREP",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "execution_policy_shadow_audit_latest.json"
    md_path = tmp_path / "execution_policy_shadow_audit_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["json_path"] == str(json_path)
