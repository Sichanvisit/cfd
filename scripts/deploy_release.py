"""Deployment automation: backup bundle + manifest + optional git tag."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[1]
RELEASES_DIR = ROOT / "releases"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.version import APP_VERSION


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_copy(src: Path, dst: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"src": str(src), "dst": str(dst), "copied": False, "reason": ""}
    if not src.exists():
        row["reason"] = "missing"
        return row
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        row["copied"] = True
        row["reason"] = "ok"
    except Exception as exc:
        row["reason"] = str(exc)
    return row


def _fetch_ops_readiness(base_url: str, timeout_sec: float) -> dict[str, Any] | None:
    url = str(base_url).rstrip("/") + "/ops/readiness"
    try:
        req = urlrequest.Request(url=url, method="GET")
        with urlrequest.urlopen(req, timeout=float(timeout_sec)) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return dict(json.loads(raw or "{}"))
    except Exception:
        return None


def _maybe_git_tag(tag_name: str, skip_git_tag: bool) -> dict[str, Any]:
    out = {"attempted": False, "tagged": False, "tag": tag_name, "reason": ""}
    if skip_git_tag:
        out["reason"] = "skipped_by_option"
        return out
    if not (ROOT / ".git").exists():
        out["reason"] = "not_a_git_repository"
        return out
    try:
        out["attempted"] = True
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], cwd=ROOT, check=True)
        out["tagged"] = True
        out["reason"] = "ok"
    except subprocess.CalledProcessError as exc:
        out["reason"] = f"git_tag_failed({exc.returncode})"
    except Exception as exc:
        out["reason"] = str(exc)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Release automation for CFD project")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="FastAPI base URL")
    parser.add_argument("--timeout-sec", type=float, default=8.0, help="Readiness fetch timeout")
    parser.add_argument("--skip-git-tag", action="store_true", help="Do not create a git tag")
    parser.add_argument("--skip-readiness-fetch", action="store_true", help="Do not fetch /ops/readiness")
    args = parser.parse_args()

    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    tag = _now_tag()
    release_name = f"release_{tag}"
    release_dir = RELEASES_DIR / release_name
    release_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        "CHANGELOG.md",
        "backend/core/version.py",
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/ALERT_POLICY.md",
        "0_흐름/STEP11_관측성_확정.md",
        "0_흐름/STEP12_운영변경관리_확정.md",
        "models/ai_models.joblib",
        "models/metrics.json",
        "models/deploy_state.json",
        "data/runtime_status.json",
        "data/runtime_acceptance_baseline.json",
    ]

    copied_rows: list[dict[str, Any]] = []
    copied_count = 0
    for rel in files_to_backup:
        src = ROOT / rel
        dst = release_dir / rel
        row = _safe_copy(src, dst)
        copied_rows.append(row)
        if bool(row.get("copied")):
            copied_count += 1

    readiness = None
    if not args.skip_readiness_fetch:
        readiness = _fetch_ops_readiness(args.base_url, args.timeout_sec)
        if readiness is not None:
            (release_dir / "ops_readiness.json").write_text(
                json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    git_tag = _maybe_git_tag(f"v{APP_VERSION}-{tag}", skip_git_tag=bool(args.skip_git_tag))

    archive_path = shutil.make_archive(str(release_dir), "zip", root_dir=release_dir)

    manifest = {
        "release_name": release_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "app_version": APP_VERSION,
        "copied_count": copied_count,
        "backup_items": copied_rows,
        "archive_path": archive_path,
        "git_tag": git_tag,
        "ops_readiness_included": readiness is not None,
        "ops_readiness_gate": (
            (readiness or {}).get("release_gate", {}) if isinstance(readiness, dict) else {}
        ),
    }
    (release_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASES_DIR / "latest_release.json").write_text(
        json.dumps(
            {
                "release_name": release_name,
                "created_at": manifest["created_at"],
                "archive_path": archive_path,
                "app_version": APP_VERSION,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[DEPLOY] release={release_name}")
    print(f"[DEPLOY] copied={copied_count}/{len(files_to_backup)}")
    print(f"[DEPLOY] archive={archive_path}")
    print(f"[DEPLOY] git_tag tagged={git_tag['tagged']} reason={git_tag['reason']}")
    if readiness is None:
        print("[DEPLOY] readiness_snapshot=missing")
    else:
        gate = (readiness.get("release_gate", {}) if isinstance(readiness, dict) else {})
        print(f"[DEPLOY] readiness_gate={gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
