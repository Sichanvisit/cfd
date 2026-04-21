import csv
import json
from pathlib import Path

import pandas as pd

from backend.services.breakout_event_overlay import (
    BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1,
    build_breakout_event_overlay_candidates_v1,
    build_breakout_event_overlay_trace_v1,
)
from backend.services.breakout_event_replay import (
    BREAKOUT_ACTION_TARGET_ENTER_NOW,
    BREAKOUT_ACTION_TARGET_EXIT_PROTECT,
    BREAKOUT_ACTION_TARGET_WAIT_MORE,
    BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1,
    build_breakout_action_target_v1,
    build_breakout_manual_alignment_v1,
)
from backend.services.breakout_event_report import (
    build_breakout_manual_alignment_report_v1,
    build_breakout_event_phase0_report_v1,
    render_breakout_event_phase0_markdown,
    render_breakout_manual_alignment_markdown,
)
from backend.services.breakout_manual_overlap_recovery import (
    build_breakout_manual_overlap_recovery_queue,
)
from backend.services.breakout_manual_overlap_seed_draft import (
    build_breakout_manual_overlap_seed_draft,
)
from backend.services.breakout_backfill_runner_scaffold import (
    write_breakout_backfill_runner_scaffold,
)
from backend.services.breakout_manual_learning_bridge import (
    build_breakout_manual_learning_bridge,
    merge_breakout_manual_sources,
)
from backend.services.breakout_manual_learning_recovery import (
    build_breakout_manual_learning_recovery_queue,
)
from backend.services.breakout_external_source_priority import (
    build_breakout_external_source_priority_report,
    write_breakout_external_source_priority_report,
)
from backend.services.breakout_aligned_training_seed import (
    write_breakout_aligned_training_seed_report,
)
from backend.services.breakout_replay_time_correction import (
    write_breakout_replay_time_correction_report,
)
from backend.services.breakout_alignment_gap_recovery import (
    write_breakout_alignment_gap_recovery_report,
)
from backend.services.breakout_shadow_preview_training_set import (
    write_breakout_shadow_preview_training_set,
)
from backend.services.breakout_replay_learning_alignment import (
    write_breakout_replay_learning_alignment_report,
)
from backend.services.breakout_event_runtime import (
    BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1,
    build_breakout_event_runtime_v1,
)
from backend.services.entry_try_open_entry import _build_semantic_owner_runtime_bundle_v1
from backend.services.storage_compaction import build_entry_decision_hot_payload


def _runtime_row() -> dict:
    return {
        "symbol": "BTCUSD",
        "micro_breakout_readiness_state": "READY_BREAKOUT",
        "micro_swing_high_retest_count_20": 1,
        "transition_forecast_v1": {
            "p_buy_confirm": 0.74,
            "p_sell_confirm": 0.12,
            "p_false_break": 0.22,
            "p_continuation_success": 0.61,
        },
        "response_vector_v2": {
            "breakout_up": 0.78,
            "breakout_down": 0.08,
        },
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.74,
                "false_break_score": 0.22,
                "continuation_score": 0.61,
                "wait_confirm_gap": 0.18,
                "hold_exit_gap": 0.05,
                "decision_hint": "CONFIRM_BIASED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "range",
                "scene_pattern_name": "Morning Consolidation",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {
                "flip_readiness": 0.21,
            }
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {
                "barrier_total": 0.24,
            }
        },
    }


def test_breakout_scope_freeze_contract_separates_runtime_and_replay_fields():
    assert BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["breakout_event_role"] == "action_transition_event_owner"
    assert "breakout_state" in BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["runtime_direct_use_fields"]
    assert "manual_wait_teacher_label" in BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["learning_only_fields"]
    assert "future_favorable_move_ratio" in BREAKOUT_EVENT_SCOPE_FREEZE_CONTRACT_V1["forbidden_runtime_inputs"]


def test_runtime_builder_ignores_manual_and_future_fields():
    row = _runtime_row()
    clean = build_breakout_event_runtime_v1(row)
    polluted = build_breakout_event_runtime_v1(
        {
            **row,
            "manual_wait_teacher_label": "bad_wait_missed_move",
            "future_favorable_move_ratio": 9.9,
            "future_adverse_move_ratio": 0.0,
            "breakout_action_target_v1": {"target": "AVOID_ENTRY"},
        }
    )

    assert clean == polluted
    assert clean["breakout_detected"] is True
    assert clean["breakout_direction"] == "UP"
    assert clean["breakout_state"] in {"breakout_pullback", "breakout_continuation"}


def test_runtime_builder_can_bridge_proxy_breakout_axes():
    row = {
        **_runtime_row(),
        "response_vector_v2": {
            "upper_break_up": 0.76,
            "lower_break_down": 0.06,
            "mid_reclaim_up": 0.18,
            "mid_lose_down": 0.05,
        },
    }

    runtime = build_breakout_event_runtime_v1(row)

    assert runtime["breakout_detected"] is True
    assert runtime["breakout_direction"] == "UP"
    assert runtime["breakout_axis_mode"] == "proxy"
    assert runtime["breakout_axis_bridge_applied"] is True
    assert runtime["breakout_up_source"] == "upper_break_up"
    assert runtime["breakout_down_source"] == "lower_break_down"
    assert runtime["breakout_type_candidate"] == "initial_breakout_candidate"
    assert runtime["selected_axis_family"] == "initial"
    assert runtime["effective_breakout_readiness_state"] == "READY_BREAKOUT"
    assert runtime["breakout_readiness_origin"] == "runtime"


def test_runtime_builder_can_create_surrogate_readiness_state():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.44,
            "lower_break_down": 0.06,
            "mid_reclaim_up": 0.12,
            "mid_lose_down": 0.03,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_score": 0.24,
                "false_break_score": 0.36,
                "continuation_score": 0.28,
                "wait_confirm_gap": -0.02,
            },
        },
    }

    runtime = build_breakout_event_runtime_v1(row)

    assert runtime["breakout_direction"] == "UP"
    assert runtime["effective_breakout_readiness_state"] == "BUILDING_BREAKOUT"
    assert runtime["breakout_readiness_origin"] == "surrogate"
    assert runtime["breakout_type_candidate"] == "initial_breakout_candidate"
    assert runtime["selected_axis_family"] == "initial"
    assert runtime["breakout_state"] == "initial_breakout"


def test_runtime_builder_can_create_coiled_surrogate_from_historical_scale():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.18,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.11,
            "mid_lose_down": 0.02,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.08,
                "false_break_score": 0.17,
                "continuation_score": 0.10,
                "wait_confirm_gap": -0.03,
            },
        },
    }

    runtime = build_breakout_event_runtime_v1(row)

    assert runtime["effective_breakout_readiness_state"] == "BUILDING_BREAKOUT"
    assert runtime["breakout_readiness_origin"] == "surrogate"
    assert runtime["breakout_type_candidate"] == "initial_breakout_candidate"
    assert runtime["breakout_direction"] == "UP"


