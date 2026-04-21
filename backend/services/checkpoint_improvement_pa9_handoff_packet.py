from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_PACKET_CONTRACT_VERSION = (
    "checkpoint_improvement_pa9_action_baseline_handoff_packet_v0"
)
DEFAULT_PA9_HANDOFF_SYMBOLS = ("NAS100", "BTCUSD", "XAUUSD")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_checkpoint_improvement_pa9_handoff_packet_json_path() -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_packet_latest.json"
    )


def default_checkpoint_improvement_pa9_handoff_packet_markdown_path() -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_improvement_pa9_action_baseline_handoff_packet_latest.md"
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


def _artifact_path(symbol: str, artifact_name: str) -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / f"checkpoint_pa8_{str(symbol).lower()}_{artifact_name}_latest.json"
    )


def _handoff_apply_artifact_path(symbol: str) -> Path:
    return (
        _repo_root()
        / "data"
        / "analysis"
        / "shadow_auto"
        / f"checkpoint_pa9_{str(symbol).lower()}_action_baseline_handoff_apply_latest.json"
    )


def _build_symbol_row(symbol: str) -> dict[str, Any]:
    activation_apply = _load_json(_artifact_path(symbol, "action_only_canary_activation_apply"))
    closeout = _load_json(_artifact_path(symbol, "action_only_canary_closeout_decision"))
    first_window = _load_json(_artifact_path(symbol, "action_only_canary_first_window_observation"))
    handoff_apply = _load_json(_handoff_apply_artifact_path(symbol))

    activation_summary = _mapping(activation_apply.get("summary"))
    closeout_summary = _mapping(closeout.get("summary"))
    first_window_summary = _mapping(first_window.get("summary"))
    handoff_apply_summary = _mapping(handoff_apply.get("summary"))

    return {
        "symbol": _to_text(symbol).upper(),
        "activation_apply_state": _to_text(activation_summary.get("activation_apply_state")),
        "approval_state": _to_text(activation_summary.get("approval_state")),
        "closeout_state": _to_text(closeout_summary.get("closeout_state")),
        "live_observation_ready": _to_bool(closeout_summary.get("live_observation_ready")),
        "observed_window_row_count": _to_int(closeout_summary.get("observed_window_row_count")),
        "sample_floor": _to_int(closeout_summary.get("sample_floor")),
        "active_trigger_count": _to_int(closeout_summary.get("active_trigger_count")),
        "first_window_status": _to_text(first_window_summary.get("first_window_status")),
        "closeout_recommended_next_action": _to_text(closeout_summary.get("recommended_next_action")),
        "handoff_apply_state": _to_text(handoff_apply_summary.get("apply_state")),
        "handoff_applied_at": _to_text(handoff_apply_summary.get("generated_at")),
        "handoff_apply_recommended_next_action": _to_text(
            handoff_apply_summary.get("recommended_next_action")
        ),
    }


def _handoff_state(rows: list[dict[str, Any]]) -> tuple[str, str]:
    applied_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("handoff_apply_state")).upper() == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
    )
    prepared_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("activation_apply_state")).upper() == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
    )
    ready_closeout_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("closeout_state")).upper() == "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"
    )
    active_canary_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("activation_apply_state")).upper() == "ACTIVE_ACTION_ONLY_CANARY"
    )
    live_window_ready_count = sum(1 for row in rows if _to_bool(row.get("live_observation_ready")))

    if prepared_symbol_count > 0:
        return (
            "READY_FOR_ACTION_BASELINE_HANDOFF_REVIEW",
            "review_prepared_pa9_action_baseline_handoff_packet",
        )
    if ready_closeout_symbol_count > 0:
        return (
            "WAIT_FOR_CLOSEOUT_APPROVAL_APPLICATION",
            "approve_and_apply_pa8_closeout_review_before_pa9_handoff",
        )
    if active_canary_symbol_count > 0 and live_window_ready_count < active_canary_symbol_count:
        return (
            "HOLD_PENDING_PA8_LIVE_WINDOW",
            "wait_for_live_first_window_rows_before_pa9_handoff",
        )
    if active_canary_symbol_count > 0:
        return (
            "HOLD_PENDING_PA8_CLOSEOUT_REVIEW",
            "wait_for_pa8_closeout_review_candidates_before_pa9_handoff",
        )
    if applied_symbol_count > 0:
        return (
            "ACTION_BASELINE_HANDOFF_ALREADY_APPLIED",
            "keep_monitoring_post_handoff_baseline_and_collect_runtime_feedback",
        )
    return (
        "HOLD_NO_ACTIVE_PA8_CANARY",
        "keep_pa9_handoff_scaffold_ready_until_pa8_canaries_prepare_a_symbol",
    )


def build_checkpoint_improvement_pa9_handoff_packet(
    *,
    symbols: Iterable[str] = DEFAULT_PA9_HANDOFF_SYMBOLS,
) -> dict[str, Any]:
    rows = [_build_symbol_row(symbol) for symbol in symbols]
    handoff_state, recommended_next_action = _handoff_state(rows)
    prepared_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("activation_apply_state")).upper() == "PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY"
    )
    ready_closeout_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("closeout_state")).upper() == "READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW"
    )
    active_canary_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("activation_apply_state")).upper() == "ACTIVE_ACTION_ONLY_CANARY"
    )
    live_window_ready_count = sum(1 for row in rows if _to_bool(row.get("live_observation_ready")))
    applied_symbol_count = sum(
        1
        for row in rows
        if _to_text(row.get("handoff_apply_state")).upper() == "PA9_ACTION_BASELINE_HANDOFF_APPLIED"
    )
    return {
        "summary": {
            "contract_version": CHECKPOINT_IMPROVEMENT_PA9_HANDOFF_PACKET_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "handoff_state": handoff_state,
            "recommended_next_action": recommended_next_action,
            "applied_symbol_count": applied_symbol_count,
            "prepared_symbol_count": prepared_symbol_count,
            "ready_closeout_symbol_count": ready_closeout_symbol_count,
            "active_canary_symbol_count": active_canary_symbol_count,
            "live_window_ready_count": live_window_ready_count,
        },
        "rows": rows,
    }


def render_checkpoint_improvement_pa9_handoff_packet_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])

    lines: list[str] = []
    lines.append("# PA9 Action Baseline Handoff Packet")
    lines.append("")
    for key in (
        "handoff_state",
        "recommended_next_action",
        "applied_symbol_count",
        "prepared_symbol_count",
        "ready_closeout_symbol_count",
        "active_canary_symbol_count",
        "live_window_ready_count",
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
            "approval_state",
            "closeout_state",
            "live_observation_ready",
            "observed_window_row_count",
            "sample_floor",
            "active_trigger_count",
            "handoff_apply_state",
            "handoff_applied_at",
            "handoff_apply_recommended_next_action",
            "closeout_recommended_next_action",
        ):
            lines.append(f"- {key}: `{row_map.get(key)}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_improvement_pa9_handoff_packet_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    json_path = Path(json_output_path or default_checkpoint_improvement_pa9_handoff_packet_json_path())
    markdown_path = Path(markdown_output_path or default_checkpoint_improvement_pa9_handoff_packet_markdown_path())
    _write_json(json_path, payload)
    _write_text(markdown_path, render_checkpoint_improvement_pa9_handoff_packet_markdown(payload))
