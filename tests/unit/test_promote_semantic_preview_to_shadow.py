import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "promote_semantic_preview_to_shadow.py"
spec = importlib.util.spec_from_file_location("promote_semantic_preview_to_shadow", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_preview_source(path: Path) -> None:
    _write_text(path / "timing_model.joblib", "timing")
    _write_text(path / "entry_quality_model.joblib", "entry")
    _write_text(path / "exit_management_model.joblib", "exit")
    _write_text(
        path / "metrics.json",
        json.dumps(
            {
                "timing_metrics": {"auc": 0.61, "accuracy": 0.63, "split_health_status": "healthy"},
                "entry_quality_metrics": {"auc": 0.59, "accuracy": 0.44, "split_health_status": "warning"},
                "exit_management_metrics": {"auc": 0.90, "accuracy": 0.60, "split_health_status": "warning"},
            }
        ),
    )
    _write_text(path / "timing_model.summary.json", "{}")


def _write_audit(path: Path, *, ready: bool) -> None:
    _write_text(
        path,
        json.dumps(
            {
                "promotion_gate": {
                    "shadow_compare_ready": ready,
                    "status": "pass" if ready else "blocked",
                    "blocking_issues": [] if ready else ["timing:split_health_fail"],
                    "warning_issues": ["entry_quality:split_health_warning"],
                }
            }
        ),
    )


def test_promote_semantic_preview_to_shadow_copies_bundle_and_writes_manifest(tmp_path):
    source_dir = tmp_path / "models" / "semantic_v1_preview_candidate"
    target_dir = tmp_path / "models" / "semantic_v1"
    backup_root = tmp_path / "models" / "backups"
    manifest_dir = tmp_path / "data" / "manifests" / "rollout"
    audit_path = tmp_path / "data" / "analysis" / "semantic_v1" / "semantic_preview_audit_latest.json"

    _build_preview_source(source_dir)
    _write_audit(audit_path, ready=True)
    _write_text(target_dir / "stale.txt", "old-active")

    summary = module.promote_semantic_preview_to_shadow(
        source_dir=source_dir,
        target_dir=target_dir,
        backup_root=backup_root,
        manifest_dir=manifest_dir,
        audit_path=audit_path,
    )

    assert (target_dir / "timing_model.joblib").read_text(encoding="utf-8") == "timing"
    assert not (target_dir / "stale.txt").exists()
    backup_dir = Path(summary["backup_dir"])
    assert backup_dir.exists()
    assert (backup_dir / "stale.txt").read_text(encoding="utf-8") == "old-active"

    manifest_path = Path(summary["manifest_path"])
    latest_manifest_path = Path(summary["latest_manifest_path"])
    assert manifest_path.exists()
    assert latest_manifest_path.exists()
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["audit_summary"]["shadow_compare_ready"] is True
    assert manifest_payload["metrics_summary"]["timing"]["auc"] == 0.61


def test_promote_semantic_preview_to_shadow_blocks_when_audit_not_ready(tmp_path):
    source_dir = tmp_path / "models" / "semantic_v1_preview_candidate"
    target_dir = tmp_path / "models" / "semantic_v1"
    manifest_dir = tmp_path / "data" / "manifests" / "rollout"
    audit_path = tmp_path / "data" / "analysis" / "semantic_v1" / "semantic_preview_audit_latest.json"

    _build_preview_source(source_dir)
    _write_audit(audit_path, ready=False)

    with pytest.raises(ValueError):
        module.promote_semantic_preview_to_shadow(
            source_dir=source_dir,
            target_dir=target_dir,
            manifest_dir=manifest_dir,
            audit_path=audit_path,
        )
