"""
Apply episode-centric manual wait-teacher truth to trade_closed_history.csv.

Usage:
  python scripts/backfill_manual_wait_teacher_truth.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_wait_teacher_seed_enrichment import (  # noqa: E402
    DEFAULT_AMBIGUITY_GAP_SECONDS,
    DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES,
    apply_manual_wait_teacher_seed_enrichment,
    build_manual_wait_teacher_seed_enrichment_plan,
    load_manual_wait_teacher_annotations,
)
from backend.services.teacher_pattern_backfill import (  # noqa: E402
    read_closed_history_for_backfill,
    write_closed_history_backfill,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_annotation_path() -> Path:
    return ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closed-history-path", default=str(_default_closed_history_path()))
    parser.add_argument("--annotation-path", default=str(_default_annotation_path()))
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-gap-minutes", type=int, default=DEFAULT_MAX_ENTRY_TIME_GAP_MINUTES)
    parser.add_argument("--ambiguity-gap-seconds", type=int, default=DEFAULT_AMBIGUITY_GAP_SECONDS)
    args = parser.parse_args()

    closed_history_path = Path(args.closed_history_path)
    annotation_path = Path(args.annotation_path)

    frame = read_closed_history_for_backfill(closed_history_path)
    annotations = load_manual_wait_teacher_annotations(annotation_path)

    if args.dry_run:
        report = build_manual_wait_teacher_seed_enrichment_plan(
            frame,
            annotations=annotations,
            overwrite_existing=bool(args.overwrite_existing),
            max_entry_time_gap_minutes=int(args.max_gap_minutes),
            ambiguity_gap_seconds=int(args.ambiguity_gap_seconds),
        )
        report["closed_history_path"] = str(closed_history_path)
        report["annotation_path"] = str(annotation_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    updated_frame, report = apply_manual_wait_teacher_seed_enrichment(
        frame,
        annotations=annotations,
        overwrite_existing=bool(args.overwrite_existing),
        max_entry_time_gap_minutes=int(args.max_gap_minutes),
        ambiguity_gap_seconds=int(args.ambiguity_gap_seconds),
    )
    backup_path = write_closed_history_backfill(
        closed_history_path,
        updated_frame,
        backup=True,
        backup_suffix="manual_wait_teacher_enrichment",
    )
    report["closed_history_path"] = str(closed_history_path)
    report["annotation_path"] = str(annotation_path)
    report["backup_path"] = str(backup_path) if backup_path is not None else ""
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
