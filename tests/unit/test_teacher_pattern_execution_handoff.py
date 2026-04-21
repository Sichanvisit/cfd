from backend.services.teacher_pattern_execution_handoff import (
    build_teacher_pattern_execution_handoff_report,
)


def _ready_asset_report():
    return {"warnings": []}


def _ready_full_qa_report():
    return {
        "full_qa_readiness": {"full_qa_ready": True, "shortfall_rows": 0},
        "labeled_rows": 12_000,
        "pattern_coverage": {"covered_primary_count": 9},
        "warnings": [],
    }


def _ready_baseline_report():
    return {
        "baseline_ready": True,
        "baseline_warnings": [],
        "tasks": {
            "group_task": {
                "skipped": False,
                "model_metrics": {"test": {"macro_f1": 0.82}},
            },
            "pattern_task": {
                "skipped": False,
                "supported_pattern_ids": [1, 5, 9, 12, 14, 23],
                "model_metrics": {"test": {"macro_f1": 0.71}},
            },
        },
    }


def test_execution_handoff_report_marks_ready_when_all_gates_pass():
    report = build_teacher_pattern_execution_handoff_report(
        asset_calibration_report=_ready_asset_report(),
        full_qa_report=_ready_full_qa_report(),
        baseline_report=_ready_baseline_report(),
        confusion_report={
            "group_candidates": [],
            "pattern_candidates": [],
            "watchlist_status": [],
            "warnings": [],
        },
    )

    assert report["handoff_status"] == "READY"
    assert report["execution_handoff_ready"] is True
    assert report["blockers"] == []


def test_execution_handoff_report_blocks_when_seed_and_confusions_are_not_ready():
    report = build_teacher_pattern_execution_handoff_report(
        asset_calibration_report={"warnings": ["group_skew:BTCUSD:A"]},
        full_qa_report={
            "full_qa_readiness": {"full_qa_ready": False, "shortfall_rows": 7860},
            "labeled_rows": 2140,
            "pattern_coverage": {"covered_primary_count": 6},
            "warnings": ["overall_group_skew:A"],
        },
        baseline_report={
            "baseline_ready": True,
            "tasks": {
                "group_task": {
                    "skipped": False,
                    "model_metrics": {"test": {"macro_f1": 0.91}},
                },
                "pattern_task": {
                    "skipped": False,
                    "supported_pattern_ids": [1, 5, 9, 14],
                    "model_metrics": {"test": {"macro_f1": 0.97}},
                },
            },
        },
        confusion_report={
            "group_candidates": [{"pair": "A->D", "severity": "high"}],
            "pattern_candidates": [{"pair": "1-5", "severity": "medium"}],
            "watchlist_status": [{"pair": "12-23", "status": "observe_only"}],
            "warnings": ["watchlist_pairs_not_yet_observed"],
        },
    )

    blocker_codes = {row["code"] for row in report["blockers"]}
    assert report["handoff_status"] == "NOT_READY"
    assert "full_qa_seed_shortfall" in blocker_codes
    assert "insufficient_primary_coverage" in blocker_codes
    assert "insufficient_supported_pattern_classes" in blocker_codes
    assert "unresolved_high_confusions" in blocker_codes


def test_execution_handoff_report_marks_ready_with_warnings_when_only_soft_warnings_remain():
    report = build_teacher_pattern_execution_handoff_report(
        asset_calibration_report={"warnings": ["group_skew:XAUUSD:A"]},
        full_qa_report={
            "full_qa_readiness": {"full_qa_ready": True, "shortfall_rows": 0},
            "labeled_rows": 11_500,
            "pattern_coverage": {"covered_primary_count": 8},
            "warnings": ["rare_primary_patterns_present"],
        },
        baseline_report=_ready_baseline_report(),
        confusion_report={
            "group_candidates": [],
            "pattern_candidates": [{"pair": "1-5", "severity": "medium"}],
            "watchlist_status": [{"pair": "12-23", "status": "observe_only"}],
            "warnings": ["watchlist_pairs_not_yet_observed"],
        },
    )

    assert report["handoff_status"] == "READY_WITH_WARNINGS"
    assert report["execution_handoff_ready"] is True
    assert report["blockers"] == []
    assert "medium_confusions_present" in report["warnings"]
