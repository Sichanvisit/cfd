"""Human approval workflow for staged bounded semantic shadow candidates."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SEMANTIC_SHADOW_BOUNDED_CANDIDATE_APPROVAL_VERSION = "semantic_shadow_bounded_candidate_approval_v0"
SEMANTIC_SHADOW_BOUNDED_CANDIDATE_APPROVAL_COLUMNS = [
    "approval_event_id",
    "generated_at",
    "stage_event_id",
    "selected_sweep_profile_id",
    "stage_status",
    "approval_required",
    "approval_entry_count",
    "approval_status",
    "approval_decision",
    "decision_by",
    "decision_at",
    "reason_code",
    "reason_summary",
    "preview_decision",
    "gate_decision",
    "value_diff",
    "manual_alignment_improvement",
    "drawdown_diff",
    "candidate_stage_dir",
    "approved_model_dir",
    "approved_file_count",
    "activation_manifest_path",
    "recommended_next_action",
]


def load_semantic_shadow_bounded_candidate_approval_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return str(default or "")
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else str(default or "")


def _normalize_decision(value: object) -> str:
    decision = _to_text(value, "").upper()
    if decision in {"APPROVE", "REJECT", "HOLD"}:
        return decision
    return ""


def _reason_code(value: object) -> str:
    text = _to_text(value, "")
    if "::" in text:
        return text.split("::", 1)[0]
    return text or "unspecified"


def _copy_stage_bundle(candidate_stage_dir: Path, approved_model_dir: Path) -> list[str]:
    approved_model_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if not candidate_stage_dir.exists():
        return copied
    for source in sorted(candidate_stage_dir.iterdir()):
        if not source.is_file():
            continue
        target = approved_model_dir / source.name
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _write_activation_manifest(
    approved_model_dir: Path,
    payload: Mapping[str, Any],
) -> Path:
    manifest_path = approved_model_dir / "semantic_shadow_bounded_candidate_activation_manifest.json"
    manifest_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def _select_latest_entry(entries: pd.DataFrame, stage_event_id: str) -> pd.Series | None:
    if entries is None or entries.empty:
        return None
    scoped = entries.copy()
    if "stage_event_id" in scoped.columns:
        scoped = scoped[scoped["stage_event_id"].fillna("").astype(str) == stage_event_id]
    if scoped.empty:
        return None
    if "decision_at" in scoped.columns:
        scoped["decision_at_sort"] = pd.to_datetime(scoped["decision_at"], errors="coerce")
        scoped = scoped.sort_values(
            by=["decision_at_sort"],
            ascending=[False],
            kind="stable",
            na_position="last",
        ).drop(columns=["decision_at_sort"])
    return scoped.iloc[0]


def build_semantic_shadow_bounded_candidate_approval(
    stage_frame: pd.DataFrame | None,
    approval_entries: pd.DataFrame | None,
    *,
    approved_model_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    stage_row = stage_frame.iloc[0].to_dict() if stage_frame is not None and not stage_frame.empty else {}
    stage_status = _to_text(stage_row.get("stage_status", ""), "")
    stage_event_id = _to_text(stage_row.get("stage_event_id", ""), "")
    stage_required = str(stage_row.get("approval_required", "")).lower() in {"true", "1", "yes"}
    stage_dir = Path(_to_text(stage_row.get("candidate_stage_dir", ""), ""))
    approved_dir = Path(approved_model_dir)
    entry = _select_latest_entry(approval_entries if approval_entries is not None else pd.DataFrame(), stage_event_id)
    approval_entry_count = 0 if approval_entries is None or approval_entries.empty else int(
        approval_entries[
            approval_entries.get("stage_event_id", pd.Series(dtype=str)).fillna("").astype(str) == stage_event_id
        ].shape[0]
    ) if stage_event_id and approval_entries is not None and "stage_event_id" in approval_entries.columns else int(
        len(approval_entries if approval_entries is not None else pd.DataFrame())
    )

    approval_decision = _normalize_decision(entry.get("decision", "")) if entry is not None else ""
    decision_by = _to_text(entry.get("decision_by", ""), "") if entry is not None else ""
    decision_at = _to_text(entry.get("decision_at", ""), "") if entry is not None else ""
    reason_summary = _to_text(entry.get("reason_summary", ""), "") if entry is not None else ""
    reason_code = _reason_code(reason_summary) if reason_summary else ""

    activation_manifest_path: Path | None = None
    approved_files: list[str] = []
    if stage_status != "candidate_runtime_staged" or not stage_required:
        approval_status = "stage_unavailable"
        recommended_next_action = _to_text(stage_row.get("recommended_next_action", ""), "keep_preview_only")
    elif approval_decision == "APPROVE":
        approved_files = _copy_stage_bundle(stage_dir, approved_dir)
        activation_manifest_path = _write_activation_manifest(
            approved_dir,
            {
                "semantic_shadow_bounded_candidate_approval_version": SEMANTIC_SHADOW_BOUNDED_CANDIDATE_APPROVAL_VERSION,
                "generated_at": now,
                "stage_event_id": stage_event_id,
                "selected_sweep_profile_id": _to_text(stage_row.get("selected_sweep_profile_id", ""), ""),
                "approval_decision": approval_decision,
                "decision_by": decision_by,
                "decision_at": decision_at,
                "reason_summary": reason_summary,
                "preview_decision": _to_text(stage_row.get("preview_decision", ""), ""),
                "gate_decision": _to_text(stage_row.get("gate_decision", ""), ""),
                "value_diff": float(stage_row.get("value_diff", 0.0) or 0.0),
                "manual_alignment_improvement": float(stage_row.get("manual_alignment_improvement", 0.0) or 0.0),
                "drawdown_diff": float(stage_row.get("drawdown_diff", 0.0) or 0.0),
                "approved_files": approved_files,
                "approved_file_count": len(approved_files),
                "recommended_next_action": "activate_bounded_candidate_when_runtime_is_idle",
            },
        )
        approval_status = "approved_pending_activation"
        recommended_next_action = "activate_bounded_candidate_when_runtime_is_idle"
    elif approval_decision == "REJECT":
        approval_status = "rejected_candidate"
        recommended_next_action = "keep_preview_only_and_collect_rejection_followup"
    elif approval_decision == "HOLD":
        approval_status = "hold_candidate"
        recommended_next_action = "request_additional_human_review"
    else:
        approval_status = "pending_human_review"
        recommended_next_action = "fill_shadow_bounded_candidate_approval_entry"

    frame = pd.DataFrame(
        [
            {
                "approval_event_id": "semantic_shadow_bounded_candidate_approval::0001",
                "generated_at": now,
                "stage_event_id": stage_event_id,
                "selected_sweep_profile_id": _to_text(stage_row.get("selected_sweep_profile_id", ""), ""),
                "stage_status": stage_status,
                "approval_required": bool(stage_required),
                "approval_entry_count": approval_entry_count,
                "approval_status": approval_status,
                "approval_decision": approval_decision,
                "decision_by": decision_by,
                "decision_at": decision_at,
                "reason_code": reason_code,
                "reason_summary": reason_summary,
                "preview_decision": _to_text(stage_row.get("preview_decision", ""), ""),
                "gate_decision": _to_text(stage_row.get("gate_decision", ""), ""),
                "value_diff": round(float(stage_row.get("value_diff", 0.0) or 0.0), 6),
                "manual_alignment_improvement": round(float(stage_row.get("manual_alignment_improvement", 0.0) or 0.0), 6),
                "drawdown_diff": round(float(stage_row.get("drawdown_diff", 0.0) or 0.0), 6),
                "candidate_stage_dir": str(stage_dir),
                "approved_model_dir": str(approved_dir),
                "approved_file_count": int(len(approved_files)),
                "activation_manifest_path": str(activation_manifest_path) if activation_manifest_path is not None else "",
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SEMANTIC_SHADOW_BOUNDED_CANDIDATE_APPROVAL_COLUMNS,
    )
    summary = {
        "semantic_shadow_bounded_candidate_approval_version": SEMANTIC_SHADOW_BOUNDED_CANDIDATE_APPROVAL_VERSION,
        "generated_at": now,
        "approval_status_counts": frame["approval_status"].value_counts().to_dict() if not frame.empty else {},
        "approval_decision_counts": frame["approval_decision"].replace("", "NONE").value_counts().to_dict()
        if not frame.empty
        else {},
    }
    return frame, summary


def render_semantic_shadow_bounded_candidate_approval_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Shadow Bounded Candidate Approval",
        "",
        f"- version: `{summary.get('semantic_shadow_bounded_candidate_approval_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- approval_status: `{row.get('approval_status', '')}`",
        f"- approval_decision: `{row.get('approval_decision', '')}`",
        f"- decision_by: `{row.get('decision_by', '')}`",
        f"- decision_at: `{row.get('decision_at', '')}`",
        f"- preview_decision: `{row.get('preview_decision', '')}`",
        f"- gate_decision: `{row.get('gate_decision', '')}`",
        f"- approved_file_count: `{row.get('approved_file_count', 0)}`",
        f"- activation_manifest_path: `{row.get('activation_manifest_path', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
