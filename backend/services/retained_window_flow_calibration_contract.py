from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.btc_pilot_mapping_contract import build_btc_pilot_mapping_contract_v1
from backend.services.nas_pilot_mapping_contract import build_nas_pilot_mapping_contract_v1
from backend.services.xau_pilot_mapping_contract import build_xau_pilot_mapping_contract_v1


RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION = "retained_window_flow_calibration_contract_v1"
RETAINED_WINDOW_FLOW_CALIBRATION_SUMMARY_VERSION = "retained_window_flow_calibration_summary_v1"

RETAINED_WINDOW_GROUP_ENUM_V1 = (
    "CONFIRMED_POSITIVE",
    "BUILDING_POSITIVE",
    "UNCONFIRMED_MIXED",
    "OPPOSED_FALSE",
)
FLOW_THRESHOLD_PROFILE_ENUM_V1 = ("COMMON", "XAU_TUNED", "NAS_TUNED", "BTC_TUNED")
RETAINED_WINDOW_CALIBRATION_STATE_ENUM_V1 = (
    "PROVISIONAL_BAND_READY",
    "PARTIAL_READY",
    "REVIEW_PENDING",
    "UNCONFIGURED",
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


def _threshold_profiles_v1() -> dict[str, dict[str, Any]]:
    return {
        "XAUUSD": {
            "flow_threshold_profile_v1": "XAU_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.65,
            "aggregate_conviction_building_floor_v1": 0.45,
            "flow_persistence_confirmed_floor_v1": 0.62,
            "flow_persistence_building_floor_v1": 0.48,
            "min_persisting_bars_v1": 4,
            "exact_match_bonus_strength_v1": "MEDIUM",
        },
        "NAS100": {
            "flow_threshold_profile_v1": "NAS_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.60,
            "aggregate_conviction_building_floor_v1": 0.40,
            "flow_persistence_confirmed_floor_v1": 0.58,
            "flow_persistence_building_floor_v1": 0.45,
            "min_persisting_bars_v1": 3,
            "exact_match_bonus_strength_v1": "LOW_MEDIUM",
        },
        "BTCUSD": {
            "flow_threshold_profile_v1": "BTC_TUNED",
            "aggregate_conviction_confirmed_floor_v1": 0.70,
            "aggregate_conviction_building_floor_v1": 0.50,
            "flow_persistence_confirmed_floor_v1": 0.68,
            "flow_persistence_building_floor_v1": 0.52,
            "min_persisting_bars_v1": 5,
            "exact_match_bonus_strength_v1": "LOW",
        },
    }


def _group_for_window(symbol: str, row: Mapping[str, Any]) -> str:
    stage = _text(row.get("stage_slot_v1")).upper()
    texture = _text(row.get("texture_slot_v1")).upper()
    ambiguity = _text(row.get("ambiguity_level_v1")).upper()
    status = _text(row.get("pilot_status_v1")).upper()

    if status == "ACTIVE_PILOT" and stage == "ACCEPTANCE" and ambiguity == "LOW" and texture in {"CLEAN", "WITH_FRICTION"}:
        return "CONFIRMED_POSITIVE"
    if status == "ACTIVE_PILOT":
        return "BUILDING_POSITIVE"
    if symbol == "BTCUSD" and ambiguity == "HIGH":
        return "UNCONFIRMED_MIXED"
    if status == "REVIEW_PENDING":
        return "UNCONFIRMED_MIXED"
    return "OPPOSED_FALSE"


def _retained_window_catalog_v1() -> list[dict[str, Any]]:
    catalogs = [
        build_xau_pilot_mapping_contract_v1().get("pilot_window_catalog_v1", []),
        build_nas_pilot_mapping_contract_v1().get("pilot_window_catalog_v1", []),
        build_btc_pilot_mapping_contract_v1().get("pilot_window_catalog_v1", []),
    ]
    rows: list[dict[str, Any]] = []
    for catalog in catalogs:
        for raw in list(catalog or []):
            row = dict(raw or {})
            symbol = _text(row.get("symbol_v1")).upper()
            row["retained_window_group_v1"] = _group_for_window(symbol, row)
            rows.append(row)
    return rows


def build_retained_window_flow_calibration_contract_v1() -> dict[str, Any]:
    threshold_profiles = _threshold_profiles_v1()
    return {
        "contract_version": RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Locks retained pilot windows into a common calibration set so later threshold bands are anchored to "
            "validated or review-worthy windows instead of ad hoc tuning."
        ),
        "retained_window_group_enum_v1": list(RETAINED_WINDOW_GROUP_ENUM_V1),
        "flow_threshold_profile_enum_v1": list(FLOW_THRESHOLD_PROFILE_ENUM_V1),
        "retained_window_calibration_state_enum_v1": list(RETAINED_WINDOW_CALIBRATION_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "retained_window_flow_calibration_profile_v1",
            "flow_threshold_profile_v1",
            "aggregate_conviction_confirmed_floor_v1",
            "aggregate_conviction_building_floor_v1",
            "flow_persistence_confirmed_floor_v1",
            "flow_persistence_building_floor_v1",
            "flow_min_persisting_bars_v1",
            "retained_window_calibration_state_v1",
            "retained_window_calibration_reason_summary_v1",
        ],
        "control_rules_v1": [
            "retained windows are grouped before exact bonus is weakened in later phases",
            "structure remains common while threshold bands can differ by symbol",
            "hard disqualifiers, rejection split, and dominance protection are not symbol-tunable",
            "review-pending windows can inform provisional building bands without becoming confirmed anchors",
            "execution and state25 remain unchanged in this phase",
        ],
        "symbol_specific_calibration_allowed_v1": [
            "aggregate conviction confirmed/building floors",
            "flow persistence confirmed/building floors",
            "minimum persisting bars",
            "exact match bonus strength",
        ],
        "symbol_specific_calibration_forbidden_v1": [
            "rejection split rules",
            "dominance ownership",
            "structure gate hard disqualifiers",
            "extension confirmed cap",
        ],
        "threshold_profiles_v1": threshold_profiles,
        "retained_window_catalog_v1": _retained_window_catalog_v1(),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _symbol_group_counts(catalog: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter] = {}
    for row in catalog:
        symbol = _text(row.get("symbol_v1")).upper()
        counts.setdefault(symbol, Counter()).update([_text(row.get("retained_window_group_v1")).upper()])
    return {symbol: dict(counter) for symbol, counter in counts.items()}


def _calibration_state(symbol: str, *, symbol_counts: Mapping[str, int]) -> str:
    confirmed = int(symbol_counts.get("CONFIRMED_POSITIVE", 0))
    building = int(symbol_counts.get("BUILDING_POSITIVE", 0))
    mixed = int(symbol_counts.get("UNCONFIRMED_MIXED", 0))
    if confirmed >= 1 and (building + mixed) >= 1:
        return "PROVISIONAL_BAND_READY"
    if (building + mixed) >= 2:
        return "PARTIAL_READY"
    if confirmed or building or mixed:
        return "REVIEW_PENDING"
    return "UNCONFIGURED"


def build_retained_window_flow_calibration_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(row)
    symbol = _text(payload.get("symbol")).upper()
    threshold_profiles = _threshold_profiles_v1()
    profile = dict(
        threshold_profiles.get(symbol)
        or {
            "flow_threshold_profile_v1": "COMMON",
            "aggregate_conviction_confirmed_floor_v1": 0.65,
            "aggregate_conviction_building_floor_v1": 0.45,
            "flow_persistence_confirmed_floor_v1": 0.60,
            "flow_persistence_building_floor_v1": 0.45,
            "min_persisting_bars_v1": 4,
            "exact_match_bonus_strength_v1": "LOW",
        }
    )
    catalog = _retained_window_catalog_v1()
    group_counts = _symbol_group_counts(catalog).get(symbol, {})
    state = _calibration_state(symbol, symbol_counts=group_counts)
    reason = (
        f"symbol={symbol or 'UNKNOWN'}; "
        f"profile={profile.get('flow_threshold_profile_v1', 'COMMON')}; "
        f"confirmed_windows={group_counts.get('CONFIRMED_POSITIVE', 0)}; "
        f"building_windows={group_counts.get('BUILDING_POSITIVE', 0)}; "
        f"mixed_windows={group_counts.get('UNCONFIRMED_MIXED', 0)}; "
        f"state={state}"
    )
    nested = {
        "contract_version": RETAINED_WINDOW_FLOW_CALIBRATION_CONTRACT_VERSION,
        "flow_threshold_profile_v1": profile["flow_threshold_profile_v1"],
        "aggregate_conviction_confirmed_floor_v1": profile["aggregate_conviction_confirmed_floor_v1"],
        "aggregate_conviction_building_floor_v1": profile["aggregate_conviction_building_floor_v1"],
        "flow_persistence_confirmed_floor_v1": profile["flow_persistence_confirmed_floor_v1"],
        "flow_persistence_building_floor_v1": profile["flow_persistence_building_floor_v1"],
        "flow_min_persisting_bars_v1": profile["min_persisting_bars_v1"],
        "exact_match_bonus_strength_v1": profile["exact_match_bonus_strength_v1"],
        "retained_window_group_counts_v1": dict(group_counts),
        "retained_window_calibration_state_v1": state,
        "retained_window_calibration_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "retained_window_flow_calibration_profile_v1": nested,
        "flow_threshold_profile_v1": nested["flow_threshold_profile_v1"],
        "aggregate_conviction_confirmed_floor_v1": nested["aggregate_conviction_confirmed_floor_v1"],
        "aggregate_conviction_building_floor_v1": nested["aggregate_conviction_building_floor_v1"],
        "flow_persistence_confirmed_floor_v1": nested["flow_persistence_confirmed_floor_v1"],
        "flow_persistence_building_floor_v1": nested["flow_persistence_building_floor_v1"],
        "flow_min_persisting_bars_v1": nested["flow_min_persisting_bars_v1"],
        "retained_window_calibration_state_v1": state,
        "retained_window_calibration_reason_summary_v1": reason,
    }


def attach_retained_window_flow_calibration_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = dict(_mapping(raw))
        row.update(build_retained_window_flow_calibration_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_retained_window_flow_calibration_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    contract = build_retained_window_flow_calibration_contract_v1()
    catalog = list(contract.get("retained_window_catalog_v1") or [])
    rows_by_symbol = attach_retained_window_flow_calibration_fields_v1(latest_signal_by_symbol)
    group_counts = Counter()
    profile_counts = Counter()
    state_counts = Counter()
    symbol_group_counts = _symbol_group_counts(catalog)

    for row in catalog:
        group_counts.update([_text(row.get("retained_window_group_v1")).upper()])

    for symbol in sorted({_text(item.get("symbol_v1")).upper() for item in catalog if _text(item.get("symbol_v1"))}):
        profile = contract["threshold_profiles_v1"].get(symbol, {}).get("flow_threshold_profile_v1", "COMMON")
        state = _calibration_state(symbol, symbol_counts=symbol_group_counts.get(symbol, {}))
        profile_counts.update([profile])
        state_counts.update([state])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if catalog else "HOLD",
        "status_reasons": (
            ["retained_window_calibration_catalog_available"] if catalog else ["no_retained_window_catalog"]
        ),
        "retained_window_count": len(catalog),
        "symbol_count": len(contract.get("threshold_profiles_v1", {})),
        "row_surface_count": len(rows_by_symbol),
        "retained_window_group_count_summary": dict(group_counts),
        "threshold_profile_count_summary": dict(profile_counts),
        "retained_window_calibration_state_count_summary": dict(state_counts),
        "symbol_group_count_summary_v1": symbol_group_counts,
        "threshold_profiles_v1": contract.get("threshold_profiles_v1", {}),
    }
    return {
        "contract_version": RETAINED_WINDOW_FLOW_CALIBRATION_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_retained_window_flow_calibration_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))

    lines = [
        "# Retained Window Flow Calibration",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- retained_window_count: {summary.get('retained_window_count', 0)}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Group Counts",
        f"- retained_window_group_count_summary: {json.dumps(summary.get('retained_window_group_count_summary', {}), ensure_ascii=False)}",
        f"- threshold_profile_count_summary: {json.dumps(summary.get('threshold_profile_count_summary', {}), ensure_ascii=False)}",
        f"- retained_window_calibration_state_count_summary: {json.dumps(summary.get('retained_window_calibration_state_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Threshold Profiles",
    ]
    for symbol, profile in dict(summary.get("threshold_profiles_v1", {})).items():
        lines.append(
            f"- {symbol}: profile={profile.get('flow_threshold_profile_v1', '')}, "
            f"conviction_confirmed={profile.get('aggregate_conviction_confirmed_floor_v1', 0.0)}, "
            f"conviction_building={profile.get('aggregate_conviction_building_floor_v1', 0.0)}, "
            f"persistence_confirmed={profile.get('flow_persistence_confirmed_floor_v1', 0.0)}, "
            f"persistence_building={profile.get('flow_persistence_building_floor_v1', 0.0)}, "
            f"min_bars={profile.get('min_persisting_bars_v1', 0)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_retained_window_flow_calibration_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_retained_window_flow_calibration_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "retained_window_flow_calibration_latest.json"
    markdown_path = output_dir / "retained_window_flow_calibration_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_retained_window_flow_calibration_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
