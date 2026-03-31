import os
from datetime import datetime

from backend.services.storage_compaction import (
    build_entry_decision_hot_payload,
    compact_runtime_signal_row,
    is_generic_runtime_signal_row_key,
    resolve_entry_decision_detail_path,
    resolve_entry_decision_row_key,
    resolve_runtime_signal_row_key,
    resolve_trade_link_key,
    rotate_entry_decision_detail_if_needed,
)


def test_build_entry_decision_hot_payload_promotes_probe_quick_fields():
    payload = {
        "symbol": "BTCUSD",
        "time": "2026-03-21T16:12:00",
        "observe_reason": "outer_band_reversal_support_required_observe",
        "blocked_by": "outer_band_sell_reversal_support_required",
        "action_none_reason": "probe_not_promoted",
        "entry_probe_plan_v1": {
            "contract_version": "entry_probe_plan_v1",
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_pair_gap_not_ready",
            "symbol_scene_relief": "btc_lower_buy_conservative_probe",
            "symbol_probe_temperament_v1": {
                "entry_style_hint": "conservative_hold_first",
                "promotion_bias": "conservative_hold_first",
                "source_map_id": "shared_symbol_temperament_map_v1",
                "note": "btc_lower_buy_less_frequent_hold_longer",
            },
            "pair_gap": 0.14,
        },
        "probe_candidate_v1": {
            "contract_version": "probe_candidate_v1",
            "active": True,
            "probe_direction": "BUY",
            "candidate_support": 0.37,
            "pair_gap": 0.14,
            "symbol_probe_temperament_v1": {
                "scene_id": "btc_lower_buy_conservative_probe",
                "promotion_bias": "conservative_hold_first",
                "source_map_id": "shared_symbol_temperament_map_v1",
                "note": "btc_lower_buy_less_frequent_hold_longer",
            },
        },
    }

    hot = build_entry_decision_hot_payload(payload, detail_row_key="detail-key")

    assert hot["probe_candidate_active"] is True
    assert hot["probe_direction"] == "BUY"
    assert hot["probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert hot["probe_candidate_support"] == 0.37
    assert hot["probe_pair_gap"] == 0.14
    assert hot["probe_plan_active"] is True
    assert hot["probe_plan_ready"] is False
    assert hot["probe_plan_reason"] == "probe_pair_gap_not_ready"
    assert hot["probe_plan_scene"] == "btc_lower_buy_conservative_probe"
    assert hot["probe_promotion_bias"] == "conservative_hold_first"
    assert hot["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert hot["probe_entry_style"] == "conservative_hold_first"
    assert hot["probe_temperament_note"] == "btc_lower_buy_less_frequent_hold_longer"
    assert hot["quick_trace_state"] == "PROBE_WAIT"
    assert hot["quick_trace_reason"] == "probe_pair_gap_not_ready"


def test_build_entry_decision_hot_payload_preserves_consumer_check_state():
    payload = {
        "symbol": "NAS100",
        "time": "2026-03-27T13:40:00",
        "consumer_check_display_ready": True,
        "consumer_check_entry_ready": False,
        "consumer_check_side": "SELL",
        "consumer_check_stage": "PROBE",
        "consumer_check_reason": "upper_reject_probe_observe",
        "consumer_check_display_strength_level": 6,
        "consumer_check_state_v1": {
            "contract_version": "consumer_check_state_v1",
            "check_candidate": True,
            "check_display_ready": True,
            "entry_ready": False,
            "check_side": "SELL",
            "check_stage": "PROBE",
            "check_reason": "upper_reject_probe_observe",
            "entry_block_reason": "probe_not_promoted",
            "display_strength_level": 6,
        },
    }

    hot = build_entry_decision_hot_payload(payload, detail_row_key="detail-key")

    assert hot["consumer_check_display_ready"] is True
    assert hot["consumer_check_entry_ready"] is False
    assert hot["consumer_check_side"] == "SELL"
    assert hot["consumer_check_stage"] == "PROBE"
    assert hot["consumer_check_reason"] == "upper_reject_probe_observe"
    assert hot["consumer_check_display_strength_level"] == 6
    assert "consumer_check_state_v1" in hot
    assert '"check_stage":"PROBE"' in str(hot["consumer_check_state_v1"])


def test_compact_runtime_signal_row_promotes_probe_quick_fields():
    row = {
        "symbol": "XAUUSD",
        "time": "2026-03-21T16:12:00",
        "observe_confirm_v2": {
            "action": "BUY",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
        },
        "probe_candidate_v1": {
            "contract_version": "probe_candidate_v1",
            "active": True,
            "probe_direction": "BUY",
            "candidate_support": 0.92,
            "pair_gap": 0.26,
            "symbol_probe_temperament_v1": {
                "scene_id": "xau_second_support_buy_probe",
                "promotion_bias": "aggressive_second_support",
                "source_map_id": "shared_symbol_temperament_map_v1",
                "note": "xau_second_support_buy_more_aggressive",
            },
        },
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
            "pair_gap": 0.26,
        },
        "entry_decision_result_v1": {
            "phase": "entry",
            "symbol": "XAUUSD",
            "action": "",
            "outcome": "wait",
            "blocked_by": "",
            "reason": "core_shadow_probe_action",
            "metrics": {
                "observe_reason": "lower_rebound_probe_observe",
                "action_none_reason": "",
            },
        },
    }

    compact = compact_runtime_signal_row(row)

    assert compact["observe_reason"] == "lower_rebound_probe_observe"
    assert compact["probe_candidate_active"] is True
    assert compact["probe_direction"] == "BUY"
    assert compact["probe_scene_id"] == "xau_second_support_buy_probe"
    assert compact["probe_candidate_support"] == 0.92
    assert compact["probe_pair_gap"] == 0.26
    assert compact["probe_plan_active"] is True
    assert compact["probe_plan_ready"] is True
    assert compact["probe_plan_reason"] == "probe_ready"
    assert compact["probe_plan_scene"] == "xau_second_support_buy_probe"
    assert compact["probe_promotion_bias"] == "aggressive_second_support"
    assert compact["probe_temperament_source"] == "shared_symbol_temperament_map_v1"
    assert compact["probe_entry_style"] == "aggressive_second_support"
    assert compact["probe_temperament_note"] == "xau_second_support_buy_more_aggressive"
    assert compact["quick_trace_state"] == "PROBE_READY"
    assert compact["quick_trace_reason"] == "probe_ready"
    assert compact["entry_probe_plan_v1"]["ready_for_entry"] is True
    assert compact["entry_probe_plan_v1"]["symbol_probe_temperament_v1"]["promotion_bias"] == "aggressive_second_support"


def test_compact_runtime_signal_row_surfaces_consumer_check_state():
    row = {
        "symbol": "BTCUSD",
        "time": "2026-03-27T13:40:00",
        "observe_reason": "lower_rebound_probe_observe",
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
    }

    compact = compact_runtime_signal_row(row)

    assert compact["consumer_check_display_ready"] is True
    assert compact["consumer_check_entry_ready"] is False
    assert compact["consumer_check_side"] == "BUY"
    assert compact["consumer_check_stage"] == "PROBE"
    assert compact["consumer_check_reason"] == "lower_rebound_probe_observe"
    assert compact["consumer_check_display_strength_level"] == 6
    assert compact["consumer_check_state_v1"]["check_stage"] == "PROBE"
    assert compact["consumer_check_state_v1"]["entry_block_reason"] == "probe_not_promoted"


def test_wait_runtime_surface_compaction_keeps_context_bundle_and_policy_summary():
    row = {
        "symbol": "BTCUSD",
        "time": "2026-03-27T19:00:00+09:00",
        "entry_wait_context_v1": {
            "contract_version": "entry_wait_context_v1",
            "observe_probe": {
                "probe_scene_id": "btc_lower_buy_conservative_probe",
                "probe_ready_for_entry": False,
                "xau_second_support_probe_relief": False,
            },
            "bias": {
                "bundle": {
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
                    },
                }
            },
            "policy": {
                "state": "HELPER_SOFT_BLOCK",
                "reason": "soft_block_preferred_wait",
                "hard_wait": True,
                "entry_wait_state_policy_input_v1": {
                    "contract_version": "entry_wait_state_policy_input_v1",
                    "identity": {"symbol": "BTCUSD", "required_side": "BUY"},
                    "special_scenes": {
                        "probe_scene_id": "btc_lower_buy_conservative_probe",
                        "btc_lower_strong_score_soft_wait_candidate": True,
                    },
                    "thresholds": {
                        "base_soft_threshold": 45.0,
                        "base_hard_threshold": 70.0,
                        "effective_soft_threshold": 38.25,
                        "effective_hard_threshold": 77.0,
                    },
                    "helper_hints": {
                        "wait_vs_enter_hint": "prefer_wait",
                        "soft_block_active": True,
                    },
                    "bias_bundle": {
                        "active_release_sources": ["belief"],
                        "active_wait_lock_sources": ["state"],
                        "release_bias_count": 1,
                        "wait_lock_bias_count": 1,
                    },
                },
            },
        },
    }

    compact = compact_runtime_signal_row(row)

    assert compact["wait_policy_state"] == "HELPER_SOFT_BLOCK"
    assert compact["wait_policy_reason"] == "soft_block_preferred_wait"
    assert compact["wait_probe_scene_id"] == "btc_lower_buy_conservative_probe"
    assert compact["wait_probe_ready_for_entry"] is False
    assert compact["wait_required_side"] == "BUY"
    assert compact["wait_bias_release_sources"] == ["belief"]
    assert compact["wait_bias_wait_lock_sources"] == ["state"]
    assert compact["wait_threshold_shift_summary"]["soft_threshold_shift"] == -6.75
    assert compact["entry_wait_context_v1"]["policy"]["state"] == "HELPER_SOFT_BLOCK"
    assert compact["entry_wait_bias_bundle_v1"]["active_wait_lock_sources"] == ["state"]
    assert compact["entry_wait_state_policy_input_v1"]["special_scenes"]["probe_scene_id"] == "btc_lower_buy_conservative_probe"

    hot = build_entry_decision_hot_payload(row, detail_row_key="detail-key")

    assert '"probe_scene_id":"btc_lower_buy_conservative_probe"' in str(hot["entry_wait_context_v1"])
    assert '"active_release_sources":["belief"]' in str(hot["entry_wait_bias_bundle_v1"])
    assert '"required_side":"BUY"' in str(hot["entry_wait_state_policy_input_v1"])


