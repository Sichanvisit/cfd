from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


CONTINUATION_STAGE_CONTRACT_VERSION = "continuation_stage_contract_v1"
CONTINUATION_STAGE_SUMMARY_VERSION = "continuation_stage_summary_v1"

CONTINUATION_STAGE_ENUM_V1 = ("NONE", "INITIATION", "ACCEPTANCE", "EXTENSION")
STAGE_MATERIAL_ENUM_V1 = (
    "POST_BREAKOUT_EARLY",
    "STABLE_HOLD",
    "HIGHER_LOW_PERSISTENCE",
    "LATE_EXTENSION_PRESSURE",
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


def build_continuation_stage_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": CONTINUATION_STAGE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only continuation stage split contract. Separates continuation into initiation, "
            "acceptance, and extension without changing dominant_side or execution directly."
        ),
        "continuation_stage_enum_v1": list(CONTINUATION_STAGE_ENUM_V1),
        "stage_material_enum_v1": list(STAGE_MATERIAL_ENUM_V1),
        "field_catalog_v1": [
            "continuation_stage_v1",
            "continuation_stage_confidence_v1",
            "continuation_stage_reason_summary_v1",
            "breakout_post_bars_v1",
            "breakout_hold_bars_v1",
            "higher_low_persistence_v1",
            "extension_pressure_state_v1",
        ],
        "classification_rules_v1": [
            {
                "stage": "INITIATION",
                "criteria": [
                    "recent breakout or reclaim just started",
                    "hold bars are still shallow",
                    "continuation intent exists but structure has not fully settled",
                ],
                "notes": "Best early continuation candidate zone, but false break risk still exists.",
            },
            {
                "stage": "ACCEPTANCE",
                "criteria": [
                    "breakout hold remains stable",
                    "higher low persistence is visible",
                    "continuation structure is settled enough to explain hold/add bias later",
                ],
                "notes": "Stable continuation zone. Same direction remains favored without calling it extension yet.",
            },
            {
                "stage": "EXTENSION",
                "criteria": [
                    "move is already elongated",
                    "late chase or extension pressure is rising",
                    "continuation may still be valid but entry quality is no longer early/clean",
                ],
                "notes": "Continuation can remain valid while reward/risk and chase quality deteriorate.",
            },
        ],
        "control_rules_v1": [
            "stage means structural time position, not execution quality",
            "texture means execution quality and must not be merged with stage",
            "continuation stage cannot change dominant_side",
            "extension does not imply reversal by itself",
            "acceptance does not guarantee clean execution quality by itself",
            "continuation stage is strongest for continuation or recovery intent and remains read-only in v1",
        ],
        "dominance_protection_v1": {
            "continuation_stage_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_texture_v1": True,
            "bridge_to_location_v1": True,
            "bridge_to_tempo_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_continuation_stage_summary_v1() -> dict[str, Any]:
    contract = build_continuation_stage_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": CONTINUATION_STAGE_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "continuation_stage_count": len(contract.get("continuation_stage_enum_v1", [])),
        "stage_material_count": len(contract.get("stage_material_enum_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("continuation_stage_can_change_dominant_side")
        ),
        "bridge_to_texture_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_texture_v1")),
        "bridge_to_location_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_location_v1")),
        "bridge_to_tempo_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_tempo_v1")),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_continuation_stage_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# Continuation Stage Contract v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- continuation_stage_count: `{summary_payload.get('continuation_stage_count', 0)}`",
        f"- stage_material_count: `{summary_payload.get('stage_material_count', 0)}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Continuation Stages",
        "",
        f"- enum: {', '.join(str(x) for x in list(contract_payload.get('continuation_stage_enum_v1') or []))}",
        f"- materials: {', '.join(str(x) for x in list(contract_payload.get('stage_material_enum_v1') or []))}",
        "",
        "## Classification Rules",
        "",
    ]
    for row in contract_payload.get("classification_rules_v1", []):
        criteria = "; ".join(str(x) for x in list(row.get("criteria") or []))
        lines.append(f"- `{row.get('stage', '')}`: {criteria} | {row.get('notes', '')}")
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_continuation_stage_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_continuation_stage_contract_v1()
    summary = build_continuation_stage_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "continuation_stage_latest.json"
    md_path = output_dir / "continuation_stage_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_continuation_stage_markdown_v1(contract, summary))
    return payload
