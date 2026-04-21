from __future__ import annotations

import json
import os
from pathlib import Path

from backend.services.cfd_storage_retention import run_cfd_storage_retention


def _write_blob(path: Path, size_bytes: int, *, char: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(char * max(0, int(size_bytes)))


def _write_jsonl(path: Path, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index in range(rows):
            handle.write(json.dumps({"row": index, "payload": "x" * 64}, ensure_ascii=False) + "\n")


def _set_old_mtime(path: Path, seconds_ago: int) -> None:
    current = path.stat().st_mtime
    target = current - float(seconds_ago)
    os.utime(path, (target, target))


def test_storage_retention_deletes_historical_candidates_before_touching_active_files(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _write_blob(data_root / "trades" / "entry_decisions.csv", 128)
    _write_blob(data_root / "trades" / "entry_decisions.detail.jsonl", 256)

    rotated = data_root / "trades" / "entry_decisions.detail.rotate_20260401_000000.jsonl"
    legacy_csv = data_root / "trades" / "entry_decisions.legacy_20260401_000000.csv"
    backfill = data_root / "backfill" / "breakout_event" / "jobs" / "job_a" / "payload.json"
    _write_blob(rotated, 4 * 1024)
    _write_blob(legacy_csv, 5 * 1024)
    _write_blob(backfill, 6 * 1024)
    _set_old_mtime(rotated, 300)
    _set_old_mtime(legacy_csv, 200)
    _set_old_mtime(backfill, 100)

    payload = run_cfd_storage_retention(
        root=tmp_path,
        cap_bytes=4 * 1024,
        mode="manual",
        allow_checkpoint_trim=False,
    )

    summary = payload["summary"]
    assert summary["under_cap"] is True
    assert rotated.exists() is False
    assert legacy_csv.exists() is False
    assert backfill.exists() is False
    assert (data_root / "trades" / "entry_decisions.csv").exists()
    assert (data_root / "trades" / "entry_decisions.detail.jsonl").exists()


def test_storage_retention_trims_checkpoint_detail_tail_when_cap_still_exceeded(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    checkpoint_detail = data_root / "runtime" / "checkpoint_rows.detail.jsonl"
    _write_jsonl(checkpoint_detail, 200)
    _write_blob(data_root / "runtime" / "checkpoint_rows.csv", 128)

    before_lines = checkpoint_detail.read_text(encoding="utf-8").strip().splitlines()
    before_last = json.loads(before_lines[-1])

    payload = run_cfd_storage_retention(
        root=tmp_path,
        cap_bytes=3 * 1024,
        mode="manual",
        allow_checkpoint_trim=True,
        checkpoint_detail_min_bytes=1024,
    )

    summary = payload["summary"]
    trim = payload["checkpoint_detail_trim"]
    after_lines = checkpoint_detail.read_text(encoding="utf-8").strip().splitlines()
    after_last = json.loads(after_lines[-1])

    assert trim["trimmed"] is True
    assert summary["under_cap"] is True
    assert len(after_lines) < len(before_lines)
    assert after_last["row"] == before_last["row"]
