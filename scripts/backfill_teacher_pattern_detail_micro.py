"""
Bounded richer backfill for teacher-pattern and micro payload fields using detail JSONL.

Usage:
  python scripts/backfill_teacher_pattern_detail_micro.py --dry-run --limit 2000
  python scripts/backfill_teacher_pattern_detail_micro.py --apply --limit 2000
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.teacher_pattern_backfill import (  # noqa: E402
    read_closed_history_for_backfill,
    write_closed_history_backfill,
)
from backend.services.teacher_pattern_detail_micro_backfill import (  # noqa: E402
    apply_teacher_pattern_detail_micro_backfill,
    build_teacher_pattern_detail_micro_backfill_plan,
    resolve_default_detail_paths,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def _default_detail_dir() -> Path:
    return ROOT / "data" / "trades"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write bounded richer backfill to CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Print richer backfill plan only.")
    parser.add_argument("--limit", type=int, default=2000, help="Recent closed rows to inspect/apply.")
    parser.add_argument("--csv-path", default=str(_default_closed_history_path()), help="Target closed-history CSV path.")
    parser.add_argument("--detail-dir", default=str(_default_detail_dir()), help="Directory containing entry decision detail JSONL files.")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        args.dry_run = True

    target_path = Path(args.csv_path)
    detail_paths = resolve_default_detail_paths(args.detail_dir)
    frame = read_closed_history_for_backfill(target_path)

    if args.dry_run and not args.apply:
        plan = build_teacher_pattern_detail_micro_backfill_plan(
            frame,
            detail_paths=detail_paths,
            recent_limit=args.limit,
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    updated, report = apply_teacher_pattern_detail_micro_backfill(
        frame,
        detail_paths=detail_paths,
        recent_limit=args.limit,
    )
    backup_path = write_closed_history_backfill(
        target_path,
        updated,
        backup=True,
        backup_suffix="teacher_pattern_detail_micro_backfill",
    )
    output = {
        "csv_path": str(target_path),
        "backup_path": str(backup_path) if backup_path else "",
        **report,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
