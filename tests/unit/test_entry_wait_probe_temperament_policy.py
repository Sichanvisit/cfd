from backend.services.entry_wait_probe_temperament_policy import (
    resolve_entry_wait_probe_temperament_v1,
)


def test_entry_wait_probe_temperament_policy_returns_neutral_defaults_without_probe_scene():
    payload = resolve_entry_wait_probe_temperament_v1()

    assert payload["present"] is False
    assert payload["scene_id"] == ""
    assert payload["prefer_confirm_release"] is False
    assert payload["prefer_wait_lock"] is False


def test_entry_wait_probe_temperament_policy_reads_candidate_fallback_for_xau_second_support():
    payload = resolve_entry_wait_probe_temperament_v1(
        payload={
            "probe_candidate_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_second_support_buy_probe",
                    "promotion_bias": "aggressive_second_support",
                    "entry_style_hint": "second_support_probe",
                    "note": "xau_second_support_buy_more_aggressive",
                },
                "active": True,
                "trigger_branch": "lower_rebound",
            }
        },
    )

    assert payload["present"] is True
    assert payload["scene_id"] == "xau_second_support_buy_probe"
    assert payload["active"] is True
    assert payload["ready_for_entry"] is False
    assert payload["trigger_branch"] == "lower_rebound"
    assert payload["prefer_confirm_release"] is True
    assert payload["prefer_wait_lock"] is False
    assert payload["enter_value_delta"] > 0.0
    assert payload["wait_value_delta"] < 0.0


def test_entry_wait_probe_temperament_policy_reads_plan_scene_for_xau_upper_sell():
    payload = resolve_entry_wait_probe_temperament_v1(
        payload={
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_upper_sell_probe",
                    "promotion_bias": "fast_probe",
                    "entry_style_hint": "early_upper_reject_probe",
                    "note": "xau_upper_sell_probe_faster",
                },
                "active": True,
                "trigger_branch": "upper_reject",
            }
        },
    )

    assert payload["present"] is True
    assert payload["scene_id"] == "xau_upper_sell_probe"
    assert payload["active"] is True
    assert payload["prefer_confirm_release"] is True
    assert payload["prefer_wait_lock"] is False
    assert payload["enter_value_delta"] > 0.0
    assert payload["wait_value_delta"] < 0.0


def test_entry_wait_probe_temperament_policy_changes_btc_conservative_wait_bias_when_ready():
    before_ready = resolve_entry_wait_probe_temperament_v1(
        payload={
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "btc_lower_buy_conservative_probe",
                    "promotion_bias": "conservative_hold_first",
                },
                "active": True,
                "ready_for_entry": False,
                "trigger_branch": "lower_rebound",
            }
        },
    )
    after_ready = resolve_entry_wait_probe_temperament_v1(
        payload={
            "entry_probe_plan_v1": {
                "symbol_probe_temperament_v1": {
                    "scene_id": "btc_lower_buy_conservative_probe",
                    "promotion_bias": "conservative_hold_first",
                },
                "active": True,
                "ready_for_entry": True,
                "trigger_branch": "lower_rebound",
            }
        },
    )

    assert before_ready["prefer_wait_lock"] is True
    assert before_ready["enter_value_delta"] < 0.0
    assert after_ready["prefer_wait_lock"] is False
    assert after_ready["enter_value_delta"] > before_ready["enter_value_delta"]
