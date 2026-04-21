"""Build breakout replay/manual learning alignment report."""

from __future__ import annotations

import argparse
import json

from backend.services.breakout_replay_learning_alignment import (
    write_breakout_replay_learning_alignment_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learning-bridge", default=None)
    parser.add_argument("--scaffold", default=None)
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--markdown-output", default=None)
    parser.add_argument("--tolerance-minutes", type=int, default=20)
    args = parser.parse_args()

    payload = write_breakout_replay_learning_alignment_report(
        learning_bridge_path=args.learning_bridge,
        scaffold_csv_path=args.scaffold,
        csv_output_path=args.csv_output,
        json_output_path=args.json_output,
        markdown_output_path=args.markdown_output,
        tolerance_minutes=args.tolerance_minutes,
    )
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
