import json

from backend.services.nas_btc_hard_opposed_truth_audit import (
    build_nas_btc_hard_opposed_truth_audit_contract_v1,
    build_nas_btc_hard_opposed_truth_audit_row_v1,
    generate_and_write_nas_btc_hard_opposed_truth_audit_summary_v1,
)


def test_nas_btc_hard_opposed_truth_audit_contract_exposes_expected_fields():
    contract = build_nas_btc_hard_opposed_truth_audit_contract_v1()
    assert contract["contract_version"] == "nas_btc_hard_opposed_truth_audit_contract_v1"
    assert "nas_btc_hard_opposed_tunable_drivers_v1" in contract["row_level_fields_v1"]
    assert "nas_btc_hard_opposed_learning_keys_v1" in contract["row_level_fields_v1"]


def test_nas_btc_hard_opposed_truth_audit_marks_fixed_blocked():
    row = build_nas_btc_hard_opposed_truth_audit_row_v1(
        {
            "symbol": "NAS100",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_structure_gate_hard_disqualifiers_v1": ["POLARITY_MISMATCH"],
            "flow_structure_gate_soft_score_v1": 4.0,
            "aggregate_conviction_v1": 0.7,
            "flow_persistence_v1": 0.7,
        }
    )
    assert row["nas_btc_hard_opposed_truth_audit_state_v1"] == "FIXED_HARD_OPPOSED"
    assert row["nas_btc_hard_opposed_learning_state_v1"] == "FIXED_BLOCKED"


def test_nas_btc_hard_opposed_truth_audit_marks_learning_candidate_when_only_tunable():
    row = build_nas_btc_hard_opposed_truth_audit_row_v1(
        {
            "symbol": "BTCUSD",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
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
    assert row["nas_btc_hard_opposed_truth_audit_state_v1"] == "TUNABLE_OVER_TIGHTEN_RISK"
    assert row["nas_btc_hard_opposed_truth_alignment_v1"] == "OVER_TIGHTEN_RISK"
    assert row["nas_btc_hard_opposed_learning_state_v1"] == "LEARNING_CANDIDATE"
    assert "flow.ambiguity_threshold" in row["nas_btc_hard_opposed_learning_keys_v1"]


def test_nas_btc_hard_opposed_truth_audit_marks_mixed_review():
    row = build_nas_btc_hard_opposed_truth_audit_row_v1(
        {
            "symbol": "NAS100",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
            "flow_structure_gate_hard_disqualifiers_v1": ["POLARITY_MISMATCH", "AMBIGUITY_HIGH"],
            "flow_structure_gate_soft_score_v1": 1.0,
            "aggregate_conviction_v1": 0.25,
            "flow_persistence_v1": 0.3,
            "aggregate_conviction_building_floor_v1": 0.6,
            "flow_persistence_building_floor_v1": 0.58,
        }
    )
    assert row["nas_btc_hard_opposed_truth_audit_state_v1"] == "MIXED_REVIEW"
    assert row["nas_btc_hard_opposed_learning_state_v1"] == "MIXED_REVIEW"


def test_generate_and_write_nas_btc_hard_opposed_truth_audit_summary_writes_artifacts(tmp_path):
    report = generate_and_write_nas_btc_hard_opposed_truth_audit_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "new_flow_enabled_state_v1": "FLOW_OPPOSED",
                "flow_candidate_improvement_verdict_v1": "OVER_TIGHTENED",
                "flow_structure_gate_hard_disqualifiers_v1": ["AMBIGUITY_HIGH"],
                "flow_structure_gate_soft_score_v1": 1.0,
                "aggregate_conviction_v1": 0.2,
                "flow_persistence_v1": 0.2,
                "aggregate_ambiguity_penalty_v1": 0.35,
                "aggregate_conviction_building_floor_v1": 0.6,
                "flow_persistence_building_floor_v1": 0.58,
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "nas_btc_hard_opposed_truth_audit_latest.json"
    md_path = tmp_path / "nas_btc_hard_opposed_truth_audit_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["learning_candidate_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
