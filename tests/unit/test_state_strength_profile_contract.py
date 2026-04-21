import json

from backend.services.state_strength_profile_contract import (
    attach_state_strength_profile_fields_v1,
    build_state_strength_profile_contract_v1,
    build_state_strength_profile_row_v1,
    generate_and_write_state_strength_summary_v1,
)


def test_build_state_strength_profile_contract_v1_has_fixed_gap_definition():
    contract = build_state_strength_profile_contract_v1()
    assert contract["contract_version"] == "state_strength_profile_contract_v1"
    assert contract["dominance_gap_definition_v1"] == "continuation_integrity - reversal_evidence"


def test_state_strength_profile_prefers_bull_continuation_with_friction():
    row = build_state_strength_profile_row_v1(
        {
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_score": 0.82,
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "leg_direction": "UP",
            "checkpoint_transition_reason": "checkpoint_continuation",
            "breakout_candidate_direction": "UP",
            "consumer_check_side": "SELL",
            "consumer_check_reason": "upper_reject_confirm",
            "blocked_by": "energy_soft_block",
            "action_none_reason": "execution_soft_blocked",
            "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
            "belief_candidate_recommended_family": "reduce_alert",
            "barrier_candidate_recommended_family": "wait_bias",
        }
    )

    assert row["state_strength_side_seed_v1"] == "BULL"
    assert row["state_strength_dominant_side_v1"] == "BULL"
    assert row["state_strength_dominant_mode_v1"] == "CONTINUATION_WITH_FRICTION"
    assert row["state_strength_dominance_gap_v1"] == round(
        row["state_strength_continuation_integrity_v1"] - row["state_strength_reversal_evidence_v1"],
        4,
    )


def test_friction_does_not_flip_side_when_bull_seed_is_strong():
    row = build_state_strength_profile_row_v1(
        {
            "directional_continuation_overlay_direction": "UP",
            "directional_continuation_overlay_enabled": True,
            "directional_continuation_overlay_score": 0.74,
            "htf_alignment_state": "WITH_HTF",
            "previous_box_break_state": "BREAKOUT_HELD",
            "previous_box_relation": "ABOVE",
            "leg_direction": "UP",
            "consumer_check_side": "SELL",
            "consumer_check_reason": "upper_reject_probe_observe",
            "blocked_by": "energy_soft_block",
            "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
        }
    )

    assert row["state_strength_side_seed_v1"] == "BULL"
    assert row["state_strength_dominant_side_v1"] == "BULL"


def test_attach_state_strength_profile_fields_v1_enriches_rows():
    enriched = attach_state_strength_profile_fields_v1(
        {
            "NAS100": {
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_score": 0.7,
            }
        }
    )
    assert "state_strength_profile_v1" in enriched["NAS100"]
    assert enriched["NAS100"]["state_strength_side_seed_v1"] == "BULL"


def test_generate_and_write_state_strength_summary_v1_writes_artifacts(tmp_path):
    report = generate_and_write_state_strength_summary_v1(
        {
            "NAS100": {
                "directional_continuation_overlay_direction": "UP",
                "directional_continuation_overlay_enabled": True,
                "directional_continuation_overlay_score": 0.72,
                "htf_alignment_state": "WITH_HTF",
                "previous_box_break_state": "BREAKOUT_HELD",
                "previous_box_relation": "ABOVE",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_strength_summary_latest.json"
    md_path = tmp_path / "state_strength_summary_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["summary"]["symbol_count"] == 1
