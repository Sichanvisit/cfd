from backend.services.utility_router import (
    compute_entry_utility,
    compute_exit_utility,
    compute_hold_utility,
    compute_reverse_utility,
    compute_wait_utility,
    select_utility_winner,
)


def test_compute_entry_utility_positive_edge():
    value = compute_entry_utility(
        p_win=0.62,
        expected_reward=1.8,
        expected_risk=1.1,
        cost=0.2,
        context_adj=0.1,
    )
    assert value > 0.0


def test_compute_wait_utility_reflects_better_wait():
    value = compute_wait_utility(
        p_better_entry_if_wait=0.72,
        expected_entry_improvement=1.1,
        expected_miss_cost=0.18,
        extra_penalty=0.02,
    )
    assert value > 0.0


def test_exit_and_reverse_utility_shapes():
    assert abs(compute_exit_utility(locked_profit=0.4, exit_cost=0.1) - 0.3) < 1e-9
    assert compute_hold_utility(p_more_profit=0.6, upside=1.0, p_giveback=0.3, giveback=0.5) > 0.0
    assert compute_reverse_utility(p_reverse_valid=0.5, reverse_edge=1.2, reverse_cost=0.2) > 0.0


def test_select_utility_winner_picks_highest_value():
    winner, value = select_utility_winner(
        {
            "exit_now": 0.15,
            "hold": 0.05,
            "reverse": 0.11,
            "wait_exit": 0.22,
        },
        priority=["exit_now", "wait_exit", "reverse", "hold"],
    )
    assert winner == "wait_exit"
    assert abs(value - 0.22) < 1e-9
