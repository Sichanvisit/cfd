from types import SimpleNamespace

import json
import pandas as pd

from backend.core.config import Config
from backend.domain.decision_models import DecisionContext
from backend.services.consumer_contract import (
    CONSUMER_INPUT_CONTRACT_V1,
    CONSUMER_LOGGING_CONTRACT_V1,
    CONSUMER_SCOPE_CONTRACT_V1,
    ENTRY_GUARD_CONTRACT_V1,
    ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1,
    RE_ENTRY_CONTRACT_V1,
    SETUP_MAPPING_CONTRACT_V1,
)
from backend.services.consumer_check_state import build_consumer_check_state_v1
from backend.services.entry_service import EntryService
from backend.services.entry_try_open_entry import try_open_entry as helper_try_open_entry


class _DummyApp:
    pass


class _DummyLogger:
    pass


class _DummySessionMgr:
    def get_session_range(self, *_args, **_kwargs):
        return {"high": 110.0, "low": 90.0}

    def get_position_in_box(self, _session, _price):
        return "MIDDLE"


class _DummyScorer:
    def __init__(self):
        self.session_mgr = _DummySessionMgr()


def _svc() -> EntryService:
    return EntryService(_DummyApp(), _DummyLogger())


def _core_context(
    *,
    symbol: str,
    market_mode: str = "RANGE",
    direction_policy: str = "BOTH",
    box_state: str = "MIDDLE",
    bb_state: str = "MID",
    metadata: dict | None = None,
) -> DecisionContext:
    return DecisionContext(
        symbol=symbol,
        phase="entry",
        market_mode=market_mode,
        direction_policy=direction_policy,
        box_state=box_state,
        bb_state=bb_state,
        liquidity_state="GOOD",
        metadata=dict(metadata or {}),
    )


def _bind_context(
    svc: EntryService,
    *,
    context: DecisionContext,
    allowed_action: str | None = None,
    approach_mode: str = "MIX",
    reason: str = "unit_test",
    regime: str | None = None,
    liquidity: str = "GOOD",
) -> None:
    svc._context_classifier = SimpleNamespace(
        build_entry_context=lambda **_: {
            "context": context,
            "preflight": {
                "allowed_action": allowed_action or context.direction_policy,
                "approach_mode": approach_mode,
                "reason": reason,
                "regime": regime or context.market_mode,
                "liquidity": liquidity,
            },
        }
    )


def _core_result(
    *,
    h1_context_buy: int = 0,
    h1_context_sell: int = 0,
    m1_trigger_buy: int = 0,
    m1_trigger_sell: int = 0,
    wait_score: float = 0.0,
    wait_conflict: float = 0.0,
    wait_noise: float = 0.0,
) -> dict:
    return {
        "components": {
            "h1_context_buy": h1_context_buy,
            "h1_context_sell": h1_context_sell,
            "m1_trigger_buy": m1_trigger_buy,
            "m1_trigger_sell": m1_trigger_sell,
            "wait_score": wait_score,
            "wait_conflict": wait_conflict,
            "wait_noise": wait_noise,
        }
    }


def test_bb_guard_blocks_buy_below_midline(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=99.0, ask=99.1)
    indicators = {"ind_bb_20_mid": 100.0, "ind_bb_20_up": 102.0, "ind_bb_20_dn": 98.0}

    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_GUARD", True)
    monkeypatch.setattr(Config, "ENTRY_BB_MID_TOL_PCT", 0.0001)
    monkeypatch.setattr(Config, "ENTRY_BB_NEAR_BAND_PCT", 0.0002)

    ok, reason = svc._pass_bb_entry_guard("NAS100", "BUY", tick, indicators)
    assert ok is False
    assert reason == "bb_buy_without_lower_touch"


def test_cluster_guard_blocks_same_side_same_price_zone(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.005)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("NAS100", "BUY", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_service.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard("NAS100", "BUY", tick)
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_cluster_guard_blocks_xau_range_upper_sell_without_spacing(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.05, ask=100.055)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("XAUUSD", "SELL", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard(
        "XAUUSD",
        "SELL",
        tick,
        setup_id="range_upper_reversal_sell",
        preflight_allowed_action="BOTH",
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_cluster_guard_blocks_xau_breakout_sell_without_spacing(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.004, ask=100.005)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("XAUUSD", "SELL", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard(
        "XAUUSD",
        "SELL",
        tick,
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_cluster_guard_relaxes_nas_breakout_sell_even_with_both(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.03, ask=100.04)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("NAS100", "SELL", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard(
        "NAS100",
        "SELL",
        tick,
        setup_id="breakout_retest_sell",
        preflight_allowed_action="BOTH",
    )
    assert ok is True
    assert reason == ""


def test_cluster_guard_relaxes_btc_breakout_sell_more_aggressively(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.024, ask=100.03)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("BTCUSD", "SELL", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard(
        "BTCUSD",
        "SELL",
        tick,
        setup_id="breakout_retest_sell",
        preflight_allowed_action="SELL_ONLY",
    )
    assert ok is True
    assert reason == ""


def test_cluster_guard_blocks_xau_shadow_lower_buy_without_spacing(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.02, ask=100.03)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)

    svc.guard_engine.mark_entry("XAUUSD", "BUY", 100.0, 10**12 - 1)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    ok, reason = svc._pass_cluster_guard(
        "XAUUSD",
        "BUY",
        tick,
        setup_id="range_lower_reversal_buy",
        preflight_allowed_action="BOTH",
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_cluster_guard_relieves_semantic_same_thesis_edge_buy(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.04, ask=100.05)

    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 10**12)

    semantic_row = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.81,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.68,
            "buy_streak": 3,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.09,
        },
        "transition_confirm_fake_gap": 0.24,
        "management_continue_fail_gap": 0.41,
    }
    svc.runtime.latest_signal_by_symbol = {"XAUUSD": dict(semantic_row)}
    svc.guard_engine.mark_entry(
        "XAUUSD",
        "BUY",
        100.0,
        10**12 - 1,
        semantic_signature=svc.guard_engine.build_cluster_semantic_signature(semantic_row, action="BUY"),
    )

    ok, reason = svc._pass_cluster_guard(
        "XAUUSD",
        "BUY",
        tick,
        setup_id="range_lower_reversal_buy",
        preflight_allowed_action="BOTH",
    )
    assert ok is True
    assert reason == ""
    trace = svc.runtime.latest_signal_by_symbol["XAUUSD"]["entry_cluster_semantic_guard_v1"]
    assert trace["semantic_relief_applied"] is True


def test_try_open_entry_max_positions_skip_does_not_crash_without_consumer_ids(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = pd.DataFrame([{"Close": 100.0}])
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"BTCUSD": {}}
    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 1))
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)))

    helper_try_open_entry(
        svc,
        symbol="BTCUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=1,
        scorer=_DummyScorer(),
        buy_s=1.2,
        sell_s=0.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    assert logged_rows[-1]["blocked_by"] == "max_positions_reached"
    assert logged_rows[-1]["consumer_archetype_id"] == ""
    assert logged_rows[-1]["consumer_invalidation_id"] == ""
    assert logged_rows[-1]["consumer_management_profile_id"] == ""


def test_try_open_entry_topdown_skip_preserves_consumer_check_state_in_log_and_runtime(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"NAS100": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.ai_runtime = None
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "hard")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "MIDDLE")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(symbol="NAS100", box_state="UPPER", bb_state="UPPER_EDGE"),
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=15,
            entry_h1_context_opposite=0,
            entry_m1_trigger_score=10,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="nas_clean_confirm_probe",
            side="BUY",
            status="matched",
            trigger_state="CONFIRM",
            entry_quality=0.72,
            score=1.30,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=False, reason="forced_topdown_block", align=0, conflict=1, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "BUY",
            "observe_reason": "nas_clean_confirm_probe_observe",
            "action_none_reason": "probe_not_promoted",
            "blocked_by": "probe_promotion_gate",
            "core_pass": 1,
            "core_reason": "core_shadow_probe_wait",
            "core_allowed_action": "BUY",
            "h1_bias_strength": 0.5,
            "m1_trigger_strength": 0.4,
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_score": 1.7,
            "core_buy_raw": 1.7,
            "core_sell_raw": 0.3,
            "core_best_raw": 1.7,
            "core_min_raw": 0.3,
            "core_margin_raw": 1.4,
            "core_tie_band_raw": 0.1,
            "wait_score": 55.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "RANGE",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "BOTH",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.7,
            "consumer_energy_wait_vs_enter_hint": "wait",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_soft_block_reason": "",
            "consumer_energy_soft_block_strength": 0.0,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "nas_clean_confirm",
            "consumer_invalidation_id": "nas_upper_fail",
            "consumer_management_profile_id": "nas_hold_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": False,
                "reason": "probe_pair_gap_not_ready",
            },
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": True,
            "consumer_check_display_ready": True,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "PROBE",
            "consumer_check_reason": "probe_not_promoted",
            "consumer_check_display_strength_level": 6,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": True,
                "check_display_ready": True,
                "entry_ready": False,
                "check_side": "BUY",
                "check_stage": "PROBE",
                "check_reason": "probe_not_promoted",
                "entry_block_reason": "probe_not_promoted",
                "display_strength_level": 6,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="NAS100",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=1.2,
        sell_s=0.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["blocked_by"] == "topdown_timeframe_gate_blocked"
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_side"] == "BUY"
    assert out["consumer_check_stage"] == "PROBE"
    assert out["consumer_check_reason"] == "probe_not_promoted"
    assert out["consumer_check_state_v1"]["entry_block_reason"] == "probe_not_promoted"
    assert isinstance(out["entry_wait_context_v1"], dict)
    assert isinstance(out["entry_wait_bias_bundle_v1"], dict)
    assert isinstance(out["entry_wait_state_policy_input_v1"], dict)
    assert isinstance(out["entry_wait_energy_usage_trace_v1"], dict)
    assert isinstance(out["entry_wait_decision_energy_usage_trace_v1"], dict)
    assert out["entry_wait_context_v1"]["policy"]["state"] == out["entry_wait_state"]
    assert out["entry_wait_context_v1"]["reasons"]["blocked_by"] == out["blocked_by"]
    assert out["entry_wait_bias_bundle_v1"]["contract_version"] == "entry_wait_bias_bundle_v1"
    assert out["entry_wait_state_policy_input_v1"]["contract_version"] == "entry_wait_state_policy_input_v1"
    assert out["entry_wait_state_policy_input_v1"]["reason_split_v1"]["blocked_by"] == out["blocked_by"]

    live_row = svc.runtime.latest_signal_by_symbol["NAS100"]
    assert live_row["blocked_by"] == out["blocked_by"]
    assert live_row["consumer_check_display_ready"] is True
    assert live_row["consumer_check_stage"] == "PROBE"
    assert live_row["consumer_check_state_v1"]["check_stage"] == "PROBE"
    assert live_row["entry_wait_state"] == out["entry_wait_state"]
    assert live_row["entry_wait_reason"] == out["entry_wait_reason"]
    assert live_row["entry_wait_selected"] == out["entry_wait_selected"]
    assert live_row["entry_wait_decision"] == out["entry_wait_decision"]
    assert live_row["entry_wait_context_v1"]["policy"]["state"] == live_row["entry_wait_state"]
    assert live_row["entry_wait_context_v1"]["reasons"]["blocked_by"] == live_row["blocked_by"]
    assert live_row["entry_wait_bias_bundle_v1"]["contract_version"] == "entry_wait_bias_bundle_v1"
    assert live_row["entry_wait_state_policy_input_v1"]["contract_version"] == "entry_wait_state_policy_input_v1"
    assert live_row["entry_wait_state_policy_input_v1"]["reason_split_v1"]["blocked_by"] == live_row["blocked_by"]


def test_try_open_entry_blocks_consumer_stage_misalignment_before_order_submit(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"NAS100": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.ai_runtime = None
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )
    svc.runtime.get_order_block_status = lambda _symbol: {"active": False}
    svc.runtime.execute_order = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("execute_order should not be called")
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)) or dict(row))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "TREND")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "MIDDLE")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(
            symbol="NAS100",
            market_mode="TREND",
            direction_policy="BUY_ONLY",
            box_state="MIDDLE",
            bb_state="MID",
        ),
        allowed_action="BUY_ONLY",
        regime="TREND",
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=15,
            entry_h1_context_opposite=0,
            entry_m1_trigger_score=12,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="trend_pullback_buy",
            side="BUY",
            status="matched",
            trigger_state="CONFIRM",
            entry_quality=0.74,
            score=1.25,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=1, conflict=0, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "BUY",
            "observe_reason": "lower_rebound_confirm",
            "action_none_reason": "",
            "blocked_by": "",
            "core_pass": 1,
            "core_reason": "core_shadow_confirm_action",
            "core_allowed_action": "BUY",
            "h1_bias_strength": 0.6,
            "m1_trigger_strength": 0.5,
            "box_state": "MIDDLE",
            "bb_state": "MID",
            "core_score": 1.8,
            "core_buy_raw": 1.8,
            "core_sell_raw": 0.2,
            "core_best_raw": 1.8,
            "core_min_raw": 0.2,
            "core_margin_raw": 1.6,
            "core_tie_band_raw": 0.1,
            "wait_score": 54.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "TREND",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "BUY_ONLY",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.7,
            "consumer_energy_wait_vs_enter_hint": "wait",
            "consumer_energy_soft_block_active": True,
            "consumer_energy_soft_block_reason": "energy_soft_block",
            "consumer_energy_soft_block_strength": 0.4,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "lower_hold_buy",
            "consumer_invalidation_id": "lower_support_fail",
            "consumer_management_profile_id": "support_hold_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": False,
                "reason": "energy_soft_block",
            },
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": True,
            "consumer_check_display_ready": True,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "BLOCKED",
            "consumer_check_reason": "lower_rebound_confirm",
            "consumer_check_display_strength_level": 5,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": True,
                "check_display_ready": True,
                "entry_ready": False,
                "check_side": "BUY",
                "check_stage": "BLOCKED",
                "check_reason": "lower_rebound_confirm",
                "entry_block_reason": "energy_soft_block",
                "display_strength_level": 5,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="NAS100",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=1.3,
        sell_s=0.2,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["blocked_by"] == "consumer_stage_blocked"
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_stage"] == "BLOCKED"
    assert out["consumer_open_guard_v1"]["guard_active"] is True
    assert out["consumer_open_guard_v1"]["allows_open"] is False
    assert out["consumer_open_guard_v1"]["failure_code"] == "consumer_stage_blocked"


