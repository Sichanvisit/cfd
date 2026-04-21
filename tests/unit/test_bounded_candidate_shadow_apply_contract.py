from backend.services.bounded_candidate_shadow_apply_contract import (
    attach_bounded_candidate_shadow_apply_fields_v1,
    build_bounded_candidate_shadow_apply_contract_v1,
    generate_and_write_bounded_candidate_shadow_apply_summary_v1,
)


def test_bounded_candidate_shadow_apply_contract_exposes_expected_fields():
    contract = build_bounded_candidate_shadow_apply_contract_v1()

    assert contract["contract_version"] == "bounded_candidate_shadow_apply_contract_v1"
    assert contract["apply_mode_enum_v1"] == ["NONE", "SHADOW_ONLY"]
    assert contract["apply_session_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "ACTIVE",
        "HOLD",
        "BLOCKED",
    ]
    assert contract["drift_guard_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "CLEAR",
        "BLOCKED_BY_CUMULATIVE_SHIFT",
    ]
    assert "bounded_apply_session_id_v1" in contract["row_level_fields_v1"]
    assert "flow_support_state_before_v1" in contract["row_level_fields_v1"]
    assert "flow_support_state_after_v1" in contract["row_level_fields_v1"]


def test_attach_bounded_candidate_shadow_apply_fields_activates_shadow_required_btc_candidate():
    rows = attach_bounded_candidate_shadow_apply_fields_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "flow_candidate_improvement_verdict_v1": "MISSED_IMPROVEMENT",
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_review_alignment_v1": "MISSED",
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "NON_OPPOSED",
                "nas_btc_hard_opposed_learning_state_v1": "NOT_APPLICABLE",
                "nas_btc_hard_opposed_learning_keys_v1": [
                    "flow.ambiguity_threshold",
                    "flow.conviction_building_floor",
                ],
                "aggregate_ambiguity_penalty_v1": 0.2,
                "aggregate_conviction_v1": 0.42,
                "aggregate_conviction_building_floor_v1": 0.45,
                "flow_persistence_v1": 0.62,
                "flow_persistence_building_floor_v1": 0.58,
                "flow_support_state_v1": "FLOW_UNCONFIRMED",
                "flow_structure_gate_v1": "ELIGIBLE",
            }
        }
    )

    row = rows["BTCUSD"]

    assert row["bounded_calibration_candidate_primary_status_v1"] == "PROPOSED"
    assert row["bounded_calibration_candidate_primary_graduation_state_v1"] == "SHADOW_REQUIRED"
    assert row["bounded_apply_session_state_v1"] == "ACTIVE"
    assert row["bounded_apply_mode_v1"] == "SHADOW_ONLY"
    assert row["bounded_apply_candidate_id_v1"] == "BTCUSD:flow.ambiguity_threshold"
    assert row["bounded_apply_scope_match_v1"] is True
    assert row["flow_support_state_before_v1"] == "FLOW_UNCONFIRMED"
    assert row["flow_support_state_after_v1"] == "FLOW_BUILDING"
    assert row["flow_state_change_type_v1"] == "FLOW_UNCONFIRMED_TO_FLOW_BUILDING"
    assert row["candidate_effect_direction_v1"] == "RELAX"
    assert row["bounded_apply_drift_guard_state_v1"] == "CLEAR"


def test_attach_bounded_candidate_shadow_apply_keeps_review_only_nas_blocked():
    rows = attach_bounded_candidate_shadow_apply_fields_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_review_alignment_v1": "REGRESSED",
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
                "nas_btc_hard_opposed_learning_state_v1": "MIXED_REVIEW",
                "nas_btc_hard_opposed_learning_keys_v1": [
                    "flow.ambiguity_threshold",
                    "flow.conviction_building_floor",
                ],
                "nas_btc_hard_opposed_fixed_blockers_v1": ["POLARITY_MISMATCH"],
                "aggregate_ambiguity_penalty_v1": 0.35,
                "aggregate_conviction_v1": 0.2,
                "aggregate_conviction_building_floor_v1": 0.6,
                "flow_persistence_v1": 0.3,
                "flow_persistence_building_floor_v1": 0.58,
                "flow_support_state_v1": "FLOW_OPPOSED",
                "flow_structure_gate_v1": "INELIGIBLE",
            }
        }
    )

    row = rows["NAS100"]

    assert row["bounded_calibration_candidate_primary_status_v1"] == "REVIEW_ONLY"
    assert row["bounded_calibration_candidate_primary_shadow_gate_state_v1"] == "BLOCKED_FIXED_OVERLAP"
    assert row["bounded_apply_session_state_v1"] == "NOT_APPLICABLE"
    assert row["bounded_apply_candidate_id_v1"] == ""
    assert row["bounded_apply_block_reason_v1"] == "PRIMARY_CANDIDATE_NOT_SHADOW_REQUIRED"


def test_generate_and_write_bounded_candidate_shadow_apply_summary(tmp_path):
    report = generate_and_write_bounded_candidate_shadow_apply_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "flow_candidate_improvement_verdict_v1": "MISSED_IMPROVEMENT",
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "flow_candidate_review_alignment_v1": "MISSED",
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "NON_OPPOSED",
                "nas_btc_hard_opposed_learning_state_v1": "NOT_APPLICABLE",
                "nas_btc_hard_opposed_learning_keys_v1": [
                    "flow.ambiguity_threshold",
                    "flow.conviction_building_floor",
                ],
                "aggregate_ambiguity_penalty_v1": 0.2,
                "aggregate_conviction_v1": 0.42,
                "aggregate_conviction_building_floor_v1": 0.45,
                "flow_persistence_v1": 0.62,
                "flow_persistence_building_floor_v1": 0.58,
                "flow_support_state_v1": "FLOW_UNCONFIRMED",
                "flow_structure_gate_v1": "ELIGIBLE",
            }
        },
        shadow_auto_dir=tmp_path,
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["shadow_required_candidate_count"] == 2
    assert summary["apply_session_count"] == 2
    assert summary["apply_session_state_count_summary"]["ACTIVE"] == 1
    assert summary["apply_session_state_count_summary"]["HOLD"] == 1
    assert summary["row_apply_session_state_count_summary"]["ACTIVE"] == 1
    assert summary["row_flow_state_change_count_summary"]["FLOW_UNCONFIRMED_TO_FLOW_BUILDING"] == 1
