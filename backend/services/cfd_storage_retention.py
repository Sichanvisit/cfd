from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


CFD_STORAGE_RETENTION_CONTRACT_VERSION = "cfd_storage_retention_v1"
_GIB = 1024 * 1024 * 1024
_COPY_CHUNK_BYTES = 8 * 1024 * 1024


def _env_flag(name: str, default: bool) -> bool:
    text = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    return text not in {"", "0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, str(default)) or str(default)).strip())
    except Exception:
        return float(default)


DEFAULT_STORAGE_CAP_BYTES = int(_env_float("CFD_STORAGE_RETENTION_CAP_GB", 20.0) * _GIB)
DEFAULT_STORAGE_WATCH_INTERVAL_MIN = max(5, int(_env_float("CFD_STORAGE_RETENTION_WATCH_INTERVAL_MIN", 60.0)))
DEFAULT_STORAGE_WATCH_ENABLED = _env_flag("CFD_STORAGE_RETENTION_WATCH_ENABLED", True)
DEFAULT_STORAGE_RUNTIME_TRIM_ENABLED = _env_flag("CFD_STORAGE_RETENTION_RUNTIME_TRIM_ENABLED", True)
DEFAULT_CHECKPOINT_DETAIL_MIN_BYTES = int(
    _env_float("CFD_STORAGE_RETENTION_CHECKPOINT_DETAIL_MIN_GB", 2.0) * _GIB
)


@dataclass(frozen=True)
class RetentionCandidate:
    path: Path
    category: str
    priority: int
    size_bytes: int
    modified_at: float


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_data_root(root: Path | None = None) -> Path:
    return Path(root or _repo_root()) / "data"


def default_manifest_root(root: Path | None = None) -> Path:
    return default_data_root(root) / "manifests" / "retention"


def default_latest_json_path(root: Path | None = None) -> Path:
    return default_data_root(root) / "analysis" / "shadow_auto" / "cfd_storage_retention_latest.json"


def default_latest_markdown_path(root: Path | None = None) -> Path:
    return default_data_root(root) / "analysis" / "shadow_auto" / "cfd_storage_retention_latest.md"


def _now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now().astimezone()).isoformat()


def _ensure_within_root(root: Path, target: Path) -> Path:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    if not str(resolved_target).startswith(str(resolved_root)):
        raise ValueError(f"Retention target escapes project root: {resolved_target}")
    return resolved_target


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (path for path in root.rglob("*") if path.is_file())


def _is_retention_housekeeping_file(path: Path) -> bool:
    normalized = str(path).replace("\\", "/").lower()
    return (
        "/data/manifests/retention/cfd_storage_retention_" in normalized
        or normalized.endswith("/data/analysis/shadow_auto/cfd_storage_retention_latest.json")
        or normalized.endswith("/data/analysis/shadow_auto/cfd_storage_retention_latest.md")
        or normalized.endswith("/data/analysis/shadow_auto/cfd_storage_retention_watch_history_latest.json")
        or normalized.endswith(".retention_tmp")
    )


def _path_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except FileNotFoundError:
        return 0


def _sum_tree_bytes(root: Path) -> int:
    return sum(_path_size(path) for path in _iter_files(root) if not _is_retention_housekeeping_file(path))


def _human_gb(value: int) -> float:
    return round(float(value) / float(_GIB), 3)


