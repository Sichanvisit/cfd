from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.services.state_structure_dominance_profile import (
    STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
    attach_state_structure_dominance_fields_v1,
)


SYMBOL_SPECIFIC_STATE_STRENGTH_CALIBRATION_CONTRACT_VERSION = (
    "symbol_specific_state_strength_calibration_contract_v1"
)
SYMBOL_SPECIFIC_STATE_STRENGTH_CALIBRATION_SUMMARY_VERSION = (
    "symbol_specific_state_strength_calibration_summary_v1"
)

PROFILE_STATUS_ENUM_V1 = (
    "ACTIVE_CANDIDATE",
    "SEPARATE_PENDING",
    "UNCONFIGURED",
)
PROFILE_MATCH_ENUM_V1 = (
    "MATCH",
    "PARTIAL_MATCH",
    "OUT_OF_PROFILE",
    "SEPARATE_PENDING",
    "UNCONFIGURED",
)
PROFILE_BIAS_HINT_ENUM_V1 = (
    "PREFER_CONTINUATION_WITH_FRICTION",
    "CONFIRM_CONTINUATION_WITH_FRICTION",
    "KEEP_SYMBOL_SEPARATE",
    "NO_SYMBOL_BIAS",
)
PROFILE_DIRECTION_ENUM_V1 = ("UP", "DOWN", "NONE")
PROFILE_FAMILY_ENUM_V1 = ("UP_CONTINUATION", "DOWN_CONTINUATION", "UNCONFIGURED")
FLOW_SUPPORT_STATE_ENUM_V1 = (
    "FLOW_CONFIRMED",
    "FLOW_BUILDING",
    "FLOW_UNCONFIRMED",
    "FLOW_OPPOSED",
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload or {}), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _list_text(values: Any) -> list[str]:
    if isinstance(values, (list, tuple, set)):
        return [_text(value).upper() for value in values if _text(value)]
    if _text(values):
        return [_text(values).upper()]
    return []


def _normalize_profile(entry: Mapping[str, Any] | None) -> dict[str, Any]:
    profile = dict(entry or {})
    direction = _text(profile.get("direction_v1")).upper() or "NONE"
    family = _text(profile.get("family_v1")).upper() or "UNCONFIGURED"
    expected_side = _text(profile.get("expected_dominant_side_v1")).upper()
    if not expected_side:
        expected_side = "BULL" if direction == "UP" else "BEAR" if direction == "DOWN" else "NONE"
    profile["direction_v1"] = direction
    profile["family_v1"] = family
    profile["expected_dominant_side_v1"] = expected_side
    profile["acceptable_structure_biases_v1"] = _list_text(profile.get("acceptable_structure_biases_v1"))
    profile["acceptable_breakout_hold_qualities_v1"] = _list_text(
        profile.get("acceptable_breakout_hold_qualities_v1")
    )
    profile["acceptable_body_drive_states_v1"] = _list_text(profile.get("acceptable_body_drive_states_v1"))
    profile["preferred_box_states_v1"] = _list_text(profile.get("preferred_box_states_v1"))
    profile["preferred_bb_states_v1"] = _list_text(profile.get("preferred_bb_states_v1"))
    profile["source_window_ids_v1"] = list(profile.get("source_window_ids_v1") or [])
    return profile


