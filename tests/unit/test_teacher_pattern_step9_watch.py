from backend.services.teacher_pattern_step9_watch import (
    build_teacher_pattern_step9_watch_report,
    render_teacher_pattern_step9_watch_markdown,
)


def test_step9_watch_report_tracks_seed_shortfall_and_runtime_log_only_watch():
    report = build_teacher_pattern_step9_watch_report(
        seed_report={
            "total_rows": 8705,
            "labeled_rows": 2596,
            "unlabeled_rows": 6109,
        },
        full_qa_report={
            "pattern_coverage": {"covered_primary_count": 8},
            "confusion_proxy_summary": {
                "watchlist_pairs": {
                    "12-23": {"count": 0, "ratio": 0.0},
                    "5-10": {"count": 0, "ratio": 0.0},
                    "2-16": {"count": 0, "ratio": 0.0},
                }
            },
        },
        baseline_report={
            "tasks": {
                "pattern_task": {
                    "supported_pattern_ids": [1, 5, 9, 11, 14, 21, 25],
                }
            }
        },
        confusion_report={
            "watchlist_status": [
                {"pair": "12-23", "count": 0, "ratio": 0.0, "status": "observe_only"},
                {"pair": "5-10", "count": 0, "ratio": 0.0, "status": "observe_only"},
                {"pair": "2-16", "count": 0, "ratio": 0.0, "status": "observe_only"},
            ]
        },
        execution_handoff_report={
            "handoff_status": "NOT_READY",
            "execution_handoff_ready": False,
            "blockers": [{"code": "full_qa_seed_shortfall"}],
            "warnings": ["watchlist_pairs_still_sparse"],
        },
        runtime_status_report={
            "runtime_recycle": {
                "mode": "log_only",
                "last_status": "waiting",
                "last_reason": "interval_not_reached",
                "last_block_reason": "flat_grace_active",
                "log_only_count": 1,
                "reexec_count": 0,
            }
        },
    )

    assert report["snapshot"]["rows_to_target"] == 7404
    assert report["watch_items"]["execution_handoff"]["blocking_seed_only"] is True
    assert report["watch_items"]["watchlist_pairs"]["status"] == "observe_only"
    assert report["watch_items"]["runtime_recycle"]["mode"] == "log_only"
    assert report["recheck_timing"]["status"] == "watch_only"


def test_step9_watch_report_marks_recheck_when_watch_milestones_change():
    previous_report = {
        "snapshot": {
            "total_rows": 8600,
            "labeled_rows": 2500,
            "supported_pattern_ids": [1, 5, 9, 14, 21],
        },
        "watch_items": {
            "watchlist_pairs": {
                "pairs": [
                    {"pair": "12-23", "count": 0},
                    {"pair": "5-10", "count": 0},
                    {"pair": "2-16", "count": 0},
                ]
            },
            "execution_handoff": {
                "blocker_codes": [
                    "full_qa_seed_shortfall",
                    "insufficient_supported_pattern_classes",
                ]
            },
            "runtime_recycle": {
                "log_only_count": 0,
            },
        },
    }

    report = build_teacher_pattern_step9_watch_report(
        seed_report={
            "total_rows": 8705,
            "labeled_rows": 2596,
            "unlabeled_rows": 6109,
        },
        full_qa_report={
            "pattern_coverage": {"covered_primary_count": 8},
            "confusion_proxy_summary": {
                "watchlist_pairs": {
                    "12-23": {"count": 2, "ratio": 0.0008},
                    "5-10": {"count": 0, "ratio": 0.0},
                    "2-16": {"count": 0, "ratio": 0.0},
                }
            },
        },
        baseline_report={
            "tasks": {
                "pattern_task": {
                    "supported_pattern_ids": [1, 5, 9, 11, 14, 21, 25],
                }
            }
        },
        confusion_report={
            "watchlist_status": [
                {"pair": "12-23", "count": 2, "ratio": 0.0008, "status": "ready_for_tuning"},
                {"pair": "5-10", "count": 0, "ratio": 0.0, "status": "observe_only"},
                {"pair": "2-16", "count": 0, "ratio": 0.0, "status": "observe_only"},
            ]
        },
        execution_handoff_report={
            "handoff_status": "NOT_READY",
            "execution_handoff_ready": False,
            "blockers": [{"code": "full_qa_seed_shortfall"}],
            "warnings": [],
        },
        runtime_status_report={
            "runtime_recycle": {
                "mode": "log_only",
                "last_status": "waiting",
                "last_reason": "interval_not_reached",
                "last_block_reason": "flat_grace_active",
                "log_only_count": 1,
                "reexec_count": 0,
            }
        },
        previous_watch_report=previous_report,
    )

    assert report["changes_since_last_watch"]["total_row_delta"] == 105
    assert report["changes_since_last_watch"]["new_watchlist_pairs"] == ["12-23"]
    assert report["changes_since_last_watch"]["supported_pattern_delta"] == [11, 25]
    assert report["changes_since_last_watch"]["runtime_recycle_cycle_advanced"] is True
    assert report["recheck_timing"]["status"] == "recheck_now"
    assert "fresh_closed_plus_100" in report["recheck_timing"]["reasons"]
    assert "new_watchlist_pair_observed" in report["recheck_timing"]["reasons"]


def test_step9_watch_markdown_renders_human_readable_summary():
    report = build_teacher_pattern_step9_watch_report(
        seed_report={
            "total_rows": 8706,
            "labeled_rows": 2596,
            "unlabeled_rows": 6110,
        },
        full_qa_report={
            "pattern_coverage": {"covered_primary_count": 8},
            "confusion_proxy_summary": {
                "watchlist_pairs": {
                    "12-23": {"count": 0, "ratio": 0.0},
                    "5-10": {"count": 0, "ratio": 0.0},
                    "2-16": {"count": 0, "ratio": 0.0},
                }
            },
        },
        baseline_report={
            "tasks": {
                "pattern_task": {
                    "supported_pattern_ids": [1, 5, 9, 11, 14, 21, 25],
                }
            }
        },
        confusion_report={
            "watchlist_status": [
                {"pair": "12-23", "count": 0, "ratio": 0.0, "status": "observe_only", "summary": "Observe first"},
            ]
        },
        execution_handoff_report={
            "handoff_status": "NOT_READY",
            "execution_handoff_ready": False,
            "blockers": [{"code": "full_qa_seed_shortfall"}],
            "warnings": [],
        },
        runtime_status_report={
            "runtime_recycle": {
                "mode": "log_only",
                "last_status": "waiting",
                "last_reason": "interval_not_reached",
                "last_block_reason": "flat_grace_active",
                "log_only_count": 1,
                "reexec_count": 0,
                "next_due_at": "2026-04-03T12:49:42",
            }
        },
    )

    markdown = render_teacher_pattern_step9_watch_markdown(report)

    assert "# Teacher Pattern Step9 Watch Report" in markdown
    assert "- labeled rows: `2596` / `10000`" in markdown
    assert "- execution handoff status: `NOT_READY`" in markdown
    assert "- `12-23`: count `0`, status `observe_only`, Observe first" in markdown
    assert "- `full_qa_seed_shortfall`" in markdown
    assert "- mode: `log_only`" in markdown
