from backend.services.bounded_btc_review_canary_activation_contract import (
    build_bounded_btc_review_canary_activation_contract,
)


def test_bounded_btc_review_canary_activation_contract_stays_pending_until_manual_signoff() -> None:
    signoff_packet_payload = {
        "rows": [
            {
                "market_family": "BTCUSD",
                "surface_name": "initial_entry_surface",
                "packet_status": "REVIEW_PACKET_READY",
                "signoff_state": "READY_FOR_MANUAL_SIGNOFF",
            }
        ]
    }

    frame, summary = build_bounded_btc_review_canary_activation_contract(
        btc_initial_entry_canary_signoff_packet_payload=signoff_packet_payload,
    )

    assert summary["row_count"] == 1
    row = frame.iloc[0]
    assert row["contract_status"] == "PENDING_MANUAL_SIGNOFF"
    assert bool(row["allow_live_activation"]) is False
    assert row["recommended_next_step"] == "manual_signoff_btcusd_initial_entry_review_canary"
