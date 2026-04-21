"""Runtime-safe reader/export helpers for state25 active candidate state."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ACTIVE_CANDIDATE_STATE_CONTRACT_VERSION = "teacher_pattern_active_candidate_state_v1"
STATE25_CANDIDATE_RUNTIME_CONTRACT_VERSION = "state25_candidate_runtime_v1"
STATE25_CANDIDATE_THRESHOLD_SURFACE_CONTRACT_VERSION = (
    "state25_candidate_threshold_surface_v1"
)
STATE25_CANDIDATE_SIZE_SURFACE_CONTRACT_VERSION = "state25_candidate_size_surface_v1"
STATE25_CANDIDATE_WEIGHT_SURFACE_CONTRACT_VERSION = (
    "state25_candidate_weight_surface_v1"
)
STATE25_CANDIDATE_ENTRY_LOG_ONLY_TRACE_CONTRACT_VERSION = (
    "state25_candidate_entry_log_only_trace_v1"
)

STATE25_TEACHER_WEIGHT_OVERRIDE_MIN = 0.25
STATE25_TEACHER_WEIGHT_OVERRIDE_MAX = 2.50
STATE25_TEACHER_WEIGHT_CATALOG = {
    "candle_body_weight": {
        "label_ko": "캔들 몸통 비중",
        "description_ko": "몸통 크기 해석 비중",
    },
    "upper_wick_weight": {
        "label_ko": "윗꼬리 반응 비중",
        "description_ko": "상단 거부/윗꼬리 해석 비중",
    },
    "lower_wick_weight": {
        "label_ko": "아랫꼬리 반응 비중",
        "description_ko": "하단 반등/아랫꼬리 해석 비중",
    },
    "doji_weight": {
        "label_ko": "도지 민감도",
        "description_ko": "도지/중립 캔들 해석 비중",
    },
    "same_color_run_weight": {
        "label_ko": "연속 캔들 비중",
        "description_ko": "같은 방향 연속 캔들 해석 비중",
    },
    "compression_weight": {
        "label_ko": "압축 구간 비중",
        "description_ko": "박스 압축/코일 해석 비중",
    },
    "volume_burst_weight": {
        "label_ko": "거래량 급증 비중",
        "description_ko": "거래량 분출 해석 비중",
    },
    "volume_decay_weight": {
        "label_ko": "거래량 감쇠 비중",
        "description_ko": "거래량 식음 해석 비중",
    },
    "swing_retest_weight": {
        "label_ko": "스윙 재시험 비중",
        "description_ko": "스윙 고점/저점 재시험 해석 비중",
    },
    "setup_keyword_weight": {
        "label_ko": "세팅 키워드 비중",
        "description_ko": "setup id/키워드 해석 비중",
    },
    "prediction_weight": {
        "label_ko": "예측 번들 비중",
        "description_ko": "prediction bundle 확률 해석 비중",
    },
    "directional_bias_weight": {
        "label_ko": "방향 우세 비중",
        "description_ko": "상방/하방 우세 판단 비중",
    },
    "wait_state_weight": {
        "label_ko": "대기 상태 비중",
        "description_ko": "wait/guard 상태 해석 비중",
    },
    "participation_weight": {
        "label_ko": "참여도 비중",
        "description_ko": "시장 참여도 해석 비중",
    },
    "reversal_risk_weight": {
        "label_ko": "반전 위험 비중",
        "description_ko": "반전 위험/false break 해석 비중",
    },
    "gap_context_weight": {
        "label_ko": "갭 문맥 비중",
        "description_ko": "갭/갭필 해석 비중",
    },
    "range_reversal_weight": {
        "label_ko": "박스 반전 비중",
        "description_ko": "range reversal/outer band 해석 비중",
    },
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    items: list[str] = []
    for raw in value:
        text = str(raw or "").strip()
        if text:
            items.append(text)
    return items


def _normalize_weight_key(value: object) -> str:
    return str(value or "").strip().lower()


def _clamp_weight_override(value: object, default: float = 1.0) -> float:
    parsed = _as_float(value, default)
    return max(
        STATE25_TEACHER_WEIGHT_OVERRIDE_MIN,
        min(STATE25_TEACHER_WEIGHT_OVERRIDE_MAX, float(parsed)),
    )


def normalize_state25_teacher_weight_overrides(
    value: object | None,
) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, float] = {}
    for raw_key, raw_value in dict(value).items():
        key = _normalize_weight_key(raw_key)
        if key not in STATE25_TEACHER_WEIGHT_CATALOG:
            continue
        normalized[key] = _clamp_weight_override(raw_value, 1.0)
    return normalized


def describe_state25_teacher_weight_overrides(
    overrides: object | None,
    *,
    baseline_overrides: object | None = None,
) -> list[dict[str, Any]]:
    normalized = normalize_state25_teacher_weight_overrides(overrides)
    baseline = normalize_state25_teacher_weight_overrides(baseline_overrides)
    rows: list[dict[str, Any]] = []
    for key, value in normalized.items():
        meta = dict(STATE25_TEACHER_WEIGHT_CATALOG.get(key, {}))
        before = float(baseline.get(key, 1.0))
        rows.append(
            {
                "weight_key": key,
                "label_ko": str(meta.get("label_ko", key) or key),
                "description_ko": str(meta.get("description_ko", "") or ""),
                "baseline_value": float(before),
                "proposed_value": float(value),
                "delta": round(float(value - before), 6),
            }
        )
    return rows


def render_state25_teacher_weight_override_lines_ko(
    overrides: object | None,
    *,
    baseline_overrides: object | None = None,
) -> list[str]:
    lines: list[str] = []
    for row in describe_state25_teacher_weight_overrides(
        overrides,
        baseline_overrides=baseline_overrides,
    ):
        label = str(row.get("label_ko", "") or "")
        description = str(row.get("description_ko", "") or "")
        proposed_value = float(row.get("proposed_value", 1.0) or 1.0)
        baseline_value = float(row.get("baseline_value", 1.0) or 1.0)
        if abs(proposed_value - baseline_value) < 1e-9:
            delta_text = "유지"
        elif proposed_value > baseline_value:
            delta_text = f"상향 x{proposed_value:.2f}"
        else:
            delta_text = f"하향 x{proposed_value:.2f}"
        if description:
            lines.append(
                f"- {label}: {description} / 기준 x{baseline_value:.2f} -> 제안 x{proposed_value:.2f} ({delta_text})"
            )
        else:
            lines.append(
                f"- {label}: 기준 x{baseline_value:.2f} -> 제안 x{proposed_value:.2f} ({delta_text})"
            )
    return lines


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()


def build_default_active_candidate_state() -> dict[str, Any]:
    return {
        "contract_version": ACTIVE_CANDIDATE_STATE_CONTRACT_VERSION,
        "active_candidate_id": "",
        "active_policy_source": "current_baseline",
        "current_rollout_phase": "disabled",
        "current_binding_mode": "disabled",
        "activated_at": "",
        "last_event": "none",
        "desired_runtime_patch": {
            "apply_now": False,
            "state25_execution_bind_mode": "disabled",
            "state25_execution_symbol_allowlist": [],
            "state25_execution_entry_stage_allowlist": [],
            "state25_threshold_log_only_enabled": False,
            "state25_threshold_log_only_delta_points": 0,
            "state25_threshold_log_only_direction": "",
            "state25_threshold_log_only_reason_keys": [],
            "state25_threshold_log_only_max_adjustment_abs": 0,
            "state25_threshold_bounded_live_enabled": False,
            "state25_threshold_bounded_live_delta_points": 0,
            "state25_threshold_bounded_live_direction": "HARDEN",
            "state25_threshold_bounded_live_reason_keys": [],
            "state25_size_log_only_enabled": False,
            "state25_size_log_only_min_multiplier": 1.0,
            "state25_size_log_only_max_multiplier": 1.0,
            "state25_weight_log_only_enabled": False,
            "state25_weight_bounded_live_enabled": False,
            "state25_teacher_weight_overrides": {},
        },
    }


def _normalize_runtime_patch(payload: dict[str, Any] | None) -> dict[str, Any]:
    patch = dict(build_default_active_candidate_state()["desired_runtime_patch"])
    patch.update(dict(payload or {}))
    min_multiplier = _as_float(
        patch.get("state25_size_log_only_min_multiplier"),
        1.0,
    )
    max_multiplier = _as_float(
        patch.get("state25_size_log_only_max_multiplier"),
        1.0,
    )
    if max_multiplier < min_multiplier:
        min_multiplier, max_multiplier = max_multiplier, min_multiplier
    return {
        "apply_now": _as_bool(patch.get("apply_now"), False),
        "state25_execution_bind_mode": str(
            patch.get("state25_execution_bind_mode", "disabled") or "disabled"
        ),
        "state25_execution_symbol_allowlist": _as_str_list(
            patch.get("state25_execution_symbol_allowlist")
        ),
        "state25_execution_entry_stage_allowlist": _as_str_list(
            patch.get("state25_execution_entry_stage_allowlist")
        ),
        "state25_threshold_log_only_enabled": _as_bool(
            patch.get("state25_threshold_log_only_enabled"),
            False,
        ),
        "state25_threshold_log_only_delta_points": _as_int(
            patch.get("state25_threshold_log_only_delta_points"),
            0,
        ),
        "state25_threshold_log_only_direction": str(
            patch.get("state25_threshold_log_only_direction", "") or ""
        ).upper(),
        "state25_threshold_log_only_reason_keys": _as_str_list(
            patch.get("state25_threshold_log_only_reason_keys")
        ),
        "state25_threshold_log_only_max_adjustment_abs": max(
            0,
            _as_int(patch.get("state25_threshold_log_only_max_adjustment_abs"), 0),
        ),
        "state25_threshold_bounded_live_enabled": _as_bool(
            patch.get("state25_threshold_bounded_live_enabled"),
            False,
        ),
        "state25_threshold_bounded_live_delta_points": max(
            0,
            _as_int(patch.get("state25_threshold_bounded_live_delta_points"), 0),
        ),
        "state25_threshold_bounded_live_direction": str(
            patch.get("state25_threshold_bounded_live_direction", "HARDEN") or "HARDEN"
        ).upper(),
        "state25_threshold_bounded_live_reason_keys": _as_str_list(
            patch.get("state25_threshold_bounded_live_reason_keys")
        ),
        "state25_size_log_only_enabled": _as_bool(
            patch.get("state25_size_log_only_enabled"),
            False,
        ),
        "state25_size_log_only_min_multiplier": max(0.0, min_multiplier),
        "state25_size_log_only_max_multiplier": max(0.0, max_multiplier),
        "state25_weight_log_only_enabled": _as_bool(
            patch.get("state25_weight_log_only_enabled"),
            False,
        ),
        "state25_weight_bounded_live_enabled": _as_bool(
            patch.get("state25_weight_bounded_live_enabled"),
            False,
        ),
        "state25_teacher_weight_overrides": normalize_state25_teacher_weight_overrides(
            patch.get("state25_teacher_weight_overrides")
        ),
    }


def _normalize_active_candidate_state(payload: dict[str, Any] | None) -> dict[str, Any]:
    active = dict(build_default_active_candidate_state())
    active.update(dict(payload or {}))
    return {
        "contract_version": str(
            active.get("contract_version", ACTIVE_CANDIDATE_STATE_CONTRACT_VERSION)
            or ACTIVE_CANDIDATE_STATE_CONTRACT_VERSION
        ),
        "active_candidate_id": str(active.get("active_candidate_id", "") or ""),
        "active_policy_source": str(
            active.get("active_policy_source", "current_baseline") or "current_baseline"
        ),
        "current_rollout_phase": str(
            active.get("current_rollout_phase", "disabled") or "disabled"
        ),
        "current_binding_mode": str(
            active.get("current_binding_mode", "disabled") or "disabled"
        ),
        "activated_at": str(active.get("activated_at", "") or ""),
        "last_event": str(active.get("last_event", "none") or "none"),
        "desired_runtime_patch": _normalize_runtime_patch(
            active.get("desired_runtime_patch", {})
        ),
    }


def load_state25_candidate_runtime_state(
    state_path: str | Path,
    *,
    current_state: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    runtime_now = str(now_iso or _now_iso())
    previous = dict(current_state or {})
    previous_state_fingerprint = str(previous.get("state_fingerprint", "") or "")
    previous_loaded_at = str(previous.get("last_loaded_at", "") or "")
    previous_state_change_at = str(previous.get("last_state_change_at", "") or "")
    previous_apply_at = str(previous.get("last_apply_at", "") or "")
    previous_apply_reason = str(previous.get("last_apply_reason", "") or "")
    previous_rollback_at = str(previous.get("last_rollback_at", "") or "")
    previous_rollback_reason = str(previous.get("last_rollback_reason", "") or "")

    path = Path(state_path)
    source_status = "missing_fallback"
    source_error = ""
    source_exists = path.exists()
    source_mtime_ns = 0
    normalized = build_default_active_candidate_state()

    if source_exists:
        try:
            source_mtime_ns = int(path.stat().st_mtime_ns)
        except OSError:
            source_mtime_ns = 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("active_candidate_state_not_object")
            normalized = _normalize_active_candidate_state(raw)
            source_status = "loaded"
        except Exception as exc:
            normalized = build_default_active_candidate_state()
            source_status = "invalid_fallback"
            source_error = str(exc)

    patch = dict(normalized.get("desired_runtime_patch", {}) or {})
    patch_fingerprint = _fingerprint(patch)
    state_fingerprint = _fingerprint(
        {
            "state_source_status": source_status,
            "active_candidate_id": normalized.get("active_candidate_id", ""),
            "active_policy_source": normalized.get("active_policy_source", ""),
            "current_rollout_phase": normalized.get("current_rollout_phase", ""),
            "current_binding_mode": normalized.get("current_binding_mode", ""),
            "desired_runtime_patch": patch,
        }
    )
    changed = state_fingerprint != previous_state_fingerprint
    apply_requested = _as_bool(patch.get("apply_now"), False)
    pending_apply_action = "none"
    if changed and source_status == "loaded" and apply_requested:
        if str(normalized.get("current_binding_mode", "disabled") or "disabled") == "disabled":
            pending_apply_action = "rollback_disable"
            previous_rollback_at = runtime_now
            rollback_reason = str(normalized.get("last_event", "") or "").strip()
            previous_rollback_reason = rollback_reason if rollback_reason and rollback_reason != "none" else "rollback_disable"
        else:
            apply_reason = str(normalized.get("last_event", "") or "").strip()
            pending_apply_action = apply_reason if apply_reason and apply_reason != "none" else "promote_log_only"
            previous_apply_at = runtime_now
            previous_apply_reason = pending_apply_action

    return {
        "contract_version": STATE25_CANDIDATE_RUNTIME_CONTRACT_VERSION,
        "available": source_status == "loaded",
        "state_source_status": source_status,
        "active_candidate_state_path": str(path),
        "active_candidate_id": str(normalized.get("active_candidate_id", "") or ""),
        "active_policy_source": str(
            normalized.get("active_policy_source", "current_baseline") or "current_baseline"
        ),
        "current_rollout_phase": str(
            normalized.get("current_rollout_phase", "disabled") or "disabled"
        ),
        "current_binding_mode": str(
            normalized.get("current_binding_mode", "disabled") or "disabled"
        ),
        "apply_requested": bool(apply_requested),
        "pending_apply_action": pending_apply_action,
        "state_fingerprint": state_fingerprint,
        "patch_fingerprint": patch_fingerprint,
        "changed_since_last_refresh": bool(changed),
        "last_refresh_at": runtime_now,
        "last_loaded_at": runtime_now if source_status == "loaded" else previous_loaded_at,
        "last_state_change_at": runtime_now if changed else previous_state_change_at,
        "activated_at": str(normalized.get("activated_at", "") or ""),
        "last_event": str(normalized.get("last_event", "none") or "none"),
        "last_apply_at": previous_apply_at,
        "last_apply_reason": previous_apply_reason,
        "last_rollback_at": previous_rollback_at,
        "last_rollback_reason": previous_rollback_reason,
        "source_file_exists": bool(source_exists),
        "source_file_mtime_ns": int(source_mtime_ns),
        "source_error": source_error,
        "desired_runtime_patch": patch,
    }


def build_state25_candidate_threshold_surface_v1(
    runtime_state: dict[str, Any] | None,
    *,
    baseline_entry_threshold: float | int = 0.0,
) -> dict[str, Any]:
    state = dict(runtime_state or {})
    patch = dict(state.get("desired_runtime_patch", {}) or {})
    mode = str(state.get("current_binding_mode", "disabled") or "disabled")
    log_only_enabled = bool(
        mode != "disabled" and _as_bool(patch.get("state25_threshold_log_only_enabled"), False)
    )
    bounded_live_enabled = bool(
        mode in {"bounded_live", "canary"}
        and _as_bool(patch.get("state25_threshold_bounded_live_enabled"), False)
    )
    enabled = bool(log_only_enabled or bounded_live_enabled)
    baseline_threshold = float(baseline_entry_threshold or 0.0)
    bounded_live_delta = max(
        0,
        _as_int(patch.get("state25_threshold_bounded_live_delta_points"), 0),
    )
    log_only_delta_points = _as_int(
        patch.get("state25_threshold_log_only_delta_points"),
        0,
    )
    log_only_direction = str(
        patch.get("state25_threshold_log_only_direction", "") or ""
    ).upper()
    if log_only_enabled and log_only_delta_points != 0:
        candidate_log_only_threshold = float(baseline_threshold + float(log_only_delta_points))
    else:
        candidate_log_only_threshold = (
            baseline_threshold
            - float(max(0, _as_int(patch.get("state25_threshold_log_only_max_adjustment_abs"), 0)))
            if log_only_enabled
            else baseline_threshold
        )
    return {
        "contract_version": STATE25_CANDIDATE_THRESHOLD_SURFACE_CONTRACT_VERSION,
        "enabled": enabled,
        "mode": mode if enabled else "disabled",
        "apply_requested": bool(state.get("apply_requested", False)),
        "symbol_scope": _as_str_list(patch.get("state25_execution_symbol_allowlist")),
        "entry_stage_scope": _as_str_list(
            patch.get("state25_execution_entry_stage_allowlist")
        ),
        "baseline_entry_threshold": baseline_threshold,
        "actual_live_entry_threshold": (
            float(baseline_threshold + float(bounded_live_delta))
            if bounded_live_enabled
            else baseline_threshold
        ),
        "log_only_enabled": bool(log_only_enabled),
        "bounded_live_enabled": bool(bounded_live_enabled),
        "candidate_log_only_entry_threshold_hint": float(candidate_log_only_threshold),
        "log_only_delta_points": int(log_only_delta_points),
        "log_only_direction": str(log_only_direction),
        "log_only_reason_keys": _as_str_list(
            patch.get("state25_threshold_log_only_reason_keys")
        ),
        "max_adjustment_abs": max(
            0,
            _as_int(patch.get("state25_threshold_log_only_max_adjustment_abs"), 0),
        ),
        "bounded_live_delta_points": int(bounded_live_delta),
        "bounded_live_direction": str(
            patch.get("state25_threshold_bounded_live_direction", "HARDEN") or "HARDEN"
        ).upper(),
        "bounded_live_reason_keys": _as_str_list(
            patch.get("state25_threshold_bounded_live_reason_keys")
        ),
    }


def build_state25_candidate_size_surface_v1(
    runtime_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = dict(runtime_state or {})
    patch = dict(state.get("desired_runtime_patch", {}) or {})
    mode = str(state.get("current_binding_mode", "disabled") or "disabled")
    enabled = bool(
        mode != "disabled" and _as_bool(patch.get("state25_size_log_only_enabled"), False)
    )
    return {
        "contract_version": STATE25_CANDIDATE_SIZE_SURFACE_CONTRACT_VERSION,
        "enabled": enabled,
        "mode": mode if enabled else "disabled",
        "apply_requested": bool(state.get("apply_requested", False)),
        "symbol_scope": _as_str_list(patch.get("state25_execution_symbol_allowlist")),
        "baseline_size_multiplier": 1.0,
        "actual_live_size_multiplier": 1.0,
        "candidate_log_only_min_multiplier": _as_float(
            patch.get("state25_size_log_only_min_multiplier"),
            1.0,
        ),
        "candidate_log_only_max_multiplier": _as_float(
            patch.get("state25_size_log_only_max_multiplier"),
            1.0,
        ),
    }


def build_state25_candidate_weight_surface_v1(
    runtime_state: dict[str, Any] | None,
    *,
    symbol: str = "",
    entry_stage: str = "",
) -> dict[str, Any]:
    state = dict(runtime_state or {})
    patch = dict(state.get("desired_runtime_patch", {}) or {})
    mode = str(state.get("current_binding_mode", "disabled") or "disabled")
    symbol_scope = _as_str_list(patch.get("state25_execution_symbol_allowlist"))
    entry_stage_scope = _as_str_list(
        patch.get("state25_execution_entry_stage_allowlist")
    )
    symbol_scope_hit = bool((not symbol_scope) or str(symbol or "").upper().strip() in symbol_scope)
    stage_scope_hit = bool((not entry_stage_scope) or str(entry_stage or "").upper().strip() in entry_stage_scope)
    log_only_enabled = bool(
        mode != "disabled"
        and _as_bool(patch.get("state25_weight_log_only_enabled"), False)
        and symbol_scope_hit
        and stage_scope_hit
    )
    bounded_live_enabled = bool(
        mode in {"bounded_live", "canary"}
        and _as_bool(patch.get("state25_weight_bounded_live_enabled"), False)
        and symbol_scope_hit
        and stage_scope_hit
    )
    enabled = bool(log_only_enabled or bounded_live_enabled)
    overrides = normalize_state25_teacher_weight_overrides(
        patch.get("state25_teacher_weight_overrides")
    )
    return {
        "contract_version": STATE25_CANDIDATE_WEIGHT_SURFACE_CONTRACT_VERSION,
        "enabled": enabled,
        "mode": mode if enabled else "disabled",
        "apply_requested": bool(state.get("apply_requested", False)),
        "symbol_scope": symbol_scope,
        "entry_stage_scope": entry_stage_scope,
        "symbol_scope_hit": bool(symbol_scope_hit),
        "entry_stage_scope_hit": bool(stage_scope_hit),
        "log_only_enabled": bool(log_only_enabled),
        "bounded_live_enabled": bool(bounded_live_enabled),
        "weight_override_count": int(len(overrides)),
        "teacher_weight_overrides": overrides if enabled else {},
        "live_teacher_weight_overrides": overrides if bounded_live_enabled else {},
        "log_only_teacher_weight_overrides": overrides if log_only_enabled else {},
        "teacher_weight_override_display_ko": (
            render_state25_teacher_weight_override_lines_ko(overrides) if enabled else []
        ),
    }


def resolve_state25_candidate_live_weight_overrides_v1(
    runtime_state: dict[str, Any] | None,
    *,
    symbol: str = "",
    entry_stage: str = "",
) -> dict[str, float]:
    surface = build_state25_candidate_weight_surface_v1(
        runtime_state,
        symbol=symbol,
        entry_stage=entry_stage,
    )
    return normalize_state25_teacher_weight_overrides(
        surface.get("live_teacher_weight_overrides")
    )


def resolve_state25_candidate_live_threshold_adjustment_v1(
    runtime_state: dict[str, Any] | None,
    *,
    symbol: str = "",
    entry_stage: str = "",
    baseline_entry_threshold: float | int = 0.0,
) -> dict[str, Any]:
    state = dict(runtime_state or {})
    patch = dict(state.get("desired_runtime_patch", {}) or {})
    mode = str(state.get("current_binding_mode", "disabled") or "disabled")
    symbol_scope = _as_str_list(patch.get("state25_execution_symbol_allowlist"))
    entry_stage_scope = _as_str_list(
        patch.get("state25_execution_entry_stage_allowlist")
    )
    symbol_scope_hit = bool((not symbol_scope) or str(symbol or "").upper().strip() in symbol_scope)
    stage_scope_hit = bool((not entry_stage_scope) or str(entry_stage or "").upper().strip() in entry_stage_scope)
    enabled = bool(
        mode in {"bounded_live", "canary"}
        and _as_bool(patch.get("state25_threshold_bounded_live_enabled"), False)
        and symbol_scope_hit
        and stage_scope_hit
    )
    baseline = float(baseline_entry_threshold or 0.0)
    delta_points = max(
        0,
        _as_int(patch.get("state25_threshold_bounded_live_delta_points"), 0),
    )
    candidate = float(baseline + float(delta_points)) if enabled else baseline
    return {
        "enabled": bool(enabled),
        "mode": mode if enabled else "disabled",
        "symbol_scope_hit": bool(symbol_scope_hit),
        "entry_stage_scope_hit": bool(stage_scope_hit),
        "baseline_entry_threshold": float(baseline),
        "candidate_effective_entry_threshold": float(candidate),
        "threshold_delta_points": float(candidate - baseline),
        "threshold_delta_direction": str(
            patch.get("state25_threshold_bounded_live_direction", "HARDEN") or "HARDEN"
        ).upper(),
        "threshold_delta_reason_keys": _as_str_list(
            patch.get("state25_threshold_bounded_live_reason_keys")
        ),
    }


def build_state25_candidate_entry_log_only_trace_v1(
    runtime_state: dict[str, Any] | None,
    *,
    symbol: str,
    entry_stage: str,
    actual_effective_entry_threshold: float | int,
    actual_size_multiplier: float | int,
) -> dict[str, Any]:
    state = dict(runtime_state or {})
    patch = dict(state.get("desired_runtime_patch", {}) or {})
    symbol_u = str(symbol or "").upper().strip()
    stage_u = str(entry_stage or "").upper().strip()
    binding_mode = str(state.get("current_binding_mode", "disabled") or "disabled")
    rollout_phase = str(state.get("current_rollout_phase", "disabled") or "disabled")
    symbol_scope = _as_str_list(patch.get("state25_execution_symbol_allowlist"))
    entry_stage_scope = _as_str_list(
        patch.get("state25_execution_entry_stage_allowlist")
    )
    symbol_scope_hit = bool((not symbol_scope) or symbol_u in symbol_scope)
    stage_scope_hit = bool((not entry_stage_scope) or stage_u in entry_stage_scope)
    threshold_enabled = bool(
        binding_mode != "disabled"
        and _as_bool(patch.get("state25_threshold_log_only_enabled"), False)
        and symbol_scope_hit
        and stage_scope_hit
    )
    size_enabled = bool(
        binding_mode != "disabled"
        and _as_bool(patch.get("state25_size_log_only_enabled"), False)
        and symbol_scope_hit
    )
    weight_surface = build_state25_candidate_weight_surface_v1(
        state,
        symbol=symbol_u,
        entry_stage=stage_u,
    )
    threshold_live = resolve_state25_candidate_live_threshold_adjustment_v1(
        state,
        symbol=symbol_u,
        entry_stage=stage_u,
        baseline_entry_threshold=float(actual_effective_entry_threshold or 0.0),
    )
    threshold_max_adjustment = max(
        0,
        _as_int(patch.get("state25_threshold_log_only_max_adjustment_abs"), 0),
    )
    threshold_log_only_delta_points = _as_int(
        patch.get("state25_threshold_log_only_delta_points"),
        0,
    )
    threshold_log_only_direction = str(
        patch.get("state25_threshold_log_only_direction", "") or ""
    ).upper()
    actual_threshold = float(actual_effective_entry_threshold or 0.0)
    if threshold_enabled and threshold_log_only_delta_points != 0:
        candidate_threshold = max(
            1.0,
            actual_threshold + float(threshold_log_only_delta_points),
        )
    else:
        candidate_threshold = (
            max(1.0, actual_threshold - float(threshold_max_adjustment))
            if threshold_enabled
            else actual_threshold
        )
    min_multiplier = max(
        0.0,
        _as_float(patch.get("state25_size_log_only_min_multiplier"), 1.0),
    )
    max_multiplier = max(
        min_multiplier,
        _as_float(patch.get("state25_size_log_only_max_multiplier"), 1.0),
    )
    actual_multiplier = max(0.0, _as_float(actual_size_multiplier, 1.0))
    candidate_multiplier = (
        max(min_multiplier, min(max_multiplier, actual_multiplier))
        if size_enabled
        else actual_multiplier
    )
    return {
        "contract_version": STATE25_CANDIDATE_ENTRY_LOG_ONLY_TRACE_CONTRACT_VERSION,
        "state_source_status": str(
            state.get("state_source_status", "missing_fallback") or "missing_fallback"
        ),
        "active_candidate_id": str(state.get("active_candidate_id", "") or ""),
        "active_policy_source": str(
            state.get("active_policy_source", "current_baseline") or "current_baseline"
        ),
        "rollout_phase": rollout_phase,
        "binding_mode": binding_mode,
        "symbol": symbol_u,
        "entry_stage": stage_u,
        "apply_requested": bool(state.get("apply_requested", False)),
        "threshold_symbol_scope_hit": bool(symbol_scope_hit),
        "threshold_stage_scope_hit": bool(stage_scope_hit),
        "threshold_log_only_enabled": bool(threshold_enabled),
        "threshold_log_only_delta_points": int(threshold_log_only_delta_points),
        "threshold_log_only_direction": str(threshold_log_only_direction),
        "threshold_log_only_reason_keys": _as_str_list(
            patch.get("state25_threshold_log_only_reason_keys")
        ),
        "actual_effective_entry_threshold": actual_threshold,
        "candidate_effective_entry_threshold": float(candidate_threshold),
        "candidate_entry_threshold_delta": round(
            float(candidate_threshold - actual_threshold), 6
        ),
        "threshold_max_adjustment_abs": int(threshold_max_adjustment),
        "size_symbol_scope_hit": bool(symbol_scope_hit),
        "size_log_only_enabled": bool(size_enabled),
        "actual_size_multiplier": float(actual_multiplier),
        "candidate_size_multiplier": float(candidate_multiplier),
        "candidate_size_multiplier_delta": round(
            float(candidate_multiplier - actual_multiplier), 6
        ),
        "candidate_size_min_multiplier": float(min_multiplier),
        "candidate_size_max_multiplier": float(max_multiplier),
        "weight_symbol_scope_hit": bool(weight_surface.get("symbol_scope_hit", False)),
        "weight_stage_scope_hit": bool(weight_surface.get("entry_stage_scope_hit", False)),
        "threshold_bounded_live_enabled": bool(threshold_live.get("enabled", False)),
        "threshold_bounded_live_delta_points": float(
            threshold_live.get("threshold_delta_points", 0.0) or 0.0
        ),
        "threshold_bounded_live_reason_keys": _as_str_list(
            threshold_live.get("threshold_delta_reason_keys")
        ),
        "weight_log_only_enabled": bool(weight_surface.get("log_only_enabled", False)),
        "weight_bounded_live_enabled": bool(
            weight_surface.get("bounded_live_enabled", False)
        ),
        "teacher_weight_override_count": int(weight_surface.get("weight_override_count", 0) or 0),
        "teacher_weight_override_keys": list(
            dict(weight_surface.get("teacher_weight_overrides", {}) or {}).keys()
        ),
        "teacher_weight_overrides": dict(
            weight_surface.get("teacher_weight_overrides", {}) or {}
        ),
        "teacher_weight_override_display_ko": list(
            weight_surface.get("teacher_weight_override_display_ko", []) or []
        ),
    }
