from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.xau_pilot_mapping_contract import build_xau_pilot_mapping_contract_v1


STATE_SLOT_COMMONIZATION_JUDGE_CONTRACT_VERSION = "state_slot_commonization_judge_contract_v1"
STATE_SLOT_COMMONIZATION_JUDGE_SUMMARY_VERSION = "state_slot_commonization_judge_summary_v1"

COMMONIZATION_VERDICT_ENUM_V1 = (
    "COMMON_READY",
    "COMMON_WITH_SYMBOL_THRESHOLD",
    "XAU_LOCAL_ONLY",
    "HOLD_FOR_MORE_SYMBOLS",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_state_slot_commonization_judge_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_SLOT_COMMONIZATION_JUDGE_CONTRACT_VERSION,
        "status": "READY",
        "commonization_verdict_enum_v1": list(COMMONIZATION_VERDICT_ENUM_V1),
        "description": (
            "Read-only commonization judge for decomposition slots. Decides whether XAU-validated slots "
            "look common-ready, common with symbol-specific thresholds, still XAU-local, or still held "
            "for more symbols before NAS/BTC rollout."
        ),
        "slot_judgement_fields_v1": [
            "state_slot_core_v1",
            "commonization_verdict_v1",
            "commonization_reason_summary_v1",
            "threshold_specificity_required_v1",
            "xau_validation_support_state_v1",
        ],
        "control_rules_v1": [
            "commonization judge is summary-only in v1",
            "xau pilot is allowed to declare common language readiness without forcing immediate NAS/BTC rollout",
            "slots with friction or drift can still be common but usually require symbol-specific thresholds",
            "single-symbol evidence is not enough to mark a slot as fully common-ready unless validation is exceptionally clean",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _collect_xau_slot_rows(xau_pilot_mapping_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    contract = _mapping(xau_pilot_mapping_report.get("contract")) if "contract" in xau_pilot_mapping_report else {}
    if not contract:
        contract = build_xau_pilot_mapping_contract_v1()
    return list(contract.get("pilot_window_catalog_v1") or [])


def _verdict_for_slot(*, slot_core: str, textures: set[str], ambiguity_levels: set[str], support_count: int) -> tuple[str, str, bool]:
    if not slot_core:
        return ("HOLD_FOR_MORE_SYMBOLS", "slot_core_missing", False)
    if support_count <= 0:
        return ("HOLD_FOR_MORE_SYMBOLS", "no_xau_support", False)
    if "HIGH" in ambiguity_levels:
        return ("HOLD_FOR_MORE_SYMBOLS", "high_ambiguity_requires_more_symbol_evidence", False)
    if any(texture in {"WITH_FRICTION", "DRIFT"} for texture in textures):
        return (
            "COMMON_WITH_SYMBOL_THRESHOLD",
            "common_slot_language_looks_valid_but_texture_requires_symbol_specific_thresholds",
            True,
        )
    if support_count >= 2:
        return ("COMMON_READY", "xau_pilot_support_is_clean_and_repeated", False)
    return ("HOLD_FOR_MORE_SYMBOLS", "single_clean_support_still_needs_more_symbols", False)


def build_state_slot_commonization_judge_summary_v1(
    *,
    xau_pilot_mapping_report: Mapping[str, Any] | None = None,
    xau_readonly_surface_report: Mapping[str, Any] | None = None,
    xau_decomposition_validation_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pilot_contract = build_xau_pilot_mapping_contract_v1()
    if isinstance(_mapping(xau_pilot_mapping_report).get("contract"), Mapping):
        pilot_contract = _mapping(_mapping(xau_pilot_mapping_report).get("contract"))
    pilot_rows = list(pilot_contract.get("pilot_window_catalog_v1") or [])
    validation_summary = _mapping(_mapping(xau_decomposition_validation_report).get("summary"))
    readonly_summary = _mapping(_mapping(xau_readonly_surface_report).get("summary"))

    slot_groups: dict[str, dict[str, Any]] = {}
    for row in pilot_rows:
        slot_core = _text(row.get("state_slot_core_v1"))
        if slot_core not in slot_groups:
            slot_groups[slot_core] = {
                "textures": set(),
                "ambiguity_levels": set(),
                "window_ids": [],
            }
        slot_groups[slot_core]["textures"].add(_text(row.get("texture_slot_v1")).upper())
        slot_groups[slot_core]["ambiguity_levels"].add(_text(row.get("ambiguity_level_v1")).upper())
        slot_groups[slot_core]["window_ids"].append(_text(row.get("window_id_v1")))

    slot_catalog: list[dict[str, Any]] = []
    verdict_counts = Counter()
    threshold_count = 0
    for slot_core, payload in slot_groups.items():
        verdict, reason, threshold_required = _verdict_for_slot(
            slot_core=slot_core,
            textures=set(payload["textures"]),
            ambiguity_levels=set(payload["ambiguity_levels"]),
            support_count=len(payload["window_ids"]),
        )
        verdict_counts.update([verdict])
        if threshold_required:
            threshold_count += 1
        slot_catalog.append(
            {
                "state_slot_core_v1": slot_core,
                "commonization_verdict_v1": verdict,
                "commonization_reason_summary_v1": reason,
                "threshold_specificity_required_v1": bool(threshold_required),
                "xau_validation_support_state_v1": (
                    "ALIGNED_ONLY"
                    if validation_summary.get("slot_alignment_rate") == 1.0
                    else "MIXED_OR_PENDING"
                ),
                "source_window_ids_v1": list(payload["window_ids"]),
            }
        )

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if slot_catalog else "HOLD",
        "status_reasons": (
            ["xau_slot_commonization_catalog_available"] if slot_catalog else ["xau_slot_catalog_missing"]
        ),
        "slot_count": int(len(slot_catalog)),
        "commonization_verdict_count_summary": dict(verdict_counts),
        "threshold_specific_slot_count": int(threshold_count),
        "xau_slot_alignment_rate": validation_summary.get("slot_alignment_rate"),
        "xau_should_have_done_candidate_count": validation_summary.get("should_have_done_candidate_count"),
        "xau_surface_ready_count": readonly_summary.get("surface_ready_count"),
    }
    return {
        "contract_version": STATE_SLOT_COMMONIZATION_JUDGE_SUMMARY_VERSION,
        "summary": summary,
        "slot_catalog_v1": slot_catalog,
    }


def render_state_slot_commonization_judge_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Slot Commonization Judge v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- slot_count: `{int(summary.get('slot_count', 0) or 0)}`",
        f"- threshold_specific_slot_count: `{int(summary.get('threshold_specific_slot_count', 0) or 0)}`",
        "",
        "## Slot Catalog",
        "",
    ]
    for row in list(payload.get("slot_catalog_v1") or []):
        lines.append(
            f"- `{row.get('state_slot_core_v1', '')}`: verdict={row.get('commonization_verdict_v1', '')} | "
            f"threshold_specific={row.get('threshold_specificity_required_v1', False)} | "
            f"reason={row.get('commonization_reason_summary_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_slot_commonization_judge_summary_v1(
    *,
    xau_pilot_mapping_report: Mapping[str, Any] | None = None,
    xau_readonly_surface_report: Mapping[str, Any] | None = None,
    xau_decomposition_validation_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_slot_commonization_judge_summary_v1(
        xau_pilot_mapping_report=xau_pilot_mapping_report,
        xau_readonly_surface_report=xau_readonly_surface_report,
        xau_decomposition_validation_report=xau_decomposition_validation_report,
    )
    json_path = output_dir / "state_slot_commonization_judge_latest.json"
    md_path = output_dir / "state_slot_commonization_judge_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_state_slot_commonization_judge_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "slot_catalog_v1": list(report.get("slot_catalog_v1") or []),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
