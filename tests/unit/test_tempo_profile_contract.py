import json

from backend.services.tempo_profile_contract import (
    build_tempo_profile_contract_v1,
    generate_and_write_tempo_profile_summary_v1,
)


def test_tempo_profile_contract_exposes_persistence_repeat_modifier_rules():
    contract = build_tempo_profile_contract_v1()

    assert contract["contract_version"] == "tempo_profile_contract_v1"
    assert contract["tempo_profile_state_enum_v1"] == [
        "NONE",
        "EARLY",
        "PERSISTING",
        "REPEATING",
        "EXTENDED",
    ]
    assert contract["dominance_protection_v1"]["tempo_profile_can_change_dominant_side"] is False
    assert "single reject is not the same as repeated rejection tempo" in contract["control_rules_v1"]
    assert "single hold is not the same as persistent hold tempo" in contract["control_rules_v1"]


def test_generate_and_write_tempo_profile_summary_writes_artifacts(tmp_path):
    report = generate_and_write_tempo_profile_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "tempo_profile_latest.json"
    md_path = tmp_path / "tempo_profile_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
