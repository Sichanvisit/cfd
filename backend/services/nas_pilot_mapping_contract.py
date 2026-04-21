from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


NAS_PILOT_MAPPING_CONTRACT_VERSION = "nas_pilot_mapping_contract_v1"
NAS_PILOT_MAPPING_SUMMARY_VERSION = "nas_pilot_mapping_summary_v1"

NAS_PILOT_STATUS_ENUM_V1 = ("ACTIVE_PILOT", "REVIEW_PENDING")


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


def _pilot_window_catalog_v1() -> list[dict[str, Any]]:
    return [
        {
            "window_id_v1": "nas_up_breakout_core_1",
            "symbol_v1": "NAS100",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "NAS100_UP_CONTINUATION_BREAKOUT_HELD_V1",
            "polarity_slot_v1": "BULL",
            "intent_slot_v1": "CONTINUATION",
            "stage_slot_v1": "ACCEPTANCE",
            "texture_slot_v1": "WITH_FRICTION",
            "location_context_v1": "POST_BREAKOUT",
            "tempo_profile_v1": "PERSISTING",
            "ambiguity_level_v1": "LOW",
            "state_slot_core_v1": "BULL_CONTINUATION_ACCEPTANCE",
            "state_slot_modifier_bundle_v1": ["WITH_FRICTION", "POST_BREAKOUT", "PERSISTING", "AMBIGUITY_LOW"],
            "mapping_reason_summary_v1": (
                "Primary NAS bull breakout-held continuation window where continuation stayed structurally strong "
                "while caution remained heavy enough to justify a friction modifier."
            ),
        },
        {
            "window_id_v1": "nas_up_breakout_core_2",
            "symbol_v1": "NAS100",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "NAS100_UP_CONTINUATION_BREAKOUT_HELD_V1",
            "polarity_slot_v1": "BULL",
            "intent_slot_v1": "CONTINUATION",
            "stage_slot_v1": "EXTENSION",
            "texture_slot_v1": "WITH_FRICTION",
            "location_context_v1": "EXTENDED",
            "tempo_profile_v1": "PERSISTING",
            "ambiguity_level_v1": "MEDIUM",
            "state_slot_core_v1": "BULL_CONTINUATION_EXTENSION",
            "state_slot_modifier_bundle_v1": ["WITH_FRICTION", "EXTENDED", "PERSISTING", "AMBIGUITY_MEDIUM"],
            "mapping_reason_summary_v1": (
                "Secondary NAS bull continuation window where the move had already extended, so extension stayed in "
                "core while friction remained a modifier instead of turning into reversal."
            ),
        },
        {
            "window_id_v1": "nas_down_pending_1",
            "symbol_v1": "NAS100",
            "pilot_status_v1": "REVIEW_PENDING",
            "linked_profile_key_v1": "NAS100_DOWN_CONTINUATION_PENDING_V1",
            "polarity_slot_v1": "BEAR",
            "intent_slot_v1": "CONTINUATION",
            "stage_slot_v1": "INITIATION",
            "texture_slot_v1": "WITH_FRICTION",
            "location_context_v1": "AT_EDGE",
            "tempo_profile_v1": "EARLY",
            "ambiguity_level_v1": "HIGH",
            "state_slot_core_v1": "BEAR_CONTINUATION_INITIATION",
            "state_slot_modifier_bundle_v1": ["WITH_FRICTION", "AT_EDGE", "EARLY", "AMBIGUITY_HIGH"],
            "mapping_reason_summary_v1": (
                "Down-side NAS continuation still needs more retained evidence, so the pilot remains review-pending "
                "even though a provisional bear continuation initiation slot is visible."
            ),
        },
    ]


def build_nas_pilot_mapping_contract_v1() -> dict[str, Any]:
    windows = _pilot_window_catalog_v1()
    return {
        "contract_version": NAS_PILOT_MAPPING_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only NAS pilot mapping contract. Uses retained NAS windows to validate the common state slot "
            "language on NAS before any rollout beyond read-only."
        ),
        "pilot_status_enum_v1": list(NAS_PILOT_STATUS_ENUM_V1),
        "common_slot_mapping_fields_v1": [
            "polarity_slot_v1",
            "intent_slot_v1",
            "stage_slot_v1",
            "texture_slot_v1",
            "location_context_v1",
            "tempo_profile_v1",
            "ambiguity_level_v1",
            "state_slot_core_v1",
            "state_slot_modifier_bundle_v1",
        ],
        "pilot_window_catalog_v1": windows,
        "control_rules_v1": [
            "nas pilot validates common decomposition language rather than creating nas-only exceptions",
            "nas pilot remains read-only and cannot change execution or state25",
            "down-side nas pilot can remain review-pending while up-side pilot is already active",
            "pilot mapping cannot change dominant_side",
        ],
        "dominance_protection_v1": {
            "pilot_mapping_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_nas_pilot_mapping_summary_v1() -> dict[str, Any]:
    contract = build_nas_pilot_mapping_contract_v1()
    catalog = list(contract.get("pilot_window_catalog_v1") or [])
    status_counts = Counter()
    polarity_counts = Counter()
    intent_counts = Counter()
    stage_counts = Counter()
    for row in catalog:
        status_counts.update([str(row.get("pilot_status_v1", ""))])
        polarity_counts.update([str(row.get("polarity_slot_v1", ""))])
        intent_counts.update([str(row.get("intent_slot_v1", ""))])
        stage_counts.update([str(row.get("stage_slot_v1", ""))])
    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": NAS_PILOT_MAPPING_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "pilot_window_count": len(catalog),
        "pilot_status_count_summary": dict(status_counts),
        "polarity_count_summary": dict(polarity_counts),
        "intent_count_summary": dict(intent_counts),
        "stage_count_summary": dict(stage_counts),
        "dominance_protected_v1": True,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def render_nas_pilot_mapping_markdown_v1(contract: Mapping[str, Any] | None, summary: Mapping[str, Any] | None) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# NAS Pilot Mapping v1",
        "",
        f"- generated_at: `{summary_payload.get('generated_at', '')}`",
        f"- status: `{summary_payload.get('status', '')}`",
        f"- pilot_window_count: `{summary_payload.get('pilot_window_count', 0)}`",
        "",
        "## Pilot Windows",
        "",
    ]
    for row in contract_payload.get("pilot_window_catalog_v1", []):
        lines.append(
            f"- `{row.get('window_id_v1', '')}`: "
            f"{row.get('state_slot_core_v1', '')} | "
            f"status={row.get('pilot_status_v1', '')} | "
            f"modifiers={', '.join(str(x) for x in list(row.get('state_slot_modifier_bundle_v1') or []))}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_nas_pilot_mapping_summary_v1(*, shadow_auto_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_nas_pilot_mapping_contract_v1()
    summary = build_nas_pilot_mapping_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "nas_pilot_mapping_latest.json"
    md_path = output_dir / "nas_pilot_mapping_latest.md"
    payload["artifact_paths"] = {"json_path": str(json_path), "markdown_path": str(md_path)}
    _write_json(json_path, payload)
    _write_text(md_path, render_nas_pilot_mapping_markdown_v1(contract, summary))
    return payload
