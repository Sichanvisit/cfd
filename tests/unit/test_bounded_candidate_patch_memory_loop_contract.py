import json

import backend.services.bounded_candidate_patch_memory_loop_contract as subject
from backend.services.bounded_candidate_patch_memory_loop_contract import (
    attach_bounded_candidate_patch_memory_loop_fields_v1,
    attach_recent_rollback_memory_fields_v1,
    build_bounded_candidate_patch_memory_loop_contract_v1,
    build_bounded_candidate_patch_memory_loop_summary_v1,
    generate_and_write_bounded_candidate_patch_memory_loop_summary_v1,
)


def test_bounded_candidate_patch_memory_loop_contract_exposes_expected_fields():
    contract = build_bounded_candidate_patch_memory_loop_contract_v1()

    assert contract["contract_version"] == "bounded_candidate_patch_memory_loop_contract_v1"
    assert contract["patch_catalog_state_enum_v1"] == ["NONE", "PATCH_CATALOG_READY"]
    assert contract["rollback_memory_state_enum_v1"] == ["NONE", "RECORDED"]
    assert contract["patch_entry_status_enum_v1"] == ["READY_FOR_REVIEW"]
    assert "bounded_candidate_followup_patch_catalog_state_v1" in contract["row_level_fields_v1"]
    assert "bounded_candidate_followup_rollback_memory_state_v1" in contract["row_level_fields_v1"]


def test_attach_bounded_candidate_patch_memory_loop_fields_marks_patch_catalog_and_rollback(monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_lifecycle_feedback_loop_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_candidate_feedback_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                },
                "NAS100": {
                    "bounded_candidate_feedback_candidate_id_v1": "NAS100:flow.conviction_building_floor",
                    "symbol": "NAS100",
                },
            },
            "candidate_feedback_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "loop_action_v1": "PROMOTE_PATCH",
                    "source_outcome_v1": "PROMOTE",
                    "source_assessment_v1": "POSITIVE",
                    "promoted_patch_v1": {
                        "current_value": 0.4,
                        "proposed_value": 0.35,
                        "delta": -0.05,
                    },
                },
                "NAS100:flow.conviction_building_floor": {
                    "candidate_id": "NAS100:flow.conviction_building_floor",
                    "symbol": "NAS100",
                    "learning_key": "flow.conviction_building_floor",
                    "loop_action_v1": "ROLLBACK_CANDIDATE",
                    "source_outcome_v1": "ROLLBACK",
                    "source_assessment_v1": "NEGATIVE",
                    "rollback_patch_v1": {
                        "rollback_to": 0.6,
                    },
                },
            },
        },
    )

    rows = attach_bounded_candidate_patch_memory_loop_fields_v1({})

    assert rows["BTCUSD"]["bounded_candidate_followup_action_v1"] == "PROMOTE_PATCH"
    assert rows["BTCUSD"]["bounded_candidate_followup_patch_catalog_state_v1"] == "PATCH_CATALOG_READY"
    assert rows["BTCUSD"]["bounded_candidate_followup_rollback_memory_state_v1"] == "NONE"

    assert rows["NAS100"]["bounded_candidate_followup_action_v1"] == "ROLLBACK_CANDIDATE"
    assert rows["NAS100"]["bounded_candidate_followup_patch_catalog_state_v1"] == "NONE"
    assert rows["NAS100"]["bounded_candidate_followup_rollback_memory_state_v1"] == "RECORDED"
    assert rows["NAS100"]["bounded_candidate_followup_recent_rollback_keys_v1"] == [
        "flow.conviction_building_floor"
    ]


def test_attach_recent_rollback_memory_fields_reads_previous_memory_file(tmp_path):
    report = {
        "rollback_memory_by_symbol_v1": {
            "BTCUSD": {
                "recent_rollback_keys_v1": ["flow.ambiguity_threshold"],
            }
        }
    }
    (tmp_path / "bounded_candidate_patch_memory_loop_latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rows = attach_recent_rollback_memory_fields_v1(
        {
            "BTCUSD": {"symbol": "BTCUSD"},
            "XAUUSD": {"symbol": "XAUUSD"},
        },
        shadow_auto_dir=tmp_path,
    )

    assert rows["BTCUSD"]["bounded_calibration_candidate_recent_rollback_keys_v1"] == [
        "flow.ambiguity_threshold"
    ]
    assert rows["XAUUSD"]["bounded_calibration_candidate_recent_rollback_keys_v1"] == []


