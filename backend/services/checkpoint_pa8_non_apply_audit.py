from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.services.path_checkpoint_pa8_canary_refresh import (
    default_checkpoint_pa8_canary_refresh_board_json_path,
)


CHECKPOINT_PA8_NON_APPLY_AUDIT_CONTRACT_VERSION = "checkpoint_pa8_non_apply_audit_v1"

PA8_REASON_LABELS_KO = {
    "canary_not_active": "canary가 아직 활성 상태가 아님",
    "no_post_activation_live_rows": "활성화 이후 live row가 아직 쌓이지 않음",
    "live_rows_below_sample_floor": "live row가 sample floor에 아직 못 미침",
    "guardrail_trigger_active": "guardrail trigger가 살아 있어 closeout 검토를 미룸",
    "live_observation_not_ready": "live observation이 아직 ready 상태가 아님",
    "closeout_review_not_reached": "closeout review 단계까지 아직 도달하지 않음",
}

PA8_TRIGGER_LABELS_KO = {
    "hold_precision_drop_below_baseline": "hold 정밀도가 baseline 아래로 내려감",
    "runtime_proxy_match_rate_drop_below_baseline": "runtime proxy match rate가 baseline 아래로 내려감",
    "partial_then_hold_quality_regression": "partial-then-hold 품질이 baseline보다 나빠짐",
    "new_worsened_rows_detected": "새 worsened row가 감지됨",
    "candidate_action_precision_drop_below_floor": "candidate action precision이 floor 아래에 머묾",
}


def _shadow_auto_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "analysis" / "shadow_auto"


def default_checkpoint_pa8_non_apply_audit_json_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_non_apply_audit_latest.json"


def default_checkpoint_pa8_non_apply_audit_markdown_path() -> Path:
    return _shadow_auto_dir() / "checkpoint_pa8_non_apply_audit_latest.md"


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


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


def _trigger_label(trigger_code: str) -> str:
    return PA8_TRIGGER_LABELS_KO.get(trigger_code, trigger_code)


def _reason_label(reason_code: str) -> str:
    return PA8_REASON_LABELS_KO.get(reason_code, reason_code)


def _build_blocker_codes(
    *,
    activation_apply_state: str,
    live_observation_ready: bool,
    observed_window_row_count: int,
    sample_floor: int,
    active_trigger_count: int,
) -> list[str]:
    blockers: list[str] = []
    if activation_apply_state != "ACTIVE_ACTION_ONLY_CANARY":
        blockers.append("canary_not_active")
    if observed_window_row_count <= 0:
        blockers.append("no_post_activation_live_rows")
    elif sample_floor > 0 and observed_window_row_count < sample_floor:
        blockers.append("live_rows_below_sample_floor")
    if active_trigger_count > 0:
        blockers.append("guardrail_trigger_active")
    if not live_observation_ready:
        blockers.append("live_observation_not_ready")
    if not blockers:
        blockers.append("closeout_review_not_reached")
    return blockers


def _primary_reason(blocker_codes: list[str]) -> str:
    for reason_code in (
        "canary_not_active",
        "no_post_activation_live_rows",
        "live_rows_below_sample_floor",
        "guardrail_trigger_active",
        "live_observation_not_ready",
    ):
        if reason_code in blocker_codes:
            return reason_code
    return "closeout_review_not_reached"


