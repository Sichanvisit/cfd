"""Promote an approved bounded semantic shadow candidate into the active runtime when idle."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SEMANTIC_SHADOW_ACTIVE_RUNTIME_ACTIVATION_VERSION = "semantic_shadow_active_runtime_activation_v0"
SEMANTIC_SHADOW_ACTIVE_RUNTIME_ACTIVATION_COLUMNS = [
    "activation_event_id",
    "generated_at",
    "approval_status",
    "approval_decision",
    "decision_by",
    "decision_at",
    "runtime_updated_at",
    "runtime_idle_flag",
    "open_positions_count",
    "force_activate",
    "override_reason",
    "semantic_live_mode",
    "approved_model_dir",
    "active_model_dir",
    "backup_dir",
    "activation_status",
    "backup_file_count",
    "activated_file_count",
    "activation_manifest_path",
    "recommended_next_action",
]


def load_semantic_shadow_active_runtime_activation_frame(path: str | Path) -> pd.DataFrame:
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


def _copy_files(source_dir: Path, target_dir: Path) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if not source_dir.exists():
        return copied
    for source in sorted(source_dir.iterdir()):
        if not source.is_file():
            continue
        target = target_dir / source.name
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _extract_runtime_state(runtime_status: Mapping[str, Any]) -> tuple[str, bool, int, str]:
    runtime_updated_at = _to_text(runtime_status.get("updated_at", ""), "")
    semantic_live_config = runtime_status.get("semantic_live_config", {})
    semantic_live_mode = _to_text(
        semantic_live_config.get("mode", "") if isinstance(semantic_live_config, Mapping) else "",
        "",
    )
    runtime_recycle = runtime_status.get("runtime_recycle", {})
    open_positions_count = 0
    if isinstance(runtime_recycle, Mapping):
        try:
            open_positions_count = int(runtime_recycle.get("last_open_positions_count", 0) or 0)
        except Exception:
            open_positions_count = 0
    runtime_idle_flag = open_positions_count <= 0
    return runtime_updated_at, runtime_idle_flag, open_positions_count, semantic_live_mode


def _write_activation_manifest(active_model_dir: Path, payload: Mapping[str, Any]) -> Path:
    manifest_path = active_model_dir / "semantic_shadow_active_runtime_activation_manifest.json"
    manifest_path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def build_semantic_shadow_active_runtime_activation(
    approval_frame: pd.DataFrame | None,
    *,
    runtime_status: Mapping[str, Any] | None,
    active_model_dir: str | Path,
    backup_root_dir: str | Path,
    force_activate: bool = False,
    override_reason: str = "",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    now = now_kst_dt().isoformat()
    approval_row = approval_frame.iloc[0].to_dict() if approval_frame is not None and not approval_frame.empty else {}
    approval_status = _to_text(approval_row.get("approval_status", ""), "")
    approval_decision = _to_text(approval_row.get("approval_decision", ""), "")
    decision_by = _to_text(approval_row.get("decision_by", ""), "")
    decision_at = _to_text(approval_row.get("decision_at", ""), "")
    approved_model_dir = Path(_to_text(approval_row.get("approved_model_dir", ""), ""))
    active_dir = Path(active_model_dir)
    backup_root = Path(backup_root_dir)

    runtime_updated_at, runtime_idle_flag, open_positions_count, semantic_live_mode = _extract_runtime_state(
        dict(runtime_status or {})
    )
    override_reason_text = _to_text(override_reason, "")
    backup_dir: Path | None = None
    backup_files: list[str] = []
    activated_files: list[str] = []
    activation_manifest_path: Path | None = None

    if approval_status != "approved_pending_activation":
        activation_status = "awaiting_approved_pending_activation"
        recommended_next_action = _to_text(approval_row.get("recommended_next_action", ""), "keep_preview_only")
    elif not approved_model_dir.exists():
        activation_status = "approved_bundle_missing"
        recommended_next_action = "rebuild_or_reapprove_bounded_candidate"
    elif not runtime_idle_flag and not force_activate:
        activation_status = "blocked_runtime_not_idle"
        recommended_next_action = "wait_for_runtime_idle_then_retry_activation"
    else:
        if active_dir.exists():
            backup_dir = backup_root / f"semantic_v1_backup_{now_kst_dt().strftime('%Y%m%d_%H%M%S')}"
            backup_files = _copy_files(active_dir, backup_dir)
        if active_dir.exists():
            for child in sorted(active_dir.iterdir()):
                if child.is_file():
                    child.unlink()
        activated_files = _copy_files(approved_model_dir, active_dir)
        activation_manifest_path = _write_activation_manifest(
            active_dir,
            {
                "semantic_shadow_active_runtime_activation_version": SEMANTIC_SHADOW_ACTIVE_RUNTIME_ACTIVATION_VERSION,
                "generated_at": now,
                "approval_status": approval_status,
                "approval_decision": approval_decision,
                "decision_by": decision_by,
                "decision_at": decision_at,
                "runtime_updated_at": runtime_updated_at,
                "runtime_idle_flag": runtime_idle_flag,
                "open_positions_count": open_positions_count,
                "force_activate": bool(force_activate),
                "override_reason": override_reason_text,
                "semantic_live_mode": semantic_live_mode,
                "approved_model_dir": str(approved_model_dir),
                "active_model_dir": str(active_dir),
                "backup_dir": str(backup_dir) if backup_dir is not None else "",
                "backup_file_count": len(backup_files),
                "activated_files": activated_files,
                "activated_file_count": len(activated_files),
                "recommended_next_action": "refresh_runtime_and_verify_semantic_shadow_loaded",
            },
        )
        activation_status = "activated_candidate_runtime_forced" if force_activate and not runtime_idle_flag else "activated_candidate_runtime"
        recommended_next_action = "refresh_runtime_and_verify_semantic_shadow_loaded"

    frame = pd.DataFrame(
        [
            {
                "activation_event_id": "semantic_shadow_active_runtime_activation::0001",
                "generated_at": now,
                "approval_status": approval_status,
                "approval_decision": approval_decision,
                "decision_by": decision_by,
                "decision_at": decision_at,
                "runtime_updated_at": runtime_updated_at,
                "runtime_idle_flag": bool(runtime_idle_flag),
                "open_positions_count": int(open_positions_count),
                "force_activate": bool(force_activate),
                "override_reason": override_reason_text,
                "semantic_live_mode": semantic_live_mode,
                "approved_model_dir": str(approved_model_dir),
                "active_model_dir": str(active_dir),
                "backup_dir": str(backup_dir) if backup_dir else "",
                "activation_status": activation_status,
                "backup_file_count": int(len(backup_files)),
                "activated_file_count": int(len(activated_files)),
                "activation_manifest_path": str(activation_manifest_path) if activation_manifest_path is not None else "",
                "recommended_next_action": recommended_next_action,
            }
        ],
        columns=SEMANTIC_SHADOW_ACTIVE_RUNTIME_ACTIVATION_COLUMNS,
    )
    summary = {
        "semantic_shadow_active_runtime_activation_version": SEMANTIC_SHADOW_ACTIVE_RUNTIME_ACTIVATION_VERSION,
        "generated_at": now,
        "activation_status_counts": frame["activation_status"].value_counts().to_dict() if not frame.empty else {},
        "runtime_idle_count": int(frame["runtime_idle_flag"].sum()) if not frame.empty else 0,
    }
    return frame, summary


def render_semantic_shadow_active_runtime_activation_markdown(
    summary: Mapping[str, Any],
    frame: pd.DataFrame,
) -> str:
    row = frame.iloc[0].to_dict() if not frame.empty else {}
    lines = [
        "# Semantic Shadow Active Runtime Activation",
        "",
        f"- version: `{summary.get('semantic_shadow_active_runtime_activation_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- approval_status: `{row.get('approval_status', '')}`",
        f"- activation_status: `{row.get('activation_status', '')}`",
        f"- runtime_idle_flag: `{row.get('runtime_idle_flag', False)}`",
        f"- open_positions_count: `{row.get('open_positions_count', 0)}`",
        f"- force_activate: `{row.get('force_activate', False)}`",
        f"- override_reason: `{row.get('override_reason', '')}`",
        f"- semantic_live_mode: `{row.get('semantic_live_mode', '')}`",
        f"- backup_file_count: `{row.get('backup_file_count', 0)}`",
        f"- activated_file_count: `{row.get('activated_file_count', 0)}`",
        f"- activation_manifest_path: `{row.get('activation_manifest_path', '')}`",
        f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"
