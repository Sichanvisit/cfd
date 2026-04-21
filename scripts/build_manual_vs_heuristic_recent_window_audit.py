"""Build a recent-window overlap audit for manual-vs-heuristic comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.manual_vs_heuristic_recent_window_audit import (  # noqa: E402
    build_manual_vs_heuristic_recent_window_audit,
    render_manual_vs_heuristic_recent_window_audit_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-annotations-path", default=str(ROOT / "data" / "manual_annotations" / "manual_wait_teacher_annotations.csv"))
    parser.add_argument("--current-entry-decisions-path", default=str(ROOT / "data" / "trades" / "entry_decisions.csv"))
    parser.add_argument("--json-output-path", default=str(ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_recent_window_audit_latest.json"))
    parser.add_argument("--md-output-path", default=str(ROOT / "data" / "manual_annotations" / "manual_vs_heuristic_recent_window_audit_latest.md"))
    args = parser.parse_args()

    summary = build_manual_vs_heuristic_recent_window_audit(
        args.manual_annotations_path,
        args.current_entry_decisions_path,
    )
    json_path = Path(args.json_output_path)
    md_path = Path(args.md_output_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_manual_vs_heuristic_recent_window_audit_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
