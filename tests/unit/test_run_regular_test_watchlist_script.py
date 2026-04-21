import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_regular_test_watchlist.py"
spec = importlib.util.spec_from_file_location("run_regular_test_watchlist", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_build_step_commands_includes_watch_report_for_core_profile():
    commands = module._build_step_commands(profile="core", include_watch_report=True)

    assert commands[0][1].endswith("teacher_pattern_step9_watch_report.py")
    assert commands[1][0].endswith("python.exe") or commands[1][0].endswith("python") or commands[1][0] == sys.executable
    assert commands[1][1:3] == ["-m", "pytest"]
    assert "tests/unit/test_teacher_pattern_step9_watch.py" in commands[1]
    assert "tests/unit/test_teacher_pattern_execution_handoff.py" in commands[1]


def test_resolve_tests_for_all_profile_dedupes_repeated_files():
    tests = module._resolve_tests_for_profile("all")

    assert tests.count("tests/unit/test_teacher_pattern_labeler.py") == 1
    assert tests.count("tests/unit/test_runtime_recycle.py") == 1
    assert "tests/unit/test_storage_compaction.py" in tests
    assert "tests/unit/test_teacher_pattern_pilot_baseline.py" in tests


def test_main_dry_run_returns_zero():
    rc = module.main(["--profile", "runtime", "--dry-run"])

    assert rc == 0
