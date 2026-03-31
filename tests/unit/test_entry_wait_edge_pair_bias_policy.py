from backend.services.entry_wait_edge_pair_bias_policy import resolve_entry_wait_edge_pair_bias_v1


def test_entry_wait_edge_pair_bias_policy_returns_neutral_defaults_without_edge_pair():
    payload = resolve_entry_wait_edge_pair_bias_v1()

    assert payload["present"] is False
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is False


def test_entry_wait_edge_pair_bias_policy_prefers_confirm_release_for_matching_clear_winner():
    payload = resolve_entry_wait_edge_pair_bias_v1(
        observe_confirm_v2={
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BUY",
                    "winner_clear": True,
                    "pair_gap": 0.18,
                }
            }
        },
        action="BUY",
    )

    assert payload["present"] is True
    assert payload["acting_side"] == "BUY"
    assert payload["prefer_confirm_release"] is True
    assert payload["prefer_wait_lock"] is False
    assert payload["enter_value_delta"] > 0.0
    assert payload["wait_value_delta"] < 0.0


def test_entry_wait_edge_pair_bias_policy_keeps_wait_lock_for_unresolved_pair():
    payload = resolve_entry_wait_edge_pair_bias_v1(
        observe_confirm_v2={
            "metadata": {
                "edge_pair_law_v1": {
                    "context_label": "LOWER_EDGE",
                    "winner_side": "BALANCED",
                    "winner_clear": False,
                    "pair_gap": 0.02,
                }
            }
        },
        action="BUY",
    )

    assert payload["present"] is True
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is True
    assert payload["enter_value_delta"] < 0.0
    assert payload["wait_value_delta"] > 0.0


def test_entry_wait_edge_pair_bias_policy_does_not_release_on_opposite_clear_winner():
    payload = resolve_entry_wait_edge_pair_bias_v1(
        payload={
            "edge_pair_law_v1": {
                "context_label": "UPPER_EDGE",
                "winner_side": "SELL",
                "winner_clear": True,
                "pair_gap": 0.16,
            }
        },
        action="BUY",
    )

    assert payload["present"] is True
    assert payload["acting_side"] == "BUY"
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is False
