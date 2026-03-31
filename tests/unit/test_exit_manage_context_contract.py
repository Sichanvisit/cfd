from backend.services.exit_manage_context_contract import (
    build_exit_manage_context_v1,
    compact_exit_manage_context_v1,
)


def test_build_exit_manage_context_prefers_canonical_handoff_and_lifecycle_profile():
    context = build_exit_manage_context_v1(
        symbol="XAUUSD",
        trade_ctx={
            "entry_setup_id": "breakout_retest_sell",
            "management_profile_id": "breakout_hold_profile",
            "invalidation_id": "breakout_failure",
            "exit_profile": "neutral",
        },
        stage_inputs={
            "regime_now": "RANGE",
            "regime_at_entry": "TREND",
            "current_box_state": "MIDDLE",
            "current_bb_state": "MID",
            "entry_direction": "SELL",
            "profit": 0.55,
            "peak_profit": 0.82,
            "duration_sec": 125.0,
        },
        chosen_stage="hold",
        policy_stage="mid",
        exec_profile="aggressive",
        confirm_needed=3,
        exit_signal_score=144,
        score_gap=22,
        adverse_risk=False,
        tf_confirm=True,
        detail={"route_txt": "unit-route", "exit_threshold": 70, "reverse_signal_threshold": 110},
    )

    assert context["handoff"]["management_profile_id"] == "breakout_hold_profile"
    assert context["handoff"]["invalidation_id"] == "breakout_failure"
    assert context["handoff"]["handoff_source"] == "canonical_entry_handoff"
    assert context["posture"]["resolved_exit_profile"] == "hold_then_trail"
    assert context["posture"]["lifecycle_exit_profile"] == "tight_protect"
    assert context["identity"]["entry_direction"] == "SELL"
    assert round(context["risk"]["giveback"], 2) == 0.27


def test_compact_exit_manage_context_keeps_operating_surface():
    context = build_exit_manage_context_v1(
        symbol="BTCUSD",
        trade_ctx={
            "entry_setup_id": "range_lower_reversal_buy",
            "management_profile_id": "support_hold_profile",
            "invalidation_id": "lower_support_fail",
            "exit_profile": "tight_protect",
        },
        stage_inputs={
            "regime_now": "RANGE",
            "current_box_state": "LOWER",
            "current_bb_state": "LOWER_EDGE",
            "entry_direction": "BUY",
            "profit": -0.12,
            "peak_profit": 0.20,
            "duration_sec": 90.0,
        },
        chosen_stage="protect",
        policy_stage="short",
        exec_profile="neutral",
        confirm_needed=2,
        exit_signal_score=88,
        score_gap=6,
        adverse_risk=True,
        tf_confirm=False,
        detail={"route_txt": "compact-unit"},
    )

    compact = compact_exit_manage_context_v1(context)

    assert compact["identity"]["symbol"] == "BTCUSD"
    assert compact["handoff"]["management_profile_id"] == "support_hold_profile"
    assert compact["posture"]["chosen_stage"] == "protect"
    assert compact["posture"]["lifecycle_exit_profile"] == "tight_protect"
    assert compact["market"]["current_box_state"] == "LOWER"
    assert compact["risk"]["adverse_risk"] is True
    assert compact["detail"]["route_txt"] == "compact-unit"
