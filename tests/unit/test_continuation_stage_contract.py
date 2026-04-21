import json

from backend.services.continuation_stage_contract import (
    build_continuation_stage_contract_v1,
    generate_and_write_continuation_stage_summary_v1,
)


def test_continuation_stage_contract_exposes_stage_split_and_control_rules():
    contract = build_continuation_stage_contract_v1()

    assert contract["contract_version"] == "continuation_stage_contract_v1"
    assert contract["continuation_stage_enum_v1"] == [
        "NONE",
        "INITIATION",
        "ACCEPTANCE",
        "EXTENSION",
    ]
    assert contract["dominance_protection_v1"]["continuation_stage_can_change_dominant_side"] is False
    assert "stage means structural time position, not execution quality" in contract["control_rules_v1"]
    assert "texture means execution quality and must not be merged with stage" in contract["control_rules_v1"]


def test_generate_and_write_continuation_stage_summary_writes_artifacts(tmp_path):
    report = generate_and_write_continuation_stage_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "continuation_stage_latest.json"
    md_path = tmp_path / "continuation_stage_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
