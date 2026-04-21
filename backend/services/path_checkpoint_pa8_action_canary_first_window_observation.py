from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.path_checkpoint_pa8_action_preview import (
    build_nas100_profit_hold_bias_action_preview,
)


def default_checkpoint_pa8_nas100_action_only_canary_first_window_observation_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_first_window_observation_latest.json"
    )


def default_checkpoint_pa8_nas100_action_only_canary_first_window_observation_markdown_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "analysis"
        / "shadow_auto"
        / "checkpoint_pa8_nas100_action_only_canary_first_window_observation_latest.md"
    )


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


def _slice_post_activation_rows(resolved_dataset: pd.DataFrame | None, activated_at: str) -> pd.DataFrame:
    frame = resolved_dataset.copy() if resolved_dataset is not None and not resolved_dataset.empty else pd.DataFrame()
    if frame.empty or not activated_at:
        return pd.DataFrame()
    if "generated_at" not in frame.columns:
        frame["generated_at"] = ""
    if "symbol" not in frame.columns:
        frame["symbol"] = ""
    times = pd.to_datetime(frame["generated_at"], errors="coerce")
    threshold = pd.to_datetime(activated_at, errors="coerce")
    if pd.isna(threshold):
        return pd.DataFrame()
    return frame.loc[(frame["symbol"].astype(str).str.upper() == "NAS100") & (times >= threshold)].copy()


def build_checkpoint_pa8_nas100_action_only_canary_first_window_observation(
    *,
    activation_apply_payload: Mapping[str, Any] | None,
    preview_payload: Mapping[str, Any] | None,
    resolved_dataset: pd.DataFrame | None = None,
) -> dict[str, Any]:
    activation = _mapping(activation_apply_payload)
    activation_summary = _mapping(activation.get("summary"))
    active_state = _mapping(activation.get("active_state"))
    guardrails = _mapping(active_state.get("guardrails"))
    preview = _mapping(preview_payload)
    preview_summary = _mapping(preview.get("summary"))

    active = bool(activation_summary.get("active")) and _to_text(
        activation_summary.get("activation_apply_state")
    ) == "ACTIVE_ACTION_ONLY_CANARY"
    activated_at = _to_text(active_state.get("activated_at"))
    post_activation_rows = _slice_post_activation_rows(resolved_dataset, activated_at)

    observed_window_row_count = 0
    live_observation_ready = False
    observation_source = "no_active_canary"
    current_hold_precision: float | None = None
    current_runtime_proxy_match_rate: float | None = None
    current_partial_then_hold_quality: float | None = None
    new_worsened_rows = 0

    if active and not post_activation_rows.empty:
        _, live_preview_summary = build_nas100_profit_hold_bias_action_preview(post_activation_rows)
        observation_source = "post_activation_scoped_rows"
        observed_window_row_count = _to_int(live_preview_summary.get("preview_changed_row_count"))
        live_observation_ready = observed_window_row_count > 0
        current_hold_precision = round(_to_float(live_preview_summary.get("preview_hold_precision")), 6)
        current_runtime_proxy_match_rate = round(
            _to_float(live_preview_summary.get("preview_runtime_proxy_match_rate")),
            6,
        )
        current_partial_then_hold_quality = round(
            _to_float(live_preview_summary.get("preview_partial_then_hold_quality")),
            6,
        )
        new_worsened_rows = _to_int(live_preview_summary.get("worsened_row_count"))
    elif active:
        observation_source = "preview_seed_reference"
        current_hold_precision = round(_to_float(preview_summary.get("preview_hold_precision")), 6)
        current_runtime_proxy_match_rate = round(
            _to_float(preview_summary.get("preview_runtime_proxy_match_rate")),
            6,
        )
        current_partial_then_hold_quality = round(
            _to_float(preview_summary.get("preview_partial_then_hold_quality")),
            6,
        )
        new_worsened_rows = _to_int(preview_summary.get("worsened_row_count"))

    baseline_hold_precision = round(_to_float(activation_summary.get("baseline_hold_precision")), 6)
    baseline_runtime_proxy_match_rate = round(
        _to_float(activation_summary.get("baseline_runtime_proxy_match_rate")),
        6,
    )
    baseline_partial_then_hold_quality = round(
        _to_float(activation_summary.get("baseline_partial_then_hold_quality")),
        6,
    )

    active_triggers: list[str] = []
    if current_hold_precision is not None and current_hold_precision < baseline_hold_precision:
        active_triggers.append("hold_precision_drop_below_baseline")
    if (
        current_runtime_proxy_match_rate is not None
        and current_runtime_proxy_match_rate < baseline_runtime_proxy_match_rate
    ):
        active_triggers.append("runtime_proxy_match_rate_drop_below_baseline")
    if (
        current_partial_then_hold_quality is not None
        and bool(guardrails.get("partial_then_hold_quality_must_not_regress"))
        and current_partial_then_hold_quality < baseline_partial_then_hold_quality
    ):
        active_triggers.append("partial_then_hold_quality_regression")
    if new_worsened_rows > _to_int(guardrails.get("worsened_row_count_ceiling"), 0):
        active_triggers.append("new_worsened_rows_detected")

    if not active:
        first_window_status = "HOLD_WINDOW_NOT_ACTIVE"
        recommended_next_action = "approve_and_apply_canary_before_observation"
    elif live_observation_ready:
        first_window_status = "FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE"
        recommended_next_action = "continue_accumulating_live_first_window_rows"
    else:
        first_window_status = "FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS"
        recommended_next_action = "keep_canary_active_and_wait_for_post_activation_rows"

    return {
        "summary": {
            "contract_version": "checkpoint_pa8_action_canary_first_window_observation_v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "symbol": _to_text(activation_summary.get("symbol"), "NAS100"),
            "activation_apply_state": _to_text(activation_summary.get("activation_apply_state")),
            "first_window_status": first_window_status,
            "observation_source": observation_source,
            "live_observation_ready": live_observation_ready,
            "recommended_next_action": recommended_next_action,
            "observed_window_row_count": observed_window_row_count,
            "seed_reference_row_count": _to_int(preview_summary.get("preview_changed_row_count")),
            "baseline_hold_precision": baseline_hold_precision,
            "baseline_runtime_proxy_match_rate": baseline_runtime_proxy_match_rate,
            "baseline_partial_then_hold_quality": baseline_partial_then_hold_quality,
            "current_hold_precision": current_hold_precision,
            "current_runtime_proxy_match_rate": current_runtime_proxy_match_rate,
            "current_partial_then_hold_quality": current_partial_then_hold_quality,
            "new_worsened_rows": new_worsened_rows,
            "active_trigger_count": len(active_triggers),
        },
        "active_triggers": active_triggers,
        "guardrail_snapshot": guardrails,
        "seed_reference": {
            "preview_hold_precision": round(_to_float(preview_summary.get("preview_hold_precision")), 6),
            "preview_runtime_proxy_match_rate": round(
                _to_float(preview_summary.get("preview_runtime_proxy_match_rate")),
                6,
            ),
            "preview_partial_then_hold_quality": round(
                _to_float(preview_summary.get("preview_partial_then_hold_quality")),
                6,
            ),
            "preview_worsened_row_count": _to_int(preview_summary.get("worsened_row_count")),
        },
    }