def test_try_open_entry_blocks_when_action_survives_with_blocked_by_guard(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"XAUUSD": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.ai_runtime = None
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )
    svc.runtime.get_order_block_status = lambda _symbol: {"active": False}
    svc.runtime.execute_order = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("execute_order should not be called")
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)) or dict(row))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "UPPER")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(symbol="XAUUSD", market_mode="RANGE", direction_policy="SELL_ONLY", box_state="UPPER", bb_state="UPPER_EDGE"),
        allowed_action="SELL_ONLY",
        regime="RANGE",
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=14,
            entry_h1_context_opposite=1,
            entry_m1_trigger_score=11,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="range_upper_reversal_sell",
            side="SELL",
            status="matched",
            trigger_state="CONFIRM",
            entry_quality=0.71,
            score=1.28,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=1, conflict=0, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "SELL",
            "observe_reason": "upper_reject_confirm",
            "action_none_reason": "observe_state_wait",
            "blocked_by": "forecast_guard",
            "core_pass": 1,
            "core_reason": "core_shadow_confirm_action",
            "core_allowed_action": "SELL",
            "h1_bias_strength": 0.6,
            "m1_trigger_strength": 0.5,
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_score": 1.9,
            "core_buy_raw": 0.1,
            "core_sell_raw": 1.9,
            "core_best_raw": 1.9,
            "core_min_raw": 0.1,
            "core_margin_raw": 1.8,
            "core_tie_band_raw": 0.1,
            "wait_score": 52.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "RANGE",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "SELL_ONLY",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.0,
            "consumer_energy_wait_vs_enter_hint": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_soft_block_reason": "",
            "consumer_energy_soft_block_strength": 0.0,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "upper_reject_sell",
            "consumer_invalidation_id": "upper_break_fail",
            "consumer_management_profile_id": "upper_reject_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {},
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": False,
            "consumer_check_display_ready": False,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "",
            "consumer_check_stage": "",
            "consumer_check_reason": "upper_reject_confirm",
            "consumer_check_display_strength_level": 0,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": False,
                "check_display_ready": False,
                "entry_ready": False,
                "check_side": "",
                "check_stage": "",
                "check_reason": "upper_reject_confirm",
                "entry_block_reason": "",
                "display_strength_level": 0,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="XAUUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=0.2,
        sell_s=1.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["blocked_by"] == "forecast_guard"
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["entry_blocked_guard_v1"]["guard_active"] is True
    assert out["entry_blocked_guard_v1"]["allows_open"] is False
    assert out["entry_blocked_guard_v1"]["failure_code"] == "forecast_guard"


def test_try_open_entry_blocks_probe_promotion_when_plan_is_not_ready(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {
        "XAUUSD": {
            "quick_trace_state": "PROBE",
            "quick_trace_reason": "probe_candidate_active",
            "probe_scene_id": "xau_upper_sell_probe",
        }
    }
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.ai_runtime = None
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )
    svc.runtime.get_order_block_status = lambda _symbol: {"active": False}
    svc.runtime.execute_order = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("execute_order should not be called")
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)) or dict(row))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "UPPER")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(
            symbol="XAUUSD",
            market_mode="RANGE",
            direction_policy="SELL_ONLY",
            box_state="UPPER",
            bb_state="UPPER_EDGE",
        ),
        allowed_action="SELL_ONLY",
        regime="RANGE",
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=14,
            entry_h1_context_opposite=0,
            entry_m1_trigger_score=11,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="range_upper_reversal_sell",
            side="SELL",
            status="matched",
            trigger_state="PROBE",
            entry_quality=0.69,
            score=1.18,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=1, conflict=0, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "SELL",
            "observe_reason": "upper_reject_probe_observe",
            "action_none_reason": "probe_not_promoted",
            "blocked_by": "",
            "core_pass": 1,
            "core_reason": "core_shadow_probe_action",
            "core_allowed_action": "SELL",
            "h1_bias_strength": 0.6,
            "m1_trigger_strength": 0.5,
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_score": 1.9,
            "core_buy_raw": 0.1,
            "core_sell_raw": 1.9,
            "core_best_raw": 1.9,
            "core_min_raw": 0.1,
            "core_margin_raw": 1.8,
            "core_tie_band_raw": 0.1,
            "wait_score": 52.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "RANGE",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "SELL_ONLY",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.0,
            "consumer_energy_wait_vs_enter_hint": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_soft_block_reason": "",
            "consumer_energy_soft_block_strength": 0.0,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "upper_reject_sell",
            "consumer_invalidation_id": "upper_break_fail",
            "consumer_management_profile_id": "upper_reject_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": False,
                "reason": "probe_forecast_not_ready",
                "intended_action": "SELL",
                "symbol_scene_relief": "xau_upper_sell_probe",
            },
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": False,
            "consumer_check_display_ready": False,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "",
            "consumer_check_stage": "",
            "consumer_check_reason": "",
            "consumer_check_display_strength_level": 0,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": False,
                "check_display_ready": False,
                "entry_ready": False,
                "check_side": "",
                "check_stage": "",
                "check_reason": "",
                "entry_block_reason": "",
                "display_strength_level": 0,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="XAUUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=0.2,
        sell_s=1.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["blocked_by"] == "probe_promotion_gate"
    assert out["action_none_reason"] == "probe_not_promoted"
    assert out["probe_promotion_guard_v1"]["guard_active"] is True
    assert out["probe_promotion_guard_v1"]["allows_open"] is False
    assert out["probe_promotion_guard_v1"]["failure_code"] == "probe_promotion_gate"
    assert out["probe_promotion_guard_v1"]["plan_ready_for_entry"] is False
    assert out["probe_promotion_guard_v1"]["quick_trace_state"] == "PROBE"


def test_try_open_entry_range_lower_skip_downgrades_ready_consumer_check_state(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"BTCUSD": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "LOWER")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(symbol="BTCUSD", box_state="BELOW", bb_state="BREAKDOWN"),
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=15,
            entry_h1_context_opposite=0,
            entry_m1_trigger_score=10,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="range_lower_reversal_buy",
            side="BUY",
            status="matched",
            trigger_state="CONFIRM",
            entry_quality=0.72,
            score=1.30,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=1, conflict=0, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "BUY",
            "observe_reason": "lower_rebound_confirm",
            "action_none_reason": "",
            "blocked_by": "",
            "core_pass": 1,
            "core_reason": "core_shadow_confirm_action",
            "core_allowed_action": "BUY",
            "h1_bias_strength": 0.5,
            "m1_trigger_strength": 0.4,
            "box_state": "BELOW",
            "bb_state": "BREAKDOWN",
            "core_score": 1.7,
            "core_buy_raw": 1.7,
            "core_sell_raw": 0.3,
            "core_best_raw": 1.7,
            "core_min_raw": 0.3,
            "core_margin_raw": 1.4,
            "core_tie_band_raw": 0.1,
            "wait_score": 55.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "RANGE",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "BOTH",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.8,
            "consumer_energy_wait_vs_enter_hint": "enter",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_soft_block_reason": "",
            "consumer_energy_soft_block_strength": 0.0,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "btc_lower_reversal",
            "consumer_invalidation_id": "btc_lower_fail",
            "consumer_management_profile_id": "btc_hold_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {
                "active": True,
                "ready_for_entry": True,
                "reason": "",
            },
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": True,
            "consumer_check_display_ready": True,
            "consumer_check_entry_ready": True,
            "consumer_check_side": "BUY",
            "consumer_check_stage": "READY",
            "consumer_check_reason": "lower_rebound_confirm",
            "consumer_check_display_strength_level": 8,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": True,
                "check_display_ready": True,
                "entry_ready": True,
                "check_side": "BUY",
                "check_stage": "READY",
                "check_reason": "lower_rebound_confirm",
                "entry_block_reason": "",
                "display_strength_level": 8,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="BTCUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=1.2,
        sell_s=0.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["blocked_by"] == "range_lower_buy_requires_lower_edge"
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_stage"] == "BLOCKED"
    assert out["consumer_check_state_v1"]["entry_ready"] is False
    assert out["entry_wait_selected"] == 0
    assert out["entry_wait_decision"] == "skip"
    assert out["entry_wait_context_v1"]["policy"]["state"] == out["entry_wait_state"]
    assert out["entry_wait_context_v1"]["reasons"]["blocked_by"] == out["blocked_by"]
    assert out["entry_wait_bias_bundle_v1"]["contract_version"] == "entry_wait_bias_bundle_v1"
    assert out["entry_wait_state_policy_input_v1"]["contract_version"] == "entry_wait_state_policy_input_v1"
    assert out["entry_wait_state_policy_input_v1"]["reason_split_v1"]["blocked_by"] == out["blocked_by"]

    live_row = svc.runtime.latest_signal_by_symbol["BTCUSD"]
    assert live_row["blocked_by"] == out["blocked_by"]
    assert live_row["consumer_check_display_ready"] is False
    assert live_row["consumer_check_entry_ready"] is False
    assert live_row["consumer_check_stage"] == "BLOCKED"
    assert live_row["entry_wait_state"] == out["entry_wait_state"]
    assert live_row["entry_wait_reason"] == out["entry_wait_reason"]
    assert live_row["entry_wait_selected"] == out["entry_wait_selected"]
    assert live_row["entry_wait_decision"] == out["entry_wait_decision"]
    assert live_row["entry_wait_context_v1"]["policy"]["state"] == live_row["entry_wait_state"]
    assert live_row["entry_wait_context_v1"]["reasons"]["blocked_by"] == live_row["blocked_by"]
    assert live_row["entry_wait_bias_bundle_v1"]["contract_version"] == "entry_wait_bias_bundle_v1"
    assert live_row["entry_wait_state_policy_input_v1"]["contract_version"] == "entry_wait_state_policy_input_v1"
    assert live_row["entry_wait_state_policy_input_v1"]["reason_split_v1"]["blocked_by"] == live_row["blocked_by"]


def test_try_open_entry_does_not_materialize_hidden_conflict_observe_into_blocked_display(monkeypatch):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"XAUUSD": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "UPPER")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(symbol="XAUUSD", box_state="UPPER", bb_state="LOWER_EDGE"),
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=10,
            entry_h1_context_opposite=10,
            entry_m1_trigger_score=10,
            entry_m1_trigger_opposite=10,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="conflict_observe",
            side="SELL",
            status="matched",
            trigger_state="OBSERVE",
            entry_quality=0.22,
            score=0.40,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=0, conflict=1, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": None,
            "observe_reason": "conflict_box_upper_bb20_lower_balanced_observe",
            "action_none_reason": "observe_state_wait",
            "blocked_by": "",
            "core_pass": 0,
            "core_reason": "core_shadow_observe_wait",
            "core_allowed_action": "SELL_ONLY",
            "box_state": "UPPER",
            "bb_state": "LOWER_EDGE",
            "consumer_check_candidate": False,
            "consumer_check_display_ready": False,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "SELL",
            "consumer_check_stage": "",
            "consumer_check_reason": "conflict_box_upper_bb20_lower_balanced_observe",
            "consumer_check_display_strength_level": 0,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": False,
                "check_display_ready": False,
                "entry_ready": False,
                "check_side": "SELL",
                "check_stage": "",
                "check_reason": "conflict_box_upper_bb20_lower_balanced_observe",
                "entry_block_reason": "observe_state_wait",
                "display_strength_level": 0,
            },
        },
    )

    helper_try_open_entry(
        svc,
        symbol="XAUUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=0.5,
        sell_s=0.4,
        entry_threshold=1.0,
    )

    assert logged_rows
    out = logged_rows[-1]
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_stage"] == ""
    assert out["consumer_check_state_v1"]["check_candidate"] is False

