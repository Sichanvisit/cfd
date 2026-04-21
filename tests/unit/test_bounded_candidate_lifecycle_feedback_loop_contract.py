import backend.services.bounded_candidate_lifecycle_feedback_loop_contract as subject
from backend.services.bounded_candidate_lifecycle_feedback_loop_contract import (
    attach_bounded_candidate_lifecycle_feedback_loop_fields_v1,
    build_bounded_candidate_lifecycle_feedback_loop_contract_v1,
    build_bounded_candidate_lifecycle_feedback_loop_summary_v1,
    generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary_v1,
)


def test_bounded_candidate_lifecycle_feedback_loop_contract_exposes_expected_fields():
    contract = build_bounded_candidate_lifecycle_feedback_loop_contract_v1()

    assert contract["contract_version"] == "bounded_candidate_lifecycle_feedback_loop_contract_v1"
    assert contract["loop_action_enum_v1"] == [
        "NO_ACTION",
        "KEEP_REVIEW",
        "KEEP_SHADOW",
        "PROMOTE_PATCH",
        "EXPIRE_CANDIDATE",
        "ROLLBACK_CANDIDATE",
    ]
    assert contract["lifecycle_state_enum_v1"] == [
        "NOT_APPLICABLE",
        "REVIEW_ONLY",
        "SHADOW_ACTIVE",
        "PROMOTION_READY",
        "EXPIRED",
        "ROLLED_BACK",
    ]
    assert "bounded_candidate_feedback_loop_action_v1" in contract["row_level_fields_v1"]
    assert "bounded_candidate_feedback_lifecycle_state_v1" in contract["row_level_fields_v1"]


def test_attach_bounded_candidate_lifecycle_feedback_loop_fields_marks_keep_shadow(monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_calibration_candidate_summary_v1",
        lambda latest_signal_by_symbol: {
            "candidate_objects_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "status": "PROPOSED",
                    "rollback": {"rollback_to": 0.4},
                }
            }
        },
    )
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_evaluation_dashboard_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold"
                }
            },
            "candidate_evaluation_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "evaluation_outcome": "KEEP_OBSERVING",
                    "evaluation_assessment_v1": "CAUTIOUS_POSITIVE",
                }
            },
            "candidate_apply_sessions_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "session_state_v1": "ACTIVE",
                }
            },
        },
    )

    rows = attach_bounded_candidate_lifecycle_feedback_loop_fields_v1({"BTCUSD": {"symbol": "BTCUSD"}})
    row = rows["BTCUSD"]

    assert row["bounded_candidate_feedback_candidate_id_v1"] == "BTCUSD:flow.ambiguity_threshold"
    assert row["bounded_candidate_feedback_loop_action_v1"] == "KEEP_SHADOW"
    assert row["bounded_candidate_feedback_lifecycle_state_v1"] == "SHADOW_ACTIVE"
    assert row["bounded_candidate_feedback_source_outcome_v1"] == "KEEP_OBSERVING"
    assert row["bounded_candidate_feedback_source_assessment_v1"] == "CAUTIOUS_POSITIVE"


def test_attach_bounded_candidate_lifecycle_feedback_loop_fields_marks_keep_review(monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_calibration_candidate_summary_v1",
        lambda latest_signal_by_symbol: {
            "candidate_objects_v1": {
                "XAUUSD:flow.conviction_building_floor": {
                    "candidate_id": "XAUUSD:flow.conviction_building_floor",
                    "symbol": "XAUUSD",
                    "learning_key": "flow.conviction_building_floor",
                    "status": "REVIEW_ONLY",
                    "rollback": {"rollback_to": 0.45},
                }
            }
        },
    )
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_evaluation_dashboard_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "XAUUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "XAUUSD:flow.conviction_building_floor"
                }
            },
            "candidate_evaluation_entries_v1": {},
            "candidate_apply_sessions_v1": {},
        },
    )

    rows = attach_bounded_candidate_lifecycle_feedback_loop_fields_v1({"XAUUSD": {"symbol": "XAUUSD"}})
    row = rows["XAUUSD"]

    assert row["bounded_candidate_feedback_loop_action_v1"] == "KEEP_REVIEW"
    assert row["bounded_candidate_feedback_lifecycle_state_v1"] == "REVIEW_ONLY"
    assert row["bounded_candidate_feedback_patch_ready_v1"] is False
    assert row["bounded_candidate_feedback_rollback_ready_v1"] is False


