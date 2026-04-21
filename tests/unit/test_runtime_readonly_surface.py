import json

from backend.services.runtime_readonly_surface import (
    attach_runtime_readonly_surface_fields_v1,
    build_runtime_readonly_surface_contract_v1,
    build_runtime_readonly_surface_row_v1,
    generate_and_write_runtime_readonly_surface_summary_v1,
)


def test_build_runtime_readonly_surface_contract_v1_has_veto_tiers():
    contract = build_runtime_readonly_surface_contract_v1()
    assert contract["contract_version"] == "runtime_readonly_surface_contract_v1"
    assert contract["consumer_veto_tier_enum_v1"] == [
        "FRICTION_ONLY",
        "BOUNDARY_WARNING",
        "REVERSAL_OVERRIDE",
    ]


def test_runtime_readonly_surface_marks_friction_only_for_bull_continuation():
    row = build_runtime_readonly_surface_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BULL",
            "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
            "state_strength_continuation_integrity_v1": 0.62,
            "state_strength_reversal_evidence_v1": 0.18,
            "state_strength_friction_v1": 0.41,
            "state_strength_caution_level_v1": "MEDIUM",
            "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
            "breakout_hold_quality_v1": "STABLE",
            "body_drive_state_v1": "WEAK_DRIVE",
            "consumer_check_reason": "upper_reject_confirm",
            "blocked_by": "energy_soft_block",
        }
    )

    assert row["consumer_veto_tier_v1"] == "FRICTION_ONLY"


def test_runtime_readonly_surface_marks_boundary_warning_for_mixed_structure():
    row = build_runtime_readonly_surface_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BULL",
            "state_strength_dominant_mode_v1": "BOUNDARY",
            "state_strength_continuation_integrity_v1": 0.44,
            "state_strength_reversal_evidence_v1": 0.31,
            "state_strength_friction_v1": 0.22,
            "state_strength_caution_level_v1": "HIGH",
            "few_candle_structure_bias_v1": "MIXED",
            "breakout_hold_quality_v1": "WEAK",
            "body_drive_state_v1": "NEUTRAL",
        }
    )

    assert row["consumer_veto_tier_v1"] == "BOUNDARY_WARNING"


def test_runtime_readonly_surface_marks_reversal_override_for_failed_breakout():
    row = build_runtime_readonly_surface_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "state_strength_dominant_side_v1": "BEAR",
            "state_strength_dominant_mode_v1": "REVERSAL_RISK",
            "state_strength_continuation_integrity_v1": 0.21,
            "state_strength_reversal_evidence_v1": 0.74,
            "state_strength_friction_v1": 0.18,
            "state_strength_caution_level_v1": "HIGH",
            "few_candle_structure_bias_v1": "REVERSAL_FAVOR",
            "breakout_hold_quality_v1": "FAILED",
            "body_drive_state_v1": "COUNTER_DRIVE",
        }
    )

    assert row["consumer_veto_tier_v1"] == "REVERSAL_OVERRIDE"


def test_attach_runtime_readonly_surface_fields_v1_enriches_rows():
    enriched = attach_runtime_readonly_surface_fields_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "state_strength_dominant_side_v1": "BULL",
                "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "state_strength_continuation_integrity_v1": 0.52,
                "state_strength_reversal_evidence_v1": 0.16,
                "state_strength_friction_v1": 0.35,
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "breakout_hold_quality_v1": "STABLE",
                "body_drive_state_v1": "WEAK_DRIVE",
            }
        }
    )

    assert "runtime_readonly_surface_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["consumer_veto_tier_v1"] in {
        "FRICTION_ONLY",
        "BOUNDARY_WARNING",
        "REVERSAL_OVERRIDE",
    }


def test_generate_and_write_runtime_readonly_surface_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_runtime_readonly_surface_summary_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "state_strength_dominant_side_v1": "BULL",
                "state_strength_dominant_mode_v1": "CONTINUATION_WITH_FRICTION",
                "state_strength_continuation_integrity_v1": 0.56,
                "state_strength_reversal_evidence_v1": 0.17,
                "state_strength_friction_v1": 0.34,
                "few_candle_structure_bias_v1": "CONTINUATION_FAVOR",
                "breakout_hold_quality_v1": "STABLE",
                "body_drive_state_v1": "WEAK_DRIVE",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "runtime_readonly_surface_summary_latest.json"
    md_path = tmp_path / "runtime_readonly_surface_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["summary"]["symbol_count"] == 1
