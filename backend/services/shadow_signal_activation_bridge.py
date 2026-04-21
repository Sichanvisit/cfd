"""Bridge candidate overlap with shadow activation availability blockers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt
from ml.semantic_v1.evaluate import DEFAULT_MODEL_DIR
from ml.semantic_v1.runtime_adapter import MODEL_FILE_MAP


SHADOW_SIGNAL_ACTIVATION_BRIDGE_VERSION = "shadow_signal_activation_bridge_v0"

SHADOW_SIGNAL_ACTIVATION_BRIDGE_COLUMNS = [
    "shadow_candidate_id",
    "family_key",
    "manual_wait_teacher_family",
    "candidate_kind",
    "bridge_status",
    "observed_overlap_rows",
    "family_overlap_rows",
    "manual_reference_rows",
    "shadow_available_rows",
    "candidate_precedence_blocked",
    "activation_state_counts",
    "activation_reason_counts",
    "dominant_activation_state",
    "dominant_activation_reason",
    "model_dir",
    "model_dir_exists",
    "timing_model_exists",
    "entry_quality_model_exists",
    "exit_management_model_exists",
    "available_bundle_count",
    "preview_bundle_ready",
    "preview_bundle_dir_count",
    "effective_runtime_stage",
    "activation_bridge_status",
    "availability_gap_summary",
    "recommended_next_action",
]


def _to_text(value: object, default: str = "") -> str:
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    text = str(value or "").strip()
    return text if text else default


def _to_bool(value: object, default: bool = False) -> bool:
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return bool(default)


def load_shadow_signal_bridge_frame(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(csv_path, low_memory=False)


def _bundle_inventory(model_dir: Path) -> dict[str, Any]:
    timing_path = model_dir / MODEL_FILE_MAP["timing"]
    entry_path = model_dir / MODEL_FILE_MAP["entry_quality"]
    exit_path = model_dir / MODEL_FILE_MAP["exit_management"]
    return {
        "model_dir": str(model_dir),
        "model_dir_exists": model_dir.exists(),
        "timing_model_exists": timing_path.exists(),
        "entry_quality_model_exists": entry_path.exists(),
        "exit_management_model_exists": exit_path.exists(),
        "available_bundle_count": int(sum(path.exists() for path in [timing_path, entry_path, exit_path])),
    }


def _discover_preview_bundle_dirs(models_root: Path, active_model_dir: Path) -> list[Path]:
    if not models_root.exists():
        return []
    required = list(MODEL_FILE_MAP.values())
    parents: dict[Path, set[str]] = {}
    for file_name in required:
        for path in models_root.rglob(file_name):
            parent = path.parent
            if parent == active_model_dir:
                continue
            parents.setdefault(parent, set()).add(file_name)
    return sorted(parent for parent, files in parents.items() if all(name in files for name in required))


def _dominant_count_label(series: pd.Series) -> tuple[str, dict[str, int]]:
    values = series.fillna("").astype(str).replace({"": "none"})
    counts = values.value_counts().to_dict()
    if not counts:
        return "none", {}
    dominant = max(counts.items(), key=lambda item: item[1])[0]
    return str(dominant), {str(k): int(v) for k, v in counts.items()}


def _activation_bridge_status(
    *,
    observed_overlap_rows: int,
    family_overlap_rows: int,
    shadow_available_rows: int,
    dominant_activation_reason: str,
    available_bundle_count: int,
    preview_bundle_ready: bool,
) -> str:
    if observed_overlap_rows == 0 and family_overlap_rows > 0:
        return "candidate_precedence_blocked"
    if observed_overlap_rows == 0:
        return "await_candidate_overlap"
    if shadow_available_rows > 0:
        return "shadow_available"
    if preview_bundle_ready and available_bundle_count == 0:
        return "preview_bundle_ready"
    if dominant_activation_reason == "model_dir_missing" or available_bundle_count == 0:
        return "model_bundle_missing"
    return "runtime_blocked"


def _availability_gap_summary(
    *,
    activation_bridge_status: str,
    inventory: dict[str, Any],
    dominant_activation_reason: str,
) -> str:
    if activation_bridge_status == "await_candidate_overlap":
        return "candidate_overlap_missing"
    if activation_bridge_status == "candidate_precedence_blocked":
        return "family_rows_claimed_by_higher_priority_candidate"
    if activation_bridge_status == "shadow_available":
        return "shadow_runtime_active"
    if activation_bridge_status == "preview_bundle_ready":
        return "preview_bundle_present_active_bundle_missing"
    if activation_bridge_status == "model_bundle_missing":
        missing = [
            key
            for key, exists in [
                ("timing", inventory["timing_model_exists"]),
                ("entry_quality", inventory["entry_quality_model_exists"]),
                ("exit_management", inventory["exit_management_model_exists"]),
            ]
            if not exists
        ]
        return "missing_models::" + "|".join(missing)
    return f"runtime_blocked::{dominant_activation_reason or 'unknown'}"


def _recommended_next_action(activation_bridge_status: str) -> str:
    mapping = {
        "await_candidate_overlap": "expand_shadow_overlap_window",
        "candidate_precedence_blocked": "keep_higher_priority_candidate_mapping",
        "shadow_available": "proceed_to_shadow_evaluation",
        "preview_bundle_ready": "continue_preview_shadow_evaluation_until_bounded_ready",
        "model_bundle_missing": "build_or_link_semantic_shadow_models",
        "runtime_blocked": "inspect_shadow_runtime_adapter",
    }
    return mapping.get(activation_bridge_status, "inspect_shadow_runtime_adapter")


def build_shadow_signal_activation_bridge(
    shadow_vs_baseline: pd.DataFrame,
    *,
    shadow_candidates: pd.DataFrame | None = None,
    model_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    compare_df = shadow_vs_baseline.copy() if shadow_vs_baseline is not None else pd.DataFrame()
    candidates_df = shadow_candidates.copy() if shadow_candidates is not None else pd.DataFrame()
    resolved_model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
    inventory = _bundle_inventory(resolved_model_dir)
    preview_bundle_dirs = _discover_preview_bundle_dirs(resolved_model_dir.parent, resolved_model_dir)
    preview_bundle_ready = bool(preview_bundle_dirs)

    rows: list[dict[str, Any]] = []
    for candidate in candidates_df.to_dict(orient="records"):
        shadow_candidate_id = _to_text(candidate.get("shadow_candidate_id"))
        manual_family = _to_text(candidate.get("manual_wait_teacher_family"))
        subset = compare_df.loc[
            compare_df.get("shadow_candidate_id", pd.Series(dtype=str)).fillna("").astype(str) == shadow_candidate_id
        ].copy()
        observed_overlap_rows = int(len(subset))
        family_overlap_rows = 0
        if manual_family:
            family_overlap_rows = int(
                compare_df.get("manual_family", pd.Series(dtype=str)).fillna("").astype(str).str.strip().str.lower().eq(manual_family.strip().lower()).sum()
            )
        manual_reference_rows = int(subset.get("manual_label", pd.Series(dtype=str)).fillna("").astype(str).ne("").sum()) if observed_overlap_rows else 0
        shadow_available_rows = int(subset.get("semantic_shadow_available", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if observed_overlap_rows else 0
        dominant_state, state_counts = _dominant_count_label(subset.get("semantic_shadow_activation_state", pd.Series(dtype=str))) if observed_overlap_rows else ("none", {})
        dominant_reason, reason_counts = _dominant_count_label(subset.get("shadow_reason", pd.Series(dtype=str))) if observed_overlap_rows else ("none", {})
        if dominant_reason in {"none", "unknown"} and observed_overlap_rows:
            dominant_reason, reason_counts = _dominant_count_label(subset.get("semantic_shadow_compare_label", pd.Series(dtype=str)))
        bridge_status = _activation_bridge_status(
            observed_overlap_rows=observed_overlap_rows,
            family_overlap_rows=family_overlap_rows,
            shadow_available_rows=shadow_available_rows,
            dominant_activation_reason=dominant_reason,
            available_bundle_count=int(inventory["available_bundle_count"]),
            preview_bundle_ready=preview_bundle_ready,
        )
        effective_runtime_stage = (
            "active"
            if bridge_status == "shadow_available"
            else ("preview_only" if bridge_status == "preview_bundle_ready" else "inactive")
        )
        rows.append(
            {
                "shadow_candidate_id": shadow_candidate_id,
                "family_key": _to_text(candidate.get("family_key")),
                "manual_wait_teacher_family": manual_family,
                "candidate_kind": _to_text(candidate.get("candidate_kind")),
                "bridge_status": _to_text(candidate.get("bridge_status")),
                "observed_overlap_rows": observed_overlap_rows,
                "family_overlap_rows": family_overlap_rows,
                "manual_reference_rows": manual_reference_rows,
                "shadow_available_rows": shadow_available_rows,
                "candidate_precedence_blocked": bool(observed_overlap_rows == 0 and family_overlap_rows > 0),
                "activation_state_counts": str(state_counts),
                "activation_reason_counts": str(reason_counts),
                "dominant_activation_state": dominant_state,
                "dominant_activation_reason": dominant_reason,
                "model_dir": inventory["model_dir"],
                "model_dir_exists": inventory["model_dir_exists"],
                "timing_model_exists": inventory["timing_model_exists"],
                "entry_quality_model_exists": inventory["entry_quality_model_exists"],
                "exit_management_model_exists": inventory["exit_management_model_exists"],
                "available_bundle_count": inventory["available_bundle_count"],
                "preview_bundle_ready": preview_bundle_ready,
                "preview_bundle_dir_count": len(preview_bundle_dirs),
                "effective_runtime_stage": effective_runtime_stage,
                "activation_bridge_status": bridge_status,
                "availability_gap_summary": _availability_gap_summary(
                    activation_bridge_status=bridge_status,
                    inventory=inventory,
                    dominant_activation_reason=dominant_reason,
                ),
                "recommended_next_action": _recommended_next_action(bridge_status),
            }
        )

    bridge = pd.DataFrame(rows, columns=SHADOW_SIGNAL_ACTIVATION_BRIDGE_COLUMNS)
    summary = {
        "shadow_signal_activation_bridge_version": SHADOW_SIGNAL_ACTIVATION_BRIDGE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "candidate_count": int(len(bridge)),
        "activation_bridge_status_counts": bridge["activation_bridge_status"].value_counts().to_dict() if not bridge.empty else {},
        "effective_runtime_stage_counts": bridge["effective_runtime_stage"].value_counts().to_dict() if not bridge.empty else {},
        "recommended_next_action_counts": bridge["recommended_next_action"].value_counts().to_dict() if not bridge.empty else {},
        "model_dir": inventory["model_dir"],
        "model_dir_exists": inventory["model_dir_exists"],
        "available_bundle_count": inventory["available_bundle_count"],
        "preview_bundle_ready": preview_bundle_ready,
        "preview_bundle_dir_count": len(preview_bundle_dirs),
    }
    return bridge, summary


def render_shadow_signal_activation_bridge_markdown(summary: dict[str, Any], bridge: pd.DataFrame) -> str:
    lines = [
        "# Shadow Signal Activation Bridge",
        "",
        f"- version: `{summary.get('shadow_signal_activation_bridge_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- model_dir: `{summary.get('model_dir', '')}`",
        f"- model_dir_exists: `{summary.get('model_dir_exists', False)}`",
        f"- available_bundle_count: `{summary.get('available_bundle_count', 0)}`",
        f"- preview_bundle_ready: `{summary.get('preview_bundle_ready', False)}`",
        f"- preview_bundle_dir_count: `{summary.get('preview_bundle_dir_count', 0)}`",
        "",
        "## Aggregate",
        "",
        f"- activation_bridge_status_counts: `{summary.get('activation_bridge_status_counts', {})}`",
        f"- effective_runtime_stage_counts: `{summary.get('effective_runtime_stage_counts', {})}`",
        f"- recommended_next_action_counts: `{summary.get('recommended_next_action_counts', {})}`",
        "",
        "## Candidate Bridge Rows",
        "",
    ]
    if bridge.empty:
        lines.append("- no activation bridge rows available")
        return "\n".join(lines) + "\n"

    for row in bridge.head(10).to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('family_key', '')}",
                "",
                f"- observed_overlap_rows: `{row.get('observed_overlap_rows', 0)}`",
                f"- family_overlap_rows: `{row.get('family_overlap_rows', 0)}`",
                f"- shadow_available_rows: `{row.get('shadow_available_rows', 0)}`",
                f"- candidate_precedence_blocked: `{row.get('candidate_precedence_blocked', False)}`",
                f"- dominant_activation_reason: `{row.get('dominant_activation_reason', '')}`",
                f"- effective_runtime_stage: `{row.get('effective_runtime_stage', '')}`",
                f"- activation_bridge_status: `{row.get('activation_bridge_status', '')}`",
                f"- recommended_next_action: `{row.get('recommended_next_action', '')}`",
                f"- availability_gap_summary: `{row.get('availability_gap_summary', '')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
