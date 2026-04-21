from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.checkpoint_improvement_pa9_handoff_packet import (
    default_checkpoint_improvement_pa9_handoff_packet_json_path,
)


CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_REVIEW_PACKET_CONTRACT_VERSION = (
    "checkpoint_improvement_pa9_action_baseline_handoff_review_packet_v0"
)


def default_checkpoint_improvement_pa9_handoff_review_packet_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_review_packet_latest.json"
    )


def default_checkpoint_improvement_pa9_handoff_review_packet_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_review_packet_latest.md"
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


def _review_state(
    *,
    applied_symbol_count: int,
    prepared_symbol_count: int,
    ready_closeout_symbol_count: int,
    active_canary_symbol_count: int,
    live_window_ready_count: int,
) -> tuple[str, str, bool]:
    if applied_symbol_count > 0 and prepared_symbol_count == 0:
        return (
            "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
            "keep_monitoring_post_handoff_baseline_and_collect_runtime_feedback",
            False,
        )
    if prepared_symbol_count > 0:
        return (
            "READY_FOR_MANUAL_ACTION_BASELINE_HANDOFF_REVIEW",
            "review_prepared_pa9_action_baseline_handoff_packet",
            True,
        )
    if ready_closeout_symbol_count > 0:
        return (
            "HOLD_PENDING_PA8_CLOSEOUT_APPLICATION",
            "approve_and_apply_pa8_closeout_review_before_pa9_handoff",
            False,
        )
    if active_canary_symbol_count > 0 and live_window_ready_count < active_canary_symbol_count:
        return (
            "HOLD_PENDING_PA8_LIVE_WINDOW",
            "wait_for_live_first_window_rows_before_pa9_handoff_review",
            False,
        )
    if active_canary_symbol_count > 0:
        return (
            "HOLD_PENDING_PA8_CLOSEOUT_REVIEW",
            "wait_for_pa8_closeout_review_candidates_before_pa9_handoff_review",
            False,
        )
    return (
        "HOLD_NO_ACTIVE_PA8_CANARY",
        "keep_pa9_handoff_review_scaffold_ready_until_pa8_prepares_a_symbol",
        False,
    )


def build_checkpoint_improvement_pa9_handoff_review_packet(
    *,
    handoff_payload: Mapping[str, Any] | None = None,
    handoff_json_path: str | Path | None = None,
) -> dict[str, Any]:
    handoff_map = (
        _mapping(handoff_payload)
        if handoff_payload is not None
        else _load_json(handoff_json_path or default_checkpoint_improvement_pa9_handoff_packet_json_path())
    )
    handoff_summary = _mapping(handoff_map.get("summary"))
    rows = []
    for row in list(handoff_map.get("rows", []) or []):
        row_map = _mapping(row)
        prepared_for_handoff = (
            _to_text(row_map.get("activation_apply_state")).upper()
            == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
        )
        already_applied = (
            _to_text(row_map.get("handoff_apply_state")).upper()
            == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
        )
        rows.append(
            {
                **row_map,
                "handoff_review_candidate": prepared_for_handoff and not already_applied,
            }
        )

    applied_symbol_count = _to_int(handoff_summary.get("applied_symbol_count"))
    prepared_symbol_count = _to_int(handoff_summary.get("prepared_symbol_count"))
    ready_closeout_symbol_count = _to_int(handoff_summary.get("ready_closeout_symbol_count"))
    active_canary_symbol_count = _to_int(handoff_summary.get("active_canary_symbol_count"))
    live_window_ready_count = _to_int(handoff_summary.get("live_window_ready_count"))
    review_candidate_symbol_count = sum(
        1 for row in rows if _to_bool(_mapping(row).get("handoff_review_candidate"))
    )
    review_state, recommended_next_action, review_ready = _review_state(
        applied_symbol_count=applied_symbol_count,
        prepared_symbol_count=prepared_symbol_count,
        ready_closeout_symbol_count=ready_closeout_symbol_count,
        active_canary_symbol_count=active_canary_symbol_count,
        live_window_ready_count=live_window_ready_count,
    )

    return {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_REVIEW_PACKET_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "review_state": review_state,
            "recommended_next_action": recommended_next_action,
            "review_ready": review_ready,
            "review_candidate_symbol_count": review_candidate_symbol_count,
            "applied_symbol_count": applied_symbol_count,
            "prepared_symbol_count": prepared_symbol_count,
            "ready_closeout_symbol_count": ready_closeout_symbol_count,
            "active_canary_symbol_count": active_canary_symbol_count,
            "live_window_ready_count": live_window_ready_count,
            "handoff_state": _to_text(handoff_summary.get("handoff_state")),
        },
        "rows": rows,
    }


def render_checkpoint_improvement_pa9_handoff_review_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])

    lines: list[str] = []
    lines.append("# PA9 Action Baseline Handoff Review Packet")
    lines.append("")
    for key in (
        "review_state",
        "recommended_next_action",
        "review_ready",
        "review_candidate_symbol_count",
        "applied_symbol_count",
        "prepared_symbol_count",
        "ready_closeout_symbol_count",
        "active_canary_symbol_count",
        "live_window_ready_count",
        "handoff_state",
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
            "handoff_review_candidate",
            "handoff_apply_state",
            "closeout_recommended_next_action",
        ):
            lines.append(f"- {key}: `{row_map.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_improvement_pa9_handoff_review_packet_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    json_path = Path(
        json_output_path or default_checkpoint_improvement_pa9_handoff_review_packet_json_path()
    )
    markdown_path = Path(
        markdown_output_path
        or default_checkpoint_improvement_pa9_handoff_review_packet_markdown_path()
    )
    _write_json(json_path, payload)
    _write_text(
        markdown_path,
        render_checkpoint_improvement_pa9_handoff_review_packet_markdown(payload),
    )
