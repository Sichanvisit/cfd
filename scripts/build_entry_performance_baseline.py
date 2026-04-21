"""Lock current entry performance baseline and refresh regression watch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.entry_performance_baseline import (  # noqa: E402
    build_entry_performance_baseline_lock,
    build_entry_performance_regression_watch,
    render_entry_performance_baseline_markdown,
)


def _load_json(path: str | Path) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_entry_eval_profile_path() -> Path:
    return ROOT / "data" / "analysis" / "entry_eval_profile_latest.json"


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_runtime_loop_debug_path() -> Path:
    return ROOT / "data" / "runtime_loop_debug.json"


def _default_baseline_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "entry_performance_baseline_latest.json"


def _default_regression_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "entry_performance_regression_watch_latest.json"


def _default_markdown_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "entry_performance_baseline_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-eval-profile-path", default=str(_default_entry_eval_profile_path()))
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--runtime-loop-debug-path", default=str(_default_runtime_loop_debug_path()))
    parser.add_argument("--baseline-json-output-path", default=str(_default_baseline_json_output_path()))
    parser.add_argument("--regression-json-output-path", default=str(_default_regression_json_output_path()))
    parser.add_argument("--markdown-output-path", default=str(_default_markdown_output_path()))
    parser.add_argument("--reentry-elapsed-ms", type=float, default=200.0)
    parser.add_argument("--refresh-lock", action="store_true")
    args = parser.parse_args()

    profile_collection = _load_json(args.entry_eval_profile_path)
    runtime_status = _load_json(args.runtime_status_path)
    runtime_loop_debug = _load_json(args.runtime_loop_debug_path)

    baseline_json_output_path = Path(args.baseline_json_output_path)
    regression_json_output_path = Path(args.regression_json_output_path)
    markdown_output_path = Path(args.markdown_output_path)
    baseline_json_output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_baseline = _load_json(baseline_json_output_path)
    if args.refresh_lock or not existing_baseline:
        baseline_lock = build_entry_performance_baseline_lock(
            profile_collection,
            runtime_status=runtime_status,
            reentry_elapsed_ms=float(args.reentry_elapsed_ms),
        )
        lock_refreshed = True
    else:
        baseline_lock = dict(existing_baseline)
        lock_refreshed = False

    regression_watch = build_entry_performance_regression_watch(
        profile_collection,
        baseline_lock,
        runtime_status=runtime_status,
        runtime_loop_debug=runtime_loop_debug,
    )
    markdown = render_entry_performance_baseline_markdown(baseline_lock, regression_watch)

    baseline_json_output_path.write_text(
        json.dumps(baseline_lock, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    regression_json_output_path.write_text(
        json.dumps(regression_watch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_output_path.write_text(markdown, encoding="utf-8")

    print(
        json.dumps(
            {
                "baseline_json_output_path": str(baseline_json_output_path),
                "regression_json_output_path": str(regression_json_output_path),
                "markdown_output_path": str(markdown_output_path),
                "lock_refreshed": bool(lock_refreshed),
                "baseline_recommended_next_action": baseline_lock.get("recommended_next_action", ""),
                "regression_recommended_next_action": regression_watch.get("recommended_next_action", ""),
                "reentry_required": bool(regression_watch.get("reentry_required", False)),
                "reentry_symbols": list(regression_watch.get("reentry_symbols", []) or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
