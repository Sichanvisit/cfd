"""Shared Korean label maps for runtime reasons and scene explanations."""

from __future__ import annotations

import re

RUNTIME_REASON_SCORE_SUFFIX_RE = re.compile(
    r"\s*\([+\-]\d+(?:\.\d+)?[^)]*\)\s*$",
    re.IGNORECASE,
)

RUNTIME_REASON_PREFIX_LABELS = {
    "flow": "흐름",
    "trigger": "트리거",
    "wait": "대기",
}

RUNTIME_REASON_EXACT_MAP = {
    "lower rebound confirm": "하단 반등 확인",
    "upper reject mixed confirm": "상단 거부 혼합 확인",
    "bb20 reclaim": "BB20 되찾기",
    "momentum recovery": "모멘텀 회복",
    "range follow": "박스 추종",
    "trend continuation": "추세 지속",
    "trend spread down": "추세 확산 하방",
    "trend spread up": "추세 확산 상방",
    "rsi divergence down": "RSI 다이버전스 하방",
    "rsi divergence up": "RSI 다이버전스 상방",
    "manual/unknown": "수동 또는 미확인 청산",
    "manual take profit": "수동 익절 청산",
    "manual stop loss": "수동 손절 청산",
    "protective loss exit": "손실 보호 청산",
    "protective profit exit": "이익 보호 청산",
    "full exit": "전량 청산",
    "partial exit": "부분 청산",
    "runner exit": "러너 청산",
    "target exit": "목표가 청산",
    "timeout exit": "시간 만료 청산",
    "forecast guard": "포리캐스트 가드 대기",
    "barrier guard": "베리어 가드 대기",
    "outer band guard": "외곽 밴드 가드 대기",
    "observe state wait": "관찰 상태 대기",
    "energy soft block": "에너지 소프트 차단 대기",
    "execution soft blocked": "실행 소프트 차단 대기",
    "entry cooldown": "진입 쿨다운 대기",
    "max positions reached": "최대 보유 수 도달",
    "market closed cooldown": "시장 마감 대기",
    "market closed session": "시장 세션 대기",
    "utility not ready": "유틸리티 준비 부족 대기",
    "topdown timeframe gate blocked": "상위 타임프레임 게이트 대기",
    "h1 entry gate blocked": "H1 진입 게이트 대기",
    "stage min prob not met": "단계 최소 확률 미달 대기",
    "ai entry filter blocked": "AI 진입 필터 대기",
    "order send failed": "주문 전송 실패 대기",
    "conflict barrier": "충돌 베리어",
    "middle chop barrier": "중앙 혼잡 베리어",
    "direction policy barrier": "방향 정책 베리어",
    "liquidity barrier": "유동성 베리어",
    "buy barrier": "매수 베리어",
    "sell barrier": "매도 베리어",
    "opposite score spike": "반대 점수 급변",
    "volatility spike": "변동성 급등",
    "plus to minus protect": "플러스→마이너스 전환 보호",
    "shock guard": "쇼크 가드",
    "shock reversal": "쇼크 반전",
}

RUNTIME_REASON_TOKEN_MAP = {
    "balanced": "균형",
    "barrier": "베리어",
    "bb": "BB",
    "belief": "빌리프",
    "buy": "매수",
    "breakout": "돌파",
    "chop": "혼잡",
    "confirm": "확인",
    "conflict": "충돌",
    "continuation": "지속",
    "cut": "차단",
    "divergence": "다이버전스",
    "down": "하방",
    "edge": "경계",
    "entry": "진입",
    "exit": "청산",
    "flat": "플랫",
    "flow": "흐름",
    "forecast": "포리캐스트",
    "full": "전량",
    "gate": "게이트",
    "guard": "가드",
    "hold": "보유",
    "hard": "강",
    "loss": "손실",
    "lower": "하단",
    "liquidity": "유동성",
    "manual": "수동",
    "market": "시장",
    "closed": "마감",
    "cooldown": "쿨다운",
    "partial": "부분",
    "policy": "정책",
    "positions": "보유수",
    "prob": "확률",
    "profit": "이익",
    "protective": "보호",
    "reclaim": "리클레임",
    "rebound": "반등",
    "reentry": "재진입",
    "reject": "거부",
    "retest": "재시험",
    "rsi": "RSI",
    "runner": "러너",
    "score": "점수",
    "sell": "매도",
    "shock": "쇼크",
    "soft": "완화",
    "spike": "급변",
    "spread": "확산",
    "stage": "단계",
    "stop": "손절",
    "target": "목표가",
    "timeout": "시간만료",
    "touch": "터치",
    "trend": "추세",
    "trigger": "트리거",
    "unknown": "미확인",
    "upper": "상단",
    "up": "상방",
    "utility": "유틸리티",
    "volatility": "변동성",
    "wait": "대기",
}

