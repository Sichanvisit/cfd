"""Observation snapshot for position-side checkpoint row growth."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_action_resolver import (
    _REFRESHABLE_BACKFILL_SOURCES,
    resolve_management_action,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_POSITION_SIDE_OBSERVATION_CONTRACT_VERSION = "checkpoint_position_side_observation_v1"
PATH_CHECKPOINT_POSITION_SIDE_OBSERVATION_COLUMNS = [
    "symbol",
    "position_side_row_count",
    "open_profit_row_count",
    "open_loss_row_count",
    "runner_secured_row_count",
    "live_runner_source_row_count",
    "hold_candidate_row_count",
    "full_exit_candidate_row_count",
    "giveback_heavy_row_count",
    "family_counts",
    "source_counts",
    "management_action_counts",
    "latest_source",
    "latest_rule_family_hint",
    "latest_management_action_label",
    "latest_time",
    "recommended_focus",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_position_side_observation_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_position_side_observation_latest.json"


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


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def build_checkpoint_position_side_observation(
    checkpoint_rows: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_POSITION_SIDE_OBSERVATION_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": 0,
        "position_side_row_count": 0,
        "open_profit_row_count": 0,
        "open_loss_row_count": 0,
        "runner_secured_row_count": 0,
        "live_runner_source_row_count": 0,
        "hold_candidate_row_count": 0,
        "full_exit_candidate_row_count": 0,
        "giveback_heavy_row_count": 0,
        "family_counts": {},
        "source_counts": {},
        "management_action_counts": {},
        "recommended_next_action": "collect_more_exit_manage_position_side_rows",
    }
    if frame.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_POSITION_SIDE_OBSERVATION_COLUMNS), summary

    for column in (
        "generated_at",
        "symbol",
        "source",
        "position_side",
        "unrealized_pnl_state",
        "runner_secured",
        "giveback_ratio",
        "checkpoint_rule_family_hint",
        "management_action_label",
    ):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    frame["position_side"] = frame["position_side"].fillna("").astype(str).str.upper()
    frame["unrealized_pnl_state"] = frame["unrealized_pnl_state"].fillna("").astype(str).str.upper()
    frame["source"] = frame["source"].fillna("").astype(str)
    frame["checkpoint_rule_family_hint"] = frame["checkpoint_rule_family_hint"].fillna("").astype(str).str.lower()
    frame["management_action_label"] = frame["management_action_label"].fillna("").astype(str)
    frame["effective_management_action_label"] = frame["management_action_label"]
    refresh_mask = frame["source"].str.lower().isin(_REFRESHABLE_BACKFILL_SOURCES)
    if bool(refresh_mask.any()):
        for index, row in frame.loc[refresh_mask].iterrows():
            payload = resolve_management_action(checkpoint_ctx=row.to_dict())
            frame.at[index, "effective_management_action_label"] = _to_text(payload.get("management_action_label"))
    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    scoped = frame.loc[frame["symbol"].isin(symbol_order)].copy()

    position_side_mask = scoped["position_side"] != "FLAT"
    hold_candidate_mask = position_side_mask & (
        scoped["checkpoint_rule_family_hint"].isin({"runner_secured_continuation", "profit_hold_bias"})
        | scoped["effective_management_action_label"].isin({"HOLD", "PARTIAL_THEN_HOLD"})
    )
    full_exit_candidate_mask = position_side_mask & (
        scoped["checkpoint_rule_family_hint"].isin({"open_loss_protective", "active_open_loss"})
        | (scoped["effective_management_action_label"] == "FULL_EXIT")
    )
    giveback_heavy_mask = position_side_mask & (scoped["giveback_ratio"].apply(_to_float) >= 0.30)
    summary["row_count"] = int(len(scoped))
    summary["position_side_row_count"] = int(position_side_mask.sum())
    summary["open_profit_row_count"] = int((position_side_mask & (scoped["unrealized_pnl_state"] == "OPEN_PROFIT")).sum())
    summary["open_loss_row_count"] = int((position_side_mask & (scoped["unrealized_pnl_state"] == "OPEN_LOSS")).sum())
    summary["runner_secured_row_count"] = int((position_side_mask & scoped["runner_secured"].apply(_to_bool)).sum())
    summary["live_runner_source_row_count"] = int(
        (position_side_mask & (scoped["source"].fillna("").astype(str) == "exit_manage_runner")).sum()
    )
    summary["hold_candidate_row_count"] = int(hold_candidate_mask.sum())
    summary["full_exit_candidate_row_count"] = int(full_exit_candidate_mask.sum())
    summary["giveback_heavy_row_count"] = int(giveback_heavy_mask.sum())
    summary["family_counts"] = scoped.loc[position_side_mask, "checkpoint_rule_family_hint"].replace("", pd.NA).dropna().value_counts().to_dict()
    summary["source_counts"] = scoped.loc[position_side_mask, "source"].replace("", pd.NA).dropna().value_counts().to_dict()
    summary["management_action_counts"] = scoped.loc[position_side_mask, "effective_management_action_label"].replace("", pd.NA).dropna().value_counts().to_dict()

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = scoped.loc[(scoped["symbol"] == symbol) & position_side_mask].copy().sort_values("__time_sort")
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "position_side_row_count": 0,
                    "open_profit_row_count": 0,
                    "open_loss_row_count": 0,
                    "runner_secured_row_count": 0,
                    "live_runner_source_row_count": 0,
                    "hold_candidate_row_count": 0,
                    "full_exit_candidate_row_count": 0,
                    "giveback_heavy_row_count": 0,
                    "family_counts": "{}",
                    "source_counts": "{}",
                    "management_action_counts": "{}",
                    "latest_source": "",
                    "latest_rule_family_hint": "",
                    "latest_management_action_label": "",
                    "latest_time": "",
                    "recommended_focus": f"collect_more_{symbol.lower()}_position_side_rows",
                }
            )
            continue

        latest = symbol_frame.iloc[-1]
        source_counts = symbol_frame["source"].replace("", pd.NA).dropna().value_counts().to_dict()
        management_counts = symbol_frame["effective_management_action_label"].replace("", pd.NA).dropna().value_counts().to_dict()
        family_counts = symbol_frame["checkpoint_rule_family_hint"].replace("", pd.NA).dropna().value_counts().to_dict()
        recommended_focus = f"inspect_{symbol.lower()}_position_side_balance"
        if int((symbol_frame["unrealized_pnl_state"] == "OPEN_LOSS").sum()) <= 0:
            recommended_focus = f"collect_more_{symbol.lower()}_open_loss_rows"
        elif int(symbol_frame["runner_secured"].apply(_to_bool).sum()) <= 0:
            recommended_focus = f"collect_more_{symbol.lower()}_runner_secured_rows"
        elif int((symbol_frame["unrealized_pnl_state"] == "OPEN_PROFIT").sum()) <= 0:
            recommended_focus = f"collect_more_{symbol.lower()}_open_profit_rows"
        elif int(
            (
                symbol_frame["checkpoint_rule_family_hint"].isin({"runner_secured_continuation", "profit_hold_bias"})
                | symbol_frame["effective_management_action_label"].isin({"HOLD", "PARTIAL_THEN_HOLD"})
            ).sum()
        ) <= 0:
            recommended_focus = f"inspect_{symbol.lower()}_hold_candidate_gap"

        rows.append(
            {
                "symbol": symbol,
                "position_side_row_count": int(len(symbol_frame)),
                "open_profit_row_count": int((symbol_frame["unrealized_pnl_state"] == "OPEN_PROFIT").sum()),
                "open_loss_row_count": int((symbol_frame["unrealized_pnl_state"] == "OPEN_LOSS").sum()),
                "runner_secured_row_count": int(symbol_frame["runner_secured"].apply(_to_bool).sum()),
                "live_runner_source_row_count": int((symbol_frame["source"].fillna("").astype(str) == "exit_manage_runner").sum()),
                "hold_candidate_row_count": int(
                    (
                        symbol_frame["checkpoint_rule_family_hint"].isin({"runner_secured_continuation", "profit_hold_bias"})
                        | symbol_frame["effective_management_action_label"].isin({"HOLD", "PARTIAL_THEN_HOLD"})
                    ).sum()
                ),
                "full_exit_candidate_row_count": int(
                    (
                        symbol_frame["checkpoint_rule_family_hint"].isin({"open_loss_protective", "active_open_loss"})
                        | (symbol_frame["effective_management_action_label"] == "FULL_EXIT")
                    ).sum()
                ),
                "giveback_heavy_row_count": int((symbol_frame["giveback_ratio"].apply(_to_float) >= 0.30).sum()),
                "family_counts": _json_counts(family_counts),
                "source_counts": _json_counts(source_counts),
                "management_action_counts": _json_counts(management_counts),
                "latest_source": _to_text(latest.get("source")),
                "latest_rule_family_hint": _to_text(latest.get("checkpoint_rule_family_hint")),
                "latest_management_action_label": _to_text(latest.get("management_action_label")),
                "latest_time": _to_text(latest.get("generated_at")),
                "recommended_focus": recommended_focus,
            }
        )

    observation = pd.DataFrame(rows, columns=PATH_CHECKPOINT_POSITION_SIDE_OBSERVATION_COLUMNS)
    if summary["open_loss_row_count"] > 0 and summary["runner_secured_row_count"] > 0:
        summary["recommended_next_action"] = "rebuild_pa5_dataset_with_richer_exit_manage_rows"
    elif summary["position_side_row_count"] > 0:
        summary["recommended_next_action"] = "keep_collecting_exit_manage_position_side_rows"
    return observation, summary
