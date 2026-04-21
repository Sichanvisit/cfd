from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.state_slot_execution_interface_bridge import (
    attach_state_slot_execution_interface_bridge_fields_v1,
)
from backend.services.state_slot_symbol_extension_surface import (
    attach_state_slot_symbol_extension_surface_fields_v1,
)


STATE_SLOT_POSITION_LIFECYCLE_POLICY_CONTRACT_VERSION = (
    "state_slot_position_lifecycle_policy_contract_v1"
)
STATE_SLOT_POSITION_LIFECYCLE_POLICY_SUMMARY_VERSION = (
    "state_slot_position_lifecycle_policy_summary_v1"
)

LIFECYCLE_POLICY_STATE_ENUM_V1 = ("READY", "REVIEW_PENDING", "NOT_APPLICABLE")
ENTRY_POLICY_ENUM_V1 = ("NO_NEW_ENTRY", "DELAYED_ENTRY", "SELECTIVE_ENTRY", "ACTIVE_ENTRY")
HOLD_POLICY_ENUM_V1 = ("NO_HOLD_EDGE", "LIGHT_HOLD", "HOLD_FAVOR", "STRONG_HOLD")
ADD_POLICY_ENUM_V1 = ("NO_ADD", "PROBE_ADD_ONLY", "SELECTIVE_ADD", "ADD_FAVOR")
REDUCE_POLICY_ENUM_V1 = ("HOLD_SIZE", "LIGHT_REDUCE", "REDUCE_FAVOR", "REDUCE_STRONG")
EXIT_POLICY_ENUM_V1 = ("NO_EXIT_EDGE", "EXIT_WATCH", "EXIT_PREP", "EXIT_FAVOR")
POLICY_SOURCE_ENUM_V1 = ("BRIDGE_BIAS", "COMMON_SLOT_DERIVED", "UNAVAILABLE")


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


