from backend.services.follow_through_negative_expansion_draft import (
    build_follow_through_negative_expansion_draft,
)


def test_follow_through_negative_expansion_draft_materializes_negative_rows() -> None:
    failure_payload = {
        "rows": [
            {
                "observation_event_id": "obs-1",
                "market_family": "XAUUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "pullback_resume",
                "failure_label": "failed_follow_through",
                "harvest_strength": "confirmed",
                "time_axis_phase": "continuation_window",
            }
        ]
    }

    frame, summary = build_follow_through_negative_expansion_draft(
        failure_label_harvest_payload=failure_payload,
    )

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["continuation_positive_binary"] == 0
    assert row["draft_weight"] == 1.0


def test_follow_through_negative_expansion_draft_accepts_wrong_side_conflict_labels() -> None:
    failure_payload = {
        "rows": [
            {
                "observation_event_id": "obs-2",
                "market_family": "XAUUSD",
                "surface_label_family": "follow_through_surface",
                "surface_label_state": "continuation_follow",
                "failure_label": "wrong_side_sell_pressure",
                "harvest_strength": "candidate",
                "time_axis_phase": "",
            }
        ]
    }

    frame, summary = build_follow_through_negative_expansion_draft(
        failure_label_harvest_payload=failure_payload,
    )

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["draft_reason"] == "wrong_side_sell_pressure"
    assert row["draft_weight"] == 0.45
