from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.services.improvement_board_field_policy import (
    IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION,
)
from backend.services.improvement_proposal_policy import (
    IMPROVEMENT_PROPOSAL_POLICY_CONTRACT_VERSION,
)
from backend.services.improvement_status_policy import (
    IMPROVEMENT_STATUS_POLICY_CONTRACT_VERSION,
)
from backend.services.telegram_route_ownership_policy import (
    TELEGRAM_ROUTE_OWNERSHIP_POLICY_CONTRACT_VERSION,
)
from backend.services.telegram_route_policy import TELEGRAM_ROUTE_POLICY_CONTRACT_VERSION


IMPROVEMENT_BASELINE_CONSISTENCY_AUDIT_CONTRACT_VERSION = (
    "improvement_baseline_consistency_audit_v1"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _required_doc_paths() -> list[Path]:
    docs_dir = _repo_root() / "docs"
    return [
        docs_dir / "current_p0_foundation_baseline_detailed_plan_ko.md",
        docs_dir / "current_p0_1_telegram_topic_role_baseline_detailed_plan_ko.md",
        docs_dir / "current_p0_2_status_enum_baseline_detailed_plan_ko.md",
        docs_dir / "current_p0_3_proposal_envelope_baseline_detailed_plan_ko.md",
        docs_dir / "current_p0_4_board_field_naming_baseline_detailed_plan_ko.md",
        docs_dir / "current_p0_5_route_ownership_baseline_detailed_plan_ko.md",
    ]


def build_improvement_baseline_consistency_audit() -> dict[str, Any]:
    required_docs = [
        {
            "path": str(path),
            "exists": path.exists(),
            "name": path.name,
        }
        for path in _required_doc_paths()
    ]
    all_docs_present = all(row["exists"] for row in required_docs)
    policy_versions = {
        "telegram_route_policy_version": TELEGRAM_ROUTE_POLICY_CONTRACT_VERSION,
        "improvement_status_policy_version": IMPROVEMENT_STATUS_POLICY_CONTRACT_VERSION,
        "improvement_proposal_policy_version": IMPROVEMENT_PROPOSAL_POLICY_CONTRACT_VERSION,
        "improvement_board_field_policy_version": IMPROVEMENT_BOARD_FIELD_POLICY_CONTRACT_VERSION,
        "telegram_route_ownership_policy_version": TELEGRAM_ROUTE_OWNERSHIP_POLICY_CONTRACT_VERSION,
    }
    checks = [
        {
            "code": "p0_docs_present",
            "status": "PASS" if all_docs_present else "FAIL",
            "message_ko": "P0 기준 문서가 모두 존재합니다."
            if all_docs_present
            else "P0 기준 문서 중 누락된 파일이 있습니다.",
        },
        {
            "code": "policy_versions_declared",
            "status": "PASS",
            "message_ko": "P0 기준 policy contract version이 모두 선언되어 있습니다.",
        },
    ]
    return {
        "contract_version": IMPROVEMENT_BASELINE_CONSISTENCY_AUDIT_CONTRACT_VERSION,
        "policy_versions": policy_versions,
        "required_docs": required_docs,
        "checks": checks,
        "overall_status": "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL",
    }


def default_improvement_baseline_consistency_audit_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "improvement_baseline_consistency_audit_latest.json",
        directory / "improvement_baseline_consistency_audit_latest.md",
    )


def render_improvement_baseline_consistency_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Improvement Baseline Consistency Audit",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        f"- overall_status: `{payload.get('overall_status', '-')}`",
        "",
        "## Policy Versions",
    ]
    for key, value in dict(payload.get("policy_versions", {}) or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Required Docs"])
    for row in list(payload.get("required_docs", []) or []):
        lines.append(
            f"- `{row.get('name', '-')}` | exists=`{row.get('exists', False)}`"
        )
    lines.extend(["", "## Checks"])
    for row in list(payload.get("checks", []) or []):
        lines.append(
            f"- `{row.get('code', '-')}` | `{row.get('status', '-')}` | {row.get('message_ko', '-')}"
        )
    return "\n".join(lines)


def write_improvement_baseline_consistency_audit_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_improvement_baseline_consistency_audit()
    default_json_path, default_markdown_path = default_improvement_baseline_consistency_audit_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    resolved_markdown_path.write_text(
        render_improvement_baseline_consistency_audit_markdown(payload),
        encoding="utf-8",
    )
    return {
        "contract_version": payload["contract_version"],
        "overall_status": payload["overall_status"],
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
    }
