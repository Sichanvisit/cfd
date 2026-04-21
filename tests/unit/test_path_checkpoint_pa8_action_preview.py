from __future__ import annotations

import pandas as pd

from backend.services.path_checkpoint_pa8_action_preview import (
    build_nas100_profit_hold_bias_action_preview,
    render_nas100_profit_hold_bias_action_preview_markdown,
)


def test_build_nas100_profit_hold_bias_action_preview_improves_hold_precision() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": "NAS100",
                "checkpoint_id": "CP1",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "current_profit": 0.12,
                "runtime_hold_quality_score": 0.53,
                "runtime_partial_exit_ev": 0.57,
                "runtime_full_exit_risk": 0.19,
                "runtime_continuation_odds": 0.84,
                "runtime_reversal_odds": 0.47,
                "giveback_ratio": 0.0,
            },
            {
                "symbol": "NAS100",
                "checkpoint_id": "CP2",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "runtime_proxy_management_action_label": "HOLD",
                "hindsight_best_management_action_label": "HOLD",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "current_profit": 0.22,
                "runtime_hold_quality_score": 0.61,
                "runtime_partial_exit_ev": 0.55,
                "runtime_full_exit_risk": 0.19,
                "runtime_continuation_odds": 0.84,
                "runtime_reversal_odds": 0.47,
                "giveback_ratio": 0.0,
            },
            {
                "symbol": "NAS100",
                "checkpoint_id": "CP3",
                "surface_name": "continuation_hold_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "checkpoint_rule_family_hint": "profit_hold_bias",
                "runtime_proxy_management_action_label": "PARTIAL_THEN_HOLD",
                "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                "unrealized_pnl_state": "OPEN_PROFIT",
                "current_profit": 0.18,
                "runtime_hold_quality_score": 0.51,
                "runtime_partial_exit_ev": 0.58,
                "runtime_full_exit_risk": 0.18,
                "runtime_continuation_odds": 0.85,
                "runtime_reversal_odds": 0.47,
                "giveback_ratio": 0.0,
            },
        ]
    )

    preview_frame, summary = build_nas100_profit_hold_bias_action_preview(frame)

    assert len(preview_frame) == 3
    assert summary["eligible_row_count"] == 1
    assert summary["preview_changed_row_count"] == 1
    assert summary["baseline_hold_precision"] == 0.5
    assert summary["preview_hold_precision"] == 1.0
    assert summary["preview_runtime_proxy_match_rate"] > summary["baseline_runtime_proxy_match_rate"]
    assert summary["recommended_next_action"] == "review_nas100_profit_hold_bias_preview_for_action_only_canary"


def test_render_nas100_profit_hold_bias_action_preview_markdown_contains_metrics() -> None:
    sample_case = {
        "checkpoint_id": "CP1",
        "baseline_action_label": "HOLD",
        "preview_action_label": "PARTIAL_THEN_HOLD",
        "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
        "checkpoint_rule_family_hint": "profit_hold_bias",
        "surface_name": "continuation_hold_surface",
        "checkpoint_type": "RUNNER_CHECK",
        "preview_reason": "nas100_profit_hold_bias_hold_to_partial_then_hold_preview",
        "current_profit": 0.12,
        "runtime_hold_quality_score": 0.53,
        "runtime_partial_exit_ev": 0.57,
        "runtime_full_exit_risk": 0.19,
        "runtime_continuation_odds": 0.84,
        "runtime_reversal_odds": 0.47,
        "giveback_ratio": 0.0,
    }

    markdown = render_nas100_profit_hold_bias_action_preview_markdown(
        {
            "summary": {
                "baseline_runtime_proxy_match_rate": 0.94,
                "preview_runtime_proxy_match_rate": 0.96,
                "baseline_hold_precision": 0.75,
                "preview_hold_precision": 0.94,
                "baseline_partial_then_hold_quality": 0.97,
                "preview_partial_then_hold_quality": 0.98,
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "improved_row_count": 82,
                "worsened_row_count": 0,
                "casebook_examples": [sample_case],
                "recommended_next_action": "review_nas100_profit_hold_bias_preview_for_action_only_canary",
            },
        }
    )

    assert "# PA8 NAS100 Profit Hold Bias Action Preview" in markdown
    assert "- baseline_hold_precision: `0.75`" in markdown
    assert "- action_path: `HOLD -> PARTIAL_THEN_HOLD -> PARTIAL_THEN_HOLD`" in markdown
