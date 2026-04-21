import json

from backend.services.local_structure_profile_contract import (
    attach_local_structure_profile_fields_v1,
    build_local_structure_profile_contract_v1,
    build_local_structure_profile_row_v1,
    generate_and_write_local_structure_summary_v1,
)


def test_build_local_structure_profile_contract_v1_has_expected_axes():
    contract = build_local_structure_profile_contract_v1()
    assert contract["contract_version"] == "local_structure_profile_contract_v1"
    assert contract["primary_axes_v1"] == [
        "few_candle_higher_low_state_v1",
        "few_candle_lower_high_state_v1",
        "breakout_hold_quality_v1",
        "body_drive_state_v1",
    ]


def test_local_structure_profile_surfaces_bull_continuation_favor():
    row = build_local_structure_profile_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "leg_direction": "UP",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "previous_box_low_retest_count": 2,
            "checkpoint_runtime_hold_quality_score": 0.61,
            "breakout_event_runtime_v1": {
                "breakout_detected": True,
                "breakout_direction": "UP",
                "breakout_state": "continuation_pullback",
                "breakout_retest_status": "passed",
                "breakout_strength": 0.44,
                "breakout_followthrough_score": 0.57,
                "breakout_failure_risk": 0.18,
            },
        }
    )

    assert row["few_candle_higher_low_state_v1"] == "CLEAN_HELD"
    assert row["breakout_hold_quality_v1"] == "STRONG"
    assert row["body_drive_state_v1"] == "STRONG_DRIVE"
    assert row["few_candle_structure_bias_v1"] == "CONTINUATION_FAVOR"


def test_local_structure_profile_surfaces_reversal_favor_on_failed_breakout():
    row = build_local_structure_profile_row_v1(
        {
            "state_strength_side_seed_v1": "BULL",
            "leg_direction": "DOWN",
            "previous_box_break_state": "BREAKOUT_FAILED",
            "previous_box_relation": "INSIDE",
            "checkpoint_runtime_hold_quality_score": 0.08,
            "breakout_event_runtime_v1": {
                "breakout_detected": True,
                "breakout_direction": "DOWN",
                "breakout_state": "failed_breakout",
                "breakout_retest_status": "failed",
                "breakout_strength": 0.31,
                "breakout_followthrough_score": 0.42,
                "breakout_failure_risk": 0.83,
            },
        }
    )

    assert row["breakout_hold_quality_v1"] == "FAILED"
    assert row["body_drive_state_v1"] == "COUNTER_DRIVE"
    assert row["few_candle_higher_low_state_v1"] == "BROKEN"
    assert row["few_candle_structure_bias_v1"] == "REVERSAL_FAVOR"


def test_attach_local_structure_profile_fields_v1_enriches_rows():
    enriched = attach_local_structure_profile_fields_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "leg_direction": "UP",
                "previous_box_break_state": "BREAKOUT_HELD",
                "previous_box_relation": "ABOVE",
                "checkpoint_runtime_hold_quality_score": 0.32,
                "breakout_event_runtime_v1": {
                    "breakout_detected": True,
                    "breakout_direction": "UP",
                    "breakout_retest_status": "passed",
                    "breakout_strength": 0.25,
                    "breakout_followthrough_score": 0.3,
                    "breakout_failure_risk": 0.25,
                },
            }
        }
    )

    assert "local_structure_profile_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["body_drive_state_v1"] in {"WEAK_DRIVE", "STRONG_DRIVE"}


def test_generate_and_write_local_structure_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_local_structure_summary_v1(
        {
            "NAS100": {
                "state_strength_side_seed_v1": "BULL",
                "leg_direction": "UP",
                "previous_box_break_state": "BREAKOUT_HELD",
                "previous_box_relation": "ABOVE",
                "previous_box_low_retest_count": 1,
                "checkpoint_runtime_hold_quality_score": 0.5,
                "breakout_event_runtime_v1": {
                    "breakout_detected": True,
                    "breakout_direction": "UP",
                    "breakout_state": "continuation_pullback",
                    "breakout_retest_status": "passed",
                    "breakout_strength": 0.33,
                    "breakout_followthrough_score": 0.4,
                    "breakout_failure_risk": 0.22,
                },
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "local_structure_summary_latest.json"
    md_path = tmp_path / "local_structure_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["summary"]["symbol_count"] == 1
