"""
Telegram notification helpers.
"""

from collections.abc import Mapping
import logging
import json
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any

import requests

from backend.core.config import Config
from backend.services.barrier_state25_runtime_bridge import build_barrier_runtime_summary_v1
from backend.services.belief_state25_runtime_bridge import build_belief_runtime_summary_v1
from backend.services.forecast_state25_runtime_bridge import build_forecast_runtime_summary_v1
from backend.services.flow_shadow_display_surface import (
    attach_flow_shadow_display_surface_fields_v1,
)
from backend.services.reason_label_map import (
    normalize_runtime_confidence_label,
    normalize_runtime_reason,
    normalize_runtime_reason_body,
    normalize_runtime_scene_gate,
    normalize_runtime_scene_label,
    normalize_runtime_transition_hint,
)
from backend.services.telegram_route_policy import resolve_telegram_route_destination

logger = logging.getLogger(__name__)
_send_queue = Queue()
_stop_event = Event()
_worker = None

_normalize_runtime_reason = normalize_runtime_reason
_normalize_runtime_reason_body = normalize_runtime_reason_body


def _coerce_thread_id(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "0":
        return None
    return text


def _normalize_pnl_window_code(window_code: str | None) -> str:
    code = str(window_code or "").strip()
    if not code:
        return ""
    if code in {"15m", "15M"}:
        return "15M"
    if code == "1m":
        # 1m is reserved for the real-time DM route, not the PnL forum.
        return ""
    lowered = code.lower()
    if lowered == "1h":
        return "1H"
    if lowered == "4h":
        return "4H"
    if lowered == "1d":
        return "1D"
    if lowered == "1w":
        return "1W"
    if code == "1M":
        return "1M"
    return ""


def _coerce_parse_mode(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_reply_markup(value: object) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None


def _resolve_pnl_thread_id(window_code: str | None) -> str | None:
    normalized = _normalize_pnl_window_code(window_code)
    mapping = {
        "15M": Config.TG_PNL_TOPIC_15M_ID,
        "1H": Config.TG_PNL_TOPIC_1H_ID,
        "4H": Config.TG_PNL_TOPIC_4H_ID,
        "1D": Config.TG_PNL_TOPIC_1D_ID,
        "1W": Config.TG_PNL_TOPIC_1W_ID,
        "1M": Config.TG_PNL_TOPIC_1M_ID,
    }
    return _coerce_thread_id(mapping.get(normalized))


def _resolve_destination(
    *,
    route: str | None = None,
    window_code: str | None = None,
    chat_id: str | int | None = None,
    thread_id: str | int | None = None,
) -> tuple[str, str | None]:
    return resolve_telegram_route_destination(
        route=route,
        window_code=window_code,
        chat_id=chat_id,
        thread_id=thread_id,
    )


def resolve_telegram_destination(
    *,
    route: str | None = None,
    window_code: str | None = None,
    chat_id: str | int | None = None,
    thread_id: str | int | None = None,
) -> tuple[str, str | None]:
    return _resolve_destination(
        route=route,
        window_code=window_code,
        chat_id=chat_id,
        thread_id=thread_id,
    )


def _telegram_api_request(method: str, payload: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any] | None:
    if not Config.TG_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{Config.TG_TOKEN}/{method}"
    response = requests.post(url, data=payload, timeout=timeout)
    if response.status_code != 200:
        logger.warning(
            "Telegram API failed: method=%s status=%s body=%s",
            method,
            response.status_code,
            response.text[:300],
        )
        return None
    try:
        body = response.json()
    except ValueError:
        logger.warning("Telegram API returned non-JSON body: method=%s", method)
        return None
    if not bool(body.get("ok", False)):
        logger.warning(
            "Telegram API returned ok=false: method=%s body=%s",
            method,
            str(body)[:300],
        )
        return None
    return dict(body)


def _build_send_payload(
    *,
    message: str,
    chat_id: str,
    thread_id: str | None = None,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": message,
    }
    parse_mode_value = _coerce_parse_mode(parse_mode)
    if parse_mode_value:
        payload["parse_mode"] = parse_mode_value
    if thread_id:
        payload["message_thread_id"] = thread_id
    reply_markup_value = _coerce_reply_markup(reply_markup)
    if reply_markup_value:
        payload["reply_markup"] = reply_markup_value
    return payload


def _send_sync(
    *,
    message: str,
    chat_id: str,
    thread_id: str | None = None,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> dict[str, Any] | None:
    if not Config.TG_TOKEN or not chat_id:
        return None
    payload = _build_send_payload(
        message=message,
        chat_id=chat_id,
        thread_id=thread_id,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )
    return _telegram_api_request("sendMessage", payload, timeout=10.0)


def _worker_loop():
    while not _stop_event.is_set():
        try:
            item = _send_queue.get(timeout=0.5)
        except Empty:
            continue

        try:
            _send_sync(**item)
        except requests.RequestException as exc:
            logger.exception("Telegram request failed: %s", exc)
        except Exception as exc:
            logger.exception("Unexpected notifier error: %s", exc)
        finally:
            _send_queue.task_done()


def _ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _stop_event.clear()
        _worker = Thread(target=_worker_loop, daemon=True, name="telegram-notifier")
        _worker.start()


def _enqueue_message(
    message: str,
    *,
    chat_id: str,
    thread_id: str | None = None,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> bool:
    if not Config.TG_TOKEN or not chat_id:
        return False
    _ensure_worker()
    _send_queue.put(
        {
            "message": str(message),
            "chat_id": str(chat_id),
            "thread_id": _coerce_thread_id(thread_id),
            "parse_mode": _coerce_parse_mode(parse_mode),
            "reply_markup": reply_markup,
        }
    )
    return True


def send_telegram(
    message: str,
    *,
    route: str = "runtime",
    window_code: str | None = None,
    chat_id: str | int | None = None,
    thread_id: str | int | None = None,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> bool:
    resolved_chat_id, resolved_thread_id = _resolve_destination(
        route=route,
        window_code=window_code,
        chat_id=chat_id,
        thread_id=thread_id,
    )
    return _enqueue_message(
        message,
        chat_id=resolved_chat_id,
        thread_id=resolved_thread_id,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


def send_telegram_sync(
    message: str,
    *,
    route: str = "runtime",
    window_code: str | None = None,
    chat_id: str | int | None = None,
    thread_id: str | int | None = None,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> dict[str, Any] | None:
    resolved_chat_id, resolved_thread_id = _resolve_destination(
        route=route,
        window_code=window_code,
        chat_id=chat_id,
        thread_id=thread_id,
    )
    return _send_sync(
        message=message,
        chat_id=resolved_chat_id,
        thread_id=resolved_thread_id,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


def send_runtime_telegram(message: str) -> bool:
    return send_telegram(message, route="runtime")


def send_check_telegram(
    message: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> bool:
    return send_telegram(message, route="check", parse_mode=parse_mode, reply_markup=reply_markup)


def send_report_telegram(
    message: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> bool:
    return send_telegram(message, route="report", parse_mode=parse_mode, reply_markup=reply_markup)


def send_pnl_telegram(
    window_code: str,
    message: str,
    *,
    parse_mode: str | None = "Markdown",
    reply_markup: object | None = None,
) -> bool:
    return send_telegram(
        message,
        route="pnl",
        window_code=window_code,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


def edit_telegram_message_text(
    *,
    chat_id: str | int,
    message_id: int,
    text: str,
    thread_id: str | int | None = None,
    parse_mode: str | None = None,
    reply_markup: object | None = None,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {
        "chat_id": str(chat_id).strip(),
        "message_id": int(message_id),
        "text": str(text),
    }
    thread_id_value = _coerce_thread_id(thread_id)
    if thread_id_value:
        payload["message_thread_id"] = thread_id_value
    parse_mode_value = _coerce_parse_mode(parse_mode)
    if parse_mode_value:
        payload["parse_mode"] = parse_mode_value
    reply_markup_value = _coerce_reply_markup(reply_markup)
    if reply_markup_value:
        payload["reply_markup"] = reply_markup_value
    return _telegram_api_request("editMessageText", payload, timeout=10.0)


def answer_callback_query(
    callback_query_id: str,
    *,
    text: str = "",
    show_alert: bool = False,
) -> dict[str, Any] | None:
    payload = {
        "callback_query_id": str(callback_query_id or "").strip(),
        "text": str(text or "").strip(),
        "show_alert": "true" if bool(show_alert) else "false",
    }
    return _telegram_api_request("answerCallbackQuery", payload, timeout=10.0)


def get_telegram_updates(
    *,
    offset: int | None = None,
    timeout: int = 0,
    allowed_updates: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "timeout": max(0, int(timeout)),
    }
    if offset is not None:
        payload["offset"] = int(offset)
    if allowed_updates:
        payload["allowed_updates"] = json.dumps(list(allowed_updates), ensure_ascii=False)
    body = _telegram_api_request("getUpdates", payload, timeout=max(10.0, float(timeout) + 5.0))
    result = body.get("result") if isinstance(body, dict) else []
    return list(result) if isinstance(result, list) else []


def shutdown(timeout=2.0):
    if _worker is None:
        return
    try:
        _send_queue.join()
    except Exception:
        pass
    _stop_event.set()
    _worker.join(timeout=timeout)


def _summarize_runtime_reasons(reasons: list[str] | tuple[str, ...] | None) -> tuple[str, str]:
    primary_reasons: list[str] = []
    wait_reasons: list[str] = []
    stage_reasons: list[str] = []
    for reason in list(reasons or []):
        raw = str(reason or "").strip()
        if not raw:
            continue
        normalized = _normalize_runtime_reason(raw)
        if not normalized:
            continue
        if normalized.startswith("진입 단계:"):
            if normalized not in stage_reasons:
                stage_reasons.append(normalized)
            continue
        if "wait" in raw.lower():
            if normalized not in wait_reasons:
                wait_reasons.append(normalized)
            continue
        if normalized not in primary_reasons:
            primary_reasons.append(normalized)
    visible_reasons = primary_reasons[:2] if primary_reasons else stage_reasons[:1]
    primary_summary = " / ".join(visible_reasons) if visible_reasons else "조건 충족"
    wait_summary = " / ".join(wait_reasons[:1])
    return primary_summary, wait_summary


def _strip_runtime_reason_prefix(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    for prefix in ("흐름:", "트리거:", "대기:"):
        if normalized.startswith(prefix):
            return normalized.split(":", 1)[1].strip()
    return normalized


def _build_runtime_lead_axis(reasons: list[str] | tuple[str, ...] | None) -> str:
    primary_reasons: list[str] = []
    stage_reason = ""
    for reason in list(reasons or []):
        raw = str(reason or "").strip()
        if not raw:
            continue
        normalized = _normalize_runtime_reason(raw)
        if not normalized:
            continue
        if normalized.startswith("진입 단계:"):
            if not stage_reason:
                stage_reason = normalized
            continue
        if "wait" in raw.lower():
            continue
        candidate = _strip_runtime_reason_prefix(normalized)
        if candidate and candidate not in primary_reasons:
            primary_reasons.append(candidate)
    if primary_reasons:
        return " + ".join(primary_reasons[:2])
    if stage_reason:
        return stage_reason
    return "조건 충족"


def _runtime_reason_raw_text(reasons: list[str] | tuple[str, ...] | None) -> str:
    return " | ".join(str(reason or "").strip().lower() for reason in list(reasons or []) if str(reason or "").strip())


def _build_runtime_risk_line(
    *,
    side: str,
    reasons: list[str] | tuple[str, ...] | None,
) -> str:
    raw_text = _runtime_reason_raw_text(reasons)
    side_upper = str(side or "").strip().upper()
    if side_upper == "BUY":
        if any(token in raw_text for token in ("upper", "reject", "divergence down", "volatility spike")):
            return "상단 저항/반대 하방 신호 재확인 필요"
        if "touch(consec)" in raw_text or "bb upper edge" in raw_text:
            return "상단 과열 구간 추격 진입 주의"
        return "상단 저항 재확인 필요"
    if side_upper == "SELL":
        if any(token in raw_text for token in ("lower", "rebound", "support", "divergence up")):
            return "하단 반등/지지 재확인 필요"
        if "touch(consec)" in raw_text or "bb lower edge" in raw_text:
            return "하단 과매도 반등 주의"
        return "하단 지지 반등 가능성 주의"
    return "반대 방향 핵심 신호 재확인 필요"


def _format_runtime_strength_label(
    *,
    score: float,
    reasons: list[str] | tuple[str, ...] | None = None,
) -> str:
    score_f = float(score or 0.0)
    reason_count = len([reason for reason in list(reasons or []) if str(reason or "").strip()])
    if score_f >= 100.0 or reason_count >= 4:
        return "HIGH"
    if score_f >= 50.0 or reason_count >= 2:
        return "MEDIUM"
    return "LOW"


def _build_wait_release_condition(
    *,
    side: str,
    row: Mapping[str, Any] | None,
    barrier_hint: str,
    forecast_hint: str,
) -> str:
    payload = dict(row or {})
    forecast_summary = _resolve_forecast_summary(payload)
    confirm_side = str(forecast_summary.get("confirm_side", "")).strip().upper()
    decision_hint = str(forecast_summary.get("decision_hint", "")).strip().upper()
    side_upper = str(side or "").strip().upper()
    if confirm_side in {"BUY", "SELL"}:
        if decision_hint == "CONFIRM_BIASED":
            return f"{confirm_side} 확인 시 진입 재검토"
        return f"{confirm_side} 확인 신호 추가 시 재검토"
    if barrier_hint:
        return f"{barrier_hint} 완화 시 재검토"
    if forecast_hint:
        return f"{forecast_hint} 해소 시 재검토"
    if side_upper in {"BUY", "SELL"}:
        return f"{side_upper} 방향 확인 신호 추가 시 재검토"
    return "방향 확인 신호 추가 시 재검토"


def _build_exit_review_hint(
    *,
    profit: float,
    points: float,
    exit_reason: str | None,
    review_context: Mapping[str, Any] | None = None,
) -> str:
    payload = dict(review_context or {})
    raw = str(exit_reason or "").strip().lower().replace("_", " ")
    shock_reason = normalize_runtime_reason_body(payload.get("shock_reason"))
    shock_level = str(payload.get("shock_level", "") or "").strip().lower()
    pre_shock_stage = str(payload.get("pre_shock_stage", "") or "").strip().lower()
    post_shock_stage = str(payload.get("post_shock_stage", "") or "").strip().lower()
    if shock_reason:
        level_label = {
            "alert": "경계",
            "watch": "주의",
            "critical": "강경계",
        }.get(shock_level, "감시")
        stage_text = ""
        if pre_shock_stage and post_shock_stage:
            stage_text = f" / {pre_shock_stage}->{post_shock_stage}"
        return f"쇼크 {level_label} 대응 복기{stage_text}"
    if "protective loss" in raw or "stop" in raw:
        return "반대 힘 급변 여부와 진입 시점 재검토"
    if "protective profit" in raw or "runner" in raw:
        return "MFE 대비 이익 포착 효율 복기"
    if "target" in raw or "full exit" in raw:
        return "목표가 전량 청산이 최선이었는지 복기"
    if "timeout" in raw:
        return "보유 시간 대비 효율과 time decay 여부 복기"
    if abs(float(points or 0.0)) >= 1000.0:
        return "변동성 큰 구간이었는지 진입 시점과 허용 역행폭 복기"
    if float(profit or 0.0) < 0.0:
        return "반대 신호가 먼저 있었는지 진입 근거 복기"
    if float(profit or 0.0) > 0.0:
        return "추가 보유보다 현재 청산이 유리했는지 복기"
    return ""


_BARRIER_BIAS_LABELS = {
    "HARD_BLOCK": "강차단",
    "WAIT_BLOCK": "대기우세",
    "RELIEF_READY": "완화준비",
    "LIGHT_BLOCK": "약차단",
    "UNAVAILABLE": "미확인",
}
_BELIEF_PERSISTENCE_LABELS = {
    "STABLE": "안정",
    "UNSTABLE": "불안정",
    "FLIP_READY": "전환준비",
    "DECAYING": "약화",
    "BALANCED": "균형",
    "UNAVAILABLE": "미확인",
}
_FORECAST_DECISION_LABELS = {
    "CONFIRM_BIASED": "확인우세",
    "WAIT_BIASED": "대기우세",
    "FAST_EXIT_BIASED": "빠른정리우세",
    "HOLD_BIASED": "보유우세",
    "BALANCED": "균형",
}


def _coerce_runtime_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value or {})
    if isinstance(value, str):
        text = str(value).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return dict(parsed or {}) if isinstance(parsed, Mapping) else {}
    return {}


def _resolve_forecast_summary(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    bridge = _coerce_runtime_mapping(payload.get("forecast_state25_runtime_bridge_v1"))
    summary = _coerce_runtime_mapping(bridge.get("forecast_runtime_summary_v1"))
    if summary:
        return summary
    return _coerce_runtime_mapping(build_forecast_runtime_summary_v1(payload))


def _resolve_belief_summary(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    bridge = _coerce_runtime_mapping(payload.get("belief_state25_runtime_bridge_v1"))
    summary = _coerce_runtime_mapping(bridge.get("belief_runtime_summary_v1"))
    if summary:
        return summary
    return _coerce_runtime_mapping(build_belief_runtime_summary_v1(payload))


def _resolve_barrier_summary(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    bridge = _coerce_runtime_mapping(payload.get("barrier_state25_runtime_bridge_v1"))
    summary = _coerce_runtime_mapping(bridge.get("barrier_runtime_summary_v1"))
    if summary:
        return summary
    return _coerce_runtime_mapping(build_barrier_runtime_summary_v1(payload))


def _format_barrier_hint(summary: Mapping[str, Any] | None) -> str:
    payload = dict(summary or {})
    if not bool(payload.get("available", False)):
        return ""
    bias = _BARRIER_BIAS_LABELS.get(str(payload.get("blocking_bias", "")).upper(), "")
    primary = _normalize_runtime_reason_body(payload.get("top_component_reason")) or _normalize_runtime_reason_body(
        payload.get("top_component")
    )
    parts = [item for item in (bias, primary) if item]
    return " / ".join(parts[:2])


def _format_belief_hint(summary: Mapping[str, Any] | None) -> str:
    payload = dict(summary or {})
    if not bool(payload.get("available", False)):
        return ""
    side = str(payload.get("acting_side", "")).upper()
    hint = _BELIEF_PERSISTENCE_LABELS.get(str(payload.get("persistence_hint", "")).upper(), "")
    parts = []
    if side in {"BUY", "SELL"}:
        parts.append(f"{side} 지속")
    if hint:
        parts.append(hint)
    return " / ".join(parts[:2])


def _format_forecast_hint(summary: Mapping[str, Any] | None) -> str:
    payload = dict(summary or {})
    if not bool(payload.get("available", False)):
        return ""
    decision = _FORECAST_DECISION_LABELS.get(str(payload.get("decision_hint", "")).upper(), "")
    confirm_side = str(payload.get("confirm_side", "")).upper()
    parts = [decision] if decision else []
    if confirm_side in {"BUY", "SELL"}:
        parts.append(f"{confirm_side} 확인")
    return " / ".join(parts[:2])


def _build_wait_context_hints(row: Mapping[str, Any] | None) -> tuple[str, str, str]:
    payload = dict(row or {})
    barrier_hint = _format_barrier_hint(_resolve_barrier_summary(payload))
    belief_hint = _format_belief_hint(_resolve_belief_summary(payload))
    forecast_hint = _format_forecast_hint(_resolve_forecast_summary(payload))
    return barrier_hint, belief_hint, forecast_hint


def _resolve_scene_hint(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    for bridge_key in (
        "forecast_state25_runtime_bridge_v1",
        "belief_state25_runtime_bridge_v1",
        "barrier_state25_runtime_bridge_v1",
    ):
        bridge = _coerce_runtime_mapping(payload.get(bridge_key))
        hint = _coerce_runtime_mapping(bridge.get("state25_runtime_hint_v1"))
        if hint:
            return hint
    scene_label = str(
        payload.get("runtime_scene_fine_label")
        or payload.get("runtime_scene_label")
        or payload.get("state25_label")
        or payload.get("scene_pattern_name")
        or payload.get("scene_group_hint")
        or ""
    ).strip()
    if not scene_label:
        return {}
    return {
        "available": True,
        "scene_pattern_name": scene_label,
        "scene_group_hint": str(payload.get("runtime_scene_coarse_family", "") or "").strip(),
        "confidence": payload.get("runtime_scene_confidence", payload.get("state25_confidence", 0.0)),
        "confidence_band": str(payload.get("runtime_scene_confidence_band", "") or "").strip(),
        "transition_risk_hint": str(payload.get("runtime_scene_transition_speed", "") or "").strip(),
    }


def _resolve_scene_gate_label(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    raw_gate = str(
        payload.get("runtime_scene_gate_label")
        or payload.get("scene_gate_label")
        or payload.get("runtime_scene_gate_block_level")
        or ""
    ).strip()
    if raw_gate:
        return normalize_runtime_scene_gate(raw_gate)
    barrier_summary = _resolve_barrier_summary(payload)
    blocking_bias = str(barrier_summary.get("blocking_bias", "") or "").strip().upper()
    derived_gate = {
        "HARD_BLOCK": "BLOCKED",
        "WAIT_BLOCK": "CAUTION",
        "LIGHT_BLOCK": "WEAK",
        "RELIEF_READY": "RELIEF_READY",
    }.get(blocking_bias, "NONE")
    return normalize_runtime_scene_gate(derived_gate)


def _build_runtime_scene_line(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    scene_hint = _resolve_scene_hint(payload)
    scene_label_raw = str(
        payload.get("runtime_scene_fine_label")
        or scene_hint.get("scene_pattern_name")
        or payload.get("state25_label")
        or scene_hint.get("scene_group_hint")
        or ""
    ).strip()
    scene_label = normalize_runtime_scene_label(scene_label_raw)
    if not scene_label:
        return ""
    confidence_band = (
        str(payload.get("runtime_scene_confidence_band") or "").strip()
        or str(scene_hint.get("confidence_band") or "").strip()
    )
    confidence_value = scene_hint.get("confidence", payload.get("runtime_scene_confidence", 0.0))
    confidence_label = normalize_runtime_confidence_label(
        band=confidence_band,
        confidence=confidence_value,
    )
    gate_label = _resolve_scene_gate_label(payload)
    parts = [scene_label]
    if gate_label:
        parts.append(f"게이트: {gate_label}")
    if confidence_label:
        parts.append(f"확신: {confidence_label}")
    return " / ".join(parts[:3])


_BREAKOUT_SCENE_LABELS = {
    "breakout",
    "breakout_retest_hold",
    "liquidity_sweep_reclaim",
    "reclaim_breakout",
    "early_breakout_probe",
    "mixed_breakout",
    "range_break",
    "correct_flip",
    "trend_ignition",
    "failed_transition",
}

_PULLBACK_SCENE_LABELS = {
    "pullback_continuation",
    "pullback_then_continue",
    "runner_hold",
    "runner_healthy",
    "correct_hold",
    "reaccumulation",
    "redistribution",
    "trend_exhaustion",
    "time_decay_risk",
    "range_reversal_scene",
    "entry_initiation",
    "defensive_exit",
    "position_management",
}


def _resolve_runtime_scene_label_raw(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    scene_hint = _resolve_scene_hint(payload)
    return str(
        payload.get("runtime_scene_fine_label")
        or scene_hint.get("scene_pattern_name")
        or payload.get("state25_label")
        or scene_hint.get("scene_group_hint")
        or ""
    ).strip()


def _resolve_runtime_scene_family(row: Mapping[str, Any] | None) -> str:
    raw = _resolve_runtime_scene_label_raw(row)
    if not raw:
        return "UNKNOWN"
    normalized = raw.lower().strip().replace("-", "_").replace(" ", "_")
    if normalized in _BREAKOUT_SCENE_LABELS:
        return "BREAKOUT"
    if normalized in _PULLBACK_SCENE_LABELS:
        return "PULLBACK"
    breakout_tokens = ("breakout", "reclaim", "sweep", "flip", "ignition")
    pullback_tokens = ("pullback", "runner", "continuation", "exhaustion", "time_decay", "defensive", "hold")
    if any(token in normalized for token in breakout_tokens):
        return "BREAKOUT"
    if any(token in normalized for token in pullback_tokens):
        return "PULLBACK"
    return "UNKNOWN"


def _resolve_position_energy(row: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(row or {})
    energy_surface = _coerce_runtime_mapping(payload.get("position_energy_surface_v1"))
    energy = _coerce_runtime_mapping(energy_surface.get("energy"))
    if energy:
        return energy
    return {
        "lower_position_force": payload.get("lower_position_force"),
        "upper_position_force": payload.get("upper_position_force"),
        "middle_neutrality": payload.get("middle_neutrality"),
    }


def _resolve_position_dominance(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    snapshot = _coerce_runtime_mapping(payload.get("position_snapshot_v2"))
    snapshot_energy = _coerce_runtime_mapping(snapshot.get("energy"))
    metadata = _coerce_runtime_mapping(snapshot_energy.get("metadata"))
    dominance = str(metadata.get("position_dominance", "") or "").strip().upper()
    if dominance:
        return dominance
    energy = _resolve_position_energy(payload)
    lower_force = float(energy.get("lower_position_force") or 0.0)
    upper_force = float(energy.get("upper_position_force") or 0.0)
    middle_force = float(energy.get("middle_neutrality") or 0.0)
    if upper_force > max(lower_force, middle_force):
        return "UPPER"
    if lower_force > max(upper_force, middle_force):
        return "LOWER"
    if middle_force > max(upper_force, lower_force):
        return "MIDDLE"
    return "MIXED"


def _build_runtime_force_dominance_line(row: Mapping[str, Any] | None) -> str:
    energy = _resolve_position_energy(row)
    lower_force = float(energy.get("lower_position_force") or 0.0)
    upper_force = float(energy.get("upper_position_force") or 0.0)
    middle_force = float(energy.get("middle_neutrality") or 0.0)
    if max(lower_force, upper_force, middle_force) <= 0.0:
        return ""
    dominance_label = {
        "UPPER": "상단 우세",
        "LOWER": "하단 우세",
        "MIDDLE": "중립 우세",
        "MIXED": "혼합",
        "UNRESOLVED": "미확정",
    }.get(_resolve_position_dominance(row), "미확정")
    return (
        f"{dominance_label} "
        f"(하단 {lower_force:.2f} / 상단 {upper_force:.2f} / 중립 {middle_force:.2f})"
    )


def _build_runtime_force_alignment_line(
    side: str | None,
    row: Mapping[str, Any] | None,
) -> str:
    side_key = str(side or "").strip().upper()
    if not side_key:
        return ""
    dominance = _resolve_position_dominance(row)
    dominance_label = {
        "UPPER": "상단 우세",
        "LOWER": "하단 우세",
        "MIDDLE": "중립 우세",
        "MIXED": "혼합",
        "UNRESOLVED": "미확정",
    }.get(dominance, "미확정")
    if dominance in {"MIDDLE", "MIXED", "UNRESOLVED"}:
        return f"{side_key}와 {dominance_label} 조합은 중립 ➖"
    scene_family = _resolve_runtime_scene_family(row)
    family_label = {
        "BREAKOUT": "돌파/리클레임 계열",
        "PULLBACK": "눌림/지속 계열",
        "UNKNOWN": "장면 미확정",
    }.get(scene_family, "장면 미확정")
    if scene_family == "BREAKOUT":
        if (side_key == "BUY" and dominance == "UPPER") or (side_key == "SELL" and dominance == "LOWER"):
            return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 정합 ✅"
        if (side_key == "BUY" and dominance == "LOWER") or (side_key == "SELL" and dominance == "UPPER"):
            return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 엇갈림 ⚠️"
        return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 중립 ➖"
    if scene_family == "PULLBACK":
        if (side_key == "BUY" and dominance == "LOWER") or (side_key == "SELL" and dominance == "UPPER"):
            return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 정합 ✅"
        if (side_key == "BUY" and dominance == "UPPER") or (side_key == "SELL" and dominance == "LOWER"):
            return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 엇갈림 ⚠️"
        return f"{side_key}와 {dominance_label} 조합은 {family_label} 기준 중립 ➖"
    return f"{side_key}와 {dominance_label} 조합은 {family_label}로 중립 ➖"


def _build_runtime_transition_line(
    reasons: list[str] | tuple[str, ...] | None,
    *,
    row: Mapping[str, Any] | None = None,
) -> str:
    raw_text = _runtime_reason_raw_text(reasons)
    normalized_raw_text = raw_text.replace("_", " ")
    parts: list[str] = []
    keyword_pairs = (
        ("plus to minus", "플러스→마이너스 전환 보호"),
        ("opposite score spike", "반대 점수 급변"),
        ("volatility spike", "변동성 급등"),
        ("shock reversal", "쇼크 반전"),
        ("shock guard", "쇼크 방어"),
    )
    for token, label in keyword_pairs:
        if token in normalized_raw_text and label not in parts:
            parts.append(label)
    scene_hint = _resolve_scene_hint(row)
    transition_hint = normalize_runtime_transition_hint(scene_hint.get("transition_risk_hint"))
    if transition_hint and transition_hint not in parts and len(parts) < 2:
        parts.append(transition_hint)
    transition_from = str((row or {}).get("runtime_scene_transition_from", "") or "").strip()
    transition_bars = int((row or {}).get("runtime_scene_transition_bars", 0) or 0)
    if transition_from and not parts:
        transition_from_label = normalize_runtime_scene_label(transition_from)
        bar_suffix = f" / {transition_bars}봉" if transition_bars > 0 else ""
        candidate = f"{transition_from_label} 이후 전이{bar_suffix}".strip()
        if candidate not in parts:
            parts.append(candidate)
    return " / ".join(parts[:2])


def _htf_alignment_detail_label_ko(detail: str | None) -> str:
    norm = str(detail or "").upper().strip()
    return {
        "ALL_ALIGNED_UP": "HTF 전체 상승 정렬",
        "MOSTLY_ALIGNED_UP": "HTF 상승 우세",
        "PARTIAL_UP": "HTF 부분 상승 정렬",
        "AGAINST_HTF_UP": "현재만 하락 역행",
        "ALL_ALIGNED_DOWN": "HTF 전체 하락 정렬",
        "MOSTLY_ALIGNED_DOWN": "HTF 하락 우세",
        "PARTIAL_DOWN": "HTF 부분 하락 정렬",
        "AGAINST_HTF_DOWN": "현재만 상승 역행",
        "MIXED": "HTF 혼조",
    }.get(norm, "")


def _htf_severity_label_ko(level: str | None) -> str:
    norm = str(level or "").upper().strip()
    return {
        "LOW": "약한 역행",
        "MEDIUM": "역행 경계",
        "HIGH": "강한 역행",
    }.get(norm, "")


def _build_runtime_htf_context_summary(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    detail = str(payload.get("htf_alignment_detail") or "").upper().strip()
    state = str(payload.get("htf_alignment_state") or "").upper().strip()
    label = _htf_alignment_detail_label_ko(detail)
    if not label or detail == "MIXED":
        return ""
    severity = _htf_severity_label_ko(payload.get("htf_against_severity"))
    if state == "AGAINST_HTF" and severity:
        return f"{label} ({severity})"
    return label


def _previous_box_break_state_label_ko(state: str | None) -> str:
    norm = str(state or "").upper().strip()
    return {
        "BREAKOUT_HELD": "직전 박스 상단 돌파 유지",
        "BREAKOUT_FAILED": "직전 박스 상단 돌파 실패",
        "BREAKDOWN_HELD": "직전 박스 하단 이탈 유지",
        "RECLAIMED": "직전 박스 되찾기",
        "REJECTED": "직전 박스 거부",
    }.get(norm, "")


def _previous_box_relation_label_ko(relation: str | None) -> str:
    norm = str(relation or "").upper().strip()
    return {
        "ABOVE": "직전 박스 위",
        "BELOW": "직전 박스 아래",
        "AT_HIGH": "직전 박스 상단 근처",
        "AT_LOW": "직전 박스 하단 근처",
        "INSIDE": "직전 박스 내부",
    }.get(norm, "")


def _build_runtime_previous_box_context_summary(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    break_state = _previous_box_break_state_label_ko(payload.get("previous_box_break_state"))
    if break_state:
        return break_state
    relation = _previous_box_relation_label_ko(payload.get("previous_box_relation"))
    if relation and relation != "직전 박스 내부":
        return relation
    return ""


def _late_chase_reason_label_ko(reason: str | None) -> str:
    norm = str(reason or "").upper().strip()
    return {
        "EXTENDED_ABOVE_PREV_BOX": "박스 상단 과확장",
        "AGAINST_PULLBACK_DEPTH": "눌림 얕음",
        "HTF_ALREADY_EXTENDED": "상위 추세 과확장",
        "MULTI_BAR_RUN_AFTER_BREAK": "돌파 후 연속 진행",
    }.get(norm, "")


def _build_runtime_late_chase_context_summary(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    risk_state = str(payload.get("late_chase_risk_state") or "").upper().strip()
    if risk_state in {"", "NONE"}:
        return ""
    base = "늦은 추격 위험 높음" if risk_state == "HIGH" else "늦은 추격 경계"
    reason = _late_chase_reason_label_ko(payload.get("late_chase_reason"))
    if reason:
        return f"{base} ({reason})"
    return base


def _build_runtime_share_context_summary(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    band = str(payload.get("cluster_share_symbol_band") or "").upper().strip()
    label = str(payload.get("share_context_label_ko") or "").strip()
    if band not in {"COMMON", "DOMINANT"} or not label:
        return ""
    return f"반복성 {label}"


def _build_runtime_context_line(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    explicit_summary = str(payload.get("context_bundle_summary_ko") or "").strip()
    if explicit_summary:
        return explicit_summary

    parts: list[str] = []
    for candidate in (
        _build_runtime_htf_context_summary(payload),
        _build_runtime_previous_box_context_summary(payload),
        _build_runtime_late_chase_context_summary(payload),
    ):
        if candidate and candidate not in parts:
            parts.append(candidate)

    share_summary = _build_runtime_share_context_summary(payload)
    if share_summary and len(parts) < 3 and share_summary not in parts:
        parts.append(share_summary)

    if not parts:
        fallback = str(payload.get("context_conflict_label_ko") or "").strip()
        state = str(payload.get("context_conflict_state") or "").upper().strip()
        if fallback and state not in {"", "NONE"}:
            parts.append(fallback)

    return " | ".join(parts[:3])


def _build_flow_shadow_axes_line(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    if "flow_shadow_continuation_persistence_prob_v1" not in payload:
        payload = dict(attach_flow_shadow_display_surface_fields_v1({"ROW": payload}).get("ROW", payload))
    if not any(
        key in payload
        for key in (
            "flow_shadow_continuation_persistence_prob_v1",
            "flow_shadow_entry_quality_prob_v1",
            "flow_shadow_reversal_risk_prob_v1",
        )
    ):
        return ""
    continuation = int(round(float(payload.get("flow_shadow_continuation_persistence_prob_v1") or 0.0) * 100.0))
    entry = int(round(float(payload.get("flow_shadow_entry_quality_prob_v1") or 0.0) * 100.0))
    reversal = int(round(float(payload.get("flow_shadow_reversal_risk_prob_v1") or 0.0) * 100.0))
    return f"Shadow: 지속 {continuation}% / 진입 {entry}% / 반전 {reversal}%"


def _build_flow_shadow_start_line(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    if "flow_shadow_start_marker_state_v1" not in payload:
        payload = dict(attach_flow_shadow_display_surface_fields_v1({"ROW": payload}).get("ROW", payload))
    state = str(payload.get("flow_shadow_start_marker_state_v1", "") or "").strip().upper()
    event = str(payload.get("flow_shadow_start_marker_event_kind_v1", "") or "").strip().upper()
    if state not in {"EXISTING_WATCH", "FALLBACK_START_WATCH"}:
        return ""
    if event not in {"BUY_WATCH", "SELL_WATCH"}:
        return ""
    return f"FlowStart: {event}"


def _build_flow_shadow_zone_line(row: Mapping[str, Any] | None) -> str:
    payload = dict(row or {})
    if "flow_shadow_entry_zone_state_v1" not in payload:
        payload = dict(attach_flow_shadow_display_surface_fields_v1({"ROW": payload}).get("ROW", payload))
    zone = str(payload.get("flow_shadow_entry_zone_state_v1", "") or "").strip().upper()
    final_kind = str(payload.get("flow_shadow_chart_event_final_kind_v1", "") or "").strip().upper()
    caution_flags = payload.get("flow_shadow_caution_flags_v1")
    caution_items: list[str] = []
    if isinstance(caution_flags, (list, tuple, set, frozenset)):
        caution_items = [str(item).strip().upper() for item in caution_flags if str(item).strip()]
    elif caution_flags:
        caution_items = [str(caution_flags).strip().upper()]
    if not zone and not final_kind and not caution_items:
        return ""
    parts = []
    if zone:
        parts.append(zone)
    if final_kind:
        parts.append(f"chart {final_kind}")
    if caution_items:
        parts.append("caution " + ",".join(caution_items[:3]))
    return "ShadowMode: " + " | ".join(parts)


def build_wait_message_signature(
    symbol: str,
    action: str,
    reason: str | None = None,
    row: Mapping[str, Any] | None = None,
) -> str:
    payload = dict(row or {})
    barrier_hint, belief_hint, forecast_hint = _build_wait_context_hints(payload)
    parts = [
        str(symbol or "").upper().strip(),
        str(action or "").upper().strip(),
        str(payload.get("entry_wait_state", "") or "").upper().strip(),
        str(payload.get("entry_wait_decision", "") or "").lower().strip(),
        _normalize_runtime_reason_body(reason or payload.get("entry_wait_reason") or payload.get("entry_skip_reason")),
        barrier_hint,
        belief_hint,
        forecast_hint,
    ]
    return "|".join(part for part in parts if part)


def _format_reverse_strength_label(score: float) -> str:
    score_f = float(score or 0.0)
    if score_f >= 320.0:
        return "매우 강함"
    if score_f >= 240.0:
        return "강함"
    if score_f >= 170.0:
        return "주의"
    return "약함"


def format_entry_message(
    symbol,
    action,
    score,
    price,
    lot,
    reasons,
    pos_count,
    max_pos,
    row: Mapping[str, Any] | None = None,
):
    side = str(action or "").strip().upper() or "UNKNOWN"
    time_str = datetime.now().strftime("%H:%M:%S")
    reason_summary, wait_summary = _summarize_runtime_reasons(reasons)
    lead_axis = _build_runtime_lead_axis(reasons)
    risk_line = _build_runtime_risk_line(side=side, reasons=reasons)
    strength_line = _format_runtime_strength_label(score=float(score or 0.0), reasons=reasons)
    scene_line = _build_runtime_scene_line(row)
    force_line = _build_runtime_force_dominance_line(row)
    alignment_line = _build_runtime_force_alignment_line(side, row)
    context_line = _build_runtime_context_line(row)
    shadow_line = _build_flow_shadow_axes_line(row)
    shadow_zone_line = _build_flow_shadow_zone_line(row)
    flow_start_line = _build_flow_shadow_start_line(row)
    lines = [
        "*진입*",
        f"시각: {time_str}",
        f"심볼: `{symbol}`",
        f"방향: *{side}*",
        f"가격: {price:.5f}",
        f"수량: {lot} lot",
        f"주도축: {lead_axis}",
        f"핵심리스크: {risk_line}",
        f"강도: {strength_line}",
    ]
    if force_line:
        lines.append(f"위/아래 힘: {force_line}")
    if alignment_line:
        lines.append(f"구조 정합: {alignment_line}")
    if context_line:
        lines.append(f"맥락: {context_line}")
    if scene_line:
        lines.append(f"장면: {scene_line}")
    if shadow_line:
        lines.append(shadow_line)
    if shadow_zone_line:
        lines.append(shadow_zone_line)
    if flow_start_line:
        lines.append(flow_start_line)
    lines.append(f"사유: {reason_summary}")
    if wait_summary:
        lines.append(f"대기 맥락: {wait_summary}")
    lines.append(f"보유: {pos_count}/{max_pos}")
    return "\n".join(lines).strip()


def format_reverse_message(
    symbol,
    action,
    score,
    price,
    reasons,
    pos_count,
    max_pos,
    pending: bool = False,
    row: Mapping[str, Any] | None = None,
):
    side = str(action or "").strip().upper() or "UNKNOWN"
    time_str = datetime.now().strftime("%H:%M:%S")
    reason_summary, wait_summary = _summarize_runtime_reasons(reasons)
    status_text = "기존 포지션 정리 후 반전 준비" if bool(pending) else "즉시 반전 진입 준비"
    lead_axis = _build_runtime_lead_axis(reasons)
    risk_line = _build_runtime_risk_line(side=side, reasons=reasons)
    strength_text = _format_runtime_strength_label(score=float(score or 0.0), reasons=reasons)
    scene_line = _build_runtime_scene_line(row)
    transition_line = _build_runtime_transition_line(reasons, row=row)
    force_line = _build_runtime_force_dominance_line(row)
    alignment_line = _build_runtime_force_alignment_line(side, row)
    context_line = _build_runtime_context_line(row)
    shadow_line = _build_flow_shadow_axes_line(row)
    shadow_zone_line = _build_flow_shadow_zone_line(row)
    flow_start_line = _build_flow_shadow_start_line(row)
    lines = [
        "*반전*",
        f"시각: {time_str}",
        f"심볼: `{symbol}`",
        f"방향: *{side}*",
        f"상태: {status_text}",
        f"주도축: {lead_axis}",
        f"핵심리스크: {risk_line}",
        f"강도: {strength_text}",
    ]
    if force_line:
        lines.append(f"위/아래 힘: {force_line}")
    if alignment_line:
        lines.append(f"구조 정합: {alignment_line}")
    if scene_line:
        lines.append(f"장면: {scene_line}")
    if context_line:
        lines.append(f"맥락: {context_line}")
    if transition_line:
        lines.append(f"전이: {transition_line}")
    if shadow_line:
        lines.append(shadow_line)
    if shadow_zone_line:
        lines.append(shadow_zone_line)
    if flow_start_line:
        lines.append(flow_start_line)
    if float(price or 0.0) > 0.0:
        lines.append(f"가격: {float(price):.5f}")
    if reason_summary:
        lines.append(f"사유: {reason_summary}")
    if wait_summary:
        lines.append(f"대기 맥락: {wait_summary}")
    lines.append(f"보유: {int(pos_count)}/{int(max_pos)}")
    return "\n".join(lines).strip()


def build_reverse_message_signature(
    symbol: str,
    action: str,
    score: float,
    reasons: list[str] | tuple[str, ...] | None,
    pending: bool = False,
) -> str:
    primary_summary, wait_summary = _summarize_runtime_reasons(list(reasons or []))
    parts = [
        str(symbol or "").upper().strip(),
        str(action or "").upper().strip(),
        "pending" if bool(pending) else "ready",
        _format_reverse_strength_label(score),
        primary_summary,
        wait_summary,
    ]
    return "|".join(part for part in parts if part)


def format_exit_message(
    symbol,
    profit,
    points,
    entry_price,
    exit_price,
    exit_reason: str | None = None,
    review_context: Mapping[str, Any] | None = None,
):
    outcome = "이익" if profit > 0 else "손실" if profit < 0 else "보합"
    time_str = datetime.now().strftime("%H:%M:%S")
    lines = [
        "*청산*",
        f"시각: {time_str}",
        f"심볼: `{symbol}`",
        f"결과: *{outcome}*",
        f"손익: *{profit:+.2f} USD*",
        f"가격: {entry_price:.5f} -> {exit_price:.5f}",
    ]
    exit_reason_text = _normalize_runtime_reason_body(exit_reason)
    if exit_reason_text:
        lines.append(f"청산사유: {exit_reason_text}")
    review_hint = _build_exit_review_hint(
        profit=float(profit or 0.0),
        points=float(points or 0.0),
        exit_reason=exit_reason,
        review_context=review_context,
    )
    if review_hint:
        lines.append(f"복기힌트: {review_hint}")
    return "\n".join(lines).strip()


def format_wait_message(
    symbol,
    action,
    price,
    pos_count,
    max_pos,
    reason: str | None = None,
    row: Mapping[str, Any] | None = None,
):
    payload = dict(row or {})
    side = str(action or payload.get("direction") or "").strip().upper()
    time_str = datetime.now().strftime("%H:%M:%S")
    wait_reason = _normalize_runtime_reason_body(
        reason
        or payload.get("entry_wait_reason")
        or payload.get("entry_skip_reason")
        or payload.get("blocked_by")
        or payload.get("observe_reason")
    )
    wait_state = str(payload.get("entry_wait_state", "") or "").strip().upper()
    wait_state_label = {
        "HARD_WAIT": "강대기",
        "SOFT_WAIT": "완화대기",
        "WAIT": "대기",
        "OBSERVE": "관찰",
        "BLOCKED": "차단",
    }.get(wait_state, "")
    barrier_hint, belief_hint, forecast_hint = _build_wait_context_hints(payload)
    scene_line = _build_runtime_scene_line(payload)
    force_line = _build_runtime_force_dominance_line(payload)
    alignment_line = _build_runtime_force_alignment_line(side, payload)
    context_line = _build_runtime_context_line(payload)
    shadow_line = _build_flow_shadow_axes_line(payload)
    shadow_zone_line = _build_flow_shadow_zone_line(payload)
    flow_start_line = _build_flow_shadow_start_line(payload)

    lines = [
        "*대기*",
        f"시각: {time_str}",
        f"심볼: `{symbol}`",
    ]
    if side:
        lines.append(f"방향: *{side}*")
    if float(price or 0.0) > 0.0:
        lines.append(f"가격: {float(price):.5f}")
    if wait_reason:
        lines.append(f"대기이유: {wait_reason}")
    release_condition = _build_wait_release_condition(
        side=side,
        row=payload,
        barrier_hint=barrier_hint,
        forecast_hint=forecast_hint,
    )
    if release_condition:
        lines.append(f"해제조건: {release_condition}")
    if force_line:
        lines.append(f"위/아래 힘: {force_line}")
    if alignment_line:
        lines.append(f"구조 정합: {alignment_line}")
    if scene_line:
        lines.append(f"장면: {scene_line}")
    if context_line:
        lines.append(f"맥락: {context_line}")
    if shadow_line:
        lines.append(shadow_line)
    if shadow_zone_line:
        lines.append(shadow_zone_line)
    if flow_start_line:
        lines.append(flow_start_line)
    if wait_state_label:
        lines.append(f"유형: {wait_state_label}")
    if barrier_hint:
        lines.append(f"베리어: {barrier_hint}")
    if belief_hint:
        lines.append(f"빌리프: {belief_hint}")
    if forecast_hint:
        lines.append(f"포리캐스트: {forecast_hint}")
    lines.append(f"보유: {pos_count}/{max_pos}")
    return "\n".join(lines).strip()
