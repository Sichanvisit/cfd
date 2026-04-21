import json

from backend.services.dominance_accuracy_shadow import (
    attach_dominance_accuracy_shadow_fields_v1,
    build_dominance_accuracy_shadow_contract_v1,
    build_dominance_accuracy_shadow_row_v1,
    generate_and_write_dominance_accuracy_shadow_reports_v1,
)


def test_build_dominance_accuracy_shadow_contract_v1_has_fields():
    contract = build_dominance_accuracy_shadow_contract_v1()
    assert contract["contract_version"] == "dominance_accuracy_shadow_contract_v1"
    assert "dominance_over_veto_flag_v1" in contract["row_level_fields_v1"]


def test_dominance_accuracy_shadow_marks_over_veto_and_raise_continuation():
    row = build_dominance_accuracy_shadow_row_v1(
        {
            "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
            "dominance_expected_mode_v1": "CONTINUATION",
            "dominance_shadow_dominant_mode_v1": "BOUNDARY",
            "dominance_vs_canonical_alignment_v1": "DIVERGED",
            "canonical_session_bucket_v1": "US",
        }
    )

    assert row["dominance_over_veto_flag_v1"] is True
    assert row["dominance_under_veto_flag_v1"] is False
    assert row["dominance_shadow_bias_effect_v1"] == "RAISE_CONTINUATION_CONFIDENCE"
    assert row["dominance_shadow_bias_candidate_state_v1"] == "READY"


def test_dominance_accuracy_shadow_marks_true_reversal_missed_as_under_veto():
    row = build_dominance_accuracy_shadow_row_v1(
        {
            "dominance_error_type_v1": "TRUE_REVERSAL_MISSED",
            "dominance_expected_mode_v1": "REVERSAL_RISK",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "dominance_vs_canonical_alignment_v1": "DIVERGED",
            "canonical_session_bucket_v1": "ASIA",
        }
    )

    assert row["dominance_under_veto_flag_v1"] is True
    assert row["dominance_shadow_bias_effect_v1"] == "LOWER_CONTINUATION_CONFIDENCE"
    assert row["dominance_shadow_bias_confidence_v1"] == "HIGH"


def test_dominance_accuracy_shadow_marks_friction_separation():
    row = build_dominance_accuracy_shadow_row_v1(
        {
            "dominance_error_type_v1": "ALIGNED",
            "dominance_expected_mode_v1": "CONTINUATION_WITH_FRICTION",
            "dominance_shadow_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "canonical_session_bucket_v1": "US",
        }
    )

    assert row["dominance_friction_separation_state_v1"] == "SEPARATED"
    assert row["dominance_shadow_bias_effect_v1"] == "KEEP_NEUTRAL"


def test_attach_dominance_accuracy_shadow_fields_v1_enriches_rows():
    enriched = attach_dominance_accuracy_shadow_fields_v1(
        {
            "NAS100": {
                "dominance_error_type_v1": "BOUNDARY_STAYED_TOO_LONG",
                "dominance_expected_mode_v1": "BOUNDARY",
                "dominance_shadow_dominant_mode_v1": "BOUNDARY",
                "dominance_vs_canonical_alignment_v1": "WAITING",
                "canonical_session_bucket_v1": "ASIA",
            }
        }
    )

    assert "dominance_accuracy_shadow_profile_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["dominance_boundary_dwell_risk_v1"] is True


def test_generate_and_write_dominance_accuracy_shadow_reports_v1_writes_artifacts(tmp_path):
    report = generate_and_write_dominance_accuracy_shadow_reports_v1(
        {
            "NAS100": {
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "dominance_expected_mode_v1": "CONTINUATION",
                "dominance_shadow_dominant_mode_v1": "BOUNDARY",
                "dominance_vs_canonical_alignment_v1": "DIVERGED",
                "canonical_session_bucket_v1": "US",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "dominance_accuracy_shadow_latest.json"
    md_path = tmp_path / "dominance_accuracy_shadow_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["accuracy_summary"]["symbol_count"] == 1
