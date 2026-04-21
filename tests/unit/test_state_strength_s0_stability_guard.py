import json

from backend.services.state_strength_s0_stability_guard import (
    build_state_strength_s0_stability_report_v1,
    generate_and_write_state_strength_s0_stability_report_v1,
)


def _write_artifacts(base_dir, name: str):
    json_path = base_dir / f"{name}.json"
    markdown_path = base_dir / f"{name}.md"
    json_path.write_text("{}", encoding="utf-8")
    markdown_path.write_text("# ok\n", encoding="utf-8")
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def _report(base_dir, name: str, *, status: str = "READY"):
    return {
        "summary": {
            "generated_at": "2026-04-15T10:00:00+09:00",
            "status": status,
        },
        "artifact_paths": _write_artifacts(base_dir, name),
    }


def test_state_strength_s0_stability_report_ready_when_dependencies_are_fresh(tmp_path):
    report = build_state_strength_s0_stability_report_v1(
        runtime_signal_wiring_audit_report=_report(tmp_path, "runtime_signal_wiring_audit"),
        ca2_r0_stability_report=_report(tmp_path, "ca2_r0_stability", status="HOLD"),
        ca2_session_split_report=_report(tmp_path, "ca2_session_split"),
        should_have_done_report=_report(tmp_path, "should_have_done"),
        canonical_surface_report=_report(tmp_path, "canonical_surface"),
        session_bias_shadow_report=_report(tmp_path, "session_bias_shadow"),
        freshness_threshold_sec=999999,
    )

    summary = report["summary"]
    assert summary["status"] == "READY"
    assert summary["summary_ready_count"] == 6
    assert summary["artifact_ready_count"] == 6
    assert summary["fresh_dependency_count"] == 6


def test_state_strength_s0_stability_report_hold_when_artifact_is_missing(tmp_path):
    broken = _report(tmp_path, "runtime_signal_wiring_audit")
    missing_json_path = tmp_path / "runtime_signal_wiring_audit.json"
    missing_json_path.unlink()

    report = build_state_strength_s0_stability_report_v1(
        runtime_signal_wiring_audit_report=broken,
        ca2_r0_stability_report=_report(tmp_path, "ca2_r0_stability"),
        ca2_session_split_report=_report(tmp_path, "ca2_session_split"),
        should_have_done_report=_report(tmp_path, "should_have_done"),
        canonical_surface_report=_report(tmp_path, "canonical_surface"),
        session_bias_shadow_report=_report(tmp_path, "session_bias_shadow"),
        freshness_threshold_sec=999999,
    )

    summary = report["summary"]
    assert summary["status"] == "HOLD"
    assert "hold_dependency::runtime_signal_wiring_audit_summary_v1" in summary["status_reasons"]


def test_state_strength_s0_stability_report_blocked_on_missing_summary_or_upstream_block(tmp_path):
    report = build_state_strength_s0_stability_report_v1(
        runtime_signal_wiring_audit_report={},
        ca2_r0_stability_report=_report(tmp_path, "ca2_r0_stability"),
        ca2_session_split_report=_report(tmp_path, "ca2_session_split", status="BLOCKED"),
        should_have_done_report=_report(tmp_path, "should_have_done"),
        canonical_surface_report=_report(tmp_path, "canonical_surface"),
        session_bias_shadow_report=_report(tmp_path, "session_bias_shadow"),
        freshness_threshold_sec=999999,
    )

    summary = report["summary"]
    assert summary["status"] == "BLOCKED"
    assert "blocked_dependency::runtime_signal_wiring_audit_summary_v1" in summary["status_reasons"]


def test_generate_and_write_state_strength_s0_stability_report_writes_artifacts(tmp_path):
    report = generate_and_write_state_strength_s0_stability_report_v1(
        runtime_signal_wiring_audit_report=_report(tmp_path, "runtime_signal_wiring_audit"),
        ca2_r0_stability_report=_report(tmp_path, "ca2_r0_stability"),
        ca2_session_split_report=_report(tmp_path, "ca2_session_split"),
        should_have_done_report=_report(tmp_path, "should_have_done"),
        canonical_surface_report=_report(tmp_path, "canonical_surface"),
        session_bias_shadow_report=_report(tmp_path, "session_bias_shadow"),
        shadow_auto_dir=tmp_path,
        freshness_threshold_sec=999999,
    )

    json_path = tmp_path / "state_strength_s0_stability_latest.json"
    md_path = tmp_path / "state_strength_s0_stability_latest.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["json_path"] == str(json_path)
    assert report["artifact_paths"]["markdown_path"] == str(md_path)
