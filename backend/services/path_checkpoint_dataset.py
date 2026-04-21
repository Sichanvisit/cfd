"""Path-aware checkpoint hindsight dataset and eval helpers for PA5."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_action_resolver import (
    PATH_CHECKPOINT_ACTION_PRECEDENCE,
    _REFRESHABLE_BACKFILL_SOURCES,
    _full_exit_gate_passed,
    build_management_action_candidate_scores,
    build_management_action_rule_features,
    resolve_management_action,
)
from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
    PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER,
    build_default_scene_runtime_payload,
)
from backend.services.path_checkpoint_scene_runtime_bridge import (
    PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    build_default_scene_candidate_runtime_bridge_payload,
)
from backend.services.path_checkpoint_scene_tagger import tag_runtime_scene
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_DATASET_CONTRACT_VERSION = "path_checkpoint_dataset_v3"
PATH_CHECKPOINT_ACTION_EVAL_CONTRACT_VERSION = "checkpoint_action_eval_v1"
PATH_CHECKPOINT_SCENE_EVAL_CONTRACT_VERSION = "checkpoint_scene_eval_v1"
PATH_CHECKPOINT_RUNTIME_PROXY_ACTIONS = (
    "HOLD",
    "PARTIAL_EXIT",
    "PARTIAL_THEN_HOLD",
    "FULL_EXIT",
    "REBUY",
    "WAIT",
)
PATH_CHECKPOINT_DATASET_COLUMNS = [
    "generated_at",
    "source",
    "symbol",
    "surface_name",
    "leg_id",
    "leg_direction",
    "checkpoint_id",
    "checkpoint_type",
    "checkpoint_index_in_leg",
    "position_side",
    "position_size_fraction",
    "avg_entry_price",
    "realized_pnl_state",
    "unrealized_pnl_state",
    "runner_secured",
    "mfe_since_entry",
    "mae_since_entry",
    "current_profit",
    "giveback_from_peak",
    "giveback_ratio",
    "checkpoint_rule_family_hint",
    "exit_stage_family",
    *PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS,
    *PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    "runtime_continuation_odds",
    "runtime_reversal_odds",
    "runtime_hold_quality_score",
    "runtime_partial_exit_ev",
    "runtime_full_exit_risk",
    "runtime_rebuy_readiness",
    "runtime_score_reason",
    "management_action_label",
    "management_action_confidence",
    "management_action_reason",
    "management_action_score_gap",
]
PATH_CHECKPOINT_RESOLVED_COLUMNS = PATH_CHECKPOINT_DATASET_COLUMNS + [
    "management_row_family",
    "runtime_proxy_management_action_label",
    "runtime_proxy_action_confidence",
    "runtime_proxy_action_reason",
    "runtime_proxy_top_score",
    "runtime_proxy_score_gap",
    "runtime_proxy_action_source",
    "hindsight_best_management_action_label",
    "hindsight_label_source",
    "hindsight_label_confidence",
    "hindsight_label_reason",
    "hindsight_resolution_state",
    "hindsight_quality_tier",
    "hindsight_manual_exception_required",
    "hindsight_outcome_family",
    "hindsight_scene_label_source",
    "hindsight_scene_confidence",
    "hindsight_scene_reason",
    "hindsight_scene_resolution_state",
    "runtime_hindsight_match",
    "runtime_hindsight_scene_match",
    "runner_capture_eligible",
    "missed_rebuy_eligible",
    "premature_full_exit_flag",
]
PATH_CHECKPOINT_EVAL_COLUMNS = [
    "symbol",
    "resolved_row_count",
    "position_side_row_count",
    "surface_counts",
    "hindsight_label_counts",
    "quality_tier_counts",
    "runtime_proxy_match_rate",
    "premature_full_exit_rate",
    "runner_capture_rate",
    "missed_rebuy_rate",
    "hold_precision",
    "partial_then_hold_quality",
    "full_exit_precision",
    "recommended_focus",
]
PATH_CHECKPOINT_SCENE_DATASET_COLUMNS = [
    "generated_at",
    "source",
    "symbol",
    "surface_name",
    "leg_id",
    "leg_direction",
    "checkpoint_id",
    "checkpoint_type",
    "checkpoint_index_in_leg",
    "position_side",
    "unrealized_pnl_state",
    "runner_secured",
    "current_profit",
    "mfe_since_entry",
    "mae_since_entry",
    "giveback_ratio",
    "runtime_scene_coarse_family",
    "runtime_scene_fine_label",
    "runtime_scene_gate_label",
    "runtime_scene_modifier_json",
    "runtime_scene_confidence",
    "runtime_scene_confidence_band",
    "runtime_scene_action_bias_strength",
    "runtime_scene_source",
    "runtime_scene_maturity",
    "runtime_scene_transition_from",
    "runtime_scene_transition_bars",
    "runtime_scene_transition_speed",
    "runtime_scene_family_alignment",
    "runtime_scene_gate_block_level",
    *PATH_CHECKPOINT_SCENE_RUNTIME_BRIDGE_KEYS,
    "hindsight_scene_fine_label",
    "hindsight_scene_quality_tier",
    "hindsight_scene_label_source",
    "hindsight_scene_confidence",
    "hindsight_scene_reason",
    "hindsight_scene_resolution_state",
    "runtime_hindsight_scene_match",
    "runtime_proxy_management_action_label",
    "hindsight_best_management_action_label",
]
PATH_CHECKPOINT_SCENE_EVAL_COLUMNS = [
    "symbol",
    "resolved_row_count",
    "runtime_scene_filled_row_count",
    "hindsight_scene_resolved_row_count",
    "runtime_scene_counts",
    "hindsight_scene_counts",
    "gate_label_counts",
    "scene_quality_tier_counts",
    "runtime_hindsight_scene_match_rate",
    "recommended_focus",
]

_REBUY_CHECKPOINT_TYPES = {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}
_RUNNER_LABELS = {"HOLD", "PARTIAL_THEN_HOLD"}
_SCENE_ENTRY_CHECKPOINT_TYPES = {"INITIAL_PUSH", "FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}
_SCENE_LATE_CHECKPOINT_TYPES = {"LATE_TREND_CHECK", "RUNNER_CHECK"}
_OUTCOME_BY_LABEL = {
    "HOLD": "runner_continuation",
    "PARTIAL_EXIT": "partial_lock",
    "PARTIAL_THEN_HOLD": "runner_capture",
    "FULL_EXIT": "thesis_break",
    "REBUY": "reentry_window",
    "WAIT": "neutral_wait",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_dataset_path() -> Path:
    return _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset.csv"


def default_checkpoint_dataset_resolved_path() -> Path:
    return _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"


def default_checkpoint_action_eval_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_action_eval_latest.json"


def default_checkpoint_scene_dataset_path() -> Path:
    return _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_scene_dataset.csv"


def default_checkpoint_scene_eval_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_scene_eval_latest.json"


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


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


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


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _ensure_dataset_frame(checkpoint_rows: pd.DataFrame | None) -> pd.DataFrame:
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_DATASET_COLUMNS)
    for column in PATH_CHECKPOINT_DATASET_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    scene_defaults = build_default_scene_runtime_payload()
    for column in PATH_CHECKPOINT_SCENE_RUNTIME_COLUMNS:
        default = scene_defaults[column]
        series = frame[column]
        if isinstance(default, str):
            frame[column] = series.fillna("").astype(str).replace("", default)
        else:
            frame[column] = series.fillna(default)
    frame = frame.loc[:, PATH_CHECKPOINT_DATASET_COLUMNS]
    frame["generated_at"] = frame["generated_at"].fillna("").astype(str)
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["surface_name"] = frame["surface_name"].fillna("").astype(str)
    frame["checkpoint_type"] = frame["checkpoint_type"].fillna("").astype(str)
    frame["position_side"] = frame["position_side"].fillna("").astype(str).str.upper()
    frame["unrealized_pnl_state"] = frame["unrealized_pnl_state"].fillna("").astype(str).str.upper()
    frame["realized_pnl_state"] = frame["realized_pnl_state"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    return frame.sort_values("__time_sort").drop(columns="__time_sort")


def _resolve_scene_replay_key(row: Mapping[str, Any]) -> str:
    symbol = _to_text(row.get("symbol")).upper()
    trade_link_key = _to_text(row.get("trade_link_key"))
    leg_id = _to_text(row.get("leg_id"))
    if trade_link_key and leg_id:
        return f"{symbol}::trade_leg::{trade_link_key}::{leg_id}"
    if leg_id:
        return f"{symbol}::leg::{leg_id}"
    if trade_link_key:
        return f"{symbol}::trade::{trade_link_key}"
    return symbol


def _hydrate_runtime_scene_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    hydrated_rows: list[dict[str, Any]] = []
    previous_runtime_by_path: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        scene_source = _to_text(row.get("runtime_scene_source"), "schema_only")
        scene_fine = _to_text(row.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
        scene_gate = _to_text(row.get("runtime_scene_gate_label"), "none")
        hydrated = dict(row)
        replay_key = _resolve_scene_replay_key(row)
        previous_runtime = previous_runtime_by_path.get(replay_key, {})
        if scene_source in {"", "schema_only"} or (scene_fine == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and scene_gate == "none"):
            scene_payload = tag_runtime_scene(
                symbol=_to_text(row.get("symbol")).upper(),
                runtime_row=row,
                checkpoint_row=row,
                previous_runtime_row=previous_runtime,
            )
            hydrated.update(dict(scene_payload.get("row") or {}))
        previous_runtime_by_path[replay_key] = {
            "checkpoint_runtime_scene_fine_label": hydrated.get("runtime_scene_fine_label"),
            "checkpoint_runtime_scene_gate_label": hydrated.get("runtime_scene_gate_label"),
            "checkpoint_runtime_scene_transition_bars": hydrated.get("runtime_scene_transition_bars"),
        }
        for bridge_key, bridge_value in build_default_scene_candidate_runtime_bridge_payload().items():
            hydrated.setdefault(bridge_key, bridge_value)
        hydrated_rows.append(hydrated)
    return pd.DataFrame(hydrated_rows, columns=frame.columns)


def derive_runtime_proxy_management_action(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(row)
    resolver_payload = resolve_management_action(checkpoint_ctx=row_map)
    features = build_management_action_rule_features(row_map)
    score_map = {
        str(key): _to_float(value, 0.0)
        for key, value in dict(resolver_payload.get("candidate_scores") or build_management_action_candidate_scores(row_map)).items()
    }
    ordered = sorted(
        ((label, score) for label, score in score_map.items() if label in PATH_CHECKPOINT_RUNTIME_PROXY_ACTIONS),
        key=lambda item: (item[1], -PATH_CHECKPOINT_ACTION_PRECEDENCE.index(item[0]) if item[0] in PATH_CHECKPOINT_ACTION_PRECEDENCE else -999),
        reverse=True,
    )
    top_score = ordered[0][1] if ordered else 0.0
    stored_label = _to_text(row_map.get("management_action_label"))
    stored_confidence = _to_float(row_map.get("management_action_confidence"), 0.0)
    stored_reason = _to_text(row_map.get("management_action_reason"))
    stored_gap = _to_float(row_map.get("management_action_score_gap"), 0.0)
    source = _to_text(row_map.get("source")).lower()
    action_source = "resolver_replay"
    label = _to_text(resolver_payload.get("management_action_label"), "WAIT")
    confidence = _to_float(resolver_payload.get("management_action_confidence"), top_score)
    reason = _to_text(resolver_payload.get("management_action_reason"), f"score_leader::{label.lower()}")
    gap = _to_float(resolver_payload.get("management_action_score_gap"), 0.0)
    if stored_label and source not in _REFRESHABLE_BACKFILL_SOURCES:
        label = stored_label
        confidence = stored_confidence if stored_confidence > 0.0 else confidence
        reason = stored_reason or reason
        gap = stored_gap if stored_gap > 0.0 else gap
        action_source = "stored_pa6_runtime"
    return {
        "management_row_family": _to_text(features.get("row_family"), "unknown"),
        "giveback_from_peak": _to_float(features.get("giveback_from_peak"), 0.0),
        "giveback_ratio": _to_float(features.get("giveback_ratio"), 0.0),
        "runtime_proxy_management_action_label": label,
        "runtime_proxy_action_confidence": _clamp(confidence),
        "runtime_proxy_action_reason": reason,
        "runtime_proxy_top_score": _clamp(top_score),
        "runtime_proxy_score_gap": _clamp(gap),
        "runtime_proxy_action_source": action_source,
        "runtime_proxy_score_map": dict(score_map),
    }


def derive_hindsight_bootstrap_label(row: Mapping[str, Any]) -> dict[str, Any]:
    score_map = build_management_action_candidate_scores(row)
    features = build_management_action_rule_features(row)
    position_side = _to_text(features.get("position_side")).upper()
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    continuation = _to_float(row.get("runtime_continuation_odds"), 0.0)
    reversal = _to_float(row.get("runtime_reversal_odds"), 0.0)
    hold_quality = _to_float(row.get("runtime_hold_quality_score"), 0.0)
    partial_exit = _to_float(row.get("runtime_partial_exit_ev"), 0.0)
    full_exit = _to_float(row.get("runtime_full_exit_risk"), 0.0)
    rebuy = _to_float(row.get("runtime_rebuy_readiness"), 0.0)
    pnl_state = _to_text(features.get("pnl_state")).upper()
    realized_pnl_state = _to_text(features.get("realized_pnl_state")).upper()
    size_fraction = _to_float(row.get("position_size_fraction"), 0.0)
    runner_secured = _to_bool(row.get("runner_secured"), False)
    current_profit = _to_float(features.get("current_profit"), 0.0)
    mfe_since_entry = _to_float(features.get("mfe_since_entry"), 0.0)
    giveback_ratio = _to_float(features.get("giveback_ratio"), 0.0)
    profit_positive = bool(features.get("open_profit") or current_profit > 0.0 or mfe_since_entry > 0.0)
    profit_negative = bool(features.get("open_loss") or current_profit < 0.0)
    part_then_hold_score = _to_float(score_map.get("PARTIAL_THEN_HOLD"), 0.0)
    wait_score = _to_float(score_map.get("WAIT"), 0.0)
    full_exit_allowed, full_exit_reason = _full_exit_gate_passed(
        features,
        full_exit_score=full_exit,
        continuation=continuation,
        reversal=reversal,
        giveback_ratio=giveback_ratio,
    )

    if position_side == "FLAT":
        if checkpoint_type in _REBUY_CHECKPOINT_TYPES and continuation >= 0.62 and rebuy >= 0.58:
            label = "REBUY"
            reason = "bootstrap_reclaim_reentry_window"
            confidence = max(continuation, rebuy)
        else:
            label = "WAIT"
            reason = "bootstrap_flat_checkpoint_wait"
            confidence = max(wait_score, 0.55 if checkpoint_type == "INITIAL_PUSH" else 0.48)
    elif features["active_flat_profit"]:
        if full_exit_allowed:
            label = "FULL_EXIT"
            reason = f"bootstrap_{full_exit_reason}"
            confidence = max(full_exit, reversal * 0.86)
        elif partial_exit >= 0.40 and reversal >= continuation + 0.10 and hold_quality <= 0.34:
            label = "PARTIAL_EXIT"
            reason = "bootstrap_flat_active_risk_trim"
            confidence = max(partial_exit, min(0.9, (reversal - continuation) + 0.44))
        elif hold_quality >= 0.46 and continuation >= reversal + 0.02:
            label = "HOLD"
            reason = "bootstrap_flat_active_hold_bias"
            confidence = max(hold_quality, continuation * 0.84)
        else:
            label = "WAIT"
            reason = "bootstrap_flat_active_wait"
            confidence = max(wait_score, 0.46)
    elif profit_negative and full_exit_allowed:
        label = "FULL_EXIT"
        reason = f"bootstrap_{full_exit_reason}"
        confidence = max(full_exit, reversal * 0.84)
    elif profit_negative and partial_exit >= 0.28 and reversal >= continuation + 0.08:
        label = "PARTIAL_EXIT"
        reason = "bootstrap_open_loss_risk_reduce"
        confidence = max(partial_exit, min(0.84, 0.40 + (reversal - continuation)))
    elif runner_secured and size_fraction <= 0.68 and hold_quality >= 0.46 and continuation >= reversal - 0.02 and giveback_ratio <= 0.22:
        label = "HOLD"
        reason = "bootstrap_runner_secured_hold_continue"
        confidence = max(hold_quality, continuation * 0.88)
    elif (
        runner_secured
        and realized_pnl_state == "LOCKED"
        and hold_quality >= 0.44
        and continuation >= reversal - 0.04
        and giveback_ratio <= 0.16
    ):
        label = "HOLD"
        reason = "bootstrap_runner_locked_hold_continue"
        confidence = max(hold_quality, continuation * 0.87)
    elif (
        profit_positive
        and _to_text(features.get("row_family")).lower() in {"runner_secured_continuation", "profit_hold_bias"}
        and hold_quality >= 0.50
        and continuation >= reversal
        and giveback_ratio <= 0.18
        and part_then_hold_score <= hold_quality + 0.10
    ):
        label = "HOLD"
        reason = "bootstrap_runner_family_hold_continue"
        confidence = max(hold_quality, continuation * 0.86)
    elif profit_positive and part_then_hold_score >= 0.54 and continuation >= reversal - 0.02 and (
        runner_secured or partial_exit >= 0.45 or hold_quality >= 0.42 or giveback_ratio >= 0.18
    ):
        label = "PARTIAL_THEN_HOLD"
        reason = "bootstrap_profit_runner_capture"
        confidence = max(part_then_hold_score, partial_exit, hold_quality, continuation * 0.86)
    elif profit_positive and partial_exit >= 0.48 and (
        partial_exit >= hold_quality + 0.03 or giveback_ratio >= 0.30
    ):
        label = "PARTIAL_EXIT"
        reason = "bootstrap_profit_trim"
        confidence = max(partial_exit, min(0.88, 0.44 + giveback_ratio))
    elif profit_positive and hold_quality >= 0.48 and continuation >= reversal + 0.03:
        label = "HOLD"
        reason = "bootstrap_hold_continuation"
        confidence = max(hold_quality, continuation * 0.84)
    elif checkpoint_type in _REBUY_CHECKPOINT_TYPES and rebuy >= 0.68 and size_fraction < 0.75:
        label = "REBUY"
        reason = "bootstrap_rebuild_reentry"
        confidence = rebuy
    else:
        label = "WAIT"
        reason = "bootstrap_balanced_wait"
        confidence = wait_score

    valid_actions = {"WAIT", "REBUY"} if position_side == "FLAT" else set(PATH_CHECKPOINT_RUNTIME_PROXY_ACTIONS)
    ordered = sorted(
        ((action, score) for action, score in score_map.items() if action in valid_actions),
        key=lambda item: (item[1], -PATH_CHECKPOINT_ACTION_PRECEDENCE.index(item[0]) if item[0] in PATH_CHECKPOINT_ACTION_PRECEDENCE else -999),
        reverse=True,
    )
    top_score = ordered[0][1] if ordered else 0.0
    second_label, second_score = ordered[1] if len(ordered) > 1 else ("", 0.0)
    gap = _clamp(top_score - second_score)
    management_ambiguity = {label, second_label}.issubset({"HOLD", "PARTIAL_EXIT", "PARTIAL_THEN_HOLD"})
    clear_auto_family = bool(
        (label == "FULL_EXIT" and confidence >= 0.66)
        or (label == "FULL_EXIT" and features["open_loss"] and features["protective_source"] and confidence >= 0.56)
        or (label == "PARTIAL_THEN_HOLD" and features["open_profit"] and continuation >= reversal - 0.02 and confidence >= 0.58)
        or (label == "PARTIAL_EXIT" and features["active_flat_profit"] and reversal >= continuation + 0.10 and confidence >= 0.58)
        or (label == "PARTIAL_EXIT" and features["open_loss"] and reversal >= continuation + 0.08 and confidence >= 0.58)
        or (label == "HOLD" and _to_text(features.get("row_family")).lower() in {"runner_secured_continuation", "profit_hold_bias"} and confidence >= 0.58)
    )
    manual_exception_required = bool(
        not clear_auto_family and (gap < 0.08 or confidence < 0.58 or (management_ambiguity and gap < 0.12))
    )
    if manual_exception_required:
        quality_tier = "manual_exception"
    elif confidence >= 0.72 and gap >= 0.10:
        quality_tier = "auto_high"
    else:
        quality_tier = "auto_medium"

    return {
        "hindsight_best_management_action_label": label,
        "hindsight_label_source": "bootstrap_proxy_v1",
        "hindsight_label_confidence": _clamp(confidence),
        "hindsight_label_reason": reason,
        "hindsight_resolution_state": "bootstrap_proxy",
        "hindsight_quality_tier": quality_tier,
        "hindsight_manual_exception_required": manual_exception_required,
        "hindsight_outcome_family": _OUTCOME_BY_LABEL.get(label, "neutral_wait"),
    }


def derive_hindsight_scene_bootstrap(row: Mapping[str, Any]) -> dict[str, Any]:
    row_map = dict(row)
    runtime_scene = _to_text(row_map.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
    gate_label = _to_text(row_map.get("runtime_scene_gate_label"), "none")
    checkpoint_type = _to_text(row_map.get("checkpoint_type")).upper()
    position_side = _to_text(row_map.get("position_side")).upper()
    pnl_state = _to_text(row_map.get("unrealized_pnl_state")).upper()
    action = _to_text(
        row_map.get("hindsight_best_management_action_label")
        or row_map.get("runtime_proxy_management_action_label"),
        "WAIT",
    ).upper()
    continuation = _to_float(row_map.get("runtime_continuation_odds"), 0.0)
    reversal = _to_float(row_map.get("runtime_reversal_odds"), 0.0)
    hold_quality = _to_float(row_map.get("runtime_hold_quality_score"), 0.0)
    partial_exit = _to_float(row_map.get("runtime_partial_exit_ev"), 0.0)
    full_exit = _to_float(row_map.get("runtime_full_exit_risk"), 0.0)
    current_profit = abs(_to_float(row_map.get("current_profit"), 0.0))
    mfe_since_entry = _to_float(row_map.get("mfe_since_entry"), 0.0)
    mae_since_entry = _to_float(row_map.get("mae_since_entry"), 0.0)
    giveback_ratio = _to_float(row_map.get("giveback_ratio"), 0.0)
    runtime_confidence = _to_float(row_map.get("runtime_scene_confidence"), 0.0)
    runtime_band = _to_text(row_map.get("runtime_scene_confidence_band"), "low")
    runtime_maturity = _to_text(row_map.get("runtime_scene_maturity"), "provisional")
    runner_secured = _to_bool(row_map.get("runner_secured"), False)
    reason_blob = " ".join(
        filter(
            None,
            [
                _to_text(row_map.get("runtime_score_reason")).lower(),
                _to_text(row_map.get("hindsight_label_reason")).lower(),
                _to_text(row_map.get("checkpoint_rule_family_hint")).lower(),
                _to_text(row_map.get("exit_stage_family")).lower(),
                _to_text(row_map.get("runtime_scene_modifier_json")).lower(),
            ],
        )
    )
    late_unresolved = runtime_scene == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and checkpoint_type in _SCENE_LATE_CHECKPOINT_TYPES

    label = PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    reason = "scene_bootstrap_unresolved"
    confidence = 0.0
    resolution_state = "diagnostic_only"

    if (
        runtime_scene == "breakout_retest_hold"
        and checkpoint_type in _SCENE_ENTRY_CHECKPOINT_TYPES
        and continuation >= 0.64
        and reversal <= continuation - 0.08
        and action in {"REBUY", "HOLD", "PARTIAL_THEN_HOLD"}
    ):
        label = "breakout_retest_hold"
        reason = "scene_bootstrap_breakout_retest_confirmation"
        confidence = max(runtime_confidence, continuation * 0.88)
    elif (
        runtime_scene == "liquidity_sweep_reclaim"
        and checkpoint_type in _SCENE_ENTRY_CHECKPOINT_TYPES
        and action in {"REBUY", "HOLD", "PARTIAL_THEN_HOLD"}
        and continuation >= 0.66
        and any(token in reason_blob for token in ("sweep", "reclaim", "wrong_side"))
    ):
        label = "liquidity_sweep_reclaim"
        reason = "scene_bootstrap_sweep_reclaim_confirmation"
        confidence = max(runtime_confidence, continuation * 0.86)
    elif (
        runtime_scene == "trend_exhaustion"
        and checkpoint_type in _SCENE_LATE_CHECKPOINT_TYPES
        and action in {"PARTIAL_THEN_HOLD", "PARTIAL_EXIT", "FULL_EXIT"}
        and partial_exit >= 0.56
        and (giveback_ratio >= 0.12 or reversal >= 0.50)
    ):
        label = "trend_exhaustion"
        reason = "scene_bootstrap_late_exhaustion_confirmation"
        confidence = max(runtime_confidence, partial_exit, reversal * 0.82)
    elif (
        late_unresolved
        and action == "PARTIAL_THEN_HOLD"
        and partial_exit >= 0.58
        and continuation >= 0.82
        and reversal <= 0.66
        and giveback_ratio >= 0.18
        and current_profit >= 0.08
        and (runner_secured or pnl_state == "OPEN_PROFIT")
        and any(token in reason_blob for token in ("runner_lock_bias", "continuation_hold_bias"))
    ):
        label = "trend_exhaustion"
        reason = "scene_bootstrap_late_exhaustion_fallback"
        confidence = max(runtime_confidence, min(0.78, partial_exit * 0.92), 0.58)
    elif (
        runtime_scene == "time_decay_risk"
        and checkpoint_type in _SCENE_LATE_CHECKPOINT_TYPES
        and action in {"WAIT", "PARTIAL_EXIT", "FULL_EXIT"}
        and current_profit <= 0.15
        and max(mfe_since_entry, mae_since_entry) <= 0.30
        and hold_quality <= 0.42
    ):
        label = "time_decay_risk"
        reason = "scene_bootstrap_late_time_decay_confirmation"
        confidence = max(runtime_confidence, 0.60)
    elif (
        late_unresolved
        and action in {"WAIT", "PARTIAL_EXIT"}
        and current_profit <= 0.18
        and max(mfe_since_entry, mae_since_entry) <= 0.35
        and hold_quality <= 0.44
        and abs(continuation - reversal) <= 0.18
        and full_exit <= 0.70
        and any(token in reason_blob for token in ("balanced_checkpoint_state", "wait", "timeout", "stalled"))
    ):
        label = "time_decay_risk"
        reason = "scene_bootstrap_late_time_decay_fallback"
        confidence = max(runtime_confidence, 0.58)
    elif gate_label == "low_edge_state" and position_side == "FLAT":
        reason = "scene_bootstrap_gate_only_low_edge"

    if label == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL:
        quality_tier = PATH_CHECKPOINT_SCENE_UNRESOLVED_QUALITY_TIER
    else:
        runtime_match = runtime_scene == label
        if runtime_match and runtime_maturity == "confirmed" and confidence >= 0.72:
            quality_tier = "auto_high"
            resolution_state = "bootstrap_confirmed"
        elif runtime_match and runtime_maturity in {"probable", "confirmed"} and confidence >= 0.58:
            quality_tier = "auto_medium"
            resolution_state = "bootstrap_confirmed"
        else:
            quality_tier = "manual_exception"
            resolution_state = "bootstrap_review"

    return {
        "hindsight_scene_fine_label": label,
        "hindsight_scene_quality_tier": quality_tier,
        "hindsight_scene_label_source": "scene_bootstrap_v1",
        "hindsight_scene_confidence": _clamp(confidence),
        "hindsight_scene_reason": reason,
        "hindsight_scene_resolution_state": resolution_state,
    }


def build_checkpoint_dataset_artifacts(
    checkpoint_rows: pd.DataFrame | None,
    *,
    recent_limit: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frame = _ensure_dataset_frame(checkpoint_rows)
    if recent_limit is not None and recent_limit > 0 and not frame.empty:
        frame = frame.tail(int(recent_limit)).copy()
    frame = _hydrate_runtime_scene_columns(frame)
    base = frame.copy()
    if base.empty:
        summary = {
            "contract_version": PATH_CHECKPOINT_DATASET_CONTRACT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "dataset_row_count": 0,
            "resolved_row_count": 0,
            "manual_exception_count": 0,
            "recommended_next_action": "collect_more_checkpoint_rows_before_pa5",
        }
        return pd.DataFrame(columns=PATH_CHECKPOINT_DATASET_COLUMNS), pd.DataFrame(columns=PATH_CHECKPOINT_RESOLVED_COLUMNS), summary

    resolved_rows: list[dict[str, Any]] = []
    for row in base.to_dict(orient="records"):
        runtime_proxy = derive_runtime_proxy_management_action(row)
        hindsight = derive_hindsight_bootstrap_label(row)
        resolved_row = dict(row)
        resolved_row["management_row_family"] = runtime_proxy["management_row_family"]
        resolved_row["giveback_from_peak"] = runtime_proxy["giveback_from_peak"]
        resolved_row["giveback_ratio"] = runtime_proxy["giveback_ratio"]
        resolved_row.update(
            {
                key: runtime_proxy[key]
                for key in (
                    "runtime_proxy_management_action_label",
                    "runtime_proxy_action_confidence",
                    "runtime_proxy_action_reason",
                    "runtime_proxy_top_score",
                    "runtime_proxy_score_gap",
                )
            }
        )
        resolved_row.update(hindsight)
        resolved_row.update(derive_hindsight_scene_bootstrap(resolved_row))
        resolved_row["runtime_hindsight_match"] = bool(
            _to_text(runtime_proxy.get("runtime_proxy_management_action_label"))
            == _to_text(hindsight.get("hindsight_best_management_action_label"))
        )
        resolved_row["runtime_hindsight_scene_match"] = bool(
            _to_text(row.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            == _to_text(resolved_row.get("hindsight_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            and _to_text(resolved_row.get("hindsight_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
        )
        resolved_row["runner_capture_eligible"] = bool(
            _to_text(hindsight.get("hindsight_best_management_action_label")) in _RUNNER_LABELS and _to_text(row.get("position_side")).upper() != "FLAT"
        )
        resolved_row["missed_rebuy_eligible"] = bool(
            _to_text(hindsight.get("hindsight_best_management_action_label")) == "REBUY"
        )
        resolved_row["premature_full_exit_flag"] = bool(
            _to_text(runtime_proxy.get("runtime_proxy_management_action_label")) == "FULL_EXIT"
            and _to_text(hindsight.get("hindsight_best_management_action_label")) != "FULL_EXIT"
        )
        resolved_rows.append(resolved_row)

    resolved = pd.DataFrame(resolved_rows, columns=PATH_CHECKPOINT_RESOLVED_COLUMNS)
    manual_exception_count = int(resolved["hindsight_manual_exception_required"].apply(_to_bool).sum())
    position_side_row_count = int((resolved["position_side"].fillna("").astype(str).str.upper() != "FLAT").sum())
    non_wait_hindsight_row_count = int(
        (resolved["hindsight_best_management_action_label"].fillna("").astype(str).str.upper() != "WAIT").sum()
    )
    runtime_scene_filled_row_count = int(
        (
            (resolved["runtime_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            | (resolved["runtime_scene_gate_label"].fillna("").astype(str) != "none")
        ).sum()
    )
    hindsight_scene_resolved_row_count = int(
        (resolved["hindsight_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL).sum()
    )
    summary = {
        "contract_version": PATH_CHECKPOINT_DATASET_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "dataset_row_count": int(len(base)),
        "resolved_row_count": int(len(resolved)),
        "manual_exception_count": manual_exception_count,
        "position_side_row_count": position_side_row_count,
        "non_wait_hindsight_row_count": non_wait_hindsight_row_count,
        "runtime_scene_filled_row_count": runtime_scene_filled_row_count,
        "hindsight_scene_resolved_row_count": hindsight_scene_resolved_row_count,
        "hindsight_label_counts": resolved["hindsight_best_management_action_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "quality_tier_counts": resolved["hindsight_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "hindsight_scene_label_counts": resolved["hindsight_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "hindsight_scene_quality_tier_counts": resolved["hindsight_scene_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "recommended_next_action": (
            "collect_more_scene_resolved_rows_before_sa4"
            if hindsight_scene_resolved_row_count < 10
            else (
                "collect_more_live_position_side_checkpoint_rows_before_pa7"
                if position_side_row_count < 4 or non_wait_hindsight_row_count < 2
                else (
                    "proceed_to_pa7_review_queue"
                    if manual_exception_count > 0
                    else "proceed_to_pa8_action_baseline_review"
                )
            )
        ),
    }
    return base, resolved, summary


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def build_checkpoint_action_eval(
    resolved_dataset: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_ACTION_EVAL_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "resolved_row_count": 0,
        "position_side_row_count": 0,
        "manual_exception_count": 0,
        "runtime_proxy_match_rate": 0.0,
        "premature_full_exit_rate": 0.0,
        "runner_capture_rate": 0.0,
        "missed_rebuy_rate": 0.0,
        "hold_precision": 0.0,
        "partial_then_hold_quality": 0.0,
        "full_exit_precision": 0.0,
        "recommended_next_action": "collect_more_checkpoint_dataset_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_EVAL_COLUMNS), summary

    for column in PATH_CHECKPOINT_RESOLVED_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    summary["resolved_row_count"] = int(len(scoped))
    summary["position_side_row_count"] = int((scoped["position_side"].fillna("").astype(str).str.upper() != "FLAT").sum())
    summary["manual_exception_count"] = int(scoped["hindsight_manual_exception_required"].apply(_to_bool).sum())
    summary["runtime_proxy_match_rate"] = _safe_rate(
        int(scoped["runtime_hindsight_match"].apply(_to_bool).sum()),
        int(len(scoped)),
    )

    proxy_full_exit_count = int((scoped["runtime_proxy_management_action_label"] == "FULL_EXIT").sum())
    proxy_hold_count = int((scoped["runtime_proxy_management_action_label"] == "HOLD").sum())
    proxy_part_hold_count = int((scoped["runtime_proxy_management_action_label"] == "PARTIAL_THEN_HOLD").sum())
    hindsight_runner_count = int(scoped["runner_capture_eligible"].apply(_to_bool).sum())
    hindsight_rebuy_count = int(scoped["missed_rebuy_eligible"].apply(_to_bool).sum())
    summary["premature_full_exit_rate"] = _safe_rate(
        int(scoped["premature_full_exit_flag"].apply(_to_bool).sum()),
        proxy_full_exit_count,
    )
    summary["runner_capture_rate"] = _safe_rate(
        int(
            (
                scoped["runner_capture_eligible"].apply(_to_bool)
                & scoped["runtime_proxy_management_action_label"].isin(list(_RUNNER_LABELS))
            ).sum()
        ),
        hindsight_runner_count,
    )
    summary["missed_rebuy_rate"] = _safe_rate(
        int(
            (
                scoped["missed_rebuy_eligible"].apply(_to_bool)
                & (scoped["runtime_proxy_management_action_label"] != "REBUY")
            ).sum()
        ),
        hindsight_rebuy_count,
    )
    summary["hold_precision"] = _safe_rate(
        int(
            (
                (scoped["runtime_proxy_management_action_label"] == "HOLD")
                & (scoped["hindsight_best_management_action_label"] == "HOLD")
            ).sum()
        ),
        proxy_hold_count,
    )
    summary["partial_then_hold_quality"] = _safe_rate(
        int(
            (
                (scoped["runtime_proxy_management_action_label"] == "PARTIAL_THEN_HOLD")
                & (scoped["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD")
            ).sum()
        ),
        proxy_part_hold_count,
    )
    summary["full_exit_precision"] = _safe_rate(
        int(
            (
                (scoped["runtime_proxy_management_action_label"] == "FULL_EXIT")
                & (scoped["hindsight_best_management_action_label"] == "FULL_EXIT")
            ).sum()
        ),
        proxy_full_exit_count,
    )
    summary["hindsight_label_counts"] = scoped["hindsight_best_management_action_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
    summary["quality_tier_counts"] = scoped["hindsight_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy()
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "resolved_row_count": 0,
                    "position_side_row_count": 0,
                    "surface_counts": "{}",
                    "hindsight_label_counts": "{}",
                    "quality_tier_counts": "{}",
                    "runtime_proxy_match_rate": 0.0,
                    "premature_full_exit_rate": 0.0,
                    "runner_capture_rate": 0.0,
                    "missed_rebuy_rate": 0.0,
                    "hold_precision": 0.0,
                    "partial_then_hold_quality": 0.0,
                    "full_exit_precision": 0.0,
                    "recommended_focus": f"collect_more_{symbol.lower()}_checkpoint_labels",
                }
            )
            continue

        symbol_proxy_full_exit = int((symbol_frame["runtime_proxy_management_action_label"] == "FULL_EXIT").sum())
        symbol_proxy_hold = int((symbol_frame["runtime_proxy_management_action_label"] == "HOLD").sum())
        symbol_proxy_part_hold = int((symbol_frame["runtime_proxy_management_action_label"] == "PARTIAL_THEN_HOLD").sum())
        symbol_runner_eligible = int(symbol_frame["runner_capture_eligible"].apply(_to_bool).sum())
        symbol_rebuy_eligible = int(symbol_frame["missed_rebuy_eligible"].apply(_to_bool).sum())
        label_counts = symbol_frame["hindsight_best_management_action_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
        quality_counts = symbol_frame["hindsight_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
        surface_counts = symbol_frame["surface_name"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
        recommended_focus = f"inspect_{symbol.lower()}_checkpoint_label_balance"
        if int(symbol_frame["hindsight_manual_exception_required"].apply(_to_bool).sum()) > 0:
            recommended_focus = f"inspect_{symbol.lower()}_manual_exception_labels"
        elif int((symbol_frame["position_side"].fillna('').astype(str).str.upper() != 'FLAT').sum()) <= 0:
            recommended_focus = f"collect_more_{symbol.lower()}_position_side_labels"

        rows.append(
            {
                "symbol": symbol,
                "resolved_row_count": int(len(symbol_frame)),
                "position_side_row_count": int((symbol_frame["position_side"].fillna("").astype(str).str.upper() != "FLAT").sum()),
                "surface_counts": _json_counts(surface_counts),
                "hindsight_label_counts": _json_counts(label_counts),
                "quality_tier_counts": _json_counts(quality_counts),
                "runtime_proxy_match_rate": _safe_rate(int(symbol_frame["runtime_hindsight_match"].apply(_to_bool).sum()), int(len(symbol_frame))),
                "premature_full_exit_rate": _safe_rate(int(symbol_frame["premature_full_exit_flag"].apply(_to_bool).sum()), symbol_proxy_full_exit),
                "runner_capture_rate": _safe_rate(
                    int((symbol_frame["runner_capture_eligible"].apply(_to_bool) & symbol_frame["runtime_proxy_management_action_label"].isin(list(_RUNNER_LABELS))).sum()),
                    symbol_runner_eligible,
                ),
                "missed_rebuy_rate": _safe_rate(
                    int((symbol_frame["missed_rebuy_eligible"].apply(_to_bool) & (symbol_frame["runtime_proxy_management_action_label"] != "REBUY")).sum()),
                    symbol_rebuy_eligible,
                ),
                "hold_precision": _safe_rate(
                    int(((symbol_frame["runtime_proxy_management_action_label"] == "HOLD") & (symbol_frame["hindsight_best_management_action_label"] == "HOLD")).sum()),
                    symbol_proxy_hold,
                ),
                "partial_then_hold_quality": _safe_rate(
                    int(((symbol_frame["runtime_proxy_management_action_label"] == "PARTIAL_THEN_HOLD") & (symbol_frame["hindsight_best_management_action_label"] == "PARTIAL_THEN_HOLD")).sum()),
                    symbol_proxy_part_hold,
                ),
                "full_exit_precision": _safe_rate(
                    int(((symbol_frame["runtime_proxy_management_action_label"] == "FULL_EXIT") & (symbol_frame["hindsight_best_management_action_label"] == "FULL_EXIT")).sum()),
                    symbol_proxy_full_exit,
                ),
                "recommended_focus": recommended_focus,
            }
        )

    eval_frame = pd.DataFrame(rows, columns=PATH_CHECKPOINT_EVAL_COLUMNS)
    summary["recommended_next_action"] = (
        "collect_more_live_position_side_checkpoint_rows_before_pa7"
        if summary["position_side_row_count"] < 4 or int((scoped["hindsight_best_management_action_label"] != "WAIT").sum()) < 2
        else (
            "proceed_to_pa7_review_queue"
            if summary["manual_exception_count"] > 0
            else "proceed_to_pa8_action_baseline_review"
        )
    )
    return eval_frame, summary


def build_checkpoint_scene_dataset_artifacts(
    resolved_dataset: pd.DataFrame | None,
    *,
    recent_limit: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    if frame.empty:
        summary = {
            "contract_version": PATH_CHECKPOINT_DATASET_CONTRACT_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "scene_dataset_row_count": 0,
            "runtime_scene_filled_row_count": 0,
            "hindsight_scene_resolved_row_count": 0,
            "recommended_next_action": "collect_more_scene_rows_before_sa3",
        }
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_DATASET_COLUMNS), summary

    for column in PATH_CHECKPOINT_RESOLVED_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["generated_at"] = frame["generated_at"].fillna("").astype(str)
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    frame = frame.sort_values("__time_sort").drop(columns="__time_sort")
    if recent_limit is not None and recent_limit > 0 and len(frame) > recent_limit:
        frame = frame.tail(int(recent_limit)).copy()

    scene_dataset = frame.loc[:, PATH_CHECKPOINT_SCENE_DATASET_COLUMNS].copy()
    runtime_scene_filled_row_count = int(
        (
            (scene_dataset["runtime_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            | (scene_dataset["runtime_scene_gate_label"].fillna("").astype(str) != "none")
        ).sum()
    )
    hindsight_scene_resolved_row_count = int(
        (scene_dataset["hindsight_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL).sum()
    )
    summary = {
        "contract_version": PATH_CHECKPOINT_DATASET_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "scene_dataset_row_count": int(len(scene_dataset)),
        "runtime_scene_filled_row_count": runtime_scene_filled_row_count,
        "hindsight_scene_resolved_row_count": hindsight_scene_resolved_row_count,
        "runtime_scene_label_counts": scene_dataset["runtime_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "hindsight_scene_label_counts": scene_dataset["hindsight_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "gate_label_counts": scene_dataset["runtime_scene_gate_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict(),
        "recommended_next_action": (
            "collect_more_scene_resolved_rows_before_sa4"
            if hindsight_scene_resolved_row_count < 10
            else "proceed_to_sa4_scene_candidate_pipeline"
        ),
    }
    return scene_dataset, summary


def build_checkpoint_scene_eval(
    scene_dataset: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = scene_dataset.copy() if scene_dataset is not None and not scene_dataset.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_EVAL_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "resolved_row_count": 0,
        "runtime_scene_filled_row_count": 0,
        "hindsight_scene_resolved_row_count": 0,
        "runtime_hindsight_scene_match_rate": 0.0,
        "recommended_next_action": "collect_more_scene_rows_before_sa4",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_EVAL_COLUMNS), summary

    for column in PATH_CHECKPOINT_SCENE_DATASET_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    runtime_scene_filled_mask = (
        (scoped["runtime_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
        | (scoped["runtime_scene_gate_label"].fillna("").astype(str) != "none")
    )
    hindsight_scene_resolved_mask = (
        scoped["hindsight_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    )
    summary["resolved_row_count"] = int(len(scoped))
    summary["runtime_scene_filled_row_count"] = int(runtime_scene_filled_mask.sum())
    summary["hindsight_scene_resolved_row_count"] = int(hindsight_scene_resolved_mask.sum())
    summary["runtime_hindsight_scene_match_rate"] = _safe_rate(
        int(scoped["runtime_hindsight_scene_match"].apply(_to_bool).sum()),
        int(hindsight_scene_resolved_mask.sum()),
    )
    summary["runtime_scene_counts"] = scoped["runtime_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
    summary["hindsight_scene_counts"] = scoped["hindsight_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
    summary["gate_label_counts"] = scoped["runtime_scene_gate_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
    summary["scene_quality_tier_counts"] = scoped["hindsight_scene_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy()
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "resolved_row_count": 0,
                    "runtime_scene_filled_row_count": 0,
                    "hindsight_scene_resolved_row_count": 0,
                    "runtime_scene_counts": "{}",
                    "hindsight_scene_counts": "{}",
                    "gate_label_counts": "{}",
                    "scene_quality_tier_counts": "{}",
                    "runtime_hindsight_scene_match_rate": 0.0,
                    "recommended_focus": f"collect_more_{symbol.lower()}_scene_rows",
                }
            )
            continue

        symbol_runtime_filled = (
            (symbol_frame["runtime_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            | (symbol_frame["runtime_scene_gate_label"].fillna("").astype(str) != "none")
        )
        symbol_hindsight_resolved = (
            symbol_frame["hindsight_scene_fine_label"].fillna("").astype(str) != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
        )
        recommended_focus = f"inspect_{symbol.lower()}_scene_distribution"
        if int(symbol_hindsight_resolved.sum()) <= 0:
            recommended_focus = f"collect_more_{symbol.lower()}_scene_resolutions"
        elif int((symbol_frame["hindsight_scene_quality_tier"] == "manual_exception").sum()) > 0:
            recommended_focus = f"inspect_{symbol.lower()}_scene_manual_exceptions"

        rows.append(
            {
                "symbol": symbol,
                "resolved_row_count": int(len(symbol_frame)),
                "runtime_scene_filled_row_count": int(symbol_runtime_filled.sum()),
                "hindsight_scene_resolved_row_count": int(symbol_hindsight_resolved.sum()),
                "runtime_scene_counts": _json_counts(
                    symbol_frame["runtime_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
                ),
                "hindsight_scene_counts": _json_counts(
                    symbol_frame["hindsight_scene_fine_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
                ),
                "gate_label_counts": _json_counts(
                    symbol_frame["runtime_scene_gate_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
                ),
                "scene_quality_tier_counts": _json_counts(
                    symbol_frame["hindsight_scene_quality_tier"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
                ),
                "runtime_hindsight_scene_match_rate": _safe_rate(
                    int(symbol_frame["runtime_hindsight_scene_match"].apply(_to_bool).sum()),
                    int(symbol_hindsight_resolved.sum()),
                ),
                "recommended_focus": recommended_focus,
            }
        )

    eval_frame = pd.DataFrame(rows, columns=PATH_CHECKPOINT_SCENE_EVAL_COLUMNS)
    summary["recommended_next_action"] = (
        "collect_more_scene_resolved_rows_before_sa4"
        if summary["hindsight_scene_resolved_row_count"] < 10
        else "proceed_to_sa4_scene_candidate_pipeline"
    )
    return eval_frame, summary
