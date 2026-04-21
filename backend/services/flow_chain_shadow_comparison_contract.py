from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.flow_support_state_contract import (
    FLOW_SUPPORT_STATE_CONTRACT_VERSION,
    attach_flow_support_state_fields_v1,
)


FLOW_CHAIN_SHADOW_COMPARISON_CONTRACT_VERSION = "flow_chain_shadow_comparison_contract_v1"
FLOW_CHAIN_SHADOW_COMPARISON_SUMMARY_VERSION = "flow_chain_shadow_comparison_summary_v1"

FLOW_CHAIN_SHADOW_DELTA_ENUM_V1 = (
    "UNCHANGED",
    "FLOW_WIDENS_ACCEPTANCE",
    "FLOW_TIGHTENS_ACCEPTANCE",
    "NEW_FLOW_OPPOSED",
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
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    return text in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_flow_chain_shadow_comparison_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_CHAIN_SHADOW_COMPARISON_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Shadow comparison between old exact-match-only acceptance and the new flow-enabled chain. "
            "Makes the delta visible without changing execution or state25."
        ),
        "upstream_contract_versions_v1": [
            FLOW_SUPPORT_STATE_CONTRACT_VERSION,
        ],
        "flow_chain_shadow_delta_enum_v1": list(FLOW_CHAIN_SHADOW_DELTA_ENUM_V1),
        "row_level_fields_v1": [
            "flow_chain_shadow_comparison_profile_v1",
            "old_exact_match_only_flow_state_v1",
            "old_exact_match_only_source_v1",
            "new_flow_enabled_state_v1",
            "new_flow_enabled_authority_v1",
            "flow_chain_shadow_delta_v1",
            "flow_chain_shadow_should_have_done_candidate_v1",
            "flow_chain_shadow_candidate_improved_v1",
            "flow_chain_shadow_reason_summary_v1",
        ],
        "control_rules_v1": [
            "old exact-only verdict is a reconstructed baseline, not a live authority",
            "new flow-enabled verdict comes from F6 and is not modified here",
            "new flow opposed is treated separately from a simple tightening",
            "should-have-done candidate improvement is reported, not executed",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("flow_support_state_v1")):
        row = dict(attach_flow_support_state_fields_v1({"_": row}).get("_", row))
    return row


def _old_exact_source(row: Mapping[str, Any]) -> str:
    source = _text(row.get("exact_pilot_match_bonus_source_v1")).upper()
    if source:
        return source
    status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    if status == "ACTIVE_CANDIDATE" and match == "MATCH":
        return "FALLBACK_MATCH"
    if status == "ACTIVE_CANDIDATE" and match == "PARTIAL_MATCH":
        return "FALLBACK_PARTIAL"
    if match == "SEPARATE_PENDING" or status == "SEPARATE_PENDING":
        return "REVIEW_PENDING"
    if match in {"OUT_OF_PROFILE", "UNCONFIGURED"}:
        return "OUT_OF_PROFILE"
    return "NOT_APPLICABLE"


def _old_exact_state(source: str) -> str:
    source = _text(source).upper()
    if source in {"MATCHED_ACTIVE_PROFILE", "FALLBACK_MATCH"}:
        return "FLOW_CONFIRMED"
    if source in {"PARTIAL_ACTIVE_PROFILE", "FALLBACK_PARTIAL"}:
        return "FLOW_BUILDING"
    return "FLOW_UNCONFIRMED"


def _state_rank(state: str) -> int:
    return {
        "FLOW_OPPOSED": 0,
        "FLOW_UNCONFIRMED": 1,
        "FLOW_BUILDING": 2,
        "FLOW_CONFIRMED": 3,
    }.get(_text(state).upper(), 1)


def _delta(old_state: str, new_state: str) -> str:
    old_state = _text(old_state).upper()
    new_state = _text(new_state).upper()
    if old_state == new_state:
        return "UNCHANGED"
    if new_state == "FLOW_OPPOSED" and old_state != "FLOW_OPPOSED":
        return "NEW_FLOW_OPPOSED"
    if _state_rank(new_state) > _state_rank(old_state):
        return "FLOW_WIDENS_ACCEPTANCE"
    return "FLOW_TIGHTENS_ACCEPTANCE"


def _reason_summary(
    *,
    old_source: str,
    old_state: str,
    new_state: str,
    new_authority: str,
    delta: str,
    candidate: bool,
    improved: bool,
) -> str:
    return (
        f"old_source={old_source}; "
        f"old={old_state}; "
        f"new={new_state}; "
        f"authority={new_authority}; "
        f"delta={delta}; "
        f"candidate={str(candidate).lower()}; "
        f"improved={str(improved).lower()}"
    )


