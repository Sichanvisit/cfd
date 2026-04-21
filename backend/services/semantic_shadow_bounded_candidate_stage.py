"""Stage a bounded semantic shadow candidate runtime for human approval."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SEMANTIC_SHADOW_BOUNDED_CANDIDATE_STAGE_VERSION = "semantic_shadow_bounded_candidate_stage_v0"
SEMANTIC_SHADOW_BOUNDED_CANDIDATE_STAGE_COLUMNS = [
    "stage_event_id",
    "generated_at",
    "selected_sweep_profile_id",
    "preview_model_dir",
    "candidate_stage_dir",
    "activation_ready_flag",
    "gate_decision",
    "preview_decision",
    "value_diff",
    "manual_alignment_improvement",
    "drawdown_diff",
    "stage_status",
    "staged_file_count",
    "approval_required",
    "candidate_manifest_path",
    "approval_packet_path",
    "recommended_next_action",
]


def load_semantic_shadow_bounded_candidate_stage_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _copy_preview_bundle(preview_model_dir: Path, candidate_stage_dir: Path) -> list[str]:
    candidate_stage_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if not preview_model_dir.exists():
        return copied
    for source in sorted(preview_model_dir.iterdir()):
        if not source.is_file():
            continue
        target = candidate_stage_dir / source.name
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _write_stage_artifacts(
    *,
    candidate_stage_dir: Path,
    stage_payload: dict[str, Any],
) -> tuple[Path, Path]:
    manifest_path = candidate_stage_dir / "semantic_shadow_bounded_candidate_manifest.json"
    approval_packet_path = candidate_stage_dir / "semantic_shadow_bounded_candidate_approval.md"
    manifest_path.write_text(json.dumps(stage_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Semantic Shadow Bounded Candidate Approval Packet",
        "",
        f"- generated_at: `{stage_payload.get('generated_at', '')}`",
        f"- selected_sweep_profile_id: `{stage_payload.get('selected_sweep_profile_id', '')}`",
        f"- preview_decision: `{stage_payload.get('preview_decision', '')}`",
        f"- gate_decision: `{stage_payload.get('gate_decision', '')}`",
        f"- value_diff: `{stage_payload.get('value_diff', 0.0)}`",
        f"- manual_alignment_improvement: `{stage_payload.get('manual_alignment_improvement', 0.0)}`",
        f"- drawdown_diff: `{stage_payload.get('drawdown_diff', 0.0)}`",
        f"- staged_file_count: `{stage_payload.get('staged_file_count', 0)}`",
        "",
        "## Recommendation",
        "",
        f"- next_action: `{stage_payload.get('recommended_next_action', '')}`",
        "- approval_note: `review candidate runtime package and approve or reject bounded live staging`",
        "",
    ]
    approval_packet_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path, approval_packet_path


def build_semantic_shadow_bounded_candidate_stage(
    readiness: pd.DataFrame | None,
    *,
    preview_bundle_summary: Mapping[str, Any] | None = None,
    bounded_gate: pd.DataFrame | None = None,
    first_non_hold: pd.DataFrame | None = None,
    execution_evaluation: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    readiness_row = readiness.iloc[0].to_dict() if readiness is not None and not readiness.empty else {}
    gate_row = bounded_gate.iloc[0].to_dict() if bounded_gate is not None and not bounded_gate.empty else {}
    decision_row = first_non_hold.iloc[0].to_dict() if first_non_hold is not None and not first_non_hold.empty else {}
    evaluation_row = execution_evaluation.iloc[0].to_dict() if execution_evaluation is not None and not execution_evaluation.empty else {}
    preview_summary = dict(preview_bundle_summary or {})

    preview_model_dir = Path(str(readiness_row.get("preview_model_dir", "") or ""))
    candidate_stage_dir = Path(str(readiness_row.get("candidate_stage_dir", "") or ""))
    activation_ready_flag = str(readiness_row.get("activation_ready_flag", "")).lower() in {"true", "1", "yes"}
    preview_bundle_ready = bool(preview_summary.get("bundle_ready", False))
    gate_decision = str(gate_row.get("gate_decision", "") or "")
    preview_decision = str(decision_row.get("decision", "") or "")
    value_diff = float(evaluation_row.get("value_diff", decision_row.get("value_diff_proxy", 0.0)) or 0.0)
    manual_alignment_improvement = float(
        evaluation_row.get("manual_alignment_improvement", decision_row.get("manual_alignment_improvement", 0.0)) or 0.0
    )
    drawdown_diff = float(evaluation_row.get("drawdown_diff", decision_row.get("drawdown_diff", 0.0)) or 0.0)
    selected_sweep_profile_id = str(
        decision_row.get("selected_sweep_profile_id", gate_row.get("selected_sweep_profile_id", "")) or ""
    )

    staged_files: list[str] = []
    candidate_manifest_path = Path()
    approval_packet_path = Path()
    if not activation_ready_flag or gate_decision != "ALLOW_BOUNDED_LIVE_CANDIDATE":
        stage_status = "blocked_before_stage"
        approval_required = False
        recommended_next_action = str(readiness_row.get("recommended_next_action", "") or "keep_preview_only")
    elif not preview_bundle_ready or not preview_model_dir.exists():
        stage_status = "preview_bundle_missing"
        approval_required = False
        recommended_next_action = "rebuild_preview_bundle_before_stage"
    else:
        staged_files = _copy_preview_bundle(preview_model_dir, candidate_stage_dir)
        stage_payload = {
            "semantic_shadow_bounded_candidate_stage_version": SEMANTIC_SHADOW_BOUNDED_CANDIDATE_STAGE_VERSION,
            "generated_at": now,
            "selected_sweep_profile_id": selected_sweep_profile_id,
            "preview_model_dir": str(preview_model_dir),
            "candidate_stage_dir": str(candidate_stage_dir),
            "preview_decision": preview_decision,
            "gate_decision": gate_decision,
            "value_diff": round(value_diff, 6),
            "manual_alignment_improvement": round(manual_alignment_improvement, 6),
            "drawdown_diff": round(drawdown_diff, 6),
            "staged_files": staged_files,
            "staged_file_count": len(staged_files),
            "recommended_next_action": "collect_human_approval_for_bounded_live_candidate",
        }
        candidate_manifest_path, approval_packet_path = _write_stage_artifacts(
            candidate_stage_dir=candidate_stage_dir,
            stage_payload=stage_payload,
        )
        stage_status = "candidate_runtime_staged"
        approval_required = True
        recommended_next_action = "collect_human_approval_for_bounded_live_candidate"

    frame = pd.DataFrame(
        [
            {
                "stage_event_id": "semantic_shadow_stage::0001",
                "generated_at": now,
                "selected_sweep_profile_id": selected_sweep_profile_id,
                "preview_model_dir": str(preview_model_dir),
                "candidate_stage_dir": str(candidate_stage_dir),
                "activation_ready_flag": bool(activation_ready_flag),
                "gate_decision": gate_decision,
                "preview_decision": preview_decision,
                "value_diff": round(value_diff, 6),
                "manual_alignment_improvement": round(manual_alignment_improvement, 6),
                "drawdown_diff": round(drawdown_diff, 6),
                "stage_status": stage_status,
                "staged_file_count": int(len(staged_files)),
                "approval_required": bool(approval_required),
                "candidate_manifest_path": str(candidate_manifest_path) if candidate_manifest_path else "",
                "approval_packet_path": str(approval_packet_path) if approval_packet_path else "",
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SEMANTIC_SHADOW_BOUNDED_CANDIDATE_STAGE_COLUMNS,
    )
    summary = {
        "semantic_shadow_bounded_candidate_stage_version": SEMANTIC_SHADOW_BOUNDED_CANDIDATE_STAGE_VERSION,
        "generated_at": now,
        "stage_status_counts": frame["stage_status"].value_counts().to_dict() if not frame.empty else {},
        "approval_required_count": int(frame["approval_required"].sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_semantic_shadow_bounded_candidate_stage_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Shadow Bounded Candidate Stage",
        "",
        f"- version: `{summary.get('semantic_shadow_bounded_candidate_stage_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- stage_status: `{row.get('stage_status', '')}`",
        f"- preview_decision: `{row.get('preview_decision', '')}`",
        f"- gate_decision: `{row.get('gate_decision', '')}`",
        f"- activation_ready_flag: `{row.get('activation_ready_flag', False)}`",
        f"- staged_file_count: `{row.get('staged_file_count', 0)}`",
        f"- approval_required: `{row.get('approval_required', False)}`",
        f"- candidate_manifest_path: `{row.get('candidate_manifest_path', '')}`",
        f"- approval_packet_path: `{row.get('approval_packet_path', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
