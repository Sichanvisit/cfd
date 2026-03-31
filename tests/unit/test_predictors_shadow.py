from backend.domain.decision_models import DecisionContext, ExitProfile, SetupCandidate, WaitState
from backend.services.predictors import ShadowEntryPredictor, ShadowExitPredictor, ShadowWaitPredictor


def test_shadow_entry_predictor_returns_expected_fields():
    predictor = ShadowEntryPredictor()
    out = predictor.predict(
        context=DecisionContext(symbol="NAS100", phase="entry", market_mode="RANGE", box_state="UPPER", bb_state="UPPER_EDGE"),
        setup=SetupCandidate(setup_id="range_upper_reversal_sell", side="SELL", status="matched", entry_quality=0.9, score=0.85),
        metrics={"raw_score": 95.0, "contra_score": 65.0, "effective_threshold": 68.0, "core_score": 0.61},
    )
    assert set(out.keys()) == {"model", "p_win", "p_tp_first", "expected_reward", "expected_risk"}
    assert 0.0 < out["p_win"] < 1.0


def test_shadow_wait_predictor_returns_entry_and_exit_payloads():
    predictor = ShadowWaitPredictor()
    context = DecisionContext(symbol="BTCUSD", phase="entry", market_mode="RANGE", box_state="MIDDLE", bb_state="UNKNOWN")
    setup = SetupCandidate(setup_id="", side="BUY", status="rejected")
    wait_state = WaitState(phase="entry", state="CENTER", score=38.0, reason="setup_rejected")
    entry_out = predictor.predict_entry_wait(context=context, setup=setup, wait_state=wait_state, metrics={})
    exit_out = predictor.predict_exit_wait(
        context=DecisionContext(symbol="BTCUSD", phase="exit"),
        wait_state=WaitState(phase="exit", state="RECOVERY", score=1.0, reason="recovery"),
        exit_profile=ExitProfile(profile_id="neutral"),
        metrics={"profit": -0.8, "giveback": 0.1},
    )
    assert "p_better_entry_if_wait" in entry_out
    assert "p_better_exit_if_wait" in exit_out


def test_shadow_exit_predictor_returns_expected_fields():
    predictor = ShadowExitPredictor()
    out = predictor.predict(
        context=DecisionContext(symbol="XAUUSD", phase="exit", market_mode="RANGE"),
        wait_state=WaitState(phase="exit", state="REVERSAL_CONFIRM"),
        exit_profile=ExitProfile(profile_id="neutral", policy_stage="mid"),
        metrics={"profit": -0.4, "score_gap": 22, "adverse_risk": True, "tf_confirm": True},
    )
    assert set(out.keys()) == {"model", "p_more_profit", "p_giveback", "p_reverse_valid"}
    assert 0.0 < out["p_reverse_valid"] < 1.0
