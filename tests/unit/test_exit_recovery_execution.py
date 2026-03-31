from types import SimpleNamespace

from backend.services.exit_manage_positions import _resolve_recovery_execution


def _wait_state(state: str, **metadata):
    return SimpleNamespace(state=state, metadata=metadata)


def test_recovery_execution_closes_at_breakeven():
    decision = _resolve_recovery_execution(
        profit=0.03,
        adverse_risk=False,
        duration_sec=40.0,
        tf_confirm=True,
        score_gap=6,
        exit_wait_state=_wait_state("RECOVERY_BE", recovery_wait_max_seconds=240, recovery_be_max_loss=0.9),
        exit_shadow={"winner": "wait_be"},
    )

    assert decision["mode"] == "exit"
    assert decision["close_reason"] == "Recovery BE"


def test_recovery_execution_holds_small_loss_tp1():
    decision = _resolve_recovery_execution(
        profit=-0.08,
        adverse_risk=False,
        duration_sec=40.0,
        tf_confirm=True,
        score_gap=6,
        exit_wait_state=_wait_state("RECOVERY_TP1", recovery_wait_max_seconds=240, recovery_tp1_max_loss=0.35),
        exit_shadow={"winner": "wait_tp1"},
    )

    assert decision["mode"] == "hold"
    assert decision["reason"] == "recovery_tp1_hold"


def test_recovery_execution_triggers_reverse_when_confirmed():
    decision = _resolve_recovery_execution(
        profit=-0.22,
        adverse_risk=True,
        duration_sec=60.0,
        tf_confirm=True,
        score_gap=30,
        exit_wait_state=_wait_state("REVERSE_READY", reverse_score_gap=26),
        exit_shadow={"winner": "reverse_now", "p_reverse_valid": 0.72},
    )

    assert decision["mode"] == "reverse"
    assert decision["can_reverse"] is True


def test_recovery_execution_blocks_reverse_when_prob_is_too_low():
    decision = _resolve_recovery_execution(
        profit=-0.22,
        adverse_risk=True,
        duration_sec=60.0,
        tf_confirm=True,
        score_gap=30,
        exit_wait_state=_wait_state("REVERSE_READY", reverse_score_gap=26),
        exit_shadow={"winner": "reverse_now", "p_reverse_valid": 0.34},
    )

    assert decision["mode"] == "none"