def test_compact_runtime_signal_row_infers_observe_side_when_observe_payload_side_is_blank():
    row = {
        "symbol": "BTCUSD",
        "box_state": "LOWER",
        "bb_state": "LOWER_EDGE",
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "outer_band_reversal_support_required_observe",
            "metadata": {
                "blocked_reason": "outer_band_buy_reversal_support_required",
            },
        },
    }

    compact = compact_runtime_signal_row(row)

    assert compact["observe_action"] == "WAIT"
    assert compact["observe_side"] == "BUY"
    assert compact["observe_reason"] == "outer_band_reversal_support_required_observe"


def test_build_entry_decision_hot_payload_infers_observe_fields_from_reason_and_guard():
    payload = {
        "symbol": "XAUUSD",
        "time": "2026-03-23T22:09:12",
        "box_state": "MIDDLE",
        "bb_state": "MID",
        "observe_reason": "middle_sr_anchor_required_observe",
        "blocked_by": "middle_sr_anchor_guard",
        "action_none_reason": "observe_state_wait",
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "",
            "reason": "middle_sr_anchor_required_observe",
            "metadata": {
                "blocked_reason": "middle_buy_requires_sr_anchor",
            },
        },
    }

    hot = build_entry_decision_hot_payload(payload, detail_row_key="detail-key")

    assert hot["observe_action"] == "WAIT"
    assert hot["observe_side"] == "BUY"


