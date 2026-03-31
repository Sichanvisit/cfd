import csv
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "rollover_entry_decisions.py"
spec = importlib.util.spec_from_file_location("rollover_entry_decisions", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_entry_decisions(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(module.ENTRY_DECISION_LOG_COLUMNS))
        writer.writeheader()
        for row in rows:
            payload = {column: "" for column in module.ENTRY_DECISION_LOG_COLUMNS}
            payload.update(row)
            writer.writerow(payload)


def test_rollover_entry_decisions_archives_and_cleans(tmp_path, monkeypatch):
    active = tmp_path / "entry_decisions.csv"
    _write_entry_decisions(
        active,
        [
            {"time": "2026-03-18T10:00:00", "symbol": "BTCUSD", "action": "BUY", "outcome": "entered"},
            {"time": "2026-03-18T10:01:00", "symbol": "BTCUSD", "action": "SELL", "outcome": "wait"},
        ],
    )

    old_tail = tmp_path / "entry_decisions.tail_999.csv"
    old_tail.write_text("old", encoding="utf-8")
    old_legacy = tmp_path / "entry_decisions.legacy_20200101_000000.csv"
    old_legacy.write_text("old", encoding="utf-8")
    recent_tail = tmp_path / "entry_decisions.tail_recent.csv"
    recent_tail.write_text("recent", encoding="utf-8")

    old_ts = (datetime.now() - timedelta(days=10)).timestamp()
    os.utime(old_tail, (old_ts, old_ts))
    os.utime(old_legacy, (old_ts, old_ts))

    monkeypatch.setattr(module.Config, "ENTRY_DECISION_LOG_PATH", str(active), raising=False)

    rc = module.main(
        [
            "--max-bytes",
            "1",
            "--archive-root",
            str(tmp_path / "archive"),
            "--manifest-root",
            str(tmp_path / "manifests"),
            "--legacy-retention-days",
            "1",
            "--legacy-retention-count",
            "1",
            "--tail-retention-days",
            "1",
            "--tail-retention-count",
            "1",
        ]
    )

    assert rc == 0
    assert active.exists()
    with active.open("r", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == list(module.ENTRY_DECISION_LOG_COLUMNS)

    rolled = sorted(tmp_path.glob("entry_decisions.legacy_*.csv"))
    assert rolled
    archived = list((tmp_path / "archive").rglob("*.parquet"))
    assert len(archived) == 1

    # Old cleanup targets should be removed, while the most recent files remain.
    assert not old_tail.exists()
    assert not old_legacy.exists()
    assert recent_tail.exists()

    manifest_root = tmp_path / "manifests"
    assert list((manifest_root / "rollover").glob("entry_decisions_rollover_*.json"))
    archive_manifests = list((manifest_root / "archive").glob("entry_decisions_archive_*.json"))
    assert archive_manifests
    assert list((manifest_root / "retention").glob("entry_decisions_retention_*.json"))

    archive_payload = json.loads(archive_manifests[0].read_text(encoding="utf-8"))
    assert archive_payload["time_range_start"] == "2026-03-18T10:00:00"
    assert archive_payload["time_range_end"] == "2026-03-18T10:01:00"
