"""
Roll over the entry decision log, archive the previous active file as parquet,
and clean up old tail/legacy artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import Config
from backend.services.entry_decision_rollover import (
    DEFAULT_ARCHIVE_CHUNK_ROWS,
    DEFAULT_ARCHIVE_COMPRESSION,
    DEFAULT_LEGACY_RETENTION_COUNT,
    DEFAULT_LEGACY_RETENTION_DAYS,
    DEFAULT_MAX_BYTES,
    DEFAULT_TAIL_RETENTION_COUNT,
    DEFAULT_TAIL_RETENTION_DAYS,
    execute_entry_decision_rollover,
)
from backend.services.entry_engines import ENTRY_DECISION_LOG_COLUMNS
from backend.services.storage_compaction import (
    DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_COUNT,
    DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_DAYS,
)


def _resolve_log_path() -> Path:
    path = Path(getattr(Config, "ENTRY_DECISION_LOG_PATH", r"data\trades\entry_decisions.csv"))
    if not path.is_absolute():
        path = ROOT / path
    return path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roll over, archive, and clean up entry_decisions storage.")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Roll when active file size reaches this limit.")
    parser.add_argument("--skip-daily-roll", action="store_true", help="Disable daily rollover checks.")
    parser.add_argument("--force", action="store_true", help="Force rollover even if thresholds are not met.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned action without mutating files.")
    parser.add_argument("--skip-archive", action="store_true", help="Skip parquet archive creation for the rolled file.")
    parser.add_argument("--archive-root", default="", help="Archive root directory. Defaults to data/trades/archive/entry_decisions.")
    parser.add_argument("--manifest-root", default="", help="Manifest root directory. Defaults to data/manifests.")
    parser.add_argument("--compression", default=DEFAULT_ARCHIVE_COMPRESSION, help="Parquet compression codec.")
    parser.add_argument("--chunk-rows", type=int, default=DEFAULT_ARCHIVE_CHUNK_ROWS, help="Rows per parquet conversion chunk.")
    parser.add_argument("--legacy-retention-days", type=int, default=DEFAULT_LEGACY_RETENTION_DAYS)
    parser.add_argument("--legacy-retention-count", type=int, default=DEFAULT_LEGACY_RETENTION_COUNT)
    parser.add_argument("--tail-retention-days", type=int, default=DEFAULT_TAIL_RETENTION_DAYS)
    parser.add_argument("--tail-retention-count", type=int, default=DEFAULT_TAIL_RETENTION_COUNT)
    parser.add_argument("--detail-retention-days", type=int, default=DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_DAYS)
    parser.add_argument("--detail-retention-count", type=int, default=DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_COUNT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = execute_entry_decision_rollover(
        path=_resolve_log_path(),
        columns=list(ENTRY_DECISION_LOG_COLUMNS),
        root=ROOT,
        max_bytes=int(args.max_bytes),
        roll_daily=not bool(args.skip_daily_roll),
        force=bool(args.force),
        dry_run=bool(args.dry_run),
        skip_archive=bool(args.skip_archive),
        archive_root=args.archive_root or None,
        manifest_root=args.manifest_root or None,
        compression=str(args.compression or DEFAULT_ARCHIVE_COMPRESSION),
        chunk_rows=int(args.chunk_rows),
        legacy_retention_days=int(args.legacy_retention_days),
        legacy_retention_count=int(args.legacy_retention_count),
        tail_retention_days=int(args.tail_retention_days),
        tail_retention_count=int(args.tail_retention_count),
        detail_retention_days=int(args.detail_retention_days),
        detail_retention_count=int(args.detail_retention_count),
        create_if_missing=not bool(args.dry_run),
        trigger_mode="manual_script",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
