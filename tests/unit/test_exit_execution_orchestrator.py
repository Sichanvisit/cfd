from backend.services.exit_execution_orchestrator import (
    resolve_exit_execution_plan_v1,
)


def test_exit_execution_orchestrator_selects_first_hit_in_order():
    plan = resolve_exit_execution_plan_v1(
        phase="managed_exit",
        candidates=[
            {"candidate_kind": "protect_exit", "should_execute": False},
            {"candidate_kind": "adverse_reverse", "should_execute": True, "reason": "Adverse Reversal"},
            {"candidate_kind": "lock_exit", "should_execute": True, "reason": "Lock Exit"},
        ],
    )

    assert plan["contract_version"] == "exit_execution_plan_v1"
    assert plan["selected"] is True
    assert plan["selected_index"] == 1
    assert plan["selected_candidate_kind"] == "adverse_reverse"
    assert plan["selected_reason"] == "Adverse Reversal"
    assert plan["plan_status"] == "execute"


def test_exit_execution_orchestrator_carries_reverse_surface():
    plan = resolve_exit_execution_plan_v1(
        phase="recovery",
        candidates=[
            {
                "candidate_kind": "recovery_reverse",
                "should_execute": True,
                "reason": "Recovery Reverse",
                "reverse_action": "SELL",
                "reverse_score": 88.0,
                "reverse_reasons": ["reverse_now"],
            }
        ],
    )

    assert plan["selected"] is True
    assert plan["reverse_action"] == "SELL"
    assert plan["reverse_score"] == 88.0
    assert plan["reverse_reasons"] == ["reverse_now"]


def test_exit_execution_orchestrator_returns_hold_when_no_candidate_selected():
    plan = resolve_exit_execution_plan_v1(
        phase="managed_exit",
        candidates=[
            {"candidate_kind": "protect_exit", "should_execute": False},
            {"candidate_kind": "lock_exit", "should_execute": False},
        ],
    )

    assert plan["selected"] is False
    assert plan["selected_index"] == -1
    assert plan["selected_candidate_kind"] == ""
    assert plan["plan_status"] == "hold"