def test_append_entry_decision_log_rewrites_try_open_entry_observe_confirm_to_v2_canonical(monkeypatch):
    svc = _svc()
    svc.runtime.latest_signal_by_symbol = {}
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(
        svc.decision_recorder,
        "append_entry_decision_log",
        lambda row: dict(row),
    )
    out = svc._append_entry_decision_log(
        {
            "time": "2026-03-26T18:30:00",
            "symbol": "BTCUSD",
            "action": "BUY",
            "considered": 1,
            "outcome": "wait",
            "observe_reason": "lower_rebound_confirm",
            "blocked_by": "",
            "setup_id": "range_lower_reversal_buy",
            "setup_side": "BUY",
            "setup_status": "matched",
            "setup_trigger_state": "confirm",
            "setup_score": 0.82,
            "setup_entry_quality": 0.71,
            "setup_reason": "lower_rebound_confirm",
            "prs_contract_version": "v2",
            "prs_canonical_observe_confirm_field": "observe_confirm_v1",
            "observe_confirm_v1": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.74,
                "reason": "lower_rebound_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {},
            },
        }
    )

    guard = json.loads(str(out["consumer_migration_guard_v1"]))
    observe_v2 = out["observe_confirm_v2"]
    if isinstance(observe_v2, str):
        observe_v2 = json.loads(observe_v2)

    assert out["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert out["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert out["consumer_input_observe_confirm_field"] == "observe_confirm_v2"
    assert observe_v2["archetype_id"] == "lower_hold_buy"
    assert guard["resolved_field_name"] == "observe_confirm_v2"
    assert guard["used_compatibility_fallback_v1"] is False


def test_box_middle_guard_blocks_when_no_bb_support(monkeypatch):
    svc = _svc()
    scorer = _DummyScorer()
    tick = SimpleNamespace(bid=100.0, ask=100.05)
    m15 = pd.DataFrame(
        {
            "high": [100.2, 100.25, 100.3, 100.28, 100.27],
            "low": [100.16, 100.18, 100.19, 100.20, 100.21],
            "close": [100.1, 100.12, 100.14, 100.13, 100.12],
        }
    )
    df_all = {"1H": pd.DataFrame({"time": [1], "high": [110.0], "low": [90.0]}), "15M": m15}
    indicators = {"ind_bb_20_mid": 100.0, "ind_bb_20_up": 101.0, "ind_bb_20_dn": 99.0}

    monkeypatch.setattr(Config, "ENABLE_ENTRY_BOX_MID_GUARD", True)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_NEAR_RATIO", 0.0005)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_TOL_PCT", 0.0002)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_BAND_NEAR_PCT", 0.0003)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_LOOKBACK", 4)

    ok, reason = svc._pass_box_middle_guard("NAS100", "BUY", tick, df_all, scorer, indicators)
    assert ok is False
    assert reason == "box_middle_buy_without_bb_support"


def test_box_middle_guard_relaxes_btc_shadow_upper_sell(monkeypatch):
    svc = _svc()
    scorer = _DummyScorer()
    tick = SimpleNamespace(bid=100.78, ask=100.82)
    m15 = pd.DataFrame(
        {
            "high": [100.65, 100.70, 100.76, 100.79, 100.81],
            "low": [100.18, 100.22, 100.25, 100.31, 100.35],
            "close": [100.40, 100.48, 100.60, 100.72, 100.76],
        }
    )
    df_all = {"1H": pd.DataFrame({"time": [1], "high": [110.0], "low": [90.0]}), "15M": m15}
    indicators = {"ind_bb_20_mid": 100.5, "ind_bb_20_up": 101.0, "ind_bb_20_dn": 99.0}

    monkeypatch.setattr(Config, "ENABLE_ENTRY_BOX_MID_GUARD", True)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_NEAR_RATIO", 0.0005)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_TOL_PCT", 0.0002)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_BAND_NEAR_PCT", 0.0003)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_LOOKBACK", 4)

    ok, reason = svc._pass_box_middle_guard(
        "BTCUSD",
        "SELL",
        tick,
        df_all,
        scorer,
        indicators,
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_reject_confirm",
    )
    assert ok is True
    assert reason == ""


def test_box_middle_guard_relaxes_xau_shadow_upper_sell(monkeypatch):
    svc = _svc()
    scorer = _DummyScorer()
    tick = SimpleNamespace(bid=100.78, ask=100.82)
    m15 = pd.DataFrame(
        {
            "high": [100.65, 100.70, 100.76, 100.79, 100.81],
            "low": [100.18, 100.22, 100.25, 100.31, 100.35],
            "close": [100.40, 100.48, 100.60, 100.72, 100.76],
        }
    )
    df_all = {"1H": pd.DataFrame({"time": [1], "high": [110.0], "low": [90.0]}), "15M": m15}
    indicators = {"ind_bb_20_mid": 100.5, "ind_bb_20_up": 101.0, "ind_bb_20_dn": 99.0}

    monkeypatch.setattr(Config, "ENABLE_ENTRY_BOX_MID_GUARD", True)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_NEAR_RATIO", 0.0005)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_TOL_PCT", 0.0002)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_BAND_NEAR_PCT", 0.0003)
    monkeypatch.setattr(Config, "ENTRY_BOX_MID_RETEST_LOOKBACK", 4)

    ok, reason = svc._pass_box_middle_guard(
        "XAUUSD",
        "SELL",
        tick,
        df_all,
        scorer,
        indicators,
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_reject_confirm",
    )
    assert ok is True
    assert reason == ""


def test_core_action_decision_requires_observe_confirm():
    svc = _svc()
    context = _core_context(symbol="BTCUSD", box_state="LOWER", bb_state="LOWER_EDGE")
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=20, wait_conflict=0, wait_noise=10),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "core_observe_confirm_missing"
    assert out["action_none_reason"] == "observe_confirm_missing"
    assert out["consumer_block_reason"] == "observe_confirm_missing"
    assert out["consumer_block_kind"] == "consumer_input_block"
    assert out["consumer_block_source_layer"] == "consumer_input"
    assert out["consumer_block_is_execution"] is False
    assert out["consumer_guard_result"] == "SEMANTIC_NON_ACTION"
    assert out["consumer_effective_action"] == "NONE"
    assert out["consumer_input_observe_confirm_field"] == "observe_confirm_v2"
    assert out["consumer_input_contract_version"] == "consumer_input_contract_v1"


def test_core_action_decision_waits_on_shadow_observe():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        metadata={
            "observe_confirm_v1": {
                "state": "OBSERVE",
                "action": "WAIT",
                "reason": "observe_default",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BUY_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=1, m1_trigger_buy=2, m1_trigger_sell=1, wait_score=18),
        buy_s=140.0,
        sell_s=25.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["observe_reason"] == "observe_default"
    assert out["blocked_by"] == ""
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_block_reason"] == ""
    assert out["consumer_block_kind"] == ""
    assert out["consumer_block_is_execution"] is False
    assert out["consumer_guard_result"] == "SEMANTIC_NON_ACTION"
    assert out["consumer_effective_action"] == "NONE"


def test_core_action_decision_separates_observe_reason_and_semantic_guard_block():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.44,
                "archetype_id": "lower_hold_buy",
                "metadata": {
                    "blocked_reason": "outer_band_buy_reversal_support_required",
                },
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=1, m1_trigger_buy=2, m1_trigger_sell=1, wait_score=12),
        buy_s=118.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["observe_reason"] == "lower_rebound_probe_observe"
    assert out["blocked_by"] == "outer_band_guard"
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_block_reason"] == "outer_band_buy_reversal_support_required"
    assert out["consumer_block_kind"] == "semantic_non_action"


def test_core_action_decision_keeps_generic_directional_observe_out_of_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        market_mode="RANGE",
        direction_policy="BUY_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "upper_approach_observe",
                "confidence": 0.38,
                "archetype_id": "trend_pullback_buy",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BUY_ONLY", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.2),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=2, m1_trigger_sell=1, wait_score=18),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["consumer_check_candidate"] is False
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_stage"] == ""


def test_core_action_decision_promotes_structural_observe_to_weak_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="MIDDLE",
        bb_state="UNKNOWN",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "outer_band_reversal_support_required_observe",
                "confidence": 0.22,
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.2),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=3, m1_trigger_buy=1, m1_trigger_sell=2, wait_score=16),
        buy_s=30.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["observe_reason"] == "outer_band_reversal_support_required_observe"
    assert out["consumer_check_candidate"] is True
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_side"] == "SELL"
    assert out["consumer_check_stage"] == "OBSERVE"
    assert out["consumer_check_display_strength_level"] in {4, 5}


def test_core_action_decision_promotes_specific_watch_reason_to_weak_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "btc_midline_sell_watch",
                "confidence": 0.10,
                "archetype_id": "mid_lose_sell",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.2),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=2, m1_trigger_buy=1, m1_trigger_sell=2, wait_score=18),
        buy_s=30.0,
        sell_s=112.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["observe_reason"] == "btc_midline_sell_watch"
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_check_candidate"] is True
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_side"] == "SELL"
    assert out["consumer_check_stage"] == "OBSERVE"
    assert out["consumer_check_display_strength_level"] == 4


def test_build_consumer_check_state_assigns_single_repeat_score_for_observe():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "outer_band_reversal_support_required_observe",
            "observe_side": "BUY",
            "action": "WAIT",
            "core_allowed_action": "BUY_ONLY",
        },
        canonical_symbol="BTCUSD",
        shadow_reason="outer_band_reversal_support_required_observe",
        shadow_side="BUY",
        box_state="LOWER",
        bb_state="MID",
    )

    assert state["check_stage"] == "OBSERVE"
    assert state["check_display_ready"] is True
    assert 0.70 <= float(state["display_score"]) < 0.80
    assert int(state["display_repeat_count"]) == 1


def test_build_consumer_check_state_assigns_double_repeat_score_for_probe():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_probe_observe",
            "observe_side": "BUY",
            "action_none_reason": "probe_not_promoted",
            "probe_scene_id": "btc_lower_buy_probe",
        },
        canonical_symbol="BTCUSD",
        shadow_reason="lower_rebound_probe_observe",
        shadow_side="BUY",
        box_state="LOWER",
        bb_state="MID",
        probe_plan_default={
            "active": True,
            "ready_for_entry": False,
            "candidate_support": 0.42,
            "pair_gap": 0.20,
        },
    )

    assert state["check_stage"] == "PROBE"
    assert state["check_display_ready"] is True
    assert 0.80 <= float(state["display_score"]) < 0.90
    assert int(state["display_repeat_count"]) == 2


def test_build_consumer_check_state_assigns_triple_repeat_score_for_ready():
    state = build_consumer_check_state_v1(
        payload={
            "observe_reason": "lower_rebound_confirm",
            "observe_side": "BUY",
            "action": "BUY",
            "consumer_effective_action": "BUY",
            "core_pass": 1,
        },
        canonical_symbol="BTCUSD",
        shadow_reason="lower_rebound_confirm",
        shadow_side="BUY",
        box_state="LOWER",
        bb_state="MID",
        probe_plan_default={
            "active": True,
            "ready_for_entry": True,
            "candidate_support": 0.48,
            "pair_gap": 0.24,
        },
    )

    assert state["check_stage"] == "READY"
    assert state["entry_ready"] is True
    assert float(state["display_score"]) >= 0.90
    assert int(state["display_repeat_count"]) == 3


def test_core_action_decision_keeps_balanced_conflict_observe_out_of_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "conflict_box_upper_bb20_lower_balanced_observe",
                "confidence": 0.09,
                "archetype_id": "upper_reject_sell",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.08,
                        "candidate_sell": 0.09,
                        "pair_gap": 0.02,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": False,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.2),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=2, m1_trigger_buy=2, m1_trigger_sell=2, wait_score=18),
        buy_s=64.0,
        sell_s=66.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["observe_reason"] == "conflict_box_upper_bb20_lower_balanced_observe"
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_check_candidate"] is False
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_stage"] == ""
    assert out["consumer_check_side"] == ""


def test_core_action_decision_separates_probe_promotion_gate_from_action_none_reason():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.41,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.87,
                        "pair_gap": 0.18,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.18,
                        "candidate_sell": 0.0,
                        "pair_gap": 0.18,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.21,
                    "p_sell_confirm": 0.03,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.09,
                    "p_fail_now": 0.42,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.06,
                    "wait_confirm_gap": 0.0,
                    "management_continue_fail_gap": -0.18,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.09,
                "sell_belief": 0.01,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.34,
                "sell_barrier": 0.18,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=14),
        buy_s=122.0,
        sell_s=28.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_probe_wait"
    assert out["observe_reason"] == "lower_rebound_probe_observe"
    assert out["blocked_by"] == "probe_promotion_gate"
    assert out["action_none_reason"] == "probe_not_promoted"
    assert out["consumer_block_reason"] == "probe_forecast_not_ready"
    assert out["consumer_block_kind"] == "semantic_non_action"
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_side"] == "BUY"
    assert out["consumer_check_stage"] == "PROBE"
    assert out["consumer_check_state_v1"]["entry_block_reason"] == "probe_not_promoted"


def test_core_action_decision_promotes_shadow_buy_confirm_for_any_symbol():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v1": {
                "state": "LOWER_REBOUND_CONFIRM",
                "action": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.82,
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=4, h1_context_sell=1, m1_trigger_buy=5, m1_trigger_sell=1, wait_score=20),
        buy_s=130.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_allowed_action"] == "BUY_ONLY"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["core_score"] == 0.82


def test_core_action_decision_promotes_shadow_sell_confirm_for_any_symbol():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v1": {
                "state": "UPPER_REJECT_CONFIRM",
                "action": "SELL",
                "reason": "upper_reject_confirm",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=5, wait_score=18),
        buy_s=30.0,
        sell_s=130.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_allowed_action"] == "SELL_ONLY"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["core_score"] == 0.55


