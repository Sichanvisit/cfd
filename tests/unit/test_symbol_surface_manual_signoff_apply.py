from backend.services.symbol_surface_manual_signoff_apply import (
    build_symbol_surface_manual_signoff_apply,
)


def test_symbol_surface_manual_signoff_apply_approves_review_ready_packets() -> None:
    payload = {
        "rows": [
            {"packet_id": "p1", "market_family": "BTCUSD", "surface_name": "initial_entry_surface", "packet_status": "REVIEW_PACKET_READY", "signoff_state": "READY_FOR_MANUAL_SIGNOFF"},
            {"packet_id": "p2", "market_family": "NAS100", "surface_name": "initial_entry_surface", "packet_status": "REVIEW_PACKET_READY", "signoff_state": "READY_FOR_MANUAL_SIGNOFF"},
            {"packet_id": "p3", "market_family": "XAUUSD", "surface_name": "initial_entry_surface", "packet_status": "REVIEW_PACKET_READY", "signoff_state": "READY_FOR_MANUAL_SIGNOFF"},
        ]
    }

    frame, summary = build_symbol_surface_manual_signoff_apply(
        symbol_surface_canary_signoff_packet_payload=payload,
        approve_all_review_ready=True,
    )

    assert summary["approved_count"] == 3
    assert set(frame["approval_state"]) == {"MANUAL_SIGNOFF_APPROVED"}
    assert frame["allow_activation_after_apply"].tolist() == [True, True, True]