def test_build_bounded_candidate_lifecycle_feedback_loop_summary_counts_actions(monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_calibration_candidate_summary_v1",
        lambda latest_signal_by_symbol: {
            "candidate_objects_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "status": "PROPOSED",
                    "current_value": 0.4,
                    "proposed_value": 0.35,
                    "delta": -0.05,
                    "rollback": {"rollback_to": 0.4},
                },
                "NAS100:flow.conviction_building_floor": {
                    "candidate_id": "NAS100:flow.conviction_building_floor",
                    "symbol": "NAS100",
                    "learning_key": "flow.conviction_building_floor",
                    "status": "PROPOSED",
                    "current_value": 0.6,
                    "proposed_value": 0.55,
                    "delta": -0.05,
                    "rollback": {"rollback_to": 0.6},
                },
                "XAUUSD:flow.ambiguity_threshold": {
                    "candidate_id": "XAUUSD:flow.ambiguity_threshold",
                    "symbol": "XAUUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "status": "FILTERED_OUT",
                    "rollback": {"rollback_to": 0.4},
                },
                "ETHUSD:flow.ambiguity_threshold": {
                    "candidate_id": "ETHUSD:flow.ambiguity_threshold",
                    "symbol": "ETHUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "status": "REVIEW_ONLY",
                    "rollback": {"rollback_to": 0.4},
                },
            }
        },
    )
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_evaluation_dashboard_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold"
                },
                "NAS100": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "NAS100:flow.conviction_building_floor"
                },
                "XAUUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "XAUUSD:flow.ambiguity_threshold"
                },
                "ETHUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "ETHUSD:flow.ambiguity_threshold"
                },
            },
            "candidate_evaluation_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "evaluation_outcome": "PROMOTE",
                    "evaluation_assessment_v1": "POSITIVE",
                },
                "NAS100:flow.conviction_building_floor": {
                    "evaluation_outcome": "ROLLBACK",
                    "evaluation_assessment_v1": "NEGATIVE",
                },
            },
            "candidate_apply_sessions_v1": {
                "BTCUSD:flow.ambiguity_threshold": {"session_state_v1": "ACTIVE"},
                "NAS100:flow.conviction_building_floor": {"session_state_v1": "BLOCKED"},
            },
        },
    )

    report = build_bounded_candidate_lifecycle_feedback_loop_summary_v1({})
    summary = report["summary"]
    entries = report["candidate_feedback_entries_v1"]

    assert summary["status"] == "READY"
    assert summary["candidate_feedback_count"] == 4
    assert summary["loop_action_count_summary"] == {
        "PROMOTE_PATCH": 1,
        "ROLLBACK_CANDIDATE": 1,
        "EXPIRE_CANDIDATE": 1,
        "KEEP_REVIEW": 1,
    }
    assert summary["lifecycle_state_count_summary"] == {
        "PROMOTION_READY": 1,
        "ROLLED_BACK": 1,
        "EXPIRED": 1,
        "REVIEW_ONLY": 1,
    }
    assert summary["patch_ready_count"] == 1
    assert summary["rollback_ready_count"] == 1
    assert entries["BTCUSD:flow.ambiguity_threshold"]["patch_ready_v1"] is True
    assert entries["NAS100:flow.conviction_building_floor"]["rollback_ready_v1"] is True


def test_generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_calibration_candidate_summary_v1",
        lambda latest_signal_by_symbol: {
            "candidate_objects_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "status": "PROPOSED",
                    "current_value": 0.4,
                    "proposed_value": 0.35,
                    "delta": -0.05,
                    "rollback": {"rollback_to": 0.4},
                }
            }
        },
    )
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_evaluation_dashboard_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_calibration_candidate_primary_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold"
                }
            },
            "candidate_evaluation_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "evaluation_outcome": "PROMOTE",
                    "evaluation_assessment_v1": "POSITIVE",
                }
            },
            "candidate_apply_sessions_v1": {
                "BTCUSD:flow.ambiguity_threshold": {"session_state_v1": "ACTIVE"}
            },
        },
    )

    report = generate_and_write_bounded_candidate_lifecycle_feedback_loop_summary_v1(
        {},
        shadow_auto_dir=tmp_path,
    )

    assert report["summary"]["loop_action_count_summary"]["PROMOTE_PATCH"] == 1
    assert report["artifact_paths"]["json_path"].endswith("bounded_candidate_lifecycle_feedback_loop_latest.json")
    assert report["artifact_paths"]["markdown_path"].endswith("bounded_candidate_lifecycle_feedback_loop_latest.md")