RUNTIME_SCENE_EXACT_MAP = {
    "breakout_retest_hold": "돌파 후 재시험 유지",
    "trend_exhaustion": "추세 소진",
    "time_decay_risk": "시간 경과 리스크",
    "runner_healthy": "러너 유지 정상",
    "runner_hold": "러너 유지",
    "correct_hold": "올바른 보유",
    "correct_flip": "올바른 반전",
    "pullback_then_continue": "눌림 후 지속",
    "reclaim_breakout": "되찾기 후 돌파",
    "early_breakout_probe": "초기 돌파 탐색",
    "mixed_breakout": "혼합 돌파",
    "gap_trend_scene": "갭 추세 장면",
    "range_reversal_scene": "박스 반전 장면",
    "entry_initiation": "진입 시작 장면",
    "defensive_exit": "방어 청산 장면",
    "position_management": "포지션 관리 장면",
    "unresolved": "미해결",
}

RUNTIME_SCENE_TOKEN_MAP = {
    "breakout": "돌파",
    "retest": "재시험",
    "hold": "유지",
    "trend": "추세",
    "exhaustion": "소진",
    "time": "시간",
    "decay": "경과",
    "risk": "리스크",
    "runner": "러너",
    "healthy": "정상",
    "correct": "올바른",
    "flip": "반전",
    "pullback": "눌림",
    "continue": "지속",
    "reclaim": "되찾기",
    "early": "초기",
    "probe": "탐색",
    "mixed": "혼합",
    "gap": "갭",
    "range": "박스",
    "reversal": "반전",
    "entry": "진입",
    "initiation": "시작",
    "defensive": "방어",
    "exit": "청산",
    "position": "포지션",
    "management": "관리",
    "unresolved": "미해결",
}

RUNTIME_SCENE_GATE_LABELS = {
    "NONE": "없음",
    "WEAK": "약함",
    "CAUTION": "주의",
    "BLOCKED": "차단",
    "WAIT": "대기",
    "RELIEF_READY": "완화 준비",
}

RUNTIME_CONFIDENCE_BAND_LABELS = {
    "LOW": "낮음",
    "MEDIUM": "보통",
    "HIGH": "높음",
    "PROBABLE": "유력",
    "CONFIRMED": "확인됨",
}

RUNTIME_TRANSITION_EXACT_MAP = {
    "plus_to_minus_protect": "플러스→마이너스 전환 보호",
    "opposite_score_spike": "반대 점수 급변",
    "volatility_spike": "변동성 급등",
    "shock_guard": "쇼크 방어",
    "shock_reversal": "쇼크 반전",
    "flip_ready": "반전 준비",
    "continuation_fragile": "지속 약화",
    "exhaustion_risk": "소진 위험",
    "breakout_failure_risk": "돌파 실패 위험",
    "false_break_risk": "가짜 돌파 위험",
    "range_reject_risk": "박스 거부 위험",
}


def _translate_tokens(text: str, *, token_map: dict[str, str], limit: int = 6) -> str:
    tokens = [token for token in re.split(r"[_\s\-]+", text.strip().lower()) if token]
    translated = [token_map.get(token, token.upper() if token.isupper() else token) for token in tokens[:limit]]
    return " ".join(item for item in translated if item).strip()


