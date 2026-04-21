from pathlib import Path
import json

from backend.services.teacher_pattern_promotion_gate import (
    build_teacher_pattern_promotion_gate_report,
    run_teacher_pattern_promotion_gate,
)


def _manifest(tmp_path: Path) -> dict:
    output_dir = tmp_path / "candidate_1"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "candidate_id": "candidate_1",
        "output_dir": str(output_dir),
        "compare_report_path": str(output_dir / "teacher_pattern_candidate_compare_report.json"),
        "promotion_decision_path": str(output_dir / "teacher_pattern_candidate_promotion_decision.json"),
    }


def _compare() -> dict:
    return {
        "reference_available": True,
        "reference_baseline_ready": True,
        "candidate_baseline_ready": True,
        "belief_compare_summary": {
            "belief_ready_delta": {
                "candidate_ready": True,
                "reference_ready": False,
                "target_rows_delta": 42,
                "high_medium_confidence_rows_delta": 42,
            },
            "belief_quality_delta": {
                "wrong_hold_ratio_delta": -0.04,
                "premature_flip_ratio_delta": 0.01,
                "missed_flip_ratio_delta": -0.02,
                "high_confidence_share_delta": 0.08,
            },
        },
        "barrier_compare_summary": {
            "barrier_ready_delta": {
                "candidate_ready": True,
                "reference_ready": False,
                "target_rows_delta": 24,
                "high_medium_confidence_rows_delta": 24,
            },
            "barrier_quality_delta": {
                "overblock_ratio_delta": -0.03,
                "avoided_loss_rate_delta": 0.05,
                "missed_profit_rate_delta": -0.02,
                "correct_wait_rate_delta": 0.03,
                "relief_failure_rate_delta": -0.01,
                "loss_avoided_r_mean_delta": 0.08,
                "profit_missed_r_mean_delta": -0.04,
                "wait_value_r_mean_delta": 0.06,
            },
        },
        "forecast_state25_compare_summary": {
            "transition_ready_delta": {
                "candidate_ready": True,
                "reference_ready": False,
                "target_rows_delta": 12,
            },
            "management_ready_delta": {
                "candidate_ready": False,
                "reference_ready": False,
                "target_rows_delta": 0,
            },
        },
    }


def _decision(name: str) -> dict:
    return {
        "decision": name,
        "recommended_action": "ai4_gate_review",
        "blockers": [],
        "warnings": [],
        "improvements": ["group_task_macro_f1_improved"] if name == "promote_review_ready" else [],
    }


def _step9(
    ready: bool,
    *,
    blocker_codes: list[str] | None = None,
    warning_codes: list[str] | None = None,
) -> dict:
    blockers = list(blocker_codes or ([] if ready else ["full_qa_seed_shortfall"]))
    warnings = list(warning_codes or [])
    return {
        "snapshot": {
            "labeled_rows": 10000 if ready else 2596,
            "rows_to_target": 0 if ready else 7404,
        },
        "watch_items": {
            "execution_handoff": {
                "execution_handoff_ready": ready,
                "handoff_status": "READY" if ready else "NOT_READY",
                "blocker_codes": blockers,
                "warning_codes": warnings,
            }
        },
        "recheck_timing": {
            "status": "recheck_now" if ready else "watch_only",
        },
    }


def _canary(
    *,
    rows_observed: int = 60,
    utility_delta: float = 0.03,
    must_release_delta: int = 0,
    bad_exit_delta: int = 0,
    wait_drift_delta: float = 0.01,
    symbol_skew_delta: float = 0.02,
    watchlist_confusion_delta: int = 0,
) -> dict:
    return {
        "candidate_id": "candidate_1",
        "rows_observed": rows_observed,
        "utility_delta": utility_delta,
        "must_release_delta": must_release_delta,
        "bad_exit_delta": bad_exit_delta,
        "wait_drift_delta": wait_drift_delta,
        "symbol_skew_delta": symbol_skew_delta,
        "watchlist_confusion_delta": watchlist_confusion_delta,
    }


