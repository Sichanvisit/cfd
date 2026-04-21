import json

from backend.services.ca2_r0_stability_audit import (
    build_ca2_r0_stability_audit,
    generate_and_write_ca2_r0_stability_audit,
)


def test_build_ca2_r0_stability_audit_first_snapshot_is_hold():
    report = build_ca2_r0_stability_audit(
        {
            "summary": {
                "symbol_count": 3,
                "execution_diff_surface_count": 3,
                "flow_sync_match_count": 3,
                "ai_entry_trace_count": 5,
                "ai_entry_trace_execution_diff_count": 3,
            }
        },
        accuracy_report={
            "summary": {
                "primary_measured_count": 12,
                "primary_correct_rate": 0.5,
                "resolved_observation_count": 20,
            }
        },
        previous_summary={},
    )

    summary = report["summary"]
    assert summary["status"] == "HOLD"
    assert "first_snapshot" in summary["status_reasons"]


def test_build_ca2_r0_stability_audit_ready_when_counts_are_full_and_growing():
    report = build_ca2_r0_stability_audit(
        {
            "summary": {
                "symbol_count": 3,
                "execution_diff_surface_count": 3,
                "flow_sync_match_count": 3,
                "ai_entry_trace_count": 7,
                "ai_entry_trace_execution_diff_count": 3,
            }
        },
        accuracy_report={
            "summary": {
                "primary_measured_count": 30,
                "primary_correct_rate": 0.6,
                "resolved_observation_count": 50,
            }
        },
        previous_summary={
            "primary_measured_count": 24,
            "resolved_observation_count": 40,
            "execution_diff_surface_count": 3,
            "flow_sync_match_count": 3,
        },
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["primary_measured_count_delta"] == 6
    assert summary["resolved_observation_count_delta"] == 10


def test_build_ca2_r0_stability_audit_blocked_on_accuracy_regression():
    report = build_ca2_r0_stability_audit(
        {
            "summary": {
                "symbol_count": 3,
                "execution_diff_surface_count": 3,
                "flow_sync_match_count": 3,
            }
        },
        accuracy_report={
            "summary": {
                "primary_measured_count": 10,
                "primary_correct_rate": 0.4,
                "resolved_observation_count": 18,
            }
        },
        previous_summary={
            "primary_measured_count": 11,
            "resolved_observation_count": 19,
        },
    )

    summary = report["summary"]
    assert summary["status"] == "BLOCKED"
    assert "primary_measured_regressed" in summary["status_reasons"]
    assert "resolved_observation_regressed" in summary["status_reasons"]


def test_generate_and_write_ca2_r0_stability_audit_writes_artifacts(tmp_path):
    report = generate_and_write_ca2_r0_stability_audit(
        {
            "summary": {
                "symbol_count": 1,
                "execution_diff_surface_count": 1,
                "flow_sync_match_count": 1,
                "ai_entry_trace_count": 1,
                "ai_entry_trace_execution_diff_count": 1,
            }
        },
        accuracy_report={
            "summary": {
                "primary_measured_count": 5,
                "primary_correct_rate": 0.8,
                "resolved_observation_count": 7,
            }
        },
        shadow_auto_dir=tmp_path,
    )

    json_path = tmp_path / "ca2_r0_stability_latest.json"
    md_path = tmp_path / "ca2_r0_stability_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
