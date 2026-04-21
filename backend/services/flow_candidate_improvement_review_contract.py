from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.dominance_validation_profile import (
    DOMINANCE_VALIDATION_CONTRACT_VERSION,
    attach_dominance_validation_fields_v1,
)
from backend.services.flow_chain_shadow_comparison_contract import (
    FLOW_CHAIN_SHADOW_COMPARISON_CONTRACT_VERSION,
    attach_flow_chain_shadow_comparison_fields_v1,
)


FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION = "flow_candidate_improvement_review_contract_v1"
FLOW_CANDIDATE_IMPROVEMENT_REVIEW_SUMMARY_VERSION = "flow_candidate_improvement_review_summary_v1"

FLOW_CANDIDATE_TRUTH_STATE_ENUM_V1 = (
    "NO_CANDIDATE",
    "WIDEN_EXPECTED",
    "TIGHTEN_EXPECTED",
    "REVIEW_PENDING",
)
FLOW_CANDIDATE_REVIEW_ALIGNMENT_ENUM_V1 = (
    "ALIGNED",
    "MISSED",
    "REGRESSED",
    "NEUTRAL",
)
FLOW_CANDIDATE_IMPROVEMENT_VERDICT_ENUM_V1 = (
    "ALIGNED_IMPROVEMENT",
    "MISSED_IMPROVEMENT",
    "OVER_TIGHTENED",
    "ALIGNED_TIGHTENING",
    "MISSED_TIGHTENING",
    "OVER_WIDENED",
    "UNVERIFIED_WIDENING",
    "SAFE_TIGHTENING",
    "NEUTRAL_NO_CANDIDATE",
    "REVIEW_PENDING",
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
    return _text(value).lower() in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_flow_candidate_improvement_review_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Review layer that checks whether the new flow-enabled chain improves should-have-done style "
            "candidate handling, misses the expected widening, or tightens correctly against reversal-style truth."
        ),
        "upstream_contract_versions_v1": [
            FLOW_CHAIN_SHADOW_COMPARISON_CONTRACT_VERSION,
            DOMINANCE_VALIDATION_CONTRACT_VERSION,
        ],
        "flow_candidate_truth_state_enum_v1": list(FLOW_CANDIDATE_TRUTH_STATE_ENUM_V1),
        "flow_candidate_review_alignment_enum_v1": list(FLOW_CANDIDATE_REVIEW_ALIGNMENT_ENUM_V1),
        "flow_candidate_improvement_verdict_enum_v1": list(FLOW_CANDIDATE_IMPROVEMENT_VERDICT_ENUM_V1),
        "row_level_fields_v1": [
            "flow_candidate_improvement_review_profile_v1",
            "flow_candidate_truth_state_v1",
            "flow_candidate_shadow_delta_v1",
            "flow_candidate_review_alignment_v1",
            "flow_candidate_improvement_verdict_v1",
            "flow_candidate_review_priority_v1",
            "flow_candidate_improved_v1",
            "flow_candidate_review_reason_summary_v1",
        ],
        "control_rules_v1": [
            "candidate truth is anchored by dominance validation error typing and should-have-done candidate state",
            "widen-expected candidates are evaluated differently from tighten-expected candidates",
            "unchanged rows can still be counted as missed improvements when candidate truth expected widening",
            "no-candidate rows do not become improvements just because the new chain widens acceptance",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("flow_chain_shadow_delta_v1")):
        row = dict(attach_flow_chain_shadow_comparison_fields_v1({"_": row}).get("_", row))
    if not _text(row.get("dominance_error_type_v1")):
        row = dict(attach_dominance_validation_fields_v1({"_": row}).get("_", row))
    return row


def _state_rank(state: str) -> int:
    return {
        "FLOW_OPPOSED": 0,
        "FLOW_UNCONFIRMED": 1,
        "FLOW_BUILDING": 2,
        "FLOW_CONFIRMED": 3,
    }.get(_text(state).upper(), 1)


