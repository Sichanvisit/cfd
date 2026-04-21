from __future__ import annotations

from pathlib import Path

from backend.services.checkpoint_improvement_pa7_narrow_review_runtime import (
    build_checkpoint_improvement_pa7_narrow_review_runtime,
)


def _board(status: str = "REVIEW_NEEDED") -> dict[str, object]:
    return {
        "readiness_state": {
            "pa7_narrow_review_surface": {
                "status": status,
                "recommended_next_action": "review_remaining_mixed_wait_boundary_groups_before_first_closeout",
                "primary_group_key": "BTCUSD::mixed",
                "primary_symbol": "BTCUSD",
            }
        }
    }


def _processor_payload() -> dict[str, object]:
    return {
        "summary": {
            "recommended_next_action": "inspect_mixed_wait_boundary_groups",
        },
        "group_rows": [
            {
                "group_key": "BTCUSD | follow_through_surface | INITIAL_PUSH | active_open_loss | active_open_loss | WAIT",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "INITIAL_PUSH",
                "review_disposition": "mixed_wait_boundary_review",
                "row_count": 6,
                "avg_abs_current_profit": 0.44,
                "avg_giveback_ratio": 0.99,
                "resolved_baseline_action_label": "HOLD",
                "policy_replay_action_label": "HOLD",
                "hindsight_best_management_action_label": "WAIT",
                "review_priority": "medium",
                "review_reason": "wait_boundary",
            },
            {
                "group_key": "BTCUSD | follow_through_surface | FIRST_PULLBACK_CHECK | active_open_loss | active_open_loss | WAIT",
                "symbol": "BTCUSD",
                "surface_name": "follow_through_surface",
                "checkpoint_type": "FIRST_PULLBACK_CHECK",
                "review_disposition": "mixed_review",
                "row_count": 5,
                "avg_abs_current_profit": 0.22,
                "avg_giveback_ratio": 0.99,
                "resolved_baseline_action_label": "WAIT",
                "policy_replay_action_label": "WAIT",
                "hindsight_best_management_action_label": "WAIT",
                "review_priority": "medium",
                "review_reason": "mixed_alignment",
            },
        ],
    }


def test_pa7_narrow_review_runtime_builds_detailed_rows(tmp_path: Path) -> None:
    payload = build_checkpoint_improvement_pa7_narrow_review_runtime(
        master_board_payload=_board(),
        pa7_review_processor_payload=_processor_payload(),
        now_ts="2026-04-13T05:03:00+09:00",
        output_json_path=tmp_path / "pa7.json",
        output_markdown_path=tmp_path / "pa7.md",
    )

    assert payload["summary"]["status"] == "REVIEW_NEEDED"
    assert payload["summary"]["group_count"] == 2
    assert payload["rows"][0]["lane_label_ko"] == "WAIT 경계 혼합 review"
    assert payload["rows"][1]["lane_label_ko"] == "일반 혼합 review"