def _collect_candidates(root: Path) -> list[RetentionCandidate]:
    data_root = _ensure_within_root(root, root / "data")
    trades_root = data_root / "trades"
    backfill_jobs_root = data_root / "backfill" / "breakout_event" / "jobs"
    patterns: list[tuple[str, int, Iterable[Path]]] = [
        ("entry_rotated_detail", 10, trades_root.glob("entry_decisions.detail.rotate_*")),
        ("entry_rotated_detail_gzip", 11, trades_root.glob("entry_decisions.detail.rotate_*.jsonl.gz")),
        ("entry_legacy_csv", 20, trades_root.glob("entry_decisions.legacy_*.csv")),
        ("entry_legacy_detail", 21, trades_root.glob("entry_decisions.legacy_*.detail.jsonl")),
        ("entry_tail_csv", 30, trades_root.glob("entry_decisions.tail_*.csv")),
        ("entry_tail_detail", 31, trades_root.glob("entry_decisions.tail_*.detail.jsonl")),
        ("backfill_jobs", 40, backfill_jobs_root.rglob("*") if backfill_jobs_root.exists() else []),
    ]
    candidates: list[RetentionCandidate] = []
    for category, priority, iterator in patterns:
        for path in iterator:
            if not path.is_file():
                continue
            resolved = _ensure_within_root(root, path)
            stat = resolved.stat()
            candidates.append(
                RetentionCandidate(
                    path=resolved,
                    category=category,
                    priority=int(priority),
                    size_bytes=int(stat.st_size),
                    modified_at=float(stat.st_mtime),
                )
            )
    candidates.sort(key=lambda item: (item.priority, item.modified_at, str(item.path).lower()))
    return candidates


def _delete_candidate(candidate: RetentionCandidate, *, dry_run: bool) -> dict[str, Any]:
    payload = {
        "path": str(candidate.path),
        "category": candidate.category,
        "size_bytes": int(candidate.size_bytes),
        "deleted": False,
        "error": "",
    }
    if dry_run:
        payload["deleted"] = True
        payload["dry_run"] = True
        return payload
    try:
        candidate.path.unlink(missing_ok=True)
        payload["deleted"] = True
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


