"""Validate current XAU DOWN bootstrap directional state-machine materialization."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.countertrend_materialization_check import (
    DEFAULT_COUNTERTREND_SYMBOL,
    DEFAULT_TARGET_SETUP_IDS,
    DEFAULT_TARGET_SETUP_REASON_TOKENS,
)
from backend.services.trade_csv_schema import now_kst_dt


COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_CONTRACT_VERSION = "countertrend_down_bootstrap_validation_v1"

REQUIRED_DOWN_BOOTSTRAP_FIELDS = (
    "countertrend_anti_long_score",
    "countertrend_anti_short_score",
    "countertrend_pro_up_score",
    "countertrend_pro_down_score",
    "countertrend_directional_bias",
    "countertrend_action_state",
    "countertrend_directional_candidate_action",
    "countertrend_directional_execution_action",
    "countertrend_directional_state_reason",
    "countertrend_directional_state_rank",
    "countertrend_directional_owner_family",
    "countertrend_directional_down_bias_score",
    "countertrend_directional_up_bias_score",
)

COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_COLUMNS = [
    "observation_event_id",
    "generated_at",
    "runtime_updated_at",
    "scope_bucket",
    "symbol",
    "time",
    "action",
    "outcome",
    "setup_id",
    "setup_reason",
    "blocked_by",
    "action_none_reason",
    "target_family_match",
    "countertrend_directional_bias",
    "countertrend_action_state",
    "countertrend_directional_candidate_action",
    "countertrend_directional_execution_action",
    "countertrend_directional_state_reason",
    "countertrend_directional_state_rank",
    "countertrend_anti_long_score",
    "countertrend_pro_down_score",
    "countertrend_directional_down_bias_score",
    "countertrend_directional_up_bias_score",
    "countertrend_continuation_reason_summary",
    "validation_note",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass
    try:
        if value in ("", None):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _to_bool(value: object) -> bool:
    return _to_text(value).lower() in {"1", "true", "yes", "y"}


def _series_counts(values: pd.Series) -> dict[str, int]:
    if values.empty:
        return {}
    series = values.fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    return {str(key): int(value) for key, value in series.value_counts().to_dict().items()}


def _json_counts(counts: Mapping[str, int]) -> str:
    return json.dumps({str(k): int(v) for k, v in counts.items()}, ensure_ascii=False, sort_keys=True) if counts else "{}"


def _target_family_mask(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=bool)
    setup_ids = frame.get("setup_id", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip().str.lower()
    setup_reasons = frame.get("setup_reason", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip().str.lower()
    action_series = frame.get("action", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip().str.upper()
    id_match = setup_ids.isin({value.lower() for value in DEFAULT_TARGET_SETUP_IDS})
    reason_match = pd.Series(False, index=frame.index)
    for token in DEFAULT_TARGET_SETUP_REASON_TOKENS:
        reason_match = reason_match | setup_reasons.str.contains(token.lower(), regex=False)
    buy_match = action_series.eq("BUY")
    return (id_match | reason_match) & buy_match


def _recommended_next_action(
    *,
    field_presence_ok: bool,
    symbol_row_count: int,
    target_family_row_count: int,
    non_target_leak_row_count: int,
    invalid_state_mismatch_count: int,
    enter_reserved_violation_count: int,
    down_watch_count: int,
    down_probe_count: int,
) -> str:
    if not field_presence_ok:
        return "repair_directional_runtime_schema_or_restart_core"
    if symbol_row_count <= 0:
        return "await_fresh_xau_rows"
    if target_family_row_count <= 0:
        return "await_fresh_xau_lower_reversal_rows"
    if non_target_leak_row_count > 0:
        return "inspect_directional_scope_leak"
    if enter_reserved_violation_count > 0:
        return "inspect_directional_state_machine_enter_gate"
    if invalid_state_mismatch_count > 0:
        return "inspect_directional_bridge_state_mapping"
    if (down_watch_count + down_probe_count) <= 0:
        return "inspect_down_bootstrap_state_thresholds"
    return "proceed_to_mf7e_up_symmetry_extension"


def build_countertrend_down_bootstrap_validation(
    runtime_status: Mapping[str, Any] | None,
    entry_decisions: pd.DataFrame | None,
    *,
    symbol: str = DEFAULT_COUNTERTREND_SYMBOL,
    recent_limit: int = 240,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    generated_at = now_kst_dt().isoformat()
    runtime = dict(runtime_status or {})
    semantic_live_config = dict(runtime.get("semantic_live_config", {}) or {})
    frame = entry_decisions.copy() if entry_decisions is not None and not entry_decisions.empty else pd.DataFrame()

    summary: dict[str, Any] = {
        "contract_version": COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "symbol": symbol,
        "recent_row_count": 0,
        "symbol_row_count": 0,
        "target_family_row_count": 0,
        "field_presence_ok": False,
        "field_presence_missing": list(REQUIRED_DOWN_BOOTSTRAP_FIELDS),
        "directional_state_counts": "{}",
        "directional_bias_counts": "{}",
        "candidate_action_counts": "{}",
        "execution_action_counts": "{}",
        "state_reason_counts": "{}",
        "down_watch_count": 0,
        "down_probe_count": 0,
        "down_enter_count": 0,
        "do_nothing_count": 0,
        "candidate_sell_count": 0,
        "execution_sell_count": 0,
        "invalid_state_mismatch_count": 0,
        "enter_reserved_violation_count": 0,
        "non_target_leak_row_count": 0,
        "recommended_next_action": "repair_directional_runtime_schema_or_restart_core",
    }
    if frame.empty:
        return pd.DataFrame(columns=COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_COLUMNS), summary

    decisions = frame.copy()
    for column in (
        "time",
        "symbol",
        "action",
        "outcome",
        "setup_id",
        "setup_reason",
        "blocked_by",
        "action_none_reason",
        "countertrend_directional_bias",
        "countertrend_action_state",
        "countertrend_directional_candidate_action",
        "countertrend_directional_execution_action",
        "countertrend_directional_state_reason",
        "countertrend_directional_state_rank",
        "countertrend_anti_long_score",
        "countertrend_pro_down_score",
        "countertrend_directional_down_bias_score",
        "countertrend_directional_up_bias_score",
        "countertrend_continuation_reason_summary",
    ):
        if column not in decisions.columns:
            decisions[column] = ""

    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(recent))

    required_missing = [field for field in REQUIRED_DOWN_BOOTSTRAP_FIELDS if field not in recent.columns]
    field_presence_ok = len(required_missing) == 0
    summary["field_presence_ok"] = bool(field_presence_ok)
    summary["field_presence_missing"] = required_missing

    symbol_frame = recent.loc[recent["symbol"].fillna("").astype(str).str.upper() == symbol.upper()].copy()
    summary["symbol_row_count"] = int(len(symbol_frame))

    if symbol_frame.empty:
        summary["recommended_next_action"] = _recommended_next_action(
            field_presence_ok=field_presence_ok,
            symbol_row_count=0,
            target_family_row_count=0,
            non_target_leak_row_count=0,
            invalid_state_mismatch_count=0,
            enter_reserved_violation_count=0,
            down_watch_count=0,
            down_probe_count=0,
        )
        return pd.DataFrame(columns=COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_COLUMNS), summary

    symbol_frame["target_family_match"] = _target_family_mask(symbol_frame)
    target_frame = symbol_frame.loc[symbol_frame["target_family_match"]].copy()
    other_frame = recent.loc[~recent.index.isin(target_frame.index)].copy()

    def _directional_state(row: Mapping[str, Any]) -> str:
        return _to_text(row.get("countertrend_action_state")).upper()

    def _candidate_action(row: Mapping[str, Any]) -> str:
        return _to_text(row.get("countertrend_directional_candidate_action")).upper()

    def _execution_action(row: Mapping[str, Any]) -> str:
        return _to_text(row.get("countertrend_directional_execution_action")).upper()

    invalid_state_mismatch_count = 0
    enter_reserved_violation_count = 0
    for _, row in target_frame.iterrows():
        state = _directional_state(row)
        candidate_action = _candidate_action(row)
        execution_action = _execution_action(row)
        if state == "DOWN_WATCH" and candidate_action:
            invalid_state_mismatch_count += 1
        elif state == "DOWN_PROBE" and candidate_action != "SELL":
            invalid_state_mismatch_count += 1
        elif state == "DOWN_ENTER" and execution_action != "SELL":
            invalid_state_mismatch_count += 1
        elif state == "DO_NOTHING" and (candidate_action or execution_action):
            invalid_state_mismatch_count += 1
        if state == "DOWN_ENTER":
            enter_reserved_violation_count += 1

    non_target_leak_frame = other_frame.loc[
        other_frame["countertrend_action_state"].fillna("").astype(str).str.strip().str.upper().isin(
            {"DOWN_WATCH", "DOWN_PROBE", "DOWN_ENTER"}
        )
        | other_frame["countertrend_directional_candidate_action"].fillna("").astype(str).str.strip().str.upper().eq("SELL")
    ].copy()

    state_counts = _series_counts(target_frame["countertrend_action_state"]) if not target_frame.empty else {}
    bias_counts = _series_counts(target_frame["countertrend_directional_bias"]) if not target_frame.empty else {}
    candidate_action_counts = (
        _series_counts(target_frame["countertrend_directional_candidate_action"]) if not target_frame.empty else {}
    )
    execution_action_counts = (
        _series_counts(target_frame["countertrend_directional_execution_action"]) if not target_frame.empty else {}
    )
    state_reason_counts = (
        _series_counts(target_frame["countertrend_directional_state_reason"]) if not target_frame.empty else {}
    )

    summary["target_family_row_count"] = int(len(target_frame))
    summary["directional_state_counts"] = _json_counts(state_counts)
    summary["directional_bias_counts"] = _json_counts(bias_counts)
    summary["candidate_action_counts"] = _json_counts(candidate_action_counts)
    summary["execution_action_counts"] = _json_counts(execution_action_counts)
    summary["state_reason_counts"] = _json_counts(state_reason_counts)
    summary["down_watch_count"] = int(state_counts.get("DOWN_WATCH", 0))
    summary["down_probe_count"] = int(state_counts.get("DOWN_PROBE", 0))
    summary["down_enter_count"] = int(state_counts.get("DOWN_ENTER", 0))
    summary["do_nothing_count"] = int(state_counts.get("DO_NOTHING", 0))
    summary["candidate_sell_count"] = int(candidate_action_counts.get("SELL", 0))
    summary["execution_sell_count"] = int(execution_action_counts.get("SELL", 0))
    summary["invalid_state_mismatch_count"] = int(invalid_state_mismatch_count)
    summary["enter_reserved_violation_count"] = int(enter_reserved_violation_count)
    summary["non_target_leak_row_count"] = int(len(non_target_leak_frame))
    summary["recommended_next_action"] = _recommended_next_action(
        field_presence_ok=field_presence_ok,
        symbol_row_count=int(len(symbol_frame)),
        target_family_row_count=int(len(target_frame)),
        non_target_leak_row_count=int(len(non_target_leak_frame)),
        invalid_state_mismatch_count=int(invalid_state_mismatch_count),
        enter_reserved_violation_count=int(enter_reserved_violation_count),
        down_watch_count=int(state_counts.get("DOWN_WATCH", 0)),
        down_probe_count=int(state_counts.get("DOWN_PROBE", 0)),
    )

    rows: list[dict[str, Any]] = []

    def _append_rows(source_frame: pd.DataFrame, scope_bucket: str) -> None:
        for _, row in source_frame.iterrows():
            state = _directional_state(row)
            candidate_action = _candidate_action(row)
            execution_action = _execution_action(row)
            note_parts: list[str] = []
            if bool(row.get("target_family_match", False)):
                note_parts.append("target_family")
            else:
                note_parts.append("non_target_scope")
            if state:
                note_parts.append(state.lower())
            if state == "DOWN_WATCH" and not candidate_action:
                note_parts.append("watch_ok")
            if state == "DOWN_PROBE" and candidate_action == "SELL":
                note_parts.append("probe_candidate_ok")
            if state == "DOWN_ENTER":
                note_parts.append("enter_reserved_violation")
            rows.append(
                {
                    "observation_event_id": (
                        f"{COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_CONTRACT_VERSION}:"
                        f"{scope_bucket}:{_to_text(row.get('time')).replace(':', '').replace('-', '')}"
                    ),
                    "generated_at": generated_at,
                    "runtime_updated_at": _to_text(runtime.get("updated_at")),
                    "scope_bucket": scope_bucket,
                    "symbol": _to_text(row.get("symbol")).upper(),
                    "time": _to_text(row.get("time")),
                    "action": _to_text(row.get("action")).upper(),
                    "outcome": _to_text(row.get("outcome")),
                    "setup_id": _to_text(row.get("setup_id")),
                    "setup_reason": _to_text(row.get("setup_reason")),
                    "blocked_by": _to_text(row.get("blocked_by")),
                    "action_none_reason": _to_text(row.get("action_none_reason")),
                    "target_family_match": bool(row.get("target_family_match", False)),
                    "countertrend_directional_bias": _to_text(row.get("countertrend_directional_bias")).upper(),
                    "countertrend_action_state": state,
                    "countertrend_directional_candidate_action": candidate_action,
                    "countertrend_directional_execution_action": execution_action,
                    "countertrend_directional_state_reason": _to_text(
                        row.get("countertrend_directional_state_reason")
                    ),
                    "countertrend_directional_state_rank": int(
                        _to_float(row.get("countertrend_directional_state_rank"), 0.0)
                    ),
                    "countertrend_anti_long_score": round(
                        _to_float(row.get("countertrend_anti_long_score")),
                        6,
                    ),
                    "countertrend_pro_down_score": round(
                        _to_float(row.get("countertrend_pro_down_score")),
                        6,
                    ),
                    "countertrend_directional_down_bias_score": round(
                        _to_float(row.get("countertrend_directional_down_bias_score")),
                        6,
                    ),
                    "countertrend_directional_up_bias_score": round(
                        _to_float(row.get("countertrend_directional_up_bias_score")),
                        6,
                    ),
                    "countertrend_continuation_reason_summary": _to_text(
                        row.get("countertrend_continuation_reason_summary")
                    ),
                    "validation_note": "|".join(note_parts),
                }
            )

    _append_rows(symbol_frame, "fresh_symbol_slice")
    if not non_target_leak_frame.empty:
        non_target_leak_frame["target_family_match"] = False
        _append_rows(non_target_leak_frame, "non_target_leak")

    return pd.DataFrame(rows, columns=COUNTERTREND_DOWN_BOOTSTRAP_VALIDATION_COLUMNS), summary


def render_countertrend_down_bootstrap_validation_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    payload = dict(summary or {})
    rows = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    lines = [
        "# Countertrend DOWN Bootstrap Validation",
        "",
        f"- generated_at: `{_to_text(payload.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(payload.get('runtime_updated_at'))}`",
        f"- rollout_mode: `{_to_text(payload.get('rollout_mode'))}`",
        f"- symbol: `{_to_text(payload.get('symbol'))}`",
        f"- recent_row_count: `{int(payload.get('recent_row_count') or 0)}`",
        f"- symbol_row_count: `{int(payload.get('symbol_row_count') or 0)}`",
        f"- target_family_row_count: `{int(payload.get('target_family_row_count') or 0)}`",
        f"- down_watch_count: `{int(payload.get('down_watch_count') or 0)}`",
        f"- down_probe_count: `{int(payload.get('down_probe_count') or 0)}`",
        f"- down_enter_count: `{int(payload.get('down_enter_count') or 0)}`",
        f"- candidate_sell_count: `{int(payload.get('candidate_sell_count') or 0)}`",
        f"- execution_sell_count: `{int(payload.get('execution_sell_count') or 0)}`",
        f"- invalid_state_mismatch_count: `{int(payload.get('invalid_state_mismatch_count') or 0)}`",
        f"- enter_reserved_violation_count: `{int(payload.get('enter_reserved_violation_count') or 0)}`",
        f"- non_target_leak_row_count: `{int(payload.get('non_target_leak_row_count') or 0)}`",
        f"- field_presence_ok: `{bool(payload.get('field_presence_ok'))}`",
        f"- recommended_next_action: `{_to_text(payload.get('recommended_next_action'))}`",
        "",
        "## State Counts",
        "",
        f"- directional_state_counts: `{_to_text(payload.get('directional_state_counts'), '{}')}`",
        f"- directional_bias_counts: `{_to_text(payload.get('directional_bias_counts'), '{}')}`",
        f"- candidate_action_counts: `{_to_text(payload.get('candidate_action_counts'), '{}')}`",
        f"- execution_action_counts: `{_to_text(payload.get('execution_action_counts'), '{}')}`",
        f"- state_reason_counts: `{_to_text(payload.get('state_reason_counts'), '{}')}`",
    ]
    if rows.empty:
        lines.extend(["", "## Recent Rows", "", "- no rows materialized"])
        return "\n".join(lines) + "\n"

    lines.extend(["", "## Recent Rows", ""])
    for _, row in rows.head(12).iterrows():
        lines.append(
            "- "
            + f"{_to_text(row.get('time'))} | `{_to_text(row.get('symbol'))}` | "
            + f"`{_to_text(row.get('setup_id'))}` | "
            + f"state={_to_text(row.get('countertrend_action_state')) or 'NONE'} | "
            + f"candidate={_to_text(row.get('countertrend_directional_candidate_action')) or 'NONE'} | "
            + f"exec={_to_text(row.get('countertrend_directional_execution_action')) or 'NONE'} | "
            + f"note={_to_text(row.get('validation_note'))}"
        )
    return "\n".join(lines) + "\n"
