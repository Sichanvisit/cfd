import json

from backend.services.exact_pilot_match_bonus_contract import (
    build_exact_pilot_match_bonus_contract_v1,
    build_exact_pilot_match_bonus_row_v1,
    generate_and_write_exact_pilot_match_bonus_summary_v1,
)


def test_exact_pilot_match_bonus_contract_exposes_expected_fields():
    contract = build_exact_pilot_match_bonus_contract_v1()
    assert contract["contract_version"] == "exact_pilot_match_bonus_contract_v1"
    assert "exact_pilot_match_bonus_effect_v1" in contract["row_level_fields_v1"]
    assert "boosted_provisional_flow_band_state_v1" in contract["row_level_fields_v1"]


def test_exact_pilot_match_bonus_blocks_when_structure_is_blocked():
    row = build_exact_pilot_match_bonus_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_flow_structure_gate_v1": "INELIGIBLE",
            "provisional_flow_band_state_v1": "STRUCTURE_BLOCKED",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "retained_window_calibration_state_v1": "PROVISIONAL_BAND_READY",
            "retained_window_flow_calibration_profile_v1": {"exact_match_bonus_strength_v1": "MEDIUM"},
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["exact_pilot_match_bonus_effect_v1"] == "BONUS_BLOCKED"
    assert row["boosted_provisional_flow_band_state_v1"] == "STRUCTURE_BLOCKED"


def test_exact_pilot_match_bonus_can_promote_building_to_confirmed_when_ready():
    row = build_exact_pilot_match_bonus_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "provisional_flow_band_state_v1": "BUILDING_CANDIDATE",
            "nas_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "retained_window_calibration_state_v1": "PROVISIONAL_BAND_READY",
            "retained_window_flow_calibration_profile_v1": {"exact_match_bonus_strength_v1": "LOW_MEDIUM"},
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["exact_pilot_match_bonus_effect_v1"] == "BUILDING_TO_CONFIRMED"
    assert row["boosted_provisional_flow_band_state_v1"] == "CONFIRMED_CANDIDATE"
    assert row["pilot_match_bonus_delta_levels_v1"] == 1


def test_exact_pilot_match_bonus_never_jumps_unconfirmed_to_confirmed():
    row = build_exact_pilot_match_bonus_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "provisional_flow_band_state_v1": "UNCONFIRMED_CANDIDATE",
            "xau_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "retained_window_calibration_state_v1": "PROVISIONAL_BAND_READY",
            "retained_window_flow_calibration_profile_v1": {"exact_match_bonus_strength_v1": "HIGH"},
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["exact_pilot_match_bonus_effect_v1"] == "UNCONFIRMED_TO_BUILDING"
    assert row["boosted_provisional_flow_band_state_v1"] == "BUILDING_CANDIDATE"


def test_exact_pilot_match_bonus_withholds_confirmed_promotion_on_extension():
    row = build_exact_pilot_match_bonus_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "provisional_flow_band_state_v1": "BUILDING_CANDIDATE",
            "nas_pilot_window_match_v1": "MATCHED_ACTIVE_PROFILE",
            "retained_window_calibration_state_v1": "PROVISIONAL_BAND_READY",
            "retained_window_flow_calibration_profile_v1": {"exact_match_bonus_strength_v1": "MEDIUM"},
            "common_state_continuation_stage_v1": "EXTENSION",
        }
    )
    assert row["exact_pilot_match_bonus_effect_v1"] == "PRIORITY_BOOST"
    assert row["boosted_provisional_flow_band_state_v1"] == "BUILDING_CANDIDATE"


def test_generate_and_write_exact_pilot_match_bonus_summary_writes_artifacts(tmp_path):
    report = generate_and_write_exact_pilot_match_bonus_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "aggregate_flow_structure_gate_v1": "ELIGIBLE",
                "provisional_flow_band_state_v1": "UNCONFIRMED_CANDIDATE",
                "btc_pilot_window_match_v1": "OUT_OF_PROFILE",
                "retained_window_calibration_state_v1": "PARTIAL_READY",
                "retained_window_flow_calibration_profile_v1": {"exact_match_bonus_strength_v1": "LOW"},
                "common_state_continuation_stage_v1": "INITIATION",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "exact_pilot_match_bonus_latest.json"
    md_path = tmp_path / "exact_pilot_match_bonus_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
