import pandas as pd

from backend.services.initial_entry_label_resolution_queue import (
    build_initial_entry_label_resolution_queue,
)


def test_initial_entry_label_resolution_queue_collects_all_needs_resolution_rows() -> None:
    preview_eval_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "readiness_state": "needs_label_resolution",
            },
            {
                "market_family": "NAS100",
                "surface_name": "initial_entry_surface",
                "readiness_state": "needs_label_resolution",
            },
            {
                "market_family": "XAUUSD",
                "surface_name": "initial_entry_surface",
                "readiness_state": "needs_label_resolution",
            },
        ]
    }
    dataset = pd.DataFrame(
        [
            {
                "preview_row_id": "btc-1",
                "market_family": "BTCUSD",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "enter_now_binary": None,
                "training_weight": 0.7,
                "time_axis_phase": "fresh_initial",
                "adapter_mode": "btc_observe_relief_adapter",
                "recommended_bias_action": "bias_follow_through_capture",
            },
            {
                "preview_row_id": "nas-1",
                "market_family": "NAS100",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "enter_now_binary": None,
                "training_weight": 0.7,
                "time_axis_phase": "fresh_initial",
                "adapter_mode": "nas_conflict_observe_adapter",
                "recommended_bias_action": "bias_release_wait",
            },
            {
                "preview_row_id": "xau-1",
                "market_family": "XAUUSD",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "enter_now_binary": None,
                "training_weight": 0.7,
                "time_axis_phase": "fresh_initial",
                "adapter_mode": "xau_initial_entry_selective_adapter",
                "recommended_bias_action": "bias_initial_entry_selectivity",
            },
        ]
    )

    frame, summary = build_initial_entry_label_resolution_queue(
        symbol_surface_preview_evaluation_payload=preview_eval_payload,
        initial_entry_dataset=dataset,
    )

    assert summary["queue_row_count"] == 3
    assert set(frame["market_family"].tolist()) == {"BTCUSD", "NAS100", "XAUUSD"}
    assert set(frame["recommended_resolution_path"].tolist()) == {"resolve_probe_entry_vs_wait"}
