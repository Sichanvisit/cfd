import json

from backend.services.aggregate_directional_flow_metrics_contract import (
    build_aggregate_directional_flow_metrics_contract_v1,
    build_aggregate_directional_flow_metrics_row_v1,
    generate_and_write_aggregate_directional_flow_metrics_summary_v1,
)


def test_aggregate_directional_flow_metrics_contract_exposes_expected_fields():
    contract = build_aggregate_directional_flow_metrics_contract_v1()
    assert contract["contract_version"] == "aggregate_directional_flow_metrics_contract_v1"
    assert "aggregate_conviction_v1" in contract["row_level_fields_v1"]
    assert "flow_persistence_v1" in contract["row_level_fields_v1"]
    assert contract["aggregate_conviction_minimum_components_v1"] == [
        "dominance_support",
        "structure_support",
        "decomposition_alignment",
    ]


def test_aggregate_directional_flow_metrics_row_marks_strong_acceptance_as_high_and_persisting():
    row = build_aggregate_directional_flow_metrics_row_v1(
        {
            "symbol": "XAUUSD",
            "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_intent_slot_v1": "RECOVERY",
            "common_state_continuation_stage_v1": "ACCEPTANCE",
            "common_state_rejection_type_v1": "FRICTION_REJECTION",
            "common_state_texture_slot_v1": "WITH_FRICTION",
            "common_state_location_context_v1": "POST_BREAKOUT",
            "common_state_tempo_profile_v1": "PERSISTING",
            "common_state_ambiguity_level_v1": "LOW",
            "flow_structure_gate_v1": "ELIGIBLE",
            "flow_structure_gate_primary_reason_v1": "STRUCTURE_ELIGIBLE",
            "flow_structure_gate_slot_polarity_v1": "BULL",
            "flow_structure_gate_stage_v1": "ACCEPTANCE",
            "flow_structure_gate_rejection_type_v1": "FRICTION_REJECTION",
            "flow_structure_gate_tempo_v1": "PERSISTING",
            "flow_structure_gate_ambiguity_v1": "LOW",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "dominance_shadow_gap_v1": 0.31,
            "state_strength_continuation_integrity_v1": 0.82,
            "state_strength_reversal_evidence_v1": 0.14,
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STRONG",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_higher_low_state_v1": "CLEAN_HELD",
            "body_drive_state_v1": "STRONG_DRIVE",
        }
    )

    assert row["aggregate_flow_structure_gate_v1"] == "ELIGIBLE"
    assert row["aggregate_conviction_bucket_v1"] == "HIGH"
    assert row["flow_persistence_state_v1"] == "PERSISTING"
    assert row["aggregate_conviction_v1"] >= 0.67
    assert row["flow_persistence_v1"] >= 0.72


def test_aggregate_directional_flow_metrics_row_marks_mixed_case_as_mid_and_fragile_or_building():
    row = build_aggregate_directional_flow_metrics_row_v1(
        {
            "symbol": "BTCUSD",
            "common_state_slot_core_v1": "BULL_RECOVERY_INITIATION",
            "common_state_polarity_slot_v1": "BULL",
            "common_state_intent_slot_v1": "RECOVERY",
            "common_state_continuation_stage_v1": "INITIATION",
            "common_state_rejection_type_v1": "FRICTION_REJECTION",
            "common_state_texture_slot_v1": "DRIFT",
            "common_state_location_context_v1": "IN_BOX",
            "common_state_tempo_profile_v1": "EARLY",
            "common_state_ambiguity_level_v1": "MEDIUM",
            "flow_structure_gate_v1": "WEAK",
            "flow_structure_gate_primary_reason_v1": "SOFT_SUPPORT_BORDERLINE",
            "flow_structure_gate_slot_polarity_v1": "BULL",
            "flow_structure_gate_stage_v1": "INITIATION",
            "flow_structure_gate_rejection_type_v1": "FRICTION_REJECTION",
            "flow_structure_gate_tempo_v1": "EARLY",
            "flow_structure_gate_ambiguity_v1": "MEDIUM",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "dominance_shadow_gap_v1": 0.12,
            "state_strength_continuation_integrity_v1": 0.55,
            "state_strength_reversal_evidence_v1": 0.28,
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
            "breakout_hold_quality_v1": "WEAK",
            "few_candle_structure_bias_v1": "MIXED",
            "few_candle_higher_low_state_v1": "FRAGILE",
            "body_drive_state_v1": "NEUTRAL",
        }
    )

    assert row["aggregate_flow_structure_gate_v1"] == "WEAK"
    assert row["aggregate_conviction_bucket_v1"] in {"MID", "LOW"}
    assert row["flow_persistence_state_v1"] in {"FADING", "FRAGILE", "BUILDING"}


