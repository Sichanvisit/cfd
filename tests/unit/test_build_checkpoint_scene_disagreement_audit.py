import json
from pathlib import Path

import joblib
import pandas as pd

from scripts.build_checkpoint_scene_disagreement_audit import main
from backend.services.path_checkpoint_scene_runtime_bridge import ensure_checkpoint_scene_active_candidate_state


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
                "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("time_decay_risk", 0.86)},
                "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.59)},
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


def test_build_checkpoint_scene_disagreement_audit_script_writes_json(tmp_path: Path) -> None:
    candidate_root = _write_candidate_root(tmp_path)
    resolved_path = tmp_path / "checkpoint_dataset_resolved.csv"
    output_path = tmp_path / "checkpoint_scene_disagreement_audit_latest.json"
    pd.DataFrame(
        [
            {
                "generated_at": "2026-04-10T21:11:00+09:00",
                "symbol": "NAS100",
                "checkpoint_id": "NAS_CP_100",
                "surface_name": "protective_exit_surface",
                "checkpoint_type": "RUNNER_CHECK",
                "source": "audit_test",
                "runtime_scene_fine_label": "unresolved",
                "hindsight_scene_fine_label": "unresolved",
                "runtime_proxy_management_action_label": "FULL_EXIT",
                "hindsight_best_management_action_label": "FULL_EXIT",
                "checkpoint_rule_family_hint": "active_open_loss",
                "exit_stage_family": "protective",
                "current_profit": -0.21,
                "giveback_ratio": 0.31,
            }
        ]
    ).to_csv(resolved_path, index=False, encoding="utf-8-sig")

    exit_code = main(
        [
            "--resolved-dataset-path",
            str(resolved_path),
            "--candidate-root",
            str(candidate_root),
            "--json-output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["high_conf_scene_disagreement_count"] == 0
    assert payload["summary"]["candidate_selected_label_counts"] == {}
    assert payload["summary"]["recommended_next_action"] == "scene_candidate_disagreement_clean_enough_for_sa6_review"