def _truth_state(row: Mapping[str, Any]) -> str:
    candidate = _bool(row.get("dominance_should_have_done_candidate_v1"))
    error_type = _text(row.get("dominance_error_type_v1")).upper()
    if not candidate:
        return "NO_CANDIDATE"
    if error_type in {
        "CONTINUATION_UNDERPROMOTED",
        "BOUNDARY_STAYED_TOO_LONG",
        "FRICTION_MISREAD_AS_REVERSAL",
        "REVERSAL_OVERCALLED",
    }:
        return "WIDEN_EXPECTED"
    if error_type == "TRUE_REVERSAL_MISSED":
        return "TIGHTEN_EXPECTED"
    return "REVIEW_PENDING"


def _review_priority(truth_state: str, delta: str) -> str:
    truth_state = _text(truth_state).upper()
    delta = _text(delta).upper()
    if truth_state in {"WIDEN_EXPECTED", "TIGHTEN_EXPECTED"}:
        return "HIGH"
    if truth_state == "REVIEW_PENDING" or delta == "FLOW_WIDENS_ACCEPTANCE":
        return "MEDIUM"
    return "LOW"


def _reason_summary(
    *,
    truth_state: str,
    error_type: str,
    old_state: str,
    new_state: str,
    delta: str,
    alignment: str,
    verdict: str,
    priority: str,
) -> str:
    return (
        f"truth={truth_state}; "
        f"error_type={error_type}; "
        f"old={old_state}; "
        f"new={new_state}; "
        f"delta={delta}; "
        f"alignment={alignment}; "
        f"verdict={verdict}; "
        f"priority={priority}"
    )


def _evaluate_candidate_review(
    *,
    truth_state: str,
    old_state: str,
    new_state: str,
    delta: str,
) -> tuple[str, str, bool]:
    truth_state = _text(truth_state).upper()
    old_state = _text(old_state).upper()
    new_state = _text(new_state).upper()
    delta = _text(delta).upper()
    old_rank = _state_rank(old_state)
    new_rank = _state_rank(new_state)

    if truth_state == "NO_CANDIDATE":
        if delta == "FLOW_WIDENS_ACCEPTANCE":
            return "NEUTRAL", "UNVERIFIED_WIDENING", False
        if delta in {"FLOW_TIGHTENS_ACCEPTANCE", "NEW_FLOW_OPPOSED"}:
            return "ALIGNED", "SAFE_TIGHTENING", False
        return "NEUTRAL", "NEUTRAL_NO_CANDIDATE", False

    if truth_state == "WIDEN_EXPECTED":
        if delta == "FLOW_WIDENS_ACCEPTANCE":
            return "ALIGNED", "ALIGNED_IMPROVEMENT", True
        if delta == "UNCHANGED":
            if new_rank >= 2 and new_rank >= old_rank:
                return "ALIGNED", "ALIGNED_IMPROVEMENT", True
            return "MISSED", "MISSED_IMPROVEMENT", False
        return "REGRESSED", "OVER_TIGHTENED", False

    if truth_state == "TIGHTEN_EXPECTED":
        if delta in {"FLOW_TIGHTENS_ACCEPTANCE", "NEW_FLOW_OPPOSED"}:
            return "ALIGNED", "ALIGNED_TIGHTENING", False
        if delta == "UNCHANGED":
            return "MISSED", "MISSED_TIGHTENING", False
        return "REGRESSED", "OVER_WIDENED", False

    return "NEUTRAL", "REVIEW_PENDING", False


def build_flow_candidate_improvement_review_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    truth_state = _truth_state(payload)
    old_state = _text(payload.get("old_exact_match_only_flow_state_v1")).upper()
    new_state = _text(payload.get("new_flow_enabled_state_v1")).upper()
    delta = _text(payload.get("flow_chain_shadow_delta_v1")).upper()
    error_type = _text(payload.get("dominance_error_type_v1")).upper() or "UNKNOWN"
    alignment, verdict, improved = _evaluate_candidate_review(
        truth_state=truth_state,
        old_state=old_state,
        new_state=new_state,
        delta=delta,
    )
    priority = _review_priority(truth_state, delta)
    reason = _reason_summary(
        truth_state=truth_state,
        error_type=error_type,
        old_state=old_state,
        new_state=new_state,
        delta=delta,
        alignment=alignment,
        verdict=verdict,
        priority=priority,
    )

    profile = {
        "contract_version": FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION,
        "flow_candidate_truth_state_v1": truth_state,
        "flow_candidate_shadow_delta_v1": delta,
        "flow_candidate_review_alignment_v1": alignment,
        "flow_candidate_improvement_verdict_v1": verdict,
        "flow_candidate_review_priority_v1": priority,
        "flow_candidate_improved_v1": improved,
        "flow_candidate_review_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "flow_candidate_improvement_review_profile_v1": profile,
        "flow_candidate_truth_state_v1": truth_state,
        "flow_candidate_shadow_delta_v1": delta,
        "flow_candidate_review_alignment_v1": alignment,
        "flow_candidate_improvement_verdict_v1": verdict,
        "flow_candidate_review_priority_v1": priority,
        "flow_candidate_improved_v1": improved,
        "flow_candidate_review_reason_summary_v1": reason,
    }


