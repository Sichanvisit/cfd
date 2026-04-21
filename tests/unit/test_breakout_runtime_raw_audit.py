import json
from pathlib import Path

import pandas as pd

from backend.services.breakout_runtime_raw_audit import build_breakout_runtime_raw_audit


def test_breakout_runtime_raw_audit_flags_missing_breakout_axes(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:40:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:40:01",
                "symbol": "NAS100",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-1",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T22:40:01",
        "symbol": "NAS100",
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {"breakout_up": 0.0, "breakout_down": 0.0},
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.12,
                "false_break_score": 0.41,
                "continuation_score": 0.18,
                "decision_hint": "BALANCED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_21",
                "scene_pattern_name": "gap_fill",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.0},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 1.0},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-1",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert summary["detail_match_count"] == 1
    assert summary["breakout_up_nonzero_count"] == 0
    assert summary["breakout_down_nonzero_count"] == 0
    assert summary["direction_none_count"] == 1
    assert summary["overlay_wait_more_count"] == 1
    assert summary["recommended_next_action"] == "inspect_response_vector_breakout_axes"
    assert frame.iloc[0]["raw_blocker_family"] == "missing_breakout_response_axis"


def test_breakout_runtime_raw_audit_can_surface_enter_now_candidate(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:42:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:42:01",
                "symbol": "BTCUSD",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-2",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T22:42:01",
        "symbol": "BTCUSD",
        "micro_breakout_readiness_state": "READY_BREAKOUT",
        "response_vector_v2": {"breakout_up": 0.72, "breakout_down": 0.05},
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.61,
                "false_break_score": 0.12,
                "continuation_score": 0.58,
                "wait_confirm_gap": 0.08,
                "decision_hint": "CONFIRM_BIASED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_breakout",
                "scene_pattern_name": "breakout",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.15},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.21},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-2",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert summary["breakout_up_nonzero_count"] == 1
    assert summary["overlay_enter_now_count"] == 1
    assert summary["recommended_next_action"] == "compare_breakout_enter_now_rows_with_candidate_bridge"
    assert frame.iloc[0]["raw_blocker_family"] == "enter_now_candidate_ready"


def test_breakout_runtime_raw_audit_can_bridge_proxy_axes(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:45:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:45:01",
                "symbol": "XAUUSD",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-3",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T22:45:01",
        "symbol": "XAUUSD",
        "micro_breakout_readiness_state": "READY_BREAKOUT",
        "response_vector_v2": {
            "upper_break_up": 0.73,
            "lower_break_down": 0.04,
            "mid_reclaim_up": 0.21,
            "mid_lose_down": 0.03,
        },
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.58,
                "false_break_score": 0.14,
                "continuation_score": 0.54,
                "wait_confirm_gap": 0.06,
                "decision_hint": "CONFIRM_BIASED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_breakout",
                "scene_pattern_name": "reclaim_breakout",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.18},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.19},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-3",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert summary["breakout_up_nonzero_count"] == 1
    assert summary["overlay_enter_now_count"] == 1
    assert '"proxy"' in summary["breakout_axis_mode_counts"]
    assert "upper_break_up" in summary["breakout_up_source_counts"]
    assert "READY_BREAKOUT" in summary["effective_breakout_readiness_counts"]
    assert "initial_breakout_candidate" in summary["breakout_type_candidate_counts"]
    assert "initial" in summary["selected_axis_family_counts"]
    assert frame.iloc[0]["breakout_axis_mode"] == "proxy"
    assert frame.iloc[0]["breakout_up_source"] == "upper_break_up"
    assert frame.iloc[0]["raw_blocker_family"] == "enter_now_candidate_ready"


