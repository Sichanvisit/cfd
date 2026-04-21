import json
from pathlib import Path

import joblib
import pandas as pd

from scripts.build_checkpoint_scene_log_only_bridge_report import main


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
                "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("breakout_retest_hold", 0.66)},
                "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.79)},
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
    return candidate_root


def test_build_checkpoint_scene_log_only_bridge_report_script_writes_json_and_active_state(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    scene_dataset_path = tmp_path / "checkpoint_scene_dataset.csv"
    output_path = tmp_path / "checkpoint_scene_log_only_bridge_latest.json"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T21:05:00+09:00",
                "symbol": "NAS100",
                "checkpoint_id": "NAS_CP_010",
                "checkpoint_type": "RUNNER_CHECK",
                "runtime_scene_fine_label": "breakout_retest_hold",
                "runtime_scene_gate_label": "none",
                "hindsight_scene_fine_label": "trend_exhaustion",
                "hindsight_scene_quality_tier": "auto_medium",
            }
        ]
    ).to_csv(scene_dataset_path, index=False, encoding="utf-8-sig")

    exit_code = main(
        [
            "--scene-dataset-path",
            str(scene_dataset_path),
            "--candidate-root",
            str(candidate_root),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert (candidate_root / "active_candidate_state.json").exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["bridge_available_row_count"] == 1
    assert payload["summary"]["active_candidate_id"] == "candidate_001"
    assert payload["summary"]["recommended_next_action"] == "review_high_confidence_scene_candidate_disagreements_before_sa6"
