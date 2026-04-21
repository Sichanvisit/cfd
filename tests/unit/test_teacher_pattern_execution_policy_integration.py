from pathlib import Path
import json

from backend.services.teacher_pattern_execution_policy_integration import (
    build_teacher_pattern_execution_policy_integration_report,
    run_teacher_pattern_execution_policy_integration,
)


def _gate(stage: str, *, recommended_action: str = "keep_current_baseline") -> dict:
    return {
        "candidate_id": "candidate_1",
        "gate_stage": stage,
        "recommended_action": recommended_action,
        "source_paths": {
            "compare_report_path": "compare.json",
        },
    }


def _compare(
    *,
    economic_ready: bool,
    wait_quality_ready: bool,
    belief_ready: bool = False,
    barrier_ready: bool = False,
    forecast_transition_ready: bool = False,
    forecast_management_ready: bool = False,
) -> dict:
    def _task(ready: bool) -> dict:
        return {
            "candidate": {
                "ready": ready,
            }
        }

    return {
        "tasks": {
            "group_task": _task(True),
            "pattern_task": _task(True),
            "economic_total_task": _task(economic_ready),
            "wait_quality_task": _task(wait_quality_ready),
            "belief_outcome_task": _task(belief_ready),
            "barrier_outcome_task": _task(barrier_ready),
            "forecast_transition_task": _task(forecast_transition_ready),
            "forecast_management_task": _task(forecast_management_ready),
        }
    }


def _runtime() -> dict:
    return {
        "entry_threshold": 45,
        "exit_threshold": 150,
        "semantic_live_config": {
            "mode": "disabled",
            "symbol_allowlist": ["BTCUSD", "NAS100"],
            "entry_stage_allowlist": [],
        },
    }


def test_execution_policy_integration_holds_when_gate_is_offline():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("hold_offline"),
        compare_report=_compare(economic_ready=True, wait_quality_ready=False),
        runtime_status=_runtime(),
    )

    assert report["integration_stage"] == "disabled_hold"
    assert report["recommended_surfaces"]["threshold_surface"]["enabled"] is False


def test_execution_policy_integration_recommends_read_only_before_canary():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("shadow_ready", recommended_action="run_shadow_then_collect_canary_evidence"),
        compare_report=_compare(economic_ready=True, wait_quality_ready=False),
        runtime_status=_runtime(),
    )

    assert report["integration_stage"] == "read_only_recommendation"
    assert report["rollout_plan"]["recommended_rollout_mode"] == "disabled"


def test_execution_policy_integration_enables_log_only_when_gate_is_log_only_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("log_only_ready", recommended_action="promote_log_only_while_seed_accumulates"),
        compare_report=_compare(economic_ready=True, wait_quality_ready=False),
        runtime_status=_runtime(),
    )

    assert report["integration_stage"] == "log_only_candidate_bind_ready"
    assert report["recommended_surfaces"]["threshold_surface"]["enabled"] is True
    assert report["rollout_plan"]["recommended_rollout_mode"] == "log_only"
    assert report["rollout_plan"]["narrow_canary_after_log_only"] is False


def test_execution_policy_integration_enables_threshold_and_size_only_when_promote_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("promote_ready", recommended_action="promote_with_bounded_ai5_bind"),
        compare_report=_compare(economic_ready=True, wait_quality_ready=False),
        runtime_status=_runtime(),
    )

    assert report["integration_stage"] == "log_only_candidate_bind_ready"
    assert report["recommended_surfaces"]["threshold_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["size_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["wait_surface"]["enabled"] is False


def test_execution_policy_integration_enables_wait_surface_when_wait_quality_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("promote_ready", recommended_action="promote_with_bounded_ai5_bind"),
        compare_report=_compare(economic_ready=True, wait_quality_ready=True),
        runtime_status=_runtime(),
    )

    assert report["recommended_surfaces"]["wait_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["wait_surface"]["mode"] == "log_only"


def test_execution_policy_integration_enables_belief_overlay_surface_when_aux_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("log_only_ready", recommended_action="promote_log_only_while_seed_accumulates"),
        compare_report=_compare(
            economic_ready=True,
            wait_quality_ready=False,
            belief_ready=True,
        ),
        runtime_status=_runtime(),
    )

    assert report["task_readiness"]["belief_outcome_task_ready"] is True
    assert report["recommended_surfaces"]["belief_overlay_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["belief_overlay_surface"]["mode"] == "log_only"


def test_execution_policy_integration_enables_barrier_overlay_surface_when_aux_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("log_only_ready", recommended_action="promote_log_only_while_seed_accumulates"),
        compare_report=_compare(
            economic_ready=True,
            wait_quality_ready=False,
            barrier_ready=True,
        ),
        runtime_status=_runtime(),
    )

    assert report["task_readiness"]["barrier_outcome_task_ready"] is True
    assert report["recommended_surfaces"]["barrier_overlay_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["barrier_overlay_surface"]["mode"] == "log_only"


def test_execution_policy_integration_enables_forecast_overlay_surface_when_aux_ready():
    report = build_teacher_pattern_execution_policy_integration_report(
        _gate("log_only_ready", recommended_action="promote_log_only_while_seed_accumulates"),
        compare_report=_compare(
            economic_ready=True,
            wait_quality_ready=False,
            forecast_transition_ready=True,
            forecast_management_ready=False,
        ),
        runtime_status=_runtime(),
    )

    assert report["task_readiness"]["forecast_transition_task_ready"] is True
    assert report["recommended_surfaces"]["forecast_overlay_surface"]["enabled"] is True
    assert report["recommended_surfaces"]["forecast_overlay_surface"]["mode"] == "log_only"


def test_run_execution_policy_integration_writes_outputs(tmp_path: Path, monkeypatch):
    root = tmp_path.resolve()
    monkeypatch.chdir(root)
    compare_path = root / "compare.json"
    gate_path = root / "teacher_pattern_promotion_gate_report.json"
    runtime_path = root / "runtime_status.json"

    compare_path.write_text(
        json.dumps(_compare(economic_ready=True, wait_quality_ready=False), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    gate_path.write_text(
        json.dumps(
            {
                **_gate("promote_ready", recommended_action="promote_with_bounded_ai5_bind"),
                "source_paths": {
                    "compare_report_path": str(compare_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    runtime_path.write_text(json.dumps(_runtime(), ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_teacher_pattern_execution_policy_integration(
        gate_report_path=gate_path,
        runtime_status_path=runtime_path,
    )

    assert result["integration_stage"] == "log_only_candidate_bind_ready"
    assert Path(result["execution_policy_report_path"]).exists()
    assert Path(result["execution_policy_markdown_path"]).exists()
