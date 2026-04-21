"""Materialize BTC initial-entry review canary signoff packet."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_VERSION = "btc_initial_entry_canary_signoff_packet_v1"

BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_COLUMNS = [
    "packet_id",
    "market_family",
    "surface_name",
    "packet_status",
    "adapter_mode",
    "rollout_mode",
    "signoff_state",
    "recommended_decision",
    "positive_preview_ids",
    "negative_preview_ids",
    "review_checklist",
    "guardrail_contract",
    "performance_summary",
    "manual_signoff_questions",
    "recommended_next_step",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads_maybe(text: object, default: object) -> object:
    if not isinstance(text, str) or not text.strip():
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def build_btc_initial_entry_canary_signoff_packet(
    *,
    bounded_rollout_review_manifest_payload: Mapping[str, Any] | None,
    bounded_rollout_signoff_criteria_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_frame = _to_frame(bounded_rollout_review_manifest_payload)
    signoff_frame = _to_frame(bounded_rollout_signoff_criteria_payload)

    if manifest_frame.empty or signoff_frame.empty:
        empty = pd.DataFrame(columns=BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_COLUMNS)
        return empty, {
            "btc_initial_entry_canary_signoff_packet_version": BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "packet_row_count": 0,
            "review_ready_count": 0,
            "recommended_next_action": "await_btc_canary_signoff_readiness",
        }

    manifest_slice = manifest_frame.loc[
        (manifest_frame["market_family"] == "BTCUSD")
        & (manifest_frame["surface_name"] == "initial_entry_surface")
    ].copy()
    signoff_slice = signoff_frame.loc[
        (signoff_frame["market_family"] == "BTCUSD")
        & (signoff_frame["surface_name"] == "initial_entry_surface")
    ].copy()

    rows: list[dict[str, Any]] = []
    if not manifest_slice.empty and not signoff_slice.empty:
        manifest = manifest_slice.iloc[0].to_dict()
        signoff = signoff_slice.iloc[0].to_dict()
        performance_summary = {
            "baseline_elapsed_ms": float(signoff.get("baseline_elapsed_ms", 0.0) or 0.0),
            "current_elapsed_ms": float(signoff.get("current_elapsed_ms", 0.0) or 0.0),
            "performance_gate_state": str(signoff.get("performance_gate_state", "")),
        }
        manual_signoff_questions = [
            "positive_preview_ids 5건이 실제 BTC observe relief initial-entry thesis와 일치하는가",
            "negative_preview_ids 5건이 label noise가 아니라 진짜 WAIT/NOT-ENTER 케이스인가",
            "현재 성능 baseline과 regression watch가 healthy 상태를 유지하는가",
            "live override 없이 review_canary_only 범위로만 시작할 준비가 되었는가",
        ]
        rows.append(
            {
                "packet_id": "btc_initial_entry_review_canary_packet",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "packet_status": (
                    "REVIEW_PACKET_READY"
                    if str(signoff.get("signoff_state", "")) == "READY_FOR_MANUAL_SIGNOFF"
                    else "HOLD_PACKET"
                ),
                "adapter_mode": str(manifest.get("adapter_mode", "")),
                "rollout_mode": str(manifest.get("rollout_mode", "")),
                "signoff_state": str(signoff.get("signoff_state", "")),
                "recommended_decision": str(signoff.get("recommended_decision", "")),
                "positive_preview_ids": str(manifest.get("positive_preview_ids", "[]")),
                "negative_preview_ids": str(manifest.get("negative_preview_ids", "[]")),
                "review_checklist": str(manifest.get("review_checklist", "[]")),
                "guardrail_contract": str(manifest.get("guardrail_contract", "{}")),
                "performance_summary": _stable_json(performance_summary),
                "manual_signoff_questions": _stable_json(manual_signoff_questions),
                "recommended_next_step": str(signoff.get("recommended_next_step", "")),
            }
        )

    frame = pd.DataFrame(rows, columns=BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_COLUMNS)
    summary = {
        "btc_initial_entry_canary_signoff_packet_version": BTC_INITIAL_ENTRY_CANARY_SIGNOFF_PACKET_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "packet_row_count": int(len(frame)),
        "review_ready_count": int((frame["packet_status"] == "REVIEW_PACKET_READY").sum()) if not frame.empty else 0,
        "recommended_next_action": (
            "manual_signoff_btcusd_initial_entry_review_canary"
            if not frame.empty
            else "await_btc_canary_signoff_readiness"
        ),
    }
    return frame, summary


def render_btc_initial_entry_canary_signoff_packet_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# BTC Initial Entry Canary Signoff Packet",
        "",
        f"- version: `{summary.get('btc_initial_entry_canary_signoff_packet_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- packet_row_count: `{summary.get('packet_row_count', 0)}`",
        f"- review_ready_count: `{summary.get('review_ready_count', 0)}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    if not frame.empty:
        row = frame.iloc[0].to_dict()
        lines.extend(
            [
                "## Packet",
                "",
                f"- status: `{row.get('packet_status', '')}`",
                f"- signoff_state: `{row.get('signoff_state', '')}`",
                f"- recommended_decision: `{row.get('recommended_decision', '')}`",
                f"- next_step: `{row.get('recommended_next_step', '')}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
