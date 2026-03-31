from backend.domain.decision_models import WaitState
from backend.services.exit_wait_taxonomy_contract import (
    build_exit_wait_taxonomy_v1,
    compact_exit_wait_taxonomy_v1,
)


def test_exit_wait_taxonomy_maps_confirm_wait_surface():
    taxonomy = compact_exit_wait_taxonomy_v1(
        build_exit_wait_taxonomy_v1(
            wait_state=WaitState(
                phase="exit",
                state="REVERSAL_CONFIRM",
                hard_wait=True,
                reason="opposite_signal_unconfirmed",
            ),
            utility_result={
                "winner": "wait_exit",
                "decision_reason": "wait_exit_reversal_confirm",
                "wait_selected": True,
                "wait_decision": "wait_exit_reversal_confirm",
            },
        )
    )

    assert taxonomy["state"]["state_family"] == "confirm_hold"
    assert taxonomy["state"]["hold_class"] == "hard_hold"
    assert taxonomy["decision"]["decision_family"] == "wait_exit"
    assert taxonomy["bridge"]["bridge_status"] == "aligned_confirm_wait"


def test_exit_wait_taxonomy_maps_recovery_wait_surface():
    taxonomy = compact_exit_wait_taxonomy_v1(
        build_exit_wait_taxonomy_v1(
            wait_state=WaitState(
                phase="exit",
                state="RECOVERY_TP1",
                hard_wait=False,
                reason="recovery_to_small_profit",
            ),
            utility_result={
                "winner": "wait_tp1",
                "decision_reason": "wait_tp1_recovery",
                "wait_selected": True,
                "wait_decision": "wait_tp1_recovery",
            },
        )
    )

    assert taxonomy["state"]["state_family"] == "recovery_hold"
    assert taxonomy["state"]["recovery_variant"] == "tp1"
    assert taxonomy["decision"]["decision_family"] == "recovery_wait"
    assert taxonomy["decision"]["recovery_variant"] == "tp1"
    assert taxonomy["bridge"]["bridge_status"] == "aligned_recovery_wait"


def test_exit_wait_taxonomy_maps_reverse_ready_surface():
    taxonomy = compact_exit_wait_taxonomy_v1(
        build_exit_wait_taxonomy_v1(
            wait_state=WaitState(
                phase="exit",
                state="REVERSE_READY",
                hard_wait=False,
                reason="reverse_ready_after_confirm",
            ),
            utility_result={
                "winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "wait_selected": False,
                "wait_decision": "",
            },
        )
    )

    assert taxonomy["state"]["state_family"] == "reverse_ready"
    assert taxonomy["decision"]["decision_family"] == "reverse_now"
    assert taxonomy["bridge"]["bridge_status"] == "aligned_reverse"


def test_exit_wait_taxonomy_maps_exit_pressure_surface():
    taxonomy = compact_exit_wait_taxonomy_v1(
        build_exit_wait_taxonomy_v1(
            wait_state=WaitState(
                phase="exit",
                state="CUT_IMMEDIATE",
                hard_wait=False,
                reason="adverse_loss_expand",
            ),
            utility_result={
                "winner": "cut_now",
                "decision_reason": "cut_now_best",
                "wait_selected": False,
                "wait_decision": "",
            },
        )
    )

    assert taxonomy["state"]["state_family"] == "exit_pressure"
    assert taxonomy["decision"]["decision_family"] == "exit_now"
    assert taxonomy["decision"]["recovery_variant"] == "cut_now"
    assert taxonomy["bridge"]["bridge_status"] == "aligned_exit_pressure"
