from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.trading.engine.offline.outcome_label_validation_report import (  # noqa: E402
    write_outcome_label_validation_report,
)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        payload = json.loads(text)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an outcome label validation report from replay dataset rows.")
    parser.add_argument("input", help="Path to a JSON array or JSONL file containing replay_dataset_row_v1 rows.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "analysis"),
        help="Directory where the validation report JSON will be written.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    if not input_path.exists():
        print(json.dumps({"error": "input_file_missing", "path": str(input_path)}, ensure_ascii=False))
        return 1

    rows = _load_rows(input_path)
    out_path = write_outcome_label_validation_report(rows, output_dir=args.output_dir)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