def test_build_bounded_candidate_patch_memory_loop_summary_counts_catalog_and_memory(monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_lifecycle_feedback_loop_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_candidate_feedback_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                },
                "NAS100": {
                    "bounded_candidate_feedback_candidate_id_v1": "NAS100:flow.conviction_building_floor",
                    "symbol": "NAS100",
                },
                "XAUUSD": {
                    "bounded_candidate_feedback_candidate_id_v1": "XAUUSD:flow.ambiguity_threshold",
                    "symbol": "XAUUSD",
                },
            },
            "candidate_feedback_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "loop_action_v1": "PROMOTE_PATCH",
                    "source_outcome_v1": "PROMOTE",
                    "source_assessment_v1": "POSITIVE",
                    "promoted_patch_v1": {"current_value": 0.4, "proposed_value": 0.35, "delta": -0.05},
                },
                "NAS100:flow.conviction_building_floor": {
                    "candidate_id": "NAS100:flow.conviction_building_floor",
                    "symbol": "NAS100",
                    "learning_key": "flow.conviction_building_floor",
                    "loop_action_v1": "ROLLBACK_CANDIDATE",
                    "source_outcome_v1": "ROLLBACK",
                    "source_assessment_v1": "NEGATIVE",
                    "rollback_patch_v1": {"rollback_to": 0.6},
                },
                "XAUUSD:flow.ambiguity_threshold": {
                    "candidate_id": "XAUUSD:flow.ambiguity_threshold",
                    "symbol": "XAUUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "loop_action_v1": "KEEP_REVIEW",
                    "source_outcome_v1": "NONE",
                    "source_assessment_v1": "NONE",
                },
            },
        },
    )

    report = build_bounded_candidate_patch_memory_loop_summary_v1({})
    summary = report["summary"]

    assert summary["status"] == "READY"
    assert summary["patch_catalog_count"] == 1
    assert summary["rollback_memory_symbol_count"] == 1
    assert summary["patch_catalog_symbol_count_summary"] == {"BTCUSD": 1}
    assert summary["rollback_memory_symbol_count_summary"] == {"NAS100": 1}
    assert summary["rollback_memory_key_count_summary"] == {"flow.conviction_building_floor": 1}
    assert report["patch_catalog_v1"]["BTCUSD:flow.ambiguity_threshold"]["status_v1"] == "READY_FOR_REVIEW"
    assert report["rollback_memory_by_symbol_v1"]["NAS100"]["recent_rollback_keys_v1"] == [
        "flow.conviction_building_floor"
    ]


def test_generate_and_write_bounded_candidate_patch_memory_loop_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subject,
        "build_bounded_candidate_lifecycle_feedback_loop_summary_v1",
        lambda latest_signal_by_symbol: {
            "rows_by_symbol": {
                "BTCUSD": {
                    "bounded_candidate_feedback_candidate_id_v1": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                },
            },
            "candidate_feedback_entries_v1": {
                "BTCUSD:flow.ambiguity_threshold": {
                    "candidate_id": "BTCUSD:flow.ambiguity_threshold",
                    "symbol": "BTCUSD",
                    "learning_key": "flow.ambiguity_threshold",
                    "loop_action_v1": "PROMOTE_PATCH",
                    "source_outcome_v1": "PROMOTE",
                    "source_assessment_v1": "POSITIVE",
                    "promoted_patch_v1": {"current_value": 0.4, "proposed_value": 0.35, "delta": -0.05},
                },
            },
        },
    )

    report = generate_and_write_bounded_candidate_patch_memory_loop_summary_v1({}, shadow_auto_dir=tmp_path)

    assert report["summary"]["patch_catalog_count"] == 1
    assert report["artifact_paths"]["json_path"].endswith("bounded_candidate_patch_memory_loop_latest.json")
    assert report["artifact_paths"]["markdown_path"].endswith("bounded_candidate_patch_memory_loop_latest.md")
