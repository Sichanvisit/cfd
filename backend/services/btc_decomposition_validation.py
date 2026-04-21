from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.btc_readonly_surface_contract import attach_btc_readonly_surface_fields_v1
from backend.services.dominance_accuracy_shadow import attach_dominance_accuracy_shadow_fields_v1
from backend.services.dominance_validation_profile import attach_dominance_validation_fields_v1


BTC_DECOMPOSITION_VALIDATION_CONTRACT_VERSION = "btc_decomposition_validation_contract_v1"
BTC_DECOMPOSITION_VALIDATION_SUMMARY_VERSION = "btc_decomposition_validation_summary_v1"

BTC_SLOT_ALIGNMENT_ENUM_V1 = (
    "ALIGNED",
    "DOMINANCE_MISMATCH",
    "BOUNDARY_OVERRUN",
    "REVIEW_PENDING",
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


def _bool(value: Any) -> bool:
    return bool(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_btc_decomposition_validation_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BTC_DECOMPOSITION_VALIDATION_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "BTC-specific decomposition validation layer. Joins BTC read-only surface with dominance validation "
            "and shadow accuracy metrics without changing execution or state25."
        ),
        "btc_slot_alignment_enum_v1": list(BTC_SLOT_ALIGNMENT_ENUM_V1),
        "row_level_fields_v1": [
            "btc_decomposition_validation_profile_v1",
            "btc_slot_alignment_state_v1",
            "btc_should_have_done_candidate_v1",
            "btc_over_veto_flag_v1",
            "btc_under_veto_flag_v1",
            "btc_decomposition_error_type_v1",
            "btc_dominance_validation_reason_summary_v1",
        ],
        "control_rules_v1": [
            "validation remains btc-specific and read-only in this phase",
            "btc slot alignment does not change dominant_side",
            "over-veto and under-veto remain diagnostics rather than execution actions",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not isinstance(row.get("btc_readonly_surface_profile_v1"), Mapping):
        symbol = _text(row.get("symbol") or row.get("ticker") or "_")
        row = dict(attach_btc_readonly_surface_fields_v1({symbol: row}).get(symbol, row))
    if not isinstance(row.get("dominance_validation_profile_v1"), Mapping):
        symbol = _text(row.get("symbol") or row.get("ticker") or "_")
        row = dict(attach_dominance_validation_fields_v1({symbol: row}).get(symbol, row))
    if not isinstance(row.get("dominance_accuracy_shadow_profile_v1"), Mapping):
        symbol = _text(row.get("symbol") or row.get("ticker") or "_")
        row = dict(attach_dominance_accuracy_shadow_fields_v1({symbol: row}).get(symbol, row))
    return row


def _alignment_state(row: Mapping[str, Any]) -> str:
    if _text(row.get("symbol")).upper() != "BTCUSD":
        return "NOT_APPLICABLE"
    pilot_match = _text(row.get("btc_pilot_window_match_v1")).upper()
    error_type = _text(row.get("dominance_error_type_v1")).upper()
    alignment = _text(row.get("dominance_vs_canonical_alignment_v1")).upper()
    if pilot_match == "REVIEW_PENDING":
        return "REVIEW_PENDING"
    if error_type == "BOUNDARY_STAYED_TOO_LONG":
        return "BOUNDARY_OVERRUN"
    if error_type == "ALIGNED" and alignment == "MATCH":
        return "ALIGNED"
    return "DOMINANCE_MISMATCH"


def build_btc_decomposition_validation_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    if _text(payload.get("symbol")).upper() != "BTCUSD":
        profile = {
            "contract_version": BTC_DECOMPOSITION_VALIDATION_CONTRACT_VERSION,
            "applicable_v1": False,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "btc_decomposition_validation_profile_v1": profile,
            "btc_slot_alignment_state_v1": "NOT_APPLICABLE",
            "btc_should_have_done_candidate_v1": False,
            "btc_over_veto_flag_v1": False,
            "btc_under_veto_flag_v1": False,
            "btc_decomposition_error_type_v1": "",
            "btc_dominance_validation_reason_summary_v1": "symbol_not_btc",
        }

    alignment_state = _alignment_state(payload)
    should_have_done_candidate = _bool(payload.get("dominance_should_have_done_candidate_v1"))
    over_veto = _bool(payload.get("dominance_over_veto_flag_v1"))
    under_veto = _bool(payload.get("dominance_under_veto_flag_v1"))
    error_type = _text(payload.get("dominance_error_type_v1")).upper()
    reason_summary = (
        f"slot={_text(payload.get('btc_state_slot_core_v1'))}; alignment={alignment_state}; "
        f"error={error_type or 'ALIGNED'}; candidate={str(should_have_done_candidate).lower()}; "
        f"friction={_text(payload.get('dominance_friction_separation_state_v1'))}"
    )
    profile = {
        "contract_version": BTC_DECOMPOSITION_VALIDATION_CONTRACT_VERSION,
        "applicable_v1": True,
        "btc_slot_alignment_state_v1": alignment_state,
        "btc_should_have_done_candidate_v1": bool(should_have_done_candidate),
        "btc_over_veto_flag_v1": bool(over_veto),
        "btc_under_veto_flag_v1": bool(under_veto),
        "btc_decomposition_error_type_v1": error_type,
        "slot_core_v1": _text(payload.get("btc_state_slot_core_v1")),
        "pilot_window_match_v1": _text(payload.get("btc_pilot_window_match_v1")),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "btc_decomposition_validation_profile_v1": profile,
        "btc_slot_alignment_state_v1": alignment_state,
        "btc_should_have_done_candidate_v1": bool(should_have_done_candidate),
        "btc_over_veto_flag_v1": bool(over_veto),
        "btc_under_veto_flag_v1": bool(under_veto),
        "btc_decomposition_error_type_v1": error_type,
        "btc_dominance_validation_reason_summary_v1": reason_summary,
    }


def attach_btc_decomposition_validation_fields_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_btc_decomposition_validation_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_btc_decomposition_validation_summary_v1(latest_signal_by_symbol: Mapping[str, Any] | None) -> dict[str, Any]:
    rows_by_symbol = attach_btc_decomposition_validation_fields_v1(latest_signal_by_symbol)
    btc_rows = {symbol: row for symbol, row in rows_by_symbol.items() if _text(row.get("symbol")).upper() == "BTCUSD"}
    alignment_counts = Counter()
    error_counts = Counter()
    match_counts = Counter()
    should_count = 0
    over_veto = 0
    under_veto = 0
    for row in btc_rows.values():
        alignment_counts.update([_text(row.get("btc_slot_alignment_state_v1"))])
        error_counts.update([_text(row.get("btc_decomposition_error_type_v1"))])
        match_counts.update([_text(row.get("btc_pilot_window_match_v1"))])
        if _bool(row.get("btc_should_have_done_candidate_v1")):
            should_count += 1
        if _bool(row.get("btc_over_veto_flag_v1")):
            over_veto += 1
        if _bool(row.get("btc_under_veto_flag_v1")):
            under_veto += 1
    btc_count = len(btc_rows)
    aligned_count = int(alignment_counts.get("ALIGNED", 0))
    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if btc_count else "HOLD",
        "status_reasons": (
            ["btc_decomposition_validation_available"] if btc_count else ["btc_row_missing_for_validation"]
        ),
        "btc_row_count": int(btc_count),
        "slot_alignment_rate": round(aligned_count / btc_count, 4) if btc_count else None,
        "should_have_done_candidate_count": int(should_count),
        "over_veto_rate": round(over_veto / btc_count, 4) if btc_count else None,
        "under_veto_rate": round(under_veto / btc_count, 4) if btc_count else None,
        "slot_alignment_state_count_summary": dict(alignment_counts),
        "pilot_window_match_count_summary": dict(match_counts),
        "dominance_error_type_count_summary": dict(error_counts),
    }
    return {
        "contract_version": BTC_DECOMPOSITION_VALIDATION_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_btc_decomposition_validation_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# BTC Decomposition Validation v1",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- btc_row_count: `{int(summary.get('btc_row_count', 0) or 0)}`",
        f"- slot_alignment_rate: `{summary.get('slot_alignment_rate')}`",
        "",
        "## BTC Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        if _text(row.get("symbol")).upper() != "BTCUSD":
            continue
        lines.append(
            f"- `{symbol}`: alignment={row.get('btc_slot_alignment_state_v1', '')} | "
            f"error={row.get('btc_decomposition_error_type_v1', '')} | "
            f"candidate={row.get('btc_should_have_done_candidate_v1', False)} | "
            f"slot={row.get('btc_state_slot_core_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_btc_decomposition_validation_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_btc_decomposition_validation_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "btc_decomposition_validation_latest.json"
    md_path = output_dir / "btc_decomposition_validation_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_btc_decomposition_validation_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {"json_path": str(json_path), "markdown_path": str(md_path)},
    }
