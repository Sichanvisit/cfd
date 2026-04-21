import json

from backend.services.retained_window_flow_calibration_contract import (
    build_retained_window_flow_calibration_contract_v1,
    build_retained_window_flow_calibration_row_v1,
    generate_and_write_retained_window_flow_calibration_summary_v1,
)


def test_retained_window_flow_calibration_contract_exposes_profiles_and_groups():
    contract = build_retained_window_flow_calibration_contract_v1()
    assert contract["contract_version"] == "retained_window_flow_calibration_contract_v1"
    assert "flow_threshold_profile_v1" in contract["row_level_fields_v1"]
    assert "CONFIRMED_POSITIVE" in contract["retained_window_group_enum_v1"]
    assert "XAU_TUNED" in contract["flow_threshold_profile_enum_v1"]


def test_retained_window_flow_calibration_row_attaches_xau_profile():
    row = build_retained_window_flow_calibration_row_v1({"symbol": "XAUUSD"})
    assert row["flow_threshold_profile_v1"] == "XAU_TUNED"
    assert row["aggregate_conviction_confirmed_floor_v1"] == 0.65
    assert row["flow_min_persisting_bars_v1"] == 4
    assert row["retained_window_calibration_state_v1"] == "PROVISIONAL_BAND_READY"


def test_retained_window_flow_calibration_row_attaches_btc_profile():
    row = build_retained_window_flow_calibration_row_v1({"symbol": "BTCUSD"})
    assert row["flow_threshold_profile_v1"] == "BTC_TUNED"
    assert row["aggregate_conviction_confirmed_floor_v1"] == 0.7
    assert row["retained_window_calibration_state_v1"] in {"PARTIAL_READY", "PROVISIONAL_BAND_READY"}


def test_generate_and_write_retained_window_flow_calibration_summary_writes_artifacts(tmp_path):
    report = generate_and_write_retained_window_flow_calibration_summary_v1(
        {
            "XAUUSD": {"symbol": "XAUUSD"},
            "NAS100": {"symbol": "NAS100"},
            "BTCUSD": {"symbol": "BTCUSD"},
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "retained_window_flow_calibration_latest.json"
    md_path = tmp_path / "retained_window_flow_calibration_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["retained_window_count"] >= 3
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
