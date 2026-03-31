from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_DIR = PROJECT_ROOT / "models" / "semantic_v1"
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "models" / "backups"
DEFAULT_MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests" / "rollout"
DEFAULT_AUDIT_PATH = PROJECT_ROOT / "data" / "analysis" / "semantic_v1" / "semantic_preview_audit_latest.json"

PROMOTION_MANIFEST_VERSION = "semantic_shadow_promotion_v1"
REQUIRED_MODEL_FILES = (
    "timing_model.joblib",
    "entry_quality_model.joblib",
    "exit_management_model.joblib",
    "metrics.json",
)


def _resolve_path(value: str | Path | None, default: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected object JSON: {path}")
    return dict(payload)


def _ensure_required_files(source_dir: Path) -> list[Path]:
    missing = [name for name in REQUIRED_MODEL_FILES if not (source_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"semantic preview source is missing required files: {', '.join(missing)}"
        )
    return [source_dir / name for name in REQUIRED_MODEL_FILES]


def _audit_gate_summary(audit_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(audit_payload or {})
    promotion_gate = dict(payload.get("promotion_gate", {}) or {})
    return {
        "shadow_compare_ready": bool(promotion_gate.get("shadow_compare_ready", False)),
        "status": str(promotion_gate.get("status", "") or ""),
        "blocking_issues": list(promotion_gate.get("blocking_issues", []) or []),
        "warning_issues": list(promotion_gate.get("warning_issues", []) or []),
        "shadow_compare_status": str(promotion_gate.get("shadow_compare_status", "") or ""),
        "shadow_compare_report_path": str(promotion_gate.get("shadow_compare_report_path", "") or ""),
    }


def _metrics_summary(metrics_payload: Mapping[str, Any]) -> dict[str, Any]:
    def _target_summary(key: str) -> dict[str, Any]:
        metrics = dict(metrics_payload.get(f"{key}_metrics", {}) or {})
        return {
            "auc": metrics.get("auc"),
            "accuracy": metrics.get("accuracy"),
            "split_health_status": metrics.get("split_health_status"),
            "promotion_blocked": metrics.get("split_health_promotion_blocked"),
        }

    return {
        "timing": _target_summary("timing"),
        "entry_quality": _target_summary("entry_quality"),
        "exit_management": _target_summary("exit_management"),
    }


def promote_semantic_preview_to_shadow(
    *,
    source_dir: str | Path,
    target_dir: str | Path | None = None,
    backup_root: str | Path | None = None,
    manifest_dir: str | Path | None = None,
    audit_path: str | Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_dir = _resolve_path(source_dir, PROJECT_ROOT / "models")
    target_dir = _resolve_path(target_dir, DEFAULT_TARGET_DIR)
    backup_root = _resolve_path(backup_root, DEFAULT_BACKUP_ROOT)
    manifest_dir = _resolve_path(manifest_dir, DEFAULT_MANIFEST_DIR)
    audit_path = _resolve_path(audit_path, DEFAULT_AUDIT_PATH)

    if not source_dir.exists():
        raise FileNotFoundError(f"semantic preview source dir not found: {source_dir}")
    required_files = _ensure_required_files(source_dir)
    metrics_path = source_dir / "metrics.json"
    metrics_payload = _load_json(metrics_path)

    audit_payload: dict[str, Any] | None = None
    if audit_path.exists():
        audit_payload = _load_json(audit_path)
    audit_summary = _audit_gate_summary(audit_payload)
    if not force and not audit_summary["shadow_compare_ready"]:
        raise ValueError(
            "semantic preview audit is not shadow-compare ready; "
            "use --force to override only if you have reviewed the blockers."
        )

    manifest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir: Path | None = None

    if target_dir.exists() and any(target_dir.iterdir()):
        backup_dir = backup_root / f"semantic_v1_{timestamp}"

    promoted_files = [path.name for path in required_files]
    source_files = sorted(path.name for path in source_dir.iterdir() if path.is_file())

    if not dry_run:
        if backup_dir is not None:
            backup_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target_dir, backup_dir)
            shutil.rmtree(target_dir)
        elif target_dir.exists():
            shutil.rmtree(target_dir)

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)

    manifest = {
        "created_at": datetime.now().astimezone().isoformat(),
        "manifest_version": PROMOTION_MANIFEST_VERSION,
        "job_name": "semantic_shadow_promotion",
        "status": "dry_run" if dry_run else "success",
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "backup_dir": (str(backup_dir) if backup_dir is not None else ""),
        "audit_path": str(audit_path),
        "audit_summary": audit_summary,
        "metrics_path": str(metrics_path),
        "metrics_summary": _metrics_summary(metrics_payload),
        "promoted_files": promoted_files,
        "source_files": source_files,
        "force": bool(force),
        "dry_run": bool(dry_run),
    }

    manifest_path = manifest_dir / f"semantic_shadow_promotion_{timestamp}.json"
    latest_manifest_path = manifest_dir / "semantic_shadow_promotion_latest.json"
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    latest_manifest_path.write_text(manifest_text, encoding="utf-8")

    manifest["manifest_path"] = str(manifest_path)
    manifest["latest_manifest_path"] = str(latest_manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote a semantic_v1 preview model bundle into the active semantic shadow model directory."
    )
    parser.add_argument("--source-dir", required=True, help="Preview model directory to promote")
    parser.add_argument(
        "--target-dir",
        default=str(DEFAULT_TARGET_DIR),
        help="Active semantic shadow model directory",
    )
    parser.add_argument(
        "--backup-root",
        default=str(DEFAULT_BACKUP_ROOT),
        help="Backup root used when target dir already exists",
    )
    parser.add_argument(
        "--manifest-dir",
        default=str(DEFAULT_MANIFEST_DIR),
        help="Directory where promotion manifests are written",
    )
    parser.add_argument(
        "--audit-path",
        default=str(DEFAULT_AUDIT_PATH),
        help="Preview audit JSON path used to gate promotion",
    )
    parser.add_argument("--force", action="store_true", help="Allow promotion even if audit is not ready")
    parser.add_argument("--dry-run", action="store_true", help="Write only the manifest without copying files")
    args = parser.parse_args()

    manifest = promote_semantic_preview_to_shadow(
        source_dir=args.source_dir,
        target_dir=args.target_dir,
        backup_root=args.backup_root,
        manifest_dir=args.manifest_dir,
        audit_path=args.audit_path,
        force=bool(args.force),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
