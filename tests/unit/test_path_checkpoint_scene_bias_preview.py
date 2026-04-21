import json
from pathlib import Path

import joblib
import pandas as pd

from backend.services.path_checkpoint_scene_bias_preview import (
    build_trend_exhaustion_scene_bias_preview,
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


def _write_candidate_root(tmp_path: Path, *, late_label: str = "trend_exhaustion", confidence: float = 0.93) -> Path:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "tasks": {
                "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.84)},
                "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
                "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.62)},
                "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor(late_label, confidence)},
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


def _row(**overrides) -> dict:
    row = {
        "generated_at": "2026-04-10T22:00:00+09:00",
        "symbol": "NAS100",
        "checkpoint_id": "NAS_CP_001",
        "surface_name": "continuation_hold_surface",
        "checkpoint_type": "RUNNER_CHECK",
        "position_side": "BUY",
        "management_action_label": "HOLD",
        "runtime_proxy_management_action_label": "HOLD",
        "hindsight_best_management_action_label": "PARTIAL_THEN_HOLD",
        "runtime_partial_exit_ev": 0.58,
        "runtime_hold_quality_score": 0.46,
        "current_profit": 0.08,
        "giveback_ratio": 0.22,
        "unrealized_pnl_state": "OPEN_PROFIT",
        "runner_secured": False,
        "checkpoint_rule_family_hint": "profit_hold_bias",
        "exit_stage_family": "hold",
    }
    row.update(overrides)
    return row


def test_trend_exhaustion_preview_moves_hold_to_partial_then_hold(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    frame = pd.DataFrame([_row()])

    preview_frame, summary = build_trend_exhaustion_scene_bias_preview(
        frame,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    assert len(preview_frame) == 1
    row = preview_frame.iloc[0]
    assert row["baseline_action_label"] == "HOLD"
    assert row["preview_action_label"] == "PARTIAL_THEN_HOLD"
    assert bool(row["preview_changed"]) is True
    assert summary["preview_changed_row_count"] == 1


def test_trend_exhaustion_preview_ignores_non_trend_exhaustion_candidates(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path, late_label="time_decay_risk")
    frame = pd.DataFrame([_row()])

    preview_frame, summary = build_trend_exhaustion_scene_bias_preview(
        frame,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    assert preview_frame.empty
    assert summary["eligible_row_count"] == 0
    assert summary["preview_changed_row_count"] == 0


def test_trend_exhaustion_preview_keeps_hold_when_partial_edge_is_too_small(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    frame = pd.DataFrame(
        [
            _row(
                runtime_partial_exit_ev=0.57,
                runtime_hold_quality_score=0.55,
                giveback_ratio=0.0,
                hindsight_best_management_action_label="HOLD",
            )
        ]
    )

    preview_frame, summary = build_trend_exhaustion_scene_bias_preview(
        frame,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
    )

    assert len(preview_frame) == 1
    row = preview_frame.iloc[0]
    assert row["preview_action_label"] == "HOLD"
    assert bool(row["preview_changed"]) is False
    assert summary["preview_changed_row_count"] == 0