def _prune_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted((item for item in root.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            next(path.iterdir())
        except StopIteration:
            try:
                path.rmdir()
            except OSError:
                pass
        except OSError:
            continue


def _cleanup_stale_retention_temps(root: Path, data_root: Path, *, dry_run: bool) -> list[dict[str, Any]]:
    if not data_root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in data_root.rglob("*.retention_tmp"):
        if not path.is_file():
            continue
        resolved = _ensure_within_root(root, path)
        size_bytes = _path_size(resolved)
        entry = {
            "path": str(resolved),
            "category": "stale_retention_tmp",
            "size_bytes": int(size_bytes),
            "deleted": False,
            "error": "",
        }
        if dry_run:
            entry["deleted"] = True
            entry["dry_run"] = True
            entries.append(entry)
            continue
        try:
            resolved.unlink(missing_ok=True)
            entry["deleted"] = True
        except Exception as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return entries


def _copy_tail_bytes_aligned(source_path: Path, target_path: Path, *, target_bytes: int) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    size = _path_size(source_path)
    with source_path.open("rb") as source, target_path.open("wb") as target:
        if target_bytes <= 0:
            return 0
        if size > target_bytes:
            start = max(0, size - int(target_bytes))
            source.seek(start)
            if start > 0:
                source.readline()
        while True:
            chunk = source.read(_COPY_CHUNK_BYTES)
            if not chunk:
                break
            target.write(chunk)
            written += len(chunk)
    return int(written)


def _trim_checkpoint_detail(
    path: Path,
    *,
    target_bytes: int,
    min_bytes: int,
    dry_run: bool,
) -> dict[str, Any]:
    result = {
        "path": str(path),
        "trimmed": False,
        "before_bytes": _path_size(path),
        "after_bytes": _path_size(path),
        "target_bytes": int(max(min_bytes, target_bytes)),
        "min_bytes": int(min_bytes),
        "error": "",
    }
    if not path.exists():
        result["error"] = "checkpoint_detail_missing"
        return result
    before_bytes = int(result["before_bytes"])
    desired_bytes = max(int(min_bytes), int(target_bytes))
    if before_bytes <= desired_bytes:
        return result

    if dry_run:
        result["trimmed"] = True
        result["after_bytes"] = min(before_bytes, desired_bytes)
        result["dry_run"] = True
        return result

    temp_path = path.with_name(f"{path.name}.retention_tmp")
    try:
        copied_bytes = _copy_tail_bytes_aligned(path, temp_path, target_bytes=desired_bytes)
        os.replace(temp_path, path)
        result["trimmed"] = True
        result["after_bytes"] = _path_size(path) or int(copied_bytes)
    except Exception as exc:
        result["error"] = str(exc)
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
    return result


def _render_markdown(payload: Mapping[str, Any]) -> str:
    summary = dict(payload.get("summary", {}) or {})
    deleted_entries = list(payload.get("deleted_entries", []) or [])
    trim = dict(payload.get("checkpoint_detail_trim", {}) or {})
    lines: list[str] = []
    lines.append("# CFD Storage Retention")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- mode: `{summary.get('mode', '')}`")
    lines.append(f"- cap_gb: `{summary.get('cap_gb', 0)}`")
    lines.append(f"- before_gb: `{summary.get('before_gb', 0)}`")
    lines.append(f"- after_gb: `{summary.get('after_gb', 0)}`")
    lines.append(f"- deleted_count: `{summary.get('deleted_count', 0)}`")
    lines.append(f"- deleted_gb: `{summary.get('deleted_gb', 0)}`")
    lines.append(f"- checkpoint_detail_trimmed: `{summary.get('checkpoint_detail_trimmed', False)}`")
    lines.append(f"- under_cap: `{summary.get('under_cap', False)}`")
    lines.append("")
    lines.append("## Deleted")
    lines.append("")
    if not deleted_entries:
        lines.append("- none")
    else:
        for item in deleted_entries[:20]:
            lines.append(
                f"- `{item.get('category', '')}` | `{item.get('size_bytes', 0)}` bytes | `{item.get('path', '')}`"
            )
        if len(deleted_entries) > 20:
            lines.append(f"- ... and `{len(deleted_entries) - 20}` more")
    lines.append("")
    lines.append("## Checkpoint Detail Trim")
    lines.append("")
    for key in ("trimmed", "before_bytes", "after_bytes", "target_bytes", "error"):
        lines.append(f"- {key}: `{trim.get(key, '')}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_cfd_storage_retention(
    *,
    root: str | Path | None = None,
    cap_bytes: int | None = None,
    mode: str = "manual",
    dry_run: bool = False,
    allow_checkpoint_trim: bool | None = None,
    checkpoint_detail_min_bytes: int | None = None,
    latest_json_path: str | Path | None = None,
    latest_markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root or _repo_root()).resolve()
    data_root = _ensure_within_root(repo_root, default_data_root(repo_root))
    manifest_root = _ensure_within_root(repo_root, default_manifest_root(repo_root))
    latest_json = _ensure_within_root(repo_root, Path(latest_json_path or default_latest_json_path(repo_root)))
    latest_markdown = _ensure_within_root(repo_root, Path(latest_markdown_path or default_latest_markdown_path(repo_root)))
    current_cap_bytes = int(cap_bytes or DEFAULT_STORAGE_CAP_BYTES)
    current_allow_checkpoint_trim = (
        DEFAULT_STORAGE_RUNTIME_TRIM_ENABLED if allow_checkpoint_trim is None else bool(allow_checkpoint_trim)
    )
    current_checkpoint_min_bytes = int(
        checkpoint_detail_min_bytes or DEFAULT_CHECKPOINT_DETAIL_MIN_BYTES
    )
    checkpoint_detail_path = _ensure_within_root(
        repo_root,
        data_root / "runtime" / "checkpoint_rows.detail.jsonl",
    )

    housekeeping_entries = _cleanup_stale_retention_temps(repo_root, data_root, dry_run=dry_run)
    before_bytes = _sum_tree_bytes(data_root)
    remaining_bytes = int(before_bytes)
    deleted_entries: list[dict[str, Any]] = []
    deleted_bytes = 0

    for candidate in _collect_candidates(repo_root):
        if remaining_bytes <= current_cap_bytes:
            break
        deleted = _delete_candidate(candidate, dry_run=dry_run)
        if deleted.get("deleted"):
            remaining_bytes = max(0, remaining_bytes - int(candidate.size_bytes))
            deleted_bytes += int(candidate.size_bytes)
            deleted_entries.append(deleted)
        elif deleted.get("error"):
            deleted_entries.append(deleted)

    trim_result = {
        "path": str(checkpoint_detail_path),
        "trimmed": False,
        "before_bytes": _path_size(checkpoint_detail_path),
        "after_bytes": _path_size(checkpoint_detail_path),
        "target_bytes": int(current_checkpoint_min_bytes),
        "min_bytes": int(current_checkpoint_min_bytes),
        "error": "",
    }
    if remaining_bytes > current_cap_bytes and current_allow_checkpoint_trim:
        trim_result = _trim_checkpoint_detail(
            checkpoint_detail_path,
            target_bytes=current_checkpoint_min_bytes,
            min_bytes=current_checkpoint_min_bytes,
            dry_run=dry_run,
        )
        if trim_result.get("trimmed"):
            freed = max(0, int(trim_result.get("before_bytes", 0)) - int(trim_result.get("after_bytes", 0)))
            remaining_bytes = max(0, remaining_bytes - freed)

    if not dry_run:
        _prune_empty_dirs(data_root / "backfill")
        _prune_empty_dirs(data_root / "trades")
    after_bytes = int(remaining_bytes) if dry_run else _sum_tree_bytes(data_root)
    timestamp = datetime.now().astimezone()
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / f"cfd_storage_retention_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    payload: dict[str, Any] = {
        "contract_version": CFD_STORAGE_RETENTION_CONTRACT_VERSION,
        "generated_at": _now_iso(timestamp),
        "summary": {
            "mode": str(mode or "manual"),
            "cap_bytes": int(current_cap_bytes),
            "cap_gb": _human_gb(current_cap_bytes),
            "before_bytes": int(before_bytes),
            "before_gb": _human_gb(before_bytes),
            "after_bytes": int(after_bytes),
            "after_gb": _human_gb(after_bytes),
            "deleted_count": len([item for item in deleted_entries if item.get("deleted")]),
            "deleted_bytes": int(deleted_bytes),
            "deleted_gb": _human_gb(deleted_bytes),
            "housekeeping_deleted_count": len([item for item in housekeeping_entries if item.get("deleted")]),
            "housekeeping_deleted_bytes": int(
                sum(int(item.get("size_bytes", 0) or 0) for item in housekeeping_entries if item.get("deleted"))
            ),
            "housekeeping_deleted_gb": _human_gb(
                sum(int(item.get("size_bytes", 0) or 0) for item in housekeeping_entries if item.get("deleted"))
            ),
            "checkpoint_detail_trimmed": bool(trim_result.get("trimmed")),
            "allow_checkpoint_trim": bool(current_allow_checkpoint_trim),
            "under_cap": int(after_bytes) <= int(current_cap_bytes),
            "dry_run": bool(dry_run),
        },
        "paths": {
            "repo_root": str(repo_root),
            "data_root": str(data_root),
            "checkpoint_detail_path": str(checkpoint_detail_path),
            "manifest_path": str(manifest_path),
            "latest_json_path": str(latest_json),
            "latest_markdown_path": str(latest_markdown),
        },
        "deleted_entries": deleted_entries,
        "housekeeping_entries": housekeeping_entries,
        "checkpoint_detail_trim": trim_result,
    }

    _write_json(manifest_path, payload)
    _write_json(latest_json, payload)
    _write_text(latest_markdown, _render_markdown(payload))
    if not dry_run:
        actual_after_bytes = _sum_tree_bytes(data_root)
        payload["summary"]["after_bytes"] = int(actual_after_bytes)
        payload["summary"]["after_gb"] = _human_gb(actual_after_bytes)
        payload["summary"]["under_cap"] = int(actual_after_bytes) <= int(current_cap_bytes)
        _write_json(manifest_path, payload)
        _write_json(latest_json, payload)
        _write_text(latest_markdown, _render_markdown(payload))
    return payload
