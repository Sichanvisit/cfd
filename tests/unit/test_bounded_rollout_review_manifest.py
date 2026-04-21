import pandas as pd

from backend.services.bounded_rollout_review_manifest import (
    build_bounded_rollout_review_manifest,
    render_bounded_rollout_review_manifest_markdown,
)


def test_bounded_rollout_review_manifest_materializes_btc_canary_packet() -> None:
    candidate_gate_payload = {
        "rows": [
            {
                "candidate_id": "bounded_rollout_candidate::BTCUSD::initial_entry_surface",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "btc_observe_relief_adapter",
                "row_count": 15,
                "strong_row_count": 7,
                "positive_count": 10,
                "negative_count": 5,
                "unlabeled_ratio": 0.0,
                "local_failure_burden": 0.333333,
                "rollout_candidate_state": "REVIEW_CANARY_CANDIDATE",
                "rollout_priority": "P1",
                "recommended_next_step": "prepare_btcusd_initial_entry_canary_review",
            }
        ]
    }
    preview_eval_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "readiness_state": "preview_eval_ready",
            }
        ]
    }
    initial_entry_dataset = pd.DataFrame(
        [
            {"preview_row_id": "btc-1", "market_family": "BTCUSD", "enter_now_binary": 1, "training_weight": 1.0},
            {"preview_row_id": "btc-2", "market_family": "BTCUSD", "enter_now_binary": 1, "training_weight": 1.0},
            {"preview_row_id": "btc-3", "market_family": "BTCUSD", "enter_now_binary": 0, "training_weight": 0.45},
        ]
    )

    frame, summary = build_bounded_rollout_review_manifest(
        bounded_rollout_candidate_gate_payload=candidate_gate_payload,
        symbol_surface_preview_evaluation_payload=preview_eval_payload,
        initial_entry_dataset=initial_entry_dataset,
    )
    markdown = render_bounded_rollout_review_manifest_markdown(summary, frame)

    assert summary["manifest_row_count"] == 1
    row = frame.iloc[0]
    assert row["market_family"] == "BTCUSD"
    assert row["manifest_status"] == "REVIEW_READY"
    assert row["rollout_mode"] == "review_canary_only"
    assert "btc-1" in row["positive_preview_ids"]
    assert "btc-3" in row["negative_preview_ids"]
    assert "Bounded Rollout Review Manifest" in markdown