def test_core_action_decision_consumes_observe_confirm_v2_only_handoff():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.82,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=4, h1_context_sell=1, m1_trigger_buy=5, m1_trigger_sell=1, wait_score=20),
        buy_s=130.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is True
    assert out["consumer_check_side"] == "BUY"
    assert out["consumer_check_stage"] == "READY"
    assert out["core_score"] == 0.82
    assert context.metadata["consumer_input_contract_v1"]["contract_version"] == CONSUMER_INPUT_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_input_contract_v1"]["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert context.metadata["setup_detector_responsibility_contract_v1"]["contract_version"] == "setup_detector_responsibility_v1"
    assert context.metadata["setup_detector_responsibility_contract_v1"]["scope"] == "setup_naming_only"
    assert context.metadata["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert context.metadata["setup_detector_responsibility_contract_v1"]["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert context.metadata["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert context.metadata["entry_service_responsibility_contract_v1"]["contract_version"] == ENTRY_SERVICE_RESPONSIBILITY_CONTRACT_V1["contract_version"]
    assert context.metadata["entry_service_responsibility_contract_v1"]["scope"] == "execution_guard_only"
    assert context.metadata["entry_service_responsibility_contract_v1"]["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_scope_contract_v1"]["contract_version"] == CONSUMER_SCOPE_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_scope_contract_v1"]["canonical_input_field"] == "observe_confirm_v2"
    assert context.metadata["consumer_scope_contract_v1"]["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_scope_contract_v1"]["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert context.metadata["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_scope_contract_v1"]["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert context.metadata["consumer_scope_contract_v1"]["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert out["consumer_archetype_id"] == "lower_hold_buy"
    assert out["consumer_invalidation_id"] == "lower_support_fail"
    assert out["consumer_management_profile_id"] == "support_hold_profile"
    assert out["consumer_input_observe_confirm_field"] == "observe_confirm_v2"
    assert out["consumer_input_contract_version"] == "consumer_input_contract_v1"
    assert out["consumer_guard_result"] == "PASS"
    assert out["consumer_effective_action"] == "BUY"
    assert out["consumer_block_reason"] == ""
    assert out["consumer_block_kind"] == ""


def test_core_action_decision_prefers_canonical_observe_confirm_v2_over_conflicting_v1():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        market_mode="TREND",
        direction_policy="SELL_ONLY",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "reason": "upper_reject_confirm",
                "confidence": 0.67,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
            },
            "observe_confirm_v1": {
                "state": "OBSERVE",
                "action": "WAIT",
                "reason": "legacy_wait",
                "confidence": 0.05,
                "archetype_id": "",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=5, wait_score=18),
        buy_s=30.0,
        sell_s=130.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["core_score"] == 0.67


def test_core_action_decision_blocks_upper_edge_buy_without_break_override_package():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "upper_break_confirm",
                "confidence": 0.72,
                "archetype_id": "upper_break_buy",
                "invalidation_id": "breakout_failure",
                "management_profile_id": "breakout_hold_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.09,
                        "candidate_sell": 0.08,
                        "pair_gap": 0.01,
                        "winner_side": "BUY",
                        "winner_archetype": "upper_break_buy",
                        "winner_clear": False,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.58,
                    "p_sell_confirm": 0.13,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.53,
                    "p_fail_now": 0.47,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.05,
                    "wait_confirm_gap": 0.01,
                    "management_continue_fail_gap": 0.0,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "mixed",
                "buy_belief": 0.49,
                "sell_belief": 0.41,
                "buy_persistence": 0.18,
                "sell_persistence": 0.12,
                "buy_streak": 1,
                "sell_streak": 1,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.28,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=2, m1_trigger_buy=4, m1_trigger_sell=2, wait_score=10),
        buy_s=130.0,
        sell_s=40.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "edge_pair_default_side_block"
    assert out["action_none_reason"] == "default_side_blocked"
    assert out["blocked_by"] == "upper_edge_buy_requires_break_override"
    assert out["consumer_block_kind"] == "semantic_non_action"
    assert out["consumer_block_source_layer"] == "entry_default_side_gate"
    assert out["entry_default_side_gate_v1"]["blocked"] is True
    assert out["entry_default_side_gate_v1"]["override_package_satisfied"] is False


def test_core_action_decision_allows_upper_edge_buy_with_complete_break_override_package():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="TREND",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "upper_break_confirm",
                "confidence": 0.78,
                "archetype_id": "upper_break_buy",
                "invalidation_id": "breakout_failure",
                "management_profile_id": "breakout_hold_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.22,
                        "candidate_sell": 0.09,
                        "pair_gap": 0.13,
                        "winner_side": "BUY",
                        "winner_archetype": "upper_break_buy",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.74,
                    "p_sell_confirm": 0.11,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.68,
                    "p_fail_now": 0.18,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.19,
                    "wait_confirm_gap": 0.09,
                    "management_continue_fail_gap": 0.15,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "continuation",
                "buy_belief": 0.67,
                "sell_belief": 0.18,
                "buy_persistence": 0.41,
                "sell_persistence": 0.11,
                "buy_streak": 3,
                "sell_streak": 1,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.44,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=4, h1_context_sell=1, m1_trigger_buy=5, m1_trigger_sell=1, wait_score=8),
        buy_s=135.0,
        sell_s=20.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["entry_default_side_gate_v1"]["blocked"] is False
    assert out["entry_default_side_gate_v1"]["override_package_satisfied"] is True


def test_core_action_decision_allows_default_side_probe_entry_when_probe_plan_is_ready():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.56,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.10,
                        "candidate_sell": 0.05,
                        "pair_gap": 0.05,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": False,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.56,
                    "p_sell_confirm": 0.18,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.59,
                    "p_fail_now": 0.32,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.05,
                    "wait_confirm_gap": 0.01,
                    "management_continue_fail_gap": 0.04,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.57,
                "sell_belief": 0.19,
                "buy_persistence": 0.24,
                "sell_persistence": 0.08,
                "buy_streak": 1,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.16,
                "sell_barrier": 0.29,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=9),
        buy_s=122.0,
        sell_s=34.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["recommended_entry_stage"] == "conservative"
    assert out["entry_probe_plan_v1"]["recommended_size_multiplier"] < 1.0


def test_core_action_decision_relaxes_probe_thresholds_for_xau_second_support_buy():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.55,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "xau_second_support_probe_relief": True,
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.11,
                        "candidate_sell": 0.05,
                        "pair_gap": 0.06,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": False,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.54,
                    "p_sell_confirm": 0.18,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.56,
                    "p_fail_now": 0.35,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.00,
                    "wait_confirm_gap": 0.01,
                    "management_continue_fail_gap": -0.03,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.45,
                "sell_belief": 0.18,
                "buy_persistence": 0.10,
                "sell_persistence": 0.02,
                "buy_streak": 1,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.31,
            },
            "energy_helper_v2": {
                "action_readiness": 0.40,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "soft_block_but_probe_relief",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.58,
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=9),
        buy_s=118.0,
        sell_s=28.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_second_support_buy_probe"
    assert out["consumer_energy_soft_block_active"] is True


def test_core_action_decision_promotes_wait_probe_candidate_using_winner_side():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.35,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.46,
                        "near_confirm": True,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.22,
                        "candidate_sell": 0.00,
                        "pair_gap": 0.22,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.30,
                    "p_sell_confirm": 0.10,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.14,
                    "p_fail_now": 0.30,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.01,
                    "wait_confirm_gap": 0.09,
                    "management_continue_fail_gap": -0.12,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.13,
                "sell_belief": 0.01,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.30,
                "sell_barrier": 0.20,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=12),
        buy_s=120.0,
        sell_s=35.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["candidate_side_hint"] == "BUY"


def test_core_action_decision_keeps_btc_lower_probe_wait_when_candidate_is_not_strong_enough():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.35,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.31,
                        "near_confirm": False,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.15,
                        "candidate_sell": 0.00,
                        "pair_gap": 0.15,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.24,
                    "p_sell_confirm": 0.10,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.12,
                    "p_fail_now": 0.32,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.01,
                    "wait_confirm_gap": 0.06,
                    "management_continue_fail_gap": -0.12,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.16,
                "sell_belief": 0.02,
                "buy_persistence": 0.04,
                "sell_persistence": 0.00,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.30,
                "sell_barrier": 0.20,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=12),
        buy_s=120.0,
        sell_s=35.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["core_allowed_action"] == "BUY_ONLY"
    assert out["core_intended_direction"] == "BUY"
    assert out["core_intended_action_source"] == "archetype_implied_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is False
    assert out["entry_probe_plan_v1"]["reason"] == "probe_pair_gap_not_ready"
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "btc_lower_buy_conservative_probe"


def test_core_action_decision_promotes_structural_btc_lower_probe_when_forecast_is_near_ready():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.33,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.9532137208985106,
                        "near_confirm": True,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.22,
                        "candidate_sell": 0.08,
                        "pair_gap": 0.13607701080972617,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.28,
                    "p_sell_confirm": 0.18,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.22,
                    "p_fail_now": 0.3453387807642622,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.09593309227951213,
                    "wait_confirm_gap": -0.031362,
                    "management_continue_fail_gap": -0.12533878076426222,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.04170007117235739,
                "sell_belief": 0.02,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.19739774704100835,
                "sell_barrier": 0.18,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=11),
        buy_s=118.0,
        sell_s=34.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "btc_lower_buy_conservative_probe"


def test_core_action_decision_promotes_structural_btc_upper_sell_probe_when_forecast_is_near_ready():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.24,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.4179,
                        "near_confirm": True,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.12,
                        "candidate_sell": 0.202,
                        "pair_gap": 0.0829,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.09,
                    "p_sell_confirm": 0.218,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.087,
                    "p_fail_now": 0.295,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.116,
                    "wait_confirm_gap": -0.051,
                    "management_continue_fail_gap": -0.178,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.02,
                "sell_belief": 0.03,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.20,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=5, wait_score=9),
        buy_s=36.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "btc_upper_sell_probe"


def test_core_action_decision_keeps_blocked_btc_upper_sell_probe_as_weak_display_check():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.18,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.06,
                        "near_confirm": False,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "btc_upper_sell_probe",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.24,
                        "candidate_sell": 0.00,
                        "pair_gap": 0.24,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.19,
                    "p_sell_confirm": 0.01,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.03,
                    "p_fail_now": 0.34,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.14,
                    "wait_confirm_gap": -0.08,
                    "management_continue_fail_gap": -0.30,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.01,
                "sell_belief": 0.002,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.55,
                "sell_barrier": 0.58,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=2, m1_trigger_buy=1, m1_trigger_sell=2, wait_score=18),
        buy_s=30.0,
        sell_s=112.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["observe_reason"] == "upper_reject_probe_observe"
    assert out["action_none_reason"] == "probe_not_promoted"
    assert out["consumer_check_candidate"] is True
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_side"] == "SELL"
    assert out["consumer_check_stage"] == "OBSERVE"


def test_core_action_decision_keeps_wait_probe_candidate_active_with_explicit_reason():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="BELOW",
        bb_state="UNKNOWN",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "confidence": 0.25,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.90,
                        "near_confirm": True,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.20,
                        "candidate_sell": 0.00,
                        "pair_gap": 0.20,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.23,
                    "p_sell_confirm": 0.02,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.08,
                    "p_fail_now": 0.36,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.08,
                    "wait_confirm_gap": -0.02,
                    "management_continue_fail_gap": -0.22,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BUY",
                "dominant_mode": "reversal",
                "buy_belief": 0.08,
                "sell_belief": 0.00,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.58,
                "sell_barrier": 0.20,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=14),
        buy_s=125.0,
        sell_s=32.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is False
    assert out["entry_probe_plan_v1"]["reason"] == "probe_forecast_not_ready"


def test_core_action_decision_promotes_live_like_xau_second_support_buy_via_structural_relief():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "BUY",
                "reason": "outer_band_reversal_support_required_observe",
                "confidence": 0.22,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "xau_second_support_probe_relief": True,
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "BUY",
                        "trigger_branch": "lower_rebound",
                        "candidate_support": 0.852236834869189,
                        "near_confirm": True,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_second_support_buy_probe",
                            "promotion_bias": "aggressive_second_support",
                            "entry_style_hint": "second_support_probe",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_second_support_buy_more_aggressive",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.208,
                        "candidate_sell": 0.021,
                        "pair_gap": 0.18737033146923063,
                        "winner_side": "BUY",
                        "winner_archetype": "lower_hold_buy",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.173233,
                    "p_sell_confirm": 0.021455,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.148,
                    "p_fail_now": 0.319,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.1467739361116228,
                    "wait_confirm_gap": -0.090749,
                    "management_continue_fail_gap": -0.17040298852170147,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.04900711877082087,
                "sell_belief": 0.0201,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.4634672677886277,
                "sell_barrier": 0.18,
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "barrier_soft_block",
                    "strength": 0.81,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=3, h1_context_sell=1, m1_trigger_buy=4, m1_trigger_sell=1, wait_score=12),
        buy_s=124.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert (
        out["entry_probe_plan_v1"]["xau_second_support_forecast_relief"] is True
        or out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    )
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_second_support_buy_probe"
    assert out["consumer_archetype_id"] == "lower_hold_buy"
    assert out["consumer_invalidation_id"] == "lower_support_fail"
    assert out["consumer_management_profile_id"] == "support_hold_profile"
    assert out["xau_second_support_energy_relief_applied"] is True


