import json

from backend.services.location_context_contract import (
    build_location_context_contract_v1,
    generate_and_write_location_context_summary_v1,
)


def test_location_context_contract_exposes_location_modifier_and_control_rules():
    contract = build_location_context_contract_v1()

    assert contract["contract_version"] == "location_context_contract_v1"
    assert contract["location_context_enum_v1"] == [
        "NONE",
        "IN_BOX",
        "AT_EDGE",
        "POST_BREAKOUT",
        "EXTENDED",
    ]
    assert contract["dominance_protection_v1"]["location_context_can_change_dominant_side"] is False
    assert "location context is a modifier, not a core slot driver in v1" in contract["control_rules_v1"]
    assert "AT_EDGE does not imply reversal by itself" in contract["control_rules_v1"]


def test_generate_and_write_location_context_summary_writes_artifacts(tmp_path):
    report = generate_and_write_location_context_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "location_context_latest.json"
    md_path = tmp_path / "location_context_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
