import csv
import json

from backend.app.trading_application import TradingApplication


class _DummyBroker:
    pass


class _DummyNotifier:
    def send(self, message):
        return None

    def shutdown(self):
        return None


class _DummyObservability:
    def incr(self, name, amount=1):
        return None

    def event(self, name, level="info", payload=None):
        return None


def _write_entry_decision_log(path, rows):
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_runtime_status_preserves_trace_quality_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "trade_history.csv"
    btc_wait_bias_bundle = {
        "contract_version": "entry_wait_bias_bundle_v1",
        "active_release_sources": ["belief"],
        "active_wait_lock_sources": ["state"],
        "release_bias_count": 1,
        "wait_lock_bias_count": 1,
        "threshold_adjustment": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 38.25,
            "effective_hard_threshold": 77.0,
            "combined_soft_multiplier": 0.85,
            "combined_hard_multiplier": 1.1,
        },
    }
    btc_wait_state_policy_input = {
        "contract_version": "entry_wait_state_policy_input_v1",
        "identity": {"symbol": "BTCUSD", "required_side": "BUY"},
        "helper_hints": {
            "wait_vs_enter_hint": "prefer_wait",
            "soft_block_active": True,
            "soft_block_reason": "energy_soft_block",
            "soft_block_strength": 0.66,
            "policy_hard_block_active": True,
            "policy_suppressed": False,
        },
        "special_scenes": {
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "probe_active": True,
            "probe_ready_for_entry": False,
            "xau_second_support_probe_relief": False,
            "btc_lower_strong_score_soft_wait_candidate": True,
        },
        "thresholds": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 38.25,
            "effective_hard_threshold": 77.0,
        },
        "bias_bundle": {
            "active_release_sources": ["belief"],
            "active_wait_lock_sources": ["state"],
            "release_bias_count": 1,
            "wait_lock_bias_count": 1,
        },
    }
    btc_wait_context = {
        "contract_version": "entry_wait_context_v1",
        "identity": {"symbol": "BTCUSD", "action": "BUY"},
        "reasons": {
            "blocked_by": "energy_soft_block",
            "observe_reason": "lower_rebound_probe_observe",
            "action_none_reason": "execution_soft_blocked",
        },
        "observe_probe": {
            "probe_scene_id": "btc_lower_buy_conservative_probe",
            "probe_active": True,
            "probe_ready_for_entry": False,
            "xau_second_support_probe_relief": False,
        },
        "bias": {"bundle": dict(btc_wait_bias_bundle)},
        "policy": {
            "state": "HELPER_SOFT_BLOCK",
            "reason": "soft_block_preferred_wait",
            "hard_wait": True,
            "entry_wait_state_policy_input_v1": dict(btc_wait_state_policy_input),
        },
    }
    xau_wait_bias_bundle = {
        "contract_version": "entry_wait_bias_bundle_v1",
        "active_release_sources": ["probe"],
        "active_wait_lock_sources": [],
        "release_bias_count": 1,
        "wait_lock_bias_count": 0,
        "threshold_adjustment": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 45.0,
            "effective_hard_threshold": 70.0,
            "combined_soft_multiplier": 1.0,
            "combined_hard_multiplier": 1.0,
        },
    }
    xau_wait_state_policy_input = {
        "contract_version": "entry_wait_state_policy_input_v1",
        "identity": {"symbol": "XAUUSD", "required_side": "BUY"},
        "helper_hints": {
            "wait_vs_enter_hint": "",
            "soft_block_active": False,
            "soft_block_reason": "",
            "soft_block_strength": 0.0,
            "policy_hard_block_active": False,
            "policy_suppressed": False,
        },
        "special_scenes": {
            "probe_scene_id": "xau_second_support_buy_probe",
            "probe_active": True,
            "probe_ready_for_entry": True,
            "xau_second_support_probe_relief": True,
            "btc_lower_strong_score_soft_wait_candidate": False,
        },
        "thresholds": {
            "base_soft_threshold": 45.0,
            "base_hard_threshold": 70.0,
            "effective_soft_threshold": 45.0,
            "effective_hard_threshold": 70.0,
        },
        "bias_bundle": {
            "active_release_sources": ["probe"],
            "active_wait_lock_sources": [],
            "release_bias_count": 1,
            "wait_lock_bias_count": 0,
        },
    }
    xau_wait_context = {
        "contract_version": "entry_wait_context_v1",
        "identity": {"symbol": "XAUUSD", "action": "BUY"},
        "reasons": {
            "blocked_by": "",
            "observe_reason": "lower_rebound_probe_observe",
            "action_none_reason": "",
        },
        "observe_probe": {
            "probe_scene_id": "xau_second_support_buy_probe",
            "probe_active": True,
            "probe_ready_for_entry": True,
            "xau_second_support_probe_relief": True,
        },
        "bias": {"bundle": dict(xau_wait_bias_bundle)},
        "policy": {
            "state": "PROBE_CANDIDATE",
            "reason": "xau_second_support_probe_wait",
            "hard_wait": False,
            "entry_wait_state_policy_input_v1": dict(xau_wait_state_policy_input),
        },
    }
    _write_entry_decision_log(
        app.entry_decision_log_path,
        [
            {
                "time": "2026-03-27T19:00:00+09:00",
                "symbol": "BTCUSD",
                "blocked_by": "energy_soft_block",
                "action_none_reason": "execution_soft_blocked",
                "consumer_check_stage": "BLOCKED",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "HELPER_SOFT_BLOCK",
                "entry_wait_hard": "True",
                "entry_wait_reason": "soft_block_preferred_wait",
                "entry_wait_selected": "True",
                "entry_wait_decision": "wait_soft_helper_block",
                "entry_wait_context_v1": json.dumps(btc_wait_context),
                "entry_wait_bias_bundle_v1": json.dumps(btc_wait_bias_bundle),
                "entry_wait_state_policy_input_v1": json.dumps(btc_wait_state_policy_input),
                "entry_wait_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_state_branch_applied",
                        "branch_records": [
                            {"branch": "helper_soft_block_state"},
                            {"branch": "helper_soft_block_hard_wait"},
                        ],
                    }
                ),
                "entry_wait_decision_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_decision_branch_applied",
                        "branch_records": [
                            {"branch": "action_readiness_utility"},
                            {"branch": "wait_soft_helper_block_decision"},
                        ],
                    }
                ),
            },
            {
                "time": "2026-03-27T19:01:00+09:00",
                "symbol": "NAS100",
                "blocked_by": "forecast_guard",
                "action_none_reason": "",
                "consumer_check_stage": "READY",
                "consumer_check_entry_ready": "True",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "NONE",
                "entry_wait_hard": "False",
                "entry_wait_reason": "",
                "entry_wait_selected": "False",
                "entry_wait_decision": "skip",
                "entry_wait_energy_usage_trace_v1": json.dumps(
                    {
                        "contract_version": "consumer_energy_usage_trace_v1",
                        "usage_source": "recorded",
                        "usage_mode": "wait_state_branch_applied",
                        "branch_records": [
                            {"branch": "helper_wait_bias_state"},
                        ],
                    }
                ),
            },
            {
                "time": "2026-03-27T19:02:00+09:00",
                "symbol": "XAUUSD",
                "blocked_by": "",
                "action_none_reason": "",
                "consumer_check_stage": "PROBE",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "PROBE_CANDIDATE",
                "entry_wait_hard": "False",
                "entry_wait_reason": "xau_second_support_probe_wait",
                "entry_wait_selected": "True",
                "entry_wait_decision": "wait_soft_probe_candidate",
                "entry_wait_context_v1": json.dumps(xau_wait_context),
                "entry_wait_bias_bundle_v1": json.dumps(xau_wait_bias_bundle),
                "entry_wait_state_policy_input_v1": json.dumps(xau_wait_state_policy_input),
            },
            {
                "time": "2026-03-27T19:03:00+09:00",
                "symbol": "BTCUSD",
                "blocked_by": "",
                "action_none_reason": "",
                "consumer_check_stage": "OBSERVE",
                "consumer_check_entry_ready": "False",
                "consumer_check_display_ready": "True",
                "entry_wait_state": "CENTER",
                "entry_wait_hard": "False",
                "entry_wait_reason": "center_wait",
                "entry_wait_selected": "False",
                "entry_wait_decision": "skip",
            },
        ],
    )
    _write_entry_decision_log(
        app.trade_history_csv_path,
        [
            {
                "close_time": "2026-03-27 19:10:00",
                "open_time": "2026-03-27 18:50:00",
                "symbol": "BTCUSD",
                "status": "OPEN",
                "exit_wait_state": "REVERSAL_CONFIRM",
                "exit_wait_selected": "1",
                "exit_wait_decision": "wait_exit_reversal_confirm",
                "decision_winner": "wait_exit",
                "decision_reason": "wait_exit_reversal_confirm",
                "exit_wait_state_family": "confirm_hold",
                "exit_wait_hold_class": "hard_hold",
                "exit_wait_decision_family": "wait_exit",
                "exit_wait_bridge_status": "aligned_confirm_wait",
            },
            {
                "close_time": "2026-03-27 19:11:00",
                "open_time": "2026-03-27 18:40:00",
                "symbol": "XAUUSD",
                "status": "CLOSED",
                "exit_wait_state": "RECOVERY_BE",
                "exit_wait_selected": "1",
                "exit_wait_decision": "wait_be_recovery",
                "decision_winner": "wait_be",
                "decision_reason": "wait_be_recovery",
                "exit_wait_state_family": "recovery_hold",
                "exit_wait_hold_class": "soft_hold",
                "exit_wait_decision_family": "recovery_wait",
                "exit_wait_bridge_status": "aligned_recovery_wait",
            },
            {
                "close_time": "2026-03-27 19:12:00",
                "open_time": "2026-03-27 18:30:00",
                "symbol": "NAS100",
                "status": "CLOSED",
                "exit_wait_state": "REVERSE_READY",
                "exit_wait_selected": "0",
                "exit_wait_decision": "",
                "decision_winner": "reverse_now",
                "decision_reason": "reverse_now_best",
                "exit_wait_state_family": "reverse_ready",
                "exit_wait_hold_class": "soft_hold",
                "exit_wait_decision_family": "reverse_now",
                "exit_wait_bridge_status": "aligned_reverse",
            },
        ],
    )
    app.latest_signal_by_symbol = {
        "BTCUSD": {
            "symbol": "BTCUSD",
            "action": "BUY",
            "next_action_hint": "BUY",
            "signal_bar_ts": 1773817800,
            "runtime_snapshot_generated_ts": 1773817812.5,
            "runtime_snapshot_key": "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1773817800|hint=BUY",
            "signal_age_sec": 12.5,
            "bar_age_sec": 12.5,
            "decision_latency_ms": 0,
            "missing_feature_count": 2,
            "data_completeness_ratio": 0.8,
            "used_fallback_count": 1,
            "compatibility_mode": "hybrid",
            "snapshot_payload_bytes": 321,
            "position_snapshot_v2": {
                "zones": {"box_zone": "LOWER"},
                "interpretation": {"primary_label": "LOWER_BIAS"},
                "energy": {"lower_position_force": 0.71},
                "vector": {"x_box": 0.12},
            },
            "response_vector_v2": {"lower_hold_up": 0.84},
            "observe_confirm_v2": {
                "action": "WAIT",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
            },
            "forecast_assist_v1": {"active": True, "decision_hint": "confirm_bias", "confirm_fake_gap": 0.21},
            "entry_default_side_gate_v1": {"contract_version": "entry_default_side_gate_v1", "gate_passed": True},
            "entry_probe_plan_v1": {
                "contract_version": "entry_probe_plan_v1",
                "active": True,
                "ready_for_entry": True,
                "reason": "probe_ready",
                "symbol_scene_relief": "xau_second_support_buy_probe",
                "symbol_probe_temperament_v1": {
                    "entry_style_hint": "aggressive_second_support",
                    "promotion_bias": "aggressive_second_support",
                    "source_map_id": "shared_symbol_temperament_map_v1",
                    "note": "xau_second_support_buy_more_aggressive",
                },
                "pair_gap": 0.28,
            },
            "edge_pair_law_v1": {"contract_version": "edge_pair_law_v1", "context_label": "LOWER_EDGE", "winner_side": "BUY"},
            "probe_candidate_v1": {
                "contract_version": "probe_candidate_v1",
                "active": True,
                "ready_for_entry": True,
                "probe_direction": "BUY",
                "candidate_support": 0.91,
                "pair_gap": 0.28,
                "intended_action": "BUY",
                "symbol_probe_temperament_v1": {
                    "scene_id": "xau_second_support_buy_probe",
                    "promotion_bias": "aggressive_second_support",
                    "source_map_id": "shared_symbol_temperament_map_v1",
                    "note": "xau_second_support_buy_more_aggressive",
                },
            },
            "entry_wait_context_v1": dict(btc_wait_context),
            "entry_wait_bias_bundle_v1": dict(btc_wait_bias_bundle),
            "entry_wait_state_policy_input_v1": dict(btc_wait_state_policy_input),
            "entry_wait_state": "HELPER_SOFT_BLOCK",
            "entry_wait_hard": 1,
            "entry_wait_reason": "soft_block_preferred_wait",
            "entry_wait_selected": 1,
            "entry_wait_decision": "wait_soft_helper_block",
            "entry_decision_context_v1": {
                "symbol": "BTCUSD",
                "phase": "entry",
                "market_mode": "RANGE",
                "box_state": "LOWER",
                "bb_state": "LOWER_EDGE",
                "metadata": {
                    "core_reason": "core_shadow_probe_action",
                    "forecast_assist_v1": {"active": True, "decision_hint": "confirm_bias", "confirm_fake_gap": 0.21},
                    "entry_probe_plan_v1": {"active": True, "ready_for_entry": True},
                },
            },
            "entry_decision_result_v1": {
                "phase": "entry",
                "symbol": "BTCUSD",
                "action": "BUY",
                "outcome": "wait",
                "blocked_by": "probe_barrier_blocked",
                "selected_setup": {"setup_id": "range_lower_reversal_buy", "side": "BUY"},
            },
            "semantic_shadow_available": 1,
            "semantic_shadow_reason": "available",
            "semantic_shadow_activation_state": "active",
            "semantic_shadow_activation_reason": "available",
            "semantic_live_threshold_applied": 0,
            "semantic_live_threshold_state": "fallback_blocked",
            "semantic_live_threshold_reason": "compatibility_mode_blocked",
        }
    }

    app._write_runtime_status(
        loop_count=1,
        symbols=["BTCUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))

    assert slim["detail_payload_path"] == "runtime_status.detail.json"
    assert slim["semantic_live_config"]["contract_version"] == "semantic_live_rollout_v1"
    assert "symbol_allowlist" in slim["semantic_live_config"]
    assert "entry_stage_allowlist" in slim["semantic_live_config"]
    assert slim["semantic_live_config"]["shadow_runtime_state"] == "inactive"
    assert slim["semantic_live_config"]["shadow_runtime_reason"] == "runtime_unavailable"
    assert slim["semantic_shadow_runtime_checked_at"]
    assert slim["semantic_shadow_runtime_model_dir"] == str(app.semantic_model_dir)
    assert slim["semantic_shadow_runtime_load_error"] == ""
    assert "semantic_rollout_state" in slim
    assert app.semantic_rollout_manifest_path.exists()
    assert slim["recent_summary_window"] == "last_200"
    assert slim["recent_stage_counts"]["READY"] == 1
    assert slim["recent_stage_counts"]["PROBE"] == 1
    assert slim["recent_stage_counts"]["OBSERVE"] == 1
    assert slim["recent_stage_counts"]["BLOCKED"] == 1
    assert slim["recent_wrong_ready_count"] == 1
    assert slim["recent_blocked_reason_counts"]["energy_soft_block"] == 1
    assert slim["recent_blocked_reason_counts"]["forecast_guard"] == 1
    assert slim["recent_symbol_summary"]["BTCUSD"]["rows"] == 2
    assert slim["recent_runtime_summary"]["windows"]["last_50"]["row_count"] == 4
    assert slim["recent_exit_summary_window"] == "last_200"
    assert slim["recent_exit_status_counts"]["CLOSED"] == 2
    assert slim["recent_exit_status_counts"]["OPEN"] == 1
    assert slim["recent_exit_state_semantic_summary"]["state_family_counts"]["confirm_hold"] == 1
    assert slim["recent_exit_state_semantic_summary"]["state_family_counts"]["recovery_hold"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["wait_exit"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["recovery_wait"] == 1
    assert slim["recent_exit_decision_summary"]["decision_family_counts"]["reverse_now"] == 1
    assert (
        slim["recent_exit_state_decision_bridge_summary"]["bridge_status_counts"]["aligned_confirm_wait"]
        == 1
    )
    assert slim["recent_exit_symbol_summary"]["BTCUSD"]["rows"] == 1
    assert "recent_runtime_diagnostics" not in slim
    assert "recent_exit_runtime_diagnostics" not in slim
    assert "semantic_shadow_runtime_diagnostics" not in slim
    slim_row = slim["latest_signal_by_symbol"]["BTCUSD"]
    assert slim_row["runtime_snapshot_key"].startswith("runtime_signal_row_v1|symbol=BTCUSD")
    assert slim_row["timestamp"]
    assert slim_row["observe_action"] == "WAIT"
    assert slim_row["observe_side"] == "BUY"
    assert slim_row["observe_reason"] == "lower_rebound_probe_observe"
    assert slim_row["signal_age_sec"] == 12.5
    assert slim_row["bar_age_sec"] == 12.5
    assert slim_row["decision_latency_ms"] == 0
    assert slim_row["missing_feature_count"] == 2
    assert slim_row["data_completeness_ratio"] == 0.8
    assert slim_row["used_fallback_count"] == 1
    assert slim_row["compatibility_mode"] == "hybrid"
    assert slim_row["snapshot_payload_bytes"] == 321
    assert slim_row["position_snapshot_v2"]["vector"]["x_box"] == 0.12
    assert slim_row["response_vector_v2"]["lower_hold_up"] == 0.84
    assert slim_row["forecast_assist_v1"]["decision_hint"] == "confirm_bias"
    assert slim_row["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert slim_row["edge_pair_law_v1"]["winner_side"] == "BUY"
    assert slim_row["probe_candidate_v1"]["intended_action"] == "BUY"
    assert slim_row["probe_candidate_active"] is True
    assert slim_row["probe_direction"] == "BUY"
    assert slim_row["probe_scene_id"] == "xau_second_support_buy_probe"
    assert slim_row["probe_candidate_support"] == 0.91
    assert slim_row["probe_pair_gap"] == 0.28
    assert slim_row["probe_plan_active"] is True
    assert slim_row["probe_plan_ready"] is True
    assert slim_row["probe_plan_reason"] == "probe_ready"
    assert slim_row["probe_plan_scene"] == "xau_second_support_buy_probe"
    assert slim_row["probe_promotion_bias"] == "aggressive_second_support"
    assert slim_row["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert slim_row["probe_entry_style"] == "aggressive_second_support"
    assert slim_row["probe_temperament_note"] == "xau_second_support_buy_more_aggressive"
    assert slim_row["quick_trace_state"] == "PROBE_READY"
    assert slim_row["quick_trace_reason"] == "probe_ready"
    assert slim_row["wait_policy_state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["wait_policy_reason"] == "soft_block_preferred_wait"
    assert slim_row["wait_probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert slim_row["wait_probe_ready_for_entry"] is False
    assert slim_row["wait_bias_release_sources"] == ["belief"]
    assert slim_row["wait_bias_wait_lock_sources"] == ["state"]
    assert slim_row["wait_required_side"] == "BUY"
    assert slim_row["entry_wait_state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["entry_wait_hard"] == 1
    assert slim_row["entry_wait_decision"] == "wait_soft_helper_block"
    assert slim_row["wait_threshold_shift_summary"]["soft_threshold_shift"] == -6.75
    assert slim_row["entry_wait_context_v1"]["policy"]["state"] == "HELPER_SOFT_BLOCK"
    assert slim_row["entry_wait_bias_bundle_v1"]["active_release_sources"] == ["belief"]
    assert slim_row["entry_wait_state_policy_input_v1"]["special_scenes"]["probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert slim_row["semantic_shadow_available"] == 1
    assert slim_row["semantic_shadow_reason"] == "available"
    assert slim_row["semantic_shadow_activation_state"] == "active"
    assert slim_row["semantic_shadow_activation_reason"] == "available"
    assert slim_row["semantic_live_threshold_applied"] == 0
    assert slim_row["semantic_live_threshold_state"] == "fallback_blocked"
    assert slim_row["semantic_live_threshold_reason"] == "compatibility_mode_blocked"
    assert slim_row["entry_decision_context_v1"]["metadata"]["core_reason"] == "core_shadow_probe_action"
    assert slim_row["entry_decision_result_v1"]["selected_setup"]["setup_id"] == "range_lower_reversal_buy"

    detail_row = detail["latest_signal_by_symbol"]["BTCUSD"]
    assert detail_row["runtime_snapshot_key"] == slim_row["runtime_snapshot_key"]
    assert detail_row["snapshot_payload_bytes"] == 321
    assert detail_row["position_snapshot_v2"]["vector"]["x_box"] == 0.12
    assert detail_row["semantic_shadow_activation_state"] == "active"
    assert detail_row["semantic_live_threshold_reason"] == "compatibility_mode_blocked"
    assert detail["recent_runtime_diagnostics"]["source_path"] == str(app.entry_decision_log_path)
    assert detail["recent_exit_runtime_diagnostics"]["source_path"] == str(app.trade_history_csv_path)
    assert detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["row_count"] == 3
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_state_semantic_summary"][
            "state_family_counts"
        ]["reverse_ready"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_decision_summary"][
            "winner_counts"
        ]["wait_be"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["exit_state_decision_bridge_summary"][
            "state_to_decision_counts"
        ]["confirm_hold->wait_exit"]
        == 1
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["XAUUSD"][
            "exit_decision_summary"
        ]["decision_family_counts"]["recovery_wait"]
        == 1
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wrong_ready_count"] == 1
    assert detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"]["rows"] == 2
    wait_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_energy_trace_summary"]
    assert wait_summary["entry_wait_state_trace"]["trace_present_rows"] == 2
    assert wait_summary["entry_wait_state_trace"]["trace_branch_rows"] == 2
    assert wait_summary["entry_wait_state_trace"]["branch_counts"]["helper_soft_block_state"] == 1
    assert wait_summary["entry_wait_state_trace"]["branch_counts"]["helper_wait_bias_state"] == 1
    assert wait_summary["entry_wait_decision_trace"]["trace_present_rows"] == 1
    assert wait_summary["entry_wait_decision_trace"]["branch_counts"]["wait_soft_helper_block_decision"] == 1
    wait_bias_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_bias_bundle_summary"]
    assert wait_bias_summary["active_release_source_counts"]["belief"] == 1
    assert wait_bias_summary["active_release_source_counts"]["probe"] == 1
    assert wait_bias_summary["active_wait_lock_source_counts"]["state"] == 1
    wait_policy_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_policy_surface_summary"]
    assert wait_policy_summary["policy_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_policy_summary["policy_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_policy_summary["policy_reason_counts"]["soft_block_preferred_wait"] == 1
    assert wait_policy_summary["policy_reason_counts"]["xau_second_support_probe_wait"] == 1
    assert wait_policy_summary["required_side_counts"]["BUY"] == 2
    assert wait_policy_summary["policy_hard_block_active_rows"] == 1
    assert wait_policy_summary["helper_soft_block_rows"] == 1
    assert wait_policy_summary["helper_wait_hint_rows"] == 1
    wait_scene_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_special_scene_summary"]
    assert wait_scene_summary["probe_scene_counts"]["btc_lower_buy_conservative_probe"] == 1
    assert wait_scene_summary["probe_scene_counts"]["xau_second_support_buy_probe"] == 1
    assert wait_scene_summary["xau_second_support_probe_relief_rows"] == 1
    assert wait_scene_summary["btc_lower_strong_score_soft_wait_candidate_rows"] == 1
    assert wait_scene_summary["probe_ready_for_entry_rows"] == 1
    wait_threshold_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_threshold_shift_summary"]
    assert wait_threshold_summary["soft_threshold_shift_avg"] == -3.375
    assert wait_threshold_summary["hard_threshold_shift_avg"] == 3.5
    assert wait_threshold_summary["soft_threshold_shift_down_rows"] == 1
    assert wait_threshold_summary["hard_threshold_shift_up_rows"] == 1
    wait_state_semantic_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_semantic_summary"]
    assert wait_state_semantic_summary["row_count"] == 4
    assert wait_state_semantic_summary["wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["CENTER"] == 1
    assert wait_state_semantic_summary["wait_state_counts"]["NONE"] == 1
    assert wait_state_semantic_summary["hard_wait_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_state_semantic_summary["hard_wait_true_rows"] == 1
    assert wait_state_semantic_summary["wait_reason_counts"]["soft_block_preferred_wait"] == 1
    wait_decision_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_decision_summary"]
    assert wait_decision_summary["decision_row_count"] == 4
    assert wait_decision_summary["wait_decision_counts"]["skip"] == 2
    assert wait_decision_summary["wait_decision_counts"]["wait_soft_helper_block"] == 1
    assert wait_decision_summary["wait_decision_counts"]["wait_soft_probe_candidate"] == 1
    assert wait_decision_summary["wait_selected_rows"] == 2
    assert wait_decision_summary["wait_skipped_rows"] == 2
    assert wait_decision_summary["wait_selected_rate"] == 0.5
    wait_bridge_summary = detail["recent_runtime_diagnostics"]["windows"]["last_200"]["wait_state_decision_bridge_summary"]
    assert wait_bridge_summary["bridge_row_count"] == 4
    assert wait_bridge_summary["state_to_decision_counts"]["HELPER_SOFT_BLOCK->wait_soft_helper_block"] == 1
    assert wait_bridge_summary["state_to_decision_counts"]["PROBE_CANDIDATE->wait_soft_probe_candidate"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["HELPER_SOFT_BLOCK"] == 1
    assert wait_bridge_summary["selected_by_state_counts"]["PROBE_CANDIDATE"] == 1
    assert wait_bridge_summary["hard_wait_selected_rows"] == 1
    assert wait_bridge_summary["soft_wait_selected_rows"] == 1
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_energy_trace_summary"
        ]["entry_wait_decision_trace"]["trace_branch_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_special_scene_summary"
        ]["btc_lower_strong_score_soft_wait_candidate_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_state_semantic_summary"
        ]["wait_state_counts"]["CENTER"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_decision_summary"
        ]["wait_selected_rows"]
        == 1
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_200"]["symbol_summary"]["BTCUSD"][
            "wait_state_decision_bridge_summary"
        ]["selected_by_state_counts"]["HELPER_SOFT_BLOCK"]
        == 1
    )
    assert (
        slim["recent_runtime_summary"]["windows"]["last_200"]["wait_energy_trace_summary"][
            "entry_wait_state_trace"
        ]["trace_branch_rows"]
        == 2
    )
    assert slim["recent_wait_bias_bundle_summary"]["active_release_source_counts"]["belief"] == 1
    assert slim["recent_wait_special_scene_summary"]["probe_scene_counts"]["xau_second_support_buy_probe"] == 1
    assert slim["recent_wait_threshold_shift_summary"]["soft_threshold_shift_avg"] == -3.375
    assert slim["recent_wait_state_semantic_summary"]["wait_state_counts"]["NONE"] == 1
    assert slim["recent_wait_decision_summary"]["wait_selected_rate"] == 0.5
    assert (
        slim["recent_wait_state_decision_bridge_summary"]["state_to_decision_counts"][
            "CENTER->skip"
        ]
        == 1
    )
    assert detail["semantic_shadow_runtime_checked_at"]
    assert detail["semantic_shadow_runtime_diagnostics"]["reason"] == "runtime_unavailable"
    assert detail["semantic_shadow_runtime_diagnostics"]["model_dir"] == str(app.semantic_model_dir)
    assert detail["semantic_shadow_runtime_diagnostics"]["raw"]["checked_at"]


def test_runtime_status_promotes_probe_candidate_from_observe_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(TradingApplication, "_load_ai_runtime", lambda self, _path: None)
    monkeypatch.setattr(TradingApplication, "_load_semantic_shadow_runtime", lambda self, _path: None)
    app = TradingApplication(
        broker=_DummyBroker(),
        notifier_client=_DummyNotifier(),
        observability=_DummyObservability(),
    )
    app.runtime_status_path = tmp_path / "runtime_status.json"
    app.runtime_status_detail_path = tmp_path / "runtime_status.detail.json"
    app.semantic_rollout_manifest_path = tmp_path / "semantic_live_rollout_latest.json"
    app.entry_decision_log_path = tmp_path / "missing_entry_decisions.csv"
    app.trade_history_csv_path = tmp_path / "missing_trade_history.csv"
    app.latest_signal_by_symbol = {
        "XAUUSD": {
            "symbol": "XAUUSD",
            "signal_bar_ts": 1773817800,
            "runtime_snapshot_generated_ts": 1773817812.5,
            "observe_confirm_v2": {
                "action": "BUY",
                "side": "BUY",
                "reason": "lower_rebound_probe_observe",
                "metadata": {
                    "blocked_reason": "outer_band_buy_reversal_support_required",
                    "blocked_guard": "outer_band_guard",
                    "probe_candidate_v1": {
                        "active": True,
                        "probe_direction": "BUY",
                        "candidate_support": 0.87,
                        "pair_gap": 0.18,
                        "symbol_probe_temperament_v1": {
                            "scene_id": "xau_second_support_buy_probe",
                            "promotion_bias": "aggressive_second_support",
                            "source_map_id": "shared_symbol_temperament_map_v1",
                            "note": "xau_second_support_buy_more_aggressive",
                        },
                    },
                    "edge_pair_law_v1": {
                        "context_label": "LOWER_EDGE",
                        "winner_side": "BUY",
                    },
                },
            },
        }
    }

    app._write_runtime_status(
        loop_count=1,
        symbols=["XAUUSD"],
        entry_threshold=45,
        exit_threshold=35,
    )

    slim = json.loads(app.runtime_status_path.read_text(encoding="utf-8"))
    slim_row = slim["latest_signal_by_symbol"]["XAUUSD"]
    detail = json.loads(app.runtime_status_detail_path.read_text(encoding="utf-8"))
    assert slim_row["blocked_by"] == "outer_band_guard"
    assert slim_row["probe_candidate_active"] is True
    assert slim_row["probe_direction"] == "BUY"
    assert slim_row["probe_scene_id"] == "xau_second_support_buy_probe"
    assert slim_row["probe_candidate_support"] == 0.87
    assert slim_row["probe_pair_gap"] == 0.18
    assert slim_row["probe_promotion_bias"] == "aggressive_second_support"
    assert slim_row["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert slim_row["probe_temperament_note"] == "xau_second_support_buy_more_aggressive"
    assert slim_row["quick_trace_state"] == "PROBE_CANDIDATE_BLOCKED"
    assert slim_row["quick_trace_reason"] == "outer_band_guard"
    assert slim_row["probe_candidate_v1"]["probe_direction"] == "BUY"
    assert slim_row["edge_pair_law_v1"]["winner_side"] == "BUY"
    assert slim["recent_runtime_summary"]["available"] is False
    assert slim["recent_runtime_summary"]["reason"] == "source_missing"
    assert slim["recent_exit_runtime_summary"]["available"] is False
    assert slim["recent_exit_runtime_summary"]["reason"] == "source_missing"
    assert slim["recent_stage_counts"] == {}
    assert slim["recent_wrong_ready_count"] == 0
    assert slim["recent_exit_status_counts"] == {}
    assert detail["recent_runtime_diagnostics"]["reason"] == "source_missing"
    assert detail["recent_exit_runtime_diagnostics"]["reason"] == "source_missing"
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["row_count"] == 0
    assert detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["row_count"] == 0
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_energy_trace_summary"][
            "entry_wait_state_trace"
        ]["trace_branch_rows"]
        == 0
    )
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_bias_bundle_summary"][
            "active_release_source_counts"
        ]
        == {}
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_state_semantic_summary"]["row_count"] == 0
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_decision_summary"]["wait_selected_rate"] == 0.0
    assert (
        detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_state_decision_bridge_summary"][
            "state_to_decision_counts"
        ]
        == {}
    )
    assert detail["recent_runtime_diagnostics"]["windows"]["last_50"]["wait_threshold_shift_summary"][
        "soft_threshold_shift_avg"
    ] == 0.0
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["exit_state_semantic_summary"][
            "state_family_counts"
        ]
        == {}
    )
    assert (
        detail["recent_exit_runtime_diagnostics"]["windows"]["last_50"]["exit_decision_summary"][
            "winner_counts"
        ]
        == {}
    )
