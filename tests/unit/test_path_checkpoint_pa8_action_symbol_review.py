from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_symbol_review import (
    build_checkpoint_pa8_action_symbol_review,
    render_checkpoint_pa8_action_symbol_review_markdown,
)


def test_build_checkpoint_pa8_action_symbol_review_identifies_top_cluster() -> None:
    payload = build_checkpoint_pa8_action_symbol_review(
        symbol="NAS100",
        pa8_action_review_checklist_payload={
            "checklist_rows": [
                {
                    "symbol": "NAS100",
                    "review_state": "PRIMARY_REVIEW",
                    "goal": "Confirm whether the HOLD boundary for NAS100 is actually correct against hindsight outcomes.",
                    "blockers": ["hold_precision_below_symbol_floor"],
                    "pass_criteria": ["Raise hold_precision to at least 0.80."],
                    "review_focuses": ["inspect_hold_precision_boundary"],
                }
            ]
        },
        resolved_rows=[
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "management_action_reason": "runner_family_hold_bias",
                "source": "exit_manage_hold",
                "current_profit": "0.12",
                "runtime_hold_quality_score": "0.53",
                "runtime_partial_exit_ev": "0.57",
                "runtime_continuation_odds": "0.84",
                "runtime_reversal_odds": "0.47",
                "checkpoint_id": "CP001",
                "hindsight_quality_tier": "manual_exception",
                "position_side": "LONG",
            },
            {
                "symbol": "NAS100",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "management_action_reason": "runner_family_hold_bias",
                "source": "exit_manage_hold",
                "current_profit": "0.08",
                "runtime_hold_quality_score": "0.52",
                "runtime_partial_exit_ev": "0.56",
                "runtime_continuation_odds": "0.85",
                "runtime_reversal_odds": "0.47",
                "checkpoint_id": "CP002",
                "hindsight_quality_tier": "manual_exception",
                "position_side": "LONG",
            },
        ],
    )

    summary = payload["summary"]
    assert summary["symbol"] == "NAS100"
    assert summary["review_result"] == "narrow_hold_boundary_candidate_identified"
    assert payload["top_mismatch_clusters"][0]["checkpoint_rule_family_hint"] == "profit_hold_bias"
    assert payload["top_mismatch_clusters"][0]["row_count"] == 2


def test_render_checkpoint_pa8_action_symbol_review_markdown_contains_top_cluster() -> None:
    markdown = render_checkpoint_pa8_action_symbol_review_markdown(
        {
            "summary": {
                "symbol": "NAS100",
                "review_state": "PRIMARY_REVIEW",
                "goal": "Confirm whether the HOLD boundary for NAS100 is actually correct against hindsight outcomes.",
                "review_result": "narrow_hold_boundary_candidate_identified",
                "mismatch_row_count": 2,
                "top_mismatch_cluster_row_count": 2,
                "review_summary": "NAS100 hold-precision blocker is concentrated in RUNNER_CHECK + profit_hold_bias.",
            },
            "checklist_context": {
                "blockers": ["hold_precision_below_symbol_floor"],
                "pass_criteria": ["Raise hold_precision to at least 0.80."],
                "review_focuses": ["inspect_hold_precision_boundary"],
            },
            "top_mismatch_clusters": [
                {
                    "surface_name": "continuation_hold_surface",
                    "checkpoint_type": "RUNNER_CHECK",
                    "checkpoint_rule_family_hint": "profit_hold_bias",
                    "management_action_label": "HOLD",
                    "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                    "row_count": 2,
                    "avg_current_profit": 0.1,
                    "avg_runtime_hold_quality_score": 0.525,
                    "avg_runtime_partial_exit_ev": 0.565,
                    "avg_runtime_continuation_odds": 0.845,
                    "avg_runtime_reversal_odds": 0.47,
                    "top_management_reason": "runner_family_hold_bias",
                    "top_source": "exit_manage_hold",
                    "sample_checkpoint_ids": ["CP001", "CP002"],
                }
            ],
            "manual_exception_top_groups": [],
            "position_side_counts": {"LONG": 2},
        }
    )

    assert "# PA8 NAS100 Action Review" in markdown
    assert "### 1. profit_hold_bias" in markdown
    assert "- action_path: `HOLD -> PARTIAL_THEN_HOLD`" in markdown


def test_build_checkpoint_pa8_action_symbol_review_identifies_wait_boundary_candidate() -> None:
    payload = build_checkpoint_pa8_action_symbol_review(
        symbol="BTCUSD",
        pa8_action_review_checklist_payload={
            "checklist_rows": [
                {
                    "symbol": "BTCUSD",
                    "review_state": "PRIMARY_REVIEW",
                    "goal": "Confirm whether BTCUSD proxy mismatch is confined to a narrow protective reclaim family.",
                    "blockers": ["runtime_proxy_match_rate_below_symbol_floor"],
                    "pass_criteria": ["Confine mismatch to a narrow family."],
                    "review_focuses": ["inspect_runtime_proxy_alignment"],
                }
            ]
        },
        resolved_rows=[
            {
                "symbol": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "management_action_reason": "full_exit_gate_not_met_trim_fallback",
                "source": "exit_manage_hold",
                "current_profit": "-0.30",
                "runtime_hold_quality_score": "0.39",
                "runtime_partial_exit_ev": "0.37",
                "runtime_continuation_odds": "0.87",
                "runtime_reversal_odds": "0.69",
                "checkpoint_id": "CP101",
                "hindsight_quality_tier": "manual_exception",
                "position_side": "SELL",
            },
            {
                "symbol": "BTCUSD",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RECLAIM_CHECK",
                "checkpoint_rule_family_hint": "active_open_loss",
                "management_action_label": "PARTIAL_EXIT",
                "hindsight_best_management_action_label": "WAIT",
                "management_action_reason": "full_exit_gate_not_met_trim_fallback",
                "source": "exit_manage_hold",
                "current_profit": "-0.28",
                "runtime_hold_quality_score": "0.38",
                "runtime_partial_exit_ev": "0.37",
                "runtime_continuation_odds": "0.88",
                "runtime_reversal_odds": "0.69",
                "checkpoint_id": "CP102",
                "hindsight_quality_tier": "manual_exception",
                "position_side": "SELL",
            },
        ],
    )

    summary = payload["summary"]
    assert summary["review_result"] == "narrow_wait_boundary_candidate_identified"
