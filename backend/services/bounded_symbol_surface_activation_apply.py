"""Apply bounded symbol-surface activation decisions after manual signoff."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_VERSION = "bounded_symbol_surface_activation_apply_v1"

BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_COLUMNS = [
    "activation_apply_id",
    "contract_id",
    "market_family",
    "surface_name",
    "contract_status_before",
    "contract_status_after_apply",
    "manual_signoff_state",
    "approval_decision",
    "performance_status",
    "current_elapsed_ms",
    "threshold_elapsed_ms",
    "runtime_idle_flag",
    "open_positions_count",
    "activation_state",
    "allow_live_activation_after_apply",
    "activation_mode",
    "activation_reason",
    "recommended_next_action",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    if frame.empty:
        return frame
    for column in ("market_family", "surface_name"):
        if column not in frame.columns:
            frame[column] = ""
    frame["market_family"] = frame["market_family"].fillna("").astype(str).str.upper()
    frame["surface_name"] = frame["surface_name"].fillna("").astype(str)
    return frame


def _performance_lookup(payload: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows = list((payload or {}).get("comparisons", []) or [])
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol:
            lookup[symbol] = dict(row)
    return lookup


def _runtime_idle(runtime_status: Mapping[str, Any] | None) -> tuple[bool, int]:
    runtime_recycle = (runtime_status or {}).get("runtime_recycle", {})
    if not isinstance(runtime_recycle, Mapping):
        return True, 0
    try:
        open_positions_count = int(runtime_recycle.get("last_open_positions_count", 0) or 0)
    except Exception:
        open_positions_count = 0
    return open_positions_count <= 0, open_positions_count


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_bounded_symbol_surface_activation_apply(
    *,
    bounded_symbol_surface_activation_contract_payload: Mapping[str, Any] | None,
    symbol_surface_manual_signoff_apply_payload: Mapping[str, Any] | None,
    entry_performance_regression_watch_payload: Mapping[str, Any] | None,
    runtime_status: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    contract_frame = _to_frame(bounded_symbol_surface_activation_contract_payload)
    signoff_frame = _to_frame(symbol_surface_manual_signoff_apply_payload)
    if contract_frame.empty:
        empty = pd.DataFrame(columns=BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_COLUMNS)
        return empty, pd.DataFrame(), {
            "bounded_symbol_surface_activation_apply_version": BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "active_review_canary_count": 0,
            "held_count": 0,
            "recommended_next_action": "await_bounded_symbol_surface_activation_contract",
        }

    performance_lookup = _performance_lookup(entry_performance_regression_watch_payload)
    threshold_elapsed_ms = float((entry_performance_regression_watch_payload or {}).get("reentry_elapsed_ms_threshold", 200.0) or 200.0)
    runtime_idle_flag, open_positions_count = _runtime_idle(runtime_status)

    rows: list[dict[str, Any]] = []
    resolved_rows: list[dict[str, Any]] = []
    for contract in contract_frame.to_dict(orient="records"):
        market_family = str(contract.get("market_family", "")).upper()
        surface_name = str(contract.get("surface_name", ""))
        if signoff_frame.empty or "market_family" not in signoff_frame.columns or "surface_name" not in signoff_frame.columns:
            signoff_match = pd.DataFrame()
        else:
            signoff_match = signoff_frame.loc[
                (signoff_frame["market_family"] == market_family)
                & (signoff_frame["surface_name"] == surface_name)
            ]
        signoff_row = signoff_match.iloc[0].to_dict() if not signoff_match.empty else {}
        manual_signoff_state = str(signoff_row.get("approval_state", "NO_DECISION_APPLIED"))
        approval_decision = str(signoff_row.get("requested_decision", ""))

        perf = performance_lookup.get(market_family, {})
        performance_status = str(perf.get("status", "healthy") or "healthy")
        current_elapsed_ms = float(perf.get("current_elapsed_ms", 0.0) or 0.0)
        symbol_reentry_required = bool(perf.get("reentry_required", False))
        performance_healthy = (
            performance_status == "healthy"
            and not symbol_reentry_required
            and current_elapsed_ms < threshold_elapsed_ms
        )

        if manual_signoff_state != "MANUAL_SIGNOFF_APPROVED":
            activation_state = "HOLD_MANUAL_SIGNOFF"
            contract_status_after_apply = "PENDING_MANUAL_SIGNOFF"
            allow_live_activation_after_apply = False
            activation_reason = "manual_signoff_not_approved"
            recommended_next_action = "await_or_update_manual_signoff_decision"
        elif not performance_healthy:
            activation_state = "HOLD_PERFORMANCE_GUARD"
            contract_status_after_apply = "APPROVED_PENDING_PERFORMANCE_RECOVERY"
            allow_live_activation_after_apply = False
            activation_reason = "performance_regression_guard_active"
            recommended_next_action = "reenter_entry_performance_optimization"
        elif not runtime_idle_flag:
            activation_state = "HOLD_RUNTIME_NOT_IDLE"
            contract_status_after_apply = "APPROVED_PENDING_RUNTIME_IDLE"
            allow_live_activation_after_apply = False
            activation_reason = "runtime_not_idle"
            recommended_next_action = "wait_for_runtime_idle_then_retry_activation"
        else:
            activation_state = "ACTIVE_REVIEW_CANARY"
            contract_status_after_apply = "ACTIVE_REVIEW_CANARY"
            allow_live_activation_after_apply = True
            activation_reason = "manual_signoff_approved_and_guards_clear"
            recommended_next_action = "observe_bounded_symbol_surface_canary_live"

        rows.append(
            {
                "activation_apply_id": f"bounded_symbol_surface_activation_apply::{market_family}::{surface_name}",
                "contract_id": str(contract.get("contract_id", "")),
                "market_family": market_family,
                "surface_name": surface_name,
                "contract_status_before": str(contract.get("contract_status", "")),
                "contract_status_after_apply": contract_status_after_apply,
                "manual_signoff_state": manual_signoff_state,
                "approval_decision": approval_decision,
                "performance_status": performance_status,
                "current_elapsed_ms": round(current_elapsed_ms, 6),
                "threshold_elapsed_ms": round(threshold_elapsed_ms, 6),
                "runtime_idle_flag": bool(runtime_idle_flag),
                "open_positions_count": int(open_positions_count),
                "activation_state": activation_state,
                "allow_live_activation_after_apply": bool(allow_live_activation_after_apply),
                "activation_mode": str(contract.get("activation_mode", "")),
                "activation_reason": activation_reason,
                "recommended_next_action": recommended_next_action,
            }
        )

        resolved_row = dict(contract)
        resolved_row["contract_status"] = contract_status_after_apply
        resolved_row["allow_live_activation"] = bool(allow_live_activation_after_apply)
        resolved_row["blocking_reason"] = "" if allow_live_activation_after_apply else activation_reason
        resolved_row["recommended_next_step"] = recommended_next_action
        resolved_row["activation_apply_context"] = _stable_json(
            {
                "manual_signoff_state": manual_signoff_state,
                "approval_decision": approval_decision,
                "performance_status": performance_status,
                "current_elapsed_ms": round(current_elapsed_ms, 6),
                "threshold_elapsed_ms": round(threshold_elapsed_ms, 6),
                "runtime_idle_flag": bool(runtime_idle_flag),
                "open_positions_count": int(open_positions_count),
                "activation_state": activation_state,
                "activation_reason": activation_reason,
            }
        )
        resolved_rows.append(resolved_row)

    frame = pd.DataFrame(rows, columns=BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_COLUMNS)
    resolved_contract_frame = pd.DataFrame(resolved_rows)
    summary = {
        "bounded_symbol_surface_activation_apply_version": BOUNDED_SYMBOL_SURFACE_ACTIVATION_APPLY_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "active_review_canary_count": int((frame["activation_state"] == "ACTIVE_REVIEW_CANARY").sum()) if not frame.empty else 0,
        "held_count": int((frame["activation_state"] != "ACTIVE_REVIEW_CANARY").sum()) if not frame.empty else 0,
        "activation_state_counts": frame["activation_state"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "observe_active_review_canaries_and_keep_blocked_symbols_held"
            if not frame.empty and (frame["activation_state"] == "ACTIVE_REVIEW_CANARY").any()
            else "await_manual_signoff_or_guard_recovery"
        ),
    }
    return frame, resolved_contract_frame, summary


def render_bounded_symbol_surface_activation_apply_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Bounded Symbol-Surface Activation Apply",
        "",
        f"- version: `{summary.get('bounded_symbol_surface_activation_apply_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- activation_state_counts: `{summary.get('activation_state_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
