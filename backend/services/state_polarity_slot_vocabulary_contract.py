from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


STATE_POLARITY_SLOT_VOCABULARY_CONTRACT_VERSION = "state_polarity_slot_vocabulary_contract_v1"
STATE_POLARITY_SLOT_VOCABULARY_SUMMARY_VERSION = "state_polarity_slot_vocabulary_summary_v1"

POLARITY_SLOT_ENUM_V1 = ("BULL", "BEAR")
INTENT_SLOT_ENUM_V1 = ("CONTINUATION", "RECOVERY", "REJECTION", "BREAKDOWN", "BOUNDARY")
STAGE_SLOT_ENUM_V1 = ("INITIATION", "ACCEPTANCE", "EXTENSION", "NONE")
TEXTURE_SLOT_ENUM_V1 = ("CLEAN", "WITH_FRICTION", "DRIFT", "EXHAUSTING", "FAILED_RECLAIM", "POST_DIP", "NONE")
LOCATION_CONTEXT_ENUM_V1 = ("IN_BOX", "AT_EDGE", "POST_BREAKOUT", "EXTENDED", "NONE")
AMBIGUITY_LEVEL_ENUM_V1 = ("LOW", "MEDIUM", "HIGH")

EXECUTION_INTERFACE_FIELDS_V1 = (
    "entry_bias_v1",
    "hold_bias_v1",
    "add_bias_v1",
    "reduce_bias_v1",
    "exit_bias_v1",
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


def build_state_polarity_slot_vocabulary_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_POLARITY_SLOT_VOCABULARY_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Common state polarity decomposition vocabulary contract. "
            "Defines the shared slot language before any symbol-specific subtype expansion."
        ),
        "core_slot_layers_v1": [
            {
                "layer": "polarity",
                "enum": list(POLARITY_SLOT_ENUM_V1),
                "notes": "Top-level directional state. Dominance layer still owns side changes.",
            },
            {
                "layer": "intent",
                "enum": list(INTENT_SLOT_ENUM_V1),
                "notes": "Core structural intent. Only promote to core when the difference changes execution decisions.",
            },
            {
                "layer": "stage",
                "enum": list(STAGE_SLOT_ENUM_V1),
                "notes": "Structural time position: when the move is happening.",
            },
        ],
        "modifier_layers_v1": [
            {
                "layer": "texture",
                "enum": list(TEXTURE_SLOT_ENUM_V1),
                "notes": "Execution quality: how the move should be consumed.",
            },
            {
                "layer": "location",
                "enum": list(LOCATION_CONTEXT_ENUM_V1),
                "notes": "Location context starts as a modifier only in v1.5.",
            },
            {
                "layer": "tempo",
                "enum": [],
                "notes": "Tempo starts as raw persistence/count fields plus modifier reasoning, not as a closed enum.",
            },
            {
                "layer": "ambiguity",
                "enum": list(AMBIGUITY_LEVEL_ENUM_V1),
                "notes": "Ambiguity adjusts mode/caution only and cannot change dominant_side.",
            },
        ],
        "field_catalog_v1": [
            "polarity_slot_v1",
            "intent_slot_v1",
            "stage_slot_v1",
            "texture_slot_v1",
            "location_context_v1",
            "tempo_profile_v1",
            "ambiguity_level_v1",
            "state_slot_core_v1",
            "state_slot_modifier_bundle_v1",
            "state_slot_reason_summary_v1",
        ],
        "core_slot_definition_v1": "polarity + intent + stage",
        "modifier_definition_v1": "texture + location + tempo + ambiguity",
        "control_rules_v1": [
            "core slot is promoted only when the structural difference changes execution decisions",
            "decomposition layer cannot change dominant_side",
            "stage means when; texture means how",
            "location and tempo start as modifiers, not core slot drivers",
            "ambiguity is a modifier that adjusts boundary/caution without changing side",
            "reversal rejection and friction rejection must never be merged",
        ],
        "dominance_protection_v1": {
            "decomposition_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "execution_bridge_v1": {
            "declared_only": True,
            "fields": list(EXECUTION_INTERFACE_FIELDS_V1),
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_state_polarity_slot_vocabulary_summary_v1() -> dict[str, Any]:
    contract = build_state_polarity_slot_vocabulary_contract_v1()
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": STATE_POLARITY_SLOT_VOCABULARY_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "core_layer_count": len(contract.get("core_slot_layers_v1", [])),
        "modifier_layer_count": len(contract.get("modifier_layers_v1", [])),
        "field_count": len(contract.get("field_catalog_v1", [])),
        "core_slot_definition_v1": contract.get("core_slot_definition_v1", ""),
        "modifier_definition_v1": contract.get("modifier_definition_v1", ""),
        "execution_bridge_declared_v1": bool(contract.get("execution_bridge_v1", {}).get("declared_only")),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("decomposition_can_change_dominant_side")
        ),
        "core_enums_v1": {
            "polarity": len(POLARITY_SLOT_ENUM_V1),
            "intent": len(INTENT_SLOT_ENUM_V1),
            "stage": len(STAGE_SLOT_ENUM_V1),
        },
        "modifier_enums_v1": {
            "texture": len(TEXTURE_SLOT_ENUM_V1),
            "location": len(LOCATION_CONTEXT_ENUM_V1),
            "ambiguity": len(AMBIGUITY_LEVEL_ENUM_V1),
        },
    }


def render_state_polarity_slot_vocabulary_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# State Polarity Slot Vocabulary v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- core_slot_definition_v1: `{summary_payload.get('core_slot_definition_v1', '')}`",
        f"- modifier_definition_v1: `{summary_payload.get('modifier_definition_v1', '')}`",
        f"- field_count: `{summary_payload.get('field_count', 0)}`",
        "",
        "## Core Layers",
        "",
    ]
    for layer in contract_payload.get("core_slot_layers_v1", []):
        lines.append(
            f"- `{layer.get('layer', '')}`: enum={', '.join(str(x) for x in list(layer.get('enum') or []))} | "
            f"notes={layer.get('notes', '')}"
        )
    lines.extend(["", "## Modifier Layers", ""])
    for layer in contract_payload.get("modifier_layers_v1", []):
        enum_values = ", ".join(str(x) for x in list(layer.get("enum") or [])) or "raw/count-based"
        lines.append(
            f"- `{layer.get('layer', '')}`: enum={enum_values} | notes={layer.get('notes', '')}"
        )
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_polarity_slot_vocabulary_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_state_polarity_slot_vocabulary_contract_v1()
    summary = build_state_polarity_slot_vocabulary_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "state_polarity_slot_vocabulary_latest.json"
    md_path = output_dir / "state_polarity_slot_vocabulary_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_state_polarity_slot_vocabulary_markdown_v1(contract, summary))
    return payload
