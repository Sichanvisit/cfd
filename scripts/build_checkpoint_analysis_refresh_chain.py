from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_analysis_refresh import (  # noqa: E402
    DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_RECENT_LIMIT,
    default_checkpoint_analysis_refresh_markdown_path,
    default_checkpoint_analysis_refresh_report_path,
    maybe_refresh_checkpoint_analysis_chain,
)
from backend.services.path_checkpoint_context import (  # noqa: E402
    default_checkpoint_rows_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-rows-path", default=str(default_checkpoint_rows_path()))
    parser.add_argument("--min-interval-seconds", type=int, default=300)
    parser.add_argument("--min-new-rows", type=int, default=25)
    parser.add_argument("--recent-limit", type=int, default=int(DEFAULT_CHECKPOINT_ANALYSIS_REFRESH_RECENT_LIMIT))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--deep-scene-review", action="store_true")
    parser.add_argument("--json-output-path", default=str(default_checkpoint_analysis_refresh_report_path()))
    parser.add_argument("--markdown-output-path", default=str(default_checkpoint_analysis_refresh_markdown_path()))
    args = parser.parse_args(argv)

    payload = maybe_refresh_checkpoint_analysis_chain(
        checkpoint_rows_path=args.checkpoint_rows_path,
        min_interval_seconds=int(args.min_interval_seconds),
        min_new_rows=int(args.min_new_rows),
        force=bool(args.force),
        recent_limit=(None if int(args.recent_limit) <= 0 else int(args.recent_limit)),
        report_path=args.json_output_path,
        markdown_path=args.markdown_output_path,
        include_deep_scene_review=bool(args.deep_scene_review),
    )
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
