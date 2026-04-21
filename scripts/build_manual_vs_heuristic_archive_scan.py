"""Build a historical semantic archive inventory for manual-vs-heuristic comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_archive_scan import (  # noqa: E402
    build_manual_vs_heuristic_archive_scan,
    render_manual_vs_heuristic_archive_scan_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades-dir", default=str(ROOT / "data" / "trades"))
    parser.add_argument("--csv-output-path", default=str(ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_archive_scan_latest.csv"))
    parser.add_argument("--json-output-path", default=str(ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_archive_scan_latest.json"))
    parser.add_argument("--md-output-path", default=str(ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_archive_scan_latest.md"))
    args = parser.parse_args()

    frame, summary = build_manual_vs_heuristic_archive_scan(args.trades_dir)
    csv_path = Path(args.csv_output_path)
    json_path = Path(args.json_output_path)
    md_path = Path(args.md_output_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_manual_vs_heuristic_archive_scan_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
