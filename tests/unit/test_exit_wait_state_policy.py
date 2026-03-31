from backend.services.exit_wait_state_policy import resolve_exit_wait_state_policy_v1


def _contract(
    *,
    identity: dict | None = None,
    market: dict | None = None,
    risk: dict | None = None,
    policy: dict | None = None,
) -> dict:
    return {
        "identity": {
            "symbol": "BTCUSD",
            "entry_direction": "BUY",
            **(identity or {}),
        },
        "market": {
            "regime_now": "TREND",
            "current_box_state": "LOWER",
            "current_bb_state": "LOWER_EDGE",
            "reached_opposite_edge": False,
            **(market or {}),
        },
        "risk": {
            "profit": 0.0,
            "giveback": 0.0,
            "duration_sec": 30.0,
            "adverse_risk": False,
            "tf_confirm": True,
            "score_gap": 0,
            **(risk or {}),
        },
        "policy": {
            "allow_wait_be": True,
            "allow_wait_tp1": False,
            "prefer_reverse": False,
            "recovery_be_max_loss": 0.90,
            "recovery_tp1_max_loss": 0.35,
            "recovery_wait_max_seconds": 240.0,
            "reverse_score_gap": 18,
            **(policy or {}),
        },
    }


def test_exit_wait_state_policy_marks_reversal_confirm():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": 0.20,
                "adverse_risk": True,
                "tf_confirm": False,
                "score_gap": 24,
            }
        )
    )

    assert resolution["state"] == "REVERSAL_CONFIRM"
    assert resolution["reason"] == "opposite_signal_unconfirmed"
    assert resolution["hard_wait"] is True
    assert resolution["matched_rule"] == "reversal_confirm"


def test_exit_wait_state_policy_marks_active_range_middle_hold():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            market={"regime_now": "RANGE", "current_box_state": "MIDDLE"},
            risk={"profit": 0.24, "giveback": 0.18},
        )
    )

    assert resolution["state"] == "ACTIVE"
    assert resolution["reason"] == "range_middle_observe"
    assert resolution["hard_wait"] is False
    assert resolution["matched_rule"] == "range_middle_active"


def test_exit_wait_state_policy_marks_recovery_tp1_for_small_loss():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": -0.22,
                "duration_sec": 90.0,
                "tf_confirm": True,
                "score_gap": 6,
            },
            policy={
                "allow_wait_be": True,
                "allow_wait_tp1": True,
                "recovery_tp1_max_loss": 0.35,
                "reverse_score_gap": 18,
            },
        )
    )

    assert resolution["state"] == "RECOVERY_TP1"
    assert resolution["reason"] == "recovery_to_small_profit"
    assert resolution["matched_rule"] == "recovery_tp1"


def test_exit_wait_state_policy_marks_recovery_be_when_tp1_is_not_enabled():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": -0.22,
                "duration_sec": 90.0,
                "tf_confirm": True,
                "score_gap": 6,
            },
            policy={
                "allow_wait_be": True,
                "allow_wait_tp1": False,
            },
        )
    )

    assert resolution["state"] == "RECOVERY_BE"
    assert resolution["reason"] == "recovery_to_breakeven"
    assert resolution["matched_rule"] == "recovery_be"


def test_exit_wait_state_policy_marks_reverse_ready_after_confirm():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": -1.20,
                "duration_sec": 45.0,
                "tf_confirm": True,
                "score_gap": 24,
            },
            policy={
                "allow_wait_be": False,
                "allow_wait_tp1": False,
                "prefer_reverse": True,
                "reverse_score_gap": 18,
            },
        )
    )

    assert resolution["state"] == "REVERSE_READY"
    assert resolution["reason"] == "reverse_ready_after_confirm"
    assert resolution["matched_rule"] == "reverse_ready"


def test_exit_wait_state_policy_marks_cut_immediate_on_adverse_loss():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": -0.50,
                "adverse_risk": True,
                "tf_confirm": True,
                "score_gap": 20,
            },
            policy={
                "allow_wait_be": False,
                "allow_wait_tp1": False,
            },
        )
    )

    assert resolution["state"] == "CUT_IMMEDIATE"
    assert resolution["reason"] == "adverse_loss_expand"
    assert resolution["hard_wait"] is False
    assert resolution["matched_rule"] == "cut_immediate"


def test_exit_wait_state_policy_marks_green_close_before_rewrite():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            risk={
                "profit": 0.24,
                "giveback": 0.05,
                "tf_confirm": False,
                "score_gap": 0,
            }
        )
    )

    assert resolution["state"] == "GREEN_CLOSE"
    assert resolution["reason"] == "green_close_hold"
    assert resolution["matched_rule"] == "green_close"


def test_exit_wait_state_policy_returns_none_when_no_rule_matches():
    resolution = resolve_exit_wait_state_policy_v1(
        _contract(
            market={"regime_now": "TREND", "current_box_state": "MIDDLE"},
            risk={
                "profit": 0.24,
                "giveback": 0.14,
                "tf_confirm": True,
                "score_gap": 2,
            },
        )
    )

    assert resolution["state"] == "NONE"
    assert resolution["reason"] == ""
    assert resolution["matched_rule"] == "none"