_PROFILE_REGISTRY_V1: dict[str, list[dict[str, Any]]] = {
    "NAS100": [
        _normalize_profile(
            {
                "profile_key_v1": "NAS100_UP_CONTINUATION_BREAKOUT_HELD_V1",
                "family_v1": "UP_CONTINUATION",
                "direction_v1": "UP",
                "subtype_v1": "BREAKOUT_HELD",
                "profile_status_v1": "ACTIVE_CANDIDATE",
                "expected_dominant_side_v1": "BULL",
                "source_mode_v1": "retained_window_numeric_audit_snapshot_v1",
                "source_artifact_stem_v1": "nas_screenshot_numeric_audit_latest",
                "source_window_ids_v1": [
                    "nas_overlap_core_continuation_1",
                    "nas_overlap_core_continuation_2",
                ],
                "continuation_integrity_floor_hint_v1": 0.95,
                "reversal_evidence_ceiling_hint_v1": 0.05,
                "preferred_veto_tier_v1": "FRICTION_ONLY",
                "acceptable_structure_biases_v1": ["CONTINUATION_FAVOR", "MIXED"],
                "acceptable_breakout_hold_qualities_v1": ["STABLE", "STRONG"],
                "acceptable_body_drive_states_v1": ["WEAK_DRIVE", "STRONG_DRIVE"],
                "preferred_box_states_v1": ["ABOVE"],
                "preferred_bb_states_v1": ["UPPER_EDGE", "BREAKOUT", "UPPER"],
                "discount_policy_v1": "ENABLE_WHEN_STRUCTURAL_SUPPORT_HIGH",
                "dominant_mode_bias_v1": "PREFER_CONTINUATION_WITH_FRICTION_OVER_BOUNDARY",
                "notes_v1": (
                    "Derived from retained NAS screenshot overlap windows where structural support stayed near 1.0 "
                    "while consumer caution stayed opposite-side heavy."
                ),
            }
        ),
        _normalize_profile(
            {
                "profile_key_v1": "NAS100_DOWN_CONTINUATION_PENDING_V1",
                "family_v1": "DOWN_CONTINUATION",
                "direction_v1": "DOWN",
                "subtype_v1": "PENDING_REVIEW",
                "profile_status_v1": "SEPARATE_PENDING",
                "expected_dominant_side_v1": "BEAR",
                "source_mode_v1": "manual_timebox_calibration_pending",
                "preferred_veto_tier_v1": "SEPARATE_PENDING",
                "discount_policy_v1": "SEPARATE_PENDING",
                "dominant_mode_bias_v1": "SEPARATE_PENDING",
                "notes_v1": "NAS100 down continuation needs its own retained screenshot/timebox calibration.",
            }
        ),
    ],
    "XAUUSD": [
        _normalize_profile(
            {
                "profile_key_v1": "XAUUSD_UP_CONTINUATION_RECOVERY_V1",
                "family_v1": "UP_CONTINUATION",
                "direction_v1": "UP",
                "subtype_v1": "RECOVERY_RECLAIM",
                "profile_status_v1": "ACTIVE_CANDIDATE",
                "expected_dominant_side_v1": "BULL",
                "source_mode_v1": "retained_window_log_review_v1",
                "source_artifact_stem_v1": "xau_manual_log_review_snapshot_v1",
                "source_window_ids_v1": [
                    "xau_up_recovery_1_0200_0300",
                    "xau_up_recovery_2_0500_0642",
                ],
                "continuation_integrity_floor_hint_v1": 0.72,
                "reversal_evidence_ceiling_hint_v1": 0.25,
                "preferred_veto_tier_v1": "FRICTION_ONLY",
                "acceptable_structure_biases_v1": ["CONTINUATION_FAVOR", "MIXED"],
                "acceptable_breakout_hold_qualities_v1": ["STABLE", "STRONG"],
                "acceptable_body_drive_states_v1": ["WEAK_DRIVE", "STRONG_DRIVE"],
                "preferred_box_states_v1": ["LOWER", "MIDDLE", "ABOVE"],
                "preferred_bb_states_v1": ["UNKNOWN", "UPPER_EDGE", "BREAKOUT", "UPPER", "MIDDLE"],
                "discount_policy_v1": "ENABLE_WHEN_RECOVERY_STRUCTURE_AND_SELL_PROBE_OVERFIRE",
                "dominant_mode_bias_v1": "PREFER_CONTINUATION_WITH_FRICTION_OVER_BOUNDARY",
                "notes_v1": (
                    "Built from XAU recovery windows where leg and breakout direction stayed UP while "
                    "upper_reject_probe_observe and wrong_side_sell_pressure overfired."
                ),
            }
        ),
        _normalize_profile(
            {
                "profile_key_v1": "XAUUSD_DOWN_CONTINUATION_REJECTION_V1",
                "family_v1": "DOWN_CONTINUATION",
                "direction_v1": "DOWN",
                "subtype_v1": "UPPER_REJECT_REJECTION",
                "profile_status_v1": "ACTIVE_CANDIDATE",
                "expected_dominant_side_v1": "BEAR",
                "source_mode_v1": "retained_window_log_review_v1",
                "source_artifact_stem_v1": "xau_manual_log_review_snapshot_v1",
                "source_window_ids_v1": [
                    "xau_down_core_1_0030_0200",
                    "xau_down_core_2_0330_0430",
                ],
                "continuation_integrity_floor_hint_v1": 0.70,
                "reversal_evidence_ceiling_hint_v1": 0.25,
                "preferred_veto_tier_v1": "FRICTION_ONLY",
                "acceptable_structure_biases_v1": ["CONTINUATION_FAVOR", "MIXED"],
                "acceptable_breakout_hold_qualities_v1": ["WEAK", "STABLE", "STRONG"],
                "acceptable_body_drive_states_v1": ["WEAK_DRIVE", "STRONG_DRIVE"],
                "preferred_box_states_v1": ["ABOVE", "MIDDLE"],
                "preferred_bb_states_v1": ["UPPER_EDGE", "BREAKOUT", "UNKNOWN", "UPPER"],
                "discount_policy_v1": "LIMIT_DISCOUNT_WHEN_REJECTION_CONTINUATION_CONFIRMED",
                "dominant_mode_bias_v1": "CONFIRM_CONTINUATION_WITH_FRICTION",
                "notes_v1": (
                    "Built from XAU down continuation windows where upper rejection kept aligning with "
                    "SELL continuation rather than acting as bull friction."
                ),
            }
        ),
    ],
    "BTCUSD": [
        _normalize_profile(
            {
                "profile_key_v1": "BTCUSD_UP_CONTINUATION_LOWER_RECOVERY_PENDING_V1",
                "family_v1": "UP_CONTINUATION",
                "direction_v1": "UP",
                "subtype_v1": "LOWER_RECOVERY_REBOUND",
                "profile_status_v1": "SEPARATE_PENDING",
                "expected_dominant_side_v1": "BULL",
                "source_mode_v1": "screenshot_overlap_numeric_audit_pending",
                "source_artifact_stem_v1": "btc_screenshot_numeric_audit_latest",
                "source_window_ids_v1": [
                    "btc_up_recovery_0500_0701",
                    "btc_up_reclaim_0125_0310",
                ],
                "preferred_veto_tier_v1": "SEPARATE_PENDING",
                "discount_policy_v1": "REVIEW_LOWER_RECOVERY_BIAS_AFTER_MORE_WINDOWS",
                "dominant_mode_bias_v1": "SEPARATE_PENDING",
                "notes_v1": (
                    "BTCUSD up continuation overlap exists around lower recovery and reclaim windows, "
                    "but current retained numeric audit is still mixed, so this remains pending."
                ),
            }
        ),
        _normalize_profile(
            {
                "profile_key_v1": "BTCUSD_DOWN_CONTINUATION_UPPER_DRIFT_PENDING_V1",
                "family_v1": "DOWN_CONTINUATION",
                "direction_v1": "DOWN",
                "subtype_v1": "UPPER_DRIFT_FADE",
                "profile_status_v1": "SEPARATE_PENDING",
                "expected_dominant_side_v1": "BEAR",
                "source_mode_v1": "screenshot_overlap_numeric_audit_pending",
                "source_artifact_stem_v1": "btc_screenshot_numeric_audit_latest",
                "source_window_ids_v1": [
                    "btc_down_drift_0333_0525",
                    "btc_down_pre_midnight_tail",
                ],
                "preferred_veto_tier_v1": "SEPARATE_PENDING",
                "discount_policy_v1": "REVIEW_UPPER_DRIFT_FADE_AFTER_MORE_WINDOWS",
                "dominant_mode_bias_v1": "SEPARATE_PENDING",
                "notes_v1": (
                    "BTCUSD down continuation appears in screenshot drift/fade scenes, but retained overlap "
                    "does not yet separate it cleanly from mixed or recovery structure."
                ),
            }
        ),
    ],
}


