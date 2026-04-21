from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from backend.services.symbol_temperament import canonical_symbol, resolve_probe_scene_direction
from backend.trading.chart_flow_distribution import build_chart_flow_distribution_report, write_chart_flow_distribution_report
from backend.trading.chart_symbol_override_policy import build_symbol_override_policy_v1
import backend.trading.engine.core.observe_confirm_router as observe_confirm_router
from backend.trading.engine.core.models import (
    BarrierState,
    BeliefState,
    EvidenceVector,
    ObserveConfirmSnapshot,
    PositionSnapshot,
    PositionVector,
    ResponseRawSnapshot,
    StateVector,
    StateVectorV2,
    TradeManagementForecast,
    TransitionForecast,
)
from backend.trading.engine.response.builder import build_response_vector_execution_bridge_from_raw


_COMPARE_HISTORY_MAXLEN = 64
_COMPARE_HISTORY_RETENTION_SEC = 12 * 60 * 60
_SUPPORTED_MODES = {"OFF", "SAMPLED", "ALWAYS"}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _analysis_dir() -> Path:
    return (_project_root() / "data" / "analysis").resolve()


def _runtime_detail_default_path() -> Path:
    return (_project_root() / "data" / "runtime_status.detail.json").resolve()


def _resolve_path(raw_path: str | Path | None, *, default_path: Path | None = None) -> Path | None:
    if raw_path is None or str(raw_path).strip() == "":
        return default_path.resolve() if default_path is not None else None
    path = Path(raw_path)
    if not path.is_absolute():
        path = (_project_root() / path).resolve()
    return path.resolve()


def resolve_chart_flow_baseline_compare_mode() -> str:
    raw_mode = str(os.getenv("CHART_FLOW_BASELINE_COMPARE_MODE", "OFF") or "").strip().upper()
    return raw_mode if raw_mode in _SUPPORTED_MODES else "OFF"


def resolve_chart_flow_baseline_compare_interval_minutes() -> int:
    try:
        interval = int(float(str(os.getenv("CHART_FLOW_BASELINE_COMPARE_INTERVAL_MINUTES", "15") or "15")))
    except (TypeError, ValueError):
        interval = 15
    return max(1, int(interval))


def resolve_chart_flow_baseline_compare_state_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_BASELINE_COMPARE_STATE_PATH", ""),
        default_path=_analysis_dir() / "chart_flow_baseline_compare_state.json",
    )


def resolve_chart_flow_compare_override_distribution_output_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_COMPARE_OVERRIDE_DISTRIBUTION_PATH", ""),
        default_path=_analysis_dir() / "chart_flow_distribution_compare_override_latest.json",
    )


def resolve_chart_flow_baseline_distribution_output_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_BASELINE_DISTRIBUTION_PATH", ""),
        default_path=_analysis_dir() / "chart_flow_distribution_baseline_latest.json",
    )


def resolve_chart_flow_compare_override_history_output_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_COMPARE_OVERRIDE_HISTORY_PATH", ""),
        default_path=_analysis_dir() / "chart_flow_compare_override_history_latest.json",
    )


def resolve_chart_flow_compare_baseline_history_output_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_COMPARE_BASELINE_HISTORY_PATH", ""),
        default_path=_analysis_dir() / "chart_flow_compare_baseline_history_latest.json",
    )


