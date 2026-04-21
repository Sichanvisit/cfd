import json
from backend.services.bounded_calibration_candidate_contract import (
    build_bounded_calibration_candidate_contract_v1,
    build_bounded_calibration_candidate_row_v1,
    generate_and_write_bounded_calibration_candidate_summary_v1,
)


def test_bounded_calibration_candidate_contract_exposes_expected_fields():
    contract = build_bounded_calibration_candidate_contract_v1()

    assert contract["contract_version"] == "bounded_calibration_candidate_contract_v1"
    assert contract["upstream_alignment_enum_v1"] == [
        "READY_FROM_ROW",
        "READY_FROM_ATTACHED_UPSTREAM",
        "PARTIAL_UPSTREAM",
    ]
    assert contract["seed_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "FIXED_BLOCKED",
        "TUNABLE_SEED",
        "MIXED_SEED",
        "FILTERED_OUT",
        "REVIEW_PENDING",
    ]
    assert contract["filtering_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "FIXED_BLOCKED",
        "REVIEW_PENDING",
        "FILTERED_READY",
        "FILTERED_OUT",
        "CONFLICT_HOLD",
    ]
    assert contract["seed_priority_enum_v1"] == ["NONE", "LOW", "MEDIUM", "HIGH"]
    assert contract["seed_confidence_enum_v1"] == ["NONE", "LOW", "MEDIUM", "HIGH"]
    assert contract["candidate_status_enum_v1"] == ["PROPOSED", "FILTERED_OUT", "REVIEW_ONLY"]
    assert contract["validation_seed_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "SYMBOL_READY",
        "SYMBOL_PARTIAL",
        "CROSS_SYMBOL_REQUIRED",
        "REVIEW_ONLY",
    ]
    assert contract["candidate_outcome_enum_v1"] == [
        "PROMOTE",
        "KEEP_OBSERVING",
        "EXPIRE_WITHOUT_PROMOTION",
        "ROLLBACK",
    ]
    assert contract["candidate_graduation_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "SHADOW_REQUIRED",
        "REQUIRES_VALIDATION_SCOPE",
        "REVIEW_ONLY",
    ]
    assert contract["shadow_gate_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "ELIGIBLE",
        "BLOCKED_FIXED_OVERLAP",
        "BLOCKED_ANCHOR_REVIEW",
        "BLOCKED_LOW_SCORE",
        "BLOCKED_VALIDATION_SCOPE",
        "BLOCKED_NEUTRAL_DIRECTION",
    ]
    assert "bounded_calibration_candidate_seed_builder_ready_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_seed_state_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_seed_importance_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_seed_primary_key_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_seed_priority_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_seed_confidence_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_filtering_state_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_filtered_keys_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_ids_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_primary_candidate_id_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_primary_graduation_state_v1" in contract["row_level_fields_v1"]
    assert "bounded_calibration_candidate_flat_reason_summary_v1" in contract["row_level_fields_v1"]