def test_runtime_builder_splits_reclaim_breakout_from_initial_breakout():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "micro_swing_high_retest_count_20": 2,
        "response_vector_v2": {
            "upper_break_up": 0.18,
            "lower_break_down": 0.07,
            "mid_reclaim_up": 0.41,
            "mid_lose_down": 0.05,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.29,
                "false_break_score": 0.16,
                "continuation_score": 0.24,
                "wait_confirm_gap": 0.01,
            },
        },
    }

    runtime = build_breakout_event_runtime_v1(row)

    assert runtime["breakout_direction"] == "UP"
    assert runtime["breakout_type_candidate"] == "reclaim_breakout_candidate"
    assert runtime["selected_axis_family"] == "reclaim"
    assert runtime["breakout_state"] == "breakout_pullback"


def test_runtime_builder_surfaces_why_none_reason_when_gap_is_too_small():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.34,
            "lower_break_down": 0.32,
            "mid_reclaim_up": 0.05,
            "mid_lose_down": 0.04,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "",
                "confirm_score": 0.18,
                "false_break_score": 0.17,
                "continuation_score": 0.12,
                "wait_confirm_gap": -0.04,
            },
        },
    }

    runtime = build_breakout_event_runtime_v1(row)

    assert runtime["breakout_type_candidate"] == "initial_breakout_candidate"
    assert runtime["breakout_direction"] == "NONE"
    assert runtime["why_none_reason"] in {"gap_too_small", "mixed_axis_conflict"}
    assert runtime["breakout_state"] == "pre_breakout"


def test_overlay_candidates_stay_log_only_and_emit_enter_now():
    row = _runtime_row()
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )
    trace = build_breakout_event_overlay_trace_v1(overlay, symbol="BTCUSD", entry_stage="READY")

    assert BREAKOUT_EVENT_OVERLAY_SCOPE_FREEZE_CONTRACT_V1["overlay_role"] == "log_only_breakout_translation_layer"
    assert overlay["overlay_mode"] == "log_only"
    assert overlay["candidate_action_target"] == BREAKOUT_ACTION_TARGET_ENTER_NOW
    assert trace["actual_policy_unchanged"] is True


def test_overlay_candidates_can_use_surrogate_ready_breakout_entry():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.44,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.18,
            "mid_lose_down": 0.02,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.26,
                "false_break_score": 0.18,
                "continuation_score": 0.31,
                "wait_confirm_gap": 0.01,
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.12},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.22},
        },
    }
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )

    assert breakout["effective_breakout_readiness_state"] == "READY_BREAKOUT"
    assert breakout["breakout_state"] == "initial_breakout"
    assert overlay["candidate_action_target"] == BREAKOUT_ACTION_TARGET_ENTER_NOW
    assert "surrogate_ready_breakout_entry" in overlay["reason_summary"]


def test_overlay_candidates_hold_when_confirm_conflicts_with_direction():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.40,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.15,
            "mid_lose_down": 0.02,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "SELL",
                "confirm_score": 0.20,
                "false_break_score": 0.32,
                "continuation_score": 0.30,
                "wait_confirm_gap": -0.01,
            },
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.24},
        },
    }
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )

    assert breakout["breakout_direction"] == "UP"
    assert breakout["breakout_state"] == "initial_breakout"
    assert overlay["candidate_action_target"] == "PROBE_BREAKOUT"
    assert overlay["conflict_level"] == "confirm_conflict"
    assert overlay["action_demotion_rule"] == "probe_breakout_confirm_conflict"
    assert "probe_breakout" in overlay["reason_summary"]


def test_overlay_candidates_can_probe_supportive_low_confidence_breakout():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.18,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.11,
            "mid_lose_down": 0.02,
        },
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.08,
                "false_break_score": 0.18,
                "continuation_score": 0.10,
                "wait_confirm_gap": -0.03,
            },
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.22},
        },
    }
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )

    assert breakout["breakout_direction"] == "UP"
    assert breakout["breakout_state"] in {"initial_breakout", "breakout_pullback"}
    assert overlay["candidate_action_target"] == "PROBE_BREAKOUT"
    assert "supportive_breakout_probe" in overlay["reason_summary"]


def test_overlay_candidates_demote_barrier_drag_to_watch_breakout():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.22,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.28,
            "mid_lose_down": 0.03,
        },
        "micro_swing_high_retest_count_20": 2,
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.16,
                "false_break_score": 0.34,
                "continuation_score": 0.13,
                "wait_confirm_gap": -0.01,
            },
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.44},
        },
    }
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )

    assert breakout["breakout_direction"] == "UP"
    assert breakout["breakout_state"] in {"initial_breakout", "breakout_pullback"}
    assert overlay["candidate_action_target"] == "WATCH_BREAKOUT"
    assert overlay["conflict_level"] == "barrier_drag"
    assert overlay["action_demotion_rule"] == "watch_breakout_barrier_drag"
    assert "watch_breakout" in overlay["reason_summary"]


def test_overlay_candidates_can_soft_probe_moderate_barrier_drag():
    row = {
        **_runtime_row(),
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.24,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.29,
            "mid_lose_down": 0.03,
        },
        "micro_swing_high_retest_count_20": 2,
        "forecast_state25_runtime_bridge_v1": {
            **_runtime_row()["forecast_state25_runtime_bridge_v1"],
            "forecast_runtime_summary_v1": {
                **_runtime_row()["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                "confirm_side": "BUY",
                "confirm_score": 0.14,
                "false_break_score": 0.22,
                "continuation_score": 0.16,
                "wait_confirm_gap": -0.01,
            },
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.58},
        },
    }
    breakout = build_breakout_event_runtime_v1(row)
    overlay = build_breakout_event_overlay_candidates_v1(
        row,
        breakout_event_runtime_v1=breakout,
        forecast_state25_runtime_bridge_v1=row["forecast_state25_runtime_bridge_v1"],
        belief_state25_runtime_bridge_v1=row["belief_state25_runtime_bridge_v1"],
        barrier_state25_runtime_bridge_v1=row["barrier_state25_runtime_bridge_v1"],
    )

    assert breakout["breakout_direction"] == "UP"
    assert breakout["breakout_state"] in {"initial_breakout", "breakout_pullback"}
    assert overlay["candidate_action_target"] == "PROBE_BREAKOUT"
    assert overlay["conflict_level"] == "barrier_drag"
    assert overlay["action_demotion_rule"] == "probe_breakout_soft_barrier_drag"
    assert "probe_breakout" in overlay["reason_summary"]


def test_replay_alignment_and_action_target_use_manual_truth_only_in_replay_layer():
    alignment = build_breakout_manual_alignment_v1(
        decision_row=_runtime_row(),
        manual_wait_teacher_row={
            "manual_wait_teacher_label": "good_wait_better_entry",
            "manual_wait_teacher_anchor_time": "2026-04-08T09:00:00+09:00",
            "manual_wait_teacher_entry_time": "2026-04-08T09:05:00+09:00",
        },
        future_outcome_row={
            "future_favorable_move_ratio": 0.006,
            "future_adverse_move_ratio": 0.001,
        },
    )
    target = build_breakout_action_target_v1(alignment)

    assert BREAKOUT_EVENT_REPLAY_SCOPE_FREEZE_CONTRACT_V1["replay_role"] == "manual_truth_alignment_and_shadow_target_builder"
    assert alignment["alignment_class"] == "aligned_breakout_entry"
    assert target["target"] == BREAKOUT_ACTION_TARGET_ENTER_NOW
    assert target["provisional_target"] is False


