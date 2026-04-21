import pandas as pd

from backend.services.hold_exit_augmentation_draft import build_hold_exit_augmentation_draft


def test_hold_exit_augmentation_draft_builds_hold_and_exit_contrasts() -> None:
    failure_payload = {
        "rows": [
            {
                "observation_event_id": "obs-early-exit",
                "market_family": "XAUUSD",
                "failure_label": "early_exit_regret",
                "harvest_strength": "confirmed",
                "time_axis_phase": "await_live_runner_preservation",
            }
        ]
    }
    protective_exit_dataset = pd.DataFrame(
        [
            {
                "preview_row_id": "protect-1",
                "market_family": "BTCUSD",
                "time_axis_phase": "protect_late",
            }
        ]
    )

    frame, summary = build_hold_exit_augmentation_draft(
        failure_label_harvest_payload=failure_payload,
        continuation_hold_dataset=pd.DataFrame(),
        protective_exit_dataset=protective_exit_dataset,
    )

    assert summary["row_count"] == 3
    assert set(frame["target_surface"].tolist()) == {
        "continuation_hold_surface",
        "protective_exit_surface",
    }