def test_bounded_calibration_candidate_row_attaches_missing_upstream_layers():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "BTCUSD",
            "dominance_should_have_done_candidate_v1": True,
            "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
            "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_chain_shadow_delta_v1": "NEW_FLOW_OPPOSED",
            "flow_structure_gate_hard_disqualifiers_v1": ["AMBIGUITY_HIGH"],
            "flow_structure_gate_soft_score_v1": 1.0,
            "aggregate_conviction_v1": 0.2,
            "flow_persistence_v1": 0.3,
            "aggregate_ambiguity_penalty_v1": 0.35,
            "aggregate_veto_penalty_v1": 0.1,
            "flow_persistence_recency_weight_v1": 0.6,
            "aggregate_conviction_building_floor_v1": 0.6,
            "flow_persistence_building_floor_v1": 0.58,
        }
    )

    assert row["bounded_calibration_candidate_upstream_alignment_v1"] == "READY_FROM_ATTACHED_UPSTREAM"
    assert row["bounded_calibration_candidate_upstream_source_v1"] == "ATTACHED_BOTH"
    assert row["bounded_calibration_candidate_seed_builder_ready_v1"] is True
    assert row["flow_candidate_improvement_verdict_v1"] == "OVER_TIGHTENED"
    assert row["nas_btc_hard_opposed_truth_audit_state_v1"] == "TUNABLE_OVER_TIGHTEN_RISK"
    assert row["bounded_calibration_candidate_seed_state_v1"] == "TUNABLE_SEED"
    assert row["bounded_calibration_candidate_seed_keys_v1"] == [
        "flow.ambiguity_threshold",
        "flow.structure_soft_score_floor",
        "flow.conviction_building_floor",
        "flow.persistence_building_floor",
        "flow.ambiguity_penalty_scale",
        "flow.veto_penalty_scale",
        "flow.persistence_recency_weight_scale",
    ]
    assert row["bounded_calibration_candidate_seed_primary_key_v1"] == "flow.ambiguity_threshold"
    assert row["bounded_calibration_candidate_seed_primary_importance_v1"] > 0.0
    assert row["bounded_calibration_candidate_seed_importance_v1"]["flow.ambiguity_threshold"]["truth_pressure"] == 1.0
    assert row["bounded_calibration_candidate_seed_importance_v1"]["flow.ambiguity_threshold"]["delta_severity"] == 1.0
    assert row["bounded_calibration_candidate_seed_relevance_score_v1"] > 0.0
    assert row["bounded_calibration_candidate_seed_safety_score_v1"] == 0.9
    assert row["bounded_calibration_candidate_seed_repeatability_score_v1"] == 0.4
    assert row["bounded_calibration_candidate_seed_priority_score_v1"] > 0.0
    assert row["bounded_calibration_candidate_seed_priority_v1"] == "HIGH"
    assert row["bounded_calibration_candidate_seed_confidence_v1"] == "HIGH"
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_READY"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == [
        "flow.ambiguity_threshold",
        "flow.conviction_building_floor",
    ]
    assert "flow.ambiguity_penalty_scale" in row["bounded_calibration_candidate_filtered_out_keys_v1"]
    assert row["bounded_calibration_candidate_filter_conflict_flag_v1"] is False
    assert row["bounded_calibration_candidate_attached_layers_v1"] == [
        "flow_candidate_improvement_review",
        "nas_btc_hard_opposed_truth_audit",
    ]
    assert row["bounded_calibration_candidate_missing_after_attach_v1"] == []


def test_bounded_calibration_candidate_row_marks_existing_upstream_as_row_only():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "XAUUSD",
            "flow_candidate_improvement_verdict_v1": "REVIEW_PENDING",
            "nas_btc_hard_opposed_truth_audit_state_v1": "NOT_APPLICABLE",
        }
    )

    assert row["bounded_calibration_candidate_upstream_alignment_v1"] == "READY_FROM_ROW"
    assert row["bounded_calibration_candidate_upstream_source_v1"] == "ROW_ONLY"
    assert row["bounded_calibration_candidate_attached_layers_v1"] == ["xau_refined_gate_timebox_audit"]
    assert row["bounded_calibration_candidate_seed_builder_ready_v1"] is True
    assert row["bounded_calibration_candidate_seed_state_v1"] == "MIXED_SEED"


def test_bounded_calibration_candidate_row_marks_fixed_blocked_seed_state():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "NAS100",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "FIXED_HARD_OPPOSED",
            "nas_btc_hard_opposed_learning_state_v1": "FIXED_BLOCKED",
            "nas_btc_hard_opposed_learning_keys_v1": [],
        }
    )

    assert row["bounded_calibration_candidate_upstream_source_v1"] == "ROW_ONLY"
    assert row["bounded_calibration_candidate_seed_state_v1"] == "FIXED_BLOCKED"
    assert row["bounded_calibration_candidate_seed_keys_v1"] == []
    assert row["bounded_calibration_candidate_seed_primary_key_v1"] == ""
    assert row["bounded_calibration_candidate_seed_priority_v1"] == "NONE"
    assert row["bounded_calibration_candidate_seed_confidence_v1"] == "NONE"
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FIXED_BLOCKED"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == []


def test_bounded_calibration_candidate_summary_surfaces_fixed_blocked_review_anchor():
    report = generate_and_write_bounded_calibration_candidate_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "flow_candidate_improvement_verdict_v1": "SAFE_TIGHTENING",
                "flow_candidate_truth_state_v1": "NO_CANDIDATE",
                "flow_chain_shadow_delta_v1": "NEW_FLOW_OPPOSED",
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "flow_structure_gate_hard_disqualifiers_v1": ["POLARITY_MISMATCH"],
                "flow_structure_gate_soft_score_v1": 1.2,
                "nas_btc_hard_opposed_truth_audit_state_v1": "FIXED_HARD_OPPOSED",
                "nas_btc_hard_opposed_learning_state_v1": "FIXED_BLOCKED",
                "nas_btc_hard_opposed_learning_keys_v1": [
                    "flow.structure_soft_score_floor",
                    "flow.conviction_building_floor",
                ],
                "aggregate_conviction_v1": 0.07,
                "aggregate_conviction_building_floor_v1": 0.6,
                "flow_persistence_v1": 0.22,
                "flow_persistence_building_floor_v1": 0.58,
            }
        }
    )

    rows = report["rows_by_symbol"]
    nas = rows["NAS100"]
    candidate_objects = report["candidate_objects_v1"]

    assert nas["bounded_calibration_candidate_primary_status_v1"] == "REVIEW_ONLY"
    assert nas["bounded_calibration_candidate_primary_anchor_role_v1"] == "FIXED_REVIEW_ANCHOR"
    assert any(item["candidate_anchor_role_v1"] == "FIXED_REVIEW_ANCHOR" for item in candidate_objects.values())


def test_bounded_calibration_candidate_row_marks_mixed_seed_state():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "BTCUSD",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
            "nas_btc_hard_opposed_learning_state_v1": "MIXED_REVIEW",
            "nas_btc_hard_opposed_learning_keys_v1": ["flow.ambiguity_threshold"],
        }
    )

    assert row["bounded_calibration_candidate_seed_state_v1"] == "MIXED_SEED"
    assert row["bounded_calibration_candidate_seed_keys_v1"] == ["flow.ambiguity_threshold"]
    assert row["bounded_calibration_candidate_seed_importance_v1"]["flow.ambiguity_threshold"]["tunable_purity"] == 0.6
    assert row["bounded_calibration_candidate_seed_safety_score_v1"] == 0.5
    assert row["bounded_calibration_candidate_seed_confidence_v1"] == "LOW"
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_READY"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == ["flow.ambiguity_threshold"]


def test_bounded_calibration_candidate_row_surfaces_xau_review_anchor_seed():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "XAUUSD",
            "aggregate_conviction_building_floor_v1": 0.45,
            "flow_persistence_building_floor_v1": 0.48,
        }
    )

    assert "xau_refined_gate_timebox_audit" in row["bounded_calibration_candidate_attached_layers_v1"]
    assert row["bounded_calibration_candidate_seed_state_v1"] == "MIXED_SEED"
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_READY"
    assert row["bounded_calibration_candidate_seed_confidence_v1"] == "LOW"
    assert "flow.conviction_building_floor" in row["bounded_calibration_candidate_seed_keys_v1"]
    assert "flow.persistence_building_floor" in row["bounded_calibration_candidate_seed_keys_v1"]
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == [
        "flow.ambiguity_threshold",
        "flow.conviction_building_floor",
    ]