def build_state_slot_position_lifecycle_policy_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_SLOT_POSITION_LIFECYCLE_POLICY_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only lifecycle policy layer derived from state slots. Converts bridge bias and common slot "
            "surfaces into declarative entry, hold, add, reduce, and exit policies without changing execution "
            "or state25."
        ),
        "lifecycle_policy_state_enum_v1": list(LIFECYCLE_POLICY_STATE_ENUM_V1),
        "policy_source_enum_v1": list(POLICY_SOURCE_ENUM_V1),
        "entry_policy_enum_v1": list(ENTRY_POLICY_ENUM_V1),
        "hold_policy_enum_v1": list(HOLD_POLICY_ENUM_V1),
        "add_policy_enum_v1": list(ADD_POLICY_ENUM_V1),
        "reduce_policy_enum_v1": list(REDUCE_POLICY_ENUM_V1),
        "exit_policy_enum_v1": list(EXIT_POLICY_ENUM_V1),
        "row_level_fields_v1": [
            "state_slot_position_lifecycle_policy_profile_v1",
            "state_slot_lifecycle_policy_state_v1",
            "state_slot_execution_policy_source_v1",
            "entry_policy_v1",
            "hold_policy_v1",
            "add_policy_v1",
            "reduce_policy_v1",
            "exit_policy_v1",
            "state_slot_lifecycle_policy_reason_summary_v1",
        ],
        "control_rules_v1": [
            "lifecycle policy is read-only in v1",
            "lifecycle policy cannot place, cancel, resize, or exit positions directly",
            "xau can use the existing bridge bias as upstream source",
            "nas and btc can derive lifecycle policy from common slot surface when bridge bias is unavailable",
            "decomposition and lifecycle policy cannot change dominant_side",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_extension_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("state_slot_symbol_extension_surface_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_state_slot_symbol_extension_surface_fields_v1({symbol: row}).get(symbol, row))


def _ensure_bridge(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("state_slot_execution_interface_bridge_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_state_slot_execution_interface_bridge_fields_v1({symbol: row}).get(symbol, row))


def _base_biases_from_stage(stage: str) -> dict[str, str]:
    stage = _text(stage).upper()
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


def _lower(bias: str) -> str:
    order = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "NONE", "NONE": "NONE"}
    return order.get(_text(bias).upper(), "NONE")


def _raise(bias: str) -> str:
    order = {"NONE": "LOW", "LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "HIGH"}
    return order.get(_text(bias).upper(), "HIGH")


def _derived_biases(row: Mapping[str, Any]) -> tuple[str, dict[str, str]]:
    stage = _text(row.get("common_state_continuation_stage_v1")).upper()
    texture = _text(row.get("common_state_texture_slot_v1")).upper()
    ambiguity = _text(row.get("common_state_ambiguity_level_v1")).upper()
    compatibility = _text(row.get("common_vocabulary_compatibility_v1")).upper()
    slot_core = _text(row.get("common_state_slot_core_v1")).upper()
    if not slot_core:
        return ("UNAVAILABLE", _base_biases_from_stage("NONE"))
    biases = _base_biases_from_stage(stage)
    if texture == "WITH_FRICTION":
        biases["entry_bias_v1"] = _lower(biases["entry_bias_v1"])
        biases["add_bias_v1"] = _lower(biases["add_bias_v1"])
        biases["reduce_bias_v1"] = _raise(biases["reduce_bias_v1"])
    elif texture == "DRIFT":
        biases["entry_bias_v1"] = "LOW"
        biases["add_bias_v1"] = "LOW"
        biases["reduce_bias_v1"] = _raise(biases["reduce_bias_v1"])
    if ambiguity == "HIGH":
        biases["entry_bias_v1"] = "LOW"
        biases["add_bias_v1"] = "NONE"
        biases["reduce_bias_v1"] = "HIGH"
        biases["exit_bias_v1"] = _raise(biases["exit_bias_v1"])
    elif ambiguity == "MEDIUM":
        if biases["entry_bias_v1"] != "NONE":
            biases["entry_bias_v1"] = "LOW"
        biases["add_bias_v1"] = _lower(biases["add_bias_v1"])
    if compatibility == "REVIEW_PENDING":
        biases["entry_bias_v1"] = "LOW"
        biases["add_bias_v1"] = "NONE"
    return ("COMMON_SLOT_DERIVED", biases)


def _policy_from_bias(action: str, bias: str) -> str:
    bias = _text(bias).upper()
    if action == "entry":
        return {
            "HIGH": "ACTIVE_ENTRY",
            "MEDIUM": "SELECTIVE_ENTRY",
            "LOW": "DELAYED_ENTRY",
            "NONE": "NO_NEW_ENTRY",
        }.get(bias, "NO_NEW_ENTRY")
    if action == "hold":
        return {
            "HIGH": "STRONG_HOLD",
            "MEDIUM": "HOLD_FAVOR",
            "LOW": "LIGHT_HOLD",
            "NONE": "NO_HOLD_EDGE",
        }.get(bias, "NO_HOLD_EDGE")
    if action == "add":
        return {
            "HIGH": "ADD_FAVOR",
            "MEDIUM": "SELECTIVE_ADD",
            "LOW": "PROBE_ADD_ONLY",
            "NONE": "NO_ADD",
        }.get(bias, "NO_ADD")
    if action == "reduce":
        return {
            "HIGH": "REDUCE_STRONG",
            "MEDIUM": "REDUCE_FAVOR",
            "LOW": "LIGHT_REDUCE",
            "NONE": "HOLD_SIZE",
        }.get(bias, "HOLD_SIZE")
    if action == "exit":
        return {
            "HIGH": "EXIT_FAVOR",
            "MEDIUM": "EXIT_PREP",
            "LOW": "EXIT_WATCH",
            "NONE": "NO_EXIT_EDGE",
        }.get(bias, "NO_EXIT_EDGE")
    return ""


def build_state_slot_position_lifecycle_policy_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_extension_surface(row or {})
    payload = _ensure_bridge(payload)
    symbol = _text(payload.get("symbol")).upper()
    bridge_profile = _mapping(payload.get("state_slot_execution_interface_bridge_profile_v1"))
    bridge_state = _text(payload.get("state_slot_bridge_state_v1")).upper()
    slot_core = _text(payload.get("common_state_slot_core_v1")).upper()

    policy_source = "UNAVAILABLE"
    lifecycle_state = "NOT_APPLICABLE"
    biases: dict[str, str] = {
        "entry_bias_v1": "NONE",
        "hold_bias_v1": "NONE",
        "add_bias_v1": "NONE",
        "reduce_bias_v1": "NONE",
        "exit_bias_v1": "NONE",
    }
    source_slot = slot_core

    if bridge_profile and bridge_state in {"READY", "REVIEW_PENDING"}:
        policy_source = "BRIDGE_BIAS"
        lifecycle_state = bridge_state
        biases = {
            "entry_bias_v1": _text(payload.get("entry_bias_v1")).upper() or "NONE",
            "hold_bias_v1": _text(payload.get("hold_bias_v1")).upper() or "NONE",
            "add_bias_v1": _text(payload.get("add_bias_v1")).upper() or "NONE",
            "reduce_bias_v1": _text(payload.get("reduce_bias_v1")).upper() or "NONE",
            "exit_bias_v1": _text(payload.get("exit_bias_v1")).upper() or "NONE",
        }
        source_slot = _text(payload.get("bridge_source_slot_v1")).upper() or slot_core
    elif symbol in {"NAS100", "BTCUSD"} and slot_core:
        policy_source, biases = _derived_biases(payload)
        lifecycle_state = "REVIEW_PENDING" if _text(payload.get("common_vocabulary_compatibility_v1")).upper() == "REVIEW_PENDING" else "READY"

    profile = {
        "contract_version": STATE_SLOT_POSITION_LIFECYCLE_POLICY_CONTRACT_VERSION,
        "lifecycle_policy_state_v1": lifecycle_state,
        "policy_source_v1": policy_source,
        "source_slot_v1": source_slot,
        "entry_policy_v1": _policy_from_bias("entry", biases["entry_bias_v1"]),
        "hold_policy_v1": _policy_from_bias("hold", biases["hold_bias_v1"]),
        "add_policy_v1": _policy_from_bias("add", biases["add_bias_v1"]),
        "reduce_policy_v1": _policy_from_bias("reduce", biases["reduce_bias_v1"]),
        "exit_policy_v1": _policy_from_bias("exit", biases["exit_bias_v1"]),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    reason = (
        f"symbol={symbol}; source={policy_source}; lifecycle_state={lifecycle_state}; "
        f"slot={source_slot or slot_core or 'none'}; entry={profile['entry_policy_v1']}; "
        f"hold={profile['hold_policy_v1']}; reduce={profile['reduce_policy_v1']}; exit={profile['exit_policy_v1']}"
    )
    return {
        "state_slot_position_lifecycle_policy_profile_v1": profile,
        "state_slot_lifecycle_policy_state_v1": lifecycle_state,
        "state_slot_execution_policy_source_v1": policy_source,
        "entry_policy_v1": profile["entry_policy_v1"],
        "hold_policy_v1": profile["hold_policy_v1"],
        "add_policy_v1": profile["add_policy_v1"],
        "reduce_policy_v1": profile["reduce_policy_v1"],
        "exit_policy_v1": profile["exit_policy_v1"],
        "state_slot_lifecycle_policy_reason_summary_v1": reason,
    }


def attach_state_slot_position_lifecycle_policy_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_extension_surface(raw)
        row = _ensure_bridge(row)
        row.update(build_state_slot_position_lifecycle_policy_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_state_slot_position_lifecycle_policy_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_state_slot_position_lifecycle_policy_fields_v1(latest_signal_by_symbol)
    lifecycle_counts = Counter()
    source_counts = Counter()
    entry_counts = Counter()
    hold_counts = Counter()
    reduce_counts = Counter()
    for row in rows_by_symbol.values():
        lifecycle_counts.update([_text(row.get("state_slot_lifecycle_policy_state_v1"))])
        source_counts.update([_text(row.get("state_slot_execution_policy_source_v1"))])
        entry_counts.update([_text(row.get("entry_policy_v1"))])
        hold_counts.update([_text(row.get("hold_policy_v1"))])
        reduce_counts.update([_text(row.get("reduce_policy_v1"))])
    symbol_count = len(rows_by_symbol)
    ready_count = int(lifecycle_counts.get("READY", 0)) + int(lifecycle_counts.get("REVIEW_PENDING", 0))
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count and ready_count == symbol_count else "HOLD",
        "status_reasons": (
            ["lifecycle_policy_surface_available_for_all_symbols"]
            if symbol_count and ready_count == symbol_count
            else ["lifecycle_policy_surface_still_partial"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(ready_count),
        "lifecycle_policy_state_count_summary": dict(lifecycle_counts),
        "policy_source_count_summary": dict(source_counts),
        "entry_policy_count_summary": dict(entry_counts),
        "hold_policy_count_summary": dict(hold_counts),
        "reduce_policy_count_summary": dict(reduce_counts),
    }
    return {
        "contract_version": STATE_SLOT_POSITION_LIFECYCLE_POLICY_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_slot_position_lifecycle_policy_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Slot Position Lifecycle Policy v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- surface_ready_count: `{int(summary.get('surface_ready_count', 0) or 0)}`",
        "",
        "## Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: source={row.get('state_slot_execution_policy_source_v1', '')} | "
            f"entry={row.get('entry_policy_v1', '')} | hold={row.get('hold_policy_v1', '')} | "
            f"add={row.get('add_policy_v1', '')} | reduce={row.get('reduce_policy_v1', '')} | exit={row.get('exit_policy_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_slot_position_lifecycle_policy_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_slot_position_lifecycle_policy_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "state_slot_position_lifecycle_policy_latest.json"
    md_path = output_dir / "state_slot_position_lifecycle_policy_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_state_slot_position_lifecycle_policy_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
