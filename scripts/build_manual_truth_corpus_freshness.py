"""
Build a freshness audit for canonical manual truth and current-rich draft coverage.

Usage:
  python scripts/build_manual_truth_corpus_freshness.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_truth_corpus_freshness import (  # noqa: E402
    build_manual_truth_corpus_freshness,
    load_current_entry_decisions_frame,
    load_current_rich_frame,
    render_manual_truth_corpus_freshness_markdown,
)


def _default_canonical_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def _default_draft_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_current_rich_seed_draft_latest.csv"


def _default_queue_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_current_rich_queue_latest.csv"


def _default_current_entry_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_truth_corpus_freshness_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_truth_corpus_freshness_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_truth_corpus_freshness_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-path", default=str(_default_canonical_path()))
    parser.add_argument("--draft-path", default=str(_default_draft_path()))
    parser.add_argument("--queue-path", default=str(_default_queue_path()))
    parser.add_argument("--current-entry-path", default=str(_default_current_entry_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    canonical_path = Path(args.canonical_path)
    draft_path = Path(args.draft_path)
    queue_path = Path(args.queue_path)
    current_entry_path = Path(args.current_entry_path)
    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)

    canonical = load_current_rich_frame(canonical_path)
    draft = load_current_rich_frame(draft_path)
    queue = load_current_rich_frame(queue_path)
    current_entry = load_current_entry_decisions_frame(current_entry_path)
    freshness, summary = build_manual_truth_corpus_freshness(
        canonical,
        draft,
        queue,
        current_entry,
    )

    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output_path.parent.mkdir(parents=True, exist_ok=True)

    freshness.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": freshness.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(
        render_manual_truth_corpus_freshness_markdown(summary, freshness),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "canonical_path": str(canonical_path),
                "draft_path": str(draft_path),
                "queue_path": str(queue_path),
                "current_entry_path": str(current_entry_path),
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
