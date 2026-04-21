import json

from backend.services.flow_structure_gate_contract import (
    build_flow_structure_gate_contract_v1,
    build_flow_structure_gate_row_v1,
    generate_and_write_flow_structure_gate_summary_v1,
)


def test_flow_structure_gate_contract_exposes_gate_fields():
    contract = build_flow_structure_gate_contract_v1()
    assert contract["contract_version"] == "flow_structure_gate_contract_v1"
    assert "flow_structure_gate_v1" in contract["row_level_fields_v1"]
    assert "flow_structure_gate_hard_disqualifiers_v1" in contract["row_level_fields_v1"]


def test_flow_structure_gate_row_marks_strong_acceptance_as_eligible():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "XAUUSD",
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "FRICTION_REJECTION",
            "common_state_tempo_profile_v1": "PERSISTING",
            "common_state_ambiguity_level_v1": "LOW",
            "dominance_shadow_dominant_side_v1": "BULL",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STRONG",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_higher_low_state_v1": "CLEAN_HELD",
            "body_drive_state_v1": "STRONG_DRIVE",
        }
    )

    assert row["flow_structure_gate_v1"] == "ELIGIBLE"
    assert row["flow_structure_gate_primary_reason_v1"] == "STRUCTURE_ELIGIBLE"
    assert row["flow_structure_gate_hard_disqualifiers_v1"] == []


def test_flow_structure_gate_row_marks_hard_disqualifier_as_ineligible():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "NAS100",
            "common_state_slot_core_v1": "BULL_CONTINUATION_ACCEPTANCE",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "REVERSAL_REJECTION",
            "common_state_tempo_profile_v1": "PERSISTING",
            "common_state_ambiguity_level_v1": "LOW",
            "dominance_shadow_dominant_side_v1": "BULL",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STRONG",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_higher_low_state_v1": "CLEAN_HELD",
            "body_drive_state_v1": "STRONG_DRIVE",
        }
    )

    assert row["flow_structure_gate_v1"] == "INELIGIBLE"
    assert row["flow_structure_gate_primary_reason_v1"] == "REVERSAL_REJECTION"
    assert "REVERSAL_REJECTION" in row["flow_structure_gate_hard_disqualifiers_v1"]


def test_flow_structure_gate_row_caps_extension_to_weak():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "BTCUSD",
            "common_state_slot_core_v1": "BULL_CONTINUATION_EXTENSION",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_continuation_stage_v1": "EXTENSION",
            "common_state_rejection_type_v1": "FRICTION_REJECTION",
            "common_state_tempo_profile_v1": "REPEATING",
            "common_state_ambiguity_level_v1": "LOW",
            "dominance_shadow_dominant_side_v1": "BULL",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STRONG",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_higher_low_state_v1": "HELD",
            "body_drive_state_v1": "WEAK_DRIVE",
        }
    )

    assert row["flow_structure_gate_v1"] == "WEAK"
    assert row["flow_structure_gate_primary_reason_v1"] == "SOFT_SUPPORT_BORDERLINE"


def test_flow_structure_gate_row_softens_xau_high_ambiguity_when_recovery_structure_is_strong():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "XAUUSD",
            "common_state_slot_core_v1": "BULL_RECOVERY_INITIATION",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_continuation_stage_v1": "INITIATION",
            "common_state_rejection_type_v1": "NONE",
            "common_state_tempo_profile_v1": "EARLY",
            "common_state_ambiguity_level_v1": "HIGH",
            "dominance_shadow_dominant_side_v1": "BULL",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
            "breakout_hold_quality_v1": "STABLE",
            "few_candle_structure_bias_v1": "MIXED",
            "body_drive_state_v1": "WEAK_DRIVE",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
        }
    )

    assert row["flow_structure_gate_v1"] == "WEAK"
    assert row["flow_structure_gate_primary_reason_v1"] == "SOFT_SUPPORT_BORDERLINE"
    assert row["flow_structure_gate_hard_disqualifiers_v1"] == []


def test_flow_structure_gate_row_does_not_treat_btc_none_dominance_as_polarity_mismatch():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "BTCUSD",
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "NONE",
            "common_state_tempo_profile_v1": "REPEATING",
            "common_state_ambiguity_level_v1": "HIGH",
            "dominance_shadow_dominant_side_v1": "NONE",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
            "breakout_hold_quality_v1": "STABLE",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_higher_low_state_v1": "HELD",
            "body_drive_state_v1": "WEAK_DRIVE",
        }
    )

    assert row["flow_structure_gate_v1"] == "INELIGIBLE"
    assert row["flow_structure_gate_primary_reason_v1"] == "AMBIGUITY_HIGH"
    assert "POLARITY_MISMATCH" not in row["flow_structure_gate_hard_disqualifiers_v1"]
    assert "AMBIGUITY_HIGH" in row["flow_structure_gate_hard_disqualifiers_v1"]


def test_flow_structure_gate_row_softens_btc_high_ambiguity_when_bearish_breakdown_context_is_consistent():
    row = build_flow_structure_gate_row_v1(
        {
            "symbol": "BTCUSD",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_ACCEPTANCE",
            "common_state_polarity_slot_v1": "BEAR",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "NONE",
            "common_state_tempo_profile_v1": "EARLY",
            "common_state_ambiguity_level_v1": "HIGH",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "consumer_check_side": "SELL",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
            "breakout_hold_quality_v1": "WEAK",
            "few_candle_structure_bias_v1": "MIXED",
            "body_drive_state_v1": "NONE",
            "previous_box_break_state": "BREAKDOWN_HELD",
            "previous_box_relation": "BELOW",
        }
    )

    assert row["flow_structure_gate_v1"] == "WEAK"
    assert row["flow_structure_gate_primary_reason_v1"] == "SOFT_SUPPORT_BORDERLINE"
    assert "AMBIGUITY_HIGH" not in row["flow_structure_gate_hard_disqualifiers_v1"]


def test_generate_and_write_flow_structure_gate_summary_writes_artifacts(tmp_path):
    report = generate_and_write_flow_structure_gate_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
                "common_state_polarity_slot_v1": "BULL",
                "common_state_continuation_stage_v1": "ACCEPTANCE",
                "common_state_rejection_type_v1": "FRICTION_REJECTION",
                "common_state_tempo_profile_v1": "PERSISTING",
                "common_state_ambiguity_level_v1": "LOW",
                "dominance_shadow_dominant_side_v1": "BULL",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "breakout_hold_quality_v1": "STRONG",
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "few_candle_higher_low_state_v1": "CLEAN_HELD",
                "body_drive_state_v1": "STRONG_DRIVE",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "flow_structure_gate_latest.json"
    md_path = tmp_path / "flow_structure_gate_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
