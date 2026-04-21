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
from backend.services.nas_btc_hard_opposed_truth_audit import (
    NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_CONTRACT_VERSION,
    attach_nas_btc_hard_opposed_truth_audit_fields_v1,
)
from backend.services.retained_window_flow_calibration_contract import (
    build_retained_window_flow_calibration_contract_v1,
)
from backend.services.xau_refined_gate_timebox_audit import (
    XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION,
    attach_xau_refined_gate_timebox_audit_fields_v1,
)


BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION = "bounded_calibration_candidate_contract_v1"
BOUNDED_CALIBRATION_CANDIDATE_SUMMARY_VERSION = "bounded_calibration_candidate_summary_v1"

UPSTREAM_ALIGNMENT_ENUM_V1 = (
    "READY_FROM_ROW",
    "READY_FROM_ATTACHED_UPSTREAM",
    "PARTIAL_UPSTREAM",
)
UPSTREAM_SOURCE_ENUM_V1 = (
    "ROW_ONLY",
    "ATTACHED_FLOW_REVIEW",
    "ATTACHED_HARD_OPPOSED",
    "ATTACHED_BOTH",
)
SEED_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "FIXED_BLOCKED",
    "TUNABLE_SEED",
    "MIXED_SEED",
    "FILTERED_OUT",
    "REVIEW_PENDING",
)
FILTERING_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "FIXED_BLOCKED",
    "REVIEW_PENDING",
    "FILTERED_READY",
    "FILTERED_OUT",
    "CONFLICT_HOLD",
)
SEED_PRIORITY_ENUM_V1 = ("NONE", "LOW", "MEDIUM", "HIGH")
SEED_CONFIDENCE_ENUM_V1 = ("NONE", "LOW", "MEDIUM", "HIGH")
CANDIDATE_STATUS_ENUM_V1 = ("PROPOSED", "FILTERED_OUT", "REVIEW_ONLY")
VALIDATION_SEED_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "SYMBOL_READY",
    "SYMBOL_PARTIAL",
    "CROSS_SYMBOL_REQUIRED",
    "REVIEW_ONLY",
)
CANDIDATE_OUTCOME_ENUM_V1 = (
    "PROMOTE",
    "KEEP_OBSERVING",
    "EXPIRE_WITHOUT_PROMOTION",
    "ROLLBACK",
)
CANDIDATE_GRADUATION_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "SHADOW_REQUIRED",
    "REQUIRES_VALIDATION_SCOPE",
    "REVIEW_ONLY",
)
SHADOW_GATE_STATE_ENUM_V1 = (
    "NOT_APPLICABLE",
    "ELIGIBLE",
    "BLOCKED_FIXED_OVERLAP",
    "BLOCKED_ANCHOR_REVIEW",
    "BLOCKED_LOW_SCORE",
    "BLOCKED_VALIDATION_SCOPE",
    "BLOCKED_NEUTRAL_DIRECTION",
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def build_bounded_calibration_candidate_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "F9 S1 upstream alignment layer. Makes bounded calibration seed building self-contained by "
            "re-attaching flow candidate review and NAS/BTC hard-opposed audit layers when a row arrives "
            "without those upstream fields."
        ),
        "upstream_contract_versions_v1": [
            FLOW_CANDIDATE_IMPROVEMENT_REVIEW_CONTRACT_VERSION,
            NAS_BTC_HARD_OPPOSED_TRUTH_AUDIT_CONTRACT_VERSION,
            XAU_REFINED_GATE_TIMEBOX_AUDIT_CONTRACT_VERSION,
        ],
        "upstream_alignment_enum_v1": list(UPSTREAM_ALIGNMENT_ENUM_V1),
        "upstream_source_enum_v1": list(UPSTREAM_SOURCE_ENUM_V1),
        "filtering_state_enum_v1": list(FILTERING_STATE_ENUM_V1),
        "seed_priority_enum_v1": list(SEED_PRIORITY_ENUM_V1),
        "seed_confidence_enum_v1": list(SEED_CONFIDENCE_ENUM_V1),
        "candidate_status_enum_v1": list(CANDIDATE_STATUS_ENUM_V1),
        "validation_seed_state_enum_v1": list(VALIDATION_SEED_STATE_ENUM_V1),
        "candidate_outcome_enum_v1": list(CANDIDATE_OUTCOME_ENUM_V1),
        "candidate_graduation_state_enum_v1": list(CANDIDATE_GRADUATION_STATE_ENUM_V1),
        "shadow_gate_state_enum_v1": list(SHADOW_GATE_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "bounded_calibration_candidate_profile_v1",
            "bounded_calibration_candidate_upstream_alignment_v1",
            "bounded_calibration_candidate_upstream_source_v1",
            "bounded_calibration_candidate_attached_layers_v1",
            "bounded_calibration_candidate_missing_after_attach_v1",
            "bounded_calibration_candidate_seed_builder_ready_v1",
            "bounded_calibration_candidate_upstream_reason_summary_v1",
            "bounded_calibration_candidate_seed_state_v1",
            "bounded_calibration_candidate_seed_keys_v1",
            "bounded_calibration_candidate_seed_importance_v1",
            "bounded_calibration_candidate_seed_primary_key_v1",
            "bounded_calibration_candidate_seed_primary_importance_v1",
            "bounded_calibration_candidate_seed_relevance_score_v1",
            "bounded_calibration_candidate_seed_safety_score_v1",
            "bounded_calibration_candidate_seed_repeatability_score_v1",
            "bounded_calibration_candidate_seed_priority_score_v1",
            "bounded_calibration_candidate_seed_priority_v1",
            "bounded_calibration_candidate_seed_confidence_v1",
            "bounded_calibration_candidate_filtering_state_v1",
            "bounded_calibration_candidate_filtered_keys_v1",
            "bounded_calibration_candidate_filtered_out_keys_v1",
            "bounded_calibration_candidate_filtered_key_scores_v1",
            "bounded_calibration_candidate_filtered_key_directions_v1",
            "bounded_calibration_candidate_filter_conflict_flag_v1",
            "bounded_calibration_candidate_filter_reason_v1",
            "bounded_calibration_candidate_recent_rollback_keys_v1",
            "bounded_calibration_candidate_seed_reason_v1",
            "bounded_calibration_candidate_ids_v1",
            "bounded_calibration_candidate_statuses_v1",
            "bounded_calibration_candidate_outcomes_v1",
            "bounded_calibration_candidate_graduation_states_v1",
            "bounded_calibration_candidate_primary_candidate_id_v1",
            "bounded_calibration_candidate_primary_status_v1",
            "bounded_calibration_candidate_primary_outcome_v1",
            "bounded_calibration_candidate_primary_graduation_state_v1",
            "bounded_calibration_candidate_primary_validation_state_v1",
            "bounded_calibration_candidate_primary_anchor_role_v1",
            "bounded_calibration_candidate_primary_direction_v1",
            "bounded_calibration_candidate_primary_priority_v1",
            "bounded_calibration_candidate_primary_confidence_v1",
            "bounded_calibration_candidate_primary_shadow_gate_state_v1",
            "bounded_calibration_candidate_primary_blockers_v1",
            "bounded_calibration_candidate_flat_reason_summary_v1",
        ],
        "seed_state_enum_v1": list(SEED_STATE_ENUM_V1),
        "control_rules_v1": [
            "seed builder must not depend on whether upstream fields were already persisted on the row",
            "flow candidate improvement review is attached first when missing",
            "nas btc hard opposed truth audit is attached second when missing",
            "missing-after-attach remains visible instead of being silently ignored",
            "row-level seed extraction classifies rows into fixed-blocked, tunable-seed, mixed-seed, filtered-out, or hold states",
            "learning key importance is split into truth pressure, delta severity, tunable purity, repetition support, and control gap",
            "candidate priority is separated into relevance, safety, repeatability, and a final priority score",
            "priority answers what to try first while confidence answers how trustworthy the candidate seed currently is",
            "row-level filtering keeps at most two review keys",
            "threshold and floor keys are preferred ahead of penalty scale keys when scores are otherwise close",
            "fixed-only rows do not create filtered candidate keys",
            "recently rolled-back keys can be suppressed when rollback memory is present on the row",
            "conflicting directions are not kept active together in the same filtered set",
            "candidate objects are materialized per symbol and learning key after row-level filtering",
            "candidate objects stay shadow-ready in this phase and do not apply any live calibration patch",
            "mixed-only candidates remain review-only until pure tunable evidence improves",
            "candidate outcome and graduation rules are governance metadata in this phase and do not replace F10 or F11 evaluation",
            "candidate validation seed includes same-symbol retained windows and same-symbol recent live scope",
            "cross-symbol validation is required only when a learning key is explicitly shared/common",
            "execution and state25 remain unchanged in this phase",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _has_flow_candidate_review(row: Mapping[str, Any]) -> bool:
    return bool(_text(row.get("flow_candidate_improvement_verdict_v1")))


def _has_hard_opposed_audit(row: Mapping[str, Any]) -> bool:
    return bool(_text(row.get("nas_btc_hard_opposed_truth_audit_state_v1")))


def _has_xau_gate_audit(row: Mapping[str, Any]) -> bool:
    return bool(_text(row.get("xau_gate_timebox_audit_state_v1")))


def _ensure_upstream(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    row = dict(_mapping(payload))
    symbol = _text(row.get("symbol")).upper()
    had_flow_review = _has_flow_candidate_review(row)
    had_hard_opposed = _has_hard_opposed_audit(row)
    had_xau_audit = _has_xau_gate_audit(row)
    attached_layers: list[str] = []

    if not had_flow_review:
        row = dict(attach_flow_candidate_improvement_review_fields_v1({"_": row}).get("_", row))
        if _has_flow_candidate_review(row):
            attached_layers.append("flow_candidate_improvement_review")

    if not had_hard_opposed:
        row = dict(attach_nas_btc_hard_opposed_truth_audit_fields_v1({"_": row}).get("_", row))
        if _has_hard_opposed_audit(row):
            attached_layers.append("nas_btc_hard_opposed_truth_audit")
        if not had_flow_review and _has_flow_candidate_review(row) and "flow_candidate_improvement_review" not in attached_layers:
            attached_layers.append("flow_candidate_improvement_review")

    if symbol == "XAUUSD" and not had_xau_audit:
        row = dict(attach_xau_refined_gate_timebox_audit_fields_v1({"_": row}).get("_", row))
        if _has_xau_gate_audit(row):
            attached_layers.append("xau_refined_gate_timebox_audit")

    missing_after_attach: list[str] = []
    if not _has_flow_candidate_review(row):
        missing_after_attach.append("flow_candidate_improvement_review")
    if not _has_hard_opposed_audit(row):
        missing_after_attach.append("nas_btc_hard_opposed_truth_audit")
    if symbol == "XAUUSD" and not _has_xau_gate_audit(row):
        missing_after_attach.append("xau_refined_gate_timebox_audit")

    if not missing_after_attach and had_flow_review and had_hard_opposed:
        alignment = "READY_FROM_ROW"
    elif not missing_after_attach:
        alignment = "READY_FROM_ATTACHED_UPSTREAM"
    else:
        alignment = "PARTIAL_UPSTREAM"

    attached_set = set(attached_layers)
    if "flow_candidate_improvement_review" in attached_set and "nas_btc_hard_opposed_truth_audit" in attached_set:
        source = "ATTACHED_BOTH"
    elif "nas_btc_hard_opposed_truth_audit" in attached_set:
        source = "ATTACHED_HARD_OPPOSED"
    elif "flow_candidate_improvement_review" in attached_set:
        source = "ATTACHED_FLOW_REVIEW"
    else:
        source = "ROW_ONLY"

    meta = {
        "had_flow_review": had_flow_review,
        "had_hard_opposed": had_hard_opposed,
        "had_xau_audit": had_xau_audit,
        "attached_layers": attached_layers,
        "missing_after_attach": missing_after_attach,
        "upstream_alignment": alignment,
        "upstream_source": source,
        "seed_builder_ready": not missing_after_attach,
    }
    return row, meta


def _reason_summary(*, alignment: str, source: str, attached_layers: list[str], missing_after_attach: list[str], seed_ready: bool) -> str:
    return (
        f"alignment={alignment}; "
        f"source={source}; "
        f"attached={','.join(attached_layers) or 'none'}; "
        f"missing={','.join(missing_after_attach) or 'none'}; "
        f"seed_ready={seed_ready}"
    )


def _seed_state_reason(
    *,
    symbol: str,
    truth_state: str,
    verdict: str,
    audit_state: str,
    learning_state: str,
    learning_keys: list[str],
    seed_state: str,
    xau_audit_state: str,
    xau_failure_stage: str,
    xau_candidate_state: str,
) -> str:
    return (
        f"symbol={symbol}; "
        f"truth={truth_state}; "
        f"verdict={verdict}; "
        f"audit_state={audit_state}; "
        f"learning_state={learning_state}; "
        f"xau_audit_state={xau_audit_state}; "
        f"xau_failure_stage={xau_failure_stage}; "
        f"xau_candidate_state={xau_candidate_state}; "
        f"keys={','.join(learning_keys) or 'none'}; "
        f"seed_state={seed_state}"
    )


def _truth_pressure_score(truth_state: str) -> float:
    truth_state = _text(truth_state).upper()
    if truth_state in {"WIDEN_EXPECTED", "TIGHTEN_EXPECTED"}:
        return 1.0
    if truth_state == "REVIEW_PENDING":
        return 0.4
    return 0.1


def _delta_severity_score(verdict: str) -> float:
    verdict = _text(verdict).upper()
    if verdict in {"OVER_TIGHTENED", "OVER_WIDENED"}:
        return 1.0
    if verdict in {"MISSED_IMPROVEMENT", "MISSED_TIGHTENING"}:
        return 0.8
    if verdict == "REVIEW_PENDING":
        return 0.4
    return 0.1


def _tunable_purity_score(seed_state: str) -> float:
    seed_state = _text(seed_state).upper()
    if seed_state == "TUNABLE_SEED":
        return 1.0
    if seed_state == "MIXED_SEED":
        return 0.6
    if seed_state == "FILTERED_OUT":
        return 0.25
    return 0.0


def _repetition_support_score(key_count: int) -> float:
    count = int(key_count or 0)
    if count >= 3:
        return 1.0
    if count == 2:
        return 0.7
    if count == 1:
        return 0.4
    return 0.0


def _control_gap_score(key: str, row: Mapping[str, Any]) -> float:
    key = _text(key)
    if key == "flow.ambiguity_threshold":
        return _clamp01(_float(row.get("aggregate_ambiguity_penalty_v1"), 0.0) / 0.35)
    if key == "flow.structure_soft_score_floor":
        soft_score = _float(row.get("flow_structure_gate_soft_score_v1"), 0.0)
        return _clamp01((3.0 - max(0.0, min(soft_score, 3.0))) / 3.0)
    if key == "flow.conviction_building_floor":
        floor = _float(row.get("aggregate_conviction_building_floor_v1"), 0.0)
        current = _float(
            row.get("aggregate_conviction_v1"),
            _float(row.get("xau_gate_effective_aggregate_conviction_v1"), 0.0),
        )
        return 0.0 if floor <= 0.0 else _clamp01((floor - current) / floor)
    if key == "flow.persistence_building_floor":
        floor = _float(row.get("flow_persistence_building_floor_v1"), 0.0)
        current = _float(
            row.get("flow_persistence_v1"),
            _float(row.get("xau_gate_effective_flow_persistence_v1"), 0.0),
        )
        return 0.0 if floor <= 0.0 else _clamp01((floor - current) / floor)
    if key == "flow.ambiguity_penalty_scale":
        return _clamp01(_float(row.get("aggregate_ambiguity_penalty_v1"), 0.0) / 0.35)
    if key == "flow.veto_penalty_scale":
        return _clamp01(_float(row.get("aggregate_veto_penalty_v1"), 0.0) / 0.25)
    if key == "flow.persistence_recency_weight_scale":
        weight = _float(row.get("flow_persistence_recency_weight_v1"), 0.0)
        return 0.0 if weight <= 0.0 else _clamp01(max(0.0, 0.7 - weight) / 0.7)
    return 0.0


def _resolved_learning_keys(row: Mapping[str, Any]) -> list[str]:
    base_keys = [_text(item) for item in list(row.get("nas_btc_hard_opposed_learning_keys_v1") or []) if _text(item)]
    symbol = _text(row.get("symbol")).upper()
    truth_state = _text(row.get("flow_candidate_truth_state_v1")).upper()
    verdict = _text(row.get("flow_candidate_improvement_verdict_v1")).upper()
    audit_state = _text(row.get("nas_btc_hard_opposed_truth_audit_state_v1")).upper()
    learning_state = _text(row.get("nas_btc_hard_opposed_learning_state_v1")).upper()
    xau_audit_state = _text(row.get("xau_gate_timebox_audit_state_v1")).upper()
    xau_failure_stage = _text(row.get("xau_gate_failure_stage_v1")).upper()
    xau_candidate_state = _text(row.get("xau_gate_effective_candidate_state_v1")).upper()
    xau_risk_gate = _text(row.get("xau_gate_effective_risk_gate_v1")).upper()
    xau_aggregate = _float(row.get("xau_gate_effective_aggregate_conviction_v1"), 0.0)
    xau_persistence = _float(row.get("xau_gate_effective_flow_persistence_v1"), 0.0)
    conviction_floor = _float(row.get("aggregate_conviction_building_floor_v1"), 0.0)
    persistence_floor = _float(row.get("flow_persistence_building_floor_v1"), 0.0)

    if symbol != "XAUUSD" or xau_audit_state != "READY":
        if (
            symbol in {"NAS100", "BTCUSD"}
            and not base_keys
            and audit_state != "FIXED_HARD_OPPOSED"
            and learning_state != "FIXED_BLOCKED"
        ):
            fallback_keys: list[str] = []
            hard_disqualifiers = {
                _text(item).upper()
                for item in list(row.get("flow_structure_gate_hard_disqualifiers_v1") or [])
                if _text(item)
            }
            candidate_pressure = truth_state in {"WIDEN_EXPECTED", "TIGHTEN_EXPECTED"} or verdict in {
                "MISSED_IMPROVEMENT",
                "OVER_TIGHTENED",
                "MISSED_TIGHTENING",
                "OVER_WIDENED",
            }
            if candidate_pressure:
                if "AMBIGUITY_HIGH" in hard_disqualifiers:
                    fallback_keys.append("flow.ambiguity_threshold")
                soft_score = _float(row.get("flow_structure_gate_soft_score_v1"), 0.0)
                if 0.0 <= soft_score < 2.0:
                    fallback_keys.append("flow.structure_soft_score_floor")
                conviction_floor = _float(row.get("aggregate_conviction_building_floor_v1"), 0.0)
                conviction = _float(row.get("aggregate_conviction_v1"), 0.0)
                if conviction_floor > 0.0 and conviction <= conviction_floor:
                    fallback_keys.append("flow.conviction_building_floor")
                persistence_floor = _float(row.get("flow_persistence_building_floor_v1"), 0.0)
                persistence = _float(row.get("flow_persistence_v1"), 0.0)
                if persistence_floor > 0.0 and persistence <= persistence_floor:
                    fallback_keys.append("flow.persistence_building_floor")
            merged_fallback: list[str] = []
            for item in fallback_keys:
                if item and item not in merged_fallback:
                    merged_fallback.append(item)
            return merged_fallback
        return base_keys

    extra_keys: list[str] = []
    if conviction_floor > 0.0 and 0.0 < xau_aggregate <= conviction_floor:
        extra_keys.append("flow.conviction_building_floor")
    if persistence_floor > 0.0 and 0.0 < xau_persistence <= persistence_floor:
        extra_keys.append("flow.persistence_building_floor")
    if xau_failure_stage in {"PILOT_MATCH", "AMBIGUITY", "TEXTURE"}:
        extra_keys.append("flow.ambiguity_penalty_scale")
    if xau_candidate_state == "OBSERVE_ONLY" or xau_risk_gate in {"FAIL_PILOT_MATCH", "FAIL_HOLD_POLICY"}:
        extra_keys.append("flow.veto_penalty_scale")

    merged: list[str] = []
    for item in [*base_keys, *extra_keys]:
        if item and item not in merged:
            merged.append(item)
    return merged


def _seed_safety_score(seed_state: str) -> float:
    seed_state = _text(seed_state).upper()
    if seed_state == "TUNABLE_SEED":
        return 0.9
    if seed_state == "MIXED_SEED":
        return 0.5
    if seed_state == "FILTERED_OUT":
        return 0.2
    if seed_state == "REVIEW_PENDING":
        return 0.15
    return 0.0


def _seed_confidence(seed_state: str, priority_score: float) -> str:
    seed_state = _text(seed_state).upper()
    score = float(priority_score or 0.0)
    if seed_state == "TUNABLE_SEED":
        if score >= 0.75:
            return "HIGH"
        if score >= 0.5:
            return "MEDIUM"
        return "LOW"
    if seed_state == "MIXED_SEED":
        return "LOW"
    if seed_state in {"FILTERED_OUT", "REVIEW_PENDING"}:
        return "LOW"
    return "NONE"


def _seed_priority_bucket(priority_score: float) -> str:
    score = float(priority_score or 0.0)
    if score >= 0.75:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    if score > 0.0:
        return "LOW"
    return "NONE"


def _seed_effect_direction(truth_state: str, verdict: str) -> str:
    truth_state = _text(truth_state).upper()
    verdict = _text(verdict).upper()
    if truth_state == "WIDEN_EXPECTED" or verdict in {"OVER_TIGHTENED", "MISSED_IMPROVEMENT"}:
        return "RELAX"
    if truth_state == "TIGHTEN_EXPECTED" or verdict in {"OVER_WIDENED", "MISSED_TIGHTENING"}:
        return "TIGHTEN"
    return "NEUTRAL"


def _is_penalty_key(key: str) -> bool:
    key = _text(key)
    return key.endswith("_penalty_scale") or key.endswith("_weight_scale")


def _build_seed_importance_surface(
    row: Mapping[str, Any],
    *,
    key_counts: Mapping[str, int] | None = None,
) -> tuple[dict[str, dict[str, float]], str, float]:
    learning_keys = [_text(item) for item in list(row.get("bounded_calibration_candidate_seed_keys_v1") or []) if _text(item)]
    truth_state = _text(row.get("flow_candidate_truth_state_v1"))
    verdict = _text(row.get("flow_candidate_improvement_verdict_v1"))
    seed_state = _text(row.get("bounded_calibration_candidate_seed_state_v1"))
    counts = {str(key): int(value) for key, value in dict(key_counts or {}).items()}

    importance_surface: dict[str, dict[str, float]] = {}
    primary_key = ""
    primary_importance = 0.0

    for key in learning_keys:
        truth_pressure = _truth_pressure_score(truth_state)
        delta_severity = _delta_severity_score(verdict)
        tunable_purity = _tunable_purity_score(seed_state)
        repetition_support = _repetition_support_score(counts.get(key, 1))
        control_gap = _control_gap_score(key, row)
        importance_score = round(
            (0.25 * truth_pressure)
            + (0.25 * delta_severity)
            + (0.20 * tunable_purity)
            + (0.15 * repetition_support)
            + (0.15 * control_gap),
            4,
        )
        importance_surface[key] = {
            "truth_pressure": round(truth_pressure, 4),
            "delta_severity": round(delta_severity, 4),
            "tunable_purity": round(tunable_purity, 4),
            "repetition_support": round(repetition_support, 4),
            "control_gap": round(control_gap, 4),
            "importance_score": float(importance_score),
        }
        if not primary_key or importance_score > primary_importance:
            primary_key = key
            primary_importance = float(importance_score)

    return importance_surface, primary_key, round(primary_importance, 4)


def _seed_state(
    *,
    symbol: str,
    seed_ready: bool,
    truth_state: str,
    verdict: str,
    audit_state: str,
    learning_state: str,
    learning_keys: list[str],
    xau_audit_state: str,
    xau_failure_stage: str,
    xau_candidate_state: str,
) -> str:
    symbol = _text(symbol).upper()
    truth_state = _text(truth_state).upper()
    verdict = _text(verdict).upper()
    audit_state = _text(audit_state).upper()
    learning_state = _text(learning_state).upper()
    learning_keys = [_text(item) for item in list(learning_keys or []) if _text(item)]
    xau_audit_state = _text(xau_audit_state).upper()
    xau_failure_stage = _text(xau_failure_stage).upper()
    xau_candidate_state = _text(xau_candidate_state).upper()

    if not seed_ready:
        return "REVIEW_PENDING"
    if symbol == "XAUUSD" and xau_audit_state == "READY":
        if xau_candidate_state == "BOUNDED_READY":
            return "NOT_APPLICABLE"
        if xau_failure_stage in {"PILOT_MATCH", "AMBIGUITY", "TEXTURE", "ENTRY_POLICY", "HOLD_POLICY", "CANARY_SCOPE"}:
            return "MIXED_SEED" if learning_keys else "REVIEW_PENDING"
    if (
        truth_state == "REVIEW_PENDING"
        or verdict == "REVIEW_PENDING"
        or audit_state == "REVIEW_PENDING"
        or learning_state == "REVIEW_PENDING"
    ):
        return "REVIEW_PENDING"
    if audit_state == "FIXED_HARD_OPPOSED" or learning_state == "FIXED_BLOCKED":
        return "FIXED_BLOCKED"
    if audit_state == "MIXED_REVIEW" or learning_state == "MIXED_REVIEW":
        return "MIXED_SEED" if learning_keys else "FILTERED_OUT"
    if audit_state == "TUNABLE_OVER_TIGHTEN_RISK" or learning_state == "LEARNING_CANDIDATE":
        return "TUNABLE_SEED" if learning_keys else "FILTERED_OUT"

    candidate_pressure = truth_state in {"WIDEN_EXPECTED", "TIGHTEN_EXPECTED"}
    review_like_verdict = verdict in {
        "MISSED_IMPROVEMENT",
        "OVER_TIGHTENED",
        "MISSED_TIGHTENING",
        "OVER_WIDENED",
    }
    if symbol in {"NAS100", "BTCUSD"} and learning_keys and (candidate_pressure or review_like_verdict):
        return "MIXED_SEED"
    if candidate_pressure or review_like_verdict:
        return "FILTERED_OUT"
    return "NOT_APPLICABLE"


def _attach_seed_importance_fields_to_row(
    row: Mapping[str, Any],
    *,
    key_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    enriched = dict(_mapping(row))
    importance_surface, primary_key, primary_importance = _build_seed_importance_surface(
        enriched,
        key_counts=key_counts,
    )
    profile = _mapping(enriched.get("bounded_calibration_candidate_profile_v1"))
    profile["bounded_calibration_candidate_seed_importance_v1"] = dict(importance_surface)
    profile["bounded_calibration_candidate_seed_primary_key_v1"] = primary_key
    profile["bounded_calibration_candidate_seed_primary_importance_v1"] = float(primary_importance)
    enriched["bounded_calibration_candidate_profile_v1"] = profile
    enriched["bounded_calibration_candidate_seed_importance_v1"] = dict(importance_surface)
    enriched["bounded_calibration_candidate_seed_primary_key_v1"] = primary_key
    enriched["bounded_calibration_candidate_seed_primary_importance_v1"] = float(primary_importance)
    return enriched


def _attach_seed_priority_fields_to_row(row: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(_mapping(row))
    seed_state = _text(enriched.get("bounded_calibration_candidate_seed_state_v1"))
    primary_key = _text(enriched.get("bounded_calibration_candidate_seed_primary_key_v1"))
    importance_surface = _mapping(enriched.get("bounded_calibration_candidate_seed_importance_v1"))
    primary_surface = _mapping(importance_surface.get(primary_key))

    relevance = round(
        (
            _float(primary_surface.get("truth_pressure"), 0.0)
            + _float(primary_surface.get("delta_severity"), 0.0)
            + _float(primary_surface.get("control_gap"), 0.0)
        )
        / 3.0,
        4,
    ) if primary_key else 0.0
    safety = round(_seed_safety_score(seed_state), 4)
    repeatability = round(_float(primary_surface.get("repetition_support"), 0.0), 4) if primary_key else 0.0
    priority_score = round(
        (0.4 * relevance) + (0.35 * safety) + (0.25 * repeatability),
        4,
    ) if primary_key else 0.0
    priority = _seed_priority_bucket(priority_score)
    confidence = _seed_confidence(seed_state, priority_score)

    profile = _mapping(enriched.get("bounded_calibration_candidate_profile_v1"))
    profile["bounded_calibration_candidate_seed_relevance_score_v1"] = float(relevance)
    profile["bounded_calibration_candidate_seed_safety_score_v1"] = float(safety)
    profile["bounded_calibration_candidate_seed_repeatability_score_v1"] = float(repeatability)
    profile["bounded_calibration_candidate_seed_priority_score_v1"] = float(priority_score)
    profile["bounded_calibration_candidate_seed_priority_v1"] = priority
    profile["bounded_calibration_candidate_seed_confidence_v1"] = confidence

    enriched["bounded_calibration_candidate_profile_v1"] = profile
    enriched["bounded_calibration_candidate_seed_relevance_score_v1"] = float(relevance)
    enriched["bounded_calibration_candidate_seed_safety_score_v1"] = float(safety)
    enriched["bounded_calibration_candidate_seed_repeatability_score_v1"] = float(repeatability)
    enriched["bounded_calibration_candidate_seed_priority_score_v1"] = float(priority_score)
    enriched["bounded_calibration_candidate_seed_priority_v1"] = priority
    enriched["bounded_calibration_candidate_seed_confidence_v1"] = confidence
    return enriched


def _attach_filtering_fields_to_row(row: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(_mapping(row))
    seed_state = _text(enriched.get("bounded_calibration_candidate_seed_state_v1")).upper()
    truth_state = _text(enriched.get("flow_candidate_truth_state_v1"))
    verdict = _text(enriched.get("flow_candidate_improvement_verdict_v1"))
    recent_rollback_keys = {
        _text(item) for item in list(enriched.get("bounded_calibration_candidate_recent_rollback_keys_v1") or []) if _text(item)
    }
    learning_keys = [_text(item) for item in list(enriched.get("bounded_calibration_candidate_seed_keys_v1") or []) if _text(item)]
    importance_surface = _mapping(enriched.get("bounded_calibration_candidate_seed_importance_v1"))
    row_safety = _float(enriched.get("bounded_calibration_candidate_seed_safety_score_v1"), 0.0)
    default_direction = _seed_effect_direction(truth_state, verdict)
    direction_overrides = _mapping(enriched.get("bounded_calibration_candidate_seed_direction_overrides_v1"))

    filtered_keys: list[str] = []
    filtered_out_keys: list[str] = []
    filtered_key_scores: dict[str, float] = {}
    filtered_key_directions: dict[str, str] = {}
    conflict_flag = False

    filtering_state = "FILTERED_OUT"
    reason = "no_seed_keys"

    if seed_state == "FIXED_BLOCKED":
        filtering_state = "FIXED_BLOCKED"
        reason = "fixed_blocked_seed"
    elif seed_state == "REVIEW_PENDING":
        filtering_state = "REVIEW_PENDING"
        reason = "review_pending_seed"
    elif seed_state == "FILTERED_OUT":
        filtering_state = "FILTERED_OUT"
        reason = "filtered_out_seed"
    elif seed_state == "NOT_APPLICABLE":
        filtering_state = "NOT_APPLICABLE"
        reason = "not_applicable_seed"
    else:
        ranked_items: list[tuple[int, float, str]] = []
        for key in learning_keys:
            if key in recent_rollback_keys:
                filtered_out_keys.append(key)
                continue
            surface = _mapping(importance_surface.get(key))
            relevance = (
                _float(surface.get("truth_pressure"), 0.0)
                + _float(surface.get("delta_severity"), 0.0)
                + _float(surface.get("control_gap"), 0.0)
            ) / 3.0
            repeatability = _float(surface.get("repetition_support"), 0.0)
            key_priority_score = round((0.4 * relevance) + (0.35 * row_safety) + (0.25 * repeatability), 4)
            preference_rank = 1 if _is_penalty_key(key) else 0
            ranked_items.append((preference_rank, -key_priority_score, key))
            filtered_key_scores[key] = float(key_priority_score)
            filtered_key_directions[key] = _text(direction_overrides.get(key)) or default_direction

        ranked_items.sort()
        filtered_keys = [key for _, __, key in ranked_items[:2]]
        filtered_out_keys.extend([key for _, __, key in ranked_items[2:]])

        active_directions = {
            _text(filtered_key_directions.get(key)).upper()
            for key in filtered_keys
            if _text(filtered_key_directions.get(key)).upper() in {"RELAX", "TIGHTEN"}
        }
        conflict_flag = len(active_directions) > 1

        if conflict_flag:
            filtering_state = "CONFLICT_HOLD"
            if filtered_keys:
                winner = max(filtered_keys, key=lambda item: filtered_key_scores.get(item, 0.0))
                filtered_out_keys.extend([key for key in filtered_keys if key != winner])
                filtered_keys = [winner]
            reason = "conflicting_directions_filtered"
        elif filtered_keys:
            filtering_state = "FILTERED_READY"
            reason = "top_review_keys_ready"
        else:
            filtering_state = "FILTERED_OUT"
            reason = "no_surviving_keys_after_filter"

    profile = _mapping(enriched.get("bounded_calibration_candidate_profile_v1"))
    profile["bounded_calibration_candidate_filtering_state_v1"] = filtering_state
    profile["bounded_calibration_candidate_filtered_keys_v1"] = list(filtered_keys)
    profile["bounded_calibration_candidate_filtered_out_keys_v1"] = list(filtered_out_keys)
    profile["bounded_calibration_candidate_filtered_key_scores_v1"] = dict(filtered_key_scores)
    profile["bounded_calibration_candidate_filtered_key_directions_v1"] = dict(filtered_key_directions)
    profile["bounded_calibration_candidate_filter_conflict_flag_v1"] = bool(conflict_flag)
    profile["bounded_calibration_candidate_filter_reason_v1"] = reason

    enriched["bounded_calibration_candidate_profile_v1"] = profile
    enriched["bounded_calibration_candidate_filtering_state_v1"] = filtering_state
    enriched["bounded_calibration_candidate_filtered_keys_v1"] = list(filtered_keys)
    enriched["bounded_calibration_candidate_filtered_out_keys_v1"] = list(filtered_out_keys)
    enriched["bounded_calibration_candidate_filtered_key_scores_v1"] = dict(filtered_key_scores)
    enriched["bounded_calibration_candidate_filtered_key_directions_v1"] = dict(filtered_key_directions)
    enriched["bounded_calibration_candidate_filter_conflict_flag_v1"] = bool(conflict_flag)
    enriched["bounded_calibration_candidate_filter_reason_v1"] = reason
    return enriched


def _build_candidate_seed_catalog_v1(
    rows_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(rows_by_symbol or {}).items():
        row = _mapping(raw)
        filtering_state = _text(row.get("bounded_calibration_candidate_filtering_state_v1")).upper()
        if filtering_state not in {"FILTERED_READY", "CONFLICT_HOLD", "FIXED_BLOCKED"}:
            continue

        symbol_name = _text(row.get("symbol") or symbol).upper() or _text(symbol).upper()
        seed_state = _text(row.get("bounded_calibration_candidate_seed_state_v1")).upper()
        fixed_blockers = [_text(item) for item in list(row.get("nas_btc_hard_opposed_fixed_blockers_v1") or []) if _text(item)]
        alignment = _text(row.get("flow_candidate_review_alignment_v1")).upper() or "UNKNOWN"
        error_type = _text(row.get("dominance_error_type_v1")).upper() or "UNKNOWN"
        direction_map = _mapping(row.get("bounded_calibration_candidate_filtered_key_directions_v1"))
        score_map = {
            _text(key): _float(value, 0.0)
            for key, value in _mapping(row.get("bounded_calibration_candidate_filtered_key_scores_v1")).items()
        }
        confidence = _text(row.get("bounded_calibration_candidate_seed_confidence_v1")).upper() or "NONE"
        priority = _text(row.get("bounded_calibration_candidate_seed_priority_v1")).upper() or "NONE"
        candidate_keys = [_text(item) for item in list(row.get("bounded_calibration_candidate_filtered_keys_v1") or []) if _text(item)]
        if filtering_state == "FIXED_BLOCKED":
            fallback_key = _text(row.get("bounded_calibration_candidate_seed_primary_key_v1"))
            if fallback_key:
                candidate_keys = [fallback_key]
                if fallback_key not in score_map:
                    score_map[fallback_key] = _float(row.get("bounded_calibration_candidate_seed_priority_score_v1"), 0.0)
                if fallback_key not in direction_map:
                    direction_map[fallback_key] = _seed_effect_direction(
                        _text(row.get("flow_candidate_truth_state_v1")),
                        _text(row.get("flow_candidate_improvement_verdict_v1")),
                    )

        for key in candidate_keys:
            learning_key = _text(key)
            if not learning_key:
                continue
            candidate_id = f"{symbol_name}:{learning_key}"
            entry = catalog.setdefault(
                candidate_id,
                {
                    "candidate_id": candidate_id,
                    "symbol": symbol_name,
                    "learning_key": learning_key,
                    "affected_row_count": 0,
                    "pure_tunable_count": 0,
                    "mixed_row_count": 0,
                    "fixed_blocker_overlap_count": 0,
                    "truth_error_type_count_summary": {},
                    "alignment_count_summary": {},
                    "direction_count_summary": {},
                    "filtering_state_count_summary": {},
                    "confidence_count_summary": {},
                    "priority_count_summary": {},
                    "avg_filtered_key_score": 0.0,
                    "avg_primary_importance": 0.0,
                    "_score_total": 0.0,
                    "_primary_importance_total": 0.0,
                },
            )

            entry["affected_row_count"] += 1
            if seed_state == "TUNABLE_SEED":
                entry["pure_tunable_count"] += 1
            if seed_state == "MIXED_SEED":
                entry["mixed_row_count"] += 1
            if fixed_blockers or filtering_state == "FIXED_BLOCKED":
                entry["fixed_blocker_overlap_count"] += 1

            truth_error_counts = dict(entry.get("truth_error_type_count_summary") or {})
            truth_error_counts[error_type] = int(truth_error_counts.get(error_type, 0) or 0) + 1
            entry["truth_error_type_count_summary"] = truth_error_counts

            alignment_counts = dict(entry.get("alignment_count_summary") or {})
            alignment_counts[alignment] = int(alignment_counts.get(alignment, 0) or 0) + 1
            entry["alignment_count_summary"] = alignment_counts

            direction = _text(direction_map.get(learning_key)).upper() or "NEUTRAL"
            direction_counts = dict(entry.get("direction_count_summary") or {})
            direction_counts[direction] = int(direction_counts.get(direction, 0) or 0) + 1
            entry["direction_count_summary"] = direction_counts

            filtering_counts = dict(entry.get("filtering_state_count_summary") or {})
            filtering_counts[filtering_state] = int(filtering_counts.get(filtering_state, 0) or 0) + 1
            entry["filtering_state_count_summary"] = filtering_counts

            confidence_counts = dict(entry.get("confidence_count_summary") or {})
            confidence_counts[confidence] = int(confidence_counts.get(confidence, 0) or 0) + 1
            entry["confidence_count_summary"] = confidence_counts

            priority_counts = dict(entry.get("priority_count_summary") or {})
            priority_counts[priority] = int(priority_counts.get(priority, 0) or 0) + 1
            entry["priority_count_summary"] = priority_counts

            entry["_score_total"] += float(score_map.get(learning_key, 0.0))
            entry["_primary_importance_total"] += _float(row.get("bounded_calibration_candidate_seed_primary_importance_v1"), 0.0)

    for candidate_id, entry in list(catalog.items()):
        affected = max(1, int(entry.get("affected_row_count", 0) or 0))
        entry["avg_filtered_key_score"] = round(float(entry.pop("_score_total", 0.0)) / affected, 4)
        entry["avg_primary_importance"] = round(float(entry.pop("_primary_importance_total", 0.0)) / affected, 4)
        catalog[candidate_id] = entry
    return catalog


def _candidate_counter_dominant_label(
    count_summary: Mapping[str, Any] | None,
    *,
    default: str = "",
    preferred_order: tuple[str, ...] = (),
) -> str:
    counts = {
        _text(key): int(value or 0)
        for key, value in dict(count_summary or {}).items()
        if _text(key)
    }
    if not counts:
        return default
    order_index = {label: idx for idx, label in enumerate(preferred_order)}
    return max(
        counts.items(),
        key=lambda item: (
            int(item[1]),
            -order_index.get(item[0], len(order_index)),
            item[0],
        ),
    )[0]


def _candidate_current_value_for_key(learning_key: str, row: Mapping[str, Any]) -> tuple[float, str]:
    learning_key = _text(learning_key)
    if learning_key == "flow.ambiguity_threshold":
        return 0.4, "DEFAULT_ANCHOR"
    if learning_key == "flow.structure_soft_score_floor":
        return 2.0, "DEFAULT_ANCHOR"
    if learning_key == "flow.conviction_building_floor":
        value = _float(row.get("aggregate_conviction_building_floor_v1"), 0.55)
        return value or 0.55, "ROW_FLOOR_FIELD"
    if learning_key == "flow.persistence_building_floor":
        value = _float(row.get("flow_persistence_building_floor_v1"), 0.55)
        return value or 0.55, "ROW_FLOOR_FIELD"
    if learning_key == "flow.ambiguity_penalty_scale":
        return 1.0, "DEFAULT_ANCHOR"
    if learning_key == "flow.veto_penalty_scale":
        return 1.0, "DEFAULT_ANCHOR"
    if learning_key == "flow.persistence_recency_weight_scale":
        value = _float(
            row.get("flow_persistence_recency_weight_scale_v1"),
            _float(row.get("flow_persistence_recency_weight_v1"), 0.7),
        )
        return value or 0.7, "ROW_WEIGHT_FIELD"
    return 0.0, "UNKNOWN"


def _candidate_max_allowed_delta_for_key(learning_key: str) -> float:
    learning_key = _text(learning_key)
    if learning_key == "flow.structure_soft_score_floor":
        return 0.5
    if learning_key in {"flow.ambiguity_penalty_scale", "flow.veto_penalty_scale"}:
        return 0.1
    if learning_key == "flow.persistence_recency_weight_scale":
        return 0.05
    return 0.05


def _candidate_value_bounds_for_key(learning_key: str) -> tuple[float, float]:
    learning_key = _text(learning_key)
    if learning_key == "flow.structure_soft_score_floor":
        return 0.0, 3.0
    if learning_key in {"flow.conviction_building_floor", "flow.persistence_building_floor"}:
        return 0.2, 0.85
    if learning_key in {"flow.ambiguity_threshold"}:
        return 0.1, 0.8
    if learning_key in {"flow.ambiguity_penalty_scale", "flow.veto_penalty_scale"}:
        return 0.5, 1.5
    if learning_key == "flow.persistence_recency_weight_scale":
        return 0.3, 1.0
    return 0.0, 1.0


def _candidate_delta_factor(priority: str, confidence: str) -> float:
    priority_factor = {
        "HIGH": 1.0,
        "MEDIUM": 0.75,
        "LOW": 0.5,
        "NONE": 0.25,
    }.get(_text(priority).upper(), 0.25)
    confidence_factor = {
        "HIGH": 1.0,
        "MEDIUM": 0.75,
        "LOW": 0.5,
        "NONE": 0.25,
    }.get(_text(confidence).upper(), 0.25)
    return round(priority_factor * confidence_factor, 4)


def _candidate_proposed_value_for_key(
    learning_key: str,
    *,
    current_value: float,
    direction: str,
    priority: str,
    confidence: str,
) -> tuple[float, float]:
    learning_key = _text(learning_key)
    direction = _text(direction).upper()
    max_allowed_delta = _candidate_max_allowed_delta_for_key(learning_key)
    delta_factor = _candidate_delta_factor(priority, confidence)
    base_delta = round(max_allowed_delta * delta_factor, 4)

    if direction not in {"RELAX", "TIGHTEN"} or base_delta <= 0.0:
        return round(float(current_value), 4), 0.0

    sign = -1.0 if direction == "RELAX" else 1.0
    if learning_key == "flow.persistence_recency_weight_scale":
        sign *= -1.0

    min_value, max_value = _candidate_value_bounds_for_key(learning_key)
    proposed_value = round(max(min_value, min(max_value, float(current_value) + (sign * base_delta))), 4)
    applied_delta = round(proposed_value - float(current_value), 4)
    return proposed_value, applied_delta


def _candidate_scope_for_direction(symbol: str, direction: str) -> dict[str, Any]:
    direction = _text(direction).upper()
    if direction == "RELAX":
        apply_states = ["FLOW_OPPOSED", "FLOW_UNCONFIRMED", "FLOW_BUILDING"]
    elif direction == "TIGHTEN":
        apply_states = ["FLOW_BUILDING", "FLOW_CONFIRMED"]
    else:
        apply_states = ["FLOW_UNCONFIRMED"]
    return {
        "apply_mode": "shadow_only",
        "apply_symbols": [_text(symbol).upper()],
        "apply_states": list(apply_states),
        "validation_windows": ["recent_live", "retained_symbol_windows"],
        "apply_duration_hours": 48,
    }


def _shared_learning_key(learning_key: str) -> bool:
    key = _text(learning_key).lower()
    return key.startswith("common.") or key.startswith("shared.") or ".shared_" in key


def _retained_window_ids_by_symbol_v1() -> dict[str, list[str]]:
    contract = build_retained_window_flow_calibration_contract_v1()
    rows = list(contract.get("retained_window_catalog_v1") or [])
    windows_by_symbol: dict[str, list[str]] = {}
    for raw in rows:
        row = _mapping(raw)
        symbol = _text(row.get("symbol_v1")).upper()
        window_id = _text(row.get("window_id_v1"))
        if not symbol or not window_id:
            continue
        windows_by_symbol.setdefault(symbol, []).append(window_id)
    return windows_by_symbol


def _candidate_rollback_config(current_value: float, learning_key: str) -> dict[str, Any]:
    return {
        "rollback_to": round(float(current_value), 4),
        "auto_rollback_if": {
            "over_veto_increase_pct": 15,
            "under_veto_increase_pct": 10,
            "unverified_widening_increase_pct": 20,
            "cross_symbol_drift_pct": 5 if _text(learning_key).startswith("flow.") else 10,
        },
    }


def _candidate_validation_seed_v1(
    *,
    symbol: str,
    learning_key: str,
    status: str,
    scope: Mapping[str, Any] | None,
    row_available: bool,
    retained_window_ids: list[str] | None,
    all_symbols: list[str] | None,
) -> dict[str, Any]:
    symbol_name = _text(symbol).upper()
    learning_key = _text(learning_key)
    retained_ids = [_text(item) for item in list(retained_window_ids or []) if _text(item)]
    recent_live_windows = ["latest_signal_by_symbol"] if row_available else []
    shared_required = _shared_learning_key(learning_key)
    cross_symbol_symbols = [
        _text(item).upper()
        for item in list(all_symbols or [])
        if _text(item).upper() and _text(item).upper() != symbol_name
    ] if shared_required else []

    status_upper = _text(status).upper()
    if status_upper == "FILTERED_OUT":
        validation_state = "NOT_APPLICABLE"
    elif status_upper == "REVIEW_ONLY":
        validation_state = "REVIEW_ONLY"
    elif shared_required and retained_ids and recent_live_windows:
        validation_state = "CROSS_SYMBOL_REQUIRED"
    elif retained_ids and recent_live_windows:
        validation_state = "SYMBOL_READY"
    else:
        validation_state = "SYMBOL_PARTIAL"

    validation_scope = {
        "same_symbol_retained_window_ids_v1": list(retained_ids),
        "same_symbol_recent_live_windows_v1": list(recent_live_windows),
        "cross_symbol_required_v1": bool(shared_required),
        "cross_symbol_symbols_v1": list(cross_symbol_symbols),
        "apply_states_v1": list(_mapping(scope).get("apply_states", []) or []),
    }
    reason = (
        f"symbol={symbol_name or 'UNKNOWN'}; "
        f"learning_key={learning_key or 'UNKNOWN'}; "
        f"retained_windows={len(retained_ids)}; "
        f"recent_live_windows={len(recent_live_windows)}; "
        f"cross_symbol_required={shared_required}; "
        f"validation_state={validation_state}"
    )
    return {
        "validation_seed_state_v1": validation_state,
        "validation_scope_v1": validation_scope,
        "validation_seed_reason_summary_v1": reason,
    }


def _candidate_outcome_and_graduation_v1(
    *,
    status: str,
    validation_seed_state: str,
    learning_key: str,
) -> dict[str, Any]:
    status_upper = _text(status).upper()
    validation_upper = _text(validation_seed_state).upper()
    shared_required = _shared_learning_key(learning_key)

    minimum_shadow_windows_required = 3 if shared_required else 2
    graduation_requirements = {
        "minimum_shadow_windows_required_v1": int(minimum_shadow_windows_required),
        "same_symbol_cross_window_required_v1": True,
        "under_veto_guard_required_v1": True,
        "unverified_widening_guard_required_v1": True,
        "cross_symbol_drift_guard_required_v1": bool(shared_required),
        "promote_after_shadow_only_v1": True,
    }

    blockers: list[str] = []
    if status_upper == "FILTERED_OUT":
        outcome = "EXPIRE_WITHOUT_PROMOTION"
        graduation_state = "NOT_APPLICABLE"
        blockers.append("NO_ACTIVE_CANDIDATE")
    elif status_upper == "REVIEW_ONLY":
        outcome = "KEEP_OBSERVING"
        graduation_state = "REVIEW_ONLY"
        blockers.append("REQUIRES_PURE_TUNABLE_EVIDENCE")
    elif validation_upper == "SYMBOL_PARTIAL":
        outcome = "KEEP_OBSERVING"
        graduation_state = "REQUIRES_VALIDATION_SCOPE"
        blockers.append("VALIDATION_SCOPE_PARTIAL")
    elif validation_upper in {"SYMBOL_READY", "CROSS_SYMBOL_REQUIRED"}:
        outcome = "KEEP_OBSERVING"
        graduation_state = "SHADOW_REQUIRED"
        blockers.append("REQUIRES_SHADOW_APPLY")
        if validation_upper == "CROSS_SYMBOL_REQUIRED":
            blockers.append("REQUIRES_CROSS_SYMBOL_GUARD")
    else:
        outcome = "KEEP_OBSERVING"
        graduation_state = "REQUIRES_VALIDATION_SCOPE"
        blockers.append("VALIDATION_SCOPE_UNCLEAR")

    reason = (
        f"status={status_upper or 'UNKNOWN'}; "
        f"validation_seed_state={validation_upper or 'UNKNOWN'}; "
        f"minimum_shadow_windows_required={minimum_shadow_windows_required}; "
        f"cross_symbol_guard_required={shared_required}; "
        f"outcome={outcome}; "
        f"graduation_state={graduation_state}; "
        f"blockers={','.join(blockers) or 'none'}"
    )
    return {
        "candidate_outcome_v1": outcome,
        "candidate_outcome_reason_summary_v1": reason,
        "candidate_graduation_state_v1": graduation_state,
        "candidate_graduation_blockers_v1": list(blockers),
        "candidate_graduation_requirements_v1": graduation_requirements,
    }


def _is_xau_review_anchor_candidate(
    *,
    symbol: str,
    affected_row_count: int,
    pure_tunable_count: int,
    mixed_row_count: int,
    direction: str,
) -> bool:
    return (
        _text(symbol).upper() == "XAUUSD"
        and int(affected_row_count or 0) > 0
        and int(pure_tunable_count or 0) <= 0
        and int(mixed_row_count or 0) > 0
        and _text(direction).upper() == "NEUTRAL"
    )


def _is_fixed_review_anchor_candidate(
    *,
    affected_row_count: int,
    pure_tunable_count: int,
    mixed_row_count: int,
    fixed_blocker_overlap_count: int,
) -> bool:
    return (
        int(affected_row_count or 0) > 0
        and int(pure_tunable_count or 0) <= 0
        and int(mixed_row_count or 0) <= 0
        and int(fixed_blocker_overlap_count or 0) > 0
    )


def _mixed_candidate_shadow_gate_v1(
    *,
    symbol: str,
    direction: str,
    affected_row_count: int,
    pure_tunable_count: int,
    mixed_row_count: int,
    fixed_blocker_overlap_count: int,
    relevance: float,
    safety: float,
    priority_score: float,
    retained_window_ids: list[str] | None,
    row_available: bool,
    xau_review_anchor: bool,
) -> dict[str, Any]:
    symbol_name = _text(symbol).upper()
    direction = _text(direction).upper()
    retained_count = len([_text(item) for item in list(retained_window_ids or []) if _text(item)])

    if pure_tunable_count > 0 or mixed_row_count <= 0 or affected_row_count <= 0:
        state = "NOT_APPLICABLE"
        eligible = False
    elif xau_review_anchor:
        state = "BLOCKED_ANCHOR_REVIEW"
        eligible = False
    elif direction not in {"RELAX", "TIGHTEN"}:
        state = "BLOCKED_NEUTRAL_DIRECTION"
        eligible = False
    elif fixed_blocker_overlap_count > 0:
        state = "BLOCKED_FIXED_OVERLAP"
        eligible = False
    elif not row_available or retained_count < 2:
        state = "BLOCKED_VALIDATION_SCOPE"
        eligible = False
    elif float(relevance or 0.0) < 0.6 or float(safety or 0.0) < 0.55 or float(priority_score or 0.0) < 0.54:
        state = "BLOCKED_LOW_SCORE"
        eligible = False
    else:
        state = "ELIGIBLE"
        eligible = True

    reason = (
        f"symbol={symbol_name or 'UNKNOWN'}; "
        f"direction={direction or 'NONE'}; "
        f"affected_rows={int(affected_row_count or 0)}; "
        f"mixed_rows={int(mixed_row_count or 0)}; "
        f"fixed_overlap={int(fixed_blocker_overlap_count or 0)}; "
        f"relevance={round(float(relevance or 0.0), 4)}; "
        f"safety={round(float(safety or 0.0), 4)}; "
        f"priority_score={round(float(priority_score or 0.0), 4)}; "
        f"retained_windows={retained_count}; "
        f"row_available={bool(row_available)}; "
        f"state={state}; "
        f"eligible={eligible}"
    )
    return {
        "candidate_shadow_gate_state_v1": state,
        "candidate_shadow_gate_eligible_v1": bool(eligible),
        "candidate_shadow_gate_reason_summary_v1": reason,
    }


def _materialize_candidate_objects_v1(
    candidate_catalog: Mapping[str, Any] | None,
    rows_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    objects: dict[str, dict[str, Any]] = {}
    rows = {str(key).upper(): _mapping(value) for key, value in dict(rows_by_symbol or {}).items()}
    retained_windows_by_symbol = _retained_window_ids_by_symbol_v1()
    all_symbols = sorted({*rows.keys(), *retained_windows_by_symbol.keys()})

    for candidate_id, raw in dict(candidate_catalog or {}).items():
        candidate = _mapping(raw)
        symbol = _text(candidate.get("symbol")).upper()
        learning_key = _text(candidate.get("learning_key"))
        row = rows.get(symbol, {})

        direction = _candidate_counter_dominant_label(
            candidate.get("direction_count_summary"),
            default="NEUTRAL",
            preferred_order=("RELAX", "TIGHTEN", "NEUTRAL"),
        )
        confidence = _candidate_counter_dominant_label(
            candidate.get("confidence_count_summary"),
            default="NONE",
            preferred_order=("HIGH", "MEDIUM", "LOW", "NONE"),
        )
        priority = _candidate_counter_dominant_label(
            candidate.get("priority_count_summary"),
            default="NONE",
            preferred_order=("HIGH", "MEDIUM", "LOW", "NONE"),
        )

        current_value, current_value_source = _candidate_current_value_for_key(learning_key, row)
        proposed_value, delta = _candidate_proposed_value_for_key(
            learning_key,
            current_value=current_value,
            direction=direction,
            priority=priority,
            confidence=confidence,
        )
        max_allowed_delta = _candidate_max_allowed_delta_for_key(learning_key)
        affected_row_count = int(candidate.get("affected_row_count", 0) or 0)
        pure_tunable_count = int(candidate.get("pure_tunable_count", 0) or 0)
        mixed_row_count = int(candidate.get("mixed_row_count", 0) or 0)
        fixed_overlap_count = int(candidate.get("fixed_blocker_overlap_count", 0) or 0)
        avg_score = _float(candidate.get("avg_filtered_key_score"), 0.0)
        avg_primary_importance = _float(candidate.get("avg_primary_importance"), 0.0)
        repeatability = _repetition_support_score(affected_row_count)
        safety = 1.0 if pure_tunable_count > 0 and fixed_overlap_count == 0 else 0.55 if mixed_row_count > 0 else 0.2
        relevance = round((avg_score + avg_primary_importance) / 2.0, 4)
        priority_score = round((0.4 * relevance) + (0.35 * safety) + (0.25 * repeatability), 4)
        retained_window_ids = retained_windows_by_symbol.get(symbol, [])
        xau_review_anchor = _is_xau_review_anchor_candidate(
            symbol=symbol,
            affected_row_count=affected_row_count,
            pure_tunable_count=pure_tunable_count,
            mixed_row_count=mixed_row_count,
            direction=direction,
        )
        fixed_review_anchor = _is_fixed_review_anchor_candidate(
            affected_row_count=affected_row_count,
            pure_tunable_count=pure_tunable_count,
            mixed_row_count=mixed_row_count,
            fixed_blocker_overlap_count=fixed_overlap_count,
        )
        shadow_gate = _mixed_candidate_shadow_gate_v1(
            symbol=symbol,
            direction=direction,
            affected_row_count=affected_row_count,
            pure_tunable_count=pure_tunable_count,
            mixed_row_count=mixed_row_count,
            fixed_blocker_overlap_count=fixed_overlap_count,
            relevance=relevance,
            safety=safety,
            priority_score=priority_score,
            retained_window_ids=retained_window_ids,
            row_available=bool(row),
            xau_review_anchor=xau_review_anchor,
        )

        if xau_review_anchor or fixed_review_anchor:
            status = "REVIEW_ONLY"
        elif affected_row_count <= 0 or direction == "NEUTRAL" or abs(delta) <= 0.0:
            status = "FILTERED_OUT"
        elif pure_tunable_count > 0:
            status = "PROPOSED"
        elif _bool(shadow_gate.get("candidate_shadow_gate_eligible_v1")):
            status = "PROPOSED"
        else:
            status = "REVIEW_ONLY"

        scope = _candidate_scope_for_direction(symbol, direction)
        validation_seed = _candidate_validation_seed_v1(
            symbol=symbol,
            learning_key=learning_key,
            status=status,
            scope=scope,
            row_available=bool(row),
            retained_window_ids=retained_windows_by_symbol.get(symbol, []),
            all_symbols=all_symbols,
        )
        outcome_meta = _candidate_outcome_and_graduation_v1(
            status=status,
            validation_seed_state=_text(validation_seed.get("validation_seed_state_v1")),
            learning_key=learning_key,
        )

        objects[str(candidate_id)] = {
            "candidate_id": _text(candidate.get("candidate_id") or candidate_id),
            "symbol": symbol,
            "learning_key": learning_key,
            "current_value": round(float(current_value), 4),
            "current_value_source_v1": current_value_source,
            "proposed_value": round(float(proposed_value), 4),
            "delta": round(float(delta), 4),
            "max_allowed_delta": round(float(max_allowed_delta), 4),
            "direction": direction,
            "confidence": confidence,
            "priority": priority,
            "candidate_relevance_score_v1": float(relevance),
            "candidate_safety_score_v1": round(float(safety), 4),
            "candidate_repeatability_score_v1": round(float(repeatability), 4),
            "candidate_priority_score_v1": float(priority_score),
            "importance_score": round(avg_primary_importance, 4),
            "candidate_anchor_role_v1": (
                "XAU_REVIEW_ANCHOR"
                if xau_review_anchor
                else "FIXED_REVIEW_ANCHOR"
                if fixed_review_anchor
                else "NONE"
            ),
            "candidate_shadow_gate_state_v1": _text(shadow_gate.get("candidate_shadow_gate_state_v1")),
            "candidate_shadow_gate_eligible_v1": _bool(shadow_gate.get("candidate_shadow_gate_eligible_v1")),
            "candidate_shadow_gate_reason_summary_v1": _text(shadow_gate.get("candidate_shadow_gate_reason_summary_v1")),
            "status": status,
            "evidence": {
                "affected_row_count": affected_row_count,
                "pure_tunable_count": pure_tunable_count,
                "mixed_row_count": mixed_row_count,
                "fixed_blocker_overlap_count": fixed_overlap_count,
                "truth_error_type_count_summary": dict(candidate.get("truth_error_type_count_summary") or {}),
                "alignment_count_summary": dict(candidate.get("alignment_count_summary") or {}),
                "direction_count_summary": dict(candidate.get("direction_count_summary") or {}),
                "filtering_state_count_summary": dict(candidate.get("filtering_state_count_summary") or {}),
                "confidence_count_summary": dict(candidate.get("confidence_count_summary") or {}),
                "priority_count_summary": dict(candidate.get("priority_count_summary") or {}),
                "avg_filtered_key_score": round(avg_score, 4),
                "avg_primary_importance": round(avg_primary_importance, 4),
            },
            "scope": scope,
            "validation_seed_state_v1": _text(validation_seed.get("validation_seed_state_v1")),
            "validation_scope_v1": _mapping(validation_seed.get("validation_scope_v1")),
            "validation_seed_reason_summary_v1": _text(validation_seed.get("validation_seed_reason_summary_v1")),
            "candidate_outcome_v1": _text(outcome_meta.get("candidate_outcome_v1")),
            "candidate_outcome_reason_summary_v1": _text(outcome_meta.get("candidate_outcome_reason_summary_v1")),
            "candidate_graduation_state_v1": _text(outcome_meta.get("candidate_graduation_state_v1")),
            "candidate_graduation_blockers_v1": list(outcome_meta.get("candidate_graduation_blockers_v1") or []),
            "candidate_graduation_requirements_v1": _mapping(outcome_meta.get("candidate_graduation_requirements_v1")),
            "rollback": _candidate_rollback_config(current_value, learning_key),
        }

    return objects


def build_bounded_calibration_candidate_row_v1(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload, meta = _ensure_upstream(row or {})
    symbol = _text(payload.get("symbol")).upper()
    alignment = _text(meta.get("upstream_alignment"))
    source = _text(meta.get("upstream_source"))
    attached_layers = list(meta.get("attached_layers") or [])
    missing_after_attach = list(meta.get("missing_after_attach") or [])
    seed_ready = _bool(meta.get("seed_builder_ready"))
    upstream_reason = _reason_summary(
        alignment=alignment,
        source=source,
        attached_layers=attached_layers,
        missing_after_attach=missing_after_attach,
        seed_ready=seed_ready,
    )
    truth_state = _text(payload.get("flow_candidate_truth_state_v1")).upper()
    verdict = _text(payload.get("flow_candidate_improvement_verdict_v1")).upper()
    audit_state = _text(payload.get("nas_btc_hard_opposed_truth_audit_state_v1")).upper()
    learning_state = _text(payload.get("nas_btc_hard_opposed_learning_state_v1")).upper()
    xau_audit_state = _text(payload.get("xau_gate_timebox_audit_state_v1")).upper()
    xau_failure_stage = _text(payload.get("xau_gate_failure_stage_v1")).upper()
    xau_candidate_state = _text(payload.get("xau_gate_effective_candidate_state_v1")).upper()
    learning_keys = _resolved_learning_keys(payload)
    seed_state = _seed_state(
        symbol=symbol,
        seed_ready=seed_ready,
        truth_state=truth_state,
        verdict=verdict,
        audit_state=audit_state,
        learning_state=learning_state,
        learning_keys=learning_keys,
        xau_audit_state=xau_audit_state,
        xau_failure_stage=xau_failure_stage,
        xau_candidate_state=xau_candidate_state,
    )
    seed_reason = _seed_state_reason(
        symbol=symbol or "UNKNOWN",
        truth_state=truth_state,
        verdict=verdict,
        audit_state=audit_state,
        learning_state=learning_state,
        learning_keys=learning_keys,
        seed_state=seed_state,
        xau_audit_state=xau_audit_state,
        xau_failure_stage=xau_failure_stage,
        xau_candidate_state=xau_candidate_state,
    )
    recent_rollback_keys = [
        _text(item)
        for item in list(payload.get("bounded_calibration_candidate_recent_rollback_keys_v1") or [])
        if _text(item)
    ]

    profile = {
        "contract_version": BOUNDED_CALIBRATION_CANDIDATE_CONTRACT_VERSION,
        "bounded_calibration_candidate_upstream_alignment_v1": alignment,
        "bounded_calibration_candidate_upstream_source_v1": source,
        "bounded_calibration_candidate_attached_layers_v1": list(attached_layers),
        "bounded_calibration_candidate_missing_after_attach_v1": list(missing_after_attach),
        "bounded_calibration_candidate_seed_builder_ready_v1": seed_ready,
        "bounded_calibration_candidate_upstream_reason_summary_v1": upstream_reason,
        "bounded_calibration_candidate_seed_state_v1": seed_state,
        "bounded_calibration_candidate_seed_keys_v1": list(learning_keys),
        "bounded_calibration_candidate_seed_importance_v1": {},
        "bounded_calibration_candidate_seed_primary_key_v1": "",
        "bounded_calibration_candidate_seed_primary_importance_v1": 0.0,
        "bounded_calibration_candidate_seed_relevance_score_v1": 0.0,
        "bounded_calibration_candidate_seed_safety_score_v1": 0.0,
        "bounded_calibration_candidate_seed_repeatability_score_v1": 0.0,
        "bounded_calibration_candidate_seed_priority_score_v1": 0.0,
        "bounded_calibration_candidate_seed_priority_v1": "NONE",
        "bounded_calibration_candidate_seed_confidence_v1": "NONE",
        "bounded_calibration_candidate_filtering_state_v1": "FILTERED_OUT",
        "bounded_calibration_candidate_filtered_keys_v1": [],
        "bounded_calibration_candidate_filtered_out_keys_v1": [],
        "bounded_calibration_candidate_filtered_key_scores_v1": {},
        "bounded_calibration_candidate_filtered_key_directions_v1": {},
        "bounded_calibration_candidate_filter_conflict_flag_v1": False,
        "bounded_calibration_candidate_filter_reason_v1": "",
        "bounded_calibration_candidate_recent_rollback_keys_v1": list(recent_rollback_keys),
        "bounded_calibration_candidate_seed_reason_v1": seed_reason,
        "bounded_calibration_candidate_ids_v1": [],
        "bounded_calibration_candidate_statuses_v1": {},
        "bounded_calibration_candidate_outcomes_v1": {},
        "bounded_calibration_candidate_graduation_states_v1": {},
        "bounded_calibration_candidate_primary_candidate_id_v1": "",
        "bounded_calibration_candidate_primary_status_v1": "NONE",
        "bounded_calibration_candidate_primary_outcome_v1": "NONE",
        "bounded_calibration_candidate_primary_graduation_state_v1": "NONE",
        "bounded_calibration_candidate_primary_validation_state_v1": "NONE",
        "bounded_calibration_candidate_primary_anchor_role_v1": "NONE",
        "bounded_calibration_candidate_primary_direction_v1": "NONE",
        "bounded_calibration_candidate_primary_priority_v1": "NONE",
        "bounded_calibration_candidate_primary_confidence_v1": "NONE",
        "bounded_calibration_candidate_primary_blockers_v1": [],
        "bounded_calibration_candidate_flat_reason_summary_v1": "",
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    row_surface = {
        **payload,
        "bounded_calibration_candidate_profile_v1": profile,
        "bounded_calibration_candidate_upstream_alignment_v1": alignment,
        "bounded_calibration_candidate_upstream_source_v1": source,
        "bounded_calibration_candidate_attached_layers_v1": list(attached_layers),
        "bounded_calibration_candidate_missing_after_attach_v1": list(missing_after_attach),
        "bounded_calibration_candidate_seed_builder_ready_v1": seed_ready,
        "bounded_calibration_candidate_upstream_reason_summary_v1": upstream_reason,
        "bounded_calibration_candidate_seed_state_v1": seed_state,
        "bounded_calibration_candidate_seed_keys_v1": list(learning_keys),
        "bounded_calibration_candidate_seed_importance_v1": {},
        "bounded_calibration_candidate_seed_primary_key_v1": "",
        "bounded_calibration_candidate_seed_primary_importance_v1": 0.0,
        "bounded_calibration_candidate_seed_relevance_score_v1": 0.0,
        "bounded_calibration_candidate_seed_safety_score_v1": 0.0,
        "bounded_calibration_candidate_seed_repeatability_score_v1": 0.0,
        "bounded_calibration_candidate_seed_priority_score_v1": 0.0,
        "bounded_calibration_candidate_seed_priority_v1": "NONE",
        "bounded_calibration_candidate_seed_confidence_v1": "NONE",
        "bounded_calibration_candidate_filtering_state_v1": "FILTERED_OUT",
        "bounded_calibration_candidate_filtered_keys_v1": [],
        "bounded_calibration_candidate_filtered_out_keys_v1": [],
        "bounded_calibration_candidate_filtered_key_scores_v1": {},
        "bounded_calibration_candidate_filtered_key_directions_v1": {},
        "bounded_calibration_candidate_filter_conflict_flag_v1": False,
        "bounded_calibration_candidate_filter_reason_v1": "",
        "bounded_calibration_candidate_recent_rollback_keys_v1": list(recent_rollback_keys),
        "bounded_calibration_candidate_seed_reason_v1": seed_reason,
        "bounded_calibration_candidate_ids_v1": [],
        "bounded_calibration_candidate_statuses_v1": {},
        "bounded_calibration_candidate_outcomes_v1": {},
        "bounded_calibration_candidate_graduation_states_v1": {},
        "bounded_calibration_candidate_primary_candidate_id_v1": "",
        "bounded_calibration_candidate_primary_status_v1": "NONE",
        "bounded_calibration_candidate_primary_outcome_v1": "NONE",
        "bounded_calibration_candidate_primary_graduation_state_v1": "NONE",
        "bounded_calibration_candidate_primary_validation_state_v1": "NONE",
        "bounded_calibration_candidate_primary_anchor_role_v1": "NONE",
        "bounded_calibration_candidate_primary_direction_v1": "NONE",
        "bounded_calibration_candidate_primary_priority_v1": "NONE",
        "bounded_calibration_candidate_primary_confidence_v1": "NONE",
        "bounded_calibration_candidate_primary_blockers_v1": [],
        "bounded_calibration_candidate_flat_reason_summary_v1": "",
    }
    row_surface = _attach_seed_importance_fields_to_row(row_surface)
    row_surface = _attach_seed_priority_fields_to_row(row_surface)
    return _attach_filtering_fields_to_row(row_surface)


def _candidate_status_rank(status: str) -> int:
    return {
        "PROPOSED": 3,
        "REVIEW_ONLY": 2,
        "FILTERED_OUT": 1,
    }.get(_text(status).upper(), 0)


def _candidate_primary_sort_key(candidate: Mapping[str, Any]) -> tuple[float, int, float, str]:
    payload = _mapping(candidate)
    return (
        _float(payload.get("candidate_priority_score_v1"), 0.0),
        _candidate_status_rank(_text(payload.get("status"))),
        _float(payload.get("importance_score"), 0.0),
        _text(payload.get("candidate_id")),
    )


def _flat_reason_summary_for_candidate_row(
    *,
    candidate_ids: list[str],
    primary_candidate: Mapping[str, Any] | None,
) -> str:
    primary = _mapping(primary_candidate)
    return (
        f"candidate_ids={','.join(candidate_ids) or 'none'}; "
        f"primary={_text(primary.get('candidate_id')) or 'none'}; "
        f"status={_text(primary.get('status')) or 'NONE'}; "
        f"outcome={_text(primary.get('candidate_outcome_v1')) or 'NONE'}; "
        f"graduation={_text(primary.get('candidate_graduation_state_v1')) or 'NONE'}; "
        f"validation={_text(primary.get('validation_seed_state_v1')) or 'NONE'}; "
        f"anchor={_text(primary.get('candidate_anchor_role_v1')) or 'NONE'}; "
        f"shadow_gate={_text(primary.get('candidate_shadow_gate_state_v1')) or 'NONE'}; "
        f"blockers={','.join(list(primary.get('candidate_graduation_blockers_v1') or [])) or 'none'}"
    )


def _attach_candidate_flat_surface_to_rows_v1(
    rows_by_symbol: Mapping[str, Any] | None,
    candidate_objects: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    candidates_by_id = {
        _text(candidate_id): _mapping(candidate)
        for candidate_id, candidate in dict(candidate_objects or {}).items()
        if _text(candidate_id)
    }
    enriched_rows: dict[str, dict[str, Any]] = {}

    for symbol, raw in dict(rows_by_symbol or {}).items():
        row = dict(_mapping(raw))
        symbol_name = _text(row.get("symbol") or symbol).upper() or _text(symbol).upper()
        filtered_keys = [_text(item) for item in list(row.get("bounded_calibration_candidate_filtered_keys_v1") or []) if _text(item)]
        if not filtered_keys and _text(row.get("bounded_calibration_candidate_seed_state_v1")).upper() == "FIXED_BLOCKED":
            anchor_key = _text(row.get("bounded_calibration_candidate_seed_primary_key_v1"))
            if anchor_key:
                filtered_keys = [anchor_key]
        candidate_ids = [f"{symbol_name}:{learning_key}" for learning_key in filtered_keys]
        matched_candidates = [
            candidates_by_id[candidate_id]
            for candidate_id in candidate_ids
            if candidate_id in candidates_by_id
        ]
        primary_candidate = max(matched_candidates, key=_candidate_primary_sort_key) if matched_candidates else {}

        statuses = {
            _text(candidate.get("candidate_id")): _text(candidate.get("status"))
            for candidate in matched_candidates
            if _text(candidate.get("candidate_id"))
        }
        outcomes = {
            _text(candidate.get("candidate_id")): _text(candidate.get("candidate_outcome_v1"))
            for candidate in matched_candidates
            if _text(candidate.get("candidate_id"))
        }
        graduation_states = {
            _text(candidate.get("candidate_id")): _text(candidate.get("candidate_graduation_state_v1"))
            for candidate in matched_candidates
            if _text(candidate.get("candidate_id"))
        }

        flat_reason = _flat_reason_summary_for_candidate_row(
            candidate_ids=candidate_ids,
            primary_candidate=primary_candidate,
        )

        profile = _mapping(row.get("bounded_calibration_candidate_profile_v1"))
        profile["bounded_calibration_candidate_ids_v1"] = list(candidate_ids)
        profile["bounded_calibration_candidate_statuses_v1"] = dict(statuses)
        profile["bounded_calibration_candidate_outcomes_v1"] = dict(outcomes)
        profile["bounded_calibration_candidate_graduation_states_v1"] = dict(graduation_states)
        profile["bounded_calibration_candidate_primary_candidate_id_v1"] = _text(primary_candidate.get("candidate_id"))
        profile["bounded_calibration_candidate_primary_status_v1"] = _text(primary_candidate.get("status")) or "NONE"
        profile["bounded_calibration_candidate_primary_outcome_v1"] = _text(primary_candidate.get("candidate_outcome_v1")) or "NONE"
        profile["bounded_calibration_candidate_primary_graduation_state_v1"] = (
            _text(primary_candidate.get("candidate_graduation_state_v1")) or "NONE"
        )
        profile["bounded_calibration_candidate_primary_validation_state_v1"] = (
            _text(primary_candidate.get("validation_seed_state_v1")) or "NONE"
        )
        profile["bounded_calibration_candidate_primary_anchor_role_v1"] = (
            _text(primary_candidate.get("candidate_anchor_role_v1")) or "NONE"
        )
        profile["bounded_calibration_candidate_primary_direction_v1"] = _text(primary_candidate.get("direction")) or "NONE"
        profile["bounded_calibration_candidate_primary_priority_v1"] = _text(primary_candidate.get("priority")) or "NONE"
        profile["bounded_calibration_candidate_primary_confidence_v1"] = _text(primary_candidate.get("confidence")) or "NONE"
        profile["bounded_calibration_candidate_primary_shadow_gate_state_v1"] = (
            _text(primary_candidate.get("candidate_shadow_gate_state_v1")) or "NONE"
        )
        profile["bounded_calibration_candidate_primary_blockers_v1"] = list(
            primary_candidate.get("candidate_graduation_blockers_v1") or []
        )
        profile["bounded_calibration_candidate_flat_reason_summary_v1"] = flat_reason

        row["bounded_calibration_candidate_profile_v1"] = profile
        row["bounded_calibration_candidate_ids_v1"] = list(candidate_ids)
        row["bounded_calibration_candidate_statuses_v1"] = dict(statuses)
        row["bounded_calibration_candidate_outcomes_v1"] = dict(outcomes)
        row["bounded_calibration_candidate_graduation_states_v1"] = dict(graduation_states)
        row["bounded_calibration_candidate_primary_candidate_id_v1"] = _text(primary_candidate.get("candidate_id"))
        row["bounded_calibration_candidate_primary_status_v1"] = _text(primary_candidate.get("status")) or "NONE"
        row["bounded_calibration_candidate_primary_outcome_v1"] = _text(primary_candidate.get("candidate_outcome_v1")) or "NONE"
        row["bounded_calibration_candidate_primary_graduation_state_v1"] = (
            _text(primary_candidate.get("candidate_graduation_state_v1")) or "NONE"
        )
        row["bounded_calibration_candidate_primary_validation_state_v1"] = (
            _text(primary_candidate.get("validation_seed_state_v1")) or "NONE"
        )
        row["bounded_calibration_candidate_primary_anchor_role_v1"] = (
            _text(primary_candidate.get("candidate_anchor_role_v1")) or "NONE"
        )
        row["bounded_calibration_candidate_primary_direction_v1"] = _text(primary_candidate.get("direction")) or "NONE"
        row["bounded_calibration_candidate_primary_priority_v1"] = _text(primary_candidate.get("priority")) or "NONE"
        row["bounded_calibration_candidate_primary_confidence_v1"] = _text(primary_candidate.get("confidence")) or "NONE"
        row["bounded_calibration_candidate_primary_shadow_gate_state_v1"] = (
            _text(primary_candidate.get("candidate_shadow_gate_state_v1")) or "NONE"
        )
        row["bounded_calibration_candidate_primary_blockers_v1"] = list(
            primary_candidate.get("candidate_graduation_blockers_v1") or []
        )
        row["bounded_calibration_candidate_flat_reason_summary_v1"] = flat_reason
        enriched_rows[str(symbol)] = row

    return enriched_rows


def _build_bounded_calibration_candidate_rows_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    base_rows: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        base_rows[str(symbol)] = build_bounded_calibration_candidate_row_v1(raw)

    key_counts = Counter()
    for row in base_rows.values():
        seed_state = _text(row.get("bounded_calibration_candidate_seed_state_v1")).upper()
        if seed_state not in {"TUNABLE_SEED", "MIXED_SEED"}:
            continue
        for key in list(row.get("bounded_calibration_candidate_seed_keys_v1") or []):
            key_counts.update([_text(key)])

    enriched: dict[str, dict[str, Any]] = {}
    for symbol, row in base_rows.items():
        enriched[str(symbol)] = _attach_seed_importance_fields_to_row(
            row,
            key_counts=key_counts,
        )
    candidate_catalog = _build_candidate_seed_catalog_v1(enriched)
    candidate_objects = _materialize_candidate_objects_v1(candidate_catalog, enriched)
    flattened_rows = _attach_candidate_flat_surface_to_rows_v1(enriched, candidate_objects)
    return flattened_rows, candidate_catalog, candidate_objects


def attach_bounded_calibration_candidate_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows_by_symbol, _, __ = _build_bounded_calibration_candidate_rows_v1(latest_signal_by_symbol)
    return rows_by_symbol


def build_bounded_calibration_candidate_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol, candidate_catalog, candidate_objects = _build_bounded_calibration_candidate_rows_v1(
        latest_signal_by_symbol
    )
    alignment_counts = Counter()
    source_counts = Counter()
    attached_layer_counts = Counter()
    seed_state_counts = Counter()
    seed_key_counts = Counter()
    seed_primary_key_counts = Counter()
    seed_priority_counts = Counter()
    seed_confidence_counts = Counter()
    filtering_state_counts = Counter()
    filtered_key_counts = Counter()
    candidate_symbol_counts = Counter()
    candidate_learning_key_counts = Counter()
    candidate_status_counts = Counter()
    candidate_direction_counts = Counter()
    candidate_confidence_counts = Counter()
    candidate_validation_seed_counts = Counter()
    candidate_outcome_counts = Counter()
    candidate_graduation_state_counts = Counter()
    candidate_shadow_gate_counts = Counter()
    row_primary_status_counts = Counter()
    row_primary_outcome_counts = Counter()
    row_primary_graduation_counts = Counter()
    row_primary_anchor_role_counts = Counter()
    row_primary_shadow_gate_counts = Counter()
    symbol_count = len(rows_by_symbol)
    seed_builder_ready_count = 0

    for row in rows_by_symbol.values():
        alignment_counts.update([_text(row.get("bounded_calibration_candidate_upstream_alignment_v1"))])
        source_counts.update([_text(row.get("bounded_calibration_candidate_upstream_source_v1"))])
        seed_state_counts.update([_text(row.get("bounded_calibration_candidate_seed_state_v1"))])
        for layer in list(row.get("bounded_calibration_candidate_attached_layers_v1") or []):
            attached_layer_counts.update([_text(layer)])
        for key in list(row.get("bounded_calibration_candidate_seed_keys_v1") or []):
            seed_key_counts.update([_text(key)])
        if _text(row.get("bounded_calibration_candidate_seed_primary_key_v1")):
            seed_primary_key_counts.update([_text(row.get("bounded_calibration_candidate_seed_primary_key_v1"))])
        seed_priority_counts.update([_text(row.get("bounded_calibration_candidate_seed_priority_v1"))])
        seed_confidence_counts.update([_text(row.get("bounded_calibration_candidate_seed_confidence_v1"))])
        filtering_state_counts.update([_text(row.get("bounded_calibration_candidate_filtering_state_v1"))])
        for key in list(row.get("bounded_calibration_candidate_filtered_keys_v1") or []):
            filtered_key_counts.update([_text(key)])
        row_primary_status_counts.update([_text(row.get("bounded_calibration_candidate_primary_status_v1"))])
        row_primary_outcome_counts.update([_text(row.get("bounded_calibration_candidate_primary_outcome_v1"))])
        row_primary_graduation_counts.update([_text(row.get("bounded_calibration_candidate_primary_graduation_state_v1"))])
        row_primary_anchor_role_counts.update([_text(row.get("bounded_calibration_candidate_primary_anchor_role_v1"))])
        row_primary_shadow_gate_counts.update([_text(row.get("bounded_calibration_candidate_primary_shadow_gate_state_v1"))])
        if _bool(row.get("bounded_calibration_candidate_seed_builder_ready_v1")):
            seed_builder_ready_count += 1

    for candidate in candidate_catalog.values():
        candidate_symbol_counts.update([_text(candidate.get("symbol"))])
        candidate_learning_key_counts.update([_text(candidate.get("learning_key"))])
    for candidate in candidate_objects.values():
        candidate_status_counts.update([_text(candidate.get("status"))])
        candidate_direction_counts.update([_text(candidate.get("direction"))])
        candidate_confidence_counts.update([_text(candidate.get("confidence"))])
        candidate_validation_seed_counts.update([_text(candidate.get("validation_seed_state_v1"))])
        candidate_outcome_counts.update([_text(candidate.get("candidate_outcome_v1"))])
        candidate_graduation_state_counts.update([_text(candidate.get("candidate_graduation_state_v1"))])
        candidate_shadow_gate_counts.update([_text(candidate.get("candidate_shadow_gate_state_v1"))])

    summary = {
        "generated_at": _now_iso(),
        "status": "READY" if symbol_count else "HOLD",
        "status_reasons": (
            ["bounded_calibration_candidate_upstream_surface_available"]
            if symbol_count
            else ["no_rows_for_bounded_calibration_candidate"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(symbol_count),
        "bounded_calibration_candidate_upstream_alignment_count_summary": dict(alignment_counts),
        "bounded_calibration_candidate_upstream_source_count_summary": dict(source_counts),
        "bounded_calibration_candidate_attached_layer_count_summary": dict(attached_layer_counts),
        "bounded_calibration_candidate_seed_state_count_summary": dict(seed_state_counts),
        "bounded_calibration_candidate_seed_key_count_summary": dict(seed_key_counts),
        "bounded_calibration_candidate_seed_primary_key_count_summary": dict(seed_primary_key_counts),
        "bounded_calibration_candidate_seed_priority_count_summary": dict(seed_priority_counts),
        "bounded_calibration_candidate_seed_confidence_count_summary": dict(seed_confidence_counts),
        "bounded_calibration_candidate_filtering_state_count_summary": dict(filtering_state_counts),
        "bounded_calibration_candidate_filtered_key_count_summary": dict(filtered_key_counts),
        "candidate_count": int(len(candidate_catalog)),
        "candidate_symbol_count_summary": dict(candidate_symbol_counts),
        "candidate_learning_key_count_summary": dict(candidate_learning_key_counts),
        "candidate_status_count_summary": dict(candidate_status_counts),
        "candidate_direction_count_summary": dict(candidate_direction_counts),
        "candidate_confidence_count_summary": dict(candidate_confidence_counts),
        "candidate_validation_seed_state_count_summary": dict(candidate_validation_seed_counts),
        "candidate_outcome_count_summary": dict(candidate_outcome_counts),
        "candidate_graduation_state_count_summary": dict(candidate_graduation_state_counts),
        "candidate_shadow_gate_state_count_summary": dict(candidate_shadow_gate_counts),
        "row_primary_candidate_status_count_summary": dict(row_primary_status_counts),
        "row_primary_candidate_outcome_count_summary": dict(row_primary_outcome_counts),
        "row_primary_candidate_graduation_state_count_summary": dict(row_primary_graduation_counts),
        "row_primary_candidate_anchor_role_count_summary": dict(row_primary_anchor_role_counts),
        "row_primary_candidate_shadow_gate_state_count_summary": dict(row_primary_shadow_gate_counts),
        "seed_builder_ready_count": int(seed_builder_ready_count),
    }
    return {
        "contract_version": BOUNDED_CALIBRATION_CANDIDATE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
        "candidate_catalog_v1": candidate_catalog,
        "candidate_objects_v1": candidate_objects,
    }


def render_bounded_calibration_candidate_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    rows_by_symbol = _mapping(payload.get("rows_by_symbol"))
    candidate_catalog = _mapping(payload.get("candidate_catalog_v1"))
    candidate_objects = _mapping(payload.get("candidate_objects_v1"))
    lines = [
        "# Bounded Calibration Candidate Upstream Alignment",
        "",
        f"- generated_at: {summary.get('generated_at', '')}",
        f"- status: {summary.get('status', '')}",
        f"- symbol_count: {summary.get('symbol_count', 0)}",
        "",
        "## Counts",
        f"- bounded_calibration_candidate_upstream_alignment_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_upstream_alignment_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_upstream_source_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_upstream_source_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_attached_layer_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_attached_layer_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_seed_state_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_seed_state_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_seed_key_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_seed_key_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_seed_primary_key_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_seed_primary_key_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_seed_priority_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_seed_priority_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_seed_confidence_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_seed_confidence_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_filtering_state_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_filtering_state_count_summary', {}), ensure_ascii=False)}",
        f"- bounded_calibration_candidate_filtered_key_count_summary: {json.dumps(summary.get('bounded_calibration_candidate_filtered_key_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_count: {summary.get('candidate_count', 0)}",
        f"- candidate_symbol_count_summary: {json.dumps(summary.get('candidate_symbol_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_learning_key_count_summary: {json.dumps(summary.get('candidate_learning_key_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_status_count_summary: {json.dumps(summary.get('candidate_status_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_direction_count_summary: {json.dumps(summary.get('candidate_direction_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_confidence_count_summary: {json.dumps(summary.get('candidate_confidence_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_validation_seed_state_count_summary: {json.dumps(summary.get('candidate_validation_seed_state_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_outcome_count_summary: {json.dumps(summary.get('candidate_outcome_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_graduation_state_count_summary: {json.dumps(summary.get('candidate_graduation_state_count_summary', {}), ensure_ascii=False)}",
        f"- candidate_shadow_gate_state_count_summary: {json.dumps(summary.get('candidate_shadow_gate_state_count_summary', {}), ensure_ascii=False)}",
        f"- row_primary_candidate_status_count_summary: {json.dumps(summary.get('row_primary_candidate_status_count_summary', {}), ensure_ascii=False)}",
        f"- row_primary_candidate_outcome_count_summary: {json.dumps(summary.get('row_primary_candidate_outcome_count_summary', {}), ensure_ascii=False)}",
        f"- row_primary_candidate_graduation_state_count_summary: {json.dumps(summary.get('row_primary_candidate_graduation_state_count_summary', {}), ensure_ascii=False)}",
        f"- row_primary_candidate_anchor_role_count_summary: {json.dumps(summary.get('row_primary_candidate_anchor_role_count_summary', {}), ensure_ascii=False)}",
        f"- row_primary_candidate_shadow_gate_state_count_summary: {json.dumps(summary.get('row_primary_candidate_shadow_gate_state_count_summary', {}), ensure_ascii=False)}",
        "",
        "## Rows",
    ]
    for symbol, row in rows_by_symbol.items():
        lines.append(
            f"- {symbol}: alignment={row.get('bounded_calibration_candidate_upstream_alignment_v1', '')}, "
            f"source={row.get('bounded_calibration_candidate_upstream_source_v1', '')}, "
            f"seed_state={row.get('bounded_calibration_candidate_seed_state_v1', '')}, "
            f"keys={json.dumps(row.get('bounded_calibration_candidate_seed_keys_v1', []), ensure_ascii=False)}, "
            f"primary_key={row.get('bounded_calibration_candidate_seed_primary_key_v1', '')}, "
            f"primary_importance={row.get('bounded_calibration_candidate_seed_primary_importance_v1', 0.0)}, "
            f"priority={row.get('bounded_calibration_candidate_seed_priority_v1', '')}, "
            f"confidence={row.get('bounded_calibration_candidate_seed_confidence_v1', '')}, "
            f"filtering_state={row.get('bounded_calibration_candidate_filtering_state_v1', '')}, "
            f"filtered_keys={json.dumps(row.get('bounded_calibration_candidate_filtered_keys_v1', []), ensure_ascii=False)}, "
            f"candidate_ids={json.dumps(row.get('bounded_calibration_candidate_ids_v1', []), ensure_ascii=False)}, "
            f"primary_candidate={row.get('bounded_calibration_candidate_primary_candidate_id_v1', '')}, "
            f"primary_status={row.get('bounded_calibration_candidate_primary_status_v1', '')}, "
            f"primary_outcome={row.get('bounded_calibration_candidate_primary_outcome_v1', '')}, "
            f"primary_graduation={row.get('bounded_calibration_candidate_primary_graduation_state_v1', '')}, "
            f"primary_validation={row.get('bounded_calibration_candidate_primary_validation_state_v1', '')}, "
            f"primary_anchor={row.get('bounded_calibration_candidate_primary_anchor_role_v1', '')}, "
            f"primary_shadow_gate={row.get('bounded_calibration_candidate_primary_shadow_gate_state_v1', '')}, "
            f"primary_blockers={json.dumps(row.get('bounded_calibration_candidate_primary_blockers_v1', []), ensure_ascii=False)}, "
            f"attached={json.dumps(row.get('bounded_calibration_candidate_attached_layers_v1', []), ensure_ascii=False)}, "
            f"missing={json.dumps(row.get('bounded_calibration_candidate_missing_after_attach_v1', []), ensure_ascii=False)}, "
            f"seed_ready={row.get('bounded_calibration_candidate_seed_builder_ready_v1', False)}"
        )
    lines.extend(["", "## Candidate Catalog"])
    for candidate_id, candidate in candidate_catalog.items():
        lines.append(
            f"- {candidate_id}: affected_rows={candidate.get('affected_row_count', 0)}, "
            f"pure_tunable={candidate.get('pure_tunable_count', 0)}, "
            f"mixed={candidate.get('mixed_row_count', 0)}, "
            f"fixed_overlap={candidate.get('fixed_blocker_overlap_count', 0)}, "
            f"avg_score={candidate.get('avg_filtered_key_score', 0.0)}, "
            f"avg_primary_importance={candidate.get('avg_primary_importance', 0.0)}"
        )
    lines.extend(["", "## Candidate Objects"])
    for candidate_id, candidate in candidate_objects.items():
        lines.append(
            f"- {candidate_id}: status={candidate.get('status', '')}, "
            f"direction={candidate.get('direction', '')}, "
            f"confidence={candidate.get('confidence', '')}, "
            f"priority={candidate.get('priority', '')}, "
            f"current={candidate.get('current_value', 0.0)}, "
            f"proposed={candidate.get('proposed_value', 0.0)}, "
            f"delta={candidate.get('delta', 0.0)}, "
            f"validation_state={candidate.get('validation_seed_state_v1', '')}, "
            f"outcome={candidate.get('candidate_outcome_v1', '')}, "
            f"graduation_state={candidate.get('candidate_graduation_state_v1', '')}, "
            f"shadow_gate={candidate.get('candidate_shadow_gate_state_v1', '')}, "
            f"retained_windows={len(_mapping(candidate.get('validation_scope_v1')).get('same_symbol_retained_window_ids_v1', []))}, "
            f"scope={json.dumps(_mapping(candidate.get('scope')), ensure_ascii=False)}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_bounded_calibration_candidate_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: Path | None = None,
) -> dict[str, Any]:
    report = build_bounded_calibration_candidate_summary_v1(latest_signal_by_symbol)
    output_dir = Path(shadow_auto_dir or _default_shadow_auto_dir())
    json_path = output_dir / "bounded_calibration_candidate_latest.json"
    markdown_path = output_dir / "bounded_calibration_candidate_latest.md"
    _write_json(json_path, report)
    _write_text(markdown_path, render_bounded_calibration_candidate_markdown_v1(report))
    return {
        **report,
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
        },
    }
