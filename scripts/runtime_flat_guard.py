from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.runtime_flat_guard import (  # noqa: E402
    build_runtime_flat_guard,
    default_runtime_status_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-status-path",
        default=str(default_runtime_status_path()),
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8010/trades/summary",
    )
    parser.add_argument(
        "--max-status-age-sec",
        type=int,
        default=180,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print full payload as json",
    )
    args = parser.parse_args(argv)

    payload = build_runtime_flat_guard(
        runtime_status_path=args.runtime_status_path,
        api_url=args.api_url,
        max_status_age_sec=args.max_status_age_sec,
    )
    summary = dict(payload.get("summary", {}) or {})
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif summary.get("guard_passed"):
        print(
            "[GUARD][OK] flat confirmed "
            f"open_count={summary.get('open_count')} "
            f"status_age_sec={summary.get('status_age_sec')} "
            f"sources={summary.get('guard_sources')}"
        )
    else:
        print(
            "[GUARD][BLOCK] guarded restart unavailable_or_open "
            f"open_count={summary.get('open_count')} "
            f"runtime_reason={summary.get('runtime_reason')} "
            f"api_reason={summary.get('api_reason')}"
        )
    return 0 if summary.get("guard_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
