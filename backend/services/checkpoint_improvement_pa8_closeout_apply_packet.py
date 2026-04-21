from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_pa8_closeout_review_packet import (
    default_checkpoint_improvement_pa8_closeout_review_packet_json_path,
)


CHECKPOINT_IMPROVEMENT_PA8_CLOSEOUT_APPLY_PACKET_CONTRACT_VERSION = (
    "checkpoint_improvement_pa8_closeout_apply_packet_v0"
)


def default_checkpoint_improvement_pa8_closeout_apply_packet_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa8_closeout_apply_packet_latest.json"
    )


def default_checkpoint_improvement_pa8_closeout_apply_packet_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa8_closeout_apply_packet_latest.md"
    )


def _to_text(value: object, default: str = "") -> str:
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
        if value in ("", None):
            return int(default)
        return int(value)
    except Exception:
        return int(default)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: str | Path, text: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


def _apply_state(*, review_state: str, review_ready: bool) -> tuple[str, str, bool]:
    normalized_review_state = _to_text(review_state).upper()
    if review_ready:
        return (
            "READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW",
            "approve_and_apply_pa8_closeout_review_when_packet_is_ready",
            True,
        )
    if normalized_review_state == "HOLD_PENDING_PA8_ROLLBACK":
        return (
            "HOLD_PENDING_PA8_ROLLBACK",
            "process_pa8_rollback_candidates_before_closeout_apply",
            False,
        )
    if normalized_review_state == "HOLD_PENDING_PA8_LIVE_WINDOW":
        return (
            "HOLD_PENDING_PA8_LIVE_WINDOW",
            "wait_for_live_first_window_rows_before_pa8_closeout_apply",
            False,
        )
    if normalized_review_state == "HOLD_PENDING_PA8_SAMPLE_FLOOR":
        return (
            "HOLD_PENDING_PA8_SAMPLE_FLOOR",
            "keep_canary_active_until_sample_floor_is_met_before_closeout_apply",
            False,
        )
    return (
        "HOLD_PENDING_PA8_CLOSEOUT_REVIEW",
        "keep_pa8_closeout_apply_scaffold_ready_until_review_candidates_appear",
        False,
    )


def build_checkpoint_improvement_pa8_closeout_apply_packet(
    *,
    review_payload: Mapping[str, Any] | None = None,
    review_json_path: str | Path | None = None,
) -> dict[str, Any]:
    review_map = (
        _mapping(review_payload)
        if review_payload is not None
        else _load_json(review_json_path or default_checkpoint_improvement_pa8_closeout_review_packet_json_path())
    )
    review_summary = _mapping(review_map.get("summary"))
    rows: list[dict[str, Any]] = []
    for row in list(review_map.get("rows", []) or []):
        row_map = _mapping(row)
        apply_candidate = _to_bool(row_map.get("closeout_review_candidate"))
        rows.append({**row_map, "closeout_apply_candidate": apply_candidate})

    review_ready = _to_bool(review_summary.get("review_ready"))
    apply_candidate_symbol_count = sum(1 for row in rows if _to_bool(_mapping(row).get("closeout_apply_candidate")))
    apply_state, recommended_next_action, allow_apply = _apply_state(
        review_state=_to_text(review_summary.get("review_state")),
        review_ready=review_ready,
    )
    return {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_PA8_CLOSEOUT_APPLY_PACKET_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "apply_state": apply_state,
            "recommended_next_action": recommended_next_action,
            "allow_apply": allow_apply,
            "apply_candidate_symbol_count": apply_candidate_symbol_count,
            "review_ready": review_ready,
            "review_state": _to_text(review_summary.get("review_state")),
            "review_candidate_symbol_count": _to_int(review_summary.get("review_candidate_symbol_count")),
            "rollback_required_symbol_count": _to_int(review_summary.get("rollback_required_symbol_count")),
        },
        "rows": rows,
    }


def render_checkpoint_improvement_pa8_closeout_apply_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])

    lines: list[str] = []
    lines.append("# PA8 Closeout Apply Packet")
    lines.append("")
    for key in (
        "apply_state",
        "recommended_next_action",
        "allow_apply",
        "apply_candidate_symbol_count",
        "review_ready",
        "review_state",
        "review_candidate_symbol_count",
        "rollback_required_symbol_count",
    ):
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Symbol Rows")
    lines.append("")
    for row in rows:
        row_map = _mapping(row)
        lines.append(f"### {_to_text(row_map.get('symbol'))}")
        lines.append("")
        for key in (
            "activation_apply_state",
            "closeout_state",
            "live_observation_ready",
            "observed_window_row_count",
            "sample_floor",
            "active_trigger_count",
            "closeout_review_candidate",
            "closeout_apply_candidate",
            "rollback_required",
        ):
            lines.append(f"- {key}: `{row_map.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_improvement_pa8_closeout_apply_packet_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    json_path = Path(
        json_output_path or default_checkpoint_improvement_pa8_closeout_apply_packet_json_path()
    )
    markdown_path = Path(
        markdown_output_path or default_checkpoint_improvement_pa8_closeout_apply_packet_markdown_path()
    )
    _write_json(json_path, payload)
    _write_text(markdown_path, render_checkpoint_improvement_pa8_closeout_apply_packet_markdown(payload))
