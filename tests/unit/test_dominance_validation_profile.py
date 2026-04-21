import json

from backend.services.dominance_validation_profile import (
    attach_dominance_validation_fields_v1,
    build_dominance_validation_contract_v1,
    build_dominance_validation_row_v1,
    generate_and_write_dominance_validation_summary_v1,
)


def test_build_dominance_validation_contract_v1_has_error_types():
    contract = build_dominance_validation_contract_v1()
    assert contract["contract_version"] == "dominance_validation_contract_v1"
    assert "FRICTION_MISREAD_AS_REVERSAL" in contract["dominance_error_type_enum_v1"]


def test_dominance_validation_marks_continuation_underpromoted():
    row = build_dominance_validation_row_v1(
        {
            "canonical_direction_annotation_v1": "UP",
            "canonical_phase_v1": "CONTINUATION",
            "consumer_veto_tier_v1": "BOUNDARY_WARNING",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "canonical_runtime_execution_alignment_v1": "DIVERGED",
            "execution_diff_final_action_side": "SELL",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "htf_alignment_state": "WITH_HTF",
            "directional_continuation_overlay_enabled": True,
            "breakout_candidate_direction": "UP",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "breakout_hold_quality_v1": "STABLE",
            "body_drive_state_v1": "WEAK_DRIVE",
            "consumer_check_reason": "upper_reject_confirm",
            "blocked_by": "energy_soft_block",
            "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
            "belief_candidate_recommended_family": "reduce_alert",
            "barrier_candidate_recommended_family": "wait_bias",
        }
    )

    assert row["dominance_expected_side_v1"] == "BULL"
    assert row["dominance_expected_mode_v1"] == "CONTINUATION"
    assert row["dominance_error_type_v1"] == "CONTINUATION_UNDERPROMOTED"
    assert row["dominance_should_have_done_candidate_v1"] is True
    assert len(row["overweighted_caution_fields_v1"]) >= 1
    assert len(row["undervalued_continuation_evidence_v1"]) >= 1


def test_dominance_validation_marks_friction_misread_as_reversal():
    row = build_dominance_validation_row_v1(
        {
            "canonical_direction_annotation_v1": "UP",
            "canonical_phase_v1": "CONTINUATION",
            "consumer_veto_tier_v1": "FRICTION_ONLY",
            "dominance_shadow_dominant_side_v1": "BEAR",
            "dominance_shadow_dominant_mode_v1": "REVERSAL_RISK",
            "canonical_runtime_execution_alignment_v1": "DIVERGED",
            "execution_diff_final_action_side": "SELL",
        }
    )

    assert row["dominance_expected_mode_v1"] == "CONTINUATION_WITH_FRICTION"
    assert row["dominance_error_type_v1"] == "FRICTION_MISREAD_AS_REVERSAL"


def test_dominance_validation_marks_true_reversal_missed():
    row = build_dominance_validation_row_v1(
        {
            "canonical_direction_annotation_v1": "DOWN",
            "canonical_phase_v1": "REVERSAL",
            "consumer_veto_tier_v1": "REVERSAL_OVERRIDE",
            "dominance_shadow_dominant_side_v1": "BULL",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "canonical_runtime_execution_alignment_v1": "DIVERGED",
            "execution_diff_final_action_side": "BUY",
        }
    )

    assert row["dominance_expected_mode_v1"] == "REVERSAL_RISK"
    assert row["dominance_error_type_v1"] == "TRUE_REVERSAL_MISSED"


def test_attach_dominance_validation_fields_v1_enriches_rows():
    enriched = attach_dominance_validation_fields_v1(
        {
            "NAS100": {
                "canonical_direction_annotation_v1": "UP",
                "canonical_phase_v1": "CONTINUATION",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "canonical_runtime_execution_alignment_v1": "MATCH",
                "execution_diff_final_action_side": "BUY",
            }
        }
    )

    assert "dominance_validation_profile_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["dominance_error_type_v1"] in {
        "ALIGNED",
        "CONTINUATION_UNDERPROMOTED",
        "REVERSAL_OVERCALLED",
        "BOUNDARY_STAYED_TOO_LONG",
        "FRICTION_MISREAD_AS_REVERSAL",
        "TRUE_REVERSAL_MISSED",
    }


def test_generate_and_write_dominance_validation_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_dominance_validation_summary_v1(
        {
            "NAS100": {
                "canonical_direction_annotation_v1": "UP",
                "canonical_phase_v1": "CONTINUATION",
                "consumer_veto_tier_v1": "FRICTION_ONLY",
                "dominance_shadow_dominant_side_v1": "BULL",
                "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "canonical_runtime_execution_alignment_v1": "MATCH",
                "execution_diff_final_action_side": "BUY",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "dominance_validation_summary_latest.json"
    md_path = tmp_path / "dominance_validation_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["summary"]["symbol_count"] == 1
