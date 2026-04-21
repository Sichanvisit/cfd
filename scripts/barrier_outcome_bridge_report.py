"""
Barrier outcome bridge report.

Usage:
  python scripts/barrier_outcome_bridge_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.barrier_outcome_bridge import (  # noqa: E402
    write_barrier_outcome_bridge_report,
)


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_output_path() -> Path:
    return ROOT / "data" / "analysis" / "barrier" / "barrier_outcome_bridge_latest.json"


def _default_markdown_output_path() -> Path:
    return ROOT / "data" / "analysis" / "barrier" / "barrier_outcome_bridge_latest.md"


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--closed-trades-path", default=str(_default_closed_history_path()))
    parser.add_argument("--future-bars-path", default="")
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--output-path", default=str(_default_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--print-full", action="store_true")
    args = parser.parse_args()

    report = write_barrier_outcome_bridge_report(
        entry_decision_path=args.entry_decisions_path,
        closed_trade_path=args.closed_trades_path,
        future_bar_path=(args.future_bars_path or None),
        runtime_status_path=(args.runtime_status_path or None),
        output_path=args.output_path,
        markdown_output_path=args.markdown_output_path,
        symbols=list(args.symbol or []),
        limit=args.limit,
    )
    if args.print_full:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    summary = report.get("summary", {}) or {}
    coverage = report.get("coverage", {}) or {}
    dashboard = coverage.get("dashboard", {}) or {}
    counterfactual_audit = report.get("counterfactual_audit", {}) or {}
    drift_audit = report.get("drift_audit", {}) or {}
    bias_baseline = report.get("bias_baseline_v1", {}) or {}
    bias_recovery = report.get("bias_recovery_v1", {}) or {}
    wait_family = report.get("wait_family_v1", {}) or {}
    correct_wait_diagnostic = report.get("correct_wait_diagnostic_v1", {}) or {}
    correct_wait_casebook = report.get("correct_wait_casebook_v1", {}) or {}
    timing_edge_absent_casebook = report.get("timing_edge_absent_casebook_v1", {}) or {}
    readiness_gate = report.get("readiness_gate", {}) or {}
    timing_edge_absent_subtype_profiles = timing_edge_absent_casebook.get("subtype_profiles", {}) or {}
    missed_profit_leaning_profile = timing_edge_absent_subtype_profiles.get("missed_profit_leaning", {}) or {}
    timing_edge_other_profile = timing_edge_absent_subtype_profiles.get("timing_edge_other", {}) or {}
    small_continuation_profile = timing_edge_absent_subtype_profiles.get("small_continuation_avoided_loss", {}) or {}
    bias_label_distribution = bias_baseline.get("label_distribution", {}) or {}
    bias_combined_distribution = bias_label_distribution.get("combined", {}) or {}
    bias_drift_baseline = bias_baseline.get("drift_baseline", {}) or {}
    wait_family_distribution = wait_family.get("family_distribution", {}) or {}
    wait_subtype_distribution = wait_family.get("subtype_distribution", {}) or {}
    print(
        json.dumps(
            {
                "raw_bridge_candidate_count": summary.get("raw_bridge_candidate_count", 0),
                "bridged_row_count": summary.get("bridged_row_count", 0),
                "strict_rows": summary.get("strict_rows", 0),
                "usable_rows": summary.get("usable_rows", 0),
                "skip_rows": summary.get("skip_rows", 0),
                "labeled_rows": summary.get("labeled_rows", 0),
                "eligible_rows": summary.get("eligible_rows", 0),
                "overblock_ratio": summary.get("overblock_ratio", 0.0),
                "avoided_loss_rate": summary.get("avoided_loss_rate", 0.0),
                "missed_profit_rate": summary.get("missed_profit_rate", 0.0),
                "correct_wait_rate": summary.get("correct_wait_rate", 0.0),
                "relief_failure_rate": summary.get("relief_failure_rate", 0.0),
                "counterfactual_cost_delta_r_mean": summary.get("counterfactual_cost_delta_r_mean", 0.0),
                "counterfactual_positive_rate": summary.get("counterfactual_positive_rate", 0.0),
                "counterfactual_negative_rate": summary.get("counterfactual_negative_rate", 0.0),
                "drift_mismatch_rows": drift_audit.get("mismatch_rows", 0),
                "drift_mismatch_rate": drift_audit.get("mismatch_rate", 0.0),
                "drift_mismatch_rate_v2": drift_audit.get("mismatch_rate_v2", 0.0),
                "top_skip_reasons": dashboard.get("top_skip_reasons", []),
                "top_counterfactual_outcomes": counterfactual_audit.get("top_counterfactual_outcomes", []),
                "top_actual_vs_recommended": counterfactual_audit.get("top_actual_vs_recommended", []),
                "top_mismatch_action_pairs": drift_audit.get("top_mismatch_action_pairs", []),
                "top_scene_family_mismatch": drift_audit.get("top_scene_family_mismatch", []),
                "top_barrier_family_mismatch": drift_audit.get("top_barrier_family_mismatch", []),
                "bias_combined_top_labels": bias_combined_distribution.get("top_labels", []),
                "bias_top_normalized_action_pairs": bias_drift_baseline.get("top_normalized_action_pairs", []),
                "bias_top_normalized_action_pairs_v2": bias_drift_baseline.get("top_normalized_action_pairs_v2", []),
                "bias_recovery_top_candidates": bias_recovery.get("top_candidate_counts", []),
                "bias_recovery_top_primary_labels": bias_recovery.get("top_primary_candidate_labels", []),
                "wait_family_top_families": wait_family_distribution.get("top_families", []),
                "wait_family_top_subtypes": wait_subtype_distribution.get("top_subtypes", []),
                "wait_family_usage_buckets": wait_family.get("usage_bucket_counts", {}),
                "correct_wait_diag_top_blockers": correct_wait_diagnostic.get("top_blocking_reasons", []),
                "correct_wait_diag_candidate_rows": {
                    "scope_rows": correct_wait_diagnostic.get("scope_rows", 0),
                    "timing_candidate_rows": correct_wait_diagnostic.get("timing_candidate_rows", 0),
                    "wait_value_candidate_rows": correct_wait_diagnostic.get("wait_value_candidate_rows", 0),
                    "labeled_correct_wait_rows": correct_wait_diagnostic.get("labeled_correct_wait_rows", 0),
                },
                "correct_wait_casebook_summary": {
                    "loss_avoided_dominates_rows": correct_wait_casebook.get("loss_avoided_dominates_rows", 0),
                    "unique_signatures": correct_wait_casebook.get("unique_signatures", 0),
                    "zero_entry_gain_rows": correct_wait_casebook.get("zero_entry_gain_rows", 0),
                    "small_entry_gain_rows": correct_wait_casebook.get("small_entry_gain_rows", 0),
                    "mean_loss_wait_margin_r": correct_wait_casebook.get("mean_loss_wait_margin_r", 0.0),
                },
                "correct_wait_casebook_top_signatures": correct_wait_casebook.get("top_signatures", []),
                "timing_edge_absent_casebook_summary": {
                    "timing_edge_absent_rows": timing_edge_absent_casebook.get("timing_edge_absent_rows", 0),
                    "unique_signatures": timing_edge_absent_casebook.get("unique_signatures", 0),
                    "zero_entry_gain_rows": timing_edge_absent_casebook.get("zero_entry_gain_rows", 0),
                    "small_entry_gain_rows": timing_edge_absent_casebook.get("small_entry_gain_rows", 0),
                    "mean_better_entry_gain_6": timing_edge_absent_casebook.get("mean_better_entry_gain_6", 0.0),
                    "mean_later_continuation_f_6": timing_edge_absent_casebook.get("mean_later_continuation_f_6", 0.0),
                },
                "timing_edge_absent_subtypes": timing_edge_absent_casebook.get("top_subtypes", []),
                "timing_edge_absent_missed_profit_profile": {
                    "row_count": missed_profit_leaning_profile.get("row_count", 0),
                    "top_labels": missed_profit_leaning_profile.get("top_labels", []),
                    "top_weak_reasons": missed_profit_leaning_profile.get("top_weak_reasons", []),
                },
                "timing_edge_absent_small_continuation_profile": {
                    "row_count": small_continuation_profile.get("row_count", 0),
                    "top_labels": small_continuation_profile.get("top_labels", []),
                },
                "timing_edge_absent_other_profile": {
                    "row_count": timing_edge_other_profile.get("row_count", 0),
                    "top_labels": timing_edge_other_profile.get("top_labels", []),
                },
                "timing_edge_absent_casebook_top_signatures": timing_edge_absent_casebook.get("top_signatures", []),
                "readiness_stage": readiness_gate.get("stage", ""),
                "readiness_ready": readiness_gate.get("ready", False),
                "readiness_blockers": readiness_gate.get("blockers", []),
                "readiness_runtime_heartbeat": (readiness_gate.get("runtime_heartbeat", {}) or {}),
                "label_counts": coverage.get("label_counts", {}),
                "confidence_counts": coverage.get("confidence_counts", {}),
                "coverage_bucket_counts": coverage.get("coverage_bucket_counts", {}),
                "json_path": report.get("output_path", ""),
                "markdown_path": report.get("markdown_output_path", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
