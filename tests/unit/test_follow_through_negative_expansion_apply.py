import pandas as pd

from backend.services.follow_through_negative_expansion_apply import (
    build_follow_through_negative_expansion_apply,
)


def test_follow_through_negative_expansion_apply_appends_negative_rows() -> None:
    dataset = pd.DataFrame(
        [
            {
                "preview_row_id": "base-1",
                "symbol": "BTCUSD",
                "market_family": "BTCUSD",
                "surface_state": "pullback_resume",
                "continuation_target": "PULLBACK_THEN_CONTINUE",
                "continuation_positive_binary": 1,
                "failure_label": "",
                "training_weight": 1.0,
                "time_axis_phase": "continuation_window",
                "adapter_mode": "btc_follow_through_balance_adapter",
                "recommended_bias_action": "bias_neutral",
                "objective_key": "follow_through_extension_ev",
            }
        ]
    )
    draft_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "source_observation_id": "obs-1",
                "surface_state": "continuation_follow",
                "continuation_target": "NOT_CONTINUE",
                "continuation_positive_binary": 0,
                "draft_weight": 0.7,
                "draft_source_strength": "candidate",
                "draft_reason": "false_breakout",
                "time_axis_phase": "continuation_window",
            }
        ]
    }

    frame, augmented, summary = build_follow_through_negative_expansion_apply(
        follow_through_dataset=dataset,
        follow_through_negative_expansion_draft_payload=draft_payload,
    )

    assert summary["applied_row_count"] == 1
    assert len(augmented) == 2
    added = augmented.loc[augmented["augmentation_source_observation_id"] == "obs-1"].iloc[0]
    assert int(added["continuation_positive_binary"]) == 0
    assert added["failure_label"] == "false_breakout"
    assert added["augmentation_status"] == "APPLIED_NEGATIVE_EXPANSION_DRAFT"