def test_resolve_entry_decision_row_key_adds_sparse_wait_discriminator():
    row = {
        "symbol": "BTCUSD",
        "signal_bar_ts": 1774092600,
        "time": "2026-03-21T17:32:10",
        "action": "",
        "setup_id": "",
        "outcome": "wait",
        "observe_reason": "lower_rebound_probe_observe",
        "action_none_reason": "probe_not_promoted",
        "quick_trace_state": "PROBE_WAIT",
    }

    key = resolve_entry_decision_row_key(row)

    assert key.startswith(
        "replay_dataset_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1774092600.0|action=|setup_id=|ticket=0"
    )
    assert "|decision_time=2026-03-21T17:32:10" in key
    assert "|observe_reason=lower_rebound_probe_observe" in key
    assert "|probe_state=PROBE_WAIT" in key
    assert "|action_none_reason=probe_not_promoted" in key


def test_resolve_entry_decision_row_key_keeps_block_reason_distinct_from_non_action_reason():
    row = {
        "symbol": "BTCUSD",
        "signal_bar_ts": 1774092600,
        "time": "2026-03-21T17:32:10",
        "action": "",
        "setup_id": "",
        "outcome": "wait",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "forecast_guard",
        "action_none_reason": "probe_not_promoted",
        "quick_trace_state": "PROBE_WAIT",
    }

    key = resolve_entry_decision_row_key(row)

    assert "|observe_reason=upper_reject_probe_observe" in key
    assert "|blocked_by=forecast_guard" in key
    assert "|action_none_reason=probe_not_promoted" in key