def test_core_action_decision_relaxes_energy_soft_block_for_xau_upper_sell_probe():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.53,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.04,
                        "candidate_sell": 0.09,
                        "pair_gap": 0.05,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": False,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.19,
                    "p_sell_confirm": 0.55,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.50,
                    "p_fail_now": 0.31,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.02,
                    "wait_confirm_gap": 0.01,
                    "management_continue_fail_gap": -0.02,
                },
            },
            "belief_state_v1": {
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_belief": 0.20,
                "sell_belief": 0.49,
                "buy_persistence": 0.04,
                "sell_persistence": 0.12,
                "buy_streak": 0,
                "sell_streak": 1,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.33,
                "sell_barrier": 0.17,
            },
            "energy_helper_v2": {
                "action_readiness": 0.42,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "soft_block_but_probe_relief",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.61,
                },
                "metadata": {
                    "forecast_gap_usage_v1": {
                        "active": True,
                        "transition_confirm_fake_gap": 0.02,
                        "management_continue_fail_gap": -0.02,
                        "management_recover_reentry_gap": 0.08,
                        "hold_exit_gap": -0.03,
                        "same_side_flip_gap": -0.05,
                        "confidence_assist_active": False,
                        "soft_block_assist_active": True,
                        "priority_assist_active": False,
                        "wait_assist_active": True,
                        "usage_mode": "active_branch_assist",
                    },
                    "utility_hints": {
                        "priority_hint": "medium",
                        "gap_dominant_hint": "WAIT_CLEAR",
                        "forecast_branch_hint": "continue_fail_drag",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=10),
        buy_s=32.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_upper_sell_probe"
    assert out["consumer_energy_soft_block_active"] is True


def test_core_action_decision_hides_repeated_xau_upper_break_fail_soft_block_from_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_break_fail_confirm",
                "confidence": 0.58,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.05,
                        "candidate_sell": 0.15,
                        "pair_gap": 0.10,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "energy_helper_v2": {
                "action_readiness": 0.34,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "forecast_wait_bias",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.72,
                },
                "metadata": {
                    "forecast_gap_usage_v1": {
                        "active": True,
                        "transition_confirm_fake_gap": 0.03,
                        "management_continue_fail_gap": -0.12,
                        "management_recover_reentry_gap": 0.09,
                        "hold_exit_gap": -0.08,
                        "same_side_flip_gap": -0.11,
                        "confidence_assist_active": False,
                        "soft_block_assist_active": True,
                        "priority_assist_active": False,
                        "wait_assist_active": True,
                        "usage_mode": "active_branch_assist",
                    },
                    "utility_hints": {
                        "priority_hint": "medium",
                        "gap_dominant_hint": "WAIT_CLEAR",
                        "forecast_branch_hint": "continue_fail_drag",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=10),
        buy_s=30.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["blocked_by"] == ""
    assert out["action_none_reason"] == "observe_state_wait"
    assert out["consumer_check_stage"] == "PROBE"
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_state_v1"]["blocked_display_reason"] == "observe_state_wait"


def test_core_action_decision_promotes_live_like_xau_upper_sell_probe_via_structural_relief():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.24,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.24,
                        "near_confirm": True,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_upper_sell_probe",
                            "promotion_bias": "fast_probe",
                            "entry_style_hint": "early_upper_reject_probe",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_upper_sell_probe_faster",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.03,
                        "candidate_sell": 0.11,
                        "pair_gap": 0.08,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.04,
                    "p_sell_confirm": 0.16,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.19,
                    "p_fail_now": 0.34,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.13,
                    "wait_confirm_gap": -0.08,
                    "management_continue_fail_gap": -0.19,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.03,
                "sell_belief": 0.05,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.46,
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.25,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=12),
        buy_s=30.0,
        sell_s=122.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["core_allowed_action"] == "SELL_ONLY"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_upper_sell_probe"
    assert out["xau_upper_sell_probe_energy_relief_applied"] is True


def test_core_action_decision_promotes_weaker_live_like_xau_upper_sell_probe_after_relief_tuning():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UNKNOWN",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.22,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.20,
                        "near_confirm": True,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_upper_sell_probe",
                            "promotion_bias": "fast_probe",
                            "entry_style_hint": "early_upper_reject_probe",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_upper_sell_probe_faster",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.03,
                        "candidate_sell": 0.10,
                        "pair_gap": 0.09,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.05,
                    "p_sell_confirm": 0.15,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.18,
                    "p_fail_now": 0.33,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.18,
                    "wait_confirm_gap": -0.11,
                    "management_continue_fail_gap": -0.20,
                },
            },
            "belief_state_v1": {
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_belief": 0.02,
                "sell_belief": 0.02,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.20,
                "sell_barrier": 0.46,
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.24,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=12),
        buy_s=30.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_upper_sell_probe"
    assert out["xau_upper_sell_probe_energy_relief_applied"] is True


def test_core_action_decision_promotes_balanced_live_trace_like_xau_upper_sell_probe_after_stagee_recalibration():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UNKNOWN",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.1644,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.1644,
                        "near_confirm": True,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_upper_sell_probe",
                            "promotion_bias": "fast_probe",
                            "entry_style_hint": "early_upper_reject_probe",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_upper_sell_probe_faster",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.0331,
                        "candidate_sell": 0.1491,
                        "pair_gap": 0.1160,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.01,
                    "p_sell_confirm": 0.16,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.06,
                    "p_fail_now": 0.34,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.179,
                    "wait_confirm_gap": -0.131,
                    "management_continue_fail_gap": -0.284,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.034,
                "sell_belief": 0.056,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.52,
                "sell_barrier": 0.645,
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.25,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=14),
        buy_s=75.0,
        sell_s=195.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_probe_action"
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is True
    assert out["entry_probe_plan_v1"]["symbol_scene_relief"] == "xau_upper_sell_probe"
    assert out["xau_upper_sell_probe_energy_relief_applied"] is True


def test_core_action_decision_keeps_too_weak_balanced_xau_upper_sell_probe_waiting_after_stagee_recalibration():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="UNKNOWN",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.156,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.156,
                        "near_confirm": True,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_upper_sell_probe",
                            "promotion_bias": "fast_probe",
                            "entry_style_hint": "early_upper_reject_probe",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_upper_sell_probe_faster",
                        },
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.033,
                        "candidate_sell": 0.111,
                        "pair_gap": 0.078,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.01,
                    "p_sell_confirm": 0.15,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.05,
                    "p_fail_now": 0.34,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.205,
                    "wait_confirm_gap": -0.145,
                    "management_continue_fail_gap": -0.305,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.03,
                "sell_belief": 0.05,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.54,
                "sell_barrier": 0.68,
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.25,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=14),
        buy_s=75.0,
        sell_s=195.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["blocked_by"] == ""
    assert out["action_none_reason"] == "probe_not_promoted"
    assert out["consumer_block_reason"] == ""
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["ready_for_entry"] is False
    assert out["entry_probe_plan_v1"]["reason"] == "probe_forecast_not_ready"
    assert out["entry_probe_plan_v1"]["structural_relief_applied"] is False
    assert out.get("xau_upper_sell_probe_energy_relief_applied", False) is False


def test_core_action_decision_relaxes_energy_soft_block_for_xau_upper_reject_mixed_confirm():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="MIDDLE",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_reject_mixed_confirm",
                "confidence": 0.58,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.04,
                        "candidate_sell": 0.12,
                        "pair_gap": 0.08,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.08,
                    "p_sell_confirm": 0.18,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.21,
                    "p_fail_now": 0.33,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.11,
                    "wait_confirm_gap": -0.07,
                    "management_continue_fail_gap": -0.15,
                },
            },
            "belief_state_v1": {
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_belief": 0.04,
                "sell_belief": 0.16,
                "buy_persistence": 0.0,
                "sell_persistence": 0.08,
                "buy_streak": 0,
                "sell_streak": 1,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.28,
            },
            "energy_helper_v2": {
                "action_readiness": 0.22,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "mixed_confirm_soft_block",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.66,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "medium",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=4, m1_trigger_buy=1, m1_trigger_sell=4, wait_score=10),
        buy_s=34.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["core_allowed_action"] == "SELL_ONLY"
    assert out["consumer_energy_soft_block_active"] is True
    assert out["xau_upper_mixed_confirm_energy_relief_applied"] is True


def test_core_action_decision_blocks_lower_edge_sell_without_break_override_package():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "lower_break_confirm",
                "confidence": 0.69,
                "archetype_id": "lower_break_sell",
                "invalidation_id": "breakdown_failure",
                "management_profile_id": "breakdown_hold_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.08,
                        "candidate_sell": 0.09,
                        "pair_gap": 0.01,
                        "winner_side": "SELL",
                        "winner_archetype": "lower_break_sell",
                        "winner_clear": False,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "lower_break_sell",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.17,
                    "p_sell_confirm": 0.55,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.51,
                    "p_fail_now": 0.49,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.04,
                    "wait_confirm_gap": 0.01,
                    "management_continue_fail_gap": 0.0,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "mixed",
                "buy_belief": 0.31,
                "sell_belief": 0.47,
                "buy_persistence": 0.15,
                "sell_persistence": 0.22,
                "buy_streak": 1,
                "sell_streak": 1,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.22,
                "sell_barrier": 0.24,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=3, m1_trigger_buy=2, m1_trigger_sell=4, wait_score=11),
        buy_s=45.0,
        sell_s=125.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "edge_pair_default_side_block"
    assert out["action_none_reason"] == "default_side_blocked"
    assert out["blocked_by"] == "lower_edge_sell_requires_break_override"
    assert out["consumer_block_kind"] == "semantic_non_action"
    assert out["consumer_block_source_layer"] == "entry_default_side_gate"
    assert out["entry_default_side_gate_v1"]["blocked"] is True
    assert out["entry_default_side_gate_v1"]["override_package_satisfied"] is False


def test_core_action_decision_allows_lower_upper_conflict_upper_reject_sell_override_when_package_is_complete():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_reject_confirm",
                "confidence": 0.72,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.11,
                        "candidate_sell": 0.19,
                        "pair_gap": 0.08,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "upper_reject_sell",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.18,
                    "p_sell_confirm": 0.63,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.58,
                    "p_fail_now": 0.15,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.16,
                    "wait_confirm_gap": 0.08,
                    "management_continue_fail_gap": 0.12,
                },
            },
            "belief_state_v1": {
                "dominant_side": "SELL",
                "dominant_mode": "reversal",
                "buy_belief": 0.21,
                "sell_belief": 0.68,
                "buy_persistence": 0.08,
                "sell_persistence": 0.44,
                "buy_streak": 0,
                "sell_streak": 2,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.34,
                "sell_barrier": 0.22,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=4, m1_trigger_buy=2, m1_trigger_sell=5, wait_score=11),
        buy_s=48.0,
        sell_s=128.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["entry_default_side_gate_v1"]["blocked"] is False
    assert out["entry_default_side_gate_v1"]["override_package_satisfied"] is True
    assert out["entry_default_side_gate_v1"]["conflict_local_upper_override"] is True
    assert "upper_reject_sell" in out["entry_default_side_gate_v1"]["allowed_override_archetypes"]


def test_core_action_decision_keeps_conflict_upper_reject_probe_plan_active_before_promotion():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="LOWER",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFLICT_OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "upper_reject_probe_observe",
                "confidence": 0.51,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "probe_candidate_v1": {
                        "contract_version": "probe_candidate_v1",
                        "active": True,
                        "probe_kind": "edge_probe",
                        "probe_direction": "SELL",
                        "trigger_branch": "upper_reject",
                        "candidate_support": 0.23,
                        "opposing_support": 0.22,
                        "floor": 0.10,
                        "advantage": 0.03,
                        "near_confirm": True,
                    },
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "LOWER_EDGE",
                        "candidate_buy": 0.18,
                        "candidate_sell": 0.23,
                        "pair_gap": 0.05,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": False,
                        "active_branch_side": "BUY",
                        "active_branch_archetype": "lower_hold_buy",
                        "opposing_branch_side": "SELL",
                        "opposing_branch_archetype": "upper_reject_sell",
                    },
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.15,
                    "p_sell_confirm": 0.24,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.21,
                    "p_fail_now": 0.33,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.05,
                    "wait_confirm_gap": -0.03,
                    "management_continue_fail_gap": -0.09,
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.22,
                "sell_belief": 0.28,
                "buy_persistence": 0.03,
                "sell_persistence": 0.04,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.32,
                "sell_barrier": 0.29,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=2, h1_context_sell=3, m1_trigger_buy=2, m1_trigger_sell=4, wait_score=11),
        buy_s=52.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["core_allowed_action"] == "SELL_ONLY"
    assert out["core_intended_direction"] == "SELL"
    assert out["core_intended_action_source"] == "archetype_implied_action"
    assert out["action_none_reason"] == "probe_not_promoted"
    assert out["blocked_by"] == ""
    assert out["entry_probe_plan_v1"]["active"] is True
    assert out["entry_probe_plan_v1"]["reason"] != "probe_not_observe_stage"


def test_core_action_decision_wait_row_keeps_direction_trace_from_shadow_side():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="RANGE",
        direction_policy="BOTH",
        box_state="UPPER",
        bb_state="MID",
        metadata={
            "observe_confirm_v2": {
                "state": "OBSERVE",
                "action": "WAIT",
                "side": "SELL",
                "reason": "middle_sr_anchor_required_observe",
                "confidence": 0.41,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="BOTH", approach_mode="MIX", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(h1_context_buy=1, h1_context_sell=2, m1_trigger_buy=1, m1_trigger_sell=2, wait_score=10),
        buy_s=48.0,
        sell_s=62.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["core_reason"] == "core_shadow_observe_wait"
    assert out["core_intended_direction"] == "SELL"
    assert out["core_intended_action_source"] == "shadow_side"


def test_core_action_decision_blocks_opposite_position_lock():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v1": {
                "state": "LOWER_REBOUND_CONFIRM",
                "action": "BUY",
                "reason": "lower_rebound_confirm",
            }
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=15),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=True,
    )

    assert out["core_pass"] == 1
    assert out["action"] is None
    assert out["action_none_reason"] == "opposite_position_lock"
    assert out["blocked_by"] == "opposite_position_lock"
    assert out["consumer_block_reason"] == "opposite_position_lock"
    assert out["consumer_block_kind"] == "execution_block"
    assert out["consumer_block_source_layer"] == "position_lock"
    assert out["consumer_block_is_execution"] is True
    assert out["consumer_guard_result"] == "EXECUTION_BLOCK"
    assert out["consumer_effective_action"] == "NONE"


