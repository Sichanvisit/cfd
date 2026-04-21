from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.state_slot_commonization_judge import (
    COMMONIZATION_VERDICT_ENUM_V1,
)
from backend.services.symbol_specific_state_strength_calibration import (
    attach_symbol_specific_state_strength_calibration_fields_v1,
)
from backend.services.xau_readonly_surface_contract import (
    attach_xau_readonly_surface_fields_v1,
)


STATE_SLOT_SYMBOL_EXTENSION_SURFACE_CONTRACT_VERSION = (
    "state_slot_symbol_extension_surface_contract_v1"
)
STATE_SLOT_SYMBOL_EXTENSION_SURFACE_SUMMARY_VERSION = (
    "state_slot_symbol_extension_surface_summary_v1"
)

SYMBOL_EXTENSION_STATE_ENUM_V1 = (
    "XAU_PILOT",
    "NAS_STAGE_EXTENSION",
    "BTC_RECOVERY_DRIFT_EXTENSION",
    "UNMAPPED",
)
VOCABULARY_COMPATIBILITY_ENUM_V1 = (
    "COMPATIBLE",
    "REVIEW_PENDING",
    "UNMAPPED",
)
XAU_SLOT_MATCH_ENUM_V1 = (
    "XAU_PILOT_SLOT",
    "MATCHED_XAU_VALIDATED_SLOT",
    "UNSEEN_IN_XAU",
    "UNMAPPED",
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


def build_state_slot_symbol_extension_surface_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": STATE_SLOT_SYMBOL_EXTENSION_SURFACE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only symbol extension surface for the common state slot vocabulary. "
            "Projects XAU-proven decomposition language onto NAS100 and BTCUSD rows so we can see "
            "whether the same core slot and modifier grammar holds across symbols before lifecycle rollout."
        ),
        "symbol_extension_state_enum_v1": list(SYMBOL_EXTENSION_STATE_ENUM_V1),
        "vocabulary_compatibility_enum_v1": list(VOCABULARY_COMPATIBILITY_ENUM_V1),
        "xau_slot_match_enum_v1": list(XAU_SLOT_MATCH_ENUM_V1),
        "xau_commonization_verdict_enum_v1": list(COMMONIZATION_VERDICT_ENUM_V1),
        "row_level_fields_v1": [
            "state_slot_symbol_extension_surface_profile_v1",
            "state_slot_symbol_extension_state_v1",
            "common_state_polarity_slot_v1",
            "common_state_intent_slot_v1",
            "common_state_continuation_stage_v1",
            "common_state_rejection_type_v1",
            "common_state_texture_slot_v1",
            "common_state_location_context_v1",
            "common_state_tempo_profile_v1",
            "common_state_ambiguity_level_v1",
            "common_state_slot_core_v1",
            "common_state_slot_modifier_bundle_v1",
            "common_vocabulary_compatibility_v1",
            "xau_commonization_slot_match_v1",
            "xau_commonization_verdict_v1",
            "common_state_slot_reason_summary_v1",
        ],
        "control_rules_v1": [
            "extension surface is read-only and does not change execution or state25",
            "xau exact slot match and common vocabulary compatibility are separate concepts",
            "nas extension focuses on continuation stage and extension readability",
            "btc extension focuses on recovery and drift readability",
            "decomposition extension cannot change dominant_side",
        ],
        "dominance_protection_v1": {
            "symbol_extension_can_change_dominant_side": False,
            "side_change_owned_by": "dominance_layer_only",
        },
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }


def _ensure_symbol_profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("symbol_specific_state_strength_profile_v1"), Mapping):
        return row
    if any(
        key in row
        for key in (
            "symbol_state_strength_best_profile_key_v1",
            "symbol_state_strength_profile_key_v1",
            "symbol_state_strength_profile_family_v1",
            "symbol_state_strength_profile_subtype_v1",
            "symbol_state_strength_profile_status_v1",
            "symbol_state_strength_profile_match_v1",
        )
    ):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_symbol_specific_state_strength_calibration_fields_v1({symbol: row}).get(symbol, row))


