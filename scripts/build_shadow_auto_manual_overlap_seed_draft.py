"""Build review-needed manual seed draft from the shadow manual-overlap queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.shadow_auto_manual_overlap_seed_draft import (  # noqa: E402
    build_shadow_auto_manual_overlap_seed_draft,
    load_shadow_auto_manual_overlap_queue,
    load_shadow_auto_manual_overlap_review_entries,
)


def _default_queue_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "shadow_manual_overlap_queue_latest.csv"


def _default_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "shadow_manual_overlap_seed_draft_latest.csv"


def _default_review_entries_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "shadow_manual_overlap_seed_review_entries.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--review-entries-path", default=str(_default_review_entries_path()))
    parser.add_argument("--output-path", default=str(_default_output_path()))
    args = parser.parse_args()

    queue = load_shadow_auto_manual_overlap_queue(Path(args.queue_path))
    review_entries = load_shadow_auto_manual_overlap_review_entries(Path(args.review_entries_path))
    draft = build_shadow_auto_manual_overlap_seed_draft(queue, review_entries)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    draft.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary = {
        "queue_path": str(Path(args.queue_path)),
        "review_entries_path": str(Path(args.review_entries_path)),
        "output_path": str(output_path),
        "draft_row_count": int(len(draft)),
        "symbol_counts": draft["symbol"].value_counts(dropna=False).to_dict() if not draft.empty else {},
        "review_status_counts": draft["review_status"].value_counts(dropna=False).to_dict() if not draft.empty else {},
        "annotation_source_counts": draft["annotation_source"].value_counts(dropna=False).to_dict() if not draft.empty else {},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
