from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


CHECKPOINT_IMPROVEMENT_FIRST_SYMBOL_FOCUS_CONTRACT_VERSION = (
    "checkpoint_improvement_first_symbol_focus_runtime_v0"
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_improvement_first_symbol_focus_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "checkpoint_improvement_first_symbol_focus_latest.json",
        directory / "checkpoint_improvement_first_symbol_focus_latest.md",
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _progress_bucket(progress_ratio: float) -> str:
    if progress_ratio >= 1.0:
        return "FULL"
    if progress_ratio >= 0.80:
        return "EIGHTY"
    if progress_ratio >= 0.50:
        return "FIFTY"
    if progress_ratio > 0.0:
        return "EARLY"
    return "ZERO"


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    lines = [
        "# Checkpoint Improvement First Symbol Focus",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "trigger_state",
        "symbol",
        "status",
        "stage",
        "progress_pct",
        "progress_delta_pct",
        "progress_bucket",
        "active_trigger_count",
        "blocking_reason",
        "next_required_action",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    return "\n".join(lines)


def build_checkpoint_improvement_first_symbol_focus_runtime(
    *,
    master_board_payload: Mapping[str, Any] | None,
    now_ts: object | None = None,
    output_json_path: str | Path | None = None,
    output_markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    default_json_path, default_markdown_path = default_checkpoint_improvement_first_symbol_focus_paths()
    json_path = Path(output_json_path or default_json_path)
    markdown_path = Path(output_markdown_path or default_markdown_path)
    previous_payload = _load_json(json_path)
    previous_summary = _mapping(previous_payload.get("summary"))

    board_payload = _mapping(master_board_payload)
    summary = _mapping(board_payload.get("summary"))
    readiness_state = _mapping(board_payload.get("readiness_state"))
    first_symbol_surface = _mapping(readiness_state.get("first_symbol_closeout_handoff_surface"))

    run_at = _text(now_ts, _now_iso())
    if not board_payload or not first_symbol_surface:
        payload = {
            "summary": {
                "contract_version": CHECKPOINT_IMPROVEMENT_FIRST_SYMBOL_FOCUS_CONTRACT_VERSION,
                "generated_at": run_at,
                "trigger_state": "FIRST_SYMBOL_NOT_AVAILABLE",
                "symbol": "",
                "status": "NOT_APPLICABLE",
                "stage": "",
                "progress_pct": 0.0,
                "progress_delta_pct": 0.0,
                "progress_bucket": "ZERO",
                "active_trigger_count": 0,
                "blocking_reason": _text(summary.get("blocking_reason")),
                "next_required_action": _text(summary.get("next_required_action")),
            }
        }
        _write_json(json_path, payload)
        _write_text(markdown_path, _render_markdown(payload))
        return payload

    progress_ratio = _to_float(first_symbol_surface.get("focus_progress_ratio"))
    progress_pct = round(progress_ratio * 100.0, 1)
    previous_progress_pct = _to_float(previous_summary.get("progress_pct"))
    delta_pct = round(progress_pct - previous_progress_pct, 1)
    previous_status = _text(previous_summary.get("status")).upper()
    status = _text(first_symbol_surface.get("observation_status")).upper()
    symbol = _text(first_symbol_surface.get("primary_symbol")).upper()
    previous_bucket = _text(previous_summary.get("progress_bucket")).upper()
    bucket = _progress_bucket(progress_ratio)

    if status != previous_status:
        trigger_state = "FIRST_SYMBOL_STATUS_CHANGED"
    elif bucket != previous_bucket:
        trigger_state = "FIRST_SYMBOL_PROGRESS_BUCKET_CHANGED"
    elif delta_pct > 0.0:
        trigger_state = "FIRST_SYMBOL_PROGRESS_ADVANCED"
    else:
        trigger_state = "FIRST_SYMBOL_PROGRESS_STABLE"

    payload = {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_FIRST_SYMBOL_FOCUS_CONTRACT_VERSION,
            "generated_at": run_at,
            "trigger_state": trigger_state,
            "symbol": symbol,
            "status": status or "NOT_APPLICABLE",
            "stage": _text(first_symbol_surface.get("observation_stage")),
            "progress_pct": progress_pct,
            "progress_delta_pct": delta_pct,
            "progress_bucket": bucket,
            "observed_window_row_count": _to_int(first_symbol_surface.get("observed_window_row_count")),
            "sample_floor": _to_int(first_symbol_surface.get("sample_floor")),
            "active_trigger_count": _to_int(first_symbol_surface.get("active_trigger_count")),
            "blocking_reason": _text(summary.get("blocking_reason")),
            "next_required_action": _text(
                first_symbol_surface.get("recommended_next_action")
                or summary.get("next_required_action")
            ),
            "reason_ko": _text(first_symbol_surface.get("reason_ko")),
        }
    }
    _write_json(json_path, payload)
    _write_text(markdown_path, _render_markdown(payload))
    return payload
