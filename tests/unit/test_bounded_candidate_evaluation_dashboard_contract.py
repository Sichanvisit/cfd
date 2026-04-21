from backend.services.bounded_candidate_evaluation_dashboard_contract import (
    attach_bounded_candidate_evaluation_dashboard_fields_v1,
    build_bounded_candidate_evaluation_dashboard_contract_v1,
    generate_and_write_bounded_candidate_evaluation_dashboard_summary_v1,
)


def test_bounded_candidate_evaluation_dashboard_contract_exposes_expected_fields():
    contract = build_bounded_candidate_evaluation_dashboard_contract_v1()

    assert contract["contract_version"] == "bounded_candidate_evaluation_dashboard_contract_v1"
    assert contract["evaluation_outcome_enum_v1"] == [
        "PROMOTE",
        "KEEP_OBSERVING",
        "EXPIRE_WITHOUT_PROMOTION",
        "ROLLBACK",
    ]
    assert contract["evaluation_assessment_enum_v1"] == [
        "POSITIVE",
        "CAUTIOUS_POSITIVE",
        "NEUTRAL",
        "BLOCKED",
        "NEGATIVE",
    ]
    assert "bounded_candidate_evaluation_outcome_v1" in contract["row_level_fields_v1"]
    assert "bounded_candidate_evaluation_sample_coverage_v1" in contract["row_level_fields_v1"]


def test_attach_bounded_candidate_evaluation_dashboard_fields_marks_active_candidate_cautious_positive():
    rows = attach_bounded_candidate_evaluation_dashboard_fields_v1(
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
    assert row["bounded_candidate_evaluation_candidate_id_v1"] == "BTCUSD:flow.ambiguity_threshold"
    assert row["bounded_candidate_evaluation_outcome_v1"] == "KEEP_OBSERVING"
    assert row["bounded_candidate_evaluation_assessment_v1"] == "CAUTIOUS_POSITIVE"
    assert row["bounded_candidate_evaluation_candidate_hit_count_v1"] == 1
    assert row["bounded_candidate_evaluation_sample_coverage_v1"] == 0.5
    assert row["bounded_candidate_evaluation_promoted_like_transition_count_v1"] == 1
    assert row["bounded_candidate_evaluation_harmful_transition_count_v1"] == 0


def test_attach_bounded_candidate_evaluation_dashboard_fields_marks_blocked_candidate_rollback():
    rows = attach_bounded_candidate_evaluation_dashboard_fields_v1(
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
                "bounded_apply_cumulative_shift_by_key_v1": {
                    "flow.ambiguity_threshold": -0.2,
                },
            }
        }
    )

    row = rows["BTCUSD"]
    assert row["bounded_apply_session_state_v1"] == "BLOCKED"
    assert row["bounded_candidate_evaluation_outcome_v1"] == "ROLLBACK"
    assert row["bounded_candidate_evaluation_assessment_v1"] == "BLOCKED"


def test_generate_and_write_bounded_candidate_evaluation_dashboard_summary(tmp_path):
    report = generate_and_write_bounded_candidate_evaluation_dashboard_summary_v1(
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
    assert summary["active_apply_session_count"] == 1
    assert summary["candidate_outcome_count_summary"]["KEEP_OBSERVING"] == 2
    assert summary["candidate_assessment_count_summary"]["CAUTIOUS_POSITIVE"] == 1
    assert summary["candidate_assessment_count_summary"]["NEUTRAL"] == 1
