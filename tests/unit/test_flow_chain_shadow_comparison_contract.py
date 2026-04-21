import json

from backend.services.flow_chain_shadow_comparison_contract import (
    build_flow_chain_shadow_comparison_contract_v1,
    build_flow_chain_shadow_comparison_row_v1,
    generate_and_write_flow_chain_shadow_comparison_summary_v1,
)


def test_flow_chain_shadow_comparison_contract_exposes_expected_fields():
    contract = build_flow_chain_shadow_comparison_contract_v1()
    assert contract["contract_version"] == "flow_chain_shadow_comparison_contract_v1"
    assert "old_exact_match_only_flow_state_v1" in contract["row_level_fields_v1"]
    assert "flow_chain_shadow_delta_v1" in contract["row_level_fields_v1"]


def test_flow_chain_shadow_comparison_marks_widened_acceptance():
    row = build_flow_chain_shadow_comparison_row_v1(
        {
            "symbol": "XAUUSD",
            "exact_pilot_match_bonus_source_v1": "OUT_OF_PROFILE",
            "flow_support_state_v1": "FLOW_BUILDING",
            "flow_support_state_authority_v1": "PROVISIONAL_BUILDING",
            "dominance_should_have_done_candidate_v1": True,
        }
    )
    assert row["old_exact_match_only_flow_state_v1"] == "FLOW_UNCONFIRMED"
    assert row["flow_chain_shadow_delta_v1"] == "FLOW_WIDENS_ACCEPTANCE"
    assert row["flow_chain_shadow_candidate_improved_v1"] is True


def test_flow_chain_shadow_comparison_marks_new_flow_opposed_separately():
    row = build_flow_chain_shadow_comparison_row_v1(
        {
            "symbol": "NAS100",
            "exact_pilot_match_bonus_source_v1": "PARTIAL_ACTIVE_PROFILE",
            "flow_support_state_v1": "FLOW_OPPOSED",
            "flow_support_state_authority_v1": "STRUCTURE_HARD_OPPOSED",
            "dominance_should_have_done_candidate_v1": False,
        }
    )
    assert row["old_exact_match_only_flow_state_v1"] == "FLOW_BUILDING"
    assert row["flow_chain_shadow_delta_v1"] == "NEW_FLOW_OPPOSED"


def test_flow_chain_shadow_comparison_marks_tightened_acceptance():
    row = build_flow_chain_shadow_comparison_row_v1(
        {
            "symbol": "BTCUSD",
            "exact_pilot_match_bonus_source_v1": "MATCHED_ACTIVE_PROFILE",
            "flow_support_state_v1": "FLOW_BUILDING",
            "flow_support_state_authority_v1": "PROVISIONAL_BUILDING",
            "dominance_should_have_done_candidate_v1": False,
        }
    )
    assert row["old_exact_match_only_flow_state_v1"] == "FLOW_CONFIRMED"
    assert row["flow_chain_shadow_delta_v1"] == "FLOW_TIGHTENS_ACCEPTANCE"


def test_generate_and_write_flow_chain_shadow_comparison_summary_writes_artifacts(tmp_path):
    report = generate_and_write_flow_chain_shadow_comparison_summary_v1(
        {
            "NAS100": {
                "symbol": "NAS100",
                "exact_pilot_match_bonus_source_v1": "MATCHED_ACTIVE_PROFILE",
                "flow_support_state_v1": "FLOW_CONFIRMED",
                "flow_support_state_authority_v1": "PROVISIONAL_CONFIRMED",
                "dominance_should_have_done_candidate_v1": True,
            }
        },
        shadow_auto_dir=tmp_path,
    )
    json_path = tmp_path / "flow_chain_shadow_comparison_latest.json"
    md_path = tmp_path / "flow_chain_shadow_comparison_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["symbol_count"] == 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
