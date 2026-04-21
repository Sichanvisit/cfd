from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


TEMPO_PROFILE_CONTRACT_VERSION = "tempo_profile_contract_v1"
TEMPO_PROFILE_SUMMARY_VERSION = "tempo_profile_summary_v1"

TEMPO_PROFILE_STATE_ENUM_V1 = ("NONE", "EARLY", "PERSISTING", "REPEATING", "EXTENDED")
TEMPO_MATERIAL_ENUM_V1 = (
    "BREAKOUT_HOLD_COUNT",
    "HIGHER_LOW_COUNT",
    "LOWER_HIGH_COUNT",
    "REJECT_REPEAT_COUNT",
    "COUNTER_DRIVE_REPEAT_COUNT",
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


def build_tempo_profile_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": TEMPO_PROFILE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only tempo profile contract. Surfaces persistence and repeat structure as a shared modifier "
            "without changing dominant_side or execution directly."
        ),
        "tempo_profile_state_enum_v1": list(TEMPO_PROFILE_STATE_ENUM_V1),
        "tempo_material_enum_v1": list(TEMPO_MATERIAL_ENUM_V1),
        "field_catalog_v1": [
            "tempo_profile_v1",
            "tempo_profile_confidence_v1",
            "tempo_reason_summary_v1",
            "breakout_hold_bars_v1",
            "higher_low_count_v1",
            "lower_high_count_v1",
            "reject_repeat_count_v1",
            "counter_drive_repeat_count_v1",
        ],
        "classification_rules_v1": [
            {
                "tempo": "EARLY",
                "criteria": [
                    "breakout/reclaim persistence is still shallow",
                    "repeat structure is not yet established",
                ],
                "notes": "Useful for fresh continuation or recovery scenes before persistence builds.",
            },
            {
                "tempo": "PERSISTING",
                "criteria": [
                    "hold bars or structural counts keep building in the same direction",
                    "persistence matters more than one-bar snapshot interpretation",
                ],
                "notes": "Explains when a move has enough persistence to stop being treated as a one-off event.",
            },
            {
                "tempo": "REPEATING",
                "criteria": [
                    "reject or counter-drive patterns repeat enough to matter structurally",
                    "single-event interpretation is no longer sufficient",
                ],
                "notes": "Makes repeated rejection/counter-drive visible without forcing reversal by itself.",
            },
            {
                "tempo": "EXTENDED",
                "criteria": [
                    "persistence and repetition have already accumulated into late-stage behavior",
                    "tempo now contributes to extension/exhaustion interpretation",
                ],
                "notes": "Late persistence modifier only. Extended tempo does not imply side change by itself.",
            },
        ],
        "control_rules_v1": [
            "tempo starts as raw count and persistence fields plus a shared modifier summary",
            "tempo profile cannot change dominant_side",
            "single reject is not the same as repeated rejection tempo",
            "single hold is not the same as persistent hold tempo",
            "extended tempo does not imply reversal by itself",
            "tempo can strengthen stage, texture, and caution interpretation without replacing dominance",
        ],
        "dominance_protection_v1": {
            "tempo_profile_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_continuation_stage_v1": True,
            "bridge_to_rejection_v1": True,
            "bridge_to_location_v1": True,
            "bridge_to_texture_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_tempo_profile_summary_v1() -> dict[str, Any]:
    contract = build_tempo_profile_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": TEMPO_PROFILE_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "tempo_profile_state_count": len(contract.get("tempo_profile_state_enum_v1", [])),
        "tempo_material_count": len(contract.get("tempo_material_enum_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("tempo_profile_can_change_dominant_side")
        ),
        "bridge_to_continuation_stage_v1": bool(
            contract.get("bridge_contract_v1", {}).get("bridge_to_continuation_stage_v1")
        ),
        "bridge_to_rejection_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_rejection_v1")),
        "bridge_to_location_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_location_v1")),
        "bridge_to_texture_v1": bool(contract.get("bridge_contract_v1", {}).get("bridge_to_texture_v1")),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_tempo_profile_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# Tempo Profile Contract v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- tempo_profile_state_count: `{summary_payload.get('tempo_profile_state_count', 0)}`",
        f"- tempo_material_count: `{summary_payload.get('tempo_material_count', 0)}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Tempo States",
        "",
        f"- enum: {', '.join(str(x) for x in list(contract_payload.get('tempo_profile_state_enum_v1') or []))}",
        f"- materials: {', '.join(str(x) for x in list(contract_payload.get('tempo_material_enum_v1') or []))}",
        "",
        "## Classification Rules",
        "",
    ]
    for row in contract_payload.get("classification_rules_v1", []):
        criteria = "; ".join(str(x) for x in list(row.get("criteria") or []))
        lines.append(f"- `{row.get('tempo', '')}`: {criteria} | {row.get('notes', '')}")
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_tempo_profile_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_tempo_profile_contract_v1()
    summary = build_tempo_profile_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "tempo_profile_latest.json"
    md_path = output_dir / "tempo_profile_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_tempo_profile_markdown_v1(contract, summary))
    return payload