def test_core_action_decision_blocks_execution_without_rewriting_handoff_ids():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.79,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=15),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=True,
    )

    assert out["core_pass"] == 1
    assert out["action"] is None
    assert out["action_none_reason"] == "opposite_position_lock"
    assert out["consumer_archetype_id"] == "lower_hold_buy"
    assert out["consumer_invalidation_id"] == "lower_support_fail"
    assert out["consumer_management_profile_id"] == "support_hold_profile"
    assert out["consumer_block_kind"] == "execution_block"
    assert out["consumer_block_is_execution"] is True
    assert out["consumer_guard_result"] == "EXECUTION_BLOCK"
    assert out["consumer_effective_action"] == "NONE"
    assert context.metadata["observe_confirm_v2"]["action"] == "BUY"
    assert context.metadata["observe_confirm_v2"]["archetype_id"] == "lower_hold_buy"


def test_core_action_decision_blocks_hard_no_trade(monkeypatch):
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="SHOCK",
        direction_policy="NONE",
        metadata={
            "observe_confirm_v1": {
                "state": "LOWER_REBOUND_CONFIRM",
                "action": "BUY",
                "reason": "lower_rebound_confirm",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="NONE", approach_mode="NO_TRADE", reason="preflight_shock", regime="SHOCK")

    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_HARD_BLOCK", True)
    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_HARD_BLOCK_SHOCK_ONLY", True)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=15),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "preflight_no_trade_hard"
    assert out["blocked_by"] == "preflight_no_trade"
    assert out["action_none_reason"] == "preflight_blocked"
    assert out["consumer_block_kind"] == "preflight_block"
    assert out["consumer_block_is_execution"] is False
    assert out["consumer_guard_result"] == "SEMANTIC_NON_ACTION"


def test_core_action_decision_blocks_hard_direction_mismatch(monkeypatch):
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="MIDDLE",
        bb_state="MID",
        metadata={
            "observe_confirm_v1": {
                "state": "UPPER_REJECT_CONFIRM",
                "action": "SELL",
                "reason": "upper_reject_confirm",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BUY_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_ENFORCE_DIRECTION_HARD", True)
    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_DIRECTION_PENALTY", 11.0)
    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_DIRECTION_PENALTY_BY_SYMBOL", {})

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=15),
        buy_s=30.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "preflight_direction_hard_block"
    assert out["blocked_by"] == "preflight_action_blocked"
    assert out["action_none_reason"] == "preflight_blocked"
    assert out["consumer_block_kind"] == "preflight_block"
    assert out["consumer_block_is_execution"] is False
    assert out["consumer_guard_result"] == "SEMANTIC_NON_ACTION"
    assert out["preflight_direction_penalty_applied"] == 11.0


def test_core_action_decision_keeps_extreme_counter_neutralization(monkeypatch):
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        market_mode="TREND",
        direction_policy="BUY_ONLY",
        box_state="ABOVE",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v1": {
                "state": "UPPER_REJECT_CONFIRM",
                "action": "SELL",
                "reason": "upper_reject_confirm",
            }
        },
    )
    _bind_context(svc, context=context, allowed_action="BUY_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    monkeypatch.setattr(Config, "ENTRY_PREFLIGHT_ENFORCE_DIRECTION_HARD", True)

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=110.0, ask=110.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=12),
        buy_s=30.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"


def test_core_action_decision_applies_layer_mode_hard_block_to_live_branch():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.74,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "layer_mode_policy_v1": {
                "layer_modes": [{"layer": "Barrier", "mode": "enforce"}],
                "effective_influences": [{"layer": "Barrier", "active_effects": ["hard_block"]}],
                "suppressed_reasons": [],
                "confidence_adjustments": [],
                "hard_blocks": [{"layer": "Barrier", "mode": "enforce", "effect": "hard_block"}],
                "mode_decision_trace": {"layers": [{"layer": "Barrier", "identity_preserved": True}]},
                "identity_preserved": True,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
                "layer_mode_policy_output_field": "layer_mode_policy_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=12),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "layer_mode_policy_hard_block"
    assert out["blocked_by"] == "layer_mode_policy_hard_block"
    assert out["action_none_reason"] == "policy_hard_blocked"
    assert out["consumer_block_reason"] == "layer_mode_policy_hard_block"
    assert out["consumer_block_kind"] == "execution_block"
    assert out["consumer_block_source_layer"] == "layer_mode_policy"
    assert out["consumer_block_is_execution"] is True
    assert out["consumer_guard_result"] == "EXECUTION_BLOCK"
    assert out["consumer_policy_identity_preserved"] is True
    assert out["consumer_archetype_id"] == "lower_hold_buy"
    assert out["consumer_invalidation_id"] == "lower_support_fail"
    assert out["consumer_management_profile_id"] == "support_hold_profile"
    assert out["consumer_layer_mode_hard_block_active"] is True


def test_core_action_decision_applies_layer_mode_confirm_suppression_to_live_branch():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.71,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "layer_mode_policy_v1": {
                "layer_modes": [{"layer": "Forecast", "mode": "enforce"}],
                "effective_influences": [{"layer": "Forecast", "active_effects": ["confirm_to_observe_suppression"]}],
                "suppressed_reasons": [
                    {"layer": "Forecast", "mode": "enforce", "effect": "confirm_to_observe_suppression"}
                ],
                "confidence_adjustments": [],
                "hard_blocks": [],
                "mode_decision_trace": {"layers": [{"layer": "Forecast", "identity_preserved": True}]},
                "identity_preserved": True,
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
                "layer_mode_policy_output_field": "layer_mode_policy_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=12),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "layer_mode_confirm_suppressed"
    assert out["blocked_by"] == "layer_mode_confirm_suppressed"
    assert out["action_none_reason"] == "confirm_suppressed"
    assert out["consumer_block_reason"] == "layer_mode_confirm_suppressed"
    assert out["consumer_block_kind"] == "semantic_non_action"
    assert out["consumer_block_source_layer"] == "layer_mode_policy"
    assert out["consumer_block_is_execution"] is False
    assert out["consumer_guard_result"] == "SEMANTIC_NON_ACTION"
    assert out["consumer_policy_block_layer"] == "Forecast"
    assert out["consumer_policy_block_effect"] == "confirm_to_observe_suppression"
    assert out["consumer_layer_mode_suppressed"] is True


def test_core_action_decision_applies_energy_soft_block_to_live_branch():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.68,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "energy_helper_v2": {
                "action_readiness": 0.34,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "suppression_or_forecast_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.72,
                },
                "metadata": {
                    "forecast_gap_usage_v1": {
                        "active": True,
                        "transition_confirm_fake_gap": 0.03,
                        "management_continue_fail_gap": -0.12,
                        "management_recover_reentry_gap": 0.09,
                        "hold_exit_gap": -0.08,
                        "same_side_flip_gap": -0.11,
                        "confidence_assist_active": False,
                        "soft_block_assist_active": True,
                        "priority_assist_active": False,
                        "wait_assist_active": True,
                        "usage_mode": "active_branch_assist",
                    },
                    "utility_hints": {
                        "priority_hint": "medium",
                        "gap_dominant_hint": "WAIT_CLEAR",
                        "forecast_branch_hint": "continue_fail_drag",
                    }
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=125.0,
        sell_s=25.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 0
    assert out["action"] is None
    assert out["core_reason"] == "energy_soft_block"
    assert out["blocked_by"] == "energy_soft_block"
    assert out["action_none_reason"] == "execution_soft_blocked"
    assert out["consumer_block_reason"] == "energy_soft_block"
    assert out["consumer_block_kind"] == "execution_block"
    assert out["consumer_block_source_layer"] == "energy_helper"
    assert out["consumer_block_is_execution"] is True
    assert out["consumer_guard_result"] == "EXECUTION_BLOCK"
    assert out["consumer_energy_action_readiness"] == 0.34
    assert out["consumer_energy_priority_hint"] == "high"
    assert out["consumer_energy_soft_block_active"] is True
    assert out["consumer_energy_soft_block_reason"] == "forecast_wait_bias"
    assert out["consumer_energy_soft_block_strength"] == 0.72
    assert out["consumer_check_display_ready"] is True
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_stage"] == "BLOCKED"
    assert out["consumer_archetype_id"] == "lower_hold_buy"


def test_core_action_decision_hides_lower_edge_breakdown_soft_block_buy_confirm_from_consumer_check_display():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        box_state="BELOW",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.67,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "energy_helper_v2": {
                "action_readiness": 0.36,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "suppression_or_forecast_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.70,
                },
                "metadata": {
                    "forecast_gap_usage_v1": {
                        "active": True,
                        "soft_block_assist_active": True,
                        "wait_assist_active": True,
                        "usage_mode": "active_branch_assist",
                    },
                    "utility_hints": {
                        "priority_hint": "medium",
                        "gap_dominant_hint": "WAIT_CLEAR",
                        "forecast_branch_hint": "continue_fail_drag",
                    },
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=124.0,
        sell_s=28.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_reason"] == "energy_soft_block"
    assert out["blocked_by"] == "energy_soft_block"
    assert out["action_none_reason"] == "execution_soft_blocked"
    assert out["consumer_check_candidate"] is True
    assert out["consumer_check_display_ready"] is False
    assert out["consumer_check_entry_ready"] is False
    assert out["consumer_check_stage"] == "BLOCKED"
    assert out["consumer_check_state_v1"]["blocked_display_reason"] == "energy_soft_block"


def test_core_action_decision_keeps_identity_while_using_layer_mode_and_energy_assists():
    svc = _svc()
    context = _core_context(
        symbol="NAS100",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_reject_confirm",
                "confidence": 0.67,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
            },
            "layer_mode_policy_v1": {
                "layer_modes": [{"layer": "Forecast", "mode": "assist"}],
                "effective_influences": [{"layer": "Forecast", "active_effects": ["priority_boost"]}],
                "suppressed_reasons": [],
                "confidence_adjustments": [{"layer": "Forecast", "mode": "assist", "delta": 0.05}],
                "hard_blocks": [],
                "mode_decision_trace": {"layers": [{"layer": "Forecast", "identity_preserved": True}]},
                "identity_preserved": True,
            },
            "energy_helper_v2": {
                "action_readiness": 0.71,
                "confidence_adjustment_hint": {
                    "direction": "increase",
                    "delta_band": "small_up",
                    "reason": "support_exceeds_suppression",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "barrier_soft_block",
                    "strength": 0.66,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "high",
                    }
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
                "layer_mode_policy_output_field": "layer_mode_policy_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=20.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["consumer_archetype_id"] == "upper_reject_sell"
    assert out["consumer_invalidation_id"] == "upper_break_reclaim"
    assert out["consumer_management_profile_id"] == "reversal_profile"
    assert out["consumer_layer_mode_priority_boost_active"] is True
    assert out["consumer_layer_mode_confidence_delta"] == 0.05
    assert out["consumer_energy_priority_hint"] == "high"
    assert out["consumer_energy_action_readiness"] == 0.71
    assert out["consumer_energy_soft_block_active"] is True
    assert out["consumer_energy_confidence_delta"] == 0.05
    assert out["core_score"] == 0.77


def test_core_action_decision_relaxes_energy_soft_block_for_clean_btc_upper_reject_confirm():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_reject_confirm",
                "confidence": 0.82,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.10,
                        "candidate_sell": 0.39,
                        "pair_gap": 0.29,
                        "winner_side": "SELL",
                        "winner_archetype": "upper_reject_sell",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                    "forecast_upper_reject_relief_v1": {
                        "applied": True,
                        "reason": "upper_reject_confirm",
                        "context_label": "UPPER_EDGE",
                    },
                },
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.25,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                        "wait_vs_enter_hint": "prefer_wait",
                    }
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.02,
                "sell_belief": 0.03,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.22,
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.02,
                    "p_sell_confirm": 0.19,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.11,
                    "p_fail_now": 0.27,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.17,
                    "wait_confirm_gap": -0.12,
                    "management_continue_fail_gap": -0.16,
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_range")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=9),
        buy_s=24.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["blocked_by"] == ""
    assert out["action_none_reason"] == ""
    assert out["confirm_energy_relief_applied"] is True
    assert out["consumer_energy_usage_trace_v1"]["usage_source"] == "recorded"
    assert [record["branch"] for record in out["consumer_energy_usage_trace_v1"]["branch_records"]] == [
        "soft_block_relief",
        "priority_rank_applied",
        "confidence_adjustment",
    ]


def test_core_action_decision_relaxes_energy_soft_block_for_btc_upper_break_fail_confirm():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="ABOVE",
        bb_state="BREAKOUT",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "SELL",
                "side": "SELL",
                "reason": "upper_break_fail_confirm",
                "confidence": 0.80,
                "archetype_id": "upper_reject_sell",
                "invalidation_id": "upper_break_reclaim",
                "management_profile_id": "reversal_profile",
                "metadata": {
                    "edge_pair_law_v1": {
                        "contract_version": "edge_pair_law_v1",
                        "context_label": "UPPER_EDGE",
                        "candidate_buy": 0.22,
                        "candidate_sell": 0.04,
                        "pair_gap": 0.18,
                        "winner_side": "BUY",
                        "winner_archetype": "upper_break_buy",
                        "winner_clear": True,
                        "active_branch_side": "SELL",
                        "active_branch_archetype": "upper_reject_sell",
                        "opposing_branch_side": "BUY",
                        "opposing_branch_archetype": "upper_break_buy",
                    },
                    "forecast_upper_reject_relief_v1": {
                        "applied": True,
                        "reason": "upper_break_fail_confirm",
                        "context_label": "UPPER_EDGE",
                    },
                },
            },
            "energy_helper_v2": {
                "action_readiness": 0.0,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "gap_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_gap_wait_bias",
                    "strength": 0.25,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "low",
                        "wait_vs_enter_hint": "prefer_wait",
                    }
                },
            },
            "belief_state_v1": {
                "dominant_side": "BALANCED",
                "dominant_mode": "balanced",
                "buy_belief": 0.02,
                "sell_belief": 0.03,
                "buy_persistence": 0.0,
                "sell_persistence": 0.0,
                "buy_streak": 0,
                "sell_streak": 0,
            },
            "barrier_state_v1": {
                "buy_barrier": 0.18,
                "sell_barrier": 0.22,
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.10,
                    "p_sell_confirm": 0.183,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.11,
                    "p_fail_now": 0.184,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": -0.20,
                    "wait_confirm_gap": -0.19,
                    "management_continue_fail_gap": 0.18,
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context, allowed_action="SELL_ONLY", approach_mode="PULLBACK_ONLY", reason="preflight_trend")

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=9),
        buy_s=24.0,
        sell_s=118.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "SELL"
    assert out["core_reason"] == "core_shadow_confirm_action"
    assert out["blocked_by"] == ""
    assert out["action_none_reason"] == ""
    assert out["confirm_energy_relief_applied"] is True


