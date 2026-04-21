from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_canary_review_packet import (
    build_checkpoint_pa8_nas100_provisional_canary_review_packet,
    render_checkpoint_pa8_nas100_provisional_canary_review_markdown,
)


def test_build_checkpoint_pa8_nas100_provisional_canary_review_packet_marks_ready() -> None:
    payload = build_checkpoint_pa8_nas100_provisional_canary_review_packet(
        pa8_action_review_packet_payload={
            "summary": {
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "action_baseline_review_ready": True,
            },
            "symbol_rows": [
                {
                    "symbol": "NAS100",
                    "review_state": "PRIMARY_REVIEW",
                    "hold_precision": 0.759036,
                    "runtime_proxy_match_rate": 0.941077,
                }
            ],
        },
        nas100_symbol_review_payload={
            "summary": {
                "symbol": "NAS100",
                "review_result": "narrow_hold_boundary_candidate_identified",
            }
        },
        nas100_profit_hold_bias_preview_payload={
            "summary": {
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "improved_row_count": 82,
                "worsened_row_count": 0,
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
                "casebook_examples": [
                    {
                        "checkpoint_id": "CP1",
                        "baseline_action_label": "HOLD",
                        "preview_action_label": "PARTIAL_THEN_HOLD",
                        "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                        "checkpoint_rule_family_hint": "profit_hold_bias",
                    }
                ],
            }
        },
    )

    summary = payload["summary"]
    assert summary["provisional_canary_ready"] is True
    assert summary["canary_review_state"] == "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW"
    assert summary["recommended_next_action"] == "prepare_nas100_action_only_provisional_canary_scope"
    assert payload["candidate_scope"]["symbol_allowlist"] == ["NAS100"]
    assert payload["candidate_scope"]["preview_action"] == "PARTIAL_THEN_HOLD"


def test_build_checkpoint_pa8_nas100_provisional_canary_review_packet_holds_with_worsened_rows() -> None:
    payload = build_checkpoint_pa8_nas100_provisional_canary_review_packet(
        pa8_action_review_packet_payload={
            "summary": {
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "action_baseline_review_ready": True,
            },
            "symbol_rows": [{"symbol": "NAS100", "review_state": "PRIMARY_REVIEW"}],
        },
        nas100_symbol_review_payload={
            "summary": {
                "symbol": "NAS100",
                "review_result": "narrow_hold_boundary_candidate_identified",
            }
        },
        nas100_profit_hold_bias_preview_payload={
            "summary": {
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "improved_row_count": 80,
                "worsened_row_count": 2,
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.82,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.95,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
            }
        },
    )

    summary = payload["summary"]
    assert summary["provisional_canary_ready"] is False
    assert summary["canary_review_state"] == "HOLD_PREVIEW_ONLY_REVIEW"
    assert "preview_has_worsened_rows" in summary["blockers"]


def test_render_checkpoint_pa8_nas100_provisional_canary_review_markdown_contains_scope() -> None:
    markdown = render_checkpoint_pa8_nas100_provisional_canary_review_markdown(
        {
            "summary": {
                "canary_review_state": "READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW",
                "provisional_canary_ready": True,
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "eligible_row_count": 82,
                "preview_changed_row_count": 82,
                "improved_row_count": 82,
                "worsened_row_count": 0,
                "baseline_hold_precision": 0.759036,
                "preview_hold_precision": 0.945946,
                "baseline_runtime_proxy_match_rate": 0.941077,
                "preview_runtime_proxy_match_rate": 0.964195,
                "baseline_partial_then_hold_quality": 0.971302,
                "preview_partial_then_hold_quality": 0.975701,
                "recommended_next_action": "prepare_nas100_action_only_provisional_canary_scope",
                "casebook_examples": [
                    {
                        "checkpoint_id": "CP1",
                        "baseline_action_label": "HOLD",
                        "preview_action_label": "PARTIAL_THEN_HOLD",
                        "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
                        "checkpoint_rule_family_hint": "profit_hold_bias",
                    }
                ],
                "blockers": [],
            },
            "candidate_scope": {
                "symbol_allowlist": ["NAS100"],
                "surface_allowlist": ["continuation_hold_surface"],
                "checkpoint_type_allowlist": ["RUNNER_CHECK"],
                "family_allowlist": ["profit_hold_bias"],
                "baseline_action_allowlist": ["HOLD"],
                "preview_action": "PARTIAL_THEN_HOLD",
                "scene_bias_mode": "preview_only_excluded_from_canary_scope",
            },
            "canary_guardrails": {
                "sample_floor": 50,
                "worsened_row_count_ceiling": 0,
                "hold_precision_floor": 0.8,
                "runtime_proxy_match_rate_must_improve": True,
                "partial_then_hold_quality_must_not_regress": True,
            },
        }
    )

    assert "# PA8 NAS100 Provisional Action-Only Canary Review" in markdown
    assert "- preview_hold_precision: `0.945946`" in markdown
    assert '- symbol_allowlist: `["NAS100"]`' in markdown
    assert "- action_path: `HOLD -> PARTIAL_THEN_HOLD -> PARTIAL_THEN_HOLD`" in markdown
