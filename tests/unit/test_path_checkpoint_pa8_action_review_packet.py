from __future__ import annotations

from backend.services.path_checkpoint_pa8_action_review_packet import build_checkpoint_pa8_action_review_packet


def test_build_checkpoint_pa8_action_review_packet_builds_symbol_review_order() -> None:
    payload = build_checkpoint_pa8_action_review_packet(
        pa78_review_packet_payload={
            "summary": {
                "pa8_review_state": "READY_FOR_ACTION_BASELINE_REVIEW",
                "scene_bias_review_state": "HOLD_PREVIEW_ONLY_SCENE_BIAS",
                "action_baseline_review_ready": True,
                "recommended_next_action": "prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only",
            }
        },
        action_eval_payload={
            "summary": {
                "resolved_row_count": 5385,
                "runtime_proxy_match_rate": 0.92182,
                "hold_precision": 0.848057,
                "partial_then_hold_quality": 0.953634,
                "full_exit_precision": 0.998647,
            },
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "resolved_row_count": 1434,
                    "runtime_proxy_match_rate": 0.889121,
                    "hold_precision": 0.944984,
                    "partial_then_hold_quality": 0.93,
                    "full_exit_precision": 0.997455,
                    "quality_tier_counts": "{\"manual_exception\": 443}",
                    "hindsight_label_counts": "{\"WAIT\": 375}",
                    "recommended_focus": "inspect_btcusd_manual_exception_labels",
                },
                {
                    "symbol": "NAS100",
                    "resolved_row_count": 3547,
                    "runtime_proxy_match_rate": 0.941077,
                    "hold_precision": 0.759036,
                    "partial_then_hold_quality": 0.971302,
                    "full_exit_precision": 1.0,
                    "quality_tier_counts": "{\"manual_exception\": 693}",
                    "hindsight_label_counts": "{\"WAIT\": 544}",
                    "recommended_focus": "inspect_nas100_manual_exception_labels",
                },
                {
                    "symbol": "XAUUSD",
                    "resolved_row_count": 404,
                    "runtime_proxy_match_rate": 0.868812,
                    "hold_precision": 0.904,
                    "partial_then_hold_quality": 0.933333,
                    "full_exit_precision": 0.976744,
                    "quality_tier_counts": "{\"manual_exception\": 156}",
                    "hindsight_label_counts": "{\"WAIT\": 119}",
                    "recommended_focus": "inspect_xauusd_manual_exception_labels",
                },
            ],
        },
        management_action_snapshot_payload={
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "management_action_counts": "{\"FULL_EXIT\": 8, \"HOLD\": 54}",
                    "recommended_focus": "inspect_btcusd_full_exit_precision",
                },
                {
                    "symbol": "NAS100",
                    "management_action_counts": "{\"FULL_EXIT\": 117, \"HOLD\": 19}",
                    "recommended_focus": "inspect_nas100_full_exit_precision",
                },
                {
                    "symbol": "XAUUSD",
                    "management_action_counts": "{\"FULL_EXIT\": 9, \"HOLD\": 32}",
                    "recommended_focus": "inspect_xauusd_full_exit_precision",
                },
            ]
        },
        observation_payload={
            "rows": [
                {
                    "symbol": "BTCUSD",
                    "live_runner_source_row_count": 573,
                    "family_counts": "{\"runner_secured_continuation\": 654}",
                    "recommended_focus": "inspect_btcusd_position_side_balance",
                },
                {
                    "symbol": "NAS100",
                    "live_runner_source_row_count": 515,
                    "family_counts": "{\"active_open_loss\": 1948}",
                    "recommended_focus": "inspect_nas100_position_side_balance",
                },
                {
                    "symbol": "XAUUSD",
                    "live_runner_source_row_count": 50,
                    "family_counts": "{\"open_loss_protective\": 111}",
                    "recommended_focus": "inspect_xauusd_position_side_balance",
                },
            ]
        },
        live_runner_watch_payload={
            "rows": [
                {"symbol": "BTCUSD", "live_runner_source_row_count": 573, "recent_live_runner_source_row_count": 30},
                {"symbol": "NAS100", "live_runner_source_row_count": 515, "recent_live_runner_source_row_count": 82},
                {"symbol": "XAUUSD", "live_runner_source_row_count": 50, "recent_live_runner_source_row_count": 5},
            ]
        },
    )

    summary = payload["summary"]
    assert summary["overall_review_state"] == "READY_FOR_HUMAN_ACTION_REVIEW"
    assert summary["pa8_review_state"] == "READY_FOR_ACTION_BASELINE_REVIEW"
    assert summary["scene_bias_review_state"] == "HOLD_PREVIEW_ONLY_SCENE_BIAS"
    assert summary["primary_review_symbols"] == ["NAS100", "BTCUSD"]
    assert summary["support_review_symbols"] == ["XAUUSD"]
    assert summary["canary_candidate_symbols"] == []

    rows = {row["symbol"]: row for row in payload["symbol_rows"]}
    assert rows["NAS100"]["review_state"] == "PRIMARY_REVIEW"
    assert "inspect_hold_precision_boundary" in rows["NAS100"]["review_focuses"]
    assert rows["BTCUSD"]["review_state"] == "PRIMARY_REVIEW"
    assert "inspect_runtime_proxy_alignment" in rows["BTCUSD"]["review_focuses"]
    assert rows["XAUUSD"]["review_state"] == "SUPPORT_REVIEW_ONLY"
    assert "collect_more_symbol_rows" in rows["XAUUSD"]["review_focuses"]
