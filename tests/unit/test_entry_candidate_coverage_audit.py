import pandas as pd

from backend.services.entry_candidate_coverage_audit import (
    build_entry_candidate_coverage_audit,
)


def test_entry_candidate_coverage_audit_surfaces_breakout_wait_more_blockers() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:10:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:10:01",
                "symbol": "BTCUSD",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "entry_candidate_bridge_available": False,
                "entry_candidate_bridge_selected": False,
                "entry_candidate_bridge_source": "",
                "breakout_candidate_action_target": "WAIT_MORE",
                "breakout_candidate_direction": "NONE",
                "action_none_reason": "observe_state_wait",
                "blocked_by": "outer_band_guard",
                "core_reason": "core_shadow_observe_wait",
                "state25_candidate_binding_mode": "log_only",
                "state25_candidate_threshold_symbol_scope_hit": False,
                "state25_candidate_threshold_stage_scope_hit": False,
            },
            {
                "time": "2026-04-08T22:09:01",
                "symbol": "NAS100",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "entry_candidate_bridge_available": False,
                "entry_candidate_bridge_selected": False,
                "entry_candidate_bridge_source": "",
                "breakout_candidate_action_target": "WAIT_MORE",
                "breakout_candidate_direction": "NONE",
                "action_none_reason": "probe_not_promoted",
                "blocked_by": "middle_sr_anchor_guard",
                "core_reason": "core_shadow_observe_wait",
                "state25_candidate_binding_mode": "log_only",
                "state25_candidate_threshold_symbol_scope_hit": True,
                "state25_candidate_threshold_stage_scope_hit": False,
            },
        ]
    )

    frame, summary = build_entry_candidate_coverage_audit(
        runtime_status,
        entry_decisions,
        recent_limit=20,
    )

    assert summary["baseline_no_action_row_count"] == 2
    assert summary["all_candidate_blank_count"] == 2
    assert summary["breakout_enter_now_count"] == 0
    assert summary["breakout_wait_more_count"] == 2
    assert summary["breakout_direction_none_count"] == 2
    assert summary["recommended_next_action"] == "inspect_breakout_runtime_thresholds_and_scene_sensitivity"
    assert set(frame["metric_group"]) >= {
        "breakout_action_target",
        "breakout_direction",
        "action_none_reason",
        "blocked_by",
        "candidate_presence",
    }


def test_entry_candidate_coverage_audit_prefers_candidate_distribution_followup_when_breakout_fires() -> None:
    runtime_status = {
        "updated_at": "2026-04-08T22:12:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-08T22:12:01",
                "symbol": "NAS100",
                "action": "",
                "entry_authority_rejected_by": "baseline_no_action",
                "entry_candidate_bridge_baseline_no_action": True,
                "entry_candidate_bridge_available": True,
                "entry_candidate_bridge_selected": True,
                "entry_candidate_bridge_source": "breakout_candidate",
                "breakout_candidate_action": "BUY",
                "breakout_candidate_action_target": "ENTER_NOW",
                "breakout_candidate_direction": "UP",
                "action_none_reason": "observe_state_wait",
                "blocked_by": "outer_band_guard",
                "core_reason": "core_shadow_observe_wait",
                "state25_candidate_binding_mode": "log_only",
                "state25_candidate_threshold_symbol_scope_hit": True,
                "state25_candidate_threshold_stage_scope_hit": True,
            }
        ]
    )

    _, summary = build_entry_candidate_coverage_audit(
        runtime_status,
        entry_decisions,
        recent_limit=20,
    )

    assert summary["breakout_candidate_available_count"] == 1
    assert summary["breakout_enter_now_count"] == 1
    assert summary["recommended_next_action"] == "inspect_breakout_candidate_selection_distribution"
