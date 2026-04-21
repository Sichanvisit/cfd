from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


REJECTION_SPLIT_RULE_CONTRACT_VERSION = "rejection_split_rule_contract_v1"
REJECTION_SPLIT_RULE_SUMMARY_VERSION = "rejection_split_rule_summary_v1"

REJECTION_TYPE_ENUM_V1 = ("NONE", "FRICTION_REJECTION", "REVERSAL_REJECTION")
REJECTION_CONSUMPTION_ROLE_ENUM_V1 = ("NONE", "FRICTION_ONLY", "REVERSAL_EVIDENCE")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_rejection_split_rule_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": REJECTION_SPLIT_RULE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only rejection split contract. Locks rejection into friction rejection "
            "versus reversal rejection before any execution or state25 linkage."
        ),
        "rejection_type_enum_v1": list(REJECTION_TYPE_ENUM_V1),
        "rejection_consumption_role_enum_v1": list(REJECTION_CONSUMPTION_ROLE_ENUM_V1),
        "field_catalog_v1": [
            "rejection_type_v1",
            "rejection_consumption_role_v1",
            "rejection_split_confidence_v1",
            "rejection_structure_break_confirmed_v1",
            "rejection_reversal_evidence_bridge_v1",
            "rejection_friction_bridge_v1",
            "rejection_reason_summary_v1",
        ],
        "classification_rules_v1": [
            {
                "rule": "structure_breaking_rejection",
                "classification": "REVERSAL_REJECTION",
                "consumption_role": "REVERSAL_EVIDENCE",
                "notes": "Use only when rejection comes with structure break or confirmed continuation failure.",
            },
            {
                "rule": "non_breaking_rejection",
                "classification": "FRICTION_REJECTION",
                "consumption_role": "FRICTION_ONLY",
                "notes": "Use when rejection creates timing friction but does not invalidate the current structure.",
            },
        ],
        "control_rules_v1": [
            "structure-breaking rejection maps to reversal evidence",
            "non-breaking rejection maps to friction only",
            "single upper_reject cannot become reversal override by itself",
            "single soft_block cannot become reversal override by itself",
            "single wait_bias cannot become reversal override by itself",
            "rejection split cannot change dominant_side",
            "friction rejection adjusts mode/caution only",
            "reversal rejection can strengthen reversal evidence but side change still belongs to dominance layer",
        ],
        "dominance_protection_v1": {
            "rejection_split_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_friction_v1": True,
            "bridge_to_reversal_evidence_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_rejection_split_rule_summary_v1() -> dict[str, Any]:
    contract = build_rejection_split_rule_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": REJECTION_SPLIT_RULE_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "rejection_type_count": len(contract.get("rejection_type_enum_v1", [])),
        "rejection_consumption_role_count": len(contract.get("rejection_consumption_role_enum_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("rejection_split_can_change_dominant_side")
        ),
        "bridge_to_friction_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_friction_v1")),
        "bridge_to_reversal_evidence_v1": bool(
            contract.get("bridge_contract_v1", {}).get("bridge_to_reversal_evidence_v1")
        ),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_rejection_split_rule_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# Rejection Split Rule v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- rejection_type_count: `{summary_payload.get('rejection_type_count', 0)}`",
        f"- rejection_consumption_role_count: `{summary_payload.get('rejection_consumption_role_count', 0)}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Rejection Types",
        "",
        f"- enum: {', '.join(str(x) for x in list(contract_payload.get('rejection_type_enum_v1') or []))}",
        f"- consumption roles: {', '.join(str(x) for x in list(contract_payload.get('rejection_consumption_role_enum_v1') or []))}",
        "",
        "## Classification Rules",
        "",
    ]
    for row in contract_payload.get("classification_rules_v1", []):
        lines.append(
            f"- `{row.get('rule', '')}` -> `{row.get('classification', '')}` / "
            f"`{row.get('consumption_role', '')}` | {row.get('notes', '')}"
        )
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_rejection_split_rule_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_rejection_split_rule_contract_v1()
    summary = build_rejection_split_rule_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "rejection_split_rule_latest.json"
    md_path = output_dir / "rejection_split_rule_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_rejection_split_rule_markdown_v1(contract, summary))
    return payload