def build_checkpoint_pa8_non_apply_audit(
    *,
    board_payload: Mapping[str, Any] | None = None,
    board_json_path: str | Path | None = None,
) -> dict[str, Any]:
    board = (
        _mapping(board_payload)
        if board_payload is not None
        else _load_json(board_json_path or default_checkpoint_pa8_canary_refresh_board_json_path())
    )
    summary = _mapping(board.get("summary"))
    refreshed_payloads = _mapping(board.get("refreshed_payloads"))
    rows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    trigger_counts: Counter[str] = Counter()

    for raw_row in list(board.get("rows", []) or []):
        row = _mapping(raw_row)
        symbol = _text(row.get("symbol")).upper()
        payload_bundle = _mapping(refreshed_payloads.get(symbol))
        first_window_summary = _mapping(_mapping(payload_bundle.get("first_window")).get("summary"))
        closeout_summary = _mapping(_mapping(payload_bundle.get("closeout")).get("summary"))
        active_triggers = list(_mapping(payload_bundle.get("closeout")).get("active_triggers", []) or [])
        if not active_triggers:
            active_triggers = list(_mapping(payload_bundle.get("first_window")).get("active_triggers", []) or [])

        activation_apply_state = _text(
            closeout_summary.get("activation_apply_state") or row.get("activation_apply_state")
        )
        live_observation_ready = _to_bool(
            closeout_summary.get("live_observation_ready")
            if "live_observation_ready" in closeout_summary
            else row.get("live_observation_ready")
        )
        observed_window_row_count = _to_int(
            closeout_summary.get("observed_window_row_count")
            if "observed_window_row_count" in closeout_summary
            else row.get("observed_window_row_count")
        )
        sample_floor = _to_int(closeout_summary.get("sample_floor"))
        active_trigger_count = _to_int(
            closeout_summary.get("active_trigger_count")
            if "active_trigger_count" in closeout_summary
            else row.get("active_trigger_count")
        )
        seed_reference_row_count = _to_int(first_window_summary.get("seed_reference_row_count"))
        blocker_codes = _build_blocker_codes(
            activation_apply_state=activation_apply_state,
            live_observation_ready=live_observation_ready,
            observed_window_row_count=observed_window_row_count,
            sample_floor=sample_floor,
            active_trigger_count=active_trigger_count,
        )
        primary_reason_code = _primary_reason(blocker_codes)
        progress_pct = round(
            (float(observed_window_row_count) / float(max(1, sample_floor))) * 100.0,
            1,
        )

        audit_row = {
            "symbol": symbol,
            "activation_apply_state": activation_apply_state,
            "first_window_status": _text(
                first_window_summary.get("first_window_status") or row.get("first_window_status")
            ),
            "closeout_state": _text(
                closeout_summary.get("closeout_state") or row.get("closeout_state")
            ),
            "live_observation_ready": live_observation_ready,
            "observed_window_row_count": observed_window_row_count,
            "seed_reference_row_count": seed_reference_row_count,
            "sample_floor": sample_floor,
            "progress_pct": progress_pct,
            "active_trigger_count": active_trigger_count,
            "active_triggers": active_triggers,
            "active_trigger_labels_ko": [_trigger_label(_text(code)) for code in active_triggers],
            "primary_non_apply_reason_code": primary_reason_code,
            "primary_non_apply_reason_ko": _reason_label(primary_reason_code),
            "blocker_codes": blocker_codes,
            "blocker_labels_ko": [_reason_label(code) for code in blocker_codes],
            "recommended_next_action": _text(
                closeout_summary.get("recommended_next_action")
                or first_window_summary.get("recommended_next_action")
                or row.get("recommended_next_action")
            ),
        }
        rows.append(audit_row)
        reason_counts[primary_reason_code] += 1
        for trigger_code in active_triggers:
            trigger_counts[_text(trigger_code)] += 1

    dominant_reason_code = ""
    if reason_counts:
        dominant_reason_code = sorted(
            reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]

    recommended_next_action = _text(summary.get("recommended_next_action"))
    if dominant_reason_code == "no_post_activation_live_rows":
        recommended_next_action = "keep_canary_active_and_wait_for_post_activation_rows"
    elif dominant_reason_code == "live_rows_below_sample_floor":
        recommended_next_action = "continue_accumulating_post_activation_live_rows_until_sample_floor"
    elif dominant_reason_code == "guardrail_trigger_active":
        recommended_next_action = "inspect_guardrail_regression_before_pa8_closeout_review"
    elif dominant_reason_code == "canary_not_active":
        recommended_next_action = "reactivate_action_only_canary_before_closeout_review"

    return {
        "summary": {
            "contract_version": CHECKPOINT_PA8_NON_APPLY_AUDIT_CONTRACT_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
            "board_generated_at": _text(summary.get("generated_at")),
            "active_symbol_count": len(rows),
            "live_observation_ready_count": sum(1 for row in rows if bool(row.get("live_observation_ready"))),
            "non_apply_symbol_count": sum(
                1 for row in rows if _text(row.get("primary_non_apply_reason_code")) != "closeout_review_not_reached"
            ),
            "dominant_non_apply_reason_code": dominant_reason_code,
            "dominant_non_apply_reason_ko": _reason_label(dominant_reason_code) if dominant_reason_code else "",
            "recommended_next_action": recommended_next_action,
            "reason_counts": dict(reason_counts),
            "trigger_counts": dict(trigger_counts),
        },
        "rows": rows,
    }


def render_checkpoint_pa8_non_apply_audit_markdown(payload: Mapping[str, Any] | None) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    rows = list(body.get("rows", []) or [])
    lines = [
        "# PA8 Non-Apply Audit",
        "",
        f"- generated_at: `{_text(summary.get('generated_at'))}`",
        f"- active_symbol_count: `{_to_int(summary.get('active_symbol_count'))}`",
        f"- live_observation_ready_count: `{_to_int(summary.get('live_observation_ready_count'))}`",
        f"- dominant_non_apply_reason: `{_text(summary.get('dominant_non_apply_reason_ko'))}`",
        f"- recommended_next_action: `{_text(summary.get('recommended_next_action'))}`",
        "",
        "## Symbol Rows",
        "",
    ]
    for raw_row in rows:
        row = _mapping(raw_row)
        lines.extend(
            [
                f"### {_text(row.get('symbol'), '-')}",
                "",
                f"- primary_non_apply_reason: `{_text(row.get('primary_non_apply_reason_ko'))}`",
                f"- first_window_status: `{_text(row.get('first_window_status'))}`",
                f"- closeout_state: `{_text(row.get('closeout_state'))}`",
                f"- live_observation_ready: `{bool(row.get('live_observation_ready'))}`",
                f"- observed_window_row_count: `{_to_int(row.get('observed_window_row_count'))}`",
                f"- seed_reference_row_count: `{_to_int(row.get('seed_reference_row_count'))}`",
                f"- sample_floor: `{_to_int(row.get('sample_floor'))}`",
                f"- progress_pct: `{row.get('progress_pct')}`",
                f"- active_trigger_count: `{_to_int(row.get('active_trigger_count'))}`",
                f"- active_trigger_labels_ko: `{', '.join(list(row.get('active_trigger_labels_ko', []) or [])) or 'none'}`",
                f"- recommended_next_action: `{_text(row.get('recommended_next_action'))}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_checkpoint_pa8_non_apply_audit_outputs(
    payload: Mapping[str, Any],
    *,
    json_output_path: str | Path | None = None,
    markdown_output_path: str | Path | None = None,
) -> None:
    _write_json(
        json_output_path or default_checkpoint_pa8_non_apply_audit_json_path(),
        payload,
    )
    _write_text(
        markdown_output_path or default_checkpoint_pa8_non_apply_audit_markdown_path(),
        render_checkpoint_pa8_non_apply_audit_markdown(payload),
    )
