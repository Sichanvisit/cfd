import json

from backend.services.ambiguity_modifier_contract import (
    build_ambiguity_modifier_contract_v1,
    generate_and_write_ambiguity_modifier_summary_v1,
)


def test_ambiguity_modifier_contract_exposes_boundary_caution_modifier_rules():
    contract = build_ambiguity_modifier_contract_v1()

    assert contract["contract_version"] == "ambiguity_modifier_contract_v1"
    assert contract["ambiguity_level_enum_v1"] == ["LOW", "MEDIUM", "HIGH"]
    assert contract["dominance_protection_v1"]["ambiguity_can_change_dominant_side"] is False
    assert "ambiguity is a modifier, not a core slot driver in v1" in contract["control_rules_v1"]
    assert "high ambiguity must not be silently absorbed into friction or continuation" in contract["control_rules_v1"]


def test_generate_and_write_ambiguity_modifier_summary_writes_artifacts(tmp_path):
    report = generate_and_write_ambiguity_modifier_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "ambiguity_modifier_latest.json"
    md_path = tmp_path / "ambiguity_modifier_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