def _ensure_xau_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_mapping(payload))
    if isinstance(row.get("xau_readonly_surface_profile_v1"), Mapping):
        return row
    symbol = _text(row.get("symbol") or row.get("ticker") or "_")
    return dict(attach_xau_readonly_surface_fields_v1({symbol: row}).get(symbol, row))


def _commonization_index(state_slot_commonization_judge_report: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    catalog = list(_mapping(state_slot_commonization_judge_report).get("slot_catalog_v1") or [])
    index: dict[str, dict[str, Any]] = {}
    for row in catalog:
        payload = _mapping(row)
        slot_core = _text(payload.get("state_slot_core_v1"))
        if slot_core:
            index[slot_core] = payload
    return index


def _resolve_generic_polarity_intent(row: Mapping[str, Any]) -> tuple[str, str]:
    family = _text(row.get("symbol_state_strength_profile_family_v1")).upper()
    subtype = _text(row.get("symbol_state_strength_profile_subtype_v1")).upper()
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    consumer_side = _text(row.get("consumer_check_side")).upper()
    dominant_side = _text(
        row.get("dominance_shadow_dominant_side_v1")
        or row.get("state_strength_dominant_side_v1")
    ).upper()
    overlay_direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    chart_hint = _text(row.get("chart_event_kind_hint")).upper()
    previous_break_state = _text(row.get("previous_box_break_state")).upper()
    previous_relation = _text(row.get("previous_box_relation")).upper()

    if family == "UP_CONTINUATION":
        if any(token in subtype for token in ("RECOVERY", "REBOUND", "RECLAIM")) or any(
            token in consumer_reason for token in ("rebound", "reclaim", "recovery")
        ):
            return "BULL", "RECOVERY"
        return "BULL", "CONTINUATION"

    if family == "DOWN_CONTINUATION":
        bullish_recovery_bias = any(
            token in subtype or token in consumer_reason
            for token in ("RECOVERY", "REBOUND", "RECLAIM", "recovery", "rebound", "reclaim", "lower_")
        )
        supportive_buy_context = (
            consumer_side == "BUY"
            or dominant_side == "BULL"
            or overlay_direction == "UP"
            or chart_hint in {"BUY_WATCH", "BUY_WAIT", "BUY_PROBE"}
        )
        breakdown_still_held = previous_break_state == "BREAKDOWN_HELD" and previous_relation in {"BELOW", "AT_LOW"}
        if bullish_recovery_bias and supportive_buy_context and not breakdown_still_held:
            return "BULL", "RECOVERY"
        if "REJECTION" in subtype or "reject" in consumer_reason:
            return "BEAR", "REJECTION"
        return "BEAR", "CONTINUATION"

    return "NONE", "BOUNDARY"


def _nas_pending_review_bullish_override(row: Mapping[str, Any]) -> bool:
    symbol = _text(row.get("symbol")).upper()
    if symbol != "NAS100":
        return False
    family = _text(row.get("symbol_state_strength_profile_family_v1")).upper()
    status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    dominant_side = _text(
        row.get("dominance_shadow_dominant_side_v1")
        or row.get("state_strength_dominant_side_v1")
    ).upper()
    htf_alignment_state = _text(row.get("htf_alignment_state")).upper()
    break_state = _text(row.get("previous_box_break_state")).upper()
    relation = _text(row.get("previous_box_relation")).upper()
    breakout_direction = _text(
        row.get("breakout_candidate_direction") or row.get("breakout_direction")
    ).upper()
    breakout_target = _text(row.get("breakout_candidate_action_target")).upper()
    overlay_direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    overlay_score = _float(row.get("directional_continuation_overlay_score"), 0.0)
    chart_event_kind_hint = _text(row.get("chart_event_kind_hint")).upper()
    trend_15m = _text(row.get("trend_15m_direction")).upper()
    trend_1h = _text(row.get("trend_1h_direction")).upper()
    trend_4h = _text(row.get("trend_4h_direction")).upper()

    if family != "DOWN_CONTINUATION":
        return False
    if status not in {"SEPARATE_PENDING", "ACTIVE_CANDIDATE"} and match != "SEPARATE_PENDING":
        return False
    if dominant_side != "BULL":
        return False
    if htf_alignment_state != "WITH_HTF":
        return False
    if break_state not in {"BREAKOUT_HELD", "RECLAIMED"}:
        return False
    if relation not in {"ABOVE", "AT_HIGH"}:
        return False
    bullish_breakout_candidate = breakout_direction == "UP" and breakout_target in {
        "WATCH_BREAKOUT",
        "PROBE_BREAKOUT",
        "ENTER_NOW",
    }
    bullish_watch_overlay = (
        overlay_direction == "UP"
        and overlay_score >= 0.75
        and chart_event_kind_hint == "BUY_WATCH"
    )
    if not bullish_breakout_candidate and not bullish_watch_overlay:
        return False
    return trend_15m == "UPTREND" and trend_1h == "UPTREND" and trend_4h == "UPTREND"


def _resolve_generic_stage(row: Mapping[str, Any], *, symbol: str, intent: str) -> str:
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    subtype = _text(row.get("symbol_state_strength_profile_subtype_v1")).upper()

    if symbol == "NAS100":
        if bb_state in {"UPPER", "LOWER"} and box_state in {"ABOVE", "BELOW"}:
            return "EXTENSION"
        if breakout_hold in {"STABLE", "STRONG"}:
            return "ACCEPTANCE"
        return "INITIATION"

    if symbol == "BTCUSD":
        if intent == "RECOVERY":
            if "probe" in consumer_reason or breakout_hold in {"", "FAILED", "WEAK"}:
                return "INITIATION"
            if breakout_hold in {"STABLE", "STRONG"}:
                return "ACCEPTANCE"
            return "INITIATION"
        if any(token in subtype for token in ("DRIFT", "FADE")):
            if bb_state in {"UPPER", "LOWER"} and box_state in {"ABOVE", "BELOW"}:
                return "EXTENSION"
            return "ACCEPTANCE"

    if intent in {"CONTINUATION", "RECOVERY", "REJECTION"}:
        if "probe" in consumer_reason:
            return "INITIATION"
        if breakout_hold in {"STABLE", "STRONG"}:
            return "ACCEPTANCE"
        return "INITIATION"
    return "NONE"


def _resolve_generic_rejection_type(row: Mapping[str, Any], *, intent: str) -> str:
    consumer_reason = _text(row.get("consumer_check_reason")).lower()
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    if intent != "REJECTION" and "reject" not in consumer_reason:
        return "NONE"
    if previous_box_break_state == "BREAKDOWN_HELD" or breakout_hold == "FAILED":
        return "REVERSAL_REJECTION"
    if "reject" in consumer_reason or "probe" in consumer_reason:
        return "FRICTION_REJECTION"
    return "NONE"


def _resolve_generic_texture(row: Mapping[str, Any], *, stage: str, rejection_type: str) -> str:
    subtype = _text(row.get("symbol_state_strength_profile_subtype_v1")).upper()
    dominant_mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    veto_tier = _text(row.get("consumer_veto_tier_v1")).upper()
    if any(token in subtype for token in ("DRIFT", "FADE")):
        return "DRIFT"
    if rejection_type == "FRICTION_REJECTION":
        return "WITH_FRICTION"
    if dominant_mode == "CONTINUATION_WITH_FRICTION" or veto_tier == "FRICTION_ONLY":
        return "WITH_FRICTION"
    if dominant_mode == "BOUNDARY" and stage != "EXTENSION":
        return "DRIFT"
    return "CLEAN"


def _resolve_generic_location(row: Mapping[str, Any]) -> str:
    previous_box_break_state = _text(row.get("previous_box_break_state")).upper()
    box_state = _text(row.get("box_state")).upper()
    bb_state = _text(row.get("bb_state")).upper()
    if previous_box_break_state in {"BREAKOUT_HELD", "BREAKDOWN_HELD"}:
        return "POST_BREAKOUT"
    if box_state in {"ABOVE", "BELOW"} and bb_state in {"UPPER", "LOWER", "UPPER_EDGE", "LOWER_EDGE"}:
        return "AT_EDGE"
    if bb_state in {"UPPER", "LOWER"}:
        return "EXTENDED"
    return "IN_BOX"


def _resolve_generic_tempo(row: Mapping[str, Any], *, stage: str, texture: str) -> str:
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    if texture == "DRIFT":
        return "REPEATING"
    if stage == "INITIATION":
        return "EARLY"
    if stage == "EXTENSION":
        return "EXTENDED"
    if breakout_hold in {"STABLE", "STRONG"}:
        return "PERSISTING"
    return "PERSISTING"


def _resolve_generic_ambiguity(row: Mapping[str, Any]) -> str:
    dominant_mode = _text(row.get("dominance_shadow_dominant_mode_v1")).upper()
    family = _text(row.get("symbol_state_strength_profile_family_v1")).upper()
    subtype = _text(row.get("symbol_state_strength_profile_subtype_v1")).upper()
    profile_match = _text(row.get("symbol_state_strength_profile_match_v1")).upper()
    structure_bias = _text(row.get("few_candle_structure_bias_v1")).upper()
    breakout_hold = _text(row.get("breakout_hold_quality_v1")).upper()
    previous_break_state = _text(row.get("previous_box_break_state")).upper()
    previous_relation = _text(row.get("previous_box_relation")).upper()
    dominant_side = _text(
        row.get("dominance_shadow_dominant_side_v1")
        or row.get("state_strength_dominant_side_v1")
    ).upper()
    consumer_side = _text(row.get("consumer_check_side")).upper()
    overlay_direction = _text(row.get("directional_continuation_overlay_direction")).upper()
    chart_hint = _text(row.get("chart_event_kind_hint")).upper()
    trend_1h = _text(row.get("trend_1h_direction")).upper()
    trend_4h = _text(row.get("trend_4h_direction")).upper()

    boundary_softening = False
    if dominant_mode == "BOUNDARY":
        if family == "UP_CONTINUATION":
            bullish_recovery_context = any(token in subtype for token in ("RECOVERY", "REBOUND", "RECLAIM"))
            bullish_support = (
                dominant_side == "BULL"
                or consumer_side == "BUY"
                or overlay_direction == "UP"
                or chart_hint in {"BUY_WATCH", "BUY_WAIT", "BUY_PROBE"}
                or (bullish_recovery_context and trend_1h == "UPTREND" and trend_4h == "UPTREND")
            )
            bullish_location = (
                previous_break_state in {"BREAKOUT_HELD", "RECLAIMED"}
                and previous_relation in {"ABOVE", "AT_HIGH"}
            )
            boundary_softening = bullish_support and (
                bullish_location or breakout_hold in {"WEAK", "STABLE", "STRONG"}
            )
        elif family == "DOWN_CONTINUATION":
            bearish_support = (
                dominant_side == "BEAR"
                or consumer_side == "SELL"
                or overlay_direction == "DOWN"
                or chart_hint in {"SELL_WATCH", "SELL_WAIT", "SELL_PROBE"}
            )
            bearish_location = (
                previous_break_state in {"BREAKDOWN_HELD", "REJECTED"}
                and previous_relation in {"BELOW", "AT_LOW"}
            )
            boundary_softening = bearish_support and (
                bearish_location or breakout_hold in {"WEAK", "STABLE", "STRONG"}
            )
    if dominant_mode == "BOUNDARY":
        if boundary_softening:
            return "MEDIUM"
        return "HIGH"
    if profile_match in {"PARTIAL_MATCH", "SEPARATE_PENDING"} or structure_bias == "MIXED":
        return "MEDIUM"
    return "LOW"


def _build_generic_row(symbol: str, row: Mapping[str, Any]) -> dict[str, Any]:
    polarity, intent = _resolve_generic_polarity_intent(row)
    if _nas_pending_review_bullish_override(row):
        polarity, intent = "BULL", "CONTINUATION"
    stage = _resolve_generic_stage(row, symbol=symbol, intent=intent)
    rejection_type = _resolve_generic_rejection_type(row, intent=intent)
    texture = _resolve_generic_texture(row, stage=stage, rejection_type=rejection_type)
    location = _resolve_generic_location(row)
    tempo = _resolve_generic_tempo(row, stage=stage, texture=texture)
    ambiguity = _resolve_generic_ambiguity(row)
    state_slot_core = (
        f"{polarity}_{intent}_{stage}"
        if polarity not in {"", "NONE"} and intent not in {"", "BOUNDARY"} and stage not in {"", "NONE"}
        else ""
    )
    modifiers = [value for value in (texture, location, tempo, f"AMBIGUITY_{ambiguity}") if value]
    extension_state = "NAS_STAGE_EXTENSION" if symbol == "NAS100" else "BTC_RECOVERY_DRIFT_EXTENSION"
    return {
        "state_slot_symbol_extension_state_v1": extension_state,
        "common_state_polarity_slot_v1": polarity,
        "common_state_intent_slot_v1": intent,
        "common_state_continuation_stage_v1": stage,
        "common_state_rejection_type_v1": rejection_type,
        "common_state_texture_slot_v1": texture,
        "common_state_location_context_v1": location,
        "common_state_tempo_profile_v1": tempo,
        "common_state_ambiguity_level_v1": ambiguity,
        "common_state_slot_core_v1": state_slot_core,
        "common_state_slot_modifier_bundle_v1": modifiers,
    }


def _build_xau_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "state_slot_symbol_extension_state_v1": "XAU_PILOT",
        "common_state_polarity_slot_v1": _text(row.get("xau_polarity_slot_v1")).upper(),
        "common_state_intent_slot_v1": _text(row.get("xau_intent_slot_v1")).upper(),
        "common_state_continuation_stage_v1": _text(row.get("xau_continuation_stage_v1")).upper(),
        "common_state_rejection_type_v1": _text(row.get("xau_rejection_type_v1")).upper(),
        "common_state_texture_slot_v1": _text(row.get("xau_texture_slot_v1")).upper(),
        "common_state_location_context_v1": _text(row.get("xau_location_context_v1")).upper(),
        "common_state_tempo_profile_v1": _text(row.get("xau_tempo_profile_v1")).upper(),
        "common_state_ambiguity_level_v1": _text(row.get("xau_ambiguity_level_v1")).upper(),
        "common_state_slot_core_v1": _text(row.get("xau_state_slot_core_v1")).upper(),
        "common_state_slot_modifier_bundle_v1": list(row.get("xau_state_slot_modifier_bundle_v1") or []),
    }


