from backend.services.exit_recovery_utility_bundle import (
    compact_exit_recovery_utility_bundle_v1,
    resolve_exit_recovery_utility_bundle_v1,
)


def _utility_input(
    *,
    profit: float = -0.4,
    peak_profit: float = 0.0,
    exit_profile_id: str = "neutral",
) -> dict:
    return {
        "contract_version": "exit_utility_input_v1",
        "identity": {
            "symbol": "BTCUSD",
            "state": "RECOVERY_BE",
            "exit_profile_id": exit_profile_id,
        },
        "risk": {
            "profit": profit,
            "peak_profit": peak_profit,
            "giveback": max(0.0, peak_profit - profit),
            "score_gap": 6.0,
            "adverse_risk": False,
            "duration_sec": 120.0,
            "roundtrip_cost": 0.06,
        },
        "policy": {
            "allow_wait_be": True,
            "allow_wait_tp1": True,
        },
        "bias": {
            "state_execution_bias_v1": {
                "prefer_fast_cut": False,
                "exit_pressure": 0.0,
            }
        },
    }


def _base_bundle() -> dict:
    return {
        "contract_version": "exit_utility_base_bundle_v1",
        "inputs": {
            "reverse_edge": 0.2875,
        },
    }


def test_exit_recovery_utility_bundle_builds_recovery_candidates():
    compact = compact_exit_recovery_utility_bundle_v1(
        resolve_exit_recovery_utility_bundle_v1(
            exit_utility_input_v1=_utility_input(),
            exit_utility_base_bundle_v1=_base_bundle(),
            recovery_predictions={
                "p_recover_be": 0.76,
                "p_recover_tp1": 0.58,
                "p_deeper_loss": 0.18,
                "p_reverse_valid": 0.12,
            },
        )
    )

    assert compact["contract_version"] == "exit_recovery_utility_bundle_v1"
    assert compact["probabilities"]["p_recover_be"] == 0.76
    assert compact["inputs"]["be_recovery_gain"] == 0.4
    assert compact["inputs"]["tp1_recovery_gain"] == 0.57
    assert compact["utilities"]["u_cut_now"] == -0.4
    assert compact["utilities"]["u_wait_be"] == 0.1696
    assert compact["utilities"]["u_wait_tp1"] == 0.1662
    assert compact["gating"]["allow_wait_be_effective"] is True
    assert compact["gating"]["tight_protect_green_disable"] is False


def test_exit_recovery_utility_bundle_disables_green_recovery_for_tight_protect():
    compact = compact_exit_recovery_utility_bundle_v1(
        resolve_exit_recovery_utility_bundle_v1(
            exit_utility_input_v1=_utility_input(
                profit=0.42,
                peak_profit=0.86,
                exit_profile_id="tight_protect",
            ),
            exit_utility_base_bundle_v1=_base_bundle(),
            recovery_predictions={
                "p_recover_be": 0.20,
                "p_recover_tp1": 0.12,
                "p_deeper_loss": 0.34,
                "p_reverse_valid": 0.08,
            },
            lower_reversal_hold_bias=False,
        )
    )

    assert compact["gating"]["tight_protect_green_disable"] is True
    assert compact["gating"]["wait_be_disable_reason"] == "tight_protect_green_disable"
    assert compact["gating"]["wait_tp1_disable_reason"] == "tight_protect_green_disable"
    assert compact["utilities"]["u_wait_be"] == -999.0
    assert compact["utilities"]["u_wait_tp1"] == -999.0
