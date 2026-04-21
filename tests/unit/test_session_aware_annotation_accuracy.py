import json

from backend.services.session_aware_annotation_accuracy import (
    SESSION_AWARE_ANNOTATION_ACCURACY_CONTRACT_VERSION,
    build_session_aware_annotation_accuracy_contract_v1,
    build_session_aware_annotation_accuracy_summary_v1,
    generate_and_write_session_aware_annotation_accuracy_v1,
)


def test_build_session_aware_annotation_accuracy_contract_v1_exposes_fields():
    contract = build_session_aware_annotation_accuracy_contract_v1()

    assert contract["contract_version"] == SESSION_AWARE_ANNOTATION_ACCURACY_CONTRACT_VERSION
    assert contract["status"] == "READY"
    assert "direction_accuracy_by_session" in contract["fields"]
    assert "phase_accuracy_by_session" in contract["fields"]


def test_build_session_aware_annotation_accuracy_summary_v1_is_hold_until_phase_labels_exist():
    report = build_session_aware_annotation_accuracy_summary_v1(
        session_split_report={
            "summary": {
                "correct_rate_by_session": {"EU": 0.41, "US": 0.64},
                "measured_count_by_session": {"EU": 84, "US": 42},
                "session_difference_significance": {"status": "SIGNIFICANT", "pair": "EU|US"},
            }
        },
        should_have_done_report={
            "summary": {
                "candidate_count_by_session": {"EU": 2, "US": 3},
            }
        },
        canonical_surface_report={
            "rows_by_symbol": {
                "NAS100": {
                    "canonical_session_bucket_v1": "US",
                    "canonical_runtime_execution_alignment_v1": "DIVERGED",
                },
                "BTCUSD": {
                    "canonical_session_bucket_v1": "EU",
                    "canonical_runtime_execution_alignment_v1": "MATCH",
                },
            }
        },
    )

    summary = report["summary"]
    assert summary["status"] == "HOLD"
    assert "direction_ready_phase_pending" in summary["status_reasons"]
    assert summary["direction_accuracy_by_session"]["US"] == 0.64
    assert summary["annotation_candidate_count_by_session"]["US"] == 3
    assert summary["runtime_execution_divergence_count_by_session"]["US"] == 1
    assert summary["phase_accuracy_data_status"] == "INSUFFICIENT_LABELED_ANNOTATIONS"


def test_generate_and_write_session_aware_annotation_accuracy_v1_writes_artifacts(tmp_path):
    report = generate_and_write_session_aware_annotation_accuracy_v1(
        session_split_report={
            "summary": {
                "correct_rate_by_session": {"EU_US_OVERLAP": 0.55},
                "measured_count_by_session": {"EU_US_OVERLAP": 61},
                "session_difference_significance": {"status": "REFERENCE_ONLY"},
            }
        },
        should_have_done_report={"summary": {"candidate_count_by_session": {"EU_US_OVERLAP": 2}}},
        canonical_surface_report={
            "rows_by_symbol": {
                "XAUUSD": {
                    "canonical_session_bucket_v1": "EU_US_OVERLAP",
                    "canonical_runtime_execution_alignment_v1": "DIVERGED",
                }
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "session_aware_annotation_accuracy_latest.json"
    md_path = tmp_path / "session_aware_annotation_accuracy_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