def test_bounded_calibration_candidate_row_keeps_btc_widen_review_as_mixed_seed():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "BTCUSD",
            "flow_candidate_improvement_verdict_v1": "MISSED_IMPROVEMENT",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "NON_OPPOSED",
            "nas_btc_hard_opposed_learning_state_v1": "NOT_APPLICABLE",
            "nas_btc_hard_opposed_learning_keys_v1": [
                "flow.ambiguity_threshold",
                "flow.conviction_building_floor",
            ],
            "aggregate_ambiguity_penalty_v1": 0.2,
            "aggregate_conviction_v1": 0.25,
            "aggregate_conviction_building_floor_v1": 0.6,
        }
    )

    assert row["bounded_calibration_candidate_seed_state_v1"] == "MIXED_SEED"
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_READY"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == [
        "flow.conviction_building_floor",
        "flow.ambiguity_threshold",
    ]


def test_bounded_calibration_candidate_row_marks_filtered_out_without_learning_keys():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "EURUSD",
            "flow_candidate_improvement_verdict_v1": "MISSED_IMPROVEMENT",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "NOT_APPLICABLE",
            "nas_btc_hard_opposed_learning_state_v1": "NOT_APPLICABLE",
            "nas_btc_hard_opposed_learning_keys_v1": ["flow.persistence_building_floor"],
        }
    )

    assert row["bounded_calibration_candidate_seed_state_v1"] == "FILTERED_OUT"
    assert row["bounded_calibration_candidate_seed_keys_v1"] == ["flow.persistence_building_floor"]
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_OUT"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == []


def test_bounded_calibration_candidate_row_suppresses_recently_rolled_back_keys():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "BTCUSD",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "TUNABLE_OVER_TIGHTEN_RISK",
            "nas_btc_hard_opposed_learning_state_v1": "LEARNING_CANDIDATE",
            "nas_btc_hard_opposed_learning_keys_v1": [
                "flow.ambiguity_threshold",
                "flow.conviction_building_floor",
            ],
            "bounded_calibration_candidate_recent_rollback_keys_v1": ["flow.ambiguity_threshold"],
            "aggregate_conviction_v1": 0.2,
            "aggregate_conviction_building_floor_v1": 0.6,
        }
    )

    assert row["bounded_calibration_candidate_filtering_state_v1"] == "FILTERED_READY"
    assert row["bounded_calibration_candidate_filtered_keys_v1"] == ["flow.conviction_building_floor"]
    assert "flow.ambiguity_threshold" in row["bounded_calibration_candidate_filtered_out_keys_v1"]


def test_bounded_calibration_candidate_row_detects_conflicting_direction_hold():
    row = build_bounded_calibration_candidate_row_v1(
        {
            "symbol": "BTCUSD",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
            "nas_btc_hard_opposed_truth_audit_state_v1": "TUNABLE_OVER_TIGHTEN_RISK",
            "nas_btc_hard_opposed_learning_state_v1": "LEARNING_CANDIDATE",
            "nas_btc_hard_opposed_learning_keys_v1": [
                "flow.ambiguity_threshold",
                "flow.conviction_building_floor",
            ],
            "bounded_calibration_candidate_seed_direction_overrides_v1": {
                "flow.ambiguity_threshold": "RELAX",
                "flow.conviction_building_floor": "TIGHTEN",
            },
            "aggregate_ambiguity_penalty_v1": 0.35,
            "aggregate_conviction_v1": 0.2,
            "aggregate_conviction_building_floor_v1": 0.6,
        }
    )

    assert row["bounded_calibration_candidate_filter_conflict_flag_v1"] is True
    assert row["bounded_calibration_candidate_filtering_state_v1"] == "CONFLICT_HOLD"
    assert len(row["bounded_calibration_candidate_filtered_keys_v1"]) == 1


