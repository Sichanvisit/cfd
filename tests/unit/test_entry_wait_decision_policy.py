from backend.services.entry_wait_decision_policy import resolve_entry_wait_decision_policy_v1


def test_entry_wait_decision_policy_prefers_policy_hard_block():
    policy = resolve_entry_wait_decision_policy_v1(
        blocked_reason="core_not_passed",
        raw_entry_score=88.0,
        effective_threshold=84.0,
        core_score=0.34,
        wait_state_state="POLICY_BLOCK",
        wait_state_score=6.0,
        wait_state_penalty=0.0,
        wait_state_hard_wait=True,
        wait_metadata={
            "action_readiness": 0.31,
            "wait_vs_enter_hint": "prefer_wait",
            "soft_block_active": True,
            "soft_block_strength": 0.81,
            "policy_hard_block_active": True,
        },
    )

    assert policy["selected"] is True
    assert policy["decision"] == "wait_policy_hard_block"
    assert policy["policy_hint_applied"] is True
    assert policy["energy_hint_applied"] is True


def test_entry_wait_decision_policy_prefers_helper_soft_block():
    policy = resolve_entry_wait_decision_policy_v1(
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
        wait_state_state="HELPER_SOFT_BLOCK",
        wait_state_score=0.0,
        wait_state_penalty=0.0,
        wait_state_hard_wait=True,
        wait_metadata={
            "action_readiness": 0.24,
            "wait_vs_enter_hint": "prefer_wait",
            "soft_block_active": True,
            "soft_block_strength": 0.72,
        },
    )

    assert policy["selected"] is True
    assert policy["decision"] == "wait_soft_helper_block"
    assert policy["wait_value"] > policy["enter_value"]


def test_entry_wait_decision_policy_keeps_generic_helper_state_name_for_prefer_enter():
    policy = resolve_entry_wait_decision_policy_v1(
        blocked_reason="core_not_passed",
        raw_entry_score=64.0,
        effective_threshold=63.0,
        core_score=0.22,
        wait_state_state="HELPER_SOFT_BLOCK",
        wait_state_score=0.0,
        wait_state_penalty=0.0,
        wait_state_hard_wait=False,
        wait_metadata={
            "action_readiness": 0.24,
            "wait_vs_enter_hint": "prefer_enter",
            "soft_block_active": True,
            "soft_block_strength": 0.72,
        },
    )

    assert policy["selected"] is True
    assert policy["decision"] == "wait_soft_helper_soft_block"
