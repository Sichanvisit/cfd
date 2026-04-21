from pathlib import Path

from backend.services import improvement_baseline_consistency_audit as audit


def test_build_improvement_baseline_consistency_audit_reports_pass() -> None:
    payload = audit.build_improvement_baseline_consistency_audit()

    assert payload["contract_version"] == audit.IMPROVEMENT_BASELINE_CONSISTENCY_AUDIT_CONTRACT_VERSION
    assert payload["overall_status"] == "PASS"
    assert payload["policy_versions"]["telegram_route_policy_version"] == "telegram_route_policy_v1"
    assert any(row["name"] == "current_p0_5_route_ownership_baseline_detailed_plan_ko.md" for row in payload["required_docs"])


def test_write_improvement_baseline_consistency_audit_snapshot(tmp_path: Path) -> None:
    json_path = tmp_path / "improvement_baseline_consistency_audit_latest.json"
    markdown_path = tmp_path / "improvement_baseline_consistency_audit_latest.md"

    result = audit.write_improvement_baseline_consistency_audit_snapshot(
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result["overall_status"] == "PASS"
    assert json_path.exists()
    assert markdown_path.exists()
    assert "Policy Versions" in markdown_path.read_text(encoding="utf-8")
