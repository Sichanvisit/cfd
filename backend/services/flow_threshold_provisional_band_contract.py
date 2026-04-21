from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.aggregate_directional_flow_metrics_contract import (
    AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION,
    attach_aggregate_directional_flow_metrics_fields_v1,
)
from backend.services.retained_window_flow_calibration_contract import (
    RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION,
    attach_retained_window_flow_calibration_fields_v1,
)


FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION = "flow_threshold_provisional_band_contract_v1"
FLOW_THRESHOLD_PROVISIONAL_BAND_SUMMARY_VERSION = "flow_threshold_provisional_band_summary_v1"

BAND_POSITION_ENUM_V1 = ("ABOVE_CONFIRMED", "WITHIN_BUILDING", "BELOW_BUILDING", "UNAVAILABLE")
PROVISIONAL_FLOW_BAND_STATE_ENUM_V1 = (
    "STRUCTURE_BLOCKED",
    "CONFIRMED_CANDIDATE",
    "BUILDING_CANDIDATE",
    "UNCONFIRMED_CANDIDATE",
    "NOT_APPLICABLE",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_shadow_auto_dir() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_flow_threshold_provisional_band_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Compares live F2 conviction/persistence values against F3 retained-window provisional bands. "
            "Keeps structure ownership upstream while surfacing where each row currently sits relative to "
            "confirmed/building floors."
        ),
        "upstream_contract_versions_v1": [
            AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION,
            RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION,
        ],
        "band_position_enum_v1": list(BAND_POSITION_ENUM_V1),
        "provisional_flow_band_state_enum_v1": list(PROVISIONAL_FLOW_BAND_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "flow_threshold_provisional_band_profile_v1",
            "provisional_flow_band_state_v1",
            "aggregate_conviction_band_position_v1",
            "flow_persistence_band_position_v1",
            "aggregate_conviction_gap_to_confirmed_v1",
            "aggregate_conviction_gap_to_building_v1",
            "flow_persistence_gap_to_confirmed_v1",
            "flow_persistence_gap_to_building_v1",
            "provisional_flow_band_reason_summary_v1",
        ],
        "control_rules_v1": [
            "structure gate remains upstream and can block the row before any band interpretation",
            "confirmed candidate requires conviction and persistence both above confirmed floors",
            "building candidate is the state where one measure leads and the other is at least building-grade",
            "extension can stay eligible but is capped away from confirmed candidate state",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("aggregate_conviction_v1")):
        row = dict(attach_aggregate_directional_flow_metrics_fields_v1({"_": row}).get("_", row))
    if not _text(row.get("flow_threshold_profile_v1")):
        row = dict(attach_retained_window_flow_calibration_fields_v1({"_": row}).get("_", row))
    return row


def _stage(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("common_state_continuation_stage_v1")
        or row.get("xau_continuation_stage_v1")
        or row.get("flow_structure_gate_stage_v1")
    ).upper()


def _band_position(value: float, *, confirmed_floor: float, building_floor: float) -> str:
    if value >= confirmed_floor:
        return "ABOVE_CONFIRMED"
    if value >= building_floor:
        return "WITHIN_BUILDING"
    return "BELOW_BUILDING"


def _reason_summary(
    *,
    gate_state: str,
    stage: str,
    flow_threshold_profile: str,
    conviction: float,
    conviction_position: str,
    persistence: float,
    persistence_position: str,
    state: str,
) -> str:
    return (
        f"profile={flow_threshold_profile}; "
        f"gate={gate_state}; "
        f"stage={stage or 'NONE'}; "
        f"conviction={round(conviction, 4)}({conviction_position}); "
        f"persistence={round(persistence, 4)}({persistence_position}); "
        f"state={state}"
    )


