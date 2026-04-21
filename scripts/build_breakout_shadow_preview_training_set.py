"""Build breakout-specific preview training corpus and dataset exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_shadow_preview_training_set import (  # noqa: E402
    write_breakout_shadow_preview_training_set,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-csv-path", default=None)
    parser.add_argument("--analysis-csv-path", default=None)
    parser.add_argument("--analysis-json-path", default=None)
    parser.add_argument("--analysis-md-path", default=None)
    parser.add_argument("--dataset-dir", default=None)
    args = parser.parse_args()

    payload = write_breakout_shadow_preview_training_set(
        seed_csv_path=args.seed_csv_path,
        analysis_csv_path=args.analysis_csv_path,
        analysis_json_path=args.analysis_json_path,
        analysis_md_path=args.analysis_md_path,
        dataset_dir=args.dataset_dir,
    )
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
