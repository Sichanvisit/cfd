import pandas as pd

from backend.services.hold_exit_augmentation_apply import (
    build_hold_exit_augmentation_apply,
)


def test_hold_exit_augmentation_apply_appends_hold_and_protect_rows() -> None:
    hold_dataset = pd.DataFrame(
        [
            {
                "preview_row_id": "hold-base-1",
                "symbol": "XAUUSD",
                "market_family": "XAUUSD",
                "surface_state": "runner_hold",
                "hold_target": "HOLD_RUNNER",
                "hold_runner_binary": 1,
                "failure_label": "",
                "training_weight": 0.35,
                "time_axis_phase": "await_live_runner_preservation",
                "adapter_mode": "xau_runner_preservation_adapter",
                "recommended_bias_action": "bias_runner_hold",
                "objective_key": "runner_hold_ev",
            }
        ]
    )
    protect_dataset = pd.DataFrame(
        [
            {
                "preview_row_id": "protect-base-1",
                "symbol": "BTCUSD",
                "market_family": "BTCUSD",
                "surface_state": "protect_exit",
                "protect_target": "EXIT_PROTECT",
                "protect_exit_binary": 1,
                "failure_label": "",
                "training_weight": 1.0,
                "time_axis_phase": "protect_late",
                "adapter_mode": "protective_exit_balance_adapter",
                "recommended_bias_action": "bias_protective_dampen",
                "objective_key": "protect_exit_loss_avoidance_ev",
            }
        ]
    )
    draft_payload = {
        "rows": [
            {
                "market_family": "XAUUSD",
                "target_surface": "continuation_hold_surface",
                "target_binary": 0,
                "source_row_id": "src-hold-1",
                "draft_reason": "late_or_active_protect_exit_can_supply_not_hold_runner_contrast",
                "draft_weight": 0.7,
                "time_axis_phase": "protect_late",
            },
            {
                "market_family": "BTCUSD",
                "target_surface": "protective_exit_surface",
                "target_binary": 0,
                "source_row_id": "src-protect-1",
                "draft_reason": "early_exit_regret_should_add_false_cut_negative_contrast",
                "draft_weight": 0.45,
                "time_axis_phase": "await_live_runner_preservation",
            },
        ]
    }

    frame, augmented_hold, augmented_protect, summary = build_hold_exit_augmentation_apply(
        continuation_hold_dataset=hold_dataset,
        protective_exit_dataset=protect_dataset,
        hold_exit_augmentation_draft_payload=draft_payload,
    )

    assert summary["applied_row_count"] == 2
    assert len(augmented_hold) == 2
    assert len(augmented_protect) == 2
    hold_added = augmented_hold.loc[augmented_hold["augmentation_source_row_id"] == "src-hold-1"].iloc[0]
    protect_added = augmented_protect.loc[augmented_protect["augmentation_source_row_id"] == "src-protect-1"].iloc[0]
    assert int(hold_added["hold_runner_binary"]) == 0
    assert int(protect_added["protect_exit_binary"]) == 0
    assert set(frame["apply_status"]) == {"APPLIED_HOLD_EXIT_AUGMENTATION_DRAFT"}
