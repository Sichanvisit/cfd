from pathlib import Path

from backend.services import improvement_status_policy as status_policy


def test_status_policy_keeps_readiness_proposal_and_approval_separate() -> None:
    payload = status_policy.build_improvement_status_baseline()

    readiness_values = {row["value"] for row in payload["readiness_statuses"]}
    proposal_values = {row["value"] for row in payload["proposal_stages"]}
    approval_values = {row["value"] for row in payload["approval_statuses"]}

    assert status_policy.READINESS_STATUS_PENDING_EVIDENCE in readiness_values
    assert status_policy.PROPOSAL_STAGE_REVIEW_PENDING in proposal_values
    assert status_policy.APPROVAL_STATUS_PENDING in approval_values
    assert status_policy.PROPOSAL_STAGE_REVIEW_PENDING not in approval_values
    assert status_policy.APPROVAL_STATUS_PENDING not in readiness_values


def test_status_policy_normalize_functions_follow_domain_conventions() -> None:
    assert status_policy.normalize_readiness_status("ready_for_review") == "READY_FOR_REVIEW"
    assert status_policy.normalize_proposal_stage("report_ready") == "REPORT_READY"
    assert status_policy.normalize_approval_status("APPROVED") == "approved"
    assert status_policy.approval_status_label_ko("held") == "보류"
    assert status_policy.readiness_status_label_ko("blocked") == "차단됨"


def test_status_policy_write_snapshot_creates_json_and_markdown(tmp_path: Path) -> None:
    json_path = tmp_path / "improvement_status_baseline_latest.json"
    markdown_path = tmp_path / "improvement_status_baseline_latest.md"

    result = status_policy.write_improvement_status_baseline_snapshot(
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert result["contract_version"] == status_policy.IMPROVEMENT_STATUS_POLICY_CONTRACT_VERSION
    assert json_path.exists()
    assert markdown_path.exists()
    assert "approval_status" in json_path.read_text(encoding="utf-8")
    assert "## Proposal Stages" in markdown_path.read_text(encoding="utf-8")
