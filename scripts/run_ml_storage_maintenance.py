from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_ml_storage_baseline import ACTIVE_FILE_POLICIES


DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_MANIFEST_ROOT = DATA_DIR / "manifests"
DEFAULT_REPORT_DIR = DATA_DIR / "reports" / "ml_storage"
RETENTION_MANIFEST_VERSION = "ml_storage_retention_v1"
HEALTH_REPORT_VERSION = "ml_storage_health_report_v1"
CHECKPOINT_VERSION = "ml_storage_monthly_checkpoint_v1"
DEFAULT_REPLAY_RETENTION_DAYS = 30
DEFAULT_REPLAY_RETENTION_COUNT = 20
DEFAULT_ANALYSIS_RETENTION_DAYS = 30
DEFAULT_ANALYSIS_RETENTION_COUNT = 40
DEFAULT_REPORTS_RETENTION_DAYS = 90
DEFAULT_REPORTS_RETENTION_COUNT = 60
DEFAULT_LARGEST_FILES = 20


@dataclass(frozen=True)
class RetentionPolicy:
    name: str
    relative_dir: str
    patterns: tuple[str, ...]
    tier: str
    keep_days: int
    keep_count: int


def _resolve_path(path_like: str | Path | None, *, default: Path) -> Path:
    if path_like in ("", None):
        return default
    target = Path(path_like)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    return target


def _now_slug(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_retention_policies(
    *,
    replay_retention_days: int,
    replay_retention_count: int,
    analysis_retention_days: int,
    analysis_retention_count: int,
    reports_retention_days: int,
    reports_retention_count: int,
) -> list[RetentionPolicy]:
    return [
        RetentionPolicy(
            name="replay_intermediate",
            relative_dir="datasets/replay_intermediate",
            patterns=("*.jsonl",),
            tier="warm",
            keep_days=int(replay_retention_days),
            keep_count=int(replay_retention_count),
        ),
        RetentionPolicy(
            name="analysis",
            relative_dir="analysis",
            patterns=("*",),
            tier="warm",
            keep_days=int(analysis_retention_days),
            keep_count=int(analysis_retention_count),
        ),
        RetentionPolicy(
            name="reports",
            relative_dir="reports",
            patterns=("*",),
            tier="warm",
            keep_days=int(reports_retention_days),
            keep_count=int(reports_retention_count),
        ),
    ]


def _iter_policy_files(data_root: Path, policy: RetentionPolicy) -> list[Path]:
    base_dir = data_root / Path(policy.relative_dir)
    if not base_dir.exists():
        return []
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in policy.patterns:
        for path in base_dir.rglob(pattern):
            if not path.is_file():
                continue
            if path in seen:
                continue
            seen.add(path)
            files.append(path)
    return files


def _cleanup_policy(
    *,
    data_root: Path,
    policy: RetentionPolicy,
    now: datetime,
    dry_run: bool,
) -> dict[str, Any]:
    matched = _iter_policy_files(data_root, policy)
    matched.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    keep_until = now - timedelta(days=max(0, int(policy.keep_days)))

    kept: list[str] = []
    deleted: list[str] = []
    deleted_bytes = 0

    for index, path in enumerate(matched):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo)
        keep_due_to_rank = index < max(0, int(policy.keep_count))
        keep_due_to_age = modified_at >= keep_until
        rel = path.relative_to(data_root).as_posix()
        if keep_due_to_rank or keep_due_to_age:
            kept.append(rel)
            continue
        deleted.append(rel)
        deleted_bytes += int(path.stat().st_size)
        if not dry_run:
            path.unlink(missing_ok=True)

    return {
        "name": policy.name,
        "tier": policy.tier,
        "relative_dir": policy.relative_dir,
        "keep_days": int(policy.keep_days),
        "keep_count": int(policy.keep_count),
        "matched_count": int(len(matched)),
        "kept_count": int(len(kept)),
        "deleted_count": int(len(deleted)),
        "deleted_bytes": int(deleted_bytes),
        "kept_paths": kept,
        "deleted_paths": deleted,
        "dry_run": bool(dry_run),
    }


def _classify_tier(relative_path: str) -> str:
    normalized = str(relative_path or "").replace("\\", "/").lstrip("/")
    hot_paths = {policy.path for policy in ACTIVE_FILE_POLICIES}
    if normalized in hot_paths:
        return "hot"
    if normalized.startswith("datasets/ml_exports/"):
        return "ml"
    if normalized.startswith("datasets/replay_intermediate/"):
        return "warm"
    if normalized.startswith("analysis/"):
        return "warm"
    if normalized.startswith("reports/"):
        return "warm"
    if normalized.startswith("trades/entry_decisions.detail.rotate_"):
        return "warm"
    if normalized.startswith("trades/archive/"):
        return "warm"
    if normalized.startswith("trades/entry_decisions.tail_"):
        return "warm"
    if normalized.startswith("trades/entry_decisions.legacy_"):
        return "warm"
    if normalized.startswith("manifests/"):
        return "cold"
    if normalized.startswith("layouts/") or normalized.startswith("mt5_draw/"):
        return "cold"
    return "cold"


