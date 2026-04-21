from pathlib import Path

import pytest

from backend.services import telegram_route_ownership_policy as ownership_policy


def test_route_ownership_policy_exposes_expected_owner_lanes() -> None:
    payload = ownership_policy.build_telegram_route_ownership_baseline()
    owner_keys = {row["owner_key"] for row in payload["owners"]}

    assert ownership_policy.OWNER_RUNTIME_EXECUTION in owner_keys
    assert ownership_policy.OWNER_IMPROVEMENT_CHECK_INBOX in owner_keys
    assert ownership_policy.OWNER_IMPROVEMENT_REPORT_TOPIC in owner_keys
    assert ownership_policy.OWNER_PNL_DIGEST in owner_keys
    assert ownership_policy.OWNER_LEGACY_LIVE_CHECK_CARD in owner_keys


def test_route_ownership_policy_validates_allowed_route() -> None:
    policy = ownership_policy.validate_telegram_route_ownership(
        owner_key=ownership_policy.OWNER_PNL_DIGEST,
        route="pnl",
    )

    assert policy.owner_key == ownership_policy.OWNER_PNL_DIGEST


def test_route_ownership_policy_rejects_wrong_route() -> None:
    with pytest.raises(ValueError, match="telegram_route_ownership_violation"):
        ownership_policy.validate_telegram_route_ownership(
            owner_key=ownership_policy.OWNER_IMPROVEMENT_REPORT_TOPIC,
            route="runtime",
        )


def test_route_ownership_policy_writes_snapshot(tmp_path: Path) -> None:
    json_path = tmp_path / "telegram_route_ownership_baseline_latest.json"
    markdown_path = tmp_path / "telegram_route_ownership_baseline_latest.md"

    result = ownership_policy.write_telegram_route_ownership_baseline_snapshot(
        json_path=json_path,
        markdown_path=markdown_path,
    )

    assert (
        result["contract_version"]
        == ownership_policy.TELEGRAM_ROUTE_OWNERSHIP_POLICY_CONTRACT_VERSION
    )
    assert json_path.exists()
    assert markdown_path.exists()
    assert "runtime_execution" in json_path.read_text(encoding="utf-8")
    assert "## Owners" in markdown_path.read_text(encoding="utf-8")
