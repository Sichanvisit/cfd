"""Focused audit for wrong_failed_wait_interpretation cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


WRONG_FAILED_WAIT_AUDIT_VERSION = "manual_vs_heuristic_wrong_failed_wait_audit_v0"

WRONG_FAILED_WAIT_AUDIT_COLUMNS = [
    "episode_id",
    "symbol",
    "anchor_time",
    "manual_wait_teacher_label",
    "heuristic_barrier_main_label",
    "heuristic_wait_family",
    "heuristic_match_gap_minutes",
    "global_detail_entry_wait_decision",
    "global_detail_blocked_by",
    "global_detail_observe_reason",
    "global_detail_core_reason",
    "global_detail_entry_enter_value",
    "global_detail_entry_wait_value",
    "gap_risk_flag",
    "value_bias_flag",
    "pattern_flag",
    "rule_change_readiness",
    "recommended_resolution",
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
        if value in ("", None):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def load_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _gap_risk_flag(gap_minutes: float) -> str:
    if gap_minutes >= 90.0:
        return "very_far_gap"
    if gap_minutes >= 60.0:
        return "far_gap"
    if gap_minutes > 0.0:
        return "near_gap"
    return "unknown_gap"


def _value_bias_flag(wait_value: float, enter_value: float) -> str:
    if wait_value <= 0.0 and enter_value <= 0.0:
        return "no_numeric_edge"
    if wait_value >= enter_value + 0.10:
        return "wait_value_dominant"
    if enter_value >= wait_value + 0.10:
        return "enter_value_dominant"
    return "balanced_value"


def _pattern_flag(wait_decision: str, blocked_by: str, observe_reason: str) -> str:
    if wait_decision == "skip" and "lower_rebound_probe_observe" in observe_reason:
        return "rebound_probe_skip"
    if "wait_soft_helper_block" in wait_decision and "outer_band_reversal_support_required_observe" in observe_reason:
        return "outer_band_helper_wait"
    return "other"


def _recommended_resolution(gap_flag: str, value_flag: str, pattern_flag: str) -> tuple[str, str]:
    if gap_flag in {"far_gap", "very_far_gap"}:
        return (
            "needs_closer_manual_truth",
            "time gap too large for direct barrier-rule edit; collect closer current-rich manual truth first",
        )
    if pattern_flag == "outer_band_helper_wait" and value_flag == "wait_value_dominant":
        return (
            "keep_wait_bias_until_recent_verified",
            "helper-wait pattern still favors waiting numerically; validate with recent current-rich manual truth before changing rule",
        )
    if pattern_flag == "rebound_probe_skip" and value_flag in {"enter_value_dominant", "balanced_value"}:
        return (
            "candidate_for_failed_wait_shift",
            "rebound-probe skip pattern may belong to failed_wait/missed_profit recovery after closer-window validation",
        )
    return (
        "needs_manual_review",
        "evidence mixed; review manually before changing barrier rule",
    )


def build_wrong_failed_wait_audit(
    comparison_report: pd.DataFrame,
    global_detail_fallback: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    comparison = comparison_report.copy() if comparison_report is not None else pd.DataFrame()
    detail = global_detail_fallback.copy() if global_detail_fallback is not None else pd.DataFrame()
    if comparison.empty:
        empty = pd.DataFrame(columns=WRONG_FAILED_WAIT_AUDIT_COLUMNS)
        return empty, {
            "audit_version": WRONG_FAILED_WAIT_AUDIT_VERSION,
            "case_count": 0,
            "gap_risk_counts": {},
            "value_bias_counts": {},
            "pattern_counts": {},
            "rule_change_readiness_counts": {},
        }

    cases = comparison[
        comparison["miss_type"].fillna("").astype(str).eq("wrong_failed_wait_interpretation")
    ].copy()
    if cases.empty:
        empty = pd.DataFrame(columns=WRONG_FAILED_WAIT_AUDIT_COLUMNS)
        return empty, {
            "audit_version": WRONG_FAILED_WAIT_AUDIT_VERSION,
            "case_count": 0,
            "gap_risk_counts": {},
            "value_bias_counts": {},
            "pattern_counts": {},
            "rule_change_readiness_counts": {},
        }

    if not detail.empty and "episode_id" in detail.columns:
        merge_cols = [
            "episode_id",
            "global_detail_entry_wait_decision",
            "global_detail_blocked_by",
            "global_detail_observe_reason",
            "global_detail_core_reason",
            "global_detail_entry_enter_value",
            "global_detail_entry_wait_value",
        ]
        available_merge_cols = [col for col in merge_cols if col in detail.columns]
        cases = cases.merge(detail[available_merge_cols], on="episode_id", how="left")

    rows: list[dict[str, Any]] = []
    for _, row in cases.iterrows():
        gap = _to_float(row.get("heuristic_match_gap_minutes", ""), 0.0)
        wait_value = _to_float(row.get("global_detail_entry_wait_value", ""), 0.0)
        enter_value = _to_float(row.get("global_detail_entry_enter_value", ""), 0.0)
        wait_decision = _to_text(row.get("global_detail_entry_wait_decision", ""), "").lower()
        blocked_by = _to_text(row.get("global_detail_blocked_by", ""), "").lower()
        observe_reason = _to_text(row.get("global_detail_observe_reason", ""), "").lower()
        core_reason = _to_text(row.get("global_detail_core_reason", ""), "").lower()

        gap_flag = _gap_risk_flag(gap)
        value_flag = _value_bias_flag(wait_value, enter_value)
        pattern_flag = _pattern_flag(wait_decision, blocked_by, observe_reason)
        readiness, resolution = _recommended_resolution(gap_flag, value_flag, pattern_flag)

        rows.append(
            {
                "episode_id": _to_text(row.get("episode_id", ""), ""),
                "symbol": _to_text(row.get("symbol", ""), "").upper(),
                "anchor_time": _to_text(row.get("anchor_time", ""), ""),
                "manual_wait_teacher_label": _to_text(row.get("manual_wait_teacher_label", ""), "").lower(),
                "heuristic_barrier_main_label": _to_text(row.get("heuristic_barrier_main_label", ""), "").lower(),
                "heuristic_wait_family": _to_text(row.get("heuristic_wait_family", ""), "").lower(),
                "heuristic_match_gap_minutes": gap,
                "global_detail_entry_wait_decision": wait_decision,
                "global_detail_blocked_by": blocked_by,
                "global_detail_observe_reason": observe_reason,
                "global_detail_core_reason": core_reason,
                "global_detail_entry_enter_value": enter_value,
                "global_detail_entry_wait_value": wait_value,
                "gap_risk_flag": gap_flag,
                "value_bias_flag": value_flag,
                "pattern_flag": pattern_flag,
                "rule_change_readiness": readiness,
                "recommended_resolution": resolution,
            }
        )

    audit = pd.DataFrame(rows)
    for column in WRONG_FAILED_WAIT_AUDIT_COLUMNS:
        if column not in audit.columns:
            audit[column] = ""
    audit = audit[WRONG_FAILED_WAIT_AUDIT_COLUMNS].copy()

    summary = {
        "audit_version": WRONG_FAILED_WAIT_AUDIT_VERSION,
        "case_count": int(len(audit)),
        "gap_risk_counts": audit["gap_risk_flag"].value_counts(dropna=False).to_dict(),
        "value_bias_counts": audit["value_bias_flag"].value_counts(dropna=False).to_dict(),
        "pattern_counts": audit["pattern_flag"].value_counts(dropna=False).to_dict(),
        "rule_change_readiness_counts": audit["rule_change_readiness"].value_counts(dropna=False).to_dict(),
    }
    return audit, summary


def render_wrong_failed_wait_audit_markdown(summary: Mapping[str, Any], audit: pd.DataFrame) -> str:
    lines = [
        "# Wrong Failed-Wait Interpretation Audit v0",
        "",
        f"- cases: `{summary.get('case_count', 0)}`",
        f"- gap risk: `{summary.get('gap_risk_counts', {})}`",
        f"- value bias: `{summary.get('value_bias_counts', {})}`",
        f"- pattern flags: `{summary.get('pattern_counts', {})}`",
        f"- rule-change readiness: `{summary.get('rule_change_readiness_counts', {})}`",
        "",
        "## Cases",
    ]
    if audit.empty:
        lines.append("- none")
    else:
        for _, row in audit.iterrows():
            lines.append(
                "- "
                + " | ".join(
                    [
                        _to_text(row.get("episode_id", "")),
                        _to_text(row.get("symbol", "")),
                        f"gap={_to_text(row.get('heuristic_match_gap_minutes', ''))}",
                        _to_text(row.get("pattern_flag", "")),
                        _to_text(row.get("value_bias_flag", "")),
                        _to_text(row.get("rule_change_readiness", "")),
                    ]
                )
            )
            lines.append(f"  resolution: {_to_text(row.get('recommended_resolution', ''), '')}")
    return "\n".join(lines) + "\n"
