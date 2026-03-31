"""Human-readable market view summaries for runtime status UI."""

from __future__ import annotations

from typing import Any


_ZONE_LABELS = {
    "ABOVE": "상단 밖",
    "UPPER": "상단",
    "UPPER_EDGE": "상단 근접",
    "MIDDLE": "중앙",
    "LOWER_EDGE": "하단 근접",
    "LOWER": "하단",
    "BELOW": "하단 밖",
    "UNKNOWN": "미확인",
}

_MARKET_MODE_LABELS = {
    "RANGE": "박스장",
    "TREND": "추세장",
    "EXPANSION": "확장장",
    "LOW_LIQUIDITY": "저유동성",
    "SHOCK": "충격장",
}

_LIQUIDITY_LABELS = {
    "GOOD": "양호",
    "NORMAL": "보통",
    "THIN": "얇음",
    "LOW": "낮음",
    "UNKNOWN": "미확인",
}

_POSITION_LABELS = {
    "ALIGNED_LOWER_STRONG": "하단 정렬이 강합니다.",
    "ALIGNED_LOWER_WEAK": "하단 정렬이 보이지만 확정은 약합니다.",
    "LOWER_BIAS": "하단 쪽 bias는 있지만 아직 확정 하단은 아닙니다.",
    "ALIGNED_UPPER_STRONG": "상단 정렬이 강합니다.",
    "ALIGNED_UPPER_WEAK": "상단 정렬이 보이지만 확정은 약합니다.",
    "UPPER_BIAS": "상단 쪽 bias는 있지만 아직 확정 상단은 아닙니다.",
    "ALIGNED_MIDDLE": "중앙 구간이라 Position 단독 진입보다 반응 확인이 우선입니다.",
    "UNRESOLVED_POSITION": "위치가 애매해 뒤 레이어로 넘겨야 합니다.",
}

_REASON_LABELS = {
    "middle_wait": "중앙 구간이라 Position 단독 진입을 보류합니다.",
    "lower_edge_observe": "하단 컨텍스트는 맞지만 반등 확정이 아직 부족해 관찰만 유지합니다.",
    "upper_approach_observe": "상단 접근 중이라 거절과 돌파 방향이 더 확인돼야 합니다.",
    "outer_band_reversal_support_required_observe": "반전 근거는 있지만 BB44 외곽 지지가 아직 부족해 보류합니다.",
    "conflict_box_lower_bb20_upper_upper_dominant_observe": "박스는 아래인데 밴드는 위라 충돌 상태로 봅니다.",
    "conflict_box_upper_bb20_lower_lower_dominant_observe": "박스는 위인데 밴드는 아래라 충돌 상태로 봅니다.",
    "lower_support_fail_confirm": "하단 지지가 무너졌다고 보고 SELL 확인으로 넘깁니다.",
    "upper_reject_mixed_confirm": "상단 거절이 확인돼 SELL 확인으로 넘깁니다.",
    "lower_rebound_confirm": "하단 지지 반등이 확인돼 BUY 확인으로 넘깁니다.",
    "lower_break_sell": "하단 이탈이 확인돼 SELL 연장으로 해석합니다.",
}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _pick(mapping: dict[str, str], raw: Any, default: str = "") -> str:
    key = str(raw or "").strip().upper()
    if not key:
        return default
    return mapping.get(key, str(raw or "").replace("_", " ").strip())