def test_breakout_runtime_raw_audit_recommends_readiness_surrogate_after_axis_bridge(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:47:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:47:01",
                "symbol": "NAS100",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-4",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T22:47:01",
        "symbol": "NAS100",
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.44,
            "lower_break_down": 0.06,
            "mid_reclaim_up": 0.12,
            "mid_lose_down": 0.03,
        },
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.24,
                "false_break_score": 0.36,
                "continuation_score": 0.28,
                "wait_confirm_gap": -0.02,
                "decision_hint": "BALANCED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_breakout",
                "scene_pattern_name": "early_breakout_probe",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.05},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.44},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-4",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert summary["breakout_up_nonzero_count"] == 1
    assert summary["state_pre_breakout_count"] == 0
    assert "BUILDING_BREAKOUT" in summary["effective_breakout_readiness_counts"]
    assert summary["recommended_next_action"] == "compare_breakout_enter_now_rows_with_candidate_bridge"
    assert frame.iloc[0]["breakout_axis_mode"] == "proxy"
    assert frame.iloc[0]["effective_breakout_readiness_state"] == "BUILDING_BREAKOUT"
    assert frame.iloc[0]["breakout_state"] == "initial_breakout"
    assert frame.iloc[0]["raw_blocker_family"] == "barrier_drag_demoted"


def test_breakout_runtime_raw_audit_surfaces_demotion_conflict_levels(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T23:19:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T23:19:01",
                "symbol": "XAUUSD",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-6",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T23:19:01",
        "symbol": "XAUUSD",
        "micro_breakout_readiness_state": "",
        "micro_swing_high_retest_count_20": 2,
        "response_vector_v2": {
            "upper_break_up": 0.22,
            "lower_break_down": 0.03,
            "mid_reclaim_up": 0.28,
            "mid_lose_down": 0.03,
        },
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "BUY",
                "confirm_score": 0.16,
                "false_break_score": 0.34,
                "continuation_score": 0.13,
                "wait_confirm_gap": -0.01,
                "decision_hint": "BALANCED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_breakout",
                "scene_pattern_name": "reclaim_breakout",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.05},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.44},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-6",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert frame.iloc[0]["overlay_target"] == "WATCH_BREAKOUT"
    assert frame.iloc[0]["conflict_level"] == "barrier_drag"
    assert frame.iloc[0]["action_demotion_rule"] == "watch_breakout_barrier_drag"
    assert frame.iloc[0]["raw_blocker_family"] == "barrier_drag_demoted"
    assert "barrier_drag" in summary["conflict_level_counts"]


def test_breakout_runtime_raw_audit_surfaces_why_none_reason_counts(tmp_path: Path) -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:49:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:49:01",
                "symbol": "BTCUSD",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "detail_row_key": "row-5",
            }
        ]
    )
    detail_path = tmp_path / "entry_decisions.detail.jsonl"
    payload = {
        "time": "2026-04-08T22:49:01",
        "symbol": "BTCUSD",
        "micro_breakout_readiness_state": "",
        "response_vector_v2": {
            "upper_break_up": 0.34,
            "lower_break_down": 0.32,
            "mid_reclaim_up": 0.05,
            "mid_lose_down": 0.04,
        },
        "forecast_state25_runtime_bridge_v1": {
            "forecast_runtime_summary_v1": {
                "confirm_side": "",
                "confirm_score": 0.18,
                "false_break_score": 0.17,
                "continuation_score": 0.12,
                "wait_confirm_gap": -0.04,
                "decision_hint": "BALANCED",
            },
            "state25_runtime_hint_v1": {
                "scene_family": "pattern_breakout",
                "scene_pattern_name": "mixed_breakout",
            },
        },
        "belief_state25_runtime_bridge_v1": {
            "belief_runtime_summary_v1": {"flip_readiness": 0.05},
        },
        "barrier_state25_runtime_bridge_v1": {
            "barrier_runtime_summary_v1": {"barrier_total": 0.31},
        },
    }
    detail_path.write_text(
        json.dumps(
            {
                "record_type": "entry_decision_detail_v1",
                "schema_version": "entry_decision_detail_v1",
                "row_key": "row-5",
                "payload": payload,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    frame, summary = build_breakout_runtime_raw_audit(
        runtime_status,
        entry_decisions,
        entry_detail_path=detail_path,
        recent_limit=20,
    )

    assert len(frame) == 1
    assert frame.iloc[0]["breakout_direction"] == "NONE"
    assert frame.iloc[0]["why_none_reason"] in {"gap_too_small", "mixed_axis_conflict"}
    assert frame.iloc[0]["raw_blocker_family"] in {"gap_too_small", "mixed_axis_conflict"}
    assert summary["why_none_reason_counts"] != "{}"
