"""Build latest checkpoint scene candidate pipeline artifacts for SA4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_context import (  # noqa: E402
    default_checkpoint_rows_path,
)
from backend.services.path_checkpoint_dataset import (  # noqa: E402
    build_checkpoint_dataset_artifacts,
    build_checkpoint_scene_dataset_artifacts,
    build_checkpoint_scene_eval,
    default_checkpoint_dataset_resolved_path,
    default_checkpoint_scene_dataset_path,
    default_checkpoint_scene_eval_path,
)
from backend.services.path_checkpoint_scene_candidate_pipeline import (  # noqa: E402
    build_checkpoint_scene_candidate_pipeline,
    default_checkpoint_scene_candidate_root,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return dict(json.loads(file_path.read_text(encoding="utf-8")) or {})


def _needs_scene_dataset_rebuild(frame: pd.DataFrame) -> bool:
    required = {
        "runtime_scene_fine_label",
        "runtime_scene_gate_label",
        "hindsight_scene_fine_label",
        "hindsight_scene_quality_tier",
    }
    return frame.empty or not required.issubset(set(frame.columns))


def _needs_scene_eval_rebuild(payload: dict) -> bool:
    summary = dict(payload.get("summary", {}) or {})
    required = {
        "runtime_scene_filled_row_count",
        "hindsight_scene_resolved_row_count",
        "runtime_hindsight_scene_match_rate",
    }
    return not summary or not required.issubset(set(summary.keys()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dataset-path", default=str(default_checkpoint_scene_dataset_path()))
    parser.add_argument("--scene-eval-path", default=str(default_checkpoint_scene_eval_path()))
    parser.add_argument("--resolved-dataset-path", default=str(default_checkpoint_dataset_resolved_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--candidate-root", default=str(default_checkpoint_scene_candidate_root()))
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--reference-metrics-path", default="")
    parser.add_argument("--recent-limit", type=int, default=0)
    args = parser.parse_args(argv)

    recent_limit = None if int(args.recent_limit) <= 0 else int(args.recent_limit)

    scene_dataset = _load_csv(args.scene_dataset_path)
    if _needs_scene_dataset_rebuild(scene_dataset):
        resolved = _load_csv(args.resolved_dataset_path)
        if resolved.empty:
            _, resolved, _ = build_checkpoint_dataset_artifacts(
                _load_csv(args.checkpoint_rows_path),
                recent_limit=recent_limit,
            )
        scene_dataset, _ = build_checkpoint_scene_dataset_artifacts(
            resolved,
            recent_limit=recent_limit,
        )
        Path(args.scene_dataset_path).parent.mkdir(parents=True, exist_ok=True)
        scene_dataset.to_csv(args.scene_dataset_path, index=False, encoding="utf-8-sig")

    scene_eval_payload = _load_json(args.scene_eval_path)
    if _needs_scene_eval_rebuild(scene_eval_payload):
        eval_frame, eval_summary = build_checkpoint_scene_eval(scene_dataset)
        Path(args.scene_eval_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.scene_eval_path).write_text(
            json.dumps({"summary": eval_summary, "rows": eval_frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        scene_eval_payload = {"summary": eval_summary, "rows": eval_frame.to_dict(orient="records")}

    manifest = build_checkpoint_scene_candidate_pipeline(
        scene_dataset,
        scene_eval_summary=dict(scene_eval_payload.get("summary", {}) or {}),
        candidate_root=args.candidate_root,
        candidate_id=(args.candidate_id or None),
        reference_metrics_path=(args.reference_metrics_path or None),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
