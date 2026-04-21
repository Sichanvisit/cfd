"""Audit how much shadow divergence evidence is anchored by manual truth."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_MANUAL_REFERENCE_AUDIT_VERSION = "shadow_auto_manual_reference_audit_v0"
SHADOW_AUTO_MANUAL_REFERENCE_AUDIT_COLUMNS = [
    "audit_scope_id",
    "scope_kind",
    "scope_value",
    "row_count",
    "manual_reference_row_count",
    "manual_reference_share",
    "manual_target_match_count",
    "manual_target_match_rate",
    "required_manual_reference_row_count",
    "manual_reference_ready_flag",
    "manual_reference_status",
    "recommended_next_action",
]


def load_shadow_auto_manual_reference_audit_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _to_bool(value: Any, default: bool = False) -> bool:
    try:
        if pd.isna(value):
            return bool(default)
    except TypeError:
        pass
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(value) if value is not None else bool(default)


def _status_for(
    *,
    manual_reference_row_count: int,
    required_manual_reference_row_count: int,
    manual_target_match_rate: float,
) -> tuple[str, str]:
    if manual_reference_row_count <= 0:
        return (
            "manual_truth_missing",
            "expand_manual_truth_shadow_overlap",
        )
    if manual_reference_row_count < required_manual_reference_row_count:
        return (
            "manual_truth_thin",
            "collect_more_manual_truth_for_shadow_family",
        )
    if manual_target_match_rate < 0.5:
        return (
            "manual_truth_conflicted",
            "review_shadow_target_mapping_against_manual_truth",
        )
    return (
        "manual_truth_ready",
        "use_manual_truth_overlap_in_bounded_gate",
    )


def _summarize_scope(
    scope_kind: str,
    scope_value: str,
    frame: pd.DataFrame,
    *,
    required_manual_reference_row_count: int,
) -> dict[str, Any]:
    row_count = int(len(frame))
    manual_mask = frame.get("manual_reference_found", pd.Series(dtype=object)).map(_to_bool)
    manual_reference_row_count = int(manual_mask.sum()) if not frame.empty else 0
    manual_rows = frame.loc[manual_mask].copy() if not frame.empty else pd.DataFrame()
    manual_target_match_count = int(
        manual_rows.get("manual_target_match_flag", pd.Series(dtype=object)).map(_to_bool).sum()
    ) if not manual_rows.empty else 0
    manual_target_match_rate = (
        round(manual_target_match_count / manual_reference_row_count, 6)
        if manual_reference_row_count > 0
        else 0.0
    )
    status, action = _status_for(
        manual_reference_row_count=manual_reference_row_count,
        required_manual_reference_row_count=int(required_manual_reference_row_count),
        manual_target_match_rate=float(manual_target_match_rate),
    )
    return {
        "audit_scope_id": f"{scope_kind}::{scope_value}",
        "scope_kind": scope_kind,
        "scope_value": scope_value,
        "row_count": row_count,
        "manual_reference_row_count": manual_reference_row_count,
        "manual_reference_share": round(manual_reference_row_count / row_count, 6) if row_count > 0 else 0.0,
        "manual_target_match_count": manual_target_match_count,
        "manual_target_match_rate": manual_target_match_rate,
        "required_manual_reference_row_count": int(required_manual_reference_row_count),
        "manual_reference_ready_flag": manual_reference_row_count >= int(required_manual_reference_row_count)
        and manual_target_match_rate >= 0.5,
        "manual_reference_status": status,
        "recommended_next_action": action,
    }


def build_shadow_auto_manual_reference_audit(
    divergence_rows: pd.DataFrame | None,
    *,
    required_manual_reference_row_count: int = 5,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    working = divergence_rows.copy() if divergence_rows is not None else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    if not working.empty:
        rows.append(
            _summarize_scope(
                "overall",
                "all",
                working,
                required_manual_reference_row_count=required_manual_reference_row_count,
            )
        )
        if "symbol" in working.columns:
            for symbol, subset in working.groupby("symbol", dropna=False):
                rows.append(
                    _summarize_scope(
                        "symbol",
                        str(symbol or "unknown"),
                        subset.copy(),
                        required_manual_reference_row_count=required_manual_reference_row_count,
                    )
                )
    frame = pd.DataFrame(rows, columns=SHADOW_AUTO_MANUAL_REFERENCE_AUDIT_COLUMNS)
    overall = frame.iloc[0].to_dict() if not frame.empty else {}
    summary = {
        "shadow_auto_manual_reference_audit_version": SHADOW_AUTO_MANUAL_REFERENCE_AUDIT_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "row_count": int(len(frame)),
        "overall_manual_reference_row_count": int(overall.get("manual_reference_row_count", 0) or 0),
        "overall_manual_reference_share": float(overall.get("manual_reference_share", 0.0) or 0.0),
        "overall_manual_target_match_rate": float(overall.get("manual_target_match_rate", 0.0) or 0.0),
        "status_counts": frame["manual_reference_status"].value_counts().to_dict() if not frame.empty else {},
        "recommended_next_action_counts": frame["recommended_next_action"].value_counts().to_dict()
        if not frame.empty
        else {},
    }
    return frame, summary


def render_shadow_auto_manual_reference_audit_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    lines = [
        "# Shadow Manual-Reference Audit",
        "",
        f"- version: `{summary.get('shadow_auto_manual_reference_audit_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- row_count: `{summary.get('row_count', 0)}`",
        f"- overall_manual_reference_row_count: `{summary.get('overall_manual_reference_row_count', 0)}`",
        f"- overall_manual_reference_share: `{summary.get('overall_manual_reference_share', 0.0)}`",
        f"- overall_manual_target_match_rate: `{summary.get('overall_manual_target_match_rate', 0.0)}`",
        f"- status_counts: `{summary.get('status_counts', {})}`",
        "",
        "## Scopes",
        "",
    ]
    if frame.empty:
        lines.append("- no divergence rows available")
    else:
        for row in frame.to_dict(orient="records"):
            lines.extend(
                [
                    f"### {row.get('scope_kind', '')} :: {row.get('scope_value', '')}",
                    "",
                    f"- manual_reference_row_count: `{row.get('manual_reference_row_count', 0)}`",
                    f"- manual_reference_share: `{row.get('manual_reference_share', 0.0)}`",
                    f"- manual_target_match_rate: `{row.get('manual_target_match_rate', 0.0)}`",
                    f"- manual_reference_status: `{row.get('manual_reference_status', '')}`",
                    f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