def test_replay_target_can_emit_exit_protect_and_wait_more():
    base_row = _runtime_row()
    exit_alignment = build_breakout_manual_alignment_v1(
        decision_row={
            **base_row,
            "forecast_state25_runtime_bridge_v1": {
                **base_row["forecast_state25_runtime_bridge_v1"],
                "forecast_runtime_summary_v1": {
                    **base_row["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                    "hold_exit_gap": -0.18,
                },
            },
        },
        manual_wait_teacher_row={
            "manual_wait_teacher_label": "good_wait_protective_exit",
        },
    )
    wait_alignment = build_breakout_manual_alignment_v1(
        decision_row={
            **base_row,
            "micro_breakout_readiness_state": "",
            "response_vector_v2": {"breakout_up": 0.0, "breakout_down": 0.0},
            "forecast_state25_runtime_bridge_v1": {
                **base_row["forecast_state25_runtime_bridge_v1"],
                "forecast_runtime_summary_v1": {
                    **base_row["forecast_state25_runtime_bridge_v1"]["forecast_runtime_summary_v1"],
                    "confirm_score": 0.10,
                    "continuation_score": 0.05,
                    "wait_confirm_gap": -0.22,
                },
            },
        },
        manual_wait_teacher_row={
            "manual_wait_teacher_label": "good_wait_better_entry",
        },
    )

    assert build_breakout_action_target_v1(exit_alignment)["target"] == BREAKOUT_ACTION_TARGET_EXIT_PROTECT
    assert build_breakout_action_target_v1(wait_alignment)["target"] == BREAKOUT_ACTION_TARGET_WAIT_MORE


def test_phase0_report_documents_single_runtime_injection_point():
    report = build_breakout_event_phase0_report_v1()
    markdown = render_breakout_event_phase0_markdown(report)

    assert report["single_runtime_injection_point"] == "backend/services/entry_try_open_entry.py"
    assert "breakout_event_runtime_v1" in markdown
    assert "No-Leakage" in markdown


def test_phase1_bundle_wires_breakout_fields_into_detail_only_payload():
    row = _runtime_row()
    bundle = _build_semantic_owner_runtime_bundle_v1(
        runtime_snapshot_row=row,
        symbol="BTCUSD",
        action="BUY",
        setup_id="breakout_retest_buy",
        setup_side="BUY",
        entry_session_name="LONDON",
        wait_state=None,
        entry_wait_decision="observe_only",
        score=61.0,
        contra_score=12.0,
        prediction_bundle=None,
        shadow_transition_forecast_v1=row["transition_forecast_v1"],
        shadow_trade_management_forecast_v1={
            "p_continue_favor": 0.62,
            "p_fail_now": 0.19,
            "metadata": {"mapper_version": "management_mapper_v1"},
        },
        shadow_observe_confirm=None,
        entry_stage="READY",
        actual_effective_entry_threshold=45.0,
        actual_size_multiplier=1.0,
        state25_candidate_runtime_state={},
    )

    detail_fields = bundle["detail_fields"]
    payload = {
        **row,
        **bundle["flat_fields"],
        **detail_fields,
    }
    hot = build_entry_decision_hot_payload(payload, detail_row_key="breakout-detail")

    assert detail_fields["breakout_event_runtime_v1"]["breakout_detected"] is True
    assert detail_fields["breakout_event_overlay_candidates_v1"]["overlay_mode"] == "log_only"
    assert detail_fields["breakout_event_overlay_trace_v1"]["actual_policy_unchanged"] is True
    assert "breakout_event_runtime_v1" not in hot
    assert "breakout_event_overlay_candidates_v1" not in hot
    assert "breakout_event_overlay_trace_v1" not in hot


def test_manual_alignment_report_builds_matched_breakout_rows():
    base_row = _runtime_row()
    report = build_breakout_manual_alignment_report_v1(
        entry_decision_rows=[
            {
                **base_row,
                "time": "2026-04-08T09:00:30+09:00",
                "signal_bar_ts": 1775606430,
                "entry_wait_decision": "wait_for_breakout",
                "entry_wait_state": "NEED_RETEST",
                "observe_reason": "range_breakout_probe_observe",
                "decision_row_key": "decision-1",
            }
        ],
        manual_rows=[
            {
                "annotation_id": "anno-1",
                "episode_id": "episode-1",
                "symbol": "BTCUSD",
                "anchor_side": "BUY",
                "anchor_time": "2026-04-08T09:00:00+09:00",
                "anchor_price": 100.0,
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "review_status": "accepted_coarse",
            }
        ],
        future_bar_rows=[
            {"symbol": "BTCUSD", "time": "2026-04-08T09:01:00+09:00", "high": 100.6, "low": 99.9, "close": 100.4},
            {"symbol": "BTCUSD", "time": "2026-04-08T09:02:00+09:00", "high": 100.8, "low": 100.1, "close": 100.7},
        ],
        accepted_only=True,
        match_tolerance_sec=90.0,
        max_future_bars=4,
    )
    markdown = render_breakout_manual_alignment_markdown(report)

    coverage = report["coverage"]
    row = report["rows"][0]

    assert coverage["manual_row_count"] == 1
    assert coverage["matched_decision_count"] == 1
    assert coverage["aligned_count"] == 1
    assert row["match_status"] == "matched"
    assert row["alignment_class"] == "missed_breakout"
    assert row["target"] == "ENTER_NOW"
    assert "Breakout Manual Alignment Report" in markdown


def test_breakout_overlap_recovery_queue_suggests_backfill_and_new_manual_windows():
    rows, summary = build_breakout_manual_overlap_recovery_queue(
        entry_rows=[
            {"symbol": "BTCUSD", "time": "2026-04-07T00:00:44+09:00"},
            {"symbol": "BTCUSD", "time": "2026-04-07T00:12:10+09:00"},
        ],
        manual_rows=[
            {
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T08:58:00+09:00",
                "manual_wait_teacher_label": "good_wait_protective_exit",
                "review_status": "accepted_coarse",
            },
            {
                "symbol": "BTCUSD",
                "anchor_time": "2026-04-06T09:17:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "review_status": "accepted_coarse",
            },
        ],
        review_window_minutes=90,
    )

    assert summary["queue_count"] == 2
    recovery_types = {row["recovery_type"] for row in rows}
    assert "replay_backfill_entry_decisions" in recovery_types
    assert "collect_new_manual_overlap" in recovery_types


def test_breakout_manual_seed_draft_builds_rows_from_collect_windows():
    queue = pd.DataFrame(
        [
            {
                "queue_id": "breakout_recovery::BTCUSD::collect_new_manual",
                "symbol": "BTCUSD",
                "recovery_type": "collect_new_manual_overlap",
                "window_start": "2026-04-07T00:00:44",
                "window_end": "2026-04-07T01:30:44",
            }
        ]
    )
    entry = pd.DataFrame(
        [
            {
                "decision_row_key": "row-1",
                "symbol": "BTCUSD",
                "time": "2026-04-07T00:10:00",
                "outcome": "wait",
                "action": "",
                "observe_reason": "range_breakout_probe_observe",
                "entry_wait_decision": "wait_for_breakout",
                "consumer_check_side": "BUY",
                "setup_side": "BUY",
                "core_allowed_action": "BUY_ONLY",
                "micro_breakout_readiness_state": "READY_BREAKOUT",
                "forecast_state25_candidate_wait_bias_action": "reinforce_wait_bias",
            }
        ]
    )
    entry["time_parsed"] = pd.to_datetime(entry["time"])
    detail_hints = pd.DataFrame(
        [
            {
                "decision_row_key": "row-1",
                "breakout_detected": True,
                "breakout_state": "initial_breakout",
                "breakout_direction": "UP",
                "breakout_candidate_action_target": "ENTER_NOW",
            }
        ]
    )

    draft = build_breakout_manual_overlap_seed_draft(
        queue,
        entry_decisions=entry,
        detail_hints=detail_hints,
    )

    assert len(draft) == 1
    row = draft.iloc[0].to_dict()
    assert row["symbol"] == "BTCUSD"
    assert row["manual_wait_teacher_label"] == "bad_wait_missed_move"
    assert row["anchor_side"] == "BUY"
    assert row["annotation_source"] == "assistant_breakout_overlap_seed"


def test_breakout_manual_seed_draft_appends_review_only_cases():
    review_entries = pd.DataFrame(
        [
            {
                "annotation_id": "nas_breakout_chart_20260408_001",
                "episode_id": "nas_breakout_chart_20260408_001",
                "symbol": "NAS100",
                "timeframe": "M1",
                "anchor_side": "BUY",
                "scene_id": "nas_breakout_chart_case",
                "chart_context": "screenshot_case",
                "box_regime_scope": "upper_box_breakout",
                "anchor_time": "2026-04-08T06:44:00+09:00",
                "anchor_price": 24960.0,
                "ideal_entry_time": "2026-04-08T06:52:00+09:00",
                "ideal_entry_price": 24976.0,
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "manual_wait_teacher_confidence": "low",
                "ideal_exit_time": "2026-04-08T07:18:00+09:00",
                "ideal_exit_price": 25018.0,
                "barrier_main_label_hint": "enter_now",
                "wait_outcome_reason_summary": "screenshot inferred",
                "annotation_note": "review only",
                "annotation_author": "codex",
                "annotation_created_at": "2026-04-08T18:05:00+09:00",
                "annotation_source": "assistant_breakout_chart_inferred",
                "review_status": "needs_manual_recheck",
                "revisit_flag": 1,
                "manual_teacher_confidence": "low",
                "label_version": "manual_wait_teacher_v1",
            }
        ]
    )

    draft = build_breakout_manual_overlap_seed_draft(
        pd.DataFrame(),
        review_entries=review_entries,
    )

    assert len(draft) == 1
    row = draft.iloc[0].to_dict()
    assert row["episode_id"] == "nas_breakout_chart_20260408_001"
    assert row["annotation_source"] == "assistant_breakout_chart_inferred"
    assert row["manual_wait_teacher_label"] == "bad_wait_missed_move"


def test_breakout_backfill_runner_scaffold_materializes_scoped_bundle(tmp_path):
    project_root = Path(tmp_path)
    trades_root = project_root / "data" / "trades"
    analysis_root = project_root / "data" / "analysis" / "breakout_event"
    manual_root = project_root / "data" / "manual_annotations"
    bundle_root = project_root / "data" / "backfill" / "breakout_event"
    trades_root.mkdir(parents=True)
    analysis_root.mkdir(parents=True)
    manual_root.mkdir(parents=True)

    legacy_csv = trades_root / "entry_decisions.legacy_20260403_103545.csv"
    legacy_detail = trades_root / "entry_decisions.legacy_20260403_103545.detail.jsonl"
    fieldnames = ["time", "symbol", "decision_row_key", "signal_bar_ts", "action", "outcome"]
    with legacy_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "time": "2026-04-03T07:20:00",
                "symbol": "NAS100",
                "decision_row_key": "nas-row-1",
                "signal_bar_ts": "1775168400",
                "action": "",
                "outcome": "wait",
            }
        )
        writer.writerow(
            {
                "time": "2026-04-03T07:26:00",
                "symbol": "NAS100",
                "decision_row_key": "nas-row-2",
                "signal_bar_ts": "1775168760",
                "action": "",
                "outcome": "wait",
            }
        )
        writer.writerow(
            {
                "time": "2026-04-03T07:30:00",
                "symbol": "NAS100",
                "decision_row_key": "nas-row-3",
                "signal_bar_ts": "1775169000",
                "action": "",
                "outcome": "wait",
            }
        )
    legacy_detail.write_text(
        "\n".join(
                [
                    json.dumps({"payload": {"decision_row_key": "nas-row-1", "breakout_event_runtime_v1": {"breakout_detected": True}}}),
                    json.dumps({"payload": {"decision_row_key": "nas-row-2", "breakout_event_runtime_v1": {"breakout_detected": True}}}),
                    json.dumps({"payload": {"decision_row_key": "nas-row-3", "breakout_event_runtime_v1": {"breakout_detected": True}}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    manual_csv = manual_root / "manual_wait_teacher_annotations.csv"
    with manual_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["annotation_id", "episode_id", "symbol", "anchor_time", "manual_wait_teacher_label", "review_status"])
        writer.writeheader()
        writer.writerow(
            {
                "annotation_id": "m1",
                "episode_id": "m1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-03T07:21:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "review_status": "accepted_coarse",
            }
        )

    queue_csv = analysis_root / "breakout_manual_overlap_recovery_latest.csv"
    with queue_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "queue_id",
                "symbol",
                "recovery_type",
                "priority",
                "window_start",
                "window_end",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "queue_id": "breakout_recovery::NAS100::replay_backfill",
                "symbol": "NAS100",
                "recovery_type": "replay_backfill_entry_decisions",
                "priority": "high",
                "window_start": "2026-04-03T07:20:00",
                "window_end": "2026-04-03T07:30:00",
            }
        )

    closed_csv = trades_root / "trade_closed_history.csv"
    closed_csv.write_text("ticket,symbol\n", encoding="utf-8-sig")

    payload = write_breakout_backfill_runner_scaffold(
        queue_path=queue_csv,
        secondary_queue_path=analysis_root / "missing_secondary_queue.csv",
        manual_path=manual_csv,
        supplemental_manual_path=manual_root / "missing_review_entries.csv",
        trades_root=trades_root,
        closed_trades_path=closed_csv,
        bundle_root=bundle_root,
        csv_output_path=analysis_root / "runner.csv",
        json_output_path=analysis_root / "runner.json",
        md_output_path=analysis_root / "runner.md",
    )

    assert payload["summary"]["job_count"] == 1
    row = payload["rows"][0]
    assert row["coverage_state"] == "full_internal_source"
    assert row["scoped_entry_row_count"] == 3
    assert row["scoped_detail_row_count"] == 3
    assert row["manual_anchor_rows"] == 1
    assert Path(row["runner_script_path"]).exists()
    assert (bundle_root / "run_all_breakout_backfill_jobs_latest.ps1").exists()


def test_breakout_manual_learning_bridge_keeps_review_only_cases_and_targets():
    merged = merge_breakout_manual_sources(
        pd.DataFrame(
            [
                {
                    "annotation_id": "base-1",
                    "episode_id": "base-1",
                    "symbol": "BTCUSD",
                    "timeframe": "M1",
                    "anchor_side": "BUY",
                    "anchor_time": "2026-04-07T00:10:00+09:00",
                    "manual_wait_teacher_label": "good_wait_better_entry",
                    "review_status": "accepted_coarse",
                    "annotation_source": "chart_annotated",
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "annotation_id": "review-1",
                    "episode_id": "review-1",
                    "symbol": "NAS100",
                    "timeframe": "M1",
                    "anchor_side": "BUY",
                    "scene_id": "first_pullback_reclaim",
                    "anchor_time": "2026-04-08T07:44:00+09:00",
                    "manual_wait_teacher_label": "good_wait_better_entry",
                    "review_status": "needs_manual_recheck",
                    "annotation_source": "assistant_breakout_chart_inferred",
                }
            ]
        ),
    )
    report = build_breakout_manual_learning_bridge(
        entry_decision_rows=[],
        manual_rows=merged.to_dict("records"),
        match_tolerance_sec=300.0,
    )

    assert report["summary"]["row_count"] == 2
    review_row = [row for row in report["rows"] if row["episode_id"] == "review-1"][0]
    assert review_row["coverage_state"] == "manual_only_review_case"
    assert review_row["action_target"] == "ENTER_NOW"
    assert review_row["continuation_target"] == "PULLBACK_THEN_CONTINUE"
    assert review_row["ideal_entry_time"] == ""


def test_breakout_manual_learning_recovery_merges_overlapping_review_cases():
    rows, summary = build_breakout_manual_learning_recovery_queue(
        [
            {
                "episode_id": "nas-review-1",
                "symbol": "NAS100",
                "coverage_state": "manual_only_review_case",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "ideal_entry_time": "2026-04-08T06:56:00+09:00",
                "ideal_exit_time": "2026-04-08T08:04:00+09:00",
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
            },
            {
                "episode_id": "nas-review-2",
                "symbol": "NAS100",
                "coverage_state": "manual_only_review_case",
                "anchor_time": "2026-04-08T07:44:00+09:00",
                "ideal_entry_time": "2026-04-08T07:58:00+09:00",
                "ideal_exit_time": "2026-04-08T09:04:00+09:00",
                "action_target": "ENTER_NOW",
                "continuation_target": "PULLBACK_THEN_CONTINUE",
            },
            {
                "episode_id": "nas-review-3",
                "symbol": "NAS100",
                "coverage_state": "manual_only_review_case",
                "anchor_time": "2026-04-08T11:22:00+09:00",
                "ideal_entry_time": "2026-04-08T11:28:00+09:00",
                "ideal_exit_time": "2026-04-08T11:38:00+09:00",
                "action_target": "EXIT_PROTECT",
                "continuation_target": "CONTINUE_THEN_PROTECT",
            },
        ]
    )

    assert summary["queue_count"] == 2
    assert rows[0]["source_case_count"] == 2
    assert rows[0]["source_episode_ids"] == "nas-review-1|nas-review-2"
    assert rows[0]["source_action_targets"] == "ENTER_NOW"


def test_backfill_scaffold_uses_secondary_review_queue_and_supplemental_manual(tmp_path):
    project_root = Path(tmp_path)
    trades_root = project_root / "data" / "trades"
    analysis_root = project_root / "data" / "analysis" / "breakout_event"
    manual_root = project_root / "data" / "manual_annotations"
    bundle_root = project_root / "data" / "backfill" / "breakout_event"
    trades_root.mkdir(parents=True)
    analysis_root.mkdir(parents=True)
    manual_root.mkdir(parents=True)

    current_csv = trades_root / "entry_decisions.csv"
    with current_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "symbol", "decision_row_key", "signal_bar_ts", "action", "outcome"])
        writer.writeheader()
        writer.writerow(
            {
                "time": "2026-04-08T06:40:00",
                "symbol": "BTCUSD",
                "decision_row_key": "btc-row-1",
                "signal_bar_ts": "1775611200",
                "action": "",
                "outcome": "wait",
            }
        )

    primary_queue_csv = analysis_root / "breakout_manual_overlap_recovery_latest.csv"
    primary_queue_csv.write_text("queue_id,symbol,recovery_type,priority,window_start,window_end\n", encoding="utf-8-sig")

    secondary_queue_csv = analysis_root / "breakout_manual_learning_recovery_latest.csv"
    with secondary_queue_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["queue_id", "symbol", "recovery_type", "priority", "window_start", "window_end"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "queue_id": "breakout_learning_recovery::NAS100::review",
                "symbol": "NAS100",
                "recovery_type": "replay_backfill_entry_decisions",
                "priority": "high",
                "window_start": "2026-04-08T06:35:00",
                "window_end": "2026-04-08T09:19:00",
            }
        )

    manual_csv = manual_root / "manual_wait_teacher_annotations.csv"
    with manual_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["annotation_id", "episode_id", "symbol", "anchor_time", "manual_wait_teacher_label", "review_status"])
        writer.writeheader()

    supplemental_manual_csv = manual_root / "breakout_manual_overlap_seed_review_entries.csv"
    with supplemental_manual_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["annotation_id", "episode_id", "symbol", "anchor_time", "manual_wait_teacher_label", "review_status"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "annotation_id": "review-1",
                "episode_id": "review-1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-08T07:44:00+09:00",
                "manual_wait_teacher_label": "good_wait_better_entry",
                "review_status": "needs_manual_recheck",
            }
        )

    closed_csv = trades_root / "trade_closed_history.csv"
    closed_csv.write_text("ticket,symbol\n", encoding="utf-8-sig")

    payload = write_breakout_backfill_runner_scaffold(
        queue_path=primary_queue_csv,
        secondary_queue_path=secondary_queue_csv,
        manual_path=manual_csv,
        supplemental_manual_path=supplemental_manual_csv,
        trades_root=trades_root,
        closed_trades_path=closed_csv,
        bundle_root=bundle_root,
        csv_output_path=analysis_root / "runner.csv",
        json_output_path=analysis_root / "runner.json",
        md_output_path=analysis_root / "runner.md",
    )

    assert payload["summary"]["job_count"] == 1
    row = payload["rows"][0]
    assert row["recovery_type"] == "replay_backfill_entry_decisions"
    assert row["coverage_state"] == "no_internal_source"
    assert row["scoped_entry_row_count"] == 0
    assert row["manual_anchor_rows"] == 1


