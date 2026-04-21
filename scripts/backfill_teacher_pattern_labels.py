"""
Bounded teacher-pattern backfill for trade_closed_history.csv.

Usage:
  python scripts/backfill_teacher_pattern_labels.py --dry-run --limit 1000
  python scripts/backfill_teacher_pattern_labels.py --apply --limit 1000
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
    apply_teacher_pattern_backfill,
    build_teacher_pattern_backfill_plan,
    read_closed_history_for_backfill,
    write_closed_history_backfill,
)


def _default_closed_history_path() -> Path:
    return ROOT / "data" / "trades" / "trade_closed_history.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write bounded backfill to CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Print bounded backfill plan only.")
    parser.add_argument("--limit", type=int, default=1000, help="Recent closed rows to inspect/apply.")
    parser.add_argument("--overwrite-existing", action="store_true", help="Allow relabeling rows that already have teacher fields.")
    parser.add_argument("--csv-path", default=str(_default_closed_history_path()), help="Target closed-history CSV path.")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        args.dry_run = True

    target_path = Path(args.csv_path)
    frame = read_closed_history_for_backfill(target_path)

    if args.dry_run and not args.apply:
        plan = build_teacher_pattern_backfill_plan(
            frame,
            recent_limit=args.limit,
            overwrite_existing=args.overwrite_existing,
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    updated, report = apply_teacher_pattern_backfill(
        frame,
        recent_limit=args.limit,
        overwrite_existing=args.overwrite_existing,
    )
    backup_path = write_closed_history_backfill(
        target_path,
        updated,
        backup=True,
        backup_suffix="teacher_pattern_backfill",
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
