"""
Run the regular state25/runtime test watchlist with one command.

Usage:
  python scripts/run_regular_test_watchlist.py
  python scripts/run_regular_test_watchlist.py --profile label
  python scripts/run_regular_test_watchlist.py --profile all
  python scripts/run_regular_test_watchlist.py --dry-run
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

CORE_TESTS = [
    "tests/unit/test_teacher_pattern_step9_watch.py",
    "tests/unit/test_teacher_pattern_execution_handoff.py",
    "tests/unit/test_runtime_recycle.py",
    "tests/unit/test_trading_application_runtime_status.py",
    "tests/unit/test_teacher_pattern_labeler.py",
]

LABEL_TESTS = [
    "tests/unit/test_teacher_pattern_labeler.py",
    "tests/unit/test_teacher_pattern_full_labeling_qa.py",
    "tests/unit/test_teacher_pattern_pilot_baseline.py",
    "tests/unit/test_teacher_pattern_asset_calibration.py",
    "tests/unit/test_teacher_pattern_backfill.py",
]

RUNTIME_TESTS = [
    "tests/unit/test_storage_compaction.py",
    "tests/unit/test_trading_application_runner_profile.py",
    "tests/unit/test_trade_logger_entry_atr_proxy.py",
    "tests/unit/test_trading_application_micro_structure.py",
    "tests/unit/test_runtime_recycle.py",
    "tests/unit/test_trading_application_runtime_status.py",
]

TEST_PROFILES = {
    "core": CORE_TESTS,
    "label": LABEL_TESTS,
    "runtime": RUNTIME_TESTS,
}


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        out.append(item)
        seen.add(item)
    return out


def _resolve_tests_for_profile(profile: str) -> list[str]:
    normalized = str(profile or "core").strip().lower()
    if normalized == "all":
        return _dedupe_preserve_order([*CORE_TESTS, *LABEL_TESTS, *RUNTIME_TESTS])
    return list(TEST_PROFILES.get(normalized, CORE_TESTS))


def _build_step_commands(*, profile: str, include_watch_report: bool) -> list[list[str]]:
    commands: list[list[str]] = []
    if include_watch_report:
        commands.append([sys.executable, "scripts/teacher_pattern_step9_watch_report.py"])
    tests = _resolve_tests_for_profile(profile)
    commands.append([sys.executable, "-m", "pytest", *tests, "-q"])
    return commands


def _format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["core", "label", "runtime", "all"],
        default="core",
        help="Which watchlist bundle to run.",
    )
    parser.add_argument(
        "--skip-watch-report",
        action="store_true",
        help="Skip the Step 9 watch report and only run pytest.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands that would run without executing them.",
    )
    args = parser.parse_args(argv)

    commands = _build_step_commands(
        profile=str(args.profile),
        include_watch_report=not bool(args.skip_watch_report),
    )

    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {_format_command(command)}")
        if args.dry_run:
            continue
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode != 0:
            return int(completed.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
