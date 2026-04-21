from backend.services.bounded_symbol_surface_activation_apply import (
    build_bounded_symbol_surface_activation_apply,
)


def test_bounded_symbol_surface_activation_apply_activates_only_healthy_symbols() -> None:
    contract_payload = {
        "rows": [
            {"contract_id": "c1", "market_family": "BTCUSD", "surface_name": "initial_entry_surface", "contract_status": "PENDING_MANUAL_SIGNOFF", "activation_mode": "review_canary_bounded"},
            {"contract_id": "c2", "market_family": "NAS100", "surface_name": "initial_entry_surface", "contract_status": "PENDING_MANUAL_SIGNOFF", "activation_mode": "review_canary_bounded"},
            {"contract_id": "c3", "market_family": "XAUUSD", "surface_name": "initial_entry_surface", "contract_status": "PENDING_MANUAL_SIGNOFF", "activation_mode": "review_canary_bounded"},
        ]
    }
    signoff_apply_payload = {
        "rows": [
            {"market_family": "BTCUSD", "surface_name": "initial_entry_surface", "approval_state": "MANUAL_SIGNOFF_APPROVED", "requested_decision": "APPROVE"},
            {"market_family": "NAS100", "surface_name": "initial_entry_surface", "approval_state": "MANUAL_SIGNOFF_APPROVED", "requested_decision": "APPROVE"},
            {"market_family": "XAUUSD", "surface_name": "initial_entry_surface", "approval_state": "MANUAL_SIGNOFF_APPROVED", "requested_decision": "APPROVE"},
        ]
    }
    regression_watch_payload = {
        "reentry_elapsed_ms_threshold": 200.0,
        "comparisons": [
            {"symbol": "BTCUSD", "current_elapsed_ms": 120.0, "reentry_required": False, "status": "healthy"},
            {"symbol": "NAS100", "current_elapsed_ms": 277.0, "reentry_required": True, "status": "reentry_required"},
            {"symbol": "XAUUSD", "current_elapsed_ms": 150.0, "reentry_required": False, "status": "healthy"},
        ],
    }
    runtime_status = {"runtime_recycle": {"last_open_positions_count": 0}}

    frame, resolved_contract, summary = build_bounded_symbol_surface_activation_apply(
        bounded_symbol_surface_activation_contract_payload=contract_payload,
        symbol_surface_manual_signoff_apply_payload=signoff_apply_payload,
        entry_performance_regression_watch_payload=regression_watch_payload,
        runtime_status=runtime_status,
    )

    btc = frame.loc[frame["market_family"] == "BTCUSD"].iloc[0]
    nas = frame.loc[frame["market_family"] == "NAS100"].iloc[0]
    xau = frame.loc[frame["market_family"] == "XAUUSD"].iloc[0]

    assert btc["activation_state"] == "ACTIVE_REVIEW_CANARY"
    assert xau["activation_state"] == "ACTIVE_REVIEW_CANARY"
    assert nas["activation_state"] == "HOLD_PERFORMANCE_GUARD"
    assert summary["active_review_canary_count"] == 2
    assert resolved_contract.loc[resolved_contract["market_family"] == "NAS100", "contract_status"].iloc[0] == "APPROVED_PENDING_PERFORMANCE_RECOVERY"
