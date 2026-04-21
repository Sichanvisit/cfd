from pathlib import Path
import json

from backend.services.teacher_pattern_execution_policy_log_only_binding import (
    build_teacher_pattern_execution_policy_log_only_binding_report,
    run_teacher_pattern_execution_policy_log_only_binding,
)


def _execution_report(stage: str) -> dict:
    return {
        "candidate_id": "candidate_1",
        "integration_stage": stage,
        "recommended_surfaces": {
            "threshold_surface": {
                "enabled": True,
                "mode": "log_only",
                "symbol_scope": ["BTCUSD", "NAS100"],
                "entry_stage_scope": ["PROBE", "READY"],
                "recommended_adjustment_points_max_abs": 4,
                "current_entry_threshold": 45.0,
                "reason": "economic_total_task_ready",
            },
            "size_surface": {
                "enabled": True,
                "mode": "log_only",
                "symbol_scope": ["BTCUSD", "NAS100"],
                "recommended_min_multiplier": 0.75,
                "recommended_max_multiplier": 1.0,
                "reason": "economic_total_task_ready",
            },
            "wait_surface": {
                "enabled": True,
                "mode": "log_only",
                "reason": "wait_quality_task_ready",
            },
            "belief_overlay_surface": {
                "enabled": True,
                "mode": "log_only",
                "recommended_scope": "hold_wait_flip_reduce_hypothesis_trace",
                "recommended_families": [
                    "hold_bias",
                    "wait_bias",
                    "flip_alert",
                    "reduce_alert",
                ],
                "reason": "belief_outcome_auxiliary_task_ready",
            },
            "barrier_overlay_surface": {
                "enabled": True,
                "mode": "log_only",
                "recommended_scope": "block_wait_relief_hypothesis_trace",
                "recommended_families": [
                    "block_bias",
                    "wait_bias",
                    "relief_watch",
                    "relief_release_bias",
                ],
                "reason": "barrier_outcome_auxiliary_task_ready",
            },
            "forecast_overlay_surface": {
                "enabled": True,
                "mode": "log_only",
                "recommended_scope": "threshold_size_wait_management_hypothesis_trace",
                "transition_task_ready": True,
                "management_task_ready": False,
                "reason": "forecast_state25_auxiliary_task_ready",
            },
        },
        "runtime_snapshot": {
            "symbol_allowlist": ["BTCUSD", "NAS100"],
        },
        "rollout_plan": {
            "symbol_allowlist_target": ["BTCUSD", "NAS100"],
            "entry_stage_allowlist_target": ["PROBE", "READY"],
        },
    }


def test_log_only_binding_stays_disabled_before_log_only_stage():
    report = build_teacher_pattern_execution_policy_log_only_binding_report(
        _execution_report("disabled_hold"),
    )

    assert report["binding_mode"] == "disabled"
    assert "integration_stage_not_log_only_ready" in report["blockers"]
    assert report["threshold_binding"]["enabled"] is False


def test_log_only_binding_enables_threshold_and_size_only():
    report = build_teacher_pattern_execution_policy_log_only_binding_report(
        _execution_report("log_only_candidate_bind_ready"),
    )

    assert report["binding_mode"] == "log_only"
    assert report["threshold_binding"]["enabled"] is True
    assert report["size_binding"]["enabled"] is True
    assert report["wait_binding"]["enabled"] is False
    assert report["belief_overlay_binding"]["enabled"] is True
    assert report["barrier_overlay_binding"]["enabled"] is True
    assert report["forecast_overlay_binding"]["enabled"] is True


def test_run_log_only_binding_writes_outputs(tmp_path: Path):
    report_path = tmp_path / "teacher_pattern_execution_policy_integration_report.json"
    candidate_dir = tmp_path / "candidate_1"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                **_execution_report("log_only_candidate_bind_ready"),
                "execution_policy_report_path": str(candidate_dir / "teacher_pattern_execution_policy_integration_report.json"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_teacher_pattern_execution_policy_log_only_binding(
        execution_policy_report_path=report_path,
    )

    assert result["binding_mode"] == "log_only"
    assert Path(result["log_only_binding_report_path"]).exists()
    assert Path(result["log_only_binding_markdown_path"]).exists()
