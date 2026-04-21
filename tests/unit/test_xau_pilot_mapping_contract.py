import json

from backend.services.xau_pilot_mapping_contract import (
    build_xau_pilot_mapping_contract_v1,
    generate_and_write_xau_pilot_mapping_summary_v1,
)


def test_xau_pilot_mapping_contract_exposes_common_frame_pilot_catalog():
    contract = build_xau_pilot_mapping_contract_v1()

    assert contract["contract_version"] == "xau_pilot_mapping_contract_v1"
    assert "ACTIVE_PILOT" in contract["pilot_status_enum_v1"]
    window_ids = [row["window_id_v1"] for row in contract["pilot_window_catalog_v1"]]
    assert "xau_up_recovery_1_0200_0300" in window_ids
    assert "xau_down_core_1_0030_0200" in window_ids
    assert contract["dominance_protection_v1"]["pilot_mapping_can_change_dominant_side"] is False


def test_generate_and_write_xau_pilot_mapping_summary_writes_artifacts(tmp_path):
    report = generate_and_write_xau_pilot_mapping_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "xau_pilot_mapping_latest.json"
    md_path = tmp_path / "xau_pilot_mapping_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
