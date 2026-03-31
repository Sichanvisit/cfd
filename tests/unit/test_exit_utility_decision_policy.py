from backend.services.exit_utility_decision_policy import (
    compact_exit_utility_decision_policy_v1,
    resolve_exit_utility_decision_policy_v1,
)


def test_exit_utility_decision_policy_picks_wait_be_on_recovery_path():
    compact = compact_exit_utility_decision_policy_v1(
        resolve_exit_utility_decision_policy_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "BTCUSD",
                    "state": "RECOVERY_BE",
                },
                "risk": {
                    "profit": -0.4,
                },
            },
            utility_candidates_v1={
                "u_cut_now": -0.4,
                "u_wait_be": 0.1696,
                "u_wait_tp1": 0.1662,
                "u_reverse": -999.0,
            },
            exit_utility_scene_bias_bundle_v1={
                "contract_version": "exit_utility_scene_bias_bundle_v1",
                "flags": {},
            },
        )
    )

    assert compact["contract_version"] == "exit_utility_decision_policy_v1"
    assert compact["identity"]["decision_mode"] == "recovery_path"
    assert compact["result"]["winner"] == "wait_be"
    assert compact["result"]["decision_reason"] == "wait_be_recovery"
    assert compact["result"]["wait_selected"] is True
    assert compact["result"]["wait_decision"] == "wait_be_recovery"


def test_exit_utility_decision_policy_uses_support_bounce_reason_on_profit_path():
    compact = compact_exit_utility_decision_policy_v1(
        resolve_exit_utility_decision_policy_v1(
            exit_utility_input_v1={
                "contract_version": "exit_utility_input_v1",
                "identity": {
                    "symbol": "BTCUSD",
                    "state": "ACTIVE",
                },
                "risk": {
                    "profit": 0.24,
                },
            },
            utility_candidates_v1={
                "utility_exit_now": 0.52,
                "utility_hold": -0.64,
                "utility_reverse": -0.05,
                "utility_wait_exit": -0.38,
            },
            exit_utility_scene_bias_bundle_v1={
                "contract_version": "exit_utility_scene_bias_bundle_v1",
                "flags": {
                    "btc_upper_support_bounce_exit": True,
                },
            },
        )
    )

    assert compact["identity"]["decision_mode"] == "profit_path"
    assert compact["result"]["winner"] == "exit_now"
    assert compact["result"]["decision_reason"] == "exit_now_support_bounce"
    assert compact["result"]["wait_selected"] is False
    assert compact["result"]["wait_decision"] == ""
