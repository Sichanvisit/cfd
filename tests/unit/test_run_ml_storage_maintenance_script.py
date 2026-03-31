import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_ml_storage_maintenance.py"
spec = importlib.util.spec_from_file_location("run_ml_storage_maintenance", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _touch(path: Path, *, text: str, days_old: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if days_old > 0:
        ts = (datetime.now() - timedelta(days=days_old)).timestamp()
        os.utime(path, (ts, ts))


def test_run_ml_storage_maintenance_cleans_and_reports(tmp_path):
    data_root = tmp_path / "data"
    manifest_root = data_root / "manifests"
    report_dir = data_root / "reports" / "ml_storage"

    _touch(data_root / "datasets" / "replay_intermediate" / "recent.jsonl", text="recent", days_old=1)
    _touch(data_root / "datasets" / "replay_intermediate" / "old.jsonl", text="old", days_old=45)
    _touch(data_root / "analysis" / "recent.json", text="{}", days_old=1)
    _touch(data_root / "analysis" / "old.json", text="{}", days_old=40)
    _touch(data_root / "reports" / "recent.md", text="# recent", days_old=1)
    _touch(data_root / "reports" / "old.md", text="# old", days_old=120)
    _touch(data_root / "trades" / "entry_decisions.csv", text="time,symbol\n", days_old=0)
    _touch(data_root / "runtime_status.json", text="{}", days_old=0)

    rollover_manifest = manifest_root / "rollover" / "entry_decisions_rollover_20260318_180000.json"
    rollover_manifest.parent.mkdir(parents=True, exist_ok=True)
    rollover_manifest.write_text(
        json.dumps({"created_at": "2026-03-18T18:00:00+09:00", "job_name": "entry_decisions_rollover", "status": "success"}),
        encoding="utf-8",
    )
    export_manifest = manifest_root / "export" / "entry_decisions_ml_export_forecast_20260318_180500.json"
    export_manifest.parent.mkdir(parents=True, exist_ok=True)
    export_manifest.write_text(
        json.dumps({"created_at": "2026-03-18T18:05:00+09:00", "job_name": "entry_decisions_ml_export_forecast", "status": "success"}),
        encoding="utf-8",
    )
    export_failure_manifest = manifest_root / "export" / "entry_decisions_ml_export_forecast_failed_20260318_180600.json"
    export_failure_manifest.write_text(
        json.dumps({"created_at": "2026-03-18T18:06:00+09:00", "job_name": "entry_decisions_ml_export_forecast", "status": "failed"}),
        encoding="utf-8",
    )

    summary = module.run_ml_storage_maintenance(
        data_root=data_root,
        manifest_root=manifest_root,
        report_dir=report_dir,
        replay_retention_days=7,
        replay_retention_count=1,
        analysis_retention_days=7,
        analysis_retention_count=1,
        reports_retention_days=30,
        reports_retention_count=1,
        largest_files=5,
        dry_run=False,
    )

    assert not (data_root / "datasets" / "replay_intermediate" / "old.jsonl").exists()
    assert (data_root / "datasets" / "replay_intermediate" / "recent.jsonl").exists()
    assert not (data_root / "analysis" / "old.json").exists()
    assert (data_root / "analysis" / "recent.json").exists()
    assert not (data_root / "reports" / "old.md").exists()
    assert (data_root / "reports" / "recent.md").exists()

    retention_manifest_path = Path(summary["retention_manifest_path"])
    report_json_path = Path(summary["report_json_path"])
    report_md_path = Path(summary["report_md_path"])
    latest_json_path = Path(summary["latest_json_path"])
    checkpoint_json_path = Path(summary["checkpoint_json_path"])

    assert retention_manifest_path.exists()
    assert report_json_path.exists()
    assert report_md_path.exists()
    assert latest_json_path.exists()
    assert checkpoint_json_path.exists()
    assert summary["deleted_file_count"] >= 3
    assert summary["manifest_failure_count"] == 1

    report = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report["report_version"] == module.HEALTH_REPORT_VERSION
    assert report["latest_manifests"]["rollover"]["job_name"] == "entry_decisions_rollover"
    assert report["latest_manifests"]["export"]["job_name"] == "entry_decisions_ml_export_forecast"
    assert report["manifest_failures"]["count"] == 1
    assert report["largest_files"]
    assert any(row["path"] == "trades/entry_decisions.csv" for row in report["active_health"])
