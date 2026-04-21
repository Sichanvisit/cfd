from backend.services.teacher_pattern_confusion_tuning import build_teacher_pattern_confusion_tuning_report


def test_confusion_tuning_report_prioritizes_observed_group_and_pattern_confusions():
    baseline_report = {
        "baseline_ready": True,
        "tasks": {
            "group_task": {
                "top_confusions": [
                    {"true_label": "A", "pred_label": "D", "count": 13, "ratio": 0.04},
                ]
            },
            "pattern_task": {
                "supported_pattern_ids": [1, 5, 9, 14],
                "top_confusions": [
                    {"true_label": "1", "pred_label": "5", "count": 7, "ratio": 0.021},
                ],
            },
        },
    }
    full_qa_report = {
        "full_qa_readiness": {"full_qa_ready": False},
        "labeled_rows": 2140,
        "confusion_proxy_summary": {
            "watchlist_pairs": {
                "12-23": {"count": 0, "ratio": 0.0},
                "5-10": {"count": 0, "ratio": 0.0},
                "2-16": {"count": 0, "ratio": 0.0},
            }
        },
    }

    report = build_teacher_pattern_confusion_tuning_report(
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
    )

    assert report["priority_actions"][0]["pair"] == "A->D"
    assert report["priority_actions"][1]["pair"] == "1-5"
    assert report["pattern_candidates"][0]["severity"] == "medium"
    assert "watchlist_pairs_not_yet_observed" in report["warnings"]


def test_confusion_tuning_report_marks_watchlist_ready_when_pair_is_present():
    baseline_report = {
        "baseline_ready": True,
        "tasks": {
            "group_task": {"top_confusions": []},
            "pattern_task": {"supported_pattern_ids": [12, 23], "top_confusions": []},
        },
    }
    full_qa_report = {
        "full_qa_readiness": {"full_qa_ready": False},
        "labeled_rows": 2140,
        "confusion_proxy_summary": {
            "watchlist_pairs": {
                "12-23": {"count": 8, "ratio": 0.08},
                "5-10": {"count": 0, "ratio": 0.0},
                "2-16": {"count": 0, "ratio": 0.0},
            }
        },
    }

    report = build_teacher_pattern_confusion_tuning_report(
        full_qa_report=full_qa_report,
        baseline_report=baseline_report,
    )

    ready_pair = next(item for item in report["watchlist_status"] if item["pair"] == "12-23")
    assert ready_pair["status"] == "ready_for_tuning"
    assert report["priority_actions"][0]["kind"] == "watchlist_pair"
