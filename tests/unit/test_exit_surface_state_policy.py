from backend.services.exit_surface_state_policy import (
    resolve_exit_surface_state_v1,
)


def test_exit_surface_state_policy_maps_runner_partial_reduce():
    out = resolve_exit_surface_state_v1(
        action_source="runner_preservation",
        candidate_kind="partial_then_runner_hold",
        reason="Runner Preserve",
        partial_executed=True,
    )

    assert out["should_record"] is True
    assert out["surface_family"] == "continuation_hold_surface"
    assert out["surface_state"] == "PARTIAL_REDUCE"


def test_exit_surface_state_policy_maps_runner_hold_runner():
    out = resolve_exit_surface_state_v1(
        action_source="partial_action",
        stop_lock_applied=True,
        reason="profit_stop_up",
    )

    assert out["should_record"] is True
    assert out["surface_family"] == "continuation_hold_surface"
    assert out["surface_state"] == "HOLD_RUNNER"


def test_exit_surface_state_policy_maps_protective_exit():
    out = resolve_exit_surface_state_v1(
        action_source="managed_exit",
        candidate_kind="protect_exit",
        reason="Protect Exit",
    )

    assert out["should_record"] is True
    assert out["surface_family"] == "protective_exit_surface"
    assert out["surface_state"] == "EXIT_PROTECT"


def test_exit_surface_state_policy_maps_lock_profit():
    out = resolve_exit_surface_state_v1(
        action_source="managed_exit",
        candidate_kind="target_exit",
        reason="Target",
    )

    assert out["should_record"] is True
    assert out["surface_family"] == "protective_exit_surface"
    assert out["surface_state"] == "LOCK_PROFIT"
