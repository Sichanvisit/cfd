from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.path_checkpoint_pa8_canary_refresh import (  # noqa: E402
    build_checkpoint_pa8_canary_refresh_board,
    write_checkpoint_pa8_canary_refresh_outputs,
)
from backend.services.path_checkpoint_pa8_action_symbol_review import (  # noqa: E402
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
    parser.add_argument(
        "--resolved-dataset-path",
        default=str(default_checkpoint_dataset_resolved_path()),
    )
    args = parser.parse_args(argv)

    payload = build_checkpoint_pa8_canary_refresh_board(_load_csv(args.resolved_dataset_path))
    write_checkpoint_pa8_canary_refresh_outputs(payload)
    print(payload["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
