"""
Build the trace sheet for the current highest-priority current-rich review batch.

Usage:
  python scripts/build_manual_current_rich_review_trace.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_review_trace import (  # noqa: E402
    build_manual_current_rich_review_trace,
    load_frame,
    render_manual_current_rich_review_trace_markdown,
)


def _default_workflow_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_workflow_latest.csv"


def _default_trace_input_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_entries.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_trace_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-path", default=str(_default_workflow_path()))
    parser.add_argument("--trace-input-path", default=str(_default_trace_input_path()))
    parser.add_argument("--target-batch-id", default="")
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    workflow_path = Path(args.workflow_path)
    trace_input_path = Path(args.trace_input_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    workflow = load_frame(workflow_path)
    trace_entries = load_frame(trace_input_path)
    trace, summary = build_manual_current_rich_review_trace(
        workflow,
        trace_entries=trace_entries,
        target_batch_id=args.target_batch_id or None,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    trace.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": trace.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_current_rich_review_trace_markdown(summary, trace),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "workflow_path": str(workflow_path),
                "trace_input_path": str(trace_input_path),
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
