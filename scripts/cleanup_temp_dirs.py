"""Best-effort cleanup for local temp/test artifact directories."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


TARGETS = [
    ".tmp_manual",
    ".pytest_tmp_run",
    ".tmp_pytest",
    ".tmp_pytest_run",
    "pytest-tmp",
    "pytest_temp",
    "pytest_temp_run",
    "pytest_temp_run2",
    "temp_run",
    "cache_run",
    "tests/.tmp_manual",
    "tests/tmp_local",
    "tests/tmp_os",
    "tests/tmp_run",
    "tests/tmp_work",
]


def _safe_rmtree(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return True, "missing"
    try:
        shutil.rmtree(path, ignore_errors=False)
        return True, "removed"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup known temp/test artifact directories")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if any cleanup target fails")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    ok = True
    for rel in TARGETS:
        p = root / rel
        done, msg = _safe_rmtree(p)
        tag = "OK" if done else "SKIP"
        print(f"[CLEANUP][{tag}] {rel} -> {msg}")
        if not done:
            ok = False
    if ok:
        return 0
    if args.strict:
        return 1
    print("[CLEANUP] completed with skipped targets (non-strict mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
