from backend.services.exit_utility_base_bundle import (
    compact_exit_utility_base_bundle_v1,
    resolve_exit_utility_base_bundle_v1,
)


def _input_contract(
    *,
    duration_sec: float = 120.0,
) -> dict:
    return {
        "contract_version": "exit_utility_input_v1",
        "identity": {
            "symbol": "BTCUSD",
            "state": "ACTIVE",
            "exit_profile_id": "tight_protect",
        },
        "risk": {
            "profit": 0.42,
            "peak_profit": 0.68,
            "giveback": 0.26,
            "score_gap": 4.0,
            "adverse_risk": False,
            "duration_sec": duration_sec,
            "roundtrip_cost": 0.06,
        },
        "prediction": {
            "p_more_profit": 0.42,
            "p_giveback": 0.48,
            "p_reverse_valid": 0.08,
            "p_better_exit_if_wait": 0.30,
            "expected_exit_improvement": 0.10,
            "expected_miss_cost": 0.10,
        },
    }


def test_exit_utility_base_bundle_computes_expected_base_utilities():
    bundle = resolve_exit_utility_base_bundle_v1(
        exit_utility_input_v1=_input_contract(),
    )
    compact = compact_exit_utility_base_bundle_v1(bundle)

    assert compact["contract_version"] == "exit_utility_base_bundle_v1"
    assert compact["identity"]["symbol"] == "BTCUSD"
    assert compact["inputs"]["locked_profit"] == 0.42
    assert compact["inputs"]["upside"] == 0.35
    assert compact["inputs"]["giveback_cost"] == 0.34
    assert compact["inputs"]["reverse_edge"] == 0.125
    assert compact["utilities"]["utility_exit_now"] == 0.36
    assert compact["utilities"]["utility_hold"] == -0.0162
    assert compact["utilities"]["utility_reverse"] == -0.05
    assert compact["utilities"]["utility_wait_exit"] == -0.07


def test_exit_utility_base_bundle_adds_duration_penalty_to_wait_utility():
    bundle = compact_exit_utility_base_bundle_v1(
        resolve_exit_utility_base_bundle_v1(
            exit_utility_input_v1=_input_contract(duration_sec=2400.0),
        )
    )

    assert bundle["inputs"]["wait_extra_penalty"] == 0.03
    assert bundle["utilities"]["utility_wait_exit"] == -0.1
