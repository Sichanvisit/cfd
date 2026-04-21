"""Path-aware checkpoint best action resolver for PA6."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_ACTION_RESOLVER_CONTRACT_VERSION = "path_checkpoint_action_resolver_v1"
PATH_CHECKPOINT_MANAGEMENT_ACTION_SNAPSHOT_CONTRACT_VERSION = "checkpoint_management_action_snapshot_v1"
PATH_CHECKPOINT_ACTION_PRECEDENCE = (
    "FULL_EXIT",
    "PARTIAL_THEN_HOLD",
    "PARTIAL_EXIT",
    "HOLD",
    "REBUY",
    "WAIT",
)
PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS = (
    "management_action_label",
    "management_action_confidence",
    "management_action_reason",
    "management_action_score_gap",
)
PATH_CHECKPOINT_MANAGEMENT_ACTION_PREFIXED_KEYS = {
    "management_action_label": "checkpoint_management_action_label",
    "management_action_confidence": "checkpoint_management_action_confidence",
    "management_action_reason": "checkpoint_management_action_reason",
    "management_action_score_gap": "checkpoint_management_action_score_gap",
}
PATH_CHECKPOINT_MANAGEMENT_ACTION_SNAPSHOT_COLUMNS = [
    "symbol",
    "recent_row_count",
    "resolved_row_count",
    "management_action_counts",
    "avg_management_action_confidence",
    "latest_checkpoint_id",
    "latest_surface_name",
    "latest_time",
    "recommended_focus",
]

_REBUY_CHECKPOINT_TYPES = {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}
_ALL_ACTIONS = ("HOLD", "PARTIAL_EXIT", "PARTIAL_THEN_HOLD", "FULL_EXIT", "REBUY", "WAIT")
_CONTINUATION_CHECKPOINT_TYPES = {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK", "LATE_TREND_CHECK", "RUNNER_CHECK"}
_ACTION_PRECEDENCE_RANK = {label: index for index, label in enumerate(PATH_CHECKPOINT_ACTION_PRECEDENCE)}
_REFRESHABLE_BACKFILL_SOURCES = {"open_trade_backfill", "closed_trade_hold_backfill", "closed_trade_runner_backfill"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_management_action_snapshot_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_management_action_snapshot_latest.json"


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


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def build_management_action_rule_features(checkpoint_ctx: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(checkpoint_ctx or {})
    position_side = _to_text(row.get("position_side")).upper()
    pnl_state = _to_text(row.get("unrealized_pnl_state")).upper()
    realized_pnl_state = _to_text(row.get("realized_pnl_state")).upper()
    current_profit = _to_float(row.get("current_profit"), 0.0)
    mfe_since_entry = _to_float(row.get("mfe_since_entry"), 0.0)
    mae_since_entry = _to_float(row.get("mae_since_entry"), 0.0)
    source = _to_text(row.get("source")).lower()
    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    explicit_stage_family = _to_text(row.get("exit_stage_family")).lower()
    explicit_rule_family = _to_text(row.get("checkpoint_rule_family_hint")).lower()
    active_position = position_side != "FLAT"
    active_flat_profit = bool(active_position and pnl_state == "FLAT")
    open_profit = bool(active_position and pnl_state == "OPEN_PROFIT")
    open_loss = bool(active_position and pnl_state == "OPEN_LOSS")
    giveback_from_peak = _to_float(row.get("giveback_from_peak"), max(0.0, mfe_since_entry - max(current_profit, 0.0)))
    giveback_ratio = _to_float(row.get("giveback_ratio"), 0.0)
    if giveback_ratio <= 0.0 and mfe_since_entry > 0.0:
        giveback_ratio = round(giveback_from_peak / mfe_since_entry, 6)
    protective_source = bool(
        explicit_stage_family == "protective"
        or explicit_rule_family == "open_loss_protective"
        or explicit_rule_family == "protective_exit_bias"
        or explicit_rule_family == "full_exit_candidate"
        or explicit_stage_family == "managed_exit"
        or source.startswith("exit_manage_protective")
        or source.startswith("exit_manage_recovery")
        or source.startswith("exit_manage_managed_exit")
    )
    runner_source = bool(explicit_stage_family == "runner" or "runner" in source or explicit_rule_family == "runner_secured_continuation")
    hold_source = bool(explicit_stage_family == "hold" or source.startswith("exit_manage_hold"))
    if explicit_rule_family:
        row_family = explicit_rule_family
    elif position_side == "FLAT":
        row_family = "flat_checkpoint"
    elif active_flat_profit:
        row_family = "active_flat_profit"
    elif open_profit:
        row_family = "active_open_profit"
    elif open_loss:
        row_family = "active_open_loss"
    else:
        row_family = "active_mixed"
    return {
        "row_family": row_family,
        "exit_stage_family": explicit_stage_family,
        "position_side": position_side,
        "pnl_state": pnl_state,
        "realized_pnl_state": realized_pnl_state,
        "current_profit": current_profit,
        "mfe_since_entry": mfe_since_entry,
        "mae_since_entry": mae_since_entry,
        "source": source,
        "checkpoint_type": checkpoint_type,
        "active_position": active_position,
        "active_flat_profit": active_flat_profit,
        "open_profit": open_profit,
        "open_loss": open_loss,
        "giveback_from_peak": round(giveback_from_peak, 6),
        "giveback_ratio": round(giveback_ratio, 6),
        "protective_source": protective_source,
        "runner_source": runner_source,
        "hold_source": hold_source,
    }


def _ordered_action_scores(score_map: Mapping[str, Any], valid_actions: set[str]) -> list[tuple[str, float]]:
    return sorted(
        ((label, _to_float(score_map.get(label), 0.0)) for label in _ALL_ACTIONS if label in valid_actions),
        key=lambda item: (item[1], -_ACTION_PRECEDENCE_RANK.get(item[0], 999)),
        reverse=True,
    )


def _full_exit_gate_passed(
    features: Mapping[str, Any],
    *,
    full_exit_score: float,
    continuation: float,
    reversal: float,
    giveback_ratio: float,
) -> tuple[bool, str]:
    open_loss = _to_bool(features.get("open_loss"), False)
    protective_source = _to_bool(features.get("protective_source"), False)
    active_flat_profit = _to_bool(features.get("active_flat_profit"), False)
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    if open_loss and protective_source and full_exit_score >= 0.54 and reversal >= continuation + 0.06 and giveback_ratio >= 0.35:
        return True, "open_loss_protective_exit"
    if open_loss and full_exit_score >= 0.82 and reversal >= continuation + 0.20 and checkpoint_type in {"LATE_TREND_CHECK", "RUNNER_CHECK", "FIRST_PULLBACK_CHECK"}:
        return True, "open_loss_extreme_pressure_exit"
    if open_loss and full_exit_score >= 0.70 and reversal >= continuation + 0.12 and giveback_ratio >= 0.45:
        return True, "open_loss_thesis_break"
    if active_flat_profit and full_exit_score >= 0.76 and reversal >= continuation + 0.12 and protective_source:
        return True, "flat_active_thesis_break"
    return False, ""


def build_management_action_candidate_scores(checkpoint_ctx: Mapping[str, Any] | None) -> dict[str, float]:
    row = dict(checkpoint_ctx or {})
    continuation = _to_float(row.get("runtime_continuation_odds"), 0.0)
    reversal = _to_float(row.get("runtime_reversal_odds"), 0.0)
    hold_quality = _to_float(row.get("runtime_hold_quality_score"), 0.0)
    partial_exit = _to_float(row.get("runtime_partial_exit_ev"), 0.0)
    full_exit = _to_float(row.get("runtime_full_exit_risk"), 0.0)
    rebuy = _to_float(row.get("runtime_rebuy_readiness"), 0.0)
    position_side = _to_text(row.get("position_side")).upper()
    size_fraction = _to_float(row.get("position_size_fraction"), 0.0)
    checkpoint_type = _to_text(row.get("checkpoint_type")).upper()
    runner_secured = _to_bool(row.get("runner_secured"), False)
    pnl_state = _to_text(row.get("unrealized_pnl_state")).upper()
    realized_pnl_state = _to_text(row.get("realized_pnl_state")).upper()
    features = build_management_action_rule_features(row)
    giveback_ratio = _to_float(features.get("giveback_ratio"), 0.0)
    top_signal = max(continuation, reversal, hold_quality, partial_exit, full_exit, rebuy, 0.0)

    partial_then_hold = _clamp(
        partial_exit * 0.58
        + hold_quality * 0.42
        + (0.12 if runner_secured else 0.0)
        + (0.08 if pnl_state == "OPEN_PROFIT" else 0.0)
        - (0.12 if position_side == "FLAT" else 0.0)
    )
    wait_score = _clamp(
        0.16
        + (0.16 if position_side == "FLAT" else 0.04)
        + max(0.0, 0.14 - abs(continuation - reversal)) * 1.6
        + (0.12 if top_signal < 0.58 else 0.0)
        + (0.10 if checkpoint_type == "INITIAL_PUSH" and position_side == "FLAT" else 0.0)
    )

    if checkpoint_type not in _REBUY_CHECKPOINT_TYPES:
        rebuy = _clamp(rebuy * 0.55)
    if position_side == "FLAT":
        hold_quality = _clamp(hold_quality * 0.20)
        partial_exit = _clamp(partial_exit * 0.10)
        partial_then_hold = _clamp(partial_then_hold * 0.10)
        full_exit = _clamp(full_exit * 0.12)
    elif size_fraction >= 0.95:
        rebuy = _clamp(rebuy * 0.55)

    if features["runner_source"] and features["open_profit"]:
        partial_then_hold = _clamp(partial_then_hold + (0.02 if runner_secured else 0.05))
    if runner_secured and features["open_profit"] and size_fraction <= 0.68 and giveback_ratio <= 0.22:
        hold_quality = _clamp(hold_quality + 0.08)
        partial_then_hold = _clamp(max(0.0, partial_then_hold - 0.06))
        wait_score = _clamp(max(0.0, wait_score - 0.05))
    if runner_secured and realized_pnl_state == "LOCKED" and features["open_profit"] and giveback_ratio <= 0.16:
        hold_quality = _clamp(hold_quality + 0.09)
        partial_then_hold = _clamp(max(0.0, partial_then_hold - 0.08))
        wait_score = _clamp(max(0.0, wait_score - 0.06))
    if features["row_family"] in {"runner_secured_continuation", "profit_hold_bias"} and features["open_profit"]:
        hold_quality = _clamp(hold_quality + 0.05)
        wait_score = _clamp(max(0.0, wait_score - 0.04))
    if features["protective_source"]:
        full_exit = _clamp(full_exit + 0.06)
        wait_score = _clamp(wait_score - 0.03)
    if features["open_profit"] and giveback_ratio >= 0.28:
        partial_exit = _clamp(partial_exit + min(0.12, giveback_ratio * 0.12))
    if features["active_flat_profit"]:
        wait_score = _clamp(max(0.0, wait_score - 0.08))
        if reversal >= continuation + 0.10:
            partial_exit = _clamp(partial_exit + 0.06)
        if reversal >= continuation + 0.16 and features["protective_source"]:
            full_exit = _clamp(full_exit + 0.08)
        if continuation >= reversal and checkpoint_type in _CONTINUATION_CHECKPOINT_TYPES:
            hold_quality = _clamp(hold_quality + 0.05)

    return {
        "HOLD": _clamp(hold_quality),
        "PARTIAL_EXIT": _clamp(partial_exit),
        "PARTIAL_THEN_HOLD": _clamp(partial_then_hold),
        "FULL_EXIT": _clamp(full_exit),
        "REBUY": _clamp(rebuy),
        "WAIT": _clamp(wait_score),
    }


def resolve_management_action(
    scores: Mapping[str, Any] | None = None,
    checkpoint_ctx: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = dict(checkpoint_ctx or {})
    score_map = (
        {str(k): _to_float(v, 0.0) for k, v in dict(scores or {}).items() if str(k) in _ALL_ACTIONS}
        if scores
        else build_management_action_candidate_scores(ctx)
    )
    features = build_management_action_rule_features(ctx)
    position_side = _to_text(features.get("position_side")).upper()
    checkpoint_type = _to_text(features.get("checkpoint_type")).upper()
    surface_name = _to_text(ctx.get("surface_name")).lower()
    continuation = _to_float(ctx.get("runtime_continuation_odds"), 0.0)
    reversal = _to_float(ctx.get("runtime_reversal_odds"), 0.0)
    pnl_state = _to_text(features.get("pnl_state")).upper()
    realized_pnl_state = _to_text(features.get("realized_pnl_state")).upper()
    source = _to_text(features.get("source")).lower()
    size_fraction = _to_float(ctx.get("position_size_fraction"), 0.0)
    runner_secured = _to_bool(ctx.get("runner_secured"), False)
    hold_score = _to_float(score_map.get("HOLD"), 0.0)
    partial_score = _to_float(score_map.get("PARTIAL_EXIT"), 0.0)
    partial_then_hold_score = _to_float(score_map.get("PARTIAL_THEN_HOLD"), 0.0)
    full_exit_score = _to_float(score_map.get("FULL_EXIT"), 0.0)
    rebuy_score = _to_float(score_map.get("REBUY"), 0.0)
    wait_score = _to_float(score_map.get("WAIT"), 0.0)
    giveback_ratio = _to_float(features.get("giveback_ratio"), 0.0)
    raw_hold_quality = _to_float(ctx.get("runtime_hold_quality_score"), hold_score)
    raw_partial_exit_ev = _to_float(ctx.get("runtime_partial_exit_ev"), partial_score)

    valid_actions = {"WAIT", "REBUY"} if position_side == "FLAT" else set(_ALL_ACTIONS)
    ordered = _ordered_action_scores(score_map, valid_actions)
    top_label, top_score = ordered[0] if ordered else ("WAIT", 0.0)
    second_label, second_score = ordered[1] if len(ordered) > 1 else ("", 0.0)
    gap = _clamp(top_score - second_score)
    full_exit_allowed, full_exit_reason = _full_exit_gate_passed(
        features,
        full_exit_score=full_exit_score,
        continuation=continuation,
        reversal=reversal,
        giveback_ratio=giveback_ratio,
    )

    if position_side == "FLAT":
        if checkpoint_type in _REBUY_CHECKPOINT_TYPES and rebuy_score >= 0.62 and continuation >= reversal:
            label = "REBUY"
            reason = "flat_reclaim_reentry_ready"
            confidence = max(rebuy_score, top_score)
        else:
            label = "WAIT"
            reason = "flat_checkpoint_wait"
            confidence = max(wait_score, top_score)
    else:
        if features["active_flat_profit"]:
            if full_exit_allowed:
                label = "FULL_EXIT"
                reason = full_exit_reason
                confidence = max(full_exit_score, reversal * 0.88)
            elif partial_score >= 0.40 and reversal >= continuation + 0.10 and hold_score <= 0.34:
                label = "PARTIAL_EXIT"
                reason = "flat_active_risk_trim"
                confidence = max(partial_score, min(0.92, (reversal - continuation) + 0.44))
            elif (
                source == "open_trade_backfill"
                and checkpoint_type == "RUNNER_CHECK"
                and features["row_family"] == "active_position"
                and not runner_secured
                and abs(_to_float(features.get("current_profit"), 0.0)) <= 0.01
                and continuation >= reversal + 0.12
                and hold_score >= 0.40
                and hold_score <= 0.50
                and partial_score <= 0.35
                and full_exit_score <= 0.28
                and gap <= 0.13
            ):
                label = "WAIT"
                reason = "backfill_flat_active_wait_retest"
                confidence = max(wait_score, min(0.62, hold_score + 0.04))
            elif (
                source in {"open_trade_backfill", "exit_manage_hold"}
                and surface_name == "continuation_hold_surface"
                and checkpoint_type in {"LATE_TREND_CHECK", "RUNNER_CHECK"}
                and features["row_family"] in {"active_position", "wait_bias"}
                and not runner_secured
                and abs(_to_float(features.get("current_profit"), 0.0)) <= 0.01
                and giveback_ratio <= 0.05
                and 0.39 <= hold_score <= 0.50
                and partial_score <= 0.36
                and full_exit_score <= 0.24
            ):
                label = "WAIT"
                reason = "flat_late_wait_bias_wait_retest"
                confidence = max(wait_score, min(0.64, hold_score + 0.03))
            elif (
                source in {"open_trade_backfill", "exit_manage_hold"}
                and surface_name == "continuation_hold_surface"
                and checkpoint_type == "RUNNER_CHECK"
                and features["row_family"] in {"active_position", "wait_bias"}
                and not runner_secured
                and abs(_to_float(features.get("current_profit"), 0.0)) <= 0.01
                and giveback_ratio <= 0.05
                and hold_score <= 0.22
                and partial_score <= 0.40
                and 0.40 <= full_exit_score <= 0.60
                and reversal >= continuation + 0.30
                and gap <= 0.20
            ):
                label = "WAIT"
                reason = "flat_backfill_wait_bias_wait_retest"
                confidence = max(wait_score, min(0.58, partial_score + 0.02))
            elif (
                source == "exit_manage_hold"
                and surface_name in {"follow_through_surface", "continuation_hold_surface"}
                and checkpoint_type in {"FIRST_PULLBACK_CHECK", "RUNNER_CHECK"}
                and features["row_family"] == "active_flat_profit"
                and not runner_secured
                and abs(_to_float(features.get("current_profit"), 0.0)) <= 0.01
                and giveback_ratio >= 0.98
                and 0.49 <= hold_score <= 0.51
                and partial_score >= 0.44
                and full_exit_score <= 0.30
                and continuation >= reversal + 0.18
                and gap <= 0.07
            ):
                label = "WAIT"
                reason = "flat_active_micro_wait_boundary"
                confidence = max(wait_score, min(0.62, hold_score + 0.01))
            elif hold_score >= 0.44 and continuation >= reversal - 0.02 and checkpoint_type in _CONTINUATION_CHECKPOINT_TYPES:
                label = "HOLD"
                reason = "flat_active_hold_retest"
                confidence = max(hold_score, continuation * 0.86)
            elif abs(continuation - reversal) <= 0.10 and partial_score < 0.46:
                label = "WAIT"
                reason = "flat_active_balanced_wait"
                confidence = max(wait_score, 0.46)
            elif wait_score >= 0.46:
                label = "WAIT"
                reason = "flat_active_balanced_wait"
                confidence = wait_score
            else:
                label = top_label
                confidence = top_score
                reason = f"score_leader::{_to_text(label).lower()}"
        elif (
            _to_text(ctx.get("symbol")).upper() == "XAUUSD"
            and source in {"open_trade_backfill", "closed_trade_hold_backfill"}
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "RUNNER_CHECK"
            and features["row_family"] == "runner_secured_continuation"
            and runner_secured
            and realized_pnl_state == "LOCKED"
            and features["open_loss"]
            and giveback_ratio <= 0.35
            and continuation >= reversal + 0.02
            and 0.35 <= hold_score <= 0.39
            and 0.39 <= partial_score <= 0.44
            and full_exit_score <= 0.57
        ):
            label = "WAIT"
            reason = "xau_backfill_runner_wait_boundary_retest"
            confidence = max(wait_score, min(0.60, partial_score + 0.02))
        elif (
            _to_text(ctx.get("symbol")).upper() == "BTCUSD"
            and source == "closed_trade_hold_backfill"
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "RUNNER_CHECK"
            and features["row_family"] == "runner_secured_continuation"
            and runner_secured
            and realized_pnl_state == "LOCKED"
            and features["open_loss"]
            and -1.05 <= _to_float(features.get("current_profit"), 0.0) < 0.0
            and continuation >= 0.706
            and 0.32 <= hold_score <= 0.37
            and 0.44 <= partial_score <= 0.46
            and 0.44 <= full_exit_score <= 0.565
        ):
            label = "WAIT"
            reason = "btc_backfill_runner_wait_boundary_retest"
            confidence = max(wait_score, min(0.62, hold_score + 0.05))
        elif (
            _to_text(ctx.get("symbol")).upper() == "NAS100"
            and source == "closed_trade_hold_backfill"
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "LATE_TREND_CHECK"
            and features["row_family"] == "runner_secured_continuation"
            and runner_secured
            and realized_pnl_state == "LOCKED"
            and features["open_loss"]
            and giveback_ratio <= 0.03
            and continuation >= reversal
            and 0.33 <= hold_score <= 0.37
            and 0.37 <= partial_score <= 0.42
            and 0.48 <= full_exit_score <= 0.56
        ):
            label = "WAIT"
            reason = "nas_backfill_late_runner_wait_boundary_retest"
            confidence = max(wait_score, min(0.62, hold_score + 0.05))
        elif (
            source == "exit_manage_hold"
            and surface_name in {"follow_through_surface", "protective_exit_surface"}
            and checkpoint_type in {"FIRST_PULLBACK_CHECK", "LATE_TREND_CHECK"}
            and features["row_family"] == "open_loss_protective"
            and _to_float(features.get("current_profit"), 0.0) < 0.0
            and abs(_to_float(features.get("current_profit"), 0.0)) <= 0.35
            and giveback_ratio >= 0.98
            and 0.26 <= hold_score <= 0.34
            and 0.31 <= partial_score <= 0.35
            and 0.50 <= full_exit_score <= 0.73
        ):
            label = "WAIT"
            reason = "protective_micro_open_loss_wait_retest"
            confidence = max(wait_score, min(0.60, partial_score + 0.02))
        elif (
            source in _REFRESHABLE_BACKFILL_SOURCES
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "RUNNER_CHECK"
            and features["row_family"] == "open_loss_protective"
            and _to_float(features.get("current_profit"), 0.0) < 0.0
            and giveback_ratio >= 0.95
            and hold_score >= 0.30
            and partial_score >= 0.44
            and 0.54 <= full_exit_score <= 0.57
            and abs(continuation - reversal) <= 0.08
            and gap <= 0.125
        ):
            label = "WAIT"
            reason = "backfill_open_loss_protective_wait_retest"
            confidence = max(wait_score, min(0.60, partial_score + 0.02))
        elif full_exit_allowed:
            label = "FULL_EXIT"
            reason = full_exit_reason
            confidence = max(full_exit_score, reversal * 0.84)
        elif (
            source in _REFRESHABLE_BACKFILL_SOURCES
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "RUNNER_CHECK"
            and features["row_family"] == "open_loss_protective"
            and _to_float(features.get("current_profit"), 0.0) < 0.0
            and giveback_ratio >= 0.95
            and hold_score >= 0.30
            and partial_score >= 0.42
            and full_exit_score <= 0.57
            and abs(continuation - reversal) <= 0.08
            and gap <= 0.13
        ):
            label = "WAIT"
            reason = "backfill_open_loss_protective_wait_retest"
            confidence = max(wait_score, min(0.60, partial_score + 0.02))
        elif features["open_loss"] and partial_score >= 0.28 and reversal >= continuation + 0.08 and not full_exit_allowed:
            label = "PARTIAL_EXIT"
            reason = "open_loss_risk_reduce"
            confidence = max(partial_score, min(0.86, 0.40 + (reversal - continuation)))
        elif (
            source == "exit_manage_hold"
            and surface_name == "follow_through_surface"
            and checkpoint_type == "INITIAL_PUSH"
            and features["row_family"] == "active_open_loss"
            and _to_float(features.get("current_profit"), 0.0) < 0.0
            and giveback_ratio >= 0.98
            and continuation >= reversal + 0.30
            and 0.44 <= hold_score <= 0.47
            and partial_score <= 0.34
            and full_exit_score <= 0.42
            and gap <= 0.12
        ):
            label = "WAIT"
            reason = "initial_push_active_open_loss_wait_boundary_retest"
            confidence = max(wait_score, min(0.64, hold_score + 0.02))
        elif (
            source == "open_trade_backfill"
            and surface_name == "continuation_hold_surface"
            and checkpoint_type == "RECLAIM_CHECK"
            and features["row_family"] == "active_open_loss"
            and _to_float(features.get("current_profit"), 0.0) < 0.0
            and continuation >= reversal + 0.20
            and giveback_ratio >= 0.85
            and hold_score >= 0.52
            and partial_score <= 0.36
            and full_exit_score <= 0.40
        ):
            label = "WAIT"
            reason = "backfill_reclaim_open_loss_wait_retest"
            confidence = max(wait_score, min(0.66, hold_score + 0.03))
        elif (
            runner_secured
            and size_fraction <= 0.68
            and raw_partial_exit_ev >= 0.68
            and partial_then_hold_score >= hold_score + 0.08
            and continuation >= reversal - 0.02
            and giveback_ratio <= 0.22
        ):
            label = "PARTIAL_THEN_HOLD"
            reason = "runner_lock_then_hold"
            confidence = max(partial_then_hold_score, partial_score, hold_score, continuation * 0.85)
        elif runner_secured and size_fraction <= 0.68 and hold_score >= 0.46 and continuation >= reversal - 0.02 and giveback_ratio <= 0.22:
            label = "HOLD"
            reason = "runner_secured_hold_continue"
            confidence = max(hold_score, continuation * 0.88)
        elif (
            runner_secured
            and realized_pnl_state == "LOCKED"
            and hold_score >= 0.44
            and continuation >= reversal - 0.04
            and giveback_ratio <= 0.16
        ):
            label = "HOLD"
            reason = "runner_locked_hold_continue"
            confidence = max(hold_score, continuation * 0.87)
        elif (
            features["row_family"] in {"runner_secured_continuation", "profit_hold_bias"}
            and pnl_state == "OPEN_PROFIT"
            and hold_score >= 0.50
            and continuation >= reversal
            and giveback_ratio <= 0.18
            and partial_then_hold_score <= hold_score + 0.10
        ):
            label = "HOLD"
            reason = "runner_family_hold_bias"
            confidence = max(hold_score, continuation * 0.86)
        elif (
            features["row_family"] == "runner_secured_continuation"
            and pnl_state == "OPEN_PROFIT"
            and raw_partial_exit_ev >= 0.52
            and raw_hold_quality <= 0.40
            and reversal >= continuation + 0.04
            and partial_then_hold_score <= partial_score + 0.10
        ):
            label = "PARTIAL_EXIT"
            reason = "runner_secured_early_trim_bias"
            confidence = max(partial_score, min(0.86, 0.42 + (reversal - continuation)))
        elif (
            features["row_family"] == "profit_hold_bias"
            and surface_name == "follow_through_surface"
            and checkpoint_type == "FIRST_PULLBACK_CHECK"
            and pnl_state == "OPEN_PROFIT"
            and _to_float(features.get("current_profit"), 0.0) <= 0.05
            and giveback_ratio <= 0.05
            and partial_score >= 0.49
            and hold_score <= 0.42
            and partial_then_hold_score <= partial_score + 0.03
        ):
            label = "PARTIAL_EXIT"
            reason = "profit_hold_micro_trim_bias"
            confidence = max(partial_score, min(0.80, partial_score + 0.03))
        elif partial_then_hold_score >= 0.56 and (runner_secured or pnl_state == "OPEN_PROFIT") and continuation >= reversal - 0.02 and (
            runner_secured or partial_score >= 0.45 or hold_score >= 0.42 or giveback_ratio >= 0.18
        ):
            label = "PARTIAL_THEN_HOLD"
            reason = "runner_lock_then_hold"
            confidence = max(partial_then_hold_score, partial_score, hold_score, continuation * 0.85)
        elif partial_score >= 0.58 and pnl_state == "OPEN_PROFIT" and giveback_ratio >= 0.30 and continuation >= reversal - 0.02:
            label = "PARTIAL_EXIT"
            reason = "profit_giveback_trim"
            confidence = max(partial_score, min(0.88, 0.46 + giveback_ratio))
        elif partial_score >= 0.60 and reversal >= continuation + 0.08:
            label = "PARTIAL_EXIT"
            reason = "partial_lock_preferred"
            confidence = partial_score
        elif hold_score >= 0.60 and continuation >= reversal - 0.02:
            label = "HOLD"
            reason = "continuation_hold_preferred"
            confidence = hold_score
        elif checkpoint_type in _REBUY_CHECKPOINT_TYPES and rebuy_score >= 0.66 and size_fraction < 0.80:
            label = "REBUY"
            reason = "same_leg_rebuild_ready"
            confidence = rebuy_score
        elif wait_score >= 0.56 and top_score < 0.60:
            label = "WAIT"
            reason = "balanced_management_wait"
            confidence = wait_score
        else:
            if top_label == "FULL_EXIT" and not full_exit_allowed:
                if (
                    surface_name == "protective_exit_surface"
                    and features["row_family"] in {"active_open_loss", "open_loss_protective"}
                    and checkpoint_type == "RECLAIM_CHECK"
                    and _to_float(features.get("current_profit"), 0.0) < 0.0
                    and continuation >= reversal + 0.08
                    and hold_score >= max(partial_score - 0.02, 0.33)
                ):
                    label = "WAIT"
                    reason = "protective_reclaim_open_loss_wait_retest"
                    confidence = max(wait_score, min(0.72, hold_score + 0.06))
                elif (
                    surface_name == "protective_exit_surface"
                    and features["row_family"] in {"active_open_loss", "open_loss_protective"}
                    and checkpoint_type == "LATE_TREND_CHECK"
                    and _to_float(features.get("current_profit"), 0.0) < 0.0
                    and giveback_ratio >= 0.95
                    and abs(continuation - reversal) <= 0.04
                    and hold_score >= 0.30
                    and partial_score >= 0.47
                    and full_exit_score <= 0.50
                    and gap <= 0.02
                ):
                    label = "WAIT"
                    reason = "protective_late_open_loss_wait_retest"
                    confidence = max(wait_score, min(0.66, partial_score + 0.02))
                elif (
                    surface_name == "follow_through_surface"
                    and features["row_family"] == "active_open_loss"
                    and checkpoint_type == "INITIAL_PUSH"
                    and _to_float(features.get("current_profit"), 0.0) < 0.0
                    and continuation >= reversal + 0.10
                    and hold_score >= max(partial_score + 0.03, 0.34)
                    and full_exit_score <= 0.52
                ):
                    label = "WAIT"
                    reason = "early_open_loss_wait_retest"
                    confidence = max(wait_score, min(0.68, hold_score + 0.05))
                elif (
                    surface_name == "follow_through_surface"
                    and features["row_family"] == "open_loss_protective"
                    and checkpoint_type == "INITIAL_PUSH"
                    and _to_float(features.get("current_profit"), 0.0) < 0.0
                    and giveback_ratio >= 0.95
                    and continuation >= reversal + 0.10
                    and hold_score >= max(partial_score + 0.02, 0.34)
                    and full_exit_score <= 0.55
                    and gap <= 0.20
                ):
                    label = "WAIT"
                    reason = "early_open_loss_protective_wait_retest"
                    confidence = max(wait_score, min(0.66, hold_score + 0.04))
                elif partial_score >= max(wait_score, 0.26):
                    label = "PARTIAL_EXIT"
                    reason = "full_exit_gate_not_met_trim_fallback"
                    confidence = max(partial_score, min(0.82, 0.38 + gap))
                else:
                    label = "WAIT"
                    reason = "full_exit_gate_not_met_wait_fallback"
                    confidence = max(wait_score, 0.44)
            else:
                label = top_label
                confidence = top_score
                reason = f"score_leader::{_to_text(label).lower()}"

    return {
        "contract_version": PATH_CHECKPOINT_ACTION_RESOLVER_CONTRACT_VERSION,
        "management_action_label": label,
        "management_action_confidence": _clamp(confidence),
        "management_action_reason": reason,
        "management_action_score_gap": gap,
        "candidate_scores": dict(score_map),
        "top_candidate_label": top_label,
        "second_candidate_label": second_label,
    }


def apply_management_action_to_runtime_row(
    runtime_row: Mapping[str, Any] | None,
    action_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(runtime_row or {})
    payload = dict(action_payload or {})
    updated["path_checkpoint_action_resolver_contract_version"] = PATH_CHECKPOINT_ACTION_RESOLVER_CONTRACT_VERSION
    for source_key, target_key in PATH_CHECKPOINT_MANAGEMENT_ACTION_PREFIXED_KEYS.items():
        if source_key in payload:
            updated[target_key] = payload.get(source_key)
    return updated


def resolve_management_action_frame(checkpoint_rows: pd.DataFrame | None) -> pd.DataFrame:
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    if frame.empty:
        for key in PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS:
            frame[key] = []
        return frame

    for column in ("symbol", "generated_at", "surface_name", "checkpoint_id", "checkpoint_type"):
        if column not in frame.columns:
            frame[column] = ""
    for column in PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["management_action_reason"] = frame["management_action_reason"].astype(object)

    for index, row in frame.iterrows():
        existing_label = _to_text(row.get("management_action_label"))
        source = _to_text(row.get("source")).lower()
        if existing_label and source not in _REFRESHABLE_BACKFILL_SOURCES:
            continue
        payload = resolve_management_action(checkpoint_ctx=row.to_dict())
        for key in PATH_CHECKPOINT_MANAGEMENT_ACTION_KEYS:
            frame.at[index, key] = payload.get(key)
    return frame


def build_checkpoint_management_action_snapshot(
    runtime_status: Mapping[str, Any] | None,
    checkpoint_rows: pd.DataFrame | None,
    *,
    recent_limit: int = 400,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = resolve_management_action_frame(checkpoint_rows)
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_MANAGEMENT_ACTION_SNAPSHOT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "resolved_row_count": 0,
        "management_action_counts": {},
        "avg_management_action_confidence": 0.0,
        "recommended_next_action": "collect_more_management_action_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_MANAGEMENT_ACTION_SNAPSHOT_COLUMNS), summary

    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    recent = frame.sort_values("__time_sort").tail(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["resolved_row_count"] = int((scoped["management_action_label"].fillna("").astype(str).str.strip() != "").sum())
    summary["management_action_counts"] = scoped["management_action_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
    confidence_series = pd.to_numeric(scoped["management_action_confidence"], errors="coerce")
    summary["avg_management_action_confidence"] = round(float(confidence_series.dropna().mean() or 0.0), 6)

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy().sort_values("__time_sort")
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "recent_row_count": 0,
                    "resolved_row_count": 0,
                    "management_action_counts": "{}",
                    "avg_management_action_confidence": 0.0,
                    "latest_checkpoint_id": "",
                    "latest_surface_name": "",
                    "latest_time": "",
                    "recommended_focus": f"collect_more_{symbol.lower()}_management_actions",
                }
            )
            continue

        latest = symbol_frame.iloc[-1]
        action_counts = symbol_frame["management_action_label"].fillna("").astype(str).replace("", pd.NA).dropna().value_counts().to_dict()
        avg_conf = round(float(pd.to_numeric(symbol_frame["management_action_confidence"], errors="coerce").dropna().mean() or 0.0), 6)
        focus = f"inspect_{symbol.lower()}_management_action_balance"
        if action_counts.get("WAIT", 0) >= len(symbol_frame):
            focus = f"collect_more_{symbol.lower()}_position_side_management_rows"
        elif action_counts.get("FULL_EXIT", 0) > 0:
            focus = f"inspect_{symbol.lower()}_full_exit_precision"

        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": int(len(symbol_frame)),
                "resolved_row_count": int((symbol_frame["management_action_label"].fillna("").astype(str).str.strip() != "").sum()),
                "management_action_counts": _json_counts(action_counts),
                "avg_management_action_confidence": avg_conf,
                "latest_checkpoint_id": _to_text(latest.get("checkpoint_id")),
                "latest_surface_name": _to_text(latest.get("surface_name")),
                "latest_time": _to_text(latest.get("generated_at")),
                "recommended_focus": focus,
            }
        )

    snapshot = pd.DataFrame(rows, columns=PATH_CHECKPOINT_MANAGEMENT_ACTION_SNAPSHOT_COLUMNS)
    summary["recommended_next_action"] = (
        "inspect_pa6_runtime_management_action_balance"
        if summary["resolved_row_count"] > 0
        else "collect_more_live_position_side_checkpoint_rows_before_pa7"
    )
    return snapshot, summary
