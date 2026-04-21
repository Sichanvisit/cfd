"""Bridge calibration outputs into shadow-auto candidate inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_CANDIDATE_BRIDGE_VERSION = "shadow_auto_candidate_bridge_v0"

SHADOW_AUTO_CANDIDATE_COLUMNS = [
    "shadow_candidate_id",
    "created_at",
    "family_key",
    "miss_type",
    "primary_correction_target",
    "manual_wait_teacher_family",
    "heuristic_wait_family",
    "heuristic_barrier_main_label",
    "case_count",
    "correction_worthy_case_count",
    "freeze_worthy_case_count",
    "hold_for_more_truth_case_count",
    "ready_case_count",
    "priority_tier",
    "recommended_next_action",
    "family_disposition",
    "baseline_mode",
    "shadow_mode",
    "correction_candidate_id",
    "correction_selected_for_patch",
    "correction_selection_reason",
    "patch_draft_id",
    "patch_draft_status",
    "patch_readiness",
    "patch_version",
    "candidate_kind",
    "selected_for_shadow",
    "selection_reason",
    "bridge_status",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else default


def _to_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return int(default)
    except TypeError:
        pass
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def load_shadow_auto_bridge_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _slugify(value: str) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in value.strip())
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_").lower() or "candidate"


def _candidate_kind(
    *,
    family_disposition: str,
    patch_draft_status: str,
    recommended_next_action: str,
    selected_for_shadow: bool,
) -> str:
    if selected_for_shadow:
        return "shadow_patch_candidate"
    if patch_draft_status == "truth_collection_before_patch" or recommended_next_action == "collect_current_rich_truth":
        return "truth_collection_probe"
    if family_disposition == "freeze_candidate":
        return "freeze_monitor"
    return "shadow_review_candidate"


def _bridge_status(
    *,
    selected_for_shadow: bool,
    patch_readiness: str,
    family_disposition: str,
    recommended_next_action: str,
) -> str:
    if selected_for_shadow:
        return "shadow_ready"
    if family_disposition == "freeze_candidate" or recommended_next_action == "freeze_and_monitor":
        return "freeze_track_only"
    if patch_readiness == "blocked" and recommended_next_action == "collect_current_rich_truth":
        return "await_more_truth"
    return "blocked_patch"


def _selection_reason(
    *,
    selected_for_shadow: bool,
    correction_selected_for_patch: bool,
    patch_readiness: str,
    recommended_next_action: str,
) -> str:
    if selected_for_shadow and correction_selected_for_patch:
        return "selected_via_correction_candidate"
    if selected_for_shadow:
        return "selected_via_shadow_patch_readiness"
    if recommended_next_action == "collect_current_rich_truth":
        return "collect_more_truth_before_shadow"
    if recommended_next_action == "freeze_and_monitor":
        return "freeze_candidate_do_not_shadow"
    if patch_readiness == "blocked":
        return "patch_blocked_pending_review"
    return "not_selected_for_shadow"


def build_shadow_auto_candidate_bridge(
    ranking: pd.DataFrame,
    *,
    patch_draft: pd.DataFrame | None = None,
    correction_candidates: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    ranking_df = ranking.copy() if ranking is not None else pd.DataFrame()
    patch_df = patch_draft.copy() if patch_draft is not None else pd.DataFrame()
    correction_df = correction_candidates.copy() if correction_candidates is not None else pd.DataFrame()

    if ranking_df.empty:
        empty = pd.DataFrame(columns=SHADOW_AUTO_CANDIDATE_COLUMNS)
        summary = {
            "shadow_candidate_bridge_version": SHADOW_AUTO_CANDIDATE_BRIDGE_VERSION,
            "generated_at": now_kst_dt().isoformat(),
            "candidate_count": 0,
            "selected_for_shadow_count": 0,
            "bridge_status_counts": {},
            "candidate_kind_counts": {},
            "selected_candidate_ids": [],
        }
        return empty, summary

    patch_map = {
        _to_text(row.get("family_id")): row
        for row in patch_df.to_dict(orient="records")
        if _to_text(row.get("family_id"))
    }
    correction_map = {
        _to_text(row.get("family_key")): row
        for row in correction_df.to_dict(orient="records")
        if _to_text(row.get("family_key"))
    }

    rows: list[dict[str, Any]] = []
    created_at = now_kst_dt().isoformat(timespec="seconds")
    for source_row in ranking_df.to_dict(orient="records"):
        family_key = _to_text(source_row.get("family_id"))
        if not family_key:
            continue
        patch_row = patch_map.get(family_key, {})
        correction_row = correction_map.get(family_key, {})
        patch_readiness = _to_text(patch_row.get("patch_readiness"), "unknown")
        correction_selected_for_patch = _to_bool(correction_row.get("selected_for_patch"))
        priority_tier = _to_text(source_row.get("correction_priority_tier") or source_row.get("priority_tier"), "hold")
        selected_for_shadow = bool(
            correction_selected_for_patch
            or (
                priority_tier in {"P1", "P2"}
                and patch_readiness not in {"blocked", "unknown"}
            )
        )
        recommended_next_action = _to_text(source_row.get("recommended_next_action"))
        family_disposition = _to_text(source_row.get("family_disposition"))
        candidate_kind = _candidate_kind(
            family_disposition=family_disposition,
            patch_draft_status=_to_text(patch_row.get("patch_draft_status")),
            recommended_next_action=recommended_next_action,
            selected_for_shadow=selected_for_shadow,
        )
        bridge_status = _bridge_status(
            selected_for_shadow=selected_for_shadow,
            patch_readiness=patch_readiness,
            family_disposition=family_disposition,
            recommended_next_action=recommended_next_action,
        )
        slug = _slugify(family_key)
        rows.append(
            {
                "shadow_candidate_id": f"shadow_candidate::{family_key}",
                "created_at": created_at,
                "family_key": family_key,
                "miss_type": _to_text(source_row.get("miss_type")),
                "primary_correction_target": _to_text(source_row.get("primary_correction_target")),
                "manual_wait_teacher_family": _to_text(source_row.get("manual_wait_teacher_family")),
                "heuristic_wait_family": _to_text(source_row.get("heuristic_wait_family")),
                "heuristic_barrier_main_label": _to_text(source_row.get("heuristic_barrier_main_label")),
                "case_count": _to_int(source_row.get("case_count")),
                "correction_worthy_case_count": _to_int(source_row.get("correction_worthy_case_count")),
                "freeze_worthy_case_count": _to_int(source_row.get("freeze_worthy_case_count")),
                "hold_for_more_truth_case_count": _to_int(source_row.get("hold_for_more_truth_case_count")),
                "ready_case_count": _to_int(source_row.get("ready_case_count")),
                "priority_tier": priority_tier,
                "recommended_next_action": recommended_next_action,
                "family_disposition": family_disposition,
                "baseline_mode": "baseline",
                "shadow_mode": "shadow_auto",
                "correction_candidate_id": _to_text(correction_row.get("run_candidate_id")),
                "correction_selected_for_patch": correction_selected_for_patch,
                "correction_selection_reason": _to_text(correction_row.get("selection_reason")),
                "patch_draft_id": _to_text(patch_row.get("patch_draft_id")),
                "patch_draft_status": _to_text(patch_row.get("patch_draft_status")),
                "patch_readiness": patch_readiness,
                "patch_version": f"shadow_patch::{slug}::v0",
                "candidate_kind": candidate_kind,
                "selected_for_shadow": selected_for_shadow,
                "selection_reason": _selection_reason(
                    selected_for_shadow=selected_for_shadow,
                    correction_selected_for_patch=correction_selected_for_patch,
                    patch_readiness=patch_readiness,
                    recommended_next_action=recommended_next_action,
                ),
                "bridge_status": bridge_status,
            }
        )

    bridge = pd.DataFrame(rows, columns=SHADOW_AUTO_CANDIDATE_COLUMNS)
    summary = {
        "shadow_candidate_bridge_version": SHADOW_AUTO_CANDIDATE_BRIDGE_VERSION,
        "generated_at": created_at,
        "candidate_count": int(len(bridge)),
        "selected_for_shadow_count": int(bridge["selected_for_shadow"].fillna(False).astype(bool).sum()) if not bridge.empty else 0,
        "bridge_status_counts": bridge["bridge_status"].value_counts().to_dict() if not bridge.empty else {},
        "candidate_kind_counts": bridge["candidate_kind"].value_counts().to_dict() if not bridge.empty else {},
        "selected_candidate_ids": bridge.loc[bridge["selected_for_shadow"].fillna(False), "shadow_candidate_id"].astype(str).tolist()
        if not bridge.empty
        else [],
    }
    return bridge, summary


def render_shadow_auto_candidate_bridge_markdown(summary: dict[str, Any], bridge: pd.DataFrame) -> str:
    lines = [
        "# Shadow Auto Candidate Bridge",
        "",
        f"- version: `{summary.get('shadow_candidate_bridge_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- selected_for_shadow_count: `{summary.get('selected_for_shadow_count', 0)}`",
        "",
        "## Status Counts",
        "",
        f"- bridge_status_counts: `{summary.get('bridge_status_counts', {})}`",
        f"- candidate_kind_counts: `{summary.get('candidate_kind_counts', {})}`",
        "",
        "## Top Candidates",
        "",
    ]
    if bridge.empty:
        lines.append("- no shadow candidates available")
        return "\n".join(lines) + "\n"

    for row in bridge.head(5).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('family_key', '')}",
                "",
                f"- candidate_kind: `{row.get('candidate_kind', '')}`",
                f"- bridge_status: `{row.get('bridge_status', '')}`",
                f"- priority_tier: `{row.get('priority_tier', '')}`",
                f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                f"- selected_for_shadow: `{row.get('selected_for_shadow', False)}`",
                f"- selection_reason: `{row.get('selection_reason', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
