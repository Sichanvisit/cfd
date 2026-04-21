"""Build latest breakout historical calibration bridge outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.breakout_historical_calibration_bridge import (  # noqa: E402
    build_breakout_historical_calibration_bridge,
    render_breakout_historical_calibration_bridge_markdown,
)


def _default_alignment_csv_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_replay_learning_alignment_latest.csv"


def _default_seed_csv_path() -> Path:
    return ROOT / "data" / "analysis" / "breakout_event" / "breakout_aligned_training_seed_latest.csv"


def _default_csv_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "breakout_historical_calibration_bridge_latest.csv"


def _default_json_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "breakout_historical_calibration_bridge_latest.json"


def _default_md_output_path() -> Path:
    return ROOT / "data" / "analysis" / "shadow_auto" / "breakout_historical_calibration_bridge_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alignment-csv-path", default=str(_default_alignment_csv_path()))
    parser.add_argument("--seed-csv-path", default=str(_default_seed_csv_path()))
    parser.add_argument("--csv-output-path", default=str(_default_csv_output_path()))
    parser.add_argument("--json-output-path", default=str(_default_json_output_path()))
    parser.add_argument("--md-output-path", default=str(_default_md_output_path()))
    args = parser.parse_args()

    frame, summary = build_breakout_historical_calibration_bridge(
        args.alignment_csv_path,
        args.seed_csv_path,
    )
    markdown = render_breakout_historical_calibration_bridge_markdown(summary, frame)

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
