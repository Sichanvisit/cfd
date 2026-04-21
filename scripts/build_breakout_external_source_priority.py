"""Build external source priority outputs for breakout backfill jobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_external_source_priority import (  # noqa: E402
    write_breakout_external_source_priority_report,
)


def _default_bundle_root() -> Path:
    return ROOT / "data" / "backfill" / "breakout_event"


def _default_scaffold_csv() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_backfill_runner_scaffold_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_external_source_priority_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_external_source_priority_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_external_source_priority_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", default=str(_default_bundle_root()))
    parser.add_argument("--scaffold-csv-path", default=str(_default_scaffold_csv()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    payload = write_breakout_external_source_priority_report(
        bundle_root=Path(args.bundle_root),
        scaffold_csv_path=Path(args.scaffold_csv_path),
        csv_output_path=Path(args.csv_output_path),
        json_output_path=Path(args.json_output_path),
        markdown_output_path=Path(args.markdown_output_path),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
