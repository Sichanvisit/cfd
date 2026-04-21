from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.path_checkpoint_pa8_action_canary_closeout_decision import (
    build_checkpoint_pa8_nas100_action_only_canary_closeout_decision,
)
from backend.services.path_checkpoint_pa8_action_canary_first_window_observation import (
    build_checkpoint_pa8_nas100_action_only_canary_first_window_observation,
)
from backend.services.path_checkpoint_pa8_symbol_action_canary import (
    _build_closeout_decision,
    _build_first_window_observation,
    default_checkpoint_pa8_symbol_action_canary_artifact_path,
    render_checkpoint_pa8_symbol_action_canary_markdown,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_pa8_canary_refresh_board_json_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_canary_refresh_board_latest.json"


def default_checkpoint_pa8_canary_refresh_board_markdown_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_canary_refresh_board_latest.md"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        import json

        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_checkpoint_pa8_canary_refresh_resolved_dataset(
    path: str | Path | None = None,
) -> pd.DataFrame:
    file_path = Path(path) if path else _repo_root() / "data" / "datasets" / "path_checkpoint" / "checkpoint_dataset_resolved.csv"
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _build_nas_refresh_row(resolved_dataset: pd.DataFrame | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    activation_apply = _load_json(_repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.json")
    preview = _load_json(_repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json")
    rollback = _load_json(_repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.json")
    first_window = build_checkpoint_pa8_nas100_action_only_canary_first_window_observation(
        activation_apply_payload=activation_apply,
        preview_payload=preview,
        resolved_dataset=resolved_dataset,
    )
    closeout = build_checkpoint_pa8_nas100_action_only_canary_closeout_decision(
        activation_apply_payload=activation_apply,
        first_window_observation_payload=first_window,
        rollback_review_payload=rollback,
    )
    summary = _mapping(first_window.get("summary"))
    closeout_summary = _mapping(closeout.get("summary"))
    row = {
        "symbol": "NAS100",
        "activation_apply_state": _to_text(_mapping(activation_apply.get("summary")).get("activation_apply_state")),
        "first_window_status": _to_text(summary.get("first_window_status")),
        "closeout_state": _to_text(closeout_summary.get("closeout_state")),
        "live_observation_ready": bool(summary.get("live_observation_ready")),
        "observed_window_row_count": _to_int(summary.get("observed_window_row_count")),
        "active_trigger_count": _to_int(summary.get("active_trigger_count")),
        "recommended_next_action": _to_text(closeout_summary.get("recommended_next_action")),
    }
    return row, first_window, closeout


def _build_symbol_refresh_row(symbol: str, resolved_dataset: pd.DataFrame | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    activation_apply = _load_json(default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, "action_only_canary_activation_apply", markdown=False))
    preview = _load_json(default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, "action_only_preview", markdown=False))
    rollback = _load_json(default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, "action_only_canary_rollback_review_packet", markdown=False))
    first_window = _build_first_window_observation(
        activation_apply,
        _mapping(preview.get("summary")),
        resolved_dataset,
    )
    closeout = _build_closeout_decision(activation_apply, first_window, rollback)
    summary = _mapping(first_window.get("summary"))
    closeout_summary = _mapping(closeout.get("summary"))
    row = {
        "symbol": _to_text(symbol).upper(),
        "activation_apply_state": _to_text(_mapping(activation_apply.get("summary")).get("activation_apply_state")),
        "first_window_status": _to_text(summary.get("first_window_status")),
        "closeout_state": _to_text(closeout_summary.get("closeout_state")),
        "live_observation_ready": bool(summary.get("live_observation_ready")),
        "observed_window_row_count": _to_int(summary.get("observed_window_row_count")),
        "active_trigger_count": _to_int(summary.get("active_trigger_count")),
        "recommended_next_action": _to_text(closeout_summary.get("recommended_next_action")),
    }
    return row, first_window, closeout


def build_checkpoint_pa8_canary_refresh_board(resolved_dataset: pd.DataFrame | None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    refreshed_payloads: dict[str, dict[str, dict[str, Any]]] = {}

    nas_row, nas_first_window, nas_closeout = _build_nas_refresh_row(resolved_dataset)
    rows.append(nas_row)
    refreshed_payloads["NAS100"] = {"first_window": nas_first_window, "closeout": nas_closeout}

    for symbol in ("BTCUSD", "XAUUSD"):
        row, first_window, closeout = _build_symbol_refresh_row(symbol, resolved_dataset)
        rows.append(row)
        refreshed_payloads[symbol] = {"first_window": first_window, "closeout": closeout}

    closeout_counts: dict[str, int] = {}
    for row in rows:
        closeout_state = _to_text(row.get("closeout_state"))
        closeout_counts[closeout_state] = closeout_counts.get(closeout_state, 0) + 1

    live_ready_count = sum(1 for row in rows if bool(row.get("live_observation_ready")))
    summary = {
        "contract_version": "checkpoint_pa8_canary_refresh_board_v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "active_symbol_count": len(rows),
        "live_observation_ready_count": live_ready_count,
        "closeout_state_counts": closeout_counts,
        "recommended_next_action": "wait_for_market_reopen_and_refresh_canary_windows" if live_ready_count == 0 else "inspect_live_ready_symbol_windows_first",
    }
    return {"summary": summary, "rows": rows, "refreshed_payloads": refreshed_payloads}


def write_checkpoint_pa8_canary_refresh_outputs(payload: Mapping[str, Any]) -> None:
    body = _mapping(payload)
    refreshed_payloads = body.get("refreshed_payloads")
    if not isinstance(refreshed_payloads, Mapping):
        refreshed_payloads = {}

    nas_payloads = _mapping(refreshed_payloads.get("NAS100"))
    if nas_payloads:
        first_window_json = _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_nas100_action_only_canary_first_window_observation_latest.json"
        first_window_md = first_window_json.with_suffix(".md")
        closeout_json = _repo_root() / "data" / "analysis" / "shadow_auto" / "checkpoint_pa8_nas100_action_only_canary_closeout_decision_latest.json"
        closeout_md = closeout_json.with_suffix(".md")
        from backend.services.path_checkpoint_pa8_action_canary_first_window_observation import (
            render_checkpoint_pa8_nas100_action_only_canary_first_window_observation_markdown,
        )
        from backend.services.path_checkpoint_pa8_action_canary_closeout_decision import (
            render_checkpoint_pa8_nas100_action_only_canary_closeout_decision_markdown,
        )

        _write_json(first_window_json, _mapping(nas_payloads.get("first_window")))
        _write_text(first_window_md, render_checkpoint_pa8_nas100_action_only_canary_first_window_observation_markdown(_mapping(nas_payloads.get("first_window"))))
        _write_json(closeout_json, _mapping(nas_payloads.get("closeout")))
        _write_text(closeout_md, render_checkpoint_pa8_nas100_action_only_canary_closeout_decision_markdown(_mapping(nas_payloads.get("closeout"))))

    for symbol in ("BTCUSD", "XAUUSD"):
        symbol_payloads = _mapping(refreshed_payloads.get(symbol))
        if not symbol_payloads:
            continue
        for artifact_name, key in (("action_only_canary_first_window_observation", "first_window"), ("action_only_canary_closeout_decision", "closeout")):
            json_path = default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, artifact_name, markdown=False)
            md_path = default_checkpoint_pa8_symbol_action_canary_artifact_path(symbol, artifact_name, markdown=True)
            artifact_payload = _mapping(symbol_payloads.get(key))
            _write_json(json_path, artifact_payload)
            render_key = "first_window_observation" if key == "first_window" else "closeout_decision"
            _write_text(md_path, render_checkpoint_pa8_symbol_action_canary_markdown(render_key, artifact_payload))

    board_json = default_checkpoint_pa8_canary_refresh_board_json_path()
    board_md = default_checkpoint_pa8_canary_refresh_board_markdown_path()
    _write_json(board_json, body)
    _write_text(board_md, render_checkpoint_pa8_canary_refresh_board_markdown(body))


def render_checkpoint_pa8_canary_refresh_board_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines: list[str] = []
    lines.append("# PA8 Canary Refresh Board")
    lines.append("")
    for key in ("active_symbol_count", "live_observation_ready_count", "closeout_state_counts", "recommended_next_action"):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Symbol Rows")
    lines.append("")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        lines.append(f"### {_to_text(row.get('symbol'))}")
        lines.append("")
        for key in ("activation_apply_state", "first_window_status", "closeout_state", "live_observation_ready", "observed_window_row_count", "active_trigger_count", "recommended_next_action"):
            lines.append(f"- {key}: `{row.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
