"""Recurring manual-truth calibration watch loop."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


DEFAULT_RUNTIME_STATUS_PATH = Path("data") / "runtime_status.json"
DEFAULT_OUT_DIR = Path("data") / "analysis" / "manual_truth_calibration"
DEFAULT_INTERVAL_MIN = 15.0
DEFAULT_MAX_CYCLES = 0
DEFAULT_STEP_TIMEOUT_SEC = 600.0


@dataclass(frozen=True)
class CalibrationTask:
    name: str
    script_path: Path
    description: str
    every_n_cycles: int = 1


Runner = Callable[[list[str], Path, float], subprocess.CompletedProcess[str]]


def _default_runner(command: list[str], cwd: Path, timeout_sec: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=max(1.0, float(timeout_sec)),
        check=False,
    )


def _runtime_fresh(status_file: Path, max_age_sec: float) -> tuple[bool, float]:
    try:
        mtime = float(status_file.stat().st_mtime)
    except Exception:
        return (False, float("inf"))
    age = max(0.0, time.time() - mtime)
    return (age <= max(1.0, float(max_age_sec)), age)


def build_manual_truth_calibration_tasks(root: Path) -> list[CalibrationTask]:
    scripts_dir = root / "scripts"
    return [
        CalibrationTask(
            name="barrier_outcome_bridge",
            script_path=scripts_dir / "barrier_outcome_bridge_report.py",
            description="Refresh barrier outcome bridge summary and markdown.",
            every_n_cycles=4,
        ),
        CalibrationTask(
            name="manual_vs_heuristic_archive_scan",
            script_path=scripts_dir / "build_manual_vs_heuristic_archive_scan.py",
            description="Refresh historical heuristic archive inventory.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="manual_vs_heuristic_global_detail_fallback",
            script_path=scripts_dir / "build_manual_vs_heuristic_global_detail_fallback_audit.py",
            description="Refresh global detail fallback recovery audit.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="manual_vs_heuristic_comparison",
            script_path=scripts_dir / "build_manual_vs_heuristic_comparison_report.py",
            description="Refresh manual-vs-heuristic comparison report.",
        ),
        CalibrationTask(
            name="shadow_auto_runtime_mode",
            script_path=scripts_dir / "build_shadow_auto_runtime_mode.py",
            description="Refresh the baseline-vs-shadow runtime mode contract.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_candidate_bridge",
            script_path=scripts_dir / "build_shadow_auto_candidates.py",
            description="Refresh the calibration-to-shadow candidate bridge.",
        ),
        CalibrationTask(
            name="shadow_vs_baseline",
            script_path=scripts_dir / "build_shadow_vs_baseline.py",
            description="Refresh baseline-vs-shadow storage from current decision logs.",
        ),
        CalibrationTask(
            name="shadow_auto_evaluation",
            script_path=scripts_dir / "build_shadow_auto_evaluation.py",
            description="Refresh the SA4 shadow evaluation layer.",
        ),
        CalibrationTask(
            name="shadow_signal_activation_bridge",
            script_path=scripts_dir / "build_shadow_signal_activation_bridge.py",
            description="Refresh the shadow signal activation and availability bridge.",
        ),
        CalibrationTask(
            name="semantic_shadow_training_corpus",
            script_path=scripts_dir / "build_semantic_shadow_training_corpus.py",
            description="Refresh the current+legacy semantic shadow preview training corpus.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="semantic_shadow_training_bridge_adapter",
            script_path=scripts_dir / "build_semantic_shadow_training_bridge_adapter.py",
            description="Refresh the normalized-key semantic training bridge between forecast outcome rows and archive parquet history.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="semantic_shadow_proxy_datasets",
            script_path=scripts_dir / "build_semantic_shadow_proxy_datasets.py",
            description="Materialize proxy semantic_v1 datasets from the preview training bridge.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="semantic_shadow_preview_bundle",
            script_path=scripts_dir / "build_semantic_shadow_preview_bundle.py",
            description="Train the preview semantic shadow model bundle from proxy datasets.",
            every_n_cycles=96,
        ),
        CalibrationTask(
            name="semantic_shadow_runtime_activation_demo",
            script_path=scripts_dir / "build_semantic_shadow_runtime_activation_demo.py",
            description="Run the offline shadow runtime activation demo against the preview bundle.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="shadow_auto_execution_evaluation",
            script_path=scripts_dir / "build_shadow_auto_execution_evaluation.py",
            description="Refresh the execution-level preview evaluation for shadow runtime.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="shadow_auto_target_mapping",
            script_path=scripts_dir / "build_shadow_auto_target_mapping.py",
            description="Refresh the coarse action-target mapping for shadow redesign.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_divergence_audit",
            script_path=scripts_dir / "build_shadow_auto_divergence_audit.py",
            description="Refresh the baseline-vs-shadow action divergence audit.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_threshold_sweep",
            script_path=scripts_dir / "build_shadow_auto_threshold_sweep.py",
            description="Refresh threshold sweep candidates for creating bounded shadow divergence.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_dataset_bias_audit",
            script_path=scripts_dir / "build_shadow_auto_dataset_bias_audit.py",
            description="Refresh dataset-bias and rebalance guidance for shadow training rows.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_first_divergence_run",
            script_path=scripts_dir / "build_shadow_auto_first_divergence_run.py",
            description="Refresh the selected first divergence run from the threshold sweep.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_manual_reference_audit",
            script_path=scripts_dir / "build_shadow_auto_manual_reference_audit.py",
            description="Refresh manual-truth overlap coverage for the selected shadow divergence run.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_manual_overlap_queue",
            script_path=scripts_dir / "build_shadow_auto_manual_overlap_queue.py",
            description="Refresh the manual-truth collection queue for shadow divergence windows missing overlap.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_manual_overlap_seed_draft",
            script_path=scripts_dir / "build_shadow_auto_manual_overlap_seed_draft.py",
            description="Refresh review-needed manual seed drafts sourced from the shadow overlap queue.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_first_non_hold_decision",
            script_path=scripts_dir / "build_shadow_auto_first_non_hold_decision.py",
            description="Refresh the first non-HOLD shadow decision trial from the divergence run.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_bounded_apply_gate",
            script_path=scripts_dir / "build_shadow_auto_bounded_apply_gate.py",
            description="Refresh the bounded live-apply gate over the current preview candidate.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="semantic_shadow_active_runtime_readiness",
            script_path=scripts_dir / "build_semantic_shadow_active_runtime_readiness.py",
            description="Refresh guarded readiness for promoting preview shadow runtime toward active use.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="semantic_shadow_bounded_candidate_stage",
            script_path=scripts_dir / "build_semantic_shadow_bounded_candidate_stage.py",
            description="Stage a bounded semantic shadow runtime package and approval packet when readiness is green.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="semantic_shadow_bounded_candidate_approval",
            script_path=scripts_dir / "build_semantic_shadow_bounded_candidate_approval.py",
            description="Refresh bounded candidate approve/reject workflow and pending activation artifact for semantic shadow staging.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="semantic_shadow_active_runtime_activation",
            script_path=scripts_dir / "build_semantic_shadow_active_runtime_activation.py",
            description="Activate an approved bounded semantic shadow candidate into the active runtime only when runtime is idle.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="semantic_live_rollout_observation",
            script_path=scripts_dir / "build_semantic_live_rollout_observation.py",
            description="Refresh bounded semantic live rollout observation over runtime status and recent entry decisions.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="entry_authority_trace",
            script_path=scripts_dir / "build_entry_authority_trace.py",
            description="Refresh entry authority owner and veto distribution over recent entry decisions.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="baseline_no_action_bridge",
            script_path=scripts_dir / "build_baseline_no_action_bridge.py",
            description="Refresh AI2 baseline-no-action candidate bridge coverage and breakout-source distribution.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="entry_candidate_coverage_audit",
            script_path=scripts_dir / "build_entry_candidate_coverage_audit.py",
            description="Refresh AI2 candidate-surface blocker distributions for baseline-no-action fresh rows.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="countertrend_materialization_check",
            script_path=scripts_dir / "build_countertrend_materialization_check.py",
            description="Refresh fresh XAU countertrend continuation field materialization and target-family coverage before direction-agnostic migration.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="countertrend_down_bootstrap_validation",
            script_path=scripts_dir / "build_countertrend_down_bootstrap_validation.py",
            description="Refresh XAU DOWN bootstrap directional-state validation over fresh lower-reversal target-family rows.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="market_family_audit_snapshot",
            script_path=scripts_dir / "build_market_family_audit_snapshot.py",
            description="Refresh market-family entry and exit audit snapshots for NAS/BTC/XAU over recent runtime and closed-trade windows.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="entry_performance_baseline",
            script_path=scripts_dir / "build_entry_performance_baseline.py",
            description="Lock the current entry-performance baseline and refresh the 200ms reentry regression watch before roadmap work resumes.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="distribution_promotion_gate_baseline",
            script_path=scripts_dir / "build_distribution_promotion_gate_baseline.py",
            description="Refresh absolute-plus-relative distribution baseline over recent candidate rows before live promotion-gate rollout.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="market_adapter_layer",
            script_path=scripts_dir / "build_market_adapter_layer.py",
            description="Refresh shared-surface plus market-family adapter contract from audit, failure, and distribution artifacts.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="multi_surface_preview_dataset_export",
            script_path=scripts_dir / "build_multi_surface_preview_dataset_export.py",
            description="Export preview-ready multi-surface datasets from formalized supervision, time-axis, failure, and market-adapter artifacts.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="initial_entry_label_resolution_queue",
            script_path=scripts_dir / "build_initial_entry_label_resolution_queue.py",
            description="Refresh unresolved NAS/XAU initial-entry preview rows that need manual label resolution before rollout.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="multi_surface_data_gap_queue",
            script_path=scripts_dir / "build_multi_surface_data_gap_queue.py",
            description="Refresh follow-through negative-row gaps and continuation/protective data collection gaps by market family.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_btc_review_canary_activation_contract",
            script_path=scripts_dir / "build_bounded_btc_review_canary_activation_contract.py",
            description="Refresh bounded BTC review-canary activation contract while manual signoff is pending.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_symbol_surface_activation_contract",
            script_path=scripts_dir / "build_bounded_symbol_surface_activation_contract.py",
            description="Refresh generic bounded symbol-surface activation contracts while manual signoff is pending.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="initial_entry_label_resolution_draft",
            script_path=scripts_dir / "build_initial_entry_label_resolution_draft.py",
            description="Refresh proposed NAS/XAU initial-entry label resolutions for unresolved probe-entry rows.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="initial_entry_label_resolution_apply",
            script_path=scripts_dir / "build_initial_entry_label_resolution_apply.py",
            description="Apply accepted NAS/XAU initial-entry label resolutions into the resolved preview dataset used by MF16/MF17 gates.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="follow_through_negative_expansion_draft",
            script_path=scripts_dir / "build_follow_through_negative_expansion_draft.py",
            description="Refresh proposed negative follow-through expansion rows from failure-harvest evidence.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="follow_through_negative_expansion_apply",
            script_path=scripts_dir / "build_follow_through_negative_expansion_apply.py",
            description="Apply reviewed negative follow-through expansion rows into the augmented follow-through preview dataset.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="hold_exit_augmentation_draft",
            script_path=scripts_dir / "build_hold_exit_augmentation_draft.py",
            description="Refresh continuation-hold and protective-exit augmentation drafts from early-exit regret and late protect examples.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="hold_exit_augmentation_apply",
            script_path=scripts_dir / "build_hold_exit_augmentation_apply.py",
            description="Apply reviewed continuation-hold and protective-exit augmentation rows into augmented preview datasets.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="symbol_surface_preview_evaluation",
            script_path=scripts_dir / "build_symbol_surface_preview_evaluation.py",
            description="Evaluate preview datasets by symbol and surface for readiness, imbalance, and behavior-specific failure coverage.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_rollout_candidate_gate",
            script_path=scripts_dir / "build_bounded_rollout_candidate_gate.py",
            description="Select bounded rollout review candidates from symbol-surface preview evaluation with stricter readiness and failure-burden gates.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_rollout_review_manifest",
            script_path=scripts_dir / "build_bounded_rollout_review_manifest.py",
            description="Materialize review-ready bounded rollout manifest packets for canary candidates before any live activation.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_rollout_signoff_criteria",
            script_path=scripts_dir / "build_bounded_rollout_signoff_criteria.py",
            description="Refresh symbol-surface review/signoff scorecards from review manifests, entry performance baseline, and regression watch.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="btc_initial_entry_canary_signoff_packet",
            script_path=scripts_dir / "build_btc_initial_entry_canary_signoff_packet.py",
            description="Materialize the compatibility BTCUSD initial-entry review/signoff packet alongside the generic signoff packet.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="symbol_surface_canary_signoff_packet",
            script_path=scripts_dir / "build_symbol_surface_canary_signoff_packet.py",
            description="Materialize generic symbol-surface review/signoff packets for review-canary candidates.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="symbol_surface_manual_signoff_apply",
            script_path=scripts_dir / "build_symbol_surface_manual_signoff_apply.py",
            description="Apply explicit review-canary manual signoff decisions into symbol-surface approval artifacts.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="bounded_symbol_surface_activation_apply",
            script_path=scripts_dir / "build_bounded_symbol_surface_activation_apply.py",
            description="Apply bounded symbol-surface activation decisions after manual signoff while keeping performance and idle guards active.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="surface_objective_ev_spec",
            script_path=scripts_dir / "build_surface_objective_ev_spec.py",
            description="Refresh market-family multi-surface objective and EV proxy specifications from current entry/exit audit snapshots.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="check_color_label_formalization",
            script_path=scripts_dir / "build_check_color_label_formalization.py",
            description="Formalize manual check/color supervision into surface/state/failure labels using manual truth, breakout seeds, and aligned breakout targets.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="surface_time_axis_contract",
            script_path=scripts_dir / "build_surface_time_axis_contract.py",
            description="Materialize time-axis fields for multi-surface manual supervision rows using anchor, entry, and exit timestamps.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="failure_label_harvest",
            script_path=scripts_dir / "build_failure_label_harvest.py",
            description="Harvest confirmed and runtime-derived candidate failure labels across multi-surface entry and exit evidence.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="wrong_side_conflict_harvest",
            script_path=scripts_dir / "build_wrong_side_conflict_harvest.py",
            description="Harvest wrong-side active-action conflicts so runtime direction clashes become reusable preview-learning evidence.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="wrong_side_conflict_replay_harness",
            script_path=scripts_dir / "build_wrong_side_conflict_replay_harness.py",
            description="Replay historical NAS/XAU wrong-side conflicts through the current guard and bridge path to verify downgrade and breakout precedence behavior.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="upper_reversal_breakout_conflict_validation",
            script_path=scripts_dir / "build_upper_reversal_breakout_conflict_validation.py",
            description="Validate fresh NAS/XAU upper-reversal sell slices against breakout-up conflict guard coverage while pairing them with replay-confirmed support.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="exit_surface_observation",
            script_path=scripts_dir / "build_exit_surface_observation.py",
            description="Refresh continuation-hold vs protective-exit surface observation over recent open and closed trade history.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="breakout_runtime_raw_audit",
            script_path=scripts_dir / "build_breakout_runtime_raw_audit.py",
            description="Refresh raw breakout runtime and overlay blocker distributions over fresh baseline-no-action rows.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="breakout_historical_calibration_bridge",
            script_path=scripts_dir / "build_breakout_historical_calibration_bridge.py",
            description="Refresh historical breakout calibration alignment over matched replay/manual rows to tune AI2 breakout direction and demotion behavior.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="breakout_barrier_drag_calibrator",
            script_path=scripts_dir / "build_breakout_barrier_drag_calibrator.py",
            description="Refresh historical/live barrier-drag calibration guidance for splitting WATCH vs PROBE breakout demotions.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="shadow_auto_correction_loop",
            script_path=scripts_dir / "build_shadow_auto_correction_loop.py",
            description="Refresh SA5 shadow correction loop from preview execution evaluation.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="shadow_auto_decision_engine",
            script_path=scripts_dir / "build_shadow_auto_decision_engine.py",
            description="Refresh SA6 bounded apply decision recommendation from preview correction loop.",
            every_n_cycles=48,
        ),
        CalibrationTask(
            name="shadow_correction_knowledge_base",
            script_path=scripts_dir / "build_shadow_correction_knowledge_base.py",
            description="Refresh the durable SA9 shadow correction knowledge base from current gate/approval/activation state.",
            every_n_cycles=12,
        ),
        CalibrationTask(
            name="semantic_shadow_bundle_bootstrap",
            script_path=scripts_dir / "build_semantic_shadow_bundle_bootstrap.py",
            description="Refresh semantic shadow bundle bootstrap and readiness guidance.",
            every_n_cycles=24,
        ),
        CalibrationTask(
            name="manual_vs_heuristic_family_ranking",
            script_path=scripts_dir / "build_manual_vs_heuristic_family_ranking.py",
            description="Refresh next mismatch family ranking.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_recovered_casebook",
            script_path=scripts_dir / "build_manual_vs_heuristic_recovered_casebook.py",
            description="Refresh recovered-case casebook.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_bias_targets",
            script_path=scripts_dir / "build_manual_vs_heuristic_bias_targets.py",
            description="Refresh bias target summary from recovered casebook.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_current_rich_queue",
            script_path=scripts_dir / "build_manual_vs_heuristic_current_rich_queue.py",
            description="Refresh current-rich manual collection queue.",
        ),
        CalibrationTask(
            name="manual_current_rich_seed_draft",
            script_path=scripts_dir / "build_manual_current_rich_seed_draft.py",
            description="Refresh assistant seed draft from current-rich queue.",
        ),
        CalibrationTask(
            name="manual_truth_corpus_freshness",
            script_path=scripts_dir / "build_manual_truth_corpus_freshness.py",
            description="Refresh manual truth corpus freshness audit.",
        ),
        CalibrationTask(
            name="manual_truth_corpus_coverage",
            script_path=scripts_dir / "build_manual_truth_corpus_coverage.py",
            description="Refresh wait-family and pattern coverage map for manual truth.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_wrong_failed_wait_audit",
            script_path=scripts_dir / "build_manual_vs_heuristic_wrong_failed_wait_audit.py",
            description="Refresh focused wrong-failed-wait audit.",
        ),
        CalibrationTask(
            name="manual_current_rich_wrong_failed_wait_review_queue",
            script_path=scripts_dir / "build_manual_current_rich_wrong_failed_wait_review_queue.py",
            description="Refresh current-rich review queue for wrong-failed-wait cases.",
        ),
        CalibrationTask(
            name="manual_current_rich_wrong_failed_wait_review_results",
            script_path=scripts_dir / "build_manual_current_rich_wrong_failed_wait_review_results.py",
            description="Refresh derived review results for wrong-failed-wait follow-up.",
        ),
        CalibrationTask(
            name="manual_current_rich_promotion_gate",
            script_path=scripts_dir / "build_manual_current_rich_promotion_gate.py",
            description="Refresh current-rich draft canonical promotion gate.",
        ),
        CalibrationTask(
            name="manual_current_rich_review_workflow",
            script_path=scripts_dir / "build_manual_current_rich_review_workflow.py",
            description="Refresh current-rich human review workflow batches and trace requirements.",
        ),
        CalibrationTask(
            name="manual_current_rich_review_trace",
            script_path=scripts_dir / "build_manual_current_rich_review_trace.py",
            description="Refresh review-batch trace sheet for the highest-priority current-rich batch.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_bias_sandbox",
            script_path=scripts_dir / "build_manual_vs_heuristic_bias_sandbox.py",
            description="Refresh bias-correction sandbox loop scaffold.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_patch_draft",
            script_path=scripts_dir / "build_manual_vs_heuristic_patch_draft.py",
            description="Refresh patch-draft templates for the top sandbox families.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_correction_loop",
            script_path=scripts_dir / "run_manual_vs_heuristic_correction_loop.py",
            description="Refresh correction candidates and correction-run screening logs.",
        ),
        CalibrationTask(
            name="manual_current_rich_post_promotion_audit",
            script_path=scripts_dir / "build_manual_current_rich_post_promotion_audit.py",
            description="Refresh post-promotion audit queue for current-rich rows promoted toward canonical.",
        ),
        CalibrationTask(
            name="manual_vs_heuristic_ranking_retrospective",
            script_path=scripts_dir / "build_manual_vs_heuristic_ranking_retrospective.py",
            description="Refresh family-ranking retrospective metrics from current ranking and correction runs.",
        ),
        CalibrationTask(
            name="manual_current_rich_promotion_discipline",
            script_path=scripts_dir / "build_manual_current_rich_promotion_discipline.py",
            description="Refresh draft/validated/canonical discipline view and canonical merge trace fields.",
        ),
        CalibrationTask(
            name="manual_calibration_approval_log",
            script_path=scripts_dir / "build_manual_calibration_approval_log.py",
            description="Refresh the unified approval log across promotion, correction, and audit decisions.",
        ),
    ]


def _safe_json_load(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _truncate_text(text: str, *, limit: int = 400) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def build_manual_truth_calibration_cycle(
    *,
    cycle: int,
    root: Path,
    python_exe: Path,
    runtime_status_path: Path,
    require_runtime_fresh: bool,
    runtime_max_age_sec: float,
    step_timeout_sec: float,
    runner: Runner | None = None,
) -> dict[str, Any]:
    runtime_ok, runtime_age_sec = _runtime_fresh(runtime_status_path, runtime_max_age_sec)
    started_at = datetime.now().isoformat(timespec="seconds")

    if require_runtime_fresh and not runtime_ok:
        return {
            "contract_version": "manual_truth_calibration_watch_cycle_v1",
            "cycle": int(cycle),
            "started_at": started_at,
            "status": "runtime_stale_skip",
            "runtime_status": {
                "path": str(runtime_status_path),
                "fresh": bool(runtime_ok),
                "age_sec": round(float(runtime_age_sec), 2),
                "required": True,
                "max_age_sec": float(runtime_max_age_sec),
            },
            "task_count": 0,
            "ok_task_count": 0,
            "failed_task_count": 0,
            "tasks": [],
            "next_actions": [
                "Keep the runtime alive and wait for a fresh heartbeat before the next calibration cycle.",
            ],
        }

    task_runner = runner or _default_runner
    tasks = build_manual_truth_calibration_tasks(root)
    task_rows: list[dict[str, Any]] = []
    ok_count = 0
    failed_count = 0
    skipped_count = 0
    executed_count = 0

    for task in tasks:
        every_n_cycles = max(1, int(task.every_n_cycles))
        if int(cycle) % every_n_cycles != 0:
            skipped_count += 1
            task_rows.append(
                {
                    "name": task.name,
                    "description": task.description,
                    "script_path": str(task.script_path),
                    "every_n_cycles": every_n_cycles,
                    "executed": False,
                    "skipped": True,
                    "returncode": None,
                    "ok": True,
                    "duration_sec": 0.0,
                    "summary": {},
                    "stdout_excerpt": "",
                    "stderr_excerpt": "",
                }
            )
            continue

        command = [str(python_exe), str(task.script_path)]
        started = time.time()
        try:
            result = task_runner(command, root, step_timeout_sec)
            duration_sec = round(max(0.0, time.time() - started), 3)
            summary = _safe_json_load(result.stdout)
            ok = int(result.returncode) == 0
            executed_count += 1
            if ok:
                ok_count += 1
            else:
                failed_count += 1
            task_rows.append(
                {
                    "name": task.name,
                    "description": task.description,
                    "script_path": str(task.script_path),
                    "every_n_cycles": every_n_cycles,
                    "executed": True,
                    "skipped": False,
                    "returncode": int(result.returncode),
                    "ok": bool(ok),
                    "duration_sec": duration_sec,
                    "summary": summary,
                    "stdout_excerpt": _truncate_text(result.stdout),
                    "stderr_excerpt": _truncate_text(result.stderr),
                }
            )
        except subprocess.TimeoutExpired:
            failed_count += 1
            executed_count += 1
            duration_sec = round(max(0.0, time.time() - started), 3)
            task_rows.append(
                {
                    "name": task.name,
                    "description": task.description,
                    "script_path": str(task.script_path),
                    "every_n_cycles": every_n_cycles,
                    "executed": True,
                    "skipped": False,
                    "returncode": None,
                    "ok": False,
                    "duration_sec": duration_sec,
                    "summary": {},
                    "stdout_excerpt": "",
                    "stderr_excerpt": f"timeout>{round(float(step_timeout_sec), 1)}s",
                }
            )

    latest_task = task_rows[-1] if task_rows else {}
    return {
        "contract_version": "manual_truth_calibration_watch_cycle_v1",
        "cycle": int(cycle),
        "started_at": started_at,
        "status": "ran" if failed_count == 0 else "partial_failure",
        "runtime_status": {
            "path": str(runtime_status_path),
            "fresh": bool(runtime_ok),
            "age_sec": round(float(runtime_age_sec), 2),
            "required": bool(require_runtime_fresh),
            "max_age_sec": float(runtime_max_age_sec),
        },
        "task_count": int(len(task_rows)),
        "executed_task_count": int(executed_count),
        "skipped_task_count": int(skipped_count),
        "ok_task_count": int(ok_count),
        "failed_task_count": int(failed_count),
        "latest_task": {
            "name": str(latest_task.get("name", "")),
            "ok": bool(latest_task.get("ok", False)),
            "returncode": latest_task.get("returncode", 0),
        },
        "tasks": task_rows,
        "next_actions": [
            "Inspect failed task stderr excerpts if any task reports partial_failure.",
            "Review refreshed comparison/current-rich/bias outputs before promoting any manual truth into canonical.",
        ],
    }


def render_manual_truth_calibration_watch_markdown(report: dict[str, Any]) -> str:
    latest = dict(report.get("latest_cycle", {}) or {})
    runtime = dict(latest.get("runtime_status", {}) or {})
    latest_task = dict(latest.get("latest_task", {}) or {})
    lines = [
        "# Manual Truth Calibration Watch",
        "",
        "## Latest Cycle",
        "",
        f"- cycle: `{latest.get('cycle', 0)}`",
        f"- status: `{latest.get('status', '')}`",
        f"- runtime_fresh: `{runtime.get('fresh', False)}`",
        f"- runtime_age_sec: `{runtime.get('age_sec', 0.0)}`",
        f"- task_count: `{latest.get('task_count', 0)}`",
        f"- executed_task_count: `{latest.get('executed_task_count', 0)}`",
        f"- skipped_task_count: `{latest.get('skipped_task_count', 0)}`",
        f"- ok_task_count: `{latest.get('ok_task_count', 0)}`",
        f"- failed_task_count: `{latest.get('failed_task_count', 0)}`",
        f"- latest_task: `{latest_task.get('name', '')}`",
        f"- latest_task_ok: `{latest_task.get('ok', False)}`",
        "",
        "## Tasks",
        "",
    ]

    for task in list(latest.get("tasks", []) or []):
        lines.extend(
            [
                f"- `{task.get('name', '')}` executed=`{task.get('executed', False)}` ok=`{task.get('ok', False)}` returncode=`{task.get('returncode', '')}` duration_sec=`{task.get('duration_sec', 0.0)}` cadence=`every {task.get('every_n_cycles', 1)} cycles`",
                f"  - script: `{task.get('script_path', '')}`",
            ]
        )

    lines.extend(["", "## Next Actions", ""])
    for action in list(latest.get("next_actions", []) or []):
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def write_manual_truth_calibration_watch_outputs(
    *,
    out_dir: Path,
    report: dict[str, Any],
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "manual_truth_calibration_watch_latest.json"
    md_path = out_dir / "manual_truth_calibration_watch_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_manual_truth_calibration_watch_markdown(report), encoding="utf-8")
    return json_path, md_path