def test_generate_and_write_bounded_calibration_candidate_summary(tmp_path):
    report = generate_and_write_bounded_calibration_candidate_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "dominance_should_have_done_candidate_v1": True,
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
                "new_flow_enabled_state_v1": "FLOW_OPPOSED",
                "flow_chain_shadow_delta_v1": "NEW_FLOW_OPPOSED",
                "flow_structure_gate_hard_disqualifiers_v1": ["AMBIGUITY_HIGH"],
                "flow_structure_gate_soft_score_v1": 1.0,
                "aggregate_conviction_v1": 0.2,
                "flow_persistence_v1": 0.3,
                "aggregate_ambiguity_penalty_v1": 0.35,
                "aggregate_veto_penalty_v1": 0.1,
                "flow_persistence_recency_weight_v1": 0.6,
                "aggregate_conviction_building_floor_v1": 0.6,
                "flow_persistence_building_floor_v1": 0.58,
            }
        },
        shadow_auto_dir=tmp_path,
    )

    summary = report["summary"]
    json_path = tmp_path / "bounded_calibration_candidate_latest.json"
    markdown_path = tmp_path / "bounded_calibration_candidate_latest.md"

    assert summary["status"] == "READY"
    assert summary["seed_builder_ready_count"] == 1
    assert summary["bounded_calibration_candidate_upstream_source_count_summary"]["ATTACHED_BOTH"] == 1
    assert summary["bounded_calibration_candidate_seed_state_count_summary"]["TUNABLE_SEED"] == 1
    assert summary["bounded_calibration_candidate_seed_key_count_summary"]["flow.ambiguity_threshold"] == 1
    assert summary["bounded_calibration_candidate_seed_primary_key_count_summary"]["flow.ambiguity_threshold"] == 1
    assert summary["bounded_calibration_candidate_seed_priority_count_summary"]["HIGH"] == 1
    assert summary["bounded_calibration_candidate_seed_confidence_count_summary"]["HIGH"] == 1
    assert summary["bounded_calibration_candidate_filtering_state_count_summary"]["FILTERED_READY"] == 1
    assert summary["bounded_calibration_candidate_filtered_key_count_summary"]["flow.ambiguity_threshold"] == 1
    assert summary["candidate_count"] == 2
    assert summary["candidate_symbol_count_summary"]["BTCUSD"] == 2
    assert summary["candidate_learning_key_count_summary"]["flow.ambiguity_threshold"] == 1
    assert summary["candidate_learning_key_count_summary"]["flow.conviction_building_floor"] == 1
    assert summary["candidate_status_count_summary"]["PROPOSED"] == 2
    assert summary["candidate_direction_count_summary"]["RELAX"] == 2
    assert summary["candidate_confidence_count_summary"]["HIGH"] == 2
    assert summary["candidate_validation_seed_state_count_summary"]["SYMBOL_READY"] == 2
    assert summary["candidate_outcome_count_summary"]["KEEP_OBSERVING"] == 2
    assert summary["candidate_graduation_state_count_summary"]["SHADOW_REQUIRED"] == 2
    candidate_catalog = report["candidate_catalog_v1"]
    candidate_objects = report["candidate_objects_v1"]
    assert "BTCUSD:flow.ambiguity_threshold" in candidate_catalog
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["affected_row_count"] == 1
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["pure_tunable_count"] == 1
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["mixed_row_count"] == 0
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["truth_error_type_count_summary"][
        "CONTINUATION_UNDERPROMOTED"
    ] == 1
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["alignment_count_summary"]["REGRESSED"] == 1
    assert candidate_catalog["BTCUSD:flow.ambiguity_threshold"]["direction_count_summary"]["RELAX"] == 1
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["status"] == "PROPOSED"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["direction"] == "RELAX"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["current_value"] == 0.4
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["proposed_value"] < 0.4
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["max_allowed_delta"] == 0.05
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["scope"]["apply_mode"] == "shadow_only"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["validation_seed_state_v1"] == "SYMBOL_READY"
    assert (
        len(
            candidate_objects["BTCUSD:flow.ambiguity_threshold"]["validation_scope_v1"][
                "same_symbol_retained_window_ids_v1"
            ]
        )
        >= 1
    )
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["validation_scope_v1"][
        "same_symbol_recent_live_windows_v1"
    ] == ["latest_signal_by_symbol"]
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_outcome_v1"] == "KEEP_OBSERVING"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_graduation_state_v1"] == "SHADOW_REQUIRED"
    assert "REQUIRES_SHADOW_APPLY" in candidate_objects["BTCUSD:flow.ambiguity_threshold"][
        "candidate_graduation_blockers_v1"
    ]
    assert (
        candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_graduation_requirements_v1"][
            "minimum_shadow_windows_required_v1"
        ]
        == 2
    )
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["rollback"]["rollback_to"] == 0.4
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_ids_v1"] == [
        "BTCUSD:flow.ambiguity_threshold",
        "BTCUSD:flow.conviction_building_floor",
    ]
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_candidate_id_v1"] == (
        "BTCUSD:flow.ambiguity_threshold"
    )
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_status_v1"] == "PROPOSED"
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_outcome_v1"] == "KEEP_OBSERVING"
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_graduation_state_v1"] == (
        "SHADOW_REQUIRED"
    )
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_validation_state_v1"] == (
        "SYMBOL_READY"
    )
    assert "REQUIRES_SHADOW_APPLY" in report["rows_by_symbol"]["BTCUSD"][
        "bounded_calibration_candidate_primary_blockers_v1"
    ]
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["status"] == "READY"
    assert markdown_path.exists()