def _compatibility_state(row: Mapping[str, Any], surface: Mapping[str, Any]) -> str:
    slot_core = _text(surface.get("common_state_slot_core_v1"))
    profile_status = _text(row.get("symbol_state_strength_profile_status_v1")).upper()
    if not slot_core:
        return "UNMAPPED"
    if profile_status == "SEPARATE_PENDING":
        return "REVIEW_PENDING"
    return "COMPATIBLE"


def _xau_slot_match(surface: Mapping[str, Any], commonization_index: Mapping[str, Any], *, symbol: str) -> tuple[str, str, bool]:
    slot_core = _text(surface.get("common_state_slot_core_v1"))
    if not slot_core:
        return ("UNMAPPED", "", False)
    if symbol == "XAUUSD":
        verdict = _text(_mapping(commonization_index.get(slot_core)).get("commonization_verdict_v1"))
        threshold = bool(_mapping(commonization_index.get(slot_core)).get("threshold_specificity_required_v1"))
        return ("XAU_PILOT_SLOT", verdict, threshold)
    match = _mapping(commonization_index.get(slot_core))
    if match:
        return (
            "MATCHED_XAU_VALIDATED_SLOT",
            _text(match.get("commonization_verdict_v1")),
            bool(match.get("threshold_specificity_required_v1")),
        )
    return ("UNSEEN_IN_XAU", "", False)