def test_core_action_decision_records_forecast_assist_trace_and_priority_boost():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.66,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "forecast_assist_v1": {
                        "present": True,
                        "decision_hint": "CONFIRM_FAVOR",
                        "confirm_fake_gap": 0.18,
                        "wait_confirm_gap": 0.11,
                        "continue_fail_gap": 0.14,
                        "target_side": "BUY",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.62,
                    "p_sell_confirm": 0.12,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.61,
                    "p_fail_now": 0.18,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.18,
                    "wait_confirm_gap": 0.11,
                    "management_continue_fail_gap": 0.14,
                },
            },
            "energy_helper_v2": {
                "action_readiness": 0.58,
                "confidence_adjustment_hint": {
                    "direction": "hold",
                    "delta_band": "",
                },
                "soft_block_hint": {
                    "active": False,
                    "reason": "",
                    "strength": 0.0,
                },
                "metadata": {
                    "utility_hints": {
                        "priority_hint": "medium",
                    }
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=8),
        buy_s=130.0,
        sell_s=18.0,
        has_buy=False,
        has_sell=False,
    )

    assert out["core_pass"] == 1
    assert out["action"] == "BUY"
    assert out["consumer_forecast_assist_active"] is True
    assert out["consumer_forecast_assist_source"] == "forecast_effective_policy_v1"
    assert out["consumer_forecast_mode"] == "assist"
    assert out["consumer_forecast_decision_hint"] == "CONFIRM_FAVOR"
    assert out["consumer_forecast_confirm_fake_gap"] == 0.18
    assert out["consumer_forecast_wait_confirm_gap"] == 0.11
    assert out["consumer_forecast_continue_fail_gap"] == 0.14
    assert out["consumer_forecast_priority_boost_active"] is True
    assert out["consumer_forecast_confidence_delta"] == 0.05
    assert out["consumer_energy_priority_hint"] == "high"
    assert out["core_score"] == 0.71


def test_core_action_decision_layer_mode_change_only_changes_decision_not_identity():
    svc = _svc()
    base_metadata = {
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "reason": "lower_rebound_confirm",
            "confidence": 0.74,
            "archetype_id": "lower_hold_buy",
            "invalidation_id": "lower_support_fail",
            "management_profile_id": "support_hold_profile",
        },
        "prs_log_contract_v2": {
            "canonical_observe_confirm_field": "observe_confirm_v2",
            "compatibility_observe_confirm_field": "observe_confirm_v1",
            "layer_mode_policy_output_field": "layer_mode_policy_v1",
        },
    }
    _bind_context(
        svc,
        context=_core_context(
            symbol="BTCUSD",
            box_state="LOWER",
            bb_state="LOWER_EDGE",
            metadata=base_metadata,
        ),
    )
    baseline = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=12),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    blocked_metadata = {
        **base_metadata,
        "layer_mode_policy_v1": {
            "layer_modes": [{"layer": "Barrier", "mode": "enforce"}],
            "effective_influences": [{"layer": "Barrier", "active_effects": ["hard_block"]}],
            "suppressed_reasons": [],
            "confidence_adjustments": [],
            "hard_blocks": [{"layer": "Barrier", "mode": "enforce", "effect": "hard_block"}],
            "mode_decision_trace": {"layers": [{"layer": "Barrier", "identity_preserved": True}]},
            "identity_preserved": True,
        },
    }
    _bind_context(
        svc,
        context=_core_context(
            symbol="BTCUSD",
            box_state="LOWER",
            bb_state="LOWER_EDGE",
            metadata=blocked_metadata,
        ),
    )
    blocked = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=12),
        buy_s=120.0,
        sell_s=30.0,
        has_buy=False,
        has_sell=False,
    )

    assert baseline["action"] == "BUY"
    assert blocked["action"] is None
    assert blocked["core_reason"] == "layer_mode_policy_hard_block"
    assert baseline["consumer_archetype_id"] == blocked["consumer_archetype_id"] == "lower_hold_buy"
    assert baseline["consumer_invalidation_id"] == blocked["consumer_invalidation_id"] == "lower_support_fail"
    assert baseline["consumer_management_profile_id"] == blocked["consumer_management_profile_id"] == "support_hold_profile"


