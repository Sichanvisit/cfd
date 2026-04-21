"""
Build a focused current-rich review queue for remaining wrong_failed_wait cases.

Usage:
  python scripts/build_manual_current_rich_wrong_failed_wait_review_queue.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_wrong_failed_wait_review_queue import (  # noqa: E402
    build_current_rich_wrong_failed_wait_review_queue,
    load_frame,
    render_current_rich_wrong_failed_wait_review_queue_markdown,
)


def _default_seed_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_draft_latest.csv"


def _default_audit_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_wrong_failed_wait_audit_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_queue_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_queue_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_wrong_failed_wait_review_queue_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-path", default=str(_default_seed_path()))
    parser.add_argument("--audit-path", default=str(_default_audit_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    seeds = load_frame(Path(args.seed_path))
    audit = load_frame(Path(args.audit_path))
    queue, summary = build_current_rich_wrong_failed_wait_review_queue(seeds, audit)

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    queue.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": queue.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_current_rich_wrong_failed_wait_review_queue_markdown(summary, queue),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "seed_path": str(Path(args.seed_path)),
                "audit_path": str(Path(args.audit_path)),
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