def _compact_code(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return "-"
    return text.replace("_", " ")


def _reason_text(reason: Any) -> str:
    key = str(reason or "").strip().lower()
    if not key:
        return "특별한 차단 사유는 없지만 아직 확정 신호가 약합니다."
    return _REASON_LABELS.get(key, _compact_code(key))


def _position_text(interp: dict[str, Any], energy: dict[str, Any]) -> str:
    primary = str(interp.get("primary_label") or "").strip().upper()
    conflict = str(interp.get("conflict_kind") or "").strip().upper()
    if conflict:
        return f"축이 서로 충돌해 Position 단독 판단을 보류합니다. ({_compact_code(conflict)})"
    if primary in _POSITION_LABELS:
        return _POSITION_LABELS[primary]
    lower_force = _safe_float(energy.get("lower_position_force"))
    upper_force = _safe_float(energy.get("upper_position_force"))
    middle = _safe_float(energy.get("middle_neutrality"))
    if middle >= 0.55:
        return "중앙 비중이 커서 Response와 State 확인이 우선입니다."
    if lower_force > upper_force:
        return "하단 쪽 압력이 우세하지만 확정은 아닙니다."
    if upper_force > lower_force:
        return "상단 쪽 압력이 우세하지만 확정은 아닙니다."
    return "위치 에너지가 비슷해 방향 판단을 뒤로 넘깁니다."


def _action_summary(action: Any, side: Any, reason: Any) -> tuple[str, str]:
    action_key = str(action or "WAIT").strip().upper() or "WAIT"
    side_key = str(side or "").strip().upper()
    if action_key == "WAIT" and side_key == "BUY":
        return ("BUY 관찰", "good")
    if action_key == "WAIT" and side_key == "SELL":
        return ("SELL 관찰", "bad")
    if action_key == "BUY":
        return ("BUY 후보", "good")
    if action_key == "SELL":
        return ("SELL 후보", "bad")
    if "conflict" in str(reason or "").lower():
        return ("충돌 대기", "warn")
    return ("중립 대기", "neutral")


def _next_trigger_text(action: Any, side: Any, reason: Any, zones: dict[str, Any], interp: dict[str, Any]) -> str:
    reason_key = str(reason or "").strip().lower()
    side_key = str(side or "").strip().upper()
    primary = str(interp.get("primary_label") or "").strip().upper()
    bb44_zone = str(zones.get("bb44_zone") or "").strip().upper()
    if reason_key == "middle_wait" or primary == "ALIGNED_MIDDLE":
        return "지지/저항 anchor나 상하단 재접촉이 나오기 전까지 대기합니다."
    if "outer_band_reversal_support_required" in reason_key:
        return "BB44가 외곽으로 더 붙거나 S/R 지지가 더 분명해지면 반전 진입을 다시 봅니다."
    if "lower" in reason_key or side_key == "BUY":
        if bb44_zone == "MIDDLE":
            return "하단 지지 유지가 더 선명해지면 BUY를 보고, 하단 붕괴가 이어지면 SELL로 전환합니다."
        return "하단 지지 유지/재탈환이 더 강해지면 BUY, 하단 붕괴면 SELL로 전환합니다."
    if "upper" in reason_key or side_key == "SELL":
        return "상단 거절이 더 선명해지면 SELL을 보고, 상단 돌파가 이어지면 BUY로 전환합니다."
    return "다음 박스 끝단 접촉이나 명확한 반응이 나올 때까지 관찰합니다."


def _force_summary(energy: dict[str, Any]) -> str:
    lower_force = _safe_float(energy.get("lower_position_force"))
    upper_force = _safe_float(energy.get("upper_position_force"))
    middle = _safe_float(energy.get("middle_neutrality"))
    return f"하단 {lower_force:.2f} / 상단 {upper_force:.2f} / 중립 {middle:.2f}"


def _gate_summary(meta: dict[str, Any], obs: dict[str, Any]) -> str:
    preflight = str(meta.get("preflight_allowed_action_raw") or "UNKNOWN").strip().upper()
    core = str(meta.get("core_allowed_action") or "").strip().upper() or "-"
    return f"Preflight {preflight} / Core {core} / Observe {str(obs.get('state') or '-').upper()}"


def _build_symbol_item(symbol: str, signal: dict[str, Any]) -> dict[str, Any]:
    context = signal.get("current_entry_context_v1") or {}
    meta = context.get("metadata") or {}
    snapshot = signal.get("position_snapshot_v2") or {}
    zones = snapshot.get("zones") or meta.get("position_zones_v2") or {}
    interp = snapshot.get("interpretation") or meta.get("position_interpretation_v2") or {}
    energy = snapshot.get("energy") or meta.get("position_energy_v2") or {}
    obs = meta.get("observe_confirm_v2") or meta.get("observe_confirm_v1") or {}
    state = meta.get("state_raw_snapshot_v1") or {}

    box_zone = _pick(_ZONE_LABELS, zones.get("box_zone"), "미확인")
    bb20_zone = _pick(_ZONE_LABELS, zones.get("bb20_zone"), "미확인")
    bb44_zone = _pick(_ZONE_LABELS, zones.get("bb44_zone"), "미확인")
    market_mode = _pick(_MARKET_MODE_LABELS, state.get("market_mode") or signal.get("market_mode"), "미확인")
    liquidity = _pick(_LIQUIDITY_LABELS, state.get("liquidity_state") or signal.get("liquidity_state"), "미확인")
    reason = str(obs.get("reason") or "").strip()
    action_text, tone = _action_summary(obs.get("action"), obs.get("side"), reason)
    position_text = _position_text(interp, energy)
    reason_text = _reason_text(reason)
    location_summary = f"박스 {box_zone} / BB20 {bb20_zone} / BB44 {bb44_zone}"
    logs = [
        {"label": "현재 위치", "text": location_summary},
        {"label": "Position", "text": position_text},
        {"label": "현재 판단", "text": f"{action_text} - {reason_text}"},
        {"label": "게이트", "text": _gate_summary(meta, obs)},
        {"label": "위치 에너지", "text": _force_summary(energy)},
    ]

    return {
        "symbol": symbol,
        "market_mode": market_mode,
        "liquidity": liquidity,
        "location_summary": location_summary,
        "position_summary": position_text,
        "action_badge": action_text,
        "action_tone": tone,
        "decision_summary": reason_text,
        "next_trigger": _next_trigger_text(obs.get("action"), obs.get("side"), reason, zones, interp),
        "logs": logs,
        "raw": {
            "position_primary_label": str(interp.get("primary_label") or ""),
            "position_bias_label": str(interp.get("bias_label") or ""),
            "observe_action": str(obs.get("action") or ""),
            "observe_side": str(obs.get("side") or ""),
            "observe_reason": reason,
            "box_zone": str(zones.get("box_zone") or ""),
            "bb20_zone": str(zones.get("bb20_zone") or ""),
            "bb44_zone": str(zones.get("bb44_zone") or ""),
        },
    }


def build_current_market_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"updated_at": "", "items": []}

    latest_by_symbol = payload.get("latest_signal_by_symbol") or {}
    symbols = list(payload.get("symbols") or latest_by_symbol.keys() or [])
    items = []
    for symbol in symbols:
        signal = latest_by_symbol.get(symbol) or {}
        if not isinstance(signal, dict) or not signal:
            continue
        items.append(_build_symbol_item(str(symbol), signal))

    return {
        "updated_at": str(payload.get("updated_at") or ""),
        "items": items,
    }