def test_core_action_decision_energy_priority_hint_changes_soft_block_outcome_without_identity_mutation():
    svc = _svc()
    base_observe_confirm = {
        "state": "CONFIRM",
        "action": "SELL",
        "side": "SELL",
        "reason": "upper_reject_confirm",
        "confidence": 0.67,
        "archetype_id": "upper_reject_sell",
        "invalidation_id": "upper_break_reclaim",
        "management_profile_id": "reversal_profile",
    }
    common_energy_helper = {
        "action_readiness": 0.71,
        "confidence_adjustment_hint": {
            "direction": "increase",
            "delta_band": "small_up",
            "reason": "support_exceeds_suppression",
        },
        "soft_block_hint": {
            "active": True,
            "reason": "barrier_soft_block",
            "strength": 0.66,
        },
    }

    low_priority_context = _core_context(
        symbol="NAS100",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": dict(base_observe_confirm),
            "energy_helper_v2": {
                **common_energy_helper,
                "metadata": {"utility_hints": {"priority_hint": "low"}},
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(
        svc,
        context=low_priority_context,
        allowed_action="SELL_ONLY",
        approach_mode="PULLBACK_ONLY",
        reason="preflight_trend",
    )
    low_priority = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=20.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    high_priority_context = _core_context(
        symbol="NAS100",
        box_state="UPPER",
        bb_state="UPPER_EDGE",
        metadata={
            "observe_confirm_v2": dict(base_observe_confirm),
            "energy_helper_v2": {
                **common_energy_helper,
                "metadata": {"utility_hints": {"priority_hint": "high"}},
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(
        svc,
        context=high_priority_context,
        allowed_action="SELL_ONLY",
        approach_mode="PULLBACK_ONLY",
        reason="preflight_trend",
    )
    high_priority = svc._core_action_decision(
        symbol="NAS100",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=20.0,
        sell_s=120.0,
        has_buy=False,
        has_sell=False,
    )

    assert low_priority["action"] is None
    assert low_priority["core_reason"] == "energy_soft_block"
    assert low_priority["consumer_energy_priority_hint"] == "medium"
    assert high_priority["action"] == "SELL"
    assert high_priority["core_reason"] == "core_shadow_confirm_action"
    assert high_priority["consumer_energy_priority_hint"] == "high"
    assert low_priority["consumer_archetype_id"] == high_priority["consumer_archetype_id"] == "upper_reject_sell"
    assert low_priority["consumer_invalidation_id"] == high_priority["consumer_invalidation_id"] == "upper_break_reclaim"
    assert low_priority["consumer_management_profile_id"] == high_priority["consumer_management_profile_id"] == "reversal_profile"


def test_entry_decision_result_from_row_records_actual_consumed_fields_for_energy_soft_block_branch():
    svc = _svc()
    context = _core_context(
        symbol="XAUUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.68,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "energy_helper_v2": {
                "action_readiness": 0.34,
                "confidence_adjustment_hint": {
                    "direction": "decrease",
                    "delta_band": "small_down",
                    "reason": "suppression_or_forecast_drag",
                },
                "soft_block_hint": {
                    "active": True,
                    "reason": "forecast_wait_bias",
                    "strength": 0.72,
                },
                "metadata": {
                    "forecast_gap_usage_v1": {
                        "active": True,
                        "transition_confirm_fake_gap": 0.03,
                        "management_continue_fail_gap": -0.12,
                        "management_recover_reentry_gap": 0.09,
                        "hold_exit_gap": -0.08,
                        "same_side_flip_gap": -0.11,
                        "confidence_assist_active": False,
                        "soft_block_assist_active": True,
                        "priority_assist_active": False,
                        "wait_assist_active": True,
                        "usage_mode": "active_branch_assist",
                    },
                    "utility_hints": {
                        "priority_hint": "medium",
                        "gap_dominant_hint": "WAIT_CLEAR",
                        "forecast_branch_hint": "continue_fail_drag",
                    }
                },
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="XAUUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=10),
        buy_s=125.0,
        sell_s=25.0,
        has_buy=False,
        has_sell=False,
    )
    row = {
        **dict(context.metadata or {}),
        **out,
        "symbol": "XAUUSD",
        "entry_wait_state": "HELPER_SOFT_BLOCK",
        "entry_wait_reason": "energy_soft_block",
        "entry_wait_decision": "wait_soft_helper_block",
    }

    result = EntryService._entry_decision_result_from_row(row)
    metadata = result.context.metadata
    trace = result.context.metadata["energy_helper_v2"]["metadata"]["consumer_usage_trace"]

    assert trace["usage_source"] == "recorded"
    assert trace["usage_mode"] == "live_branch_applied"
    assert trace["consumed_fields"] == [
        "action_readiness",
        "soft_block_hint",
        "metadata.utility_hints.priority_hint",
        "confidence_adjustment_hint",
        "metadata.forecast_gap_usage_v1",
        "metadata.utility_hints.gap_dominant_hint",
        "metadata.utility_hints.forecast_branch_hint",
    ]
    assert [record["branch"] for record in trace["branch_records"]] == [
        "soft_block_block",
        "priority_rank_applied",
        "confidence_adjustment",
        "forecast_gap_live_gate",
    ]
    assert trace["block_reason"] == "energy_soft_block"
    assert trace["effective_action"] == "NONE"
    assert metadata["consumer_energy_forecast_gap_usage_active"] is True
    assert metadata["consumer_energy_forecast_gap_live_gate_used"] is True
    assert metadata["consumer_energy_gap_dominant_hint"] == "WAIT_CLEAR"
    assert metadata["consumer_energy_forecast_branch_hint"] == "continue_fail_drag"


def test_entry_decision_result_from_row_keeps_forecast_assist_trace():
    svc = _svc()
    context = _core_context(
        symbol="BTCUSD",
        box_state="LOWER",
        bb_state="LOWER_EDGE",
        metadata={
            "observe_confirm_v2": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_confirm",
                "confidence": 0.66,
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
                "metadata": {
                    "forecast_assist_v1": {
                        "present": True,
                        "decision_hint": "CONFIRM_FAVOR",
                        "confirm_fake_gap": 0.18,
                        "wait_confirm_gap": 0.11,
                        "continue_fail_gap": 0.14,
                        "target_side": "BUY",
                    }
                },
            },
            "forecast_effective_policy_v1": {
                "current_effective_mode": "assist",
                "transition_forecast_v1": {
                    "p_buy_confirm": 0.62,
                    "p_sell_confirm": 0.12,
                },
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.61,
                    "p_fail_now": 0.18,
                },
                "forecast_gap_metrics_v1": {
                    "transition_confirm_fake_gap": 0.18,
                    "wait_confirm_gap": 0.11,
                    "management_continue_fail_gap": 0.14,
                },
            },
            "energy_helper_v2": {
                "action_readiness": 0.58,
                "soft_block_hint": {"active": False, "reason": "", "strength": 0.0},
                "metadata": {"utility_hints": {"priority_hint": "medium"}},
            },
            "prs_log_contract_v2": {
                "canonical_observe_confirm_field": "observe_confirm_v2",
                "compatibility_observe_confirm_field": "observe_confirm_v1",
            },
        },
    )
    _bind_context(svc, context=context)

    out = svc._core_action_decision(
        symbol="BTCUSD",
        tick=SimpleNamespace(bid=100.0, ask=100.1),
        df_all={},
        scorer=None,
        result=_core_result(wait_score=8),
        buy_s=130.0,
        sell_s=18.0,
        has_buy=False,
        has_sell=False,
    )
    row = {
        **dict(context.metadata or {}),
        **out,
        "symbol": "BTCUSD",
        "entry_wait_state": "READY",
        "entry_wait_reason": "",
        "entry_wait_decision": "allow_entry",
    }

    result = EntryService._entry_decision_result_from_row(row)
    metadata = result.context.metadata

    assert metadata["consumer_forecast_assist_active"] is True
    assert metadata["consumer_forecast_assist_source"] == "forecast_effective_policy_v1"
    assert metadata["consumer_forecast_decision_hint"] == "CONFIRM_FAVOR"
    assert metadata["consumer_forecast_confirm_fake_gap"] == 0.18
    assert metadata["consumer_forecast_wait_confirm_gap"] == 0.11
    assert metadata["consumer_forecast_continue_fail_gap"] == 0.14
    assert metadata["consumer_forecast_priority_boost_active"] is True
    assert metadata["forecast_assist_v1"]["decision_hint"] == "CONFIRM_FAVOR"


def test_entry_decision_result_from_row_keeps_legacy_fields_as_bridge_only():
    result = EntryService._entry_decision_result_from_row(
        {
            "symbol": "BTCUSD",
            "action": "BUY",
            "observe_confirm_v1": {
                "state": "CONFIRM",
                "action": "BUY",
                "side": "BUY",
                "confidence": 0.71,
                "reason": "legacy_only_confirm",
                "archetype_id": "lower_hold_buy",
                "invalidation_id": "lower_support_fail",
                "management_profile_id": "support_hold_profile",
            },
            "prs_canonical_observe_confirm_field": "observe_confirm_v2",
            "prs_compatibility_observe_confirm_field": "observe_confirm_v1",
            "evidence_vector_effective_v1": {
                "buy_total_evidence": 0.84,
                "sell_total_evidence": 0.12,
                "buy_reversal_evidence": 0.74,
                "sell_reversal_evidence": 0.09,
                "buy_continuation_evidence": 0.38,
                "sell_continuation_evidence": 0.08,
            },
            "belief_state_effective_v1": {
                "buy_belief": 0.64,
                "sell_belief": 0.18,
                "buy_persistence": 0.55,
                "sell_persistence": 0.14,
            },
            "barrier_state_effective_v1": {
                "buy_barrier": 0.16,
                "sell_barrier": 0.42,
                "middle_chop_barrier": 0.10,
                "direction_policy_barrier": 0.05,
                "liquidity_barrier": 0.04,
            },
            "forecast_effective_policy_v1": {
                "transition_forecast_v1": {"p_buy_confirm": 0.73, "p_sell_confirm": 0.19},
                "trade_management_forecast_v1": {
                    "p_continue_favor": 0.59,
                    "p_fail_now": 0.21,
                    "p_recover_after_pullback": 0.28,
                },
                "forecast_gap_metrics_v1": {"transition_side_separation": 0.27},
            },
            "energy_snapshot": {
                "buy_force": 0.61,
                "sell_force": 0.19,
                "net_force": 0.42,
            },
        }
    )

    metadata = result.context.metadata

    assert metadata["consumer_migration_guard_v1"]["used_compatibility_fallback_v1"] is True
    assert metadata["consumer_migration_guard_v1"]["canonical_shadow_rebuild_active"] is True
    assert metadata["consumer_migration_guard_v1"]["compatibility_field_can_own_identity"] is False
    assert metadata["consumer_migration_guard_v1"]["identity_ownership_preserved"] is True
    assert metadata["energy_migration_guard_v1"]["compatibility_snapshot_present"] is True
    assert metadata["energy_migration_guard_v1"]["compatibility_bridge_rebuild_active"] is True
    assert metadata["energy_migration_guard_v1"]["legacy_identity_input_allowed"] is False
    assert metadata["energy_migration_guard_v1"]["legacy_live_gate_allowed"] is False
    assert metadata["energy_helper_v2"]["metadata"]["legacy_bridge"]["present"] is True


def _configure_overlay_entry_path(monkeypatch, tmp_path, *, mode: str):
    svc = _svc()
    tick = SimpleNamespace(bid=100.0, ask=100.1)
    df_all = {"15M": pd.DataFrame(), "1M": pd.DataFrame([{"close": 100.0}])}
    logged_rows: list[dict] = []
    sent_lots: list[float] = []
    overlay_path = tmp_path / "p7_overlay.json"
    overlay_path.write_text(
        json.dumps(
            {
                "report_version": "profitability_operations_p7_guarded_size_overlay_v1",
                "guarded_size_overlay_by_symbol": {
                    "BTCUSD": {
                        "symbol": "BTCUSD",
                        "scene_key": "BTCUSD",
                        "target_multiplier": 0.57,
                        "size_action": "reduce",
                        "health_state": "watch",
                        "coverage_state": "in_scope",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    svc.runtime.last_entry_time = {}
    svc.runtime.latest_signal_by_symbol = {"BTCUSD": {}}
    svc.runtime.get_lot_size = lambda _symbol: 0.10
    svc.runtime.entry_indicator_snapshot = lambda *_args, **_kwargs: {}
    svc.runtime.ai_runtime = None
    svc.runtime.semantic_shadow_runtime = None
    svc.runtime.semantic_shadow_runtime_diagnostics = {}
    svc.runtime.semantic_promotion_guard = SimpleNamespace(
        evaluate_entry_rollout=lambda **_: {
            "mode": "threshold_only",
            "fallback_reason": "baseline_no_action",
            "fallback_applied": True,
            "threshold_before": 1,
            "threshold_after": 1,
            "threshold_adjustment_points": 0,
            "threshold_applied": False,
            "partial_live_weight": 0.0,
            "partial_live_applied": False,
            "alert_active": False,
            "reason": "baseline_no_action",
            "symbol_allowed": True,
            "entry_stage_allowed": True,
        }
    )
    svc.runtime.get_order_block_status = lambda _symbol: {"active": False}

    def _capture_execute_order(_symbol, _action, lot):
        sent_lots.append(float(lot))
        return None

    svc.runtime.execute_order = _capture_execute_order

    monkeypatch.setattr(Config, "get_max_positions", staticmethod(lambda _symbol: 3))
    monkeypatch.setattr(Config, "ENTRY_COOLDOWN", 0)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_CHANNEL_BREAK_GUARD", False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_EDGE_DIRECTION_HARD_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_BB_GUARD", False, raising=False)
    monkeypatch.setattr(Config, "ENABLE_ENTRY_UTILITY_GATE", False, raising=False)
    monkeypatch.setattr(Config, "ENTRY_TOPDOWN_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENTRY_H1_GATE_MODE", "soft")
    monkeypatch.setattr(Config, "ENABLE_P7_GUARDED_SIZE_OVERLAY", True, raising=False)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MODE", mode, raising=False)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH", str(overlay_path), raising=False)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_MAX_STEP", 0.10, raising=False)
    monkeypatch.setattr(Config, "P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST", (), raising=False)
    monkeypatch.setattr(svc, "_append_entry_decision_log", lambda row: logged_rows.append(dict(row)) or dict(row))
    monkeypatch.setattr(svc, "_store_runtime_snapshot", lambda **kwargs: None)
    monkeypatch.setattr(svc, "_check_hard_no_trade_guard", lambda **_: "")
    monkeypatch.setattr(svc, "_regime_name", lambda _regime: "RANGE")
    monkeypatch.setattr(svc, "_zone_from_regime", lambda _regime: "UPPER")
    monkeypatch.setattr(svc, "_volatility_state_from_ratio", lambda _ratio: "NORMAL")

    _bind_context(
        svc,
        context=_core_context(
            symbol="BTCUSD",
            market_mode="RANGE",
            direction_policy="SELL_ONLY",
            box_state="UPPER",
            bb_state="UPPER_EDGE",
        ),
        allowed_action="SELL_ONLY",
        regime="RANGE",
    )
    svc._component_extractor = SimpleNamespace(
        extract=lambda **_: SimpleNamespace(
            entry_h1_context_score=14,
            entry_h1_context_opposite=0,
            entry_m1_trigger_score=11,
            entry_m1_trigger_opposite=0,
        )
    )
    svc._setup_detector = SimpleNamespace(
        detect_entry_setup=lambda **_: SimpleNamespace(
            setup_id="range_upper_reversal_sell",
            side="SELL",
            status="matched",
            trigger_state="CONFIRM",
            entry_quality=0.71,
            score=1.28,
            metadata={"reason": "unit_test"},
        )
    )
    svc._entry_predictor = SimpleNamespace(predict=lambda **_: {})
    svc._wait_predictor = SimpleNamespace(predict_entry_wait=lambda **_: {})
    svc._session_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            session_name="london",
            weekday=2,
            threshold_mult=1.0,
        )
    )
    svc._atr_policy = SimpleNamespace(
        get_threshold_mult=lambda **_: SimpleNamespace(
            atr_ratio=1.0,
            threshold_mult=1.0,
        )
    )
    svc._topdown_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="", align=1, conflict=0, seen=1)
    )
    svc._h1_gate_policy = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(ok=True, reason="")
    )
    monkeypatch.setattr(
        svc,
        "_core_action_decision",
        lambda **_: {
            "action": "SELL",
            "observe_reason": "upper_reject_confirm",
            "action_none_reason": "",
            "blocked_by": "",
            "core_pass": 1,
            "core_reason": "core_shadow_confirm_action",
            "core_allowed_action": "SELL",
            "h1_bias_strength": 0.6,
            "m1_trigger_strength": 0.5,
            "box_state": "UPPER",
            "bb_state": "UPPER_EDGE",
            "core_score": 1.9,
            "core_buy_raw": 0.1,
            "core_sell_raw": 1.9,
            "core_best_raw": 1.9,
            "core_min_raw": 0.1,
            "core_margin_raw": 1.8,
            "core_tie_band_raw": 0.1,
            "wait_score": 0.0,
            "wait_conflict": 0.0,
            "wait_noise": 0.0,
            "wait_penalty": 0.0,
            "learn_buy_penalty": 0.0,
            "learn_sell_penalty": 0.0,
            "preflight_regime": "RANGE",
            "preflight_liquidity": "GOOD",
            "preflight_allowed_action": "SELL_ONLY",
            "preflight_approach_mode": "MIX",
            "preflight_reason": "unit_test",
            "preflight_direction_penalty_applied": 0.0,
            "consumer_layer_mode_hard_block_active": False,
            "consumer_layer_mode_suppressed": False,
            "consumer_policy_live_gate_applied": False,
            "consumer_policy_block_layer": "",
            "consumer_policy_block_effect": "",
            "consumer_energy_action_readiness": 0.0,
            "consumer_energy_wait_vs_enter_hint": "",
            "consumer_energy_soft_block_active": False,
            "consumer_energy_soft_block_reason": "",
            "consumer_energy_soft_block_strength": 0.0,
            "consumer_energy_live_gate_applied": False,
            "consumer_archetype_id": "upper_reject_sell",
            "consumer_invalidation_id": "upper_break_fail",
            "consumer_management_profile_id": "upper_reject_profile",
            "entry_default_side_gate_v1": {},
            "entry_probe_plan_v1": {},
            "compatibility_mode": "native_v2",
            "consumer_check_candidate": False,
            "consumer_check_display_ready": False,
            "consumer_check_entry_ready": False,
            "consumer_check_side": "",
            "consumer_check_stage": "",
            "consumer_check_reason": "upper_reject_confirm",
            "consumer_check_display_strength_level": 0,
            "consumer_check_state_v1": {
                "contract_version": "consumer_check_state_v1",
                "check_candidate": False,
                "check_display_ready": False,
                "entry_ready": False,
                "check_side": "",
                "check_stage": "",
                "check_reason": "upper_reject_confirm",
                "entry_block_reason": "",
                "display_strength_level": 0,
            },
        },
    )
    return svc, tick, df_all, logged_rows, sent_lots


def test_try_open_entry_p7_size_overlay_dry_run_keeps_original_lot(monkeypatch, tmp_path):
    svc, tick, df_all, logged_rows, sent_lots = _configure_overlay_entry_path(
        monkeypatch,
        tmp_path,
        mode="dry_run",
    )

    helper_try_open_entry(
        svc,
        symbol="BTCUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=0.2,
        sell_s=1.4,
        entry_threshold=1.0,
    )

    assert sent_lots == [0.1]
    assert logged_rows
    overlay = logged_rows[-1]["p7_guarded_size_overlay_v1"]
    assert overlay["matched"] is True
    assert overlay["gate_reason"] == "dry_run_only"
    assert overlay["apply_allowed"] is False


def test_try_open_entry_p7_size_overlay_apply_reduces_lot_by_guarded_step(monkeypatch, tmp_path):
    svc, tick, df_all, logged_rows, sent_lots = _configure_overlay_entry_path(
        monkeypatch,
        tmp_path,
        mode="apply",
    )

    helper_try_open_entry(
        svc,
        symbol="BTCUSD",
        tick=tick,
        df_all=df_all,
        result={},
        my_positions=[],
        pos_count=0,
        scorer=_DummyScorer(),
        buy_s=0.2,
        sell_s=1.4,
        entry_threshold=1.0,
    )

    assert sent_lots == [0.09]
    assert logged_rows
    overlay = logged_rows[-1]["p7_guarded_size_overlay_v1"]
    assert overlay["matched"] is True
    assert overlay["apply_allowed"] is True
    assert overlay["applied"] is True
    assert overlay["effective_lot"] == 0.09
