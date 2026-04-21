"""Diagnostic helpers for the current MF17 pending rollout chain."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


MF17_ROLLOUT_PENDING_DIAGNOSTIC_VERSION = "mf17_rollout_pending_diagnostic_v1"
MF17_ROLLOUT_PENDING_DIAGNOSTIC_COLUMNS = [
    "market_family",
    "surface_name",
    "preview_readiness_state",
    "candidate_state",
    "manifest_status",
    "signoff_state",
    "packet_status",
    "manual_signoff_state",
    "activation_contract_status",
    "activation_state",
    "top_blocker",
    "recommended_next_action",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_mf17_rollout_pending_diagnostic_path() -> Path:
    return _repo_root() / "data" / "analysis" / "shadow_auto" / "mf17_rollout_pending_diagnostic_latest.json"


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


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _first_row(frame: pd.DataFrame, market_family: str, surface_name: str) -> dict[str, Any]:
    if frame.empty:
        return {}
    matches = frame.loc[
        (frame["market_family"] == market_family)
        & (frame["surface_name"] == surface_name)
    ]
    if matches.empty:
        return {}
    return matches.iloc[0].to_dict()


def _preview_blocker(preview_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(preview_row or {})
    readiness_state = _to_text(row.get("readiness_state"))
    if not readiness_state:
        return "preview_row_missing", "rebuild_preview_evaluation"
    if readiness_state != "preview_eval_ready":
        return f"preview_not_ready::{readiness_state}", _to_text(row.get("recommended_action"), "collect_more_symbol_surface_contrast_rows")
    return "", ""


def _candidate_blocker(candidate_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(candidate_row or {})
    candidate_state = _to_text(row.get("rollout_candidate_state"))
    if not candidate_state:
        return "candidate_gate_missing", "rebuild_bounded_rollout_candidate_gate"
    if candidate_state != "REVIEW_CANARY_CANDIDATE":
        return f"candidate_not_review_ready::{candidate_state}", _to_text(row.get("recommended_next_step"), "collect_more_rollout_readiness_support")
    return "", ""


def _signoff_blocker(signoff_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(signoff_row or {})
    signoff_state = _to_text(row.get("signoff_state"))
    if not signoff_state:
        return "signoff_criteria_missing", "rebuild_bounded_rollout_signoff_criteria"
    if signoff_state != "READY_FOR_MANUAL_SIGNOFF":
        return f"signoff_not_ready::{signoff_state}", _to_text(row.get("recommended_next_step"), "hold_mf17_and_resolve_blockers")
    return "", ""


def _packet_blocker(packet_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(packet_row or {})
    packet_status = _to_text(row.get("packet_status"))
    if not packet_status:
        return "signoff_packet_missing", "rebuild_symbol_surface_canary_signoff_packet"
    if packet_status != "REVIEW_PACKET_READY":
        return f"signoff_packet_not_ready::{packet_status}", _to_text(row.get("recommended_next_step"), "await_symbol_surface_canary_signoff_readiness")
    return "", ""


def _manual_signoff_blocker(manual_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(manual_row or {})
    approval_state = _to_text(row.get("approval_state"))
    if not approval_state:
        return "manual_signoff_missing", "apply_manual_signoff_decisions"
    if approval_state != "MANUAL_SIGNOFF_APPROVED":
        return f"manual_signoff_pending::{approval_state}", _to_text(row.get("recommended_next_action"), "await_manual_signoff_decision")
    return "", ""


def _activation_blocker(activation_row: Mapping[str, Any] | None) -> tuple[str, str]:
    row = dict(activation_row or {})
    activation_state = _to_text(row.get("activation_state"))
    if not activation_state:
        return "activation_apply_missing", "rebuild_bounded_symbol_surface_activation_apply"
    if activation_state != "ACTIVE_REVIEW_CANARY":
        return f"activation_not_live::{activation_state}", _to_text(row.get("recommended_next_action"), "await_manual_signoff_or_guard_recovery")
    return "", ""


def _initial_scope_keys(*frames: pd.DataFrame) -> list[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for frame in frames:
        if frame.empty:
            continue
        scoped = frame
        if "surface_name" in scoped.columns:
            initial_only = scoped.loc[scoped["surface_name"] == "initial_entry_surface"]
            if not initial_only.empty:
                scoped = initial_only
        for row in scoped.to_dict(orient="records"):
            market_family = _to_text(row.get("market_family")).upper()
            surface_name = _to_text(row.get("surface_name"))
            if market_family and surface_name:
                keys.add((market_family, surface_name))
    return sorted(keys)


def build_mf17_rollout_pending_diagnostic(
    *,
    symbol_surface_preview_evaluation_payload: Mapping[str, Any] | None,
    bounded_rollout_candidate_gate_payload: Mapping[str, Any] | None,
    bounded_rollout_review_manifest_payload: Mapping[str, Any] | None,
    bounded_rollout_signoff_criteria_payload: Mapping[str, Any] | None,
    symbol_surface_canary_signoff_packet_payload: Mapping[str, Any] | None,
    symbol_surface_manual_signoff_apply_payload: Mapping[str, Any] | None,
    bounded_symbol_surface_activation_contract_payload: Mapping[str, Any] | None,
    bounded_symbol_surface_activation_apply_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    preview_frame = _to_frame(symbol_surface_preview_evaluation_payload)
    candidate_frame = _to_frame(bounded_rollout_candidate_gate_payload)
    manifest_frame = _to_frame(bounded_rollout_review_manifest_payload)
    signoff_frame = _to_frame(bounded_rollout_signoff_criteria_payload)
    packet_frame = _to_frame(symbol_surface_canary_signoff_packet_payload)
    manual_frame = _to_frame(symbol_surface_manual_signoff_apply_payload)
    contract_frame = _to_frame(bounded_symbol_surface_activation_contract_payload)
    activation_frame = _to_frame(bounded_symbol_surface_activation_apply_payload)

    keys = _initial_scope_keys(
        contract_frame,
        activation_frame,
        preview_frame,
        candidate_frame,
        manifest_frame,
        signoff_frame,
        packet_frame,
        manual_frame,
    )
    if not keys:
        empty = pd.DataFrame(columns=MF17_ROLLOUT_PENDING_DIAGNOSTIC_COLUMNS)
        return empty, {
            "contract_version": MF17_ROLLOUT_PENDING_DIAGNOSTIC_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "pending_stage": "preview",
            "top_blocker_counts": {},
            "recommended_next_action": "rebuild_mf17_rollout_chain_inputs",
        }

    rows: list[dict[str, Any]] = []
    blocker_counts: Counter[str] = Counter()
    stage_rank = {
        "preview": 1,
        "candidate": 2,
        "manifest": 3,
        "signoff": 4,
        "packet": 5,
        "manual_signoff": 6,
        "activation": 7,
        "ready": 8,
    }
    furthest_block_stage = "ready"

    for market_family, surface_name in keys:
        preview_row = _first_row(preview_frame, market_family, surface_name)
        candidate_row = _first_row(candidate_frame, market_family, surface_name)
        manifest_row = _first_row(manifest_frame, market_family, surface_name)
        signoff_row = _first_row(signoff_frame, market_family, surface_name)
        packet_row = _first_row(packet_frame, market_family, surface_name)
        manual_row = _first_row(manual_frame, market_family, surface_name)
        contract_row = _first_row(contract_frame, market_family, surface_name)
        activation_row = _first_row(activation_frame, market_family, surface_name)

        top_blocker = ""
        recommended_next_action = ""
        blocker_stage = "ready"

        preview_blocker, preview_next = _preview_blocker(preview_row)
        if preview_blocker:
            top_blocker = preview_blocker
            recommended_next_action = preview_next
            blocker_stage = "preview"
        else:
            candidate_blocker, candidate_next = _candidate_blocker(candidate_row)
            if candidate_blocker:
                top_blocker = candidate_blocker
                recommended_next_action = candidate_next
                blocker_stage = "candidate"
            elif not manifest_row:
                top_blocker = "review_manifest_missing"
                recommended_next_action = "rebuild_bounded_rollout_review_manifest"
                blocker_stage = "manifest"
            else:
                signoff_blocker, signoff_next = _signoff_blocker(signoff_row)
                if signoff_blocker:
                    top_blocker = signoff_blocker
                    recommended_next_action = signoff_next
                    blocker_stage = "signoff"
                else:
                    packet_blocker, packet_next = _packet_blocker(packet_row)
                    if packet_blocker:
                        top_blocker = packet_blocker
                        recommended_next_action = packet_next
                        blocker_stage = "packet"
                    else:
                        manual_blocker, manual_next = _manual_signoff_blocker(manual_row)
                        if manual_blocker:
                            top_blocker = manual_blocker
                            recommended_next_action = manual_next
                            blocker_stage = "manual_signoff"
                        else:
                            activation_blocker, activation_next = _activation_blocker(activation_row)
                            if activation_blocker:
                                top_blocker = activation_blocker
                                recommended_next_action = activation_next
                                blocker_stage = "activation"
                            else:
                                top_blocker = "ready_for_active_review_canary"
                                recommended_next_action = "observe_bounded_symbol_surface_canary_live"
                                blocker_stage = "ready"

        blocker_counts[top_blocker] += 1
        if stage_rank[blocker_stage] < stage_rank[furthest_block_stage]:
            furthest_block_stage = blocker_stage

        rows.append(
            {
                "market_family": market_family,
                "surface_name": surface_name,
                "preview_readiness_state": _to_text(preview_row.get("readiness_state")),
                "candidate_state": _to_text(candidate_row.get("rollout_candidate_state")),
                "manifest_status": _to_text(manifest_row.get("manifest_status")),
                "signoff_state": _to_text(signoff_row.get("signoff_state")),
                "packet_status": _to_text(packet_row.get("packet_status")),
                "manual_signoff_state": _to_text(manual_row.get("approval_state")),
                "activation_contract_status": _to_text(contract_row.get("contract_status")),
                "activation_state": _to_text(activation_row.get("activation_state")),
                "top_blocker": top_blocker,
                "recommended_next_action": recommended_next_action,
            }
        )

    summary = {
        "contract_version": MF17_ROLLOUT_PENDING_DIAGNOSTIC_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(rows)),
        "preview_eval_ready_count": int((preview_frame["readiness_state"] == "preview_eval_ready").sum()) if not preview_frame.empty and "readiness_state" in preview_frame.columns else 0,
        "review_canary_candidate_count": int((candidate_frame["rollout_candidate_state"] == "REVIEW_CANARY_CANDIDATE").sum()) if not candidate_frame.empty and "rollout_candidate_state" in candidate_frame.columns else 0,
        "manifest_row_count": int(len(manifest_frame)),
        "ready_for_manual_signoff_count": int((signoff_frame["signoff_state"] == "READY_FOR_MANUAL_SIGNOFF").sum()) if not signoff_frame.empty and "signoff_state" in signoff_frame.columns else 0,
        "review_packet_ready_count": int((packet_frame["packet_status"] == "REVIEW_PACKET_READY").sum()) if not packet_frame.empty and "packet_status" in packet_frame.columns else 0,
        "manual_signoff_approved_count": int((manual_frame["approval_state"] == "MANUAL_SIGNOFF_APPROVED").sum()) if not manual_frame.empty and "approval_state" in manual_frame.columns else 0,
        "active_review_canary_count": int((activation_frame["activation_state"] == "ACTIVE_REVIEW_CANARY").sum()) if not activation_frame.empty and "activation_state" in activation_frame.columns else 0,
        "pending_stage": furthest_block_stage,
        "top_blocker_counts": dict(blocker_counts),
        "recommended_next_action": {
            "preview": "resolve_preview_readiness_and_rebuild_mf17_chain",
            "candidate": "resolve_candidate_gate_blockers_and_rebuild_mf17_chain",
            "manifest": "rebuild_review_manifest_then_signoff_chain",
            "signoff": "resolve_signoff_gate_blockers_then_retry",
            "packet": "rebuild_signoff_packet_and_apply_manual_decision",
            "manual_signoff": "apply_manual_signoff_decisions_then_retry_activation",
            "activation": "recover_runtime_or_performance_guards_then_retry_activation",
            "ready": "observe_active_review_canaries",
        }.get(furthest_block_stage, "rebuild_mf17_rollout_chain_inputs"),
    }
    frame = pd.DataFrame(rows, columns=MF17_ROLLOUT_PENDING_DIAGNOSTIC_COLUMNS)
    return frame, summary
