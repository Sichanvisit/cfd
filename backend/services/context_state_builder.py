"""
Context state builder v1.2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from backend.services.trade_csv_schema import now_kst_dt

KST = ZoneInfo("Asia/Seoul")

CONTEXT_STATE_VERSION = "context_state_v1_2"
CONFLICT_CONTEXT_VERSION = "conflict_context_v1_2"
SHARE_CONTEXT_VERSION = "share_context_v1"
LATE_CHASE_VERSION = "late_chase_v1"

_CONFLICT_PRIORITY = {
    "AGAINST_PREV_BOX_AND_HTF": 0,
    "LATE_CHASE_RISK": 1,
    "AGAINST_HTF": 2,
    "AGAINST_PREV_BOX": 3,
    "CONTEXT_MIXED": 4,
    "NONE": 5,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_side(side: Any) -> str:
    text = str(side or "").upper().strip()
    if text in {"BUY", "SELL", "WAIT", "NONE"}:
        return text
    return "NONE"


def _side_sign(side: str) -> int:
    if str(side) == "BUY":
        return 1
    if str(side) == "SELL":
        return -1
    return 0


def _trend_sign(direction: Any) -> int:
    text = str(direction or "").upper().strip()
    if text == "UPTREND":
        return 1
    if text == "DOWNTREND":
        return -1
    return 0


def _severity_rank(level: str | None) -> int:
    norm = str(level or "").upper().strip()
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(norm, 0)


def _confidence_rank(level: str | None) -> int:
    norm = str(level or "").upper().strip()
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(norm, 0)


def _max_intensity(*levels: str | None) -> str:
    ranked = sorted((_severity_rank(level), str(level or "").upper().strip()) for level in levels)
    highest = ranked[-1][1] if ranked else ""
    return highest if highest in {"LOW", "MEDIUM", "HIGH"} else "LOW"


def _infer_share_band(share_value: float | None) -> str | None:
    if share_value is None:
        return None
    value = float(share_value)
    if value >= 0.8:
        return "DOMINANT"
    if value >= 0.6:
        return "COMMON"
    if value >= 0.3:
        return "OCCASIONAL"
    return "RARE"


def _share_label_ko(share_band: str | None) -> str | None:
    norm = str(share_band or "").upper().strip()
    return {
        "DOMINANT": "내부 지배 장면",
        "COMMON": "반복도 높은 장면",
        "OCCASIONAL": "가끔 반복되는 장면",
        "RARE": "드문 장면",
    }.get(norm)


def _detect_against_htf(side: str, htf_state: Mapping[str, Any]) -> tuple[bool, str | None]:
    side_sign = _side_sign(side)
    if side_sign == 0:
        return False, None
    higher = []
    for prefix in ("1h", "4h", "1d"):
        direction = _trend_sign(htf_state.get(f"trend_{prefix}_direction"))
        strength_score = abs(_to_float(htf_state.get(f"trend_{prefix}_strength_score"), 0.0))
        higher.append((direction, strength_score))
    opposite_scores = [score for direction, score in higher if direction == (-1 * side_sign)]
    if not opposite_scores:
        return False, None
    if len(opposite_scores) >= 3 and (sum(opposite_scores) / len(opposite_scores)) >= 2.0:
        return True, "HIGH"
    if len(opposite_scores) >= 2 and (sum(opposite_scores) / len(opposite_scores)) >= 1.0:
        return True, "MEDIUM"
    return True, "LOW"


def _detect_against_previous_box(side: str, previous_box_state: Mapping[str, Any]) -> tuple[bool, str | None]:
    side_sign = _side_sign(side)
    if side_sign == 0:
        return False, None
    relation = str(previous_box_state.get("previous_box_relation") or "").upper().strip()
    break_state = str(previous_box_state.get("previous_box_break_state") or "").upper().strip()
    confidence = str(previous_box_state.get("previous_box_confidence") or "").upper().strip()
    if side_sign < 0:
        conflict = break_state == "BREAKOUT_HELD" or relation in {"ABOVE", "AT_HIGH"}
    else:
        conflict = break_state == "BREAKDOWN_HELD" or relation in {"BELOW", "AT_LOW"}
    if not conflict:
        return False, None
    if confidence == "HIGH":
        return True, "HIGH"
    if confidence == "MEDIUM":
        return True, "MEDIUM"
    return True, "LOW"


def _detect_context_mixed(side: str, htf_state: Mapping[str, Any], previous_box_state: Mapping[str, Any]) -> bool:
    if _side_sign(side) == 0:
        return str(htf_state.get("htf_alignment_state") or "").upper().strip() == "MIXED_HTF"
    htf_mixed = str(htf_state.get("htf_alignment_state") or "").upper().strip() == "MIXED_HTF"
    prev_conf = str(previous_box_state.get("previous_box_confidence") or "").upper().strip()
    prev_lifecycle = str(previous_box_state.get("previous_box_lifecycle") or "").upper().strip()
    return bool(htf_mixed or prev_conf == "LOW" or prev_lifecycle == "INVALIDATED")


def _detect_late_chase(side: str, htf_state: Mapping[str, Any], previous_box_state: Mapping[str, Any], proxy_state: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    confidence_scores: list[float] = []

    distance_above = _to_float(previous_box_state.get("distance_from_previous_box_high_pct"), 0.0)
    break_state = str(previous_box_state.get("previous_box_break_state") or "").upper().strip()
    relation = str(previous_box_state.get("previous_box_relation") or "").upper().strip()
    same_color_run = int(proxy_state.get("same_color_run_current") or proxy_state.get("micro_same_color_run_current") or 0)
    pullback_ratio = proxy_state.get("pullback_ratio")
    pullback_ratio = None if pullback_ratio is None else _to_float(pullback_ratio, 1.0)
    strength_1h = abs(_to_float(htf_state.get("trend_1h_strength_score"), 0.0))
    trend_1h_direction = str(htf_state.get("trend_1h_direction") or "").upper().strip()
    trend_15m_direction = str(htf_state.get("trend_15m_direction") or "").upper().strip()

    if side == "BUY" and relation == "ABOVE" and distance_above > 1.5:
        reasons.append("EXTENDED_ABOVE_PREV_BOX")
        confidence_scores.append(min(1.0, distance_above / 3.0))

    if pullback_ratio is not None and pullback_ratio < 0.25:
        reasons.append("AGAINST_PULLBACK_DEPTH")
        confidence_scores.append(min(1.0, (0.25 - pullback_ratio) / 0.25 + 0.35))

    if side == "BUY" and trend_1h_direction == "UPTREND" and trend_15m_direction == "UPTREND" and strength_1h >= 2.0 and relation == "ABOVE":
        reasons.append("HTF_ALREADY_EXTENDED")
        confidence_scores.append(min(1.0, strength_1h / 3.0))

    if side == "BUY" and break_state == "BREAKOUT_HELD" and same_color_run >= 5:
        reasons.append("MULTI_BAR_RUN_AFTER_BREAK")
        confidence_scores.append(min(1.0, same_color_run / 8.0))

    trigger_count = int(len(reasons))
    if trigger_count == 0:
        return {
            "late_chase_risk_state": "NONE",
            "late_chase_reason": None,
            "late_chase_confidence": 0.0,
            "late_chase_trigger_count": 0,
        }

    confidence = max(confidence_scores) if confidence_scores else 0.0
    risk_state = "HIGH" if (trigger_count >= 2 or confidence >= 0.75) else "EARLY_WARNING"
    reason = reasons[0]
    return {
        "late_chase_risk_state": str(risk_state),
        "late_chase_reason": str(reason),
        "late_chase_confidence": float(round(confidence, 4)),
        "late_chase_trigger_count": int(trigger_count),
    }


def _primary_conflict_from_flags(flags: list[str]) -> str:
    if "AGAINST_HTF" in flags and "AGAINST_PREV_BOX" in flags:
        return "AGAINST_PREV_BOX_AND_HTF"
    if "LATE_CHASE_RISK" in flags:
        return "LATE_CHASE_RISK"
    if "AGAINST_HTF" in flags:
        return "AGAINST_HTF"
    if "AGAINST_PREV_BOX" in flags:
        return "AGAINST_PREV_BOX"
    if "CONTEXT_MIXED" in flags:
        return "CONTEXT_MIXED"
    return "NONE"


def _conflict_label_ko(primary: str, intensity: str) -> str:
    base = {
        "AGAINST_PREV_BOX_AND_HTF": "직전 박스와 상위 추세 모두 역행",
        "LATE_CHASE_RISK": "늦은 추격 위험",
        "AGAINST_HTF": "상위 추세 역행",
        "AGAINST_PREV_BOX": "직전 박스 흐름 역행",
        "CONTEXT_MIXED": "맥락 혼조",
        "NONE": "맥락 정합",
    }.get(str(primary), "맥락 혼조")
    if str(primary) == "NONE":
        return base
    suffix = {"LOW": "약함", "MEDIUM": "중간", "HIGH": "강함"}.get(str(intensity), "")
    return f"{base} ({suffix})" if suffix else base


def build_context_state_v12(
    *,
    symbol: str,
    consumer_check_side: str | None = None,
    htf_state: Mapping[str, Any] | None = None,
    previous_box_state: Mapping[str, Any] | None = None,
    share_state: Mapping[str, Any] | None = None,
    proxy_state: Mapping[str, Any] | None = None,
    built_at: datetime | None = None,
) -> dict[str, Any]:
    now_dt = built_at or now_kst_dt()
    if getattr(now_dt, "tzinfo", None) is None:
        now_dt = now_dt.replace(tzinfo=KST)

    symbol_key = str(symbol or "").upper().strip()
    side = _normalize_side(consumer_check_side)
    htf_map = dict(htf_state or {})
    previous_box_map = dict(previous_box_state or {})
    share_map = dict(share_state or {})
    proxy_map = dict(proxy_state or {})

    against_htf, htf_intensity = _detect_against_htf(side, htf_map)
    against_prev_box, prev_box_intensity = _detect_against_previous_box(side, previous_box_map)
    mixed = _detect_context_mixed(side, htf_map, previous_box_map)
    late_chase = _detect_late_chase(side, htf_map, previous_box_map, proxy_map)

    flags: list[str] = []
    if against_htf:
        flags.append("AGAINST_HTF")
    if against_prev_box:
        flags.append("AGAINST_PREV_BOX")
    if late_chase["late_chase_risk_state"] != "NONE":
        flags.append("LATE_CHASE_RISK")
    if mixed and not flags:
        flags.append("CONTEXT_MIXED")

    primary = _primary_conflict_from_flags(flags)

    late_conf = float(late_chase["late_chase_confidence"])
    late_intensity = "HIGH" if late_chase["late_chase_risk_state"] == "HIGH" else ("MEDIUM" if late_chase["late_chase_risk_state"] == "EARLY_WARNING" else None)
    conflict_intensity = _max_intensity(htf_intensity, prev_box_intensity, late_intensity)
    if primary == "NONE":
        conflict_intensity = "LOW"

    score = 0.0
    if primary != "NONE":
        score += {"LOW": 0.35, "MEDIUM": 0.65, "HIGH": 0.9}.get(conflict_intensity, 0.35)
        if "AGAINST_HTF" in flags:
            score += 0.15
        if "AGAINST_PREV_BOX" in flags:
            score += 0.15
        if "LATE_CHASE_RISK" in flags:
            score += min(0.2, late_conf * 0.2)
    score = float(round(min(1.0, score), 4))

    share_value = share_map.get("cluster_share_symbol")
    share_value = None if share_value in (None, "") else _to_float(share_value, 0.0)
    share_band = str(share_map.get("cluster_share_symbol_band") or _infer_share_band(share_value) or "").upper().strip() or None
    share_label_ko = str(share_map.get("share_context_label_ko") or _share_label_ko(share_band) or "") or None

    payload: dict[str, Any] = {
        "symbol": symbol_key,
        "consumer_check_side": side,
        "context_state_version": CONTEXT_STATE_VERSION,
        "htf_context_version": str(htf_map.get("htf_context_version") or htf_map.get("htf_state_version") or "htf_context_v1"),
        "previous_box_context_version": str(
            previous_box_map.get("previous_box_context_version")
            or previous_box_map.get("previous_box_state_version")
            or "previous_box_context_v1"
        ),
        "conflict_context_version": CONFLICT_CONTEXT_VERSION,
        "share_context_version": SHARE_CONTEXT_VERSION,
        "context_state_built_at": now_dt.isoformat(),
        "context_conflict_state": str(primary),
        "context_conflict_flags": list(flags),
        "context_conflict_intensity": str(conflict_intensity),
        "context_conflict_score": float(score),
        "context_conflict_label_ko": _conflict_label_ko(primary, conflict_intensity),
        "late_chase_risk_state": str(late_chase["late_chase_risk_state"]),
        "late_chase_reason": late_chase["late_chase_reason"],
        "late_chase_confidence": float(late_chase["late_chase_confidence"]),
        "late_chase_trigger_count": int(late_chase["late_chase_trigger_count"]),
        "cluster_share_global": share_map.get("cluster_share_global"),
        "cluster_share_symbol": share_value,
        "cluster_share_symbol_band": share_band,
        "share_context_label_ko": share_label_ko,
    }

    payload.update(htf_map)
    payload.update(previous_box_map)
    return payload