def test_generate_and_write_bounded_calibration_candidate_summary_marks_mixed_seed_candidates_review_only(tmp_path):
    report = generate_and_write_bounded_calibration_candidate_summary_v1(
        {
            "BTCUSD": {
                "symbol": "BTCUSD",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "flow_candidate_truth_state_v1": "WIDEN_EXPECTED",
                "nas_btc_hard_opposed_truth_audit_state_v1": "MIXED_REVIEW",
                "nas_btc_hard_opposed_learning_state_v1": "MIXED_REVIEW",
                "nas_btc_hard_opposed_learning_keys_v1": [
                    "flow.ambiguity_threshold",
                    "flow.conviction_building_floor",
                ],
                "aggregate_ambiguity_penalty_v1": 0.35,
                "aggregate_conviction_v1": 0.2,
                "aggregate_conviction_building_floor_v1": 0.6,
            }
        },
        shadow_auto_dir=tmp_path,
    )

    summary = report["summary"]
    candidate_objects = report["candidate_objects_v1"]

    assert summary["candidate_status_count_summary"]["PROPOSED"] == 2
    assert summary["candidate_validation_seed_state_count_summary"]["SYMBOL_READY"] == 2
    assert summary["candidate_outcome_count_summary"]["KEEP_OBSERVING"] == 2
    assert summary["candidate_graduation_state_count_summary"]["SHADOW_REQUIRED"] == 2
    assert summary["candidate_shadow_gate_state_count_summary"]["ELIGIBLE"] == 2
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["status"] == "PROPOSED"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["confidence"] == "LOW"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["direction"] == "RELAX"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["validation_seed_state_v1"] == "SYMBOL_READY"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_outcome_v1"] == "KEEP_OBSERVING"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_graduation_state_v1"] == "SHADOW_REQUIRED"
    assert candidate_objects["BTCUSD:flow.ambiguity_threshold"]["candidate_shadow_gate_state_v1"] == "ELIGIBLE"
    assert "REQUIRES_SHADOW_APPLY" in candidate_objects["BTCUSD:flow.ambiguity_threshold"][
        "candidate_graduation_blockers_v1"
    ]
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_status_v1"] == "PROPOSED"
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_graduation_state_v1"] == (
        "SHADOW_REQUIRED"
    )
    assert report["rows_by_symbol"]["BTCUSD"]["bounded_calibration_candidate_primary_shadow_gate_state_v1"] == (
        "ELIGIBLE"
    )


