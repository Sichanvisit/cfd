from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


XAU_PILOT_MAPPING_CONTRACT_VERSION = "xau_pilot_mapping_contract_v1"
XAU_PILOT_MAPPING_SUMMARY_VERSION = "xau_pilot_mapping_summary_v1"

XAU_PILOT_STATUS_ENUM_V1 = ("ACTIVE_PILOT", "REVIEW_PENDING")


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
            "window_id_v1": "xau_up_recovery_1_0200_0300",
            "symbol_v1": "XAUUSD",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
            "polarity_slot_v1": "BULL",
            "intent_slot_v1": "RECOVERY",
            "stage_slot_v1": "INITIATION",
            "texture_slot_v1": "WITH_FRICTION",
            "location_context_v1": "POST_BREAKOUT",
            "tempo_profile_v1": "EARLY",
            "ambiguity_level_v1": "MEDIUM",
            "state_slot_core_v1": "BULL_RECOVERY_INITIATION",
            "state_slot_modifier_bundle_v1": [
                "WITH_FRICTION",
                "POST_BREAKOUT",
                "EARLY",
                "AMBIGUITY_MEDIUM",
            ],
            "mapping_reason_summary_v1": (
                "Early XAU bull recovery window where recovery intent was present but sell-side probe friction "
                "still overfired, making initiation plus friction a better common explanation than raw continuation."
            ),
        },
        {
            "window_id_v1": "xau_up_recovery_2_0500_0642",
            "symbol_v1": "XAUUSD",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
            "polarity_slot_v1": "BULL",
            "intent_slot_v1": "RECOVERY",
            "stage_slot_v1": "ACCEPTANCE",
            "texture_slot_v1": "WITH_FRICTION",
            "location_context_v1": "IN_BOX",
            "tempo_profile_v1": "PERSISTING",
            "ambiguity_level_v1": "MEDIUM",
            "state_slot_core_v1": "BULL_RECOVERY_ACCEPTANCE",
            "state_slot_modifier_bundle_v1": [
                "WITH_FRICTION",
                "IN_BOX",
                "PERSISTING",
                "AMBIGUITY_MEDIUM",
            ],
            "mapping_reason_summary_v1": (
                "Later XAU bull recovery window where the rebound was no longer just starting and persistence "
                "mattered, but upper-reject friction still prevented a clean texture classification."
            ),
        },
        {
            "window_id_v1": "xau_down_core_1_0030_0200",
            "symbol_v1": "XAUUSD",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
            "polarity_slot_v1": "BEAR",
            "intent_slot_v1": "REJECTION",
            "stage_slot_v1": "ACCEPTANCE",
            "texture_slot_v1": "CLEAN",
            "location_context_v1": "AT_EDGE",
            "tempo_profile_v1": "PERSISTING",
            "ambiguity_level_v1": "LOW",
            "state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
            "state_slot_modifier_bundle_v1": [
                "CLEAN",
                "AT_EDGE",
                "PERSISTING",
                "AMBIGUITY_LOW",
            ],
            "mapping_reason_summary_v1": (
                "Core XAU bear rejection window where upper-edge rejection aligned with real down continuation "
                "instead of bull friction, making rejection acceptance the clearest common slot."
            ),
        },
        {
            "window_id_v1": "xau_down_core_2_0330_0430",
            "symbol_v1": "XAUUSD",
            "pilot_status_v1": "ACTIVE_PILOT",
            "linked_profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
            "polarity_slot_v1": "BEAR",
            "intent_slot_v1": "REJECTION",
            "stage_slot_v1": "ACCEPTANCE",
            "texture_slot_v1": "DRIFT",
            "location_context_v1": "AT_EDGE",
            "tempo_profile_v1": "REPEATING",
            "ambiguity_level_v1": "LOW",
            "state_slot_core_v1": "BEAR_REJECTION_ACCEPTANCE",
            "state_slot_modifier_bundle_v1": [
                "DRIFT",
                "AT_EDGE",
                "REPEATING",
                "AMBIGUITY_LOW",
            ],
            "mapping_reason_summary_v1": (
                "Follow-on XAU bear continuation window where rejection stayed valid but the move consumed more as "
                "drift and repeated pressure than as a single clean breakdown burst."
            ),
        },
    ]