def build_symbol_specific_state_strength_calibration_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SYMBOL_SPECIFIC_STATE_STRENGTH_CALIBRATION_CONTRACT_VERSION,
        "status": "READY",
        "profile_status_enum_v1": list(PROFILE_STATUS_ENUM_V1),
        "profile_match_enum_v1": list(PROFILE_MATCH_ENUM_V1),
        "profile_bias_hint_enum_v1": list(PROFILE_BIAS_HINT_ENUM_V1),
        "profile_direction_enum_v1": list(PROFILE_DIRECTION_ENUM_V1),
        "profile_family_enum_v1": list(PROFILE_FAMILY_ENUM_V1),
        "flow_support_state_enum_v1": list(FLOW_SUPPORT_STATE_ENUM_V1),
        "row_level_fields_v1": [
            "symbol_specific_state_strength_profile_v1",
            "symbol_state_strength_best_profile_key_v1",
            "symbol_state_strength_profile_key_v1",
            "symbol_state_strength_profile_family_v1",
            "symbol_state_strength_profile_direction_v1",
            "symbol_state_strength_profile_subtype_v1",
            "symbol_state_strength_profile_status_v1",
            "symbol_state_strength_profile_match_v1",
            "symbol_state_strength_aggregate_conviction_v1",
            "symbol_state_strength_flow_persistence_v1",
            "symbol_state_strength_flow_support_state_v1",
            "symbol_state_strength_bias_hint_v1",
            "symbol_state_strength_flow_reason_summary_v1",
            "symbol_state_strength_profile_reason_summary_v1",
        ],
        "principles": [
            "Calibration is common in framework but separated by symbol, direction, and structure subtype",
            "Every symbol can have both up and down continuation families",
            "Values learned on one symbol do not get copied blindly to another symbol",
            "Exact profile match and aggregated directional flow can coexist without being treated as the same thing",
            "If state evidence keeps flowing in one direction strongly enough, flow support can be surfaced even outside an exact pilot profile",
            "Calibration is read-only and does not change execution or state25",
        ],
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_dominance(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    flat_present = any(
        key in row
        for key in (
            "state_strength_continuation_integrity_v1",
            "state_strength_reversal_evidence_v1",
            "dominance_shadow_dominant_side_v1",
            "dominance_shadow_dominant_mode_v1",
            "consumer_veto_tier_v1",
        )
    )
    if not isinstance(row.get("state_structure_dominance_profile_v1"), Mapping):
        if flat_present:
            row["state_structure_dominance_profile_v1"] = {
                "contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
                "dominance_shadow_dominant_side_v1": _text(row.get("dominance_shadow_dominant_side_v1")).upper(),
                "dominance_shadow_dominant_mode_v1": _text(row.get("dominance_shadow_dominant_mode_v1")).upper(),
                "dominance_shadow_caution_level_v1": _text(row.get("dominance_shadow_caution_level_v1")).upper(),
                "dominance_shadow_gap_v1": row.get("dominance_shadow_gap_v1"),
                "local_continuation_discount_v1": row.get("local_continuation_discount_v1"),
            }
        else:
            row = dict(attach_state_structure_dominance_fields_v1({"_": row}).get("_", row))
    return row


def _profiles_for_symbol(symbol: str) -> list[dict[str, Any]]:
    return [dict(profile) for profile in (_PROFILE_REGISTRY_V1.get(_text(symbol).upper()) or [])]


def _row_side(row: Mapping[str, Any]) -> str:
    for key in ("dominance_shadow_dominant_side_v1", "state_strength_dominant_side_v1", "state_strength_side_seed_v1"):
        value = _text(row.get(key)).upper()
        if value in {"BULL", "BEAR"}:
            return value
    direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    if direction == "UP":
        return "BULL"
    if direction == "DOWN":
        return "BEAR"
    return "NONE"


def _row_direction(row: Mapping[str, Any]) -> str:
    side = _row_side(row)
    if side == "BULL":
        return "UP"
    if side == "BEAR":
        return "DOWN"
    return "NONE"


def _matches_allowed(value: Any, allowed: Iterable[str]) -> bool:
    allowed_set = {item for item in (_text(item).upper() for item in allowed) if item}
    if not allowed_set:
        return True
    return _text(value).upper() in allowed_set


def _evaluate_active_profile(profile: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    row_side = _row_side(row)
    continuation = _float(row.get("state_strength_continuation_integrity_v1"), 0.0)
    reversal = _float(row.get("state_strength_reversal_evidence_v1"), 0.0)
    veto_tier = _text(row.get("consumer_veto_tier_v1")).upper()
    structure_bias = _text(row.get("few_candle_structure_bias_v1")).upper()
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    body_drive = _text(row.get("body_drive_state_v1")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()

    expected_side = _text(profile.get("expected_dominant_side_v1")).upper()
    floor_hint = _float(profile.get("continuation_integrity_floor_hint_v1"), 0.0)
    ceiling_hint = _float(profile.get("reversal_evidence_ceiling_hint_v1"), 1.0)
    side_match = row_side == expected_side

    score = 0.0
    reasons: list[str] = []
    if side_match:
        score += 0.45
        reasons.append("side_match")
    else:
        reasons.append("side_mismatch")

    if continuation >= floor_hint:
        score += 0.2
        reasons.append("continuation_above_floor")
    elif continuation >= max(0.0, floor_hint - 0.12):
        score += 0.1
        reasons.append("continuation_near_floor")

    if reversal <= ceiling_hint:
        score += 0.15
        reasons.append("reversal_below_ceiling")
    elif reversal <= min(1.0, ceiling_hint + 0.12):
        score += 0.05
        reasons.append("reversal_near_ceiling")

    if _text(profile.get("preferred_veto_tier_v1")).upper() == veto_tier:
        score += 0.08
        reasons.append("preferred_veto_match")
    if _matches_allowed(structure_bias, profile.get("acceptable_structure_biases_v1") or []):
        score += 0.04
        reasons.append("structure_bias_acceptable")
    if _matches_allowed(breakout_hold, profile.get("acceptable_breakout_hold_qualities_v1") or []):
        score += 0.03
        reasons.append("breakout_hold_acceptable")
    if _matches_allowed(body_drive, profile.get("acceptable_body_drive_states_v1") or []):
        score += 0.02
        reasons.append("body_drive_acceptable")
    if _matches_allowed(box_state, profile.get("preferred_box_states_v1") or []):
        score += 0.015
        reasons.append("box_state_preferred")
    if _matches_allowed(bb_state, profile.get("preferred_bb_states_v1") or []):
        score += 0.015
        reasons.append("bb_state_preferred")

    score = round(min(score, 1.0), 4)
    if side_match and continuation >= floor_hint and reversal <= ceiling_hint and score >= 0.78:
        match_state = "MATCH"
    elif side_match and continuation >= max(0.0, floor_hint - 0.12) and reversal <= min(1.0, ceiling_hint + 0.12) and score >= 0.55:
        match_state = "PARTIAL_MATCH"
    else:
        match_state = "OUT_OF_PROFILE"

    return {
        "profile": dict(profile),
        "score_v1": score,
        "match_state_v1": match_state,
        "reason_tokens_v1": reasons,
    }


def _evaluate_pending_profile(profile: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    row_direction = _row_direction(row)
    profile_direction = _text(profile.get("direction_v1")).upper()
    direction_match = row_direction == profile_direction
    score = 0.55 if direction_match else (0.2 if row_direction == "NONE" else 0.05)
    reasons = ["pending_direction_match" if direction_match else "pending_direction_review"]
    return {
        "profile": dict(profile),
        "score_v1": round(score, 4),
        "match_state_v1": "SEPARATE_PENDING",
        "reason_tokens_v1": reasons,
    }


def _evaluate_profile(profile: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    status = _text(profile.get("profile_status_v1")).upper()
    if status == "ACTIVE_CANDIDATE":
        return _evaluate_active_profile(profile, row)
    if status == "SEPARATE_PENDING":
        return _evaluate_pending_profile(profile, row)
    return {
        "profile": dict(profile),
        "score_v1": 0.0,
        "match_state_v1": "UNCONFIGURED",
        "reason_tokens_v1": ["unconfigured_profile"],
    }


def _choose_profile(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    if not evaluations:
        return {
            "profile": {},
            "score_v1": 0.0,
            "match_state_v1": "UNCONFIGURED",
            "reason_tokens_v1": ["no_profile_registry_entry"],
        }
    return max(
        evaluations,
        key=lambda item: (
            2
            if _text(item.get("match_state_v1")).upper() == "MATCH"
            else 1
            if _text(item.get("match_state_v1")).upper() == "PARTIAL_MATCH"
            else 0
            if _text(item.get("match_state_v1")).upper() == "SEPARATE_PENDING"
            else -1,
            _float(item.get("score_v1"), 0.0),
        ),
    )


def _candidate_surface(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for evaluation in evaluations:
        profile = _mapping(evaluation.get("profile"))
        candidates.append(
            {
                "profile_key_v1": _text(profile.get("profile_key_v1")),
                "family_v1": _text(profile.get("family_v1")).upper(),
                "direction_v1": _text(profile.get("direction_v1")).upper(),
                "subtype_v1": _text(profile.get("subtype_v1")).upper(),
                "profile_status_v1": _text(profile.get("profile_status_v1")).upper(),
                "match_state_v1": _text(evaluation.get("match_state_v1")).upper(),
                "score_v1": round(_float(evaluation.get("score_v1"), 0.0), 4),
                "reason_tokens_v1": list(evaluation.get("reason_tokens_v1") or []),
            }
        )
    candidates.sort(
        key=lambda item: (_float(item.get("score_v1"), 0.0), _text(item.get("profile_key_v1"))),
        reverse=True,
    )
    return candidates


def _bias_hint(selected_profile: Mapping[str, Any], row: Mapping[str, Any], *, match_state: str) -> str:
    status = _text(selected_profile.get("profile_status_v1")).upper()
    if status == "SEPARATE_PENDING":
        return "KEEP_SYMBOL_SEPARATE"
    if status != "ACTIVE_CANDIDATE":
        return "NO_SYMBOL_BIAS"

    mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    mode_bias = _text(selected_profile.get("dominant_mode_bias_v1")).upper()
    if match_state in {"MATCH", "PARTIAL_MATCH"} and mode == "BOUNDARY" and "PREFER_CONTINUATION_WITH_FRICTION" in mode_bias:
        return "PREFER_CONTINUATION_WITH_FRICTION"
    if match_state in {"MATCH", "PARTIAL_MATCH"} and mode == "CONTINUATION_WITH_FRICTION":
        return "CONFIRM_CONTINUATION_WITH_FRICTION"
    return "NO_SYMBOL_BIAS"


def _flow_structure_score(row: Mapping[str, Any]) -> float:
    structure_bias = _text(row.get("few_candle_structure_bias_v1")).upper()
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    body_drive = _text(row.get("body_drive_state_v1")).upper()

    structure_score = {
        "CONTINUATION_FAVOR": 1.0,
        "MIXED": 0.65,
        "REVERSAL_FAVOR": 0.15,
    }.get(structure_bias, 0.35)
    hold_score = {
        "STRONG": 1.0,
        "STABLE": 0.8,
        "WEAK": 0.45,
        "FAILED": 0.0,
    }.get(breakout_hold, 0.25)
    drive_score = {
        "STRONG_DRIVE": 1.0,
        "WEAK_DRIVE": 0.7,
        "NEUTRAL": 0.35,
        "COUNTER_DRIVE": 0.0,
    }.get(body_drive, 0.2)
    return round((structure_score * 0.4) + (hold_score * 0.35) + (drive_score * 0.25), 4)


def _flow_mode_score(row: Mapping[str, Any]) -> float:
    mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    veto_tier = _text(row.get("consumer_veto_tier_v1")).upper()
    base = {
        "CONTINUATION": 1.0,
        "CONTINUATION_WITH_FRICTION": 0.88,
        "BOUNDARY": 0.45,
        "REVERSAL_RISK": 0.0,
    }.get(mode, 0.25)
    if veto_tier == "REVERSAL_OVERRIDE":
        base *= 0.2
    elif veto_tier == "BOUNDARY_WARNING":
        base *= 0.75
    return round(base, 4)


def _flow_conviction_metrics(selected_profile: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    expected_side = _text(selected_profile.get("expected_dominant_side_v1")).upper()
    row_side = _row_side(row)
    side_match = row_side == expected_side and expected_side in {"BULL", "BEAR"}
    continuation = max(0.0, min(1.0, _float(row.get("state_strength_continuation_integrity_v1"), 0.0)))
    reversal = max(0.0, min(1.0, _float(row.get("state_strength_reversal_evidence_v1"), 0.0)))
    gap = _float(row.get("dominance_shadow_gap_v1"), _float(row.get("state_strength_dominance_gap_v1"), 0.0))
    floor_hint = max(0.0, min(1.0, _float(selected_profile.get("continuation_integrity_floor_hint_v1"), 0.0)))
    ceiling_hint = max(0.0, min(1.0, _float(selected_profile.get("reversal_evidence_ceiling_hint_v1"), 1.0)))
    structure_score = _flow_structure_score(row)
    mode_score = _flow_mode_score(row)

    if side_match:
        gap_support = max(0.0, min(1.0, gap))
        floor_support = max(0.0, min(1.0, continuation / floor_hint)) if floor_hint > 0 else continuation
        ceiling_support = (
            max(0.0, min(1.0, 1.0 - (reversal / ceiling_hint))) if ceiling_hint > 0 else (1.0 - reversal)
        )
        aggregate = (
            continuation * 0.28
            + (1.0 - reversal) * 0.24
            + gap_support * 0.18
            + structure_score * 0.18
            + mode_score * 0.12
        )
        persistence = (
            structure_score * 0.55
            + mode_score * 0.25
            + floor_support * 0.12
            + ceiling_support * 0.08
        )
    else:
        aggregate = 0.12 + (continuation * 0.08)
        persistence = 0.1

    aggregate = round(max(0.0, min(1.0, aggregate)), 4)
    persistence = round(max(0.0, min(1.0, persistence)), 4)

    if not side_match:
        state = "FLOW_OPPOSED"
    elif aggregate >= 0.7 and persistence >= 0.6:
        state = "FLOW_CONFIRMED"
    elif aggregate >= 0.58 and persistence >= 0.45:
        state = "FLOW_BUILDING"
    else:
        state = "FLOW_UNCONFIRMED"

    reason = (
        f"expected_side={expected_side.lower() or 'none'}; "
        f"row_side={row_side.lower() or 'none'}; "
        f"continuation={round(continuation, 4)}; "
        f"reversal={round(reversal, 4)}; "
        f"gap={round(gap, 4)}; "
        f"structure_score={structure_score}; "
        f"mode_score={mode_score}; "
        f"aggregate={aggregate}; "
        f"persistence={persistence}; "
        f"flow_state={state.lower()}"
    )
    return {
        "aggregate_conviction_v1": aggregate,
        "flow_persistence_v1": persistence,
        "flow_support_state_v1": state,
        "flow_reason_summary_v1": reason,
    }


def build_symbol_specific_state_strength_calibration_row_v1(
    row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _ensure_dominance(row or {})
    symbol = _text(payload.get("symbol")).upper()
    profiles = _profiles_for_symbol(symbol)
    evaluations = [_evaluate_profile(profile, payload) for profile in profiles]
    selected = _choose_profile(evaluations)
    selected_profile = _mapping(selected.get("profile"))
    status = _text(selected_profile.get("profile_status_v1")).upper() or "UNCONFIGURED"
    match_state = _text(selected.get("match_state_v1")).upper() or "UNCONFIGURED"
    bias_hint = _bias_hint(selected_profile, payload, match_state=match_state)
    flow_metrics = _flow_conviction_metrics(selected_profile, payload)

    continuation = round(_float(payload.get("state_strength_continuation_integrity_v1"), 0.0), 4)
    reversal = round(_float(payload.get("state_strength_reversal_evidence_v1"), 0.0), 4)
    score = round(_float(selected.get("score_v1"), 0.0), 4)
    reason_summary = (
        f"symbol={symbol}; "
        f"family={_text(selected_profile.get('family_v1')).lower()}; "
        f"direction={_text(selected_profile.get('direction_v1')).lower()}; "
        f"subtype={_text(selected_profile.get('subtype_v1')).lower()}; "
        f"profile_status={status.lower()}; "
        f"match={match_state.lower()}; "
        f"bias_hint={bias_hint.lower()}; "
        f"score={score}; "
        f"continuation={continuation}; "
        f"reversal={reversal}; "
        f"aggregate={flow_metrics['aggregate_conviction_v1']}; "
        f"persistence={flow_metrics['flow_persistence_v1']}; "
        f"flow_state={_text(flow_metrics['flow_support_state_v1']).lower()}"
    )

    candidate_profiles = _candidate_surface(evaluations)
    selected_payload = {
        "profile_key_v1": _text(selected_profile.get("profile_key_v1")),
        "family_v1": _text(selected_profile.get("family_v1")).upper(),
        "direction_v1": _text(selected_profile.get("direction_v1")).upper(),
        "subtype_v1": _text(selected_profile.get("subtype_v1")).upper(),
        "profile_status_v1": status,
        "match_state_v1": match_state,
        "score_v1": score,
        "expected_dominant_side_v1": _text(selected_profile.get("expected_dominant_side_v1")).upper(),
        "continuation_integrity_floor_hint_v1": selected_profile.get("continuation_integrity_floor_hint_v1"),
        "reversal_evidence_ceiling_hint_v1": selected_profile.get("reversal_evidence_ceiling_hint_v1"),
        "preferred_veto_tier_v1": _text(selected_profile.get("preferred_veto_tier_v1")).upper(),
        "discount_policy_v1": _text(selected_profile.get("discount_policy_v1")),
        "dominant_mode_bias_v1": _text(selected_profile.get("dominant_mode_bias_v1")),
        "source_mode_v1": _text(selected_profile.get("source_mode_v1")),
        "source_artifact_stem_v1": _text(selected_profile.get("source_artifact_stem_v1")),
        "source_window_ids_v1": list(selected_profile.get("source_window_ids_v1") or []),
        "notes_v1": _text(selected_profile.get("notes_v1")),
        "reason_tokens_v1": list(selected.get("reason_tokens_v1") or []),
        "aggregate_conviction_v1": flow_metrics["aggregate_conviction_v1"],
        "flow_persistence_v1": flow_metrics["flow_persistence_v1"],
        "flow_support_state_v1": flow_metrics["flow_support_state_v1"],
        "flow_reason_summary_v1": flow_metrics["flow_reason_summary_v1"],
    }

    profile_payload = {
        "contract_version": SYMBOL_SPECIFIC_STATE_STRENGTH_CALIBRATION_CONTRACT_VERSION,
        "upstream_contract_version": STATE_STRUCTURE_DOMINANCE_CONTRACT_VERSION,
        "symbol_state_strength_profile_catalog_v1": candidate_profiles,
        "symbol_state_strength_selected_profile_v1": selected_payload,
        "symbol_state_strength_profile_count_v1": len(candidate_profiles),
        "symbol_state_strength_bias_hint_v1": bias_hint,
        "symbol_state_strength_aggregate_conviction_v1": flow_metrics["aggregate_conviction_v1"],
        "symbol_state_strength_flow_persistence_v1": flow_metrics["flow_persistence_v1"],
        "symbol_state_strength_flow_support_state_v1": flow_metrics["flow_support_state_v1"],
        "symbol_state_strength_flow_reason_summary_v1": flow_metrics["flow_reason_summary_v1"],
        "symbol_state_strength_profile_reason_summary_v1": reason_summary,
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "symbol_specific_state_strength_profile_v1": profile_payload,
        "symbol_state_strength_best_profile_key_v1": _text(selected_profile.get("profile_key_v1")),
        "symbol_state_strength_profile_key_v1": _text(selected_profile.get("profile_key_v1")),
        "symbol_state_strength_profile_family_v1": _text(selected_profile.get("family_v1")).upper(),
        "symbol_state_strength_profile_direction_v1": _text(selected_profile.get("direction_v1")).upper(),
        "symbol_state_strength_profile_subtype_v1": _text(selected_profile.get("subtype_v1")).upper(),
        "symbol_state_strength_profile_status_v1": status,
        "symbol_state_strength_profile_match_v1": match_state,
        "symbol_state_strength_bias_hint_v1": bias_hint,
        "symbol_state_strength_aggregate_conviction_v1": flow_metrics["aggregate_conviction_v1"],
        "symbol_state_strength_flow_persistence_v1": flow_metrics["flow_persistence_v1"],
        "symbol_state_strength_flow_support_state_v1": flow_metrics["flow_support_state_v1"],
        "symbol_state_strength_continuation_floor_hint_v1": selected_profile.get("continuation_integrity_floor_hint_v1"),
        "symbol_state_strength_reversal_ceiling_hint_v1": selected_profile.get("reversal_evidence_ceiling_hint_v1"),
        "symbol_state_strength_preferred_veto_tier_v1": _text(selected_profile.get("preferred_veto_tier_v1")).upper(),
        "symbol_state_strength_discount_policy_v1": _text(selected_profile.get("discount_policy_v1")),
        "symbol_state_strength_dominant_mode_bias_v1": _text(selected_profile.get("dominant_mode_bias_v1")),
        "symbol_state_strength_source_mode_v1": _text(selected_profile.get("source_mode_v1")),
        "symbol_state_strength_source_artifact_stem_v1": _text(selected_profile.get("source_artifact_stem_v1")),
        "symbol_state_strength_flow_reason_summary_v1": flow_metrics["flow_reason_summary_v1"],
        "symbol_state_strength_profile_reason_summary_v1": reason_summary,
    }


def attach_symbol_specific_state_strength_calibration_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_dominance(raw)
        row.update(build_symbol_specific_state_strength_calibration_row_v1(row))
        enriched[str(symbol)] = row
    return enriched


def build_symbol_specific_state_strength_calibration_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
) -> dict[str, Any]:
    rows_by_symbol = attach_symbol_specific_state_strength_calibration_fields_v1(latest_signal_by_symbol)
    status_counts = Counter()
    match_counts = Counter()
    bias_counts = Counter()
    family_counts = Counter()
    direction_counts = Counter()
    flow_state_counts = Counter()
    surface_ready_count = 0
    aggregate_total = 0.0
    persistence_total = 0.0

    for row in rows_by_symbol.values():
        if isinstance(row.get("symbol_specific_state_strength_profile_v1"), Mapping):
            surface_ready_count += 1
        status_counts.update([_text(row.get("symbol_state_strength_profile_status_v1"))])
        match_counts.update([_text(row.get("symbol_state_strength_profile_match_v1"))])
        bias_counts.update([_text(row.get("symbol_state_strength_bias_hint_v1"))])
        family_counts.update([_text(row.get("symbol_state_strength_profile_family_v1"))])
        direction_counts.update([_text(row.get("symbol_state_strength_profile_direction_v1"))])
        flow_state_counts.update([_text(row.get("symbol_state_strength_flow_support_state_v1"))])
        aggregate_total += _float(row.get("symbol_state_strength_aggregate_conviction_v1"), 0.0)
        persistence_total += _float(row.get("symbol_state_strength_flow_persistence_v1"), 0.0)

    status = "READY" if rows_by_symbol and surface_ready_count == len(rows_by_symbol) else "HOLD"
    symbol_count = int(len(rows_by_symbol))
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["symbol_direction_subtype_profiles_surface_available"]
            if status == "READY"
            else ["symbol_direction_subtype_surface_missing_or_no_rows"]
        ),
        "symbol_count": symbol_count,
        "surface_ready_count": int(surface_ready_count),
        "profile_status_count_summary": dict(status_counts),
        "profile_match_count_summary": dict(match_counts),
        "flow_support_state_count_summary": dict(flow_state_counts),
        "bias_hint_count_summary": dict(bias_counts),
        "profile_family_count_summary": dict(family_counts),
        "profile_direction_count_summary": dict(direction_counts),
        "active_candidate_count": int(status_counts.get("ACTIVE_CANDIDATE", 0)),
        "separate_pending_count": int(status_counts.get("SEPARATE_PENDING", 0)),
        "avg_aggregate_conviction_v1": round(aggregate_total / symbol_count, 4) if symbol_count else None,
        "avg_flow_persistence_v1": round(persistence_total / symbol_count, 4) if symbol_count else None,
    }
    return {
        "contract_version": SYMBOL_SPECIFIC_STATE_STRENGTH_CALIBRATION_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_symbol_specific_state_strength_calibration_markdown_v1(
    report: Mapping[str, Any] | None,
) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Symbol Specific State Strength Calibration",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- status: `{summary.get('status', '')}`",
        f"- symbol_count: `{int(summary.get('symbol_count', 0) or 0)}`",
        f"- active_candidate_count: `{int(summary.get('active_candidate_count', 0) or 0)}`",
        f"- separate_pending_count: `{int(summary.get('separate_pending_count', 0) or 0)}`",
        "",
        "## Symbol Rows",
        "",
    ]
    for symbol, raw in dict(payload.get("rows_by_symbol") or {}).items():
        row = _mapping(raw)
        lines.append(
            f"- `{symbol}`: family={row.get('symbol_state_strength_profile_family_v1', '')} | "
            f"direction={row.get('symbol_state_strength_profile_direction_v1', '')} | "
            f"subtype={row.get('symbol_state_strength_profile_subtype_v1', '')} | "
            f"status={row.get('symbol_state_strength_profile_status_v1', '')} | "
            f"match={row.get('symbol_state_strength_profile_match_v1', '')} | "
            f"flow={row.get('symbol_state_strength_flow_support_state_v1', '')} | "
            f"aggregate={row.get('symbol_state_strength_aggregate_conviction_v1', '')} | "
            f"persistence={row.get('symbol_state_strength_flow_persistence_v1', '')} | "
            f"bias={row.get('symbol_state_strength_bias_hint_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_symbol_specific_state_strength_calibration_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_symbol_specific_state_strength_calibration_summary_v1(latest_signal_by_symbol)
    json_path = output_dir / "symbol_specific_state_strength_calibration_latest.json"
    md_path = output_dir / "symbol_specific_state_strength_calibration_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_symbol_specific_state_strength_calibration_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