def test_breakout_external_source_priority_reports_full_and_gap_requests(tmp_path):
    bundle_root = Path(tmp_path) / "data" / "backfill" / "breakout_event"
    jobs_root = bundle_root / "jobs"
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    jobs_root.mkdir(parents=True)
    analysis_root.mkdir(parents=True)

    no_internal_dir = jobs_root / "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00"
    no_internal_dir.mkdir()
    (no_internal_dir / "breakout_backfill_job_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00",
                "queue_id": "breakout_learning_recovery::NAS100::2026-04-08T06_15_00::2026-04-08T08_19_00",
                "symbol": "NAS100",
                "priority": "high",
                "recovery_type": "replay_backfill_entry_decisions",
                "window_start": "2026-04-08T06:15:00",
                "window_end": "2026-04-08T08:19:00",
                "coverage_state": "no_internal_source",
                "coverage_gaps": [{"gap_start": "2026-04-08T06:15:00", "gap_end": "2026-04-08T08:19:00"}],
                "manual_anchor_rows": 2,
                "scoped_entry_row_count": 0,
                "ready_for_replay_execution": False,
                "external_source_required": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    partial_dir = jobs_root / "nas100_2026_04_03t07_11_00_2026_04_06t09_07_00"
    partial_dir.mkdir()
    (partial_dir / "breakout_backfill_job_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "nas100_2026_04_03t07_11_00_2026_04_06t09_07_00",
                "queue_id": "breakout_recovery::NAS100::replay_backfill",
                "symbol": "NAS100",
                "priority": "high",
                "recovery_type": "replay_backfill_entry_decisions",
                "window_start": "2026-04-03T07:11:00",
                "window_end": "2026-04-06T09:07:00",
                "coverage_state": "partial_internal_source",
                "coverage_gaps": [{"gap_start": "2026-04-03T07:11:00", "gap_end": "2026-04-03T10:35:45"}],
                "manual_anchor_rows": 25,
                "scoped_entry_row_count": 5147,
                "ready_for_replay_execution": True,
                "external_source_required": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    scaffold_csv = analysis_root / "breakout_backfill_runner_scaffold_latest.csv"
    with scaffold_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["queue_id", "manual_anchor_rows"],
        )
        writer.writeheader()
        writer.writerow({"queue_id": "breakout_recovery::NAS100::replay_backfill", "manual_anchor_rows": 25})

    payload = write_breakout_external_source_priority_report(
        bundle_root=bundle_root,
        scaffold_csv_path=scaffold_csv,
        csv_output_path=analysis_root / "priority.csv",
        json_output_path=analysis_root / "priority.json",
        markdown_output_path=analysis_root / "priority.md",
    )

    assert payload["summary"]["row_count"] == 2
    scopes = {row["request_scope"] for row in payload["rows"]}
    assert scopes == {"full_window", "gap_only"}
    assert all(Path(row["request_manifest_path"]).exists() for row in payload["rows"])
    assert all(Path(row["request_markdown_path"]).exists() for row in payload["rows"])


def test_breakout_replay_learning_alignment_matches_manual_case_to_replay_row(tmp_path):
    project_root = Path(tmp_path)
    analysis_root = project_root / "data" / "analysis" / "breakout_event"
    jobs_root = project_root / "data" / "backfill" / "breakout_event" / "jobs"
    analysis_root.mkdir(parents=True)
    jobs_root.mkdir(parents=True)

    learning_csv = analysis_root / "breakout_manual_learning_bridge_latest.csv"
    with learning_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "episode_id",
                "symbol",
                "anchor_time",
                "ideal_entry_time",
                "ideal_exit_time",
                "review_status",
                "annotation_source",
                "coverage_state",
                "action_target",
                "continuation_target",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "episode_id": "nas-breakout-1",
                "symbol": "NAS100",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "ideal_entry_time": "2026-04-08T06:56:00+09:00",
                "ideal_exit_time": "2026-04-08T08:04:00+09:00",
                "review_status": "needs_manual_recheck",
                "annotation_source": "assistant_breakout_chart_inferred",
                "coverage_state": "manual_only_review_case",
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
            }
        )

    job_dir = jobs_root / "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00"
    replay_dir = job_dir / "replay_dataset"
    replay_dir.mkdir(parents=True)
    scoped_entry_csv = job_dir / "entry_decisions_scoped.csv"
    with scoped_entry_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["time", "action", "outcome", "setup_id", "observe_reason", "blocked_by", "decision_row_key"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "time": "2026-04-08T06:57:00",
                "action": "BUY",
                "outcome": "entered",
                "setup_id": "breakout_reclaim_buy",
                "observe_reason": "upper_box_breakout_confirm",
                "blocked_by": "",
                "decision_row_key": "replay-key-1",
            }
        )

    replay_path = replay_dir / "replay_dataset_rows_20260408_193740.jsonl"
    replay_path.write_text(
        json.dumps(
            {
                "decision_row_key": "replay-key-1",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "decision_row": {
                    "time": "2026-04-08T06:57:00",
                    "action": "BUY",
                    "outcome": "entered",
                    "setup_id": "breakout_reclaim_buy",
                    "observe_reason": "upper_box_breakout_confirm",
                    "blocked_by": "",
                },
                "label_quality_summary_v1": {
                    "transition": {
                        "forecast_probabilities": {
                            "p_buy_confirm": 0.72,
                            "p_continuation_success": 0.61,
                            "p_false_break": 0.11,
                        },
                        "forecast_vs_outcome_v1": {
                            "summary": {"hit_rate": 0.8},
                            "evaluations": {
                                "p_buy_confirm": {"actual_positive": True},
                                "p_continuation_success": {"actual_positive": True},
                                "p_false_break": {"actual_positive": False},
                            },
                        },
                    },
                    "management": {
                        "forecast_probabilities": {
                            "p_continue_favor": 0.67,
                            "p_fail_now": 0.09,
                            "p_opposite_edge_reach": 0.58,
                        },
                        "forecast_vs_outcome_v1": {
                            "summary": {"hit_rate": 1.0},
                            "evaluations": {
                                "p_continue_favor": {"actual_positive": True},
                                "p_fail_now": {"actual_positive": False},
                                "p_opposite_edge_reach": {"actual_positive": True},
                            },
                        },
                    },
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    scaffold_csv = analysis_root / "breakout_backfill_runner_scaffold_latest.csv"
    with scaffold_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["job_id", "queue_id", "symbol", "window_start", "window_end", "job_dir", "manual_anchor_rows"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "job_id": "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00",
                "queue_id": "breakout_learning_recovery::NAS100::2026-04-08T06_15_00::2026-04-08T08_19_00",
                "symbol": "NAS100",
                "window_start": "2026-04-08T06:15:00",
                "window_end": "2026-04-08T08:19:00",
                "job_dir": str(job_dir),
                "manual_anchor_rows": 2,
            }
        )

    payload = write_breakout_replay_learning_alignment_report(
        learning_bridge_path=learning_csv,
        scaffold_csv_path=scaffold_csv,
        csv_output_path=analysis_root / "replay_learning_alignment.csv",
        json_output_path=analysis_root / "replay_learning_alignment.json",
        markdown_output_path=analysis_root / "replay_learning_alignment.md",
        tolerance_minutes=20,
    )

    assert payload["summary"]["matched_count"] == 1
    row = payload["rows"][0]
    assert row["match_status"] == "matched"
    assert row["matched_job_id"] == "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00"
    assert row["setup_id"] == "breakout_reclaim_buy"
    assert row["actual_continuation_success"] == "1"
    assert row["actual_false_break"] == "0"


def test_breakout_aligned_training_seed_promotes_only_strict_and_good_matches(tmp_path):
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    analysis_root.mkdir(parents=True)
    alignment_csv = analysis_root / "breakout_replay_learning_alignment_latest.csv"
    with alignment_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "episode_id",
                "symbol",
                "match_status",
                "time_gap_sec",
                "action_target",
                "continuation_target",
                "transition_label_status",
                "management_label_status",
            ],
        )
        writer.writeheader()
        writer.writerow({"episode_id": "strict", "symbol": "NAS100", "match_status": "matched", "time_gap_sec": "12", "action_target": "ENTER_NOW", "continuation_target": "CONTINUE_AFTER_BREAK", "transition_label_status": "VALID", "management_label_status": "VALID"})
        writer.writerow({"episode_id": "good", "symbol": "BTCUSD", "match_status": "matched", "time_gap_sec": "240", "action_target": "EXIT_PROTECT", "continuation_target": "CONTINUE_THEN_PROTECT", "transition_label_status": "VALID", "management_label_status": "VALID"})
        writer.writerow({"episode_id": "coarse", "symbol": "XAUUSD", "match_status": "matched", "time_gap_sec": "600", "action_target": "WAIT_MORE", "continuation_target": "WAIT_OR_UNCLEAR", "transition_label_status": "VALID", "management_label_status": "VALID"})

    payload = write_breakout_aligned_training_seed_report(
        alignment_csv_path=alignment_csv,
        csv_output_path=analysis_root / "seed.csv",
        json_output_path=analysis_root / "seed.json",
        markdown_output_path=analysis_root / "seed.md",
    )

    assert payload["summary"]["promoted_count"] == 2
    promoted = [row for row in payload["rows"] if row["promote_to_training"]]
    assert {row["episode_id"] for row in promoted} == {"strict", "good"}


def test_breakout_replay_time_correction_suggests_shifted_manual_times(tmp_path):
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    jobs_root = Path(tmp_path) / "data" / "backfill" / "breakout_event" / "jobs"
    analysis_root.mkdir(parents=True)
    jobs_root.mkdir(parents=True)

    alignment_csv = analysis_root / "breakout_replay_learning_alignment_latest.csv"
    with alignment_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "episode_id",
                "symbol",
                "coverage_state",
                "action_target",
                "continuation_target",
                "matched_job_id",
                "match_status",
                "reason_summary",
                "anchor_time",
                "ideal_entry_time",
                "ideal_exit_time",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "episode_id": "nas-gap",
                "symbol": "NAS100",
                "coverage_state": "manual_unmatched",
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
                "matched_job_id": "nas-job",
                "match_status": "unmatched",
                "reason_summary": "no_replay_row_within_tolerance",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "ideal_entry_time": "2026-04-08T06:56:00+09:00",
                "ideal_exit_time": "2026-04-08T08:04:00+09:00",
            }
        )

    job_dir = jobs_root / "nas-job"
    job_dir.mkdir()
    scoped_entry_csv = job_dir / "entry_decisions_scoped.csv"
    with scoped_entry_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "action", "outcome", "setup_id", "observe_reason", "blocked_by"])
        writer.writeheader()
        writer.writerow({"time": "2026-04-08T07:06:00", "action": "BUY", "outcome": "entered", "setup_id": "breakout_reclaim_buy", "observe_reason": "upper_box_breakout_confirm", "blocked_by": ""})

    scaffold_csv = analysis_root / "breakout_backfill_runner_scaffold_latest.csv"
    with scaffold_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["job_id", "job_dir"])
        writer.writeheader()
        writer.writerow({"job_id": "nas-job", "job_dir": str(job_dir)})

    payload = write_breakout_replay_time_correction_report(
        alignment_csv_path=alignment_csv,
        scaffold_csv_path=scaffold_csv,
        csv_output_path=analysis_root / "correction.csv",
        json_output_path=analysis_root / "correction.json",
        markdown_output_path=analysis_root / "correction.md",
        coarse_tolerance_seconds=1800,
        review_tolerance_seconds=7200,
    )

    assert payload["summary"]["auto_retime_candidate_count"] == 1
    row = payload["rows"][0]
    assert row["coarse_match_status"] == "auto_retime_candidate"
    assert row["suggested_entry_time"] == "2026-04-08T07:06:00"