def build_xau_pilot_mapping_contract_v1() -> dict[str, Any]:
    windows = _pilot_window_catalog_v1()
    return {
        "contract_version": XAU_PILOT_MAPPING_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only XAU pilot mapping contract. Uses retained XAU windows to validate the common state polarity "
            "decomposition frame rather than creating permanent XAU-only exceptions."
        ),
        "pilot_status_enum_v1": list(XAU_PILOT_STATUS_ENUM_V1),
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
            "xau pilot exists to validate the common decomposition frame, not to create permanent symbol-only exceptions",
            "both bull and bear continuation evidence must remain visible in the pilot catalog",
            "pilot mapping cannot change dominant_side",
            "pilot mapping remains read-only and does not change execution or state25",
            "common slot language is promoted before any symbol-specific naming expansion",
        ],
        "dominance_protection_v1": {
            "pilot_mapping_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "bridge_contract_v1": {
            "bridge_to_slot_vocabulary_v1": True,
            "bridge_to_rejection_split_v1": True,
            "bridge_to_continuation_stage_v1": True,
            "bridge_to_location_v1": True,
            "bridge_to_tempo_v1": True,
            "bridge_to_ambiguity_v1": True,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        },
    }


def build_xau_pilot_mapping_summary_v1() -> dict[str, Any]:
    contract = build_xau_pilot_mapping_contract_v1()
    catalog = list(contract.get("pilot_window_catalog_v1") or [])
    status_counts = Counter()
    polarity_counts = Counter()
    intent_counts = Counter()
    stage_counts = Counter()
    texture_counts = Counter()

    for row in catalog:
        status_counts.update([str(row.get("pilot_status_v1", ""))])
        polarity_counts.update([str(row.get("polarity_slot_v1", ""))])
        intent_counts.update([str(row.get("intent_slot_v1", ""))])
        stage_counts.update([str(row.get("stage_slot_v1", ""))])
        texture_counts.update([str(row.get("texture_slot_v1", ""))])

    return {
        "generated_at": _now_iso(),
        "status": "READY",
        "summary_version": XAU_PILOT_MAPPING_SUMMARY_VERSION,
        "contract_version": contract["contract_version"],
        "pilot_window_count": len(catalog),
        "pilot_status_count_summary": dict(status_counts),
        "polarity_count_summary": dict(polarity_counts),
        "intent_count_summary": dict(intent_counts),
        "stage_count_summary": dict(stage_counts),
        "texture_count_summary": dict(texture_counts),
        "dominance_protected_v1": not bool(
            contract.get("dominance_protection_v1", {}).get("pilot_mapping_can_change_dominant_side")
        ),
        "execution_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("execution_change_allowed")),
        "state25_change_allowed": bool(contract.get("bridge_contract_v1", {}).get("state25_change_allowed")),
    }


def render_xau_pilot_mapping_markdown_v1(
    contract: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    contract_payload = dict(contract or {})
    summary_payload = dict(summary or {})
    lines = [
        "# XAU Pilot Mapping v1",
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
            f"modifiers={', '.join(str(x) for x in list(row.get('state_slot_modifier_bundle_v1') or []))} | "
            f"profile={row.get('linked_profile_key_v1', '')}"
        )
    lines.extend(["", "## Control Rules", ""])
    for rule in contract_payload.get("control_rules_v1", []):
        lines.append(f"- {rule}")
    return "\n".join(lines).strip() + "\n"


def generate_and_write_xau_pilot_mapping_summary_v1(
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_xau_pilot_mapping_contract_v1()
    summary = build_xau_pilot_mapping_summary_v1()
    payload = {
        "contract_version": contract["contract_version"],
        "summary": summary,
    }
    json_path = output_dir / "xau_pilot_mapping_latest.json"
    md_path = output_dir / "xau_pilot_mapping_latest.md"
    payload["artifact_paths"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    _write_json(json_path, payload)
    _write_text(md_path, render_xau_pilot_mapping_markdown_v1(contract, summary))
    return payload
