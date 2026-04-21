from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.flow_candidate_improvement_review_contract import (
    FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION,
    attach_flow_candidate_improvement_review_fields_v1,
)


NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_CONTRACT_VERSION = "nas_btc_hard_opposed_truth_audit_contract_v1"
NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_SUMMARY_VERSION = "nas_btc_hard_opposed_truth_audit_summary_v1"

AUDIT_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "NON_OPPOSED",
    "FIXED_HARD_OPPOSED",
    "TUNABLE_OVER_TIGHTEN_RISK",
    "MIXED_REVIEW",
    "REVIEW_PENDING",
)
ALIGNMENT_ENUM_V1 = (
    "NOT_APPLICABLE",
    "ALIGNED",
    "OVER_TIGHTEN_RISK",
    "REVIEW_PENDING",
)
LEARNING_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "FIXED_BLOCKED",
    "LEARNING_CANDIDATE",
    "MIXED_REVIEW",
    "REVIEW_PENDING",
)

FIXED_HARD_BLOCKERS_V1 = {
    "POLARITY_MISMATCH",
    "REVERSAL_REJECTION",
    "REVERSAL_OVERRIDE",
}


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


def build_nas_btc_hard_opposed_truth_audit_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Audits whether NAS/BTC hard-opposed outcomes are driven by immutable blockers or by tunable control "
            "scores that should stay learnable. Separates fixed blockers from learning-ready drivers."
        ),
        "upstream_contract_versions_v1": [
            FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION,
        ],
        "audit_state_enum_v1": list(AUDIT_STATE_ENUM_V1),
        "alignment_enum_v1": list(ALIGNMENT_ENUM_V1),
        "learning_state_enum_v1": list(LEARNING_STATE_ENUM_V1),
        "fixed_hard_blockers_v1": sorted(FIXED_HARD_BLOCKERS_V1),
        "row_level_fields_v1": [
            "nas_btc_hard_opposed_truth_audit_profile_v1",
            "nas_btc_hard_opposed_truth_audit_state_v1",
            "nas_btc_hard_opposed_truth_alignment_v1",
            "nas_btc_hard_opposed_fixed_blockers_v1",
            "nas_btc_hard_opposed_tunable_drivers_v1",
            "nas_btc_hard_opposed_control_score_snapshot_v1",
            "nas_btc_hard_opposed_learning_state_v1",
            "nas_btc_hard_opposed_learning_keys_v1",
            "nas_btc_hard_opposed_reason_summary_v1",
        ],
        "control_rules_v1": [
            "polarity mismatch, reversal rejection, and reversal override stay immutable and are not learnable",
            "ambiguity thresholds, soft support thresholds, conviction bands, persistence bands, and recency weighting remain tunable",
            "this phase audits learnable controls only and does not change live thresholds",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_upstream(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if not _text(row.get("flow_candidate_improvement_verdict_v1")):
        row = dict(attach_flow_candidate_improvement_review_fields_v1({"_": row}).get("_", row))
    return row


def _hard_disqualifiers(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("flow_structure_gate_hard_disqualifiers_v1")
    if isinstance(raw, list):
        return [_text(item).upper() for item in raw if _text(item)]
    return []


def _fixed_blockers(hard: list[str]) -> list[str]:
    return [item for item in hard if item in FIXED_HARD_BLOCKERS_V1]


def _tunable_drivers(row: Mapping[str, Any], hard: list[str]) -> list[str]:
    drivers: list[str] = []
    if "AMBIGUITY_HIGH" in hard:
        drivers.append("AMBIGUITY_THRESHOLD")
    soft_score = _float(row.get("flow_structure_gate_soft_score_v1"), 0.0)
    conviction = _float(row.get("aggregate_conviction_v1"), 0.0)
    persistence = _float(row.get("flow_persistence_v1"), 0.0)
    conviction_floor = _float(row.get("aggregate_conviction_building_floor_v1"), 0.0)
    persistence_floor = _float(row.get("flow_persistence_building_floor_v1"), 0.0)
    ambiguity_penalty = _float(row.get("aggregate_ambiguity_penalty_v1"), 0.0)
    veto_penalty = _float(row.get("aggregate_veto_penalty_v1"), 0.0)
    recency_weight = _float(row.get("flow_persistence_recency_weight_v1"), 0.0)

    if 0.0 < soft_score < 3.0:
        drivers.append("STRUCTURE_SOFT_SCORE_FLOOR")
    if conviction_floor > 0.0 and conviction < conviction_floor:
        drivers.append("CONVICTION_BUILDING_FLOOR")
    if persistence_floor > 0.0 and persistence < persistence_floor:
        drivers.append("PERSISTENCE_BUILDING_FLOOR")
    if ambiguity_penalty > 0.0:
        drivers.append("AMBIGUITY_PENALTY_SCALE")
    if veto_penalty > 0.0:
        drivers.append("VETO_PENALTY_SCALE")
    if recency_weight > 0.0 and recency_weight < 0.7:
        drivers.append("RECENCY_WEIGHT_SCALE")
    deduped: list[str] = []
    for item in drivers:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _control_score_snapshot(row: Mapping[str, Any]) -> dict[str, float]:
    return {
        "flow_structure_gate_soft_score_v1": round(_float(row.get("flow_structure_gate_soft_score_v1"), 0.0), 4),
        "aggregate_conviction_v1": round(_float(row.get("aggregate_conviction_v1"), 0.0), 4),
        "flow_persistence_v1": round(_float(row.get("flow_persistence_v1"), 0.0), 4),
        "aggregate_ambiguity_penalty_v1": round(_float(row.get("aggregate_ambiguity_penalty_v1"), 0.0), 4),
        "aggregate_veto_penalty_v1": round(_float(row.get("aggregate_veto_penalty_v1"), 0.0), 4),
        "flow_persistence_recency_weight_v1": round(_float(row.get("flow_persistence_recency_weight_v1"), 0.0), 4),
        "aggregate_conviction_building_floor_v1": round(
            _float(row.get("aggregate_conviction_building_floor_v1"), 0.0), 4
        ),
        "flow_persistence_building_floor_v1": round(
            _float(row.get("flow_persistence_building_floor_v1"), 0.0), 4
        ),
    }


def _learning_keys(tunable_drivers: list[str]) -> list[str]:
    mapping = {
        "AMBIGUITY_THRESHOLD": "flow.ambiguity_threshold",
        "STRUCTURE_SOFT_SCORE_FLOOR": "flow.structure_soft_score_floor",
        "CONVICTION_BUILDING_FLOOR": "flow.conviction_building_floor",
        "PERSISTENCE_BUILDING_FLOOR": "flow.persistence_building_floor",
        "AMBIGUITY_PENALTY_SCALE": "flow.ambiguity_penalty_scale",
        "VETO_PENALTY_SCALE": "flow.veto_penalty_scale",
        "RECENCY_WEIGHT_SCALE": "flow.persistence_recency_weight_scale",
    }
    return [mapping[item] for item in tunable_drivers if item in mapping]


def _reason_summary(
    *,
    symbol: str,
    audit_state: str,
    alignment: str,
    learning_state: str,
    fixed_blockers: list[str],
    tunable_drivers: list[str],
    verdict: str,
) -> str:
    return (
        f"symbol={symbol}; "
        f"audit_state={audit_state}; "
        f"alignment={alignment}; "
        f"learning_state={learning_state}; "
        f"verdict={verdict}; "
        f"fixed={','.join(fixed_blockers) or 'none'}; "
        f"tunable={','.join(tunable_drivers) or 'none'}"
    )


def build_nas_btc_hard_opposed_truth_audit_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _ensure_upstream(row or {})
    symbol = _text(payload.get("symbol")).upper()
    new_state = _text(payload.get("new_flow_enabled_state_v1") or payload.get("flow_support_state_v1")).upper()
    verdict = _text(payload.get("flow_candidate_improvement_verdict_v1")).upper()
    hard = _hard_disqualifiers(payload)
    fixed = _fixed_blockers(hard)
    tunable = _tunable_drivers(payload, hard)
    score_snapshot = _control_score_snapshot(payload)
    learning_keys = _learning_keys(tunable)

    if symbol not in {"NAS100", "BTCUSD"}:
        audit_state = "NOT_APPLICABLE"
        alignment = "NOT_APPLICABLE"
        learning_state = "NOT_APPLICABLE"
    elif new_state != "FLOW_OPPOSED":
        audit_state = "NON_OPPOSED"
        alignment = "NOT_APPLICABLE"
        learning_state = "NOT_APPLICABLE"
    elif verdict == "REVIEW_PENDING":
        audit_state = "REVIEW_PENDING"
        alignment = "REVIEW_PENDING"
        learning_state = "REVIEW_PENDING"
    elif verdict == "OVER_TIGHTENED":
        alignment = "OVER_TIGHTEN_RISK"
        if fixed and tunable:
            audit_state = "MIXED_REVIEW"
            learning_state = "MIXED_REVIEW"
        elif fixed:
            audit_state = "FIXED_HARD_OPPOSED"
            learning_state = "FIXED_BLOCKED"
        else:
            audit_state = "TUNABLE_OVER_TIGHTEN_RISK"
            learning_state = "LEARNING_CANDIDATE"
    else:
        alignment = "ALIGNED"
        if fixed:
            audit_state = "FIXED_HARD_OPPOSED"
            learning_state = "FIXED_BLOCKED"
        elif tunable:
            audit_state = "MIXED_REVIEW"
            learning_state = "LEARNING_CANDIDATE"
        else:
            audit_state = "FIXED_HARD_OPPOSED"
            learning_state = "FIXED_BLOCKED"

    reason = _reason_summary(
        symbol=symbol or "UNKNOWN",
        audit_state=audit_state,
        alignment=alignment,
        learning_state=learning_state,
        fixed_blockers=fixed,
        tunable_drivers=tunable,
        verdict=verdict or "UNKNOWN",
    )

    profile = {
        "contract_version": NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_CONTRACT_VERSION,
        "nas_btc_hard_opposed_truth_audit_state_v1": audit_state,
        "nas_btc_hard_opposed_truth_alignment_v1": alignment,
        "nas_btc_hard_opposed_fixed_blockers_v1": list(fixed),
        "nas_btc_hard_opposed_tunable_drivers_v1": list(tunable),
        "nas_btc_hard_opposed_control_score_snapshot_v1": dict(score_snapshot),
        "nas_btc_hard_opposed_learning_state_v1": learning_state,
        "nas_btc_hard_opposed_learning_keys_v1": list(learning_keys),
        "nas_btc_hard_opposed_reason_summary_v1": reason,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "nas_btc_hard_opposed_truth_audit_profile_v1": profile,
        "nas_btc_hard_opposed_truth_audit_state_v1": audit_state,
        "nas_btc_hard_opposed_truth_alignment_v1": alignment,
        "nas_btc_hard_opposed_fixed_blockers_v1": list(fixed),
        "nas_btc_hard_opposed_tunable_drivers_v1": list(tunable),
        "nas_btc_hard_opposed_control_score_snapshot_v1": dict(score_snapshot),
        "nas_btc_hard_opposed_learning_state_v1": learning_state,
        "nas_btc_hard_opposed_learning_keys_v1": list(learning_keys),
        "nas_btc_hard_opposed_reason_summary_v1": reason,
    }


def attach_nas_btc_hard_opposed_truth_audit_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_upstream(raw)
        row.update(build_nas_btc_hard_opposed_truth_audit_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_nas_btc_hard_opposed_truth_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_nas_btc_hard_opposed_truth_audit_fields_v1(latest_signal_by_symbol)
    audit_counts = Counter()
    alignment_counts = Counter()
    learning_counts = Counter()
    fixed_counts = Counter()
    tunable_counts = Counter()
    symbol_count = len(rows_by_symbol)
    learning_candidate_count = 0
    mixed_review_count = 0

    for row in rows_by_symbol.values():
        audit_counts.update([_text(row.get("nas_btc_hard_opposed_truth_audit_state_v1"))])
        alignment_counts.update([_text(row.get("nas_btc_hard_opposed_truth_alignment_v1"))])
        learning_counts.update([_text(row.get("nas_btc_hard_opposed_learning_state_v1"))])
        for item in list(row.get("nas_btc_hard_opposed_fixed_blockers_v1") or []):
            fixed_counts.update([_text(item)])
        for item in list(row.get("nas_btc_hard_opposed_tunable_drivers_v1") or []):
            tunable_counts.update([_text(item)])
        if _text(row.get("nas_btc_hard_opposed_learning_state_v1")) == "LEARNING_CANDIDATE":
            learning_candidate_count += 1
        if _text(row.get("nas_btc_hard_opposed_truth_audit_state_v1")) == "MIXED_REVIEW":
            mixed_review_count += 1

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["nas_btc_hard_opposed_truth_audit_surface_available"]
            if symbol_count
            else ["no_rows_for_nas_btc_hard_opposed_truth_audit"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "nas_btc_hard_opposed_truth_audit_state_count_summary": dict(audit_counts),
        "nas_btc_hard_opposed_truth_alignment_count_summary": dict(alignment_counts),
        "nas_btc_hard_opposed_learning_state_count_summary": dict(learning_counts),
        "nas_btc_hard_opposed_fixed_blocker_count_summary": dict(fixed_counts),
        "nas_btc_hard_opposed_tunable_driver_count_summary": dict(tunable_counts),
        "learning_candidate_count": int(learning_candidate_count),
        "mixed_review_count": int(mixed_review_count),
    }
    return {
        "contract_version": NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_nas_btc_hard_opposed_truth_audit_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    lines = [
        "# NAS/BTC Hard Opposed Truth Audit",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- nas_btc_hard_opposed_truth_audit_state_count_summary: {json.dumps(summary.get('nas_btc_hard_opposed_truth_audit_state_count_summary', {}), ensure_ascii=False)}",
        f"- nas_btc_hard_opposed_truth_alignment_count_summary: {json.dumps(summary.get('nas_btc_hard_opposed_truth_alignment_count_summary', {}), ensure_ascii=False)}",
        f"- nas_btc_hard_opposed_learning_state_count_summary: {json.dumps(summary.get('nas_btc_hard_opposed_learning_state_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: state={row.get('nas_btc_hard_opposed_truth_audit_state_v1', '')}, "
            f"alignment={row.get('nas_btc_hard_opposed_truth_alignment_v1', '')}, "
            f"fixed={json.dumps(row.get('nas_btc_hard_opposed_fixed_blockers_v1', []), ensure_ascii=False)}, "
            f"tunable={json.dumps(row.get('nas_btc_hard_opposed_tunable_drivers_v1', []), ensure_ascii=False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_nas_btc_hard_opposed_truth_audit_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_nas_btc_hard_opposed_truth_audit_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "nas_btc_hard_opposed_truth_audit_latest.json"
    markdown_path = output_dir / "nas_btc_hard_opposed_truth_audit_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_nas_btc_hard_opposed_truth_audit_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
