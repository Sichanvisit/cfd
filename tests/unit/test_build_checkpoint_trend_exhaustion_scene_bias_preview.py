import json
import io
from pathlib import Path
from contextlib import redirect_stdout

import joblib
import pandas as pd

from backend.services.path_checkpoint_scene_runtime_bridge import (
    ensure_checkpoint_scene_active_candidate_state,
)
from scripts.build_checkpoint_trend_exhaustion_scene_bias_preview import (
    main,
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


def test_build_checkpoint_trend_exhaustion_scene_bias_preview_script(tmp_path: Path) -> None:
    candidate_root = tmp_path / "scene_candidates"
    candidate_dir = candidate_root / "candidate_001"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "tasks": {
                "coarse_family_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("POSITION_MANAGEMENT", 0.84)},
                "gate_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("none", 0.91)},
                "resolved_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.62)},
                "late_scene_task": {"feature_columns": {"categorical": [], "numeric": []}, "model": FixedPredictor("trend_exhaustion", 0.93)},
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

    resolved = pd.DataFrame(
        [
            {
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
        ]
    )
    resolved_path = tmp_path / "resolved.csv"
    resolved.to_csv(resolved_path, index=False, encoding="utf-8-sig")
    output_path = tmp_path / "preview.json"

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(
            [
                "--resolved-dataset-path",
                str(resolved_path),
                "--candidate-root",
                str(candidate_root),
                "--json-output-path",
                str(output_path),
            ]
        )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert code == 0
    assert payload["summary"]["eligible_row_count"] == 1
    assert payload["summary"]["preview_changed_row_count"] == 1
    assert payload["rows"][0]["preview_action_label"] == "PARTIAL_THEN_HOLD"
    assert json.loads(stdout.getvalue())["preview_changed_row_count"] == 1
