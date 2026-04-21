import json

from backend.services.nas_pilot_mapping_contract import (
    build_nas_pilot_mapping_contract_v1,
    generate_and_write_nas_pilot_mapping_summary_v1,
)


def test_nas_pilot_mapping_contract_exposes_pilot_catalog():
    contract = build_nas_pilot_mapping_contract_v1()

    assert contract["contract_version"] == "nas_pilot_mapping_contract_v1"
    assert "ACTIVE_PILOT" in contract["pilot_status_enum_v1"]
    window_ids = [row["window_id_v1"] for row in contract["pilot_window_catalog_v1"]]
    assert "nas_up_breakout_core_1" in window_ids
    assert "nas_down_pending_1" in window_ids


def test_generate_and_write_nas_pilot_mapping_summary_writes_artifacts(tmp_path):
    report = generate_and_write_nas_pilot_mapping_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "nas_pilot_mapping_latest.json"
    md_path = tmp_path / "nas_pilot_mapping_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
