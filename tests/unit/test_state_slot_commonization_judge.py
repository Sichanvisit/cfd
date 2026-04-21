import json

from backend.services.state_slot_commonization_judge import (
    build_state_slot_commonization_judge_contract_v1,
    generate_and_write_state_slot_commonization_judge_summary_v1,
)


def test_state_slot_commonization_judge_contract_exposes_verdicts():
    contract = build_state_slot_commonization_judge_contract_v1()

    assert contract["contract_version"] == "state_slot_commonization_judge_contract_v1"
    assert "COMMON_WITH_SYMBOL_THRESHOLD" in contract["commonization_verdict_enum_v1"]


def test_generate_and_write_state_slot_commonization_judge_summary_writes_artifacts(tmp_path):
    report = generate_and_write_state_slot_commonization_judge_summary_v1(
        xau_pilot_mapping_report={},
        xau_readonly_surface_report={"summary": {"surface_ready_count": 1}},
        xau_decomposition_validation_report={"summary": {"slot_alignment_rate": 1.0, "should_have_done_candidate_count": 1}},
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "state_slot_commonization_judge_latest.json"
    md_path = tmp_path / "state_slot_commonization_judge_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["slot_count"] >= 1
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