def render_checkpoint_pa8_nas100_action_only_canary_first_window_observation_markdown(
    payload: Mapping[str, Any] | None,
) -> str:
    body = _mapping(payload)
    summary = _mapping(body.get("summary"))
    active_triggers = list(body.get("active_triggers", []) or [])
    seed_reference = _mapping(body.get("seed_reference"))

    lines: list[str] = []
    lines.append("# PA8 NAS100 Action-Only Canary First Window Observation")
    lines.append("")
    lines.append(f"- first_window_status: `{_to_text(summary.get('first_window_status'))}`")
    lines.append(f"- observation_source: `{_to_text(summary.get('observation_source'))}`")
    lines.append(f"- live_observation_ready: `{summary.get('live_observation_ready', False)}`")
    lines.append(f"- observed_window_row_count: `{_to_int(summary.get('observed_window_row_count'))}`")
    lines.append(f"- seed_reference_row_count: `{_to_int(summary.get('seed_reference_row_count'))}`")
    lines.append(f"- current_hold_precision: `{summary.get('current_hold_precision')}`")
    lines.append(f"- current_runtime_proxy_match_rate: `{summary.get('current_runtime_proxy_match_rate')}`")
    lines.append(f"- current_partial_then_hold_quality: `{summary.get('current_partial_then_hold_quality')}`")
    lines.append(f"- new_worsened_rows: `{_to_int(summary.get('new_worsened_rows'))}`")
    lines.append(f"- recommended_next_action: `{_to_text(summary.get('recommended_next_action'))}`")
    lines.append("")
    lines.append("## Seed Reference")
    lines.append("")
    for key in (
        "preview_hold_precision",
        "preview_runtime_proxy_match_rate",
        "preview_partial_then_hold_quality",
        "preview_worsened_row_count",
    ):
        lines.append(f"- {key}: `{seed_reference.get(key)}`")
    lines.append("")
    lines.append("## Active Triggers")
    lines.append("")
    if active_triggers:
        for item in active_triggers:
            lines.append(f"- `{_to_text(item)}`")
    else:
        lines.append("- `none`")
    return "\n".join(lines).rstrip() + "\n"
