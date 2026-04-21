import json

from backend.services.state_polarity_slot_vocabulary_contract import (
    build_state_polarity_slot_vocabulary_contract_v1,
    generate_and_write_state_polarity_slot_vocabulary_summary_v1,
)


def test_state_polarity_slot_vocabulary_contract_exposes_core_modifier_rules():
    contract = build_state_polarity_slot_vocabulary_contract_v1()

    assert contract["contract_version"] == "state_polarity_slot_vocabulary_contract_v1"
    assert contract["core_slot_definition_v1"] == "polarity + intent + stage"
    assert contract["modifier_definition_v1"] == "texture + location + tempo + ambiguity"
    assert contract["dominance_protection_v1"]["decomposition_can_change_dominant_side"] is False
    assert "entry_bias_v1" in contract["execution_bridge_v1"]["fields"]


def test_generate_and_write_state_polarity_slot_vocabulary_summary_writes_artifacts(tmp_path):
    report = generate_and_write_state_polarity_slot_vocabulary_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "state_polarity_slot_vocabulary_latest.json"
    md_path = tmp_path / "state_polarity_slot_vocabulary_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
