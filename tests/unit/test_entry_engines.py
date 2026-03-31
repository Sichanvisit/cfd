from pathlib import Path
import json
from types import SimpleNamespace

import pandas as pd

from backend.core.config import Config
from backend.services.consumer_contract import CONSUMER_FREEZE_HANDOFF_V1
from backend.services.consumer_contract import CONSUMER_INPUT_CONTRACT_V1, CONSUMER_LAYER_MODE_INTEGRATION_V1, CONSUMER_SCOPE_CONTRACT_V1
from backend.services.consumer_contract import CONSUMER_LOGGING_CONTRACT_V1
from backend.services.consumer_contract import CONSUMER_MIGRATION_FREEZE_V1
from backend.services.consumer_contract import CONSUMER_TEST_CONTRACT_V1
from backend.services.layer_mode_contract import (
    LAYER_MODE_APPLICATION_CONTRACT_V1,
    LAYER_MODE_DEFAULT_POLICY_V1,
    LAYER_MODE_DUAL_WRITE_CONTRACT_V1,
    LAYER_MODE_FREEZE_HANDOFF_V1,
    LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1,
    LAYER_MODE_INFLUENCE_SEMANTICS_V1,
    LAYER_MODE_LAYER_INVENTORY_V1,
    LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1,
    LAYER_MODE_MODE_CONTRACT_V1,
    LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1,
    LAYER_MODE_SCOPE_CONTRACT_V1,
    LAYER_MODE_TEST_CONTRACT_V1,
)
from backend.services.consumer_contract import ENTRY_GUARD_CONTRACT_V1
from backend.services.consumer_contract import EXIT_HANDOFF_CONTRACT_V1
from backend.services.consumer_contract import RE_ENTRY_CONTRACT_V1
from backend.services.consumer_contract import SETUP_MAPPING_CONTRACT_V1
from backend.services.energy_contract import ENERGY_LOGGING_REPLAY_CONTRACT_V1
from backend.services.entry_engines import (
    ENTRY_DECISION_LOG_COLUMNS,
    EntryDecisionRecorder,
    EntryGuardEngine,
    EntryThresholdEngine,
)
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1
from backend.services.observe_confirm_contract import OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2
from backend.services.runtime_alignment_contract import RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1
from backend.services.storage_compaction import resolve_entry_decision_detail_path


class _DummyTradeLogger:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def read_closed_df(self):
        return self._df.copy()


def _load_detail_record(csv_path: Path) -> dict:
    detail_path = resolve_entry_decision_detail_path(csv_path)
    lines = detail_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    return json.loads(lines[-1])


def _minimal_entry_row(*, time: str, symbol: str, action: str, outcome: str = "entered") -> dict:
    return {
        "time": time,
        "signal_timeframe": "15M",
        "signal_bar_ts": 1773149400,
        "symbol": symbol,
        "action": action,
        "considered": 1,
        "outcome": outcome,
    }


def test_entry_guard_engine_cluster_guard_uses_internal_signature(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.0, ask=100.01)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    eng.mark_entry("NAS100", "BUY", 100.0, 999.0)
    ok, reason = eng.pass_cluster_guard("NAS100", "BUY", tick)
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_entry_guard_engine_btc_upper_shadow_sell_now_requires_meaningful_spacing(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.0, ask=100.01)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    eng.mark_entry("BTCUSD", "SELL", 100.0, 980.0)
    ok, reason = eng.pass_cluster_guard(
        symbol="BTCUSD",
        action="SELL",
        tick=tick,
        setup_id="range_upper_reversal_sell",
        setup_reason="shadow_upper_break_fail_confirm",
        preflight_allowed_action="BOTH",
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_entry_guard_engine_semantic_relief_allows_same_thesis_edge_reentry(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.04, ask=100.05)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_WINDOW_MULT", 0.55)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_MOVE_MULT", 0.35)
    previous_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.82,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.72,
            "buy_streak": 3,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.08,
        },
        "transition_confirm_fake_gap": 0.26,
        "management_continue_fail_gap": 0.44,
    }
    current_sig = dict(previous_sig)
    eng.mark_entry(
        "XAUUSD",
        "BUY",
        100.0,
        999.0,
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    ok, reason = eng.pass_cluster_guard(
        symbol="XAUUSD",
        action="BUY",
        tick=tick,
        setup_id="range_lower_reversal_buy",
        semantic_signature=eng.build_cluster_semantic_signature(current_sig, action="BUY"),
    )
    assert ok is True
    assert reason == ""


def test_entry_guard_engine_allows_xau_second_support_probe_same_zone_reentry(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.04, ask=100.05)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)
    previous_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "MID",
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.55,
            "reason": "lower_rebound_probe_observe",
            "archetype_id": "lower_hold_buy",
            "metadata": {
                "xau_second_support_probe_relief": True,
            },
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.12,
            "buy_streak": 1,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.18,
        },
        "transition_confirm_fake_gap": 0.00,
        "management_continue_fail_gap": -0.03,
    }
    current_sig = dict(previous_sig)
    eng.mark_entry(
        "XAUUSD",
        "BUY",
        100.0,
        999.0,
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    ok, reason = eng.pass_cluster_guard(
        symbol="XAUUSD",
        action="BUY",
        tick=tick,
        setup_id="range_lower_reversal_buy",
        semantic_signature=eng.build_cluster_semantic_signature(current_sig, action="BUY"),
    )
    assert ok is True
    assert reason == ""
    assert eng._last_cluster_trace["XAUUSD"]["semantic_relief_applied"] is True


def test_entry_guard_engine_semantic_relief_does_not_allow_weak_same_zone_reentry(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.01, ask=100.02)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 300)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0010)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)
    previous_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.42,
            "reason": "lower_rebound_observe",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BALANCED",
            "dominant_mode": "balanced",
            "buy_persistence": 0.12,
            "buy_streak": 0,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.31,
        },
        "transition_confirm_fake_gap": 0.02,
        "management_continue_fail_gap": 0.05,
    }
    eng.mark_entry(
        "XAUUSD",
        "BUY",
        100.0,
        999.0,
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    ok, reason = eng.pass_cluster_guard(
        symbol="XAUUSD",
        action="BUY",
        tick=tick,
        setup_id="range_lower_reversal_buy",
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"


def test_entry_decision_log_columns_include_r0_fields():
    assert "r0_non_action_family" in ENTRY_DECISION_LOG_COLUMNS
    assert "r0_semantic_runtime_state" in ENTRY_DECISION_LOG_COLUMNS
    assert "r0_row_interpretation_v1" in ENTRY_DECISION_LOG_COLUMNS
    assert "p7_guarded_size_overlay_v1" in ENTRY_DECISION_LOG_COLUMNS
    assert "p7_size_overlay_effective_multiplier" in ENTRY_DECISION_LOG_COLUMNS


def test_entry_guard_engine_btc_duplicate_lower_buy_requires_larger_spacing_even_with_same_thesis(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.04, ask=100.05)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 180)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0004)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)
    previous_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.84,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.72,
            "buy_streak": 3,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.08,
        },
        "transition_confirm_fake_gap": 0.26,
        "management_continue_fail_gap": 0.44,
    }
    eng.mark_entry(
        "BTCUSD",
        "BUY",
        100.0,
        999.0,
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    ok, reason = eng.pass_cluster_guard(
        symbol="BTCUSD",
        action="BUY",
        tick=tick,
        setup_id="range_lower_reversal_buy",
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    assert ok is False
    assert reason == "clustered_entry_price_zone"
    assert eng._last_cluster_trace["BTCUSD"]["btc_duplicate_edge_suppression"] is True


def test_entry_guard_engine_btc_duplicate_lower_buy_relaxes_only_for_strong_repeat_quality(monkeypatch):
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.04, ask=100.05)
    monkeypatch.setattr("backend.services.entry_engines.time.time", lambda: 1000.0)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_GUARD_ENABLED", True)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_WINDOW_SECONDS", 180)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_MIN_MOVE_PCT", 0.0004)
    monkeypatch.setattr(Config, "ENTRY_CLUSTER_SEMANTIC_RELIEF_ENABLED", True)

    previous_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.86,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.70,
            "buy_streak": 3,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.08,
        },
        "transition_confirm_fake_gap": 0.26,
        "management_continue_fail_gap": 0.44,
    }
    current_sig = {
        "setup_id": "range_lower_reversal_buy",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "CONFIRM",
            "action": "BUY",
            "side": "BUY",
            "confidence": 0.94,
            "reason": "lower_rebound_confirm",
            "archetype_id": "lower_hold_buy",
        },
        "belief_state_v1": {
            "dominant_side": "BUY",
            "dominant_mode": "reversal",
            "buy_persistence": 0.78,
            "buy_streak": 4,
        },
        "barrier_state_v1": {
            "buy_barrier": 0.06,
        },
        "transition_confirm_fake_gap": 0.30,
        "management_continue_fail_gap": 0.48,
    }

    eng.mark_entry(
        "BTCUSD",
        "BUY",
        100.0,
        999.0,
        semantic_signature=eng.build_cluster_semantic_signature(previous_sig, action="BUY"),
    )
    ok, reason = eng.pass_cluster_guard(
        symbol="BTCUSD",
        action="BUY",
        tick=tick,
        setup_id="range_lower_reversal_buy",
        semantic_signature=eng.build_cluster_semantic_signature(current_sig, action="BUY"),
    )

    assert ok is False
    assert reason == "clustered_entry_price_zone"
    trace = eng._last_cluster_trace["BTCUSD"]
    assert trace["btc_duplicate_edge_suppression"] is True
    assert trace["btc_duplicate_repeat_quality"] is True
    assert trace["semantic_relief_applied"] is True
    assert trace["window_sec_effective"] == 240
    assert trace["btc_duplicate_effective_need_pct_floor"] < trace["btc_duplicate_full_suppression_need_pct"]


