"""
Build the current-rich draft canonical promotion gate report.

Usage:
  python scripts/build_manual_current_rich_promotion_gate.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_promotion_gate import (  # noqa: E402
    build_manual_current_rich_promotion_gate,
    load_current_rich_frame,
    render_manual_current_rich_promotion_gate_markdown,
)


def _default_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_draft_latest.csv"


def _default_queue_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.csv"


def _default_review_results_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_results_latest.csv"


def _default_review_trace_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_entries.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_promotion_gate_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_promotion_gate_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_promotion_gate_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft-path", default=str(_default_draft_path()))
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--review-results-path", default=str(_default_review_results_path()))
    parser.add_argument("--review-trace-path", default=str(_default_review_trace_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    draft_path = Path(args.draft_path)
    queue_path = Path(args.queue_path)
    review_results_path = Path(args.review_results_path)
    review_trace_path = Path(args.review_trace_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    draft = load_current_rich_frame(draft_path)
    queue = load_current_rich_frame(queue_path)
    review_results = load_current_rich_frame(review_results_path)
    review_trace = load_current_rich_frame(review_trace_path)
    gate, summary = build_manual_current_rich_promotion_gate(
        draft,
        queue=queue,
        review_results=review_results,
        review_trace_entries=review_trace,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    gate.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": gate.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_current_rich_promotion_gate_markdown(summary, gate),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "draft_path": str(draft_path),
                "queue_path": str(queue_path),
                "review_results_path": str(review_results_path),
                "review_trace_path": str(review_trace_path),
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
