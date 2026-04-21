"""Replay-based heuristic scene sanity check for SA2.5."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.path_checkpoint_scene_contract import (
    PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL,
)
from backend.services.path_checkpoint_scene_tagger import (
    tag_runtime_scene,
)
from backend.services.trade_csv_schema import now_kst_dt


PATH_CHECKPOINT_SCENE_SANITY_CONTRACT_VERSION = "checkpoint_scene_sanity_v1"
PATH_CHECKPOINT_SCENE_SANITY_COLUMNS = [
    "symbol",
    "row_count",
    "scene_filled_row_count",
    "fine_label_counts",
    "gate_label_counts",
    "alignment_counts",
    "watchlist_transition_count",
    "unexpected_transition_count",
    "top_fine_label",
    "recommended_focus",
]
_ALLOWED_TRANSITION_PAIRS = {
    ("trend_ignition", "breakout"),
    ("breakout", "breakout_retest_hold"),
    ("breakout", "time_decay_risk"),
    ("pullback_continuation", "runner_healthy"),
    ("runner_healthy", "trend_exhaustion"),
    ("trend_exhaustion", "climax_reversal"),
    ("runner_healthy", "protective_risk"),
    ("protective_risk", "failed_transition"),
    ("time_decay_risk", "rebuy_setup"),
}
_WATCHLIST_TRANSITION_PAIRS = {
    ("breakout_retest_hold", "trend_exhaustion"),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_scene_sanity_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_scene_sanity_latest.json"


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


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


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _resolve_transition_audit_key(row: Mapping[str, Any]) -> str:
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


def replay_checkpoint_scene_frame(
    checkpoint_rows: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
    recent_limit: int | None = None,
) -> pd.DataFrame:
    frame = checkpoint_rows.copy() if checkpoint_rows is not None and not checkpoint_rows.empty else pd.DataFrame()
    if frame.empty:
        return pd.DataFrame()

    for column in ("generated_at", "symbol"):
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
    if symbols:
        symbol_order = [str(symbol).upper() for symbol in symbols]
        frame = frame.loc[frame["symbol"].isin(symbol_order)].copy()
    if frame.empty:
        return pd.DataFrame()

    frame["__time_sort"] = pd.to_datetime(frame["generated_at"], errors="coerce")
    frame = frame.sort_values(["symbol", "__time_sort", "generated_at"]).copy()
    if recent_limit is not None and recent_limit > 0 and len(frame) > recent_limit:
        frame = frame.tail(int(recent_limit)).copy()

    previous_runtime_by_path: dict[str, dict[str, Any]] = {}
    replay_rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        symbol = _to_text(row.get("symbol")).upper()
        transition_key = _resolve_transition_audit_key(row)
        previous_runtime = previous_runtime_by_path.get(transition_key, {})
        scene_payload = tag_runtime_scene(
            symbol=symbol,
            runtime_row=row,
            checkpoint_row=row,
            previous_runtime_row=previous_runtime,
        )
        scene_row = dict(scene_payload.get("row", {}) or {})
        merged = dict(row)
        merged.update(scene_row)
        merged["__scene_transition_key"] = transition_key
        replay_rows.append(merged)
        previous_runtime_by_path[transition_key] = {
            "checkpoint_runtime_scene_fine_label": scene_row.get("runtime_scene_fine_label"),
            "checkpoint_runtime_scene_gate_label": scene_row.get("runtime_scene_gate_label"),
            "checkpoint_runtime_scene_transition_bars": scene_row.get("runtime_scene_transition_bars"),
        }
    replay = pd.DataFrame(replay_rows)
    return replay.drop(columns="__time_sort", errors="ignore")


def build_checkpoint_scene_sanity(
    checkpoint_rows: pd.DataFrame | None,
    *,
    symbols: Iterable[str] = ("BTCUSD", "NAS100", "XAUUSD"),
    recent_limit: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    replay = replay_checkpoint_scene_frame(checkpoint_rows, symbols=symbols, recent_limit=recent_limit)
    symbol_order = [str(symbol).upper() for symbol in symbols]
    summary: dict[str, Any] = {
        "contract_version": PATH_CHECKPOINT_SCENE_SANITY_CONTRACT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": 0,
        "scene_filled_row_count": 0,
        "fine_resolved_row_count": 0,
        "gate_tagged_row_count": 0,
        "unresolved_row_count": 0,
        "fine_label_counts": {},
        "gate_label_counts": {},
        "coarse_family_counts": {},
        "confidence_band_counts": {},
        "maturity_counts": {},
        "alignment_counts": {},
        "transition_pair_counts": {},
        "watchlist_transition_pair_counts": {},
        "unexpected_transition_pair_counts": {},
        "recommended_next_action": "collect_more_scene_seed_rows",
    }
    if replay.empty:
        return pd.DataFrame(columns=PATH_CHECKPOINT_SCENE_SANITY_COLUMNS), summary, replay

    fine_series = replay["runtime_scene_fine_label"].fillna("").astype(str)
    gate_series = replay["runtime_scene_gate_label"].fillna("").astype(str)
    coarse_series = replay["runtime_scene_coarse_family"].fillna("").astype(str)
    alignment_series = replay["runtime_scene_family_alignment"].fillna("").astype(str)
    band_series = replay["runtime_scene_confidence_band"].fillna("").astype(str)
    maturity_series = replay["runtime_scene_maturity"].fillna("").astype(str)
    scene_filled_mask = (fine_series != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL) | (gate_series != "none")
    fine_resolved_mask = fine_series != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL
    gate_tagged_mask = gate_series != "none"
    unresolved_mask = ~scene_filled_mask

    transition_counter: Counter[str] = Counter()
    watchlist_transition_counter: Counter[str] = Counter()
    unexpected_transition_counter: Counter[str] = Counter()
    previous_fine_by_path: dict[str, str] = {}
    for row in replay.sort_values(["symbol", "__scene_transition_key", "generated_at"]).to_dict(orient="records"):
        path_key = _to_text(row.get("__scene_transition_key"))
        current_fine = _to_text(row.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
        if current_fine == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL:
            continue
        previous_fine = previous_fine_by_path.get(path_key, PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
        if previous_fine != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and previous_fine != current_fine:
            pair = f"{previous_fine}->{current_fine}"
            transition_counter[pair] += 1
            if (previous_fine, current_fine) in _WATCHLIST_TRANSITION_PAIRS:
                watchlist_transition_counter[pair] += 1
            elif (previous_fine, current_fine) not in _ALLOWED_TRANSITION_PAIRS:
                unexpected_transition_counter[pair] += 1
        previous_fine_by_path[path_key] = current_fine

    summary["row_count"] = int(len(replay))
    summary["scene_filled_row_count"] = int(scene_filled_mask.sum())
    summary["fine_resolved_row_count"] = int(fine_resolved_mask.sum())
    summary["gate_tagged_row_count"] = int(gate_tagged_mask.sum())
    summary["unresolved_row_count"] = int(unresolved_mask.sum())
    summary["fine_label_counts"] = fine_series[fine_resolved_mask].replace("", pd.NA).dropna().value_counts().to_dict()
    summary["gate_label_counts"] = gate_series[gate_tagged_mask].replace("", pd.NA).dropna().value_counts().to_dict()
    summary["coarse_family_counts"] = coarse_series.replace("", pd.NA).dropna().value_counts().to_dict()
    summary["confidence_band_counts"] = band_series.replace("", pd.NA).dropna().value_counts().to_dict()
    summary["maturity_counts"] = maturity_series.replace("", pd.NA).dropna().value_counts().to_dict()
    summary["alignment_counts"] = alignment_series.replace("", pd.NA).dropna().value_counts().to_dict()
    summary["transition_pair_counts"] = dict(transition_counter)
    summary["watchlist_transition_pair_counts"] = dict(watchlist_transition_counter)
    summary["unexpected_transition_pair_counts"] = dict(unexpected_transition_counter)

    rows: list[dict[str, Any]] = []
    for symbol in symbol_order:
        symbol_frame = replay.loc[replay["symbol"] == symbol].copy()
        if symbol_frame.empty:
            rows.append(
                {
                    "symbol": symbol,
                    "row_count": 0,
                    "scene_filled_row_count": 0,
                    "fine_label_counts": "{}",
                    "gate_label_counts": "{}",
                    "alignment_counts": "{}",
                    "watchlist_transition_count": 0,
                    "unexpected_transition_count": 0,
                    "top_fine_label": "",
                    "recommended_focus": f"collect_more_{symbol.lower()}_scene_rows",
                }
            )
            continue

        symbol_fine = symbol_frame["runtime_scene_fine_label"].fillna("").astype(str)
        symbol_gate = symbol_frame["runtime_scene_gate_label"].fillna("").astype(str)
        symbol_alignment = symbol_frame["runtime_scene_family_alignment"].fillna("").astype(str)
        symbol_fine_counts = symbol_fine.loc[symbol_fine != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL].value_counts().to_dict()
        symbol_gate_counts = symbol_gate.loc[symbol_gate != "none"].value_counts().to_dict()
        symbol_alignment_counts = symbol_alignment.replace("", pd.NA).dropna().value_counts().to_dict()
        top_fine_label = next(iter(symbol_fine_counts.keys()), "")
        watchlist_count = 0
        unexpected_count = 0
        previous_fine_by_path_local: dict[str, str] = {}
        for _, scene_row in symbol_frame.sort_values(["__scene_transition_key", "generated_at"]).iterrows():
            current_fine = _to_text(scene_row.get("runtime_scene_fine_label"), PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            if current_fine == PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL:
                continue
            path_key = _to_text(scene_row.get("__scene_transition_key"))
            previous_fine = previous_fine_by_path_local.get(path_key, PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL)
            if previous_fine != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL and previous_fine != current_fine:
                if (previous_fine, current_fine) in _WATCHLIST_TRANSITION_PAIRS:
                    watchlist_count += 1
                elif (previous_fine, current_fine) not in _ALLOWED_TRANSITION_PAIRS:
                    unexpected_count += 1
            previous_fine_by_path_local[path_key] = current_fine

        recommended_focus = f"inspect_{symbol.lower()}_scene_distribution"
        scene_filled = int(((symbol_fine != PATH_CHECKPOINT_SCENE_UNRESOLVED_LABEL) | (symbol_gate != "none")).sum())
        if scene_filled <= 0:
            recommended_focus = f"loosen_{symbol.lower()}_heuristic_seed_coverage"
        elif int(symbol_alignment.eq("conflict").sum()) > 0:
            recommended_focus = f"inspect_{symbol.lower()}_surface_scene_conflicts"
        elif unexpected_count > 0:
            recommended_focus = f"inspect_{symbol.lower()}_unexpected_scene_transitions"
        elif watchlist_count > 0:
            recommended_focus = f"monitor_{symbol.lower()}_watchlist_scene_transitions"

        rows.append(
            {
                "symbol": symbol,
                "row_count": int(len(symbol_frame)),
                "scene_filled_row_count": scene_filled,
                "fine_label_counts": _json_counts(symbol_fine_counts),
                "gate_label_counts": _json_counts(symbol_gate_counts),
                "alignment_counts": _json_counts(symbol_alignment_counts),
                "watchlist_transition_count": int(watchlist_count),
                "unexpected_transition_count": int(unexpected_count),
                "top_fine_label": top_fine_label,
                "recommended_focus": recommended_focus,
            }
        )

    observation = pd.DataFrame(rows, columns=PATH_CHECKPOINT_SCENE_SANITY_COLUMNS)

    fine_counts = summary["fine_label_counts"]
    top_scene_count = max(fine_counts.values()) if fine_counts else 0
    conflict_count = _to_int(summary["alignment_counts"].get("conflict"), 0)
    if summary["scene_filled_row_count"] <= 0:
        summary["recommended_next_action"] = "collect_or_replay_more_scene_seed_rows_before_sa3"
    elif summary["scene_filled_row_count"] > 0 and top_scene_count / max(summary["scene_filled_row_count"], 1) >= 0.80:
        summary["recommended_next_action"] = "tighten_or_rebalance_scene_heuristics_before_sa3"
    elif conflict_count > 0:
        summary["recommended_next_action"] = "inspect_surface_scene_alignment_before_sa3"
    elif sum(unexpected_transition_counter.values()) > 0:
        summary["recommended_next_action"] = "inspect_unexpected_scene_transitions_before_sa3"
    elif sum(watchlist_transition_counter.values()) > 0:
        summary["recommended_next_action"] = "keep_watchlist_transition_monitoring_before_sa3"
    else:
        summary["recommended_next_action"] = "proceed_to_sa3_scene_dataset_export"
    return observation, summary, replay