def test_build_entry_decision_hot_payload_preserves_reason_triplet_without_collapse():
    payload = {
        "symbol": "XAUUSD",
        "time": "2026-03-23T22:09:12",
        "observe_reason": "upper_reject_probe_observe",
        "blocked_by": "probe_promotion_gate",
        "action_none_reason": "probe_not_promoted",
        "entry_probe_plan_v1": {
            "contract_version": "entry_probe_plan_v1",
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_forecast_not_ready",
            "symbol_scene_relief": "xau_upper_sell_probe",
        },
        "probe_candidate_v1": {
            "contract_version": "probe_candidate_v1",
            "active": True,
            "probe_direction": "SELL",
            "candidate_support": 0.39,
            "pair_gap": 0.17,
        },
    }

    hot = build_entry_decision_hot_payload(payload, detail_row_key="detail-key")

    assert hot["observe_reason"] == "upper_reject_probe_observe"
    assert hot["blocked_by"] == "probe_promotion_gate"
    assert hot["action_none_reason"] == "probe_not_promoted"
    assert hot["r0_non_action_family"] == "probe_not_promoted"
    assert '"non_action_family":"probe_not_promoted"' in str(hot["r0_row_interpretation_v1"])
    assert hot["quick_trace_state"] == "PROBE_WAIT"
    assert hot["quick_trace_reason"] == "probe_forecast_not_ready"


def test_compact_runtime_signal_row_builds_r0_interpretation_contract():
    row = {
        "symbol": "BTCUSD",
        "time": "2026-03-28T11:31:00+09:00",
        "observe_confirm_v2": {
            "state": "OBSERVE",
            "action": "WAIT",
            "side": "BUY",
            "reason": "lower_rebound_probe_observe",
            "metadata": {
                "blocked_guard": "probe_promotion_gate",
            },
        },
        "probe_candidate_v1": {
            "contract_version": "probe_candidate_v1",
            "active": True,
            "probe_direction": "BUY",
        },
        "entry_probe_plan_v1": {
            "contract_version": "entry_probe_plan_v1",
            "active": True,
            "ready_for_entry": False,
            "reason": "probe_forecast_not_ready",
        },
        "entry_decision_result_v1": {
            "phase": "entry",
            "symbol": "BTCUSD",
            "action": "",
            "outcome": "wait",
            "metrics": {
                "action_none_reason": "probe_not_promoted",
            },
        },
        "semantic_live_rollout_mode": "threshold_only",
        "semantic_live_fallback_reason": "baseline_no_action",
        "semantic_live_symbol_allowed": 1,
        "semantic_live_entry_stage_allowed": 1,
    }

    compact = compact_runtime_signal_row(row)

    assert compact["r0_non_action_family"] == "probe_not_promoted"
    assert compact["r0_semantic_runtime_state"] == "FALLBACK"
    assert compact["r0_row_interpretation_v1"]["observe_reason"] == "lower_rebound_probe_observe"
    assert compact["r0_row_interpretation_v1"]["blocked_by"] == "probe_promotion_gate"
    assert compact["r0_row_interpretation_v1"]["action_none_reason"] == "probe_not_promoted"
    assert compact["r0_row_interpretation_v1"]["non_action_family"] == "probe_not_promoted"
    assert compact["r0_row_interpretation_v1"]["semantic_live_fallback_reason"] == "baseline_no_action"