def test_aggregate_directional_flow_metrics_row_keeps_extension_late_even_with_some_persistence():
    row = build_aggregate_directional_flow_metrics_row_v1(
        {
            "symbol": "NAS100",
            "common_state_slot_core_v1": "BEAR_CONTINUATION_EXTENSION",
            "common_state_polarity_slot_v1": "BEAR",
            "common_state_intent_slot_v1": "CONTINUATION",
            "common_state_continuation_stage_v1": "EXTENSION",
            "common_state_rejection_type_v1": "FRICTION_REJECTION",
            "common_state_texture_slot_v1": "WITH_FRICTION",
            "common_state_location_context_v1": "EXTENDED",
            "common_state_tempo_profile_v1": "EXTENDED",
            "common_state_ambiguity_level_v1": "LOW",
            "flow_structure_gate_v1": "WEAK",
            "flow_structure_gate_primary_reason_v1": "SOFT_SUPPORT_BORDERLINE",
            "flow_structure_gate_slot_polarity_v1": "BEAR",
            "flow_structure_gate_stage_v1": "EXTENSION",
            "flow_structure_gate_rejection_type_v1": "FRICTION_REJECTION",
            "flow_structure_gate_tempo_v1": "EXTENDED",
            "flow_structure_gate_ambiguity_v1": "LOW",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "dominance_shadow_gap_v1": 0.24,
            "state_strength_continuation_integrity_v1": 0.7,
            "state_strength_reversal_evidence_v1": 0.2,
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "breakout_hold_quality_v1": "STABLE",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "few_candle_lower_high_state_v1": "HELD",
            "body_drive_state_v1": "WEAK_DRIVE",
        }
    )

    assert row["aggregate_flow_structure_gate_v1"] == "WEAK"
    assert row["aggregate_decomposition_alignment_v1"] < 0.7
    assert row["flow_persistence_recency_weight_v1"] <= 0.6
    assert row["flow_persistence_state_v1"] in {"FRAGILE", "BUILDING"}


def test_generate_and_write_aggregate_directional_flow_metrics_summary_writes_artifacts(tmp_path):
    report = generate_and_write_aggregate_directional_flow_metrics_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "common_state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
                "common_state_polarity_slot_v1": "BULL",
                "common_state_intent_slot_v1": "RECOVERY",
                "common_state_continuation_stage_v1": "ACCEPTANCE",
                "common_state_rejection_type_v1": "FRICTION_REJECTION",
                "common_state_texture_slot_v1": "WITH_FRICTION",
                "common_state_location_context_v1": "POST_BREAKOUT",
                "common_state_tempo_profile_v1": "PERSISTING",
                "common_state_ambiguity_level_v1": "LOW",
                "flow_structure_gate_v1": "ELIGIBLE",
                "flow_structure_gate_primary_reason_v1": "STRUCTURE_ELIGIBLE",
                "flow_structure_gate_slot_polarity_v1": "BULL",
                "flow_structure_gate_stage_v1": "ACCEPTANCE",
                "flow_structure_gate_rejection_type_v1": "FRICTION_REJECTION",
                "flow_structure_gate_tempo_v1": "PERSISTING",
                "flow_structure_gate_ambiguity_v1": "LOW",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "dominance_shadow_gap_v1": 0.31,
                "state_strength_continuation_integrity_v1": 0.82,
                "state_strength_reversal_evidence_v1": 0.14,
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "breakout_hold_quality_v1": "STRONG",
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "few_candle_higher_low_state_v1": "CLEAN_HELD",
                "body_drive_state_v1": "STRONG_DRIVE",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "aggregate_directional_flow_metrics_latest.json"
    md_path = tmp_path / "aggregate_directional_flow_metrics_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
