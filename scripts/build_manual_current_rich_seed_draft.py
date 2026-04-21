"""
Build assistant seed drafts from the current-rich manual collection queue.

Usage:
  python scripts/build_manual_current_rich_seed_draft.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_current_rich_seed_draft import (  # noqa: E402
    build_manual_current_rich_seed_draft,
    load_queue_frame,
    load_review_override_frame,
)


def _default_queue_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.csv"


def _default_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_draft_latest.csv"


def _default_review_entry_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_review_entries.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--output-path", default=str(_default_output_path()))
    parser.add_argument("--review-entry-path", default=str(_default_review_entry_path()))
    args = parser.parse_args()

    queue_path = Path(args.queue_path)
    output_path = Path(args.output_path)
    review_entry_path = Path(args.review_entry_path)

    queue = load_queue_frame(queue_path)
    review_overrides = load_review_override_frame(review_entry_path)
    draft = build_manual_current_rich_seed_draft(queue, review_overrides=review_overrides)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draft.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary = {
        "queue_path": str(queue_path),
        "review_entry_path": str(review_entry_path),
        "output_path": str(output_path),
        "draft_row_count": int(len(draft)),
        "review_override_count": int(len(review_overrides)),
        "symbol_counts": draft["symbol"].value_counts(dropna=False).to_dict() if not draft.empty else {},
        "annotation_source_counts": draft["annotation_source"].value_counts(dropna=False).to_dict() if not draft.empty else {},
        "review_status_counts": draft["review_status"].value_counts(dropna=False).to_dict() if not draft.empty else {},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
