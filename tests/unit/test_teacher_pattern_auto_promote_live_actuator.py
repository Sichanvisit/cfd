from pathlib import Path
import json

from backend.services.teacher_pattern_auto_promote_live_actuator import (
    build_teacher_pattern_auto_promote_live_actuator_report,
    run_teacher_pattern_auto_promote_live_actuator,
)


def _gate(stage: str, candidate_id: str = "candidate_1") -> dict:
    return {
        "candidate_id": candidate_id,
        "gate_stage": stage,
        "recommended_action": "keep_current_baseline",
    }


def _execution(stage: str, candidate_id: str = "candidate_1") -> dict:
    return {
        "candidate_id": candidate_id,
        "integration_stage": stage,
    }


def _binding(mode: str, candidate_id: str = "candidate_1") -> dict:
    return {
        "candidate_id": candidate_id,
        "binding_mode": mode,
        "proposed_runtime_patch": {
            "apply_now": False,
            "state25_execution_bind_mode": mode,
            "state25_threshold_log_only_enabled": mode == "log_only",
        },
    }


def test_auto_promote_hold_when_gate_not_ready():
    report = build_teacher_pattern_auto_promote_live_actuator_report(
        _gate("hold_offline"),
        execution_policy_report=_execution("disabled_hold"),
        log_only_binding_report=_binding("disabled"),
    )

    assert report["controller_stage"] == "hold_disabled"
    assert report["auto_promote_plan"]["eligible"] is False


def test_auto_promote_ready_when_log_only_gate_and_binding_are_ready():
    report = build_teacher_pattern_auto_promote_live_actuator_report(
        _gate("log_only_ready"),
        execution_policy_report=_execution("log_only_candidate_bind_ready"),
        log_only_binding_report=_binding("log_only"),
    )

    assert report["controller_stage"] == "promote_log_only_ready"
    assert report["auto_promote_plan"]["eligible"] is True


def test_auto_promote_ready_when_gate_and_binding_are_ready():
    report = build_teacher_pattern_auto_promote_live_actuator_report(
        _gate("promote_ready"),
        execution_policy_report=_execution("log_only_candidate_bind_ready"),
        log_only_binding_report=_binding("log_only"),
    )

    assert report["controller_stage"] == "promote_log_only_ready"
    assert report["auto_promote_plan"]["eligible"] is True
    assert report["live_actuator_plan"]["mode"] == "log_only"


def test_rollback_ready_only_when_candidate_is_active():
    report = build_teacher_pattern_auto_promote_live_actuator_report(
        _gate("rollback_recommended"),
        execution_policy_report=_execution("disabled_rollback_hold"),
        log_only_binding_report=_binding("disabled"),
        active_candidate_state={
            "active_candidate_id": "candidate_1",
            "current_rollout_phase": "log_only",
            "current_binding_mode": "log_only",
        },
    )

    assert report["controller_stage"] == "rollback_ready"
    assert report["rollback_plan"]["eligible"] is True


def test_run_auto_promote_apply_writes_active_state_and_history(tmp_path: Path):
    candidate_dir = tmp_path / "candidate_1"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    gate_path = candidate_dir / "teacher_pattern_promotion_gate_report.json"
    execution_path = candidate_dir / "teacher_pattern_execution_policy_integration_report.json"
    binding_path = candidate_dir / "teacher_pattern_execution_policy_log_only_binding_report.json"
    state_path = tmp_path / "active_candidate_state.json"
    history_path = tmp_path / "auto_promote_history.jsonl"

    gate_path.write_text(json.dumps(_gate("promote_ready"), ensure_ascii=False, indent=2), encoding="utf-8")
    execution_path.write_text(
        json.dumps(_execution("log_only_candidate_bind_ready"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    binding_path.write_text(json.dumps(_binding("log_only"), ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_teacher_pattern_auto_promote_live_actuator(
        gate_report_path=gate_path,
        execution_policy_report_path=execution_path,
        log_only_binding_report_path=binding_path,
        active_candidate_state_path=state_path,
        history_path=history_path,
        apply=True,
    )

    assert result["apply_requested"] is True
    assert result["applied_action"] == "promote_log_only"
    assert result["active_candidate_state_path"] == str(state_path)
    assert result["history_path"] == str(history_path)
    assert state_path.exists()
    assert history_path.exists()
