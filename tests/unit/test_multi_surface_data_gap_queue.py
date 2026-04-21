from backend.services.multi_surface_data_gap_queue import build_multi_surface_data_gap_queue


def test_multi_surface_data_gap_queue_collects_followthrough_and_hold_exit_gaps() -> None:
    preview_eval_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "follow_through_surface",
                "readiness_state": "single_class_only",
                "row_count": 16,
                "positive_count": 16,
                "negative_count": 0,
                "recommended_action": "collect_negative_follow_through_rows",
            },
            {
                "market_family": "XAUUSD",
                "surface_name": "continuation_hold_surface",
                "readiness_state": "insufficient_rows",
                "row_count": 1,
                "positive_count": 1,
                "negative_count": 0,
                "recommended_action": "harvest_more_runner_preservation_rows",
            },
            {
                "market_family": "NAS100",
                "surface_name": "protective_exit_surface",
                "readiness_state": "insufficient_rows",
                "row_count": 7,
                "positive_count": 7,
                "negative_count": 0,
                "recommended_action": "collect_more_symbol_surface_rows",
            },
        ]
    }

    frame, summary = build_multi_surface_data_gap_queue(
        symbol_surface_preview_evaluation_payload=preview_eval_payload,
    )

    assert summary["queue_row_count"] == 3
    assert set(frame["gap_family"].tolist()) == {
        "negative_follow_through_gap",
        "runner_preservation_gap",
        "protective_exit_contrast_gap",
    }
