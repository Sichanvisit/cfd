from pathlib import Path
import json
import subprocess

from backend.services.manual_truth_calibration_watch import (
    build_manual_truth_calibration_cycle,
    build_manual_truth_calibration_tasks,
    write_manual_truth_calibration_watch_outputs,
)


def test_calibration_watch_tasks_include_countertrend_materialization_check(tmp_path: Path) -> None:
    tasks = build_manual_truth_calibration_tasks(tmp_path)
    task_names = {task.name: task for task in tasks}

    assert "countertrend_materialization_check" in task_names
    assert task_names["countertrend_materialization_check"].script_path.name == "build_countertrend_materialization_check.py"
    assert task_names["countertrend_materialization_check"].every_n_cycles == 12
    assert "countertrend_down_bootstrap_validation" in task_names
    assert (
        task_names["countertrend_down_bootstrap_validation"].script_path.name
        == "build_countertrend_down_bootstrap_validation.py"
    )
    assert task_names["countertrend_down_bootstrap_validation"].every_n_cycles == 12
    assert "entry_performance_baseline" in task_names
    assert task_names["entry_performance_baseline"].script_path.name == "build_entry_performance_baseline.py"
    assert task_names["entry_performance_baseline"].every_n_cycles == 12
    assert "distribution_promotion_gate_baseline" in task_names
    assert (
        task_names["distribution_promotion_gate_baseline"].script_path.name
        == "build_distribution_promotion_gate_baseline.py"
    )
    assert task_names["distribution_promotion_gate_baseline"].every_n_cycles == 12
    assert "market_adapter_layer" in task_names
    assert task_names["market_adapter_layer"].script_path.name == "build_market_adapter_layer.py"
    assert task_names["market_adapter_layer"].every_n_cycles == 12
    assert "multi_surface_preview_dataset_export" in task_names
    assert (
        task_names["multi_surface_preview_dataset_export"].script_path.name
        == "build_multi_surface_preview_dataset_export.py"
    )
    assert task_names["multi_surface_preview_dataset_export"].every_n_cycles == 12
    assert "symbol_surface_preview_evaluation" in task_names
    assert (
        task_names["symbol_surface_preview_evaluation"].script_path.name
        == "build_symbol_surface_preview_evaluation.py"
    )
    assert task_names["symbol_surface_preview_evaluation"].every_n_cycles == 12
    assert "bounded_rollout_candidate_gate" in task_names
    assert (
        task_names["bounded_rollout_candidate_gate"].script_path.name
        == "build_bounded_rollout_candidate_gate.py"
    )
    assert task_names["bounded_rollout_candidate_gate"].every_n_cycles == 12
    assert "bounded_rollout_review_manifest" in task_names
    assert (
        task_names["bounded_rollout_review_manifest"].script_path.name
        == "build_bounded_rollout_review_manifest.py"
    )
    assert task_names["bounded_rollout_review_manifest"].every_n_cycles == 12
    assert "bounded_rollout_signoff_criteria" in task_names
    assert (
        task_names["bounded_rollout_signoff_criteria"].script_path.name
        == "build_bounded_rollout_signoff_criteria.py"
    )
    assert task_names["bounded_rollout_signoff_criteria"].every_n_cycles == 12
    assert "btc_initial_entry_canary_signoff_packet" in task_names
    assert (
        task_names["btc_initial_entry_canary_signoff_packet"].script_path.name
        == "build_btc_initial_entry_canary_signoff_packet.py"
    )
    assert task_names["btc_initial_entry_canary_signoff_packet"].every_n_cycles == 12
    assert "symbol_surface_canary_signoff_packet" in task_names
    assert (
        task_names["symbol_surface_canary_signoff_packet"].script_path.name
        == "build_symbol_surface_canary_signoff_packet.py"
    )
    assert task_names["symbol_surface_canary_signoff_packet"].every_n_cycles == 12
    assert "initial_entry_label_resolution_queue" in task_names
    assert (
        task_names["initial_entry_label_resolution_queue"].script_path.name
        == "build_initial_entry_label_resolution_queue.py"
    )
    assert task_names["initial_entry_label_resolution_queue"].every_n_cycles == 12
    assert "multi_surface_data_gap_queue" in task_names
    assert (
        task_names["multi_surface_data_gap_queue"].script_path.name
        == "build_multi_surface_data_gap_queue.py"
    )
    assert task_names["multi_surface_data_gap_queue"].every_n_cycles == 12
    assert "bounded_btc_review_canary_activation_contract" in task_names
    assert (
        task_names["bounded_btc_review_canary_activation_contract"].script_path.name
        == "build_bounded_btc_review_canary_activation_contract.py"
    )
    assert task_names["bounded_btc_review_canary_activation_contract"].every_n_cycles == 12
    assert "bounded_symbol_surface_activation_contract" in task_names
    assert (
        task_names["bounded_symbol_surface_activation_contract"].script_path.name
        == "build_bounded_symbol_surface_activation_contract.py"
    )
    assert task_names["bounded_symbol_surface_activation_contract"].every_n_cycles == 12
    assert "initial_entry_label_resolution_draft" in task_names
    assert (
        task_names["initial_entry_label_resolution_draft"].script_path.name
        == "build_initial_entry_label_resolution_draft.py"
    )
    assert task_names["initial_entry_label_resolution_draft"].every_n_cycles == 12
    assert "initial_entry_label_resolution_apply" in task_names
    assert (
        task_names["initial_entry_label_resolution_apply"].script_path.name
        == "build_initial_entry_label_resolution_apply.py"
    )
    assert task_names["initial_entry_label_resolution_apply"].every_n_cycles == 12
    assert "follow_through_negative_expansion_draft" in task_names
    assert (
        task_names["follow_through_negative_expansion_draft"].script_path.name
        == "build_follow_through_negative_expansion_draft.py"
    )
    assert task_names["follow_through_negative_expansion_draft"].every_n_cycles == 12
    assert "hold_exit_augmentation_draft" in task_names
    assert (
        task_names["hold_exit_augmentation_draft"].script_path.name
        == "build_hold_exit_augmentation_draft.py"
    )
    assert task_names["hold_exit_augmentation_draft"].every_n_cycles == 12
    assert "wrong_side_conflict_harvest" in task_names
    assert (
        task_names["wrong_side_conflict_harvest"].script_path.name
        == "build_wrong_side_conflict_harvest.py"
    )
    assert task_names["wrong_side_conflict_harvest"].every_n_cycles == 12


