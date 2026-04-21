import pandas as pd

from backend.services.semantic_baseline_no_action_sample_audit import (
    build_semantic_baseline_no_action_sample_audit,
    render_semantic_baseline_no_action_sample_audit_markdown,
)


def test_semantic_baseline_no_action_sample_audit_builds_dominant_cluster():
    frame = pd.DataFrame(
        [
            {
                "time": "2026-04-13T17:32:27",
                "symbol": "BTCUSD",
                "semantic_live_fallback_reason": "baseline_no_action",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "outer_band_guard",
                "action_none_reason": "probe_not_promoted",
                "semantic_shadow_available": 0,
                "semantic_shadow_should_enter": 0,
                "semantic_shadow_trace_quality": "unavailable",
                "probe_state": "BLOCKED",
            },
            {
                "time": "2026-04-13T17:29:35",
                "symbol": "BTCUSD",
                "semantic_live_fallback_reason": "baseline_no_action",
                "observe_reason": "outer_band_reversal_support_required_observe",
                "blocked_by": "outer_band_guard",
                "action_none_reason": "probe_not_promoted",
                "semantic_shadow_available": 0,
                "semantic_shadow_should_enter": 0,
                "semantic_shadow_trace_quality": "unavailable",
                "probe_state": "BLOCKED",
            },
            {
                "time": "2026-04-13T17:10:00",
                "symbol": "NAS100",
                "semantic_live_fallback_reason": "semantic_unavailable",
                "observe_reason": "setup_rejected",
                "blocked_by": "setup_rejected",
                "action_none_reason": "observe_state_wait",
            },
        ]
    )
    payload = build_semantic_baseline_no_action_sample_audit(
        entry_decisions=frame,
        recent_limit=200,
        sample_limit=10,
    )

    summary = payload["summary"]
    assert summary["baseline_no_action_count"] == 2
    assert summary["symbol_counts"] == {"BTCUSD": 2}
    assert "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted" in summary["dominant_cluster"]


def test_semantic_baseline_no_action_markdown_renders_samples():
    markdown = render_semantic_baseline_no_action_sample_audit_markdown(
        {
            "summary": {
                "generated_at": "2026-04-13T17:50:00+09:00",
                "recent_row_count": 200,
                "baseline_no_action_count": 35,
                "dominant_cluster": "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted",
                "recommended_next_action": "inspect dominant baseline_no_action cluster before semantic threshold changes",
                "symbol_counts": {"BTCUSD": 35},
                "observe_reason_counts": {"outer_band_reversal_support_required_observe": 34},
                "blocked_by_counts": {"outer_band_guard": 21},
                "action_none_reason_counts": {"probe_not_promoted": 21},
            },
            "samples": [
                {
                    "time": "2026-04-13T17:32:27",
                    "symbol": "BTCUSD",
                    "observe_reason": "outer_band_reversal_support_required_observe",
                    "blocked_by": "outer_band_guard",
                    "action_none_reason": "probe_not_promoted",
                    "semantic_shadow_available": 0,
                    "semantic_shadow_should_enter": 0,
                    "semantic_shadow_trace_quality": "unavailable",
                    "probe_state": "BLOCKED",
                    "cluster_key": "BTCUSD | outer_band_reversal_support_required_observe | outer_band_guard | probe_not_promoted",
                }
            ],
        }
    )

    assert "Semantic Baseline No-Action Sample Audit" in markdown
    assert "outer_band_reversal_support_required_observe" in markdown
    assert "BTCUSD" in markdown
