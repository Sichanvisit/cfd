"""Audit fresh runtime materialization for countertrend continuation fields."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


COUNTERTREND_MATERIALIZATION_CHECK_CONTRACT_VERSION = "countertrend_materialization_check_v1"
DEFAULT_COUNTERTREND_SYMBOL = "XAUUSD"
DEFAULT_TARGET_SETUP_IDS = ("range_lower_reversal_buy", "trend_pullback_buy")
DEFAULT_TARGET_SETUP_REASON_TOKENS = (
    "shadow_lower_rebound",
    "shadow_outer_band_reversal_support_required_observe",
)
REQUIRED_COUNTERTREND_FIELDS = (
    "countertrend_continuation_enabled",
    "countertrend_continuation_state",
    "countertrend_continuation_action",
    "countertrend_continuation_confidence",
    "countertrend_candidate_action",
    "countertrend_candidate_confidence",
)

COUNTERTREND_MATERIALIZATION_CHECK_COLUMNS = [
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
    "countertrend_continuation_enabled",
    "countertrend_continuation_state",
    "countertrend_continuation_action",
    "countertrend_continuation_confidence",
    "countertrend_continuation_reason_summary",
    "countertrend_candidate_action",
    "countertrend_candidate_confidence",
    "countertrend_candidate_reason",
    "entry_candidate_bridge_source",
    "entry_candidate_bridge_action",
    "entry_candidate_surface_family",
    "entry_candidate_surface_state",
    "materialization_note",
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
    text = _to_text(value).lower()
    return text in {"1", "true", "yes", "y"}


def _series_counts(values: pd.Series) -> dict[str, int]:
    if values.empty:
        return {}
    series = values.fillna("").astype(str).str.strip().replace("", pd.NA).dropna()
    counts = series.value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


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
    enabled_count: int,
    candidate_sell_count: int,
    leak_row_count: int,
) -> str:
    if not field_presence_ok:
        return "repair_countertrend_runtime_schema_or_restart_core"
    if symbol_row_count <= 0:
        return "await_fresh_xau_rows"
    if target_family_row_count <= 0:
        return "await_fresh_xau_lower_reversal_rows"
    if leak_row_count > 0:
        return "inspect_countertrend_scope_leak"
    if enabled_count <= 0:
        return "inspect_countertrend_warning_overlap_thresholds"
    if candidate_sell_count <= 0:
        return "inspect_countertrend_bridge_mapping"
    return "proceed_to_mf7b_directional_evidence_split"


def build_countertrend_materialization_check(
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
        "contract_version": COUNTERTREND_MATERIALIZATION_CHECK_CONTRACT_VERSION,
        "generated_at": generated_at,
        "runtime_updated_at": _to_text(runtime.get("updated_at")),
        "rollout_mode": _to_text(semantic_live_config.get("mode"), "disabled"),
        "symbol": symbol,
        "recent_row_count": 0,
        "symbol_row_count": 0,
        "target_family_row_count": 0,
        "countertrend_enabled_count": 0,
        "countertrend_candidate_sell_count": 0,
        "non_target_leak_row_count": 0,
        "field_presence_ok": False,
        "field_presence_missing": list(REQUIRED_COUNTERTREND_FIELDS),
        "target_setup_id_counts": "{}",
        "target_setup_reason_counts": "{}",
        "target_blocked_by_counts": "{}",
        "target_action_none_reason_counts": "{}",
        "target_reason_summary_counts": "{}",
        "recommended_next_action": "repair_countertrend_runtime_schema_or_restart_core",
    }
    if frame.empty:
        return pd.DataFrame(columns=COUNTERTREND_MATERIALIZATION_CHECK_COLUMNS), summary

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
        "countertrend_continuation_enabled",
        "countertrend_continuation_state",
        "countertrend_continuation_action",
        "countertrend_continuation_confidence",
        "countertrend_continuation_reason_summary",
        "countertrend_candidate_action",
        "countertrend_candidate_confidence",
        "countertrend_candidate_reason",
        "entry_candidate_bridge_source",
        "entry_candidate_bridge_action",
        "entry_candidate_surface_family",
        "entry_candidate_surface_state",
    ):
        if column not in decisions.columns:
            decisions[column] = ""

    decisions["__time_sort"] = pd.to_datetime(decisions["time"], errors="coerce")
    decisions = decisions.sort_values("__time_sort", ascending=False).drop(columns="__time_sort")
    recent = decisions.head(max(1, int(recent_limit))).copy()
    summary["recent_row_count"] = int(len(recent))

    required_missing = [field for field in REQUIRED_COUNTERTREND_FIELDS if field not in recent.columns]
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
            enabled_count=0,
            candidate_sell_count=0,
            leak_row_count=0,
        )
        return pd.DataFrame(columns=COUNTERTREND_MATERIALIZATION_CHECK_COLUMNS), summary

    symbol_frame["target_family_match"] = _target_family_mask(symbol_frame)
    target_frame = symbol_frame.loc[symbol_frame["target_family_match"]].copy()
    leak_frame = recent.loc[
        recent["symbol"].fillna("").astype(str).str.upper() != symbol.upper()
    ].copy()
    if not leak_frame.empty:
        leak_frame["target_family_match"] = False
        leak_frame = leak_frame.loc[
            leak_frame["countertrend_continuation_enabled"].map(_to_bool)
            | leak_frame["countertrend_candidate_action"].fillna("").astype(str).str.strip().ne("")
        ].copy()

    enabled_count = int(target_frame["countertrend_continuation_enabled"].map(_to_bool).sum()) if not target_frame.empty else 0
    candidate_sell_count = (
        int(target_frame["countertrend_candidate_action"].fillna("").astype(str).str.strip().str.upper().eq("SELL").sum())
        if not target_frame.empty
        else 0
    )
    leak_row_count = int(len(leak_frame))

    summary["target_family_row_count"] = int(len(target_frame))
    summary["countertrend_enabled_count"] = enabled_count
    summary["countertrend_candidate_sell_count"] = candidate_sell_count
    summary["non_target_leak_row_count"] = leak_row_count
    summary["target_setup_id_counts"] = _json_counts(_series_counts(target_frame["setup_id"])) if not target_frame.empty else "{}"
    summary["target_setup_reason_counts"] = _json_counts(_series_counts(target_frame["setup_reason"])) if not target_frame.empty else "{}"
    summary["target_blocked_by_counts"] = _json_counts(_series_counts(target_frame["blocked_by"])) if not target_frame.empty else "{}"
    summary["target_action_none_reason_counts"] = _json_counts(_series_counts(target_frame["action_none_reason"])) if not target_frame.empty else "{}"
    summary["target_reason_summary_counts"] = (
        _json_counts(_series_counts(target_frame["countertrend_continuation_reason_summary"])) if not target_frame.empty else "{}"
    )
    summary["recommended_next_action"] = _recommended_next_action(
        field_presence_ok=field_presence_ok,
        symbol_row_count=int(len(symbol_frame)),
        target_family_row_count=int(len(target_frame)),
        enabled_count=enabled_count,
        candidate_sell_count=candidate_sell_count,
        leak_row_count=leak_row_count,
    )

    rows: list[dict[str, Any]] = []

    def _append_rows(source_frame: pd.DataFrame, scope_bucket: str) -> None:
        for _, row in source_frame.iterrows():
            enabled = _to_bool(row.get("countertrend_continuation_enabled"))
            target_match = bool(row.get("target_family_match", False))
            candidate_action = _to_text(row.get("countertrend_candidate_action")).upper()
            note_parts: list[str] = []
            if target_match:
                note_parts.append("target_family")
            else:
                note_parts.append("non_target_scope")
            if enabled:
                note_parts.append("enabled")
            if candidate_action == "SELL":
                note_parts.append("candidate_sell")
            if not enabled and candidate_action != "SELL":
                note_parts.append("inactive")
            rows.append(
                {
                    "observation_event_id": (
                        f"{COUNTERTREND_MATERIALIZATION_CHECK_CONTRACT_VERSION}:"
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
                    "target_family_match": bool(target_match),
                    "countertrend_continuation_enabled": bool(enabled),
                    "countertrend_continuation_state": _to_text(row.get("countertrend_continuation_state")),
                    "countertrend_continuation_action": _to_text(row.get("countertrend_continuation_action")).upper(),
                    "countertrend_continuation_confidence": round(
                        _to_float(row.get("countertrend_continuation_confidence")), 6
                    ),
                    "countertrend_continuation_reason_summary": _to_text(
                        row.get("countertrend_continuation_reason_summary")
                    ),
                    "countertrend_candidate_action": candidate_action,
                    "countertrend_candidate_confidence": round(_to_float(row.get("countertrend_candidate_confidence")), 6),
                    "countertrend_candidate_reason": _to_text(row.get("countertrend_candidate_reason")),
                    "entry_candidate_bridge_source": _to_text(row.get("entry_candidate_bridge_source")),
                    "entry_candidate_bridge_action": _to_text(row.get("entry_candidate_bridge_action")).upper(),
                    "entry_candidate_surface_family": _to_text(row.get("entry_candidate_surface_family")),
                    "entry_candidate_surface_state": _to_text(row.get("entry_candidate_surface_state")),
                    "materialization_note": "|".join(note_parts),
                }
            )

    _append_rows(symbol_frame, "fresh_symbol_slice")
    if not leak_frame.empty:
        _append_rows(leak_frame, "non_target_leak")

    audit_frame = pd.DataFrame(rows, columns=COUNTERTREND_MATERIALIZATION_CHECK_COLUMNS)
    return audit_frame, summary


def render_countertrend_materialization_check_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame | None,
) -> str:
    payload = dict(summary or {})
    rows = frame.copy() if frame is not None and not frame.empty else pd.DataFrame()
    lines = [
        "# Countertrend Materialization Check",
        "",
        f"- generated_at: `{_to_text(payload.get('generated_at'))}`",
        f"- runtime_updated_at: `{_to_text(payload.get('runtime_updated_at'))}`",
        f"- rollout_mode: `{_to_text(payload.get('rollout_mode'))}`",
        f"- symbol: `{_to_text(payload.get('symbol'))}`",
        f"- recent_row_count: `{int(payload.get('recent_row_count') or 0)}`",
        f"- symbol_row_count: `{int(payload.get('symbol_row_count') or 0)}`",
        f"- target_family_row_count: `{int(payload.get('target_family_row_count') or 0)}`",
        f"- countertrend_enabled_count: `{int(payload.get('countertrend_enabled_count') or 0)}`",
        f"- countertrend_candidate_sell_count: `{int(payload.get('countertrend_candidate_sell_count') or 0)}`",
        f"- non_target_leak_row_count: `{int(payload.get('non_target_leak_row_count') or 0)}`",
        f"- field_presence_ok: `{bool(payload.get('field_presence_ok'))}`",
        f"- recommended_next_action: `{_to_text(payload.get('recommended_next_action'))}`",
        "",
        "## Target Slice Counts",
        "",
        f"- target_setup_id_counts: `{_to_text(payload.get('target_setup_id_counts'), '{}')}`",
        f"- target_setup_reason_counts: `{_to_text(payload.get('target_setup_reason_counts'), '{}')}`",
        f"- target_blocked_by_counts: `{_to_text(payload.get('target_blocked_by_counts'), '{}')}`",
        f"- target_action_none_reason_counts: `{_to_text(payload.get('target_action_none_reason_counts'), '{}')}`",
        f"- target_reason_summary_counts: `{_to_text(payload.get('target_reason_summary_counts'), '{}')}`",
    ]
    if rows.empty:
        lines.extend(["", "## Recent Rows", "", "- no rows materialized"])
        return "\n".join(lines) + "\n"

    lines.extend(["", "## Recent Rows", ""])
    preview = rows.head(12)
    for _, row in preview.iterrows():
        lines.append(
            "- "
            + f"{_to_text(row.get('time'))} | `{_to_text(row.get('symbol'))}` | "
            + f"`{_to_text(row.get('setup_id'))}` | "
            + f"target={row.get('target_family_match')} | "
            + f"enabled={row.get('countertrend_continuation_enabled')} | "
            + f"candidate={_to_text(row.get('countertrend_candidate_action')) or 'NONE'} | "
            + f"note={_to_text(row.get('materialization_note'))}"
        )
    return "\n".join(lines) + "\n"
