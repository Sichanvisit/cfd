from pathlib import Path
import json

import pandas as pd

from backend.services.teacher_pattern_candidate_watch import (
    build_teacher_pattern_candidate_watch_cycle,
    write_teacher_pattern_candidate_watch_outputs,
)


def test_candidate_watch_cycle_skips_when_runtime_stale(tmp_path: Path):
    csv_path = tmp_path / "trade_closed_history.csv"
    csv_path.write_text("a\n1\n", encoding="utf-8")
    runtime_status = tmp_path / "runtime_status.json"

    cycle = build_teacher_pattern_candidate_watch_cycle(
        cycle=1,
        csv_path=csv_path,
        runtime_status_path=runtime_status,
        candidate_root=tmp_path / "candidates",
        reference_metrics_path=tmp_path / "reference.json",
        step9_watch_report_path=None,
        canary_evidence_path=None,
        require_runtime_fresh=True,
        runtime_max_age_sec=10.0,
        min_seed_rows=1,
        pattern_min_support=1,
        wait_quality_min_support=1,
        economic_target_min_support=1,
    )

    assert cycle["status"] == "runtime_stale_skip"


def test_candidate_watch_cycle_runs_full_chain_with_monkeypatched_dependencies(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "trade_closed_history.csv"
    pd.DataFrame([{"x": 1}]).to_csv(csv_path, index=False)
    runtime_status = tmp_path / "runtime_status.json"
    runtime_status.write_text("{}", encoding="utf-8")
    reference_path = tmp_path / "reference.json"
    reference_path.write_text("{}", encoding="utf-8")

    candidate_dir = tmp_path / "candidates" / "candidate_1"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    gate_json = candidate_dir / "teacher_pattern_promotion_gate_report.json"
    integration_json = candidate_dir / "teacher_pattern_execution_policy_integration_report.json"
    binding_json = candidate_dir / "teacher_pattern_execution_policy_log_only_binding_report.json"
    ai6_json = candidate_dir / "teacher_pattern_auto_promote_live_actuator_report.json"
    gate_json.write_text(json.dumps({"next_actions": ["hold"]}, ensure_ascii=False), encoding="utf-8")
    integration_json.write_text(json.dumps({"next_actions": ["disabled"]}, ensure_ascii=False), encoding="utf-8")
    binding_json.write_text(json.dumps({"next_actions": ["wait"]}, ensure_ascii=False), encoding="utf-8")
    ai6_json.write_text(json.dumps({"next_actions": ["keep"]}, ensure_ascii=False), encoding="utf-8")

    def _pipeline(*args, **kwargs):
        manifest_path = candidate_dir / "teacher_pattern_candidate_run_manifest.json"
        manifest = {
            "candidate_id": "candidate_1",
            "output_dir": str(candidate_dir),
            "summary_md_path": str(candidate_dir / "summary.md"),
            "promotion_decision": {"decision": "hold_no_material_gain"},
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return manifest

    def _gate(**kwargs):
        return {
            "gate_stage": "hold_offline",
            "recommended_action": "keep_current_baseline",
            "gate_report_path": str(gate_json),
            "gate_markdown_path": str(candidate_dir / "teacher_pattern_promotion_gate_report.md"),
        }

    def _integration(**kwargs):
        return {
            "integration_stage": "disabled_hold",
            "recommended_action": "keep_current_baseline",
            "execution_policy_report_path": str(integration_json),
            "execution_policy_markdown_path": str(candidate_dir / "teacher_pattern_execution_policy_integration_report.md"),
        }

    def _binding(**kwargs):
        return {
            "binding_mode": "disabled",
            "log_only_binding_report_path": str(binding_json),
            "log_only_binding_markdown_path": str(candidate_dir / "teacher_pattern_execution_policy_log_only_binding_report.md"),
        }

    def _ai6(**kwargs):
        return {
            "controller_stage": "hold_disabled",
            "recommended_action": "keep_current_baseline",
            "apply_requested": True,
            "applied_action": "none",
            "auto_promote_report_path": str(ai6_json),
            "auto_promote_markdown_path": str(candidate_dir / "teacher_pattern_auto_promote_live_actuator_report.md"),
            "active_candidate_state_path": str(tmp_path / "candidates" / "active_candidate_state.json"),
            "history_path": str(tmp_path / "candidates" / "auto_promote_history.jsonl"),
        }

    monkeypatch.setattr("backend.services.teacher_pattern_candidate_watch.run_teacher_pattern_candidate_pipeline", _pipeline)
    monkeypatch.setattr("backend.services.teacher_pattern_candidate_watch.run_teacher_pattern_promotion_gate", _gate)
    monkeypatch.setattr("backend.services.teacher_pattern_candidate_watch.run_teacher_pattern_execution_policy_integration", _integration)
    monkeypatch.setattr("backend.services.teacher_pattern_candidate_watch.run_teacher_pattern_execution_policy_log_only_binding", _binding)
    monkeypatch.setattr("backend.services.teacher_pattern_candidate_watch.run_teacher_pattern_auto_promote_live_actuator", _ai6)

    cycle = build_teacher_pattern_candidate_watch_cycle(
        cycle=2,
        csv_path=csv_path,
        runtime_status_path=runtime_status,
        candidate_root=tmp_path / "candidates",
        reference_metrics_path=reference_path,
        step9_watch_report_path=None,
        canary_evidence_path=None,
        require_runtime_fresh=False,
        runtime_max_age_sec=180.0,
        min_seed_rows=1,
        pattern_min_support=1,
        wait_quality_min_support=1,
        economic_target_min_support=1,
        apply_ai6=True,
    )

    assert cycle["status"] == "ran"
    assert cycle["apply_ai6_requested"] is True
    assert cycle["candidate"]["candidate_id"] == "candidate_1"
    assert cycle["gate"]["gate_stage"] == "hold_offline"
    assert cycle["integration"]["integration_stage"] == "disabled_hold"
    assert cycle["binding"]["binding_mode"] == "disabled"
    assert cycle["ai6"]["controller_stage"] == "hold_disabled"
    assert cycle["ai6"]["apply_requested"] is True
    assert cycle["ai6"]["active_candidate_state_path"].endswith("active_candidate_state.json")


def test_candidate_watch_outputs_write_latest_json_and_md(tmp_path: Path):
    report = {
        "latest_cycle": {
            "cycle": 1,
            "status": "ran",
            "runtime_status": {"fresh": True, "age_sec": 10.0},
            "candidate": {"candidate_id": "candidate_1", "promotion_decision": {"decision": "hold"}},
            "gate": {"gate_stage": "hold_offline", "next_actions": ["hold"]},
            "integration": {"integration_stage": "disabled_hold", "next_actions": ["disabled"]},
            "binding": {"binding_mode": "disabled", "next_actions": ["wait"]},
            "ai6": {
                "controller_stage": "hold_disabled",
                "apply_requested": True,
                "applied_action": "none",
                "active_candidate_state_path": str(tmp_path / "active_candidate_state.json"),
                "next_actions": ["keep"],
            },
        }
    }

    json_path, md_path = write_teacher_pattern_candidate_watch_outputs(
        out_dir=tmp_path,
        report=report,
    )

    assert json_path.exists()
    assert md_path.exists()