def resolve_chart_flow_baseline_compare_runtime_status_detail_path() -> Path:
    return _resolve_path(
        os.getenv("CHART_FLOW_BASELINE_COMPARE_RUNTIME_DETAIL_PATH", ""),
        default_path=_runtime_detail_default_path(),
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(parsed) if parsed == parsed else float(default)


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _load_json_document(path: str | Path | None):
    resolved = _resolve_path(path)
    if resolved is None or not resolved.exists():
        return None
    try:
        raw_text = resolved.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except (TypeError, ValueError):
        return None


def _write_json_document(path: str | Path, payload: dict) -> Path:
    resolved = _resolve_path(path)
    assert resolved is not None
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved


def _read_state(path: str | Path | None) -> dict:
    payload = _load_json_document(path)
    return dict(payload or {}) if isinstance(payload, dict) else {}


def _write_state(path: str | Path, *, mode: str, interval_minutes: int, last_run_ts: int) -> Path:
    payload = {
        "contract_version": "chart_flow_baseline_compare_state_v1",
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": str(mode or "OFF").upper(),
        "interval_minutes": int(max(1, int(interval_minutes or 1))),
        "last_run_ts": int(max(0, int(last_run_ts or 0))),
    }
    return _write_json_document(path, payload)


def _load_shadow_history(path: str | Path | None) -> dict[str, list[dict]]:
    payload = _load_json_document(path)
    if not isinstance(payload, dict):
        return {}
    events_by_symbol = dict(payload.get("events_by_symbol", {}) or {})
    history: dict[str, list[dict]] = {}
    for symbol, events in events_by_symbol.items():
        if not isinstance(events, list):
            continue
        normalized_symbol = canonical_symbol(symbol)
        history[normalized_symbol] = [dict(event) for event in events if isinstance(event, dict)]
    return history


def _write_shadow_history(
    history_by_symbol: dict[str, list[dict]],
    *,
    path: str | Path,
    baseline_mode: str,
    window_mode: str,
    window_value: int,
) -> Path:
    payload = {
        "contract_version": "chart_flow_compare_shadow_history_v1",
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "baseline_mode": str(baseline_mode or ""),
        "window": {"mode": str(window_mode or "candles"), "value": int(max(1, int(window_value or 1)))},
        "events_by_symbol": {
            canonical_symbol(symbol): [dict(event) for event in list(events or []) if isinstance(event, dict)]
            for symbol, events in sorted(dict(history_by_symbol or {}).items())
        },
    }
    return _write_json_document(path, payload)


def _is_enabled_dict_type(field_type: Any) -> Any:
    if isinstance(field_type, type) and is_dataclass(field_type):
        return field_type
    origin = get_origin(field_type)
    if origin is None:
        return None
    for candidate in get_args(field_type):
        if isinstance(candidate, type) and is_dataclass(candidate):
            return candidate
    return None


def _build_dataclass(model_cls, payload):
    if isinstance(payload, model_cls):
        return payload
    raw = dict(payload or {}) if isinstance(payload, dict) else {}
    type_hints = get_type_hints(model_cls)
    kwargs = {}
    for field in fields(model_cls):
        if field.name not in raw:
            continue
        value = raw.get(field.name)
        nested_cls = _is_enabled_dict_type(type_hints.get(field.name, field.type))
        if nested_cls is not None and isinstance(value, dict):
            kwargs[field.name] = _build_dataclass(nested_cls, value)
            continue
        kwargs[field.name] = copy.deepcopy(value)
    return model_cls(**kwargs)


def _disable_symbol_override_policy(source_policy: dict | None = None) -> dict:
    payload = copy.deepcopy(source_policy or build_symbol_override_policy_v1())

    def _walk(node):
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if str(key) == "enabled":
                    out[key] = False
                else:
                    out[key] = _walk(value)
            return out
        if isinstance(node, list):
            return [_walk(item) for item in node]
        return copy.deepcopy(node)

    return _walk(payload)


def _extract_latest_signal_rows(runtime_status_detail: dict | None) -> dict[str, dict]:
    payload = dict(runtime_status_detail or {}) if isinstance(runtime_status_detail, dict) else {}
    latest_rows = dict(payload.get("latest_signal_by_symbol", {}) or {})
    return {
        canonical_symbol(symbol): dict(row)
        for symbol, row in latest_rows.items()
        if isinstance(row, dict) and str(symbol or "").strip()
    }


@contextmanager
def _router_symbol_override_policy(policy: dict | None):
    prev = getattr(observe_confirm_router, "_SYMBOL_OVERRIDE_POLICY_V1", {})
    if policy is not None:
        observe_confirm_router._SYMBOL_OVERRIDE_POLICY_V1 = copy.deepcopy(policy)
    try:
        yield
    finally:
        observe_confirm_router._SYMBOL_OVERRIDE_POLICY_V1 = prev


def _painter_classes() -> tuple[type, type]:
    from backend.trading.chart_painter import Painter

    class _BaselineShadowPainter(Painter):
        _SYMBOL_OVERRIDE_POLICY_V1 = _disable_symbol_override_policy(Painter._SYMBOL_OVERRIDE_POLICY_V1)

    return Painter, _BaselineShadowPainter


def _pick_probe_scene_id(source_row: dict, observe_payload: dict) -> str:
    raw_meta = dict((observe_payload.get("metadata") or {}))
    temperament = dict(raw_meta.get("symbol_probe_temperament_v1") or {})
    return str(
        source_row.get("probe_scene_id")
        or source_row.get("edge_execution_scene_id")
        or temperament.get("scene_id")
        or ""
    ).strip()


def _candidate_support_from_semantics(*, side: str, buy_support: float, sell_support: float, confidence: float) -> float:
    if str(side or "").upper() == "BUY":
        return max(float(buy_support), float(confidence))
    if str(side or "").upper() == "SELL":
        return max(float(sell_support), float(confidence))
    return max(float(buy_support), float(sell_support), float(confidence))


def _derive_quick_trace_state(
    *,
    action: str,
    reason: str,
    blocked_by: str,
    probe_candidate_active: bool,
) -> str:
    action_u = str(action or "").upper()
    reason_n = str(reason or "").strip().lower()
    blocked_n = str(blocked_by or "").strip().lower()
    if probe_candidate_active and blocked_n:
        return "PROBE_CANDIDATE_BLOCKED"
    if probe_candidate_active:
        return "PROBE_CANDIDATE"
    if action_u == "WAIT":
        if blocked_n:
            return "WAIT_BLOCKED"
        if reason_n:
            return "WAIT"
    return ""


def _build_shadow_row(source_row: dict, observe_payload: dict) -> dict:
    observe = dict(observe_payload or {})
    observe_meta = dict(observe.get("metadata") or {})
    edge_pair = dict(observe_meta.get("edge_pair_law_v1") or {})
    readiness = dict(observe_meta.get("semantic_readiness_bridge_v1") or {})
    final_readiness = dict(readiness.get("final") or {})
    action = str(observe.get("action", "") or "").upper()
    side = str(observe.get("side", "") or "").upper()
    reason = str(observe.get("reason", "") or "")
    probe_scene_id = _pick_probe_scene_id(source_row, observe)
    scene_side = resolve_probe_scene_direction(
        probe_scene_id,
        reason=reason,
        side=side,
        action=action,
    )
    support_side = side or scene_side or str(edge_pair.get("winner_side", "") or "").upper()
    buy_support = _safe_float(final_readiness.get("buy_support"), 0.0)
    sell_support = _safe_float(final_readiness.get("sell_support"), 0.0)
    confidence = _safe_float(observe.get("confidence"), 0.0)
    probe_candidate_active = bool(
        action == "WAIT"
        and (
            "_probe_observe" in str(reason or "").lower()
            or scene_side in {"BUY", "SELL"}
        )
    )
    blocked_by = str(
        observe_meta.get("blocked_guard")
        or observe_meta.get("blocked_by")
        or ""
    ).strip()
    action_none_reason = str(
        observe_meta.get("blocked_reason")
        or observe_meta.get("action_none_reason")
        or ""
    ).strip()
    probe_pair_gap = _safe_float(
        edge_pair.get("pair_gap", source_row.get("probe_pair_gap")),
        0.0,
    )
    return {
        "observe_confirm_v2": observe,
        "observe_action": action,
        "observe_side": side,
        "observe_reason": reason,
        "edge_pair_law_v1": edge_pair,
        "entry_decision_result_v1": {},
        "exit_wait_state_v1": {},
        "box_state": str(source_row.get("box_state", "") or ""),
        "bb_state": str(source_row.get("bb_state", "") or ""),
        "probe_scene_id": probe_scene_id,
        "my_position_count": _safe_float(source_row.get("my_position_count"), 0.0),
        "probe_candidate_active": probe_candidate_active,
        "probe_plan_active": False,
        "probe_plan_ready": False,
        "probe_candidate_support": _candidate_support_from_semantics(
            side=support_side,
            buy_support=buy_support,
            sell_support=sell_support,
            confidence=confidence,
        ),
        "probe_pair_gap": probe_pair_gap,
        "blocked_by": blocked_by,
        "action_none_reason": action_none_reason,
        "quick_trace_state": _derive_quick_trace_state(
            action=action,
            reason=reason,
            blocked_by=blocked_by,
            probe_candidate_active=probe_candidate_active,
        ),
    }


def _event_payload_from_shadow_row(*, symbol: str, shadow_row: dict, event_ts: int, painter_cls) -> dict:
    event_kind, side, reason = painter_cls._resolve_flow_event_kind(symbol, shadow_row)
    score = painter_cls._flow_event_signal_score(shadow_row, event_kind, side=side)
    level = painter_cls._flow_event_strength_level(score=score)
    return {
        "ts": int(event_ts),
        "price": 0.0,
        "event_kind": str(event_kind or ""),
        "reason": str(reason or ""),
        "side": str(side or ""),
        "score": float(score),
        "level": int(level),
        "blocked_by": str(shadow_row.get("blocked_by", "") or ""),
        "action_none_reason": str(shadow_row.get("action_none_reason", "") or ""),
        "box_state": str(shadow_row.get("box_state", "") or ""),
        "bb_state": str(shadow_row.get("bb_state", "") or ""),
        "probe_scene_id": str(shadow_row.get("probe_scene_id", "") or ""),
        "my_position_count": _safe_float(shadow_row.get("my_position_count"), 0.0),
    }


def _append_shadow_event(
    history_by_symbol: dict[str, list[dict]],
    *,
    symbol: str,
    event_payload: dict,
    now_ts: int,
) -> None:
    normalized_symbol = canonical_symbol(symbol)
    min_ts = int(now_ts) - int(_COMPARE_HISTORY_RETENTION_SEC)
    history = [dict(event) for event in list(history_by_symbol.get(normalized_symbol, [])) if isinstance(event, dict)]
    history = [event for event in history if _safe_int(event.get("ts"), 0) >= min_ts]
    if history and _safe_int(history[-1].get("ts"), 0) == _safe_int(event_payload.get("ts"), 0):
        history[-1] = dict(event_payload)
    else:
        history.append(dict(event_payload))
    history_by_symbol[normalized_symbol] = history[-_COMPARE_HISTORY_MAXLEN:]


def _load_compare_report(path: Path | None) -> dict:
    payload = _load_json_document(path)
    return dict(payload or {}) if isinstance(payload, dict) else {}


def _should_run_sampled_compare(*, mode: str, interval_minutes: int, state_payload: dict, now_ts: int) -> tuple[bool, str]:
    mode_u = str(mode or "OFF").upper()
    if mode_u == "OFF":
        return False, "mode_off"
    if mode_u == "ALWAYS":
        return True, "always"
    last_run_ts = _safe_int(state_payload.get("last_run_ts"), 0)
    if last_run_ts <= 0:
        return True, "initial_run"
    wait_seconds = max(60, int(interval_minutes) * 60)
    if int(now_ts) - int(last_run_ts) >= wait_seconds:
        return True, "interval_elapsed"
    return False, "interval_not_due"


def _row_router_inputs(source_row: dict):
    position = _build_dataclass(PositionVector, source_row.get("position_vector_v2") or source_row.get("position_vector") or {})
    position_snapshot = _build_dataclass(
        PositionSnapshot,
        source_row.get("position_snapshot_v2") or source_row.get("position_snapshot") or {},
    )
    response_raw = _build_dataclass(
        ResponseRawSnapshot,
        source_row.get("response_raw_snapshot_v1") or source_row.get("response_raw_snapshot") or {},
    )
    response = build_response_vector_execution_bridge_from_raw(response_raw)
    state_payload = source_row.get("state_vector_v2") or source_row.get("state_vector") or {}
    if str(source_row.get("observe_confirm_input_contract_v2", "") or "").strip():
        state = _build_dataclass(StateVectorV2, state_payload)
    else:
        state = _build_dataclass(StateVectorV2, state_payload) if isinstance(state_payload, dict) else _build_dataclass(StateVector, {})
    evidence = _build_dataclass(EvidenceVector, source_row.get("evidence_vector_v1") or {})
    belief = _build_dataclass(BeliefState, source_row.get("belief_state_v1") or {})
    barrier = _build_dataclass(BarrierState, source_row.get("barrier_state_v1") or {})
    transition = _build_dataclass(TransitionForecast, source_row.get("transition_forecast_v1") or {})
    trade_management = _build_dataclass(
        TradeManagementForecast,
        source_row.get("trade_management_forecast_v1") or {},
    )
    forecast_gap_metrics = dict(source_row.get("forecast_gap_metrics_v1") or {})
    return {
        "position": position,
        "position_snapshot": position_snapshot,
        "response": response,
        "state": state,
        "evidence": evidence,
        "belief": belief,
        "barrier": barrier,
        "transition": transition,
        "trade_management": trade_management,
        "forecast_gap_metrics": forecast_gap_metrics,
    }


def _reroute_observe_snapshot(source_row: dict, *, disabled_symbol_override_policy: dict | None = None) -> ObserveConfirmSnapshot:
    inputs = _row_router_inputs(source_row)
    with _router_symbol_override_policy(disabled_symbol_override_policy):
        return observe_confirm_router.route_observe_confirm(
            inputs["position"],
            inputs["response"],
            inputs["state"],
            inputs["position_snapshot"],
            evidence_vector_v1=inputs["evidence"],
            belief_state_v1=inputs["belief"],
            barrier_state_v1=inputs["barrier"],
            transition_forecast_v1=inputs["transition"],
            trade_management_forecast_v1=inputs["trade_management"],
            forecast_gap_metrics_v1=inputs["forecast_gap_metrics"],
        )


def generate_and_write_chart_flow_baseline_compare_reports(
    *,
    runtime_status_detail: dict | None = None,
    runtime_status_detail_path: str | Path | None = None,
    now_ts: int | None = None,
    window_mode: str = "candles",
    window_value: int = 16,
) -> dict:
    mode = resolve_chart_flow_baseline_compare_mode()
    interval_minutes = resolve_chart_flow_baseline_compare_interval_minutes()
    compare_override_distribution_path = resolve_chart_flow_compare_override_distribution_output_path()
    baseline_distribution_path = resolve_chart_flow_baseline_distribution_output_path()
    compare_override_history_path = resolve_chart_flow_compare_override_history_output_path()
    baseline_history_path = resolve_chart_flow_compare_baseline_history_output_path()
    state_path = resolve_chart_flow_baseline_compare_state_path()
    detail_path = _resolve_path(runtime_status_detail_path, default_path=resolve_chart_flow_baseline_compare_runtime_status_detail_path())
    payload = dict(runtime_status_detail or {}) if isinstance(runtime_status_detail, dict) else {}
    if not payload:
        loaded = _load_json_document(detail_path)
        payload = dict(loaded or {}) if isinstance(loaded, dict) else {}
    compare_override_report = _load_compare_report(compare_override_distribution_path)
    baseline_report = _load_compare_report(baseline_distribution_path)
    state_payload = _read_state(state_path)
    current_ts = int(now_ts if now_ts is not None else datetime.now().timestamp())
    should_run, gate_reason = _should_run_sampled_compare(
        mode=mode,
        interval_minutes=interval_minutes,
        state_payload=state_payload,
        now_ts=current_ts,
    )
    result = {
        "mode": mode,
        "active": bool(mode != "OFF"),
        "ran": False,
        "reason": gate_reason,
        "compare_override_report": compare_override_report,
        "baseline_report": baseline_report,
        "compare_override_distribution_path": compare_override_distribution_path,
        "baseline_distribution_path": baseline_distribution_path,
        "state_path": state_path,
        "runtime_status_detail_path": detail_path,
    }
    if not should_run:
        return result

    latest_rows = _extract_latest_signal_rows(payload)
    if not latest_rows:
        result["reason"] = "latest_signal_rows_unavailable"
        return result

    override_history = _load_shadow_history(compare_override_history_path)
    baseline_history = _load_shadow_history(baseline_history_path)
    disabled_symbol_override_policy = _disable_symbol_override_policy()
    override_painter_cls, baseline_painter_cls = _painter_classes()

    generated_symbol_count = 0
    for symbol, source_row in sorted(latest_rows.items()):
        try:
            override_snapshot = _reroute_observe_snapshot(source_row)
            baseline_snapshot = _reroute_observe_snapshot(
                source_row,
                disabled_symbol_override_policy=disabled_symbol_override_policy,
            )
        except Exception:
            continue

        override_shadow_row = _build_shadow_row(source_row, override_snapshot.to_dict())
        baseline_shadow_row = _build_shadow_row(source_row, baseline_snapshot.to_dict())
        override_event = _event_payload_from_shadow_row(
            symbol=symbol,
            shadow_row=override_shadow_row,
            event_ts=current_ts,
            painter_cls=override_painter_cls,
        )
        baseline_event = _event_payload_from_shadow_row(
            symbol=symbol,
            shadow_row=baseline_shadow_row,
            event_ts=current_ts,
            painter_cls=baseline_painter_cls,
        )
        _append_shadow_event(override_history, symbol=symbol, event_payload=override_event, now_ts=current_ts)
        _append_shadow_event(baseline_history, symbol=symbol, event_payload=baseline_event, now_ts=current_ts)
        generated_symbol_count += 1

    compare_override_report = build_chart_flow_distribution_report(
        override_history,
        window_mode=window_mode,
        window_value=window_value,
        baseline_mode="comparison_override",
        now_ts=current_ts,
    )
    baseline_report = build_chart_flow_distribution_report(
        baseline_history,
        window_mode=window_mode,
        window_value=window_value,
        baseline_mode="baseline_only",
        now_ts=current_ts,
    )
    compare_override_distribution_path = write_chart_flow_distribution_report(
        compare_override_report,
        output_path=compare_override_distribution_path,
    )
    baseline_distribution_path = write_chart_flow_distribution_report(
        baseline_report,
        output_path=baseline_distribution_path,
    )
    _write_shadow_history(
        override_history,
        path=compare_override_history_path,
        baseline_mode="comparison_override",
        window_mode=window_mode,
        window_value=window_value,
    )
    _write_shadow_history(
        baseline_history,
        path=baseline_history_path,
        baseline_mode="baseline_only",
        window_mode=window_mode,
        window_value=window_value,
    )
    _write_state(
        state_path,
        mode=mode,
        interval_minutes=interval_minutes,
        last_run_ts=current_ts,
    )
    result.update(
        {
            "ran": True,
            "reason": "generated",
            "generated_symbol_count": int(generated_symbol_count),
            "compare_override_report": compare_override_report,
            "baseline_report": baseline_report,
            "compare_override_distribution_path": compare_override_distribution_path,
            "baseline_distribution_path": baseline_distribution_path,
        }
    )
    return result
