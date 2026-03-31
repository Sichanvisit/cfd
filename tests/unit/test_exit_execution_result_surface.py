from backend.services.exit_execution_result_surface import (
    build_exit_execution_result_surface_v1,
)


def test_exit_execution_result_surface_builds_selected_payload():
    surface = build_exit_execution_result_surface_v1(
        symbol="BTCUSD",
        ticket=1001,
        execution_plan_v1={
            "phase": "managed_exit",
            "selected": True,
            "selected_candidate_kind": "lock_exit",
            "selected_reason": "Lock Exit",
            "selected_detail": "detail",
            "selected_metric_keys": ["exit_lock"],
            "reverse_action": "",
            "reverse_score": 0.0,
            "reverse_reasons": [],
        },
        execution_status="selected",
    )

    assert surface["contract_version"] == "exit_execution_result_surface_v1"
    assert surface["summary"]["selected"] is True
    assert surface["trade_logger_payload"]["exit_reason"] == "Lock Exit"
    assert surface["trade_logger_payload"]["policy_scope"] == "exit_execution:managed_exit:lock_exit"
    assert surface["live_metrics_payload"]["exit_execution_candidate_kind"] == "lock_exit"


def test_exit_execution_result_surface_builds_hold_surface_without_logger_update():
    surface = build_exit_execution_result_surface_v1(
        symbol="BTCUSD",
        ticket=1001,
        execution_plan_v1={
            "phase": "managed_exit",
            "selected": False,
            "selected_candidate_kind": "",
            "selected_reason": "",
        },
        execution_status="hold",
    )

    assert surface["summary"]["selected"] is False
    assert surface["trade_logger_payload"] == {}
    assert surface["live_metrics_payload"]["exit_execution_status"] == "hold"