def build_flow_threshold_provisional_band_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    gate_state = _text(payload.get("aggregate_flow_structure_gate_v1") or payload.get("flow_structure_gate_v1")).upper()
    conviction = _float(payload.get("aggregate_conviction_v1"), 0.0)
    persistence = _float(payload.get("flow_persistence_v1"), 0.0)
    conviction_confirmed = _float(payload.get("aggregate_conviction_confirmed_floor_v1"), 0.65)
    conviction_building = _float(payload.get("aggregate_conviction_building_floor_v1"), 0.45)
    persistence_confirmed = _float(payload.get("flow_persistence_confirmed_floor_v1"), 0.60)
    persistence_building = _float(payload.get("flow_persistence_building_floor_v1"), 0.45)
    flow_threshold_profile = _text(payload.get("flow_threshold_profile_v1")).upper() or "COMMON"
    stage = _stage(payload)

    conviction_position = _band_position(
        conviction,
        confirmed_floor=conviction_confirmed,
        building_floor=conviction_building,
    )
    persistence_position = _band_position(
        persistence,
        confirmed_floor=persistence_confirmed,
        building_floor=persistence_building,
    )

    if gate_state not in {"ELIGIBLE", "WEAK"}:
        state = "STRUCTURE_BLOCKED"
    elif stage == "EXTENSION":
        if conviction_position == "ABOVE_CONFIRMED" and persistence_position == "ABOVE_CONFIRMED":
            state = "BUILDING_CANDIDATE"
        elif conviction_position in {"ABOVE_CONFIRMED", "WITHIN_BUILDING"} and persistence_position in {
            "ABOVE_CONFIRMED",
            "WITHIN_BUILDING",
        }:
            state = "BUILDING_CANDIDATE"
        else:
            state = "UNCONFIRMED_CANDIDATE"
    elif gate_state == "ELIGIBLE" and conviction_position == "ABOVE_CONFIRMED" and persistence_position == "ABOVE_CONFIRMED":
        state = "CONFIRMED_CANDIDATE"
    elif (
        conviction_position in {"ABOVE_CONFIRMED", "WITHIN_BUILDING"}
        and persistence_position in {"ABOVE_CONFIRMED", "WITHIN_BUILDING"}
    ):
        state = "BUILDING_CANDIDATE"
    else:
        state = "UNCONFIRMED_CANDIDATE"

    reason = _reason_summary(
        gate_state=gate_state,
        stage=stage,
        flow_threshold_profile=flow_threshold_profile,
        conviction=conviction,
        conviction_position=conviction_position,
        persistence=persistence,
        persistence_position=persistence_position,
        state=state,
    )

    profile = {
        "contract_version": FLOW_THRESHOLD_PROVISIONAL_BAND_CONTRACT_VERSION,
        "upstream_aggregate_contract_version_v1": AGGREGATE_DIRECTIONAL_FLOW_METRICS_CONTRACT_VERSION,
        "upstream_retained_contract_version_v1": RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION,
        "provisional_flow_band_state_v1": state,
        "aggregate_conviction_band_position_v1": conviction_position,
        "flow_persistence_band_position_v1": persistence_position,
        "aggregate_conviction_gap_to_confirmed_v1": round(conviction - conviction_confirmed, 4),
        "aggregate_conviction_gap_to_building_v1": round(conviction - conviction_building, 4),
        "flow_persistence_gap_to_confirmed_v1": round(persistence - persistence_confirmed, 4),
        "flow_persistence_gap_to_building_v1": round(persistence - persistence_building, 4),
        "provisional_flow_band_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "flow_threshold_provisional_band_profile_v1": profile,
        "provisional_flow_band_state_v1": state,
        "aggregate_conviction_band_position_v1": conviction_position,
        "flow_persistence_band_position_v1": persistence_position,
        "aggregate_conviction_gap_to_confirmed_v1": profile["aggregate_conviction_gap_to_confirmed_v1"],
        "aggregate_conviction_gap_to_building_v1": profile["aggregate_conviction_gap_to_building_v1"],
        "flow_persistence_gap_to_confirmed_v1": profile["flow_persistence_gap_to_confirmed_v1"],
        "flow_persistence_gap_to_building_v1": profile["flow_persistence_gap_to_building_v1"],
        "provisional_flow_band_reason_summary_v1": reason,
    }


def attach_flow_threshold_provisional_band_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_flow_threshold_provisional_band_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_flow_threshold_provisional_band_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_threshold_provisional_band_fields_v1(latest_signal_by_symbol)
    state_counts = Counter()
    conviction_position_counts = Counter()
    persistence_position_counts = Counter()
    profile_counts = Counter()
    symbol_count = len(rows_by_symbol)

    for row in rows_by_symbol.values():
        state_counts.update([_text(row.get("provisional_flow_band_state_v1"))])
        conviction_position_counts.update([_text(row.get("aggregate_conviction_band_position_v1"))])
        persistence_position_counts.update([_text(row.get("flow_persistence_band_position_v1"))])
        profile_counts.update([_text(row.get("flow_threshold_profile_v1"))])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["flow_threshold_provisional_band_surface_available"] if symbol_count else ["no_rows_for_provisional_band"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "provisional_flow_band_state_count_summary": dict(state_counts),
        "aggregate_conviction_band_position_count_summary": dict(conviction_position_counts),
        "flow_persistence_band_position_count_summary": dict(persistence_position_counts),
        "flow_threshold_profile_count_summary": dict(profile_counts),
    }
    return {
        "contract_version": FLOW_THRESHOLD_PROVISIONAL_BAND_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_threshold_provisional_band_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Flow Threshold Provisional Band",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- provisional_flow_band_state_count_summary: {json.dumps(summary.get('provisional_flow_band_state_count_summary', {}), ensure_ascii=False)}",
        f"- aggregate_conviction_band_position_count_summary: {json.dumps(summary.get('aggregate_conviction_band_position_count_summary', {}), ensure_ascii=False)}",
        f"- flow_persistence_band_position_count_summary: {json.dumps(summary.get('flow_persistence_band_position_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: profile={row.get('flow_threshold_profile_v1', '')}, "
            f"state={row.get('provisional_flow_band_state_v1', '')}, "
            f"conviction={row.get('aggregate_conviction_band_position_v1', '')}, "
            f"persistence={row.get('flow_persistence_band_position_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_threshold_provisional_band_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_flow_threshold_provisional_band_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "flow_threshold_provisional_band_latest.json"
    markdown_path = output_dir / "flow_threshold_provisional_band_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_flow_threshold_provisional_band_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
