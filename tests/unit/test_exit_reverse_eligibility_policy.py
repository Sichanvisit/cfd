from backend.services.exit_reverse_eligibility_policy import (
    compact_exit_reverse_eligibility_v1,
    resolve_exit_reverse_eligibility_v1,
)


def _utility_input(
    *,
    state: str = "REVERSE_READY",
    profit: float = -0.35,
    adverse_risk: bool = True,
    duration_sec: float = 120.0,
    score_gap: float = 36.0,
    prefer_reverse: bool = False,
) -> dict:
    return {
        "contract_version": "exit_utility_input_v1",
        "identity": {
            "symbol": "BTCUSD",
            "state": state,
        },
        "risk": {
            "profit": profit,
            "adverse_risk": adverse_risk,
            "duration_sec": duration_sec,
            "score_gap": score_gap,
        },
        "policy": {
            "prefer_reverse": prefer_reverse,
            "reverse_gap_required": 18,
            "reverse_min_prob": 0.58,
            "reverse_min_hold_seconds": 45.0,
        },
    }


def _recovery_bundle(
    *,
    p_reverse_valid: float = 0.92,
    u_reverse_candidate: float = 0.21,
) -> dict:
    return {
        "contract_version": "exit_recovery_utility_bundle_v1",
        "probabilities": {
            "p_reverse_valid": p_reverse_valid,
        },
        "utilities": {
            "u_reverse_candidate": u_reverse_candidate,
        },
    }


def test_exit_reverse_eligibility_policy_blocks_when_state_is_not_ready():
    compact = compact_exit_reverse_eligibility_v1(
        resolve_exit_reverse_eligibility_v1(
            exit_utility_input_v1=_utility_input(
                state="RECOVERY_BE",
                prefer_reverse=False,
            ),
            exit_recovery_utility_bundle_v1=_recovery_bundle(),
        )
    )

    assert compact["result"]["reverse_eligible"] is False
    assert compact["result"]["reverse_reason"] == "state_not_reverse_ready"
    assert compact["result"]["u_reverse"] == -999.0


def test_exit_reverse_eligibility_policy_grants_bonus_for_preferred_reversal_confirm():
    compact = compact_exit_reverse_eligibility_v1(
        resolve_exit_reverse_eligibility_v1(
            exit_utility_input_v1=_utility_input(
                state="REVERSAL_CONFIRM",
                prefer_reverse=True,
                score_gap=24.0,
            ),
            exit_recovery_utility_bundle_v1=_recovery_bundle(
                p_reverse_valid=0.92,
                u_reverse_candidate=0.21,
            ),
        )
    )

    assert compact["result"]["reverse_eligible"] is True
    assert compact["result"]["reverse_reason"] == "reversal_confirm_prefer_reverse"
    assert compact["result"]["reverse_bonus"] == 0.04
    assert compact["result"]["u_reverse"] == 0.25
