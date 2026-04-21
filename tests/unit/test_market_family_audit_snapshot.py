import pandas as pd

from backend.services.market_family_audit_snapshot import (
    build_market_family_entry_audit,
    build_market_family_exit_audit,
)


def test_market_family_entry_audit_surfaces_symbol_specific_blockers() -> None:
    runtime_status = {
        "updated_at": "2026-04-09T01:05:00+09:00",
        "semantic_live_config": {"mode": "log_only"},
    }
    entry_decisions = pd.DataFrame(
        [
            {
                "time": "2026-04-09T01:04:00",
                "symbol": "XAUUSD",
                "outcome": "wait",
                "blocked_by": "outer_band_guard",
                "action_none_reason": "probe_not_promoted",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "core_reason": "core_shadow_observe_wait",
            },
            {
                "time": "2026-04-09T01:03:00",
                "symbol": "XAUUSD",
                "outcome": "entered",
                "blocked_by": "",
                "action_none_reason": "",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "core_reason": "core_shadow_probe_action",
            },
            {
                "time": "2026-04-09T01:02:00",
                "symbol": "BTCUSD",
                "outcome": "wait",
                "blocked_by": "middle_sr_anchor_guard",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "middle_sr_anchor_required_observe",
                "core_reason": "core_shadow_observe_wait",
            },
            {
                "time": "2026-04-09T01:01:00",
                "symbol": "NAS100",
                "outcome": "wait",
                "blocked_by": "",
                "action_none_reason": "observe_state_wait",
                "observe_reason": "conflict_box_upper_bb20_lower_upper_dominant_observe",
                "core_reason": "core_shadow_observe_wait",
            },
        ]
    )

    frame, summary = build_market_family_entry_audit(runtime_status, entry_decisions, recent_limit=20)

    assert summary["market_family_row_count"] == 4
    assert "inspect_xau_outer_band_follow_through_bridge" in summary["recommended_next_action"]
    assert "inspect_btc_middle_anchor_probe_relief" in summary["recommended_next_action"]
    assert "inspect_nas_conflict_observe_decomposition" in summary["recommended_next_action"]
    assert set(frame["metric_group"]) >= {"outcome", "blocked_by", "action_none_reason", "observe_reason", "core_reason"}
    xau_rows = frame.loc[frame["symbol"] == "XAUUSD"]
    assert not xau_rows.empty
    assert (xau_rows["recommended_focus"] == "inspect_xau_outer_band_follow_through_bridge").any()


def test_market_family_exit_audit_surfaces_runner_preservation_focus() -> None:
    runtime_status = {"updated_at": "2026-04-09T01:10:00+09:00"}
    closed_history = pd.DataFrame(
        [
            {
                "symbol": "XAUUSD",
                "entry_reason": "[AUTO] something",
                "exit_reason": "Target | exec_profile=balanced",
                "status": "CLOSED",
                "profit": "2.58",
                "open_time": "2026-04-09 00:15:30",
                "close_time": "2026-04-09 00:17:32",
            },
            {
                "symbol": "XAUUSD",
                "entry_reason": "[AUTO] something",
                "exit_reason": "Lock Exit, Flow: BB20 mid 이탈저항 (+120점) | exec_profile=neutral | hard_guard=profit_giveback",
                "status": "CLOSED",
                "profit": "1.94",
                "open_time": "2026-04-09 00:29:12",
                "close_time": "2026-04-09 00:31:12",
            },
            {
                "symbol": "BTCUSD",
                "entry_reason": "[AUTO] something",
                "exit_reason": "Protect Exit, Flow: BB20 breakout down (+150점)",
                "status": "CLOSED",
                "profit": "-0.50",
                "open_time": "2026-04-09 00:10:00",
                "close_time": "2026-04-09 00:12:00",
            },
            {
                "symbol": "NAS100",
                "entry_reason": "[MANUAL] something",
                "exit_reason": "Manual/Unknown",
                "status": "CLOSED",
                "profit": "5.00",
                "open_time": "2026-04-09 00:05:00",
                "close_time": "2026-04-09 00:10:00",
            },
        ]
    )

    frame, summary = build_market_family_exit_audit(runtime_status, closed_history, recent_limit=20)

    assert summary["market_family_row_count"] == 4
    assert "inspect_xauusd_runner_preservation" in summary["recommended_next_action"]
    assert "inspect_btcusd_protective_exit_overfire" in summary["recommended_next_action"]
    assert "collect_more_nas100_auto_exit_rows" in summary["recommended_next_action"]
    xau_rows = frame.loc[frame["symbol"] == "XAUUSD"]
    assert not xau_rows.empty
    assert (xau_rows["metric_group"] == "auto_exit_reason").any()
    assert (xau_rows["recommended_focus"] == "inspect_xauusd_runner_preservation").any()