def build_state_slot_symbol_extension_surface_row_v1(
    row: Mapping[str, Any] | None,
    *,
    state_slot_commonization_judge_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _ensure_symbol_profile(row or {})
    symbol = _text(payload.get("symbol")).upper()
    if symbol == "XAUUSD":
        payload = _ensure_xau_surface(payload)
        surface = _build_xau_row(payload)
    elif symbol in {"NAS100", "BTCUSD"}:
        surface = _build_generic_row(symbol, payload)
    else:
        profile = {
            "contract_version": STATE_SLOT_SYMBOL_EXTENSION_SURFACE_CONTRACT_VERSION,
            "applicable_v1": False,
            "execution_change_allowed": False,
            "state25_change_allowed": False,
        }
        return {
            "state_slot_symbol_extension_surface_profile_v1": profile,
            "state_slot_symbol_extension_state_v1": "UNMAPPED",
            "common_state_polarity_slot_v1": "",
            "common_state_intent_slot_v1": "",
            "common_state_continuation_stage_v1": "",
            "common_state_rejection_type_v1": "",
            "common_state_texture_slot_v1": "",
            "common_state_location_context_v1": "",
            "common_state_tempo_profile_v1": "",
            "common_state_ambiguity_level_v1": "",
            "common_state_slot_core_v1": "",
            "common_state_slot_modifier_bundle_v1": [],
            "common_vocabulary_compatibility_v1": "UNMAPPED",
            "xau_commonization_slot_match_v1": "UNMAPPED",
            "xau_commonization_verdict_v1": "",
            "xau_commonization_threshold_specificity_required_v1": False,
            "common_state_slot_reason_summary_v1": "symbol_not_supported_for_d10_extension",
        }

    commonization_index = _commonization_index(state_slot_commonization_judge_report)
    compatibility = _compatibility_state(payload, surface)
    slot_match, verdict, threshold_required = _xau_slot_match(surface, commonization_index, symbol=symbol)
    reason = (
        f"symbol={symbol}; extension={surface.get('state_slot_symbol_extension_state_v1', '')}; "
        f"slot={surface.get('common_state_slot_core_v1', '')}; compatibility={compatibility}; "
        f"xau_slot_match={slot_match}; verdict={verdict or 'none'}"
    )
    profile = {
        "contract_version": STATE_SLOT_SYMBOL_EXTENSION_SURFACE_CONTRACT_VERSION,
        "applicable_v1": True,
        **surface,
        "common_vocabulary_compatibility_v1": compatibility,
        "xau_commonization_slot_match_v1": slot_match,
        "xau_commonization_verdict_v1": verdict,
        "xau_commonization_threshold_specificity_required_v1": bool(threshold_required),
        "execution_change_allowed": False,
        "state25_change_allowed": False,
    }
    return {
        "state_slot_symbol_extension_surface_profile_v1": profile,
        **surface,
        "common_vocabulary_compatibility_v1": compatibility,
        "xau_commonization_slot_match_v1": slot_match,
        "xau_commonization_verdict_v1": verdict,
        "xau_commonization_threshold_specificity_required_v1": bool(threshold_required),
        "common_state_slot_reason_summary_v1": reason,
    }


def attach_state_slot_symbol_extension_surface_fields_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    state_slot_commonization_judge_report: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for symbol, raw in dict(latest_signal_by_symbol or {}).items():
        row = _ensure_symbol_profile(raw)
        if _text(row.get("symbol")).upper() == "XAUUSD":
            row = _ensure_xau_surface(row)
        row.update(
            build_state_slot_symbol_extension_surface_row_v1(
                row,
                state_slot_commonization_judge_report=state_slot_commonization_judge_report,
            )
        )
        enriched[str(symbol)] = row
    return enriched


def build_state_slot_symbol_extension_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    state_slot_commonization_judge_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows_by_symbol = attach_state_slot_symbol_extension_surface_fields_v1(
        latest_signal_by_symbol,
        state_slot_commonization_judge_report=state_slot_commonization_judge_report,
    )
    extension_counts = Counter()
    compatibility_counts = Counter()
    slot_match_counts = Counter()
    core_counts = Counter()
    ready_symbols = 0
    for row in rows_by_symbol.values():
        extension_counts.update([_text(row.get("state_slot_symbol_extension_state_v1"))])
        compatibility_counts.update([_text(row.get("common_vocabulary_compatibility_v1"))])
        slot_match_counts.update([_text(row.get("xau_commonization_slot_match_v1"))])
        core_counts.update([_text(row.get("common_state_slot_core_v1"))])
        if _text(row.get("common_vocabulary_compatibility_v1")) in {"COMPATIBLE", "REVIEW_PENDING"}:
            ready_symbols += 1
    symbol_count = len(rows_by_symbol)
    status = "READY" if symbol_count and ready_symbols >= 3 else "HOLD"
    summary = {
        "generated_at": _now_iso(),
        "status": status,
        "status_reasons": (
            ["common_state_slot_language_visible_on_all_symbols"]
            if status == "READY"
            else ["nas_btc_extension_surface_still_partial"]
        ),
        "symbol_count": int(symbol_count),
        "surface_ready_count": int(ready_symbols),
        "symbol_extension_state_count_summary": dict(extension_counts),
        "common_vocabulary_compatibility_count_summary": dict(compatibility_counts),
        "xau_slot_match_count_summary": dict(slot_match_counts),
        "core_slot_count_summary": dict(core_counts),
    }
    return {
        "contract_version": STATE_SLOT_SYMBOL_EXTENSION_SURFACE_SUMMARY_VERSION,
        "summary": summary,
        "rows_by_symbol": rows_by_symbol,
    }


def render_state_slot_symbol_extension_surface_markdown_v1(report: Mapping[str, Any] | None) -> str:
    payload = _mapping(report)
    summary = _mapping(payload.get("summary"))
    lines = [
        "# State Slot Symbol Extension Surface v1",
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
            f"- `{symbol}`: extension={row.get('state_slot_symbol_extension_state_v1', '')} | "
            f"slot={row.get('common_state_slot_core_v1', '')} | "
            f"compatibility={row.get('common_vocabulary_compatibility_v1', '')} | "
            f"xau_match={row.get('xau_commonization_slot_match_v1', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def generate_and_write_state_slot_symbol_extension_surface_summary_v1(
    latest_signal_by_symbol: Mapping[str, Any] | None,
    *,
    state_slot_commonization_judge_report: Mapping[str, Any] | None = None,
    shadow_auto_dir: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(shadow_auto_dir) if shadow_auto_dir is not None else _default_shadow_auto_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_state_slot_symbol_extension_surface_summary_v1(
        latest_signal_by_symbol,
        state_slot_commonization_judge_report=state_slot_commonization_judge_report,
    )
    json_path = output_dir / "state_slot_symbol_extension_surface_latest.json"
    md_path = output_dir / "state_slot_symbol_extension_surface_latest.md"
    _write_json(json_path, report)
    _write_text(md_path, render_state_slot_symbol_extension_surface_markdown_v1(report))
    return {
        "summary": _mapping(report.get("summary")),
        "rows_by_symbol": _mapping(report.get("rows_by_symbol")),
        "artifact_paths": {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        },
    }