def test_calibration_watch_cycle_skips_when_runtime_stale(tmp_path: Path):
    runtime_status = tmp_path / "runtime_status.json"

    cycle = build_manual_truth_calibration_cycle(
        cycle=1,
        root=tmp_path,
        python_exe=Path("python"),
        runtime_status_path=runtime_status,
        require_runtime_fresh=True,
        runtime_max_age_sec=10.0,
        step_timeout_sec=10.0,
    )

    assert cycle["status"] == "runtime_stale_skip"
    assert cycle["task_count"] == 0


def test_calibration_watch_cycle_runs_tasks_with_runner(tmp_path: Path):
    runtime_status = tmp_path / "runtime_status.json"
    runtime_status.write_text("{}", encoding="utf-8")

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for task in build_manual_truth_calibration_tasks(tmp_path):
        task.script_path.write_text("print('ok')", encoding="utf-8")

    def _runner(command: list[str], cwd: Path, timeout_sec: float) -> subprocess.CompletedProcess[str]:
        payload = {"script": Path(command[1]).name, "cwd": str(cwd)}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    cycle = build_manual_truth_calibration_cycle(
        cycle=2,
        root=tmp_path,
        python_exe=Path("python"),
        runtime_status_path=runtime_status,
        require_runtime_fresh=False,
        runtime_max_age_sec=180.0,
        step_timeout_sec=10.0,
        runner=_runner,
    )

    assert cycle["status"] == "ran"
    assert cycle["task_count"] >= 5
    assert cycle["executed_task_count"] >= 5
    assert cycle["skipped_task_count"] >= 1
    assert cycle["ok_task_count"] == cycle["executed_task_count"]
    assert cycle["failed_task_count"] == 0
    assert cycle["latest_task"]["ok"] is True
    first_executed = next(row for row in cycle["tasks"] if row["executed"])
    assert first_executed["summary"]["cwd"] == str(tmp_path)


def test_calibration_watch_outputs_write_latest_json_and_md(tmp_path: Path):
    report = {
        "latest_cycle": {
            "cycle": 1,
            "status": "ran",
            "runtime_status": {"fresh": True, "age_sec": 3.0},
            "task_count": 2,
            "executed_task_count": 1,
            "skipped_task_count": 1,
            "ok_task_count": 1,
            "failed_task_count": 0,
            "latest_task": {"name": "manual_vs_heuristic_comparison", "ok": True},
            "tasks": [
                {
                    "name": "manual_vs_heuristic_comparison",
                    "executed": True,
                    "ok": True,
                    "returncode": 0,
                    "duration_sec": 1.0,
                    "every_n_cycles": 1,
                    "script_path": str(tmp_path / "scripts" / "build_manual_vs_heuristic_comparison_report.py"),
                }
            ],
            "next_actions": ["keep refreshing outputs"],
        }
    }

    json_path, md_path = write_manual_truth_calibration_watch_outputs(out_dir=tmp_path, report=report)

    assert json_path.exists()
    assert md_path.exists()