def test_breakout_alignment_gap_recovery_groups_missing_job_windows(tmp_path):
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    analysis_root.mkdir(parents=True)
    alignment_csv = analysis_root / "breakout_replay_learning_alignment_latest.csv"
    with alignment_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "episode_id",
                "symbol",
                "action_target",
                "continuation_target",
                "reason_summary",
                "anchor_time",
                "ideal_entry_time",
                "ideal_exit_time",
            ],
        )
        writer.writeheader()
        writer.writerow({"episode_id": "nas-1", "symbol": "NAS100", "action_target": "ENTER_NOW", "continuation_target": "CONTINUE_AFTER_BREAK", "reason_summary": "no_replay_job_window_for_manual_case", "anchor_time": "2026-04-08T06:50:00+09:00", "ideal_entry_time": "2026-04-08T06:56:00+09:00", "ideal_exit_time": "2026-04-08T08:04:00+09:00"})
        writer.writerow({"episode_id": "nas-2", "symbol": "NAS100", "action_target": "ENTER_NOW", "continuation_target": "PULLBACK_THEN_CONTINUE", "reason_summary": "no_replay_job_window_for_manual_case", "anchor_time": "2026-04-08T07:44:00+09:00", "ideal_entry_time": "2026-04-08T07:58:00+09:00", "ideal_exit_time": "2026-04-08T09:04:00+09:00"})

    payload = write_breakout_alignment_gap_recovery_report(
        alignment_csv_path=alignment_csv,
        csv_output_path=analysis_root / "gap.csv",
        json_output_path=analysis_root / "gap.json",
        markdown_output_path=analysis_root / "gap.md",
    )

    assert payload["summary"]["queue_count"] == 1
    row = payload["rows"][0]
    assert row["symbol"] == "NAS100"
    assert row["source_case_count"] == 2
    assert row["source_episode_ids"] == "nas-1|nas-2"