def test_promotion_gate_holds_offline_when_candidate_has_no_material_gain(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("hold_no_material_gain"),
        step9_watch_report=_step9(ready=True),
    )

    assert report["gate_stage"] == "hold_offline"
    assert report["recommended_action"] == "keep_current_baseline"


def test_promotion_gate_allows_log_only_when_step9_has_only_soft_blockers(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("promote_review_ready"),
        step9_watch_report=_step9(ready=False),
    )

    assert report["gate_stage"] == "log_only_ready"
    assert "step9_soft:full_qa_seed_shortfall" in report["warnings"]


def test_promotion_gate_waits_for_step9_when_critical_blocker_is_present(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("promote_review_ready"),
        step9_watch_report=_step9(
            ready=False,
            blocker_codes=["full_qa_seed_shortfall", "unresolved_high_confusions"],
        ),
    )

    assert report["gate_stage"] == "hold_step9"
    assert "step9:unresolved_high_confusions" in report["blockers"]


def test_promotion_gate_reports_log_only_ready_before_canary_evidence(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("promote_review_ready"),
        step9_watch_report=_step9(ready=True),
    )

    assert report["gate_stage"] == "log_only_ready"
    assert report["recommended_action"] == "run_log_only_then_collect_canary_evidence"
    assert report["offline_compare_summary"]["belief_compare_summary"]["belief_ready_delta"]["candidate_ready"] is True
    assert report["offline_compare_summary"]["barrier_compare_summary"]["barrier_ready_delta"]["candidate_ready"] is True
    assert report["offline_compare_summary"]["forecast_state25_compare_summary"]["transition_ready_delta"]["candidate_ready"] is True


def test_promotion_gate_keeps_log_only_when_offline_compare_has_soft_regression(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("log_only_review_ready"),
        step9_watch_report=_step9(ready=True),
    )

    assert report["gate_stage"] == "log_only_ready"
    assert report["recommended_action"] == "promote_log_only_after_offline_soft_regression_review"


def test_promotion_gate_promote_ready_when_canary_passes(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("promote_review_ready"),
        step9_watch_report=_step9(ready=True),
        canary_evidence=_canary(),
    )

    assert report["gate_stage"] == "promote_ready"
    assert report["rollback_reasons"] == []


def test_promotion_gate_recommends_rollback_when_canary_degrades(tmp_path: Path):
    report = build_teacher_pattern_promotion_gate_report(
        _manifest(tmp_path),
        compare_report=_compare(),
        promotion_decision=_decision("promote_review_ready"),
        step9_watch_report=_step9(ready=True),
        canary_evidence=_canary(utility_delta=-0.02, bad_exit_delta=1),
    )

    assert report["gate_stage"] == "rollback_recommended"
    assert "utility_delta_below_threshold" in report["rollback_reasons"]
    assert "bad_exit_delta_above_threshold" in report["rollback_reasons"]


def test_run_teacher_pattern_promotion_gate_writes_outputs(tmp_path: Path, monkeypatch):
    root = tmp_path.resolve()
    monkeypatch.chdir(root)
    manifest = _manifest(root)
    manifest_path = root / "latest_candidate_run.json"
    compare_path = Path(manifest["compare_report_path"])
    decision_path = Path(manifest["promotion_decision_path"])
    step9_path = root / "teacher_pattern_step9_watch_latest.json"
    canary_path = root / "latest_candidate_canary_evidence.json"

    compare_path.write_text(json.dumps(_compare(), ensure_ascii=False, indent=2), encoding="utf-8")
    decision_path.write_text(
        json.dumps(_decision("promote_review_ready"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    step9_path.write_text(json.dumps(_step9(True), ensure_ascii=False, indent=2), encoding="utf-8")
    canary_path.write_text(json.dumps(_canary(), ensure_ascii=False, indent=2), encoding="utf-8")

    result = run_teacher_pattern_promotion_gate(
        candidate_manifest_path=manifest_path,
        step9_watch_report_path=step9_path,
        canary_evidence_path=canary_path,
    )

    assert result["gate_stage"] == "promote_ready"
    assert Path(result["gate_report_path"]).exists()
    assert Path(result["gate_markdown_path"]).exists()