def _scan_files(data_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not data_root.exists():
        return rows
    for path in data_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(data_root).as_posix()
        stat = path.stat()
        rows.append(
            {
                "path": relative,
                "size_bytes": int(stat.st_size),
                "size_mb": round(float(stat.st_size) / (1024.0 * 1024.0), 3),
                "tier": _classify_tier(relative),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
            }
        )
    rows.sort(key=lambda item: int(item["size_bytes"]), reverse=True)
    return rows


def _build_tier_totals(file_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for row in file_rows:
        tier = str(row.get("tier", "cold") or "cold")
        slot = totals.setdefault(tier, {"file_count": 0, "size_bytes": 0, "size_mb": 0.0})
        slot["file_count"] = int(slot["file_count"]) + 1
        slot["size_bytes"] = int(slot["size_bytes"]) + int(row.get("size_bytes", 0) or 0)
    for tier, slot in totals.items():
        slot["size_mb"] = round(float(slot["size_bytes"]) / (1024.0 * 1024.0), 3)
    for tier in ("hot", "warm", "ml", "cold"):
        totals.setdefault(tier, {"file_count": 0, "size_bytes": 0, "size_mb": 0.0})
    return totals


def _build_active_health(data_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy in ACTIVE_FILE_POLICIES:
        target = data_root / Path(policy.path)
        exists = target.exists()
        size_bytes = int(target.stat().st_size) if exists else 0
        status = "missing"
        if exists:
            if size_bytes >= int(policy.critical_bytes):
                status = "critical"
            elif size_bytes >= int(policy.warning_bytes):
                status = "warning"
            else:
                status = "ok"
        rows.append(
            {
                "path": policy.path,
                "owner": policy.owner,
                "tier": policy.tier,
                "exists": bool(exists),
                "size_bytes": int(size_bytes),
                "size_mb": round(float(size_bytes) / (1024.0 * 1024.0), 3),
                "warning_bytes": int(policy.warning_bytes),
                "critical_bytes": int(policy.critical_bytes),
                "status": status,
            }
        )
    return rows


def _latest_manifest_entry(manifest_dir: Path) -> dict[str, Any]:
    if not manifest_dir.exists():
        return {}
    candidates = [path for path in manifest_dir.glob("*.json") if path.is_file()]
    if not candidates:
        return {}
    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    payload = _read_json(latest)
    return {
        "path": str(latest),
        "job_name": str(payload.get("job_name", latest.stem) or latest.stem),
        "created_at": str(payload.get("created_at", "") or ""),
        "status": str(payload.get("status", "success") or "success"),
        "output_path": str(payload.get("output_path", "") or ""),
        "retention_policy": payload.get("retention_policy", ""),
    }


def _manifest_failures(manifest_root: Path, *, limit: int = 10) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    if manifest_root.exists():
        for path in manifest_root.rglob("*.json"):
            payload = _read_json(path)
            status = str(payload.get("status", "") or "").strip().lower()
            stem = path.stem.lower()
            if status in {"failed", "error", "failure"} or "failed" in stem or "error" in stem:
                failures.append(
                    {
                        "path": str(path),
                        "job_name": str(payload.get("job_name", path.stem) or path.stem),
                        "created_at": str(payload.get("created_at", "") or ""),
                        "status": status or "failed",
                    }
                )
    failures.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {
        "count": int(len(failures)),
        "recent": failures[: max(0, int(limit))],
    }


def _build_latest_manifests(manifest_root: Path) -> dict[str, dict[str, Any]]:
    return {
        "baseline": _latest_manifest_entry(manifest_root / "baseline"),
        "rollover": _latest_manifest_entry(manifest_root / "rollover"),
        "archive": _latest_manifest_entry(manifest_root / "archive"),
        "export": _latest_manifest_entry(manifest_root / "export"),
        "retention": _latest_manifest_entry(manifest_root / "retention"),
    }


def _render_health_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ML Storage Health Report",
        "",
        f"- created_at: `{report['created_at']}`",
        f"- report_version: `{report['report_version']}`",
        f"- dry_run: `{report['dry_run']}`",
        "",
        "## Tier Totals",
        "",
        "| tier | file_count | size_mb |",
        "| --- | ---: | ---: |",
    ]
    for tier in ("hot", "warm", "ml", "cold"):
        slot = report["tier_totals"].get(tier, {})
        lines.append(
            f"| {tier} | {int(slot.get('file_count', 0))} | {float(slot.get('size_mb', 0.0)):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Active Health",
            "",
            "| path | status | size_mb |",
            "| --- | --- | ---: |",
        ]
    )
    for row in report["active_health"]:
        lines.append(f"| {row['path']} | {row['status']} | {float(row['size_mb']):.3f} |")
    lines.extend(
        [
            "",
            "## Retention Summary",
            "",
            "| name | matched | kept | deleted | deleted_mb |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["retention_results"]:
        lines.append(
            f"| {row['name']} | {int(row['matched_count'])} | {int(row['kept_count'])} | "
            f"{int(row['deleted_count'])} | {float(row['deleted_bytes']) / (1024.0 * 1024.0):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Largest Files",
            "",
            "| path | tier | size_mb |",
            "| --- | --- | ---: |",
        ]
    )
    for row in report["largest_files"]:
        lines.append(f"| {row['path']} | {row['tier']} | {float(row['size_mb']):.3f} |")
    lines.extend(
        [
            "",
            "## Latest Manifests",
            "",
        ]
    )
    for name, row in report["latest_manifests"].items():
        if not row:
            lines.append(f"- {name}: `missing`")
            continue
        lines.append(
            f"- {name}: `{row.get('job_name', '')}` at `{row.get('created_at', '')}` "
            f"status=`{row.get('status', '')}`"
        )
    failures = report["manifest_failures"]
    lines.extend(
        [
            "",
            "## Manifest Failures",
            "",
            f"- failure_count: `{int(failures.get('count', 0))}`",
        ]
    )
    for item in failures.get("recent", []):
        lines.append(f"- `{item.get('job_name', '')}` `{item.get('created_at', '')}` `{item.get('status', '')}`")
    return "\n".join(lines) + "\n"


def _write_monthly_checkpoint(
    *,
    report_dir: Path,
    now: datetime,
    report: dict[str, Any],
) -> dict[str, str]:
    month_key = now.strftime("%Y_%m")
    checkpoint_dir = report_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    json_path = checkpoint_dir / f"ml_storage_checkpoint_{month_key}.json"
    md_path = checkpoint_dir / f"ml_storage_checkpoint_{month_key}.md"
    payload = {
        "created_at": report["created_at"],
        "checkpoint_version": CHECKPOINT_VERSION,
        "checkpoint_month": month_key,
        "tier_totals": report["tier_totals"],
        "largest_files": report["largest_files"],
        "latest_manifests": report["latest_manifests"],
        "manifest_failures": report["manifest_failures"],
        "active_health_summary": {
            "warning_or_critical": [
                row["path"]
                for row in report["active_health"]
                if row.get("status") in {"warning", "critical"}
            ]
        },
    }
    _write_json(json_path, payload)
    _write_markdown(
        md_path,
        "\n".join(
            [
                "# ML Storage Monthly Checkpoint",
                "",
                f"- checkpoint_month: `{month_key}`",
                f"- created_at: `{report['created_at']}`",
                "",
                "## Warning Or Critical Active Files",
                "",
                *[
                    f"- `{path}`"
                    for path in payload["active_health_summary"]["warning_or_critical"]
                ],
            ]
        )
        + "\n",
    )
    return {
        "json_path": str(json_path),
        "md_path": str(md_path),
    }


def run_ml_storage_maintenance(
    *,
    data_root: Path,
    manifest_root: Path,
    report_dir: Path,
    replay_retention_days: int = DEFAULT_REPLAY_RETENTION_DAYS,
    replay_retention_count: int = DEFAULT_REPLAY_RETENTION_COUNT,
    analysis_retention_days: int = DEFAULT_ANALYSIS_RETENTION_DAYS,
    analysis_retention_count: int = DEFAULT_ANALYSIS_RETENTION_COUNT,
    reports_retention_days: int = DEFAULT_REPORTS_RETENTION_DAYS,
    reports_retention_count: int = DEFAULT_REPORTS_RETENTION_COUNT,
    largest_files: int = DEFAULT_LARGEST_FILES,
    dry_run: bool = False,
) -> dict[str, Any]:
    now = datetime.now().astimezone()
    timestamp = _now_slug(now)
    manifest_root.mkdir(parents=True, exist_ok=True)
    retention_dir = manifest_root / "retention"
    retention_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    policies = _build_retention_policies(
        replay_retention_days=replay_retention_days,
        replay_retention_count=replay_retention_count,
        analysis_retention_days=analysis_retention_days,
        analysis_retention_count=analysis_retention_count,
        reports_retention_days=reports_retention_days,
        reports_retention_count=reports_retention_count,
    )
    retention_results = [
        _cleanup_policy(data_root=data_root, policy=policy, now=now, dry_run=dry_run)
        for policy in policies
    ]

    retention_manifest = {
        "created_at": now.isoformat(),
        "job_name": "ml_storage_retention",
        "schema_version": RETENTION_MANIFEST_VERSION,
        "source_path": str(data_root),
        "output_path": "",
        "row_count": 0,
        "file_size_bytes": 0,
        "retention_policy": {
            row["name"]: {
                "keep_days": row["keep_days"],
                "keep_count": row["keep_count"],
            }
            for row in retention_results
        },
        "notes": retention_results,
        "status": "dry_run" if dry_run else "success",
    }
    retention_manifest_path = retention_dir / f"ml_storage_retention_{timestamp}.json"
    _write_json(retention_manifest_path, retention_manifest)

    file_rows = _scan_files(data_root)
    largest_subset = file_rows[: max(1, int(largest_files))]
    report = {
        "created_at": now.isoformat(),
        "report_version": HEALTH_REPORT_VERSION,
        "dry_run": bool(dry_run),
        "data_root": str(data_root),
        "manifest_root": str(manifest_root),
        "report_dir": str(report_dir),
        "retention_manifest_path": str(retention_manifest_path),
        "retention_results": retention_results,
        "tier_totals": _build_tier_totals(file_rows),
        "active_health": _build_active_health(data_root),
        "largest_files": largest_subset,
        "latest_manifests": _build_latest_manifests(manifest_root),
        "manifest_failures": _manifest_failures(manifest_root),
    }

    report_json_path = report_dir / f"ml_storage_health_{timestamp}.json"
    report_md_path = report_dir / f"ml_storage_health_{timestamp}.md"
    latest_json_path = report_dir / "ml_storage_health_latest.json"
    latest_md_path = report_dir / "ml_storage_health_latest.md"
    _write_json(report_json_path, report)
    _write_markdown(report_md_path, _render_health_markdown(report))
    _write_json(latest_json_path, report)
    _write_markdown(latest_md_path, _render_health_markdown(report))

    checkpoint_paths = _write_monthly_checkpoint(report_dir=report_dir, now=now, report=report)

    summary = {
        "created_at": now.isoformat(),
        "retention_manifest_path": str(retention_manifest_path),
        "report_json_path": str(report_json_path),
        "report_md_path": str(report_md_path),
        "latest_json_path": str(latest_json_path),
        "latest_md_path": str(latest_md_path),
        "checkpoint_json_path": checkpoint_paths["json_path"],
        "checkpoint_md_path": checkpoint_paths["md_path"],
        "largest_files_count": int(len(largest_subset)),
        "deleted_file_count": int(sum(int(row["deleted_count"]) for row in retention_results)),
        "deleted_bytes": int(sum(int(row["deleted_bytes"]) for row in retention_results)),
        "manifest_failure_count": int(report["manifest_failures"]["count"]),
        "warning_or_critical_active_files": [
            row["path"]
            for row in report["active_health"]
            if row.get("status") in {"warning", "critical"}
        ],
        "dry_run": bool(dry_run),
    }
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run retention cleanup and health reporting for ML storage tiers.")
    parser.add_argument("--data-root", default=str(DATA_DIR))
    parser.add_argument("--manifest-root", default=str(DEFAULT_MANIFEST_ROOT))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--replay-retention-days", type=int, default=DEFAULT_REPLAY_RETENTION_DAYS)
    parser.add_argument("--replay-retention-count", type=int, default=DEFAULT_REPLAY_RETENTION_COUNT)
    parser.add_argument("--analysis-retention-days", type=int, default=DEFAULT_ANALYSIS_RETENTION_DAYS)
    parser.add_argument("--analysis-retention-count", type=int, default=DEFAULT_ANALYSIS_RETENTION_COUNT)
    parser.add_argument("--reports-retention-days", type=int, default=DEFAULT_REPORTS_RETENTION_DAYS)
    parser.add_argument("--reports-retention-count", type=int, default=DEFAULT_REPORTS_RETENTION_COUNT)
    parser.add_argument("--largest-files", type=int, default=DEFAULT_LARGEST_FILES)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_ml_storage_maintenance(
        data_root=_resolve_path(args.data_root, default=DATA_DIR),
        manifest_root=_resolve_path(args.manifest_root, default=DEFAULT_MANIFEST_ROOT),
        report_dir=_resolve_path(args.report_dir, default=DEFAULT_REPORT_DIR),
        replay_retention_days=int(args.replay_retention_days),
        replay_retention_count=int(args.replay_retention_count),
        analysis_retention_days=int(args.analysis_retention_days),
        analysis_retention_count=int(args.analysis_retention_count),
        reports_retention_days=int(args.reports_retention_days),
        reports_retention_count=int(args.reports_retention_count),
        largest_files=int(args.largest_files),
        dry_run=bool(args.dry_run),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
