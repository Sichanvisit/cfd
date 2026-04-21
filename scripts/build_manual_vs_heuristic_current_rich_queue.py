"""
Build a current-rich window collection queue for new manual truth episodes.

Usage:
  python scripts/build_manual_vs_heuristic_current_rich_queue.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_current_rich_queue import (  # noqa: E402
    build_manual_vs_heuristic_current_rich_queue,
    load_default_manual_and_current_heuristics,
    render_manual_vs_heuristic_current_rich_queue_markdown,
)


def _default_annotations_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_heuristic_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations-path", default=str(_default_annotations_path()))
    parser.add_argument("--heuristic-path", default=str(_default_heuristic_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--window-minutes", type=int, default=30)
    parser.add_argument("--limit-per-symbol", type=int, default=4)
    args = parser.parse_args()

    annotations_path = Path(args.annotations_path)
    heuristic_path = Path(args.heuristic_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    manual, heuristics = load_default_manual_and_current_heuristics(annotations_path, heuristic_path)
    queue, summary = build_manual_vs_heuristic_current_rich_queue(
        manual,
        heuristics,
        window_minutes=int(args.window_minutes),
        limit_per_symbol=int(args.limit_per_symbol),
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    queue.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": queue.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_output_path.write_text(render_manual_vs_heuristic_current_rich_queue_markdown(summary, queue), encoding="utf-8")

    print(
        json.dumps(
            {
                "annotations_path": str(annotations_path),
                "heuristic_path": str(heuristic_path),
                "csv_output_path": str(csv_output_path),
                "json_output_path": str(json_output_path),
                "md_output_path": str(md_output_path),
                **summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
