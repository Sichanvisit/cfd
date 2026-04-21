"""Log-only runtime bridge for checkpoint scene candidates (SA5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_CONTRACT_VERSION = "checkpoint_scene_runtime_bridge_v1"
PATH_CHECKPOINT_SCENE_ACTIVE_CANDIDATE_STATE_VERSION = "checkpoint_scene_active_candidate_state_v1"
PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_VERSION = "checkpoint_scene_log_only_bridge_report_v1"
PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS = [
    "scene_candidate_available",
    "scene_candidate_candidate_id",
    "scene_candidate_binding_mode",
    "scene_candidate_coarse_family",
    "scene_candidate_coarse_confidence",
    "scene_candidate_gate_label",
    "scene_candidate_gate_confidence",
    "scene_candidate_gate_block_level",
    "scene_candidate_fine_label",
    "scene_candidate_fine_confidence",
    "scene_candidate_late_label",
    "scene_candidate_late_confidence",
    "scene_candidate_selected_label",
    "scene_candidate_selected_confidence",
    "scene_candidate_selected_source",
    "scene_candidate_runtime_scene_match",
    "scene_candidate_runtime_gate_match",
    "scene_candidate_reason",
]
PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_PREFIXED_KEYS = {
    key: f"checkpoint_{key}" for key in PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS
}
PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_COLUMNS = [
    "symbol",
    "row_count",
    "bridge_available_row_count",
    "candidate_selected_label_counts",
    "candidate_gate_label_counts",
    "runtime_candidate_scene_match_rate",
    "runtime_candidate_gate_match_rate",
    "high_confidence_scene_disagreement_count",
    "high_confidence_gate_disagreement_count",
    "recommended_focus",
]
PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_DEFAULT_PAYLOAD = {
    "scene_candidate_available": False,
    "scene_candidate_candidate_id": "",
    "scene_candidate_binding_mode": "disabled",
    "scene_candidate_coarse_family": "UNRESOLVED",
    "scene_candidate_coarse_confidence": 0.0,
    "scene_candidate_gate_label": "none",
    "scene_candidate_gate_confidence": 0.0,
    "scene_candidate_gate_block_level": "none",
    "scene_candidate_fine_label": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "scene_candidate_fine_confidence": 0.0,
    "scene_candidate_late_label": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "scene_candidate_late_confidence": 0.0,
    "scene_candidate_selected_label": PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    "scene_candidate_selected_confidence": 0.0,
    "scene_candidate_selected_source": "none",
    "scene_candidate_runtime_scene_match": False,
    "scene_candidate_runtime_gate_match": True,
    "scene_candidate_reason": "scene_candidate_bridge_unavailable",
}
_SCENE_GATE_BLOCK_LEVEL_BY_LABEL = {
    "none": "none",
    "low_edge_state": "entry_block",
    "dead_leg_wait": "all_block",
    "ambiguous_structure": "all_block",
}
_SCENE_LATE_CHECKPOINT_TYPES = {"LATE_TREND_CHECK", "RUNNER_CHECK"}
_TIME_DECAY_RISK_ROW_FAMILIES = {"active_open_loss", "open_loss_protective"}
_TIME_DECAY_RUNNER_FAMILIES = {"runner_secured_continuation"}
_TIME_DECAY_PROFIT_BIAS_FAMILIES = {"profit_trim_bias", "profit_hold_bias"}
_BUNDLE_CACHE: dict[str, dict[str, Any]] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_scene_candidate_root() -> Path:
    return _repo_root() / "models" / "path_checkpoint_scene_candidates"


def default_checkpoint_scene_candidate_latest_run_path() -> Path:
    return default_checkpoint_scene_candidate_root() / "latest_candidate_run.json"


def default_checkpoint_scene_candidate_active_state_path() -> Path:
    return default_checkpoint_scene_candidate_root() / "active_candidate_state.json"


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float) -> float:
    return round(max(0.0, min(0.99, float(value))), 6)


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return dict(json.loads(file_path.read_text(encoding="utf-8")) or {})


def _resolve_latest_run_path(
    *,
    latest_run_path: str | Path | None = None,
    active_state_path: str | Path | None = None,
) -> Path:
    if latest_run_path:
        return Path(latest_run_path)
    if active_state_path:
        return Path(active_state_path).parent / "latest_candidate_run.json"
    return default_checkpoint_scene_candidate_latest_run_path()


def build_default_scene_candidate_runtime_bridge_payload(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_DEFAULT_PAYLOAD)
    if not overrides:
        return payload
    for key in PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS:
        if key not in overrides:
            continue
        value = overrides[key]
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        payload[key] = value
    return payload


def default_checkpoint_scene_log_only_bridge_report_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_scene_log_only_bridge_latest.json"
    )


def apply_checkpoint_scene_runtime_bridge_to_runtime_row(
    runtime_row: dict[str, Any] | None,
    bridge_row: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(runtime_row or {})
    row = dict(bridge_row or {})
    for key in PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS:
        prefixed_key = PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_PREFIXED_KEYS[key]
        payload[prefixed_key] = row.get(key, PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_DEFAULT_PAYLOAD.get(key, ""))
    return payload


def _resolve_implicit_active_state(
    active_state_path: str | Path | None = None,
    *,
    allow_latest_manifest_fallback: bool = False,
) -> dict[str, Any]:
    active_path = Path(active_state_path) if active_state_path else default_checkpoint_scene_candidate_active_state_path()
    active_state = _load_json(active_path)
    if active_state:
        return active_state
    if not allow_latest_manifest_fallback:
        return {}
    latest_manifest = _load_json(default_checkpoint_scene_candidate_latest_run_path())
    if not latest_manifest:
        return {}
    return {
        "contract_version": PATH_CHECKPOINT_SCENE_ACTIVE_CANDIDATE_STATE_VERSION,
        "active_candidate_id": _to_text(latest_manifest.get("candidate_id")),
        "active_policy_source": "scene_candidate",
        "current_rollout_phase": "log_only",
        "current_binding_mode": "log_only",
        "activated_at": _to_text(latest_manifest.get("generated_at")),
        "last_event": "implicit_latest_candidate_log_only",
        "desired_runtime_patch": {
            "apply_now": True,
            "checkpoint_scene_bind_mode": "log_only",
            "checkpoint_scene_action_influence": False,
        },
    }


def ensure_checkpoint_scene_active_candidate_state(
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
) -> dict[str, Any]:
    active_path = Path(active_state_path) if active_state_path else default_checkpoint_scene_candidate_active_state_path()
    active_state = _load_json(active_path)
    latest_manifest = _load_json(_resolve_latest_run_path(latest_run_path=latest_run_path, active_state_path=active_state_path))
    if not latest_manifest:
        return active_state
    latest_candidate_id = _to_text(latest_manifest.get("candidate_id"))
    current_candidate_id = _to_text(active_state.get("active_candidate_id"))
    if active_state and latest_candidate_id and latest_candidate_id == current_candidate_id:
        return active_state
    payload = {
        "contract_version": PATH_CHECKPOINT_SCENE_ACTIVE_CANDIDATE_STATE_VERSION,
        "active_candidate_id": latest_candidate_id,
        "active_policy_source": "scene_candidate",
        "current_rollout_phase": "log_only",
        "current_binding_mode": "log_only",
        "activated_at": now_kst_dt().isoformat(),
        "last_event": "promote_log_only",
        "previous_candidate_id": current_candidate_id,
        "desired_runtime_patch": {
            "apply_now": True,
            "checkpoint_scene_bind_mode": "log_only",
            "checkpoint_scene_action_influence": False,
            "checkpoint_scene_symbol_allowlist": ["BTCUSD", "NAS100", "XAUUSD"],
        },
    }
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _resolve_bundle_path(
    active_state: dict[str, Any],
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
) -> Path | None:
    active_candidate_id = _to_text(active_state.get("active_candidate_id"))
    if not active_candidate_id:
        return None
    latest_manifest = _load_json(_resolve_latest_run_path(latest_run_path=latest_run_path, active_state_path=active_state_path))
    if _to_text(latest_manifest.get("candidate_id")) == active_candidate_id:
        latest_bundle = Path(_to_text(latest_manifest.get("candidate_bundle_path")))
        if latest_bundle.exists():
            return latest_bundle
    bundle_path = default_checkpoint_scene_candidate_latest_run_path().parent / active_candidate_id / "checkpoint_scene_candidate_bundle.joblib"
    return bundle_path if bundle_path.exists() else None


def _load_candidate_bundle(bundle_path: Path | None) -> dict[str, Any]:
    if bundle_path is None or not bundle_path.exists():
        return {}
    cache_key = str(bundle_path)
    mtime_ns = bundle_path.stat().st_mtime_ns
    cached = _BUNDLE_CACHE.get(cache_key)
    if cached and int(cached.get("mtime_ns", 0)) == int(mtime_ns):
        return dict(cached.get("payload", {}) or {})
    payload = dict(joblib.load(bundle_path) or {})
    _BUNDLE_CACHE[cache_key] = {"mtime_ns": int(mtime_ns), "payload": payload}
    return payload


def _predict_task_label(task_bundle: dict[str, Any], checkpoint_ctx: dict[str, Any]) -> tuple[str, float]:
    model = task_bundle.get("model")
    if model is None:
        return "", 0.0
    feature_columns = dict(task_bundle.get("feature_columns", {}) or {})
    categorical_cols = list(feature_columns.get("categorical", []) or [])
    numeric_cols = list(feature_columns.get("numeric", []) or [])
    row: dict[str, Any] = {}
    for column in categorical_cols:
        row[column] = _to_text(checkpoint_ctx.get(column))
    for column in numeric_cols:
        row[column] = _to_float(checkpoint_ctx.get(column), 0.0)
    frame = pd.DataFrame([row], columns=categorical_cols + numeric_cols)
    label = _to_text(model.predict(frame)[0])
    confidence = 0.0
    if hasattr(model, "predict_proba"):
        try:
            probabilities = model.predict_proba(frame)[0]
            confidence = max((float(value) for value in probabilities), default=0.0)
        except Exception:
            confidence = 0.0
    return label, _clamp(confidence)


def _time_decay_selection_guard(row: dict[str, Any], *, label: str, confidence: float) -> tuple[bool, str]:
    selected_label = _to_text(label)
    if selected_label != "time_decay_risk" or confidence <= 0.0:
        return True, ""

    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    surface_name = _to_text(row.get("surface_name"))
    unrealized_state = _to_text(row.get("unrealized_pnl_state")).upper()
    management_action = _to_text(row.get("management_action_label")).upper()
    row_family = _to_text(row.get("checkpoint_rule_family_hint")).lower()
    exit_stage_family = _to_text(row.get("exit_stage_family")).lower()
    current_profit = abs(_to_float(row.get("current_profit"), 0.0))
    giveback_ratio = _to_float(row.get("giveback_ratio"), 0.0)
    full_exit_risk = _to_float(row.get("runtime_full_exit_risk"), 0.0)
    reversal = _to_float(row.get("runtime_reversal_odds"), 0.0)
    continuation = _to_float(row.get("runtime_continuation_odds"), 0.0)
    hold_quality = _to_float(row.get("runtime_hold_quality_score"), 0.0)
    bars_since_last_push = _to_float(row.get("bars_since_last_push"), 0.0)
    bars_since_last_checkpoint = _to_float(row.get("bars_since_last_checkpoint"), 0.0)
    runner_secured = _to_bool(row.get("runner_secured"), False)

    if checkpoint_type not in _SCENE_LATE_CHECKPOINT_TYPES:
        return False, "time_decay_requires_late_checkpoint"

    if surface_name == "protective_exit_surface":
        if (
            unrealized_state == "OPEN_LOSS"
            or management_action == "FULL_EXIT"
            or row_family in _TIME_DECAY_RISK_ROW_FAMILIES
            or full_exit_risk >= 0.65
            or giveback_ratio >= 0.60
            or reversal >= continuation + 0.10
        ):
            return False, "time_decay_protective_overpull_guard"

    if unrealized_state != "FLAT" and current_profit > 0.12:
        return False, "time_decay_nonflat_profit_guard"

    if surface_name == "continuation_hold_surface":
        if row_family in _TIME_DECAY_RUNNER_FAMILIES or exit_stage_family == "runner" or runner_secured:
            return False, "time_decay_runner_secured_guard"

        is_true_late_stall = (
            unrealized_state == "FLAT"
            and current_profit <= 0.05
            and giveback_ratio >= 0.85
            and bars_since_last_push >= 4
            and bars_since_last_checkpoint >= 2
            and (continuation <= 0.58 or hold_quality <= 0.42)
            and reversal < continuation + 0.15
        )
        if row_family == "active_flat_profit" and not is_true_late_stall:
            return False, "time_decay_active_flat_profit_guard"
        if (
            unrealized_state == "OPEN_PROFIT"
            and row_family in _TIME_DECAY_PROFIT_BIAS_FAMILIES
            and current_profit >= 0.03
            and continuation >= 0.70
            and hold_quality >= 0.45
            and giveback_ratio <= 0.75
        ):
            return False, "time_decay_profit_bias_guard"

    return True, ""


def build_checkpoint_scene_log_only_bridge_v1(
    checkpoint_ctx: dict[str, Any] | None,
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
) -> dict[str, Any]:
    row = dict(checkpoint_ctx or {})
    active_state = _resolve_implicit_active_state(active_state_path=active_state_path, allow_latest_manifest_fallback=False)
    binding_mode = _to_text(active_state.get("current_binding_mode"), "disabled") or "disabled"
    if binding_mode != "log_only":
        reason = "scene_candidate_bridge_active_state_missing" if not active_state else "scene_candidate_bridge_not_log_only"
        payload = build_default_scene_candidate_runtime_bridge_payload(
            {
                "scene_candidate_candidate_id": _to_text(active_state.get("active_candidate_id")),
                "scene_candidate_binding_mode": binding_mode,
                "scene_candidate_reason": reason,
            }
        )
        return {
            "contract_version": PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_CONTRACT_VERSION,
            "row": payload,
            "detail": {"active_state": active_state, "tasks": {}},
        }

    bundle = _load_candidate_bundle(
        _resolve_bundle_path(
            active_state,
            active_state_path=active_state_path,
            latest_run_path=latest_run_path,
        )
    )
    tasks = dict(bundle.get("tasks", {}) or {})
    if not tasks:
        payload = build_default_scene_candidate_runtime_bridge_payload(
            {
                "scene_candidate_candidate_id": _to_text(active_state.get("active_candidate_id")),
                "scene_candidate_binding_mode": binding_mode,
                "scene_candidate_reason": "scene_candidate_bundle_unavailable",
            }
        )
        return {
            "contract_version": PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_CONTRACT_VERSION,
            "row": payload,
            "detail": {"active_state": active_state, "tasks": {}},
        }

    coarse_label, coarse_conf = _predict_task_label(dict(tasks.get("coarse_family_task", {}) or {}), row)
    gate_label, gate_conf = _predict_task_label(dict(tasks.get("gate_task", {}) or {}), row)
    fine_label, fine_conf = _predict_task_label(dict(tasks.get("resolved_scene_task", {}) or {}), row)
    late_label, late_conf = _predict_task_label(dict(tasks.get("late_scene_task", {}) or {}), row)

    fine_allowed, fine_guard_reason = _time_decay_selection_guard(row, label=fine_label, confidence=fine_conf)
    late_allowed, late_guard_reason = _time_decay_selection_guard(row, label=late_label, confidence=late_conf)
    effective_fine_label = fine_label if fine_allowed else PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    effective_fine_conf = fine_conf if fine_allowed else 0.0
    effective_late_label = late_label if late_allowed else PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    effective_late_conf = late_conf if late_allowed else 0.0

    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    selected_label = effective_fine_label or PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    selected_conf = effective_fine_conf
    selected_source = "resolved_scene_task" if effective_fine_label != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL else "none"
    if checkpoint_type in _SCENE_LATE_CHECKPOINT_TYPES and effective_late_label != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and effective_late_conf >= max(effective_fine_conf + 0.05, 0.60):
        selected_label = effective_late_label
        selected_conf = effective_late_conf
        selected_source = "late_scene_task"
    gate_label = gate_label or "none"
    gate_block_level = _SCENE_GATE_BLOCK_LEVEL_BY_LABEL.get(gate_label, "none")

    runtime_scene = _to_text(row.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
    runtime_gate = _to_text(row.get("runtime_scene_gate_label"), "none")
    scene_match = bool(selected_label != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and runtime_scene == selected_label)
    gate_match = bool(runtime_gate == gate_label)

    reason_parts = [selected_source or "none"]
    if not fine_allowed and fine_guard_reason:
        reason_parts.append(f"suppressed::{fine_guard_reason}")
    if not late_allowed and late_guard_reason and late_guard_reason != fine_guard_reason:
        reason_parts.append(f"suppressed::{late_guard_reason}")
    if gate_label != "none" and not gate_match and gate_conf >= 0.60:
        reason_parts.append("gate_disagreement_watch")
    if selected_label != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and not scene_match and selected_conf >= 0.60:
        reason_parts.append("scene_disagreement_watch")
    if not reason_parts:
        reason_parts.append("scene_candidate_bridge_balanced")

    payload = build_default_scene_candidate_runtime_bridge_payload(
        {
            "scene_candidate_available": True,
            "scene_candidate_candidate_id": _to_text(active_state.get("active_candidate_id")),
            "scene_candidate_binding_mode": binding_mode,
            "scene_candidate_coarse_family": coarse_label or "UNRESOLVED",
            "scene_candidate_coarse_confidence": coarse_conf,
            "scene_candidate_gate_label": gate_label,
            "scene_candidate_gate_confidence": gate_conf,
            "scene_candidate_gate_block_level": gate_block_level,
            "scene_candidate_fine_label": fine_label or PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
            "scene_candidate_fine_confidence": fine_conf,
            "scene_candidate_late_label": late_label or PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
            "scene_candidate_late_confidence": late_conf,
            "scene_candidate_selected_label": selected_label or PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
            "scene_candidate_selected_confidence": selected_conf,
            "scene_candidate_selected_source": selected_source,
            "scene_candidate_runtime_scene_match": scene_match,
            "scene_candidate_runtime_gate_match": gate_match,
            "scene_candidate_reason": "|".join(reason_parts),
        }
    )
    detail = {
        "active_state": active_state,
        "tasks": {
            "coarse_family_task": {"label": coarse_label, "confidence": coarse_conf},
            "gate_task": {"label": gate_label, "confidence": gate_conf},
            "resolved_scene_task": {"label": fine_label, "confidence": fine_conf},
            "late_scene_task": {"label": late_label, "confidence": late_conf},
        },
    }
    return {
        "contract_version": PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_CONTRACT_VERSION,
        "row": payload,
        "detail": detail,
    }


def _json_counts(counts: dict[str, int]) -> str:
    return json.dumps({str(key): int(value) for key, value in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def build_checkpoint_scene_log_only_bridge_report(
    scene_dataset: pd.DataFrame | None,
    *,
    active_state_path: str | Path | None = None,
    latest_run_path: str | Path | None = None,
    ensure_active_state: bool = True,
    symbols: tuple[str, ...] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = scene_dataset.copy() if scene_dataset is not None and not scene_dataset.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    active_state = (
        ensure_checkpoint_scene_active_candidate_state(active_state_path=active_state_path, latest_run_path=latest_run_path)
        if ensure_active_state
        else _resolve_implicit_active_state(active_state_path=active_state_path, allow_latest_manifest_fallback=False)
    )
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "active_candidate_id": _to_text(active_state.get("active_candidate_id")),
        "binding_mode": _to_text(active_state.get("current_binding_mode"), "disabled") or "disabled",
        "scene_dataset_row_count": 0,
        "bridge_available_row_count": 0,
        "candidate_selected_label_counts": {},
        "candidate_gate_label_counts": {},
        "candidate_selected_source_counts": {},
        "runtime_candidate_scene_match_rate": 0.0,
        "runtime_candidate_gate_match_rate": 0.0,
        "high_confidence_scene_disagreement_count": 0,
        "high_confidence_gate_disagreement_count": 0,
        "disagreement_examples": [],
        "recommended_next_action": "activate_scene_candidate_log_only_before_sa6",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_COLUMNS), summary

    for column in ("symbol", "checkpoint_id", "runtime_scene_fine_label", "runtime_scene_gate_label"):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    summary["scene_dataset_row_count"] = int(len(scoped))
    if scoped.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_COLUMNS), summary

    bridged_rows: list[dict[str, Any]] = []
    disagreement_examples: list[dict[str, Any]] = []
    for row in scoped.to_dict(orient="records"):
        bridge_payload = build_checkpoint_scene_log_only_bridge_v1(
            row,
            active_state_path=active_state_path,
            latest_run_path=latest_run_path,
        )
        bridge_row = dict(bridge_payload.get("row") or {})
        merged = dict(row)
        merged.update(bridge_row)
        bridged_rows.append(merged)

        selected_conf = _to_float(bridge_row.get("scene_candidate_selected_confidence"), 0.0)
        gate_conf = _to_float(bridge_row.get("scene_candidate_gate_confidence"), 0.0)
        if bridge_row.get("scene_candidate_available") and (
            (selected_conf >= 0.70 and not _to_bool(bridge_row.get("scene_candidate_runtime_scene_match"), False))
            or (gate_conf >= 0.70 and not _to_bool(bridge_row.get("scene_candidate_runtime_gate_match"), True))
        ):
            disagreement_examples.append(
                {
                    "symbol": _to_text(row.get("symbol")).upper(),
                    "checkpoint_id": _to_text(row.get("checkpoint_id")),
                    "runtime_scene_fine_label": _to_text(row.get("runtime_scene_fine_label")),
                    "candidate_selected_label": _to_text(bridge_row.get("scene_candidate_selected_label")),
                    "candidate_selected_confidence": selected_conf,
                    "runtime_scene_gate_label": _to_text(row.get("runtime_scene_gate_label"), "none"),
                    "candidate_gate_label": _to_text(bridge_row.get("scene_candidate_gate_label"), "none"),
                    "candidate_gate_confidence": gate_conf,
                    "reason": _to_text(bridge_row.get("scene_candidate_reason")),
                }
            )

    bridged = pd.DataFrame(bridged_rows)
    available_mask = bridged["scene_candidate_available"].apply(_to_bool)
    scene_match_mask = bridged["scene_candidate_runtime_scene_match"].apply(_to_bool)
    gate_match_mask = bridged["scene_candidate_runtime_gate_match"].apply(_to_bool)
    high_conf_scene_mask = bridged["scene_candidate_selected_confidence"].apply(_to_float) >= 0.70
    high_conf_gate_mask = bridged["scene_candidate_gate_confidence"].apply(_to_float) >= 0.70

    selected_counts = (
        bridged.loc[available_mask, "scene_candidate_selected_label"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    gate_counts = (
        bridged.loc[available_mask, "scene_candidate_gate_label"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )
    source_counts = (
        bridged.loc[available_mask, "scene_candidate_selected_source"]
        .fillna("")
        .astype(str)
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .to_dict()
    )

    summary["bridge_available_row_count"] = int(available_mask.sum())
    summary["candidate_selected_label_counts"] = dict(selected_counts)
    summary["candidate_gate_label_counts"] = dict(gate_counts)
    summary["candidate_selected_source_counts"] = dict(source_counts)
    summary["runtime_candidate_scene_match_rate"] = _safe_rate(
        int((available_mask & scene_match_mask).sum()),
        int(available_mask.sum()),
    )
    summary["runtime_candidate_gate_match_rate"] = _safe_rate(
        int((available_mask & gate_match_mask).sum()),
        int(available_mask.sum()),
    )
    summary["high_confidence_scene_disagreement_count"] = int((available_mask & high_conf_scene_mask & ~scene_match_mask).sum())
    summary["high_confidence_gate_disagreement_count"] = int((available_mask & high_conf_gate_mask & ~gate_match_mask).sum())
    disagreement_examples.sort(
        key=lambda row: (
            -max(_to_float(row.get("candidate_selected_confidence"), 0.0), _to_float(row.get("candidate_gate_confidence"), 0.0)),
            str(row.get("symbol", "")),
            str(row.get("checkpoint_id", "")),
        )
    )
    summary["disagreement_examples"] = disagreement_examples[:20]

    symbol_rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = bridged.loc[bridged["symbol"] == symbol].copy()
        if symbol_frame.empty:
            symbol_rows.append(
                {
                    "symbol": symbol,
                    "row_count": 0,
                    "bridge_available_row_count": 0,
                    "candidate_selected_label_counts": "{}",
                    "candidate_gate_label_counts": "{}",
                    "runtime_candidate_scene_match_rate": 0.0,
                    "runtime_candidate_gate_match_rate": 0.0,
                    "high_confidence_scene_disagreement_count": 0,
                    "high_confidence_gate_disagreement_count": 0,
                    "recommended_focus": f"collect_more_{symbol.lower()}_scene_rows",
                }
            )
            continue
        symbol_available = symbol_frame["scene_candidate_available"].apply(_to_bool)
        symbol_scene_match = symbol_frame["scene_candidate_runtime_scene_match"].apply(_to_bool)
        symbol_gate_match = symbol_frame["scene_candidate_runtime_gate_match"].apply(_to_bool)
        symbol_high_conf_scene = symbol_frame["scene_candidate_selected_confidence"].apply(_to_float) >= 0.70
        symbol_high_conf_gate = symbol_frame["scene_candidate_gate_confidence"].apply(_to_float) >= 0.70
        recommended_focus = f"review_{symbol.lower()}_scene_candidate_alignment"
        if int((symbol_available & symbol_high_conf_scene & ~symbol_scene_match).sum()) > 0:
            recommended_focus = f"inspect_{symbol.lower()}_high_conf_scene_disagreement"
        elif int((symbol_available & symbol_high_conf_gate & ~symbol_gate_match).sum()) > 0:
            recommended_focus = f"inspect_{symbol.lower()}_high_conf_gate_disagreement"
        elif int(symbol_available.sum()) <= 0:
            recommended_focus = f"activate_{symbol.lower()}_scene_candidate_log_only"

        symbol_rows.append(
            {
                "symbol": symbol,
                "row_count": int(len(symbol_frame)),
                "bridge_available_row_count": int(symbol_available.sum()),
                "candidate_selected_label_counts": _json_counts(
                    symbol_frame.loc[symbol_available, "scene_candidate_selected_label"]
                    .fillna("")
                    .astype(str)
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .to_dict()
                ),
                "candidate_gate_label_counts": _json_counts(
                    symbol_frame.loc[symbol_available, "scene_candidate_gate_label"]
                    .fillna("")
                    .astype(str)
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .to_dict()
                ),
                "runtime_candidate_scene_match_rate": _safe_rate(
                    int((symbol_available & symbol_scene_match).sum()),
                    int(symbol_available.sum()),
                ),
                "runtime_candidate_gate_match_rate": _safe_rate(
                    int((symbol_available & symbol_gate_match).sum()),
                    int(symbol_available.sum()),
                ),
                "high_confidence_scene_disagreement_count": int((symbol_available & symbol_high_conf_scene & ~symbol_scene_match).sum()),
                "high_confidence_gate_disagreement_count": int((symbol_available & symbol_high_conf_gate & ~symbol_gate_match).sum()),
                "recommended_focus": recommended_focus,
            }
        )

    report_frame = pd.DataFrame(symbol_rows, columns=PATH_CHECKPOINT_SCENE_LOG_ONLY_BRIDGE_REPORT_COLUMNS)
    if summary["bridge_available_row_count"] <= 0:
        summary["recommended_next_action"] = "activate_scene_candidate_log_only_before_sa6"
    elif summary["high_confidence_scene_disagreement_count"] > 0 or summary["high_confidence_gate_disagreement_count"] > 0:
        summary["recommended_next_action"] = "review_high_confidence_scene_candidate_disagreements_before_sa6"
    elif summary["runtime_candidate_scene_match_rate"] < 0.60:
        summary["recommended_next_action"] = "keep_sa5_log_only_and_collect_more_rows"
    else:
        summary["recommended_next_action"] = "proceed_to_sa6_action_bias_review"
    return report_frame, summary
