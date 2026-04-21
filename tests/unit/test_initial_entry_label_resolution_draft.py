from backend.services.initial_entry_label_resolution_draft import (
    build_initial_entry_label_resolution_draft,
)


def test_initial_entry_label_resolution_draft_proposes_btc_nas_enter_and_xau_wait() -> None:
    queue_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "preview_row_id": "btc-1",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "adapter_mode": "btc_observe_relief_adapter",
                "recommended_bias_action": "bias_follow_through_capture",
            },
            {
                "market_family": "NAS100",
                "preview_row_id": "nas-1",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "adapter_mode": "nas_conflict_observe_adapter",
                "recommended_bias_action": "bias_neutral",
            },
            {
                "market_family": "XAUUSD",
                "preview_row_id": "xau-1",
                "surface_state": "timing_better_entry",
                "action_target": "PROBE_ENTRY",
                "adapter_mode": "xau_initial_entry_selective_adapter",
                "recommended_bias_action": "bias_initial_entry_selectivity",
            },
        ]
    }

    frame, summary = build_initial_entry_label_resolution_draft(
        initial_entry_label_resolution_queue_payload=queue_payload,
    )

    assert summary["row_count"] == 3
    btc = frame.loc[frame["market_family"] == "BTCUSD"].iloc[0]
    nas = frame.loc[frame["market_family"] == "NAS100"].iloc[0]
    xau = frame.loc[frame["market_family"] == "XAUUSD"].iloc[0]
    assert btc["proposed_enter_now_binary"] == 1
    assert nas["proposed_enter_now_binary"] == 1
    assert xau["proposed_enter_now_binary"] == 0
