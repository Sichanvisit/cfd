"""
Build review results for current-rich wrong-failed-wait follow-up candidates.

Usage:
  python scripts/build_manual_current_rich_wrong_failed_wait_review_results.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_wrong_failed_wait_review_results import (  # noqa: E402
    build_current_rich_wrong_failed_wait_review_results,
    load_frame,
    render_current_rich_wrong_failed_wait_review_results_markdown,
)


def _default_queue_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_queue_latest.csv"


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_results_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_results_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_results_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    parser.add_argument("--window-minutes", type=int, default=30)
    args = parser.parse_args()

    queue = load_frame(Path(args.queue_path))
    entry_decisions = load_frame(Path(args.entry_decisions_path))
    review, summary = build_current_rich_wrong_failed_wait_review_results(
        queue,
        entry_decisions,
        window_minutes=int(args.window_minutes),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    review.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": review.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_current_rich_wrong_failed_wait_review_results_markdown(summary, review),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "queue_path": str(Path(args.queue_path)),
                "entry_decisions_path": str(Path(args.entry_decisions_path)),
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
