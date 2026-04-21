"""Build BTC canary review/signoff scorecards from rollout review manifests."""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_VERSION = "bounded_rollout_signoff_criteria_v1"

BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_COLUMNS = [
    "signoff_id",
    "manifest_id",
    "market_family",
    "surface_name",
    "adapter_mode",
    "rollout_mode",
    "dataset_gate_state",
    "performance_gate_state",
    "guardrail_gate_state",
    "manual_signoff_state",
    "signoff_state",
    "sample_row_count",
    "strong_row_count",
    "positive_count",
    "negative_count",
    "unlabeled_ratio",
    "local_failure_burden",
    "baseline_elapsed_ms",
    "current_elapsed_ms",
    "max_canary_size_multiplier",
    "signoff_checklist",
    "signoff_blockers",
    "recommended_decision",
    "recommended_next_step",
]


def _to_frame(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    frame = pd.DataFrame(list((payload or {}).get("rows", []) or []))
    return frame if not frame.empty else pd.DataFrame()


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_json_loads(text: object, default: object) -> object:
    if not isinstance(text, str) or not text.strip():
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _surface_slug(surface_name: str) -> str:
    return str(surface_name or "").strip().lower().replace(" ", "_")


def _performance_lookup(
    baseline_payload: Mapping[str, Any] | None,
    regression_payload: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    baseline_rows = list((baseline_payload or {}).get("symbol_metrics", []) or [])
    regression_rows = list((regression_payload or {}).get("comparisons", []) or [])
    lookup: dict[str, dict[str, Any]] = {}
    for row in baseline_rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol:
            lookup.setdefault(symbol, {}).update(dict(row))
    for row in regression_rows:
        symbol = str(row.get("symbol", "")).upper()
        if symbol:
            lookup.setdefault(symbol, {}).update(dict(row))
    return lookup


def build_bounded_rollout_signoff_criteria(
    *,
    bounded_rollout_review_manifest_payload: Mapping[str, Any] | None,
    entry_performance_baseline_payload: Mapping[str, Any] | None,
    entry_performance_regression_watch_payload: Mapping[str, Any] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_frame = _to_frame(bounded_rollout_review_manifest_payload)
    if manifest_frame.empty:
        empty = pd.DataFrame(columns=BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_COLUMNS)
        return empty, {
            "bounded_rollout_signoff_criteria_version": BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "row_count": 0,
            "ready_for_manual_signoff_count": 0,
            "hold_count": 0,
            "recommended_next_action": "await_review_manifest_rows",
        }

    performance_lookup = _performance_lookup(
        entry_performance_baseline_payload,
        entry_performance_regression_watch_payload,
    )
    baseline_locked = bool((entry_performance_baseline_payload or {}).get("baseline_locked", False))
    global_reentry_required = bool((entry_performance_regression_watch_payload or {}).get("reentry_required", False))
    reentry_threshold = float((entry_performance_baseline_payload or {}).get("reentry_elapsed_ms_threshold", 200.0) or 200.0)

    rows: list[dict[str, Any]] = []
    for manifest in manifest_frame.to_dict(orient="records"):
        market_family = str(manifest.get("market_family", "")).upper()
        surface_name = str(manifest.get("surface_name", ""))
        perf = performance_lookup.get(market_family, {})
        guardrail_contract = _safe_json_loads(manifest.get("guardrail_contract", ""), {})

        sample_row_count = int(manifest.get("sample_row_count", 0) or 0)
        strong_row_count = int(manifest.get("strong_row_count", 0) or 0)
        positive_count = int(manifest.get("positive_count", 0) or 0)
        negative_count = int(manifest.get("negative_count", 0) or 0)
        unlabeled_ratio = float(manifest.get("unlabeled_ratio", 0.0) or 0.0)
        local_failure_burden = float(manifest.get("local_failure_burden", 0.0) or 0.0)

        dataset_blockers: list[str] = []
        if sample_row_count < 12:
            dataset_blockers.append("sample_row_count_below_12")
        if strong_row_count < 7:
            dataset_blockers.append("strong_row_count_below_7")
        if positive_count < 3 or negative_count < 3:
            dataset_blockers.append("class_balance_too_thin")
        if unlabeled_ratio > 0.0:
            dataset_blockers.append("unlabeled_rows_present")
        if local_failure_burden > 0.40:
            dataset_blockers.append("local_failure_burden_above_0_40")
        dataset_gate_state = "PASS" if not dataset_blockers else "HOLD"

        performance_blockers: list[str] = []
        baseline_elapsed_ms = float(perf.get("baseline_elapsed_ms", perf.get("elapsed_ms", 0.0)) or 0.0)
        current_elapsed_ms = float(perf.get("current_elapsed_ms", perf.get("elapsed_ms", 0.0)) or 0.0)
        symbol_reentry_required = bool(perf.get("reentry_required", global_reentry_required))
        if not baseline_locked:
            performance_blockers.append("performance_baseline_not_locked")
        if symbol_reentry_required:
            performance_blockers.append("performance_regression_reentry_required")
        if current_elapsed_ms >= reentry_threshold:
            performance_blockers.append("current_elapsed_ms_above_threshold")
        if str(perf.get("status", "healthy")).lower() not in ("", "healthy"):
            performance_blockers.append("performance_status_not_healthy")
        performance_gate_state = "PASS" if not performance_blockers else "HOLD"

        guardrail_blockers: list[str] = []
        if bool(guardrail_contract.get("allow_live_override", True)):
            guardrail_blockers.append("live_override_must_stay_disabled")
        if not bool(guardrail_contract.get("require_manual_signoff", False)):
            guardrail_blockers.append("manual_signoff_must_be_required")
        if bool(guardrail_contract.get("require_no_unlabeled_rows", False)) and unlabeled_ratio > 0.0:
            guardrail_blockers.append("guardrail_requires_zero_unlabeled")
        if str(guardrail_contract.get("allowed_symbol", "")).upper() != market_family:
            guardrail_blockers.append("symbol_allowlist_mismatch")
        if str(guardrail_contract.get("allowed_surface", "")) != surface_name:
            guardrail_blockers.append("surface_allowlist_mismatch")
        max_canary_size_multiplier = float(guardrail_contract.get("max_canary_size_multiplier", 0.0) or 0.0)
        if max_canary_size_multiplier > 0.25:
            guardrail_blockers.append("canary_size_multiplier_above_cap")
        guardrail_gate_state = "PASS" if not guardrail_blockers else "HOLD"

        all_blockers = dataset_blockers + performance_blockers + guardrail_blockers
        manual_signoff_state = "PENDING_SIGNOFF" if not all_blockers else "BLOCKED_BEFORE_SIGNOFF"
        signoff_state = "READY_FOR_MANUAL_SIGNOFF" if not all_blockers else "HOLD_BEFORE_SIGNOFF"
        recommended_decision = (
            "APPROVE_REVIEW_CANARY_PENDING_MANUAL_SIGNOFF"
            if signoff_state == "READY_FOR_MANUAL_SIGNOFF"
            else "HOLD_AND_COLLECT_MORE_EVIDENCE"
        )
        surface_slug = _surface_slug(surface_name)
        signoff_checklist = [
            f"review positive preview ids against {market_family.lower()} {surface_slug} adapter thesis",
            "review negative preview ids to confirm true wait/not-enter cases",
            "confirm entry performance regression watch remains healthy and under 200ms",
            "keep live override disabled and size capped at 0.25x",
            "require explicit manual signoff before any bounded canary activation",
        ]

        rows.append(
            {
                "signoff_id": f"bounded_rollout_signoff::{market_family}::{surface_name}",
                "manifest_id": str(manifest.get("manifest_id", "")),
                "market_family": market_family,
                "surface_name": surface_name,
                "adapter_mode": str(manifest.get("adapter_mode", "")),
                "rollout_mode": str(manifest.get("rollout_mode", "review_canary_only")),
                "dataset_gate_state": dataset_gate_state,
                "performance_gate_state": performance_gate_state,
                "guardrail_gate_state": guardrail_gate_state,
                "manual_signoff_state": manual_signoff_state,
                "signoff_state": signoff_state,
                "sample_row_count": sample_row_count,
                "strong_row_count": strong_row_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "unlabeled_ratio": round(unlabeled_ratio, 6),
                "local_failure_burden": round(local_failure_burden, 6),
                "baseline_elapsed_ms": round(baseline_elapsed_ms, 6),
                "current_elapsed_ms": round(current_elapsed_ms, 6),
                "max_canary_size_multiplier": max_canary_size_multiplier,
                "signoff_checklist": _stable_json(signoff_checklist),
                "signoff_blockers": _stable_json(all_blockers),
                "recommended_decision": recommended_decision,
                "recommended_next_step": (
                    f"manual_signoff_{market_family.lower()}_{surface_slug}_review_canary"
                    if signoff_state == "READY_FOR_MANUAL_SIGNOFF"
                    else "hold_mf17_and_resolve_blockers"
                ),
            }
        )

    frame = pd.DataFrame(rows, columns=BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_COLUMNS)
    summary = {
        "bounded_rollout_signoff_criteria_version": BOUNDED_ROLLOUT_SIGNOFF_CRITERIA_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "ready_for_manual_signoff_count": int((frame["signoff_state"] == "READY_FOR_MANUAL_SIGNOFF").sum()) if not frame.empty else 0,
        "hold_count": int((frame["signoff_state"] != "READY_FOR_MANUAL_SIGNOFF").sum()) if not frame.empty else 0,
        "signoff_state_counts": frame["signoff_state"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action": (
            "manual_signoff_canary_candidates"
            if not frame.empty and (frame["signoff_state"] == "READY_FOR_MANUAL_SIGNOFF").any()
            else "hold_rollout_until_signoff_blockers_clear"
        ),
    }
    return frame, summary


def render_bounded_rollout_signoff_criteria_markdown(summary: Mapping[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Bounded Rollout Signoff Criteria",
        "",
        f"- version: `{summary.get('bounded_rollout_signoff_criteria_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- signoff_state_counts: `{summary.get('signoff_state_counts', {})}`",
        f"- recommended_next_action: `{summary.get('recommended_next_action', '')}`",
        "",
    ]
    if not frame.empty:
        lines.extend(["## Signoff Packets", ""])
        for row in frame.to_dict(orient="records"):
            lines.append(
                "- "
                + f"{row.get('market_family', '')} | {row.get('surface_name', '')} | "
                + f"signoff_state={row.get('signoff_state', '')} | "
                + f"decision={row.get('recommended_decision', '')} | "
                + f"next={row.get('recommended_next_step', '')}"
            )
    return "\n".join(lines).rstrip() + "\n"
