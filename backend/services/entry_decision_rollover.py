from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from backend.services.storage_compaction import (
    DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_COUNT,
    DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_DAYS,
    resolve_entry_decision_detail_path,
)


logger = logging.getLogger(__name__)

ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION = "entry_decision_rollover_v1"


def _env_flag(name: str, default: bool) -> bool:
    text = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    return text not in {"", "0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, str(default)) or str(default)).strip())
    except Exception:
        return int(default)


def _env_text(name: str, default: str) -> str:
    return str(os.getenv(name, default) or default).strip() or default


DEFAULT_MAX_BYTES = int(os.getenv("ENTRY_DECISION_ROLLOVER_MAX_BYTES", str(1024 * 1024 * 1024)))
DEFAULT_ROLL_DAILY = _env_flag("ENTRY_DECISION_ROLLOVER_DAILY", True)
DEFAULT_ENABLED = _env_flag("ENTRY_DECISION_ROLLOVER_ENABLED", True)
DEFAULT_ARCHIVE_CHUNK_ROWS = int(os.getenv("ENTRY_DECISION_ARCHIVE_CHUNK_ROWS", "10000"))
DEFAULT_ARCHIVE_COMPRESSION = str(os.getenv("ENTRY_DECISION_ARCHIVE_COMPRESSION", "zstd") or "zstd").strip() or "zstd"
DEFAULT_LEGACY_RETENTION_DAYS = int(os.getenv("ENTRY_DECISION_LEGACY_RETENTION_DAYS", "7"))
DEFAULT_LEGACY_RETENTION_COUNT = int(os.getenv("ENTRY_DECISION_LEGACY_RETENTION_COUNT", "3"))
DEFAULT_TAIL_RETENTION_DAYS = int(os.getenv("ENTRY_DECISION_TAIL_RETENTION_DAYS", "7"))
DEFAULT_TAIL_RETENTION_COUNT = int(os.getenv("ENTRY_DECISION_TAIL_RETENTION_COUNT", "3"))


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _resolve_archive_root(path_like: str | Path | None, *, root: Path) -> Path:
    env_value = str(os.getenv("ENTRY_DECISION_ARCHIVE_ROOT", "") or "").strip()
    raw = path_like if path_like else env_value
    if raw:
        target = Path(raw)
        if not target.is_absolute():
            target = root / target
    else:
        target = root / "data" / "trades" / "archive" / "entry_decisions"
    return target


def _resolve_manifest_root(path_like: str | Path | None, *, root: Path) -> Path:
    env_value = str(os.getenv("ENTRY_DECISION_MANIFEST_ROOT", "") or "").strip()
    raw = path_like if path_like else env_value
    if raw:
        target = Path(raw)
        if not target.is_absolute():
            target = root / target
    else:
        target = root / "data" / "manifests"
    return target


def _ensure_manifest_dirs(manifest_root: Path) -> dict[str, Path]:
    mapping = {
        "rollover": manifest_root / "rollover",
        "archive": manifest_root / "archive",
        "retention": manifest_root / "retention",
    }
    for path in mapping.values():
        path.mkdir(parents=True, exist_ok=True)
    return mapping


def _write_manifest(dir_path: Path, prefix: str, payload: dict[str, Any], timestamp: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    out_path = dir_path / f"{prefix}_{timestamp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return list(next(reader))
        except StopIteration:
            return []


def _write_fresh_active_csv(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()


def _build_rollover_reasons(
    path: Path,
    *,
    columns: list[str],
    max_bytes: int,
    roll_daily: bool,
    force: bool,
    now: datetime,
) -> list[str]:
    reasons: list[str] = []
    if force:
        reasons.append("force")
    if not path.exists():
        return reasons
    current_size = int(path.stat().st_size)
    if current_size >= int(max_bytes):
        reasons.append("size_limit")
    if roll_daily and current_size > 0:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_at.date() < now.date():
            reasons.append("day_boundary")
    existing_header = _read_header(path)
    if list(existing_header) != list(columns):
        reasons.append("schema_change")
    return reasons


def _archive_csv_to_parquet(
    csv_path: Path,
    *,
    archive_root: Path,
    partition_dt: datetime,
    timestamp: str,
    compression: str,
    chunk_rows: int,
) -> dict[str, Any]:
    archive_dir = archive_root / f"year={partition_dt:%Y}" / f"month={partition_dt:%m}" / f"day={partition_dt:%d}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = archive_dir / f"{csv_path.stem}_{timestamp}.parquet"

    header = _read_header(csv_path)
    schema = pa.schema([(column, pa.string()) for column in header])
    row_count = 0
    writer: pq.ParquetWriter | None = None
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None

    try:
        for chunk in pd.read_csv(
            csv_path,
            dtype=str,
            chunksize=max(1, int(chunk_rows)),
            encoding="utf-8-sig",
            keep_default_na=False,
            na_filter=False,
        ):
            if list(chunk.columns) != header:
                chunk = chunk.reindex(columns=header, fill_value="")
            if "time" in chunk.columns:
                for value in chunk["time"].astype(str).tolist():
                    parsed = _parse_dt(value)
                    if parsed is None:
                        continue
                    time_range_start = parsed if time_range_start is None else min(time_range_start, parsed)
                    time_range_end = parsed if time_range_end is None else max(time_range_end, parsed)
            arrays = [pa.array(chunk[col].astype(str).tolist(), type=pa.string()) for col in header]
            table = pa.Table.from_arrays(arrays, schema=schema)
            if writer is None:
                writer = pq.ParquetWriter(parquet_path, schema=schema, compression=compression)
            writer.write_table(table)
            row_count += int(len(chunk))

        if writer is None:
            writer = pq.ParquetWriter(parquet_path, schema=schema, compression=compression)
            empty_arrays = [pa.array([], type=pa.string()) for _ in header]
            writer.write_table(pa.Table.from_arrays(empty_arrays, schema=schema))
    finally:
        if writer is not None:
            writer.close()

    return {
        "path": str(parquet_path),
        "row_count": int(row_count),
        "file_size_bytes": int(parquet_path.stat().st_size),
        "compression": compression,
        "chunk_rows": int(chunk_rows),
        "columns": list(header),
        "time_range_start": time_range_start.isoformat(timespec="seconds") if time_range_start else "",
        "time_range_end": time_range_end.isoformat(timespec="seconds") if time_range_end else "",
    }


def _cleanup_group(
    *,
    parent_dir: Path,
    stem: str,
    suffix: str,
    marker: str,
    keep_days: int,
    keep_count: int,
    now: datetime,
) -> dict[str, Any]:
    pattern = f"{stem}.{marker}_*{suffix}"
    matched = [path for path in parent_dir.glob(pattern) if path.is_file()]
    matched.sort(key=lambda item: item.stat().st_mtime, reverse=True)

    keep_count = max(0, int(keep_count))
    keep_until = now - timedelta(days=max(0, int(keep_days)))

    kept: list[str] = []
    deleted: list[str] = []

    for index, item in enumerate(matched):
        modified_at = datetime.fromtimestamp(item.stat().st_mtime)
        keep_due_to_rank = index < keep_count
        keep_due_to_age = modified_at >= keep_until
        if keep_due_to_rank or keep_due_to_age:
            kept.append(str(item))
            continue
        item.unlink(missing_ok=True)
        deleted.append(str(item))

    return {
        "marker": marker,
        "pattern": pattern,
        "matched_count": len(matched),
        "kept_count": len(kept),
        "deleted_count": len(deleted),
        "keep_days": int(keep_days),
        "keep_count": int(keep_count),
        "kept_paths": kept,
        "deleted_paths": deleted,
    }


def _artifact_label_from_path(path: Path) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_")
    return text or "entry_decisions"


def archive_entry_decision_csv_source(
    *,
    source_path: Path,
    root: Path,
    now: datetime | None = None,
    archive_root: str | Path | None = None,
    manifest_root: str | Path | None = None,
    source_detail_path: Path | None = None,
    compression: str | None = None,
    chunk_rows: int | None = None,
    trigger_mode: str = "targeted_backfill",
    notes: str = "",
    archive_partition_dt: datetime | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path)
    current_now = now or datetime.now()
    current_compression = str(
        compression if compression is not None else _env_text("ENTRY_DECISION_ARCHIVE_COMPRESSION", DEFAULT_ARCHIVE_COMPRESSION)
    ).strip() or "zstd"
    current_chunk_rows = int(
        _env_int("ENTRY_DECISION_ARCHIVE_CHUNK_ROWS", DEFAULT_ARCHIVE_CHUNK_ROWS)
        if chunk_rows is None
        else chunk_rows
    )
    archive_root_path = _resolve_archive_root(archive_root, root=root)
    manifest_root_path = _resolve_manifest_root(manifest_root, root=root)
    manifest_dirs = _ensure_manifest_dirs(manifest_root_path)
    detail_path = Path(source_detail_path) if source_detail_path is not None else resolve_entry_decision_detail_path(source_path)

    if not source_path.exists():
        return {
            "ok": False,
            "error": f"source_not_found: {source_path}",
            "source_path": str(source_path),
            "detail_source_path": str(detail_path),
            "archive_path": "",
            "archive_manifest_path": "",
            "row_count": 0,
            "time_range_start": "",
            "time_range_end": "",
        }

    stat = source_path.stat()
    source_modified_at = datetime.fromtimestamp(stat.st_mtime)
    partition_dt = archive_partition_dt or source_modified_at
    timestamp = f"{current_now.strftime('%Y%m%d_%H%M%S_%f')}_{_artifact_label_from_path(source_path)}"
    archive_payload = _archive_csv_to_parquet(
        source_path,
        archive_root=archive_root_path,
        partition_dt=partition_dt,
        timestamp=timestamp,
        compression=current_compression,
        chunk_rows=current_chunk_rows,
    )
    archive_manifest = {
        "created_at": current_now.astimezone().isoformat(),
        "job_name": "entry_decisions_archive",
        "trigger_mode": str(trigger_mode or "targeted_backfill"),
        "source_path": str(source_path),
        "detail_source_path": str(detail_path) if detail_path.exists() else "",
        "output_path": archive_payload["path"],
        "archive_root": str(archive_root_path),
        "manifest_root": str(manifest_root_path),
        "schema_version": "entry_decisions_archive_v2",
        "contract_version": ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION,
        "row_count": int(archive_payload["row_count"]),
        "file_size_bytes": int(archive_payload["file_size_bytes"]),
        "compression": archive_payload["compression"],
        "source_size_bytes": int(stat.st_size),
        "time_range_start": archive_payload.get("time_range_start", ""),
        "time_range_end": archive_payload.get("time_range_end", ""),
        "source_modified_at": source_modified_at.astimezone().isoformat(),
        "retention_policy": "historical_backfill_archive",
        "notes": notes or "Historical source archived for decision_log_coverage_gap targeted backfill.",
    }
    archive_manifest_path = str(
        _write_manifest(manifest_dirs["archive"], "entry_decisions_archive", archive_manifest, timestamp)
    )
    return {
        "ok": True,
        "error": "",
        "source_path": str(source_path),
        "detail_source_path": str(detail_path) if detail_path.exists() else "",
        "archive_path": archive_payload["path"],
        "archive_manifest_path": archive_manifest_path,
        "row_count": int(archive_payload["row_count"]),
        "file_size_bytes": int(archive_payload["file_size_bytes"]),
        "time_range_start": archive_payload.get("time_range_start", ""),
        "time_range_end": archive_payload.get("time_range_end", ""),
        "compression": archive_payload["compression"],
        "trigger_mode": str(trigger_mode or "targeted_backfill"),
    }


def execute_entry_decision_rollover(
    *,
    path: Path,
    columns: list[str],
    root: Path,
    now: datetime | None = None,
    max_bytes: int | None = None,
    roll_daily: bool | None = None,
    enabled: bool | None = None,
    force: bool = False,
    dry_run: bool = False,
    skip_archive: bool = False,
    archive_root: str | Path | None = None,
    manifest_root: str | Path | None = None,
    compression: str | None = None,
    chunk_rows: int | None = None,
    legacy_retention_days: int | None = None,
    legacy_retention_count: int | None = None,
    tail_retention_days: int | None = None,
    tail_retention_count: int | None = None,
    detail_retention_days: int | None = None,
    detail_retention_count: int | None = None,
    create_if_missing: bool = False,
    trigger_mode: str = "manual_script",
) -> dict[str, Any]:
    current_now = now or datetime.now()
    current_enabled = _env_flag("ENTRY_DECISION_ROLLOVER_ENABLED", True) if enabled is None else bool(enabled)
    current_max_bytes = int(_env_int("ENTRY_DECISION_ROLLOVER_MAX_BYTES", DEFAULT_MAX_BYTES) if max_bytes is None else max_bytes)
    current_roll_daily = _env_flag("ENTRY_DECISION_ROLLOVER_DAILY", True) if roll_daily is None else bool(roll_daily)
    current_compression = str(
        compression if compression is not None else _env_text("ENTRY_DECISION_ARCHIVE_COMPRESSION", DEFAULT_ARCHIVE_COMPRESSION)
    ).strip() or "zstd"
    current_chunk_rows = int(
        _env_int("ENTRY_DECISION_ARCHIVE_CHUNK_ROWS", DEFAULT_ARCHIVE_CHUNK_ROWS)
        if chunk_rows is None
        else chunk_rows
    )
    current_legacy_retention_days = int(
        _env_int("ENTRY_DECISION_LEGACY_RETENTION_DAYS", DEFAULT_LEGACY_RETENTION_DAYS)
        if legacy_retention_days is None
        else legacy_retention_days
    )
    current_legacy_retention_count = int(
        _env_int("ENTRY_DECISION_LEGACY_RETENTION_COUNT", DEFAULT_LEGACY_RETENTION_COUNT)
        if legacy_retention_count is None
        else legacy_retention_count
    )
    current_tail_retention_days = int(
        _env_int("ENTRY_DECISION_TAIL_RETENTION_DAYS", DEFAULT_TAIL_RETENTION_DAYS)
        if tail_retention_days is None
        else tail_retention_days
    )
    current_tail_retention_count = int(
        _env_int("ENTRY_DECISION_TAIL_RETENTION_COUNT", DEFAULT_TAIL_RETENTION_COUNT)
        if tail_retention_count is None
        else tail_retention_count
    )
    current_detail_retention_days = int(
        _env_int("ENTRY_DECISION_DETAIL_RETENTION_DAYS", DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_DAYS)
        if detail_retention_days is None
        else detail_retention_days
    )
    current_detail_retention_count = int(
        _env_int("ENTRY_DECISION_DETAIL_RETENTION_COUNT", DEFAULT_ENTRY_DECISION_DETAIL_RETENTION_COUNT)
        if detail_retention_count is None
        else detail_retention_count
    )

    archive_root_path = _resolve_archive_root(archive_root, root=root)
    manifest_root_path = _resolve_manifest_root(manifest_root, root=root)
    detail_path = resolve_entry_decision_detail_path(path)
    reasons = _build_rollover_reasons(
        path,
        columns=columns,
        max_bytes=current_max_bytes,
        roll_daily=current_roll_daily,
        force=bool(force),
        now=current_now,
    )
    summary: dict[str, Any] = {
        "contract_version": ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION,
        "created_at": current_now.isoformat(timespec="seconds"),
        "job_name": "entry_decisions_rollover",
        "trigger_mode": str(trigger_mode or "manual_script"),
        "source_path": str(path),
        "detail_source_path": str(detail_path),
        "exists": path.exists(),
        "enabled": bool(current_enabled),
        "source_size_bytes": int(path.stat().st_size) if path.exists() else 0,
        "detail_exists": detail_path.exists(),
        "detail_source_size_bytes": int(detail_path.stat().st_size) if detail_path.exists() else 0,
        "rollover_reasons": list(reasons),
        "would_roll": bool(path.exists() and reasons and (current_enabled or bool(force))),
        "rolled": False,
        "max_bytes": current_max_bytes,
        "roll_daily": bool(current_roll_daily),
        "archive_root": str(archive_root_path),
        "manifest_root": str(manifest_root_path),
        "archive_path": "",
        "archive_manifest_path": "",
        "retention_manifest_path": "",
        "rollover_manifest_path": "",
        "backup_path": "",
        "detail_backup_path": "",
        "error": "",
    }

    if not current_enabled and not force:
        summary["skip_reason"] = "rollover_disabled"
        return summary

    if dry_run or not path.exists() or not reasons:
        if create_if_missing and not path.exists() and not dry_run:
            _write_fresh_active_csv(path, columns)
            summary["created_new_active_file"] = True
        return summary

    manifest_dirs = _ensure_manifest_dirs(manifest_root_path)
    timestamp = current_now.strftime("%Y%m%d_%H%M%S")
    header_before = _read_header(path)
    source_size_bytes = int(path.stat().st_size)
    source_modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    backup_path = path.with_name(f"{path.stem}.legacy_{timestamp}{path.suffix}")
    detail_backup_path = resolve_entry_decision_detail_path(backup_path)

    try:
        shutil.move(str(path), str(backup_path))
        if detail_path.exists():
            shutil.move(str(detail_path), str(detail_backup_path))
        _write_fresh_active_csv(path, columns)

        archive_payload: dict[str, Any] | None = None
        archive_manifest_path = ""
        if not skip_archive:
            archive_payload = _archive_csv_to_parquet(
                backup_path,
                archive_root=archive_root_path,
                partition_dt=source_modified_at,
                timestamp=timestamp,
                compression=current_compression,
                chunk_rows=current_chunk_rows,
            )
            archive_manifest = {
                "created_at": current_now.astimezone().isoformat(),
                "job_name": "entry_decisions_archive",
                "trigger_mode": str(trigger_mode or "manual_script"),
                "source_path": str(backup_path),
                "detail_source_path": str(detail_backup_path) if detail_backup_path.exists() else "",
                "output_path": archive_payload["path"],
                "archive_root": str(archive_root_path),
                "manifest_root": str(manifest_root_path),
                "schema_version": "entry_decisions_archive_v2",
                "contract_version": ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION,
                "row_count": int(archive_payload["row_count"]),
                "file_size_bytes": int(archive_payload["file_size_bytes"]),
                "compression": archive_payload["compression"],
                "source_size_bytes": int(source_size_bytes),
                "time_range_start": archive_payload.get("time_range_start", ""),
                "time_range_end": archive_payload.get("time_range_end", ""),
                "source_modified_at": source_modified_at.astimezone().isoformat(),
                "retention_policy": "legacy_csv_retained_until_cleanup",
                "notes": "CSV archived as all-string parquet for warm retention.",
            }
            archive_manifest_path = str(
                _write_manifest(manifest_dirs["archive"], "entry_decisions_archive", archive_manifest, timestamp)
            )

        retention_results = {
            "legacy": _cleanup_group(
                parent_dir=path.parent,
                stem=path.stem,
                suffix=path.suffix,
                marker="legacy",
                keep_days=current_legacy_retention_days,
                keep_count=current_legacy_retention_count,
                now=current_now,
            ),
            "tail": _cleanup_group(
                parent_dir=path.parent,
                stem=path.stem,
                suffix=path.suffix,
                marker="tail",
                keep_days=current_tail_retention_days,
                keep_count=current_tail_retention_count,
                now=current_now,
            ),
            "legacy_detail": _cleanup_group(
                parent_dir=path.parent,
                stem=path.stem,
                suffix=".detail.jsonl",
                marker="legacy",
                keep_days=current_legacy_retention_days,
                keep_count=current_legacy_retention_count,
                now=current_now,
            ),
            "tail_detail": _cleanup_group(
                parent_dir=path.parent,
                stem=path.stem,
                suffix=".detail.jsonl",
                marker="tail",
                keep_days=current_tail_retention_days,
                keep_count=current_tail_retention_count,
                now=current_now,
            ),
            "rotated_detail": _cleanup_group(
                parent_dir=detail_path.parent,
                stem=detail_path.stem,
                suffix=detail_path.suffix,
                marker="rotate",
                keep_days=current_detail_retention_days,
                keep_count=current_detail_retention_count,
                now=current_now,
            ),
            "rotated_detail_gzip": _cleanup_group(
                parent_dir=detail_path.parent,
                stem=detail_path.stem,
                suffix=f"{detail_path.suffix}.gz",
                marker="rotate",
                keep_days=current_detail_retention_days,
                keep_count=current_detail_retention_count,
                now=current_now,
            ),
        }
        retention_manifest = {
            "created_at": current_now.astimezone().isoformat(),
            "job_name": "entry_decisions_retention",
            "trigger_mode": str(trigger_mode or "manual_script"),
            "source_path": str(path.parent),
            "output_path": "",
            "archive_root": str(archive_root_path),
            "manifest_root": str(manifest_root_path),
            "schema_version": "entry_decisions_retention_v2",
            "contract_version": ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION,
            "row_count": 0,
            "file_size_bytes": 0,
            "compression": "",
            "retention_policy": {
                "legacy_days": current_legacy_retention_days,
                "legacy_count": current_legacy_retention_count,
                "tail_days": current_tail_retention_days,
                "tail_count": current_tail_retention_count,
                "detail_days": current_detail_retention_days,
                "detail_count": current_detail_retention_count,
            },
            "notes": retention_results,
        }
        retention_manifest_path = str(
            _write_manifest(manifest_dirs["retention"], "entry_decisions_retention", retention_manifest, timestamp)
        )

        rollover_manifest = {
            "created_at": current_now.astimezone().isoformat(),
            "job_name": "entry_decisions_rollover",
            "trigger_mode": str(trigger_mode or "manual_script"),
            "source_path": str(path),
            "detail_source_path": str(detail_path),
            "backup_path": str(backup_path),
            "detail_backup_path": str(detail_backup_path) if detail_backup_path.exists() else "",
            "output_path": str(path),
            "archive_root": str(archive_root_path),
            "manifest_root": str(manifest_root_path),
            "schema_version": "entry_decisions_rollover_v3",
            "contract_version": ENTRY_DECISION_ROLLOVER_CONTRACT_VERSION,
            "row_count": int(archive_payload["row_count"]) if archive_payload is not None else 0,
            "file_size_bytes": int(source_size_bytes),
            "compression": archive_payload["compression"] if archive_payload is not None else "",
            "previous_header": list(header_before),
            "new_header": list(columns),
            "rollover_reasons": list(reasons),
            "source_modified_at": source_modified_at.astimezone().isoformat(),
            "archive_path": (archive_payload or {}).get("path", ""),
            "archive_time_range_start": (archive_payload or {}).get("time_range_start", ""),
            "archive_time_range_end": (archive_payload or {}).get("time_range_end", ""),
            "archive_manifest_path": archive_manifest_path,
            "retention_manifest_path": retention_manifest_path,
            "retention_summary": {
                "legacy_deleted_count": retention_results["legacy"]["deleted_count"],
                "tail_deleted_count": retention_results["tail"]["deleted_count"],
                "legacy_detail_deleted_count": retention_results["legacy_detail"]["deleted_count"],
                "tail_detail_deleted_count": retention_results["tail_detail"]["deleted_count"],
                "rotated_detail_deleted_count": retention_results["rotated_detail"]["deleted_count"],
                "rotated_detail_gzip_deleted_count": retention_results["rotated_detail_gzip"]["deleted_count"],
            },
        }
        rollover_manifest_path = str(
            _write_manifest(manifest_dirs["rollover"], "entry_decisions_rollover", rollover_manifest, timestamp)
        )

        summary.update(
            {
                "rolled": True,
                "would_roll": True,
                "backup_path": str(backup_path),
                "detail_backup_path": str(detail_backup_path) if detail_backup_path.exists() else "",
                "archive_path": (archive_payload or {}).get("path", ""),
                "archive_manifest_path": archive_manifest_path,
                "retention_manifest_path": retention_manifest_path,
                "rollover_manifest_path": rollover_manifest_path,
                "row_count": int((archive_payload or {}).get("row_count", 0) or 0),
                "source_modified_at": source_modified_at.astimezone().isoformat(),
            }
        )
        return summary
    except Exception as exc:
        logger.exception("entry decision rollover failed")
        summary["error"] = str(exc)
        return summary
