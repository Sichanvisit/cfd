import json

from backend.services.state_structure_dominance_profile import (
    attach_state_structure_dominance_fields_v1,
    build_state_structure_dominance_contract_v1,
    build_state_structure_dominance_profile_row_v1,
    generate_and_write_state_structure_dominance_summary_v1,
)


def test_build_state_structure_dominance_contract_v1_has_gap_definition():
    contract = build_state_structure_dominance_contract_v1()
    assert contract["contract_version"] == "state_structure_dominance_contract_v1"
    assert contract["dominance_gap_definition_v1"] == "continuation_integrity - reversal_evidence"


def test_state_structure_dominance_marks_friction_override_shadow_for_bull_continuation():
    row = build_state_structure_dominance_profile_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BULL",
            "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "state_strength_continuation_integrity_v1": 0.63,
            "state_strength_reversal_evidence_v1": 0.14,
            "state_strength_friction_v1": 0.34,
            "state_strength_caution_level_v1": "MEDIUM",
            "few_candle_higher_low_state_v1": "HELD",
            "few_candle_lower_high_state_v1": "FRAGILE",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "breakout_hold_quality_v1": "STRONG",
            "body_drive_state_v1": "STRONG_DRIVE",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
        }
    )

    assert row["dominance_shadow_dominant_side_v1"] == "BULL"
    assert row["dominance_shadow_dominant_mode_v1"] == "CONTINUATION_WITH_FRICTION"
    assert row["local_continuation_discount_v1"] > 0.0
    assert row["would_override_caution_v1"] is True


def test_state_structure_dominance_marks_boundary_when_gap_is_small():
    row = build_state_structure_dominance_profile_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BULL",
            "state_strength_dominant_mode_v1": "BOUNDARY",
            "state_strength_continuation_integrity_v1": 0.36,
            "state_strength_reversal_evidence_v1": 0.31,
            "state_strength_friction_v1": 0.12,
            "state_strength_caution_level_v1": "HIGH",
            "few_candle_higher_low_state_v1": "FRAGILE",
            "few_candle_structure_bias_v1": "MIXED",
            "breakout_hold_quality_v1": "WEAK",
            "body_drive_state_v1": "NEUTRAL",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
        }
    )

    assert row["dominance_shadow_dominant_mode_v1"] == "BOUNDARY"
    assert row["dominance_shadow_caution_level_v1"] == "HIGH"
    assert row["would_override_caution_v1"] is False


def test_state_structure_dominance_keeps_reversal_override_without_discount():
    row = build_state_structure_dominance_profile_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BEAR",
            "state_strength_dominant_mode_v1": "REVERSAL_RISK",
            "state_strength_continuation_integrity_v1": 0.19,
            "state_strength_reversal_evidence_v1": 0.71,
            "state_strength_friction_v1": 0.17,
            "state_strength_caution_level_v1": "HIGH",
            "few_candle_higher_low_state_v1": "BROKEN",
            "few_candle_structure_bias_v1": "REVERSAL_FAVOR",
            "breakout_hold_quality_v1": "FAILED",
            "body_drive_state_v1": "COUNTER_DRIVE",
            "consumer_veto_tier_v1": "REVERSAL_OVERRIDE",
        }
    )

    assert row["dominance_shadow_dominant_side_v1"] == "BEAR"
    assert row["dominance_shadow_dominant_mode_v1"] == "REVERSAL_RISK"
    assert row["local_continuation_discount_v1"] == 0.0
    assert row["would_override_caution_v1"] is False


def test_attach_state_structure_dominance_fields_v1_enriches_rows():
    enriched = attach_state_structure_dominance_fields_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "state_strength_dominant_side_v1": "BULL",
                "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "state_strength_continuation_integrity_v1": 0.58,
                "state_strength_reversal_evidence_v1": 0.16,
                "state_strength_friction_v1": 0.28,
                "few_candle_higher_low_state_v1": "HELD",
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "breakout_hold_quality_v1": "STABLE",
                "body_drive_state_v1": "WEAK_DRIVE",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
            }
        }
    )

    assert "state_structure_dominance_profile_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["dominance_shadow_dominant_mode_v1"] in {
        "CONTINUATION",
        "CONTINUATION_WITH_FRICTION",
        "BOUNDARY",
        "REVERSAL_RISK",
    }


def test_generate_and_write_state_structure_dominance_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_state_structure_dominance_summary_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "state_strength_dominant_side_v1": "BULL",
                "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "state_strength_continuation_integrity_v1": 0.6,
                "state_strength_reversal_evidence_v1": 0.15,
                "state_strength_friction_v1": 0.31,
                "few_candle_higher_low_state_v1": "HELD",
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "breakout_hold_quality_v1": "STRONG",
                "body_drive_state_v1": "STRONG_DRIVE",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_structure_dominance_summary_latest.json"
    md_path = tmp_path / "state_structure_dominance_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["summary"]["symbol_count"] == 1
