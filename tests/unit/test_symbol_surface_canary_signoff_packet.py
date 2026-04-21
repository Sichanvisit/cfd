from backend.services.symbol_surface_canary_signoff_packet import (
    build_symbol_surface_canary_signoff_packet,
)


def test_symbol_surface_canary_signoff_packet_materializes_generic_review_packet() -> None:
    review_manifest_payload = {
        "rows": [
            {
                "manifest_id": "bounded_rollout_review_manifest::BTCUSD::initial_entry_surface",
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "adapter_mode": "btc_observe_relief_adapter",
                "rollout_mode": "review_canary_only",
                "positive_preview_ids": "[\"btc-1\"]",
                "negative_preview_ids": "[\"btc-2\"]",
                "review_checklist": "[\"check-1\"]",
                "guardrail_contract": "{\"allow_live_override\": false}",
            }
        ]
    }
    signoff_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "signoff_state": "READY_FOR_MANUAL_SIGNOFF",
                "recommended_decision": "APPROVE_REVIEW_CANARY_PENDING_MANUAL_SIGNOFF",
                "recommended_next_step": "manual_signoff_btcusd_initial_entry_surface_review_canary",
                "baseline_elapsed_ms": 91.0,
                "current_elapsed_ms": 92.0,
                "performance_gate_state": "PASS",
            }
        ]
    }

    frame, summary = build_symbol_surface_canary_signoff_packet(
        bounded_rollout_review_manifest_payload=review_manifest_payload,
        bounded_rollout_signoff_criteria_payload=signoff_payload,
    )

    assert summary["packet_row_count"] == 1
    row = frame.iloc[0]
    assert row["packet_status"] == "REVIEW_PACKET_READY"
    assert row["packet_id"] == "symbol_surface_review_canary_packet::BTCUSD::initial_entry_surface"
