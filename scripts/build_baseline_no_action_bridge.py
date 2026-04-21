"""Build latest AI2 baseline-no-action bridge outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.baseline_no_action_bridge import (  # noqa: E402
    build_baseline_no_action_bridge_outputs,
)


def _default_runtime_status_path() -> Path:
    return ROOT / "data" / "runtime_status.json"


def _default_entry_decisions_path() -> Path:
    return ROOT / "data" / "trades" / "entry_decisions.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "baseline_no_action_bridge_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "baseline_no_action_bridge_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "baseline_no_action_bridge_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-status-path", default=str(_default_runtime_status_path()))
    parser.add_argument("--entry-decisions-path", default=str(_default_entry_decisions_path()))
    parser.add_argument("--recent-limit", type=int, default=200)
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary, markdown = build_baseline_no_action_bridge_outputs(
        runtime_status_path=args.runtime_status_path,
        entry_decisions_path=args.entry_decisions_path,
        recent_limit=int(args.recent_limit),
    )

    csv_output_path = Path(args.csv_output_path)
    json_output_path = Path(args.json_output_path)
    md_output_path = Path(args.md_output_path)
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        json.dumps({"summary": summary, "rows": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_output_path.write_text(markdown, encoding="utf-8")
    print(json.dumps({"csv_output_path": str(csv_output_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