def test_generate_and_write_bounded_calibration_candidate_summary_keeps_fixed_overlap_mixed_candidates_review_only(tmp_path):
    report = generate_and_write_bounded_calibration_candidate_summary_v1(
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
            }
        },
        shadow_auto_dir=tmp_path,
    )

    summary = report["summary"]
    candidate_objects = report["candidate_objects_v1"]

    assert summary["candidate_status_count_summary"]["REVIEW_ONLY"] == 2
    assert summary["candidate_graduation_state_count_summary"]["REVIEW_ONLY"] == 2
    assert summary["candidate_shadow_gate_state_count_summary"]["BLOCKED_FIXED_OVERLAP"] == 2
    assert candidate_objects["NAS100:flow.ambiguity_threshold"]["status"] == "REVIEW_ONLY"
    assert candidate_objects["NAS100:flow.ambiguity_threshold"]["candidate_shadow_gate_state_v1"] == (
        "BLOCKED_FIXED_OVERLAP"
    )
    assert report["rows_by_symbol"]["NAS100"]["bounded_calibration_candidate_primary_status_v1"] == "REVIEW_ONLY"
    assert report["rows_by_symbol"]["NAS100"]["bounded_calibration_candidate_primary_shadow_gate_state_v1"] == (
        "BLOCKED_FIXED_OVERLAP"
    )


def test_generate_and_write_bounded_calibration_candidate_summary_keeps_xau_anchor_candidates_review_only(tmp_path):
    report = generate_and_write_bounded_calibration_candidate_summary_v1(
        {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "aggregate_conviction_building_floor_v1": 0.45,
                "flow_persistence_building_floor_v1": 0.48,
            }
        },
        shadow_auto_dir=tmp_path,
    )

    summary = report["summary"]
    candidate_objects = report["candidate_objects_v1"]

    assert summary["candidate_count"] == 2
    assert summary["candidate_symbol_count_summary"]["XAUUSD"] == 2
    assert summary["candidate_status_count_summary"]["REVIEW_ONLY"] == 2
    assert summary["candidate_outcome_count_summary"]["KEEP_OBSERVING"] == 2
    assert candidate_objects["XAUUSD:flow.ambiguity_threshold"]["status"] == "REVIEW_ONLY"
    assert candidate_objects["XAUUSD:flow.ambiguity_threshold"]["direction"] == "NEUTRAL"
    assert candidate_objects["XAUUSD:flow.ambiguity_threshold"]["candidate_anchor_role_v1"] == "XAU_REVIEW_ANCHOR"
    assert candidate_objects["XAUUSD:flow.ambiguity_threshold"]["validation_seed_state_v1"] == "REVIEW_ONLY"
    assert candidate_objects["XAUUSD:flow.ambiguity_threshold"]["candidate_graduation_state_v1"] == "REVIEW_ONLY"
    assert report["rows_by_symbol"]["XAUUSD"]["bounded_calibration_candidate_ids_v1"] == [
        "XAUUSD:flow.ambiguity_threshold",
        "XAUUSD:flow.conviction_building_floor",
    ]
    assert report["rows_by_symbol"]["XAUUSD"]["bounded_calibration_candidate_primary_status_v1"] == "REVIEW_ONLY"
    assert report["rows_by_symbol"]["XAUUSD"]["bounded_calibration_candidate_primary_graduation_state_v1"] == (
        "REVIEW_ONLY"
    )
    assert report["rows_by_symbol"]["XAUUSD"]["bounded_calibration_candidate_primary_anchor_role_v1"] == (
        "XAU_REVIEW_ANCHOR"
    )
    assert "REQUIRES_PURE_TUNABLE_EVIDENCE" in report["rows_by_symbol"]["XAUUSD"][
        "bounded_calibration_candidate_primary_blockers_v1"
    ]