def build_flow_chain_shadow_comparison_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    old_source = _old_exact_source(payload)
    old_state = _old_exact_state(old_source)
    new_state = _text(payload.get("flow_support_state_v1")).upper() or "FLOW_UNCONFIRMED"
    new_authority = _text(payload.get("flow_support_state_authority_v1")).upper()
    delta = _delta(old_state, new_state)
    candidate = _bool(payload.get("dominance_should_have_done_candidate_v1"))
    improved = candidate and delta == "FLOW_WIDENS_ACCEPTANCE"
    reason = _reason_summary(
        old_source=old_source,
        old_state=old_state,
        new_state=new_state,
        new_authority=new_authority,
        delta=delta,
        candidate=candidate,
        improved=improved,
    )

    profile = {
        "contract_version": FLOW_CHAIN_SHADOW_COMPARISON_CONTRACT_VERSION,
        "old_exact_match_only_flow_state_v1": old_state,
        "old_exact_match_only_source_v1": old_source,
        "new_flow_enabled_state_v1": new_state,
        "new_flow_enabled_authority_v1": new_authority,
        "flow_chain_shadow_delta_v1": delta,
        "flow_chain_shadow_should_have_done_candidate_v1": candidate,
        "flow_chain_shadow_candidate_improved_v1": improved,
        "flow_chain_shadow_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "flow_chain_shadow_comparison_profile_v1": profile,
        "old_exact_match_only_flow_state_v1": old_state,
        "old_exact_match_only_source_v1": old_source,
        "new_flow_enabled_state_v1": new_state,
        "new_flow_enabled_authority_v1": new_authority,
        "flow_chain_shadow_delta_v1": delta,
        "flow_chain_shadow_should_have_done_candidate_v1": candidate,
        "flow_chain_shadow_candidate_improved_v1": improved,
        "flow_chain_shadow_reason_summary_v1": reason,
    }


def attach_flow_chain_shadow_comparison_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_flow_chain_shadow_comparison_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_flow_chain_shadow_comparison_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_chain_shadow_comparison_fields_v1(latest_signal_by_symbol)
    old_counts = Counter()
    new_counts = Counter()
    delta_counts = Counter()
    improved_count = 0
    symbol_count = len(rows_by_symbol)

    for row in rows_by_symbol.values():
        old_counts.update([_text(row.get("old_exact_match_only_flow_state_v1"))])
        new_counts.update([_text(row.get("new_flow_enabled_state_v1"))])
        delta_counts.update([_text(row.get("flow_chain_shadow_delta_v1"))])
        if _bool(row.get("flow_chain_shadow_candidate_improved_v1")):
            improved_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["flow_chain_shadow_comparison_surface_available"] if symbol_count else ["no_rows_for_flow_chain_shadow_comparison"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "old_exact_match_only_flow_state_count_summary": dict(old_counts),
        "new_flow_enabled_state_count_summary": dict(new_counts),
        "flow_chain_shadow_delta_count_summary": dict(delta_counts),
        "flow_chain_shadow_candidate_improved_count": int(improved_count),
    }
    return {
        "contract_version": FLOW_CHAIN_SHADOW_COMPARISON_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_chain_shadow_comparison_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Flow Chain Shadow Comparison",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- old_exact_match_only_flow_state_count_summary: {json.dumps(summary.get('old_exact_match_only_flow_state_count_summary', {}), ensure_ascii=False)}",
        f"- new_flow_enabled_state_count_summary: {json.dumps(summary.get('new_flow_enabled_state_count_summary', {}), ensure_ascii=False)}",
        f"- flow_chain_shadow_delta_count_summary: {json.dumps(summary.get('flow_chain_shadow_delta_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: old={row.get('old_exact_match_only_flow_state_v1', '')}, "
            f"new={row.get('new_flow_enabled_state_v1', '')}, "
            f"delta={row.get('flow_chain_shadow_delta_v1', '')}, "
            f"candidate_improved={row.get('flow_chain_shadow_candidate_improved_v1', False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_chain_shadow_comparison_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_flow_chain_shadow_comparison_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "flow_chain_shadow_comparison_latest.json"
    markdown_path = output_dir / "flow_chain_shadow_comparison_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_flow_chain_shadow_comparison_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
