"""File-backed observability adapter."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from ports.observability_port import ObservabilityPort


class FileObservabilityAdapter(ObservabilityPort):
    """
    Persist lightweight runtime counters/events as files.

    - counters: JSON object map
    - events: JSONL stream
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        events_max_bytes: int | None = None,
        events_backup_count: int | None = None,
        events_retention_days: int | None = None,
        roll_daily: bool = True,
    ):
        root = Path(base_dir) if base_dir is not None else (Path(__file__).resolve().parents[1] / "data" / "observability")
        self._base_dir = root
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._counters_path = self._base_dir / "counters.json"
        self._events_path = self._base_dir / "events.jsonl"
        self._lock = Lock()
        self._events_max_bytes = int(events_max_bytes or os.getenv("OBS_EVENTS_MAX_BYTES", 10 * 1024 * 1024))
        self._events_backup_count = int(events_backup_count or os.getenv("OBS_EVENTS_BACKUP_COUNT", 5))
        self._events_retention_days = int(events_retention_days or os.getenv("OBS_EVENTS_RETENTION_DAYS", 7))
        self._roll_daily = bool(roll_daily)
        if not self._counters_path.exists():
            self._write_json(self._counters_path, {})

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return dict(json.loads(path.read_text(encoding="utf-8")) or {})
        except Exception:
            return {}

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def _event_archive_paths(self) -> list[Path]:
        paths = [
            path
            for path in self._base_dir.glob("events.*.jsonl")
            if path.is_file() and path.name != self._events_path.name
        ]
        return sorted(paths, key=lambda item: item.stat().st_mtime)

    def _should_roll_events(self) -> bool:
        if not self._events_path.exists():
            return False
        size_bytes = int(self._events_path.stat().st_size)
        if size_bytes >= self._events_max_bytes:
            return True
        if self._roll_daily and size_bytes > 0:
            modified_at = datetime.fromtimestamp(self._events_path.stat().st_mtime)
            if modified_at.date() < datetime.now().date():
                return True
        return False

    def _cleanup_event_archives(self) -> None:
        archives = sorted(self._event_archive_paths(), key=lambda item: item.stat().st_mtime, reverse=True)
        cutoff = datetime.now() - timedelta(days=max(0, self._events_retention_days))
        for index, path in enumerate(archives):
            modified_at = datetime.fromtimestamp(path.stat().st_mtime)
            if index < max(0, self._events_backup_count):
                continue
            if modified_at >= cutoff:
                continue
            path.unlink(missing_ok=True)

    def _roll_events_if_needed(self) -> None:
        if not self._should_roll_events():
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self._base_dir / f"events.{timestamp}.jsonl"
        if archive_path.exists():
            archive_path.unlink(missing_ok=True)
        self._events_path.replace(archive_path)
        self._cleanup_event_archives()

    def incr(self, name: str, amount: int = 1) -> None:
        key = str(name or "").strip()
        if not key:
            return
        with self._lock:
            row = self._read_json(self._counters_path)
            row[key] = int(row.get(key, 0) or 0) + int(amount)
            row["updated_at"] = self._now_iso()
            self._write_json(self._counters_path, row)

    def event(self, name: str, *, level: str = "info", payload: dict[str, Any] | None = None) -> None:
        event_name = str(name or "").strip()
        if not event_name:
            return
        item = {
            "at": self._now_iso(),
            "name": event_name,
            "level": str(level or "info").lower(),
            "payload": dict(payload or {}),
        }
        line = json.dumps(item, ensure_ascii=False)
        with self._lock:
            self._roll_events_if_needed()
            with self._events_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def snapshot(self, last_n: int = 50) -> dict[str, Any]:
        n = max(1, min(500, int(last_n)))
        with self._lock:
            counters = self._read_json(self._counters_path)
            events: list[dict[str, Any]] = []
            event_paths = self._event_archive_paths() + ([self._events_path] if self._events_path.exists() else [])
            try:
                lines: list[str] = []
                for path in event_paths:
                    lines.extend(path.read_text(encoding="utf-8").splitlines())
                for line in lines[-n:]:
                    line = str(line or "").strip()
                    if not line:
                        continue
                    try:
                        events.append(dict(json.loads(line)))
                    except Exception:
                        continue
            except Exception:
                events = []
        return {
            "counters": counters,
            "events": events,
            "events_count": len(events),
            "base_dir": str(self._base_dir),
        }
