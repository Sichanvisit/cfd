"""Apply explicit manual signoff decisions to symbol-surface canary packets."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_VERSION = "symbol_surface_manual_signoff_apply_v1"

SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_COLUMNS = [
    "approval_id",
    "packet_id",
    "market_family",
    "surface_name",
    "packet_status",
    "requested_decision",
    "approval_actor",
    "approval_reason",
    "approval_state",
    "signoff_state_after_apply",
    "allow_activation_after_apply",
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


def _decision_lookup(payload: Mapping[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    frame = _to_frame(payload)
    if frame.empty:
        return {}
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        key = (str(row.get("market_family", "")).upper(), str(row.get("surface_name", "")))
        if key[0] and key[1]:
            lookup[key] = dict(row)
    return lookup


def _normalize_decision(value: object) -> str:
    decision = str(value or "").strip().upper()
    if decision in {"APPROVE", "REJECT", "HOLD"}:
        return decision
    return ""


def build_symbol_surface_manual_signoff_apply(
    *,
    symbol_surface_canary_signoff_packet_payload: Mapping[str, Any] | None,
    manual_signoff_decision_payload: Mapping[str, Any] | None = None,
    approve_all_review_ready: bool = False,
    default_approval_actor: str = "user_requested_manual_signoff",
    default_approval_reason: str = "explicit_user_request_to_proceed",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    packet_frame = _to_frame(symbol_surface_canary_signoff_packet_payload)
    decision_lookup = _decision_lookup(manual_signoff_decision_payload)

    if packet_frame.empty:
        empty = pd.DataFrame(columns=SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_COLUMNS)
        return empty, {
            "symbol_surface_manual_signoff_apply_version": SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "approved_count": 0,
            "held_count": 0,
            "rejected_count": 0,
            "recommended_next_action": "await_symbol_surface_signoff_packets",
        }

    rows: list[dict[str, Any]] = []
    for packet in packet_frame.to_dict(orient="records"):
        market_family = str(packet.get("market_family", "")).upper()
        surface_name = str(packet.get("surface_name", ""))
        packet_status = str(packet.get("packet_status", ""))
        explicit = decision_lookup.get((market_family, surface_name), {})
        requested_decision = _normalize_decision(explicit.get("approval_decision", ""))
        if not requested_decision and approve_all_review_ready and packet_status == "REVIEW_PACKET_READY":
            requested_decision = "APPROVE"

        approval_actor = str(explicit.get("approval_actor", "") or default_approval_actor)
        approval_reason = str(explicit.get("approval_reason", "") or default_approval_reason)

        if packet_status != "REVIEW_PACKET_READY":
            approval_state = "PACKET_NOT_READY"
            signoff_state_after_apply = str(packet.get("signoff_state", ""))
            allow_activation_after_apply = False
            recommended_next_action = "hold_until_packet_review_ready"
        elif requested_decision == "APPROVE":
            approval_state = "MANUAL_SIGNOFF_APPROVED"
            signoff_state_after_apply = "MANUAL_SIGNOFF_APPROVED"
            allow_activation_after_apply = True
            recommended_next_action = "apply_bounded_symbol_surface_activation"
        elif requested_decision == "REJECT":
            approval_state = "MANUAL_SIGNOFF_REJECTED"
            signoff_state_after_apply = "MANUAL_SIGNOFF_REJECTED"
            allow_activation_after_apply = False
            recommended_next_action = "hold_rollout_and_collect_more_evidence"
        elif requested_decision == "HOLD":
            approval_state = "MANUAL_SIGNOFF_HELD"
            signoff_state_after_apply = "MANUAL_SIGNOFF_HELD"
            allow_activation_after_apply = False
            recommended_next_action = "hold_review_canary_until_manual_revisit"
        else:
            approval_state = "NO_DECISION_APPLIED"
            signoff_state_after_apply = str(packet.get("signoff_state", ""))
            allow_activation_after_apply = False
            recommended_next_action = "await_manual_signoff_decision"

        rows.append(
            {
                "approval_id": f"symbol_surface_manual_signoff::{market_family}::{surface_name}",
                "packet_id": str(packet.get("packet_id", "")),
                "market_family": market_family,
                "surface_name": surface_name,
                "packet_status": packet_status,
                "requested_decision": requested_decision,
                "approval_actor": approval_actor,
                "approval_reason": approval_reason,
                "approval_state": approval_state,
                "signoff_state_after_apply": signoff_state_after_apply,
                "allow_activation_after_apply": bool(allow_activation_after_apply),
                "recommended_next_action": recommended_next_action,
            }
        )

    frame = pd.DataFrame(rows, columns=SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_COLUMNS)
    summary = {
        "symbol_surface_manual_signoff_apply_version": SYMBOL_SURFACE_MANUAL_SIGNOFF_APPLY_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "approved_count": int((frame["approval_state"] == "MANUAL_SIGNOFF_APPROVED").sum()) if not frame.empty else 0,
        "held_count": int((frame["approval_state"] == "MANUAL_SIGNOFF_HELD").sum()) if not frame.empty else 0,
        "rejected_count": int((frame["approval_state"] == "MANUAL_SIGNOFF_REJECTED").sum()) if not frame.empty else 0,
        "approval_state_counts": frame["approval_state"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "apply_bounded_symbol_surface_activation"
            if not frame.empty and (frame["approval_state"] == "MANUAL_SIGNOFF_APPROVED").any()
            else "await_manual_signoff_decision"
        ),
    }
    return frame, summary


def render_symbol_surface_manual_signoff_apply_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Symbol-Surface Manual Signoff Apply",
        "",
        f"- version: `{summary.get('symbol_surface_manual_signoff_apply_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- approval_state_counts: `{summary.get('approval_state_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