def test_breakout_external_source_priority_writes_manual_target_bundle(tmp_path):
    bundle_root = Path(tmp_path) / "data" / "backfill" / "breakout_event"
    jobs_root = bundle_root / "jobs"
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    jobs_root.mkdir(parents=True)
    analysis_root.mkdir(parents=True)

    job_dir = jobs_root / "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00"
    job_dir.mkdir()
    manual_subset = job_dir / "manual_anchor_subset.csv"
    with manual_subset.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["episode_id", "scene_id", "chart_context", "anchor_time", "ideal_entry_time", "ideal_exit_time", "manual_wait_teacher_label", "review_status"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "episode_id": "nas_breakout_chart_20260408_001",
                "scene_id": "nas_breakout_chart_20260408_open_box_release",
                "chart_context": "screenshot_nas_breakout_case_20260408",
                "anchor_time": "2026-04-08T06:50:00+09:00",
                "ideal_entry_time": "2026-04-08T06:56:00+09:00",
                "ideal_exit_time": "2026-04-08T08:04:00+09:00",
                "manual_wait_teacher_label": "bad_wait_missed_move",
                "review_status": "needs_manual_recheck",
            }
        )

    (job_dir / "breakout_backfill_job_manifest.json").write_text(
        json.dumps(
            {
                "job_id": "nas100_2026_04_08t06_15_00_2026_04_08t08_19_00",
                "queue_id": "breakout_learning_recovery::NAS100::2026-04-08T06_15_00::2026-04-08T08_19_00",
                "symbol": "NAS100",
                "priority": "high",
                "recovery_type": "replay_backfill_entry_decisions",
                "window_start": "2026-04-08T06:15:00",
                "window_end": "2026-04-08T08:19:00",
                "coverage_state": "no_internal_source",
                "coverage_gaps": [{"gap_start": "2026-04-08T06:15:00", "gap_end": "2026-04-08T08:19:00"}],
                "manual_anchor_rows": 1,
                "scoped_entry_row_count": 0,
                "ready_for_replay_execution": False,
                "external_source_required": True,
                "manual_anchor_subset_path": str(manual_subset),
                "replay_command": "python build_replay_dataset.py --symbol NAS100",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    scaffold_csv = analysis_root / "breakout_backfill_runner_scaffold_latest.csv"
    with scaffold_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["queue_id", "manual_anchor_rows"])
        writer.writeheader()
        writer.writerow({"queue_id": "breakout_learning_recovery::NAS100::2026-04-08T06_15_00::2026-04-08T08_19_00", "manual_anchor_rows": 1})

    payload = write_breakout_external_source_priority_report(
        bundle_root=bundle_root,
        scaffold_csv_path=scaffold_csv,
        csv_output_path=analysis_root / "priority.csv",
        json_output_path=analysis_root / "priority.json",
        markdown_output_path=analysis_root / "priority.md",
    )

    row = payload["rows"][0]
    assert "nas_breakout_chart_20260408_001" in row["source_episode_ids"]
    assert Path(row["manual_targets_path"]).exists()
    assert "Replay Command" in Path(row["request_markdown_path"]).read_text(encoding="utf-8")


def test_breakout_shadow_preview_training_set_exports_three_dataset_families(tmp_path):
    analysis_root = Path(tmp_path) / "data" / "analysis" / "breakout_event"
    shadow_root = Path(tmp_path) / "data" / "analysis" / "shadow_auto"
    dataset_root = Path(tmp_path) / "data" / "datasets" / "breakout_shadow_preview"
    analysis_root.mkdir(parents=True)
    shadow_root.mkdir(parents=True)

    seed_csv = analysis_root / "breakout_aligned_training_seed_latest.csv"
    with seed_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "episode_id",
                "symbol",
                "action_target",
                "continuation_target",
                "matched_job_id",
                "matched_decision_time",
                "seed_grade",
                "promote_to_training",
                "transition_label_status",
                "management_label_status",
                "transition_hit_rate",
                "management_hit_rate",
                "p_buy_confirm",
                "actual_buy_confirm",
                "p_continuation_success",
                "actual_continuation_success",
                "p_false_break",
                "actual_false_break",
                "p_continue_favor",
                "actual_continue_favor",
                "p_fail_now",
                "actual_fail_now",
                "p_opposite_edge_reach",
                "actual_opposite_edge_reach",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "episode_id": "nas-enter",
                "symbol": "NAS100",
                "action_target": "ENTER_NOW",
                "continuation_target": "CONTINUE_AFTER_BREAK",
                "matched_job_id": "job-1",
                "matched_decision_time": "2026-04-03T10:37:00",
                "seed_grade": "strict",
                "promote_to_training": "True",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "transition_hit_rate": "0.6",
                "management_hit_rate": "0.8",
                "p_buy_confirm": "0.7",
                "actual_buy_confirm": "1",
                "p_continuation_success": "0.6",
                "actual_continuation_success": "1",
                "p_false_break": "0.1",
                "actual_false_break": "0",
                "p_continue_favor": "0.55",
                "actual_continue_favor": "1",
                "p_fail_now": "0.08",
                "actual_fail_now": "0",
                "p_opposite_edge_reach": "0.58",
                "actual_opposite_edge_reach": "1",
            }
        )
        writer.writerow(
            {
                "episode_id": "nas-wait",
                "symbol": "NAS100",
                "action_target": "WAIT_MORE",
                "continuation_target": "WAIT_OR_UNCLEAR",
                "matched_job_id": "job-1",
                "matched_decision_time": "2026-04-03T11:22:01",
                "seed_grade": "strict",
                "promote_to_training": "True",
                "transition_label_status": "VALID",
                "management_label_status": "INSUFFICIENT_FUTURE_BARS",
                "transition_hit_rate": "0.6",
                "management_hit_rate": "0.0",
                "p_buy_confirm": "0.3",
                "actual_buy_confirm": "1",
                "p_continuation_success": "0.2",
                "actual_continuation_success": "1",
                "p_false_break": "0.29",
                "actual_false_break": "0",
                "p_continue_favor": "0.15",
                "actual_continue_favor": "",
                "p_fail_now": "0.20",
                "actual_fail_now": "",
                "p_opposite_edge_reach": "0.42",
                "actual_opposite_edge_reach": "",
            }
        )
        writer.writerow(
            {
                "episode_id": "btc-exit",
                "symbol": "BTCUSD",
                "action_target": "EXIT_PROTECT",
                "continuation_target": "CONTINUE_THEN_PROTECT",
                "matched_job_id": "job-2",
                "matched_decision_time": "2026-04-02T15:39:24",
                "seed_grade": "strict",
                "promote_to_training": "True",
                "transition_label_status": "VALID",
                "management_label_status": "VALID",
                "transition_hit_rate": "0.7",
                "management_hit_rate": "0.9",
                "p_buy_confirm": "0.0",
                "actual_buy_confirm": "",
                "p_continuation_success": "0.0",
                "actual_continuation_success": "",
                "p_false_break": "0.0",
                "actual_false_break": "",
                "p_continue_favor": "0.62",
                "actual_continue_favor": "1",
                "p_fail_now": "0.05",
                "actual_fail_now": "0",
                "p_opposite_edge_reach": "0.71",
                "actual_opposite_edge_reach": "1",
            }
        )

    payload = write_breakout_shadow_preview_training_set(
        seed_csv_path=seed_csv,
        analysis_csv_path=shadow_root / "preview.csv",
        analysis_json_path=shadow_root / "preview.json",
        analysis_md_path=shadow_root / "preview.md",
        dataset_dir=dataset_root,
    )

    assert payload["summary"]["corpus_row_count"] == 3
    assert payload["summary"]["dataset_artifacts"]["timing"]["rows"] == 2
    assert payload["summary"]["dataset_artifacts"]["breakout_continuation"]["rows"] == 3
    assert payload["summary"]["dataset_artifacts"]["exit_management"]["rows"] == 3
    assert (dataset_root / "timing_dataset.parquet").exists()
    assert (dataset_root / "breakout_continuation_dataset.parquet").exists()
    assert (dataset_root / "exit_management_dataset.parquet").exists()
