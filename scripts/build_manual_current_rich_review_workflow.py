"""
Build the current-rich review workflow from the promotion gate output.

Usage:
  python scripts/build_manual_current_rich_review_workflow.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_review_workflow import (  # noqa: E402
    build_manual_current_rich_review_workflow,
    load_frame,
    render_manual_current_rich_review_workflow_markdown,
)


def _default_gate_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_promotion_gate_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_workflow_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_workflow_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_review_workflow_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-path", default=str(_default_gate_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    gate_path = Path(args.gate_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    gate = load_frame(gate_path)
    workflow, summary = build_manual_current_rich_review_workflow(gate)

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    workflow.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": workflow.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_current_rich_review_workflow_markdown(summary, workflow),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "gate_path": str(gate_path),
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
