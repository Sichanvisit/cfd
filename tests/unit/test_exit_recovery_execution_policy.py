from types import SimpleNamespace

from backend.services.exit_recovery_execution_policy import (
    resolve_exit_recovery_execution_candidate_v1,
)


def _wait_state(state: str):
    return SimpleNamespace(state=state)


def test_exit_recovery_execution_policy_closes_at_breakeven():
    decision = resolve_exit_recovery_execution_candidate_v1(
        profit=0.03,
        adverse_risk=False,
        duration_sec=40.0,
        tf_confirm=True,
        score_gap=6,
        wait_state=_wait_state("RECOVERY_BE"),
        wait_metadata={"recovery_wait_max_seconds": 240, "recovery_be_max_loss": 0.9},
        exit_shadow={"winner": "wait_be"},
    )

    assert decision["contract_version"] == "exit_recovery_execution_candidate_v1"
    assert decision["mode"] == "exit"
    assert decision["close_reason"] == "Recovery BE"


def test_exit_recovery_execution_policy_triggers_reverse_when_confirmed():
    decision = resolve_exit_recovery_execution_candidate_v1(
        profit=-0.22,
        adverse_risk=True,
        duration_sec=60.0,
        tf_confirm=True,
        score_gap=30,
        wait_state=_wait_state("REVERSE_READY"),
        wait_metadata={"reverse_score_gap": 26},
        exit_shadow={"winner": "reverse_now", "p_reverse_valid": 0.72},
    )

    assert decision["mode"] == "reverse"
    assert decision["can_reverse"] is True
    assert decision["candidate_kind"] == "recovery_reverse_execute"
