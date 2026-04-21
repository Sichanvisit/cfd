"""Runtime mode contract for the shadow auto system."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.services.trade_csv_schema import now_kst_dt


SHADOW_AUTO_RUNTIME_MODE_VERSION = "shadow_auto_runtime_mode_v0"

SHADOW_AUTO_RUNTIME_MODE_COLUMNS = [
    "mode",
    "mode_role",
    "live_execution_authority",
    "live_trade_mutation_allowed",
    "shadow_candidate_execution_allowed",
    "calibration_input_allowed",
    "approval_required",
    "decision_log_marker_runtime_mode",
    "decision_log_marker_candidate_id",
    "decision_log_marker_patch_version",
    "mode_contract_status",
    "description",
]


def build_shadow_auto_runtime_mode_contract() -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = [
        {
            "mode": "baseline",
            "mode_role": "live_reference",
            "live_execution_authority": True,
            "live_trade_mutation_allowed": True,
            "shadow_candidate_execution_allowed": False,
            "calibration_input_allowed": True,
            "approval_required": False,
            "decision_log_marker_runtime_mode": "baseline",
            "decision_log_marker_candidate_id": "",
            "decision_log_marker_patch_version": "",
            "mode_contract_status": "active_live_reference",
            "description": "Current production execution owner. Keeps live authority and acts as the reference lane.",
        },
        {
            "mode": "shadow_auto",
            "mode_role": "non_live_shadow_lane",
            "live_execution_authority": False,
            "live_trade_mutation_allowed": False,
            "shadow_candidate_execution_allowed": True,
            "calibration_input_allowed": True,
            "approval_required": True,
            "decision_log_marker_runtime_mode": "shadow_auto",
            "decision_log_marker_candidate_id": "shadow_candidate_id",
            "decision_log_marker_patch_version": "shadow_patch_version",
            "mode_contract_status": "non_live_parallel_evaluation_only",
            "description": "Parallel non-live lane that may execute candidate patches for evaluation only.",
        },
    ]
    contract = pd.DataFrame(rows, columns=SHADOW_AUTO_RUNTIME_MODE_COLUMNS)
    summary = {
        "shadow_runtime_mode_version": SHADOW_AUTO_RUNTIME_MODE_VERSION,
        "generated_at": now_kst_dt().isoformat(),
        "runtime_mode_count": int(len(contract)),
        "live_authority_modes": ["baseline"],
        "shadow_modes": ["shadow_auto"],
        "decision_log_marker_runtime_mode": "shadow_runtime_mode",
        "decision_log_marker_candidate_id": "shadow_candidate_id",
        "decision_log_marker_patch_version": "shadow_patch_version",
        "contract_status": "baseline_live_shadow_non_live",
    }
    return contract, summary


def render_shadow_auto_runtime_mode_markdown(summary: dict[str, Any], contract: pd.DataFrame) -> str:
    lines = [
        "# Shadow Auto Runtime Mode Contract",
        "",
        f"- version: `{summary.get('shadow_runtime_mode_version', '')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- contract_status: `{summary.get('contract_status', '')}`",
        "",
        "## Modes",
        "",
    ]
    if contract.empty:
        lines.append("- no runtime modes available")
        return "\n".join(lines) + "\n"

    for row in contract.to_dict(orient="records"):
        lines.extend(
            [
                f"### {row.get('mode', '')}",
                "",
                f"- role: `{row.get('mode_role', '')}`",
                f"- live_execution_authority: `{row.get('live_execution_authority', False)}`",
                f"- shadow_candidate_execution_allowed: `{row.get('shadow_candidate_execution_allowed', False)}`",
                f"- approval_required: `{row.get('approval_required', False)}`",
                f"- decision markers: `runtime={row.get('decision_log_marker_runtime_mode', '')}` / "
                f"`candidate={row.get('decision_log_marker_candidate_id', '')}` / "
                f"`patch={row.get('decision_log_marker_patch_version', '')}`",
                f"- description: {row.get('description', '')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
