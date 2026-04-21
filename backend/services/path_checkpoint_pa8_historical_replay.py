from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.path_checkpoint_pa8_action_preview import (
    build_nas100_profit_hold_bias_action_preview,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    build_checkpoint_pa8_symbol_action_preview,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_pa8_historical_replay_board_json_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_historical_replay_board_latest.json"


def default_checkpoint_pa8_historical_replay_board_markdown_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_historical_replay_board_latest.md"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _slice_replay_window(preview_frame: pd.DataFrame, sample_floor: int) -> pd.DataFrame:
    if preview_frame is None or preview_frame.empty:
        return pd.DataFrame()
    changed = preview_frame.loc[preview_frame["preview_changed"].astype(bool)].copy()
    if changed.empty:
        return pd.DataFrame()
    if "generated_at" in changed.columns:
        changed["__generated_at"] = pd.to_datetime(changed["generated_at"], errors="coerce", utc=True)
        if changed["__generated_at"].notna().any():
            changed = changed.sort_values(by=["__generated_at", "checkpoint_id"], ascending=[True, True])
    return changed.tail(sample_floor).copy()


def _build_symbol_replay(symbol: str, resolved_dataset: pd.DataFrame | None) -> dict[str, Any]:
    symbol_upper = _to_text(symbol).upper()
    if symbol_upper == "NAS100":
        preview_frame, preview_summary = build_nas100_profit_hold_bias_action_preview(resolved_dataset)
        sample_floor = 50
        candidate_action = "PARTIAL_THEN_HOLD"
    else:
        preview_frame, preview_summary = build_checkpoint_pa8_symbol_action_preview(resolved_dataset, symbol=symbol_upper)
        sample_floor = _to_int(preview_summary.get("sample_floor"))
        candidate_action = _to_text(preview_summary.get("candidate_action"))

    replay_window = _slice_replay_window(preview_frame, sample_floor)
    replay_row_count = int(len(replay_window))
    replay_action_precision = 0.0
    replay_runtime_proxy_match_rate = 0.0
    replay_worsened_rows = 0
    replay_ready = False
    closeout_preview_state = "HOLD_REPLAY_WINDOW_BELOW_FLOOR"
    recommended_next_action = "collect_more_replay_scope_rows"
    replay_window_first_generated_at = ""
    replay_window_last_generated_at = ""

    if replay_row_count > 0:
        if "generated_at" in replay_window.columns:
            generated_at_values = replay_window["generated_at"].fillna("").astype(str).tolist()
            if generated_at_values:
                replay_window_first_generated_at = _to_text(generated_at_values[0])
                replay_window_last_generated_at = _to_text(generated_at_values[-1])
        hindsight = replay_window["hindsight_best_management_action_label"].fillna("").astype(str).str.upper()
        preview_action = replay_window["preview_action_label"].fillna("").astype(str).str.upper()
        baseline_action = replay_window["baseline_action_label"].fillna("").astype(str).str.upper()
        replay_action_precision = round(float((hindsight == preview_action).mean()), 6)
        replay_runtime_proxy_match_rate = round(float(replay_window["preview_hindsight_match"].astype(bool).mean()), 6)
        replay_worsened_rows = int(((~replay_window["preview_hindsight_match"].astype(bool)) & (replay_window["baseline_hindsight_match"].astype(bool))).sum())
        if replay_row_count >= sample_floor and replay_worsened_rows == 0:
            replay_ready = True
            closeout_preview_state = "READY_FOR_PA9_REPLAY_PREVIEW"
            recommended_next_action = "treat_replay_as_supporting_evidence_only_and_wait_for_live_window"
        else:
            closeout_preview_state = "HOLD_REPLAY_WINDOW_BELOW_FLOOR"

    return {
        "symbol": symbol_upper,
        "candidate_action": candidate_action,
        "preview_changed_row_count": _to_int(preview_summary.get("preview_changed_row_count")),
        "sample_floor": sample_floor,
        "replay_window_row_count": replay_row_count,
        "replay_window_first_generated_at": replay_window_first_generated_at,
        "replay_window_last_generated_at": replay_window_last_generated_at,
        "replay_action_precision": replay_action_precision,
        "replay_runtime_proxy_match_rate": replay_runtime_proxy_match_rate,
        "replay_worsened_rows": replay_worsened_rows,
        "replay_ready": replay_ready,
        "closeout_preview_state": closeout_preview_state,
        "recommended_next_action": recommended_next_action,
        "historical_replay_only": True,
        "preview_recommended_next_action": _to_text(preview_summary.get("recommended_next_action")),
    }


def build_checkpoint_pa8_historical_replay_board(resolved_dataset: pd.DataFrame | None) -> dict[str, Any]:
    rows = [
        _build_symbol_replay("NAS100", resolved_dataset),
        _build_symbol_replay("BTCUSD", resolved_dataset),
        _build_symbol_replay("XAUUSD", resolved_dataset),
    ]
    replay_ready_count = sum(1 for row in rows if bool(row.get("replay_ready")))
    closeout_counts: dict[str, int] = {}
    for row in rows:
        key = _to_text(row.get("closeout_preview_state"))
        closeout_counts[key] = closeout_counts.get(key, 0) + 1
    return {
        "summary": {
            "contract_version": "checkpoint_pa8_historical_replay_board_v1",
            "generated_at": _now(),
            "symbol_count": len(rows),
            "replay_ready_count": replay_ready_count,
            "closeout_preview_state_counts": closeout_counts,
            "recommended_next_action": "use_replay_as_supporting_evidence_and_wait_for_live_window",
            "caveat": "historical_replay_does_not_replace_true_post_activation_live_observation",
        },
        "rows": rows,
    }


def render_checkpoint_pa8_historical_replay_board_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines: list[str] = []
    lines.append("# PA8 Historical Replay Board")
    lines.append("")
    for key in ("symbol_count", "replay_ready_count", "closeout_preview_state_counts", "recommended_next_action", "caveat"):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Symbol Rows")
    lines.append("")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        lines.append(f"### {_to_text(row.get('symbol'))}")
        lines.append("")
        for key in (
            "candidate_action",
            "preview_changed_row_count",
            "sample_floor",
            "replay_window_row_count",
            "replay_window_first_generated_at",
            "replay_window_last_generated_at",
            "replay_action_precision",
            "replay_runtime_proxy_match_rate",
            "replay_worsened_rows",
            "replay_ready",
            "closeout_preview_state",
            "recommended_next_action",
        ):
            lines.append(f"- {key}: `{row.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_pa8_historical_replay_outputs(payload: Mapping[str, Any]) -> None:
    body = _mapping(payload)
    json_path = default_checkpoint_pa8_historical_replay_board_json_path()
    markdown_path = default_checkpoint_pa8_historical_replay_board_markdown_path()
    _write_json(json_path, body)
    _write_text(markdown_path, render_checkpoint_pa8_historical_replay_board_markdown(body))
