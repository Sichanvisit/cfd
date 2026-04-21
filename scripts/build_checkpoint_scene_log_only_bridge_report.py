"""Build latest checkpoint scene log-only runtime bridge report for SA5."""

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
    default_checkpoint_dataset_resolved_path,
    default_checkpoint_scene_dataset_path,
)
from backend.services.path_checkpoint_scene_candidate_pipeline import (  # noqa: E402
    default_checkpoint_scene_candidate_root,
)
from backend.services.path_checkpoint_scene_runtime_bridge import (  # noqa: E402
    build_checkpoint_scene_log_only_bridge_report,
    default_checkpoint_scene_log_only_bridge_report_path,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def _needs_scene_dataset_rebuild(frame: pd.DataFrame) -> bool:
    required = {
        "runtime_scene_fine_label",
        "runtime_scene_gate_label",
        "hindsight_scene_fine_label",
        "hindsight_scene_quality_tier",
    }
    return frame.empty or not required.issubset(set(frame.columns))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dataset-path", default=str(default_checkpoint_scene_dataset_path()))
    parser.add_argument("--resolved-dataset-path", default=str(default_checkpoint_dataset_resolved_path()))
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--candidate-root", default=str(default_checkpoint_scene_candidate_root()))
    parser.add_argument("--recent-limit", type=int, default=0)
    parser.add_argument("--skip-ensure-active-state", action="store_true")
    parser.add_argument("--json-output-path", default=str(default_checkpoint_scene_log_only_bridge_report_path()))
    args = parser.parse_args(argv)

    scene_dataset = _load_csv(args.scene_dataset_path)
    if _needs_scene_dataset_rebuild(scene_dataset):
        resolved = _load_csv(args.resolved_dataset_path)
        if resolved.empty:
            _, resolved, _ = build_checkpoint_dataset_artifacts(
                _load_csv(args.checkpoint_rows_path),
                recent_limit=(None if int(args.recent_limit) <= 0 else int(args.recent_limit)),
            )
        scene_dataset, _ = build_checkpoint_scene_dataset_artifacts(
            resolved,
            recent_limit=(None if int(args.recent_limit) <= 0 else int(args.recent_limit)),
        )

    candidate_root = Path(args.candidate_root)
    report_frame, summary = build_checkpoint_scene_log_only_bridge_report(
        scene_dataset,
        active_state_path=candidate_root / "active_candidate_state.json",
        latest_run_path=candidate_root / "latest_candidate_run.json",
        ensure_active_state=not bool(args.skip_ensure_active_state),
    )

    output_path = Path(args.json_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"summary": summary, "rows": report_frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"json_output_path": str(output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
