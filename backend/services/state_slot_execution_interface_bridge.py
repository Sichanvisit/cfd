from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.xau_readonly_surface_contract import attach_xau_readonly_surface_fields_v1


STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_CONTRACT_VERSION = "state_slot_execution_interface_bridge_contract_v1"
STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_SUMMARY_VERSION = "state_slot_execution_interface_bridge_summary_v1"

EXECUTION_BIAS_ENUM_V1 = ("NONE", "LOW", "MEDIUM", "HIGH")
EXECUTION_BRIDGE_STATE_ENUM_V1 = ("READY", "REVIEW_PENDING", "NOT_APPLICABLE")


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


def build_state_slot_execution_interface_bridge_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only bridge from state slots to a future execution policy layer. "
            "Declares entry, hold, add, reduce, and exit bias without changing execution or state25."
        ),
        "execution_bias_enum_v1": list(EXECUTION_BIAS_ENUM_V1),
        "execution_bridge_state_enum_v1": list(EXECUTION_BRIDGE_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "state_slot_execution_interface_bridge_profile_v1",
            "state_slot_bridge_state_v1",
            "bridge_source_slot_v1",
            "entry_bias_v1",
            "hold_bias_v1",
            "add_bias_v1",
            "reduce_bias_v1",
            "exit_bias_v1",
            "state_slot_execution_bridge_reason_summary_v1",
        ],
        "control_rules_v1": [
            "bridge is declarative and read-only in v1",
            "bridge cannot place, cancel, resize, or exit positions directly",
            "stage primarily changes lifecycle posture while texture and ambiguity adjust aggressiveness",
            "WITH_FRICTION reduces entry or add bias before it ever becomes a trade command",
            "EXTENSION shifts bias toward reduce and exit preparation without forcing reversal",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("xau_readonly_surface_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_xau_readonly_surface_fields_v1({symbol: row}).get(symbol, row))


def _lower(bias: str) -> str:
    order = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NONE", "NONE": "NONE"}
    return order.get(bias, "NONE")


def _raise(bias: str) -> str:
    order = {"NONE": "LOW", "LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "HIGH"}
    return order.get(bias, "HIGH")


def _base_biases(stage: str) -> dict[str, str]:
    stage = stage.upper()
    if stage == "INITIATION":
        return {
            "entry_bias_v1": "HIGH",
            "hold_bias_v1": "MEDIUM",
            "add_bias_v1": "LOW",
            "reduce_bias_v1": "LOW",
            "exit_bias_v1": "LOW",
        }
    if stage == "ACCEPTANCE":
        return {
            "entry_bias_v1": "MEDIUM",
            "hold_bias_v1": "HIGH",
            "add_bias_v1": "MEDIUM",
            "reduce_bias_v1": "LOW",
            "exit_bias_v1": "LOW",
        }
    if stage == "EXTENSION":
        return {
            "entry_bias_v1": "LOW",
            "hold_bias_v1": "MEDIUM",
            "add_bias_v1": "LOW",
            "reduce_bias_v1": "HIGH",
            "exit_bias_v1": "MEDIUM",
        }
    return {
        "entry_bias_v1": "NONE",
        "hold_bias_v1": "LOW",
        "add_bias_v1": "NONE",
        "reduce_bias_v1": "LOW",
        "exit_bias_v1": "LOW",
    }


def _apply_modifiers(biases: dict[str, str], *, texture: str, ambiguity: str, match_state: str) -> dict[str, str]:
    adjusted = dict(biases)
    if texture == "WITH_FRICTION":
        adjusted["entry_bias_v1"] = _lower(adjusted["entry_bias_v1"])
        adjusted["add_bias_v1"] = _lower(adjusted["add_bias_v1"])
        adjusted["reduce_bias_v1"] = _raise(adjusted["reduce_bias_v1"])
    elif texture == "DRIFT":
        adjusted["entry_bias_v1"] = "LOW"
        adjusted["add_bias_v1"] = "LOW"
        adjusted["reduce_bias_v1"] = _raise(adjusted["reduce_bias_v1"])
    if ambiguity == "HIGH":
        adjusted["entry_bias_v1"] = "LOW"
        adjusted["add_bias_v1"] = "NONE"
        adjusted["reduce_bias_v1"] = "HIGH"
        adjusted["exit_bias_v1"] = _raise(adjusted["exit_bias_v1"])
    elif ambiguity == "MEDIUM":
        adjusted["entry_bias_v1"] = "LOW" if adjusted["entry_bias_v1"] != "NONE" else "NONE"
        adjusted["add_bias_v1"] = _lower(adjusted["add_bias_v1"])
    if match_state == "REVIEW_PENDING":
        adjusted["entry_bias_v1"] = "LOW"
        adjusted["add_bias_v1"] = "NONE"
    return adjusted


def build_state_slot_execution_interface_bridge_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_surface(row or {})
    symbol = _text(payload.get("symbol")).upper()
    slot_core = _text(payload.get("xau_state_slot_core_v1")).upper()
    match_state = _text(payload.get("xau_pilot_window_match_v1")).upper()
    stage = _text(payload.get("xau_continuation_stage_v1")).upper()
    texture = _text(payload.get("xau_texture_slot_v1")).upper()
    ambiguity = _text(payload.get("xau_ambiguity_level_v1")).upper()

    if symbol != "XAUUSD" or not slot_core:
        profile = {
            "contract_version": STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_CONTRACT_VERSION,
            "bridge_state_v1": "NOT_APPLICABLE",
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "state_slot_execution_interface_bridge_profile_v1": profile,
            "state_slot_bridge_state_v1": "NOT_APPLICABLE",
            "bridge_source_slot_v1": "",
            "entry_bias_v1": "NONE",
            "hold_bias_v1": "NONE",
            "add_bias_v1": "NONE",
            "reduce_bias_v1": "NONE",
            "exit_bias_v1": "NONE",
            "state_slot_execution_bridge_reason_summary_v1": "slot_not_available",
        }

    bridge_state = "REVIEW_PENDING" if match_state == "REVIEW_PENDING" else "READY"
    biases = _apply_modifiers(_base_biases(stage), texture=texture, ambiguity=ambiguity, match_state=match_state)
    reason = (
        f"slot={slot_core}; stage={stage}; texture={texture}; ambiguity={ambiguity}; "
        f"match={match_state}; bridge_state={bridge_state}"
    )
    profile = {
        "contract_version": STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_CONTRACT_VERSION,
        "bridge_state_v1": bridge_state,
        "bridge_source_slot_v1": slot_core,
        **biases,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "state_slot_execution_interface_bridge_profile_v1": profile,
        "state_slot_bridge_state_v1": bridge_state,
        "bridge_source_slot_v1": slot_core,
        **biases,
        "state_slot_execution_bridge_reason_summary_v1": reason,
    }


def attach_state_slot_execution_interface_bridge_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_surface(raw)
        row.update(build_state_slot_execution_interface_bridge_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_state_slot_execution_interface_bridge_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_state_slot_execution_interface_bridge_fields_v1(latest_signal_by_symbol)
    bridge_state_counts = Counter()
    entry_counts = Counter()
    hold_counts = Counter()
    xau_count = 0
    for row in rows_by_symbol.values():
        if _text(row.get("symbol")).upper() == "XAUUSD":
            xau_count += 1
            bridge_state_counts.update([_text(row.get("state_slot_bridge_state_v1"))])
            entry_counts.update([_text(row.get("entry_bias_v1"))])
            hold_counts.update([_text(row.get("hold_bias_v1"))])
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if xau_count else "HOLD",
        "status_reasons": (
            ["execution_interface_bridge_declared_for_xau"] if xau_count else ["xau_slot_surface_missing"]
        ),
        "xau_row_count": int(xau_count),
        "bridge_state_count_summary": dict(bridge_state_counts),
        "entry_bias_count_summary": dict(entry_counts),
        "hold_bias_count_summary": dict(hold_counts),
    }
    return {
        "contract_version": STATE_SLOT_EXECUTION_INTERFACE_BRIDGE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_slot_execution_interface_bridge_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Slot Execution Interface Bridge v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- xau_row_count: `{int(summary.get('xau_row_count', 0) or 0)}`",
        "",
        "## XAU Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "XAUUSD":
            continue
        lines.append(
            f"- `{symbol}`: slot={row.get('bridge_source_slot_v1', '')} | "
            f"entry={row.get('entry_bias_v1', '')} | hold={row.get('hold_bias_v1', '')} | "
            f"add={row.get('add_bias_v1', '')} | reduce={row.get('reduce_bias_v1', '')} | exit={row.get('exit_bias_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_slot_execution_interface_bridge_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_slot_execution_interface_bridge_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "state_slot_execution_interface_bridge_latest.json"
    md_path = output_dir / "state_slot_execution_interface_bridge_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_state_slot_execution_interface_bridge_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
