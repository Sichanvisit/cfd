import json
from pathlib import Path

import joblib
import pandas as pd

from backend.services.path_checkpoint_scene_disagreement_audit import (
    build_checkpoint_scene_disagreement_audit,
)
from backend.services.path_checkpoint_scene_runtime_bridge import (
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
    joblib.dump(
        {
            "tasks": {
                "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.84)},
                "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
                "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.62)},
                "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.83)},
            }
        },
        candidate_dir / "checkpoint_scene_candidate_bundle.joblib",
    )
    (candidate_root / "latest_candidate_run.json").write_text(
        json.dumps(
            {
                "candidate_id": "candidate_001",
                "candidate_bundle_path": str(candidate_dir / "checkpoint_scene_candidate_bundle.joblib"),
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
    return candidate_root


def _row(
    *,
    idx: int,
    symbol: str,
    checkpoint_type: str,
    surface_name: str,
    runtime_scene_fine_label: str = "unresolved",
    hindsight_scene_fine_label: str = "unresolved",
    runtime_proxy_management_action_label: str = "FULL_EXIT",
    hindsight_best_management_action_label: str = "FULL_EXIT",
) -> dict:
    return {
        "generated_at": f"2026-04-10T21:{idx:02d}:00+09:00",
        "symbol": symbol,
        "checkpoint_id": f"{symbol}_CP_{idx}",
        "surface_name": surface_name,
        "checkpoint_type": checkpoint_type,
        "source": "audit_test",
        "runtime_scene_fine_label": runtime_scene_fine_label,
        "hindsight_scene_fine_label": hindsight_scene_fine_label,
        "runtime_proxy_management_action_label": runtime_proxy_management_action_label,
        "hindsight_best_management_action_label": hindsight_best_management_action_label,
        "checkpoint_rule_family_hint": "active_open_loss",
        "exit_stage_family": "protective",
        "current_profit": -0.2,
        "giveback_ratio": 0.33,
    }


def test_build_checkpoint_scene_disagreement_audit_flags_overpull_watch_and_casebook(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    rows = [
        _row(idx=idx, symbol="NAS100", checkpoint_type="RUNNER_CHECK", surface_name="protective_exit_surface")
        for idx in range(1, 21)
    ]
    rows.extend(
        [
            _row(idx=21, symbol="BTCUSD", checkpoint_type="RUNNER_CHECK", surface_name="protective_exit_surface"),
            _row(idx=22, symbol="BTCUSD", checkpoint_type="RUNNER_CHECK", surface_name="protective_exit_surface"),
            _row(idx=23, symbol="XAUUSD", checkpoint_type="RUNNER_CHECK", surface_name="protective_exit_surface"),
            _row(idx=24, symbol="XAUUSD", checkpoint_type="RUNNER_CHECK", surface_name="protective_exit_surface"),
            _row(
                idx=25,
                symbol="BTCUSD",
                checkpoint_type="RUNNER_CHECK",
                surface_name="continuation_hold_surface",
                runtime_proxy_management_action_label="HOLD",
                hindsight_best_management_action_label="PARTIAL_THEN_HOLD",
            ),
        ]
    )
    frame = pd.DataFrame(rows)

    audit_frame, summary = build_checkpoint_scene_disagreement_audit(
        frame,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    assert len(audit_frame) == 3
    assert summary["high_conf_scene_disagreement_count"] == 25
    assert summary["candidate_selected_label_counts"]["trend_exhaustion"] == 25
    assert summary["runtime_unresolved_disagreement_share"] == 1.0
    assert len(summary["casebook_examples"]) == 10
    assert summary["label_pull_profiles"][0]["watch_state"] == "overpull_watch"
    assert summary["recommended_next_action"] == "keep_scene_candidate_log_only_and_patch_overpull_labels_before_sa6"