def attach_flow_candidate_improvement_review_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_flow_candidate_improvement_review_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_flow_candidate_improvement_review_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_flow_candidate_improvement_review_fields_v1(latest_signal_by_symbol)
    truth_counts = Counter()
    verdict_counts = Counter()
    alignment_counts = Counter()
    candidate_count = 0
    improved_count = 0
    missed_count = 0
    regression_count = 0
    unverified_widening_count = 0
    symbol_count = len(rows_by_symbol)

    for row in rows_by_symbol.values():
        truth = _text(row.get("flow_candidate_truth_state_v1"))
        verdict = _text(row.get("flow_candidate_improvement_verdict_v1"))
        alignment = _text(row.get("flow_candidate_review_alignment_v1"))
        truth_counts.update([truth])
        verdict_counts.update([verdict])
        alignment_counts.update([alignment])
        if truth in {"WIDEN_EXPECTED", "TIGHTEN_EXPECTED", "REVIEW_PENDING"}:
            candidate_count += 1
        if _bool(row.get("flow_candidate_improved_v1")):
            improved_count += 1
        if verdict in {"MISSED_IMPROVEMENT", "MISSED_TIGHTENING"}:
            missed_count += 1
        if verdict in {"OVER_TIGHTENED", "OVER_WIDENED"}:
            regression_count += 1
        if verdict == "UNVERIFIED_WIDENING":
            unverified_widening_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["flow_candidate_improvement_review_surface_available"]
            if symbol_count
            else ["no_rows_for_flow_candidate_improvement_review"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "flow_candidate_truth_state_count_summary": dict(truth_counts),
        "flow_candidate_improvement_verdict_count_summary": dict(verdict_counts),
        "flow_candidate_review_alignment_count_summary": dict(alignment_counts),
        "candidate_count": int(candidate_count),
        "candidate_improved_count": int(improved_count),
        "candidate_missed_count": int(missed_count),
        "candidate_regression_count": int(regression_count),
        "unverified_widening_count": int(unverified_widening_count),
    }
    return {
        "contract_version": FLOW_CANDIDATE_IMPROVEMENT_REVIEW_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_flow_candidate_improvement_review_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# Flow Candidate Improvement Review",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- flow_candidate_truth_state_count_summary: {json.dumps(summary.get('flow_candidate_truth_state_count_summary', {}), ensure_ascii=False)}",
        f"- flow_candidate_improvement_verdict_count_summary: {json.dumps(summary.get('flow_candidate_improvement_verdict_count_summary', {}), ensure_ascii=False)}",
        f"- flow_candidate_review_alignment_count_summary: {json.dumps(summary.get('flow_candidate_review_alignment_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: truth={row.get('flow_candidate_truth_state_v1', '')}, "
            f"delta={row.get('flow_candidate_shadow_delta_v1', '')}, "
            f"verdict={row.get('flow_candidate_improvement_verdict_v1', '')}, "
            f"priority={row.get('flow_candidate_review_priority_v1', '')}, "
            f"improved={row.get('flow_candidate_improved_v1', False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_flow_candidate_improvement_review_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_flow_candidate_improvement_review_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "flow_candidate_improvement_review_latest.json"
    markdown_path = output_dir / "flow_candidate_improvement_review_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_flow_candidate_improvement_review_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