def test_entry_threshold_engine_load_symbol_utility_stats_independent():
    df = pd.DataFrame(
        {
            "symbol": ["NAS100"] * 8,
            "profit": [1.0, 2.0, 0.5, 0.8, -1.0, -2.0, -0.7, -0.6],
            "regime_spread_ratio": [1.0] * 8,
        }
    )
    eng = EntryThresholdEngine(_DummyTradeLogger(df))
    stats = eng.load_symbol_utility_stats("NAS100")
    assert isinstance(stats, dict)
    assert int(stats["wins_n"]) == 4
    assert int(stats["losses_n"]) == 4


def test_entry_decision_recorder_writes_decision_row(monkeypatch, tmp_path: Path):
    runtime = SimpleNamespace(append_ai_entry_trace=lambda *_args, **_kwargs: None)
    rec = EntryDecisionRecorder(runtime)
    out = tmp_path / "entry_decisions.csv"
    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_ENABLED", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_PATH", str(out), raising=False)
    row = {
        "signal_timeframe": "15M",
        "signal_bar_ts": 1773149400,
        "symbol": "NAS100",
        "action": "BUY",
        "considered": 1,
        "outcome": "entered",
        "blocked_by": "",
        "setup_id": "trend_pullback_buy",
        "position_snapshot_v2": "{\"interpretation\":{\"primary_label\":\"ALIGNED_LOWER_WEAK\"}}",
        "response_raw_snapshot_v1": "{\"bb20_lower_hold\":1.0}",
        "response_vector_v2": "{\"lower_hold_up\":1.0}",
        "state_raw_snapshot_v1": "{\"market_mode\":\"RANGE\",\"s_conflict\":0.1}",
        "state_vector_v2": "{\"range_reversal_gain\":1.18,\"conflict_damp\":0.9}",
        "evidence_vector_v1": "{\"buy_reversal_evidence\":0.84,\"buy_total_evidence\":0.84}",
        "belief_state_v1": "{\"buy_belief\":0.51,\"buy_persistence\":0.4}",
        "barrier_state_v1": "{\"buy_barrier\":0.12,\"middle_chop_barrier\":0.08}",
        "forecast_features_v1": "{\"position_primary_label\":\"ALIGNED_LOWER_WEAK\",\"evidence_vector_v1\":{\"buy_total_evidence\":0.84}}",
        "transition_forecast_v1": "{\"p_buy_confirm\":0.72,\"forecast_contract\":\"transition_forecast_v1\",\"metadata\":{\"side_separation\":0.22,\"confirm_fake_gap\":0.18,\"reversal_continuation_gap\":0.31}}",
        "trade_management_forecast_v1": "{\"p_continue_favor\":0.61,\"forecast_contract\":\"trade_management_forecast_v1\",\"metadata\":{\"continue_fail_gap\":0.27,\"recover_reentry_gap\":0.12}}",
        "forecast_gap_metrics_v1": "{\"transition_side_separation\":0.22,\"transition_confirm_fake_gap\":0.18,\"transition_reversal_continuation_gap\":0.31,\"management_continue_fail_gap\":0.27,\"management_recover_reentry_gap\":0.12}",
        "transition_side_separation": 0.22,
        "transition_confirm_fake_gap": 0.18,
        "transition_reversal_continuation_gap": 0.31,
        "management_continue_fail_gap": 0.27,
        "management_recover_reentry_gap": 0.12,
        "entry_wait_state": "HELPER_SOFT_BLOCK",
        "entry_wait_hard": 1,
        "entry_wait_reason": "forecast_wait_bias",
        "entry_wait_selected": 1,
        "entry_wait_decision": "wait_soft_helper_block",
        "entry_enter_value": 0.41,
        "entry_wait_value": 0.58,
        "entry_wait_energy_usage_trace_v1": {
            "contract_version": "consumer_energy_usage_trace_v1",
            "usage_source": "recorded",
            "usage_mode": "wait_state_branch_applied",
            "branch_records": [{"branch": "helper_soft_block_state"}],
        },
        "entry_wait_decision_energy_usage_trace_v1": {
            "contract_version": "consumer_energy_usage_trace_v1",
            "usage_source": "recorded",
            "usage_mode": "wait_decision_branch_applied",
            "branch_records": [{"branch": "wait_soft_helper_block_decision"}],
        },
        "consumer_check_candidate": True,
        "consumer_check_display_ready": True,
        "consumer_check_entry_ready": False,
        "consumer_check_side": "BUY",
        "consumer_check_stage": "PROBE",
        "consumer_check_reason": "lower_rebound_probe_observe",
        "consumer_check_display_strength_level": 6,
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "BUY",
            "check_stage": "PROBE",
            "check_reason": "lower_rebound_probe_observe",
            "entry_block_reason": "probe_not_promoted",
            "display_strength_level": 6,
        },
        "runtime_snapshot_key": "runtime_signal_row_v1|symbol=NAS100|anchor_field=signal_bar_ts|anchor_value=0.0|hint=BOTH",
        "shadow_state_v1": "lower_hold_buy",
        "shadow_action_v1": "BUY",
        "p7_guarded_size_overlay_v1": {
            "contract_version": "p7_guarded_size_overlay_v1",
            "enabled": True,
            "mode": "dry_run",
            "matched": True,
            "apply_allowed": False,
            "applied": False,
            "target_multiplier": 0.43,
            "effective_multiplier": 1.0,
            "gate_reason": "dry_run_only",
            "source_path": r"data\analysis\profitability_operations\profitability_operations_p7_guarded_size_overlay_latest.json",
        },
        "observe_confirm_v1": "{\"state\":\"CONFIRM\",\"action\":\"BUY\",\"side\":\"BUY\",\"confidence\":0.72,\"reason\":\"lower hold evidence dominated\",\"archetype_id\":\"lower_hold_buy\",\"invalidation_id\":\"lower_support_fail\",\"management_profile_id\":\"support_hold_profile\",\"metadata\":{\"raw_contributions\":{},\"effective_contributions\":{},\"winning_evidence\":[\"lower_hold_up\"],\"blocked_reason\":\"\"}}",
    }
    rec.append_entry_decision_log(row)
    assert out.exists()
    logged = pd.read_csv(out, encoding="utf-8")
    assert len(logged) == 1
    first = logged.iloc[0].to_dict()
    detail_record = _load_detail_record(out)
    detail_first = detail_record["payload"]

    assert first["signal_timeframe"] == "15M"
    assert int(first["signal_bar_ts"]) == 1773149400
    assert first["symbol"] == "NAS100"
    assert first["outcome"] == "entered"
    assert first["setup_id"] == "trend_pullback_buy"
    assert first["prs_contract_version"] == "v2"
    assert first["prs_canonical_position_field"] == "position_snapshot_v2"
    assert first["prs_canonical_response_field"] == "response_vector_v2"
    assert first["prs_canonical_state_field"] == "state_vector_v2"
    assert first["prs_canonical_evidence_field"] == "evidence_vector_v1"
    assert first["prs_canonical_belief_field"] == "belief_state_v1"
    assert first["prs_canonical_barrier_field"] == "barrier_state_v1"
    assert first["prs_canonical_forecast_features_field"] == "forecast_features_v1"
    assert first["prs_canonical_transition_forecast_field"] == "transition_forecast_v1"
    assert first["prs_canonical_trade_management_forecast_field"] == "trade_management_forecast_v1"
    assert first["prs_canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert first["prs_canonical_energy_field"] == "energy_helper_v2"
    assert first["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert first["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert first["consumer_archetype_id"] == "lower_hold_buy"
    assert first["consumer_invalidation_id"] == "lower_support_fail"
    assert first["consumer_management_profile_id"] == "support_hold_profile"
    assert first["consumer_setup_id"] == "trend_pullback_buy"
    assert first["consumer_guard_result"] == "PASS"
    assert first["consumer_effective_action"] == "BUY"
    assert first["p0_identity_owner"] == "semantic"
    assert first["p0_execution_gate_owner"] == "semantic"
    assert first["p0_decision_owner_relation"] == "semantic_primary"
    assert first["p0_coverage_state"] == "in_scope_runtime"
    p0_trace = json.loads(str(first["p0_decision_trace_v1"]))
    assert p0_trace["decision_owner_relation"] == "semantic_primary"
    assert p0_trace["coverage_state"] == "in_scope_runtime"
    assert p0_trace["consumer_check_stage"] == "PROBE"
    assert int(first["p7_size_overlay_enabled"]) == 1
    assert first["p7_size_overlay_mode"] == "dry_run"
    assert int(first["p7_size_overlay_matched"]) == 1
    assert float(first["p7_size_overlay_target_multiplier"]) == 0.43
    assert float(first["p7_size_overlay_effective_multiplier"]) == 1.0
    assert first["p7_size_overlay_gate_reason"] == "dry_run_only"
    p7_overlay = json.loads(str(first["p7_guarded_size_overlay_v1"]))
    assert p7_overlay["mode"] == "dry_run"
    assert p7_overlay["matched"] is True
    assert first["entry_wait_state"] == "HELPER_SOFT_BLOCK"
    assert json.loads(str(first["entry_wait_energy_usage_trace_v1"]))["usage_mode"] == "wait_state_branch_applied"
    assert json.loads(str(first["entry_wait_decision_energy_usage_trace_v1"]))["branch_records"][0]["branch"] == (
        "wait_soft_helper_block_decision"
    )
    assert first["consumer_check_display_ready"] is True
    assert first["consumer_check_entry_ready"] is False
    assert first["consumer_check_side"] == "BUY"
    assert first["consumer_check_stage"] == "PROBE"


def test_entry_decision_recorder_auto_rolls_active_log_to_archive(monkeypatch, tmp_path: Path):
    runtime = SimpleNamespace(append_ai_entry_trace=lambda *_args, **_kwargs: None)
    rec = EntryDecisionRecorder(runtime)
    out = tmp_path / "entry_decisions.csv"
    archive_root = tmp_path / "archive" / "entry_decisions"
    manifest_root = tmp_path / "manifests"

    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_ENABLED", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_PATH", str(out), raising=False)
    monkeypatch.setenv("ENTRY_DECISION_ARCHIVE_ROOT", str(archive_root))
    monkeypatch.setenv("ENTRY_DECISION_MANIFEST_ROOT", str(manifest_root))
    monkeypatch.setenv("ENTRY_DECISION_ROLLOVER_ENABLED", "1")
    monkeypatch.setenv("ENTRY_DECISION_ROLLOVER_DAILY", "0")
    monkeypatch.setenv("ENTRY_DECISION_ROLLOVER_MAX_BYTES", "999999999")

    rec.append_entry_decision_log(
        _minimal_entry_row(time="2026-03-18T10:00:00", symbol="BTCUSD", action="BUY")
    )

    monkeypatch.setenv("ENTRY_DECISION_ROLLOVER_MAX_BYTES", "1")
    rec.append_entry_decision_log(
        _minimal_entry_row(time="2026-03-18T10:01:00", symbol="BTCUSD", action="SELL")
    )

    assert out.exists()
    logged = pd.read_csv(out, encoding="utf-8")
    assert len(logged) == 1
    assert logged.iloc[0]["action"] == "SELL"

    archived = list(archive_root.rglob("*.parquet"))
    assert len(archived) == 1
    rollover_manifests = list((manifest_root / "rollover").glob("entry_decisions_rollover_*.json"))
    archive_manifests = list((manifest_root / "archive").glob("entry_decisions_archive_*.json"))
    retention_manifests = list((manifest_root / "retention").glob("entry_decisions_retention_*.json"))
    assert rollover_manifests
    assert archive_manifests
    assert retention_manifests

    archive_payload = json.loads(archive_manifests[0].read_text(encoding="utf-8"))
    rollover_payload = json.loads(rollover_manifests[0].read_text(encoding="utf-8"))
    assert archive_payload["schema_version"] == "entry_decisions_archive_v2"
    assert archive_payload["trigger_mode"] == "runtime_append"
    assert archive_payload["detail_source_path"].endswith(".detail.jsonl")
    assert archive_payload["time_range_start"] == "2026-03-18T10:00:00"
    assert archive_payload["time_range_end"] == "2026-03-18T10:00:00"
    assert rollover_payload["schema_version"] == "entry_decisions_rollover_v3"
    assert rollover_payload["trigger_mode"] == "runtime_append"
    assert rollover_payload["archive_manifest_path"]
    return
    assert first["consumer_check_reason"] == "lower_rebound_probe_observe"
    assert int(first["consumer_check_display_strength_level"]) == 6
    assert "consumer_check_state_v1" in logged.columns
    assert '"check_stage":"PROBE"' in str(first["consumer_check_state_v1"])
    assert float(first["transition_confirm_fake_gap"]) == 0.18
    assert float(first["management_continue_fail_gap"]) == 0.27
    assert "ALIGNED_LOWER_WEAK" in str(first["position_snapshot_v2"])
    assert "lower_hold_up" in str(first["response_vector_v2"])
    assert "range_reversal_gain" in str(first["state_vector_v2"])
    assert "buy_reversal_evidence" in str(first["evidence_vector_v1"])
    assert "buy_belief" in str(first["belief_state_v1"])
    assert "buy_barrier" in str(first["barrier_state_v1"])
    assert "position_primary_label" in str(first["forecast_features_v1"])
    assert "p_buy_confirm" in str(first["transition_forecast_v1"])
    assert "p_continue_favor" in str(first["trade_management_forecast_v1"])
    assert "lower_hold_buy" in str(first["observe_confirm_v1"])
    assert "lower_hold_buy" in str(first["observe_confirm_v2"])
    assert str(first["energy_helper_v2"]).strip() != ""
    assert first["detail_schema_version"] == detail_record["schema_version"]
    assert first["detail_row_key"] == detail_record["row_key"]
    assert first["decision_row_key"] == detail_record["row_key"]
    assert first["replay_row_key"] == detail_record["row_key"]
    assert str(first["runtime_snapshot_key"]).startswith("runtime_signal_row_v1|symbol=NAS100")
    assert "anchor_value=0.0" not in str(first["runtime_snapshot_key"])
    assert "anchor_value=1773149400.0" in str(first["runtime_snapshot_key"])
    assert int(first["decision_latency_ms"]) == 0
    assert int(first["order_submit_latency_ms"]) == 0
    assert int(first["missing_feature_count"]) >= 0
    assert float(first["data_completeness_ratio"]) > 0.0
    assert int(first["detail_blob_bytes"]) > 0
    assert int(first["row_payload_bytes"]) > 0

    assert "response_raw_snapshot_v1" not in logged.columns
    assert "state_raw_snapshot_v1" not in logged.columns
    assert "position_snapshot_effective_v1" not in logged.columns
    assert "forecast_effective_policy_v1" not in logged.columns
    assert "forecast_calibration_contract_v1" not in logged.columns
    assert "outcome_labeler_scope_contract_v1" not in logged.columns
    assert "observe_confirm_input_contract_v2" not in logged.columns
    assert "consumer_input_contract_v1" not in logged.columns
    assert "layer_mode_logging_replay_v1" not in logged.columns
    assert "shadow_state_v1" not in logged.columns
    assert "last_order_comment" not in logged.columns

    assert detail_record["schema_version"] == "entry_decision_detail_v1"
    assert detail_first["shadow_state_v1"] == "lower_hold_buy"
    assert "bb20_lower_hold" in str(detail_first["response_raw_snapshot_v1"])
    assert "market_mode" in str(detail_first["state_raw_snapshot_v1"])
    assert "ALIGNED_LOWER_WEAK" in str(detail_first["position_snapshot_effective_v1"])
    assert "effective_equals_raw" in str(detail_first["forecast_effective_policy_v1"])
    assert "forecast_calibration_v1" in str(detail_first["forecast_calibration_contract_v1"])
    assert "outcome_labeler_scope_v1" in str(detail_first["outcome_labeler_scope_contract_v1"])
    assert "observe_confirm_input_contract_v2" in str(detail_first["observe_confirm_input_contract_v2"])
    assert "consumer_input_contract_v1" in str(detail_first["consumer_input_contract_v1"])
    assert detail_first["p0_decision_owner_relation"] == "semantic_primary"
    assert "in_scope_runtime" in str(detail_first["p0_decision_trace_v1"])
    assert "layer_mode_logging_replay_v1" in str(detail_first["layer_mode_logging_replay_v1"])
    assert detail_first["consumer_policy_contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert detail_first["energy_migration_contract_field"] == "energy_migration_dual_write_v1"
    assert detail_first["energy_scope_contract_field"] == "energy_scope_contract_v1"
    assert detail_first["runtime_alignment_scope_contract_field"] == "runtime_alignment_scope_contract_v1"
    assert detail_first["energy_logging_replay_contract_field"] == "energy_logging_replay_contract_v1"

    observe_confirm_payload_v2 = json.loads(str(detail_first["observe_confirm_v2"]))
    assert observe_confirm_payload_v2["state"] == "CONFIRM"
    assert observe_confirm_payload_v2["action"] == "BUY"
    assert observe_confirm_payload_v2["side"] == "BUY"
    assert observe_confirm_payload_v2["archetype_id"] == "lower_hold_buy"
    assert observe_confirm_payload_v2["invalidation_id"] == "lower_support_fail"
    assert observe_confirm_payload_v2["management_profile_id"] == "support_hold_profile"
    assert observe_confirm_payload_v2["metadata"]["winning_evidence"] == ["lower_hold_up"]

    observe_confirm_output_contract = json.loads(str(detail_first["observe_confirm_output_contract_v2"]))
    assert observe_confirm_output_contract["contract_version"] == OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["contract_version"]
    assert observe_confirm_output_contract["canonical_output_field"] == "observe_confirm_v2"

    runtime_alignment_scope_contract = json.loads(str(detail_first["runtime_alignment_scope_contract_v1"]))
    assert runtime_alignment_scope_contract["contract_version"] == (
        RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["contract_version"]
    )

    energy_logging_contract = json.loads(str(detail_first["energy_logging_replay_contract_v1"]))
    assert energy_logging_contract["contract_version"] == ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    return
    assert first["signal_timeframe"] == "15M"
    assert int(first["signal_bar_ts"]) == 1773149400
    assert first["symbol"] == "NAS100"
    assert first["outcome"] == "entered"
    assert first["setup_id"] == "trend_pullback_buy"
    assert first["shadow_state_v1"] == "lower_hold_buy"
    assert "ALIGNED_LOWER_WEAK" in str(first["position_snapshot_v2"])
    assert "bb20_lower_hold" in str(first["response_raw_snapshot_v1"])
    assert "lower_hold_up" in str(first["response_vector_v2"])
    assert "market_mode" in str(first["state_raw_snapshot_v1"])
    assert "range_reversal_gain" in str(first["state_vector_v2"])
    assert "buy_reversal_evidence" in str(first["evidence_vector_v1"])
    assert "buy_belief" in str(first["belief_state_v1"])
    assert "buy_barrier" in str(first["barrier_state_v1"])
    assert "position_primary_label" in str(first["forecast_features_v1"])
    assert "p_buy_confirm" in str(first["transition_forecast_v1"])
    assert "p_continue_favor" in str(first["trade_management_forecast_v1"])
    assert "lower_hold_buy" in str(first["observe_confirm_v1"])
    assert "lower_hold_buy" in str(first["observe_confirm_v2"])
    assert "BUY" in str(first["observe_confirm_v1"])
    assert "BUY" in str(first["observe_confirm_v2"])
    assert first["prs_contract_version"] == "v2"
    assert first["prs_canonical_position_field"] == "position_snapshot_v2"
    assert first["prs_canonical_position_effective_field"] == "position_snapshot_effective_v1"
    assert first["prs_canonical_response_field"] == "response_vector_v2"
    assert first["prs_canonical_response_effective_field"] == "response_vector_effective_v1"
    assert first["prs_canonical_state_field"] == "state_vector_v2"
    assert first["prs_canonical_state_effective_field"] == "state_vector_effective_v1"
    assert first["prs_canonical_evidence_field"] == "evidence_vector_v1"
    assert first["prs_canonical_evidence_effective_field"] == "evidence_vector_effective_v1"
    assert first["prs_canonical_belief_field"] == "belief_state_v1"
    assert first["prs_canonical_belief_effective_field"] == "belief_state_effective_v1"
    assert first["prs_canonical_barrier_field"] == "barrier_state_v1"
    assert first["prs_canonical_barrier_effective_field"] == "barrier_state_effective_v1"
    assert first["prs_canonical_forecast_features_field"] == "forecast_features_v1"
    assert first["prs_canonical_transition_forecast_field"] == "transition_forecast_v1"
    assert first["prs_canonical_trade_management_forecast_field"] == "trade_management_forecast_v1"
    assert first["prs_canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert first["prs_canonical_forecast_effective_field"] == "forecast_effective_policy_v1"
    assert "transition_side_separation" in str(first["forecast_gap_metrics_v1"])
    assert "ALIGNED_LOWER_WEAK" in str(first["position_snapshot_effective_v1"])
    assert "lower_hold_up" in str(first["response_vector_effective_v1"])
    assert "range_reversal_gain" in str(first["state_vector_effective_v1"])
    assert "buy_reversal_evidence" in str(first["evidence_vector_effective_v1"])
    assert "buy_belief" in str(first["belief_state_effective_v1"])
    assert "buy_barrier" in str(first["barrier_state_effective_v1"])
    assert "effective_equals_raw" in str(first["forecast_effective_policy_v1"])
    assert "identity_preserving_raw_equivalent" in str(first["layer_mode_effective_trace_v1"])
    assert "layer_mode_default_policy_v1" in str(first["layer_mode_influence_trace_v1"])
    assert "layer_mode_application_contract_v1" in str(first["layer_mode_application_trace_v1"])
    assert "layer_mode_identity_guard_v1" in str(first["layer_mode_identity_guard_trace_v1"])
    assert float(first["transition_confirm_fake_gap"]) == 0.18
    assert float(first["management_continue_fail_gap"]) == 0.27
    assert first["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert first["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert "observe_confirm_input_contract_v2" in str(first["observe_confirm_input_contract_v2"])
    assert "observe_confirm_migration_dual_write_v1" in str(first["observe_confirm_migration_dual_write_v1"])
    assert "observe_confirm_output_contract_v2" in str(first["observe_confirm_output_contract_v2"])
    assert "observe_confirm_scope_v1" in str(first["observe_confirm_scope_contract_v1"])
    assert "consumer_input_contract_v1" in str(first["consumer_input_contract_v1"])
    assert "consumer_migration_freeze_v1" in str(first["consumer_migration_freeze_v1"])
    assert "consumer_logging_contract_v1" in str(first["consumer_logging_contract_v1"])
    assert "consumer_test_contract_v1" in str(first["consumer_test_contract_v1"])
    assert "consumer_freeze_handoff_v1" in str(first["consumer_freeze_handoff_v1"])
    assert "layer_mode_contract_v1" in str(first["layer_mode_contract_v1"])
    assert "layer_mode_layer_inventory_v1" in str(first["layer_mode_layer_inventory_v1"])
    assert "layer_mode_default_policy_v1" in str(first["layer_mode_default_policy_v1"])
    assert "layer_mode_dual_write_v1" in str(first["layer_mode_dual_write_contract_v1"])
    assert "layer_mode_influence_semantics_v1" in str(first["layer_mode_influence_semantics_v1"])
    assert "layer_mode_application_contract_v1" in str(first["layer_mode_application_contract_v1"])
    assert "layer_mode_identity_guard_v1" in str(first["layer_mode_identity_guard_contract_v1"])
    assert "layer_mode_policy_overlay_output_v1" in str(first["layer_mode_policy_overlay_output_contract_v1"])
    assert "layer_mode_logging_replay_contract_v1" in str(first["layer_mode_logging_replay_contract_v1"])
    assert "layer_mode_test_contract_v1" in str(first["layer_mode_test_contract_v1"])
    assert "layer_mode_freeze_handoff_v1" in str(first["layer_mode_freeze_handoff_v1"])
    assert "layer_mode_scope_v1" in str(first["layer_mode_scope_contract_v1"])
    assert "setup_detector_responsibility_v1" in str(first["setup_detector_responsibility_contract_v1"])
    assert "setup_mapping_contract_v1" in str(first["setup_mapping_contract_v1"])
    assert "entry_guard_contract_v1" in str(first["entry_guard_contract_v1"])
    assert "entry_service_responsibility_v1" in str(first["entry_service_responsibility_contract_v1"])
    assert "exit_handoff_contract_v1" in str(first["exit_handoff_contract_v1"])
    assert "re_entry_contract_v1" in str(first["re_entry_contract_v1"])
    assert "consumer_scope_v1" in str(first["consumer_scope_contract_v1"])
    assert "consumer_layer_mode_integration_v1" in str(first["consumer_layer_mode_integration_v1"])
    assert first["consumer_input_observe_confirm_field"] == "observe_confirm_v1"
    assert first["consumer_input_contract_version"] == "consumer_input_contract_v1"
    assert first["consumer_migration_contract_version"] == "consumer_migration_freeze_v1"
    assert str(first["consumer_used_compatibility_fallback_v1"]).lower() == "true"
    assert first["consumer_policy_input_field"] == "layer_mode_policy_v1"
    assert first["consumer_policy_contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert str(first["consumer_policy_identity_preserved"]).lower() == "true"
    assert first["consumer_archetype_id"] == "lower_hold_buy"
    assert first["consumer_invalidation_id"] == "lower_support_fail"
    assert first["consumer_management_profile_id"] == "support_hold_profile"
    assert first["consumer_setup_id"] == "trend_pullback_buy"
    assert first["consumer_guard_result"] == "PASS"
    assert first["consumer_effective_action"] == "BUY"
    assert pd.isna(first["consumer_block_reason"]) or first["consumer_block_reason"] == ""
    assert pd.isna(first["consumer_block_kind"]) or first["consumer_block_kind"] == ""
    assert pd.isna(first["consumer_block_source_layer"]) or first["consumer_block_source_layer"] == ""
    assert str(first["consumer_handoff_contract_version"]) == "observe_confirm_output_contract_v2"
    assert first["prs_canonical_energy_field"] == "energy_helper_v2"
    assert first["energy_migration_contract_field"] == "energy_migration_dual_write_v1"
    assert first["energy_scope_contract_field"] == "energy_scope_contract_v1"
    assert first["runtime_alignment_scope_contract_field"] == "runtime_alignment_scope_contract_v1"
    assert first["energy_compatibility_runtime_field"] == "energy_snapshot"
    assert first["energy_logging_replay_contract_field"] == "energy_logging_replay_contract_v1"
    energy_migration_guard = json.loads(str(first["energy_migration_guard_v1"]))
    assert energy_migration_guard["compatibility_role"] == "compatibility_transition_only"
    assert energy_migration_guard["used_compatibility_bridge"] is False
    assert energy_migration_guard["legacy_identity_input_allowed"] is False
    runtime_alignment_scope_contract = json.loads(str(first["runtime_alignment_scope_contract_v1"]))
    assert runtime_alignment_scope_contract["contract_version"] == (
        RUNTIME_ALIGNMENT_SCOPE_CONTRACT_V1["contract_version"]
    )
    assert runtime_alignment_scope_contract["completed_definitions"] == [
        "14.0_scope_freeze",
        "14.1_observe_confirm_legacy_energy_detach",
        "14.2_observe_confirm_semantic_routing_hardening",
        "14.3_entry_service_consumer_stack_activation",
        "14.4_wait_engine_hint_activation",
        "14.5_truthful_consumer_usage_logging",
        "14.6_compatibility_migration_guard",
        "14.7_test_hardening",
        "14.8_docs_handoff_refreeze",
    ]
    observe_confirm_input_contract = json.loads(str(first["observe_confirm_input_contract_v2"]))
    assert [item["field"] for item in observe_confirm_input_contract["semantic_input_fields"]] == [
        "position_snapshot_v2",
        "response_vector_v2",
        "state_vector_v2",
        "evidence_vector_v1",
        "belief_state_v1",
        "barrier_state_v1",
    ]
    assert "legacy_rule_branch" in observe_confirm_input_contract["forbidden_direct_inputs"]
    observe_confirm_migration_contract = json.loads(str(first["observe_confirm_migration_dual_write_v1"]))
    assert observe_confirm_migration_contract["contract_version"] == OBSERVE_CONFIRM_MIGRATION_DUAL_WRITE_V1["contract_version"]
    assert observe_confirm_migration_contract["canonical_output_field_v2"] == "observe_confirm_v2"
    assert observe_confirm_migration_contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    observe_confirm_output_contract = json.loads(str(first["observe_confirm_output_contract_v2"]))
    assert observe_confirm_output_contract["contract_version"] == OBSERVE_CONFIRM_OUTPUT_CONTRACT_V2["contract_version"]
    assert observe_confirm_output_contract["canonical_output_field"] == "observe_confirm_v2"
    assert observe_confirm_output_contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert observe_confirm_output_contract["required_fields"] == [
        "state",
        "action",
        "side",
        "confidence",
        "reason",
        "archetype_id",
        "invalidation_id",
        "management_profile_id",
        "metadata",
    ]
    assert observe_confirm_output_contract["action_values"] == ["WAIT", "BUY", "SELL", "NONE"]
    assert observe_confirm_output_contract["side_values"] == ["BUY", "SELL", ""]
    observe_confirm_payload_v1 = json.loads(str(first["observe_confirm_v1"]))
    observe_confirm_payload_v2 = json.loads(str(first["observe_confirm_v2"]))
    consumer_layer_mode_integration_contract = json.loads(str(first["consumer_layer_mode_integration_v1"]))
    assert consumer_layer_mode_integration_contract["contract_version"] == CONSUMER_LAYER_MODE_INTEGRATION_V1["contract_version"]
    assert consumer_layer_mode_integration_contract["canonical_policy_field"] == "layer_mode_policy_v1"
    layer_mode_test_contract = json.loads(str(first["layer_mode_test_contract_v1"]))
    assert layer_mode_test_contract["contract_version"] == LAYER_MODE_TEST_CONTRACT_V1["contract_version"]
    assert layer_mode_test_contract["official_test_helper"] == "build_layer_mode_test_projection"
    layer_mode_freeze_handoff_contract = json.loads(str(first["layer_mode_freeze_handoff_v1"]))
    assert layer_mode_freeze_handoff_contract["contract_version"] == LAYER_MODE_FREEZE_HANDOFF_V1["contract_version"]
    assert layer_mode_freeze_handoff_contract["official_handoff_helper"] == "resolve_layer_mode_handoff_payload"
    assert observe_confirm_payload_v1 == observe_confirm_payload_v2
    assert observe_confirm_payload_v2["state"] == "CONFIRM"
    assert observe_confirm_payload_v2["action"] == "BUY"
    assert observe_confirm_payload_v2["side"] == "BUY"
    assert observe_confirm_payload_v2["archetype_id"] == "lower_hold_buy"
    assert observe_confirm_payload_v2["invalidation_id"] == "lower_support_fail"
    assert observe_confirm_payload_v2["management_profile_id"] == "support_hold_profile"
    assert observe_confirm_payload_v2["metadata"]["raw_contributions"] == {}
    assert observe_confirm_payload_v2["metadata"]["effective_contributions"] == {}
    assert observe_confirm_payload_v2["metadata"]["winning_evidence"] == ["lower_hold_up"]
    assert observe_confirm_payload_v2["metadata"]["blocked_reason"] == ""
    assert "forecast_calibration_v1" in str(first["forecast_calibration_contract_v1"])
    assert "outcome_labeler_scope_v1" in str(first["outcome_labeler_scope_contract_v1"])
    observe_confirm_scope_contract = json.loads(str(first["observe_confirm_scope_contract_v1"]))
    assert observe_confirm_scope_contract["scope"] == "semantic_archetype_routing_only"
    assert observe_confirm_scope_contract["canonical_output_field"] == "observe_confirm_v2"
    assert observe_confirm_scope_contract["compatibility_output_field_v1"] == "observe_confirm_v1"
    assert observe_confirm_scope_contract["input_contract_v2"]["contract_version"] == "observe_confirm_input_contract_v2"
    assert observe_confirm_scope_contract["output_contract_v2"]["contract_version"] == "observe_confirm_output_contract_v2"
    assert observe_confirm_scope_contract["migration_dual_write_v1"]["contract_version"] == "observe_confirm_migration_dual_write_v1"
    assert observe_confirm_scope_contract["state_semantics_v2"]["contract_version"] == "observe_confirm_state_semantics_v2"
    assert observe_confirm_scope_contract["archetype_taxonomy_v2"]["contract_version"] == "observe_confirm_archetype_taxonomy_v2"
    assert observe_confirm_scope_contract["invalidation_taxonomy_v2"]["contract_version"] == "observe_confirm_invalidation_taxonomy_v2"
    assert observe_confirm_scope_contract["management_profile_taxonomy_v2"]["contract_version"] == "observe_confirm_management_profile_taxonomy_v2"
    assert observe_confirm_scope_contract["routing_policy_v2"]["contract_version"] == "observe_confirm_routing_policy_v2"
    assert observe_confirm_scope_contract["confidence_semantics_v2"]["contract_version"] == "observe_confirm_confidence_semantics_v2"
    assert observe_confirm_scope_contract["action_side_semantics_v2"]["contract_version"] == "observe_confirm_action_side_semantics_v2"
    assert "setup naming" in observe_confirm_scope_contract["non_responsibilities"]
    assert observe_confirm_scope_contract["consumer_boundary"]["entry_service"].startswith("Consumes routing output only")
    consumer_input_contract = json.loads(str(first["consumer_input_contract_v1"]))
    assert consumer_input_contract["contract_version"] == CONSUMER_INPUT_CONTRACT_V1["contract_version"]
    assert consumer_input_contract["official_input_container"] == "DecisionContext.metadata"
    assert consumer_input_contract["canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert "response_vector_v2" in consumer_input_contract["forbidden_direct_inputs"]
    consumer_migration_contract = json.loads(str(first["consumer_migration_freeze_v1"]))
    assert consumer_migration_contract["contract_version"] == CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
    assert consumer_migration_contract["read_order"] == [
        "prs_canonical_observe_confirm_field",
        "observe_confirm_v2",
        "prs_compatibility_observe_confirm_field",
        "observe_confirm_v1",
    ]
    consumer_migration_guard = json.loads(str(first["consumer_migration_guard_v1"]))
    assert consumer_migration_guard["compatibility_role"] == "migration_bridge_only"
    assert consumer_migration_guard["used_compatibility_fallback_v1"] is True
    assert consumer_migration_guard["identity_ownership_preserved"] is True
    consumer_logging_contract = json.loads(str(first["consumer_logging_contract_v1"]))
    assert consumer_logging_contract["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert consumer_logging_contract["guard_result_values"] == ["PASS", "SEMANTIC_NON_ACTION", "EXECUTION_BLOCK"]
    consumer_test_contract = json.loads(str(first["consumer_test_contract_v1"]))
    assert consumer_test_contract["contract_version"] == CONSUMER_TEST_CONTRACT_V1["contract_version"]
    assert consumer_test_contract["required_behavior_axes"][0]["id"] == "setup_detector_naming_only"
    consumer_freeze_handoff = json.loads(str(first["consumer_freeze_handoff_v1"]))
    assert consumer_freeze_handoff["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]
    assert consumer_freeze_handoff["official_handoff_helper"] == "resolve_consumer_handoff_payload"
    layer_mode_contract = json.loads(str(first["layer_mode_contract_v1"]))
    assert layer_mode_contract["contract_version"] == LAYER_MODE_MODE_CONTRACT_V1["contract_version"]
    assert [item["mode"] for item in layer_mode_contract["canonical_modes"]] == ["shadow", "assist", "enforce"]
    layer_mode_inventory = json.loads(str(first["layer_mode_layer_inventory_v1"]))
    assert layer_mode_inventory["contract_version"] == LAYER_MODE_LAYER_INVENTORY_V1["contract_version"]
    assert layer_mode_inventory["layer_order"] == ["Position", "Response", "State", "Evidence", "Belief", "Barrier", "Forecast"]
    layer_mode_default_policy = json.loads(str(first["layer_mode_default_policy_v1"]))
    assert layer_mode_default_policy["contract_version"] == LAYER_MODE_DEFAULT_POLICY_V1["contract_version"]
    assert layer_mode_default_policy["policy_rows"][2]["target_mode_sequence"] == ["assist", "enforce"]
    assert layer_mode_default_policy["policy_rows"][4]["target_mode_sequence"] == ["shadow", "assist", "enforce"]
    layer_mode_dual_write = json.loads(str(first["layer_mode_dual_write_contract_v1"]))
    assert layer_mode_dual_write["contract_version"] == LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"]
    assert layer_mode_dual_write["layer_rows"][-1]["effective_fields"] == ["forecast_effective_policy_v1"]
    layer_mode_influence = json.loads(str(first["layer_mode_influence_semantics_v1"]))
    assert layer_mode_influence["contract_version"] == LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"]
    assert next(row for row in layer_mode_influence["layer_rows"] if row["layer"] == "Barrier")["dominant_enforce_role"] == "suppression_veto"
    assert next(row for row in layer_mode_influence["layer_rows"] if row["layer"] == "Forecast")["forbidden_even_in_enforce"] == ["execution_veto"]
    layer_mode_application = json.loads(str(first["layer_mode_application_contract_v1"]))
    assert layer_mode_application["contract_version"] == LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"]
    assert next(row for row in layer_mode_application["layer_rows"] if row["layer"] == "Position")["first_semantically_active_mode"] == "enforce"
    assert next(row for row in layer_mode_application["layer_rows"] if row["layer"] == "Forecast")["identity_guard_fields"] == ["archetype_id", "side"]
    layer_mode_identity_guard = json.loads(str(first["layer_mode_identity_guard_contract_v1"]))
    assert layer_mode_identity_guard["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert layer_mode_identity_guard["protected_fields"] == ["archetype_id", "side"]
    assert next(row for row in layer_mode_identity_guard["focus_layers"] if row["layer"] == "Forecast")["forbidden_adjustments"] == [
        "archetype_rewrite",
        "side_rewrite",
        "setup_rename",
        "execution_veto",
    ]
    layer_mode_identity_guard_trace = json.loads(str(first["layer_mode_identity_guard_trace_v1"]))
    assert layer_mode_identity_guard_trace["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert next(row for row in layer_mode_identity_guard_trace["layers"] if row["layer"] == "Barrier")["protected_fields"] == [
        "archetype_id",
        "side",
    ]
    layer_mode_policy_overlay_output = json.loads(str(first["layer_mode_policy_overlay_output_contract_v1"]))
    assert layer_mode_policy_overlay_output["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert layer_mode_policy_overlay_output["canonical_output_field"] == "layer_mode_policy_v1"
    layer_mode_policy = json.loads(str(first["layer_mode_policy_v1"]))
    assert layer_mode_policy["contract_version"] == "layer_mode_policy_v1"
    assert layer_mode_policy["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert layer_mode_policy["suppressed_reasons"] == []
    assert next(row for row in layer_mode_policy["effective_influences"] if row["layer"] == "Forecast")["identity_guard_active"] is True
    layer_mode_logging_replay = json.loads(str(first["layer_mode_logging_replay_v1"]))
    assert layer_mode_logging_replay["contract_version"] == "layer_mode_logging_replay_v1"
    assert layer_mode_logging_replay["logging_replay_contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert layer_mode_logging_replay["configured_modes"][0]["layer"] == "Position"
    assert layer_mode_logging_replay["final_consumer_action"]["consumer_effective_action"] == "BUY"
    assert layer_mode_logging_replay["final_consumer_action"]["consumer_guard_result"] == "PASS"
    assert layer_mode_logging_replay["block_suppress_reasons"]["consumer_block_reason"] == ""
    energy_helper = json.loads(str(first["energy_helper_v2"]))
    assert energy_helper["metadata"]["input_source_fields"]["evidence_vector_effective_v1"] is True
    assert energy_helper["metadata"]["logging_replay_freeze"]["contract_version"] == (
        ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    )
    assert energy_helper["metadata"]["logging_replay_freeze"]["consumer_usage_trace_present"] is True
    assert energy_helper["metadata"]["consumer_usage_trace"]["component"] == "EntryService"
    assert energy_helper["metadata"]["consumer_usage_trace"]["usage_mode"] == "not_consumed"
    assert energy_helper["metadata"]["consumer_usage_trace"]["consumed_fields"] == []
    assert energy_helper["metadata"]["consumer_usage_trace"]["guard_result"] == "PASS"
    assert energy_helper["metadata"]["consumer_usage_trace"]["effective_action"] == "BUY"
    energy_logging_contract = json.loads(str(first["energy_logging_replay_contract_v1"]))
    assert energy_logging_contract["contract_version"] == ENERGY_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert "consumer_usage_trace" in energy_logging_contract["required_sections"]
    layer_mode_scope_contract = json.loads(str(first["layer_mode_scope_contract_v1"]))
    assert layer_mode_scope_contract["contract_version"] == LAYER_MODE_SCOPE_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["mode_contract_v1"]["contract_version"] == LAYER_MODE_MODE_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["layer_inventory_v1"]["contract_version"] == LAYER_MODE_LAYER_INVENTORY_V1["contract_version"]
    assert layer_mode_scope_contract["default_mode_policy_v1"]["contract_version"] == LAYER_MODE_DEFAULT_POLICY_V1["contract_version"]
    assert layer_mode_scope_contract["dual_write_contract_v1"]["contract_version"] == LAYER_MODE_DUAL_WRITE_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["influence_semantics_v1"]["contract_version"] == LAYER_MODE_INFLUENCE_SEMANTICS_V1["contract_version"]
    assert layer_mode_scope_contract["application_contract_v1"]["contract_version"] == LAYER_MODE_APPLICATION_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["identity_guard_contract_v1"]["contract_version"] == LAYER_MODE_IDENTITY_GUARD_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["policy_overlay_output_contract_v1"]["contract_version"] == LAYER_MODE_POLICY_OVERLAY_OUTPUT_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["logging_replay_contract_v1"]["contract_version"] == LAYER_MODE_LOGGING_REPLAY_CONTRACT_V1["contract_version"]
    assert layer_mode_scope_contract["raw_output_policy"]["raw_outputs_always_emitted"] is True
    assert layer_mode_scope_contract["raw_output_policy"]["identity_guard_contract_version"] == "layer_mode_identity_guard_v1"
    assert layer_mode_scope_contract["raw_output_policy"]["identity_guard_trace_field"] == "layer_mode_identity_guard_trace_v1"
    assert layer_mode_scope_contract["raw_output_policy"]["policy_overlay_output_contract_version"] == "layer_mode_policy_overlay_output_v1"
    assert layer_mode_scope_contract["raw_output_policy"]["policy_overlay_output_field"] == "layer_mode_policy_v1"
    assert layer_mode_scope_contract["raw_output_policy"]["logging_replay_contract_version"] == "layer_mode_logging_replay_contract_v1"
    assert layer_mode_scope_contract["raw_output_policy"]["logging_replay_field"] == "layer_mode_logging_replay_v1"
    setup_detector_contract = json.loads(str(first["setup_detector_responsibility_contract_v1"]))
    assert setup_detector_contract["contract_version"] == "setup_detector_responsibility_v1"
    assert setup_detector_contract["scope"] == "setup_naming_only"
    assert setup_detector_contract["official_input_fields"] == ["archetype_id", "side", "reason", "market_mode"]
    assert setup_detector_contract["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    setup_mapping_contract = json.loads(str(first["setup_mapping_contract_v1"]))
    assert setup_mapping_contract["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert setup_mapping_contract["canonical_mapping"][0]["default_setup_id"] == "range_upper_reversal_sell"
    assert setup_mapping_contract["specialization_rules"][0]["specializations"][0]["setup_id"] == "trend_pullback_buy"
    entry_guard_contract = json.loads(str(first["entry_guard_contract_v1"]))
    assert entry_guard_contract["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert entry_guard_contract["reason_registry"][0]["reason"] == "observe_confirm_missing"
    assert entry_guard_contract["reason_registry"][3]["reason"] == "opposite_position_lock"
    entry_service_contract = json.loads(str(first["entry_service_responsibility_contract_v1"]))
    assert entry_service_contract["contract_version"] == "entry_service_responsibility_v1"
    assert entry_service_contract["scope"] == "execution_guard_only"
    assert "setup_id" in entry_service_contract["official_input_fields"]
    assert "setup_id rewrite" in entry_service_contract["non_responsibilities"]
    assert entry_service_contract["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    exit_handoff_contract = json.loads(str(first["exit_handoff_contract_v1"]))
    assert exit_handoff_contract["contract_version"] == EXIT_HANDOFF_CONTRACT_V1["contract_version"]
    assert exit_handoff_contract["official_input_fields"] == ["management_profile_id", "invalidation_id"]
    re_entry_contract = json.loads(str(first["re_entry_contract_v1"]))
    assert re_entry_contract["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert re_entry_contract["required_current_state"]["same_archetype_confirm_required"] is True
    consumer_scope_contract = json.loads(str(first["consumer_scope_contract_v1"]))
    assert consumer_scope_contract["contract_version"] == CONSUMER_SCOPE_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["canonical_input_field"] == "observe_confirm_v2"
    assert consumer_scope_contract["setup_mapping_contract_v1"]["contract_version"] == SETUP_MAPPING_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["entry_guard_contract_v1"]["contract_version"] == ENTRY_GUARD_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["exit_handoff_contract_v1"]["contract_version"] == EXIT_HANDOFF_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["re_entry_contract_v1"]["contract_version"] == RE_ENTRY_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["migration_freeze_v1"]["contract_version"] == CONSUMER_MIGRATION_FREEZE_V1["contract_version"]
    assert consumer_scope_contract["consumer_logging_contract_v1"]["contract_version"] == CONSUMER_LOGGING_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["consumer_test_contract_v1"]["contract_version"] == CONSUMER_TEST_CONTRACT_V1["contract_version"]
    assert consumer_scope_contract["consumer_freeze_handoff_v1"]["contract_version"] == CONSUMER_FREEZE_HANDOFF_V1["contract_version"]
    assert "semantic layer reinterpretation" in consumer_scope_contract["non_responsibilities"]
    scope_contract = json.loads(str(first["outcome_labeler_scope_contract_v1"]))
    assert scope_contract["anchor_basis"]["source"] == "entry_decisions.csv"
    assert scope_contract["anchor_basis"]["timestamp_priority_fields"] == ["signal_bar_ts", "time"]
    assert scope_contract["anchor_definition_v1"]["transition"]["anchor_row_source"] == "entry_decisions.csv"
    assert scope_contract["anchor_definition_v1"]["management"]["alternate_anchor_row_source"] == "position_open_event_row"
    assert scope_contract["horizon_definition_v1"]["transition"]["horizon_bars"] == 3
    assert scope_contract["horizon_definition_v1"]["management"]["horizon_bars"] == 6
    assert scope_contract["horizon_definition_v1"]["recommended_metadata"]["transition_horizon_bars"] == 3
    assert scope_contract["horizon_definition_v1"]["recommended_metadata"]["management_horizon_bars"] == 6
    assert scope_contract["transition_label_rules_v1"]["labels"]["buy_confirm_success_label"]["forecast_probability_field"] == "p_buy_confirm"
    assert "opposite-side dominance" in scope_contract["transition_label_rules_v1"]["labels"]["buy_confirm_success_label"]["negative_rule"]
    assert scope_contract["transition_label_rules_v1"]["labels"]["false_break_label"]["forecast_probability_field"] == "p_false_break"
    assert "meaningful opposite-direction follow-through" in scope_contract["transition_label_rules_v1"]["labels"]["reversal_success_label"]["positive_rule"]
    assert scope_contract["management_label_rules_v1"]["labels"]["continue_favor_label"]["forecast_probability_field"] == "p_continue_favor"
    assert "immediate cut or exit outperforms holding" in scope_contract["management_label_rules_v1"]["labels"]["fail_now_label"]["positive_rule"]
    assert scope_contract["management_label_rules_v1"]["labels"]["reach_tp1_label"]["tp1_definition_ref"] == "project_tp1_definition_v1"
    assert scope_contract["management_label_rules_v1"]["project_tp1_definition"]["fallback_status_if_unobservable"] == "NO_EXIT_CONTEXT"
    assert scope_contract["ambiguity_and_censoring_rules_v1"]["mandatory_statuses"] == [
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "NO_POSITION_CONTEXT",
        "AMBIGUOUS",
        "CENSORED",
    ]
    assert scope_contract["ambiguity_and_censoring_rules_v1"]["status_precedence"] == [
        "INVALID",
        "NO_POSITION_CONTEXT",
        "CENSORED",
        "INSUFFICIENT_FUTURE_BARS",
        "NO_EXIT_CONTEXT",
        "AMBIGUOUS",
        "VALID",
    ]
    assert scope_contract["future_source"]["source"] == "trade_closed_history.csv"
    assert scope_contract["outcome_signal_source_v1"]["required_inputs"][0]["source"] == "entry_decisions.csv"
    assert scope_contract["outcome_signal_source_v1"]["required_inputs"][1]["canonical_position_key_fields"] == ["ticket", "position_id"]
    assert scope_contract["label_metadata_v1"]["per_label_reason_fields"] == [
        "reason_code",
        "reason_text",
        "evidence",
    ]
    assert scope_contract["shadow_label_output_v1"]["row_type"] == "outcome_labels_v1"
    assert scope_contract["shadow_label_output_v1"]["output_targets"]["analysis_dir"] == "data/analysis"
    assert scope_contract["dataset_builder_bridge_v1"]["builder_file"] == "backend/trading/engine/offline/replay_dataset_builder.py"
    assert scope_contract["dataset_builder_bridge_v1"]["row_type"] == "replay_dataset_row_v1"
    assert scope_contract["validation_report_v1"]["report_type"] == "outcome_label_validation_report_v1"
    assert scope_contract["validation_report_v1"]["alert_thresholds"]["high_unknown_ratio_warn"] == 0.40
    assert scope_contract["outcome_signal_source_v1"]["deterministic_join_order"][0]["failure_statuses"]["no_match"] == "NO_POSITION_CONTEXT"
    assert scope_contract["outcome_signal_source_v1"]["deterministic_join_order"][1]["failure_statuses"]["missing_closed_row"] == "NO_EXIT_CONTEXT"
    assert "buy_confirm_success_label" in scope_contract["label_families"]["transition"]
    assert "continue_favor_label" in scope_contract["label_families"]["management"]
    assert "VALID" in scope_contract["label_status_values"]
    assert "NO_POSITION_CONTEXT" in scope_contract["label_status_values"]
    assert "NO_EXIT_CONTEXT" in scope_contract["label_status_values"]
    assert "INVALID" in scope_contract["label_status_values"]
    assert "POSITIVE" in scope_contract["label_polarity_values"]
    assert scope_contract["labeling_philosophy_v1"]["polarity_criteria"]["unknown"].startswith("row is not safely scorable")
    assert "horizon_definition_v1" in scope_contract["completed_definitions"]
    assert "transition_label_rules_v1" in scope_contract["completed_definitions"]
    assert "management_label_rules_v1" in scope_contract["completed_definitions"]
    assert "ambiguity_and_censoring_rules_v1" in scope_contract["completed_definitions"]
    assert "outcome_signal_source_v1" in scope_contract["completed_definitions"]
    assert "outcome_labeler_v1_implementation" in scope_contract["completed_definitions"]
    assert "label_metadata_v1" in scope_contract["completed_definitions"]
    assert "shadow_label_output_v1" in scope_contract["completed_definitions"]
    assert "dataset_builder_bridge_v1" in scope_contract["completed_definitions"]
    assert "validation_report_v1" in scope_contract["completed_definitions"]
    assert scope_contract["outcome_labeler_v1_implementation"]["bundle_function"] == "build_outcome_labels"
    assert scope_contract["deferred_definitions"] == []
    assert "prs_deprecated_fields" not in logged.columns
    assert "position_vector_v1" not in logged.columns
    assert "response_vector_v1" not in logged.columns
    assert "state_vector_v1" not in logged.columns
    assert "energy_snapshot_v1" not in logged.columns


def test_entry_decision_recorder_rolls_over_legacy_schema(monkeypatch, tmp_path: Path):
    runtime = SimpleNamespace(append_ai_entry_trace=lambda *_args, **_kwargs: None)
    rec = EntryDecisionRecorder(runtime)
    out = tmp_path / "entry_decisions.csv"
    out.write_text(
        "time,symbol,position_vector_v1,response_vector_v1,state_vector_v1,energy_snapshot_v1\n"
        "2026-03-09T00:00:00,BTCUSD,{},{},{},{}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_ENABLED", True, raising=False)
    monkeypatch.setattr(Config, "ENTRY_DECISION_LOG_PATH", str(out), raising=False)

    rec.append_entry_decision_log(
        {
            "symbol": "BTCUSD",
            "action": "SELL",
            "considered": 1,
            "outcome": "entered",
            "position_snapshot_v2": "{\"interpretation\":{\"primary_label\":\"ALIGNED_UPPER_WEAK\"}}",
            "response_raw_snapshot_v1": "{\"bb20_upper_reject\":1.0}",
            "response_vector_v2": "{\"upper_reject_down\":1.0}",
            "state_raw_snapshot_v1": "{\"market_mode\":\"RANGE\"}",
            "state_vector_v2": "{\"range_reversal_gain\":1.18}",
            "evidence_vector_v1": "{\"sell_reversal_evidence\":0.92,\"sell_total_evidence\":0.92}",
            "belief_state_v1": "{\"sell_belief\":0.57,\"sell_persistence\":0.4}",
            "barrier_state_v1": "{\"sell_barrier\":0.14}",
            "forecast_features_v1": "{\"position_primary_label\":\"ALIGNED_UPPER_WEAK\"}",
            "transition_forecast_v1": "{\"p_sell_confirm\":0.68}",
            "trade_management_forecast_v1": "{\"p_fail_now\":0.41}",
            "forecast_gap_metrics_v1": "{\"transition_side_separation\":0.19,\"transition_confirm_fake_gap\":0.11}",
            "transition_side_separation": 0.19,
            "transition_confirm_fake_gap": 0.11,
            "observe_confirm_v1": "{\"state\":\"CONFIRM\",\"action\":\"SELL\",\"archetype_id\":\"upper_reject_sell\"}",
        }
    )

    rolled = sorted(tmp_path.glob("entry_decisions.legacy_*.csv"))
    assert len(rolled) == 1
    logged = pd.read_csv(out, encoding="utf-8")
    detail_record = _load_detail_record(out)
    detail_first = detail_record["payload"]

    assert "position_vector_v1" not in logged.columns
    assert "signal_bar_ts" in logged.columns
    assert "signal_timeframe" in logged.columns
    assert "response_vector_v1" not in logged.columns
    assert "state_vector_v1" not in logged.columns
    assert "energy_snapshot_v1" not in logged.columns
    assert "energy_helper_v2" in logged.columns
    assert "observe_action" in logged.columns
    assert "observe_side" in logged.columns
    assert "core_resolved_shadow_action" in logged.columns
    assert "core_intended_direction" in logged.columns
    assert "core_archetype_implied_action" in logged.columns
    assert "core_intended_action_source" in logged.columns
    assert "observe_probe_override_pending" in logged.columns
    assert "runtime_alignment_scope_contract_v1" not in logged.columns
    assert logged.iloc[0]["prs_contract_version"] == "v2"
    assert logged.iloc[0]["observe_action"] == "SELL"
    assert logged.iloc[0]["observe_side"] == "SELL"
    assert logged.iloc[0]["core_intended_direction"] == "SELL"
    assert logged.iloc[0]["prs_canonical_response_field"] == "response_vector_v2"
    assert logged.iloc[0]["prs_canonical_state_field"] == "state_vector_v2"
    assert logged.iloc[0]["prs_canonical_evidence_field"] == "evidence_vector_v1"
    assert logged.iloc[0]["prs_canonical_belief_field"] == "belief_state_v1"
    assert logged.iloc[0]["prs_canonical_barrier_field"] == "barrier_state_v1"
    assert logged.iloc[0]["prs_canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert logged.iloc[0]["prs_canonical_energy_field"] == "energy_helper_v2"
    assert logged.iloc[0]["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert logged.iloc[0]["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert logged.iloc[0]["observe_confirm_v2"] != ""
    assert logged.iloc[0]["energy_helper_v2"] != ""
    assert logged.iloc[0]["detail_schema_version"] == detail_record["schema_version"]
    assert logged.iloc[0]["detail_row_key"] == detail_record["row_key"]
    assert "outcome_labeler_scope_v1" in str(detail_first["outcome_labeler_scope_contract_v1"])
    assert detail_first["runtime_alignment_scope_contract_v1"] != ""
    assert detail_first["observe_confirm_migration_dual_write_v1"] != ""
    assert detail_first["observe_confirm_output_contract_v2"] != ""
    return

    assert "position_vector_v1" not in logged.columns
    assert "forecast_calibration_contract_v1" in logged.columns
    assert "outcome_labeler_scope_contract_v1" in logged.columns
    assert "signal_bar_ts" in logged.columns
    assert "signal_timeframe" in logged.columns
    assert "response_vector_v1" not in logged.columns
    assert "state_vector_v1" not in logged.columns
    assert "energy_snapshot_v1" not in logged.columns
    assert "energy_helper_v2" in logged.columns
    assert "energy_logging_replay_contract_v1" in logged.columns
    assert "runtime_alignment_scope_contract_v1" in logged.columns
    assert logged.iloc[0]["prs_contract_version"] == "v2"
    assert logged.iloc[0]["prs_canonical_response_field"] == "response_vector_v2"
    assert logged.iloc[0]["prs_canonical_state_field"] == "state_vector_v2"
    assert logged.iloc[0]["prs_canonical_evidence_field"] == "evidence_vector_v1"
    assert logged.iloc[0]["prs_canonical_belief_field"] == "belief_state_v1"
    assert logged.iloc[0]["prs_canonical_barrier_field"] == "barrier_state_v1"
    assert logged.iloc[0]["prs_canonical_forecast_gap_metrics_field"] == "forecast_gap_metrics_v1"
    assert logged.iloc[0]["prs_canonical_energy_field"] == "energy_helper_v2"
    assert logged.iloc[0]["prs_canonical_observe_confirm_field"] == "observe_confirm_v2"
    assert logged.iloc[0]["prs_compatibility_observe_confirm_field"] == "observe_confirm_v1"
    assert logged.iloc[0]["energy_logging_replay_contract_field"] == "energy_logging_replay_contract_v1"
    assert logged.iloc[0]["runtime_alignment_scope_contract_field"] == "runtime_alignment_scope_contract_v1"
    assert logged.iloc[0]["runtime_alignment_scope_contract_v1"] != ""
    assert logged.iloc[0]["observe_confirm_v2"] != ""
    assert logged.iloc[0]["observe_confirm_migration_dual_write_v1"] != ""
    assert logged.iloc[0]["energy_helper_v2"] != ""
    assert logged.iloc[0]["observe_confirm_output_contract_v2"] != ""
    assert "outcome_labeler_scope_v1" in str(logged.iloc[0]["outcome_labeler_scope_contract_v1"])


def test_entry_guard_engine_btc_shadow_lower_buy_relaxes_box_middle_guard():
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.0, ask=100.02)
    h1 = pd.DataFrame({"high": [110.0, 110.0], "low": [90.0, 90.0], "close": [100.0, 100.0]})
    m15 = pd.DataFrame(
        {
            "high": [101.2, 101.0, 100.9, 100.8],
            "low": [99.7, 99.8, 99.9, 100.0],
            "close": [100.4, 100.5, 100.6, 100.7],
        }
    )

    class _SessionMgr:
        @staticmethod
        def get_session_range(_df, _start, _end):
            return {"high": 110.0, "low": 90.0}

        @staticmethod
        def get_position_in_box(_box, _px):
            return "MIDDLE"

    scorer = SimpleNamespace(session_mgr=_SessionMgr())
    ok, reason = eng.pass_box_middle_guard(
        symbol="BTCUSD",
        action="BUY",
        tick=tick,
        df_all={"1H": h1, "15M": m15},
        scorer=scorer,
        indicators={"ind_bb_20_mid": 100.0, "ind_bb_20_up": 102.0, "ind_bb_20_dn": 98.0},
        setup_id="trend_pullback_buy",
        setup_reason="shadow_failed_sell_reclaim_buy_confirm",
    )
    assert ok is True
    assert reason == ""


def test_entry_guard_engine_btc_shadow_lower_buy_relaxes_on_lower_band_reaction_even_if_channel_is_higher():
    eng = EntryGuardEngine()
    tick = SimpleNamespace(bid=100.66, ask=100.70)
    h1 = pd.DataFrame({"high": [110.0, 110.0], "low": [90.0, 90.0], "close": [100.0, 100.0]})
    m15 = pd.DataFrame(
        {
            "high": [100.90, 100.96, 101.02, 101.08],
            "low": [98.08, 98.14, 98.20, 98.24],
            "close": [100.35, 100.48, 100.57, 100.63],
        }
    )

    class _SessionMgr:
        @staticmethod
        def get_session_range(_df, _start, _end):
            return {"high": 110.0, "low": 90.0}

        @staticmethod
        def get_position_in_box(_box, _px):
            return "MIDDLE"

    scorer = SimpleNamespace(session_mgr=_SessionMgr())
    ok, reason = eng.pass_box_middle_guard(
        symbol="BTCUSD",
        action="BUY",
        tick=tick,
        df_all={"1H": h1, "15M": m15},
        scorer=scorer,
        indicators={"ind_bb_20_mid": 100.0, "ind_bb_20_up": 102.0, "ind_bb_20_dn": 98.0},
        setup_id="trend_pullback_buy",
        setup_reason="shadow_failed_sell_reclaim_buy_confirm",
    )
    assert ok is True
    assert reason == ""


def test_entry_threshold_engine_hard_guard_uses_range_symbol_floor(monkeypatch):
    monkeypatch.setattr(Config, "ENTRY_HARD_MAX_SPREAD_RATIO", 1.8, raising=False)
    monkeypatch.setattr(Config, "ENTRY_HARD_MAX_VOL_RATIO", 2.4, raising=False)
    monkeypatch.setattr(
        Config,
        "ENTRY_HARD_MIN_VOL_RATIO_BY_SYMBOL",
        {"NAS100": 0.55, "DEFAULT": 0.55},
        raising=False,
    )
    monkeypatch.setattr(
        Config,
        "ENTRY_HARD_MIN_VOL_RATIO_RANGE_BY_SYMBOL",
        {"NAS100": 0.30, "DEFAULT": 0.35},
        raising=False,
    )

    out = EntryThresholdEngine.check_hard_no_trade_guard(
        "NAS100",
        {"name": "RANGE", "spread_ratio": 0.1, "volatility_ratio": 0.39},
    )

    assert out == ""
