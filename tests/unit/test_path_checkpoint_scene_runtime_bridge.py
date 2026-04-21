import json
from pathlib import Path

import joblib
import pandas as pd

from backend.services.path_checkpoint_scene_runtime_bridge import (
    build_checkpoint_scene_log_only_bridge_report,
    build_checkpoint_scene_log_only_bridge_v1,
    ensure_checkpoint_scene_active_candidate_state,
)


class FixedPredictor:
    def __init__(self, label: str, confidence: float) -> None:
        self.label = str(label)
        self.confidence = float(confidence)

    def predict(self, frame: pd.DataFrame) -> list[str]:
        return [self.label for _ in range(len(frame))]

    def predict_proba(self, frame: pd.DataFrame) -> list[list[float]]:
        confidence = max(0.0, min(1.0, self.confidence))
        other = max(0.0, 1.0 - confidence)
        if other <= 0.0:
            return [[confidence] for _ in range(len(frame))]
        return [[confidence, other] for _ in range(len(frame))]


def _write_candidate_root(tmp_path: Path) -> Path:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {
                "feature_columns": {"categorical": [], "numeric": []},
                "model": FixedPredictor("POSITION_MANAGEMENT", 0.81),
            },
            "gate_task": {
                "feature_columns": {"categorical": [], "numeric": []},
                "model": FixedPredictor("none", 0.92),
            },
            "resolved_scene_task": {
                "feature_columns": {"categorical": [], "numeric": []},
                "model": FixedPredictor("breakout_retest_hold", 0.62),
            },
            "late_scene_task": {
                "feature_columns": {"categorical": [], "numeric": []},
                "model": FixedPredictor("trend_exhaustion", 0.82),
            },
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    latest_manifest = {
        "candidate_id": "candidate_001",
        "candidate_bundle_path": str(bundle_path),
    }
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps(latest_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return candidate_root


def _build_scene_row(*, symbol: str, checkpoint_id: str, checkpoint_type: str, runtime_scene_fine_label: str) -> dict:
    return {
        "generated_at": "2026-04-10T21:00:00+09:00",
        "symbol": symbol,
        "checkpoint_id": checkpoint_id,
        "checkpoint_type": checkpoint_type,
        "runtime_scene_fine_label": runtime_scene_fine_label,
        "runtime_scene_gate_label": "none",
    }


def test_log_only_bridge_requires_explicit_active_state_even_when_latest_candidate_exists(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)

    payload = build_checkpoint_scene_log_only_bridge_v1(
        _build_scene_row(
            symbol="BTCUSD",
            checkpoint_id="BTC_CP_001",
            checkpoint_type="RUNNER_CHECK",
            runtime_scene_fine_label="breakout_retest_hold",
        ),
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_available"] is False
    assert row["scene_candidate_binding_mode"] == "disabled"
    assert row["scene_candidate_reason"] == "scene_candidate_bridge_active_state_missing"


def test_log_only_bridge_selects_late_scene_when_active_state_is_ready(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    active_state = ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        _build_scene_row(
            symbol="NAS100",
            checkpoint_id="NAS_CP_001",
            checkpoint_type="RUNNER_CHECK",
            runtime_scene_fine_label="breakout_retest_hold",
        ),
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert active_state["active_candidate_id"] == "candidate_001"
    assert row["scene_candidate_available"] is True
    assert row["scene_candidate_candidate_id"] == "candidate_001"
    assert row["scene_candidate_selected_label"] == "trend_exhaustion"
    assert row["scene_candidate_selected_source"] == "late_scene_task"
    assert row["scene_candidate_runtime_scene_match"] is False


def test_build_log_only_bridge_report_summarizes_scene_disagreements(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )
    scene_dataset = pd.DataFrame(
        [
            _build_scene_row(
                symbol="NAS100",
                checkpoint_id="NAS_CP_001",
                checkpoint_type="RUNNER_CHECK",
                runtime_scene_fine_label="breakout_retest_hold",
            ),
            _build_scene_row(
                symbol="XAUUSD",
                checkpoint_id="XAU_CP_001",
                checkpoint_type="RECLAIM_CHECK",
                runtime_scene_fine_label="breakout_retest_hold",
            ),
        ]
    )

    report_frame, summary = build_checkpoint_scene_log_only_bridge_report(
        scene_dataset,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
        ensure_active_state=False,
    )

    assert len(report_frame) == 3
    assert summary["bridge_available_row_count"] == 2
    assert summary["candidate_selected_label_counts"]["trend_exhaustion"] == 1
    assert summary["candidate_selected_label_counts"]["breakout_retest_hold"] == 1
    assert summary["runtime_candidate_scene_match_rate"] == 0.5
    assert summary["runtime_candidate_gate_match_rate"] == 1.0
    assert summary["high_confidence_scene_disagreement_count"] == 1
    assert summary["recommended_next_action"] == "review_high_confidence_scene_candidate_disagreements_before_sa6"


def test_log_only_bridge_suppresses_time_decay_overpull_on_protective_runner_open_loss(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("DEFENSIVE_EXIT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.92)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.84)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps(
            {
                "candidate_id": "candidate_001",
                "candidate_bundle_path": str(bundle_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_900",
            "surface_name": "protective_exit_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "OPEN_LOSS",
            "current_profit": -0.29,
            "giveback_ratio": 0.99,
            "runtime_full_exit_risk": 0.78,
            "runtime_reversal_odds": 0.88,
            "runtime_continuation_odds": 0.56,
            "checkpoint_rule_family_hint": "active_open_loss",
            "management_action_label": "FULL_EXIT",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_fine_label"] == "time_decay_risk"
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert row["scene_candidate_selected_confidence"] == 0.0
    assert "suppressed::time_decay_protective_overpull_guard" in row["scene_candidate_reason"]


def test_log_only_bridge_suppresses_time_decay_on_runner_secured_continuation(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.90)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.94)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "BTCUSD",
            "checkpoint_id": "BTC_CP_950",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "FLAT",
            "current_profit": 0.0,
            "giveback_ratio": 0.99,
            "runtime_full_exit_risk": 0.24,
            "runtime_reversal_odds": 0.42,
            "runtime_continuation_odds": 0.50,
            "runtime_hold_quality_score": 0.48,
            "bars_since_last_push": 6,
            "bars_since_last_checkpoint": 3,
            "checkpoint_rule_family_hint": "runner_secured_continuation",
            "exit_stage_family": "runner",
            "runner_secured": True,
            "management_action_label": "HOLD",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_fine_label"] == "time_decay_risk"
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert "suppressed::time_decay_runner_secured_guard" in row["scene_candidate_reason"]


def test_log_only_bridge_keeps_time_decay_for_true_late_stall_active_flat_profit(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.82)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.93)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_951",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "FLAT",
            "current_profit": 0.03,
            "giveback_ratio": 0.96,
            "runtime_full_exit_risk": 0.22,
            "runtime_reversal_odds": 0.49,
            "runtime_continuation_odds": 0.47,
            "runtime_hold_quality_score": 0.37,
            "bars_since_last_push": 7,
            "bars_since_last_checkpoint": 3,
            "checkpoint_rule_family_hint": "active_flat_profit",
            "exit_stage_family": "hold",
            "runner_secured": False,
            "management_action_label": "WAIT",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_selected_label"] == "time_decay_risk"
    assert row["scene_candidate_selected_source"] == "late_scene_task"
    assert "time_decay_active_flat_profit_guard" not in row["scene_candidate_reason"]


def test_log_only_bridge_suppresses_time_decay_on_nonstall_active_flat_profit(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.84)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.92)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_952",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "FLAT",
            "current_profit": 0.0,
            "giveback_ratio": 0.42,
            "runtime_full_exit_risk": 0.18,
            "runtime_reversal_odds": 0.39,
            "runtime_continuation_odds": 0.64,
            "runtime_hold_quality_score": 0.57,
            "bars_since_last_push": 2,
            "bars_since_last_checkpoint": 1,
            "checkpoint_rule_family_hint": "active_flat_profit",
            "exit_stage_family": "hold",
            "runner_secured": False,
            "management_action_label": "HOLD",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert "suppressed::time_decay_active_flat_profit_guard" in row["scene_candidate_reason"]


def test_log_only_bridge_suppresses_time_decay_on_profit_trim_bias_open_profit(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.84)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.92)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_953",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "current_profit": 0.09,
            "giveback_ratio": 0.22,
            "runtime_reversal_odds": 0.41,
            "runtime_continuation_odds": 0.84,
            "runtime_hold_quality_score": 0.56,
            "checkpoint_rule_family_hint": "profit_trim_bias",
            "exit_stage_family": "hold",
            "management_action_label": "PARTIAL_THEN_HOLD",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert "suppressed::time_decay_profit_bias_guard" in row["scene_candidate_reason"]


def test_log_only_bridge_suppresses_time_decay_on_profit_hold_bias_open_profit(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.83)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.93)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_954",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "current_profit": 0.06,
            "giveback_ratio": 0.10,
            "runtime_reversal_odds": 0.46,
            "runtime_continuation_odds": 0.81,
            "runtime_hold_quality_score": 0.53,
            "checkpoint_rule_family_hint": "profit_hold_bias",
            "exit_stage_family": "hold",
            "management_action_label": "HOLD",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_selected_label"] == "unresolved"
    assert "suppressed::time_decay_profit_bias_guard" in row["scene_candidate_reason"]


def test_log_only_bridge_keeps_time_decay_on_wait_bias_tiny_profit(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    bundle_payload = {
        "tasks": {
            "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.88)},
            "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
            "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.85)},
            "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.94)},
        }
    }
    bundle_path = candidate_dir / "checkpoint_scene_candidate_bundle.joblib"
    joblib.dump(bundle_payload, bundle_path)
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps({"candidate_id": "candidate_001", "candidate_bundle_path": str(bundle_path)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ensure_checkpoint_scene_active_candidate_state(
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    payload = build_checkpoint_scene_log_only_bridge_v1(
        {
            "symbol": "NAS100",
            "checkpoint_id": "NAS_CP_955",
            "surface_name": "continuation_hold_surface",
            "checkpoint_type": "RUNNER_CHECK",
            "runtime_scene_fine_label": "unresolved",
            "runtime_scene_gate_label": "none",
            "unrealized_pnl_state": "OPEN_PROFIT",
            "current_profit": 0.01,
            "giveback_ratio": 0.0,
            "runtime_reversal_odds": 0.50,
            "runtime_continuation_odds": 0.60,
            "runtime_hold_quality_score": 0.40,
            "checkpoint_rule_family_hint": "wait_bias",
            "exit_stage_family": "hold",
            "management_action_label": "WAIT",
        },
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    row = payload["row"]
    assert row["scene_candidate_selected_label"] == "time_decay_risk"
    assert row["scene_candidate_selected_source"] == "late_scene_task"
