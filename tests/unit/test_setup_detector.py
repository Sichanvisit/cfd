from backend.domain.decision_models import DecisionContext
from backend.services.setup_detector import SetupDetector


def _ctx(
    *,
    action_state: str | None = None,
    action: str | None = None,
    confidence: float = 0.0,
    reason: str = "",
    archetype_id: str = "",
    use_v2_only: bool = False,
    include_conflicting_v1: bool = False,
):
    metadata = {}
    if action_state is not None:
        payload = {
            "state": action_state,
            "action": action or "",
            "confidence": confidence,
            "reason": reason,
            "archetype_id": archetype_id,
        }
        if use_v2_only:
            metadata["observe_confirm_v2"] = dict(payload)
            metadata["prs_log_contract_v2"] = {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            }
            if include_conflicting_v1:
                metadata["observe_confirm_v1"] = {
                    "state": "OBSERVE",
                    "action": "WAIT",
                    "confidence": 0.05,
                    "reason": "legacy_conflict",
                    "archetype_id": "",
                }
        else:
            metadata["observe_confirm_v1"] = dict(payload)
    return DecisionContext(
        symbol="BTCUSD",
        phase="entry",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata=metadata,
    )


def test_setup_detector_rejects_when_observe_confirm_is_missing():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(),
        action="BUY",
        h1_gap=0.0,
        m1_gap=2.0,
        score_gap=5.0,
    )

    assert out.setup_id == ""
    assert out.status == "rejected"
    assert out.metadata["reason"] == "observe_confirm_missing"


def test_setup_detector_names_setup_without_redeciding_wait_vs_confirm():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="OBSERVE",
            action="WAIT",
            confidence=0.22,
            reason="lower_edge_observe",
            archetype_id="lower_hold_buy",
        ),
        action="BUY",
        h1_gap=0.0,
        m1_gap=0.0,
        score_gap=10.0,
    )

    assert out.setup_id == "range_lower_reversal_buy"
    assert out.status == "matched"
    assert out.metadata["reason"] == "shadow_lower_edge_observe"
    assert out.metadata["setup_mapping_contract"] == "setup_mapping_contract_v1"
    assert out.metadata["setup_mapping_rule_id"] == "lower_hold_buy_default"
    assert out.metadata["setup_mapping_specialized"] is False


def test_setup_detector_maps_lower_rebound_buy_from_shadow_confirm():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="BUY",
            confidence=0.71,
            reason="lower_rebound_confirm",
            archetype_id="lower_hold_buy",
        ),
        action="BUY",
        h1_gap=0.0,
        m1_gap=5.0,
        score_gap=10.0,
    )

    assert out.setup_id == "range_lower_reversal_buy"
    assert out.status == "matched"
    assert out.trigger_state == "READY"
    assert out.metadata["reason"] == "shadow_lower_rebound_confirm"
    assert out.entry_quality == 0.71


def test_setup_detector_maps_trend_pullback_sell_from_shadow_confirm():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="SELL",
            confidence=0.63,
            reason="trend_pullback_sell_confirm",
            archetype_id="mid_lose_sell",
        ),
        action="SELL",
        h1_gap=0.0,
        m1_gap=-5.0,
        score_gap=-12.0,
    )

    assert out.setup_id == "trend_pullback_sell"
    assert out.status == "matched"
    assert out.metadata["reason"] == "shadow_trend_pullback_sell_confirm"
    assert out.metadata["setup_mapping_specialized"] is True
    assert out.metadata["setup_mapping_rule_id"] == "mid_lose_sell_reason_trend_pullback"


def test_setup_detector_specializes_mid_reclaim_buy_by_market_mode_only():
    detector = SetupDetector()
    ctx = _ctx(
        action_state="OBSERVE",
        action="WAIT",
        confidence=0.58,
        reason="mid_reclaim_observe",
        archetype_id="mid_reclaim_buy",
        use_v2_only=True,
    )
    ctx.market_mode = "TREND"

    out = detector.detect_entry_setup(
        context=ctx,
        action="BUY",
        h1_gap=0.0,
        m1_gap=0.0,
        score_gap=0.0,
    )

    assert out.setup_id == "trend_pullback_buy"
    assert out.status == "matched"
    assert out.metadata["setup_mapping_specialized"] is True
    assert out.metadata["setup_mapping_rule_id"] == "mid_reclaim_buy_market_mode_trend"


