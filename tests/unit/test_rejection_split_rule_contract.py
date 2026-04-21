import json

from backend.services.rejection_split_rule_contract import (
    build_rejection_split_rule_contract_v1,
    generate_and_write_rejection_split_rule_summary_v1,
)


def test_rejection_split_rule_contract_exposes_friction_vs_reversal_split():
    contract = build_rejection_split_rule_contract_v1()

    assert contract["contract_version"] == "rejection_split_rule_contract_v1"
    assert contract["rejection_type_enum_v1"] == [
        "NONE",
        "FRICTION_REJECTION",
        "REVERSAL_REJECTION",
    ]
    assert contract["rejection_consumption_role_enum_v1"] == [
        "NONE",
        "FRICTION_ONLY",
        "REVERSAL_EVIDENCE",
    ]
    assert contract["dominance_protection_v1"]["rejection_split_can_change_dominant_side"] is False
    assert "single upper_reject cannot become reversal override by itself" in contract["control_rules_v1"]


def test_generate_and_write_rejection_split_rule_summary_writes_artifacts(tmp_path):
    report = generate_and_write_rejection_split_rule_summary_v1(shadow_auto_dir=tmp_path)

    json_path = tmp_path / "rejection_split_rule_latest.json"
    md_path = tmp_path / "rejection_split_rule_latest.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
