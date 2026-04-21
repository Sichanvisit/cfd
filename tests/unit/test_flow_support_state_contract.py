import json

from backend.services.flow_support_state_contract import (
    build_flow_support_state_contract_v1,
    build_flow_support_state_row_v1,
    generate_and_write_flow_support_state_summary_v1,
)


def test_flow_support_state_contract_exposes_expected_fields():
    contract = build_flow_support_state_contract_v1()
    assert contract["contract_version"] == "flow_support_state_contract_v1"
    assert "flow_support_state_v1" in contract["row_level_fields_v1"]
    assert "flow_support_state_authority_v1" in contract["row_level_fields_v1"]


def test_flow_support_state_marks_hard_structure_conflict_as_opposed():
    row = build_flow_support_state_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "INELIGIBLE",
            "flow_structure_gate_hard_disqualifiers_v1": ["POLARITY_MISMATCH"],
            "provisional_flow_band_state_v1": "STRUCTURE_BLOCKED",
            "boosted_provisional_flow_band_state_v1": "STRUCTURE_BLOCKED",
            "exact_pilot_match_bonus_effect_v1": "BONUS_BLOCKED",
            "flow_threshold_profile_v1": "NAS_TUNED",
            "common_state_continuation_stage_v1": "INITIATION",
        }
    )
    assert row["flow_support_state_v1"] == "FLOW_OPPOSED"
    assert row["flow_support_state_authority_v1"] == "STRUCTURE_HARD_OPPOSED"


def test_flow_support_state_marks_ambiguity_block_as_unconfirmed():
    row = build_flow_support_state_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_flow_structure_gate_v1": "INELIGIBLE",
            "flow_structure_gate_hard_disqualifiers_v1": ["AMBIGUITY_HIGH"],
            "provisional_flow_band_state_v1": "STRUCTURE_BLOCKED",
            "boosted_provisional_flow_band_state_v1": "STRUCTURE_BLOCKED",
            "exact_pilot_match_bonus_effect_v1": "BONUS_BLOCKED",
            "flow_threshold_profile_v1": "XAU_TUNED",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["flow_support_state_v1"] == "FLOW_UNCONFIRMED"
    assert row["flow_support_state_authority_v1"] == "STRUCTURE_BLOCKED_UNCONFIRMED"


def test_flow_support_state_maps_confirmed_candidate_to_confirmed():
    row = build_flow_support_state_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "flow_structure_gate_hard_disqualifiers_v1": [],
            "provisional_flow_band_state_v1": "CONFIRMED_CANDIDATE",
            "boosted_provisional_flow_band_state_v1": "CONFIRMED_CANDIDATE",
            "exact_pilot_match_bonus_effect_v1": "VALIDATION_ONLY",
            "flow_threshold_profile_v1": "XAU_TUNED",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
        }
    )
    assert row["flow_support_state_v1"] == "FLOW_CONFIRMED"
    assert row["flow_support_state_authority_v1"] == "PROVISIONAL_CONFIRMED"


def test_flow_support_state_caps_extension_confirmed_to_building():
    row = build_flow_support_state_row_v1(
        {
            "symbol": "NAS100",
            "aggregate_flow_structure_gate_v1": "ELIGIBLE",
            "flow_structure_gate_hard_disqualifiers_v1": [],
            "provisional_flow_band_state_v1": "BUILDING_CANDIDATE",
            "boosted_provisional_flow_band_state_v1": "CONFIRMED_CANDIDATE",
            "exact_pilot_match_bonus_effect_v1": "BUILDING_TO_CONFIRMED",
            "flow_threshold_profile_v1": "NAS_TUNED",
            "common_state_continuation_stage_v1": "EXTENSION",
        }
    )
    assert row["flow_support_state_v1"] == "FLOW_BUILDING"
    assert row["flow_support_state_authority_v1"] == "EXTENSION_CAPPED_BUILDING"


def test_generate_and_write_flow_support_state_summary_writes_artifacts(tmp_path):
    report = generate_and_write_flow_support_state_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "aggregate_flow_structure_gate_v1": "ELIGIBLE",
                "flow_structure_gate_hard_disqualifiers_v1": [],
                "provisional_flow_band_state_v1": "UNCONFIRMED_CANDIDATE",
                "boosted_provisional_flow_band_state_v1": "BUILDING_CANDIDATE",
                "exact_pilot_match_bonus_effect_v1": "UNCONFIRMED_TO_BUILDING",
                "flow_threshold_profile_v1": "BTC_TUNED",
                "common_state_continuation_stage_v1": "INITIATION",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "flow_support_state_latest.json"
    md_path = tmp_path / "flow_support_state_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