def normalize_runtime_reason_body(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lower = raw.lower().replace("_", " ").strip()
    if lower in RUNTIME_REASON_EXACT_MAP:
        return f"{RUNTIME_REASON_EXACT_MAP[lower]} ({raw})"
    if lower.startswith("bb upper edge"):
        suffix = raw[len("BB upper edge") :].strip() if raw.startswith("BB upper edge") else raw[13:].strip()
        return f"BB 상단 경계 {suffix}".strip()
    if lower.startswith("bb lower edge"):
        suffix = raw[len("BB lower edge") :].strip() if raw.startswith("BB lower edge") else raw[13:].strip()
        return f"BB 하단 경계 {suffix}".strip()
    if lower.startswith("bb 20/2 touch(consec)"):
        suffix = raw[len("BB 20/2 touch(consec)") :].strip() if raw.startswith("BB 20/2 touch(consec)") else raw[21:].strip()
        return f"BB 20/2 연속 터치 {suffix}".strip()

    candidate = _translate_tokens(lower, token_map=RUNTIME_REASON_TOKEN_MAP, limit=5)
    if candidate and candidate != lower:
        return f"{candidate} ({raw})"
    return raw


def normalize_runtime_reason(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    text = RUNTIME_REASON_SCORE_SUFFIX_RE.sub("", raw).strip()
    if text.startswith("ENTRY_STAGE:"):
        stage_text = text.split(":", 1)[1].strip()
        stage_text = re.sub(r"\s+p=\{.*\}\s*$", "", stage_text).strip()
        if not stage_text:
            return ""
        stage_label = RUNTIME_REASON_TOKEN_MAP.get(stage_text.lower(), stage_text)
        return f"진입 단계: {stage_label}"

    prefix = ""
    body = text
    if ":" in text:
        maybe_prefix, maybe_body = text.split(":", 1)
        prefix_key = maybe_prefix.strip().lower().replace(" ", "_")
        if prefix_key in RUNTIME_REASON_PREFIX_LABELS:
            prefix = RUNTIME_REASON_PREFIX_LABELS[prefix_key]
            body = maybe_body.strip()

    body_text = normalize_runtime_reason_body(body)
    if not body_text:
        return ""
    return f"{prefix}: {body_text}" if prefix else body_text


def normalize_runtime_scene_label(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lower = raw.lower().strip()
    if lower in RUNTIME_SCENE_EXACT_MAP:
        return f"{RUNTIME_SCENE_EXACT_MAP[lower]} ({raw})"
    candidate = _translate_tokens(lower, token_map=RUNTIME_SCENE_TOKEN_MAP, limit=6)
    if candidate and candidate != lower:
        return f"{candidate} ({raw})"
    return raw


def normalize_runtime_scene_gate(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    return RUNTIME_SCENE_GATE_LABELS.get(upper, raw)


def normalize_runtime_confidence_label(*, band: object | None = None, confidence: object | None = None) -> str:
    band_text = str(band or "").strip().upper()
    if band_text in RUNTIME_CONFIDENCE_BAND_LABELS:
        return RUNTIME_CONFIDENCE_BAND_LABELS[band_text]
    try:
        confidence_value = float(confidence)
    except Exception:
        confidence_value = 0.0
    if confidence_value >= 0.75:
        return "높음"
    if confidence_value >= 0.45:
        return "보통"
    if confidence_value > 0.0:
        return "낮음"
    return ""


def normalize_runtime_transition_hint(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lower = raw.lower().strip()
    if lower in RUNTIME_TRANSITION_EXACT_MAP:
        return RUNTIME_TRANSITION_EXACT_MAP[lower]
    candidate = _translate_tokens(lower, token_map={**RUNTIME_REASON_TOKEN_MAP, **RUNTIME_SCENE_TOKEN_MAP}, limit=6)
    return candidate or raw
