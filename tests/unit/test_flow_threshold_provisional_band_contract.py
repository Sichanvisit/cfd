import json

from backend.services.flow_threshold_provisional_band_contract import (
    build_flow_threshold_provisional_band_contract_v1,
    build_flow_threshold_provisional_band_row_v1,
    generate_and_write_flow_threshold_provisional_band_summary_v1,
)


def test_flow_threshold_provisional_band_contract_exposes_expected_fields():
    contract = build_flow_threshold_provisional_band_contract_v1()
    assert contract["contract_version"] == "flow_threshold_provisional_band_contract_v1"
    assert "provisional_flow_band_state_v1" in contract["row_level_fields_v1"]
    assert "aggregate_conviction_band_position_v1" in contract["row_level_fields_v1"]


def test_flow_threshold_provisional_band_row_blocks_when_structure_ineligible():
    row = build_flow_threshold_provisional_band_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_flow_structure_gate_v1": "INELIGIBLE",
            "aggregate_conviction_v1": 0.8,
            "flow_persistence_v1": 0.8,
            "flow_threshold_profile_v1": "XAU_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.65,
            "aggregate_conviction_building_floor_v1": 0.45,
            "flow_persistence_confirmed_floor_v1": 0.62,
            "flow_persistence_building_floor_v1": 0.48,
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["provisional_flow_band_state_v1"] == "STRUCTURE_BLOCKED"


def test_flow_threshold_provisional_band_row_marks_confirmed_candidate_when_both_above_confirmed():
    row = build_flow_threshold_provisional_band_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "aggregate_conviction_v1": 0.73,
            "flow_persistence_v1": 0.71,
            "flow_threshold_profile_v1": "NAS_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.60,
            "aggregate_conviction_building_floor_v1": 0.40,
            "flow_persistence_confirmed_floor_v1": 0.58,
            "flow_persistence_building_floor_v1": 0.45,
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["provisional_flow_band_state_v1"] == "CONFIRMED_CANDIDATE"
    assert row["aggregate_conviction_band_position_v1"] == "ABOVE_CONFIRMED"
    assert row["flow_persistence_band_position_v1"] == "ABOVE_CONFIRMED"


def test_flow_threshold_provisional_band_row_caps_extension_to_building_candidate():
    row = build_flow_threshold_provisional_band_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "aggregate_conviction_v1": 0.75,
            "flow_persistence_v1": 0.70,
            "flow_threshold_profile_v1": "NAS_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.60,
            "aggregate_conviction_building_floor_v1": 0.40,
            "flow_persistence_confirmed_floor_v1": 0.58,
            "flow_persistence_building_floor_v1": 0.45,
            "common_state_continuation_stage_v1": "EXTENSION",
        }
    )
    assert row["provisional_flow_band_state_v1"] == "BUILDING_CANDIDATE"


def test_generate_and_write_flow_threshold_provisional_band_summary_writes_artifacts(tmp_path):
    report = generate_and_write_flow_threshold_provisional_band_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "aggregate_flow_structure_gate_v1": "INELIGIBLE",
                "aggregate_conviction_v1": 0.2,
                "flow_persistence_v1": 0.3,
                "flow_threshold_profile_v1": "XAU_TUNED",
                "aggregate_conviction_confirmed_floor_v1": 0.65,
                "aggregate_conviction_building_floor_v1": 0.45,
                "flow_persistence_confirmed_floor_v1": 0.62,
                "flow_persistence_building_floor_v1": 0.48,
                "common_state_continuation_stage_v1": "ACCEPTANCE",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "flow_threshold_provisional_band_latest.json"
    md_path = tmp_path / "flow_threshold_provisional_band_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
