from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_review_checklist import (
    build_checkpoint_pa8_action_review_checklist,
    render_checkpoint_pa8_action_review_checklist_markdown,
)


def test_build_checkpoint_pa8_action_review_checklist_orders_symbols_and_builds_checks() -> None:
    payload = build_checkpoint_pa8_action_review_checklist(
        pa8_action_review_packet_payload={
            "summary": {
                "overall_review_state": "READY_FOR_HUMAN_ACTION_REVIEW",
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "review_order": ["NAS100", "BTCUSD", "XAUUSD"],
                "primary_review_symbols": ["NAS100", "BTCUSD"],
                "support_review_symbols": ["XAUUSD"],
                "recommended_next_action": "review_primary_symbols_then_decide_if_action_only_canary_should_wait",
                "scene_bias_separation_note": "scene_bias_remains_preview_only_while_pa8_reviews_action_baseline",
            },
            "symbol_rows": [
                {
                    "symbol": "NAS100",
                    "review_state": "PRIMARY_REVIEW",
                    "review_blockers": ["hold_precision_below_symbol_floor"],
                    "review_focuses": ["inspect_hold_precision_boundary"],
                    "resolved_row_count": 3547,
                    "live_runner_source_row_count": 515,
                    "runtime_proxy_match_rate": 0.941077,
                    "hold_precision": 0.759036,
                    "partial_then_hold_quality": 0.971302,
                    "full_exit_precision": 1.0,
                },
                {
                    "symbol": "BTCUSD",
                    "review_state": "PRIMARY_REVIEW",
                    "review_blockers": [
                        "runtime_proxy_match_rate_below_symbol_floor",
                        "partial_then_hold_quality_below_symbol_floor",
                    ],
                    "review_focuses": ["inspect_runtime_proxy_alignment", "inspect_partial_then_hold_boundary"],
                    "resolved_row_count": 1434,
                    "live_runner_source_row_count": 573,
                    "runtime_proxy_match_rate": 0.889121,
                    "hold_precision": 0.944984,
                    "partial_then_hold_quality": 0.93,
                    "full_exit_precision": 0.997455,
                },
            ],
        }
    )

    summary = payload["summary"]
    assert summary["review_order"] == ["NAS100", "BTCUSD", "XAUUSD"]
    rows = payload["checklist_rows"]
    assert rows[0]["symbol"] == "NAS100"
    assert rows[0]["review_order"] == 1
    assert "Raise hold_precision to at least 0.80" in rows[0]["pass_criteria"][0]
    assert any("inspect_hold_precision_boundary" in item for item in rows[0]["check_items"])
    assert rows[1]["symbol"] == "BTCUSD"
    assert any("inspect_runtime_proxy_alignment" in item for item in rows[1]["check_items"])


def test_render_checkpoint_pa8_action_review_checklist_markdown_contains_sections() -> None:
    markdown = render_checkpoint_pa8_action_review_checklist_markdown(
        {
            "summary": {
                "overall_review_state": "READY_FOR_HUMAN_ACTION_REVIEW",
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "review_order": ["NAS100"],
                "recommended_next_action": "review_primary_symbols_then_decide_if_action_only_canary_should_wait",
                "scene_bias_note": "scene_bias_remains_preview_only_while_pa8_reviews_action_baseline",
            },
            "checklist_rows": [
                {
                    "review_order": 1,
                    "symbol": "NAS100",
                    "review_state": "PRIMARY_REVIEW",
                    "goal": "Confirm whether the HOLD boundary for NAS100 is actually correct against hindsight outcomes.",
                    "current_metrics": {
                        "resolved_row_count": 3547,
                        "live_runner_source_row_count": 515,
                        "runtime_proxy_match_rate": 0.941077,
                        "hold_precision": 0.759036,
                        "partial_then_hold_quality": 0.971302,
                        "full_exit_precision": 1.0,
                    },
                    "blockers": ["hold_precision_below_symbol_floor"],
                    "pass_criteria": [
                        "Raise hold_precision to at least 0.80, or explain with review evidence why the remaining gap is isolated to a narrow family."
                    ],
                    "check_items": ["Inspect rows for `inspect_hold_precision_boundary` first."],
                    "decision_options": ["Open a patch or review task for the current blocker."],
                }
            ],
        }
    )

    assert "# PA8 Action-Only Review Checklist" in markdown
    assert "## 1. NAS100" in markdown
    assert "- [ ] Inspect rows for `inspect_hold_precision_boundary` first." in markdown
