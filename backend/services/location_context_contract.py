from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


LOCATION_CONTEXT_CONTRACT_VERSION = "location_context_contract_v1"
LOCATION_CONTEXT_SUMMARY_VERSION = "location_context_summary_v1"

LOCATION_CONTEXT_ENUM_V1 = ("NONE", "IN_BOX", "AT_EDGE", "POST_BREAKOUT", "EXTENDED")
LOCATION_MATERIAL_ENUM_V1 = (
    "BOX_INTERIOR",
    "BOX_OR_BAND_EDGE",
    "RECENT_BREAKOUT_ZONE",
    "LATE_EXTENSION_ZONE",
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


def build_location_context_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": LOCATION_CONTEXT_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only location context contract. Surfaces where the current state is happening "
            "without changing dominant_side or execution directly."
        ),
        "location_context_enum_v1": list(LOCATION_CONTEXT_ENUM_V1),
        "location_material_enum_v1": list(LOCATION_MATERIAL_ENUM_V1),
        "field_catalog_v1": [
            "location_context_v1",
            "location_context_confidence_v1",
            "location_context_reason_summary_v1",
            "box_position_state_v1",
            "edge_proximity_state_v1",
            "post_breakout_zone_v1",
            "extension_zone_state_v1",
        ],
        "classification_rules_v1": [
            {
                "location": "IN_BOX",
                "criteria": [
                    "price is structurally inside the active box/interior zone",
                    "edge pressure is not the dominant explanation",
                ],
                "notes": "Use for interior state reading before edge/breakout interpretation dominates.",
            },
            {
                "location": "AT_EDGE",
                "criteria": [
                    "price is interacting with the box edge or strong band edge",
                    "edge interpretation matters more than interior drift",
                ],
                "notes": "Useful for rejection/friction interpretation without forcing reversal by itself.",
            },
            {
                "location": "POST_BREAKOUT",
                "criteria": [
                    "breakout or reclaim happened recently",
                    "current interpretation still depends on the breakout zone",
                ],
                "notes": "Separates fresh breakout context from ordinary edge or extended continuation context.",
            },
            {
                "location": "EXTENDED",
                "criteria": [
                    "move is already spatially stretched relative to the breakout/box origin",
                    "late chase or extension context dominates the explanation",
                ],
                "notes": "Supports extension/exhaustion interpretation without changing side by itself.",
            },
        ],
        "control_rules_v1": [
            "location context is a modifier, not a core slot driver in v1",
            "location context cannot change dominant_side",
            "the same rejection can mean friction or reversal depending on location context",
            "the same continuation stage can mean initiation or extension depending on location context",
            "AT_EDGE does not imply reversal by itself",
            "EXTENDED does not imply reversal by itself",
        ],
        "dominance_protection_v1": {
            "location_context_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_rejection_v1": True,
            "bridge_to_continuation_stage_v1": True,
            "bridge_to_texture_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_location_context_summary_v1() -> dict[str, Any]:
    contract = build_location_context_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": LOCATION_CONTEXT_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "location_context_count": len(contract.get("location_context_enum_v1", [])),
        "location_material_count": len(contract.get("location_material_enum_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("location_context_can_change_dominant_side")
        ),
        "bridge_to_rejection_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_rejection_v1")),
        "bridge_to_continuation_stage_v1": bool(
            contract.get("bridge_contract_v1", {}).get("bridge_to_continuation_stage_v1")
        ),
        "bridge_to_texture_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_texture_v1")),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_location_context_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# Location Context Contract v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- location_context_count: `{summary_payload.get('location_context_count', 0)}`",
        f"- location_material_count: `{summary_payload.get('location_material_count', 0)}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Location Contexts",
        "",
        f"- enum: {', '.join(str(x) for x in list(contract_payload.get('location_context_enum_v1') or []))}",
        f"- materials: {', '.join(str(x) for x in list(contract_payload.get('location_material_enum_v1') or []))}",
        "",
        "## Classification Rules",
        "",
    ]
    for row in contract_payload.get("classification_rules_v1", []):
        criteria = "; ".join(str(x) for x in list(row.get("criteria") or []))
        lines.append(f"- `{row.get('location', '')}`: {criteria} | {row.get('notes', '')}")
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_location_context_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_location_context_contract_v1()
    summary = build_location_context_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "location_context_latest.json"
    md_path = output_dir / "location_context_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_location_context_markdown_v1(contract, summary))
    return payload
