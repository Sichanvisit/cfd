"""Build latest checkpoint scene sanity artifact by replaying SA2 heuristics."""

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
from backend.services.path_checkpoint_scene_sanity import (  # noqa: E402
    build_checkpoint_scene_sanity,
    default_checkpoint_scene_sanity_path,
)


def _load_csv(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(file_path, low_memory=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--json-output-path", default=str(default_checkpoint_scene_sanity_path()))
    parser.add_argument("--recent-limit", type=int, default=1200)
    args = parser.parse_args(argv)

    rows = _load_csv(args.checkpoint_rows_path)
    observation, summary, replay = build_checkpoint_scene_sanity(rows, recent_limit=args.recent_limit)
    json_output_path = Path(args.json_output_path)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": observation.to_dict(orient="records"),
                "replay_preview": replay.tail(50).to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"json_output_path": str(json_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
