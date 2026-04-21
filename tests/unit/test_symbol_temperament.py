from backend.services.symbol_temperament import (
    resolve_allowed_action,
    resolve_archetype_implied_action,
    resolve_edge_execution_overrides,
    resolve_probe_plan_temperament,
    resolve_probe_scene_direction,
    resolve_probe_scene_policy_family,
    resolve_probe_temperament,
    resolve_wait_probe_temperament,
)


def test_resolve_probe_temperament_for_xau_upper_sell():
    payload = resolve_probe_temperament(
        "XAUUSD",
        context_label="UPPER_EDGE",
        trigger_branch="upper_reject",
        probe_direction="SELL",
    )
    assert payload["scene_id"] == "xau_upper_sell_probe"
    assert payload["promotion_bias"] == "fast_probe"
    assert payload["source_map_id"] == "shared_symbol_temperament_map_v1"


def test_resolve_probe_temperament_for_xau_upper_sell_even_when_context_is_not_upper_edge():
    payload = resolve_probe_temperament(
        "XAUUSD",
        context_label="LOWER_EDGE",
        trigger_branch="upper_reject",
        probe_direction="SELL",
    )
    assert payload["scene_id"] == "xau_upper_sell_probe"
    assert payload["promotion_bias"] == "fast_probe"


def test_resolve_probe_plan_temperament_for_xau_upper_sell_uses_relaxed_stagee_relief():
    payload = resolve_probe_plan_temperament(
        symbol="XAUUSD",
        intended_action="SELL",
        trigger_branch="upper_reject",
    )
    assert payload["scene_id"] == "xau_upper_sell_probe"
    assert payload["structural_relief_candidate_support"] <= 0.16
    assert payload["structural_relief_action_confirm_score"] <= 0.13
    assert payload["structural_relief_max_side_barrier"] >= 0.66


def test_resolve_probe_plan_temperament_for_btc_lower_buy():
    payload = resolve_probe_plan_temperament(
        symbol="BTCUSD",
        intended_action="BUY",
        trigger_branch="lower_rebound",
    )
    assert payload["scene_id"] == "btc_lower_buy_conservative_probe"
    assert payload["allow_energy_relief"] is False
    assert payload["min_pair_gap"] >= 0.18


def test_resolve_probe_plan_temperament_for_btc_upper_sell():
    payload = resolve_probe_plan_temperament(
        symbol="BTCUSD",
        intended_action="SELL",
        trigger_branch="upper_reject",
    )
    assert payload["scene_id"] == "btc_upper_sell_probe"
    assert payload["structural_relief_active"] is True
    assert payload["min_action_confirm_score"] <= 0.20


def test_resolve_probe_plan_temperament_for_nas_clean_confirm_enables_native_relief():
    payload = resolve_probe_plan_temperament(
        symbol="NAS100",
        intended_action="BUY",
        trigger_branch="lower_rebound",
    )
    assert payload["scene_id"] == "nas_clean_confirm_probe"
    assert payload["allow_energy_relief"] is True
    assert payload["structural_relief_active"] is True
    assert payload["structural_relief_candidate_support"] <= 0.11


def test_resolve_probe_scene_direction_uses_reason_context_for_nas_clean_confirm_probe():
    assert resolve_probe_scene_direction(
        "nas_clean_confirm_probe",
        reason="upper_reject_probe_observe",
    ) == "SELL"
    assert resolve_probe_scene_direction(
        "nas_clean_confirm_probe",
        reason="lower_rebound_probe_observe",
    ) == "BUY"


def test_resolve_probe_scene_policy_family_prefers_shared_family_meaning():
    assert resolve_probe_scene_policy_family("xau_upper_sell_probe") == "upper_reject"
    assert resolve_probe_scene_policy_family("btc_lower_buy_conservative_probe") == "lower_rebound"
    assert resolve_probe_scene_policy_family("nas_clean_confirm_probe") == "clean_confirm"
    assert resolve_probe_scene_policy_family("", reason="middle_sr_anchor_required_observe") == "upper_reject"


def test_resolve_wait_probe_temperament_for_btc_not_ready():
    payload = resolve_wait_probe_temperament("btc_lower_buy_conservative_probe", ready_for_entry=False)
    assert payload["prefer_wait_lock"] is True
    assert payload["enter_value_delta"] < 0.0
    assert payload["wait_value_delta"] > 0.0


def test_resolve_edge_execution_overrides_for_xau_lower_buy():
    payload = resolve_edge_execution_overrides(
        symbol="XAUUSD",
        entry_setup_id="range_lower_reversal_buy",
        entry_direction="BUY",
    )
    assert payload["active"] is True
    assert payload["scene_id"] == "xau_lower_edge_to_edge_buy"
    assert payload["prefer_hold_to_opposite_edge"] is True


def test_resolve_archetype_implied_action_uses_directional_suffix():
    assert resolve_archetype_implied_action("upper_reject_sell") == "SELL"
    assert resolve_archetype_implied_action("lower_hold_buy") == "BUY"
    assert resolve_archetype_implied_action("balanced_hold") == ""


def test_resolve_allowed_action_prefers_direction_when_present():
    assert resolve_allowed_action("BUY", fallback="BOTH") == "BUY_ONLY"
    assert resolve_allowed_action("SELL", fallback="BOTH") == "SELL_ONLY"
    assert resolve_allowed_action("", fallback="BUY_ONLY") == "BUY_ONLY"