def test_setup_detector_prefers_v2_over_conflicting_v1_during_migration():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="BUY",
            confidence=0.67,
            reason="lower_rebound_confirm",
            archetype_id="lower_hold_buy",
            use_v2_only=True,
            include_conflicting_v1=True,
        ),
        action="BUY",
        h1_gap=0.0,
        m1_gap=3.0,
        score_gap=8.0,
    )

    assert out.setup_id == "range_lower_reversal_buy"
    assert out.status == "matched"
    assert out.metadata["reason"] == "shadow_lower_rebound_confirm"


def test_setup_detector_rejects_side_mismatch_as_invalid_naming_input():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="SELL",
            confidence=0.55,
            reason="upper_reject_confirm",
            archetype_id="upper_reject_sell",
        ),
        action="BUY",
        h1_gap=0.0,
        m1_gap=4.0,
        score_gap=8.0,
    )

    assert out.setup_id == ""
    assert out.status == "rejected"
    assert out.metadata["reason"] == "setup_naming_side_mismatch_sell"


def test_setup_detector_rejects_unmapped_shadow_confirm():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="SELL",
            confidence=0.61,
            reason="failed_buy_break_sell_confirm",
            archetype_id="FAILED_BUY_BREAK_SELL_CONFIRM",
        ),
        action="SELL",
        h1_gap=0.0,
        m1_gap=-4.0,
        score_gap=-8.0,
    )

    assert out.setup_id == ""
    assert out.status == "rejected"
    assert out.metadata["reason"] == "setup_naming_unmapped_failed_buy_break_sell_confirm"


def test_setup_detector_ignores_gap_inputs_for_naming_only_output():
    detector = SetupDetector()

    out_a = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="BUY",
            confidence=0.64,
            reason="lower_rebound_confirm",
            archetype_id="lower_hold_buy",
        ),
        action="BUY",
        h1_gap=100.0,
        m1_gap=50.0,
        score_gap=999.0,
    )
    out_b = detector.detect_entry_setup(
        context=_ctx(
            action_state="OBSERVE",
            action="WAIT",
            confidence=0.64,
            reason="lower_rebound_confirm",
            archetype_id="lower_hold_buy",
        ),
        action="BUY",
        h1_gap=-100.0,
        m1_gap=-50.0,
        score_gap=-999.0,
    )

    assert out_a.setup_id == "range_lower_reversal_buy"
    assert out_b.setup_id == "range_lower_reversal_buy"
    assert out_a.trigger_state == "READY"
    assert out_b.trigger_state == "READY"
    assert out_a.entry_quality == 0.64
    assert out_b.entry_quality == 0.64


def test_setup_detector_consumes_observe_confirm_v2_only_handoff():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="BUY",
            confidence=0.74,
            reason="lower_rebound_confirm",
            archetype_id="lower_hold_buy",
            use_v2_only=True,
        ),
        action="BUY",
        h1_gap=0.0,
        m1_gap=5.0,
        score_gap=10.0,
    )

    assert out.setup_id == "range_lower_reversal_buy"
    assert out.status == "matched"


def test_setup_detector_prefers_canonical_observe_confirm_v2_over_conflicting_v1():
    detector = SetupDetector()

    out = detector.detect_entry_setup(
        context=_ctx(
            action_state="CONFIRM",
            action="SELL",
            confidence=0.63,
            reason="trend_pullback_sell_confirm",
            archetype_id="mid_lose_sell",
            use_v2_only=True,
            include_conflicting_v1=True,
        ),
        action="SELL",
        h1_gap=0.0,
        m1_gap=-5.0,
        score_gap=-12.0,
    )

    assert out.setup_id == "trend_pullback_sell"
    assert out.status == "matched"
    assert out.metadata["reason"] == "shadow_trend_pullback_sell_confirm"
