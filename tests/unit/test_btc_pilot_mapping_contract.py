import json

from backend.services.btc_pilot_mapping_contract import (
    build_btc_pilot_mapping_contract_v1,
    generate_and_write_btc_pilot_mapping_summary_v1,
)


def test_btc_pilot_mapping_contract_exposes_pilot_catalog():
    contract = build_btc_pilot_mapping_contract_v1()

    assert contract["contract_version"] == "btc_pilot_mapping_contract_v1"
    assert "REVIEW_PENDING" in contract["pilot_status_enum_v1"]
    window_ids = [row["window_id_v1"] for row in contract["pilot_window_catalog_v1"]]
    assert "btc_up_recovery_0500_0701" in window_ids
    assert "btc_down_drift_0333_0525" in window_ids


def test_generate_and_write_btc_pilot_mapping_summary_writes_artifacts(tmp_path):
    report = generate_and_write_btc_pilot_mapping_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "btc_pilot_mapping_latest.json"
    md_path = tmp_path / "btc_pilot_mapping_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