def test_runtime_snapshot_key_keeps_anchor_identity_without_reason_suffixes():
    key = resolve_runtime_signal_row_key(
        {
            "symbol": "BTCUSD",
            "signal_bar_ts": 1774092600,
            "next_action_hint": "WAIT",
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
        }
    )

    assert key == (
        "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=1774092600.0|hint=WAIT"
    )
    assert "observe_reason" not in key
    assert "blocked_by" not in key
    assert "action_none_reason" not in key


def test_runtime_snapshot_key_uses_time_when_signal_bar_ts_is_zero():
    key = resolve_runtime_signal_row_key(
        {
            "symbol": "BTCUSD",
            "signal_bar_ts": 0,
            "time": "2026-03-29T10:15:30",
            "next_action_hint": "WAIT",
        }
    )

    assert key == (
        "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=time|anchor_value=2026-03-29T10:15:30|hint=WAIT"
    )
    assert is_generic_runtime_signal_row_key(key) is False
    assert is_generic_runtime_signal_row_key(
        "runtime_signal_row_v1|symbol=BTCUSD|anchor_field=signal_bar_ts|anchor_value=0.0|hint=WAIT"
    ) is True


def test_trade_link_key_tracks_execution_identity_without_non_action_reason():
    key = resolve_trade_link_key(
        {
            "ticket": 12345,
            "symbol": "XAUUSD",
            "direction": "SELL",
            "open_ts": 1774092602,
            "observe_reason": "upper_reject_probe_observe",
            "blocked_by": "forecast_guard",
            "action_none_reason": "probe_not_promoted",
        }
    )

    assert key == "trade_link_v1|ticket=12345|symbol=XAUUSD|direction=SELL|open_ts=1774092602"
    assert "observe_reason" not in key
    assert "blocked_by" not in key
    assert "action_none_reason" not in key


def test_resolve_entry_decision_row_key_uses_trade_link_ticket_for_entered_rows_without_ticket():
    first = resolve_entry_decision_row_key(
        {
            "symbol": "BTCUSD",
            "signal_bar_ts": 1774509300,
            "action": "BUY",
            "setup_id": "range_lower_reversal_buy",
            "outcome": "entered",
            "trade_link_key": "trade_link_v1|ticket=101223990|symbol=BTCUSD|direction=BUY|open_ts=1774498503",
        }
    )
    second = resolve_entry_decision_row_key(
        {
            "symbol": "BTCUSD",
            "signal_bar_ts": 1774509300,
            "action": "BUY",
            "setup_id": "range_lower_reversal_buy",
            "outcome": "entered",
            "trade_link_key": "trade_link_v1|ticket=101224602|symbol=BTCUSD|direction=BUY|open_ts=1774498631",
        }
    )

    assert "|ticket=101223990" in first
    assert "|ticket=101224602" in second
    assert first != second


def test_rotate_entry_decision_detail_if_needed_rotates_size_limit(tmp_path):
    active_csv = tmp_path / "entry_decisions.csv"
    detail_path = resolve_entry_decision_detail_path(active_csv)
    detail_path.write_text('{"row":1}\n{"row":2}\n', encoding="utf-8")

    result = rotate_entry_decision_detail_if_needed(
        active_csv,
        now=datetime(2026, 3, 22, 9, 15, 0),
        max_bytes=8,
        roll_daily=False,
    )

    assert result["rotated"] is True
    assert result["reasons"] == ["size_limit"]
    assert result["rotated_path"].endswith(".jsonl")
    assert detail_path.exists() is False

    rotated_path = tmp_path / os.path.basename(result["rotated_path"])
    assert rotated_path.read_text(encoding="utf-8") == '{"row":1}\n{"row":2}\n'


def test_rotate_entry_decision_detail_if_needed_rotates_day_boundary(tmp_path):
    active_csv = tmp_path / "entry_decisions.csv"
    detail_path = resolve_entry_decision_detail_path(active_csv)
    detail_path.write_text('{"row":1}\n', encoding="utf-8")
    old_time = datetime(2026, 3, 21, 23, 59, 0).timestamp()
    os.utime(detail_path, (old_time, old_time))

    result = rotate_entry_decision_detail_if_needed(
        active_csv,
        now=datetime(2026, 3, 22, 0, 1, 0),
        max_bytes=1024 * 1024,
        roll_daily=True,
    )

    assert result["rotated"] is True
    assert result["reasons"] == ["day_boundary"]
    assert detail_path.exists() is False
