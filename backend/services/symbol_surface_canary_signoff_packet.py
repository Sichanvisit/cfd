"""Materialize generic symbol-surface review canary signoff packets."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_VERSION = "symbol_surface_canary_signoff_packet_v1"

SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_COLUMNS = [
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


def _surface_slug(surface_name: str) -> str:
    return str(surface_name or "").strip().lower().replace(" ", "_")


def build_symbol_surface_canary_signoff_packet(
    *,
    bounded_rollout_review_manifest_payload: Mapping[str, Any] | None,
    bounded_rollout_signoff_criteria_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_frame = _to_frame(bounded_rollout_review_manifest_payload)
    signoff_frame = _to_frame(bounded_rollout_signoff_criteria_payload)

    if manifest_frame.empty or signoff_frame.empty:
        empty = pd.DataFrame(columns=SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_COLUMNS)
        return empty, {
            "symbol_surface_canary_signoff_packet_version": SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "packet_row_count": 0,
            "review_ready_count": 0,
            "recommended_next_action": "await_symbol_surface_canary_signoff_readiness",
        }

    rows: list[dict[str, Any]] = []
    for manifest in manifest_frame.to_dict(orient="records"):
        market_family = str(manifest.get("market_family", "")).upper()
        surface_name = str(manifest.get("surface_name", ""))
        signoff_match = signoff_frame.loc[
            (signoff_frame["market_family"] == market_family)
            & (signoff_frame["surface_name"] == surface_name)
        ]
        if signoff_match.empty:
            continue
        signoff = signoff_match.iloc[0].to_dict()
        surface_slug = _surface_slug(surface_name)
        performance_summary = {
            "baseline_elapsed_ms": float(signoff.get("baseline_elapsed_ms", 0.0) or 0.0),
            "current_elapsed_ms": float(signoff.get("current_elapsed_ms", 0.0) or 0.0),
            "performance_gate_state": str(signoff.get("performance_gate_state", "")),
        }
        manual_signoff_questions = [
            f"positive_preview_ids가 {market_family} {surface_slug} adapter thesis와 실제로 맞는가",
            "negative_preview_ids가 label noise가 아니라 진짜 WAIT/NOT-ENTER 케이스인가",
            "현재 성능 baseline과 regression watch가 healthy 상태를 유지하는가",
            "live override 없이 review_canary_only 범위로만 시작할 준비가 되었는가",
        ]
        rows.append(
            {
                "packet_id": f"symbol_surface_review_canary_packet::{market_family}::{surface_name}",
                "market_family": market_family,
                "surface_name": surface_name,
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

    frame = pd.DataFrame(rows, columns=SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_COLUMNS)
    summary = {
        "symbol_surface_canary_signoff_packet_version": SYMBOL_SURFACE_CANARY_SIGNOFF_PACKET_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "packet_row_count": int(len(frame)),
        "review_ready_count": int((frame["packet_status"] == "REVIEW_PACKET_READY").sum()) if not frame.empty else 0,
        "market_family_counts": frame["market_family"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "manual_signoff_symbol_surface_review_canaries"
            if not frame.empty
            else "await_symbol_surface_canary_signoff_readiness"
        ),
    }
    return frame, summary


def render_symbol_surface_canary_signoff_packet_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Symbol-Surface Canary Signoff Packet",
        "",
        f"- version: `{summary.get('symbol_surface_canary_signoff_packet_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- packet_row_count: `{summary.get('packet_row_count', 0)}`",
        f"- review_ready_count: `{summary.get('review_ready_count', 0)}`",
        f"- market_family_counts: `{summary.get('market_family_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
