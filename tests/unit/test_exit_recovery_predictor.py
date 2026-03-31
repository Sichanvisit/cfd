from backend.domain.decision_models import DecisionContext, ExitProfile, WaitState
from backend.services.exit_recovery_predictor import ExitRecoveryPredictor


def test_exit_recovery_predictor_returns_recovery_probabilities():
    predictor = ExitRecoveryPredictor()
    payload = predictor.predict(
        context=DecisionContext(
            symbol="XAUUSD",
            phase="exit",
            market_mode="RANGE",
            box_state="UPPER",
            bb_state="UPPER_EDGE",
        ),
        wait_state=WaitState(phase="exit", state="RECOVERY_BE"),
        exit_profile=ExitProfile(profile_id="tight_protect"),
        metrics={
            "profit": -0.24,
            "giveback": 0.0,
            "score_gap": 8,
            "adverse_risk": False,
            "tf_confirm": True,
            "duration_sec": 80.0,
        },
    )

    assert payload["p_recover_be"] > payload["p_deeper_loss"]
    assert payload["p_recover_tp1"] > 0.0


def test_exit_recovery_predictor_breakout_policy_tilts_to_reverse():
    predictor = ExitRecoveryPredictor()
    payload = predictor.predict(
        context=DecisionContext(
            symbol="BTCUSD",
            phase="exit",
            market_mode="TREND",
            box_state="MIDDLE",
            bb_state="MID",
        ),
        wait_state=WaitState(phase="exit", state="REVERSE_READY"),
        exit_profile=ExitProfile(profile_id="neutral"),
        metrics={
            "management_profile_id": "breakout_hold_profile",
            "invalidation_id": "breakout_failure",
            "entry_setup_id": "",
            "profit": -0.28,
            "giveback": 0.0,
            "score_gap": 22,
            "adverse_risk": False,
            "tf_confirm": True,
            "duration_sec": 70.0,
        },
    )

    assert payload["recovery_policy_id"] == "breakout_hold_profile"
    assert payload["p_reverse_valid"] >= payload["p_recover_be"]


def test_exit_recovery_predictor_uses_belief_driven_fast_exit_policy():
    predictor = ExitRecoveryPredictor()
    payload = predictor.predict(
        context=DecisionContext(
            symbol="BTCUSD",
            phase="exit",
            market_mode="RANGE",
            box_state="LOWER",
            bb_state="LOWER_EDGE",
        ),
        wait_state=WaitState(phase="exit", state="RECOVERY_BE"),
        exit_profile=ExitProfile(profile_id="tight_protect"),
        metrics={
            "entry_setup_id": "range_lower_reversal_buy",
            "entry_direction": "BUY",
            "profit": -0.20,
            "giveback": 0.0,
            "score_gap": 22,
            "adverse_risk": False,
            "tf_confirm": True,
            "duration_sec": 60.0,
            "belief_state_v1": {
                "buy_persistence": 0.0,
                "sell_persistence": 0.64,
                "belief_spread": -0.22,
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_streak": 0,
                "sell_streak": 3,
                "metadata": {"dominance_deadband": 0.05},
            },
        },
    )

    assert payload["recovery_policy_id"] == "range_lower_reversal_buy_btc_balanced"
    assert payload["p_deeper_loss"] >= payload["p_recover_be"]


def test_exit_recovery_predictor_supports_xau_edge_to_edge_hold_policy():
    predictor = ExitRecoveryPredictor()
    payload = predictor.predict(
        context=DecisionContext(
            symbol="XAUUSD",
            phase="exit",
            market_mode="RANGE",
            box_state="MIDDLE",
            bb_state="MID",
        ),
        wait_state=WaitState(phase="exit", state="RECOVERY_BE"),
        exit_profile=ExitProfile(profile_id="tight_protect"),
        metrics={
            "entry_setup_id": "range_lower_reversal_buy",
            "entry_direction": "BUY",
            "profit": -0.12,
            "giveback": 0.0,
            "score_gap": 6,
            "adverse_risk": False,
            "tf_confirm": False,
            "duration_sec": 120.0,
        },
    )

    assert payload["recovery_policy_id"] == "range_lower_reversal_buy_xau_balanced"
    assert payload["p_recover_be"] > payload["p_deeper_loss"]
