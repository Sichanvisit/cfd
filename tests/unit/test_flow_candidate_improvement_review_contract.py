import json

from backend.services.flow_candidate_improvement_review_contract import (
    build_flow_candidate_improvement_review_contract_v1,
    build_flow_candidate_improvement_review_row_v1,
    generate_and_write_flow_candidate_improvement_review_summary_v1,
)


def test_flow_candidate_improvement_review_contract_exposes_expected_fields():
    contract = build_flow_candidate_improvement_review_contract_v1()
    assert contract["contract_version"] == "flow_candidate_improvement_review_contract_v1"
    assert "flow_candidate_truth_state_v1" in contract["row_level_fields_v1"]
    assert "flow_candidate_improvement_verdict_v1" in contract["row_level_fields_v1"]


def test_flow_candidate_improvement_review_marks_aligned_improvement():
    row = build_flow_candidate_improvement_review_row_v1(
        {
            "dominance_should_have_done_candidate_v1": True,
            "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
            "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
            "new_flow_enabled_state_v1": "FLOW_BUILDING",
            "flow_chain_shadow_delta_v1": "FLOW_WIDENS_ACCEPTANCE",
        }
    )
    assert row["flow_candidate_truth_state_v1"] == "WIDEN_EXPECTED"
    assert row["flow_candidate_improvement_verdict_v1"] == "ALIGNED_IMPROVEMENT"
    assert row["flow_candidate_improved_v1"] is True


def test_flow_candidate_improvement_review_marks_over_tightened():
    row = build_flow_candidate_improvement_review_row_v1(
        {
            "dominance_should_have_done_candidate_v1": True,
            "dominance_error_type_v1": "BOUNDARY_STAYED_TOO_LONG",
            "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_chain_shadow_delta_v1": "NEW_FLOW_OPPOSED",
        }
    )
    assert row["flow_candidate_review_alignment_v1"] == "REGRESSED"
    assert row["flow_candidate_improvement_verdict_v1"] == "OVER_TIGHTENED"


def test_flow_candidate_improvement_review_marks_aligned_tightening():
    row = build_flow_candidate_improvement_review_row_v1(
        {
            "dominance_should_have_done_candidate_v1": True,
            "dominance_error_type_v1": "TRUE_REVERSAL_MISSED",
            "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
            "new_flow_enabled_state_v1": "FLOW_OPPOSED",
            "flow_chain_shadow_delta_v1": "NEW_FLOW_OPPOSED",
        }
    )
    assert row["flow_candidate_truth_state_v1"] == "TIGHTEN_EXPECTED"
    assert row["flow_candidate_improvement_verdict_v1"] == "ALIGNED_TIGHTENING"


def test_flow_candidate_improvement_review_marks_unverified_widening_without_candidate():
    row = build_flow_candidate_improvement_review_row_v1(
        {
            "dominance_should_have_done_candidate_v1": False,
            "dominance_error_type_v1": "ALIGNED",
            "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
            "new_flow_enabled_state_v1": "FLOW_BUILDING",
            "flow_chain_shadow_delta_v1": "FLOW_WIDENS_ACCEPTANCE",
        }
    )
    assert row["flow_candidate_truth_state_v1"] == "NO_CANDIDATE"
    assert row["flow_candidate_improvement_verdict_v1"] == "UNVERIFIED_WIDENING"


def test_generate_and_write_flow_candidate_improvement_review_summary_writes_artifacts(tmp_path):
    report = generate_and_write_flow_candidate_improvement_review_summary_v1(
        {
            "XAUUSD": {
                "dominance_should_have_done_candidate_v1": True,
                "dominance_error_type_v1": "CONTINUATION_UNDERPROMOTED",
                "old_exact_match_only_flow_state_v1": "FLOW_UNCONFIRMED",
                "new_flow_enabled_state_v1": "FLOW_BUILDING",
                "flow_chain_shadow_delta_v1": "FLOW_WIDENS_ACCEPTANCE",
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "flow_candidate_improvement_review_latest.json"
    md_path = tmp_path / "flow_candidate_improvement_review_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["candidate_improved_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
