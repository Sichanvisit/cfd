from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


AMBIGUITY_MODIFIER_CONTRACT_VERSION = "ambiguity_modifier_contract_v1"
AMBIGUITY_MODIFIER_SUMMARY_VERSION = "ambiguity_modifier_summary_v1"

AMBIGUITY_LEVEL_ENUM_V1 = ("LOW", "MEDIUM", "HIGH")
AMBIGUITY_SOURCE_ENUM_V1 = (
    "CONTINUATION_REVERSAL_CONFLICT",
    "BOUNDARY_CONFLICT",
    "STRUCTURE_MIXED",
    "INSUFFICIENT_CONFIRMATION",
)


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


def build_ambiguity_modifier_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": AMBIGUITY_MODIFIER_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only ambiguity modifier contract. Keeps ambiguous scenes from being force-consumed "
            "as continuation, friction, or reversal too early."
        ),
        "ambiguity_level_enum_v1": list(AMBIGUITY_LEVEL_ENUM_V1),
        "ambiguity_source_enum_v1": list(AMBIGUITY_SOURCE_ENUM_V1),
        "field_catalog_v1": [
            "ambiguity_level_v1",
            "ambiguity_source_v1",
            "ambiguity_confidence_v1",
            "ambiguity_reason_summary_v1",
            "boundary_bias_adjustment_v1",
            "caution_bias_adjustment_v1",
        ],
        "classification_rules_v1": [
            {
                "ambiguity_level": "LOW",
                "criteria": [
                    "dominant interpretation is comparatively clear",
                    "conflict exists only as weak noise",
                ],
                "notes": "Low ambiguity should not distort an otherwise stable continuation or reversal reading.",
            },
            {
                "ambiguity_level": "MEDIUM",
                "criteria": [
                    "competing interpretations coexist",
                    "one side still leads but confidence is not clean",
                ],
                "notes": "Medium ambiguity should strengthen caution and boundary awareness without changing side.",
            },
            {
                "ambiguity_level": "HIGH",
                "criteria": [
                    "continuation and reversal evidence remain materially unresolved",
                    "or confirmation quality is too weak to force either side",
                ],
                "notes": "High ambiguity is a protection layer against over-classifying mixed scenes too early.",
            },
        ],
        "control_rules_v1": [
            "ambiguity is a modifier, not a core slot driver in v1",
            "ambiguity cannot change dominant_side",
            "ambiguity can strengthen boundary bias and caution level",
            "high ambiguity must not be silently absorbed into friction or continuation",
            "ambiguity is allowed to preserve unresolved scenes as mixed rather than forcing a premature decision",
            "execution and state25 remain read-only while ambiguity is being calibrated",
        ],
        "dominance_protection_v1": {
            "ambiguity_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_boundary_v1": True,
            "bridge_to_caution_level_v1": True,
            "bridge_to_texture_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_ambiguity_modifier_summary_v1() -> dict[str, Any]:
    contract = build_ambiguity_modifier_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": AMBIGUITY_MODIFIER_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "ambiguity_level_count": len(contract.get("ambiguity_level_enum_v1", [])),
        "ambiguity_source_count": len(contract.get("ambiguity_source_enum_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("ambiguity_can_change_dominant_side")
        ),
        "bridge_to_boundary_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_boundary_v1")),
        "bridge_to_caution_level_v1": bool(
            contract.get("bridge_contract_v1", {}).get("bridge_to_caution_level_v1")
        ),
        "bridge_to_texture_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_texture_v1")),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_ambiguity_modifier_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# Ambiguity Modifier Contract v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- ambiguity_level_count: `{summary_payload.get('ambiguity_level_count', 0)}`",
        f"- ambiguity_source_count: `{summary_payload.get('ambiguity_source_count', 0)}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Ambiguity Levels",
        "",
        f"- enum: {', '.join(str(x) for x in list(contract_payload.get('ambiguity_level_enum_v1') or []))}",
        f"- sources: {', '.join(str(x) for x in list(contract_payload.get('ambiguity_source_enum_v1') or []))}",
        "",
        "## Classification Rules",
        "",
    ]
    for row in contract_payload.get("classification_rules_v1", []):
        criteria = "; ".join(str(x) for x in list(row.get("criteria") or []))
        lines.append(f"- `{row.get('ambiguity_level', '')}`: {criteria} | {row.get('notes', '')}")
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_ambiguity_modifier_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_ambiguity_modifier_contract_v1()
    summary = build_ambiguity_modifier_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "ambiguity_modifier_latest.json"
    md_path = output_dir / "ambiguity_modifier_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_ambiguity_modifier_markdown_v1(contract, summary))
    return payload
