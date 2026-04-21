"""Path-aware passive checkpoint score calculation for PA4."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCORING_CONTRACT_VERSION = "path_checkpoint_scoring_v1"
PATH_CHECKPOINT_SCORE_SNAPSHOT_CONTRACT_VERSION = "checkpoint_score_snapshot_v1"
PATH_CHECKPOINT_RUNTIME_SCORE_KEYS = (
    "runtime_continuation_odds",
    "runtime_reversal_odds",
    "runtime_hold_quality_score",
    "runtime_partial_exit_ev",
    "runtime_full_exit_risk",
    "runtime_rebuy_readiness",
    "runtime_score_reason",
)
PATH_CHECKPOINT_RUNTIME_SCORE_PREFIXED_KEYS = {
    "runtime_continuation_odds": "checkpoint_runtime_continuation_odds",
    "runtime_reversal_odds": "checkpoint_runtime_reversal_odds",
    "runtime_hold_quality_score": "checkpoint_runtime_hold_quality_score",
    "runtime_partial_exit_ev": "checkpoint_runtime_partial_exit_ev",
    "runtime_full_exit_risk": "checkpoint_runtime_full_exit_risk",
    "runtime_rebuy_readiness": "checkpoint_runtime_rebuy_readiness",
    "runtime_score_reason": "checkpoint_runtime_score_reason",
}
PATH_CHECKPOINT_SCORE_SNAPSHOT_COLUMNS = [
    "symbol",
    "recent_row_count",
    "scored_row_count",
    "surface_counts",
    "avg_runtime_continuation_odds",
    "avg_runtime_reversal_odds",
    "avg_runtime_hold_quality_score",
    "avg_runtime_partial_exit_ev",
    "avg_runtime_full_exit_risk",
    "avg_runtime_rebuy_readiness",
    "high_full_exit_risk_count",
    "high_rebuy_readiness_count",
    "latest_checkpoint_id",
    "latest_surface_name",
    "latest_time",
    "recommended_focus",
]

_LEG_ACTION_BY_DIRECTION = {"UP": "BUY", "DOWN": "SELL"}
_CONTINUATION_BASE_BY_TYPE = {
    "INITIAL_PUSH": 0.58,
    "FIRST_PULLBACK_CHECK": 0.47,
    "RECLAIM_CHECK": 0.68,
    "LATE_TREND_CHECK": 0.54,
    "RUNNER_CHECK": 0.50,
}
_REVERSAL_BASE_BY_TYPE = {
    "INITIAL_PUSH": 0.24,
    "FIRST_PULLBACK_CHECK": 0.42,
    "RECLAIM_CHECK": 0.27,
    "LATE_TREND_CHECK": 0.40,
    "RUNNER_CHECK": 0.48,
}
_CONTINUATION_TOKENS = (
    "reclaim",
    "continuation",
    "follow_through",
    "followthrough",
    "breakout",
    "runner",
)
_ADVERSE_TOKENS = (
    "protect",
    "reject",
    "break_fail",
    "breakdown",
    "adverse",
    "bad_loss",
    "fast_cut",
    "thesis_break",
    "timeout",
    "loss",
    "stop",
)
_WRONG_SIDE_SUPPORT_TOKENS = (
    "active_action_conflict_guard",
    "wrong_side",
    "missed_up_continuation",
    "missed_down_continuation",
    "false_down_pressure",
    "false_up_pressure",
)


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


def _clamp_score(value: float) -> float:
    return round(max(0.01, min(0.99, float(value))), 6)


def _normalize_action(value: object) -> str:
    text = _to_text(value).upper()
    if text in {"BUY", "LONG"}:
        return "BUY"
    if text in {"SELL", "SHORT"}:
        return "SELL"
    return ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_score_snapshot_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_score_snapshot_latest.json"


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _resolve_alignment_flags(leg_action: str, row: Mapping[str, Any]) -> tuple[int, int]:
    candidate_values = (
        row.get("observe_action"),
        row.get("observe_side"),
        row.get("entry_candidate_bridge_action"),
        row.get("breakout_candidate_action"),
        row.get("position_side"),
    )
    same_hits = 0
    opposite_hits = 0
    opposite_action = "SELL" if leg_action == "BUY" else ("BUY" if leg_action == "SELL" else "")
    for value in candidate_values:
        normalized = _normalize_action(value)
        if not normalized:
            continue
        if normalized == leg_action:
            same_hits += 1
        elif normalized == opposite_action:
            opposite_hits += 1
    return same_hits, opposite_hits


def _build_reason_blob(row: Mapping[str, Any], checkpoint_row: Mapping[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                _to_text(row.get("blocked_by")).lower(),
                _to_text(row.get("action_none_reason")).lower(),
                _to_text(row.get("consumer_check_reason")).lower(),
                _to_text(row.get("setup_reason")).lower(),
                _to_text(checkpoint_row.get("checkpoint_transition_reason")).lower(),
                _to_text(row.get("entry_candidate_bridge_mode")).lower(),
            ],
        )
    )


def build_passive_checkpoint_scores(
    *,
    symbol: str,
    runtime_row: Mapping[str, Any] | None,
    checkpoint_row: Mapping[str, Any] | None,
    symbol_state: Mapping[str, Any] | None = None,
    position_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = dict(runtime_row or {})
    checkpoint = dict(checkpoint_row or {})
    _ = dict(symbol_state or {})
    position = dict(position_state or {})

    symbol_u = _to_text(symbol or checkpoint.get("symbol") or row.get("symbol")).upper()
    checkpoint_type = _to_text(checkpoint.get("checkpoint_type")).upper()
    surface_name = _to_text(checkpoint.get("surface_name")).lower()
    leg_direction = _to_text(checkpoint.get("leg_direction") or row.get("leg_direction")).upper()
    leg_action = _LEG_ACTION_BY_DIRECTION.get(leg_direction, "")
    bars_since_last_checkpoint = _to_int(checkpoint.get("bars_since_last_checkpoint"), 0)
    size_fraction = max(0.0, min(1.0, _to_float(checkpoint.get("position_size_fraction"), position.get("position_size_fraction", 0.0))))
    runner_secured = _to_bool(checkpoint.get("runner_secured"), _to_bool(position.get("runner_secured"), False))
    unrealized_pnl_state = _to_text(checkpoint.get("unrealized_pnl_state"), _to_text(position.get("unrealized_pnl_state"), "FLAT")).upper()
    mfe_since_entry = max(0.0, _to_float(checkpoint.get("mfe_since_entry"), position.get("mfe_since_entry", 0.0)))
    mae_since_entry = max(0.0, _to_float(checkpoint.get("mae_since_entry"), position.get("mae_since_entry", 0.0)))
    total_excursion = mfe_since_entry + mae_since_entry
    favorable_ratio = (mfe_since_entry / total_excursion) if total_excursion > 0 else (1.0 if unrealized_pnl_state == "OPEN_PROFIT" else 0.0)
    adverse_ratio = (mae_since_entry / total_excursion) if total_excursion > 0 else (1.0 if unrealized_pnl_state == "OPEN_LOSS" else 0.0)
    same_hits, opposite_hits = _resolve_alignment_flags(leg_action, {**row, **checkpoint})
    reason_blob = _build_reason_blob(row, checkpoint)

    continuation_base = _CONTINUATION_BASE_BY_TYPE.get(checkpoint_type, 0.50)
    reversal_base = _REVERSAL_BASE_BY_TYPE.get(checkpoint_type, 0.34)
    same_direction_support = min(0.18, same_hits * 0.05)
    opposite_pressure = min(0.24, opposite_hits * 0.06)
    continuation_token_support = 0.08 if any(token in reason_blob for token in _CONTINUATION_TOKENS) else 0.0
    wrong_side_support = 0.16 if any(token in reason_blob for token in _WRONG_SIDE_SUPPORT_TOKENS) else 0.0
    adverse_pressure = 0.12 if any(token in reason_blob for token in _ADVERSE_TOKENS) else 0.0
    reclaim_support = 0.10 if checkpoint_type == "RECLAIM_CHECK" else 0.0
    late_exhaustion_pressure = 0.06 if checkpoint_type in {"LATE_TREND_CHECK", "RUNNER_CHECK"} and bars_since_last_checkpoint >= 2 else 0.0
    early_pullback_pressure = 0.06 if checkpoint_type == "FIRST_PULLBACK_CHECK" else 0.0
    protective_pressure = 0.18 if surface_name == "protective_exit_surface" else 0.0
    profit_support = 0.08 if unrealized_pnl_state == "OPEN_PROFIT" else 0.0
    loss_pressure = 0.12 if unrealized_pnl_state == "OPEN_LOSS" else 0.0
    runner_support = 0.08 if runner_secured else 0.0

    if wrong_side_support > 0.0:
        opposite_pressure = max(0.0, opposite_pressure - 0.10)

    continuation = _clamp_score(
        continuation_base
        + same_direction_support
        + continuation_token_support
        + wrong_side_support
        + reclaim_support
        + profit_support
        + runner_support * 0.5
        + favorable_ratio * 0.10
        - opposite_pressure * 0.45
        - adverse_pressure * 0.30
        - protective_pressure * 0.35
        - loss_pressure * 0.35
        - late_exhaustion_pressure * 0.20
        - early_pullback_pressure * 0.12
    )
    reversal = _clamp_score(
        reversal_base
        + opposite_pressure
        + adverse_pressure
        + protective_pressure
        + loss_pressure
        + adverse_ratio * 0.10
        + late_exhaustion_pressure
        + early_pullback_pressure * 0.60
        - same_direction_support * 0.35
        - continuation_token_support * 0.20
        - wrong_side_support * 0.25
        - reclaim_support * 0.28
        - profit_support * 0.20
    )
    hold_quality = _clamp_score(
        0.18
        + continuation * 0.55
        - reversal * 0.28
        + runner_support * 0.25
        + profit_support * 0.20
        - loss_pressure * 0.35
        - protective_pressure * 0.20
        - (0.04 if _to_text(checkpoint.get("position_side")).upper() == "FLAT" else 0.0)
    )
    partial_exit_ev = _clamp_score(
        0.10
        + continuation * 0.20
        + reversal * 0.14
        + runner_support * 0.30
        + late_exhaustion_pressure * 0.55
        + favorable_ratio * 0.12
        + (0.08 if unrealized_pnl_state == "OPEN_PROFIT" else 0.0)
        - (0.06 if _to_text(checkpoint.get("position_side")).upper() == "FLAT" else 0.0)
        - (0.05 if size_fraction <= 0.25 and _to_text(checkpoint.get("position_side")).upper() != "FLAT" else 0.0)
    )
    full_exit_risk = _clamp_score(
        0.08
        + reversal * 0.55
        + protective_pressure * 0.40
        + loss_pressure * 0.35
        + adverse_ratio * 0.20
        - continuation * 0.18
        - wrong_side_support * 0.12
        - runner_support * 0.10
    )
    rebuy_readiness = _clamp_score(
        0.08
        + continuation * 0.30
        - reversal * 0.16
        + (0.16 if checkpoint_type in {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"} else 0.0)
        + same_direction_support * 0.18
        + continuation_token_support * 0.10
        + (0.10 if size_fraction < 0.75 else 0.0)
        - protective_pressure * 0.18
        - loss_pressure * 0.10
        - (0.08 if size_fraction >= 0.95 and _to_text(checkpoint.get("position_side")).upper() != "FLAT" else 0.0)
    )

    if full_exit_risk >= max(hold_quality, partial_exit_ev, rebuy_readiness) and full_exit_risk >= 0.62:
        score_reason = f"{surface_name or 'checkpoint'}::protective_pressure_dominant"
    elif partial_exit_ev >= max(hold_quality, rebuy_readiness) and partial_exit_ev >= 0.58:
        score_reason = f"{surface_name or 'checkpoint'}::runner_lock_bias"
    elif rebuy_readiness >= 0.60 and checkpoint_type in {"FIRST_PULLBACK_CHECK", "RECLAIM_CHECK"}:
        score_reason = f"{surface_name or 'checkpoint'}::pullback_reentry_ready"
    elif hold_quality >= full_exit_risk and continuation >= reversal:
        score_reason = f"{surface_name or 'checkpoint'}::continuation_hold_bias"
    else:
        score_reason = f"{surface_name or 'checkpoint'}::balanced_checkpoint_state"

    score_row = {
        "runtime_continuation_odds": continuation,
        "runtime_reversal_odds": reversal,
        "runtime_hold_quality_score": hold_quality,
        "runtime_partial_exit_ev": partial_exit_ev,
        "runtime_full_exit_risk": full_exit_risk,
        "runtime_rebuy_readiness": rebuy_readiness,
        "runtime_score_reason": score_reason,
    }
    score_detail = {
        "contract_version": PATH_CHECKPOINT_SCORING_CONTRACT_VERSION,
        "symbol": symbol_u,
        "checkpoint_type": checkpoint_type,
        "surface_name": surface_name,
        "components": {
            "continuation_base": round(continuation_base, 6),
            "reversal_base": round(reversal_base, 6),
            "same_direction_support": round(same_direction_support, 6),
            "continuation_token_support": round(continuation_token_support, 6),
            "wrong_side_support": round(wrong_side_support, 6),
            "opposite_pressure": round(opposite_pressure, 6),
            "adverse_pressure": round(adverse_pressure, 6),
            "reclaim_support": round(reclaim_support, 6),
            "late_exhaustion_pressure": round(late_exhaustion_pressure, 6),
            "early_pullback_pressure": round(early_pullback_pressure, 6),
            "protective_pressure": round(protective_pressure, 6),
            "profit_support": round(profit_support, 6),
            "loss_pressure": round(loss_pressure, 6),
            "runner_support": round(runner_support, 6),
            "favorable_ratio": round(favorable_ratio, 6),
            "adverse_ratio": round(adverse_ratio, 6),
        },
        "flags": {
            "leg_direction": leg_direction,
            "leg_action": leg_action,
            "same_direction_hits": int(same_hits),
            "opposite_direction_hits": int(opposite_hits),
            "runner_secured": bool(runner_secured),
            "unrealized_pnl_state": unrealized_pnl_state,
            "size_fraction": round(size_fraction, 6),
        },
        "row": dict(score_row),
    }
    return {
        "contract_version": PATH_CHECKPOINT_SCORING_CONTRACT_VERSION,
        "row": score_row,
        "detail": score_detail,
    }


def apply_checkpoint_scores_to_runtime_row(
    runtime_row: Mapping[str, Any] | None,
    score_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(runtime_row or {})
    scores = dict(score_row or {})
    updated["path_checkpoint_scoring_contract_version"] = PATH_CHECKPOINT_SCORING_CONTRACT_VERSION
    for source_key, target_key in PATH_CHECKPOINT_RUNTIME_SCORE_PREFIXED_KEYS.items():
        if source_key in scores:
            updated[target_key] = scores.get(source_key)
    return updated


def score_checkpoint_frame(checkpoint_rows: pd.DataFrame | None) -> pd.DataFrame:
    if checkpoint_rows is None or checkpoint_rows.empty:
        frame = pd.DataFrame()
    else:
        frame = checkpoint_rows.copy()
    if frame.empty:
        for key in PATH_CHECKPOINT_RUNTIME_SCORE_KEYS:
            frame[key] = []
        return frame

    for column in ("symbol", "generated_at", "surface_name", "checkpoint_id", "checkpoint_type"):
        if column not in frame.columns:
            frame[column] = ""
    for column in PATH_CHECKPOINT_RUNTIME_SCORE_KEYS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["runtime_score_reason"] = frame["runtime_score_reason"].astype(object)

    for index, row in frame.iterrows():
        score_values = [row.get(key) for key in PATH_CHECKPOINT_RUNTIME_SCORE_KEYS[:-1]]
        has_scores = any(_to_text(value) for value in score_values)
        if has_scores:
            continue
        payload = build_passive_checkpoint_scores(
            symbol=_to_text(row.get("symbol")),
            runtime_row=row.to_dict(),
            checkpoint_row=row.to_dict(),
        )
        score_row = dict(payload.get("row", {}) or {})
        for key, value in score_row.items():
            frame.at[index, key] = value
    return frame


def build_checkpoint_score_snapshot(
    runtime_status: Mapping[str, Any] | None,
    checkpoint_rows: pd.DataFrame | None,
    *,
    recent_limit: int = 400,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    frame = score_checkpoint_frame(checkpoint_rows)
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCORE_SNAPSHOT_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "recent_row_count": 0,
        "market_family_row_count": 0,
        "score_row_count": 0,
        "avg_runtime_continuation_odds": 0.0,
        "avg_runtime_reversal_odds": 0.0,
        "avg_runtime_hold_quality_score": 0.0,
        "avg_runtime_partial_exit_ev": 0.0,
        "avg_runtime_full_exit_risk": 0.0,
        "avg_runtime_rebuy_readiness": 0.0,
        "recommended_next_action": "collect_more_checkpoint_score_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCORE_SNAPSHOT_COLUMNS), summary

    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    recent = frame.sort_values("__time_sort").tail(max(1, int(recent_limit))).copy()
    scoped = recent.loc[recent["symbol"].isin(symbol_order)].copy()
    summary["recent_row_count"] = int(len(recent))
    summary["market_family_row_count"] = int(len(scoped))

    numeric_keys = PATH_CHECKPOINT_RUNTIME_SCORE_KEYS[:-1]
    for key in numeric_keys:
        scoped[key] = pd.to_numeric(scoped[key], errors="coerce")
    summary["score_row_count"] = int(scoped["runtime_continuation_odds"].notna().sum())
    for key in numeric_keys:
        summary[f"avg_{key}"] = round(float(scoped[key].dropna().mean() or 0.0), 6)

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = scoped.loc[scoped["symbol"] == symbol].copy().sort_values("__time_sort")
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "recent_row_count": 0,
                    "scored_row_count": 0,
                    "surface_counts": "{}",
                    "avg_runtime_continuation_odds": 0.0,
                    "avg_runtime_reversal_odds": 0.0,
                    "avg_runtime_hold_quality_score": 0.0,
                    "avg_runtime_partial_exit_ev": 0.0,
                    "avg_runtime_full_exit_risk": 0.0,
                    "avg_runtime_rebuy_readiness": 0.0,
                    "high_full_exit_risk_count": 0,
                    "high_rebuy_readiness_count": 0,
                    "latest_checkpoint_id": "",
                    "latest_surface_name": "",
                    "latest_time": "",
                    "recommended_focus": f"collect_more_{symbol.lower()}_checkpoint_scores",
                }
            )
            continue

        surface_counts = (
            symbol_frame["surface_name"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().value_counts().to_dict()
        )
        latest = symbol_frame.iloc[-1]
        high_full_exit_risk_count = int((symbol_frame["runtime_full_exit_risk"] >= 0.60).sum())
        high_rebuy_readiness_count = int((symbol_frame["runtime_rebuy_readiness"] >= 0.60).sum())
        avg_hold_quality = round(float(symbol_frame["runtime_hold_quality_score"].dropna().mean() or 0.0), 6)
        avg_full_exit_risk = round(float(symbol_frame["runtime_full_exit_risk"].dropna().mean() or 0.0), 6)
        avg_rebuy_readiness = round(float(symbol_frame["runtime_rebuy_readiness"].dropna().mean() or 0.0), 6)
        focus = f"inspect_{symbol.lower()}_checkpoint_score_balance"
        if avg_full_exit_risk >= 0.58:
            focus = f"inspect_{symbol.lower()}_protective_exit_bias"
        elif avg_rebuy_readiness >= 0.58:
            focus = f"inspect_{symbol.lower()}_reentry_reclaim_quality"
        elif avg_hold_quality <= 0.50:
            focus = f"inspect_{symbol.lower()}_hold_quality_gap"

        rows.append(
            {
                "symbol": symbol,
                "recent_row_count": int(len(symbol_frame)),
                "scored_row_count": int(symbol_frame["runtime_continuation_odds"].dropna().shape[0]),
                "surface_counts": _json_counts(surface_counts),
                "avg_runtime_continuation_odds": round(float(symbol_frame["runtime_continuation_odds"].dropna().mean() or 0.0), 6),
                "avg_runtime_reversal_odds": round(float(symbol_frame["runtime_reversal_odds"].dropna().mean() or 0.0), 6),
                "avg_runtime_hold_quality_score": avg_hold_quality,
                "avg_runtime_partial_exit_ev": round(float(symbol_frame["runtime_partial_exit_ev"].dropna().mean() or 0.0), 6),
                "avg_runtime_full_exit_risk": avg_full_exit_risk,
                "avg_runtime_rebuy_readiness": avg_rebuy_readiness,
                "high_full_exit_risk_count": high_full_exit_risk_count,
                "high_rebuy_readiness_count": high_rebuy_readiness_count,
                "latest_checkpoint_id": _to_text(latest.get("checkpoint_id")),
                "latest_surface_name": _to_text(latest.get("surface_name")),
                "latest_time": _to_text(latest.get("generated_at")),
                "recommended_focus": focus,
            }
        )

    snapshot = pd.DataFrame(rows, columns=PATH_CHECKPOINT_SCORE_SNAPSHOT_COLUMNS)
    summary["recommended_next_action"] = (
        "proceed_to_pa5_hindsight_label_dataset_eval"
        if summary["market_family_row_count"] > 0 and summary["score_row_count"] > 0
        else "collect_more_live_checkpoint_scores_before_pa5"
    )
    return snapshot, summary
