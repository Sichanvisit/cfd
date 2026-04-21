"""Build latest checkpoint dataset exports for PA5 instrumentation."""

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
    default_checkpoint_dataset_path,
    default_checkpoint_dataset_resolved_path,
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
    parser.add_argument("--recent-limit", type=int, default=0)
    parser.add_argument("--dataset-output-path", default=str(default_checkpoint_dataset_path()))
    parser.add_argument("--resolved-output-path", default=str(default_checkpoint_dataset_resolved_path()))
    args = parser.parse_args(argv)

    base, resolved, summary = build_checkpoint_dataset_artifacts(
        _load_csv(args.checkpoint_rows_path),
        recent_limit=(None if int(args.recent_limit) <= 0 else int(args.recent_limit)),
    )

    dataset_output_path = Path(args.dataset_output_path)
    resolved_output_path = Path(args.resolved_output_path)
    dataset_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(dataset_output_path, index=False, encoding="utf-8-sig")
    resolved.to_csv(resolved_output_path, index=False, encoding="utf-8-sig")
    print(
        json.dumps(
            {
                "dataset_output_path": str(dataset_output_path),
                "resolved_output_path": str(resolved_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
